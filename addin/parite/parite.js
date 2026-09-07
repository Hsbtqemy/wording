/**
 * Verificateur de parite : rejoue le cahier fabrique par jardin/parite.py.
 *
 *     node addin/parite/parite.js addin/parite/cas.json
 *
 * Rien n'est genere ici. Le cahier contient le texte ET les reponses du
 * Python ; ce fichier ne fait que refaire les memes appels cote JavaScript et
 * signaler le premier ecart, en le situant.
 *
 * Les nombres se comparent a 1e-9 pres, pas au bit. Les deux langages font les
 * memes sommes dans le meme ordre, donc l'ecart devrait etre nul — sauf apres
 * Math.exp, dont ni Python ni JavaScript ne garantissent l'arrondi correct, et
 * apres round(), qui ne tranche pas un demi exact du meme cote. Comparer au bit
 * ferait echouer le portage sur une propriete que personne ne lui demande.
 */

import { readFileSync } from "node:fs";
import {
  extraire, revele, scores, en_mots, en_phrases, en_paragraphes,
  est_structurel, mattr, arrondi, TABLES as TABLES_TRAITS,
} from "../src/traits.js";
import {
  Paysage, empreinte, normaliser, TABLES as TABLES_PAYSAGE,
} from "../src/paysage.js";
import { Alea } from "../src/alea.js";

const TOLERANCE = 1e-9;

let echecs = 0;
let comparaisons = 0;
const DETAILS_MAX = 6;

function ecart(ou, attendu, obtenu) {
  echecs += 1;
  if (echecs <= DETAILS_MAX) {
    console.log(`  ECART  ${ou}`);
    console.log(`         python : ${JSON.stringify(attendu)}`);
    console.log(`         js     : ${JSON.stringify(obtenu)}`);
  } else if (echecs === DETAILS_MAX + 1) {
    console.log("  ... (ecarts suivants masques)");
  }
}

function memeNombre(ou, attendu, obtenu) {
  comparaisons += 1;
  if (typeof obtenu !== "number" || !Number.isFinite(obtenu)
      || Math.abs(attendu - obtenu) > TOLERANCE) {
    ecart(`${ou} (ecart ${Math.abs(attendu - obtenu).toExponential(2)})`, attendu, obtenu);
    return false;
  }
  return true;
}

function meme(ou, attendu, obtenu) {
  comparaisons += 1;
  if (typeof attendu === "number") return memeNombre(ou, attendu, obtenu);
  if (JSON.stringify(attendu) !== JSON.stringify(obtenu)) {
    ecart(ou, attendu, obtenu);
    return false;
  }
  return true;
}

/**
 * Comparaison en profondeur, nombre par nombre.
 *
 * JSON.stringify ne convient pas pour une structure qui contient des
 * flottants : Python et JavaScript ecrivent tous deux la chaine la plus courte
 * qui relit le meme nombre, mais pas de la meme facon partout — 1e-05 d'un
 * cote, 0.00001 de l'autre. On comparerait alors des ecritures, pas des
 * valeurs, et l'etat() du paysage en est plein.
 */
function memeProfond(ou, attendu, obtenu) {
  if (typeof attendu === "number") return memeNombre(ou, attendu, obtenu);
  if (Array.isArray(attendu)) {
    if (!Array.isArray(obtenu) || attendu.length !== obtenu.length) {
      comparaisons += 1;
      ecart(`${ou} (longueur)`, attendu, obtenu);
      return false;
    }
    let bon = true;
    for (let i = 0; i < attendu.length; i++) {
      bon = memeProfond(`${ou}[${i}]`, attendu[i], obtenu[i]) && bon;
    }
    return bon;
  }
  if (attendu !== null && typeof attendu === "object") {
    if (obtenu === null || typeof obtenu !== "object") {
      comparaisons += 1;
      ecart(ou, attendu, obtenu);
      return false;
    }
    const cles = new Set([...Object.keys(attendu), ...Object.keys(obtenu)]);
    let bon = true;
    for (const cle of cles) {
      if (!(cle in attendu) || !(cle in obtenu)) {
        comparaisons += 1;
        ecart(`${ou}.${cle} (champ absent d'un cote)`, attendu[cle], obtenu[cle]);
        bon = false;
        continue;
      }
      bon = memeProfond(`${ou}.${cle}`, attendu[cle], obtenu[cle]) && bon;
    }
    return bon;
  }
  return meme(ou, attendu, obtenu);
}

function titre(nom) {
  console.log(`\n${nom}`);
}

// --------------------------------------------------------------------------
const chemin = process.argv[2];
if (!chemin) {
  console.log("usage : node parite.js <cas.json>");
  process.exit(2);
}
const cahier = JSON.parse(readFileSync(chemin, "utf-8"));

// --------------------------------------------------------------------------
// 0. Le generateur
// --------------------------------------------------------------------------
// Il passe en premier parce que tout ce qui se dessine en depend. random,
// uniform et randrange doivent tomber au BIT pres — ce sont des fonctions
// deterministes de deux entiers de 32 bits, il n'y a rien a arrondir.
// expovariate seul passe par un logarithme, dont ni Python ni JavaScript ne
// garantissent le dernier bit.
titre("generateur de nombres");
{
  let ecartMax = 0;
  let tirages = 0;
  for (const c of cahier.alea.cas) {
    const r = new Alea(c.graine);
    for (const [nom, args, attendu] of c.suite) {
      let obtenu;
      if (nom === "random") obtenu = r.random();
      else if (nom === "uniform") obtenu = r.uniform(args[0], args[1]);
      else if (nom === "randrange") obtenu = r.randrange(args[0]);
      else obtenu = r.expovariate(args[0]);
      tirages += 1;
      ecartMax = Math.max(ecartMax, Math.abs(obtenu - attendu));
      if (nom === "expovariate") {
        meme(`alea(${c.graine}).${nom}`, attendu, obtenu);
      } else if (obtenu !== attendu) {
        comparaisons += 1;
        ecart(`alea(${c.graine}).${nom} (pas identique au bit)`, attendu, obtenu);
      } else {
        comparaisons += 1;
      }
    }
  }
  // Le tri par cle aleatoire de grammaire.py : un tri stable des deux cotes ne
  // suffit pas, il faut aussi les memes cles.
  for (const t of cahier.alea.tris) {
    const r = new Alea(t.graine);
    const cles = Array.from({ length: t.n }, () => r.random());
    const ordre = Array.from({ length: t.n }, (_, k) => k).sort((a, b) => cles[a] - cles[b]);
    meme(`tri par cle aleatoire, graine ${t.graine}`, t.ordre, ordre);
  }
  console.log(`  ${cahier.alea.cas.length} graines, ${tirages} tirages,`
    + ` ecart maximal ${ecartMax.toExponential(2)} (logarithme)`);
}

// --------------------------------------------------------------------------
// 1. Les tables litterales
// --------------------------------------------------------------------------
// Comparees pour elles-memes : sur les dix-neuf abreviations, le cahier de
// textes n'en visite que deux. Les dix-sept autres pourraient etre fausses
// depuis toujours sans que rien ne le signale.
titre("tables litterales");
memeProfond("traits", cahier.tables.traits, TABLES_TRAITS);
memeProfond("paysage", cahier.tables.paysage, TABLES_PAYSAGE);
console.log(`  ${Object.keys(cahier.tables.traits).length}`
  + ` + ${Object.keys(cahier.tables.paysage).length} tables`);

// --------------------------------------------------------------------------
// 2. Ce qu'une relecture ratee doit rendre
// --------------------------------------------------------------------------
// Un paysage illisible doit repartir vide, jamais lever : l'add-in n'aurait
// nulle part ou rattraper l'erreur, et le volet resterait noir.
titre("relectures refusees");
for (const c of cahier.relectures) {
  let r;
  try {
    r = Paysage.depuis(c.brut);
  } catch (e) {
    ecart(`depuis(${JSON.stringify(c.brut)}) a leve`, "un paysage vide", String(e));
    continue;
  }
  meme(`depuis(${JSON.stringify(c.brut)}).identifiant`, c.identifiant, r.identifiant);
  meme(`depuis(${JSON.stringify(c.brut)}).plants`, c.plants, r.segments.length);
  meme(`depuis(${JSON.stringify(c.brut)}).empreintes`, c.empreintes, r.registre.size);
  meme(`depuis(${JSON.stringify(c.brut)}).version`, c.version, r.version);
}
console.log(`  ${cahier.relectures.length} entrees illisibles`);

// --------------------------------------------------------------------------
// 3. L'arrondi
// --------------------------------------------------------------------------
// Teste pour lui-meme, parce qu'on ne peut pas compter sur le hasard pour le
// mettre en defaut : les valeurs qui separent les deux methodes d'arrondi sont
// trop petites pour apparaitre dans un score, et apparaissent seulement dans
// une marge entre deux scores — le cas du refus de classement.
titre("arrondi");
for (const [x, a4, a3] of cahier.arrondis) {
  meme(`arrondi(${x}, 4)`, a4, arrondi(x, 4));
  meme(`arrondi(${x}, 3)`, a3, arrondi(x, 3));
}
console.log(`  ${cahier.arrondis.length} valeurs`);

// --------------------------------------------------------------------------
// 4. Normalisation et decoupage
// --------------------------------------------------------------------------
// C'est ici que se voient les ecarts d'Unicode. Tout le reste en depend : si
// "l'ecole" et "l’école" ne se normalisent pas pareil des deux cotes, le
// registre d'empreintes ne reconnait plus rien et la forme pousse toute seule.
titre("decoupage et normalisation");
let debut = Date.now();
for (const c of cahier.tokenisation) {
  const apercu = JSON.stringify(c.texte.slice(0, 34));
  meme(`normalise ${apercu}`, c.normalise, normaliser(c.texte));
  meme(`mots ${apercu}`, c.mots, en_mots(c.texte).length);
  meme(`phrases ${apercu}`, c.phrases, en_phrases(c.texte).length);
  meme(`paragraphes ${apercu}`, c.paragraphes, en_paragraphes(c.texte).length);
  meme(`structurel ${apercu}`, c.structurel, est_structurel(c.texte));
  // MATTR a part, pas seulement a travers diversite : borne(mattr, 0.55, 0.80)
  // ecrete, et sur un texte court les deux valeurs comparees seraient deux
  // zeros identiques quoi qu'il arrive en amont.
  meme(`mattr ${apercu}`, c.mattr, mattr(en_mots(c.texte)));
}
console.log(`  ${cahier.tokenisation.length} textes, ${Date.now() - debut} ms`);

// --------------------------------------------------------------------------
// 5. Traits, scores, revelation
// --------------------------------------------------------------------------
titre("traits et revelation");
debut = Date.now();
for (const c of cahier.traits) {
  const t = extraire(c.texte);
  for (const [nom, valeur] of Object.entries(c.comptes)) meme(`${c.nom}.${nom}`, valeur, t[nom]);
  for (const [nom, valeur] of Object.entries(c.traits)) meme(`${c.nom}.${nom}`, valeur, t[nom]);
  meme(`${c.nom}.mattr`, c.mattr, mattr(en_mots(c.texte)));
  const s = scores(t);
  for (const [f, valeur] of Object.entries(c.scores)) meme(`${c.nom}.score.${f}`, valeur, s[f]);
  const r = revele(t);
  for (const [nom, valeur] of Object.entries(c.revelation)) meme(`${c.nom}.${nom}`, valeur, r[nom]);
}
console.log(`  ${cahier.traits.length} vecteurs, ${Date.now() - debut} ms`);

// --------------------------------------------------------------------------
// 6. Le journal, appel par appel
// --------------------------------------------------------------------------
// Le verdict de chaque appel est compare sur place : un ecart est situe au
// paragraphe pres, et pas seulement constate a la fin sur un total qui ne dit
// pas ou il s'est forme.
titre("journal de redaction");
debut = Date.now();
const p = new Paysage({ identifiant: "parite", cle_dossier: "parite" });
let n = 0;
const empreintesCorpus = new Set();
for (const appel of cahier.journal) {
  n += 1;
  const geste = appel[0];
  if (geste === "quitter") {
    p.quitter();
    continue;
  }
  if (geste === "absorber") {
    const [, texte, style, mpi, jour, heure, attendu] = appel;
    empreintesCorpus.add(empreinte(texte));
    const obtenu = p.absorber(texte, style, mpi, jour, heure);
    if (!meme(`appel ${n} absorber ${JSON.stringify(texte.slice(0, 30))}`, attendu, obtenu)) {
      if (echecs > DETAILS_MAX) break;
    }
    continue;
  }
  const [, ancien, nouveau, jour, heure, greffe, attendu] = appel;
  const obtenu = p.retoucher(ancien, nouveau, jour, heure, greffe);
  meme(`appel ${n} retoucher ${JSON.stringify(ancien.slice(0, 30))}`, attendu, obtenu);
}
console.log(`  ${cahier.journal.length} appels, ${Date.now() - debut} ms`);

// --------------------------------------------------------------------------
// 7. L'etat final
// --------------------------------------------------------------------------
titre("etat des plants");
meme("nombre de plants", cahier.plants.length, p.segments.length);
const paires = Math.min(cahier.plants.length, p.segments.length);
for (let i = 0; i < paires; i++) {
  const a = cahier.plants[i];
  const s = p.segments[i];
  for (const nom of ["rang", "titre", "mots", "nouveaux", "reprises", "greffes",
                     "famille", "candidate", "confirmations",
                     "mots_derniere_lecture", "mots_de_nuit"]) {
    meme(`plant ${i}.${nom}`, a[nom], s[nom]);
  }
  meme(`plant ${i}.extension`, a.extension, s.extension);
  meme(`plant ${i}.maturite`, a.maturite, s.maturite);
  meme(`plant ${i}.nuit`, a.nuit, s.nuit);
  meme(`plant ${i}.stade`, a.stade, s.stade());
  meme(`plant ${i}.dates`, a.dates, s.dates());
  for (const [nom, valeur] of Object.entries(a.traits)) {
    meme(`plant ${i}.trait.${nom}`, valeur, s.traits_courants[nom]);
  }
  for (const [nom, valeur] of Object.entries(a.scores)) {
    meme(`plant ${i}.score.${nom}`, valeur, s.scores_courants[nom]);
  }
  meme(`plant ${i}.influences`, a.influences, s.influences());
}

// --------------------------------------------------------------------------
// 8. Les empreintes
// --------------------------------------------------------------------------
// Les deux fonctions de hachage sont differentes — blake2s d'un cote, murmur3
// de l'autre, faute de hachage synchrone dans un navigateur. On ne peut donc
// pas comparer les cles. Ce qu'on peut comparer, c'est ce que le reste du
// systeme observe d'elles : le nombre de choses distinctes qu'elles voient.
// Un ecart ici serait une collision, et une collision serait un paragraphe
// neuf pris pour un paragraphe deja ecrit.
titre("empreintes");
meme("empreintes distinctes du corpus", cahier.empreintes_corpus, empreintesCorpus.size);
meme("taille du registre", cahier.empreintes, p.registre.size);
console.log(`  ${cahier.textes_corpus} paragraphes haches,`
  + ` ${empreintesCorpus.size} distincts des deux cotes`);

// --------------------------------------------------------------------------
// 9. Ce que le volet lira, et ce qu'il rangera
// --------------------------------------------------------------------------
// etat() et serialiser() sont la seule interface du module vers le reste de
// l'add-in, et le journal ne les traverse jamais : il ne compare que des
// verdicts et des champs de Segment. Une panne de schema y serait invisible
// jusqu'au jour ou un paysage se relit vide.
titre("etat et persistance");
memeProfond("etat", cahier.etat, p.etat());

// Le JavaScript doit relire ce que le Python a ecrit : c'est la meme forme de
// donnees, meme si les cles du registre different (les deux hachages ne sont
// pas les memes, seul leur NOMBRE est comparable).
memeProfond("etat apres relecture du Python", cahier.etat,
            Paysage.depuis(cahier.serialise).etat());

// Et il doit se relire lui-meme sans rien perdre.
memeProfond("aller-retour JavaScript", p.etat(),
            Paysage.depuis(p.serialiser()).etat());
meme("registre apres aller-retour", p.registre.size,
     Paysage.depuis(p.serialiser()).registre.size);

// --------------------------------------------------------------------------
// 10. Le rattachement
// --------------------------------------------------------------------------
// Decision 11 : le premier geste du vrai add-in, celui que le journal ne fait
// jamais puisqu'il commence sur un document vide.
titre("rattachement d'un document existant");
const r = cahier.rattachement;
const q = new Paysage({ identifiant: "rattache", cle_dossier: "rattache" });
q.rattacher(r.entree, r.jour, r.heure);
memeProfond("rattachement", r.etat, q.etat());
console.log(`  ${r.entree.length} paragraphes, ${q.segments.length} plants`);

// --------------------------------------------------------------------------
console.log("\n" + "=".repeat(78));
if (echecs === 0) {
  console.log(`parite : ${comparaisons} comparaisons, aucun ecart`);
} else {
  console.log(`parite : ${comparaisons} comparaisons, ${echecs} ecarts`);
}
console.log("=".repeat(78));
process.exit(echecs === 0 ? 0 : 1);
