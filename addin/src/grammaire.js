/**
 * La grammaire graphique, portage de jardin/grammaire.py.
 *
 * Regle qui tient tout (decision 9) : la couleur ne touche jamais la structure,
 * uniquement l'etoffage. Le squelette reste a l'encre dans les quatre familles.
 * C'est cette seule regle qui preserve l'unite etablie a la decision 8, et
 * c'est pour ca que trait() porte un drapeau `structure` — marquee dans la
 * donnee, la regle devient une invariante qu'un essai peut tenir.
 *
 * Ce qui n'est PAS porte : les planches. Elles appartiennent au banc d'essai et
 * restent en Python, avec les interrupteurs de comparaison qu'elles pilotent.
 * Le code de production n'a jamais eu besoin de les toucher.
 *
 * ATTENTION A L'ORDRE DES TIRAGES. Tout ce fichier consomme le meme generateur
 * que le Python, dans le meme ordre (voir alea.js). Deplacer un rng.uniform()
 * d'une ligne, ou evaluer deux arguments dans l'autre sens, ne casse rien de
 * visible : la figure reste plausible, elle est simplement AUTRE. Les appels
 * sont donc ecrits dans l'ordre exact du Python, meme quand une variable
 * intermediaire serait plus lisible.
 */

import { Alea } from "./alea.js";
import { blake2s_hex } from "./blake2s.js";
import { arrondi } from "./traits.js";

export const TRAIT = "#2c3230";
export const FOND = "#faf8f4";
export const EPAISSEUR = 1.5;
export const SEGMENT = 26.0;

// --------------------------------------------------------------------------
// Couleur (decision 9)
// --------------------------------------------------------------------------
// Cinq tons par palette : une plante de printemps porte plusieurs verts sans
// que rien ne devienne aleatoire — meme document, meme graine, meme figure.
export const PALETTES = {
  hiver: ["#5b7a8c", "#8ba3ad", "#43596b", "#6e8fa0", "#9fb3ba"],
  printemps: ["#6d9450", "#96b56a", "#4f7a3f", "#7fa85e", "#adc47f"],
  ete: ["#c08a3e", "#d4aa5c", "#a86f2d", "#caa04e", "#b8823a"],
  automne: ["#a3542f", "#bd7448", "#7d3d22", "#b0603a", "#8e4a28"],
  // La palette de nuit de la v5 etait un bleu-gris a deux doigts de l'hiver :
  // sur planche, "3H DU MATIN" et "HIVER" etaient indiscernables, et l'easter
  // egg ressemblait a une decoloration. Le violet de la v6 n'appartient a
  // aucune saison, ce qui est exactement ce qu'on lui demande.
  nuit: ["#8d84c4", "#a99ede", "#7a6fb0", "#9a90d2", "#b8aeea"],
};

// Debut de chaque saison, en jours. L'hiver enjambe la fin de l'annee.
export const SAISONS = [
  ["printemps", 80, 172], ["ete", 172, 264],
  ["automne", 264, 355], ["hiver", 355, 80 + 365],
];
export const FONDU = 12;          // jours de transition, DE PART ET D'AUTRE
export const HEURE_NUIT = [2, 5];

/** Le modulo de Python : jamais negatif. */
function mod(a, n) {
  return ((a % n) + n) % n;
}

function _saison(jour) {
  const j = mod(jour, 365);
  for (const [nom, debut, fin] of SAISONS) {
    if (debut <= j && j < fin) return [nom, debut, fin];
  }
  return ["hiver", 355, 80 + 365];          // janvier : j < 80
}

function _melange(c1, c2, f) {
  let sortie = "#";
  for (const i of [1, 3, 5]) {
    const a = parseInt(c1.slice(i, i + 2), 16);
    const b = parseInt(c2.slice(i, i + 2), 16);
    // int() en Python tronque vers zero, pas vers le bas.
    const v = Math.trunc(a + (b - a) * f);
    sortie += v.toString(16).padStart(2, "0");
  }
  return sortie;
}

const NOMS_SAISONS = SAISONS.map((s) => s[0]);

function _suivante(nom) {
  return NOMS_SAISONS[mod(NOMS_SAISONS.indexOf(nom) + 1, NOMS_SAISONS.length)];
}

function _precedente(nom) {
  return NOMS_SAISONS[mod(NOMS_SAISONS.indexOf(nom) - 1, NOMS_SAISONS.length)];
}

/**
 * Le ton numero `ton` de la palette du jour donne.
 *
 * Le fondu court sur FONDU jours DES DEUX COTES de chaque frontiere : la v5 ne
 * le posait que du cote tardif et plafonnait a 50 %, la v6 l'avait perdu. Une
 * plante a cheval sur deux saisons doit porter les deux, sinon une date a un
 * jour d'ecart change brutalement de palette.
 */
export function palette(jour, ton = 0, nuit = false) {
  ton = mod(ton, 5);
  if (nuit) return PALETTES.nuit[ton];

  let j = mod(jour, 365);
  const [nom, debut, fin] = _saison(jour);
  if (nom === "hiver" && j < 80) j += 365;   // on se replace dans la fenetre

  const couleur = PALETTES[nom][ton];
  if (j - debut < FONDU) {
    const f = 0.5 * (1 - (j - debut) / FONDU);
    return _melange(couleur, PALETTES[_precedente(nom)][ton], f);
  }
  if (fin - j < FONDU) {
    const f = 0.5 * (1 - (fin - j) / FONDU);
    return _melange(couleur, PALETTES[_suivante(nom)][ton], f);
  }
  return couleur;
}

/**
 * Le contexte chromatique d'un plant.
 *
 * LES VRAIES DATES. La v4 donnait a chaque tour de ville la date
 * `jour + rang x 47` : un decalage invente, donc une ville dont les tours
 * affichaient des saisons qui n'ont jamais eu lieu, alors que la decision 9
 * fait porter la teinte par la date d'ecriture. Ici les dates viennent du
 * plant — {jour: mots} — et un tour tire la sienne dans cette distribution,
 * ponderee par les mots.
 *
 * L'ARBITRAGE LAISSE OUVERT AU POINT 9. La date garde la TEINTE ; le texte
 * prend le NOMBRE DE TONS tires dans la palette. Un segment lexicalement riche
 * deploie les cinq verts du printemps, un segment monotone n'en tire qu'un.
 * Aucune variable ne porte deux choses.
 */
export class Teinte {
  constructor(dates = null, nuit = false, richesse = 0.5) {
    this.dates = dates && dates.length ? dates.map((d) => [d[0], d[1]]) : [[200, 1]];
    this.nuit = Boolean(nuit);
    // ⚠️ x5 ET Math.min(4, ...), PAS x4. Avec x4 le cinquieme ton ne sort
    // qu'a richesse == 1,000 exactement — au-dessus du plafond reel
    // (0,931 sur 120 plants), donc jamais. Pire : chaque famille tenait
    // dans UN seul niveau — le vegetal toujours 3, l'abstrait toujours 4
    // — et la richesse ne disait rien A L'INTERIEUR d'une famille, ce
    // qui est precisement ce qu'elle est la pour dire. Voir grammaire.py.
    this.n_tons = 1 + Math.min(4, Math.trunc(Math.min(1.0, Math.max(0.0, richesse)) * 5));
    this._poids = [];
    let cumul = 0;
    for (const [, poids] of this.dates) {
      cumul += Math.max(1, poids);
      this._poids.push(cumul);
    }
    this._total = cumul;
  }

  /** Raccourci : un plant ecrit d'un seul jet. */
  static du_jour(jour = 200, heure = 14, richesse = 0.5) {
    return new Teinte([[jour, 1]], HEURE_NUIT[0] <= heure && heure < HEURE_NUIT[1],
                      richesse);
  }

  /** Une vraie date du plant, tiree au poids des mots ecrits ce jour-la. */
  jour(rng) {
    const cible = rng.randrange(this._total);
    for (let i = 0; i < this._poids.length; i++) {
      if (cible < this._poids[i]) return this.dates[i][0];
    }
    return this.dates[this.dates.length - 1][0];
  }

  ton(rng, jour = null) {
    const j = jour === null ? this.jour(rng) : jour;
    return palette(j, rng.randrange(this.n_tons), this.nuit);
  }
}

/**
 * La graine vient du document, jamais de l'horloge : c'est ce qui garantit
 * qu'on retrouve la meme figure a chaque ouverture du fichier.
 *
 * Le vrai blake2s, pas le murmur de l'empreinte : cette valeur-la determine la
 * figure entiere, et deux paysages differents pour le meme document feraient
 * mentir les planches.
 */
export function graine_du_document(nom) {
  return parseInt(blake2s_hex(nom, 4), 16);
}

// --------------------------------------------------------------------------
// La primitive
// --------------------------------------------------------------------------
/**
 * Le formatage de Python : arrondi correct, demis exacts vers le pair, et le
 * SIGNE DU ZERO.
 *
 * Ce dernier n'est pas une coquetterie. Une branche qui repart exactement a
 * l'horizontale donne un y de -0,02 ; Python ecrit « -0.0 », et JavaScript
 * ecrirait « 0.0 » — non pas parce que toFixed se trompe, (-0.02).toFixed(1)
 * donne bien « -0.0 », mais parce qu'on passe par un nombre intermediaire, et
 * que toFixed appele sur le zero negatif rend « 0.0 ». Un caractere d'ecart sur
 * un SVG de trente mille, et les deux figures ne sont plus comparables.
 */
export function fixe(x, n) {
  const v = arrondi(x, n);
  if (v === 0 && (x < 0 || Object.is(x, -0))) return "-" + (0).toFixed(n);
  return v.toFixed(n);
}

/**
 * Un segment, et rien d'autre. L'unite des quatre familles ne vient pas d'un
 * style plaque par-dessus mais de cette primitive partagee (decision 8).
 */
export class Toile {
  constructor() {
    this.segments = [];
    this.noeuds = [];
    // Cadre impose. Sans lui, une figure qui se revele progressivement est
    // centree sur ce qui est DEJA visible : chaque element nouveau recadre
    // l'ensemble et fait bouger tout ce qui etait deja trace.
    this.cadre = null;
  }

  /**
   * `structure` marque le squelette porteur — ce qui tient la forme.
   *
   * La decision 9 dit que la couleur ne touche JAMAIS la structure. Tant que ce
   * n'etait qu'une intention dans les commentaires, on ne pouvait la verifier
   * qu'en comptant les traits a l'encre — et un vegetal dont on colorait les
   * branches passait quand meme, parce que l'anastomose restait noire.
   */
  trait(x1, y1, x2, y2, m = 0.0, col = null, structure = false) {
    this.segments.push([x1, y1, x2, y2, m, col || TRAIT, structure]);
  }

  noeud(x, y, m, col = null) {
    // Tardifs et petits : en v1 ils devenaient une rougeole qui ecrasait tout.
    if (m > 0.55) this.noeuds.push([x, y, m, col || TRAIT]);
  }

  bbox() {
    if (!this.segments.length) return [0, 0, 1, 1];
    let x0 = Infinity; let y0 = Infinity; let x1 = -Infinity; let y1 = -Infinity;
    for (const s of this.segments) {
      x0 = Math.min(x0, s[0], s[2]);
      x1 = Math.max(x1, s[0], s[2]);
      y0 = Math.min(y0, s[1], s[3]);
      y1 = Math.max(y1, s[1], s[3]);
    }
    return [x0, y0, x1, y1];
  }

  _corps(k, ox, oy) {
    const out = [`<g transform="translate(${fixe(ox, 1)},${fixe(oy, 1)}) scale(${fixe(k, 3)})">`];
    for (const [a, b, c, d, m, col] of this.segments) {
      const e = EPAISSEUR * (1 + 1.7 * m) / Math.max(k, 0.35);
      out.push(`<line x1="${fixe(a, 1)}" y1="${fixe(b, 1)}" x2="${fixe(c, 1)}" y2="${fixe(d, 1)}" `
        + `stroke="${col}" stroke-width="${fixe(e, 2)}" stroke-linecap="round"/>`);
    }
    for (const [px, py, m, col] of this.noeuds) {
      const r = (1.0 + 1.8 * m) / Math.max(k, 0.35);
      out.push(`<circle cx="${fixe(px, 1)}" cy="${fixe(py, 1)}" r="${fixe(r, 2)}" `
        + `fill="${col}" opacity="${fixe(0.35 + 0.5 * m, 2)}"/>`);
    }
    return out.join("") + "</g>";
  }

  /**
   * Pose la figure a un endroit choisi, base posee sur (x, y_base).
   *
   * svg() cadre dans une case — c'est ce qu'il faut pour une planche, pas pour
   * un paysage, ou chaque plant doit tenir sa place et son echelle par rapport
   * aux autres.
   */
  pose(x, y_base, echelle) {
    const [x0, , x1, y1] = this.cadre || this.bbox();
    const k = echelle;
    return this._corps(k, x - (x0 + x1) / 2 * k, y_base - y1 * k);
  }

  hauteur() {
    const [, y0, , y1] = this.cadre || this.bbox();
    return Math.max(y1 - y0, 1);
  }

  largeur() {
    const [x0, , x1] = this.cadre || this.bbox();
    return Math.max(x1 - x0, 1);
  }

  svg(cx, cy, cw, ch) {
    const [x0, y0, x1, y1] = this.cadre || this.bbox();
    const w = Math.max(x1 - x0, 1);
    const h = Math.max(y1 - y0, 1);
    const k = Math.min(1.0, (cw - 26) / w, (ch - 26) / h);
    return this._corps(k, cx + cw / 2 - (x0 + w / 2) * k, cy + ch / 2 - (y0 + h / 2) * k);
  }
}

// --------------------------------------------------------------------------
// Ce que le texte dit de la FORME (et non de la couleur ni de la taille).
//
// Les trois curseurs de la creature et la geometrie de l'abstrait existaient
// depuis les v4-v5, mais RIEN NE LES ALIMENTAIT : toutes les creatures etaient
// donc la meme creature, tous les abstraits le meme cristal — un paysage de
// vingt-sept plants n'aurait montre que quatre formes repetees.
//
// Chaque correspondance ci-dessous doit dire quelque chose de vrai. Ce ne sont
// pas des branchements arbitraires : c'est la ou le texte devient anatomie.
// --------------------------------------------------------------------------
export const TRAITS_NEUTRES = {
  longueur: 0.5, rythme: 0.5, subordination: 0.5, regularite: 0.5,
  structure: 0.5, dialogue: 0.5, interrogation: 0.5,
  diversite: 0.5, richesse: 0.5, ponctuation_rare: 0.5,
};

function _traits(traits) {
  const t = { ...TRAITS_NEUTRES };
  if (traits) {
    for (const [k, v] of Object.entries(traits)) {
      if (k in TRAITS_NEUTRES) t[k] = v;
    }
  }
  return t;
}

// Plafond GLOBAL du feuillage. Le correctif de la v4 bornait chaque bouquet,
// mais le NOMBRE de bouquets croit en 2^profondeur : le feuillage densifiait
// quand meme et fusionnait en aplat, masquant l'anastomose qu'on venait
// d'ajouter. Meme remede que les cycles de 5 000 mots — plafonner le total et
// le repartir, jamais l'unite locale.
export const BUDGET_FEUILLAGE = 210;

// A false, les membres reprennent la longueur ABSOLUE de la v5 : une bete
// gracile et une bete massive recoivent alors exactement les memes pattes
// (rapport 1,00 contre 3,48). Sert uniquement aux planches d'avant/apres, qui
// restent en Python — le code de production ne le touche pas.
export const MEMBRES_PROPORTIONNELS = true;

// --------------------------------------------------------------------------
// Vegetal — il se ramifie
// --------------------------------------------------------------------------
/**
 * Dans quel ordre ce rameau sort, entre 0 et 1.
 *
 * Le bit INVERSE (van der Corput). Pris dans l'ordre naturel, les rameaux
 * apparaitraient de gauche a droite et l'arbre pousserait d'un cote ; tires au
 * hasard, ils changeraient de place a chaque redessin. Le bit inverse les
 * disperse dans toute la couronne ET fixe l'ordre une fois pour toutes.
 *
 * C'est cette fixite qui compte : un rameau sorti ne rentre jamais quand
 * l'extension monte, donc la forme ne peut que croitre — decision 1.
 */
function _rang_de_pousse(lignee) {
  // 31 - clz32 est le bit_length de Python, moins un.
  const niveau = 31 - Math.clz32(lignee);
  if (niveau <= 0) return 0.0;
  const index = lignee - (1 << niveau);
  let inverse = 0;
  for (let i = 0; i < niveau; i++) inverse = (inverse << 1) | ((index >> i) & 1);
  return inverse / (1 << niveau);
}

export function vegetal(t, extension, maturite, graine, teinte = null, traits = null) {
  const rng = new Alea(graine);
  const m = maturite;
  const tt = teinte || Teinte.du_jour();
  const tr = _traits(traits);
  // Une phrase qui se subordonne se ramifie : la subordination ouvre l'angle.
  // Un texte regulier fait un arbre symetrique ; un texte irregulier penche.
  let ouverture = 0.26 + tr.subordination * 0.42;
  const dissymetrie = (1.0 - tr.regularite) * 0.30;
  // Des phrases longues font de longues entre-noeuds.
  let entre_noeuds = 0.72 + tr.longueur * 0.34;
  // ⚠️ L'AXE, ET C'EST LA QU'UNE THESE SE DISTINGUE D'ELLE-MEME.
  //   Voir grammaire.py : `structure` est le trait qui bouge le plus dans une
  //   these et le vegetal l'ignorait. Il devient la dominance apicale.
  const axe = tr.structure;
  // Le feuillage suit le vocabulaire. Le NOMBRE de feuilles ne bouge pas.
  const eventail = 0.22 + tr.richesse * 0.36;
  const frisson = 0.05 + tr.richesse * 0.14;
  // ⚠️ LE PORT SE TIRE AU SORT, LA TAILLE JAMAIS. Voir grammaire.py.
  const port = rng.uniform(-1.0, 1.0);
  ouverture *= 1.0 - port * 0.7;
  entre_noeuds *= 1.0 + port * 0.02;
  // ⚠️ LA PROFONDEUR EST FRACTIONNAIRE, et c'est tout le sujet.
  //
  //   Elle valait « 4 + int(extension * 3.0) » : un entier, donc QUATRE formes sur
  //   toute la vie d'un plant. L'extension n'entrait dans l'arbre que par la, et
  //   entre deux crans, ecrire ne changeait rien du tout. A 2 500 mots par plant
  //   cela faisait un changement visible toutes les 625 — deux pages — la ou la
  //   creature en offre onze fois plus.
  //
  //   On ne peut pas ajouter des niveaux : ils doublent le nombre de branches. On
  //   ouvre donc le DERNIER, rameau par rameau. La partie entiere donne les niveaux
  //   pleins, la decimale la proportion du dernier qui est sortie.
  //
  //   Un rameau pas encore sorti reste un BOURGEON — un bouquet de feuilles — au
  //   lieu de disparaitre : la couronne n'a jamais de trou, et pousser consiste a
  //   ouvrir un bourgeon en rameau, ce qui est monotone.
  //
  //   Aux quatre valeurs entieres l'arbre est EXACTEMENT celui d'avant : le
  //   changement raffine l'entre-deux, il ne redessine pas ce qui existait.
  const prof_max = 4.0 + extension * 3.0;
  // Le compte des pointes, qui donne le budget de feuillage. En ENTIERS :
  // 2 ** un flottant n'a pas forcement la meme derniere decimale en Python
  // et en JavaScript, et la parite se joue exactement la.
  const niveaux = Math.trunc(prof_max);
  const reste = prof_max - niveaux;
  const pointes = (1 << niveaux) + Math.trunc(reste * (1 << niveaux));
  // ⚠️ LE BUDGET SE REPARTIT, IL NE SE DIVISE PAS.
  //
  //   C'etait « BUDGET_FEUILLAGE // pointes », le meme nombre de feuilles pour
  //   chaque bouquet. Un quotient entier n'est pas monotone : 52 pointes a 4
  //   traits font 208 traits, 53 pointes a 3 traits en font 159. Le feuillage
  //   RECULAIT donc au moment ou l'arbre gagnait un rameau — mesure sur la vie
  //   d'un plant : 271 -> 223, 300 -> 235, puis 331 -> 230 traits, soit un tiers
  //   de la couronne perdu d'un seul pas.
  //
  //   C'est la decision 1 violee, et ce n'est pas la profondeur fractionnaire qui
  //   l'a introduit : la version entiere reculait deja au dernier cran de chaque
  //   plant, 192 traits a la profondeur 6 contre 128 a la profondeur 7. L'arbre
  //   s'eclaircissait exactement quand il s'achevait. C'est vraisemblablement ce
  //   qu'on voyait dans le vrai Word et qu'on prenait pour un rapetissement.
  //
  //   On donne donc a chaque pointe sa part ENTIERE du budget, et une feuille de
  //   plus a la fraction des pointes que le rang de pousse designe — le meme ordre
  //   que celui des rameaux, pour que le supplement soit disperse et non groupe
  //   d'un cote. Le total suit le budget au lieu de sauter par paliers.
  const part = BUDGET_FEUILLAGE / pointes;
  const plafond = 3 + Math.trunc(m * 3);
  const noeuds = [];

  function branche(x, y, angle, lg, prof, lignee) {
    // Le dernier niveau est fractionnaire : ce rameau-ci n'est peut-etre pas
    // encore sorti. Il reste alors un bourgeon.
    if (prof > 0.0 && prof < 1.0 && _rang_de_pousse(lignee) >= prof) prof = 0.0;
    if (prof <= 0 || lg < 3.0) {
      const n_feuilles = Math.max(1, Math.min(plafond, Math.trunc(part)
        + (_rang_de_pousse(lignee) < part - Math.trunc(part) ? 1 : 0)));
      for (let i = 0; i < n_feuilles; i++) {
        const a = angle + (i - n_feuilles / 2) * eventail
          + rng.uniform(-frisson, frisson);
        const r = lg * (1.3 + 0.8 * m);
        t.trait(x, y, x + Math.cos(a) * r, y + Math.sin(a) * r, m * 0.55, tt.ton(rng));
      }
      return;
    }
    const x2 = x + Math.cos(angle) * lg;
    const y2 = y + Math.sin(angle) * lg;
    t.trait(x, y, x2, y2, m, null, true);          // squelette
    t.noeud(x2, y2, m, tt.ton(rng));
    noeuds.push([x2, y2, lignee]);
    const ouv = ouverture * rng.uniform(0.85, 1.15);
    // Lequel des deux rameaux prolonge l'axe. Il ALTERNE avec la lignee :
    // fixe d'un cote, l'axe derivait et l'arbre partait en biais.
    const meneur = (lignee & 1) ? -1 : 1;
    for (const s of [-1, 1]) {
      const biais = 1.0 + s * dissymetrie;
      const tenue = s === meneur ? 1.0 - axe * 0.72 : 1.0 + axe * 0.4;
      const allonge = s === meneur ? 1.0 + axe * 0.22 : 1.0;
      // Le tirage de la longueur est evalue AVANT la descente, comme en
      // Python ou c'est un argument. L'ordre de consommation est la figure.
      const lg2 = lg * entre_noeuds * allonge * rng.uniform(0.94, 1.06);
      branche(x2, y2, angle + s * ouv * biais * tenue, lg2, prof - 1,
              lignee * 2 + (s > 0 ? 1 : 0));
    }
  }

  // Le port de l'arbre : inclinaison du tronc et vigueur, tires sur la graine
  // du document. Deux plants du meme texte doivent rester deux arbres, pas
  // deux exemplaires du meme arbre.
  const angle0 = -Math.PI / 2 + rng.uniform(-0.16, 0.16);
  const lg0 = SEGMENT * (1.4 + tr.longueur * 0.7) * rng.uniform(0.85, 1.18);
  branche(100, 200, angle0, lg0, prof_max, 1);

  // ANASTOMOSE : des branches de lignees differentes se rejoignent. C'est ce
  // seul ajout qui cree des boucles fermees, donc de la profondeur — sans lui
  // le vegetal est un graphe acyclique et ressemble a un schema.
  const seuil = SEGMENT * (0.5 + 0.45 * m);
  let faits = 0;
  for (let i = 0; i < noeuds.length; i++) {
    const [x1, y1, l1] = noeuds[i];
    for (let j = i + 1; j < noeuds.length; j++) {
      const [x2, y2, l2] = noeuds[j];
      if (l1 === l2 || faits > 30 * m + 6) continue;
      const d = Math.hypot(x2 - x1, y2 - y1);
      if (6 < d && d < seuil && rng.random() < 0.45) {
        t.trait(x1, y1, x2, y2, m * 0.55, null, true);
        faits += 1;
      }
    }
  }
}

// --------------------------------------------------------------------------
// Architecture — il s'empile
// --------------------------------------------------------------------------
export function architecture(t, extension, maturite, graine, teinte = null, traits = null) {
  const rng = new Alea(graine);
  const m = maturite;
  const tt = teinte || Teinte.du_jour();
  const tr = _traits(traits);
  // Plus le texte est decoupe en titres et en listes, plus la ville a de
  // batiments distincts. Plus il est regulier, plus ils s'alignent en hauteur —
  // un rapport tres structure fait une ville de barres, un texte inegal fait
  // des tours et des maisons.
  const n_tours = 2 + Math.trunc(extension * 3) + Math.trunc(tr.structure * 3);
  const ecart_hauteur = 0.25 + (1.0 - tr.regularite) * 1.10;
  const hauteur_base = 1.6 + tr.longueur * 3.4;
  // Posees de l'arriere vers l'avant et chevauchantes : c'est l'occlusion qui
  // fait la silhouette de ville, pas l'empilement.
  const cles = Array.from({ length: n_tours }, () => rng.random());
  const ordre = Array.from({ length: n_tours }, (_, k) => k)
    .sort((a, b) => cles[a] - cles[b]);
  for (let rang = 0; rang < ordre.length; rang++) {
    const k = ordre[rang];
    // Chaque tour a sa propre date : un chapitre ecrit l'hiver et un autre
    // l'ete ne s'eclairent pas de la meme couleur.
    const col = tt.ton(rng);
    const h = SEGMENT * hauteur_base * rng.uniform(1.0, 1.0 + ecart_hauteur)
      * (0.55 + extension * 0.7);
    const w = SEGMENT * rng.uniform(0.85, 1.7);
    const cx = 100 + (k - n_tours / 2) * SEGMENT * 1.15 + rng.uniform(-6, 6);
    const base = 205 - rang * SEGMENT * 0.22;
    const g = cx - w / 2;
    const d = cx + w / 2;
    const top = base - h;
    for (const seg of [[g, base, g, top], [d, base, d, top],
                       [g, top, d, top], [g, base, d, base]]) {
      t.trait(seg[0], seg[1], seg[2], seg[3], m, null, true);   // squelette
    }
    // La grandeur vient de la repetition d'une unite petite, pas de deux ou
    // trois refends.
    const etages = Math.max(2, Math.trunc(h / (SEGMENT * (0.62 - 0.22 * m))));
    const colonnes = Math.max(1, Math.trunc(w / (SEGMENT * (0.55 - 0.18 * m))));
    for (let e = 1; e < etages; e++) {            // trame : etoffage colore
      const y = base - h * e / etages;
      t.trait(g, y, d, y, m * 0.5, col);
    }
    for (let c = 1; c < colonnes; c++) {
      const x = g + w * c / colonnes;
      t.trait(x, base, x, top, m * 0.4, col);
    }
    t.noeud(g, top, m, col);
    t.noeud(d, top, m, col);
    if (rng.random() < 0.45) {                    // antenne, fleche
      t.trait(cx, top, cx, top - SEGMENT * rng.uniform(0.4, 1.2), m * 0.8);
    }
  }
  t.trait(18, 205, 182, 205, m);
}

// --------------------------------------------------------------------------
// Creature — il s'enchaine
// --------------------------------------------------------------------------
/**
 * Trois parties nommees. Les curseurs agissent sur la GEOMETRIE — largeur du
 * corps, taille de la tete, longueur des membres — et pas seulement sur la
 * densite de traits : en v4 seul le curseur membres changeait la silhouette.
 *
 * Le corps est un contour FERME. Sans lui, la creature v3 n'avait plus de
 * silhouette et devenait illisible : la superposition doit rester
 * hierarchique, le desordre n'est pas l'originalite.
 */
export function creature(t, extension, maturite, graine, teinte = null,
                         traits = null, etoffage = null) {
  const rng = new Alea(graine);
  const m = maturite;
  const tt = teinte || Teinte.du_jour();
  const tr = _traits(traits);
  // La tete est ce qui parle : elle suit le dialogue.
  // Le corps est ce qui porte : des phrases longues font une bete massive.
  // Les membres sont ce qui articule : c'est le rythme, l'irregularite.
  const e = etoffage || {
    tete: 0.15 + tr.dialogue * 0.85,
    corps: 0.12 + tr.longueur * 0.80,
    membres: 0.12 + tr.rythme * 0.80,
  };

  // L'epine doit varier d'un plant a l'autre. En v5 elle etait
  // `sin(i*0.40)*0.30 + 0.12` a un bruit de 0,05 pres : la graine ne changeait
  // presque rien, et six creatures cote a cote dans un paysage etaient six fois
  // la meme bete. L'architecture, elle, variait beaucoup — parce que ses
  // hauteurs sont tirees. On donne a la creature la meme latitude.
  const courbure = rng.uniform(0.17, 0.44);
  const phase = rng.uniform(0.0, 6.283);
  const avance = rng.uniform(0.04, 0.24);
  const cadence = rng.uniform(0.28, 0.58);
  const n = 7 + Math.trunc(extension * 11);
  const spine = [];
  let angle = rng.uniform(-1.1, 0.1);
  let x = 55;
  let y = 165;
  for (let i = 0; i < n; i++) {
    const f = i / Math.max(n - 1, 1);
    const lg = SEGMENT * 0.60 * (1.15 - 0.55 * f);
    angle += Math.sin(i * cadence + phase) * courbure + avance + rng.uniform(-0.05, 0.05);
    x += Math.cos(angle) * lg;
    y += Math.sin(angle) * lg;
    spine.push([x, y, angle, 1.15 - 0.85 * f]);
  }

  // CORPS : de gracile a massif, facteur 5 entre les extremes.
  const ampleur = 0.16 + e.corps * 0.68;
  const gauche = [];
  const droite = [];
  for (const [px, py, pa, ep] of spine) {
    const larg = SEGMENT * ampleur * ep;
    gauche.push([px + Math.cos(pa - 1.57) * larg, py + Math.sin(pa - 1.57) * larg]);
    droite.push([px + Math.cos(pa + 1.57) * larg, py + Math.sin(pa + 1.57) * larg]);
  }
  const contour = gauche.concat(droite.slice().reverse());
  for (let i = 0; i < contour.length; i++) {
    const a = contour[i];
    const b = contour[(i + 1) % contour.length];
    t.trait(a[0], a[1], b[0], b[1], m, null, true);            // squelette
  }
  const pas = Math.max(1, Math.trunc(3 - e.corps * 2));
  for (let i = 0; i < spine.length; i += pas) {
    t.trait(gauche[i][0], gauche[i][1], droite[i][0], droite[i][1], m * 0.55, tt.ton(rng));
  }

  // TETE : le rayon suit le curseur, pas seulement le nombre d'appendices.
  const [hx, hy, ha] = spine[0];
  const rayon = SEGMENT * (0.22 + e.tete * 1.15);
  const n_tete = 3 + Math.trunc(e.tete * 6);
  for (let k = 0; k < n_tete; k++) {
    const a = ha + Math.PI + (k - n_tete / 2) * (1.9 / Math.max(n_tete, 1));
    t.trait(hx, hy, hx + Math.cos(a) * rayon, hy + Math.sin(a) * rayon,
            m * 0.85, tt.ton(rng));
  }
  if (e.tete > 0.5) {                             // calotte : ferme la tete
    const pts = [];
    for (let k = 0; k < 7; k++) {
      pts.push([hx + Math.cos(ha + Math.PI + (k - 3) * 0.32) * rayon * 0.8,
                hy + Math.sin(ha + Math.PI + (k - 3) * 0.32) * rayon * 0.8]);
    }
    for (let i = 0; i < pts.length - 1; i++) {
      t.trait(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], m * 0.7);
    }
  }

  // MEMBRES : en peripherie, articules, jamais en travers du corps.
  //
  // Bornes RELATIVEMENT A LA LARGEUR DU CORPS. Une longueur absolue donne des
  // pattes de meme taille sur une bete gracile et sur une bete massive : la
  // gracile devient une araignee, la massive un mille-pattes ras. En proportion
  // du corps, le curseur membres ne fait plus que ce qu'on lui demande,
  // allonger, sans changer l'espece au passage.
  const largeur_corps = SEGMENT * ampleur;
  const pas_m = Math.max(1, Math.trunc(3 - e.membres * 2));
  for (let i = 1; i < spine.length - 1; i += pas_m) {
    const [px, py, pa, ep] = spine[i];
    for (const [s, bord] of [[-1, gauche], [1, droite]]) {
      const [ax, ay] = bord[i];
      const a1 = pa + s * (1.15 + 0.2 * Math.sin(i));
      const p1 = MEMBRES_PROPORTIONNELS
        ? largeur_corps * (0.8 + 3.2 * e.membres) * ep
        : SEGMENT * (0.25 + 1.25 * e.membres) * ep;
      const bx = ax + Math.cos(a1) * p1;
      const by = ay + Math.sin(a1) * p1;
      t.trait(ax, ay, bx, by, m * 0.8);
      const a2 = a1 + s * rng.uniform(0.55, 1.0);
      t.trait(bx, by, bx + Math.cos(a2) * p1 * 0.65, by + Math.sin(a2) * p1 * 0.65,
              m * 0.6, tt.ton(rng));
      t.noeud(bx, by, m, tt.ton(rng));
    }
  }
}

// --------------------------------------------------------------------------
// Abstrait — il se pave
// --------------------------------------------------------------------------
/**
 * Sa geometrie n'est pas fixee : elle est LUE sur le vecteur de traits. Sans
 * cela, la famille du refus de classement aurait la regle la plus rigide des
 * quatre — un pavage hexagonal regulier.
 *
 *     richesse         -> nombre de facettes
 *     ponctuation_rare -> irregularite des sommets
 *     rythme           -> torsion d'un anneau au suivant
 *     subordination    -> etoilement (sommets pousses vers l'interieur)
 */
export function abstrait(t, extension, maturite, graine, teinte = null, traits = null) {
  const rng = new Alea(graine);
  const m = maturite;
  const tt = teinte || Teinte.du_jour();
  const tr = _traits(traits);

  const cotes = 5 + Math.trunc(tr.richesse * 4.4);           // 5 a 9 facettes
  const irreg = 0.06 + tr.ponctuation_rare * 0.34;
  const torsion = tr.rythme * 0.62;
  const etoile = tr.subordination * 0.42;

  // Jitter tire une fois par sommet puis reutilise sur tous les anneaux : les
  // facettes restent alignees radialement au lieu de partir en bouillie.
  const jitter = [];
  for (let k = 0; k < cotes; k++) jitter.push(rng.uniform(1 - irreg, 1 + irreg));
  const rentrant = [];
  for (let k = 0; k < cotes; k++) rentrant.push(k % 2 ? 1 - etoile : 1.0);

  const anneaux = 1 + Math.trunc(extension * 3.4);
  let prec = null;
  for (let a = 1; a <= anneaux; a++) {
    const r = SEGMENT * 0.58 * a;
    const depart = a * torsion;
    const pts = [];
    for (let k = 0; k < cotes; k++) {
      const ang = 2 * Math.PI * k / cotes + depart;
      const rr = r * jitter[k] * rentrant[k];
      pts.push([100 + Math.cos(ang) * rr, 110 + Math.sin(ang) * rr]);
    }
    for (let k = 0; k < cotes; k++) {
      const p = pts[k];
      const q = pts[(k + 1) % cotes];
      t.trait(p[0], p[1], q[0], q[1], m, null, true);
    }
    if (prec) {
      for (let k = 0; k < cotes; k++) {
        t.trait(prec[k][0], prec[k][1], pts[k][0], pts[k][1], m * 0.8, null, true);
        t.noeud(pts[k][0], pts[k][1], m, tt.ton(rng));
        if (m > 0.45) {                              // etoffage : colore
          const mx = [(prec[k][0] + pts[k][0]) / 2, (prec[k][1] + pts[k][1]) / 2];
          const kk = (k + 1) % cotes;
          const nx = [(prec[kk][0] + pts[kk][0]) / 2, (prec[kk][1] + pts[kk][1]) / 2];
          t.trait(mx[0], mx[1], nx[0], nx[1], m * 0.5, tt.ton(rng));
        }
      }
    } else {
      // Anneau initial subdivise tout de suite : un abstrait jeune doit etre
      // une facette, pas un polygone nu.
      for (let k = 0; k < cotes; k += 2) {
        t.trait(100, 110, pts[k][0], pts[k][1], m * 0.55, tt.ton(rng));
      }
    }
    prec = pts;
  }
}

// --------------------------------------------------------------------------
// Le germe — ce qui pousse avant qu'une famille soit connue
// --------------------------------------------------------------------------
// traits.py prevoit trois stades depuis le debut — germe, indices, divergence —
// et rien n'en dessinait les deux premiers. C'est 16 % de CHAQUE cycle de
// 5 000 mots, donc vingt-sept fois sur une these ; et la premiere de ces
// vingt-sept fois, ce sont les 800 premiers mots ecrits avec le cadeau
// installe. Un volet vide, ce jour-la, est le pire accueil possible.
//
// Ce qu'on dessine : la PRIMITIVE AVANT SON ASSEMBLAGE. Les quatre familles
// sont quatre reponses a la meme question — que fait une chaine de segments
// ensuite ? Elle bifurque, elle s'empile, elle ondule, elle se referme.
//
// Au stade indices, la chaine PENCHE vers la famille pressentie sans s'y
// engager. C'est honnete a une condition : l'inflexion ne doit JAMAIS produire
// un objet reconnaissable. Si le germe ressemblait deja a un arbre et devenait
// une ville, l'organisme se contredirait sous les yeux de la personne. Une
// tendance peut se corriger ; une promesse, non.
/**
 * @param taille    0..1, les mots ecrits rapportes au palier de divergence
 * @param inflexion 0..1, nul au stade germe, croissant au stade indices
 */
export function germe(t, taille, inflexion = 0.0, pressentie = null, graine = 0,
                      teinte = null) {
  const rng = new Alea(graine);
  const tt = teinte || Teinte.du_jour();
  const n = Math.max(1, Math.trunc(1 + taille * 9));
  const m = 0.10 + 0.30 * taille;      // un germe reste maigre : rien n'a muri
  const lg = SEGMENT * 0.60;
  let x = 100.0;
  let y = 200.0;
  let a = -Math.PI / 2;
  const dos = [];

  for (let i = 0; i < n; i++) {
    if (pressentie === "architecture" && inflexion > 0) {
      // elle s'empile : une traverse s'insere entre deux montees. La traverse
      // est un trait EN PLUS, elle ne remplace pas une montee : sans ca, le
      // germe d'architecture tracait deux fois moins de segments que les
      // autres, et les cinq cas differaient DEJA a inflexion nulle.
      const traverse = lg * inflexion * 0.62;
      if (i && traverse > 0.4) {
        const sens = Math.floor(i / 2) % 2 === 0 ? 0.0 : Math.PI;
        const xt = x + Math.cos(sens) * traverse;
        const yt = y + Math.sin(sens) * traverse;
        t.trait(x, y, xt, yt, m);
        x = xt;
        y = yt;
      }
      a = -Math.PI / 2;
    } else if (pressentie === "creature") {
      // elle s'enchaine : la chaine ondule
      a += inflexion * Math.sin(i * 0.95) * 0.40;
    } else if (pressentie === "abstrait") {
      // elle se pave : la chaine s'incurve vers sa propre fermeture
      a += inflexion * 0.30;
    }
    a += rng.uniform(-0.04, 0.04);
    const x2 = x + Math.cos(a) * lg;
    const y2 = y + Math.sin(a) * lg;
    t.trait(x, y, x2, y2, m);
    dos.push([x2, y2, a]);
    x = x2;
    y = y2;
  }

  if (pressentie === "vegetal" && inflexion > 0.15 && dos.length >= 3) {
    // elle se ramifie : une seule bifurcation, courte, en tete de chaine
    const [bx, by, ba] = dos[dos.length - 2];
    for (const sgn of [-1, 1]) {
      const aa = ba + sgn * (0.30 + inflexion * 0.30);
      t.trait(bx, by, bx + Math.cos(aa) * lg * (0.45 + inflexion * 0.5),
              by + Math.sin(aa) * lg * (0.45 + inflexion * 0.5), m * 0.9);
    }
  }

  // Un seul point de couleur en tete : le germe est deja date, et c'est le seul
  // signe qui l'annonce vivant plutot qu'inacheve.
  if (dos.length) {
    const [hx, hy, ha] = dos[dos.length - 1];
    t.trait(hx, hy, hx + Math.cos(ha) * lg * 0.28, hy + Math.sin(ha) * lg * 0.28,
            m * 0.8, tt.ton(rng));
  }
}

export const FAMILLES = {
  vegetal: ["Vegetal / ramifier", vegetal],
  architecture: ["Architecture / empiler", architecture],
  creature: ["Creature / enchainer", creature],
  abstrait: ["Abstrait / paver", abstrait],
};

export function dessiner(famille, extension, maturite, graine, teinte = null,
                         traits = null, etoffage = null) {
  const t = new Toile();
  const f = FAMILLES[famille][1];
  if (famille === "creature") f(t, extension, maturite, graine, teinte, traits, etoffage);
  else f(t, extension, maturite, graine, teinte, traits);
  return t;
}

/**
 * Dessine un plant a partir de l'etat rendu par Paysage.etat().
 *
 * C'est le seul point de contact entre l'etat et le rendu : tout ce que le
 * dessin sait du texte passe par ici.
 */
export function depuis_plant(plant, graine, etoffage = null) {
  const traits = plant.traits || {};
  const teinte = new Teinte(plant.dates, plant.nuit,
    "richesse" in traits ? traits.richesse : 0.5);
  const g = plant.germe;
  if (!plant.famille) {
    // Pas encore de famille : on dessine le germe, qui penche vers la
    // pressentie sans s'y engager.
    const t = new Toile();
    germe(t, g && "taille" in g ? g.taille : 0.1,
          g && "inflexion" in g ? g.inflexion : 0.0,
          plant.pressentie, graine, teinte);
    return t;
  }
  return dessiner(plant.famille, plant.extension, plant.maturite, graine,
                  teinte, traits, etoffage);
}

// Voir le commentaire de TABLES dans traits.js : derivees, jamais recopiees.
export const TABLES = {
  PALETTES,
  SAISONS,
  FONDU,
  HEURE_NUIT: [...HEURE_NUIT],
  TRAIT,
  FOND,
  EPAISSEUR,
  SEGMENT,
  BUDGET_FEUILLAGE,
  TRAITS_NEUTRES,
};
