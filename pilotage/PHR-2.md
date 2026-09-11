---
chantier: PHR-2
statut: interrompu
---

# PHR-2 — le message de nuit et les phrases, dans l'add-in

**Arrêté sur** — `92ad1cb`, 11 septembre : le câblage est fait et éprouvé contre
l'hôte simulé — le profil lu derrière le `#`, la question du prénom posée une fois, le
message de nuit dans le ciel du volet, révélé aux mots et non à l'heure (`286f23a`).
Une relecture à froid y a trouvé trois promesses sans essai, et un essai du `#` qui ne
lisait rien : 38 essais du volet, 137 mutations. Le volet charge 74,7 Ko compressés au
lieu de 61,6. La question reste muette tant que son texte n'est pas écrit (PHR-1). La
suite est la zone Vrai Word : la passe `qa/profil.md` sur l'Office LTSC 2021, et
`LISEZMOI.md` pour mettre le profil dans le manifeste.

## Reste

### Spécification
- [x] Dans `phrases.py`, une phrase qui s'accorde porte ses trois formes
  `{fort|forte|fort.e}` et l'accord choisit ; sans prénom les nominatives sortent du
  paquet, sans accord les phrases qui s'accordent aussi — et `essais.py` le vérifie
- [x] L'alphabet de `message.py` dessine « - », et `signes_hors_alphabet` laisse
  passer un prénom composé

### Portage
- [x] `addin/src/message.js` porte `message.py` — alphabet en segments, tracé à la main,
  révélation — et la parité le compare au Python sans écart
- [x] `addin/src/phrases.js` porte `phrases.py` — registres, routage par événement,
  paquet battu — et la parité le compare au Python sans écart
- [x] Chaque mutation que `jardin/mutations.py` porte sur `phrases.py` ou `message.py` a
  sa jumelle dans `addin/parite/mutations.js`, et la batterie l'attrape

### Câblage
- [x] Le volet lit `prenom` et `accord` derrière le `#` de son adresse, et
  `essais_volet.js` le vérifie
- [x] Sans prénom dans l'adresse, le volet le demande une fois ; ignorée, la question
  n'est jamais reposée — `essais_volet.js` le vérifie
- [x] Répondre n'écrit rien dans le document : le prénom part avec la prochaine copie du
  paysage — `essais_volet.js` le vérifie
- [x] Un signe du prénom que l'alphabet ne dessine pas est signalé à la saisie
- [x] Le volet affiche le message de nuit dans les conditions de la décision 10, et
  `essais_volet.js` le vérifie contre l'hôte simulé
- [x] Un registre vide retombe sur le paquet dans le volet comme en Python : `CREUX` vide
  ne casse rien (décision 15)
- [x] Le poids ajouté à ce que charge le volet est mesuré, brut et compressé, et écrit
  dans le corps du commit

### Vrai Word
- [ ] La passe `qa/profil.md` est jouée sur l'Office LTSC 2021, et chacune de ses cases
  est cochée par qui l'a jouée
- [ ] `addin/LISEZMOI.md` dit comment mettre le profil dans le manifeste, aux deux
  adresses du volet

## Contexte

Point de départ, avant `fcb55da` — décision 13 : « Reste à porter : le message et les
phrases. » `jardin/message.py` et `jardin/phrases.py` n'ont pas de jumeau dans
`addin/src/`, et `volet.js` n'importe ni l'un ni l'autre. Le seul « nuit » du livrable
est la palette des plants écrits entre 2 h et 5 h. `parite.py` n'importe aucun des deux
modules, et deux mutations seulement les visent : le filet est à construire avec le
portage, pas après.

La décision 13 appelait le message « un easter egg » dont l'add-in se passe. C'était
vrai du livrable ; ça ne l'est plus du cadeau, depuis que PHR-1 existe : sans ce
portage, ni les phrases de l'auteur ni le registre `CREUX` n'ont de chemin jusqu'à la
personne. Écrire vingt phrases avant ce chantier, c'est les écrire pour le banc d'essai.

Le hasard du message est dans le livrable, donc c'est le **générateur** qui se porte,
pas ses tirages — `alea.js` existe déjà pour ça (décision 13, « Le générateur se porte,
le corpus non »). Même document, même graine, même figure.

La spécification change avant le portage, et dans cet ordre : c'est le Python qui fait
foi, et l'on ne porte pas un modèle d'accord qu'on sait faux.

⚠️ Porter `phrases.py`, c'est copier ses registres tels qu'ils sont. `CREUX` reste vide
dans le port comme dans la spec : ce chantier n'écrit pas une phrase (`CLAUDE.md`, « Ce
qui n'est pas à toi »).

⚠️ Le texte de la question du prénom est de la même main (PHR-1). Tant qu'il n'est pas
écrit, la question ne s'affiche pas, et le prénom ne vient que du manifeste — un texte
provisoire serait justement l'écrire à sa place.
