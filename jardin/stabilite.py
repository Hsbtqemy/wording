"""
Test de stabilite : on rejoue l'ecriture mot a mot et on regarde a partir de
quand la famille arrete de changer d'avis.

C'est ce qui calibre PALIER_DIVERGENCE. Reveler trop tot, c'est risquer que
l'organisme se contredise sous les yeux de la personne.
"""

from pathlib import Path

from traits import extraire, revele, scores, NOMS


def parcours(texte: str, pas: int = 40) -> list[tuple[int, str, float]]:
    """Rejoue le texte par tranches de `pas` mots."""
    mots = texte.split()
    etapes = []
    for n in range(pas, len(mots) + pas, pas):
        partiel = " ".join(mots[:n])
        # On preserve les sauts de paragraphe presents dans la tranche.
        coupe = len(" ".join(mots[:n]))
        partiel = texte[:coupe + 1]
        t = extraire(partiel)
        if t.mots == 0:
            continue
        s = scores(t)
        classement = sorted(s.items(), key=lambda kv: kv[1], reverse=True)
        etapes.append((t.mots, classement[0][0], classement[0][1] - classement[1][1]))
    return etapes


def point_de_stabilite(etapes: list[tuple[int, str, float]]) -> int | None:
    """Nombre de mots a partir duquel la famille ne change plus."""
    if not etapes:
        return None
    finale = etapes[-1][1]
    dernier_desaccord = None
    for mots, famille, _ in etapes:
        if famille != finale:
            dernier_desaccord = mots
    if dernier_desaccord is None:
        return etapes[0][0]
    for mots, famille, _ in etapes:
        if mots > dernier_desaccord:
            return mots
    return None


def main() -> None:
    dossier = Path(__file__).parent / "echantillons"
    for f in sorted(dossier.glob("*.txt")):
        texte = f.read_text(encoding="utf-8")
        etapes = parcours(texte)
        stable = point_de_stabilite(etapes)
        print(f"\n=== {f.stem} ===")
        trace = []
        for mots, famille, marge in etapes:
            trace.append(f"{mots:>4}:{NOMS[famille][:4]}")
        # Affichage compact, 6 par ligne
        for i in range(0, len(trace), 6):
            print("   " + "  ".join(trace[i:i + 6]))
        if stable:
            print(f"   -> stable a partir de {stable} mots "
                  f"(marge finale {etapes[-1][2]:.3f})")
        else:
            print("   -> jamais stable")


if __name__ == "__main__":
    main()
