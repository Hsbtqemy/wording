"""
Etat persistant de l'organisme.

Le point cle : la famille est VERROUILLEE au moment de la divergence.
Sans ce verrou, le classement porte sur l'ensemble du document et bascule des
que l'equilibre s'inverse ; concretement, un texte qui commence en prose et
passe a des chapitres structures voit sa plante se changer en ville. Sur un
cadeau, c'est un reniement.

Apres le verrou, le texte continue d'agir, mais seulement sur les traits
secondaires : la plante se met a produire des formes geometriques. La forme
finale garde ainsi la memoire de tout le parcours, sans jamais se contredire.

Cet objet est concu pour etre serialise dans Office.context.document.settings,
c'est-a-dire pour vivre a l'interieur du fichier .docx.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict

from traits import (
    Traits, extraire, scores, NOMS,
    PALIER_INDICES, PALIER_DIVERGENCE, MARGE_DOMINANCE,
)

VERSION_ETAT = 1

# Il faut que la dominance tienne sur plusieurs relectures d'affilee avant de
# verrouiller. Un seul echantillon favorable ne suffit pas.
CONFIRMATIONS_REQUISES = 3


@dataclass
class Jardin:
    famille: str | None = None          # verrouillee, ou None avant divergence
    mots_au_verrouillage: int = 0
    scores_au_verrouillage: dict = field(default_factory=dict)
    confirmations: int = 0
    candidate: str | None = None
    mots_max: int = 0                   # anti-retour arriere sur les suppressions
    version: int = VERSION_ETAT

    # ---------------------------------------------------------------- lecture
    @property
    def verrouille(self) -> bool:
        return self.famille is not None

    def stade(self, mots: int) -> str:
        if self.verrouille:
            return "croissance"
        if mots < PALIER_INDICES:
            return "germe"
        return "indices"

    # ------------------------------------------------------------ mise a jour
    def mettre_a_jour(self, texte: str, reecriture: float = 0.0) -> dict:
        """
        Recalcule l'etat a partir du texte complet du document.

        Renvoie de quoi alimenter le rendu : stade, famille, influences.
        """
        t = extraire(texte, reecriture=reecriture)
        s = scores(t)
        self.mots_max = max(self.mots_max, t.mots)

        classement = sorted(s.items(), key=lambda kv: kv[1], reverse=True)
        tete, suivant = classement[0], classement[1]
        marge = tete[1] - suivant[1]

        famille_pressentie = tete[0]
        par_refus = False
        if marge < MARGE_DOMINANCE and famille_pressentie != "abstrait":
            famille_pressentie = "abstrait"
            par_refus = True

        if not self.verrouille:
            # On compte les confirmations successives du meme candidat.
            if famille_pressentie == self.candidate:
                self.confirmations += 1
            else:
                self.candidate = famille_pressentie
                self.confirmations = 1

            if (t.mots >= PALIER_DIVERGENCE
                    and self.confirmations >= CONFIRMATIONS_REQUISES):
                self.famille = famille_pressentie
                self.mots_au_verrouillage = t.mots
                self.scores_au_verrouillage = dict(s)

        return {
            "stade": self.stade(t.mots),
            "famille": self.famille,
            "pressentie": famille_pressentie if not self.verrouille else None,
            "par_refus": par_refus,
            "marge": round(marge, 4),
            "mots": t.mots,
            "progression_vers_revelation": min(1.0, t.mots / PALIER_DIVERGENCE),
            "influences": self.influences(s),
            "scores": s,
            "traits": asdict(t),
        }

    def influences(self, s: dict[str, float]) -> dict[str, float]:
        """
        Ce qui nourrit les traits secondaires apres le verrou.

        On mesure la DERIVE depuis le verrouillage, pas le score absolu : c'est
        le changement de maniere d'ecrire qui fait apparaitre de nouveaux
        traits, pas le niveau de base deja encode dans la famille.
        """
        if not self.verrouille:
            return {}
        sortie = {}
        for nom, valeur in s.items():
            if nom == self.famille:
                continue
            base = self.scores_au_verrouillage.get(nom, valeur)
            derive = valeur - base
            if derive > 0.02:
                sortie[nom] = round(min(1.0, derive * 2.5), 3)
        return sortie

    # ------------------------------------------------- persistance dans .docx
    def serialiser(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def depuis(cls, brut: str | None) -> "Jardin":
        if not brut:
            return cls()
        try:
            donnees = json.loads(brut)
        except (json.JSONDecodeError, TypeError):
            return cls()
        if donnees.get("version") != VERSION_ETAT:
            return cls()
        connus = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in donnees.items() if k in connus})


def resume(etat: dict) -> str:
    """Une ligne lisible, pour le debug."""
    if etat["famille"]:
        infl = ", ".join(
            f"{NOMS[k]} +{v:.2f}" for k, v in
            sorted(etat["influences"].items(), key=lambda kv: -kv[1])[:2]
        )
        return (f"{etat['mots']:>5} mots | {NOMS[etat['famille']].upper():<13}"
                f" verrouille | influences: {infl or 'aucune'}")
    p = etat["progression_vers_revelation"]
    pressentie = NOMS[etat["pressentie"]] if etat["pressentie"] else "-"
    return (f"{etat['mots']:>5} mots | {etat['stade']:<13}"
            f" | pressenti: {pressentie:<13} | vers revelation: {p:.0%}")
