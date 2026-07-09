> ⚠️ SUPERADA 2026-07-07 — implementada (obligatoris mínims 3 + Watchpoint import, 8a906df/7fef5dc). Consulta només com a històric.

# DIAGNOSI — Flux d'import mínim + Watchpoint viu + Gate suau a POMS

**Protocol:** FASE B · READ-ONLY ABSOLUT · 0 codi · 0 push · branca `dev` (`/var/www/ftt-staging`).
**Data:** 2026-06-26.
**Mètode:** director + 5 investigadors (Explore) en paral·lel (àrees 1-5) + verificació directa de l'autor
dels fets càrrega (validació, matching, NOT NULL). Dades schema `fhort` en read; golden 162 no tocat.
**Llegenda:** `FET (fitxer:línia)` · 💡PROPOSTA (a validar) · OBERT (no determinable read-only).

**Objectiu:** portar els fets per construir el flux *"importa mínim → Watchpoint del que falta → gate suau a
POMS → completar al wizard de Model"*. Cap decisió de disseny es pren aquí.

---

## RESUM EXECUTIU (per dissenyar sense obrir cap fitxer)

1. **Import mínim (À1):** `commit_import` **JA POT** crear un Model amb només `nom+any+temporada`. El
   matching de talles és **condicional** (s'omet si no hi ha run); l'únic que bloqueja avui és la **llista
   `OBLIGATORIES`** (9 camps) validada en bucle. **Retoc = canviar 1 llista** (`bulk_import_service.py:20-21`),
   cap canvi profund a `commit_import`. Un `SizeFitting(tipus='Proto')` es crea **sempre** (buit si no hi ha sizing).
2. **Watchpoint (À2):** **ja pot néixer sense tasca** (`task` és `null=True`). Però **només desa text lliure**
   (`TextField`) — per desar *estructura* ("quins camps falten") **cal afegir un `JSONField` + migració**.
3. **Watchpoint viu/derivat (À3):** els 4 camps de config viuen tots al `Model` (nullable); **no existeix cap
   `config_completa`**. Els *signals d'ompliment* són els endpoints d'assignació (`create-wizard`,
   `update-step2`, bulk-commit, `confirmar-talla-base`, `generar-grading`). Es resoldria sol quan els 4 siguin no-nuls.
4. **Gate suau a POMS (À4):** els POMs s'obren via `open-task {code:'pom'}` → `MeasuresEntryPanel` →
   `materialitzar-poms`. El gate dur actual és a `materialize_poms_view` (rebutja si no hi ha `garment_type_item`).
   La config està **repartida** (ModelWizard blocs 2/3 + RuleSetCard); **no hi ha un sol lloc** que cobreixi els 4.
5. **Plantilla (À5):** ordre de fulls = Plantilla(1) · Instruccions(2) · ocults · _meta. Per Instruccions full 1 =
   `create_sheet('Instruccions', index=0)`. Validació **list-based** (fàcil relaxar a 3).
6. **Fronteres (À6):** el bulk **no assigna `grading_rule_set`** (queda NULL) → l'import mínim **no toca grading
   propagat** (D-10/G6) per construcció. El "document mana" és del **single-model** (ImportSession), camí
   **separat** del bulk.

---

# ÀREA 1 — `commit_import`: pot crear Model amb només nom+any+temporada?

**PREGUNTA:** ¿exigeix sizing/talles, o tolera mínim?

### FET — el que realment bloqueja és una LLISTA, no la lògica de creació
- `bulk_import_service.py:20-21` — `OBLIGATORIES = ['nom_prenda','familia','tipus','any','temporada','target',
  'construccio','run_talles','talla_base']` (9 camps).
- `bulk_import_service.py:210-212` — bucle `for col in OBLIGATORIES: if not g(col): errors.append(...camp obligatori)`.
  → **és l'únic** que força els 9. Relaxar la llista relaxa la validació (no hi ha checks hardcoded per camp obligatori).
- Els altres errors són **condicionals a presència**: `familia` (`:219` `if g('familia') and not fam`),
  `tipus` (`:225/230`), `target` (`:254`), `construccio` (`:261`) → **només peten si el camp ve i és invàlid**,
  no si ve buit i no és obligatori.

### FET — el matching de talles és CONDICIONAL (no bloqueja una fila sense talles)
- `bulk_import_service.py:266-275`:
  ```
  labels = _split_sizes(g('run_talles'))   # buit → []
  if target_codi and labels:               # ← sense run/target, S'OMET
      mr = match_size_system(...); size_system = mr.size_system
      if mr.error: errors.append(...)
  ```
  → sense `run_talles`, `match_size_system` **ni es crida**; `size_system=None`, **cap error**. El matching
  només bloqueja si run/talla_base **vénen però són invàlids** (`matching.py:55-125`).

### FET — la creació de Model no peta amb camps de config buits
- `_build_model` (`bulk_import_service.py:483-503`) passa `garment_type=r['garment_type']`,
  `garment_type_item=…`, `size_system=…`, `size_run_model=…`, `base_size_label=…` → **tots admeten None**
  (`models.py:146-167, 186-192, 264-271`).
- **NOT NULL reals del Model** (només aquests peten): `codi_intern` (`models.py:117`), `any` (`:136`),
  `temporada` (`:137`), `sequencial` (`:138`); `customer` el serveix sempre el context d'importació.
- `codi_intern` es genera a `commit_import` com `f"{customer.codi}-{season}{yy}-{seq}"` → depèn **només** de
  `(customer, any, temporada)` + seqüència (`reserve_sequence_range`), **no** de sizing ni nom.
- `SizeFitting(tipus='Proto')` es crea **SEMPRE** per cada Model (`bulk_import_service.py:451-456`,
  incondicional) → un model mínim té un Proto buit (sense `size_system`).
- `commit_import` només processa files `estat in ('OK','AVIS')` (`:380`); les `ERROR` se salten.

### FET — derivació família
- `familia` **NO** es deriva de `tipus` avui: `resolve_row` busca el camp `familia` a l'Excel (`:217`) i posa
  `garment_type=fam` (`:296`), **no** `item.garment_type`. (La taxonomia ho permetria —
  `GarmentTypeItem.garment_type`— però el codi no ho fa.)

### 💡 PROPOSTA (abast del retoc)
- **Mínim viable:** canviar `OBLIGATORIES` a `['nom_prenda','any','temporada']` (`:20-21`). Amb això, una fila
  sense família/tipus/target/construccio/run/talla_base **passa a OK** i `commit_import` crea el Model
  (config en None, Proto buit). Cap altre canvi de `commit_import` necessari.
- **Opcional (millora):** derivar `garment_type` de `garment_type_item` quan `familia` és buida però `tipus` ve
  (afegir a `resolve_row` ~:217). No imprescindible per al mínim.

---

# ÀREA 2 — Watchpoint: origen sistema sense tasca + estructura

**PREGUNTA:** ¿admet origen 'import/sistema' sense tasca, i pot desar QUINS camps falten com a dades?

### FET — camps reals del model `Watchpoint` (`models_app/models.py:807-834` + migr. `0042_watchpoint.py`)
| Camp | Tipus | Null? | Default / choices |
|---|---|---|---|
| `model` | FK→Model | NO | — |
| `task` | FK→ModelTask | **SÍ (nullable)** | — |
| `text` | TextField | NO | — |
| `estat` | CharField | NO | `'open'` · choices `open`/`resolved` |
| `created_by` | FK→UserProfile | SÍ | — |
| `created_at` | DateTimeField | NO | `auto_now_add` |
| `resolved_by` / `resolved_at` | FK / DateTime | SÍ | — |
| `resolution_note` | TextField | — | `''` |

- **FET (a)** pot **néixer SENSE tasca**: `task` és `null=True, blank=True` → el model i el front ja ho
  suporten (`WatchpointDrawer.jsx` crea amb `taskId=null`). **No cal cap canvi** per a un origen sistema/import.
- **FET (b)** **NO** pot desar estructura avui: l'únic contingut és `text` (TextField). **No hi ha `JSONField`**
  ni cap camp de dades. El serializer (`serializers.py:145-158`) exposa write només `model/task/text`.
  → per "quins camps falten" com a dades estructurades **cal afegir** p.ex. `dades = JSONField(null=True)` + migració + serializer.
- **FET** **no hi ha camp `origen`/`tipus`** a `Watchpoint` (a diferència de `POMAlert`). Si es vol distingir
  "import" d'altres, caldria un camp nou (o inferir-ho de `task IS NULL` + el `JSONField`).

### FET — endpoints i render
- `WatchpointViewSet` (`models_app/views.py:143-174`): `list` (filtra per `model`/`estat`/`task`, `:148`),
  `create` (`:152`), `resolve` (`:155-164`), `reopen` (`:166-174`). Rutes a `models_app/urls.py`
  (`/api/v1/watchpoints/…/resolve|reopen/`).
- `WatchpointsPanel.jsx` (muntat dins `DashboardTab.jsx:282`): renderitza `w.text` (pre-wrap, ratllat si
  resolved), `w.estat` (icona flag/check), `w.created_by_nom`/`created_at`/`task_type_code`/`resolved_by_nom`.
  → **render de TEXT pla**, no per clau. Per "render per clau al lector" caldria llegir el `JSONField` nou.

### 💡 PROPOSTA (reusar vs variant) — cost
- **Reusar `Watchpoint`** amb `task=NULL` + afegir **`dades JSONField`** (i opcionalment `tipus='IMPORT'`):
  cost = 1 camp + 1 migració + serializer + render condicional al panel. **Recomanat** (no cal entitat nova;
  el panel persistent i resolve/reopen ja existeixen). La variant (entitat pròpia) duplicaria infra sense guany.

---

# ÀREA 3 — Watchpoint VIU (es va buidant) + resolució derivada

**PREGUNTA:** ¿on viu "aquest camp ja té valor", per derivar què falta i resoldre sol?

### FET — els 4 camps de config viuen tots al `Model` (nullable)
| Camp config | On viu | Fitxer:línia | "Ple" quan |
|---|---|---|---|
| garment_type / item | `Model.garment_type` / `Model.garment_type_item` | `models.py:146-167` | FK IS NOT NULL (l'item força/deriva el garment_type) |
| Talla base | `Model.base_size_label` (+ `BaseMeasurement.base_value_cm`) | `models.py:268-271` / `:428-484` | `base_size_label` no buit (mesures: `BaseMeasurement.is_active` amb valor) |
| Run + sistema | `Model.size_run_model` + `Model.size_system` (FK) | `models.py:264-267, 186-192` | ambdós no nuls |
| Ruleset | `Model.grading_rule_set` (FK) | `models.py:193-199` | FK IS NOT NULL |

- **FET** **no existeix** cap camp/propietat `config_completa` ni càlcul de completesa (grep `config/incomplet/completa` → res). Les úniques comprovacions de prerequisits són **en arribada** d'endpoints (sota).

### FET — signals d'ompliment (on el Watchpoint "es buidaria" i recalcularia)
- Assignen els 4: `create-wizard` (`views.py:298`, helper `_resolve_garment_def` `:249-293`),
  `update-step2` (`views.py:451`, reusa el helper), bulk-commit (`bulk_import_service.py`).
- Talla base: `guardar-talla-base` (`pom/wizard_views.py:153`), `confirmar-talla-base` (`:230`, tanca base i
  pot disparar grading si els 3 hi són).
- Grading: `generar-grading` (`views.py:1343`, prerequisit `grading_rule_set` + `size_run_model` + `base_size_label`).
- **FET** **no hi ha signal de "buidatge"** avui (els camps s'omplen, mai es netegen) → el Watchpoint viu
  s'hauria de **recalcular en cada ompliment** (post_save del Model / dels endpoints) i **resoldre's** quan els
  4 passin a no-nuls. **OBERT:** no existeix `signals.py` per a Model; on enganxar-ho (post_save vs dins cada endpoint) és decisió de disseny.

### 💡 PROPOSTA (mecanisme, on s'enganxa)
- Una funció `model_config_missing(model) -> list[str]` (font única, reusable per Watchpoint **i** gate À4) que
  retorni quins dels 4 són nuls. Recalcular el Watchpoint (actualitzar `dades` + `text`, o resoldre'l) en el
  `post_save` del Model o al final dels endpoints d'assignació. Resolt quan la llista queda buida.

---

# ÀREA 4 — Gate SUAU a POMS (avisa + ofereix wizard, persistent, no bloqueja)

**PREGUNTA:** on enganxar el gate suau i quina superfície completa els 4 camps.

### FET — obertura de POMs avui
- Front: botó "Editar mides" / `?mode=entry` → `enterEdit('Mesures','pom')` (`ModelSheet.jsx:197-211`) →
  `openTask` POST `/api/v1/models/<id>/open-task/ {code:'pom'}` (`tasks/views_b.py:469-522`: crea ModelTask
  idempotent + transició InProgress) → es manté a la tab **Mesures** → `MeasuresEntryPanel.jsx` → POST
  `/api/v1/models/<id>/materialitzar-poms/` (`models_app/views.py:520-593`).
- **FET — gate dur actual:** `materialize_poms_view` **rebutja si no hi ha `garment_type_item`**
  (`views.py:~536-538`, warning + resultat buit). És l'únic prerequisit comprovat per obrir POMs.

### FET — punt natural per al gate suau
- Backend: dins `open_model_task_view` (`tasks/views_b.py:469-522`), després de resoldre la tasca i abans/amb
  la resposta, afegir `missing_config: [...]` (reusant la font de l'À3). El front (`enterEdit`,
  `ModelSheet.jsx:197-211`) ja rep la resposta → mostraria avís + oferta de wizard. (Punt **OBERT**, candidat.)

### FET — superfícies de config (repartides, cap cobreix els 4)
| Superfície | Camps que cobreix | Fitxer:línia |
|---|---|---|
| ModelWizard bloc 2 (Garment) | `garment_type_item` | `ModelWizard.jsx:52-54, 173` |
| ModelWizard bloc 3 (Talles) | `size_run_model` + `base_size_label` | `ModelWizard.jsx:58-65, 115-117` |
| RuleSetCard (tab Resum) | `grading_rule_set` | `components/model/RuleSetCard.jsx:50-73` |
| TabSummary | mostra els 4 (read-only) | `ModelSheet.jsx:770-900` |

→ **FET:** garment_item i talles viuen al **ModelWizard** (ruta `/models/:id/editar`); el ruleset a
**RuleSetCard** (Resum). **No hi ha un sol lloc** que completi els 4. Per fer-ho caldria unificar (p.ex.
estendre RuleSetCard o un pas únic del wizard) — abast de cobertura, no disseny.

### FET — banners/avisos persistents existents al ModelSheet
- `Feedback` (transitori, `ModelSheet.jsx:106,338`), `Error div` (`:366-372`), **`WatchpointsPanel`**
  (persistent, dins `DashboardTab.jsx:282`), alertes de TabSummary (`ModelSheet.jsx:1460-1501`).

### 💡 PROPOSTA
- L'avís suau pot **reutilitzar el WatchpointsPanel** (ja persistent, no ignorable, amb resolve) per mostrar
  el Watchpoint d'import viu (À2/À3), i/o un banner a la tab Mesures abans del `MeasuresEntryPanel`. La
  comprovació "config incompleta" ha de venir de la **mateixa font** que el Watchpoint (`model_config_missing`),
  **no duplicar-la**. El gate és **suau**: avisa i ofereix el wizard, no rebutja (a diferència del check dur de `materialize_poms_view`).

---

# ÀREA 5 — Plantilla Excel (Instruccions full 1 + 3 capes)

**PREGUNTA:** què cal per Instruccions full 1 i relaxar els 9 obligatoris a 3.

### FET — ordre real dels fulls (`generate_template_bytes`, `bulk_import_service.py:97-162`)
1. **Plantilla** (full actiu, `:108-111`) ← full 1 actual · 2. **Instruccions** (`create_sheet`, `:114`) ·
3. ocults `_families/_items/_targets/_construccions/_seasons/_years` (`:124-139`) · 4. `_meta` (`:142-145`).
- **Per Instruccions full 1:** `wb.create_sheet('Instruccions', index=0)` (o `wb.move_sheet('Instruccions', offset=-1)` després). Canvi localitzat a `:108-121`.

### FET — validació que bloqueja (list-based, fàcil de relaxar)
- `resolve_row:210-212` (bucle sobre `OBLIGATORIES`). `validate_rows` posa `estat='ERROR'` si hi ha errors
  (`:~350`). `upload_view` (`bulk_import_views.py:79`) **desa totes** les files (no rebuig global);
  `commit_import:380` només committeja `OK/AVIS`. → relaxar = canviar `OBLIGATORIES` (`:20-21`); **cap check hardcoded** addicional per als obligatoris.

### FET — classificació de les 15 columnes en 3 capes (segons què alimenta cada una a `resolve_row`)
| Capa | Columnes |
|---|---|
| **OBLIGATORI mínim** | `nom_prenda`, `any`, `temporada` (generen `codi_intern` + dedup; NOT NULL al Model) |
| **OPCIONAL informatiu** | `familia`, `tipus`, `codi_client`, `col·leccio`, `color_referencia` (FK/descriptius; no bloquegen) |
| **OPCIONAL configuració** | `target`, `construccio`, `run_talles`, `talla_base` (sizing/matching condicional), `es_conjunt`, `referencia_conjunt`, `piece_number` (lògica de conjunts) |

> Nota: `tipus`/`familia` són "informatius" en el sentit que no bloquegen el mínim, però alimenten la
> taxonomia (garment_type_item) que després el gate de POMS (À4) demana — per això són els primers candidats
> a completar post-import. La capa exacta (informatiu vs config) per a `tipus` és decisió de producte.

---

# ÀREA 6 — Fronteres (no creuar)

- **FET — grading propagat (D-10/G6):** el **bulk import NO assigna `grading_rule_set`** (queda NULL; l'À3
  confirma que el ruleset s'assigna després via wizard/update-step2). Per tant l'import mínim **no toca el
  grading propagat** per construcció. Si en el futur s'afegís ruleset a la plantilla, hauria de **RETENIR la
  regla** (llei de sobirania de la regla), **no propagar** — frontera a marcar, no creuar en aquesta feina.
- **FET — "el document mana":** la derivació de POMs des del document és del **single-model** (wizard
  `ImportSession`, `import_session_*`, camí `ImportWizard.jsx`). Aquesta feina és sobre el **BULK** (plantilla
  N models, `bulk_import_*`). Són **camins de codi separats** (no comparteixen `commit_import`); no es barregen.

---

## CRITERI D'ÈXIT — cobert
Amb aquest doc es pot dissenyar: (a) el retoc de `commit_import` per acceptar mínim = **relaxar `OBLIGATORIES`
a 3** (`:20-21`), matching ja condicional, Proto ja incondicional; (b) el Watchpoint d'import = **reusar
Watchpoint** (`task=NULL` ja OK) **+ `JSONField`** per estructura + font `model_config_missing`; (c) el gate
suau a POMS = enganxar `missing_config` a `open-task`/`MeasuresEntryPanel`, avís via WatchpointsPanel/banner,
wizard destí repartit (ModelWizard 2/3 + RuleSetCard) — **falta unificar-los**; (d) plantilla = Instruccions
`index=0` + 3 capes amb `OBLIGATORIES` relaxat.

**OBERT principal:** on viu el signal de recàlcul del Watchpoint (post_save Model vs dins endpoints; no hi ha
`signals.py`); i si es vol un únic lloc que completi els 4 camps (avui repartits). Cap fet ha exigit executar
codi/migracions.
