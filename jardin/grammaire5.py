"""
Grammaire v5.

PALETTES SAISONNIERES. Quatre palettes de trois tons, plutot qu'une rotation
continue de teinte : une palette d'hiver se reconnait, une teinte a 0.08 sur la
roue chromatique ne veut rien dire. Fondu aux frontieres pour qu'une plante a
cheval sur deux saisons porte les deux.

EASTER EGG. Les segments ecrits entre 2h et 5h prennent une palette qui
n'apparait nulle part ailleurs. Rien ne l'annonce dans l'interface ; sur une
these, la personne finira par la decouvrir seule.

CREATURE. Correction : les trois curseurs agissent desormais sur la GEOMETRIE
— largeur du corps, taille de la tete, longueur des membres — et plus seulement
sur la densite de traits. En v4 seul le curseur membres changeait la silhouette.
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
    "hiver":     ["#5b7a8c", "#8ba3ad", "#43596b"],
    "printemps": ["#6d9450", "#96b56a", "#4f7a3f"],
    "ete":       ["#c08a3e", "#d4aa5c", "#a86f2d"],
    "automne":   ["#a3542f", "#bd7448", "#7d3d22"],
    "nuit":      ["#7a7f9c", "#9aa0bd", "#5c6180"],   # easter egg
}

BORNES = [(0, "hiver"), (80, "printemps"), (172, "ete"), (264, "automne"), (355, "hiver")]
FONDU = 12  # jours de transition de part et d'autre d'une frontiere


def _melange(c1, c2, f):
    p = lambda c: tuple(int(c[i:i+2], 16) for i in (1, 3, 5))
    a, b = p(c1), p(c2)
    return "#" + "".join(f"{int(a[i] + (b[i]-a[i])*f):02x}" for i in range(3))


def palette(jour: int, heure: int = 14, ton: int = 0) -> str:
    """Couleur d'un segment selon le moment ou il a ete ecrit."""
    if 2 <= heure < 5:
        return PALETTES["nuit"][ton % 3]
    jour = jour % 365
    saison, suivante, f = "hiver", "hiver", 0.0
    for i in range(len(BORNES) - 1):
        d, nom = BORNES[i]
        d2, nom2 = BORNES[i + 1]
        if d <= jour < d2:
            saison, suivante = nom, nom2
            if jour > d2 - FONDU:                      # fondu de frontiere
                f = (jour - (d2 - FONDU)) / FONDU * 0.5
            break
    c1 = PALETTES[saison][ton % 3]
    c2 = PALETTES[suivante][ton % 3]
    return _melange(c1, c2, f) if f else c1


class Toile:
    def __init__(self):
        self.segments: list[tuple] = []

    def trait(self, x1, y1, x2, y2, m=0.0, col=None):
        self.segments.append((x1, y1, x2, y2, m, col or TRAIT))

    def bbox(self):
        xs = [v for s in self.segments for v in (s[0], s[2])]
        ys = [v for s in self.segments for v in (s[1], s[3])]
        return (min(xs), min(ys), max(xs), max(ys)) if xs else (0, 0, 1, 1)

    def svg(self, cx, cy, cw, ch) -> str:
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


def creature(t, extension, m, graine, jour, heure=14, etoffage=None):
    """
    etoffage pilote la GEOMETRIE, pas seulement la densite :
        corps   -> largeur du corps
        tete    -> taille de la tete
        membres -> longueur et nombre des membres
    """
    rng = random.Random(graine)
    e = etoffage or {"tete": 0.6, "corps": 0.6, "membres": 0.6}

    n = 7 + int(extension * 11)
    spine, angle, x, y = [], -0.55, 55, 165
    for i in range(n):
        f = i / max(n - 1, 1)
        lg = SEGMENT * 0.60 * (1.15 - 0.55*f)
        angle += math.sin(i*0.40)*0.30 + 0.12 + rng.uniform(-0.05, 0.05)
        x, y = x + math.cos(angle)*lg, y + math.sin(angle)*lg
        spine.append((x, y, angle, 1.15 - 0.85*f))

    # CORPS : la largeur va de gracile a massif (facteur 5 entre les extremes)
    ampleur = 0.16 + e["corps"] * 0.68
    gauche, droite = [], []
    for (px, py, pa, ep) in spine:
        larg = SEGMENT * ampleur * ep
        gauche.append((px + math.cos(pa-1.57)*larg, py + math.sin(pa-1.57)*larg))
        droite.append((px + math.cos(pa+1.57)*larg, py + math.sin(pa+1.57)*larg))
    contour = gauche + droite[::-1]
    for i in range(len(contour)):
        t.trait(*contour[i], *contour[(i+1) % len(contour)], m)
    pas = max(1, int(3 - e["corps"]*2))
    for i in range(0, len(spine), pas):
        t.trait(*gauche[i], *droite[i], m*0.55, palette(jour, heure, 1))

    # TETE : le rayon suit le curseur, pas seulement le nombre d'appendices
    hx, hy, ha, _ = spine[0]
    rayon = SEGMENT * (0.22 + e["tete"] * 1.15)
    n_tete = 3 + int(e["tete"] * 6)
    for k in range(n_tete):
        a = ha + math.pi + (k - n_tete/2) * (1.9 / max(n_tete, 1))
        t.trait(hx, hy, hx + math.cos(a)*rayon, hy + math.sin(a)*rayon,
                m*0.85, palette(jour, heure, 0))
    if e["tete"] > 0.5:                                # calotte : ferme la tete
        pts = [(hx + math.cos(ha + math.pi + (k-3)*0.32)*rayon*0.8,
                hy + math.sin(ha + math.pi + (k-3)*0.32)*rayon*0.8) for k in range(7)]
        for i in range(len(pts)-1):
            t.trait(*pts[i], *pts[i+1], m*0.7)

    # MEMBRES
    pas_m = max(1, int(3 - e["membres"]*2))
    for i in range(1, len(spine)-1, pas_m):
        px, py, pa, ep = spine[i]
        for s, bord in ((-1, gauche), (1, droite)):
            ax, ay = bord[i]
            a1 = pa + s*(1.15 + 0.2*math.sin(i))
            p1 = SEGMENT * (0.25 + 1.25*e["membres"]) * ep
            bx, by = ax + math.cos(a1)*p1, ay + math.sin(a1)*p1
            t.trait(ax, ay, bx, by, m*0.8)
            a2 = a1 + s*rng.uniform(0.55, 1.0)
            t.trait(bx, by, bx + math.cos(a2)*p1*0.65, by + math.sin(a2)*p1*0.65,
                    m*0.6, palette(jour, heure, 2))


CAS_SAISON = [("HIVER", 20, 14), ("PRINTEMPS", 110, 14), ("ETE", 200, 14),
              ("AUTOMNE", 300, 14), ("3H DU MATIN", 200, 3)]
CAS_ANATOMIE = [("gracile", {"tete": .2, "corps": .1, "membres": .2}),
                ("massif", {"tete": .3, "corps": 1.0, "membres": .2}),
                ("grosse tete", {"tete": 1.0, "corps": .35, "membres": .2}),
                ("pattu", {"tete": .25, "corps": .3, "membres": 1.0}),
                ("tout", {"tete": .85, "corps": .85, "membres": .85})]


def planche(cas, titre_ligne, saison=True):
    CW, CH, MG, TOP = 190, 200, 150, 56
    W, H = MG + CW*len(cas) + 20, TOP + CH + 16
    o = _entete(W, H)
    for j, item in enumerate(cas):
        o.append(f'<text x="{MG + j*CW + CW/2}" y="32" font-size="10.5" '
                 f'text-anchor="middle" letter-spacing="1.4">{item[0].upper()}</text>')
        t = Toile()
        if saison:
            creature(t, 0.7, 0.8, 777, item[1], item[2],
                     {"tete": .8, "corps": .7, "membres": .7})
        else:
            creature(t, 0.7, 0.8, 777, 200, 14, item[1])
        o.append(t.svg(MG + j*CW, TOP, CW, CH))
    o.append(f'<text x="18" y="{TOP + CH/2}" font-size="13" fill="#2c3230">{titre_ligne}</text>')
    return "\n".join(o) + '</g></svg>'


if __name__ == "__main__":
    open("planche_saisons.svg", "w", encoding="utf-8").write(
        planche(CAS_SAISON, "Palettes"))
    open("planche_anatomie2.svg", "w", encoding="utf-8").write(
        planche(CAS_ANATOMIE, "Geometrie", saison=False))
    print("planches ecrites")
    for j, h in ((20, 14), (110, 14), (200, 14), (300, 14), (200, 3), (76, 14)):
        print(f"  jour {j:>3} {h:>2}h -> {palette(j, h)}")
