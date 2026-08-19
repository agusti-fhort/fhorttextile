# DIAGNOSI — Multi-peça: cas LOS-SS27-0834 DALIA

Data: 2026-07-27 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`

**Abast.** Cas real a PROD: un xlsx amb 3 peces (DRESS / KNICKERS / HEADIADEM) que el wizard
d'import fusiona en un sol model amb les taules de POMs seguides. Es diagnostica què hi ha
CONSTRUÏT per a multi-peça (Q1-Q4) abans de decidir una convenció d'arrel per peça
(`01.` / `02.` / `03.`), i es documenta un bug confirmat del pas 2 (Q5).

**Convenció.** Cada afirmació porta `fitxer:línia` o sortida literal. **"NO EXISTEIX" =
confirmat absent al codi**, no especulat. **Cap recomanació d'arquitectura: la decisió és
Patró C.** Cap escriptura de codi, BD, config ni servei.

**Nota de dades.** A staging, `LOS-SS27-0834` és **AMARANTA**, no DALIA (PROD difereix). El
que sí que hi coincideix és l'escenari del bug: `base_size_label='00/01'`,
`size_run='00/01·01/03·03/06·06/09·09/12'`.

**Diagnosi prèvia vigent que cobreix part de Q1-Q2:**
[`DIAGNOSI_COMPONENTS_MULTIPLES_MESURES.md`](DIAGNOSI_COMPONENTS_MULTIPLES_MESURES.md)
(21/07/2026). Aquí no se'n repeteix el cens; s'hi remet i s'hi afegeix el que és nou.

---

## Resum executiu

1. **`GarmentSet` és un embrió complet però mai encès.** Model, migració i FKs aplicats als
   dos esquemes; el backend el crea per dos camins; el fitting el sap consumir. Però hi ha
   **0 files a `fhort` i a `los`**, i **cap referència al frontend** (grep `garment_set` /
   `piece_number` a `frontend/src` → **0 hits**).

2. **NO EXISTEIX cap dimensió de secció/peça a les mesures.** I el bloqueig no és "falta un
   camp": és la clau `BaseMeasurement.unique_together = [('model','pom')]`
   (`models_app/models.py:619`) — **un POM no pot existir dues vegades al mateix model**.

3. **El cas bikini CRUZADO mai es va implementar ni importar.** El sufix de secció es va
   declarar com a decisió ajornada (`INFORME_FASE1_TANCAMENT_LOSAN.md:58`) i prou.
   `LOS-SS27-0322 CRUZADO` existeix amb **0 BaseMeasurement**.

4. **La secció d'origen es perd al punt d'extracció, pels DOS camins.** El parser ràpid salta
   les files de secció sense llegir-ne el text (`extraction_views.py:385-386`) i el dict de
   POM no té cap clau de secció (`:402-409`); el prompt de la IA no demana secció enlloc
   (`extraction_prompt.py:127-131`). **La convenció d'arrel no es pot automatitzar sense
   tocar l'extractor.**

5. **Cap regla comercial compta peces.** La meritació és **per Model** i es dispara amb la
   PRIMERA `ModelTask` que entra a `InProgress` (`tasks/services_c.py:150-181`) — mai en
   desar un model. Està **activa** (33 events), però **no s'activaria sola** en guardar un
   model de 3 peces.

6. **Bug del pas 2 confirmat i localitzat**: asimetria entre `:358` (canonicalitza per trobar
   la columna) i `:419` (compara cru per comptar files).

---

## Q1 — `GarmentSet`: estat real

### Model i esquema

`models_app/models.py:43-73`. Camps: `codi_base` (unique), `nom_comercial`, `num_pieces`
(*"Immutable després de la creació"*), `created_at`. El docstring (`:44-58`) el separa
explícitament de `pom.GarmentGroup`: *"GarmentGroup is a TAXONOMY... GarmentSet is a CONCRETE
product instance"*.

Pertinença **explícita, mai derivada del codi**: `Model.garment_set` (FK `SET_NULL`,
`models_app/models.py:194-200`) + `Model.piece_number` (`:201`). El comentari `:190-192`:
*"Membership in a commercial set is explicit (FK + piece_number), not parsed from
codi_intern."*

**Migració:** `models_app/0019_garmentset_model_piece_number_model_garment_set`, **aplicada**.
Taula `models_app_garmentset` present a `fhort` i `los`.

### Dades vives

```
fhort: GarmentSet=0 · Models amb garment_set=0 · (Models totals=1056)
los:   GarmentSet=0 · Models amb garment_set=0 · (Models totals=51)
```

**Zero conjunts creats mai.**

### Consumidors

| Capa | Estat | Ancoratge |
|---|---|---|
| Creació · wizard API | **EXISTEIX** | `models_app/views.py:824-870` (`create_model_wizard`, `POST models/create-wizard/`, `urls.py:203`) |
| Creació · import massiu | **EXISTEIX** | `bulk_import_service.py:511-517` |
| Numeració | **EXISTEIX** | `views.py:773-787` — el `codi_base` d'un set consumeix número, les peces són `-01`/`-02` |
| Fitting (sessió sobre un set) | **EXISTEIX** | `fitting/models.py:224-236` (target = GarmentSet XOR Model); `fitting/services.py:154-155`; `fitting/serializers.py:69-71`, `:117`, `:151`, `:174` |
| Serializer de `Model` | **NO EXPOSA** | 0 hits de `garment_set` a `models_app/serializers*.py` |
| **Frontend** | **NO EXISTEIX** | grep `garment_set`/`piece_number` a `frontend/src` → **0 hits** |

### Hi ha CAP camí d'UI que en creï un?

**Un de sol, i indirecte: l'import massiu.** El backend accepta `is_multipiece`/`num_pieces` a
`create_model_wizard` (`views.py:711`, `:751-759`), però **el frontend no els envia mai** (0
hits). El `ModelWizard` no té casella de multi-peça.

L'únic camí real és l'Excel de l'import massiu, amb tres columnes que **omple l'operador a mà**:
`es_conjunt`, `referencia_conjunt`, `piece_number` (`bulk_import_service.py:18`, instruccions a
`:141` i `:147`: *"Conjunts (combo): omple 'referencia_conjunt' igual a totes les peces i
'piece_number' (1,2,...)"*). Validació a `:311-324`. **Cap detecció automàtica: la declara qui
escriu l'Excel.**

### Veredicte d'estat

**Embrió cablejat, no mort-viu.** A diferència del patró `Model.estat`, aquí no hi ha codi
enganyós ni guardes falses: el domini és coherent i el fitting el sap tractar. El que falta és
**superfície d'UI i ús**: 0 files, 0 hits al frontend. `DECISIONS.md:404` ja el declarava com a
via (*"Combo/multipeça: GarmentSet, 2 graelles per peça identificades (presa simultània) → peça
pròpia"*), i `DIAGNOSI_COMPONENTS_MULTIPLES_MESURES.md:170` (fila 6) el marca *"EXISTEIX — és la
sortida barata"*.

---

## Q2 — Estructura de peça/secció a les mesures

### Cens de camps (introspecció ORM, no grep)

| Model | Camps | Secció/peça/grup/prefix |
|---|---|---|
| `BaseMeasurement` | `base_value_cm, created_at, created_by, id, is_active, is_key, model, nom_fitxa, notes, ordre, origen, pom, tolerancia_minus, tolerancia_plus, updated_at` | **CAP** |
| `POMMaster` | `actiu, categoria, codi_client, id, nom_client, notes, origen_import, pendent_revisio, pom_global, tolerancia_default_*` | **CAP** |
| `GarmentPOMMap` | `garment_type_item, id, is_key, nivell, obligatori, ordre, pendent_revisio, pom` | **CAP** |

**Cap JSONField annex** a `BaseMeasurement` ni a `POMMaster` (introspecció: `JSONFields: cap`).
L'únic ordre és `ordre` (enter pla, `models_app/models.py:614`).

### El bloqueig real no és el camp que falta: és la clau

`models_app/models.py:619` → `unique_together = [('model', 'pom')]`.

Un model **no pot tenir el mateix POM dues vegades**. Per al cas DALIA: si DRESS i KNICKERS
comparteixen qualsevol POM (cintura, llarg…), la segona fila **no és ambigua — és
ininsertable**. `DIAGNOSI_COMPONENTS_MULTIPLES_MESURES.md` (resum §2-§3) ja ho havia establert i
hi afegeix que la clau `pom` sense discriminant travessa **5 taules més**: `SizeCheckLine`
(`models_app/models.py:924`), `GradedSpec` (`fitting/models.py:209`), `PieceFittingLine`
(`fitting/models.py:374`), `ModelGradingRule` (`models_app/models.py:746`),
`ModelGradingOverride` (`:689`).

### El cas bikini CRUZADO: decisió, **mai implementació**

`docs/diagnosis/INFORME_FASE1_TANCAMENT_LOSAN.md:58`, dins la llista de **pendents NO sembrats**:

> `M.8 (PANTIE)` POM DUPLICAT TOP/PANTIE (mecanisme de sufix de secció → **decisió a fase
> mesures**).

Es va **detectar el xoc i ajornar el mecanisme**. Verificació que no es va materialitzar enlloc:

- POMMaster amb sufix de secció al codi (`(`, `PANTIE`, `TOP)`, `_TOP`, `_PANT`): **0**.
- BaseMeasurement amb secció a `nom_fitxa`: **0** (sobre 647 files a `fhort`).
- `LOS-SS27-0322 CRUZADO`: existeix com a Model, **`base_measurements` = 0**.

**No s'ha importat enlloc.** Era decisió sense implementació, i segueix sense-la.

---

## Q3 — El detector multi-model del wizard

### On surt el missatge

`frontend/src/i18n/ca.json:3423`:
`"multimodel_warn": "El document conté {{count}} models detectats ({{names}}). La importació
tractarà un sol model."`

Alimentat per `num_models` / `model_detectat` de la resposta de cribratge
(`extraction_views.py:671-676`).

### Com es detecta

Pas de **cribratge** amb IA barata: `CRIBRATGE_PROMPT` (`extraction_views.py:96-122`) demana
`num_models` + `models_detectats[{nom, pagina, descripcio}]`, amb la regla explícita
*"num_models counts distinct styles/patterns. Two patterns on the same page = 2"* (`:118`).

Es desa a `session.model_detectat` (`:653`) i condiciona `pot_continuar`
(`:668-671`): pel camí IA exigeix `num_models == 1`; **pel camí determinista
(`not cribratge_ia`) `pot_continuar` és cert sempre**, independentment de quants models s'hagin
detectat.

### Què fa exactament amb les seccions

**Les fusiona.** No les descarta ni té branca alternativa.

**Camí determinista (parser ràpid).** `extraction_views.py:367-386`:

```
# ── 6. Files de dades. Tres menes de fila que NO són POMs:
#   · SECCIÓ ('Bodice:', 'Cord:') → codi buit + descripció plena. SALTAR, mai `break`
```

`:384-386` → `if not codi: continue`. La fila de secció té **codi buit i descripció plena**: es
salta per la condició del codi i **el text de la descripció no s'arriba a llegir mai**. Totes
les files de POM de totes les seccions cauen a la MATEIXA llista `poms` (`:402`), seguides. És
literalment el comportament observat a DALIA.

Hi ha test que ho fixa com a contracte: `test_parser_excel.py:171-172`, *"Aquesta fitxa té TRES
seccions ('Bodice:', 'CF Sequins piece:', 'Cord:')"* → es salten.

**Camí IA.** `extraction_prompt.py:127-131`, esquema de fila de la taula de mesures:
`client_code`, `description`, `values`, `tol_minus`, `tol_plus`. **Cap camp de secció ni de
peça.** Grep de `section|piece|sub-garment` al prompt sencer: només `pattern_piece` com a tipus
de contingut de PÀGINA (`:161`), sense relació amb l'agrupació de mesures.

### Guarda la secció d'origen de cada POM?

**No. Es perd al punt d'extracció, pels dos camins.**

- Parser ràpid: el dict de POM és
  `{'codi_fitxa','descripcio','dim','values','tol_minus','tol_plus'}`
  (`extraction_views.py:402-409`). **Cap clau de secció.**
- IA: l'esquema de sortida no en té cap (`extraction_prompt.py:127-131`).

**Conseqüència directa per a la decisió pendent:** la convenció d'arrel per peça
(`01.` / `02.` / `03.`) **no es pot automatitzar sense tocar l'extractor**, perquè avui no hi ha
d'on treure la peça: al parser ràpid el text de la secció ni tan sols es llegeix.

### 🔴 Troballa addicional no demanada: el parser només llegeix UN full

`extraction_views.py:272` obre `for ws in wb.worksheets:` i `:435` fa `return poms, …` **amb
indentació 12, dins del bucle**. El parser **retorna al primer full que passa la porta**
(`:419-422`) i **no mira els fulls següents**.

Si un document multi-peça posa cada peça en un full separat (en comptes de seccions dins d'un
full), els fulls 2..N es perden **sencers i sense avís de contingut** — l'avís que arriba és el
genèric de multi-model del cribratge, no un "hi havia 3 fulls i n'he llegit 1".

*(Anotat, no verificat contra el fitxer real de DALIA: no en tinc còpia a staging.)*

---

## Q4 — La regla comercial de multi-peça

### La regla: meritació per Model, no per peça

**Disparador únic a runtime:** `tasks/services_c.py:150-181`, dins la transició d'una
`ModelTask` a `InProgress`:

- `:162-164` — `Model.objects.filter(pk=task.model_id, consumption_started_at__isnull=True)
  .update(consumption_started_at=now)`. **Guard d'idempotència: només la primera vegada.**
- `:166-172` — crea **un** `ConsumptionRecord` per model.
- `:174-181` — emet `model_consumption_started` → `backoffice/receivers.py:7-23` escriu un
  `ModelConsumptionEvent` a `public` (`get_or_create` per `opaque_ref`).

**Segon punt d'escriptura, manual:** `backoffice/management/commands/reconcile_consumption.py:141`,
que repesca forats amb el criteri *"models amb activitat real i sense marca de meritació"*
(`:76-82`: `model_tasks__status__in=['InProgress','Done','Paused']`).

**No n'hi ha cap més**: grep de `ConsumptionRecord.objects.create` i `consumption_started_at` →
només aquests dos.

### Facturació: la unitat és el Model

`backoffice/recurring_service.py:87` compta events del període (`.count()`) i `:104` factura
l'**excés** sobre la quota (`quantitat=Decimal(str(exces))`). La unitat facturable és el
`ModelConsumptionEvent` = **el Model**.

### Estat: **ACTIVA**, no aparcada

```
ModelConsumptionEvent (public): 33
fhort: ConsumptionRecord=28 · Models amb consumption_started_at=28
los:   ConsumptionRecord=0
```

Grep de `billing.?park|parked|facturació aparcada` → **cap coincidència**. **No hi ha cap
"billing parked" al codi**: la meritació funciona i té dades.

### Cap regla compta "peces"

- `num_pieces` només té **un consumidor** fora de la creació: `fitting/services.py:155`
  (`n = GarmentSet.num_pieces or 1`), que és la porta de segellat de la sessió de fitting —
  **món tècnic, no comercial**.
- Grep `piece` a `commerce/` i `backoffice/`: només `commerce/0002_seed_units.py:6`
  `('piece','Piece')`, que és una **unitat de mesura d'article** (ut), sense relació.
- **Packs del manifest SS27: NO EXISTEIXEN.** L'únic `manifest.json`
  (`pom/seed_data/losan_package/manifest.json`) té les claus
  `package, source_schema, commit, customer_codi, design, gate_qa_targets, layers` — cap noció
  de pack comercial.

### Resposta a la pregunta exacta del brief

**Confirmat: guardar un model de 3 peces NO activaria res.** La meritació no s'enganxa a
`Model.save()` ni a la creació: exigeix una `ModelTask` a `InProgress`
(`tasks/services_c.py:150`) o l'execució manual de `reconcile_consumption`, que a més també
exigeix activitat de tasca.

**Conseqüència de la decisió pendent, com a FET (no com a recomanació):** avui la unitat
meritada és el Model. Fusionar 3 peces en 1 model merita **1**; separar-les en 3 Models d'un
`GarmentSet` merita **3** (el guard d'idempotència és per `pk` de Model, i cada peça és un Model
propi). La convenció d'arrel té, doncs, efecte de facturació. **Quin dels dos és el correcte és
decisió Patró C: aquesta diagnosi no s'hi pronuncia.**

---

## Q5 — BUG CONFIRMAT: la talla base del pas 2 contradiu l'aparellament del pas 1

**Símptoma.** Pas 1 aparella ★ `0M-1M` (document) ⟷ `00/01` (model). Pas 2 mostra
"talla base: 3M-6M" i l'extracció ha caigut a IA.

### Punt 1 — el lookup del parser ràpid: una asimetria

`base_hint` entra com **l'etiqueta del MODEL**, no la del document:
`extraction_views.py:505` i `:1266` → `base_hint=model.base_size_label` (a staging, `'00/01'`).

`:354` → `base_label = (sample_size or base_hint or '').strip()`. Si el document no porta fila
`SAMPLE SIZE`, **mana `base_hint`** → `base_label = '00/01'`.

Aleshores el fitxer fa **dues coses diferents amb la mateixa variable**:

```
 358          base_ci = next((ci for ci, lbl in size_cols
 359                          if canonical_size_label(lbl) == canon), None)     ← CANONICALITZA
...
 419          amb_base = sum(1 for p in poms if base_label in p['values'])      ← COMPARA CRU
```

- `:357-359` **canonicalitza les dues bandes** i troba la columna correctament. Verificat:
  `canonical_size_label('0M-1M') == canonical_size_label('00/01') == '0/1'` → **True**. Per tant
  **l'abdicació de `:360-363` NO es dispara**.
- Com que la branca `else` de `:364-365` (l'única que reassigna `base_label` a l'etiqueta del
  document) **no s'executa**, `base_label` es queda com `'00/01'`.
- `:419` compara `base_label in p['values']` **per igualtat literal de cadena**. I `values`
  està indexat per l'etiqueta **CRUA del document** (`:394` → `values[lbl] = nv`, amb `lbl` de
  `size_cols`). Així: `'00/01' in {'0M-1M': …}` → **False a cada fila** → `amb_base = 0`.
- `:420-422` → `0 < _MIN_FILES_ENTESA` (**3**) → `motiu` + `continue` → **el parser abdica i cau
  a la IA**, exactament el símptoma reportat.

**L'aparellament del pas 1 no hi participa en cap moment**: el parser no el consulta.

### Punt 2 — d'on surt la "talla base" del banner IA

Del **document**, mai del model ni de l'aparellament:

- `extraction_views.py:1473` → `extracted = safe_json_parse(raw)` (JSON cru de Claude).
- `:1544` → `'base_size': extracted.get('base_size')` a la resposta del pas 2.
- El prompt li demana que la identifiqui **del document**:
  `extraction_prompt.py:125` (*"SIZES AND BASE SIZE — extract all size labels and identify
  base_size"*), exemple de sortida `"base_size": "S"` (`:198`).

I **la injecció de context que evitaria això no s'usa en aquest camí**: existeix
`build_extraction_prompt(wizard_context)` (`extraction_prompt.py:19-55`), que injecta
`- Base size: {ctx base_size}` (`:46`) i *"Identify the base size values for size: …"* (`:53`).
Però l'import de fitxa fa servir el prompt **nu**: `extraction_views.py:1390` importa
`TECH_SHEET_EXTRACTION_PROMPT` i `:1445-1446` el passa tal qual, sense `ctx`. L'única
consumidora de la versió amb context és una superfície diferent:
`pom/size_map_views.py:430` (`extract_from_file` → `extraction_service.py:144`).

### El wizard té TRES nocions de talla base alhora

| Pas | Etiqueta que fa servir | Ancoratge |
|---|---|---|
| 1 · aparellament | document ⟷ model (★) | taula d'aparellament |
| 2 · banner IA | **document** (`'3M-6M'`) | `extraction_views.py:1544` ← `:1473` |
| Confirm | **model** (`'00/01'`), mai document | `:1967-1970` — comentari literal: *"base_size = etiqueta tenant del model (mai document)"* |

I al confirm hi ha ja una guarda que preveu el xoc: `:1993-1999` emet
`{'tipus': 'base_size_absent'}` quan l'etiqueta del model no és entre les etiquetes extretes.

**Els dos punts demanats:** lookup del parser ràpid = `extraction_views.py:419` (amb origen a
`:354` ← `:505`/`:1266`); talla base del banner IA = `extraction_views.py:1544` ← `:1473`,
esquema a `extraction_prompt.py:125,198`. **Només diagnosi: no s'ha tocat res.**

---

## TAULA FINAL

| # | Peça | Estat | Ancoratge |
|---|---|---|---|
| 1 | `GarmentSet` model + migració | **EXISTEIX, aplicada** | `models_app/models.py:43`; `0019_…` |
| 2 | `Model.garment_set` + `piece_number` | **EXISTEIX** | `models_app/models.py:194-201` |
| 3 | Files de `GarmentSet` | **0 a fhort i los** | SELECT |
| 4 | Creació via API wizard | **EXISTEIX** | `views.py:824-870` |
| 5 | Creació via import massiu (Excel manual) | **EXISTEIX** | `bulk_import_service.py:511-517`, `:18` |
| 6 | Frontend de multi-peça | **NO EXISTEIX** | 0 hits a `frontend/src` |
| 7 | Fitting sobre un set | **EXISTEIX** | `fitting/models.py:224-236`; `services.py:154` |
| 8 | Camp de secció a les mesures | **NO EXISTEIX** | introspecció ORM |
| 9 | Clau `('model','pom')` | **EXISTEIX i bloqueja** | `models_app/models.py:619` |
| 10 | Sufix de secció bikini TOP/PANTIE | **DECISIÓ AJORNADA, mai implementada** | `INFORME_FASE1_TANCAMENT_LOSAN.md:58`; CRUZADO amb 0 BM |
| 11 | Detector multi-model | **EXISTEIX (cribratge IA)** | `extraction_views.py:96-122`, `:641-676` |
| 12 | Tractament de seccions | **FUSIONA** | `extraction_views.py:384-386`, `:402` |
| 13 | Branca no cablejada per separar seccions | **NO EXISTEIX** | — |
| 14 | Secció d'origen del POM | **ES PERD a l'extracció** | `:402-409`; `extraction_prompt.py:127-131` |
| 15 | Parser llegeix tots els fulls | **NO — només el primer que passa** | `:272` bucle, `:435` return dins |
| 16 | Meritació per peça | **NO EXISTEIX** (és per Model) | `tasks/services_c.py:162-172` |
| 17 | Meritació activa | **SÍ** (33 events) | SELECT; cap "billing parked" al codi |
| 18 | Es dispara en desar un model | **NO** (cal `ModelTask`→InProgress) | `tasks/services_c.py:150` |
| 19 | Packs del manifest SS27 | **NO EXISTEIXEN** | `manifest.json` (7 claus, cap de pack) |
| 20 | Validació que compti peces | **NO EXISTEIX** al món comercial | `num_pieces` només a `fitting/services.py:155` |
| 21 | Bug talla base · parser ràpid | **CONFIRMAT** | `extraction_views.py:419` vs `:358` |
| 22 | Bug talla base · banner IA | **CONFIRMAT** | `:1544` ← `:1473`; ctx no injectat (`:1445`) |

---

## Límits d'aquesta diagnosi

- **No tinc el xlsx de DALIA.** El comportament del parser sobre aquell fitxer concret
  (seccions dins d'un full vs. un full per peça) està **inferit del codi**, no executat sobre
  els bytes reals. La troballa #15 (un sol full) és per tant una **hipòtesi de lectura de codi**
  per a aquell cas, tot i que el codi en si és inequívoc.
- **`LOS-SS27-0834` a staging és AMARANTA**, no DALIA: PROD i staging divergeixen. Els valors
  citats (`base_size_label='00/01'`) són de staging.
- **No he executat l'import** ni cap crida a la IA: hauria escrit sessió i consumit tokens.
- Q5 documenta **on** falla i **per què**; no s'ha provat cap correcció ni se'n proposa cap.
