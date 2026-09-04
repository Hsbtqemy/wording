"""
Grammaire v6 : polychromie et message de nuit.

COULEURS MULTIPLES. Chaque palette compte cinq tons, tires par segment depuis
la graine du document. Une plante de printemps porte donc plusieurs verts, sans
que rien ne devienne aleatoire au sens strict : meme document, meme figure.

MESSAGE DE NUIT. Entre 2h et 5h, une phrase se revele progressivement. Elle est
tracee AVEC LE MEME SEGMENT que les plantes — pas avec une police. C'est ce qui
lui evite de casser la langue graphique : le message est fait de la meme matiere
que le paysage.

Et elle se revele a la REDACTION, pas a l'horloge : rester assis ne suffit pas,
il faut ecrire. La phrase se complete sur environ 800 mots dans la fenetre de
nuit, quelle que soit sa longueur.

Les phrases sont a ecrire par celui qui offre. C'est le seul endroit du systeme
ou sa voix passe ; tout le reste marcherait pour n'importe qui.
"""

from __future__ import annotations

import math
import random

from grammaire2 import _entete

TRAIT = "#2c3230"
FOND = "#faf8f4"
EPAISSEUR = 1.5
SEGMENT = 26.0

PALETTES = {
    "hiver":     ["#5b7a8c", "#8ba3ad", "#43596b", "#6e8fa0", "#9fb3ba"],
    "printemps": ["#6d9450", "#96b56a", "#4f7a3f", "#7fa85e", "#adc47f"],
    "ete":       ["#c08a3e", "#d4aa5c", "#a86f2d", "#caa04e", "#b8823a"],
    "automne":   ["#a3542f", "#bd7448", "#7d3d22", "#b0603a", "#8e4a28"],
    "nuit":      ["#8d84c4", "#a99ede", "#7a6fb0", "#9a90d2", "#b8aeea"],
}

BORNES = [(0, "hiver"), (80, "printemps"), (172, "ete"), (264, "automne"), (355, "hiver")]


def palette(jour, heure=14, rng=None):
    """Un ton parmi cinq, tire par le generateur du document."""
    if 2 <= heure < 5:
        tons = PALETTES["nuit"]
    else:
        jour %= 365
        nom = "hiver"
        for i in range(len(BORNES) - 1):
            if BORNES[i][0] <= jour < BORNES[i + 1][0]:
                nom = BORNES[i][1]
                break
        tons = PALETTES[nom]
    return (rng or random).choice(tons)


# ------------------------------------------------- alphabet fait de segments
# Grille 0..3 en x, 0..5 en y. Traits droits uniquement : c'est la meme
# primitive que les plantes, donc le message appartient au meme dessin.
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
    "'": [(1.5,0,1.2,1.4)],
    ",": [(1.5,4.2,1.1,5.6)],
    "!": [(1.5,0,1.5,3.4),(1.5,4.4,1.5,5)],
    ".": [(1.4,4.7,1.6,5)],
    " ": [],
}


class Toile:
    def __init__(self):
        self.segments = []

    def trait(self, x1, y1, x2, y2, m=0.0, col=None):
        self.segments.append((x1, y1, x2, y2, m, col or TRAIT))

    def bbox(self):
        xs = [v for s in self.segments for v in (s[0], s[2])]
        ys = [v for s in self.segments for v in (s[1], s[3])]
        return (min(xs), min(ys), max(xs), max(ys)) if xs else (0, 0, 1, 1)

    def svg(self, cx, cy, cw, ch):
        x0, y0, x1, y1 = self.bbox()
        w, h = max(x1 - x0, 1), max(y1 - y0, 1)
        k = min(1.0, (cw - 26) / w, (ch - 26) / h)
        ox, oy = cx + cw/2 - (x0 + w/2)*k, cy + ch/2 - (y0 + h/2)*k
        out = [f'<g transform="translate({ox:.1f},{oy:.1f}) scale({k:.3f})">']
        for a, b, c, d, m, col in self.segments:
            e = EPAISSEUR * (1 + 1.7*m) / max(k, 0.35)
            out.append(f'<line x1="{a:.1f}" y1="{b:.1f}" x2="{c:.1f}" y2="{d:.1f}" '
                       f'stroke="{col}" stroke-width="{e:.2f}" stroke-linecap="round"/>')
        return "".join(out) + "</g>"


def message(t, phrase, avancement, x0=0, y0=0, corps=22.0, graine=1, largeur=22):
    """
    Trace la phrase avec la primitive segment.

    `avancement` (0..1) vient des mots ecrits pendant la fenetre de nuit, pas
    de l'heure : la phrase ne se complete que si la personne travaille.
    Le dernier caractere en cours est trace partiellement, d'ou l'impression
    d'une main qui ecrit.
    """
    rng = random.Random(graine)
    phrase = phrase.upper()
    phrase = phrase.replace(" ?", "\u00a0?").replace(" !", "\u00a0!")
    lignes, courante = [], ""
    for mot in phrase.split(" "):
        if len(courante) + len(mot) + 1 > largeur:
            lignes.append(courante); courante = mot
        else:
            courante = (courante + " " + mot).strip()
    lignes.append(courante)

    total = sum(len(l) for l in lignes)
    reveles = avancement * total
    vus = 0
    for li, ligne in enumerate(lignes):
        ligne = ligne.replace("\u00a0", " ")
        for ci, ch in enumerate(ligne):
            part = reveles - vus
            vus += 1
            if part <= 0:
                continue
            f = min(1.0, part)
            px = x0 + ci * corps * 1.38
            py = y0 + li * corps * 2.0
            traits = A.get(ch, [])
            n = len(traits)
            for i, (a, b, c, d) in enumerate(traits):
                seuil = (i + 1) / max(n, 1)
                if f < seuil - 1/max(n,1):
                    continue
                # le trait en cours est dessine partiellement
                g = 1.0 if f >= seuil else (f - (seuil - 1/max(n,1))) * max(n, 1)
                col = palette(0, 3, rng)
                j = corps * 0.055   # tremblement : sans lui, c'est une police
                ax = px + a*corps/3 + rng.uniform(-j, j)
                ay = py + b*corps/5 + rng.uniform(-j, j)
                bx = px + (a + (c-a)*g)*corps/3 + rng.uniform(-j, j)
                by = py + (b + (d-b)*g)*corps/5 + rng.uniform(-j, j)
                t.trait(ax, ay, bx, by, rng.uniform(0.45, 0.85), col)


PHRASES = [
    "il est tard, et tu ecris quand meme",
    "personne ne te regarde. moi si.",
    "encore une phrase, puis va dormir",
    "ce paragraphe comptera, meme si tu le coupes",
]


def planche_message():
    CW, CH, MG, TOP = 330, 210, 130, 54
    W, H = MG + CW*3 + 20, TOP + CH*2 + 20
    o = _entete(W, H)
    for j, lab in enumerate(("120 MOTS", "450 MOTS", "800 MOTS")):
        o.append(f'<text x="{MG + j*CW + CW/2}" y="30" font-size="10.5" '
                 f'text-anchor="middle" letter-spacing="1.5">{lab}</text>')
    for i, phrase in enumerate(PHRASES[:2]):
        y0 = TOP + i*CH
        for j, av in enumerate((0.15, 0.56, 1.0)):
            t = Toile()
            message(t, phrase, av, graine=40 + i)
            o.append(t.svg(MG + j*CW, y0, CW, CH))
    o.append(f'<text x="18" y="{TOP + CH - 20}" font-size="12" fill="#2c3230">'
             f'Entre 2h et 5h</text>')
    return "\n".join(o) + '</g></svg>'


if __name__ == "__main__":
    open("planche_message.svg", "w", encoding="utf-8").write(planche_message())
    print("planche_message.svg ecrit")
    manquants = {c for p in PHRASES for c in p.upper()} - set(A)
    print("caracteres manquants dans l'alphabet :", manquants or "aucun")
