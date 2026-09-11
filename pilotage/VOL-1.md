---
chantier: VOL-1
statut: à venir
---

# VOL-1 — le guet dans un vrai Word

**Point de départ** — le paysage n'a jamais poussé dans un vrai Word, pas une fois
(`addin/LISEZMOI.md`). Le guet de la décision 17 est éprouvé contre un hôte simulé par
`essais_volet.js` ; `pont.js`, qui n'est plus dans le livrable, attend avec ses essais
que le guet ait tourné pour de vrai.

## Reste

### Le vrai Word
- [ ] La passe `qa/vrai-word.md` est jouée sur l'Office LTSC 2021 de la machine cible, et
  chacune de ses cases est cochée par qui l'a jouée

### Le départ du pont
- [ ] `addin/src/pont.js` et `addin/essais.js` partent dans le même commit
- [ ] Les cinq mutations qui visent `pont.js` dans `addin/parite/mutations.js` partent
  avec lui, et la batterie attrape toutes celles qui restent
- [ ] La commande de vérification de `CLAUDE.md` compte cinq suites avec leurs attendus
  à jour, et le tableau des fichiers de `DECISIONS.md` ne cite plus ni `pont.js` ni
  `essais.js`

## Contexte

L'ordre compte : la passe d'abord. Tant que le guet n'a pas tourné dans un vrai Word, le
chemin des événements doit rester à une ligne de distance, et c'est la seule raison pour
laquelle `pont.js` est encore là (`CLAUDE.md`, « Vérifier »).

Aucune batterie ne prouve que le vrai Word se comporte comme le faux ; c'est le risque
irréductible du livrable, et cette fiche est l'endroit où il se lève.
