"""
Les trois icones du ruban, dessinees par la grammaire elle-meme.

    python addin/icones.py

Le germe, et pas un arbre : c'est la forme qui appartient aux quatre familles a
la fois, donc la seule qui puisse representer le paysage sans en choisir une.
C'est aussi ce qu'on voit le premier jour.

Produit icone-16, icone-32 et icone-80, aux tailles que le manifeste demande.
Rasterise avec Chrome sans fenetre, comme les planches — le projet n'ajoute
aucune dependance, et un navigateur est deja la.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(ICI), "jardin"))

from grammaire import Toile, germe, Teinte, FOND       # noqa: E402

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TAILLES = (16, 32, 80)


def dessin(cote: int) -> str:
    """Le germe, cadre dans un carre."""
    t = Toile()
    # Le germe AVEC son inflexion vegetale, pas la chaine nue.
    #
    # A inflexion nulle, le germe est une chaine droite — c'est-a-dire, a seize
    # pixels, un trait vertical qu'on ne distingue pas d'une barre. L'icone doit
    # se lire ; elle montre donc ce que le volet montre les premiers jours,
    # quand une tendance commence a paraitre. La regle du point 6 — l'inflexion
    # ne doit jamais produire un objet reconnaissable — porte sur ce que la
    # personne voit pousser, pas sur la vignette du ruban.
    germe(t, 0.85, 0.75, "vegetal", 20240, Teinte.du_jour(110, 14, 0.7))

    # CADRE SUR LA TETE, pas sur la figure entiere. Le germe fait dix fois plus
    # haut que large : loge dans un carre, il devient un sliver de trois pixels
    # qu'on ne distingue pas d'une barre. On cadre donc sur sa bifurcation — ce
    # qui est aussi la chose juste a montrer, « la primitive avant son
    # assemblage ». Meme raisonnement que la vue de travail : c'est le cadre qui
    # fait le sujet, pas un autre dessin.
    x0, y0, x1, y1 = t.bbox()
    cx = (x0 + x1) / 2
    fenetre = (x1 - x0) * 1.9
    t.cadre = (cx - fenetre / 2, y0 - fenetre * 0.06,
               cx + fenetre / 2, y0 - fenetre * 0.06 + fenetre)

    # ON DESSINE TOUJOURS A 160, et c'est le navigateur qui reduit.
    #
    # Toile.svg calcule l'epaisseur des traits comme EPAISSEUR / max(k, 0.35) :
    # en dessous de k = 0,35 l'epaisseur cesse de compenser, donc plus la case
    # est petite, plus le trait rendu est fin. Dessine directement a 32 pixels,
    # le germe devenait un cheveu presque invisible — 164 octets de PNG. A 160
    # les traits sont francs, et la reduction du navigateur les garde.
    L = 160
    marge = L * 0.10
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{cote}" '
            f'height="{cote}" viewBox="0 0 {L} {L}">'
            f'<rect width="{L}" height="{L}" fill="{FOND}"/>'
            f'{t.svg(marge, marge, L - 2 * marge, L - 2 * marge)}</svg>')


def main() -> int:
    if not os.path.exists(CHROME):
        print(f"Chrome introuvable : {CHROME}")
        return 2
    dossier = tempfile.mkdtemp()
    for cote in TAILLES:
        svg = os.path.join(dossier, f"i{cote}.svg")
        with open(svg, "w", encoding="utf-8") as f:
            f.write(dessin(cote))
        sortie = os.path.join(ICI, f"icone-{cote}.png")
        subprocess.run([
            CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
            f"--screenshot={sortie}", f"--window-size={cote},{cote}",
            "--default-background-color=00000000",
            "file:///" + svg.replace("\\", "/"),
        ], capture_output=True)
        etat = "ok" if os.path.exists(sortie) else "MANQUE"
        poids = os.path.getsize(sortie) if os.path.exists(sortie) else 0
        print(f"  icone-{cote}.png  {poids:>6} octets  {etat}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
