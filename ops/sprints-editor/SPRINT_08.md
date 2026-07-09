# SPRINT 08 — Buscatraços + presets cota POM i anotació
FRONTEND only. Depèn de S0, S6 (subpaths sans), S7 (formes riques).

## Abast
1. BUSCATRAÇOS (Pathfinder) sobre 2+ objectes seleccionats convertibles a path
   (path/rect/rect_round/ellipse/polígon): UNIR · RESTAR (superior retalla inferior) ·
   INTERSECAR · EXCLOURE. Implementació: convertir a Paper.js en memòria (paper.Path /
   CompoundPath des del JSON — la conversió JSON→Paper ja existeix al PaperFlatEditor:
   REUTILITZAR-LA extreta a helper, no reescriure-la), aplicar unite/subtract/
   intersect/exclude, serialitzar de tornta amb el mateix camí que el roundtrip del
   sub-editor (§22, fidel). Resultat = UN type:'path' (evenodd si cal — S6 ho suporta);
   estil de l'objecte inferior. Botons al ribbon (grup nou, Tabler outline), actius
   només amb selecció vàlida. Història: 1 entrada.
2. PRESET COTA POM: nou preset (patró PRESET_TOOLS existent): group{ línia amb
   extrems perpendiculars (cota tècnica) + text editable a sobre }. Sense binding a
   POM viu (frontera G1 — 🔴 futur; el text és lliure, el tècnic hi escriu "A · 37").
3. PRESET ANOTACIÓ: group{ text + fletxa fina } variant lleugera del callout existent,
   pensada per a notes de fitting sobre el flat.

## Porta verda
Unir 2 el·lipses = 1 path; restar un cercle d'un rect = forat visible (live i PDF —
prova àcida de S6); intersecar i excloure correctes; undo reverteix l'operació sencera
i recupera els objectes originals. Presets s'insereixen i s'editen. Build net.

## Commits: 1. helper JSON↔Paper extret · 2. buscatraços · 3. presets.
