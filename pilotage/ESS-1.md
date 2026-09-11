---
chantier: ESS-1
statut: à venir
---

# ESS-1 — les essais à graine unique

**Point de départ** — point ouvert 16. Le 9 septembre, en réparant la croissance, une
douzaine d'essais sur soixante-dix ont été examinés de près ; quatre ne tenaient pas ce
qu'ils annonçaient. Les soixante autres n'ont jamais été éprouvés sur ce motif : une
graine fixe, un seuil numérique ajusté sur elle.

## Reste

### Relevé
- [ ] La liste des essais de `jardin/essais.py` qui tirent une graine littérale ET
  comparent à un seuil numérique est écrite au point 16, avec son compte — relevée au
  `grep`, pas au jugement

### Mesure
- [ ] Chaque essai relevé est rejoué sur vingt graines, sur le code inchangé ; médiane,
  minimum et nombre de graines sous le seuil sont reportés au point 16
- [ ] Chaque essai relevé traverse ce qu'il surveille : une mutation de la chose
  surveillée le fait échouer

### Réparation
- [ ] Chaque essai dont une graine au moins tombe asserte sur la médiane de douze
  graines, avec son seuil d'origine inchangé
- [ ] Le surcoût par passage d'`essais.py` est mesuré en tours alternés, et écrit dans le
  corps du commit

## Contexte

La méthode est au point 16 de `DECISIONS.md`, et elle ne se réinvente pas. ⚠️ Tout ce
qui entre dans `essais.py` est multiplié par soixante-cinq : un essai réparé sur douze
graines coûte douze fois sa mesure à chaque mutation.

⚠️ Les quatre du 9 septembre ont été trouvés en perturbant le code, ce qui fait remonter
les essais fragiles. Leur taux — quatre sur douze — n'est pas une prévision pour les
soixante autres.
