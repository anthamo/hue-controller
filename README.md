# Hue Controller

Les lumières d'une pièce Philips Hue dans la barre de menus du Mac : une ampoule à côté de l'horloge, un panneau en verre dessous, les scènes et les lampes de la pièce à un clic.

Projet personnel, fait pour une maison et un bridge précis (une seule pièce, pas d'appairage dans l'app). Il est publié tel quel, avec ses documents de travail : le problème, la direction visuelle, l'architecture, le plan. Non affilié à Philips Hue ni à Signify.

Écrit en Python (PyObjC pour la barre de menus, une page HTML pour le panneau), sans Swift. Demande macOS et [uv](https://docs.astral.sh/uv/).

- `PRD.md` : le problème, la solution, ce qu'on ne traite pas.
- `DESIGN.md` : la direction visuelle (Natif) et ses règles ; maquette dans `design/maquette.html`.
- `ARCHITECTURE.md` : les fichiers, le contrat entre la page et Python, les décisions.
- `PLAN.md` : les tranches et les tâches.

## Lancer

`./installer.sh` crée « Hue Controller » dans `~/Applications` (on peut ensuite le déplacer dans le dossier Applications du Mac : il pointe vers le dossier du projet, où qu'il soit rangé) : l'app s'ouvre ensuite depuis Spotlight ou le Launchpad, comme une autre. À la main :

    uv run python -m hue_controller            # l'icône apparaît dans la barre ; Ctrl-C pour arrêter
    uv run python -m hue_controller --essai    # ouvre le panneau, dit si tout répond, s'arrête

## Réglages

L'adresse du bridge et sa clé sont dans `~/Library/Application Support/hue-controller/reglages.json`, hors du dépôt.
Pour les créer à partir du `.env` du téléphone (les valeurs ne sont pas affichées) :

    uv run python -m hue_controller.reglages --depuis ../telephone-s63/.env

Dans le panneau, la roue dentée ouvre les réglages : adresse du bridge, lancement à l'ouverture de session, Quitter.

## Installer sur un autre Mac

1. Installer `uv` (https://docs.astral.sh/uv/).
2. Copier ce dossier sur le Mac.
3. Copier `reglages.json` au même endroit que sur le premier Mac (il contient la clé du bridge : ne pas l'envoyer par un canal public).
4. Lancer `./installer.sh` : il prépare l'environnement, active le lancement à l'ouverture de session et lance l'app.

Non essayé sur un autre Mac. Le fond en verre du panneau n'existe que sur macOS 26 ; sur une version d'avant, l'app
se rabat sur le flou classique, jamais essayé non plus.

## Travailler sans toucher aux lampes

    open hue_controller/panneau/index.html     # la page sur un faux bridge
    uv run python -m unittest                  # les tests, sans réseau
    PYTHONPATH=. uv run python outils/faux_etat.py   # refaire l'état du faux bridge

## État

Les cinq tranches du plan sont écrites (12/11/2026). Ce qui reste est dans `PLAN.md` et dans les questions ouvertes de `DESIGN.md`.
