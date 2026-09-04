"""
Les phrases de nuit.

Ce fichier regle les points ouverts 1 et 2, qui n'en font qu'un.

    1. « Le creux des phrases. Neuf sur douze felicitent ou encouragent. Il
       manque celle qui ne demande rien — pour les nuits ou on ecrit parce que
       ca ne va pas. »
    2. « Declencher "c'est genial" et "mais oui" sur un evenement plutot que
       sur le paquet : un paragraphe repris cinq fois puis prolonge est un
       deblocage, et une phrase qui arrive pile la ne semblerait plus
       aleatoire. »

Le systeme n'a besoin d'aucun signal nouveau pour les deux. Il mesure deja les
DEUX AXES, et ce sont eux qui disent dans quel etat quelqu'un se trouve :

    maturite qui monte, extension nulle    -> on retourne la meme phrase sans
                                              avancer. C'est la nuit ou on
                                              ecrit parce que ca ne va pas.
    reprises repetees PUIS un paragraphe   -> on a laché prise et on est
    neuf                                      reparti. C'est le deblocage.
    extension reguliere, aucune reprise    -> ca coule.

Les deux axes qui resolvent le probleme de la recompense resolvent donc aussi
celui du ton. C'est la meme decision qui paie deux fois.

⚠️ LES PHRASES NE SE GENERENT PAS. Le registre `creux` est deliberement vide :
c'est a celui qui offre de l'ecrire. Tout le reste du systeme marcherait pour
n'importe qui ; ces phrases-la, non. Tant qu'il est vide, la nuit de creux
retombe sur le paquet ordinaire — rien ne casse, il manque juste ce qui compte.
"""

from __future__ import annotations

import random
import unicodedata
from dataclasses import dataclass, field
from datetime import date as _date

from message import A, Toile, message, cadre_de
from grammaire import _entete, SAUT, Teinte

ORIGINE = "2027-01-01"

# --------------------------------------------------------------------------
# Les registres
# --------------------------------------------------------------------------
# COMMUNES : le paquet battu, pour les nuits ordinaires.
COMMUNES = [
    "il est tard, et tu ecris quand meme",
    "personne ne te regarde. moi si.",
    "tu es trop {fort}",
    "j'aime bien ce paragraphe, ca tue",
    "un petit cafe ? un the ?",
    "alleeeeeeeez",
    "n'oublie pas de boire de l'eau",
]

# NOMINATIVES : plus rares, elles frappent parce qu'elles n'arrivent pas
# souvent. Elles restent dans le paquet.
NOMINATIVES = [
    "{prenom}, encore debout ?",
    "{prenom}, ce chapitre avance bien",
    "va dormir, {prenom}",
]

# DEBLOCAGE : ces deux-la etaient dans le paquet, ou elles tombaient n'importe
# quand. Elles sortent du paquet et attendent leur moment.
DEBLOCAGE = [
    "c'est geniaaaaaaaaaaaal",
    "mais ouiiiiiiii",
]

# ELAN : rien ici pour l'instant. Facultatif — une nuit qui coule n'a peut-etre
# besoin de personne.
ELAN: list = []

# ------------------------------------------------------------------- A ECRIRE
# CREUX : la nuit ou la maturite monte et ou rien ne pousse. Quelqu'un tourne
# autour de la meme phrase depuis deux heures.
#
# Ce qu'il ne faut pas y mettre : rien qui felicite, rien qui encourage, rien
# qui demande quoi que ce soit — ni de continuer, ni d'aller dormir, ni de
# boire de l'eau. Les neuf autres font deja ca. Ce registre est celui d'une
# presence qui n'attend rien.
#
# Il est vide, et c'est voulu : c'est le seul endroit du systeme ou la voix de
# celui qui offre passe.
CREUX: list = []

REGISTRES = {
    "creux": CREUX,
    "deblocage": DEBLOCAGE,
    "elan": ELAN,
}

PROFILS = {
    "camille": {"prenom": "camille", "accord": "e"},
    "julien": {"prenom": "julien", "accord": ""},
}


def sans_accent(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


# --------------------------------------------------------------------------
# Ce que la nuit a produit
# --------------------------------------------------------------------------
REPRISES_AVANT_DEBLOCAGE = 5     # « repris cinq fois puis prolonge »
REPRISES_POUR_UN_CREUX = 4
PARAGRAPHES_POUR_UN_ELAN = 6


@dataclass
class Nuit:
    """
    Les deux axes, mesures sur la seule fenetre de nuit.

    Alimente par les memes verdicts que Paysage.absorber / .retoucher : le
    routage des phrases ne demande aucune instrumentation supplementaire.
    """
    nouveaux: int = 0
    reprises: int = 0
    mots: int = 0
    _reprises_courantes: int = 0     # sur le paragraphe en cours
    _deblocage: bool = False

    def enregistrer(self, verdict: str, mots: int = 0):
        if verdict in ("ecriture", "conversion"):
            # Un paragraphe neuf juste apres avoir tourne longtemps autour du
            # precedent : c'est le moment ou ca se debloque.
            if self._reprises_courantes >= REPRISES_AVANT_DEBLOCAGE:
                self._deblocage = True
            self._reprises_courantes = 0
            self.nouveaux += 1
            self.mots += mots
        elif verdict == "frappe":
            self.mots += mots
        elif verdict == "reprise":
            self.reprises += 1
            self._reprises_courantes += 1

    def evenement(self) -> str | None:
        """Le registre a servir cette nuit, ou None pour le paquet ordinaire."""
        if self._deblocage:
            return "deblocage"
        if self.nouveaux == 0 and self.reprises >= REPRISES_POUR_UN_CREUX:
            return "creux"
        if self.reprises == 0 and self.nouveaux >= PARAGRAPHES_POUR_UN_ELAN:
            return "elan"
        return None


# --------------------------------------------------------------------------
# Le paquet battu
# --------------------------------------------------------------------------
def _numero_de_nuit(date_iso: str, origine=ORIGINE) -> int:
    return (_date(*map(int, date_iso.split("-")))
            - _date(*map(int, origine.split("-")))).days


_MEMOIRE_PAQUETS: dict = {}


def _paquet(tour: int, corpus: list) -> list:
    """
    Le paquet REELLEMENT servi au tour donne, raccord compris.

    Le raccord doit se faire contre le paquet effectivement servi au tour
    precedent, pas contre son premier brassage. La version d'avant comparait
    a `battre(tour - 1)` — c'est-a-dire au paquet AVANT son propre raccord —
    donc elle protegeait la frontiere par rapport a un ordre qui n'avait
    jamais ete joue. Resultat mesure : ecart minimum de 1 nuit, soit la meme
    phrase deux soirs de suite, ce que le paquet existe pour empecher.

    On construit donc les tours en chaine, en memorisant.
    """
    cle = (tour, len(corpus), corpus[0] if corpus else "")
    if cle in _MEMOIRE_PAQUETS:
        return _MEMOIRE_PAQUETS[cle]

    garde = max(2, min(4, len(corpus) // 3))
    paquet = list(corpus)
    random.Random(tour * 7919).shuffle(paquet)
    if tour > 0:
        queue = set(_paquet(tour - 1, corpus)[-garde:])
        essai = 0
        while set(paquet[:garde]) & queue and essai < 200:
            essai += 1
            random.Random(tour * 7919 + essai * 104729).shuffle(paquet)
    _MEMOIRE_PAQUETS[cle] = paquet
    return paquet


def _du_paquet(date_iso: str, corpus: list) -> str:
    """
    Une phrase par nuit, distribuee comme un PAQUET BATTU.

    Un tirage independant par nuit produit des repetitions immediates — deux
    fois la meme phrase a deux nuits d'intervalle, ce qui detruit la rarete.
    Avec un paquet, aucune phrase ne revient avant que toutes soient passees.
    """
    nuit = _numero_de_nuit(date_iso)
    tour, rang = divmod(nuit, len(corpus))
    return _paquet(tour, corpus)[rang]


def phrase_de_la_nuit(profil: dict, date_iso: str, nuit: Nuit | None = None) -> str:
    """
    La phrase de cette nuit.

    Un evenement l'emporte sur le paquet : c'est tout l'objet du point ouvert
    2. Une phrase qui arrive pile au moment du deblocage ne semble plus
    aleatoire — et elle ne peut pas tomber a cote, puisqu'elle n'est plus
    tiree au sort.

    Si le registre de l'evenement est vide, on retombe sur le paquet. C'est le
    cas du creux tant que ses phrases ne sont pas ecrites.
    """
    corpus = COMMUNES + NOMINATIVES
    brut = None

    if nuit is not None:
        registre = REGISTRES.get(nuit.evenement() or "", [])
        if registre:
            # Dans un registre d'evenement, on tourne sur la date pour ne pas
            # servir deux fois la meme a deux declenchements rapproches.
            brut = registre[_numero_de_nuit(date_iso) % len(registre)]

    if brut is None:
        brut = _du_paquet(date_iso, corpus)

    return sans_accent(brut.format(prenom=profil["prenom"],
                                   fort="fort" + profil["accord"]))


# --------------------------------------------------------------------------
def verifier(profils=PROFILS) -> bool:
    manque = set()
    tout = COMMUNES + NOMINATIVES + DEBLOCAGE + ELAN + CREUX
    for p in profils.values():
        for brut in tout:
            t = sans_accent(brut.format(prenom=p["prenom"],
                                        fort="fort" + p["accord"])).upper()
            manque |= {c for c in t if c not in A}
    print(f"  caracteres non tracables : {sorted(manque) or 'aucun'}")

    # Ecart entre deux occurrences de la meme phrase, sur deux ans.
    vues, ecarts = {}, []
    for n in range(730):
        j = (_date(2027, 1, 1)).toordinal() + n
        d = _date.fromordinal(j).isoformat()
        ph = phrase_de_la_nuit(PROFILS["camille"], d)
        if ph in vues:
            ecarts.append(n - vues[ph])
        vues[ph] = n
    print(f"  paquet : ecart moyen {sum(ecarts)/len(ecarts):.1f} nuits,"
          f" minimum {min(ecarts)}, {len(vues)} phrases distinctes")

    # Routage par evenement.
    cas = [
        ("nuit ordinaire", [("ecriture", 90)] * 3),
        ("creux (on tourne en rond)", [("reprise", 0)] * 6),
        ("deblocage (5 reprises puis on repart)",
         [("reprise", 0)] * 5 + [("ecriture", 80)]),
        ("elan (ca coule)", [("ecriture", 95)] * 8),
    ]
    print()
    ok = True
    for lab, evenements in cas:
        n = Nuit()
        for v, m in evenements:
            n.enregistrer(v, m)
        ev = n.evenement()
        ph = phrase_de_la_nuit(PROFILS["camille"], "2027-03-02", n)
        vide = ev in REGISTRES and not REGISTRES[ev]
        note = "  <- registre vide, repli sur le paquet" if vide else ""
        print(f"  {lab:<38} {str(ev):<10} \"{ph}\"{note}")
    attendus = ["deblocage", "creux", "elan"]
    for lab, evenements, attendu in (("creux", [("reprise", 0)] * 6, "creux"),
                                     ("deblocage",
                                      [("reprise", 0)] * 5 + [("ecriture", 80)],
                                      "deblocage"),
                                     ("elan", [("ecriture", 95)] * 8, "elan")):
        n = Nuit()
        for v, m in evenements:
            n.enregistrer(v, m)
        ok &= n.evenement() == attendu
    print(f"\n  routage des trois evenements : {'ok' if ok else 'ECHEC'}")
    if not CREUX:
        print("")
        print("  /!\ le registre CREUX est vide - point ouvert 1 non clos.")
        print("       Le mecanisme l'attend ; les phrases sont a ecrire.")
    return ok


def planche():
    CW, CH, MG, TOP = 330, 200, 130, 54
    exemples = [("camille", "2027-01-14"), ("camille", "2027-03-02"),
                ("julien", "2027-01-14"), ("julien", "2027-05-21"),
                ("camille", "2027-11-08"), ("julien", "2027-09-30")]
    W, H = MG + CW * 3 + 20, TOP + CH * 2 + 20
    o = _entete(W, H)
    o.append(f'<text x="18" y="{TOP + 40}" font-size="12" fill="#2c3230">Une nuit,</text>')
    o.append(f'<text x="18" y="{TOP + 58}" font-size="12" fill="#2c3230">une phrase</text>')
    for k, (qui, date) in enumerate(exemples):
        i, j = divmod(k, 3)
        t = Toile()
        # Graine derivee de la date, pas de hash() : hash() sur une chaine est
        # randomise a chaque processus, donc la planche n'etait pas
        # reproductible — dans un projet dont la regle est que la graine vient
        # du document, jamais de l'horloge.
        message(t, phrase_de_la_nuit(PROFILS[qui], date),
                1.0, graine=_numero_de_nuit(date) * 2654435761 % 65536)
        o.append(t.svg(MG + j * CW, TOP + i * CH, CW, CH))
        o.append(f'<text x="{MG + j*CW + CW/2}" y="{TOP + i*CH + CH - 8}" '
                 f'font-size="9.5" text-anchor="middle" fill="#9a938c" '
                 f'letter-spacing="1.2">{qui.upper()} — {date}</text>')
    return SAUT.join(o) + '</g></svg>'


if __name__ == "__main__":
    verifier()
    open("planche_phrases_v7.svg", "w", encoding="utf-8").write(planche())
    print("\nplanche_phrases_v7.svg ecrit")
