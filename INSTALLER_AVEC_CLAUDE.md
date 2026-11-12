# Installer Hue Controller avec Claude

Ouvrir [Claude Code](https://claude.com/claude-code) dans un terminal, sur le Mac où installer l'app, puis coller la consigne ci-dessous.

```text
Installe sur ce Mac l'application Hue Controller, qui met les lumières Philips Hue d'une pièce dans la barre de menus.
Dépôt : https://github.com/anthamo/hue-controller

Avance étape par étape et dis-moi ce que tu fais en une phrase à chaque fois. Parle-moi en français.

1. Vérifie le terrain : la version de macOS (`sw_vers -productVersion` ; l'app est faite pour macOS 26, préviens-moi
   si la version est plus ancienne), et la présence de `git` et de `uv`. Si `uv` manque, explique-moi ce que c'est,
   donne-moi la commande d'installation officielle (https://docs.astral.sh/uv/) et attends mon accord avant de la lancer.
2. Demande-moi où ranger le projet (propose `~/Applications-code/hue-controller` ou un dossier de mon choix), puis
   clone le dépôt à cet endroit. Ne le mets pas dans un dossier synchronisé (iCloud, Dropbox).
3. Lis `README.md` et `installer.sh` avant de lancer quoi que ce soit, et dis-moi en trois lignes ce que le script va faire.
4. Lance les tests : `uv run python -m unittest`. S'ils échouent, arrête-toi et montre-moi l'erreur.
5. Connecte l'app à mon bridge Hue. Préviens-moi AVANT de lancer la commande que je vais devoir appuyer sur le gros
   bouton rond du bridge dans les 30 secondes, et attends que je te dise que je suis à côté du bridge. Puis lance
   `uv run python -m hue_controller.appairage`. Si elle ne trouve pas le bridge, demande-moi son adresse (elle est dans
   l'app Hue du téléphone : Réglages → Mes bridges) et relance avec `--adresse`. Si elle me demande de choisir une
   pièce et que tu ne peux pas répondre à ma place, donne-moi la commande à lancer moi-même, ou relance-la avec
   `--piece "<nom>"` une fois que je t'ai dit laquelle.
6. Lance `./installer.sh` : il crée « Hue Controller » dans le dossier Applications, active le lancement à
   l'ouverture de session et ouvre l'app.
7. Vérifie : `uv run python -m hue_controller --essai` doit répondre « connexion : ok » ; « Hue Controller.app » doit
   exister dans /Applications (ou ~/Applications) ; dis-moi de regarder si l'ampoule est bien en haut à droite de l'écran.
8. Termine par un résumé : où est le projet, où est l'application, comment l'ouvrir, comment la quitter, comment la
   désinstaller (section « Désinstaller » du README).

Règles à respecter :
- La clé du bridge est un secret : ne l'affiche jamais, ne lis pas et ne copie pas le fichier
  `~/Library/Application Support/hue-controller/reglages.json` dans la conversation.
- N'allume, n'éteins et ne modifie aucune lampe pour « tester » : c'est moi qui essaierai depuis le panneau.
- N'utilise pas `sudo`. Si une étape demande plus de droits, explique-moi pourquoi et laisse-moi décider.
- Ne modifie pas le code du projet. Si quelque chose ne marche pas, montre-moi le message d'erreur exact et propose
  une cause, sans improviser un contournement.
```
