#!/bin/sh
# Installe Hue Controller sur ce Mac : prépare l'environnement, vérifie les réglages, active le lancement
# à l'ouverture de session et lance l'app. À relancer sans risque : chaque étape se refait à l'identique.
#
#   ./installer.sh
#
# Avant : copier le dossier du projet sur ce Mac, et le fichier de réglages (adresse et clé du bridge) depuis
# un Mac où l'app marche déjà, au même endroit :
#   ~/Library/Application Support/hue-controller/reglages.json
set -e
cd "$(dirname "$0")"

REGLAGES="$HOME/Library/Application Support/hue-controller/reglages.json"

if ! command -v uv >/dev/null 2>&1; then
    echo "Il manque « uv », l'outil qui installe Python et ses bibliothèques."
    echo "L'installer (voir https://docs.astral.sh/uv/), puis relancer ./installer.sh"
    exit 1
fi

echo "1/4  Préparation de l'environnement…"
uv sync --quiet

echo "2/4  Réglages…"
if [ ! -f "$REGLAGES" ]; then
    echo "     Le fichier de réglages est absent :"
    echo "       $REGLAGES"
    echo "     Le copier depuis un Mac où l'app marche (il contient l'adresse et la clé du bridge), puis relancer."
    exit 1
fi
chmod 600 "$REGLAGES"

echo "3/4  Application dans ~/Applications et lancement à l'ouverture de session…"
uv run --quiet python -c "from hue_controller import demarrage; demarrage.installer_app(); demarrage.activer()"

echo "4/4  Lancement de l'app…"
open "$HOME/Applications/Hue Controller.app"

echo "C'est prêt : l'ampoule est dans la barre de menus."
echo "Pour la rouvrir : « Hue Controller » dans Spotlight ou le Launchpad."
echo "Pour l'arrêter ou retirer le lancement automatique : la roue dentée du panneau."
