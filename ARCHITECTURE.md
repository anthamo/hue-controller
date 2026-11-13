# ARCHITECTURE : Hue Controller

Écrit après l'essai de faisabilité (`essais/panneau.py`). À lire avec `PRD.md` (quoi, pourquoi) et `DESIGN.md` (à quoi ça ressemble). `PLAN.md` découpe le travail.

## Ce que l'essai a prouvé

`uv run essais/panneau.py --essai` : une icône dans la barre de menus, un panneau accroché dessous, une page HTML dedans, un message de la page vers Python et un de Python vers la page. PyObjC pèse 31 Mo installé. La page est transparente : le fond translucide du panneau natif passe au travers, ce qui donne la direction Natif sans rien dessiner.

**Corrigé à l'usage** : le panneau standard (`NSPopover`) a un fond presque opaque et ne ressemble pas aux panneaux du système. L'app utilise à la place une fenêtre sans bord avec le fond en verre de macOS 26 (`essais/verre.py`), placée sous l'icône, qui se referme au clic ailleurs et ne prend pas la main à l'app en cours.

## Vue d'ensemble

```
   barre de menus
        |
   +----v-----------------------------+
   | app.py  (seul fichier qui parle   |      fil principal : l'interface du Mac
   | au Mac : icône, panneau, page)    |
   +----+--------------------^---------+
        | message             | recevoir(etat)
        | {action: ...}       |
   +----v--------------------+---------+
   | panneau/  index.html              |      la page : affiche l'état, envoie des gestes
   | panneau.css  panneau.js  faux.js  |
   +-----------------------------------+

   app.py --> file d'ordres --> fil de travail --> bridge.py --> bridge Hue (HTTPS local)
                                     |
                                 etat.py + couleurs.py  (fabriquent l'état que la page affiche)
```

## Les fichiers

| Fichier | Rôle | Dépend de |
| --- | --- | --- |
| `hue_controller/couleurs.py` | Conversions : couleur du bridge (xy, kelvins) vers couleur d'écran, et retour. Fonctions pures. | rien |
| `hue_controller/bridge.py` | Parle au bridge : lire une ressource, écrire sur une ressource. Ne connaît ni les pièces ni la page. | bibliothèque standard |
| `hue_controller/etat.py` | Transforme ce que le bridge renvoie en « état » : exactement ce que la page affiche. Fonctions pures. | `couleurs.py` |
| `hue_controller/reglages.py` | Lit et écrit le fichier de réglages (adresse du bridge, clé, pièce). | bibliothèque standard |
| `hue_controller/app.py` | L'icône, le panneau, la page, le fil de travail. | tout le reste, PyObjC |
| `hue_controller/panneau/` | La page : `index.html`, `panneau.css`, `panneau.js`, et `faux.js` (un faux bridge pour travailler sans les lampes). | rien |
| `tests/` | Un fichier de tests par module Python, plus `donnees/bridge.json` (une lecture réelle du bridge, figée). | `unittest` |

Règle : `app.py` est le seul fichier qui importe AppKit ou WebKit. Tout le reste se teste sans Mac et sans bridge.

## Le contrat entre la page et Python

C'est la frontière la plus importante : la page et Python peuvent être écrits séparément tant qu'ils la respectent.

**La page envoie** (`window.webkit.messageHandlers.pont.postMessage`) :

| Message | Sens | Tranche |
| --- | --- | --- |
| `{action: "pret"}` | la page est chargée, elle veut l'état | 1 |
| `{action: "scene", id}` | appliquer cette scène | 1 |
| `{action: "piece", on}` | tout allumer / tout éteindre | 1 |
| `{action: "piece", intensite}` | intensité de la pièce, 1 à 100 | 2 |
| `{action: "lampe", id, on}` | allumer / éteindre une lampe | 3 |
| `{action: "lampe", id, intensite}` | intensité d'une lampe, 1 à 100 | 3 |
| `{action: "zone", id, on}` | tout allumer / tout éteindre dans une zone (Cuisine, Salon…) | 3 |
| `{action: "lampe", id, kelvin}` | blanc (sa chaleur), dans les bornes de la lampe ; pour toute lampe qui a le blanc | 4 |
| `{action: "lampe", id, teinte, saturation}` | couleur : teinte 0 à 360 et saturation 0 à 100, toujours envoyées ensemble | 4 |
| `{action: "reglages"}` | la page ouvre les réglages : elle veut l'adresse du bridge et l'état du lancement automatique | 5 |
| `{action: "reglages", bridge_ip}` | changer l'adresse du bridge | 5 |
| `{action: "demarrage", on}` | lancer ou non l'app à l'ouverture de session | 5 |
| `{action: "quitter"}` | arrêter l'app | 5 |
| `{action: "changer_piece", nom}` | piloter une autre pièce du bridge ; elle est gardée dans les réglages et revient à la prochaine ouverture | après la tranche 5 |

**Python répond** en appelant `window.recevoir(etat)` :

```json
{
  "connexion": "ok",
  "piece": { "nom": "Salon", "on": true, "intensite": 53, "allumees": 10, "total": 11 },
  "scenes": [
    { "id": "…", "nom": "Détente", "couleurs": ["#ffc991"], "intensite": 56, "active": false }
  ],
  "lampes": [
    { "id": "…", "nom": "Plafond salon", "zone": "Salon", "on": true, "intensite": 50,
      "couleur": "#ff8041", "reglages": ["blanc", "teinte"], "mode": "teinte", "kelvin": null, "teinte": 21 }
  ]
}
```

Aux messages de réglages, Python répond par `window.reglages({"bridge_ip": "192.168.…" ou null, "demarrage": true|false, "erreur": "…" ou absent})`. La clé du bridge ne va jamais dans la page.

- `connexion` vaut `"ok"`, `"erreur"` (le bridge ne répond pas) ou `"reglages"` (pas de fichier de réglages). Hors `"ok"`, un champ `message` porte la phrase à afficher et les listes sont vides.
- Toutes les couleurs sont déjà des couleurs d'écran (`#rrggbb`). La page n'en calcule aucune, sauf pendant qu'on tire un curseur.
- `zones` : `[{"id": "…", "nom": "Salon", "allumees": 6, "total": 6}]`, une entrée par zone du bridge qui contient au moins une lampe de la pièce, dans l'ordre du bridge. `id` est celui du groupe de lampes de la zone : c'est lui qu'on commande.
- Lampe de couleur : `teinte` (0 à 360) et `saturation` (0 à 100) sont toujours donnés, calculés depuis la couleur que la lampe rapporte, quel que soit son mode. La couleur d'écran d'un couple (teinte, saturation) est celle de même teinte, à cette saturation et à pleine clarté. `kelvins` : `[mini, maxi]` pour une lampe qui a le blanc, sinon `null`.
- `pieces` : les noms de toutes les pièces du bridge, dans l'ordre du bridge. La page n'affiche le sélecteur de pièce que s'il y en a plus d'une.
- `scenes[].couleurs` : cinq au plus, triées par teinte. `lampes` : dans l'ordre des zones.
- Les noms viennent toujours du bridge.

## Décisions, et pourquoi

1. **Les couleurs se calculent en Python, pas dans la page.** Une seule source, testable. La maquette les calculait en JavaScript : ces fonctions sont portées dans `couleurs.py`.
2. **Jamais de réseau sur le fil principal.** Un appel au bridge qui traîne gèlerait le panneau. Tout ordre passe par une file, lue par un seul fil de travail ; le résultat revient sur le fil principal (`AppHelper.callAfter`).
3. **Une connexion gardée ouverte.** Chaque lecture coûtait 120 à 210 ms avec une connexion neuve, dont une bonne part pour l'ouvrir. Lire l'état demande plusieurs ressources : le fil de travail garde une connexion (`http.client`) et la rouvre une fois si elle tombe.
4. **À l'ouverture, on montre d'abord le dernier état connu, puis on corrige.** Le panneau n'attend jamais le bridge pour s'afficher. La condition de succès du PRD (« état réel en moins d'une demi-seconde ») se mesure sur la correction.
5. **Ce qui ne change pas se lit une fois.** Pièces, zones et appareils (les noms, qui est où) sont lus au lancement et relus toutes les dix minutes. À l'ouverture du panneau, puis toutes les cinq secondes tant qu'il est ouvert, et 0,6 s après chaque ordre : seulement les lampes, les scènes et le groupe.
6. **Pendant qu'on tire un curseur, seul le dernier ordre compte.** Un seul ordre en attente par cible. Un ordre par seconde vers la pièce (consigne de Hue pour un groupe). Vers une lampe : quatre par seconde, avec un fondu de 200 ms. Le bridge en accepte dix, mais les lampes ne suivent pas : les ordres s'empilent et la lampe rejoue le geste en retard (constaté à l'essai ; le bridge lui-même répond en 28 ms).
7. **La page affiche tout de suite le geste, sans attendre le bridge**, et ignore l'état reçu pour le contrôle qu'on est en train de manipuler. Sinon le curseur saute sous le doigt.
8. **La page ne peut agir que sur la pièce en cours.** Python refuse tout identifiant qui n'est pas dans le dernier état construit, et borne chaque valeur (1 à 100, 2000 à 6500, 0 à 360). Changer de pièce ne se fait que par le message `changer_piece`, avec un nom présent dans `pieces`.
9. **Réglages dans `~/Library/Application Support/hue-controller/reglages.json`**, lisible par le seul utilisateur : `bridge_ip`, `cle`, `piece` (le nom de la pièce). Hors du dépôt. Pour un second Mac : copier ce fichier. Pas d'appairage dans l'app (PRD). **Première connexion** (`appairage.py`) : la commande cherche le bridge par l'annuaire de Philips Hue (seule méthode : une requête, une réponse JSON ; pas de recherche mDNS sur le réseau local ; à défaut, `--adresse`), attend l'appui sur son bouton, obtient une clé, fait choisir la pièce et écrit ce fichier. Elle n'a pas été essayée sur un vrai bridge.
10. **Le certificat du bridge n'est pas vérifié** : il est signé par Signify, pas par une autorité connue du Mac, et tout reste sur le réseau de la maison. Amélioration possible plus tard : n'accepter que l'autorité de Signify.
11. **Travailler sans toucher aux lampes.** Ouverte dans un navigateur, la page ne trouve pas le Mac derrière elle et charge `faux.js` : un faux bridge qui répond avec un état figé et applique les gestes en mémoire. Tout le travail d'interface se fait là. Les tests Python utilisent un faux transport. **Pendant le développement, aucun ordre ne part vers les vraies lampes sans qu'on l'ait décidé** : un essai qui allume ou éteint se fait exprès, quand personne n'en est gêné dans la maison.
12. **Tests avec `unittest`**, sans dépendance de plus : `uv run python -m unittest`.
13. **Lancement** : `uv run python -m hue_controller`, depuis le dossier du projet. Pour l'ouvrir comme une autre app (Spotlight, Launchpad), `demarrage.installer_app()` crée dans `~/Applications` un lanceur « Hue Controller.app » : un dossier d'application dont le programme est un script de deux lignes qui lance cette commande. Le code n'est pas copié dedans : le lanceur pointe vers le dossier du projet. Seule l'icône y est copiée (`hue_controller/AppIcon.icns`, fabriquée par `outils/icone.py` depuis `design/icone/`) ; après un changement d'icône, refaire le lanceur.
14. **Lancement à l'ouverture de session** : un fichier `~/Library/LaunchAgents/fr.hue-controller.plist` que l'app écrit ou supprime (`demarrage.py`). Il lance `uv run` avec le chemin complet de `uv` et celui du projet. Rien d'autre n'est installé dans le système.
15. **Une seule app à la fois** : un verrou sur un fichier du dossier de réglages. Une seconde instance (lancée à la main alors que celle de l'ouverture de session tourne) s'arrête tout de suite, sinon deux ampoules apparaîtraient dans la barre.
16. **Changer l'adresse du bridge** arrête le fil de travail en cours et en démarre un neuf ; la clé ne change pas.

## Risques connus

| Risque | Parade |
| --- | --- |
| La transparence de la page repose sur un réglage non documenté de WebKit (`drawsBackground`) | Si une mise à jour de macOS le casse : fond uni de la couleur du panneau, une ligne à changer |
| Le verre (`NSGlassEffectView`) n'existe que sur macOS 26 | Repli écrit sur le flou des versions d'avant (`NSVisualEffectView`), **jamais essayé** : à vérifier sur le second Mac du foyer avant d'y installer l'app |
| Une vingtaine de scènes et une dizaine de lampes dans 360 px : le panneau défile | Accepté (DESIGN). Hauteur du panneau fixe |
| L'ombre de la fenêtre dessinait un cadre gris dans les coins arrondis | La fenêtre n'a plus d'ombre propre et dépasse le panneau de 32 px : l'ombre est celle du verre, qui s'éteint dans cette marge |
| Mode sombre de macOS | Le panneau suit l'apparence du système : le verre s'assombrit seul, la page change ses couleurs (`data-theme` posé par `panneau.js`) |
