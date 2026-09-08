"""
Etat du paysage.

Remplace jardin.py, qui verrouillait la famille GLOBALEMENT au bout de 800
mots — c'est-a-dire exactement ce que la decision 5 interdit. La consequence
se reproduit en trois lignes (prose puis rapport structure) :

    445 mots -> Vegetal       (marge 0.009)
    498 mots -> Architecture  (marge 0.183)

Ce module implemente ce que jardin.py laissait de cote :

     3. le registre d'empreintes   deplacer / fusionner / copier / supprimer
     4. le collage                 ecriture, greffe, conversion
     5. le verrou par segment      800 mots ET 3 lectures espacees
     6. l'echelle                  un plant au Titre 1 ou a 2 500 mots
    11. le perimetre               le paysage appartient au dossier

Comme traits.py, ce fichier n'a aucune dependance externe : le portage vers
JavaScript doit rester mecanique.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field, asdict

from traits import (
    extraire, scores, en_mots, _sans_accent, _deplier, NOMS,
    MARGE_DOMINANCE, PALIER_INDICES, PALIER_DIVERGENCE,
)

VERSION_ETAT = 3
# La 3 ajoute le PROPRIETAIRE de chaque empreinte. La 2 se relit et se convertit
# — voir depuis(). Jeter un paysage parce qu'il vient d'une version d'avant
# serait la pire chose que ce fichier puisse faire.

# Une empreinte dont on ne sait pas a quel plant elle appartient : tout ce qui
# vient d'un etat de version 2, ou d'un rang qui ne designe plus rien.
RANG_INCONNU = -1

# --------------------------------------------------------------------------
# Constantes. Chacune a sa raison dans DECISIONS.md ; les changer sans lire
# l'entree correspondante casse quelque chose qui a ete paye cher.
# --------------------------------------------------------------------------
MOTS_PAR_PLANT = 2500          # decision 6 : au-dela, le retour se perd
# ⚠️ 2 500 ET NON 5 000. La premiere valeur a ete calibree sur une these et
# sur rien d'autre. Confrontee a un article de 8 000 mots — vingt pages — elle
# en faisait 1,6 plant : un germe et un arbre, pas un paysage.
#
# Ce qu'on a mesure avant de changer, sur une these entiere de 146 000 mots,
# en comptant paragraphe par paragraphe ce que le volet montrait :
#
#     mots/plant   part du temps en germe   plants   la these
#        5 000              18 %              32     lisible
#        2 500              33 %              59     lisible, plus dense
#        1 000              78 %             139     une trainee
#
# Le plancher n'est pas negociable : il faut 800 mots pour que le style d'une
# personne soit lisible, donc pour qu'un plant ait une famille. Plus le plant
# est petit, plus ces 800 mots en mangent la vie — a 1 000, la personne
# regarde une tache sans forme trois quarts du temps, et la vue d'ensemble
# cesse d'avoir des objets dedans.
#
# 2 500 est le point ou l'arbre de la premiere semaine est deux fois plus
# fourni qu'a 5 000 (extension 0,48 contre 0,24) sans que rien ne se perde.
# ⚠️ PARAGRAPHES_PAR_PLANT A ETE RETIRE. Il valait 52, calcule comme
# 5 000 / ~96 : ce n'etait pas une quantite independante mais le nombre de mots
# exprime dans une longueur de paragraphe SUPPOSEE. La decision 17 a fait de la
# LIGNE l'unite du paysage, et un vrai document a montre ce que la constante y
# devenait — trente-cinq pages ecrites en lignes d'une phrase, onze mots
# chacune, donc 52 lignes = 570 mots. Un plant tous les 1,6 page au lieu d'un
# tous les douze, et deux cent cinquante plants pour une these au lieu de
# vingt-neuf.
#
# Un plant se mesure donc en MOTS, et en mots seuls. La forme reflete ce qu'on a
# ecrit, pas la facon dont on ponctue.
MOTS_MINIMUM_VERROU = 800      # decision 5 : 32 % du plant, pas 0,58 % de la these
LECTURES_CONCORDANTES = 3
# Le verrou demande "3 lectures concordantes d'affilee". Espacees en MOTS, pas
# en ticks : jardin.py comptait des appels a mettre_a_jour, donc dans un add-in
# cadence a 2 s la garantie valait six secondes et ne garantissait rien.
MOTS_ENTRE_LECTURES = 100
SEUIL_COLLAGE = 15             # decision 4 : mots par intervalle de 2 s (450 mots/min)
HEURE_NUIT = (2, 5)            # decision 9 : la palette qui n'apparait nulle part ailleurs
MOTS_LISIBLES = 200            # en dessous, rien n'est lisible : c'est un germe
SATURATION_REPRISES = 3.0      # decision 2 : 1 - exp(-reprises/3)

STYLES_TITRE = {"titre 1", "heading 1", "titre1", "heading1"}
STYLES_IGNORES = {"citation", "quote", "intense quote", "citation intense"}


# --------------------------------------------------------------------------
# Empreintes (decision 3)
# --------------------------------------------------------------------------
# On plie la casse, les accents et les variantes typographiques du meme signe.
# Word remplace l'apostrophe droite par la courbe tout seul : sans ce pliage,
# une correction automatique ferait passer un paragraphe deja ecrit pour un
# paragraphe neuf, et la forme pousserait sans que personne n'ait ecrit.
_VARIANTES = str.maketrans({
    "’": "'", "‘": "'", "“": '"', "”": '"',
    "«": '"', "»": '"', "—": "-", "–": "-",
    " ": " ", "…": "...",
})
_ESPACES = re.compile(r"\s+")
_BORDS = re.compile(r"^[\s\W_]+|[\s\W_]+$")


def normaliser(paragraphe: str) -> str:
    # _deplier et non _sans_accent : un paragraphe ne se represente jamais deux
    # fois a l'identique, le mettre en cache ne fait que garder une copie du
    # document en memoire (voir le commentaire du cache dans traits.py).
    p = _deplier(paragraphe).lower().translate(_VARIANTES)
    return _ESPACES.sub(" ", _BORDS.sub("", p))


def empreinte(paragraphe: str) -> str:
    """
    6 octets, soit 12 caracteres hexadecimaux.

    1 450 paragraphes -> 17 Ko, et 59 Ko avec trois fois plus de reprises :
    c'est le chiffre annonce a la decision 3, et la raison de ne pas prendre
    un digest plus large.
    """
    return hashlib.blake2s(normaliser(paragraphe).encode("utf-8"),
                           digest_size=6).hexdigest()


# --------------------------------------------------------------------------
# Un plant
# --------------------------------------------------------------------------
@dataclass
class Segment:
    rang: int
    jour: int = 0                  # date de creation -> palette (decision 9)
    heure: int = 14
    titre: str = ""
    mots: int = 0                  # mots ECRITS ici (jamais les mots deplaces)
    nouveaux: int = 0              # paragraphes ecrits    -> extension
    reprises: int = 0              # retouches             -> maturite
    greffes: int = 0               # colles, en attente
    # Les VRAIES dates d'ecriture, ponderees par les mots : {jour: mots}.
    # Sans elles, le rendu doit inventer une date par tour de ville
    # (jour + rang x 47 en v4), et la ville affiche des saisons qui n'ont
    # jamais eu lieu — alors que la decision 9 fait porter la teinte par la
    # date d'ecriture. Une dizaine d'entiers par plant.
    jours: dict = field(default_factory=dict)
    mots_de_nuit: int = 0          # ecrits entre 2h et 5h
    textes: list[str] = field(default_factory=list)
    famille: str | None = None
    candidate: str | None = None
    confirmations: int = 0
    mots_derniere_lecture: int = 0
    scores_courants: dict = field(default_factory=dict)
    scores_au_verrouillage: dict = field(default_factory=dict)
    # Le vecteur de traits normalise, tel quel. C'est lui qui donne a chaque
    # plant sa physionomie propre : sans lui, tous les plants d'une meme
    # famille sont la meme figure au grain pres, et un paysage de vingt-sept
    # objets n'est plus que quatre formes repetees.
    traits_courants: dict = field(default_factory=dict)

    # -- les deux axes (decision 2) ----------------------------------------
    @property
    def extension(self) -> float:
        """
        Combien de segments : ca pousse.

        UNE SEULE MONNAIE, ET C'EST LE MOT. La version d'avant prenait le
        plus avance de deux comptes — les paragraphes rapportes a 52, les mots
        rapportes au plant — pour ne pas fermer la forme de quelqu'un qui ecrit
        des paragraphes de 250 mots avant qu'elle ait fini de pousser. Le
        remede etait bon tant que les deux nombres decrivaient la meme chose.

        Ils ont cesse de le faire. La decision 17 a fait de la LIGNE l'unite du
        paysage, et 52 supposait des paragraphes de 96 mots. Sur un vrai
        document ecrit en lignes d'une phrase — onze mots — un plant se
        remplissait en 570 mots, soit une page et demie au lieu de douze, et la
        famille n'etait meme pas encore lisible : la forme restait une tige a
        extension 1,00, puis devenait un arbre fini d'un seul coup, et ne
        bougeait plus jamais.

        Mesurer en mots seuls ne perd rien de ce que l'ancien remede defendait :
        le plant se ferme aussi en mots, donc l'extension vaut exactement 1 au
        moment ou il est plein, quelle que soit la longueur des lignes. Le
        compte de lignes n'a pas disparu du projet pour autant — c'est lui qui
        porte la maturite, en rapport reprises / paragraphes.
        """
        return min(1.0, self.mots / MOTS_PAR_PLANT)

    @property
    def maturite(self) -> float:
        """
        Ce que devient un segment deja la : ca murit.

        Sature vers 5-6 passages. Le rapport reprises/paragraphes est la
        variable juste : reprendre quarante fois UN paragraphe et reprendre
        une fois quarante paragraphes ne sont pas le meme geste.
        """
        if not self.nouveaux:
            return 0.0
        return 1.0 - math.exp(-(self.reprises / self.nouveaux) / SATURATION_REPRISES)

    def dater(self, jour: int, heure: int, mots: int):
        """Enregistre quand ces mots ont ete ecrits."""
        if mots <= 0:
            return
        j = jour % 365
        self.jours[j] = self.jours.get(j, 0) + mots
        if HEURE_NUIT[0] <= heure < HEURE_NUIT[1]:
            self.mots_de_nuit += mots

    def dates(self) -> list:
        """[(jour, poids)] tries : la vraie dispersion des dates du plant."""
        if not self.jours:
            return [(self.jour % 365, 1)]
        return sorted(self.jours.items())

    @property
    def nuit(self) -> bool:
        """
        Le plant prend la palette de nuit si l'essentiel de son texte a ete
        ecrit entre 2h et 5h. La decision 9 parle des SEGMENTS ecrits la nuit,
        pas des traits : une seule session a 3h ne doit pas semer du violet
        dans un plant de jour, sinon l'easter egg devient un bruit de fond.
        """
        return self.mots > 0 and self.mots_de_nuit / self.mots > 0.5

    @property
    def plein(self) -> bool:
        return self.mots >= MOTS_PAR_PLANT

    @property
    def verrouille(self) -> bool:
        return self.famille is not None

    # -- verrou (decision 5) -----------------------------------------------
    def relire(self) -> bool:
        """
        Une lecture, si le segment a gagne assez de mots depuis la derniere.

        Renvoie True si une lecture a eu lieu. Apres verrou les lectures
        continuent : elles ne mesurent plus que la derive.
        """
        if self.mots - self.mots_derniere_lecture < MOTS_ENTRE_LECTURES:
            return False
        self.mots_derniere_lecture = self.mots

        t = extraire("\n\n".join(self.textes))
        if not t.mots:
            return False
        s = scores(t)
        self.scores_courants = s
        self.traits_courants = {k: v for k, v in asdict(t).items()
                                if isinstance(v, float)}

        classement = sorted(s.items(), key=lambda kv: kv[1], reverse=True)
        pressentie = classement[0][0]
        marge = classement[0][1] - classement[1][1]
        if marge < MARGE_DOMINANCE and pressentie != "abstrait":
            pressentie = "abstrait"          # refus de classement

        if self.verrouille:
            return True

        if pressentie == self.candidate:
            self.confirmations += 1
        else:
            self.candidate = pressentie
            self.confirmations = 1

        if (self.mots >= MOTS_MINIMUM_VERROU
                and self.confirmations >= LECTURES_CONCORDANTES):
            self.famille = pressentie
            self.scores_au_verrouillage = dict(s)
        return True

    def influences(self) -> dict[str, float]:
        """Derive depuis le verrouillage : ce qui produit les traits hybrides."""
        if not self.verrouille or not self.scores_courants:
            return {}
        sortie = {}
        for nom, valeur in self.scores_courants.items():
            if nom == self.famille:
                continue
            derive = valeur - self.scores_au_verrouillage.get(nom, valeur)
            if derive > 0.02:
                sortie[nom] = round(min(1.0, derive * 2.5), 3)
        return sortie

    def stade(self) -> str:
        if self.verrouille:
            return "croissance"
        return "germe" if self.mots < MOTS_LISIBLES else "indices"


# --------------------------------------------------------------------------
# Le paysage
# --------------------------------------------------------------------------
@dataclass
class Paysage:
    """
    Le paysage appartient au DOSSIER (decision 11).

    L'identifiant est tire une fois et recopie dans les Settings de chaque
    document du dossier. C'est lui qui fait autorite, pas le nom du dossier :
    deux theses rangees dans deux dossiers nommes "Chapitres" partageraient
    sinon le meme paysage. Le nom du dossier ne sert plus qu'a rattacher un
    document neuf a un paysage existant.
    """
    identifiant: str = ""
    cle_dossier: str = ""
    # ⚠️ UNE TABLE, PAS UN ENSEMBLE : empreinte -> rang du plant qui la porte.
    #
    # C'etait un ensemble, et retoucher() creditait donc la reprise au plant
    # COURANT, seul plant qu'il savait nommer. Retravailler le chapitre 1
    # faisait murir le chapitre 8, et le chapitre 1 ne murissait jamais : un
    # plant achevé voyait sa maturite gelee pour toujours, quoi qu'on
    # retravaille dedans. La moitie du travail d'une these — la reecriture —
    # etait donc invisible, et attribuee a l'endroit ou l'on se trouvait.
    #
    # La cause etait dans la persistance : serialiser() exclut les textes, donc
    # a la reouverture aucun plant ne sait plus ce qu'il contient. Le registre
    # gardait toutes les empreintes mais pas a qui elles appartenaient. Il les
    # garde maintenant : trois octets de plus par paragraphe, environ 7 Ko sur
    # une these de 2 400 paragraphes.
    registre: dict = field(default_factory=dict)
    segments: list = field(default_factory=list)
    version: int = VERSION_ETAT

    # Le curseur. Etat de session, jamais serialise : a la reouverture, plus
    # rien n'est en construction, ce qui est exact.
    #
    # Il resout un manque de la decision 2. Dans Word, ecrire un paragraphe
    # pour la premiere fois et y revenir trois jours plus tard produisent la
    # MEME suite d'evenements : onParagraphChanged, N fois. Lire ces
    # changements comme des reprises, c'est une premiere redaction qui ne fait
    # jamais pousser la forme ; les lire comme de l'ecriture, c'est rouvrir
    # l'exploit que la decision 2 ferme — allonger un paragraphe indefiniment
    # ferait grandir la plante.
    #
    # La separation juste n'est pas dans le texte, elle est dans le curseur :
    # un paragraphe est en construction tant qu'on ne l'a pas quitte. Une fois
    # quitte, il est ecrit ; y revenir est une reprise, et une seule par
    # visite — sinon dix minutes de reecriture compteraient trois cents
    # passages la ou la decision 2 en attend cinq ou six.
    _actif: str = ""
    _mode: str = ""          # "frappe" ou "reprise"
    # Le rang du plant qui a change en dernier, quel que soit l'axe : ecrire
    # designe le plant courant, retoucher designe celui qui porte le texte.
    # C'est lui que le volet cadre — sinon retravailler un vieux chapitre fait
    # murir un plant qu'on ne regarde pas. Etat de session, jamais serialise :
    # a la reouverture, rien n'a encore change.
    _touche: int = RANG_INCONNU

    # ---------------------------------------------------------------- plants
    def _plant(self, jour: int, heure: int) -> Segment:
        if not self.segments:
            self.segments.append(Segment(rang=0, jour=jour, heure=heure))
        return self.segments[-1]

    def _segment_de(self, e: str):
        """
        Le plant qui porte cette empreinte, ou None.

        None couvre deux cas qu'il ne faut pas confondre avec une panne : une
        empreinte inconnue, et une empreinte venue d'un etat de version 2, ou
        le proprietaire n'etait pas enregistre. Dans les deux cas l'appelant
        retombe sur le plant courant, c'est-a-dire sur le comportement d'avant.
        """
        rang = self.registre.get(e, RANG_INCONNU)
        if 0 <= rang < len(self.segments):
            return self.segments[rang]
        return None

    def _nouveau_plant(self, jour: int, heure: int, titre: str = "") -> Segment:
        # Un plant ouvert par debordement (2 500 mots) appartient encore au
        # chapitre en cours : il herite de la parcelle. Sans cet heritage, la
        # hierarchie du point 6 — paysage, parcelles, plants — n'existe que
        # pour les plants ouverts par un Titre 1, c'est-a-dire un sur trois.
        if not titre and self.segments:
            titre = self.segments[-1].titre
        s = Segment(rang=len(self.segments), jour=jour, heure=heure, titre=titre)
        self.segments.append(s)
        return s

    # --------------------------------------------------------------- collage
    def absorber(self, texte: str, style: str = "Normal",
                 mots_par_intervalle: int = 0, jour: int = 0,
                 heure: int = 14, naissance: bool = False) -> str:
        """
        Un paragraphe arrive. Ordre de verification strict (decision 4) :

            1. empreinte deja connue          -> rien
            2. inconnue + arrivee progressive -> ecriture
            3. inconnue + arrivee instantanee -> greffe
            4. greffe ensuite retouchee       -> ecriture   (voir retoucher)

        Le registre passe AVANT le test de vitesse : sinon la fusion de douze
        chapitres dans le document maitre est lue comme un collage geant.
        """
        st = _sans_accent(style or "").lower().strip()

        # Filtre gratuit : une citation ne compte jamais.
        if st in STYLES_IGNORES:
            return "ignoree"

        # Un paragraphe SANS MOTS n'est pas encore un paragraphe.
        #
        # Word en cree un a chaque retour a la ligne, avant qu'on ait tape quoi
        # que ce soit. Sans ce filtre, l'empreinte du vide entre au registre au
        # premier Entree — et tous les retours a la ligne suivants sont lus
        # comme « connue », donc le plant CESSE DE POUSSER au deuxieme
        # paragraphe. Personne ne s'en apercevrait avant d'ecrire dans le vrai
        # Word, parce que le corpus n'emet jamais de paragraphe vide.
        #
        # rattacher() filtrait deja le vide ; absorber() ne le faisait pas. Les
        # deux portes d'entree doivent dire la meme chose.
        if not en_mots(texte):
            return "vide"

        e = empreinte(texte)

        # 1. Connue : rien. Ni croissance, ni mots, ni traits, ET PAS DE PLANT
        #    NEUF meme sur un Titre 1 — sans quoi le scan complet a l'ouverture
        #    (decision 11) rouvrirait un plant a chaque titre deja connu, a
        #    chaque ouverture du fichier. Le registre passe avant tout le reste.
        #    C'est ce qui rend un deplacement, une fusion et une suppression
        #    gratuits.
        #    `naissance` est l'exception, et elle a une raison precise. Un
        #    paragraphe qu'on TAPE passe par tous ses etats intermediaires, et
        #    chacun entre au registre. Or « Il faut donc admettre » a toutes
        #    les chances d'avoir deja commence un autre paragraphe : en
        #    francais, un paragraphe sur deux debute par les memes quatre mots.
        #    Le registre declarait alors « connue » un paragraphe genuinement
        #    neuf, et LE PLANT CESSAIT DE POUSSER — sans rien signaler.
        #
        #    Quand l'appelant a VU le paragraphe naitre vide sous le curseur,
        #    il sait ce que le registre ne peut pas savoir. La reconnaissance
        #    existe pour rendre un DEPLACEMENT gratuit, pas pour nier une
        #    frappe.
        if e in self.registre and not naissance:
            return "connue"

        # Un Titre 1 ouvre un plant (decision 6) — sauf si le plant courant
        # vient tout juste de naitre. Quand un chapitre commence peu apres
        # qu'un plant s'est rempli, ouvrir quand meme laisse derriere soi un
        # moignon de quelques dizaines de mots, qui n'atteindra jamais les 800
        # mots du verrou et restera un germe pour toujours. Sur une these on
        # en compte un par frontiere malheureuse. En dessous du seuil de
        # lisibilite, le titre reprend le plant en cours au lieu d'en ouvrir
        # un neuf.
        if st in STYLES_TITRE:
            courant = self.segments[-1] if self.segments else None
            if courant is not None and courant.mots < MOTS_LISIBLES:
                courant.titre = texte.strip()
            else:
                self._nouveau_plant(jour, heure, titre=texte.strip())

        plant = self._plant(jour, heure)
        if plant.plein:
            plant = self._nouveau_plant(jour, heure)

        self.registre[e] = plant.rang
        self._touche = plant.rang

        # 3. Inconnue et arrivee d'un bloc : greffe, en attente.
        if mots_par_intervalle > SEUIL_COLLAGE:
            plant.greffes += 1
            plant.textes.append(texte)
            return "greffe"

        # 2. Inconnue et arrivee progressive : ca pousse.
        plant.nouveaux += 1
        n = len(en_mots(texte))
        plant.mots += n
        plant.dater(jour, heure, n)
        plant.textes.append(texte)
        self._actif, self._mode = e, "frappe"
        plant.relire()
        return "ecriture"

    def quitter(self):
        """
        Le curseur sort du paragraphe. Dans l'add-in : changement de selection,
        sauvegarde, fermeture. A partir de la, le paragraphe est ecrit — y
        revenir sera une reprise.
        """
        self._actif, self._mode = "", ""

    def retoucher(self, ancien: str, nouveau: str, jour: int = 0,
                  heure: int = 14, etait_greffe: bool = False,
                  mots_par_intervalle: float = 0) -> str:
        """
        Un paragraphe deja present change : c'est de la MATURITE, pas de
        l'extension. C'est la decision centrale du projet — reprendre quarante
        fois la meme phrase produit un element somptueux sur une forme qui n'a
        pas grandi, et tripoter ne peut donc pas simuler de la croissance.

        Une greffe retouchee se convertit en ecriture : une citation ne se
        retouche jamais, un brouillon rapporte d'ailleurs se retravaille
        toujours. Le cas se resout seul, sans rien demander a personne.

        ⚠️ LE DEBIT EST ARRIVE TARD, ET IL MANQUAIT. La decision 4 ne gardait
        qu'absorber() : coller dans la ligne qu'on est EN TRAIN d'ecrire
        ajoutait tous les mots colles en extension, sans le moindre controle.
        C'est le trou par lequel un vrai document est passe d'une tige a un
        arbre entier en trois collages, dans le premier Word ou l'add-in ait
        jamais tourne. Le chemin des evenements avait exactement le meme.

        La meme arrivee ne peut pas compter differemment selon qu'elle tombe
        dans une ligne neuve ou dans une ligne en cours.
        """
        e = empreinte(nouveau)
        if empreinte(ancien) == e:
            return "inchangee"

        vieille = empreinte(ancien)
        # ⚠️ LE PLANT QUI PORTE LE TEXTE, PAS LE PLANT COURANT.
        #
        # C'etait self._plant(), donc toujours le dernier. Retravailler un
        # paragraphe du chapitre 1 creditait la reprise au chapitre en cours :
        # le chapitre 1 ne murissait jamais, et le plant courant murissait d'un
        # travail fait sur du texte qu'il ne contient pas. Mesure sur un
        # paysage de cent vingt-trois plants : cinq retouches sur un paragraphe
        # du plant 0 donnaient plant 0 maturite 0,000 et plant 122 maturite
        # 0,076.
        #
        # Un plant inconnu — empreinte jamais vue, ou etat de version 2 ou le
        # proprietaire n'etait pas garde — retombe sur le plant courant, ce qui
        # est exactement le comportement d'avant.
        plant = self._segment_de(vieille) or self._plant(jour, heure)
        # La nouvelle version appartient au meme plant : un paragraphe qu'on
        # retravaille ne change pas de chapitre.
        self.registre[e] = plant.rang
        self._touche = plant.rang
        for i, t in enumerate(plant.textes):
            if empreinte(t) == vieille:
                plant.textes[i] = nouveau
                break

        if etait_greffe:
            plant.greffes = max(0, plant.greffes - 1)
            plant.nouveaux += 1
            n = len(en_mots(nouveau))
            plant.mots += n
            plant.dater(jour, heure, n)
            self._actif, self._mode = e, "frappe"
            plant.relire()
            return "conversion"

        if vieille == self._actif and self._mode == "frappe":
            # Meme visite, premiere redaction : c'est encore de l'ecriture —
            # SAUF si ca arrive d'un bloc, auquel cas c'est une greffe, comme
            # dans absorber(). Les mots ne comptent pas, et la ligne est
            # marquee pour que la retravailler la convertisse plus tard.
            #
            # Une imprecision assumee : la conversion recomptera la ligne
            # ENTIERE, y compris les mots deja comptes avant le collage. Le
            # depassement est borne par ce qu'on avait ecrit soi-meme, et le
            # point 1 interdit de reculer — on prefere compter un peu deux fois
            # que de retrancher quoi que ce soit.
            if mots_par_intervalle > SEUIL_COLLAGE:
                plant.greffes += 1
                self._actif = e
                return "greffe"
            # Les mots comptent, aucune reprise n'est enregistree.
            ajout = max(0, len(en_mots(nouveau)) - len(en_mots(ancien)))
            plant.mots += ajout
            plant.dater(jour, heure, ajout)
            self._actif = e
            plant.relire()
            return "frappe"

        if vieille == self._actif and self._mode == "reprise":
            # Meme visite, deja comptee. On suit le texte sans rien ajouter.
            self._actif = e
            plant.relire()
            return "reprise en cours"

        # Nouvelle visite sur un paragraphe deja ecrit : une reprise, une seule.
        # Les mots ajoutes NE COMPTENT PAS dans l'extension — sinon rallonger
        # sans fin le meme paragraphe ferait pousser la forme, et tripoter
        # redeviendrait un moyen de simuler de la croissance.
        plant.reprises += 1
        self._actif, self._mode = e, "reprise"
        plant.relire()
        return "reprise"

    # ------------------------------------------------------------- ouverture
    def rattacher(self, paragraphes: list, jour: int = 0, heure: int = 14):
        """
        Rattachement initial : tout ce qui est deja la est acquis comme capital
        de depart (decision 11). Personne n'a a recommencer sa these pour que
        le cadeau ait un sens.

        Accepte des chaines ou des couples (texte, style) : les Titre 1 du
        document existant decoupent deja le paysage en parcelles.
        """
        for item in paragraphes:
            # tuple OU liste : un couple reste un couple apres un aller-retour
            # par du JSON, qui n'a que des tableaux. Le refuser faisait recevoir
            # la liste comme une chaine, et « ['texte', 'Titre 1'] » n'a pas de
            # methode strip.
            couple = isinstance(item, (tuple, list))
            p, style = item if couple else (item, "Normal")
            if not p.strip():
                continue
            st = _sans_accent(style or "").lower().strip()
            if st in STYLES_IGNORES:
                continue
            e = empreinte(p)
            if e in self.registre:
                continue
            if st in STYLES_TITRE:
                self._nouveau_plant(jour, heure, titre=p.strip())
            plant = self._plant(jour, heure)
            if plant.plein:
                plant = self._nouveau_plant(jour, heure)
            # ⚠️ APRES avoir resolu le plant, pas avant : c'est son rang qu'on
            # enregistre, et le Titre 1 vient peut-etre d'en ouvrir un neuf.
            self.registre[e] = plant.rang
            plant.nouveaux += 1
            n = len(en_mots(p))
            plant.mots += n
            plant.dater(jour, heure, n)
            plant.textes.append(p)
            plant.relire()

    # ----------------------------------------------------------------- rendu
    def etat(self) -> dict:
        return {
            "identifiant": self.identifiant,
            "plants": [
                {
                    "rang": s.rang,
                    "famille": s.famille,
                    "pressentie": None if s.verrouille else s.candidate,
                    "stade": s.stade(),
                    "mots": s.mots,
                    "extension": round(s.extension, 3),
                    "maturite": round(s.maturite, 3),
                    "greffes": s.greffes,
                    "dates": s.dates(),
                    "nuit": s.nuit,
                    "titre": s.titre,
                    "traits": dict(s.traits_courants),
                    # De quoi dessiner un plant qui n'a pas encore de famille.
                    "germe": None if s.verrouille else {
                        "taille": min(1.0, s.mots / PALIER_DIVERGENCE),
                        "inflexion": max(0.0, min(1.0,
                            (s.mots - PALIER_INDICES)
                            / max(PALIER_DIVERGENCE - PALIER_INDICES, 1))),
                    },
                    "influences": s.influences(),
                    # Le plant que le volet doit cadrer : celui qui vient de
                    # changer, par l'un ou l'autre axe.
                    "actif": s.rang == self._rang_actif(),
                }
                for s in self.segments
            ],
            "mots": sum(s.mots for s in self.segments),
            "empreintes": len(self.registre),
        }

    def _rang_actif(self) -> int:
        """
        Le plant que le volet cadre.

        Celui qui a change en dernier — ecrire designe le plant courant,
        retoucher celui qui porte le texte. Tant que rien n'a change, c'est le
        dernier plant VIVANT : a la reouverture d'un document, on regarde ou on
        en etait, pas un moignon invisible.
        """
        if 0 <= self._touche < len(self.segments):
            return self._touche
        for s in reversed(self.segments):
            if s.famille or s.mots:
                return s.rang
        return len(self.segments) - 1

    # ----------------------------------------------------------- persistance
    def serialiser(self) -> str:
        return json.dumps({
            "version": self.version,
            "identifiant": self.identifiant,
            "cle_dossier": self.cle_dossier,
            # « empreinte:rang ». Trie, pour qu'un meme paysage donne toujours
            # le meme texte — sans quoi la copie dans le .docx repartirait a
            # chaque tic (decision 16) et le fichier serait marque modifie.
            # ⚠️ LE PLANT TOUCHE SE GARDE, contrairement au curseur (_actif,
            # _mode) qui lui ne se serialise pas. Les deux ne disent pas la
            # meme chose : le curseur dit « ce paragraphe est en construction »,
            # ce qui est faux des qu'on ferme le document ; le plant touche dit
            # « c'est la qu'on travaillait », ce qui reste vrai. Rouvrir son
            # document et retrouver la camera sur le chapitre qu'on revisait
            # vaut mieux que la voir sauter a la fin.
            "touche": self._touche,
            "registre": sorted(f"{e}:{r}" for e, r in self.registre.items()),
            "segments": [
                {k: v for k, v in s.__dict__.items() if k != "textes"}
                for s in self.segments
            ],
        }, ensure_ascii=False)

    @classmethod
    def depuis(cls, brut) -> "Paysage":
        if not brut:
            return cls()
        try:
            d = json.loads(brut)
        except (json.JSONDecodeError, TypeError):
            return cls()
        # isinstance et pas seulement .get : "[]" et "null" sont du JSON
        # parfaitement valide, et une liste n'a pas de methode get. Un reglage
        # tronque ou ecrase dans les Settings de Word faisait donc lever ici,
        # au chargement, la ou il n'y a personne pour rattraper — le volet
        # serait reste noir. Un paysage illisible repart vide, jamais en erreur.
        version = d.get("version") if isinstance(d, dict) else None
        if not isinstance(d, dict) or not isinstance(version, int) \
                or not 2 <= version <= VERSION_ETAT:
            return cls()

        # ⚠️ ON CONVERTIT, ON NE JETTE PAS. Un paysage de version 2 est un
        # paysage de trois ans de these : le refuser parce qu'il lui manque le
        # proprietaire des empreintes serait la pire chose que ce fichier
        # puisse faire. Ses empreintes gardent RANG_INCONNU, ce qui rend a
        # celles-la — et a celles-la seules — le comportement d'avant : une
        # retouche credite le plant courant. Tout ce qui s'ecrit ensuite est
        # correctement attribue.
        registre = {}
        for entree in d.get("registre", []):
            if not isinstance(entree, str):
                continue
            e, sep, rang = entree.rpartition(":")
            if sep and rang.lstrip("-").isdigit():
                registre[e] = int(rang)
            else:
                registre[entree] = RANG_INCONNU

        p = cls(identifiant=d.get("identifiant", ""),
                cle_dossier=d.get("cle_dossier", ""),
                registre=registre)
        touche = d.get("touche", RANG_INCONNU)
        p._touche = touche if isinstance(touche, int) else RANG_INCONNU
        for brut_s in d.get("segments", []):
            brut_s["jours"] = {int(k): v for k, v in brut_s.get("jours", {}).items()}
            p.segments.append(Segment(**brut_s))
        return p


def resume(paysage: Paysage) -> str:
    lignes = []
    for s in paysage.segments:
        if s.verrouille:
            infl = ", ".join(f"{NOMS[k]} +{v:.2f}" for k, v in
                             sorted(s.influences().items(), key=lambda kv: -kv[1])[:2])
            etat = f"{NOMS[s.famille].upper():<13} verrouille"
        else:
            pressentie = NOMS[s.candidate] if s.candidate else "-"
            etat = f"{s.stade():<13} ({pressentie})"
            infl = ""
        lignes.append(f"  plant {s.rang:>2} | {s.mots:>5} mots | {etat}"
                      f" | ext {s.extension:.2f} mat {s.maturite:.2f}"
                      f"{' | ' + infl if infl else ''}")
    return "\n".join(lignes)
