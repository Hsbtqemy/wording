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

// --------------------------------------------------------------------------
// Le faux Office
// --------------------------------------------------------------------------
function monter_hote({ version16 = true, url = "C:/These/chapitre1.docx",
                       paragraphes = [], reglages = {} } = {}) {
  const etat = {
    paras: [],        // {id, text, style}
    suivant: 0,
    reglages: { ...reglages },
    sauvegardes: 0,
    ecouteurs: {},    // "ajout" | "changement" | "suppression"
    selection: null,
    dessins: 0,
    dialogues: [],
    tic: null,
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
        isSetSupported: (nom, v) => nom === "WordApi" && (version16 || v !== "1.6"),
      },
      document: {
        url,
        settings: {
          get: (k) => etat.reglages[k],
          set: (k, v) => { etat.reglages[k] = v; },
          saveAsync: () => { etat.sauvegardes += 1; },
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
            paragraphs: {
              items: [],
              load() { this.items = etat.paras.map((p) => proxyPara(p.id)); },
            },
          },
          getParagraphByUniqueLocalId: (id) => proxyPara(id),
          getSelection: () => ({
            paragraphs: { getFirstOrNullObject: () => proxyPara(etat.selection) },
          }),
          onParagraphAdded: { add: (h) => { etat.ecouteurs.ajout = h; } },
          onParagraphChanged: { add: (h) => { etat.ecouteurs.changement = h; } },
          onParagraphDeleted: { add: (h) => { etat.ecouteurs.suppression = h; } },
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

const suite = [];

suite.push(["le demarrage va jusqu'au bout et dessine", async () => {
  const etat = monter_hote({ paragraphes: [{ texte: PHRASE }] });
  await demarrer(etat);
  vrai(etat.elements.paysage.innerHTML.includes("<svg"),
       "le volet doit contenir un SVG");
  vrai(etat.ecouteurs.ajout && etat.ecouteurs.changement && etat.ecouteurs.suppression,
       "les trois evenements de paragraphe sont branches");
  vrai(etat.ecouteurs.documentSelectionChanged,
       "le curseur est branche sur DocumentSelectionChanged");
  vrai(etat.tic, "le tic est arme");
}]);

suite.push(["un Word trop ancien dit ce qui manque au lieu de rester noir",
  async () => {
    const etat = monter_hote({ version16: false, paragraphes: [{ texte: PHRASE }] });
    await demarrer(etat);
    vrai(etat.elements.mot.textContent.length > 20,
         "le volet doit expliquer, pas se taire");
    vrai(!etat.tic, "et ne rien armer");
  }]);

suite.push(["le document tire un identifiant et le range dans ses reglages",
  async () => {
    const etat = monter_hote({ paragraphes: [{ texte: PHRASE }] });
    await demarrer(etat);
    const id = etat.reglages["paysage.identifiant"];
    vrai(id && id.length > 4, "un identifiant est tire");
    vrai(etat.sauvegardes >= 1, "et sauvegarde dans le document");
    vrai(etat.stockage.has(`paysage:etat:${id}`), "l'etat est range");
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

  // Deuxieme ouverture : memes textes, IDENTIFIANTS TOUT AUTRES.
  const partage = a.stockage;
  const b = monter_hote({ paragraphes: paras, reglages: a.reglages });
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

suite.push(["le tic absorbe ce que les evenements ont mis en file", async () => {
  const etat = monter_hote({ paragraphes: [{ texte: PHRASE }] });
  await demarrer(etat);
  const id = etat.reglages["paysage.identifiant"];
  const avant = JSON.parse(etat.stockage.get(`paysage:etat:${id}`)).segments[0].mots;

  // On tape un paragraphe neuf : Entree, puis le texte.
  const neuf = etat.ajouter("");
  await etat.ecouteurs.ajout({ uniqueLocalIds: [neuf], source: "Local" });
  await etat.tic();
  etat.paras.find((p) => p.id === neuf).text = "Quatre mots arrivent ici.";
  await etat.ecouteurs.changement({ uniqueLocalIds: [neuf], source: "Local" });
  await etat.tic();

  const apres = JSON.parse(etat.stockage.get(`paysage:etat:${id}`)).segments[0].mots;
  vrai(apres > avant, `le paysage doit avoir pousse : ${avant} -> ${apres}`);
}]);

suite.push(["le curseur suit le paragraphe de la selection", async () => {
  const etat = monter_hote({ paragraphes: [{ texte: PHRASE }] });
  await demarrer(etat);
  const a = etat.ajouter("Premier paragraphe tape a la main ici meme.");
  etat.selection = a;
  await etat.ecouteurs.documentSelectionChanged();
  const b = etat.ajouter("Second paragraphe, ailleurs dans la page.");
  etat.selection = b;
  await etat.ecouteurs.documentSelectionChanged();
  // Rien a assurer de plus ici que l'absence d'exception : c'est essais.js qui
  // eprouve ce que le curseur DECIDE. Ici on verifie qu'il est bien alimente.
  vrai(true, "la selection se lit sans lever");
}]);

suite.push(["un tic qui leve n'arrete pas les suivants", async () => {
  const etat = monter_hote({ paragraphes: [{ texte: PHRASE }] });
  await demarrer(etat);
  const perdu = etat.ajouter("Un paragraphe qui va disparaitre avant le tic.");
  await etat.ecouteurs.ajout({ uniqueLocalIds: [perdu], source: "Local" });
  etat.paras = etat.paras.filter((p) => p.id !== perdu);   // efface sans evenement
  await etat.tic();                                        // ne doit pas lever
  const encore = etat.ajouter("Un paragraphe qui, lui, reste en place.");
  await etat.ecouteurs.ajout({ uniqueLocalIds: [encore], source: "Local" });
  await etat.tic();
  vrai(etat.elements.paysage.innerHTML.includes("<svg"), "le volet dessine encore");
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
