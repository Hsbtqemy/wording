---
chantier: VOL-2
statut: différé
---

# VOL-2 — rastériser les plants achevés

**Point de départ** — la décision 12 l'a décidé : « seul le plant en cours est vivant ;
les plants achevés sont rastérisés une fois et jamais retouchés ». Le volet ne le fait
pas. `addin/src/volet.js` l'écrit lui-même, au-dessus de `dernier_svg` : « en attendant,
on évite au moins de RE-POSER un dessin identique ».

## Reste

### Arbitrages
- [ ] Trancher, au vu de la passe `qa/vrai-word.md` sur la thèse entière : rastériser
  comme décidé, ou consigner dans `DECISIONS.md` que la décision 12 n'est plus requise

### Si on rastérise
- [ ] Un plant achevé est rendu une fois, et `essais_volet.js` vérifie qu'aucun tic
  suivant ne le reconstruit
- [ ] Le tic reste sous le budget de 100 ms de la décision 12, sur la thèse entière,
  dans un vrai Word — mesuré, et le chiffre écrit dans `DECISIONS.md`

## Contexte

**Différé exprès, et ce qui le rouvre** : la case « sur le document de la thèse entière,
volet ouvert, la frappe n'accroche pas » de `qa/vrai-word.md`. Si elle échoue, c'est
ici qu'on agit. Si elle passe, la décision 12 a peut-être décrit un moyen plutôt qu'une
exigence — c'est l'arbitrage ci-dessus, et il revient à celui qui a pris la décision.

Ce qu'on sait déjà : un tic réel coûte 3 ms en Python (décision 12), et lire le corps de
74 000 signes 17 à 21 ms dans le vrai Word (décision 17). Le rendu SVG d'un paysage
entier dans le volet n'a jamais été mesuré.
