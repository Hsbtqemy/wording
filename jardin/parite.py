"""
Parite Python / JavaScript.

Le Python est la specification, le JavaScript est le livrable. Tant que les
deux existent, il faut une facon de savoir qu'ils disent la meme chose — sinon
le banc d'essai valide un programme que personne n'installe.

Ce fichier fabrique un cahier de cas AVEC LES REPONSES DU PYTHON, puis lance
node dessus. Le JavaScript rejoue exactement les memes appels et compare.

    python parite.py            fabrique, lance node, rend un code de sortie
    python parite.py --cas      fabrique seulement (addin/parite/cas.json)

Le corpus, lui, reste du Python : le cahier porte le TEXTE que corpus.py a
fabrique, pas la graine qui l'a fabrique. Rejouer la graine cote JavaScript ne
verifierait que le generateur, et le premier ecart viendrait de la — c'est-a-
dire de l'endroit ou l'on n'apprend rien sur le portage.

Le generateur, lui, EST porte (addin/src/alea.js), et c'est une autre question.
Dans corpus.py il fabrique des donnees d'essai, qu'on peut simplement ecrire
dans le cahier. Dans grammaire, composition et message il est DANS LE LIVRABLE :
l'add-in tire au sort au moment de dessiner, et la decision 8 demande meme
document, meme graine, meme figure. Sans un generateur identique, rien de ce qui
se dessine ne serait comparable.

Ce qui est compare :

  generateur      random, uniform, randrange au BIT pres ; expovariate a un
                  logarithme pres
  tables          les listes litterales des deux cotes — abreviations,
                  connecteurs, puces, styles, variantes typographiques
  arrondi         round(x, n) tel que Python le fait, demis exacts compris
  normalisation   la meme chaine normalisee. C'est la que se voient les ecarts
                  d'Unicode : \\w ASCII contre \\w Unicode, NFD, casse.
  decoupage       mots, phrases, paragraphes, titre-ou-pas
  traits          les neuf traits normalises, a 1e-9 pres
  scores          les quatre familles, et la revelation qui en sort
  journal         chaque verdict de absorber / retoucher, appel par appel
  plants          l'etat final de chaque plant
  etat            ce que le volet lira, et ce qu'il rangera
  relectures      ce qu'un etat illisible doit rendre : un paysage vide
  empreintes      le meme nombre d'empreintes DISTINCTES — les deux fonctions
                  de hachage different (voir empreinte() cote JS), seule leur
                  capacite a separer le document est comparable
"""

from __future__ import annotations

import json
import os
import random
import subprocess
import sys
from pathlib import Path

import composition
import corpus
import grammaire
import traits
import paysage as paysage_mod
from paysage import Paysage, empreinte, normaliser

RACINE = Path(__file__).resolve().parent.parent
CAS = RACINE / "addin" / "parite" / "cas.json"
SCRIPT = RACINE / "addin" / "parite" / "parite.js"

MOTS_ECHANTILLON = 30000


# --------------------------------------------------------------------------
# Cas de decoupage et de traits
# --------------------------------------------------------------------------
def cas_tokenisation(rng) -> list[dict]:
    """Des paragraphes de chaque profil, plus les cas limites du decoupage."""
    textes: list[str] = []
    for famille in corpus.PROFILS:
        for _ in range(30):
            textes.append(corpus.paragraphe(rng, famille)[0])

    # Les cas ou les deux langages ont de bonnes raisons de diverger. Chacun
    # vise une ligne precise du portage ; s'ils passent, le reste suit.
    textes += [
        "Elephant a l'ecole.",                    # apostrophe droite
        "L’elephant à l’école.",  # apostrophe courbe + accents
        "ÉLÉPHANT À L'ÉCOLE",     # casse + accents a plier
        "Fin de texte sans espace.",              # $ colle a la ponctuation
        "Fin de texte avec saut.\n",              # $ devant un saut de ligne
        "Deux sauts.\n\n",
        "Cf. la note. Puis la suite.",            # abreviation protegee
        "M. Dupont est parti. Il revient.",
        # Numerotation : assez longues pour que SEULE la regle de
        # numerotation puisse les declarer structurelles. Courtes, la regle du
        # titre les rattraperait et le cas ne testerait plus rien.
        "1. Un element de liste numerote qui depasse largement les soixante"
        " caracteres et les neuf mots",
        "١. Un element numerote en chiffres arabes qui depasse largement"
        " les soixante caracteres et les neuf mots",
        "- Une puce",
        "— Une replique de dialogue, pas une puce",
        "« bruit » n'est pas un dialogue",       # un mot entre guillemets
        "« il fait froid ce matin » dit-elle",   # un enonce, lui
        "Ponctuation rare ; deux points : parentheses (ici) tirets — et suite…",
        "    espaces insecables partout    ",
        "smärt en NFD",                     # deja decompose
        # Des lettres que NFD ne decompose pas, aux deux bords : c'est le seul
        # endroit ou se voit la difference entre le \\W de Python (Unicode) et
        # celui de JavaScript (ASCII). Partout ailleurs les accents sont deja
        # tombes quand on arrive au rognage des bords, et la panne se cache.
        "œuvre de Ludwig van Beethoven, opus 111",
        "une fin en Ω",
        # Le meme mot ecrit des deux facons dans le meme texte. Ca arrive
        # tout le temps quand on tape vite, et c'est la seule chose que
        # deplier les accents change dans MATTR : sans le pliage, « these »
        # et « thèse » comptent pour deux formes et le vocabulaire parait
        # plus riche qu'il n'est.
        "La these avance. La thèse recule. Une cle tourne dans la clé."
        " Un echo repond a l'écho. La methode et la méthode."
        " Le resume, puis le résumé. Une reference, une référence.",
        "",
        "   ",
        "###",
        "Titre court",
        "Une ligne de plus de soixante caracteres qui ne doit surtout pas passer"
        " pour un titre malgre l'absence de point",
        # Exactement 59 points de code, dont un hors du plan de base : 60
        # unites UTF-16. len() compte des points de code en Python, .length
        # des unites en JavaScript — la ligne est un titre d'un cote et pas
        # de l'autre si le portage prend .length pour len().
        "\U0001f331 germe" + "e" * 52,
    ]

    sortie = []
    for t in textes:
        sortie.append({
            "texte": t,
            "normalise": normaliser(t),
            "mots": len(traits.en_mots(t)),
            "phrases": len(traits.en_phrases(t)),
            "paragraphes": len(traits.en_paragraphes(t)),
            "structurel": traits.est_structurel(t),
            # MATTR a part : borne(mattr, 0.55, 0.80) ecrete, et un texte
            # court passe sous la borne basse. Le comparer a travers
            # diversite seulement, c'est comparer deux zeros.
            "mattr": traits.mattr(traits.en_mots(t)),
        })
    return sortie


def cas_traits(rng) -> list[dict]:
    """Un texte par profil et par taille : la ou MATTR change de branche."""
    sortie = []
    for famille in corpus.PROFILS:
        for cible in (120, 250, 900, 5000, 20000):
            blocs, mots = [], 0
            while mots < cible:
                t, _ = corpus.paragraphe(rng, famille)
                blocs.append(t)
                mots += len(t.split())
            texte = "\n\n".join(blocs)
            r = traits.revele(traits.extraire(texte))
            sortie.append({
                "nom": f"{famille}-{cible}",
                "texte": texte,
                "traits": {n: getattr(r.traits, n) for n in (
                    "longueur", "rythme", "subordination", "regularite",
                    "structure", "dialogue", "interrogation", "diversite",
                    "ponctuation_rare", "reecriture")},
                "comptes": {"mots": r.traits.mots, "phrases": r.traits.phrases,
                            "paragraphes": r.traits.paragraphes},
                "mattr": traits.mattr(traits.en_mots(texte)),
                "scores": r.scores,
                "revelation": {"stade": r.stade, "famille": r.famille,
                               "provisoire": r.provisoire, "par_refus": r.par_refus,
                               "marge": r.marge, "secondaire": r.secondaire},
            })

    # Les quatre echantillons ecrits a la main : du vrai francais accentue.
    for f in sorted((Path(__file__).parent / "echantillons").glob("*.txt")):
        texte = f.read_text(encoding="utf-8")
        r = traits.revele(traits.extraire(texte))
        sortie.append({
            "nom": f.stem,
            "texte": texte,
            "traits": {n: getattr(r.traits, n) for n in (
                "longueur", "rythme", "subordination", "regularite",
                "structure", "dialogue", "interrogation", "diversite",
                "ponctuation_rare", "reecriture")},
            "comptes": {"mots": r.traits.mots, "phrases": r.traits.phrases,
                        "paragraphes": r.traits.paragraphes},
            "mattr": traits.mattr(traits.en_mots(texte)),
            "scores": r.scores,
            "revelation": {"stade": r.stade, "famille": r.famille,
                           "provisoire": r.provisoire, "par_refus": r.par_refus,
                           "marge": r.marge, "secondaire": r.secondaire},
        })
    return sortie


def cas_arrondis() -> list:
    """
    round(x, n) tel que Python le fait, sur des valeurs qui separent les
    methodes.

    Le portage naif — Math.round(x * 10**n) / 10**n — donne la meme reponse que
    Python sur 346 385 sommes de scores tirees au hasard sur 346 389. Les
    quatre restantes sont minuscules : 0,00035, 0,00095... C'est exactement la
    taille que prend la MARGE quand deux familles se tiennent, c'est-a-dire le
    cas ou la decision 5 refuse de classer. Une valeur qu'on ne voit jamais
    dans un score, on la voit dans un ecart entre deux scores.

    Donc on ne peut pas attendre que le cahier de traits tombe dessus par
    hasard : il faut viser.
    """
    valeurs = [0.00035, 0.00095, 0.00115, 0.00165, 0.0, 1.0, 0.5, 0.125,
               0.06, 0.059999, 0.06000001, 0.12345678, 0.99995, 0.00005,
               0.1 + 0.2, 1 / 3, 2 / 3, 0.845, 2.675 / 10]
    for i in range(1, 64):
        valeurs.append(i / 64)
    return [[v, round(v, 4), round(v, 3)] for v in valeurs]


# --------------------------------------------------------------------------
# Le journal : une redaction entiere, appel par appel
# --------------------------------------------------------------------------
def _retouche(texte: str, tour: int) -> str:
    """Une retouche deterministe, qui allonge sans changer de famille."""
    return texte.rstrip(".!?") + f", precisement, au tour {tour}."


def cas_journal() -> tuple[list, list, int]:
    """
    Rejoue une redaction et note le verdict de chaque appel.

    Le corpus n'emet que des paragraphes neufs. On y injecte a intervalle fixe
    les quatre gestes que le corpus ne produit jamais et qui sont precisement
    ceux que la decision 2 arbitre : deux frappes dans la meme visite, une
    sortie de curseur, une reprise, une reprise en cours, une greffe, sa
    conversion, et pour finir une fusion — cinquante paragraphes deja connus
    qui reviennent, et qui ne doivent rien faire pousser.
    """
    p = Paysage(identifiant="parite", cle_dossier="parite")
    journal: list = []
    ecrits: list[str] = []
    tour = 0

    def noter(ancien, nouveau, jour, heure, greffe=False):
        verdict = p.retoucher(ancien, nouveau, jour, heure, greffe)
        journal.append(["retoucher", ancien, nouveau, jour, heure, greffe, verdict])
        return verdict

    for texte, style, jour, heure in corpus.these(mots_cibles=MOTS_ECHANTILLON):
        tour += 1
        greffe = (tour % 120 == 0)
        mpi = 40 if greffe else 0
        verdict = p.absorber(texte, style, mpi, jour, heure)
        journal.append(["absorber", texte, style, mpi, jour, heure, verdict])
        if verdict in ("ecriture", "greffe"):
            ecrits.append(texte)

        if greffe:
            # 4. une greffe retouchee se convertit en ecriture
            neuf = _retouche(texte, tour)
            noter(texte, neuf, jour, heure, True)
            ecrits[-1] = neuf

        if tour % 40 == 0 and len(ecrits) > 5:
            # Le paragraphe qu'on vient d'ecrire, qu'on continue de taper :
            # meme visite, donc FRAPPE, et les mots comptent.
            #
            # Il faut viser ecrits[-1], le paragraphe actif. La premiere
            # version de ce cahier retouchait ecrits[-2] : le curseur n'y
            # etait plus, chaque retouche repassait par la reprise, et sur
            # 616 appels le mot « frappe » n'apparaissait pas une fois. Le
            # cahier avait donc l'air complet en ne visitant jamais le seul
            # chemin pour lequel le curseur de la decision 2 a ete ecrit.
            a = ecrits[-1]
            b = _retouche(a, tour)
            noter(a, b, jour, heure)                      # frappe
            c = _retouche(b, tour + 1)
            noter(b, c, jour, heure)                      # frappe
            # Le curseur sort : ce qui suit est un retour.
            p.quitter()
            journal.append(["quitter"])
            d = _retouche(c, tour + 2)
            noter(c, d, jour, heure)                      # reprise
            e = _retouche(d, tour + 3)
            noter(d, e, jour, heure)                      # reprise en cours
            ecrits[-1] = e

        if tour % 70 == 0 and len(ecrits) > 5:
            # Un paragraphe plus ancien : visite neuve, donc une reprise et
            # une seule, sans avoir eu besoin de quitter quoi que ce soit.
            vieux = ecrits[-4]
            neuf = _retouche(vieux, tour)
            noter(vieux, neuf, jour, heure)               # reprise
            ecrits[-4] = neuf

        if tour % 200 == 0:
            p.quitter()
            journal.append(["quitter"])

    # ----------------------------------------------------------------------
    # Ce que trente mille mots de corpus ne produisent jamais, et qu'il faut
    # donc ecrire a la main. Mesure faite avant de les ajouter : sur les douze
    # plants, zero de nuit, zero au stade germe, et les verdicts « ignoree » et
    # « inchangee » n'apparaissaient pas une fois. Le bloc germe de etat() —
    # taille et inflexion, ce qui dessine une plante qui n'a pas encore de
    # famille — n'etait donc compare que sous la forme null.
    # ----------------------------------------------------------------------
    def chapitre(titre, mots_cibles, famille, jour, heure, graine):
        """
        Un chapitre a la demande, sous un Titre 1.

        La graine est passee explicitement. La premiere version la tirait de
        hash(titre) : Python randomise le hachage des chaines a chaque
        processus, donc le cahier changeait d'un lancement a l'autre — 5 924
        comparaisons puis 5 920. Un cahier qui bouge tout seul ne sert a rien :
        un ecart ne serait pas reproductible, et le fichier changerait a chaque
        regeneration sans que personne n'ait rien touche.
        """
        journal.append(["absorber", titre, "Titre 1", 0, jour, heure,
                        p.absorber(titre, "Titre 1", 0, jour, heure)])
        rng = random.Random(graine)
        ecrits_ici, mots = [], 0
        while mots < mots_cibles:
            texte, _ = corpus.paragraphe(rng, famille)
            journal.append(["absorber", texte, "Normal", 0, jour, heure,
                            p.absorber(texte, "Normal", 0, jour, heure)])
            ecrits_ici.append(texte)
            mots += len(texte.split())
        p.quitter()
        journal.append(["quitter"])
        return ecrits_ici

    # Un chapitre ecrit entierement entre 2h et 5h : le seul moyen d'avoir un
    # plant dont nuit vaut vrai (decision 9 : la palette de nuit tient aux
    # SEGMENTS ecrits la nuit, pas a une session isolee).
    chapitre("Chapitre de nuit", 1000, "vegetal", jour=200, heure=3, graine=901)

    # Une citation : le filtre gratuit de la decision 4, que le corpus n'emet
    # jamais puisqu'il ne connait que Normal, Titre 1, Titre 2 et liste.
    cit = "Une citation rapportee, qui ne compte ni en mots ni en croissance."
    journal.append(["absorber", cit, "Citation", 0, 210, 14,
                    p.absorber(cit, "Citation", 0, 210, 14)])

    # Deux chemins que seul le vrai Word emprunte, et que le corpus ne produit
    # jamais : le paragraphe VIDE cree par un retour a la ligne, et la
    # NAISSANCE — un paragraphe qu'on a vu naitre sous le curseur, et qui
    # echappe donc a la reconnaissance du registre. Les deux ont ete trouves
    # en eprouvant le pont contre un Word simule, pas ici.
    for vide in ("", "   ", chr(10)):
        journal.append(["absorber", vide, "Normal", 0, 210, 14,
                        p.absorber(vide, "Normal", 0, 210, 14)])
    deja = ecrits[3]
    journal.append(["absorber-naissance", deja, "Normal", 0, 210, 14,
                    p.absorber(deja, "Normal", 0, 210, 14, True)])

    # Une retouche qui ne change rien : Word reecrit un paragraphe a l'identique
    # des qu'on entre et sort d'une cellule, et ce cas doit rester gratuit.
    inchange = ecrits[-1]
    noter(inchange, inchange, 210, 14)                   # inchangee
    # Et une qui ne change que la typographie de l'apostrophe, ce que Word fait
    # tout seul : normaliser() doit la voir comme la meme.
    if "'" in inchange:
        journal.append(["retoucher", inchange, inchange.replace("'", "\u2019"),
                        210, 14, False,
                        p.retoucher(inchange, inchange.replace("'", "\u2019"), 210, 14)])

    # Un chapitre qui DEBORDE, c'est-a-dire qui depasse a lui seul les 5 000
    # mots d'un plant. Il ouvre le second plant par debordement et non par un
    # Titre 1, ce qui est le seul moyen d'obtenir DEUX PLANTS SOUS LE MEME
    # TITRE — donc une parcelle de plus d'un plant, donc le serrage du massif.
    #
    # Ce chemin etait traverse par accident tant que le plant se fermait aussi
    # a 52 paragraphes : les chapitres de 3 800 mots du corpus franchissaient
    # ce plafond-la. Le jour ou l'extension est passee aux seuls mots, plus
    # aucun chapitre ne remplissait un plant, l'heritage de parcelle a cesse
    # d'etre exerce, et la mutation qui defait le massif a echappe au cahier
    # sans que rien ne le signale. On l'ecrit donc a la main, comme le reste de
    # ce bloc.
    #
    # Depuis que le plant vaut 2 500 mots, les chapitres du corpus debordent a
    # nouveau tout seuls et ce chapitre-ci n'est plus le seul massif du cahier.
    # IL RESTE QUAND MEME, et c'est la lecon de la panne : une couverture qui
    # tient par accident tombe silencieusement au prochain changement de
    # constante. Celui-ci deborde quelle que soit la valeur du plant.
    chapitre("Chapitre fleuve", 6400, "vegetal", jour=214, heure=15,
             graine=904)

    # Deux plants jeunes, laisses jeunes. L'ordre compte : un Titre 1 sur un
    # plant de moins de 200 mots le RENOMME au lieu d'en ouvrir un neuf, donc le
    # chapitre lisible doit passer avant le chapitre germe.
    chapitre("Chapitre a peine lisible", 420, "architecture", jour=220,
             heure=11, graine=902)
    derniers = chapitre("Chapitre germe", 110, "creature", jour=222,
                        heure=11, graine=903)

    # Une greffe qu'on ne convertit pas : un plant doit finir avec des greffes
    # en attente, sinon le champ n'est jamais compare qu'a zero.
    colle = "Un bloc rapporte d'ailleurs, colle d'un seul geste et laisse tel quel."
    journal.append(["absorber", colle, "Normal", 40, 222, 11,
                    p.absorber(colle, "Normal", 40, 222, 11)])

    # La fusion : le document maitre reprend cinquante paragraphes existants.
    for texte in ecrits[:50]:
        verdict = p.absorber(texte, "Normal", 0, 300, 14)
        journal.append(["absorber", texte, "Normal", 0, 300, 14, verdict])

    # Un cahier qui n'emprunte pas tous les chemins a l'air complet sans
    # l'etre. On refuse de le fabriquer plutot que de le decouvrir plus tard.
    vus = {e[-1] for e in journal if e[0] != "quitter"}
    attendus = {"ecriture", "connue", "greffe", "conversion", "ignoree",
                "inchangee", "vide", "frappe", "reprise", "reprise en cours"}
    manquants = attendus - vus
    if manquants:
        raise AssertionError(f"le journal n'emprunte pas : {sorted(manquants)}")

    # Et il doit laisser derriere lui au moins un plant de chaque sorte.
    stades = {s.stade() for s in p.segments}
    if not {"germe", "indices", "croissance"} <= stades:
        raise AssertionError(f"stades absents : {sorted({'germe','indices','croissance'} - stades)}")
    if not any(s.nuit for s in p.segments):
        raise AssertionError("aucun plant de nuit")
    if not any(s.greffes for s in p.segments):
        raise AssertionError("aucune greffe en attente")
    assert derniers

    plants = []
    for s in p.segments:
        plants.append({
            "rang": s.rang, "titre": s.titre, "mots": s.mots,
            "nouveaux": s.nouveaux, "reprises": s.reprises, "greffes": s.greffes,
            "famille": s.famille, "candidate": s.candidate,
            "confirmations": s.confirmations,
            "mots_derniere_lecture": s.mots_derniere_lecture,
            "extension": s.extension, "maturite": s.maturite,
            "mots_de_nuit": s.mots_de_nuit, "nuit": s.nuit,
            "stade": s.stade(), "dates": [list(d) for d in s.dates()],
            "traits": dict(s.traits_courants),
            "scores": dict(s.scores_courants),
            "influences": s.influences(),
        })
    return journal, plants, p


def cas_composition(plants) -> dict:
    """
    Le paysage entier, et les deux vues.

    On rejoue les plants REELS du journal, plus des sous-ensembles qui exercent
    les cas ou composer() a le choix : un seul plant, aucun plant vivant, deux
    plants du meme chapitre, deux chapitres differents (la respiration de
    parcelle), et le paysage complet.

    Le gabarit est compare a part parce que c'est lui qui porte la decision : un
    plant sans famille prend la taille de LA PLUS GRANDE des quatre familles,
    pour que l'echelle ne puisse que monter quand le verrou tombe.
    """
    sous = {
        "vide": [],
        "un": plants[:1],
        "germe seul": [p for p in plants if p["stade"] == "germe"][:1],
        "tout": plants,
    }

    # ⚠️ Cette vue s'appelait « deux du meme chapitre » et prenait plants[:2],
    # qui sont deux chapitres DIFFERENTS. Elle portait donc le nom du cas sans
    # le cas : composer() en faisait deux parcelles d'un plant chacune, le
    # serrage ne valait jamais 0,46, et le supprimer ne changeait rien a aucune
    # comparaison. On les CHERCHE, et on refuse de fabriquer le cahier s'il n'y
    # en a pas — un cahier muet coute un cycle a diagnostiquer, une assertion
    # coute une seconde.
    #
    # La regle est recopiee de composer() : les parcelles sont des SUITES de
    # plants consecutifs de meme titre, et un plant sans famille n'est pas pose
    # du tout.
    suites: list = []
    for q in plants:
        if not q["famille"]:
            continue
        cle = q["titre"] or ""
        if not suites or suites[-1][0] != cle:
            suites.append((cle, []))
        suites[-1][1].append(q)
    massif = next((g for _c, g in suites if len(g) > 1), None)
    if massif is None:
        raise AssertionError(
            "aucune parcelle ne porte deux plants : le serrage du massif"
            " n'est traverse par aucune vue")
    sous["deux du meme chapitre"] = massif[:2]
    # Deux plants de titres differents : la respiration de parcelle.
    titres = {}
    for q in plants:
        titres.setdefault(q["titre"], q)
    sous["deux chapitres"] = list(titres.values())[:2]

    vues = {}
    for nom, sp in sous.items():
        poses, largeur = composition.composer(sp, 560, 1)
        vues[nom] = {
            "plants": [p["rang"] for p in sp],
            "largeur": largeur,
            # Les poses sans la Toile : profondeur, x, y, echelle. C'est la
            # composition elle-meme, avant tout rendu.
            "poses": [[d, cx, y, k] for d, cx, y, k, _t in poses],
            "svg": composition.svg(sp, 560, 1),
            "vue_de_travail": composition.vue_de_travail(sp, 1),
            "apercu": composition.svg_apercu(sp, 520, 1),
        }

    gabarits = []
    for p in plants:
        g = 1 + p["rang"] * 977
        gl, gh = composition.gabarit(p, g)
        gabarits.append({"rang": p["rang"], "graine": g,
                         "largeur": gl, "hauteur": gh})
    return {"vues": vues, "gabarits": gabarits}


def cas_couleur() -> dict:
    """
    La palette, exhaustivement.

    365 jours x 5 tons x jour/nuit, soit 3 650 couleurs : c'est assez petit pour
    ne pas echantillonner. Les frontieres de saison et les fondus de douze jours
    des deux cotes sont exactement le genre d'arithmetique ou un modulo negatif
    ou un int() qui arrondit au lieu de tronquer passe inapercu onze mois sur
    douze.
    """
    tons = []
    for jour in range(365):
        for ton in range(5):
            tons.append([jour, ton, False, grammaire.palette(jour, ton, False)])
            tons.append([jour, ton, True, grammaire.palette(jour, ton, True)])
    # Hors bornes des deux cotes : le modulo de Python n'est jamais negatif,
    # celui de JavaScript si.
    limites = []
    for jour in (-400, -366, -365, -1, 0, 364, 365, 366, 800):
        for ton in (-7, -1, 0, 4, 5, 12):
            limites.append([jour, ton, grammaire.palette(jour, ton, False)])
    return {"tons": tons, "limites": limites}


def cas_teinte() -> list:
    """Teinte : le nombre de tons, et le tirage d'une date au poids des mots."""
    sortie = []
    cas = [
        ([[200, 1]], False, 0.0),
        ([[200, 1]], False, 1.0),
        ([[200, 1]], True, 0.5),
        ([[20, 300], [110, 900], [300, 40]], False, 0.7),
        ([[355, 5], [356, 5], [80, 5], [79, 5]], False, 0.25),
        ([[1, 1], [2, 1], [3, 1]], True, 0.99),
        ([], False, 0.5),
    ]
    for dates, nuit, div in cas:
        t = grammaire.Teinte(dates or None, nuit, div)
        rng = random.Random(4242)
        tirages = [[t.jour(rng), t.ton(rng)] for _ in range(40)]
        sortie.append({"dates": dates, "nuit": nuit, "diversite": div,
                       "n_tons": t.n_tons, "total": t._total,
                       "tirages": tirages})
    return sortie


def cas_graines() -> list:
    """graine_du_document : elle determine la FIGURE, elle ne peut pas diverger."""
    noms = ["", "these", "these.docx", "Chapitres", "Memoire — chapitre 3",
            "c:/Dev/Wording/these.docx", "œuvre", "\U0001f331",
            "un nom tres long " * 20]
    return [[n, grammaire.graine_du_document(n)] for n in noms]


def cas_figures() -> list:
    """
    Les quatre familles et le germe, segment par segment.

    On compare la LISTE DE SEGMENTS avant le SVG : un ecart de coordonnee se
    lit alors sur le segment fautif, au lieu d'apparaitre comme deux chaines de
    trente mille caracteres qui different quelque part. Le SVG est compare
    ensuite, parce que c'est lui le livrable.

    Les vecteurs de traits vont jusqu'aux extremes (tout a zero, tout a un) :
    au milieu, une correspondance trait -> geometrie qu'on aurait inversee
    donnerait presque la meme figure.
    """
    vecteurs = {
        "neutre": None,
        "zero": {k: 0.0 for k in grammaire.TRAITS_NEUTRES},
        "un": {k: 1.0 for k in grammaire.TRAITS_NEUTRES},
        "prose": {"longueur": 0.82, "rythme": 0.21, "subordination": 0.77,
                  "regularite": 0.34, "structure": 0.05, "dialogue": 0.02,
                  "interrogation": 0.11, "diversite": 0.63,
                  "ponctuation_rare": 0.29},
        "rapport": {"longueur": 0.19, "rythme": 0.28, "subordination": 0.12,
                    "regularite": 0.88, "structure": 0.91, "dialogue": 0.0,
                    "interrogation": 0.03, "diversite": 0.31,
                    "ponctuation_rare": 0.08},
    }
    teintes = {
        "jour": grammaire.Teinte.du_jour(110, 14, 0.7),
        "nuit": grammaire.Teinte.du_jour(200, 3, 0.7),
        "etale": grammaire.Teinte([[20, 300], [110, 900], [300, 40]], False, 0.9),
    }
    sortie = []
    for famille in grammaire.FAMILLES:
        for nom_v, tr in vecteurs.items():
            for e, m in ((0.0, 0.0), (0.15, 0.15), (0.55, 0.55), (1.0, 0.92)):
                for nom_t in ("jour", "nuit", "etale"):
                    graine = 500 + len(sortie) * 17
                    t = grammaire.dessiner(famille, e, m, graine,
                                           teintes[nom_t], tr)
                    sortie.append({
                        "quoi": "famille", "famille": famille, "vecteur": nom_v,
                        "teinte": nom_t, "extension": e, "maturite": m,
                        "graine": graine,
                        "segments": [list(s) for s in t.segments],
                        "noeuds": [list(n) for n in t.noeuds],
                        "bbox": list(t.bbox()),
                        # La boite voyage AVEC le cas. Elle etait ecrite en
                        # dur des deux cotes, et l'etoffage la voulait plus
                        # grande : le verificateur comparait alors deux
                        # cadrages differents et accusait le portage.
                        "boite": [0, 0, 200, 200],
                        "svg": t.svg(0, 0, 200, 200),
                        "pose": t.pose(100, 300, 0.75),
                    })

    # La creature avec un etoffage impose : le chemin que depuis_plant n'emprunte
    # pas, et celui que la planche des membres a servi a corriger.
    for cp in (0.10, 0.5, 1.0):
        t = grammaire.Toile()
        grammaire.creature(t, 0.7, 0.8, 777, teintes["jour"],
                           etoffage={"tete": 0.4, "corps": cp, "membres": 1.0})
        sortie.append({"quoi": "etoffage", "corps": cp,
                       "segments": [list(s) for s in t.segments],
                       "noeuds": [list(n) for n in t.noeuds],
                       "bbox": list(t.bbox()),
                       "boite": [0, 0, 250, 240],
                       "svg": t.svg(0, 0, 250, 240),
                       "pose": t.pose(100, 300, 0.75)})

    # Le germe : les cinq cas de la decision 6, aux deux stades.
    for pressentie in (None, "vegetal", "architecture", "creature", "abstrait"):
        for taille, inflexion in ((0.05, 0.0), (0.25, 0.0), (0.5, 0.4),
                                  (0.8, 0.8), (1.0, 1.0)):
            t = grammaire.Toile()
            grammaire.germe(t, taille, inflexion, pressentie, 313,
                            teintes["jour"])
            sortie.append({"quoi": "germe", "pressentie": pressentie,
                           "taille": taille, "inflexion": inflexion,
                           "segments": [list(s) for s in t.segments],
                           "noeuds": [list(n) for n in t.noeuds],
                           "bbox": list(t.bbox()),
                           "boite": [0, 0, 200, 200],
                           "svg": t.svg(0, 0, 200, 200),
                           "pose": t.pose(100, 300, 0.75)})
    return sortie


def cas_depuis_plant(plants) -> list:
    """
    Le seul point de contact entre l'etat et le rendu.

    On rejoue les plants REELS du journal — dont celui de nuit, celui au stade
    germe et celui au stade indices, qu'on a du fabriquer expres.
    """
    sortie = []
    for p in plants:
        graine = 900 + p["rang"] * 977
        t = grammaire.depuis_plant(p, graine)
        sortie.append({"rang": p["rang"], "graine": graine,
                       "segments": [list(s) for s in t.segments],
                       "noeuds": [list(n) for n in t.noeuds],
                       "svg": t.svg(0, 0, 200, 200)})
    return sortie


def cas_alea() -> dict:
    """
    Le generateur de Python, tirage par tirage.

    La decision 8 demande : meme document, meme graine, meme figure. La
    grammaire, la composition et le message tirent trente-six nombres au sort ;
    si les deux langages ne tirent pas la MEME suite, plus rien de ce qui se
    dessine n'est comparable, et les quinze cents lignes de geometrie qui
    restent a porter deviennent invisibles au verificateur.

    Les graines vont jusqu'aux bornes ou le semis change de forme : 0 (cle
    [0]), 2**32 et au-dela (cle a deux mots), 2**53 - 1 (le dernier entier
    sur). C'est la que la simplification habituelle — appeler init_genrand avec
    la graine au lieu de init_by_array — cesse de donner la meme suite.
    """
    graines = [0, 1, 2, 3, 7, 11, 42, 977, 1234, 65535, 65536,
               2 ** 31 - 1, 2 ** 31, 2 ** 32 - 1, 2 ** 32, 2 ** 32 + 1,
               123456789012, 2 ** 53 - 1]
    cas = []
    for g in graines:
        r = random.Random(g)
        suite = []
        for i in range(60):
            t = i % 4
            if t == 0:
                suite.append(["random", [], r.random()])
            elif t == 1:
                suite.append(["uniform", [-0.16, 0.16], r.uniform(-0.16, 0.16)])
            elif t == 2:
                n = 1 + (i * 7) % 97
                suite.append(["randrange", [n], r.randrange(n)])
            else:
                suite.append(["expovariate", [1.4], r.expovariate(1.4)])
        cas.append({"graine": g, "suite": suite})

    # grammaire.py trie les tours d'une ville par cle aleatoire. Un tri stable
    # des deux cotes ne suffit pas : il faut aussi les MEMES cles.
    tris = []
    for g in (3, 19, 512):
        r = random.Random(g)
        tris.append({"graine": g, "n": 9,
                     "ordre": sorted(range(9), key=lambda k: r.random())})
    return {"cas": cas, "tris": tris}


def cas_tables() -> dict:
    """
    Les tables litterales des deux cotes.

    C'est la derive la plus probable d'un projet a deux langages, et la plus
    silencieuse : on ajoute une abreviation, un connecteur, un style de titre
    d'un seul cote. Rien ne casse. Le texte se lit juste un peu differemment.
    Sur les dix-neuf abreviations, le cahier n'en visitait que deux ; les
    dix-sept autres pouvaient etre fausses depuis toujours.
    """
    return {
        "traits": {
            "ABREVIATIONS": sorted(traits.ABREVIATIONS),
            "PUCES": list(traits.PUCES),
            "CONNECTEURS_SUBORDINATION": sorted(traits.CONNECTEURS_SUBORDINATION),
            "MOTS_MINIMUM_ENONCE": traits.MOTS_MINIMUM_ENONCE,
            "PALIER_INDICES": traits.PALIER_INDICES,
            "PALIER_DIVERGENCE": traits.PALIER_DIVERGENCE,
            "MARGE_DOMINANCE": traits.MARGE_DOMINANCE,
            "FAMILLES": list(traits.POIDS),
            "POIDS": {k: [list(t) for t in v] for k, v in traits.POIDS.items()},
            "NOMS": dict(traits.NOMS),
        },
        "grammaire": {
            "PALETTES": {k: list(v) for k, v in grammaire.PALETTES.items()},
            "SAISONS": [list(s) for s in grammaire.SAISONS],
            "FONDU": grammaire.FONDU,
            "HEURE_NUIT": list(grammaire.HEURE_NUIT),
            "TRAIT": grammaire.TRAIT,
            "FOND": grammaire.FOND,
            "EPAISSEUR": grammaire.EPAISSEUR,
            "SEGMENT": grammaire.SEGMENT,
            "BUDGET_FEUILLAGE": grammaire.BUDGET_FEUILLAGE,
            "TRAITS_NEUTRES": dict(grammaire.TRAITS_NEUTRES),
        },
        "composition": {
            "HORIZON": composition.HORIZON,
            "ECHELLE_FOND": composition.ECHELLE_FOND,
            "ECHELLE_AVANT": composition.ECHELLE_AVANT,
            "OPACITE_FOND": composition.OPACITE_FOND,
            "ECART": composition.ECART,
            "ECART_PARCELLE": composition.ECART_PARCELLE,
        },
        "paysage": {
            "STYLES_TITRE": sorted(paysage_mod.STYLES_TITRE),
            "STYLES_IGNORES": sorted(paysage_mod.STYLES_IGNORES),
            "VARIANTES": {chr(k): v for k, v in paysage_mod._VARIANTES.items()},
            "MOTS_PAR_PLANT": paysage_mod.MOTS_PAR_PLANT,
            "MOTS_MINIMUM_VERROU": paysage_mod.MOTS_MINIMUM_VERROU,
            "LECTURES_CONCORDANTES": paysage_mod.LECTURES_CONCORDANTES,
            "MOTS_ENTRE_LECTURES": paysage_mod.MOTS_ENTRE_LECTURES,
            "SEUIL_COLLAGE": paysage_mod.SEUIL_COLLAGE,
            "HEURE_NUIT": list(paysage_mod.HEURE_NUIT),
            "MOTS_LISIBLES": paysage_mod.MOTS_LISIBLES,
            "SATURATION_REPRISES": paysage_mod.SATURATION_REPRISES,
            "VERSION_ETAT": paysage_mod.VERSION_ETAT,
        },
    }


def cas_relectures() -> list:
    """
    Ce que depuis() doit refuser, et ce qu'il doit rendre a la place.

    Un paysage qui se relit mal doit repartir vide, jamais lever : l'add-in
    n'aurait nulle part ou rattraper l'erreur, et le volet resterait noir.
    """
    cas = ["", "   ", "pas du json", "{}", "[]", "null",
           '{"version": 1, "segments": []}',
           '{"version": 99, "identifiant": "x", "registre": [], "segments": []}']
    sortie = []
    for brut in cas:
        r = Paysage.depuis(brut)
        sortie.append({"brut": brut, "identifiant": r.identifiant,
                       "plants": len(r.segments), "empreintes": len(r.registre),
                       "version": r.version})
    return sortie


def cas_rattachement() -> dict:
    """
    Decision 11 : une these deja ecrite se rattache d'un bloc.

    C'est le premier geste que fera le vrai add-in, et le journal ne le prend
    jamais : lui commence sur un document vide. On y met aussi ce que
    rattacher() doit savoir ignorer — une citation, du vide, et un paragraphe
    deja vu.
    """
    p = Paysage(identifiant="rattache", cle_dossier="rattache")
    rng = random.Random(23)
    familles = list(corpus.PROFILS)
    entree: list = []
    for c in range(3):
        entree.append([f"Chapitre {c + 1}", "Titre 1"])
        for _ in range(70):
            texte, style = corpus.paragraphe(rng, familles[c])
            entree.append([texte, style])
    entree.append(["Une citation qui ne compte pas.", "Citation"])
    entree.append(["", "Normal"])
    entree.append(["   ", "Normal"])
    entree.append(list(entree[3]))          # deja connu : rien
    p.rattacher(entree, jour=40, heure=10)
    return {"entree": entree, "jour": 40, "heure": 10, "etat": p.etat()}


def cas_guet() -> dict:
    """
    Le guet, releve par releve, avec ses reponses.

    Le premier morceau du cablage Word que la parite puisse couvrir : le
    rapprochement de deux instantanes est de la logique pure sur des tableaux de
    chaines, donc il a un Python en face. pont.js ne l'a jamais eu.

    On rejoue une session d'ecriture, et on enregistre a chaque releve les faits
    rendus, LES IDENTIFIANTS, et le compte de paragraphes. Les identifiants
    comptent autant que les faits : c'est leur stabilite qui empeche une
    insertion de se lire comme une pluie de retouches.

    ⚠️ Le cahier REFUSE de se construire s'il ne traverse pas les quatre genres
    de faits. Un cahier qui a l'air complet et ne passe jamais par le mecanisme
    surveille a deja coute cher a ce projet — sur 616 appels, le verdict frappe
    n'apparaissait pas une fois.
    """
    from guet import Guet, SEPARATEUR_PARAGRAPHE, SEPARATEURS_LIGNE

    cr, vt = SEPARATEUR_PARAGRAPHE, SEPARATEURS_LIGNE[0]
    rng = random.Random(77)
    familles = list(corpus.PROFILS)
    phrases = [corpus.paragraphe(rng, familles[i % len(familles)])[0]
               for i in range(12)]

    def corps(paragraphes: list) -> str:
        """Des paragraphes, chacun fait de lignes : les deux niveaux de Word."""
        return cr.join(vt.join(lignes) for lignes in paragraphes)

    # ⚠️ DEUX LIGNES QUI SONT DES NOMS DE PROPRIETE HERITEE. En JavaScript,
    # un index construit sur un objet nu trouverait une entree pour
    # « __proto__ » ou « constructor » sans que personne ne l'y ait mise, et
    # apparierait des lignes qui n'existent pas. Python n'a pas ce piege, donc
    # le cahier doit le tendre lui-meme, sinon la parite ne peut pas le voir.
    depart = [["Chapitre premier"],
              [phrases[0], "__proto__", phrases[1], "constructor"],
              [phrases[2], "", "", phrases[9]]]
    etapes = []

    # 1. On tape au bout d'une ligne, par morceaux, comme on ecrit vraiment.
    a = [list(p) for p in depart]
    a[1][1] = phrases[1][:40]
    etapes.append([list(p) for p in a])
    a[1][1] = phrases[1][:80]
    etapes.append([list(p) for p in a])
    a[1][1] = phrases[1]
    etapes.append([list(p) for p in a])

    # 2. Entree : une ligne vide nait sous le curseur, puis se remplit.
    #    On vise par le BOUT et non par un rang absolu : les etapes qui
    #    suivaient des indices fixes ont cesse de viser juste le jour ou deux
    #    lignes ont ete ajoutees au depart, et le verdict « ecriture »
    #    n'apparaissait plus nulle part. Le controle en fin de cahier l'a dit.
    a[1].append("")
    etapes.append([list(p) for p in a])
    a[1][-1] = phrases[3][:30]
    etapes.append([list(p) for p in a])
    a[1][-1] = phrases[3]
    etapes.append([list(p) for p in a])

    # 2bis. ON COLLE DANS LA LIGNE QU'ON VIENT D'ECRIRE. Elle est active et en
    #       mode frappe : sans le controle de debit dans retoucher(), tous ces
    #       mots compteraient en extension. C'est le trou par lequel un vrai
    #       document est passe d'une tige a un arbre en trois collages.
    a[1][-1] = phrases[3] + " " + " ".join("mot%d" % i for i in range(120))
    etapes.append([list(p) for p in a])

    # 3. Une ligne inseree AU MILIEU : le cas qui tient l'invariant.
    a[1].insert(1, phrases[4])
    etapes.append([list(p) for p in a])

    # 4. Un deplacement : gratuit (point 3), donc aucun fait.
    a[1][1], a[1][2] = a[1][2], a[1][1]
    etapes.append([list(p) for p in a])

    # 5. Une suppression.
    del a[1][2]
    etapes.append([list(p) for p in a])

    # 6. Un collage de trois lignes d'un bloc.
    #    DANS LE PARAGRAPHE ORDINAIRE, pas dans le dernier : celui-la porte le
    #    style « Citation », et une citation ne compte JAMAIS (point 3). Colle
    #    la, le bloc rendait « ignoree » et le cahier ne traversait ni la
    #    greffe ni sa conversion — c'est le controle de fin qui l'a dit.
    a[1].extend([phrases[5], phrases[6], phrases[7]])
    etapes.append([list(p) for p in a])

    # 6bis. On modifie de part et d'autre des deux lignes vides, dans le meme
    #       releve. Le rognage ne peut plus les emporter, elles restent dans la
    #       fenetre, et l'ordre d'appariement des lignes egales devient visible :
    #       pop(0) et pop() ne rendent alors pas les memes identifiants.
    a[2][0] = phrases[2] + " Une precision ajoutee au bout."
    a[2][3] = phrases[9] + " Et une autre, a l'autre bout."
    etapes.append([list(p) for p in a])

    # 6ter. On retravaille une ligne du bloc colle. Elle etait une GREFFE, elle
    #       doit devenir de l'ecriture (point 4). Le pont ne savait pas le
    #       faire : il passait toujours etait_greffe=False, donc un chapitre
    #       colle puis retravaille restait une greffe pour toujours.
    a[1][-1] = phrases[7] + " Et une suite ecrite a la main, celle-la."
    etapes.append([list(p) for p in a])

    # 7. Un paragraphe NEUF : la table des styles s'allonge, et le compte de
    #    paragraphes doit le dire.
    a.append([phrases[8]])
    etapes.append([list(p) for p in a])

    # 7bis. Une ligne qui RACCOURCIT. Sans elle, la soustraction de mots reste
    #       toujours positive et retirer le max(0, ...) ne change rien : un
    #       debit negatif compenserait pourtant un collage arrive dans le meme
    #       releve, et un chapitre colle passerait pour de l'ecriture.
    a[1][-1] = phrases[7][:40]
    etapes.append([list(p) for p in a])

    # 7ter. Une ligne neuve dont le texte est DEJA DANS LE REGISTRE — c'est un
    #       etat intermediaire d'une autre ligne, tape plus tot. En francais une
    #       ligne sur deux commence par les memes mots, et sans le drapeau de
    #       naissance le registre la declarerait « connue » : le plant cesserait
    #       de pousser sans que rien ne le signale.
    a[1].append("")
    etapes.append([list(p) for p in a])
    a[1][-1] = phrases[3][:30]
    etapes.append([list(p) for p in a])

    # 8. Le calme, assez longtemps pour que la visite se ferme.
    for _ in range(5):
        etapes.append([list(p) for p in a])

    # 8bis. Une retouche APRES le silence, SUR LA LIGNE QUI ETAIT ACTIVE.
    #
    #       C'est le seul endroit ou quitter() se voit. _actif n'a qu'une case :
    #       retoucher une AUTRE ligne tombe de toute facon dans « nouvelle
    #       visite », et la mutation qui supprime quitter() echappait. Sur la
    #       meme ligne, la difference est nette — « reprise » si la visite a
    #       ete fermee, « frappe » sinon, et dans ce dernier cas les mots
    #       recomptent en extension alors qu'ils ne devraient pas.
    a[1][-1] = phrases[3][:30] + " Repris apres une longue pause."
    etapes.append([list(p) for p in a])

    # 9. Tout effacer : chaque ligne disparait.
    etapes.append([[""]])

    # Un paysage marche a cote, nourri par les faits. C'est la chaine
    # ENTIERE qui se compare alors — texte, faits, verdicts, etat final — et
    # pas seulement le rapprochement. Une divergence de verdict ne se verrait
    # nulle part ailleurs : les deux cotes rendraient les memes faits et
    # feraient pousser deux paysages differents.
    p = Paysage(identifiant="guet", cle_dossier="guet")
    g = Guet(silence=3)
    def styles_de(paras):
        # Le dernier paragraphe est une citation : sans un style DIFFERENT plus
        # loin que le premier, indexer par ligne ou par paragraphe donnerait le
        # meme resultat, et la mutation qui les confond echapperait.
        return ["Titre 1"] + ["Normal"] * (len(paras) - 2) + ["Citation"]
    releves = []
    depart_corps = corps(depart)
    amorce = g.amorcer(depart_corps, styles_de(depart))
    p.rattacher(amorce, jour=40, heure=10)
    # Pris ICI et pas apres la boucle : a la fin le document est vide, donc
    # g.ids l'est aussi, et le cahier promettait une liste vide la ou le
    # portage rend les quatre identifiants de l'amorce. La parite l'a dit tout
    # de suite — c'est le cahier qui avait tort, pas le code.
    ids_depart = list(g.ids)
    # Des temps ECOULES varies, et c'est necessaire : avec toujours
    # l'intervalle, max(ecoule, 1) et max(ecoule, INTERVALLE) rendent la meme
    # chose, et le plancher de la normalisation ne se verifie pas. On y met un
    # releve EN AVANCE (5 ms), celui qui transformait quatre mots tapes en un
    # collage, et des releves EN RETARD, qu'il faut au contraire corriger.
    ecoules = [2000, 10000, 5, 2000, 800, 30000, 1, 2000, 4000]
    for n, paras in enumerate(etapes):
        texte = corps(paras)
        styles = styles_de(paras)
        ecoule = ecoules[n % len(ecoules)]
        faits = g.relever(texte, styles)
        debit = g.debit(faits, ecoule)
        verdicts = g.nourrir(p, faits, jour=40, heure=10, debit=debit)
        releves.append({"texte": texte, "styles": styles, "faits": faits,
                        "ids": list(g.ids), "paragraphes": g.paragraphes,
                        "visitee": g.visitee, "calme": g.calme,
                        "ecoule": ecoule, "debit": debit, "verdicts": verdicts,
                        "greffes": sorted(g.greffes)})

    genres = {f["type"] for r in releves for f in r["faits"]}
    attendus = {"nee", "retouchee", "disparue", "visite_finie"}
    if genres != attendus:
        raise SystemExit(
            "cahier du guet incomplet : %s manquent" % (attendus - genres))

    rendus = {v["verdict"] for r in releves for v in r["verdicts"]}
    for exige in ("ecriture", "frappe", "reprise", "vide", "disparue",
                  "greffe", "conversion"):
        if exige not in rendus:
            raise SystemExit(
                "cahier du guet : le verdict %r n'est jamais rendu" % exige)

    return {"silence": 3, "depart": depart_corps,
            "styles_depart": styles_de(depart), "amorce": amorce,
            "ids_depart": ids_depart, "releves": releves,
            "etat": p.etat(), "serialise": p.serialiser()}


# --------------------------------------------------------------------------
def fabriquer() -> dict:
    import random
    rng = random.Random(11)
    journal, plants, p = cas_journal()
    textes = [e[1] for e in journal if e[0] == "absorber"]
    return {
        "alea": cas_alea(),
        "couleur": cas_couleur(),
        "teinte": cas_teinte(),
        "graines": cas_graines(),
        "figures": cas_figures(),
        "depuis_plant": cas_depuis_plant(p.etat()["plants"]),
        "composition": cas_composition(p.etat()["plants"]),
        "tables": cas_tables(),
        "relectures": cas_relectures(),
        "arrondis": cas_arrondis(),
        "tokenisation": cas_tokenisation(rng),
        "traits": cas_traits(rng),
        "journal": journal,
        "plants": plants,
        "empreintes": len(p.registre),
        # etat() est ce que le volet lira ; serialiser() est ce qu'il
        # rangera. Ni l'un ni l'autre n'apparait dans le journal, et une
        # panne de schema y serait invisible jusqu'au jour ou un paysage
        # se relit vide.
        "etat": p.etat(),
        "serialise": p.serialiser(),
        "rattachement": cas_rattachement(),
        "guet": cas_guet(),
        # Le nombre d'empreintes distinctes sur le corpus entier. Les deux
        # fonctions de hachage sont differentes ; ce chiffre est la seule chose
        # qu'on puisse honnetement leur demander d'avoir en commun.
        "empreintes_corpus": len({empreinte(t) for t in textes}),
        "textes_corpus": len(textes),
    }


def main() -> int:
    CAS.parent.mkdir(parents=True, exist_ok=True)
    d = fabriquer()
    CAS.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    poids = CAS.stat().st_size / 1024
    print(f"cahier : {len(d['tokenisation'])} decoupages,"
          f" {len(d['traits'])} vecteurs,"
          f" {len(d['journal'])} appels,"
          f" {len(d['plants'])} plants  ({poids:.0f} Ko)")

    if "--cas" in sys.argv:
        return 0

    node = "node.exe" if os.name == "nt" else "node"
    try:
        r = subprocess.run([node, str(SCRIPT), str(CAS)], cwd=str(RACINE))
    except FileNotFoundError:
        print("node introuvable : impossible de verifier la parite.")
        return 2
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
