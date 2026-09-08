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
