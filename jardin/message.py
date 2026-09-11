"""
Le message de nuit.

Reprend grammaire6.py et regle ses deux defauts.

POINT OUVERT 4 — les lettres restaient une police. Deux correctifs, dont un
seul compte vraiment.

Le premier : chaque trait devient une POLYLIGNE a longueurs inegales, comme les
branches du vegetal ou aucun segment n'a la longueur du precedent. Ca aide,
mais peu — la planche le montre.

Le second, qui est le vrai : on deplace les SOMMETS de la lettre, pas ses
traits. Secouer les extremites (v6) ou onduler entre elles laisse intacts les
angles — l'apex du M, la pointe du A, la diagonale du N tombent toujours sur
les memes points de la grille 3x5, et l'oeil lit une fonte tremblee. Une fois
les sommets deplaces, les angles eux-memes changent d'un tirage a l'autre. Le
decalage est partage par tous les traits qui se rejoignent en un point, sinon
la lettre se descoud aux jonctions. Voir planche_main.png : deux lignes, le
meme mot, trois tirages.

POINT OUVERT 9 — le message se recentrait a chaque lettre. La toile etait
cadree sur sa boite englobante, donc sur le texte DEJA REVELE : chaque
caractere nouveau elargissait la boite et deplacait tout ce qui etait deja
trace. A l'ecran, le message aurait tremble lateralement toute la nuit. Le
cadre est desormais celui de la phrase COMPLETE, calcule avant de dessiner.

Ce qui ne change pas : la phrase se revele aux MOTS ECRITS, jamais a l'horloge.
Rester assis ne suffit pas.
"""

from __future__ import annotations

import math
import random

from grammaire import Toile, Teinte, SAUT, TRAIT, _entete

# --------------------------------------------------------------------------
# Alphabet. Grille 0..3 en x, 0..5 en y, traits droits uniquement : la meme
# primitive que les plantes, donc le message appartient au meme dessin.
# --------------------------------------------------------------------------
A = {
    "A": [(0,5,1.5,0),(1.5,0,3,5),(0.55,3.2,2.45,3.2)],
    "B": [(0,0,0,5),(0,0,2.2,0),(2.2,0,2.6,1.2),(2.6,1.2,2.2,2.4),(0,2.4,2.2,2.4),
          (2.2,2.4,2.8,3.6),(2.8,3.6,2.2,5),(0,5,2.2,5)],
    "C": [(3,0.9,2,0),(2,0,0.7,0.6),(0.7,0.6,0,2.5),(0,2.5,0.7,4.4),(0.7,4.4,2,5),(2,5,3,4.1)],
    "D": [(0,0,0,5),(0,0,1.9,0),(1.9,0,2.9,1.7),(2.9,1.7,2.9,3.3),(2.9,3.3,1.9,5),(1.9,5,0,5)],
    "E": [(2.9,0,0,0),(0,0,0,5),(0,5,2.9,5),(0,2.5,2.2,2.5)],
    "F": [(2.9,0,0,0),(0,0,0,5),(0,2.5,2.1,2.5)],
    "G": [(3,0.9,2,0),(2,0,0.7,0.6),(0.7,0.6,0,2.5),(0,2.5,0.7,4.4),(0.7,4.4,2,5),
          (2,5,3,4.1),(3,4.1,3,2.8),(3,2.8,1.7,2.8)],
    "H": [(0,0,0,5),(3,0,3,5),(0,2.6,3,2.6)],
    "I": [(1.5,0,1.5,5),(0.6,0,2.4,0),(0.6,5,2.4,5)],
    "J": [(2.5,0,2.5,3.9),(2.5,3.9,1.6,5),(1.6,5,0.4,4.3)],
    "K": [(0,0,0,5),(3,0,0.2,2.8),(0.9,2.1,3,5)],
    "L": [(0,0,0,5),(0,5,2.8,5)],
    "M": [(0,5,0,0),(0,0,1.5,2.6),(1.5,2.6,3,0),(3,0,3,5)],
    "N": [(0,5,0,0),(0,0,3,5),(3,5,3,0)],
    "O": [(1.5,0,0.3,1.3),(0.3,1.3,0.3,3.7),(0.3,3.7,1.5,5),(1.5,5,2.7,3.7),
          (2.7,3.7,2.7,1.3),(2.7,1.3,1.5,0)],
    "P": [(0,5,0,0),(0,0,2.3,0),(2.3,0,2.9,1.4),(2.9,1.4,2.3,2.7),(2.3,2.7,0,2.7)],
    "Q": [(1.5,0,0.3,1.3),(0.3,1.3,0.3,3.7),(0.3,3.7,1.5,5),(1.5,5,2.7,3.7),
          (2.7,3.7,2.7,1.3),(2.7,1.3,1.5,0),(1.9,3.6,3.1,5.4)],
    "R": [(0,5,0,0),(0,0,2.3,0),(2.3,0,2.9,1.4),(2.9,1.4,2.3,2.7),(2.3,2.7,0,2.7),
          (1.3,2.7,3,5)],
    "S": [(2.9,0.8,1.8,0),(1.8,0,0.4,0.7),(0.4,0.7,0.5,2),(0.5,2,2.5,2.9),
          (2.5,2.9,2.7,4.2),(2.7,4.2,1.4,5),(1.4,5,0.1,4.2)],
    "T": [(0,0,3,0),(1.5,0,1.5,5)],
    "U": [(0,0,0,3.7),(0,3.7,1.5,5),(1.5,5,3,3.7),(3,3.7,3,0)],
    "V": [(0,0,1.5,5),(1.5,5,3,0)],
    "W": [(0,0,0.7,5),(0.7,5,1.5,1.8),(1.5,1.8,2.3,5),(2.3,5,3,0)],
    "X": [(0,0,3,5),(3,0,0,5)],
    "Y": [(0,0,1.5,2.6),(3,0,1.5,2.6),(1.5,2.6,1.5,5)],
    "Z": [(0,0,3,0),(3,0,0,5),(0,5,3,5)],
    "?": [(0.2,1.0,1.4,0.0),(1.4,0.0,2.7,1.0),(2.7,1.0,1.5,2.6),
          (1.5,2.6,1.5,3.4),(1.5,4.4,1.5,5.0)],
    "'": [(1.5,0,1.2,1.4)],
    ",": [(1.5,4.2,1.1,5.6)],
    "!": [(1.5,0,1.5,3.4),(1.5,4.4,1.5,5)],
    ".": [(1.4,4.7,1.6,5)],
    # Le trait d'union, pour les prenoms composes (decision 10) : « Marie-Eve »
    # ne se dessinait pas. La barre du E, raccourcie.
    "-": [(0.5,2.5,2.5,2.5)],
    " ": [],
}

CORPS = 22.0
CHASSE = 1.38        # avance horizontale, en corps
INTERLIGNE = 2.0     # avance verticale, en corps
LARGEUR = 22         # caracteres par ligne


# --------------------------------------------------------------------------
# Le trait de main
# --------------------------------------------------------------------------
def _polyligne(t: Toile, ax, ay, bx, by, corps, rng, col, m, part=1.0):
    """
    Un trait de lettre, trace comme une branche.

    Trois choses, et c'est la troisieme qui compte : des sous-segments de
    LONGUEURS INEGALES (une droite subdivisee regulierement reste une droite
    reguliere), une marche perpendiculaire qui accumule au lieu de bruiter
    chaque point independamment (sinon c'est du grain, pas un geste), et un
    depassement aux extremites — une main ne s'arrete jamais pile.
    """
    d = math.hypot(bx - ax, by - ay)
    if d < 1e-6:
        return
    n = max(2, min(5, int(d / (corps * 0.34)) + 2))

    # Coupures inegales : le coeur du correctif du point ouvert 4.
    coupes = sorted(rng.uniform(0.10, 0.90) for _ in range(n - 1))
    jalons = [0.0] + coupes + [1.0]

    ux, uy = (bx - ax) / d, (by - ay) / d
    px, py = -uy, ux                              # perpendiculaire unitaire
    amp = corps * 0.030
    depart = -corps * 0.020 * rng.uniform(0, 1)   # depassement d'attaque
    arrivee = corps * 0.030 * rng.uniform(0, 1)   # depassement de sortie

    devs, courant = [], rng.uniform(-amp, amp) * 0.4
    for _ in jalons:
        courant += rng.uniform(-amp, amp) * 0.7
        devs.append(max(-amp * 1.6, min(amp * 1.6, courant)))

    pts = []
    for k, f in enumerate(jalons):
        long = depart + (d - depart + arrivee) * f
        pts.append((ax + ux * long + px * devs[k],
                    ay + uy * long + py * devs[k]))

    # Revelation : le trait en cours s'arrete en chemin.
    total = len(pts) - 1
    vus = part * total
    for k in range(total):
        if vus <= k:
            break
        g = min(1.0, vus - k)
        x1, y1 = pts[k]
        x2, y2 = pts[k + 1]
        t.trait(x1, y1, x1 + (x2 - x1) * g, y1 + (y2 - y1) * g, m, col)


def _droit_v6(t: Toile, ax, ay, bx, by, corps, rng, col, m, part=1.0):
    """
    Le trace de la v6, garde pour comparaison : une droite, dont on secoue les
    deux extremites. C'est ce qui laissait lire une grille.
    """
    j = corps * 0.055
    t.trait(ax + rng.uniform(-j, j), ay + rng.uniform(-j, j),
            ax + (bx - ax) * part + rng.uniform(-j, j),
            ay + (by - ay) * part + rng.uniform(-j, j), m, col)


TRACE = {"main": _polyligne, "v6": _droit_v6}


def _sommets(traits, rng, corps, force=1.0):
    """
    Deplace les SOMMETS de la lettre, pas ses traits.

    C'est le vrai correctif du point ouvert 4. Secouer les extremites de
    chaque trait (v6) ou onduler entre elles (premiere tentative) laisse
    intacts les angles : l'apex du M, la pointe du A, la diagonale du N
    tombent toujours sur les memes points de la grille 3x5, et l'oeil lit une
    fonte tremblee. En deplacant les sommets, les angles eux-memes changent
    d'un tirage a l'autre.

    Le decalage est partage par tous les traits qui se rejoignent en un point
    — sinon la lettre se descoud aux jonctions.
    """
    coins = {}
    d = corps * 0.055 * force

    def coin(x, y):
        cle = (round(x, 2), round(y, 2))
        if cle not in coins:
            coins[cle] = (rng.uniform(-d, d), rng.uniform(-d, d))
        return coins[cle]

    # Proportions propres a chaque instance : une main ne tient pas une
    # hauteur d'x constante d'une lettre a l'autre.
    kx = rng.uniform(0.93, 1.07)
    ky = rng.uniform(0.95, 1.05)

    sortie = []
    for (a, b, c, e) in traits:
        da = coin(a, b)
        db = coin(c, e)
        sortie.append((a * kx + da[0], b * ky + da[1],
                       c * kx + db[0], e * ky + db[1]))
    return sortie


def _mise_en_page(phrase: str, largeur=LARGEUR):
    phrase = phrase.upper().replace(" ?", " ?").replace(" !", " !")
    lignes, courante = [], ""
    for mot in phrase.split(" "):
        if len(courante) + len(mot) + 1 > largeur:
            lignes.append(courante)
            courante = mot
        else:
            courante = (courante + " " + mot).strip()
    lignes.append(courante)
    return [l.replace(" ", " ") for l in lignes]


def cadre_de(phrase: str, corps=CORPS, largeur=LARGEUR, x0=0.0, y0=0.0):
    """
    La boite de la phrase COMPLETE, calculee avant de dessiner.

    C'est ce qui empeche le message de se recentrer a chaque lettre.
    """
    lignes = _mise_en_page(phrase, largeur)
    l_max = max(len(l) for l in lignes)
    return (x0 - corps * 0.2,
            y0 - corps * 0.2,
            x0 + (l_max - 1) * corps * CHASSE + corps + corps * 0.2,
            y0 + (len(lignes) - 1) * corps * INTERLIGNE + corps + corps * 0.2)


def message(t: Toile, phrase: str, avancement: float, x0=0.0, y0=0.0,
            corps=CORPS, graine=1, largeur=LARGEUR, teinte=None, trace="main"):
    """
    Trace la phrase avec la primitive segment.

    `avancement` (0..1) vient des mots ecrits pendant la fenetre de nuit, pas
    de l'heure : la phrase ne se complete que si la personne travaille.
    """
    rng = random.Random(graine)
    tt = teinte or Teinte([(0, 1)], nuit=True, richesse=1.0)
    lignes = _mise_en_page(phrase, largeur)

    # Le cadre est pose d'abord, sur la phrase entiere.
    t.cadre = cadre_de(phrase, corps, largeur, x0, y0)

    total = sum(len(l) for l in lignes)
    reveles = avancement * total
    vus = 0
    for li, ligne in enumerate(lignes):
        for ci, ch in enumerate(ligne):
            part = reveles - vus
            vus += 1
            if part <= 0:
                continue
            f = min(1.0, part)
            px = x0 + ci * corps * CHASSE
            py = y0 + li * corps * INTERLIGNE
            traits = A.get(ch, [])
            n = len(traits)
            if not n:
                continue
            if trace == "main":
                # Les sommets de CETTE instance de la lettre.
                traits = _sommets(traits, rng, 3.0)
            # Chaque lettre est posee un peu de travers : la grille ne doit
            # pas se lire d'une lettre a l'autre non plus.
            plume = TRACE[trace]
            inclinaison = rng.uniform(-0.035, 0.035) if trace == "main" else 0.0
            decal = rng.uniform(-corps * 0.045, corps * 0.045)
            for i, (a, b, c, d) in enumerate(traits):
                seuil = (i + 1) / n
                if f < seuil - 1 / n:
                    continue
                part_trait = 1.0 if f >= seuil else (f - (seuil - 1 / n)) * n
                ax = px + a * corps / 3
                ay = py + b * corps / 5 + decal
                bx = px + c * corps / 3
                by = py + d * corps / 5 + decal
                cy = py + corps * 0.5
                # rotation de la lettre autour de son milieu
                def tourne(X, Y):
                    dx, dy = X - (px + corps / 2), Y - cy
                    co, si = math.cos(inclinaison), math.sin(inclinaison)
                    return (px + corps / 2 + dx * co - dy * si,
                            cy + dx * si + dy * co)
                ax, ay = tourne(ax, ay)
                bx, by = tourne(bx, by)
                plume(t, ax, ay, bx, by, corps, rng,
                      tt.ton(rng), rng.uniform(0.45, 0.85), part_trait)


# --------------------------------------------------------------------------
PHRASES_ESSAI = [
    "il est tard, et tu ecris quand meme",
    "personne ne te regarde. moi si.",
]


def planche_revelation():
    """Le message ne doit plus bouger d'une colonne a l'autre."""
    CW, CH, MG, TOP = 330, 210, 130, 54
    W, H = MG + CW * 3 + 20, TOP + CH * 2 + 20
    o = _entete(W, H)
    for j, lab in enumerate(("120 MOTS", "450 MOTS", "800 MOTS")):
        o.append(f'<text x="{MG + j*CW + CW/2}" y="30" font-size="10.5" '
                 f'text-anchor="middle" letter-spacing="1.5">{lab}</text>')
    for i, phrase in enumerate(PHRASES_ESSAI):
        y0 = TOP + i * CH
        for j, av in enumerate((0.15, 0.56, 1.0)):
            t = Toile()
            message(t, phrase, av, graine=40 + i)
            o.append(t.svg(MG + j * CW, y0, CW, CH))
    o.append(f'<text x="18" y="{TOP + CH - 20}" font-size="12" '
             f'fill="#2c3230">Entre 2h et 5h</text>')
    return SAUT.join(o) + '</g></svg>'


def planche_main():
    """Point ouvert 4 : la lettre doit cesser de venir d'une grille."""
    CW, CH, MG, TOP = 290, 150, 210, 54
    W, H = MG + CW * 3 + 20, TOP + CH * 2 + 20
    o = _entete(W, H)
    for j in range(3):
        o.append(f'<text x="{MG + j*CW + CW/2}" y="32" font-size="10.5" '
                 f'text-anchor="middle" letter-spacing="1.4">'
                 f'TIRAGE {j + 1}</text>')
    for i, (lab, trace) in enumerate((("droite + extremites secouees (v6)", "v6"),
                                      ("polyligne a longueurs inegales", "main"))):
        y0 = TOP + i * CH
        o.append(f'<text x="18" y="{y0 + CH/2}" font-size="11.5" '
                 f'fill="#2c3230">{lab}</text>')
        for j in range(3):
            t = Toile()
            message(t, "MAIN", 1.0, corps=46, graine=300 + j * 91,
                    largeur=8, trace=trace)
            o.append(t.svg(MG + j * CW, y0, CW, CH))
    return SAUT.join(o) + '</g></svg>'


def verifier():
    """Le cadre ne doit pas dependre de l'avancement (point ouvert 9)."""
    cadres = set()
    for av in (0.05, 0.2, 0.5, 0.8, 1.0):
        t = Toile()
        message(t, PHRASES_ESSAI[0], av, graine=7)
        cadres.add(tuple(round(v, 3) for v in t.cadre))
    stable = len(cadres) == 1
    print(f"  cadre identique a tous les avancements : "
          f"{'oui' if stable else 'NON'}  {cadres}")

    manquants = {c for p in PHRASES_ESSAI for c in p.upper()} - set(A)
    print(f"  caracteres manquants dans l'alphabet : {manquants or 'aucun'}")

    t = Toile()
    message(t, PHRASES_ESSAI[0], 1.0, graine=7)
    droits = sum(1 for s in t.segments)
    print(f"  '{PHRASES_ESSAI[0]}' -> {droits} segments"
          f" ({droits / max(len(PHRASES_ESSAI[0].replace(' ', '')), 1):.1f} par lettre)")
    return stable


if __name__ == "__main__":
    for nom, fn in (("planche_revelation", planche_revelation),
                    ("planche_main", planche_main)):
        open(f"{nom}.svg", "w", encoding="utf-8").write(fn())
        print(f"{nom}.svg ecrit")
    print()
    verifier()
