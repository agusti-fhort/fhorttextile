# DIAGNOSI — MOTOR DE MESURES I DERIVACIÓ ENTRE CAPES/INSTÀNCIES (C3)

Data: 2026-08-02 · **Patró A (READ-ONLY ABSOLUT)** · staging `/var/www/ftt-staging` branca `dev`
HEAD: **`277cb9e0d96f440a92e6b36e2dfcfe16809c5206`** (Sat Aug 1 17:24:42 2026)
BD: `ftt_staging` @ 127.0.0.1:5433 · schemas `fhort` · `los` · `public`

Abast: l'estat REAL del motor de grading davant la identitat de mesura `(model, POM, capa, instància)`,
i què hi ha —i què no— per sostenir la DERIVACIÓ d'increments dins la família d'un POM.

Convenció: cada afirmació porta `fitxer:línia` verificat al HEAD d'avui. **"NO EXISTEIX" = confirmat
absent** (grep exhaustiu buit o SELECT amb 0 files), mai suposat. Les propostes van marcades `💡` i
separades dels fets. **Cap proposta de fix**: aquest document és registre.

Cap escriptura a BD, cap migració, cap fitxer del repo modificat, cap management command, cap commit.
Única escriptura: aquest document. Excepció autoritzada i executada: la sonda d'A10, dins d'una
transacció revertida i verificada (§A10).

---

## RESUM EXECUTIU — les conclusions que decideixen

**1. La frontera C3 és UNA funció, i el codi ja ho diu amb data.**
`_load_base_measurements` (`backend/fhort/pom/services.py:774-790`) segueix retornant
**`{pom_id: base_value_cm}`** — un sol eix, declarat al docstring `:775` i materialitzat a `:783`.
Tot el motor penja d'aquest dict. El propi codi declara la frontera i la condició de sortida a
`services.py:728-729` («El dia que C3 doni capa a `_load_base_measurements`, aquesta clau ha de créixer
amb ella i el filtre se'n va: **van junts**») i `:734-735` (i el mateix per la instància).

**2. Tres premisses del brief ja NO són vigents. S'han tancat abans d'avui.**

| Premissa del brief | Estat real al HEAD | Prova |
|---|---|---|
| «l'accident de C4 armat a `_upsert_graded_spec`» | **DESARMAT** | el lookup és de 5 camps: `services.py:1064-1069` |
| «el signal F1 no estampa capa» | **ESTAMPA els dos eixos** | `signals.py:274-275` i `:322-323` |
| «`preview_graded_specs` out[pom_id]=row» (pendent heretat) | **VIU, confirmat** | `services.py:401` |

El bloqueig s'ha desplaçat **un nivell amunt**: `_upsert_graded_spec` sap rebre els dos eixos —són
paràmetres declarats amb default explícit (`:1022-1023`)— però **el seu únic cridador de producció no
els passa** (`:284-292`), perquè el bucle que recorre (`:233`) ve del dict d'un sol eix. Tres nodes,
en fila: `:783` → `:233` → `:284`. Això és C3, i res més.

**3. Amb dues germanes, qui guanya s'endú la FILA SENCERA, no una cel·la. Mesurat.**
`{pom_id: valor}` és un **escalar per POM**. Sobre dues germanes col·lapsa a una entrada i guanya
l'**última** de l'`.order_by('ordre')` (`:786`) — mesurat literalment: `[exterior, folre] → {299: 6.5}`,
`[folre, exterior] → {299: 1.5}`. I com que el valor base propaga a tota la fila graduada, la germana
perdedora no perd una cel·la: **desapareix sencera, sense excepció, sense log, sense warning**. Amb
`ordre` empatat, el guanyador el decideix el planner de Postgres.

**4. Avui res d'això és observable: dues germanes NO PODEN EXISTIR.** No és una tria del motor, és la
BD qui ho barra, a les dues puntes de la cadena. **9 taules** porten comportes CHECK bessones
(`capa='exterior'` + `instancia=''`), vives a `fhort` **i** a `los`. El corpus és 100% pre-família:
760 `BaseMeasurement`, 760 claus `(model,pom)` distintes → **cardinalitat exactament 1**, zero germanes,
una capa, una instància. Tot el dany registrat aquí és **latent**, no actiu.

**5. El coll d'ampolla no és un, són DOS, i el segon no estava anotat enlloc.**
A banda de `_load_base_measurements`, la signatura de `preview_graded_specs(model, base_values: dict)`
(`services.py:333`) és **estructuralment cega**: `base_values` és `{pom_id: valor}`, i dues germanes
**ni tan sols s'hi poden expressar com a entrada**, independentment del que faci la BD o el loader.
Són dues fronteres separades; només la primera està documentada al codi.

**6. Per a la derivació hi ha 10 llocs naturals, però només DOS són honestos.**
Dels 16 punts d'escriptura de mesura base, 10 tenen lloc estructural on l'increment ja és calculable al
moment. Però només **dos coneixen els seus eixos per CÒPIA i no per literal** —
`fitting/services.py:391` i `services_size_check.py:241` — i per tant són els únics on «la família» és
avui interrogable sense endevinar res. Els altres declaren `capa='exterior', instancia=''` a mà.

**7. El camí principal no té transacció, i el llenç net és irreversible.**
`ATOMIC_REQUESTS` **NO EXISTEIX** (`settings.py:118-127`). `POST generar-grading/` (`views.py:2394`)
**no obre cap `atomic`**: `ModelGradingOverride.objects.filter(model=model).delete()` (`:2464`) commita
tot sol. Si la propagació peta després, el llenç net **no es desfà** — i la v+1 pot quedar creada i
buida. Cap `select_for_update` a tot el cicle.

**8. El changelog és append-only de MÈTODE, no de BD — i ja hi ha producció que el travessa.**
`save()`/`delete()` alcen (`models.py:902-909`), però són guards d'instància: `QuerySet.update()` i el
CASCADE de Postgres hi passen per sota. `consolidate_pom_catalog.py:117` **reescriu el `pom_id` de files
de changelog ja escrites**, amb el bypass reconegut al comentari `:111-112`.

**9. El motor està verd perquè mai no ha vist una germana.** Els 3 harnesses de germanes que
existeixen viuen **tots** a `models_app/`. `pom/services.py` — el motor — **no té ni un sol test amb dues
files del mateix `(model, pom)`**. I no hi ha CAP automatisme que corri els tests (ni CI, ni hooks, ni
cron, ni script `test`); a sobre, en aquest entorn **la BD de test no es pot construir**.

**10. Dos pins del repo es contradiuen literalment**, i avui conviuen només perquè les comportes
impedeixen el cas: `test_escriptors_instancia_cins.py:132` afirma «una línia per germana, no una per POM»
(n==3); `test_size_check_completa_linies.py:53/59/100/113/121` afirmen n==1/n==2 sobre la mateixa
materialització. **El dia que caiguin les comportes, un dels dos fitxers menteix.**

---

## A1 · `_load_base_measurements` — l'estat REAL avui

### A1.1 · Transcripció literal (`backend/fhort/pom/services.py:774-790`)

```python
774: def _load_base_measurements(model_id: int) -> dict:
775:     """Return {pom_id: base_value_cm}."""
776:     try:
777:         from fhort.models_app.models import BaseMeasurement
778:         # Ignora files materialitzades sense valor (base_value_cm=None) → no es graden.
779:         # D2: i també les de valor 0 — una talla base a zero és físicament impossible, o
780:         # sigui que el POM no existeix per a aquest model. No gradua, no emet cel·la. Que
781:         # un 0 no arribi mai a la base és feina de la validació d'entrada (autoria/import).
782:         return {
783:             bm.pom_id: bm.base_value_cm
784:             for bm in BaseMeasurement.objects.filter(
785:                 model_id=model_id, is_active=True, base_value_cm__isnull=False
786:             ).exclude(base_value_cm=0).order_by('ordre')
787:         }
788:     except Exception as e:
789:         logger.warning(f"Could not load BaseMeasurements: {e}")
790:         return {}
```

**Forma del retorn: `{pom_id: base_value_cm}`.** Declarat al docstring `:775`, materialitzat a la clau
de la comprensió **`:783`**. Un sol eix. Cap `capa` ni `instancia` **ni al filtre** (`:785`), **ni a la
clau** (`:783`), **ni a l'ordre** (`:786`).

Dos detalls que importen:
- L'`.order_by('ordre')` de `:786` **sobreescriu** el `Meta.ordering` del model, que sí que agrupa per
  capa (`models_app/models.py:759`: `['model','capa','ordre','pom']`). El loader renuncia
  explícitament a l'agrupació que el model li oferia.
- L'`except Exception` de `:788-790` **retorna un dict buit i només loguja un warning**. Un error de BD
  al loader no fa petar el grading: el converteix en «aquest model no té mesures», i el cridador alça
  `ValueError` (`:216-220`) amb un missatge que no diu la causa real.

### A1.2 · `BaseMeasurement` TÉ els dos eixos — i el loader els ignora

ORM (`backend/fhort/models_app/models.py`, classe a `:588`):

| camp | línia | declaració |
|---|---|---|
| `capa` | `:710-714` | `CharField(max_length=20, default='exterior', db_index=True)` |
| `instancia` | `:734-738` | `CharField(max_length=60, default='', db_index=True)` |
| clau única | `:754` | `unique_together = [('model', 'pom', 'capa', 'instancia')]` |

Postgres (`fhort.models_app_basemeasurement`, 20 columnes; extracte):

```
 column_name | data_type         | column_default
-------------+-------------------+----------------
 capa        | character varying |
 instancia   | character varying |
```

**Divergència confirmada amb tres proves**: els camps existeixen (`models.py:710` + `:734`), la clau de
BD els incorpora (`:754`, i l'índex real
`models_app_basemeasureme_model_id_pom_id_capa_ins_8405ced0_uniq`), i **el loader només llegeix
`pom_id`** (`services.py:783`).

> 🚩 **`column_default` és BUIT a Postgres** per a `capa` i `instancia`, tot i que Django declara
> `default='exterior'` / `default=''`. Són `NOT NULL` sense default de columna. Confirmat també per a
> `fitting_gradedspec`, `models_app_modelgradingoverride` i `models_app_measurementchangelog`, i a
> **tots dos schemas (`fhort` i `los`)**. Qualsevol INSERT que no passi per l'ORM (SQL cru, `COPY`,
> `pg_restore` d'un dump anterior a C1, loader de paquet) **peta per NOT NULL** en comptes d'agafar el
> default. És el mateix deute ja anotat a memòria per a `capa`; aquí queda confirmat que **també val per
> a `instancia` i també per a tres taules més**.

### A1.3 · Consumidors del retorn — cadena completa fins a l'última conseqüència

`grep -rn "_load_base_measurements"` → 9 hits, dels quals **2 són crides reals** (la resta: la
definició `:774` i comentaris a `:368`, `:717`, `:728`, `:734`, `:1042`).

**Consumidor 1 — `generate_graded_specs` (producció):**

| pas | fitxer:línia | què fa |
|---|---|---|
| crida | `pom/services.py:215` | `base_measurements = _load_base_measurements(model.pk)` |
| guard | `:216-220` | dict buit → `ValueError` |
| **itera** | `:233` | `for pom_id, base_val in base_measurements.items()` — **l'única identitat de mesura a l'abast del motor** |
| indexa | `:234` | `rule = rules.get(pom_id)` |
| indexa | `:239` | `override = model_overrides.get((pom_id, size_label))` |
| indexa | `:246` | `pom_id in poms_nomes_override` |
| calcula | `:265-268` | `_apply_rule(rule, base_val, steps, i, base_idx, …)` |
| **mor** | `:284-292` | `_upsert_graded_spec(...)` → `GradedSpec.objects.update_or_create` (`:1064`) → fila a `fhort.fitting_gradedspec` |
| retorn | `:322` | `return created` (int) |
| lateral | `:311-313` | `SizeFitting…update(estat='TallesGenerades')` |

**On mor el `int` de retorn, per cridador** (7 cridadors, 4 sense ruta HTTP — v. A3.1):

1. `pom/grading_views.py:41-46` → `{'graded_specs_actualitzats': n}` (200) · 409 si segell · 400 si `ValueError`
2. `pom/wizard_views.py:277-291` → `{'talles_generades': …}` (200)
3. `pom/services.py:501-502` (`close_base`) → `{'generated_now': …, 'graded_specs': …}` (`:515-521`)
4. `pom/services.py:898` (dins `bump_grading_version_and_generate`) — **retorn DESCARTAT**; el que arriba a la resposta és `GradedSpec…count()` a `models_app/views.py:2489`
5. `models_app/views.py:2664` (`set_size_override_view`) — descartat; mor a la relectura `:2678-2680`
6. `models_app/views.py:2828` (`escalat_ajustar_talla_view`) — descartat; mor a `linies` (`:2842-2846`)
7. `management/commands/clone_model_for_qa.py:111` → `stdout` (`:112`)

**Consumidor 2 — `backend/scripts_tmp/golden_163_snapshot.py:23`:**
`bases` entra com a `base_values` de `preview_graded_specs` (`:24`), s'aplana a
`flat[f'{pom_id}|{size}']` (`:26-28`) i mor a `/tmp/golden_163.json` (`:35-36`). **La clau del golden
és `pom_id|talla`** — v. A8.

**Consumidor indirecte — `preview_graded_specs` via HTTP:** `extraction_views.py:1980`, on
`base_values` **no** ve del loader sinó del body (`:1968-1978`).

**Veredicte A1:** el dict és `{pom_id: valor}` a `services.py:783`. La taula té els dos eixos i la clau
única els incorpora. Divergència total, i és el node mestre de tot el que segueix.

---

## A2 · Els veïns del motor

### A2.1 · Taula de claus — memòria vs BD

| # | funció (fitxer:línia) | clau EN MEMÒRIA | unicitat A BD | divergeix? | què col·lapsa |
|---|---|---|---|---|---|
| 1 | `_load_base_measurements` `services.py:774` (clau `:783`) | `pom_id` | `UNIQUE (model_id, pom_id, capa, instancia)` | **SÍ** | germanes → **una entrada**; guanya l'última per `order_by('ordre')`. La perdedora **no genera cap cel·la** |
| 2 | `_load_model_overrides` `:711` (clau `:741`) | `(pom_id, size_label)` | `UNIQUE (model_id, pom_id, size_label, capa, instancia)` | **SÍ en clau, NO en efecte** | **àncora exterior explícita** a `:743-744` (`capa=SLUG_DEFECTE, instancia=''`). Amb el filtre, res. **Sense** ell, un override de folre sobreescriuria la cel·la d'exterior amb petja `'EXCEPTION'` i cap rastre |
| 3 | `_load_grading_rules` `:682` (claus `:702`,`:705`) | `pom_id` | `UNIQUE (model_id, pom_id)` · `UNIQUE (rule_set_id, pom_id)` | **NO** | res. Les dues taules **NO tenen columnes `capa`/`instancia`** (SELECT amb 0 files) — decisió de domini documentada a `models_app/models.py:982-1010` |
| 4 | `_te_regles` `:647` | cap dict (`.exists()`) | — | N/A | res (booleà de porta) |
| 5 | `_poms_amb_override` `:751` (cos `:771`) | `{pom_id for pom_id, _label in …}` — **descarta el `size_label`** | derivat de #2 | **SÍ** (hereta la clau parcial) | avui res (#2 filtra). Obert el filtre, fusionaria «override a l'exterior» i «al folre» en un `pom_id`, i la branca de rescat (`:245-252`) escriuria el base col·lapsat a totes les capes |
| 6 | `escala_del_model` `:104` (retorn `:163`) | etiqueta de talla → índex | geometria | N/A | res (l'eix és la TALLA) |
| 7 | `preview_graded_specs` `:333` (escriptura `:401`) | `out[pom_id] = row` → `(pom_id, size_label)` | (no persisteix) | **SÍ** | v. A2.3 |
| 8 | `generate_graded_specs` `:166` (bucle `:233`) | `pom_id` (heretat de #1) | `UNIQUE (gv, pom, size_label, capa, instancia)` | **SÍ, per herència** | el bucle només té un `pom_id`; escriu sempre `('exterior','')` pels defaults |
| 9 | `_upsert_graded_spec` `:1014` (lookup `:1064-1069`) | **`(gv, pom_id, size_label, capa, instancia)` — 5 camps** | **els mateixos 5 camps** | **NO** | **res. Coincideixen exactament.** V. A2.4 |

### A2.2 · Sortides SQL (extracte literal)

```
 fitting_gradedspec_grading_version_id_pom_i_2dd89ac9_uniq
   | CREATE UNIQUE INDEX ... USING btree (grading_version_id, pom_id, size_label, capa, instancia)
 models_app_basemeasureme_model_id_pom_id_capa_ins_8405ced0_uniq
   | CREATE UNIQUE INDEX ... USING btree (model_id, pom_id, capa, instancia)
 models_app_modelgradingo_model_id_pom_id_size_lab_2b3deedb_uniq
   | CREATE UNIQUE INDEX ... USING btree (model_id, pom_id, size_label, capa, instancia)
 models_app_modelgradingrule_model_id_pom_id_717138a3_uniq
   | CREATE UNIQUE INDEX ... USING btree (model_id, pom_id)
 pom_gradingrule_rule_set_id_pom_id_cec331bc_uniq
   | CREATE UNIQUE INDEX ... USING btree (rule_set_id, pom_id)
```

Existència de columnes (`information_schema`, schema `fhort`):

```
           table_name            | column_name |     data_type
---------------------------------+-------------+-------------------
 fitting_gradedspec              | capa        | character varying
 fitting_gradedspec              | instancia   | character varying
 models_app_modelgradingoverride | capa        | character varying
 models_app_modelgradingoverride | instancia   | character varying
(4 rows)
```

→ **`models_app_modelgradingrule` i `pom_gradingrule` NO tenen aquestes columnes: 0 files.**
La regla de graduació **no porta capa ni instància**, exactament com el context de disseny estableix, i
això ja és així a l'esquema — no cal fer-hi res.

Dades vives (per què cap col·lapse és observable):

```
models_app_basemeasurement      : capa='exterior', instancia='' →  760 files (única combinació)
fitting_gradedspec              : capa='exterior', instancia='' → 2061 files (única combinació)
models_app_modelgradingoverride : 0 files
```

> 🚩 **`models_app_modelgradingoverride` és BUIDA a `fhort`.** Tota la branca d'override del motor
> (`services.py:239-252`) i el predicat `_poms_amb_override` són **codi inert amb les dades d'avui**:
> cap QA sobre dades reals de staging pot exercitar-los.

### A2.3 · El PENDENT heretat — `out[pom_id] = row`

**`backend/fhort/pom/services.py:401`** (dins el guard `if row:` de `:400`; bucle obert a `:366`,
`row` construït a `:374`/`:398`). **VIU, confirmat.**

Amb dues germanes del mateix POM:
- Si `base_values` ve del loader: **ja han col·lapsat abans d'arribar-hi**, a `:783`. El preview
  només en veu una.
- Si ve del body HTTP (`extraction_views.py:1968-1978`): les claus són `int(k)` d'un JSON — **un
  objecte JSON no pot ni expressar dues germanes**; la clau repetida guanya al parseig.
- Si dues germanes hi arribessin a iterar, `:401` **sobreescriuria** silenciosament. Última guanya.

### A2.4 · L'"accident C4" a `_upsert_graded_spec` — **DESARMAT**

Funció sencera: `services.py:1014-1082`.

Els dos eixos són **paràmetres declarats amb default explícit**:
```
1022:    capa: str | None = None,
1023:    instancia: str = '',
```
resolts a `:1053-1054` (`capa = MeasurementLayer.SLUG_DEFECTE`, declarat a `pom/models.py:223`).

**Lookup de l'`update_or_create` (`:1064-1069`) — 5 camps:**
```python
1064:        GradedSpec.objects.update_or_create(
1065:            grading_version_id=grading_version_id,
1066:            pom_id=pom_id,
1067:            size_label=size_label,
1068:            capa=capa,
1069:            instancia=instancia,
```
`defaults` (`:1070-1076`): `graded_value_cm`, `grading_type_applied`, `increment_applied_cm`,
`is_active`, `generated_from_version`.

**Coincideix EXACTAMENT** amb `UNIQUE (grading_version_id, pom_id, size_label, capa, instancia)`. El
docstring `:1032-1046` ho documenta en passat, sota l'etiqueta FASE_3/C1-ins: «AQUEST ERA EL NODE QUE
ARMAVA L'ACCIDENT DE C4».

**Resultat amb dues germanes**: ni `IntegrityError` de lògica, ni sobreescriptura silenciosa, ni
`MultipleObjectsReturned`. Faria dos `get()` disjunts i mantindria **dues files independents** — el
comportament correcte. **El que el frena avui és la comporta de BD, no la lògica** (mesurat a A10).

**El bloqueig real és un nivell amunt:** l'únic cridador de producció, `:284-292`, **no passa els
eixos** — 7 arguments, cap dels dos. El motiu és al mateix docstring (`:1040-1045`): el cridador recorre
el dict de la Pèrdua 1 i «no els sap dir».

### A2.5 · Els "7 germans" — escriptors de `GradedSpec`

**Producció: UN SOL escriptor.**

| # | fitxer:línia | operació |
|---|---|---|
| 1 | `pom/services.py:1064` | `GradedSpec.objects.update_or_create(...)` — **únic camí de creació/actualització a tot el backend de producció** |
| 2 | `management/commands/clone_model_for_qa.py:157` | `.delete()` (no crea) |

**Tests (creen directament, saltant-se la porta) — els 7 germans literals:**

| # | fitxer:línia |
|---|---|
| 3 | `patterns/tests.py:2215` |
| 4 | `fitting/test_graded_table_regla.py:84` |
| 5 | `pom/test_ordre_taula_mesures.py:81` |
| 6 | `pom/test_g6_grading_gates.py:87` |
| 7 | `models_app/test_lectors_capa_onada1.py:179,185,247,249` (4 crides — les úniques que creen germanes explícitament) |
| 8 | `models_app/test_escriptors_instancia_cins.py:215` |
| 9 | `fitting/test_g6_estalitud.py:138,148` · `pom/test_g6_segell.py:136` (`.update()` / `.delete()`) |

Confirmat: **cap `bulk_create`, cap `save()` directe sobre `GradedSpec`, cap SQL cru** fora de l'ORM.

**Veredicte A2:** de 9 nodes, **1 divergeix de manera destructiva** (`_load_base_measurements`),
**2 estan continguts per àncora explícita** (`_load_model_overrides` i el seu derivat), **2 no han de
créixer mai** (les regles, per decisió de domini ja reflectida a l'esquema) i **1 ja és correcte i
espera** (`_upsert_graded_spec`).

---

## A3 · El camí complet de resolució

### A3.1 · Inventari d'entrades

**13 fitxers no-test hi apareixen; 9 punts són crides reals.** Prefix de totes les rutes: `api/v1/`
(`fhort/urls.py:46-53`).

| # | Caller | Vista | Ruta | Estat |
|---|---|---|---|---|
| **A** | `models_app/views.py:2477` / `:2507` | `generate_grading_view` `:2394` | `models/<id>/generar-grading/` (`urls.py:221`) POST | **VIU — camí principal** |
| **B** | `models_app/views.py:2828` | `escalat_ajustar_talla_view` `:2694` | `models/<id>/escalat/ajustar-talla/` (`:224`) POST | **VIU** |
| **C** | `models_app/views.py:1585` | `close_table_view` `:1558` | `models/<id>/tancar-taula/` (`:214`) POST | **VIU** |
| **D** | `extraction_views.py:1980` | `import_session_grading_preview_view` `:1949` | `import-sessions/<token>/grading-preview/` (`:86`) POST | **VIU** (no persisteix) |
| **E** | `models_app/views.py:2475` | `consolidate_base_from_fitting` | (la d'A) | **VIU** (pre-pas d'A) |
| **F** | `fitting/services.py:442` | `PieceFittingViewSet.close` | `piece-fittings/<pk>/close/` | **VIU — però NO gradua** (retirat a `fitting/services.py:463-467`) |
| G | `models_app/views.py:2664` | `set_size_override_view` `:2564` | **CAP** — jubilada (`urls.py:222-223`) | viva, sense ruta |
| H | `pom/grading_views.py:20` / `:42` | `close_base_view` / `regenerate_sizes_view` | **CAP** — jubilades (`tasks/urls.py:123-129`) | vives, sense ruta |
| I | `pom/wizard_views.py:278` | `confirm_base_size_view` `:237` | **CAP** — jubilada (`urls.py:115`) | viva, sense ruta |
| J | `clone_model_for_qa.py:111` | management command | — CLI | viu (QA) |

**Cap signal, cap tasca periòdica, cap celery dispara grading.** Les dues auto-propagacions
històriques estan retirades amb acta: `fitting/services.py:463-467` i `services_size_check.py:246-249`.

> **Nota:** quatre vistes escriptores segueixen vives i importables sense ruta HTTP. Els tests les
> exerciten (`pom/test_g6_segell.py:137`, `:173`). `confirm_base_size_view` (`wizard_views.py:266-280`)
> escriu l'estat de l'SF en **dos `save()` separats sense cap transacció**.

### A3.2 · Ordre de crida — el motor (idèntic per a tots els camins)

```
pom/services.py:166  generate_graded_specs(size_fitting_id: int)
  :184  SizeFitting.objects.select_related(...).get
  :193  _te_regles(model)                    → :647
  :206  escala_del_model(model)              → :104   (:134 run_sistema_de · :135 canonical_size_label)
  :209  _load_grading_rules(model)           → :682   → {pom_id: rule}
  :211  _load_model_overrides(model.pk)      → :711   → {(pom_id, size_label): value}   🟡 àncora :744
  :212  _poms_amb_override(...)              → :751   → {pom_id}
  :215  _load_base_measurements(model.pk)    → :774   → {pom_id: base_value}            🔴 PÈRDUA 1
  :224  _get_or_create_grading_version(sf)   → :793   (:811 sealed_active_version → raise :813)
  :227  current_version = model.measurements_version
  :233  for pom_id, base_val in base_measurements.items():        ← sense eix
  :236    for size_label in size_run:
  :242      override = model_overrides.get((pom_id, size_label))  → :248 EXCEPTION
  :250      elif pom_id in poms_nomes_override and i == base_idx  → :255 EXCEPTION
  :257      elif rule is None                                     → :270 continue (llei D2)
  :272      else _apply_rule(...)                                 → :917
  :284      _upsert_graded_spec(gv, pom, size, val, tipus, incr, ver)  🔴 PÈRDUA 2
  :298  if created == 0 → raise ValueError (:300 / :305)
  :320  SizeFitting…update(estat='TallesGenerades')
  :330  return created
```

Camí A, branca `new_version=True` (la del botó), salt a salt:

```
urls.py:221 → generate_grading_view (views.py:2394)
  :2404  _te_regles · :2413 BaseMeasurement…exists() · :2418 SizeFitting…first() [o create :2427]
  :2449  GradingVersion aprovada=True → 409 a :2458
  :2464  ModelGradingOverride…delete()                      ← LLENÇ NET, fora de transacció
  :2474  for _pf in PieceFitting(session Oberta)
  :2475    consolidate_base_from_fitting                    → fitting/services.py:354
             :382 BaseMeasurement.get_or_create(model,pom,capa,instancia)   ✅
             :391 bm.save() → signal post_save (signals.py:237) → :319 MeasurementChangeLog.create
  :2477  bump_grading_version_and_generate                  → pom/services.py:831
             :863 sealed_active_version · :876 update(is_active=False) · :880 create(v+1)
             :891 (base_changed=False → NO toca measurements_version)
             :898 generate_graded_specs                     → pom/services.py:166
  :2489  GradedSpec…count() · :2496 Watchpoint (si s'ha superat segell) · :2520 vigent_grading_version
```

### A3.3 · Transacció

**`ATOMIC_REQUESTS` NO EXISTEIX** (grep sobre tot `backend/**/*.py`: zero resultats;
`settings.py:118-127` només declara ENGINE/NAME/USER/PASSWORD/HOST/PORT). **Cap request és atòmica per
defecte.**

**El motor no obre cap transacció**: `pom/services.py` no conté ni un `transaction.atomic` ni un
`@atomic` (només mencions a comentaris `:44-46`). Escriu al nivell d'atomicitat que li doni el cridador.

**`select_for_update` / bloquejos: CAP a tot el camí.** Cap `GradingVersion`, `SizeFitting` ni
`GradedSpec` es bloqueja mai.

| Camí | Atomicitat | Escriptures FORA de transacció |
|---|---|---|
| **A · generar-grading** | **CAP** | `ModelGradingOverride.delete()` `:2464` · N× `BaseMeasurement.save()` + changelog · `GradingVersion.update/create` `:876`/`:880` · `measurements_version++` `:893` · **totes les `GradedSpec`** `:1064` · `SizeFitting.update` `:320` · `Watchpoint.create` `:2496` |
| **B · escalat** | `views.py:2773` | — (rollback explícit `:2832`/`:2835`) |
| **C · tancar-taula** | `views.py:1583` | — |
| **D · grading-preview** | — | cap escriptura |
| G | `views.py:2621` | — |
| H | **CAP** | tot |
| I | **CAP** | tres commits separats |
| J | `@atomic` `clone_model_for_qa.py:43` | — |

**Conseqüències del camí A sense transacció, amb la línia:**
- Si `bump_grading_version_and_generate` alça (guard D-1 `:865`, o `ValueError` del motor `:194`/`:300`/
  `:305`), la vista retorna 400 a `:2486` — però el **llenç net de `:2464` i les consolidacions de
  `:2475` ja estan compromesos i no es desfan**.
- Pot deixar la **v+1 creada i buida**: `:880` crea, `:898` crida el motor; si el motor alça a `:298`,
  la v+1 ja hi és i és l'activa (l'anterior ha quedat `is_active=False` a `:876`).
- Pot deixar **specs a mitges**: una excepció a la cel·la N deixa N-1 files escrites i
  `SizeFitting.estat` sense actualitzar (`:320` no s'executa).

> 🚩 Sense `select_for_update` ni `ATOMIC_REQUESTS`, **dues peticions concurrents de `generar-grading`
> sobre el mateix SF poden creuar-se a `:876-880`** i violar la invariant «una sola versió activa» que
> la migració `fitting/0016` diu que sosté el codi.

### A3.4 · Com viatgen (o no) capa i instància

**Entrada: l'eix NO entra mai pel payload.**

| Endpoint | Camps llegits del cos | capa? | instancia? |
|---|---|---|---|
| `generar-grading/` | `new_version` (`:2437`), `allow_reopen_sealed` (`:2438`) | **NO** | **NO** |
| `escalat/ajustar-talla/` | `pom_id`, `talla`, `valor` (`:2724-2726`) | **NO** | **NO** |
| `tancar-taula/` | cap camp | **NO** | **NO** |
| `grading-preview/` | `base_values` = `{pom_id: valor}` (`extraction_views.py:1969-1977`) | **NO** | **NO** |

**No hi ha cap serializer al camí**: les quatre vistes llegeixen `request.data` en cru.

**Els cinc punts on l'eix es perd:**

| | Node | fitxer:línia | Què passa |
|---|---|---|---|
| 🔴 **1** | `_load_base_measurements` | `services.py:782-787` | **NODE MESTRE.** Entren files amb els 4 eixos; surt `{pom_id: valor}`. Ni filtra ni conserva |
| 🔴 **2** | crida a `_upsert_graded_spec` | `services.py:284-292` | El destí **sap** rebre'ls (`:1022-1023`, lookup `:1064-1069`); **el cridador no els té** |
| 🔴 **3** | `preview_graded_specs` | `services.py:401` | `{pom_id: {size_label: v}}` — el wizard rep una taula per POM pelat |
| 🔴 **4** | resposta de `generar-grading` | `views.py:2525` i `:2532` | `BaseMeasurement…filter(model, is_active)` i `GradedSpec…filter(gv, pom)` **sense àncora** → `graded[spec.size_label]` (`:2533`). El que el motor separa correctament a BD es **torna a col·lapsar a la resposta** |
| 🔴 **5** | resposta d'escalat / override | `views.py:2842-2845`, `:2678-2680` | mateix patró |
| 🟡 | `_load_model_overrides` | `services.py:744` | **àncora explícita** (contenció, no propagació) |
| ⚪ | `escala_del_model`, `_apply_rule` | `:104`, `:917` | sense eix **per decisió de domini** |

**On l'eix SÍ viatja (per contrast):** `_upsert_graded_spec` lookup `:1064-1069` · signal F1
`signals.py:274-275`, `:322-323` · `consolidate_base_from_fitting` `fitting/services.py:382-383`
(llegits de `line.capa`/`line.instancia`) · `GradedSpec → PieceFittingLine` `fitting/services.py:343-344`
· literals explícits a `views.py:2630`, `:2634`, `:2648`, `:2800`, `:2811`, `:2815`, `:2822`, `:2872` i
`wizard_views.py:211-212`.

### A3.5 · Diagrama del flux

```
┌─ FRONTEND ────────────────────────────────────────────────────────────────────┐
│ endpoints.js:120 generarGrading(modelId, {new_version, allow_reopen_sealed})   │
│ endpoints.js:124 escalatAjustarTalla(modelId, {pom_id, talla, valor})          │
│ ModelFabric.jsx:110  POST tancar-taula/                                        │
│      🔴 CAP dels tres cossos porta `capa` ni `instancia` — l'eix mai entra     │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │  (cap serializer: request.data en cru)
       ┌────────────────────────┼────────────────────────┬─────────────────────┐
       ▼ A                      ▼ B                      ▼ C                   ▼ D
 urls.py:221              urls.py:224              urls.py:214          urls.py:86
 generate_grading_view    escalat_ajustar_talla    close_table_view     grading_preview
 views.py:2394            views.py:2694            views.py:1558        extraction:1949
   SENSE atomic             atomic :2773             atomic :1583         (sense escriptura)
       │                        │                        │                    │
       │ :2464 OVERRIDES.delete()  :2791/:2804          │ :1584 get_or_create│ :1969 base_values
       │   ⚠️ FORA de transacció     _write_base         │       _size_fitting│   = {pom_id:val} 🔴
       │ :2475 consolidate_base_   (literals :2872 🟡)  │ :1585 close_base   │ :1980 preview_
       │   from_fitting :382 ✅    :2798 override.delete│   services.py:460  │  graded_specs :333
       │   :391 save → F1 ✅       :2813 override upsert│   :501 exists()?   │   :401 out[pom_id] 🔴
       │ :2477 bump_grading_…      :2820 change log     │   :502 ─┐          │
       │   :876 desactiva actives                        │         │          └─▶ resposta
       │   :880 crea v+1                                 │         │
       │   :898 ─────┐            :2828 ────┐            │         │
       │ :2507 ──────┤ (in-place)           │            │         │
       └─────────────┤                      │            └─────────┤
                     ▼                      ▼                      ▼
        ╔══════════════════════════════════════════════════════════════════════╗
        ║  generate_graded_specs(size_fitting_id)      pom/services.py:166     ║
        ║  ── firma: NOMÉS un int. Cap eix pot entrar-hi ni que el tingués ──   ║
        ║  :209 _load_grading_rules → {pom_id: rule}             (sense eix ⚪)║
        ║  :211 _load_model_overrides  :744 filter(exterior,'')  🟡 ÀNCORA     ║
        ║  :215 _load_base_measurements :774                                   ║
        ║        entra BaseMeasurement(model,pom,CAPA,INSTANCIA)               ║
        ║        :782-787 surt {pom_id: valor}     🔴 PÈRDUA 1 — NODE MESTRE   ║
        ║  :233 for pom_id, base_val in …items()            ← l'eix ja no hi és║
        ║  :284   _upsert_graded_spec(...)  🔴 PÈRDUA 2 — capa/instancia NO    ║
        ╚══════════════════════════════┬═══════════════════════════════════════╝
                                       ▼
        ┌──────────────────────────────────────────────────────────────────────┐
        │ _upsert_graded_spec              pom/services.py:1014                │
        │   :1022-1023 capa/instancia SÓN paràmetres (default None / '')       │
        │   :1053-1054 capa=None → MeasurementLayer.SLUG_DEFECTE               │
        │   :1064-1069 update_or_create(gv, pom, size_label, capa, instancia)✅│
        └──────────────────────────────────────────────────────────────────────┘
                                       ▼
             fitting_gradedspec — UNIQUE (gv, pom, size_label, capa, instancia)
                     fitting/models.py:230 · CHECK capa='exterior'  :234-237
                                            CHECK instancia=''      :240-243
                                       │
        ┌──────────────────────────────┴───────────────────────────────────────┐
        │ RESPOSTA A: :2525 BaseMeasurement sense àncora  🔴 PÈRDUA 4          │
        │             :2532 GradedSpec sense àncora → graded[size_label] 🔴    │
        │ RESPOSTA B: :2842 GradedSpec sense àncora        🔴 PÈRDUA 5         │
        └──────────────────────────────────────────────────────────────────────┘

Llegenda: 🔴 l'eix es perd · 🟡 àncora explícita · ⚪ sense eix per decisió de domini · ✅ viatja sencer
```

**Veredicte A3:** l'eix **no entra mai** pel payload, es perd definitivament al node mestre `:783`, i
es torna a col·lapsar **a la sortida** encara que la BD l'hagi desat bé. El camí principal no té
transacció.

---

## A4 · On NEIX una correcció de mesura

**16 punts d'escriptura de `BaseMeasurement` a producció.** Fitxes completes a l'informe de camp; taula
resum:

| # | Punt | Fitxer:línia | Clau d'escriptura | capa/inst. a la clau? | Grading? | Changelog? | Lloc natural |
|---|---|---|---|---|---|---|---|
| 1 | Fitting · consolidate | `fitting/services.py:382,386-391` | `(model, pom, capa, instancia)` | **SÍ · COPIATS de la línia** | NO | SÍ (F1 + `fitting_ref`) | **SÍ** `:391` |
| 2 | Size check · resolve | `services_size_check.py:229,237-241` | `(model, pom, capa, instancia)` | **SÍ · COPIATS de la línia** | NO | SÍ (F1) | **SÍ** `:241` |
| 3 | Manual · set_measurements | `models_app/views.py:1810` | `(model, pom, 'exterior', '')` | SÍ però **LITERALS** | NO | SÍ / **NO** a la poda `:1838` | **SÍ** `:1818` |
| 4 | Manual · gravar_pom | `models_app/views.py:1946,1964` | `(model, pom, 'exterior', '')` | SÍ però **LITERALS** | NO | SÍ / **NO** a la poda `:1982` | **SÍ** `:1964` |
| 5 | Escalat · `_write_base` | `models_app/views.py:2872,2877` | `(model, pom, 'exterior', '')` | SÍ · LITERALS | **SÍ** `:2828` | SÍ (F1) | **SÍ** `:2877` |
| 6 | Escalat · talla no-base | `models_app/views.py:2812-2824` | override `(model,pom,size,'exterior','')` | SÍ · LITERALS | **SÍ** `:2828` | SÍ (a mà `:2820`) | SÍ `:2824` |
| 7 | **Wizard · save_base_size** | `pom/wizard_views.py:208` / **`:193-195`** | upsert complet / **`.update()` per `(model, pom_id)` SOL** | upsert SÍ · **buidatge NO** 🚨 | NO | SÍ / **NO al buidatge** | **SÍ** `:220` |
| 8 | Import · confirmar | `extraction_views.py:2566` | `(model, pom, 'exterior', '')` | SÍ · LITERALS | overrides `:2702` | SÍ / NO al DELETE `:2518` | **SÍ** `:2572` |
| 9 | Xat IA · mesures | `models_app/views.py:2337-2340/2350/2368` | PK · PK · literals | PK exacte / LITERALS | NO | SÍ / **NO a ELIMINAR** | **SÍ** `:2340` |
| 10 | Còpia model→model | `models_app/views.py:1432,1450,1465` | `(model, pom, capa, instancia)` | **SÍ · COPIATS de l'origen** | NO | SÍ (F1) | NO (`:1450`) |
| 11 | Sembra item→model | `models_app/views.py:1191,1195,1206,1223` | `(model, pom, capa, instancia)` | **SÍ · del `GarmentPOMMap`** | NO | SÍ (F1) | NO (`:1223`) |
| 12 | Federació · recepció | `tenants/federation_service.py:765,769,796` | `(model, pom, capa, instancia)` | **SÍ · de la clau del paquet** | NO | SÍ (F1) | NO (`:781`) |
| 13 | Fitxa proveïdor | `tech_sheet_views.py:367` | `(model, pom, 'exterior', '')` | SÍ · LITERALS | NO | SÍ (creació) | NO (`:381`) |
| 14 | REST genèric ViewSet | `models_app/views.py:521-523` | **PK** | PK exacte; **serializer no els exposa** | NO | SÍ (F1) | **SÍ** `:523` |
| 15 | Poda · desactivar_pom | `models_app/views.py:4041-4043,4054` | `(model_id, pom_id, is_active)` + **`.first()`** 🚨 | **NO** | NO | SÍ (`_desactivat`) | NO |
| 16 | QA · clone_model | `clone_model_for_qa.py:95` | còpia d'instància | SÍ (per còpia) | SÍ `:111` | SÍ | NO |

**Comptatge del lloc natural:** **10 dels 16** tenen punt estructural on l'increment ja és calculable
(1,2,3,4,5,6,7,8,9,14). Els altres 6 són **naixements de família**, no correccions (10,11,12,13,16), més
la poda (15).

> **El fet que decideix:** dels 10, només **DOS** coneixen els seus eixos **per còpia i no per literal**
> — `fitting/services.py:391` i `services_size_check.py:241`. Són els únics on «la família» és avui
> interrogable sense endevinar res. A `:391` hi són vius alhora `line` (que sap dir els dos eixos),
> `bm` (la fila escrita) i `bm._old_value` (posat pel `pre_save` a `signals.py:229`): **l'increment ja
> és calculable en aquest punt.**

**`measurements_version++` — només 3 punts a tot el backend:** `fitting/services.py:475-478`,
`services_size_check.py:260-263`, `pom/services.py:892-895` (i **només si `base_changed=True`**).
Cap dels 11 escriptors restants el mou.

> 🚩 **La propagació conscient NO mou `measurements_version`.** `views.py:2475` crida
> `consolidate_base_from_fitting` (que ESCRIU base) i tot seguit `bump_grading_version_and_generate(...,
> base_changed=False)` (`:2477-2479`). Com que `services.py:891` només incrementa si `base_changed`, una
> base consolidada durant «Propagar a grading» **no incrementa la versió** — i `fitting/staleness.py:105`
> compara justament amb aquest camp. A sobre, la consolidació passa **fora de tota transacció**.

> 🚨 **Cinc portes fan desaparèixer un valor SENSE deixar rastre al changelog**, mentre dues sí el
> deixen. Mudes: `wizard_views.py:195` (`.update(base_value_cm=None)`), `views.py:1838` i `:1982`
> (podes `.update(is_active=False)` → cap signal), `views.py:2368-2369` (ELIMINAR del xat IA: `save()`
> sense `_desactivat`, i el signal surt pel guard de valor-no-canviat de `signals.py:297`),
> `extraction_views.py:2518` (DELETE dur — aquest **sí** per decisió declarada a `:2508-2512`). Amb
> rastre: `views.py:4051-4054` i `extraction_views.py:2519-2524`/`:2585-2591`. **El principi del soroll
> està aplicat a 2 portes de 5.**

**Veredicte A4:** hi ha llocs naturals de sobres, però la superfície és desigual: dos punts honestos,
vuit que declaren l'eix a mà, i un (el wizard) que ni el mira.

---

## A5 · Changelog F1

Model: `MeasurementChangeLog` — `backend/fhort/models_app/models.py:824`. Taula:
`fhort.models_app_measurementchangelog`.

### A5.1 · Escriptors — són TRES, no un

| fitxer:línia | què |
|---|---|
| `models_app/signals.py:267` | la PODA (gate `_desactivat`) |
| `models_app/signals.py:319` | el CANVI DE VALOR |
| `models_app/views.py:2646` | override de talla no-base (`_editar_talla`) |
| `models_app/views.py:2820` | override de talla no-base (escalat) |

El comentari de `signals.py:307` diu «l'ÚNIC escriptor **automàtic**» — literalment cert; els dos de
`views.py` són explícits i s'hi autodeclaren (`views.py:2642-2643`). **Cap altre `signals.py` escriu
changelog** (grep sobre `tasks/`, `accounts/`, `commerce/` → 0). Els únics receivers sobre
`BaseMeasurement` són `signals.py:218` (pre_save) i `:237` (post_save).

### A5.2 · Què estampa avui — **inclosos els dos eixos**

Receivers a `signals.py:195-332`. Camins i guards:

| línia | comportament |
|---|---|
| `:250-251` | surt si el sender no és `BaseMeasurement` |
| `:252-253` | surt si `raw=True` (loaddata) |
| `:266-286` | **camí PODA** (gate `_desactivat and not created`) |
| `:290-291` | surt si `base_value_cm is None` (files `TEMPLATE`) |
| `:294-295` | surt si `not created and old_value == instance.base_value_cm` |
| `:319-332` | **camí CANVI DE VALOR** |

**`capa` i `instancia`: SÍ, des de la `instance`** (no literals):
- poda: `signals.py:274` `capa=instance.capa` · `:275` `instancia=instance.instancia`
- canvi: `signals.py:322` `capa=instance.capa` · `:323` `instancia=instance.instancia`

El comentari `:305-318` ho documenta com a tancament de FASE_3/C1-ins. **El forat anotat en sessions
prèvies («el signal F1 no estampa capa») ja NO és vigent.** Els dos escriptors de `views.py` també els
posen, però **amb literals** (`:2647`, `:2823`).

Camps de la poda (`:267-285`): `model, pom, capa, instancia, base_measurement, valor_anterior,
valor_nou=0.0, context, created_by, motiu` (defaulta a `'desactivacio'`, `:284`). **No escriu
`fitting_ref` ni `fora_de_tolerancia`.**
Camps del canvi (`:319-332`): els anteriors **més** `fitting_ref`, `motiu`, `fora_de_tolerancia`,
des de les marques d'instància `_fitting_ref`/`_motiu`/`_fora_de_tolerancia` (`:301-303`).

### A5.3 · Valors d'origen

Enum `BaseMeasurement.ORIGEN_CHOICES` (`models.py:591-611`) — **10 valors**: `STANDARD` `:592` ·
`IMPORTED` `:593` · `MANUAL` `:594` · `FITTED` `:595` · `CALCULATED` `:596` · `TEMPLATE` `:597` ·
`CHECKED` `:598` · `ITEM_STANDARD` `:599` · `COPIED` `:604` · `FEDERAT` `:610`.

Realment a staging:

```
  origen  | count          context (al changelog)  | count
----------+-------        --------------------------+-------
 TEMPLATE |   525          import                   |   229
 MANUAL   |   165          manual                   |    34
 IMPORTED |    65          checked                  |    17
 FITTED   |     4          fitting                  |     7
 CHECKED  |     1          item_standard            |     2
```

### A5.4 · `_ORIGEN_TO_CONTEXT` — 6 de 10, fallback silenciós

Transcripció sencera (`signals.py:199-210`), única definició del repo:

```python
199  # Maps BaseMeasurement.origen → MeasurementChangeLog.context.
200  _ORIGEN_TO_CONTEXT = {
201      'IMPORTED': 'import',
202      'MANUAL': 'manual',
203      'FITTED': 'fitting',
204      'CALCULATED': 'calculated',
205      'STANDARD': 'standard',
206      # Sprint B (2026-07-27) — sense aquesta entrada el context queia al fallback `origen.lower()`
207      # (:273). El resultat hi coincidiria per casualitat ('copied'), però el mapa és la font
208      # declarada del vocabulari del log i un origen viu no hi ha de faltar.
209      'COPIED': 'copied',
210  }
```

**NO mapejats (4 de 10):** `TEMPLATE`, `CHECKED`, `ITEM_STANDARD`, `FEDERAT`.

**Què passa: FALLBACK SILENCIÓS, mai KeyError.** Les dues línies que ho decideixen:
- poda `:281` → `_ORIGEN_TO_CONTEXT.get(instance.origen, (instance.origen or '').lower())`
- canvi `:327` → `_ORIGEN_TO_CONTEXT.get(instance.origen, instance.origen.lower())`

**Prova viva al corpus:** `context='checked'` (17 files) i `context='item_standard'` (2) **no surten del
mapa** — són el fallback. `TEMPLATE` no hi apareix perquè el guard de `:290-291` el talla abans, no
perquè estigui mapejat.

> 🚩 **Asimetria entre les dues línies germanes:** `:281` protegeix contra `origen=None`
> (`(instance.origen or '')`); `:327` fa `instance.origen.lower()` pelat i petaria amb `AttributeError`.
> Avui és inaccessible (columna `NOT NULL` amb default `'STANDARD'`), però no diuen el mateix.

> 🚩 **El vocabulari de `context` no està tancat.** El fallback permet que qualsevol origen nou entri
> com a `context` nou **sense tocar el mapa i sense fer soroll**, malgrat que el comentari `:206-208`
> diu que el mapa hauria de ser «la font declarada del vocabulari».

### A5.5 · Humana vs derivada — **NO EXISTEIX cap camp que ho digui**

Camps de `MeasurementChangeLog` (`models.py:835-880`): `model`, `pom`, `base_measurement`,
`valor_anterior`, `valor_nou`, `motiu`, `context`, `fitting_ref`, `fora_de_tolerancia`, `created_at`,
`created_by`, `capa`, `instancia`. **Cap és un marcador d'autoria automàtica.**

El que hi ha és INDIRECTE:
- `context` (`:844`), derivat d'`origen`. **L'única codificació explícita de la distinció viu al costat
  CONSUMIDOR, no a la fila:** `fitting/repas_views.py:76` —
  `CONTEXTOS_DE_FITTING = ('fitting', 'checked', 'manual')`, amb el comentari `:74-75`: «La resta
  (import, standard, calculated, item_standard, copied, federat) són moviments de dades, no preses».
  **La regla humana/derivada està hardcodejada en un lector.** Cada lector nou l'ha de reinventar.
- `created_by` (`:852-855`) és nullable i s'omple des de `_changed_by` (`:297`); un nul no distingeix
  «derivada» de «humana sense sessió».
- `motiu` (`:843`), text lliure sense vocabulari.
- `fitting_ref` (`:846-849`) només diu «ve d'un fitting»; queda `NULL` als overrides i a tota la poda.

### A5.6 · Cabria «derivat de»? — constatació estructural

**(a) És append-only DE FET?**

**A nivell d'instància, SÍ, amb guards durs:** `models.py:902-906` (`save()` alça `ValueError`
'MeasurementChangeLog is append-only: updates are not allowed.') i `:908-909` (`delete()` idem).

**A nivell de QuerySet i de BD, NO.** Els guards són overrides de mètode d'instància;
`QuerySet.update()`/`.delete()` i els CASCADE hi passen per sota. Camins de producció que ho travessen:

| # | fitxer:línia | què |
|---|---|---|
| 1 | `pom/management/commands/consolidate_pom_catalog.py:117` | `type(obj).objects.filter(pk=obj.pk).update(pom=dest)` sobre `FUSIO_MOVE_RELS`, que **inclou `'measurement_changes'`** (`pom/seed_data/consolidate_pom_los.py:31`, el `related_name` de `MeasurementChangeLog.pom`, `models.py:836`). **REESCRIU el `pom_id` de files ja escrites.** El comentari `:111-112` **reconeix el bypass** («evita save() — és append-only») |
| 2 | `consolidate_pom_catalog.py:257` | `getattr(m, rel).all().delete()` sobre les mateixes rels |
| 3 | `clone_model_for_qa.py:161` | `MeasurementChangeLog.objects.filter(model=model).delete()` |
| 4 | CASCADE de BD | `MeasurementChangeLog.model` és `CASCADE` (`models.py:835`); esborrar un `Model` s'endú el seu changelog sense passar per `delete()` |

A Postgres **no hi ha ni trigger ni regla** que ho impedeixi: `pg_constraint` sobre la taula només
llista 2 CHECK (les comportes), 5 FK, els NOT NULL i la PK — **cap constraint d'immutabilitat**.

**(b) Hi ha lloc on cabria un punter a la fila d'origen?**
- **FK a si mateixa: NO EXISTEIX.** Les 5 FK van a `models_app_basemeasurement`, `auth_user`,
  `fitting_sizefitting`, `models_app_model` i `pom_pommaster`.
- **JSONField: NO EXISTEIX** (cap columna `jsonb`).
- **Camp de nota lliure: SÍ** — `motiu = CharField(max_length=255, blank=True, default='')`
  (`models.py:843`). És l'únic text lliure, i ja el fan servir com a pont semàntic
  (`services_size_check.py` hi escriu `'Size check · check <pk>'`; `repas_views.py:90` constata que «no
  té camp de nota propi»).
- `base_measurement` (`:837-840`, `SET_NULL`) apunta a la **mesura**, no a una altra fila de log.

> 🚩 **Cap `post_delete` sobre `BaseMeasurement`.** Un esborrat dur no deixa fila al log; només la poda
> soft (`_desactivat`) ho fa. La FK `base_measurement` és `SET_NULL`, així que la fila històrica queda
> òrfena.

**Veredicte A5:** el log ja porta els dos eixos i té UN camp lliure. El que **no** té és cap manera
estructural de dir «derivat de», ni cap garantia real d'immutabilitat: l'append-only és una convenció
que la producció ja travessa.

---

## A6 · Enumerar la família

### A6.1 · Model i esquema

`BaseMeasurement` (`models_app/models.py:588`). `Meta` (`:740-818`), declaracions literals:

```python
754          unique_together = [('model', 'pom', 'capa', 'instancia')]
759          ordering = ['model', 'capa', 'ordre', 'pom']
760          constraints = [
781-784          CheckConstraint(Q(capa='exterior'),      name='..._capa_gate_c1')
799-802          CheckConstraint(Q(instancia=''),          name='..._instancia_gate_cins')
814-817          CheckConstraint(~Q(instancia__gt='', nom_fitxa=''), name='..._instancia_exigeix_nom')
818          ]
```

Sense `indexes = [...]`: els índexs de `capa`/`instancia` vénen dels `db_index=True` dels camps.

A Postgres, 9 índexs i 24 constraints. Els que decideixen:

```
 models_app_basemeasureme_model_id_pom_id_capa_ins_8405ced0_uniq
   | CREATE UNIQUE INDEX ... USING btree (model_id, pom_id, capa, instancia)
 models_app_basemeasurement_capa_gate_c1          | c | CHECK (((capa)::text = 'exterior'::text))
 models_app_basemeasurement_instancia_gate_cins   | c | CHECK (((instancia)::text = ''::text))
 models_app_basemeasurement_instancia_exigeix_nom | c | CHECK ((NOT (((instancia)::text > ''::text)
                                                          AND ((nom_fitxa)::text = ''::text))))
```

La FK de `pom` va a **`fhort.pom_pommaster`** (no a `public`), consistent amb el ja anotat.

### A6.2 · La consulta de germanes

ORM:
```python
BaseMeasurement.objects.filter(
    model_id=bm.model_id, pom_id=bm.pom_id, is_active=True,
).exclude(pk=bm.pk).order_by('capa', 'instancia')
```

SQL:
```sql
SELECT id, model_id, pom_id, capa, instancia, base_value_cm, nom_fitxa, ordre, origen
  FROM fhort.models_app_basemeasurement
 WHERE model_id = %s AND pom_id = %s AND is_active
 ORDER BY capa ASC, instancia ASC;
```

> 🚩 **`Meta.ordering` NO inclou `instancia`** (`:759`). Sense `.order_by()` explícit, dues germanes que
> només difereixin en instància tenen **ordre indefinit** entre elles.

### A6.3 · Cost — l'índex la cobreix

Cerca prèvia de parells amb germanes:
```
SELECT model_id, pom_id, COUNT(*) FROM fhort.models_app_basemeasurement
 WHERE is_active GROUP BY 1,2 HAVING COUNT(*)>1 ORDER BY 3 DESC LIMIT 10;
(0 rows)
```
**No n'hi ha cap**, i és estructuralment impossible avui. L'EXPLAIN va doncs sobre cardinalitat 1
(`model_id=1302, pom_id=273`):

```
 Index Scan using models_app_basemeasureme_model_id_pom_id_capa_ins_8405ced0_uniq
   on models_app_basemeasurement  (cost=0.28..8.29 rows=1) (actual time=0.185..0.187 rows=1.00 loops=1)
   Index Cond: ((model_id = 1302) AND (pom_id = 273))
   Filter: is_active
   Buffers: shared hit=5 read=1
 Execution Time: 0.271 ms
```

**Un índex existent la cobreix: cap Seq Scan.** `(model_id, pom_id)` és el **prefix exacte** del UNIQUE,
i l'`ORDER BY capa, instancia` són les columnes 3a i 4a del **mateix** índex → **no apareix cap node
Sort**. La consulta de germanes no demana cap índex nou.

### A6.4 · Estadística del corpus

```
 total_files | actives | parells_model_pom | capes_distintes | instancies_distintes
-------------+---------+-------------------+-----------------+----------------------
         760 |     685 |               760 |               1 |                    1

 parells_amb_2mes | files_amb_germana_per_capa | files_amb_germana_per_instancia
------------------+----------------------------+---------------------------------
                0 |                          0 |                               0

   capa   | instancia | count        (measurementchangelog)
 exterior |           |   760          exterior | '' | 289
```

**760 files, 760 parells `(model,pom)` distints → cardinalitat exactament 1.** Zero famílies. Una capa,
una instància. `los.models_app_basemeasurement` = **0 files**.

### A6.5 · On es faria la consulta

Constant canònica de la capa: `MeasurementLayer.SLUG_DEFECTE = 'exterior'` (`pom/models.py:223`).
**NO EXISTEIX constant equivalent per a la instància única**: el `''` és literal a tot arreu (grep de
`INSTANCIA_UNICA|SLUG_UNICA` → 0 resultats).

Els punts d'A4 ja tenen `model_id` i `pom_id` a mà (v. taula d'A4). Els dos on la fila escrita
**coneix els seus propis eixos per còpia** — i per tant on la família és interrogable sense endevinar —
són `fitting/services.py:391` i `services_size_check.py:241`.

**Veredicte A6:** enumerar la família és **barat i ja indexat**; no cal esquema nou. El que falta no és
la consulta, és que hi hagi germanes i que el lector del motor les sàpiga demanar.

---

## A7 · Contractes

### A7.1 · La cadena, endpoint a endpoint

| # | Endpoint | Vista (fitxer:línia) | `capa` | `instancia` |
|---|---|---|---|---|
| 1 | `/api/v1/base-measurements/` (ViewSet) | `models_app/views.py:497` · serializer `serializers.py:389`, fields `:403-411` | **NO** | **NO** |
| 2 | `GET models/{id}/base-measurements/` | `pom/wizard_views.py:322` (dict a mà `:368-401`) | **NO** | **NO** |
| 3 | `GET models/{id}/base-measurements-units/` | `pom/s6_views.py:77` | **NO** (ancorat `:94-96`) | **NO** (ancorat) |
| 4 | `POST models/{id}/set-measurements/` | `models_app/views.py:1780` | **NO** — literal `:1806` | **NO** |
| 5 | `PATCH base-measurements/{id}/noms/` | `models_app/views.py:2954` | **NO** | **NO** |
| 6 | `POST models/{id}/base-measurements/reorder/` | `models_app/views.py:2921` | **NO** | **NO** |
| 7 | `GET models/{id}/base-stages/` | `models_app/views.py:3015` (fila `:3105-3123`) | **NO al payload** (clau interna 3-tupla `:3076`,`:3087`,`:3100`) | **NO al payload** |
| 8 | `POST models/{id}/escalat/ajustar-talla/` | `models_app/views.py:2690` (`linies` id `f'{pom.id}:{s}'` `:2845-2847`) | **NO** | **NO** |
| 9 | `POST models/{id}/generar-grading/` | `models_app/views.py:2394` | **NO** | **NO** |
| 10 | **motor** | `pom/services.py:166` / `:333` | **NO — LA CLAU DEL MOTOR** | **NO** |
| 11 | `GET size-fittings/{id}/taula-mesures/` | `pom/grading_views.py:89` | **NO** (ancorat `:135`) | **NO** (ancorat) |
| 12 | `GET fitting/{id}/graded-table/` | `fitting/graded_spec_views.py:22` (filtre fix `:48`, `:107`) | **NO** | **NO** |
| 13 | `POST import-sessions/{token}/grading-preview/` | `extraction_views.py:1949` | **NO** | **NO** |

**Fet dur: cap serializer del repo declara `capa` ni `instancia` a `fields`.** L'única
`Meta.model = BaseMeasurement` de tot `backend/` és `models_app/serializers.py:402`. I
`BaseMeasurementViewSet.filterset_fields` (`views.py:508`) tampoc: `['model','pom','is_active','origen']`.
**Cap client pot avui ni llegir ni triar l'eix d'una mesura per la porta genèrica.**

Els dos eixos només viuen en **claus internes de lectura**: `fitting/serializers.py:278-282` i `:287`,
`serializers_size_check.py:90-91` i `:102`, `pom/s10_views.py:43-47`, `models_app/views.py:3076/3087/3100`.

**Està declarat com a DECISIÓ, no com a oblit** — `pom/grading_views.py:120-124`:
> «No pot ser clau composta: `cells` es serialitza tal qual a la resposta (`{str(k): v}`) i `poms_info`
> porta l'`id` del POM — **la clau ÉS el contracte, i el contracte no es toca fins a C4**.»

### A7.2 · Quins payloads haurien de créixer — CONSTATACIÓ DE SUPERFÍCIE

> Marcat com a tal: només s'identifica **on no hi ha lloc**. No es dissenya cap camp ni cap esquema.

**Avui NO EXISTEIX cap endpoint HTTP amb semàntica d'«afectacions + acceptar/desmarcar».** L'únic
precedent de proposta amb dry-run és una management command (`seed_scope_nodes_proposals`), no una API.

| Fitxer:línia | Cos actual | Per què no hi cap |
|---|---|---|
| `views.py:1844-1846` | `{created, updated, deactivated, errors}` | escalars + llista d'strings; cap estructura per fila afectada |
| `views.py:2846-2847` | `{ok, propagat, motiu, grading_version_id, linies}` | `propagat` és **booleà**, `motiu` string; `linies` porta id `f'{pom.id}:{talla}'` — **no pot nomenar una germana** |
| `views.py:3008-3013` | `{id, nom_canonic_model, nom_traduit_model, updated_at}` | resposta d'una sola fila |
| `serializers.py:403-411` | `BaseMeasurementSerializer.fields` | l'únic escriptor per API; ni pot rebre ni retornar els eixos |
| `extraction_views.py:1983-1985` | `{grading, base_size, size_run, avisos}` | `avisos` és `list[str]` (`:1979`) — text, no afectacions accionables |
| `grading_views.py` (`measurements_table_view`) | `{poms[], cells{str(pom_id): …}}` | **la clau del payload ÉS `pom_id`** |
| `views.py:3105-3123` | fila de `base-stages` | el pin `test_base_stages_no_regressio.py:75-82` fixa el joc EXACTE de claus |

Entrades que tampoc ho poden expressar: `set-measurements` identifica per `pom_id` i poda per
`keep_pom_ids` (`:1786-1790`, `:1836-1840`); `escalat/ajustar-talla` rep `{pom_id, talla, valor}`
(`:2693`); `grading-preview` rep `{base_values: {pom_id: valor}}` (`extraction_views.py:1969`).

### A7.3 · El green flag CEC — la causa és d'una sola línia

**Com es genera:** `drf-spectacular==0.29.0` (`requirements.txt:12`), `settings.py:51` a
`INSTALLED_APPS`, `settings.py:229` `DEFAULT_SCHEMA_CLASS = AutoSchema`, `SPECTACULAR_SETTINGS`
`:247-254`, servit a `urls.py:41`. `drf_yasg`/`SchemaGenerator`: **NO EXISTEIX**.
**Cap fitxer d'esquema commitat** (`git ls-files | grep -iE "openapi|swagger|schema.*\.(ya?ml|json)"` → 0).

**LA RAÓ TÈCNICA:** `grep -rn "@extend_schema" backend/` (fora del venv) → **0**. Les úniques dues
importacions de `drf_spectacular` del codi d'aplicació són `urls.py:3` i `urls_public.py:10`.
**L'esquema és 100% inferència d'`AutoSchema`**, que només fabrica `requestBody` on hi ha
`serializer_class`. Per tant **cada `@api_view` i cada `APIView` sense `serializer_class` surt sense cos
declarat**. Recompte: **148 `@api_view` en 28 fitxers; 19 subclasses `APIView`, cap decorada**.

Mesura contra l'esquema viu (HTTP 200, **745 469 bytes, 365 paths**, 214 ocurrències de
`No response body`). Endpoints de la cadena **sense `requestBody` ni `2xx` amb `content`**, amb la raó:

| Endpoint | raó tècnica |
|---|---|
| `models/{id}/set-measurements/` POST | `@api_view` `views.py:1778-1780` |
| `models/{id}/generar-grading/` POST | `@api_view` `:2392-2394` |
| `models/{id}/escalat/ajustar-talla/` POST | `@api_view` `:2690` |
| `models/{id}/base-stages/` GET | `@api_view` `:3015` |
| `models/{id}/taula-mesures/` GET | `@api_view` |
| `size-fittings/{id}/taula-mesures/` GET | `@api_view` `grading_views.py:87-89` |
| `fitting/{id}/graded-table/` GET | `APIView` sense `serializer_class` `graded_spec_views.py:22` |
| `fitting/model/{id}/repas/` GET | `APIView` sense `serializer_class` `repas_views.py:177` |
| `models/{id}/base-measurements/` GET | `@api_view` `wizard_views.py:320-322` |
| `models/{id}/base-measurements-units/` GET | `@api_view` `s6_views.py:77` |
| `models/{id}/base-measurements/reorder/` POST | `@api_view` `:2921` |
| `base-measurements/{id}/noms/` PATCH | `@api_view` `:2954` |
| `import-sessions/{token}/{9 accions}` POST/PATCH | `@api_view` (9 de 9) |
| `grading-rule-sets/{id}/regles/…` PATCH/GET | `@api_view` |
| **contrast:** `base-measurements/` i els 12 ViewSets de `pom/views.py` | **SÍ** tenen forma (serializer inferit) |

**Mutadores de la cadena sense `requestBody`: 32.**

**El contracte no exposa `capa` enlloc — reconfirmat al YAML de 745 KB:** els únics 2 hits de `capa`
són `punts_per_capa` (`:22382`, capes de dibuix DXF de `patterns` — homònim); `instancia` surt 2 cops,
tots dos **dins de text de docstring** (`:9340`, `:9968`). **Cap propietat de cap component.**
Component `BaseMeasurement` → `['base_value_cm','id','is_active','model','nom_fitxa','notes','origen',
'pom','pom_*','updated_at']`.

**La xifra prèvia del MAPA_TOC** (`MAPA_TOC_INSTANCIA.md:49-52`: «54 dels 80 endpoints (68%) declaren
`No response body`»): **CONFIRMADA en substància, DENOMINADOR NO REPRODUÏBLE.**
- Verificats **un per un** els 11 grups que el doc enumera a `:574-578`: **tots** són cecs. **Cap fals
  positiu.** El doc encerta fins i tot el matís fàcil de perdre (`models/{id}/base-measurements/`, no el
  ViewSet `/api/v1/base-measurements/`, que **sí** té forma declarada).
- **No reproduïble**: el doc no publica la llista dels 80 paths i l'esquema ha crescut (364→365 paths).
  Mesura amb criteri propi: **63/99 = 64%** — mateix ordre, denominador diferent.
- **Matís de vocabulari**: la xifra del doc és sobre **RESPONSE** body; la pregunta del brief («cos
  buit») dona **32 mutadores sense REQUEST body**. Les dues són certes i no s'han de barrejar. La
  conseqüència operativa que el doc treu a `:580-582` val per als dos sentits.

**Veredicte A7:** el contracte HTTP és, avui, l'única capa on l'eix **no existeix en absolut** — ni al
payload, ni al serializer, ni a l'esquema. I l'esquema no ho pot detectar mai perquè no hi ha **cap**
`@extend_schema` al repo.

---

## A8 · Tests i pins

> **Execució: IMPOSSIBLE en aquest entorn.** Un sol intent
> (`venv/bin/python manage.py test fhort.models_app.test_lectors_instancia_cins`). Error literal:
> ```
> File ".../django/db/backends/base/creation.py", line 232, in _create_test_db
>     confirm = input("Type 'yes' if you would like to try deleting the test database '%s'…")
> EOFError: EOF when reading a line
> ```
> No s'hi ha insistit. **Tota l'anàlisi d'A8 és ESTÀTICA.** (Consistent amb el 🚩 ja anotat a memòria:
> la BD de test no es pot construir des de zero.)

### A8.1 · Els sis artefactes demanats

| Artefacte | Què afirma | Germanes? |
|---|---|---|
| `models_app/test_base_stages_no_regressio.py` (294 ln) | **EL PIN.** Docstring `:7-11`: «no és un test del comportament: és un PIN. Fixa la resposta sencera camp a camp i en ordre». **`:75-82`** joc EXACTE de 13 claus de fila — **`capa`/`instancia` NO hi són**. També `:69`, `:84`, `:96`, `:103`, `:139-141`, `:177`, `:190` | **NO** |
| `models_app/test_lectors_capa_onada1.py` (317 ln) | Harness `comporta_alcada()` `:36-52` (DROP CONSTRAINT dins savepoint revertit). **`_dues_capes_de_base()` `:84-96`**. Asserts `:115-117`, `:144-149`, `:194-196`, **`:240-242`/`:256-257`** (`cells[str(pom)]['M']==100.0` per les DUES portes), `:297-300`, `:316` (cens 9 comportes) | **SÍ · 2** |
| `models_app/test_lectors_instancia_cins.py` (295 ln) | Docstring `:9-12`: «un lector que hagués crescut a `(pom, capa)` i s'hi hagués quedat passa TOTS els tests d'Onada 1 i col·lapsa igualment. **La tercera fila és la que ho detecta**». **`_tres_germanes()` `:90-107`**. Asserts `:121-124`, `:148-160`, `:195-204`; cara B (lectors ancorats) `:230-232`, `:256-258`, `:273-275`; `:294` | **SÍ · 3** |
| `pom/tests.py` (281 ln) | **Fora de la zona.** Cap `BaseMeasurement`, cap `GradedSpec`, cap grading. Guard d'àlies `:39-167` i sembres de catàleg `:170-281` (**`:265-266`** `primera.slug == SLUG_DEFECTE == 'exterior'`) | **NO** |
| `scripts_tmp/c1_fumeig_base_stages.py` (50 ln) | Termòmetre read-only, **cap assert**. Contracte `:4-5`: «**T0 i T5 han de ser BYTE-IDÈNTICS**». Comparació externa per md5 | — |
| `scripts_tmp/golden_163_snapshot.py` (37 ln) | **El golden, i és col·lapsat.** `:23-24` loader→preview; **`:28` `flat[f'{pom_id}|{size}']`**; `:31` `'n_poms': len(specs)` | — |

### A8.2 · Harness de germanes — cens exhaustiu

**Només 5 fitxers a tot `backend/**/test*.py`, tots a `models_app/`:**

| Fitxer | Germanes | Línia | Què n'espera |
|---|---|---|---|
| `test_escriptors_instancia_cins.py` | **SÍ · 3** | `:67`, `:69-71`, `:72-74` | La 3-tupla com a esperada: `:89` · **`:132` `assertEqual(n, 3, 'una línia per germana, no una per POM')`** · `:181-183` · `:190` `count()==3` · `:191-193` |
| `test_lectors_instancia_cins.py` | **SÍ · 3** | `:98-106` | (v. A8.1) |
| `test_lectors_capa_onada1.py` | **SÍ · 2** | `:90-95` | (v. A8.1) |
| `test_capa_comporta_c1.py` | NO (`assertRaises`) | `:63-66`, `:74-81` | Que la comporta les **barri** |
| `test_instancia_comporta_cins.py` | NO (`assertRaises`) | `:106-110`, `:118-126` | Que la comporta les barri |

> 🚨 **ZERO harness de germanes a `fhort/pom/`, `fhort/fitting/`, `fhort/patterns/`, `fhort/tenants/`.**
> El motor (`pom/services.py`) **no té ni un sol test amb dues files del mateix `(model, pom)`**. Els
> seus tests creen sempre un POM per fila. **El motor està verd perquè mai no ha vist una germana.**

### A8.3 · Tests que afirmen el col·lapse com a ESPERAT

| fitxer:línia | Test | Assert |
|---|---|---|
| `models_app/test_seccio_captura.py:172` | `SeccioBaseMeasurementTest::test_DUES_SECCIONS_AMB_EL_MATEIX_POM_COL·LAPSEN` | `assertEqual(files.count(), 1, 'la clau encara col·lapsa: si això falla, la clau ha canviat')` — docstring `:165-166`: «hi és perquè el dia que algú toqui la clau, ho vegi caure aquí i sàpiga que era conegut». **El pin deliberat.** |
| `pom/test_g6_grading_gates.py:152` | `GateDeLesReglesResidentsTest::test_el_preview_diu_el_MATEIX_que_el_generador` | dict literal `{self.pom.id: {...}}` |
| `pom/test_d2_nomes_override.py:135-136` | `PomNomesOverrideGraduaTest::test_preview_diu_el_mateix_que_el_generador` | `prev[<int>]` |
| `pom/test_ordre_taula_mesures.py:111-115` | `OrdreTaulaMesuresTest::test_les_celles_segueixen_l_ordre_dels_poms` | claus de `cells` == `str(pom_id)` |
| `models_app/test_lectors_capa_onada1.py:240`,`:256` | `test_c7_la_taula_de_mesures_no_barreja_les_capes…` | amb 2 germanes, n'espera UNA cel·la |
| `models_app/test_lectors_instancia_cins.py:230`,`:256`,`:273` | 3 tests de lectors ancorats | `count==1`/`total==1` **amb 3 germanes vives** — col·lapse com a contracte deliberat via àncora |
| `models_app/test_base_stages_no_regressio.py:75-82` | `test_la_forma_de_cada_fila_es_exactament_aquesta` | joc EXACTE de claus |
| `fitting/test_repas.py:106`,`:128`,`:286` | 3 tests | `pom_id` pelats / `{r['pom_id']: r}` |
| `patterns/tests.py:3342`,`:3404` | 2 tests | `{codi_client: fila}` · `total == 2` |
| `tenants/tests_enviament_feina.py:155-157` | `test_enviament_complet` | `{codi_global: bm}` |
| `models_app/test_size_check_completa_linies.py:53,59,100,113,121` | 5 mètodes | «una línia per POM» |
| `scripts_tmp/golden_163_snapshot.py:26-31` | (script) | `f'{pom_id}|{size}'` + `n_poms` |

### A8.4 · Què cau si la clau del motor passa a `(pom_id, capa, instancia)`

**Context mecànic:** `services.py:233` itera el dict; dins del bucle, `rules.get(pom_id)` (`:234`, dict
d'`int` de `:702`/`:705-707`), `model_overrides.get((pom_id, size_label))` (`:242`, clau de `:741`),
`pom_id in poms_nomes_override` (`:250`, set d'`int` de `:771`) i `_upsert_graded_spec(pom_id=…)` (FK).
**Si `_load_base_measurements` emet tuples i res més es mou, tots els POMs cauen a `rule is None` → cap
cel·la.** `preview_graded_specs` té la mateixa forma.

**A · CAU DUR** (asserten literalment la forma col·lapsada):

| `fitxer::Classe::metode` | Raó |
|---|---|
| `pom/test_g6_grading_gates.py::GateDeLesReglesResidentsTest::test_el_preview_diu_el_MATEIX_que_el_generador` | `:152` dict literal clavat a `{int: …}` |
| `pom/test_d2_nomes_override.py::PomNomesOverrideGraduaTest::test_preview_diu_el_mateix_que_el_generador` | `:135-136` `prev[<int>]` → `KeyError` amb clau 3-tupla |
| `pom/test_ordre_taula_mesures.py::OrdreTaulaMesuresTest::test_les_celles_segueixen_l_ordre_dels_poms` | `:111-115` claus de `cells` == `str(pom_id)` |
| `models_app/test_seccio_captura.py::SeccioBaseMeasurementTest::test_DUES_SECCIONS_AMB_EL_MATEIX_POM_COL·LAPSEN` | `:172` `count()==1` amb el missatge «si això falla, la clau ha canviat» |
| `models_app/test_base_stages_no_regressio.py::BaseStagesNoRegressioTest::test_la_forma_de_cada_fila_es_exactament_aquesta` | `:75-82` joc EXACTE: qualsevol eix nou al payload el trenca |
| `fitting/test_repas.py::FittingRepasAPITest::test_files_en_ordre_de_fitxa` | `:106` llista de `pom_id` pelats |
| `fitting/test_repas.py::FittingRepasAPITest::test_ultim_comentari_per_pom_quan_lultima_sessio_no_comenta_tot` | `:128` `{r['pom_id']: r}` |
| `fitting/test_repas.py::FittingRepasEtapesTest::test_una_etapa_no_arrossega_POMs_que_ningu_va_tocar` | `:286` idem |
| `patterns/tests.py::LlistaDeTreballAPITest::test_la_tolerancia_de_la_mesura_mana_sobre_la_del_cataleg` | `:3342` `{codi_client: fila}` fusiona germanes |
| `tenants/tests_enviament_feina.py::EnviamentFeinaTest::test_enviament_complet` | `:155-157` `{codi_global: bm}` + `mesures==2` |
| `tenants/tests_enviament_feina.py::EnviamentFeinaTest::test_la_marca_es_sobirana_del_seu_schema` | `:211`,`:214` `.get(model=twin, pom=…)` com a identitat única |
| `scripts_tmp/golden_163_snapshot.py` (script) | `:26-31` la cel·la del golden és `f'{pom_id}|{size}'` |
| `scripts_tmp/c1_fumeig_base_stages.py` (script) | `:4-5` exigeix bytes idèntics |

**B · CAU PER RETIRADA DE COMPORTES** (existeixen **per** caure aleshores; declarat als docstrings
`test_capa_comporta_c1.py:15` i `test_lectors_instancia_cins.py:18`):

`test_capa_comporta_c1.py::test_una_mesura_base_de_folre_no_entra` (`:63-66`) ·
`::test_una_linia_de_size_check_de_folre_no_entra` (`:68-72`) ·
`::test_tampoc_hi_entra_per_update_massiu` (`:74-81`) ·
`::test_les_nou_comportes_existeixen_a_la_bd` (`:94-105`) ·
`test_instancia_comporta_cins.py::test_una_mesura_base_amb_instancia_no_entra` (`:106-110`) ·
`::test_una_linia_de_size_check_amb_instancia_no_entra` (`:112-116`) ·
`::test_tampoc_hi_entra_per_update_massiu` (`:118-126`) ·
`::test_els_dos_eixos_son_independents` (`:147-148`) ·
`::test_les_nou_comportes_existeixen_a_la_bd` (`:153-164`) ·
`::test_les_dues_families_de_comporta_conviuen` (`:177`) ·
`::test_la_comporta_torna_a_estar_viva` (`:244-251`) ·
`test_lectors_capa_onada1.py::test_la_comporta_torna_a_estar_viva` (`:316`) ·
`test_lectors_instancia_cins.py::test_les_dues_comportes_tornen_a_estar_vives` (`:294`) ·
`test_escriptors_instancia_cins.py::test_les_comportes_tornen_a_estar_vives` (`:271-280`).

**C · CAU CONDICIONAL** (passen mentre el fixture no tingui germanes; el dia que en tingui són falsos):

`test_size_check_completa_linies.py` (5 mètodes: `:53`,`:59`,`:100`,`:111/113`,`:121`,`:129`) ·
`test_copia_model_a_model.py::CopiaValorsTest::test_subconjunt_pom_ids` (`:181`,`:184`) i
`::test_copy_values_false_deixa_la_pertinenca_sense_valor` (`:205`) ·
`test_g1_graduacio.py::DesarMesuresNoFabricaReglesTest::…` (`:163-164`) i
`::SenseGraduacioNoPetaResTest::…` (`:187`) ·
`patterns/tests.py::LlistaDeTreballAPITest` (`:3311`, `:3404`, `:3410`) ·
`tenants/tests_enviament_feina.py` (`:187`, `:235`, `:239`) ·
`pom/test_g6_segell.py::IntegritatDelMotorTest` (`:209`, `:219` — `== 9`, «3 POMs × 3 talles»).

> 🚨 **CONTRADICCIÓ DE PINS.** `test_escriptors_instancia_cins.py:132` afirma **n == 3** («una línia per
> germana, no una per POM»); `test_size_check_completa_linies.py:53/59/100/113/121` afirmen **n == 1 /
> n == 2** sobre la mateixa materialització de `SizeCheckLine`. **Avui conviuen només perquè les
> comportes impedeixen el cas. El dia que caiguin, un dels dos fitxers menteix.**

**D · FRÀGILS** (no cauen amb el canvi de clau; cauen quan el fixture creï la primera germana —
`.get(model=…, pom=…)` sense eixos → `MultipleObjectsReturned`, o `.update()` que escriu de més):
~40 punts a `pom/test_d2_nomes_override.py:116` · `pom/test_guarda_rang_mesura.py:140`,`:151` ·
`pom/test_step_conserva_valors.py:174` · `fitting/test_g6_estalitud.py:50`,`:91`,`:160-161`,`:181` ·
`models_app/tests_sembra_grading.py` (≈15 `.get(model,pom)` + 3 sets per `pom_id`) ·
`test_copia_model_a_model.py:114`,`:123`,`:134`,`:165`,`:175` · `patterns/tests.py:2203-2208`.

**E · COST ZERO:** `pom/test_espai_de_sistema.py` (17) · `pom/test_arestes_tea205.py` (13) ·
`models_app/test_parser_excel.py` (10 classes) — tots `SimpleTestCase` sense BD · `pom/tests.py` (14,
fora de zona) · `fitting/test_graded_table_regla.py` (7) ·
**`test_escriptors_instancia_cins.py` (excepte `:271-280`) — ja asserta la 3-tupla: és la referència de
destí, no cost.**

### A8.5 · CI / hooks — **NO EXISTEIX cap automatisme**

Evidència exhaustiva: `.github/` no existeix · cap `settings.json` de projecte a `.claude/`, i
`grep -rn "hooks" .claude/` → 0 · cap Makefile · `package.json` de `frontend` i `frontend-backoffice`
sense script `test` · `.pre-commit-config.yaml`, `.husky/`, `.gitlab-ci.yml`, `tox.ini`, `pytest.ini`,
`setup.cfg`, `pyproject.toml`, `Jenkinsfile`, `.circleci/`, `conftest.py` → **cap existeix** ·
`.git/hooks/` només `.sample` · cap `.sh` al repo · `crontab -l` → cap · `/etc/systemd/system/
ftt-staging.service:11` només arrenca gunicorn.

Els **55 hits** de `manage.py test` al repo són **tots documentació** (46 docstrings dels propis tests +
9 `.md` amb receptes manuals). `CLAUDE.md` no conté la paraula «test»; la porta dura que sí existeix és
`manage.py check` (`.claude/agents/verificador.md:11`).

**Veredicte A8:** hi ha vigilància escrita i és bona — però **no la corre ningú automàticament, i en
aquest entorn ni tan sols es pot córrer a mà**. Els dos artefactes que sí detectarien un canvi de forma
(perquè l'OpenAPI no pot) són **tots dos scripts manuals i tots dos col·lapsats**.

---

## A9 · Residual trio (+1)

### A9.1 · Propagació `.update()` per POM sol — **VIU**

`backend/fhort/fitting/views.py:665-667`, dins de `PieceFittingLineViewSet.propagar` (acció `:594`,
def `:595`):

```python
(PieceFittingLine.objects
 .filter(piece_fitting=pf, pom=line.pom, size_label=sl)
 .update(valor_real=val))
```

El filtre porta `piece_fitting` i `size_label` però **NO `capa` ni `instancia`**. La clau declarada del
model és `('piece_fitting','pom','size_label','capa','instancia')` (`fitting/models.py:425`): el filtre
és **estrictament més ampli que la identitat**. El `.update()` és queryset-level → **no dispara cap
signal**; `valor_teoric` no es toca (documentat a `:596-598`). Transacció: `:663`.

**El germà de LECTURA té el mateix forat:** `fitting/views.py:626-628`, `_resp()` retorna
`filter(piece_fitting=pf, pom=line.pom)` sense eixos → la resposta que refresca la graella barrejaria
germanes.

**Abast real avui (SELECT):**
```
fhort.fitting_piecefittingline
  files_totals ............................................. 153
  DISTINCT (piece_fitting, pom, size_label) ................ 153
  DISTINCT (piece_fitting, pom, size_label, capa, instancia)  153
  grups amb >1 fila per la clau cega ......................... 0
los.fitting_piecefittingline ................................. 0
```
→ **el filtre cec i el complet seleccionen el mateix conjunt: 1 fila per crida.** Latent, no actiu.

### A9.2 · Id sintètic `'pom:talla'` — **VIU**

És l'**únic** generador d'aquesta forma a tot el projecte (grep exhaustiu backend + frontend).

**GENERA:**
- `backend/fhort/models_app/views.py:2845` —
  `linies = [{'id': f'{pom.id}:{s}', 'valor_real': graded.get(s)} for s in size_run]`
- `frontend/src/components/model/fittingGridAdapter.jsx:144` —
  ``active: { lineId: `${row.pom_id}:${s}`, … }`` (dins `buildEscalatRows` `:136`, contracte al
  comentari `:123`)

**CONSUMEIX:**
- `frontend/src/components/model/MeasureGrid.jsx:365-372` — l'id és la clau del mapa `vals`
- `frontend/src/pages/PropagatedEditor.jsx:68-71` — **es desmunta de tornada**:
  `lastIndexOf(':')` → `pomId` + `talla` → `escalatAjustarTalla(modelId, pomId, talla, value)`

**Col·lapsa germanes? SÍ, inequívocament, i el cicle es tanca als dos extrems:**
1. **A la font**: `fittingGridAdapter.jsx:144` neix d'una fila de `measurements_table_view`, i aquesta
   ja col·lapsa abans — `models_app/views.py:1652-1658` construeix
   `graded_by_pom[spec.pom_id][spec.size_label]` **sense els eixos** (l'últim `GradedSpec` iterat guanya).
   Mateix patró a `:2841-2844`.
2. **Al retorn**: `PropagatedEditor.jsx:71` només pot recompondre `(pomId, talla)`, i
   `escalat_ajustar_talla_view` acaba als literals de `_write_base` (`views.py:2872`).

**Contra-cas verificat:** la graella de FITTING **no** té el problema — `fittingGridAdapter.jsx:47` usa
`lineId: line.id`, la PK real de `PieceFittingLine`.

### A9.3 · `desactivar_pom` desactiva una instància arbitrària — **VIU**

`desactivar_pom_view`, `models_app/views.py:4027` (ruta `models_app/urls.py:233`,
`models/<int:model_id>/pom/<int:pom_id>/desactivar/`). Queryset (`:4041-4043`):

```python
bm = (BaseMeasurement.objects
      .filter(model_id=model_id, pom_id=pom_id, is_active=True)
      .select_related('pom').first())
```

**Per què és arbitrària:** és un **`.first()` sobre un filtre sense `capa` ni `instancia`** (`:4042`).
No és un `.update()` massiu — en toca exactament UNA — però **quina és un artefacte d'ordenació**: el
`Meta.ordering` és `['model','capa','ordre','pom']` (`models.py:754`) i **`instancia` no hi surt**, de
manera que entre dues germanes de la mateixa capa el desempat el fa el planner de Postgres.

L'escriptura és a `:4054` (`bm.save(update_fields=['is_active'])`), precedida de `_desactivat=True`
(`:4051`) → **sí genera entrada al changelog**… **atribuïda a la germana que el `.first()` hagi triat**.
I aquella taula és append-only (`models.py:905`): **la fila mal atribuïda no es podrà corregir després.**
Cap transacció: la view no té `atomic`.

**Abast avui:** 685 files actives, 685 claus `(model,pom)`, 685 claus completes → 0 grups amb germanes.
El `.first()` és determinista **per manca d'alternativa**.

### A9.4 · 🚨 EL QUART — no estava al brief, i és el pitjor de la família

**`backend/fhort/pom/wizard_views.py:193-195`**, dins de `save_base_size_view` (def `:156`), camí
`valor == 0/None`:

```python
BaseMeasurement.objects.filter(model=model, pom_id=pom_id).update(base_value_cm=None)
```

**És l'ÚNIC escriptor de `BaseMeasurement` de tot el backend amb lookup cec als DOS eixos.** Tots els
altres 15 punts d'A4 o bé copien els eixos de la fila d'origen o bé els declaren amb literals (l'altre
camí d'aquesta mateixa vista, `:208-219`, sí que els declara).

Acumula els tres defectes alhora:
- **filtre cec**: amb germanes vives buidaria TOTES les files de `(model, pom)` de qualsevol capa i
  qualsevol instància;
- **`.update()` de queryset**: **no dispara cap signal** → buidar un valor pel wizard **no deixa cap
  entrada al `MeasurementChangeLog`** (ni per valor ni per poda: no hi ha `_desactivat`);
- **cap transacció**: `grep -c transaction.atomic wizard_views.py` = **0**.

Abast avui: 685 files actives, 1 fila per grup → 0 germanes col·laterals.

**Veredicte A9:** els tres deutes del brief segueixen vius amb les línies actualitzades, n'hi ha un
quart de pitjor, i **cap dels quatre fa dany avui** — els quatre esperen la primera germana.

---

## A10 · Prova real de dues germanes

**Sonda executada** dins d'una transacció revertida per excepció (`_Rollback`), amb
`schema_context('fhort')`, reutilitzant el patró de `scripts_tmp/golden_163_snapshot.py` i
`c1_fumeig_base_stages.py`. Script al scratchpad, **mai al repo**. `git status` net.

**Tria del model:** el **163 està SEGELLAT** (`GV 81 · v3 · aprovada=True`) i
`_get_or_create_grading_version` hi hauria petat amb `SealedGradingVersionError` abans d'arribar enlloc.
S'ha triat el **396** (`LOS-SS27-0122`, el cas de la instància): 20 BaseMeasurements actives amb valor,
20 regles residents, `SizeFitting 171` en `TallesGenerades`, `GradingVersion 77 · v1 · aprovada=False`
amb 120 specs.

### A10.1 · Verificació de rollback — procés NOU

| comptador | ABANS | DESPRÉS |
|---|---|---|
| `BaseMeasurement.objects.count()` | 760 | **760** |
| `GradedSpec.objects.count()` | 2061 | **2061** |
| `GradingVersion.objects.count()` | 34 | **34** |
| BM del model 396 | 20 | **20** |
| GradedSpec de GV 77 | 120 | **120** |
| `SizeFitting 171.estat` | `TallesGenerades` | **`TallesGenerades`** |
| `max(BaseMeasurement.id)` | 2074 | **2074** |
| `max(GradedSpec.id)` | 6602 | **6602** |

Comprovació de **valor**, no només de recompte: la cel·la que la sonda va sobreescriure a 999.0 dins de
la transacció torna a llegir-se `GS id=4259 pom=299 03/06 valor=1.5 FIXED capa='exterior' instancia=''`;
`BM 1677 valor = 1.5`. **Cap fila nova, cap valor mutat.** (Els ids 2097-2099 i 6615-6616 dels `DETAIL`
són ids de seqüència reservats i descartats — comportament normal de Postgres, no files.)

### A10.2 · Es pot crear la germana? — les quatre proves, literals

```
>>> EIX CAPA · BaseMeasurement germana amb capa='folre'
    EXCEPCIO: django.db.utils.IntegrityError
      | new row for relation "models_app_basemeasurement" violates check constraint
      | "models_app_basemeasurement_capa_gate_c1"

>>> EIX INSTANCIA · germana instancia='left', nom_fitxa=''
    EXCEPCIO: django.db.utils.IntegrityError
      | violates check constraint "models_app_basemeasurement_instancia_exigeix_nom"

>>> EIX INSTANCIA · germana instancia='left', nom_fitxa='L' (D1 satisfeta)
    EXCEPCIO: django.db.utils.IntegrityError
      | violates check constraint "models_app_basemeasurement_instancia_gate_cins"

>>> CONTROL · germana amb capa='exterior', instancia='' (duplicat exacte)
    EXCEPCIO: django.db.utils.IntegrityError
      | duplicate key value violates unique constraint
      | "models_app_basemeasureme_model_id_pom_id_capa_ins_8405ced0_uniq"
      | DETAIL:  Key (model_id, pom_id, capa, instancia)=(396, 299, exterior, ) already exists.
```

### A10.3 · El col·lapse del lector, mesurat

```
files elegibles a BD = 20 · entrades del dict = 20
entrada del POM 299 = 1.5  (ESCALAR, no llista)
expressio del codi sobre [exterior, folre] -> {299: 6.5}   (n=1)
expressio del codi sobre [folre, exterior] -> {299: 1.5}   (n=1)
```

L'expressió literal de `services.py:783-786` executada sobre dues germanes **no desades**: col·lapsa a
**una entrada**, i **guanya l'ÚLTIMA** llegida.

### A10.4 · Preview i generació

```
§3 preview_graded_specs
POMs a la taula = 20 · cel·les del POM 299 = 6
fila = {'03/06': 1.5, '06/09': 1.5, '09/12': 1.5, '12/18': 1.5, '18/24': 1.5, '24/36': 1.5}
preview amb el valor de la GERMANA (base+5) = {'03/06': 6.5, …, '24/36': 6.5}

§4 generate_graded_specs(171)  →  RESULTAT: OK · 120
GradedSpec del POM 299: abans=6 despres=6 (GV 77)
      03/06 = 1.5 · FIXED · capa='exterior' instancia=''   (×6 talles)
total GradedSpec a la BD ara = 2061
```

**120 = 20 POMs × 6 talles: exactament 1 `GradedSpec` per `(POM, talla)`, mai 2.** Total sense canvis
(0 files noves): **és un update pur** sobre la versió activa.

> **El fet que decideix:** sobre un POM `FIXED`, base 1.5 → fila tota a 1.5; amb el valor de la germana
> (6.5) → fila tota a 6.5. Sobre un POM no-FIXED (pom 685): base real → `26.5·27.5·28.5·29.5·30.5·31.5`;
> base+5 → `31.5·32.5·33.5·34.5·35.5·36.5`. **Qui guanyi el col·lapse s'endú la FILA SENCERA**, no una
> cel·la.

### A10.5 · `_upsert_graded_spec` — peta, sobreescriu o duplica?

```
>>> upsert capa=default, instancia='' (mateixa clau que el motor)
    RESULTAT: OK · files (GV,pom,talla) = 1 · 999.0@capa='exterior'/ins=''

>>> upsert capa='folre' (germana per CAPA)
    EXCEPCIO: django.db.utils.IntegrityError
      | violates check constraint "fitting_gradedspec_capa_gate_c1"
      | DETAIL:  Failing row contains (6615, 03/06, 888, FIXED, 0, t, 77, 299, null, folre, ).

>>> upsert instancia='left' (germana per INSTANCIA)
    EXCEPCIO: django.db.utils.IntegrityError
      | violates check constraint "fitting_gradedspec_instancia_gate_cins"
      | DETAIL:  Failing row contains (6616, 03/06, 777, FIXED, 0, t, 77, 299, null, exterior, left).
```

**Ni sobreescriu ni duplica: peta — i peta a POSTGRES, no al Python.** El lookup de 5 camps no troba res
amb capa/instància diferent i intenta un INSERT nou (comportament correcte); el que el frena és la
comporta. El `try/except` de `:1078-1082` **loguja a ERROR i re-llança**: l'error arriba sencer amb el
`DETAIL` de Postgres inclòs.

### A10.6 · Veredicte A10

**Avui el motor no fa res amb dues germanes, perquè dues germanes NO PODEN EXISTIR.** No és una tria
del motor: és la BD qui ho barra, **a les dues puntes de la cadena**. El comportament del motor davant
de dues germanes és **inobservable a staging**.

**Els dos eixos es comporten IGUAL al motor** (lector, preview, upsert): mateix col·lapse a
`{pom_id: escalar}`, mateixa clau de 5 camps a l'upsert, mateixa forma d'error a `fitting_gradedspec`.

**On difereixen —i és una diferència real:** la BD posa **DUES barreres a la instància i UNA a la capa**.
Amb `nom_fitxa=''`, l'error que veus **no és el de la comporta** sinó el de D1
(`instancia_exigeix_nom`): qui llegeixi el missatge pot concloure que li falta un nom quan el que li
falta és que **C4-ins encara no ha passat**. `GradedSpec`, en canvi, només porta la comporta — cap
equivalent de D1 al costat del resultat.

---

## TAULA FINAL DE NODES

| # | Node | Fitxer:línia | Tipus | Amb 2 germanes | Risc |
|---|---|---|---|---|---|
| 1 | `_load_base_measurements` | `pom/services.py:774-790` (clau `:783`) | **Lector · NODE MESTRE** | Col·lapsa a 1 entrada; guanya l'última per `ordre`; la perdedora **perd la fila sencera** | 🔴 **CRÍTIC** — la frontera C3 |
| 2 | Bucle del motor | `pom/services.py:233` | Lector | Només té `pom_id`: no pot dir l'eix ni que el tingués | 🔴 CRÍTIC (deriva de #1) |
| 3 | Crida a `_upsert_graded_spec` | `pom/services.py:284-292` | Escriptor | No passa els eixos; tot cau als defaults | 🔴 CRÍTIC (deriva de #1) |
| 4 | `preview_graded_specs` | `pom/services.py:333`, `:401` | Lector | `base_values={pom_id:v}` — **germanes no s'hi poden ni expressar** | 🔴 **CRÍTIC — 2a frontera, no anotada** |
| 5 | `_upsert_graded_spec` | `pom/services.py:1014`, lookup `:1064-1069` | Escriptor | **Correcte**: 2 `get()` disjunts, 2 files. Frenat per la comporta de BD | 🟢 **LLEST** |
| 6 | `_load_model_overrides` | `pom/services.py:711`, àncora `:743-744` | Lector | Contingut: només entra `('exterior','')` | 🟡 Contingut (cau amb #1) |
| 7 | `_poms_amb_override` | `pom/services.py:751`, `:771` | Derivat | Fusionaria POMs de capes diferents si #6 obre | 🟡 Contingut (cau amb #6) |
| 8 | `_load_grading_rules` | `pom/services.py:682` | Lector | Correcte **per decisió de domini**: la regla no porta eix, ni a l'ORM ni a BD | 🟢 LLEST |
| 9 | Signal F1 | `models_app/signals.py:274-275`, `:322-323` | Escriptor de log | Estampa els dos eixos des de la `instance` | 🟢 **LLEST** |
| 10 | `_ORIGEN_TO_CONTEXT` | `models_app/signals.py:199-210`, `:281`, `:327` | Vocabulari | 4/10 origens no mapejats → **fallback silenciós** | 🟡 Incompletesa oberta |
| 11 | `consolidate_base_from_fitting` | `fitting/services.py:382-391` | Escriptor | **Copia els eixos de la línia** · lloc natural a `:391` | 🟢 LLEST · **candidat A4** |
| 12 | `resolve_size_check` | `services_size_check.py:229-241` | Escriptor | **Copia els eixos de la línia** · lloc natural a `:241` | 🟢 LLEST · **candidat A4** |
| 13 | **Wizard · buidatge** | `pom/wizard_views.py:193-195` | Escriptor | **Buida TOTES les germanes** · cap signal · cap transacció | 🔴 **CRÍTIC — el pitjor d'A9** |
| 14 | Propagació de fitting | `fitting/views.py:665-667` (+ lectura `:626-628`) | Escriptor | Escampa `valor_real` a totes les germanes de la talla | 🔴 ALT |
| 15 | `desactivar_pom_view` | `models_app/views.py:4041-4043`, `:4054` | Escriptor | `.first()` arbitrari; changelog **mal atribuït i append-only** | 🔴 ALT |
| 16 | Id sintètic `pom:talla` | `views.py:2845` · `fittingGridAdapter.jsx:144` · `PropagatedEditor.jsx:68-71` | Contracte | Dues germanes → **el mateix string**, als dos extrems | 🔴 ALT |
| 17 | Resposta de `generar-grading` | `models_app/views.py:2525`, `:2532` | Lector | **Re-col·lapsa** el que la BD havia desat bé | 🟠 MITJÀ |
| 18 | `measurements_table_view` | `models_app/views.py:1652-1658` | Lector | `graded_by_pom[pom_id][size]` — l'últim spec guanya | 🟠 MITJÀ |
| 19 | Motor de patrons · `delta()` | `patterns/engine/ports.py:97-101` · adapter `adapters.py:483-489` | Lector | **Sense àncora ni eixos**: retorna la primera coincidència | 🟠 MITJÀ · transversal |
| 20 | `BaseMeasurementSerializer` | `models_app/serializers.py:403-411` · filtres `views.py:508` | Contracte | L'eix **ni entra ni surt** per la porta genèrica | 🟠 MITJÀ |
| 21 | Camí A sense transacció | `models_app/views.py:2394`, llenç net `:2464` | Transacció | Llenç net irreversible; v+1 buida; specs a mitges | 🔴 ALT · **independent de C3** |
| 22 | Append-only travessat | `consolidate_pom_catalog.py:117`, `:257` | Integritat | Reescriu `pom_id` de files de log ja escrites | 🟠 MITJÀ · **independent de C3** |
| 23 | Les 9 comportes | 9 taules; canòniques a `models_app/models.py:781-802` | Guard de BD | **Impedeixen que existeixi la germana.** Vives a `fhort` i `los` | 🟢 Bastida (C4/C4-ins la retiren) |
| 24 | Pins contradictoris | `test_escriptors_instancia_cins.py:132` vs `test_size_check_completa_linies.py:53…` | Test | n==3 contra n==1/2 sobre la mateixa materialització | 🔴 ALT — cal decidir quin mana |
| 25 | Golden + fumeig | `golden_163_snapshot.py:26-31` · `c1_fumeig_base_stages.py:4-5` | Vigilància | **Tots dos col·lapsats i tots dos manuals** | 🟠 MITJÀ |

---

## LÍMITS DECLARATS DEL TREBALL

1. **No s'ha mesurat el motor amb germanes REALS persistides.** Hauria calgut un
   `ALTER TABLE … DROP CONSTRAINT` fins i tot dins d'una transacció revertida — DDL, fora de la
   frontera («cap migració»). L'investigador ho va considerar un workaround creatiu i **no ho va fer**.
   Tot el que s'afirma del col·lapse ve de (a) l'expressió literal del codi executada sobre instàncies
   **no desades** i (b) la forma de les signatures. **Si es vol el mesurament amb files persistides, cal
   autorització explícita per a DDL dins de la transacció.**
2. **Cap veredicte CAU/NO CAU d'A8 està verificat per execució.** La BD de test **no es pot construir**
   en aquest entorn (`EOFError` a `_create_test_db`). Tot A8 és inferència estàtica; els CAU DUR estan
   ancorats en asserts llegits i citats amb línia, els CAU CONDICIONAL depenen del fixture.
3. **El denominador del 68% del MAPA_TOC no és reproduïble** (el doc no publica la llista dels 80 paths;
   l'esquema ha crescut 364→365). Confirmat **nominalment** tot el que enumera; la fracció exacta queda
   sense verificar. Mesura pròpia: 63/99 = 64%.
4. **`los` no s'ha auditat amb dades reals**: té 0 `BaseMeasurement` i 0 `PieceFittingLine`. S'ha
   verificat que **les comportes i els constraints hi són idèntics**, però cap comptatge d'abast d'A9
   cobreix aquell schema amb dades.
5. **`public` no s'ha auditat** en cap dels blocs.
6. **L'ordre d'avaluació dels CHECK de Postgres no està garantit.** Que `instancia_exigeix_nom` disparés
   abans que `instancia_gate_cins` és el que va passar en aquella execució, **no una llei**. Qualsevol
   test que asserteixi el *nom* del constraint en el cas `instancia≠'' + nom_fitxa=''` és fràgil.
7. **Punts no auditats un per un**: els 7 escriptors de `BaseMeasurement` de `views.py` que no s'han
   llegit línia a línia (`:1195`, `:1206`, `:1435`, `:1810`, `:1948`, `:2350`), la cadena de consum de
   `GradingSnapshot.deltas` més enllà de `grading_projection.py:180-181`, i els lectors de `GradedSpec`
   restants (`fitting/serializers.py:251`, `fitting/services.py:329`, `pom/s6_views.py:174`,
   `pom/grading_views.py:134`, `fitting/graded_spec_views.py:46`, `models_app/views.py:1653/2532/2842`).
8. **`scripts_tmp/` queda exclòs** del registre d'A4 (no és producció); hi ha escriptures de
   `BaseMeasurement` a `diag_t3c.py:31,36` i `diag_t3_t4bis.py:56`.
9. **Obert**: `pom/wizard_views.py:322-334` (`GET models/{id}/base-measurements/`) **no està ancorat** ni
   porta eixos, a diferència del seu germà `s6_views.py:94-96` que sí ho està i que un test pina. No
   s'ha pogut determinar si és un dels **2 forats d'Onada 1** ja censats a `MAPA_TOC_INSTANCIA.md:42-46`
   (aquells són `patterns/views.py:552-556` i `tenants/federation_service.py:593`) **o un tercer**.
   Atenuant: emet una **llista**, no un dict per `pom_id`, per tant no col·lapsa files — però el
   consumidor no té amb què distingir-les tret de `nom_fitxa`.
10. **Obert**: `close_base` decideix per `exists()` global de specs de l'SF (`services.py:501`), sense
    mirar capa. El dia que hi hagi capes, una taula amb specs només d'exterior es tancaria sense generar
    mai els de folre. **No s'ha trobat cap comentari que ho declari**; s'anota com a dubtós, no com a bug.

---

## RESPOSTA DIRECTA — el canvi de catàleg Type-first, ¿toca aquest camí?

# **SÍ. I hi toca al costat PRODUCTOR de l'entrada del motor.**

*(Nota de precisió: l'etiqueta literal «Type-first» **NO EXISTEIX** al repo — grep exhaustiu sobre `.md`,
`.py`, `.js`, `.jsx` → 0 resultats. S'interpreta com el catàleg ancorat a `GarmentTypeItem`, que és el que
existeix i que és el que alimenta les mesures base d'un model.)*

### La prova, node a node

El catàleg Type-first és la cadena `GarmentTypeItem → GarmentPOMMap → ItemBaseSet →
ItemBaseMeasurement`, i **ja parla els quatre eixos**:

| Node del catàleg | Clau | Prova |
|---|---|---|
| `GarmentPOMMap` (pertinença) | `('garment_type_item', 'pom', 'capa', 'instancia')` | `pom/models.py:623` |
| `ItemBaseMeasurement` (el valor) | `('base_set', 'pom', 'capa', 'instancia')` | `pom/models.py:925` |
| — i porta les mateixes comportes | `pom_itembasemeasurement_capa_gate_c1` `:930` · `..._instancia_gate_cins` `:936` · `pom_garmentpommap_*` `:629`,`:635` | |

El pont catàleg→model és `materialize_poms_view` (`models_app/views.py:1068`), i **és 4-axis-aware
d'extrem a extrem**:

```python
1183:    with transaction.atomic():
1186:        ibm = ibms.get((m.pom_id, m.capa, m.instancia))       # clau de 3 del catàleg
1190-1191:  existing = BaseMeasurement.objects.filter(
              model=model, pom=m.pom, capa=m.capa, instancia=m.instancia).first()
1195-1202:  BaseMeasurement.objects.create(
              model=model, pom=m.pom, capa=m.capa, instancia=m.instancia, …
              origen='ITEM_STANDARD', …)
```

El comentari de `:1185` ho diu explícitament: «La clau completa surt del `GarmentPOMMap`, que és el
portador de la pertinença». I `ItemBaseMeasurement` declara la sembra al seu propi docstring
(`pom/models.py:845-846`): «a la sembra (P5) aquests valors es COPIEN a `BaseMeasurement` del Model
(copy-at-the-moment, `origen='ITEM_STANDARD'`)».

### Per què això és exactament el camí d'aquesta diagnosi

```
GarmentTypeItem                                  ← el catàleg Type-first
   └─ GarmentPOMMap        (pom, capa, instancia)   pom/models.py:623        ✅ 4 eixos
   └─ ItemBaseSet
        └─ ItemBaseMeasurement (pom, capa, instancia) pom/models.py:925      ✅ 4 eixos
              │
              │  materialize_poms_view · models_app/views.py:1186-1202       ✅ 4 eixos
              ▼
        BaseMeasurement  UNIQUE(model, pom, capa, instancia)  models.py:754  ✅ 4 eixos
              │
              ▼
        _load_base_measurements → {pom_id: valor}   pom/services.py:783      🔴 1 EIX
```

**El catàleg pot ENCUNYAR una família que el motor no pot LLEGIR.** Un `GarmentTypeItem` que reclami el
mateix POM dues vegades —dues instàncies, o exterior + folre— produeix, via la sembra, **dues
`BaseMeasurement` germanes legítimes**… que `_load_base_measurements` col·lapsa a una, i la perdedora
perd la fila graduada sencera (§A10.4), sense excepció ni log.

I no és hipotètic pel costat del catàleg: **la INSTÀNCIA ja existeix encunyada com a POM de catàleg**
(cas viu registrat a memòria, model 396 — el mateix que ha servit de banc a la sonda d'A10).

### El matís que canvia la urgència, no la resposta

**Avui el canvi de catàleg no pot fer dany**, perquè les comportes CHECK són a les **quatre** taules de
la cadena, no només a les dues del motor: `pom_garmentpommap_*` (`:629`, `:635`),
`pom_itembasemeasurement_*` (`:930`, `:936`), `models_app_basemeasurement_*` (`:783`, `:801`),
`fitting_gradedspec_*` (`fitting/models.py:234`, `:243`). El catàleg **no pot ni tan sols encunyar la
família** mentre C4/C4-ins no passin.

Per tant, en termes operatius:

- **Mentre les comportes siguin vives:** el canvi de catàleg Type-first toca el camí **estructuralment**
  però no pot produir cap col·lapse. Es pot fer sense tocar C3.
- **El dia que C4/C4-ins retirin les comportes:** el catàleg **serà el primer productor de germanes del
  sistema** —abans que cap tècnic n'escrigui una a mà— perquè la sembra és automàtica i ja sap dir els
  dos eixos. **Si C3 no ha passat abans, el primer `GarmentTypeItem` amb un POM repetit produirà
  silenciosament mesures graduades incompletes.**

**En una frase:** el catàleg Type-first i el motor comparteixen exactament un node —`BaseMeasurement`— i
hi arriben amb vocabularis diferents: el catàleg hi escriu amb quatre eixos, el motor el llegeix amb un.
**Type-first no crea el problema de C3; és qui l'alimentarà primer.**

---

*Document de diagnosi · Patró A · READ-ONLY. Al working tree, MAI commitejat.*
*Cap proposta de fix: les decisions són humanes (Patró C).*
