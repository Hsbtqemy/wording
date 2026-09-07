/**
 * BLAKE2s (RFC 7693), la partie qu'il nous faut : pas de cle, un condensat
 * court, une seule passe.
 *
 * Pourquoi il a fallu l'ecrire. `graine_du_document()` tire la graine du NOM du
 * document, et cette graine determine la figure entiere — decision 8 : meme
 * document, meme graine, meme figure. Contrairement a l'empreinte d'un
 * paragraphe, elle ne peut donc PAS diverger d'un langage a l'autre : le meme
 * document donnerait deux paysages, et la planche cesserait d'etre une preuve
 * de ce que l'add-in affiche.
 *
 * Le navigateur n'offre pas de hachage synchrone (SubtleCrypto est
 * asynchrone), et le projet ne prend aucune dependance. Restait a le porter.
 * C'est cent lignes entierement specifiees, et ca ne tourne qu'une fois par
 * document.
 *
 * Verifie contre les vecteurs de la RFC et contre hashlib, dans le cahier de
 * parite.
 */

// Les huit mots d'initialisation, ceux de SHA-256 : la partie fractionnaire des
// racines carrees des huit premiers nombres premiers.
const IV = new Uint32Array([
  0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
  0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
]);

// Les dix permutations du message. BLAKE2s fait dix tours, pas douze : les
// deux dernieres lignes de BLAKE2b n'existent pas ici.
const SIGMA = [
  [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
  [14, 10, 4, 8, 9, 15, 13, 6, 1, 12, 0, 2, 11, 7, 5, 3],
  [11, 8, 12, 0, 5, 2, 15, 13, 10, 14, 3, 6, 7, 1, 9, 4],
  [7, 9, 3, 1, 13, 12, 11, 14, 2, 6, 5, 10, 4, 0, 15, 8],
  [9, 0, 5, 7, 2, 4, 10, 15, 14, 1, 11, 12, 6, 8, 3, 13],
  [2, 12, 6, 10, 0, 11, 8, 3, 4, 13, 7, 5, 15, 14, 1, 9],
  [12, 5, 1, 15, 14, 13, 4, 10, 0, 7, 6, 3, 9, 2, 8, 11],
  [13, 11, 7, 14, 12, 1, 3, 9, 5, 0, 15, 4, 8, 6, 2, 10],
  [6, 15, 14, 9, 11, 3, 0, 8, 12, 2, 13, 7, 1, 4, 10, 5],
  [10, 2, 8, 4, 7, 6, 1, 5, 15, 11, 9, 14, 3, 12, 13, 0],
];

const encodeur = new TextEncoder();

function rotr(x, n) {
  return ((x >>> n) | (x << (32 - n))) >>> 0;
}

/**
 * Un bloc de 64 octets melange l'etat.
 *
 * `t` est le nombre total d'octets deja absorbes, `dernier` marque le bloc
 * final. Les deux comptent : sans eux, deux messages differents dont l'un est
 * le prefixe de l'autre se condenseraient pareil.
 */
function comprimer(h, bloc, t, dernier) {
  const v = new Uint32Array(16);
  for (let i = 0; i < 8; i++) v[i] = h[i];
  for (let i = 0; i < 8; i++) v[i + 8] = IV[i];
  v[12] = (v[12] ^ (t >>> 0)) >>> 0;
  v[13] = (v[13] ^ Math.floor(t / 4294967296)) >>> 0;
  if (dernier) v[14] = (~v[14]) >>> 0;

  const m = new Uint32Array(16);
  for (let i = 0; i < 16; i++) {
    m[i] = (bloc[i * 4] | (bloc[i * 4 + 1] << 8)
          | (bloc[i * 4 + 2] << 16) | (bloc[i * 4 + 3] << 24)) >>> 0;
  }

  const G = (a, b, c, d, x, y) => {
    v[a] = (v[a] + v[b] + x) >>> 0;
    v[d] = rotr((v[d] ^ v[a]) >>> 0, 16);
    v[c] = (v[c] + v[d]) >>> 0;
    v[b] = rotr((v[b] ^ v[c]) >>> 0, 12);
    v[a] = (v[a] + v[b] + y) >>> 0;
    v[d] = rotr((v[d] ^ v[a]) >>> 0, 8);
    v[c] = (v[c] + v[d]) >>> 0;
    v[b] = rotr((v[b] ^ v[c]) >>> 0, 7);
  };

  for (let r = 0; r < 10; r++) {
    const s = SIGMA[r];
    G(0, 4, 8, 12, m[s[0]], m[s[1]]);
    G(1, 5, 9, 13, m[s[2]], m[s[3]]);
    G(2, 6, 10, 14, m[s[4]], m[s[5]]);
    G(3, 7, 11, 15, m[s[6]], m[s[7]]);
    G(0, 5, 10, 15, m[s[8]], m[s[9]]);
    G(1, 6, 11, 12, m[s[10]], m[s[11]]);
    G(2, 7, 8, 13, m[s[12]], m[s[13]]);
    G(3, 4, 9, 14, m[s[14]], m[s[15]]);
  }

  for (let i = 0; i < 8; i++) h[i] = (h[i] ^ v[i] ^ v[i + 8]) >>> 0;
}

/**
 * @param {Uint8Array} octets
 * @param {number} taille longueur du condensat, de 1 a 32 octets
 * @returns {Uint8Array}
 */
export function blake2s(octets, taille = 32) {
  if (taille < 1 || taille > 32) {
    throw new RangeError(`blake2s : taille de condensat hors bornes (${taille})`);
  }
  const h = new Uint32Array(IV);
  // Bloc de parametres : longueur du condensat, longueur de cle (nulle ici),
  // profondeur d'arbre et eventail a 1 — le mode sequentiel.
  h[0] = (h[0] ^ 0x01010000 ^ taille) >>> 0;

  const bloc = new Uint8Array(64);
  let compte = 0;
  let i = 0;
  // Tous les blocs pleins SAUF le dernier : BLAKE2 veut que le bloc final
  // passe par le drapeau, meme quand il tombe juste sur 64 octets.
  while (octets.length - i > 64) {
    bloc.set(octets.subarray(i, i + 64));
    compte += 64;
    comprimer(h, bloc, compte, false);
    i += 64;
  }
  bloc.fill(0);
  const reste = octets.length - i;
  bloc.set(octets.subarray(i, i + reste));
  compte += reste;
  comprimer(h, bloc, compte, true);

  const sortie = new Uint8Array(taille);
  for (let k = 0; k < taille; k++) {
    sortie[k] = (h[k >> 2] >>> (8 * (k & 3))) & 0xff;
  }
  return sortie;
}

/** Le condensat en hexadecimal, comme hashlib.blake2s(...).hexdigest(). */
export function blake2s_hex(texte, taille = 32) {
  const d = blake2s(encodeur.encode(texte), taille);
  let s = "";
  for (const o of d) s += o.toString(16).padStart(2, "0");
  return s;
}
