/**
 * Le volet : le seul fichier qui parle a Office.js.
 *
 * Tout ce qui decide quoi que ce soit est ailleurs — guet.js pour lire ce qui a
 * change, paysage.js pour l'etat, magasin.js pour l'arbitrage entre les deux
 * copies, composition.js pour le dessin. Ici on ne fait que brancher, et c'est
 * voulu : ce fichier ne peut etre eprouve ni par la parite ni autrement que
 * contre un hote simule, donc moins il decide, mieux c'est.
 *
 * ⚠️ IL NE PASSE PLUS PAR LES EVENEMENTS DE PARAGRAPHE. Ils demandent WordApi
 * 1.6, et la machine a qui ce cadeau est destine est un Office LTSC 2021, gele
 * a sa version de sortie : elle ne les aura jamais. Le volet REGARDE donc, au
 * lieu d'etre prevenu — il relit body.text a chaque tic et le compare au
 * precedent. Mesure sur cette machine : 74 000 signes coutent 17 a 21 ms, le
 * prix d'un aller-retour et rien de plus, alors que dix-neuf paragraphes lus
 * objet par objet en coutent quarante-cinq. Le cout est dans les OBJETS
 * qu'Office.js fabrique, pas dans le texte.
 *
 * Ce qui reste necessaire tient maintenant en WordApi 1.1, c'est-a-dire
 * n'importe quel Word.
 *
 * ⚠️ CE QUE CE CHEMIN NE SAIT PLUS FAIRE : distinguer la frappe d'un CO-AUTEUR.
 * Les evenements portaient args.source, et le pont ignorait les modifications
 * distantes. Un instantane de texte ne dit pas qui a ecrit. Sur un document
 * partage, la frappe de quelqu'un d'autre fera donc pousser le paysage. C'est
 * assume : sans WordApi 1.6, l'information n'existe pas, et une these s'ecrit
 * seul.
 *
 * Ce qu'il porte, et qui n'est nulle part ailleurs :
 *
 *   - la cle du DOSSIER, tiree de l'URL du document (decision 11) ;
 *   - les deux magasins branches sur l'hote (decision 16) ;
 *   - la lecture du corps, et celle des styles quand la structure bouge ;
 *   - le tic de deux secondes (decision 12) ;
 *   - le profil, la question du prenom, et la nuit branchee sur le tic
 *     (decision 10) — ce qui en decide est dans nuit.js.
 */

import { Guet, INTERVALLE, compter_paragraphes } from "./guet.js";
import { Magasin, CLE_ETAT, REGLAGE_ID } from "./magasin.js";
import { graine_du_document } from "./grammaire.js";
import { vue_de_travail } from "./composition.js";
import { Veille, dans_le_ciel, mots_de_nuit, profil_de_l_adresse,
         faut_il_demander, signalement } from "./nuit.js";

let paysage = null;
let guet = null;
let magasin = null;
let graine = 1;
let dialogue = null;
let aEcrire = false;
// La nuit (decision 10) : le profil, et ce que la nuit en cours a revele.
let profil = { prenom: null, accord: null };
let veille = null;

/**
 * Combien de temps entre deux ecritures dans le dossier.
 *
 * ⚠️ localStorage EST SYNCHRONE. Le point 12 le dit depuis le debut : un
 * JSON.stringify de l'etat complet toutes les deux secondes bloque le fil qui
 * gere la frappe, et il prescrit une ecriture amortie a trente secondes. Le
 * portage ne l'avait jamais appliquee — on ecrivait a chaque tic ou quelque
 * chose avait pousse.
 *
 * Ce qu'on risque a attendre : trente secondes de pousse, et seulement si le
 * volet se ferme entre deux ecritures. La copie dans le document, elle, est
 * deja bien plus espacee.
 */
const AMORTI = 30000;

// La table des styles, un par paragraphe. Relue seulement quand le nombre de
// paragraphes change — voir lire_corps().
let styles = [];
// ⚠️ Une relecture qui a echoue laisse la table DECALEE, pas seulement vieille :
// la structure a bouge et la table ne l'a pas suivie. Sans ce drapeau, le compte
// de paragraphes correspondrait des le tic suivant et on ne la relirait plus
// jamais — les styles resteraient de travers jusqu'au prochain changement de
// structure, sans que rien ne le signale.
let styles_perimes = false;

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
// Le profil (decision 10)
// --------------------------------------------------------------------------
// Le prenom, quand il a ete DONNE en reponse : au dossier, et dans le document
// par la prochaine copie du paysage — jamais par une copie a lui seul.
const CLE_PRENOM = "paysage:prenom";
const REGLAGE_PRENOM = "paysage.prenom";
// La question a ete posee. Ignoree, elle n'est jamais reposee : ce serait un
// rappel.
const CLE_DEMANDE = "paysage:prenom:demande";

/**
 * Le profil : l'adresse d'abord — c'est celui qui offre qui l'a posee dans le
 * manifeste —, puis un prenom deja donne en reponse, au dossier, ou dans le
 * document s'il vient d'une autre machine. L'accord ne vient QUE de l'adresse :
 * il ne se demande pas, parce que le demander devoilerait une phrase.
 */
function profil_du_volet() {
  const lu = profil_de_l_adresse(window.location.href);
  if (lu.prenom) return lu;
  let prenom = null;
  try {
    prenom = localStorage.getItem(CLE_PRENOM);
  } catch { /* donnees de site bloquees : le document peut encore le rendre */ }
  const du_fichier = Office.context.document.settings.get(REGLAGE_PRENOM) || null;
  if (!prenom) {
    prenom = du_fichier;
  } else if (du_fichier !== prenom) {
    // set() sans saveAsync, comme l'identifiant : il partira avec la
    // prochaine copie, et ouvrir ne marque rien comme modifie.
    Office.context.document.settings.set(REGLAGE_PRENOM, prenom);
  }
  return { prenom, accord: lu.accord };
}

/**
 * La question du prenom, une fois (decision 10).
 *
 * ⚠️ SON TEXTE N'EST PAS ICI. Il est dans volet.html, et il est vide : c'est la
 * voix de celui qui offre, comme les phrases. Tant qu'il n'est pas ecrit, la
 * question se tait — voir faut_il_demander().
 *
 * Posee, elle est marquee AUSSITOT, pas a la reponse : ignoree, elle n'est
 * jamais reposee.
 */
function demander_prenom() {
  const forme = document.getElementById("demande");
  const question = document.getElementById("question");
  const champ = document.getElementById("prenom");
  if (!forme || !question || !champ) return;
  let deja = true;
  try {
    deja = localStorage.getItem(CLE_DEMANDE) === "1";
  } catch { /* sans memoire de l'avoir posee, on ne la pose pas */ }
  if (!faut_il_demander(profil, question.textContent || "", deja)) return;
  try {
    localStorage.setItem(CLE_DEMANDE, "1");
  } catch {
    return;
  }
  forme.hidden = false;
  const hors = document.getElementById("hors");
  // Un signe que l'alphabet ne dessine pas se signale A LA SAISIE, au lieu de
  // disparaitre en silence au trace.
  champ.addEventListener("input", () => {
    if (hors) hors.textContent = signalement(champ.value);
  });
  forme.addEventListener("submit", (e) => {
    if (e && e.preventDefault) e.preventDefault();
    repondre(champ.value);
    forme.hidden = true;
  });
}

/**
 * ⚠️ REPONDRE N'ECRIT PAS DANS LE DOCUMENT. Le prenom va au dossier, et au
 * reglage de la session par set() SANS saveAsync : il part avec la prochaine
 * copie du paysage, jamais dans une copie pour lui seul — Word demanderait
 * d'enregistrer un fichier ou l'on n'a rien tape.
 */
function repondre(texte) {
  const prenom = (texte || "").trim();
  if (!prenom) return;
  try {
    localStorage.setItem(CLE_PRENOM, prenom);
  } catch { /* il vivra la session, et partira quand meme avec la copie */ }
  Office.context.document.settings.set(REGLAGE_PRENOM, prenom);
  profil = { ...profil, prenom };
  if (veille) veille.profil = profil;
}

// --------------------------------------------------------------------------
// La lecture du document
// --------------------------------------------------------------------------
/**
 * Le corps entier, en UNE chaine.
 *
 * C'est la seule facon abordable de regarder un document a chaque tic :
 * body.text ne fabrique aucun objet intermediaire, et c'est la que se trouvait
 * tout le cout.
 */
async function lire_texte() {
  return Word.run(async (ctx) => {
    const corps = ctx.document.body;
    corps.load("text");
    await ctx.sync();
    return corps.text || "";
  });
}

/**
 * Les styles, un par paragraphe. C'est la lecture CHERE : un objet Office.js
 * par paragraphe, ~1,7 ms piece, soit deux secondes et demie sur une these.
 */
async function lire_styles() {
  return Word.run(async (ctx) => {
    const paras = ctx.document.body.paragraphs;
    paras.load("items/style");
    await ctx.sync();
    return paras.items.map((p) => p.style);
  });
}

/**
 * Le corps, et les styles SEULEMENT s'ils ont pu changer.
 *
 * Le style appartient au paragraphe ; taper dedans ne le change pas. Le nombre
 * de paragraphes se lit gratuitement dans la chaine qu'on vient de recevoir, et
 * il suffit a savoir si la table est perimee. La lecture chere ne part donc que
 * quand la structure bouge, jamais pendant qu'on ecrit.
 */
async function lire_corps() {
  const texte = await lire_texte();
  if (styles_perimes || compter_paragraphes(texte) !== guet.paragraphes) {
    try {
      styles = await lire_styles();
      styles_perimes = false;
    } catch {
      // Une table qu'on n'a pas pu relire vaut mieux qu'un tic qui leve. Mais
      // on RETIENT qu'elle est perimee : sinon le compte correspondrait des le
      // tic suivant et elle ne serait plus jamais relue.
      styles_perimes = true;
    }
  }
  return texte;
}

/**
 * Le jour de l'annee, base zero, et l'heure : ce que la palette attend.
 *
 * Date.now() et non new Date() : c'est l'horloge que les essais savent figer,
 * et la fenetre de nuit ne s'eprouve pas autrement.
 */
function horloge(d = new Date(Date.now())) {
  const debut = Date.UTC(d.getFullYear(), 0, 1);
  const jour = Math.floor((Date.UTC(d.getFullYear(), d.getMonth(), d.getDate())
    - debut) / 86400000);
  return { jour, heure: d.getHours() };
}

// --------------------------------------------------------------------------
// Le rendu
// --------------------------------------------------------------------------
function dessiner() {
  const hote = document.getElementById("paysage");
  if (!hote || !paysage) return;
  const plants = paysage.etat().plants;
  const travail = vue_de_travail(plants, graine, hote.clientWidth || 340,
                                 hote.clientHeight || 430);
  // Le message de nuit, s'il y en a un, dans le ciel de la meme vue.
  const svg = dans_le_ciel(travail, veille);
  // Poser innerHTML fait reparser tout le document SVG. Sur un paysage mur
  // c'est le poste le plus cher du tic, et il est le plus souvent inutile.
  if (svg === dernier_svg) return;
  dernier_svg = svg;
  hote.innerHTML = svg;
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
let dernier_rangement = 0;      // 0 : la premiere ecriture part tout de suite
// Le dernier SVG pose dans le volet. Le point 12 veut que les plants acheves
// soient rasterises une fois et jamais retouches ; en attendant, on evite au
// moins de RE-POSER un dessin identique. Le vegetal ne change de forme que
// quatre fois sur toute la vie d'un plant, donc la plupart des tics
// reconstruisaient le meme document pour rien.
let dernier_svg = "";

async function tic() {
  if (occupe) return;             // un tic en retard ne doit pas en doubler un autre
  occupe = true;
  const maintenant = Date.now();
  const ecoule = maintenant - dernier;
  dernier = maintenant;
  try {
    const faits = guet.relever(await lire_corps(), styles);
    if (faits.length) {
      const instant = new Date(maintenant);
      const { jour, heure } = horloge(instant);
      const verdicts = guet.nourrir(paysage, faits, jour, heure,
                                    guet.debit(faits, ecoule));
      // La nuit lit les memes verdicts, et les mots de nuit que le paysage vient
      // de compter — a la MEME heure que lui, sinon un paragraphe a cheval sur
      // 2 h serait compte par l'un et pas par l'autre.
      veille.suivre(verdicts, mots_de_nuit(paysage), instant);
      dessiner();
      aEcrire = true;
    }
    // ⚠️ AMORTI, et non a chaque tic. aEcrire reste vrai tant que l'ecriture
    // n'a pas eu lieu : rien ne se perd, tout attend.
    if (aEcrire && maintenant - dernier_rangement >= AMORTI) {
      ranger();
      dernier_rangement = maintenant;
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
  //
  // 1.1 ET NON 1.6. Depuis que le volet regarde au lieu d'etre prevenu, il n'a
  // plus besoin que de body.text et body.paragraphs — autant dire n'importe
  // quel Word. C'etait tout le but : la machine a qui ce cadeau est destine ne
  // depassera jamais 1.3, et la version precedente s'y ouvrait pour dire
  // qu'elle ne pouvait rien faire.
  if (!Office.context.requirements.isSetSupported("WordApi", "1.1")) {
    dire("Ce Word est trop ancien pour que le paysage suive l'ecriture. "
       + "Tout le reste est deja la.");
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
  guet = new Guet();
  profil = profil_du_volet();

  // Le premier instantane : tout ce qui est deja la est acquis (decision 11).
  // rattacher() passe par le registre, donc rouvrir le fichier ne fait rien
  // pousser — c'est l'empreinte qui traverse les sessions.
  //
  // Les styles sont lus SANS CONDITION ici : le guet n'a pas encore de compte
  // de paragraphes a comparer, et l'ouverture est le seul moment ou la lecture
  // chere est permise — elle est hors du tic, donc hors du budget de 100 ms.
  try {
    const texte = await lire_texte();
    try {
      styles = await lire_styles();
    } catch {
      styles = [];
    }
    const { jour, heure } = horloge();
    paysage.rattacher(guet.amorcer(texte, styles), jour, heure);
    ranger();
  } catch (e) {
    console.warn("paysage : premier instantane manque", e);
  }

  // La nuit part des mots de nuit deja la : le capital de depart est acquis,
  // il ne revele rien (decision 11).
  veille = new Veille(profil, mots_de_nuit(paysage));
  demander_prenom();

  dessiner();
  setInterval(tic, INTERVALLE);
  window.addEventListener("resize", dessiner);
});
