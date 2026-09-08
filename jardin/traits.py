"""
Extraction des traits d'un texte et determination de la famille qui pousse.

Ce module est volontairement independant de Word : il prend du texte brut et
rend un vecteur de traits normalises + un score par famille. L'add-in n'aura
qu'a l'appeler (ou a le reimplementer en JS) avec le contenu du document.

Usage :
    python traits.py mon_texte.txt
    python traits.py --demo
"""

from __future__ import annotations

import math
import re
import sys
import unicodedata
from dataclasses import dataclass, asdict
from pathlib import Path

# --------------------------------------------------------------------------
# Paliers de revelation (en mots). A recalibrer en testant sur de vrais textes.
# --------------------------------------------------------------------------
PALIER_INDICES = 200      # le germe commence a s'orienter
PALIER_DIVERGENCE = 800   # la famille devient lisible

# En dessous de cette marge entre le 1er et le 2e score, aucune famille ne
# domine vraiment : c'est l'abstrait qui l'emporte, par refus de classement.
MARGE_DOMINANCE = 0.06


# --------------------------------------------------------------------------
# Outils de normalisation
# --------------------------------------------------------------------------
def borne(x: float, bas: float, haut: float) -> float:
    """Ramene x dans 0..1 lineairement entre bas et haut, en ecretant."""
    if haut == bas:
        return 0.0
    return max(0.0, min(1.0, (x - bas) / (haut - bas)))


def coefficient_variation(valeurs: list[float]) -> float:
    """Ecart-type / moyenne. Mesure la regularite independamment de l'echelle."""
    if len(valeurs) < 2:
        return 0.0
    moy = sum(valeurs) / len(valeurs)
    if moy == 0:
        return 0.0
    var = sum((v - moy) ** 2 for v in valeurs) / len(valeurs)
    return math.sqrt(var) / moy


# --------------------------------------------------------------------------
# Decoupage
# --------------------------------------------------------------------------
FIN_DE_PHRASE = re.compile(r"[.!?\u2026]+[\s\u00a0]+|[.!?\u2026]+$")
MOT = re.compile(r"[^\W\d_]+", re.UNICODE)

# Abreviations frequentes en francais, pour eviter les fausses coupures.
ABREVIATIONS = {
    "m", "mme", "mlle", "dr", "pr", "st", "ste", "cf", "etc", "ex",
    "av", "ap", "env", "p", "pp", "vol", "no", "fig", "art",
}


def en_mots(texte: str) -> list[str]:
    return MOT.findall(texte)


def en_phrases(texte: str) -> list[str]:
    """Decoupage naif mais suffisant : on protege les abreviations connues."""
    brut = FIN_DE_PHRASE.split(texte)
    phrases: list[str] = []
    tampon = ""
    for morceau in brut:
        if morceau is None:
            continue
        morceau = morceau.strip()
        if not morceau:
            continue
        candidat = (tampon + " " + morceau).strip() if tampon else morceau
        dernier = en_mots(candidat)
        if dernier and _sans_accent(dernier[-1]).lower() in ABREVIATIONS:
            tampon = candidat
            continue
        phrases.append(candidat)
        tampon = ""
    if tampon:
        phrases.append(tampon)
    return [p for p in phrases if en_mots(p)]


def en_paragraphes(texte: str) -> list[str]:
    lignes = [l.strip() for l in texte.replace("\r\n", "\n").split("\n")]
    paragraphes: list[str] = []
    courant: list[str] = []
    for ligne in lignes:
        if ligne:
            courant.append(ligne)
        elif courant:
            paragraphes.append(" ".join(courant))
            courant = []
    if courant:
        paragraphes.append(" ".join(courant))
    # Si le texte n'utilise pas de ligne vide, chaque ligne est un paragraphe.
    if len(paragraphes) <= 1:
        paragraphes = [l for l in lignes if l]
    return paragraphes


def _deplier(texte: str) -> str:
    """Depose les accents. Sans memoire : a utiliser sur autre chose qu'un mot."""
    return "".join(
        c for c in unicodedata.normalize("NFD", texte)
        if unicodedata.category(c) != "Mn"
    )


# Memoire de normalisation. Le vocabulaire d'un document est borne (~30 000
# formes pour une these) alors que les appels se comptent en centaines de
# milliers : sans ce cache, unicodedata.normalize represente l'essentiel du
# temps d'extraction une fois MATTR passe en O(n). Se porte tel quel en JS.
#
# Le cache ne vaut que si la cle revient. Sur un MOT c'est le cas des centaines
# de fois ; sur un PARAGRAPHE, jamais — chacun est normalise une fois et
# n'existe qu'a un exemplaire. Faire passer les paragraphes par ici remplissait
# le cache de 656 entrees pour 656 paragraphes — 766 Ko sur 40 000 mots, et
# 2,8 Mo sur une these de 146 000 — et le cache cense tenir un vocabulaire
# devenait une copie du document. Tout ce qui n'est pas un mot passe par
# _deplier.
_ACCENTS: dict[str, str] = {}


def _sans_accent(mot: str) -> str:
    connu = _ACCENTS.get(mot)
    if connu is not None:
        return connu
    nu = _deplier(mot)
    _ACCENTS[mot] = nu
    return nu


# --------------------------------------------------------------------------
# Signaux bruts
# --------------------------------------------------------------------------
# Attention : le tiret cadratin (\u2014) est EXCLU des puces. En francais il
# introduit une replique de dialogue, pas un element de liste. Le confondre
# faisait basculer toute la fiction dialoguee vers Architecture.
PUCES = ("*", "\u2022", "\u25e6", "\u00b7")
TIRET_REPLIQUE = re.compile(r"^[\u2014\u2013]\s+")
# Une paire de guillemets n'est un dialogue que si elle enferme un enonce.
# Sur un mot isole, c'est une mise a distance (« bruit », « symptome »), ce qui
# est un marqueur d'essai, pas de fiction.
PAIRE_GUILLEMETS = re.compile(r"\u00ab([^\u00bb]{0,400})\u00bb|\u201c([^\u201d]{0,400})\u201d")
MOTS_MINIMUM_ENONCE = 4
PONCTUATION_RARE = re.compile(r"[;:\u2014\u2013()\[\]\u2026]")

CONNECTEURS_SUBORDINATION = {
    "que", "qui", "dont", "lequel", "laquelle", "lesquels", "lesquelles",
    "parce", "puisque", "quoique", "bien", "alors", "tandis", "lorsque",
    "afin", "pourvu", "malgre", "cependant", "toutefois", "neanmoins",
    "ainsi", "donc", "or", "car", "mais", "comme", "si", "quand",
}


def est_structurel(paragraphe: str) -> bool:
    """
    Heuristique de titre / element de liste, pour du texte brut.

    Dans l'add-in Word, remplacer cette fonction par une lecture du style reel
    du paragraphe (Heading 1, List Paragraph, etc.) : c'est bien plus fiable.
    """
    p = paragraphe.strip()
    if not p:
        return False
    # Une replique de dialogue n'est jamais un element de structure.
    if TIRET_REPLIQUE.match(p):
        return False
    if p.startswith("#"):
        return True
    if any(p.startswith(puce + " ") for puce in PUCES):
        return True
    if p.startswith("- "):
        return True
    if re.match(r"^\d+[.)]\s", p):
        return True
    # Ligne courte, sans ponctuation finale : tres probablement un titre.
    if len(p) < 60 and p[-1] not in ".!?\u2026:;," and len(en_mots(p)) <= 9:
        return True
    return False


def mattr(mots: list[str], fenetre: int = 200) -> float:
    """
    Moving-Average Type-Token Ratio.

    Le TTR brut chute mecaniquement quand le texte s'allonge : utiliser le TTR
    brut ici ferait deriver la famille au fil de la redaction, ce qui est
    exactement ce qu'on ne veut pas. La moyenne glissante rend la mesure
    stable quelle que soit la longueur.
    """
    if not mots:
        return 0.0
    formes = [_sans_accent(m).lower() for m in mots]
    if len(formes) <= fenetre:
        return len(set(formes)) / len(formes)

    # Fenetre glissante a comptes courants : O(n) au lieu de O(n x fenetre).
    # Refaire un set() a chaque decalage coutait 772 ms sur 146 000 mots, soit
    # 70 % du temps d'extraction, et c'est ce qui a fait croire que MATTR
    # devait etre mis en cache pour tenir dans le budget de 100 ms.
    comptes: dict[str, int] = {}
    for f in formes[:fenetre]:
        comptes[f] = comptes.get(f, 0) + 1
    distincts = len(comptes)
    total = distincts / fenetre
    fenetres = 1
    for i in range(fenetre, len(formes)):
        sortant = formes[i - fenetre]
        comptes[sortant] -= 1
        if comptes[sortant] == 0:
            del comptes[sortant]
            distincts -= 1
        entrant = formes[i]
        if entrant not in comptes:
            distincts += 1
            comptes[entrant] = 1
        else:
            comptes[entrant] += 1
        total += distincts / fenetre
        fenetres += 1
    return total / fenetres


# --------------------------------------------------------------------------
# Vecteur de traits
# --------------------------------------------------------------------------
@dataclass
class Traits:
    mots: int
    phrases: int
    paragraphes: int
    # Tous les champs ci-dessous sont normalises entre 0 et 1.
    longueur: float          # phrases longues
    rythme: float            # irregularite de la longueur des phrases
    subordination: float     # densite de virgules et de connecteurs
    regularite: float        # regularite de la longueur des paragraphes
    structure: float         # titres, listes, blocs
    dialogue: float          # guillemets, tirets de replique
    interrogation: float     # densite de points d'interrogation
    diversite: float         # richesse lexicale (MATTR)
    ponctuation_rare: float  # ; : parentheses tirets points de suspension
    # Signal comportemental, fourni par l'add-in (voir plus bas).
    reecriture: float = 0.0


def extraire(texte: str, reecriture: float = 0.0) -> Traits:
    """Calcule le vecteur de traits normalise d'un texte."""
    mots = en_mots(texte)
    phrases = en_phrases(texte)
    paragraphes = en_paragraphes(texte)

    if not mots or not phrases:
        return Traits(0, 0, 0, *([0.0] * 9))

    longueurs_phrases = [len(en_mots(p)) for p in phrases]
    longueurs_phrases = [l for l in longueurs_phrases if l > 0]
    longueurs_paragraphes = [len(en_mots(p)) for p in paragraphes]
    longueurs_paragraphes = [l for l in longueurs_paragraphes if l > 0]

    longueur_moy = sum(longueurs_phrases) / len(longueurs_phrases)
    cv_phrases = coefficient_variation(longueurs_phrases)
    cv_paragraphes = coefficient_variation(longueurs_paragraphes)

    virgules_par_phrase = texte.count(",") / len(phrases)
    # On compte les OCCURRENCES pour cent mots, pas les types presents.
    # Compter les types (len(formes & CONNECTEURS)) etait une couverture de
    # vocabulaire : elle croit avec la longueur et sature vers 1 100 mots, donc
    # a l'echelle d'un segment de 2 500 mots tout texte francais valait 1,00 et
    # la composante ne distinguait plus rien. C'est exactement la derive
    # mecanique reprochee au TTR brut, par une autre porte.
    occurrences = sum(1 for m in mots
                      if _sans_accent(m).lower() in CONNECTEURS_SUBORDINATION)
    connecteurs = occurrences / len(mots) * 100

    enonces = 0
    for gauche, droite in PAIRE_GUILLEMETS.findall(texte):
        contenu = gauche or droite
        if len(en_mots(contenu)) >= MOTS_MINIMUM_ENONCE:
            enonces += 1
    repliques = sum(1 for p in paragraphes if TIRET_REPLIQUE.match(p.strip()))
    densite_dialogue = (2 * enonces + 3 * repliques) / max(len(mots), 1) * 100

    interro = texte.count("?") / len(phrases)
    rares = len(PONCTUATION_RARE.findall(texte)) / max(len(mots), 1) * 100
    part_structurelle = sum(1 for p in paragraphes if est_structurel(p)) / len(paragraphes)

    return Traits(
        mots=len(mots),
        phrases=len(phrases),
        paragraphes=len(paragraphes),
        longueur=borne(longueur_moy, 8, 30),
        rythme=borne(cv_phrases, 0.30, 1.00),
        subordination=0.7 * borne(virgules_par_phrase, 0.3, 3.0)
                      + 0.3 * borne(connecteurs, 0.5, 6.0),
        regularite=1.0 - borne(cv_paragraphes, 0.20, 1.20),
        structure=borne(part_structurelle, 0.0, 0.35),
        dialogue=borne(densite_dialogue, 0.0, 4.0),
        interrogation=borne(interro, 0.0, 0.15),
        diversite=borne(mattr(mots), 0.55, 0.80),
        ponctuation_rare=borne(rares, 0.3, 3.0),
        reecriture=max(0.0, min(1.0, reecriture)),
    )


# --------------------------------------------------------------------------
# Familles
# --------------------------------------------------------------------------
# Poids explicites, faits pour etre bidouilles. Chaque entree est
# (nom_du_trait, poids, inverser).
POIDS: dict[str, list[tuple[str, float, bool]]] = {
    "vegetal": [
        ("subordination", 0.34, False),
        ("longueur", 0.26, False),
        ("regularite", 0.22, True),
        ("structure", 0.18, True),
    ],
    "architecture": [
        ("structure", 0.40, False),
        ("regularite", 0.24, False),
        ("longueur", 0.20, True),
        ("subordination", 0.16, True),
    ],
    # L'interrogation pese peu : l'essai est plein de questions rhetoriques,
    # et lui donner du poids faisait passer la philosophie pour du dialogue.
    "creature": [
        ("dialogue", 0.52, False),
        ("rythme", 0.33, False),
        ("interrogation", 0.15, False),
    ],
    "abstrait": [
        ("diversite", 0.58, False),
        ("ponctuation_rare", 0.42, False),
    ],
}

NOMS = {
    "vegetal": "Vegetal",
    "architecture": "Architecture",
    "creature": "Creature",
    "abstrait": "Abstrait",
}


def scores(traits: Traits) -> dict[str, float]:
    """Score 0..1 pour chaque famille."""
    valeurs = asdict(traits)
    resultat: dict[str, float] = {}
    for famille, composantes in POIDS.items():
        total = 0.0
        for nom, poids, inverser in composantes:
            v = valeurs[nom]
            total += poids * (1.0 - v if inverser else v)
        resultat[famille] = round(total, 4)
    return resultat


@dataclass
class Revelation:
    stade: str                    # germe | indices | divergence
    famille: str | None           # None tant qu'on est au stade germe
    provisoire: bool              # True au stade indices
    par_refus: bool               # True si l'abstrait gagne faute de dominance
    marge: float                  # ecart entre le 1er et le 2e score
    secondaire: str | None        # famille d'appoint, pour les traits hybrides
    scores: dict[str, float]
    traits: Traits


def revele(traits: Traits) -> Revelation:
    s = scores(traits)
    classement = sorted(s.items(), key=lambda kv: kv[1], reverse=True)
    premier, second = classement[0], classement[1]
    marge = premier[1] - second[1]

    par_refus = False
    famille = premier[0]
    if marge < MARGE_DOMINANCE and famille != "abstrait":
        famille = "abstrait"
        par_refus = True

    if traits.mots < PALIER_INDICES:
        stade, provisoire, visible = "germe", True, None
    elif traits.mots < PALIER_DIVERGENCE:
        stade, provisoire, visible = "indices", True, famille
    else:
        stade, provisoire, visible = "divergence", False, famille

    secondaire = next((n for n, _ in classement if n != famille), None)
    return Revelation(
        stade=stade,
        famille=visible,
        provisoire=provisoire,
        par_refus=par_refus,
        marge=round(marge, 4),
        secondaire=secondaire,
        scores=s,
        traits=traits,
    )


# --------------------------------------------------------------------------
# Affichage
# --------------------------------------------------------------------------
def barre(valeur: float, largeur: int = 22) -> str:
    plein = round(valeur * largeur)
    return "#" * plein + "." * (largeur - plein)


def rapport(r: Revelation, titre: str = "") -> str:
    t = r.traits
    lignes = []
    if titre:
        lignes.append(f"\n=== {titre} ===")
    lignes.append(f"{t.mots} mots / {t.phrases} phrases / {t.paragraphes} paragraphes")
    lignes.append("")
    for nom in ("longueur", "rythme", "subordination", "regularite",
                "structure", "dialogue", "interrogation", "diversite",
                "ponctuation_rare"):
        v = getattr(t, nom)
        lignes.append(f"  {nom:>17} {barre(v)} {v:.2f}")
    lignes.append("")
    for nom, val in sorted(r.scores.items(), key=lambda kv: kv[1], reverse=True):
        lignes.append(f"  {NOMS[nom]:>17} {barre(val)} {val:.3f}")
    lignes.append("")
    if r.famille is None:
        lignes.append(f"  -> stade germe : rien de lisible avant {PALIER_INDICES} mots")
    else:
        suffixe = " (provisoire)" if r.provisoire else ""
        motif = " par refus de classement" if r.par_refus else ""
        lignes.append(f"  -> {NOMS[r.famille].upper()}{suffixe}{motif}")
        lignes.append(f"     marge sur le suivant : {r.marge:.3f}"
                      f" | trait secondaire : {NOMS[r.secondaire]}")
    return "\n".join(lignes)


def demo() -> None:
    dossier = Path(__file__).parent / "echantillons"
    fichiers = sorted(dossier.glob("*.txt"))
    if not fichiers:
        print("Aucun echantillon trouve.")
        return
    for f in fichiers:
        texte = f.read_text(encoding="utf-8")
        print(rapport(revele(extraire(texte)), f.stem))
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demo()
    elif len(sys.argv) > 1:
        chemin = Path(sys.argv[1])
        print(rapport(revele(extraire(chemin.read_text(encoding="utf-8"))), chemin.name))
    else:
        print(__doc__)
