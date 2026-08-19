# DIAGNOSI C4 · L'ONA REAL

Data: 2026-08-03 · **Patró A — DIAGNOSI READ-ONLY** · staging `/var/www/ftt-staging`, branca `dev`
HEAD auditat: **`acc2291b`** · BD: `ftt_staging` @ 5433 (schemas `fhort` · `los` · `public`)

**Res tocat.** Cap escriptura a `ftt_staging`. Cap fitxer del repo modificat. Cap migració, cap
management command, cap push, cap deploy. Escriptures fetes: aquest document i la BD de test
(`test_ftt_staging`, ritual anti-enverinament + `manage.py test --keepdb`).

**Convenció.** `fitxer:línia` verificat a HEAD `acc2291b`. «NO EXISTEIX» = confirmat absent.
REGLA D'OR: en cas de dubte, el node és DINS, marcat ⚪. **Cap proposta de fix.**

---

## 0 · RESUM EXECUTIU

### 0.1 · Les quatre premisses del brief que NO se sostenen

**① El HEAD no és el que el brief esperava.** Els sis commits demanats hi són tots, però n'hi ha
**tres més a sobre**, i el brief no els anomena: `e4c675aa` i `8ac2d257` (cua PRE-C4 del matí) i
**`acc2291b` (avui 13:23, de l'Agus)**, que canvia el gate de Mesures a `ModelSheet.jsx:173`
(`pomDone && hasBaseValue` → `||`). No toca la cadena d'identitat de mesura: és un gate d'UI.
**No aturo el tram per això**, però queda dit: `dev` va 13 commits per davant d'`origin/dev`, cap
pushat, i hi ha hagut una sessió concurrent avui a la tarda.

**② El «RESIDUAL TRIO» NO està tancat sencer. Està tancat 2 de 3.** El brief demanava verificar-lo
com a JA RESOLT. Dos ho són de debò; **el tercer no**, i ho diu el seu propi docstring:

| peça | commit | estat real |
|---|---|---|
| E3+E4 · propagació de fitting | `a590c827` | ✅ **RESOLT DE DEBÒ** — `capa=line.capa, instancia=line.instancia`: deriva els eixos de la línia, no els ancora |
| A1 · buidatge del wizard | `09fcdaee` | ✅ **RESOLT DE DEBÒ** — el 4t escriptor cec tancat, clau completa + `atomic()` + rastre explícit |
| E5 · `desactivar_pom` | `55e13cab` | 🚨 **ANCORAT, NO RESOLT** — `models_app/views.py:4095-4097` filtra `capa=SLUG_DEFECTE, instancia=''` |

El docstring d'`E5` (`models_app/views.py:4084-4090`) ho declara literalment:

> «No es pot arreglar del tot aquesta nit: **el contracte de la ruta només porta `pom_id`**
> (`models_app/urls.py:233`), i fer-hi entrar els eixos és tocar la interfície, que és C4 amb
> maqueta (llei 3c.5). […] **DEUTE C4: quan la ruta sàpiga dir la capa i la instància, aquest
> ancoratge se'n va.**»

**Això és feina de C4, i és feina que el brief donava per feta.**

**③ No hi ha 18 comportes. N'hi ha 42, i una d'elles no és una comporta.** El brief diu «18 CHECK
(9 taules × 2 famílies)». Això és cert **per schema de tenant**, però n'hi ha **tres** schemas amb
files gatejades: `fhort` (19), `los` (19) i `public` (4 — només les dues taules de catàleg). Total
**42 constraints**. I la 19a de cada tenant, **`models_app_basemeasurement_instancia_exigeix_nom`**
—`NOT (instancia > '' AND nom_fitxa = '')`— **no és una comporta del tram: és la invariant que ha de
SOBREVIURE C4.** Retirar-la per error seria permetre una germana anònima. Detall a §4.

**④ El cens de 203/158 no és estable des de C3: ho és des de la FASE F2/F3 de l'01/08.** El brief
atribueix el delta a «~16 commits, TOT C3». Fals: entre el cens (31/07, HEAD `72d2e579`) i avui hi ha
**dues onades**, i la que va moure els lectors de payload és **F2/F3 de l'01/08** (`6e28ef72`,
`f4c6af24`, `94f64f7e`, `d3999ab1`, `d8e740c9`, `79314af5`, `e33f3ff7`…), no C3 del 02/08. Detall a §2.

### 0.2 · La troballa que decideix la mida de C4

**El cens tenia cinc estats. En fa falta un sisè, i és on viu gairebé tot C4.**

Els lectors de payload **no s'han resolt i no s'han quedat igual**: s'han **ANCORAT**. Avui filtren
explícitament `capa='exterior', instancia=''` i **el payload segueix sortint indexat per `pom_id` sol**,
amb acta escrita al codi que difereix el canvi de contracte a C4. Exemple canònic,
`fitting/graded_spec_views.py:97-104`:

> «La clau es queda per POM perquè la FILA que la consulta (`rows_by_pom`) tampoc no porta capa, i
> donar-n'hi voldria dir afegir un camp al payload —**canvi de contracte, i el contracte no es toca
> fins a C4**—.»

**Conseqüència pràctica, i és un canvi de mode de fallada:** amb les comportes retirades i una germana
viva, aquests endpoints **ja no col·lapsaran (l'última guanya): amagaran** (la germana no surt del
`filter`). Passar de «dada equivocada» a «dada absent» és millor per a la integritat i **pitjor per a
la detecció**: la pantalla es veurà coherent i correcta, i faltarà una fila. **Cap test d'avui ho veu**,
perquè amb les comportes vives el conjunt filtrat i el conjunt sencer són el mateix.

### 0.3 · Recompte real de C4 després del delta

| bloc | cens 31/07 | avui | mort per F2/F3 o C3 | viu a C4 |
|---|---|---|---|---|
| **A** · payloads dict per `pom_id` | 11 | 11 | **1** (`pom_placement_views`, F3-5) | **10** |
| **B** · contractes amb `pom_id` al path/llista | ~12 | ~12 | 0 | **12** (1 amb deute declarat: `desactivar`) |
| **C** · serializers sense eix | 5 | 5 | 0 | **5** |
| **D** · `TechSheetEditor.jsx` | 79 | 79 | 0 | **79** |
| **E** · resta de frontend | 79 | 79 | 0 | **79** |
| **F** · i18n que afirma la llei | 7 claus | 7 claus | 0 | **7** |
| **TOTAL** | **203** | | **1** | **≈202** |

**C3 ha matat ZERO nodes de C4-ins. F2/F3 n'ha matat UN.** El recompte de frontend és **158, intacte**:
cap commit posterior al cens ha tocat cap dels 158 fitxers de frontend censats (l'únic commit de
frontend del tram és `acc2291b`, i toca `ModelSheet.jsx`, que **no és al cens**).

**El que C3 SÍ ha fet** no és matar nodes de C4: és **desarmar l'accident** i **tancar els escriptors**.
Això canvia el RISC de C4, no la seva MIDA. Detall a §2.3.

### 0.4 · La línia base de tests nova — **verda del tot, per primer cop**

`fhort.models_app` **504** · `fhort.pom` **207** · `fhort.fitting` **71** · `fhort.patterns` **380** ·
`fhort.tasks` **86** · `fhort.tenants` **133** → **1 381 tests · 0 errors · 0 fallades · 0 saltats**,
sis `OK` nets, 83,4 min. **Cap vermell a cap app.** Les 2 fallades que quedaven a `fitting`+`pom` al
tancament PRE-C4 les va tancar `657e41fe`.

**Això canvia el green flag del tram:** ja no cal comparar nominalment contra una llista de
preexistents — **qualsevol vermell durant C4 és de C4**. Detall i prova anti-enverinament a §1.

### 0.5 · Les xifres que desdramatitzen

| mesura | resultat | on |
|---|---|---|
| POMs orfes als dos eixos | **0** a 9 taules × 3 schemas | §8 |
| Items que produirien germanes en sembrar | **0** (`GarmentPOMMap` i `ItemBaseMeasurement`, els dos eixos) | §5 |
| Cotes `.ftt` sense àncora segura `bmId` | **0 de 239** (17 fitxers, tots del model `LOS-SS27-0274`) | §7 |
| `.ftt` vius a staging | 632 a disc `fhort` · 365 files DB · **15 vigents** | §7 |

**C4 té marge real.** No hi ha ni una sola dada viva que necessiti desambiguació, i el corpus `.ftt`
—el watchpoint més car del cens— **té exposició zero**: totes les cotes vives porten `bmId`, que és
l'àncora per PK de fila i sobreviu a la germana. El camí de col·lapse (`bmByPom`,
`TechSheetEditor.jsx:3457`) existeix al codi però **cap document viu el necessita**.

### 0.6 · Grups mínims de retirada de comportes

Quatre grups. Dins d'un grup, les comportes **han d'anar al mateix commit**; entre grups, no.

| grup | taules | què les lliga |
|---|---|---|
| **G1 · la mesura i el seu rastre** | `basemeasurement` + `measurementchangelog` | **signal `log_measurement_change`** (`signals.py:254`, `post_save` síncron, mateixa transacció) + **l'única FK entre taules gatejades** |
| **G2 · el fitting complet** | `gradedspec` + `piecefittingline` + G1 | cadena d'escriptura `generate_graded_specs` → `create_piece_fitting` (`fitting/services.py:339`) → `consolidate_base_from_fitting` (`:383`) → signal → changelog |
| **G3 · el catàleg** | `garmentpommap` + `itembasemeasurement` | mateix `confirm` de promoció, mateix bucle (`models_app/views.py:3900` i `:3919`) |
| **G4 · solitaris** | `sizecheckline` · `pomplacement` · `modelgradingoverride` | cap acoblament d'escriptura amb els altres |

**Detall que el brief demanava i que és el punt fi:** l'exemple del brief («crear una mesura de folre
dispara el signal F1, que escriu al changelog») **és exacte i és G1**. Retirar la comporta de
`basemeasurement` sense retirar la de `measurementchangelog` fa petar l'escriptura a mig camí —
el signal és `post_save` síncron dins la mateixa transacció.

**Fora de tot grup, i és important:** `pom_gradingrule` (1174 files) i `models_app_modelgradingrule`
(344 files) **no tenen columnes `capa`/`instancia` i per tant no tenen comporta**. No és un forat:
és **decisió de domini amb acta**, `pom/services.py:723-730` — «mateix POM, mateix increment a totes
les capes i a totes les instàncies». **C4 no els ha de tocar.**

---

## 1 · LÍNIA BASE DE TESTS, PER APP

Ritual anti-enverinament aplicat abans de córrer: `ps aux | grep "manage.py test"` → cap PID viu ·
sobre `test_ftt_staging` (mai `ftt_staging`): `DELETE FROM public.tenants_client WHERE
schema_name='test'` (0 files) + `DROP SCHEMA IF EXISTS test CASCADE` (no existia) · verificat **0
files + 0 schema** abans de llançar · llançat desacoblat amb `setsid nohup`.

> ⚠️ **Correcció d'etiqueta:** les apps **no** es diuen `models_app`/`pom`/…: viuen sota el paquet
> `fhort`. L'etiqueta correcta és **`fhort.models_app`**. Amb l'etiqueta pelada el runner no peta amb
> «app desconeguda» sinó que fa `ModuleNotFoundError` i retorna **`FAILED (errors=1)` en 1 segon** —
> exactament la forma d'un fals verd/vermell. Anotat perquè no torni a passar.

### 1.1 · La línia base nova — **1 381 tests, 0 errors, 0 fallades**

Corregut app per app amb `--keepdb`, seqüencial, desacoblat. Finestra real: **15:53:51 → 17:17:29 UTC**.

| # | app (etiqueta real) | tests | errors | fallades | temps | veredicte |
|---|---|---|---|---|---|---|
| 1 | `fhort.models_app` | **504** | **0** | **0** | 1 599,9 s (26,7 min) | `OK` |
| 2 | `fhort.pom` | **207** | **0** | **0** | 742,2 s (12,4 min) | `OK` |
| 3 | `fhort.fitting` | **71** | **0** | **0** | 223,7 s (3,7 min) | `OK` |
| 4 | `fhort.patterns` | **380** | **0** | **0** | 999,7 s (16,7 min) | `OK` |
| 5 | `fhort.tasks` | **86** | **0** | **0** | 399,2 s (6,7 min) | `OK` |
| 6 | `fhort.tenants` | **133** | **0** | **0** | 1 038,4 s (17,3 min) | `OK` |
| | **TOTAL** | **1 381** | **0** | **0** | **5 003 s ≈ 83,4 min** | **sis `OK` nets** |

**Signatura de cada vermell: no n'hi ha cap.** Verificat que no és un fals verd: cap fitxer de log
conté `FAILED` ni `ERROR:`, i **cap test saltat ni cap `expected failure`** (`grep` sobre els sis
logs: 0 coincidències de `skipped=` i `expected failures=`). Els sis acaben amb `OK` pelat.

**Prova anti-enverinament:** 1 381 tests en 5 003 s = **3,6 s/test de mitjana**, i l'app més gran
(`models_app`) va trigar **26,7 minuts**. La signatura d'enverinament que el brief descriu (~400
tests en <60 s) **no s'ha donat en cap de les sis**.

### 1.2 · Dues coses que aquesta línia base canvia

**① Les 2 fallades que quedaven al tram `fitting`+`pom` han desaparegut.** El tancament del bloc
PRE-C4 les deixava a `269 tests · 0 errors · 2 failures` (a `40dc480d`). Avui, a `acc2291b`, el
mateix parell fa **`278 tests · 0 errors · 0 failures`**. Les 2 fallades eren les de
`PropagarActionTest` i **les va tancar `657e41fe`** («el fixture de `PropagarActionTest` diu la
veritat sobre el sistema de talles»); els 9 tests de diferència són els que van entrar amb
`e4c675aa` (`test_pomalert_vocabulari.py`) i `8ac2d257` (`test_regla_inactiva_no_editable.py`).

**② El green flag de C4 ja no és «cap error nou»: és «cap error».** Amb els sis apps a zero, la
comparació nominal deixa de necessitar llista de preexistents. **Qualsevol vermell durant C4 és,
per definició, de C4.** És la primera vegada en tot el tram que això es pot dir.

> 🚩 **Anotat per a l'Agus, contra la premissa del brief:** córrer-ho **app per app va costar 83,4
> minuts**, pràcticament el mateix que els 86 minuts de la suite sencera que la prohibició volia
> evitar. La prohibició estalvia **risc d'enverinament entre apps**, no temps de rellotge. Si l'estalvi
> buscat era el temps, cal saber que no hi és.

---

## 2 · RE-CENS DELTA DELS 203/158

### 2.1 · El delta no és de C3: és de F2/F3

El cens és del **31/07 a HEAD `72d2e579`**. Entre aquell HEAD i avui hi ha **dues onades**, no una:

| onada | data | què va fer als nodes de C4-ins |
|---|---|---|
| **F2/F3** | **01/08** | va **ANCORAR** tots els lectors de payload a `('exterior','')` i va tancar la clau natural de sembradors i federació |
| **C3** | **02/08** | va **desarmar l'accident** del motor i **tancar els escriptors**; **cap node de contracte ni d'UI** |
| cua PRE-C4 | 03/08 | fixtures + 2 fixes de vocabulari/estat; cap node del cens |

Verificat per `git log` per fitxer: els cinc lectors de payload del bloc A que han canviat porten
`6e28ef72` (F2-3), `f4c6af24` (F2-4), `94f64f7e` (F2-1), `d3999ab1` (F3-5), `d8e740c9` (F3-7) —
**tots de l'01/08**.

### 2.2 · Bloc A — els 11 payloads, node a node

| # | node al cens | a HEAD `acc2291b` | estat |
|---|---|---|---|
| 1 | `pom/grading_views.py:156` | `:155-156` (`cells[pom_id]`), payload `:208`; **ancorat** `:136`, `:168` | 🟠 **ANCORAT-COL·LAPSA** |
| 2 | `models_app/views.py:1736-1738` | **MOGUT → `:1771`** (`'deltes': deltas`) | 🟠 ANCORAT-COL·LAPSA |
| 3 | `fitting/graded_spec_views.py:120` | **MOGUT → `:132`**; ancorat `:48-50`; **acta explícita `:97-104`** | 🟠 ANCORAT-COL·LAPSA (amb acta) |
| 4 | `pom/s6_views.py:193` | **MOGUT → `:192`, `:201`**; ancorat `:96`, `:176` | 🟠 ANCORAT-COL·LAPSA |
| 5 | `fitting/repas_views.py:333` | **MOGUT → `:294`**; ancorat `:156`, `:277`; el mapa de notes ja és per clau de 4 (`:118`) | 🟠 ANCORAT-COL·LAPSA |
| 6 | `models_app/pom_placement_views.py:60-92` | `clau(p) = (p.pom_id, p.capa, p.instancia)` **`:59`**; `bm_by_pom` per triple **`:96`** | ✅ **JA RESOLT** (F3-5 `d3999ab1`) |
| 7 | `models_app/views.py:3016-3045` | **MOGUT → `:3046`**; clau interna `(pom_id, capa, instancia)` `:3107`; **el payload NO canvia, per acta `:3100-3106`** | 🟠 ANCORAT-COL·LAPSA (amb acta) |
| 8 | `models_app/extraction_views.py:2176-2182` | **MOGUT → `import_session_confirmar_view:2147`**; eixos **declarats com a literals** (F3-7 `d8e740c9`) | 🟠 ANCORAT — el document importat no sap dir la capa |
| 9 | `pom/wizard_views.py:339-367` | **MOGUT → `:391`, `:406`** (`regla_by_pom.get(bm.pom_id)`) | ⚪ **CAU SOL** — la regla no té eixos **per decisió** (§4.4) |
| 10 | `patterns/views.py:144` | **MOGUT → `:605-615`**; ancorat `:608`; acta al sostre de `F2-patrons` `:600-604` | 🟠 ANCORAT-COL·LAPSA |
| 11 | `models_app/tech_sheet_views.py:322` | **MOGUT → `:371`**; `instancia=''` literal | 🟠 ANCORAT — el mapa és `{client_code: pom_code}`, el col·lapse és al POM |

**Resultat del bloc A: 1 resolt · 1 que cau sol · 9 vius a C4.**

### 2.3 · Què va fer C3 de debò (i per què no redueix C4)

Tres nodes que el cens marcava com a perill màxim **estan desarmats**, i cap dels tres és de C4-ins:

- **L'accident de C4** (`_upsert_graded_spec`, cens §5.2, «l'espera C4»): **DESARMAT**. El lookup ja és
  de 5 camps i el cridador passa els eixos (`pom/services.py:1069-1078` + `:294-306`). Docstring:
  «AQUEST ERA EL NODE QUE ARMAVA L'ACCIDENT DE C4».
- **El node mestre del col·lapse** (`_load_base_measurements`): **RESOLT** — retorna
  `{(pom_id, capa, instancia): valor}` (C3/B1).
- **El forat de l'Onada 1 al signal F1**: **TANCAT** — `signals.py:335-341` estampa `capa` i `instancia`
  copiant-los de la `instance` (F3-3 `25628518`). Taula append-only: no podia esperar.

**Cap d'aquests tres és un node de contracte ni d'UI.** Redueixen el risc de retirar les comportes;
no redueixen la feina de C4.

---

## 3 · NODES DE MATEIX-COMMIT

### 3.1 · Els tres del frontend que perden dades abans del backend — **TOTS TRES VIUS**

| node | línia a HEAD | forma |
|---|---|---|
| `EditableTable.jsx` · `keep_pom_ids` | **`:172`** | `localRows.map(r => r.pom_id).filter(Boolean)` → retornat a `:180` |
| `CheckMeasureEditor.jsx` · `desactivarPom` | **`:389`** | `models.desactivarPom(model.id, row.pom_id)` |
| `endpoints.js` · `escalatAjustarTalla` | **`:123-124`** | body `{pom_id, talla, valor}`; el `lineId` sintètic es desmunta a `PropagatedEditor.jsx:70-72` |

**L'asimetria que això crea és el punt de §3.** Dos dels tres tenen el backend ja tocat per C3:

- `desactivar_pom` — **backend ancorat** (`views.py:4095-4097`), **frontend segueix enviant `pom_id` sol**.
  Amb la comporta retirada, la crida desactivarà **la de l'exterior**, silenciosament, sempre.
- `escalat/ajustar-talla` — **backend ancorat amb literals** (`views.py:2831`, `:2842`, `:2846`, `:2853`),
  **frontend segueix enviant `pom_id` sol**.

**Cap dels dos peta. Tots dos trien l'exterior i no ho diuen a la pantalla.**

### 3.2 · El «residual trio» — 2 de 3 (⚠️ premissa del brief corregida)

Vegeu §0.1 ②. `a590c827` i `09fcdaee` són resolucions reals; `55e13cab` és un **ancoratge amb deute
C4 declarat al docstring**. El residu existeix, és **una sola peça**, i està documentat pel seu autor.

### 3.3 · `bootstrap_tenant.py:162` — ⚠️ **la sospita del brief era correcta: és referència vella**

A HEAD la línia **162 és un comentari**, i la clau natural viu a **`:167`**:

```python
(GarmentPOMMap, ('garment_type_item', 'pom', 'capa', 'instancia'), {}, (), None),
```

Amb acta a `:162-166` («FASE_3/C1-ins — la clau natural creix amb els DOS EIXOS. Era el deute de C1
que el dossier va trobar»). **RESOLT per F3-9 (`79314af5`, 01/08).** El watchpoint del cens §5.1/§8.2
—«el dia que C4 la retiri, el copiador comença a perdre files en silenci»— **ja no aplica**.

> ⚪ Anotat, no és d'aquest tram: a la mateixa taula, `:168` declara `GradingRule` com
> `('rule_set', 'pom')`. És **coherent** amb la decisió de §4.4 (la regla no té eixos), no un oblit.

---

## 4 · ACOBLAMENT DE LES COMPORTES

### 4.1 · L'inventari real — 42 constraints, no 18

```sql
SELECT n.nspname, t.relname, c.conname, pg_get_constraintdef(c.oid)
FROM pg_constraint c
JOIN pg_class t ON t.oid = c.conrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
WHERE c.contype = 'c'
  AND (pg_get_constraintdef(c.oid) ILIKE '%capa%'
    OR pg_get_constraintdef(c.oid) ILIKE '%instancia%');
```

| schema | taules gatejades | constraints |
|---|---|---|
| `fhort` | 9 | 18 comportes + 1 invariant = **19** |
| `los` | 9 | 18 comportes + 1 invariant = **19** |
| `public` | 2 (`pom_garmentpommap`, `pom_itembasemeasurement`) | **4** |
| | | **42** |

**La 19a no és una comporta.** `models_app_basemeasurement_instancia_exigeix_nom`:
`CHECK (NOT (instancia > '' AND nom_fitxa = ''))` — «una germana ha de tenir nom». **Ha de sobreviure
C4**; és precisament la regla que fa distingible la germana a la pantalla.

### 4.2 · L'acoblament per FK — n'hi ha exactament UNA

De 24 FK sortints de les 9 taules gatejades, **una sola apunta a una altra taula gatejada**:

```
models_app_measurementchangelog.base_measurement_id → models_app_basemeasurement.id
```

Totes les altres van a taules **sense** eixos (`pom_pommaster`, `models_app_model`,
`models_app_sizecheck`, `fitting_piecefitting`, `fitting_gradingversion`, `models_app_itemfitxer`,
`pom_itembaseset`, usuaris). **La FK no és el que lliga les comportes: ho són els signals.**

### 4.3 · L'acoblament per signal i per cadena d'escriptura

**El signal que mana** — `models_app/signals.py:253-341`, `log_measurement_change`, `post_save` sobre
`BaseMeasurement`, **síncron i dins de la mateixa transacció**. Escriu `MeasurementChangeLog`
copiant `capa` i `instancia` de la `instance` (`:335-341`). Un `INSERT` de germana a `basemeasurement`
amb la comporta del changelog encara viva **peta al signal, després d'haver escrit la mesura**.

**Les cadenes d'escriptura multi-taula:**

| cadena | punt d'entrada | taules gatejades tocades |
|---|---|---|
| tancament de fitting | `fitting/services.py:339` → `:383` → signal | `gradedspec` → `piecefittingline` → `basemeasurement` → `changelog` |
| promoció model→item | `models_app/views.py:3900` + `:3919` (mateix `confirm`) | `garmentpommap` + `itembasemeasurement` |
| obertura de size check | `models_app/services_size_check.py:64` | `sizecheckline` (llegeix `basemeasurement`) |
| override de talla | `models_app/views.py:2663` + `:2677` (mateixa funció) | `modelgradingoverride` + `changelog` |

> ⚪ **Anotat, fora de scope:** l'override de talla escriu a `modelgradingoverride` **i** al changelog
> a la mateixa funció, però el changelog hi arriba per crida **explícita** (`:2677`), no pel signal —
> el signal només cobreix `BaseMeasurement`. Són dues portes al mateix rastre.

### 4.4 · El que NO té comporta, i és a posta

`pom_gradingrule` (1174 files a `fhort`) i `models_app_modelgradingrule` (344 files) **no tenen les
columnes**. Verificat contra `information_schema`: només 9 taules de `fhort` porten `capa`/`instancia`.

Acta a `pom/services.py:723-730` (C3/B6):

> «AQUESTA CLAU NO CREIX, i és a posta. […] És decisió de domini —mateix POM, mateix increment a
> totes les capes i a totes les instàncies— […]. Si algun dia la regla ha de distingir capes, això és
> una **decisió humana i una migració**, no un retoc d'aquest lookup.»

**Per a C4 això és una bona notícia:** el motor busca la regla amb el `pom_id` **extret** de la
identitat (`services.py:239`, `:413`), i això seguirà funcionant amb germanes vives sense tocar res.

> 🚩 **Asimetria anotada, decisió de l'Agus:** `models_app_modelgradingoverride` **SÍ** té els dos
> eixos (i 0 files), mentre que `models_app_modelgradingrule` **NO** en té (i 344 files). La regla
> és per-POM i l'excepció a la regla és per-germana. És defensable —l'override és una mesura, la
> regla és una llei— però **no hi ha acta que ho digui**, i les dues taules són veïnes.

---

## 5 · EL CATÀLEG COM A PRIMER PRODUCTOR DE GERMANES

**Mesurat sobre `fhort` (schema del tenant BRW/LOS a staging; `los` és buit i `public` no té files).**

```sql
SELECT count(*) FROM (SELECT garment_type_item_id, pom_id FROM fhort.pom_garmentpommap
                      GROUP BY 1,2 HAVING count(*) > 1) x;   -- 0
SELECT count(*) FROM (SELECT base_set_id, pom_id FROM fhort.pom_itembasemeasurement
                      GROUP BY 1,2 HAVING count(*) > 1) y;   -- 0
```

| taula | files | eix d'agrupació | parells repetits | items/sets afectats |
|---|---|---|---|---|
| `pom_garmentpommap` | 1748 (55 GTI) | `(garment_type_item, pom)` | **0** | **0** |
| `pom_itembasemeasurement` | 37 (1 base_set) | `(base_set, pom)` | **0** | **0** |

**Zero. `materialize_poms` no produiria ni una germana no demanada.**

> **Per què havia de sortir 0, i per què l'he mesurat igual.** La unicitat real ja inclou els dos
> eixos —`UNIQUE (garment_type_item_id, pom_id, capa, instancia)` i
> `UNIQUE (base_set_id, pom_id, capa, instancia)`— i les comportes forcen els eixos a constants: un
> duplicat de `(gti, pom)` és **impossible per construcció avui**. La xifra confirma que **cap fila
> ha entrat abans que la constraint** (la de `pom_itembasemeasurement` va per `base_set`, no per
> `garment_type_item`, i he mesurat els dos eixos per no donar per bo el que el brief suposava).

**C4 té marge.** El primer productor de germanes serà un acte humà —un tècnic que declari una capa o
una instància—, no la sembra.

---

## 6 · LECTORS QUE RE-COL·LAPSEN A LA SORTIDA

**Separats en dos blocs, com demanava el brief.** El backend **hi arriba bé** a tots els casos: la
pèrdua és sempre a la vora del payload o al frontend.

### 6.1 · Ja resolts — no tornen a ajuntar

| node | per què és segur |
|---|---|
| `models_app/pom_placement_views.py:59,96` | clau `(pom_id, capa, instancia)` a les dues bandes (F3-5) |
| `fitting/repas_views.py:118,172` | el mapa de notes va per `(check, pom, capa, instancia)` |
| `TechSheetEditor.jsx:3462` | prova **`bmById` primer** — PK de fila, immune a la germana |

### 6.2 · Vius — la BD desarà bé i la pantalla tornarà a ajuntar

| # | node | on col·lapsa | què es perd a pantalla | backend hi arriba bé? |
|---|---|---|---|---|
| 1 | `pom/grading_views.py:155-156,208` | `cells: {str(pom_id): …}` | la germana **no surt** (filtrada a `:136`,`:168`) | ✅ sí |
| 2 | `fitting/graded_spec_views.py:57-82,132` | `rows_by_pom[pom.id]` | fila sencera absent | ✅ sí, amb acta |
| 3 | `pom/s6_views.py:192,201` | `pom_dict[pid]` | fila sencera absent | ✅ sí |
| 4 | `fitting/repas_views.py:294` | `files[pom_id]` | fila sencera absent | ✅ sí |
| 5 | `models_app/views.py:1771` | `'deltes': {pom_id: …}` | delta de la germana absent | ✅ sí |
| 6 | `models_app/views.py:3046-3107` (`base-stages`) | clau interna correcta, **payload per `pom_id` sol** | fila sencera absent | ✅ sí, amb acta `:3100-3106` |
| 7 | `patterns/views.py:605-615` | `{pom_id: {…}}` (`model-poms`) | fila sencera absent | ✅ sí |
| 8 | **`fittingGridAdapter.jsx:144`** | `lineId: ` \`${row.pom_id}:${s}\` | identificador **sintètic** sense eixos | ✅ sí |
| 9 | **`repasGridAdapter.jsx:123`** | `lineId: ` \`repas:${row.pom_id}\` | ídem — **NOU, no era al cens** | ✅ sí |
| 10 | `PropagatedEditor.jsx:70-72` | desmunta el `lineId` → `pomId` i el torna al backend | l'edició aterra a l'exterior | ✅ sí |
| 11 | `TechSheetEditor.jsx:3457` | `bmByPom` (fallback de `:3462`) | etiqueta de la germana equivocada | ✅ sí |
| 12 | `EditableTable.jsx:172` | `keep_pom_ids` | **poda**: la germana no conservada s'inactiva | ✅ sí |
| 13 | `CheckMeasureEditor.jsx:389` | `desactivarPom(model.id, row.pom_id)` | desactiva l'exterior, sempre | ✅ ancorat |

**L'identificador sintètic `{pom_id}:{talla}`** que el brief citava a «backend `:2789-2793`» **no és
al backend**: el backend rep `{pom_id, talla, valor}` per body a `ajustar_talla_view`
(`models_app/views.py:2726`). **El sintètic es fabrica i es desmunta sencer al frontend**
(`fittingGridAdapter.jsx:144` → `PropagatedEditor.jsx:70-72`). Correcció al cens.

> 🆕 **Node NOU (no era al cens de 31/07):** `repasGridAdapter.jsx:123` fabrica `repas:${row.pom_id}`
> amb la mateixa forma que `fittingGridAdapter`. És `readonly: true`, o sigui que **no escriu** — però
> és el mateix patró i entra per la regla d'or.

---

## 7 · `.ftt` — CENS SOBRE L'ESTAT D'AVUI

### 7.1 · Quants n'hi ha

| mesura | `fhort` | `los` | `test` (residu) |
|---|---|---|---|
| files `ModelFitxer` tipus `TECHSHEET` | **365** | 0 | — |
| … de les quals **vigents** (`is_current`) | **15** | 0 | — |
| `EXPORT` (PDF generat) | 8 | 0 | — |
| fitxers `.ftt` a disc | **632** | 0 | 656 |

**El `.ftt` és un ZIP** (`manifest.json` + `document.json`) — per això cap `grep` sobre el fitxer cru
en treu res. Cens fet obrint els 632 arxius.

> 🚩 **Dues xifres que no quadren, anotades:** (a) **632 fitxers a disc vs 365 files a la BD** →
> ~267 orfes de disc, coherent amb la poda del desat (esborra la fila, no el fitxer). (b) A
> `backend/media/test/` hi ha **656 `.ftt`, 120 dels quals corruptes** (no s'obren com a ZIP): residu
> de corregudes de test que escriuen a `media/` real. Cap de les dues afecta C4; van al calaix d'higiene.

### 7.2 · Quants porten `pomId` a dins — i la xifra que ho decideix tot

| mesura | resultat |
|---|---|
| `.ftt` de `fhort` amb clau `pomId` | **17** de 632 |
| cotes amb `pomId` en total | **239** |
| **cotes amb `bmId` (àncora per PK de fila)** | **239 / 239 — el 100%** |
| **cotes SENSE `bmId`** | **0** |
| models implicats | **1** (totes 17 són versions de `LOS-SS27-0274`) |

### 7.3 · Quins camins els llegeixen, i què fan amb dues instàncies

| camí | comportament amb dues germanes |
|---|---|
| `TechSheetEditor.jsx:3454-3481` (efecte F1, re-deriva l'etiqueta) | `bmById.get(o.bmId) || bmByPom.get(o.pomId)` — **prova la PK primer**. Amb `bmId` present: **correcte**. Sense: agafa la germana que hagi quedat última al `Map` i **re-etiqueta** la cota |
| `buildLiveCota` `:320-344` | **escriu** `pomId` **i** `bmId` (+ `pomCanonical`, `viewSlot`, `precedentGermana`) → tota cota nova neix segura |
| `models_app/pom_placement_views.py:76,96` | materialitza la cota per `(pom_id, capa, instancia)` — **ja resolt** |

**Cap camí peta. Cap camí esborra.** El pitjor cas és **re-etiquetar** una cota, i **avui no és
assolible**: no hi ha ni una cota viva sense `bmId`.

**Conclusió de §7: el watchpoint del `.ftt` està buit.** El cost «fora de Postgres» que el cens
dimensionava sobre 3606 documents és, a la pràctica, **17 fitxers d'un sol model, tots ja segurs**.

---

## 8 · AUDITORIA CAP-POM-ORFE, ELS DOS EIXOS

**Consulta** (SQL directe, sense ORM), aplicada a **9 taules × 3 schemas**:

```sql
SELECT count(*) FILTER (WHERE capa IS DISTINCT FROM 'exterior') AS capa_orfe,
       count(*) FILTER (WHERE instancia IS DISTINCT FROM '')    AS inst_orfe,
       count(*)                                                 AS total
FROM <schema>.<taula>;
```

`IS DISTINCT FROM` cobreix **el `NULL` i el valor divergent alhora**, que és el que demanava el brief
(`capa != 'exterior' O capa IS NULL`).

| taula | `fhort` (orfes / total) | `los` | `public` |
|---|---|---|---|
| `models_app_basemeasurement` | 0 / 0 · **602** | 0 / 0 · 0 | — |
| `models_app_measurementchangelog` | 0 / 0 · **193** | 0 / 0 · 0 | — |
| `models_app_modelgradingoverride` | 0 / 0 · 0 | 0 / 0 · 0 | — |
| `models_app_pomplacement` | 0 / 0 · **2** | 0 / 0 · 0 | — |
| `models_app_sizecheckline` | 0 / 0 · **92** | 0 / 0 · 0 | — |
| `fitting_gradedspec` | 0 / 0 · **1635** | 0 / 0 · 0 | — |
| `fitting_piecefittingline` | 0 / 0 · **153** | 0 / 0 · 0 | — |
| `pom_garmentpommap` | 0 / 0 · **1748** | 0 / 0 · 0 | 0 / 0 · 0 |
| `pom_itembasemeasurement` | 0 / 0 · **37** | 0 / 0 · 0 | 0 / 0 · 0 |

**Resultat: 0 orfes a totes les taules i tots els schemas.** Total de files gatejades vives a
staging: **4 462**, totes a `fhort`. `los` és buit a les 9 taules (coherent amb el cens: els models
LOS viuen a `fhort`).

> ⚠️ **Límit declarat:** això és **staging**, còpia endarrerida. No he pogut contrastar-ho contra PROD
> (sense SSH; la via documentada és llegir el backup diari). **La xifra de PROD queda sense mesurar**,
> i és l'única de tot aquest document que ho queda.

---

## 9 · ELS 7 QUE NO S'ADAPTEN — TOTS VIUS, AMB LÍNIES NOVES

**No hi ha cap proposta d'inversió.** Patró C: el cas puja a l'Agus, la decisió és seva.

| # | node (cens) | a HEAD | què bloqueja | cas real citat al codi |
|---|---|---|---|---|
| 1 | `pom/size_map_views.py:54-75` | **`:54-75` IGUAL** | dues files del document que resolen al mateix POM per **fuzzy/descripció** → cap auto-vincula (`many_to_one`) | **LOS `H.11` sleeve opening / `H.16` cuff opening**. ⚠️ **L'àlies exacte JA n'està EXEMPT** (`match_type == 'alias_match'`) |
| 2 | `models_app/extraction_views.py:1148-1193` | **`:1149-1192`** | mateix guard `_apply_many_to_one_guard` a la porta d'import | ídem |
| 3 | `models_app/extraction_views.py:1734,1753` | **MOGUT → `:1755`** | `pom_ja_usat`: un POM ja pres per una altra fila del mateix pla | — (guard de pla, sense cas al docstring) |
| 4 | `pom/services.py:613-622` | **MOGUT → `:653-677`** | un POM que el client ja reclama amb un ALTRE codi → l'àlies neix **`pendent_revisio`** | **BRW `F` (FRONT total length) i `FF` (BACK total length) → POM 389** · **`U`/`U2`/`U3` → POM 439** |
| 5 | `seed_losan_rules_v2.py:128-134` | **`:128-138`** | `seen{}` per `pom.codi_client` dins d'un contenidor → **col·lisió** registrada, regla descartada | LOS (el sembrador del ruleset) |
| 6 | `patterns/models.py:430-437` | **`:429-436`** | `UniqueConstraint(pattern_piece, pom_master)` — «Dos ancoratges del mateix POM a la mateixa peça serien dues veritats sobre la mateixa mesura» | — (constraint d'esquema) |
| 7 | `frontend/SizeMapSetup.jsx:340-346` | **`:339-346`** | `dupPomIds` → marca visual + **create bloquejat** (backend 400) | **«decisió CTO: bloquejar»** |

### 9.1 · La correcció al cens, i el que fa el cas més fàcil del que semblava

- **El cens deia «BRW U2/U3→POM U».** El codi diu una altra cosa: `U`, `U2` **i** `U3` → **POM 439**
  (i `F`/`FF` → **POM 389**). Són **tres** codis a un POM, no dos, i el POM destí és numèric.
- **El node 1 ja no bloqueja el cas de LOS.** L'àlies **exacte** està **exempt** del guard des de
  QA-S8: «un client pot etiquetar legítimament el mateix POM amb dos codis (Losan H.11 sleeve opening
  / H.16 cuff opening)». **El cas que la instància vol legitimar ja està mig legitimat**, i el que
  queda bloquejat és només el camí **fuzzy/descripció**.
- **El node 4 no bloqueja: marca.** L'àlies s'escriu igualment, amb `pendent_revisio=True`
  (`services.py:670`, `:677`). És una **cua de revisió humana**, no una porta tancada.
- **Els que bloquegen de debò són el 3, el 5, el 6 i el 7.** El 6 és una `UniqueConstraint` de
  Postgres —cau amb una migració, no amb codi— i el 7 porta acta de CTO explícita.

---

## 10 · LÍMITS D'AQUEST DOCUMENT

1. **PROD no mesurat.** §8 i §5 són de `staging`. Sense SSH a PROD; la via documentada (llegir el
   backup diari) no s'ha recorregut en aquesta sessió. **Totes les xifres de dades d'aquest document
   són de `ftt_staging` @ 5433**, i cada taula ho diu.
2. **Els 158 de frontend no s'han re-verificat un a un.** El que **sí** s'ha verificat, i és una prova
   dura, és que `git diff --name-only 72d2e579..HEAD -- frontend/` retorna **exactament UN fitxer**:
   `frontend/src/pages/ModelSheet.jsx` — **que no és a cap dels blocs D ni E del cens**. Cap dels 158
   nodes pot haver canviat, perquè cap dels fitxers on viuen ha estat tocat. A més s'han re-localitzat
   a mà **els 6 nodes de frontend nominats pel brief**. La resta es dona per IGUAL **per absència de
   commit**, no per lectura línia a línia. (Contrast: al backend hi ha **46** fitxers de producció
   tocats en el mateix interval.)
3. **`patterns_patternpom` segueix a 0 files** als tres schemas: el bloc `F2-patrons` és tot codi sense
   dades, com al cens.
4. **La línia base de tests és per app i amb `--keepdb`**, no la suite sencera (ordre de l'Agus).
   Comparació **NOMINAL** per signatura, mai «suite verda».

---

*Diagnosi read-only. Cap fitxer del repo modificat, cap escriptura a `ftt_staging`, cap migració, cap
management command, cap push, cap deploy. Aquest document viu al working tree i **no es commiteja**.*
