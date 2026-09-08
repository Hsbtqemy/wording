/**
 * Extraction des traits d'un texte et determination de la famille qui pousse.
 *
 * Portage mecanique de jardin/traits.py. Le Python reste la specification :
 * quand les deux divergent, c'est le Python qui a raison et ce fichier qui a
 * un bug. Les noms, l'ordre des fonctions et les commentaires de fond suivent
 * l'original pour qu'on puisse lire les deux cote a cote sans traduire.
 *
 * Ce que le portage ne peut pas rendre a l'identique, et pourquoi :
 *
 *   \w        Python le lit en Unicode, JavaScript en ASCII. Partout ou le
 *             Python ecrit \w ou \W, ce fichier ecrit \p{L}\p{N} : c'est la
 *             meme classe, ecrite explicitement. Sans ca, "elephant" reste un
 *             mot et "elephant" avec accent n'en est plus un.
 *
 *   \d        idem : \p{Nd}, la classe que Python entend.
 *
 *   $         Python le fait matcher aussi devant un saut de ligne final,
 *             JavaScript non. Le seul endroit concerne est FIN_DE_PHRASE, ou
 *             l'autre branche du OU rattrape le cas : un texte finissant par
 *             ".\n" se coupe pareil des deux cotes. parite.js le verifie.
 *
 *   round     arrondi() plus bas.
 *
 * Aucune dependance, aucune API Word, aucun DOM : ce module prend du texte et
 * rend des nombres. C'est volet.js qui va chercher le texte dans Word.
 */

// --------------------------------------------------------------------------
// Paliers de revelation (en mots). A recalibrer en testant sur de vrais textes.
// --------------------------------------------------------------------------
export const PALIER_INDICES = 200;      // le germe commence a s'orienter
export const PALIER_DIVERGENCE = 800;   // la famille devient lisible

// En dessous de cette marge entre le 1er et le 2e score, aucune famille ne
// domine vraiment : c'est l'abstrait qui l'emporte, par refus de classement.
export const MARGE_DOMINANCE = 0.06;

// --------------------------------------------------------------------------
// Outils de normalisation
// --------------------------------------------------------------------------
export function borne(x, bas, haut) {
  if (haut === bas) return 0.0;
  return Math.max(0.0, Math.min(1.0, (x - bas) / (haut - bas)));
}

/**
 * L'equivalent de round(x, n) en Python. Aucun outil de JavaScript ne le fait
 * seul : il faut composer deux moities.
 *
 * Python arrondit la valeur BINAIRE EXACTE, et tranche un demi exact vers le
 * PAIR. Les trois candidats evidents ratent l'un ou l'autre :
 *
 *   Math.round(x * 10**n) / 10**n    la multiplication a sa propre erreur et
 *                                    fait basculer des valeurs que Python ne
 *                                    bascule pas — 0,00035 monte alors que le
 *                                    flottant est en dessous de 0,00035.
 *   x.toFixed(n)                     lit bien la valeur exacte, mais tranche
 *                                    un demi exact vers le HAUT : 0,40625
 *                                    donne 0,4063 la ou Python donne 0,4062.
 *   Intl roundingMode "halfEven"     tranche bien vers le pair, mais part de
 *                                    l'ecriture decimale COURTE et non de la
 *                                    valeur exacte : 0,00035 remonte a 0,0004.
 *
 * On prend donc toFixed, et on ne rattrape que le demi exact. Il se reconnait
 * sans approximation : x * 10^n vaut un demi pile si et seulement si x est un
 * multiple de 2^-(n+1) et pas de 2^-n — c'est-a-dire si x * 2^(n+1) est un
 * entier IMPAIR. La multiplication par une puissance de deux est exacte, donc
 * le test l'est aussi. Et dans ce cas x n'a que n+1 bits apres la virgule,
 * donc x * 10^n est exact lui aussi : on peut arrondir a la main.
 */
export function arrondi(x, n) {
  const d = x * 2 ** (n + 1);
  if (Number.isInteger(d) && d % 2 !== 0) {
    const y = x * 10 ** n;              // exact : x est un multiple de 2^-(n+1)
    const bas = Math.floor(y);          // y vaut bas + 0,5
    return (bas % 2 === 0 ? bas : bas + 1) / 10 ** n;
  }
  return parseFloat(x.toFixed(n));
}

export function coefficient_variation(valeurs) {
  if (valeurs.length < 2) return 0.0;
  const moy = valeurs.reduce((a, b) => a + b, 0) / valeurs.length;
  if (moy === 0) return 0.0;
  let var_ = 0;
  for (const v of valeurs) var_ += (v - moy) ** 2;
  var_ /= valeurs.length;
  return Math.sqrt(var_) / moy;
}

// --------------------------------------------------------------------------
// Decoupage
// --------------------------------------------------------------------------
const FIN_DE_PHRASE = /[.!?…]+[\s ]+|[.!?…]+$/u;
const MOT = /\p{L}+/gu;
const NUMEROTATION = /^\p{Nd}+[.)]\s/u;

// Abreviations frequentes en francais, pour eviter les fausses coupures.
const ABREVIATIONS = new Set([
  "m", "mme", "mlle", "dr", "pr", "st", "ste", "cf", "etc", "ex",
  "av", "ap", "env", "p", "pp", "vol", "no", "fig", "art",
]);

export function en_mots(texte) {
  return texte.match(MOT) || [];
}

/** Decoupage naif mais suffisant : on protege les abreviations connues. */
export function en_phrases(texte) {
  const brut = texte.split(FIN_DE_PHRASE);
  const phrases = [];
  let tampon = "";
  for (let morceau of brut) {
    if (morceau === undefined || morceau === null) continue;
    morceau = morceau.trim();
    if (!morceau) continue;
    const candidat = tampon ? (tampon + " " + morceau).trim() : morceau;
    const dernier = en_mots(candidat);
    if (dernier.length
        && ABREVIATIONS.has(_sans_accent(dernier[dernier.length - 1]).toLowerCase())) {
      tampon = candidat;
      continue;
    }
    phrases.push(candidat);
    tampon = "";
  }
  if (tampon) phrases.push(tampon);
  return phrases.filter((p) => en_mots(p).length);
}

export function en_paragraphes(texte) {
  const lignes = texte.replace(/\r\n/g, "\n").split("\n").map((l) => l.trim());
  let paragraphes = [];
  let courant = [];
  for (const ligne of lignes) {
    if (ligne) courant.push(ligne);
    else if (courant.length) {
      paragraphes.push(courant.join(" "));
      courant = [];
    }
  }
  if (courant.length) paragraphes.push(courant.join(" "));
  // Si le texte n'utilise pas de ligne vide, chaque ligne est un paragraphe.
  if (paragraphes.length <= 1) paragraphes = lignes.filter((l) => l);
  return paragraphes;
}

const _MARQUES = /\p{Mn}/gu;

/** Depose les accents. Sans memoire : a utiliser sur autre chose qu'un mot. */
export function _deplier(texte) {
  return texte.normalize("NFD").replace(_MARQUES, "");
}

// Memoire de normalisation. Le vocabulaire d'un document est borne (~30 000
// formes pour une these) alors que les appels se comptent en centaines de
// milliers : sans ce cache, la normalisation Unicode represente l'essentiel du
// temps d'extraction une fois MATTR passe en O(n).
//
// Le cache ne vaut que si la cle revient : sur un MOT, des centaines de fois ;
// sur un PARAGRAPHE, jamais. Y faire passer les paragraphes remplissait le
// cache de 2,8 Mo sur une these de 146 000 mots, sans une seule relecture.
// Tout ce qui n'est pas un mot passe par _deplier.
const _ACCENTS = new Map();

export function _sans_accent(mot) {
  const connu = _ACCENTS.get(mot);
  if (connu !== undefined) return connu;
  const nu = _deplier(mot);
  _ACCENTS.set(mot, nu);
  return nu;
}

// --------------------------------------------------------------------------
// Signaux bruts
// --------------------------------------------------------------------------
// Attention : le tiret cadratin (—) est EXCLU des puces. En francais il
// introduit une replique de dialogue, pas un element de liste. Le confondre
// faisait basculer toute la fiction dialoguee vers Architecture.
const PUCES = ["*", "•", "◦", "·"];
const TIRET_REPLIQUE = /^[—–]\s+/u;
// Une paire de guillemets n'est un dialogue que si elle enferme un enonce.
// Sur un mot isole, c'est une mise a distance (« bruit », « symptome »), ce qui
// est un marqueur d'essai, pas de fiction.
const PAIRE_GUILLEMETS = /«([^»]{0,400})»|“([^”]{0,400})”/gu;
const MOTS_MINIMUM_ENONCE = 4;
const PONCTUATION_RARE = /[;:—–()[\]…]/gu;
const FINS_DE_PHRASE_CHARS = ".!?…:;,";

const CONNECTEURS_SUBORDINATION = new Set([
  "que", "qui", "dont", "lequel", "laquelle", "lesquels", "lesquelles",
  "parce", "puisque", "quoique", "bien", "alors", "tandis", "lorsque",
  "afin", "pourvu", "malgre", "cependant", "toutefois", "neanmoins",
  "ainsi", "donc", "or", "car", "mais", "comme", "si", "quand",
]);

/**
 * Heuristique de titre / element de liste, pour du texte brut.
 *
 * Dans l'add-in Word, on ne passe PAS par ici : volet.js lit le style reel du
 * paragraphe (Heading 1, List Paragraph...), ce qui est bien plus fiable. La
 * fonction reste pour que le banc d'essai lise le meme texte que le Python.
 */
export function est_structurel(paragraphe) {
  const p = paragraphe.trim();
  if (!p) return false;
  // Une replique de dialogue n'est jamais un element de structure.
  if (TIRET_REPLIQUE.test(p)) return false;
  if (p.startsWith("#")) return true;
  if (PUCES.some((puce) => p.startsWith(puce + " "))) return true;
  if (p.startsWith("- ")) return true;
  if (NUMEROTATION.test(p)) return true;
  // Ligne courte, sans ponctuation finale : tres probablement un titre.
  // Python compte des POINTS DE CODE, ici et pour le dernier caractere :
  // len(p) et p[-1]. Les equivalents en unites UTF-16 (p.length, p.charAt)
  // donnent une autre longueur et un demi-substitut a la place du dernier
  // caractere des qu'un signe sort du plan de base.
  const points = [...p];
  if (points.length < 60
      && !FINS_DE_PHRASE_CHARS.includes(points[points.length - 1])
      && en_mots(p).length <= 9) return true;
  return false;
}

/**
 * Moving-Average Type-Token Ratio.
 *
 * Le TTR brut chute mecaniquement quand le texte s'allonge : utiliser le TTR
 * brut ici ferait deriver la famille au fil de la redaction, ce qui est
 * exactement ce qu'on ne veut pas. La moyenne glissante rend la mesure stable
 * quelle que soit la longueur.
 */
export function mattr(mots, fenetre = 200) {
  if (!mots.length) return 0.0;
  const formes = mots.map((m) => _sans_accent(m).toLowerCase());
  if (formes.length <= fenetre) return new Set(formes).size / formes.length;

  // Fenetre glissante a comptes courants : O(n) au lieu de O(n x fenetre).
  // Refaire un Set a chaque decalage coutait 772 ms sur 146 000 mots, soit
  // 70 % du temps d'extraction, et c'est ce qui a fait croire que MATTR devait
  // etre mis en cache pour tenir dans le budget de 100 ms.
  const comptes = new Map();
  for (let i = 0; i < fenetre; i++) {
    const f = formes[i];
    comptes.set(f, (comptes.get(f) || 0) + 1);
  }
  let distincts = comptes.size;
  let total = distincts / fenetre;
  let fenetres = 1;
  for (let i = fenetre; i < formes.length; i++) {
    const sortant = formes[i - fenetre];
    const reste = comptes.get(sortant) - 1;
    if (reste === 0) {
      comptes.delete(sortant);
      distincts -= 1;
    } else {
      comptes.set(sortant, reste);
    }
    const entrant = formes[i];
    const present = comptes.get(entrant);
    if (present === undefined) {
      distincts += 1;
      comptes.set(entrant, 1);
    } else {
      comptes.set(entrant, present + 1);
    }
    total += distincts / fenetre;
    fenetres += 1;
  }
  return total / fenetres;
}

// --------------------------------------------------------------------------
// Vecteur de traits
// --------------------------------------------------------------------------
// Les neuf traits normalises, plus reecriture. mots / phrases / paragraphes
// sont des comptes, pas des traits : en Python le tri se fait sur le type
// (isinstance float), qui n'existe pas ici — la liste est donc explicite.
export const NOMS_TRAITS = [
  "longueur",          // phrases longues
  "rythme",            // irregularite de la longueur des phrases
  "subordination",     // densite de virgules et de connecteurs
  "regularite",        // regularite de la longueur des paragraphes
  "structure",         // titres, listes, blocs
  "dialogue",          // guillemets, tirets de replique
  "interrogation",     // densite de points d'interrogation
  "diversite",         // richesse lexicale (MATTR)
  "ponctuation_rare",  // ; : parentheses tirets points de suspension
  "reecriture",        // signal comportemental, fourni par l'add-in
];

function traits_vides() {
  const t = { mots: 0, phrases: 0, paragraphes: 0 };
  for (const nom of NOMS_TRAITS) t[nom] = 0.0;
  return t;
}

function compter(texte, signe) {
  let n = 0;
  let i = texte.indexOf(signe);
  while (i !== -1) {
    n += 1;
    i = texte.indexOf(signe, i + 1);
  }
  return n;
}

/** Calcule le vecteur de traits normalise d'un texte. */
export function extraire(texte, reecriture = 0.0) {
  const mots = en_mots(texte);
  const phrases = en_phrases(texte);
  const paragraphes = en_paragraphes(texte);

  if (!mots.length || !phrases.length) return traits_vides();

  const longueurs_phrases = phrases.map((p) => en_mots(p).length).filter((l) => l > 0);
  const longueurs_paragraphes = paragraphes.map((p) => en_mots(p).length).filter((l) => l > 0);

  const longueur_moy = longueurs_phrases.reduce((a, b) => a + b, 0) / longueurs_phrases.length;
  const cv_phrases = coefficient_variation(longueurs_phrases);
  const cv_paragraphes = coefficient_variation(longueurs_paragraphes);

  const virgules_par_phrase = compter(texte, ",") / phrases.length;
  // On compte les OCCURRENCES pour cent mots, pas les types presents.
  // Compter les types etait une couverture de vocabulaire : elle croit avec la
  // longueur et sature vers 1 100 mots, donc a l'echelle d'un segment de 2 500
  // mots tout texte francais valait 1,00 et la composante ne distinguait plus
  // rien. C'est exactement la derive mecanique reprochee au TTR brut, par une
  // autre porte.
  let occurrences = 0;
  for (const m of mots) {
    if (CONNECTEURS_SUBORDINATION.has(_sans_accent(m).toLowerCase())) occurrences += 1;
  }
  const connecteurs = (occurrences / mots.length) * 100;

  let enonces = 0;
  for (const paire of texte.matchAll(PAIRE_GUILLEMETS)) {
    const contenu = paire[1] || paire[2] || "";
    if (en_mots(contenu).length >= MOTS_MINIMUM_ENONCE) enonces += 1;
  }
  let repliques = 0;
  for (const p of paragraphes) if (TIRET_REPLIQUE.test(p.trim())) repliques += 1;
  const densite_dialogue = ((2 * enonces + 3 * repliques) / Math.max(mots.length, 1)) * 100;

  const interro = compter(texte, "?") / phrases.length;
  const rares = ((texte.match(PONCTUATION_RARE) || []).length / Math.max(mots.length, 1)) * 100;
  let structurels = 0;
  for (const p of paragraphes) if (est_structurel(p)) structurels += 1;
  const part_structurelle = structurels / paragraphes.length;

  return {
    mots: mots.length,
    phrases: phrases.length,
    paragraphes: paragraphes.length,
    longueur: borne(longueur_moy, 8, 45),   // 30 saturait toute these : voir traits.py
    rythme: borne(cv_phrases, 0.30, 1.00),
    subordination: 0.7 * borne(virgules_par_phrase, 0.3, 3.0)
                 + 0.3 * borne(connecteurs, 0.5, 6.0),
    regularite: 1.0 - borne(cv_paragraphes, 0.20, 1.20),
    structure: borne(part_structurelle, 0.0, 0.35),
    dialogue: borne(densite_dialogue, 0.0, 4.0),
    interrogation: borne(interro, 0.0, 0.15),
    diversite: borne(mattr(mots), 0.55, 0.80),
    ponctuation_rare: borne(rares, 0.3, 3.0),
    reecriture: Math.max(0.0, Math.min(1.0, reecriture)),
  };
}

// --------------------------------------------------------------------------
// Familles
// --------------------------------------------------------------------------
// L'ordre compte : a egalite de score, c'est lui qui departage, ici comme dans
// le dict Python. Un tri stable des deux cotes suffit alors a donner le meme
// classement — a condition de partir du meme ordre.
export const FAMILLES = ["vegetal", "architecture", "creature", "abstrait"];

// Poids explicites, faits pour etre bidouilles. Chaque entree est
// [nom_du_trait, poids, inverser].
export const POIDS = {
  vegetal: [
    ["subordination", 0.34, false],
    ["longueur", 0.26, false],
    ["regularite", 0.22, true],
    ["structure", 0.18, true],
  ],
  architecture: [
    ["structure", 0.40, false],
    ["regularite", 0.24, false],
    ["longueur", 0.20, true],
    ["subordination", 0.16, true],
  ],
  // L'interrogation pese peu : l'essai est plein de questions rhetoriques, et
  // lui donner du poids faisait passer la philosophie pour du dialogue.
  creature: [
    ["dialogue", 0.52, false],
    ["rythme", 0.33, false],
    ["interrogation", 0.15, false],
  ],
  abstrait: [
    ["diversite", 0.58, false],
    ["ponctuation_rare", 0.42, false],
  ],
};

export const NOMS = {
  vegetal: "Vegetal",
  architecture: "Architecture",
  creature: "Creature",
  abstrait: "Abstrait",
};

/** Score 0..1 pour chaque famille. */
export function scores(traits) {
  const resultat = {};
  for (const famille of FAMILLES) {
    let total = 0.0;
    for (const [nom, poids, inverser] of POIDS[famille]) {
      const v = traits[nom];
      total += poids * (inverser ? 1.0 - v : v);
    }
    resultat[famille] = arrondi(total, 4);
  }
  return resultat;
}

/** Le classement, du plus fort au plus faible. Stable, comme sorted(). */
export function classer(s) {
  return FAMILLES.map((f) => [f, s[f]]).sort((a, b) => b[1] - a[1]);
}

// --------------------------------------------------------------------------
// Les tables litterales, rassemblees pour que parite.js verifie qu'elles n'ont
// pas derive. C'est la panne la plus probable d'un projet a deux langages et la
// plus silencieuse : on ajoute un connecteur d'un seul cote, rien ne casse, le
// texte se lit juste un peu differemment.
//
// Elles sont DERIVEES des constantes ci-dessus, jamais recopiees : une table
// recopiee serait un second endroit ou se tromper, et le jour ou les deux
// divergeraient c'est la copie qui serait comparee.
export const TABLES = {
  ABREVIATIONS: [...ABREVIATIONS].sort(),
  PUCES: [...PUCES],
  CONNECTEURS_SUBORDINATION: [...CONNECTEURS_SUBORDINATION].sort(),
  MOTS_MINIMUM_ENONCE,
  PALIER_INDICES,
  PALIER_DIVERGENCE,
  MARGE_DOMINANCE,
  FAMILLES: [...FAMILLES],
  POIDS,
  NOMS,
};

export function revele(traits) {
  const s = scores(traits);
  const classement = classer(s);
  const premier = classement[0];
  const second = classement[1];
  const marge = premier[1] - second[1];

  let par_refus = false;
  let famille = premier[0];
  if (marge < MARGE_DOMINANCE && famille !== "abstrait") {
    famille = "abstrait";
    par_refus = true;
  }

  let stade;
  let provisoire;
  let visible;
  if (traits.mots < PALIER_INDICES) {
    stade = "germe"; provisoire = true; visible = null;
  } else if (traits.mots < PALIER_DIVERGENCE) {
    stade = "indices"; provisoire = true; visible = famille;
  } else {
    stade = "divergence"; provisoire = false; visible = famille;
  }

  const suivante = classement.find(([n]) => n !== famille);
  return {
    stade,
    famille: visible,
    provisoire,
    par_refus,
    marge: arrondi(marge, 4),
    secondaire: suivante ? suivante[0] : null,
    scores: s,
    traits,
  };
}
