# FASE_3 · ONADA 2 — ELS ESCRIPTORS ESTAMPEN ELS DOS EIXOS (desarmar C4)

Prerequisit: REPORT_FASE_2 verd. Nodes: DOSSIER §II.10 bloc Onada2 (94 nodes),
amb el bloc A (els 8 upserts de l'accident armat) com a NUCLI. Fet estructural
que aquesta fase mata: «cap escriptor del repo estampa capa avui».

## CONTRACTE
- Tot escriptor de les 9 taules declara EXPLÍCITAMENT capa i instancia — avui
  amb els literals del cas ('exterior', '') o amb el valor de la fila d'origen
  quan propaga (p.ex. clonar GradedSpec→PieceFittingLine copia capa i
  instancia de l'spec; el signal F1 estampa els de la BaseMeasurement).
- Tot get_or_create/update_or_create/first()/exclude alinea la seva CLAU DE
  LOOKUP amb la unicitat real de la taula (els 8 del bloc A del dossier són el
  cas de llibre: lookup sense capa contra unicitat amb capa+instancia).
- Res de comportament nou: amb comportes tancades només circulen
  'exterior'/'' → byte-idèntic obligatori igualment.
- Poda/baixa/esborrat: mai operar per pom_id sol — la identitat de la baixa és
  la fila (o la clau completa). El delete d'overrides :2751 i el soft-delete
  :1943-1946 del dossier són els exemples a corregir.

## ABAST ESPECIAL
- Signal F1 (signals.py, dossier §A5.6): estampa capa i instancia de la
  instance — tanca el forat anotat des de l'Onada 1. Després, ESTRENY l'assert
  del harness de C9/Onada1 (d'assertNotIn a igualtat, com el report d'Onada 1
  va deixar dit).
- materialize_lines + N3 (services_size_check): l'aparellament passa de pom_id
  pelat a clau completa — és el «pitjor cas del cens», tracta'l amb el seu
  propi commit i el seu propi test.
- Federació: _clau_natural_pom creix a 4-tupla (codi_global, codi_client,
  capa, instancia) + versionat del paquet (camp 'format' o equivalent mínim;
  els paquets vells es llegeixen com a exterior/''). Documenta-ho al docstring
  que ja explica per què la clau és estricta.
- Sembra item→model (materialize_poms): hereta capa I instancia de l'item.
- bootstrap_tenant.py:162: la clau natural de GarmentPOMMap creix (el deute de
  C1 que el dossier va trobar) — mateix commit que els seeds.
- reorder/ordering dins-de-capa: NOMÉS si el dossier el té a Onada2 i el canvi
  és invisible amb una sola capa; si implica migració d'ordering amb efecte
  visible, PENDENT per a sessió amb Agus.
- NO TOQUIS: els 7 guards de §II.13 (la seva inversió és Onada 3/C4, amb UI i
  409-amb-candidats — NO aquesta tarda) · els intocables del motor · cap .jsx.

## TESTS
Harness d'escriptors: dins de rollback amb comportes alçades, executa els
camins d'escriptura principals (resolve size check, consolidate fitting, alta
manual, sembra) creant files amb capa/instancia explícites → cap
MultipleObjectsReturned, cap col·lapse, unicitats respectades → rollback.

## GREEN FLAGS
Els de FASE_2 + harness d'escriptors verd + «grep d'estampat»: cap
get_or_create/update_or_create sobre les 9 taules sense capa i instancia a la
clau o als defaults (llista'ls al report com a prova) + fumeig i dump
byte-idèntics + comportes vives.

REPORT: docs/diagnosis/REPORT_FASE_3.md. Veredicte: «FASE_4 POT ARRENCAR».
