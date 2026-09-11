---
chantier: GRA-1
statut: interrompu
---

# GRA-1 — le cinquième ton

**Arrêté sur** — `9db6158`, 9 septembre, seul commit de la branche `cinquieme-ton` :
`n_tons` passe de `1 + int(richesse * 4)` à `1 + min(4, int(richesse * 5))`, et chaque
famille cesse de tenir dans un seul niveau de palette. Parité sans écart, 199 059
comparaisons. Mis de côté parce qu'il décalait le flux aléatoire et faisait tomber
l'essai de caméra ; débloqué depuis que la géométrie ne lit plus le flux partagé —
décision 18, vérifié en rebasant.

## Reste

### Intégration
- [ ] `cinquieme-ton` est rebasée sur `main`, et son commit cite `GRA-1` en tête de
  sujet — sans quoi le chantier reste à `0 commit`
- [ ] Sur la branche rebasée, les six suites passent dans une seule commande : aucun
  essai en échec, aucune mutation qui échappe, aucun écart de parité
- [ ] Le commit est sur `origin/main`

### Décisions
- [ ] `DECISIONS.md` dit le cinquième ton fusionné, et plus « mis de côté » — au
  point ouvert 13 et dans « Ce qui reste » de la décision 18

## Contexte

Ce que ×4 coûtait, mesuré sur 120 plants : le cinquième ton ne sortait qu'à richesse
1,000 exactement, au-dessus du plafond réel de la population (0,931) — donc jamais.
Le vrai défaut était ailleurs : le végétal toujours à 3 tons, l'abstrait toujours à 4.
À l'intérieur d'une famille, la richesse ne disait rien. En ×5 : végétal [3, 4],
abstrait [4, 5]. Le détail est dans le corps de `9db6158`.

⚠️ À savoir avant de pousser : chaque push sur `main` republie le volet. Les deux plants
réels de la thèse, aujourd'hui à 4 tons, passeront à 4 et 5 — une plante déjà là change
de palette à l'ouverture suivante. Le commit le compte comme un gain ; il ne dit pas si
ce changement sous les yeux de la personne est acceptable.
