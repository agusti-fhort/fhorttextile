# FASE_1 · C1-ins — LA COLUMNA `instancia` AMB EL MOTLLE DE C1

Prerequisit: REPORT_FASE_0 amb «FASE_1 POT ARRENCAR». Regles generals: FASE_0.
Referència de nodes: DOSSIER §II.10 (bloc C1-ins, 74 nodes) i §I.A1 (unicitats).

## DECISIONS QUE GOVERNEN (ratificades, no reobrir)
- Columna `instancia` = CharField(60), default `''`, NOT NULL, db_index, slug
  compost canònic (p.ex. 'left-relaxed'; l'ordre de composició el farà la UI,
  la BD només guarda l'string). MAI FK, mai choices (com `capa`).
- Va a LES MATEIXES 9 TAULES que `capa` (dossier §I.A1 #1-8 + POMPlacement).
- NO va a: ModelGradingRule ni GradingRule (decisió Montse "graduen igual" —
  deixa-ho dit en comentari al model) · ClientMesuraPerfil, POMEstadistica*,
  PatternPOM, CustomerPOMAlias (fora per assignació d'onada del dossier).
- MeasurementChangeLog: SÍ rep la columna (com va rebre capa).

## COMMITS (mateix patró que C1, un per app)
C1 · models_app: migració ADD COLUMN + DROP DEFAULT (patró Django estàndard —
     recorda: el default queda al MODEL, no a Postgres) per a BaseMeasurement,
     MeasurementChangeLog, ModelGradingOverride, SizeCheckLine, POMPlacement.
C2 · models_app: unicitats — cada UNIQUE que porta capa creix amb instancia
     (p.ex. (model, pom, capa) → (model, pom, capa, instancia)); la vella es
     retira A LA MATEIXA migració. + CheckConstraint COMPORTA:
     *_instancia_gate_cins amb Q(instancia='') a les 5 taules.
     + CHECK «instància⇒nom»: a BaseMeasurement,
     ~Q(instancia__gt='', nom_fitxa='') (una instància sense nom de fitxa és
     il·legal per construcció — decisió D1).
C3 · fitting: ídem per a GradedSpec i PieceFittingLine (columna + unicitat +
     comporta).
C4 · pom: ídem per a GarmentPOMMap i ItemBaseMeasurement (SHARED+TENANT: la
     migració emet SQL també a public — com a C1).
C5 · tests: backend/…/test_instancia_comporta_cins.py calcant
     test_capa_comporta_c1: llista literal de les comportes noves + verificació
     information_schema que ModelGradingRule NO té instancia + prova del CHECK
     instància⇒nom (INSERT amb instancia i sense nom → rebutjat, dins rollback).
     NO toquis test_capa_comporta_c1 (el seu pin de 9 noms segueix vàlid: les
     comportes noves tenen nom propi).

## EXECUCIÓ A BD
- Mostra cada fitxer de migració generat AL REPORT abans d'aplicar (no hi ha
  Agus per validar: el report és la validació diferida — sqlmigrate de cada una,
  enganxada).
- migrate_schemas (MAI --schema) → ×3 schemas.
- systemctl restart ftt-staging.service (codi vell + columna nova = petada; la
  lliçó de C1).
- AUDITORIA: cins_audit_counts.sql + cins_audit_constraints.sql → 100% files
  amb instancia='' als 3 schemas, comportes vives al catàleg de PG, cap NULL.

## GREEN FLAGS DE FASE
manage.py check · migracions aplicades ×3 amb auditoria SQL · pin base_stages
13/13 · test_capa_comporta_c1 intacte i verd · test_instancia_comporta_cins
verd · fumeig = T0 byte-idèntic · dump de superfícies = T0 · OpenAPI: 0
ocurrències de 'instancia'.

REPORT: docs/diagnosis/REPORT_FASE_1.md (hashes, sqlmigrate de cada migració,
auditories, flags). Veredicte: «FASE_2 POT ARRENCAR» o STOP motivat.
