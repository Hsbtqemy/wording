# -*- coding: utf-8 -*-
"""
Assemble la page de verification : les planches inline, plus la sortie des
essais et du test de mutation.

Les SVG sont inlines plutot que les PNG. Une planche de 4 800 px reste alors
nette et defile a taille reelle, au lieu d'etre ecrasee dans la largeur de la
page — et le fichier reste plus leger que les images.

Chaque planche est adossee a une entree de DECISIONS.md, et celles de la
section « corrige » montrent l'avant ET l'apres : une planche qui ne montre
que l'etat corrige prouve que le mecanisme marche, pas que la correction
change quelque chose.

    python page.py    ->  planches.html
"""
import io
import re
import subprocess
import sys
import os

JARDIN = os.path.dirname(os.path.abspath(__file__))
SORTIE = os.path.join(JARDIN, "planches.html")

PLANCHES = [
    ("etat", "planche_etat.svg", "L'état", "décision 8",
     "Les quatre familles, à l'état des décisions",
     "La même primitive segment dans les quatre, et deux axes qui ne se "
     "confondent pas : de gauche à droite ça pousse, de haut en bas ça mûrit. "
     "C'était la première fois qu'elles existaient ensemble à jour — le code "
     "avait divergé en versions parallèles dont aucune n'était complète.", None),

    ("etat", "planche_saisons_v7.svg", "L'état", "décision 9",
     "Cinq palettes, dont une qui n'appartient à aucune saison",
     "Regarde la colonne 3 h du matin. En v5 c'était un bleu-gris à deux doigts "
     "de l'hiver, et l'easter egg ressemblait à une décoloration.",
     "La nuit est à 38 d'une saison, quand deux saisons se frôlent à 20."),

    ("corrige", "planche_feuillage.svg", "Corrigé", "point ouvert 3",
     "Le plafond du feuillage doit être global, pas local",
     "À extension 1,00 : en haut la couronne est un aplat qui masque "
     "l'anastomose, en bas les branches restent lisibles. Le correctif v4 "
     "bornait chaque bouquet — mais leur nombre croît en "
     "2<sup>profondeur</sup>.", None),

    ("corrige", "planche_main.svg", "Corrigé", "point ouvert 4",
     "Les lettres ne viennent plus d'une grille",
     "Le même mot, trois tirages. En haut le tracé v6 : les trois M ont "
     "exactement le même angle. En bas les sommets sont déplacés, donc l'apex "
     "penche différemment à chaque fois. Les polylignes n'y suffisaient pas — "
     "il fallait bouger les sommets, pas les traits.", None),

    ("corrige", "planche_dates.svg", "Corrigé", "point ouvert 7",
     "La ville doit porter de vraies dates",
     "La colonne du milieu affiche quatre saisons dans un seul chapitre : le "
     "décalage jour + rang × 47 de la v4, inventé de toutes pièces. À droite, "
     "la vraie dispersion des dates du plant, de février à mai.", None),

    ("corrige", "planche_membres.svg", "Corrigé", "point ouvert 6",
     "Les membres bornés à la largeur du corps",
     "En haut, les trois bêtes ont presque la même taille — une gracile qui "
     "porte les pattes d'une massive. En bas, la fourchette est réelle.",
     "Rapport massif/gracile : 1,00 avant, 3,48 après."),

    ("neuf", "planche_germination.svg", "Neuf", "décision 6",
     "Le germe se dessine",
     "À 60 et 190 mots les cinq lignes sont identiques : aucune tendance. "
     "Ensuite chacune penche selon ce que fait sa famille — elle bifurque, "
     "elle s'empile, elle ondule, elle se referme. Aucune ne produit un objet "
     "reconnaissable, donc un changement de pressentie ne mentirait pas.",
     "16 % de chaque cycle, vingt-sept fois sur une thèse."),

    ("neuf", "planche_volet.svg", "Neuf", "décision 14",
     "Le volet n'est jamais vide",
     "Cinq instants autour d'une naissance de plant, de 22 à 2 639 mots. Le "
     "précédent sort par la gauche pendant que le nouveau germe. Le plant en "
     "cours est posé aux deux tiers à droite, pas au centre.", None),

    ("neuf", "planche_apercu.svg", "Neuf", "décision 14",
     "La vue d'ensemble compresse en groupant, pas en réduisant",
     "Une thèse de 146 000 mots : 49 plants, 4 parcelles. Les plants d'un même "
     "chapitre se serrent et se recouvrent — ils font un relief. La couleur "
     "dérive avec les saisons à l'intérieur de chaque massif.",
     "12 803 px en bande linéaire contre 4 826 en massifs (38 %)."),

    ("neuf", "planche_paysage.svg", "Neuf", "décision 14",
     "La profondeur porte la maturité",
     "La même composition en bande, sur une rédaction plus courte. Les "
     "chapitres les plus retravaillés viennent devant ; ceux posés d'un jet "
     "restent au fond. Le fond s'éloigne, il ne fane pas — le point 1 interdit "
     "que quoi que ce soit recule.", None),
]

NOTES = {
    "planche_membres.svg":
        "Cette planche a été refaite deux fois. La première ne montrait que "
        "l'état corrigé : elle prouvait que le curseur fonctionne, pas que la "
        "correction change quelque chose. La deuxième mettait chaque case à "
        "l'échelle indépendamment — une bête plus grande était donc réduite "
        "pour tenir, ce qui gommait justement la différence à montrer. C'est "
        "le même défaut que celui trouvé dans <code>composer()</code>.",
}


def svg_de(nom):
    src = io.open(os.path.join(JARDIN, nom), encoding="utf-8").read()
    m = re.search(r'viewBox="([\d.\-]+) ([\d.\-]+) ([\d.]+) ([\d.]+)"', src)
    w, h = float(m.group(3)), float(m.group(4))
    src = src.replace('<svg xmlns="http://www.w3.org/2000/svg" ', '<svg ', 1)
    ratio = w / h
    if ratio > 3.6:
        # Trop large pour tenir : on fixe la hauteur et on laisse defiler.
        hauteur = 300
        src = src.replace('width="100%"',
                          f'height="{hauteur}" width="{w / h * hauteur:.0f}"', 1)
        return src, True
    return src.replace('width="100%"', 'width="100%" height="auto"', 1), False


essais = subprocess.run([sys.executable, "essais.py"], cwd=JARDIN,
                        capture_output=True, text=True)
mutations = subprocess.run([sys.executable, "mutations.py"], cwd=JARDIN,
                           capture_output=True, text=True)


def nettoyer(t):
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return t.replace("\ufffd", "—")


GROUPES = [
    ("etat", "L'état", "Ce que le système dessine aujourd'hui."),
    ("corrige", "Ce qui a été corrigé",
     "Chaque planche montre l'avant et l'après. Sans les deux, on ne peut pas "
     "juger un correctif."),
    ("neuf", "Ce qui est neuf",
     "Le germe, le volet, la composition — ce que rien ne dessinait avant."),
]

out = []
out.append("""<title>Planches du paysage</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,300;0,400;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{
  --papier:#faf8f4; --carte:#f2efe8; --encre:#2c3230; --doux:#6b6560;
  --filet:#ddd7cb; --accent:#43596b; --accent-doux:#7d90a0;
  --mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  --serif:"Spectral",Georgia,"Times New Roman",serif;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --papier:#171b1a; --carte:#1f2422; --encre:#e6e2d9; --doux:#9c968c;
    --filet:#333b38; --accent:#9fb3ba; --accent-doux:#6e8fa0;
  }
}
:root[data-theme="dark"]{
  --papier:#171b1a; --carte:#1f2422; --encre:#e6e2d9; --doux:#9c968c;
  --filet:#333b38; --accent:#9fb3ba; --accent-doux:#6e8fa0;
}
*{box-sizing:border-box}
body{background:var(--papier);color:var(--encre);font-family:var(--serif);
  font-size:17px;line-height:1.62;margin:0;-webkit-font-smoothing:antialiased}
.enveloppe{max-width:1180px;margin:0 auto;padding:0 28px 120px}
a{color:var(--accent)}
code{font-family:var(--mono);font-size:.88em;background:var(--carte);
  padding:.1em .35em;border-radius:2px}

header{padding:72px 0 40px;border-bottom:1px solid var(--filet)}
h1{font-size:clamp(34px,5vw,52px);font-weight:600;line-height:1.06;margin:0;
  letter-spacing:-.018em;text-wrap:balance}
.chapo{max-width:60ch;color:var(--doux);margin:18px 0 0;font-size:18px}
.compteurs{display:flex;flex-wrap:wrap;gap:0;margin:34px 0 0;
  border:1px solid var(--filet);border-radius:3px;overflow:hidden}
.compteur{flex:1 1 190px;padding:16px 20px;border-right:1px solid var(--filet)}
.compteur:last-child{border-right:0}
.compteur b{display:block;font-family:var(--mono);font-size:23px;
  font-weight:500;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.compteur span{display:block;font-family:var(--mono);font-size:11px;
  text-transform:uppercase;letter-spacing:.09em;color:var(--doux);margin-top:5px}

section.groupe{margin:72px 0 0}
.titre-groupe{display:flex;align-items:baseline;gap:16px;
  border-bottom:1px solid var(--filet);padding-bottom:10px}
.titre-groupe h2{font-size:24px;font-weight:600;margin:0;letter-spacing:-.01em}
.titre-groupe p{margin:0;color:var(--doux);font-size:15px;max-width:52ch}

article.planche{margin:44px 0 0;padding:0 0 8px}
.entete{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:20px;
  align-items:start;margin-bottom:16px}
.reference{font-family:var(--mono);font-size:11px;letter-spacing:.09em;
  text-transform:uppercase;color:var(--accent);white-space:nowrap;
  border:1px solid var(--filet);border-radius:2px;padding:4px 9px}
h3{font-size:21px;font-weight:600;margin:0 0 6px;letter-spacing:-.008em;
  text-wrap:balance}
.regarder{margin:0;color:var(--doux);max-width:68ch;font-size:16px}
.mesure{margin:10px 0 0;font-family:var(--mono);font-size:13px;
  color:var(--encre);font-variant-numeric:tabular-nums}
.mesure::before{content:"→ ";color:var(--accent-doux)}
.note{margin:12px 0 0;padding:12px 15px;background:var(--carte);
  border-left:2px solid var(--accent-doux);font-size:15px;color:var(--doux);
  max-width:72ch}

.cadre{border:1px solid var(--filet);border-radius:3px;background:#faf8f4;
  overflow-x:auto;overflow-y:hidden;line-height:0}
.cadre.large{padding:0}
.cadre svg{display:block;max-width:none}
.cadre:not(.large) svg{width:100%;height:auto}
sup{font-size:.72em;line-height:0}
.legende{font-family:var(--mono);font-size:11px;color:var(--doux);
  margin:7px 0 0;letter-spacing:.03em}

pre{font-family:var(--mono);font-size:12.5px;line-height:1.55;
  background:var(--carte);border:1px solid var(--filet);border-radius:3px;
  padding:18px 20px;overflow-x:auto;margin:0;color:var(--encre)}
.deux{display:grid;grid-template-columns:1fr;gap:22px;margin-top:26px}
@media(min-width:900px){.deux{grid-template-columns:1fr 1fr}}
.bloc h4{font-family:var(--mono);font-size:11px;text-transform:uppercase;
  letter-spacing:.09em;color:var(--doux);margin:0 0 9px;font-weight:500}
footer{margin-top:80px;padding-top:22px;border-top:1px solid var(--filet);
  color:var(--doux);font-size:15px}
@media(prefers-reduced-motion:no-preference){
  .cadre{scroll-behavior:smooth}
}
</style>

<div class="enveloppe">
<header>
  <h1>Planches du paysage</h1>
  <p class="chapo">Dix planches, chacune adossée à une entrée du journal des
  décisions. Celles de la section « corrigé » montrent l'avant et l'après :
  sans les deux, on ne peut pas juger un correctif. Les mesures sous chaque
  planche sont reproductibles depuis le dépôt.</p>
  <div class="compteurs">
    <div class="compteur"><b>30</b><span>assertions, essais.py</span></div>
    <div class="compteur"><b>8 / 8</b><span>régressions détectées</span></div>
    <div class="compteur"><b>10</b><span>planches</span></div>
    <div class="compteur"><b>705 → 63 ms</b><span>MATTR sur 146 000 mots</span></div>
  </div>
</header>
""")

for cle, titre, sous in GROUPES:
    out.append(f'<section class="groupe"><div class="titre-groupe">'
               f'<h2>{titre}</h2><p>{sous}</p></div>')
    for g, fichier, _sec, ref, claim, regarder, mesure in PLANCHES:
        if g != cle:
            continue
        svg, large = svg_de(fichier)
        out.append('<article class="planche"><div class="entete"><div>')
        out.append(f'<h3>{claim}</h3><p class="regarder">{regarder}</p>')
        if mesure:
            out.append(f'<p class="mesure">{mesure}</p>')
        out.append(f'</div><div class="reference">{ref}</div></div>')
        if fichier in NOTES:
            out.append(f'<p class="note">{NOTES[fichier]}</p>')
        out.append(f'<div class="cadre{" large" if large else ""}">{svg}</div>')
        out.append(f'<p class="legende">{fichier.replace(".svg", ".png")}'
                   f'{" — défile horizontalement" if large else ""}</p>')
        out.append('</article>')
    out.append('</section>')

out.append(f'''<section class="groupe">
<div class="titre-groupe"><h2>Les essais</h2>
<p>Avant, chaque module imprimait ses résultats et sortait avec le code 0 quoi
qu'il arrive. Une régression n'était détectable qu'en lisant la sortie.</p></div>
<div class="deux">
  <div class="bloc"><h4>python essais.py</h4><pre>{nettoyer(essais.stdout)}</pre></div>
  <div class="bloc"><h4>python mutations.py</h4><pre>{nettoyer(mutations.stdout)}</pre>
  <p class="regarder" style="margin-top:14px">Une batterie qui passe ne prouve
  rien tant qu'on n'a pas montré qu'elle sait échouer. <code>mutations.py</code>
  réintroduit huit régressions réellement commises pendant la conception et
  vérifie qu'elles sont rattrapées. Au premier passage : 5 sur 7, et les deux
  évasions étaient des défauts des essais, pas du code.</p></div>
</div>
</section>

<footer>Tout se régénère depuis le dépôt :
<code>python grammaire.py</code>, <code>python composition.py</code>,
<code>python message.py</code> écrivent les SVG ;
<code>python essais.py</code> et <code>python mutations.py</code> rendent
les deux sorties ci-dessus.</footer>
</div>''')

io.open(SORTIE, "w", encoding="utf-8", newline="\n").write("\n".join(out))
print(f"page ecrite : {os.path.getsize(SORTIE)/1024:.0f} Ko")
print(f"essais   : code {essais.returncode}")
print(f"mutations: code {mutations.returncode}")
