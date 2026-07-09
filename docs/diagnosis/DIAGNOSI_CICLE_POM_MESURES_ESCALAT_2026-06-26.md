# DIAGNOSI GLOBAL — Cicle POM → Mesures → Escalat

Data: 2026-06-26  
Scope: read-only sobre codi. Cap canvi de codi.

## Nomenclatura fixada

**FET**: en aquesta diagnosi s'usa la nomenclatura d'Agus:

- **POM** = la tasca/moment on es creen per primera vegada valors + regles sobre la talla base (genesi).
- **Mesures** = treballar sobre la base que ja existeix.
- **Escalat** = treballar a partir de la propagacio.

**FET**: el codi actual ja separa aquests moments al `ModelSheet`: `MeasuresEntryPanel` per entrada/genesi, `CheckMeasureEditor` per Mesures i `PropagatedEditor` per Escalat. Referencies: `frontend/src/pages/ModelSheet.jsx:7-9`, `frontend/src/pages/ModelSheet.jsx:378-447`.

**FET**: `MeasureGrid` no decideix el moment; es un component controlat per `rows`, `groups`, `leadCols`, `editable`, `onSave`, `onNomSave`, `editCodi`, `reorderable`. El proveidor d'eix construeix `groups` i `rows`; el grid "no se'n sap res". Referencies: `frontend/src/components/model/MeasureGrid.jsx:5-14`, `frontend/src/components/model/MeasureGrid.jsx:211-221`.

## Pregunta 1 — Context del model que defineix l'alimentacio

**FET**: els camps de model rellevants per al cicle son: `garment_type_item` (context de POMs suggerits/item), `size_system`, `grading_rule_set`, `base_size_label`, `size_run_model`, `estat/fase_actual`. Referencies: `backend/fhort/models_app/models.py:161-167`, `backend/fhort/models_app/models.py:186-199`, `backend/fhort/models_app/models.py:201-202`, `backend/fhort/models_app/serializers.py:89-115`.

**FET**: el `GarmentTypeItem` porta `base_size_definition` i `grading_rule_set`; aquest es el context de plantilla/item abans que el model posseeixi la seva dada. Referencies: `backend/fhort/tasks/models.py:267-292`.

**FET**: `ModelSheet` carrega simultaniament el model i `taula-mesures`; guarda `taulaRows`, `sizesAmbDades` i `deltes` al seu estat local. Referencies: `frontend/src/pages/ModelSheet.jsx:121-134`.

**FET**: el senyal frontend de "encara no te base" es `verge = !taulaRows.some(r => r.base_value_cm != null)`. En entrar al tab Mesures, `verge || entryMode`, sense `taskParam`, activa `mesuresEntry` i pinta genesi. Referencies: `frontend/src/pages/ModelSheet.jsx:136-155`.

**FET**: `entryMode` ve de `?mode=entry`; `taskParam` ve de `?task_id=`. El comentari fixa que `?mode=entry` obre Definicio POM encara que ja hi hagi mesures; `task_id` de size_check força TREBALL, no entrada. Referencies: `frontend/src/pages/ModelSheet.jsx:91-95`, `frontend/src/pages/ModelSheet.jsx:145-153`.

**FET**: el boto intern "Editar mides" obre `enterEdit('Mesures','pom')`; si el codi de tasca es `pom`, `ModelSheet` posa `mesuresEntry=true` i no `editing='Mesures'`. Referencies: `frontend/src/pages/ModelSheet.jsx:186-197`, `frontend/src/pages/ModelSheet.jsx:397-404`.

**FET**: una tasca entrant de Mesures amb `task_id` entra a `editing='Mesures'` i consumeix la tasca viva, sense crear-ne una de nova. Referencies: `frontend/src/pages/ModelSheet.jsx:225-240`.

**FET**: `Escalat` no s'activa per `verge`; el tab sempre renderitza `PropagatedEditor`, en consulta o edicio segons `editing === 'Escalat'`. Referencies: `frontend/src/pages/ModelSheet.jsx:427-448`.

**FET**: el senyal de "ja s'ha propagat" es `grading-status`: busca `SizeFitting` de treball + `GradingVersion` vigent i retorna `te_dades_propagades`, `segellada`, `version_number`. Referencies: `frontend/src/pages/ModelSheet.jsx:255-284`, `backend/fhort/models_app/views.py:1570-1592`, `frontend/src/api/endpoints.js:59-61`.

**FET**: `taula-mesures` tambe llegeix `GradedSpec` de la `GradingVersion` vigent per omplir `graded`; si no hi ha propagacio, `graded` queda buit. Referencies: `backend/fhort/models_app/views.py:680-699`, `backend/fhort/models_app/views.py:714-738`.

## Pregunta 2 — Moment POM (genesi): que esta resolt

**FET**: `MeasuresEntryPanel` esta declarat com a flux d'entrada/genesi i exclou explícitament el cami `size_check`, que pertany al treball. Quan la base queda materialitzada, crida `onMaterialized()` per passar a consulta/treball. Referencies: `frontend/src/components/model/MeasuresEntryPanel.jsx:9-18`.

**FET**: POMs suggerits venen de `GarmentPOMMap` filtrat per `model.garment_type_item`, ordenat per `-is_key, ordre`. Si el model no te item, no hi ha suggeriments. Referencies: `backend/fhort/models_app/views.py:479-513`.

**FET**: `MeasuresEntryPanel` llegeix `poms-suggerits`, `taula-mesures` i `item-base-measurements` per decidir selector/manual/import/s sembra. Referencies: `frontend/src/components/model/MeasuresEntryPanel.jsx:70-128`.

**FET**: `materialitzar-poms` crea `BaseMeasurement` des de l'item: amb `ItemBaseMeasurement` copia `base_value_cm`, `nom_fitxa`, tolerancies, `origen='ITEM_STANDARD'`; sense valor crea `TEMPLATE` amb `base_value_cm=None`. Referencies: `backend/fhort/models_app/views.py:516-528`, `backend/fhort/models_app/views.py:542-573`.

**FET**: `materialitzar-poms` es idempotent sota sobirania del model: nomes sembra un `TEMPLATE` buit si l'item porta valor; no trepitja `MANUAL/IMPORTED/FITTED` o files amb valor. Referencies: `backend/fhort/models_app/views.py:526-528`, `backend/fhort/models_app/views.py:576-589`.

**FET**: `set-measurements` es el cami d'escriptura en bloc de l'entrada: rep `measurements` i `keep_pom_ids`; fa upsert de `BaseMeasurement` amb `origen='MANUAL'`, reactiva `is_active`, copia tolerancia default del POM i soft-deleteja actius que no siguin a `keep_pom_ids`. Referencies: `frontend/src/components/EditableTable/EditableTable.jsx:118-135`, `backend/fhort/models_app/views.py:787-849`.

**FET**: en l'entrada actual hi ha alta/cerca de POM tenant: `EditableTable` cerca a `/poms/cerca/` i pot crear a `/poms/crear-tenant/`, despres afegeix una fila temporal. Referencies: `frontend/src/components/EditableTable/EditableTable.jsx:370-415`.

**FET**: l'ordre d'entrada es local fins a guardar; despres `EditableTable` crida `reorder-measurements` amb ids persistits no `tmp-*`. Referencies: `frontend/src/components/EditableTable/EditableTable.jsx:51-60`, `frontend/src/components/EditableTable/EditableTable.jsx:137-143`, `backend/fhort/models_app/views.py:852-872`.

**FET**: les regles inicials del model es poden materialitzar des del `grading_rule_set` del model amb `materialize_model_grading_rules`: wipe-and-recreate de `ModelGradingRule`, copia `logica`, `increment`, `valors_step`, `increment_base`, `increment_break`, `talla_break_label`, `talla_break_pos`, i no copia base/talla base perquè viuen a `BaseMeasurement`/`model.base_size_label`. Referencies: `backend/fhort/models_app/views.py:468-476`, `backend/fhort/models_app/services.py:67-87`.

**FET**: si una regla resident no existeix quan s'edita regim/delta/break, `set_pom_regim_view` la sembra des del fallback del `model.grading_rule_set`; si tampoc hi ha regla de cataleg, crea una regla nova. Referencies: `backend/fhort/models_app/views.py:2142-2157`, `backend/fhort/models_app/views.py:2181-2197`.

**FET**: import de fitxa no reté grading propagat: crea `BaseMeasurement`, deriva/reapunta ruleset, materialitza `ModelGradingRule` importada si toca, crea `SizeFitting` contenidor i deixa `n_specs=0`. Referencies: `backend/fhort/models_app/extraction_views.py:1171-1177`, `backend/fhort/models_app/extraction_views.py:1260-1283`, `backend/fhort/models_app/extraction_views.py:1302-1359`, `backend/fhort/models_app/extraction_views.py:1408-1418`.

**FET**: la derivacio de regles d'import usa `derive_grading_rule_set`, que detecta grading per POM, crea o reutilitza `GradingRuleSet`, i omple `increment_base`, `increment_break`, `talla_break_label`, `talla_break_pos`. Referencies: `backend/fhort/pom/grading_utils.py:229-249`, `backend/fhort/pom/grading_utils.py:276-294`, `backend/fhort/pom/grading_utils.py:360-382`.

**FET**: avui POM/genesi el pinta `EditableTable`, no `MeasureGrid`. `EditableTable` sap treballar amb files `tmp-*`, afegir POM, eliminar files, editar base en bloc i mostrar totes les talles + delta. Referencies: `frontend/src/components/model/MeasuresEntryPanel.jsx:229-243`, `frontend/src/components/EditableTable/EditableTable.jsx:81-95`, `frontend/src/components/EditableTable/EditableTable.jsx:188-244`, `frontend/src/components/EditableTable/EditableTable.jsx:246-315`.

**FET**: a `MeasureGrid` li falta contracte d'entrada POM: el seu reorder depen de `bm_id`, `onSave` desa per `lineId`, i l'edicio de `nom_fitxa` requereix `bmId`. Les files temporals sense `bm_id` i l'alta/soft-delete de POM no son part del contracte actual. Referencies: `frontend/src/components/model/MeasureGrid.jsx:211-221`, `frontend/src/components/model/MeasureGrid.jsx:229-239`, `frontend/src/components/model/MeasureGrid.jsx:263-280`, `frontend/src/components/model/MeasureGrid.jsx:164-178`.

## Pregunta 3 — Moment Mesures (treball sobre base existent)

**FET**: `CheckMeasureEditor` en consulta llegeix l'ultim size check; en treball obre/reutilitza un check pendent. Sempre llegeix `base-stages` en paral.lel. Referencies: `frontend/src/components/model/CheckMeasureEditor.jsx:183-198`.

**FET**: `base-stages` es una lectura derivada del log: estadis de talla base que creixen per presa, snapshots carry-forward, ultima columna = base vigent. Referencies: `backend/fhort/models_app/views.py:1621-1630`, `backend/fhort/models_app/views.py:1646-1665`, `backend/fhort/models_app/views.py:1676-1704`.

**FET**: `open_size_check` crea o reutilitza `SizeCheck` pendent i materialitza una `SizeCheckLine` per cada `BaseMeasurement` actiu amb valor; `valor_teoric` es snapshot del `base_value_cm`. Referencies: `backend/fhort/models_app/services_size_check.py:16-38`, `backend/fhort/models_app/services_size_check.py:41-78`.

**FET**: autosave de cel.la Mesures escriu `SizeCheckLine.valor_real`; decisio i nota tambe s'escriuen a `SizeCheckLine`. Referencies: `frontend/src/components/model/CheckMeasureEditor.jsx:228`, `frontend/src/components/model/CheckMeasureEditor.jsx:200-226`, `backend/fhort/models_app/views_size_check.py:78-83`, `backend/fhort/models_app/serializers_size_check.py:14-20`.

**FET**: en resoldre Acceptat, el motor promou linies acceptades amb `valor_real` a `BaseMeasurement` amb `origen='CHECKED'`; si hi ha canvi de base i deltes, crea nova versio/regradua via `bump_grading_version_and_generate`. Referencies: `backend/fhort/models_app/services_size_check.py:98-118`, `backend/fhort/models_app/services_size_check.py:157-209`.

**FET**: `CheckMeasureEditor` adapta dades a `MeasureGrid`: un grup `base`, historyCols = `stages`, activa = `Real`, trail = decisio/nota, leadCols = regim/tolerancia. Referencies: `frontend/src/components/model/CheckMeasureEditor.jsx:245-315`.

**FET**: en Mesures, `MeasureGrid` tambe edita ordre (`baseMeasurements.reorder`) i `nom_fitxa` (`baseMeasurements.update`) sobre `BaseMeasurement`. Referencies: `frontend/src/components/model/CheckMeasureEditor.jsx:229-241`, `frontend/src/api/endpoints.js:68-73`.

**FET**: els deltes/breaks editables de Mesures s'escriuen a `ModelGradingRule` amb `setPomRule`/`set_pom_regim_view`. Referencies: `frontend/src/components/model/CheckMeasureEditor.jsx:282-296`, `frontend/src/api/endpoints.js:41-45`, `backend/fhort/models_app/views.py:2142-2226`.

## Pregunta 4 — Moment Escalat (propagacio)

**FET**: el boto "Propagar a grading" viu a Mesures; primer consulta `grading-status`, avisa si ja hi ha propagacio, i executa `models.generarGrading({new_version:true})`. Referencies: `frontend/src/pages/ModelSheet.jsx:255-284`, `frontend/src/pages/ModelSheet.jsx:406-415`.

**FET**: `generate_grading_view` exigeix `grading_rule_set`, `size_run_model`, `base_size_label` i BaseMeasurements; crea `SizeFitting` si falta, i amb `new_version=true` crea una GradingVersion nova via `bump_grading_version_and_generate`. Referencies: `backend/fhort/models_app/views.py:1170-1211`, `backend/fhort/models_app/views.py:1213-1250`.

**FET**: l'acte de propagar fa "llenç net": esborra `ModelGradingOverride` del model abans de generar la nova versio. Referencies: `backend/fhort/models_app/views.py:1231-1237`.

**FET**: `generate_graded_specs` llegeix `BaseMeasurement`, regles (`ModelGradingRule` amb fallback a `GradingRule`), excepcions i overrides; escriu `GradedSpec` per POM x talla dins la `GradingVersion` activa. Referencies: `backend/fhort/pom/services.py:18-30`, `backend/fhort/pom/services.py:62-78`, `backend/fhort/pom/services.py:83-139`, `backend/fhort/pom/services.py:356-376`.

**FET**: `GradingVersion` i `GradedSpec` son el contenidor i la sortida persistent de l'escalat; `GradedSpec` es unique per `(grading_version,pom,size_label)`. Referencies: `backend/fhort/fitting/models.py:62-95`, `backend/fhort/fitting/models.py:163-195`.

**FET**: `PropagatedEditor` s'alimenta de `GET /taula-mesures/`, projecta `size_run/base/rows` amb `buildEscalatGroups` i `buildEscalatRows`, i pinta `MeasureGrid`. Referencies: `frontend/src/pages/PropagatedEditor.jsx:23-39`, `frontend/src/pages/PropagatedEditor.jsx:98-104`.

**FET**: `buildEscalatRows` crea un grup per talla, amb history `vigent` i activa editable; el valor ve de `base_value_cm` per talla base i `graded[size]` per no-base. Referencies: `frontend/src/components/model/fittingGridAdapter.jsx:101-139`.

**FET**: editar Escalat crida `escalat/ajustar-talla`: si regla LINEAR/canonica, ancora la talla, deriva nova base amb `propaga_ancoratges`, escriu `BaseMeasurement` i re-genera; si STEP/sense regla i no-base, escriu `ModelGradingOverride`; sempre retorna `linies` per refrescar la fila. Referencies: `frontend/src/pages/PropagatedEditor.jsx:40-48`, `backend/fhort/models_app/views.py:1434-1452`, `backend/fhort/models_app/views.py:1500-1555`.

**FET**: `propaga_ancoratges` calcula tots els valors del run a partir d'una talla ancorada i de `increment_base` + break per etiqueta; es simetric respecte del run. Referencies: `backend/fhort/pom/grading_utils.py:552-610`.

## Pregunta 5 — Frontera real i compartit

**FET**: els tres moments comparteixen `BaseMeasurement` com a nucli de base: POM el crea o l'actualitza, Mesures hi promou una presa acceptada, Escalat el pot reescriure quan una correccio propagada recalcula la base. Referencies: `backend/fhort/models_app/views.py:787-849`, `backend/fhort/models_app/services_size_check.py:163-185`, `backend/fhort/models_app/views.py:1507-1523`, `backend/fhort/models_app/views.py:1558-1566`.

**FET**: la frontera real POM/Mesures no es visual: POM admet `BaseMeasurement` inexistent, `TEMPLATE` buit, POMs temporals i soft-delete estructural; Mesures requereix base existent amb valor per crear `SizeCheckLine`. Referencies: `backend/fhort/models_app/views.py:556-573`, `frontend/src/components/model/MeasuresEntryPanel.jsx:229-236`, `backend/fhort/models_app/services_size_check.py:23-38`.

**FET**: la frontera Mesures/Escalat es la propagacio: abans d'Escalat no hi ha necessitat de `GradedSpec`; Escalat llegeix `graded` de `taula-mesures` i requereix `SizeFitting`/`GradingVersion` generada per editar talles propagades. Referencies: `backend/fhort/models_app/views.py:680-699`, `backend/fhort/models_app/views.py:1434-1452`, `backend/fhort/models_app/views.py:1483-1486`.

**FET**: ordre global es compartit conceptualment (`BaseMeasurement.ordre`) i tots els lectors principals ordenen per `ordre`; pero hi ha dos endpoints de reorder: `reorder-measurements` i `base-measurements/reorder`. Referencies: `backend/fhort/models_app/models.py:474-480`, `backend/fhort/models_app/views.py:675-678`, `backend/fhort/models_app/views.py:852-872`, `backend/fhort/models_app/views.py:1595-1618`.

**FET**: `nom_fitxa` es compartit conceptualment i viu a `BaseMeasurement`; `MeasureGrid` el persisteix via PATCH a `base-measurements`, pero `EditableTable` l'envia a `set-measurements` i el backend no el desa en els defaults. Referencies: `backend/fhort/models_app/models.py:465-470`, `frontend/src/components/model/MeasureGrid.jsx:164-178`, `frontend/src/components/model/CheckMeasureEditor.jsx:235-241`, `frontend/src/components/EditableTable/EditableTable.jsx:121-126`, `backend/fhort/models_app/views.py:818-829`.

**FET**: la regla resident (`ModelGradingRule`) es compartida per Mesures/Escalat/fitting i el motor la llegeix amb prioritat sobre `GradingRuleSet`; POM pot materialitzar-la inicialment, pero `EditableTable` no l'edita avui. Referencies: `backend/fhort/models_app/models.py:573-624`, `backend/fhort/pom/services.py:356-376`, `backend/fhort/models_app/services.py:67-87`, `frontend/src/components/EditableTable/EditableTable.jsx:97-110`.

💡 **PROPOSTA (a validar)**: el contracte unic d'alimentacio de `MeasureGrid` no hauria de ser "el grid endevina el moment", sino un provider explicit per moment:

- `entry/POM`: base rows amb `tmpId|bm_id`, POM add/search/create, save en bloc, keep/delete, ordre, nom_fitxa, regla inicial.
- `base/Mesures`: base-stages + active take (`SizeCheckLine`) + resolve.
- `grading/Escalat`: taula propagada vigent + active ajust per talla.

💡 **PROPOSTA (a validar)**: reusar el que ja esta resolt: `MeasureGrid` com esquelet visual, `fittingGridAdapter` com patró d'adapters, `set_pom_regim_view` per regla viva, `base-measurements/reorder` per ordre unic, `BaseMeasurementSerializer`/PATCH per `nom_fitxa`, `generate_grading_view` i `escalat_ajustar_talla` per Escalat.

## Pregunta 6 — Riscos de convergencia

**FET**: consumidors actuals de `MeasureGrid`:

- `CheckMeasureEditor` per Mesures/check. Referencies: `frontend/src/components/model/CheckMeasureEditor.jsx:311-314`.
- `PropagatedEditor` per Escalat. Referencies: `frontend/src/pages/PropagatedEditor.jsx:98-104`.
- `FittingDetail` per fitting en lectura i edicio. Referencies: `frontend/src/pages/FittingDetail.jsx:675-680`, `frontend/src/pages/FittingDetail.jsx:731-737`.
- `fittingGridAdapter` proveeix adapters `buildFittingGroups/Rows`, `buildEscalatGroups/Rows`, `makeFittingOnSave`. Referencies: `frontend/src/components/model/fittingGridAdapter.jsx:1-5`, `frontend/src/components/model/fittingGridAdapter.jsx:15-53`, `frontend/src/components/model/fittingGridAdapter.jsx:101-149`.

**FET**: `FittingDetail` depen de `MeasureGrid` com a component amb buffer intern; remunta per peça amb `key={activePieceId}`. Referencies: `frontend/src/pages/FittingDetail.jsx:480-483`, `frontend/src/pages/FittingDetail.jsx:506-514`.

**FET**: fitting te motor propi: `PieceFittingLine` parteix de `GradedSpec`; `makeFittingOnSave` fa PATCH si STEP i `propagar` si LINEAR; tancar fitting promou nomes talla base a `BaseMeasurement` i crea nova `GradingVersion`. Referencies: `backend/fhort/fitting/services.py:320-338`, `frontend/src/components/model/fittingGridAdapter.jsx:141-149`, `backend/fhort/fitting/services.py:341-455`.

**FET**: afegir un mode `entry` dins `MeasureGrid` tocaria una API usada per check/fitting/escalat. Les props actuals assumeixen que cada cel.la activa te `lineId` i que l'ordre usa `bm_id`; POM necessita files temporals i save en bloc. Referencies: `frontend/src/components/model/MeasureGrid.jsx:211-221`, `frontend/src/components/model/MeasureGrid.jsx:229-239`, `frontend/src/components/model/MeasureGrid.jsx:263-280`.

💡 **PROPOSTA (a validar)**: escape valve si l'extraccio es arriscada: no convertir `MeasureGrid` en component amb mode intern gran. Mantenir `MeasureGrid` estable per check/fitting/escalat i crear un adapter/presenter `EntryMeasureGrid` que comparteixi presentacio/cel.les, pero encapsuli contracte POM (tmp rows, add/delete, bulk save). Aixo evita regressions sobre els tres consumidors vius.

## Mapa final de fets

**FET**: POM/genesi esta parcialment resolt amb `MeasuresEntryPanel + EditableTable + materialitzar-poms + set-measurements + import`, pero queda divergent en `nom_fitxa`, doble reorder i absencia de regla/delta/break dins la mateixa graella d'entrada.

**FET**: Mesures esta resolt amb `CheckMeasureEditor + MeasureGrid + base-stages + SizeCheck/SizeCheckLine + resolve`.

**FET**: Escalat esta resolt amb `PropagatedEditor + MeasureGrid + taula-mesures + generate_grading_view + GradedSpec + escalat_ajustar_talla`.

**FET**: la decisio de quin moment alimenta la graella viu a `ModelSheet`/context de tasca/model (`verge`, `entryMode`, `taskParam`, `editing`, `grading-status`), no a `MeasureGrid`.

💡 **PROPOSTA (a validar)**: abans de fusionar `EditableTable→MeasureGrid`, decidir contractualment el provider POM. La convergencia segura es per adapter de dades i no per aparenca.
