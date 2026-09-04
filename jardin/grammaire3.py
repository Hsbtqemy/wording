"""
Grammaire v3 : les trois familles faibles.

Diagnostic : l'abstrait tient parce qu'il se superpose. Les trois autres
etaient des graphes acycliques — aucune ligne n'en croisait une autre — d'ou
l'impression de schema. On leur rend la capacite de se recouper.

  vegetal      : les branches se rejoignent (anastomose) + bouquets terminaux
  architecture : plusieurs tours a des profondeurs differentes, qui se masquent
  creature     : gradient tete-queue, membres articules, echine qui se replie
"""

from __future__ import annotations

import math
import random

from grammaire2 import Toile, SEGMENT, _entete


# ------------------------------------------------------------------- VEGETAL
def vegetal(t: Toile, extension, m, graine):
    rng = random.Random(graine)
    noeuds: list[tuple[float, float, int]] = []
    prof_max = 4 + int(extension * 3.2)

    def branche(x, y, angle, lg, prof, lignee):
        if prof <= 0 or lg < 3.0:
            # bouquet terminal : c'est lui qui donne la masse du feuillage
            n = 3 + int(m * 5)
            for i in range(n):
                a = angle + (i - n / 2) * 0.42 + rng.uniform(-0.1, 0.1)
                r = lg * (1.6 + 1.4 * m)
                t.trait(x, y, x + math.cos(a) * r, y + math.sin(a) * r, m * 0.7)
            return
        x2, y2 = x + math.cos(angle) * lg, y + math.sin(angle) * lg
        t.trait(x, y, x2, y2, m)
        noeuds.append((x2, y2, lignee))
        ouv = rng.uniform(0.34, 0.56)
        for s in (-1, 1):
            branche(x2, y2, angle + s * ouv, lg * rng.uniform(0.70, 0.80),
                    prof - 1, lignee * 2 + (s > 0))

    branche(100, 200, -math.pi / 2, SEGMENT * 1.7, prof_max, 1)

    # ANASTOMOSE : des branches issues de lignees differentes se rejoignent.
    # C'est ce seul ajout qui cree des boucles fermees, donc de la profondeur.
    seuil = SEGMENT * (0.55 + 0.5 * m)
    faits = 0
    for i, (x1, y1, l1) in enumerate(noeuds):
        for x2, y2, l2 in noeuds[i + 1:]:
            if l1 == l2 or faits > 40 * m + 6:
                continue
            d = math.hypot(x2 - x1, y2 - y1)
            if 6 < d < seuil and rng.random() < 0.45:
                t.trait(x1, y1, x2, y2, m * 0.6)
                faits += 1


# -------------------------------------------------------------- ARCHITECTURE
def architecture(t: Toile, extension, m, graine):
    rng = random.Random(graine)
    n_tours = 3 + int(extension * 4)
    # Les tours sont posees de l'arriere vers l'avant et se chevauchent en x :
    # c'est l'occlusion qui fait la silhouette de ville, pas l'empilement.
    ordre = sorted(range(n_tours), key=lambda k: rng.random())
    for rang, k in enumerate(ordre):
        h = SEGMENT * rng.uniform(2.2, 6.5) * (0.55 + extension * 0.7)
        w = SEGMENT * rng.uniform(0.85, 1.7)
        cx = 100 + (k - n_tours / 2) * SEGMENT * 1.15 + rng.uniform(-6, 6)
        base = 205 - rang * SEGMENT * 0.22
        g, d, top = cx - w / 2, cx + w / 2, base - h
        t.trait(g, base, g, top, m)
        t.trait(d, base, d, top, m)
        t.trait(g, top, d, top, m)
        t.trait(g, base, d, base, m)
        # trame de fenetres : la grandeur vient de la repetition d'une unite
        # petite, pas de deux ou trois refends
        etages = max(2, int(h / (SEGMENT * (0.62 - 0.22 * m))))
        colonnes = max(1, int(w / (SEGMENT * (0.55 - 0.18 * m))))
        for e in range(1, etages):
            y = base - h * e / etages
            t.trait(g, y, d, y, m * 0.55)
        for c in range(1, colonnes):
            x = g + w * c / colonnes
            t.trait(x, base, x, top, m * 0.45)
        if rng.random() < 0.45:                      # antenne, fleche
            t.trait(cx, top, cx, top - SEGMENT * rng.uniform(0.4, 1.2), m * 0.8)
    t.trait(20, 205, 180, 205, m)


# ------------------------------------------------------------------ CREATURE
def creature(t: Toile, extension, m, graine):
    rng = random.Random(graine)
    n = 8 + int(extension * 16)
    x, y, angle = 60, 170, -1.1
    # l'echine se replie sur elle-meme : la courbure accumulee depasse un tour
    courbure = 0.30 + extension * 0.22
    for i in range(n):
        f = i / max(n - 1, 1)
        taille = (1.25 - 0.75 * f)                   # gradient tete -> queue
        lg = SEGMENT * 0.62 * taille
        angle += math.sin(i * 0.42) * courbure + 0.16 + rng.uniform(-0.06, 0.06)
        x2, y2 = x + math.cos(angle) * lg, y + math.sin(angle) * lg
        t.trait(x, y, x2, y2, m)
        if i == 0:                                   # tete differenciee
            for k in range(7):
                a = angle + math.pi + (k - 3) * 0.34
                r = SEGMENT * 0.55 * (0.6 + 0.7 * m)
                t.trait(x, y, x + math.cos(a) * r, y + math.sin(a) * r, m * 0.9)
        elif i % 2 == 0:                             # membres ARTICULES
            for s in (-1, 1):
                a1 = angle + s * (1.05 + 0.25 * math.sin(i))
                p1 = lg * (1.5 + 0.9 * m) * taille
                xa, ya = x2 + math.cos(a1) * p1, y2 + math.sin(a1) * p1
                t.trait(x2, y2, xa, ya, m * 0.85)
                a2 = a1 + s * rng.uniform(0.6, 1.1)  # second segment : le coude
                p2 = p1 * rng.uniform(0.55, 0.8)
                t.trait(xa, ya, xa + math.cos(a2) * p2, ya + math.sin(a2) * p2, m * 0.7)
        x, y = x2, y2


RENDUS = {"Vegetal / anastomose": vegetal,
          "Architecture / occlusion": architecture,
          "Creature / articulation": creature}


def planche():
    CW, CH, MG, TOP = 210, 210, 210, 56
    W, H = MG + CW * 3 + 20, TOP + CH * 3 + 16
    o = _entete(W, H)
    for j, lab in enumerate(("JEUNE", "MOYEN", "ETENDU")):
        o.append(f'<text x="{MG + j*CW + CW/2}" y="32" font-size="11" '
                 f'text-anchor="middle" letter-spacing="1.5">{lab}</text>')
    for i, (nom, fn) in enumerate(RENDUS.items()):
        y0 = TOP + i * CH
        o.append(f'<text x="20" y="{y0 + CH/2}" font-size="13" fill="#2c3230">{nom}</text>')
        for j, (e, mm) in enumerate(((0.15, 0.35), (0.55, 0.6), (1.0, 0.85))):
            t = Toile()
            fn(t, e, mm, 400 + i * 31 + j * 7)
            o.append(t.svg(MG + j * CW, y0, CW, CH))
    o.append('</g></svg>')
    return "\n".join(o)


if __name__ == "__main__":
    open("planche_v3.svg", "w", encoding="utf-8").write(planche())
    print("planche_v3.svg ecrit")
