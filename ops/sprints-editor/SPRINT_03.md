# SPRINT 03 — Taules snapshot (T1a/T1b/T2/custom) + substitució graded_table
FRONTEND + backend zero (fonts ja existeixen). Depèn de S0.

## Lleis (decisions Agus 2026-07-06 — NO desviar-se'n)
- SNAPSHOT: valors/text HARDCODEJATS al JSON en col·locar. Cap binding viu. Bloc
  `snapshot:{model_id,size_fitting_id?,snapshot_at}` = traçabilitat, no reactivitat.
- T1a/T1b: cel·les CONGELADES (no editables). T2/custom: cel·les editables.
- La graded_table viva se SUBSTITUEIX al ribbon (render llegat es queda per a docs
  existents; cap conversió automàtica).

## Element nou
{ type:'table', layer:'free', x,y,width, kind:'pom_fitting|pom_grading|bom|custom',
  snapshot:{...}, columns:[{key,label,width}], rows:[[...strings]],
  style:{fontSize:9, headerFill, zebra:bool} }
Render a DUES bandes via buildTablePrimitives (helper compartit existent — estendre'l,
no duplicar-lo). Cos mínim 8pt (llei fitxa tècnica). Amplades de columna reals.

## Variants i fonts (endpoints verificats a la diagnosi §BLOC4)
- T1a FITTING: GET models/<id>/base-measurements/ + grading-rules (regles/deltes/breaks).
  Columnes: POM (nom EN canònic + nom idioma usuari a sota, gris petit — llei
  nomenclatura) · Nomenclatura fitxa (nom_fitxa) · Valor base (cm) · Regla/delta ·
  Break (marca) · Tol ± · **Mesura nova** (BUIDA, ampla) · **Comentaris** (BUIDA, la més
  ampla, ~30%). Per imprimir i anotar A MÀ al fitting.
- T1b GRADING FINAL: GET size-fittings/{id}/taula-mesures/ (cells{pom:{talla:{value,
  type,increment}}}) — run complet, breaks marcats visualment (vora/negreta al canvi
  d'increment via grading-rules).
- T2 BOM: neix buida; columnes material·ref·proveïdor·consum·notes; edició manual.
- CUSTOM: diàleg files×columnes; edició manual.

## Flux de col·locació
Botó ribbon (substitueix el de graded_table :2231) → picker de variant → per T1a/T1b
selector de size_fitting si n'hi ha més d'un → fetch → construir rows → inserir.
Estats de càrrega/error amb gràcia (fetch falla = missatge, mai crash).

## Porta verda
Les 4 variants es col·loquen, es mouen/escalen, live==export (PDF llegible ≥8pt).
T1a mostra les 2 llengües de POM, tolerància, i les 2 columnes buides. T1b marca breaks.
Doc antic amb data_block graded_table encara renderitza. i18n: totes les etiquetes
noves amb clau. Build net.

## Commits: 1. element table+render · 2. picker+fonts T1a/T1b · 3. T2/custom ·
4. substitució botó ribbon.
