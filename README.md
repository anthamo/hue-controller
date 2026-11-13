# Hue Controller

Les lumières d'une pièce Philips Hue dans la barre de menus du Mac.

Une ampoule à côté de l'horloge. Un clic ouvre un panneau : les scènes de la pièce, l'intensité, chaque lampe avec sa luminosité, sa couleur et sa température de blanc. Pas besoin de chercher son téléphone.

Application créée par [Anthony Hamo](https://github.com/anthamo). Projet personnel, non affilié à Philips Hue ni à Signify.

## Ce qu'elle fait

- **Scènes** : toutes les scènes de la pièce, en un clic, avec la scène en cours en tête.
- **Pièce** : tout allumer, tout éteindre, régler l'intensité.
- **Lampes** : rangées par zone. Pour chacune : allumer, éteindre, luminosité, couleur sur une roue chromatique, température du blanc. « Tout éteindre » par zone.
- **Réglages** : adresse du bridge, lancement à l'ouverture de session, quitter.
- Suit le mode clair ou sombre du Mac et sa couleur d'accent.

Elle pilote **une seule pièce**, choisie à l'installation.

## Ce qu'il faut

- Un Mac sous macOS 26 (le panneau en verre vient de cette version ; sur une version plus ancienne, un repli existe mais n'a jamais été essayé).
- Un bridge Philips Hue sur le même réseau que le Mac.
- [uv](https://docs.astral.sh/uv/), l'outil qui installe Python et ses bibliothèques.

## Installer

```sh
git clone https://github.com/anthamo/hue-controller.git
cd hue-controller
./installer.sh
```

Le script fait quatre choses :

1. il prépare l'environnement Python ;
2. il connecte l'app au bridge : il le cherche sur le réseau, demande d'**appuyer sur le gros bouton du bridge**, puis fait choisir la pièce ;
3. il crée « Hue Controller » dans le dossier Applications et active le lancement à l'ouverture de session ;
4. il ouvre l'app.

L'ampoule apparaît dans la barre de menus. Ensuite, l'app s'ouvre comme une autre : « Hue Controller » dans Spotlight ou le Launchpad.

**Installer avec Claude.** Le fichier [INSTALLER_AVEC_CLAUDE.md](INSTALLER_AVEC_CLAUDE.md) contient une consigne à coller dans Claude Code : il fait l'installation pas à pas et vérifie que tout marche.

## En cas de souci

| Symptôme | Quoi faire |
| --- | --- |
| « Aucun bridge trouvé » | Relancer la connexion avec l'adresse du bridge (elle est dans l'app Hue : Réglages → Mes bridges) : `uv run python -m hue_controller.appairage --adresse 192.168.x.x` |
| « Le bouton du bridge n'a pas été appuyé à temps » | Relancer `./installer.sh` et appuyer sur le bouton dans les 30 secondes |
| « Le bridge ne répond pas » dans le panneau | Le bridge a peut-être changé d'adresse : la corriger dans les réglages du panneau (la roue dentée) |
| Changer de pièce, ou repartir de zéro | Supprimer `~/Library/Application Support/hue-controller/reglages.json`, puis relancer `./installer.sh` |
| L'app ne s'ouvre plus après avoir déplacé son dossier | Relancer `./installer.sh` depuis le nouvel emplacement |

## Désinstaller

Dans le panneau, roue dentée : couper « Lancer à l'ouverture de session », puis « Quitter ». Supprimer ensuite « Hue Controller » du dossier Applications, le dossier du projet, et `~/Library/Application Support/hue-controller`.

## Où sont les réglages

L'adresse du bridge, sa clé et le nom de la pièce sont dans `~/Library/Application Support/hue-controller/reglages.json`, hors du dossier du projet, lisibles par le seul utilisateur. La clé donne le contrôle des lampes : ne pas la partager.

Pour chercher le bridge, l'installation interroge une fois l'annuaire de Philips Hue (`discovery.meethue.com`). Ensuite, tout reste sur le réseau de la maison.

## Pour qui veut lire ou modifier le code

L'app est en Python : PyObjC pour la barre de menus et la fenêtre, une page HTML pour l'intérieur du panneau. Pas de Swift.

```sh
uv run python -m hue_controller            # lancer depuis le dossier du projet ; Ctrl-C pour arrêter
uv run python -m hue_controller --essai    # ouvre le panneau, dit si tout répond, s'arrête
uv run python -m hue_controller --journal  # écrit chaque ordre envoyé au bridge, avec sa durée
uv run python -m unittest                  # les tests, sans réseau
open hue_controller/panneau/index.html     # la page seule, sur un faux bridge : rien n'est envoyé aux lampes
```

Les documents de travail racontent comment le projet a été pensé et construit :

- [PRD.md](PRD.md) : le problème, la solution, ce qu'on ne traite pas ;
- [DESIGN.md](DESIGN.md) : la direction visuelle et ses règles ; la maquette est dans `design/maquette.html` ;
- [ARCHITECTURE.md](ARCHITECTURE.md) : les fichiers, le contrat entre la page et Python, les décisions ;
- [PLAN.md](PLAN.md) : le découpage en tranches et en tâches.

Limites connues : une seule pièce ; pas de création de scène ; pas d'effets ; la roue chromatique ne se règle pas au clavier ; installation jamais essayée sur un second Mac.

## Licence

[MIT](LICENSE) : libre de l'utiliser, de le modifier et de le redistribuer, sans garantie.
