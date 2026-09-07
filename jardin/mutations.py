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
     r'SEPARATEURS = ("\r", "\x0b", "\n")',
     r'SEPARATEURS = ("\r", "\n")',
     "point 14 : le saut de ligne cesse de separer, 35 pages font un paragraphe"),

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
     "        self.lignes = decouper(texte)\n"
     "        self.ids = [self._neuf() for _ in self.lignes]",
     "        self.lignes = []\n"
     "        self.ids = []",
     "decision 11 : le capital de depart est declare NE, une these entiere"
     " pousse d'un coup a l'ouverture"),

    ("guet.py",
     '                faits.append({"type": "retouchee", "id": self.ids[i],\n'
     '                              "texte": nouvelles[j], "ancien": self.lignes[i]})',
     '                faits.append({"type": "retouchee", "id": self.ids[i],\n'
     '                              "texte": nouvelles[j], "ancien": None})',
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
    sauvegardes = {f: io.open(os.path.join(RACINE, f), encoding="utf-8").read()
                   for f in fichiers}
    print("=" * 78)
    print("MUTATIONS — la batterie sait-elle echouer ?")
    print("=" * 78)
    attrapees, manquees = 0, []
    for fichier, vieux, neuf, libelle in MUTATIONS:
        chemin = os.path.join(RACINE, fichier)
        src = sauvegardes[fichier]
        if vieux not in src:
            manquees.append((libelle, "motif introuvable — mutation obsolete"))
            print(f"  ????  {libelle}")
            continue
        cote = chemin + ".intact"
        io.open(cote, "w", encoding="utf-8", newline="\n").write(src)
        io.open(chemin, "w", encoding="utf-8", newline="\n").write(
            src.replace(vieux, neuf, 1))
        try:
            r = subprocess.run([sys.executable, "essais.py"], cwd=RACINE,
                               capture_output=True, text=True)
        finally:
            io.open(chemin, "w", encoding="utf-8", newline="\n").write(src)
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
