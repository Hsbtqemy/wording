/**
 * Le verificateur de parite sait-il echouer ?
 *
 *     node addin/parite/mutations.js
 *
 * Pendant de jardin/mutations.py, pour l'autre moitie du projet. Celui-la
 * reintroduit des regressions deja rencontrees ; celui-ci reintroduit les
 * pieges du PORTAGE — les endroits ou une traduction ligne a ligne, qui a
 * l'air juste, ne l'est pas.
 *
 * Presque tous tiennent au meme malentendu : les classes de caracteres de
 * JavaScript sont de l'ASCII quand celles de Python sont de l'Unicode. \w ne
 * connait pas les lettres accentuees, \d ne connait pas les chiffres arabes,
 * et .length compte des unites UTF-16 la ou len() compte des points de code.
 * Aucune de ces erreurs ne fait planter quoi que ce soit : elles decoupent le
 * texte un peu differemment, la famille bascule un peu plus tot, et personne
 * ne s'en apercoit avant de comparer avec la specification.
 *
 * Une mutation qui ECHAPPE est un cas manquant dans le cahier, pas une bonne
 * nouvelle.
 */

import { readFileSync, writeFileSync, existsSync, rmSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const ICI = dirname(fileURLToPath(import.meta.url));
const SRC = join(ICI, "..", "src");
const CAS = join(ICI, "cas.json");

// [fichier, motif, remplacement, ce que la regression retablit]
const MUTATIONS = [
  ["traits.js",
   "const MOT = /\\p{L}+/gu;",
   "const MOT = /\\w+/gu;",
   "\\w redevient de l'ASCII : « l'école » compte deux mots au lieu de trois"],

  ["paysage.js",
   "const _BORDS = /^[^\\p{L}\\p{N}]+|[^\\p{L}\\p{N}]+$/gu;",
   "const _BORDS = /^[\\s\\W_]+|[\\s\\W_]+$/gu;",
   "\\W redevient de l'ASCII : « œuvre » perd son o-e liant au rognage"],

  ["traits.js",
   "const NUMEROTATION = /^\\p{Nd}+[.)]\\s/u;",
   "const NUMEROTATION = /^\\d+[.)]\\s/u;",
   "\\d redevient de l'ASCII : une liste numerotee hors ASCII n'est plus une structure"],

  ["traits.js",
   "  return parseFloat(x.toFixed(n));",
   "  return Math.round(x * 10 ** n) / 10 ** n;",
   "l'arrondi passe par une multiplication, qui a sa propre erreur"],

  // Celle-ci est la premiere version ecrite ici, et elle etait fausse. Le
  // cahier ne la voyait pas : il a fallu y mettre des valeurs dyadiques pour
  // qu'un demi exact apparaisse. Elle reste pour que la panne ne repasse pas.
  ["traits.js",
   "  if (Number.isInteger(d) && d % 2 !== 0) {",
   "  if (Number.isInteger(d) && d % 2 === 2) {",
   "l'arrondi ne rattrape plus le demi exact : toFixed monte, Python va au pair"],

  ["traits.js",
   "  if (points.length < 60",
   "  if (p.length < 60",
   ".length pour len() : une ligne devient un titre selon l'encodage"],

  ["traits.js",
   "  const formes = mots.map((m) => _sans_accent(m).toLowerCase());",
   "  const formes = mots.map((m) => m.toLowerCase());",
   "MATTR ne deplie plus les accents : deux formes du meme mot comptent double"],

  ["traits.js",
   "  return FAMILLES.map((f) => [f, s[f]]).sort((a, b) => b[1] - a[1]);",
   "  return FAMILLES.map((f) => [f, s[f]]).sort((a, b) => a[1] - b[1]);",
   "le classement s'inverse : reverse=True mal porte"],

  ["paysage.js",
   '  return a.toString(16).padStart(8, "0") + (b & 0xffff).toString(16).padStart(4, "0");',
   '  return (a & 0xffff).toString(16).padStart(4, "0");',
   "l'empreinte tombe a 16 bits : des paragraphes distincts se confondent"],

  ["paysage.js",
   "    const n = en_mots(texte).length;\n    plant.mots += n;",
   '    const n = texte.split(" ").length;\n    plant.mots += n;',
   "les mots se comptent au blanc : la ponctuation devient du texte ecrit"],

  ["paysage.js",
   '    this._actif = e;\n    this._mode = "frappe";\n    plant.relire();\n    return "ecriture";',
   '    this._actif = e;\n    this._mode = "reprise";\n    plant.relire();\n    return "ecriture";',
   "decision 2 : le curseur ouvre en reprise, la premiere frappe devient une reprise"],

  // Les quatre raccourcis qu'on prend naturellement en portant un Mersenne
  // Twister. Aucun ne fait planter quoi que ce soit : le generateur rend
  // toujours des nombres d'allure honnete, simplement PAS LES MEMES — et deux
  // tirages plus loin la branche est ailleurs, sans que rien n'ait l'air faux.
  ["alea.js",
   "    this._init_par_tableau(cle);",
   "    this._init_genrand(graine);",
   "le semis passe par init_genrand : la graine ne donne plus la meme suite"],

  ["alea.js",
   "    let r = this.getrandbits(k);\n    while (r >= n) r = this.getrandbits(k);\n    return r;",
   "    return this.getrandbits(k) % n;",
   "randrange prend un modulo au lieu du rejet : il consomme un mot de moins"],

  ["alea.js",
   "    const a = this._mot() >>> 5;\n    const b = this._mot() >>> 6;",
   "    const a = this._mot() >>> 6;\n    const b = this._mot() >>> 5;",
   "random() intervertit les deux decalages : 53 bits, mais pas les memes"],

  ["alea.js",
   "    y = (y ^ ((y << 7) & 0x9d2c5680)) >>> 0;",
   "    y = (y ^ ((y << 7) & 0x9d2c5600)) >>> 0;",
   // Le bit 7, pas le bit 0 : (y << 7) a toujours ses sept bits de poids
   // faible a zero, donc une mutation du bit 0 du masque ne mord sur rien
   // et ECHAPPE sans que le cahier ait le moindre tort.
   "un bit de travers dans le masque de trempe du Mersenne Twister"],

  // Les deux suivantes existent pour prouver que les sections « tables » et
  // « relectures » gagnent leur place. Sans elles, une table pourrait deriver
  // d'un seul cote sans que rien ne bouge : sur dix-neuf abreviations, le
  // cahier de textes n'en visite que deux.
  ["traits.js",
   '  "av", "ap", "env", "p", "pp", "vol", "no", "fig", "art",',
   '  "av", "ap", "env", "p", "pp", "no", "fig", "art",',
   "une abreviation disparait d'un seul cote : « vol. » coupe une phrase en deux"],

  ["paysage.js",
   "        || d.version !== VERSION_ETAT) return new Paysage();",
   "        || false) return new Paysage();",
   "depuis() accepte n'importe quel schema : un vieil etat se relit comme neuf"],

  // ---------------------------------------------------------------- grammaire
  // La geometrie est l'endroit ou une erreur de portage se voit le moins : la
  // figure reste plausible quoi qu'il arrive. C'est justement pour ca qu'il
  // faut la comparer segment par segment.
  ["grammaire.js",
   "  ton = mod(ton, 5);",
   "  ton = ton % 5;",
   "le modulo de JavaScript redevient signe : un ton negatif sort de la palette"],

  ["grammaire.js",
   "    const v = Math.trunc(a + (b - a) * f);",
   "    const v = Math.round(a + (b - a) * f);",
   "le fondu arrondit au lieu de tronquer : int() de Python tronque"],

  ["grammaire.js",
   "    this.n_tons = 1 + Math.trunc(Math.min(1.0, Math.max(0.0, diversite)) * 4);",
   "    this.n_tons = 1 + Math.round(Math.min(1.0, Math.max(0.0, diversite)) * 4);",
   "le nombre de tons arrondit : un texte monotone tire dans deux tons"],

  // L'ORDRE DES TIRAGES. Deux lignes echangees, aucune erreur visible : la
  // figure reste un arbre, ce n'est simplement plus le meme arbre.
  ["grammaire.js",
   "  const angle0 = -Math.PI / 2 + rng.uniform(-0.16, 0.16);\n"
   + "  const lg0 = SEGMENT * (1.4 + tr.longueur * 0.7) * rng.uniform(0.85, 1.18);",
   "  const lg0 = SEGMENT * (1.4 + tr.longueur * 0.7) * rng.uniform(0.85, 1.18);\n"
   + "  const angle0 = -Math.PI / 2 + rng.uniform(-0.16, 0.16);",
   "l'inclinaison et la vigueur du tronc sont tirees dans l'autre ordre"],

  // Decision 9 : la couleur ne touche jamais la structure. Marquee dans la
  // donnee, la regle est verifiable ; sans le drapeau, elle redevient une
  // intention dans un commentaire.
  ["grammaire.js",
   "    t.trait(x, y, x2, y2, m, null, true);          // squelette",
   "    t.trait(x, y, x2, y2, m, null, false);         // squelette",
   "le squelette du vegetal n'est plus marque comme structure"],

  ["grammaire.js",
   "  const contour = gauche.concat(droite.slice().reverse());",
   "  const contour = gauche.concat(droite);",
   "le contour de la creature ne se referme plus : droite[::-1] mal porte"],

  // Celle-ci est la panne rencontree en ecrivant ce portage. Elle ne touche
  // qu'un caractere sur trente mille.
  ["grammaire.js",
   '  if (v === 0 && (x < 0 || Object.is(x, -0))) return "-" + (0).toFixed(n);',
   "  if (false) return \"\";",
   "le signe du zero se perd au formatage : Python ecrit -0.0, pas 0.0"],

  // Une frontiere de saison fermee des deux cotes ne mordrait sur RIEN, et le
  // verificateur aurait tort de le signaler : a la frontiere, melange(A,B,0.5)
  // et melange(B,A,0.5) donnent tous deux le milieu. Mesure : 0 couleur
  // changee sur 1 825. C'est une propriete du fondu, pas un trou dans le
  // cahier. On mute donc la ligne d'a cote, celle qui replace janvier dans la
  // fenetre de l'hiver — un « + 365 » qu'on oublie facilement en portant.
  ["grammaire.js",
   "  if (nom === \"hiver\" && j < 80) j += 365;   // on se replace dans la fenetre",
   "  if (false) j += 365;",
   "janvier ne se replace plus dans la fenetre de l'hiver"],

  ["grammaire.js",
   "    return _melange(couleur, PALETTES[_precedente(nom)][ton], f);",
   "    return _melange(couleur, PALETTES[_suivante(nom)][ton], f);",
   "le fondu d'entree de saison melange vers la saison suivante"],

  ["grammaire.js",
   "  return parseInt(blake2s_hex(nom, 4), 16);",
   "  return parseInt(blake2s_hex(nom, 4).slice(0, 6), 16);",
   "la graine du document perd un octet : meme document, autre figure"],

  // -------------------------------------------------------------- composition
  // Ici les mutations ne sont pas des coquilles : ce sont les erreurs que les
  // decisions interdisent nommement. Chacune produit un paysage parfaitement
  // presentable, et faux.
  ["composition.js",
   "  return Math.max(0.0, Math.min(1.0, plant.maturite || 0.0));",
   "  return Math.max(0.0, Math.min(1.0, plant.extension || 0.0));",
   "decision 2 : la profondeur passe a l'extension, les deux axes fusionnent"],

  ["composition.js",
   "  plein.extension = 1.0;",
   "  plein.extension = plant.extension || 0.0;",
   "decision 14 : le gabarit revient sur la taille courante, l'extension disparait"],

  ["composition.js",
   "      if (grand === null || enc > grand[0]) grand = [enc, t.largeur(), t.hauteur()];",
   "      if (grand === null || enc < grand[0]) grand = [enc, t.largeur(), t.hauteur()];",
   "decision 1 : le germe prend la plus PETITE famille, donc il retrecit au verrou"],

  ["composition.js",
   "  const tries = poses.slice().sort((a, b) => a[0] - b[0]);",
   "  const tries = poses.slice().sort((a, b) => b[0] - a[0]);",
   "l'ordre de dessin s'inverse : l'occlusion se fait de l'avant vers le fond"],

  ["composition.js",
   "  return rendre(poses, [cx - vw * 0.63, y - vh * 0.86, vw, vh], hauteur);",
   "  return rendre(poses, [cx - vw * 0.5, y - vh * 0.86, vw, vh], hauteur);",
   "le volet recentre le plant en cours : un plant qui nait redonne un volet vide"],

  ["composition.js",
   "    const serrage = groupe.length > 1 ? 0.46 : 1.0;",
   "    const serrage = 1.0;",
   "les plants d'une meme parcelle ne se recouvrent plus : le massif se defait"],

  ["composition.js",
   "    if (parcelle !== null && titre && titre !== parcelle) {",
   "    if (parcelle !== null && titre && titre === parcelle) {",
   "la respiration de chapitre se pose entre les mauvais plants"],

  ["composition.js",
   "    const opacite = OPACITE_FOND + (1.0 - OPACITE_FOND) * d;",
   "    const opacite = OPACITE_FOND * d;",
   "decision 1 : le fond fane au lieu de s'eloigner, un plant jamais repris s'efface"],
];

if (!existsSync(CAS)) {
  console.log("cas.json absent — lancer d'abord : python jardin/parite.py --cas");
  process.exit(2);
}

const fichiers = [...new Set(MUTATIONS.map((m) => m[0]))];

// Une mutation laissee sur le disque est pire qu'un essai en echec. Le finally
// rend le fichier d'origine quand l'essai echoue ; il ne le rend pas si le
// processus est tue. Le fichier mute reste alors en place, et la fois suivante
// toute la batterie signale des regressions qui n'existent pas, dans des
// fichiers que personne n'a touches. On ecrit donc la copie a cote avant de
// muter, et on la relit au demarrage.
for (const f of fichiers) {
  const cote = join(SRC, f + ".intact");
  if (existsSync(cote)) {
    writeFileSync(join(SRC, f), readFileSync(cote, "utf-8"), "utf-8");
    rmSync(cote);
    console.log(`  (reste d'une execution interrompue : ${f} restaure)`);
  }
}

const sauvegardes = Object.fromEntries(
  fichiers.map((f) => [f, readFileSync(join(SRC, f), "utf-8")]),
);

const barre = "=".repeat(78);
console.log(barre);
console.log("MUTATIONS DU PORTAGE — le verificateur sait-il echouer ?");
console.log(barre);

let attrapees = 0;
const manquees = [];

for (const [fichier, vieux, neuf, libelle] of MUTATIONS) {
  const chemin = join(SRC, fichier);
  const src = sauvegardes[fichier];
  if (!src.includes(vieux)) {
    manquees.push([libelle, "motif introuvable — mutation obsolete"]);
    console.log(`  ????  ${libelle}`);
    continue;
  }
  const cote = chemin + ".intact";
  writeFileSync(cote, src, "utf-8");
  writeFileSync(chemin, src.replace(vieux, neuf), "utf-8");
  let r;
  try {
    r = spawnSync(process.execPath, [join(ICI, "parite.js"), CAS], { encoding: "utf-8" });
  } finally {
    writeFileSync(chemin, src, "utf-8");
    rmSync(cote);
  }
  if (r.status !== 0) {
    attrapees += 1;
    const premier = (r.stdout || "").split("\n").find((l) => l.includes("ECART"));
    console.log(`  ok    ${libelle}`);
    if (premier) console.log(`          vue en : ${premier.trim().slice(7)}`);
  } else {
    manquees.push([libelle, "aucune comparaison ne la voit"]);
    console.log(`  ECHAPPE ${libelle}`);
  }
}

console.log(barre);
console.log(`${attrapees}/${MUTATIONS.length} pieges de portage detectes`);
for (const [libelle, raison] of manquees) console.log(`  - ${libelle}\n      ${raison}`);
console.log(barre);
process.exit(manquees.length ? 1 : 0);
