/**
 * Le volet, deroule contre un Office.js simule.
 *
 *     node addin/essais_volet.js
 *
 * Ce que ces essais peuvent dire, et ce qu'ils ne peuvent pas.
 *
 * PEUVENT : que le demarrage va jusqu'au bout, que le document est rattache au
 * bon paysage, que le scan d'ouverture ne fait rien pousser, que le tic dessine,
 * que l'etat se range et se relit, que le volet dit quelque chose plutot que de
 * rester noir quand Word est trop ancien. Autrement dit : que le cablage tient.
 *
 * NE PEUVENT PAS : que le vrai Word se comporte comme ce faux. C'est le risque
 * irreductible du projet, et il ne se leve qu'en deposant le manifeste dans un
 * vrai Word. Le simulateur ne fait qu'une chose honnete — il implemente les
 * formes documentees de l'API, et rien de plus. La ou la documentation ne dit
 * rien, il ne devine pas : il echoue.
 */

import { readFileSync } from "node:fs";
import { choisir } from "./src/magasin.js";
import { Veille } from "./src/nuit.js";
import { phrase_de_la_nuit, DEBLOCAGE, CREUX } from "./src/phrases.js";
import { CORPS } from "./src/message.js";

// --------------------------------------------------------------------------
// Le faux Office
// --------------------------------------------------------------------------
function monter_hote({ plafond = 109, url = "C:/These/chapitre1.docx",
                       paragraphes = [], reglages = {},
                       refus_sauvegarde = false,
                       fragment = "", question = "", question_genre = "" } = {}) {
  const etat = {
    paras: [],        // {id, text, style}
    suivant: 0,
    // DEUX SACS, PAS UN. set() garde en memoire pour la session ; c'est
    // saveAsync qui ecrit dans le .docx. Les confondre rendrait invisible le
    // seul comportement qui compte ici — un document ou personne n'a ecrit ne
    // doit pas ressortir marque comme modifie.
    reglages: { ...reglages },      // ce que la session voit
    persistes: { ...reglages },     // ce qui est reellement dans le fichier
    refus_sauvegarde,
    sauvegardes: 0,
    ecouteurs: {},    // "ajout" | "changement" | "suppression"
    selection: null,
    dessins: 0,
    dialogues: [],
    tic: null,
    casser: false,
    styles_cassent: false,
    ecritures: 0,
    lectures_de_style: 0,
    stockage: new Map(),
  };
  for (const p of paragraphes) {
    etat.paras.push({ id: `w${etat.suivant++}`, text: p.texte,
                      style: p.style || "Normal" });
  }

  const trouver = (id) => etat.paras.find((p) => p.id === id);

  // Un objet charge paresseusement, comme Office.js : load() puis sync().
  function proxyPara(id) {
    const o = { uniqueLocalId: id, _id: id, load() {}, isNullObject: !trouver(id) };
    Object.defineProperty(o, "text", { get() {
      const p = trouver(id);
      if (!p) throw new Error(`paragraphe ${id} introuvable`);
      return p.text;
    } });
    Object.defineProperty(o, "style", { get() {
      const p = trouver(id);
      if (!p) throw new Error(`paragraphe ${id} introuvable`);
      return p.style;
    } });
    return o;
  }

  globalThis.Office = {
    HostType: { Word: "Word" },
    AsyncResultStatus: { Succeeded: "succeeded", Failed: "failed" },
    EventType: {
      DocumentSelectionChanged: "documentSelectionChanged",
      DialogEventReceived: "dialogEventReceived",
      DialogMessageReceived: "dialogMessageReceived",
      DialogParentMessageReceived: "dialogParentMessageReceived",
    },
    context: {
      requirements: {
        // Les jeux d'API sont EMBOITES : un hote qui ne sait pas faire 1.6 ne
        // sait pas davantage faire 1.7. Le plafond est donne en centiemes —
        // 109 pour 1.9, 103 pour un Office LTSC 2021, 0 pour un Word qui ne
        // sait rien faire du tout.
        isSetSupported: (nom, v) => {
          if (nom !== "WordApi") return false;
          const [maj, min] = String(v).split(".").map(Number);
          return maj * 100 + (min || 0) <= plafond;
        },
      },
      diagnostics: { host: "Word", platform: "PC", version: "16.0.14334" },
      document: {
        url,
        settings: {
          get: (k) => etat.reglages[k],
          set: (k, v) => { etat.reglages[k] = v; },
          // La vraie signature rend un AsyncResult au rappel. Sans lui, un
          // refus du document serait indiscernable d'une reussite, et le volet
          // croirait avoir une copie de secours qu'il n'a pas.
          saveAsync: (rappel) => {
            etat.sauvegardes += 1;
            if (etat.refus_sauvegarde) {
              if (rappel) {
                rappel({ status: "failed",
                         error: { name: "Refuse", message: "trop gros" } });
              }
              return;
            }
            etat.persistes = { ...etat.reglages };
            if (rappel) rappel({ status: "succeeded" });
          },
        },
        addHandlerAsync: (type, h) => { etat.ecouteurs[type] = h; },
      },
      ui: {
        displayDialogAsync: (u, opts, cb) => {
          const d = { messages: [], addEventHandler(t, h) { this[t] = h; },
                      messageChild(m) { this.messages.push(m); } };
          etat.dialogues.push(d);
          cb({ status: "succeeded", value: d });
        },
      },
    },
    onReady: (cb) => { etat.demarrer = cb; },
  };

  globalThis.Word = {
    async run(f) {
      const ctx = {
        document: {
          body: {
            // Word joint les paragraphes par un retour chariot dans body.text.
            // Le simulateur doit le faire aussi, sinon la mesure du « corps en
            // un bloc » compterait des lignes qui n'existent pas.
            load() {},
            get text() {
              // Un corps qu'on n'arrive pas a lire : le document a bouge sous
              // les pieds du volet, ce qui remplace le paragraphe disparu du
              // chemin des evenements.
              if (etat.casser) throw new Error("le corps est illisible");
              return etat.paras.map((p) => p.text).join("\r");
            },
            paragraphs: {
              items: [],
              load(quoi) {
                // On COMPTE les lectures de style : c'est la lecture chere, et
                // savoir qu'elle ne part pas a chaque tic est tout l'interet.
                if (String(quoi || "").includes("style")) {
                  etat.lectures_de_style += 1;
                  if (etat.styles_cassent) throw new Error("styles illisibles");
                }
                this.items = etat.paras.map((p) => proxyPara(p.id));
              },
            },
          },
          getParagraphByUniqueLocalId: (id) => proxyPara(id),
          getSelection: () => ({
            paragraphs: { getFirstOrNullObject: () => proxyPara(etat.selection) },
          }),
        },
        sync: async () => {},
      };
      return f(ctx);
    },
  };

  globalThis.localStorage = {
    getItem: (k) => (etat.stockage.has(k) ? etat.stockage.get(k) : null),
    setItem: (k, v) => {
      // On COMPTE les ecritures de l'etat. localStorage est synchrone, et le
      // point 12 prescrit une ecriture amortie a trente secondes : savoir
      // qu'elle ne part pas a chaque tic est tout l'interet.
      if (k.startsWith("paysage:etat:")) etat.ecritures += 1;
      etat.stockage.set(k, String(v));
    },
    removeItem: (k) => { etat.stockage.delete(k); },
  };

  const faireElement = () => {
    const el = {
      innerHTML: "", textContent: "", clientWidth: 340, clientHeight: 430,
      // Les ecouteurs etaient jetes — addEventListener() {} — donc aucun essai
      // ne pouvait declencher le geste d'une personne. C'est ce qui a laisse
      // l'essai de l'apercu se contenter de verifier qu'AUCUN dialogue ne
      // s'ouvrait avant le clic, sans jamais cliquer.
      ecouteurs: {},
      addEventListener(type, h) { this.ecouteurs[type] = h; },
      attributs: {},
      setAttribute(k, v) { this.attributs[k] = String(v); },
      cliquer() {
        if (!this.ecouteurs.click) throw new Error("rien n'ecoute le clic");
        return this.ecouteurs.click();
      },
    };
    return el;
  };
  const elements = { paysage: faireElement(), mot: faireElement(),
                     apercu: faireElement(),
                     // Les questions du profil, comme dans volet.html : cachees,
                     // et leurs textes a ceux de qui offre — les essais leur en
                     // donnent un a eux, qui ne part jamais dans le livrable.
                     demande: faireElement(), question: faireElement(),
                     prenom: faireElement(), hors: faireElement(),
                     "partie-prenom": faireElement(), "partie-genre": faireElement(),
                     "question-genre": faireElement(), "accord-m": faireElement(),
                     "accord-f": faireElement(), "accord-i": faireElement() };
  elements.demande.hidden = true;
  elements.question.textContent = question;
  elements["question-genre"].textContent = question_genre;
  elements.prenom.value = "";
  elements.demande.soumettre = function soumettre() {
    if (!this.ecouteurs.submit) throw new Error("rien n'ecoute la reponse");
    this.ecouteurs.submit({ preventDefault() {} });
  };
  elements.prenom.taper = function taper(v) {
    this.value = v;
    if (!this.ecouteurs.input) throw new Error("rien n'ecoute la saisie");
    this.ecouteurs.input();
  };
  globalThis.document = { getElementById: (id) => elements[id] || null };
  globalThis.window = {
    // Le profil vit derriere le # : volet.html#prenom=…&accord=…
    location: { href: "https://exemple.invalid/paysage/volet.html"
                      + (fragment ? `#${fragment}` : "") },
    addEventListener() {},
  };
  globalThis.setInterval = (f) => { etat.tic = f; return 1; };
  globalThis.URL = URL;

  etat.elements = elements;
  etat.proxyPara = proxyPara;
  etat.ajouter = (texte, style = "Normal") => {
    const id = `w${etat.suivant++}`;
    etat.paras.push({ id, text: texte, style });
    return id;
  };
  return etat;
}

// --------------------------------------------------------------------------
let passes = 0;
const echecs = [];

function vrai(c, quoi) { if (!c) throw new Error(quoi); }
function egal(o, a, quoi) {
  if (JSON.stringify(a) !== JSON.stringify(o)) {
    throw new Error(`${quoi} : attendu ${JSON.stringify(a)}, obtenu ${JSON.stringify(o)}`);
  }
}

/**
 * Recharge volet.js.
 *
 * Un module ESM est mis en cache par son URL : sans le parametre qui change, le
 * deuxieme essai reutiliserait l'etat du premier — et les essais se
 * contamineraient sans qu'on le voie.
 */
let tour = 0;
async function demarrer(etat) {
  await import(`./src/volet.js?t=${tour++}`);
  await etat.demarrer({ host: "Word" });
}

const PHRASE = "La chambre neuve gardait la porte, et le couloir revenait vers "
  + "la lampe posee contre le mur, sans que rien ne bouge.";

/**
 * Taper un paragraphe comme Word le fait vraiment : Entree d'abord, qui cree
 * un paragraphe VIDE, puis le texte.
 */
async function entrer(etat) {
  // Word cree un paragraphe VIDE a chaque Entree. Personne ne previent le
  // volet : c'est le tic qui le verra en relisant le corps.
  const id = etat.ajouter("");
  await etat.tic();
  return id;
}

async function pousser(etat, texte) {
  const id = await entrer(etat);
  etat.paras.find((p) => p.id === id).text = texte;
  await etat.tic();
  return id;
}

/**
 * Laisse partir l'ecriture en attente.
 *
 * Le volet amortit a trente secondes (point 12) : un essai qui lit le stockage
 * juste apres avoir tape lit l'etat d'AVANT. C'est le comportement voulu, pas
 * un contretemps — il faut donc le laisser passer explicitement.
 */
async function laisser_ranger(etat) {
  const vraie = Date.now;
  try {
    Date.now = () => vraie() + 60000;
    await etat.tic();
  } finally {
    Date.now = vraie;
  }
}

/**
 * Ecrire en prenant son temps : chaque paragraphe dix minutes apres l'autre,
 * donc au-dela de ATTENTE_COPIE. Sans le saut, la copie dans le document se
 * retient — c'est justement ce qu'elle doit faire.
 */
async function pousser_au_long(etat, textes, pas = 10 * 60 * 1000) {
  const vraie = Date.now;
  let saut = vraie();
  try {
    for (const t of textes) {
      saut += pas;
      Date.now = () => saut;
      // eslint-disable-next-line no-await-in-loop
      await pousser(etat, t);
    }
  } finally {
    Date.now = vraie;
  }
}

const suite = [];

suite.push(["le demarrage va jusqu'au bout et dessine", async () => {
  const etat = monter_hote({ paragraphes: [{ texte: PHRASE }] });
  await demarrer(etat);
  vrai(etat.elements.paysage.innerHTML.includes("<svg"),
       "le volet doit contenir un SVG");
  vrai(etat.tic, "le tic est arme : c'est lui qui regarde, faute d'evenements");
}]);

// Un Office LTSC 2021 s'arrete a WordApi 1.3, et c'est la machine a qui ce
// cadeau est destine. Tout doit y marcher — c'est toute la raison du guet.
suite.push(["un Word de 2021, sans les evenements, fait pousser le paysage",
  async () => {
    const etat = monter_hote({ plafond: 103, paragraphes: [{ texte: PHRASE }] });
    await demarrer(etat);
    vrai(etat.tic, "le tic doit etre arme sur un WordApi 1.3");
    const avant = etat.elements.paysage.innerHTML;
    await pousser(etat, "Un paragraphe tape a la main, du premier au dernier mot.");
    vrai(etat.elements.paysage.innerHTML !== avant,
         "la forme doit avoir bouge");
    await laisser_ranger(etat);
    const id = etat.reglages["paysage.identifiant"];
    const range = JSON.parse(etat.stockage.get(`paysage:etat:${id}`));
    vrai(range.segments[0].nouveaux >= 2,
         `le plant doit avoir pousse, obtenu ${range.segments[0].nouveaux}`);
  }]);

suite.push(["un Word trop ancien dit ce qui manque au lieu de rester noir",
  async () => {
    const etat = monter_hote({ plafond: 0, paragraphes: [{ texte: PHRASE }] });
    await demarrer(etat);
    const mot = etat.elements.mot.textContent;
    vrai(mot.length > 20, "le volet doit expliquer, pas se taire");
    // L'invariant : un Word trop ancien ne fait RIEN pousser, et ne laisse
    // aucune trace derriere lui.
    vrai(!etat.elements.paysage.innerHTML.includes("<svg"),
         "aucun paysage ne doit etre dessine");
    egal(etat.stockage.size, 0, "ni quoi que ce soit range");
    egal(etat.sauvegardes, 0, "ni le document marque comme modifie");
  }]);

// Decision 11 : le paysage appartient au DOSSIER. Un second document du meme
// dossier rejoint le paysage du premier ; un document d'ailleurs en ouvre un
// autre, meme si le dossier porte le meme nom.
suite.push(["un second document du meme dossier rejoint le meme paysage", async () => {
  const a = monter_hote({ url: "C:/These/chapitre1.docx",
                          paragraphes: [{ texte: PHRASE }] });
  await demarrer(a);
  const id = a.reglages["paysage.identifiant"];
  const partage = a.stockage;

  const b = monter_hote({ url: "C:/These/chapitre2.docx",
                          paragraphes: [{ texte: "Un autre chapitre entier." }] });
  b.stockage = partage;                       // meme machine, meme localStorage
  globalThis.localStorage.getItem = (k) => (partage.has(k) ? partage.get(k) : null);
  globalThis.localStorage.setItem = (k, v) => { partage.set(k, String(v)); };
  await demarrer(b);
  egal(b.reglages["paysage.identifiant"], id,
       "le second document doit rejoindre le paysage du dossier");
}]);

suite.push(["un dossier different ouvre un autre paysage", async () => {
  const a = monter_hote({ url: "C:/These/chapitre1.docx",
                          paragraphes: [{ texte: PHRASE }] });
  await demarrer(a);
  const partage = a.stockage;
  const b = monter_hote({ url: "C:/Autre/Chapitres/note.docx",
                          paragraphes: [{ texte: "Un texte sans rapport." }] });
  b.stockage = partage;
  globalThis.localStorage.getItem = (k) => (partage.has(k) ? partage.get(k) : null);
  globalThis.localStorage.setItem = (k, v) => { partage.set(k, String(v)); };
  await demarrer(b);
  vrai(b.reglages["paysage.identifiant"] !== a.reglages["paysage.identifiant"],
       "deux dossiers, deux paysages");
}]);

// Decision 11 : rouvrir le fichier ne doit RIEN faire pousser. Les identifiants
// de paragraphe changent a chaque session ; c'est l'empreinte qui traverse.
suite.push(["rouvrir le document ne fait rien pousser", async () => {
  const paras = [];
  for (let i = 0; i < 12; i++) paras.push({ texte: `${PHRASE} Numero ${i}.` });
  const a = monter_hote({ paragraphes: paras });
  await demarrer(a);
  const id = a.reglages["paysage.identifiant"];
  const premier = JSON.parse(a.stockage.get(`paysage:etat:${id}`));
  const mots = premier.segments[0].mots;
  vrai(mots > 100, `le capital de depart doit etre reel, obtenu ${mots}`);

  // Deuxieme ouverture : memes textes, IDENTIFIANTS TOUT AUTRES. Et le fichier
  // ne porte encore rien — personne n'a tape, donc rien n'a ete sauvegarde :
  // c'est l'index du dossier qui doit rendre le meme paysage.
  const partage = a.stockage;
  const b = monter_hote({ paragraphes: paras, reglages: a.persistes });
  b.suivant = 500;                            // des identifiants qui ne collent pas
  b.paras = paras.map((p, i) => ({ id: `z${i}`, text: p.texte, style: "Normal" }));
  b.stockage = partage;
  globalThis.localStorage.getItem = (k) => (partage.has(k) ? partage.get(k) : null);
  globalThis.localStorage.setItem = (k, v) => { partage.set(k, String(v)); };
  await demarrer(b);
  const second = JSON.parse(partage.get(`paysage:etat:${id}`));
  egal(second.segments[0].mots, mots, "rouvrir n'ajoute pas un mot");
  egal(second.segments[0].nouveaux, premier.segments[0].nouveaux,
       "ni un paragraphe");
}]);

suite.push(["le tic voit ce qui a change, sans que personne le previenne",
  async () => {
    const etat = monter_hote({ paragraphes: [{ texte: PHRASE }] });
    await demarrer(etat);
    const id = etat.reglages["paysage.identifiant"];
    const avant = JSON.parse(etat.stockage.get(`paysage:etat:${id}`)).segments[0].mots;

    // On tape un paragraphe neuf : Entree, puis le texte. AUCUN evenement n'est
    // envoye — le simulateur n'en offre plus. Le tic doit s'en apercevoir seul.
    await pousser(etat, "Quatre mots arrivent ici, puis quelques autres encore.");
    await laisser_ranger(etat);

    const apres = JSON.parse(etat.stockage.get(`paysage:etat:${id}`)).segments[0].mots;
    vrai(apres > avant, `le paysage doit avoir pousse : ${avant} -> ${apres}`);
  }]);

// Ce que le guet decide — la fermeture de visite, le debit, la conversion — est
// eprouve par la parite, qui a un Python en face. Ici on ne verifie que le
// cablage : que le volet lise, nourrisse, et survive.
suite.push(["un tic qui leve n'arrete pas les suivants", async () => {
  const etat = monter_hote({ paragraphes: [{ texte: PHRASE }] });
  await demarrer(etat);
  etat.casser = true;
  await etat.tic();                       // le corps est illisible : ne doit pas lever
  etat.casser = false;
  await pousser(etat, "Un paragraphe qui, lui, arrive sans encombre.");
  vrai(etat.elements.paysage.innerHTML.includes("<svg"), "le volet dessine encore");
  const id = etat.reglages["paysage.identifiant"];
  vrai(etat.stockage.has(`paysage:etat:${id}`), "et range ce qui a pousse");
}]);

// ⚠️ localStorage EST SYNCHRONE. Le point 12 prescrit une ecriture amortie a
// trente secondes depuis le debut, et le portage ne l'avait jamais appliquee :
// on serialisait l'etat complet a chaque tic ou quelque chose avait pousse, sur
// le fil qui gere la frappe. C'est ce qui faisait saccader le vrai add-in.
suite.push(["l'etat ne se range pas a chaque tic", async () => {
  const etat = monter_hote({ paragraphes: [{ texte: PHRASE }] });
  await demarrer(etat);
  const depart = etat.ecritures;
  await pousser(etat, "Un premier paragraphe, tape sans lever les mains.");
  await pousser(etat, "Un second dans la foulee, quelques secondes apres.");
  await pousser(etat, "Un troisieme, toujours dans la meme minute.");
  egal(etat.ecritures, depart + 1,
       "une seule ecriture pour trois pousses rapprochees");
  // Rien ne se perd pour autant : l'ecriture attend, elle ne saute pas.
  await laisser_ranger(etat);
  egal(etat.ecritures, depart + 2, "et elle part des que le delai est passe");
  const id = etat.reglages["paysage.identifiant"];
  const range = JSON.parse(etat.stockage.get(`paysage:etat:${id}`));
  vrai(range.segments[0].nouveaux >= 4,
       `l'etat range doit porter les trois pousses, obtenu ${range.segments[0].nouveaux}`);
}]);

// Poser innerHTML fait reparser tout le SVG. Le point 12 veut que les plants
// acheves soient rasterises une fois ; en attendant, on evite au moins de
// re-poser un dessin identique — le vegetal ne change de forme que quatre fois
// sur toute la vie d'un plant.
//
// ⚠️ La premiere version de cet essai faisait deux tics SANS RIEN TAPER et
// verifiait que rien n'etait pose. Elle passait avec ou sans la garde :
// dessiner() n'est appele QUE si le tic a releve des faits, donc un tic vide
// ne pose jamais rien, garde ou pas. L'essai ne traversait pas le mecanisme
// qu'il pretendait tenir, et la mutation qui supprime la garde lui a echappe.
// C'est exactement le troisieme piege du LISEZMOI : un cahier qui a l'air
// complet et ne traverse jamais le mecanisme surveille.
//
// Le vrai cas est celui-la : un fait arrive ET le dessin ne change pas. Word
// cree un paragraphe VIDE a chaque Entree — c'est un fait, et il ne fait
// pousser personne.
suite.push(["un dessin identique n'est pas repose", async () => {
  const etat = monter_hote({ paragraphes: [{ texte: PHRASE }] });
  await demarrer(etat);
  const hote = etat.elements.paysage;
  let poses = 0;
  let valeur = hote.innerHTML;
  Object.defineProperty(hote, "innerHTML", {
    get() { return valeur; },
    set(v) { poses += 1; valeur = v; },
    configurable: true,
  });

  // Une Entree seule : le guet la releve, le paysage n'en tire rien.
  const id = await entrer(etat);
  egal(poses, 0, "une Entree seule ne doit rien reposer");

  // Et le texte qui la remplit, lui, doit bien redessiner.
  etat.paras.find((p) => p.id === id).text =
    "Un paragraphe entier, tape jusqu'au point final.";
  await etat.tic();
  vrai(poses > 0, "mais une pousse doit bien redessiner");
}]);

// Le style appartient au paragraphe, et la lecture qui le donne est CHERE : un
// objet Office.js par paragraphe. Elle ne doit partir que quand la structure
// bouge, jamais pendant qu'on tape dans un paragraphe existant.
// Une relecture ratee laisse la table DECALEE, pas seulement vieille. Sans
// memoire de cet echec, le compte de paragraphes correspondrait des le tic
// suivant et la table ne serait plus jamais relue.
suite.push(["une lecture de styles ratee se rejoue au tic suivant", async () => {
  const etat = monter_hote({ paragraphes: [{ texte: PHRASE }] });
  await demarrer(etat);
  const depart = etat.lectures_de_style;

  etat.styles_cassent = true;
  etat.ajouter("Un paragraphe neuf, dont on ne pourra pas lire le style.");
  await etat.tic();                       // la structure bouge, la lecture echoue
  egal(etat.lectures_de_style, depart + 1, "la relecture a bien ete tentee");
  vrai(etat.elements.paysage.innerHTML.includes("<svg"),
       "et l'echec n'arrete pas le volet");

  etat.styles_cassent = false;
  await etat.tic();                       // rien n'a bouge : elle doit repartir
  egal(etat.lectures_de_style, depart + 2,
       "une table perimee doit etre relue meme sans changement de structure");
  await etat.tic();
  egal(etat.lectures_de_style, depart + 2, "puis se taire une fois rattrapee");
}]);

suite.push(["les styles ne se relisent que quand la structure bouge", async () => {
  const etat = monter_hote({ paragraphes: [{ texte: PHRASE }] });
  await demarrer(etat);
  const depart = etat.lectures_de_style;
  // Taper DANS un paragraphe : aucune relecture.
  etat.paras[0].text = `${PHRASE} Et une suite.`;
  await etat.tic();
  egal(etat.lectures_de_style, depart, "taper ne change pas la structure");
  // Un paragraphe de plus : la table est perimee.
  etat.ajouter("Un paragraphe entierement neuf, avec son propre style.");
  await etat.tic();
  egal(etat.lectures_de_style, depart + 1, "un paragraphe de plus la perime");
}]);

// ⚠️ CET ESSAI NE CLIQUAIT PAS. Il portait « recoit la cle de son paysage »
// et verifiait une seule chose : qu'aucun dialogue n'etait ouvert AVANT le
// clic. Il ne cliquait jamais, donc il ne traversait rien de ce qu'il
// pretendait tenir — le troisieme piege du LISEZMOI, en entier.
//
// La poignee de main tient en trois temps, et chacun peut casser seul :
//   1. le clic ouvre le dialogue ;
//   2. le dialogue dit « pret » ;
//   3. LE VOLET REPOND ALORS la cle du paysage de CE dossier.
// Le volet ne parle pas le premier : le dialogue doit avoir pose son ecouteur.
suite.push(["l'apercu s'ouvre et recoit la cle de son paysage", async () => {
  const etat = monter_hote({ paragraphes: [{ texte: PHRASE }] });
  await demarrer(etat);
  await pousser(etat, "Un paragraphe, pour qu'il y ait quelque chose a voir.");
  await laisser_ranger(etat);
  egal(etat.dialogues.length, 0, "aucun dialogue avant le clic");

  etat.elements.apercu.cliquer();
  egal(etat.dialogues.length, 1, "le clic ouvre le dialogue");
  const d = etat.dialogues[0];
  egal(d.messages.length, 0,
       "et le volet se tait tant que le dialogue n'a pas parle");

  // Le dialogue dit « pret ».
  d.dialogMessageReceived();
  egal(d.messages.length, 1, "le volet repond, et une seule fois");

  const { cle, graine } = JSON.parse(d.messages[0]);
  const id = etat.reglages["paysage.identifiant"];
  egal(cle, `paysage:etat:${id}`,
       "la cle designe le paysage de CE dossier, pas un autre");
  vrai(typeof graine === "number" && Number.isFinite(graine),
       `la graine part avec, obtenu ${graine}`);

  // ⚠️ ET LA CLE DOIT EXISTER. Le dialogue relit le localStorage tout seul :
  // une cle juste qui ne designe rien lui fait afficher un volet vide, ce qui
  // ressemble a une panne alors que tout le cablage a marche.
  vrai(etat.stockage.has(cle),
       `le stockage ne contient rien sous ${cle} : le dialogue s'ouvrirait vide`);
  const relu = JSON.parse(etat.stockage.get(cle));
  vrai(relu.segments.length >= 1, "et ce qui s'y trouve porte au moins un plant");
}]);

// --------------------------------------------------------------------------
// Le dialogue de la vue d'ensemble (decision 14)
// --------------------------------------------------------------------------
// ⚠️ CE CABLAGE ETAIT EN LIGNE DANS apercu.html, donc atteignable par AUCUNE
// batterie : il n'y a rien a importer dans un script ecrit au milieu d'un
// fichier HTML. C'est exactement la qu'il s'est casse, et personne n'a rien vu.
// Il vit maintenant dans src/apercu.js, sous le meme faux Office que le volet.

/** Un faux Office.context.ui, ou addHandlerAsync est VRAIMENT asynchrone. */
function faux_bureau(journal) {
  let ecouteur = null;
  return {
    EventType: { DialogParentMessageReceived: "dialogParentMessageReceived" },
    context: {
      ui: {
        addHandlerAsync(type, h, rappel) {
          journal.push(`pose:${type}`);
          // Office.js pose l'ecouteur en asynchrone. Le simuler en synchrone
          // rendrait la course invisible, et c'est la course qui casse.
          setTimeout(() => {
            ecouteur = h;
            journal.push("pose");
            if (rappel) rappel({ status: "succeeded" });
          }, 0);
        },
        messageParent(m) { journal.push(`parent:${m}`); },
      },
    },
    // Ce que ferait le volet en repondant.
    repondre(message) {
      if (!ecouteur) { journal.push("PERDU"); return false; }
      ecouteur({ message });
      return true;
    },
  };
}

function faux_document() {
  const els = {
    paysage: { innerHTML: "", textContent: "", clientHeight: 520 },
    mot: { innerHTML: "", textContent: "" },
  };
  return { getElementById: (id) => els[id] || null, els };
}

suite.push(["l'apercu pose son ecouteur AVANT de se dire pret", async () => {
  const { demarrer_apercu } = await import("./src/apercu.js");
  const journal = [];
  const bureau = faux_bureau(journal);
  demarrer_apercu(bureau, faux_document());
  await new Promise((r) => setTimeout(r, 5));

  // L'ordre EST le contrat. Dire « pret » avant que l'ecouteur soit pose
  // laisse la reponse du volet tomber dans le vide — et le volet ne repond
  // qu'une fois, donc le dialogue reste blanc pour toujours.
  const pose = journal.indexOf("pose");
  const pret = journal.indexOf("parent:pret");
  vrai(pose !== -1, "l'ecouteur doit finir par etre pose");
  vrai(pret !== -1, "et le dialogue doit finir par se dire pret");
  vrai(pose < pret,
       `« pret » est parti avant que l'ecouteur soit pose : ${journal.join(" ")}`);
}]);

suite.push(["la reponse du volet dessine le paysage", async () => {
  const { demarrer_apercu } = await import("./src/apercu.js");
  const { Paysage } = await import("./src/paysage.js");

  const p = new Paysage("dlg", "dlg");
  p.absorber("Chapitre premier", "Titre 1", 0, 30, 14);
  // ⚠️ ASSEZ DE MOTS POUR LE VERROU. Douze paragraphes font 264 mots, sous
  // les 800 du verrou : le plant reste un germe et le SVG fait 156 octets. Un
  // essai du dialogue qui ne dessine qu'un germe ne dit presque rien.
  for (let i = 0; i < 45; i++) {
    p.absorber(`Une phrase de travail numero ${i}, ecrite a la main sans se`
      + " presser le moins du monde, pour que le plant ait de quoi pousser.",
    "Normal", 7, 30, 14);
  }
  const magasin = new Map([["paysage:etat:dlg", p.serialiser()]]);
  globalThis.localStorage = {
    getItem: (k) => (magasin.has(k) ? magasin.get(k) : null),
    setItem() {}, removeItem() {},
  };

  const doc = faux_document();
  const bureau = faux_bureau([]);
  demarrer_apercu(bureau, doc);
  await new Promise((r) => setTimeout(r, 5));

  vrai(bureau.repondre(JSON.stringify({ cle: "paysage:etat:dlg", graine: 7 })),
       "l'ecouteur doit etre la quand le volet repond");
  vrai(doc.els.paysage.innerHTML.startsWith("<svg"),
       `le dialogue doit porter un SVG, obtenu "${doc.els.paysage.innerHTML.slice(0, 40)}"`);
  vrai(doc.els.paysage.innerHTML.includes("<line"),
       "le dialogue doit porter des traits, pas un SVG vide");
  vrai(doc.els.paysage.innerHTML.length > 2000,
       "un plant verrouille fait bien plus qu'un germe (156 octets), obtenu "
       + doc.els.paysage.innerHTML.length);
  egal(doc.els.mot.textContent, "", "et rien a dire quand tout va bien");

  // Et une cle qui ne designe rien se DIT, au lieu de laisser un blanc.
  const doc2 = faux_document();
  const b2 = faux_bureau([]);
  demarrer_apercu(b2, doc2);
  await new Promise((r) => setTimeout(r, 5));
  b2.repondre(JSON.stringify({ cle: "paysage:etat:absent", graine: 7 }));
  vrai(doc2.els.mot.textContent.length > 0,
       "un paysage introuvable doit se dire, pas laisser une fenetre blanche");
  egal(doc2.els.paysage.innerHTML, "", "et ne rien dessiner");

  // ⚠️ ET UNE LECTURE IMPOSSIBLE, qui n'est pas la meme chose qu'un paysage
  // absent. Paysage.depuis() est defensive : elle ne leve jamais, meme sur du
  // JSON casse — elle rend un paysage vide. Le seul chemin qui atteint le
  // catch est localStorage LUI-MEME qui refuse, ce qui arrive quand le
  // navigateur bloque les donnees de site : getItem LEVE, il ne rend pas null.
  // Sans message, la fenetre reste blanche et rien ne dit pourquoi.
  const garde = globalThis.localStorage;
  globalThis.localStorage = {
    getItem() {
      const e = new Error("acces refuse aux donnees de site");
      e.name = "SecurityError";
      throw e;
    },
  };
  const doc3 = faux_document();
  const b3 = faux_bureau([]);
  demarrer_apercu(b3, doc3);
  await new Promise((r) => setTimeout(r, 5));
  b3.repondre(JSON.stringify({ cle: "paysage:etat:dlg", graine: 7 }));
  globalThis.localStorage = garde;
  vrai(doc3.els.mot.textContent.includes("SecurityError"),
       "une lecture impossible doit NOMMER la panne, obtenu"
       + ` "${doc3.els.mot.textContent}"`);
  egal(doc3.els.paysage.innerHTML, "", "et ne rien dessiner de faux");
}]);

// --------------------------------------------------------------------------
// Les deux magasins (decision 16)
// --------------------------------------------------------------------------
// Le localStorage est indexe par ORIGINE : il meurt avec l'hebergeur, avec la
// machine, et avec un simple vidage des donnees de site. La copie rangee dans
// le .docx est ce qui rend le paysage independant de tout ca.

suite.push(["entre les deux copies, la plus fournie fait autorite", async () => {
  const { Paysage } = await import("./src/paysage.js");
  const petit = new Paysage();
  petit.absorber(PHRASE, "Normal", 0, 10, 14);
  const grand = Paysage.depuis(petit.serialiser());
  grand.absorber("Un second paragraphe, plus loin dans le meme chapitre, qui "
    + "ne ressemble pas du tout au premier.", "Normal", 0, 10, 14);
  vrai(grand.registre.size === petit.registre.size + 1,
       "le montage doit bien donner une empreinte de plus");

  egal(choisir(petit.serialiser(), grand.serialiser()).source, "fichier",
       "le fichier plus fourni l'emporte");
  egal(choisir(grand.serialiser(), petit.serialiser()).source, "dossier",
       "et le dossier plus fourni aussi");
  // A egalite, le dossier : c'est le magasin de travail, et basculer pour un
  // contenu identique ne rapporterait rien.
  egal(choisir(grand.serialiser(), grand.serialiser()).source, "dossier",
       "a egalite, le dossier garde la main");
  // Une copie illisible repart vide, donc a zero empreinte : elle perd toute
  // seule, sans qu'on ait a la valider en plus.
  egal(choisir(null, "{tronque").source, "neuf", "deux riens font un neuf");
  egal(choisir(petit.serialiser(), "{tronque").source, "dossier",
       "une copie illisible ne peut pas gagner");
}]);

suite.push(["la copie de secours part des que le paysage pousse", async () => {
  const etat = monter_hote({ paragraphes: [{ texte: PHRASE }] });
  await demarrer(etat);
  egal(etat.persistes["paysage.etat"], undefined,
       "rien dans le fichier avant la premiere pousse");
  await pousser(etat, "Un paragraphe tape a la main, du premier au dernier mot.");
  const copie = etat.persistes["paysage.etat"];
  vrai(copie && JSON.parse(copie).registre.length > 0,
       "le document doit porter une copie relisible");
  egal(etat.persistes["paysage.identifiant"], etat.reglages["paysage.identifiant"],
       "et l'identite part par la meme sauvegarde");
}]);

// Le cas pour lequel tout ceci existe : l'origine change, la machine change,
// ou les donnees de site sont videes. Il ne reste que le fichier.
suite.push(["le dossier perdu, le document rend le paysage", async () => {
  const a = monter_hote({ paragraphes: [{ texte: PHRASE }] });
  await demarrer(a);
  await pousser_au_long(a, [
    "Le premier paragraphe arrive lentement, un mot apres l'autre.",
    "Le deuxieme suit bien plus tard, sans que rien ne presse personne.",
    "Le troisieme ferme la page et laisse la lampe allumee derriere lui.",
  ]);
  const id = a.reglages["paysage.identifiant"];
  const fichier = JSON.parse(a.persistes["paysage.etat"]);
  vrai(fichier.registre.length >= 3,
       `la copie doit suivre la pousse, obtenu ${fichier.registre.length}`);

  // Machine neuve : localStorage vide, seul le .docx arrive avec ses reglages.
  const b = monter_hote({ paragraphes: [{ texte: PHRASE }], reglages: a.persistes });
  vrai(b.stockage.size === 0, "le nouveau poste ne connait rien");
  await demarrer(b);
  const rendu = JSON.parse(b.stockage.get(`paysage:etat:${id}`));
  egal(rendu.registre.length, fichier.registre.length,
       "le paysage revient du document sans rien perdre en route");
  egal(rendu.segments[0].mots, fichier.segments[0].mots, "avec ses mots");
  egal(b.reglages["paysage.identifiant"], id, "et sous la meme identite");
}]);

// ⚠️ UNE MINUTE entre les pousses, pas zero, et c'est tout l'essai.
//
// Depuis que le volet amortit l'ecriture a trente secondes, trois pousses
// instantanees n'appellent copier() QU'UNE SEULE FOIS : le frein du volet
// suffisait a donner le bon compte, et l'essai passait sans jamais atteindre
// l'etranglement du magasin qu'il croyait tenir. La mutation qui supprime cet
// etranglement lui a echappe le jour ou l'amortissement est arrive.
//
// Il faut donc laisser passer AMORTI (30 s) sans laisser passer ATTENTE_COPIE
// (5 min) : trois appels a copier(), une seule copie.
suite.push(["deux pousses rapprochees ne recopient qu'une fois", async () => {
  const etat = monter_hote({ paragraphes: [{ texte: PHRASE }] });
  await demarrer(etat);
  await pousser_au_long(etat, [
    "Un premier paragraphe, tape sans lever les mains.",
    "Un second dans la foulee, une minute apres.",
    "Un troisieme, toujours dans le meme quart d'heure.",
  ], 60 * 1000);
  egal(etat.sauvegardes, 1,
       "recopier 78 Ko dans le document a chaque tic marquerait le fichier"
     + " modifie mille huit cents fois par heure");
}]);

suite.push(["passe le delai, la copie repart", async () => {
  const etat = monter_hote({ paragraphes: [{ texte: PHRASE }] });
  await demarrer(etat);
  await pousser_au_long(etat, [
    "Un premier paragraphe, ecrit sans se presser le moins du monde.",
    "Un second paragraphe, bien plus tard dans la meme soiree.",
  ]);
  egal(etat.sauvegardes, 2, "une copie par pousse quand elles sont espacees");
}]);

suite.push(["un verdict sans empreinte neuve ne recopie rien", async () => {
  const etat = monter_hote({ paragraphes: [{ texte: PHRASE }] });
  await demarrer(etat);
  await pousser(etat, "Un paragraphe entier, tape jusqu'au point final.");

  // Deux retours a la ligne, tres espaces, pour que le delai ne soit jamais en
  // cause. Un paragraphe vide n'est pas encore un paragraphe : il rend un
  // verdict, mais aucune empreinte de plus.
  const vraie = Date.now;
  try {
    Date.now = () => vraie() + 10 * 60 * 1000;
    await entrer(etat);                       // rattrape le retard de la pousse
    const rattrape = etat.sauvegardes;
    egal(rattrape, 2, "le premier tic espace rattrape ce qui restait a copier");
    Date.now = () => vraie() + 20 * 60 * 1000;
    await entrer(etat);                       // et celui-la n'a plus rien a porter
    egal(etat.sauvegardes, rattrape,
         "le document n'est pas reecrit pour reposer la meme chose");
  } finally {
    Date.now = vraie;
  }
}]);

suite.push(["un document qui refuse la copie ne casse pas le volet", async () => {
  const etat = monter_hote({ paragraphes: [{ texte: PHRASE }],
                             refus_sauvegarde: true });
  await demarrer(etat);
  await pousser_au_long(etat, [
    "Un premier paragraphe, pose la comme si de rien n'etait.",
    "Un second paragraphe, longtemps apres, dans le meme calme.",
  ]);
  vrai(etat.elements.paysage.innerHTML.includes("<svg"), "le volet dessine encore");
  egal(etat.sauvegardes, 1, "apres un refus on n'insiste pas");
  const id = etat.reglages["paysage.identifiant"];
  vrai(etat.stockage.has(`paysage:etat:${id}`), "et le dossier garde tout");
}]);

suite.push(["une copie illisible dans le document ne casse pas l'ouverture",
  async () => {
    const etat = monter_hote({ paragraphes: [{ texte: PHRASE }],
                               reglages: { "paysage.etat": "{tronque" } });
    await demarrer(etat);
    vrai(etat.elements.paysage.innerHTML.includes("<svg"),
         "le volet dessine quand meme");
  }]);

// --------------------------------------------------------------------------
// La nuit (decision 10)
// --------------------------------------------------------------------------
// Le profil, la question du prenom, et le message qui se revele entre 2 h et
// 5 h. Ce qui choisit la phrase et ce qui la trace est eprouve par la parite ;
// ici, le cablage — et nuit.js, qui n'a pas de Python en face.

/**
 * Fige l'horloge. En heure LOCALE : c'est ainsi que le volet lit la fenetre de
 * nuit, et un essai qui tournerait sur l'heure reelle changerait de verdict
 * selon le moment ou on le lance.
 */
async function a_l_heure(quand, f) {
  const vraie = Date.now;
  Date.now = () => quand.getTime();
  try {
    return await f();
  } finally {
    Date.now = vraie;
  }
}

const le_12_a = (h, m = 0) => new Date(2026, 8, 12, h, m);
const NUIT = (i) => `Une ligne ecrite dans la nuit, la numero ${i}, sans lever `
  + "les mains du clavier ni regarder l'heure.";
const QUESTION = "(texte d'essai, pas celui du cadeau)";

/** Les traits du message dans le volet, ou -1 s'il n'y a pas de message. */
function traits_du_message(etat) {
  const s = etat.elements.paysage.innerHTML;
  const i = s.indexOf('<g class="message">');
  return i < 0 ? -1 : (s.slice(i).match(/<line/g) || []).length;
}

/**
 * Les traits du message en coordonnees LOCALES, sans la pose.
 *
 * ⚠️ PAS LE GROUPE ENTIER. La pose — translate, scale, epaisseur — suit le
 * cadre de la vue, donc le paysage, donc la graine du document, tiree au
 * hasard a chaque hote monte. Deux volets differaient TOUJOURS par la, meme
 * sur la meme phrase : l'essai du # passait sans que le # soit lu, et la
 * mutation qui l'ignore ne l'a jamais fait echouer. Les coordonnees locales ne
 * dependent que de la phrase, de la nuit et des mots ecrits.
 */
function coordonnees(dessin) {
  return [...dessin.matchAll(/x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"/g)]
    .map((m) => m.slice(1).join(",")).join(" ");
}

/** Meme machine, meme localStorage : un second volet sur le stockage du premier. */
function partager(etat, stockage) {
  etat.stockage = stockage;
  globalThis.localStorage.getItem = (k) => (stockage.has(k) ? stockage.get(k) : null);
  globalThis.localStorage.setItem = (k, v) => { stockage.set(k, String(v)); };
}

/**
 * Ecrire un paragraphe de nuit comme une personne : Entree, puis le texte
 * trente secondes plus tard.
 *
 * ⚠️ PAS D'UN COUP. Tape dans le meme releve que l'Entree, un paragraphe de
 * dix-sept mots depasse SEUIL_COLLAGE — quinze mots par intervalle : c'est un
 * collage pour la decision 4, et un collage ne credite aucun mot, ni au
 * paysage ni a la nuit. Les premiers essais de la nuit tapaient ainsi, et le
 * message n'apparaissait jamais : le cablage etait juste, la frappe ne l'etait
 * pas.
 */
async function ecrire_la_nuit(etat, quand, texte) {
  const id = await a_l_heure(quand, () => entrer(etat));
  await a_l_heure(new Date(quand.getTime() + 30 * 1000), async () => {
    etat.paras.find((p) => p.id === id).text = texte;
    await etat.tic();
  });
}

suite.push(["le message de nuit se revele aux mots ecrits, pas a l'horloge",
  async () => {
    const etat = monter_hote({ paragraphes: [{ texte: PHRASE }] });
    await a_l_heure(le_12_a(3), () => demarrer(etat));
    egal(traits_du_message(etat), -1, "pas de message avant le premier mot de la nuit");
    await ecrire_la_nuit(etat, le_12_a(3, 5), NUIT(0));
    const premiers = traits_du_message(etat);
    vrai(premiers > 0, "le premier paragraphe de la nuit ouvre le message");
    // Rester assis ne suffit pas : une heure et demie plus tard, une Entree
    // seule — un releve, des verdicts, et pas un mot.
    await a_l_heure(le_12_a(4, 35), () => entrer(etat));
    egal(traits_du_message(etat), premiers,
         "une heure et demie sans ecrire ne revele rien de plus");
    await ecrire_la_nuit(etat, le_12_a(4, 40), NUIT(1));
    vrai(traits_du_message(etat) > premiers, "ecrire revele la suite");
  }]);

suite.push(["a 5 h le message reste, et la reouverture l'efface", async () => {
  const a = monter_hote({ paragraphes: [{ texte: PHRASE }] });
  await a_l_heure(le_12_a(4, 50), () => demarrer(a));
  await ecrire_la_nuit(a, le_12_a(4, 55), NUIT(0));
  const traces = traits_du_message(a);
  vrai(traces > 0, "le message a commence avant 5 h");
  // On ecrit encore apres 5 h : plus rien ne se revele, et rien ne s'efface
  // sous les yeux.
  await ecrire_la_nuit(a, le_12_a(5, 10), NUIT(1));
  egal(traits_du_message(a), traces, "apres 5 h, ce qui est trace reste tel quel");

  // Word se ferme et se rouvre, la matinee venue : rien n'a ete range.
  const b = monter_hote({ paragraphes: [{ texte: PHRASE }], reglages: a.persistes });
  partager(b, a.stockage);
  await a_l_heure(le_12_a(9), () => demarrer(b));
  await ecrire_la_nuit(b, le_12_a(9, 5), NUIT(2));
  egal(traits_du_message(b), -1, "la reouverture ne ramene pas le message");
}]);

suite.push(["la nuit ne se revele qu'avec ses propres mots, entiere vers 800",
  async () => {
    const profil = { prenom: "Camille", accord: "f" };
    // Cinq cents mots ecrits lors de nuits d'avant : ils sont au paysage, pas
    // a cette nuit-ci.
    const v = new Veille(profil, 500);
    v.suivre([{ verdict: "ecriture" }], 540, le_12_a(3));
    vrai(v.phrase !== null, "le premier mot tire la phrase");
    vrai(v.avancement > 0 && v.avancement < 0.1,
         `quarante mots ne revelent presque rien, obtenu ${v.avancement}`);
    v.suivre([{ verdict: "ecriture" }], 900, le_12_a(3, 30));
    vrai(v.avancement > 0.4 && v.avancement < 0.6,
         `quatre cents mots en revelent la moitie, obtenu ${v.avancement}`);
    v.suivre([{ verdict: "ecriture" }], 1300, le_12_a(4));
    egal(v.avancement, 1, "huit cents mots, et la phrase est entiere");
  }]);

suite.push(["la phrase est fixee au premier mot, et un deblocage arrive a temps",
  async () => {
    const profil = { prenom: "Camille", accord: "f" };
    const cinq = Array.from({ length: 5 }, () => ({ verdict: "reprise" }));

    // Cinq reprises ne comptent aucun mot : rien n'est tire. Le paragraphe qui
    // les suit ouvre la nuit, et c'est un deblocage.
    const a = new Veille(profil, 0);
    a.suivre(cinq, 0, le_12_a(3));
    egal(a.phrase, null, "des reprises seules ne tirent rien");
    a.suivre([{ verdict: "ecriture" }], 14, le_12_a(3, 10));
    vrai(DEBLOCAGE.includes(a.phrase),
         `le deblocage donne sa phrase, obtenu "${a.phrase}"`);

    // Une nuit ordinaire tire dans le paquet, puis un deblocage survient : la
    // phrase ne change pas sous les yeux.
    const b = new Veille(profil, 0);
    b.suivre([{ verdict: "ecriture" }], 14, le_12_a(3));
    const premiere = b.phrase;
    vrai(premiere !== null && !DEBLOCAGE.includes(premiere),
         "une nuit ordinaire tire dans le paquet");
    b.suivre(cinq, 14, le_12_a(3, 20));
    b.suivre([{ verdict: "ecriture" }], 30, le_12_a(3, 30));
    egal(b.nuit.evenement(), "deblocage", "le deblocage est bien survenu");
    egal(b.phrase, premiere, "mais la phrase tiree au premier mot reste");
  }]);

suite.push(["un registre vide retombe sur le paquet, comme en Python", async () => {
  const profil = { prenom: "Camille", accord: "f" };
  const v = new Veille(profil, 0);
  v.suivre(Array.from({ length: 4 }, () => ({ verdict: "reprise" })), 0, le_12_a(3));
  v.suivre([{ verdict: "frappe" }], 9, le_12_a(3, 5));
  egal(v.nuit.evenement(), "creux",
       "quatre reprises sans paragraphe neuf font un creux");
  vrai(v.phrase !== null, "un registre vide ne casse rien : une phrase est servie");
  // CREUX est vide tant que celui qui offre ne l'a pas ecrit. Le jour ou il le
  // sera, c'est lui qui servira, et cette derniere verification se taira.
  if (!CREUX.length) {
    egal(v.phrase, phrase_de_la_nuit(profil, "2026-09-12"), "celle du paquet, a sa date");
  }
}]);

suite.push(["le volet lit le prenom et l'accord derriere le # de son adresse",
  async () => {
    const profils = [["prenom=Camille&accord=f", { prenom: "Camille", accord: "f" }],
                     ["prenom=Camille", { prenom: "Camille", accord: null }],
                     ["", { prenom: null, accord: null }]];
    // Une nuit ou les trois profils tirent trois phrases qui ne commencent pas
    // par la meme lettre — sinon les premiers traits se ressembleraient. On la
    // CHERCHE, on ne la suppose pas.
    const iso = (j) => `2026-09-${String(j).padStart(2, "0")}`;
    const tetes = (j) => new Set(profils.map(([, p]) => phrase_de_la_nuit(p, iso(j))[0]));
    let jour = 12;
    while (jour < 30 && tetes(jour).size < 3) jour += 1;
    vrai(jour < 30, "aucune nuit de septembre ne separe les trois profils");

    const dessins = [];
    for (const [fragment] of profils) {
      const etat = monter_hote({ paragraphes: [{ texte: PHRASE }], fragment });
      // eslint-disable-next-line no-await-in-loop
      await a_l_heure(new Date(2026, 8, jour, 3), () => demarrer(etat));
      for (let i = 0; i < 3; i++) {
        // eslint-disable-next-line no-await-in-loop
        await ecrire_la_nuit(etat, new Date(2026, 8, jour, 3, 5 + i), NUIT(i));
      }
      const s = etat.elements.paysage.innerHTML;
      vrai(s.includes('<g class="message">'), `#${fragment} : le message doit etre la`);
      dessins.push(coordonnees(s.slice(s.indexOf('<g class="message">'))));
    }
    egal(new Set(dessins).size, 3, "trois adresses, trois messages : le # est lu");
  }]);

suite.push(["sans prenom dans l'adresse, la question est posee une fois", async () => {
  const paras = [{ texte: PHRASE }];
  const a = monter_hote({ paragraphes: paras, question: QUESTION });
  await demarrer(a);
  egal(a.elements.demande.hidden, false, "posee a la premiere ouverture");

  // Ignoree : Word se ferme sans reponse. Meme machine, deuxieme ouverture.
  const b = monter_hote({ paragraphes: paras, question: QUESTION, reglages: a.persistes });
  partager(b, a.stockage);
  await demarrer(b);
  egal(b.elements.demande.hidden, true, "ignoree, elle n'est jamais reposee");

  const c = monter_hote({ paragraphes: paras, question: QUESTION,
                          fragment: "prenom=Camille" });
  await demarrer(c);
  egal(c.elements.demande.hidden, true, "un prenom dans l'adresse : rien a demander");

  // Le document arrive d'une autre machine, ou le prenom avait ete donne.
  const d = monter_hote({ paragraphes: paras, question: QUESTION,
                          reglages: { "paysage.prenom": "Camille" } });
  await demarrer(d);
  egal(d.elements.demande.hidden, true, "un prenom venu dans le document : rien non plus");

  // Sans son texte, la question se tait — et n'est pas comptee comme posee.
  const e = monter_hote({ paragraphes: paras });
  await demarrer(e);
  egal(e.elements.demande.hidden, true, "sans texte, pas de question");
  egal(e.stockage.has("paysage:prenom:demande"), false,
       "et elle reste a poser, pour le jour ou le texte sera ecrit");
}]);

suite.push(["repondre n'ecrit rien dans le document", async () => {
  const etat = monter_hote({ paragraphes: [{ texte: PHRASE }], question: QUESTION });
  await demarrer(etat);
  etat.elements.prenom.value = "Camille";
  etat.elements.demande.soumettre();
  egal(etat.elements.demande.hidden, true, "la question se retire une fois repondue");
  egal(etat.sauvegardes, 0, "repondre ne sauvegarde pas le document");
  egal(etat.persistes["paysage.prenom"], undefined, "rien dans le fichier");
  egal(etat.reglages["paysage.prenom"], "Camille", "le reglage attend dans la session");
  egal(etat.stockage.get("paysage:prenom"), "Camille", "et le dossier le garde");
  await pousser(etat, "Un paragraphe tape a la main, du premier au dernier mot.");
  egal(etat.persistes["paysage.prenom"], "Camille",
       "il part avec la prochaine copie du paysage");
}]);

suite.push(["un signe que l'alphabet ne dessine pas est signale a la saisie",
  async () => {
    const etat = monter_hote({ paragraphes: [{ texte: PHRASE }], question: QUESTION });
    await demarrer(etat);
    const { prenom, hors } = etat.elements;
    prenom.taper("Zoé");
    egal(hors.textContent, "", "un accent se retire au trace : rien a signaler");
    prenom.taper("Marie-Anne N’Dri");
    egal(hors.textContent, "", "l'espace, le trait d'union et l'apostrophe se dessinent");
    prenom.taper("Søren");
    vrai(hors.textContent.includes("Ø"),
         `le Ø doit etre signale, obtenu "${hors.textContent}"`);
  }]);

suite.push(["le message se pose dans le ciel, par-dessus le paysage", async () => {
  const etat = monter_hote({ paragraphes: [{ texte: PHRASE }] });
  await a_l_heure(le_12_a(3), () => demarrer(etat));
  for (let i = 0; i < 20; i++) {
    // eslint-disable-next-line no-await-in-loop
    await ecrire_la_nuit(etat, le_12_a(3, 1 + i), NUIT(i));
  }
  const s = etat.elements.paysage.innerHTML;
  const i = s.indexOf('<g class="message">');
  vrai(i > s.lastIndexOf("<g opacity="), "le message vient apres les plants, donc par-dessus");
  const [vx, vy, vw, vh] = s.match(/viewBox="([^"]+)"/)[1].split(" ").map(Number);
  const [, ox, oy, k] = s.slice(i)
    .match(/translate\(([-\d.]+),([-\d.]+)\) scale\(([-\d.]+)\)/).map(Number);
  let bas = -Infinity;
  let gauche = Infinity;
  let droite = -Infinity;
  for (const m of s.slice(i).matchAll(
    /x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"/g)) {
    const [, x1, y1, x2, y2] = m.map(Number);
    bas = Math.max(bas, oy + y1 * k, oy + y2 * k);
    gauche = Math.min(gauche, ox + x1 * k, ox + x2 * k);
    droite = Math.max(droite, ox + x1 * k, ox + x2 * k);
  }
  vrai(bas > -Infinity, "le message doit porter des traits");
  vrai(bas < vy + vh * 0.45,
       `le message doit rester dans le haut de la vue, il descend a ${((bas - vy) / vh).toFixed(2)}`);
  vrai(gauche >= vx && droite <= vx + vw, "et tenir dans sa largeur");
}]);

// ⚠️ LES TROIS ESSAIS QUI SUIVENT MANQUAIENT a la premiere livraison. Une
// relecture a froid a trouve trois promesses du cablage qu'aucun essai ne
// traversait — et chacune de leurs regressions passait les trente-cinq autres.

const jour_iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-`
  + String(d.getDate()).padStart(2, "0");
const lendemain = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate() + 1, d.getHours());

/** Ecrit trois paragraphes a partir de 3 h 05 cette nuit-la, et rend le message. */
async function trois_paragraphes(etat, nuit) {
  for (let k = 0; k < 3; k++) {
    // eslint-disable-next-line no-await-in-loop
    await ecrire_la_nuit(etat, new Date(nuit.getTime() + (5 + k) * 60000), NUIT(k));
  }
  const s = etat.elements.paysage.innerHTML;
  const i = s.indexOf('<g class="message">');
  return i < 0 ? "" : s.slice(i);
}

suite.push(["un prenom compose n'ouvre pas le message sur un blanc", async () => {
  // A quatorze signes par ligne, « MARIE-ANTOINETTE, » ne tient pas : sans
  // largeur_pour, _mise_en_page pousse une premiere ligne VIDE, et les
  // premieres lettres tombent sur la deuxieme. On cherche une nuit ou le
  // prenom ouvre la phrase — on ne la suppose pas.
  const profil = { prenom: "Marie-Antoinette", accord: "f" };
  const ouvre = (d) => phrase_de_la_nuit(profil, jour_iso(d)).toLowerCase()
    .startsWith("marie-antoinette,");
  let nuit = le_12_a(3);
  for (let k = 0; k < 60 && !ouvre(nuit); k++) nuit = lendemain(nuit);
  vrai(ouvre(nuit), "aucune nuit de ces deux mois ne s'ouvre sur le prenom");

  const etat = monter_hote({ paragraphes: [{ texte: PHRASE }],
                             fragment: "prenom=Marie-Antoinette&accord=f" });
  await a_l_heure(nuit, () => demarrer(etat));
  const dessin = await trois_paragraphes(etat, nuit);
  // Les coordonnees des traits sont LOCALES au message : la premiere ligne
  // occupe 0 a CORPS, la deuxieme commence a deux corps.
  const ys = [...dessin.matchAll(/y1="([-\d.]+)" x2="[-\d.]+" y2="([-\d.]+)"/g)]
    .flatMap((m) => [Number(m[1]), Number(m[2])]);
  vrai(ys.length > 0, "le message doit porter des traits");
  vrai(Math.min(...ys) < CORPS,
       `les premieres lettres doivent tomber sur la premiere ligne, pas sous un blanc :`
       + ` le plus haut trait est a ${Math.min(...ys)}`);
}]);

suite.push(["un prenom deja repondu part avec le document suivant", async () => {
  // Repondu sur ce poste, dans un autre document : le volet le reprend, et le
  // pose dans celui-ci — il partira avec sa premiere copie, pas avant.
  const etat = monter_hote({ paragraphes: [{ texte: PHRASE }] });
  etat.stockage.set("paysage:prenom", "Camille");
  await demarrer(etat);
  egal(etat.sauvegardes, 0, "ouvrir n'enregistre rien");
  egal(etat.persistes["paysage.prenom"], undefined, "rien dans le fichier a l'ouverture");
  await pousser(etat, "Un paragraphe tape a la main, du premier au dernier mot.");
  egal(etat.persistes["paysage.prenom"], "Camille",
       "il part avec la premiere copie de ce document");
}]);

suite.push(["la reponse compte des cette nuit, sans rouvrir", async () => {
  // Une nuit ou le prenom change la premiere lettre de la phrase : sinon les
  // deux dessins se ressembleraient au debut, avec ou sans lui.
  const tete = (p, d) => phrase_de_la_nuit(p, jour_iso(d))[0];
  const avec = { prenom: "Camille", accord: null };
  const sans = { prenom: null, accord: null };
  let nuit = le_12_a(3);
  for (let k = 0; k < 60 && tete(avec, nuit) === tete(sans, nuit); k++) nuit = lendemain(nuit);
  vrai(tete(avec, nuit) !== tete(sans, nuit), "aucune nuit ne distingue les deux profils");

  const repondu = monter_hote({ paragraphes: [{ texte: PHRASE }], question: QUESTION });
  await a_l_heure(nuit, () => demarrer(repondu));
  repondu.elements.prenom.value = "Camille";
  repondu.elements.demande.soumettre();
  const d1 = await trois_paragraphes(repondu, nuit);

  const par_adresse = monter_hote({ paragraphes: [{ texte: PHRASE }],
                                    fragment: "prenom=Camille" });
  await a_l_heure(nuit, () => demarrer(par_adresse));
  const d2 = await trois_paragraphes(par_adresse, nuit);

  vrai(coordonnees(d1).length > 0, "le message doit etre la");
  vrai(coordonnees(d1) === coordonnees(d2),
       "le prenom repondu doit compter cette nuit comme celui de l'adresse");
}]);

// Le genre, demande depuis le 11 septembre 2026 sous trois choix neutres
// (decision 10 revisee une seconde fois).
const TEXTE_GENRE = "(texte d'essai du genre, pas celui du cadeau)";

suite.push(["sans accord dans l'adresse, le genre est demande une fois", async () => {
  const paras = [{ texte: PHRASE }];
  // Le prenom vient de l'adresse : seule la question du genre se pose.
  const a = monter_hote({ paragraphes: paras, question: QUESTION,
                          question_genre: TEXTE_GENRE, fragment: "prenom=Camille" });
  await demarrer(a);
  egal(a.elements.demande.hidden, false, "posee a la premiere ouverture");
  egal(a.elements["partie-genre"].hidden, false, "le genre est demande");
  egal(a.elements["partie-prenom"].hidden, true, "pas le prenom, que l'adresse donne");

  const b = monter_hote({ paragraphes: paras, question: QUESTION, question_genre: TEXTE_GENRE,
                          fragment: "prenom=Camille", reglages: a.persistes });
  partager(b, a.stockage);
  await demarrer(b);
  egal(b.elements.demande.hidden, true, "ignoree, elle n'est jamais reposee");

  const c = monter_hote({ paragraphes: paras, question_genre: TEXTE_GENRE,
                          fragment: "prenom=Camille&accord=f" });
  await demarrer(c);
  egal(c.elements.demande.hidden, true, "un accord dans l'adresse : rien a demander");

  const d = monter_hote({ paragraphes: paras, question_genre: TEXTE_GENRE,
                          fragment: "prenom=Camille", reglages: { "paysage.accord": "i" } });
  await demarrer(d);
  egal(d.elements.demande.hidden, true, "un accord venu dans le document : rien non plus");

  const e = monter_hote({ paragraphes: paras, fragment: "prenom=Camille" });
  await demarrer(e);
  egal(e.elements.demande.hidden, true, "sans sa phrase, pas de question du genre");
  egal(e.stockage.has("paysage:accord:demande"), false,
       "et elle reste a poser, pour le jour ou la phrase sera donnee");

  // UNE MARQUE PAR QUESTION. Le prenom demande d'abord, seul ; la phrase du
  // genre donnee ensuite : a l'ouverture suivante, le genre se pose quand meme.
  const f = monter_hote({ paragraphes: paras, question: QUESTION });
  await demarrer(f);
  egal(f.elements["partie-genre"].hidden, true, "sans sa phrase, le genre ne se montre pas");
  const g = monter_hote({ paragraphes: paras, question: QUESTION, question_genre: TEXTE_GENRE,
                          reglages: f.persistes });
  partager(g, f.stockage);
  await demarrer(g);
  egal(g.elements.demande.hidden, false, "la phrase donnee plus tard, le genre est demande");
  egal(g.elements["partie-prenom"].hidden, true, "mais pas le prenom, deja demande");

  // Et les trois choix de volet.html designent bien les trois formes.
  const html = readFileSync(new URL("./volet.html", import.meta.url), "utf-8");
  for (const [id, choix] of [["accord-m", "M"], ["accord-f", "F"], ["accord-i", "NB"]]) {
    vrai(new RegExp(`id="${id}"[^>]*>${choix}<`).test(html),
         `volet.html : « ${choix} » doit choisir ${id}`);
  }
}]);

suite.push(["choisir le genre n'ecrit rien dans le document, et compte des cette nuit",
  async () => {
    // Une nuit ou l'accord change la premiere lettre de la phrase.
    const tete = (p, d) => phrase_de_la_nuit(p, jour_iso(d))[0];
    const avec = { prenom: null, accord: "f" };
    const sans = { prenom: null, accord: null };
    let nuit = le_12_a(3);
    for (let k = 0; k < 60 && tete(avec, nuit) === tete(sans, nuit); k++) nuit = lendemain(nuit);
    vrai(tete(avec, nuit) !== tete(sans, nuit), "aucune nuit ne distingue les deux profils");

    const choisi = monter_hote({ paragraphes: [{ texte: PHRASE }], question_genre: TEXTE_GENRE });
    await a_l_heure(nuit, () => demarrer(choisi));
    choisi.elements["accord-f"].cliquer();
    egal(choisi.elements.demande.hidden, true,
         "seule, la question du genre se retire des qu'on a choisi");
    egal(choisi.sauvegardes, 0, "choisir ne sauvegarde pas le document");
    egal(choisi.persistes["paysage.accord"], undefined, "rien dans le fichier");
    egal(choisi.reglages["paysage.accord"], "f", "le reglage attend dans la session");
    egal(choisi.stockage.get("paysage:accord"), "f", "et le dossier le garde");
    const d1 = await trois_paragraphes(choisi, nuit);
    egal(choisi.persistes["paysage.accord"], "f", "il part avec la copie du paysage");

    const par_adresse = monter_hote({ paragraphes: [{ texte: PHRASE }], fragment: "accord=f" });
    await a_l_heure(nuit, () => demarrer(par_adresse));
    const d2 = await trois_paragraphes(par_adresse, nuit);
    vrai(coordonnees(d1).length > 0, "le message doit etre la");
    vrai(coordonnees(d1) === coordonnees(d2),
         "le genre choisi doit compter cette nuit comme celui de l'adresse");
  }]);

// --------------------------------------------------------------------------
// Le manifeste
// --------------------------------------------------------------------------
suite.push(["le manifeste est bien forme et complet", async () => {
  const xml = readFileSync(new URL("./manifest.xml", import.meta.url), "utf-8");
  for (const balise of ["Id", "Version", "ProviderName", "DisplayName",
                        "Description", "DefaultSettings", "Permissions",
                        "SourceLocation", "VersionOverrides"]) {
    vrai(xml.includes(`<${balise}`), `il manque <${balise}>`);
  }
  const id = xml.match(/<Id>([^<]+)<\/Id>/);
  vrai(id && /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/
    .test(id[1]), `l'identifiant doit etre un GUID, obtenu ${id && id[1]}`);
  // Bien forme : on empile les balises et on verifie qu'elles se referment
  // dans l'ordre. Compter les ouvrantes et les fermantes ne suffisait pas —
  // les commentaires du manifeste contiennent des chevrons, et le compte
  // partait a l'envers.
  const net = xml.replace(/<!--[\s\S]*?-->/g, "").replace(/<\?[\s\S]*?\?>/g, "");
  const pile = [];
  for (const m of net.matchAll(/<(\/?)([A-Za-z][\w:.-]*)([^>]*?)(\/?)>/g)) {
    const [, fermante, nom, reste, seule] = m;
    if (seule || reste.endsWith("/")) continue;
    if (fermante) {
      const attendu = pile.pop();
      vrai(attendu === nom, `</${nom}> ferme <${attendu}>`);
    } else {
      pile.push(nom);
    }
  }
  egal(pile, [], "toutes les balises se referment");
  // Et surtout : AUCUNE contrainte de version, qui rendrait l'add-in invisible.
  // Sur `net` et non sur `xml` : le manifeste EXPLIQUE en commentaire pourquoi
  // il n'en a pas, et l'essai trebuchait sur sa propre explication.
  vrai(!net.includes("<Requirements>"),
       "une contrainte non satisfaite rend l'add-in invisible, sans un mot :"
       + " le volet doit s'ouvrir et expliquer lui-meme");
}]);

suite.push(["les pages pointent vers des fichiers qui existent", async () => {
  for (const page of ["volet.html", "apercu.html"]) {
    const html = readFileSync(new URL(`./${page}`, import.meta.url), "utf-8");
    vrai(html.includes("appsforoffice.microsoft.com/lib/1/hosted/office.js"),
         `${page} doit charger office.js`);
    for (const m of html.matchAll(/(?:src|from)\s*=?\s*["']\.?\/?(src\/[\w.]+)["']/g)) {
      readFileSync(new URL(`./${m[1]}`, import.meta.url));   // leve si absent
    }
  }
}]);

// --------------------------------------------------------------------------
(async () => {
  const barre = "=".repeat(78);
  console.log(barre);
  console.log("ESSAIS — le volet contre un Office.js simule");
  console.log(barre);
  for (const [nom, f] of suite) {
    try {
      await f();
      passes += 1;
      console.log(`  ok     ${nom}`);
    } catch (e) {
      echecs.push([nom, e && e.message ? e.message : String(e)]);
      console.log(`  ECHEC  ${nom}`);
      console.log(`           ${e && e.message ? e.message : e}`);
    }
  }
  console.log(barre);
  console.log(`${passes} passes, ${echecs.length} en echec`);
  console.log(barre);
  process.exit(echecs.length ? 1 : 0);
})();
