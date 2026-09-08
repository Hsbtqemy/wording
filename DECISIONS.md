# Paysage — journal des décisions

Ce document existe pour une raison précise : **les constantes de ce projet ont
l'air arbitraires.** Sans les raisons, elles seront « nettoyées » au premier
refactor. Chaque entrée dit ce qui casse si on revient dessus.

Le code Python n'est pas le livrable. C'est la spécification exécutable et le
banc d'essai. Le livrable est un add-in Word en JavaScript.

---

## 1. Ce qui compte comme progression

**Décidé :** l'unité est le paragraphe, pas le mot.

Le mot ne veut rien dire et se triche seul. La page est trop lente pour donner
du retour. Le paragraphe correspond à une unité de pensée réelle, et Word
l'expose nativement via `onParagraphAdded` / `onParagraphChanged` (WordApi 1.6).

**Décidé :** rien ne fane jamais.

Une croissance qui ralentit, jamais qui recule. La punition fonctionne mal chez
quelqu'un qui écrit déjà avec de la culpabilité.

---

## 2. Deux axes, pas un

**Décidé :** étendre et mûrir sont deux variables visuelles distinctes.

- **Extension** — un paragraphe nouveau : la forme pousse.
- **Maturité** — un paragraphe repris : la forme s'épaissit et se garnit.

C'est la décision centrale du projet. Elle résout sans compromis le problème de
la réécriture en boucle : reprendre quarante fois la même phrase produit un
élément somptueux sur une forme qui n'a pas grandi. Description exacte, sans
récompense truquée ni punition. Et l'exploit disparaît — on ne peut pas simuler
de la croissance en tripotant, parce que tripoter produit un autre effet.

Saturation de la maturité : `1 - exp(-reprises/3)`, plafonnée vers 5–6 passages.

**Décidé :** un paragraphe est *en construction* jusqu'à ce que le curseur le
quitte. Après, y revenir est une reprise — **une par visite, pas une par
frappe.**

Sans cette règle, les deux axes ne sont pas séparables. Dans Word, écrire un
paragraphe pour la première fois et y revenir trois jours plus tard produisent
la même suite d'événements : `onParagraphChanged`, N fois. Les deux lectures
possibles cassent chacune quelque chose :

- tout lire comme des reprises → la première rédaction ne fait **jamais**
  pousser la forme, tout est maturité ;
- tout lire comme de l'écriture → allonger indéfiniment un paragraphe fait
  pousser la plante, et l'exploit que ce point ferme est rouvert.

La séparation juste n'est pas dans le texte, elle est dans le **curseur**. Et le
comptage par visite est nécessaire aussi : à un tick de 2 s, dix minutes de
réécriture compteraient trois cents passages là où la saturation en attend cinq.

⚠️ Fusionner les deux axes en un seul paramètre « intensité » est l'erreur que
j'ai commise à la v1 de la grammaire. Elle rend le test des planches
non concluant et vide le design de son intérêt.

---

## 3. Le registre d'empreintes

**Décidé :** on compte les empreintes de paragraphes distinctes jamais vues,
pas les mots présents dans un fichier.

Hachage du paragraphe normalisé (casse, espaces, ponctuation faible ignorées).
Un seul mécanisme règle quatre cas d'un coup :

| Action | Effet | Correct ? |
|---|---|---|
| Déplacer d'un fichier à l'autre | rien | oui, rien n'a été écrit |
| Copier-coller interne | rien | oui |
| Fusionner 12 chapitres | rien | oui |
| Supprimer | **rien** | oui — le texte coupé a été écrit |

⚠️ La suppression qui ne retire rien est un choix, pas un oubli. Les 20 000 mots
coupés d'une thèse ont été écrits. Tous les compteurs punissent de couper ;
celui-ci non.

Coût : 17 Ko pour 1 450 paragraphes, 59 Ko avec trois fois plus de reprises.

### Une exception, trouvée en simulant Word

La reconnaissance existe pour rendre un **déplacement** gratuit. Elle ne doit
pas pouvoir nier une frappe — et elle le pouvait.

Un paragraphe qu'on tape passe par tous ses états intermédiaires, et chacun
entre au registre : après « Il faut donc admettre », le registre contient ce
début. Or en français un paragraphe sur deux commence par les mêmes quatre
mots. Le suivant était donc déclaré `connue`, ne comptait pas, et **le plant
cessait de pousser au milieu d'une page**, sans que rien ne le signale.

`absorber()` prend donc un drapeau `naissance` : l'appelant qui a **vu** le
paragraphe naître vide sous le curseur sait ce que le registre ne peut pas
savoir. C'est le pont qui le tient, parce que c'est lui qui a vu.

Le même endroit a livré un second défaut : Word crée un paragraphe **vide** à
chaque retour à la ligne. Sans filtre, l'empreinte du vide entrait au registre
au premier `Entrée`, et tous les suivants étaient `connue` — le plant cessait de
pousser au deuxième paragraphe. `rattacher()` filtrait déjà le vide ;
`absorber()` non. Les deux portes d'entrée disent maintenant la même chose.

⚠️ Aucun des deux n'était visible sur le banc : le corpus n'émet ni paragraphe
vide, ni frappe progressive. Ils ne sont apparus qu'en rejouant les **suites
d'événements** que Word produit réellement.

---

## 4. Le collage

**Décidé :** ordre de vérification strict.

```
1. empreinte déjà connue          -> rien       (déplacement, merge, copie)
2. inconnue + arrivée progressive -> écriture   (ça pousse)
3. inconnue + arrivée instantanée -> greffe     (en attente)
4. greffe ensuite retouchée       -> écriture   (ça pousse à ce moment-là)
```

⚠️ Le registre **doit** passer avant le test de vitesse. Sinon la fusion des
chapitres dans le document maître est lue comme un collage géant.

**Seuil de vitesse : 15 mots par intervalle de 2 s**, soit 450 mots/minute,
3,2× le record du monde de frappe. Un paragraphe de 80 mots collé équivaut à
2 400 mots/minute — deux ordres de grandeur de séparation, aucune zone grise.

**La greffe** résout le cas du brouillon rédigé ailleurs sans rien demander à
l'utilisateur : une citation ne se retouche jamais, donc elle reste greffe ;
un brouillon se retravaille toujours, donc il se convertit seul.

Filtre gratuit : un paragraphe en style Citation ne compte jamais.

### La porte dérobée, trouvée au premier vrai usage

⚠️ **Cette garde ne protégeait qu'`absorber()`.** `retoucher()` n'avait pas de
paramètre de débit du tout, donc coller dans une ligne qu'on est *en train
d'écrire* — même visite, mode `frappe` — ajoutait **tous les mots collés en
extension**, sans le moindre contrôle.

C'est par là qu'un vrai document est passé d'une tige à un arbre entier en trois
collages, dans le premier Word où l'add-in ait jamais tourné. Le chemin des
événements avait exactement le même trou : il est là depuis le début, et aucune
batterie ne pouvait le voir puisque aucun cahier ne collait dans une ligne
active.

**La même arrivée ne peut pas compter différemment selon qu'elle tombe dans une
ligne neuve ou dans une ligne en cours.** `retoucher()` reçoit donc le débit et
rend `greffe` comme `absorber()`.

Une imprécision assumée : convertir cette ligne plus tard recomptera le texte
**entier**, y compris les mots écrits avant le collage. Le dépassement est borné
par ce qu'on avait écrit soi-même, et le point 1 interdit de reculer — on
préfère compter un peu deux fois que de retrancher.

---

## 5. Le verrou de famille

**Décidé :** verrouillage **par segment de 5 000 mots**, pas globalement.

Sur une thèse, 800 mots représentent 0,58 % du document — et c'est
l'introduction, souvent écrite en dernier. Fixer l'identité de cinq ans de
travail là-dessus est un tirage au sort déguisé. Par segment, 800 mots
représentent 16 % de l'échantillon.

Conditions : ≥ 800 mots dans le segment **et** 3 lectures concordantes d'affilée.

Après verrou, les scores continuent de tourner mais ne mesurent plus que la
**dérive** depuis le verrouillage. C'est ce qui produit les traits hybrides.

⚠️ Sans verrou, le classement porte sur tout le texte et bascule dès que
l'équilibre s'inverse : reproduit en collant de la prose puis un rapport
structuré, la plante devient une ville vers 500 mots.

**Marge de dominance : 0,06.** En dessous, aucune famille ne domine et
l'Abstrait l'emporte par refus de classement. A rattrapé l'échantillon de
philosophie, qui était à deux millièmes de devenir une Créature.

---

## 6. L'échelle

**Décidé :** un nouveau plant au Titre 1 **ou** à 2 500 mots, au premier des deux.

La limite technique n'est pas le problème (≈ 7 000 éléments SVG pour une thèse,
un navigateur en tient 10 000). Le mur est perceptif, et il y en a deux :

- saturation — la forme devient illisible
- perte de retour — à 70 000 mots, un paragraphe change 0,14 % de la forme

⚠️ La croissance logarithmique est le réflexe pour régler le premier et
**aggrave** le second : elle passe sous le seuil de perception dès 5 000 mots,
plus tôt que la croissance linéaire qu'elle corrigeait. Le mécanisme mourrait
pile dans le tunnel du milieu.

500 pages ≈ 137 500 mots ≈ **55 plants**. Trois niveaux :
paysage → parcelles (fichiers/chapitres) → plants.

⚠️ L'extension se mesure en **mots, et en mots seuls**. Elle prenait le plus
avancé de deux comptes — les paragraphes rapportés à 52, les mots rapportés au
plant — et 52 n'était pas une quantité indépendante : c'était 5 000 / 96, le
plant exprimé dans une longueur de paragraphe **supposée**. La décision 17 a
fait de la ligne l'unité du paysage, et un vrai document a montré ce que la
constante y devenait : trente-cinq pages écrites en lignes d'une phrase, onze
mots chacune, donc 52 lignes = 570 mots. Un plant toutes les 1,6 page au lieu
d'une tous les douze, et deux cent cinquante plants pour une thèse.

### Ce qu'un article a montré

**Reconsidéré, et changé : 5 000 → 2 500.**

5 000 avait été calibré sur une thèse et sur rien d'autre. Un article de 8 000
mots — vingt pages — en fait **1,6 plant** : un germe et un arbre. Pas un
paysage, une plante en pot. Et à l'autre bout, l'auteur a posé la vraie
question : en écriture scientifique, douze pages et demie de texte fini peuvent
demander un mois. Un objet dont l'unité est le mois n'accompagne pas une
journée de travail.

Le réflexe — descendre franchement, vers 1 000 ou moins — est **faux**, et
c'est mesuré. Le plancher ne se déplace pas : il faut 800 mots pour que le
style de quelqu'un soit lisible, donc pour qu'un plant ait une famille. Plus le
plant est petit, plus ces 800 mots en mangent la vie. Compté paragraphe par
paragraphe sur une thèse de 146 000 mots, en regardant à chaque pas ce que le
volet montrait :

| mots par plant | part du temps en germe | plants | la vue d'ensemble |
|---|---|---|---|
| 5 000 | 18 % | 32 | lisible, huit massifs |
| **2 500** | **33 %** | **59** | **lisible, plus dense** |
| 1 000 | 78 % | 139 | une traînée |

À 1 000, la personne regarde une tache sans forme **plus de trois quarts du
temps**, et la vue d'ensemble n'a plus d'objets dedans — les plants deviennent
de la texture. 2 500 est le point où l'arbre de la première semaine est deux
fois plus fourni qu'à 5 000 (extension 0,48 contre 0,24) sans que rien ne se
perde.

⚠️ **Une piste écartée par la mesure : fermer le plant sur le rythme de
travail** plutôt que sur un compteur — un plant par session, dès qu'il a ses
800 mots. Elle donnait des plants inégaux qui auraient raconté *comment* on
avait travaillé, ce qui est séduisant. Mesurée, elle donne 123 plants et
surtout **0 %** : un plant fermé en fin de session n'atteint jamais son
extension pleine, donc **aucun plant n'est jamais achevé**. Elle produisait
exactement la frustration qu'elle devait guérir.

⚠️ Et une chose qu'aucun réglage ne change : « plant complet » n'est un état
que 1 à 6 % du temps, à toutes les valeurs. Le plant se referme dans la
seconde où il se remplit. **Terminer n'est pas un endroit où l'on se pose,
c'est un seuil qu'on franchit** — le sentiment que ça avance aujourd'hui ne
peut pas venir de là. Il vient du grain de l'extension, ci-dessous.

### Le grain : la profondeur devient fractionnaire

**Décidé :** l'extension entre dans le végétal de façon **continue**.

Elle n'y entrait que par une ligne — `prof_max = 4 + int(extension * 3.0)` — un
entier, donc **quatre formes** sur toute la vie d'un plant. À 2 500 mots, un
changement visible toutes les 625 : deux pages et demie, parfois une semaine de
travail. La créature en offrait onze fois plus, pour la même écriture.

On ne peut pas ajouter des niveaux, ils doublent le nombre de branches. On
ouvre donc le **dernier**, rameau par rameau : la partie entière donne les
niveaux pleins, la décimale la proportion du dernier qui est sortie. Un rameau
pas encore sorti reste un **bourgeon** — un bouquet de feuilles — au lieu de
disparaître, donc la couronne n'a jamais de trou et pousser consiste à ouvrir
un bourgeon en rameau. Aux quatre valeurs entières, l'arbre est exactement
celui d'avant : le changement raffine l'entre-deux, il ne redessine pas.

Mesuré : **83 formes distinctes** sur la vie d'un plant, un changement tous les
30 mots, contre 4 et 625.

⚠️ L'ordre d'apparition est le **bit inversé** (van der Corput), pas l'ordre
naturel des lignées. Dans l'ordre naturel, le compte des traits est le même à
chaque pas — mais à mi-pousse une moitié de la couronne est garnie et l'autre
nue : l'arbre pousse d'un côté. Ni la monotonie ni le grain ne voient la
différence ; il a fallu un essai qui regarde l'ordre lui-même.

### Le feuillage reculait d'un tiers, et c'était ancien

Le remède évident au grain — subdiviser plus fin — peut faire **reculer** la
forme, ce qu'interdit le point 1. C'est arrivé, et la mesure a montré que le
défaut était **antérieur**.

Le feuillage se partageait `BUDGET_FEUILLAGE // pointes` : le même nombre de
feuilles pour chaque bouquet. Un quotient entier n'est pas monotone — 52
pointes à 4 feuilles font 208 traits, 53 pointes à 3 en font 159. Sur la vie
d'un plant : **271 → 223, 300 → 235, 331 → 230**. Un tiers de la couronne perdu
en gagnant un rameau. La version entière le faisait déjà au dernier cran de
chaque plant (192 traits à la profondeur 6, 128 à la profondeur 7) :
**l'arbre s'éclaircissait exactement en s'achevant.** C'est très probablement
ce qu'on voyait dans le vrai Word et qu'on prenait pour un rapetissement.

Le budget se **répartit** désormais au lieu de se diviser : chaque pointe reçoit
sa part entière, et une feuille de plus à la fraction des pointes que le rang de
pousse désigne — le même ordre que les rameaux, pour que le supplément soit
dispersé. Pire recul mesuré après correction : **2,2 %** des traits.

⚠️ **Point ouvert, mesuré et non corrigé.** Il reste un flottement : le
générateur est consommé séquentiellement, donc ouvrir un rameau décale toutes
les valeurs tirées après lui et les longueurs bougent d'un pas à l'autre.
L'encombrement du plant varie ainsi de ±10 % d'un pas au suivant. La silhouette
tient — c'est le même arbre qui s'épaissit — mais la décision 1 demande zéro. Le
corriger demande de tirer les perturbations de l'arbre entier avant de dessiner,
indexées par lignée, pour que la géométrie d'un rameau ne dépende plus de
l'extension. Ce n'est pas fait.

**Décidé :** le germe se dessine. `traits.py` prévoyait trois stades depuis le
début — germe, indices, divergence — et rien n'en dessinait les deux premiers.

Ce qu'on trace, c'est **la primitive avant son assemblage**. Les quatre familles
sont quatre réponses à la même question : que fait une chaîne de segments
ensuite ? Elle bifurque, elle s'empile, elle ondule, elle se referme. Le germe
est la chaîne avant la réponse — il appartient donc aux quatre à la fois, ce qui
est exactement son état. Au stade indices, elle **penche** vers la pressentie
sans s'y engager.

⚠️ L'inflexion ne doit **jamais produire un objet reconnaissable**. Si le germe
ressemblait déjà à un arbre et devenait une ville, l'organisme se contredirait
sous les yeux de la personne — ce que le point 5 interdit. Une tendance peut se
corriger ; une promesse, non. Voir `planche_germination.png`.

⚠️ La taille de référence d'un germe est **la plus grande des quatre familles**,
pas celle de la pressentie. Les quatre n'ont pas le même encombrement natif :
avec la pressentie, le germe se mettrait à **rétrécir** le jour où une tendance
apparaît. Avec la plus grande, l'échelle ne peut que monter au verrouillage. La
croissance reste monotone quoi qu'il arrive — c'est le point 1.

---

## 7. Le contenant

**Décidé :** un **paysage**, pas un jardin.

Chaque segment ayant sa propre famille, une thèse produit 27 objets mélangés :
douze plantes, huit bâtiments, quatre créatures, trois cristaux. Un jardin ne
peut pas contenir ça sans être un fourre-tout. Un paysage, si — il contient
naturellement du végétal, du bâti, du vivant et du minéral.

---

## 8. La grammaire graphique

**Décidé :** une primitive unique — le segment — et quatre règles d'assemblage.

- il se ramifie → végétal
- il s'empile → architecture
- il s'enchaîne → créature
- il se pave → abstrait

⚠️ L'unité ne vient **pas** d'un style commun plaqué par-dessus. Elle vient de
la primitive partagée. Testée et validée sur planche.

**Décidé :** les formes doivent pouvoir **se recouper**.

L'abstrait fonctionnait parce qu'il était le seul à se superposer ; les trois
autres étaient des graphes acycliques, d'où l'impression de schéma. D'où
l'anastomose (végétal), l'occlusion de plusieurs tours (architecture), le
contour fermé et les membres articulés (créature).

⚠️ Mais la superposition doit rester **hiérarchique**. La créature v3 n'avait
plus de contour et devenait illisible. Le désordre n'est pas l'originalité.

**Décidé :** les trois curseurs de la créature agissent sur la géométrie —
largeur du corps, taille de la tête, longueur des membres — et pas seulement
sur la densité de traits.

**Décidé :** ces curseurs sont **alimentés par le vecteur de traits**, et
chaque correspondance doit dire quelque chose de vrai.

| Famille | Ce que le texte pilote |
|---|---|
| Végétal | la subordination ouvre l'angle des branches ; l'irrégularité penche l'arbre ; les phrases longues font de longs entre-nœuds |
| Architecture | les titres et les listes font le nombre de bâtiments ; la régularité aligne les hauteurs |
| Créature | le dialogue fait la tête — c'est elle qui parle ; la longueur fait le corps ; le rythme fait les membres |
| Abstrait | diversité → facettes, ponctuation rare → irrégularité, rythme → torsion, subordination → étoilement |

⚠️ Ces curseurs existaient depuis les v4-v5 mais **rien ne les alimentait** :
`etoffage` et `traits` tombaient sur leurs valeurs par défaut à chaque appel.
Toutes les créatures étaient donc la même créature, tous les abstraits le même
cristal. Invisible sur une planche, qui montre une figure à la fois — et fatal
dans un paysage, où vingt-sept plants n'auraient été que quatre formes
répétées. C'est le point 7 qui serait tombé sans qu'on comprenne pourquoi.

**Décidé :** la graine du document donne aussi de la variété **à l'intérieur**
d'une famille — port de l'arbre, courbure de l'échine. L'architecture en avait
déjà, ses hauteurs étant tirées ; la créature n'en avait aucune, son échine
étant `sin(i×0,40)×0,30` à un bruit de 0,05 près. Six créatures côte à côte
étaient six fois la même bête.

---

## 9. La couleur

**Décidé :** la teinte vient de la **date d'écriture**. Cinq palettes de cinq
tons, tirés par segment depuis la graine du document.

⚠️ **La couleur ne touche jamais la structure, uniquement l'étoffage.** C'est
cette seule règle qui préserve l'unité établie au point 8. Le squelette reste à
l'encre dans les quatre familles.

Palettes saisonnières plutôt qu'une rotation continue de teinte : une palette
d'hiver se reconnaît, une teinte à 0,08 sur la roue ne veut rien dire. Fondu de
12 jours aux frontières.

**Easter egg :** les segments écrits entre 2h et 5h prennent une palette qui
n'apparaît nulle part ailleurs. Rien ne l'annonce.

Arbitrage laissé ouvert : faire porter la teinte par la date, c'est renoncer à
ce qu'elle porte le texte. Pas les deux sur la même variable.

---

## 10. Le message de nuit

**Décidé :** tracé avec la **même primitive segment** que les plantes, pas avec
une police. C'est ce qui l'empêche de casser la langue graphique.

**Décidé :** la révélation suit les **mots écrits**, pas l'horloge. Rester assis
ne suffit pas. Complet vers 800 mots dans la fenêtre de nuit.

**Décidé :** distribution en **paquet battu**, pas en tirage indépendant. Des
tirages indépendants produisent des répétitions immédiates. État actuel : écart
moyen de 11 nuits, minimum 5. La vraie réponse est d'atteindre 20 phrases, pas
d'empiler de la logique de brassage.

Le prénom et l'accord de genre sont un **profil**, demandé au rattachement du
dossier. Le cadeau peut être offert à plusieurs personnes.

⚠️ Les phrases sont le seul endroit du système où la voix de celui qui offre
passe. Tout le reste marcherait pour n'importe qui. Elles ne se génèrent pas.

---

## 11. Stockage et périmètre

**Décidé :** le paysage appartient au **dossier**, pas au fichier.

⚠️ Les Settings appartiennent au document de destination : fusionner douze
chapitres dans un maître évapore onze paysages. Perte sèche, au moment où la
thèse est presque finie.

État dans `localStorage`, clé dérivée du **nom du dossier parent** —
`document.url` renvoie tantôt un chemin local tantôt une URL OneDrive, et bascule
selon la synchronisation. Ne jamais utiliser la chaîne brute. Préfixer par
`Office.context.partitionKey` quand il est défini (undefined sur Windows).
Copie miroir dans les Settings de chaque document comme sauvegarde — c'est la
décision 16, et elle a fini par valoir plus que la sauvegarde : c'est elle qui
détache le paysage de l'hébergeur.

⚠️ **Un add-in Word ne peut pas lire un dossier.** Il est document-scoped. Le
dossier est une *clé*, jamais un *scanner*. Un fichier n'est connu qu'une fois
ouvert avec le volet actif ; un scan complet à l'ouverture rattrape.

Au rattachement initial : tout est acquis comme capital de départ. Ensuite, tout
texte inconnu sans donnée d'arrivée est traité en greffe.

---

## 12. Performance

Mesuré sur une thèse synthétique de 146 000 mots (Python, ordre de grandeur) :

| Opération | Avant | Après | Verdict |
|---|---|---|---|
| Extraction complète | 1 110 ms | 400 ms | hors budget, mais jamais dans un tick |
| dont MATTR seul | 772 ms (70 %) | **63 ms** | n'est plus le coupable |
| Segment actif (5 000 mots) | 43 ms | 13 ms | tenable |
| Un paragraphe | 0,32 ms | 0,45 ms | trivial |
| Un tick réel (absorption + relecture) | — | **3 ms** | 3 % du budget |

Budget par tick : 100 ms. Au-delà, la frappe accroche et l'add-in sera désactivé.

**Décidé :** MATTR en **fenêtre glissante à comptes courants**, O(n) au lieu de
O(n × fenêtre). Refaire un `set()` complet à chaque décalage était un problème
d'algorithme, pas de budget : le corriger rend le cache facultatif. Y ajouter une
mémoire de normalisation d'accents — le vocabulaire d'une thèse est borné à
~30 000 formes quand les appels se comptent en centaines de milliers — fait le
reste du chemin (188 ms → 63 ms).

⚠️ **MATTR, pas TTR brut.** Le TTR chute mécaniquement avec la longueur ; il
ferait dériver la famille au fil des mois de rédaction.

⚠️ **La même erreur s'était glissée dans le compteur de connecteurs.** Il
comptait les *types* présents (`len(formes & CONNECTEURS)`), c'est-à-dire une
couverture de vocabulaire : elle croît avec la longueur et sature à 1,00 vers
1 100 mots. Sur un segment de 5 000 mots, tout texte français valait 1,00 et la
composante ne distinguait plus rien — sur le trait qui pèse le plus lourd du
végétal. Mesuré :

```
  110 mots ->  5/28 -> 0.18      854 mots -> 12/28 -> 0.82
  426 mots -> 10/28 -> 0.64     1132 mots -> 14/28 -> 1.00
```

Corrigé en **occurrences pour cent mots**, bornées entre 0,5 et 6,0 : la mesure
est alors indépendante de la longueur, et de la longueur des phrases, qui est
déjà un trait à part.

**Décidé :** le paysage est presque entièrement statique. Seul le plant en cours
est vivant ; les plants achevés sont rastérisés une fois et jamais retouchés.

**Décidé :** zéro coût à l'arrêt. Aucune boucle d'animation permanente.
Transitions CSS uniquement, déclenchées au changement.

⚠️ `localStorage` est **synchrone**. Un `JSON.stringify` de 150 Ko toutes les
2 s bloque le fil principal. Écriture amortie à 30 s, plus sauvegarde et
fermeture.

---

## 13. Portage

**Décidé :** pas de serveur.

Un cadeau adossé à un serveur meurt le jour où l'hébergement n'est plus payé.
`traits.py` n'a aucune dépendance externe précisément pour que le portage vers
JavaScript soit mécanique.

Hébergement statique HTTPS quand même nécessaire (le manifeste pointe vers une
URL). C'est **GitHub Pages**, servi depuis le dépôt lui-même :
`https://hsbtqemy.github.io/wording/addin/`. Gratuit tant que le dépôt est
public, et rien de plus à administrer.

⚠️ **L'adresse est aussi l'identité du magasin**, et ça n'avait pas été vu. Le
paysage vit dans le `localStorage`, qui est indexé par *origine* : changer
d'hébergeur, ou passer à un domaine propre, perdrait le jardin. Pour un cadeau
censé durer le temps d'une thèse, c'est la mauvaise dépendance — voir le point
ouvert 13.

Cible ≈ 30–40 Ko : pas de framework, pas de bibliothèque d'icônes ni
d'animation, polices système. Moins pour la vitesse que pour la durabilité — un
projet sans dépendances se recharge encore dans cinq ans.

**Manifeste XML classique**, pas le manifeste unifié JSON : ce dernier ne peut
pas être chargé manuellement sur Mac.

Installation Mac : déposer le XML dans
`~/Library/Containers/com.microsoft.Word/Data/Documents/wef`, redémarrer Word.
Windows : dossier partagé déclaré comme catalogue de confiance. Faire
l'installation soi-même.

**Garder le Python après le portage.** C'est le banc d'essai : on itère sur les
bornes de normalisation en une seconde avec `--demo`, puis on reporte les
constantes. Les deux bases ne partagent que des nombres.

### Ce qui est porté, et ce que le portage a trouvé

**Fait.** `addin/src/traits.js` et `addin/src/paysage.js`. Aucune dépendance,
aucune API Word, aucun DOM, aucun `localStorage` : ils prennent du texte et des
événements, ils rendent des nombres et un état. Aller chercher le texte dans
Word sera le travail du volet, et de lui seul.

`addin/src/alea.js` — le générateur de Python, refait à l'identique.
`addin/src/blake2s.js` — pour la graine du document, qui ne peut pas diverger.
`addin/src/grammaire.js` — la couleur, la primitive, les quatre familles, le
germe. Les planches restent en Python : elles sont le banc d'essai.
`addin/src/composition.js` — où se pose un plant, et les deux vues.

**Le dessin est complet.** Le JavaScript sait rendre un paysage entier, la vue
de travail et l'aperçu. Les huit mutations de la composition ne sont pas des
coquilles : chacune est une erreur qu'une décision interdit nommément — la
profondeur qui passe à l'extension (2), le gabarit qui revient sur la taille
courante (14), le germe qui prend la plus petite famille et rétrécit donc au
verrou (1), le fond qui fane au lieu de s'éloigner (1). Chacune produit un
paysage parfaitement présentable, et faux.

`addin/src/pont.js` — le pont entre Word et le paysage.
`addin/src/volet.js`, `volet.html`, `apercu.html`, `manifest.xml` — la coquille.

**Reste à porter :** le message et les phrases. **L'add-in tient debout sans
eux** : le message de nuit est un easter egg, et le registre `creux` de
`phrases.py` appartient de toute façon à l'auteur.

### Le pont, et ce qu'aucune parité ne peut voir

Tout le reste du portage est vérifié par parité : il y a un Python en face qui
dit la réponse. Le pont, non — il traduit des événements Office.js que le banc
ne produit jamais. C'est pourtant lui qui porte la décision 2. Il a donc sa
propre batterie, `addin/essais.js`, contre un Word **simulé** : pas une
imitation de Word, une imitation des suites d'événements qu'il documente.

Trois faits de l'API ont changé la conception, et aucun ne se devine :

**Les identifiants de paragraphe changent à chaque session.** `uniqueLocalId`
est un GUID « qui diffère d'une session et d'un co-auteur à l'autre ». Rien ne
peut être persisté avec. Le registre du point 3 est heureusement textuel : c'est
l'empreinte qui traverse, pas l'identifiant.

**Il n'y a aucun événement de sélection sur `Word.Document`.** Le curseur du
point 2 doit passer par l'API commune, `DocumentSelectionChanged` — qui se
déclenche **aussi quand on tape**, puisque taper déplace le point d'insertion.
Appeler `quitter()` à chaque déclenchement rouvrirait exactement ce que le
point 2 ferme : chaque frappe deviendrait une visite neuve, donc une reprise, et
une première rédaction ne ferait plus jamais pousser la forme. Le curseur n'est
donc pas « la sélection a bougé » mais « la sélection a changé de paragraphe ».

**Un événement peut venir d'ailleurs.** `args.source` vaut `Local` ou `Remote` :
la frappe d'un co-auteur ne doit pas faire pousser le paysage de quelqu'un
d'autre.

Un quatrième point, mesuré plutôt que lu : le débit du point 4 se compte **par
intervalle**, pas par vidage. Quinze mots en deux secondes valent 450 mots par
minute, que personne n'atteint à la main — mais si un vidage a pris dix secondes
(machine chargée, volet masqué), quinze mots tapés honnêtement arrivent d'un
coup et deviennent une greffe. On aurait converti l'écriture de quelqu'un en
collage, en silence.

**La parité se vérifie, elle ne se suppose pas.** `jardin/parite.py` fabrique un
cahier de cas *avec les réponses du Python* ; `addin/parite/parite.js` le rejoue
et compare. 163 914 comparaisons, dont le verdict de chaque appel d'une rédaction
de 30 000 mots, pris un par un — un écart est situé au paragraphe près, et pas
constaté à la fin sur un total qui ne dit pas où il s'est formé.

Le cahier est reproductible à l'octet près — trois générations, la même
empreinte. Une première version semait un générateur avec `hash(titre)`, et
Python randomise le hachage des chaînes à chaque processus : le cahier changeait
tout seul d'un lancement à l'autre. Un écart n'aurait pas été reproductible, et
le fichier aurait bougé à chaque régénération sans que personne n'ait rien
touché.

Pas la même graine des deux côtés, comme le laissait entendre `corpus.py` :
rejouer la graine demanderait de porter le Mersenne Twister de `random.Random`.
On testerait alors le générateur, et le premier écart viendrait de là,
c'est-à-dire de l'endroit où l'on n'apprend rien. Le cahier met la frontière au
bon endroit : le corpus reste du Python, le JavaScript ne reçoit que du texte et
des appels.

### Le générateur se porte, le corpus non

La décision 8 demande : même document, même graine, même figure. La grammaire,
la composition et le message tirent trente-six nombres au sort — pour incliner
une branche, décaler un toit, faire trembler une lettre. Si les deux langages ne
tirent pas la **même suite**, plus rien de ce qui se dessine n'est comparable, et
les quinze cents lignes de géométrie qui restent à porter deviennent invisibles
au vérificateur. On ne pourrait plus que les croire.

C'est l'inverse du choix fait pour `corpus.py`, et la distinction est nette :

|  | rôle du hasard | ce qu'on porte |
|---|---|---|
| `corpus.py` | fabrique des **données d'essai** | le texte produit, écrit dans le cahier |
| `grammaire`, `composition`, `message` | est **dans le livrable** | le générateur lui-même |

L'add-in tire au sort au moment de dessiner. Il lui faut donc un générateur
déterministe de toute façon ; la seule question était de savoir s'il devait être
*le même*. MT19937 est exactement spécifié, et le projet n'utilise que quatre
méthodes — `random`, `uniform`, `randrange`, `expovariate`. Ni `gauss`, ni
`choice`, ni `shuffle` : les compter avant d'écrire a évité de porter ce dont
personne n'a besoin. Cent trente lignes.

**Mesuré :** 1 080 tirages sur 18 graines, dont les bornes où le semis change de
forme — 0, 2³², 2⁵³−1. `random`, `uniform` et `randrange` tombent **au bit
près** ; ce ne sont que des fonctions déterministes de deux entiers de 32 bits,
il n'y a rien à arrondir. Seul `expovariate` dévie d'un ulp, par le logarithme.
Et le tri par clé aléatoire de `grammaire.py` retrouve le même ordre — un tri
stable des deux côtés n'y suffisait pas, il fallait aussi les mêmes clés.

Les quatre raccourcis qu'on prend naturellement sont dans les mutations :
semer par `init_genrand` au lieu de `init_by_array`, prendre un modulo au lieu
du rejet dans `randrange` (il consomme un mot de moins, donc tout décale deux
tirages plus loin), intervertir les deux décalages de `random()`. Aucun ne fait
planter quoi que ce soit — le générateur rend toujours des nombres d'allure
honnête, simplement pas les mêmes.

Une cinquième mutation a **échappé**, et c'était la mutation qui avait tort :
changer le bit 0 du masque de trempe ne peut rien changer, puisque `y << 7` a
toujours ses sept bits de poids faible à zéro. Vérifié plutôt que raisonné —
0 cas sur 4 999 pour le bit 0, 2 500 pour le bit 7. Une mutation sans effet n'est
pas un trou dans le cahier ; c'est un mauvais test, et le dire est la seule
manière de ne pas maquiller un 16/17 en 17/17.

**Une seule divergence assumée : l'empreinte d'un paragraphe.** Le Python prend
`blake2s(digest_size=6)`, le JavaScript MurmurHash3 — deux graines, 48 bits
gardés, la largeur du Python, donc les 17 Ko du point 3 et le même risque de
collision.

Le motif d'abord invoqué était qu'un navigateur n'a pas de hachage synchrone.
**C'était faux**, et `blake2s.js` le prouve : il a fallu l'écrire pour
`graine_du_document()`, qui ne peut pas diverger. Le vrai motif est le coût,
mesuré : sur 1 450 paragraphes, murmur3 prend 3,6 ms et blake2s 29,6 ms. Ça ne
se voit pas dans un tick — un tick ne hache qu'un ou deux paragraphes — mais au
scan complet du point 11, à chaque ouverture, où le budget est de 100 ms et où
une thèse de 2 400 paragraphes passerait de 21 à 64 ms. Pour rien : les deux
registres ne se relisent jamais, et la seule propriété demandée est celle d'une
table de hachage. La parité ne compare donc pas les clés mais ce que le reste du
système observe d'elles — le même document se découpe en le même nombre
d'empreintes distinctes des deux côtés.

**La graine du document, elle, ne peut pas diverger.** Elle détermine la figure
entière ; deux paysages différents pour le même document feraient mentir les
planches, qui sont les preuves du projet. Elle passe donc par un vrai BLAKE2s —
cent lignes, vérifiées contre `hashlib` et contre le vecteur de la RFC 7693, et
appelées une fois par document.

**Les pièges du portage sont presque tous le même.** Les classes de caractères
de JavaScript sont de l'ASCII là où celles de Python sont de l'Unicode : `\w`
ne connaît pas les lettres accentuées, `\d` ne connaît pas les chiffres arabes,
`.length` compte des unités UTF-16 quand `len()` compte des points de code.
Aucune de ces erreurs ne fait planter quoi que ce soit — le texte se découpe un
peu autrement, la famille bascule un peu plus tôt, et personne ne s'en aperçoit.
`addin/parite/mutations.js` les réintroduit une par une : 53 sur 53 sont vues.
Seize d'entre elles ne passent pas par la parité mais par les deux batteries à
hôte simulé — c'est la part du portage qu'aucun Python ne couvre, donc celle où
une mutation qui échappe coûterait le plus cher.

Cinq choses sont sorties du portage. **Aucune des cinq n'était dans le
JavaScript** : porter un programme, c'est le relire une fois de plus, et par
un autre bout.

**1. Un cache qui gardait une copie du document.** `normaliser()` passait chaque
paragraphe par `_sans_accent`, dont la mémoire avait été dimensionnée pour un
*vocabulaire*. Un cache ne vaut que si la clé revient : un mot revient des
centaines de fois, un paragraphe jamais. Mesuré : 656 entrées pour 656
paragraphes sur 40 000 mots, 766 Ko, dont pas une seule relue — et 2 372
entrées pour 2,8 Mo sur une thèse de 146 000 mots. Corrigé des deux côtés :
`_deplier` sans mémoire pour tout ce qui n'est pas un mot.

**2. `round()` n'existe pas en JavaScript.** Python arrondit la valeur binaire
*exacte* et tranche un demi exact vers le *pair*. Aucun outil de JavaScript ne
fait les deux : `Math.round(x * 10ⁿ)` a l'erreur de sa propre multiplication et
fait monter 0,00035 que le flottant place en dessous ; `toFixed` lit bien la
valeur exacte mais tranche un demi vers le haut, et rend 0,4063 là où Python
rend 0,4062 ; `Intl` avec `roundingMode: "halfEven"` tranche bien vers le pair
mais part de l'écriture décimale *courte*, et remonte 0,00035 à 0,0004.

La première version écrite ici prenait `toFixed` en supposant qu'un demi exact
n'arriverait jamais sur une somme de poids en centièmes. C'était vrai des
scores — 4 divergences sur 346 389 tirages — et faux de la **marge**, qui est un
*écart* entre deux scores : les quatre valeurs concernées sont minuscules, et
minuscule est exactement la taille d'une marge quand deux familles se tiennent,
c'est-à-dire au moment où le point 5 refuse de classer.

Un demi exact se reconnaît pourtant sans approximation : `x × 10ⁿ` vaut un demi
pile si et seulement si `x × 2ⁿ⁺¹` est un entier impair, et la multiplication
par une puissance de deux est exacte. Six lignes, vérifiées sur 316 393 valeurs
dont tous les rationnels dyadiques jusqu'au 1/16384 : aucun écart.

**3. 616 appels, et pas une frappe.** Le cahier rejouait une rédaction entière
avec ses retouches, et il avait l'air complet. Il ne l'était pas : les retouches
visaient l'avant-dernier paragraphe écrit, jamais celui où le curseur se
trouvait. Chaque retouche repassait donc par la reprise, et sur 616 appels le
verdict `frappe` n'apparaissait **pas une seule fois** — le cahier ne visitait
jamais le seul chemin pour lequel le curseur du point 2 a été écrit.

C'est la même panne que la planche des membres : une vérification qui a l'air
d'en faire beaucoup, et qui ne passe pas par le mécanisme qu'elle est censée
surveiller. En comptant vraiment ce que le cahier traversait, il manquait aussi
les verdicts `ignoree` et `inchangee`, tout plant écrit la nuit, et **tout plant
au stade germe** — donc le bloc `germe {taille, inflexion}` de `etat()`, qui est
exactement ce qui dessine une plante sans famille encore lisible, n'était jamais
comparé autrement que sous la forme `null`. `cas_journal()` refuse désormais de
fabriquer un cahier qui n'emprunte pas les neuf verdicts et ne laisse pas
derrière lui un plant de chaque stade, un plant de nuit et une greffe en attente.

**4. Les tables littérales n'étaient comparées par personne.** Dix-neuf
abréviations, vingt-huit connecteurs, quatre puces, les styles de titre, les
variantes typographiques. Le cahier de textes n'en visite que deux ou trois ; les
autres pouvaient être fausses depuis toujours. C'est la dérive la plus probable
d'un projet à deux langages et la plus silencieuse — on ajoute un mot d'un seul
côté, rien ne casse, le texte se lit juste un peu différemment. Les deux modules
exportent maintenant un `TABLES` **dérivé** des constantes, jamais recopié : une
table recopiée serait un second endroit où se tromper.

**5. `depuis()` plantait sur `[]`.** `"[]"` et `"null"` sont du JSON
parfaitement valide, et une liste n'a pas de méthode `get` : un réglage tronqué
ou écrasé dans les Settings de Word levait au chargement, là où il n'y a
personne pour rattraper — le volet serait resté noir. Le JavaScript, lui,
passait : le portage était sur ce point plus robuste que sa propre
spécification. Corrigé du bon côté, celui du Python.

### Ce que la géométrie a demandé de plus

Le dessin se compare **segment par segment avant le SVG** : un écart de
coordonnée se lit alors sur le segment fautif, au lieu d'apparaître comme deux
chaînes de trente mille caractères qui diffèrent quelque part. 268 figures,
18 443 segments, et les SVG identiques caractère par caractère.

**La trigonométrie n'est pas garantie, elle est mesurée.** Ni Python ni
JavaScript ne promettent le dernier bit sur `cos` et `sin`. Sur les 71 944
coordonnées comparées, 98,4 % sont identiques au bit et l'écart maximal est de
**1,14 × 10⁻¹³**, accumulé à travers la récursion des branches. Le SVG reste
identique parce qu'on formate à une décimale : il y a onze ordres de grandeur
entre l'écart observé et le demi-pas d'arrondi. C'est une marge, pas une
garantie — et la dire est plus honnête que d'annoncer une exactitude qu'on n'a
pas.

**Le signe du zéro.** Une branche qui repart à l'horizontale donne un y de
−0,02 ; Python écrit `-0.0`. Le portage écrivait `0.0` — non pas parce que
`toFixed` se trompe, mais parce qu'il passait par un nombre intermédiaire, et
que `toFixed` appelé sur le zéro négatif rend `0.0`. Un caractère d'écart sur
trente mille, et les deux figures ne sont plus comparables.

**Deux mutations ont échappé, et les deux avaient tort.** Le bit 0 du masque de
trempe du générateur ne peut rien changer — `y << 7` a toujours ses sept bits de
poids faible à zéro : 0 cas sur 4 999. Et une frontière de saison fermée des deux
côtés ne change aucune couleur — 0 sur 1 825 — parce qu'à la frontière
`mélange(A, B, 0,5)` et `mélange(B, A, 0,5)` donnent tous deux le milieu. Dans
les deux cas la mutation était un mauvais test, pas le cahier un mauvais cahier.
Mesuré plutôt que raisonné, et remplacé par une mutation qui mord.

**Et un défaut du vérificateur, qui accusait le portage.** La boîte de cadrage
était écrite en dur des deux côtés — 200 × 200 ici, 250 × 240 là pour la planche
des membres. Le vérificateur comparait deux cadrages différents et signalait un
écart de SVG qui n'existait pas. La boîte voyage maintenant avec le cas.

### La coquille, et où s'arrête ce qui se vérifie

`manifest.xml` est un manifeste **XML classique**, pas le JSON unifié : le point
13 le dit, l'unifié ne se charge pas à la main sur Mac, et l'installation se
fait à la main.

⚠️ **Aucune contrainte `<Requirements>` n'y est déclarée**, alors que le code a
besoin de WordApi 1.6. C'est délibéré : une contrainte non satisfaite rend
l'add-in **invisible**, sans un mot. Le volet s'ouvre donc toujours, vérifie
lui-même la version, et dit ce qui manque. Un cadeau qui ne s'ouvre pas et
n'explique rien est le pire accueil possible.

`volet.js` ne décide presque rien — il branche. Tout ce qui arbitre est
ailleurs, et c'est voulu : c'est le seul fichier qu'aucune batterie ne peut
vraiment tenir. Il garde quand même trois choses qui ne sont nulle part ailleurs
— le rattachement du document à *son* paysage, la dégradation quand 1.6 manque,
et le tic de deux secondes.

Une quatrième panne trouvée là, dans le même esprit que les précédentes : la
normalisation du débit **ne doit corriger que dans un sens**. Divisé par cinq
millisecondes, un vidage en avance transformait quatre mots tapés en un débit de
mille six cents — donc en collage. Le plancher est l'intervalle, pas 1 : la
correction peut réduire le débit, jamais l'amplifier.

**Ce qui reste hors d'atteinte.** Les deux batteries JavaScript prouvent que le
câblage tient contre un hôte simulé, pas que le vrai Word se comporte comme le
faux. Trois choses valent d'être regardées le premier jour, et `LISEZMOI.md` les
liste : que trois paragraphes tapés d'affilée fassent bien pousser la forme
(sinon `DocumentSelectionChanged` ne se comporte pas comme supposé, et c'est le
point 2 qui tombe), que le retour à la ligne compte, et qu'un chapitre collé ne
fasse rien pousser.

Et un détail qui n'en est pas un : `rattacher()` acceptait un couple
`(texte, style)` sous forme de tuple, pas de liste. JSON n'a que des tableaux,
donc le couple ne survivait pas à un aller-retour — et le premier geste du vrai
add-in, rattacher une thèse déjà écrite, est précisément celui qui passe une
liste de couples. Les deux implémentations n'avaient pas la même signature sans
que rien ne le dise.

---

## 14. La composition du paysage

**Décidé :** trois règles de placement, chacune portant une chose vraie du texte.

- **x — l'ordre dans le document.** On lit le paysage comme on lirait la thèse.
  Les parcelles sont séparées par un intervalle plus large : les trois niveaux
  du point 6 deviennent visibles sans qu'on ait rien à étiqueter.
- **échelle et profondeur — la maturité.** Un plant beaucoup repris vient au
  premier plan ; un plant posé une fois reste au fond. C'est la seule règle qui
  rend visible **où le travail est réellement allé** — et sur une thèse dont
  l'introduction a été écrite en dernier, ça se voit.
- **y — suit la profondeur.** La perspective la plus simple suffit, puisque la
  profondeur porte déjà une information.

Dessin du fond vers l'avant : c'est l'occlusion entre plants qui fait un
paysage plutôt qu'une rangée. Même raison que les tours de l'architecture.

⚠️ **L'extension n'entre pas dans le placement.** Elle est déjà dans la taille
propre du plant — un plant étendu est un grand arbre, une ville à sept tours.
La faire aussi porter la profondeur fusionnerait les deux axes par la bande.

⚠️ **Le fond s'éloigne, il ne fane pas.** Premier essai à 0,42 d'échelle et
0,45 d'opacité : un plant jamais repris devenait un fantôme, et se lisait comme
une punition de ne pas avoir retravaillé — alors que le point 1 dit que rien ne
fane jamais. La profondeur doit rester lisible comme de la distance : le plant
du fond est entier, net, un peu plus loin.

### Deux vues, pas une échelle

**Décidé :** le paysage ne se dézoome pas. Deux vues, dont une seule est
soumise à l'exigence de retour.

⚠️ **Le dézoom progressif est la croissance logarithmique du point 6,
transposée d'un cran.** Si tout doit tenir dans le cadre, un paragraphe déplace
3,84 % / n de ce qu'on regarde :

| plants | mots | dézoom pour tout tenir | vue du plant seul |
|---|---|---|---|
| 10 | 25 000 | 0,384 % | 3,84 % |
| **28** | **70 000** | **0,137 %** | 3,84 % |
| 55 | 137 500 | 0,070 % | 3,84 % |
| 104 | 260 000 | 0,037 % | 3,84 % |

⚠️ Ce calcul **ne dépend pas de la taille d'un plant** : le rapport
paragraphe / plant et le nombre de plants se compensent exactement. Passer de
5 000 à 2 500 mots par plant a doublé les deux colonnes de gauche — 1,92 % à
14 plants, 3,84 % à 28 — et laissé 0,137 % inchangé. La conclusion tient donc
quelle que soit l'échelle. Ça n'allait pas de soi, et ça a été revérifié le jour
où la constante a bougé.

Le seuil de mort donné au point 6 est 0,14 % par paragraphe, atteint à
70 000 mots. Le dézoom l'atteint à 14 plants — **soit 70 000 mots**. Le même
mur, au même endroit. Les cycles de 5 000 mots avaient racheté ce retour ; le
dézoom le redépenserait.

Une barre défilante à échelle constante garde le retour mais perd l'ensemble —
or l'ensemble est ce pour quoi le cadeau existe, à la fin. Les deux exigences
sont contraires : aucune échelle unique ne les tient. Le point 12 avait déjà
séparé les deux régimes sans le dire — « seul le plant en cours est vivant ».

- **Vue de travail** — le plant en cours, seul, dans le volet. Son échelle est
  fixée par sa taille **finale**, jamais par sa taille du moment. ⚠️ Le cadrer
  sur le plant tel qu'il est détruirait le retour par l'autre bout : s'il
  remplit toujours le volet, un plant jeune et un plant achevé se ressemblent
  et la croissance devient invisible. Voir `planche_volet.png`.
- **Vue d'ensemble** — le paysage entier, ouvert délibérément. Aucune exigence
  de retour : on n'écrit pas pendant qu'on la regarde.

**Décidé :** il n'y a **qu'un seul rendu**. La vue de travail et la vue
d'ensemble ne sont pas deux dessins mais deux **cadres** sur le même monde
composé. Deux dessins du même objet finissent toujours par diverger ; deux
cadres ne le peuvent pas. Le dézoom que tu fais toi-même devient alors
littéralement un recul de caméra : le monde ne rétrécit pas.

**Décidé :** le plant en cours n'est pas au centre du volet mais **aux deux
tiers à droite**, de sorte que le précédent reste visible en train de sortir
par la gauche.

⚠️ Sans ce décalage, le volet est **vide pendant 800 mots** — soit 16 % de
chaque cycle, vingt-sept fois sur une thèse, et la première de ces vingt-sept
fois est celle des 800 premiers mots écrits avec le cadeau installé. Avec, on
avance dans le paysage au lieu de repartir de zéro à chaque chapitre, et la
naissance d'un plant devient un événement visible : le précédent s'en va. Voir
`planche_volet.png`.

⚠️ **L'échelle d'un plant se calcule sur sa taille finale, partout — volet et
paysage.** Normaliser sur la taille du moment ramène tout plant à la même
hauteur, donc **l'extension devient invisible** : un chapitre de 1 200 mots et
un chapitre de 5 000 s'affichent identiques. Le cadre doit aussi contenir la
taille finale en LARGEUR, sinon un plant plus large que haut — un arbre, une
créature déployée — se fait rogner le jour où il arrive à maturité, c'est-à-dire
au pire moment.

**Décidé :** la vue d'ensemble compresse **en groupant, pas en réduisant**. La
hiérarchie du point 6 le donne gratuitement : les plants d'une même parcelle se
serrent et se recouvrent — c'est le même texte, ils font un relief — et les
parcelles respirent entre elles. Mesuré sur une thèse de 146 000 mots :
49 plants, 4 parcelles, **12 803 px en bande linéaire contre 4 826 en massifs
(38 %)**. Et ça se lit comme un paysage au lieu d'une rangée. Voir
`planche_apercu.png`.

### Le recul de la caméra : un exposant, pas des paliers

**Décidé :** la taille apparente du plant en cours vaut

> apparente = (taille / finale) ** `RECUL_CAMERA`, avec `RECUL_CAMERA` = 0,5

et non `taille / finale`.

Le cadre valait la taille **finale** du plant, pour que la croissance reste
visible — un cadre qui suit la taille du moment rend un plant jeune
indiscernable d'un plant achevé. Mais l'autre bout du raisonnement n'avait pas
été regardé : un plant dont la taille vaut 5 % de sa taille finale occupe alors
**5 % du volet**, c'est-à-dire un cheveu. Et la personne regarde un plant sans
famille **33 % du temps** (point 6). Voir `planche_alpha.png` : à α = 1, les
colonnes 5 % et 20 % sont vides ; à α = 0,5, c'est une tige avec son bourgeon.

⚠️ **Ce qui fait tenir le point 1 ici, c'est la monotonie, pas la valeur.** La
proposition rivale était des **paliers** de dézoom : très zoomé au départ, on
recule d'un cran quand le plant devient grand, puis encore. Elle donne la même
présence au germe — et chaque palier est un **rétrécissement visible**, trois ou
quatre fois par plant. On rachèterait avec la caméra ce qu'on venait de corriger
dans le dessin. Un exposant n'a pas de palier : le cadre ne fait que grandir
tant que le plant grandit.

⚠️ **Et il amortit le flottement**, ce qui n'est pas une chance mais une
propriété de la puissance. Le point ouvert du point 6 mesure un flottement de
l'encombrement : sur un plant de 2 500 mots, **38 reculs, un tous les 66 mots**,
dont 6 dépassent 5 % et 1 dépasse 10 %. Élevé à 0,5, un recul de 10,8 % de la
taille n'en fait plus que **5,5 %** de l'apparence, et les six reculs de plus de
5 % deviennent des reculs de 2,5 %. C'est la raison pour laquelle le flottement
reste consigné et non corrigé : le remède coûterait une réécriture du modèle
aléatoire du dessin, et l'exposant en enlève la moitié pour rien.

⚠️ Une porte de plus, trouvée en regardant la planche : `gabarit()` anticipe
aussi la **maturité** (il suppose 0,85). Un plant jamais repris ne remplit donc
jamais son cadre, quel que soit l'exposant. Non traité.

**Conséquence pour l'add-in :** le volet Word est une colonne étroite et haute
(~320-450 px). Une bande horizontale y est le pire format possible. La vue de
travail va dans le volet ; la vue d'ensemble appartient à un **dialogue**
(`displayDialogAsync`), qui s'ouvre en fenêtre large.

---

## 15. Le ton des phrases

**Décidé :** une phrase peut être appelée par un **événement** plutôt que tirée
du paquet. Et l'événement se lit sur les **deux axes**, sans aucun signal
nouveau à inventer.

| Ce que disent les axes | L'état | Registre |
|---|---|---|
| maturité monte, extension nulle | on retourne la même phrase sans avancer | `creux` |
| reprises répétées **puis** un paragraphe neuf | on a lâché prise, ça repart | `deblocage` |
| extension régulière, aucune reprise | ça coule | `elan` |
| rien de saillant | une nuit ordinaire | le paquet battu |

C'est la décision 2 qui paie une deuxième fois. Les deux axes ont été séparés
pour régler le problème de la récompense ; il se trouve qu'ils décrivent aussi,
exactement, dans quel état quelqu'un se trouve à trois heures du matin.

« C'est génial » et « mais oui » sortent donc du paquet, où elles tombaient
n'importe quand, et attendent leur moment. Une phrase qui arrive pile au
déblocage ne peut plus sembler aléatoire — elle ne l'est plus.

⚠️ **Les phrases ne se génèrent pas.** Un registre vide retombe sur le paquet :
le mécanisme n'exige rien de personne. Mais il ne remplace personne non plus.

---

## 16. Deux magasins, et lequel gagne

**Décidé :** le paysage vit dans le `localStorage`, et **chaque document en garde
une copie dans son `.docx`**.

Le point 11 met le paysage au niveau du **dossier**, ce qu'aucun fichier ne peut
porter : il faut donc un magasin au-dessus des fichiers, et `localStorage` est le
seul disponible. Mais il est indexé par **origine**. Tant que le volet est servi
par GitHub Pages, le jardin dépend de cette adresse : en changer, passer à un
domaine propre, ou simplement vider les données de site, le perdrait. Pour un
cadeau censé durer le temps d'une thèse, c'était la mauvaise dépendance — et la
dernière qui restait à un tiers.

`Office.context.document.settings` est rangé **dans le `.docx` lui-même**. Il
voyage donc avec le fichier : sauvegarde, clé USB, machine neuve, autre
hébergeur. Mesuré : une thèse de 143 000 mots fait **78 Ko** d'état sérialisé
(37 de registre, 41 de segments). Dans un document Word, ce n'est rien.

### La règle d'arbitrage : le plus d'empreintes gagne

À l'ouverture on lit les deux, et on garde **celui qui en a le plus**.

C'est la décision 1 qui rend la règle sûre : rien ne recule jamais, le registre
ne fait que grandir — y compris quand on reprend un paragraphe, puisqu'un texte
retouché est un texte de plus. La comparaison est donc **monotone**, et ne peut
pas se tromper de sens.

Ni horodatage, ni numéro de révision : les deux mentent dès qu'une horloge est
fausse ou qu'un fichier est restauré depuis une sauvegarde. Et une copie
illisible, tronquée, ou d'une autre version repart vide — c'est `depuis()` qui le
garantit, et la panne n°5 du portage l'a payé — donc à zéro empreinte : **elle
perd toute seule**, sans qu'on ait à la valider en plus.

À égalité, le dossier garde la main : c'est le magasin de travail, et basculer
pour un contenu identique ne rapporterait rien.

⚠️ **Ce que la règle ne couvre pas : deux branches qui divergent.** Elle suppose
une histoire linéaire, où une copie est simplement en retard sur l'autre. Si la
même thèse est écrite en parallèle sur deux machines, les deux registres
grandissent séparément et la plus fournie écrase l'autre. Une fusion serait
possible pour les empreintes, pas pour les segments : ils ont un ordre et des
dates, et un plant ne se recoud pas. La branche la plus courte est donc perdue —
c'est assumé, sans serveur il n'y a pas de troisième version pour trancher. Le
cas visé est l'autre, et c'est le fréquent : une machine à la fois, et un magasin
qui disparaît sous les pieds.

### Quand on écrit, et pourquoi si rarement

⚠️ **`saveAsync` marque le document comme modifié.** C'est ce qui a dicté toute
la politique d'écriture, et c'est ce que la construction a appris.

Le dossier s'écrit **à chaque tic** : synchrone, gratuit, sans effet sur le
fichier. Le document, lui, ne se réécrit que si le paysage a **réellement**
poussé, et au plus **une fois toutes les cinq minutes**.

- *Rien n'a poussé.* Un tic peut rendre des verdicts sans une empreinte de plus :
  le paragraphe vide que Word crée à chaque `Entrée`, un texte déjà connu retapé,
  une annulation. On ne repose pas la même chose.
- *C'est trop tôt.* Sans étranglement, 78 Ko repartiraient dans le document
  toutes les deux secondes — mille huit cents fois par heure, chacune relançant
  la synchronisation de qui le stocke en ligne. Ce qu'on risque à attendre :
  cinq minutes de pousse, et seulement si le `localStorage` disparaît entre-temps,
  puisque la copie n'est relue que là.
- *Le document a refusé.* On n'insiste pas. Une limite ne bougera pas d'ici la
  fin de la session, et redemander toutes les cinq minutes ne ferait que remplir
  la console. Le volet ne dit rien : un cadeau ne prévient pas qu'il a mal dormi.

**Et le réglage d'identité attend le même moment.** Il était jusqu'ici enregistré
dès l'ouverture — donc ouvrir un document, regarder le volet et refermer
suffisait à faire apparaître « voulez-vous enregistrer les modifications ? » sur
un fichier où personne n'avait tapé une lettre. Il est maintenant posé en mémoire
à l'ouverture et écrit par la **première copie**, c'est-à-dire quand le paysage a
poussé — donc quand la personne a tapé, et que le document est déjà modifié de
son fait. Le cadeau ne salit rien.

### Où ça se vérifie

`magasin.js` ne connaît pas Office.js, pas plus que `pont.js` : les deux magasins
sont **injectés**, chacun réduit à `lire`/`ecrire`. L'arbitrage — la seule chose
qui décide, ici — s'éprouve donc sans hôte du tout ; le reste contre l'Office.js
simulé : la copie qui part à la première pousse, le `localStorage` effacé d'où le
paysage revient entier, les deux étranglements, un document qui refuse, une copie
tronquée qui ne casse pas l'ouverture.

Le simulateur a dû devenir plus honnête pour ça. Il tenait **un seul sac** de
réglages là où Word en a deux — `set()` garde en mémoire, `saveAsync` écrit dans
le fichier — et il ignorait le rappel de `saveAsync`, donc un refus du document
était indiscernable d'une réussite. Les deux raccourcis rendaient invisible
exactement ce que cette décision règle.

---

## 17. Le guet : regarder au lieu d'être prévenu

**Décidé :** le volet ne passe plus par les événements de paragraphe. À chaque
tic il relit le corps du document en **une seule chaîne** et le compare au
relevé précédent.

Ce n'est pas un choix d'élégance, c'est une contrainte : les événements
`onParagraphAdded` / `Changed` / `Deleted` demandent **WordApi 1.6**, et la
machine à qui ce cadeau est destiné est un **Office LTSC Professionnel Plus
2021**, gelé à sa version de sortie pour cinq ans. `isSetSupported` y répond
`false` et le fera toujours. Ce n'était pas un canal en retard : c'était la
conception qui ne passait pas sur la machine cible.

### Ce qui a été mesuré, sur cette machine et sur du vrai texte

| Mesure | Valeur | Ce qu'elle décide |
|---|---|---|
| Jeu d'API | `WordApi 1.3` | `body.text`, `body.paragraphs`, `getSelection` présents ; ni événements ni `uniqueLocalId` |
| Aller-retour à vide | ~6 ms | le plancher d'un `Word.run` |
| 19 paragraphes, texte + style | ~45 ms | ~1,7 ms par paragraphe |
| 74 000 signes, **1 paragraphe** | 17–21 ms | **le coût est dans les objets, pas dans le texte** |
| Paragraphe sous le curseur | ~14 ms | 14 % du budget du point 12 |
| Frappe vue sans événements | 33 puis 43 changements | `DocumentSelectionChanged` suffisait déjà |

La ligne qui tranche est la troisième. Relire un document **objet par objet**
coûterait ~2,4 s sur une thèse — vingt-cinq fois le budget d'un tic. Mais
`body.text` rend le corps entier en une chaîne, sans fabriquer un seul objet
intermédiaire, et reste **plat quelle que soit la taille**.

⚠️ La toute première mesure disait 216 ms pour dix-huit paragraphes, et elle
était fausse : c'était le **premier `Word.run` de la session**, donc l'allumage
du canal RPC. Le tic, lui, ne tourne jamais à froid. Mesurer une fois, c'était
mesurer la mauvaise chose — et en conclure que le repli ne tenait pas aurait
fermé la seule porte qui restait.

### Ce que ça règle en plus, et qui vaut mieux que le dépannage

Le premier vrai document ouvert avec le volet faisait trente-cinq pages et **un
seul paragraphe** : `0 CR · 1119 VT · 0 LF`. Son auteur allait à la ligne sans
en créer une — ce qu'on fait pour éviter l'espacement entre paragraphes.

Le paysage y aurait vu **une empreinte pour 74 000 signes**. Aucune extension,
jamais ; chaque frappe lue comme une reprise du document entier. La plante
n'aurait pas poussé d'un millimètre, et rien ne l'aurait signalé.

Le guet découpe donc sur `\r` **et** sur `\x0b`. **L'unité est la ligne que la
personne fabrique en écrivant, pas celle que Word enregistre** — sinon le cadeau
récompenserait une habitude de traitement de texte.

### La règle de rapprochement

Deux instantanés, et il faut savoir ce qui a bougé. Trois temps :

1. **Rogner** la tête et la queue identiques. Écrire ne change qu'une région
   locale, donc il ne reste presque toujours qu'une ou deux lignes.
2. **Apparier ce qui est ÉGAL** dans la fenêtre restante.
3. **Apparier le reste par rang.**

⚠️ **C'est le deuxième temps qui tient l'invariant cardinal, pas le premier.**
Identifier les lignes par leur rang serait la faute : insérer une ligne au
milieu décalerait toutes les suivantes, et une insertion se lirait comme une
pluie de retouches — de l'extension prise pour de la maturité. Le rognage n'est
qu'une accélération : le retirer ne change aucun verdict.

Ce n'est pas un raisonnement, c'est une mesure. La première version de ce
commentaire attribuait la protection au rognage ; les mutations l'ont démentie —
retirer le rognage laisse tous les essais passer, retirer l'appariement par
texte les fait tomber. **Un commentaire qui désigne la mauvaise pièce fait
retirer la bonne.**

L'appariement par texte donne au passage ce que le point 3 promet : une ligne
**déplacée** garde son identifiant et ne rend aucun verdict.

### La fermeture de visite

Le curseur est mort avec ce document : sur trente-cinq pages en un paragraphe,
`getSelection().paragraphs` ne rend aucune ligne. Il fallait fermer les visites
autrement — et deux choses réduisent beaucoup l'enjeu, toutes deux découvertes
en relisant `paysage.py` plutôt qu'en raisonnant :

- **changer de ligne ferme déjà la visite**, sans rien ajouter : `_actif` n'a
  qu'une case, donc écrire ailleurs la déplace et revenir tombe forcément dans
  la branche « reprise » ;
- **tripoter ne pousse pas**, même dans une visite ouverte : la branche `frappe`
  compte `max(0, mots(nouveau) − mots(ancien))`.

Ce que `quitter()` protégeait n'était donc **pas l'extension mais la maturité**.
Sans lui, revenir sur une ligne une semaine plus tard reste la même visite,
`plant.reprises` ne monte jamais, et l'élément cesse de mûrir — l'autre axe
meurt en silence.

Le guet ferme donc la visite après `SILENCE` relevés sans changement, soit deux
minutes. **La borne basse est mesurée** : 57 % des relevés voient un changement
en écriture active, 24 % en frappe distraite, donc soixante relevés calmes ne
peuvent pas arriver pendant qu'on écrit. ⚠️ **La borne haute reste un
jugement** — assez pour une pause de réflexion, pas pour un café. À confirmer au
banc.

### Les styles

`body.text` n'en porte aucun, et sans eux une citation compterait comme de
l'écriture (point 3) et un Titre 1 n'ouvrirait plus de plant (point 6).

La structure donne la réponse : `body.text` sépare les **paragraphes** par `\r`
et les **lignes** par `\x0b`. Découper en deux temps rend les deux échelles, et
une ligne hérite du style de son paragraphe, exactement.

Et le rafraîchissement est gratuit : le **nombre de paragraphes** se lit dans la
chaîne qu'on vient de recevoir. Taper dedans ne le change pas ; en ajouter un,
si. La lecture chère ne part donc que quand la structure bouge.

### Ce que ça coûte

⚠️ **Le guet ne sait pas QUAND le texte est arrivé.** Un événement se produit au
moment de la chose ; un instantané dit seulement qu'elle est là. Diviser le
débit par le temps écoulé était juste tant qu'on était prévenu — un relevé en
retard signifiait alors que la personne avait tapé lentement.

Mesuré : un collage de deux cents mots vu deux secondes plus tard donne un débit
de **200**, donc une greffe ; vu soixante secondes plus tard, **6,7**, donc de
l'**écriture**. Deux cents mots comptés pour rien.

**L'asymétrie tranche.** Une greffe déclarée à tort se rattrape toute seule : la
retravailler la convertit (point 4). Une pousse déclarée à tort ne se rattrape
**jamais**, puisque le point 1 interdit de reculer. Dans le doute, il faut donc
lire un collage — d'où `PLAFOND_ECOULE`, quatre intervalles. Personne ne tape
soixante mots dans un seul élan, donc le plafond ne peut pas transformer de la
frappe honnête en collage ; au-delà, on n'a de toute façon plus aucune idée de
quand le texte est arrivé.

⚠️ **Le guet ne distingue plus la frappe d'un CO-AUTEUR.** Les événements
portaient `args.source`, et le pont ignorait les modifications distantes. Un
instantané de texte ne dit pas qui a écrit. Sur un document partagé, la frappe
de quelqu'un d'autre fera pousser le paysage. Sans WordApi 1.6 l'information
n'existe pas — et une thèse s'écrit seul.

⚠️ **Un seul chemin, pas deux.** Le guet marche sur tous les Word, les
événements seulement sur certains : ce n'est donc pas deux versions pour deux
publics, mais un chemin universel plus une optimisation. Dans un cadeau, la
complexité facultative est ce qu'il faut refuser — et deux chemins voudraient
dire que chaque mutation devrait être attrapée sur les deux, sinon la moitié du
code n'est pas éprouvée. `pont.js` reste dans l'arbre, plus importé par le
livrable, jusqu'à ce que le guet ait tourné dans un vrai Word.

### Un défaut trouvé en chemin

`pont.js` passait **toujours** `etait_greffe = false`, donc la branche
`conversion` de `retoucher()` n'était **jamais atteinte** dans l'add-in : un
chapitre collé puis retravaillé restait une greffe pour toujours, et la décision
4 ne s'appliquait qu'à moitié. Le guet retient quelles lignes sont arrivées en
greffe, et la conversion a enfin lieu.

### Où ça se vérifie

**Le guet est le premier morceau du câblage Word couvert par la PARITÉ.**
`pont.js` et `volet.js` n'ont jamais eu de Python en face ; le rapprochement de
deux instantanés, lui, est de la logique pure sur des tableaux de chaînes.

Le cahier rejoue une session d'écriture et compare, à chaque relevé, les faits,
**les identifiants**, le compte de paragraphes, le débit, les verdicts et l'état
du paysage. Il refuse de se construire s'il ne traverse pas les quatre genres de
faits et les sept verdicts.

Six mutations ont pourtant échappé au premier passage, toutes pour la même
raison — **le cahier ne contenait rien qui traverse ce qu'elles cassaient** :

| Ce qui échappait | Ce qui manquait au cahier |
|---|---|
| `pop()` pour `pop(0)` | aucune ligne en double dans une même fenêtre |
| le style indexé par ligne | tous les styles après le premier valaient « Normal » |
| le drapeau de naissance | aucun texte n'entrait en collision avec le registre |
| le plancher du débit | `ecoule` valait toujours l'intervalle |
| la fermeture de visite | aucune retouche **sur la ligne active** après le silence |
| le débit négatif | aucune ligne ne raccourcissait jamais |

Une mutation qui échappe est un trou dans les cas, pas une bonne nouvelle. Les
six trous sont comblés, et le cahier porte maintenant deux lignes vides
consécutives, un dernier paragraphe en style Citation, une ligne qui raccourcit,
une ligne dont le texte est déjà au registre, des temps écoulés variés — dont un
relevé **en avance**, celui qui transformait quatre mots tapés en collage.

Les deux harnais **vérifient leurs motifs avant de muter quoi que ce soit**. Un
motif périmé se signalait « obsolète » en cours de route, après avoir laissé
tourner la vérification complète pour toutes les mutations d'avant. C'est arrivé
trois fois dans la même journée, dans les deux langages, et toujours pour la
même cause : le motif contenait un échappement que le langage interprétait à
l'exécution.

---

## Points ouverts

1. **Le creux des phrases — le mécanisme est prêt, les phrases sont à écrire.**
   Elles ne se génèrent pas : c'est le seul endroit du système où la voix de
   celui qui offre passe. Le registre `CREUX` de `phrases.py` est délibérément
   vide, et tant qu'il l'est, la nuit de creux retombe sur le paquet ordinaire —
   rien ne casse, il manque juste ce qui compte. Ce qu'il ne faut pas y mettre :
   rien qui félicite, rien qui encourage, rien qui demande quoi que ce soit.
2. ~~**Déclencher « c'est génial » et « mais oui » sur un événement.**~~
   **Réglé** — et par la décision 2, sans aucun signal nouveau. Voir le point 15.
3. ~~**Le végétal sature en haut.**~~ **Réglé.** Le plafond de la v4 bornait
   chaque bouquet, mais le *nombre* de bouquets croît en 2^profondeur. On
   plafonne désormais le total et on le répartit — même remède que les cycles de
   5 000 mots. Voir `planche_feuillage.png`, les deux lignes côte à côte.
4. ~~**Les lettres restent une police.**~~ **Réglé, mais pas par où on croyait.**
   Les polylignes à longueurs inégales aident peu. Ce qui compte, c'est de
   déplacer les **sommets** de la lettre : l'apex du M, la pointe du A et la
   diagonale du N tombaient toujours sur les mêmes points de la grille 3×5, donc
   l'œil lisait une fonte tremblée quel que soit le tremblement. Décalage
   partagé par tous les traits qui se rejoignent en un point, sinon la lettre se
   découd. Voir `planche_main.png`.
5. ~~**Saturation de la palette de nuit.**~~ **Réglé.** Le bleu-gris de la v5
   était à deux doigts de l'hiver ; le violet de la v6 n'appartient à aucune
   saison. Voir `planche_saisons_v7.png`.
6. ~~**Membres de la créature.**~~ **Réglé.** Bornés à la largeur du corps. Une
   longueur absolue donnait des pattes identiques sur une bête gracile et sur
   une bête massive : la gracile devenait une araignée. Voir
   `planche_membres.png`.
7. ~~**La couleur de l'architecture invente des dates.**~~ **Réglé.** Le plant
   retient `{jour: mots}` — la vraie dispersion, pondérée — et chaque tour y tire
   la sienne. Une dizaine d'entiers par plant. Voir `planche_dates.png`.
8. ~~**Le nombre de plants dépend du style, d'un facteur deux.**~~ **Assumé.**
   Le plafond qui mord en premier gagne, et c'est correct : la garantie qui
   compte est celle du point 6 — chaque paragraphe doit bouger la forme d'au
   moins 1,92 %. La tenir pour quelqu'un qui écrit en paragraphes courts impose
   plus de plants, tous complets. Un paysage plus dense, pas un paysage moins
   juste.
9. ~~**Le message de nuit se recentre à chaque lettre.**~~ **Réglé.** Le cadre
   est celui de la phrase complète, calculé avant de dessiner. Vérifié : le
   cadre est identique à tous les avancements.

**Restent ouverts :**

10. **Le raccord du paquet ne portait pas.** Il comparait le nouveau paquet à
    `battre(tour - 1)` — c'est-à-dire au paquet *avant* son propre raccord, un
    ordre qui n'a jamais été joué. Mesuré : écart minimum d'**une** nuit, soit la
    même phrase deux soirs de suite. Corrigé en chaînant les tours ; l'écart
    minimum passe à 4. Mais avec dix phrases dans le paquet, l'écart moyen
    plafonne à 10 nuits. La vraie réponse reste d'atteindre vingt phrases.
11. ~~**Le paysage complet fait 13 000 px de large.**~~ **Réglé** — voir le
    point 14, « deux vues, pas une échelle », et le décalage aux deux tiers qui
    règle le volet d'un plant qui vient de naître.
12. **La transition germe → famille reste une coupure.** À 800 mots, une chaîne
    penchée devient un arbre. L'échelle est monotone, mais la forme, non. Sur un
    cadeau, c'est le seul instant où l'organisme change de nature sous les yeux
    de la personne — et c'est peut-être bien ainsi : c'est une naissance, pas un
    fondu. À regarder en vrai avant de trancher.

---

13. ~~**Sortir le paysage du `localStorage`.**~~ **Réglé** — voir la décision 16.
    Chaque document garde une copie de l'état dans son `.docx` ; à l'ouverture,
    c'est celle qui a le plus d'empreintes qui fait autorité. L'origine qui
    change, la machine neuve et les données de site vidées sont couvertes.

    La construction a trouvé une chose que le point ne disait pas : `saveAsync`
    **marque le document comme modifié**. Toute la politique d'écriture en
    découle — copie rare, jamais pour rien, et le réglage d'identité qui attend
    la première pousse au lieu de partir à l'ouverture.

14. ~~**L'unité du paysage n'est pas celle de tout le monde.**~~ **Réglé** —
    voir la décision 17 : le guet découpe sur tous les séparateurs de ligne. Le
    premier vrai document ouvert avec le volet faisait trente-cinq pages — et
    **un seul paragraphe**. Mesuré : `0 CR · 1119 VT · 0 LF · 1 objets`. Aucune
    marque de paragraphe, mille cent dix-neuf sauts de ligne (Maj+Entrée), soit
    soixante-six signes par ligne. Word a raison, il n'y a bien qu'un
    paragraphe ; c'est l'auteur qui allait à la ligne sans en créer un, ce
    qu'on fait naturellement pour éviter l'espacement entre paragraphes.

    ⚠️ **Le paysage y verrait une empreinte pour 74 000 signes.** Aucune
    extension, jamais ; chaque frappe lue comme une reprise du document entier.
    La plante ne pousserait pas d'un millimètre, et rien ne le signalerait — la
    pire des pannes selon le point 3, celle qui ne dit pas son nom.

    Ce n'est pas un défaut du portage. C'est un décalage entre l'unité du projet
    — le paragraphe au sens de Word — et une façon d'écrire parfaitement
    légitime. Aucune batterie ne pouvait le trouver : il a fallu un vrai texte
    sur une vraie machine.

    **Direction pressentie :** compter les *lignes*, pas les paragraphes.
    L'unité qui compte est celle que la personne fabrique en écrivant, pas celle
    que Word enregistre. Quelqu'un qui va à la ligne a produit quelque chose,
    qu'il ait appuyé sur Entrée ou sur Maj+Entrée, et la forme doit pousser
    pareil — sinon le cadeau récompense une habitude de traitement de texte.

    ⚠️ Découper au bon endroit ne suffit pas. Si les sous-lignes sont
    identifiées par leur **rang**, insérer une ligne au milieu décale toutes les
    suivantes : le miroir les voit toutes changer, et une insertion se lit comme
    une pluie de retouches. C'est **l'invariant cardinal retourné** — de
    l'extension prise pour de la maturité. L'identification doit passer par le
    contenu, donc par un rapprochement des deux états, jamais par l'indice.

15. ~~**Un Office LTSC ne verra jamais les événements de paragraphe.**~~
    **Réglé** — voir la décision 17 : le volet regarde au lieu d'être prévenu,
    et ne demande plus que WordApi 1.1. La machine cible est un Office LTSC
    Professionnel Plus 2021, version 2108 — gelé à sa version de sortie pour
    cinq ans, correctifs de sécurité seulement. `isSetSupported("WordApi",
    "1.6")` répond `false` et le fera toujours. La personne à qui le cadeau est
    destiné a la même. Ce n'est pas un canal en retard : c'est la conception
    qui ne passe pas sur la machine cible.

    Mesuré sur cette machine, et plus rien n'est supposé :

    | Ce qui a été mesuré | Valeur | Ce qu'elle décide |
    |---|---|---|
    | Jeu d'API | `WordApi 1.3` | `body.paragraphs`, `getSelection`, `getFirstOrNullObject` présents ; ni événements ni `uniqueLocalId` |
    | Aller-retour à vide | ~6 ms | le plancher d'un `Word.run` |
    | 19 paragraphes, texte + style | ~45 ms | ~1,7 ms par paragraphe |
    | 74 000 signes, 1 paragraphe | 17–21 ms | **le coût est dans les objets, pas dans le texte ni les styles** |
    | Paragraphe sous le curseur | ~14 ms | 14 % du budget du point 12 |
    | Frappe vue sans événements | 33 puis 43 changements | **`DocumentSelectionChanged` suffit** |

    Donc : relire tout le document *objet par objet* coûterait ~2,4 s sur une
    thèse, vingt-cinq fois le budget d'un tic — mort. Mais `body.text` rend le
    corps entier en **une chaîne**, sans un seul objet intermédiaire, et reste
    plat quelle que soit la taille.

    **Direction pressentie :** un *guet*. Le tic prend un instantané de
    `body.text`, le découpe sur `\r` **et** sur `\u000B`, et le compare au
    précédent. Deux propriétés le recommandent au-delà du dépannage :

    - il règle le point 14 par construction, puisqu'il retrouve les lignes que
      la personne a écrites quelle que soit la touche employée ;
    - c'est de la **logique pure sur des tableaux de chaînes**, donc
      spécifiable en Python et **couverte par la parité** — ce que `pont.js`
      n'a jamais pu être, faute de Python en face. Le remplacement serait mieux
      vérifié que ce qu'il remplace.

    `pont.js` n'a pas à changer : sur ses vingt usages d'identifiant, tous sont
    des clés opaques ou un `===`. Il n'en lit jamais la forme, et `lire()` lui
    est injecté. Le guet fournirait donc ses propres identifiants, tirés du
    rapprochement, et résoudrait `lire()` depuis son propre instantané — sans
    aucun aller-retour vers Word.

    ⚠️ Reste à trancher si les deux chemins **cohabitent**. Le guet marche sur
    tous les Word ; les événements seulement sur certains. Ce n'est donc pas
    deux versions pour deux publics, mais un chemin universel plus une
    optimisation — et dans un cadeau, la complexité facultative est ce qu'il
    faut refuser. Deux chemins voudraient aussi dire que chaque mutation devrait
    être attrapée sur les deux, sinon la moitié du code n'est pas éprouvée.

---

## Fichiers

**En service.**

| Fichier | Rôle |
|---|---|
| `traits.py` | extraction des traits, classement en familles |
| `paysage.py` | registre, collage, segments, verrou par segment, dérive |
| `guet.py` | deux instantanés comparés : ce que le volet lit sans être prévenu |
| `grammaire.py` | les quatre familles, couleur, à l'état des décisions |
| `message.py` | alphabet en segments, tracé à la main, révélation |
| `composition.py` | où se pose un plant : le paysage entier |
| `phrases.py` | registres, routage par événement, paquet battu |
| `corpus.py` | génération de texte à profil de traits imposé |
| `essais.py` | **toutes les vérifications, avec un code de sortie** |
| `parite.py` | fabrique le cahier de cas et lance la vérification JavaScript |
| `mutations.py` | la batterie sait-elle échouer ? |
| `banc.py` | les six essais de décision, appelés par `essais.py` |
| `stabilite.py` | test : la famille tient-elle au fil de la rédaction |

**Le livrable**, sous `addin/`. Le Python reste la spécification : quand les
deux divergent, c'est le JavaScript qui a un bug.

| Fichier | Rôle |
|---|---|
| `src/alea.js` | le générateur de Python, refait à l'identique |
| `src/blake2s.js` | BLAKE2s, pour la graine du document |
| `src/composition.js` | portage de `composition.py`, sans les planches |
| `src/pont.js` | le pont vers Word — sans Python en face |
| `src/magasin.js` | les deux copies du paysage, et laquelle gagne (point 16) |
| `src/guet.js` | portage de `guet.py` — le premier cablage couvert par la parité |
| `essais.js` | **le pont, contre un Word simulé, avec un code de sortie** |
| `essais_volet.js` | **le câblage Office.js, contre un hôte simulé** |
| `src/volet.js` | le seul fichier qui parle à Office.js |
| `manifest.xml` | le manifeste XML, sans contrainte de version |
| `volet.html` · `apercu.html` | les deux vues du point 14 |
| `icones.py` | les trois icônes du ruban, dessinées par la grammaire |
| `LISEZMOI.md` | installer, et quoi regarder le premier jour |
| `src/grammaire.js` | portage de `grammaire.py`, sans les planches |
| `src/traits.js` | portage de `traits.py` |
| `src/paysage.js` | portage de `paysage.py` |
| `parite/parite.js` | rejoue le cahier et compare — **code de sortie** |
| `parite/mutations.js` | le vérificateur sait-il échouer ? |

**Historique.** Ces fichiers ont servi à trancher, et les planches qui les
accompagnent sont les preuves. Ils ne sont plus le code de référence : ce qu'ils
ont établi est repris dans `grammaire.py` et `paysage.py`.

| Fichier | Ce qu'il a établi | Remplacé par |
|---|---|---|
| `jardin.py` | verrou et dérive — mais **globaux**, ce que le point 5 interdit | `paysage.py` |
| `grammaire2.py` | primitive segment, quatre assemblages, les deux axes | `grammaire.py` |
| `abstrait.py` | abstrait piloté par le vecteur de traits | `grammaire.py` |
| `grammaire3.py` | superposition : anastomose, occlusion, articulation | `grammaire.py` |
| `grammaire4.py` | couleur par date, créature en trois parties | `grammaire.py` |
| `grammaire5.py` | palettes saisonnières, géométrie des parties | `grammaire.py` |
| `grammaire6.py` | alphabet en segments, révélation progressive | `message.py` |

⚠️ Le code avait divergé en versions parallèles dont **aucune n'était
complète** : `Toile` redéfinie quatre fois avec des signatures incompatibles,
`PALETTES` en deux versions, le végétal et l'architecture restés en v4, la
créature en v5, la couleur en v6. Le fondu de 12 jours décidé au point 9 était
présent en v5 et **perdu** en v6. Porter en JavaScript dans cet état, c'était
porter un assemblage que personne n'avait jamais vu en entier.
