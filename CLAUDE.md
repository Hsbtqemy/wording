# Paysage

Un add-in Word qui fait pousser un paysage SVG pendant qu'on écrit une thèse.
C'est un cadeau, pas un outil de productivité : rien ne doit ressembler à une
barre de progression, à un score, ni à un rappel.

**`DECISIONS.md` est la colonne du projet.** Quinze décisions, chacune payée par
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

Les quatre suites, **dans une seule commande**, jamais en parallèle :

```bash
python jardin/essais.py && python jardin/mutations.py \
  && python jardin/parite.py && node addin/essais.js \
  && node addin/parite/mutations.js
```

PowerShell 5.1 n'a pas `&&` : ecrire `a; if ($?) { b }`, ou passer par
l'outil Bash.

Attendu : `30 passes, 0 en echec` · `8/8` · `aucun ecart` · `22 passes` ·
`42/42`.

`addin/essais.js` éprouve le **pont** vers Word contre un Word simulé. C'est la
seule partie du portage qu'aucune parité ne couvre — il n'y a pas de Python en
face — et c'est celle qui porte la décision 2. Elle y a déjà trouvé deux défauts
qui auraient été livrés.

⚠️ **`mutations.py` et `mutations.js` réécrivent les fichiers source sur le
disque** pour vérifier que les essais savent échouer. Deux suites en même temps,
ou une suite tuée, laissent du code muté en place — et la suivante signale des
régressions dans des fichiers que personne n'a touchés. Un filet existe (copie
`.intact` relue au démarrage), il ne protège pas de deux écritures simultanées.
Après coup, vérifier `git status`.

Durée mesurée de l'enchaînement complet : **3 min 46**. Assez long pour donner
envie de paralléliser, ce qu'il ne faut surtout pas faire — `mutations` relance
`essais` huit fois, et `mutations.js` relance la parité ou les essais du pont
quarante-deux fois.

`addin/parite/cas.json` et `jardin/planches.html` sont des produits de
compilation, ignorés par git et régénérés en quelques secondes.

## Comment on teste ici

**Une batterie qui passe ne prouve rien tant qu'on n'a pas montré qu'elle sait
échouer.** C'est à ça que servent les deux `mutations` : elles réintroduisent
des régressions réellement commises et vérifient qu'on les rattrape. Une
mutation qui ÉCHAPPE est un trou dans les cas, pas une bonne nouvelle.

Trois pièges déjà rencontrés, à ne pas refaire :

- un essai qui **recalcule lui-même** la valeur attendue teste sa propre
  arithmétique, pas le code ;
- un essai qui **compare à la constante** qu'on est en train de casser s'adapte
  à la panne ;
- un cahier qui a l'air complet et **ne traverse jamais** le mécanisme surveillé
  — sur 616 appels, le verdict `frappe` n'apparaissait pas une fois.

Compter ce qui est réellement traversé, ne pas le supposer.

---

## Conventions

- **Le code et les commentaires s'écrivent sans accents** (`meme`, `deja`,
  `ecart`). Le tiret cadratin, les guillemets français et `⚠️` restent. Les
  accents sont réservés à `DECISIONS.md`, à ce fichier, et aux chaînes de
  données qui en ont besoin (jeux d'essai, texte affiché à un lecteur).
- **Messages de commit** : le sujet énonce la trouvaille, pas la tâche — « La
  planche des membres montrait le curseur, pas la correction ». Sans accents.
  Le corps donne les chiffres mesurés et ce qu'on a compris.
- Tout est en français, y compris les noms de variables.
- Les commentaires disent **pourquoi**, et surtout ce qui a été essayé avant et
  pourquoi ça ne marchait pas. C'est la mémoire du projet.

**Fichiers historiques — ne pas modifier :** `jardin.py`, `abstrait.py`,
`grammaire2.py` à `grammaire6.py`. Ils ont servi à trancher et leurs planches
sont les preuves ; le code de référence est `grammaire.py`, `paysage.py`,
`message.py`. Voir le tableau en fin de `DECISIONS.md`.

---

## Ce qui n'est pas à toi

⚠️ **Le registre `creux` de `phrases.py` est délibérément vide.** C'est le seul
endroit du système où passe la voix de celui qui offre le cadeau. Ne pas
l'écrire, ne pas le remplir « en attendant », ne pas proposer de brouillon.

Restent aussi à l'auteur : atteindre vingt phrases pour que l'écart moyen du
paquet dépasse dix nuits (point ouvert 10), et décider si la transition
germe → famille doit rester une coupure — à regarder dans le vrai add-in, pas
sur planche (point ouvert 12).
