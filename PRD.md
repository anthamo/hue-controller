# PRD : les lumières dans la barre de menus du Mac

Brouillon du 12/11/2026, à valider par Antho. Dossier : `hue-controller` (nom choisi par Antho).

Les lignes marquées **[à confirmer]** sont des propositions de ma part, pas des choses qu'Antho a dites.

## 1. Le problème

**Quel problème.** Depuis le Mac, Antho n'a rien pour changer l'ambiance ou régler une lampe. Aujourd'hui il doit retrouver son téléphone et ouvrir l'app Hue, ou se lever pour prendre la télécommande Hue (dit par Antho, 12/11).

**Pourquoi vrai et pourquoi maintenant.**
- L'app qui fait ça (Hue In The Menu) est payante.
- Le plus dur est déjà fait dans le projet du téléphone : la clé du bridge existe, `hue.py` sait lire les scènes et les lancer.
- Second objectif, dit par Antho : dérouler un projet court avec une méthode propre (PRD, architecture, plan, puis code confié à un modèle moins coûteux) pour voir ce que ça donne.

**Cible.** Antho, sur son Mac, à la maison. Personne d'autre.

**Condition de succès.**
- Changer d'ambiance en deux clics depuis n'importe quelle app, sans quitter ce qu'il fait.
- Le panneau s'ouvre avec l'état réel des lampes en moins d'une demi-seconde (le bridge répond en 120 à 210 ms, mesuré le 12/11).
- Signal d'arrêt (validé par Antho) : si après deux semaines Antho prend encore l'iPhone pour les lumières quand il est devant le Mac, l'app n'a pas trouvé sa place et on n'y ajoute rien.

## 2. La solution

**Description.** Une icône d'ampoule dans la barre de menus. Un clic ouvre un panneau accroché à l'icône. Tout se passe dans ce panneau : aucune fenêtre à part. **Une seule pièce : le Séjour** (11 lampes, 22 scènes). Pas de sélecteur de pièce, pas de zones, pas la chambre (décidé par Antho, 12/11). Les noms des lampes et des scènes sont relus sur le bridge, jamais écrits en dur.

```
                                   [ampoule]   son   wifi   heure
        +---------------------------------------+
        |  Séjour                      ( on )   |   tout allumer / éteindre               
        |  o-----------------#---------------   |   intensité du groupe
        |                                       |
        |  [ Ambiances ]   [ Lampes ]           |   deux onglets
        |                                       |
        |  +----------+ +----------+ +--------+ |
        |  | Lumineux | | Détente  | | Repas  | |   une tuile par scène,
        |  +----------+ +----------+ +--------+ |   teintée aux couleurs de la scène
        |  +----------+ +----------+ +--------+ |
        |  | Lecture  | | Veilleuse| |  ...   | |
        |  +----------+ +----------+ +--------+ |
        +---------------------------------------+

   onglet Lampes :
        |  Plafond salon               ( on )   |
        |  o-----------#------------------      |   intensité
        |  blanc chaud o------#------- froid    |   seulement si la lampe le permet
        |  [ couleur ]                          |   seulement si la lampe le permet
```

**Ce que fait le panneau, par tranches.** Chaque tranche se livre seule et sert telle quelle.

| Tranche | Contenu |
| --- | --- |
| 1 | L'icône, le panneau, les scènes du Séjour en tuiles, tout allumer / tout éteindre |
| 2 | L'intensité du groupe ; l'état réel relu à chaque ouverture |
| 3 | L'onglet Lampes : allumer / éteindre et intensité de chaque lampe |
| 4 | Température de blanc et couleur par lampe, pour celles qui les ont |
| 5 | Réglages dans le panneau : adresse du bridge, état de la connexion, lancement à l'ouverture de session |

**Ce qu'on ne traite pas.**
- Pas d'appairage dans l'app. Se connecter demande deux choses : l'adresse du bridge et une clé, que le bridge ne donne qu'après un appui sur son bouton. La clé existe déjà : elle va dans un fichier de réglages hors dépôt. Les réglages montrent l'adresse (modifiable) et l'état de la connexion (demande d'Antho).
- Pas de création ni de modification de scène : ça reste dans l'app Hue.
- Pas d'automatisation, d'horaires, de capteurs.
- Pas d'effets (bougie, scènes dynamiques) pour le moment (Antho, 12/11).
- Pas d'accès hors de la maison.
- Pas de distribution (ni signature, ni installeur, ni Mac App Store).
- Pas de photos sur les tuiles comme dans l'app Hue : le bridge ne donne qu'une référence d'image. La tuile prend les couleurs de la scène (présentes dans la réponse du bridge ; à vérifier sur pièce).

**Proposition de valeur.** Les lumières à un clic du travail en cours, avec une app qui tient en quelques fichiers et qu'Antho peut lire et changer.

**Rollout.** Sur un seul Mac. Tranche 1 utilisée quelques jours avant d'écrire la 2. Chaque essai qui allume ou éteint de vraies lampes se fait avec le oui d'Antho juste avant.
Ensuite, si l'app sert : l'installer sur un second Mac du foyer (MacBook M1) (souhait d'Antho). Conséquence pour l'architecture : l'installation doit tenir en une commande, et la clé se copie d'un Mac à l'autre avec le fichier de réglages.

## 3. Décisions

| # | Question | Décision |
| --- | --- | --- |
| 1 | Technique, sans Swift | Python (PyObjC) pour l'icône et le panneau, l'intérieur du panneau en HTML/CSS. Prouvé le 12/11 par `essais/panneau.py`. Détail dans `ARCHITECTURE.md`. |
| 2 | Pièces | Le Séjour seul, ses 22 scènes toutes affichées. |
| 3 | Direction visuelle | Natif (comme un réglage du Mac), retenue le 12/11. Règles dans `DESIGN.md`, maquette dans `design/maquette.html`. |
| 4 | Nom et dépôt | `hue-controller`. Dépôt GitHub privé à créer (aujourd'hui le dossier est sauvegardé par le vault). |

## Annexes

**Ce que le bridge contient (lu le 12/11/2026, lecture seule).**

| Groupe              | Type  | Lampes | Scènes |
| ------------------- | ----- | ------ | ------ |
| Séjour              | pièce | 11     | 22     |

- 10 lampes du Séjour ont intensité, température de blanc et couleur. « Plafond cuisine » n'a que l'intensité.
- 7 des 22 scènes sont des blancs (Lumineux, Lecture, Détente...) : leurs couleurs se ressemblent, seul le nom les distingue.
- Les couleurs de chaque scène se lisent bien sur le bridge (vérifié le 12/11) : elles servent à teinter les tuiles.

**Ce que le Mac a déjà (vérifié le 12/11/2026).** Python 3.12, `uv`, Node, les outils en ligne de commande d'Apple. Ni PyObjC ni rumps installés.

**Qui fait quoi (méthode).**

| Étape | Livrable | Modèle |
| --- | --- | --- |
| 1. PRD | ce fichier, validé par Antho | le plus capable |
| 2. Essai de faisabilité | trente lignes : une icône, un panneau, une page | le plus capable |
| 3. Architecture + plan | `ARCHITECTURE.md` et `PLAN.md` : fichiers, contrats entre eux, tâches assez précises pour être exécutées sans deviner | le plus capable |
| 4. Code, tranche par tranche | le code et ses tests | un modèle moins coûteux, à qui on donne le plan |
| 5. Revue | relecture du code contre le plan, puis essai par Antho | le plus capable |
