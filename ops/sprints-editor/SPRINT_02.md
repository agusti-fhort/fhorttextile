# SPRINT 02 — Snapping, regles en mm i guies
FRONTEND only. TechSheetEditor.jsx (+ mòdul ftt/snapping.js si supera ~100 línies).

## Abast
1. SNAPPING en drag/resize: imants a (a) vores i centres dels altres objectes de la
   pàgina, (b) marges i centre de pàgina. Llindar ~2mm en unitats document (escalar
   amb zoom). Línies guia temporals (gold, 1px) mentre l'imant actua. Tecla per
   desactivar temporalment mentre s'arrossega: Cmd/Ctrl.
2. REGLES en mm als marges superior/esquerre del viewport (el document ja pensa en mm:
   MM_TO_PX/toMm). Marcador de posició del cursor.
3. GUIES arrossegables des de les regles (H i V), persistides al JSON de pàgina
   (`guides:[{axis,pos}]`, retrocompatible si absent). Els objectes hi snapegen.
   Esborrar = arrossegar fora. Les guies NO s'exporten al PDF (només live).

## Notes
- Rendiment: computar candidats d'snap al dragstart (no per frame).
- Història: moure una guia = entrada d'història.

## Porta verda
Drag d'un rect s'imanta a la vora d'un altre i al centre de pàgina amb guia visible.
Guia creada persisteix al desar/recarregar. PDF exportat sense regles ni guies. Build net.

## Commits: 1. snapping · 2. regles · 3. guies.
