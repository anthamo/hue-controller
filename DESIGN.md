# DESIGN : Hue Controller

Direction **Natif** : le panneau ressemble à un réglage du Mac. La référence, c'est la page elle-même : `open hue_controller/panneau/index.html` l'ouvre dans un navigateur sur un faux bridge (rien n'est envoyé aux lampes). `design/maquette.html` est la maquette de départ, dépassée sur plusieurs points.

## Direction, en cinq lignes

1. **Produit.** Un panneau sous une icône de la barre de menus, pour changer l'ambiance d'une pièce sans quitter ce qu'on fait.
2. **Caractère.** Neutre, familier, rapide : on dirait un réglage du Mac.
3. **Univers.** Le Centre de contrôle de macOS : panneau translucide, police du système.
4. **Où vit la couleur.** Dans ce qui vient des lampes, et nulle part ailleurs : l'échantillon d'une scène, le halo d'une lampe, la roue chromatique. Une couleur à l'écran est donc toujours une donnée. Seule exception : la couleur d'accent choisie dans les réglages du Mac, pour les interrupteurs allumés, les curseurs et l'anneau de la scène en cours.
5. **Signature.** Aucune, par choix : le panneau se fond dans le système. Ce qui le distingue, ce sont les couleurs de la maison.

## Couleurs

Le panneau suit l'apparence du Mac (clair ou sombre). Le fond est le verre des panneaux de la barre de menus de macOS 26 (`NSGlassEffectView`), coins de 20 px, sans flèche ; le flou classique sur un macOS plus ancien. La page est transparente : le verre passe au travers, et s'assombrit seul en mode sombre.

| Rôle | Clair | Sombre |
| --- | --- | --- |
| Texte | `#1d1d1f` | `#f5f5f7` |
| Texte secondaire | `#5c5c61` | `rgba(255,255,255,.62)` |
| Creux (onglets, fond du dépli, survol) | `rgba(0,0,0,.07)` | `rgba(255,255,255,.08)` |
| Relevé (onglet choisi) | `#fff` | `rgba(255,255,255,.24)` |
| Tuile, carte | `rgba(255,255,255,.74)` | `rgba(255,255,255,.1)` |
| Surface en avant (survol, carte ouverte, scène en cours, champ) | `#fff` | `rgba(255,255,255,.2)` |
| Voile de la carte Scène actuelle | `rgba(255,255,255,.8)` | `rgba(28,28,30,.6)` |
| Filets | `rgba(0,0,0,.1)` | `rgba(255,255,255,.12)` |
| Contours forts (pastilles) | `rgba(0,0,0,.25)` | `rgba(255,255,255,.3)` |
| Piste vide d'un curseur, interrupteur éteint | `rgba(0,0,0,.14)` / `rgba(0,0,0,.18)` | `rgba(255,255,255,.2)` |
| Bouton plein (Enregistrer) | fond `#1d1d1f`, texte `#fff` | fond `#f5f5f7`, texte `#1d1d1f` |
| Accent | la couleur d'accent du Mac, lue par l'app ; `#34c759` dans un navigateur | idem |

Les poignées des curseurs, le rond des interrupteurs et la pastille de la coche restent blancs dans les deux modes.

## Structure du panneau

De haut en bas, dans l'ordre des gestes :

1. **En-tête** : le nom de la pièce, une phrase d'état (« 10 lampes allumées sur 11 », « Tout est éteint »), la roue dentée des réglages, l'interrupteur général.
2. **Intensité de la pièce** : un curseur entre un petit soleil et un grand, sans valeur chiffrée.
3. **Deux onglets** : Scènes (ouvert par défaut), Lampes.
4. **Scènes.**
   - **Scène actuelle** : un bloc fixe, une carte teintée aux couleurs de la scène en cours : grand échantillon, nom, et une pastille par lampe à sa couleur du moment (vide si la lampe est éteinte). Sans scène en cours : « Réglage manuel » si des lampes sont allumées, « Lumières éteintes » sinon.
   - Dessous, toutes les scènes en tuiles sur deux colonnes (échantillon, puis nom), dans l'ordre du bridge, qui défilent. Un clic applique. La scène en cours a un fond blanc, un anneau à sa propre couleur et une coche posée sur son échantillon : ni gras ni coche à droite, qui couperaient les noms longs.
5. **Lampes** : rangées par zone, dans l'ordre où le bridge donne les zones. Par zone : son nom en titre avec « Tout éteindre » ou « Tout allumer », puis **une carte par lampe**.
   - Carte fermée, toujours dans cet ordre : un halo à la couleur de la lampe, le nom en gras et dessous son état en une ligne (« 85 % · Blanc chaud », « 60 % · Couleur », « 80 % · Blanc fixe », « Éteinte »), l'interrupteur. Pas de chevron : le fond qui blanchit au survol dit que la carte s'ouvre.
   - Un clic sur la carte (hors interrupteur) la déplie, une seule à la fois : « Luminosité », sa valeur, et le curseur sur toute la largeur. Dessous, selon la lampe :
     - lampe de couleur : un sélecteur à deux segments, **Couleur** et **Blanc**, ouvert sur le mode en cours de la lampe. Couleur montre une **roue chromatique** (la teinte autour, la saturation du centre vers le bord), plus précise que deux curseurs. Blanc montre le curseur de **température**, du chaud au froid. Jamais les deux ensemble. Changer de segment n'envoie rien : c'est le premier geste sur la roue ou le curseur qui change la lampe ;
     - lampe blanche à température réglable : le curseur « Température » seul ;
     - lampe à blanc fixe : rien de plus, l'ampoule n'a pas ce réglage.
   - **La couleur suit la luminosité.** Le halo, la roue, la piste de température et leurs repères s'assombrissent avec la luminosité de la lampe, pendant qu'on tire le curseur comme après : de toute leur clarté à 100 % jusqu'à 30 % de leur clarté à 1 %. En dessous de 30 %, la roue serait noire et illisible.
   - Le curseur d'une lampe se remplit de la couleur d'accent, comme celui de la pièce : rempli de la couleur d'une lampe blanche, il ne se verrait pas. La couleur de la lampe est portée par le halo.
6. **Pied : le choix de la pièce**, seulement si le bridge a plus d'une pièce. Une barre de 40 px en bas du panneau, séparée par un filet : un bouton avec une petite maison, le nom de la pièce en cours et un chevron. Un clic ouvre au-dessus la liste des pièces, la pièce en cours cochée ; en choisir une referme la liste et tout le panneau passe à cette pièce. La dernière pièce choisie est gardée pour la prochaine ouverture. Pas de pied dans la vue Réglages.
7. **Réglages** : la roue dentée remplace tout ce qui est sous l'en-tête par la vue Réglages ; « Terminé » en revient.
   - **Bridge** : l'adresse (un champ), l'état de la connexion en une phrase (« Connecté », ou la phrase d'erreur), « Enregistrer » qui n'apparaît que si l'adresse a changé.
   - **Lancer à l'ouverture de session** : un interrupteur.
   - **Quitter Hue Controller** : une carte cliquable de même forme, avec le pictogramme marche/arrêt (en texte seul, on le prendrait pour un libellé).
   - En bas à gauche, sur la ligne de « Terminé » : le nom de l'auteur, en texte secondaire, qui ouvre sa page GitHub.

**Le panneau se rouvre toujours sur les scènes.** À sa fermeture (clic ailleurs ou sur l'icône), il revient à l'onglet Scènes, en haut de la liste ; les réglages, la carte dépliée et la liste des pièces se referment, et une adresse tapée sans être enregistrée est oubliée. Ça se fait pendant que le panneau est caché : rien ne bouge à l'écran.

## Règles

- **Grille de 4 px** pour toutes les marges, hauteurs et espacements. Largeur du panneau : 360 px.
- **Rayons** : 20 (panneau, celui du système), 8 (cartes, tuiles, creux), 6 (échantillons).
- **Un seul curseur**, dessiné sur le modèle de celui de macOS 26 : piste de 4 px remplie de la couleur d'accent, poignée blanche en gélule de 24 × 16 px, qui grossit et devient translucide quand on la tient. Ni le curseur par défaut de WebKit (piste épaisse cerclée de blanc) ni le vrai contrôle du Mac (poignée ronde). Sur un macOS plus ancien, le curseur garde donc ce dessin.
- **Texte** : police du système. Nom de la pièce 20 px gras ; nom d'une lampe ou de la scène en cours en gras ; courant 13 px ; secondaire 12 px gris. Titres de section : 11 px, capitales espacées, gris. Chiffres à chasse fixe (`tabular-nums`).
- **Un signe, un sens** : le fond blanc dit « scène en cours », dans la carte du haut comme dans la liste ; la pastille pleine dit « allumée, de cette couleur » ; un nom grisé dit « éteinte ».
- **Un blanc s'affiche éclairci** : 2700 K rendu tel quel paraît orange vif à l'écran.
- Pas d'infobulle au survol.
- Au survol d'une tuile de scène : le fond passe au blanc, l'échantillon grossit de 12 % avec une lueur de sa couleur.
- Pas de cadre dans un cadre, pas de couleur d'accent décorative.

## Écarté, et pourquoi

| Écarté | Pourquoi |
| --- | --- |
| Une ligne d'état de connexion permanente (« Connecté · 8 lampes actives ») | Du bruit : l'état de la connexion ne sert que quand elle casse, il est dans les réglages |
| Des préréglages maison (« Chaud », « Lecture », « Énergie ») | Doublon des scènes Hue |
| Créer une scène, des préréglages par lampe | Hors périmètre (voir `PRD.md`), et une ligne de plus par lampe |
| « Tout éteindre » en pied de panneau | Doublon de l'interrupteur général |
| Une carte dans une carte | Trois cadres pour une lampe |
| Un fond sombre avec un accent de marque | Tableau de bord générique : ne dit rien des lumières de la maison |

## Questions ouvertes

- Beaucoup de scènes, et le panneau défile : accepté avec la disposition en tuiles.
- Les scènes de blancs se ressemblent à l'écran : faut-il un autre signe que la couleur (un pictogramme, comme dans l'app Hue) ?
- Un nom de lampe long est coupé : le raccourcir dans l'app Hue, ou élargir le panneau ?
