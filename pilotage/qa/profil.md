---
passe: Le profil dans un vrai Word
chantier: PHR-2
derniere: 2026-09-11
---

# QA — le prénom et l'accord, dans un vrai Word

Ce que la décision 10 révisée promet, et qu'aucune parité ne peut voir : il n'y a pas
de Python en face d'une question affichée dans le volet, ni de l'adresse que Word
compose. `essais_volet.js` l'éprouve contre un hôte simulé ; cette passe, contre le
vrai.

À jouer une fois PHR-2 porté, sur Word pour le bureau — Office LTSC Professionnel Plus
2021, version 2108. Il faut deux manifestes : l'un dont l'adresse porte
`#prenom=…&accord=…`, l'autre sans rien derrière `volet.html`. Comment les écrire :
`addin/LISEZMOI.md`, « Le prénom et l'accord ».

⚠️ **Jouer d'abord le manifeste qui porte le profil.** La question, une fois posée, ne
revient jamais — c'est voulu. Jouée après l'autre, la première case ne distinguerait
plus rien : le volet se tairait avec ou sans `#`. Sur une machine où il a déjà demandé,
elle ne se joue plus.

Ne couvre pas le message lui-même : il ne sort qu'entre 2 h et 5 h, et se révèle sur
800 mots. Sa forme se vérifie par la parité, pas au bureau.

### L'adresse

- [ ] Le manifeste qui porte le profil : le volet s'ouvre sans rien demander — le `#` a
  survécu à l'adresse que compose Word

### La question

- [ ] Le manifeste sans prénom : le volet le demande à la première ouverture, et à nulle
  autre
- [ ] La question fermée sans réponse : elle ne revient ni à l'ouverture suivante, ni
  après un redémarrage de Word
- [ ] Un prénom composé, « Marie-Ève » : accepté sans signalement
- [ ] Un prénom portant un signe que l'alphabet ne dessine pas : le signe est signalé à
  la saisie, pas perdu en silence

### Le genre

- [ ] Le manifeste sans accord : le genre est demandé à la première ouverture, sous
  « Tu te genres comment ? », avec les trois choix « M · F · NB » — et à nulle autre
- [ ] Seul le genre demandé (le prénom dans le manifeste) : un choix le retire aussitôt
- [ ] Le genre choisi, document fermé sans rien taper : Word ne demande pas
  d'enregistrer les modifications

### Le document

- [ ] Le prénom donné, document fermé sans rien taper : Word ne demande pas
  d'enregistrer les modifications
- [ ] Le prénom donné et quelques lignes écrites, puis les données du site vidées : à
  la réouverture du document, le prénom n'est pas redemandé — il est revenu avec la
  copie du paysage
