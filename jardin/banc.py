"""
Banc d'essai des decisions.

stabilite.py teste les bornes de normalisation sur quatre caricatures de 300
mots — chacune classee juste des 40 mots, alors que le palier qu'elle calibre
est a 800. Ce fichier teste autre chose : les mecanismes dont depend la
justesse du cadeau, et qui n'existaient nulle part avant paysage.py.

    essai 1  le registre        deplacer, fusionner, copier, supprimer
    essai 2  le collage         ecriture / greffe / conversion, dans cet ordre
    essai 3  le verrou          la plante ne devient pas une ville
    essai 4  les deux axes      tripoter ne fait pas pousser
    essai 5  l'echelle          une these de 146 000 mots
    essai 6  la performance     le budget de 100 ms par tick

    python banc.py
"""

from __future__ import annotations

import random
import time
from pathlib import Path

from traits import en_mots
from corpus import paragraphe, these, PROFILS
from paysage import (
    Paysage, empreinte, resume,
    MOTS_PAR_PLANT, SEUIL_COLLAGE, MOTS_MINIMUM_VERROU,
)

LARGEUR = 74


def titre(n, texte):
    print(f"\n{'=' * LARGEUR}\nESSAI {n} — {texte}\n{'=' * LARGEUR}")


def verdict(ok, texte):
    print(f"  [{'OK    ' if ok else 'ECHEC '}] {texte}")
    return ok


# --------------------------------------------------------------------------
# Essai 1 — le registre
# --------------------------------------------------------------------------
def essai_1():
    titre(1, "le registre : deplacer, fusionner, copier, supprimer")
    rng = random.Random(3)
    p = Paysage(identifiant="essai1")
    ecrits = [paragraphe(rng, "vegetal")[0] for _ in range(40)]
    for t in ecrits:
        p.absorber(t, jour=40)
    plant = p.segments[0]
    ref = (plant.nouveaux, plant.mots, plant.extension)
    print(f"  apres redaction        : {plant.nouveaux} paragraphes, {plant.mots} mots,"
          f" extension {plant.extension:.3f}")

    ok = True
    # Deplacement d'un fichier a l'autre : les memes paragraphes reapparaissent.
    for t in ecrits:
        p.absorber(t, jour=41)
    ok &= verdict((plant.nouveaux, plant.mots, plant.extension) == ref,
                  "deplacer d'un fichier a l'autre ne fait rien pousser")

    # Fusion de douze chapitres : tout arrive d'un bloc, tres vite.
    for t in ecrits:
        p.absorber(t, mots_par_intervalle=900, jour=42)
    ok &= verdict((plant.nouveaux, plant.greffes) == (ref[0], 0),
                  "fusionner douze chapitres n'est pas lu comme un collage geant")

    # Copier-coller interne.
    for t in ecrits[:10]:
        p.absorber(t, mots_par_intervalle=400, jour=42)
    ok &= verdict(plant.greffes == 0, "le copier-coller interne ne cree pas de greffe")

    # Suppression : le paysage ne bouge pas. Les mots coupes ont ete ecrits.
    avant = (plant.nouveaux, plant.mots)
    plant.textes = plant.textes[:5]
    ok &= verdict((plant.nouveaux, plant.mots) == avant,
                  "supprimer ne retire rien")

    # Correction typographique automatique de Word.
    n_avant = plant.nouveaux
    p.absorber(ecrits[0].replace("'", "’"), jour=43)
    ok &= verdict(plant.nouveaux == n_avant,
                  "l'apostrophe corrigee par Word ne cree pas un paragraphe neuf")
    return ok


# --------------------------------------------------------------------------
# Essai 2 — le collage
# --------------------------------------------------------------------------
def essai_2():
    titre(2, "le collage : ecriture, greffe, conversion")
    rng = random.Random(11)
    p = Paysage(identifiant="essai2")
    ok = True

    frappe = paragraphe(rng, "vegetal")[0]
    ok &= verdict(p.absorber(frappe, mots_par_intervalle=6) == "ecriture",
                  f"frappe normale (6 mots / 2 s) -> ecriture")

    colle = paragraphe(rng, "abstrait")[0]
    ok &= verdict(p.absorber(colle, mots_par_intervalle=80) == "greffe",
                  f"paragraphe colle (80 mots / 2 s, > {SEUIL_COLLAGE}) -> greffe")
    ok &= verdict(p.segments[0].greffes == 1, "la greffe est en attente")

    # Une citation ne se retouche jamais : elle reste greffe pour toujours.
    # Un brouillon rapporte d'ailleurs se retravaille : il se convertit seul.
    retravaille = colle + " " + paragraphe(rng, "abstrait")[0]
    ok &= verdict(p.retoucher(colle, retravaille, etait_greffe=True) == "conversion",
                  "greffe retouchee -> ecriture (le brouillon se convertit seul)")
    ok &= verdict(p.segments[0].greffes == 0, "la greffe convertie n'est plus en attente")

    cit = paragraphe(rng, "abstrait")[0]
    ok &= verdict(p.absorber(cit, style="Citation", mots_par_intervalle=99) == "ignoree",
                  "un paragraphe en style Citation ne compte jamais")

    # Le record du monde de frappe est a 140 mots/minute, soit ~5 mots / 2 s.
    dicte = paragraphe(rng, "vegetal")[0]
    ok &= verdict(p.absorber(dicte, mots_par_intervalle=SEUIL_COLLAGE - 1) == "ecriture",
                  "la dictee vocale (jusqu'a 420 mots/min) reste de l'ecriture")
    return ok


# --------------------------------------------------------------------------
# Essai 3 — le verrou par segment
# --------------------------------------------------------------------------
def essai_3():
    titre(3, "le verrou : la plante ne devient pas une ville")
    rng = random.Random(5)
    p = Paysage(identifiant="essai3")

    # Exactement le scenario de la decision 5 : de la prose, puis un rapport
    # structure. Sans verrou par segment, la famille bascule vers 500 mots.
    # ⚠️ 1 100 MOTS CHACUN, ET LA SOMME DOIT TENIR DANS UN PLANT.
    #
    # C'etait 3 000 et 3 000, quand un plant en valait 5 000 : le rapport
    # tombait donc pour moitie dans le plant 0, et la derive s'y lisait. A
    # 2 500 mots par plant, le plant 0 se fermait avant la premiere ligne du
    # rapport — l'essai ne testait plus le verrou, il testait le debordement,
    # et il a echoue en annoncant une influence vide.
    #
    # Ce que la decision 5 demande de montrer, c'est UN MEME PLANT qui recoit
    # les deux textes et ne renie pas le premier. Les deux moities doivent donc
    # rentrer dans un plant, quel que soit le nombre de mots qu'il vaut.
    # Les deux longueurs sont des FRACTIONS DE PLANT, et chacune porte une des
    # trois choses que l'essai doit montrer. La prose remplit deux cinquiemes
    # du plant : assez pour verrouiller, pas assez pour le fermer. Le rapport
    # en vaut un entier : il finit donc de remplir le plant 0 — c'est la que la
    # derive se lit — puis DEBORDE, et la ville pousse a cote en plant neuf.
    prose_cible = MOTS_PAR_PLANT * 2 // 5
    rapport_cible = MOTS_PAR_PLANT
    prose = []
    while sum(len(en_mots(t)) for t in prose) < prose_cible:
        prose.append(paragraphe(rng, "vegetal")[0])
    rapport = []
    while sum(len(en_mots(t)) for t in rapport) < rapport_cible:
        rapport.append(paragraphe(rng, "architecture")[0])

    jalons = []
    for t in prose:
        p.absorber(t, jour=30)
    plant = p.segments[0]
    jalons.append((f"apres {prose_cible} mots de prose", plant.famille, plant.mots))
    famille_verrouillee = plant.famille

    for t in rapport:
        p.absorber(t, style="Normal", jour=200)
    jalons.append((f"apres {rapport_cible} mots de rapport", plant.famille, plant.mots))

    for lab, fam, mots in jalons:
        print(f"  {lab:<30} plant 0 : {str(fam).upper():<13} ({mots} mots)")

    ok = verdict(famille_verrouillee == "vegetal",
                 "la prose verrouille le plant 0 sur Vegetal")
    ok &= verdict(plant.famille == "vegetal",
                  "le rapport structure ne retourne pas le plant 0 en ville")
    infl = plant.influences()
    ok &= verdict("architecture" in infl,
                  f"le rapport se lit en derive, pas en reniement : {infl}")
    ok &= verdict(len(p.segments) > 1,
                  f"la ville pousse a cote, en plant neuf ({len(p.segments)} plants)")
    print(resume(p))
    return ok


# --------------------------------------------------------------------------
# Essai 4 — les deux axes
# --------------------------------------------------------------------------
def essai_4():
    titre(4, "les deux axes : tripoter ne fait pas pousser")
    rng = random.Random(9)
    p = Paysage(identifiant="essai4")
    base = [paragraphe(rng, "vegetal")[0] for _ in range(20)]
    for t in base:
        p.absorber(t, jour=60)
    plant = p.segments[0]
    e0, m0 = plant.extension, plant.maturite
    print(f"  20 paragraphes ecrits  : extension {e0:.3f}  maturite {m0:.3f}")

    # Quarante reprises du meme paragraphe, quarante visites distinctes :
    # on quitte le paragraphe entre chacune, comme le curseur le ferait.
    p.quitter()
    courant = base[0]
    for i in range(40):
        suivant = courant + " " + paragraphe(rng, "vegetal")[0]
        p.retoucher(courant, suivant, jour=60)
        p.quitter()
        courant = suivant
    e1, m1 = plant.extension, plant.maturite
    print(f"  + 40 reprises du meme  : extension {e1:.3f}  maturite {m1:.3f}")

    ok = verdict(abs(e1 - e0) < 1e-9,
                 "quarante reprises ne font pas grandir la forme")
    ok &= verdict(plant.reprises == 40,
                  f"une reprise par visite, pas par frappe ({plant.reprises})")
    ok &= verdict(m1 > m0 + 0.3,
                  "quarante reprises epaississent l'element")
    ok &= verdict(m1 < 1.0, f"la maturite sature au lieu de s'emballer ({m1:.3f})")

    # La premiere redaction d'un paragraphe, elle, doit faire pousser :
    # meme suite d'evenements que la reprise, sens oppose.
    q = Paysage(identifiant="frappe")
    debut = paragraphe(rng, "vegetal")[0]
    q.absorber(debut, mots_par_intervalle=5)
    courant, verdicts = debut, []
    for _ in range(12):
        suivant = courant + " " + paragraphe(rng, "vegetal")[0]
        verdicts.append(q.retoucher(courant, suivant))
        courant = suivant
    ok &= verdict(set(verdicts) == {"frappe"} and q.segments[0].reprises == 0,
                  "taper un paragraphe pour la premiere fois est de l'ecriture,"
                  " pas une reprise")
    ok &= verdict(q.segments[0].extension > 0.1,
                  f"et cette frappe fait pousser ({q.segments[0].extension:.2f})")

    # Vingt paragraphes neufs, en face. Ils peuvent atterrir sur le plant
    # suivant si celui-ci est plein : c'est la croissance du PAYSAGE qu'on
    # mesure, pas celle d'un plant en particulier.
    total = sum(s.extension for s in p.segments)
    for t in [paragraphe(rng, "vegetal")[0] for _ in range(20)]:
        p.absorber(t, jour=61)
    total_apres = sum(s.extension for s in p.segments)
    print(f"  + 20 paragraphes neufs : extension du paysage"
          f" {total:.3f} -> {total_apres:.3f} sur {len(p.segments)} plant(s)")
    ok &= verdict(total_apres > total, "ecrire, en face, fait grandir le paysage")
    return ok


# --------------------------------------------------------------------------
# Essai 5 — l'echelle
# --------------------------------------------------------------------------
def essai_5(doc):
    titre(5, "l'echelle : une these de 146 000 mots")
    p = Paysage(identifiant="essai5")
    for texte, style, jour, heure in doc:
        p.absorber(texte, style=style, jour=jour, heure=heure, mots_par_intervalle=7)

    mots = sum(s.mots for s in p.segments)
    plants = len(p.segments)
    verrouilles = sum(1 for s in p.segments if s.verrouille)
    familles = {}
    for s in p.segments:
        if s.verrouille:
            familles[s.famille] = familles.get(s.famille, 0) + 1

    octets = len(p.serialiser().encode("utf-8"))
    registre_octets = len(p.registre) * 13   # 12 hex + separateur

    mpp = mots / max(len(doc), 1)
    print(f"  {mots} mots, {len(doc)} paragraphes ({mpp:.0f} mots/paragraphe),"
          f" {plants} plants")
    print(f"  verrouilles : {verrouilles}/{plants}   -> {familles}")
    print(f"  registre    : {len(p.registre)} empreintes, {registre_octets/1024:.0f} Ko")
    print(f"  etat serialise complet : {octets/1024:.0f} Ko")

    ok = verdict(len(p.registre) == len({empreinte(t) for t, *_ in doc}),
                 "aucune collision d'empreinte sur la these entiere")
    # La decision 6 annonce 27 plants pour 137 500 mots, et depuis que le plant
    # se mesure en MOTS SEULS ce chiffre ne depend plus du style : quelqu'un qui
    # ecrit en lignes d'une phrase obtient le meme paysage que quelqu'un qui
    # ecrit des paragraphes de 250 mots. C'etait tout l'objet du changement —
    # avec l'ancien plafond en paragraphes, un vrai document en donnait 250.
    attendu = mots / MOTS_PAR_PLANT
    ok &= verdict(abs(plants - attendu) / attendu < 0.25,
                  f"le nombre de plants suit les mots ecrits"
                  f" ({plants} obtenus, {attendu:.0f} attendus)")
    # ⚠️ UNE REGLE, PAS UN EFFECTIF. C'etait « verrouilles >= plants - 2 »,
    # qui tenait tant qu'il y avait trente-deux plants et huit frontieres de
    # chapitre. A cinquante-neuf plants les moignons de fin de chapitre sont
    # plus nombreux — trois au lieu de deux — et l'essai a echoue sans qu'aucune
    # regle soit violee. Le nombre suivait la constante, pas le comportement.
    #
    # Ce que l'essai veut dire ne depend d'aucun effectif : un plant qui a
    # atteint le seuil du verrou A une famille. Ceux qui n'en ont pas sont les
    # moignons, et c'est leur definition meme.
    orphelins = [s for s in p.segments
                 if s.mots >= MOTS_MINIMUM_VERROU and not s.verrouille]
    ok &= verdict(not orphelins,
                  f"tous les plants pleins ont trouve leur famille"
                  f" ({len(orphelins)} au-dela de {MOTS_MINIMUM_VERROU} mots"
                  f" sans famille)")
    ok &= verdict(len(familles) >= 3,
                  "le paysage est melange, pas monochrome")
    ok &= verdict(max(s.mots for s in p.segments) <= MOTS_PAR_PLANT + 400,
                  f"aucun plant ne depasse le cycle de {MOTS_PAR_PLANT} mots")
    print()
    print(resume(p))
    return ok, p


# --------------------------------------------------------------------------
# Essai 6 — la performance
# --------------------------------------------------------------------------
def essai_6(doc):
    titre(6, "la performance : le budget de 100 ms par tick")
    from traits import extraire

    texte_complet = "\n\n".join(t for t, *_ in doc)
    t0 = time.perf_counter()
    tr = extraire(texte_complet)
    t_complet = (time.perf_counter() - t0) * 1000

    segment = []
    for t, *_ in doc:
        segment.append(t)
        if sum(len(en_mots(x)) for x in segment) > MOTS_PAR_PLANT:
            break
    texte_segment = "\n\n".join(segment)
    t0 = time.perf_counter()
    extraire(texte_segment)
    t_segment = (time.perf_counter() - t0) * 1000

    un = doc[10][0]
    t0 = time.perf_counter()
    for _ in range(200):
        extraire(un)
    t_para = (time.perf_counter() - t0) * 1000 / 200

    p = Paysage(identifiant="essai6")
    t0 = time.perf_counter()
    for texte, style, jour, heure in doc[:400]:
        p.absorber(texte, style=style, jour=jour, heure=heure, mots_par_intervalle=7)
    t_tick = (time.perf_counter() - t0) * 1000 / 400

    print(f"  extraction complete ({tr.mots} mots) : {t_complet:>8.0f} ms")
    print(f"  segment actif (2 500 mots)          : {t_segment:>8.1f} ms")
    print(f"  un paragraphe                       : {t_para:>8.2f} ms")
    print(f"  un tick reel (absorber + relecture) : {t_tick:>8.2f} ms")

    ok = verdict(t_tick < 100, "le tick tient dans le budget de 100 ms")
    ok &= verdict(t_segment < 100, "une relecture de segment tient dans le budget")
    return ok


# --------------------------------------------------------------------------
def main():
    print("Banc d'essai des decisions — paysage.py")
    doc = these()
    resultats = [essai_1(), essai_2(), essai_3(), essai_4()]
    ok5, _ = essai_5(doc)
    resultats.append(ok5)
    resultats.append(essai_6(doc))
    print(f"\n{'=' * LARGEUR}")
    print(f"{sum(1 for r in resultats if r)}/{len(resultats)} essais passes")
    print("=" * LARGEUR)


if __name__ == "__main__":
    main()
