# DIAGNOSI — Federació v2: camí crític (token-link, EXTERN, catàleg cross-schema, meritació)

Data: 2026-07-22 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`

**Abast:** els fets necessaris per dissenyar el camí crític de la Federació Brand↔Studio abans
de LOSAN dilluns: quina primitiva de lectura fora del schema actiu ja existeix, què costa crear
un Model marcat EXTERN, d'on menja el wizard, on s'emet la meritació, i on ancorar el TenantLink.

**Convenció:** cada afirmació porta `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi**
(verificat per grep/BD, no especulat). Tota proposta va marcada `💡 PROPOSTA (a validar)`.

**Dades:** els comptatges d'aquest doc són de **staging** (schemas `fhort`, `los`, `public`).
Les dades reals de `los` viuen a PROD i **no s'han tocat**; les SQL per a PROD queden escrites
al doc perquè les executi l'Agus.

**Precedent:** cens BRW a `DIAGNOSI_FEDERACIO_BRW_STUDIO.md`.

---

## BLOC 1 — Primitiva cross-schema (R10)

### 1.1 Topologia de partida (el que fa que el problema sigui el que és)

- `SHARED_APPS` = `django_tenants`, `fhort.tenants`, contrib, third-party, **`fhort.pom`**,
  **`fhort.backoffice`** — `backend/fhort/settings.py:44-66`.
- `TENANT_APPS` = `accounts`, `models_app`, **`pom`**, `fitting`, `tasks`, `planning`,
  `commerce`, `patterns`, `i18n_content` — `backend/fhort/settings.py:67-78`.
- **`pom` viu a SHARED *i* a TENANT** (comentari explícit a `settings.py:52-54`). Conseqüència
  verificada a BD: **les 25 taules `pom_*` existeixen als tres schemas** (`fhort`, `los`,
  `public`) — `information_schema.tables`. No és una taula compartida: són **tres còpies
  independents**.
- `TenantMainMiddleware` resol el schema **pel Host** — `backend/fhort/settings.py:96` (llista
  MIDDLEWARE) amb `ROOT_URLCONF='fhort.urls'` i `PUBLIC_SCHEMA_URLCONF='fhort.urls_public'`
  (`settings.py:97-98`). Una petició = **un** schema actiu.

**Fet clau:** `pom__pom_global`, `pom__categoria` i companyia (`fhort/pom/grading_views.py:93`,
`fhort/pom/s10_views.py:27`, `fhort/patterns/views.py:489`) **NO són lectures cross-schema**:
són FKs normals resoltes dins el schema actiu sobre files **replicades**. La replicació la fa
`bootstrap_tenant` (§1.3), no el runtime.

### 1.2 Inventari complet de `schema_context()` fora de management commands i tests

Grep exhaustiu (`grep -rln schema_context --include=*.py fhort/ | grep -v /management/ | grep -v tests`)
→ **exactament 4 fitxers**. Aquesta és tota la superfície de runtime que canvia de schema:

| # | Fitxer:línia | Direcció | Camí | Reutilitzable com a gateway Brand→Studio? |
|---|---|---|---|---|
| A | `fhort/backoffice/receivers.py:10` | **tenant → public** (escriptura) | signal `model_consumption_started` | **No** (escriptura, i public no és un tenant) |
| B | `fhort/backoffice/invoice_pdf.py:50` | **public → tenant** (lectura delegada) | request (`views_invoices.py:190`) | **Parcial** — patró correcte, direcció contrària |
| C | `fhort/tenants/discovery_service.py:35` | **public → N tenants** (lectura, bucle) | request (urlconf public) | **SÍ — el precedent més proper** |
| D | `fhort/pom/s9_views.py:119` | `request.tenant.schema_name` = **no-op** | request (tenant) | No (no canvia res) |

Detall dels tres que compten:

- **B — `_emissor()`, `fhort/backoffice/invoice_pdf.py:48-70`.** La docstring del fitxer
  (`invoice_pdf.py:10-13`) escriu la llei de frontera ja acceptada al projecte:
  > "`backoffice` viu a public i `accounts.TenantConfig` viu al schema del tenant. La lectura
  > es fa explícitament amb `schema_context(EMISSOR_SCHEMA)`; és una **lectura delegada, no una
  > FK**: el backoffice segueix sense referenciar models de tenant a la seva capa de dades."

  Disciplina que ja aplica i que un gateway hauria de copiar: **còpia dels valors a un dict
  abans de sortir del context** — `invoice_pdf.py:54` ("fora del `schema_context` l'objecte no
  s'ha de tornar a consultar"). El schema destí surt de settings, no de dades:
  `EMISSOR_SCHEMA = getattr(settings, 'FHORT_EMISSOR_SCHEMA', 'fhort')` — `invoice_pdf.py:42`.

- **C — `find_workspaces_for_email()`, `fhort/tenants/discovery_service.py:22-44`.** És
  **l'únic codi de runtime que entra a un schema de tenant decidit per dades** (no per Host, no
  per settings): enumera `Client.objects.exclude(schema_name=public)` (`:34`), entra a cada un
  amb `schema_context(tenant.schema_name)` (`:35`) i llegeix. La pròpia docstring el declara
  "patró canònic provat" (`:9-12`). Porta a més una llei de privadesa explícita (`:4-7`) i una
  mitigació de timing (recórrer sempre tots els tenants, sense early-out — `:25-26`).
  **Té test:** `fhort/tenants/tests_discovery.py:60-63` (casos 1 / 0 / >1).

- **A — `on_model_consumption_started()`, `fhort/backoffice/receivers.py:7-18`.** Vegeu BLOC 4.

**NO EXISTEIX** cap lectura **tenant → altre tenant** en el camí de petició. **NO EXISTEIX** cap
mòdul, helper, mixin ni funció d'abstracció cross-schema: grep de `cross_schema|gateway|federac`
sobre `fhort/**/*.py` no torna cap implementació — només comentaris que descriuen el problema
(`fhort/models_app/models.py:724`, `fhort/pom/models.py:964`, `fhort/settings.py:54`) i un
`n = -1  # relació cross-schema no resoluble` a `fhort/pom/management/commands/cleanup_losan_old.py:45`.

### 1.3 `bootstrap_tenant` — la primitiva tenant→tenant que SÍ existeix (però copia)

`backend/fhort/tasks/management/commands/bootstrap_tenant.py` és **l'únic codi que llegeix d'un
tenant per escriure a un altre**. No és un gateway de lectura: és un **copiador materialitzador**.

- Lectura de l'origen: `_read_source()` amb `schema_context(source)` — `:195-213`; M2M a
  `_read_m2m()` `:215-218`; claus naturals a `_natural_lookup()` `:220-223`.
- Recompte de l'origen exposat al backoffice (public) sense importar models de tenant:
  `seed_block_counts(source='fhort')` — `:100-122`, cridat des de
  `fhort/backoffice/views_seeding.py:49-51`. **És un segon precedent de public→tenant en
  request.**
- Ordre topològic i estratègies de FK a `_spec()` — `:126-176`. Estratègies: `MAP`, `NULL`,
  `DEFER`, `NATURAL` (`:113-116`).
- **Dos `NULL` decisius per a la federació** — el catàleg viatja **despullat de client**:
  - `(GradingRuleSet, ('nom',), {'customer': NULL, 'parent_version': DEFER}, ('targets',), None)` — `:157`
  - `(SizingProfile, (...), {'customer': NULL, 'modified_by_id': NULL, 'parent_profile': DEFER}, ...)` — `:161-164`
- Blocs de sembra seleccionables i el seu graf de dependències: `SEED_BLOCKS` `:55-63`,
  `SEED_BLOCK_DEPS` `:64+`. `grading` arrossega `base + garments + size_systems + pom_masters`.
- Gate de sembra: el filtre de font permet restringir a rulesets `origen=CANONICAL` — `:197-200`.

**Conseqüència per al camí crític:** avui, "portar el catàleg d'un tenant a un altre" té una
sola implementació i és **materialització per còpia amb remapatge de pk**, executable només per
management command. Un Brand que consulti el catàleg del Studio **en viu** no té cap peça feta.

### 1.4 FKs `db_constraint=False` — inventari complet (10)

Totes són **FK lògiques dins el mateix schema** que perden la constraint perquè el model viu a
una app SHARED i apunta a una app tenant-only. **Cap és una FK cross-schema real** — no hi ha
integritat referencial de BD que travessi schemas, i cap d'elles habilita llegir un altre tenant.

| Fitxer:línia | Camp | Destí | Motiu al codi |
|---|---|---|---|
| `pom/models.py:250-252` | `CustomerPOMAlias.customer` | `tasks.Customer` | `:248-249` |
| `pom/models.py:437-440` | `GarmentPOMMap.garment_type_item` | `tasks.GarmentTypeItem` | `:435-436` |
| `pom/models.py:476-478` | `ItemBaseMeasurement.garment_type_item` | `tasks.*` | `:474-475` |
| `pom/models.py:569-571` | `GradingRuleSet.garment_type_item` | `tasks.GarmentTypeItem` | llei CONTENIDOR |
| `pom/models.py:577-579` | `GradingRuleSet.customer` | `tasks.Customer` | `:574-576` |
| `pom/models.py:664-666` | `RuleSetScopeNode.garment_type_item` | `tasks.*` | `:663` |
| `pom/models.py:954-956` | `SizingProfile.customer` | `tasks.Customer` | `:951-953` |
| `models_app/models.py:725-727` | `ModelGradingRule.pom` | `pom.POMMaster` | `:722-724` |
| `models_app/models.py:910-912` | `SizeCheckLine.pom` | `pom.POMMaster` | `:908-909` |

Divergència ja anotada al codi i **no tocada**: `SizeSystem.customer_codi` va per **codi de 3
chars** (`pom/models.py:329-332`) mentre `GradingRuleSet.customer` i `SizingProfile.customer`
van per **FK** (`pom/models.py:574-576`). Són **dues maneres diferents** de dir "de qui és
això" convivint a la mateixa app.

### 1.5 Referències cross-schema per **id nu** (sense FK, sense constraint)

Patró ja acceptat quan la relació travessa de veritat: es desa l'enter, no la relació.

- `SizingProfile.modified_by_id = IntegerField(...)` — `pom/models.py:963-964`
  ("ID de l'usuari que ha modificat (cross-schema)")
- `pom/models.py:992` — mateix patró ("ID usuari cross-schema")
- `fitting/models.py:161` — "ID usuari cross-schema (Sprint S11)"
- `backoffice.ModelConsumptionEvent.codi_client` = **CharField**, no FK (vegeu BLOC 4)

**💡 PROPOSTA (a validar):** el `TenantLink` i qualsevol referència Brand→Studio segueixin
aquest patró ja establert (**codi/id opac + resolució explícita**), no una FK.

### 1.6 💡 PROPOSTA (a validar) — la forma del gateway

> No hi ha res construït; això és disseny, no fet.
>
> Un `read_from_tenant(schema, fn)` d'una sola peça, amb les tres disciplines que el codi
> existent ja demostra: (a) **entrar/sortir amb `schema_context`** i **retornar dicts, mai
> objectes ORM** (llei de `invoice_pdf.py:54`); (b) **schema destí resolt per dades**
> (`discovery_service.py:34-35`) però **validat contra un vincle**, no contra la llista sencera
> de tenants; (c) **sense FK** — el vincle és un codi (§1.5).
> Ubicació natural: `fhort/tenants/` (ja hi viu `discovery_service.py`, ja és SHARED, ja té
> tests de cross-schema). Posar-lo a `pom` o `backoffice` trencaria la frontera que
> `invoice_pdf.py:10-13` declara.

---

### Veredicte BLOC 1: **llest**

- La primitiva de **lectura cross-schema en request existeix i està provada**, però només en
  direcció **public → tenant** (`invoice_pdf.py:50`, `views_seeding.py:49`) i
  **public → N tenants** (`discovery_service.py:35`, amb test).
- **Lectura tenant → tenant en request: NO EXISTEIX.** El gateway Brand→Studio és **peça nova**
  — però no inventa res: n'hi ha prou generalitzant `discovery_service.find_workspaces_for_email`
  amb la disciplina de còpia-a-dict de `invoice_pdf._emissor`.
- La **única** via tenant→tenant construïda és `bootstrap_tenant`, i **copia** (materialitza amb
  remapatge de pk) en comptes de llegir en viu; a més **NUL·LIFICA `customer`** al catàleg que
  viatja (`bootstrap_tenant.py:157,161`).
- Les 10 FKs `db_constraint=False` **no habiliten res cross-schema**: són intra-schema sense
  constraint. No hi ha integritat referencial que travessi schemas i no n'hi pot haver.
- Cap abstracció cross-schema existeix (grep net). Hi ha **dos vocabularis de propietat**
  convivint (`customer_codi` 3-chars vs `customer` FK) que el vincle haurà de triar o pontar.

---

## BLOC 2 — Creació mínima de Model i marca EXTERN

### 2.1 Quatre camins de creació de Model (grep exhaustiu)

`grep -rn "Model.objects.create|Model.objects.bulk_create" --include=*.py fhort/` (sense tests):

| # | Camí | Fitxer:línia | Codi/seqüència | Signals |
|---|---|---|---|---|
| 1 | **Wizard** (l'únic camí viu d'UI) | `models_app/views.py:694` (simple) i `:733` (peça de set) | codi **calculat a la vista** | **NO** entra al signal de codi-gen |
| 2 | **Import de fitxa** (.ftt/Excel single) | `models_app/tech_sheet_views.py:295` | **delega al signal** | SÍ, tots |
| 3 | **Bulk collection** (Excel N models) | `models_app/bulk_import_service.py:518` | `ModelSequence` + `_build_model` (`:563`) | **NO — `bulk_create` bypassa signals** (`:517`) |
| 4 | **Seed LOSAN** | `models_app/management/commands/seed_losan_models.py:219` | `bulk_create` | **NO** |

### 2.2 Camps obligatoris

**A BD** (`information_schema`, NOT NULL sense default) — 21 columnes, de les quals les que un
caller ha d'aportar sí o sí: `codi_intern`, `codi_client`, `codi_tenant`, `any`, `temporada`,
`sequencial`, `fit_type`, `estat`, `fase_actual`, `prioritat`, `data_entrada`,
`fabric_composition`, `fabric_main`, `fabric_notes`, `shrinkage_type`, `measurements_version`,
`collection`, `created_at`, `shrinkage_iso_key`, `reanchored_by_start`. Les de text/enum tenen
`default=''`/valor a nivell Django, de manera que a la pràctica el mínim real és
**`codi_intern` + `codi_tenant` + `any` + `temporada` + `sequencial`**.

**`customer` és NULLABLE a BD** — `models_app/models.py:125-131` ("Nullable a BD per a la
transició; el wizard l'exigeix"), `on_delete=PROTECT`.

**Al wizard** (guards de servei, no de BD):
- `year` i `season` obligatoris — `views.py:637-638`.
- **`garment_type_item_id` obligatori** — `views.py:646-647`. El comentari `:641-645` és
  explícit: "és la baula del motor de temps i de la valoració de receptes (comercial). Guard de
  servei; la columna segueix nullable a BD".
- `customer_id` **NO** és obligatori: `_resolve_customer_code()` (`views.py:452-462`) cau al
  self-customer, i en últim recurs al literal `'IMP'`.
- La talla base ja **no** arrossega ruleset: llei 5 CAPES, `views.py:611-614`.

**"Model funcional" té definició al codi** — `CONFIG_KEYS` a `models_app/services.py:105` i
`model_config_missing()` `:106-125`: **`garment_type_item`, `base_size`, `size_run`
(= `size_run_model` + `size_system`), `grading_rule_set`**. És la font única, reusada pel
Watchpoint d'import i pel gate suau de POMs (`:103-105`). Sense els 4, el model existeix però
no gradua ni admet POMs.

### 2.3 Numeració: tres lleis i dos formats convivint

**Llei A — signal `generate_model_code`** (`models_app/signals.py:16-80`): `SELECT MAX(sequencial)`
escopat per `customer_id + any + temporada` (`:59-68`), format
**`{CUST}-{YY}-{TT}-{NNNN}`** (`:80`). El propi codi el declara no concurrency-safe
(`commerce/services.py:6`: "confirmat NO concurrency-safe").

**Llei B — wizard** (`views.py:664-690`): **no toca `ModelSequence` ni el signal**. Escaneja per
**regex** `^{PREFIX}-{SS}{YY}-[0-9]{4}$` sobre `models_app_model.codi_intern` **i**
`models_app_garmentset.codi_base` (`:675-687`), format **`{CUST}-{SSYY}-{NNNN}`**.

**Llei C — bulk** (`services.py:38-72`): `ModelSequence` amb `select_for_update`. El terra és
**`max(comptador, MAX(sequencial) real)`** (`:68`, `_real_max_seq` `:75-81`) precisament perquè
les lleis A i B escriuen `sequencial` sense tocar mai el comptador (`:50-54`). Lectura pura
equivalent: `sequence_floor()` `:84-98`.

**Verificat a BD (staging, schema `fhort`):**
- **1002 models en format B (wizard)** vs **3 en format A (signal)**:
  `BRW-26-FW-0036`, `BRW-26-SS-0002`, `LOS-27-SS-0001`.
- La deriva comptador↔terreny és **real i observable**: `ModelSequence` de BRW 2026/FW té
  `last_seq=35` mentre el terreny té `MAX(sequencial)=36`. La llei del `max()` és el que ho
  sosté.

**`codi_intern` és `unique=True`** (`models_app/models.py:117`; constraint
`models_app_model_codi_intern_key`) — **únic per schema**, no global.

### 2.4 Senyals que salten en crear un Model

Els 4 receivers de `models_app/signals.py` estan registrats **sense `sender=`** (`@receiver(pre_save)`
/ `@receiver(post_save)`, `:16, :83, :142, :174`) i filtren dins amb `if sender is not Model:
return`. **Salten a CADA save de qualsevol model del projecte.**

1. `generate_model_code` (pre_save, `:17`) — genera codi+seqüencial. **Escapatòria explícita**: §2.5.
2. `sync_size_fitting` (post_save, `:84`) — crea **sempre** una `SizeFitting` `Proto/Pendent`
   amb codi `{codi_intern}-SF1` (`:126-136`). `creat_per` és **PROTECT no-null**: resol
   `responsable → created_by → primer UserProfile` (`:115-119`); **un tenant amb zero
   UserProfiles no pot crear la SF** — es logueja i se salta (`:120-125`). El docstring
   ho justifica com el tancament del "forat universal B2" (`:92-96`).
3. `recompute_import_watchpoint` (post_save, `:143`) — recalcula el Watchpoint d'import obert
   via `model_config_missing()` (`:165-171`). No crea, no re-desa.
4. `update_last_activity` (post_save, `:175`) — `darrera_activitat = now()` per `queryset.update()`.

**F1 (log append-only de mesures)** NO penja del Model sinó de `BaseMeasurement`:
`capture_old_measurement_value` (pre_save, `:212`) + `log_measurement_change` (post_save, `:231`),
que escriuen `MeasurementChangeLog` (`:292-303`). Inclou la poda explícita (`_desactivat`,
`:259-273`, principi del soroll 2026-07-22). **Crear un Model no dispara F1**; F1 arrenca amb
la primera mesura.

**Conseqüència:** els camins 3 i 4 (`bulk_create`) **no disparen res** i han de replicar a mà
el que el signal faria: `bulk_import_service.py:522-536` crea les `SizeFitting` i els
`Watchpoint` explícitament, amb el comentari "bulk_create bypassa signals, per això la creació
es fa aquí explícitament" (`:529-531`).

### 2.5 Es pot crear un Model amb codi extern sense consumir seqüència?

**SÍ, i l'escapatòria ja existeix i està documentada:**

```
# El caller ja mana el codi (i el seu sequencial) → no interferir.
if getattr(instance, 'codi_intern', None):
    return
```
— `models_app/signals.py:37-39` (docstring `:23-24`).

Condicions perquè funcioni avui, sense tocar cap línia:
1. `codi_intern` ha de venir informat → el signal no genera res.
2. **`sequencial` és NOT NULL** → cal donar-li **algun** valor igualment.
3. `codi_tenant` és NOT NULL → cal informar-lo (el signal només l'omple si el genera ell, `:78-79`).

**⚠️ RISC REAL, no hipotètic — enverinament del terra de seqüència.** `_real_max_seq()`
(`services.py:75-81`) fa `MAX(sequencial)` filtrant per `customer + any + temporada`, **sense
mirar l'origen del model**. Un model EXTERN importat conservant el `sequencial` del Brand
(p.ex. 4711) elevaria el terra del Studio per a aquell (customer, any, temporada) i cremaria
4710 números al següent bulk. La deriva de §2.3 (35 vs 36) mostra que aquest camí ja es toca.

### 2.6 Marca EXTERN: què hi ha i què no

**`Model.origen` NO EXISTEIX.** Verificat a BD: l'únic camp amb "origen" a `models_app_model`
és **`origen_patro`** — i és **un altre eix**, amb choices `CAD Client / Digitalització / Des de
zero` (`models_app/models.py:112-116`). Tampoc existeix cap columna `extern`/`source`
(`information_schema`, filtre `%origen%|%extern%|%source%` → 1 sola fila: `origen_patro`).

Camps de text lliure existents que **podrien** portar la marca però **no la signifiquen**:
`codi_client` ("SKU/referència pròpia del client... **NO és prefix ni clau tècnica**",
`models_app/models.py:118-120`), `collection`, `observacions`.

**Vocabulari de provinença que SÍ existeix al projecte** (precedent a copiar, no a reinventar):
- `GradingRuleSet.origen`: `CANONICAL / CLIENT_RUN / IMPORT / MANUAL / MIGRACIO / DICCIONARI`.
- `ModelGradingRule.origen`: `IMPORTED / CANONICAL / CLIENT_RUN / MANUAL`.
- El pont entre tots dos és explícit: `_ORIGEN_RS_A_MGR` a `models_app/services.py:147-155`, amb
  la nota que abans el wizard escrivia sempre `'CANONICAL'` i **"és el que va fer que 104 regles
  de client es presentessin com a canòniques"**.
- `BaseMeasurement.origen`: `IMPORTED / MANUAL / FITTED / CALCULATED / STANDARD` +
  `TEMPLATE` (`signals.py:197-203, 275-276`).

### 2.7 La semàntica de federació ja té un precedent viu

`_validar_ruleset_assignable()` — `models_app/views.py:492-546` — ja modela "fer servir una
definició d'un altre client":

- 0 regles actives → **400 `GRADING_RULESET_EMPTY`** (`:512-520`).
- `size_system` divergent → **400 `GRADING_SIZE_SYSTEM_MISMATCH`** (`:522-532`).
- **`customer` divergent → 409 `GRADING_CUSTOMER_MISMATCH`**, mai bloqueig: *"aplicar la forma
  d'un altre client és un flux de taller legítim"* (`:505-507`, `:534-544`), desbloquejable amb
  `confirmar_altre_client` (`views.py:632`).

És **exactament** la semàntica Brand→Studio, ja escrita, ja provada, però resolta **dins d'un
sol schema**.

### 2.8 SQL per a PROD (schema `los`) — l'executa l'Agus

```sql
-- 1) Formats de codi_intern i volum a LOSAN.
SELECT CASE
         WHEN codi_intern ~ '^[A-Z]{3}-[0-9]{2}-[A-Z]{2}-[0-9]{4}$'      THEN 'A signal'
         WHEN codi_intern ~ '^[A-Z]{3}-[A-Z]{2}[0-9]{2}-[0-9]{4}$'        THEN 'B wizard'
         WHEN codi_intern ~ '^[A-Z]{3}-[A-Z]{2}[0-9]{2}-[0-9]{4}-[0-9]{2}$' THEN 'B peca'
         ELSE 'ALTRES' END AS fmt,
       count(*)
FROM los.models_app_model GROUP BY 1 ORDER BY 2 DESC;

-- 2) Deriva comptador ModelSequence vs terreny real (el risc de §2.5).
SELECT s.customer_id, s.year, s.season, s.last_seq,
       (SELECT max(m.sequencial) FROM los.models_app_model m
         WHERE m.customer_id=s.customer_id AND m."any"=s.year AND m.temporada=s.season) AS terreny
FROM los.models_app_modelsequence s ORDER BY 1,2,3;

-- 3) Models sense els 4 camps de CONFIG_KEYS (quants NO són funcionals avui).
SELECT count(*) FILTER (WHERE garment_type_item_id IS NULL)                    AS sense_gti,
       count(*) FILTER (WHERE coalesce(trim(base_size_label),'')='')           AS sense_base_size,
       count(*) FILTER (WHERE coalesce(trim(size_run_model),'')='' OR size_system_id IS NULL) AS sense_size_run,
       count(*) FILTER (WHERE grading_rule_set_id IS NULL)                     AS sense_ruleset,
       count(*)                                                                AS total
FROM los.models_app_model;

-- 4) Customers del tenant LOSAN (per saber contra qui s'escopa la seqüència).
SELECT id, codi, nom, is_self, codi_global FROM los.tasks_customer ORDER BY id;

-- 5) Hi ha cap UserProfile al tenant? (PROTECT de sync_size_fitting, signals.py:120-125)
SELECT count(*) FROM los.accounts_userprofile;
```

### 2.9 💡 PROPOSTA (a validar)

> **P2-a — `Model.origen` nou, no reutilitzar `origen_patro`.** `origen_patro` és l'eix
> "d'on ve el patró", no "de qui és el model". Reutilitzar-lo repetiria l'error documentat a
> `services.py:149-151` (un sol camp servint dos vocabularis → 104 regles mal etiquetades).
> Choices en la línia del vocabulari ja existent: `INTERN` (default) / `EXTERN`.
>
> **P2-b — el camí EXTERN entra pel camí 1 (wizard) amb `codi_intern` pre-fixat**, aprofitant
> l'escapatòria de `signals.py:37-39`, i **NO** pel bulk (que bypassa signals i hauria de
> replicar-ho tot a mà).
>
> **P2-c — trencar el vincle entre `sequencial` i el terra de seqüència per als EXTERN.** Dues
> sortides possibles, cap feta: (i) `sequencial = 0` per als EXTERN + excloure'ls a
> `_real_max_seq()` (`services.py:75-81`); (ii) mantenir la seqüència del Studio i desar el codi
> del Brand a un camp propi. Sense una de les dues, §2.5 crema números.
>
> **P2-d — el 409 `GRADING_CUSTOMER_MISMATCH` (`views.py:534-544`) és el motlle del gate
> Brand→Studio**: mateix contracte (avís conscient + confirmació), amb l'origen del ruleset
> resolt pel vincle en comptes de per `customer_id`.

---

### Veredicte BLOC 2: **llest, amb 2 banderes**

- **Crear un Model amb codi extern sense passar pel codi-gen JA ÉS POSSIBLE avui**, sense tocar
  cap línia: `signals.py:37-39` retorna si `codi_intern` ve informat. És l'escapatòria que fa
  viable EXTERN sense refactor.
- **Marca EXTERN: NO EXISTEIX.** `Model` no té camp `origen` (només `origen_patro`, un altre
  eix). És l'única peça de model de dades estrictament nova del BLOC 2.
- 🚩 **Bandera 1 — el terra de seqüència s'enverina.** `_real_max_seq()` (`services.py:75-81`)
  no distingeix origen; un EXTERN amb `sequencial` del Brand crema el rang del Studio.
- 🚩 **Bandera 2 — dos formats de `codi_intern` conviuen** (1002 wizard / 3 signal a `fhort`) i
  **tres lleis de numeració** que no comparteixen font. Introduir una quarta provinença sobre
  aquest terreny sense fixar-ho abans multiplica la deriva ja observada (35 vs 36).
- El wizard exigeix `garment_type_item` (`views.py:646`) però `customer` és opcional i cau al
  self-customer — un model EXTERN mal format acabaria atribuït al Studio, no al Brand.
- La semàntica de federació ja té motlle provat dins un schema:
  `_validar_ruleset_assignable` (`views.py:492-546`).

---

## BLOC 3 — Wizard data sources: on menja i on injectar la segona font

### 3.1 Les 6 crides HTTP del wizard (inventari tancat)

`frontend/src/pages/ModelWizard.jsx` importa **un sol mòdul d'API** (`:10`:
`models, sizeSystems, gradingRuleSets, garmentGroups, garmentTypes, garmentTypeItems`) i **no
fa cap `fetch`/`axios` directe** (grep net). Tot passa per `frontend/src/api/endpoints.js`.

| # | Font | Crida al wizard | Endpoint (`endpoints.js`) | URL → view backend | Queryset |
|---|---|---|---|---|---|
| 1 | **GarmentGroup** | `garmentCatalog.js:33` (via `CascadeSelector.jsx:71,231`) i `ModelWizard.jsx:264` | `endpoints.js:166` `/api/v1/garment-groups/` | `pom/urls.py:23` → `GarmentGroupViewSet` `pom/views.py:151` | `GarmentGroup.objects.all()` `pom/views.py:154` |
| 2 | **GarmentType** (família) | `garmentCatalog.js:43` i `ModelWizard.jsx:135` | `endpoints.js:158` `/api/v1/garment-types/` | `pom/urls.py:24` → `GarmentTypeViewSet` `pom/views.py:103` | `pom/views.py:112-115` + `get_queryset` `:121-132` |
| 3 | **GarmentTypeItem (GTI)** | `CascadeSelector.jsx:78` i `:246` (llista, peresós per família) + `ModelWizard.jsx:292` (detall) | `endpoints.js:384-385` `/api/v1/garment-type-items/` | `tasks/urls.py:37` → `GarmentTypeItemViewSet` `tasks/views_b.py:842` | `tasks/views_b.py:857-863` |
| 4 | **SizeSystem** | `ModelWizard.jsx:194` | `endpoints.js:170` `/api/v1/size-systems/` | `pom/urls.py:21` → `SizeSystemViewSet` `pom/views.py:59` | `pom/views.py:66` |
| 5 | **GradingRuleSet** | `ModelWizard.jsx:264` | `endpoints.js:210` `/api/v1/grading-rule-sets/` | `pom/urls.py:25` → `GradingRuleSetViewSet` `pom/views.py:171` | `pom/views.py:181-190` |
| 6 | **Model** (preview + escriptura) | `ModelWizard.jsx:152` (`nextRef`), `:414` (`createWizard`), `:433` (`updateStep2`) | `endpoints.js:56-58` | `models_app/urls.py:194-196` | — |

**Les 5 fonts de catàleg són `<Model>.objects` nu.** Cap porta `schema_context`, cap accepta un
paràmetre de schema, cap filtra per tenant: django-tenants els resol **implícitament al schema
del Host** (§1.1). **NO EXISTEIX** cap paràmetre de font/origen a cap dels 6 endpoints.

### 3.2 Fonts que **no** són HTTP (i que per tant no es poden federar via endpoint)

- **Targets i constructions són constants de frontend hardcodejades**, no BD:
  `TARGETS` `frontend/src/components/grading/gradingAxes.js:10-24` i `CONSTRUCTIONS` `:26-31`,
  importades a `ModelWizard.jsx:8`. Existeix `/api/v1/targets/` (`endpoints.js:185`) però
  **el wizard no el crida** (grep net al fitxer).
- **`GARMENT_GROUPS`** (`gradingAxes.js`, via `garmentCatalog.js:18-19`) aporta **només ordre i
  noms ca/en/es**; la disponibilitat mana des de BD (`garmentCatalog.js:14-16`, `:52-59`).
- **`RuleSetPicker`** no fa cap crida: rep `ruleSets` per prop des de `ModelWizard.jsx:727`
  (imports a `RuleSetPicker.jsx:1-3`). El matching és **pur al client**
  (`matchingRuleSetsStrict`, `gradingAxes.js`), invocat a `ModelWizard.jsx:309` i `:328`.

### 3.3 **SizingProfile: no és una font directa del wizard — és un filtre amagat al backend**

El wizard **no crida mai `/api/v1/sizing-profiles/`** (grep de `sizingProfiles` a
`frontend/src/`: només `CustomerDetail.jsx:184`, `SizeLibrary.jsx:36`, `SizeSetDetail.jsx:28,36`,
`SizingProfileSelector.jsx:4` — **cap a `ModelWizard.jsx` ni a `CascadeSelector.jsx`**).

Hi entra **indirectament**, com a taula de compatibilitat darrere `?target=`:

```python
qs = qs.filter(id__in=SizingProfile.objects
               .filter(target__codi=target)
               .values('garment_type'))
```
— `pom/views.py:128-131` (comentari `:122-124`). **Cap altre endpoint del wizard toca
SizingProfile** (grep `SizingProfile` a `pom/views.py`, `tasks/views_b.py`: només aquí).

Conseqüència per a la federació: **el pas 3 (Talles) del wizard beu de `SizeSystem`, no de
`SizingProfile`** (`ModelWizard.jsx:194`; el `sizingResult` `:109-118` es construeix només amb
`selSystem` + `selectedSizes` + `baseSize`) — llei 5 CAPES, comentari `:106-108`. Federar el
catàleg de talles és federar `SizeSystem`; `SizingProfile` només decideix **quines famílies
surten per a un target**.

### 3.4 `_validar_ruleset_assignable` **SÍ és al camí del wizard** (les dues portes)

Grep exhaustiu (`grep -rn _validar_ruleset_assignable --include=*.py fhort/`) → **3 aparicions,
cap fora de `models_app/views.py`**:

- definició `views.py:492`
- **crida 1 — `create_model_wizard`** (`views.py:626`), a `views.py:657-662`. Comentari `:652-653`:
  "mateixa porta que a update_model_step2: el wizard pot arrossegar graduació ja des de la creació".
- **crida 2 — `update_model_step2`** (`views.py:804`), a `views.py:836`.

**Confirmat: no és només d'assignació directa.** És la porta d'entrada de graduació **tant a la
creació com a l'edició** del wizard, i s'activa només si el payload porta `grading_rule_set_id`
(`views.py:654-655`). El 409 `GRADING_CUSTOMER_MISMATCH` (§2.7) és, doncs, **codi viu del wizard**,
desbloquejable amb `confirmar_altre_client` — que el frontend ja sap enviar en els dos camins:
`ModelWizard.jsx:417` (create) i `:436` (step2).

### 3.5 El punt d'injecció de la segona font: `_resolve_garment_def`

Tot el payload de catàleg del wizard es resol en **una sola funció compartida pels dos camins**:

`_resolve_garment_def(d, model=None)` — `models_app/views.py:549` (docstring `:550-565`: "Aquesta
funció la comparteixen `create_model_wizard` i `update_model_step2`"). Cridada a `views.py:648`
(create) i dins `update_model_step2`.

Els **4 lookups per pk nu**, tots al schema actiu:

| Entitat | Línia | Comportament si no existeix |
|---|---|---|
| `GarmentTypeItem` (`garment_type_item_id`) | `views.py:572-579` | `400 'GarmentTypeItem no trobat'` |
| `GarmentGroup` (derivat de l'item, per `codi`) | `views.py:580-582` | silenciós (no el posa) |
| `GarmentType` (legacy `garment_type_id`) | `views.py:583-588` | `400 'GarmentType no trobat'` |
| `SizeSystem` (`size_system_id`) | `views.py:589-593` | `400 'SizeSystem no trobat'` |
| `GradingRuleSet` (`grading_rule_set_id`) | `views.py:594-598` | **`pass` — tolerant, silenciós** |

**Fets que condicionen qualsevol injecció:**
1. El pont família↔item és **estricte**: si arriba `garment_type_item_id`, la família i el grup es
   **deriven** de l'item i el `garment_type_id` del payload s'**ignora** (`views.py:570-571`). Un
   GTI extern arrossegaria la seva família externa sencera.
2. Els camps resolts es desen com a **objectes ORM** a `fields[...]`, no com a ids → són
   instàncies del schema actiu i acaben en FKs reals del `Model`. Un objecte llegit d'un altre
   schema **no és assignable** aquí (violaria la llei de còpia-a-dict de `invoice_pdf.py:54`, §1.2).
3. `size_run` passa per `run_del_model` (`views.py:603-609`), que ordena contra el `SizeSystem`
   resolt → depèn de l'entitat, no només de l'etiqueta.

### 3.6 💡 PROPOSTA (a validar) — on injectar la segona font amb codi mínim

> **P3-a — dues superfícies, no una.** El wizard té **lectura** (6 endpoints, §3.1) i
> **escriptura** (`_resolve_garment_def`, §3.5). Federar només la lectura ensenya catàleg extern
> que l'escriptura rebutjaria amb `400 ... no trobat`. Les dues s'han de tocar alhora o cap.
>
> **P3-b — el cost mínim de lectura és 1 paràmetre × 5 endpoints**, perquè els 5 viewsets
> comparteixen forma (`queryset` de classe + `filterset_fields`). Un mixin de `get_queryset` que,
> davant `?source=<vincle>`, retorni **dicts del gateway (§1.6)** en comptes del queryset local
> és l'única peça nova de lectura. **Cap dels 5 viewsets és apte tal com està**: tots retornen
> objectes ORM al serializer.
>
> **P3-c — el punt únic d'escriptura és `views.py:549`**, i és **una sola funció per als dos
> camins del wizard** (create i step2). És el lloc de menys codi per decidir "aquest pk és local
> o extern". Però §3.5-2 diu que no s'hi pot assignar un objecte extern: el camí realista és
> **materialitzar/resoldre el GTI extern a un local abans d'arribar-hi**, no fer
> `_resolve_garment_def` cross-schema.
>
> **P3-d — el 409 ja és al camí.** No cal inventar el gate de confirmació: `views.py:657` i
> `:836` ja el criden i el frontend ja el sap contestar (`ModelWizard.jsx:417`, `:436`). Un
> `GRADING_EXTERNAL_SOURCE` seguiria el mateix contracte sense tocar la UI del wizard.

---

### Veredicte BLOC 3: **llest, amb 1 bandera**

- **Les 5 fonts de catàleg del wizard són `<Model>.objects` nu** al schema actiu
  (`pom/views.py:66,112,154,181`, `tasks/views_b.py:857`). **Cap accepta un paràmetre de font o
  de schema. NO EXISTEIX** cap punt d'extensió per a una segona font, ni de lectura ni d'escriptura.
- **`_validar_ruleset_assignable` és al camí del wizard**, en les **dues** portes
  (`views.py:657` create, `:836` step2) — confirmat, no és només assignació directa. El 409
  `GRADING_CUSTOMER_MISMATCH` és el motlle de gate ja cablat end-to-end (frontend inclòs,
  `ModelWizard.jsx:417,436`).
- **`SizingProfile` no és una font del wizard**: hi entra només com a filtre de compatibilitat
  target↔família dins `GarmentTypeViewSet.get_queryset` (`pom/views.py:128-131`). El pas Talles
  beu de `SizeSystem` (`ModelWizard.jsx:194`).
- **Punt d'injecció d'escriptura: un de sol** — `_resolve_garment_def` (`views.py:549`),
  compartit per creació i edició. Punt d'injecció de lectura: **5**, però amb forma idèntica.
- 🚩 **Bandera 3 — els 4 lookups de `_resolve_garment_def` desen objectes ORM, no ids**
  (`views.py:572-598`), i el `Model` els guarda com a FKs reals. **Un catàleg llegit en viu d'un
  altre schema no és assignable per aquest camí**: o es materialitza abans, o el camí EXTERN no
  passa pel wizard. Això xoca amb §2.9 P2-b (que proposava entrar pel wizard) i és la decisió
  que el BLOC 3 posa sobre la taula.
- Nota transversal: `TARGETS`/`CONSTRUCTIONS` són **constants de frontend** (`gradingAxes.js:10,26`),
  no BD. Dos tenants federats comparteixen aquest vocabulari **per build**, no per dades.

---

## BLOC 4 — Meritació: el punt d'emissió i on entra l'ACTOR

### 4.1 La cadena completa, punt per punt

**Emissor únic de producció: `transition_task()`** — `fhort/tasks/services_c.py:96`
(decorada `@transaction.atomic` `:93`). El bloc de meritació és `:152-186`:

```
if to_status == 'InProgress':                                    # services_c.py:147
    Model.objects.filter(pk=..., fase_actual='Pending').update(fase_actual='Dev')   # :155
    try:
        with transaction.atomic():                               # :161
            rows = Model.objects.filter(
                pk=task.model_id, consumption_started_at__isnull=True
            ).update(consumption_started_at=now)                  # :162-164
            if rows:                                              # :165  <-- EL TRIGGER
                model = Model.objects.select_related('customer').get(pk=task.model_id)
                record = ConsumptionRecord.objects.create(...)     # :168-174
                model_consumption_started.send(                    # :175-181
                    sender=Model, codi_client=model.customer.codi,
                    period=record.period, opaque_ref=record.opaque_ref, merited_at=now)
    except Exception:
        logger.exception(...)                                     # :182-186 — NO re-raise
```

Fets que la caracteritzen:

- **El trigger no és "primera tasca InProgress": és `rows` != 0** (`services_c.py:162-165`), és a
  dir **el `UPDATE ... WHERE consumption_started_at IS NULL` que guanya la cursa**. La idempotència
  és **per BD**, no per lògica. La marca viu a `Model.consumption_started_at`
  (`models_app/models.py:204`, nullable).
- **Meritació no-fatal i aïllada**: savepoint propi + `except` que no re-llança
  (`services_c.py:182-186`). Comentari `:157-159`: llei **DUES FACTURACIONS SEPARADES** — l'atomic
  de meritació no conté res de `commerce`. El forat es tapa després amb `reconcile_consumption`.
- El senyal és `Signal()` nu — `fhort/tasks/signals.py:17`; s'envia amb `sender=Model`.
- **Receiver únic** — `fhort/backoffice/receivers.py:7-18`: entra a `schema_context('public')` (`:10`)
  i fa `get_or_create(opaque_ref=..., defaults={codi_client, period, merited_at})` (`:11-17`).
  **Segona idempotència**, per `opaque_ref` únic.
- **Segon emissor: `reconcile_consumption`** (management command) —
  `backoffice/management/commands/reconcile_consumption.py:150-156`, amb la mateixa forma.
- **Consumidors** (3): `recurring_service.billable_events()` `:49-51` (filtre anti-doble-cobrament),
  `billing_service.py:63-65` (recompte), `views_invoices.py:239` (vista de consum del backoffice).
  Vincle a factura: `recurring_service.py:143-144` (`update(invoice_line=line)`).

### 4.2 Camps actuals de l'event a `public` (verificat a BD)

`public.backoffice_modelconsumptionevent` — **8 columnes**, cap més
(staging; declaració `backoffice/models.py:79-104`):

| Columna | Tipus | Origen |
|---|---|---|
| `id` | bigint | — |
| `codi_client` | **varchar(3)** | `model.customer.codi` (`services_c.py:176`) |
| `period` | varchar(7) | `now.strftime('%Y-%m')` (`services_c.py:171`) |
| `opaque_ref` | uuid **unique** | `ConsumptionRecord.opaque_ref` (`models_app/models.py:849`) |
| `merited_at` | timestamptz | `now` |
| `exclos` / `exclos_motiu` | bool / varchar(200) | operador (`models.py:97-98`) |
| `invoice_line_id` | FK nullable | motor F-RECUR (`recurring_service.py:143`) |

**NO EXISTEIX cap columna de tenant, schema, actor, executor ni origen.** El docstring diu el
disseny explícitament: *"Mínim absolut: cap codi ni nom de model. Referència fluixa per
codi_client + opaque_ref"* (`models.py:80-83`). La banda tenant (`ConsumptionRecord`,
`models_app/models.py:839-856`) tampoc en té: `model`, `code_snapshot`, `name_snapshot`, `period`,
`opaque_ref`, `merited_at`.

### 4.3 L'ACTOR ja divergeix avui — amb dades, no en hipòtesi

El camp es diu `codi_client` i el comentari del model diu **`= Client.codi_tenant` (ref fluixa)**
(`backoffice/models.py:84`). Però l'emissor hi posa **`model.customer.codi`**
(`services_c.py:176`), que és el **`tasks.Customer` del model dins del tenant** — "de qui és el
model", no "quin tenant ha fet la feina". El reconcile ho fa igual, amb un fallback revelador:

```python
codi_client = model.customer.codi if model.customer else tenant.codi_tenant
```
— `reconcile_consumption.py:111`. **És l'única línia de tot el codi que escriu el tenant real a
l'event**, i només quan el model no té customer.

**Verificat a staging (31 events a public; 26 `ConsumptionRecord`, tots al schema `fhort` —
`los` en té 0):**

| `codi_client` de l'event | events a public | amb `ConsumptionRecord` a `fhort` | és un tenant? |
|---|---|---|---|
| `BRW` | 18 | **18** | **NO** — `tenants_client` només té `FTT`, `LOS`, `SYS` |
| `LOS` | 9 | **6** | sí (`schema_name='los'`) |
| `FTT` | 4 | 2 | sí (`schema_name='fhort'`) |

- **Els 18 events BRW són orfes de facturació**: `BRW` no existeix a `public.tenants_client` — és
  un `tasks.Customer` del schema `fhort` (41 models). El filtre de facturació és
  `billable_events(client.codi_tenant, period)` (`recurring_service.py:84`, `billing_service.py:63`),
  o sigui que **cap client de backoffice els reclamarà mai**. Concorda amb la capacitat `exclos`
  prevista "per als orfes de tenants morts" (`backoffice/models.py:95-96`).
- **Els 9 events LOS són el cas de federació ja passant**: es van meritar **des del tenant
  `fhort`** (els 6 amb record viuen a `fhort`, i `los.models_app_consumptionrecord` està buit),
  però s'atribueixen al client `LOS`. **Feina feta pel Studio, meritada al Brand** — exactament la
  dimensió ACTOR, ja viva, sense cap camp que la registri.
- **5 events no tenen `ConsumptionRecord` enlloc.** `ConsumptionRecord.model` és
  `OneToOneField(on_delete=CASCADE)` (`models_app/models.py:843-845`): esborrar el model esborra el
  record del tenant, **però l'event de public sobreviu**. És append-only de facto.

### 4.4 On entraria l'ACTOR sense trencar els 18 BRW ni el flux

Restriccions dures observades:

1. **`opaque_ref` és `unique`** (`models.py:86` + constraint `..._opaque_ref_key`) i el receiver fa
   `get_or_create(opaque_ref=...)` amb la resta a `defaults` (`receivers.py:11-17`). Un camp nou
   dins `defaults` **no reescriu els events existents** — els 18 BRW quedarien amb el default de la
   migració, intactes.
2. **Cap columna té default a BD** excepte `exclos`/`exclos_motiu`; el patró de la casa per afegir
   capacitat sense migrar dades és exactament el d'`exclos` (`models.py:95-98`): **camp nou amb
   default**, mai NOT NULL sense default.
3. **El receiver només rep kwargs del senyal** (`receivers.py:8`, amb `**kwargs`) i el senyal és
   `Signal()` nu (`tasks/signals.py:17`) → **afegir un kwarg no trenca cap receiver**, però sí els
   emissors si es fa obligatori. Emissors a actualitzar: **2** (`services_c.py:175`,
   `reconcile_consumption.py:150`).
4. **L'actor és conegut al punt d'emissió sense cap query nova**: `transition_task(task, to_status,
   profile)` (`services_c.py:96`) té el `profile` que executa, i el schema actiu és
   `connection.schema_name` / `request.tenant`. **NO EXISTEIX** cap ús d'això al bloc de meritació.
5. **Els 3 consumidors filtren per `codi_client` sol** (`recurring_service.py:49-51`,
   `billing_service.py:63`, `views_invoices.py:239`). Un camp actor **additiu i no filtrat** no
   canvia cap import facturat.

### 4.5 💡 PROPOSTA (a validar)

> **P4-a — l'ACTOR és una columna nova a `ModelConsumptionEvent`, additiva i amb default**, no un
> canvi de semàntica de `codi_client`. Reinterpretar `codi_client` reescriuria el sentit dels 31
> events existents; afegir `actor_schema` amb `default=''` els deixa literalment intactes i els fa
> auditables a posteriori. Patró idèntic al d'`exclos` (`backoffice/models.py:95-98`).
>
> **P4-b — la dualitat ja existent és la bona**: `codi_client` = **de qui és el model** (a qui es
> factura) · actor = **qui ha obert la tasca** (quin schema). Els 9 events LOS demostren que la
> primera meitat ja funciona federada; només falta registrar la segona.
>
> **P4-c — 2 emissors a tocar, 1 receiver, 0 consumidors.** `services_c.py:175-181` i
> `reconcile_consumption.py:150-156` passen el kwarg; `receivers.py:11-17` l'afegeix a `defaults`.
> Cap dels 3 consumidors de facturació canvia (§4.4-5) → **cap import facturat es mou**.
>
> **P4-d — els 18 BRW no s'han de "reparar" en aquest sprint.** No són facturables per BD (`BRW`
> no és cap `codi_tenant`) i la capacitat `exclos` ja existeix per a exactament aquest cas
> (`models.py:95-96`). Marcar-los és decisió d'operador, no migració.
>
> **P4-e — bandera separada, no d'aquest sprint:** els 5 events sense `ConsumptionRecord` revelen
> que public i tenant poden divergir per `CASCADE` (`models_app/models.py:843-845`) sense que res
> ho detecti. `reconcile_consumption` només busca el forat **en un sentit** (models sense event,
> `:73-82`), mai events sense model.

---

### Veredicte BLOC 4: **llest, amb 2 banderes**

- **Punt d'emissió confirmat i únic en producció:** `transition_task()`
  `tasks/services_c.py:152-181`, dins `if to_status == 'InProgress'` (`:147`). El trigger real és
  **`UPDATE ... WHERE consumption_started_at IS NULL` retornant `rows>0`** (`:162-165`) —
  idempotència per BD, no per lògica. Segon emissor: `reconcile_consumption.py:150`.
- Camí complet: senyal `Signal()` nu (`tasks/signals.py:17`) → receiver únic
  `backoffice/receivers.py:7-18` → `schema_context('public')` (`:10`) → `get_or_create` per
  `opaque_ref` (segona idempotència).
- **Camps de l'event: 8, cap d'ells actor/tenant/schema** (BD verificada + `models.py:79-104`).
  Tampoc a `ConsumptionRecord` (`models_app/models.py:839-856`).
- 🚩 **Bandera 4 — `codi_client` no és el tenant, és el customer del model**
  (`services_c.py:176` vs comentari `models.py:84`). **18 events `BRW` són orfes de facturació**
  (`BRW` no existeix a `tenants_client`) i **9 events `LOS` es van meritar des del tenant `fhort`**.
  La federació no és futura: **la meritació cross-casa ja passa i no queda registrada enlloc**.
- 🚩 **Bandera 5 — divergència silenciosa public↔tenant.** 5 dels 31 events no tenen
  `ConsumptionRecord` (CASCADE del model, `models_app/models.py:843-845`); `reconcile_consumption`
  només mira el forat contrari (`:73-82`).
- **Cost d'introduir l'ACTOR: 2 emissors + 1 receiver + 1 migració additiva.** Els consumidors de
  facturació filtren només per `codi_client` → **cap import es mou** i **els events ja meritats no
  es toquen** (`get_or_create` no reescriu `defaults`).

---

## BLOC 5 — public/Client: l'ancoratge del TenantLink

### 5.1 Camps actuals de `tenants.Client` (`fhort/tenants/models.py:69-215`)

`Client(TenantMixin)` — hereta `schema_name` de django-tenants. Camps propis, per famílies:

| Família | Camps | Línies |
|---|---|---|
| **Identitat** | `nom`, `codi_tenant` (**varchar(3) unique**), `tipologia`, `plan` (FK `Plan`, PROTECT, nullable) | `:117-131` |
| **Cicle de vida** | `estat` (`onboarding/actiu/suspes/baixa`), `actiu` (bool legacy), `data_alta`, `onboarding_complet`, `data_suspensio`, `data_baixa`, `motiu_baixa` | `:120-134`, `:164-166` |
| **Preferències** | `moneda`, `unitats` (cm/inch), `idioma` | `:123-125` |
| **Fiscal** | `rao_social`, `nif`, `adreca_fiscal` (LEGACY `:139`), `pais`, `email_facturacio`, adreça estructurada (`adreca_linia1/2`, `ciutat`, `estat_provincia`, `codi_postal`) | `:137-149` |
| **VAT** | `vat_number`, `vat_validat`, `vat_validat_data`, `tipus_client` (b2b/b2c), `regim_vat` (derivat per `recalcular_regim_vat()` `:203-215`) | `:152-161` |
| **Pagaments** | `stripe_customer_id`, `metode_pagament`, `stripe_payment_method_id` | `:163-166` |
| **Comercial** | `gratis_fins`, `nota_comercial` | `:169-176` |
| **Capacitats** | **`feature_flags` (JSONField, `default=dict`)** | `:120` |

Altres models de l'app `tenants`: `Plan` (`:15-66`), `Domain` (`:220`), **`CodiAuth`** (`:224-296`,
login únic) i `TenantContacte` (`:299-320`).

### 5.2 🔵 **El camp tipus/rol de tenant SÍ EXISTEIX** — i ja està poblat correctament

L'objectiu del punt 5 era *"confirmar absència de camp tipus/rol de tenant (Brand/Studio)"*.
**No és absent: existeix, és obligatori a l'alta, i les dades ja són les correctes.**

- **`Client.tipologia`** — `tenants/models.py:118`, choices `TIPOLOGIA_ESTUDI='estudi'` /
  `TIPOLOGIA_MARCA='marca'` (`:70-75`). **És exactament l'eix Studio/Brand.**
- **`Plan.tipologia`** — `tenants/models.py:40`, amb un tercer valor: `estudi/marca/enterprise`
  (`:31-38`).
- **Obligatori a l'alta de tenant**: `'tipologia': {'required': True}` —
  `backoffice/serializers_tenants.py:104`; present a les dues superfícies del serializer
  (`:32`, `:96`).
- **Filtrable al backoffice**: `filterset_fields = ['estat', 'tipologia', 'plan']` —
  `backoffice/views_tenants.py:61`.
- **Cablejat a la UI del backoffice**: `TenantFormPage.jsx:268-269` (select, default `'estudi'`
  `:18`, `:95`, enviat `:157`), `TenantsPage.jsx:196` (columna), `TenantDetailPage.jsx:388` (fitxa).

**Dades reals a staging (`public.tenants_client`):**

| `codi_tenant` | `nom` | `schema_name` | **`tipologia`** | `estat` | `plan_id` |
|---|---|---|---|---|---|
| `SYS` | FHORT System | `public` | `estudi` | actiu | — |
| `FTT` | FHORT Management | `fhort` | **`estudi`** | actiu | — |
| `LOS` | LOSAN | `los` | **`marca`** | onboarding | 7 |

**El Studio ja està marcat Studio i el Brand ja està marcat Brand.** L'eix de la federació no
s'ha de crear: s'ha de **fer servir**.

**🚩 Però és un camp INERT.** Grep de `tipologia` sobre `fhort/**/*.py` (fora de migracions):
**cap branca de lògica de domini hi depèn**. Les úniques aparicions no-test són el serializer,
el filterset, i `seed_free_plan.py:30`. Les ~20 aparicions restants són `setUp` de tests que a
més hi escriuen **`'MARCA'` en majúscules** (p.ex. `tasks/tests.py:31`, `pom/tests.py:26`,
`fitting/tests.py:32`) — **un valor que no és cap dels choices** (`'marca'`), i que ningú valida
perquè res no el llegeix. `tests_discovery.py:29,41` sí usa `'marca'` correctament.

### 5.3 El segon ancoratge, ja pre-declarat al codi: `Customer.codi_global`

**`tasks.Customer.codi_global`** — `fhort/tasks/models.py:207`, `CharField(max_length=3,
null=True, blank=True)`. El comentari immediatament anterior (`:205-206`) és literal:

> "Ganxo per al registre global de codis del backoffice futur (**permeabilitat cross-tenant**).
> Placeholder sense lògica en aquest sprint."

- **Ja té una escriptura real**: `bootstrap_tenant._close_onboarding()` —
  `tasks/management/commands/bootstrap_tenant.py:348-356`. Propaga
  `self_customer.codi_global = client.codi_tenant` (`:353-355`), amb el comentari "identitat
  canònica ... el ganxo del registre global cross-tenant" (`:350-351`).
- **Cap lectura enlloc**: grep de `codi_global` a `fhort/**/*.py` (fora de migracions) → 10 hits,
  dels quals **7 són d'un altre `codi_global`** (el de `POMGlobal`: `patterns/views.py:509`,
  `pom/dictionary_service.py:102`, `load_losan_package.py:115-118`,
  `export_losan_package.py:125`). Del `Customer.codi_global` només hi ha la **declaració** i la
  **propagació del bootstrap**. **Zero consumidors.**
- **A staging està BUIT a tot arreu**: els 3 customers de `fhort` (`FTT`/`LOS`/`BRW`) i el de
  `los` (`LOS`, `is_self=true`) tenen `codi_global = NULL`. Els tenants existents es van crear
  abans de `_close_onboarding`, o sense passar-hi.

**Conseqüència:** el projecte ja tenia previst **exactament** el problema del vincle i hi va
deixar el ganxo — però `codi_global` és **de 3 chars i unidireccional** (customer → codi de
tenant). No pot expressar direcció, rol, ni permisos: no és un vincle, és una **etiqueta d'identitat**.

### 5.4 Taules de backoffice a `public` (verificat a BD)

`information_schema`, schema `public`, excloent `django_*`/`auth_*` → **45 taules**, de tres
famílies:

- **`tenants_*` (4)**: `tenants_client`, `tenants_domain`, `tenants_plan`, `tenants_codiauth`,
  `tenants_tenantcontacte`.
- **`backoffice_*` (14)**: `backofficeuser`, `backofficeactionlog`, `modelconsumptionevent`,
  `invoice`, `invoiceline`, `invoiceserie`, `contractline`, `tenantcontract`, `servicecatalog`,
  `vatrate`, `seedprofile`, `legaldocument`, `legaldocumentversion`, `legalacceptance`.
- **`pom_*` (25)**: la còpia de public del catàleg (§1.1) — **no és backoffice**, és la rèplica
  del catàleg que `pom` té per viure a SHARED *i* TENANT (`settings.py:52-54`).

### 5.5 Les fronteres reals (dues, no una)

El brief cita `invoice_pdf.py:10-13` com a frontera declarada. **Verificat: aquesta frontera és
`backoffice` ↛ models de TENANT** (`accounts.TenantConfig`), i és la que obliga a la lectura
delegada per `schema_context` (§1.2-B). **NO diu res sobre `backoffice` ↔ `tenants`.**

De fet **`backoffice` depèn de `tenants` obertament, amb FKs reals i amb constraint** (les dues
apps són SHARED, o sigui mateix schema):

| FK | Fitxer:línia |
|---|---|
| `TenantContract.client → tenants.Client` (PROTECT) | `backoffice/models.py:244` |
| `Invoice.client → tenants.Client` (PROTECT) | `backoffice/models.py:349` |
| `LegalAcceptance.client → tenants.Client` (PROTECT) | `backoffice/models.py:677` |

I 7 imports directes de `fhort.tenants.models` des de `backoffice`
(`views_tenants.py:17`, `billing_service.py:13`, `recurring_service.py:23`,
`views_pricing_client.py:21`, `serializers_invoices.py:4`, `views_legal.py:10`,
`serializers_tenants.py:7`, `seed_free_plan.py:26`).

**La dependència inversa NO existeix**: grep de `backoffice` sobre `fhort/tenants/**/*.py` (fora
de migracions) → **cap resultat**. `tenants` no coneix `backoffice`.

Hi ha una **segona frontera declarada**, i és la més rellevant per a la federació —
`SeedProfile` (`backoffice/models.py:424-438`):

> "**FRONTERA:** el backoffice és SHARED (public) i **NO ha de conèixer el detall del catàleg
> d'un tenant**. Per això `seleccio` guarda **BLOCS** (concepte de producte), no models ni
> registres concrets. El mapatge bloc→models de catàleg i el graf de dependències viuen a
> `tasks/management/commands/bootstrap_tenant.py`."

És el **precedent exacte** que demanava el brief: una taula de public que **governa** una
operació cross-schema **sense referenciar cap entitat de tenant** — parla en vocabulari de
producte (blocs), i el mapatge a dades viu al costat tenant.

### 5.6 Precedents de vincle a public: què hi ha i què no

- **NO EXISTEIX** cap taula que relacioni **dos `Client`** entre si: cap FK auto-referencial ni
  M2M a `Client` (`tenants/models.py:69-215`). Totes les FKs a `Client` existents són
  **unilaterals** (`TenantContract`, `Invoice`, `LegalAcceptance`, `TenantContacte`).
- **NO EXISTEIX** cap camp de rol/direcció entre tenants.
- **El precedent més proper de "relació cross-tenant viva a public" és `CodiAuth`**
  (`tenants/models.py:224-296`), i la seva docstring **justifica per què viu a `tenants` i no
  enlloc més** (`:226-233`):
  > "PER QUÈ AL PUBLIC: el bescanvi **creua orígens**. Qui EMET el codi és l'autenticació central
  > ... i qui el CONSUMEIX és el host del tenant de destí. **Una taula per-schema no la veurien
  > tots dos.** `fhort.tenants` és a SHARED_APPS i no a TENANT_APPS → les seves taules només
  > existeixen a `public`, que és exactament el que aquesta peça necessita."

  El seu camp de destí és **`tenant_schema = CharField(max_length=63)`** (`:281`) — **no una FK a
  `Client`**: el mateix patró de referència opaca de §1.5.
- L'altra peça cross-tenant de `tenants` és `discovery_service.py` (§1.2-C). **L'app `tenants` és,
  de fet, on ja viu tota la lògica que travessa cases.**

### 5.7 💡 PROPOSTA (a validar) — ancoratge, no disseny de taula

> **P5-a — el rol Brand/Studio NO és peça nova.** `Client.tipologia` ja existeix
> (`tenants/models.py:118`), és obligatori (`serializers_tenants.py:104`), està a la UI
> (`TenantFormPage.jsx:268`) i **les dades ja són correctes** (FTT=estudi, LOS=marca). El que
> falta no és el camp: és **el primer consumidor de domini** (avui: zero).
>
> **P5-b — `TenantLink` viu a `fhort/tenants/`, no a `backoffice`.** Tres raons ancorades:
> (i) `CodiAuth` ja hi és pel mateix motiu literal — creua orígens i necessita ser visible als
> dos costats (`tenants/models.py:226-233`); (ii) `discovery_service.py` (l'únic runtime
> tenant-decidit-per-dades) ja hi és; (iii) **`tenants` no depèn de `backoffice`** (grep net,
> §5.5) mentre que `backoffice` sí depèn de `tenants` — posar el vincle a `backoffice`
> **invertiria** una dependència que avui és neta i unidireccional.
>
> **P5-c — el vincle apunta per `schema_name`/`codi_tenant`, no per FK.** Precedent directe:
> `CodiAuth.tenant_schema = CharField(63)` (`:281`) i la llei de §1.5 (id/codi opac). Una FK a
> `Client` funcionaria tècnicament (mateix schema), però el vincle ha de sobreviure a la lectura
> des de dins d'un tenant, on `Client` no és consultable sense `schema_context`.
>
> **P5-d — `Customer.codi_global` (`tasks/models.py:207`) és el pont natural cap al costat
> tenant**, i ja té la seva escriptura feta (`bootstrap_tenant.py:353-355`). Però està **buit a
> tots els tenants de staging** i **no té cap lector**. Abans de fer-lo servir com a baula, cal
> decidir si es rebackfilla — altrament el vincle no tindrà on aterrar dins el schema.
>
> **P5-e — el motlle de govern és `SeedProfile`** (`backoffice/models.py:424-438`), no `Invoice`:
> una taula de public que decideix una operació cross-schema **parlant en vocabulari de producte**
> i deixant el mapatge a dades al costat tenant. Si `TenantLink` acaba enumerant blocs o àmbits,
> ha de fer-ho amb aquest vocabulari, no amb pks de catàleg.

---

### Veredicte BLOC 5: **llest, amb 1 correcció de premissa**

- 🔵 **CORRECCIÓ AL BRIEF: el camp de rol Brand/Studio NO és absent.** `Client.tipologia`
  (`tenants/models.py:118`, choices `estudi`/`marca` `:70-75`) existeix, és **obligatori a l'alta**
  (`serializers_tenants.py:104`), és filtrable (`views_tenants.py:61`) i està a la UI del
  backoffice. **Les dades ja són correctes: FTT=`estudi`, LOS=`marca`.**
- 🚩 **Bandera 6 — `tipologia` és un camp INERT.** Cap branca de lògica de domini el llegeix
  (grep net fora de serializer/filterset/tests). Els tests hi escriuen `'MARCA'` en majúscules
  (`tasks/tests.py:31` i ~18 més), **un valor fora de choices que ningú valida** — prova que res
  no en depèn. El primer consumidor real serà el de la federació.
- **Segon ganxo ja pre-declarat: `Customer.codi_global`** (`tasks/models.py:205-207`, literal
  "permeabilitat cross-tenant ... placeholder sense lògica"). Escrit per
  `bootstrap_tenant.py:353-355`, **llegit per ningú, i NULL als 4 customers de staging**.
- **Ubicació del `TenantLink`: `fhort/tenants/`.** `backoffice` → `tenants` és una dependència
  real i unidireccional (3 FKs `models.py:244,349,677` + 8 imports); **`tenants` → `backoffice` no
  existeix** (grep net). Posar-hi el vincle invertiria l'única frontera neta que queda.
- **La frontera d'`invoice_pdf.py:10-13` no aplica aquí**: separa `backoffice` de models de
  **tenant**, no de l'app `tenants`. La frontera que sí és el motlle és la de **`SeedProfile`**
  (`backoffice/models.py:428-434`): public governa el cross-schema **en vocabulari de blocs**,
  mai amb entitats de catàleg.
- **Precedent de referència opaca cross-tenant a public: `CodiAuth`**
  (`tenants/models.py:224-296`), amb `tenant_schema = CharField(63)` (`:281`) en comptes de FK, i
  una docstring que **justifica explícitament** viure al public per creuar orígens (`:226-233`).
- **NO EXISTEIX** cap taula que vinculi dos `Client`, ni cap FK auto-referencial, ni cap camp de
  direcció/rol entre tenants. Totes les FKs a `Client` són unilaterals.

---

### 5.8 Com neix un tenant avui, end-to-end (on s'inseriria l'emissió del token)

**Camí A — HTTP, l'únic camí de producte** (`backoffice/views_tenants.py:78-107`):

| # | Pas | Fitxer:línia | Nota |
|---|---|---|---|
| 1 | `POST /api/backoffice/v1/tenants/` → `ClientViewSet.create` | `views_tenants.py:78` | Només rol ADMIN (`ADMIN_ACTIONS` `:31`) |
| 2 | `serializer.save()` → **`auto_create_schema` de django-tenants** crea el schema i hi corre les migracions | `views_tenants.py:89`; `schema_name = codi_tenant.lower()` a `serializers_tenants.py:154-155` | **FORA de `transaction.atomic` a posta** (`:82-88`): dins d'una transacció Postgres falla amb *"cannot ALTER TABLE ... pending trigger events"* |
| 3 | `Domain.objects.create(f'{codi}.fhorttextile.tech', is_primary=True)` | `views_tenants.py:90-91` | Domini derivat, no parametritzable |
| 4 | `BackofficeActionLog` `client.create` | `views_tenants.py:92-99` | |
| 5 | **Només si `plan.nom == Plan.NOM_FREE`**: `_llanca_sembra_free()` | `views_tenants.py:103-104`, def a `:34-52` | `subprocess.Popen(..., start_new_session=True)` **detached**; el 201 torna sense esperar |
| 6 | El client neix en `estat='onboarding'`; el frontend fa **polling** de `Client.estat` | docstring `views_tenants.py:41-43` | |

**Compromís declarat al codi** (`views_tenants.py:87-89`): si falla el pas 3, queda un `Client` + schema **orfe**; cleanup manual, comanda de neteja inexistent.

**Camí B — el provisionador** (`backoffice/management/commands/provision_free_tenant.py`):

1. Resol el `SeedProfile` (`--profile` o el `is_default_free=True, actiu=True`) — `:57-65`. Sense perfil → **error dur**, no sembra res.
2. `call_command('bootstrap_tenant', schema, '--profile', pk)` — `:69`.
3. `call_command('create_tenant_admin', schema, '--email', email)` — `:88`. L'email surt de `Client.email_facturacio`; **si és buit, l'admin queda DIFERIT** i no s'inventa (`:81-87`).
4. Cada pas escriu `BackofficeActionLog`; **tots dos passos són idempotents → la comanda és re-executable** (docstring `:12-14`).

**Camí C — `bootstrap_tenant`** (`tasks/management/commands/bootstrap_tenant.py`), el que fa la feina real:

- Guardes d'entrada (`:361-372`): `public` no és tenant; origen ≠ destí; el `Client` destí ha d'existir; l'origen també.
- **Llegeix el `SeedProfile` des de `public` ABANS d'obrir el `schema_context` del destí** (`:374-377`, comentari literal) — el patró de §5.5.
- Còpia peça a peça dins `transaction.atomic()` + `schema_context(schema)` (`:411-413`), amb 2a passada de FKs diferides (`:430`).
- **Tancament (`:444-451`)**: `_close_onboarding(client)` (`:348-356`) → propaga `Customer.codi_global = client.codi_tenant`; després, **ja a `public`**, `client.estat = 'actiu'` i `onboarding_complet=True` (`:449-451`).

**Estat real de `Customer.codi_global` a staging (verificat a BD, no inferit):**

| Schema | `codi` | `is_self` | `codi_global` |
|---|---|---|---|
| `fhort` | `FTT` | ✔ | **NULL** |
| `fhort` | `LOS` | ✗ | **NULL** |
| `fhort` | `BRW` | ✗ | **NULL** |
| `los` | `LOS` | ✔ | **NULL** |

- **4 de 4 NULL.** Cap tenant de staging ha passat mai per `_close_onboarding` amb èxit (o es van crear abans que existís).
- **NO EXISTEIX cap unique constraint ni cap índex sobre `codi_global`**, ni a `fhort` ni a `los` (`pg_indexes` i `pg_constraint` de `tasks_customer`: l'únic unique és `tasks_customer_codi_key` sobre **`codi`**). El "registre global de codis" del comentari `tasks/models.py:205-206` **no té integritat de cap mena**: dos customers poden compartir `codi_global` sense que res es queixi.

**On s'inseriria l'emissió del token en un onboarding real** (fet, no proposta): l'únic punt del camí HTTP on el `Client` ja existeix, el schema ja està provisionat i el domini ja resol és **`views_tenants.py:100-104`** — el mateix punt on avui es decideix `_llanca_sembra_free`. El pas equivalent al costat command és **`bootstrap_tenant.py:444-451`** (`_close_onboarding` + tancament d'estat), que ja és el lloc on el projecte va posar l'única escriptura d'identitat cross-tenant que existeix.

> **💡 P5-f (a validar)** — `_close_onboarding` (`bootstrap_tenant.py:348-356`) és l'únic escriptor de `codi_global` i **només toca el self-Customer del tenant nou**. Perquè el `TenantLink` tingui on aterrar caldria (i) backfill dels 4 customers actuals i (ii) decidir si `codi_global` es fa unique — avui no ho és, i el vincle hi confiaria.

---

## BLOC 6 — `/me` i `feature_flags`: què sap el frontend de la seva pròpia casa

### 6.1 Què retorna `/me` avui, camp per camp

| Peça | Fitxer:línia |
|---|---|
| Ruta | `accounts/urls.py:14` (`me/`), muntada sota `api/v1/` a `fhort/urls.py:44` |
| View | `accounts/views.py:40-59` (`@api_view(['GET'])`, `IsAuthenticated`) |
| Serializer | `accounts/serializers.py:13-68` (`MeSerializer`, sobre `User`) |
| Capacitats | `accounts/capabilities.py:31-42` (`get_capabilities`) |

Càrrega útil: `id`, `profile_id` (`serializers.py:63-65`), `username`, `first_name`, `last_name`,
`email` (`:30`), `full_name` (`:39-44`), `avatar_url` (**sempre `None`**, placeholder `:46-49`),
`nom_complet` (`:51-53`), `rol_nom` (`:55-57`), `color_avatar` (`:59-61`), `capabilities`
(`:67-68`) i `legal_pending`, injectat **fora del serializer**, a la view (`views.py:52-58`).

🔵 **Camps del tenant a `/me`: CAP.** `MeSerializer` no toca `tenants.Client` en absolut.
La view **sí** té el tenant a la mà — `client = getattr(request, 'tenant', None)`
(`accounts/views.py:54`) — però només el passa a `pending_versions_for_client()`. `nom`,
`codi_tenant`, **`tipologia`**, `plan`, `unitats`, `moneda`, `idioma`, `estat`: **NO EXISTEIXEN**
a la resposta.

**Consumidors al frontend:**

| Consumidor | Fitxer:línia | Què en guarda |
|---|---|---|
| Client API | `frontend/src/api/endpoints.js:672-675` | `me.get()` → `/api/v1/me/` |
| **Store zustand (font única)** | `frontend/src/store/auth.js:81-99` (`fetchMe`) | Només `{id, username, nom_complet, rol_nom, color_avatar, capabilities}`. **Descarta** `profile_id`, `email`, `full_name`, `avatar_url` i `legal_pending` |
| Gating d'UI | `frontend/src/store/auth.js:102` (`hasCapability`) | Llegeix `user.capabilities` |
| `fetch` directe (bypass del store) | `Dashboard.jsx:370-373`, `WorkPlan.jsx:185-187`, `TaskTree.jsx:91` | estat local |

`legal_pending` es calcula a **cada** `/me` i **cap consumidor el llegeix** (grep a `frontend/src`
i `frontend-backoffice/src` → 0 resultats). Precedent útil: **ja hi ha camp injectat a la view que
el store ignora**; afegir-n'hi un altre no trencaria res, però tampoc arribaria enlloc sol.

L'endpoint bessó del backoffice és un altre món: `BackofficeMeView` (`backoffice/views.py:46-55`,
ruta `backoffice/urls.py:35`), consumit per `frontend-backoffice/src/store/authStore.js:8`.

### 6.2 `feature_flags`: el camp existeix dues vegades i no el llegeix ningú

Grep exhaustiu de `feature_flags` a `fhort/**/*.py` (fora de migracions) — **6 hits, cap de decisió**:

| Ocurrència | Fitxer:línia | Naturalesa |
|---|---|---|
| `Plan.feature_flags` (JSONField) | `tenants/models.py:46` | definició, al **pla** |
| `Client.feature_flags` (JSONField) | `tenants/models.py:123` | definició, al **tenant** |
| `feature_flags={}` al seed del pla Free | `backoffice/.../seed_free_plan.py:39` | escriptura literal buida |
| a `ClientDetailSerializer.Meta.fields` | `backoffice/serializers_tenants.py:59` | **única lectura API** (només detall backoffice) |
| «el gate de tier (feature_flags) arriba a B5» | `commerce/views.py:5` | docstring, no codi |

🚩 **Bandera 7 — el formulari del backoffice edita `feature_flags` i el serializer ho llença.**
`TenantFormPage.jsx` el valida com a JSON (`:147-149`), el pinta (`:350-354`) i el posa al payload
(`:172`) → però **ni `ClientUpdateSerializer.Meta.fields` (`serializers_tenants.py:178-186`) ni
`ClientCreateSerializer` (`:194-202`) l'inclouen**. L'operador creu que l'edita i **no l'edita mai**.
Silenciós: DRF ignora camps no declarats sense error.

Al frontend de tenant (`frontend/src`), `feature_flags`: **NO EXISTEIX** (grep 0 resultats).

**Contingut real a BD (staging):**

| tenant | `tipologia` | `plan_id` | `feature_flags` |
|---|---|---|---|
| `SYS` / public | estudi | NULL | `{}` |
| `FTT` / fhort | estudi | NULL | `{}` |
| `LOS` / los | marca | 7 | `{}` |

| pla | tipologia | `feature_flags` |
|---|---|---|
| Free (id 2) | estudi | `{}` |
| Team (id 7) | *(buit)* | `{}` |

**`{}` a tot arreu, als 3 tenants i als 2 plans.** A més, **2 dels 3 tenants tenen `plan_id = NULL`**
— o sigui que un gate que depengués del pla no tindria pla a què preguntar per a `fhort`.

**`TenantConfig` (`accounts/models.py:30-83`) NO duplica el concepte de flags**: és configuració de
contingut (unitats, norma, identitat fiscal de l'emissor per als PDFs), sense cap booleà ni JSON de
capacitats. **Sí duplica el d'unitats**: `TenantConfig.unitat_mesura` (`CM`/`INCH`, llegit a
`pom/s6_views.py:12-13`, `s9_views.py:20-22`, `s10_views.py:12-13`) vs `Client.unitats`
(`cm`/`inch`, `tenants/models.py:128`) — dos camps, dos schemes, dos vocabularis.

🔵 **Hi ha TRES eixos de "capacitat" i estan desconnectats entre si:**

1. **Per USUARI** — `accounts/capabilities.py:6-56` (rol + overrides). **L'únic que arriba a `/me`.**
2. **Per PLA** — `Plan.max_models_actius`, `max_usuaris`, `storage_gb`, `ia_credits_mes`,
   `models_inclosos` (`tenants/models.py:42-53`). **Cap lector al backend de tenant.**
3. **Per TENANT** — `feature_flags` (Plan + Client). Buits i sense lectors.

**Què falta perquè `/me` exposi `feature_flags`** (fets, no disseny):

- *Ja existeix*: el camp migrat (`tenants/models.py:123`), l'accés al tenant dins la view
  (`accounts/views.py:54` — precedent d'incursió tenant→public dins `/me`), el consumidor de destí
  (`store/auth.js:81-99` + `hasCapability:102`) i l'editor d'operador ja dibuixat.
- *Peça nova*: (a) el camp al payload — `MeSerializer` es crida **sense `context`**
  (`views.py:52`), per tant o s'injecta a la view a l'estil de `legal_pending` (`:55-58`) o cal
  passar-li context; (b) el **camí d'escriptura** (bandera 7); (c) **cap funció fusiona
  `Plan.feature_flags` amb `Client.feature_flags`** — **NO EXISTEIX** helper d'override a tot el
  backend; (d) **cap vocabulari controlat de flags** (compara amb `ALL_CAPABILITIES`,
  `capabilities.py:15-18`) — **NO EXISTEIX**; (e) cap gate de lectura al backend: `commerce/views.py:5`
  ho difereix a «B5».

### 6.3 Mapa del login únic en curs (per NO xocar-hi)

Tot l'sprint F1/F2/F3 és **d'avui, 2026-07-22**, a `dev`:

| Commit | Què | Fitxers |
|---|---|---|
| `66d6798` | `CodiAuth`, el tiquet d'un sol ús | `tenants/migrations/0006_codiauth.py`, `tenants/models.py` |
| `f4893ad` | la porta única prova credencials a CADA schema (F1-C1) | `tenants/auth_central_service.py`, `views_auth_central.py`, `fhort/urls.py`, `urls_public.py` |
| `b22721e` | bescanvi de codi per sessió AL HOST DEL TENANT (F2-C3) | `tenants/views_bescanvi.py`, `fhort/urls.py` |
| `27f5762` | 22 tests del login únic | `tenants/tests_login_unic.py` |
| `407a323` / `4fb4d25` / `865c566` | `/entrar` de debò + veto d'UI + token ranci | `frontend/src/{api/client.js,api/endpoints.js,pages/Entrar.jsx,store/auth.js,i18n/*}` |

`git diff --stat 66d6798~1..HEAD` sobre accounts/tenants/front-auth: **+1033 / −32, 9 fitxers**.
**`accounts/` NO hi apareix** (últim toc: `93cb51a`, 2026-07-17, `legal_footer` de `TenantConfig`).

Rutes del flux: `POST /api/auth/central/` (`fhort/urls.py:33` **i** `urls_public.py:42`, als dos
urlconf a posta), `POST /api/auth/central/tria/` (`urls.py:34`, `urls_public.py:43`),
`POST /api/auth/bescanvi/` (`urls.py:38`, **només al tenant, mai al public**). Servei:
`tenants/auth_central_service.py` (`autentica_cross_schema:56`, `resol_host:84`,
`descriu_workspace:114`, `emet_codi:146`, `consumeix_codi:161`). Throttle 20/h per IP
(`views_auth_central.py:54-72`). Pantalla `/entrar` a `frontend/src/App.jsx:244`.

🔵 **La forma amb què el servidor descriu avui un workspace** (`auth_central_service.py:123-128`)
és `{schema, nom, host, mateix_host}` — **cap `codi_tenant`, cap `tipologia`, cap `plan`, cap
`feature_flags`**. És el segon lloc (amb `/me`) on el frontend podria saber de quina mena de casa
és, i tampoc ho sap.

**Fitxers CALENTS — un disseny de gates de federació no els hauria de tocar aquesta setmana:**

| Fitxer | Per què |
|---|---|
| `tenants/models.py` | tocat avui (`66d6798`, +67 l.). **Hi viu també `Client.feature_flags:123`** → conflicte segur |
| `tenants/migrations/0006_codiauth.py` | cap de branca: tota migració nova de `tenants` hi ha de dependre |
| `tenants/auth_central_service.py`, `views_auth_central.py`, `views_bescanvi.py`, `tests_login_unic.py` | nous avui (186+159+78+291 l.) |
| `fhort/urls.py`, `fhort/urls_public.py` | tocats a `f4893ad` i `b22721e` |
| `frontend/src/store/auth.js` | tocat 2× avui. **És exactament on aniria `feature_flags` del `/me`** → col·lisió de disseny, no només de merge |
| `frontend/src/api/client.js`, `pages/Entrar.jsx`, `api/endpoints.js`, `i18n/{ca,en,es}.json` | tocats avui |

**Fitxers FREDS i segurs** (cap commit des del 2026-07-17): `accounts/serializers.py` (`MeSerializer`),
`accounts/views.py` (`me_view`), `accounts/capabilities.py`, `backoffice/serializers_tenants.py`,
`frontend-backoffice/src/pages/TenantFormPage.jsx`.

### Veredicte BLOC 6: **llest, amb 1 bandera i 1 col·lisió de calendari**

- **`/me` no diu res del tenant.** Cap camp de `Client` hi arriba (`accounts/serializers.py:13-68`),
  tot i que la view ja té `request.tenant` a la mà (`views.py:54`). El frontend **no sap si és un
  Studio o una Brand**: `tipologia` existeix (§5.2) però no viatja.
- **`feature_flags` existeix per duplicat (`Plan:46` + `Client:123`), és `{}` a tot arreu, i té zero
  lectors de decisió.** L'única exposició és de lectura al detall del backoffice
  (`serializers_tenants.py:59`).
- 🚩 **Bandera 7 — l'edició de `feature_flags` al backoffice és un miratge**: el formulari l'envia
  (`TenantFormPage.jsx:172`) i els serializers d'alta/edició **no el declaren**
  (`serializers_tenants.py:178-186`, `:194-202`) → es descarta en silenci.
- **NO EXISTEIX** cap fusió `Plan.feature_flags` ↔ `Client.feature_flags`, ni vocabulari de flags,
  ni cap gate que en llegeixi cap. El gate de tier està explícitament diferit («B5»,
  `commerce/views.py:5`).
- **Col·lisió de calendari**: l'sprint de login únic (7 commits, tots d'avui) posseeix
  `tenants/models.py`, `fhort/urls*.py` i **`frontend/src/store/auth.js`** — els tres llocs naturals
  d'un gate de federació. La via freda és `accounts/` (`MeSerializer` + `me_view`), intacta des del 17.

---

## BLOC 7 — Bulk import: el model pot néixer al Studio (correcció C5)

### 7.1 Les peces, la màquina d'estats i on es crea el `Model`

| Model | Fitxer:línia | Nucli |
|---|---|---|
| `ModelSequence` | `models_app/models.py:760-778` | `customer` FK PROTECT (`:766`), `year`, `season`, `last_seq`, **`unique_together (customer, year, season)`** (`:773`) |
| `BulkCollectionImport` | `models_app/models.py:781-809` | `customer` FK PROTECT (`:792`), `document` (`upload_to='bulk_imports/%Y/%m/'` `:794`), `estat` (`:795`), `creat_per`→`accounts.UserProfile` (`:797`), `resum`/`resultat` JSON (`:800-801`) |
| `BulkCollectionRow` | `models_app/models.py:812-836` | `importacio` CASCADE (`:821`), `row_num`, `raw_data` JSON, `estat`, `errors` JSON, `model_creat`→`Model` SET_NULL (`:827`) |
| Migració | `models_app/migrations/0033_bulkcollectionimport_bulkcollectionrow_modelsequence.py` | |

**Màquina d'estats declarada vs. usada.** Declarats 5 (`PUJAT/VALIDANT/PREVISAT/IMPORTAT/DESCARTAT`,
`models.py:785-791`); **escrits només 2**: `PREVISAT` a l'alta (`bulk_import_views.py:86`) i
`IMPORTAT` al commit (`bulk_import_service.py:569`). `PUJAT`, `VALIDANT`, `DESCARTAT`: **NO EXISTEIX**
cap escriptura, ni endpoint de descart. Única guarda de transició: `bulk_import_views.py:114`
(`if imp.estat == 'IMPORTAT'` → 400).

**On es creen els objectes:**

| Objecte | Fitxer:línia |
|---|---|
| `BulkCollectionImport` | `bulk_import_views.py:85-89` (+ `document.save()` `:90`) |
| `BulkCollectionRow` | `bulk_import_views.py:92-96` (`bulk_create`) |
| **`Model`** | **`bulk_import_service.py:533`** (`bulk_create`), instàncies a `_build_model` (`:578-598`) |
| `GarmentSet` | `bulk_import_service.py:517` |
| `SizeFitting` | `bulk_import_service.py:536-540` (un per model, `numero=1`, `codi={codi_intern}-SF1`, `tipus='Proto'`) |
| `Watchpoint` | `bulk_import_service.py:546-551` (per model amb config incompleta) |

**NO crea**: `ModelTask`/tasques (explícit a `seed_losan_models.py:5`), `Customer` (ha d'existir ja,
`bulk_import_views.py:26-30` només el llegeix), ni cap entitat `Collection` — **`Model.collection`
és un `CharField`** (`models_app/models.py:144`) i **la classe `Collection` NO EXISTEIX**.

🔵 **La numeració: SÍ passa per l'escapatòria, i amb doble blindatge.**

- L'escapatòria és a **`models_app/signals.py:37-39`** (confirmat: `tasks/signals.py` té 17 línies i
  cap receiver de codi — només declara `model_consumption_started`):
  ```python
  # El caller ja mana el codi (i el seu sequencial) → no interferir.
  if getattr(instance, 'codi_intern', None):
      return
  ```
- `_build_model` sempre passa `codi_intern=` ja calculat (`bulk_import_service.py:580-581`) i
  `sequencial=seq or 1` (`:586`).
- A més, **`bulk_create` bypassa els signals** — comentat a posta a `bulk_import_service.py:483` i `:530`.

El codi es genera al pipeline, no al signal: `_plan_codes` (`:456-476`) →
`f"{customer.codi}-{season}{yy}-{str(seq).zfill(4)}"` (`:471`), conjunts consumint 1 número (`:474`),
peces `f"{gset.codi_base}-{str(pn).zfill(2)}"` (`:524`). La font del número al **commit** és
`reserve_sequence_range(customer, year, season, n)` (`:503-505` → `models_app/services.py:38-71`) amb
`select_for_update` (`services.py:60`) i **terra = `max(comptador, MAX(sequencial) real)`**
(`services.py:63`, `_real_max_seq` `:74-81`). Al **dry-run** només `sequence_floor(...)+1` (`:725` →
`services.py:84-98`), sense reservar.

### 7.2 El destí: el schema actiu és implícit, i són 16 baules

🔵 **`schema_context` al camí del bulk: NO EXISTEIX.** Grep sobre `bulk_import_views.py`,
`bulk_import_service.py`, `models_app/services.py`, `models_app/signals.py` → **0 resultats**. El
schema el fixa `TenantMainMiddleware` per host (`settings.py:87`). El `customer_id` **sí** és
paràmetre, però es resol sense schema (`bulk_import_views.py:26-30`) → és un `Customer` **del tenant
actiu**. Cap dels 5 endpoints (`models_app/urls.py:148-152`) accepta un tenant destí.

**Dependències del tenant actiu que caldria resoldre per escriure a un schema ≠ actiu:**

| # | Dependència | Fitxer:línia | App |
|---|---|---|---|
| 1 | `Customer` (pk sense schema) | `bulk_import_views.py:26-30`; reusat `service:491,717` | `tasks` (TENANT) |
| 2 | `request.user.profile` → `UserProfile` (`creat_per`, `Model.responsable`, `SizeFitting.creat_per`) | `views:56,112`; `service:596,537` | `accounts` (TENANT) |
| 3-6 | `GarmentType`, `GarmentTypeItem`, `Target`, `ConstructionType` | `service:63-66,73,83,91` | `pom`/`tasks` del tenant actiu |
| 7 | `SizeSystem` + `SizeDefinition` (matching de run) | `models_app/matching.py:64-77` ← `service:232,298` | `pom` |
| 8 | `run_del_model` (grading utils) | `service:330-331` | `pom` |
| 9 | `TEMPORADA_CHOICES` + dedup per customer | `service:271-272,386-388,432-434` | `models_app` |
| 10 | **`ModelSequence`** (numeració del destí) | `services.py:57-59` (`get_or_create`+`select_for_update`), `:93-95` | **ha de córrer DINS el schema destí perquè la numeració sigui la del destí** |
| 11 | `_real_max_seq` sobre `Model` del destí | `services.py:74-81` | |
| 12 | Anti-col·lisió `codi_intern__in` | `service:735-736` | |
| 13 | Escriptures (`Model`, `GarmentSet`, `SizeFitting`, `Watchpoint`, rows, import) | `service:517,533,540,551,557,564,572` | **el staging viu al MATEIX schema que els Models creats** |
| 14 | **Media**: `TenantFileSystemStorage`, `MULTITENANT_RELATIVE_MEDIA_ROOT='%s'` (=schema) | `settings.py:175,180,188,190-192`; escriptura `views:90` | l'Excel es desa a `MEDIA_ROOT/<schema actiu>/bulk_imports/…` → **document i models es partirien entre dos arbres** |
| 15 | **JWT tenant claim** | `fhort/auth_jwt.py:49,78` (rebutja si `token[TENANT_CLAIM] != connection.schema_name`) | **un import cross-tenant no té token vàlid per al destí** |
| 16 | `transaction.atomic()` únic | `service:501` | el `select_for_update` de la seqüència s'aplica al schema **actiu** de la connexió |

`TenantConfig`: **NO EXISTEIX** cap lectura al camí del bulk.

🔵 **El patró "canviar de schema abans d'entrar al pipeline" JA està provat** — però només per
management command: `seed_losan_models.py:63-64` embolica tot el `_run` dins
`schema_context(opts['schema'])` (default `'fhort'`) i **reusa `_build_model` (`:212`) i
`reserve_sequence_range` (`:191`)**. El pipeline és, doncs, schema-agnòstic *si* se li obre el context
a fora; el que és cablejat és **el camí HTTP** (baules 1, 2, 14, 15).

### 7.3 Format d'entrada: només Excel, 15 columnes, 3 obligatòries

- **Només `.xlsx`/`.xls`** (`bulk_import_views.py:71-73`). CSV/JSON en aquest flux: **NO EXISTEIX**
  (el CSV només l'usa `seed_losan_models.py:11,120`). Llibreria: **openpyxl**
  (`bulk_import_service.py:115-118`, `:198-199`, `:771`); **pandas NO EXISTEIX** al camí.
- Parser `parse_upload` (`bulk_import_service.py:195-224`): full `'Plantilla'` (fallback `wb.active`,
  `:205`), capçalera a la fila 1 (`:209`), dades des de la 2 (`:212`), files buides ignorades (`:222`).
  Full ocult `'_meta'!A1 = customer.codi` (`:202-203`) → **validació anti-mismatch de client**
  (`bulk_import_views.py:76-80`).
- **Columnes** (font única `bulk_import_service.py:15-19`), en ordre: `nom_prenda`, `familia`,
  `tipus`, `any`, `temporada`, `target`, `construccio`, `run_talles`, `talla_base`, `codi_client`,
  `col·leccio`, `color_referencia`, `es_conjunt`, `referencia_conjunt`, `piece_number`.
  - **Obligatòries (3)**: `nom_prenda`, `any`, `temporada` (`:22`, validades `:238-240`).
  - Amb desplegable: `familia`, `tipus`, `any`, `temporada`, `target`, `construccio` (`:23`,
    `:177-186`, files 2..601 — `NROWS=600` `:176`).
  - Condicionals: `referencia_conjunt` si `es_conjunt` (`:312-314`); `piece_number` si hi ha
    `referencia_conjunt` (`:316-318`); `talla_base` ha de pertànyer al `run_talles` (`:297-304`).
- **Plantilla generada per client** (`generate_template_bytes`, `:113-190`), amb fulls
  `Instruccions` (`:136-149`), `Plantilla` (`:126-132`) i ocults de vocabulari (`:153-173`).
  Endpoint: `GET /api/v1/bulk-import/template/?customer_id=X` (`bulk_import_views.py:32-44`).
  **Fitxer .xlsx d'exemple versionat: NO EXISTEIX.**
- **Endpoints** (`models_app/urls.py:139-155`, import defensiu dins `try/except`): `template/` (`:148`),
  `upload/` (`:149`, MultiPart `views:49`), `<id>/reconciliation/` (`:150` → `reconcile()` `:706-763`),
  `<id>/commit/` (`:151` → `commit_import()` `:481`, 409 en `IntegrityError` `views:126-131`),
  `<id>/errors-report/` (`:152`). Tots `IsAuthenticated`; **cap check de capability** més enllà de
  tenir `profile` (`views:56,112`).
- **Frontend**: `endpoints.js:316-327`; wizard de 4 passos `BulkImportWizard.jsx:47` (upload+
  reconciliation encadenats `:83-101`, commit `:114-124`); `BulkImportReconciliation.jsx:22`; ruta
  `App.jsx:277` (`models/importar-colleccio`); entrada `Models.jsx:526`. Tests:
  `models_app/tests_bulk_import.py` (355 línies).

### 7.4 Dades reals a staging: la correcció C5 ja ha passat, i sense retorn

**Schema `fhort` (el Studio):**

- `bulkcollectionimport`: **3 files** — id 3 (customer 1 `FTT`, 2 creats), id 4 (customer 7 `BRW`,
  15 creats), id 11 (customer 7 `BRW`, 20 creats). Totes `IMPORTAT`, 0 errors, 0 duplicats.
- `bulkcollectionrow`: **37 files, totes OK, 37/37 amb `model_creat_id` no nul**.
- `modelsequence`: `(customer 1, 2027, FW)=2`, `(customer 7, 2026, FW)=35`, **`(customer 6, 2027, SS)=962`**.
- `models_app_model`: **1005 models** — `LOS`=962, `BRW`=41, `FTT`=2.
- `tasks_customer`: 1 `FTT` (self), 6 `LOS` (LOSAN IBERIA SA), 7 `BRW` (Brownie SL).

**Schema `los` (el Brand):** `bulkcollectionimport` **0** · `bulkcollectionrow` **0** ·
`modelsequence` **0** · `models_app_model` **0** · `tasks_customer` 1 fila (`LOS`, self).

🔵 **Fet dur.** Els **962 models de LOSAN i el seu comptador `ModelSequence` viuen al schema `fhort`
(el Studio)**; el tenant `los` (el Brand) està **buit de models**. Van entrar per
`seed_losan_models.py` amb `schema_context('fhort')` (`:63-64`). La correcció C5 no és una hipòtesi:
**ja és l'estat de staging**. I **no existeix cap camí de retorn**: grep de `schema_context` a tot
`fhort/` retorna només tests, `backoffice/receivers.py:10` i `invoice_pdf.py:50` (cap a `public`),
`patterns/.../materialize_segments.py:46`, `tasks/.../retype_scaling_to_grading.py:36`,
`bootstrap_tenant.py:111,198,213,219,376` (còpia de **catàlegs** en crear tenant, mai de `Model`) i
`seed_losan_models.py:63`. **Cap endpoint, comanda o servei sembra Models de `fhort` cap a `los`.**

### Veredicte BLOC 7: **llest, amb 1 bandera i 1 fet que canvia el calendari**

- **El bulk NO consumeix el signal de numeració**: doble blindatge (escapatòria
  `models_app/signals.py:37-39` + `bulk_create` que bypassa signals, `:483,530`). El número surt de
  `reserve_sequence_range` (`models_app/services.py:38-71`) amb `select_for_update` i terra real.
  **Un naixement al Studio i una sembra al Brand poden numerar-se amb la mateixa primitiva.**
- **El pipeline és schema-agnòstic; el camí HTTP no.** `seed_losan_models.py:63-64` ja demostra que
  embolicar `_run` en `schema_context` funciona i reusa `_build_model`/`reserve_sequence_range`. Les
  baules que ho impedeixen per HTTP són **4**: `Customer` del tenant actiu (1), `UserProfile` (2),
  **media per-schema** (14) i **el claim `tenant_schema` del JWT** (15).
- 🚩 **Bandera 8 — la sembra de retorn Studio→Brand NO EXISTEIX en cap forma.** 962 models `LOS` i el
  comptador `(customer 6, 2027, SS)=962` viuen a `fhort`; `los` té **0 models i 0 ModelSequence**.
  `bootstrap_tenant` copia **catàleg**, mai `Model` (`_spec()` `:127-167`). Si dilluns LOSAN ha de
  veure els seus models des del seu propi tenant, **la peça no existeix ni parcialment**.
- **Format tancat i ja usat en producció interna**: Excel de 15 columnes, 3 obligatòries, plantilla
  generada per client amb `_meta` anti-mismatch. 37 files importades històricament, 0 errors.
  "El client ens passa el seu Excel" **ja funciona avui** — el que no funciona és **a quina casa aterra**.
- **Sense control d'accés propi**: els 5 endpoints només demanen `IsAuthenticated` + `profile`
  (`bulk_import_views.py:56,112`). Un import cross-tenant hi hauria d'afegir el seu propi gate.

---

## BLOC 8 — SÍNTESI EXECUTIVA

### 8.1 El camí crític, peça a peça

| # | Peça | Fets que la suporten | Ja existeix i és reutilitzable | Peça nova mínima | Banderes |
|---|---|---|---|---|---|
| 1 | **TenantLink + token** (el pont Studio↔Brand) | §5.1-5.7: cap taula vincula dos `Client`; `CodiAuth` és el precedent viu de relació cross-origen a `public` (`tenants/models.py:224-296`) amb `tenant_schema` CharField, no FK (`:281`) | `Client.tipologia` (`tenants/models.py:118`) **ja existeix, és obligatòria i les dades ja són correctes** (FTT=estudi, LOS=marca); `Customer.codi_global` (`tasks/models.py:207`) amb la seva escriptura feta (`bootstrap_tenant.py:353-355`); l'app `tenants` ja és on viu tot el cross-casa | **1 model a `fhort/tenants/`** amb referència per `schema_name`/`codi_tenant` (mai FK), + estat de token. **NO a `backoffice`**: invertiria l'única dependència neta (§5.5) | 🚩6 (`tipologia` inert), 🚩7 |
| 2 | **`Model.origen = EXTERN`** | §2.6: no existeix cap marca de provinença; §2.7: la semàntica de federació ja té precedent viu | L'escapatòria `models_app/signals.py:37-39` permet crear amb codi imposat **sense consumir seqüència** (§2.5, confirmat de nou a §7.1) | **1 camp + 1 migració additiva** (SQL de PROD ja redactat a §2.8) | 🚩1 (terra de seqüència), 🚩2 (dos formats de `codi_intern`) |
| 3 | **Instanciació** (el model del Brand vist des del Studio) | §2.1: 4 camins de creació; §2.2-2.3: camps obligatoris i tres lleis de numeració | `_build_model` (`bulk_import_service.py:578-598`) i `reserve_sequence_range` (`models_app/services.py:38-71`) són **schema-agnòstics si se'ls obre el context a fora** (provat a `seed_losan_models.py:63-64`) | Cap model nou; **un caller que obri `schema_context` i imposi `codi_intern`** | 🚩1, 🚩2 |
| 4 | **Gateway de llistat** (llegir catàleg d'una altra casa) | §1.2: inventari de `schema_context`; §1.5: la llei de la referència per id/codi nu; §3.1: les 6 crides del wizard | `discovery_service.py` (`tenants/`) és **l'únic runtime que decideix el schema per dades**; `bootstrap_tenant._read_source` (`:192-198`) ja llegeix d'un schema origen | **Una funció que torni DICTS, mai objectes ORM** (C4). El punt d'injecció és `_resolve_garment_def` (§3.5) | 🚩3 (els 4 lookups desen objectes ORM, no ids) |
| 5 | **Materialització quirúrgica** (aplicar catàleg aliè) | §1.3: `bootstrap_tenant` és **la primitiva tenant→tenant que ja existeix i que ja copia**; §5.5: `SeedProfile` és el motlle de govern en vocabulari de **blocs**, no de pks | `_copy_piece` + `_resolve_deferred` + `_spec()` (`bootstrap_tenant.py:224-334`, `:127-167`) — 2a passada de FKs inclosa | **Un `--profile` acotat** (o equivalent) per copiar un subconjunt, no el catàleg sencer | 🚩3 |
| 6 | **ACTOR a la meritació** | §4.1-4.4: la cadena completa; **8 camps a l'event, cap d'ells actor/tenant/schema**; l'actor **ja divergeix avui amb dades** | `get_or_create` per `opaque_ref` (`backoffice/receivers.py:7-18`) → **els events ja meritats no es reescriuen**; els consumidors filtren per `codi_client` → **cap import es mou** | **1 migració additiva + 2 emissors + 1 receiver** (cost tancat a §4.4) | 🚩4 (18 events `BRW` orfes, 9 `LOS` meritats des de `fhort`), 🚩5 (5 de 31 events sense `ConsumptionRecord`) |
| 7 | **Sembra de retorn** (Studio → Brand) | §7.4: **962 models `LOS` viuen a `fhort`; `los` té 0 models i 0 `ModelSequence`**; cap `schema_context` mou `Model` enlloc | `bootstrap_tenant` prova que la còpia cross-schema transaccional funciona — **però copia catàleg, mai `Model`** (`_spec()`) | **La peça que NO EXISTEIX ni parcialment.** Cal decidir-la sencera | 🚩8 |
| 8 | **Bulk cross-schema** (l'Excel del client) | §7.2: 16 baules al tenant actiu; §7.3: format tancat (15 col., 3 obligatòries) ja usat (37 files, 0 errors) | Tot el pipeline de parseig/conciliació/commit; plantilla per client amb `_meta` anti-mismatch (`bulk_import_service.py:202-203`) | Desbloquejar **4 baules**: `Customer` (1), `UserProfile` (2), **media per-schema** (14), **claim `tenant_schema` del JWT** (15) | 🚩8 |

**Peces transversals que ja hi són i que ningú fa servir** (cost zero de creació, cost real d'activació):
`Client.tipologia` (§5.2), `Customer.codi_global` (§5.3), `Client.feature_flags` + `Plan.feature_flags`
(§6.2), `Plan` limits (§6.2). **Els quatre tenen zero consumidors de domini.**

### 8.2 Decisions obertes per al CTO

1. **On viu el `TenantLink`** — `fhort/tenants/` (recomanat pels fets: §5.5, §5.6) o `backoffice`.
   Decidir-ho fixa la direcció de dependència per a tot el que vingui després.
2. **Referència per codi nu o per FK.** Els fets apunten a codi nu (`CodiAuth.tenant_schema:281`,
   §1.5), però `Client` és al mateix schema i una FK seria tècnicament possible. Cal tancar-ho.
3. **`Customer.codi_global`: es backfilla i es fa unique?** Avui **NULL als 4 customers** i **sense cap
   índex ni constraint** (§5.8). Si el vincle hi aterra, el vincle hereta aquesta manca d'integritat.
4. **Què fa `tipologia` quan s'activi** (§5.2). És el primer consumidor de domini d'un camp inert. A
   més: **els tests hi escriuen `'MARCA'` en majúscules** (fora de choices, ~18 fitxers) — decidir si
   es normalitza abans o després.
5. **Actor a la meritació: es backfilla o no?** Els 18 events `BRW` orfes i els 9 `LOS` meritats des
   de `fhort` (🚩4) ja existeixen. La migració és additiva i no els toca — **decidir si es deixen com
   estan** o es reparen.
6. **`feature_flags`: Plan o Client, i com es fusionen?** No hi ha helper d'override, ni vocabulari de
   flags, ni gate lector (§6.2). I **2 de 3 tenants tenen `plan_id = NULL`**.
7. **`/me` s'amplia ara o s'espera al login únic?** `frontend/src/store/auth.js` és el lloc natural i
   **s'ha tocat dues vegades avui** (§6.3). La via freda és `accounts/` (`MeSerializer`/`me_view`).
8. **La sembra de retorn Studio→Brand: entra a l'abast o es difereix?** És l'única peça del camí
   crític que **no té ni una baula construïda** (🚩8) i és, alhora, la que decideix on veurà LOSAN
   els seus 962 models.
9. **El bulk cross-schema: HTTP o management command?** Per command el patró ja està provat
   (`seed_losan_models.py:63-64`); per HTTP calen les 4 baules de §8.1-8 (media i JWT inclosos).
10. **Materialització quirúrgica: vocabulari de blocs o de pks?** `SeedProfile` fixa el precedent de
    "public governa parlant de producte" (§5.5). Si s'admeten pks de catàleg, es trenca la frontera.

### 8.3 Riscos per a dilluns LOSAN, per severitat

| # | Risc | Severitat | Fets |
|---|---|---|---|
| R1 | **LOSAN no té els seus models a la seva casa.** 962 models `LOS` viuen al schema `fhort`; el tenant `los` està **buit** (0 models, 0 `ModelSequence`, 0 imports) i **no existeix cap camí per moure'ls** | 🔴 **Bloquejant si dilluns s'espera que LOSAN entri al SEU tenant** | §7.4, 🚩8 |
| R2 | **El tenant `los` està en `estat='onboarding'`** amb `plan_id=7` (Team, no Free) → **`_llanca_sembra_free` no s'ha disparat mai** i el bootstrap no s'ha tancat | 🔴 Alt | §6.2 (BD), `views_tenants.py:103-104` |
| R3 | **La meritació cross-casa ja passa i no queda registrada.** 18 events `BRW` orfes de facturació + 9 events `LOS` meritats des de `fhort` | 🟠 Alt — **contamina la facturació abans que la federació existeixi** | 🚩4 |
| R4 | **Col·lisió amb l'sprint de login únic** (7 commits, tots del 22/07): `tenants/models.py`, `fhort/urls*.py` i `frontend/src/store/auth.js` són exactament els tres punts d'un gate de federació | 🟠 Alt — de calendari, no de disseny | §6.3 |
| R5 | **El frontend no sap de quina mena de casa és.** Ni `/me` ni `descriu_workspace` exposen `tipologia`. Qualsevol UI diferenciada Studio/Brand no té d'on llegir-ho | 🟠 Mitjà-alt | §6.1, §6.3 |
| R6 | **`codi_global` buit i sense integritat** (NULL×4, sense unique ni índex) → el vincle no té on aterrar dins el schema | 🟡 Mitjà | §5.8 |
| R7 | **El terra de seqüència s'enverina** si entren codis externs sense marca de provinença (🚩1) i **conviuen dos formats de `codi_intern`** (🚩2) | 🟡 Mitjà | §2.3, §2.8 |
| R8 | **Els lookups del wizard desen objectes ORM, no ids** → una lectura en viu cross-schema els corromp (motiu de la correcció C4) | 🟡 Mitjà | 🚩3 |
| R9 | **`feature_flags` s'edita al backoffice i es descarta en silenci** → qualsevol gate que s'hi recolzi serà inoperant sense que ningú ho vegi | 🟡 Mitjà | 🚩7 |
| R10 | **Divergència silenciosa public↔tenant**: 5 de 31 events sense `ConsumptionRecord`; `reconcile_consumption` només mira el forat contrari | 🟢 Baix (avui), creixent amb el volum | 🚩5 |
| R11 | **Client + schema orfe** si falla la creació del `Domain` a l'alta HTTP — compromís acceptat al codi, sense comanda de neteja | 🟢 Baix | `views_tenants.py:87-89` |

**El risc dominant no és de disseny: és R1 + R2.** Vuit de les nou peces del camí crític tenen
precedent viu al codi; la que no en té (sembra de retorn) és precisament la que decideix si dilluns
LOSAN treballa a casa seva o a casa del Studio.

---

*Fi de la diagnosi. Cap línia de codi tocada. El disseny és de demà (Patró C).*
