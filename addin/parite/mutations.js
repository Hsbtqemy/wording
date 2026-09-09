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

// [fichier, motif, remplacement, ce que la regression retablit, verificateur]
//
// Le verificateur vaut "parite" par defaut. Ce qui n'a pas de Python en face se
// verifie autrement :
//
//   "essais"  le pont, contre un Word simule (addin/essais.js)
//   "volet"   le cablage Office.js ET les deux magasins de la decision 16,
//             contre un hote simule (essais_volet.js)
//
// Ce sont justement les parties qu'aucune parite ne couvre, donc celles ou une
// mutation qui echappe couterait le plus cher.
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

  // ⚠️ LE MOTIF A SUIVI LA VERSION 3. Il visait « d.version !== VERSION_ETAT »,
  // qui n'existe plus : depuis() accepte maintenant une PLAGE de versions,
  // parce qu'un etat de version 2 se convertit au lieu d'etre jete. Le
  // controle prealable des motifs a signale la peremption avant de muter quoi
  // que ce soit — c'est exactement ce pour quoi il existe.
  ["paysage.js",
   "        || d.version < 2 || d.version > VERSION_ETAT) return new Paysage();",
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
   "    this.n_tons = 1 + Math.trunc(Math.min(1.0, Math.max(0.0, richesse)) * 4);",
   "    this.n_tons = 1 + Math.round(Math.min(1.0, Math.max(0.0, richesse)) * 4);",
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
   "    const serrage = _serrage(groupe.length);",
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

  // ---------------------------------------------------------------------- pont
  // Verifiees contre le Word simule, pas contre le Python. Les deux premieres
  // sont les defauts que cette batterie a reellement trouves, et qui auraient
  // ete livres.
  ["pont.js",
   "        if (v === \"vide\") {",
   "        if (false) {",
   "le paragraphe vide entre au registre : le plant cesse de pousser au deuxieme",
   "essais"],

  ["pont.js",
   "        const ne = this.naissances.has(p.id);",
   "        const ne = false;",
   "un paragraphe qui commence comme un autre est declare connu et disparait",
   "essais"],

  // Celle-ci est la raison d'etre du pont. Word n'a pas d'evenement de
  // selection : il faut DocumentSelectionChanged, qui se declenche aussi a
  // chaque frappe puisque taper deplace le point d'insertion.
  ["pont.js",
   "    if (id === this.curseur) return false;",
   "    if (false) return false;",
   "decision 2 : le curseur quitte a chaque frappe, toute redaction devient reprise",
   "essais"],

  ["pont.js",
   "    if (distant) return 0;          // la frappe d'un co-auteur n'est pas la notre",
   "    if (false) return 0;",
   "la frappe d'un co-auteur fait pousser notre paysage",
   "essais"],

  ["pont.js",
   "    const debit = mots * INTERVALLE / Math.max(ecoule, INTERVALLE);",
   "    const debit = mots;",
   "le debit n'est plus ramene a l'intervalle : un vidage en retard fait une greffe",
   "essais"],

  // Et les deux corrections apportees a la specification, vues par la parite.
  ["paysage.js",
   "    if (!en_mots(texte).length) return \"vide\";",
   "    if (false) return \"vide\";",
   "absorber accepte de nouveau le vide, comme avant le portage"],

  ["paysage.js",
   "    if (this.registre.has(e) && !naissance) return \"connue\";",
   "    if (this.registre.has(e)) return \"connue\";",
   "la naissance ne dispense plus de la reconnaissance du registre"],

  ["pont.js",
   "    const debit = mots * INTERVALLE / Math.max(ecoule, INTERVALLE);",
   "    const debit = mots * INTERVALLE / Math.max(ecoule, 1);",
   "le debit s'amplifie quand un vidage arrive tot : quatre mots font un collage",
   "essais"],

  // --------------------------------------------------------------------- volet
  ["volet.js",
   "  if (!Office.context.requirements.isSetSupported(\"WordApi\", \"1.1\")) {",
   "  if (false) {",
   "un Word trop ancien laisse le volet noir au lieu de dire ce qui manque",
   "volet"],

  ["volet.js",
   "    paysage.rattacher(guet.amorcer(texte, styles), jour, heure);\n    ranger();",
   "    paysage.rattacher(guet.amorcer(texte, styles), jour, heure);",
   "le capital de depart n'est pas range : rouvrir le fichier le perd",
   "volet"],

  // La lecture des styles est la seule qui coute cher — un objet Office.js par
  // paragraphe, deux secondes et demie sur une these. La lancer a chaque tic
  // tiendrait dans aucun budget, et rien ne le signalerait : le paysage
  // pousserait juste, en faisant ramer Word.
  ["volet.js",
   "  if (styles_perimes || compter_paragraphes(texte) !== guet.paragraphes) {",
   "  if (compter_paragraphes(texte) !== guet.paragraphes) {",
   "une lecture de styles ratee n'est jamais rejouee : la table reste DECALEE"
   + " d'un paragraphe jusqu'au prochain changement de structure",
   "volet"],

  ["volet.js",
   "  if (styles_perimes || compter_paragraphes(texte) !== guet.paragraphes) {",
   "  if (true) {",
   "les styles se relisent a chaque tic : deux secondes et demie de lecture"
   + " toutes les deux secondes",
   "volet"],

  ["volet.js",
   "  const coupe = url.lastIndexOf(\"/\");\n  return coupe > 0 ? url.slice(0, coupe) : url;",
   "  return url;",
   "la cle du dossier devient le chemin du FICHIER : plus aucun partage",
   "volet"],

  // ------------------------------------------------------------------ magasin
  // La copie du paysage dans le .docx (decision 16). Aucune de ces regressions
  // ne fait planter quoi que ce soit : elles laissent le volet dessiner
  // exactement comme avant, et ne se voient que le jour ou le localStorage a
  // disparu — c'est-a-dire le jour ou il est trop tard.
  ["magasin.js",
   "    const id = connu || index[dossier] || tirer_identifiant();",
   "    const id = connu || tirer_identifiant();",
   "decision 11 : chaque document ouvre son paysage, le dossier ne compte plus",
   "volet"],

  ["magasin.js",
   "  if (n_fichier > n_dossier) {",
   "  if (n_dossier > n_fichier) {",
   "l'arbitrage part a l'envers : la copie la plus pauvre ecrase l'autre",
   "volet"],

  ["magasin.js",
   "    if (n <= this.copiees) return false;",
   "    if (n < this.copiees) return false;",
   "le document est reecrit pour reposer exactement la meme chose",
   "volet"],

  ["magasin.js",
   "    if (this.derniere !== null && t - this.derniere < ATTENTE_COPIE) return false;",
   "    if (this.derniere !== null && t - this.derniere < 0) return false;",
   "plus d'etranglement : le .docx est marque modifie a chaque tic",
   "volet"],

  ["magasin.js",
   "    if (this.refuse) return false;",
   "    if (false) return false;",
   "on redemande a un document qui a deja dit non, toutes les cinq minutes",
   "volet"],

  ["volet.js",
   "      await magasin.copier(paysage);\n",
   "",
   "plus de copie de secours : le paysage remeurt avec le localStorage",
   "volet"],

  // C'etait le code d'avant la decision 16, et il salissait les documents :
  // ouvrir un fichier suffisait a le faire ressortir « modifie ».
  ["volet.js",
   "  if (id !== connu) Office.context.document.settings.set(REGLAGE_ID, id);",
   "  if (id !== connu) {\n"
   + "    Office.context.document.settings.set(REGLAGE_ID, id);\n"
   + "    Office.context.document.settings.saveAsync();\n  }",
   "le reglage est enregistre des l'ouverture : Word demande d'enregistrer un"
   + " document ou personne n'a tape",
   "volet"],

  // ------------------------------------------------------------------- guet
  // Le guet est le premier morceau du cablage Word couvert par la PARITE : le
  // rapprochement de deux instantanes a un Python en face. Ces mutations se
  // verifient donc contre le cahier, pas contre un hote simule.
  ["guet.js",
   'export const SEPARATEURS_LIGNE = ["\\u000B", "\\n"];',
   'export const SEPARATEURS_LIGNE = ["\\n"];',
   "point 14 : le saut de ligne cesse de separer, 35 pages font une seule ligne"],

  ["guet.js",
   "    while (libres && libres.length) {",
   "    while (false) {",
   "les lignes egales ne se reconnaissent plus : un deplacement devient deux"
   + " retouches, donc de la maturite inventee"],

  ["guet.js",
   "      const i = libres.shift();",
   "      const i = libres.pop();",
   "pop() pour pop(0) : parmi des lignes identiques, c'est la derniere qui est"
   + " appariee, et les identifiants divergent de la specification"],

  ["guet.js",
   "  return texte.split(SEPARATEUR_PARAGRAPHE).length;",
   "  return texte.split(SEPARATEURS_LIGNE[0]).length;",
   "la peremption des styles se compte en LIGNES : la table ne se rafraichit"
   + " plus quand un paragraphe apparait"],

  ["guet.js",
   "  const rang = appartenance[k];\n"
   + "  return rang < styles.length ? styles[rang] : \"Normal\";",
   "  return \"Normal\";",
   "plus aucun style ne remonte : une citation compte comme de l'ecriture"
   + " (point 3) et un Titre 1 n'ouvre plus de plant (point 6)"],

  ["guet.js",
   "      lignes.push(m);\n      appartenance.push(rang);",
   "      lignes.push(m);\n      appartenance.push(lignes.length - 1);",
   "le style est indexe par LIGNE et non par paragraphe : deux lignes d'un meme"
   + " paragraphe recoivent deux styles differents"],

  ["guet.js",
   "  const disparues = restants_a.slice(restants_b.length);",
   "  const disparues = [];",
   "une ligne supprimee ne disparait plus : le miroir garde un fantome"],

  ["guet.js",
   "        ids[j] = this.ids[i];\n        faits.push({ type: \"retouchee\"",
   "        ids[j] = this._neuf();\n        faits.push({ type: \"retouchee\"",
   "une ligne retouchee change d'identifiant : chaque frappe devient une ligne"
   + " neuve"],

  ["guet.js",
   "      if (this.calme >= this.silence) {",
   "      if (this.calme >= 1) {",
   "la visite se ferme au premier releve calme : une pause pour reflechir"
   + " devient une reprise, et l'extension s'effondre"],


  // ------------------------------------------------- guet : nourrir le paysage
  // C'est ici que le guet remplace le pont, donc ici que les decisions du pont
  // doivent survivre. Le cahier compare la chaine entiere — texte, faits,
  // verdicts, etat final — donc ces regressions se voient sur le verdict ET
  // sur la forme qui pousse.
  ["guet.js",
   "      } else if (!compter_mots(f.ancien)) {",
   "      } else if (false) {",
   "une ligne nee vide qui se remplit redevient une REPRISE : le premier mot de"
   + " chaque ligne neuve cesse de compter, et l'extension n'existe plus"],

  ["guet.js",
   "        v = paysage.absorber(f.texte, f.style, debit, jour, heure, true);",
   "        v = paysage.absorber(f.texte, f.style, debit, jour, heure, false);",
   "le drapeau de naissance se perd : une ligne qui commence comme une autre est"
   + " declaree connue et le plant cesse de pousser"],

  ["guet.js",
   "                              this.greffes.has(f.id), debit);",
   "                              false, debit);",
   "decision 4 : un chapitre colle puis retravaille reste une greffe pour"
   + " toujours — le defaut que le pont avait, remis en place"],

  ["guet.js",
   '      if (v === "greffe") this.greffes.add(f.id);',
   '      if (v === "ecriture") this.greffes.add(f.id);',
   "les greffes ne sont plus retenues : la conversion se declenche sur le mauvais"
   + " verdict"],

  ["guet.js",
   "    const borne = Math.min(Math.max(ecoule, INTERVALLE), PLAFOND_ECOULE);",
   "    const borne = Math.min(Math.max(ecoule, 1), PLAFOND_ECOULE);",
   "le debit s'amplifie quand un releve arrive tot : quatre mots tapes deviennent"
   + " un collage"],

  ["guet.js",
   '      if (genre === "visite_finie") {\n        paysage.quitter();',
   '      if (genre === "visite_finie") {\n        paysage.etat();',
   "la visite ne se ferme plus : plant.reprises ne monte jamais et l'element"
   + " cesse de murir"],

  ["guet.js",
   "        mots += Math.max(0, compter_mots(f.texte) - compter_mots(f.ancien));",
   "        mots += compter_mots(f.texte) - compter_mots(f.ancien);",
   "raccourcir une ligne rend un debit NEGATIF, qui compense un collage arrive"
   + " dans le meme releve"],


  // ------------------------------------------- la porte derobee du collage
  // Le trou par lequel un vrai document est passe d'une tige a un arbre entier
  // en trois collages, dans le premier Word ou l'add-in ait jamais tourne.
  ["paysage.js",
   "      if (mots_par_intervalle > SEUIL_COLLAGE) {",
   "      if (false) {",
   "decision 4 : coller dans la ligne qu'on ecrit compte tous les mots colles"
   + " en extension, sans le moindre controle"],

  ["guet.js",
   "    const borne = Math.min(Math.max(ecoule, INTERVALLE), PLAFOND_ECOULE);",
   "    const borne = Math.max(ecoule, INTERVALLE);",
   "le temps ecoule n'est plus plafonne : un collage vu une minute trop tard"
   + " passe pour de l'ecriture"],


  // ------------------------------------------------- le point 12, applique
  // Deux prescriptions du point 12 que le portage n'avait jamais suivies. Ni
  // l'une ni l'autre ne casse quoi que ce soit : elles font ramer Word, ce que
  // personne ne rapporte comme un bug — et un tic lent dilue le debit, donc
  // affaiblit la garde contre le collage.
  ["volet.js",
   "    if (aEcrire && maintenant - dernier_rangement >= AMORTI) {",
   "    if (aEcrire) {",
   "l'etat complet est serialise a CHAQUE tic, en synchrone, sur le fil qui gere"
   + " la frappe",
   "volet"],

  ["volet.js",
   "  if (svg === dernier_svg) return;",
   "  if (false) return;",
   "le SVG entier est repose a chaque tic, meme identique : un reparse complet"
   + " du document toutes les deux secondes",
   "volet"],


  // ------------------------------------------- la pousse du vegetal (point 1)
  // La profondeur fractionnaire et la repartition du feuillage. Aucune des
  // trois ne casse le dessin : elles le rendent plus grossier, ou le font
  // reculer — et seule une comparaison au point pres les voit.
  ["grammaire.js",
   "  const part = BUDGET_FEUILLAGE / pointes;",
   "  const part = Math.floor(BUDGET_FEUILLAGE / pointes);",
   "decision 1 : le feuillage se divise au lieu de se repartir"],

  ["grammaire.js",
   "  const prof_max = 4.0 + extension * 3.0;",
   "  const prof_max = 4.0 + Math.trunc(extension * 3.0);",
   "la profondeur redevient entiere : quatre formes sur la vie d'un plant"],

  ["grammaire.js",
   "  for (let i = 0; i < niveau; i++) inverse = (inverse << 1) | ((index >> i) & 1);",
   "  inverse = index;",
   "les rameaux sortent de gauche a droite au lieu d'etre disperses"],


  ["composition.js",
   "export const RECUL_CAMERA = 0.5;",
   "export const RECUL_CAMERA = 1.0;",
   "le cadre du volet revient a la taille finale : un germe redevient un cheveu"],

  ["composition.js",
   "  gl = Math.max(t.largeur(), 1.0) ** (1 - RECUL_CAMERA) * gl ** RECUL_CAMERA;",
   "  gl = gl ** RECUL_CAMERA;",
   "le cadre n'interpole plus qu'en hauteur : une creature deployee se fait"
   + " rogner sur les cotes"],


  // ------------------------------------ la poignee de main du dialogue (14)
  // La course qui a rendu « tout voir » blanc. Elle ne casse rien de visible
  // dans le code : elle deplace une ligne.
  ["apercu.js",
   "    () => {\n      // L'ecouteur est pose : on peut parler.\n"
   + "      bureau.context.ui.messageParent(\"pret\");",
   "    () => {\n      // L'ecouteur est pose : on peut parler.\n"
   + "      void 0;",
   "le dialogue ne se dit jamais pret : le volet ne repond pas et la fenetre"
   + " reste blanche",
   "volet"],

  ["apercu.js",
   "    mot.textContent = `Le paysage n'a pas pu etre relu (${e.name}).`;",
   "    mot.textContent = \"\";",
   "une lecture impossible laisse une fenetre blanche au lieu de se dire",
   "volet"],


  // ------------------------- l'attribution de la reprise (decisions 2 et 3)
  ["paysage.js",
   "    const plant = this._segment_de(vieille) || this._plant(jour, heure);",
   "    const plant = this._plant(jour, heure);",
   "decision 2 : la reprise repart sur le plant courant"],

  ["paysage.js",
   "    this.registre.set(e, plant.rang);\n    this._touche = plant.rang;\n"
   + "\n    // 3. Inconnue et arrivee d'un bloc : greffe, en attente.",
   "    this.registre.set(e, RANG_INCONNU);\n    this._touche = plant.rang;\n"
   + "\n    // 3. Inconnue et arrivee d'un bloc : greffe, en attente.",
   "le registre n'enregistre plus le proprietaire"],

  ["paysage.js",
   "        || d.version < 2 || d.version > VERSION_ETAT) return new Paysage();",
   "        || d.version !== VERSION_ETAT) return new Paysage();",
   "un paysage de version 2 est jete au lieu d'etre converti"],

  ["paysage.js",
   "      touche: this._touche,",
   "      touche: RANG_INCONNU,",
   "le plant travaille est oublie a la fermeture : la camera saute a la fin"],

  ["composition.js",
   "  let i = poses_de.findIndex((q) => q.actif);\n  if (i === -1) i = poses_de.length - 1;",
   "  let i = poses_de.length - 1;",
   "le volet recadre toujours le dernier plant"],


  // ------------------------------- le plafond, l'axe, le feuillage, le port
  // Les deux lectures de MATTR, cote portage. Le cahier porte `diversite` ET
  // `richesse` avec des valeurs DIFFERENTES sur les vecteurs dessines (0,63
  // contre 0,84, 0,31 contre 0,12) : c'est ce qui rend visible un portage qui
  // lit l'un pour l'autre. Sans cet ecart, ces trois mutations passeraient.
  ["traits.js",
   "    diversite: borne(mattr_du_texte, 0.55, 0.80),",
   "    diversite: borne(mattr_du_texte, 0.42, 0.70),",
   "le portage classe avec la borne du DESSIN : le paysage JavaScript range"
   + " en abstrait des chapitres que Python garde en arbres"],

  ["traits.js",
   "    richesse: borne(mattr_du_texte, 0.42, 0.70),",
   "    richesse: borne(mattr_du_texte, 0.55, 0.80),",
   "le portage garde l'ancienne borne : le paysage JavaScript perd trois tons"
   + " de palette sur cinq"],

  ["grammaire.js",
   '    "richesse" in traits ? traits.richesse : 0.5);',
   '    "diversite" in traits ? traits.diversite : 0.5);',
   "le portage peint le plant avec le trait de CLASSEMENT au lieu de celui du"
   + " dessin"],

  ["traits.js",
   "    longueur: borne(longueur_moy, 8, 45),",
   "    longueur: borne(longueur_moy, 8, 30),",
   "le plafond de longueur revient a 30 : toute these sature"],

  ["grammaire.js",
   "  const axe = tr.structure;",
   "  const axe = 0.0;",
   "l'arbre reoublie la structure"],

  ["grammaire.js",
   "  const eventail = 0.22 + tr.richesse * 0.36;",
   "  const eventail = 0.40;",
   "le feuillage s'ouvre pareil pour tous"],

  ["grammaire.js",
   "  const port = rng.uniform(-1.0, 1.0);",
   "  const port = 0.0;",
   "tous les plants prennent le meme port"],

  ["grammaire.js",
   "  ouverture *= 1.0 - port * 0.7;",
   "  ouverture *= 1.0 - port * 0.38;",
   "le port se retracte : le portage a garde l'ancienne valeur"],

  ["grammaire.js",
   "      const tenue = s === meneur ? 1.0 - axe * 0.72 : 1.0 + axe * 0.4;",
   "      const tenue = 1.0;",
   "le rameau meneur ne prolonge plus l'axe"],


  // ----------------------------------------------- le serrage du massif
  ["composition.js",
   "  const lache = 1.0 - PLANTS_CACHES / (n - 1);",
   "  const lache = 1.0 - PLANTS_CACHES / n;",
   "le portage decale d'un le nombre d'intervalles : un massif de trois"
   + " se pose a 0,64 au lieu de 0,46"],

  // ⚠️ Le plafond avait ete ecrit d'abord, puis retire cote Python. Un
  //    portage fait sur la premiere version le garderait, et RIEN ne se
  //    verrait avant quinze plants par massif : c'est la seule mutation que
  //    la vue « un chapitre entier » du cahier soit seule a attraper, et
  //    c'est elle qui justifie que cette vue existe.
  ["composition.js",
   "  return Math.max(SERRAGE_SERRE, lache);",
   "  return Math.max(SERRAGE_SERRE, Math.min(0.92, lache));",
   "le plafond retire cote Python survit dans le portage : invisible"
   + " jusqu'a quatorze plants par massif"],

  ["composition.js",
   "  return Math.max(SERRAGE_SERRE, lache);",
   "  return lache;",
   "le plancher saute : a deux plants le serrage devient negatif"],

  // ⚠️ Piege de portage pur : Python leverait ZeroDivisionError, JavaScript
  //    rend -Infinity sans un mot, et le plant part a l'infini a gauche.
  ["composition.js",
   "  if (n < 2) return 1.0;",
   "  if (n < 1) return 1.0;",
   "un massif d'un seul plant tombe dans la formule : division par zero,"
   + " que JavaScript ne signale pas"],

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

// ⚠️ DEUX VERSIONS DE CHAQUE FICHIER. Git normalise les fins de ligne en CRLF
// a chaque checkout sur Windows, et les motifs multi-lignes portent des sauts
// simples : ils cessent alors de mordre, et le controle prealable declare tout
// le fichier perime alors qu'aucun motif n'a vieilli. Un clone frais du depot
// refuserait de lancer les mutations.
//
// On compare et on mute sur la copie en LF, et on restaure les OCTETS
// D'ORIGINE : le fichier ressort exactement comme il etait entre.
const octets = Object.fromEntries(
  fichiers.map((f) => [f, readFileSync(join(SRC, f), "utf-8")]),
);
const sauvegardes = Object.fromEntries(
  Object.entries(octets).map(([f, t]) => [f, t.replace(/\r\n/g, "\n")]),
);

// Les motifs d'abord, avant de toucher un seul fichier.
//
// Un motif perime se signalait « obsolete » en cours de route, apres avoir
// laisse tourner la verification complete pour toutes les mutations d'avant —
// des minutes pour apprendre qu'une ligne avait bouge. Pire, « obsolete » a
// l'air d'un probleme de maintenance et non d'une mutation qui ne teste rien.
// C'est arrive trois fois dans la meme journee, dans les deux langages : le
// motif contenait un echappement que le langage interpretait a l'execution,
// donc il cherchait un vrai caractere de controle la ou la source porte ses
// quatre caracteres. Le controle est instantane, il vient en premier.
const perimes = MUTATIONS.filter(([f, vieux]) => !sauvegardes[f].includes(vieux));
if (perimes.length) {
  console.log("=".repeat(78));
  console.log("MOTIFS PERIMES — rien n'a ete mute");
  console.log("=".repeat(78));
  for (const [fichier, , , libelle] of perimes) {
    console.log(`  ${fichier} : ${libelle}`);
  }
  console.log(`\n${perimes.length} motif(s) ne mordent plus sur la source.`);
  process.exit(2);
}

const barre = "=".repeat(78);
console.log(barre);
console.log("MUTATIONS DU PORTAGE — le verificateur sait-il echouer ?");
console.log(barre);

let attrapees = 0;
const manquees = [];

for (const [fichier, vieux, neuf, libelle, verificateur] of MUTATIONS) {
  const chemin = join(SRC, fichier);
  const src = sauvegardes[fichier];
  // Plus besoin de tester le motif ici : le controle prealable a deja rendu
  // la main si l'un d'eux ne mordait plus.
  const cote = chemin + ".intact";
  writeFileSync(cote, octets[fichier], "utf-8");
  writeFileSync(chemin, src.replace(vieux, neuf), "utf-8");
  let r;
  try {
    const args = verificateur === "essais" ? [join(ICI, "..", "essais.js")]
      : verificateur === "volet" ? [join(ICI, "..", "essais_volet.js")]
      : [join(ICI, "parite.js"), CAS];
    r = spawnSync(process.execPath, args, { encoding: "utf-8" });
  } finally {
    writeFileSync(chemin, octets[fichier], "utf-8");
    rmSync(cote);
  }
  if (r.status !== 0) {
    attrapees += 1;
    const lignes = (r.stdout || "").split("\n");
    const premier = lignes.find((l) => l.includes("ECART") || l.includes("ECHEC"));
    console.log(`  ok    ${libelle}`);
    if (premier) console.log(`          vue en : ${premier.trim().replace(/^(ECART|ECHEC)\s*/, "")}`);
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
