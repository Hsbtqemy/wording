/**
 * Le magasin : ou vit le paysage, et lequel des deux fait autorite.
 *
 * DEUX MAGASINS, PAS UN.
 *
 *   LE DOSSIER — localStorage, une entree par paysage. C'est le magasin de
 *   travail. Le point 11 veut que le paysage appartienne au DOSSIER et pas au
 *   fichier ; un fichier ne peut pas porter ce qui est commun a plusieurs
 *   fichiers, donc il faut un magasin au-dessus des fichiers. Ecrit a chaque
 *   tic : synchrone, gratuit, sans effet sur le document.
 *
 *   LE FICHIER — Office.context.document.settings, range DANS le .docx. Une
 *   copie de secours, et elle voyage avec le document : sauvegarde, cle USB,
 *   autre machine, autre hebergeur.
 *
 * POURQUOI LA COPIE. Le localStorage est indexe par ORIGINE. Tant que le volet
 * est servi par GitHub Pages, le jardin depend de cette adresse : en changer,
 * passer a un domaine propre, ou simplement vider les donnees de site, le
 * perdrait. Pour un cadeau cense durer le temps d'une these, c'est la mauvaise
 * dependance — et c'etait la derniere qui restait a un tiers.
 *
 * Mesure : une these de 143 000 mots fait 78 Ko d'etat serialise (37 de
 * registre, 41 de segments). Dans un .docx, ce n'est rien.
 *
 * CE FICHIER NE CONNAIT PAS OFFICE.JS, pas plus que pont.js. Les deux magasins
 * sont injectes, chacun reduit a lire/ecrire, pour que la regle d'arbitrage —
 * la seule chose ici qui DECIDE — s'eprouve sans hote du tout.
 */

import { Paysage } from "./paysage.js";

/** Le dossier : l'index dossier -> identifiant, puis un etat par identifiant. */
export const CLE_INDEX = "paysage:index";
export const CLE_ETAT = "paysage:etat:";

/** Le fichier : deux reglages, ecrits ensemble par le meme saveAsync. */
export const REGLAGE_ID = "paysage.identifiant";
export const REGLAGE_ETAT = "paysage.etat";

/**
 * Au plus une copie toutes les cinq minutes.
 *
 * Ce qu'on risque a attendre : cinq minutes de pousse, et seulement si le
 * dossier disparait entre-temps — la copie n'est relue que la. Ce qu'on risque
 * a ne pas attendre : l'etat reecrit dans le document toutes les deux secondes,
 * dix-huit cents fois par heure, chacune marquant le document modifie et
 * relancant la synchronisation de qui le stocke en ligne.
 */
export const ATTENTE_COPIE = 5 * 60 * 1000;

/**
 * Au-dela, on renonce plutot que de demander a Word d'avaler n'importe quoi.
 *
 * Six fois le pire cas mesure (78 Ko pour 143 000 mots), soit de quoi tenir
 * bien au-dela d'une these. La vraie garde reste le refus de saveAsync, qui est
 * signale et definitif ; celle-ci evite seulement d'aller le chercher.
 */
export const TAILLE_MAX = 512 * 1024;

/**
 * Lequel des deux fait autorite : celui qui a le plus d'empreintes.
 *
 * Le point 1 dit que rien ne recule jamais — le registre ne fait que grandir,
 * y compris quand on reprend un paragraphe, puisqu'un texte retouche est un
 * texte de plus. La comparaison est donc monotone et ne peut pas se tromper de
 * sens. Ni horodatage, ni numero de revision : les deux mentent des qu'une
 * horloge est fausse ou qu'un fichier est restaure depuis une sauvegarde.
 *
 * Une copie illisible, tronquee, ou d'une autre version repart vide — c'est
 * Paysage.depuis qui le garantit — donc a zero empreinte : elle perd toute
 * seule, sans qu'on ait a la valider en plus.
 *
 * A egalite, le dossier gagne. C'est le magasin de travail, et il porte la cle
 * de dossier a jour ; basculer pour un contenu identique ne rapporterait rien.
 */
export function choisir(du_dossier, du_fichier) {
  const a = Paysage.depuis(du_dossier);
  const b = Paysage.depuis(du_fichier);
  const n_dossier = a.registre.size;
  const n_fichier = b.registre.size;
  if (n_fichier > n_dossier) {
    return { paysage: b, source: "fichier", n_dossier, n_fichier };
  }
  return {
    paysage: a, source: n_dossier ? "dossier" : "neuf", n_dossier, n_fichier,
  };
}

/**
 * Un identifiant de paysage.
 *
 * Pas de crypto.randomUUID partout ; deux nombres suffisent, la valeur n'a
 * besoin que d'etre unique sur cette machine.
 */
export function tirer_identifiant() {
  return `p${Date.now().toString(36)}${Math.floor(Math.random() * 1e9).toString(36)}`;
}

export class Magasin {
  /**
   * @param dossier    { lire(cle) -> string|null, ecrire(cle, valeur) }
   * @param fichier    { lire(nom) -> string|undefined,
   *                     ecrire(nom, valeur) -> Promise }
   * @param maintenant () -> ms, pour que les essais puissent avancer l'horloge
   */
  constructor(dossier, fichier, maintenant = () => Date.now()) {
    this.dossier = dossier;
    this.fichier = fichier;
    this.maintenant = maintenant;
    // Ce que le fichier porte DEJA : la copie ne se refait que si elle a pris
    // du retard, jamais pour reposer la meme chose.
    this.copiees = 0;
    this.derniere = null;           // quand la derniere copie est partie
    this.refuse = false;            // le fichier a dit non : on n'insiste plus
  }

  // ------------------------------------------------------------------ index
  _index() {
    let d;
    try {
      d = JSON.parse(this.dossier.lire(CLE_INDEX) || "{}");
    } catch {
      return {};
    }
    // Meme prudence que dans Paysage.depuis : "[]" et "3" sont du JSON valide,
    // et on ecrirait dedans sans rien casser ni rien retenir.
    return d && typeof d === "object" && !Array.isArray(d) ? d : {};
  }

  /**
   * L'identifiant du paysage de ce dossier, et l'index tenu a jour.
   *
   * Ordre : ce que le document porte, sinon ce que le dossier connait, sinon un
   * neuf. C'est le document qui fait autorite (point 11) — deux theses rangees
   * dans deux dossiers nommes « Chapitres » partageraient sinon le meme
   * paysage. Le dossier ne sert qu'a rattacher un document NEUF a un paysage
   * existant.
   *
   * @param dossier la cle du dossier
   * @param connu   l'identifiant que le document porte deja, ou rien
   */
  identifiant(dossier, connu) {
    const index = this._index();
    const id = connu || index[dossier] || tirer_identifiant();
    index[dossier] = id;
    try {
      this.dossier.ecrire(CLE_INDEX, JSON.stringify(index));
    } catch { /* plein ou refuse : ce n'est pas fatal, l'identifiant tient */ }
    return id;
  }

  // -------------------------------------------------------------- ouverture
  /** Relit les deux copies et garde la plus fournie. */
  charger(id) {
    const choix = choisir(this.dossier.lire(CLE_ETAT + id),
                          this.fichier.lire(REGLAGE_ETAT));
    this.copiees = choix.n_fichier;
    return choix;
  }

  // -------------------------------------------------------------- ecritures
  /** Le dossier. A chaque tic, et sans consequence si ca echoue. */
  ranger(paysage) {
    try {
      this.dossier.ecrire(CLE_ETAT + paysage.identifiant, paysage.serialiser());
    } catch {
      // Rien a faire de mieux : un paysage qu'on ne peut pas ranger continue de
      // vivre dans la session. Mieux vaut ca qu'une exception dans un tic.
    }
  }

  /**
   * Le fichier. Rare, et jamais pour rien.
   *
   * Trois retenues, dans cet ordre :
   *
   *   1. RIEN N'A POUSSE — on ne repose pas la meme chose. Un tic peut rendre
   *      des verdicts sans une empreinte de plus : un paragraphe duplique, un
   *      texte deja connu retape, une annulation.
   *   2. C'EST TROP TOT — au plus une copie par ATTENTE_COPIE. La premiere de
   *      la session passe tout de suite, pour qu'une session interrompue ait
   *      quand meme laisse quelque chose.
   *   3. LE FICHIER A REFUSE — on n'insiste pas. Une limite de taille ne
   *      bougera pas d'ici la fin de la session ; redemander toutes les cinq
   *      minutes ne ferait que remplir la console.
   *
   * ⚠️ saveAsync MARQUE LE DOCUMENT COMME MODIFIE, et c'est pourquoi la copie
   * n'a pas lieu au demarrage. Ouvrir un document, regarder le volet et fermer
   * ne doit pas faire apparaitre « Voulez-vous enregistrer les modifications ? »
   * — le cadeau n'a pas a salir un fichier ou personne n'a ecrit. Le reglage
   * d'identite attend d'ailleurs le meme moment : il est pose des l'ouverture,
   * mais c'est ce saveAsync-la qui l'ecrit. Quand le paysage pousse, la personne
   * a tape : le document est deja modifie de son fait.
   *
   * @returns true si la copie est reellement partie
   */
  async copier(paysage) {
    if (this.refuse) return false;
    const n = paysage.registre.size;
    if (n <= this.copiees) return false;
    const t = this.maintenant();
    if (this.derniere !== null && t - this.derniere < ATTENTE_COPIE) return false;
    const brut = paysage.serialiser();
    if (brut.length > TAILLE_MAX) {
      this.refuse = true;
      console.warn(`paysage : ${brut.length} octets, trop pour un reglage`);
      return false;
    }
    // L'horodatage AVANT l'attente, pas apres : deux appels qui se recouvrent
    // passeraient sinon l'etranglement tous les deux, puisque le second lirait
    // un `derniere` que le premier n'a pas encore pose. Le tic ne peut pas se
    // doubler aujourd'hui, mais rien dans cette classe ne l'exige de l'appelant.
    // Rien a perdre en cas d'echec : on renonce alors pour la session entiere.
    this.derniere = t;
    try {
      await this.fichier.ecrire(REGLAGE_ETAT, brut);
    } catch (e) {
      // Silencieux cote volet : un cadeau ne previent pas qu'il a mal dormi.
      this.refuse = true;
      console.warn("paysage : le document n'accepte pas la copie", e);
      return false;
    }
    // Et le compte APRES : on ne declare copie que ce qui est parti.
    this.copiees = n;
    return true;
  }
}
