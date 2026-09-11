---
chantier: PHR-1
statut: à venir
---

# PHR-1 — les phrases de nuit

**Point de départ** — le mécanisme est prêt en Python, pas encore dans l'add-in (PHR-2) ;
les phrases sont à écrire. Le registre
`CREUX` de `jardin/phrases.py` est vide exprès (point ouvert 1) ; le paquet battu en
compte dix, sept communes et trois nominatives, et l'écart moyen entre deux retours
d'une même phrase plafonne donc à dix nuits (point ouvert 10).

## Reste

- [ ] Le registre `CREUX` porte des phrases écrites par celui qui offre le cadeau
- [ ] Le paquet compte vingt phrases écrites par l'auteur, et l'écart moyen mesuré
  dépasse dix nuits
- [x] Le texte de la question du prénom est écrit par celui qui offre (décision 10) —
  « Ton prénom ? », dans le `label` de `addin/volet.html`

## Contexte

⚠️ **Ce chantier n'est pas à l'agent.** C'est le seul endroit du système où passe la voix
de celui qui offre : ne pas écrire ces phrases, ne pas remplir « en attendant », ne pas
proposer de brouillon (`CLAUDE.md`, « Ce qui n'est pas à toi »). L'agent peut mesurer
l'écart moyen une fois le paquet rempli ; rien de plus.

Ce qu'il ne faut pas mettre dans `CREUX`, tel que le registre le dit lui-même : rien qui
félicite, rien qui encourage, rien qui demande quoi que ce soit.

⚠️ Depuis `286f23a`, ce qui s'écrit ici arrive dans Word. Une phrase ajoutée à
`jardin/phrases.py` doit l'être aussi, à l'identique, dans `addin/src/phrases.js` : la
parité compare les deux registres.

Deux contraintes de forme, venues de la décision 10 révisée : une phrase qui s'accorde
porte ses trois formes, `{fort|forte|fort.e}` ; et tout ne s'écrit qu'avec ce que
l'alphabet du message sait dessiner — A à Z, l'espace, `! ' , . ? -`. Les
accents tombent au tracé. Sans prénom connu, une phrase nominative ne sort pas ; sans
accord, une phrase qui s'accorde non plus.
