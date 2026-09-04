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
]


def main() -> int:
    sauvegardes = {f: io.open(os.path.join(RACINE, f), encoding="utf-8").read()
                   for f in {m[0] for m in MUTATIONS}}
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
        io.open(chemin, "w", encoding="utf-8", newline="\n").write(
            src.replace(vieux, neuf, 1))
        try:
            r = subprocess.run([sys.executable, "essais.py"], cwd=RACINE,
                               capture_output=True, text=True)
        finally:
            io.open(chemin, "w", encoding="utf-8", newline="\n").write(src)
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
