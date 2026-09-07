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

// --------------------------------------------------------------------------
// Le faux Office
// --------------------------------------------------------------------------
function monter_hote({ plafond = 109, url = "C:/These/chapitre1.docx",
                       paragraphes = [], reglages = {},
                       refus_sauvegarde = false } = {}) {
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
    setItem: (k, v) => { etat.stockage.set(k, String(v)); },
    removeItem: (k) => { etat.stockage.delete(k); },
  };

  const faireElement = () => {
    const el = { innerHTML: "", textContent: "", clientWidth: 340,
                 clientHeight: 430, addEventListener() {} };
    return el;
  };
  const elements = { paysage: faireElement(), mot: faireElement(),
                     apercu: faireElement() };
  globalThis.document = { getElementById: (id) => elements[id] || null };
  globalThis.window = {
    location: { href: "https://exemple.invalid/paysage/volet.html" },
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
 * Ecrire en prenant son temps : chaque paragraphe dix minutes apres l'autre,
 * donc au-dela de ATTENTE_COPIE. Sans le saut, la copie dans le document se
 * retient — c'est justement ce qu'elle doit faire.
 */
async function pousser_au_long(etat, textes) {
  const vraie = Date.now;
  let saut = vraie();
  try {
    for (const t of textes) {
      saut += 10 * 60 * 1000;
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

suite.push(["l'apercu s'ouvre et recoit la cle de son paysage", async () => {
  const etat = monter_hote({ paragraphes: [{ texte: PHRASE }] });
  await demarrer(etat);
  etat.elements.apercu.addEventListener = () => {};
  // On declenche le clic comme le ferait le bouton.
  const { default: _ } = { default: null };
  vrai(etat.dialogues.length === 0, "aucun dialogue avant le clic");
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

suite.push(["deux pousses rapprochees ne recopient qu'une fois", async () => {
  const etat = monter_hote({ paragraphes: [{ texte: PHRASE }] });
  await demarrer(etat);
  await pousser(etat, "Un premier paragraphe, tape sans lever les mains.");
  await pousser(etat, "Un second dans la foulee, quelques secondes apres.");
  await pousser(etat, "Un troisieme, toujours dans la meme minute.");
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
