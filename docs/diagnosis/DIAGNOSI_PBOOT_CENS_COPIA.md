# DIAGNOSI — P-BOOT Pas 1: cens de la superfície de còpia (`bootstrap_tenant`)

Data: 2026-07-10 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`

**Abast:** mapa exacte del que `bootstrap_tenant <schema> --from fhort` haurà de copiar, en quin
ordre i amb quines trampes. **No es dissenya la comanda: es censa.**

**Convenció:** cada afirmació porta `fitxer:línia` o sortida literal. `"NO EXISTEIX"` = confirmat
absent al codi/BD (no especulat). Propostes marcades `💡 PROPOSTA (a validar)`.

**Guardes de concurrència (re-verificades a l'inici):** territori `tasks/**` i `commerce/**` net.
La sessió paral·lela treballa a `models_app/fitxers` (commits `5159843`, `c6b4112`, `964ca07`).
Els meus commits de P-LLEI (`51a113e`, `a09ab20`) segueixen a la història. Última migració de
`models_app` = `0055_modelfitxer_derivat_de_item`; **el `~0056` amb `derivat_de_model` encara no
hi és** — si apareix, és de l'altra sessió, no drift.

**Verificació:** BD `ftt_staging` (127.0.0.1:5433), només `SELECT`. Cap comanda de seed executada,
ni amb `--dry-run`.

---

## Resum executiu

1. **Tot el catàleg neix BUIT en un tenant nou.** Cap migració de `pom` sembra catàleg: les 7
   `RunPython` de `pom` són transformacions, i **cap migració de cap app fa
   `POMGlobal.objects.create/update_or_create`**. Les 125 files de `POMGlobal` a `fhort` (i les
   125 de `public`) hi són perquè algú va córrer commands a mà. **Resposta a la pregunta del
   brief: un tenant nou neix amb POMGlobal = 0.** Tot el cens s'ha de copiar.

2. **🛑 No hi ha cap discriminador estructural canònic-vs-derivat a `GradingRuleSet`.** Dels
   **25** rulesets de `fhort`, **només 2 tenen `customer_id`** — i tots dos són **LOS**, no
   Brownie. El run de Brownie (`rs110`) té `customer_id = NULL`. Una còpia automàtica **no pot
   distingir** un canònic d'un run de client per cap camp. Contradiu la llei RUN-CLIENT. **STOP:
   decisió CTO abans de qualsevol còpia de grading.**

3. **Correcció a la premissa del brief.** «rs111, rs107 i companyia» **no són de Brownie**:
   `rs111` és `EU ALPHA LOS TOP KNIT REGULAR V01` (customer LOS) i `rs107` és
   `Importació fitxa · FTT-CO27-0001` (customer NULL). El de Brownie és `rs110`.

4. **Quatre models del cens no tenen cap clau natural** (només `*_pkey`): `GarmentType`,
   `POMMaster`, `GradingRuleSet`, `SizingProfile`. Sense clau natural, la còpia idempotent-additiva
   és impossible sense sintetitzar-ne una o mantenir mapes `pk→pk`.

5. **No existeix cap mecanisme de còpia entre schemes.** `grep -rn "clone_schema" backend/` →
   **NO EXISTEIX**. Tots els seeds del repo són *autoria* des de literals o Excel, mai
   `schema_context(origen)` → `schema_context(destí)`. El bootstrap s'ha de construir de zero,
   combinant dos patrons que ja existeixen per separat.

6. **El provisioning aplica ~190 migracions síncrones dins la request HTTP**, i **cap transició
   automàtica** porta el tenant d'`onboarding` a `actiu`. Tampoc existeix cap via programàtica per
   crear el primer usuari d'un tenant: cap-i-cua (calen usuaris per crear usuaris).

---

## B1 — Graf de dependències del catàleg

### Marc: `pom` viu a SHARED **i** TENANT

`settings.py:55` (SHARED_APPS) i `settings.py:68` (TENANT_APPS). Comentari a `settings.py:53-54`:
*"'pom' viu en SHARED i TENANT: els models \*Global viuen a 'public' i la resta es repliquen a
cada tenant per a FKs cross-schema."* Conseqüència verificada per psql: **totes** les taules
`pom_*` existeixen a `public` i a `fhort`; les `tasks_*` només a `fhort`.

`SELECT schema_name FROM public.tenants_client` → només `public` i `fhort`. **NO EXISTEIX cap
tenant verge** per contrastar → el "neix amb 0 vs N" es dedueix del codi de les migracions.

### Cens per model

| Model | Fitxer:línia | App / schema | Clau natural | Volum `fhort` / `public` |
|---|---|---|---|---|
| `POMGlobal` | `pom/models.py:8` | pom · SHARED+TENANT | **`codi`** (unique, `:31`) ✅ | 125 / 125 |
| `GarmentTypeGlobal` | `pom/models.py:79` | pom · SHARED+TENANT | **`codi`** (unique, `:80`) ✅ | 59 / 59 |
| `GarmentType` | `pom/models.py:385` | pom · tenant | **CAP** (Meta `:419`) 🛑 | 19 / 0 |
| `GarmentTypeItem` | `tasks/models.py:280` | tasks · TENANT-only | `(garment_type, code)` (`:321`) | 57 / — |
| `POMMaster` | `pom/models.py:144` | pom · tenant | **CAP** (Meta `:182`) 🛑 | 170 / 0 |
| `GarmentPOMMap` | `pom/models.py:427` | pom · tenant | `(garment_type_item, pom)` (`:454`) | **1529** / 0 |
| `SizingProfile` | `pom/models.py:809` | pom · tenant | **CAP** (Meta `:844`) 🛑 | 26 / 0 |
| `GradingRuleSet` | `pom/models.py:499` | pom · tenant | **CAP** (Meta `:562`) 🛑 | 25 / 14 |
| `GradingRule` | `pom/models.py:570` | pom · tenant | `(rule_set, pom)` (`:606`) | 707 / 0 |
| `GradingException` | `pom/models.py:617` | pom · tenant | `(rule_set, pom, size_label)` (`:629`) | 0 / 0 |
| `TaskTimeEstimate` | `tasks/models.py:343` | tasks · TENANT-only | `(garment_type_item, task_type)` (`:356`) | 460 / — |
| `TimeSeed` | `tasks/models.py:392` | tasks · TENANT-only | **`(scope, key)`** (`:413`) ✅ | 8 / — |
| `CustomerPOMAlias` | `pom/models.py:236` | pom · tenant | `(customer, client_code)` (`:274`) ⚠️ ancorada a entitat | 7 / 0 |

### 🛑 Trampa 1 — quatre models sense clau natural

Confirmat a la BD (només `*_pkey`, cap constraint d'unicitat): `GarmentType`, `POMMaster`,
`GradingRuleSet`, `SizingProfile`. Candidates existents però **no imposades**:

- `GarmentType.codi_client` — no unique.
- `POMMaster` — relació 1:1 *de facto* amb `POMGlobal` (la sembra `reseed_tenant_fhort.py:255-267`
  crea 1 POMMaster per POMGlobal), **no imposada**; `pom_global` pot ser NULL → sense clau.
- `GradingRuleSet.codi_sistema` (`:558`) — seria la clau ideal, però és `blank` i està **buit a 5
  dels 25** (vegeu B2).
- `SizingProfile` — cap; caldria sintetitzar
  `(target, garment_type, construction, fit_type, customer, version)`.

Sense clau natural, una còpia additiva no pot decidir si una fila del destí "ja hi és" → cal
mantenir mapes `pk_origen → pk_destí` durant tota la còpia.

### FKs que NO han de viatjar

**A entitat (`tasks.Customer`, cross-schema `db_constraint=False`):**
`GradingRuleSet.customer` (`pom/models.py:513`), `SizingProfile.customer` (`:830`),
`CustomerPOMAlias.customer` (`:249`).

⚠️ Les dues primeres són `SET_NULL`: en copiar a un tenant nou **quedarien NULL en silenci, sense
error de BD** — pèrdua de procedència muda. `CustomerPOMAlias.customer` és `PROTECT` → petaria.

**A usuari / auditoria:** `SizingProfile.modified_by_id` (`:839`), `SizingProfile.modified_at`
(`:841`), `TimeSeed.updated_by` (`tasks/models.py:407`), i tots els `created_at`/`updated_at`/
`creat_at`/`actualitzat_at`.

**Estat d'ús (no és definició):**
- 🔴 `TaskTimeEstimate.n` / `mean_minutes` / `m2` (`tasks/models.py:351-353`) — **estadística
  Welford de temps reals observats**. Només `estimated_minutes` (`:350`, el seed) és definició.
  Copiar el Welford de fhort a un tenant nou li regalaria una història de temps que no ha viscut.
- `GradingRuleSet.pendents_vincular` (`pom/models.py:518`) — estat R2 d'un run.
- `GradingRule.talla_break_pos` (`:600`) — cache del run.
- `GradingRuleSet.version_number` / `parent_version`, `SizingProfile.version`.

### Ordre topològic de còpia

Catàlegs-fulla pressuposats (targets de FK, han d'existir abans): `BodyMeasurementISO`,
`POMCategory`, `SizeSystem` → `SizeDefinition`, `GarmentGroup`, `Target`, `FitType`,
`ConstructionType`, i (tasks) `TaskType`.

1. `POMGlobal` → 2. `GarmentTypeGlobal` → 3. `GarmentType` → 4. `POMMaster` →
5. `GradingRuleSet` → 6. `GarmentTypeItem` → 7. `GarmentPOMMap` → 8. `GradingRule` →
9. `GradingException` → 10. `SizingProfile` → 11. `TaskTimeEstimate` → 12. `TimeSeed` →
13. `CustomerPOMAlias`

**Cicles:** `SizingProfile.parent_profile` (`:835`) i `GradingRuleSet.parent_version` (`:551`) són
auto-FK → calen **dues passades** (crear amb `parent=NULL`, després resoldre pares).

### El cas SHARED+TENANT: què neix i què s'ha de copiar

Les úniques `RunPython` de `pom/migrations/` són **7 transformacions** (`0021`, `0023`, `0030`,
`0031`, `0032`, `0034`, `0035`); **cap toca `POMGlobal` ni `GarmentTypeGlobal`** (verificat:
0 referències a cadascuna). I `grep -rn "POMGlobal.objects\|GarmentTypeGlobal.objects"
backend/fhort/*/migrations/` → **cap resultat**.

> **Resposta a la pregunta crítica del brief: un tenant nou neix amb `POMGlobal` = 0**, no 125.
> Les 125 de `fhort` i les 125 de `public` provenen d'haver executat `extend_pom_catalog.py` /
> `replace_pom_catalog.py` **a mà** contra aquells schemes. S'han de copiar.

**Cap model del cens neix per migració. Tots neixen buits → tots s'han de copiar.**

### TROBALLA TRANSVERSAL — el que SÍ neix sol (i per tant NO s'ha de copiar)

Dues taules **fora del cens** neixen poblades, perquè `tasks` és TENANT_APP i les seves migracions
corren a cada schema nou:

- `tasks_tasktype` ← `tasks/migrations/0025_seed_canonical_task_types.py` (`update_or_create` per
  `code`) → **~14 TaskType**. **NO copiar.** Conseqüència directa: `TaskTimeEstimate.task_type` i
  `TimeSeed.key` s'han de **re-resoldre per `code`** al destí, mai per pk (llei G9).
- `tasks_customer` ← `tasks/migrations/0020_seed_self_customer.py` → 1 self-Customer amb
  `codi = Client.codi_tenant`. És on haurien d'apuntar (o no) les FK d'entitat.

I `TimeSeed`: `tasks/0032_distill_time_seeds.py` destil·la des de `TaskTimeEstimate`, que en un
tenant nou està buit → **TimeSeed neix amb 0**. Els 8 de `fhort` s'han de copiar.

> **Veredicte B1:** ordre topològic clar i 13 peces censades. Dues trampes dures: **4 models sense
> clau natural** i **el Welford de `TaskTimeEstimate`**, que és història d'ús disfressada de catàleg.

---

## B2 — Procedència de les regles de grading

### El fet central: no hi ha camp de procedència

Camps de `GradingRuleSet` (`pom/models.py:499-567`): `nom`, `garment_group`, `size_system`,
`actiu`, `customer`, `pendents_vincular`, `target`, `targets`, `construction`, `fit_type`,
`is_system_default`, `parent_version`, `version_number`, `codi_sistema`.

Cercats explícitament: `origen`, `origin`, `source`, `run_id`, `provinenca`, `provenance`,
`derivat`, `is_canonical`, `document_origen`, `snapshot` → **NO EXISTEIXEN a cap dels tres models**
(`GradingRuleSet`, `GradingRule`, `GradingException`). Confirmat també contra la BD: la taula
`fhort.pom_gradingruleset` té exactament 14 columnes, cap d'elles de procedència.

`GradingRule` i `GradingException` **no tenen cap camp de procedència**; hereten l'origen del seu
`rule_set` per FK CASCADE.

### La llei existeix; la implementació no

`DECISIONS.md:304` — **RUN-CLIENT**: *"[LLEI DE DOMINI] GradingRuleSet = ACTIU CORE i SECRET
INDUSTRIAL del tenant"*, amb corol·laris que a federació les regles s'apliquen **sense còpia de la
forma** i que el benchmark cross-tenant **exclou per llei** tota forma de graduació.

`DECISIONS.md:348` — **PROVINENÇA**: *"(llei nova, **PENDENT d'implementar**): tot GradingRuleSet
importat ha de guardar el document d'origen + snapshot dels `values_by_size`... Un actiu de secret
industrial ha de ser auditable i regenerable contra la seva font."*

> La provinença estava **decidida i explícitament no implementada**. El cens ho confirma
> estructuralment: cap columna, ni al model ni a la BD.

### Els 25 rulesets reals (SELECT verificat personalment)

```
  id  cust sysdef rules  codi_sistema             nom
  75  None   True    61  EU_WOVEN_WOMAN_REGULAR   EU Woven Woman Regular
  76  None  False    61  EU_WOVEN_WOMAN_SLIM      EU Woven Woman Slim
  ...  (75-93: el seed ISO canònic, 19 rulesets, customer NULL)
  93  None  False     9  -                        EU Knit Baby Months
  98  None  False    19  EU_STRETCH_WOMAN_SLIM_CUSTOM  Custom Alpha EU — Women
 104   LOS  False    19  -                        LOS Kids Knit Regular 2Y - 12Y
 107  None  False    20  -                        Importació fitxa · FTT-CO27-0001
 108  None  False     0  -                        Mango EU woven woman regular - only dress
 110  None  False     6  -                        Importació fitxa · BRW-SS27-0001
 111   LOS  False    16  -                        EU ALPHA LOS TOP KNIT REGULAR V01
TOTAL fhort: 25 · TOTAL public: 14
```

### ⚠️ Correcció a la premissa del brief

«els rulesets derivats dels runs de Brownie (rs111, rs107 i companyia)» **no descriu la realitat**:

- `rs111` = `EU ALPHA LOS TOP KNIT REGULAR V01`, **customer = LOS** (Losan), no Brownie.
- `rs107` = `Importació fitxa · FTT-CO27-0001`, **customer = NULL**, i el prefix és FTT.
- El run de **Brownie** és `rs110` (`Importació fitxa · BRW-SS27-0001`, 6 regles) i té
  **`customer_id = NULL`**.

### 🛑 STOP — cap discriminador estructural

**Només 2 rulesets de 25 tenen `customer_id`** (104 i 111, tots dos LOS). Els runs importats
**no fixen `customer`**, verificat al camí de creació:
`models_app/extraction_views.py:1395` posa `nom=f"Importació fitxa · {model.codi_intern}"`, i
`pom/grading_utils.py:353-362` fa `GradingRuleSet.objects.create(...)` **sense argument `customer`**.

I els altres candidats a discriminador **tampoc serveixen**:

- `is_system_default` → **False a 76, 77, 78, 80, 82, 85, 92, 93**, que són canònics del seed ISO.
  Distingeix "primer de la família", no "canònic".
- `codi_sistema` → buit a `93` (canònic) i també a `104`, `107`, `110`, `111` (derivats).
- `customer_id` → NULL a `107`, `110` (derivats de client!) i també a tots els canònics.
- `nom` → l'únic senyal real (`"Importació fitxa · <codi_intern>"`, on el prefix del document porta
  BRW/FTT/LOS), però és **convenció humana**, no estructura. I `rs108` es diu "Mango…", nom de
  client, sense cap altra marca.

**Conseqüència per a `bootstrap_tenant`:** iterant la taula, la comanda **no pot distingir** un
canònic d'un run de client. O bé copia runs de client al tenant nou (**viola RUN-CLIENT / secret
industrial**), o bé aplica una heurística de nom (fràgil) i s'arrisca a deixar canònics enrere.

**Agreujant d'idempotència:** el `nom` no és únic i es reescriu amb sufix determinista si
col·lideix (`pom/grading_utils.py:350-352`) → copiar per `nom` **no és idempotent**.

**Cadena a client:** `GradingRuleSet` **no té FK a `Model`**. El vincle amb el run es fa des del
costat del Model (`grading_utils.py:342`: *"el cridador re-apunta el model"*). No hi ha cadena
estructural ruleset→run→client.

### CustomerPOMAlias — confirmat: no viatja

`pom/models.py:249-251`: `customer = ForeignKey('tasks.Customer', on_delete=PROTECT,
related_name='pom_aliases', db_constraint=False)`. Comentari `:247-248`: *"`pom` és SHARED+TENANT
però `tasks.Customer` és tenant-only → la FK creua schemes."* Unicitat `(customer, client_code)`
(`:274`).

Cada fila és la nomenclatura pròpia d'un client concret de fhort → **per construcció NO pot
viatjar**. Volum: **7 files** (FTT: 2 · Brownie: 5 · Losan: 0).

> **Veredicte B2: BLOQUEJANT.** Cap còpia de grading és segura fins que el CTO decideixi. La llei
> PROVINENÇA, ja decidida i no implementada, és exactament la peça que falta.

---

## B3 — Mecanismes existents reaprofitables

### El buit central

`grep -rn "clone_schema" backend/` → **NO EXISTEIX** (ni de django-tenants ni l'extensió Postgres).
`grep bootstrap_tenant` → **NO EXISTEIX**.

**Cap command del repo copia dades d'un tenant a un altre.** La font sempre és literal inline o
Excel, mai `schema_context(origen)` llegit i reescrit a `schema_context(destí)`.

### Els dos commands que el brief demanava resoldre

**`author_baby_pom_maps.py`** — dades **literals inline** (`ITEMS`, `:35-101`) amb `pom_master_id`
i `item_id` **enters absoluts de fhort**. Escriu només `GarmentPOMMap`.
**Idempotència: RESOLTA — SÍ**, però no per `get_or_create`: és un **reconciliador declaratiu** que
calcula creates/updates/deletes contra el set desitjat (`:148-166`) i els aplica a `_apply`
(`:202-215`). `SCHEMA = 'fhort'` hardcoded (`:29`), sense flag.
**Lògica de còpia reutilitzable: NO** — és autoria amb pks literals.

**`load_map_inline.py`** — literals inline (`RAW`, `:23-46`), escriu `GarmentPOMMap`.
**Idempotència: RESOLTA — SÍ**, `update_or_create(garment_type_item=item, pom=pom, ...)` (`:144`),
mai `.delete()`. `--schema` parametritzable (`:80`).
**Lògica reutilitzable: SÍ, parcialment — és el patró més imitable.** Conté **resolució de FK per
clau natural**: `pm_by_code = {pm.pom_global.codi: pm}` (`:98-101`), `GarmentTypeItem` per `code`
amb skip-and-log dels absents/ambigus (`:112-121`).

### Inventari de la resta

Idempotents per clau natural i no destructius (imitables): `seed_baby_poms.py`,
`seed_commercial_size_runs.py`, `seed_baby_months_grading.py`, `seed_baby_months_profiles.py`,
`extend_pom_catalog.py` (`update_or_create`, `:177`, `:195`).

**Destructius (evitar):** `replace_pom_catalog.py` (`POMGlobal.objects.all().delete()`, `:753` +
`bulk_create`, `:805`); `reseed_tenant_fhort.py` (avorta amb `CommandError` a `:84-87`; el codi mort
de sota fa `.all().delete()` a `:228-239`, `:279`, `:315-316`, `:399`).

**Lligats a fhort per rutes absolutes:** `reseed_size_definitions.py:27,29`
(`/root/fhort-sessions/*.xlsx`), `reseed_tenant_fhort.py:29-30`.

### La maquinària de clonatge que sí existeix

**`clone_model_for_qa.py`** (`models_app/management/commands/`) — clona el graf d'un Model **dins
del mateix schema**. Patró: `pk=None; save()` objecte a objecte amb recorregut explícit
(`:73-86` el Model; `:92-96` BaseMeasurements; `:101-102` ModelGradingRule), reassignant el pare
explícitament (`bm.model = clone`, `:94`).

🔴 **El detall que el fa NO directament imitable:** **reusa les FK de catàleg per valor**
(`grading_rule_set`, `size_system`, `garment_type` es mantenen apuntant al mateix objecte,
`:86`). Això **només és vàlid intra-schema**. Entre schemes, aquestes FK apuntarien a pks
inexistents al destí. Cal substituir el reús-per-valor per **remapeig per clau natural**.

Altres peces del mateix patró: `commerce/services.py:126-160` (`convert_quote_to_order`, documentat
com *"patró clone_model_for_qa"*) → confirma que `pk=None; save()` és **l'idioma de clonatge del
repo, sempre intra-schema**.

**Expansió per grup amb dedup** (`reseed_tenant_fhort.py:428-449`) + **resolució massiva de FK per
mapa de clau natural** (`:280-321`, `gt_map`, `pm_by_pgcodi`, `target_map`, `ss_map`) — és **l'únic
lloc del repo que re-crea catàleg resolent FK per clau natural**. Val com a plànol, tot i viure en
un command mort.

### Imitar / evitar

| Patró | Font | Veredicte | Motiu ancorat |
|---|---|---|---|
| `update_or_create` per clau natural | `load_map_inline.py:144` | **IMITAR** | Default segur del repo; re-executable |
| Resolució de FK per clau natural + skip-and-log | `load_map_inline.py:98-121`; `reseed_tenant_fhort.py:280-321` | **IMITAR (imprescindible)** | Entre schemes les pks difereixen; copiar FK per pk és impossible |
| Reconciliador declaratiu (create/update/delete al set desitjat) | `author_baby_pom_maps.py:148-215` | **IMITAR** | Estat final idempotent sense delete-all cec |
| `pk=None; save()` per recórrer grafs | `clone_model_for_qa.py:73-102` | **IMITAR amb compte** | Correcte per als fills; **el reús de FK per valor (`:86`) trenca entre schemes** |
| Regenerar en lloc de copiar (specs) | `clone_model_for_qa.py:110-111` | **IMITAR** | El derivat es recalcula; garanteix consistència |
| Purga en ordre topològic invers | `clone_model_for_qa.py:149-164` | **IMITAR** (per a `--recreate`) | Única gestió correcta de FK `PROTECT` del repo |
| `bulk_create` | `reseed_tenant_fhort.py:267,306,390,450` | **EVITAR si hi ha signals** | No dispara signals ni `save()` |
| delete-all + recrear | `replace_pom_catalog.py:753` | **EVITAR** | Destructiu; xoca amb FK `PROTECT` |
| Excel absolut + schema hardcoded | `reseed_size_definitions.py:27,29` | **EVITAR** | No portable; el contrari d'un `--from/--to` |

> **Veredicte B3:** el bootstrap s'ha de construir. Els dos ingredients existeixen però **mai s'han
> combinat**: recorregut de graf (`clone_model_for_qa`) + remapeig per clau natural
> (`load_map_inline`). Cap dels dos, sol, cobreix una còpia tenant→tenant.

---

## B4 — Provisioning actual (encaix ONBOARDING→ACTIU, D8)

### Cicle de `ClientViewSet.create` (`backoffice/views_tenants.py:56-79`)

Tot **síncron dins la request HTTP**:

1. `:57-58` `serializer.is_valid(raise_exception=True)`.
2. `:67` `serializer.save()` → `Client.save()` (`tenants/models.py:206-210`) → `TenantMixin.save()`
   amb `auto_create_schema = True` (`tenants/models.py:171`) → **`CREATE SCHEMA` + aplicació de
   TOTES les migracions de TENANT_APPS**, bloquejant.
3. `:68-69` `Domain.objects.create(...)` amb `{codi_tenant.lower()}.fhorttextile.tech` — **fora de
   tot `atomic`**.
4. `:70-76` `BackofficeActionLog.objects.create(...)`. 5. `:77-79` resposta 201.

L'absència d'`atomic` és **deliberada i documentada** (`:59-66`): posar-hi el DDL de
`auto_create_schema` provoca a PostgreSQL *"cannot ALTER TABLE ... because it has pending trigger
events"*. Compromís acceptat: si falla el `Domain`, queda Client + schema orfe.
`auto_drop_schema = False` (`tenants/models.py:172`) → esborrar el Client no neteja el schema.

> Matís rellevant per a D8: l'`atomic` que la diagnosi anterior trobava a faltar **no és un
> oblit** — hi ha un motiu tècnic escrit al codi. La solució no és "afegir atomic".

### Cost del provisioning (**estimació**, no mesura)

| App (TENANT_APPS) | Migracions | Amb `RunPython` |
|---|---|---|
| accounts | 7 | 0 |
| models_app | 55 | 3 |
| pom | 35 | 7 |
| fitting | 15 | 0 |
| tasks | 37 | 4 |
| planning | 2 | 0 |
| commerce | 19 | 3 |
| i18n_content | 1 | 0 |
| **TOTAL `fhort.*`** | **171** | **17** |

Més `contenttypes` + `auth` (~15-20, dins el venv). **≈190 migracions síncrones**, 17 amb
`RunPython`. **Estimació d'ordre de magnitud: desenes de segons** dins una única request HTTP
bloquejant. *(No cronometrat: cap execució, per llei del Patró A.)*

### Estats del tenant

`Client.estat` (`tenants/models.py:123`): `CharField(choices=ESTAT_CHOICES,
default=ESTAT_ONBOARDING)`. Choices (`:73-82`): `onboarding`, `actiu`, `suspes`, `baixa`.
**`ONBOARDING` existeix i és el default.** També hi ha un booleà legacy `actiu` (`:112`), la
property pont `es_actiu` (`:181-184`) i un `onboarding_complet = BooleanField(default=False)`
(`:114`), **independent** d'`estat`.

La UI el filtra: `frontend-backoffice/src/config/estats.js:7,14` i
`frontend-backoffice/src/pages/TenantsPage.jsx:11,60`; el backend ho suporta amb
`filterset_fields = ['estat', 'tipologia', 'plan']` (`views_tenants.py:39`).

**Què el transiciona avui:** l'única escriptura a `Client.estat` en tot el backend és **manual**,
per l'endpoint admin `update_estat` (`views_tenants.py:124`). **NO EXISTEIX cap transició
automàtica** onboarding→actiu. Ningú escriu mai `onboarding_complet = True` (només apareix a
`serializers_tenants.py:34` com a camp exposat).

BD real: només `public/SYS/actiu` i `fhort/FTT/actiu` — **cap tenant ha passat mai pel flux**.

### Primer usuari del tenant (D6)

Camí HTTP actual: `accounts/views.py:105-118` (`UserViewSet.create`), gated per `MANAGE_USERS`
(`:91`) i que **rebutja explícitament el schema `public`** (`:108-110`).
`UserCreateSerializer.create` (`accounts/serializers.py:225-239`) fa `User.objects.create_user(...)`
i després recull el `UserProfile` **que el signal ja ha creat**, per fixar-li `rol_nom`.

Signal: `accounts/signals.py:19-33`, `post_save` sobre `User`, amb guarda
`if connection.schema_name == get_public_schema_name(): return` (`:24-25`). Defaults: `rol_nom =
DEFAULT_ROLE` (`:30`), és a dir **`"technician"`** (`accounts/capabilities.py:28`), que **no té
`MANAGE_USERS`**.

**Via programàtica des de `public`: NO EXISTEIX.** L'únic command de creació d'usuaris és
`backoffice/management/commands/create_backoffice_admin.py`, i és **exclusiu de public**: aborta amb
`CommandError` si `connection.schema_name != public` (`:49-54`) i crea `auth.User` + `BackofficeUser`
(rol de backoffice), **no** un `UserProfile` de tenant. **NO EXISTEIX cap `create_tenant_admin`.**

**El mecanisme, però, ja funcionaria:** dins `schema_context('<tenant_nou>')`,
`connection.schema_name` ≠ public → la guarda del signal no salta → el `UserProfile` es crearia sol.
**Només falta el codi que obri aquell `schema_context` i cridi `create_user`.**

**Què falta, exactament:**
1. Un punt d'entrada programàtic (command o hook al `create`) amb
   `with schema_context(client.schema_name): User.objects.create_user(...)`. Avui és un **cap-i-cua**:
   l'endpoint HTTP exigeix estar ja dins el schema **i** tenir `MANAGE_USERS` — calen usuaris per
   crear usuaris.
2. Forçar `UserProfile.rol_nom = 'admin'` després del signal (el default `technician` no pot crear
   ningú més).
3. Res marca `estat = actiu` ni `onboarding_complet = True` en acabar.

> **Veredicte B4:** el schema neix, però el tenant **no neix viu**: sense catàleg, sense usuari i
> sense sortir d'`onboarding`. Les tres peces són independents i cap existeix.

---

## B5 — Resum: taula de còpia

| Peça | Copiar? | Clau natural | Ordre | Trampa |
|---|---|---|---|---|
| `POMGlobal` | **SÍ** (neix 0) | `codi` ✅ | 1 | També cal a `public`? Decidir abast |
| `GarmentTypeGlobal` | **SÍ** (neix 0) | `codi` ✅ | 2 | — |
| `GarmentType` | **SÍ** | **CAP** 🛑 | 3 | Sense clau → mapa pk→pk |
| `POMMaster` | **SÍ** | **CAP** 🛑 | 4 | 1:1 amb POMGlobal *de facto*, no imposada; `pom_global` nullable |
| `GradingRuleSet` | **🛑 DECISIÓ CTO** | **CAP** 🛑 | 5 | Cap discriminador canònic/derivat. Viola RUN-CLIENT si es copia cec |
| `GarmentTypeItem` | **SÍ** | `(garment_type, code)` | 6 | FK a `GradingRuleSet` és `PROTECT` → depèn de la decisió anterior |
| `GarmentPOMMap` | **SÍ** | `(item, pom)` | 7 | 1529 files, el volum gros |
| `GradingRule` | **🛑 amb el seu ruleset** | `(rule_set, pom)` | 8 | Hereta la decisió de `GradingRuleSet` |
| `GradingException` | **SÍ** (buit avui) | `(rule_set, pom, size_label)` | 9 | 0 files a fhort |
| `SizingProfile` | **SÍ**, sense `customer` | **CAP** 🛑 | 10 | `customer` és `SET_NULL` → es perd en silenci. `parent_profile` auto-FK → 2 passades |
| `TaskTimeEstimate` | **SÍ, només `estimated_minutes`** | `(item, task_type)` | 11 | 🔴 `n`/`mean_minutes`/`m2` = Welford, **història d'ús: NO copiar** |
| `TimeSeed` | **SÍ** | `(scope, key)` ✅ | 12 | `key` referencia `TaskType.code` per string → re-resoldre per code |
| `CustomerPOMAlias` | **NO** | `(customer, client_code)` | 13 | FK `PROTECT` a `Customer` de fhort. Per construcció no viatja |
| `TaskType` | **NO** (neix sol) | `code` | — | Migració `tasks/0025`. Llei G9: referència per `code`, mai pk |
| `Customer` (self) | **NO** (neix sol) | `codi` | — | Migració `tasks/0020` |

### 🛑 STOPs declarats (anotats, no resolts)

1. **`GradingRuleSet` no té procedència.** Cap camp distingeix canònic de derivat de run de client;
   només 2 de 25 tenen `customer_id` i cap és el run de Brownie. Copiar a cegues viola la llei
   RUN-CLIENT (secret industrial). **La llei PROVINENÇA ja està decidida i sense implementar**
   (`DECISIONS.md:348`) — és exactament la peça que ho desbloquejaria.
2. **Premissa del brief incorrecta:** `rs111` i `rs107` no són de Brownie (són LOS i FTT). El de
   Brownie és `rs110`, i té `customer_id = NULL`.
3. **`TaskTimeEstimate` barreja definició i estat d'ús** en una sola taula. Copiar-la sencera
   regalaria a un tenant nou l'estadística Welford de fhort.

### Decisions Patró C que caldran abans del Pas 2

- **DC-1 (bloquejant) — Què fa el bootstrap amb el grading.** Opcions: (a) copiar només els
  rulesets amb `codi_sistema` poblat i `customer IS NULL`; (b) implementar PROVINENÇA primer i
  copiar per la marca nova; (c) no copiar grading i deixar que el tenant nou l'importi. La (b) és
  l'única que no depèn d'una heurística de nom. 💡 PROPOSTA (a validar).
- **DC-2 — Clau natural per als 4 models que no en tenen.** ¿S'imposen constraints noves
  (`GarmentType.codi_client`, `POMMaster.pom_global`, `GradingRuleSet.codi_sistema`) — cosa que vol
  migració i sanejat de dades — o el bootstrap manté mapes `pk→pk` en memòria?
- **DC-3 — Abast de `POMGlobal`/`GarmentTypeGlobal`.** Són models `*Global` que viuen a `public`
  però es repliquen a cada tenant. ¿El bootstrap copia `public → tenant_nou`, o `fhort → tenant_nou`?
  (Avui tots dos tenen les mateixes 125/59 files, però `GradingRuleSet` ja divergeix: 25 a `fhort`,
  14 a `public`.)
- **DC-4 — `TaskTimeEstimate`:** copiar només `estimated_minutes` i deixar el Welford a zero
  (recomanat), o no copiar-la gens i deixar que la sembri `restructure_garment_types_v2`.
- **DC-5 (D6) — Primer admin del tenant.** Cal `create_tenant_admin` (o hook al `create`) amb
  `schema_context` + `rol_nom='admin'` forçat. Definir el flux de credencials.
- **DC-6 (D8) — ONBOARDING→ACTIU.** Res transiciona `estat` ni `onboarding_complet`. ¿El
  `bootstrap_tenant` és qui tanca l'onboarding en acabar bé? ¿Síncron o asíncron, vist que el
  provisioning ja bloqueja la request desenes de segons?
