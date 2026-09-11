// L'inventaire de CE depot : ce que l'outil ne peut pas deviner, et rien d'autre.
// Facultatif — sans lui on garde les chantiers, les passes et le controleur, et on
// perd les masses par aire.

export default {
  // Une seule ref d'integration : on travaille sur main, et chaque push sur main
  // republie le volet sur GitHub Pages. Un chantier `livre` dont le dernier commit
  // n'est pas sur origin/main n'est donc pas chez la personne — et l'ecran le dement.
  refs: ["origin/main"],

  // Une aire = un prefixe de chemin ; le PREMIER qui matche l'emporte, d'ou les
  // fichiers nommes avant les dossiers qui les contiennent. Plusieurs prefixes
  // peuvent porter le meme nom : ils s'additionnent.
  //
  // Les deux langages sont separes expres : `jardin/` est la specification, `addin/`
  // le livrable, et quand ils divergent c'est le JavaScript qui a un bug. Leurs
  // batteries sont detachees de leur code, parce que tout ce qui entre dans essais.py
  // est multiplie par soixante-cinq : sa masse se lit a part.
  //
  // Les planches aussi : un SVG de planche se reecrit en entier a chaque rendu, et
  // noierait la courbe de la spec.
  aires: [
    ["spec/essais",     "jardin/essais.py"],
    ["spec/essais",     "jardin/banc.py"],
    ["spec/essais",     "jardin/stabilite.py"],
    ["spec/essais",     "jardin/mutations.py"],
    ["spec/essais",     "jardin/parite.py"],
    ["planches",        "jardin/planche_"],
    ["spec",            "jardin/"],
    ["livrable/essais", "addin/essais.js"],
    ["livrable/essais", "addin/essais_volet.js"],
    ["livrable/essais", "addin/parite/"],
    ["livrable",        "addin/"],
    ["décisions",       "DECISIONS.md"],
    ["décisions",       "CLAUDE.md"],
    ["dossier",         "pilotage/"]
  ]

  // Pas de `veille`, et c'est une decision. Elle veut UN fichier et un seuil en
  // lignes ; la seule limite reelle du depot n'a pas cette forme. Ce qui coute ici,
  // c'est le TEMPS d'essais.py, multiplie par soixante-cinq — des lignes ne le
  // mesurent pas — et le poids du livrable se mesure sans se borner (decision 13).
  // Un seuil pose pour remplir le champ serait une borne calee sur rien :
  // exactement ce que CLAUDE.md interdit.
  //
  // Pas de `documentation` non plus : `dossier` doit etre un DOSSIER (l'outil teste
  // `startsWith(dossier + "/")`), et les decisions vivent dans DECISIONS.md, a la
  // racine. Consequence : un commit qui cite un code et ne touche que DECISIONS.md
  // compte comme du code, et dement un `a venir`. C'est juste ici — trancher un
  // arbitrage, c'est commencer le chantier.
};
