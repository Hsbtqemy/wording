"""
Grammaire v4 : couleur et anatomie.

COULEUR. Elle ne vient ni du hasard ni d'une graine arbitraire mais de la DATE
d'ecriture du segment. Sur une these de cinq ans, le paysage garde la trace des
saisons. La date est enregistree une fois, a la creation du segment, donc la
figure reste identique a chaque reouverture.

Deux regles pour preserver l'unite etablie a la v2 :
  - la couleur ne touche jamais la structure, uniquement l'etoffage
  - saturation et clarte restent dans une plage etroite ; seule la teinte bouge

CREATURE. Reconstruite en trois parties nommees — tete, corps, membres —
chacune avec son propre etoffage. Le corps est un contour FERME : c'est ce qui
lui rend une silhouette, ce qui manquait a la v3.
"""

from __future__ import annotations

import colorsys
import math
import random

from grammaire2 import _entete

TRAIT = "#2c3230"
FOND = "#faf8f4"
EPAISSEUR = 1.5
SEGMENT = 26.0


# ------------------------------------------------------------------- couleur
def teinte_du_moment(jour_de_l_annee: int, decalage=0.0) -> str:
    """
    Teinte parcourant l'annee. Saturation et clarte volontairement bornees :
    c'est ce qui empeche la couleur de faire exploser la coherence de la planche.
    """
    h = ((jour_de_l_annee / 365.0) * 0.82 + 0.03 + decalage) % 1.0
    s = 0.42
    l = 0.44
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


class Toile:
    def __init__(self):
        self.segments: list[tuple] = []

    def trait(self, x1, y1, x2, y2, m=0.0, col=None):
        self.segments.append((x1, y1, x2, y2, m, col or TRAIT))

    def bbox(self):
        xs = [v for s in self.segments for v in (s[0], s[2])]
        ys = [v for s in self.segments for v in (s[1], s[3])]
        if not xs:
            return 0, 0, 1, 1
        return min(xs), min(ys), max(xs), max(ys)

    def svg(self, cx, cy, cw, ch) -> str:
        x0, y0, x1, y1 = self.bbox()
        w, h = max(x1 - x0, 1), max(y1 - y0, 1)
        k = min(1.0, (cw - 26) / w, (ch - 26) / h)
        ox = cx + cw / 2 - (x0 + w / 2) * k
        oy = cy + ch / 2 - (y0 + h / 2) * k
        out = [f'<g transform="translate({ox:.1f},{oy:.1f}) scale({k:.3f})">']
        for a, b, c, d, m, col in self.segments:
            e = EPAISSEUR * (1 + 1.7 * m) / max(k, 0.35)
            out.append(f'<line x1="{a:.1f}" y1="{b:.1f}" x2="{c:.1f}" y2="{d:.1f}" '
                       f'stroke="{col}" stroke-width="{e:.2f}" stroke-linecap="round"/>')
        out.append('</g>')
        return "".join(out)


# ------------------------------------------------------------------- VEGETAL
def vegetal(t, extension, m, graine, jour):
    rng = random.Random(graine)
    col = teinte_du_moment(jour)
    noeuds = []
    prof_max = 4 + int(extension * 3.0)

    def branche(x, y, angle, lg, prof, lignee):
        if prof <= 0 or lg < 3.0:
            # Bouquet plafonne : en v3 il fusionnait en aplat noir des que
            # l'arbre grandissait, et masquait la structure.
            n = 3 + int(m * 3)
            for i in range(n):
                a = angle + (i - n / 2) * 0.40 + rng.uniform(-0.1, 0.1)
                r = lg * (1.3 + 0.8 * m)
                t.trait(x, y, x + math.cos(a) * r, y + math.sin(a) * r, m * 0.55, col)
            return
        x2, y2 = x + math.cos(angle) * lg, y + math.sin(angle) * lg
        t.trait(x, y, x2, y2, m)                       # structure : jamais coloree
        noeuds.append((x2, y2, lignee))
        ouv = rng.uniform(0.34, 0.56)
        for s in (-1, 1):
            branche(x2, y2, angle + s * ouv, lg * rng.uniform(0.70, 0.80),
                    prof - 1, lignee * 2 + (s > 0))

    branche(100, 200, -math.pi / 2, SEGMENT * 1.7, prof_max, 1)

    seuil = SEGMENT * (0.5 + 0.45 * m)
    faits = 0
    for i, (x1, y1, l1) in enumerate(noeuds):
        for x2, y2, l2 in noeuds[i + 1:]:
            if l1 == l2 or faits > 30 * m + 6:
                continue
            if 6 < math.hypot(x2 - x1, y2 - y1) < seuil and rng.random() < 0.45:
                t.trait(x1, y1, x2, y2, m * 0.55)
                faits += 1


# -------------------------------------------------------------- ARCHITECTURE
def architecture(t, extension, m, graine, jour):
    rng = random.Random(graine)
    n_tours = 3 + int(extension * 4)
    ordre = sorted(range(n_tours), key=lambda k: rng.random())
    for rang, k in enumerate(ordre):
        # Chaque tour a sa propre date : un chapitre ecrit l'hiver et un autre
        # l'ete ne s'eclairent pas de la meme couleur.
        col = teinte_du_moment((jour + rang * 47) % 365)
        h = SEGMENT * rng.uniform(2.2, 6.0) * (0.55 + extension * 0.7)
        w = SEGMENT * rng.uniform(0.85, 1.7)
        cx = 100 + (k - n_tours / 2) * SEGMENT * 1.15 + rng.uniform(-6, 6)
        base = 205 - rang * SEGMENT * 0.22
        g, d, top = cx - w / 2, cx + w / 2, base - h
        for seg in ((g, base, g, top), (d, base, d, top),
                    (g, top, d, top), (g, base, d, base)):
            t.trait(*seg, m)                            # structure
        etages = max(2, int(h / (SEGMENT * (0.62 - 0.22 * m))))
        colonnes = max(1, int(w / (SEGMENT * (0.55 - 0.18 * m))))
        for e in range(1, etages):                      # trame : etoffage colore
            y = base - h * e / etages
            t.trait(g, y, d, y, m * 0.5, col)
        for c in range(1, colonnes):
            x = g + w * c / colonnes
            t.trait(x, base, x, top, m * 0.4, col)
        if rng.random() < 0.45:
            t.trait(cx, top, cx, top - SEGMENT * rng.uniform(0.4, 1.2), m * 0.8)
    t.trait(18, 205, 182, 205, m)


# ------------------------------------------------------------------ CREATURE
def creature(t, extension, m, graine, jour, etoffage=None):
    """
    Trois parties nommees, chacune avec son propre etoffage dans 0..1 :
        etoffage = {"tete": .., "corps": .., "membres": ..}
    Le corps est un contour ferme, d'ou une silhouette.
    """
    rng = random.Random(graine)
    col = teinte_du_moment(jour)
    e = etoffage or {"tete": 0.6, "corps": 0.6, "membres": 0.6}

    n = 7 + int(extension * 11)
    spine, angle, x, y = [], -0.55, 55, 165
    for i in range(n):
        f = i / max(n - 1, 1)
        lg = SEGMENT * 0.60 * (1.15 - 0.55 * f)
        angle += math.sin(i * 0.40) * 0.30 + 0.12 + rng.uniform(-0.05, 0.05)
        x, y = x + math.cos(angle) * lg, y + math.sin(angle) * lg
        spine.append((x, y, angle, 1.15 - 0.85 * f))

    # CORPS : contour ferme, largeur decroissante de la tete a la queue
    gauche, droite = [], []
    for (px, py, pa, ep) in spine:
        larg = SEGMENT * 0.34 * ep * (0.7 + 0.8 * e["corps"])
        gauche.append((px + math.cos(pa - 1.57) * larg, py + math.sin(pa - 1.57) * larg))
        droite.append((px + math.cos(pa + 1.57) * larg, py + math.sin(pa + 1.57) * larg))
    contour = gauche + droite[::-1]
    for i in range(len(contour)):
        t.trait(*contour[i], *contour[(i + 1) % len(contour)], m)
    pas = max(1, int(3 - e["corps"] * 2))               # segmentation interne
    for i in range(0, len(spine), pas):
        t.trait(*gauche[i], *droite[i], m * 0.55, col)

    # TETE
    hx, hy, ha, _ = spine[0]
    n_tete = 3 + int(e["tete"] * 6)
    for k in range(n_tete):
        a = ha + math.pi + (k - n_tete / 2) * (0.9 / max(n_tete, 1) * 2.2)
        r = SEGMENT * (0.45 + 0.75 * e["tete"])
        t.trait(hx, hy, hx + math.cos(a) * r, hy + math.sin(a) * r, m * 0.85, col)

    # MEMBRES : en peripherie, articules, jamais en travers du corps
    pas_m = max(1, int(3 - e["membres"] * 2))
    for i in range(1, len(spine) - 1, pas_m):
        px, py, pa, ep = spine[i]
        for s, bord in ((-1, gauche), (1, droite)):
            ax, ay = bord[i]
            a1 = pa + s * (1.15 + 0.2 * math.sin(i))
            p1 = SEGMENT * (0.5 + 0.85 * e["membres"]) * ep
            bx, by = ax + math.cos(a1) * p1, ay + math.sin(a1) * p1
            t.trait(ax, ay, bx, by, m * 0.8)
            a2 = a1 + s * rng.uniform(0.55, 1.0)
            t.trait(bx, by, bx + math.cos(a2) * p1 * 0.65,
                    by + math.sin(a2) * p1 * 0.65, m * 0.6, col)


# -------------------------------------------------------------------- planche
SAISONS = [("HIVER", 20), ("PRINTEMPS", 110), ("ETE", 200), ("AUTOMNE", 290)]


def planche():
    CW, CH, MG, TOP = 200, 200, 190, 56
    W, H = MG + CW * 4 + 20, TOP + CH * 3 + 16
    o = _entete(W, H)
    for j, (lab, _) in enumerate(SAISONS):
        o.append(f'<text x="{MG + j*CW + CW/2}" y="32" font-size="11" '
                 f'text-anchor="middle" letter-spacing="1.5">{lab}</text>')
    lignes = [
        ("Vegetal", lambda t, j, g: vegetal(t, 0.75, 0.8, g, j)),
        ("Ville", lambda t, j, g: architecture(t, 0.7, 0.85, g, j)),
        ("Creature", lambda t, j, g: creature(t, 0.7, 0.8, g, j)),
    ]
    for i, (nom, fn) in enumerate(lignes):
        y0 = TOP + i * CH
        o.append(f'<text x="20" y="{y0 + CH/2}" font-size="13" fill="#2c3230">{nom}</text>')
        for j, (_, jour) in enumerate(SAISONS):
            t = Toile()
            fn(t, jour, 500 + i * 13)
            o.append(t.svg(MG + j * CW, y0, CW, CH))
    o.append('</g></svg>')
    return "\n".join(o)


def planche_anatomie():
    """La creature, meme squelette, etoffages differents par partie."""
    CW, CH, MG, TOP = 200, 200, 190, 56
    cas = [("tete", {"tete": 1.0, "corps": 0.25, "membres": 0.25}),
           ("corps", {"tete": 0.25, "corps": 1.0, "membres": 0.25}),
           ("membres", {"tete": 0.25, "corps": 0.25, "membres": 1.0}),
           ("tout", {"tete": 0.9, "corps": 0.9, "membres": 0.9})]
    W, H = MG + CW * 4 + 20, TOP + CH + 16
    o = _entete(W, H)
    for j, (lab, et) in enumerate(cas):
        o.append(f'<text x="{MG + j*CW + CW/2}" y="32" font-size="11" '
                 f'text-anchor="middle" letter-spacing="1.5">{lab.upper()}</text>')
        t = Toile()
        creature(t, 0.7, 0.8, 777, 200, et)
        o.append(t.svg(MG + j * CW, TOP, CW, CH))
    o.append(f'<text x="20" y="{TOP + CH/2}" font-size="13" fill="#2c3230">'
             f'Etoffage par partie</text>')
    o.append('</g></svg>')
    return "\n".join(o)


if __name__ == "__main__":
    open("planche_couleur.svg", "w", encoding="utf-8").write(planche())
    open("planche_anatomie.svg", "w", encoding="utf-8").write(planche_anatomie())
    print("planches ecrites")
