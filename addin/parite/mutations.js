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
