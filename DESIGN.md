# DESIGN : Hue Controller

Direction **Natif**, retenue par Antho le 12/11/2026. Maquette de référence : `design/maquette.html` (vraies données du Séjour, tout se clique, rien n'est envoyé aux lampes). Écartées : Braise (fond sombre) et Nuancier (papier chaud, réglette).

## Direction, en cinq lignes

1. **Produit.** Un panneau sous une icône de la barre de menus, pour changer l'ambiance du Séjour sans quitter ce qu'on fait. Pour Antho, puis sa compagne.
2. **Caractère.** Neutre, familier, rapide : on dirait un réglage du Mac.
3. **Univers.** Le Centre de contrôle de macOS : panneau translucide, police du système.
4. **Où vit la couleur.** Dans ce qui vient des lampes, et nulle part ailleurs : l'échantillon d'une scène, la pastille et le curseur d'une lampe. Une couleur à l'écran est donc toujours une donnée. Seule exception : la couleur d'accent choisie dans les réglages du Mac, pour l'interrupteur allumé et l'anneau de la scène en cours.
5. **Signature.** Aucune, par choix : le panneau se fond dans le système. Ce qui le distingue, ce sont les couleurs de la maison.

## Couleurs

| Rôle | Valeur |
| --- | --- |
| Fond du panneau | le verre des panneaux de la barre de menus de macOS 26 (`NSGlassEffectView`), coins de 20 px, sans flèche ; le flou classique sur un macOS plus ancien. La page est transparente. En maquette `rgba(244,244,246,.82)` flouté |
| Texte | `#1d1d1f` |
| Texte secondaire | `#5c5c61` |
| Creux (onglets, fond du dépli, survol) | `rgba(0,0,0,.07)` |
| Relevé (onglet choisi) | `#fff` |
| Tuile de scène | `rgba(255,255,255,.62)` |
| Filets | `rgba(0,0,0,.1)` ; contour d'une pastille `rgba(0,0,0,.25)` |
| Accent (interrupteur allumé, anneau de la scène en cours) | la couleur d'accent du Mac, lue par l'app ; `#34c759` dans un navigateur |
| Interrupteur éteint | `rgba(0,0,0,.18)` |

**Mode sombre** (12/11) : le panneau suit l'apparence du Mac. Le verre s'assombrit seul ; la page prend ces valeurs :

| Rôle | Clair | Sombre |
| --- | --- | --- |
| Texte | `#1d1d1f` | `#f5f5f7` |
| Texte secondaire | `#5c5c61` | `rgba(255,255,255,.62)` |
| Creux | `rgba(0,0,0,.07)` | `rgba(255,255,255,.08)` |
| Relevé (onglet choisi) | `#fff` | `rgba(255,255,255,.24)` |
| Tuile, carte | `rgba(255,255,255,.74)` | `rgba(255,255,255,.1)` |
| Surface en avant (survol, carte ouverte, scène en cours, champ) | `#fff` | `rgba(255,255,255,.2)` |
| Voile de la carte Scène actuelle | `rgba(255,255,255,.8)` | `rgba(28,28,30,.6)` |
| Filets | `rgba(0,0,0,.1)` | `rgba(255,255,255,.12)` |
| Contours forts | `rgba(0,0,0,.25)` | `rgba(255,255,255,.3)` |
| Piste vide d'un curseur, interrupteur éteint | `rgba(0,0,0,.14)` / `rgba(0,0,0,.18)` | `rgba(255,255,255,.2)` |
| Bouton plein (Enregistrer) | fond `#1d1d1f`, texte `#fff` | fond `#f5f5f7`, texte `#1d1d1f` |

Les poignées des curseurs, le rond des interrupteurs et la pastille de la coche restent blancs dans les deux modes.

## Structure du panneau (commune aux trois pistes)

De haut en bas, dans l'ordre des gestes :

1. **En-tête** : « Séjour », une phrase d'état (« 10 lampes allumées sur 11 », « Tout est éteint »), l'interrupteur général.
2. **Intensité de la pièce** : un curseur entre deux soleils.
3. **Deux onglets** : Scènes (ouvert par défaut), Lampes.
4. **Scène actuelle** : un bloc fixe, une carte teintée aux couleurs de la scène en cours : grand échantillon, nom, et une pastille par lampe à sa couleur du moment (vide si la lampe est éteinte). Quand aucune scène n'est en cours : « Réglage manuel » si des lampes sont allumées, « Lumières éteintes » sinon (« Aucune » ne se comprenait pas). **Scènes** : les 22 tuiles sur deux colonnes (échantillon, puis nom), dans l'ordre du bridge, qui défilent. Un clic applique. Dans la liste, la scène en cours a un fond blanc, un anneau à sa propre couleur et une coche posée sur son échantillon (demande d'Antho, 12/11 ; ni gras ni coche à droite, qui coupaient les noms longs).
5. **Lampes** : rangées par zone, dans l'ordre où le bridge donne les zones (décidé par Antho le 12/11). Par zone : son nom en titre, puis **une carte par lampe** (refait le 12/11 sur un modèle fourni par Antho : la ligne compacte avec curseur et interrupteur côte à côte se lisait mal, deux gélules blanches collées quand tout est à 100 %).
   - Carte fermée, toujours dans cet ordre : un halo à la couleur de la lampe, le nom en gras et dessous son état en une ligne (« 85 % · Blanc chaud », « 60 % · Couleur », « Éteinte »), l'interrupteur. Pas de chevron (retiré à la demande d'Antho) : le fond qui blanchit au survol dit que la carte s'ouvre.
   - Un clic sur la carte (hors interrupteur) la déplie, une seule à la fois : « Luminosité », sa valeur, et le curseur sur toute la largeur. Sous Luminosité, selon la lampe (12/11) :
     - lampe de couleur : un sélecteur à deux segments, **Couleur** et **Blanc**, ouvert sur le mode en cours de la lampe. Couleur montre une **roue chromatique** (la teinte autour, la saturation du centre vers le bord) : Antho la trouve plus précise que deux curseurs. Blanc montre le curseur de **température**, du chaud au froid. Les deux réglages ne sont jamais montrés ensemble. Changer de segment n'envoie rien : c'est le premier geste sur la roue ou le curseur qui change la lampe ;
     - lampe blanche à température réglable : le curseur de température seul (libellé « Température ») ;
     - lampe à blanc fixe (« Plafond cuisine », une Hue white) : rien de plus, l'ampoule n'a pas ce réglage.
   - Le curseur d'une lampe se remplit de la couleur d'accent, comme celui de la pièce : rempli de la couleur d'une lampe blanche, il ne se voyait pas. La couleur de la lampe est portée par le halo.
6. **Réglages** : une roue dentée dans l'en-tête, entre le nom de la pièce et l'interrupteur. Elle remplace tout ce qui est sous l'en-tête par la vue Réglages ; « Terminé » en revient. Pas de pied de panneau.
   - **Bridge** : l'adresse (un champ), l'état de la connexion en une phrase (« Connecté », ou la phrase d'erreur), « Enregistrer » qui n'apparaît que si l'adresse a changé.
   - **Lancer à l'ouverture de session** : un interrupteur.
   - **Quitter Hue Controller** : un bouton, en bas, discret.

## Règles

- **Grille de 4 px** pour toutes les marges, hauteurs et espacements. Largeur du panneau : 360 px.
- **Rayons** : 20 (panneau, celui du système), 8 (carte, tuiles, creux du curseur), 6 (échantillons).
- **Un seul curseur**, dessiné sur le modèle de celui de macOS 26 : piste de 4 px remplie de la couleur d'accent, poignée blanche en gélule de 24 × 16 px, qui grossit et devient translucide quand on la tient. Le curseur de la pièce est entre un petit soleil et un grand, sans valeur chiffrée. Écartés le 12/11 : le curseur par défaut de WebKit (piste épaisse cerclée de blanc) et le vrai contrôle du Mac (poignée ronde). Conséquence : sur un macOS plus ancien, le curseur garde ce dessin.
- **Texte** : police du système. « Séjour » 20 px gras ; nom d'une lampe ou de la scène en cours en gras ; courant 13 px ; secondaire 12 px gris. **Titres de section** : 11 px, capitales, espacées, gris (repris du modèle fourni par Antho le 12/11, qui prime sur la règle « pas d'intertitre en petit gris »). Chiffres à chasse fixe (`tabular-nums`).
- **Un signe, un sens** : le fond blanc dit « scène en cours », dans la carte du haut comme dans la liste ; la pastille pleine dit « allumée, de cette couleur » ; un nom grisé dit « éteinte ».
- **Un blanc s'affiche éclairci** : 2700 K rendu tel quel paraît orange vif à l'écran.
- Pas d'infobulle au survol.
- Au survol d'une tuile de scène : le fond passe au blanc, l'échantillon grossit de 12 % avec une lueur de sa couleur.
- Pas de cadre dans un cadre, pas de couleur d'accent décorative.

## Repris de la seconde proposition (12/11)

Gardé : le titre de pièce plus grand, le curseur dans un creux, la carte de scène en cours teintée, les tuiles plus hautes et plus blanches. Écarté : les intertitres en petites capitales grises, la pastille « En diffusion », le crayon et le bouton « Dynamique », les filtres de scènes, la barre du bas (« Toutes les pièces », « Éteindre »), le pourcentage.

## Ce que je garde et ce que j'écarte de la proposition Stitch

| Gardé | Pourquoi |
| --- | --- |
| L'intensité générale en haut | C'est le geste le plus fréquent après le choix d'une scène |
| Les scènes en tuiles colorées | On reconnaît une ambiance à sa couleur avant de lire son nom |
| La ligne de lampe : pastille, nom, curseur, interrupteur | Grammaire claire |
| Le réglage de couleur qui se déplie sous la lampe | Pas de fenêtre en plus |

| Écarté | Pourquoi |
| --- | --- |
| « Philips Hue · Connecté · Bridge Pro · 8 lampes actives » | Du bruit : l'état de la connexion ne sert que quand elle casse |
| L'onglet Pièces et « Sync & Rythme » | Hors périmètre (une seule pièce) |
| « Recettes lumineuses » (Chaud, Doux, Lecture, Énergie) | Doublon : les scènes Hue Lecture, Détente, Concentration existent déjà |
| « + Créer », « Presets » par lampe | Hors périmètre, et une ligne de plus par lampe |
| Carte dans une carte dans une carte | Trois cadres pour une lampe |
| « Tout éteindre » en pied | Doublon de l'interrupteur général |
| La roue chromatique | Trop grande pour le panneau ; un curseur de teinte fait le même travail |
| Le fond violet et l'accent ambre | Tableau de bord sombre générique : ne dit rien de cette maison |

## Questions ouvertes

- 22 scènes sur deux colonnes : il faut défiler (accepté avec la disposition en tuiles).
- 7 scènes sont des blancs presque identiques à l'écran : faut-il un autre signe que la couleur pour celles-là (un pictogramme, comme dans l'app Hue) ?
- « Salle à manger - plafond » reste coupé dans la liste (nom à raccourcir dans l'app Hue, ou panneau plus large).
