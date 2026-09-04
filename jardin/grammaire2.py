"""
Grammaire commune, version 2.

Correction majeure par rapport a v1 : l'extension et la maturite etaient
pilotees par un seul parametre, donc la planche testait la croissance et pas
du tout les deux axes. Ici elles sont independantes.

  extension -> combien de segments (ca pousse)
  maturite  -> ce que devient un segment deja la (ca murit)
"""

from __future__ import annotations

import math
import random

TRAIT = "#2c3230"
NOEUD = "#a8532f"
FOND = "#faf8f4"
EPAISSEUR = 1.5
SEGMENT = 26.0


class Toile:
    def __init__(self):
        self.segments: list[tuple] = []
        self.noeuds: list[tuple] = []

    def trait(self, x1, y1, x2, y2, m=0.0):
        self.segments.append((x1, y1, x2, y2, m))

    def noeud(self, x, y, m):
        # Les noeuds n'apparaissent que tard, et restent petits : en v1 ils
        # devenaient une rougeole qui ecrasait tout le reste.
        if m > 0.55:
            self.noeuds.append((x, y, m))

    def bbox(self):
        xs = [v for s in self.segments for v in (s[0], s[2])]
        ys = [v for s in self.segments for v in (s[1], s[3])]
        if not xs:
            return 0, 0, 1, 1
        return min(xs), min(ys), max(xs), max(ys)

    def svg(self, cx, cy, cw, ch) -> str:
        """Centre dans la case, et ne reduit QUE si ca deborde."""
        x0, y0, x1, y1 = self.bbox()
        w, h = max(x1 - x0, 1), max(y1 - y0, 1)
        k = min(1.0, (cw - 24) / w, (ch - 24) / h)
        ox = cx + cw / 2 - (x0 + w / 2) * k
        oy = cy + ch / 2 - (y0 + h / 2) * k
        out = [f'<g transform="translate({ox:.1f},{oy:.1f}) scale({k:.3f})">']
        for a, b, c, d, m in self.segments:
            e = EPAISSEUR * (1 + 1.9 * m) / max(k, 0.35)
            out.append(f'<line x1="{a:.1f}" y1="{b:.1f}" x2="{c:.1f}" y2="{d:.1f}" '
                       f'stroke="{TRAIT}" stroke-width="{e:.2f}" stroke-linecap="round"/>')
        for x, y, m in self.noeuds:
            r = (1.0 + 1.8 * m) / max(k, 0.35)
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" '
                       f'fill="{NOEUD}" opacity="{0.35 + 0.5*m:.2f}"/>')
        out.append('</g>')
        return "".join(out)


def _plume(t, x, y, angle, longueur, m, rng):
    """Detail de maturite commun : de courtes barbes le long d'un segment."""
    if m < 0.3:
        return
    n = int(m * 4)
    for i in range(1, n + 1):
        f = i / (n + 1)
        px, py = x + math.cos(angle) * longueur * f, y + math.sin(angle) * longueur * f
        l = longueur * 0.22 * m
        for s in (-1, 1):
            a = angle + s * 1.25
            t.trait(px, py, px + math.cos(a) * l, py + math.sin(a) * l, m * 0.45)


# ------------------------------------------------------------------- assemblages
def ramifier(t, x, y, angle, longueur, prof, m, rng):
    if prof <= 0 or longueur < 3.5:
        return
    x2, y2 = x + math.cos(angle) * longueur, y + math.sin(angle) * longueur
    t.trait(x, y, x2, y2, m)
    _plume(t, x, y, angle, longueur, m, rng)
    t.noeud(x2, y2, m)
    ouv = rng.uniform(0.40, 0.60)
    for s in (-1, 1):
        ramifier(t, x2, y2, angle + s * ouv,
                 longueur * rng.uniform(0.68, 0.79), prof - 1, m * 0.95, rng)


def empiler(t, cx, base, niveaux, largeur, m, rng):
    y = base
    for i in range(niveaux):
        h = SEGMENT * rng.uniform(0.62, 0.82)
        l = largeur * (1 - i / (niveaux + 3.0)) * rng.uniform(0.9, 1.0)
        g, d = cx - l / 2, cx + l / 2
        t.trait(g, y, d, y, m)
        t.trait(g, y, g, y - h, m)
        t.trait(d, y, d, y - h, m)
        t.noeud(g, y, m); t.noeud(d, y, m)
        n = int(m * 3.6)                       # refends : detail de maturite
        for k in range(1, n + 1):
            xk = g + (d - g) * k / (n + 1)
            t.trait(xk, y, xk, y - h, m * 0.65)
        if m > 0.6:                            # linteaux
            t.trait(g, y - h * 0.55, d, y - h * 0.55, m * 0.5)
        y -= h
    t.trait(cx - largeur * 0.3, y, cx + largeur * 0.3, y, m)


def enchainer(t, x, y, angle, n, m, rng):
    for i in range(n):
        lg = SEGMENT * rng.uniform(0.48, 0.66)
        angle += math.sin(i * 0.5) * 0.30 + rng.uniform(-0.07, 0.07)
        x2, y2 = x + math.cos(angle) * lg, y + math.sin(angle) * lg
        t.trait(x, y, x2, y2, m)
        if i % 2 == 0:
            p = lg * (0.5 + 0.9 * m)
            for s in (-1, 1):
                a = angle + s * 1.2
                xa, ya = x2 + math.cos(a) * p, y2 + math.sin(a) * p
                t.trait(x2, y2, xa, ya, m * 0.85)
                _plume(t, x2, y2, a, p, m, rng)
                t.noeud(xa, ya, m)
        x, y = x2, y2


def paver(t, cx, cy, anneaux, cotes, m, rng):
    prec = None
    for a in range(1, anneaux + 1):
        r = SEGMENT * 0.6 * a
        pts = [(cx + math.cos(2*math.pi*k/cotes + a*0.14) * r * rng.uniform(0.94, 1.06),
                cy + math.sin(2*math.pi*k/cotes + a*0.14) * r * rng.uniform(0.94, 1.06))
               for k in range(cotes)]
        for k in range(cotes):
            t.trait(*pts[k], *pts[(k+1) % cotes], m)
        if prec:
            for k in range(cotes):
                t.trait(*prec[k], *pts[k], m * 0.8)
                t.noeud(*pts[k], m)
                if m > 0.45:                   # subdivision : detail de maturite
                    mx = ((prec[k][0]+pts[k][0])/2, (prec[k][1]+pts[k][1])/2)
                    nx = ((prec[(k+1) % cotes][0]+pts[(k+1) % cotes][0])/2,
                          (prec[(k+1) % cotes][1]+pts[(k+1) % cotes][1])/2)
                    t.trait(*mx, *nx, m * 0.5)
        prec = pts


FAMILLES = ["vegetal", "architecture", "creature", "abstrait"]
LIB = {"vegetal": "Vegetal / ramifier", "architecture": "Architecture / empiler",
       "creature": "Creature / enchainer", "abstrait": "Abstrait / paver"}


def dessiner(famille, extension, maturite, graine):
    """extension et maturite dans 0..1, strictement independants."""
    rng = random.Random(graine)
    t = Toile()
    e, m = extension, maturite
    if famille == "vegetal":
        ramifier(t, 100, 200, -math.pi/2, SEGMENT*1.6, 3 + int(e*3.4), SEGMENT*0+m, rng)
    elif famille == "architecture":
        empiler(t, 100, 200, 2 + int(e*5), 88, m, rng)
    elif famille == "creature":
        enchainer(t, 40, 120, -0.30, 5 + int(e*13), m, rng)
    elif famille == "abstrait":
        paver(t, 100, 110, 1 + int(e*3.4), 6, m, rng)
    return t


def _entete(W, H):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%">',
            f'<rect width="{W}" height="{H}" fill="{FOND}"/>',
            '<g font-family="Georgia, serif" fill="#6b6560">']


def planche_unite():
    """4 familles x 3 extensions, maturite constante : teste l'unite."""
    CW, CH, MG = 200, 200, 190
    W, H = MG + CW*3 + 20, 54 + CH*4
    o = _entete(W, H)
    for j, lab in enumerate(("PEU ETENDU", "MOYEN", "TRES ETENDU")):
        o.append(f'<text x="{MG + j*CW + CW/2}" y="30" font-size="11" '
                 f'text-anchor="middle" letter-spacing="1.6">{lab}</text>')
    for i, f in enumerate(FAMILLES):
        y0 = 46 + i*CH
        o.append(f'<text x="20" y="{y0 + CH/2}" font-size="13" fill="#2c3230">{LIB[f]}</text>')
        for j, e in enumerate((0.15, 0.55, 1.0)):
            o.append(dessiner(f, e, 0.28, 900 + i*23 + j).svg(MG + j*CW, y0, CW, CH))
    o.append('</g></svg>')
    return "\n".join(o)


def planche_axes(famille="vegetal"):
    """3 extensions x 3 maturites : teste que les deux axes sont distincts."""
    CW, CH, MG, TOP = 200, 200, 150, 54
    W, H = MG + CW*3 + 20, TOP + CH*3 + 10
    o = _entete(W, H)
    for j, lab in enumerate(("PEU ETENDU", "MOYEN", "TRES ETENDU")):
        o.append(f'<text x="{MG + j*CW + CW/2}" y="30" font-size="11" '
                 f'text-anchor="middle" letter-spacing="1.6">{lab}</text>')
    for i, (lab, m) in enumerate((("BRUT", 0.08), ("REPRIS", 0.5), ("ABOUTI", 0.95))):
        y0 = TOP + i*CH
        o.append(f'<text x="20" y="{y0 + CH/2}" font-size="11" letter-spacing="1.6">{lab}</text>')
        for j, e in enumerate((0.15, 0.55, 1.0)):
            o.append(dessiner(famille, e, m, 700 + j*11).svg(MG + j*CW, y0, CW, CH))
    o.append('</g></svg>')
    return "\n".join(o)


if __name__ == "__main__":
    open("planche_unite.svg", "w", encoding="utf-8").write(planche_unite())
    open("planche_axes.svg", "w", encoding="utf-8").write(planche_axes("vegetal"))
    print("planches ecrites")
