/**
 * Le volet : le seul fichier qui parle a Office.js.
 *
 * Tout ce qui decide quoi que ce soit est ailleurs — pont.js pour la lecture
 * des evenements, paysage.js pour l'etat, composition.js pour le dessin. Ici on
 * ne fait que brancher, et c'est voulu : ce fichier ne peut etre eprouve ni par
 * la parite ni par les essais du pont, donc moins il decide, mieux c'est.
 * magasin.js a ete detache pour la meme raison — l'arbitrage entre les deux
 * copies du paysage est une decision, et une decision doit pouvoir s'eprouver
 * sans hote.
 *
 * Ce qu'il porte quand meme, et qui n'est nulle part ailleurs :
 *
 *   - la cle du DOSSIER, tiree de l'URL du document (decision 11) ;
 *   - les deux magasins branches sur l'hote (decision 16) ;
 *   - la degradation quand WordApi 1.6 manque ;
 *   - le tic de deux secondes (decision 12).
 */

import { Pont, INTERVALLE } from "./pont.js";
import { Magasin, CLE_ETAT, REGLAGE_ID } from "./magasin.js";
import { graine_du_document } from "./grammaire.js";
import { vue_de_travail } from "./composition.js";

let paysage = null;
let pont = null;
let magasin = null;
let graine = 1;
let dialogue = null;
let aEcrire = false;

// --------------------------------------------------------------------------
// Les deux magasins (decision 16)
// --------------------------------------------------------------------------
// Tout ce qui arbitre entre eux est dans magasin.js ; ici on ne fait que les
// brancher sur l'hote, chacun reduit a lire et ecrire.
const DOSSIER = {
  lire: (cle) => localStorage.getItem(cle),
  ecrire: (cle, valeur) => localStorage.setItem(cle, valeur),
};

/**
 * Le fichier.
 *
 * set() ne fait que garder le reglage en memoire pour la session ; c'est
 * saveAsync qui l'ecrit dans le .docx — et qui marque le document comme
 * modifie. Voir Magasin.copier : c'est pour ca qu'il n'est appele que quand le
 * paysage a pousse, jamais a l'ouverture.
 */
const FICHIER = {
  lire: (nom) => Office.context.document.settings.get(nom),
  ecrire: (nom, valeur) => new Promise((tenu, rompu) => {
    Office.context.document.settings.set(nom, valeur);
    Office.context.document.settings.saveAsync((res) => {
      if (res && res.status === Office.AsyncResultStatus.Succeeded) tenu();
      else rompu((res && res.error) || new Error("saveAsync a refuse"));
    });
  }),
};

// --------------------------------------------------------------------------
// Le perimetre (decision 11)
// --------------------------------------------------------------------------
/**
 * Le paysage appartient au DOSSIER, pas au fichier — d'ou cette cle.
 *
 * Elle ne fait pourtant pas autorite : c'est l'identifiant range dans les
 * Settings du document qui la fait, sans quoi deux theses posees dans deux
 * dossiers nommes « Chapitres » partageraient le meme paysage. Le dossier ne
 * sert qu'a rattacher un document NEUF a un paysage existant. Cet ordre-la est
 * dans Magasin.identifiant, avec le reste de ce qui decide.
 */
function cle_du_dossier() {
  const url = (Office.context.document.url || "").replace(/\\/g, "/");
  const coupe = url.lastIndexOf("/");
  return coupe > 0 ? url.slice(0, coupe) : url;
}

function identifiant_du_document() {
  const dossier = cle_du_dossier();
  const connu = Office.context.document.settings.get(REGLAGE_ID);
  const id = magasin.identifiant(dossier, connu);
  // set() sans saveAsync : le reglage vit dans la session et partira avec la
  // premiere copie, quand le paysage aura pousse. Enregistrer ici marquerait
  // comme modifie un document que la personne n'a fait qu'ouvrir.
  if (id !== connu) Office.context.document.settings.set(REGLAGE_ID, id);
  return { id, dossier };
}

function ranger() {
  if (paysage) magasin.ranger(paysage);
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

/**
 * Ce que cet hote sait faire, en clair.
 *
 * ECHAFAUDAGE, et il porte une date. Le refus « il manque une version de Word »
 * ne disait pas CE QUI manque, et sur une machine qui ne peut pas etre mise a
 * jour — un Office LTSC est gele a sa version de sortie pour cinq ans — c'est
 * la seule question qui compte. Ces lignes disparaissent le jour ou le volet
 * saura se passer des evenements de paragraphe.
 *
 * On monte jusqu'a 1.8 sans s'arreter au premier refus : les jeux d'API sont
 * emboites, mais rien n'oblige un hote a le rester, et supposer l'emboitement
 * ici reviendrait a mesurer sa propre hypothese.
 */
async function signalement() {
  const morceaux = [];
  try {
    let haut = "aucun";
    for (const v of ["1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7", "1.8"]) {
      if (Office.context.requirements.isSetSupported("WordApi", v)) haut = v;
    }
    morceaux.push(`WordApi ${haut}`);
  } catch {
    morceaux.push("WordApi indeterminable");
  }
  try {
    const d = Office.context.diagnostics;
    if (d) morceaux.push(`${d.host} ${d.platform} ${d.version}`);
  } catch { /* diagnostics n'est pas partout : son absence n'est pas une panne */ }

  // Le second chiffre, et il decide autant que le premier. Prive d'evenements,
  // le seul repli est que le tic REGARDE au lieu d'etre prevenu — ce qui ne
  // tient que dans le budget de 100 ms par tic de la decision 12.
  //
  // ⚠️ LA PREMIERE MESURE PRISE ICI DISAIT 216 ms POUR DIX-HUIT PARAGRAPHES.
  // Cinq mille signes ne coutent pas un cinquieme de seconde a traverser un
  // pont : c'etait le PREMIER Word.run de la session, qui monte tout le canal.
  // Un cout d'allumage, pas un cout de lecture — et le tic ne tourne jamais a
  // froid. Mesurer une fois, c'etait mesurer la mauvaise chose.
  //
  // On TOUCHE le texte de chaque paragraphe, on ne compte pas les objets : le
  // cout est dans le passage du texte par le pont, et un compteur qui ne lit
  // rien mesurerait un aller-retour vide.
  const relire_tout = () => Word.run(async (ctx) => {
    const paras = ctx.document.body.paragraphs;
    paras.load("items/text,items/style");
    await ctx.sync();
    let total = 0;
    for (const p of paras.items) total += p.text.length;
    return { n: paras.items.length, signes: total };
  });

  try {
    const t0 = Date.now();
    const { n, signes } = await relire_tout();
    const froid = Date.now() - t0;
    morceaux.push(`${n} paragraphes / ${Math.round(signes / 1000)} k signes`);
    const chaud = [];
    for (let i = 0; i < 4; i++) {
      const t = Date.now();
      // eslint-disable-next-line no-await-in-loop
      await relire_tout();
      chaud.push(Date.now() - t);
    }
    morceaux.push(`tout : froid ${froid} puis ${chaud.join(" ")} ms`);
  } catch {
    morceaux.push("relecture complete impossible");
  }

  // Et le chiffre qui decide vraiment : le paragraphe SOUS LE CURSEUR, seul.
  // C'est ce que le guet lirait a chaque tic, pas le document entier — la
  // decision 2 dit deja que la croissance se produit la ou est le curseur.
  //
  // On charge `text`, pas `uniqueLocalId` : c'est justement la propriete qui
  // demande 1.6 et qui manque ici. sur_selection() la charge encore, et devra
  // changer si le guet est retenu.
  try {
    const t = [];
    for (let i = 0; i < 4; i++) {
      const t0 = Date.now();
      // eslint-disable-next-line no-await-in-loop
      await Word.run(async (ctx) => {
        const p = ctx.document.getSelection().paragraphs.getFirstOrNullObject();
        p.load("text,style");
        await ctx.sync();
        return p.isNullObject ? 0 : p.text.length;
      });
      t.push(Date.now() - t0);
    }
    morceaux.push(`curseur seul : ${t.join(" ")} ms`);
  } catch {
    morceaux.push("curseur illisible");
  }
  return morceaux.join(" · ");
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
      // Et la copie dans le document, qui se retient elle-meme : au plus une
      // toutes les cinq minutes, et jamais si rien n'a pousse.
      await magasin.copier(paysage);
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
       + "paysage suive l'ecriture. Tout le reste est deja la."
       + `\n\n${await signalement()}`);
    return;
  }

  magasin = new Magasin(DOSSIER, FICHIER);
  const { id, dossier } = identifiant_du_document();
  const choix = magasin.charger(id);
  paysage = choix.paysage;
  if (choix.source === "fichier") {
    // Le seul cas qui merite une trace : le dossier ne l'avait plus. C'est
    // exactement ce que la copie du point 16 existe pour rattraper.
    console.info(`paysage : rendu par le document, ${choix.n_fichier} empreintes`);
  }
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
