"""Réglages de l'app (adresse du bridge, clé, pièce), hors du dépôt."""
import argparse
import ipaddress
import json
import os
import re
import sys
import tempfile
from pathlib import Path

CHEMIN = Path("~/Library/Application Support/hue-controller/reglages.json").expanduser()


_NOM_HOTE = re.compile(r"[A-Za-z0-9.-]{1,253}")


def adresse_valide(texte):
    """Rend l'adresse nettoyée si c'est une IPv4 privée ou un nom d'hôte simple, sinon None."""
    if not isinstance(texte, str):
        return None
    texte = texte.strip()
    try:
        ip = ipaddress.ip_address(texte)
    except ValueError:
        # Pas une IP : un nom simple. Les chiffres et points seuls (ex. 300.1.1.1) ne sont pas un nom.
        if _NOM_HOTE.fullmatch(texte) and not re.fullmatch(r"[0-9.]+", texte):
            return texte
        return None
    if ip.version == 4 and ip.is_private and not ip.is_loopback and not ip.is_multicast:
        return texte
    return None


def charger(chemin=None):
    """Rend les réglages, ou None si le fichier manque ou est illisible."""
    chemin = CHEMIN if chemin is None else chemin
    try:
        brut = json.loads(Path(chemin).read_text(encoding="utf-8"))
        return {
            "bridge_ip": brut["bridge_ip"],
            "cle": brut["cle"],
            # Sans pièce, l'état prend la première du bridge (etat.construire).
            "piece": brut.get("piece") or None,
        }
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def enregistrer(reglages, chemin=None):
    """Écrit d'un coup : un fichier partiel ne doit jamais prendre la place du bon."""
    chemin = Path(CHEMIN if chemin is None else chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    # mkstemp crée déjà le fichier en 600 ; on le refixe par prudence.
    fd, temporaire = tempfile.mkstemp(dir=chemin.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(reglages, f, ensure_ascii=False, indent=2)
        os.chmod(temporaire, 0o600)
        os.replace(temporaire, chemin)
    except BaseException:
        try:
            os.unlink(temporaire)
        except OSError:
            pass
        raise


def lire_env(fichier):
    """Lit les lignes NOM=valeur d'un .env, guillemets retirés."""
    valeurs = {}
    for ligne in Path(fichier).read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        nom, valeur = ligne.split("=", 1)
        nom = nom.strip()
        if nom.startswith("export "):
            nom = nom[len("export "):].strip()
        valeur = valeur.strip()
        if len(valeur) >= 2 and valeur[0] == valeur[-1] and valeur[0] in "\"'":
            valeur = valeur[1:-1]
        valeurs[nom] = valeur
    return valeurs


def principal(argv=None, chemin=None):
    parseur = argparse.ArgumentParser(prog="python -m hue_controller.reglages")
    parseur.add_argument("--depuis", required=True, help="fichier .env à lire")
    args = parseur.parse_args(argv)
    chemin = CHEMIN if chemin is None else chemin
    try:
        valeurs = lire_env(args.depuis)
    except (OSError, ValueError):
        # Pas de détail de l'exception : elle pourrait citer le contenu.
        print("Impossible de lire le fichier indiqué.", file=sys.stderr)
        return 1
    for nom in ("HUE_BRIDGE_IP", "HUE_APP_KEY"):
        if not valeurs.get(nom):
            print(f"Variable absente ou vide : {nom}", file=sys.stderr)
            return 1
    enregistrer(
        {
            "bridge_ip": valeurs["HUE_BRIDGE_IP"],
            "cle": valeurs["HUE_APP_KEY"],
            "piece": None,
        },
        chemin,
    )
    print(f"Réglages écrits dans {chemin}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
