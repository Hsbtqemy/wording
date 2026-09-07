/**
 * Le guet : lire ce qui a change en comparant deux instantanes.
 *
 * Portage de jardin/guet.py. La specification est la-bas, et c'est elle qui
 * fait foi ; ce fichier ne doit rien decider de plus.
 *
 * POURQUOI CE MODULE EXISTE
 *
 * Les evenements de paragraphe demandent WordApi 1.6, et la machine a qui ce
 * cadeau est destine est un Office LTSC 2021 gele a sa version de sortie : elle
 * ne les aura jamais. Mesure sur cette machine : relire le document objet par
 * objet coute ~1,7 ms PAR PARAGRAPHE, soit deux secondes et demie sur une
 * these, vingt-cinq fois le budget d'un tic. Mais le corps entier rendu en UNE
 * chaine coute 17 a 21 ms quelle que soit sa taille, parce qu'aucun objet
 * intermediaire n'est fabrique. On regarde donc, au lieu d'etre prevenu.
 *
 * ET C'EST CE QUI REGLE LE POINT 14. Le premier vrai document ouvert avec le
 * volet faisait trente-cinq pages et UN SEUL paragraphe : 0 marque de
 * paragraphe, 1119 sauts de ligne. Le paysage y aurait vu une empreinte pour
 * 74 000 signes et n'aurait jamais pousse. Le guet decoupe sur tous les
 * separateurs, et retrouve les lignes que la personne a ecrites quelle que soit
 * la touche employee.
 *
 * ⚠️ CE FICHIER NE CONNAIT PAS OFFICE.JS, comme pont.js. Il recoit une chaine
 * et une table de styles ; volet.js va les chercher. C'est ce qui permet a la
 * parite de le couvrir — le premier morceau du cablage Word a l'etre.
 */

// Word joint ses paragraphes par un retour chariot dans body.text, et ses
// sauts de ligne (Maj+Entree) par une tabulation verticale. Elle s'ecrit
// \u000B en toutes lettres et jamais en clair : un caractere de controle dans
// une source est invisible en relecture et ne survit pas au premier
// copier-coller — la panne a ete faite deux fois avant d'etre ecrite ici.
//
// LES DEUX NIVEAUX SONT DISTINGUES, et ce n'est pas de la coquetterie : le
// style appartient au PARAGRAPHE. Decouper d'abord sur le retour chariot donne
// les paragraphes de Word, donc l'echelle a laquelle les styles se lisent ;
// decouper ensuite chaque paragraphe donne les lignes de la personne, qui est
// l'unite du paysage. Une ligne herite du style de son paragraphe, exactement.
export const SEPARATEUR_PARAGRAPHE = "\r";
export const SEPARATEURS_LIGNE = ["\u000B", "\n"];

/**
 * Combien de releves sans un changement avant qu'une visite soit close.
 *
 * Voir jardin/guet.py pour le raisonnement complet. En deux lignes : changer de
 * ligne ferme deja la visite tout seul, puisque _actif n'a qu'une case, et
 * tripoter ne pousse pas puisque la branche frappe ne compte que les mots
 * AJOUTES. Ce silence ne protege donc pas l'extension mais LA MATURITE — sans
 * lui, revenir sur une ligne une semaine plus tard reste la meme visite,
 * plant.reprises ne monte jamais, et l'element cesse de murir.
 *
 * Borne basse mesuree sur la machine cible : 57 % des releves voient un
 * changement en ecriture active, 24 % en frappe distraite. Soixante releves
 * calmes ne peuvent pas arriver pendant qu'on ecrit. La borne haute — deux
 * minutes — reste un jugement, a confirmer au banc.
 */
export const SILENCE = 60;

/**
 * Combien de temps entre deux releves (decision 12). Le pont a la meme, pour le
 * chemin des evenements ; elle est redite ici parce que le guet doit pouvoir se
 * specifier sans lui.
 */
export const INTERVALLE = 2000;

/**
 * Les mots d'une ligne, pour le SEUL calcul du debit.
 *
 * en_mots() serait plus juste mais coute une expression reguliere Unicode par
 * ligne, et le debit ne sert qu'a comparer a SEUIL_COLLAGE — quinze mots par
 * intervalle de deux secondes, soit 450 mots par minute. A cette echelle,
 * decouper aux blancs suffit et ne se trompe jamais de cote.
 */
export function compter_mots(texte) {
  if (!texte) return 0;
  const t = texte.trim();
  return t ? t.split(/\s+/u).length : 0;
}

/**
 * Les lignes du corps, et le paragraphe d'ou chacune vient.
 *
 * Rend {lignes, appartenance}, de meme longueur : appartenance[k] est l'indice
 * du paragraphe Word qui contient la ligne k.
 */
export function decouper_marque(texte) {
  if (!texte) return { lignes: [], appartenance: [] };
  const lignes = [];
  const appartenance = [];
  const paragraphes = texte.split(SEPARATEUR_PARAGRAPHE);
  for (let rang = 0; rang < paragraphes.length; rang++) {
    let morceaux = [paragraphes[rang]];
    for (const s of SEPARATEURS_LIGNE) {
      const suivants = [];
      for (const m of morceaux) suivants.push(...m.split(s));
      morceaux = suivants;
    }
    for (const m of morceaux) {
      lignes.push(m);
      appartenance.push(rang);
    }
  }
  return { lignes, appartenance };
}

/** Les seules lignes, quand l'appartenance n'interesse pas l'appelant. */
export function decouper(texte) {
  return decouper_marque(texte).lignes;
}

/**
 * Combien de paragraphes Word voit dans ce corps.
 *
 * Sert a savoir quand la table des styles est PERIMEE, et ce compte-la est
 * gratuit : il se lit dans la chaine qu'on vient deja de recevoir. Taper dans
 * un paragraphe ne le change pas ; en ajouter ou en retirer un, si.
 */
export function compter_paragraphes(texte) {
  if (!texte) return 0;
  return texte.split(SEPARATEUR_PARAGRAPHE).length;
}

/**
 * Ce qui a bouge entre deux instantanes.
 *
 * Rend une liste de mouvements [genre, i, j], dans l'ordre du nouvel
 * instantane : "gardee", "retouchee", "nee" (i vaut null), "disparue" (j vaut
 * null).
 *
 * CE QUI PROTEGE L'INVARIANT CARDINAL : L'APPARIEMENT PAR TEXTE EGAL.
 * Identifier les lignes par leur RANG est la faute a ne pas commettre —
 * inserer une ligne au milieu decalerait toutes les suivantes, et une insertion
 * se lirait comme une pluie de retouches, donc de l'extension prise pour de la
 * maturite. On apparie d'abord ce qui est EGAL : une ligne qui n'a pas bouge,
 * ou qui a seulement change de place, retrouve son identifiant et ne rend aucun
 * verdict — ce que le point 3 promet d'un deplacement.
 *
 * Le rognage des bouts communs, lui, n'est qu'une acceleration : le retirer ne
 * change aucun verdict, seulement le travail. La premiere version de ce
 * commentaire disait le contraire, et les mutations l'ont dementie.
 */
export function rapprocher(anciennes, nouvelles) {
  const a = anciennes.length;
  const b = nouvelles.length;

  let tete = 0;
  while (tete < a && tete < b && anciennes[tete] === nouvelles[tete]) tete += 1;

  let queue = 0;
  while (queue < a - tete && queue < b - tete
         && anciennes[a - 1 - queue] === nouvelles[b - 1 - queue]) queue += 1;

  const fenetre_a = [];
  for (let i = tete; i < a - queue; i++) fenetre_a.push(i);
  const fenetre_b = [];
  for (let j = tete; j < b - queue; j++) fenetre_b.push(j);

  // 1. Les lignes egales, ou qu'elles soient dans la fenetre : deplacees.
  //
  // ⚠️ Une Map et non un objet. Les cles sont du TEXTE DE THESE, donc
  // n'importe quoi : une ligne qui vaut « __proto__ » ou « constructor »
  // trouverait une entree heritee sur un objet nu et apparierait des lignes qui
  // n'existent pas. Python n'a pas ce piege, et le portage ligne a ligne
  // l'aurait rapporte sans le voir.
  const par_texte = new Map();
  for (const i of fenetre_a) {
    if (!par_texte.has(anciennes[i])) par_texte.set(anciennes[i], []);
    par_texte.get(anciennes[i]).push(i);
  }
  const deplacees = new Map();          // j -> i
  const pris = new Set();
  for (const j of fenetre_b) {
    const libres = par_texte.get(nouvelles[j]);
    while (libres && libres.length) {
      const i = libres.shift();
      if (!pris.has(i)) {
        deplacees.set(j, i);
        pris.add(i);
        break;
      }
    }
  }

  // 2. Le reste, par rang.
  const restants_a = fenetre_a.filter((i) => !pris.has(i));
  const restants_b = fenetre_b.filter((j) => !deplacees.has(j));
  const couples = new Map();            // j -> i
  const commun = Math.min(restants_a.length, restants_b.length);
  for (let k = 0; k < commun; k++) couples.set(restants_b[k], restants_a[k]);
  const disparues = restants_a.slice(restants_b.length);

  const mouvements = [];
  for (let k = 0; k < tete; k++) mouvements.push(["gardee", k, k]);
  for (const j of fenetre_b) {
    if (deplacees.has(j)) mouvements.push(["gardee", deplacees.get(j), j]);
    else if (couples.has(j)) mouvements.push(["retouchee", couples.get(j), j]);
    else mouvements.push(["nee", null, j]);
  }
  for (let k = 0; k < queue; k++) {
    mouvements.push(["gardee", a - queue + k, b - queue + k]);
  }
  for (const i of disparues) mouvements.push(["disparue", i, null]);

  return mouvements;
}

/**
 * Le style de la ligne k, pris sur son paragraphe.
 *
 * Tolerant par construction : une table absente, trop courte, ou decalee d'un
 * releve rend « Normal » plutot que de lever. Le style se rafraichit au releve
 * suivant, alors qu'une exception dans un tic arreterait tout.
 */
function _style(styles, appartenance, k) {
  if (!styles || !styles.length || k >= appartenance.length) return "Normal";
  const rang = appartenance[k];
  return rang < styles.length ? styles[rang] : "Normal";
}

export class Guet {
  /**
   * LES IDENTIFIANTS SONT FABRIQUES ICI, et c'est ce qui permet au pont de ne
   * pas changer d'une ligne : sur ses vingt usages d'identifiant, tous sont des
   * cles de Map ou une egalite. Il n'en lit jamais la forme.
   */
  constructor(silence = SILENCE) {
    this.lignes = [];       // le dernier instantane
    this.ids = [];          // un identifiant par ligne, meme longueur
    this._suivant = 0;
    this.silence = silence;
    this.visitee = null;
    this.calme = 0;
    this.paragraphes = 0;
    // Les lignes arrivees en GREFFE, pour que retoucher() sache les convertir
    // (point 4). Le pont ne l'a jamais su, et la conversion n'arrivait donc
    // jamais dans l'add-in.
    this.greffes = new Set();
  }

  _neuf() {
    this._suivant += 1;
    return `g${this._suivant}`;
  }

  /**
   * Le premier instantane, qui ne fait RIEN pousser.
   *
   * Decision 11 : ce qui est deja la est un capital de depart, pas une pousse.
   * Sans ce depart separe, ouvrir le volet sur une these de mille cinq cents
   * lignes les declarerait toutes NEES d'un coup.
   *
   * Rend des couples [texte, style], ce que paysage.rattacher() attend.
   */
  amorcer(texte, styles = null) {
    const { lignes, appartenance } = decouper_marque(texte);
    this.lignes = lignes;
    this.ids = lignes.map(() => this._neuf());
    this.paragraphes = compter_paragraphes(texte);
    return lignes.map((l, k) => [l, _style(styles, appartenance, k)]);
  }

  /**
   * Les mots arrives DANS CE RELEVE, ramenes a l'intervalle.
   *
   * Decision 4 : c'est le bloc qu'il faut mesurer, pas la ligne. Un collage de
   * douze chapitres arrive d'un coup ; une ligne de 400 mots tapee a la main
   * n'existe pas, mais 400 mots arrives en deux secondes, si.
   *
   * ⚠️ LE PLANCHER EST L'INTERVALLE, PAS 1. La normalisation doit corriger un
   * releve EN RETARD, jamais un releve en avance : divise par cinq
   * millisecondes, quatre mots tapes deviendraient un debit de mille six cents
   * et passeraient pour un collage. Elle ne peut donc que reduire le debit,
   * jamais l'amplifier.
   */
  debit(faits, ecoule = INTERVALLE) {
    let mots = 0;
    for (const f of faits) {
      if (f.type === "nee") mots += compter_mots(f.texte);
      else if (f.type === "retouchee") {
        mots += Math.max(0, compter_mots(f.texte) - compter_mots(f.ancien));
      }
    }
    return mots * INTERVALLE / Math.max(ecoule, INTERVALLE);
  }

  /**
   * Donne au paysage ce que le releve a vu, et rend les verdicts.
   *
   * C'est ici que le guet remplace le pont, et les trois decisions qu'il
   * portait sont reprises telles quelles.
   *
   * UNE LIGNE NEE VIDE QUI SE REMPLIT EST UNE ECRITURE, pas une reprise. Word
   * cree une ligne vide a chaque Entree, et le guet la voit naitre ; elle
   * arrive donc en « retouchee » avec un ancien texte vide. Sans cette
   * conversion, absorber() n'aurait jamais pose _actif, retoucher() tomberait
   * dans la branche « nouvelle visite », et LE PREMIER MOT TAPE SUR CHAQUE
   * LIGNE NEUVE compterait comme une reprise.
   *
   * UNE SUPPRESSION EST GRATUITE (point 3) : le registre garde l'empreinte.
   *
   * UN COLLAGE RETRAVAILLE SE CONVERTIT (point 4), et c'est neuf. Le pont
   * passait toujours etait_greffe = false, donc cette branche n'etait JAMAIS
   * atteinte dans l'add-in.
   */
  nourrir(paysage, faits, jour = 0, heure = 14, debit = 0.0) {
    const verdicts = [];
    for (const f of faits) {
      const genre = f.type;
      if (genre === "visite_finie") {
        paysage.quitter();
        verdicts.push({ id: f.id, verdict: "visite finie" });
        continue;
      }
      if (genre === "disparue") {
        this.greffes.delete(f.id);
        verdicts.push({ id: f.id, verdict: "disparue" });
        continue;
      }
      let v;
      if (genre === "nee") {
        v = paysage.absorber(f.texte, f.style, debit, jour, heure, false);
      } else if (!compter_mots(f.ancien)) {
        v = paysage.absorber(f.texte, f.style, debit, jour, heure, true);
      } else {
        v = paysage.retoucher(f.ancien, f.texte, jour, heure,
                              this.greffes.has(f.id));
      }
      if (v === "greffe") this.greffes.add(f.id);
      else if (v === "conversion" || v === "ecriture") this.greffes.delete(f.id);
      verdicts.push({ id: f.id, verdict: v });
    }
    return verdicts;
  }

  /**
   * Compare le corps a ce qu'on avait vu, et rend ce qui a bouge.
   *
   * Les lignes gardees ne rendent rien, et c'est tout l'interet : sur une these
   * de mille cinq cents lignes, un tic n'en signale qu'une ou deux.
   */
  relever(texte, styles = null) {
    const { lignes: nouvelles, appartenance } = decouper_marque(texte);
    const mouvements = rapprocher(this.lignes, nouvelles);

    const ids = new Array(nouvelles.length).fill(null);
    const faits = [];
    for (const [genre, i, j] of mouvements) {
      if (genre === "gardee") {
        ids[j] = this.ids[i];
      } else if (genre === "retouchee") {
        ids[j] = this.ids[i];
        faits.push({ type: "retouchee", id: this.ids[i], texte: nouvelles[j],
                     ancien: this.lignes[i],
                     style: _style(styles, appartenance, j) });
      } else if (genre === "nee") {
        ids[j] = this._neuf();
        faits.push({ type: "nee", id: ids[j], texte: nouvelles[j],
                     ancien: null, style: _style(styles, appartenance, j) });
      } else {
        faits.push({ type: "disparue", id: this.ids[i], texte: null,
                     ancien: this.lignes[i], style: "" });
      }
    }

    this.lignes = nouvelles;
    this.ids = ids;
    this.paragraphes = compter_paragraphes(texte);

    // La visite. Elle se ferme d'elle-meme quand on ecrit ailleurs — _actif
    // n'a qu'une case — donc il ne reste ici qu'a fermer celle qu'on a
    // ABANDONNEE sans rien toucher d'autre.
    const remuees = faits.filter((f) => f.type !== "disparue").map((f) => f.id);
    if (remuees.length) {
      this.visitee = remuees[remuees.length - 1];
      this.calme = 0;
    } else if (this.visitee !== null) {
      this.calme += 1;
      if (this.calme >= this.silence) {
        faits.push({ type: "visite_finie", id: this.visitee, texte: null,
                     ancien: null, style: "" });
        this.visitee = null;
        this.calme = 0;
      }
    }

    return faits;
  }
}
