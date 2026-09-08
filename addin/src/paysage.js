/**
 * Etat du paysage.
 *
 * Portage mecanique de jardin/paysage.py, qui reste la specification. Ce
 * module implemente les decisions 2 a 6 et 11 :
 *
 *      2. les deux axes              extension / maturite, et le curseur
 *      3. le registre d'empreintes   deplacer / fusionner / copier / supprimer
 *      4. le collage                 ecriture, greffe, conversion
 *      5. le verrou par segment      800 mots ET 3 lectures espacees
 *      6. l'echelle                  un plant au Titre 1 ou a 5 000 mots
 *     11. le perimetre               le paysage appartient au dossier
 *
 * Aucune API Word, aucun DOM, aucun localStorage : ce module prend des
 * evenements et rend un etat. serialiser() et depuis() rendent et relisent une
 * chaine ; c'est volet.js qui decide ou elle est rangee.
 *
 * Le seul endroit ou le portage n'est PAS mecanique est empreinte() — voir
 * son commentaire.
 */

import {
  extraire, scores, en_mots, _deplier, _sans_accent, arrondi, NOMS, NOMS_TRAITS,
  classer,
  MARGE_DOMINANCE, PALIER_INDICES, PALIER_DIVERGENCE,
} from "./traits.js";

export { NOMS, PALIER_INDICES, PALIER_DIVERGENCE };

export const VERSION_ETAT = 2;

// --------------------------------------------------------------------------
// Constantes. Chacune a sa raison dans DECISIONS.md ; les changer sans lire
// l'entree correspondante casse quelque chose qui a ete paye cher.
// --------------------------------------------------------------------------
export const MOTS_PAR_PLANT = 5000;        // decision 6 : au-dela, le retour se perd
export const PARAGRAPHES_PAR_PLANT = 52;   // 5 000 / ~96 mots, soit 1,92 % par paragraphe
export const MOTS_MINIMUM_VERROU = 800;    // decision 5 : 16 % du segment, pas 0,58 % de la these
export const LECTURES_CONCORDANTES = 3;
// Le verrou demande "3 lectures concordantes d'affilee". Espacees en MOTS, pas
// en ticks : compter des appels a la mise a jour, dans un add-in cadence a 2 s,
// ferait valoir six secondes a une garantie qui ne garantirait rien.
export const MOTS_ENTRE_LECTURES = 100;
export const SEUIL_COLLAGE = 15;           // decision 4 : mots par intervalle de 2 s
export const HEURE_NUIT = [2, 5];          // decision 9 : la palette qui n'apparait nulle part ailleurs
export const MOTS_LISIBLES = 200;          // en dessous, rien n'est lisible : c'est un germe
export const SATURATION_REPRISES = 3.0;    // decision 2 : 1 - exp(-reprises/3)

const STYLES_TITRE = new Set(["titre 1", "heading 1", "titre1", "heading1"]);
const STYLES_IGNORES = new Set(["citation", "quote", "intense quote", "citation intense"]);

// --------------------------------------------------------------------------
// Empreintes (decision 3)
// --------------------------------------------------------------------------
// On plie la casse, les accents et les variantes typographiques du meme signe.
// Word remplace l'apostrophe droite par la courbe tout seul : sans ce pliage,
// une correction automatique ferait passer un paragraphe deja ecrit pour un
// paragraphe neuf, et la forme pousserait sans que personne n'ait ecrit.
const _VARIANTES = {
  "’": "'", "‘": "'", "“": '"', "”": '"',
  "«": '"', "»": '"', "—": "-", "–": "-",
  " ": " ", "…": "...",
};
const _A_PLIER = /[’‘“”«»—– …]/gu;
const _ESPACES = /\s+/gu;
// [\s\W_] en Python, c'est-a-dire tout ce qui n'est ni lettre ni chiffre.
// Ecrit tel quel ici, \W serait de l'ASCII et mangerait les lettres accentuees.
const _BORDS = /^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu;

export function normaliser(paragraphe) {
  // _deplier et non _sans_accent : un paragraphe ne se represente jamais deux
  // fois a l'identique, le mettre en cache ne fait que garder une copie du
  // document en memoire.
  const p = _deplier(paragraphe).toLowerCase().replace(_A_PLIER, (c) => _VARIANTES[c]);
  return p.replace(_BORDS, "").replace(_ESPACES, " ");
}

/**
 * MurmurHash3 32 bits sur les unites UTF-16. Deux graines, 48 bits gardes.
 *
 * C'EST LE SEUL ENDROIT OU LE PORTAGE N'EST PAS MECANIQUE. Le Python prend
 * blake2s(digest_size=6).
 *
 * Le motif d'abord invoque ici etait qu'un navigateur n'a pas de hachage
 * synchrone. C'est faux, et blake2s.js le prouve deux fichiers plus loin — il a
 * fallu l'ecrire pour graine_du_document(), qui ne peut PAS diverger. Le vrai
 * motif est le cout, mesure : sur 1 450 paragraphes, murmur3 prend 3,6 ms et
 * blake2s 29,6 ms. Ce n'est pas dans un tick que ca se voit — un tick ne hache
 * qu'un ou deux paragraphes — mais au scan complet de la decision 11, a chaque
 * ouverture du fichier, ou le budget est de 100 ms et ou une these de 2 400
 * paragraphes passerait de 21 a 64 ms pour rien.
 *
 * Pour rien, parce que rien ici ne demande un condensat cryptographique ni un
 * condensat PARTAGE : les deux implementations ne relisent jamais le registre
 * l'une de l'autre. La seule propriete utile est celle d'une table de hachage —
 * meme texte, meme cle ; textes differents, cles differentes sauf accident. On
 * garde donc la largeur du Python, 48 bits, 12 caracteres hexadecimaux : c'est
 * elle qui porte les 17 Ko pour 1 450 paragraphes annonces a la decision 3, et
 * elle qui fixe le risque de collision (moins de 2 chances sur 10 millions sur
 * 10 000 paragraphes). parite.js verifie que les deux fonctions decoupent le
 * meme document en le meme nombre d'empreintes distinctes — c'est la seule
 * chose que le reste du systeme observe d'elles.
 *
 * La graine du document, elle, est un autre cas : elle determine la FIGURE, et
 * une figure differente d'un cote a l'autre ferait mentir les planches. Elle
 * passe donc par le vrai blake2s.
 */
function _murmur(texte, graine) {
  let h = graine >>> 0;
  const n = texte.length;
  let i = 0;
  for (; i + 1 < n; i += 2) {
    let k = (texte.charCodeAt(i) | (texte.charCodeAt(i + 1) << 16)) >>> 0;
    k = Math.imul(k, 0xcc9e2d51) >>> 0;
    k = ((k << 15) | (k >>> 17)) >>> 0;
    k = Math.imul(k, 0x1b873593) >>> 0;
    h = (h ^ k) >>> 0;
    h = ((h << 13) | (h >>> 19)) >>> 0;
    h = (Math.imul(h, 5) + 0xe6546b64) >>> 0;
  }
  if (i < n) {
    let k = texte.charCodeAt(i) >>> 0;
    k = Math.imul(k, 0xcc9e2d51) >>> 0;
    k = ((k << 15) | (k >>> 17)) >>> 0;
    k = Math.imul(k, 0x1b873593) >>> 0;
    h = (h ^ k) >>> 0;
  }
  h = (h ^ n) >>> 0;
  h = (h ^ (h >>> 16)) >>> 0;
  h = Math.imul(h, 0x85ebca6b) >>> 0;
  h = (h ^ (h >>> 13)) >>> 0;
  h = Math.imul(h, 0xc2b2ae35) >>> 0;
  return (h ^ (h >>> 16)) >>> 0;
}

/** 6 octets, soit 12 caracteres hexadecimaux. */
export function empreinte(paragraphe) {
  const n = normaliser(paragraphe);
  const a = _murmur(n, 0x9747b28c);
  const b = _murmur(n, 0x85ebca6b);
  return a.toString(16).padStart(8, "0") + (b & 0xffff).toString(16).padStart(4, "0");
}

// --------------------------------------------------------------------------
// Un plant
// --------------------------------------------------------------------------
export class Segment {
  constructor(champs = {}) {
    this.rang = 0;
    this.jour = 0;              // date de creation -> palette (decision 9)
    this.heure = 14;
    this.titre = "";
    this.mots = 0;              // mots ECRITS ici (jamais les mots deplaces)
    this.nouveaux = 0;          // paragraphes ecrits    -> extension
    this.reprises = 0;          // retouches             -> maturite
    this.greffes = 0;           // colles, en attente
    // Les VRAIES dates d'ecriture, ponderees par les mots : {jour: mots}.
    // Sans elles, le rendu doit inventer une date par tour de ville, et la
    // ville affiche des saisons qui n'ont jamais eu lieu — alors que la
    // decision 9 fait porter la teinte par la date d'ecriture.
    this.jours = {};
    this.mots_de_nuit = 0;      // ecrits entre 2h et 5h
    this.textes = [];
    this.famille = null;
    this.candidate = null;
    this.confirmations = 0;
    this.mots_derniere_lecture = 0;
    this.scores_courants = {};
    this.scores_au_verrouillage = {};
    // Le vecteur de traits normalise, tel quel. C'est lui qui donne a chaque
    // plant sa physionomie propre : sans lui, tous les plants d'une meme
    // famille sont la meme figure au grain pres, et un paysage de vingt-sept
    // objets n'est plus que quatre formes repetees.
    this.traits_courants = {};
    Object.assign(this, champs);
  }

  // -- les deux axes (decision 2) ------------------------------------------
  /**
   * Combien de segments : ca pousse.
   *
   * Les deux bornes de la decision 6 doivent aller ensemble. Mesurer
   * l'extension en paragraphes (52) pendant qu'on ferme le plant en mots
   * (5 000) laisse quelqu'un qui ecrit des paragraphes de 250 mots plafonner a
   * 0,38 d'extension pour toujours : sa forme se ferme avant d'avoir fini de
   * pousser. On prend donc la plus avancee des deux, et le plant se ferme sur
   * la meme condition — l'extension vaut exactement 1 au moment ou le plant est
   * plein, quelle que soit la longueur des paragraphes.
   */
  get extension() {
    return Math.min(1.0, Math.max(this.nouveaux / PARAGRAPHES_PAR_PLANT,
                                  this.mots / MOTS_PAR_PLANT));
  }

  /**
   * Ce que devient un segment deja la : ca murit.
   *
   * Sature vers 5-6 passages. Le rapport reprises/paragraphes est la variable
   * juste : reprendre quarante fois UN paragraphe et reprendre une fois
   * quarante paragraphes ne sont pas le meme geste.
   */
  get maturite() {
    if (!this.nouveaux) return 0.0;
    return 1.0 - Math.exp(-(this.reprises / this.nouveaux) / SATURATION_REPRISES);
  }

  /** Enregistre quand ces mots ont ete ecrits. */
  dater(jour, heure, mots) {
    if (mots <= 0) return;
    const j = ((jour % 365) + 365) % 365;
    this.jours[j] = (this.jours[j] || 0) + mots;
    if (HEURE_NUIT[0] <= heure && heure < HEURE_NUIT[1]) this.mots_de_nuit += mots;
  }

  /** [[jour, poids]] tries : la vraie dispersion des dates du plant. */
  dates() {
    const cles = Object.keys(this.jours);
    if (!cles.length) return [[((this.jour % 365) + 365) % 365, 1]];
    return cles.map((k) => [Number(k), this.jours[k]]).sort((a, b) => a[0] - b[0]);
  }

  /**
   * Le plant prend la palette de nuit si l'essentiel de son texte a ete ecrit
   * entre 2h et 5h. La decision 9 parle des SEGMENTS ecrits la nuit, pas des
   * traits : une seule session a 3h ne doit pas semer du violet dans un plant
   * de jour, sinon l'easter egg devient un bruit de fond.
   */
  get nuit() {
    return this.mots > 0 && this.mots_de_nuit / this.mots > 0.5;
  }

  get plein() {
    return this.mots >= MOTS_PAR_PLANT || this.nouveaux >= PARAGRAPHES_PAR_PLANT;
  }

  get verrouille() {
    return this.famille !== null;
  }

  // -- verrou (decision 5) -------------------------------------------------
  /**
   * Une lecture, si le segment a gagne assez de mots depuis la derniere.
   *
   * Renvoie true si une lecture a eu lieu. Apres verrou les lectures
   * continuent : elles ne mesurent plus que la derive.
   */
  relire() {
    if (this.mots - this.mots_derniere_lecture < MOTS_ENTRE_LECTURES) return false;
    this.mots_derniere_lecture = this.mots;

    const t = extraire(this.textes.join("\n\n"));
    if (!t.mots) return false;
    const s = scores(t);
    this.scores_courants = s;
    this.traits_courants = {};
    for (const nom of NOMS_TRAITS) this.traits_courants[nom] = t[nom];

    const classement = classer(s);
    let pressentie = classement[0][0];
    const marge = classement[0][1] - classement[1][1];
    if (marge < MARGE_DOMINANCE && pressentie !== "abstrait") {
      pressentie = "abstrait";          // refus de classement
    }

    if (this.verrouille) return true;

    if (pressentie === this.candidate) {
      this.confirmations += 1;
    } else {
      this.candidate = pressentie;
      this.confirmations = 1;
    }

    if (this.mots >= MOTS_MINIMUM_VERROU && this.confirmations >= LECTURES_CONCORDANTES) {
      this.famille = pressentie;
      this.scores_au_verrouillage = { ...s };
    }
    return true;
  }

  /** Derive depuis le verrouillage : ce qui produit les traits hybrides. */
  influences() {
    if (!this.verrouille || !Object.keys(this.scores_courants).length) return {};
    const sortie = {};
    for (const [nom, valeur] of Object.entries(this.scores_courants)) {
      if (nom === this.famille) continue;
      const reference = nom in this.scores_au_verrouillage
        ? this.scores_au_verrouillage[nom] : valeur;
      const derive = valeur - reference;
      if (derive > 0.02) sortie[nom] = arrondi(Math.min(1.0, derive * 2.5), 3);
    }
    return sortie;
  }

  stade() {
    if (this.verrouille) return "croissance";
    return this.mots < MOTS_LISIBLES ? "germe" : "indices";
  }
}

// --------------------------------------------------------------------------
// Le paysage
// --------------------------------------------------------------------------
/**
 * Le paysage appartient au DOSSIER (decision 11).
 *
 * L'identifiant est tire une fois et recopie dans les Settings de chaque
 * document du dossier. C'est lui qui fait autorite, pas le nom du dossier :
 * deux theses rangees dans deux dossiers nommes "Chapitres" partageraient
 * sinon le meme paysage. Le nom du dossier ne sert plus qu'a rattacher un
 * document neuf a un paysage existant.
 */
export class Paysage {
  constructor(champs = {}) {
    this.identifiant = "";
    this.cle_dossier = "";
    this.registre = new Set();
    this.segments = [];
    this.version = VERSION_ETAT;

    // Le curseur. Etat de session, jamais serialise : a la reouverture, plus
    // rien n'est en construction, ce qui est exact.
    //
    // Il resout un manque de la decision 2. Dans Word, ecrire un paragraphe
    // pour la premiere fois et y revenir trois jours plus tard produisent la
    // MEME suite d'evenements : onParagraphChanged, N fois. Lire ces
    // changements comme des reprises, c'est une premiere redaction qui ne fait
    // jamais pousser la forme ; les lire comme de l'ecriture, c'est rouvrir
    // l'exploit que la decision 2 ferme — allonger un paragraphe indefiniment
    // ferait grandir la plante.
    //
    // La separation juste n'est pas dans le texte, elle est dans le curseur :
    // un paragraphe est en construction tant qu'on ne l'a pas quitte. Une fois
    // quitte, il est ecrit ; y revenir est une reprise, et une seule par
    // visite — sinon dix minutes de reecriture compteraient trois cents
    // passages la ou la decision 2 en attend cinq ou six.
    this._actif = "";
    this._mode = "";          // "frappe" ou "reprise"
    Object.assign(this, champs);
  }

  // ----------------------------------------------------------------- plants
  _plant(jour, heure) {
    if (!this.segments.length) {
      this.segments.push(new Segment({ rang: 0, jour, heure }));
    }
    return this.segments[this.segments.length - 1];
  }

  _nouveau_plant(jour, heure, titre = "") {
    // Un plant ouvert par debordement (5 000 mots) appartient encore au
    // chapitre en cours : il herite de la parcelle. Sans cet heritage, la
    // hierarchie du point 6 — paysage, parcelles, plants — n'existe que pour
    // les plants ouverts par un Titre 1, c'est-a-dire un sur trois.
    if (!titre && this.segments.length) {
      titre = this.segments[this.segments.length - 1].titre;
    }
    const s = new Segment({ rang: this.segments.length, jour, heure, titre });
    this.segments.push(s);
    return s;
  }

  // ---------------------------------------------------------------- collage
  /**
   * Un paragraphe arrive. Ordre de verification strict (decision 4) :
   *
   *     1. empreinte deja connue          -> rien
   *     2. inconnue + arrivee progressive -> ecriture
   *     3. inconnue + arrivee instantanee -> greffe
   *     4. greffe ensuite retouchee       -> ecriture   (voir retoucher)
   *
   * Le registre passe AVANT le test de vitesse : sinon la fusion de douze
   * chapitres dans le document maitre est lue comme un collage geant.
   */
  absorber(texte, style = "Normal", mots_par_intervalle = 0, jour = 0,
           heure = 14, naissance = false) {
    // _sans_accent et non _deplier : contrairement a un paragraphe, un nom de
    // style revient a chaque appel et se compte sur les doigts. C'est le cas
    // pour lequel la memoire a ete faite.
    const st = _sans_accent(style || "").toLowerCase().trim();

    // Filtre gratuit : une citation ne compte jamais.
    if (STYLES_IGNORES.has(st)) return "ignoree";

    // Un paragraphe SANS MOTS n'est pas encore un paragraphe.
    //
    // Word en cree un a chaque retour a la ligne, avant qu'on ait tape quoi que
    // ce soit. Sans ce filtre, l'empreinte du vide entre au registre au premier
    // Entree — et tous les retours a la ligne suivants sont lus comme
    // « connue », donc le plant CESSE DE POUSSER au deuxieme paragraphe.
    // rattacher() filtrait deja le vide ; absorber() ne le faisait pas.
    if (!en_mots(texte).length) return "vide";

    const e = empreinte(texte);

    // 1. Connue : rien. Ni croissance, ni mots, ni traits, ET PAS DE PLANT
    //    NEUF meme sur un Titre 1 — sans quoi le scan complet a l'ouverture
    //    (decision 11) rouvrirait un plant a chaque titre deja connu, a chaque
    //    ouverture du fichier. Le registre passe avant tout le reste. C'est ce
    //    qui rend un deplacement, une fusion et une suppression gratuits.
    //    `naissance` est l'exception. Un paragraphe qu'on TAPE passe par
    //    tous ses etats intermediaires, et chacun entre au registre. Or « Il
    //    faut donc admettre » a toutes les chances d'avoir deja commence un
    //    autre paragraphe : en francais, un paragraphe sur deux debute par les
    //    memes quatre mots. Le registre declarait alors « connue » un
    //    paragraphe genuinement neuf, et LE PLANT CESSAIT DE POUSSER — sans
    //    rien signaler. Quand l'appelant a VU le paragraphe naitre vide sous
    //    le curseur, il sait ce que le registre ne peut pas savoir.
    if (this.registre.has(e) && !naissance) return "connue";

    // Un Titre 1 ouvre un plant (decision 6) — sauf si le plant courant vient
    // tout juste de naitre. Quand un chapitre commence peu apres qu'un plant
    // s'est rempli, ouvrir quand meme laisse derriere soi un moignon de
    // quelques dizaines de mots, qui n'atteindra jamais les 800 mots du verrou
    // et restera un germe pour toujours. En dessous du seuil de lisibilite, le
    // titre reprend le plant en cours au lieu d'en ouvrir un neuf.
    if (STYLES_TITRE.has(st)) {
      const courant = this.segments.length ? this.segments[this.segments.length - 1] : null;
      if (courant !== null && courant.mots < MOTS_LISIBLES) {
        courant.titre = texte.trim();
      } else {
        this._nouveau_plant(jour, heure, texte.trim());
      }
    }

    let plant = this._plant(jour, heure);
    if (plant.plein) plant = this._nouveau_plant(jour, heure);

    this.registre.add(e);

    // 3. Inconnue et arrivee d'un bloc : greffe, en attente.
    if (mots_par_intervalle > SEUIL_COLLAGE) {
      plant.greffes += 1;
      plant.textes.push(texte);
      return "greffe";
    }

    // 2. Inconnue et arrivee progressive : ca pousse.
    plant.nouveaux += 1;
    const n = en_mots(texte).length;
    plant.mots += n;
    plant.dater(jour, heure, n);
    plant.textes.push(texte);
    this._actif = e;
    this._mode = "frappe";
    plant.relire();
    return "ecriture";
  }

  /**
   * Le curseur sort du paragraphe. Dans l'add-in : changement de selection,
   * sauvegarde, fermeture. A partir de la, le paragraphe est ecrit — y revenir
   * sera une reprise.
   */
  quitter() {
    this._actif = "";
    this._mode = "";
  }

  /**
   * Un paragraphe deja present change : c'est de la MATURITE, pas de
   * l'extension. C'est la decision centrale du projet — reprendre quarante fois
   * la meme phrase produit un element somptueux sur une forme qui n'a pas
   * grandi, et tripoter ne peut donc pas simuler de la croissance.
   *
   * Une greffe retouchee se convertit en ecriture : une citation ne se
   * retouche jamais, un brouillon rapporte d'ailleurs se retravaille toujours.
   * Le cas se resout seul, sans rien demander a personne.
   */
  retoucher(ancien, nouveau, jour = 0, heure = 14, etait_greffe = false,
            mots_par_intervalle = 0) {
    const e = empreinte(nouveau);
    if (empreinte(ancien) === e) return "inchangee";

    const plant = this._plant(jour, heure);
    this.registre.add(e);          // cette version-la existe maintenant
    const vieille = empreinte(ancien);
    for (let i = 0; i < plant.textes.length; i++) {
      if (empreinte(plant.textes[i]) === vieille) {
        plant.textes[i] = nouveau;
        break;
      }
    }

    if (etait_greffe) {
      plant.greffes = Math.max(0, plant.greffes - 1);
      plant.nouveaux += 1;
      const n = en_mots(nouveau).length;
      plant.mots += n;
      plant.dater(jour, heure, n);
      this._actif = e;
      this._mode = "frappe";
      plant.relire();
      return "conversion";
    }

    if (vieille === this._actif && this._mode === "frappe") {
      // Meme visite, premiere redaction : c'est encore de l'ecriture — SAUF si
      // ca arrive d'un bloc, auquel cas c'est une greffe, comme dans
      // absorber(). La decision 4 ne gardait que celui-la, et coller dans la
      // ligne qu'on est EN TRAIN d'ecrire ajoutait tous les mots colles sans
      // le moindre controle. C'est le trou par lequel un vrai document est
      // passe d'une tige a un arbre entier en trois collages.
      if (mots_par_intervalle > SEUIL_COLLAGE) {
        plant.greffes += 1;
        this._actif = e;
        return "greffe";
      }
      // Les mots comptent, aucune reprise n'est enregistree.
      const ajout = Math.max(0, en_mots(nouveau).length - en_mots(ancien).length);
      plant.mots += ajout;
      plant.dater(jour, heure, ajout);
      this._actif = e;
      plant.relire();
      return "frappe";
    }

    if (vieille === this._actif && this._mode === "reprise") {
      // Meme visite, deja comptee. On suit le texte sans rien ajouter.
      this._actif = e;
      plant.relire();
      return "reprise en cours";
    }

    // Nouvelle visite sur un paragraphe deja ecrit : une reprise, une seule.
    // Les mots ajoutes NE COMPTENT PAS dans l'extension — sinon rallonger sans
    // fin le meme paragraphe ferait pousser la forme, et tripoter redeviendrait
    // un moyen de simuler de la croissance.
    plant.reprises += 1;
    this._actif = e;
    this._mode = "reprise";
    plant.relire();
    return "reprise";
  }

  // -------------------------------------------------------------- ouverture
  /**
   * Rattachement initial : tout ce qui est deja la est acquis comme capital de
   * depart (decision 11). Personne n'a a recommencer sa these pour que le
   * cadeau ait un sens.
   *
   * Accepte des chaines ou des couples [texte, style] : les Titre 1 du document
   * existant decoupent deja le paysage en parcelles.
   */
  rattacher(paragraphes, jour = 0, heure = 14) {
    for (const item of paragraphes) {
      const [p, style] = Array.isArray(item) ? item : [item, "Normal"];
      if (!p.trim()) continue;
      const st = _sans_accent(style || "").toLowerCase().trim();
      if (STYLES_IGNORES.has(st)) continue;
      const e = empreinte(p);
      if (this.registre.has(e)) continue;
      this.registre.add(e);
      if (STYLES_TITRE.has(st)) this._nouveau_plant(jour, heure, p.trim());
      let plant = this._plant(jour, heure);
      if (plant.plein) plant = this._nouveau_plant(jour, heure);
      plant.nouveaux += 1;
      const n = en_mots(p).length;
      plant.mots += n;
      plant.dater(jour, heure, n);
      plant.textes.push(p);
      plant.relire();
    }
  }

  // ------------------------------------------------------------------ rendu
  etat() {
    return {
      identifiant: this.identifiant,
      plants: this.segments.map((s) => ({
        rang: s.rang,
        famille: s.famille,
        pressentie: s.verrouille ? null : s.candidate,
        stade: s.stade(),
        mots: s.mots,
        extension: arrondi(s.extension, 3),
        maturite: arrondi(s.maturite, 3),
        greffes: s.greffes,
        dates: s.dates(),
        nuit: s.nuit,
        titre: s.titre,
        traits: { ...s.traits_courants },
        // De quoi dessiner un plant qui n'a pas encore de famille.
        germe: s.verrouille ? null : {
          taille: Math.min(1.0, s.mots / PALIER_DIVERGENCE),
          inflexion: Math.max(0.0, Math.min(1.0,
            (s.mots - PALIER_INDICES)
            / Math.max(PALIER_DIVERGENCE - PALIER_INDICES, 1))),
        },
        influences: s.influences(),
      })),
      mots: this.segments.reduce((a, s) => a + s.mots, 0),
      empreintes: this.registre.size,
    };
  }

  // ------------------------------------------------------------ persistance
  serialiser() {
    return JSON.stringify({
      version: this.version,
      identifiant: this.identifiant,
      cle_dossier: this.cle_dossier,
      registre: [...this.registre].sort(),
      segments: this.segments.map((s) => {
        const brut = {};
        for (const [k, v] of Object.entries(s)) {
          if (k !== "textes") brut[k] = v;
        }
        return brut;
      }),
    });
  }

  static depuis(brut) {
    if (!brut) return new Paysage();
    let d;
    try {
      d = JSON.parse(brut);
    } catch {
      return new Paysage();
    }
    // "[]" et "null" sont du JSON valide : sans le test de forme, on lirait
    // .version sur une liste ou sur null. Un paysage illisible repart vide,
    // jamais en erreur — au chargement il n'y a personne pour rattraper.
    if (!d || typeof d !== "object" || Array.isArray(d)
        || d.version !== VERSION_ETAT) return new Paysage();
    const p = new Paysage({
      identifiant: d.identifiant || "",
      cle_dossier: d.cle_dossier || "",
      registre: new Set(d.registre || []),
    });
    for (const brut_s of d.segments || []) {
      p.segments.push(new Segment(brut_s));
    }
    return p;
  }
}

// Voir le commentaire de TABLES dans traits.js : derivees, jamais recopiees.
export const TABLES = {
  STYLES_TITRE: [...STYLES_TITRE].sort(),
  STYLES_IGNORES: [...STYLES_IGNORES].sort(),
  VARIANTES: _VARIANTES,
  MOTS_PAR_PLANT,
  PARAGRAPHES_PAR_PLANT,
  MOTS_MINIMUM_VERROU,
  LECTURES_CONCORDANTES,
  MOTS_ENTRE_LECTURES,
  SEUIL_COLLAGE,
  HEURE_NUIT: [...HEURE_NUIT],
  MOTS_LISIBLES,
  SATURATION_REPRISES,
  VERSION_ETAT,
};

export function resume(paysage) {
  const lignes = [];
  for (const s of paysage.segments) {
    let etat;
    let infl = "";
    if (s.verrouille) {
      infl = Object.entries(s.influences())
        .sort((a, b) => b[1] - a[1]).slice(0, 2)
        .map(([k, v]) => `${NOMS[k]} +${v.toFixed(2)}`).join(", ");
      etat = `${NOMS[s.famille].toUpperCase().padEnd(13)} verrouille`;
    } else {
      const pressentie = s.candidate ? NOMS[s.candidate] : "-";
      etat = `${s.stade().padEnd(13)} (${pressentie})`;
    }
    lignes.push(`  plant ${String(s.rang).padStart(2)} | ${String(s.mots).padStart(5)} mots`
      + ` | ${etat} | ext ${s.extension.toFixed(2)} mat ${s.maturite.toFixed(2)}`
      + (infl ? ` | ${infl}` : ""));
  }
  return lignes.join("\n");
}
