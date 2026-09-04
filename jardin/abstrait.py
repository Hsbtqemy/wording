"""
L'abstrait, revu.

Probleme de la v2 : l'abstrait etait un pavage hexagonal regulier, donc la
famille du refus de classement avait la regle la plus rigide des quatre.

Correction : sa geometrie n'est plus fixee, elle est LUE sur le vecteur de
traits. Ce n'est pas de l'aleatoire — la graine vient du document, donc la
forme est stable a la reouverture — mais chaque texte produit une figure
differente parce qu'il fournit des nombres differents.

  diversite        -> nombre de facettes
  ponctuation_rare -> irregularite des sommets
  rythme           -> torsion d'un anneau au suivant
  subordination    -> etoilement (sommets pousses vers l'interieur)
"""

from __future__ import annotations

import hashlib
import math
import random

from grammaire2 import Toile, TRAIT, NOEUD, FOND, SEGMENT, _entete


def graine_du_document(nom: str) -> int:
    """La graine vient du texte, jamais de l'horloge. C'est ce qui garantit
    qu'on retrouve la meme figure a chaque ouverture du fichier."""
    return int(hashlib.blake2s(nom.encode(), digest_size=4).hexdigest(), 16)


def paver(t: Toile, cx, cy, anneaux, m, traits: dict, graine: int):
    rng = random.Random(graine)

    cotes = 5 + int(traits["diversite"] * 4.4)          # 5 a 9 facettes
    irreg = 0.06 + traits["ponctuation_rare"] * 0.34    # jitter des sommets
    torsion = traits["rythme"] * 0.62                   # decalage par anneau
    etoile = traits["subordination"] * 0.42             # sommets rentrants

    # Jitter tire une fois par sommet, puis reutilise sur tous les anneaux :
    # les facettes restent alignees radialement au lieu de partir en bouillie.
    jitter = [rng.uniform(1 - irreg, 1 + irreg) for _ in range(cotes)]
    rentrant = [1 - etoile if k % 2 else 1.0 for k in range(cotes)]

    prec = None
    for a in range(1, anneaux + 1):
        r = SEGMENT * 0.58 * a
        depart = a * torsion
        pts = []
        for k in range(cotes):
            ang = 2 * math.pi * k / cotes + depart
            rr = r * jitter[k] * rentrant[k]
            pts.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr))

        for k in range(cotes):
            t.trait(*pts[k], *pts[(k + 1) % cotes], m)

        if prec:
            for k in range(cotes):
                t.trait(*prec[k], *pts[k], m * 0.8)
                t.noeud(*pts[k], m)
                if m > 0.45:
                    mx = ((prec[k][0] + pts[k][0]) / 2, (prec[k][1] + pts[k][1]) / 2)
                    kk = (k + 1) % cotes
                    nx = ((prec[kk][0] + pts[kk][0]) / 2, (prec[kk][1] + pts[kk][1]) / 2)
                    t.trait(*mx, *nx, m * 0.5)
        else:
            # Anneau initial : on le subdivise tout de suite, pour qu'un abstrait
            # jeune soit deja une facette et non un polygone nu.
            for k in range(0, cotes, 2):
                t.trait(cx, cy, *pts[k], m * 0.55)
        prec = pts


def figure(nom_doc: str, traits: dict, extension=0.6, maturite=0.35) -> Toile:
    t = Toile()
    g = graine_du_document(nom_doc)
    paver(t, 100, 110, 1 + int(extension * 3.4), maturite, traits, g)
    return t


# Quatre profils de texte plausibles, tres differents les uns des autres.
DOCUMENTS = {
    "chapitre_01": dict(diversite=0.20, ponctuation_rare=0.15, rythme=0.20, subordination=0.10),
    "chapitre_02": dict(diversite=0.55, ponctuation_rare=0.70, rythme=0.35, subordination=0.60),
    "chapitre_03": dict(diversite=0.85, ponctuation_rare=0.30, rythme=0.80, subordination=0.25),
    "chapitre_04": dict(diversite=1.00, ponctuation_rare=0.95, rythme=0.55, subordination=0.90),
}


def planche():
    CW, CH, MG, TOP = 200, 200, 130, 56
    W, H = MG + CW * 4 + 20, TOP + CH * 2 + 20
    o = _entete(W, H)
    for j, nom in enumerate(DOCUMENTS):
        o.append(f'<text x="{MG + j*CW + CW/2}" y="32" font-size="11" '
                 f'text-anchor="middle" letter-spacing="1.5">{nom.upper()}</text>')
    for i, (lab, ext, mat) in enumerate((("JEUNE", 0.15, 0.20), ("ETENDU", 1.0, 0.55))):
        y0 = TOP + i * CH
        o.append(f'<text x="20" y="{y0 + CH/2}" font-size="11" letter-spacing="1.5">{lab}</text>')
        for j, (nom, tr) in enumerate(DOCUMENTS.items()):
            o.append(figure(nom, tr, ext, mat).svg(MG + j * CW, y0, CW, CH))
    o.append('</g></svg>')
    return "\n".join(o)


def test_determinisme():
    """La meme figure doit ressortir a chaque appel, sinon le fichier ment."""
    print("Determinisme (3 rendus successifs du meme document) :")
    for nom, tr in list(DOCUMENTS.items())[:2]:
        sigs = []
        for _ in range(3):
            t = figure(nom, tr)
            sigs.append(hashlib.blake2s(
                "".join(f"{s[0]:.2f},{s[1]:.2f}" for s in t.segments).encode(),
                digest_size=4).hexdigest())
        etat = "identique" if len(set(sigs)) == 1 else "INSTABLE"
        print(f"  {nom:<14} {sigs[0]}  x3  -> {etat}")
    print("\nVariete (documents differents, memes reglages) :")
    vus = {}
    for nom, tr in DOCUMENTS.items():
        t = figure(nom, tr)
        vus[nom] = (len(t.segments), 5 + int(tr["diversite"] * 4.4))
    for nom, (n, c) in vus.items():
        print(f"  {nom:<14} {c} facettes, {n:>3} segments")


if __name__ == "__main__":
    open("planche_abstrait.svg", "w", encoding="utf-8").write(planche())
    print("planche_abstrait.svg ecrit\n")
    test_determinisme()
