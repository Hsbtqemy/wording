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


@essai("traits / MATTR tient dans le budget de 100 ms sur une these")
def _():
    from traits import mattr
    rng = random.Random(1)
    mots = [f"mot{rng.randrange(900)}" for _ in range(146000)]
    essais_ms = []
    for _ in range(3):
        t0 = time.perf_counter()
        mattr(mots)
        essais_ms.append((time.perf_counter() - t0) * 1000)
    ms = min(essais_ms)          # le meilleur des trois : on mesure le code,
                                 # pas la charge de la machine
    assert ms < 100, f"{ms:.0f} ms"
    return f"{ms:.0f} ms pour 146 000 mots"


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
    CONN = "que qui dont parce puisque quoique alors tandis lorsque afin "            "malgre cependant toutefois neanmoins ainsi donc or car mais "            "comme si quand".split()
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
    CONN = "que qui dont parce puisque quoique alors tandis lorsque afin "            "malgre cependant toutefois neanmoins ainsi donc or car mais "            "comme si quand".split()

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
    assert riche - pauvre > 0.15,         f"un texte tres subordonne ({riche:.2f}) ne se distingue pas d'un texte"         f" qui ne l'est pas ({pauvre:.2f})"
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
    import composition
    src = open(composition.__file__, encoding="utf-8").read()
    # Un seul endroit construit le SVG : rendre().
    assert src.count("<svg xmlns=") <= 2, \
        "plus d'un chemin de rendu : les deux vues peuvent diverger"
    return "un seul chemin de rendu"


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
