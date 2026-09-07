/**
 * Le pont, eprouve contre un Word simule.
 *
 *     node addin/essais.js
 *
 * Pourquoi une batterie separee. Tout le reste du portage est verifie par
 * parite : il y a un Python en face qui dit la reponse. Le pont, non — il n'a
 * pas d'equivalent Python, parce qu'il traduit des evenements Office.js que le
 * banc d'essai ne produit jamais. C'est pourtant lui qui porte la decision 2 :
 * si les suites d'evenements que Word emet reellement ne se lisent pas comme
 * on l'a suppose, le curseur ne separe plus une premiere frappe d'un retour, et
 * tripoter redevient un moyen de simuler de la croissance.
 *
 * Le Word simule ici n'imite pas Word : il imite les SUITES D'EVENEMENTS
 * documentees. Notamment celle qui a motive tout le fichier — la selection qui
 * se declenche a chaque frappe, parce que taper deplace le point d'insertion.
 */

import { Paysage, SEUIL_COLLAGE, MOTS_LISIBLES } from "./src/paysage.js";
import { Pont } from "./src/pont.js";

// --------------------------------------------------------------------------
let passes = 0;
const echecs = [];
let courant = "";

function essai(nom, f) {
  courant = nom;
  return f().then(
    () => { passes += 1; },
    (e) => { echecs.push([nom, e && e.message ? e.message : String(e)]); },
  );
}

function vrai(condition, quoi) {
  if (!condition) throw new Error(quoi);
}

function egal(obtenu, attendu, quoi) {
  const a = JSON.stringify(attendu);
  const o = JSON.stringify(obtenu);
  if (a !== o) throw new Error(`${quoi} : attendu ${a}, obtenu ${o}`);
}

/**
 * Un Word simule. Il ne tient qu'un tableau de paragraphes et distribue des
 * identifiants de session, comme le vrai — qui les change a chaque ouverture.
 */
class WordSimule {
  constructor() {
    this.paras = new Map();       // id -> {texte, style}
    this.suivant = 0;
    this.pont = null;
  }

  lire(ids) {
    return Promise.resolve(ids
      .filter((id) => this.paras.has(id))
      .map((id) => ({ id, texte: this.paras.get(id).texte,
                      style: this.paras.get(id).style })));
  }

  /**
   * L'utilisateur appuie sur Entree : Word cree un paragraphe VIDE.
   *
   * C'est la sequence reelle, et elle a fait tomber le premier jet du pont —
   * l'empreinte du vide entrait au registre, et le deuxieme retour a la ligne
   * etait lu comme « connue ».
   */
  entree(style = "Normal") {
    const id = `p${this.suivant++}`;
    this.paras.set(id, { texte: "", style });
    this.pont.signaler("ajout", [id]);
    this.pont.signaler_curseur(id);
    return id;
  }

  /** Un paragraphe apparait deja plein : c'est la signature d'un collage. */
  coller(texte, style = "Normal") {
    const id = `p${this.suivant++}`;
    this.paras.set(id, { texte, style });
    this.pont.signaler("ajout", [id]);
    return id;
  }

  /**
   * L'utilisateur TAPE un paragraphe, a vitesse humaine.
   *
   * Entree, puis le texte arrive par bouffees de quatre mots — soixante mots
   * par minute — avec un vidage entre chaque, comme le ferait le tic de deux
   * secondes. Ecrire le paragraphe entier d'un coup, comme le faisait la
   * premiere version de ces essais, c'est simuler un collage et pas une
   * frappe : les vingt-quatre mots arrivaient dans le meme intervalle et
   * passaient legitimement le seuil de la decision 4.
   */
  async taper(texte, style = "Normal", mots_par_bouffee = 4) {
    const id = this.entree(style);
    await this.pont.vider();
    const mots = texte.split(/\s+/u);
    let courant = "";
    for (let i = 0; i < mots.length; i += mots_par_bouffee) {
      courant = mots.slice(0, i + mots_par_bouffee).join(" ");
      this.paras.get(id).texte = courant;
      this.pont.signaler("changement", [id]);
      this.pont.signaler_curseur(id);        // taper deplace le point d'insertion
      await this.pont.vider();
    }
    return id;
  }

  /** L'utilisateur modifie un paragraphe existant. onParagraphChanged. */
  modifier(id, texte, { curseur = true } = {}) {
    this.paras.get(id).texte = texte;
    this.pont.signaler("changement", [id]);
    if (curseur) this.pont.signaler_curseur(id);
  }

  supprimer(id) {
    this.paras.delete(id);
    this.pont.signaler("suppression", [id]);
  }

  /** Un co-auteur modifie un paragraphe : source = "Remote". */
  distant(id, texte) {
    this.paras.get(id).texte = texte;
    this.pont.signaler("changement", [id], true);
  }
}

function monter(horloge = null) {
  const p = new Paysage({ identifiant: "essai", cle_dossier: "essai" });
  const w = new WordSimule();
  const pont = new Pont(p, (ids) => w.lire(ids), horloge || (() => ({ jour: 100, heure: 14 })));
  w.pont = pont;
  return { paysage: p, word: w, pont };
}

const PHRASE = "La chambre neuve gardait la porte, et le couloir revenait vers "
  + "la lampe posee contre le mur, sans que rien ne bouge.";

// --------------------------------------------------------------------------
// Decision 2 : le curseur
// --------------------------------------------------------------------------
const suite = [];

suite.push(["taper un paragraphe neuf le fait pousser", async () => {
  const { word, paysage } = monter();
  await word.taper(PHRASE);
  egal(paysage.segments[0].nouveaux, 1, "un paragraphe ecrit");
  vrai(paysage.segments[0].mots > 15,
       `les mots comptent, obtenu ${paysage.segments[0].mots}`);
}]);

// Le defaut que cette batterie a trouve, et qui aurait ete livre : Word cree un
// paragraphe VIDE a chaque retour a la ligne. Sans filtre, l'empreinte du vide
// entre au registre au premier Entree, et tous les suivants sont « connue » —
// le plant cesse de pousser au deuxieme paragraphe.
suite.push(["chaque retour a la ligne compte, pas seulement le premier", async () => {
  const { word, paysage } = monter();
  for (let i = 0; i < 5; i++) await word.taper(`${PHRASE} Numero ${i}.`);
  egal(paysage.segments[0].nouveaux, 5,
       "cinq paragraphes tapes doivent faire cinq paragraphes");
}]);

// Le second defaut trouve par cette batterie, et le pire des deux. Un
// paragraphe qu'on TAPE passe par tous ses etats intermediaires, et chacun
// entre au registre. En francais, un paragraphe sur deux commence par les memes
// quatre mots : le suivant etait donc declare « connue » et disparaissait, sans
// que rien ne le signale. Le plant cessait de pousser au milieu d'une page.
suite.push(["un paragraphe qui COMMENCE comme un autre compte quand meme",
  async () => {
    const { word, paysage } = monter();
    await word.taper("Il faut donc admettre que la mesure ne dit rien de son objet.");
    await word.taper("Il faut donc reprendre la question par un tout autre bout.");
    await word.taper("Il faut donc admettre que la suite ne se laisse pas ecrire.");
    egal(paysage.segments[0].nouveaux, 3,
         "trois paragraphes tapes, meme s'ils commencent pareil");
  }]);

// Et l'inverse doit rester vrai : un paragraphe qui ARRIVE deja fait, sans
// qu'on l'ait vu naitre, reste reconnu. C'est ce qui rend un deplacement
// gratuit, et c'est pour ca que l'exception est portee par le pont — lui seul
// sait ce qu'il a vu naitre.
suite.push(["la naissance n'excuse que ce qu'on a vu naitre", async () => {
  const { word, pont, paysage } = monter();
  const texte = "Un paragraphe qui existera en deux exemplaires dans la page.";
  await word.taper(texte);
  const mots = paysage.segments[0].mots;
  word.coller(texte);                    // apparait deja fait : c'est un doublon
  const v = await pont.vider();
  egal(v.map((x) => x.verdict), ["connue"], "verdict");
  egal(paysage.segments[0].mots, mots, "rien n'a pousse");
}]);

suite.push(["un paragraphe vide ne fait rien et n'entre pas au registre", async () => {
  const { word, pont, paysage } = monter();
  word.entree();
  const v = await pont.vider();
  egal(v.map((x) => x.verdict), ["vide"], "verdict");
  egal(paysage.segments.length, 0, "aucun plant ouvert pour du vide");
  vrai(!pont.miroir.has("p0"), "le vide n'entre pas au miroir : il va se remplir");
}]);

suite.push(["continuer a taper dans le meme paragraphe reste une frappe", async () => {
  const { word, pont, paysage } = monter();
  const id = await word.taper(PHRASE);
  const avant = paysage.segments[0].mots;
  word.modifier(id, PHRASE + " Et la suite arrive tranquillement ensuite.");
  const v = await pont.vider();
  egal(v.map((x) => x.verdict), ["frappe"], "verdict");
  egal(paysage.segments[0].reprises, 0, "aucune reprise");
  vrai(paysage.segments[0].mots > avant, "les mots ajoutes comptent");
}]);

// C'EST L'ESSAI QUI JUSTIFIE LE PONT. Word n'a pas d'evenement de selection ;
// il faut passer par DocumentSelectionChanged, qui se declenche AUSSI a chaque
// frappe puisque taper deplace le point d'insertion. Si le pont appelait
// quitter() a chaque declenchement, chaque frappe deviendrait une visite neuve,
// donc une reprise — et une premiere redaction ne ferait plus jamais pousser la
// forme, ce que la decision 2 interdit exactement.
suite.push(["la selection qui se redeclenche dans le MEME paragraphe ne quitte rien",
  async () => {
    const { word, pont, paysage } = monter();
    const id = await word.taper(PHRASE);
    let texte = PHRASE;
    for (let i = 0; i < 20; i++) {
      texte += ` mot${i}`;
      word.modifier(id, texte);              // chaque frappe re-signale le curseur
      const v = await pont.vider();
      egal(v.map((x) => x.verdict), ["frappe"], `verdict au tour ${i}`);
    }
    egal(paysage.segments[0].reprises, 0,
         "vingt frappes ne doivent produire aucune reprise");
  }]);

suite.push(["quitter le paragraphe puis y revenir donne une reprise", async () => {
  const { word, pont, paysage } = monter();
  const a = await word.taper(PHRASE);
  const b = await word.taper("Un second paragraphe, ecrit juste apres le premier.");
  const mots = paysage.segments[0].mots;
  // On revient sur le premier : la selection change de paragraphe.
  word.modifier(a, PHRASE + " Une precision ajoutee trois jours plus tard.");
  const v = await pont.vider();
  egal(v.map((x) => x.verdict), ["reprise"], "verdict");
  egal(paysage.segments[0].reprises, 1, "une reprise, une seule");
  egal(paysage.segments[0].mots, mots,
       "les mots d'une reprise NE COMPTENT PAS dans l'extension");
  vrai(b !== a, "deux identifiants distincts");
}]);

suite.push(["dix reprises dans la meme visite n'en comptent qu'une", async () => {
  const { word, pont, paysage } = monter();
  const a = await word.taper(PHRASE);
  await word.taper("Un second paragraphe ecrit ailleurs dans la page.");
  let texte = PHRASE;
  for (let i = 0; i < 10; i++) {
    texte += ` retouche${i}`;
    word.modifier(a, texte);
    await pont.vider();
  }
  egal(paysage.segments[0].reprises, 1,
       "une visite vaut une reprise, pas dix — sinon dix minutes de reecriture"
       + " compteraient trois cents passages");
}]);

// --------------------------------------------------------------------------
// Decision 3 : le registre
// --------------------------------------------------------------------------
suite.push(["un paragraphe deplace ne fait rien pousser", async () => {
  const { word, pont, paysage } = monter();
  const a = await word.taper(PHRASE);
  const avant = { nouveaux: paysage.segments[0].nouveaux,
                  mots: paysage.segments[0].mots };
  // Deplacer, c'est disparaitre puis reapparaitre sous un identifiant NEUF,
  // avec le meme texte. Le registre de la decision 3 doit rendre ca gratuit.
  word.supprimer(a);
  word.coller(PHRASE);
  const v = await pont.vider();
  egal(v.map((x) => x.verdict), ["connue"], "verdict");
  egal(paysage.segments[0].nouveaux, avant.nouveaux, "aucun paragraphe de plus");
  egal(paysage.segments[0].mots, avant.mots, "aucun mot de plus");
}]);

suite.push(["supprimer est gratuit et ne casse rien", async () => {
  const { word, pont, paysage } = monter();
  const a = await word.taper(PHRASE);
  const mots = paysage.segments[0].mots;
  word.supprimer(a);
  await pont.vider();
  egal(paysage.segments[0].mots, mots, "rien ne recule (decision 1)");
  vrai(!pont.miroir.has(a), "le miroir oublie le paragraphe supprime");
}]);

// --------------------------------------------------------------------------
// Decision 4 : le collage
// --------------------------------------------------------------------------
suite.push(["un collage d'un bloc devient une greffe", async () => {
  const { word, pont, paysage } = monter();
  // Douze paragraphes arrivent dans le meme intervalle de deux secondes.
  for (let i = 0; i < 12; i++) word.coller(`${PHRASE} Variante numero ${i}.`);
  const v = await pont.vider();
  vrai(v.every((x) => x.verdict === "greffe"),
       `tout devrait etre greffe, obtenu ${JSON.stringify(v.map((x) => x.verdict))}`);
  egal(paysage.segments[0].nouveaux, 0, "une greffe ne fait pas pousser");
  vrai(paysage.segments[0].greffes === 12, "douze greffes en attente");
}]);

suite.push(["une greffe retouchee reste une greffe si on ne la convertit pas",
  async () => {
    const { word, pont, paysage } = monter();
    for (let i = 0; i < 12; i++) word.coller(`${PHRASE} Variante ${i}.`);
    await pont.vider();
    // Le pont appelle retoucher(..., etait_greffe=false) : la conversion de la
    // decision 4 demande de savoir qu'on retouche une greffe, et le pont ne le
    // sait pas encore. C'est un point ouvert, consigne comme tel.
    word.modifier("p0", `${PHRASE} Variante 0, retravaillee a la main.`);
    const v = await pont.vider();
    egal(v.map((x) => x.verdict), ["reprise"], "verdict");
    egal(paysage.segments[0].greffes, 12, "la greffe n'est pas convertie");
  }]);

suite.push(["ecrire a vitesse humaine ne declenche jamais la greffe", async () => {
  const { word, paysage } = monter();
  for (let i = 0; i < 6; i++) await word.taper(`${PHRASE} Paragraphe ${i}.`);
  egal(paysage.segments[0].nouveaux, 6, "six paragraphes ecrits");
  egal(paysage.segments[0].greffes, 0, "aucune greffe");
}]);

// Le debit se compte PAR INTERVALLE, pas par vidage. Si le volet est masque ou
// la machine chargee, un vidage peut couvrir dix secondes : quinze mots tapes
// honnetement arrivent alors d'un coup, et sans normalisation ils passent le
// seuil. On aurait converti l'ecriture de quelqu'un en collage.
suite.push(["un vidage en retard ne transforme pas la frappe en collage", async () => {
  const { word, pont, paysage } = monter();
  const id = word.entree();
  await pont.vider();
  // Trente mots arrives d'un coup, mais apres dix secondes d'attente.
  word.paras.get(id).texte = PHRASE + " " + PHRASE;
  pont.signaler("changement", [id]);
  await pont.vider(10000);
  egal(paysage.segments[0].greffes, 0, "ce n'est pas un collage");
  vrai(paysage.segments[0].mots > 40, "les mots comptent");
}]);

// --------------------------------------------------------------------------
// Ce que la documentation d'Office.js a impose
// --------------------------------------------------------------------------
suite.push(["la frappe d'un co-auteur ne fait pas pousser notre paysage", async () => {
  const { word, pont, paysage } = monter();
  const a = await word.taper(PHRASE);
  const avant = paysage.segments[0].mots;
  word.distant(a, `${PHRASE} Ajout d'un relecteur, a distance.`);
  const v = await pont.vider();
  egal(v, [], "aucun verdict : l'evenement distant est ignore");
  egal(paysage.segments[0].mots, avant, "rien n'a bouge");
}]);

suite.push(["le curseur qui sort du document quitte le paragraphe", async () => {
  const { word, pont, paysage } = monter();
  const a = await word.taper(PHRASE);
  vrai(pont.signaler_curseur(null), "sortir du document est un depart");
  word.modifier(a, `${PHRASE} Repris apres avoir ferme la fenetre.`,
                { curseur: true });
  const v = await pont.vider();
  egal(v.map((x) => x.verdict), ["reprise"], "verdict");
  egal(paysage.segments[0].reprises, 1, "une reprise");
}]);

// --------------------------------------------------------------------------
// Decision 11 : l'ouverture
// --------------------------------------------------------------------------
suite.push(["un document deja ecrit est acquis, pas recommence", async () => {
  const { pont, paysage } = monter();
  const deja = [];
  for (let i = 0; i < 40; i++) {
    deja.push({ id: `v${i}`, texte: `${PHRASE} Paragraphe existant ${i}.`,
                style: i === 0 ? "Titre 1" : "Normal" });
  }
  pont.rattacher(deja);
  vrai(paysage.segments[0].mots > 800,
       `le capital de depart doit etre reel, obtenu ${paysage.segments[0].mots}`);
  egal(paysage.segments[0].nouveaux, 40, "quarante paragraphes acquis");
  vrai(pont.miroir.size === 40, "le miroir est reconstruit");
}]);

suite.push(["apres rattachement, les memes paragraphes ne repoussent pas", async () => {
  const { word, pont, paysage } = monter();
  const deja = [];
  for (let i = 0; i < 10; i++) {
    deja.push({ id: `v${i}`, texte: `${PHRASE} Existant ${i}.`, style: "Normal" });
  }
  pont.rattacher(deja);
  const mots = paysage.segments[0].mots;
  // Word rouvre le fichier : nouveaux identifiants, meme texte. Les
  // identifiants de session ne survivent pas a une fermeture — c'est
  // l'empreinte qui traverse, pas l'identifiant.
  for (let i = 0; i < 10; i++) {
    word.paras.set(`n${i}`, { texte: `${PHRASE} Existant ${i}.`, style: "Normal" });
    pont.signaler("ajout", [`n${i}`]);
  }
  const v = await pont.vider();
  vrai(v.every((x) => x.verdict === "connue"),
       `tout devrait etre connu, obtenu ${JSON.stringify(v.map((x) => x.verdict))}`);
  egal(paysage.segments[0].mots, mots, "le paysage n'a pas bouge");
}]);

// --------------------------------------------------------------------------
// La file
// --------------------------------------------------------------------------
suite.push(["deux evenements sur le meme paragraphe ne comptent qu'une fois",
  async () => {
    const { word, pont, paysage } = monter();
    const id = word.entree();
    await pont.vider();
    word.paras.get(id).texte = "Quatre mots ici seulement.";
    // Word emet souvent plusieurs changements pour une meme frappe.
    pont.signaler("changement", [id]);
    pont.signaler("changement", [id]);
    pont.signaler("changement", [id]);
    const v = await pont.vider();
    egal(v.length, 1, "un seul verdict pour trois evenements");
    egal(v[0].verdict, "ecriture", "le paragraphe naissant est une ecriture");
    egal(paysage.segments[0].nouveaux, 1, "un paragraphe");
  }]);

suite.push(["un vidage a vide ne fait rien", async () => {
  const { pont } = monter();
  egal(await pont.vider(), [], "rien a vider");
}]);

suite.push(["un paragraphe efface avant le vidage ne plante pas", async () => {
  const { word, pont } = monter();
  const id = word.coller(PHRASE);
  word.paras.delete(id);          // efface sans evenement : Word peut le faire
  const v = await pont.vider();
  egal(v, [], "aucun verdict, aucune exception");
}]);

// --------------------------------------------------------------------------
(async () => {
  const barre = "=".repeat(78);
  console.log(barre);
  console.log("ESSAIS — le pont entre Word et le paysage");
  console.log(barre);
  for (const [nom, f] of suite) {
    await essai(nom, f);
    if (echecs.length && echecs[echecs.length - 1][0] === nom) {
      console.log(`  ECHEC  ${nom}`);
      console.log(`           ${echecs[echecs.length - 1][1]}`);
    } else {
      console.log(`  ok     ${nom}`);
    }
  }
  console.log(barre);
  console.log(`${passes} passes, ${echecs.length} en echec`);
  console.log(barre);
  process.exit(echecs.length ? 1 : 0);
})();
