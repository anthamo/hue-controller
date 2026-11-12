"""Logique de l'app sans AppKit : lire les ressources du bridge, contrôler et traduire les messages de la page."""

from . import couleurs

FONDU_MS = 200  # durée du fondu d'une lampe vers sa nouvelle intensité : court, pour qu'elle suive le curseur
RESSOURCES_FIXES = ("room", "zone", "device")
RESSOURCES_VIVES = ("light", "scene", "grouped_light")


def lire_tout(bridge):
    return {r: bridge.lire(r) for r in RESSOURCES_FIXES + RESSOURCES_VIVES}


def lire_vif(bridge, brut):
    """Relit seulement ce qui bouge ; les noms et les zones restent ceux de `brut`."""
    nouveau = {r: brut[r] for r in RESSOURCES_FIXES}
    for r in RESSOURCES_VIVES:
        nouveau[r] = bridge.lire(r)
    return nouveau


def groupe_de(brut, piece):
    for salle in brut.get("room", []):
        if salle.get("metadata", {}).get("name") == piece:
            for s in salle.get("services", []):
                if s.get("rtype") == "grouped_light":
                    return s.get("rid")
    return None


def traduire(message, etat_courant, id_groupe):
    """Contrôle un message de la page (décision 8) : rend (ressource, id, corps) ou None s'il est refusé."""
    if not isinstance(message, dict):
        return None
    if not isinstance(etat_courant, dict) or etat_courant.get("connexion") != "ok":
        return None
    action = message.get("action")
    if action == "scene":
        identifiant = message.get("id")
        connues = {s["id"] for s in etat_courant.get("scenes", [])}
        if isinstance(identifiant, str) and identifiant in connues:
            return ("scene", identifiant, {"recall": {"action": "active"}})
    elif action == "piece":
        if not id_groupe:
            return None
        on, intensite = message.get("on"), message.get("intensite")
        if "on" in message and "intensite" in message:
            return None
        if isinstance(on, bool):
            return ("grouped_light", id_groupe, {"on": {"on": on}})
        if isinstance(intensite, (int, float)) and not isinstance(intensite, bool) and 1 <= intensite <= 100:
            return ("grouped_light", id_groupe, {"dimming": {"brightness": intensite}})
    elif action == "lampe":
        identifiant = message.get("id")
        lampe = next((x for x in etat_courant.get("lampes", []) if isinstance(x, dict) and x.get("id") == identifiant), None)
        if not isinstance(identifiant, str) or lampe is None:
            return None
        champs = [c for c in ("on", "intensite", "kelvin", "teinte", "saturation") if c in message]
        reglages = lampe.get("reglages") or []

        def nombre(v):
            return isinstance(v, (int, float)) and not isinstance(v, bool)

        if champs == ["teinte", "saturation"]:
            teinte, saturation = message["teinte"], message["saturation"]
            if "teinte" in reglages and nombre(teinte) and nombre(saturation) and 0 <= teinte <= 360 and 0 <= saturation <= 100:
                x, y = couleurs.hex_vers_xy(couleurs.couleur_de(teinte, saturation))
                return ("light", identifiant, {"color": {"xy": {"x": round(x, 4), "y": round(y, 4)}}, "dynamics": {"duration": FONDU_MS}})
            return None
        if len(champs) != 1:
            return None
        champ, valeur = champs[0], message[champs[0]]
        if champ == "on":
            if isinstance(valeur, bool):
                return ("light", identifiant, {"on": {"on": valeur}})
            return None
        if not nombre(valeur):
            return None
        if champ == "intensite" and 1 <= valeur <= 100:
            return ("light", identifiant, {"dimming": {"brightness": valeur}, "dynamics": {"duration": FONDU_MS}})
        if champ == "kelvin":
            kelvins = lampe.get("kelvins")
            # Le blanc en kelvins est réservé aux lampes blanches : une lampe de couleur règle teinte et saturation
            # (tranché par Antho le 12/11).
            if "blanc" in reglages and "teinte" not in reglages and kelvins and kelvins[0] <= valeur <= kelvins[1]:
                return ("light", identifiant, {"color_temperature": {"mirek": round(1e6 / valeur)}, "dynamics": {"duration": FONDU_MS}})
    elif action == "zone":
        identifiant, on = message.get("id"), message.get("on")
        connues = {z.get("id") for z in etat_courant.get("zones", []) if isinstance(z, dict)}
        if set(message) != {"action", "id", "on"}:
            return None
        if isinstance(identifiant, str) and identifiant in connues and isinstance(on, bool):
            return ("grouped_light", identifiant, {"on": {"on": on}})
    return None


class Cadence:
    """Les ordres en attente, et à quel moment chacun peut partir. Sans horloge : l'heure est passée en argument."""

    # Lampes : le bridge accepte 10 ordres par seconde, mais les lampes (radio Zigbee) ne suivent pas : les ordres
    # s'empilent et la lampe rejoue le geste avec du retard (vu par Antho le 12/11/2026). Quatre par seconde au plus.
    INTERVALLES = {"grouped_light": 1.0, "light": 0.25, "scene": 0.0}

    def __init__(self):
        self._attente = {}  # cible -> ordre ; un dict garde l'ordre d'arrivée, même quand une valeur est remplacée
        self._parti = {}  # ressource -> heure du dernier départ

    def poser(self, ordre):
        ressource, identifiant, corps = ordre
        self._attente[(ressource, identifiant, tuple(sorted(corps)))] = ordre

    def prochain(self, maintenant):
        plus_courte = None
        for cible, ordre in self._attente.items():
            ressource = cible[0]
            dernier = self._parti.get(ressource)
            reste = 0 if dernier is None else self.INTERVALLES.get(ressource, 0) - (maintenant - dernier)
            if reste <= 0:
                del self._attente[cible]
                self._parti[ressource] = maintenant
                return ordre, 0
            if plus_courte is None or reste < plus_courte:
                plus_courte = reste
        return None, plus_courte

    def vide(self):
        return not self._attente
