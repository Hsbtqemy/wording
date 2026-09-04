"""
Parite Python / JavaScript.

Le Python est la specification, le JavaScript est le livrable. Tant que les
deux existent, il faut une facon de savoir qu'ils disent la meme chose — sinon
le banc d'essai valide un programme que personne n'installe.

Ce fichier fabrique un cahier de cas AVEC LES REPONSES DU PYTHON, puis lance
node dessus. Le JavaScript rejoue exactement les memes appels et compare.

    python parite.py            fabrique, lance node, rend un code de sortie
    python parite.py --cas      fabrique seulement (addin/parite/cas.json)

Pourquoi un cahier plutot que la meme graine des deux cotes, comme le laissait
entendre corpus.py : rejouer la graine demanderait de porter le Mersenne
Twister de random.Random en JavaScript. On testerait alors le generateur, pas
le portage — et le premier ecart viendrait du generateur, la ou on ne peut rien
en apprendre. Le cahier deplace la frontiere au bon endroit : le corpus reste
du Python, et le JavaScript ne recoit que du texte et des appels.

Ce qui est compare :

  normalisation   la meme chaine normalisee. C'est la que se voient les ecarts
                  d'Unicode : \\w ASCII contre \\w Unicode, NFD, casse.
  decoupage       mots, phrases, paragraphes, titre-ou-pas
  traits          les neuf traits normalises, a 1e-9 pres
  scores          les quatre familles, et la revelation qui en sort
  journal         chaque verdict de absorber / retoucher, appel par appel
  plants          l'etat final de chaque plant
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

import corpus
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
                "inchangee", "frappe", "reprise", "reprise en cours"}
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
        "paysage": {
            "STYLES_TITRE": sorted(paysage_mod.STYLES_TITRE),
            "STYLES_IGNORES": sorted(paysage_mod.STYLES_IGNORES),
            "VARIANTES": {chr(k): v for k, v in paysage_mod._VARIANTES.items()},
            "MOTS_PAR_PLANT": paysage_mod.MOTS_PAR_PLANT,
            "PARAGRAPHES_PAR_PLANT": paysage_mod.PARAGRAPHES_PAR_PLANT,
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


# --------------------------------------------------------------------------
def fabriquer() -> dict:
    import random
    rng = random.Random(11)
    journal, plants, p = cas_journal()
    textes = [e[1] for e in journal if e[0] == "absorber"]
    return {
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
