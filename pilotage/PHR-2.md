---
chantier: PHR-2
statut: à venir
---

# PHR-2 — le message de nuit et les phrases, dans l'add-in

**Point de départ** — décision 13 : « Reste à porter : le message et les phrases. »
`jardin/message.py` et `jardin/phrases.py` n'ont pas de jumeau dans `addin/src/`, et
`volet.js` n'importe ni l'un ni l'autre. Le seul « nuit » du livrable est la palette des
plants écrits entre 2 h et 5 h. Le message de nuit, le paquet battu et le routage par
événement de la décision 15 n'existent qu'en Python.

## Reste

### Portage
- [ ] `addin/src/message.js` porte `message.py` — alphabet en segments, tracé à la main,
  révélation — et la parité le compare au Python sans écart
- [ ] `addin/src/phrases.js` porte `phrases.py` — registres, routage par événement,
  paquet battu — et la parité le compare au Python sans écart
- [ ] Chaque mutation que `jardin/mutations.py` porte sur `phrases.py` ou `message.py` a
  sa jumelle dans `addin/parite/mutations.js`, et la batterie l'attrape

### Câblage
- [ ] Le volet affiche le message de nuit dans les conditions de la décision 10, et
  `essais_volet.js` le vérifie contre l'hôte simulé
- [ ] Un registre vide retombe sur le paquet dans le volet comme en Python : `CREUX`
  vide ne casse rien (décision 15)
- [ ] Le poids ajouté à ce que charge le volet est mesuré, brut et compressé, et écrit
  dans le corps du commit

## Contexte

La décision 13 appelait le message « un easter egg » dont l'add-in se passe. C'était
vrai du livrable ; ça ne l'est plus du cadeau, depuis que PHR-1 existe : sans ce
portage, ni les phrases de l'auteur ni le registre `CREUX` n'ont de chemin jusqu'à la
personne. Écrire vingt phrases avant ce chantier, c'est les écrire pour le banc d'essai.

Le hasard du message est dans le livrable, donc c'est le **générateur** qui se porte,
pas ses tirages — `alea.js` existe déjà pour ça (décision 13, « Le générateur se porte,
le corpus non »). Même document, même graine, même figure.

⚠️ Porter `phrases.py`, c'est copier ses registres tels qu'ils sont. `CREUX` reste vide
dans le port comme dans la spec : ce chantier n'écrit pas une phrase (`CLAUDE.md`, « Ce
qui n'est pas à toi »).
