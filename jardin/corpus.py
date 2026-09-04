"""
Generateur de texte a profil de traits impose.

Les quatre echantillons sont des caricatures de 300 mots. Ils suffisent a
regler les bornes de normalisation, pas a eprouver les mecanismes : recombiner
leurs phrases produit surtout des doublons (2 346 empreintes distinctes pour
4 548 paragraphes au premier essai), donc un document qui ne pousse pas.

Ici le texte est fabrique a partir d'un PROFIL — longueur de phrase, densite de
virgules et de connecteurs, part de structure, dialogue, ponctuation rare,
etendue du vocabulaire. C'est exactement ce que traits.py mesure, donc c'est un
corpus honnete pour tester les mecanismes : on ne teste pas si le francais est
credible, on teste si la machine lit ce qu'on lui donne a lire.

Deux usages :
  - fabriquer une these de 146 000 mots pour banc.py
  - au portage, rejouer la meme graine en JS et comparer les vecteurs de traits
"""

from __future__ import annotations

import random

# --------------------------------------------------------------------------
# Vocabulaire, sans accents comme le reste du code.
# --------------------------------------------------------------------------
NOMS = """maison porte fenetre couloir table lampe chambre jardin mur toit
plancher escalier cuisine armoire tiroir papier lettre carnet page ligne mot
phrase image ombre lumiere matin soir nuit hiver ete automne printemps route
chemin ville village riviere arbre feuille pierre sable vent pluie neige silence
bruit voix pas geste main regard visage memoire souvenir absence presence
distance mesure releve carte trace bord marge residu anomalie lacune symptome
methode systeme charge base index colonne requete reponse rapport analyse
contexte constat risque sauvegarde environnement service delai seuil
hypothese cadre corpus terrain protocole lexique frontiere epaisseur relation
resolution attitude exclusion affinement objet sujet echelle
seuil registre empreinte parcelle plant paysage saison teinte palette contour
membre echine facette anneau sommet branche bouquet tour trame linteau refend
grille tremblement germe divergence dominance derive verrou segment cycle
budget tick fil signal capital greffe brouillon citation marge borne""".split()

VERBES = """ouvrait fermait passait revenait gardait tenait cherchait trouvait
laissait prenait posait montrait cachait suivait attendait traversait
depassait comportait supposait signalait produisait retranchait conservait
augmentait diminuait restait devenait paraissait semblait tombait montait
comptait mesurait notait ecrivait relisait coupait ajoutait""".split()

ADJECTIFS = """long longue court courte vieux vieille neuf neuve froid froide
clair claire sombre etroit etroite large ouvert ouverte ferme fermee lourd
lourde leger legere lent lente vif vive propre sale simple double manuel
manuelle irregulier irreguliere principal principale suffisant insuffisant
commode obstine tenue exacte""".split()

ADVERBES = """toujours jamais souvent parfois encore deja presque a_peine
lentement doucement brusquement ensuite enfin surtout precisement""".split()

DETERMINANTS = "le la les un une des ce cette ses mes leurs quelques".split()
PREPOSITIONS = "dans sur sous vers par pour avec sans contre entre depuis".split()

# Connecteurs reellement presents dans CONNECTEURS_SUBORDINATION de traits.py.
CONNECTEURS = """que qui dont parce_que puisque quoique alors_que tandis_que
lorsque afin_que malgre cependant toutefois neanmoins ainsi donc or car mais
comme si quand""".split()

REPLIQUES = """tu dors est_ce_que ca_change quelque_chose non menteur je_sais
alors_pourquoi j_aime_bien tu_restes il_fait_froid quelle_heure_il_est
ca_depend pas_encore peut_etre je_ne_crois_pas dis_moi""".split()

MOTS_TITRE = """contexte constats methode corpus limites resultats discussion
protocole terrain sources hypothese perspectives annexe cadre mesures
recommandations synthese calendrier budget""".split()


# --------------------------------------------------------------------------
class Profil:
    """
    Chaque champ vise directement un trait de traits.py.

    mots_par_phrase   -> longueur
    dispersion        -> rythme (irregularite de la longueur des phrases)
    virgules          -> subordination (composante virgules)
    connecteurs       -> subordination (composante connecteurs, pour 100 mots)
    structure         -> structure (part de titres et de listes)
    dialogue          -> dialogue (tirets de replique, guillemets)
    questions         -> interrogation
    rare              -> ponctuation_rare (; : parentheses tirets suspension)
    vocabulaire       -> diversite (MATTR)
    """

    def __init__(self, mots_par_phrase, dispersion, virgules, connecteurs,
                 structure, dialogue, questions, rare, vocabulaire,
                 phrases_par_paragraphe, regularite):
        self.mots_par_phrase = mots_par_phrase
        self.dispersion = dispersion
        self.virgules = virgules
        self.connecteurs = connecteurs
        self.structure = structure
        self.dialogue = dialogue
        self.questions = questions
        self.rare = rare
        self.vocabulaire = vocabulaire
        self.phrases_par_paragraphe = phrases_par_paragraphe
        self.regularite = regularite


PROFILS = {
    # Phrases longues, tres subordonnees, paragraphes inegaux, aucune structure.
    "vegetal": Profil(mots_par_phrase=34, dispersion=0.30, virgules=0.85,
                      connecteurs=0.55, structure=0.0, dialogue=0.0,
                      questions=0.01, rare=0.10, vocabulaire=190,
                      phrases_par_paragraphe=3, regularite=0.45),
    # Phrases breves, beaucoup de titres et de listes, paragraphes reguliers.
    "architecture": Profil(mots_par_phrase=11, dispersion=0.22, virgules=0.05,
                           connecteurs=0.04, structure=0.34, dialogue=0.0,
                           questions=0.0, rare=0.04, vocabulaire=70,
                           phrases_par_paragraphe=6, regularite=0.88),
    # Repliques, rythme tres irregulier, beaucoup de questions.
    "creature": Profil(mots_par_phrase=8, dispersion=0.95, virgules=0.12,
                       connecteurs=0.20, structure=0.0, dialogue=0.72,
                       questions=0.30, rare=0.55, vocabulaire=34,
                       phrases_par_paragraphe=4, regularite=0.30),
    # Vocabulaire large, ponctuation rare partout, ni dialogue ni structure.
    "abstrait": Profil(mots_par_phrase=19, dispersion=0.50, virgules=0.35,
                       connecteurs=0.30, structure=0.02, dialogue=0.0,
                       questions=0.18, rare=0.95, vocabulaire=430,
                       phrases_par_paragraphe=5, regularite=0.75),
}

_SIGNES_RARES = [" ; ", " : ", " (parenthese) ", " — ", "... "]


def _lexique(rng, profil):
    """Un vocabulaire de taille imposee : c'est lui qui pilote MATTR."""
    n = profil.vocabulaire
    return {
        "noms": rng.sample(NOMS, min(len(NOMS), max(8, n // 3))),
        "verbes": rng.sample(VERBES, min(len(VERBES), max(5, n // 6))),
        "adjectifs": rng.sample(ADJECTIFS, min(len(ADJECTIFS), max(4, n // 8))),
        "adverbes": rng.sample(ADVERBES, min(len(ADVERBES), max(3, n // 12))),
    }


def _groupe(rng, lx, richesse=0.45):
    # Determinants et prepositions sont un squelette qui se repete et ecrase
    # MATTR quel que soit le vocabulaire. Plus le profil vise une diversite
    # haute, plus on allege ce squelette.
    m = []
    if rng.random() < 1.0 - richesse * 0.6:
        m.append(rng.choice(DETERMINANTS))
    m.append(rng.choice(lx["noms"]))
    if rng.random() < richesse:
        m.append(rng.choice(lx["adjectifs"]))
    return m


def _phrase(rng, profil, lx):
    """Une phrase de longueur tiree autour de la moyenne du profil."""
    cible = max(3, int(rng.gauss(profil.mots_par_phrase,
                                 profil.mots_par_phrase * profil.dispersion)))
    mots: list[str] = []
    while len(mots) < cible:
        if mots:
            if rng.random() < profil.virgules:
                mots[-1] += ","
            if rng.random() < profil.connecteurs:
                mots.append(rng.choice(CONNECTEURS).replace("_", " "))
        richesse = min(0.9, profil.vocabulaire / 480)
        mots += _groupe(rng, lx, richesse)
        mots.append(rng.choice(lx["verbes"]))
        if rng.random() < 0.5:
            mots.append(rng.choice(PREPOSITIONS))
            mots += _groupe(rng, lx, richesse)
        if rng.random() < 0.3:
            mots.append(rng.choice(lx["adverbes"]).replace("_", " "))
    texte = " ".join(mots)
    if rng.random() < profil.rare:
        signe = rng.choice(_SIGNES_RARES)
        coupe = rng.randint(1, max(1, len(mots) - 1))
        texte = " ".join(mots[:coupe]) + signe + " ".join(mots[coupe:])
    return texte + ("?" if rng.random() < profil.questions else ".")


def paragraphe(rng, famille):
    """Renvoie (texte, style) — le style est celui que Word exposerait."""
    profil = PROFILS[famille]
    lx = _lexique(rng, profil)

    if rng.random() < profil.structure:
        d = rng.random()
        titre = " ".join(rng.sample(MOTS_TITRE, rng.randint(1, 3)))
        if d < 0.35:
            return titre.capitalize(), "Titre 2"
        if d < 0.75:
            return "- " + _phrase(rng, profil, lx), "Paragraphe de liste"
        return f"{rng.randint(1, 9)}. " + _phrase(rng, profil, lx), "Paragraphe de liste"

    if rng.random() < profil.dialogue:
        if rng.random() < 0.75:
            return "— " + rng.choice(REPLIQUES).replace("_", " ") + " " \
                   + _phrase(rng, profil, lx), "Normal"
        return '« ' + _phrase(rng, profil, lx).rstrip(".") + ' » ' \
               + _phrase(rng, profil, lx), "Normal"

    # Regularite : plus elle est haute, moins le nombre de phrases varie.
    base = profil.phrases_par_paragraphe
    ecart = max(0, int(round(base * (1 - profil.regularite))))
    n = max(1, base + rng.randint(-ecart, ecart))
    return " ".join(_phrase(rng, profil, lx) for _ in range(n)), "Normal"


def these(mots_cibles=146000, chapitres=8, graine=7):
    """
    Une these : des chapitres a dominante differente, avec contamination.

    Renvoie une liste de (texte, style, jour, heure) — de quoi rejouer une
    redaction complete a travers Paysage.absorber.
    """
    rng = random.Random(graine)
    familles = list(PROFILS)
    sortie, mots, jour, session = [], 0, 12, 0
    par_chapitre = mots_cibles / chapitres

    for c in range(chapitres):
        dominante = familles[c % len(familles)]
        sortie.append((f"Chapitre {c + 1} — {rng.choice(MOTS_TITRE)}",
                       "Titre 1", jour, 14))
        mots_chapitre = 0
        while mots_chapitre < par_chapitre and mots < mots_cibles:
            # 15 % venu d'ailleurs : une these n'est jamais pure, et c'est
            # precisement la que le classement doit tenir.
            f = dominante if rng.random() > 0.15 else rng.choice(familles)
            texte, style = paragraphe(rng, f)
            n = len(texte.split())
            heure = 3 if rng.random() < 0.06 else rng.choice([9, 11, 15, 17, 21, 23])
            sortie.append((texte, style, jour, heure))
            mots += n
            mots_chapitre += n
            # On ecrit par SESSIONS, pas un peu chaque paragraphe. Une session
            # fait quelques centaines a deux mille mots ; entre deux, il se
            # passe des jours, parfois des semaines. Sans ca le document tient
            # sur une seule saison et la couleur ne raconte rien.
            session += n
            if session > rng.randint(400, 1800):
                session = 0
                jour += rng.randint(1, 4) if rng.random() < 0.75                     else rng.randint(5, 30)
    return sortie


def verifier():
    """Chaque profil doit produire la famille qu'il vise."""
    from traits import extraire, revele, NOMS as LIB
    rng = random.Random(1)
    print("Profil -> famille lue (2 000 mots par profil) :\n")
    ok = True
    for famille in PROFILS:
        blocs, mots = [], 0
        while mots < 2000:
            t, _ = paragraphe(rng, famille)
            blocs.append(t)
            mots += len(t.split())
        r = revele(extraire("\n\n".join(blocs)))
        juste = r.famille == famille
        ok &= juste
        print(f"  {famille:<13} -> {LIB[r.famille].upper():<13}"
              f" marge {r.marge:.3f}  {'ok' if juste else 'ECHEC'}")
        t = r.traits
        print(f"                  long {t.longueur:.2f} ryth {t.rythme:.2f}"
              f" subo {t.subordination:.2f} regu {t.regularite:.2f}"
              f" stru {t.structure:.2f} dial {t.dialogue:.2f}"
              f" inte {t.interrogation:.2f} dive {t.diversite:.2f}"
              f" rare {t.ponctuation_rare:.2f}")
    return ok


if __name__ == "__main__":
    verifier()
    d = these()
    from paysage import empreinte
    uniques = len({empreinte(t) for t, *_ in d})
    print(f"\nThese : {sum(len(t.split()) for t, *_ in d)} mots,"
          f" {len(d)} paragraphes, {uniques} empreintes distinctes"
          f" ({uniques / len(d):.1%})")
