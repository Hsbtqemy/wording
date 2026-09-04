"""
La grammaire graphique, en un seul endroit.

Le code avait diverge en versions paralleles et aucune n'etait complete :
Toile redefinie quatre fois avec des signatures incompatibles, PALETTES en
deux versions (trois tons en v5, cinq en v6), le vegetal et l'architecture
restes en v4, la creature en v5, la couleur en v6. Il n'existait aucun module
capable de dessiner les quatre familles a l'etat des decisions — on aurait
porte en JavaScript un assemblage que personne n'avait jamais vu en entier.

Ce fichier est cet etat. Ce qu'il retient de chaque version :

    v2   la primitive segment, les noeuds tardifs
    v3   la superposition : anastomose, occlusion, articulation
    v4   la couleur par date, l'architecture a trames, le contour ferme
    v5   les trois curseurs de la creature agissant sur la GEOMETRIE
    v6   cinq tons par palette, la palette de nuit reellement distincte
    +    le fondu de 12 jours des deux cotes d'une frontiere (decision 9,
         decide en v5 et perdu en v6 : v6 n'avait plus aucun fondu)
    +    le plafond GLOBAL du feuillage (point ouvert 3)
    +    l'abstrait colore comme les trois autres (il ne l'etait pas)

Regle qui tient tout (decision 9) : la couleur ne touche jamais la structure,
uniquement l'etoffage. Le squelette reste a l'encre dans les quatre familles.
C'est cette seule regle qui preserve l'unite etablie a la decision 8.
"""

from __future__ import annotations

import hashlib
import math
import random

TRAIT = "#2c3230"
FOND = "#faf8f4"
EPAISSEUR = 1.5
SEGMENT = 26.0
SAUT = chr(10)

# --------------------------------------------------------------------------
# Couleur (decision 9)
# --------------------------------------------------------------------------
# Cinq tons par palette : une plante de printemps porte plusieurs verts sans
# que rien ne devienne aleatoire — meme document, meme graine, meme figure.
PALETTES = {
    "hiver":     ["#5b7a8c", "#8ba3ad", "#43596b", "#6e8fa0", "#9fb3ba"],
    "printemps": ["#6d9450", "#96b56a", "#4f7a3f", "#7fa85e", "#adc47f"],
    "ete":       ["#c08a3e", "#d4aa5c", "#a86f2d", "#caa04e", "#b8823a"],
    "automne":   ["#a3542f", "#bd7448", "#7d3d22", "#b0603a", "#8e4a28"],
    # La palette de nuit de la v5 etait un bleu-gris a deux doigts de l'hiver :
    # sur planche, "3H DU MATIN" et "HIVER" etaient indiscernables, et l'easter
    # egg ressemblait a une decoloration. Le violet de la v6 n'appartient a
    # aucune saison, ce qui est exactement ce qu'on lui demande.
    "nuit":      ["#8d84c4", "#a99ede", "#7a6fb0", "#9a90d2", "#b8aeea"],
}

# Debut de chaque saison, en jours. L'hiver enjambe la fin de l'annee.
SAISONS = [("printemps", 80, 172), ("ete", 172, 264),
           ("automne", 264, 355), ("hiver", 355, 80 + 365)]
FONDU = 12          # jours de transition, DE PART ET D'AUTRE d'une frontiere
HEURE_NUIT = (2, 5)


def _saison(jour: int):
    """Renvoie (nom, debut, fin) en tenant compte de l'enjambement d'annee."""
    j = jour % 365
    for nom, debut, fin in SAISONS:
        if debut <= j < fin:
            return nom, debut, fin
    return "hiver", 355, 80 + 365          # janvier : j < 80


def _melange(c1: str, c2: str, f: float) -> str:
    a = tuple(int(c1[i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(c2[i:i + 2], 16) for i in (1, 3, 5))
    return "#" + "".join(f"{int(a[i] + (b[i] - a[i]) * f):02x}" for i in range(3))


def _suivante(nom: str) -> str:
    noms = [s[0] for s in SAISONS]
    return noms[(noms.index(nom) + 1) % len(noms)]


def _precedente(nom: str) -> str:
    noms = [s[0] for s in SAISONS]
    return noms[(noms.index(nom) - 1) % len(noms)]


def palette(jour: int, ton: int = 0, nuit: bool = False) -> str:
    """
    Le ton numero `ton` de la palette du jour donne.

    Le fondu court sur FONDU jours DES DEUX COTES de chaque frontiere : la v5
    ne le posait que du cote tardif et plafonnait a 50 %, la v6 l'avait perdu.
    Une plante a cheval sur deux saisons doit porter les deux, sinon une date
    a un jour d'ecart change brutalement de palette.
    """
    ton %= 5
    if nuit:
        return PALETTES["nuit"][ton]

    j = jour % 365
    nom, debut, fin = _saison(jour)
    if nom == "hiver" and j < 80:
        j += 365                            # on se replace dans la fenetre

    couleur = PALETTES[nom][ton]
    if j - debut < FONDU:
        f = 0.5 * (1 - (j - debut) / FONDU)
        return _melange(couleur, PALETTES[_precedente(nom)][ton], f)
    if fin - j < FONDU:
        f = 0.5 * (1 - (fin - j) / FONDU)
        return _melange(couleur, PALETTES[_suivante(nom)][ton], f)
    return couleur


class Teinte:
    """
    Le contexte chromatique d'un plant.

    Deux choses y sont resolues.

    LES VRAIES DATES. La v4 donnait a chaque tour de ville la date
    `jour + rang x 47` : un decalage invente, donc une ville dont les tours
    affichaient des saisons qui n'ont jamais eu lieu, alors que la decision 9
    fait porter la teinte par la date d'ecriture. Ici les dates viennent du
    plant — {jour: mots} — et un tour tire la sienne dans cette distribution,
    ponderee par les mots. Un chapitre commence en fevrier et fini en mai
    porte reellement les deux.

    L'ARBITRAGE LAISSE OUVERT AU POINT 9. « Faire porter la teinte par la
    date, c'est renoncer a ce qu'elle porte le texte. Pas les deux sur la meme
    variable. » Ce n'est vrai que si la couleur n'a qu'une variable. La date
    garde la TEINTE ; le texte prend le NOMBRE DE TONS tires dans la palette.
    Un segment lexicalement riche deploie les cinq verts du printemps, un
    segment monotone n'en tire qu'un. La saison reste lisible, la richesse du
    texte devient une richesse chromatique, et aucune variable ne porte deux
    choses.
    """

    def __init__(self, dates=None, nuit=False, diversite=0.5):
        self.dates = list(dates) if dates else [(200, 1)]
        self.nuit = bool(nuit)
        self.n_tons = 1 + int(min(1.0, max(0.0, diversite)) * 4)   # 1 a 5
        self._poids, cumul = [], 0
        for _, poids in self.dates:
            cumul += max(1, poids)
            self._poids.append(cumul)
        self._total = cumul

    @classmethod
    def du_jour(cls, jour=200, heure=14, diversite=0.5):
        """Raccourci pour les planches : un plant ecrit d'un seul jet."""
        return cls([(jour, 1)], HEURE_NUIT[0] <= heure < HEURE_NUIT[1], diversite)

    def jour(self, rng) -> int:
        """Une vraie date du plant, tiree au poids des mots ecrits ce jour-la."""
        cible = rng.randrange(self._total)
        for i, seuil in enumerate(self._poids):
            if cible < seuil:
                return self.dates[i][0]
        return self.dates[-1][0]

    def ton(self, rng, jour=None) -> str:
        j = self.jour(rng) if jour is None else jour
        return palette(j, rng.randrange(self.n_tons), self.nuit)


def graine_du_document(nom: str) -> int:
    """La graine vient du document, jamais de l'horloge : c'est ce qui garantit
    qu'on retrouve la meme figure a chaque ouverture du fichier."""
    return int(hashlib.blake2s(nom.encode("utf-8"), digest_size=4).hexdigest(), 16)


# --------------------------------------------------------------------------
# La primitive
# --------------------------------------------------------------------------
class Toile:
    """
    Un segment, et rien d'autre. L'unite des quatre familles ne vient pas d'un
    style plaque par-dessus mais de cette primitive partagee (decision 8).
    """

    def __init__(self):
        self.segments: list = []
        self.noeuds: list = []
        # Cadre impose. Sans lui, une figure qui se revele progressivement est
        # centree sur ce qui est DEJA visible : chaque element nouveau recadre
        # l'ensemble et fait bouger tout ce qui etait deja trace.
        self.cadre = None

    def trait(self, x1, y1, x2, y2, m=0.0, col=None):
        self.segments.append((x1, y1, x2, y2, m, col or TRAIT))

    def noeud(self, x, y, m, col=None):
        # Tardifs et petits : en v1 ils devenaient une rougeole qui ecrasait
        # tout le reste.
        if m > 0.55:
            self.noeuds.append((x, y, m, col or TRAIT))

    def bbox(self):
        xs = [v for s in self.segments for v in (s[0], s[2])]
        ys = [v for s in self.segments for v in (s[1], s[3])]
        return (min(xs), min(ys), max(xs), max(ys)) if xs else (0, 0, 1, 1)

    def pose(self, x, y_base, echelle) -> str:
        """
        Pose la figure a un endroit choisi, base posee sur (x, y_base).

        svg() cadre dans une case — c'est ce qu'il faut pour une planche, pas
        pour un paysage, ou chaque plant doit tenir sa place et son echelle
        par rapport aux autres.
        """
        x0, y0, x1, y1 = self.cadre or self.bbox()
        k = echelle
        ox = x - (x0 + x1) / 2 * k
        oy = y_base - y1 * k
        out = [f'<g transform="translate({ox:.1f},{oy:.1f}) scale({k:.3f})">']
        for a, b, c, d, m, col in self.segments:
            e = EPAISSEUR * (1 + 1.7 * m) / max(k, 0.35)
            out.append(f'<line x1="{a:.1f}" y1="{b:.1f}" x2="{c:.1f}" y2="{d:.1f}" '
                       f'stroke="{col}" stroke-width="{e:.2f}" stroke-linecap="round"/>')
        for px, py, m, col in self.noeuds:
            r = (1.0 + 1.8 * m) / max(k, 0.35)
            out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r:.2f}" '
                       f'fill="{col}" opacity="{0.35 + 0.5 * m:.2f}"/>')
        return "".join(out) + "</g>"

    def hauteur(self):
        x0, y0, x1, y1 = self.cadre or self.bbox()
        return max(y1 - y0, 1)

    def largeur(self):
        x0, y0, x1, y1 = self.cadre or self.bbox()
        return max(x1 - x0, 1)

    def svg(self, cx, cy, cw, ch) -> str:
        x0, y0, x1, y1 = self.cadre or self.bbox()
        w, h = max(x1 - x0, 1), max(y1 - y0, 1)
        k = min(1.0, (cw - 26) / w, (ch - 26) / h)
        ox, oy = cx + cw / 2 - (x0 + w / 2) * k, cy + ch / 2 - (y0 + h / 2) * k
        out = [f'<g transform="translate({ox:.1f},{oy:.1f}) scale({k:.3f})">']
        for a, b, c, d, m, col in self.segments:
            e = EPAISSEUR * (1 + 1.7 * m) / max(k, 0.35)
            out.append(f'<line x1="{a:.1f}" y1="{b:.1f}" x2="{c:.1f}" y2="{d:.1f}" '
                       f'stroke="{col}" stroke-width="{e:.2f}" stroke-linecap="round"/>')
        for x, y, m, col in self.noeuds:
            r = (1.0 + 1.8 * m) / max(k, 0.35)
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" '
                       f'fill="{col}" opacity="{0.35 + 0.5 * m:.2f}"/>')
        return "".join(out) + "</g>"


# --------------------------------------------------------------------------
# Vegetal — il se ramifie
# --------------------------------------------------------------------------
# Plafond GLOBAL du feuillage. Le correctif de la v4 bornait chaque bouquet
# (3 + m*3 traits), mais le NOMBRE de bouquets croit en 2^profondeur : le
# feuillage densifiait quand meme et fusionnait en aplat, masquant l'anastomose
# qu'on venait d'ajouter. Meme remede que les cycles de 5 000 mots — plafonner
# le total et le repartir, jamais l'unite locale.
BUDGET_FEUILLAGE = 210

# --------------------------------------------------------------------------
# Ce que le texte dit de la FORME (et non de la couleur ni de la taille).
#
# Les trois curseurs de la creature et la geometrie de l'abstrait existaient
# depuis les v4-v5, mais rien ne les alimentait : `etoffage` et `traits`
# tombaient sur leurs valeurs par defaut a chaque appel. Toutes les creatures
# etaient donc la meme creature, tous les abstraits le meme cristal — un
# paysage de vingt-sept plants n'aurait montre que quatre formes repetees, ce
# qui aurait ruine la decision 7 (un paysage, pas un fourre-tout) sans qu'on
# comprenne pourquoi.
#
# Chaque correspondance ci-dessous doit dire quelque chose de vrai. Ce ne sont
# pas des branchements arbitraires : c'est la ou le texte devient anatomie.
# --------------------------------------------------------------------------
TRAITS_NEUTRES = {
    "longueur": 0.5, "rythme": 0.5, "subordination": 0.5, "regularite": 0.5,
    "structure": 0.5, "dialogue": 0.5, "interrogation": 0.5,
    "diversite": 0.5, "ponctuation_rare": 0.5,
}


def _traits(traits):
    t = dict(TRAITS_NEUTRES)
    if traits:
        t.update({k: v for k, v in traits.items() if k in TRAITS_NEUTRES})
    return t


def vegetal(t: Toile, extension, maturite, graine, teinte=None,
            traits=None):
    rng = random.Random(graine)
    m = maturite
    tt = teinte or Teinte.du_jour()
    tr = _traits(traits)
    # Une phrase qui se subordonne se ramifie : la subordination ouvre l'angle.
    # Un texte regulier fait un arbre symetrique ; un texte irregulier penche.
    ouverture = 0.26 + tr["subordination"] * 0.42
    dissymetrie = (1.0 - tr["regularite"]) * 0.30
    # Des phrases longues font de longues entre-noeuds.
    entre_noeuds = 0.72 + tr["longueur"] * 0.34
    prof_max = 4 + int(extension * 3.0)
    par_bouquet = max(1, min(3 + int(m * 3), BUDGET_FEUILLAGE // (2 ** prof_max)))
    noeuds = []

    def branche(x, y, angle, lg, prof, lignee):
        if prof <= 0 or lg < 3.0:
            for i in range(par_bouquet):
                a = angle + (i - par_bouquet / 2) * 0.40 + rng.uniform(-0.1, 0.1)
                r = lg * (1.3 + 0.8 * m)
                t.trait(x, y, x + math.cos(a) * r, y + math.sin(a) * r,
                        m * 0.55, tt.ton(rng))
            return
        x2, y2 = x + math.cos(angle) * lg, y + math.sin(angle) * lg
        t.trait(x, y, x2, y2, m)                    # structure : jamais coloree
        t.noeud(x2, y2, m, tt.ton(rng))
        noeuds.append((x2, y2, lignee))
        ouv = ouverture * rng.uniform(0.85, 1.15)
        for s in (-1, 1):
            biais = 1.0 + s * dissymetrie
            branche(x2, y2, angle + s * ouv * biais,
                    lg * entre_noeuds * rng.uniform(0.94, 1.06),
                    prof - 1, lignee * 2 + (s > 0))

    # Le port de l'arbre : inclinaison du tronc et vigueur, tires sur la
    # graine du document. Deux plants du meme texte doivent rester deux
    # arbres, pas deux exemplaires du meme arbre.
    branche(100, 200, -math.pi / 2 + rng.uniform(-0.16, 0.16),
            SEGMENT * (1.4 + tr["longueur"] * 0.7) * rng.uniform(0.85, 1.18),
            prof_max, 1)

    # ANASTOMOSE : des branches de lignees differentes se rejoignent. C'est ce
    # seul ajout qui cree des boucles fermees, donc de la profondeur — sans lui
    # le vegetal est un graphe acyclique et ressemble a un schema.
    seuil = SEGMENT * (0.5 + 0.45 * m)
    faits = 0
    for i, (x1, y1, l1) in enumerate(noeuds):
        for x2, y2, l2 in noeuds[i + 1:]:
            if l1 == l2 or faits > 30 * m + 6:
                continue
            if 6 < math.hypot(x2 - x1, y2 - y1) < seuil and rng.random() < 0.45:
                t.trait(x1, y1, x2, y2, m * 0.55)
                faits += 1


# --------------------------------------------------------------------------
# Architecture — il s'empile
# --------------------------------------------------------------------------
def architecture(t: Toile, extension, maturite, graine, teinte=None,
                 traits=None):
    rng = random.Random(graine)
    m = maturite
    tt = teinte or Teinte.du_jour()
    tr = _traits(traits)
    # Plus le texte est decoupe en titres et en listes, plus la ville a de
    # batiments distincts. Plus il est regulier, plus ils s'alignent en
    # hauteur — un rapport tres structure fait une ville de barres, un texte
    # inegal fait des tours et des maisons.
    n_tours = 2 + int(extension * 3) + int(tr["structure"] * 3)
    ecart_hauteur = 0.25 + (1.0 - tr["regularite"]) * 1.10
    hauteur_base = 1.6 + tr["longueur"] * 3.4
    # Posees de l'arriere vers l'avant et chevauchantes : c'est l'occlusion qui
    # fait la silhouette de ville, pas l'empilement.
    ordre = sorted(range(n_tours), key=lambda k: rng.random())
    for rang, k in enumerate(ordre):
        # Chaque tour a sa propre date : un chapitre ecrit l'hiver et un autre
        # l'ete ne s'eclairent pas de la meme couleur.
        col = tt.ton(rng)
        h = SEGMENT * hauteur_base * rng.uniform(1.0, 1.0 + ecart_hauteur)             * (0.55 + extension * 0.7)
        w = SEGMENT * rng.uniform(0.85, 1.7)
        cx = 100 + (k - n_tours / 2) * SEGMENT * 1.15 + rng.uniform(-6, 6)
        base = 205 - rang * SEGMENT * 0.22
        g, d, top = cx - w / 2, cx + w / 2, base - h
        for seg in ((g, base, g, top), (d, base, d, top),
                    (g, top, d, top), (g, base, d, base)):
            t.trait(*seg, m)                          # structure
        # La grandeur vient de la repetition d'une unite petite, pas de deux
        # ou trois refends.
        etages = max(2, int(h / (SEGMENT * (0.62 - 0.22 * m))))
        colonnes = max(1, int(w / (SEGMENT * (0.55 - 0.18 * m))))
        for e in range(1, etages):                    # trame : etoffage colore
            y = base - h * e / etages
            t.trait(g, y, d, y, m * 0.5, col)
        for c in range(1, colonnes):
            x = g + w * c / colonnes
            t.trait(x, base, x, top, m * 0.4, col)
        t.noeud(g, top, m, col)
        t.noeud(d, top, m, col)
        if rng.random() < 0.45:                       # antenne, fleche
            t.trait(cx, top, cx, top - SEGMENT * rng.uniform(0.4, 1.2), m * 0.8)
    t.trait(18, 205, 182, 205, m)


# --------------------------------------------------------------------------
# Creature — il s'enchaine
# --------------------------------------------------------------------------
def creature(t: Toile, extension, maturite, graine, teinte=None,
             traits=None, etoffage=None):
    """
    Trois parties nommees. Les curseurs agissent sur la GEOMETRIE — largeur du
    corps, taille de la tete, longueur des membres — et pas seulement sur la
    densite de traits : en v4 seul le curseur membres changeait la silhouette.

    Le corps est un contour FERME. Sans lui, la creature v3 n'avait plus de
    silhouette et devenait illisible : la superposition doit rester
    hierarchique, le desordre n'est pas l'originalite.
    """
    rng = random.Random(graine)
    m = maturite
    tt = teinte or Teinte.du_jour()
    tr = _traits(traits)
    # La tete est ce qui parle : elle suit le dialogue.
    # Le corps est ce qui porte : des phrases longues font une bete massive.
    # Les membres sont ce qui articule : c'est le rythme, l'irregularite.
    e = etoffage or {"tete": 0.15 + tr["dialogue"] * 0.85,
                     "corps": 0.12 + tr["longueur"] * 0.80,
                     "membres": 0.12 + tr["rythme"] * 0.80}

    # L'epine doit varier d'un plant a l'autre. En v5 elle etait
    # `sin(i*0.40)*0.30 + 0.12` a un bruit de 0,05 pres : la graine ne
    # changeait presque rien, et six creatures cote a cote dans un paysage
    # etaient six fois la meme bete. L'architecture, elle, variait beaucoup —
    # parce que ses hauteurs sont tirees. On donne a la creature la meme
    # latitude : c'est la graine du document, donc la figure reste stable a
    # la reouverture du fichier.
    courbure = rng.uniform(0.17, 0.44)
    phase = rng.uniform(0.0, 6.283)
    avance = rng.uniform(0.04, 0.24)
    cadence = rng.uniform(0.28, 0.58)
    n = 7 + int(extension * 11)
    spine, angle, x, y = [], rng.uniform(-1.1, 0.1), 55, 165
    for i in range(n):
        f = i / max(n - 1, 1)
        lg = SEGMENT * 0.60 * (1.15 - 0.55 * f)
        angle += math.sin(i * cadence + phase) * courbure + avance             + rng.uniform(-0.05, 0.05)
        x, y = x + math.cos(angle) * lg, y + math.sin(angle) * lg
        spine.append((x, y, angle, 1.15 - 0.85 * f))

    # CORPS : de gracile a massif, facteur 5 entre les extremes.
    ampleur = 0.16 + e["corps"] * 0.68
    gauche, droite = [], []
    for (px, py, pa, ep) in spine:
        larg = SEGMENT * ampleur * ep
        gauche.append((px + math.cos(pa - 1.57) * larg, py + math.sin(pa - 1.57) * larg))
        droite.append((px + math.cos(pa + 1.57) * larg, py + math.sin(pa + 1.57) * larg))
    contour = gauche + droite[::-1]
    for i in range(len(contour)):
        t.trait(*contour[i], *contour[(i + 1) % len(contour)], m)   # structure
    pas = max(1, int(3 - e["corps"] * 2))
    for i in range(0, len(spine), pas):
        t.trait(*gauche[i], *droite[i], m * 0.55, tt.ton(rng))

    # TETE : le rayon suit le curseur, pas seulement le nombre d'appendices.
    hx, hy, ha, _ = spine[0]
    rayon = SEGMENT * (0.22 + e["tete"] * 1.15)
    n_tete = 3 + int(e["tete"] * 6)
    for k in range(n_tete):
        a = ha + math.pi + (k - n_tete / 2) * (1.9 / max(n_tete, 1))
        t.trait(hx, hy, hx + math.cos(a) * rayon, hy + math.sin(a) * rayon,
                m * 0.85, tt.ton(rng))
    if e["tete"] > 0.5:                               # calotte : ferme la tete
        pts = [(hx + math.cos(ha + math.pi + (k - 3) * 0.32) * rayon * 0.8,
                hy + math.sin(ha + math.pi + (k - 3) * 0.32) * rayon * 0.8)
               for k in range(7)]
        for i in range(len(pts) - 1):
            t.trait(*pts[i], *pts[i + 1], m * 0.7)

    # MEMBRES : en peripherie, articules, jamais en travers du corps.
    #
    # Bornes RELATIVEMENT A LA LARGEUR DU CORPS. Une longueur absolue donne
    # des pattes de meme taille sur une bete gracile et sur une bete massive :
    # la gracile devient une araignee, la massive un mille-pattes ras. En
    # proportion du corps, la creature garde ses proportions quel que soit le
    # reglage — et le curseur membres ne fait plus que ce qu'on lui demande,
    # allonger, sans changer l'espece au passage.
    largeur_corps = SEGMENT * ampleur
    pas_m = max(1, int(3 - e["membres"] * 2))
    for i in range(1, len(spine) - 1, pas_m):
        px, py, pa, ep = spine[i]
        for s, bord in ((-1, gauche), (1, droite)):
            ax, ay = bord[i]
            a1 = pa + s * (1.15 + 0.2 * math.sin(i))
            p1 = largeur_corps * (0.8 + 3.2 * e["membres"]) * ep
            bx, by = ax + math.cos(a1) * p1, ay + math.sin(a1) * p1
            t.trait(ax, ay, bx, by, m * 0.8)
            a2 = a1 + s * rng.uniform(0.55, 1.0)
            t.trait(bx, by, bx + math.cos(a2) * p1 * 0.65,
                    by + math.sin(a2) * p1 * 0.65, m * 0.6,
                    tt.ton(rng))
            t.noeud(bx, by, m, tt.ton(rng))


# --------------------------------------------------------------------------
# Abstrait — il se pave
# --------------------------------------------------------------------------
def abstrait(t: Toile, extension, maturite, graine, teinte=None,
             traits=None):
    """
    Sa geometrie n'est pas fixee : elle est LUE sur le vecteur de traits. Sans
    cela, la famille du refus de classement aurait la regle la plus rigide des
    quatre — un pavage hexagonal regulier.

        diversite        -> nombre de facettes
        ponctuation_rare -> irregularite des sommets
        rythme           -> torsion d'un anneau au suivant
        subordination    -> etoilement (sommets pousses vers l'interieur)
    """
    rng = random.Random(graine)
    m = maturite
    tt = teinte or Teinte.du_jour()
    tr = _traits(traits)

    cotes = 5 + int(tr["diversite"] * 4.4)              # 5 a 9 facettes
    irreg = 0.06 + tr["ponctuation_rare"] * 0.34
    torsion = tr["rythme"] * 0.62
    etoile = tr["subordination"] * 0.42

    # Jitter tire une fois par sommet puis reutilise sur tous les anneaux : les
    # facettes restent alignees radialement au lieu de partir en bouillie.
    jitter = [rng.uniform(1 - irreg, 1 + irreg) for _ in range(cotes)]
    rentrant = [1 - etoile if k % 2 else 1.0 for k in range(cotes)]

    anneaux = 1 + int(extension * 3.4)
    prec = None
    for a in range(1, anneaux + 1):
        r = SEGMENT * 0.58 * a
        depart = a * torsion
        pts = []
        for k in range(cotes):
            ang = 2 * math.pi * k / cotes + depart
            rr = r * jitter[k] * rentrant[k]
            pts.append((100 + math.cos(ang) * rr, 110 + math.sin(ang) * rr))
        for k in range(cotes):
            t.trait(*pts[k], *pts[(k + 1) % cotes], m)     # structure
        if prec:
            for k in range(cotes):
                t.trait(*prec[k], *pts[k], m * 0.8)        # structure
                t.noeud(*pts[k], m, tt.ton(rng))
                if m > 0.45:                               # etoffage : colore
                    mx = ((prec[k][0] + pts[k][0]) / 2, (prec[k][1] + pts[k][1]) / 2)
                    kk = (k + 1) % cotes
                    nx = ((prec[kk][0] + pts[kk][0]) / 2,
                          (prec[kk][1] + pts[kk][1]) / 2)
                    t.trait(*mx, *nx, m * 0.5, tt.ton(rng))
        else:
            # Anneau initial subdivise tout de suite : un abstrait jeune doit
            # etre une facette, pas un polygone nu.
            for k in range(0, cotes, 2):
                t.trait(100, 110, *pts[k], m * 0.55, tt.ton(rng))
        prec = pts


FAMILLES = {
    "vegetal": ("Vegetal / ramifier", vegetal),
    "architecture": ("Architecture / empiler", architecture),
    "creature": ("Creature / enchainer", creature),
    "abstrait": ("Abstrait / paver", abstrait),
}


def dessiner(famille, extension, maturite, graine, teinte=None, traits=None,
             **kw):
    t = Toile()
    FAMILLES[famille][1](t, extension, maturite, graine, teinte, traits, **kw)
    return t


def depuis_plant(plant: dict, graine: int, **kw) -> Toile:
    """
    Dessine un plant a partir de l'etat rendu par paysage.Paysage.etat().

    C'est le seul point de contact entre l'etat et le rendu : tout ce que le
    dessin sait du texte passe par ici.
    """
    traits = plant.get("traits") or {}
    teinte = Teinte(plant["dates"], plant["nuit"],
                    traits.get("diversite", 0.5))
    return dessiner(plant["famille"] or "abstrait",
                    plant["extension"], plant["maturite"], graine, teinte,
                    traits, **kw)


# --------------------------------------------------------------------------
# Planches
# --------------------------------------------------------------------------
def _entete(W, H):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
            f'width="100%">',
            f'<rect width="{W}" height="{H}" fill="{FOND}"/>',
            '<g font-family="Georgia, serif" fill="#6b6560">']


def planche_etat():
    """Les quatre familles, deux axes, a l'etat des decisions."""
    CW, CH, MG, TOP = 200, 200, 200, 56
    W, H = MG + CW * 3 + 20, TOP + CH * 4 + 16
    o = _entete(W, H)
    cas = (("JEUNE / BRUT", 0.15, 0.15), ("MOYEN / REPRIS", 0.55, 0.55),
           ("ETENDU / ABOUTI", 1.0, 0.92))
    for j, (lab, _, _) in enumerate(cas):
        o.append(f'<text x="{MG + j*CW + CW/2}" y="32" font-size="11" '
                 f'text-anchor="middle" letter-spacing="1.5">{lab}</text>')
    for i, (cle, (nom, _)) in enumerate(FAMILLES.items()):
        y0 = TOP + i * CH
        o.append(f'<text x="20" y="{y0 + CH/2}" font-size="13" '
                 f'fill="#2c3230">{nom}</text>')
        for j, (_, e, m) in enumerate(cas):
            o.append(dessiner(cle, e, m, 500 + i * 17,
                              Teinte.du_jour(200, 14, 0.7)).svg(
                MG + j * CW, y0, CW, CH))
    return "\n".join(o) + '</g></svg>'


def planche_saisons():
    """Les cinq palettes sur les quatre familles. La nuit doit sauter aux yeux."""
    cas = [("HIVER", 20, 14), ("PRINTEMPS", 110, 14), ("ETE", 200, 14),
           ("AUTOMNE", 300, 14), ("3H DU MATIN", 200, 3)]
    CW, CH, MG, TOP = 185, 190, 200, 56
    W, H = MG + CW * len(cas) + 20, TOP + CH * 4 + 16
    o = _entete(W, H)
    for j, (lab, _, _) in enumerate(cas):
        o.append(f'<text x="{MG + j*CW + CW/2}" y="32" font-size="10.5" '
                 f'text-anchor="middle" letter-spacing="1.4">{lab}</text>')
    for i, (cle, (nom, _)) in enumerate(FAMILLES.items()):
        y0 = TOP + i * CH
        o.append(f'<text x="20" y="{y0 + CH/2}" font-size="13" '
                 f'fill="#2c3230">{nom}</text>')
        for j, (_, jour, heure) in enumerate(cas):
            o.append(dessiner(cle, 0.7, 0.8, 500 + i * 17,
                              Teinte.du_jour(jour, heure, 0.7)).svg(
                MG + j * CW, y0, CW, CH))
    return "\n".join(o) + '</g></svg>'


def planche_feuillage():
    """Le point ouvert 3 : le feuillage doit s'alleger quand l'arbre grandit."""
    global BUDGET_FEUILLAGE
    CW, CH, MG, TOP = 200, 210, 200, 56
    W, H = MG + CW * 4 + 20, TOP + CH * 2 + 16
    o = _entete(W, H)
    for j, e in enumerate((0.15, 0.45, 0.75, 1.0)):
        o.append(f'<text x="{MG + j*CW + CW/2}" y="32" font-size="10.5" '
                 f'text-anchor="middle" letter-spacing="1.4">'
                 f'EXTENSION {e:.2f}</text>')
    for i, (lab, budget) in enumerate((("sans plafond global (v4)", 10 ** 6),
                                       ("avec plafond global", BUDGET_FEUILLAGE))):
        y0 = TOP + i * CH
        o.append(f'<text x="20" y="{y0 + CH/2}" font-size="12" '
                 f'fill="#2c3230">{lab}</text>')
        for j, e in enumerate((0.15, 0.45, 0.75, 1.0)):
            garde, BUDGET_FEUILLAGE = BUDGET_FEUILLAGE, budget
            t = Toile()
            vegetal(t, e, 0.85, 909, Teinte.du_jour(110, 14, 0.7))
            BUDGET_FEUILLAGE = garde
            o.append(t.svg(MG + j * CW, y0, CW, CH))
    return "\n".join(o) + '</g></svg>'


def planche_membres():
    """Point ouvert 6 : les membres doivent rester proportionnes au corps."""
    corps = [("gracile", 0.12), ("moyen", 0.5), ("massif", 1.0)]
    membres = [0.0, 0.35, 0.7, 1.0]
    CW, CH, MG, TOP = 190, 200, 150, 56
    W, H = MG + CW * len(membres) + 20, TOP + CH * len(corps) + 16
    o = _entete(W, H)
    for j, mb in enumerate(membres):
        o.append(f'<text x="{MG + j*CW + CW/2}" y="32" font-size="10.5" '
                 f'text-anchor="middle" letter-spacing="1.4">MEMBRES {mb:.2f}</text>')
    for i, (lab, cp) in enumerate(corps):
        y0 = TOP + i * CH
        o.append(f'<text x="20" y="{y0 + CH/2}" font-size="12" '
                 f'fill="#2c3230">corps {lab}</text>')
        for j, mb in enumerate(membres):
            t = Toile()
            creature(t, 0.7, 0.8, 777, Teinte.du_jour(200, 14, 0.7),
                     {"tete": 0.45, "corps": cp, "membres": mb})
            o.append(t.svg(MG + j * CW, y0, CW, CH))
    return SAUT.join(o) + '</g></svg>'


def planche_dates():
    """Point ouvert 7 : la ville doit porter de vraies dates."""
    cas = [
        ("une seule date (mai)", Teinte([(128, 1)], False, 0.8)),
        ("dates inventees (v4 : jour + rang x 47)",
         Teinte([(128, 1), (175, 1), (222, 1), (269, 1), (316, 1),
                 (363, 1), (45, 1)], False, 0.8)),
        ("vraies dates : fevrier -> mai",
         Teinte([(40, 900), (58, 1400), (79, 800), (95, 1200), (128, 700)],
                False, 0.8)),
    ]
    CW, CH, MG, TOP = 250, 230, 40, 74
    W, H = MG + CW * len(cas) + 20, TOP + CH + 20
    o = _entete(W, H)
    for j, (lab, tt) in enumerate(cas):
        o.append(f'<text x="{MG + j*CW + CW/2}" y="36" font-size="10.5" '
                 f'text-anchor="middle" letter-spacing="1.2">{lab}</text>')
        t = Toile()
        architecture(t, 0.85, 0.8, 606, tt)
        o.append(t.svg(MG + j * CW, TOP, CW, CH))
    return SAUT.join(o) + '</g></svg>'


def verifier():
    """La couleur ne doit jamais toucher la structure (decision 9)."""
    print("Determinisme et regle de couleur :\n")
    ok = True
    for cle in FAMILLES:
        sigs = set()
        for _ in range(3):
            t = dessiner(cle, 0.7, 0.8, 404, Teinte.du_jour(110, 14, 0.7))
            sigs.add(hashlib.blake2s(
                "".join(f"{s[0]:.2f},{s[1]:.2f},{s[5]}" for s in t.segments
                        ).encode(), digest_size=4).hexdigest())
        stable = len(sigs) == 1
        t = dessiner(cle, 0.7, 0.8, 404, Teinte.du_jour(110, 14, 0.7))
        encre = sum(1 for s in t.segments if s[5] == TRAIT)
        total = len(t.segments)
        print(f"  {cle:<13} {total:>4} segments, {encre:>4} a l'encre"
              f" ({encre/total:.0%} de structure)   "
              f"{'deterministe' if stable else 'INSTABLE'}")
        ok &= stable and 0 < encre < total
    print()
    for jour, heure, lab in ((20, 14, "hiver"), (76, 14, "hiver->printemps"),
                             (84, 14, "printemps<-hiver"), (110, 14, "printemps"),
                             (200, 14, "ete"), (200, 3, "3h du matin")):
        rng = random.Random(1)
        tt = Teinte.du_jour(jour, heure, 1.0)
        tons = [tt.ton(rng) for _ in range(3)]
        print(f"  jour {jour:>3} {heure:>2}h  {lab:<18} {' '.join(tons)}")

    print("")
    print("Le texte porte le nombre de tons, la date porte la teinte :")
    for dive in (0.0, 0.35, 0.7, 1.0):
        tt = Teinte.du_jour(110, 14, dive)
        rng = random.Random(4)
        tons = sorted({tt.ton(rng) for _ in range(40)})
        print(f"  diversite {dive:.2f} -> {len(tons)} ton(s)   {' '.join(tons)}")

    print("")
    print("Un plant ecrit de fevrier a mai (vraies dates ponderees) :")
    tt = Teinte([(40, 900), (58, 1400), (79, 800), (95, 1200), (128, 700)],
                False, 0.8)
    rng = random.Random(11)
    print("  " + " ".join(tt.ton(rng) for _ in range(8)))
    return ok


if __name__ == "__main__":
    for nom, fn in (("planche_etat", planche_etat),
                    ("planche_saisons_v7", planche_saisons),
                    ("planche_feuillage", planche_feuillage),
                    ("planche_membres", planche_membres),
                    ("planche_dates", planche_dates)):
        open(f"{nom}.svg", "w", encoding="utf-8").write(fn())
        print(f"{nom}.svg ecrit")
    print()
    verifier()
