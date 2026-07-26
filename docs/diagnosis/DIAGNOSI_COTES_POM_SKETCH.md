# DIAGNOSI — COL·LOCACIÓ DE COTES POM SOBRE EL SKETCH DE LA FITXA TÈCNICA

> **Patró A (read-only estricte).** Equip PROTOCOL_FASE_B: director-investigació +
> 8 investigadors-codi (un per bloc) + documentador. Cap modificació de codi, cap
> migració, cap escriptura fora de `docs/`.
> **Staging:** `/var/www/ftt-staging`, branca `dev` (HEAD `a2afe59`, +5 sobre origin/dev).
> **Data:** 2026-07-26. **Abast:** cartografiar 8 blocs amb evidència `fitxer:línia`
> per dimensionar F1–F3 sense especular.
> **Règim declarat (Patró C, Agus):** la fitxa és camp INFORMATIU, no de precisió. La
> llei «LLM mai dibuixa coordenades» protegeix el DXF sobirà i **NO** aplica aquí.
> El motor de patrons/traçadora NO es toca en cap cas.

---

## 0 · RESUM EXECUTIU (llegir primer)

**El descobriment que reescriu el dimensionament: la cota POM sobre el sketch JA EXISTEIX,
però com a DIBUIX MORT, no com a vincle viu.**

L'editor de fitxa ja té l'eina completa «cota POM» (doble fletxa + contenidor vermell +
text blanc), amb la seva paleta, els seus presets i la seva i18n:

- Eina `cota_pom` de dos clics (A→B) que dibuixa un `group` = `path` de doble punta
  (corbable) en vermell `KONVA_COL.pom` + `text` blanc sobre fons vermell —
  `frontend/src/pages/TechSheetEditor.jsx:3196-3227`.
- Paleta: `KONVA_COL.pom = '#dc2626'` — `TechSheetEditor.jsx:120`.
- Presets: `PRESET_TOOLS = [...,'preset_cota_pom','preset_annotation']` —
  `TechSheetEditor.jsx:152`; `preset_cota_pom` a `:2158-2169`.
- Panell dret que llista els POMs del model i «arma» la cota —
  `TechSheetEditor.jsx:4945-4962`.
- i18n `tech_sheet.tool_cota_pom` / `preset_cota_pom` / `pom_cota_hint` a `ca/es/en.json`.

**El que NO existeix i és, exactament, la feina de F1–F3:**

| Fase | Delta real (no és el que semblava el brief) |
|---|---|
| **F1** | La cota entra com a **STRING LITERAL**: «sense cap `pom_id` ni `bm_id` a l'objecte. La cota no és un binding viu; és un dibuix» (`TechSheetEditor.jsx:3204-3205`). L'etiqueta = `nom_fitxa \|\| pom_abbreviation \|\| codi_client` (`:4956`), **no** codi canònic + àlies de client resolt. **F1 = promoure el dibuix mort a cota VIVA**: dur `pom_id`/`bm_id` a l'objecte i re-derivar l'etiqueta del POM viu (codi canònic + àlies). |
| **F2** | No existeix `POMPlacement` ni cap eix «vista». La col·locació d'avui viu dins el `.ftt` de cada document, no com a precedent normalitzat i reutilitzable. **F2 = entitat nova + sembra.** |
| **F3** | No existeix cap crida de visió, ni cap «mode revisió» (objectes proposats amb estat pendent/acceptat/descartat) enlloc de l'editor. **F3 = endpoint IA + mode revisió, greenfield sobre infra existent.** |

**Frontera G1 ja codificada i respectada:** la cota d'avui és deliberadament un dibuix
sense binding per no trepitjar l'escriptura de mesures (G1). F1 haurà de dur un vincle
**només-lectura** que preservi aquesta frontera (llegeix el POM, mai n'escriu el valor).

---

## B1 — CICLE DE VIDA DEL SKETCH DINS EL DOCUMENT

### Fets
- **Entrada d'imatge/SVG, dos camins.** Pujada local: `handleFile` → `FileReader.readAsDataURL`
  → `addImageFromDataURL` (`TechSheetEditor.jsx:3467-3476`); drop al canvas `:3477-3482`.
  Import des de Finder/ModelFitxer (tenant): `importarDelTenant(f)` baixa els BYTES
  autenticats de `/api/v1/{model-fitxers|item-fitxers}/<id>/download/` (`:4463-4486`); **no
  vincula** el fitxer, n'importa una còpia (`:4459-4462`).
- **SVG es manté VECTORIAL, no es rasteritza.** `importFlatSvgText` → `sketch_svg` transitori →
  `convertLegacySketchSvgObject` → `legacySketchSvgToPath` fa
  `scope.project.importSVG(..., {expandShapes:true})` (Paper.js) i recorre l'arbre mapejant
  cada segment Bézier a `{x,y,inX,inY,outX,outY}` (`:1742-1812`). Els forats (`CompoundPath`,
  `evenodd`) es conserven com a `subpaths` sense aplanar (`:1766-1788`). `sketch_svg` és un
  tipus legacy que encara existeix (`SketchSvgObj` rasteritza a `KonvaImage`, `:1502-1512`),
  però tot SVG nou es converteix a `path` vectorial immediatament.
- **Layout del `.ftt` (zip).** `manifest.json` (`{magic:"FTT", schema_version, app_version,
  kind, checksums}`) + `document.json` (document lògic, compacte) + `assets/<sha16>.<ext>`
  (entrades zip separades, binari cru) + `preview.png` — `services_ftt.py:3-8, 58-98`.
  **Les imatges NO s'incrusten com a base64 al JSON**: `_extract_inline_objects` descodifica
  qualsevol `src` `data:` a bytes i reescriu `src='assets/<sha16>.<ext>'` (dedup per hash),
  recursiu per `children` (`services_ftt.py:106-158`). El client mai rep el zip: el backend
  desempaqueta i serveix `document_json + {nom→URL}` (`ftt_document_views.py:92-102`,
  `FttDocumentAssetView:232-248`).
- **Esquema v2 `pages`.** Document lògic = `{ftt_schema, metadata, pageFormat, pages:[{id,
  objects:[], guides:[]}]}` (`services_ftt.py:44-55`). L'objecte pot ser un arbre amb
  `children` (grups). Tipus vistos: `image, path, sketch_svg, text, field, rect, line, arrow,
  group, table, data_block(header/graded_table), pattern_piece`. La referència a l'asset viu al
  camp `src` de l'objecte; no hi ha taula de refs.
- **NO existeix cap noció de «vista» (davant/darrere/detall).** Només objectes plans (arbre de
  grups) sobre una pàgina; l'única discriminació és `pageFormat` global i `layer:'free'` per
  objecte. (Verificat: grep de `front/back/detail/view` al backend no dona cap camp d'estructura.)
- **Versionat.** Dos camps distints: `manifest.schema_version` (contenidor, `FTT_SCHEMA_VERSION=1`,
  `services_ftt.py:23`) i `document.json.ftt_schema` (esquema lògic, `FTT_DOCUMENT_SCHEMA=1`, `:36`).
  `unpack` valida `schema_version` amb **igualtat estricta** → apujar-lo trencaria tots els `.ftt`
  v1 (`:250-260`). **Camps additius i tipus nous round-trippen SOLS**: pack/unpack tracten
  `document.json` com a opac i preserven claus desconegudes (`_map_object_tree` fa `dict(obj)`
  sense whitelist, `:130-141`). No hi ha cap funció de migració/upgrade de `.ftt` vells.

### Forats / Riscos
- No hi ha cap concepte de «vista» al `.ftt`. Afegir-lo és viable sense trencar res (opacitat de
  `document.json`), però és disseny nou (pàgina-per-vista o camp per-pàgina/objecte).
- Un tipus nou que porti una **referència de host** (FK a fitxer) HA d'afegir la seva clau a
  `HOST_REF_KEYS` (`services_ftt_document.py:121-127`) o el test `test_cap_referencia_de_host...`
  peta. Un `pom_id` escalar (F1) NO és host-ref → round-trippa lliure.
- `schema_version` rígid: cap canvi additiu ha de tocar-lo; confiar en l'opacitat del document.

---

## B2 — EDITOR: PRESET COTA I PUNT D'ENDOLL DEL MODE REVISIÓ

### Fets
- **Doble render.** Live: `ObjectNode(...)` (`TechSheetEditor.jsx:1560`). Export/offscreen:
  `addObjectToLayer(layer, obj, ctx)` (`:1300`), cridat per `renderPageToDataURL` (`:1438`) que
  `onExport` (`:3964`) rasteritza a la pàgina pdf-lib. **No hi ha registre central de tipus**:
  són dues cadenes `if (obj.type===...)` mantingudes a mà. El fitxer fa **5893 línies** (el brief
  deia ~2825; obsolet).
- **La cota POM ja és composició d'existents, NO cal tipus nou.** El flux viu `cota_pom`
  (`:3196-3227`) construeix `group{ path(headStart+headEnd, KONVA_COL.pom) + text(fill:white,
  bgFill:KONVA_COL.pom, bold) }`. El preset estàtic `preset_cota_pom` (`:2158-2169`) és la
  variant lliure (línia + marques + text, negre). Com que és un `group` de tipus existents,
  travessa els dos renders i l'export **de franc** (recursió de grup a `:1301` i `:1651`).
- **Paleta.** `KONVA_COL` (`:120`) ja conté `pom:'#dc2626'`; és l'excepció sancionada a la regla
  «colors via tokens» (Konva no resol `var()`, CLAUDE.md). El swatch ràpid `QUICK_COLORS` (`:5818`)
  ja inclou `#dc2626`. **Res a afegir a la paleta.**
- **Estat per-objecte existent (per a piggyback del mode revisió):** `layer` (`'template'|'data'|
  'free'`, z-order via `LAYER_ORDER` `:128`, gate d'edició), `locked` (bloqueja selecció/
  transform/delete), `visible` (`visible===false` amaga, honrat als TRES bucles: live `:1656`,
  export `:1449`, filtre `:1309`).
- **Precedent d'«estat derivat pintat»:** `isPendentVincle(obj)` (`:1242`) marca un `graded_table`
  amb binding pendent i el pinta amb una «cinta pendent» via `buildPendingRibbonPrims`
  (`:1372,1397,1583`). És exactament la forma que tindria un overlay d'estat de revisió.
- **Punt de compartició live↔export:** els helpers `build*Prims` / `addPrimsToGroup` (`:961`) són
  l'ÚNIC lloc on live i export comparteixen codi de dibuix — l'escape valve natural.

### Forats / Riscos
- **Cap bastida de «mode revisió» existeix** (ni estat `reviewState`, ni UI, ni branca de render).
  És greenfield; només `visible/locked/layer` i el patró `isPendentVincle`+`build*Prims` per
  recolzar-s'hi. (Nota: `reviewMode` a `FittingDetail.jsx:496` és una altra superfície — NO
  confondre.)
- **Perill de paritat del monòlit:** qualsevol estat visual nou s'ha d'afegir a DOS switches +
  potser la cadena de bounds (`:1301+`), transform (`:3041-3130`) i serialització. Mitigació:
  hostatjar la lògica de revisió a la capa `build*Prims` compartida, no una tercera cadena
  `.type===`.
- La persistència d'un camp per-objecte nou (p.ex. `pom_id` o `reviewState`) al camí de desat
  `.ftt` no s'ha traçat end-to-end; verificar-la abans d'implementar (és opac → probablement OK).

---

## B3 — SUPERFÍCIE DE DADES POM DEL MODEL

### Fets
- **La fitxa JA carrega els POMs del model.** `TechSheetEditor.jsx:2631` fa
  `fetch(.../models/${id}/base-measurements/)` → `pomRows` (`:1919`). Endpoint =
  `models/<id>/base-measurements/` (`models_app/urls.py:113`) → `base_measurements_view`
  (`pom/wizard_views.py:303`), funció que construeix el dict a mà (`:318-334`).
- **Camps entregats per POM** (`wizard_views.py:318-334`): `id, pom_id, codi_client, nom_client,
  nom_ca, nom_en, categoria_nom, base_value_cm, notes, nom_fitxa, origen, pom_abbreviation,
  **pom_code_global** (codi canònic `POM-XXX`), pom_is_key`. → **Codi canònic: SÍ. Nom: SÍ.
  `pom_id`: SÍ (ja hi és al payload, encara que la cota no el guardi).**
- **Àlies de client: ABSENT del payload del model.** `CustomerPOMAlias` (`pom/models.py:237-290`,
  FK `customer` cross-schema `db_constraint=False`, FK `pom` nullable, `client_code`,
  `description_en/local`) només es consulta per `customer` al seu propi viewset
  (`pom/views.py:529`) i a la pàgina de client (`CustomerDetail.jsx`, `DictionaryWizard.jsx`,
  `endpoints.js:301-313`). **Cap view resol els POMs d'un model a través dels àlies del seu client.**
- **Resolver reutilitzable existent:** `find_pom_master(code, description, customer)` →
  `(pom_master, match_type, confidence)` (`models_app/extraction_views.py:889`); prova l'àlies
  primer (`:914-941`). Però resol codi_entrant→POM (import), **no** POM→àlies (display).
  `dictionary_service.py` no té resolver propi; crida `find_pom_master` (`:129,147`).
- **La definició completa «com es mesura»** (start/end/reference point, scope, orientation,
  toleràncies, iso_ref, descripció) NO viatja per cap endpoint de model-POM; només a
  `POMMasterSerializer` (`pom/serializers.py:33-94`) i `GarmentPOMMapSerializer` (`:322-401`).

### Forats / Riscos
- **F1 — cap endpoint dona codi + nom + àlies + definició alhora per als POMs d'un model.** El
  payload de la fitxa porta codi canònic + noms però NO l'àlies ni la definició. Per a l'etiqueta
  «codi canònic + àlies de client» cal (a) estendre `base_measurements_view` amb l'àlies resolt,
  o (b) un fetch extra `customer-pom-aliases/?customer=<id>` i join client-side per `pom_id`.
- L'etiqueta d'avui al panell (`:4956`) = `nom_fitxa || pom_abbreviation || codi_client` — no és
  l'àlies canònic-resolt que demana el brief.
- Risc N+1: `find_pom_master` escaneja tot `POMMaster` per crida (`:947-968`); per decorar la
  llista viva d'un model, preferir un prefetch de `CustomerPOMAlias` per `pom_id`.

---

## B4 — PIPELINE ASYNC D'IA EXISTENT

### Fets
- **Feature:** wizard d'`ImportSession` (extracció de mesures d'xlsx amb fallback). Fitxer mestre
  `models_app/extraction_views.py`; parser determinista `_parse_excel_poms` (`:233-438`) com a
  «porta d'abdicació»; si abdica → IA. Rutes a `models_app/urls.py:74-91`.
- **TOT SÍNCRON dins la request HTTP.** Cap Celery, cap thread, cap background task, cap polling
  (grep negatiu de `celery|delay(|apply_async|threading|Thread(|async def` a `models_app/`). Cada
  view instancia `anthropic.Anthropic(api_key)` i bloqueja fins a la resposta:
  `import_session_extraccio_view` (`:1440-1449`, Opus, `max_tokens=16000`, thinking adaptatiu),
  `import_session_cribratge_view` (`:610-616`), `_revise_excel_poms_with_sonnet` (`:1192-1203`).
  L'estat viu a `ImportSession.estat`; és un wizard multi-pas conduït pel client, **no** un
  patró de feina async amb polling.
- **Comptabilitat, no status:** `AIUsage` (migració `0059_aiusage.py`) registra cost/tokens
  després de cada crida via `registra_us_ia()` (`extraction_utils.py:155`); `cami` ∈
  `cribratge|revisio|extraccio|fallback`. No hi ha taula de jobs ni progrés recuperable.
- **Config:** `ANTHROPIC_API_KEY` (env → `settings.py:132-133`; fallback dual a
  `extraction_service.py:86-94`). Models hardcoded: `CRIBRATGE_MODEL/EXTRACCIO_MODEL =
  'claude-opus-4-7'` (`:93,1177`), `EXCEL_REVISION_MODEL='claude-sonnet-4-6'` (`:1180`).
  El camí SDK del wizard **no fixa timeout** (default SDK ~10 min); el camí httpx sí
  (`extraction_service.py:168`, 120s).
- **Multimodalitat JA existent i en ús.** `_cribratge_content_block()` (`:441-475`) i
  `_file_to_content_block()` (`extraction_service.py:97-128`) construeixen blocs
  `{"type":"image","source":{"type":"base64",...}}` per png/jpg/webp/gif i `document` per PDF; ja
  s'invoquen amb imatges reals al cribratge (`:607`) i extracció PDF (`:1437`). **Cap canvi al
  client per acceptar una imatge de pàgina.**

### Forats / Riscos (per a F3)
- **Reutilitzable:** el patró d'instanciació + `messages.create(content=[image_block, text_block])`
  + `safe_json_parse` + `registra_us_ia` és directament reaprofitable per a la crida de visió
  (imatge de pàgina + llista de codis POM → JSON de placements). Cal un view nou, un prompt nou i
  (opcional) un `cami` nou a `AIUsage`.
- **Risc central — timeout:** l'Opus + thinking + 16k sense timeout ja frega el temps de worker
  Gunicorn; una crida de visió llarga síncrona pot donar 502. **No hi ha CAP infra async
  reutilitzable** → si es vol no bloquejar, s'ha de construir de zero.
- Sense traçabilitat de «feina en vol»: si el worker cau a mig `messages.create`, no queda rastre.

---

## B5 — CAPACITAT SVG I DETECCIÓ DE VISTES

### Fets (correccions al brief incloses)
- **Llibreries reals** (`requirements.lock`, dump 68 línies): `numpy==2.4.6` **SÍ present** (el
  brief deia que no), `pandas==3.0.3`, `pillow==12.2.0`, **`PyMuPDF==1.27.2.3`** (ràster robust),
  `reportlab`, `ezdxf==1.4.4`. `cairosvg==2.9.0` **NO és al lock** — només a `requirements.txt:33`,
  importat defensivament amb `except ImportError` (`accounts/logo.py:41`) → fràgil.
  **Absents confirmats:** shapely, lxml, svgpathtools, scipy, scikit-image, opencv.
- **Frontend:** `paper@0.12.18`, `konva@10.3.0`, `pdf-lib@1.17.1`. Paper.js fa tota la feina d'SVG:
  `importSVG(..., {expandShapes:true})` + `imported.bounds` (`PaperFlatEditor.jsx:501-507`,
  `TechSheetEditor.jsx:1747-1799`).
- **Única rasterització SVG→PNG del backend:** `cairosvg.svg2png` a `accounts/logo.py:44` (només
  upload del logo). **El backend NO parseja estructura SVG en producció** (només a `patterns/
  tests.py:111,1051-1092` via `xml.etree`). Els SVG de fitxa venen del client; el backend els
  tracta com a blob opac.
- **Bounding-box existent** (tot min/max de punts, cap silueta): backend `patterns/svg.py:143-155`,
  `grading_projection.py:571-581`, `serializers.py:89-98`; frontend `patternGeometry.js:14-34`,
  bounds de Paper (`PaperFlatEditor.jsx:394-425`) i Konva `getClientRect` (`TechSheetEditor.jsx:
  3010-3016`).
- **ZERO connected-components / flood-fill / silhouette / hull / labeling** a tot el codebase
  (grep negatiu backend + frontend).

### Forats / Riscos (detecció de vistes)
- La detecció de vistes és **greenfield** per qualsevol camí:
  - **Backend ràster** (preferit determinista): `cairosvg`/`PyMuPDF` → `pillow` → `numpy` →
    connected-components **a mà** (no hi ha `scipy.ndimage.label`/skimage/opencv).
  - **Backend estructura**: caldria un lector `xml.etree` nou; agrupar per `<g>` assumeix que el
    dibuixant ha agrupat (no garantit).
  - **Frontend paper.js** (més barat, ja muntat): clustering per solapament de `bounds` a nivell
    de bounding-box, no de píxel; però NO és «determinista de servidor».
- **`cairosvg` no és al lock i és fràgil**; `PyMuPDF` (sí al lock) és l'alternativa robusta
  infrautilitzada.
- **Col·lisió de nom:** `vista` ja significa peça-facing al domini de patrons (`patterns/models.py:
  623`, `serializers.py:104`) → triar un altre mot per a «vista de pàgina» (p.ex. `view_slot`).

---

## B6 — CASA DE POMPlacement

### Fets
- **Migracions 0054-0056 (la infra «sketch base»):**
  - `0054_itemfitxer.py` crea **`ItemFitxer`** (catàleg), ancorat a `tasks.GarmentTypeItem`
    (garment-piece), CASCADE, `related_name='fitxers'` (`:30`); `tipus` inclou `SKETCH_FLETXES/
    SKETCH_NET/SKETCH_SVG` (`:22`); cadena de versions `versio/is_current/versio_anterior`
    (`:23,24,32`). Model viu `models_app/models.py:485-522`.
  - `0055_modelfitxer_derivat_de_item.py` afegeix `ModelFitxer.derivat_de_item` →
    `models_app.itemfitxer`, **SET_NULL** (`:14-18`). El comentari (`models.py:418-420`) diu que és
    una **CÒPIA importada**: «l'origen no es toca mai i pot desaparèixer sense afectar la còpia».
  - `0056_modelfitxer_derivat_de_model.py` afegeix `ModelFitxer.derivat_de_model` → self, SET_NULL
    (`:14-18`; procedència model→model, D17).
- **⚠️ MATÍS crític:** la relació és **còpia-amb-procedència (snapshot, SET_NULL), NO herència
  viva.** El fitxer del model és independent de l'ItemFitxer origen. No hi ha cap referència
  read-only *viva* al sketch base a nivell de fitxer. → contradiu la premissa «heretat pels models»
  del brief (veure PREGUNTES PATRÓ C).
- **Casa natural = `models_app`.** POMPlacement faria FK a `models_app.ItemFitxer` i/o
  `models_app.ModelFitxer` (sketch base, 2 dels 3 FK viuen aquí) + FK a `pom.POMMaster` (POM viu,
  mateix target que `BaseMeasurement.pom`, `models_app/models.py:583`). El patró establert és
  «consumidor de POM viu a la seva app i fa FK a `pom.POMMaster`». Descartats: `pom` (invertiria la
  dependència models_app→pom), `patterns` (geometria CAD real, capa diferent).
- **Sense eix customer explícit:** django-tenants segrega per schema. `models_app`, `pom`
  (`POMMaster` és per-tenant), `tasks` són tots `TENANT_APPS` (`settings.py:67-70`) → viuen al
  mateix schema; les FK cross-app són constraints reals.
- **Collision check — CAP col·lisió.** Revisats: `BaseMeasurement` (`models.py:568-623`:
  `base_value_cm`, `nom_fitxa` = etiqueta textual, `ordre`; cap coordenada/vista), `GradedSpec`
  (`fitting/models.py:181+`: valors de grading, cap coordenada), `PatternPOM` (`patterns/models.py:
  303-368`: geometria CAD DXF, capa diferent), logs i regles de grading. Cap model guarda
  coordenades de col·locació d'un POM sobre un sketch normalitzades per vista.

### Forats / Riscos
- **Còpia-snapshot vs herència viva** (veure PREGUNTES PATRÓ C, D1): cal decidir si POMPlacement
  penja de l'`ItemFitxer` (una veritat, catàleg) i els models el llegeixen, o es copia per-model
  com `BaseMeasurement`. El codi actual afavoreix còpia-snapshot; l'herència viva és paradigma nou.
- **Fall-through de peça ambigu:** dos candidats — `tasks.GarmentTypeItem` (àncora del sketch base,
  probable) vs `models_app.GarmentSet`/`Model.piece_number`.
- **Zona intocable (CLAUDE.md):** FK a `pom.POMMaster` amb `on_delete=PROTECT` (com PatternPOM),
  read-only al POM viu, **sense tocar** POMMaster ni el motor.
- **Doble FK ItemFitxer XOR ModelFitxer** → constraint + unicitat `(fitxer, pom, vista)` a decidir.
- **Eix «vista» inexistent** al domini → es crea de zero (vocabulari a fixar).

---

## B7 — SEMBRA DES D'ORIGINALS SVG (LOSAN/Brownie)

### Fets
- **Millor motlle idempotent:** `pom/management/commands/seed_losan_master_delta.py` (el nom és
  «sembra»). Font ancorada a `__file__`: `JSON_PATH = Path(__file__).resolve().parents[2] /
  'seed_data' / '...json'` (`:41`); idempotència per `get_or_create` de clau natural (`:154,179,
  189`); **dry-run per defecte** (`--no-dry-run`, `set_rollback(True)`, `:53,82-83`); i una
  **INVARIANT dura que ABORTA** si el recompte és incomplet (`:226-229`) — el guard contra pèrdua
  silenciosa. Variant `update_or_create`: `seed_losan_rules_v2.py:155` (si els re-runs han de
  refrescar).
- **On aterren els fitxers font:** `backend/fhort/pom/seed_data/` (únic `seed_data/` del repo). Ja
  hi ha un subdir d'assets binaris `seed_data/losan_package/assets/` amb un SVG real
  (`losan-logo.svg`) + un `.fttpt`. Landing natural per a fitxes precedents: un subdir nou sota
  `seed_data/`, resolt amb el mateix idiom `parents[2]/'seed_data'/...`.
- **Diana de persistència (si les fitxes es fan files):** `ModelFitxer`/`ItemFitxer` ja tenen
  `TIPUS='SKETCH_SVG'` (`models.py:385`) i `FileField(upload_to=...)`.
- **Cap codi existent ingesta ni parseja SVG de fitxa.** SVG només es *genera* (`patterns/svg.py`)
  o *rasteritza* (`accounts/logo.py`). Precedent de «llegir cotes + text d'un dibuix vectorial»:
  **DXF/AAMA via `ezdxf`** (`patterns/engine/aama_reader.py:89-242`, `_modelspace_texts`,
  `_max_piece_dimension`) — demostra la cascada (geometria decideix, text corrobora) però **NO és
  codi reutilitzable per a SVG**.

### Inventari de risc (parsing pur sense IA)
- Material recuperable per `xml.etree` pur: cotes vermelles com a `<line>`/`<path>` amb `stroke`
  vermell (fletxes) + `<text>` amb `fill` vermell (valor); siluetes com a `<path>` no-vermells. El
  repo ja emet i parseja aquesta mateixa forma de DOM (`patterns/svg.py:91,115,125`; `tests.py:
  1051-1092`).
- **Forat dominant — l'ASSOCIACIÓ.** Res al XML lliga un `<text>` «42» a la fletxa que anota, ni
  la fletxa a l'aresta que mesura. Aquest aparellament (edge, valor, POM) és inferència espacial i
  **no hi ha `shapely`** → bbox/distància a mà. Aquest és el risc que fa que «sembra per parsing
  pur» sigui molt més cara del que sembla.
- Altres forats: `xml.etree` NO resol classes CSS / `<style>` / atributs heretats de `<g>` (la
  detecció de «vermell» és multi-cas: `red/#ff0000/#f00/rgb()`); les fletxes solen ser `<path>`
  amb corbes (`C/A`) no `<line>`; el text pot venir en `<tspan>` amb `transform`/`dx/dy`.
  `cairosvg` només rasteritza → inútil per extreure.
- **Mitigació:** adoptar la INVARIANT-abort del motlle (`seed_losan_master_delta.py:226-229`): si
  una silueta/cota no resol, NO sembrar una fitxa parcial.

---

## B8 — FRONTERES I COL·LISIONS TRANSVERSALS

### Fets — Art previ (el més important)
- **`patterns/engine/ftt_pom_layer.py` = capa d'anotacions POM al DXF SOBIRÀ**, NO la fitxa
  informativa. És l'espec + reader/writer de la capa DXF `FTT-POM`. Llei canònica (`:14-25`):
  «**Projecció, mai font de veritat.** La veritat viu a `PatternPOM` (BD)... es llegeix com a
  PROPOSTA a validar, mai com a escriptura directa.» Dibuixa `LINE/POLYLINE/TEXT` als BLOCS DXF de
  la peça (`FTTPOMLayerWriter.write_piece_poms:247-274`); valors de `PatternPOM.valor_mesurat_mm`,
  mai d'un client. **Superfície: el DXF exportat (lliurable sobirà).**
- **`patterns/annotation_views.py` = API per ANCORAR POMs a geometria + declarar costures**, no
  cotes. `PatternPOMViewSet` (`:518-557`): el valor mesurat mai s'accepta del client, el servidor
  resol la RECEPTA (`definicio_mesura`) sobre la geometria (`_mesurar:134-150`). `SewRelationViewSet`
  (`:560-853`): costures/pinces. **Superfície: receptes DB resoltes contra la geometria DXF.**
- **Conclusió: superfícies diferents.** Cap dels dos toca el croquis informatiu de la fitxa.
- **La feature JA existeix a la fitxa informativa** (veure Resum executiu): `PRESET_TOOLS`
  (`:152`), presets `preset_cota_pom/annotation/callout` (`:2140-2187`), flux viu `cota_pom`
  (`:3196-3227`), `KONVA_COL.pom` (`:120`), i18n `tech_sheet.*`. → **B8 és extensió d'aquest
  fitxer, no construcció nova.**

### Fronteres confirmades (zero contacte)
- **Motor de patrons / traçadora** (`patterns/engine/operations.py`, `geometry.py`, `ports.py`) —
  ZERO. La cota és un dibuix Konva; ni llegeix ni escriu geometria de patró.
- **Capa DXF `FTT-POM`** (`ftt_pom_layer.py`) — ZERO. Superfície sobirana diferent.
- **API d'ancoratge POM/costures** (`annotation_views.py`) — ZERO. Ancora receptes; la cota no
  porta `pom_id`/recepta (i F1 en portarà només com a vincle de lectura, no recepta de geometria).
- **G6 grading + G1 escriptura de mesures** (`fitting/services.py:561`, `fitting/views.py:77`,
  `pom/services.py:generate_graded_specs`) — ZERO. La cota entra com a **string literal, sense
  binding** (frontera G1 guardada a `TechSheetEditor.jsx:3204,2159`). F1 preserva la frontera:
  vincle **només-lectura**.
- **Billing (parkat)** (`commerce/`) — ZERO.
- **Llei «LLM mai dibuixa coordenades»** — és del motor DXF (`MOTOR_DE_PATRONS_V2.md:87`;
  `patterns/engine/ports.py:118` «lectura determinista»), **NO** de la fitxa informativa →
  fora d'abast per a aquesta feature, coherent amb el règim Patró C declarat.
- **i18n:** claus del TechSheetEditor al namespace **`tech_sheet`** de
  `frontend/src/i18n/{ca,es,en}.json` (obre a `ca.json:2551`). Exemples existents:
  `tool_cota_pom` (`:2632`), `preset_cota_pom` (`:2650`), `poms_hint` (`:2708`), `pom_cota_hint`
  (`:2718`). Les cadenes noves del mode revisió hi entren, amb paritat ca/es/en (i18n-gate CLAUDE.md).

---

## DIMENSIONAMENT PER FASE

### F1 — Cota VIVA sense IA (promoure el dibuix mort a vincle de lectura)
**Objectiu:** la cota `cota_pom` deixa de ser un string literal i passa a portar `pom_id`/`bm_id`,
amb l'etiqueta re-derivada del POM viu (codi canònic + àlies de client), en **només lectura**
(mai escriu el valor de mesura → preserva la frontera G1).

Fitxers que es tocarien:
- `frontend/src/pages/TechSheetEditor.jsx` — (a) l'objecte de la cota guarda `pom_id`/`bm_id`
  (`:3206-3227`, avui `cotaPreset={text}`); (b) el panell «arma» amb el `bm` sencer, no només
  `{text}` (`:4958`); (c) etiqueta = codi canònic + àlies resolt en comptes de `nom_fitxa||...`
  (`:4956`); (d) re-derivació de l'etiqueta a la càrrega/render des de `pomRows` (POM viu).
- `backend/fhort/pom/wizard_views.py` — `base_measurements_view` (`:303-337`): afegir l'àlies de
  client resolt per `pom_id` (prefetch de `CustomerPOMAlias`), perquè l'etiqueta canònic+àlies es
  pugui construir sense fetch extra.
- `frontend/src/i18n/{ca,es,en}.json` — cap clau nova imprescindible si es reutilitza `tech_sheet.*`
  existent; textos d'ajuda si canvia l'afordança del panell.
- **Sense migració, sense tocar `schema_version`** (`pom_id` és escalar, round-trippa lliure;
  no és host-ref).

### F2 — POMPlacement + sembra des d'originals SVG
**Objectiu:** entitat de precedent de col·locació normalitzat per vista + comandes de sembra.

Fitxers que es tocarien:
- `backend/fhort/models_app/models.py` — nou model `POMPlacement` (FK `ItemFitxer`/`ModelFitxer` +
  FK `pom.POMMaster` `PROTECT`, eix `vista`/`view_slot`, extrems en coordenades RELATIVES a la
  caixa de la silueta de la vista, unicitat `(fitxer, pom, vista)`).
- `backend/fhort/models_app/migrations/00XX_pompacement.py` — migració (auditar columnes als 3
  schemas després de `migrate_schemas`, mai `--schema`).
- `backend/fhort/models_app/{serializers.py, views.py, urls.py}` — CRUD read del precedent + la
  cascada de resolució (precedent exacte → transposició de peça germana → buit).
- `frontend/src/pages/TechSheetEditor.jsx` — consumir el precedent (pre-omplir cotes des de
  POMPlacement) + marcar la «llista de treball» (ja hi ha `cotesColocades`, `:4957`).
- **Sembra:** `backend/fhort/pom/management/commands/seed_<...>.py` (motlle
  `seed_losan_master_delta.py`, dry-run + invariant-abort) + `backend/fhort/pom/seed_data/<subdir>/`
  per als SVG font.
- ⚠️ **La sembra per parsing pur té el forat d'ASSOCIACIÓ (B7) sense suport de llibreria** → veure
  PREGUNTES PATRÓ C (D3): decidir parsing pur vs IA-assistida vs manual per a la ingesta inicial.

### F3 — Endpoint proposta IA + mode revisió
**Objectiu:** crida de visió (imatge de pàgina + llista de codis POM → JSON de col·locacions) +
mode revisió (acceptar/descartar/arrossegar; motlle `DictionaryWizard`, mai autoescriptura).

Fitxers que es tocarien:
- `backend/fhort/models_app/` (nou view + prompt) — reutilitzar `_cribratge_content_block()`
  (`extraction_views.py:441-475`) per al bloc imatge, el patró `messages.create` + `safe_json_parse`
  + `registra_us_ia`; nou `cami` a `AIUsage` (`0059_aiusage.py`). ⚠️ decidir sync vs async
  (timeout, B4-F2): no hi ha infra async → sync amb guard de timeout o construir job de zero.
- `frontend/src/pages/TechSheetEditor.jsx` — mode revisió: objectes proposats amb estat
  pendent/acceptat/descartat, recolzat en `visible/layer` + el patró `isPendentVincle`+`build*Prims`
  (`:1242,961`); acceptar → cota viva F1; descartar → esborrar; arrossegar → ajust manual d'extrems.
- `frontend/src/components/DictionaryWizard.jsx` — motlle d'UI del cicle acceptar/descartar.
- `frontend/src/i18n/{ca,es,en}.json` — cadenes noves del mode revisió al namespace `tech_sheet`.

---

## PREGUNTES PATRÓ C (decisions per a l'Agus)

- **D1 · Còpia-snapshot vs herència viva.** El brief diu que el precedent «penja del sketch base
  (heretat pels models que en neixen)». Però la infra existent (`ModelFitxer.derivat_de_item/model`,
  0055/0056) és **còpia-amb-procedència SET_NULL, no herència viva** (`models.py:418-420`).
  POMPlacement ha de: (a) penjar de l'`ItemFitxer` (una veritat de catàleg) i els models llegir-lo
  via `derivat_de_item`, o (b) copiar-se per-model com `BaseMeasurement`? L'opció (a) és paradigma
  nou al codebase.
- **D2 · Etiqueta de la cota viva (F1).** Confirmar la fórmula: «codi canònic (`pom_code_global`) +
  àlies de client (`CustomerPOMAlias.client_code`)». Avui el panell mostra `nom_fitxa ||
  pom_abbreviation || codi_client` (`:4956`). Quin d'aquests és l'etiqueta visible i quin
  metadada? Cal l'àlies resolt (implica estendre `base_measurements_view`)?
- **D3 · Ingesta inicial dels precedents SVG (F2).** El parsing pur té el forat d'ASSOCIACIÓ
  (edge↔valor↔POM) sense `shapely` (B7). Tres opcions: (i) parsing pur amb invariant-abort (car,
  fràgil, sense pèrdua silenciosa); (ii) IA-assistida (visió sobre l'SVG rasteritzat, revisió
  humana — reutilitza F3); (iii) manual (llista de treball des de zero). Quina per a LOSAN/Brownie?
- **D4 · Vocabulari de «vista».** No existeix cap eix vista al domini; a més `vista` ja vol dir
  peça-facing a `patterns` (col·lisió, B5). Quin vocabulari (davant/darrere/detall?) i quin nom de
  camp (`view_slot`?) per no xocar?
- **D5 · Sync vs async per a la crida de visió (F3).** No hi ha infra async (B4). Acceptem la crida
  de visió SÍNCRONA (amb guard de timeout, risc de 502 en pàgines denses) o cal construir un job
  async de zero abans de F3?
- **D6 · Detecció de vistes: backend determinista vs frontend paper.js (B5).** El brief prefereix
  backend determinista, però requereix connected-components a mà sobre numpy (no scipy/opencv) i
  `cairosvg`/`PyMuPDF`. El camí frontend (clustering de `bounds` de Paper) és molt més barat però no
  és «de servidor». Quin per a la v1?
- **D7 · Fall-through de peça (B6).** El precedent cau a nivell de `tasks.GarmentTypeItem` (catàleg,
  on viu el sketch base) o de `GarmentSet`/`piece_number`? Afecta la clau d'unicitat de POMPlacement.

---

*Diagnosi read-only. Cap codi tocat, cap migració, cap escriptura fora de `docs/`. Els números de
línia són del HEAD `a2afe59` (branca `dev`) el 2026-07-26 i poden desplaçar-se amb commits
concurrents. Relacionat: `DIAGNOSI_EDITOR_ESTAT.md`, `DIAGNOSI_W6_I_FITXA.md`.*
