#!/bin/sh
# Installe Hue Controller sur ce Mac. À relancer sans risque : chaque étape se refait à l'identique.
#
#   ./installer.sh
#
# Ce qu'il fait : prépare l'environnement Python, connecte l'app au bridge Hue si ce n'est pas déjà fait
# (il faudra appuyer sur le bouton du bridge), crée « Hue Controller » dans le dossier Applications,
# active le lancement à l'ouverture de session, puis ouvre l'app.
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

echo "2/4  Connexion au bridge…"
if [ -f "$REGLAGES" ]; then
    echo "     Déjà connecté (réglages trouvés)."
else
    uv run --quiet python -m hue_controller.appairage
fi
chmod 600 "$REGLAGES"

echo "3/4  Application et lancement à l'ouverture de session…"
APP="$(uv run --quiet python -c "from hue_controller import demarrage; print(demarrage.installer_app()); demarrage.activer()")"

echo "4/4  Ouverture de l'app…"
open "$APP"

echo "C'est prêt : l'ampoule est dans la barre de menus, en haut à droite."
echo "Pour la rouvrir : « Hue Controller » dans Spotlight ou le Launchpad."
echo "Pour l'arrêter ou retirer le lancement automatique : la roue dentée du panneau."
