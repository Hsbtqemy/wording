/**
 * Les phrases de nuit, portage de jardin/phrases.py.
 *
 * Le routage par evenement de la decision 15, le paquet battu de la decision
 * 10, et le profil de la decision 10 revisee — un prenom et un accord, l'un et
 * l'autre facultatifs. Pas la planche, pas verifier() : le banc d'essai reste
 * en Python.
 *
 * ⚠️ LES PHRASES NE SE GENERENT PAS. Les registres sont COPIES tels quels de
 * phrases.py. CREUX reste vide ici comme la-bas : c'est la voix de celui qui
 * offre, et elle ne s'ecrit pas a sa place.
 *
 * TROIS PIEGES DE PORTAGE, et ils ont tous la meme cause : les nuits d'avant le
 * 1er janvier 2027 portent un numero NEGATIF.
 *   - divmod de Python arrondit vers le bas ; la division de JavaScript, vers
 *     zero. Math.floor, jamais Math.trunc.
 *   - le modulo de Python n'est jamais negatif, celui de JavaScript si : un
 *     registre servirait sa case -1, qui n'existe pas.
 *   - random.Random(n) prend la valeur absolue de la graine ; Alea aussi.
 */

import { Alea } from "./alea.js";
import { A } from "./message.js";

export const ORIGINE = "2027-01-01";

// --------------------------------------------------------------------------
// Les registres — copies de phrases.py, a garder identiques (la parite le dit)
// --------------------------------------------------------------------------
export const COMMUNES = [
  "il est tard, et tu ecris quand meme",
  "personne ne te regarde. moi si.",
  "tu es trop {fort|forte|fort.e}",
  "j'aime bien ce paragraphe, ca tue",
  "un petit cafe ? un the ?",
  "alleeeeeeeez",
  "n'oublie pas de boire de l'eau",
];

export const NOMINATIVES = [
  "{prenom}, encore debout ?",
  "{prenom}, ce chapitre avance bien",
  "va dormir, {prenom}",
];

export const DEBLOCAGE = [
  "c'est geniaaaaaaaaaaaal",
  "mais ouiiiiiiii",
];

export const ELAN = [];

// Vide, et c'est voulu : la voix de celui qui offre. Voir phrases.py.
export const CREUX = [];

export const REGISTRES = {
  creux: CREUX,
  deblocage: DEBLOCAGE,
  elan: ELAN,
};

// L'ordre des formes dans une phrase qui s'accorde : {fort|forte|fort.e}.
export const ACCORDS = ["m", "f", "i"];
const _CHAMP = /\{([^{}]*)\}/g;

// --------------------------------------------------------------------------
// Ce que le trace sait ecrire
// --------------------------------------------------------------------------
export function sans_accent(s) {
  return s.normalize("NFD").replace(/\p{Mn}/gu, "");
}

/** Sans accents, et l'apostrophe de Word ramenee a '. */
export function au_trace(s) {
  return sans_accent(s.replace(/[\u2019\u2018]/g, "'"));
}

/** Les signes que l'alphabet ne sait pas dessiner — pour la saisie du prenom. */
export function signes_hors_alphabet(texte) {
  const hors = new Set();
  for (const c of au_trace(texte).toUpperCase()) {
    if (!Object.prototype.hasOwnProperty.call(A, c)) hors.add(c);
  }
  return hors;
}

// --------------------------------------------------------------------------
// Le profil
// --------------------------------------------------------------------------
const _champs = (brut) => Array.from(brut.matchAll(_CHAMP), (m) => m[1]);

/** Le profil permet-il de remplir cette phrase ? Voir phrases.py. */
export function _servable(brut, profil) {
  const champs = _champs(brut);
  if (champs.includes("prenom") && !profil.prenom) return false;
  if (champs.some((c) => c.includes("|")) && !ACCORDS.includes(profil.accord)) return false;
  return true;
}

/** La phrase, champs remplis. STRICTE : leve s'il manque de quoi. */
export function remplir(brut, profil) {
  return brut.replace(_CHAMP, (_tout, c) => {
    if (c === "prenom") {
      if (!profil.prenom) throw new Error(`${JSON.stringify(brut)} : pas de prenom`);
      return profil.prenom;
    }
    if (!c.includes("|")) throw new Error(`${JSON.stringify(brut)} : champ inconnu {${c}}`);
    const formes = c.split("|");
    if (formes.length !== ACCORDS.length) {
      throw new Error(`${JSON.stringify(brut)} : ${formes.length} formes, il en faut ${ACCORDS.length}`);
    }
    if (!ACCORDS.includes(profil.accord)) throw new Error(`${JSON.stringify(brut)} : pas d'accord`);
    return formes[ACCORDS.indexOf(profil.accord)];
  });
}

// --------------------------------------------------------------------------
// Ce que la nuit a produit
// --------------------------------------------------------------------------
export const REPRISES_AVANT_DEBLOCAGE = 5;
export const REPRISES_POUR_UN_CREUX = 4;
export const PARAGRAPHES_POUR_UN_ELAN = 6;

/** Les deux axes, mesures sur la seule fenetre de nuit. */
export class Nuit {
  constructor() {
    this.nouveaux = 0;
    this.reprises = 0;
    this.mots = 0;
    this._reprises_courantes = 0;
    this._deblocage = false;
  }

  enregistrer(verdict, mots = 0) {
    if (verdict === "ecriture" || verdict === "conversion") {
      if (this._reprises_courantes >= REPRISES_AVANT_DEBLOCAGE) this._deblocage = true;
      this._reprises_courantes = 0;
      this.nouveaux += 1;
      this.mots += mots;
    } else if (verdict === "frappe") {
      this.mots += mots;
    } else if (verdict === "reprise") {
      this.reprises += 1;
      this._reprises_courantes += 1;
    }
  }

  /** Le registre a servir cette nuit, ou null pour le paquet ordinaire. */
  evenement() {
    if (this._deblocage) return "deblocage";
    if (this.nouveaux === 0 && this.reprises >= REPRISES_POUR_UN_CREUX) return "creux";
    if (this.reprises === 0 && this.nouveaux >= PARAGRAPHES_POUR_UN_ELAN) return "elan";
    return null;
  }
}

// --------------------------------------------------------------------------
// Le paquet battu
// --------------------------------------------------------------------------
const _jour = (iso) => {
  const [a, m, j] = iso.split("-").map(Number);
  return Date.UTC(a, m - 1, j) / 86400000;
};

export function _numero_de_nuit(date_iso, origine = ORIGINE) {
  return _jour(date_iso) - _jour(origine);
}

/** Le modulo de Python : jamais negatif. */
const modulo = (a, n) => ((a % n) + n) % n;

const _MEMOIRE_PAQUETS = new Map();

/**
 * Le paquet REELLEMENT servi au tour donne, raccord compris. Voir phrases.py :
 * la cle est le corpus entier, et le raccord se fait vers le tour 0, des deux
 * cotes — un tour positif contre la FIN du tour d'avant, un tour negatif
 * contre le DEBUT du tour d'apres.
 */
export function _paquet(tour, corpus) {
  const cle = JSON.stringify([tour, corpus]);
  if (_MEMOIRE_PAQUETS.has(cle)) return _MEMOIRE_PAQUETS.get(cle);

  const garde = Math.max(2, Math.min(4, Math.floor(corpus.length / 3)));
  const paquet = corpus.slice();
  new Alea(tour * 7919).shuffle(paquet);
  let voisin = null;
  let bord = null;
  if (tour > 0) {
    voisin = new Set(_paquet(tour - 1, corpus).slice(-garde));
    bord = (p) => p.slice(0, garde);
  } else if (tour < 0) {
    voisin = new Set(_paquet(tour + 1, corpus).slice(0, garde));
    bord = (p) => p.slice(-garde);
  }
  if (tour !== 0) {
    let essai = 0;
    while (bord(paquet).some((x) => voisin.has(x)) && essai < 200) {
      essai += 1;
      new Alea(tour * 7919 + essai * 104729).shuffle(paquet);
    }
  }
  _MEMOIRE_PAQUETS.set(cle, paquet);
  return paquet;
}

/** Une phrase par nuit, distribuee comme un PAQUET BATTU. */
export function _du_paquet(date_iso, corpus) {
  const nuit = _numero_de_nuit(date_iso);
  // divmod de Python : vers le bas, meme pour une nuit negative.
  const tour = Math.floor(nuit / corpus.length);
  const rang = nuit - tour * corpus.length;
  return _paquet(tour, corpus)[rang];
}

/**
 * La phrase de cette nuit. Un evenement l'emporte sur le paquet ; un registre
 * vide retombe sur le paquet ; une phrase que le profil ne permet pas de
 * remplir ne sort pas.
 */
export function phrase_de_la_nuit(profil, date_iso, nuit = null) {
  const corpus = COMMUNES.concat(NOMINATIVES).filter((b) => _servable(b, profil));
  let brut = null;

  if (nuit !== null) {
    const ev = nuit.evenement();
    const registre = (ev && Object.prototype.hasOwnProperty.call(REGISTRES, ev) ? REGISTRES[ev] : [])
      .filter((b) => _servable(b, profil));
    if (registre.length) {
      brut = registre[modulo(_numero_de_nuit(date_iso), registre.length)];
    }
  }

  if (brut === null) brut = _du_paquet(date_iso, corpus);

  return au_trace(remplir(brut, profil));
}
