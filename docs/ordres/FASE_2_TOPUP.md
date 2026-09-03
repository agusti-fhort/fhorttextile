# FASE_2 · TOP-UP DE LECTORS — CLAU COMPLETA (pom, capa, instancia)

Prerequisit: REPORT_FASE_1 verd. Nodes: DOSSIER §II.10 blocs A i B
(top-up-lectors, 68 nodes) — la llista amb fitxer:línia és ALLÀ; re-verifica
cada línia abans de tocar (deriva possible post-FASE_1).

## CONTRACTE (el criteri destil·lat de l'Onada 1, ara amb tres elements)
- Cap dict/set/lookup per pom_id (ni per (pom_id, capa)) sobre les 9 taules:
  la clau passa a (pom_id, capa, instancia) quan la fila consumidora la sap
  dir (forma A), o el queryset filtra capa='exterior', instancia='' amb
  comentari del motiu semàntic (forma B).
- Mapes germans del mateix bloc creixen TOTS ALHORA (mai un sí i un no).
- Amb les dues comportes tancades, TOT byte-idèntic. Un byte de diferència al
  dump → revert del commit i PENDENT.
- Els lectors que l'Onada 1/1b ja va passar a (pom, capa): només CREIXEN amb
  instancia — no els redissenyis.

## ABAST ESPECIAL D'AQUESTA FASE
- Els 2 FORATS DE CAPA del dossier (§II.10): patterns/views.py:552-556 i
  federation_service.py:593 — lectura de BaseMeasurement sense àncora: forma B
  amb els DOS filtres. (El bug viu de patterns:544-549 NO es toca: cua diürna.)
- base_stages_view: creix a clau completa — és el node del pin: pin + fumeig
  immediatament després del seu commit, abans de continuar.
- ELS INTOCABLES SEGUEIXEN INTOCABLES: pom/services.py _load_base_measurements
  i _load_grading_rules NO es toquen (C3, decisió humana). Si un node t'hi
  arrossega, PENDENT i endavant.

## ORGANITZACIÓ
Commits per fitxer o per parella de fitxers germans (l'Onada 1 en va fer 10;
aquí seran ~12-16). Ordre suggerit: pom/s*_views → services (_load_model_
overrides, que ja té el docstring que mana créixer) → fitting (serializers,
graded_spec_views, repas_views) → models_app (serializers_size_check,
pom_placement_views lectura, base_stages_view penúltim) → els 2 forats de capa
→ tests.

## TESTS
Amplia test_lectors_capa_onada1.py (o fitxer germà test_lectors_instancia):
harness de files germanes v2 — dins savepoint: alça LES DUES comportes de la
taula → insereix fila capa='folre' I fila instancia='left' → asserts que cap
lector col·lapsa ni barreja → rollback → comportes vives al final.

## GREEN FLAGS
Els de FASE_1 + harness v2 verd + dump de superfícies byte-idèntic complet +
comportes (totes dues famílies) rebutjant dins de rollback.

REPORT: docs/diagnosis/REPORT_FASE_2.md — per commit: forma A/B i per què;
PENDENTs amb motiu. Veredicte: «FASE_3 POT ARRENCAR» o STOP.
