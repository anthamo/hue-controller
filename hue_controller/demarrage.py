"""Lancement à l'ouverture de session : un fichier LaunchAgent écrit ou supprimé.

On n'appelle pas `launchctl` : macOS relit le dossier à la prochaine ouverture de session, et l'app tourne déjà.
"""
import os
import plistlib
import shlex
import shutil
import tempfile
from pathlib import Path

ETIQUETTE = "fr.hue-controller"
CHEMIN = Path("~/Library/LaunchAgents/fr.hue-controller.plist").expanduser()
DOSSIER_PROJET = Path(__file__).resolve().parent.parent
ICONE = Path(__file__).resolve().parent / "AppIcon.icns"


def contenu(uv, dossier):
    # Pas de KeepAlive : quitter l'app depuis le panneau doit la fermer pour de bon.
    return plistlib.dumps(
        {
            "Label": ETIQUETTE,
            "ProgramArguments": [str(uv), "run", "--project", str(dossier), "python", "-m", "hue_controller"],
            "WorkingDirectory": str(dossier),
            "RunAtLoad": True,
        }
    )


def actif(chemin=None):
    return Path(CHEMIN if chemin is None else chemin).exists()


def activer(chemin=None, uv=None, dossier=None):
    uv = uv or shutil.which("uv")
    if not uv:
        raise RuntimeError("uv est introuvable.")
    dossier = DOSSIER_PROJET if dossier is None else dossier
    chemin = Path(CHEMIN if chemin is None else chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    # Écrit d'un coup : un plist tronqué ferait échouer le lancement à l'ouverture de session.
    fd, temporaire = tempfile.mkstemp(dir=chemin.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(contenu(uv, dossier))
        os.chmod(temporaire, 0o644)
        os.replace(temporaire, chemin)
    except BaseException:
        try:
            os.unlink(temporaire)
        except OSError:
            pass
        raise


def desactiver(chemin=None):
    try:
        Path(CHEMIN if chemin is None else chemin).unlink()
    except FileNotFoundError:
        pass


# --- Le lanceur : une petite application dans ~/Applications, pour ouvrir l'app depuis Spotlight ou le Launchpad ---

APP = Path("~/Applications/Hue Controller.app").expanduser()
APP_COMMUNE = Path("/Applications/Hue Controller.app")


def emplacement_app():
    """Où ranger le lanceur : s'il existe déjà, là où il est ; sinon dans le dossier Applications du Mac s'il est
    ouvert en écriture (c'est là qu'on cherche une app), à défaut dans celui du compte."""
    for app in (APP_COMMUNE, APP):
        if app.exists():
            return app
    return APP_COMMUNE if os.access(APP_COMMUNE.parent, os.W_OK) else APP


def installer_app(app=None, uv=None, dossier=None):
    """Crée (ou refait) « Hue Controller.app » : un dossier d'application dont le programme lance `uv run`.

    Sans lui, l'app n'existe que comme commande de terminal : Spotlight ne la trouve pas (essayé par Antho le 12/11/2026).
    """
    app = Path(emplacement_app() if app is None else app)
    uv = shutil.which("uv") if uv is None else uv
    if not uv:
        raise RuntimeError("uv est introuvable.")
    dossier = str(Path(__file__).resolve().parent.parent if dossier is None else dossier)
    programme = app / "Contents" / "MacOS" / "hue-controller"
    programme.parent.mkdir(parents=True, exist_ok=True)
    (app / "Contents" / "Info.plist").write_bytes(plistlib.dumps({
        "CFBundleName": "Hue Controller",
        "CFBundleDisplayName": "Hue Controller",
        "CFBundleIdentifier": ETIQUETTE,
        "CFBundleExecutable": "hue-controller",
        "CFBundlePackageType": "APPL",
        "CFBundleVersion": "1",
        "CFBundleShortVersionString": "1.0",
        "LSUIElement": True,  # pas d'icône dans le Dock : l'app vit dans la barre de menus
        "CFBundleIconFile": "AppIcon",
    }))
    # L'icône (fabriquée par outils/icone.py) est copiée dans le lanceur : Finder, Spotlight et Launchpad la lisent là.
    ressources = app / "Contents" / "Resources"
    ressources.mkdir(exist_ok=True)
    shutil.copyfile(ICONE, ressources / "AppIcon.icns")
    # Le Finder garde l'ancienne icône en cache tant que la date du dossier ne change pas.
    os.utime(app)
    # shlex.quote : le chemin du projet peut contenir des espaces.
    # `cd` d'abord : le paquet n'est pas installé, Python le trouve dans le dossier courant (sans ça : « No module named
    # hue_controller », constaté le 12/11/2026).
    programme.write_text(f"#!/bin/sh\ncd {shlex.quote(dossier)} || exit 1\nexec {shlex.quote(uv)} run python -m hue_controller\n")
    programme.chmod(0o755)
    return app
