"""L'app : icône dans la barre de menus, panneau, page, fil de travail.

Seul fichier qui importe AppKit / WebKit / PyObjCTools. La logique testable est dans ordres.py.
"""

import fcntl
import json
import sys
import threading
import time
from pathlib import Path

import objc
from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSBackingStoreBuffered,
    NSColor,
    NSColorSpace,
    NSEvent,
    NSEventMaskLeftMouseDown,
    NSEventMaskRightMouseDown,
    NSImage,
    NSMakeRect,
    NSObject,
    NSPanel,
    NSPopUpMenuWindowLevel,
    NSScreen,
    NSStatusBar,
    NSVariableStatusItemLength,
    NSView,
    NSVisualEffectView,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
)
from Foundation import NSJSONSerialization, NSURL
from PyObjCTools import AppHelper
from WebKit import WKWebView, WKWebViewConfiguration

from . import etat as etat_mod
from . import demarrage, ordres, reglages
from .bridge import Bridge, BridgeErreur

DOSSIER_PAGE = Path(__file__).parent / "panneau"
LARGEUR, HAUTEUR = 360, 600
DELAI_APRES_ORDRE = 0.6  # le bridge met un instant à refléter l'ordre
DELAI_SECONDE_LECTURE = 1.4  # puis une seconde relecture : la première tombe quand la page ignore encore l'état
MARGE = 32  # la fenêtre dépasse le panneau de cette marge, pour que son ombre ait la place de s'éteindre
RAYON = 20  # coins du panneau, comme ceux des panneaux de la barre de menus du système
ECART = 6  # entre la barre de menus et le panneau
RELECTURE_OUVERT = 5  # secondes entre deux lectures du vif, panneau ouvert
RELECTURE_COMPLETE = 600  # secondes : noms, zones et appareils changent rarement


JOURNAL = "--journal" in sys.argv  # écrit chaque message et chaque appel au bridge, avec sa durée


def noter(*quoi):
    if JOURNAL:
        print(f"{time.monotonic() % 1000:8.3f}", *quoi, flush=True)


class Travail:
    """Le fil de travail : seul à toucher au Bridge. Les résultats repartent par `pousser`.

    Les ordres passent par une Cadence (un par cible, au rythme que le bridge supporte). La boucle dort sur une
    Condition jusqu'à la prochaine échéance ; elle ne fait jamais de réseau en tenant le verrou.
    """

    def __init__(self, ip, cle, piece, pousser):
        self._bridge = Bridge(ip, cle)
        self._piece = piece
        self._pousser = pousser
        self._brut = None
        self._tout_relire = True
        self.derniere_complete = 0.0  # lu aussi par le fil principal : un simple flottant
        self.dernier_etat = None
        self.id_groupe = None
        self._verrou = threading.Condition()
        self._cadence = ordres.Cadence()
        self._demande = None  # None, "vif" ou "tout" ("tout" l'emporte)
        self._ouvert = False
        self._relecture_due = None  # heure de la relecture qui suit le dernier ordre
        self._seconde = False  # la première relecture est faite, la seconde est due
        self._arrete = False  # lu et écrit sous le verrou
        self._derniere_lecture = float("-inf")
        threading.Thread(target=self._boucle, daemon=True).start()

    def ordre(self, ressource, identifiant, corps):
        with self._verrou:
            self._cadence.poser((ressource, identifiant, corps))
            self._verrou.notify()

    def lire(self, complet=False):
        with self._verrou:
            if complet or self._demande is None:
                self._demande = "tout" if complet else "vif"
            self._verrou.notify()

    def panneau(self, ouvert):
        with self._verrou:
            self._ouvert = ouvert
            self._verrou.notify()

    def arreter(self):
        """Termine la boucle ; plus rien n'est publié ensuite."""
        with self._verrou:
            self._arrete = True
            self._verrou.notify()

    def _boucle(self):
        while True:
            action = self._choisir()
            if action[0] == "fin":
                self._bridge.fermer()
                return
            try:
                if action[0] == "ecrire":
                    debut = time.monotonic()
                    self._bridge.ecrire(*action[1])
                    noter("écrit", action[1][0], action[1][2], f"{(time.monotonic() - debut) * 1000:.0f} ms")
                    with self._verrou:  # repoussée à chaque ordre : une seule relecture après le dernier
                        self._relecture_due = time.monotonic() + DELAI_APRES_ORDRE
                        self._seconde = False
                else:
                    self._derniere_lecture = time.monotonic()
                    self._lire(complet=action[0] == "tout")
                    noter("lu", action[0], f"{(time.monotonic() - self._derniere_lecture) * 1000:.0f} ms")
            except BridgeErreur:
                self._tout_relire = True
                self._publier(etat_mod.erreur("Le bridge ne répond pas."))
            except Exception as exc:  # le fil ne doit jamais mourir en silence
                self._tout_relire = True
                print("erreur inattendue :", type(exc).__name__, flush=True)
                self._publier(etat_mod.erreur("Le bridge ne répond pas."))

    def _choisir(self):
        """Attend sous le verrou jusqu'à avoir une action à faire, puis la rend (le verrou est relâché)."""
        with self._verrou:
            while True:
                if self._arrete:
                    return ("fin",)
                maintenant = time.monotonic()
                ordre, attente = self._cadence.prochain(maintenant)
                if ordre is not None:
                    return ("ecrire", ordre)
                if self._demande is not None:
                    demande, self._demande = self._demande, None
                    return (demande,)
                if self._relecture_due is not None and maintenant >= self._relecture_due:
                    self._relecture_due = None if self._seconde else maintenant + DELAI_SECONDE_LECTURE
                    self._seconde = not self._seconde
                    return ("vif",)
                echeances = []
                if attente is not None:
                    echeances.append(attente)
                if self._relecture_due is not None:
                    echeances.append(self._relecture_due - maintenant)
                if self._ouvert:
                    reste = self._derniere_lecture + RELECTURE_OUVERT - maintenant
                    if reste <= 0:
                        return ("vif",)
                    echeances.append(reste)
                self._verrou.wait(min(echeances) if echeances else None)

    def _lire(self, complet):
        if complet or self._tout_relire or self._brut is None:
            self._brut = ordres.lire_tout(self._bridge)
            self._tout_relire = False
            self.derniere_complete = time.monotonic()
        else:
            self._brut = ordres.lire_vif(self._bridge, self._brut)
        self.id_groupe = ordres.groupe_de(self._brut, self._piece)
        self._publier(etat_mod.construire(self._brut, self._piece))

    def _publier(self, etat):
        with self._verrou:
            if self._arrete:
                return
        self.dernier_etat = etat
        AppHelper.callAfter(self._pousser, etat)


def accent_du_mac():
    """La couleur d'accent choisie dans les réglages du Mac, en #rrggbb."""
    c = NSColor.controlAccentColor().colorUsingColorSpace_(NSColorSpace.sRGBColorSpace())
    return "#%02x%02x%02x" % tuple(round(255 * v) for v in (c.redComponent(), c.greenComponent(), c.blueComponent()))


def corps_en_dict(corps):
    """NSDictionary -> dict Python. Passer par JSON garantit de vrais bool, str, int."""
    try:
        donnees, _ = NSJSONSerialization.dataWithJSONObject_options_error_(corps, 0, None)
        return json.loads(bytes(donnees))
    except Exception:
        return None


class Fenetre(NSPanel):
    def canBecomeKeyWindow(self):  # sans ça, une fenêtre sans bord refuse les clics dans la page
        return True


def fond_en_verre(page):
    """Le fond des panneaux du système : le verre de macOS 26, sinon le flou des versions d'avant.

    NSPopover, essayé d'abord, a un fond presque opaque : le panneau ne ressemblait pas à ceux du Mac.
    """
    cadre = NSMakeRect(0, 0, LARGEUR, HAUTEUR)
    try:
        verre = objc.lookUpClass("NSGlassEffectView").alloc().initWithFrame_(cadre)
        verre.setCornerRadius_(RAYON)
        verre.setContentView_(page)
        return verre
    except objc.nosuchclass_error:
        flou = NSVisualEffectView.alloc().initWithFrame_(cadre)
        flou.setMaterial_(6)  # NSVisualEffectMaterialPopover
        flou.setState_(1)  # actif même quand l'app n'a pas la main
        flou.setWantsLayer_(True)
        flou.layer().setCornerRadius_(RAYON)
        flou.layer().setMasksToBounds_(True)
        page.setFrame_(cadre)
        flou.addSubview_(page)
        return flou


class Pont(NSObject, protocols=[objc.protocolNamed("WKScriptMessageHandler")]):
    def userContentController_didReceiveScriptMessage_(self, controleur, message):
        self.app.message_de_la_page(corps_en_dict(message.body()))


class App(NSObject):
    def applicationDidFinishLaunching_(self, _):
        self.page_prete = False
        self.travail = None
        self.etat_sans_bridge = None

        self.icone = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        bouton = self.icone.button()
        bouton.setImage_(NSImage.imageWithSystemSymbolName_accessibilityDescription_("lightbulb", "Lumières"))
        bouton.setTarget_(self)
        bouton.setAction_("basculer:")

        config = WKWebViewConfiguration.alloc().init()
        self.pont = Pont.alloc().init()
        self.pont.app = self
        config.userContentController().addScriptMessageHandler_name_(self.pont, "pont")
        self.page = WKWebView.alloc().initWithFrame_configuration_(NSMakeRect(0, 0, LARGEUR, HAUTEUR), config)
        self.page.setValue_forKey_(False, "drawsBackground")  # le fond translucide du panneau passe au travers
        self.page.loadFileURL_allowingReadAccessToURL_(
            NSURL.fileURLWithPath_(str(DOSSIER_PAGE / "index.html")),
            NSURL.fileURLWithPath_isDirectory_(str(DOSSIER_PAGE), True),
        )

        self.panneau = Fenetre.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, LARGEUR + 2 * MARGE, HAUTEUR + 2 * MARGE),
            NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel,  # ne prend pas la main à l'app en cours
            NSBackingStoreBuffered,
            False,
        )
        self.panneau.setOpaque_(False)
        self.panneau.setBackgroundColor_(NSColor.clearColor())
        # Pas d'ombre de fenêtre : macOS la dessinait sur le rectangle de la fenêtre, d'où un cadre gris et un fond dans
        # les coins arrondis (vu par Antho le 12/11/2026). L'ombre est celle du panneau lui-même, dans la marge.
        self.panneau.setHasShadow_(False)
        self.panneau.setLevel_(NSPopUpMenuWindowLevel)
        cadre = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, LARGEUR + 2 * MARGE, HAUTEUR + 2 * MARGE))
        fond = fond_en_verre(self.page)
        fond.setFrameOrigin_((MARGE, MARGE))
        cadre.addSubview_(fond)
        self.panneau.setContentView_(cadre)
        # Un clic ailleurs referme le panneau (les clics dans nos propres fenêtres n'arrivent pas ici).
        self.guet = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
            NSEventMaskLeftMouseDown | NSEventMaskRightMouseDown, lambda _: self.fermer()
        )

        regl = reglages.charger()
        if regl is None:
            self.etat_sans_bridge = etat_mod.sans_reglages("Réglages absents : voir le README.")
        else:
            self.travail = Travail(regl["bridge_ip"], regl["cle"], regl["piece"], self.pousser)
            self.travail.lire(complet=True)

        if ESSAI:
            AppHelper.callLater(1, self.basculer_, None)
            AppHelper.callLater(3, self.bilan)

    @objc.python_method
    def dernier_etat(self):
        return self.travail.dernier_etat if self.travail else self.etat_sans_bridge

    def basculer_(self, _):
        if self.panneau.isVisible():
            self.fermer()
            return
        icone = self.icone.button().window().frame()
        ecran = NSScreen.mainScreen().frame()
        # Centré sous l'icône, sans sortir de l'écran.
        x = min(max(icone.origin.x + icone.size.width / 2 - LARGEUR / 2, 8), ecran.size.width - LARGEUR - 8)
        self.panneau.setFrameOrigin_((x - MARGE, icone.origin.y - HAUTEUR - ECART - MARGE))
        self.panneau.makeKeyAndOrderFront_(None)
        self.donner_accent()
        self.pousser(self.dernier_etat())
        if self.travail:
            vieux = time.monotonic() - self.travail.derniere_complete > RELECTURE_COMPLETE
            self.travail.panneau(True)
            self.travail.lire(complet=vieux)

    @objc.python_method
    def fermer(self):
        self.panneau.orderOut_(None)
        if self.travail:
            self.travail.panneau(False)

    @objc.python_method
    def donner_accent(self):
        """Relue à chaque ouverture : si Antho change la couleur d'accent du Mac, le panneau suit sans relancer l'app."""
        if self.page_prete:
            self.page.evaluateJavaScript_completionHandler_(f"window.accent({json.dumps(accent_du_mac())})", None)

    @objc.python_method
    def message_de_la_page(self, message):
        if isinstance(message, dict) and message.get("action") == "pret":
            self.page_prete = True
            self.donner_accent()
            self.pousser(self.dernier_etat())
            return
        if isinstance(message, dict) and message.get("action") in ("reglages", "demarrage", "quitter"):
            self.message_reglages(message)
            return
        if not self.travail:
            return
        noter("message", {k: v for k, v in message.items() if k != "id"} if isinstance(message, dict) else message)
        ordre = ordres.traduire(message, self.travail.dernier_etat, self.travail.id_groupe)
        if ordre is None:
            print("message refusé", flush=True)
            return
        self.travail.ordre(*ordre)

    @objc.python_method
    def message_reglages(self, message):
        action = message["action"]
        erreur = None
        if action == "quitter":
            if self.travail:
                self.travail.arreter()
            NSApplication.sharedApplication().terminate_(None)
            return
        if action == "demarrage":
            if isinstance(message.get("on"), bool):
                try:
                    demarrage.activer() if message["on"] else demarrage.desactiver()
                except (RuntimeError, OSError) as exc:
                    erreur = str(exc) or "Lancement automatique impossible."
            else:
                erreur = "Demande invalide."
        elif "bridge_ip" in message:
            erreur = self.changer_adresse(message["bridge_ip"])
        self.repondre_reglages(erreur)

    @objc.python_method
    def changer_adresse(self, texte):
        """Rend un message d'erreur, ou None. Redémarre le fil de travail si l'adresse change."""
        adresse = reglages.adresse_valide(texte)
        if adresse is None:
            return "Adresse invalide."
        regl = reglages.charger()
        if regl is None:
            return "Réglages absents : voir le README."
        if adresse == regl["bridge_ip"]:
            return None
        regl["bridge_ip"] = adresse
        try:
            reglages.enregistrer(regl)
        except OSError:
            return "Enregistrement impossible."
        if self.travail:
            self.travail.arreter()
        self.etat_sans_bridge = None
        # Rien de provisoire poussé : la lecture complète publie son résultat.
        self.travail = Travail(regl["bridge_ip"], regl["cle"], regl["piece"], self.pousser)
        self.travail.panneau(bool(self.panneau.isVisible()))
        self.travail.lire(complet=True)
        return None

    @objc.python_method
    def repondre_reglages(self, erreur=None):
        regl = reglages.charger()
        reponse = {"bridge_ip": regl["bridge_ip"] if regl else None, "demarrage": demarrage.actif()}
        if erreur:
            reponse["erreur"] = erreur
        if self.page_prete:
            js = f"window.reglages({json.dumps(reponse, ensure_ascii=False)})"
            self.page.evaluateJavaScript_completionHandler_(js, None)

    @objc.python_method
    def pousser(self, etat):
        if etat is None or not self.page_prete:
            return
        js = f"window.recevoir({json.dumps(etat, ensure_ascii=False)})"
        self.page.evaluateJavaScript_completionHandler_(js, None)

    @objc.python_method
    def bilan(self):
        etat = self.dernier_etat()
        print(
            "panneau ouvert :", bool(self.panneau.isVisible()),
            "| page prête :", self.page_prete,
            "| connexion :", etat["connexion"] if etat else None,
            flush=True,
        )
        AppHelper.stopEventLoop()


ESSAI = "--essai" in sys.argv


VERROU = None  # gardé ouvert pendant toute la vie de l'app : le verrou tombe avec le processus


def prendre_verrou():
    """Une seule app à la fois. Rend False si une autre tient déjà le verrou."""
    global VERROU
    dossier = reglages.CHEMIN.parent
    dossier.mkdir(parents=True, exist_ok=True)
    fichier = open(dossier / "verrou", "w")
    try:
        fcntl.flock(fichier, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fichier.close()
        return False
    VERROU = fichier
    return True


def principal():
    if not ESSAI and not prendre_verrou():  # l'essai doit pouvoir tourner à côté de l'app
        print("Hue Controller tourne déjà.")
        return
    application = NSApplication.sharedApplication()
    application.setActivationPolicy_(NSApplicationActivationPolicyAccessory)  # pas d'icône dans le Dock
    app = App.alloc().init()
    application.setDelegate_(app)
    AppHelper.runEventLoop()
