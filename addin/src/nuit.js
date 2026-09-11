/**
 * La nuit, dans le volet : le profil, la phrase, et ce qui s'en revele.
 *
 * Sans Python en face, comme magasin.js. Ce qui CHOISIT la phrase et ce qui la
 * TRACE est dans phrases.js et message.js, que la parite compare au Python ; il
 * ne reste ici que du cablage — d'ou vient le profil, QUAND la phrase est
 * tiree, CE QUI la revele, et OU elle se pose. Ce fichier ne connait pas
 * Office.js : il s'eprouve dans essais_volet.js, contre l'hote simule ou sans
 * hote du tout.
 *
 * Trois arbitrages, tranches le 11 septembre 2026 (decision 10) :
 *
 *   DANS LE CIEL. Le message se pose en haut de la vue de travail, dans le
 *   meme SVG que le paysage : il appartient au dessin, et la camera ne bouge
 *   pas pour lui. Il peut chevaucher la cime d'un plant haut.
 *
 *   FIXEE AU PREMIER MOT. La phrase est tiree quand le premier mot de la nuit
 *   arrive, puis ne bouge plus : des lettres deja tracees ne changent pas sous
 *   les yeux. Un deblocage arrive a temps — les reprises ne comptent aucun mot,
 *   et c'est le paragraphe qui les suit qui ouvre la nuit. Un elan, qui vient
 *   apres six paragraphes, n'en donne jamais ; son registre est vide.
 *
 *   JUSQU'A LA FERMETURE. A 5 h, les mots ne revelent plus rien, mais ce qui
 *   est trace reste tant que le volet est ouvert. Rien n'est range : a la
 *   reouverture, il n'est plus la. Le revoir le lendemain sans avoir ecrit la
 *   nuit ressemblerait a un rappel.
 */

import { HEURE_NUIT } from "./paysage.js";
import { ACCORDS, Nuit, phrase_de_la_nuit, signes_hors_alphabet,
         _numero_de_nuit } from "./phrases.js";
import { message, _mise_en_page } from "./message.js";
import { Toile } from "./grammaire.js";

/** Decision 10 : la phrase est complete vers 800 mots ecrits dans la fenetre. */
export const MOTS_POUR_TOUT_REVELER = 800;

/**
 * Caracteres par ligne, dans le volet.
 *
 * message.js en met vingt-deux, ce qui va a une planche. Le volet est une
 * colonne de 340 px : a vingt-deux, une lettre y fait une dizaine de pixels, a
 * quatorze pres de seize — au calcul, pas encore vu dans un vrai volet. La
 * mise en page reste celle de la spec, et la parite
 * la compare deja a une autre largeur que celle par defaut (la planche de la
 * main, a huit).
 */
export const LARGEUR_VOLET = 14;

// Ce que le message peut occuper de la vue de travail : sa largeur, sa hauteur,
// et l'air laisse au-dessus de lui.
const CIEL_LARGEUR = 0.88;
const CIEL_HAUTEUR = 0.34;
const CIEL_MARGE = 0.05;

// --------------------------------------------------------------------------
// Le profil (decision 10 revisee)
// --------------------------------------------------------------------------
/**
 * Le profil tel que celui qui offre l'a pose dans le manifeste, derriere le #
 * de l'adresse du volet : volet.html#prenom=…&accord=…
 *
 * Le fragment ne part jamais vers le serveur et ne change pas l'origine, donc
 * pas le magasin (decision 16). Un accord hors de m, f, i vaut ABSENT, pas
 * masculin : les phrases qui s'accordent sortent alors du paquet, et rien ne
 * casse.
 *
 * ⚠️ Personne ne sait encore si le # survit a l'adresse que Word compose dans
 * l'Office LTSC 2021. S'il ne survit pas, ce profil est vide : le prenom sera
 * demande, et l'accord manquera. Voir la passe qa/profil.md.
 */
export function profil_de_l_adresse(href) {
  let fragment = "";
  try {
    fragment = new URL(href).hash.slice(1);
  } catch { /* une adresse illisible donne un profil vide, pas une panne */ }
  const lu = new URLSearchParams(fragment);
  const prenom = (lu.get("prenom") || "").trim();
  const accord = lu.get("accord");
  return { prenom: prenom || null, accord: ACCORDS.includes(accord) ? accord : null };
}

/**
 * Faut-il poser une question du profil — le prenom, ou le genre ? Une fois, et
 * seulement si rien ne donne deja la reponse.
 *
 * ⚠️ PAS SANS SON TEXTE. Il est la voix de celui qui offre, et il reste vide
 * tant qu'il ne l'a pas ecrit : la question se tait alors — et elle n'est pas
 * comptee comme posee, pour l'etre le jour ou le texte existera.
 *
 * @param connu la reponse que l'adresse, le dossier ou le document donnent deja
 */
export function faut_il_demander(connu, question, deja_demande) {
  return !connu && !deja_demande && question.trim() !== "";
}

/**
 * Ce que la saisie du prenom doit signaler : les signes que l'alphabet ne
 * dessine pas, qui disparaitraient sinon en silence au trace. Les accents ne
 * sont pas signales — ils se retirent, comme partout ailleurs dans le message.
 */
export function signalement(prenom) {
  const hors = [...signes_hors_alphabet(prenom)].sort();
  if (!hors.length) return "";
  const cites = hors.map((c) => `« ${c} »`).join(", ");
  return hors.length === 1 ? `${cites} ne se dessine pas` : `${cites} ne se dessinent pas`;
}

// --------------------------------------------------------------------------
// La nuit
// --------------------------------------------------------------------------
const deux = (n) => String(n).padStart(2, "0");

/** La date, en heure LOCALE : une fenetre de 2 h a 5 h tient dans un seul jour. */
export function date_locale(d) {
  return `${d.getFullYear()}-${deux(d.getMonth() + 1)}-${deux(d.getDate())}`;
}

export function dans_la_fenetre(d) {
  const h = d.getHours();
  return HEURE_NUIT[0] <= h && h < HEURE_NUIT[1];
}

/**
 * Les mots ecrits entre 2 h et 5 h, sur tout le paysage.
 *
 * C'est la que la revelation se lit, et nulle part ailleurs : le paysage les
 * compte deja, plant par plant, pour la palette de nuit (decision 9), et ils ne
 * font que croitre — un paragraphe supprime ne reprend pas ses mots (point 3).
 * Les verdicts du guet ne portent aucun compte de mots ; les en doter aurait
 * double un compte qui existe.
 */
export function mots_de_nuit(paysage) {
  return paysage.segments.reduce((a, s) => a + s.mots_de_nuit, 0);
}

/**
 * La graine du trace, tiree de la date comme sur la planche de phrases.py : la
 * meme nuit trace la meme main. Le modulo de Python, jamais negatif — toute
 * nuit d'avant 2027 porte un numero negatif.
 */
function graine_de(date) {
  const n = _numero_de_nuit(date) * 2654435761;
  return ((n % 65536) + 65536) % 65536;
}

/** Ce que la nuit en cours a revele. Une par volet ouvert, jamais rangee. */
export class Veille {
  /**
   * @param profil { prenom, accord }, l'un et l'autre facultatifs
   * @param mots   les mots de nuit du paysage a l'ouverture : le capital de
   *               depart est acquis, il ne revele rien (decision 11)
   */
  constructor(profil, mots = 0) {
    this.profil = profil;
    this.precedent = mots;      // les mots de nuit au dernier releve
    this.date = null;           // la nuit en cours, ou aucune
    this.nuit = null;           // ses evenements (decision 15)
    this.depart = 0;            // les mots de nuit quand elle a commence
    this.phrase = null;         // tiree au premier mot, puis fixe
    this.graine = 1;
    this.avancement = 0.0;
  }

  /**
   * Un releve du guet.
   *
   * @param verdicts ce que Guet.nourrir vient de rendre
   * @param mots     les mots de nuit du paysage, APRES ce releve
   * @param instant  l'heure du releve, celle qu'on a donnee au paysage
   */
  suivre(verdicts, mots, instant) {
    const avant = this.precedent;
    this.precedent = mots;
    // Hors de la fenetre, rien ne bouge : ce qui est trace reste, et ce qu'on
    // ecrit ne revele plus rien.
    if (!dans_la_fenetre(instant)) return;
    const date = date_locale(instant);
    if (date !== this.date) {
      // Une nuit commence. Le depart est le compte d'AVANT ce releve : les mots
      // qu'il apporte sont deja les premiers de la nuit.
      this.date = date;
      this.nuit = new Nuit();
      this.depart = avant;
      this.phrase = null;
      this.avancement = 0.0;
    }
    // Aucun compte de mots ici : les evenements ne lisent que les verdicts.
    for (const v of verdicts) this.nuit.enregistrer(v.verdict);
    const ecrits = mots - this.depart;
    if (ecrits <= 0) return;
    if (this.phrase === null) {
      this.phrase = phrase_de_la_nuit(this.profil, date, this.nuit);
      this.graine = graine_de(date);
    }
    this.avancement = Math.min(1.0, ecrits / MOTS_POUR_TOUT_REVELER);
  }
}

// --------------------------------------------------------------------------
// Dans le ciel
// --------------------------------------------------------------------------
/**
 * La largeur de ligne pour cette phrase.
 *
 * ⚠️ _mise_en_page pousse une ligne VIDE quand le premier mot depasse la
 * largeur : a quatorze, un prenom compose suivi de sa virgule y suffit —
 * « MARIE-ANTOINETTE, » en fait dix-sept. Le message descendait alors d'une
 * ligne sous un blanc. On elargit jusqu'a ce que le premier mot tienne ; la
 * borne ne sert qu'a ne jamais tourner sans fin.
 */
export function largeur_pour(phrase) {
  let largeur = LARGEUR_VOLET;
  while (largeur < 60 && _mise_en_page(phrase, largeur)[0] === "") largeur += 1;
  return largeur;
}

/**
 * Pose le message dans le ciel de la vue de travail.
 *
 * Dans le MEME SVG, apres les plants : le message appartient au dessin, meme
 * primitive, meme epaisseur de trait. Il se regle sur le cadre de la vue — sa
 * largeur d'abord, sa hauteur s'il est long — et ne la deplace pas.
 */
export function dans_le_ciel(svg, veille) {
  if (!veille || veille.phrase === null || veille.avancement <= 0) return svg;
  const vue = svg.match(/viewBox="([^"]+)"/);
  if (!vue) return svg;
  const [vx, vy, vw, vh] = vue[1].split(" ").map(Number);
  const t = new Toile();
  message(t, veille.phrase, veille.avancement,
          { graine: veille.graine, largeur: largeur_pour(veille.phrase) });
  const [x0, y0, x1, y1] = t.cadre;
  const k = Math.min(vw * CIEL_LARGEUR / (x1 - x0), vh * CIEL_HAUTEUR / (y1 - y0));
  const haut = vy + vh * CIEL_MARGE;
  return svg.replace(/<\/svg>$/,
    `<g class="message">${t.pose(vx + vw / 2, haut + (y1 - y0) * k, k)}</g></svg>`);
}
