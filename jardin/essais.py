"""
Tous les essais, en un seul endroit, avec un code de sortie.

Avant ce fichier, chaque module avait son `verifier()` qui IMPRIMAIT ses
resultats et sortait avec le code 0 quoi qu'il arrive — banc.py compris. Un
banc d'essai qu'on ne peut consulter qu'en le lisant ne protege de rien : il
faut se souvenir de le lancer, et se souvenir de ce qu'il affichait avant.

Ici chaque verification est une assertion nommee. Le lanceur sort avec 1 des
qu'une seule echoue.

    python essais.py            tout
    python essais.py couleur    seulement les essais dont le nom contient ca
"""

from __future__ import annotations

import copy
import math
import random
import sys
import time

ESSAIS = []
LARGEUR = 78


def essai(nom):
    def poser(fn):
        ESSAIS.append((nom, fn))
        return fn
    return poser


# ==========================================================================
# traits.py
# ==========================================================================
@essai("traits / MATTR donne le meme resultat que la version naive")
def _():
    from traits import mattr, _sans_accent

    def naif(mots, fenetre=200):
        formes = [_sans_accent(m).lower() for m in mots]
        if len(formes) <= fenetre:
            return len(set(formes)) / len(formes)
        total = 0.0
        for i in range(len(formes) - fenetre + 1):
            total += len(set(formes[i:i + fenetre])) / fenetre
        return total / (len(formes) - fenetre + 1)

    rng = random.Random(1)
    vocab = [f"mot{i}" for i in range(900)]
    for n in (150, 400, 3000, 12000):
        mots = [rng.choice(vocab) for _ in range(n)]
        a, b = naif(mots), mattr(mots)
        assert abs(a - b) < 1e-12, f"n={n} : {a} != {b}"
    return "4 longueurs, ecart nul"


@essai("traits / MATTR est bien en O(n), pas en O(n x fenetre)")
def _():
    from traits import mattr, _sans_accent

    def naif(mots, fenetre=200):
        formes = [_sans_accent(m).lower() for m in mots]
        total = 0.0
        for i in range(len(formes) - fenetre + 1):
            total += len(set(formes[i:i + fenetre])) / fenetre
        return total / (len(formes) - fenetre + 1)

    # On mesure un RAPPORT, pas des millisecondes. Un seuil absolu dans une
    # batterie d'essais est un faux ami : la premiere version affichait 63 ms
    # un jour et 116 ms le lendemain selon ce qui tournait a cote, et
    # echouait donc sans qu'aucune ligne de code ait bouge. Ce qu'on affirme
    # est de toute facon un rapport — O(n) au lieu de O(n x fenetre) — et un
    # rapport se moque de la charge de la machine.
    rng = random.Random(1)
    mots = [f"mot{rng.randrange(900)}" for _ in range(30000)]

    def chrono(fn):
        return min(_mesure(fn, mots) for _ in range(3))

    def _mesure(fn, arg):
        t0 = time.perf_counter()
        fn(arg)
        return time.perf_counter() - t0

    lent, rapide = chrono(naif), chrono(mattr)
    facteur = lent / max(rapide, 1e-9)
    assert facteur > 4, f"seulement x{facteur:.1f} plus rapide que la version naive"
    # Le budget de 100 ms par tick, lui, est verifie par banc.py essai 6 sur
    # un tick reel — c'est la contrainte qui mord vraiment.
    return f"x{facteur:.0f} plus rapide sur 30 000 mots ({rapide*1000:.0f} ms)"


@essai("traits / le compteur de connecteurs ne sature pas avec la longueur")
def _():
    from traits import extraire
    import random as R

    # On passe par extraire(), sinon on ne teste que sa propre arithmetique :
    # premiere version de cet essai, elle recalculait la borne elle-meme et
    # laissait donc passer n'importe quel changement de traits.py.
    #
    # Texte fabrique exprès : beaucoup de connecteurs, AUCUNE virgule. La
    # subordination vaut alors 0,7 x 0 + 0,3 x (composante connecteurs), donc
    # elle donne directement a lire ce qu'on veut mesurer.
    CONN = ("que qui dont parce puisque quoique alors tandis lorsque afin"
            " malgre cependant toutefois neanmoins ainsi donc or car mais"
            " comme si quand").split()
    MOTS = [f"terme{i}" for i in range(400)]
    rng = R.Random(3)

    def texte_de(n_mots):
        out, n = [], 0
        while n < n_mots:
            phrase = []
            for _ in range(12):
                phrase.append(rng.choice(MOTS))
                if rng.random() < 0.25:
                    phrase.append(rng.choice(CONN))
            out.append(" ".join(phrase) + ".")
            n += len(phrase)
        return " ".join(out)

    mesures = [extraire(texte_de(n)).subordination for n in (600, 2500, 9000)]
    ecart = max(mesures) - min(mesures)
    # Avec l'ancien compteur (types presents), la mesure grimpe avec la
    # longueur : c'est la derive mecanique reprochee au TTR brut.
    assert ecart < 0.05, f"derive de {ecart:.3f} : {[round(x, 3) for x in mesures]}"
    return (f"600 -> 9 000 mots : {mesures[0]:.3f} -> {mesures[-1]:.3f}"
            f" (derive {ecart:.3f})")


@essai("traits / le compteur de connecteurs distingue encore deux styles")
def _():
    from traits import extraire
    import random as R

    # La stabilite avec la longueur ne suffit pas : une mesure qui vaut 1,00
    # partout est stable ET inutile. C'est d'ailleurs ce que devient l'ancien
    # compteur des qu'on lui laisse les bornes actuelles — saturee, donc
    # constante, donc aveugle. Il faut aussi qu'elle SEPARE.
    MOTS = [f"terme{i}" for i in range(400)]
    CONN = ("que qui dont parce puisque quoique alors tandis lorsque afin"
            " malgre cependant toutefois neanmoins ainsi donc or car mais"
            " comme si quand").split()

    def texte(part, graine):
        rng = R.Random(graine)
        out, n = [], 0
        while n < 3000:
            phrase = []
            for _ in range(12):
                phrase.append(rng.choice(MOTS))
                if rng.random() < part:
                    phrase.append(rng.choice(CONN))
            out.append(" ".join(phrase) + ".")
            n += len(phrase)
        return " ".join(out)

    riche = extraire(texte(0.30, 1)).subordination
    pauvre = extraire(texte(0.01, 2)).subordination
    assert riche - pauvre > 0.15, (
        f"un texte tres subordonne ({riche:.2f}) ne se distingue pas"
        f" d'un texte qui ne l'est pas ({pauvre:.2f})")
    return f"tres subordonne {riche:.2f} contre {pauvre:.2f}"


# ==========================================================================
# corpus.py
# ==========================================================================
@essai("corpus / chaque profil produit la famille qu'il vise")
def _():
    import corpus
    assert corpus.verifier(), "un profil au moins ne tombe pas juste"
    return "4 profils sur 4"


@essai("corpus / la these synthetique n'est pas faite de doublons")
def _():
    from corpus import these
    from paysage import empreinte
    d = these(mots_cibles=60000, chapitres=3, graine=5)
    uniques = len({empreinte(t) for t, *_ in d})
    part = uniques / len(d)
    assert part > 0.95, f"{part:.1%} de paragraphes distincts"
    return f"{part:.1%} distincts sur {len(d)} paragraphes"


# ==========================================================================
# paysage.py — les decisions
# ==========================================================================
@essai("paysage / les six essais de decision (banc.py)")
def _():
    import io
    import contextlib
    import banc
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        doc = banc.these()
        r = [banc.essai_1(), banc.essai_2(), banc.essai_3(), banc.essai_4()]
        ok5, _p = banc.essai_5(doc)
        r.append(ok5)
        r.append(banc.essai_6(doc))
    rates = [i + 1 for i, x in enumerate(r) if not x]
    assert not rates, f"essais rates : {rates}"
    return f"{len(r)}/{len(r)}"


@essai("paysage / le verrou attend des lectures ESPACEES, pas des ticks")
def _():
    import paysage as P
    from corpus import paragraphe
    from paysage import Paysage, MOTS_ENTRE_LECTURES, LECTURES_CONCORDANTES

    # On enregistre le nombre de mots a chaque lecture reelle. La decision 5
    # demande « 3 lectures concordantes d'affilee » : si elles tombent a
    # quelques mots d'intervalle, ce ne sont pas trois confirmations, c'est
    # trois fois la meme. jardin.py comptait des appels a mettre_a_jour, donc
    # six secondes dans un add-in cadence a 2 s.
    lectures = []
    vraie = P.Segment.relire

    def espionne(self):
        avant = self.mots_derniere_lecture
        r = vraie(self)
        if self.mots_derniere_lecture != avant:
            lectures.append((self.rang, self.mots, self.famille))
        return r

    P.Segment.relire = espionne
    try:
        # Profil a paragraphes COURTS : c'est la seule facon de voir
        # l'espacement jouer. Avec des paragraphes de 150 mots, une lecture
        # par paragraphe est deja espacee de 150 mots et la constante ne
        # change rien — l'essai passait meme en la mettant a zero.
        rng = random.Random(12)
        p = Paysage(identifiant="verrou")
        while not p.segments or not p.segments[0].verrouille:
            p.absorber(paragraphe(rng, "creature")[0], jour=40, heure=14)
            if p.segments[0].mots > 4000:
                break
    finally:
        P.Segment.relire = vraie

    du_plant = [m for r, m, _f in lectures if r == 0]
    verrou = next((m for r, m, f in lectures if r == 0 and f), None)
    assert verrou, "le plant 0 ne s'est jamais verrouille"
    avant = [m for m in du_plant if m <= verrou][-LECTURES_CONCORDANTES:]
    ecarts = [b - a for a, b in zip(avant, avant[1:])]
    assert len(avant) >= LECTURES_CONCORDANTES, f"{len(avant)} lectures seulement"
    # Le plancher vient de la DECISION, pas de la constante : comparer a
    # MOTS_ENTRE_LECTURES laisse l'essai s'adapter si on met la constante a
    # zero, ce qui est precisement la regression a attraper. Trois lectures
    # concordantes ne veulent dire quelque chose que si elles couvrent une
    # part notable des 800 mots du verrou.
    portee = avant[-1] - avant[0]
    assert portee >= 200,         f"les {LECTURES_CONCORDANTES} lectures du verrou ne couvrent que {portee} mots"
    return (f"verrou a {verrou} mots, {len(du_plant)} lectures,"
            f" espacees de {min(ecarts)}-{max(ecarts)} mots")


@essai("paysage / l'etat se serialise et se relit sans perte")
def _():
    from paysage import Paysage
    from corpus import paragraphe
    rng = random.Random(8)
    p = Paysage(identifiant="rt")
    for _ in range(60):
        p.absorber(paragraphe(rng, "creature")[0], jour=40, heure=14)
    avant = p.etat()
    q = Paysage.depuis(p.serialiser())
    apres = q.etat()
    for a, b in zip(avant["plants"], apres["plants"]):
        for cle in ("famille", "extension", "maturite", "dates", "nuit"):
            assert a[cle] == b[cle], f"{cle} : {a[cle]} != {b[cle]}"
    assert avant["empreintes"] == apres["empreintes"]
    return f"{len(avant['plants'])} plants, {avant['empreintes']} empreintes"


# ==========================================================================
# grammaire.py
# ==========================================================================
@essai("grammaire / le rendu est deterministe")
def _():
    from grammaire import dessiner, Teinte, FAMILLES
    for cle in FAMILLES:
        sig = set()
        for _ in range(3):
            t = dessiner(cle, 0.7, 0.8, 404, Teinte.du_jour(110, 14, 0.7))
            sig.add(tuple((round(s[0], 4), round(s[1], 4), s[5])
                          for s in t.segments))
        assert len(sig) == 1, f"{cle} instable"
    return "4 familles x 3 rendus"


@essai("grammaire / la couleur ne touche jamais la structure")
def _():
    from grammaire import dessiner, Teinte, FAMILLES, TRAIT
    total = 0
    for cle in FAMILLES:
        t = dessiner(cle, 0.7, 0.8, 404, Teinte.du_jour(110, 14, 0.7))
        squelette = [x for x in t.segments if x[6]]
        etoffage = [x for x in t.segments if not x[6]]
        assert squelette, f"{cle} n'a aucun segment de structure"
        fautifs = [x for x in squelette if x[5] != TRAIT]
        assert not fautifs,             f"{cle} : {len(fautifs)} segments de structure sont colores"
        assert any(x[5] != TRAIT for x in etoffage),             f"{cle} : aucun etoffage n'est colore"
        total += len(squelette)
    return f"{total} segments de structure, tous a l'encre"


@essai("grammaire / la palette de nuit ne ressemble a aucune saison")
def _():
    from grammaire import PALETTES

    def rvb(c):
        return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))

    def mini(a, b):
        return min(sum((x - y) ** 2 for x, y in zip(rvb(ca), rvb(cb))) ** 0.5
                   for ca in PALETTES[a] for cb in PALETTES[b])

    saisons = [k for k in PALETTES if k != "nuit"]
    nuit = min(mini("nuit", s) for s in saisons)
    # Le bon etalon n'est pas un seuil choisi au doigt mouille : c'est l'ecart
    # que deux SAISONS se laissent entre elles. Si la nuit est au moins aussi
    # distincte que l'ete l'est de l'automne, elle se reconnait.
    entre = min(mini(a, b) for i, a in enumerate(saisons) for b in saisons[i + 1:])
    assert nuit > entre * 1.5,         f"nuit a {nuit:.0f} d'une saison, mais deux saisons se frolent a {entre:.0f}"
    return f"nuit a {nuit:.0f} ; deux saisons se frolent a {entre:.0f}"


@essai("grammaire / le fondu de saison joue des DEUX cotes d'une frontiere")
def _():
    from grammaire import palette
    # Frontiere hiver -> printemps au jour 80.
    avant, apres = palette(74, 0), palette(86, 0)
    pur_hiver, pur_print = palette(40, 0), palette(120, 0)
    assert avant != pur_hiver, "pas de fondu du cote tardif"
    assert apres != pur_print, "pas de fondu du cote precoce"
    return f"j74 {avant} / j86 {apres}"


@essai("grammaire / le texte pilote la physionomie, pas seulement la couleur")
def _():
    from grammaire import dessiner, Teinte
    doux = {"dialogue": 0.1, "longueur": 0.1, "rythme": 0.1}
    fort = {"dialogue": 0.95, "longueur": 0.95, "rythme": 0.95}
    tt = Teinte.du_jour(200, 14, 0.7)
    a = dessiner("creature", 0.7, 0.8, 55, tt, doux)
    b = dessiner("creature", 0.7, 0.8, 55, tt, fort)
    assert len(a.segments) != len(b.segments) or a.bbox() != b.bbox(), \
        "deux textes opposes donnent la meme creature"
    ra = a.largeur() / a.hauteur()
    rb = b.largeur() / b.hauteur()
    return f"{len(a.segments)} vs {len(b.segments)} segments, silhouettes {ra:.2f} / {rb:.2f}"


@essai("grammaire / deux plants de la meme famille ne sont pas jumeaux")
def _():
    from grammaire import dessiner, Teinte
    tt = Teinte.du_jour(200, 14, 0.7)
    formes = set()
    for g in range(6):
        t = dessiner("creature", 0.8, 0.6, 100 + g * 977, tt)
        formes.add(tuple(round(v, 1) for v in t.bbox()))
    assert len(formes) == 6, f"{len(formes)} silhouettes distinctes sur 6"
    return "6 graines, 6 silhouettes"


# ==========================================================================
# Le germe
# ==========================================================================
@essai("germe / il ne se dessine rien avant d'avoir des mots")
def _():
    from grammaire import Toile, germe
    t = Toile()
    germe(t, 0.0, 0.0, None, 1)
    assert len(t.segments) <= 2, f"{len(t.segments)} traits pour zero mot"
    return f"{len(t.segments)} traits"


@essai("germe / l'echelle ne recule JAMAIS, meme au verrouillage")
def _():
    from composition import gabarit
    base = dict(rang=0, famille=None, pressentie=None, extension=0.0,
                maturite=0.0, dates=[(110, 1)], nuit=False, titre="",
                traits={}, germe={"taille": 0.0, "inflexion": 0.0})
    hauteurs = []
    for mots in range(0, 801, 40):
        p = copy.deepcopy(base)
        p["germe"] = {"taille": mots / 800,
                      "inflexion": max(0.0, (mots - 200) / 600)}
        p["pressentie"] = None if mots < 200 else "abstrait"
        gl, gh = gabarit(p, 1)
        hauteurs.append(max(gh, gl * 0.52))
    # Puis le verrouillage : la reference passe a la vraie famille.
    verrouille = copy.deepcopy(base)
    verrouille.update(famille="abstrait", extension=0.16, germe=None)
    gl, gh = gabarit(verrouille, 1)
    hauteurs.append(max(gh, gl * 0.52))
    # gabarit croissant => echelle de rendu decroissante => plant plus petit.
    # On veut donc que la reference ne CROISSE jamais.
    for i in range(1, len(hauteurs)):
        assert hauteurs[i] <= hauteurs[i - 1] + 1e-9, \
            f"la reference grandit a l'etape {i} : {hauteurs[i-1]:.0f} -> {hauteurs[i]:.0f}"
    return f"reference {hauteurs[0]:.0f} -> {hauteurs[-1]:.0f}, monotone"


@essai("germe / l'inflexion distingue les quatre familles")
def _():
    from grammaire import Toile, germe, FAMILLES
    formes = {}
    for cle in list(FAMILLES) + [None]:
        t = Toile()
        germe(t, 1.0, 1.0, cle, 7)
        formes[cle] = tuple(round(v, 1) for v in t.bbox())
    assert len(set(formes.values())) == len(formes), f"inflexions confondues : {formes}"
    return f"{len(formes)} germes distincts"


@essai("germe / a 200 mots aucune tendance n'est encore visible")
def _():
    from grammaire import Toile, germe, FAMILLES
    formes = set()
    for cle in list(FAMILLES) + [None]:
        t = Toile()
        germe(t, 200 / 800, 0.0, cle, 7)
        formes.add(tuple(round(v, 2) for v in t.bbox()))
    assert len(formes) == 1, f"{len(formes)} formes differentes avant l'inflexion"
    return "les cinq cas sont identiques, comme voulu"


# ==========================================================================
# message.py
# ==========================================================================
@essai("message / le cadre ne bouge pas pendant la revelation")
def _():
    from grammaire import Toile
    from message import message
    cadres = set()
    for av in (0.03, 0.2, 0.5, 0.8, 1.0):
        t = Toile()
        message(t, "il est tard, et tu ecris quand meme", av, graine=7)
        cadres.add(tuple(round(v, 4) for v in t.cadre))
    assert len(cadres) == 1, f"{len(cadres)} cadres differents"
    return "5 avancements, 1 cadre"


@essai("message / l'alphabet couvre toutes les phrases")
def _():
    from message import A
    import phrases
    manque = set()
    tout = (phrases.COMMUNES + phrases.NOMINATIVES + phrases.DEBLOCAGE
            + phrases.ELAN + phrases.CREUX)
    for profil in phrases.PROFILS.values():
        for brut in tout:
            t = phrases.sans_accent(brut.format(
                prenom=profil["prenom"], fort="fort" + profil["accord"])).upper()
            manque |= {c for c in t if c not in A}
    assert not manque, f"non tracables : {sorted(manque)}"
    return f"{len(tout)} phrases, 2 profils"


@essai("message / les lettres cessent de venir d'une grille")
def _():
    from grammaire import Toile
    from message import message
    angles = []
    for g in (11, 22, 33):
        t = Toile()
        message(t, "AAA", 1.0, corps=40, graine=g, largeur=8)
        angles.append(tuple(round(math.atan2(s[3] - s[1], s[2] - s[0]), 3)
                            for s in t.segments[:6]))
    assert len(set(angles)) == 3, "les angles sont identiques d'un tirage a l'autre"
    return "3 tirages, 3 jeux d'angles"


# ==========================================================================
# phrases.py
# ==========================================================================
@essai("phrases / les trois evenements sont routes correctement")
def _():
    from phrases import Nuit
    cas = [(["reprise"] * 6, "creux"),
           (["reprise"] * 5 + ["ecriture"], "deblocage"),
           (["ecriture"] * 8, "elan"),
           (["ecriture"] * 3, None)]
    for evenements, attendu in cas:
        n = Nuit()
        for v in evenements:
            n.enregistrer(v, 90)
        assert n.evenement() == attendu, f"{evenements[:3]}... -> {n.evenement()}"
    return "creux, deblocage, elan, ordinaire"


@essai("phrases / le paquet ne sert jamais deux fois de suite")
def _():
    from phrases import phrase_de_la_nuit, PROFILS
    from datetime import date
    vues, ecarts = {}, []
    for n in range(1095):                     # trois ans
        d = date.fromordinal(date(2027, 1, 1).toordinal() + n).isoformat()
        ph = phrase_de_la_nuit(PROFILS["camille"], d)
        if ph in vues:
            ecarts.append(n - vues[ph])
        vues[ph] = n
    mini = min(ecarts)
    # Le raccord casse donnait 1 : la meme phrase deux soirs de suite.
    assert mini >= 4, f"ecart minimum de {mini} nuits"
    return f"ecart minimum {mini}, moyen {sum(ecarts)/len(ecarts):.1f} nuits"


@essai("phrases / un registre vide retombe sur le paquet sans casser")
def _():
    from phrases import Nuit, phrase_de_la_nuit, PROFILS, CREUX
    n = Nuit()
    for _ in range(6):
        n.enregistrer("reprise")
    assert n.evenement() == "creux"
    ph = phrase_de_la_nuit(PROFILS["julien"], "2027-06-01", n)
    assert ph and isinstance(ph, str)
    return "creux vide -> repli, aucune exception"


@essai("grammaire / le vegetal pousse sans jamais reculer (decision 1)")
def _():
    import grammaire
    from paysage import MOTS_PAR_PLANT

    """
    Deux choses a la fois, parce qu'elles se contredisent si on n'y prend garde.

    GRANULARITE. L'extension n'entrait dans l'arbre que par
    « 4 + int(extension * 3.0) » : QUATRE formes sur toute la vie d'un plant,
    donc un changement visible toutes les 625 mots — deux pages et demie
    d'ecriture scientifique, parfois une semaine. La profondeur est devenue
    fractionnaire : les rameaux du dernier niveau sortent un par un.

    MONOTONIE. Le remede evident a la granularite — subdiviser plus fin —
    peut faire RECULER la forme, ce qu'interdit la decision 1. C'est arrive :
    le feuillage se partageait « BUDGET // pointes », le meme compte pour
    chaque bouquet. Un quotient entier n'est pas monotone (52 pointes a 4
    feuilles font 208 traits, 53 pointes a 3 en font 159), et l'arbre perdait
    un tiers de sa couronne en gagnant un rameau : mesure 271 -> 223,
    300 -> 235, 331 -> 230. L'ancienne version entiere le faisait deja, au
    dernier cran de chaque plant — l'arbre s'eclaircissait en s'achevant.

    ⚠️ LE POINT OUVERT QUE CE COMMENTAIRE PORTAIT EST FERME (decision 18).

    Il disait, et il avait entierement raison : « il reste un flottement connu,
    mesure et NON corrige : ouvrir un rameau decale toutes les valeurs tirees
    apres lui [...] le corriger demande de tirer les perturbations de l'arbre
    entier avant de dessiner ; c'est un point ouvert. » Le mecanisme, le remede
    et le statut y etaient. C'est fait : `_tirages()` lit le hasard par
    IDENTITE de lignee, plus par rang dans le flux.

    ⚠️ ET CE POINT OUVERT N'A JAMAIS FIGURE DANS `DECISIONS.md`. Il n'etait
    donc visible que de qui ouvrait ce fichier-la. La tolerance de 10 %
    ci-dessous couvrait exactement le defaut qu'il decrivait, et l'essai
    passait au vert en le disant.

    ⚠️ ET IL A SUFFI D'UN JOUR. Ce docstring date du 8 septembre
    2026 ; il a ete redecouvert le 9, apres une journee entiere passee a
    rediagnostiquer ce qu'il disait deja — dans ce fichier meme, edite tout du
    long. La premiere version de ce commentaire disait « des mois » : c'etait
    faux, le depot a cinq jours. La lecon n'en est pas adoucie, elle est
    durcie. Un point ouvert qui reste dans un commentaire n'existe pas ; ce
    n'est pas une affaire de DUREE, c'est une affaire d'ENDROIT.

    Le seuil vaut donc ZERO desormais, et c'est un seuil DE PRINCIPE — la
    decision 1 dit que rien ne recule — pas un seuil ajuste sur la mesure du
    jour, ce que ce docstring interdisait deja. Mesure sur quarante graines :
    3,91 % de pire recul et 161 pas en recul sur 2 000 avant, 0,00 % et zero
    pas apres.

    ⚠️ Cet essai compte les TRAITS ; celui qui s'appelle « un plant ne
    retrecit jamais quand il pousse » mesure l'ENCOMBREMENT et les ANCRES sur
    les quatre familles. C'est pour cette raison que celui-ci n'a jamais pu
    voir le rapetissement : un arbre peut garder son compte de traits en
    reculant, et c'est ce qu'il faisait.
    """
    pire, formes, reculs = 0.0, set(), 0
    for graine in (7, 41, 903):
        precedent = None
        for mots in range(0, MOTS_PAR_PLANT + 1, 50):
            t = grammaire.Toile()
            grammaire.vegetal(t, min(1.0, mots / MOTS_PAR_PLANT), 0.35, graine,
                              grammaire.Teinte.du_jour(120))
            n = len(t.segments)
            if graine == 7:
                formes.add(repr(t.segments))
            if precedent:
                if n < precedent:
                    reculs += 1
                pire = max(pire, (precedent - n) / precedent)
            precedent = n

    assert not reculs, (
        f"{reculs} pas de croissance retirent des traits a l'arbre, le pire"
        f" lui en coute {pire * 100:.2f} % : la forme recule, ce qu'interdit"
        f" la decision 1. Le seuil est zero et non 10 % depuis que le hasard"
        f" se lit par lignee — voir la decision 18")
    assert len(formes) >= 30, (
        f"seulement {len(formes)} formes distinctes sur la vie d'un plant :"
        f" l'extension ne fait plus bouger l'arbre qu'a gros crans")
    # Et L'ORDRE d'apparition, que ni la monotonie ni la granularite ne
    # voient : avec les rameaux sortis dans l'ordre naturel des lignees, le
    # compte des traits est exactement le meme a chaque pas — seulement, a
    # mi-pousse, une moitie de la couronne est garnie et l'autre est nue.
    # L'arbre pousse d'un cote. On regarde donc l'ordre lui-meme.
    #
    # Les huit lignees de GAUCHE du niveau 4 (16 a 23) doivent se repartir sur
    # toute la duree de la pousse, pas se presser au debut.
    gauche = [grammaire._rang_de_pousse(l) for l in range(16, 24)]
    assert max(gauche) > 0.8, (
        f"les huit rameaux de gauche du niveau 4 sortent tous en debut de"
        f" pousse (rang maximum {max(gauche):.2f}) : l'arbre pousse d'un cote")

    return (f"{len(formes)} formes distinctes, un changement tous les"
            f" {MOTS_PAR_PLANT / (len(formes) - 1):.0f} mots ;"
            f" pire recul {pire * 100:.1f} %")

@essai("composition / la camera recule, et ne fait que reculer")
def _():
    import re
    import composition
    from paysage import Paysage, MOTS_PAR_PLANT
    from corpus import paragraphe
    import random

    """
    Deux proprietes, et la seconde est celle qui a failli manquer.

    ELLE RECULE. Le cadre du volet valait la taille FINALE du plant : un plant
    a 5 % de sa taille finale occupait 5 % du volet, un cheveu, et la personne
    regarde un plant sans famille un tiers du temps. Le cadre interpole
    desormais entre la taille du moment et la taille finale (RECUL_CAMERA).

    ELLE NE FAIT QUE RECULER. C'est la seule chose qui fait tenir la decision 1
    ici, et c'est ce qui separe un exposant de la proposition rivale — des
    PALIERS de dezoom, ou chaque cran est un retrecissement visible. Un essai
    qui ne verifierait que la premiere propriete accepterait les paliers.

    ⚠️ On lit le cadre dans le viewBox du SVG, pas en le recalculant. Un essai
    qui refait le calcul teste sa propre arithmetique, pas le code.
    """
    def cadre(plants):
        svg = composition.vue_de_travail(plants, 1, 300, 380)
        vb = re.search(r'viewBox="([-\d. ]+)"', svg).group(1).split()
        return float(vb[3])

    rng = random.Random(11)
    p = Paysage(identifiant="camera")
    p.absorber("Chapitre unique", "Titre 1", 0, 30, 14)
    cadres, jalons = [], [0.05, 0.20, 0.50, 1.00]
    while jalons:
        p.absorber(paragraphe(rng, "vegetal")[0], jour=30, heure=14)
        if p.segments[-1].mots / MOTS_PAR_PLANT >= jalons[0]:
            jalons.pop(0)
            cadres.append(cadre(p.etat()["plants"]))

    # Elle recule : le cadre du germe est nettement plus serre que le final.
    assert cadres[0] < cadres[-1] * 0.75, (
        f"le cadre du plant jeune ({cadres[0]:.0f}) ne se distingue pas de"
        f" celui du plant plein ({cadres[-1]:.0f}) : la camera ne bouge pas,"
        f" et un germe reste un cheveu dans un grand cadre")

    # Et elle ne fait que reculer, ce qui exclut les paliers.
    for avant, apres in zip(cadres, cadres[1:]):
        assert apres >= avant - 1e-9, (
            f"le cadre est passe de {avant:.0f} a {apres:.0f} : la camera"
            f" s'est rapprochee, donc le plant a retreci — decision 1")

    return " -> ".join(f"{c:.0f}" for c in cadres)

@essai("paysage / la reprise murit le plant qui PORTE le texte (decision 2)")
def _():
    import random
    from corpus import paragraphe
    from paysage import Paysage, MOTS_PAR_PLANT

    """
    ⚠️ CET ESSAI EST NE D'UNE PANNE MESUREE EN VRAI WORD.

    retoucher() prenait _plant(), c'est-a-dire toujours le DERNIER segment —
    le seul plant qu'il savait nommer, puisque serialiser() exclut les textes
    et qu'a la reouverture aucun plant ne sait plus ce qu'il contient. Donc
    retravailler le chapitre 1 faisait murir le chapitre 8, et le chapitre 1 ne
    murissait jamais. Mesure sur cent vingt-trois plants : cinq retouches sur
    un paragraphe du plant 0 donnaient plant 0 maturite 0,000 et plant 122
    maturite 0,076. La moitie du travail d'une these — la reecriture — etait
    attribuee a l'endroit ou l'on se trouvait.

    Le registre porte desormais le rang du plant. On verifie les DEUX cotes :
    le vieux plant murit, et le courant ne murit pas.
    """
    rng = random.Random(3)
    p = Paysage(identifiant="attribution")
    p.absorber("Chapitre premier", "Titre 1", 0, 10, 14)
    premiers = []
    while len(p.segments) < 2:
        t = paragraphe(rng, "vegetal")[0]
        p.absorber(t, jour=10)
        premiers.append(t)
    p.absorber("Chapitre second", "Titre 1", 0, 40, 14)
    for _ in range(20):
        p.absorber(paragraphe(rng, "architecture")[0], jour=40)

    assert len(p.segments) >= 2, "il faut au moins deux plants pour que ca ait un sens"
    courant = p.segments[-1]
    vieux = p.segments[0]
    assert courant.rang != vieux.rang

    texte, avant_vieux, avant_courant = premiers[3], vieux.reprises, courant.reprises
    for _ in range(5):
        p.quitter()
        suivant = texte + " Une precision ajoutee."
        p.retoucher(texte, suivant, jour=41)
        texte = suivant

    assert vieux.reprises == avant_vieux + 5, (
        f"le plant qui porte le texte doit recevoir les cinq reprises,"
        f" obtenu {vieux.reprises - avant_vieux}")
    assert courant.reprises == avant_courant, (
        f"et le plant courant ne doit rien recevoir : il n'a pas ete touche,"
        f" obtenu {courant.reprises - avant_courant} reprises")
    assert vieux.maturite > 0, "le vieux plant doit murir"
    assert courant.maturite == 0, "le plant courant ne doit pas murir"

    # Et le volet doit cadrer le plant qui vient de changer, pas le dernier.
    actifs = [q["rang"] for q in p.etat()["plants"] if q["actif"]]
    assert actifs == [vieux.rang], (
        f"la camera doit revenir sur le plant retouche {vieux.rang},"
        f" obtenu {actifs}")

    # Une empreinte inconnue retombe sur le plant courant : c'est ce qui rend
    # leur comportement d'avant aux paysages de version 2.
    p.quitter()
    p.retoucher("Un texte que ce paysage n'a jamais vu passer, nulle part.",
                "Le meme, retouche une fois.", jour=42)
    assert courant.reprises == avant_courant + 1, (
        "une empreinte sans proprietaire connu doit retomber sur le plant"
        " courant")
    return (f"vieux plant : {vieux.reprises} reprises, maturite"
            f" {vieux.maturite:.3f} ; courant : {courant.reprises}")


@essai("paysage / un etat de version 2 se convertit au lieu d'etre jete")
def _():
    import json
    from paysage import Paysage, VERSION_ETAT, RANG_INCONNU

    """
    depuis() refusait tout ce qui n'etait pas la version courante et rendait un
    paysage VIDE. Monter la version sans migration effacerait donc le paysage
    de quelqu'un — et sa copie de secours dans le .docx avec, puisque les deux
    portent la meme version. C'est la pire chose que ce fichier puisse faire.
    """
    p = Paysage(identifiant="migration")
    p.absorber("Chapitre", "Titre 1", 0, 1, 14)
    for i in range(6):
        p.absorber(f"Un paragraphe numero {i}, ecrit a la main sans se presser.",
                   jour=1)
    d = json.loads(p.serialiser())
    assert d["version"] == VERSION_ETAT

    # La version 2 : les memes empreintes, sans proprietaire.
    vieux = dict(d, version=2,
                 registre=[e.rsplit(":", 1)[0] for e in d["registre"]])
    r = Paysage.depuis(json.dumps(vieux, ensure_ascii=False))
    assert len(r.registre) == len(p.registre), (
        f"les empreintes doivent survivre : {len(r.registre)} sur"
        f" {len(p.registre)}")
    assert len(r.segments) == len(p.segments), "et les plants aussi"
    assert set(r.registre.values()) == {RANG_INCONNU}, (
        "leurs proprietaires sont inconnus, et c'est exact : la version 2 ne"
        " les gardait pas")

    # Et ce qui n'est pas une version connue reste refuse.
    for mauvaise in (1, 99, "2", None):
        assert not Paysage.depuis(json.dumps(dict(d, version=mauvaise))).segments, (
            f"la version {mauvaise!r} ne doit rien rendre")
    return f"{len(r.registre)} empreintes conservees, proprietaires inconnus"

@essai("composition / le volet cadre le plant qui vient de changer")
def _():
    import re
    import random
    import composition
    from corpus import paragraphe
    from paysage import Paysage

    """
    ⚠️ IL NE SUFFIT PAS DE MARQUER LE PLANT ACTIF, IL FAUT QUE LE CADRE LE
    SUIVE. Le premier essai de l'attribution verifiait le drapeau « actif »
    rendu par etat(), et la mutation qui fait recadrer vue_de_travail() sur le
    dernier plant lui a echappe : rien ne traversait le cadre lui-meme.

    On lit donc le viewBox du SVG — pas un recalcul du cadre, qui testerait
    l'arithmetique de l'essai — et on verifie que le plant retouche y est, et
    que le dernier plant n'y est PAS. La seconde moitie est celle qui mord :
    sans elle, un cadre assez large pour tout contenir passerait.
    """
    rng = random.Random(17)
    p = Paysage(identifiant="camera")
    ecrits = []
    for c in range(6):
        p.absorber(f"Chapitre {c + 1}", "Titre 1", 0, 10 + c * 5, 14)
        while p.segments[-1].mots < 2000:
            t = paragraphe(rng, "vegetal")[0]
            p.absorber(t, jour=10 + c * 5)
            if c == 0:
                ecrits.append(t)
    assert len(p.segments) >= 6, f"il faut plusieurs plants, obtenu {len(p.segments)}"

    p.quitter()
    p.retoucher(ecrits[2], ecrits[2] + " Une precision tardive.", jour=60)
    plants = p.etat()["plants"]

    poses, _ = composition.composer(plants, 560, 1)
    poses_de = [q for q in plants
                if q.get("famille") or (q.get("germe") or {}).get("taille")]
    actifs = [n for n, q in enumerate(poses_de) if q["actif"]]
    assert actifs == [0], f"le plant retouche est le premier, obtenu {actifs}"

    svg = composition.vue_de_travail(plants, 1, 300, 380)
    vx, _vy, vw, _vh = (float(v) for v in
                        re.search(r'viewBox="([^"]+)"', svg).group(1).split())
    cx_actif = poses[actifs[0]][1]
    cx_dernier = poses[-1][1]
    assert vx <= cx_actif <= vx + vw, (
        f"le plant retouche (x={cx_actif:.0f}) doit etre dans le cadre"
        f" [{vx:.0f}, {vx + vw:.0f}]")
    assert not vx <= cx_dernier <= vx + vw, (
        f"le dernier plant (x={cx_dernier:.0f}) ne doit PAS y etre : la camera"
        f" est restee au bout au lieu de revenir")
    return (f"cadre [{vx:.0f}, {vx + vw:.0f}] sur le plant 0 (x={cx_actif:.0f}),"
            f" dernier a x={cx_dernier:.0f}")

@essai("traits / une prose academique n'est plus collee au plafond")
def _():
    from traits import extraire, revele

    """
    ⚠️ CET ESSAI EST NE D'UN EXTRAIT DE THESE REELLE.

    `longueur` plafonnait a 30 mots par phrase. L'extrait en faisait 32,2, donc
    le trait valait 1,000 partout, dans toutes les sections, du debut a la fin.
    Trois de ses cinq paragraphes y etaient colles alors que l'auteur va de
    24,6 a 41,6 mots par phrase.

    Et ca ne coutait pas qu'une physionomie plate : `longueur` pese 0,26 pour
    le vegetal et 0,20 EN NEGATIF pour l'architecture. A 1,000 elle donne 0,46
    d'avance a l'arbre avant qu'un seul titre soit compte. Il fallait HUIT
    titres dans 2 500 mots pour cesser d'etre un arbre, et on tombait alors
    dans l'abstrait par refus : LA VILLE ETAIT INATTEIGNABLE pour cet auteur,
    a n'importe quelle densite de structure.

    On compare des TEXTES entre eux, jamais a la constante : un essai qui dit
    « le plafond vaut 45 » s'adapte a la panne le jour ou on le casse.
    """
    def prose(mots_par_phrase, phrases=30):
        return " ".join(("territoire " * mots_par_phrase).strip() + "."
                        for _ in range(phrases))

    l = [extraire(prose(n)).longueur for n in (22, 32, 40)]
    assert l[0] < l[1] < l[2], (
        f"trois proses de 22, 32 et 40 mots par phrase doivent donner trois"
        f" longueurs distinctes, obtenu {l}")
    assert l[2] < 1.0, (
        f"a 40 mots par phrase le trait sature encore ({l[2]:.3f}) : une these"
        f" entiere retomberait sur la meme valeur")

    # ⚠️ ET LA CONSEQUENCE, QUI EST LE VRAI SUJET.
    #
    # `longueur` pese 0,26 pour le vegetal et 0,20 EN NEGATIF pour
    # l'architecture : a 1,000 elle donne 0,46 d'avance a l'arbre avant qu'un
    # seul titre soit compte. Une section charpentee restait un arbre a
    # n'importe quelle densite de structure — mesure sur une these reelle, il
    # fallait huit titres dans 2 500 mots pour cesser d'etre un arbre, et on
    # tombait alors dans l'abstrait par refus, jamais dans une ville.
    #
    # LE CORPUS EST CALE SUR DES STATISTIQUES MESUREES, pas invente : 33 mots
    # par phrase et une subordination de 0,59, contre 32,2 et 0,55 relevees sur
    # un extrait de these reelle. Un corpus moins subordonne devenait une ville
    # AVEC ET SANS le plafond casse, et l'essai n'aurait rien traverse — le
    # piege du cahier qui a l'air complet.
    #
    # Quatre phrases par paragraphe, et c'est l'autre nerf : a une phrase par
    # paragraphe il faut soixante-six paragraphes pour faire 2 500 mots, donc
    # huit titres n'en font que 11 % et la structure ne monte jamais. Un
    # paragraphe de these fait environ cent cinquante mots.
    phrases = [
        "Les colons europeens au nord du continent, plus tardivement que"
        " l Espagne, ont progressivement mis en place leurs propres formes"
        " d integration et institutionnalise ce processus au dix-neuvieme siecle.",
        "Cet ecart temporel montre que les puissances coloniales, meme si elles"
        " ont agi selon des modalites distinctes, ont toutes contribue a une"
        " meme logique de domination territoriale et culturelle.",
        "L assimilation n etait pas un phenomene homogene mais un processus"
        " etale dans le temps, dont l objectif commun restait de controler les"
        " territoires en effacant les identites culturelles des populations"
        " autochtones.",
        "A cette periode les colons passaient outre certains traites conclus"
        " avec des nations autochtones afin de revendiquer des terres"
        " appartenant legalement a ces dernieres, comme l illustrent les"
        " traites rompus au long du siecle.",
    ]
    titres = ["Introduction", "Chapitre III", "Conclusion partielle",
              "Sources primaires", "2.1. Les traites", "Bilan",
              "Annexe", "Corpus"]
    paras, pose, k = [], 0, 0
    while sum(len(p.split()) for p in paras) < 2500:
        paras.append(" ".join(phrases[(k + j) % len(phrases)] for j in range(4)))
        k += 1
        if len(paras) % 2 == 0 and pose < len(titres):
            paras.append(titres[pose])
            pose += 1
    t = extraire("\n\n".join(paras))
    r = revele(t)
    assert 0.50 < t.subordination < 0.65, (
        f"le corpus de l'essai a derive : subordination {t.subordination:.3f},"
        f" attendue autour de 0,59 — c'est la seule bande ou le plafond decide"
        f" du verdict, donc la seule ou l'essai prouve quelque chose")
    # Un garde-fou sur le corpus, pas la propriete eprouvee : on verifie que
    # le plant est bien charpente avant de lui demander de faire une ville.
    assert t.structure > 0.75, (
        f"huit titres devraient charpenter le plant, structure obtenue"
        f" {t.structure:.3f}")
    assert r.famille == "architecture", (
        f"une section de these decoupee par huit titres doit devenir une ville,"
        f" obtenu {r.famille}{' par refus' if r.par_refus else ''}"
        f" (scores {r.scores}) — avec le plafond a 30 elle restait un arbre"
        f" quelle que soit sa structure")
    return (f"longueurs {l[0]:.2f} / {l[1]:.2f} / {l[2]:.2f} ;"
            f" huit titres font une {r.famille}")


# --------------------------------------------------------------------------
# MATTR EST LU DEUX FOIS, ET LES DEUX LECTURES ONT CHACUNE LEUR ESSAI.
#
# On a longtemps cru qu'une seule borne pouvait servir aux deux metiers. Elle
# ne le peut pas, et la demonstration a coute un vrai paysage :
#
#   trop haute (0,55..0,80), elle ECRASE LE DESSIN — vingt plants sur quarante
#   valaient 0,000 et trois tons de palette sur cinq etaient inatteignables ;
#   trop basse (0,45..0,72), elle RENVERSE LE CLASSEMENT — l'abstrait pese
#   0,58 sur ce seul trait, donc l'elargir a ajoute +0,198 au score abstrait
#   de tous les plants a la fois, et une these entiere a perdu ses arbres pour
#   avoir gagne des couleurs.
#
# D'ou deux traits issus du meme MATTR : `diversite` classe, `richesse`
# dessine. Trois essais, un par risque :
#
#   1. `richesse` separe les familles A L'OEIL, et sa borne tient par les deux
#      bouts — rien a 0,000, rien a 1,000.
#   2. `diversite` garde le CLASSEMENT d'une these reelle, et le temoin porte
#      la ponctuation que l'auteur ecrit vraiment.
#   3. `richesse` n'entre dans AUCUN poids de famille — le jour ou elle y
#      entre, le partage est defait et on a refait l'erreur du 9 septembre.
# --------------------------------------------------------------------------
def _plants_de(famille, mots=1200, graines=3):
    """Des plants engendres, pas des caricatures reechantillonnees.

    ⚠️ Rejouer un echantillon de 300 mots pour en faire 2 500 ne marche
    PAS : il n'y reste que deux ou trois paragraphes eligibles, donc la
    fenetre de 200 mots voit sans arret des repetitions qui n'existent pas
    dans le texte, et MATTR s'effondre de 0,64 a 0,54. Mesure faite, erreur
    commise. Sur du texte reellement engendre, MATTR tient sa promesse : 0,591
    a 600 mots contre 0,594 a 2 500, d'ou les 1 200 mots d'ici — assez pour
    etre stable, assez peu pour que quarante-cinq relances restent gratuites.
    """
    import random
    from corpus import paragraphe
    out = []
    for g in range(graines):
        rng, bloc, n = random.Random(g), [], 0
        while n < mots:
            texte, _style = paragraphe(rng, famille)
            bloc.append(texte)
            n += len(texte.split())
        out.append("\n\n".join(bloc))
    return out


@essai("traits / la richesse lexicale separe les quatre familles")
def _():
    from traits import extraire
    from grammaire import Teinte
    from corpus import PROFILS

    # MATTR brut, mesure sur cent vingt plants : quatre familles, cinq
    # tailles de 600 a 2 500 mots, six graines.
    #   creature     0,4323..0,5078 (vocabulaire 34)
    #   architecture 0,4582..0,4879 (70)
    #   vegetal      0,5736..0,6070 (190)
    #   these reelle 0,6409..0,6442 (dix pages de l'auteur, deux plants)
    #   abstrait     0,6449..0,6896 (430)
    # `richesse` (0,42..0,70) doit rendre cet ordre LISIBLE A L'OEIL. C'est
    # son seul metier : nombre de tons, ouverture du feuillage, facettes.
    #
    # Les tailles comptent : un plant court descend plus bas qu'un long — la
    # creature perd 0,03 de MATTR entre 2 500 et 600 mots. Une borne calee sur
    # une seule taille ecrase les autres, ce qui est arrive avec 0,45.
    par_famille = {f: [extraire(t).richesse for t in _plants_de(f)]
                   for f in PROFILS}
    toutes = [r for rs in par_famille.values() for r in rs]

    veg, abs_ = par_famille["vegetal"], par_famille["abstrait"]
    pauvres = par_famille["architecture"] + par_famille["creature"]

    # Les deux bouts de la borne, chacun paye par une panne reelle.
    ecrases = [r for r in toutes if r <= 0.001]
    assert not ecrases, (
        f"{len(ecrases)} plants sur {len(toutes)} valent 0,000 de richesse :"
        f" c'est le regime ou la moitie du corpus etait plate et ou trois tons"
        f" de palette sur cinq etaient inatteignables")
    satures = [r for r in toutes if r >= 0.999]
    assert not satures, (
        f"{len(satures)} plants collent au plafond de richesse : la borne est"
        f" trop basse et le trait cesse de separer par l'autre bout")

    assert min(veg) - max(pauvres) > 0.25, (
        f"un vocabulaire de 190 mots ({min(veg):.3f}) ne se distingue plus"
        f" d'un vocabulaire de 34 ou 70 ({max(pauvres):.3f})")
    assert min(abs_) - max(veg) > 0.15, (
        f"l'abstrait ({min(abs_):.3f}) ne se detache plus du vegetal"
        f" ({max(veg):.3f}) : les deux se peindront pareil")

    tons = sorted({Teinte([(251, 1)], False, r).n_tons for r in toutes})
    assert len(tons) >= 3, (
        f"la palette n'utilise que {len(tons)} niveaux {tons} : avant le"
        f" partage il y en avait deux, 1 et 2, sur cinq possibles")
    return (f"architecture/creature {max(pauvres):.2f}, vegetal"
            f" {min(veg):.2f}, abstrait {min(abs_):.2f} — tons {tons}")


@essai("traits / une these lexicalement riche garde ses arbres")
def _():
    from traits import extraire, revele, MARGE_DOMINANCE
    from corpus import PROFILS, Profil

    # ⚠️ LE CAS QUE LE CORPUS NE SAIT PAS PRODUIRE, ET LE SEUL QUI DECIDE.
    #
    # Le corpus se classe 40/40 a TOUTES les bornes essayees, de 0,40..0,75 a
    # 0,55..0,80 : il ne peut pas arbitrer celle-ci. Ce qui l'arbitre est une
    # these reelle. Dix pages de l'auteur, decoupees comme l'add-in les
    # decoupe — deux plants de 2 624 et 2 138 mots :
    #
    #             longueur  subord.  ponct_rare  structure  MATTR   marge
    #   plant 1     0,555    0,488     0,256       0,136    0,6420  +0,155
    #   plant 2     0,701    0,598     0,530       0,000    0,6442  +0,169
    #
    # A la borne livree, ces deux plants basculeraient vers l'abstrait a 2,02
    # et 2,44 signes « ; : ( ) — … » pour cent mots. L'auteur en ecrit 0,99 et
    # 1,73. A la borne elargie a 0,45..0,72, les memes seuils tombaient a 0,74
    # et 1,16 — SOUS ce qui est ecrit — et les deux plants sont devenus
    # abstraits. C'est ce qui s'est passe sur son paysage, en une nuit.
    #
    # Le profil ci-dessous le reproduit : syntaxe vegetale peu subordonnee,
    # vocabulaire de l'abstrait, et une ponctuation rare de 0,400 a 0,489 —
    # dans la plage reellement ecrite. Ses marges vont de +0,108 a +0,161,
    # soit un peu SOUS les +0,155..+0,169 mesures : le temoin est plus dur que
    # la realite, ce qui est le bon sens de l'ecart.
    #
    # ⚠️ IL A LONGTEMPS PORTE rare=0,0, ET C'ETAIT L'ERREUR DANS L'ESSAI.
    # La borne fautive avait ete calee sur un extrait de 772 mots qui ne
    # contenait pas un seul signe rare ; le temoin heritait du meme angle
    # mort et ne tombait que pour un elargissement sur deux. Avec la densite
    # reelle, il tombe pour 0,45..0,72, pour 0,45..0,69, pour 0,50..0,80 et
    # meme pour 0,55..0,75.
    #
    # ⚠️ Le vegetal ORDINAIRE du corpus ne convient pas : sa subordination
    # sature a 1,00 et sa marge vaut +0,30, donc il reste vegetal meme avec la
    # borne cassee. L'essai aurait ete vert dans les deux cas — le piege du
    # cahier qui a l'air complet, pour la troisieme fois sur ce projet.
    v = PROFILS["vegetal"]
    PROFILS["these_riche"] = Profil(
        mots_par_phrase=32, dispersion=v.dispersion, virgules=0.30,
        connecteurs=0.15, structure=0.0, dialogue=0.0, questions=v.questions,
        rare=0.60, vocabulaire=PROFILS["abstrait"].vocabulaire,
        phrases_par_paragraphe=v.phrases_par_paragraphe,
        regularite=v.regularite)
    try:
        revelations = [revele(extraire(t))
                       for t in _plants_de("these_riche")]
    finally:
        del PROFILS["these_riche"]

    rares = [r.traits.ponctuation_rare for r in revelations]
    assert min(rares) > 0.20, (
        f"le temoin n'ecrit plus que {min(rares):.3f} de ponctuation rare :"
        f" il est retombe dans l'angle mort de l'extrait de 772 mots et ne"
        f" peut plus rien dire du trait qui decide")

    for i, r in enumerate(revelations):
        assert r.famille == "vegetal", (
            f"la these riche numero {i} devient {r.famille}"
            f"{' par refus' if r.par_refus else ''} (marge {r.marge:+.3f},"
            f" diversite {r.traits.diversite:.3f}, ponctuation rare"
            f" {r.traits.ponctuation_rare:.3f}) : une prose devient abstraite"
            f" par sa seule richesse lexicale, et un auteur perd tous ses"
            f" arbres d'un coup")
    marges = [r.marge for r in revelations]
    assert min(marges) > MARGE_DOMINANCE, (
        f"la marge tombe a {min(marges):+.3f} pour une marge de dominance de"
        f" {MARGE_DOMINANCE} : la these tient encore, mais au bord, et le"
        f" moindre chapitre un peu plus riche basculera")
    return (f"marges {min(marges):+.3f} a {max(marges):+.3f} pour"
            f" MARGE_DOMINANCE {MARGE_DOMINANCE}, ponctuation rare"
            f" {min(rares):.2f}..{max(rares):.2f}")


@essai("traits / le trait qui dessine n'entre jamais dans le classement")
def _():
    from dataclasses import replace
    from traits import POIDS, extraire, revele, scores

    # ⚠️ C'EST TOUTE LA DECISION, ET ELLE NE TIENT A RIEN D'AUTRE.
    #
    # `richesse` existe pour que le dessin puisse avoir sa propre echelle sans
    # deplacer la frontiere des familles. Le jour ou elle entre dans un poids,
    # le partage est defait en silence : elargir la borne pour voir des
    # couleurs recommencera a couter des arbres. Deux gardes, parce que le
    # premier seul se contourne en renommant.
    utilises = {nom for comps in POIDS.values() for nom, _p, _i in comps}
    assert "richesse" not in utilises, (
        f"`richesse` est entree dans POIDS ({sorted(utilises)}) : le trait de"
        f" DESSIN decide de nouveau du CLASSEMENT, et on a refait l'erreur du"
        f" 9 septembre")

    # Et le garde par le comportement : deux textes identiques dont seule la
    # richesse differe doivent se classer exactement pareil.
    #
    # ⚠️ `mots` est force au-dela de PALIER_DIVERGENCE. Sans ca la famille
    # vaut None des deux cotes — l'extrait ne fait pas 200 mots — et cette
    # moitie de l'essai comparait deux None : verte, et creuse.
    base = extraire(
        "Le colon europeen mettait sa masculinite a l'epreuve et la"
        " reaffirmait en se montrant digne des qualites qui y etaient"
        " associees, selon une perspective eurocentree, comme la force et le"
        " courage. Ces contre-modeles desservaient la binarite stricte"
        " opposant hommes et femmes, la naturalisation du genre et la"
        " hierarchisation des sexes, dont la portee reste discutee.")
    base = replace(base, mots=1200)
    pauvre, riche = replace(base, richesse=0.0), replace(base, richesse=1.0)
    assert scores(pauvre) == scores(riche), (
        f"changer la seule richesse change les scores : {scores(pauvre)}"
        f" contre {scores(riche)}")
    assert revele(pauvre).famille == revele(riche).famille, (
        f"changer la seule richesse change la famille :"
        f" {revele(pauvre).famille} contre {revele(riche).famille}")
    return (f"{len(utilises)} traits classent, richesse n'en est pas ;"
            f" 0,0 et 1,0 donnent {revele(riche).famille}")


@essai("grammaire / le plant se peint avec le trait du dessin, pas du classement")
def _():
    from dataclasses import asdict
    from traits import extraire
    import grammaire

    """
    ⚠️ CETTE MUTATION AVAIT ECHAPPE A TOUTE LA BATTERIE.

    `depuis_plant` est le seul point de contact entre l'etat d'un plant et son
    rendu : tout ce que le dessin sait du texte passe par cette ligne. Elle
    lit `richesse`. Lui faire lire `diversite` remet la couleur sous la
    dependance du trait qui CLASSE — c'est-a-dire defait le partage — et rien
    ne bronchait.

    Pourquoi rien ne bronchait : les deux sortent du meme MATTR et varient
    dans le MEME SENS. Un essai qui verifie « un texte plus riche fait plus de
    tons » reste vert quel que soit celui des deux qu'on lit. Ce qui les
    separe n'est pas le sens, c'est la VALEUR — il faut donc un texte ou elles
    sont franchement distinctes, et il faut le VERIFIER avant d'en conclure
    quoi que ce soit, sinon l'essai est creux.
    """
    texte = _plants_de("abstrait", mots=600, graines=1)[0]
    tr = asdict(extraire(texte))
    ecart = tr["richesse"] - tr["diversite"]
    assert ecart > 0.25, (
        f"les deux lectures de MATTR ne different plus que de {ecart:+.3f} sur"
        f" ce texte : l'essai ne peut plus distinguer laquelle est lue, et il"
        f" serait vert dans les deux cas")

    dates, nuit, graine = [(120, 3)], False, 7
    plant = {"famille": "abstrait", "extension": 0.6, "maturite": 0.4,
             "dates": dates, "nuit": nuit, "traits": tr}

    def peint(valeur):
        return grammaire.dessiner("abstrait", 0.6, 0.4, graine,
                                  grammaire.Teinte(dates, nuit, valeur),
                                  tr).segments

    par_richesse, par_diversite = peint(tr["richesse"]), peint(tr["diversite"])
    assert par_richesse != par_diversite, (
        f"les deux valeurs donnent le meme dessin ({len(par_richesse)}"
        f" segments identiques) : l'essai ne traverse rien et rassure pour"
        f" rien")

    assert grammaire.depuis_plant(plant, graine).segments == par_richesse, (
        f"le plant n'est pas peint avec `richesse` ({tr['richesse']:.3f}) :"
        f" la couleur est repassee par le trait de classement"
        f" ({tr['diversite']:.3f}), et le prochain elargissement de borne"
        f" recoutera des arbres")
    return (f"richesse {tr['richesse']:.2f} contre diversite"
            f" {tr['diversite']:.2f}, {len(par_richesse)} segments")


@essai("grammaire / un plant ne retrecit jamais quand il pousse (decision 1)")
def _():
    from grammaire import depuis_plant, TRAITS_NEUTRES

    """
    ⚠️ L'ESSAI QUI MANQUAIT SOUS TOUS LES AUTRES.

    La decision 1 dit que rien ne recule. Elle etait gardee UN CRAN TROP
    HAUT — par l'essai de camera, qui mesure le cadre du volet a travers
    la composition, le gabarit et la teinte. Il regardait une graine a
    quatre endroits : sur le code qui l'a introduit, 1 graine sur 50 le
    faisait tomber a quatre jalons, 48 sur 50 a huit. Il passait par
    chance.

    Ici on ne mesure plus rien d'assemble. TOUT EST CONSTANT SAUF
    L'EXTENSION — traits neutres, dates figees, maturite figee, graine
    figee — et on demande la seule chose qui doit etre vraie : ecrire
    plus ne peut pas faire un plant plus petit.

    ⚠️ CE QUE LE COMMENTAIRE DE `vegetal()` AFFIRMAIT, ET QUI ETAIT FAUX.
    « Un rameau pas encore sorti reste un BOURGEON [...] pousser consiste
    a ouvrir un bourgeon en rameau, ce qui est monotone. » Mesure : le
    vegetal reculait sur 8 graines sur 8, jusqu'a -14,3 %, et jusqu'a
    -16,3 % pour l'architecture. L'abstrait, lui, etait deja monotone.

    On mesure l'ENCOMBREMENT `max(h, l x 0.52)`, et pas la hauteur seule :
    c'est exactement la grandeur par laquelle `composer()` divise pour
    poser un plant dans le paysage, donc celle qui decide de la taille
    vue. Une hauteur qui tient pendant que la largeur s'effondre serait un
    retrecissement bien reel, et la hauteur seule ne le dirait pas.

    ⚠️ L'ECHANTILLONNAGE EST MESURE, PAS CHOISI AU FLAIR. A 4 graines et
    20 pas l'essai coute ~130 ms, soit 6,5 s sur les cinquante relances de
    `mutations.py`. Verifie avant de le fixer : de 2x10 a 8x60, tous les
    reglages essayes voyaient les trois familles fautives. Le defaut est
    dense — c'est le seul point commun qu'il n'a PAS avec celui de la
    camera, qui lui etait rare et n'a survecu que pour ca.
    """
    GRAINES, PAS = 4, 20

    def dessin(famille, graine, extension):
        return depuis_plant({"famille": famille, "extension": extension,
                             "maturite": 0.5, "dates": [(30, 1)],
                             "nuit": False, "rang": 0,
                             "traits": dict(TRAITS_NEUTRES)}, graine)

    def ancres(t):
        """Les abscisses du SQUELETTE. Le feuillage se deplace legitimement
        quand un bourgeon s'ouvre ; l'ossature, non."""
        return ({round(x[0], 2) for x in t.segments if x[6]}
                | {round(x[2], 2) for x in t.segments if x[6]})

    pires, effaces = [], []
    for famille in ("vegetal", "architecture", "creature", "abstrait"):
        for graine in range(GRAINES):
            suite = []
            for n in range(PAS):
                e = 0.05 + 0.95 * n / (PAS - 1)
                t = dessin(famille, graine, e)
                suite.append((e, max(t.hauteur(), t.largeur() * 0.52), ancres(t)))
            for (e0, a, an0), (e1, b, an1) in zip(suite, suite[1:]):
                if b < a - 1e-9:
                    pires.append((1 - b / a, famille, graine, e0, e1, a, b))
                if an0 - an1:
                    effaces.append((len(an0 - an1), famille, graine, e0, e1,
                                    len(an0)))

    pires.sort(reverse=True)
    assert not pires, (
        f"{len(pires)} reculs sur {4 * GRAINES * (PAS - 1)} pas de croissance,"
        f" le pire de {pires[0][0] * 100:.1f} % : {pires[0][1]} graine"
        f" {pires[0][2]} passe de {pires[0][5]:.1f} a {pires[0][6]:.1f} en"
        f" grandissant de {pires[0][3]:.2f} a {pires[0][4]:.2f} d'extension."
        f" Ecrire a fait retrecir le plant — c'est la decision 1, et elle se"
        f" voit a l'ecran")
    # ⚠️ ET LA SECONDE PROPRIETE, QUI EST LA PLUS FORTE DES DEUX.
    #
    #   Ne pas retrecir ne suffit pas : un plant peut garder sa taille en se
    #   redessinant entierement, et c'est ce qu'il faisait — 8,6 pour cent de
    #   ses traits survivaient d'un pas de croissance au suivant. Deux des
    #   mutations neuves ECHAPPAIENT a l'assertion ci-dessus tout en
    #   deplacant la moitie de la figure ; c'est en cherchant ce qu'elles
    #   cassaient qu'on a trouve la bonne formulation.
    #
    #   Une abscisse de squelette est une ANCRE : le montant d'une tour, un
    #   noeud de rameau, un point d'epine. Elle peut s'elever, s'epaissir, se
    #   colorer — elle ne doit pas DISPARAITRE. Ce qui pousse s'ajoute.
    effaces.sort(reverse=True)
    assert not effaces, (
        f"{len(effaces)} pas de croissance effacent une ancre deja posee ; le"
        f" pire en perd {effaces[0][0]} sur {effaces[0][5]} : {effaces[0][1]}"
        f" graine {effaces[0][2]} entre {effaces[0][3]:.2f} et"
        f" {effaces[0][4]:.2f} d'extension. Le plant ne pousse pas, il se"
        f" redessine — et ce que la personne regardait a bouge")
    return (f"{4 * GRAINES * (PAS - 1)} pas de croissance, aucun recul,"
            f" aucune ancre effacee")


@essai("grammaire / la couleur d'un trait lui appartient (decision 9)")
def _():
    from grammaire import depuis_plant, TRAITS_NEUTRES

    """
    ⚠️ LA DECISION 9 FAIT PORTER LA COULEUR PAR LA DATE D'ECRITURE.

    Un chapitre commence en fevrier et fini en mai montre les deux : chaque
    trait tire sa date dans la distribution {jour: mots} du plant. Encore
    faut-il que la date d'un trait soit une propriete DE CE TRAIT.

    Elle ne l'etait pas. `Teinte.ton(rng)` tirait dans le flux du dessin, donc
    la date d'un trait dependait de COMBIEN DE TRAITS AVAIENT ETE DESSINES
    AVANT LUI. Une feuille « ecrite en fevrier » devenait une feuille de mai a
    la frappe suivante, sans que rien de ce que la decision 9 decrit n'ait
    bouge. Mesure : un tiers des traits du vegetal, 18 pour cent de ceux de la
    creature, 4,6 pour cent des tours de la ville.

    ⚠️ CE N'ETAIT PAS UN SCINTILLEMENT A LA FRAPPE, et c'est ce qui l'a rendu
    invisible : 0 pour cent de changement a +1, +2 et +10 mots, puis un
    re-tirage d'un coup tous les quelques dizaines de mots. `randrange(n)`
    rejette et retire quand son tirage depasse n, et cette probabilite change
    avec n — or n vaut le nombre de mots du plant. Un seul rejet qui differe
    decale tout le reste du flux.

    ⚠️ DEUX ASSERTIONS, PARCE QU'UNE SEULE NE COUVRE PAS L'ARCHITECTURE. Ses
    tours GRANDISSENT en hauteur, donc presque aucun de ses traits ne se
    retrouve a l'identique d'un pas au suivant : la premiere assertion y est
    vraie sans rien dire. La seconde suit les tours par leur abscisse, qui,
    elle, ne bouge plus depuis la decision 18.
    """
    GRAINES, PAS = 3, 10
    DATES = [(200, 400), (201, 300), (205, 250)]   # trois jours, sinon la
    # date est constante et l'essai ne peut rien distinguer

    # ⚠️ MATURITE 0,70 ET NON 0,50, ET CE N'EST PAS UN DETAIL.
    #   `Toile.noeud()` ne fabrique RIEN tant que la maturite ne depasse pas
    #   0,55 — et les noeuds ne vont pas dans `segments` mais dans `noeuds`.
    #   Ecrit d'abord a 0,50 en ne regardant que `segments`, cet essai ne
    #   traversait donc pas du tout la couleur des noeuds : deux mutations
    #   passaient au travers sans qu'il bronche. C'est le troisieme piege de
    #   CLAUDE.md — un cahier qui a l'air complet et ne traverse jamais le
    #   mecanisme surveille — repris a une ligne pres.
    MATURITE = 0.70

    def dessin(famille, graine, extension):
        return depuis_plant({"famille": famille, "extension": extension,
                             "maturite": MATURITE, "dates": DATES,
                             "nuit": False, "rang": 0,
                             "traits": dict(TRAITS_NEUTRES)}, graine)

    def couleurs(t):
        """Traits ET noeuds : les seconds portent aussi une date."""
        d = {(round(x[0], 3), round(x[1], 3),
              round(x[2], 3), round(x[3], 3)): x[5] for x in t.segments}
        for x in t.noeuds:
            d[("noeud", round(x[0], 3), round(x[1], 3))] = x[3]
        return d

    vires = []
    for famille in ("vegetal", "architecture", "creature", "abstrait"):
        for graine in range(GRAINES):
            precedent = None
            for n in range(PAS):
                e = 0.05 + 0.95 * n / (PAS - 1)
                cour = couleurs(dessin(famille, graine, e))
                if precedent is not None:
                    for cle in set(precedent) & set(cour):
                        if precedent[cle] != cour[cle]:
                            vires.append((famille, graine, e,
                                          precedent[cle], cour[cle]))
                precedent = cour
    assert not vires, (
        f"{len(vires)} traits gardent leur place et CHANGENT de couleur ; le"
        f" premier est un {vires[0][0]} de graine {vires[0][1]} a"
        f" {vires[0][2]:.2f} d'extension, {vires[0][3]} devenu {vires[0][4]}."
        f" La date d'un trait ne lui appartient plus : elle depend de combien"
        f" de traits ont ete dessines avant lui")

    assert any(isinstance(k, tuple) and k and k[0] == "noeud"
               for k in couleurs(dessin("vegetal", 0, 1.0))), (
        "l'essai ne voit aucun noeud : ils ne naissent qu'au-dessus de"
        " maturite 0,55 et ne sont pas dans `segments`. Sans eux il ne"
        " traverse pas la moitie des points de couleur")

    def tours(t):
        """Une tour, ce sont ses horizontales de trame, reperees par abscisse."""
        par = {}
        for x in t.segments:
            if not x[6] and abs(x[1] - x[3]) < 1e-9:
                par.setdefault(round((x[0] + x[2]) / 2, 1), set()).add(x[5])
        return {a: sorted(c) for a, c in par.items()}

    bougees = []
    for graine in range(GRAINES + 3):
        precedent = None
        for n in range(PAS):
            cour = tours(dessin("architecture", graine, 0.05 + 0.95 * n / (PAS - 1)))
            if precedent is not None:
                for a in set(precedent) & set(cour):
                    if precedent[a] != cour[a]:
                        bougees.append((graine, a))
            precedent = cour
    assert not bougees, (
        f"{len(bougees)} tours changent de couleur en restant a leur place,"
        f" la premiere a l'abscisse {bougees[0][1]} de la graine"
        f" {bougees[0][0]} : la ville se recolore quand elle s'agrandit")
    return "quatre familles, aucune couleur ne bouge sous un trait qui reste"


@essai("grammaire / la structure du texte change la silhouette de l'arbre")
def _():
    import grammaire

    """
    L'arbre ne lisait que subordination, regularite et longueur — les trois
    traits les plus STABLES chez un meme auteur. Mesure sur cent vingt plants
    simules d'une these : le texte faisait varier l'encre de 19 % quand la
    seule GRAINE la faisait varier de 37 %. Deux chapitres differaient surtout
    par chance.

    `structure` est le trait qui bouge le plus dans une these — de 0,00 a 0,91
    selon qu'une section est decoupee en titres ou coule d'un trait — et le
    vegetal l'ignorait. Une bibliographie, un chapitre a sous-parties et un
    chapitre de recit donnaient le meme arbre.

    On mesure l'ELANCEMENT (hauteur / largeur) et pas la taille : la
    composition divise chaque plant par son encombrement final, donc la taille
    brute ne survit pas au paysage. La proportion, si.
    """
    import statistics

    # ⚠️ CET ESSAI TIRAIT UNE SEULE GRAINE, ET SON SEUIL ETAIT CALE
    # DESSUS. Mesure sur vingt graines avec le code d'AVANT toute reparation :
    # mediane 1,351, minimum 1,206, et DEUX graines sur vingt DEJA sous le seuil
    # de 1,25. Il ne tenait donc pas la propriete, il tenait la graine 3 — et
    # n'importe quel changement du hasard le faisait tomber sans que rien de
    # reel n'ait bouge. C'est exactement ce qui est arrive quand la croissance
    # est devenue additive : la mediane n'a pas bronche (1,336), la graine 3
    # est passee de l'autre cote.
    #
    # On mesure donc la MEDIANE sur douze graines. Meme propriete, meme seuil,
    # mais il porte enfin sur ce qu'il pretend mesurer.

    GRAINES = 12

    def elancement(structure, graine):
        tr = dict(grammaire.TRAITS_NEUTRES, structure=structure)
        t = grammaire.Toile()
        grammaire.vegetal(t, 1.0, 0.5, graine, grammaire.Teinte.du_jour(120),
                          traits=tr)
        x0, y0, x1, y1 = t.bbox()
        return (y1 - y0) / max(x1 - x0, 1.0), len(t.segments)

    plats = [elancement(0.0, g) for g in range(GRAINES)]
    dresses = [elancement(0.9, g) for g in range(GRAINES)]
    plat = statistics.median(e for e, _ in plats)
    dresse = statistics.median(e for e, _ in dresses)
    n_plat = statistics.median(n for _, n in plats)
    n_dresse = statistics.median(n for _, n in dresses)
    assert dresse > plat * 1.25, (
        f"un texte charpente doit se dresser : elancement median {plat:.2f}"
        f" sans structure contre {dresse:.2f} avec, soit {dresse / plat:.2f}"
        f" fois sur {GRAINES} graines — il en faut au moins 1,25")
    # Et l'axe ne doit PAS ajouter de bois : c'est une difference de port.
    assert abs(n_dresse - n_plat) < n_plat * 0.10, (
        f"l'axe change le nombre de traits ({n_plat} -> {n_dresse}) : il"
        f" simule de la pousse au lieu de redresser la forme")
    return f"elancement {plat:.2f} -> {dresse:.2f}, {n_plat} -> {n_dresse} traits"


@essai("grammaire / le vocabulaire ouvre le feuillage, sans en ajouter")
def _():
    import math
    from collections import defaultdict
    import grammaire

    """
    Le feuillage s'ouvrait a 0,40 radian par feuille, quel que soit le texte.
    La richesse lexicale ne servait qu'a la couleur. Elle ouvre maintenant le
    bouquet : un lexique large fait une etoile, un lexique etroit une brosse.

    Elle passe par `richesse`, jamais par `diversite` : le feuillage est du
    DESSIN. Lire ici le trait de classement remettrait la frontiere des
    familles au bout d'un pinceau.

    ⚠️ Le NOMBRE de feuilles ne bouge pas, et c'est la moitie importante de
    l'essai : il est tenu par le budget, et la decision 1 interdit qu'il
    recule. Si ouvrir le feuillage se mettait a en ajouter, un texte au
    vocabulaire riche paraitrait plus AVANCE qu'un texte pauvre de meme
    longueur — de la maturite deguisee en extension.
    """
    import statistics

    # ⚠️ CET ESSAI TIRAIT UNE SEULE GRAINE, ET SON SEUIL ETAIT CALE
    # DESSUS. Mesure sur vingt graines avec le code d'AVANT toute reparation :
    # mediane 1,371, minimum 1,061, et SEPT graines sur vingt DEJA sous le seuil
    # de 1,30. Il ne tenait donc pas la propriete, il tenait la graine 3 — et
    # n'importe quel changement du hasard le faisait tomber sans que rien de
    # reel n'ait bouge. C'est exactement ce qui est arrive quand la croissance
    # est devenue additive : la mediane n'a pas bronche (1,351), la graine 3
    # est passee de l'autre cote.
    #
    # On mesure donc la MEDIANE sur douze graines. Meme propriete, meme seuil,
    # mais il porte enfin sur ce qu'il pretend mesurer.

    GRAINES = 12

    def bouquet(richesse, graine):
        tr = dict(grammaire.TRAITS_NEUTRES, richesse=richesse)
        t = grammaire.Toile()
        grammaire.vegetal(t, 1.0, 0.5, graine, grammaire.Teinte.du_jour(120),
                          traits=tr)
        par = defaultdict(list)
        for s in t.segments:
            if not s[6]:                       # les feuilles, pas le squelette
                par[(round(s[0], 6), round(s[1], 6))].append(
                    math.atan2(s[3] - s[1], s[2] - s[0]))
        larges = [max(a) - min(a) for a in par.values() if len(a) > 1]
        return sum(larges) / len(larges), sum(len(a) for a in par.values())

    serres = [bouquet(0.0, g) for g in range(GRAINES)]
    ouverts = [bouquet(1.0, g) for g in range(GRAINES)]
    serre = statistics.median(a for a, _ in serres)
    ouvert = statistics.median(a for a, _ in ouverts)
    n_serre = statistics.median(n for _, n in serres)
    n_ouvert = statistics.median(n for _, n in ouverts)
    assert ouvert > serre * 1.30, (
        f"un lexique riche doit ouvrir le bouquet : {math.degrees(serre):.0f}"
        f" degres contre {math.degrees(ouvert):.0f} en mediane sur {GRAINES}"
        f" graines — il en faut au moins 30 % de plus")
    assert n_serre == n_ouvert, (
        f"le nombre de feuilles a bouge ({n_serre} -> {n_ouvert}) : ouvrir le"
        f" feuillage ne doit jamais en ajouter, sinon le vocabulaire simule de"
        f" la pousse")
    return (f"bouquet {math.degrees(serre):.0f} -> {math.degrees(ouvert):.0f}"
            f" degres, {n_serre} feuilles dans les deux cas")


@essai("grammaire / le port distingue deux plants SANS mentir sur la taille")
def _():
    import grammaire

    """
    ⚠️ CET ESSAI GARDE LA DECISION 2 CONTRE UNE BONNE IDEE.

    « Rajouter de l'aleatoire sur la pousse : tres long, tres grand, gros. »
    L'intention est juste — deux chapitres doivent faire deux arbres — mais un
    plant plus GROS au hasard, c'est l'invariant cardinal qui tombe : la taille
    dit combien on a ecrit, et si la graine la tire, tripoter et ecrire
    deviennent indistinguables a l'oeil.

    La composition l'annulerait de toute facon : elle divise chaque plant par
    son encombrement final (composer(), k), donc deux plants acheves
    remplissent le meme cadre quoi qu'on tire. Ce qui SURVIT a cette
    normalisation, c'est la proportion — angles serres et longues entre-noeuds
    font un peuplier, angles ouverts et entre-noeuds courts un pommier.

    On verifie donc les deux moities : le port change la PROPORTION, et il ne
    change pas la QUANTITE DE BOIS.
    """
    # ⚠️ ON MESURE L'ECART-TYPE, PAS LE MIN/MAX, ET C'EST TOUT LE SUJET.
    #
    # La premiere version de cet essai comparait le plus elance au plus etale
    # sur vingt-quatre graines. Elle PASSAIT avec le port neutralise : sans
    # lui, l'inclinaison du tronc et la vigueur produisent deja un rapport de
    # 1,42 entre les deux extremes — plus que les 1,39 obtenus AVEC le port.
    # Deux tirages extremes ne disent rien de ce que fait la population.
    #
    # Sur deux cents graines, l'ecart-type relatif separe net : 6,3 % sans le
    # port, 14,5 % avec. La mutation qui le neutralise se fait donc prendre,
    # ce qui n'etait pas le cas avant.
    import statistics

    els, comptes = [], []
    for graine in range(200):
        t = grammaire.Toile()
        grammaire.vegetal(t, 1.0, 0.5, graine, grammaire.Teinte.du_jour(120))
        x0, y0, x1, y1 = t.bbox()
        els.append((y1 - y0) / max(x1 - x0, 1.0))
        comptes.append(len(t.segments))

    disperse = statistics.pstdev(els) / statistics.fmean(els)
    assert disperse > 0.10, (
        f"deux cents plants du meme texte ont presque le meme port :"
        f" ecart-type relatif de l'elancement {disperse * 100:.1f} % — il en"
        f" faut plus de 10 pour que deux chapitres se distinguent, et"
        f" l'inclinaison du tronc en donne deja 6 a elle seule")
    ecart = (max(comptes) - min(comptes)) / statistics.fmean(comptes)
    assert ecart < 0.10, (
        f"le port fait varier le nombre de traits de {ecart * 100:.0f} % :"
        f" la graine se met a simuler de la pousse, ce qu'interdit la"
        f" decision 2 ({min(comptes)} a {max(comptes)} traits)")
    return (f"elancement disperse a {disperse * 100:.1f} %"
            f" pour {ecart * 100:.1f} % d'ecart de bois")

# ==========================================================================
# composition.py
# ==========================================================================
@essai("composition / l'extension est visible dans le paysage")
def _():
    from composition import composer
    def plant(rang, ext):
        return dict(rang=rang, famille="architecture", pressentie=None,
                    extension=ext, maturite=0.3, dates=[(110, 1)], nuit=False,
                    titre="c", traits={}, germe=None)
    poses, _ = composer([plant(0, 0.25), plant(1, 1.0)], 560, 1)
    hauteurs = [t.hauteur() * k for d, cx, y, k, t in
                sorted(poses, key=lambda q: q[1])]
    assert hauteurs[0] < hauteurs[1] * 0.75, \
        f"un plant a 25 % fait {hauteurs[0]:.0f} contre {hauteurs[1]:.0f} a 100 %"
    return f"{hauteurs[0]:.0f} px a 25 % contre {hauteurs[1]:.0f} px a 100 %"


@essai("composition / le volet n'est jamais vide, meme sur un plant neuf")
def _():
    from composition import vue_de_travail
    plants = [dict(rang=0, famille="vegetal", pressentie=None, extension=1.0,
                   maturite=0.5, dates=[(110, 1)], nuit=False, titre="c1",
                   traits={}, germe=None),
              dict(rang=1, famille=None, pressentie=None, extension=0.0,
                   maturite=0.0, dates=[(115, 1)], nuit=False, titre="c2",
                   traits={}, germe={"taille": 0.02, "inflexion": 0.0})]
    s = vue_de_travail(plants)
    assert s.count("<line") > 30, f"{s.count('<line')} traits dans le volet"
    return f"{s.count('<line')} traits avec un plant de 20 mots"


@essai("composition / vue de travail et apercu passent par le meme rendu")
def _():
    import ast
    import composition

    # Verification STRUCTURELLE, pas textuelle. La premiere version comptait
    # les "<svg xmlns=" dans le source et se declenchait des qu'une planche
    # assemblait son propre cadre — un essai qui casse quand on ajoute une
    # planche ne surveille pas ce qu'il pretend surveiller. Ce qui compte
    # n'est pas combien de fois la chaine apparait, c'est que les deux vues
    # passent par rendre().
    arbre = ast.parse(open(composition.__file__, encoding="utf-8").read())
    appels = {}
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.FunctionDef):
            appels[noeud.name] = {
                n.func.id for n in ast.walk(noeud)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    for vue in ("svg", "svg_apercu", "vue_de_travail"):
        assert "rendre" in appels.get(vue, set()), \
            f"{vue}() ne passe pas par rendre() : les vues peuvent diverger"
    return "svg, svg_apercu et vue_de_travail passent tous par rendre()"


@essai("composition / un paysage vierge ne fait pas planter le volet")
def _():
    from composition import vue_de_travail, svg, svg_apercu
    for fn in (vue_de_travail, svg, svg_apercu):
        s = fn([])
        assert s.startswith("<svg"), fn.__name__
    return "3 vues sur une liste vide"


# --------------------------------------------------------------------------
# Le serrage du massif.
#
# ⚠️ Les deux essais qui suivent mesurent sur les POSES, jamais sur la
# constante. Lire _serrage() et comparer a ce qu'elle renvoie serait comparer
# la constante a elle-meme : elle s'adapterait a la panne. On lit donc les
# abscisses rendues et les gabarits, ce qui traverse gabarit(), l'echelle, la
# profondeur et le placement — et ce qui se casse si l'un d'eux se casse.
# --------------------------------------------------------------------------
# ⚠️ LE BALAYAGE SE FAIT EN ABSTRAIT, ET C'EST UNE QUESTION DE DUREE.
#
# Ecrit d'abord en vegetal, il posait mille six cent trente-six plants et
# faisait passer essais.py de 10,1 a 22,9 secondes. mutations.py relance
# essais.py quarante-quatre fois : neuf minutes ajoutees a une chaine qui doit
# rester assez courte pour qu'on ne soit pas tente de la paralleliser — ce
# qu'il ne faut surtout pas faire. Mesure : douze plants coutent 114 ms en
# vegetal (4 124 traits) contre 5 ms en abstrait (636).
#
# Le serrage est un simple facteur sur la largeur reservee, donc la pose ne
# depend pas de la famille. L'essai le VERIFIE au lieu de le supposer : sans
# ca, un balayage en abstrait ne dirait rien du paysage de l'auteur, qui porte
# vingt-deux vegetaux sur trente-cinq. Les trois seuils que le lecteur voit se
# mesurent d'ailleurs sur SA famille.
TAILLES_DE_MASSIF = tuple(range(2, 41))


def _massif(n, titre="c", depart=0, famille="abstrait"):
    """n plants acheves du MEME chapitre : une seule parcelle."""
    return [dict(rang=depart + r, famille=famille, pressentie=None,
                 extension=1.0, maturite=0.0, dates=[(110, 1)], nuit=False,
                 titre=titre, traits={}, germe=None) for r in range(n)]


def _bandes(plants):
    """Pour chaque plant : (bord gauche, largeur reservee), dans l'apercu."""
    from composition import apercu, gabarit
    poses, largeur = apercu(plants, 520, 1)
    bandes = []
    for p, (_d, cx, _y, k, _t) in zip(plants, poses):
        # La graine est celle d'apercu(). Si elle change la, elle doit changer
        # ici : l'essai mesurerait sinon le gabarit d'un autre plant.
        gl, _gh = gabarit(p, 1 + p["rang"] * 977)
        bandes.append((cx - gl * k / 2, gl * k))
    return bandes, largeur


def _decouverts(n, famille="abstrait"):
    """La part de chaque plant que le SUIVANT ne recouvre pas."""
    bandes, _ = _bandes(_massif(n, famille=famille))
    return [(x1 - x0) / l0 for (x0, l0), (x1, _l1) in zip(bandes, bandes[1:])]


@essai("composition / un gros chapitre ne se tasse plus en haie")
def _():
    # Le defaut, releve dans le vrai Word : trente-cinq plants, quatre
    # Titre 1, donc des massifs de 6, 6, 14 et 9 la ou le serrage avait ete
    # regle pour trois. 55 % de recouvrement moyen — le premier arbre etait le
    # seul lisible du paysage, parce que le seul dont le cote gauche fut libre.
    court = _decouverts(3, "vegetal")
    assert max(court) < 0.55, (
        f"trois plants d'un meme chapitre ne se recouvrent plus qu'a"
        f" {(1 - max(court)) * 100:.0f} % : c'est le cas pour lequel 0,46"
        f" avait ete regle, il ne devait pas bouger")
    large = _decouverts(14, "vegetal")
    assert min(large) > 0.80, (
        f"dans un massif de quatorze, un plant n'en montre que"
        f" {min(large) * 100:.0f} % : c'est la haie qu'on vient de corriger")
    assert max(large) < 0.99, (
        f"un massif de quatorze ne se recouvre plus du tout"
        f" ({max(large):.3f}) : il ne se distingue plus d'une suite de"
        f" chapitres d'un seul plant, et les trois niveaux se confondent")
    deux = _decouverts(2, "vegetal")
    assert 0.30 < min(deux) < 0.55, (
        f"deux plants d'un meme chapitre se posent a {min(deux):.3f} : sous"
        f" zero, le second est A GAUCHE du premier et le paysage se lit a"
        f" l'envers")

    # L'INVARIANT, et c'est lui qui porte la decision : un massif cache
    # toujours la meme chose, qu'il en porte trois ou quarante. Ce rapport ne
    # se compare a aucune constante — casser PLANTS_CACHES le laisse a 1,00,
    # casser la FORME de la regle le fait exploser.
    mesures = {t: _decouverts(t) for t in TAILLES_DE_MASSIF}

    # La pose ne depend pas de la famille. C'est ce qui autorise le balayage
    # ci-dessous a se faire en abstrait ; sans cette ligne, il mesurerait un
    # paysage que personne n'a.
    assert abs(max(large) - max(mesures[14])) < 1e-9, (
        f"un massif de quatorze se pose a {max(large):.4f} en vegetal et"
        f" {max(mesures[14]):.4f} en abstrait : le serrage a cesse d'etre un"
        f" simple facteur sur la largeur reservee")

    totaux = [sum(1 - v for v in mesures[t])
              for t in TAILLES_DE_MASSIF if t >= 3]
    assert max(totaux) / min(totaux) < 1.02, (
        f"le total cache dans un massif depend de sa taille :"
        f" {min(totaux):.2f} a {max(totaux):.2f} largeurs de plant")

    # Et il ne se tasse jamais davantage quand le chapitre grossit.
    moyennes = [(t, sum(mesures[t]) / (t - 1)) for t in TAILLES_DE_MASSIF]
    for (ta, a), (tb, b) in zip(moyennes, moyennes[1:]):
        assert b >= a - 1e-12, (
            f"un massif de {tb} plants se serre plus qu'un de {ta}"
            f" ({b:.3f} contre {a:.3f})")
    return (f"3 plants a {court[0]:.2f}, 14 a {min(large):.2f},"
            f" {min(totaux):.2f} largeur cachee quelle que soit la taille")


@essai("composition / un gros massif reste un massif")
def _():
    # Ce que le desserrement pouvait couter : si les plants d'un chapitre
    # cessent de se toucher, plus rien ne distingue un massif de deux
    # parcelles voisines, et les trois niveaux du point 6 tombent — sans
    # qu'aucune image ne soit fausse pour autant. C'est le genre de perte
    # qu'on ne voit pas en regardant une planche.
    # ⚠️ En VEGETAL, explicitement : c'est la famille dont l'auteur a
    # vingt-deux plants sur trente-cinq, et les trois niveaux se jugent sur la
    # silhouette la plus large des quatre. Vingt-quatre plants ne coutent que
    # deux dixiemes de seconde ; le balayage, lui, en posait mille six cents.
    plants = (_massif(12, "c1", famille="vegetal")
              + _massif(12, "c2", depart=12, famille="vegetal"))
    bandes, _ = _bandes(plants)
    inter = [x1 - (x0 + l0) for (x0, l0), (x1, _l1) in zip(bandes, bandes[1:])]
    dedans = inter[:11] + inter[12:]
    entre = inter[11]
    assert max(dedans) < 0, (
        f"deux plants d'un massif de douze ne se touchent plus :"
        f" {max(dedans):.1f} px d'ecart")
    largeur_moyenne = sum(l for _x, l in bandes) / len(bandes)
    assert entre > largeur_moyenne * 0.4, (
        f"la respiration de parcelle ne fait plus que {entre:.0f} px pour des"
        f" plants de {largeur_moyenne:.0f} : le chapitre ne se voit plus")
    return (f"douze plants chevauches de {-max(dedans):.0f} a"
            f" {-min(dedans):.0f} px, {entre:.0f} px entre deux chapitres")


@essai("composition / la meme redaction donne le meme paysage")
def _():
    from composition import _demonstration, svg
    a = svg([p for p in _demonstration(mots=12000, graine=3).etat()["plants"]])
    b = svg([p for p in _demonstration(mots=12000, graine=3).etat()["plants"]])
    assert a == b, "deux rejeux du meme document donnent deux paysages"
    return f"{len(a)} caracteres de SVG, identiques"


# ==========================================================================
# guet.py
# ==========================================================================
@essai("guet / Entree et Maj+Entree donnent les memes lignes")
def _():
    from guet import decouper
    par_entree = decouper("un\rdeux\rtrois")
    par_saut = decouper("un\x0bdeux\x0btrois")
    assert par_entree == par_saut == ["un", "deux", "trois"], (par_entree, par_saut)
    # Le document reel qui a motive tout ceci : 1119 sauts, zero retour chariot.
    melange = decouper("a\rb\x0bc\nd")
    assert melange == ["a", "b", "c", "d"], melange
    return "point 14 : l'unite est la ligne ecrite, pas le paragraphe de Word"


@essai("guet / le premier instantane ne fait rien pousser")
def _():
    from guet import Guet
    g = Guet()
    depart = g.amorcer("Alpha\x0bBeta\x0bGamma")
    # rattacher() attend des couples (texte, style) : l'amorce les rend prets.
    assert depart == [("Alpha", "Normal"), ("Beta", "Normal"),
                      ("Gamma", "Normal")], depart
    assert g.relever("Alpha\x0bBeta\x0bGamma") == [], "un instantane egal doit etre muet"
    return "decision 11 : le capital de depart n'est pas une pousse"


@essai("guet / une ligne herite du style de son paragraphe")
def _():
    from guet import decouper_marque, Guet
    corps = "Titre du chapitre\rUne ligne.\x0bUne autre.\rUne citation."
    lignes, appartenance = decouper_marque(corps)
    assert lignes == ["Titre du chapitre", "Une ligne.", "Une autre.",
                      "Une citation."], lignes
    # Les deux lignes du deuxieme paragraphe pointent le meme paragraphe : c'est
    # ce qui leur donne le meme style sans le demander a Word ligne par ligne.
    assert appartenance == [0, 1, 1, 2], appartenance

    styles = ["Titre 1", "Normal", "Citation"]
    g = Guet()
    assert g.amorcer(corps, styles) == [
        ("Titre du chapitre", "Titre 1"), ("Une ligne.", "Normal"),
        ("Une autre.", "Normal"), ("Une citation.", "Citation")], \
        g.amorcer(corps, styles)
    # Sans style, une citation compterait comme de l'ecriture (point 3) et un
    # Titre 1 n'ouvrirait plus de plant (point 6). Deux pannes muettes.
    faits = g.relever(corps.replace("Une autre.", "Une autre ligne."), styles)
    assert [f["style"] for f in faits] == ["Normal"], faits
    return "le style descend du paragraphe a ses lignes, exactement"


@essai("guet / une table de styles absente ou courte ne fait pas lever")
def _():
    from guet import Guet
    corps = "A\rB\rC"
    for table in (None, [], ["Titre 1"], ["a", "b", "c", "d", "e"]):
        g = Guet()
        depart = g.amorcer(corps, table)
        assert len(depart) == 3, (table, depart)
        # Une table absente, trop courte ou decalee d'un releve doit rendre
        # « Normal » plutot que lever : une exception dans un tic arreterait
        # tout, alors qu'un style faux se corrige au releve suivant.
        for _texte, style in depart:
            assert isinstance(style, str) and style, (table, depart)
    return "4 tables de travers, aucune exception"


@essai("guet / le compte de paragraphes dit quand les styles sont perimes")
def _():
    from guet import Guet, compter_paragraphes
    assert compter_paragraphes("") == 0
    assert compter_paragraphes("un seul") == 1
    assert compter_paragraphes("a\rb\rc") == 3

    g = Guet()
    g.amorcer("a\rb")
    assert g.paragraphes == 2, g.paragraphes
    # Taper DANS un paragraphe ne change pas la structure : la lecture couteuse
    # des styles — un objet Office.js par paragraphe — n'a pas a repartir.
    g.relever("aa\rb")
    assert g.paragraphes == 2, g.paragraphes
    g.relever("aa\rb\rc")
    assert g.paragraphes == 3, g.paragraphes
    return "la table ne se rafraichit que quand la structure bouge"


@essai("guet / inserer au milieu ne decale aucune identite")
def _():
    from guet import Guet
    g = Guet()
    g.amorcer("A\x0bB\x0bC")
    avant = list(g.ids)
    faits = g.relever("A\x0bX\x0bB\x0bC")
    # LE cas du point 14. Identifier par le rang aurait rendu trois retouches
    # et une naissance : de l'extension prise pour de la maturite.
    assert [f["type"] for f in faits] == ["nee"], [f["type"] for f in faits]
    assert g.ids[0] == avant[0] and g.ids[2] == avant[1] and g.ids[3] == avant[2], \
        f"les voisines ont perdu leur identifiant : {avant} -> {g.ids}"
    return "une insertion reste une naissance, pas une pluie de retouches"


@essai("guet / une ligne deplacee ne rend aucun verdict")
def _():
    from guet import Guet
    g = Guet()
    g.amorcer("A\x0bB\x0bC\x0bD")
    avant = list(g.ids)
    faits = g.relever("A\x0bC\x0bB\x0bD")
    # Decision 3 : un deplacement est gratuit. L'appariement par rang en aurait
    # fait deux retouches, donc de la maturite inventee sans que personne
    # n'ait rien recrit.
    assert faits == [], [f["type"] for f in faits]
    assert g.ids == [avant[0], avant[2], avant[1], avant[3]], (avant, g.ids)
    return "decision 3 : l'identifiant suit son texte, et rien n'est signale"


@essai("guet / une retouche rend le texte d'avant")
def _():
    from guet import Guet
    g = Guet()
    g.amorcer("A\x0bB\x0bC")
    faits = g.relever("A\x0bBis\x0bC")
    assert len(faits) == 1, faits
    # paysage.retoucher() a besoin des DEUX textes : sans l'ancien, il ne peut
    # pas distinguer une reprise d'une premiere redaction.
    assert faits[0]["type"] == "retouchee", faits[0]
    assert faits[0]["ancien"] == "B" and faits[0]["texte"] == "Bis", faits[0]
    assert faits[0]["id"] == g.ids[1], "l'identifiant doit survivre a la retouche"
    return "l'ancien texte voyage avec la retouche"


@essai("guet / supprimer une ligne compacte les identifiants")
def _():
    from guet import Guet
    g = Guet()
    g.amorcer("A\x0bB\x0bC")
    avant = list(g.ids)
    faits = g.relever("A\x0bC")
    assert [f["type"] for f in faits] == ["disparue"], faits
    assert faits[0]["id"] == avant[1] and faits[0]["ancien"] == "B", faits[0]
    assert g.ids == [avant[0], avant[2]], (avant, g.ids)
    return "la disparition nomme la ligne partie, les autres ne bougent pas"


@essai("guet / un collage rend autant de naissances que de lignes")
def _():
    from guet import Guet
    g = Guet()
    g.amorcer("A\x0bB")
    faits = g.relever("A\x0bP1\x0bP2\x0bP3\x0bB")
    # C'est ce nombre que le debit de la decision 4 mesure : un bloc arrive
    # d'un coup, et c'est le bloc qu'il faut voir, pas une ligne a la fois.
    assert [f["type"] for f in faits] == ["nee"] * 3, [f["type"] for f in faits]
    assert [f["texte"] for f in faits] == ["P1", "P2", "P3"], faits
    return "trois lignes d'un bloc, trois naissances dans un seul releve"


@essai("guet / la visite se ferme apres le silence, et une seule fois")
def _():
    from guet import Guet
    g = Guet(silence=3)
    g.amorcer("A\x0bB")
    g.relever("A\x0bBb")                       # on ecrit : la visite s'ouvre
    vus = []
    for _tour in range(6):
        vus.append([f["type"] for f in g.relever("A\x0bBb")])
    # Sans cette fermeture, revenir sur une ligne une semaine plus tard reste la
    # meme visite : plant.reprises ne monte jamais et l'element cesse de MURIR.
    assert vus == [[], [], ["visite_finie"], [], [], []], vus
    return "une seule fermeture, au bon tour, puis plus rien"


@essai("guet / ecrire ailleurs ne demande aucune fermeture")
def _():
    from guet import Guet
    g = Guet(silence=3)
    g.amorcer("A\x0bB")
    g.relever("Aa\x0bB")
    faits = g.relever("Aa\x0bBb")
    # _actif n'a qu'une case : ecrire ailleurs la deplace, et revenir tombe
    # forcement dans la branche « reprise ». Le guet n'a rien a emettre.
    assert [f["type"] for f in faits] == ["retouchee"], faits
    assert g.visitee == g.ids[1], (g.visitee, g.ids)
    return "changer de ligne ferme la visite tout seul, dans paysage.py"


@essai("guet / le compte de silence repart des qu'on ecrit")
def _():
    from guet import Guet
    g = Guet(silence=3)
    g.amorcer("A")
    g.relever("Aa")
    g.relever("Aa")
    g.relever("Aa")                             # deux tours de calme
    assert g.calme == 2, g.calme
    g.relever("Aaa")                            # on reprend : le compte tombe
    assert g.calme == 0 and g.visitee is not None, (g.calme, g.visitee)
    types = [f["type"] for f in g.relever("Aaa")]
    assert types == [], types
    return "une pause de deux tours ne ferme rien"


@essai("guet / mille lignes, un tic n'en signale qu'une")
def _():
    from guet import Guet
    lignes = [f"Ligne numero {i}, avec assez de texte pour ressembler a une phrase."
              for i in range(1000)]
    g = Guet()
    g.amorcer("\x0b".join(lignes))
    lignes[500] += " Et un ajout."
    faits = g.relever("\x0b".join(lignes))
    # C'est tout l'interet du rognage : sur une these, un releve ne rend pas
    # mille verdicts, il en rend un.
    assert len(faits) == 1 and faits[0]["type"] == "retouchee", len(faits)
    assert faits[0]["id"] == g.ids[500], "la bonne ligne doit etre nommee"
    return "1000 lignes, 1 verdict"


@essai("guet / une ligne nee vide qui se remplit est une ecriture")
def _():
    from guet import Guet
    from paysage import Paysage
    p, g = Paysage(), Guet()
    p.rattacher(g.amorcer("Un debut de chapitre ecrit a la main."), 10, 14)

    def tour(texte):
        f = g.relever(texte)
        return [v["verdict"] for v in g.nourrir(p, f, 10, 14, g.debit(f))]

    # Word cree une ligne VIDE a chaque Entree ; le guet la voit naitre, donc
    # elle revient ensuite en « retouchee » avec un ancien texte vide.
    assert tour("Un debut de chapitre ecrit a la main.\x0b") == ["vide"]
    avant = p.segments[0].mots
    # Sans la conversion, absorber() n'aurait jamais pose _actif, retoucher()
    # tomberait dans « nouvelle visite », et LE PREMIER MOT DE CHAQUE LIGNE
    # NEUVE serait une reprise. L'extension n'existerait plus.
    assert tour("Un debut de chapitre ecrit a la main.\x0bIl faut donc") == ["ecriture"]
    assert tour("Un debut de chapitre ecrit a la main.\x0bIl faut donc admettre.") \
        == ["frappe"]
    assert p.segments[0].mots > avant, "les mots tapes doivent compter"
    assert p.segments[0].reprises == 0, "et aucune reprise ne doit etre comptee"
    return "vide, puis ecriture, puis frappe — jamais une reprise"


@essai("guet / une ligne neuve echappe au registre quand on l'a vue naitre")
def _():
    from guet import Guet
    from paysage import Paysage
    p, g = Paysage(), Guet()
    debut = "Il faut donc admettre que la chose est entendue."
    p.rattacher(g.amorcer(debut), 10, 14)

    def tour(texte):
        f = g.relever(texte)
        return [v["verdict"] for v in g.nourrir(p, f, 10, 14, g.debit(f))]

    # En francais, une ligne sur deux commence par les memes mots. Sans le
    # drapeau de naissance, le registre declarerait « connue » une ligne
    # genuinement neuve et le plant cesserait de pousser, sans rien signaler.
    tour(debut + "\x0b")
    assert tour(debut + "\x0b" + debut) == ["ecriture"], \
        "une ligne vue naitre doit passer outre le registre"
    return "le registre passe apres ce qu'on a vu de ses propres yeux"


@essai("guet / un collage retravaille se convertit en ecriture")
def _():
    from guet import Guet
    from paysage import Paysage
    from paysage import SEUIL_COLLAGE
    p, g = Paysage(), Guet()
    p.rattacher(g.amorcer("Un debut ecrit a la main."), 10, 14)
    colle = " ".join("mot%d" % i for i in range(SEUIL_COLLAGE * 4))

    def tour(texte):
        f = g.relever(texte)
        return [v["verdict"] for v in g.nourrir(p, f, 10, 14, g.debit(f))]

    assert tour("Un debut ecrit a la main.\x0b" + colle) == ["greffe"]
    assert g.greffes, "le guet doit retenir quelles lignes sont des greffes"
    # LE PONT NE L'A JAMAIS SU : il passait toujours etait_greffe=False, donc
    # cette branche n'etait jamais atteinte dans l'add-in et un chapitre colle
    # puis retravaille restait une greffe pour toujours.
    assert tour("Un debut ecrit a la main.\x0b" + colle + " et une suite ecrite.") \
        == ["conversion"]
    assert not g.greffes, "et l'oublier une fois convertie"
    assert p.segments[0].greffes == 0, "le plant ne doit plus compter de greffe"
    return "point 4 : la greffe retravaillee devient de l'ecriture"


@essai("guet / une suppression ne rend rien au paysage")
def _():
    from guet import Guet
    from paysage import Paysage
    p, g = Paysage(), Guet()
    p.rattacher(g.amorcer("Alpha.\x0bBeta.\x0bGamma."), 10, 14)
    avant = dict(mots=p.segments[0].mots, reprises=p.segments[0].reprises)
    f = g.relever("Alpha.\x0bGamma.")
    v = g.nourrir(p, f, 10, 14, g.debit(f))
    # Point 3 : le registre garde l'empreinte, donc supprimer ne coute rien.
    assert [x["verdict"] for x in v] == ["disparue"], v
    assert p.segments[0].mots == avant["mots"], "rien ne doit reculer"
    assert p.segments[0].reprises == avant["reprises"], "ni murir"
    return "decision 3 : une suppression est gratuite"


@essai("guet / le debit se ramene a l'intervalle, jamais au-dela")
def _():
    from guet import Guet, INTERVALLE
    g = Guet()
    g.amorcer("Depart.")
    faits = g.relever("Depart.\x0bun deux trois quatre")
    # Un releve EN RETARD : quatre mots arrives en dix secondes valent moins
    # que quatre mots en deux secondes.
    lent = g.debit(faits, 10000)
    normal = g.debit(faits, INTERVALLE)
    assert lent < normal, (lent, normal)
    # ⚠️ Un releve EN AVANCE ne doit PAS amplifier. Divise par cinq
    # millisecondes, quatre mots deviendraient un debit de mille six cents et
    # passeraient pour un collage. Le plancher est l'intervalle, pas 1.
    rapide = g.debit(faits, 5)
    assert rapide == normal, (rapide, normal)
    return f"4 mots : {normal:.0f} a l'heure, {lent:.1f} en retard, {rapide:.0f} en avance"


@essai("guet / une reprise par visite, et une seule")
def _():
    from guet import Guet
    from paysage import Paysage
    p, g = Paysage(), Guet(silence=2)
    base = "Une ligne posee la, et rien d'autre"
    p.rattacher(g.amorcer(base + "."), 10, 14)

    def tour(texte):
        f = g.relever(texte)
        return [v["verdict"] for v in g.nourrir(p, f, 10, 14, g.debit(f))]

    # Le document existait deja : retoucher une ligne rattachee EST une reprise.
    tour(base + ", avec une suite.")
    assert p.segments[0].reprises == 1, p.segments[0].reprises
    # Dans la meme visite, on suit le texte sans rien recompter — sinon dix
    # minutes de reecriture compteraient trois cents passages.
    tour(base + ", avec une suite plus longue.")
    tour(base + ", avec une suite bien plus longue encore.")
    assert p.segments[0].reprises == 1, "une seule reprise par visite"

    vus = []
    for _tour in range(3):
        vus += tour(base + ", avec une suite bien plus longue encore.")
    assert "visite finie" in vus, vus

    # Visite neuve : le droit a une reprise est rouvert. Sans quitter(),
    # plant.reprises ne monterait plus jamais et l'element cesserait de murir —
    # c'est l'axe de la maturite qui meurt, pas celui de l'extension.
    tour(base + ", avec une troisieme suite.")
    assert p.segments[0].reprises == 2, p.segments[0].reprises
    return "trois retouches d'affilee valent une reprise, la quatrieme en vaut deux"


@essai("guet / coller dans la ligne qu'on ecrit ne la fait pas pousser")
def _():
    from guet import Guet
    from paysage import Paysage, SEUIL_COLLAGE
    p, g = Paysage(), Guet()
    base = "Un debut de chapitre ecrit a la main."
    p.rattacher(g.amorcer(base), 10, 14)

    def tour(texte):
        f = g.relever(texte)
        return [v["verdict"] for v in g.nourrir(p, f, 10, 14, g.debit(f))]

    tour(base + "\x0b")
    assert tour(base + "\x0bUne ligne neuve tapee a la main.") == ["ecriture"]
    avant = p.segments[0].mots

    # LE TROU PAR LEQUEL UN VRAI DOCUMENT EST PASSE D'UNE TIGE A UN ARBRE.
    # La decision 4 ne gardait qu'absorber() : coller dans la ligne qu'on est
    # EN TRAIN d'ecrire ajoutait tous les mots, sans le moindre controle.
    colle = " ".join("mot%d" % i for i in range(SEUIL_COLLAGE * 10))
    assert tour(base + "\x0bUne ligne neuve tapee a la main. " + colle) == ["greffe"]
    assert p.segments[0].mots == avant, \
        f"un collage ne doit pas ajouter un mot : {avant} -> {p.segments[0].mots}"
    assert p.segments[0].greffes == 1, "et il doit rester en attente"
    return "la meme arrivee compte pareil dans une ligne neuve et dans une ligne en cours"


@essai("guet / un collage vu tard reste un collage")
def _():
    from guet import Guet, INTERVALLE, PLAFOND_ECOULE
    from paysage import Paysage, SEUIL_COLLAGE

    def coller(ecoule):
        p, g = Paysage(), Guet()
        base = "Un debut de chapitre ecrit a la main."
        p.rattacher(g.amorcer(base), 10, 14)
        colle = " ".join("mot%d" % i for i in range(SEUIL_COLLAGE * 13))
        f = g.relever(base + "\x0b" + colle)
        d = g.debit(f, ecoule)
        return [v["verdict"] for v in g.nourrir(p, f, 10, 14, d)], d, p.segments[0].mots

    tot, d_tot, mots_tot = coller(INTERVALLE)
    tard, d_tard, mots_tard = coller(60000)
    assert tot == ["greffe"], tot
    # Sans plafond, le meme collage vu une minute plus tard donnait un debit de
    # 6,7 et passait pour de l'ECRITURE : deux cents mots comptes pour rien.
    # Un evenement arrive QUAND la chose se produit ; un instantane ne dit pas
    # quand le texte est arrive. L'asymetrie tranche — une greffe declaree a
    # tort se convertit en la retravaillant, une pousse declaree a tort ne se
    # rattrape jamais.
    assert tard == ["greffe"], (tard, d_tard)
    assert mots_tard == mots_tot, "un collage tardif ne doit rien ajouter"
    assert d_tard < d_tot, "le retard doit quand meme reduire le debit"
    return f"debit {d_tot:.0f} vu tot, {d_tard:.0f} vu tard, greffe dans les deux cas"


@essai("guet / le plafond ne transforme pas la frappe en collage")
def _():
    from guet import Guet, PLAFOND_ECOULE
    from paysage import Paysage
    p, g = Paysage(), Guet()
    base = "Un debut de chapitre ecrit a la main."
    p.rattacher(g.amorcer(base), 10, 14)
    g.relever(base + "\x0b")
    f = g.relever(base + "\x0bDouze mots tapes tranquillement apres une longue pause, sans hate.")
    # Le plafond doit proteger du collage sans condamner la frappe honnete :
    # personne ne tape soixante mots dans un seul elan.
    d = g.debit(f, 600000)
    v = [x["verdict"] for x in g.nourrir(p, f, 10, 14, d)]
    assert v == ["ecriture"], (v, d)
    return f"douze mots apres dix minutes : debit {d:.0f}, ecriture"


# ==========================================================================
def main(filtre=None):
    print("=" * LARGEUR)
    print("ESSAIS — paysage")
    print("=" * LARGEUR)
    rates, passes, section = [], 0, None
    for nom, fn in ESSAIS:
        if filtre and filtre.lower() not in nom.lower():
            continue
        tete = nom.split(" / ")[0]
        if tete != section:
            section = tete
            print(f"\n{tete}")
        libelle = nom.split(" / ", 1)[-1]
        try:
            detail = fn() or ""
            passes += 1
            print(f"  ok    {libelle}")
            if detail:
                print(f"          {detail}")
        except AssertionError as e:
            rates.append((nom, str(e)))
            print(f"  ECHEC {libelle}")
            print(f"          {e}")
        except Exception as e:            # une erreur est un echec, pas un crash
            rates.append((nom, f"{type(e).__name__}: {e}"))
            print(f"  ERREUR {libelle}")
            print(f"          {type(e).__name__}: {e}")

    print()
    print("=" * LARGEUR)
    print(f"{passes} passes, {len(rates)} en echec")
    for nom, msg in rates:
        print(f"  - {nom}\n      {msg}")
    print("=" * LARGEUR)
    return 1 if rates else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
