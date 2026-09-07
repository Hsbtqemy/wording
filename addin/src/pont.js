/**
 * Le pont entre Word et le paysage.
 *
 * CE FICHIER NE CONNAIT PAS OFFICE.JS. Il recoit des evenements deja traduits
 * et decide quoi appeler sur Paysage ; volet.js fait le branchement. La
 * separation n'est pas de la coquetterie : c'est la seule partie de l'add-in
 * qui ne peut PAS etre verifiee par parite — il n'y a pas de Python en face —
 * et c'est aussi celle qui porte la decision 2. Isolee, elle s'eprouve contre
 * un Word simule, avec les suites d'evenements que le vrai Word produit.
 *
 * Trois choses que la documentation d'Office.js a apprises, et qui ont chacune
 * change la conception :
 *
 * 1. LES IDENTIFIANTS DE PARAGRAPHE CHANGENT A CHAQUE SESSION. uniqueLocalId
 *    est un GUID « qui differe d'une session et d'un co-auteur a l'autre ». On
 *    ne peut donc rien persister avec. Le registre de la decision 3 est
 *    heureusement textuel — c'est l'empreinte qui traverse les sessions, pas
 *    l'identifiant. Le miroir id -> texte tenu ici est de session, et il est
 *    reconstruit au scan d'ouverture.
 *
 * 2. IL N'Y A PAS D'EVENEMENT DE SELECTION SUR Word.Document. Le curseur de la
 *    decision 2 doit passer par l'API commune,
 *    Office.EventType.DocumentSelectionChanged. Or celle-la se declenche aussi
 *    QUAND ON TAPE, puisque taper deplace le point d'insertion. Appeler
 *    quitter() a chaque declenchement rouvrirait exactement ce que la decision
 *    2 ferme : chaque frappe deviendrait une visite neuve, donc une reprise, et
 *    une premiere redaction ne ferait plus jamais pousser la forme.
 *
 *    Le curseur n'est donc pas « la selection a bouge » mais « la selection a
 *    change de PARAGRAPHE ». C'est signaler_curseur(id) qui l'arbitre, et lui
 *    seul appelle quitter().
 *
 * 3. UN EVENEMENT PEUT VENIR D'AILLEURS. args.source vaut « Local » ou
 *    « Remote » — une modification d'un co-auteur. Ce n'est pas la personne qui
 *    ecrit, et sa frappe ne doit pas faire pousser le paysage de quelqu'un
 *    d'autre. Les evenements distants sont ignores.
 */

import { SEUIL_COLLAGE } from "./paysage.js";

/** Combien de temps entre deux vidages de la file (decision 12). */
export const INTERVALLE = 2000;

/**
 * Le pont.
 *
 * @param paysage  une instance de Paysage
 * @param lire     async (ids) -> [{id, texte, style}] — resout des identifiants
 *                 en texte. C'est le seul contact avec Word, et il est injecte.
 * @param horloge  () -> {jour, heure}, pour que les essais puissent mentir
 */
export class Pont {
  constructor(paysage, lire, horloge = null) {
    this.paysage = paysage;
    this.lire = lire;
    this.horloge = horloge || (() => {
      const d = new Date();
      // Le jour de l'annee, base zero : c'est ce que la palette attend.
      const debut = Date.UTC(d.getFullYear(), 0, 1);
      const jour = Math.floor((Date.UTC(d.getFullYear(), d.getMonth(), d.getDate())
        - debut) / 86400000);
      return { jour, heure: d.getHours() };
    });

    // Le miroir : identifiant de session -> dernier texte connu. Sans lui,
    // retoucher() n'a pas d'« ancien » a donner, et une reprise ne peut pas se
    // distinguer d'une ecriture.
    this.miroir = new Map();
    // Les identifiants vus depuis le dernier vidage, dans l'ordre d'arrivee.
    this.enAttente = new Map();     // id -> "ajout" | "changement"
    this.curseur = null;            // le paragraphe ou se trouve la selection
    this.verdicts = [];             // ce que le dernier vidage a produit
    // Les paragraphes qu'on a vus naitre VIDES dans cette session. Eux seuls
    // echappent a la reconnaissance du registre : un paragraphe qu'on tape
    // passe par tous ses etats intermediaires, et « Il faut donc admettre » a
    // toutes les chances d'avoir deja commence un autre paragraphe. Sans cette
    // memoire, le troisieme paragraphe d'une page en francais est declare
    // connu et disparait.
    this.naissances = new Set();
  }

  // ------------------------------------------------------------ evenements
  /**
   * Un evenement de Word. `type` vaut "ajout", "changement" ou "suppression".
   *
   * Un ajout n'ecrase jamais un changement deja en file pour le meme
   * paragraphe : le premier verdit compte, et c'est l'ajout qui fait naitre le
   * paragraphe.
   */
  signaler(type, ids, distant = false) {
    if (distant) return 0;          // la frappe d'un co-auteur n'est pas la notre
    let retenus = 0;
    for (const id of ids) {
      if (type === "suppression") {
        // Rien a faire : la decision 3 rend une suppression gratuite, et le
        // registre garde l'empreinte. Le miroir, lui, peut oublier.
        this.miroir.delete(id);
        this.naissances.delete(id);
        this.enAttente.delete(id);
        continue;
      }
      if (!this.enAttente.has(id)) this.enAttente.set(id, type);
      retenus += 1;
    }
    return retenus;
  }

  /**
   * La selection a bouge. On ne quitte le paragraphe que si elle a change de
   * PARAGRAPHE — voir le point 2 de l'en-tete.
   *
   * @returns true si le curseur a reellement quitte un paragraphe
   */
  signaler_curseur(id) {
    if (id === this.curseur) return false;
    // On quitte l'ancien, quel qu'il soit — y compris quand la selection sort
    // du document (id nul) : fermer la fenetre, c'est aussi quitter.
    if (this.curseur !== null) this.paysage.quitter();
    this.curseur = id;
    return true;
  }

  // ---------------------------------------------------------------- vidage
  /**
   * Vide la file : resout les textes, puis nourrit le paysage.
   *
   * Le debit sert la decision 4. `mots_par_intervalle` est le total des mots
   * arrives DANS CET INTERVALLE, pas la longueur du paragraphe courant : un
   * collage de douze chapitres arrive d'un bloc, et c'est le bloc qu'il faut
   * mesurer. Un seul paragraphe de 400 mots tape a la main n'existe pas ;
   * quatre cents mots arrives en deux secondes, si.
   */
  async vider(ecoule = INTERVALLE) {
    if (!this.enAttente.size) return [];
    const attente = this.enAttente;
    this.enAttente = new Map();

    const lus = await this.lire([...attente.keys()]);
    const { jour, heure } = this.horloge();

    // Le debit d'abord, sur tout ce qui est arrive : il faut le connaitre AVANT
    // d'absorber le premier paragraphe.
    //
    // Et RAMENE A L'INTERVALLE, pas compte par vidage. SEUIL_COLLAGE vaut
    // quinze mots par deux secondes, soit 450 mots par minute — un debit que
    // personne n'atteint a la main. Mais si un vidage a pris dix secondes
    // (machine chargee, volet masque, Word occupe), quinze mots tapes
    // honnetement arrivent d'un coup et deviennent une greffe. On aurait
    // converti l'ecriture de quelqu'un en collage sans que rien ne le signale.
    let mots = 0;
    for (const p of lus) {
      const ancien = this.miroir.get(p.id);
      const n = compter_mots(p.texte);
      mots += ancien === undefined ? n : Math.max(0, n - compter_mots(ancien));
    }
    const debit = mots * INTERVALLE / Math.max(ecoule, 1);

    const verdicts = [];
    for (const p of lus) {
      const ancien = this.miroir.get(p.id);
      if (ancien === undefined) {
        // Inconnu de cette session. absorber() tranchera : le registre
        // d'empreintes passe avant tout, donc un paragraphe deja connu du
        // paysage ne fera rien — c'est ce qui rend un deplacement gratuit.
        const ne = this.naissances.has(p.id);
        const v = this.paysage.absorber(p.texte, p.style, debit, jour, heure, ne);
        verdicts.push({ id: p.id, verdict: v, texte: p.texte });
        // Ni le vide ni une citation n'entrent au miroir : le vide parce qu'il
        // n'est pas encore un paragraphe et qu'il le deviendra, la citation
        // parce qu'elle ne compte jamais.
        if (v === "vide") {
          // Ne le mirroite pas, mais RETIENT qu'il est ne ici, sous le
          // curseur. C'est la seule chose que le registre ne peut pas deviner.
          this.naissances.add(p.id);
        } else {
          this.naissances.delete(p.id);
          if (v !== "ignoree") this.miroir.set(p.id, p.texte);
        }
        if (v === "ecriture") this.curseur = p.id;
      } else if (ancien !== p.texte) {
        const v = this.paysage.retoucher(ancien, p.texte, jour, heure, false);
        verdicts.push({ id: p.id, verdict: v, texte: p.texte });
        this.miroir.set(p.id, p.texte);
      }
    }
    this.verdicts = verdicts;
    return verdicts;
  }

  // -------------------------------------------------------------- ouverture
  /**
   * Le scan complet de la decision 11 : tout ce qui est deja la est acquis.
   *
   * On passe par rattacher(), pas par absorber() : un document existant n'est
   * pas un collage geant, c'est le capital de depart. Personne n'a a
   * recommencer sa these pour que le cadeau ait un sens.
   */
  rattacher(paragraphes) {
    const { jour, heure } = this.horloge();
    this.paysage.rattacher(paragraphes.map((p) => [p.texte, p.style]), jour, heure);
    for (const p of paragraphes) {
      if (p.id !== undefined && p.id !== null) this.miroir.set(p.id, p.texte);
    }
  }
}

/**
 * Les mots d'un paragraphe, pour le seul calcul du debit.
 *
 * en_mots() de traits.js serait plus juste, mais il coute une expression
 * reguliere Unicode par paragraphe, et le debit ne sert qu'a comparer a
 * SEUIL_COLLAGE — quinze mots par intervalle de deux secondes, soit 450 mots
 * par minute. A cette echelle, decouper aux blancs suffit et ne se trompe
 * jamais de cote.
 */
function compter_mots(texte) {
  const t = texte.trim();
  return t ? t.split(/\s+/u).length : 0;
}

export { compter_mots, SEUIL_COLLAGE };
