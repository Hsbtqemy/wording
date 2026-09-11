/**
 * Le generateur de Python, refait a l'identique.
 *
 * La decision 8 demande : meme document, meme graine, meme figure. La
 * grammaire, la composition et le message tirent trente-six nombres au sort
 * pour placer une branche, incliner un toit, trembler une lettre. Si les deux
 * langages ne tirent pas la MEME suite, les figures ne sont plus comparables —
 * et les quinze cents lignes de geometrie qui restent a porter deviennent
 * invisibles au verificateur de parite. On ne pourrait plus que les croire.
 *
 * C'est l'inverse du choix fait pour corpus.py, et pour une raison precise :
 * la, le generateur fabriquait des DONNEES DE TEST, qu'on pouvait simplement
 * ecrire dans le cahier. Ici il est DANS LE LIVRABLE — l'add-in tire au sort au
 * moment de dessiner. Le JavaScript a donc besoin d'un generateur deterministe
 * de toute facon ; la seule question etait de savoir s'il devait etre le meme.
 * Il ne coute qu'une centaine de lignes exactement specifiees, et il rend
 * verifiable tout ce qui vient apres.
 *
 * Portage de CPython 3.12 : MT19937 (Matsumoto & Nishimura, 1998) tel que
 * _randommodule.c l'utilise, plus les quatre methodes de Random dont le projet
 * se sert. Aucune autre : ni gauss, ni choice, ni shuffle — les compter avant
 * d'ecrire evite de porter ce dont personne n'a besoin.
 *
 * Ce qui n'est PAS porte, et pourquoi ca ne manque pas :
 *   - le germe par defaut (urandom) : ici une graine est toujours donnee ;
 *   - les graines non entieres (str, bytes) : le projet n'en passe jamais ;
 *   - getrandbits au-dela de 32 bits : randrange n'est appele que sur de
 *     petits nombres, et un k plus grand leve plutot que de mentir.
 */

const N = 624;
const M = 397;
const MATRICE_A = 0x9908b0df;
const MASQUE_HAUT = 0x80000000;   // bit de poids fort
const MASQUE_BAS = 0x7fffffff;    // les 31 bits de poids faible

export class Alea {
  /** @param {number} graine entier positif ou nul, entier sur au plus 53 bits */
  constructor(graine = 0) {
    this.mt = new Uint32Array(N);
    this.mti = N + 1;
    this.seed(graine);
  }

  /**
   * seed(n) pour un entier, comme random_seed() dans _randommodule.c : on prend
   * la valeur absolue, on la coupe en mots de 32 bits de poids faible d'abord,
   * et on passe le tout a init_by_array. Zero donne la cle [0].
   */
  seed(graine) {
    let n = Math.abs(graine);
    if (!Number.isSafeInteger(n)) {
      throw new RangeError(`graine hors des entiers surs : ${graine}`);
    }
    const cle = [];
    if (n === 0) {
      cle.push(0);
    } else {
      while (n > 0) {
        cle.push(n % 4294967296);
        n = Math.floor(n / 4294967296);
      }
    }
    this._init_par_tableau(cle);
  }

  _init_genrand(s) {
    const mt = this.mt;
    mt[0] = s >>> 0;
    for (let i = 1; i < N; i++) {
      const p = mt[i - 1] ^ (mt[i - 1] >>> 30);
      mt[i] = (Math.imul(1812433253, p) + i) >>> 0;
    }
    this.mti = N;
  }

  _init_par_tableau(cle) {
    this._init_genrand(19650218);
    const mt = this.mt;
    let i = 1;
    let j = 0;
    for (let k = Math.max(N, cle.length); k; k--) {
      const p = mt[i - 1] ^ (mt[i - 1] >>> 30);
      mt[i] = (((mt[i] ^ Math.imul(p, 1664525)) >>> 0) + cle[j] + j) >>> 0;
      i++; j++;
      if (i >= N) { mt[0] = mt[N - 1]; i = 1; }
      if (j >= cle.length) j = 0;
    }
    for (let k = N - 1; k; k--) {
      const p = mt[i - 1] ^ (mt[i - 1] >>> 30);
      mt[i] = (((mt[i] ^ Math.imul(p, 1566083941)) >>> 0) - i) >>> 0;
      i++;
      if (i >= N) { mt[0] = mt[N - 1]; i = 1; }
    }
    mt[0] = MASQUE_HAUT;          // garantit un etat non nul
  }

  /** genrand_uint32 : un mot de 32 bits, le seul endroit ou l'etat avance. */
  _mot() {
    const mt = this.mt;
    if (this.mti >= N) {
      let y;
      let k = 0;
      for (; k < N - M; k++) {
        y = ((mt[k] & MASQUE_HAUT) | (mt[k + 1] & MASQUE_BAS)) >>> 0;
        mt[k] = (mt[k + M] ^ (y >>> 1) ^ (y & 1 ? MATRICE_A : 0)) >>> 0;
      }
      for (; k < N - 1; k++) {
        y = ((mt[k] & MASQUE_HAUT) | (mt[k + 1] & MASQUE_BAS)) >>> 0;
        mt[k] = (mt[k + (M - N)] ^ (y >>> 1) ^ (y & 1 ? MATRICE_A : 0)) >>> 0;
      }
      y = ((mt[N - 1] & MASQUE_HAUT) | (mt[0] & MASQUE_BAS)) >>> 0;
      mt[N - 1] = (mt[M - 1] ^ (y >>> 1) ^ (y & 1 ? MATRICE_A : 0)) >>> 0;
      this.mti = 0;
    }
    let y = mt[this.mti++];
    y = (y ^ (y >>> 11)) >>> 0;
    y = (y ^ ((y << 7) & 0x9d2c5680)) >>> 0;
    y = (y ^ ((y << 15) & 0xefc60000)) >>> 0;
    y = (y ^ (y >>> 18)) >>> 0;
    return y >>> 0;
  }

  /**
   * random() : 53 bits de hasard, comme random_random().
   *
   *     (a >> 5) * 2^26 + (b >> 6)  puis  / 2^53
   *
   * Les deux produits intermediaires tiennent exactement dans un flottant 64
   * bits, donc le resultat est identique au bit pres des deux cotes — ce n'est
   * pas une approximation qu'on tolere, c'est la meme valeur.
   */
  random() {
    const a = this._mot() >>> 5;
    const b = this._mot() >>> 6;
    return (a * 67108864 + b) * (1.0 / 9007199254740992.0);
  }

  /** getrandbits(k), pour k de 1 a 32 — au-dela, personne n'en a besoin ici. */
  getrandbits(k) {
    if (k <= 0) throw new RangeError("getrandbits demande au moins un bit");
    if (k > 32) throw new RangeError("getrandbits au-dela de 32 bits n'est pas porte");
    return this._mot() >>> (32 - k);
  }

  /**
   * _randbelow_with_getrandbits : un entier de 0 a n-1, par rejet.
   *
   * Le rejet compte : il CONSOMME des mots. Prendre un modulo a la place
   * donnerait presque la meme distribution et une suite differente — donc des
   * figures differentes deux tirages plus loin, sans que rien n'ait l'air faux.
   */
  _endessous(n) {
    if (!n) return 0;
    const k = 32 - Math.clz32(n);          // n.bit_length()
    let r = this.getrandbits(k);
    while (r >= n) r = this.getrandbits(k);
    return r;
  }

  /** randrange(n) : la seule forme utilisee par le projet. */
  randrange(n) {
    if (!Number.isInteger(n) || n <= 0) {
      throw new RangeError(`randrange(${n}) : seule la forme a un argument positif est portee`);
    }
    return this._endessous(n);
  }

  /**
   * shuffle(x) : le melange de random.shuffle, en place, du dernier au premier.
   *
   * La decision 13 comptait quatre methodes — « ni gauss, ni choice, ni
   * shuffle » — a une epoque ou phrases.py n'etait pas du livrable. Le paquet
   * battu en a besoin. Meme algorithme que CPython : pour i de n-1 a 1, un j
   * tire par _randbelow(i + 1), puis l'echange. Tirer _randbelow(i) donnerait
   * un melange tout aussi plausible — celui de Sattolo — et une autre suite.
   */
  shuffle(x) {
    for (let i = x.length - 1; i > 0; i--) {
      const j = this._endessous(i + 1);
      const tmp = x[i];
      x[i] = x[j];
      x[j] = tmp;
    }
  }

  uniform(a, b) {
    return a + (b - a) * this.random();
  }

  expovariate(lambd = 1.0) {
    return -Math.log(1.0 - this.random()) / lambd;
  }
}

/** Raccourci : random.Random(graine). */
export function alea(graine = 0) {
  return new Alea(graine);
}
