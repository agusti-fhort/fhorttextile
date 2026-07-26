# DIAGNOSI — W6 TALLER-GTI i EL PATRÓ A LA FITXA TÈCNICA

> **Data:** 2026-07-14 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
> **Abast:** (1) els 4 deltes del disseny W6 (Taller-GTI) contra el codi real; (2) el camí del patró
> cap a la fitxa tècnica — tab Fitxers, element de canvas, pipeline de PDF i `render-signed`.
> **Encàrrec:** brief W6-GTI + FITXA. Serveix per dimensionar tres sprints: **W6 Taller-GTI**,
> **Fitxers unificats** i **Peces a la fitxa**.
>
> **Convenció:** tota afirmació porta `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi**
> (verificat, no especulat). Les propostes van marcades `💡 PROPOSTA (a validar)` i **no** són
> decisions: les decisions són humanes (Patró C).
>
> **Guardes:** cap escriptura de codi, cap migració, cap restart · BD només `SELECT` (schema
> `fhort`) · únic fitxer creat: aquest. Sessió concurrent escrivint a `App.jsx` (D10): no s'ha
> tocat res.

---

## RESUM EXECUTIU

1. **El XOR model/item no és feina pendent: ja està construït i la porta d'upload d'item també.**
   `PatternFile` té els dos FK i el `CheckConstraint` XOR **des de la migració inicial**
   (`patterns/models.py:42-56`, `:109-115`; `patterns/migrations/0001_initial.py:112-115`), i
   `PatternFileViewSet.create` **ja accepta `garment_type_item`** amb resolució de propietari i
   guard de versió del mateix amo (`patterns/views.py:219-344`), amb `filterset_fields` que ja
   l'inclou (`:196`). **El backend d'entrada del Taller-GTI existeix avui.** El que falta no és la
   porta: és tot el que hi ha **darrere**, que encara pregunta `model_id`.

2. **El delta (4) del disseny està INFRAVALORAT: no és una taula, són TRES.** A més de
   `SewRelation.model` (`patterns/models.py:440-442`), tenen la mateixa FK **NOT NULL** a
   `models_app.Model` les dues taules de rebuig d'anotació assistida: `SewProposalRejection`
   (`:510-512`) i `DartProposalRejection` (`:559-561`), i s'escriuen des dels mateixos endpoints
   (`annotation_views.py:633`, `:676`). Fer el XOR només a `SewRelation` deixaria els rebuigs
   petant amb `IntegrityError` sobre un patró d'item. **Migració trivial però triple** (4 files
   vives a `SewRelation`, 0 a les de rebuig; cap backfill: totes complirien el XOR).

3. **El delta (2) (SENSE rellotge) es desactiva sol: cap línia de `patterns/` coneix `ModelTask`.**
   Verificat per grep exhaustiu al backend del motor: l'única coincidència és una dependència
   d'ordre de migracions (`patterns/migrations/0001_initial.py:15`). El rellotge viu **només al
   frontend** i ja és tolerant al fallo (`TallerPatro.jsx:170-194`: el `.catch` no bloqueja, només
   desa l'error). **Però compte amb l'efecte col·lateral:** avui el gate de l'anotació **no és una
   capability, és el rellotge** — els botons POM/tram/pinça/cosir són `disabled={!tascaId}`
   (`TallerPatro.jsx:1148,1156,1166,1173`). Treure el rellotge al catàleg **treu el gate**: cal
   substituir-lo, no només suprimir-lo.

4. **El delta (3) (permisos CONFIGURE) és una incoherència ja viva, no una feina nova.**
   Tot el catàleg gata l'escriptura amb `CONFIGURE` (`item_fitxer_views.py:48-50`,
   `tasks/views_b.py:864-868`, `pom/views.py:259-264`), i **només `admin` té CONFIGURE**
   (`accounts/capabilities.py:20-26`). `PatternFileViewSet` és **l'única superfície d'escriptura
   que ja pot apuntar a un `GarmentTypeItem` i no aplica el gate** (`patterns/views.py:205-211`,
   amb el comentari "L'escriptura va al MODEL, no a un catàleg" — premissa que el XOR ja ha
   invalidat). **Avui, qualsevol autenticat pot pujar un `PatternFile` a un item del catàleg.**

5. **El delta (1) (2n contenidor) està tapiat per un 400 explícit.** `model-poms` retorna **400 si
   el patró no té model** (`patterns/views.py:383-390`), i `grading-versions` retorna **`[]`**
   (`:471-472`) — o sigui que un patró d'item avui no té ni llista de treball ni exportació de
   niada. La font germana existeix i és neta (`GarmentPOMMap` + `ItemBaseMeasurement`,
   `pom/models.py:434-501`), però **NO EXISTEIX cap camí canònic**: tres consumidors copien el
   mateix query amb formes de sortida diferents (`pom/wizard_views.py:77`,
   `models_app/views.py:651`, `:699`).

6. **PART 2 — la premissa del brief és falsa, i a favor nostre: el PDF de la fitxa NO corre al
   servidor.** Es genera **100% al navegador** (Konva → PNG → `pdf-lib`,
   `TechSheetEditor.jsx:3017-3056`); el backend només **rep el PDF ja fet i el desa**
   (`ftt_document_views.py:163`). Per tant **`render-signed` NO CAL per al PDF**: el navegador ja
   sap baixar bytes autenticats i convertir-los a dataURL, i el patró exacte ja està escrit
   (`TechSheetEditor.jsx:3323-3347`). El **generador de PDF ÉS `addObjectToLayer`**
   (`TechSheetEditor.jsx:806`): un tipus d'element nou hi entra **sense tocar ni una línia de
   Python, sense migracions i sense canviar l'API de desat**.

7. **El sprint més barat dels tres és "Peces a la fitxa"; el més car és W6.** Ordre de cost real:
   Peces a la fitxa (~6-8 punts, tots a un fitxer + i18n) < Fitxers unificats (1 punt d'entrada,
   però amb col·lisió d'ids i accions per enrutar) < W6 Taller-GTI (3 migracions + ~13 punts
   backend + ~7 frontend + una **entrada d'UI que no existeix**).

---

# PART 1 — W6 TALLER-GTI

## BLOC A — `ItemFitxer` com a host de `PatternFile` (el camí d'upload/list)

### A.1 El XOR ja existeix, i és sòlid

`PatternFile` (`patterns/models.py:33`) ja neix amb els dos amos:

| element | fitxer:línia |
|---|---|
| `model` FK **null=True** | `patterns/models.py:42-45` |
| `garment_type_item` FK **null=True** → `tasks.GarmentTypeItem` | `patterns/models.py:46-50` |
| `source_asset` FK → **`models_app.ItemFitxer`**, SET_NULL, `related_name='pattern_files_sembrats'` | `patterns/models.py:53-56` |
| `CheckConstraint` `patternfile_xor_model_item` | `patterns/models.py:109-115` |
| guard de Python `clean()` | `patterns/models.py:129-132` |
| migració (des del **primer dia**) | `patterns/migrations/0001_initial.py:41-44`, `:112-115` |

**`GarmentTypeItemAsset` NO EXISTEIX** — i està documentat al codi que qui fa de biblioteca
d'actius d'item és `ItemFitxer` (`patterns/models.py:51-52`). El disseny (V2 §4.3, §4.4) hi
al·ludeix com a hipòtesi; el codi ja ha decidit. **`source_asset` apunta a `ItemFitxer`, no a cap
asset nou.**

### A.2 El camí d'upload/list d'un fitxer d'item (la referència a calcar)

| baula | fitxer:línia |
|---|---|
| router | `models_app/urls.py:44` (`item-fitxers`) |
| ViewSet (Create+Destroy+ReadOnly, multipart) | `models_app/item_fitxer_views.py:28-36` |
| permisos | `item_fitxer_views.py:40-51` — **escriptura = `CONFIGURE`**; `download_signed` = `AllowAny` |
| `create()` (no passa pel serializer) | `item_fitxer_views.py:57-88` |
| validació (extensió + 20 MiB) | `services_fitxers.py:36-67` |
| servei d'escriptura | `services_fitxers.save_item_file:139-178` |
| serializer (100% read-only) | `models_app/serializers.py:64-88` |
| storage (namespace de tenant) | `settings.py:185-187` → `MEDIA_ROOT/<schema>/items/<gti_id>/` |
| pont catàleg→model | `item_fitxer_views.py:126-172` (`usar-al-model`) |

### A.3 Què falta a l'API perquè accepti `garment_type_item` — **quasi res**

L'entrada ja hi és. El que queda acoblat a `model`:

| # | punt | fitxer:línia | estat |
|---|---|---|---|
| 1 | `PatternFileViewSet.create` accepta `model` O `garment_type_item` | `patterns/views.py:219-295`, `_resoldre_propietari:297-316` | ✅ **JA FET** |
| 2 | `filterset_fields` amb `garment_type_item` | `patterns/views.py:196` | ✅ **JA FET** |
| 3 | serializer d'escriptura | no n'hi ha (tot read-only, `patterns/serializers.py`) | ✅ **res a fer** |
| 4 | `model-poms` → **400** sense model | `patterns/views.py:383-390` | ❌ **falta la germana d'item** (BLOC B) |
| 5 | `grading-versions` → **`[]`** sense model | `patterns/views.py:471-472` | ❌ decisió de producte (§A.4) |
| 6 | permisos d'escriptura sense `CONFIGURE` | `patterns/views.py:205-211` | ❌ **incoherència** (BLOC D) |
| 7 | frontend: `patterns.list(modelId)` amb `model` **hardcodat** | `frontend/src/api/endpoints.js:622` | ❌ falta la variant d'item |
| 8 | frontend: `fd.append('model', modelId)` a l'upload | `components/pattern/PatternTab.jsx:125` | ❌ ídem |

### A.4 Dos forats que el XOR fa visibles (no els crea: els destapa)

- **L'export d'un patró d'item exportaria ZERO costures, en silenci.** `adapters.sew_specs` té un
  guard que ja anticipa el cas i el resol tornant `()` (`patterns/adapters.py:584-585`). Amb el
  XOR viu, aquest silenci passa de defensiu a **mentider**.
- **L'export d'un patró d'item no té versions de niada per triar**: `grading_versions` les busca
  per `GradingVersion.size_fitting__model_id` (`patterns/views.py:476`), i `build_export` exigeix
  un `grading_version_id` (`:507`, `:543`).
  **❓ PREGUNTA DE PRODUCTE (Patró C):** una base de biblioteca, ¿s'exporta graduada? Si la
  resposta és "les bases GTI es lliuren en talla base i el grading arriba quan el model es
  sembra", llavors l'export d'item **queda fora de W6** i aquests dos forats es tanquen amb un
  missatge honest, no amb codi nou. Si la resposta és "sí", el pont natural és
  `GarmentTypeItem.grading_rule_set` (`tasks/models.py:319-323`) i **W6 creix molt**.

**Veredicte A: la porta d'entrada del Taller-GTI ja és construïda al backend.** El treball real és
darrere (POMs d'item, costures, permisos) i **a la UI, que no té on posar la porta** (BLOC E).

---

## BLOC B — `GarmentPOMMap` a nivell d'item (el 2n contenidor)

### B.1 Forma exacta de la plantilla de POMs d'un item

`GarmentPOMMap` — `pom/models.py:434-465`:

| camp | línia | detall |
|---|---|---|
| `garment_type_item` | `:441-443` | FK → `tasks.GarmentTypeItem`, CASCADE, `related_name='pom_maps'`, `db_constraint=False` (shared↔tenant) |
| `pom` | `:444` | FK → `POMMaster`, PROTECT |
| `obligatori` / `is_key` | `:445-446` | Bool |
| `nivell` | `:449-452` | K/M/O/D — **no s'exposa a l'API** |
| `ordre` | `:453` | ordre de la plantilla |
| `pendent_revisio` | `:455` | clons de germà a revisar |

`unique_together = ('garment_type_item','pom')` (`:461`). **La migració família→item ja està
completada** (l'eix `garment_type` va morir; `pom/models.py:435-437`).

**El VALOR no viu al map: viu al germà `ItemBaseMeasurement`** (`pom/models.py:468-501`), amb la
mateixa clau `(garment_type_item, pom)` + `base_value_cm`, `tol_minus`, `tol_plus`, `nom_fitxa`.
**La plantilla d'un item és, doncs, la JUNTURA de dues taules** — exactament com al model la
juntura ja està aplanada dins `BaseMeasurement`.

### B.2 NO EXISTEIX camí canònic — hi ha tres còpies

No hi ha cap servei ni helper tipus `get_item_pom_template(item)`. Cada consumidor repeteix el
query amb ordre i forma de sortida **diferents**:

| consumidor | fitxer:línia |
|---|---|
| wizard "POMs suggerits" | `pom/wizard_views.py:60-107` (query a `:77`) |
| suggerits per model (resol l'item del model) | `models_app/views.py:638-670` (query a `:651`) |
| **sembra item→model** | `models_app/views.py:672-745` (query a `:699`) |
| CRUD | `pom/views.py:249-278` |

La sembra escriu `BaseMeasurement` (`models_app/models.py:542`) amb `origen='ITEM_STANDARD'` o
`'TEMPLATE'`, i és idempotent i sobirana: només trepitja files `TEMPLATE` buides
(`models_app/views.py:731-743`). **NO EXISTEIX cap `ModelPOM`.**

### B.3 La forma que el 2n contenidor del Taller espera avui

- Frontend: `TallerPatro.jsx:143,403` → `patterns.modelPoms(id)` (`endpoints.js:644`) → pintat a
  `TallerPatro.jsx:898-914` amb `<ModelPomList files={feina?.results||[]}>`
  (`components/pattern/ModelPomList.jsx:19`).
- Backend: `patterns/views.py:367-459`, alimentat per
  `BaseMeasurement.filter(model_id=fp.model_id, is_active=True)` (`:402-407`) creuat amb
  `PatternPOM` per `pom_master_id` (`:393-399`).
- **La frontissa amb la geometria és `pom_master`** (`PatternPOM.pom_master` → `pom.POMMaster`,
  `patterns/models.py:318-320`). `base_measurement` **només és la clau de fila de React**
  (`ModelPomList.jsx:31`).

Forma del JSON (`patterns/views.py:417-459`): `{pattern_file, model, total, ancorats, results:[{
base_measurement, pom_master, codi_client, nom_fitxa, nom_client, nom_canonic, codi_global,
valor_fitxa_cm, tolerancia_minus_cm, tolerancia_plus_cm, is_key, ancorat, pattern_pom,
pattern_piece, peca, valor_mesurat_cm, delta_cm, dins_tolerancia }]}`.

💡 **PROPOSTA (a validar) — la germana `item-poms`.** Una `@action` germana al mateix ViewSet que
torni **la MATEIXA forma**, alimentada per `GarmentPOMMap` + `ItemBaseMeasurement` de
`fp.garment_type_item`: `pom_master` = `map.pom_id` (idèntic), `is_key`/`ordre` del map,
`nom_fitxa`/`valor_fitxa_cm`/`tolerancia_*` de l'`ItemBaseMeasurement` (**null si el POM és a la
plantilla sense valor** — cas que `ModelPomList.jsx:60-63` **ja tracta**), i la clau de fila
substituïda per `map.id` o `pom_master` (l'`ItemBaseMeasurement.id` pot no existir). Amb la mateixa
forma, **`ModelPomList` es reutilitza sense tocar-lo**.

💡 **PROPOSTA (a validar) — aprofitar per crear el camí canònic.** Les tres còpies del query (§B.2)
són la mateixa malaltia que la diagnosi G6 va catalogar ("arreglar-ne un i no l'altre"). Si W6
n'afegeix una quarta sense unificar, en seran quatre.

### B.4 El "mode ASSIGN" ja existeix (el disseny el dona per pendent)

`POMBrowser` amb `mode='assign'` és el gestor de pertinença POM↔item, viu a `/poms`
(`pages/POMs.jsx:45`, `components/POMBrowser/POMBrowser.jsx:111-170`, ruta `App.jsx:333`). **El que
és pendent no és el mode: és la columna de VALORS dins d'ell** (la peça P4 de "Mesures Base per
Item"). El disseny W6 diu "convergeix amb el mode ASSIGN pendent" — la convergència és, doncs, més
petita del que sembla.

**Veredicte B: llest per construir, amb 1 decisió.** La font existeix i és neta; la germana
`item-poms` és una `@action` de baix risc. **Cal decidir si W6 crea el camí canònic o hi afegeix
la quarta còpia.**

---

## BLOC C — `SewRelation` penja de `Model`: dimensió del XOR

### C.1 Qui penja de Model i qui no (taxatiu)

**Pengen de `models_app.Model` (4 entitats):**

| entitat | fitxer:línia | null? |
|---|---|---|
| `PatternFile.model` | `patterns/models.py:42-45` | ✅ ja nullable + XOR |
| `SewRelation.model` | `patterns/models.py:440-442` | ❌ **NOT NULL** |
| `SewProposalRejection.model` | `patterns/models.py:510-512` | ❌ **NOT NULL** |
| `DartProposalRejection.model` | `patterns/models.py:559-561` | ❌ **NOT NULL** |

**Deriven de `PatternFile` (cap FK a Model → hereten la sobirania del XOR, no els cal res):**
`PatternPiece` (`:153-155`), `PatternPoint` (`:215`), `PatternSegment` (`:271`), `PatternPOM`
(`:315-317`), `ExportAcknowledgement` (`:380-381`).

**`GradeRule` NO EXISTEIX com a model de BD** — és el dataclass `GradeRuleData`
(`patterns/engine/geometry.py:305`); l'única persistència de niada és el JSONField
`PatternFile.grade_table` (`patterns/models.py:95`).

### C.2 Radi del canvi: ~13 punts backend + ~7 frontend

**Lectors que filtren per `model_id` (8):** `adapters.py:590` · `annotation_views.py:156`,
`:337-338`, `:421+426` (`filterset_fields=['model','tipus']`), `:211` · `seam_proposals.py:39-40`,
`:54` · `dart_proposals.py:38-39`.

**Escriptors que assignen `model_id` (4):** `annotation_views.py:513-514` (pinça, amb `model`
**obligatori del client**: `:481-484`), `:601-602` (confirmar), `:633` i `:676` (rebuigs).

**EL COLL D'AMPOLLA REAL — `SewRelationViewSet._patro()`** (`annotation_views.py:529-546`): exigeix
`?model=` i resol el patró amb `PatternFile.objects.filter(model_id=...)`. **Alimenta 5 endpoints**
(`propostes`, `confirmar-proposta`, `rebutjar-proposta`, `pinces-proposades`, `rebutjar-pinca`).
**Un patró d'item no hi pot arribar per definició.**

💡 **PROPOSTA (a validar):** aquestes vies han de resoldre's **per `?file=` (pattern_file_id)** i
derivar el propietari del fitxer, **no a l'inrevés**. És el gest que ja fa `_resoldre_propietari`
(`patterns/views.py:297-316`).

**No es trenquen:** els lectors que van pel costat segment (`annotation_views.py:450`, `:748`,
`:854`). **L'engine no coneix `SewRelation`** (treballa amb el dataclass `SewSpec` via
`adapters.sew_specs`) — cap comanda de `management/` la toca.

**Frontend (7 crides):** `endpoints.js:663,674,686,693,699,708,712` — totes passen `model`; a
`TallerPatro.jsx`: `:357, :431, :456, :479, :509, :769`.

### C.3 Dades i riscos de migració

BD (schema `fhort`): `sewrelation` = **4 files** (models 186 i 163; `model_id NULL`: 0) ·
`sewproposalrejection` = **0** · `dartproposalrejection` = **0** · `patternfile` = 4 (**0 d'item**).
**Cap backfill necessari:** totes les files vives satisfarien `model NOT NULL, item NULL`.

| risc | fitxer:línia | gravetat |
|---|---|---|
| `model_id bigint NOT NULL` a les 3 taules | DDL viu | **cal `AlterField` + `AddConstraint` XOR ×3** |
| `unique_together` que assumeixi model | **NO EXISTEIX** a cap de les 3 | ✅ cap bloqueig |
| `Meta.ordering=['model','id']` | `patterns/models.py:481` | cosmètic (NULLs al final) |
| `__str__` amb `model_id` | `patterns/models.py:484` | cosmètic ("model None") |
| accés a `.model` (atribut) que petaria amb null | **NO EXISTEIX** dins `patterns/` (tot va per `model_id`) | ✅ risc nul |
| **`sew_specs` retorna `()` en silenci** | `patterns/adapters.py:584-585` | ⚠️ **export mut** (§A.4) |

**Veredicte C: el XOR és mecànicament barat i epistemològicament car.** La migració és trivial
(3 `AlterField`, 0 backfill), però el radi de lectors (~13+7) i el guard mut de `sew_specs` volen
que el canvi es faci **sencer o gens**: mig XOR és pitjor que cap.

---

## BLOC D — Permisos (CONFIGURE) i el rellotge

### D.1 CONFIGURE avui: només `admin`, i el catàleg sencer el demana

Font única: `accounts/capabilities.py`. `CONFIGURE = "configure"` (`:10`); matriu rol→capacitats
(`:20-26`) — **només `admin` el té** (technician / product_manager / manager, **no**). La classe DRF
és `HasCapability` (`:46-54`), que **sense `required_capability` es comporta com `IsAuthenticated`**
(`:52-53`).

| ViewSet | lectura | escriptura | fitxer:línia |
|---|---|---|---|
| `ItemFitxerViewSet` (**la referència**) | `IsAuthenticated` | **CONFIGURE** | `item_fitxer_views.py:40-50` |
| `GarmentTypeItemViewSet` | `IsAuthenticated` | **CONFIGURE** | `tasks/views_b.py:864-868` |
| `GarmentPOMMapViewSet` | `IsAuthenticated` | **CONFIGURE** | `pom/views.py:259-264` |
| `ItemBaseMeasurementViewSet` | `IsAuthenticated` | **CONFIGURE** | `pom/views.py:293-298` |
| **`PatternFileViewSet`** | `IsAuthenticated` | **`IsAuthenticated`** ⚠️ | `patterns/views.py:205-211` |
| `PatternPOMViewSet` / `SewRelationViewSet` / `PatternSegmentViewSet` | `IsAuthenticated` | `IsAuthenticated` | `annotation_views.py:387`, `:424`, `:760` |

**Cap endpoint del motor exigeix cap capability.** El comentari que ho justifica
(`patterns/views.py:206-208`: "L'escriptura va al MODEL, no a un catàleg") **ja és fals**: el XOR
del mateix fitxer permet escriure al catàleg. Excepció ja precedent i correcta: `usar_al_model`
queda a `IsAuthenticated` perquè escriu al model, no al catàleg
(`item_fitxer_views.py:146-148`).

**❓ DECISIÓ (Patró C):** ¿escriure un `PatternFile`/anotació **d'item** ha d'exigir `CONFIGURE`
(mirall d'`ItemFitxer`) mentre el de **model** es queda a `IsAuthenticated`? Si sí, el gate és per
**propietari resolt**, no per acció — un `get_permissions` no ho pot decidir sol (no coneix el
`garment_type_item` fins que llegeix el body/objecte). 💡 **PROPOSTA:** gate dins
`_resoldre_propietari` (`patterns/views.py:297-316`), que és l'únic lloc que ja sap de qui penja.

⚠️ **Conseqüència de RRHH, no de codi:** si el Taller-GTI es gata amb `CONFIGURE`, **només un
`admin` podrà anotar bases de biblioteca** — i la Montse (autora de les bases, per disseny) hauria
de ser `admin` o tenir un `grant` explícit (`accounts/capabilities.py:31-43`).

### D.2 El rellotge: NO és una pressuposició del Taller — però SÍ és el gate

**Backend del motor: ignorància total de `ModelTask`.** Grep exhaustiu de
`task_id|ModelTask|rellotge|temps` a `patterns/**` → **única coincidència**: una dependència d'ordre
de migracions (`patterns/migrations/0001_initial.py:15`). **Cap model, view o serializer del motor
referencia una tasca.**

**Frontend (`TallerPatro.jsx`):** el rellotge és una capa afegida i **tolerant al fallo**:

| element | fitxer:línia | obligatori? |
|---|---|---|
| `?task_id=` (reprèn tasca del pla) | `:39` | **opcional** |
| `models.openTask(modelId,'pattern_digit')` en muntar | `:170-194` (crida a `:180`) | **opcional**: el `.catch` (`:185-193`) **no peta ni bloqueja** — "el patró es pot MIRAR igualment" (`:188-189`) |
| `pauseActiveTask()` en sortir | `:112-117`, `:198` | **opcional** (`if (tid==null) return`) |
| la càrrega del taller (`carregar`) | `:122-162` | **no depèn de cap tasca** |
| **gate de les eines** `disabled={!tascaId}` | **`:1148, :1156, :1166, :1173`** | ⚠️ **AQUÍ SÍ**: sense rellotge **no hi ha anotació** |

`PatternTab.jsx` (el tab de consulta) **no toca cap tasca** — grep buit; comentat a `:26-28`, `:451`
("qui ve només a mirar no ha d'obrir cap tasca").

El rellotge del model penja de `open_model_task_view` (`tasks/views_b.py:509-553`), que és **per
model per definició** (`Model.objects.get(pk=model_id)`, `ModelTask.objects.create(model=...)`) i
té el seu propi gate d'allow-list (403 `task_type_not_allowed`, `:543-546`). **Per a
`GarmentTypeItem` NO EXISTEIX cap equivalent** (ni `open-item-task`, ni `ItemTask`).

**Veredicte D: el delta (2) no costa res al backend i el delta (3) és una incoherència ja viva.**
Però els dos es toquen: **el rellotge és avui l'únic gate de l'anotació**. Treure'l al catàleg
sense posar `CONFIGURE` al seu lloc deixaria el Taller-GTI **més obert que el Taller de model**
— qualsevol autenticat anotant la biblioteca. **Els deltes (2) i (3) s'han de decidir junts.**

---

## BLOC E — L'entrada: la pantalla de l'item al catàleg

### E.1 NO EXISTEIX cap pàgina de detall d'item amb tabs

L'item viu **repartit en dos llocs**, i cap dels dos és una fitxa amb tabs on encaixi una "porta"
com la del model:

| superfície | fitxer:línia | forma |
|---|---|---|
| `pages/GarmentTypes.jsx` | mestre-detall del catàleg | esquerra = GarmentTypes, dreta = items; secció **FITXERS** (D21) a `:257-287` |
| `pages/ItemAuthoring.jsx` | `:51` | **wizard de 2 passos** (`step`), no tabs; pas 2 = `MeasurementBaseGrid` (`:328`). **Cap secció de fitxers ni de patrons.** |

**Rutes** (`App.jsx`): `garment-types` (`:301`), `garment-type-items/nou/:typeId` (`:304`),
`garment-type-items/:itemId/editar` (`:305`). **NO EXISTEIX** cap ruta de detall d'item
(`garment-type-items/:itemId` sense `/editar`), ni cap ruta de taller per a item. L'única ruta de
taller és `/models/:id/patro/taller` (`App.jsx:263`), i `TallerPatro` llegeix `useParams().id`
com un **Model** (`TallerPatro.jsx:35-36`).

### E.2 Els fitxers d'item ni tan sols es poden obrir avui

La secció de fitxers de `GarmentTypes.jsx` renderitza `<FileList files={files} …>` (`:285`)
**sense `onSelect` ni `onOpen`**; i `FileList` (`components/assets/FileList.jsx:19`) **no
renderitza cap `<a href>`**: només `onDoubleClick → onOpen?.(f)` (`:75`). El `download_url` signat
d'un `ItemFitxer` **existeix al serializer** (`models_app/serializers.py:85-88`, salt propi
`ITEM_DOWNLOAD_SALT`, TTL 900s) però **no es consumeix enlloc del frontend**.
→ **Avui un fitxer d'item no es pot descarregar des del catàleg.** (Forat previ, fora de W6, però
la porta del Taller cauria just al costat.)

### E.3 La "porta" a calcar (la del model)

`components/pattern/PatternTab.jsx` — prop única `{modelId}` (`:30`), muntat des de
`ModelSheet.jsx:585`; fa `patterns.list(modelId)` (`:62`), upload (`:121-134`), visor de consulta, i
el botó cap al banc: `navigate('/models/${modelId}/patro/taller?file=${actual.id}')` (`:178`).

💡 **PROPOSTA (a validar) — on va la porta d'item.** Tres opcions, amb cost molt diferent:
1. **Secció dins `GarmentTypes.jsx`**, al costat de FITXERS (calca D21). Barat, però amuntega el
   catàleg en una pàgina que ja fa de mestre-detall.
2. **Pas 3 del wizard `ItemAuthoring`.** Coherent amb "autoria de la base", però el wizard és de
   creació/edició, no de treball continuat.
3. **Ruta nova de detall d'item amb tabs** (`garment-type-items/:itemId`), mirall d'`ModelSheet`.
   Cara, però és **l'única que dona a l'item la mateixa dignitat que al model** — i el disseny W6
   preveu "menú Disseny → Biblioteca de patrons" com a segona entrada.

**Veredicte E: aquest és el forat més gran de W6, i no és de backend.** El Taller-GTI no té on
penjar. **Cal decisió d'Agus abans de dimensionar.**

---

# PART 2 — EL PATRÓ A LA FITXA TÈCNICA

## BLOC F — Tab Fitxers (`TabFiles`)

### F.1 No és un fitxer: és una funció inline dins `ModelSheet.jsx`

`function TabFiles({ modelId })` — **`ModelSheet.jsx:1267`**. Prop única: `modelId`. **No rep
`items` per props: té l'endpoint hardcodat a dins** (`:1282`,
`GET /api/v1/model-fitxers/?model=${modelId}&is_current=true`). Subcomponents privats al mateix
fitxer: `FileRow` (`:1514`), `FileDetail` (`:1553`), `DetailRow` (`:1543`).

**Duplicació ja existent:** hi ha un `FileList` compartit i presentacional
(`components/assets/FileList.jsx:19`, rep `files`) que `TabFiles` **no** usa — el consumeixen
`AssetNavigator` i `GarmentTypes`. **Dues implementacions de llista de fitxers conviuen.**

Accions: llistar (`:1281-1287`), pujar/nova versió (`:1290-1313`), historial (`:1317-1326`),
esborrar (`:1328-1334`), previsualitzar (`previewUrl:1249` → `download_url + '&inline=1'`), i
editar el `.ftt` (`:1494` → `/models/{id}/ftt/{fitxerId}`).

### F.2 `PatternFile` no és un `ModelFitxer` — i no es veu al tab

`PatternFile` és una **entitat completament separada**, sense cap FK a `ModelFitxer`: té **bytes
propis** (`fitxer_dxf` `patterns/models.py:68` i `fitxer_rul` `:74`), cadena de versions pròpia
(`:58-64`) i **salts de signatura deliberadament distints** (`patterns/views.py:50-53`: "amb un salt
compartit, un token de ModelFitxer id=5 validaria aquí").

Els valors `PATRO`/`RUL` **existeixen** a `ModelFitxer.TIPUS_CHOICES` (`models_app/models.py:350-362`)
però **el motor no els escriu mai** (grep de `ModelFitxer` dins `patterns/` → només comentaris).
Els `PatternFile` només es veuen al tab **Patró** (`PatternTab.jsx:62`) i al Taller
(`TallerPatro.jsx:127`). **Al tab Fitxers, avui, NO hi són.**

### F.3 Punt mínim d'intervenció: **un sol lloc**

La llista es construeix en tres punts encadenats: càrrega (`ModelSheet.jsx:1281-1287`) → estat
únic (`:1273`) → ordenació/render (`:1342-1346`, `:1482-1484`). **El punt mínim és el `useEffect`
de `:1281`**: un `Promise.all([fetch(model-fitxers), patterns.list(modelId)])` + un adaptador
`PatternFile → forma ModelFitxer`. `sorted`/`FileRow`/`FileDetail` ja funcionen amb qualsevol
objecte que tingui `nom_fitxer`/`data_pujada`/`versio`/`download_url`.

**Riscos concrets d'aquest merge (fets, no opinions):**

| risc | fitxer:línia |
|---|---|
| **col·lisió d'ids** (`ModelFitxer.id=5` vs `PatternFile.id=5`): `key={f.id}` (`:1483`), `selectedId` (`:1279`), `find(f=>f.id===selectedId)` (`:1348`) → cal clau composta `font+id` | `ModelSheet.jsx:1279,1348,1483` |
| **accions de `FileDetail` són ModelFitxer-específiques** (delete/nova versió/historial/editar) → per a un `PatternFile` cal enrutar a `patterns.*` o desactivar-les i oferir "Obre al Taller" | `ModelSheet.jsx:1490-1495` |
| el `download_url` d'un `PatternFile` **es couva** (15 min): cal `downloadLinks(id)` al clic, no el camp serialitzat | `endpoints.js:630-633` |

**Veredicte F: llest, amb 1 punt d'entrada i 3 riscos coneguts.** 💡 **PROPOSTA:** el mínim honest
és **llista unificada + accions enrutades per `_font`**, no "un tab que ho barreja tot": el
`PatternFile` té un cicle de vida propi (Taller, export, niada) que `FileDetail` no sap servir.

---

## BLOC G — `TechSheetEditor`: un tipus d'element nou

### G.1 Un monòlit amb un switch tancat, duplicat

`pages/TechSheetEditor.jsx` — **4.472 línies**, component únic (`:1299`), **sense store**
(tot `useState`/`useRef`). L'element és un objecte pla `{id, type, layer, x, y, …}` en **mm**.

**11 tipus existents** (`data_block`, `table`, `field`, `text`, `rect`, `ellipse`, `line`, `arrow`,
`path`, `image`, `sketch_svg`, `group`), i el discriminador `type` es resol en **dos switches
tancats que cal mantenir sincronitzats a mà**:

| switch | fitxer:línia | serveix |
|---|---|---|
| `ObjectNode` (React-Konva) | `TechSheetEditor.jsx:1016` (imatge a `:1085`) | **el canvas viu** |
| `addObjectToLayer` (Konva imperatiu) | `TechSheetEditor.jsx:806` (imatge a `:896`) | **el PDF i les miniatures** |

**NO hi ha registry.** El `type` es consulta escampat per ~35 punts més (`objectBounds:237`,
resize `:1781`, transformEnd `:2263-2327`, icona de capes `:3950`…).

### G.2 La persistència i el PDF són **agnòstics al tipus** — aquesta és la clau

- `serializeObject` (`:170`) desa **qualsevol tipus tal qual** (només filtra `src` per a
  `data_block`).
- `documentToV2`/`v2ToDocument` (`:285`, `:305`) mapegen `src` **per convenció (`typeof
  obj.src === 'string'`), no per tipus**.
- El backend `_extract_inline_objects` (`models_app/services_ftt.py:144`) extreu **qualsevol** `src`
  dataURL a `assets/<sha16>.<ext>` (cridat des de `services_ftt_document.save_document:336`).

→ **Si el nou element usa la clau `src` amb un dataURL, la persistència funciona sense tocar ni una
línia de Python, i els camps extra (`pattern_file_id`, `piece_name`, `escala_mm`) es desen sols dins
el JSON, sense migració.**

### G.3 Persistència: el `.ftt` és un ZIP versionat sobre `ModelFitxer`

No hi ha model Django amb el layout: viu dins un `.ftt` (zip amb `manifest.json` + `document.json` +
`assets/`), empaquetat a `models_app/services_ftt.py:58` (`pack`) / `:227` (`unpack`), sobre un
`ModelFitxer` amb `tipus=TECHSHEET`. Desat: `PATCH /api/v1/ftt-documents/<id>/`
(`ftt_document_views.py:104` → `services_ftt_document.save_document:324`), que **crea una versió
nova** a cada desat; l'autosave és un debounce de 2s (`TechSheetEditor.jsx:1953-1973`).
→ Coherent amb el churn de versions ja observat (memòria `ftt-version-churn`).

### G.4 Mínim per a l'element "peça de patró per imatge"

| # | punt | fitxer:línia | obligatori? |
|---|---|---|---|
| 1 | render LIVE (branca nova → reutilitza `ImageObj:946`) | `TechSheetEditor.jsx:1085` | ✅ **sí** |
| 2 | render OFFSCREEN (= **el PDF**) | `TechSheetEditor.jsx:896` | ✅ **sí** |
| 3 | geometria (`imageProps`) | `:780` | ✅ reutilitzable tal qual |
| 4 | resize numèric (afegir a la llista `['rect','image','sketch_svg','text']`) | `:1781` | UX |
| 5 | transformEnd | `:2327` | ✅ **cau al camí genèric — res a fer** |
| 6 | icona al panell de capes | `:3950` | cosmètic |
| 7 | eina de creació + palette/ribbon | `:2634`, `:3234`, `:3449` | ✅ sí |
| 8 | i18n ca/en/es | `frontend/src/i18n/*.json` | ✅ **llei CLAUDE.md** |
| — | **backend** | — | ✅ **ZERO punts** (§G.2) |

**La font de la imatge ja existeix:** `GET /api/v1/patterns/pattern-files/<id>/render.svg?piece=<nom>`
(`patterns/views.py:358-364`, motor a `patterns/svg.py:48`). I **el patró de consum ja està
escrit**: `importarDelTenant` (`TechSheetEditor.jsx:3323-3347`) fa **fetch autenticat → blob →
`FileReader.readAsDataURL` → `addImageFromDataURL`**. Cal fer-ho **així** (no posar la URL a `src`),
perquè `useImage` (`:338`) fa `new Image()` i **no pot enviar el Bearer**. L'editor fins i tot ja té
el forat reservat: `flash(t('tech_sheet.import_dxf_soon'))` (`:3338`).

**Veredicte G: ~6-8 punts d'edició, tots a un fitxer + i18n. Zero migracions, zero Python.** El cost
real no és el tipus nou: és que `TechSheetEditor.jsx` té la lògica de tipus escampada per ~35 punts
i **dos switches que divergeixen si te'n descuides un** (el canvas es veuria bé i el PDF sortiria
buit — la variant exacta de la lliçó W4 "build verd no és producte verd").

---

## BLOC H — Pipeline de PDF

### H.1 Hi ha DOS pipelines, i el de la fitxa **no és al servidor**

| # | generador | llibreria | fitxer:línia | documents |
|---|---|---|---|---|
| 1 | comercial | **reportlab** (platypus) | `commerce/pdf_service.py:20-30`, `:216`, `:221`, `:400` | pressupost, comanda, **albarà** |
| 2 | **FITXA TÈCNICA** | **pdf-lib (NAVEGADOR)** | `TechSheetEditor.jsx:6`, `:3017-3056` | fitxa `.ftt` → PDF |
| 3 | plantilles | pdf-lib (navegador) | `TechSheetTemplateEditor.jsx:9`, `:269-271` | plantilla → PDF |

**NO EXISTEIX** weasyprint, jsPDF, puppeteer ni xhtml2pdf.

**FET TAXATIU:** la fitxa es genera al client — `renderPageToDataURL(p, 3.5, ctx)` (`:3025`) munta un
`Konva.Stage` offscreen, en treu un **PNG de la pàgina sencera** (`:930`) i el clava amb
`pdf.embedPng` + `page.drawImage(x:0,y:0,…)` (`:3026-3028`). **Cada pàgina del PDF és un ràster.**
El backend **només rep el PDF ja fet i el desa** com a `ModelFitxer` TIPUS_EXPORT
(`POST /api/v1/ftt-documents/<id>/export/`, `ftt_document_views.py:171` →
`services_ftt_document.save_export:350`). **Codi backend que llegeixi el layout i el pinti: NO
EXISTEIX.**

### H.2 Imatges i resolució

- **Backend (reportlab):** l'única imatge és el logo del tenant — `Image(path)` amb un **path de
  disc** (`commerce/pdf_service.py:146-175`), amb `try/except` ja escrit per a "storage sense path
  local" (`:150-153`). ⚠️ **`logo.path` només és correcte amb context de tenant actiu**
  (`TenantFileSystemStorage` resol `location` des de `connection.schema_name`,
  `settings.py:174-187`) — el risc real de qualsevol PDF server-side futur, i coherent amb la
  memòria `ftt-media-namespace-tenant`.
- **Frontend (pdf-lib):** les imatges dins la pàgina es carreguen amb `crossOrigin='anonymous'`
  (`:328-355`) des de `/api/v1/ftt-documents/<id>/asset/<nom>/` (`IsAuthenticated`,
  `ftt_document_views.py:214`) → depèn de la **cookie de sessió**, i si falla **s'omet la imatge en
  silenci** (`catch {}` a `:902`, `:908`). Fràgil, ja viu.
- **Llindars reals:** logo = PNG de 600 px a 15 mm ≈ **1016 dpi** (`accounts/logo.py:16-18`,
  sobre-mostreig a posta) · fitxa = `MM_TO_PX 2.4` (`TechSheetEditor.jsx:38`) × `pixelRatio 3.5`
  (`:3025`) = **8,4 px/mm ≈ 213 dpi**. **213 dpi és el llistó de facto de la fitxa.**

### H.3 cairosvg i l'SVG del motor

- **cairosvg s'usa en un únic lloc:** `accounts/logo.py:40-47` → `svg2png(bytestring=raw,
  output_height=600)`. **Només passa `output_height`** — ni `dpi` ni `output_width`
  (`requirements.txt:33`).
- **Cobriria SVG→PNG a la mida/DPI del PDF? SÍ.** `svg2png` accepta `output_width/height/scale/dpi`,
  i l'SVG del motor porta **`width`/`height` en mm i `viewBox` en mm**
  (`patterns/svg.py:153-161`) — escalable sense ambigüitat.
- **L'SVG del motor és propi, no ezdxf-draw** (rebutjat per no arrossegar matplotlib/PySide6/PyMuPDF
  — `patterns/svg.py:1-19`): `render_document(doc, piece_name='') -> str` (`:48-72`). **Torna un
  `str` en memòria; no es persisteix mai, no hi ha cache** — es recalcula a cada GET.

**Veredicte H: cairosvg cobreix el cas de sobres, però per a la fitxa NO CAL** — el PDF de la fitxa
no passa per Python. cairosvg només entra en joc si algun dia es construeix un PDF server-side (i
llavors el problema no serà la resolució, serà el **context de tenant**).

---

## BLOC I — `render-signed`

### I.1 **NO EXISTEIX** — i el codi ja diu per què està diferit

Cap `render_signed`/`render-signed` al backend ni al frontend. Els únics endpoints signats de
`patterns/` són `download-signed` i `download-rul-signed`. Està **diferit explícitament**, i el pla
en nomena el despertador: *"`render-signed` DIFERIT al backlog — S5 dibuixa des de la GEOMETRIA, no
des de l'SVG; **el despertador és el PDF de fitxa amb peces**"*
(`PLA_IMPLEMENTACIO_MOTOR_PATRONS.md:567-569`, reafirmat a `:842`).

**Contrast net al serializer:** `download_url` i `download_rul_url` van **signats**
(`patterns/serializers.py:197-208`), però **`render_url` és una URL nua** cap a un endpoint
`IsAuthenticated` (`:210-217`). El client ho resol baixant **blob amb capçalera `Authorization`**
(`endpoints.js:735-745`, amb el comentari: *"un `<img src>` no pot portar capçaleres"*). El visor
Konva **ni tan sols usa l'SVG**: dibuixa des de `geometry` (`patterns/views.py:346-356`).

### I.2 La pregunta clau, responduda: **el servidor no necessita cap render-signed**

El despertador que el pla esperava (**"el PDF de fitxa amb peces"**) **ha sonat amb una premissa
diferent de la prevista: el PDF de la fitxa no corre al servidor** (BLOC H). Les tres opcions:

| opció | què ja existeix | què falta | veredicte |
|---|---|---|---|
| **A — SVG in-process** (si algun dia hi ha PDF server-side) | `DjangoGeometryStore().load_from(fp)` (`adapters.py:197-203`) + `render_document()` (`svg.py:48`) són **funcions pures sobre l'ORM, sense request ni sessió** — exactament el que fa la vista (`views.py:361-363`); cairosvg instal·lat; reportlab amb `Image` | passar `BytesIO` a `reportlab.Image` (avui rep path) + el generador server-side, **que no existeix** | ✅ **la bona, si mai cal** |
| **B — llegir un render persistit** | — | **NO EXISTEIX**: l'SVG no es desa mai (`svg.py`, `services.save_pattern_file`) | ❌ caldria artefacte + invalidació |
| **C — auto-crida HTTP amb URL signada** (= `render-signed`) | el motlle exacte (`download-signed`: `authentication_classes=[]` + `AllowAny` + `_verificar_token`, `views.py:630-661`) i el signador (`serializers.py:13-25`) | l'`@action` amb **salt propi** + client HTTP | ❌ **contraindicada**: el `Host` del tenant o `django_tenants` resol al schema `public`; és un viatge de xarxa per obtenir un string que la funció et torna en memòria |

**I per a l'sprint "Peces a la fitxa" (el cas real): tampoc cal.** El navegador **ja sap** fer fetch
autenticat i convertir a dataURL — `importarDelTenant` (`TechSheetEditor.jsx:3323-3347`) és el patró,
i `endpoints.js:735-745` ja té `renderSvg(id, piece)` amb `responseType:'blob'`. La imatge entra al
`.ftt` com a **asset** (§G.2) i **el PDF la treu de l'asset, no del servidor**.

### I.3 El sistema signat existent (per si es reutilitza)

`django.core.signing` (`dumps`/`loads`), **no `TimestampSigner` directe**. Emissió:
`_signed_download_url` (`patterns/serializers.py:13-25`). **TTL = 900 s** (15 min,
`services_fitxers.py:26`). Validació: `_verificar_token` (`patterns/views.py:649-661`) —
`SignatureExpired`/`BadSignature` → 403, **i comprova que l'id signat coincideix amb el `pk`**.
Salts separats a posta (`views.py:52-53`). Refresc fresc al clic: `download-links`
(`views.py:608-628`, D9).

**Veredicte I: `render-signed` es pot deixar dormint.** El despertador ha sonat, s'ha mirat el
rellotge, i **el PDF no el necessita**. 💡 **PROPOSTA:** actualitzar la nota del pla
(`PLA_IMPLEMENTACIO_MOTOR_PATRONS.md:567-569`) — el despertador ja no és el PDF de fitxa; només ho
seria un **PDF server-side**, que avui no existeix per a la fitxa.

---

# TAULA FINAL — EXISTEIX / FALTA / DIFERENT (per al CTO)

| # | Peça | Estat | Evidència |
|---|---|---|---|
| 1 | XOR `model`/`garment_type_item` a `PatternFile` | ✅ **EXISTEIX** (des de 0001) | `patterns/models.py:109-115` |
| 2 | Upload/list de `PatternFile` per a item (API) | ✅ **EXISTEIX** | `patterns/views.py:196`, `:219-344` |
| 3 | `GarmentTypeItemAsset` | ❌ **NO EXISTEIX** — el host és `ItemFitxer` | `patterns/models.py:51-56` |
| 4 | 2n contenidor per a item (`item-poms`) | ❌ **FALTA** — avui **400** | `patterns/views.py:383-390` |
| 5 | Camí canònic de la plantilla de POMs d'item | ❌ **NO EXISTEIX** (3 còpies del query) | `wizard_views.py:77`, `models_app/views.py:651`, `:699` |
| 6 | XOR a `SewRelation` | ❌ **FALTA** (NOT NULL) | `patterns/models.py:440-442` |
| 7 | XOR a `SewProposalRejection` + `DartProposalRejection` | ❌ **FALTA** — **el disseny no les compta** | `patterns/models.py:510-512`, `:559-561` |
| 8 | `_patro()` exigeix `?model=` (5 endpoints assistits) | ❌ **FALTA** obrir-lo per `?file=` | `annotation_views.py:529-546` |
| 9 | `sew_specs` retorna `()` en silenci per a item | ⚠️ **BUG LATENT** (export mut) | `patterns/adapters.py:584-585` |
| 10 | Export de niada per a item | ⚠️ **DECISIÓ DE PRODUCTE** (avui `[]`) | `patterns/views.py:471-472` |
| 11 | Rellotge/`ModelTask` al backend del motor | ✅ **NO EXISTEIX** → delta (2) gratuït | grep `patterns/**` |
| 12 | Gate de l'anotació = el rellotge (no una capability) | ⚠️ **DIFERENT del que el disseny assumeix** | `TallerPatro.jsx:1148-1173` |
| 13 | `CONFIGURE` a l'escriptura de `PatternFile` | ❌ **FALTA** (única superfície de catàleg sense gate) | `patterns/views.py:205-211` |
| 14 | Entrada d'UI per a l'item (pàgina/tab) | ❌ **NO EXISTEIX** — **el forat més gran de W6** | `App.jsx:301-305` |
| 15 | Descàrrega de fitxers d'item des del catàleg | ❌ **NO EXISTEIX** (`FileList` sense `onOpen`) | `GarmentTypes.jsx:285`, `FileList.jsx:75` |
| 16 | `TabFiles` amb 2a font | ❌ **FALTA** — 1 punt d'entrada | `ModelSheet.jsx:1281-1287` |
| 17 | Element de canvas nou = zero backend | ✅ **EXISTEIX** (persistència agnòstica al tipus) | `services_ftt.py:144`, `TechSheetEditor.jsx:170` |
| 18 | PDF de la fitxa al servidor | ❌ **NO EXISTEIX** — es fa al **navegador** | `TechSheetEditor.jsx:3017-3056` |
| 19 | `render-signed` | ❌ **NO EXISTEIX** — i **no cal** per al PDF | `PLA_IMPLEMENTACIO…:567-569`, `endpoints.js:735-745` |
| 20 | cairosvg per a SVG→PNG a mida/DPI | ✅ **EXISTEIX i cobreix** (només s'usa amb `output_height`) | `accounts/logo.py:40-47`, `patterns/svg.py:153-161` |

---

# DIMENSIÓ DELS TRES SPRINTS

### (1) W6 — TALLER-GTI · **el més car dels tres**

**Fixos mínims:** 3 `AlterField`+`AddConstraint` (XOR a les 3 taules, **0 backfill**) · `_patro()`
per `?file=` en lloc de `?model=` (desbloqueja 5 endpoints) · `@action item-poms` amb **la mateixa
forma** que `model-poms` (reutilitza `ModelPomList` sense tocar-lo) · reescriure el guard mut de
`sew_specs` · gate d'escriptura per propietari resolt · frontend: variant d'item de `patterns.list`
/ upload / les 7 crides que passen `model`.

**⚠️ 3 decisions humanes BLOQUEJANTS abans de dimensionar:**
1. **On va la porta** (§E.3) — el catàleg **no té** pàgina de detall d'item. Sense això, W6 no té on
   penjar.
2. **`CONFIGURE` sí o no** (§D.1) — i si sí, **la Montse ha de ser `admin`** o tenir un `grant`.
3. **¿L'export d'item existeix?** (§A.4) — si les bases es lliuren sense niada, W6 **es redueix
   molt**.

**Els deltes (2) i (3) s'han de decidir junts:** treure el rellotge treu el gate.

### (2) Sprint "FITXERS UNIFICATS" · **mitjà, 1 punt d'entrada**

`ModelSheet.jsx:1281` (merge de les dues fonts) + clau composta `_font+id` (col·lisió real) +
enrutar les 4 accions de `FileDetail` per font (o desactivar-les i oferir "Obre al Taller") +
`downloadLinks(id)` al clic per als `PatternFile` (el `download_url` es couva). **Zero backend.**
💡 Val la pena decidir si s'aprofita per **jubilar la duplicació** `FileRow`/`FileDetail` vs el
`FileList` compartit (`components/assets/FileList.jsx:19`) — avui en conviuen dues.

### (3) Sprint "PECES A LA FITXA" · **el més barat — i es pot fer JA**

~6-8 punts, **tots a `TechSheetEditor.jsx` + i18n×3**: els **dos switches** (`:1085` i `:896` — el
segon **és** el PDF), l'eina de creació que calca `importarDelTenant` (fetch autenticat → blob →
dataURL), resize (`:1781`), icona (`:3950`). **Zero Python, zero migracions, zero canvis a l'API de
desat, i `render-signed` NO cal.** La font (`render.svg?piece=`) i el patró de consum **ja
existeixen**.

⚠️ **L'única trampa:** els dos switches s'han de tocar **tots dos**. Si només es toca el del canvas,
la peça es veurà a la pantalla i **el PDF sortirà buit** — la variant exacta de la lliçó W4
("build verd no és producte verd").

**Ordre suggerit** 💡: **(3) → (2) → (1)**. (3) dona valor visible immediat amb risc quasi nul i
**exercita el render del motor dins la fitxa** (que és el que el client veurà); (1) espera les tres
decisions d'Agus.

---

*Fi de la diagnosi. Cap línia de codi tocada. Les decisions són humanes (Patró C).*
