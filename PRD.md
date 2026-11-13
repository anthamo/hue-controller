# PRD : les lumières dans la barre de menus du Mac

## 1. Le problème

**Quel problème.** Depuis le Mac, rien ne permet de changer l'ambiance d'une pièce ou de régler une lampe Hue. Il faut prendre son téléphone et ouvrir l'app Hue, ou se lever jusqu'à la télécommande.

**Pourquoi.**
- L'app qui le fait déjà sur Mac (Hue In The Menu) est payante.
- Le bridge Hue a une interface locale complète et documentée : lire les pièces, les lampes et les scènes, envoyer des ordres. Il n'y a pas de service à payer ni de compte à créer.

**Cible.** Une personne qui travaille sur son Mac, chez elle, avec un bridge Hue sur le même réseau.

**Condition de succès.**
- Changer d'ambiance en deux clics depuis n'importe quelle app, sans quitter ce qu'on fait.
- Le panneau s'ouvre sur l'état réel des lampes en moins d'une demi-seconde (le bridge répond en 120 à 210 ms).
- Signal d'échec : si l'on prend encore son téléphone pour les lumières quand on est devant le Mac, l'app n'a pas trouvé sa place.

## 2. La solution

**Description.** Une icône d'ampoule dans la barre de menus. Un clic ouvre un panneau accroché à l'icône. Tout se passe dans ce panneau, sans autre fenêtre. **Une pièce à la fois** : celle choisie à l'installation. Si le bridge a plusieurs pièces, un sélecteur en bas du panneau permet d'en changer, et la dernière pièce choisie est gardée. Les noms des pièces, des lampes et des scènes sont toujours lus sur le bridge, jamais écrits en dur.

```
                                   [ampoule]   son   wifi   heure
        +---------------------------------------+
        |  Salon                       ( on )   |   tout allumer / éteindre
        |  o-----------------#---------------   |   intensité de la pièce
        |                                       |
        |  [ Scènes ]   [ Lampes ]              |   deux onglets
        |                                       |
        |  +----------+ +----------+            |
        |  | Lumineux | | Détente  |            |   une tuile par scène,
        |  +----------+ +----------+            |   teintée aux couleurs de la scène
        |  +----------+ +----------+            |
        |  | Lecture  | | Veilleuse|            |
        |  +----------+ +----------+            |
        |  [maison] Salon v                     |   choix de la pièce
        +---------------------------------------+

   onglet Lampes, une carte par lampe, rangées par zone :
        |  (o) Plafond             85 % ( on )  |
        |      Luminosité  o--------#--------   |   dépliée au clic
        |      [ Couleur | Blanc ]              |   selon ce que permet la lampe
        |      roue chromatique ou température  |
```

**Ce que fait le panneau.**

| Partie | Contenu |
| --- | --- |
| En-tête | Nom de la pièce, phrase d'état (« 10 lampes allumées sur 11 »), interrupteur général, accès aux réglages |
| Pièce | Intensité de toutes les lampes de la pièce |
| Scènes | Les scènes de la pièce en tuiles ; un clic applique |
| Lampes | Rangées par zone. Allumer, éteindre, luminosité ; couleur et température du blanc pour les lampes qui les ont ; tout éteindre ou tout allumer par zone |
| Réglages | Adresse du bridge et état de la connexion, lancement à l'ouverture de session, quitter |

**Ce qu'on ne traite pas.**
- Pas d'écran d'appairage dans le panneau. Se connecter demande l'adresse du bridge et une clé, que le bridge ne donne qu'après un appui sur son bouton : c'est la commande d'installation qui s'en charge, une fois. Ensuite, les réglages montrent l'adresse (modifiable) et l'état de la connexion.
- Pas de création ni de modification de scène : ça reste dans l'app Hue.
- Pas d'automatisation, d'horaires ni de capteurs.
- Pas d'effets (bougie, scènes dynamiques).
- Pas d'accès hors de la maison : tout passe par le réseau local.
- Pas de distribution signée (ni Mac App Store, ni app notarisée) : l'app s'installe depuis le code source.
- Pas de photos sur les tuiles comme dans l'app Hue : le bridge ne donne qu'une référence d'image. La tuile prend les couleurs de la scène, qu'il donne.

**Proposition de valeur.** Les lumières à un clic du travail en cours, avec une app qui tient en quelques fichiers qu'on peut lire et changer.

## 3. Décisions

| # | Question | Décision |
| --- | --- | --- |
| 1 | Technique | Python (PyObjC) pour l'icône et le panneau, l'intérieur du panneau en HTML/CSS. Pas de Swift. Détail dans `ARCHITECTURE.md`. |
| 2 | Pièces | Une pièce à la fois, toutes ses scènes affichées. Les zones (Cuisine, Salon…) servent à ranger les lampes, pas à changer de pièce. |
| 3 | Direction visuelle | Natif : le panneau ressemble à un réglage du Mac. Règles dans `DESIGN.md`. |
| 4 | Installation | Une commande, qui fait aussi l'appairage. Les réglages (adresse, clé, pièce) vivent hors du dossier du projet ; pour un second Mac, on peut copier ce fichier. |

## Ce que donne le bridge

- Chaque lampe annonce ce qu'elle sait faire : intensité seule (une ampoule « white »), intensité et température du blanc, ou intensité, température et couleur. Le panneau ne montre que les réglages qu'elle a.
- Les couleurs de chaque scène se lisent sur le bridge : elles servent à teinter les tuiles.
- Plusieurs scènes sont des blancs (Lumineux, Lecture, Détente…) : leurs couleurs se ressemblent, seul le nom les distingue.
