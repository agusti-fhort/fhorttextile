> ⚠️ SUPERADA 2026-07-07 — implementada (G3 import vell retirat + G7 fix calendari 86a05cd). Consulta només com a històric.

# DIAGNOSI BLOC 4 — import vell + plantilla + calendari

**Protocol:** FASE B · READ-ONLY ABSOLUT · 0 codi · 0 push · branca `dev` (worktree `/var/www/ftt-staging`).
**Data:** 2026-06-26.
**Mètode:** director-investigació + investigador-codi ×6 (paral·lel) + documentador. Tots els fets
verificats amb `grep -n` + lectura de rangs. Recomptes de BD amb `SELECT COUNT` read-only sobre schema
`fhort` (tenant únic; no hi ha schema de clon QA separat — el model QA viu dins `fhort`; **golden 162 no tocat**).
**Llegenda:** `FET (fitxer:línia)` = verificat · 💡PROPOSTA = a validar pel CTO · OBERT = no determinable read-only.

> ⚠️ **Nota de fiabilitat:** durant la investigació un investigador va afirmar que un commit `8048e77`
> havia "retirat" les views d'import. **És FALS** (no existeix tal retir; les rutes són vives — veure §A).
> Tota la §A s'ha re-verificat contra `urls.py`, `ImportWizard.jsx` i `git log`. Els números de línia del
> brief original estaven desfasats en diversos punts; aquí hi ha els **àncores reals actuals**.

---

## RESUM EXECUTIU (per decidir sense obrir cap fitxer)

1. **§A / G3 — la contradicció de registre RESOLTA:** el "camí VELL d'import" (les views
   `extract_from_file_view` / `create_from_extraction_view` + rutes `extract-from-file` /
   `create-from-extraction`) **ja està retirat**: les definicions no existeixen i les rutes no són a
   `urls.py`. El que el MAPA encara etiqueta com a "vell" (`extraction_service.py` + `EXTRACTION_PROMPT`)
   **NO és el camí d'import**: avui és el **motor d'extracció de la size-map** (1 consumidor viu).
   El **wizard nou** (`import_session_*`) usa una pila DIFERENT (SDK `anthropic` + `TECH_SHEET_EXTRACTION_PROMPT`,
   models opus-4-7/sonnet-4-6), no `extraction_service`. → **"retirar el camí vell d'import" està en gran part FET**;
   només queden 2 restes mortes de debò (`extract_images_from_pdf`, `_create_pom_alert`). G3 és **pur codi, cap migració**.
2. **§B — plantilla:** la plantilla **bulk ja apunta a la taxonomia nova** (GarmentType actiu + GarmentTypeItem
   active), alineada amb **17 famílies / 57 items / 125 POMGlobal** (recomptes confirmats a BD). No cal canvi
   estructural de columnes. El deute real és una eina de seed obsoleta (`reseed_tenant_fhort.py`) que petaria.
   Frontera grading (D-10/G6) **no s'ha de creuar**.
3. **§C / G7 — bug calendari:** asimetria confirmada (confecció col·lapsada, fitting convocatòria NO).
   **Fix backend** (col·lapsar com la confecció, `views.py:456-458`) té **blast radius ~zero** i és coherent amb
   la mitigació ja feta; fix frontend toca el render compartit. Decisió de forma (N marcadors vs 1 bloc) = CTO.

---

# SECCIÓ A — G3: retirar el camí VELL d'import (CONTRADICCIÓ RESOLTA)

## A0 — Veritat de terra que resol la tensió de registre

| Afirmació | Font | Veredicte amb grep |
|---|---|---|
| "extraction_service/EXTRACTION_PROMPT es MANTÉ (viu: **wizard nou** + size-map)" | DECISIONS P6 | **CONCLUSIÓ correcta (mantenir), RAONAMENT erroni**: el wizard nou **NO** l'usa; **només** la size-map |
| "extraction_service.py + EXTRACTION_PROMPT són el camí VELL, candidats a retir; el wizard nou usa TECH_SHEET" | MAPA_SISTEMA | **Correcte** que el wizard usa `TECH_SHEET` (fitxer diferent); **sobredimensionat** dir "candidat a retir" → té consumidor viu (size-map) |

**FET** — `extraction_service` només té **1 importador viu** a tot el backend:
- `pom/size_map_views.py:330` (`from fhort.models_app.extraction_service import extract_from_file`) + crida a `size_map_views.py:353`.
- `models_app/settings.py:130` (comentari) i `models_app/urls.py:64` (comentari) — no són usos, són text.

**FET** — el **comentari** de `urls.py:64` ("`extraction_service`/`EXTRACTION_PROMPT` … els usa el wizard nou + size-map")
**és INEXACTE**: el wizard nou no importa `extraction_service` (confirmat per grep d'imports). És la mateixa
conflació que va arrossegar el P6.

**Hipòtesi de conflació del brief — CONFIRMADA:** el P6 va barrejar tres coses de nom semblant que viuen en
fitxers diferents: `extraction_service.py` (motor opus-4-5/httpx, ara size-map), `extraction_utils.py` (parse
compartit) i `find_pom_master`/`match_size_system` (que viuen a `extraction_views.py`/`matching.py`, **no** a
`extraction_service.py`).

## A1 — Les 3 peces de nom semblant (la trampa)

| Símbol | Def (fitxer:línia) | Pila | Cridadors VIUS |
|---|---|---|---|
| **extraction_service.py** | | opus-4-5, **httpx cru** | |
| `extract_from_file` | `extraction_service.py:129` | — | **NOMÉS** `size_map_views.py:353` |
| `extract_images_from_pdf` | `extraction_service.py:234` | — | **0 (MORT)** |
| `EXTRACTION_PROMPT` (català) | `extraction_service.py:15-77` | — | intern a `extract_from_file` (`:142`) |
| MODEL `claude-opus-4-5` (httpx raw) | `extraction_service.py:81` (+ post `:166`) | — | intern |
| **extraction_prompt.py** | | | |
| `build_extraction_prompt` | `extraction_prompt.py:19` | size-map | `extraction_service.py:142` |
| `TECH_SHEET_EXTRACTION_PROMPT` | `extraction_prompt.py:86` | **wizard nou** | `extraction_views.py:756/798`, `tech_sheet_views.py:38/120` |
| **extraction_utils.py** (compartit, viu) | | | |
| `safe_json_parse` | `extraction_utils.py:69` | compartit | `extraction_service.py:181`, `extraction_views.py:350/642/812`, `views.py:1279`, `tech_sheet_views.py:140` |
| `salvage_measurements` | `extraction_utils.py:126` | compartit | `extraction_views.py:814`, `tech_sheet_views.py:143` |

**FET — el wizard nou (`import_session_*`) NO toca `extraction_service`.** La seva pila d'extracció:
`anthropic.Anthropic` (SDK, no httpx) a `extraction_views.py:287/333, 622/627, 752/792`, models
`CRIBRATGE_MODEL='claude-opus-4-7'` (`:121`), `EXTRACCIO_MODEL='claude-opus-4-7'` (`:612`),
`EXCEL_REVISION_MODEL='claude-sonnet-4-6'` (`:615`), i `TECH_SHEET_EXTRACTION_PROMPT` (`:756/798`).

## A2 — Les "2 views velles" + rutes → JA RETIRADES

**FET** — `def extract_from_file_view` i `def create_from_extraction_view` **NO existeixen** a tot el backend
(`grep def …` → NONE). Les rutes `extract-from-file` / `create-from-extraction` **no són a `urls.py`** (només
un comentari obsolet a `urls.py:47`). → El "camí vell d'import" (views + rutes) **ja està retirat**.

**FET — el que SÍ és viu i és el wizard NOU** (no confondre amb "vell"): rutes `import_session_*` a
`urls.py:62-84`, consumides pel component **`components/ImportWizard/ImportWizard.jsx`**:
`:143` cribratge · `:164` talles · `:212` extracció · `:262` poms · `:315` grading-preview · `:351/377` mesures ·
`:381` library-prefill · `:428` teixit · `:452` confirmar. → **9 consumidors de UI vius** (no 0).

**FET — efectes laterals "del camí vell" que ja NO disparen:**
- `_create_pom_alert` (`extraction_views.py:44`, crea `POMAlert origen='IMPORTACIO'` a `:67`): **0 cridadors → zombi, mai s'executa.**
- Creació automàtica de `POMMaster` / email a admins: **no existeix al codi actual** (`find_pom_master` només cerca, no crea).

## A3 — Extracció d'imatges del PDF (pregunta de producte)

- **FET** `extract_images_from_pdf` (`extraction_service.py:234`): **0 cridadors** a tot el backend.
- **FET** no desa res: retorna dicts `{nom, categoria:'Disseny', bytes, origen:'INCRUSTADA'|'RASTERITZADA'}`
  (`extraction_service.py:272-284, 301-313`). Qui decidia desar-les era el camí vell (ja retirat).
- **FET** el wizard nou **NO** extreu imatges: desa el PDF com a `ModelFitxer(categoria='Document')`
  (a `import_session_confirmar_view`).
- **FET** cap consumidor viu de les imatges: 0 referències frontend a `'sketch'`/`'Disseny'`/`'INCRUSTADA'`/`'RASTERITZADA'`.
- 💡 **Conclusió:** retirar `extract_images_from_pdf` **no perd res viu** — és funcionalitat morta de facto.

## A4 — Serveis COMPARTITS que sobreviuen (confirmat: 0 dependència del "vell")

| Símbol | Def (fitxer:línia) | Importa `extraction_service`/`EXTRACTION_PROMPT`? | Consumidors |
|---|---|---|---|
| `find_pom_master` (6 estratègies) | `extraction_views.py:529` | **No** | wizard `import_session_poms_view`; usa `_POM_SYNONYMS` (`:562`) |
| `match_size_system` | `matching.py:55` | **No** | bulk_import (`resolve_row`) + W5 |
| `safe_json_parse` / `salvage_measurements` | `extraction_utils.py:69/126` | **No** | compartit (taula A1) |
| `build_extraction_prompt` | `extraction_prompt.py:19` | usa `EXTRACTION_PROMPT` però viu via size-map | `extraction_service.py:142` |
| `TECH_SHEET_EXTRACTION_PROMPT` | `extraction_prompt.py:86` | **No** (constant independent) | wizard nou + tech_sheet |

**Cap BANDERA:** cap servei compartit depèn de `extraction_service`. `find_pom_master` viu a `extraction_views.py`,
**no** a `extraction_service.py` (desmenteix la conflació). `build_extraction_prompt` només viu lligat a la
size-map (via `extract_from_file`), no al wizard nou.

## A5 — Veredicte G3 (FET, sense decidir l'acció)

| Peça | Estat | Abast de retir si el CTO ho decideix |
|---|---|---|
| views `extract_from_file_view` / `create_from_extraction_view` + rutes | **JA RETIRAT** | — (fet) |
| `extract_images_from_pdf` (`extraction_service.py:234`) | **MORT SEGUR** (0 cridador) | esborrar funció; cap ruta, cap i18n, cap migració |
| `_create_pom_alert` (`extraction_views.py:44`) + branca `POMAlert origen='IMPORTACIO'` (`:67`) | **MORT SEGUR** (0 cridador, mai dispara) | esborrar funció; **cap migració** (veure sota) |
| `extraction_service.extract_from_file` + `EXTRACTION_PROMPT` + `build_extraction_prompt` | **VIU** (size-map) | **NO retirable** sense trencar la size-map (`size_map_views.py:353`) |
| `find_pom_master`, `match_size_system`, `extraction_utils.*`, `TECH_SHEET_EXTRACTION_PROMPT` | **COMPARTIT** (sobreviu) | no tocar |

**FET — G3 és PUR CODI, cap esquema:**
- `POMAlert.origen` és un `CharField(max_length=20, default='FITTING')` **sense `choices`** (`fitting/models.py`,
  migració `fitting/0005_sprint_s11_pomalert_extra.py`). `'IMPORTACIO'` és un string lliure; retirar el codi
  **no requereix migració** (registres històrics, si n'hi ha, queden inerts).
- Cap ruta a treure (ja no existeixen); **0 claus i18n exclusives** del camí vell (les claus existents són genèriques i reutilitzades).

> 🔑 **Reframe per al CTO:** "retirar el camí vell d'import" està **gairebé fet**. El que queda etiquetat "vell"
> (`extraction_service`) és en realitat **el motor de la size-map** sobre la pila antiga (opus-4-5 + httpx cru).
> Jubilar-lo seria una decisió **diferent** —migrar la size-map a la pila del wizard nou (SDK `anthropic` +
> `TECH_SHEET`)— **no** una neteja d'import. Retirals "gratis" ara mateix: `extract_images_from_pdf` i `_create_pom_alert`.

---

# SECCIÓ B — PLANTILLA D'IMPORT (17 famílies + nova taxonomia)

## B1 — Estat de la plantilla BULK actual

**FET** `bulk_import_service.py:15-24`:
- `COLUMNS` (15): nom_prenda, **familia**, **tipus**, any, temporada, target, construccio, run_talles,
  talla_base, codi_client, col·leccio, color_referencia, es_conjunt, referencia_conjunt, piece_number.
- `OBLIGATORIES` (9): nom_prenda, familia, tipus, any, temporada, target, construccio, run_talles, talla_base.
- `DROPDOWN_COLS` (6): familia, tipus, any, temporada, target, construccio.
- `META_SHEET='_meta'` · `PLANTILLA_SHEET='Plantilla'`.

**FET** generació: `bulk_import_views.py:28` (GET `bulk-import/template/`) → `generate_template_bytes(customer)`.
Fulls: `Plantilla` + `Instruccions` + ocults `_families/_items/_targets/_construccions/_seasons/_years` + `_meta`
(`bulk_import_service.py:97-162`).

**FET — fonts dels dropdowns (`build_catalog`, `bulk_import_service.py:48-92`):**
- `familia` → `GarmentType.objects.filter(actiu=True)` per `nom_client` (`:54-57`)
- `tipus` → `GarmentTypeItem.objects.filter(active=True)`, label `"{nom_client} / {item.name}"` (`:61-69`)
- `target` → `Target` (`:71-77`) · `construccio` → `ConstructionType` (`:79-85`) · `_seasons` → `Model.TEMPORADA_CHOICES` · `_years` → rang ±2 anys.
- Coherència família↔item forçada a `resolve_row` (`:229`, `item.garment_type_id == fam.id`); `resolve_row` retorna `garment_type` + `garment_type_item` (`:296`).

→ **FET: la plantilla bulk JA referencia la taxonomia nova** (GarmentType actiu + GarmentTypeItem active), **no** un eix família vell.

## B2 — Taxonomia nova (referència) + recomptes de BD

- **FET** `GarmentType` — `pom/models.py:372`: `codi_client`, `nom_client`, `grup` (macro-categoria), `construccio_habitual`, `garment_type_global` (FK), `is_system`, `actiu`.
- **FET** `GarmentTypeItem` — `tasks/models.py:255`: `garment_type` (FK), `code`, `name`, `complexity_order`, `active`, `base_size_definition` (FK), `grading_rule_set` (FK).
- **FET** `restructure_garment_types_v2` — `pom/management/commands/restructure_garment_types_v2.py:32-162`: sembra **17 famílies** (`:32-85`) + **57 items** (`:87-160`), idempotent (`update_or_create`, mai esborra).
- **FET (BD, schema `fhort`, read-only)** — confirmats per `SELECT COUNT`:

  | Recompte | Model / taula | Valor |
  |---|---|---|
  | POMGlobal | `pom/models.py:8` / `pom_pomglobal` | **125** ✅ (no 116/106) |
  | GarmentType actius (= famílies) | `pom/models.py:372` / `pom_garmenttype` | **17** ✅ (total 19; 2 inactius) |
  | GarmentTypeItem | `tasks/models.py:255` / `tasks_garmenttypeitem` | **57** |

  ⚠️ **Nomenclatura:** el camp `grup` **NO** són les "famílies" (només 6-7 valors macro: TOPS/BOTTOMS/…); la
  "família" canònica = **una fila de `GarmentType`** (17 actives).
- **FET** POM a la plantilla: **NO** hi van directament. Els POMs es materialitzen **després** de crear el model;
  `GarmentPOMMap` s'indexa per `garment_type_item` (migració `pom/0016_...` va **eliminar** `garment_type` del map).

## B3 — Eines de seed (¿petarien?)

- **FET** `reseed_tenant_fhort.py:290-295` crea `GarmentPOMMap(garment_type=gt, …)` — **camp eliminat** per migració
  `pom/0016`. → **petaria** si s'executés (AttributeError/IntegrityError). Capçalera ja el marca OBSOLET (2026-06-17). **No executar.**
- **FET** el camp `Model.familia` ja va ser eliminat (migració `models_app/0025_remove_model_familia_...`); cap codi viu el referencia.
- **OBERT** `seed_pom_maps_to_items.py`: no verificat símbol per símbol en aquesta passada; cal `grep` del camp `garment_type=` abans de reusar-lo (probable mateix patró obsolet que `reseed_tenant_fhort`).

## B4 — Wizard single-model

- **FET** opera **per `garment_type_item`**: `create-wizard` (`views.py:298-388`) resol amb `_resolve_garment_def`
  (`views.py:249-293`) → si arriba `garment_type_item_id`, **deriva** `garment_type` i `grup` de l'item (`:265-268`);
  el Model rep `garment_type_item`/`garment_type`/`garment_group` (`:387`).
- **FET** cribratge (`extraction_views.py:308`) llegeix `garment_type_item_code` i el desa a
  `ImportSession.tipologia_confirmada` (`:325`), **no** muta el Model (el Model ja el porta assignat). Els POMs es
  deriven del **document + catàleg (matching)**, no de `GarmentPOMMap` ("el document mana").

## B5 — Pregunta de disseny + frontera grading

💡 **PROPOSTA (a validar):** la feina de plantilla és **més petita del que es temia** — la plantilla bulk **ja està
alineada** amb 17 famílies / 57 items / 125 POMs (les fonts dels dropdowns ja són GarmentType actiu + GarmentTypeItem
active). El que cal acotar:
- (a) confirmar que els dropdowns filtren correctament (actiu/active) i que la coherència família↔item (`:229`) cobreix els 57 items;
- (b) **decisió de producte:** els POMs **no** són a la plantilla avui (es materialitzen després). Si es vol portar-los a la plantilla, caldria un eix nou per `garment_type_item` (com el POMBrowser ASSIGN), **no** per família;
- (c) **deute net:** `reseed_tenant_fhort.py` (i probablement `seed_pom_maps_to_items.py`) usen l'eix família eliminat → jubilar/reescriure abans de reusar.

🚧 **FRONTERA (no creuar):** la sprint SOBIRANIA DE LA REGLA fixa que l'import **reté base+deltes+breaks** i **NO** el
grading propagat (col·lisiona amb el motor). La feina de plantilla **no ha de reobrir** grading propagat (**D-10/G6**).

---

# SECCIÓ C — G7: bug calendari (convocatòria de fitting replicada cada dia)

## C1 — El bug segueix viu (codi exacte actual; àncores corregides)

- **FET — confecció COL·LAPSADA** `planning/views.py:302-327`: `marker_d = p.expected_at or req_d`;
  `start = end = marker_d.isoformat()` (`:311-312`); `all_day=True` (`:319`). *(El brief deia ~296-321.)*
- **FET — fitting convocatòria NO col·lapsat** `planning/views.py:456-458`:
  `start_dt = primera.data` · `end_dt = sessions_grup[-1].data` · `all_day=True`. *(El brief deia 447-449.)*
  → **ASIMETRIA confirmada.**
- **FET — fitting individual** `planning/views.py:390-392`: `start == end` (un dia, no multi-dia).
- **FET — `inRange` (frontend)** `PlanningCalendar.jsx:171-174`: pinta un all-day a **cada** dia entre `_start` i
  `_end`. Consumidors: `allDayByDay` (`:177` → TimeGrid `:285`) i `monthByDay` (`:178` → MonthGrid `:252`).
  L'expansió s'aplica a **tot** `_allDay`, no només fitting.
- **FET — únic productor d'all-day MULTI-DIA** = fitting convocatòria (`:456-457`). Confecció i fitting individual són `start==end`.

## C2 — Les dues vies de fix (cost de cada una)

**FIX BACKEND (col·lapsar com la confecció) — cost BAIX, blast radius ~zero:**
- Canvi: `planning/views.py:456-458` → emetre `start_dt == end_dt` (un marcador).
- Consumidors de `calendar/events`: **només** `PlanningCalendar.jsx`. Altres lectors són insensibles al rang:
  `ModelMilestones.jsx` agrupa per `ev.start.slice(0,10)`; `Dashboard.jsx` filtra `tipus === 'tasca'` (ignora fitting);
  `ProjectGantt.jsx` usa `/plan/gantt/`, no `calendar/events`.
- **Coherent amb la confecció ja mitigada** (mateix patró).

**FIX FRONTEND (que `inRange` no expandeixi grups multi-dia) — cost BAIX però acoblament semàntic:**
- Canvi: `PlanningCalendar.jsx:171-174` (condició per excloure `meta.convocatoria`).
- Toca el **render compartit** (`allDayByDay`/`monthByDay`), però com que l'únic all-day multi-dia és la convocatòria,
  el dany col·lateral és baix. Més fràgil: el front ha de conèixer la semàntica de "convocatòria".
- **(alt) backend `all_day=False`** per la convocatòria: la treu de la franja all-day cap a la graella horària →
  **cost MEDI** (canvi de presentació).

💡 **PROPOSTA tècnica (decisió del CTO):** el **fix backend** és el de menys risc i coherent amb la confecció ja
arreglada. Però abans cal resoldre C3 (forma correcta), perquè condiciona com es col·lapsa.

## C3 — Semàntica (pregunta de producte a deixar plantejada)

- **FET** model `FittingSession` — `fitting/models.py:202-289`: **1 sessió = 1 data** (`data` DateField, `start_time`/
  `duracio_minuts` opcionals); `convocatoria` (UUID) **agrupa N sessions** creades juntes. Una convocatòria = **N files
  `FittingSession` separades** que comparteixen el UUID.
- 💡 **Pregunta oberta de disseny:** una convocatòria amb N sessions en dies diferents s'ha de veure com **N marcadors**
  (un per sessió real) o com **1 bloc**? El bug actual (replicar a **tots** els dies del rang, inclosos els **sense
  sessió**) és **incorrecte segur**; N-vs-1 és decisió de producte.

---

# SECCIÓ D — CAPS SOLTS / FRONTERES del domini import-calendari

## D1 — Òrfenes d'import

- **FET** `ImportSession.historia_xat` (`models_app/models.py:414`): **0 escriptura/lectura** al codi viu (només a la
  migració `0030_importsession.py`). → **ORFE.**
- **FET** `_POM_SYNONYMS` (`extraction_views.py:499-526`): **9 claus duplicades** ("last wins", les primeres mortes) —
  p.ex. `'waist position'` (`:501`/`:517`), `'hip position'` (`:502`/`:518`), `'collar width'` (`:509`/`:521`), etc.
  Comentaris `:515-516` ho documenten com a **intencionat (spec S19)**. Cridat des de `find_pom_master` (`:562`).

## D2 — Endpoints calendari òrfens de UI (DEUTE, no codi mort esborrable)

- **FET** `endpoints.js`: `jornada.get/update` (`:292/294`), `absencies.list/create/remove` (`:299/301/302`).
  *(El brief deia 256-268.)*
- **FET** cap pantalla `.jsx` els crida (`grep "jornada\."`/`"absencies\."` → 0). Mencions latents:
  `ModelSheet.jsx` (comentari) i `TaskAssignWizard.jsx` (TODO "llegir jornada de CompanyCalendar").
- ⚠️ **NO és codi mort esborrable** — els llegeix el motor de planificació backend (`/api/v1/plan/`). Anotar com a **deute de UI**.

## D3 — Migracions head per app (punt de partida)

| App | Última migració |
|---|---|
| models_app | `0043_delete_modelservei.py` |
| pom | `0026_itembasemeasurement_nom_fitxa.py` |
| fitting | `0015_fittingsession_finished_at_and_more.py` |
| tasks | `0028_modeltask_origen.py` |
| planning | `0002_technicianqueueorder.py` |

## D4 — Altres restes mortes del domini import

- **FET** `_create_pom_alert` (`extraction_views.py:44`): **0 cridadors → zombi** (vegeu §A5).
- **FET** `extract_images_from_pdf` (`extraction_service.py:234`): **0 cridadors → mort** (vegeu §A3).
- **FET** comentari obsolet `urls.py:47` ("Sprint 6 … models/extract-from-file/") + comentari inexacte `urls.py:64`
  (atribueix `extraction_service` al wizard nou) → **deute de documentació**, no codi.

---

## CRITERI D'ÈXIT — cobert

1. **G3:** contradicció resolta (el "vell d'import" ja està retirat; `extraction_service` = motor size-map viu, no import);
   abast exacte de retir lliure = `extract_images_from_pdf` + `_create_pom_alert`; **pur codi, cap migració**.
2. **Plantilla:** acotada — ja alineada amb 17/57/125; el treball real és confirmació + decisió POM-a-plantilla + jubilar seed obsolet; **frontera grading D-10/G6 marcada**.
3. **G7:** dues vies amb cost (backend ~zero blast radius vs frontend render compartit); forma N-vs-1 deixada al CTO.

**Caps OBERT pendents:** recompte/ús de `seed_pom_maps_to_items.py` (B3); forma de producte de la convocatòria (C3);
decisió POMs-a-plantilla (B5). Cap fet exigia executar codi/migracions (tot read-only).
