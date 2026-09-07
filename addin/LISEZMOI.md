# Installer le paysage

Trois choses à faire, dans cet ordre. La troisième est la seule qui demande
Word.

---

## 1. Poser les fichiers sur un hébergement statique HTTPS

Word refuse de charger un add-in autrement : le manifeste pointe vers une URL,
même si tout le code est local et sans dépendance. GitHub Pages, Netlify,
Cloudflare Pages — n'importe lequel, et le jour où il ferme, on change une
ligne du manifeste.

Il faut y déposer :

```
volet.html
apercu.html
src/            (tous les .js)
icone-16.png  icone-32.png  icone-80.png
```

⚠️ **HTTPS obligatoire.** Word refuse le HTTP en clair, y compris en local.

## 2. Remplacer l'URL dans le manifeste

`manifest.xml` contient `https://exemple.invalid/paysage/` à six endroits.
Toutes doivent pointer vers l'hébergement de l'étape 1 — y compris
`<AppDomain>`, sans lequel le dialogue d'aperçu ne s'ouvrira pas.

```bash
sed -i 's|https://exemple.invalid/paysage|https://VOTRE-URL|g' manifest.xml
sed -i 's|https://exemple.invalid|https://VOTRE-URL|g' manifest.xml
```

## 3. Charger le manifeste dans Word

**Mac** — déposer `manifest.xml` dans :

```
~/Library/Containers/com.microsoft.Word/Data/Documents/wef
```

puis redémarrer Word. Le bouton apparaît dans l'onglet Accueil.

**Windows** — mettre `manifest.xml` dans un dossier, le partager, puis dans
Word : *Fichier → Options → Centre de gestion de la confidentialité →
Paramètres → Catalogues d'add-ins*, ajouter le chemin du dossier partagé et
cocher « Afficher dans le menu ». Redémarrer Word ; l'add-in est sous
*Insertion → Mes compléments → Dossier partagé*.

---

## Ce qu'il faut regarder en premier

Le portage est vérifié par 164 000 comparaisons contre le Python, et le câblage
par deux batteries contre un Word simulé. **Rien de tout cela ne prouve que le
vrai Word se comporte comme le faux.** Trois choses valent d'être regardées
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
  que le fichier n'a pas de chemin, donc le paysage ne peut pas être rattaché à
  un dossier. Enregistrer le document une fois suffit.
- **Le paysage vit dans le `localStorage` du navigateur intégré à Word.** Vider
  les données de site le perd. C'est un choix de la décision 13 : aucun serveur,
  donc aucun compte à créer et rien à payer — mais aussi rien à récupérer
  ailleurs.
