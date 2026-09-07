/**
 * La composition du paysage, portage de jardin/composition.py.
 *
 * Trois regles, chacune portant une chose vraie du texte (decision 14) :
 *
 *   x        l'ordre dans le document. On lit le paysage comme on lirait la
 *            these. Les parcelles sont separees par un intervalle plus large :
 *            les trois niveaux deviennent visibles sans rien etiqueter.
 *
 *   echelle  la MATURITE. Un plant beaucoup repris vient au premier plan ; un
 *            plant pose une fois reste au fond. C'est la seule regle qui rend
 *            visible OU LE TRAVAIL EST REELLEMENT ALLE.
 *
 *   y        suit l'echelle : ce qui est au premier plan est plus bas.
 *
 * L'extension n'entre PAS dans le placement. Elle est deja dans la taille
 * propre de chaque plant ; la faire aussi porter la profondeur fusionnerait les
 * deux axes par la bande, ce que la decision 2 interdit.
 *
 * Ce qui n'est PAS porte : _demonstration() et planche_volet(), qui rejouent
 * une redaction pour fabriquer des planches. Elles appartiennent au banc.
 */

import { Alea } from "./alea.js";
import { FOND, FAMILLES, depuis_plant, fixe } from "./grammaire.js";

export const HORIZON = 0.62;      // part de la hauteur ou passe l'horizon
// Le fond s'ELOIGNE, il ne fane pas. Avec une echelle de 0,42 et une opacite de
// 0,45, un plant jamais repris devenait un fantome — et se lisait comme une
// punition de ne pas avoir retravaille, alors que la decision 1 dit que rien ne
// fane jamais. La profondeur doit rester lisible comme de la distance, pas
// comme de l'effacement.
export const ECHELLE_FOND = 0.66;   // un plant jamais repris
export const ECHELLE_AVANT = 1.0;   // un plant tres repris
export const OPACITE_FOND = 0.78;
export const ECART = 1.06;          // respiration entre deux plants
export const ECART_PARCELLE = 1.55; // entre deux chapitres

/** 0 au fond, 1 au premier plan. C'est la maturite, et rien d'autre. */
function _profondeur(plant) {
  return Math.max(0.0, Math.min(1.0, plant.maturite || 0.0));
}

/**
 * L'encombrement que CE plant atteindra une fois plein.
 *
 * Le volet ne doit pas cadrer sur le plant tel qu'il est : s'il le remplit
 * toujours, un plant jeune et un plant acheve se ressemblent et la croissance
 * devient invisible — on aurait detruit le retour par l'autre bout, en voulant
 * le preserver. On cadre donc sur la taille FINALE : chaque paragraphe en
 * remplit 1,92 %, ce qui est exactement la garantie de la decision 6.
 */
export function gabarit(plant, graine) {
  const plein = { ...plant };
  plein.extension = 1.0;
  plein.maturite = Math.max(plant.maturite || 0.0, 0.85);
  if (!plein.famille) {
    // Un germe n'a pas encore de famille, donc pas de taille finale connue. On
    // prend LA PLUS GRANDE des quatre.
    //
    // Pas la pressentie : sa taille changerait le jour ou une tendance
    // apparait, et comme les quatre familles n'ont pas le meme encombrement
    // natif, le germe se mettrait a RETRECIR sous les yeux de la personne. Le
    // point 1 interdit que quoi que ce soit recule. Avec la plus grande,
    // l'echelle ne peut que monter : la croissance reste monotone.
    plein.germe = null;
    let grand = null;
    for (const famille of Object.keys(FAMILLES)) {
      plein.famille = famille;
      const t = depuis_plant(plein, graine);
      const enc = Math.max(t.hauteur(), t.largeur() * 0.52);
      if (grand === null || enc > grand[0]) grand = [enc, t.largeur(), t.hauteur()];
    }
    return [grand[1], grand[2]];
  }
  const t = depuis_plant(plein, graine);
  return [t.largeur(), t.hauteur()];
}

/**
 * Rend le paysage entier. `plants` vient de Paysage.etat().plants.
 *
 * Renvoie [poses, largeur_totale].
 */
export function composer(plants, hauteur = 560, graine = 1, marge = 90) {
  const rng = new Alea(graine);
  const figures = [];

  // 1. Chaque plant a sa taille propre. Un germe se dessine aussi : il n'a pas
  //    de famille, mais il a deja quelque chose a montrer.
  for (const p of plants) {
    const vide = !p.famille && !((p.germe || {}).taille);
    if (vide) continue;
    // depuis_plant est le seul point de contact entre l'etat et le rendu : la
    // teinte ET la physionomie viennent du texte de ce plant.
    figures.push([p, depuis_plant(p, graine + p.rang * 977)]);
  }

  if (!figures.length) return [[], marge * 2];

  // 2. Echelle et position.
  const y_horizon = hauteur * HORIZON;
  const haut_utile = hauteur * 0.52;
  const poses = [];
  let x = marge;
  let parcelle = null;
  for (const [p, t] of figures) {
    const d = _profondeur(p);
    // L'echelle se calcule sur la taille FINALE du plant, jamais sur sa taille
    // du moment. Normaliser sur la taille courante ramenait tout plant a la
    // meme hauteur : un plant a 800 mots et un plant a 5 000 apparaissaient
    // identiques, et L'EXTENSION DEVENAIT INVISIBLE DANS LE PAYSAGE.
    //
    // On normalise sur l'ENCOMBREMENT et non sur la seule hauteur : une
    // creature deployee est basse et tres large, et la mettre a la hauteur des
    // autres lui donnait le tiers du paysage a elle seule.
    const [gl, gh] = gabarit(p, graine + p.rang * 977);
    const encombrement = Math.max(gh, gl * 0.52);
    const k = (ECHELLE_FOND + (ECHELLE_AVANT - ECHELLE_FOND) * d)
      * haut_utile / encombrement;
    // La place reservee est celle de la taille finale : un plant qui grandit ne
    // doit pas pousser ses voisins.
    const largeur = gl * k;
    const titre = p.titre || "";
    if (parcelle !== null && titre && titre !== parcelle) {
      x += largeur * (ECART_PARCELLE - ECART);      // respiration de chapitre
    }
    parcelle = titre || parcelle;
    // Le premier plan descend sous l'horizon, le fond remonte dessus.
    const y = y_horizon + (d - 0.5) * hauteur * 0.20 + rng.uniform(-4, 4);
    poses.push([d, x + largeur / 2, y, k, t]);
    x += largeur * ECART;
  }

  return [poses, x + marge];
}

/**
 * Rend le monde a travers un CADRE [x, y, largeur, hauteur] en coordonnees du
 * monde.
 *
 * C'est le seul rendu qui existe : la vue de travail et la vue d'ensemble ne
 * sont pas deux dessins, ce sont deux cadres sur le meme. Deux dessins
 * pourraient se contredire ; deux cadres, non.
 */
export function rendre(poses, cadre, hauteur, largeur_svg = "100%") {
  const [vx, vy, vw, vh] = cadre;
  // Du fond vers l'avant : c'est l'occlusion qui fait un paysage.
  const out = [];
  const tries = poses.slice().sort((a, b) => a[0] - b[0]);
  for (const [d, cx, y, k, t] of tries) {
    // Un voile atmospherique tres leger, juste de quoi separer les plans.
    const opacite = OPACITE_FOND + (1.0 - OPACITE_FOND) * d;
    out.push(`<g opacity="${fixe(opacite, 2)}">${t.pose(cx, y, k)}</g>`);
  }
  return '<svg xmlns="http://www.w3.org/2000/svg" '
    + `viewBox="${fixe(vx, 1)} ${fixe(vy, 1)} ${fixe(vw, 1)} ${fixe(vh, 1)}" `
    + `width="${largeur_svg}">`
    + `<rect x="${fixe(vx, 1)}" y="${fixe(vy, 1)}" width="${fixe(vw, 1)}" `
    + `height="${fixe(vh, 1)}" fill="${FOND}"/>`
    + `${out.join("")}</svg>`;
}

export function svg(plants, hauteur = 560, graine = 1) {
  const [poses, largeur] = composer(plants, hauteur, graine);
  return rendre(poses, [0, 0, largeur, hauteur], hauteur);
}

// --------------------------------------------------------------------------
// Deux vues, pas une echelle
// --------------------------------------------------------------------------
// Le dezoom progressif est la croissance logarithmique du point 6, transposee
// d'un cran. Mesure : si tout doit tenir dans le cadre, un paragraphe deplace
// 1,92 % / n de ce qu'on regarde. A 14 plants — 70 000 mots — cela fait
// 0,137 %, exactement le seuil ou le point 6 declare le mecanisme mort, atteint
// exactement au meme nombre de mots.
//
// Une barre defilante a l'echelle constante garde le retour mais perd
// l'ensemble — or l'ensemble est ce pour quoi le cadeau existe, a la fin. Les
// deux exigences sont contraires, donc aucune echelle unique ne les tient.
//
//   VUE DE TRAVAIL   le plant en cours, a taille pleine, dans le volet.
//   VUE D'ENSEMBLE   le paysage entier, ouvert deliberement.
//
// Le volet Word est une colonne etroite et haute (~320-450 px) : une bande
// horizontale y est le pire format possible. La vue d'ensemble appartient donc
// a un dialogue, qui s'ouvre en fenetre large ; le volet garde la vue de
// travail.

/**
 * Ce que le volet montre pendant qu'on ecrit.
 *
 * Ce n'est PAS un autre dessin du paysage : c'est le meme monde, vu par un
 * cadre plus serre pose sur le plant en cours. Deux dessins separes du meme
 * objet finissent toujours par se contredire — celui-ci ne le peut pas.
 */
export function vue_de_travail(plants, graine = 1, largeur = 360, hauteur = 440,
                               monde = 560) {
  const [poses] = composer(plants, monde, graine);
  if (!poses.length) {
    return '<svg xmlns="http://www.w3.org/2000/svg" '
      + `viewBox="0 0 ${largeur} ${hauteur}" width="100%">`
      + `<rect width="${largeur}" height="${hauteur}" fill="${FOND}"/></svg>`;
  }

  // Le plant en cours est le dernier pose. On retrouve sa pose par son x.
  const vivants = plants.filter((p) => p.famille || p.germe);
  const actif = vivants[vivants.length - 1];
  // max() de Python garde le PREMIER maximum ; un > strict fait pareil.
  let pose = poses[0];
  for (const q of poses) if (q[1] > pose[1]) pose = q;
  const [, cx, y, k] = pose;

  // Taille FINALE de ce plant, dans les unites du monde. Le cadre doit la
  // contenir ENTIEREMENT : un plant plus large que haut — une creature
  // deployee, un arbre — se ferait sinon rogner sur les cotes le jour ou il
  // arrive a maturite, c'est-a-dire au pire moment.
  const [gl, gh] = gabarit(actif, graine + actif.rang * 977);
  const vh = Math.max(gh * k * 1.30, gl * k * 1.15 * hauteur / largeur, 1.0);
  const vw = vh * largeur / hauteur;

  // Le plant en cours n'est pas au centre mais aux deux tiers a droite.
  //
  // C'est la reponse a la seule chose que ce volet ne savait pas montrer : un
  // plant qui vient de naitre n'est presque rien, et centre dans son cadre il
  // donne un volet vide — vingt-sept fois sur une these, dont la premiere fois
  // est celle des 800 premiers mots ecrits avec le cadeau. Decale, il laisse
  // voir le plant precedent qui sort par la gauche : on avance dans le paysage
  // au lieu de repartir de zero a chaque chapitre, et la naissance d'un plant
  // devient un evenement visible — le precedent s'en va.
  return rendre(poses, [cx - vw * 0.63, y - vh * 0.86, vw, vh], hauteur);
}

/**
 * La vue d'ensemble, groupee par PARCELLE.
 *
 * La compression ne vient pas d'une reduction d'echelle mais du regroupement :
 * la hierarchie du point 6 la donne gratuitement. Vingt-sept plants en huit
 * chapitres font huit massifs, et un massif se regarde d'un coup. Les plants
 * d'une meme parcelle se chevauchent — c'est le meme texte, ils forment un
 * relief — et les parcelles respirent entre elles.
 */
export function apercu(plants, hauteur = 520, graine = 1, marge = 70) {
  const rng = new Alea(graine);
  const parcelles = [];
  for (const p of plants) {
    if (!p.famille) continue;
    const cle = p.titre || "";
    if (!parcelles.length || parcelles[parcelles.length - 1][0] !== cle) {
      parcelles.push([cle, []]);
    }
    parcelles[parcelles.length - 1][1].push(p);
  }
  if (!parcelles.length) return [[], marge * 2];

  const y_horizon = hauteur * HORIZON;
  const haut_utile = hauteur * 0.44;
  const poses = [];
  let x = marge;
  for (const [, groupe] of parcelles) {
    // Dans un massif, les plants se serrent et se recouvrent.
    const serrage = groupe.length > 1 ? 0.46 : 1.0;
    let largeur_massif = 0.0;
    for (const p of groupe) {
      const t = depuis_plant(p, graine + p.rang * 977);
      const d = _profondeur(p);
      const [gl, gh] = gabarit(p, graine + p.rang * 977);
      const enc = Math.max(gh, gl * 0.52);
      const k = (ECHELLE_FOND + (ECHELLE_AVANT - ECHELLE_FOND) * d)
        * haut_utile / enc;
      const l = gl * k;
      const y = y_horizon + (d - 0.5) * hauteur * 0.18 + rng.uniform(-5, 5);
      poses.push([d, x + largeur_massif + l / 2, y, k, t]);
      largeur_massif += l * serrage;
    }
    x += largeur_massif + haut_utile * 0.55;        // respiration de parcelle
  }

  return [poses, x + marge];
}

export function svg_apercu(plants, hauteur = 520, graine = 1) {
  const [poses, largeur] = apercu(plants, hauteur, graine);
  return rendre(poses, [0, 0, largeur, hauteur], hauteur);
}

// Voir le commentaire de TABLES dans traits.js : derivees, jamais recopiees.
export const TABLES = {
  HORIZON, ECHELLE_FOND, ECHELLE_AVANT, OPACITE_FOND, ECART, ECART_PARCELLE,
};
