# DIAGNOSI — Contenidor de graduació de client (la llei del contenidor acumulatiu)

> **Data:** 2026-07-16 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`, tenant `fhort` (id=2)
> **Abast:** rastrejar tot el radi de la llei «GradingRuleSet de client = CONTENIDOR ACUMULATIU únic per
> (customer + size_system + garment_type_item + fit)» abans d'implementar-la. Cobreix: totes les superfícies que
> exposen rulesets per triar (A.1), el paper del SizingProfile (A.2), veredicte regressió-o-mai-cablat (A.3),
> el camí de l'import AVUI contra les 4 operacions de la llei (A.4), la identitat del contenidor i si cal
> migració (A.5), i l'inventari de reparació del cas Brownie 115/116 (A.6). **Bloquejant abans de la Fase B.**
> **Convenció:** cada fet porta `fitxer:línia`; **"NO EXISTEIX" = confirmat absent al codi**; xifres = `SELECT`
> real sobre `fhort`. Propostes marcades `💡 PROPOSTA (a validar)` — decisió Agus (Patró C).
>
> **NOTA de llei:** la llei del contenidor (revoca la lectura de 1B/1D del sprint anterior) **encara NO és a
> `DECISIONS.md`** (§2 no la conté a data d'avui). Aquest doc la pren del brief com a font; la Fase B hauria
> d'escriure-la a `DECISIONS.md §2`.

---

## RESUM EXECUTIU

1. **El contenidor de client SÍ és triable des dels selectors de ruleset (fitxa de model, autoria d'item, CRUD),
   però NO des d'on el model rep la graduació al crear/editar-lo** («Editar model → 3. Talles»). Aquella targeta
   («Sistema de talles disponible per…») llista **SizingProfile**, no GradingRuleSet, i **ni el 115 ni el 116 tenen
   cap SizingProfile** (0 files cadascun) → **tots dos són invisibles exactament al punt on s'assigna el grading al
   model**. És el forat central. (A.1, A.2)

2. **Veredicte A.3 binari: MAI-CABLAT, no regressió.** No hi ha cap estat «funcionava i es va trencar». El
   `create()` del wizard size-map i l'editor CRUD **mai** van cablar els eixos que el picker necessita en tota la
   seva història; tots dos es van cablar **per primera vegada avui** (`59d5b02` F-1, `89eb9a0` F-2). El filtre del
   picker ha estat axis-first des del naixement i **mai** ha filtrat per `customer` (`git log -S customer` sobre el
   picker = 0). El 115 (eixos incomplets) és el **primer orfe** que destapa el camí no-cablat. (A.3)

3. **El camí d'import AVUI fa el CONTRARI de la llei en 3 de les 4 operacions.** SEMBRAR: materialitza **totes** les
   regles del contenidor, no les POMs de la fitxa (`services.py:156-167`). AMPLIAR: **NO EXISTEIX** (mai eixampla un
   contenidor). CONFLICTE: **NO EXISTEIX per-regla** (la dedup 1D crea un ruleset nou en silenci; el 409 de grading
   compara importat vs residents del model, tot-o-res). CREAR-EXPLÍCIT: **fa el contrari** (`derive_grading_rule_set`
   crea en silenci quan no casa). (A.4)

4. **Cal migració (A.5).** El model `GradingRuleSet` té `customer`, `size_system` i `fit_type`, però **NO té
   `garment_type_item`** (només `garment_group`, un eix més bast i sense camí net des de l'item) i **NO té cap
   constraint d'unicitat** (0 UNIQUE a la BD). Per encabir la llei cal **camp nou `garment_type_item` + constraint
   d'unicitat parcial** (només per a rulesets de client) — el disseny i l'estratègia per als 27 existents entren al
   GATE. (A.5)

5. **La duplicació és un únic incident, ja identificat i reparable net.** Cens: l'únic parell que col·lisiona sota
   la identitat de la llei és **(customer 7, ss 29, fit REGULAR) = {115, 116}** (difereixen només en `garment_group`,
   que NO és eix d'identitat). Els 11 canònics (customer NULL) no col·lisionen. Reparació: afegir al 115 només les
   **4 POMs** que 116 té i 115 no ({501,502,503,504} = M1/M2/I/I4), re-apuntar el model **269→115** i esborrar 116
   (camí net 204). (A.5, A.6)

6. **La peça R (409 `ruleset_reuse`) es REORIENTA, no es reverteix.** Avui està orientada a un món de *N germans*
   («reutilitzar quin dels N o crear-ne un»). Sota un contenidor únic, la pregunta canvia: **sempre s'apunta a
   l'únic contenidor** → SEMBRAR-hi, AMPLIAR (avís tou) i CONFLICTE (409 per-regla); l'opció «new» es reconverteix en
   el **prompt explícit d'Op4** (crear contenidor per a una combinació verge), mai una caiguda silenciosa a `derive`.
   Les primitives de comparació de la dedup 1D es reaprofiten per a l'Op3; la caça-de-bessó es jubila. (A.4)

---

## BLOC A.1 — VISIBILITAT: totes les superfícies que exposen rulesets per triar

**Dada base (SELECT `fhort`, verificat directament):**

| id | nom | origen | customer | ss | construction | fit | garment_group | is_sysdef | n_targets | n_regles | n_profiles |
|----|-----|--------|----------|----|----|----|----|----|----|----|----|
| 115 | BRW · Blusa · ALPHA_EU_W | CLIENT_RUN | 7 | 29 | **WOVEN(1)** | **REGULAR(1)** | **NULL** | f | 1 (WOMAN) | 34 | **0** |
| 116 | Importació fitxa · BRW-FW27-0002 | CLIENT_RUN | 7 | 29 | WOVEN(1) | REGULAR(1) | TOPS(7) | f | 1 (WOMAN) | 25 | **0** |

> ⚠️ **Correcció d'una troballa anterior:** les diagnosis `DIAGNOSI_CRUD…` i `DIAGNOSI_DUPLICACIO…` (mateix dia,
> abans) deien que **115 tenia construction/fit NULL**. **Avui el 115 té construction=WOVEN, fit=REGULAR**; només
> `garment_group` resta NULL. Els eixos del 115 s'han cablat entremig (F-1/F-2 o sessió concurrent). El que resta
> incomplet al 115 és **garment_group + SizingProfile + el vincle garment_type_item**, no construction/fit.

**Mapa de superfícies (front → endpoint → filtre backend → llista-per → visibilitat 115/116):**

| # | Superfície | Front | Endpoint | Filtre backend | Llista per | 115? | 116? |
|---|---|---|---|---|---|---|---|
| a | **Editar model → 3. Talles** (targetes «Sistema de talles disponible per…») | `ModelWizard.jsx:137` (fetch), render `:337/:343`, títol i18n `model_wizard.sizes_for` (`ca.json:855`); vincula el FK a `:75-76,:178` | `GET /api/v1/sizing-profiles/` | `s2_views.py:64` `sizing_profiles_view`; filtra `target__codi/construction__codi/fit_type/garment_type` (`:96-105`); `customer_codi` = **només ordena** (`:107-119`); itera `SizingProfile.objects` (`:77`) | **SizingProfile** | **NO** | **NO** |
| b | **RuleSetPicker/AxesSelector — fitxa de model** | `RuleSetCard.jsx:23` (fetch), `AxesSelector :55`, `RuleSetPicker :57`, `ggCodiById :59`; muntat a `ModelSheet.jsx:451` | `GET /api/v1/grading-rule-sets/?page_size=200` | `pom/views.py:152` `GradingRuleSetViewSet`, queryset `.all()` (`:155-160`); filterset `['actiu','garment_group','size_system','customer']` (`:162`) **però el front no en passa cap** | **GradingRuleSet** | **SÍ** | **SÍ** |
| c | **RuleSetPicker — autoria d'item** | `ItemAuthoring.jsx:81` (fetch), `AxesSelector :256`, `RuleSetPicker :260`, `ggCodiById :262` | `GET /api/v1/grading-rule-sets/?page_size=200` | mateix viewset, tots els rulesets | **GradingRuleSet** | **SÍ** | **SÍ** |
| d | **CRUD GradingRuleSets** (còpia inline del matching) | `GradingRuleSets.jsx:104` (fetch); matching inline `:133-192` | `GET /api/v1/grading-rule-sets/?page_size=200` | mateix viewset, tots els rulesets | **GradingRuleSet** | **SÍ** | **SÍ** |
| e | **Selector del create-wizard de model** | **= el mateix component que (a)** en mode creació (`ModelWizard.jsx` bloc 3, `isEditMode=false`) | `GET /api/v1/sizing-profiles/` | `s2_views.py:64`, idèntic a (a) | **SizingProfile** | **NO** | **NO** |

**Semàntica dels eixos NULL:**
- **Superfícies de ruleset (b/c/d):** NULL = **COMODÍ**. `matchesTarget`/`matchesGarmentGroup` retornen match si l'eix és buit (`gradingAxes.js:65-72`), i construction/fit igual (`:106-110`: `!rs.construction_codi || rs.construction_codi === construction`). La còpia inline del CRUD és idèntica (`GradingRuleSets.jsx:141,:188-189`). **Un eix NULL mai exclou.**
- **Superfície ModelWizard (a/e):** N/A — filtra files de SizingProfile (amb construction/fit no-null per definició del model), no eixos de ruleset.

**Per què 115/116 es veuen o no, per superfície:**
- **(a)+(e) ModelWizard bloc 3 — tots dos AMAGATS.** Llista **només SizingProfile** i **cap dels dos té SizingProfile** → invisibles independentment dels eixos. I és **exactament la superfície que assigna `grading_rule_set_id` al model al crear/editar**. **Forat central de la llei.**
- **(b/c/d) superfícies de ruleset — tots dos VISIBLES** un cop es baixen els 4 eixos fins a WOMAN→WOVEN→REGULAR→(TOPS): 116 casa exacte, 115 casa (té WOVEN/REGULAR propis; `garment_group` NULL = comodí). *(Nota: `matchingRuleSets` retorna `[]` fins que es trien els 4 eixos, `gradingAxes.js:105`; i els xips de construction/fit surten només de rulesets que HI TENEN codi, `:82-100`. El 115, amb WOVEN/REGULAR propis, il·lumina els seus xips tot sol — ja NO depèn d'un germà. Un contenidor de client amb els 3 eixos NULL i sense germà complet **sí** seria inabastable aquí.)*

**⚠️ Deute lateral (anotat, fora d'abast):** la llista `GARMENT_GROUPS` del front (`gradingAxes.js:46-54`) és hardcoded i **no conté** els grups de BD `TOPS-WOVEN(5)/TOPS-KNIT(6)/KNITWEAR(10)` → un ruleset ancorat en aquells grups seria inabastable al picker. No és el cas del 115/116 (gg NULL / TOPS).

**Veredicte A.1:** el contenidor de client és triable a **3 de 5** superfícies (b/c/d, per GradingRuleSet); és **invisible a les 2** que assignen grading al model (a/e, per SizingProfile). Fer-lo visible on importa = o bé sembrar SizingProfile que apuntin al contenidor, o bé fer que ModelWizard bloc 3 pugui llistar per GradingRuleSet.

---

## BLOC A.2 — SizingProfile: el paper real

**Model:** `pom/models.py:837-869` (taula `pom_sizingprofile`). És el JOIN de catàleg
`(target + garment_type + construction + fit_type)` → `(size_system + grading_rule_set)`, opcionalment amb
`customer` (`:858`, SET_NULL, `db_constraint=False`; NULL = perfil genèric de tenant). FK a ruleset
`grading_rule_set` (`:852`, **PROTECT, no-nullable**); FK a size_system (`:850`).

**Qui el CREA — només la Size Library / wizard size-map, MAI import-fitxa:**
- Creador real: `size_map_views.py` (create `:907`, reuse+update `:897-905`), via el front `SizeMapSetup.jsx` → `sizeMap.create` (`endpoints.js:178`). Clon: `s2_views.py:221`.
- **import-fitxa NO crea SizingProfile:** `import_session_confirmar_view` (`extraction_views.py:1645`) deriva/reapunta **només el GradingRuleSet** (`derive_grading_rule_set` a `:1891`, re-apuntat `model.grading_rule_set` a `:1927`). `grep SizingProfile grading_utils.py` = **0 hits**; a `extraction_views.py` l'únic hit és un **comentari** (`:1596`). → tot ruleset que entra per import-fitxa neix **orfe de perfil**.

**Qui el LLEGEIX (superfícies que LLISTEN perfils):** endpoint `sizing_profiles_view` (`s2_views.py:64`, filtres `:96-105`, ordre per customer `:107-119`), URL `sizing-profiles/` (`tasks/urls.py:162`), client `sizingProfiles.list` (`endpoints.js:150-151`). Consumidors: **ModelWizard bloc 3** (`ModelWizard.jsx:137`, el lector central), **SizingProfileSelector** (`:115`, usat per `SizeLibrary.jsx:91`), **CustomerDetail** (`:184`). El **RuleSetPicker NO** el consumeix (opera sobre GradingRuleSet, `RuleSetPicker.jsx:25`).

**Orfe de perfil:** un GradingRuleSet sense SizingProfile és **invisible a tota superfície que llista perfils**
(`s2_views.py:77` itera `SizingProfile.objects`). Segueix abastable només per les superfícies natives de ruleset
(picker, CRUD) i pel FK `model.grading_rule_set`.

**SELECT:** perfils del 115 = **0**; del 116 = **0**. size_system 29 → **7 perfils** (ids 264,276,288,485,497,510,523),
tots amb `customer_id = NULL` (genèrics). customer 7 → **0 perfils**. Els 3 models de BRW (267/268/269) apunten al
ruleset **directament**, mai via perfil.

**Veredicte A.2:** el SizingProfile és la clau de catàleg del pas «3. Talles», i el creen només els fluxos de Size
Library/size-map. Com que import-fitxa no en crea, el contenidor de client hi és cec. La coherència (B.3) passa
perquè el camí size-map creï contenidors complets **i** que el pas «3. Talles» pugui veure el contenidor del client.

---

## BLOC A.3 — Regressió o mai-cablat: VEREDICTE BINARI

**MAI-CABLAT. No hi ha cap regressió datada.**

- `create()` del wizard size-map: la línia `GradingRuleSet.objects.create(...)` ve de `eea6f71b` (2026-06-11,
  naixement del wizard) i posava **només `target`**. `git log -S "construction=rs_construction"` sobre
  `size_map_views.py` = **només `59d5b02`** (2026-07-16, F-1) → el wizard va parir rulesets de client amb
  construction/fit **NULL des del 2026-06-11 fins avui**.
- Editor CRUD: el modal deshabilitava sempre target/construction/fit (TODO obsolet «no hi ha endpoint codi→id»);
  cablat per primera vegada a `89eb9a0` (2026-07-16, F-2).
- Picker: la cascada filtra pels 4 eixos **des del naixement** (S15 `7b0dc8d`, S16b `80ae194`, 2026-05-27);
  extracció pura a `gradingAxes.js`/`RuleSetPicker.jsx` (`d18039c`, 2026-06-22). `git log -S "customer"` sobre
  `GradingRuleSets.jsx` = **0** → **mai** hi va haver filtre per client que pogués regressar.
- Camins que sí paren rulesets complets (i per això mai van veure el bug): el seed (`reseed_tenant_fhort.py:331-333,
  430-433` sempre posa target/construction/fit) i import-fitxa (`derive_grading_rule_set` rep
  `construction_codi/fit_type_codi` i els resol, `grading_utils.py:330-331`).

**Veredicte A.3:** el 115 és el **primer contenidor de client del wizard sense germà complet** → el primer orfe que
destapa un camí **que mai va estar cablat**. No cal buscar un commit culpable; cal **cablar per primera vegada** la
identitat i la visibilitat.

---

## BLOC A.4 — El camí de l'import AVUI vs les 4 operacions de la llei

**Els tres motors:**
- **DETECCIÓ** (`grading_utils.py`): `detect_grading` (`:141-220`) classifica els valors per-talla d'una POM en
  LINEAR/FIXED/STEP; `derive_break_fields` (`:223-248`) plega `valors_step` a la forma canònica
  `increment_base/increment_break/talla_break_label`. Pures, per-POM, degraden (salten una POM, mai peten). **Es
  REUTILITZEN** per derivar les regles a sembrar/afegir.
- **DERIVACIÓ** (`derive_grading_rule_set`, `:251-422`): avui és *reutilitzar-idèntic-o-crear-nou*, no *sembrar-un-contenidor*.
- **MATERIALITZACIÓ** (`materialize_model_grading_rules`, `services.py:147-168`): esborra-i-recrea els
  `ModelGradingRule` residents des de `source_rules`.

| Op de la llei | Veredicte | Evidència |
|---|---|---|
| **1 SEMBRAR** (escollir del contenidor només les POMs de la fitxa, descartar la resta) | **FA EL CONTRARI** | `materialize_model_grading_rules` copia **exactament `source_rules`** sense filtrar per les POMs confirmades (`services.py:156-167`); la crida passa **`new_rule_set.regles.all()`** = totes les regles del contenidor (`extraction_views.py:1932-1933`). Al camí crear-nou surt bé **per construcció** (les regles del ruleset nou SÓN les de la fitxa), però a `reuse:<id>`/`keep_current` el contenidor pot ser **més ample** i sembra tot. **No hi ha enlloc un pas «escull les POMs de la fitxa».** |
| **2 AMPLIAR** (POM de la fitxa que el contenidor no té → afegir-la al contenidor, avís tou) | **FALTA** | Cap camí eixampla un contenidor existent. `derive` o retorna un candidat idèntic sense escriure (`grading_utils.py:343-373`) o crea un ruleset **sencer nou** (`:387-422`). El `reuse` només re-apunta (`extraction_views.py:1882-1889`). Conseqüència: amb `reuse:<id>`, una POM de la fitxa absent del contenidor es **perd en silenci** (materialize copia només les del contenidor). |
| **3 CONFLICTE** (regla de fitxa que contradiu una del contenidor → tria conscient per-regla) | **FALTA per-regla** | (a) la dedup 1D marca `igual=False` a qualsevol divergència i **rebutja** el candidat (`grading_utils.py:352-363`) → cau a **crear-nou silenciós** (`:387`); un conflicte pareix un contenidor nou, no un prompt. (b) el 409 «grading» (`extraction_views.py:1906-1924`) sí existeix, però compara **importat vs residents RETINGUTS del model** (`grading_rules_match`, `grading_utils.py:32-81`), no fitxa-vs-contenidor, i resol **tot-o-res** (`grading_choice` = `heretats`\|`importats`). Cap «mantenir catàleg / actualitzar catàleg / resident-només». |
| **4 CREAR EXPLÍCIT** (contenidor nou només com a acte explícit) | **FA EL CONTRARI (crea en silenci)** | El branch de creació (`grading_utils.py:387-422`) dispara sempre que no troba bessó byte-a-byte, sense prompt. L'únic porter amunt és el 409 de la peça R, que **només salta si `cerca_client_equivalent` retorna germans** (`extraction_views.py:1830`); si el client no en té per (customer,ss), `derive` **crea en silenci** amb nom auto-sufixat. Fins i tot `ruleset_choice='new'` (`:1826`) no és «crear un contenidor NOU» sinó «no reutilitzis un germà». |

**Peça R (`ruleset_reuse` 409) — semàntica actual i reorientació.** `cerca_client_equivalent`
(`grading_utils.py:119-138`) retorna tots els rulesets actius no-sistema del mateix `customer + size_system`
(trigger = customer+ss, **ignora eixos i solapament de POM**). El confirm 409-a amb `tipus:'ruleset_reuse'` i
`reuse_candidates` (`extraction_views.py:1829-1844`); tries: `reuse:<actual>`→mantenir, `reuse:<altre>`→apuntar+materialitzar,
`new`→caure a `derive`. **Aproxima parcialment Op4** (porter humà abans de crear) i **Op1** (triar quin contenidor),
però està orientada a **N germans, tot-o-res**. **Reorientació:** sota contenidor únic → **sempre apuntar a l'únic
contenidor**, SEMBRAR-hi, córrer AMPLIAR (avís) i CONFLICTE (409 per-regla); `new` es reconverteix en el **prompt
explícit d'Op4** (combinació verge), mai caiguda silenciosa a `derive`.

**Sort de la dedup 1D.** *Jubila:* la caça-de-bessó-i-reutilitza (`:334-373`) i el crear-nou **silenciós**
(`:387-422`, que sobreviu **només** darrere el prompt d'Op4). *Reaprofita:* les primitives de comparació per-regla
(`_step_equal :17-29` i el check de 4 dimensions base/logica/increment/valors_step, `grading_rules_match :32-81`)
esdevenen el **detector de CONFLICTE (Op3)**, aplicat fitxa-regla-vs-contenidor-regla. *Manté com a clau de
contenidor:* el filtre de combinació (`:335-342`) deixa de ser guarda-de-proliferació i passa a **identificar l'únic
contenidor** — reescrit sobre la identitat de la llei (A.5). *(Deute PG-3 anotat, `grading_utils.py:92-95`: 1D casa
`target` pel FK legacy mentre `cerca_canonic_equivalent` usa el M2M `targets` — reconciliar en formalitzar la clau.)*

**Veredicte A.4:** l'import fa el contrari de la llei a 3/4 ops i li falta l'AMPLIAR. La reescriptura del bloc W5 és
el cor de la Fase B (B.2), reutilitzant els motors de detecció i les primitives de comparació ja existents.

---

## BLOC A.5 — Identitat del contenidor i migració

**Camps d'identitat al model `GradingRuleSet` (`pom/models.py:506-599`):**

| Eix de la llei | Al model? | Camp | Línia |
|---|---|---|---|
| customer | **SÍ** | `customer` FK→`tasks.Customer`, nullable, `db_constraint=False` | 545-547 |
| size_system | **SÍ** | `size_system` FK→`SizeSystem`, nullable | 540 |
| fit | **SÍ** | `fit_type` FK→`FitType`, nullable | 576-580 |
| garment_type_item | **NO EXISTEIX** | només `garment_group` FK→`GarmentGroup`, nullable | 533-539 |

**`garment_group` ≠ `garment_type_item`, i no hi ha camí net entre ells:**
- `GarmentGroup` (`pom/models.py:375-389`): família plana (SWIMWEAR/BOTTOMS/TOPS…), `codi` unique. Bast.
- `GarmentTypeItem` (`tasks/models.py:286-325`): el node fi (variant de complexitat d'un `GarmentType`),
  `garment_type` FK→`pom.GarmentType` (`:290`); **ja té el seu propi `grading_rule_set` FK** (`:319`, PROTECT) i
  `base_size_definition` (`:305`).
- Derivable garment_group ← garment_type_item? **NO net.** `GarmentTypeItem.garment_type` → `GarmentType`, i
  `GarmentType.grup` és un **CharField(40)** (`pom/models.py:402`), no FK a `GarmentGroup`. L'únic pont és la
  convenció fràgil `GarmentType.grup ≈ GarmentGroup.codi` (sense constraint). Granularitats diferents, no
  convertibles mecànicament.

**Constraints d'unicitat a `pom_gradingruleset`:** `SELECT … pg_constraint … regclass` = **14 files, ZERO UNIQUE**
(només PK, NOT NULL i 6 FK). Meta (`:594-596`) no declara `unique_together`/`constraints`. **Res impedeix avui un
contenidor duplicat.**

**⚠️ Tensió de disseny per al GATE — el vincle ja existeix des de l'item.** `GarmentTypeItem` ja porta
`grading_rule_set` (`tasks/models.py:319`). O sigui hi ha **dues maneres** de modelar la identitat:
- **(i) afegir `garment_type_item` FK al `GradingRuleSet`** + constraint d'unicitat → «troba EL contenidor per
  (customer, ss, garment_type_item, fit)» és una query directa sobre el ruleset. El FK invers de l'item
  (`GTI.grading_rule_set`) es reconcilia perquè apunti al mateix contenidor.
- **(ii) mantenir la identitat des de l'item** (`GTI.grading_rule_set` és el punter al contenidor) — però GTI no té
  `customer` ni `fit`, així que la unicitat per (customer, ss, gti, fit) no és enforçable des d'allà.

> `💡 PROPOSTA (a validar) — recomanació:` **opció (i)**. Camp `garment_type_item` FK→`tasks.GarmentTypeItem`
> **nullable i additiu** al `GradingRuleSet`; els canònics/seed el deixen NULL. **Constraint d'unicitat PARCIAL**
> `UniqueConstraint(fields=[customer, size_system, garment_type_item, fit_type], condition=Q(origen='CLIENT_RUN'))`
> — deixa **intactes** els 11 canònics (customer NULL) i tota fila NULL, i enforça un-sol-contenidor **només** per a
> rulesets de client. (Preferible `origen='CLIENT_RUN'` a `customer__isnull=False`: és la provinença exacta que la
> llei ataca.) Reconciliar el FK invers `GTI.grading_rule_set` perquè apunti al contenidor (backfill: GTI 5 → 115).

**CENS dels 27 rulesets (SELECT, ordenat per customer NULLS FIRST):**
- **customer NULL — 23 files:** 11 canònics `is_system_default` amb origen CANONICAL (75,79,81,83,84,86,87,88,89,90,91),
  la resta origen NULL/IMPORT (76,77,78,80,82,85,92,93,98,107,108,110). Cap col·lisiona sota la identitat de la llei
  (no són de client).
- **customer 6 (LOS) — 2 files:** `104` (ss50, fit NULL, 19 regles), `111` (ss51, fit NULL, 16 regles). **ss
  diferents → NO col·lisió.**
- **customer 7 (BRW) — 2 files:** `115` (ss29, fit REGULAR, gg NULL, 34 regles), `116` (ss29, fit REGULAR, gg TOPS,
  25 regles). **Mateix (customer,ss,fit) → COL·LISIÓ.**

**Grups de col·lisió (rulesets de client, per (customer, size_system, fit_type)):**

| customer | size_system | fit | ids | col·lisió? |
|---|---|---|---|---|
| 6 | 50 | NULL | {104} | no |
| 6 | 51 | NULL | {111} | no |
| **7** | **29** | **REGULAR** | **{115, 116}** | **⚠️ SÍ (2)** |

L'únic parell a resoldre és **{115,116}** (difereixen només en `garment_group`, que NO és eix d'identitat de la llei).

**Estratègia per als 27 sota la nova identitat (💡 a validar):**
- Canònics (11, customer NULL): `garment_type_item` NULL, **intactes** (constraint parcial no els toca).
- Client LOS (104,111): backfill `garment_type_item` quan es conegui l'item; no col·lisionen entre ells.
- Client BRW (115,116): resoldre la col·lisió a A.6 **abans** d'activar la constraint (fusió 116→115).
- Origen NULL «no classificat» (14): fora d'abast d'aquest sprint (deute S10 `set_grading_origen`); la constraint
  parcial per `origen='CLIENT_RUN'` **no** els afecta mentre siguin NULL.

**Veredicte A.5:** cal **camp nou + constraint parcial** (opció i recomanada). Migració additiva, sense risc per als
canònics. El disseny exacte del camp, la reconciliació amb `GTI.grading_rule_set`, i l'ordre (resoldre {115,116}
abans d'activar la constraint) són **decisió del GATE**.

---

## BLOC A.6 — Inventari de reparació Brownie (115 com a EL contenidor)

**Objectiu:** 115 = contenidor canònic de client de **(BRW · ss29 ALPHA_EU_W · blusa · REGULAR)**.

**Què li falta al 115 (SELECT):**
- **garment_group:** NULL (116 té TOPS(7)). *(construction/fit JA els té: WOVEN/REGULAR — corregit vs diagnosis
  anteriors.)*
- **SizingProfile:** 0 files.
- **garment_type_item:** el camp encara no existeix; cap `GarmentTypeItem` apunta al 115/116; **GTI 5 «Blusa»**
  (que és el `garment_type_item` dels 3 models BRW 267/268/269) té `grading_rule_set = NULL` → **backfill net GTI 5 → 115**.

**Delta de regles 116 vs 115 (SELECT `pom_gradingrule`):**
- 115 = 34 regles · 116 = 25 regles.
- **En 116 i NO en 115 → candidates a AFEGIR: 4 POMs {501,502,503,504}** = `M1` (Front piece width at top), `M2`
  (Front piece width at bottom), `I` (Sleeve length), `I4` (Sleeve length from CB…). **⚠️ Nota de domini:** aquestes
  són precisament de les «7 forats específics de model» que l'S10 va **excloure** conscientment del 115 (checklist
  Montse, `DECISIONS.md`); la llei diu «AMPLIAR el contenidor», però la decisió S10 les volia **residents de model**.
  **Conflicte de criteri a resoldre al GATE:** afegir-les al catàleg 115 vs deixar-les residents del 269. (Les altres
  3 POMs de sleeve/front-width poden ser catàleg legítim de blusa; decisió humana.)
- **21 POMs compartides:** el **115 és l'autoritatiu** (curat a mà a l'S10); els valors del 116 es **descarten** (no
  es mouen). Divergències: `increment` legacy = 0.00 a les 34 del 115 (condueix per `increment_base/break`), poblat al
  116; `increment_base` casa a 20/21 (**només POM 437 difereix**: 115=1.00 vs 116=0.00); `logica` difereix a **6 POMs**
  (286,299,437,455,461,464: 115=LINEAR, 116=FIXED). → **cap regla del 116 sobreescriu el 115**; només s'avaluen les 4 noves.
- 115-only (13 POMs: 275,292,441,442,453,456,467,468,475,476,484,498,499): es queden tal com són.

**Models que apunten a 115/116 (SELECT):**

| model | codi_intern | prenda | grs actual | garment_type_item |
|---|---|---|---|---|
| 267 | BRW-26-FW-0036 | [QA-S10] Blusa RUFUS STARS | **115** | 5 |
| **268** | BRW-FW27-0001 | **Blusa POP** | **115** | 5 |
| **269** | BRW-FW27-0002 | **POP** | **116** | 5 |

→ **268 i 267 ja apunten al 115**; **només el 269 apunta al 116** (és el que cal re-apuntar).

**Pla de fusió 116→115 (fets):**
1. (Opcional, decisió GATE) afegir al 115 les 4 POMs {501-504} amb la seva regla derivada (o deixar-les residents del 269).
2. Re-apuntar `models_app_model[269].grading_rule_set = 115` (via `update-step2 {grading_rule_set_id:115}` real → re-materialitza residents del 269 des del 115).
3. Esborrar 116. **Guarda del destroy** (`pom/views.py:171-209`): `is_system_default`→403 (116 no ho és); compta
   dependents `SizingProfile`(PROTECT) + `Model`(SET_NULL); **sense `?force=1` i amb dependents → 409 `{error:'protected',
   models_afectats,…}`** (`:188-204`). **Camí net:** re-apuntar 269→115 PRIMER (deixa `n_models`=0), DESPRÉS DELETE 116
   → **204** sense force i sense orfe. (`GTI.grading_rule_set` és PROTECT però 0 items apunten al 116.)
4. Backfill: `garment_group=TOPS(7)` al 115 (si es vol paritat d'eix amb 116) i `GTI 5.grading_rule_set = 115`.
5. Verificar 268/269 amb SELECT (grs=115, residents coherents) i re-materialitzar el 269.

**Veredicte A.6:** reparació neta i acotada. Única decisió de domini pendent: **les 4 POMs {501-504} van al catàleg
115 o resten residents del 269** (conflicte amb la decisió S10). La resta és mecànica i reversible (backup PRE-CONT).

---

## TAULA FINAL — per al GATE d'Agus (EXISTEIX / FALTA / FA-EL-CONTRARI)

| Node | Estat | Detall | Referència |
|---|---|---|---|
| Contenidor triable a fitxa-model/item/CRUD | **EXISTEIX** | per GradingRuleSet, NULL=comodí | `views.py:152-162`, `gradingAxes.js:65-110` |
| Contenidor triable a «Editar model → 3. Talles» | **FALTA** | llista SizingProfile; 115/116 = 0 perfils | `ModelWizard.jsx:137`→`s2_views.py:77` |
| import-fitxa crea SizingProfile | **NO EXISTEIX** | només deriva GradingRuleSet | `grading_utils.py` (0 hits), `extraction_views.py:1596` (comentari) |
| Regressió de visibilitat | **NO EXISTEIX** (mai-cablat) | wizard/CRUD mai van cablar eixos; sense filtre customer mai | `59d5b02`,`89eb9a0`; `-S customer`=0 |
| Op1 SEMBRAR (POMs de la fitxa) | **FA EL CONTRARI** | materialitza tot el contenidor | `services.py:156-167`, `extraction_views.py:1932` |
| Op2 AMPLIAR (afegir POM nova al contenidor) | **FALTA** | cap camí eixampla; es perd en silenci | `grading_utils.py:343-422` |
| Op3 CONFLICTE per-regla | **FALTA** (409 tot-o-res existeix) | 1D crea-nou silenciós; 409 compara vs residents | `grading_utils.py:352-363`, `extraction_views.py:1906-1924` |
| Op4 CREAR EXPLÍCIT | **FA EL CONTRARI** | crea en silenci si no casa | `grading_utils.py:387-422`, `extraction_views.py:1830` |
| `garment_type_item` al ruleset | **NO EXISTEIX** | només `garment_group` (bast, sense camí net) | `models.py:533` vs `tasks/models.py:319` |
| Constraint d'unicitat del contenidor | **NO EXISTEIX** | 0 UNIQUE a la BD | `pg_constraint`; `models.py:594-596` |
| Duplicació sistèmica | **AÏLLADA** (1 parell) | només (7,29,REGULAR)={115,116} | cens A.5 |
| Reparació 115/116 neta | **EXISTEIX** (camí) | +4 POMs?, re-apuntar 269→115, delete 116 (204) | `views.py:188-207` |

---

## GATE D'AGUS — què decidir (Patró C)

1. **A.3 veredicte:** MAI-CABLAT (no regressió). → la Fase B **cabla per primera vegada** identitat + visibilitat.
2. **A.4 gap-map:** import fa el contrari a 3/4 ops + falta AMPLIAR → **reescriure el bloc W5** (B.2), reutilitzant
   motors de detecció + primitives 1D per a Op3, reorientant la peça R (409 per-regla + prompt Op4).
3. **A.5 migració — DISSENY DEL CAMP (decisió requerida):**
   - Camp nou `garment_type_item` FK→`tasks.GarmentTypeItem` al `GradingRuleSet`, nullable additiu (**opció i
     recomanada**) **vs** modelar-ho des de l'item (opció ii). Reconciliar amb `GTI.grading_rule_set` existent.
   - **Constraint parcial** `UniqueConstraint([customer,size_system,garment_type_item,fit_type], condition=Q(origen='CLIENT_RUN'))`
     — canònics intactes. Confirmar la condició (`origen='CLIENT_RUN'` vs `customer IS NOT NULL`).
   - Estratègia 27 existents: canònics NULL intactes; resoldre {115,116} **abans** d'activar la constraint; LOS
     backfill quan es conegui l'item; NULL-no-classificats fora d'abast.
4. **A.6 fusió — decisió de domini:** les **4 POMs {501-504}** (M1/M2/I/I4) van al **catàleg 115** (AMPLIAR, llei) o
   resten **residents del 269** (decisió S10)? La resta de la fusió és mecànica (re-apuntar 269→115, delete 116, GTI 5→115).
5. **Abast dels commits de la Fase B (B.1–B.5):** confirmar l'ordre i que **cap** toca el motor
   (`generate_graded_specs`/`_apply_rule`), F-4/garment_group al picker, ni el fork gradingAxes.

**Fora d'abast confirmat:** motor de grau per dins · F-4 garment_group picker · fork gradingAxes vs còpia inline ·
Motor de Patrons. Si un pas de B exigeix tocar el motor → ATURAR i reportar.

---

*Fase A tancada. Read-only respectat: cap escriptura fora d'aquest fitxer, cap dada modificada. Cada fet ancorat a
`fitxer:línia` o a `SELECT` real sobre `fhort` (tenant id=2).*

---

## GATE D'AGUS (2026-07-16) — decisions Patró C

1. **Disseny del camp (A.5):** **opció (i)** — afegir `garment_type_item` FK (nullable, additiu) al `GradingRuleSet`
   i reconciliar `GTI.grading_rule_set` perquè apunti al mateix contenidor.
2. **Constraint parcial (A.5):** `UniqueConstraint([customer, size_system, garment_type_item, fit_type],
   condition=Q(origen='CLIENT_RUN'))`. Canònics (customer NULL) intactes.
3. **Les 4 POMs {501-504} (A.6):** **residents del model 269**, NO al catàleg 115 (es respecta la decisió S10:
   POMs específics de model, no de catàleg). 115 es manté curat a 34 regles.
4. **Fase B:** endavant amb tot B.1–B.5, commits petits i verds, backup **PRE-CONT** abans de la 1a escriptura,
   aturar si un pas exigeix tocar el motor de grau.

*Fase B en execució. Resultat i cens final s'anoten al final d'aquest doc.*

---

# RESULTAT — FASE B (2026-07-16, dev, SENSE push)

> Backup lògic PRE-CONT del schema `fhort` pres abans de la 1a escriptura (1.5 MB, verificat).
> Regla del verd respectada a cada commit (`manage.py check` + `npm run build`). Cap push (l'Agus).

## Commits (7, per ordre)

| # | Hash | Peça |
|---|---|---|
| B.1 | `0db194a` | GradingRuleSet: camp `garment_type_item` + `UniqueConstraint` parcial (origen=CLIENT_RUN) |
| B.2a | `4174d60` | primitives de la llei (detecció + cerca + classificació) |
| B.2c | `6298fb7` | Import W5 reescrit segons la llei (SEMBRA/AMPLIA/CONFLICTE/CREA) |
| B.2d | `cff5a3c` | ImportWizard: prompts (crear? · conflicte per-regla) + i18n ca/en/es |
| B.3 | `206c79a` | size-map identity-aware (cabla `garment_type_item` + unicitat) |
| B.4 | *(dades)* | reparació Brownie (sense codi; script ORM + destroy real) |
| — | *(doc)* | aquesta diagnosi |

## Migració (B.1)
`pom.0039` additiva: `garment_type_item_id` (nullable) + índex únic parcial
`uniq_client_container_identity ON (customer,size_system,garment_type_item,fit_type) WHERE origen='CLIENT_RUN'`.
Auditat a `fhort`: 27 files amb `garment_type_item` NULL (cap canònic afectat).

## Reparació de dades (B.4)
- **115** completat: `garment_type_item=5` (Blusa), `garment_group=7` (TOPS), + **SizingProfile #524** (visible a «3. Talles»). 34 regles (intacte; les 4 POMs {501-504} NO s'hi afegeixen, decisió GATE).
- **GTI 5** «Blusa» → `grading_rule_set=115` (reconciliació del FK invers).
- **269** re-apuntat a 115; residents re-sembrats = **21 (de 115, autoritatiu) + 4 model-resident {501-504}** = 25 (coherent amb els 25 POMs amb base del 269). POM 437 ara pren la forma de 115 (ib=1.00).
- **116 esborrat** via el destroy real (guard 409 net: 0 models, 0 profiles → **204** sense force).

## Verificació end-to-end (B.5) — evidència real (endpoints via request-factory + SELECT)

| Punt | Resultat | Evidència |
|---|---|---|
| **(a)** «Editar model → 3. Talles» del 268/269 → 115 hi és | ✅ | `sizing-profiles/?target=WOMAN&construction=WOVEN&fit=REGULAR&garment_type=63` → `[115]` |
| **(b)** RuleSetPicker → cascada → 115 | ✅ | `grading-rule-sets/` retorna 115 amb WOVEN/REGULAR/TOPS, origen CLIENT_RUN |
| **(c)** import sobre 269 → SEMBRA de 115 + AMPLIA, **cap ruleset nou** | ✅ | confirmar 201; 115 rules 34→35 (afegit POM 501); rulesets 26→26; 8 residents; *(rollback)* |
| **(d)** combinació verge → 409 «crear?» → NO (residents i prou) → SÍ (contenidor nou) | ✅ | 409 `container_absent`; `no_container`→201 grs=None, cap ruleset nou; `create`→201 contenidor **#nou** (cust7/ss29/gti6/fit1/CLIENT_RUN); *(rollback)* |
| **(e)** Regular→Slim (re-point via picker) → residents re-sembrats, GradedSpec canvien, **bases INTACTES** | ✅ | update-step2 (PATCH) → regen; POM 286 XXS/XS/M/L canvien (2.0→0/1/3/4); 21 BaseMeasurement idèntiques; *(rollback)* |
| **(f)** seeds ISO intactes; cens comptat | ✅ | 11 `is_system_default` intactes; total **27→26**; **1** CLIENT_RUN (només 115) |

*Les verificacions (c)(d)(e) s'han fet dins transaccions amb rollback → cap dada real alterada més enllà de la reparació B.4. Estat final net: 0 orfes de test.*

## Cens final de rulesets
**27 → 26** (esborrat el 116). **CLIENT_RUN: 2 → 1** (només **115**, ara contenidor canònic complet amb identitat
`customer 7 · ss 29 · garment_type_item 5 (Blusa) · fit REGULAR`). Cap col·lisió de contenidor de client restant.
11 canònics `is_system_default` intactes. La constraint parcial protegeix la unicitat d'ara endavant.

## Notes / deute anotat
- **Llei a `DECISIONS.md`:** cal escriure la llei del contenidor a `DECISIONS.md §2` (avui només viu al brief i aquí).
- **Tensió AMPLIAR vs decisió S10 (4 POMs):** la llei diu que un re-import AMPLIA el contenidor amb les POMs noves
  de la fitxa; el GATE va decidir que, per a la REPARACIÓ del 269, les 4 POMs {501-504} resten model-resident (no
  al catàleg 115). Un futur re-import de 269 SÍ les afegiria a 115 (comportament de la llei). Assenyalat, no bloqueja.
- **Model sense classificar:** la cerca del contenidor depèn de la classificació del model (customer+ss+gti+fit).
  El model 268 té els codis d'eix buits (artefacte del clon S10) → un re-import seu no trobaria 115 per fit buit;
  no és un defecte de la llei sinó de classificació del model. 269 (fit='Regular') sí resol correctament.
- **`derive_grading_rule_set` / `cerca_client_equivalent`** queden com a codi mort (cap cridador) després de
  jubilar-los del camí d'import; no s'esborren en aquest sprint (fora de focus).
- **Divergència `propaga_ancoratges` vs `_apply_rule`** en el break a l'extrem petit: observada en construir les
  fitxes de prova (la primera projeccció no reproduïa el break); NO és d'aquest sprint (motor, zona intocable) —
  anotada per a una diagnosi pròpia.

## Diagnosis superades
Aquest sprint supera la conclusió de `DIAGNOSI_DUPLICACIO_GRADINGRULESET_CLIENT.md` («no fusionar 115/116, deute
anotat») i completa `DIAGNOSI_CRUD_GRADINGRULESET_EIXOS.md` (F-1..F-5 + identitat del contenidor). La llei del
contenidor únic les revoca com a font de decisió (queden com a històric del camí recorregut).

*Fase B tancada. 7 commits locals verds a `dev`, SENSE push. L'Agus fa el push quan la seva prova visual del
punt (a) surti verda.*
