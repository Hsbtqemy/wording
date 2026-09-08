"""
La composition du paysage.

C'etait le dernier trou de structure. Les decisions 6 et 7 posent trois
niveaux — paysage, parcelles, plants — et annoncent cinquante-cinq objets melanges,
mais rien ne dit OU un plant se pose. Sans reponse, le paysage est une rangee,
c'est-a-dire une planche de test, pas un paysage. Et comme la reponse fixe le
systeme de coordonnees, elle doit etre prise avant le portage, pas apres.

PROPOSITION — trois regles, chacune portant une chose vraie du texte.

  x        l'ordre dans le document. On lit le paysage comme on lirait la
           these, de gauche a droite. Les parcelles (chapitres) sont separees
           par un intervalle plus large : les trois niveaux deviennent
           visibles sans qu'on ait rien a etiqueter.

  echelle  la MATURITE. Un plant beaucoup repris vient au premier plan,
           grand et net ; un plant pose une fois et jamais retouche reste au
           fond, petit et pale. C'est la seule regle qui rend visible OU LE
           TRAVAIL EST REELLEMENT ALLE — et sur une these dont l'introduction
           a ete ecrite en dernier, ca se voit.

  y        suit l'echelle : ce qui est au premier plan est plus bas. C'est la
           perspective la plus simple qui existe et elle suffit, parce que la
           profondeur porte deja une information.

⚠️ L'extension n'entre PAS dans le placement. Elle est deja dans la taille
propre de chaque plant — un plant etendu est un grand arbre, une ville a sept
tours. La faire aussi porter la profondeur reviendrait a fusionner les deux
axes par la bande, ce que la decision 2 interdit.

⚠️ L'ordre de dessin va du fond vers l'avant, donc du moins mur au plus mur.
C'est ce qui produit l'occlusion entre plants — la meme raison qui a fait
poser les tours de l'architecture de l'arriere vers l'avant.
"""

from __future__ import annotations

import random

from grammaire import (Toile, FOND, SAUT, FAMILLES, depuis_plant,
                       graine_du_document)

HORIZON = 0.62          # part de la hauteur ou passe la ligne d'horizon
# ⚠ Le fond s'ELOIGNE, il ne fane pas. Avec une echelle de 0,42 et une
# opacite de 0,45, un plant jamais repris devenait un fantome — et se lisait
# comme une punition de ne pas avoir retravaille, alors que la decision 1 dit
# que rien ne fane jamais. La profondeur doit rester lisible comme de la
# distance, pas comme de l'effacement : le plant du fond est entier, net, un
# peu plus loin.
ECHELLE_FOND = 0.66     # un plant jamais repris
ECHELLE_AVANT = 1.0     # un plant tres repris
OPACITE_FOND = 0.78
ECART = 1.06            # respiration entre deux plants, en largeur de plant
ECART_PARCELLE = 1.55   # entre deux chapitres

# ⚠️ LE SERRAGE D'UN MASSIF SUIT SA TAILLE, ET C'EST CE QUI EST CACHE
# QU'ON BORNE, PAS CE QUI EST MONTRE.
#
# C'etait 0,46 des qu'une parcelle portait deux plants : chacun recouvrait
# 54 % du suivant. Regle pour la forme que la docstring d'apercu() annonce —
# vingt-sept plants en huit chapitres, donc trois ou quatre par massif, ou le
# chevauchement fait un relief.
#
# Mesure sur le paysage REEL de l'auteur, releve dans Word : trente-cinq
# plants, mais QUATRE Titre 1. Massifs de 6, 6, 14 et 9, et 55 % de
# recouvrement moyen sur trente et une paires consecutives. Quatorze arbres
# qui se recouvrent a moitie ne font pas un relief, ils font une haie — et le
# premier arbre etait le seul lisible du paysage parce qu'il etait le seul
# dont le cote gauche fut libre. La constante avait ete reglee pour trois,
# elle en recevait quatorze.
#
# On borne donc le TOTAL recouvert dans un massif, au lieu de fixer le pas :
#
#       (n - 1) x (1 - serrage) = PLANTS_CACHES
#
# soit serrage = 1 - PLANTS_CACHES / (n - 1). Un massif cache toujours la
# meme chose — un peu plus d'une largeur de plant — qu'il en porte trois ou
# trente. A trois plants la formule redonne EXACTEMENT 0,46 : le cas pour
# lequel la valeur avait ete reglee ne bouge pas d'un pixel.
#
# ⚠️ Le plancher n'est pas une precaution de style, il tient le cas a deux
# plants : la formule y donnerait -0,08, c'est-a-dire un plant pose A GAUCHE
# de son predecesseur. Le paysage se lirait a l'envers.
#
# ⚠️ Il n'y a PAS de plafond, et il ne faut pas en ajouter un. Le serrage
# tend vers 1 sans jamais l'atteindre, donc deux plants d'un meme massif se
# recouvrent toujours un peu, si gros soit le chapitre — c'est ce qui garde
# les trois niveaux du point 6 lisibles sans etiquette : un massif se
# chevauche, une parcelle respire. Un plafond a 0,92 avait ete essaye ; il ne
# protegeait de rien que la formule ne protege deja, et il cassait le seul
# invariant que cette regle ait — le total cache cessait d'etre constant.
SERRAGE_SERRE = 0.46    # le pas le plus serre : deux ou trois plants
PLANTS_CACHES = 1.08    # largeurs de plant recouvertes, au total, par massif


def _serrage(n: int) -> float:
    """Le pas d'un massif de n plants, en largeur de plant."""
    if n < 2:
        return 1.0
    lache = 1.0 - PLANTS_CACHES / (n - 1)
    return max(SERRAGE_SERRE, lache)


def _profondeur(plant: dict) -> float:
    """0 au fond, 1 au premier plan. C'est la maturite, et rien d'autre."""
    return max(0.0, min(1.0, plant.get("maturite", 0.0)))


def composer(plants: list, hauteur=560, graine=1, marge=90):
    """
    Rend le paysage entier. `plants` vient de paysage.Paysage.etat()["plants"].

    Renvoie (svg_interieur, largeur_totale).
    """
    rng = random.Random(graine)
    figures = []

    # 1. On dessine chaque plant a sa taille propre. Un germe se dessine
    #    aussi : il n'a pas de famille, mais il a deja quelque chose a montrer.
    for p in plants:
        vide = not p.get("famille") and not (p.get("germe") or {}).get("taille")
        if vide:
            continue
        # depuis_plant est le seul point de contact entre l'etat et le
        # rendu : la teinte ET la physionomie viennent du texte de ce plant.
        figures.append((p, depuis_plant(p, graine + p["rang"] * 977)))

    if not figures:
        return [], marge * 2

    # 2. Echelle et position.
    y_horizon = hauteur * HORIZON
    haut_utile = hauteur * 0.52
    poses, x = [], marge
    parcelle = None
    for p, t in figures:
        d = _profondeur(p)
        # L'echelle se calcule sur la taille FINALE du plant, jamais sur sa
        # taille du moment.
        #
        # Normaliser sur la taille courante ramenait tout plant a la meme
        # hauteur : un plant a 800 mots et un plant a 2 500 apparaissaient
        # identiques, et L'EXTENSION DEVENAIT INVISIBLE DANS LE PAYSAGE. On
        # aurait montre cinquante-cinq objets de meme taille pour une these dont
        # les chapitres n'ont rien a voir en volume. C'est exactement l'erreur
        # du volet, un cran plus haut.
        #
        # On normalise sur l'ENCOMBREMENT et non sur la seule hauteur : une
        # creature deployee est basse et tres large, et la mettre a la hauteur
        # des autres lui donnait le tiers du paysage a elle seule.
        gl, gh = gabarit(p, graine + p["rang"] * 977)
        encombrement = max(gh, gl * 0.52)
        k = (ECHELLE_FOND + (ECHELLE_AVANT - ECHELLE_FOND) * d) \
            * haut_utile / encombrement
        # La place reservee est celle de la taille finale : un plant qui
        # grandit ne doit pas pousser ses voisins.
        largeur = gl * k
        titre = p.get("titre") or ""
        if parcelle is not None and titre and titre != parcelle:
            x += largeur * (ECART_PARCELLE - ECART)   # respiration de chapitre
        parcelle = titre or parcelle
        # Le premier plan descend sous l'horizon, le fond remonte dessus.
        y = y_horizon + (d - 0.5) * hauteur * 0.20 + rng.uniform(-4, 4)
        poses.append((d, x + largeur / 2, y, k, t))
        x += largeur * ECART

    largeur_totale = x + marge
    return poses, largeur_totale


def rendre(poses, cadre, hauteur, largeur_svg="100%") -> str:
    """
    Rend le monde a travers un CADRE (x, y, largeur, hauteur) en coordonnees
    du monde. C'est le seul rendu qui existe : la vue de travail et la vue
    d'ensemble ne sont pas deux dessins, ce sont deux cadres sur le meme.
    Deux dessins pourraient se contredire ; deux cadres, non.
    """
    vx, vy, vw, vh = cadre
    # Du fond vers l'avant : c'est l'occlusion qui fait un paysage.
    out = []
    for d, cx, y, k, t in sorted(poses, key=lambda q: q[0]):
        # Un voile atmospherique tres leger, juste de quoi separer les plans.
        opacite = OPACITE_FOND + (1.0 - OPACITE_FOND) * d
        out.append(f'<g opacity="{opacite:.2f}">{t.pose(cx, y, k)}</g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="{vx:.1f} {vy:.1f} {vw:.1f} {vh:.1f}" '
            f'width="{largeur_svg}">'
            f'<rect x="{vx:.1f}" y="{vy:.1f}" width="{vw:.1f}" '
            f'height="{vh:.1f}" fill="{FOND}"/>'
            f'{"".join(out)}</svg>')


def svg(plants: list, hauteur=560, graine=1) -> str:
    poses, largeur = composer(plants, hauteur, graine)
    return rendre(poses, (0, 0, largeur, hauteur), hauteur)


# --------------------------------------------------------------------------
def _demonstration(mots=42000, graine=7):
    """Une redaction complete, rejouee, puis rendue en paysage."""
    from corpus import these
    from paysage import Paysage

    doc = these(mots_cibles=mots, chapitres=4, graine=graine)
    pays = Paysage(identifiant="demo")
    rng = random.Random(graine)

    # On ne reprend pas tous les chapitres autant. C'est meme le contraire :
    # il y a celui qu'on a pose d'un jet et celui sur lequel on est revenu
    # vingt fois. Sans cette inegalite, la profondeur n'a rien a montrer — et
    # une redaction ou tout serait repris pareil n'existe pas.
    intensite = [0.4, 3.2, 1.1, 5.0]
    chapitre = -1
    for texte, style, jour, heure in doc:
        if style.lower().startswith("titre 1"):
            chapitre += 1
        v = pays.absorber(texte, style=style, jour=jour, heure=heure,
                          mots_par_intervalle=7)
        if v != "ecriture":
            continue
        moyenne = intensite[chapitre % len(intensite)]
        courant = texte
        for _ in range(int(rng.expovariate(1.0 / max(moyenne, 0.05)))):
            pays.quitter()
            suivant = courant.replace(".", ",", 1) if "." in courant                 else courant + " " + courant.split()[0]
            pays.retoucher(courant, suivant, jour=jour, heure=heure)
            courant = suivant
        pays.quitter()
    return pays


# --------------------------------------------------------------------------
# Deux vues, pas une echelle
# --------------------------------------------------------------------------
# Le dezoom progressif est la croissance logarithmique du point 6, transposee
# d'un cran. Mesure : si tout doit tenir dans le cadre, un paragraphe deplace
# 3,84 % / n de ce qu'on regarde. A 28 plants — 70 000 mots — cela fait
# 0,137 %, c'est-a-dire exactement le seuil ou le point 6 declare le mecanisme
# mort, atteint exactement au meme nombre de mots. Les cycles de plant
# avaient rachete ce retour ; le dezoom le redepenserait.
#
# ⚠️ CE CALCUL NE DEPEND PAS DE LA TAILLE D'UN PLANT. Le rapport
# paragraphe / plant et le nombre de plants se compensent exactement : passer
# de 5 000 a 2 500 mots par plant double les deux — 1,92 % a 14 plants,
# 3,84 % a 28 — et laisse 0,137 % inchange. La conclusion tient donc quelle
# que soit l'echelle. Ca n'allait pas de soi, et ca a ete reverifie le jour ou
# la constante a bouge.
#
# Une barre defilante a l'echelle constante garde le retour, mais perd
# l'ensemble — or l'ensemble est ce pour quoi le cadeau existe, a la fin.
#
# Les deux exigences sont contraires, donc aucune echelle unique ne les tient.
# La decision 12 avait deja separe les deux regimes sans le dire : « seul le
# plant en cours est vivant ; les plants acheves sont rasterises une fois ».
#
#   VUE DE TRAVAIL   le plant en cours, a taille pleine, dans le volet.
#                    Retour intact, 0,04 % par mot, indefiniment.
#                    Les plants acheves ne sont meme pas dessines.
#
#   VUE D'ENSEMBLE   le paysage entier, ouvert deliberement. Aucune exigence
#                    de retour : on n'ecrit pas pendant qu'on la regarde.
#
# Contrainte de forme : le volet Word est une colonne etroite et haute
# (~320-450 px de large). Une bande horizontale y est le pire format possible.
# La vue d'ensemble appartient donc a un dialogue (displayDialogAsync), qui
# s'ouvre en fenetre large ; le volet garde la vue de travail.


# ⚠️ LE RECUL DE LA CAMERA. La taille apparente du plant en cours vaut
#
#       apparente = (taille / finale) ** RECUL_CAMERA
#
#   et non taille / finale.
#
#   A 1,0 — ce qu'on a fait longtemps — le cadre EST la taille finale : un plant
#   dont la taille vaut 5 % de sa taille finale occupe 5 % du volet, c'est-a-dire
#   un cheveu. Or la personne regarde un plant sans famille 33 % du temps
#   (decision 6). A 0,0 le cadre serait la taille du moment, ce que gabarit()
#   refuse par ailleurs : un plant jeune et un plant acheve se ressembleraient et
#   la croissance deviendrait invisible.
#
#   A 0,5, ce meme plant occupe 22 % du volet, et la croissance reste entierement
#   lisible puisque la fonction est strictement croissante.
#
#   ⚠️ CE QUI FAIT TENIR LA DECISION 1, C'EST LA MONOTONIE, PAS LA VALEUR.
#   L'autre proposition etait des PALIERS de dezoom — tres zoome au depart, on
#   recule d'un cran quand le plant devient grand, puis encore. Elle donne la
#   meme presence au germe, mais chaque palier est un retrecissement VISIBLE,
#   trois ou quatre fois par plant : on rachete avec la camera ce qu'on venait de
#   corriger dans le dessin. Un exposant n'a pas de palier — le cadre ne fait que
#   grandir tant que le plant grandit, donc rien ne peut reculer.
#
#   EFFET DE BORD MESURE, et ce n'est pas un hasard heureux mais une propriete de
#   la puissance : l'encombrement d'un plant flotte de +-10 % d'un pas au suivant
#   (decision 6, point ouvert). Eleve a 0,5, un recul de 10,8 % de la taille n'en
#   fait plus que 5,5 % de l'apparence. L'exposant amortit le flottement dans le
#   meme mouvement qu'il rapproche la camera.
RECUL_CAMERA = 0.5


def gabarit(plant: dict, graine: int):
    """
    L'encombrement que CE plant atteindra une fois plein.

    Le volet ne doit pas cadrer sur le plant tel qu'il est : s'il le remplit
    toujours, un plant jeune et un plant acheve se ressemblent et la croissance
    devient invisible — on aurait detruit le retour par l'autre bout, en
    voulant le preserver. On cadre donc sur la taille FINALE : un plant jeune
    occupe une fraction du volet, et chaque mot en remplit 0,04 % —
    quelle que soit la facon dont on ponctue, ce qui est exactement la
    garantie de la decision 6 depuis qu'elle se compte en mots seuls.
    """
    plein = dict(plant)
    plein["extension"] = 1.0
    plein["maturite"] = max(plant.get("maturite", 0.0), 0.85)
    if not plein.get("famille"):
        # Un germe n'a pas encore de famille, donc pas de taille finale
        # connue. On prend LA PLUS GRANDE des quatre.
        #
        # Pas la pressentie : sa taille changerait le jour ou une tendance
        # apparait, et comme les quatre familles n'ont pas le meme
        # encombrement natif, le germe se mettrait a RETRECIR sous les yeux de
        # la personne. Le point 1 interdit que quoi que ce soit recule.
        #
        # Avec la plus grande, le germe est dessine a la plus petite echelle
        # possible : quand la famille se verrouille, l'echelle ne peut que
        # monter. La croissance reste monotone quoi qu'il arrive.
        plein["germe"] = None
        grand = None
        for famille in FAMILLES:
            plein["famille"] = famille
            t = depuis_plant(plein, graine)
            enc = max(t.hauteur(), t.largeur() * 0.52)
            if grand is None or enc > grand[0]:
                grand = (enc, t.largeur(), t.hauteur())
        return grand[1], grand[2]
    t = depuis_plant(plein, graine)
    return t.largeur(), t.hauteur()


def vue_de_travail(plants: list, graine=1, largeur=360, hauteur=440,
                   monde=560) -> str:
    """
    Ce que le volet montre pendant qu'on ecrit.

    Ce n'est PAS un autre dessin du paysage : c'est le meme monde, vu par un
    cadre plus serre, pose sur le plant en cours. Deux dessins separes du meme
    objet finissent toujours par se contredire — celui-ci ne le peut pas.

    Trois consequences, et c'est pour elles qu'on l'a fait ainsi :

      - le volet n'est JAMAIS vide. Le plant qui vient de naitre est presque
        rien, mais le precedent est juste derriere, qui deborde du cadre. On
        avance dans le paysage au lieu de repartir de zero cinquante-cinq fois.

      - le cadre est dimensionne sur la taille FINALE du plant en cours, jamais
        sur sa taille du moment. S'il remplissait toujours le volet, un plant
        jeune et un plant acheve se ressembleraient et la croissance
        deviendrait invisible : on aurait detruit le retour en voulant le
        preserver.

      - passer de cette vue a la vue d'ensemble est un dezoom qu'on FAIT, pas
        un dezoom qu'on SUBIT. C'est toute la difference avec le dezoom
        progressif : la camera recule, le monde ne retrecit pas.
    """
    poses, _ = composer(plants, monde, graine)
    if not poses:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'viewBox="0 0 {largeur} {hauteur}" width="100%">'
                f'<rect width="{largeur}" height="{hauteur}" '
                f'fill="{FOND}"/></svg>')

    # ⚠️ LE PLANT QUI VIENT DE CHANGER, ET NON LE DERNIER.
    #
    #   C'etait vivants[-1] et max(poses) : le volet cadrait toujours le plant le
    #   plus a droite, donc le plus recent. Revenir travailler sur le chapitre 1 ne
    #   ramenait pas la camera dessus — et comme la reprise etait creditee au plant
    #   courant, il n'y avait de toute facon rien a y voir.
    #
    #   Les deux moities se tiennent : depuis que le registre dit A QUI appartient
    #   chaque paragraphe (point 3), retoucher fait murir le bon plant, et la camera
    #   peut le montrer. Ecrire designe le plant courant, retoucher celui qui porte
    #   le texte — une seule regle pour les deux axes du point 2.
    #
    #   Une pose ne porte pas son rang, donc on refait ici le filtre exact de
    #   composer() pour retrouver l'indice. Si aucun plant n'est marque — un
    #   sous-ensemble de plants, un etat d'avant — on retombe sur le dernier pose,
    #   c'est-a-dire sur le comportement precedent.
    poses_de = [q for q in plants
                if q.get("famille") or (q.get("germe") or {}).get("taille")]
    i = next((n for n, q in enumerate(poses_de) if q.get("actif")),
             len(poses_de) - 1)
    actif = poses_de[i]
    d, cx, y, k, t = poses[i]

    # Taille FINALE de ce plant, dans les unites du monde. Le cadre doit la
    # contenir ENTIEREMENT : un plant plus large que haut — une creature
    # deployee, un arbre — se ferait sinon rogner sur les cotes le jour ou il
    # arrive a maturite, c'est-a-dire au pire moment.
    gl, gh = gabarit(actif, graine + actif["rang"] * 977)
    # Le cadre interpole entre la taille du moment et la taille finale — voir
    # RECUL_CAMERA. Il contient toujours le plant : la taille finale est par
    # construction superieure a la taille du moment, donc le cadre aussi.
    gl = max(t.largeur(), 1.0) ** (1 - RECUL_CAMERA) * gl ** RECUL_CAMERA
    gh = max(t.hauteur(), 1.0) ** (1 - RECUL_CAMERA) * gh ** RECUL_CAMERA
    vh = max(gh * k * 1.30, gl * k * 1.15 * hauteur / largeur, 1.0)
    vw = vh * largeur / hauteur

    # Le plant en cours n'est pas au centre mais aux deux tiers a droite.
    #
    # C'est la reponse a la seule chose que ce volet ne savait pas montrer :
    # un plant qui vient de naitre n'est presque rien, et centre dans son
    # cadre il donne un volet vide — cinquante-cinq fois sur une these, dont la
    # premiere fois est celle des 800 premiers mots ecrits avec le cadeau.
    # Decale, il laisse voir le plant precedent qui sort par la gauche. On
    # avance dans le paysage au lieu de repartir de zero a chaque chapitre, et
    # la naissance d'un plant devient un evenement visible : le precedent
    # s'en va.
    return rendre(poses, (cx - vw * 0.63, y - vh * 0.86, vw, vh), hauteur)


def apercu(plants: list, hauteur=520, graine=1, marge=70):
    """
    La vue d'ensemble, groupee par PARCELLE.

    La compression ne vient pas d'une reduction d'echelle mais du regroupement :
    la hierarchie du point 6 la donne gratuitement. Un massif se regarde d'un
    coup. Les plants d'une meme parcelle se chevauchent — c'est le meme texte,
    ils forment un relief — et les parcelles respirent entre elles.

    ⚠️ Cette docstring disait « vingt-sept plants en huit chapitres font
    huit massifs », et le serrage etait regle sur cette phrase. Un vrai
    document ne decoupe pas si regulierement : celui de l'auteur fait
    trente-cinq plants en QUATRE chapitres. Le nombre de plants par massif
    n'est pas une constante du probleme, c'est une variable — voir _serrage().
    """
    rng = random.Random(graine)
    parcelles: list = []
    for p in plants:
        if not p.get("famille"):
            continue
        cle = p.get("titre") or ""
        if not parcelles or parcelles[-1][0] != cle:
            parcelles.append((cle, []))
        parcelles[-1][1].append(p)
    if not parcelles:
        return [], marge * 2

    y_horizon = hauteur * HORIZON
    haut_utile = hauteur * 0.44
    poses, x = [], marge
    for cle, groupe in parcelles:
        # Dans un massif, les plants se serrent et se recouvrent — d'autant
        # moins qu'ils sont nombreux. Voir _serrage().
        serrage = _serrage(len(groupe))
        largeur_massif = 0.0
        for p in groupe:
            t = depuis_plant(p, graine + p["rang"] * 977)
            d = _profondeur(p)
            gl, gh = gabarit(p, graine + p["rang"] * 977)
            enc = max(gh, gl * 0.52)
            k = (ECHELLE_FOND + (ECHELLE_AVANT - ECHELLE_FOND) * d) \
                * haut_utile / enc
            l = gl * k
            y = y_horizon + (d - 0.5) * hauteur * 0.18 + rng.uniform(-5, 5)
            poses.append((d, x + largeur_massif + l / 2, y, k, t))
            largeur_massif += l * serrage
        x += largeur_massif + haut_utile * 0.55      # respiration de parcelle

    return poses, x + marge


def svg_apercu(plants: list, hauteur=520, graine=1) -> str:
    poses, largeur = apercu(plants, hauteur, graine)
    return rendre(poses, (0, 0, largeur, hauteur), hauteur)


def planche_volet(mots=60000, graine=7, vol_l=330, vol_h=420):
    """
    Le volet, autour d'une naissance de plant.

    On rejoue une redaction et on capture le volet a cinq instants de la vie
    du troisieme plant : c'est le seul moment que la vue de travail ne savait
    pas montrer.
    """
    import copy
    from corpus import these
    from paysage import Paysage

    doc = these(mots_cibles=mots, chapitres=3, graine=graine)
    pays = Paysage(identifiant="volet")
    rng = random.Random(graine)
    captures, cibles, i = [], None, 0

    for texte, style, jour, heure in doc:
        v = pays.absorber(texte, style=style, jour=jour, heure=heure,
                          mots_par_intervalle=7)
        if v == "ecriture":
            for _ in range(int(rng.expovariate(1 / 2.2))):
                pays.quitter()
                suiv = texte.replace(".", ",", 1) if "." in texte else texte + " x"
                pays.retoucher(texte, suiv, jour=jour, heure=heure)
                texte = suiv
            pays.quitter()
        if len(pays.segments) >= 3 and cibles is None:
            cibles = [0, 70, 260, 800, 2600]
        if cibles and i < len(cibles) and pays.segments[-1].mots >= cibles[i]:
            captures.append((pays.segments[-1].mots, pays.segments[-1].stade(),
                             copy.deepcopy(pays.etat()["plants"])))
            i += 1
        if cibles and i >= len(cibles):
            break

    W = 30 + len(captures) * (vol_l + 26)
    H = 90 + vol_h
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
         f'width="100%"><rect width="{W}" height="{H}" fill="#f3f1ec"/>',
         '<g font-family="Georgia, serif" fill="#6b6560">']
    for j, (m, stade, plants) in enumerate(captures):
        x = 30 + j * (vol_l + 26)
        interieur = vue_de_travail(plants, largeur=vol_l, hauteur=vol_h)
        interieur = interieur.replace(
            '<svg xmlns="http://www.w3.org/2000/svg" ', '<svg ')
        o.append(f'<text x="{x + vol_l/2}" y="34" font-size="10.5" '
                 f'text-anchor="middle" letter-spacing="1.4">'
                 f'{m} MOTS — {stade.upper()}</text>')
        o.append(f'<svg x="{x}" y="52" width="{vol_l}" height="{vol_h}" '
                 f'viewBox="0 0 {vol_l} {vol_h}">{interieur}</svg>')
        o.append(f'<rect x="{x}" y="52" width="{vol_l}" height="{vol_h}" '
                 f'fill="none" stroke="#d9d4ca"/>')
    return SAUT.join(o) + "</g></svg>"


if __name__ == "__main__":
    pays = _demonstration()
    etat = pays.etat()
    plants = etat["plants"]
    print(f"{etat['mots']} mots, {len(plants)} plants")
    for p in plants:
        if p["famille"]:
            print(f"  plant {p['rang']:>2} | {p['famille']:<13}"
                  f" ext {p['extension']:.2f} mat {p['maturite']:.2f}"
                  f" | {len(p['dates'])} dates"
                  f"{' | NUIT' if p['nuit'] else ''}")
    open("planche_paysage.svg", "w", encoding="utf-8").write(svg(plants))
    print("\nplanche_paysage.svg ecrit")
