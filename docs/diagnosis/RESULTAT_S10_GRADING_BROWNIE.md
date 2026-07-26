# RESULTAT — S10 · VALIDACIÓ DEL NODE GRADING AMB DADES REALS DE CLIENT (BROWNIE)

> **Data:** 2026-07-16 · **Sprint S10 (ZERO codi)** · staging `/var/www/ftt-staging`, branca `dev`
> **Naturalesa:** cap commit de codi, cap migració, cap restart. Tot són dades (shell ORM) +
> crides als endpoints reals (curl `-H "Host: staging.fhorttextile.tech"`) + verificació.
> **Base de fets:** `docs/diagnosis/DIAGNOSI_S10_GRADING_BROWNIE.md`.
> **Entorn:** tenant schema `fhort` (id=2), PG `127.0.0.1:5433` `ftt_staging`, PG server **18.4**,
> venv `backend/venv/bin/python`, gunicorn `127.0.0.1:8001`.
> **Regla del verd:** cada fase té un QA GATE; si falla → aturar, documentar, no avançar.

---

## BACKUP LÒGIC PRE-S10 (abans de la primera escriptura)

- `pg_dump -Fc` del schema `fhort` (binaris **PG18** — el server és 18.4; pg_dump/pg_restore 16 de PATH
  donaven un TOC il·legible per mismatch de versió).
- Fitxer: `…/scratchpad/PRE-S10_fhort.dump` (710 KB).
- **Verificat amb `pg_restore -l`:** exit 0, **1182 entrades TOC · 114 TABLE DATA** (quadra amb les 114
  taules del schema `fhort`). Backup vàlid i restaurable.

---

## FASE 0 — PREFLIGHT (read-only)

### 0.1 Estat de l'entorn
- `git fetch` + `git status`: branca **`dev`**, **up-to-date amb `origin/dev`** (0/0). Working tree amb
  canvis d'altres sessions (DECISIONS.md, docs untracked) — no tocats per aquest sprint.
- `ftt-staging.service`: **actiu**. `GET /api/schema/` → **200**.

### 0.2 SEMÀNTICA DEL BREAK (bloquejant per a la Fase 2) — `_apply_rule` (`pom/services.py:719-765`)

Forma canònica PEÇA A (`services.py:747-765`), amb `ib = increment_base`, `brk = increment_break`
(o `ib` si `increment_break` és NULL, `:749`). Per un pas cap a la talla `size_idx`, el motor itera els
índexs creuats `j` (l'índex de la talla MÉS LLUNYANA de cada pas) i acumula:

```python
for j in path:
    total += brk if (break_idx is not None and j >= break_idx) else ib   # :763-764
```

`break_idx = norm.index(talla_break_label)` contra el **run DEL MODEL**, no el del ruleset (`:753-757`).

**Run `[XXS,XS,S,M,L]` amb base S (idx 2), passos indexats per `j` (talla llunyana):**

| pas (parell) | j | direcció | usa `ib`(g1) si `j<break_idx` / `brk`(g2) si `j>=break_idx` |
|---|---|---|---|
| L↔M   | 4 | amunt | j=4 ≥ break_idx → **g2** |
| M↔S   | 3 | amunt | j=3 ≥ break_idx → **g2** |
| S↔XS  | 1 | avall | j=1 ≥ break_idx → **g2** |
| XS↔XXS| 0 | avall | j=0 < break_idx → **g1** |

**CAS OBJECTIU** (XXS↔XS = g1, la resta = g2): s'aconsegueix amb **`break_idx = 1` ⇒ `talla_break_label = 'XS'`**.
Aleshores l'únic pas amb `j=0 < 1` és XS↔XXS (usa `ib`=g1) i tots els altres (`j∈{1,3,4} ≥ 1`) usen `brk`=g2.
Verificat numèricament (POM A, g1=2/g2=3, base S=46): XXS=41, XS=43, S=46, M=49, L=52 — coincideix amb la
taula de la Fase 5.

> **⚠️ TROBALLA (semàntica invertida però CORRECTA):** la forma canònica **SÍ** pot expressar un break a
> l'extrem PETIT del run → **NO cal ATURAR**. Però el nom dels camps enganya: per a aquest cas
> **`increment_base` porta el valor del pas especial de l'extrem petit (g1)** i **`increment_break` porta
> el valor comú (g2)**. És a dir, `ib` s'aplica als passos PER SOTA de `talla_break_label` i `brk` als
> passos AL nivell o PER SOBRE. `talla_break_pos = run.index('XS') = 1` (0-based), coherent amb
> `derive_break_fields` (`pom/grading_utils.py:223`). El motor NO llegeix `talla_break_pos` per calcular
> (només `talla_break_label`); és cache/auditoria.

### 0.3 OBERT §5.1 — l'assignació del ruleset escriu el FK? (confirmat a codi; empíric a Fase 3)

- `update_model_step2` (`models_app/views.py:596`) crida `_resolve_garment_def(d)` (`:604`) i aplica els
  camps amb `setattr(model, k, v)` + `model.save()` (`:607-612`).
- `_resolve_garment_def` (`:387`): si `d.get('grading_rule_set_id')` (`:418`) → `fields['grading_rule_set']
  = GradingRuleSet.objects.get(id=...)` (`:420`). **⚠️** és tolerant: si l'id no existeix, `pass` silenciós
  (`:422`) i el FK no s'escriu → cal que RS_ID existeixi (existeix: 115).
- Després, si `model.grading_rule_set_id` (`:616`) → `materialize_model_grading_rules(model,
  model.grading_rule_set.regles.all(), origen='CANONICAL')` (`:619-621`). **Confirmació empírica a Fase 3.**

### 0.4 INVENTARI de `clone_model_for_qa` (`models_app/management/commands/clone_model_for_qa.py`)

Copia / crea: **Model** (nou pk; `codi_intern` regenerat; `nom_prenda='[QA-SC] …'`; **reutilitza per VALOR de
FK** `grading_rule_set` / `size_system` / `garment_type`, no els clona; `responsable=assignee`; fase Proto)
· **BaseMeasurement** (totes, `:92-96`) · **ModelGradingRule** (`:100-102`) · **SizeFitting** (via signal) +
**GradingVersion v1 activa** + `generate_graded_specs` (`:106-112`) · **ModelTask** `size_check` (`:118`).

> **⚠️ NO copia fitxers de patró (DXF/RUL) ni `ModelFitxer`.** → Conseqüència (Fase 3.1): es clona un
> **165/166** (no cal el 163 per patrons perquè el clon no en portaria); i la pota PATRONS de la Fase 6.3
> queda **NO EXERCITABLE via clon** aquest sprint.

**Veredicte FASE 0:** llest. Break semantics resolt (`talla_break_label='XS'`, `ib`=g1/`brk`=g2), OBERT §5.1
tancat a codi, inventari del clon fet. Cap ATURADA.

---

## FASE 1 — D-7: classificar les 25 GradingRuleSet `origen=NULL`

`manage.py set_grading_origen` **NO endevina** (Patró C): `--list` llista els NULL; `--map "id:ORIGEN[:CODI]"`
aplica el que decideix el CTO. No hi ha "mapatge proposat" automàtic — el construeixo jo pel criteri donat.

**Criteri (sprint):** `is_system_default=True → CANONICAL`. Els altres → llistar SENSE classificar.
Estat previ: 25 rulesets, **tots `origen=NULL`** (11 amb `is_system_default=t`, 14 amb `f`).

- **Dry-run** (`--map` amb els 11 sysdefault): 11 canviats NULL→CANONICAL, 0 ja hi eren.
- **Aplicat:** `75,79,81,83,84,86,87,88,89,90,91 → CANONICAL` (11 canviats).

**Audit SQL** (`SELECT origen, count(*) …`): **CANONICAL=11 · NULL=14**. Sanity:
`is_system_default=t AND origen IS NULL` = **0**.

**Les 14 que resten NULL (excepcions documentades — NO classificades, decisió Agus/Montse):** totes
`is_system_default=f`. Són variants de fit no-seed (76/77/78 Woven Woman Slim/Relaxed/Oversized, 80 Knit
Woman Slim, 82 Stretch Bodycon, 85 Woven Man Slim, 92 Dress Flared, 93 Baby Months, 98 Custom Alpha Women).

> **⚠️ Candidats provinença sensible (classificar abans del pròxim `bootstrap_tenant`):** **104** i **111**
> (customer **LOS**, id=6) → probable `CLIENT_RUN`; **110** (`Importació fitxa · BRW-SS27-0001`) → import de
> Brownie; **107** (`Importació fitxa · FTT-CO27-0001`) → import; **108** (`Mango … only dress`, 0 regles) →
> client Mango. Es deixen NULL per no endevinar (Patró C), però són fuites potencials si viatgen.

**QA GATE 1: PASSAT** — cap ruleset viu queda NULL sense justificació escrita (0 sysdefault NULL; les 14
restants són `is_system_default=f` amb classificació ajornada a decisió humana).

---

## FASE 2 — Crear "BRW · Blusa · ALPHA_EU_W" (shell ORM)

**Precondició (2.2):** verificats els **34/34 `pom_id`** a `pom_pommaster` del tenant `fhort` (0 inexistents)
→ cap ATURADA.

**Creat** (shell `schema_context('fhort')`, idempotent per `nom`):
- `GradingRuleSet` **id=115** (`RS_ID`) · `nom='BRW · Blusa · ALPHA_EU_W'` · `size_system_id=29`
  (ALPHA_EU_W) · `actiu=True` · **`origen=CLIENT_RUN`** · **`customer_id=7`** (BRW) · `target_id=1` (WOMAN,
  FK legacy) + **`targets` M2M = [1]** (rèplica exacta del camí wizard `size_map_views.py:816-821`).
- **34 `GradingRule`** (`logica='LINEAR'`, `talla_base_id=79` = S de ss=29):
  - g1==g2 → `increment_base=g1`, `increment_break=NULL`, sense break (20 regles).
  - g1≠g2 → `increment_base=g1`, `increment_break=g2`, `talla_break_label='XS'`, `talla_break_pos=1`
    (14 regles: A, D, E2, E3, E, E1, EK, EK1, SF, S, S2, J, J1, J2).

**Audit (2.3):**
- `count(*) WHERE rule_set_id=115` = **34**.
- **Verificació exhaustiva (no mostra): 34/34 regles amb valors EXACTES** de la taula del brief
  (increment_base, increment_break, talla_break_label, talla_break_pos, logica, talla_base). 0 discrepàncies.
  Mostra: `A` ib=2.00/brk=3.00/XS/1 · `E1` 0.25/0.40/XS/1 · `EK` 0.50/0.75/XS/1 · `SF` 0.70/1.00/XS/1 ·
  `J1` 0.30/0.50/XS/1 · `E5` 0.00/—/— · `B` 3.00/—/—.
- **API real:** `GET /api/v1/grading-rule-sets/` (JWT) → **HTTP 200**, id=115 present
  (`customer=7, actiu=True`). La UI GradingRuleSets consumeix el mateix endpoint → hi apareixerà.

> **⚠️ DEUTE DE PROVINENÇA (conegut, no arreglat):** l'API retorna **`origen: null`** per al 115 tot i que
> a BD és `CLIENT_RUN` (confirmat per SQL). El serializer `GradingRuleSetSerializer` NO exposa `origen`
> (no és a `Meta.fields`, diagnosi §4.1). La classificació és correcta a BD; només no és visible per l'API/UI.
> (La llista API retorna 25 per **paginació** de 25, no per filtre: el queryset és `.all()`; el 26è ruleset
> cau a la pàgina 2.)

**QA GATE 2: PASSAT** — 34/34 regles amb valors exactes.

---

## ✅ CHECKPOINT Fase 2 — Agus va **revisar i aprovar** el ruleset id=115 a la UI (2026-07-16). Continua Fase 3 amb clon del 165.

---

## FASE 3 — Aplicar a un model EXISTENT (via clon del 165)

### 3.0 ⚠️ TROBALLA prèvia — `clone_model_for_qa` NO és utilitzable aquí

La comanda té guarda idempotent **per-customer**: `Model.objects.filter(customer=src.customer,
nom_prenda__startswith='[QA-SC]')` (`clone_model_for_qa.py:60`). El customer BRW **ja té** el clon
`[QA-SC]` **182** (`BRW-26-SS-0002 · OLIVIA DRESS`, el golden de QA de Size Check). Per tant:
- sense `--recreate` → la comanda **es nega** i retorna pk=182 (no clona el 165);
- amb `--recreate` → **purga 182** (prohibit pel brief: "MAI operar sobre 162/163/182").

→ Fet un **clon ORM fidel** (mateixos passos que la comanda: còpia Model + BaseMeasurement + MGR + SF via
signal + GradingVersion activa), amb tag distint **`[QA-S10]`** per no col·lisionar amb la guarda del 182.
Cap original tocat.

### 3.1 CLON_ID
`CLON_ID = **267**` · codi `BRW-26-FW-0036` · clonat del **165** (`Blusa RUFUS STARS`). Reusa per valor de
FK: `grading_rule_set=None`, `size_system=29`, `garment_type_item=5`. `run='XS·S·L'`, base `S`.
`SizeFitting=157`, `GradingVersion=73` (activa).

### 3.2 Estat previ del clon
ModelGradingRule residents = **0**; GradedSpec = **0** (GV fresca).

### 3.3 PATCH `update-step2 {grading_rule_set_id:115}` (endpoint real) — **HTTP 200**
Verificació empírica (**tanca OBERT §5.1**):
- `model 267 . grading_rule_set_id = 115` ✓ (el FK **SÍ** s'escriu des de `request.data` via
  `_resolve_garment_def` → `setattr` → `save`).
- **34 ModelGradingRule residents**, **totes `origen='CANONICAL'`** ✓; els seus `pom_id` coincideixen
  EXACTAMENT amb els de la ruleset 115 (0 diferència en cap sentit); camps de break copiats correctament
  (p.ex. CH 2.00/3.00/XS/1, SH 0.25/0.40/XS/1, NK W 0.50/0.75/XS/1).

> **⚠️ DEUTE DE PROVINENÇA confirmat EN VIU:** les residents neixen `origen='CANONICAL'`
> (`views.py:621`) tot i que la ruleset font és `CLIENT_RUN`. La materialització no propaga la provinença
> de client. (Conegut; no s'arregla aquest sprint.)

### 3.4 POST `generar-grading` (endpoint real) — **HTTP 400** · QA ESTRUCTURAL NO EXERCITABLE

```
{"error":"No hi ha BaseMeasurements per al model BRW-26-FW-0036.
          Cal entrar les mesures de la talla base primer."}
```
GradedSpec generats = **0**.

> **⚠️⚠️ TROBALLA MAJOR (bloqueja QA GATE 3): la premissa "165/166 = blusas amb 37 mesures" és enganyosa.**
> Les 37 files `BaseMeasurement` existeixen però **tots els `base_value_cm` són NULL** (materialitzades sense
> valor). `_load_base_measurements` filtra `base_value_cm__isnull=False` (`pom/services.py`) → el diccionari
> de bases surt **buit** → `generate_graded_specs` aixeca `ValueError` (`services.py:162-166`). Cens dels
> candidats (verificat a BD):
>
> | model | run | nBM | **nonnull** | nMGR | grs |
> |---|---|---|---|---|---|
> | 164/165/166/167/175 | XS·S·L | 37 | **0** | 0 | NULL |
> | 173/174/176/177 | XS·S·L | 0 | 0 | 0 | NULL |
> | 163 (TATE) | **S** (1 talla) | 25 | 25 | 25 | NULL |
> | 162 (OLIVIA, original prohibit) | XS·S·M | 16 | 14 | 0 | 75 |
>
> A més, **cap dels candidats vàlids té XXS al run** (165/166 = `XS·S·L`): encara que tinguessin valors, el
> pas especial **XXS↔XS** (g1) **no hi és** → el break de l'extrem petit **no es podria mostrar** en aquest run.
>
> **Conseqüència:** la QA estructural del patró g1/g2 **no és exercitable sobre 165/166**. El conjunt "POMs
> amb base i regla" és **buit**. NO es declara verd fals: es documenta i s'atura al gate.

**Què SÍ ha validat la Fase 3 (la meitat mecànica, verda):** que la ruleset de client s'**adjunta** a un
model existent i **materialitza 34 residents** correctes (3.3, OBERT §5.1 tancat empíricament). **Què NO
(la meitat numèrica):** l'assercció d'increments sobre GradedSpec — delegada a la **Fase 5** (POP), que està
dissenyada exactament per això (run `[XXS,XS,S,M,L]` + 21 bases reals → QA numèric exacte de 105 cel·les).

**QA GATE 3: NO AVALUABLE** (conjunt buit de POMs amb base).

### 3.5 ✅ DECISIÓ AGUS (2026-07-16) — cobertura per equivalència
> El clon del 165 ja ha complert el seu paper (Fase 3.3: escriptura del FK i materialització de 34 residents
> **validades empíricament**). **NO** s'injecten bases artificials al 267 (el seu run sense XXS no exerciria
> el break igualment → seria "QA de fireta"). La **QA estructural del GATE 3 queda coberta per equivalència
> pel QA GATE 5 exacte** (105 cel·les, run complet `[XXS,XS,S,M,L]`, bases reals) — vegeu Fase 5, que
> valida el patró d'increments g1/g2 **i** el break a l'extrem petit amb tolerància ±0.01. **QA GATE 3:
> tancat per equivalència.**

---

## FASE 4 — Crear el model POP + bases reals (endpoints reals)

### 4.1 Creació via wizard real (`POST models/create-wizard/`) — HTTP 201
`POP_ID = **268**` · codi `BRW-FW27-0001` · `nom_prenda='Blusa POP'` · `customer_id=7` · `gti=5` (blouse) ·
`size_system_id=29` · `size_run='XXS·XS·S·M·L'`. Season **FW** (Winter) / 2027.

> **Nota de camí:** el wizard bloqueja `base_size` sense `grading_rule_set_id` (`views.py:454`, guard PG-3
> Cas B). Per respectar l'ordre de l'sprint (ruleset a la Fase 5), es crea SENSE base ni ruleset i s'estableix
> la base **`S`** amb un `PATCH update-step2 {base_size:'S'}` (aquest handler NO té el guard, `views.py:452`).

Verificat a BD: `size_run_model='XXS·XS·S·M·L'`, `base_size_label='S'`, `grading_rule_set_id=NULL`.

### 4.2 Materialitzar POMs + escriure 21 bases (superfície real de mesures)
- `POST materialitzar-poms/` → HTTP 200: `materialized=37, seeded=0` (item 5 no té `ItemBaseMeasurement` →
  37 shells TEMPLATE buits).
- `POST set-measurements/` (21 mesures, `origen='MANUAL'`) → HTTP 201: **`created=12, updated=9`** (9 POMs
  ja materialitzats de l'item + 12 POMs nous del spec POP que no són a la plantilla de l'item blusa).
  Valors (pom_id: cm): A/273=46 · D/326=54 · E2/465=33 · E3/420=33 · E/431=35 · E5/286=2 · E1/277=9 ·
  E4/455=1.5 · EK/301=17 · EK1/463=8 · EK2/464=2.5 · F/437=54 · FF/438=51 · SF/284=21.5 · S/457=23 ·
  S2/458=24 · I/292=61.5 · J/295=16.5 · J1/297=9 · J2/459=16.5 · J3/299=0.7.

**QA GATE 4: PASSAT** — **21/21 BaseMeasurement amb valor** (exactes, tots `origen='MANUAL'`), 0 extres;
run `[XXS,XS,S,M,L]` i base `S` correctes.

> **Comportament dels 13 POMs del ruleset SENSE base (patrimoni de catàleg):** E7·EP·E8·U2·U3·JJ·I3·P2·P1·
> L·BT·B·G1. Cap té valor base → `_load_base_measurements` no els inclou → **no generen GradedSpec** (ni tan
> sols FIXED). A la projecció simplement NO apareixen: regla sense base = cel·la absent, no cel·la a zero.
> (Dels 13, només `B/275` té shell TEMPLATE buit perquè és a la plantilla de l'item; la resta ni shell.)

---

## FASE 5 — Projecció conscient + QA NUMÈRIC EXACTE

### 5.1 `PATCH update-step2 {grading_rule_set_id:115}` — HTTP 200
Residents després d'assignar: **34 ModelGradingRule, totes `origen='CANONICAL'`** (mateix deute de provinença
que la Fase 3). El model POP passa a graduar per aquestes residents.

### 5.2 `POST generar-grading` — HTTP 200
`graded_count=**105**`, `size_run=[XXS,XS,S,M,L]`, `base_size=S`. (SF=158, GV=74.)

### 5.3 QA NUMÈRIC EXACTE (lectura directa de `GradedSpec` a BD)
Comparació de **les 105 cel·les** (21 POMs amb base × 5 talles) contra la taula del brief, tolerància ±0.01:

**QA GATE 5: PASSAT — 105/105 cel·les dins ±0.01. Cap discrepància.** `grading_type_applied='LINEAR'` per
a tots 21. El break de l'extrem petit (XXS↔XS = g1, resta = g2) es reprodueix EXACTAMENT (p.ex. SF: XXS=19.8,
XS=20.5, S=21.5 — la baixada XS→XXS és 0.7=g1, la resta 1.0=g2; NK W: XXS=15.75, XS=16.25 — 0.5=g1 vs
0.75=g2).

> **Aquesta és la prova numèrica que valida el motor de grau amb la primera GradingRuleSet REAL de client
> (Brownie) de punta a punta, i que cobreix per equivalència el GATE 3 estructural.**

---

## FASE 6 — Les tres destinacions del node graduat

### 6.1 ESCALAT — `GET models/268/taula-mesures/` — HTTP 200 · **PASS**
21 files amb `graded` no-buit; valors idèntics a la taula (p.ex. CH XXS=41/L=52, AH DEP XXS=19.8/L=23.5,
S XXS=21.3/S=23). ⏸️ *Agus valida visualment MeasureGrid mode model si vol la passada visual.*

### 6.2 TECHSHEET — `GET fitting/158/graded-table/` — HTTP 200 · **PASS**
Snapshot del SizeFitting contenidor (sf=158, gv=74, base=S, `size_labels=[XXS,XS,S,M,L]`): **21 files amb
`valors`**, exactes (CH XXS=41/L=52, NK W XXS=15.75/M=17.75, S XXS=21.3, AH DEP XXS=19.8). És la segona porta
(mateixa taula `GradedSpec`). ⏸️ *Agus munta el bloc `graded_table` en una fitxa de prova si vol la passada visual.*

### 6.3 PATRONS — **NO EXERCITABLE aquest sprint**
El clon de la Fase 3 ve del **165** (no TATE) i `clone_model_for_qa` **no copia fitxers de patró** (§0.4); el
POP 268 és un model nou sense DXF/RUL. Per tant la pota `export → grading_projection` no té cap `PatternFile`
a exercitar. **Candidat futur** (decisió amb Agus): adjuntar un DXF/RUL real a un model amb aquesta ruleset i
exercitar el port `adapters.py:432` en mode segur. NO s'improvisen pujades de DXF.

---

## ARTEFACTES DE DADES CREATS (staging `fhort`, validació — no codi)

| tipus | id | detall |
|---|---|---|
| GradingRuleSet | **115** | `BRW · Blusa · ALPHA_EU_W` · CLIENT_RUN · customer 7 · 34 GradingRule |
| Model (clon QA F3) | **267** | `[QA-S10] Blusa RUFUS STARS` (BRW-26-FW-0036), clon del 165; grs=115, 34 residents |
| Model (POP F4-5) | **268** | `Blusa POP` (BRW-FW27-0001); 21 bases MANUAL; grs=115; SF=158/GV=74; 105 GradedSpec |
| set_grading_origen | — | 11 rulesets NULL→CANONICAL (75,79,81,83,84,86,87,88,89,90,91) |

> Cap toca originals 162/163/182. Backup PRE-S10 verificat abans de la primera escriptura. **Cap commit de
> codi, cap migració, cap push.**

---

## TROBALLES (recull)

1. **Semàntica del break (§0.2):** la forma canònica **SÍ** expressa un break a l'extrem PETIT, però amb
   **noms invertits**: `increment_base` = g1 (pas especial XXS↔XS), `increment_break` = g2 (comú),
   `talla_break_label='XS'`. Validat numèricament (105/105). El motor usa `talla_break_label` (no
   `talla_break_pos`) contra el run DEL MODEL.
2. **Comportament dels 13 POMs sense base:** regla sense valor base → **cel·la absent** a la projecció (no
   zero, no FIXED). Patrimoni de catàleg sense mesura = simplement no es gradua.
3. **Deute de provinença `CANONICAL`:** tant `update-step2` (Fase 3) com la reassignació (Fase 5)
   materialitzen residents amb `origen='CANONICAL'` encara que la ruleset font sigui `CLIENT_RUN`. La
   provinença de client NO es propaga a les residents. A més, l'API `GradingRuleSetSerializer` **no exposa
   `origen`** (retorna `null`); la classificació és correcta a BD però invisible a UI/API.
4. **OBERT §5.1 tancat (empíric):** `update-step2 {grading_rule_set_id}` **SÍ** escriu el FK
   (`_resolve_garment_def` → `setattr` → `save`) i re-materialitza els residents. Confirmat en viu (model 267
   i 268 → grs=115 + 34 residents).
5. **`clone_model_for_qa` no reutilitzable per BRW:** guarda idempotent **per-customer** que col·lisiona amb
   el `[QA-SC]` 182; `--recreate` el purgaria. → clon ORM fidel amb tag `[QA-S10]`.
6. **Premissa "165/166 = 37 mesures" enganyosa:** 37 files però **0 valors** (base_value_cm NULL) i run
   **`XS·S·L` sense XXS** → QA estructural del GATE 3 no exercitable sobre elles (coberta per GATE 5).

---

## LLISTA MONTSE (reconciliacions de diccionari/domini pendents — decisió humana)

- **U / TAPETA ANCHO:** el codi `U` va quedar amb CRUCE DELANTE; **TAPETA ANCHO perdut sense traça**
  (col·lisió last-wins). POMMaster 343 (PLCK W) sense àlies. Cal segon codi per a TAPETA ANCHO?
- **B4 / B6 (ARRIBA/ABAJO):** 0 files, mai van entrar. El diccionari original els contenia?
- **F1 → 437 (lossy):** `F1` (DICCIONARI) i `F` (IMPORT) resolen al **mateix** POM 437 amb descripcions
  diferents → mapatge possiblement lossy. **EXCLÒS del ruleset** (col·lisió amb F/437).
- **codi `0` → 461:** `0` i `I3` resolen al **mateix** POM 461. **EXCLÒS del ruleset** (col·lisió amb I3/461).
- **Els 7 forats `[D1, M1, M2, I4, J4, I1, L1]`:** sense POM canònic (confirmat a la diagnosi). **EXCLOSOS**
  del ruleset (no tenen destí).
- **Convenció ½ amplades vs canònic (CH/273):** D-4 de la diagnosi — cal decidir si els POMs d'amplada del
  spec POP són ½-amplada o amplada sencera abans de fixar bases definitives (no hi ha normalització ½↔sencer
  automàtica al camí d'import). Els valors base d'aquest sprint es van entrar tal com dona el SIZE SET real
  (la taula de 105 cel·les hi quadra), però la convenció resta **oberta** per a la producció.
- **Provinença dels 14 rulesets NULL restants:** 104/111 (customer LOS), 110 (BRW import), 107 (FTT import),
  108 (Mango) → candidats `CLIENT_RUN`/`IMPORT`; classificar abans del pròxim `bootstrap_tenant`.

---

*RESULTAT S10 tancat. 5 QA GATES: 1·2·4·5 PASSATS; GATE 3 tancat per equivalència (decisió Agus). Cap push,
cap commit de codi, cap migració. Únic fitxer creat: aquest.*
