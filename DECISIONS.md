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

**Décidé :** un nouveau plant au Titre 1 **ou** à 5 000 mots, au premier des deux.

La limite technique n'est pas le problème (≈ 7 000 éléments SVG pour une thèse,
un navigateur en tient 10 000). Le mur est perceptif, et il y en a deux :

- saturation — la forme devient illisible
- perte de retour — à 70 000 mots, un paragraphe change 0,14 % de la forme

⚠️ La croissance logarithmique est le réflexe pour régler le premier et
**aggrave** le second : elle passe sous le seuil de perception dès 5 000 mots,
plus tôt que la croissance linéaire qu'elle corrigeait. Le mécanisme mourrait
pile dans le tunnel du milieu.

Des cycles de 5 000 mots plafonnent à 52 paragraphes, soit 1,92 % par
paragraphe, indéfiniment.

500 pages ≈ 137 500 mots ≈ 1 450 paragraphes ≈ 27 plants. Trois niveaux :
paysage → parcelles (fichiers/chapitres) → plants.

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
Copie miroir dans les Settings de chaque document comme sauvegarde.

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
URL) : GitHub Pages, Netlify, Cloudflare Pages.

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
1,92 % / n de ce qu'on regarde :

| plants | mots | dézoom pour tout tenir | vue du plant seul |
|---|---|---|---|
| 5 | 25 000 | 0,384 % | 1,92 % |
| **14** | **70 000** | **0,137 %** | 1,92 % |
| 27 | 135 000 | 0,071 % | 1,92 % |
| 52 | 260 000 | 0,037 % | 1,92 % |

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

## Fichiers

**En service.**

| Fichier | Rôle |
|---|---|
| `traits.py` | extraction des traits, classement en familles |
| `paysage.py` | registre, collage, segments, verrou par segment, dérive |
| `grammaire.py` | les quatre familles, couleur, à l'état des décisions |
| `message.py` | alphabet en segments, tracé à la main, révélation |
| `composition.py` | où se pose un plant : le paysage entier |
| `phrases.py` | registres, routage par événement, paquet battu |
| `corpus.py` | génération de texte à profil de traits imposé |
| `essais.py` | **toutes les vérifications, avec un code de sortie** |
| `mutations.py` | la batterie sait-elle échouer ? |
| `banc.py` | les six essais de décision, appelés par `essais.py` |
| `stabilite.py` | test : la famille tient-elle au fil de la rédaction |

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
