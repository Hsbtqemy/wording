"""
La composition du paysage.

C'etait le dernier trou de structure. Les decisions 6 et 7 posent trois
niveaux — paysage, parcelles, plants — et annoncent vingt-sept objets melanges,
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

from grammaire import Toile, FOND, SAUT, depuis_plant, graine_du_document

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

    # 1. On dessine chaque plant a sa taille propre.
    for p in plants:
        famille = p.get("famille")
        if not famille:
            continue                       # un germe ne se dessine pas encore
        # depuis_plant est le seul point de contact entre l'etat et le
        # rendu : la teinte ET la physionomie viennent du texte de ce plant.
        figures.append((p, depuis_plant(p, graine + p["rang"] * 977)))

    if not figures:
        return "", marge * 2

    # 2. Echelle et position.
    y_horizon = hauteur * HORIZON
    haut_utile = hauteur * 0.52
    poses, x = [], marge
    parcelle = None
    for p, t in figures:
        d = _profondeur(p)
        # On normalise sur l'ENCOMBREMENT, pas sur la seule hauteur : une
        # creature deployee est basse et tres large, et la mettre a la hauteur
        # des autres lui donnait le tiers du paysage a elle seule.
        encombrement = max(t.hauteur(), t.largeur() * 0.52)
        k = (ECHELLE_FOND + (ECHELLE_AVANT - ECHELLE_FOND) * d) \
            * haut_utile / encombrement
        largeur = t.largeur() * k
        titre = p.get("titre") or ""
        if parcelle is not None and titre and titre != parcelle:
            x += largeur * (ECART_PARCELLE - ECART)   # respiration de chapitre
        parcelle = titre or parcelle
        # Le premier plan descend sous l'horizon, le fond remonte dessus.
        y = y_horizon + (d - 0.5) * hauteur * 0.20 + rng.uniform(-4, 4)
        poses.append((d, x + largeur / 2, y, k, t))
        x += largeur * ECART

    largeur_totale = x + marge

    # 3. Du fond vers l'avant : c'est l'occlusion qui fait un paysage.
    poses.sort(key=lambda q: q[0])
    out = []
    for d, cx, y, k, t in poses:
        # Un voile atmospherique tres leger, juste de quoi separer les plans.
        opacite = OPACITE_FOND + (1.0 - OPACITE_FOND) * d
        out.append(f'<g opacity="{opacite:.2f}">{t.pose(cx, y, k)}</g>')
    return "".join(out), largeur_totale


def svg(plants: list, hauteur=560, graine=1) -> str:
    interieur, largeur = composer(plants, hauteur, graine)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {largeur:.0f} {hauteur}" width="100%">'
            f'<rect width="{largeur:.0f}" height="{hauteur}" fill="{FOND}"/>'
            f'{interieur}</svg>')


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


# --------------------------------------------------------------------------
# Deux vues, pas une echelle
# --------------------------------------------------------------------------
# Le dezoom progressif est la croissance logarithmique du point 6, transposee
# d'un cran. Mesure : si tout doit tenir dans le cadre, un paragraphe deplace
# 1,92 % / n de ce qu'on regarde. A 14 plants — 70 000 mots — cela fait
# 0,137 %, c'est-a-dire exactement le seuil ou le point 6 declare le mecanisme
# mort, atteint exactement au meme nombre de mots. Les cycles de 5 000 mots
# avaient rachete ce retour ; le dezoom le redepenserait.
#
# Une barre defilante a l'echelle constante garde le retour, mais perd
# l'ensemble — or l'ensemble est ce pour quoi le cadeau existe, a la fin.
#
# Les deux exigences sont contraires, donc aucune echelle unique ne les tient.
# La decision 12 avait deja separe les deux regimes sans le dire : « seul le
# plant en cours est vivant ; les plants acheves sont rasterises une fois ».
#
#   VUE DE TRAVAIL   le plant en cours, a taille pleine, dans le volet.
#                    Retour intact, 1,92 % par paragraphe, indefiniment.
#                    Les plants acheves ne sont meme pas dessines.
#
#   VUE D'ENSEMBLE   le paysage entier, ouvert deliberement. Aucune exigence
#                    de retour : on n'ecrit pas pendant qu'on la regarde.
#
# Contrainte de forme : le volet Word est une colonne etroite et haute
# (~320-450 px de large). Une bande horizontale y est le pire format possible.
# La vue d'ensemble appartient donc a un dialogue (displayDialogAsync), qui
# s'ouvre en fenetre large ; le volet garde la vue de travail.


def gabarit(plant: dict, graine: int):
    """
    L'encombrement que CE plant atteindra une fois plein.

    Le volet ne doit pas cadrer sur le plant tel qu'il est : s'il le remplit
    toujours, un plant jeune et un plant acheve se ressemblent et la croissance
    devient invisible — on aurait detruit le retour par l'autre bout, en
    voulant le preserver. On cadre donc sur la taille FINALE : un plant jeune
    occupe une fraction du volet, et chaque paragraphe en remplit 1,92 %, ce
    qui est exactement la garantie de la decision 6.
    """
    plein = dict(plant)
    plein["extension"] = 1.0
    plein["maturite"] = max(plant.get("maturite", 0.0), 0.85)
    t = depuis_plant(plein, graine)
    return t.largeur(), t.hauteur()


def vue_de_travail(plant: dict, graine: int, largeur=360, hauteur=440,
                   marge=28) -> str:
    """
    Le plant en cours, seul. C'est ce que le volet montre pendant qu'on ecrit,
    et son echelle ne change JAMAIS : elle est fixee par la taille finale du
    plant, pas par sa taille du moment.
    """
    cadre = (f'<svg xmlns="http://www.w3.org/2000/svg" '
             f'viewBox="0 0 {largeur} {hauteur}" width="100%">'
             f'<rect width="{largeur}" height="{hauteur}" fill="{FOND}"/>')
    if not plant.get("famille"):
        return cadre + "</svg>"

    gl, gh = gabarit(plant, graine)
    k = min((largeur - 2 * marge) / gl, (hauteur - 2 * marge) / gh)
    t = depuis_plant(plant, graine)
    # Pose au sol, centre : le plant pousse vers le haut depuis une base fixe,
    # comme il le ferait dans le paysage.
    return cadre + t.pose(largeur / 2, hauteur - marge, k) + "</svg>"


def apercu(plants: list, hauteur=520, graine=1, marge=70):
    """
    La vue d'ensemble, groupee par PARCELLE.

    La compression ne vient pas d'une reduction d'echelle mais du regroupement :
    la hierarchie du point 6 la donne gratuitement. Vingt-sept plants en huit
    chapitres font huit massifs, et un massif se regarde d'un coup. Les plants
    d'une meme parcelle se chevauchent — c'est le meme texte, ils forment un
    relief — et les parcelles respirent entre elles.
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
        return "", marge * 2

    y_horizon = hauteur * HORIZON
    haut_utile = hauteur * 0.44
    poses, x = [], marge
    for cle, groupe in parcelles:
        # Dans un massif, les plants se serrent et se recouvrent.
        serrage = 0.46 if len(groupe) > 1 else 1.0
        largeur_massif = 0.0
        for p in groupe:
            t = depuis_plant(p, graine + p["rang"] * 977)
            d = _profondeur(p)
            enc = max(t.hauteur(), t.largeur() * 0.52)
            k = (ECHELLE_FOND + (ECHELLE_AVANT - ECHELLE_FOND) * d) \
                * haut_utile / enc
            l = t.largeur() * k
            y = y_horizon + (d - 0.5) * hauteur * 0.18 + rng.uniform(-5, 5)
            poses.append((d, x + largeur_massif + l / 2, y, k, t))
            largeur_massif += l * serrage
        x += largeur_massif + haut_utile * 0.55      # respiration de parcelle

    poses.sort(key=lambda q: q[0])
    out = []
    for d, cx, y, k, t in poses:
        op = OPACITE_FOND + (1.0 - OPACITE_FOND) * d
        out.append(f'<g opacity="{op:.2f}">{t.pose(cx, y, k)}</g>')
    return "".join(out), x + marge


def svg_apercu(plants: list, hauteur=520, graine=1) -> str:
    interieur, largeur = apercu(plants, hauteur, graine)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {largeur:.0f} {hauteur}" width="100%">'
            f'<rect width="{largeur:.0f}" height="{hauteur}" fill="{FOND}"/>'
            f'{interieur}</svg>')
