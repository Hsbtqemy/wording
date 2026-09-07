/**
 * Le volet : le seul fichier qui parle a Office.js.
 *
 * Tout ce qui decide quoi que ce soit est ailleurs — pont.js pour la lecture
 * des evenements, paysage.js pour l'etat, composition.js pour le dessin. Ici on
 * ne fait que brancher, et c'est voulu : ce fichier ne peut etre eprouve ni par
 * la parite ni par les essais du pont, donc moins il decide, mieux c'est.
 *
 * Ce qu'il porte quand meme, et qui n'est nulle part ailleurs :
 *
 *   - le rattachement du document a SON paysage (decision 11) ;
 *   - la degradation quand WordApi 1.6 manque ;
 *   - le tic de deux secondes (decision 12).
 */

import { Paysage } from "./paysage.js";
import { Pont, INTERVALLE } from "./pont.js";
import { graine_du_document } from "./grammaire.js";
import { vue_de_travail } from "./composition.js";

const CLE_INDEX = "paysage:index";        // dossier -> identifiant
const CLE_ETAT = "paysage:etat:";         // + identifiant
const REGLAGE = "paysage.identifiant";

let paysage = null;
let pont = null;
let graine = 1;
let dialogue = null;
let aEcrire = false;

// --------------------------------------------------------------------------
// Le perimetre (decision 11)
// --------------------------------------------------------------------------
/**
 * Le paysage appartient au DOSSIER, pas au fichier.
 *
 * L'identifiant est tire une fois et recopie dans les Settings de chaque
 * document du dossier. C'est LUI qui fait autorite, pas le nom du dossier :
 * deux theses rangees dans deux dossiers nommes « Chapitres » partageraient
 * sinon le meme paysage. Le dossier ne sert qu'a rattacher un document neuf a
 * un paysage existant.
 */
function cle_du_dossier() {
  const url = (Office.context.document.url || "").replace(/\\/g, "/");
  const coupe = url.lastIndexOf("/");
  return coupe > 0 ? url.slice(0, coupe) : url;
}

function lire_index() {
  try {
    return JSON.parse(localStorage.getItem(CLE_INDEX) || "{}") || {};
  } catch {
    return {};
  }
}

function tirer_identifiant() {
  // Pas de crypto.randomUUID partout ; deux nombres aleatoires suffisent, la
  // valeur n'a besoin que d'etre unique sur cette machine.
  return `p${Date.now().toString(36)}${Math.floor(Math.random() * 1e9).toString(36)}`;
}

function identifiant_du_document() {
  const dossier = cle_du_dossier();
  let id = Office.context.document.settings.get(REGLAGE);
  if (!id) {
    // Ce document ne connait pas encore son paysage. S'il y en a un pour ce
    // dossier, il le rejoint ; sinon on en ouvre un.
    const index = lire_index();
    id = index[dossier] || tirer_identifiant();
    Office.context.document.settings.set(REGLAGE, id);
    Office.context.document.settings.saveAsync();
  }
  const index = lire_index();
  index[dossier] = id;
  try {
    localStorage.setItem(CLE_INDEX, JSON.stringify(index));
  } catch { /* le stockage peut etre plein ou refuse : ce n'est pas fatal */ }
  return { id, dossier };
}

function ranger() {
  if (!paysage) return;
  try {
    localStorage.setItem(CLE_ETAT + paysage.identifiant, paysage.serialiser());
  } catch {
    // Rien a faire de mieux : un paysage qu'on ne peut pas ranger continue de
    // vivre dans la session. Mieux vaut ca qu'une exception dans un tic.
  }
}

// --------------------------------------------------------------------------
// La lecture du document
// --------------------------------------------------------------------------
/**
 * Resout des identifiants de paragraphe en texte.
 *
 * Un identifiant peut avoir disparu entre l'evenement et le vidage : le
 * paragraphe a ete supprime, annule, ou fusionne. On tente le lot d'un coup,
 * et si le lot echoue on reprend un par un — un paragraphe disparu ne doit pas
 * emporter les onze autres.
 */
async function lire(ids) {
  try {
    return await Word.run(async (ctx) => {
      const charges = ids.map((id) => {
        const p = ctx.document.getParagraphByUniqueLocalId(id);
        p.load("text,style");
        return { id, p };
      });
      await ctx.sync();
      return charges.map(({ id, p }) => ({ id, texte: p.text, style: p.style }));
    });
  } catch {
    const sortie = [];
    for (const id of ids) {
      try {
        // eslint-disable-next-line no-await-in-loop
        const un = await Word.run(async (ctx) => {
          const p = ctx.document.getParagraphByUniqueLocalId(id);
          p.load("text,style");
          await ctx.sync();
          return { id, texte: p.text, style: p.style };
        });
        sortie.push(un);
      } catch { /* ce paragraphe n'existe plus : c'est une reponse, pas une panne */ }
    }
    return sortie;
  }
}

/** Le scan complet a l'ouverture (decision 11). */
async function scanner() {
  return Word.run(async (ctx) => {
    const paras = ctx.document.body.paragraphs;
    paras.load("items/text,items/style,items/uniqueLocalId");
    await ctx.sync();
    return paras.items.map((p) => ({
      id: p.uniqueLocalId, texte: p.text, style: p.style,
    }));
  });
}

// --------------------------------------------------------------------------
// Le curseur (decision 2)
// --------------------------------------------------------------------------
/**
 * La selection a bouge. On demande a Word DANS QUEL PARAGRAPHE elle est, et
 * c'est le pont qui decide si cela vaut un depart.
 *
 * DocumentSelectionChanged se declenche aussi quand on tape, puisque taper
 * deplace le point d'insertion. Sans ce detour par l'identite du paragraphe,
 * chaque frappe serait une visite neuve — voir l'en-tete de pont.js.
 */
async function sur_selection() {
  try {
    await Word.run(async (ctx) => {
      const p = ctx.document.getSelection().paragraphs.getFirstOrNullObject();
      p.load("uniqueLocalId,isNullObject");
      await ctx.sync();
      pont.signaler_curseur(p.isNullObject ? null : p.uniqueLocalId);
    });
  } catch {
    // Une selection qu'on n'arrive pas a lire ne doit pas casser la frappe en
    // cours. On prefere ne rien quitter plutot que quitter a tort.
  }
}

// --------------------------------------------------------------------------
// Le rendu
// --------------------------------------------------------------------------
function dessiner() {
  const hote = document.getElementById("paysage");
  if (!hote || !paysage) return;
  const plants = paysage.etat().plants;
  hote.innerHTML = vue_de_travail(plants, graine, hote.clientWidth || 340,
                                  hote.clientHeight || 430);
}

function dire(texte) {
  const hote = document.getElementById("mot");
  if (hote) hote.textContent = texte || "";
}

// --------------------------------------------------------------------------
// Le tic (decision 12)
// --------------------------------------------------------------------------
let dernier = Date.now();
let occupe = false;

async function tic() {
  if (occupe) return;             // un tic en retard ne doit pas en doubler un autre
  occupe = true;
  const maintenant = Date.now();
  const ecoule = maintenant - dernier;
  dernier = maintenant;
  try {
    const verdicts = await pont.vider(ecoule);
    if (verdicts.length) {
      dessiner();
      aEcrire = true;
    }
    if (aEcrire) {
      ranger();
      aEcrire = false;
    }
  } catch (e) {
    // Un tic qui leve ne doit pas arreter les suivants : le volet doit
    // survivre a un document qui bouge sous ses pieds.
    console.warn("paysage : tic manque", e);
  } finally {
    occupe = false;
  }
}

// --------------------------------------------------------------------------
// L'apercu (decision 14 : deux vues, pas une echelle)
// --------------------------------------------------------------------------
// Le volet Word est une colonne etroite et haute : une bande horizontale y est
// le pire format possible. La vue d'ensemble s'ouvre donc en dialogue, qui est
// large — et c'est un dezoom qu'on FAIT, pas un dezoom qu'on subit.
function ouvrir_apercu() {
  const url = new URL("apercu.html", window.location.href).href;
  Office.context.ui.displayDialogAsync(
    url, { height: 62, width: 78, displayInIframe: true },
    (res) => {
      if (res.status !== Office.AsyncResultStatus.Succeeded) return;
      dialogue = res.value;
      dialogue.addEventHandler(Office.EventType.DialogEventReceived, () => {
        dialogue = null;
      });
      // Le dialogue partage l'origine, donc localStorage : il relit l'etat
      // tout seul. On ne lui passe que la cle.
      dialogue.addEventHandler(Office.EventType.DialogMessageReceived, () => {
        dialogue.messageChild(JSON.stringify({
          cle: CLE_ETAT + paysage.identifiant, graine,
        }));
      });
    },
  );
}

// --------------------------------------------------------------------------
// Le demarrage
// --------------------------------------------------------------------------
Office.onReady(async (info) => {
  const bouton = document.getElementById("apercu");
  if (bouton) bouton.addEventListener("click", ouvrir_apercu);

  if (info.host !== Office.HostType.Word) {
    dire("Ce volet ne pousse que dans Word.");
    return;
  }

  // On verifie la version ICI et pas dans le manifeste : une contrainte non
  // satisfaite dans le manifeste rend l'add-in invisible, sans un mot.
  if (!Office.context.requirements.isSetSupported("WordApi", "1.6")) {
    dire("Il manque une version de Word un peu plus recente pour que le "
       + "paysage suive l'ecriture. Tout le reste est deja la.");
    return;
  }

  const { id, dossier } = identifiant_du_document();
  paysage = Paysage.depuis(localStorage.getItem(CLE_ETAT + id));
  paysage.identifiant = id;
  paysage.cle_dossier = dossier;
  graine = graine_du_document(id);
  pont = new Pont(paysage, lire);

  // Le scan complet : tout ce qui est deja la est acquis (decision 11).
  // rattacher() passe par le registre, donc rouvrir le fichier ne fait rien
  // pousser — c'est l'empreinte qui traverse les sessions, pas l'identifiant
  // de paragraphe, qui lui change a chaque ouverture.
  try {
    pont.rattacher(await scanner());
    ranger();
  } catch (e) {
    console.warn("paysage : scan d'ouverture manque", e);
  }

  await Word.run(async (ctx) => {
    ctx.document.onParagraphAdded.add(async (args) => {
      pont.signaler("ajout", args.uniqueLocalIds, args.source === "Remote");
    });
    ctx.document.onParagraphChanged.add(async (args) => {
      pont.signaler("changement", args.uniqueLocalIds, args.source === "Remote");
    });
    ctx.document.onParagraphDeleted.add(async (args) => {
      pont.signaler("suppression", args.uniqueLocalIds, args.source === "Remote");
    });
    await ctx.sync();
  });

  Office.context.document.addHandlerAsync(
    Office.EventType.DocumentSelectionChanged, sur_selection,
  );

  dessiner();
  setInterval(tic, INTERVALLE);
  window.addEventListener("resize", dessiner);
});
