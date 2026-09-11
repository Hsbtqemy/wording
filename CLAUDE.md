# Paysage

Un add-in Word qui fait pousser un paysage SVG pendant qu'on écrit une thèse.
C'est un cadeau, pas un outil de productivité : rien ne doit ressembler à une
barre de progression, à un score, ni à un rappel.

**`DECISIONS.md` est la colonne du projet.** Dix-sept décisions, chacune payée par
une panne réelle. Avant de toucher une constante, lire son entrée — le nombre
qui a l'air arbitraire ne l'est pas, et le changer casse quelque chose qui a
coûté cher. Toute décision de conception se consigne là, avec ce qui l'a
motivée et ce qu'on a mesuré.

---

## L'invariant cardinal : deux axes, jamais un

- **extension** — des paragraphes NEUFS arrivent : la forme *pousse*.
- **maturité** — un paragraphe déjà là change : l'élément *mûrit*.

Reprendre quarante fois la même phrase produit un élément somptueux sur une
forme qui n'a pas grandi. **Tripoter ne doit jamais pouvoir simuler de la
croissance.** Confondre les deux est l'erreur centrale du projet ; tout le reste
en découle. Voir la décision 2, et le curseur qui sépare une première frappe
d'un retour.

Le second piège récurrent : **une échelle calculée sur la taille courante**
efface les différences de taille qu'elle est censée montrer. Toujours passer par
le gabarit final (`gabarit()`), en largeur comme en hauteur.

---

## Deux langages, un seul maître

| | |
|---|---|
| `jardin/*.py` | la **spécification** et le banc d'essai |
| `addin/**/*.js` | le **livrable**, l'add-in Word |

Quand les deux divergent, **c'est le JavaScript qui a un bug** — sauf si le
portage révèle que le Python est le plus fragile des deux, ce qui est arrivé
trois fois. Dans ce cas on corrige le Python, jamais on n'aligne la spec sur le
port.

Une seule divergence assumée : `empreinte()`. Pas de hachage synchrone dans un
navigateur, donc MurmurHash3 au lieu de blake2s. Les deux registres ne se
relisent jamais ; seule la largeur (48 bits) et le pouvoir séparateur comptent.

**Aucune dépendance, jamais.** Ni côté Python, ni côté JavaScript. Un cadeau
adossé à une bibliothèque meurt le jour où elle casse. Cible ≈ 30–40 Ko.

---

## Vérifier

Les six suites, **dans une seule commande**, jamais en parallèle :

```bash
python jardin/essais.py && python jardin/mutations.py \
  && python jardin/parite.py && node addin/essais.js \
  && node addin/essais_volet.js && node addin/parite/mutations.js
```

PowerShell 5.1 n'a pas `&&` : ecrire `a; if ($?) { b }`, ou passer par
l'outil Bash.

Attendu : `70 passes, 0 en echec` · `58/58` · `aucun ecart` · `23 passes` ·
`25 passes` · `106/106`.

`essais_volet.js` éprouve le **câblage Office.js** contre un hôte simulé — ce
qu'aucune parité ne peut couvrir, faute de Python en face. Elle y a trouvé
quatre défauts qui auraient été livrés.

⚠️ `essais.js` éprouve `pont.js`, **qui n'est plus dans le livrable** depuis la
décision 17 : `volet.js` ne l'importe pas. Le fichier et ses vingt-trois essais
restent le temps que le guet ait tourné dans un vrai Word — le chemin des
événements est alors à une ligne de distance. Ils partiront ensemble.

⚠️ Aucune des deux ne prouve que le vrai Word se comporte comme le faux. C'est
le risque irréductible, et il ne se lève qu'en déposant le manifeste dans Word —
voir `addin/LISEZMOI.md`.

⚠️ **`mutations.py` et `mutations.js` réécrivent les fichiers source sur le
disque** pour vérifier que les essais savent échouer. Deux suites en même temps,
ou une suite tuée, laissent du code muté en place — et la suivante signale des
régressions dans des fichiers que personne n'a touchés. Un filet existe (copie
`.intact` relue au démarrage), il ne protège pas de deux écritures simultanées.
Après coup, vérifier `git status`.

Durée mesurée de l'enchaînement complet : **13 min 14** (9 septembre 2026, à 58
et 106 mutations). C'était 14 min 50 à 54 et 103, 15 min 38 à 50 et 100, 9 min 38
à 13 min 35 à 47 et 98, et 5 min 57 à 36 et 87.

⚠️ **Lire cette suite dans l'ordre : 15 min 38, puis 14 min 50, puis 13 min 14 —
pendant que la chaîne gagnait huit mutations et deux essais.** Le code n'a pas
accéléré ; la machine était moins chargée. Ces totaux ne sont pas une tendance,
et le seul usage honnête qu'on peut en faire est de savoir combien de temps
prévoir, jamais de comparer deux versions. Pour ça, alterner — voir plus bas. Où le temps passe, parce que ça se voit
mal autrement :

| `essais.py` | `mutations.py` | `parite.py` | les deux `essais*.js` | `mutations.js` |
|---|---|---|---|---|
| 13–16 s | **≈ 13 min** | 4–5 s | < 1 s | ≈ 2 min |

⚠️ Les deux colonnes en ≈ sont **déduites**, pas chronométrées : total mesuré
moins les quatre suites courtes, elles chronométrées. Un chiffre déduit d'un
total où l'essentiel est justement ce qu'on déduit ne vaut pas grand-chose —
si la question est « où passe le temps », c'est `mutations.py` qu'il faut
chronométrer directement, et personne ne l'a fait.

⚠️ La fourchette est de la **charge machine, pas du code** : deux mesures dos à
dos du même `essais.py` ont donné 14 194 ms et 14 018 ms là où il avait mis
10 037 ms une heure plus tôt. Avant d'accuser un essai neuf d'avoir ralenti la
chaîne, mesurer les deux versions **l'une après l'autre** — sinon on retire du
travail juste pour rien.

`mutations.py` relance `essais.py` cinquante-huit fois, et `mutations.js`
relance la parité ou la batterie du volet cent six fois. Assez
long pour donner envie de paralléliser, ce qu'il ne faut surtout pas faire.

⚠️ **Tout ce qu'on ajoute à `essais.py` est donc multiplié par cinquante-huit.**
Un essai qui balayait les tailles de massif de 2 à 40 en végétal a coûté 12,8 s
par passage — neuf minutes de chaîne — pour une propriété qui ne dépend pas de
la famille. Mesurer le coût d'un essai neuf fait partie de l'écrire : voir la
décision 14.

Exemple de mesure faite comme il faut : les deux essais ajoutés pour le partage
de MATTR coûtent **+808 ms** par passage — médiane de trois tours **alternés**
entre les deux versions, 13 864 contre 14 672 ms. Sur cinquante relances, une
quarantaine de secondes. Les tours individuels allaient de 12 993 à 24 592 ms
selon la charge : sans l'alternance, n'importe quelle conclusion était
disponible.

De même pour l'essai de croissance additive (décision 18), qui balaie quatre
familles × quatre graines × vingt pas : **+654 ms** par passage, médiane de
trois tours alternés, 11 866 contre 12 520 ms. Son échantillonnage n'a pas été
choisi au flair — il a été **mesuré contre les mutations qu'il doit attraper**,
et deux d'entre elles ont d'ailleurs révélé qu'il manquait une assertion, pas
des graines.

⚠️ Pendant qu'une suite de mutations tourne, ne rien **modifier** dans
`jardin/*.py` ni `addin/**/*.js` — elle garde en mémoire la version lue au
démarrage et la réécrit après chaque mutation, donc une modification faite
entre-temps disparaît sans un mot et la suite finit en vert.

⚠️ Et ne rien **exécuter** qui importe ces sources, ce qui est plus insidieux.
Reconstruire le cahier de parité pendant une passe de mutations l'a rempli avec
les réponses d'un `guet.py` **muté** : tous les styles valaient « Normal », la
parité a signalé quarante-six écarts, et le diagnostic a coûté un cycle entier
avant qu'on comprenne que le code était bon et le cahier faux.

⚠️ Les motifs de mutation sont **sensibles aux fins de ligne**, et git
normalise en CRLF à chaque `checkout` sous Windows. Un motif multi-ligne cesse
alors de mordre, et le contrôle préalable déclare tout le fichier périmé alors
qu'aucun motif n'a vieilli — **un clone frais du dépôt refuserait de lancer les
mutations**. Les deux harnais comparent donc sur une copie en LF et restaurent
les octets d'origine ; ne pas défaire ça.

`addin/parite/cas.json` et `jardin/planches.html` sont des produits de
compilation, ignorés par git et régénérés en quelques secondes.

## Comment on teste ici

**Une batterie qui passe ne prouve rien tant qu'on n'a pas montré qu'elle sait
échouer.** C'est à ça que servent les deux `mutations` : elles réintroduisent
des régressions réellement commises et vérifient qu'on les rattrape. Une
mutation qui ÉCHAPPE est un trou dans les cas, pas une bonne nouvelle.

Quatre pièges déjà rencontrés, à ne pas refaire :

- un essai qui **recalcule lui-même** la valeur attendue teste sa propre
  arithmétique, pas le code ;
- un essai qui **compare à la constante** qu'on est en train de casser s'adapte
  à la panne ;
- un cahier qui a l'air complet et **ne traverse jamais** le mécanisme surveillé
  — sur 616 appels, le verdict `frappe` n'apparaissait pas une fois ;
- ⚠️ **un essai qui tire UNE graine et compare à un seuil calé sur elle.**
  Trouvé trois fois dans la même journée. L'essai de caméra passait parce que
  la graine 11 ne tombait pas dans un creux : à huit jalons au lieu de quatre,
  48 graines sur 50 le faisaient échouer. « La structure change la silhouette »
  et « le vocabulaire ouvre le feuillage » échouaient déjà, sur le code
  inchangé, 2 fois et 7 fois sur 20 graines. Un seuil ajusté sur une
  réalisation du hasard ne mesure pas la propriété qu'il annonce : prendre une
  **médiane sur une douzaine de graines**, et vérifier ce que fait le seuil sur
  les autres avant de l'écrire ;
- ⚠️ **une borne calée sur le corpus.** `jardin/corpus.py` produit quatre
  familles séparables ; il ne dit rien de l'endroit où poser une borne, et il
  n'en a jamais rien dit. Son abstrait écrit 3,25 à 5,18 signes rares pour cent
  mots, sa créature jusqu'à 11,73 — la vraie prose visée en écrit **1,38**. Une
  borne ne se cale que contre du texte réellement écrit. Coût de l'oubli :
  vingt-deux arbres sur trente-cinq, en une nuit. Voir la décision 5.

Compter ce qui est réellement traversé, ne pas le supposer.

---

## Conventions

- **Le code et les commentaires s'écrivent sans accents** (`meme`, `deja`,
  `ecart`). Le tiret cadratin, les guillemets français et `⚠️` restent. Les
  accents sont réservés à `DECISIONS.md`, à ce fichier, et aux chaînes de
  données qui en ont besoin (jeux d'essai, texte affiché à un lecteur).
- **Messages de commit** : le sujet énonce la trouvaille, pas la tâche — « La
  planche des membres montrait le curseur, pas la correction ». Sans accents.
  Le corps donne les chiffres mesurés et ce qu'on a compris. Quand le commit
  sert un chantier, son code vient en tête : « GRA-1 : Chaque famille tenait
  dans un seul niveau de palette » — voir « Pilotage ».
- Tout est en français, y compris les noms de variables.
- Les commentaires disent **pourquoi**, et surtout ce qui a été essayé avant et
  pourquoi ça ne marchait pas. C'est la mémoire du projet.

**Fichiers historiques — ne pas modifier :** `jardin.py`, `abstrait.py`,
`grammaire2.py` à `grammaire6.py`. Ils ont servi à trancher et leurs planches
sont les preuves ; le code de référence est `grammaire.py`, `paysage.py`,
`message.py`. Voir le tableau en fin de `DECISIONS.md`.

---

## Pilotage

Ce qui reste à faire vit dans `pilotage/`, lu par
[`pilote`](https://github.com/Hsbtqemy/pilote) :

```bash
npx github:Hsbtqemy/pilote --port 4125            # le journal, localhost:4125
npx github:Hsbtqemy/pilote verifier               # avant de clore une session
npx github:Hsbtqemy/pilote arreter --port 4125
```

Par npx, pas en dépendance : « aucune dépendance, jamais » vaut aussi pour
l'outillage, et le prix est de quatre secondes par lancement. Port 4125 parce
que 4123 sert le journal d'AGRAFES et 4124 celui de BD_ditor sur cette machine.

Un chantier a sa fiche `pilotage/<CODE>.md` ; une vérification dans un vrai
Word est une passe rejouable dans `pilotage/qa/<nom>.md`. Voir
`pilotage/_TEMPLATE.md`. **`DECISIONS.md` reste la colonne** : une fiche dit ce
qui reste à faire, jamais pourquoi une constante vaut ce qu'elle vaut. Un
arbitrage tranché se consigne là.

IMPORTANT — respecter exactement `## Reste` et les H3 de zone : l'outil ne lit
que ces sections.

- **Un préfixe par domaine**, arrêté le 11 septembre 2026, avant le premier
  commit à en porter un : `GRA` grammaire (forme, couleur) · `PAY` paysage
  (axes, familles, composition) · `ESS` essais et mutations · `PHR` phrases de
  nuit · `VOL` volet, Office.js, le vrai Word. Quatre majuscules au plus :
  `journal-contrat.mjs` ne lit pas au-delà.
- **Le commit de code cite son code en tête de sujet**, puis énonce la
  trouvaille. Sans citation : `0 commit`, aucune date, aucune barre, quel que
  soit le travail. Les commits d'avant le 11 septembre 2026 n'en portent aucun
  et n'en porteront jamais.
- **Le commit de code d'abord, le commit de fiche ensuite, séparément**, sujet
  « Pilotage : … ». Une fiche ne peut pas citer le commit qui la met à jour, et
  les commits qui ne touchent que `pilotage/` sont exclus du datage.
- Fin de session : mettre à jour le `Reste` du chantier travaillé, et son
  `**Arrêté sur**` — l'écran le signale décalé dès qu'il ne cite plus le dernier
  commit de code.
- `statut:` se prend dans `à venir` · `interrompu` · `différé` · `clos` ·
  `livré` · `abandonné`, rien d'autre. Un `différé` dit ce qui le rouvrira.
  `livré` est démenti tant que le dernier commit n'est pas sur `origin/main` —
  c'est aussi ce qui le met chez la personne, puisque chaque push sur `main`
  republie le volet.
- Une case = une affirmation vérifiable, avec son attendu.
- ⚠️ **Ne jamais cocher soi-même une case d'une passe de QA** : la rédiger, la
  rendre, laisser cocher qui l'a jouée.
- Pas de fiche pour une trouvaille traitée en un seul commit.

Attendu du contrôleur : code de retour 0. **Un avertissement est assumé, ne pas
partir le corriger** : « N items ouverts sans `audit:` », sur toutes les fiches.
Elles viennent des points ouverts de `DECISIONS.md`, qui ne portent pas de
tableau de constats ; y pointer `audit:` changerait « manquant » en « inconnu »,
et inventer un audit pour éteindre l'avertissement serait une fausse
déclaration.

---

## Ce qui n'est pas à toi

⚠️ **Le registre `creux` de `phrases.py` est délibérément vide.** C'est le seul
endroit du système où passe la voix de celui qui offre le cadeau. Ne pas
l'écrire, ne pas le remplir « en attendant », ne pas proposer de brouillon.

Restent aussi à l'auteur : atteindre vingt phrases pour que l'écart moyen du
paquet dépasse dix nuits (point ouvert 10), et décider si la transition
germe → famille doit rester une coupure — à regarder dans le vrai add-in, pas
sur planche (point ouvert 12). Leurs fiches, `PHR-1` et `GRA-2`, les suivent ;
elles ne se remplissent pas à la place de l'auteur.
