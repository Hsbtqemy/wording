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
#
# LES DEUX NIVEAUX SONT DISTINGUES, et ce n'est pas de la coquetterie : le style
# appartient au PARAGRAPHE. Decouper d'abord sur le retour chariot donne les
# paragraphes de Word, donc l'echelle a laquelle les styles se lisent ; decouper
# ensuite chaque paragraphe donne les lignes de la personne, qui est l'unite du
# paysage (point 14). Une ligne herite du style de son paragraphe, exactement.
SEPARATEUR_PARAGRAPHE = "\r"
SEPARATEURS_LIGNE = ("\x0b", "\n")

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

# Combien de temps entre deux releves (decision 12). Le pont a la meme, pour le
# chemin des evenements ; elle est redite ici parce que le guet doit pouvoir se
# specifier sans lui.
INTERVALLE = 2000

# Le temps ecoule au-dela duquel on cesse de croire ce qu'il dit.
#
# ⚠️ C'EST LA FAIBLESSE PROPRE AU GUET. Un evenement arrive QUAND la chose se
# produit ; un instantane, lui, ne dit pas quand le texte est arrive, seulement
# qu'il est la. Diviser par le temps ecoule etait juste tant qu'on etait
# prevenu — un releve en retard signifiait alors que la personne avait tape
# lentement. Le guet, lui, ne distingue pas « deux cents mots tapes en une
# minute » de « deux cents mots colles, vus une minute trop tard ».
#
# Mesure sur un vrai Word : un collage de deux cents mots vu deux secondes plus
# tard donne un debit de 200, donc une greffe ; vu soixante secondes plus tard,
# un debit de 6,7, donc de l'ECRITURE. Deux cents mots comptes pour rien. C'est
# par la qu'un vrai document est passe d'une tige a un arbre en trois collages.
#
# L'ASYMETRIE TRANCHE. Une greffe declaree a tort se rattrape toute seule : la
# retravailler la convertit en ecriture (point 4). Une pousse declaree a tort
# ne se rattrape JAMAIS, puisque le point 1 interdit de reculer. Dans le doute,
# il faut donc lire un collage.
#
# Quatre intervalles, soit huit secondes. Personne ne tape soixante mots dans un
# seul elan, donc le plafond ne peut pas transformer de la frappe honnete en
# collage ; au-dela, on n'a de toute facon plus aucune idee de quand le texte
# est arrive.
PLAFOND_ECOULE = 4 * INTERVALLE


def decouper_marque(texte):
    """Les lignes du corps, et le paragraphe d'ou chacune vient.

    Rend (lignes, appartenance), de meme longueur : appartenance[k] est
    l'indice du paragraphe Word qui contient la ligne k. C'est ce qui permet de
    donner un style a une ligne sans le demander a Word ligne par ligne.

    Toutes les separations valent pour l'unite du paysage : celle qui vient
    d'Entree comme celle qui vient de Maj+Entree (point 14).
    """
    if not texte:
        return [], []
    lignes, appartenance = [], []
    for rang, paragraphe in enumerate(texte.split(SEPARATEUR_PARAGRAPHE)):
        morceaux = [paragraphe]
        for s in SEPARATEURS_LIGNE:
            suivants = []
            for m in morceaux:
                suivants.extend(m.split(s))
            morceaux = suivants
        for m in morceaux:
            lignes.append(m)
            appartenance.append(rang)
    return lignes, appartenance


def decouper(texte):
    """Les seules lignes, quand l'appartenance n'interesse pas l'appelant."""
    return decouper_marque(texte)[0]


def compter_paragraphes(texte):
    """Combien de paragraphes Word voit dans ce corps.

    Sert a savoir quand la table des styles est PERIMEE, et ce compte-la est
    gratuit : il se lit dans la chaine qu'on vient deja de recevoir. Taper dans
    un paragraphe ne le change pas ; en ajouter ou en retirer un, si. La lecture
    couteuse des styles — un objet Office.js par paragraphe, ~1,7 ms piece — ne
    part donc que quand la structure bouge, jamais pendant qu'on ecrit.
    """
    return texte.count(SEPARATEUR_PARAGRAPHE) + 1 if texte else 0


def rapprocher(anciennes, nouvelles):
    """Ce qui a bouge entre deux instantanes.

    Rend une liste de mouvements, dans l'ordre du nouvel instantane :

        ("gardee",      i, j)   la ligne i est devenue la ligne j, texte egal
        ("retouchee",   i, j)   la ligne i est devenue la ligne j, texte change
        ("nee",       None, j)  la ligne j n'existait pas
        ("disparue",    i, None) la ligne i n'existe plus

    CE QUI PROTEGE L'INVARIANT CARDINAL : L'APPARIEMENT PAR TEXTE EGAL.

    Identifier les lignes par leur RANG est la faute a ne pas commettre :
    inserer une ligne au milieu decalerait toutes les suivantes, le miroir les
    verrait toutes changer, et une insertion se lirait comme une pluie de
    retouches — de l'extension prise pour de la maturite, l'erreur centrale du
    projet. On apparie donc d'abord ce qui est EGAL. Une ligne qui n'a pas
    bouge, ou qui a seulement change de place, retrouve son identifiant et ne
    rend aucun verdict : c'est aussi ce que le point 3 promet d'un deplacement.

    ⚠️ Ecrit ici parce que la premiere version de ce commentaire attribuait la
    protection au ROGNAGE ci-dessous, et c'etait faux : retirer le rognage
    laisse tous les essais passer, retirer l'appariement par texte les fait
    tomber. Un commentaire qui designe la mauvaise piece est pire que pas de
    commentaire — on finit par retirer la bonne.

    LE ROGNAGE, LUI, N'EST QU'UNE ACCELERATION.

    Ecrire ne change qu'une region locale. Retirer la tete et la queue
    identiques laisse une fenetre d'une ou deux lignes, et evite de construire
    l'index de mille cinq cents chaines a chaque releve. Le resultat est le
    meme ; seul le travail change.

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


def compter_mots(texte):
    """Les mots d'une ligne, pour le SEUL calcul du debit.

    en_mots() serait plus juste mais coute une expression reguliere Unicode par
    ligne, et le debit ne sert qu'a comparer a SEUIL_COLLAGE — quinze mots par
    intervalle de deux secondes, soit 450 mots par minute. A cette echelle,
    decouper aux blancs suffit et ne se trompe jamais de cote.
    """
    return len(texte.split()) if texte and texte.strip() else 0


def _style(styles, appartenance, k):
    """Le style de la ligne k, pris sur son paragraphe.

    Tolerant par construction : une table absente, trop courte, ou decalee d'un
    releve rend « Normal » plutot que de lever. Le style se rafraichit au releve
    suivant, alors qu'une exception dans un tic arreterait tout.
    """
    if not styles or k >= len(appartenance):
        return "Normal"
    rang = appartenance[k]
    return styles[rang] if rang < len(styles) else "Normal"


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
        # Le nombre de paragraphes du dernier releve : l'appelant s'en sert pour
        # savoir s'il doit aller rechercher les styles.
        self.paragraphes = 0
        # Les lignes arrivees en GREFFE, pour que retoucher() sache les
        # convertir (point 4). Le pont ne l'a jamais su, et la conversion
        # n'arrivait donc jamais dans l'add-in.
        self.greffes = set()

    def _neuf(self):
        self._suivant += 1
        return "g%d" % self._suivant

    def amorcer(self, texte, styles=None):
        """Le premier instantane, qui ne fait RIEN pousser.

        Decision 11 : ce qui est deja la est un capital de depart, pas une
        pousse. Sans ce depart separe, ouvrir le volet sur une these de mille
        cinq cents lignes les declarerait toutes NEES d'un coup — le pire
        contresens que le paysage puisse commettre, et exactement ce que
        rattacher() existe pour eviter.

        Rend des couples (texte, style), qui est exactement ce que
        paysage.rattacher() attend.
        """
        self.lignes, appartenance = decouper_marque(texte)
        self.ids = [self._neuf() for _ in self.lignes]
        self.paragraphes = compter_paragraphes(texte)
        return [(l, _style(styles, appartenance, k))
                for k, l in enumerate(self.lignes)]

    def debit(self, faits, ecoule=INTERVALLE):
        """Les mots arrives DANS CE RELEVE, ramenes a l'intervalle.

        Decision 4 : c'est le bloc qu'il faut mesurer, pas la ligne. Un collage
        de douze chapitres arrive d'un coup ; une ligne de 400 mots tapee a la
        main n'existe pas, mais 400 mots arrives en deux secondes, si.

        ⚠️ LE PLANCHER EST L'INTERVALLE, PAS 1. La normalisation doit corriger
        un releve EN RETARD, jamais un releve en avance : divise par cinq
        millisecondes, quatre mots tapes deviendraient un debit de mille six
        cents et passeraient pour un collage. Elle ne peut donc que reduire le
        debit, jamais l'amplifier — panne trouvee en deroulant le volet contre
        un Office.js simule, ou tout s'enchaine sans attendre.

        ⚠️ ET LE PLAFOND EST DE QUATRE INTERVALLES. Voir PLAFOND_ECOULE : au
        dela, le temps ecoule ne dit plus rien de l'arrivee du texte, et
        l'asymetrie des erreurs impose de lire un collage.
        """
        mots = 0
        for f in faits:
            if f["type"] == "nee":
                mots += compter_mots(f["texte"])
            elif f["type"] == "retouchee":
                mots += max(0, compter_mots(f["texte"])
                            - compter_mots(f["ancien"]))
        borne = min(max(ecoule, INTERVALLE), PLAFOND_ECOULE)
        return mots * INTERVALLE / borne

    def nourrir(self, paysage, faits, jour=0, heure=14, debit=0.0):
        """Donne au paysage ce que le releve a vu, et rend les verdicts.

        C'est ici que le guet remplace le pont, et les trois decisions qu'il
        portait sont reprises telles quelles.

        UNE LIGNE NEE VIDE QUI SE REMPLIT EST UNE ECRITURE, pas une reprise.
        Word cree une ligne vide a chaque Entree, et le guet la voit naitre ;
        elle arrive donc en « retouchee » avec un ancien texte vide. Sans cette
        conversion, absorber() n'aurait jamais mis _actif, retoucher() tomberait
        dans la branche « nouvelle visite », et LE PREMIER MOT TAPE SUR CHAQUE
        LIGNE NEUVE compterait comme une reprise. L'extension n'existerait plus.

        Et naissance=True pour la meme raison que sous les evenements : « Il
        faut donc admettre » a toutes les chances d'avoir deja commence une
        autre ligne, et le registre declarerait connue une ligne genuinement
        neuve. Quand on a VU la ligne naitre vide, on sait ce que le registre ne
        peut pas savoir.

        UNE SUPPRESSION EST GRATUITE (point 3). Le registre garde l'empreinte,
        donc supprimer, deplacer ou fusionner ne coute rien et ne rend rien.

        UN COLLAGE RETRAVAILLE SE CONVERTIT (point 4), et c'est neuf. Le pont
        passait toujours etait_greffe=False, donc la branche « conversion » de
        retoucher() n'etait JAMAIS atteinte dans l'add-in : un chapitre colle
        puis retravaille restait une greffe pour toujours. Le guet retient
        quelles lignes sont arrivees en greffe, et la conversion a enfin lieu.
        """
        verdicts = []
        for f in faits:
            genre = f["type"]
            if genre == "visite_finie":
                paysage.quitter()
                verdicts.append({"id": f["id"], "verdict": "visite finie"})
                continue
            if genre == "disparue":
                self.greffes.discard(f["id"])
                verdicts.append({"id": f["id"], "verdict": "disparue"})
                continue
            if genre == "nee":
                v = paysage.absorber(f["texte"], f["style"], debit, jour,
                                     heure, False)
            elif not compter_mots(f["ancien"]):
                v = paysage.absorber(f["texte"], f["style"], debit, jour,
                                     heure, True)
            else:
                v = paysage.retoucher(f["ancien"], f["texte"], jour, heure,
                                      f["id"] in self.greffes, debit)
            if v == "greffe":
                self.greffes.add(f["id"])
            elif v in ("conversion", "ecriture"):
                self.greffes.discard(f["id"])
            verdicts.append({"id": f["id"], "verdict": v})
        return verdicts

    def relever(self, texte, styles=None):
        """Compare le corps a ce qu'on avait vu, et rend ce qui a bouge.

        Rend une liste de faits, prets pour le pont :

            {"type": "nee" | "retouchee" | "disparue",
             "id": ..., "texte": ..., "ancien": ..., "style": ...}

        `styles` est la table des styles par PARAGRAPHE, ou None. Une ligne
        herite du style du paragraphe qui la contient ; sans table, tout vaut
        « Normal ». Sans elle, une citation compterait comme de l'ecriture
        (point 3) et un Titre 1 n'ouvrirait plus de plant (point 6) — deux
        regressions qui ne se voient pas.

        Les lignes gardees ne rendent rien, et c'est tout l'interet : sur une
        these de mille cinq cents lignes, un tic n'en signale qu'une ou deux.
        """
        nouvelles, appartenance = decouper_marque(texte)
        mouvements = rapprocher(self.lignes, nouvelles)

        ids = [None] * len(nouvelles)
        faits = []
        for genre, i, j in mouvements:
            if genre == "gardee":
                ids[j] = self.ids[i]
            elif genre == "retouchee":
                ids[j] = self.ids[i]
                faits.append({"type": "retouchee", "id": self.ids[i],
                              "texte": nouvelles[j], "ancien": self.lignes[i],
                              "style": _style(styles, appartenance, j)})
            elif genre == "nee":
                ids[j] = self._neuf()
                faits.append({"type": "nee", "id": ids[j],
                              "texte": nouvelles[j], "ancien": None,
                              "style": _style(styles, appartenance, j)})
            else:
                faits.append({"type": "disparue", "id": self.ids[i],
                              "texte": None, "ancien": self.lignes[i],
                              "style": ""})

        self.lignes = nouvelles
        self.ids = ids
        self.paragraphes = compter_paragraphes(texte)

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
                              "texte": None, "ancien": None, "style": ""})
                self.visitee = None
                self.calme = 0

        return faits
