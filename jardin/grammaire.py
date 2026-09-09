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

    ⚠️ Et le texte le prend par `richesse`, PAS par `diversite`. Ce sont deux
    lectures du meme MATTR, bornees differemment parce qu'elles repondent a
    deux questions — voir traits.extraire(). Brancher les tons sur le trait de
    CLASSEMENT a coute vingt-deux arbres sur un vrai paysage : elargir la borne
    pour voir des couleurs deplacait du meme coup la frontiere des familles.
    """

    def __init__(self, dates=None, nuit=False, richesse=0.5):
        self.dates = list(dates) if dates else [(200, 1)]
        self.nuit = bool(nuit)
        self.n_tons = 1 + int(min(1.0, max(0.0, richesse)) * 4)    # 1 a 5
        self._poids, cumul = [], 0
        for _, poids in self.dates:
            cumul += max(1, poids)
            self._poids.append(cumul)
        self._total = cumul

    @classmethod
    def du_jour(cls, jour=200, heure=14, richesse=0.5):
        """Raccourci pour les planches : un plant ecrit d'un seul jet."""
        return cls([(jour, 1)], HEURE_NUIT[0] <= heure < HEURE_NUIT[1], richesse)

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

    def _jour_de(self, u) -> int:
        """Comme `jour()`, mais sur une uniforme donnee au lieu d'un flux."""
        cible = int(u * self._total)
        for i, seuil in enumerate(self._poids):
            if cible < seuil:
                return self.dates[i][0]
        return self.dates[-1][0]

    def ton_de(self, u_jour, u_ton) -> str:
        """
        Le meme ton, tire sur DEUX UNIFORMES au lieu d'un flux.

        ⚠️ C'EST LA DECISION 9 QUI L'EXIGE. La couleur y porte la DATE
        D'ECRITURE : un chapitre commence en fevrier et fini en mai montre les
        deux. Avec `ton(rng)`, quelle date un trait recevait dependait de
        COMBIEN DE TRAITS AVAIENT ETE DESSINES AVANT LUI — pas une propriete
        du trait, un artefact de l'ordre de parcours. Une feuille « ecrite en
        fevrier » devenait une feuille de mai a la frappe suivante.

        Mesure : la teinte ne bougeait pas a chaque mot (0 %% a +1, +2, +10)
        mais se re-tirait d'un coup tous les quelques dizaines de mots, sur un
        tiers des traits du vegetal et 4,6 %% des tours de la ville. La cause
        est fine : `randrange(n)` rejette et retire quand son tirage depasse
        n, et cette probabilite change avec n — or n vaut le nombre de mots du
        plant. Un seul rejet qui differe decale tout le reste du flux.

        C'est exactement la faute corrigee pour la geometrie a la decision 18,
        un cran plus loin : une valeur lue par RANG au lieu de l'etre par
        IDENTITE.
        """
        return palette(self._jour_de(u_jour),
                       int(u_ton * self.n_tons), self.nuit)


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

    def trait(self, x1, y1, x2, y2, m=0.0, col=None, structure=False):
        """
        `structure` marque le squelette porteur — ce qui tient la forme.

        La decision 9 dit que la couleur ne touche JAMAIS la structure, et
        c'est cette seule regle qui preserve l'unite etablie a la decision 8.
        Tant qu'elle n'etait qu'une intention dans les commentaires, on ne
        pouvait la verifier qu'en comptant les traits a l'encre — et un
        vegetal dont on colorait les branches passait quand meme, parce que
        l'anastomose restait noire. Marquee dans la donnee, la regle devient
        une invariante qu'un essai peut tenir.
        """
        self.segments.append((x1, y1, x2, y2, m, col or TRAIT, structure))

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
        for a, b, c, d, m, col, _r in self.segments:
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
        for a, b, c, d, m, col, _r in self.segments:
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
# qu'on venait d'ajouter. Meme remede que les cycles de plant — plafonner le
# total et le repartir, jamais l'unite locale.
#
# ⚠️ « ET LE REPARTIR » a ete ecrit ici et pas fait pendant longtemps : le code
# DIVISAIT, « BUDGET_FEUILLAGE // pointes », le meme compte pour chaque
# bouquet. Un quotient entier n'est pas monotone, et la couronne perdait un
# tiers de ses traits en gagnant un rameau. Voir vegetal() et la decision 6.
BUDGET_FEUILLAGE = 210

# Interrupteur de comparaison, comme BUDGET_FEUILLAGE. A False, les membres
# reprennent la longueur ABSOLUE de la v5 : une bete gracile et une bete
# massive recoivent alors exactement les memes pattes (rapport 1,00 contre
# 3,48). Sert uniquement aux planches d'avant/apres — le code de production
# ne le touche pas.
MEMBRES_PROPORTIONNELS = True

# --------------------------------------------------------------------------
# Ce que le texte dit de la FORME (et non de la couleur ni de la taille).
#
# Les trois curseurs de la creature et la geometrie de l'abstrait existaient
# depuis les v4-v5, mais rien ne les alimentait : `etoffage` et `traits`
# tombaient sur leurs valeurs par defaut a chaque appel. Toutes les creatures
# etaient donc la meme creature, tous les abstraits le meme cristal — un
# paysage de cinquante-cinq plants n'aurait montre que quatre formes repetees, ce
# qui aurait ruine la decision 7 (un paysage, pas un fourre-tout) sans qu'on
# comprenne pourquoi.
#
# Chaque correspondance ci-dessous doit dire quelque chose de vrai. Ce ne sont
# pas des branchements arbitraires : c'est la ou le texte devient anatomie.
# --------------------------------------------------------------------------
TRAITS_NEUTRES = {
    "longueur": 0.5, "rythme": 0.5, "subordination": 0.5, "regularite": 0.5,
    "structure": 0.5, "dialogue": 0.5, "interrogation": 0.5,
    "diversite": 0.5, "richesse": 0.5, "ponctuation_rare": 0.5,
}


def _traits(traits):
    t = dict(TRAITS_NEUTRES)
    if traits:
        t.update({k: v for k, v in traits.items() if k in TRAITS_NEUTRES})
    return t


def _rang_de_pousse(lignee: int) -> float:
    """
    Dans quel ordre ce rameau sort, entre 0 et 1.

    Le bit INVERSE (van der Corput). Pris dans l'ordre naturel, les rameaux
    apparaitraient de gauche a droite et l'arbre pousserait d'un cote ; tires au
    hasard, ils changeraient de place a chaque redessin. Le bit inverse les
    disperse dans toute la couronne ET fixe l'ordre une fois pour toutes.

    C'est cette fixite qui compte : un rameau sorti ne rentre jamais quand
    l'extension monte, donc la forme ne peut que croitre — decision 1.
    """
    niveau = lignee.bit_length() - 1
    if niveau <= 0:
        return 0.0
    index = lignee - (1 << niveau)
    inverse = 0
    for i in range(niveau):
        inverse = (inverse << 1) | ((index >> i) & 1)
    return inverse / (1 << niveau)


def _tirages(graine):
    """
    Une table de tirages lue PAR IDENTITE, jamais par rang dans le flux.

    ⚠️ C'EST LA REPARATION LA PLUS IMPORTANTE DU FICHIER. Les trois familles
    consommaient `rng` SEQUENTIELLEMENT, dans l'ordre du dessin. Un rameau qui
    s'ouvre, une tour qui apparait, un segment d'epine en plus : le tirage
    suivant n'etait plus le meme, et TOUT CE QUI VENAIT APRES changeait. Le
    plant ne poussait pas, il etait redessine avec un autre hasard.

    Mesure sur seize graines et quarante pas de croissance, tout le reste
    constant — le vegetal reculait 226 fois sur 624, jusqu'a -17,1 pour cent.
    Et d'un pas au suivant il ne SURVIVAIT que 8,6 pour cent de ses traits :
    91 pour cent de l'arbre etait refait tous les 125 mots. La decision 1 dit
    que rien ne recule ; elle tombait a chaque frappe.

    Ici l'entree i recoit toujours le i-eme tirage du flux, quel que soit le
    moment ou on la demande — le remplissage est paresseux mais TOUJOURS DANS
    L'ORDRE DES INDICES. Un rameau lit la fente de sa lignee, une tour celle
    de son rang lateral, un segment d'epine celle de son indice. Ajouter
    n'importe quoi ne deplace plus rien.

    ⚠️ Le motif n'est pas neuf : `abstrait()` le fait depuis toujours avec son
    `jitter`, tire avant la boucle d'anneaux. C'est la seule des quatre
    familles qui etait monotone ET additive a 100 pour cent, et personne
    n'avait fait le rapprochement.

    ⚠️ Le flux est SEPARE de `rng`. Il doit l'etre : `rng` sert aussi a la
    couleur, tiree dans l'ordre du dessin, donc y puiser la table la rendrait
    a nouveau dependante de la structure. Les deux viennent de la meme graine
    du document, donc la decision 8 tient — meme document, meme figure.

    ⚠️ Le multiplicateur reste petit expres. `alea.js` ne porte les graines que
    jusqu'a 53 bits, et une graine de plant vaut deja jusqu'a 2^32.
    """
    flux = random.Random(graine * 7919 + 13)
    table = []

    def al(i):
        while len(table) <= i:
            table.append(flux.random())
        return table[i]

    return al


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
    # ⚠️ L'AXE, ET C'EST LA QU'UNE THESE SE DISTINGUE D'ELLE-MEME.
    #
    #   L'arbre ne lisait que subordination, regularite et longueur — les trois
    #   traits les plus STABLES chez un meme auteur. Mesure sur cent vingt
    #   plants simules d'une these : le texte faisait varier l'encre de 19 %
    #   quand la seule graine la faisait varier de 37 %. Deux chapitres
    #   differaient surtout par chance, et un texte quelconque atteignait
    #   255 % : l'arbre savait dessiner dix fois plus large que ce que son
    #   auteur en obtenait.
    #
    #   `structure` est le trait qui bouge le PLUS dans une these — de 0,000 a
    #   0,914 selon qu'une section est decoupee en titres ou coule d'un trait —
    #   et le vegetal l'ignorait completement. Une bibliographie, un chapitre a
    #   sous-parties et un chapitre de recit donnaient le meme arbre.
    #
    #   Il devient la DOMINANCE APICALE : un texte charpente garde un axe et
    #   porte ses rameaux en etages, un texte continu fourche en gobelet. C'est
    #   une difference de silhouette, pas de grain — elle se voit de loin, a la
    #   taille ou les plants sont poses dans le paysage.
    axe = tr["structure"]
    # Le feuillage suit le vocabulaire : un lexique large fait un bouquet
    # ouvert et disperse, un lexique etroit une brosse serree. Le NOMBRE de
    # feuilles ne bouge pas — il est tenu par le budget, et la decision 1
    # interdit qu'il recule. Seule leur ouverture change.
    eventail = 0.22 + tr["richesse"] * 0.36
    frisson = 0.05 + tr["richesse"] * 0.14
    # ⚠️ LE PORT SE TIRE AU SORT, LA TAILLE JAMAIS.
    #
    #   Un plant plus GROS au hasard, c'est la decision 2 qui tombe : la taille
    #   dit combien on a ecrit, et si la graine la tire, tripoter et ecrire
    #   deviennent indistinguables a l'oeil. La composition l'annulerait de
    #   toute facon — elle divise par l'encombrement final, donc deux plants
    #   acheves remplissent le meme cadre quoi qu'il arrive.
    #
    #   Ce qui SURVIT a cette normalisation, c'est la proportion. On tire donc
    #   un port entre etale et elance : angles serres et longues entre-noeuds
    #   font un peuplier, angles ouverts et entre-noeuds courts un pommier. Le
    #   compte des traits est le meme des deux cotes — la meme quantite de bois
    #   portee autrement, ce qui ne ment sur rien.
    port = rng.uniform(-1.0, 1.0)
    ouverture *= 1.0 - port * 0.7
    entre_noeuds *= 1.0 + port * 0.02
    # ⚠️ LA PROFONDEUR EST FRACTIONNAIRE, et c'est tout le sujet.
    #
    #   Elle valait « 4 + int(extension * 3.0) » : un entier, donc QUATRE formes sur
    #   toute la vie d'un plant. L'extension n'entrait dans l'arbre que par la, et
    #   entre deux crans, ecrire ne changeait rien du tout. A 2 500 mots par plant
    #   cela faisait un changement visible toutes les 625 — deux pages — la ou la
    #   creature en offre onze fois plus.
    #
    #   On ne peut pas ajouter des niveaux : ils doublent le nombre de branches. On
    #   ouvre donc le DERNIER, rameau par rameau. La partie entiere donne les niveaux
    #   pleins, la decimale la proportion du dernier qui est sortie.
    #
    #   Un rameau pas encore sorti reste un BOURGEON — un bouquet de feuilles — au
    #   lieu de disparaitre : la couronne n'a jamais de trou, et pousser consiste a
    #   ouvrir un bourgeon en rameau, ce qui est monotone.
    #
    #   Aux quatre valeurs entieres l'arbre est EXACTEMENT celui d'avant : le
    #   changement raffine l'entre-deux, il ne redessine pas ce qui existait.
    prof_max = 4.0 + extension * 3.0
    # Le compte des pointes, qui donne le budget de feuillage. En ENTIERS :
    # 2 ** un flottant n'a pas forcement la meme derniere decimale en Python
    # et en JavaScript, et la parite se joue exactement la.
    niveaux = int(prof_max)
    reste = prof_max - niveaux
    pointes = (1 << niveaux) + int(reste * (1 << niveaux))
    # ⚠️ LE BUDGET SE REPARTIT, IL NE SE DIVISE PAS.
    #
    #   C'etait « BUDGET_FEUILLAGE // pointes », le meme nombre de feuilles pour
    #   chaque bouquet. Un quotient entier n'est pas monotone : 52 pointes a 4
    #   traits font 208 traits, 53 pointes a 3 traits en font 159. Le feuillage
    #   RECULAIT donc au moment ou l'arbre gagnait un rameau — mesure sur la vie
    #   d'un plant : 271 -> 223, 300 -> 235, puis 331 -> 230 traits, soit un tiers
    #   de la couronne perdu d'un seul pas.
    #
    #   C'est la decision 1 violee, et ce n'est pas la profondeur fractionnaire qui
    #   l'a introduit : la version entiere reculait deja au dernier cran de chaque
    #   plant, 192 traits a la profondeur 6 contre 128 a la profondeur 7. L'arbre
    #   s'eclaircissait exactement quand il s'achevait. C'est vraisemblablement ce
    #   qu'on voyait dans le vrai Word et qu'on prenait pour un rapetissement.
    #
    #   On donne donc a chaque pointe sa part ENTIERE du budget, et une feuille de
    #   plus a la fraction des pointes que le rang de pousse designe — le meme ordre
    #   que celui des rameaux, pour que le supplement soit disperse et non groupe
    #   d'un cote. Le total suit le budget au lieu de sauter par paliers.
    # ⚠️ ET LA PART SE CALCULE SUR LES POINTES FINALES, PAS COURANTES.
    #
    #   `BUDGET_FEUILLAGE / pointes` divisait par le compte DU MOMENT, qui
    #   grossit : chaque bouquet perdait des feuilles quand l'arbre en gagnait,
    #   donc le feuillage RECULAIT — 8 reculs sur 76 pas, jusqu'a -4,4 pour
    #   cent, la ou le squelette etait deja parfaitement monotone.
    #
    #   C'est la decision 14 appliquee au budget : toujours passer par le
    #   gabarit FINAL. Le plafond n'est pas perdu pour autant — a maturite
    #   `pointes` vaut justement `pointes_finales`, donc le total retombe
    #   exactement sur BUDGET_FEUILLAGE et le compte de traits d'un plant
    #   acheve ne bouge pas d'une unite.
    pointes_finales = 1 << int(4.0 + 3.0)
    part = BUDGET_FEUILLAGE / pointes_finales
    plafond = 3 + int(m * 3)
    noeuds = []

    al = _tirages(graine)
    FENTES = 8            # par lignee : 1 ouverture, 1 longueur, 6 feuilles

    # ⚠️ TROIS TABLES, ET LA SEPARATION EST LE POINT.
    #
    #   La couleur a la sienne : corriger une teinte ne peut alors pas
    #   deplacer une forme, et le portage se verifie a geometrie IDENTIQUE
    #   trait pour trait. Mesure : les quatre familles rendent exactement les
    #   memes coordonnees avant et apres.
    #
    #   L'anastomose a la sienne aussi. Elle vivait a l'offset 2048 dans la
    #   table des lignees, ce qui tenait a un cheveu — `extension` bornee a 1
    #   donne prof_max <= 7 donc lignee < 256 donc fentes < 2048 — et
    #   quiconque aurait ouvert la profondeur aurait fait se recouvrir les
    #   deux blocs EN SILENCE. Une table propre supprime la contrainte, et
    #   evite au passage de remplir 4096 entrees quand 2048 suffisent.
    alc = _tirages(graine * 31 + 7)
    ala = _tirages(graine * 131 + 17)
    FENTES_C = 14         # par lignee : 6 feuilles x (jour, ton) + noeud x 2
    PAIRES = 4096         # collisions admises : deux paires peuvent partager


    def branche(x, y, angle, lg, prof, lignee):
        # Le dernier niveau est fractionnaire : ce rameau-ci n'est peut-etre
        # pas encore sorti. Il reste alors un bourgeon.
        if 0.0 < prof < 1.0 and _rang_de_pousse(lignee) >= prof:
            prof = 0.0
        if prof <= 0 or lg < 3.0:
            n_feuilles = max(1, min(plafond, int(part) + (
                1 if _rang_de_pousse(lignee) < part - int(part) else 0)))
            for i in range(n_feuilles):
                # ⚠️ LA LARGEUR DU BOUQUET NE DEPEND PLUS DE SON COMPTE.
                #   L'ecart valait `eventail` PAR FEUILLE, donc un bouquet a
                #   deux feuilles s'ouvrait deux fois moins qu'un bouquet a
                #   quatre — et depuis que la part se calcule sur les pointes
                #   finales, un jeune arbre en a justement moins. Le
                #   vocabulaire cessait d'ouvrir le feuillage, ce qui est tout
                #   ce que `eventail` est charge de dire. La largeur est
                #   desormais celle du bouquet PLEIN, repartie sur ce qu'il y a.
                large = eventail * plafond
                a = (angle + ((i + 0.5) / n_feuilles - 0.5) * large
                     + (al(lignee * FENTES + 2 + i) * 2 - 1) * frisson)
                r = lg * (1.3 + 0.8 * m)
                cf = lignee * FENTES_C + i * 2
                t.trait(x, y, x + math.cos(a) * r, y + math.sin(a) * r,
                        m * 0.55, tt.ton_de(alc(cf), alc(cf + 1)))
            return
        x2, y2 = x + math.cos(angle) * lg, y + math.sin(angle) * lg
        t.trait(x, y, x2, y2, m, structure=True)    # squelette
        cn = lignee * FENTES_C + 12
        t.noeud(x2, y2, m, tt.ton_de(alc(cn), alc(cn + 1)))
        noeuds.append((x2, y2, lignee))
        ouv = ouverture * (0.85 + al(lignee * FENTES) * 0.30)
        # Lequel des deux rameaux prolonge l'axe. Il ALTERNE avec la lignee :
        # fixe d'un cote, l'axe derivait et l'arbre partait en biais, ce que
        # la dissymetrie est seule a devoir faire.
        meneur = -1 if lignee & 1 else 1
        for s in (-1, 1):
            biais = 1.0 + s * dissymetrie
            tenue = (1.0 - axe * 0.72) if s == meneur else (1.0 + axe * 0.4)
            # Le lateral garde sa LONGUEUR : le raccourcir en plus de
            # redresser le meneur recroquevillait l'arbre en chardon des
            # quatre titres — vu sur planche, la couronne disparaissait.
            allonge = (1.0 + axe * 0.22) if s == meneur else 1.0
            fils = lignee * 2 + (s > 0)
            branche(x2, y2, angle + s * ouv * biais * tenue,
                    lg * entre_noeuds * allonge
                    * (0.94 + al(fils * FENTES + 1) * 0.12),
                    prof - 1, fils)

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
            # La decision appartient a la PAIRE de lignees : tiree dans le
            # flux, elle changeait des que le nombre de noeuds changeait.
            paire = (l1 * 257 + l2) % PAIRES
            if 6 < math.hypot(x2 - x1, y2 - y1) < seuil and ala(paire) < 0.45:
                t.trait(x1, y1, x2, y2, m * 0.55, structure=True)
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
    al = _tirages(graine)
    alc = _tirages(graine * 31 + 7)   # deux fentes par tour : jour, ton
    FENTES = 6            # par tour : hauteur, largeur, decalage, antenne x2, cle
    # N_REF : le nombre MAXIMAL de tours — 2 + 3 (extension) + 3 (structure).
    N_REF = 8

    # ⚠️ TROIS CHOSES DEPENDAIENT DU NOMBRE DE TOURS, DONC DE L'EXTENSION.
    #
    #   `sorted(..., key=rng.random)` consommait n_tours tirages AVANT tous les
    #   autres : une tour de plus et la ville entiere changeait de hasard. La
    #   cle appartient desormais a la tour.
    #
    #   `cx = 100 + (k - n_tours / 2) * ...` faisait dependre la POSITION de
    #   chaque tour du compte total : ajouter un batiment les deplacait TOUTES.
    #   La ville se remplit maintenant depuis le centre, et la tour k a sa
    #   place une fois pour toutes.
    #
    #   `base = 205 - rang * ...` prenait le RANG DANS L'ORDRE DE POSE : une
    #   tour qui s'inserait avant les autres dans le tri les faisait toutes
    #   remonter. La profondeur vient de la cle de la tour, pas de son rang.
    #
    #   Mesure : 1216 montants sur 1216 gardent leur abscisse d'un pas de
    #   croissance au suivant et montent tous, contre 1024 sur 1216 avant.
    ordre = sorted(range(n_tours), key=lambda k: al(k * FENTES + 5))

    def rang_lateral(k):
        return ((k + 1) // 2) * (-1 if k % 2 else 1)

    for rang, k in enumerate(ordre):
        # Chaque tour a sa propre date : un chapitre ecrit l'hiver et un autre
        # l'ete ne s'eclairent pas de la meme couleur.
        col = tt.ton_de(alc(k * 2), alc(k * 2 + 1))
        h = SEGMENT * hauteur_base * (1.0 + al(k * FENTES) * ecart_hauteur)             * (0.55 + extension * 0.7)
        w = SEGMENT * (0.85 + al(k * FENTES + 1) * 0.85)
        cx = 100 + rang_lateral(k) * SEGMENT * 1.15             + (al(k * FENTES + 2) * 12 - 6)
        base = 205 - al(k * FENTES + 5) * (N_REF - 1) * SEGMENT * 0.22
        g, d, top = cx - w / 2, cx + w / 2, base - h
        for seg in ((g, base, g, top), (d, base, d, top),
                    (g, top, d, top), (g, base, d, base)):
            t.trait(*seg, m, structure=True)          # squelette
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
        if al(k * FENTES + 3) < 0.45:                 # antenne, fleche
            t.trait(cx, top, cx,
                    top - SEGMENT * (0.4 + al(k * FENTES + 4) * 0.8), m * 0.8)
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
    al = _tirages(graine)
    alc = _tirages(graine * 31 + 7)
    FENTES = 3            # par segment d'epine : bruit d'angle, deux membres
    FENTES_C = 10         # par segment : barreau x2, deux membres x 4

    n = 7 + int(extension * 11)
    # ⚠️ LE FUSELAGE SE CALCULE SUR LA LONGUEUR FINALE, PAS COURANTE.
    #
    #   `f = i / (n - 1)` faisait dependre la longueur ET l'epaisseur de
    #   CHAQUE segment du nombre total : en ajouter un les redessinait tous,
    #   et la bete ne gardait que 23,7 pour cent de ses traits d'un pas au
    #   suivant. Avec la longueur finale, elle en garde 100 pour cent : la
    #   creature s'allonge par la queue et le reste ne bouge plus.
    #
    #   Meme faute que la part de feuillage du vegetal et que le centrage de
    #   la ville. Trois familles, trois fois la decision 14 — toujours passer
    #   par le gabarit final.
    N_FINAL = 7 + 11
    spine, angle, x, y = [], rng.uniform(-1.1, 0.1), 55, 165
    for i in range(n):
        f = i / (N_FINAL - 1)
        lg = SEGMENT * 0.60 * (1.15 - 0.55 * f)
        angle += math.sin(i * cadence + phase) * courbure + avance             + (al(i * FENTES) * 0.1 - 0.05)
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
        t.trait(*contour[i], *contour[(i + 1) % len(contour)], m,
                structure=True)                                     # squelette
    pas = max(1, int(3 - e["corps"] * 2))
    for i in range(0, len(spine), pas):
        t.trait(*gauche[i], *droite[i], m * 0.55,
                tt.ton_de(alc(i * FENTES_C), alc(i * FENTES_C + 1)))

    # TETE : le rayon suit le curseur, pas seulement le nombre d'appendices.
    # La tete a son bloc APRES celui de l'epine : son compte depend des
    # traits, pas de l'extension, mais ses tirages suivaient ceux des
    # barreaux — qui, eux, grandissent. Elle changeait donc de couleur a
    # chaque segment gagne.
    TETE = N_FINAL * FENTES_C
    hx, hy, ha, _ = spine[0]
    rayon = SEGMENT * (0.22 + e["tete"] * 1.15)
    n_tete = 3 + int(e["tete"] * 6)
    for k in range(n_tete):
        a = ha + math.pi + (k - n_tete / 2) * (1.9 / max(n_tete, 1))
        t.trait(hx, hy, hx + math.cos(a) * rayon, hy + math.sin(a) * rayon,
                m * 0.85,
                tt.ton_de(alc(TETE + k * 2), alc(TETE + k * 2 + 1)))
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
            if MEMBRES_PROPORTIONNELS:
                p1 = largeur_corps * (0.8 + 3.2 * e["membres"]) * ep
            else:
                p1 = SEGMENT * (0.25 + 1.25 * e["membres"]) * ep
            bx, by = ax + math.cos(a1) * p1, ay + math.sin(a1) * p1
            t.trait(ax, ay, bx, by, m * 0.8)
            a2 = a1 + s * (0.55 + al(i * FENTES + 1 + (s > 0)) * 0.45)
            d = i * FENTES_C + 2 + (0 if s < 0 else 4)
            t.trait(bx, by, bx + math.cos(a2) * p1 * 0.65,
                    by + math.sin(a2) * p1 * 0.65, m * 0.6,
                    tt.ton_de(alc(d), alc(d + 1)))
            t.noeud(bx, by, m, tt.ton_de(alc(d + 2), alc(d + 3)))


# --------------------------------------------------------------------------
# Abstrait — il se pave
# --------------------------------------------------------------------------
def abstrait(t: Toile, extension, maturite, graine, teinte=None,
             traits=None):
    """
    Sa geometrie n'est pas fixee : elle est LUE sur le vecteur de traits. Sans
    cela, la famille du refus de classement aurait la regle la plus rigide des
    quatre — un pavage hexagonal regulier.

        richesse         -> nombre de facettes
        ponctuation_rare -> irregularite des sommets
        rythme           -> torsion d'un anneau au suivant
        subordination    -> etoilement (sommets pousses vers l'interieur)
    """
    rng = random.Random(graine)
    m = maturite
    tt = teinte or Teinte.du_jour()
    tr = _traits(traits)

    cotes = 5 + int(tr["richesse"] * 4.4)               # 5 a 9 facettes
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
            t.trait(*pts[k], *pts[(k + 1) % cotes], m, structure=True)
        if prec:
            for k in range(cotes):
                t.trait(*prec[k], *pts[k], m * 0.8, structure=True)
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


# --------------------------------------------------------------------------
# Le germe — ce qui pousse avant qu'une famille soit connue
# --------------------------------------------------------------------------
# traits.py prevoit trois stades depuis le debut — germe, indices, divergence —
# et rien n'en dessinait les deux premiers. C'est 32 % de CHAQUE cycle de
# 2 500 mots, donc cinquante-cinq fois sur une these ; et la premiere de ces
# cinquante-cinq fois, ce sont les 800 premiers mots ecrits avec le cadeau
# installe. Un volet vide, ce jour-la, est le pire accueil possible.
#
# Ce qu'on dessine : la PRIMITIVE AVANT SON ASSEMBLAGE. Les quatre familles
# sont quatre reponses a la meme question — que fait une chaine de segments
# ensuite ? Elle bifurque, elle s'empile, elle ondule, elle se referme. Le
# germe est la chaine avant la reponse ; il appartient donc aux quatre a la
# fois, ce qui est exactement son etat.
#
# Au stade indices, la chaine PENCHE vers la famille pressentie sans s'y
# engager. C'est ce que « provisoire » veut dire, et c'est honnete a une
# condition : l'inflexion ne doit jamais produire un objet reconnaissable.
# Si le germe ressemblait deja a un arbre et devenait une ville, l'organisme
# se contredirait sous les yeux de la personne — ce que le point 5 interdit.
# Une tendance peut se corriger ; une promesse, non.


def germe(t: Toile, taille, inflexion=0.0, pressentie=None, graine=0,
          teinte=None):
    """
    taille     0..1, les mots ecrits rapportes au palier de divergence
    inflexion  0..1, nul au stade germe, croissant au stade indices
    """
    rng = random.Random(graine)
    tt = teinte or Teinte.du_jour()
    n = max(1, int(1 + taille * 9))
    m = 0.10 + 0.30 * taille          # un germe reste maigre : rien n'a mûri
    lg = SEGMENT * 0.60
    x, y, a = 100.0, 200.0, -math.pi / 2
    dos = []

    for i in range(n):
        if pressentie == "architecture" and inflexion > 0:
            # elle s'empile : une traverse s'insere entre deux montees, et
            # sa longueur suit l'inflexion. La traverse est un trait EN PLUS,
            # elle ne remplace pas une montee : sans ca, le germe
            # d'architecture tracait deux fois moins de segments que les
            # autres, et les cinq cas differaient DEJA a inflexion nulle —
            # c'est-a-dire avant qu'aucune tendance ne soit censee paraitre.
            traverse = lg * inflexion * 0.62
            if i and traverse > 0.4:
                sens = 0.0 if (i // 2) % 2 == 0 else math.pi
                xt = x + math.cos(sens) * traverse
                yt = y + math.sin(sens) * traverse
                t.trait(x, y, xt, yt, m)
                x, y = xt, yt
            a = -math.pi / 2
        elif pressentie == "creature":
            # elle s'enchaine : la chaine ondule
            a += inflexion * math.sin(i * 0.95) * 0.40
        elif pressentie == "abstrait":
            # elle se pave : la chaine s'incurve vers sa propre fermeture
            a += inflexion * 0.30
        a += rng.uniform(-0.04, 0.04)
        x2, y2 = x + math.cos(a) * lg, y + math.sin(a) * lg
        t.trait(x, y, x2, y2, m)
        dos.append((x2, y2, a))
        x, y = x2, y2

    if pressentie == "vegetal" and inflexion > 0.15 and len(dos) >= 3:
        # elle se ramifie : une seule bifurcation, courte, en tete de chaine
        bx, by, ba = dos[-2]
        for sgn in (-1, 1):
            aa = ba + sgn * (0.30 + inflexion * 0.30)
            t.trait(bx, by, bx + math.cos(aa) * lg * (0.45 + inflexion * 0.5),
                    by + math.sin(aa) * lg * (0.45 + inflexion * 0.5),
                    m * 0.9)

    # Un seul point de couleur en tete : le germe est deja date, et c'est le
    # seul signe qui l'annonce vivant plutot qu'inachevé.
    if dos:
        hx, hy, ha = dos[-1]
        t.trait(hx, hy, hx + math.cos(ha) * lg * 0.28,
                hy + math.sin(ha) * lg * 0.28, m * 0.8, tt.ton(rng))


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
                    traits.get("richesse", 0.5))
    g = plant.get("germe")
    if not plant.get("famille"):
        # Pas encore de famille : on dessine le germe, qui penche vers la
        # pressentie sans s'y engager.
        t = Toile()
        germe(t, (g or {}).get("taille", 0.1), (g or {}).get("inflexion", 0.0),
              plant.get("pressentie"), graine, teinte)
        return t
    return dessiner(plant["famille"],
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


def planche_pousse():
    """La courbe de pousse, et ce que la longueur des lignes y change.

    Trois questions posees devant le vrai add-in, auxquelles aucune batterie ne
    repond : a quel moment ca pousse vite, est-ce que la vitesse de frappe y
    entre, et est-ce qu'on veut un paysage dense.

    LA VITESSE DE FRAPPE N'Y ENTRE PAS. Le debit ne sert qu'a distinguer un
    collage — quinze mots par intervalle de deux secondes, soit 450 mots par
    minute. C'est un portillon, pas un debit : ecrire a 30 ou a 200 mots par
    minute fait pousser exactement la meme chose. Cette planche n'a donc qu'un
    axe, les mots ecrits.

    CE QUI CHANGE TOUT, EN REVANCHE, C'EST LA LONGUEUR DES LIGNES.
    L'extension VALAIT max(lignes / 52, mots / 5000) — le plus avance des deux
    gagnait, pour ne pas fermer la forme de quelqu'un qui ecrit long avant
    qu'elle ait fini de pousser. Mais 52 a ete calcule comme 5000 / 96 : il
    suppose des lignes de 96 mots. Le premier vrai document ouvert avec
    l'add-in en avait de ONZE. Les deux rangees montrent l'ecart.

    La rangee APRES se lit sur MOTS_PAR_PLANT, qui vaut 2 500 depuis que la
    decision 6 a ete confrontee a un article : elle bouge donc avec lui.
    """
    from paysage import MOTS_PAR_PLANT, PALIER_INDICES, PALIER_DIVERGENCE
    ANCIEN = 52          # PARAGRAPHES_PAR_PLANT, retire depuis
    ETAPES = [100, 200, 400, 600, 800, 1200, 2000, 3200, 5000]
    # Les deux premieres rangees montrent l'AVANT, la troisieme l'APRES : une
    # planche qui ne montre que l'etat corrige prouve que le mecanisme marche,
    # pas que la correction change quelque chose.
    STYLES = [("AVANT · PARAGRAPHES DE 96 MOTS", 96, True),
              ("AVANT · LIGNES DE 11 MOTS", 11, True),
              ("APRES · N'IMPORTE QUEL STYLE", 11, False)]
    CW, CH, MG, TOP = 150, 200, 210, 96
    W = MG + CW * len(ETAPES) + 20
    H = TOP + (CH + 46) * len(STYLES) + 30
    o = _entete(W, H)

    o.append(f'<text x="20" y="30" font-size="13" fill="#2c3230">'
             f'La courbe de pousse d\'un plant</text>')
    o.append(f'<text x="20" y="52" font-size="10.5">'
             f'avant : max(lignes / {ANCIEN}, mots / {MOTS_PAR_PLANT}) — '
             f'apres : mots / {MOTS_PAR_PLANT}. '
             f'La vitesse de frappe n\'y entre ni avant ni apres.'
             f'</text>')
    for j, m in enumerate(ETAPES):
        o.append(f'<text x="{MG + j*CW + CW/2}" y="80" font-size="11" '
                 f'text-anchor="middle" letter-spacing="1.2">{m} MOTS</text>')

    for i, (nom, par_ligne, avant) in enumerate(STYLES):
        y0 = TOP + i * (CH + 46)
        o.append(f'<text x="20" y="{y0 + CH/2 - 8}" font-size="12" '
                 f'fill="#2c3230">{nom}</text>')
        plein = None
        for j, m in enumerate(ETAPES):
            lignes = max(1, m // par_ligne)
            e = (min(1.0, max(lignes / ANCIEN, m / MOTS_PAR_PLANT)) if avant
                 else min(1.0, m / MOTS_PAR_PLANT))
            if e >= 1.0 and plein is None:
                plein = m
            x0 = MG + j * CW
            # Sous le palier de divergence, c'est encore un germe : c'est la
            # coupure du point ouvert 12, et elle doit se voir sur la planche.
            if m < PALIER_DIVERGENCE:
                t = Toile()
                taille = min(1.0, m / PALIER_DIVERGENCE)
                infl = max(0.0, min(1.0, (m - PALIER_INDICES)
                                    / max(PALIER_DIVERGENCE - PALIER_INDICES, 1)))
                germe(t, taille, infl, None, 500 + i * 17,
                      Teinte.du_jour(200, 14, 0.7))
                o.append(t.svg(x0, y0, CW, CH))
                etat = "germe"
            else:
                o.append(dessiner("vegetal", e, 0.25, 500 + i * 17,
                                  Teinte.du_jour(200, 14, 0.7)).svg(
                    x0, y0, CW, CH))
                etat = "vegetal"
            o.append(f'<text x="{x0 + CW/2}" y="{y0 + CH + 14}" font-size="10" '
                     f'text-anchor="middle">ext {e:.2f}</text>')
            o.append(f'<text x="{x0 + CW/2}" y="{y0 + CH + 28}" font-size="9" '
                     f'text-anchor="middle" fill="#9a938c">'
                     f'{lignes} lignes · {etat}</text>')
        # Le chiffre qui repond a la question de la densite.
        if plein:
            plants = 143000 // plein
            o.append(f'<text x="20" y="{y0 + CH/2 + 12}" font-size="9.5" '
                     f'fill="#9a938c">plein a {plein} mots</text>')
            o.append(f'<text x="20" y="{y0 + CH/2 + 26}" font-size="9.5" '
                     f'fill="#9a938c">these de 143 000 mots :</text>')
            o.append(f'<text x="20" y="{y0 + CH/2 + 40}" font-size="9.5" '
                     f'fill="#9a938c">~{plants} plants</text>')
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
    """
    Point ouvert 6 : les membres doivent rester proportionnes au corps.

    Deux pieges evites ici, tous deux deja rencontres ailleurs dans le projet.

    1. La premiere version ne montrait que l'etat CORRIGE : elle prouvait que
       le curseur marche, pas que la correction change quelque chose. On ne
       peut pas juger un correctif sans voir ce qu'il corrige.

    2. La deuxieme mettait chaque case a l'echelle independamment — donc une
       bete plus grande etait reduite pour tenir, et la difference qu'on
       voulait montrer se trouvait justement gommee. C'est le meme defaut que
       celui trouve dans composer() : une echelle par element efface les
       differences de taille. Ici toutes les figures partagent une echelle.
    """
    global MEMBRES_PROPORTIONNELS
    corps = [("gracile", 0.10), ("moyen", 0.5), ("massif", 1.0)]
    lignes = [("longueur absolue (v5)", False),
              ("proportionnelle au corps", True)]
    CW, CH, MG, TOP = 250, 240, 235, 62

    figures = {}
    for i, (_lab, mode) in enumerate(lignes):
        for j, (_n, cp) in enumerate(corps):
            garde, MEMBRES_PROPORTIONNELS = MEMBRES_PROPORTIONNELS, mode
            t = Toile()
            creature(t, 0.7, 0.8, 777, Teinte.du_jour(200, 14, 0.7),
                     etoffage={"tete": 0.4, "corps": cp, "membres": 1.0})
            MEMBRES_PROPORTIONNELS = garde
            figures[(i, j)] = t

    # Une seule echelle pour les six.
    encombrement = max(max(t.hauteur(), t.largeur() * 0.62)
                       for t in figures.values())
    k = (CH - 46) / encombrement

    W, H = MG + CW * len(corps) + 20, TOP + CH * 2 + 16
    o = _entete(W, H)
    for j, (lab, _) in enumerate(corps):
        o.append(f'<text x="{MG + j*CW + CW/2}" y="34" font-size="10.5" '
                 f'text-anchor="middle" letter-spacing="1.4">'
                 f'CORPS {lab.upper()}</text>')
    for i, (lab, _mode) in enumerate(lignes):
        y0 = TOP + i * CH
        o.append(f'<text x="18" y="{y0 + CH/2}" font-size="11.5" '
                 f'fill="#2c3230">{lab}</text>')
        for j, _c in enumerate(corps):
            t = figures[(i, j)]
            o.append(t.pose(MG + j * CW + CW / 2, y0 + CH - 16, k))
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


def planche_germination():
    """Ce que le volet montre avant qu'une famille soit connue."""
    paliers = [(60, "60 MOTS"), (190, "190 MOTS"), (400, "400 MOTS"),
               (620, "620 MOTS"), (800, "800 MOTS")]
    CW, CH, MG, TOP = 175, 185, 200, 56
    W, H = MG + CW * len(paliers) + 20, TOP + CH * 5 + 16
    o = _entete(W, H)
    for j, (_, lab) in enumerate(paliers):
        o.append(f'<text x="{MG + j*CW + CW/2}" y="32" font-size="10.5" '
                 f'text-anchor="middle" letter-spacing="1.4">{lab}</text>')
    lignes = [(None, "aucune tendance")] +              [(c, f"penche vers {n}") for c, (n, _) in FAMILLES.items()]
    for i, (cand, lab) in enumerate(lignes):
        y0 = TOP + i * CH
        o.append(f'<text x="18" y="{y0 + CH/2}" font-size="11.5" '
                 f'fill="#2c3230">{lab}</text>')
        for j, (mots, _) in enumerate(paliers):
            t = Toile()
            germe(t, min(1.0, mots / 800),
                  max(0.0, min(1.0, (mots - 200) / 600)),
                  cand, 31 + i * 7, Teinte.du_jour(110, 14, 0.7))
            o.append(t.svg(MG + j * CW, y0, CW, CH))
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
    for rich in (0.0, 0.35, 0.7, 1.0):
        tt = Teinte.du_jour(110, 14, rich)
        rng = random.Random(4)
        tons = sorted({tt.ton(rng) for _ in range(40)})
        print(f"  richesse {rich:.2f} -> {len(tons)} ton(s)   {' '.join(tons)}")

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
                    ("planche_dates", planche_dates),
                    ("planche_germination", planche_germination),
                    ("planche_pousse", planche_pousse)):
        open(f"{nom}.svg", "w", encoding="utf-8").write(fn())
        print(f"{nom}.svg ecrit")
    print()
    verifier()
