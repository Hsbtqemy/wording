/**
 * Le message de nuit, portage de jardin/message.py.
 *
 * Trace avec la meme primitive segment que les plantes (decision 10) : c'est
 * ce qui l'empeche de casser la langue graphique. La phrase se revele aux MOTS
 * ECRITS, jamais a l'horloge — rester assis ne suffit pas.
 *
 * Ce qui n'est PAS porte : les planches, et le trace « v6 » que message.py
 * garde pour comparaison sur l'une d'elles. Le livrable n'a qu'une main.
 *
 * ATTENTION A L'ORDRE DES TIRAGES, comme dans grammaire.js. Chaque lettre
 * consomme le generateur dans l'ordre exact du Python : les proportions, puis
 * les sommets a mesure qu'on les rencontre, puis l'inclinaison et le decalage,
 * puis, trait par trait, le ton et l'epaisseur AVANT la polyligne. Deplacer un
 * seul tirage ne casse rien de visible : le message reste lisible, il est
 * simplement AUTRE, et la parite ne compare plus rien.
 *
 * DEUX PIEGES DE PORTAGE, tous deux dans la mise en page :
 *   - len() de Python compte des points de code, .length des unites UTF-16 :
 *     on compte avec Array.from, jamais avec .length ;
 *   - str.replace de Python remplace TOUTES les occurrences, String.replace
 *     la premiere seulement. « un the ? » perdrait son insecable, et le point
 *     d'interrogation passerait seul a la ligne.
 */

import { Alea } from "./alea.js";
import { Teinte } from "./grammaire.js";
import { arrondi } from "./traits.js";

// --------------------------------------------------------------------------
// Alphabet. Grille 0..3 en x, 0..5 en y, traits droits uniquement : la meme
// primitive que les plantes, donc le message appartient au meme dessin.
// --------------------------------------------------------------------------
export const A = {
  A: [[0, 5, 1.5, 0], [1.5, 0, 3, 5], [0.55, 3.2, 2.45, 3.2]],
  B: [[0, 0, 0, 5], [0, 0, 2.2, 0], [2.2, 0, 2.6, 1.2], [2.6, 1.2, 2.2, 2.4], [0, 2.4, 2.2, 2.4],
      [2.2, 2.4, 2.8, 3.6], [2.8, 3.6, 2.2, 5], [0, 5, 2.2, 5]],
  C: [[3, 0.9, 2, 0], [2, 0, 0.7, 0.6], [0.7, 0.6, 0, 2.5], [0, 2.5, 0.7, 4.4], [0.7, 4.4, 2, 5],
      [2, 5, 3, 4.1]],
  D: [[0, 0, 0, 5], [0, 0, 1.9, 0], [1.9, 0, 2.9, 1.7], [2.9, 1.7, 2.9, 3.3], [2.9, 3.3, 1.9, 5],
      [1.9, 5, 0, 5]],
  E: [[2.9, 0, 0, 0], [0, 0, 0, 5], [0, 5, 2.9, 5], [0, 2.5, 2.2, 2.5]],
  F: [[2.9, 0, 0, 0], [0, 0, 0, 5], [0, 2.5, 2.1, 2.5]],
  G: [[3, 0.9, 2, 0], [2, 0, 0.7, 0.6], [0.7, 0.6, 0, 2.5], [0, 2.5, 0.7, 4.4], [0.7, 4.4, 2, 5],
      [2, 5, 3, 4.1], [3, 4.1, 3, 2.8], [3, 2.8, 1.7, 2.8]],
  H: [[0, 0, 0, 5], [3, 0, 3, 5], [0, 2.6, 3, 2.6]],
  I: [[1.5, 0, 1.5, 5], [0.6, 0, 2.4, 0], [0.6, 5, 2.4, 5]],
  J: [[2.5, 0, 2.5, 3.9], [2.5, 3.9, 1.6, 5], [1.6, 5, 0.4, 4.3]],
  K: [[0, 0, 0, 5], [3, 0, 0.2, 2.8], [0.9, 2.1, 3, 5]],
  L: [[0, 0, 0, 5], [0, 5, 2.8, 5]],
  M: [[0, 5, 0, 0], [0, 0, 1.5, 2.6], [1.5, 2.6, 3, 0], [3, 0, 3, 5]],
  N: [[0, 5, 0, 0], [0, 0, 3, 5], [3, 5, 3, 0]],
  O: [[1.5, 0, 0.3, 1.3], [0.3, 1.3, 0.3, 3.7], [0.3, 3.7, 1.5, 5], [1.5, 5, 2.7, 3.7],
      [2.7, 3.7, 2.7, 1.3], [2.7, 1.3, 1.5, 0]],
  P: [[0, 5, 0, 0], [0, 0, 2.3, 0], [2.3, 0, 2.9, 1.4], [2.9, 1.4, 2.3, 2.7], [2.3, 2.7, 0, 2.7]],
  Q: [[1.5, 0, 0.3, 1.3], [0.3, 1.3, 0.3, 3.7], [0.3, 3.7, 1.5, 5], [1.5, 5, 2.7, 3.7],
      [2.7, 3.7, 2.7, 1.3], [2.7, 1.3, 1.5, 0], [1.9, 3.6, 3.1, 5.4]],
  R: [[0, 5, 0, 0], [0, 0, 2.3, 0], [2.3, 0, 2.9, 1.4], [2.9, 1.4, 2.3, 2.7], [2.3, 2.7, 0, 2.7],
      [1.3, 2.7, 3, 5]],
  S: [[2.9, 0.8, 1.8, 0], [1.8, 0, 0.4, 0.7], [0.4, 0.7, 0.5, 2], [0.5, 2, 2.5, 2.9],
      [2.5, 2.9, 2.7, 4.2], [2.7, 4.2, 1.4, 5], [1.4, 5, 0.1, 4.2]],
  T: [[0, 0, 3, 0], [1.5, 0, 1.5, 5]],
  U: [[0, 0, 0, 3.7], [0, 3.7, 1.5, 5], [1.5, 5, 3, 3.7], [3, 3.7, 3, 0]],
  V: [[0, 0, 1.5, 5], [1.5, 5, 3, 0]],
  W: [[0, 0, 0.7, 5], [0.7, 5, 1.5, 1.8], [1.5, 1.8, 2.3, 5], [2.3, 5, 3, 0]],
  X: [[0, 0, 3, 5], [3, 0, 0, 5]],
  Y: [[0, 0, 1.5, 2.6], [3, 0, 1.5, 2.6], [1.5, 2.6, 1.5, 5]],
  Z: [[0, 0, 3, 0], [3, 0, 0, 5], [0, 5, 3, 5]],
  "?": [[0.2, 1.0, 1.4, 0.0], [1.4, 0.0, 2.7, 1.0], [2.7, 1.0, 1.5, 2.6],
        [1.5, 2.6, 1.5, 3.4], [1.5, 4.4, 1.5, 5.0]],
  "'": [[1.5, 0, 1.2, 1.4]],
  ",": [[1.5, 4.2, 1.1, 5.6]],
  "!": [[1.5, 0, 1.5, 3.4], [1.5, 4.4, 1.5, 5]],
  ".": [[1.4, 4.7, 1.6, 5]],
  // Le trait d'union, pour les prenoms composes (decision 10).
  "-": [[0.5, 2.5, 2.5, 2.5]],
  " ": [],
};

export const CORPS = 22.0;
export const CHASSE = 1.38;        // avance horizontale, en corps
export const INTERLIGNE = 2.0;     // avance verticale, en corps
export const LARGEUR = 22;         // caracteres par ligne

// len() de Python : des points de code, pas des unites UTF-16.
const longueur = (s) => Array.from(s).length;

/** A.get(ch, []) — sans jamais remonter au prototype de l'objet. */
const glyphe = (ch) => (Object.prototype.hasOwnProperty.call(A, ch) ? A[ch] : []);

// --------------------------------------------------------------------------
// Le trait de main
// --------------------------------------------------------------------------
/**
 * Un trait de lettre, trace comme une branche : sous-segments de longueurs
 * inegales, marche perpendiculaire qui accumule, depassement aux extremites.
 * Voir message.py pour ce que chacun corrige.
 */
function _polyligne(t, ax, ay, bx, by, corps, rng, col, m, part = 1.0) {
  const d = Math.hypot(bx - ax, by - ay);
  if (d < 1e-6) return;
  const n = Math.max(2, Math.min(5, Math.trunc(d / (corps * 0.34)) + 2));

  const coupes = [];
  for (let k = 0; k < n - 1; k++) coupes.push(rng.uniform(0.10, 0.90));
  coupes.sort((a, b) => a - b);
  const jalons = [0.0, ...coupes, 1.0];

  const ux = (bx - ax) / d;
  const uy = (by - ay) / d;
  const px = -uy;
  const py = ux;
  const amp = corps * 0.030;
  const depart = -corps * 0.020 * rng.uniform(0, 1);
  const arrivee = corps * 0.030 * rng.uniform(0, 1);

  const devs = [];
  let courant = rng.uniform(-amp, amp) * 0.4;
  for (let k = 0; k < jalons.length; k++) {
    courant += rng.uniform(-amp, amp) * 0.7;
    devs.push(Math.max(-amp * 1.6, Math.min(amp * 1.6, courant)));
  }

  const pts = [];
  for (let k = 0; k < jalons.length; k++) {
    const long = depart + (d - depart + arrivee) * jalons[k];
    pts.push([ax + ux * long + px * devs[k], ay + uy * long + py * devs[k]]);
  }

  // Revelation : le trait en cours s'arrete en chemin.
  const total = pts.length - 1;
  const vus = part * total;
  for (let k = 0; k < total; k++) {
    if (vus <= k) break;
    const g = Math.min(1.0, vus - k);
    const [x1, y1] = pts[k];
    const [x2, y2] = pts[k + 1];
    t.trait(x1, y1, x1 + (x2 - x1) * g, y1 + (y2 - y1) * g, m, col);
  }
}

/**
 * Deplace les SOMMETS de la lettre, pas ses traits (point ouvert 4). Le
 * decalage est partage par tous les traits qui se rejoignent en un point,
 * sinon la lettre se descoud aux jonctions.
 *
 * Les proportions sont tirees AVANT le premier sommet : c'est l'ordre du
 * Python, et c'est lui qui fait la figure.
 */
function _sommets(traits, rng, corps, force = 1.0) {
  const coins = new Map();
  const d = corps * 0.055 * force;
  const coin = (x, y) => {
    const cle = `${arrondi(x, 2)},${arrondi(y, 2)}`;
    if (!coins.has(cle)) coins.set(cle, [rng.uniform(-d, d), rng.uniform(-d, d)]);
    return coins.get(cle);
  };
  const kx = rng.uniform(0.93, 1.07);
  const ky = rng.uniform(0.95, 1.05);
  const sortie = [];
  for (const [a, b, c, e] of traits) {
    const da = coin(a, b);
    const db = coin(c, e);
    sortie.push([a * kx + da[0], b * ky + da[1], c * kx + db[0], e * ky + db[1]]);
  }
  return sortie;
}

/**
 * Les lignes de la phrase. L'insecable colle « ? » et « ! » au mot d'avant :
 * sans elle, un point d'interrogation peut passer seul a la ligne.
 * replaceAll, pas replace — voir l'en-tete.
 */
export function _mise_en_page(phrase, largeur = LARGEUR) {
  const p = phrase.toUpperCase().replaceAll(" ?", "\u00a0?").replaceAll(" !", "\u00a0!");
  const lignes = [];
  let courante = "";
  for (const mot of p.split(" ")) {
    if (longueur(courante) + longueur(mot) + 1 > largeur) {
      lignes.push(courante);
      courante = mot;
    } else {
      // strip() de Python retire aussi l'insecable ; trim() de JavaScript
      // aussi. Ils different sur quelques separateurs de controle, que
      // l'alphabet ne dessine pas et que la saisie du prenom signale.
      courante = (courante + " " + mot).trim();
    }
  }
  lignes.push(courante);
  return lignes.map((l) => l.replaceAll("\u00a0", " "));
}

/**
 * La boite de la phrase COMPLETE, calculee avant de dessiner : c'est ce qui
 * empeche le message de se recentrer a chaque lettre (point ouvert 9).
 */
export function cadre_de(phrase, corps = CORPS, largeur = LARGEUR, x0 = 0.0, y0 = 0.0) {
  const lignes = _mise_en_page(phrase, largeur);
  const l_max = Math.max(...lignes.map(longueur));
  return [x0 - corps * 0.2,
          y0 - corps * 0.2,
          x0 + (l_max - 1) * corps * CHASSE + corps + corps * 0.2,
          y0 + (lignes.length - 1) * corps * INTERLIGNE + corps + corps * 0.2];
}

/**
 * Trace la phrase avec la primitive segment.
 *
 * `avancement` (0..1) vient des mots ecrits pendant la fenetre de nuit, pas de
 * l'heure. Les arguments nommes du Python arrivent dans un objet.
 */
export function message(t, phrase, avancement,
                        { x0 = 0.0, y0 = 0.0, corps = CORPS, graine = 1,
                          largeur = LARGEUR, teinte = null } = {}) {
  const rng = new Alea(graine);
  const tt = teinte || new Teinte([[0, 1]], true, 1.0);
  const lignes = _mise_en_page(phrase, largeur);

  // Le cadre est pose d'abord, sur la phrase entiere.
  t.cadre = cadre_de(phrase, corps, largeur, x0, y0);

  const total = lignes.reduce((s, l) => s + longueur(l), 0);
  const reveles = avancement * total;
  let vus = 0;
  lignes.forEach((ligne, li) => {
    Array.from(ligne).forEach((ch, ci) => {
      const part = reveles - vus;
      vus += 1;
      if (part <= 0) return;
      const f = Math.min(1.0, part);
      const px = x0 + ci * corps * CHASSE;
      const py = y0 + li * corps * INTERLIGNE;
      const n = glyphe(ch).length;
      if (!n) return;
      // Les sommets de CETTE instance de la lettre.
      const traits = _sommets(glyphe(ch), rng, 3.0);
      // Chaque lettre posee un peu de travers.
      const inclinaison = rng.uniform(-0.035, 0.035);
      const decal = rng.uniform(-corps * 0.045, corps * 0.045);
      for (let i = 0; i < n; i++) {
        const [a, b, c, d] = traits[i];
        const seuil = (i + 1) / n;
        if (f < seuil - 1 / n) continue;
        const part_trait = f >= seuil ? 1.0 : (f - (seuil - 1 / n)) * n;
        let ax = px + a * corps / 3;
        let ay = py + b * corps / 5 + decal;
        let bx = px + c * corps / 3;
        let by = py + d * corps / 5 + decal;
        const cy = py + corps * 0.5;
        // rotation de la lettre autour de son milieu
        const tourne = (X, Y) => {
          const dx = X - (px + corps / 2);
          const dy = Y - cy;
          const co = Math.cos(inclinaison);
          const si = Math.sin(inclinaison);
          return [px + corps / 2 + dx * co - dy * si, cy + dx * si + dy * co];
        };
        [ax, ay] = tourne(ax, ay);
        [bx, by] = tourne(bx, by);
        // Le ton PUIS l'epaisseur : l'ordre des arguments est celui du Python,
        // et c'est un ordre de tirages.
        _polyligne(t, ax, ay, bx, by, corps, rng,
                   tt.ton(rng), rng.uniform(0.45, 0.85), part_trait);
      }
    });
  });
}
