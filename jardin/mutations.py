"""
Le harnais attrape-t-il les erreurs deja commises dans ce projet ?

Une batterie d'essais qui passe ne prouve rien tant qu'on n'a pas montre
qu'elle sait echouer. Ce fichier reintroduit, une par une, les regressions
reellement rencontrees pendant la conception — chacune correspond a une entree
de DECISIONS.md — et verifie que `essais.py` les rattrape.

C'est ce qui a montre que deux essais ne servaient a rien :

  - « la subordination ne sature pas » recalculait la borne lui-meme au lieu
    de passer par extraire(), donc il testait sa propre arithmetique ;
  - « le verrou attend des lectures espacees » comparait a la constante qu'on
    venait justement de mettre a zero, donc il s'adaptait a la panne.

Un essai qui s'adapte a la regression qu'il surveille est pire qu'absent : il
rassure.

    python mutations.py
"""

from __future__ import annotations

import io
import os
import subprocess
import sys

RACINE = os.path.dirname(os.path.abspath(__file__))

# (fichier, motif, remplacement, ce que la regression retablit)
MUTATIONS = [
    ("traits.py",
     "    connecteurs = occurrences / len(mots) * 100",
     "    connecteurs = len({_sans_accent(m).lower() for m in mots}"
     " & CONNECTEURS_SUBORDINATION)",
     "decision 12 : le compteur de connecteurs redevient une couverture"),

    ("paysage.py",
     '        plant.reprises += 1\n        self._actif, self._mode = e, "reprise"',
     '        plant.reprises += 1\n'
     '        plant.mots += max(0, len(en_mots(nouveau)) - len(en_mots(ancien)))\n'
     '        self._actif, self._mode = e, "reprise"',
     "decision 2 : une reprise recompte dans l'extension (exploit rouvert)"),

    ("paysage.py", "MOTS_ENTRE_LECTURES = 100", "MOTS_ENTRE_LECTURES = 0",
     "decision 5 : le verrou ne compte plus des lectures espacees"),

    ("composition.py",
     '        gl, gh = gabarit(p, graine + p["rang"] * 977)\n'
     "        encombrement = max(gh, gl * 0.52)",
     "        encombrement = max(t.hauteur(), t.largeur() * 0.52)\n"
     "        gl = t.largeur()",
     "decision 14 : l'echelle revient sur la taille courante"),

    ("grammaire.py",
     '"nuit":      ["#8d84c4", "#a99ede", "#7a6fb0", "#9a90d2", "#b8aeea"]',
     '"nuit":      ["#7a7f9c", "#9aa0bd", "#5c6180", "#6e7392", "#8a90ad"]',
     "decision 9 : la palette de nuit revient au bleu-gris de la v5"),

    ("grammaire.py",
     "        t.trait(x, y, x2, y2, m, structure=True)    # squelette",
     "        t.trait(x, y, x2, y2, m, tt.ton(rng), structure=True)",
     "decision 9 : la couleur deborde sur la structure"),

    ("grammaire.py",
     "    part = BUDGET_FEUILLAGE / pointes",
     "    part = BUDGET_FEUILLAGE // pointes",
     "decision 1 : le feuillage se divise au lieu de se repartir,"
     " et la couronne perd un tiers de ses traits en gagnant un rameau"),

    ("grammaire.py",
     "    prof_max = 4.0 + extension * 3.0",
     "    prof_max = 4.0 + int(extension * 3.0)",
     "la profondeur redevient entiere : quatre formes sur la vie d'un plant"),

    ("grammaire.py",
     "        inverse = (inverse << 1) | ((index >> i) & 1)",
     "        inverse = index",
     "les rameaux sortent de gauche a droite au lieu d'etre disperses"),

    ("composition.py",
     "RECUL_CAMERA = 0.5",
     "RECUL_CAMERA = 1.0",
     "le cadre du volet revient a la taille finale : un germe redevient"
     " un cheveu un tiers du temps"),

    ("message.py",
     "    t.cadre = cadre_de(phrase, corps, largeur, x0, y0)",
     "    t.cadre = None",
     "point ouvert 9 : le message se recentre a chaque lettre"),

    ("phrases.py",
     "        queue = set(_paquet(tour - 1, corpus)[-garde:])",
     "        queue = set()",
     "point ouvert 10 : le raccord du paquet ne porte plus"),

    # ------------------------------------------------------------------ guet
    # Le guet remplace les evenements de paragraphe, absents de la machine
    # cible (point ouvert 15). Aucune de ces regressions ne fait planter quoi
    # que ce soit : elles decalent des identifiants, et le paysage pousse de
    # travers sans que rien ne le dise.
    ("guet.py",
     r'SEPARATEURS_LIGNE = ("\x0b", "\n")',
     r'SEPARATEURS_LIGNE = ()',
     "point 14 : le saut de ligne cesse de separer, 35 pages font un paragraphe"),

    # Le style appartient au PARAGRAPHE, la ligne en herite. Confondre
    # les deux indices est la faute naturelle a cet endroit.
    ("guet.py",
     "            appartenance.append(rang)",
     "            appartenance.append(len(lignes) - 1)",
     "le style est indexe par LIGNE et non par paragraphe : deux lignes"
     " d'un meme paragraphe recoivent deux styles differents"),

    ("guet.py",
     "    rang = appartenance[k]\n"
     '    return styles[rang] if rang < len(styles) else "Normal"',
     '    return "Normal"',
     "plus aucun style ne remonte : une citation compte comme de"
     " l'ecriture (point 3) et un Titre 1 n'ouvre plus de plant (point 6)"),

    ("guet.py",
     "    if not styles or k >= len(appartenance):",
     "    if False:",
     "une table absente fait lever dans un tic, au lieu de rendre Normal"),

    ("guet.py",
     "    return texte.count(SEPARATEUR_PARAGRAPHE) + 1 if texte else 0",
     "    return texte.count(SEPARATEURS_LIGNE[0]) + 1 if texte else 0",
     "la peremption des styles se compte en LIGNES : la table ne se"
     " rafraichit plus quand un paragraphe apparait"),

    ("guet.py",
     """    deplacees = {}                       # j -> i
    pris = set()
    for j in fenetre_b:
        libres = par_texte.get(nouvelles[j])
        while libres:
            i = libres.pop(0)
            if i not in pris:
                deplacees[j] = i
                pris.add(i)
                break""",
     """    deplacees = {}
    pris = set()""",
     "les lignes egales ne se reconnaissent plus : un deplacement devient"
     " deux retouches, donc de la maturite inventee"),

    ("guet.py",
     "        self.lignes, appartenance = decouper_marque(texte)\n"
     "        self.ids = [self._neuf() for _ in self.lignes]",
     "        self.lignes, appartenance = [], []\n"
     "        self.ids = []",
     "decision 11 : le capital de depart est declare NE, une these entiere"
     " pousse d'un coup a l'ouverture"),

    ("guet.py",
     '                              "texte": nouvelles[j], "ancien": self.lignes[i],\n'
     '                              "style": _style(styles, appartenance, j)})',
     '                              "texte": nouvelles[j], "ancien": None,\n'
     '                              "style": _style(styles, appartenance, j)})',
     "la retouche perd son ancien texte : paysage.retoucher ne peut plus"
     " distinguer une reprise d'une premiere redaction"),

    ("guet.py",
     "            elif genre == \"retouchee\":\n                ids[j] = self.ids[i]",
     "            elif genre == \"retouchee\":\n                ids[j] = self._neuf()",
     "une ligne retouchee change d'identifiant : chaque frappe devient une"
     " ligne neuve"),

    ("guet.py",
     "    disparues = restants_a[len(restants_b):]",
     "    disparues = []",
     "une ligne supprimee ne disparait plus : le miroir garde un fantome"),

    ("guet.py",
     "            if self.calme >= self.silence:",
     "            if self.calme >= 1:",
     "la visite se ferme au premier releve calme : une pause pour reflechir"
     " devient une reprise, et l'extension s'effondre"),

    ("guet.py",
     "            self.visitee = remuees[-1]\n            self.calme = 0",
     "            self.visitee = remuees[-1]",
     "le compte de silence ne repart pas : la visite se ferme en pleine"
     " ecriture"),


    # ----------------------------------------------------- guet : nourrir
    # C'est ici que le guet remplace le pont, donc ici que les decisions du
    # pont doivent survivre. Aucune de ces regressions ne fait planter : la
    # forme pousse de travers, et personne ne le voit.
    ("guet.py",
     '            elif not compter_mots(f["ancien"]):',
     "            elif False:",
     "une ligne nee vide qui se remplit redevient une REPRISE : le premier mot"
     " de chaque ligne neuve cesse de compter, l'extension n'existe plus"),

    ("guet.py",
     '                v = paysage.absorber(f["texte"], f["style"], debit, jour,\n'
     "                                     heure, True)",
     '                v = paysage.absorber(f["texte"], f["style"], debit, jour,\n'
     "                                     heure, False)",
     "le drapeau de naissance se perd : une ligne qui commence comme une autre"
     " est declaree connue et le plant cesse de pousser"),

    ("guet.py",
     '                                      f["id"] in self.greffes, debit)',
     "                                      False, debit)",
     "decision 4 : un chapitre colle puis retravaille reste une greffe pour"
     " toujours — le defaut que le pont avait, remis en place"),

    ("guet.py",
     '            if v == "greffe":',
     '            if v == "ecriture":',
     "les greffes ne sont plus retenues : la conversion se declenche sur le"
     " mauvais verdict"),

    ("guet.py",
     "        borne = min(max(ecoule, INTERVALLE), PLAFOND_ECOULE)",
     "        borne = min(max(ecoule, 1), PLAFOND_ECOULE)",
     "le debit s'amplifie quand un releve arrive tot : quatre mots tapes"
     " deviennent un collage"),

    ("guet.py",
     '            if genre == "visite_finie":\n                paysage.quitter()',
     '            if genre == "visite_finie":\n                paysage.etat()',
     "la visite ne se ferme plus : plant.reprises ne monte jamais et l'element"
     " cesse de murir"),


    # ------------------------------------------- la porte derobee du collage
    ("paysage.py",
     "            if mots_par_intervalle > SEUIL_COLLAGE:\n"
     "                plant.greffes += 1\n"
     "                self._actif = e\n"
     "                return \"greffe\"",
     "            if False:\n"
     "                plant.greffes += 1\n"
     "                self._actif = e\n"
     "                return \"greffe\"",
     "decision 4 : coller dans la ligne qu'on ecrit compte tous les mots — le"
     " trou par lequel un vrai document est passe d'une tige a un arbre"),

    ("guet.py",
     "        borne = min(max(ecoule, INTERVALLE), PLAFOND_ECOULE)",
     "        borne = max(ecoule, INTERVALLE)",
     "le temps ecoule n'est plus plafonne : un collage vu une minute trop tard"
     " passe pour de l'ecriture"),

]


def _restaurer_les_restes(fichiers) -> None:
    """
    Une mutation laissee sur le disque est pire qu'un essai en echec.

    Le `finally` rend le fichier d'origine quand l'essai echoue ou leve. Il ne
    le rend pas si le processus est tue — une interruption, un delai depasse,
    une fenetre fermee. Le fichier mute reste alors en place, et la fois
    suivante TOUTE la batterie signale des regressions qui n'existent pas, dans
    des fichiers que personne n'a touches.

    On ecrit donc la copie a cote avant de muter, et on la relit au demarrage.
    """
    for f in fichiers:
        cote = os.path.join(RACINE, f + ".intact")
        if os.path.exists(cote):
            src = io.open(cote, encoding="utf-8").read()
            io.open(os.path.join(RACINE, f), "w", encoding="utf-8",
                    newline="\n").write(src)
            os.remove(cote)
            print(f"  (reste d'une execution interrompue : {f} restaure)")


def main() -> int:
    fichiers = {m[0] for m in MUTATIONS}
    _restaurer_les_restes(fichiers)
    # ⚠️ DEUX VERSIONS DE CHAQUE FICHIER. Git normalise les fins de ligne en
    # CRLF a chaque checkout sur Windows, et les motifs multi-lignes portent des
    # sauts simples : ils cessent alors de mordre, et le controle prealable
    # declare tout le fichier perime alors qu'aucun motif n'a vieilli. Un clone
    # frais du depot refuserait de lancer les mutations.
    #
    # On compare et on mute sur la copie en LF, et on restaure les OCTETS
    # D'ORIGINE : le fichier ressort exactement comme il etait entre.
    octets = {f: io.open(os.path.join(RACINE, f), encoding="utf-8").read()
              for f in fichiers}
    sauvegardes = {f: t.replace(chr(13) + chr(10), chr(10))
                   for f, t in octets.items()}
    # Les motifs d'abord, avant de toucher un seul fichier.
    #
    # Un motif perime se signalait « obsolete » en cours de route, apres avoir
    # laisse tourner la batterie complete pour toutes les mutations d'avant —
    # plusieurs minutes pour apprendre qu'une ligne du fichier avait bouge. Pire,
    # « obsolete » a l'air d'un probleme de maintenance et non d'une mutation qui
    # ne mord pas : c'est arrive deux fois de suite, et deux fois le diagnostic a
    # coute un passage entier. Le controle est instantane, il doit venir avant.
    perimes = [(f, lib) for f, vieux, _n, lib in MUTATIONS
               if vieux not in sauvegardes[f]]
    if perimes:
        print("=" * 78)
        print("MOTIFS PERIMES — rien n'a ete mute")
        print("=" * 78)
        for fichier, libelle in perimes:
            print(f"  {fichier} : {libelle}")
        print(f"\n{len(perimes)} motif(s) ne mordent plus sur la source.")
        return 2

    print("=" * 78)
    print("MUTATIONS — la batterie sait-elle echouer ?")
    print("=" * 78)
    attrapees, manquees = 0, []
    for fichier, vieux, neuf, libelle in MUTATIONS:
        chemin = os.path.join(RACINE, fichier)
        src = sauvegardes[fichier]
        # Plus besoin de tester le motif ici : le controle prealable a deja
        # rendu la main si l'un d'eux ne mordait plus.
        cote = chemin + ".intact"
        io.open(cote, "w", encoding="utf-8", newline="\n").write(octets[fichier])
        io.open(chemin, "w", encoding="utf-8", newline="\n").write(
            src.replace(vieux, neuf, 1))
        try:
            r = subprocess.run([sys.executable, "essais.py"], cwd=RACINE,
                               capture_output=True, text=True)
        finally:
            io.open(chemin, "w", encoding="utf-8",
                    newline="").write(octets[fichier])
            os.remove(cote)
        if r.returncode:
            attrapees += 1
            coupables = [l.strip()[6:].strip() for l in r.stdout.splitlines()
                         if l.strip().startswith("ECHEC")]
            print(f"  ok    {libelle}")
            for c in coupables:
                print(f"          rattrapee par : {c}")
        else:
            manquees.append((libelle, "aucun essai ne la voit"))
            print(f"  ECHAPPE {libelle}")

    print("=" * 78)
    print(f"{attrapees}/{len(MUTATIONS)} regressions detectees")
    for libelle, raison in manquees:
        print(f"  - {libelle}\n      {raison}")
    print("=" * 78)
    return 1 if manquees else 0


if __name__ == "__main__":
    sys.exit(main())
