---
passe: Le premier jour dans un vrai Word
chantier: VOL-1
derniere: 2026-09-11
---

# QA — le paysage dans un vrai Word

Ce qu'aucune batterie ne couvre : la parité prouve le portage, `essais_volet.js` le
câblage contre un hôte simulé, et rien ne prouve que le vrai Word se comporte comme le
faux. Tirée de « Ce qu'il faut regarder en premier » dans `addin/LISEZMOI.md` — si l'une
change, l'autre aussi — plus l'invariant cardinal de `CLAUDE.md`, que rien n'a jamais
éprouvé hors du Word simulé.

À jouer sur Word pour le bureau, pas sur le web : les points portent sur la frappe.
Machine cible : Office LTSC Professionnel Plus 2021, version 2108. Le manifeste se
charge comme le dit `LISEZMOI.md`.

Ne couvre pas la coupure germe → famille (GRA-2) : elle se regarde, elle ne se coche pas.

### Ouverture

- [ ] Le bouton du paysage apparaît dans Word, et le volet s'ouvre sans message d'erreur

### La pousse

- [ ] Quelques lignes neuves écrites volet ouvert : la forme change dans les secondes qui
  suivent, sans aucun autre geste
- [ ] Trois lignes séparées par Maj+Entrée, sans paragraphe neuf : la forme pousse comme
  pour trois paragraphes
- [ ] La même phrase reprise de nombreuses fois de suite : la forme ne s'étend pas —
  l'élément peut mûrir, la silhouette ne grandit pas

### Le collage

- [ ] Un chapitre entier collé : rien ne pousse
- [ ] Le texte collé, retravaillé ensuite : il bascule en écriture, et la forme pousse

### La frappe

- [ ] Sur le document de la thèse entière, volet ouvert, la frappe n'accroche pas

### Les fichiers

- [ ] Un chapitre ouvert, volet ouvert, fermé sans rien taper : Word ne demande pas
  d'enregistrer les modifications
- [ ] Un document neuf, enregistré dans le dossier de la thèse avant d'écrire, volet
  ouvert : ce qui s'affiche — le paysage déjà poussé, ou une forme repartie de zéro —
  est écrit dans `DECISIONS.md`
