# PLAN : Hue Controller

Écrit le 12/11/2026. Chaque tâche est faite pour être confiée telle quelle à un modèle moins coûteux : elle dit quels fichiers, quel contrat, comment vérifier. Si l'exécutant doit deviner, c'est le plan qui est en tort : il s'arrête et le dit.

## Règles pour l'exécutant

1. Lire `ARCHITECTURE.md` (le contrat) et `DESIGN.md` (les règles visuelles) avant de coder. Ne pas les modifier, ni `PRD.md`.
2. Ne faire que la tâche demandée. Pas de fichier, de fonction ou d'option en plus.
3. **Aucun appel au vrai bridge**, ni en lecture ni en écriture. Les tests passent par un faux transport, la page par `faux.js`.
4. Aucune dépendance de plus. Python : bibliothèque standard, plus PyObjC dans `app.py` seulement.
5. Noms en français, comme dans la maquette (`etat`, `lampes`, `scenes`, `intensite`). Commentaires : le pourquoi, pas le quoi.
6. Interface : reprendre le code de `design/maquette.html`, pas le réécrire. Grille de 4 px, pas de couleur hors de la table de `DESIGN.md`.
7. Finir par lancer `uv run python -m unittest` et rapporter la sortie telle quelle. Ne rien committer.

## Tranche 1 : l'icône, les ambiances, tout allumer / éteindre

| # | Tâche | Fichiers | Vérification |
| --- | --- | --- | --- |
| 1.1 | **Couleurs.** Porter de la maquette : `xy_vers_hex(x, y)`, `kelvin_vers_hex(k)` (éclairci de 45 % vers le blanc, comme `couleur()` de la maquette), `teinte_de(hex)` en degrés, `palette(couleurs)` (uniques, triées par teinte, cinq au plus, prises à intervalle régulier). | `hue_controller/couleurs.py`, `tests/test_couleurs.py` | xy (0.5, 0.4) donne un orangé ; 2700 K est plus chaud que 6500 K ; une palette de 8 couleurs en rend 5 triées ; une liste vide rend une liste vide |
| 1.2 | **Bridge.** `Bridge(ip, cle, transport=None)` avec `lire(ressource) -> list` (GET `/clip/v2/resource/<ressource>`, renvoie `data`) et `ecrire(ressource, id, corps)` (PUT). En-tête `hue-application-key`. Connexion `http.client.HTTPSConnection` gardée ouverte, certificat non vérifié, délai de 3 s, une seule nouvelle tentative si la connexion est tombée. Toute panne lève `BridgeErreur`. `transport` est une fonction `(methode, chemin, corps) -> dict` qui remplace le réseau dans les tests. | `hue_controller/bridge.py`, `tests/test_bridge.py` | avec un faux transport : `lire("light")` appelle le bon chemin ; `ecrire` envoie le bon corps ; une exception du transport devient `BridgeErreur` |
| 1.3 | **État.** `construire(brut, piece) -> dict` : `brut` est `{"room": [...], "zone": [...], "device": [...], "light": [...], "scene": [...], "grouped_light": [...]}`, le résultat est l'état décrit dans `ARCHITECTURE.md`, pour la pièce nommée `piece`. Scène active : `status.active` différent de `"inactive"`. Zone d'une lampe : la première zone qui la contient, sinon `"Autres"` ; lampes triées par zone dans l'ordre du bridge. `erreur(message)` et `sans_reglages(message)` rendent les états `"erreur"` et `"reglages"`. Pièce introuvable : état `"erreur"`. | `hue_controller/etat.py`, `tests/test_etat.py`, `tests/donnees/bridge.json` (fourni) | sur les données fournies : 11 lampes, 22 scènes, trois zones, « Plafond cuisine » sans réglage de couleur, une seule scène active au plus |
| 1.4 | **Réglages.** `charger() -> dict ou None`, `enregistrer(reglages)` (fichier en mode 600, dossier créé au besoin), `CHEMIN`. Une commande `python -m hue_controller.reglages --depuis <fichier .env>` qui lit `HUE_BRIDGE_IP` et `HUE_APP_KEY` et écrit le fichier **sans jamais afficher les valeurs**. Le chemin se remplace dans les tests. | `hue_controller/reglages.py`, `tests/test_reglages.py` | aller-retour dans un dossier temporaire ; fichier absent rend `None` ; mode du fichier = 600 |
| 1.5 | **La page.** À partir de la maquette : en-tête (nom, phrase d'état, interrupteur), tuiles des scènes. Pas d'onglets ni de curseur dans cette tranche (ils arrivent avec ce qu'ils commandent). `panneau.js` expose `window.recevoir(etat)` et envoie les messages par `envoyer(message)` ; sans `window.webkit`, il charge `faux.js`, qui répond avec un état figé et applique scène et interrupteur en mémoire. États `"erreur"` et `"reglages"` : la phrase du message à la place de la phrase d'état, contrôles désactivés. Fond de page transparent ; dans un navigateur, un fond de démonstration. | `hue_controller/panneau/index.html`, `panneau.css`, `panneau.js`, `faux.js` | ouvrir `index.html` dans un navigateur : 22 tuiles, un clic déplace l'anneau et change la phrase d'état, l'interrupteur éteint tout ; aucune erreur dans la console |
| 1.6 | **L'app.** À partir de `essais/panneau.py` : icône, panneau de 360 × 600, page chargée depuis les fichiers. Un fil de travail lit une file d'ordres ; les messages `pret`, `scene`, `piece.on` y sont posés après contrôle (identifiant connu, décision 8). Lecture de l'état au lancement, à chaque ouverture du panneau, et 0,6 s après un ordre. Le dernier état connu est renvoyé tout de suite à l'ouverture. Sans réglages : état `"reglages"`. La logique (contrôle des messages, traduction en ordres pour le bridge) est dans des fonctions sans AppKit, testées. | `hue_controller/app.py`, `hue_controller/__main__.py`, `tests/test_app.py` | tests : un message avec un identifiant inconnu est refusé ; `scene` devient `PUT scene/<id> {"recall": {"action": "active"}}` ; `piece.on` devient `PUT grouped_light/<id> {"on": {"on": …}}` |
| 1.7 | **Revue et essai réel.** Relecture du code contre ce plan et l'architecture (modèle le plus capable). Puis, avec le oui d'Antho : copier les réglages, lancer, cliquer une scène. | | Antho change d'ambiance depuis le Mac |

Ordre : 1.1 à 1.4 sont indépendantes ; 1.5 ne dépend que du contrat ; 1.6 vient en dernier.

## Tranche 2 : l'intensité de la pièce, l'état qui se rafraîchit

Limites du bridge, vérifiées le 12/11/2026 : environ 10 ordres par seconde vers une lampe, 1 par seconde vers un groupe (consigne officielle de Hue pour l'ancienne API ; reprise par des sources secondaires pour la nouvelle).

| # | Tâche | Fichiers | Vérification |
| --- | --- | --- | --- |
| 2.1 | **Ordres et cadence.** `traduire` accepte `{"action": "piece", "intensite": n}` (nombre de 1 à 100, pas un booléen ; hors bornes : refusé) et rend `("grouped_light", id_groupe, {"dimming": {"brightness": n}})`. Nouvelle classe `Cadence`, sans horloge propre : `poser(ordre)` remplace l'ordre en attente pour la même cible (même ressource, même id, mêmes clés du corps) ; `prochain(maintenant)` rend `(ordre, 0)` si un ordre peut partir, sinon `(None, secondes à attendre)` ou `(None, None)` s'il n'y a rien ; un ordre parti est noté pour sa ressource. Intervalles : 1 s pour `grouped_light`, 0,1 s pour `light`, 0 pour `scene`. Le premier ordre part tout de suite. | `hue_controller/ordres.py`, `tests/test_ordres.py` | dix intensités posées d'affilée : la première part, puis seule la dernière, une seconde après ; une scène posée entre-temps part sans attendre |
| 2.2 | **Le fil de travail suit la cadence.** `Travail` n'empile plus les écritures : il les pose dans une `Cadence` et sa boucle envoie ce qui peut partir, relit le vif 0,6 s après le dernier ordre parti (une seule relecture, pas une par ordre), et, tant que le panneau est ouvert, relit le vif toutes les 5 s. L'app lui dit quand le panneau s'ouvre et se ferme. La boucle dort jusqu'à la prochaine échéance ou jusqu'à ce qu'on la réveille (`threading.Condition`), elle ne tourne pas à vide. | `hue_controller/app.py` | `--essai` : panneau ouvert, page prête, connexion ok |
| 2.3 | **Le curseur.** Sous l'en-tête, le curseur d'intensité de la pièce et sa valeur (`.groupe` de la maquette). Désactivé quand la pièce est éteinte. Pendant le geste : la valeur affichée suit, et `envoyer({action: "piece", intensite})` à chaque mouvement. L'état reçu ne touche pas au curseur tant qu'on le tient, ni pendant 1,5 s après le dernier mouvement (décision 7). `faux.js` applique l'intensité à la pièce et aux lampes allumées. | `hue_controller/panneau/panneau.js`, `panneau.css`, `faux.js` | dans un navigateur : tirer le curseur change la valeur ; il ne saute pas quand l'état revient ; éteint, il est grisé |
| 2.4 | **Revue et essai réel**, avec le oui d'Antho. | | Antho baisse la lumière depuis le Mac |

## Tranche 3 : les onglets, les lampes une par une

Tranche 2 essayée par Antho le 12/11 ; depuis, la page a changé à sa demande (curseur sur le modèle du système, carte « Scène actuelle », scène en cours marquée dans la liste) : `DESIGN.md` fait foi.

| # | Tâche | Fichiers | Vérification |
| --- | --- | --- | --- |
| 3.1 | **Ordres pour une lampe.** `traduire` accepte `{"action": "lampe", "id": X, "on": bool}` et `{"action": "lampe", "id": X, "intensite": n}` (1 à 100, pas un booléen), X présent dans `etat_courant["lampes"]` ; rend `("light", X, {"on": {"on": bool}})` ou `("light", X, {"dimming": {"brightness": n}})`. Refusé : id inconnu, `on` et `intensite` ensemble, mauvais type, hors bornes. | `hue_controller/ordres.py`, `tests/test_ordres.py` | les cas ci-dessus ; avec `Cadence`, deux lampes différentes partent à 0,1 s d'écart |
| 3.2 | **Onglets et liste des lampes.** Sous le curseur de la pièce, deux onglets : « Scènes » (ouvert au départ : la carte Scène actuelle et les tuiles, inchangées) et « Lampes ». L'onglet choisi est gardé tant que l'app tourne. Onglet Lampes : pour chaque zone, dans l'ordre où elles arrivent dans `etat.lampes`, un titre (le nom de la zone) puis une carte qui contient ses lampes, une ligne par lampe séparée de la suivante par un filet. Une ligne, toujours dans cet ordre : pastille à la couleur de la lampe (vide si éteinte), nom (coupé par des points de suspension s'il est trop long, grisé si éteinte), curseur d'intensité, interrupteur. Le curseur d'une lampe a le dessin du curseur de la pièce, rempli de la couleur de la lampe au lieu de la couleur d'accent ; désactivé si la lampe est éteinte. Gestes : `envoyer({action: "lampe", id, on})` et `envoyer({action: "lampe", id, intensite})`, affichés tout de suite (pastille, nom grisé, phrase d'état et interrupteur général de l'en-tête recomptés). Décision 7 pour chaque curseur de lampe : les lignes sont créées une fois (tant que la liste des identifiants ne change pas) puis mises à jour en place ; un curseur tenu, ou touché depuis moins de 1,5 s, ignore l'état reçu. `faux.js` applique ces deux gestes, recompte la pièce, et une lampe changée à la main désactive la scène en cours. | `hue_controller/panneau/panneau.js`, `panneau.css`, `faux.js` | dans un navigateur : changer d'onglet ; éteindre une lampe change la phrase de l'en-tête ; un curseur de lampe tenu ne saute pas quand l'état revient ; trois titres de zone |
| 3.3 | **Revue et essai réel**, avec le oui d'Antho. | | Antho éteint une lampe et en baisse une autre depuis le Mac |

## Tranche 4 : le blanc et la couleur de chaque lampe

Tranche 3 essayée par Antho le 12/11 ; refaite à sa demande en cartes dépliables, avec « Tout éteindre » par zone. Cadence vers une lampe ramenée à quatre ordres par seconde, avec un fondu de 200 ms.

| # | Tâche | Fichiers | Vérification |
| --- | --- | --- | --- |
| 4.1 | **Conversions et état.** `couleurs.teinte_vers_hex(degres)` (teinte pleine, la même formule que `deTeinte` de la maquette) et `couleurs.hex_vers_xy(hex)` (inverse de `xy_vers_hex` : gamma sRGB inverse, puis matrice inverse « Wide RGB D65 » de Hue : X = r·0.664511 + g·0.154324 + b·0.162028 ; Y = r·0.283881 + g·0.668433 + b·0.047685 ; Z = r·0.000088 + g·0.072310 + b·0.986039 ; x = X/(X+Y+Z), y = Y/(X+Y+Z) ; noir : (0.3127, 0.3290)). Dans l'état, chaque lampe qui a « blanc » dans `reglages` reçoit `"kelvins": [mini, maxi]` (entiers, tirés de `color_temperature.mirek_schema` : mini = 1e6 / mirek_maximum, maxi = 1e6 / mirek_minimum) ; les autres `"kelvins": null`. | `hue_controller/couleurs.py`, `hue_controller/etat.py`, leurs tests | aller-retour hex → xy → hex à une unité près par canal sur six couleurs vives ; sur les données : 10 lampes avec `kelvins` (2000 à 6535), « Plafond cuisine » à `null` |
| 4.2 | **Ordres.** `traduire` accepte `{"action": "lampe", "id", "kelvin": n}` (lampe avec « blanc », n dans ses `kelvins`) → `("light", id, {"color_temperature": {"mirek": round(1e6 / n)}, "dynamics": {"duration": FONDU_MS}})`, et `{"action": "lampe", "id", "teinte": d}` (lampe avec « teinte », 0 ≤ d ≤ 360) → `("light", id, {"color": {"xy": {"x": …, "y": …}}, "dynamics": {"duration": FONDU_MS}})` avec x et y arrondis à 4 décimales. Un seul champ d'action par message. | `hue_controller/ordres.py`, `tests/test_ordres.py` | chaque cas, dont une lampe sans le réglage demandé |
| 4.3 | **La page.** Dans le dépli d'une lampe, sous Luminosité : une ligne « Blanc » et une ligne « Couleur », chacune avec son curseur sur toute la largeur, seulement pour une lampe qui a le réglage. Même dessin de curseur ; la piste de Blanc est un dégradé du chaud au froid, celle de Couleur l'arc-en-ciel des teintes (ceux de la maquette). La poignée du réglage en cours (`lampe.mode`) est remplie de la couleur de la lampe. Pendant le geste : `envoyer` à chaque mouvement ; le halo, la poignée et la ligne d'état (« · Blanc chaud », « · Couleur ») suivent tout de suite (seul endroit où la page calcule une couleur : fonctions `deTeinte` et `deBlanc` de la maquette). Désactivés si la lampe est éteinte. Décision 7 pour chacun. `faux.js` applique `kelvin` et `teinte`. | `hue_controller/panneau/panneau.js`, `panneau.css`, `faux.js` | dans un navigateur : tirer Couleur change le halo ; passer de Couleur à Blanc change la ligne d'état ; « Plafond cuisine » n'a que Luminosité |
| 4.4 | **Revue et essai réel**, avec le oui d'Antho. La justesse des couleurs se juge à l'œil. | | Antho met une lampe en bleu puis en blanc chaud depuis le Mac |

**Changé à l'essai (12/11)** : sur une lampe de couleur, Antho remplace Blanc par Saturation ; Blanc ne reste que pour une lampe blanche. La couleur est donc un couple (teinte, saturation), envoyé ensemble. `ARCHITECTURE.md` (contrat) et `DESIGN.md` font foi.

## Tranche 5 : les réglages, le lancement automatique, l'installation

| # | Tâche | Fichiers | Vérification |
| --- | --- | --- | --- |
| 5.1 | **Lancement automatique.** `demarrage.py`, sans AppKit : `CHEMIN` (`~/Library/LaunchAgents/fr.hue-controller.plist`), `contenu(uv, dossier) -> bytes` (plist : `Label`, `ProgramArguments` = [uv, "run", "--project", dossier, "python", "-m", "hue_controller"], `WorkingDirectory`, `RunAtLoad` vrai), `actif(chemin=None)`, `activer(chemin=None, uv=None, dossier=None)` (uv par défaut : `shutil.which("uv")` ; lève `RuntimeError` s'il est introuvable), `desactiver(chemin=None)`. | `hue_controller/demarrage.py`, `tests/test_demarrage.py` | dans un dossier temporaire : activer crée un plist relisible par `plistlib`, désactiver le supprime, désactiver deux fois ne plante pas |
| 5.2 | **L'app.** `reglages.adresse_valide(texte) -> str ou None` (adresse IPv4 privée ou nom d'hôte simple, espaces retirés). Dans `app.py` : les messages `reglages`, `demarrage`, `quitter` (contrat) ; `Travail.arreter()` et redémarrage quand l'adresse change ; verrou d'instance unique (décision 15). | `hue_controller/reglages.py`, `hue_controller/app.py`, tests | tests de `adresse_valide` ; `--essai` : connexion ok |
| 5.3 | **La page.** La roue dentée et la vue Réglages (DESIGN, point 6). `faux.js` simule les trois messages. | `hue_controller/panneau/panneau.js`, `panneau.css`, `faux.js` | dans un navigateur : ouvrir, changer l'adresse fait apparaître « Enregistrer », l'interrupteur bascule, « Terminé » revient |
| 5.4 | **Installer sur un autre Mac.** `installer.sh` : vérifie `uv`, prépare l'environnement, dit où copier les réglages, active le lancement automatique, lance l'app. README à jour. | `installer.sh`, `README.md` | relecture ; non essayé sur un autre Mac |
| 5.5 | **Revue et essai réel**, avec le oui d'Antho. | | |

## Reste à faire (au 13/11/2026)

Les cinq tranches sont faites. Ce qui n'a jamais été essayé en vrai :

- l'installation sur un second Mac, et l'appairage avec un bridge (il n'a tourné que sur des faux) ;
- le changement de pièce depuis le sélecteur ;
- le clic sur le lien de signature ;
- le mode sombre dans le vrai panneau ;
- le fond du panneau sur un macOS d'avant la version 26.

Ce qui reste à faire :

- l'icône de l'application ;
- écrire « Blanc fixe » sur la ligne des lampes qui n'ont que l'intensité (proposé, pas tranché) ;
- souligner le lien de signature en permanence (proposé, pas tranché).

## Qui fait quoi

| Étape | Modèle |
| --- | --- |
| Ce plan, l'architecture, `tests/donnees/bridge.json` | Fable (le plus capable) |
| Tâches 1.1 à 1.6 | Sonnet, une tâche à la fois, avec ce plan pour consigne |
| 1.7 et la revue de chaque tranche | Fable |
