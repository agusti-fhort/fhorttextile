# DIAGNOSI — Contracte de dades: EditableTable (entrada) vs MeasureGrid (treball)

Data: 2026-06-26  
Scope: read-only sobre codi. Cap canvi de codi.

## Resum executiu

**VEREDICTE: contractes divergents → HOMOGENEITZAR aspecte, pero mantenir dues superfícies o crear un adapter explicit de genesi.**

**FET**: `EditableTable` i `MeasureGrid` poden llegir dades que acaben tocant el mateix nucli persistent (`BaseMeasurement`), pero no comparteixen el mateix contracte d'entrada/sortida ni el mateix moment de vida de la dada.

- `EditableTable` es la superfície de **genesi/estructura**: crea o actualitza `BaseMeasurement`, pot tenir POMs temporals sense `bm_id`, soft-deleteja files absents, desa en bloc i llegeix una taula plana `taula-mesures`.
- `MeasureGrid` en `CheckMeasureEditor` es la superfície de **treball sobre una presa**: llegeix historial derivat (`base-stages`) + una entitat transitoria `SizeCheck/SizeCheckLine`, desa cel.la a cel.la a `SizeCheckLine`, i només en resoldre promou valors acceptats a `BaseMeasurement`.
- Les regles/deltes editables reals viuen a `ModelGradingRule` i s'editen des de `MeasureGrid`; el `delta` que mostra `EditableTable` es lectura derivada/calculada de valors ja existents.

**PROPOSTA (a validar)**: no fusionar encara com "una sola graella" sense abans definir un adapter de contracte per a genesi. El cami segur es homogeneitzar UI i, si es vol convergir, fer que `EditableTable` sigui substituida per `MeasureGrid` nomes quan hi hagi un proveidor `entry` que preservi explícitament: POMs temporals, alta de POM, materialitzacio, soft-delete, save en bloc, ordre, `nom_fitxa`, tolerancies i regla resident.

## Pregunta 1 — Que llegeix cada graella

### EditableTable via MeasuresEntryPanel

**FET**: `MeasuresEntryPanel` llegeix `GET /api/v1/models/{id}/taula-mesures/` per carregar la taula d'entrada si existeix. Ho fa a `reloadTable` i a la carrega inicial. Referencies: `frontend/src/components/model/MeasuresEntryPanel.jsx:48-52`, `frontend/src/components/model/MeasuresEntryPanel.jsx:90-97`.

**FET**: tambe llegeix `GET /api/v1/models/{id}/poms-suggerits/` per proposar POMs del `GarmentTypeItem`, i `GET /api/v1/item-base-measurements/?garment_type_item=...` per decidir si ofereix sembra amb valors. Referencies: `frontend/src/components/model/MeasuresEntryPanel.jsx:75-82`, `frontend/src/components/model/MeasuresEntryPanel.jsx:105-113`.

**FET**: el contracte de `taula-mesures` retorna:

- capcalera: `model_id`, `base_size`, `size_run`, `size_run_complet`, `sizes_amb_dades`, `deltes`, `tancat`;
- files `rows` amb `id` (= `BaseMeasurement.id`), `ordre`, `pom_id`, `pom_code`, `nom_fitxa`, noms, `base_value_cm`, `is_key`, `origen`, `notes`, `graded`, i camps de regla (`logica`, `increment_base`, `increment_break`, `talla_break_label`).

Referencies: `backend/fhort/models_app/views.py:714-738`, `backend/fhort/models_app/views.py:773-784`.

**FET**: `EditableTable` rep una forma plana: `rows`, `sizeRun`, `baseSize`, `deltes`. Si no hi ha files persistides, construeix files temporals `tmp-{pom_id}` amb `pom_id`, `pom_code`, noms, `nom_fitxa`, `base_value_cm:null`, `graded:{}`, `ordre`. Referencies: `frontend/src/components/model/MeasuresEntryPanel.jsx:229-243`.

**FET**: el delta que veu `EditableTable` ve de `deltes` retornat pel backend; el fallback local nomes calcula sobre `sizeRun` si no hi ha `deltes`. Referencia: `frontend/src/components/EditableTable/EditableTable.jsx:97-110`.

### MeasureGrid via CheckMeasureEditor

**FET**: `CheckMeasureEditor` no llegeix `taula-mesures` per construir la graella de check. Llegeix en paral.lel:

- `GET /api/v1/models/{id}/base-stages/`;
- en mode treball, `POST /api/v1/size-checks/open/ {model_id}`;
- en mode consulta, `GET /api/v1/size-checks/?model=...&ordering=-created_at&page_size=1` + `GET /api/v1/size-checks/{id}/`.

Referencies: `frontend/src/components/model/CheckMeasureEditor.jsx:183-191`, `frontend/src/api/endpoints.js:49-50`, `frontend/src/api/endpoints.js:391-397`.

**FET**: `base-stages` retorna una taula de talla base amb `stages` derivats del log i `rows` amb `pom_id`, `pom_code`, `nom_fitxa`, noms, `is_key`, tolerancies, `base_value_cm`, `base_measurement_id`, i `takes`. Referencies: `backend/fhort/models_app/views.py:1621-1630`, `backend/fhort/models_app/views.py:1637-1648`, `backend/fhort/models_app/views.py:1676-1704`.

**FET**: el check aporta `lines`: `SizeCheckLine` amb `valor_teoric`, `valor_real`, decisio/nota, tolerancia i regla per POM. El serializer carrega tolerancia i ordre vigents des de `BaseMeasurement`, regles via `_load_grading_rules`, i ordena per `BaseMeasurement.ordre`. Referencies: `backend/fhort/models_app/serializers_size_check.py:78-89`, `backend/fhort/models_app/serializers_size_check.py:91-127`, `backend/fhort/models_app/serializers_size_check.py:129-131`.

**FET**: `CheckMeasureEditor` adapta `baseData.rows + check.lines` a la forma propia de `MeasureGrid`: `groups` amb historia (`stages`) + columna activa `Real` + trail `Decisio/Nota`; `rows` amb `cells.base.history`, `cells.base.active`, i `cells.base.trail`. Referencies: `frontend/src/components/model/CheckMeasureEditor.jsx:245-277`.

### Mateixa font?

**FET**: no. Comparteixen parcialment `BaseMeasurement`, pero no llegeixen la mateixa font:

- entrada: `taula-mesures` = estat actual pla del model + grading propagat vigent + deltes calculats;
- treball/check: `base-stages` = llibre major derivat de `MeasurementChangeLog` + `SizeCheck/SizeCheckLine` = presa transitoria.

Referencies: `backend/fhort/models_app/views.py:661-784`, `backend/fhort/models_app/views.py:1621-1704`, `backend/fhort/models_app/models.py:486-535`, `backend/fhort/models_app/models.py:737-801`.

## Pregunta 2 — Que escriu cada graella i per quin cami

### Entrada / EditableTable

**FET**: la materialitzacio de POMs passa per `POST /api/v1/models/{id}/materialitzar-poms/`. El frontend la crida en confirmar sembra i tambe en cas verge sense valors d'item. Referencies: `frontend/src/components/model/MeasuresEntryPanel.jsx:54-67`, `frontend/src/components/model/MeasuresEntryPanel.jsx:116-121`.

**FET**: `EditableTable` desa en bloc a `POST /api/v1/models/{modelId}/set-measurements/` amb `measurements` i `keep_pom_ids`. Cada measurement inclou `pom_id`, `base_value_cm`, `notes`, `nom_fitxa`; `keep_pom_ids` serveix per persistir eliminacions. Referencies: `frontend/src/components/EditableTable/EditableTable.jsx:118-135`.

**FET**: despres intenta reordenar per `POST /api/v1/models/{modelId}/reorder-measurements/` amb `order` de `BaseMeasurement.id`. Referencies: `frontend/src/components/EditableTable/EditableTable.jsx:137-143`, `backend/fhort/models_app/views.py:852-872`.

**FET**: el backend de `set-measurements` fa `update_or_create(BaseMeasurement)` per `(model,pom)`, escriu `base_value_cm`, `notes`, `origen='MANUAL'`, reactiva `is_active`, copia tolerancia per defecte del POM, i soft-deleteja `BaseMeasurement` actius que no son a `keep_pom_ids`. Referencies: `backend/fhort/models_app/views.py:787-849`.

**FET**: malgrat que el frontend envia `nom_fitxa`, el backend de `set-measurements` no el posa als `defaults`; per tant aquest cami no persisteix `nom_fitxa`. Referencies: frontend payload a `frontend/src/components/EditableTable/EditableTable.jsx:121-126`; defaults backend a `backend/fhort/models_app/views.py:818-829`.

**FET**: `set-measurements` no genera grading; el comentari diu explícitament que nomes fa upsert de `BaseMeasurement`, i que `GradedSpec` viu exclusivament a `generar-grading -> generate_graded_specs`. Referencies: `backend/fhort/models_app/views.py:843-846`.

### Treball / MeasureGrid / CheckMeasureEditor

**FET**: en mode treball, `CheckMeasureEditor` obre o reutilitza un `SizeCheck` pendent amb `POST /api/v1/size-checks/open/`; el servei crea una `SizeCheckLine` per cada `BaseMeasurement` actiu amb valor, fent snapshot de `base_value_cm` a `valor_teoric`. Referencies: `backend/fhort/models_app/views_size_check.py:48-60`, `backend/fhort/models_app/services_size_check.py:16-38`, `backend/fhort/models_app/services_size_check.py:41-78`.

**FET**: la cel.la activa de `MeasureGrid` desa via `onSave(lineId,value)`, que en check es `PATCH /api/v1/size-check-lines/{id}/` amb `{valor_real}`. Referencies: `frontend/src/components/model/CheckMeasureEditor.jsx:228`, `frontend/src/components/model/MeasureGrid.jsx:263-280`, `frontend/src/api/endpoints.js:404-407`.

**FET**: decisio i nota tambe s'escriuen a `SizeCheckLine` via `sizeCheckLines.update`. Referencies: `frontend/src/components/model/CheckMeasureEditor.jsx:54-68`, `backend/fhort/models_app/views_size_check.py:78-83`, `backend/fhort/models_app/serializers_size_check.py:14-20`.

**FET**: la resolucio final passa per `POST /api/v1/size-checks/{id}/resolve/`; si queda Acceptat, promou les linies acceptades amb `valor_real` a `BaseMeasurement` amb `origen='CHECKED'`, i si hi ha canvi de base + deltes, regradua via `bump_grading_version_and_generate`. Referencies: `frontend/src/components/model/CheckMeasureEditor.jsx:210-225`, `backend/fhort/models_app/views_size_check.py:62-75`, `backend/fhort/models_app/services_size_check.py:157-185`, `backend/fhort/models_app/services_size_check.py:189-209`.

**FET**: `MeasureGrid` tambe escriu ordre i nomenclatura per-model des de `CheckMeasureEditor`: ordre a `POST /models/{id}/base-measurements/reorder/`, `nom_fitxa` a `PATCH /api/v1/base-measurements/{id}/`. Referencies: `frontend/src/components/model/CheckMeasureEditor.jsx:229-241`, `frontend/src/api/endpoints.js:68-73`, `backend/fhort/models_app/views.py:1595-1618`.

**FET**: els deltes/breaks editables s'escriuen des de la columna `RegleEditCell` a `POST /api/v1/models/{model_id}/pom/{pom_id}/regim/`, que fa upsert de `ModelGradingRule`. Referencies: `frontend/src/components/model/CheckMeasureEditor.jsx:116-142`, `frontend/src/api/endpoints.js:41-45`, `backend/fhort/models_app/views.py:2142-2215`.

### Mateix contracte d'escriptura?

**FET**: no.

- Entrada: `set-measurements` escriu `BaseMeasurement` directament i en bloc, amb `keep_pom_ids` per eliminar.
- Treball/check: escriu primer `SizeCheckLine`, despres `resolve_size_check` decideix si promou a `BaseMeasurement`.
- Regla/delta/break: no l'escriu `EditableTable`; l'escriu `MeasureGrid` via `ModelGradingRule`.

Referencies: `backend/fhort/models_app/views.py:787-849`, `backend/fhort/models_app/services_size_check.py:98-118`, `backend/fhort/models_app/services_size_check.py:157-209`, `backend/fhort/models_app/views.py:2142-2157`.

## Pregunta 3 — Sistema de generacio de l'entrada

### D'on venen els deltes

**FET**: `taula-mesures` carrega regles per POM amb `_load_grading_rules(model)`, que prioritza `ModelGradingRule` actiu i fa fallback a `GradingRule` del `model.grading_rule_set`. Referencies: `backend/fhort/models_app/views.py:702-709`, `backend/fhort/pom/services.py:356-376`.

**FET**: pero el camp `deltes` que consumeix `EditableTable` no surt directament de `ModelGradingRule.increment_base`; es calcula com la mitjana d'increments entre talles amb dades dins `taula-mesures`, mirant `base_value_cm` i `graded` vigent. Referencies: `backend/fhort/models_app/views.py:740-763`.

**FET**: el `GradingRuleSet` vigent penja del `Model` (`model.grading_rule_set`) i el `GarmentTypeItem` tambe te `grading_rule_set` com a context de grading de l'item. Referencies: `backend/fhort/models_app/models.py:193-199`, `backend/fhort/tasks/models.py:281-292`.

**FET**: les regles residents del model (`ModelGradingRule`) contenen `increment_base`, `increment_break`, `talla_break_label`, `talla_break_pos`, amb unique `(model,pom)`. Referencies: `backend/fhort/models_app/models.py:573-583`, `backend/fhort/models_app/models.py:608-624`.

### Breaks

**FET**: els breaks es defineixen a la regla (`increment_break`, `talla_break_label`, `talla_break_pos`) i s'escriuen amb `set_pom_regim_view`. El backend recalcula `talla_break_pos` si la label existeix al `size_run_model`. Referencies: `backend/fhort/models_app/models.py:608-613`, `backend/fhort/models_app/views.py:2147-2156`, `backend/fhort/models_app/views.py:2207-2215`.

**FET**: `EditableTable` no te controls ni endpoint per escriure breaks. Nomes mostra una columna `Delta` calculada. Referencies: `frontend/src/components/EditableTable/EditableTable.jsx:188-198`, `frontend/src/components/EditableTable/EditableTable.jsx:301-304`.

### Materialitzacio de POMs

**FET**: `materialitzar-poms` instancia POMs de l'item com a `BaseMeasurement`, copiant `is_key/ordre` de `GarmentPOMMap`. Si hi ha `ItemBaseMeasurement`, copia `base_value_cm`, `nom_fitxa`, tolerancies i `origen='ITEM_STANDARD'`; si no, crea fila buida `origen='TEMPLATE'`, `base_value_cm=None`. Referencies: `backend/fhort/models_app/views.py:516-528`, `backend/fhort/models_app/views.py:542-573`.

**FET**: es idempotent sota sobirania del model: si ja existeix una fila, nomes sembra si es `TEMPLATE` buit i l'item porta valor; no trepitja files amb valor o origen mes especific. Referencies: `backend/fhort/models_app/views.py:526-528`, `backend/fhort/models_app/views.py:576-589`.

**FET**: el model `BaseMeasurement` permet `base_value_cm=None` per POM materialitzat sense valor, te `is_key`, `is_active`, `tolerancia_minus/plus`, `nom_fitxa`, `origen` i `ordre`; unique per `(model,pom)`. Referencies: `backend/fhort/models_app/models.py:428-480`.

**FET**: `ItemBaseMeasurement` es plantilla d'item, no instancia; a la sembra es copia a `BaseMeasurement` del model i a partir d'aqui el model es sobira. Referencies: `backend/fhort/pom/models.py:448-459`, `backend/fhort/pom/models.py:463-473`.

## Pregunta 4 — Integritat i invariants divergents

**FET**: l'entrada pot tenir files sense valor (`TEMPLATE`, `base_value_cm=None`) i fins i tot files temporals encara no persistides (`tmp-*`). El check nomes materialitza linies per `BaseMeasurement` actius amb valor no nul. Referencies: `frontend/src/components/model/MeasuresEntryPanel.jsx:229-236`, `backend/fhort/models_app/models.py:444-446`, `backend/fhort/models_app/services_size_check.py:23-36`.

**FET**: l'entrada pot eliminar POMs de l'estructura amb `keep_pom_ids` i soft-delete `is_active=False`; el check no te contracte d'eliminacio de POM, nomes pot descartar o acceptar una presa. Referencies: `frontend/src/components/EditableTable/EditableTable.jsx:128-135`, `backend/fhort/models_app/views.py:795-841`, `backend/fhort/models_app/services_size_check.py:104-110`.

**FET**: l'entrada escriu directament la base; el check escriu una presa auditada (`SizeCheckLine`) i nomes en resolucio promou alguns valors a base. Referencies: `backend/fhort/models_app/views.py:818-829`, `backend/fhort/models_app/models.py:773-795`, `backend/fhort/models_app/services_size_check.py:163-185`.

**FET**: `base-stages` depen de `MeasurementChangeLog`, que nomes registra canvis de `base_value_cm`; reorders, `is_active` i `nom_fitxa` no generen entrada de log. Referencies: `backend/fhort/models_app/signals.py:183-190`, `backend/fhort/models_app/signals.py:201-230`.

**FET**: ordre global existeix als dos mons, pero amb endpoints diferents. `EditableTable` usa `reorder-measurements` amb `{order:[bm_id]}`; `MeasureGrid` usa `base-measurements/reorder` amb `{ids:[bm_id]}`. Referencies: `frontend/src/components/EditableTable/EditableTable.jsx:137-143`, `backend/fhort/models_app/views.py:852-872`, `frontend/src/components/model/CheckMeasureEditor.jsx:229-234`, `backend/fhort/models_app/views.py:1595-1618`.

**FET**: la columna POM/nomenclatura curta no esta alineada completament. `MeasureGrid` edita `nom_fitxa` per-model a `BaseMeasurement` via `PATCH base-measurements/{id}`. Referencies: `frontend/src/components/model/MeasureGrid.jsx:164-178`, `frontend/src/components/model/CheckMeasureEditor.jsx:235-241`. `EditableTable` permet editar `nom_fitxa` localment i l'envia a `set-measurements`, pero el backend no el persisteix en aquest endpoint. Referencies: `frontend/src/components/EditableTable/EditableTable.jsx:121-126`, `backend/fhort/models_app/views.py:818-829`.

**FET**: nomenclatura descriptiva tampoc es el mateix contracte. `MeasureGrid` mostra dues linies i, segons mode, separa codi curt (`nom_fitxa`) de nom EN/local. Referencies: `frontend/src/components/model/MeasureGrid.jsx:119-129`, `frontend/src/components/model/MeasureGrid.jsx:164-168`. `EditableTable` tracta `nom_ca` com a camp editable local de descripcio, pero `set-measurements` tampoc el persisteix. Referencies: `frontend/src/components/EditableTable/EditableTable.jsx:286-288`, `backend/fhort/models_app/views.py:818-829`.

**FET**: els deltes/breaks son invariant de regla (`ModelGradingRule`) en el treball, pero a l'entrada el delta mostrat es derivat de dades propagades existents; no hi ha edicio de break ni de regla dins `EditableTable`. Referencies: `frontend/src/components/model/CheckMeasureEditor.jsx:116-142`, `backend/fhort/models_app/views.py:2142-2215`, `backend/fhort/models_app/views.py:754-763`, `frontend/src/components/EditableTable/EditableTable.jsx:97-110`.

## Veredicte

**FET**: amb el codi actual, no hi ha "mateix contracte de dades" entre `EditableTable` i `MeasureGrid(CheckMeasureEditor)`.

**FET**: comparteixen entitats finals (`BaseMeasurement`, ordre, `nom_fitxa`, regla resident), pero les operacions son diferents:

- genesi: crear POMs de plantilla, POMs temporals, base buida, entrada en bloc, eliminacio estructural, materialitzacio idempotent;
- treball: obrir presa, snapshot teoric, autosave de mesura real, decisio/nota, resolucio, promocio auditada a base, possible regrading.

**PROPOSTA (a validar)**: decisio de producte/arquitectura recomanada:

1. **Curt termini**: HOMOGENEITZAR visualment `EditableTable` amb `MeasureGrid` (nomenclatura, ordre, sticky columns, controls), mantenint dos contractes.
2. **Convergencia futura**: nomes fusionar si es crea un `MeasureGrid` provider/mode `entry` amb contracte propi i tests d'integritat per:
   - files temporals sense `BaseMeasurement.id`;
   - materialitzacio `ITEM_STANDARD/TEMPLATE`;
   - soft-delete `is_active=False`;
   - `nom_fitxa` persistent per-model;
   - alta/cerca de POM;
   - save en bloc o estrategia equivalent;
   - deltes/breaks des de `ModelGradingRule`, no delta derivat ambigu.

**Conclusio**: avui la fusio directa seria falsa per dades. La decisio correcta basada en integritat es **HOMOGENEITZAR aspecte, mantenint contractes separats**, amb una possible migracio posterior a una graella comuna nomes mitjancant adapters de dades explicits.
