# -*- coding: utf-8 -*-
"""Le guet : lire ce qui a change en comparant deux instantanes.

POURQUOI CE MODULE EXISTE

Word ne previent pas toujours. Les evenements de paragraphe demandent WordApi
1.6, et la machine a qui ce cadeau est destine est un Office LTSC 2021, gele a
sa version de sortie : elle ne les aura jamais. Le point ouvert 15 le mesure.

Il reste a regarder. Mesure sur cette machine : relire le document objet par
objet coute ~1,7 ms PAR PARAGRAPHE — deux secondes et demie sur une these, soit
vingt-cinq fois le budget d'un tic. Mais le corps entier rendu en UNE chaine
coute 17 a 21 ms quelle que soit sa taille, parce qu'aucun objet intermediaire
n'est fabrique. On prend donc un instantane du texte, et on le compare au
precedent.

CE QUE CA REGLE EN PLUS, ET QUI VAUT MIEUX QUE LE DEPANNAGE

Le premier vrai document ouvert avec le volet faisait trente-cinq pages et UN
SEUL paragraphe : 0 marque de paragraphe, 1119 sauts de ligne. Son auteur allait
a la ligne sans en creer une — ce qu'on fait pour eviter l'espacement. Le
paysage y aurait vu une empreinte pour 74 000 signes, aucune extension jamais,
et la plante n'aurait pas pousse d'un millimetre sans que rien ne le dise.

L'unite qui compte est celle que la personne fabrique en ecrivant, pas celle que
Word enregistre. Le guet decoupe donc sur TOUS les separateurs de ligne, et
retrouve ce qu'elle a ecrit quelle que soit la touche employee.
"""

# Word joint ses paragraphes par un retour chariot dans body.text, et ses sauts
# de ligne (Maj+Entree) par une tabulation verticale. Elle s'ecrit \x0b en
# toutes lettres et jamais en clair : un caractere de controle dans une source
# est invisible en relecture, et ne survit pas au premier copier-coller — la
# panne a ete faite deux fois avant d'etre ecrite ici.
SEPARATEURS = ("\r", "\x0b", "\n")

# Combien de releves sans un changement avant qu'une visite soit close.
#
# LE CURSEUR EST MORT AVEC CE DOCUMENT. Sous les evenements, quitter() partait
# quand la selection changeait de paragraphe. Le guet ne peut plus le savoir :
# sur un document ou tout tient en un paragraphe, getSelection().paragraphs rend
# les trente-cinq pages, et aucune ligne ne s'en deduit.
#
# Il faut donc fermer la visite autrement. Deux choses avant de choisir un
# nombre, et elles reduisent beaucoup l'enjeu :
#
#   - CHANGER DE LIGNE FERME DEJA LA VISITE, sans rien ajouter. _actif n'a
#     qu'une case : ecrire ailleurs la deplace, et revenir tombe forcement dans
#     la branche « reprise ». Le guet n'a rien a faire pour ca ;
#   - TRIPOTER NE POUSSE PAS, meme dans une visite ouverte. La branche frappe
#     compte max(0, mots(nouveau) - mots(ancien)) : reecrire quarante fois la
#     meme phrase sans l'allonger ajoute zero.
#
# Ce que ce silence protege n'est donc pas l'extension, c'est LA MATURITE. Sans
# lui, revenir sur une ligne une semaine plus tard reste la meme visite,
# plant.reprises ne monte jamais, et l'element cesse de murir — l'autre axe
# meurt sans rien dire.
#
# Trop court, une pause pour reflechir devient une reprise, chaque continuation
# cesse de compter en extension, et la forme ne pousse plus ; trop long, plus
# rien ne murit. Cette constante arbitre l'equilibre des deux axes du projet et
# ne se choisit pas au gout.
#
# LA BORNE BASSE EST MESUREE, sur la machine cible et sur du vrai texte. Le
# guet a compte 27 changements sur 47 releves en ecriture active (57 %), et 33
# sur 139 en frappe distraite (24 %). Les trous de deux a quatre releves sont
# donc ordinaires, et une suite de soixante releves calmes ne peut pas arriver
# pendant qu'on ecrit. Le decoupage abusif est exclu.
#
# ⚠️ LA BORNE HAUTE, ELLE, RESTE UN JUGEMENT. Soixante releves font deux
# minutes : assez pour traverser une pause de reflexion, pas pour traverser un
# cafe. C'est defendable, ce n'est pas mesure — a confirmer au banc, en
# regardant comment les deux axes repondent quand on fait varier ce nombre.
SILENCE = 60


def decouper(texte):
    """Le texte du corps, rendu en lignes.

    Toutes les separations valent : celle qui vient d'Entree comme celle qui
    vient de Maj+Entree. C'est le point 14 — le paysage compte ce que la
    personne fabrique, pas ce que Word enregistre.
    """
    if not texte:
        return []
    lignes = [texte]
    for s in SEPARATEURS:
        suivantes = []
        for morceau in lignes:
            suivantes.extend(morceau.split(s))
        lignes = suivantes
    return lignes


def rapprocher(anciennes, nouvelles):
    """Ce qui a bouge entre deux instantanes.

    Rend une liste de mouvements, dans l'ordre du nouvel instantane :

        ("gardee",      i, j)   la ligne i est devenue la ligne j, texte egal
        ("retouchee",   i, j)   la ligne i est devenue la ligne j, texte change
        ("nee",       None, j)  la ligne j n'existait pas
        ("disparue",    i, None) la ligne i n'existe plus

    LA METHODE : ROGNER LES BOUTS.

    Ecrire ne change qu'une region locale. On retire donc la tete et la queue
    identiques, et il ne reste presque toujours qu'une ou deux lignes a
    reconcilier.

    ⚠️ C'EST CE ROGNAGE QUI PROTEGE L'INVARIANT CARDINAL. Identifier les lignes
    par leur RANG serait la faute a ne pas commettre : inserer une ligne au
    milieu decalerait toutes les suivantes, le miroir les verrait toutes
    changer, et une insertion se lirait comme une pluie de retouches — de
    l'extension prise pour de la maturite, l'erreur centrale du projet. Apres
    rognage, une insertion laisse une fenetre VIDE du cote ancien : elle ne peut
    donc pas se confondre avec une retouche.

    DANS LA FENETRE, LES LIGNES IDENTIQUES SE RECONNAISSENT D'ABORD.

    Un deplacement est gratuit (point 3), et l'appariement par rang en aurait
    fait des retouches : echanger deux lignes aurait invente de la maturite sans
    que personne n'ait rien recrit. On apparie donc d'abord ce qui est egal, et
    la ligne deplacee garde son identifiant sans rendre le moindre verdict.

    CE QUI RESTE S'APPARIE PAR RANG, et c'est assume.

    Ce n'est exact que si le reste se correspond une a une. Taper une ligne
    neuve ET en retoucher une autre dans le meme intervalle de deux secondes
    donnerait un appariement de travers — une retouche declaree sur la mauvaise
    ligne, et une naissance sur l'autre. La fenetre est minuscule, deux secondes
    de frappe, et le registre absorbe le reste : un texte deja connu ne fait
    rien pousser. Le cout d'une erreur est donc un verdict de travers, jamais
    une pousse inventee.
    """
    a, b = len(anciennes), len(nouvelles)

    tete = 0
    while tete < a and tete < b and anciennes[tete] == nouvelles[tete]:
        tete += 1

    queue = 0
    while (queue < a - tete and queue < b - tete
           and anciennes[a - 1 - queue] == nouvelles[b - 1 - queue]):
        queue += 1

    fenetre_a = list(range(tete, a - queue))
    fenetre_b = list(range(tete, b - queue))

    # 1. Les lignes egales, ou qu'elles soient dans la fenetre : deplacees.
    par_texte = {}
    for i in fenetre_a:
        par_texte.setdefault(anciennes[i], []).append(i)
    deplacees = {}                       # j -> i
    pris = set()
    for j in fenetre_b:
        libres = par_texte.get(nouvelles[j])
        while libres:
            i = libres.pop(0)
            if i not in pris:
                deplacees[j] = i
                pris.add(i)
                break

    # 2. Le reste, par rang.
    restants_a = [i for i in fenetre_a if i not in pris]
    restants_b = [j for j in fenetre_b if j not in deplacees]
    couples = {}                         # j -> i
    for i, j in zip(restants_a, restants_b):
        couples[j] = i
    disparues = restants_a[len(restants_b):]

    mouvements = []
    for k in range(tete):
        mouvements.append(("gardee", k, k))
    for j in fenetre_b:
        if j in deplacees:
            mouvements.append(("gardee", deplacees[j], j))
        elif j in couples:
            mouvements.append(("retouchee", couples[j], j))
        else:
            mouvements.append(("nee", None, j))
    for k in range(queue):
        mouvements.append(("gardee", a - queue + k, b - queue + k))
    for i in disparues:
        mouvements.append(("disparue", i, None))

    return mouvements


class Guet:
    """Tient l'instantane precedent et les identifiants qui vont avec.

    LES IDENTIFIANTS SONT FABRIQUES ICI, et c'est ce qui permet au pont de ne
    pas changer d'une ligne. Sur ses vingt usages d'identifiant, tous sont des
    cles de dictionnaire ou une egalite : il n'en lit jamais la forme. Un
    identifiant du guet vaut donc un uniqueLocalId de Word, pourvu qu'il reste
    stable tant que la ligne existe — ce dont le rapprochement se charge.
    """

    def __init__(self, silence=SILENCE):
        self.lignes = []        # le dernier instantane
        self.ids = []           # un identifiant par ligne, meme longueur
        self._suivant = 0
        # La visite en cours : la derniere ligne qui a bouge, et depuis combien
        # de releves elle ne bouge plus. Voir SILENCE.
        self.silence = silence
        self.visitee = None
        self.calme = 0

    def _neuf(self):
        self._suivant += 1
        return "g%d" % self._suivant

    def amorcer(self, texte):
        """Le premier instantane, qui ne fait RIEN pousser.

        Decision 11 : ce qui est deja la est un capital de depart, pas une
        pousse. Sans ce depart separe, ouvrir le volet sur une these de mille
        cinq cents lignes les declarerait toutes NEES d'un coup — le pire
        contresens que le paysage puisse commettre, et exactement ce que
        rattacher() existe pour eviter.

        Rend les lignes, pour que l'appelant les donne a rattacher().
        """
        self.lignes = decouper(texte)
        self.ids = [self._neuf() for _ in self.lignes]
        return list(self.lignes)

    def relever(self, texte):
        """Compare le corps a ce qu'on avait vu, et rend ce qui a bouge.

        Rend une liste de faits, prets pour le pont :

            {"type": "nee" | "retouchee" | "disparue",
             "id": ..., "texte": ..., "ancien": ...}

        Les lignes gardees ne rendent rien, et c'est tout l'interet : sur une
        these de mille cinq cents lignes, un tic n'en signale qu'une ou deux.
        """
        nouvelles = decouper(texte)
        mouvements = rapprocher(self.lignes, nouvelles)

        ids = [None] * len(nouvelles)
        faits = []
        for genre, i, j in mouvements:
            if genre == "gardee":
                ids[j] = self.ids[i]
            elif genre == "retouchee":
                ids[j] = self.ids[i]
                faits.append({"type": "retouchee", "id": self.ids[i],
                              "texte": nouvelles[j], "ancien": self.lignes[i]})
            elif genre == "nee":
                ids[j] = self._neuf()
                faits.append({"type": "nee", "id": ids[j],
                              "texte": nouvelles[j], "ancien": None})
            else:
                faits.append({"type": "disparue", "id": self.ids[i],
                              "texte": None, "ancien": self.lignes[i]})

        self.lignes = nouvelles
        self.ids = ids

        # La visite. Elle se ferme d'elle-meme quand on ecrit ailleurs — _actif
        # n'a qu'une case — donc il ne reste ici qu'a fermer celle qu'on a
        # ABANDONNEE sans rien toucher d'autre. Sans ca, plant.reprises ne
        # monterait plus jamais et l'element cesserait de murir.
        remuees = [f["id"] for f in faits if f["type"] != "disparue"]
        if remuees:
            self.visitee = remuees[-1]
            self.calme = 0
        elif self.visitee is not None:
            self.calme += 1
            if self.calme >= self.silence:
                faits.append({"type": "visite_finie", "id": self.visitee,
                              "texte": None, "ancien": None})
                self.visitee = None
                self.calme = 0

        return faits
