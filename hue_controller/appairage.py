"""Première connexion à un bridge Hue : obtenir une clé, choisir la pièce, écrire les réglages.

    uv run python -m hue_controller.appairage                       # cherche le bridge sur le réseau
    uv run python -m hue_controller.appairage --adresse 192.168.1.20  # si on connaît son adresse

Le bridge ne donne une clé qu'à qui appuie sur son bouton : la commande le demande, puis attend l'appui.
La clé n'est jamais affichée ; elle va dans le fichier de réglages, lisible par le seul utilisateur.
"""

import argparse
import json
import ssl
import sys
import time
import urllib.request

from . import reglages
from .bridge import Bridge, BridgeErreur

ANNUAIRE = "https://discovery.meethue.com/"  # le service de Philips Hue qui donne l'adresse locale des bridges
NOM_APP = "hue_controller#mac"
BOUTON_PAS_APPUYE = 101


class AppairageErreur(Exception):
    pass


def _requete(url, corps=None, verifier=True):
    donnees = None if corps is None else json.dumps(corps).encode()
    # Le bridge présente un certificat signé par Signify, inconnu du Mac : pas de vérification sur le réseau local.
    contexte = None if verifier else ssl._create_unverified_context()
    with urllib.request.urlopen(urllib.request.Request(url, data=donnees), timeout=5, context=contexte) as reponse:
        return json.load(reponse)


def trouver(obtenir=None):
    """Les adresses locales des bridges du réseau, d'après l'annuaire de Philips Hue."""
    obtenir = obtenir or (lambda: _requete(ANNUAIRE))
    try:
        return [b["internalipaddress"] for b in obtenir() if b.get("internalipaddress")]
    except Exception:
        raise AppairageErreur("Impossible d'interroger l'annuaire des bridges.") from None


def demander_cle(ip, poster=None):
    """La clé du bridge, ou None si son bouton n'a pas encore été appuyé."""
    poster = poster or (lambda corps: _requete(f"https://{ip}/api", corps, verifier=False))
    try:
        reponse = poster({"devicetype": NOM_APP, "generateclientkey": True})
        resultat = reponse[0]
    except Exception:
        raise AppairageErreur("Le bridge ne répond pas à cette adresse.") from None
    if "success" in resultat:
        return resultat["success"]["username"]
    if resultat.get("error", {}).get("type") == BOUTON_PAS_APPUYE:
        return None
    raise AppairageErreur("Le bridge a refusé la demande.")


def attendre_cle(ip, poster=None, essais=30, pause=time.sleep):
    for _ in range(essais):
        cle = demander_cle(ip, poster)
        if cle:
            return cle
        pause(1)
    raise AppairageErreur("Le bouton du bridge n'a pas été appuyé à temps.")


def pieces(bridge):
    return [p["metadata"]["name"] for p in bridge.lire("room")]


def choisir(question, choix, lire=input, dire=print):
    if len(choix) == 1:
        return choix[0]
    for numero, nom in enumerate(choix, 1):
        dire(f"  {numero}. {nom}")
    while True:
        reponse = lire(question).strip()
        if reponse.isdigit() and 1 <= int(reponse) <= len(choix):
            return choix[int(reponse) - 1]


def principal(argv=None, lire=input, dire=print):
    options = argparse.ArgumentParser(prog="python -m hue_controller.appairage", description="Connecter Hue Controller à un bridge Hue.")
    options.add_argument("--adresse", help="adresse du bridge sur le réseau local ; sinon elle est cherchée")
    options.add_argument("--piece", help="nom de la pièce à piloter ; sinon elle est demandée")
    arguments = options.parse_args(argv)
    try:
        if arguments.adresse:
            adresse = reglages.adresse_valide(arguments.adresse)
            if adresse is None:
                raise AppairageErreur("Adresse invalide.")
        else:
            trouves = trouver()
            if not trouves:
                raise AppairageErreur("Aucun bridge trouvé. Relancer avec --adresse suivi de son adresse.")
            dire("Bridge trouvé." if len(trouves) == 1 else "Plusieurs bridges trouvés :")
            adresse = choisir("Lequel ? ", trouves, lire, dire)
        dire("Appuie sur le gros bouton rond du bridge. J'attends 30 secondes…")
        cle = attendre_cle(adresse)
        noms = pieces(Bridge(adresse, cle))
        if not noms:
            raise AppairageErreur("Ce bridge n'a aucune pièce : en créer une dans l'app Hue.")
        if arguments.piece:
            if arguments.piece not in noms:
                raise AppairageErreur("Pièce inconnue. Pièces du bridge : " + ", ".join(noms))
            piece = arguments.piece
        else:
            dire("Quelle pièce piloter ?")
            piece = choisir("Numéro : ", noms, lire, dire)
        reglages.enregistrer({"bridge_ip": adresse, "cle": cle, "piece": piece})
    except (AppairageErreur, BridgeErreur) as erreur:
        dire(f"Échec : {erreur}")
        return 1
    dire(f"Connecté. Pièce : {piece}. Réglages écrits dans {reglages.CHEMIN}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
