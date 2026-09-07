# Installer le paysage

Une seule chose à faire : déposer le manifeste. L'hébergement est déjà en
place.

---

## L'hébergement — déjà fait

Word refuse de charger un add-in autrement : le manifeste pointe vers une URL,
même si tout le code est local et sans dépendance.

C'est **GitHub Pages**, servi depuis ce dépôt :

```
https://hsbtqemy.github.io/wording/addin/volet.html
```

Gratuit tant que le dépôt est public, HTTPS par défaut — Word refuse le HTTP en
clair, y compris en local. Un `.nojekyll` à la racine empêche Jekyll de traiter
le dépôt et d'escamoter des fichiers.

Chaque `git push` sur `main` republie le site, avec une minute de délai et un
cache de dix minutes : après une modification, Word peut encore servir l'ancien
fichier un moment.

Cette adresse est aussi l'identité du magasin : le paysage vit dans le
`localStorage`, qui est indexé par *origine*. **Ce n'est plus une dépendance** —
chaque document garde une copie de son paysage dans le `.docx` lui-même
(décision 16). Changer d'hébergeur, changer de machine, vider les données de
site : le paysage revient du fichier à l'ouverture suivante.

⚠️ Il ne revient que d'un document où l'on a **écrit avec le volet ouvert** : la
copie part quand le paysage pousse, pas avant. Un document qu'on n'a fait
qu'ouvrir ne porte rien — c'est délibéré, il ne doit pas ressortir « modifié ».

## Charger le manifeste dans Word

Rien à modifier dans `manifest.xml` : les URL y sont déjà. Et où qu'on le
dépose, **le code vient toujours de GitHub Pages** — le manifeste ne fait que
dire à Word où aller le chercher. C'est un fichier XML de 5,6 Ko, rien de plus.

### Le plus rapide, pour un premier coup d'œil : Word sur le web

Aucun partage, aucun catalogue, aucune manipulation système. Ouvrir le document
depuis OneDrive, puis *Insertion → Compléments → Mes compléments →
**Charger mon complément*** et désigner `manifest.xml`.

Ça suffit à voir si le volet s'ouvre et si la forme se dessine. Mais **le vrai
essai reste le bureau** : c'est là qu'on écrit, et les quatre points de la
section suivante portent tous sur des comportements de frappe. Si la version du
web ne suffit pas, le volet le dira lui-même — il vérifie WordApi 1.6 et
explique ce qui manque au lieu de rester noir.

### Mac

Déposer `manifest.xml` dans :

```
~/Library/Containers/com.microsoft.Word/Data/Documents/wef
```

puis redémarrer Word. Le bouton apparaît dans l'onglet Accueil.

### Windows

⚠️ **Word n'accepte pas un chemin local** dans un catalogue de confiance :
`C:\Paysage` est refusé sans explication. Il lui faut un **chemin réseau UNC** —
`\\NOM-DU-PC\Paysage` — même quand le dossier est sur sa propre machine.
« Partager le dossier » ne veut dire rien d'autre que : créer un partage
Windows, ce qui fait apparaître ce chemin-là.

1. Un dossier, disons `C:\Paysage`, avec `manifest.xml` dedans.
2. Clic droit → **Propriétés** → onglet **Partage** → **Partage avancé…** →
   cocher **Partager ce dossier** → OK. La fenêtre affiche alors le **chemin
   réseau** : `\\NOM-DU-PC\Paysage`. C'est celui-là qu'il faut, pas `C:\Paysage`.
3. Word → *Fichier → Options → Centre de gestion de la confidentialité →
   Paramètres du Centre de gestion de la confidentialité → **Catalogues de
   compléments approuvés***.
4. Coller `\\NOM-DU-PC\Paysage` dans **URL du catalogue**, cliquer **Ajouter le
   catalogue**, puis cocher **Afficher dans le menu**. OK.
5. Redémarrer Word, puis *Insertion → Compléments → Mes compléments → onglet
   **Dossier partagé*** → Paysage.

Le dossier partagé n'héberge que le manifeste : Word y cherche des fichiers XML,
et rien d'autre. Il doit rester joignable au démarrage de Word — sur sa propre
machine, c'est acquis.

---

## Ce qu'il faut regarder en premier

Le portage est vérifié par 164 000 comparaisons contre le Python, et le câblage
par deux batteries contre un Word simulé. **Rien de tout cela ne prouve que le
vrai Word se comporte comme le faux.** Quatre choses valent d'être regardées
tout de suite :

**Le curseur.** Taper trois paragraphes d'affilée, sans revenir en arrière. Les
trois doivent faire pousser la forme. Si la plante ne bouge qu'au premier, c'est
que `DocumentSelectionChanged` se comporte autrement qu'on l'a supposé — et
c'est la décision 2 qui est en jeu.

**Le retour à la ligne.** Le même essai vérifie l'autre panne : Word crée un
paragraphe vide à chaque `Entrée`, et deux paragraphes français sur trois
commencent par les mêmes mots.

**Le collage.** Coller un chapitre entier. Rien ne doit pousser — la forme
attend qu'on retravaille le texte collé.

**Le document qu'on n'a fait qu'ouvrir.** Ouvrir un chapitre, regarder le volet,
fermer sans rien taper. Word ne doit **pas** demander d'enregistrer les
modifications. Le paysage n'écrit dans le fichier qu'une fois qu'il a poussé, et
c'est la décision 16 qui l'exige : un cadeau ne salit pas les fichiers.

Et une chose qu'aucun essai ne peut trancher, **le point ouvert 12** : la
transition du germe vers une famille est une coupure. À 800 mots, une chaîne
penchée devient un arbre. C'est peut-être une naissance, c'est peut-être un
défaut. Ça ne se juge pas sur planche.

---

## Si le volet reste vide

Il ne devrait jamais l'être : un plant qui vient de naître est presque rien,
mais le précédent déborde du cadre par la gauche. Un volet vraiment vide veut
dire que le paysage n'a pas été retrouvé.

- **Word trop ancien** : le volet le dit lui-même. Les événements de paragraphe
  demandent WordApi 1.6. Aucune contrainte n'est déclarée dans le manifeste
  exprès — une contrainte non satisfaite rendrait l'add-in *invisible*, sans un
  mot, ce qui est le pire accueil possible.
- **Document jamais enregistré** : `Office.context.document.url` est vide tant
  que le fichier n'a pas de chemin, donc la clé du dossier l'est aussi, et
  **tous les documents non enregistrés partagent un même paysage**.

  ⚠️ Conséquence à connaître : depuis la décision 16, l'identité du paysage est
  gravée dans le `.docx` à la première copie. Un nouveau chapitre commencé
  *avant* d'être enregistré garde donc son paysage à lui, et ne rejoint plus
  celui de la thèse une fois rangé dans le bon dossier. **Enregistrer le
  document d'abord, écrire ensuite.**

  C'est aussi une chose à regarder le premier jour, et aucun essai ne la couvre :
  personne ne sait encore ce que le vrai Word renvoie pour un document neuf —
  vide, `Document1`, ou un chemin temporaire. Les trois appellent des réponses
  différentes. Pour le voir : ouvrir un document neuf dans le dossier de la
  thèse, volet ouvert, et regarder si le paysage déjà poussé apparaît ou si la
  forme repart de zéro.
- **Le paysage vit dans le `localStorage` du navigateur intégré à Word**, et
  chaque document en garde une copie (décision 16). Vider les données de site ne
  le perd donc plus : il revient du `.docx` à l'ouverture suivante, et la console
  le dit — « rendu par le document, N empreintes ». Un volet vide sur un document
  où l'on a déjà écrit veut dire que ni l'un ni l'autre n'a été retrouvé.
