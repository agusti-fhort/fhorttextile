# DIAGNOSI — CRUD GradingRuleSet: els eixos (target/construction/fit/group) i per què un ruleset de client no és usable end-to-end

> **Data:** 2026-07-16 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
> **Abast:** dimensionar el fix perquè crear un `GradingRuleSet` de client (`origen=CLIENT_RUN`) sigui
> usable des de producte (picker del model + de l'item), sense passar per shell ORM. Origen del problema:
> el ruleset 115 (S10) neix amb `construction/fit/garment_group = NULL` i queda inabastable a la cascada.
> **Convenció:** cada afirmació porta `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi** (verificat).
> Propostes marcades `💡 PROPOSTA (a validar)` — decisions humanes (Patró C). Cap escriptura fora d'aquest doc.

---

## RESUM EXECUTIU

1. **El wizard size-map ja RECULL construction/fit, però només els aplica al SizingProfile, no al
   GradingRuleSet.** El front `SizeMapSetup.jsx` té selectors de construction/fit alimentats pel `lookups`
   (`SizeMapSetup.jsx:493-502`) i els envia com a `construction_id`/`fit_type_id` **dins `perfils`**
   (`:351-354`). El backend els resol per a `SizingProfile` (`size_map_views.py:701-702`) però crea el
   `GradingRuleSet` **només amb `target`** (`size_map_views.py:816-819`). **La dada hi és al mateix payload;
   simplement no es cabla al ruleset.** → fix petit i de baix risc.

2. **El "disabled" del CRUD ve d'un TODO OBSOLET, no d'una raó de domini.** El `RuleSetModal` deshabilita
   target/construction/fit (`GradingRuleSets.jsx:1013-1015`) amb el motiu escrit: "el backend espera IDs i el
   front només té codis; **cal endpoint codi→id**" (`:909-918, :936-939`). **Aquests endpoints JA EXISTEIXEN**
   (Sprint S2): `targets/`, `construction-types/`, `fit-types/` (`tasks/urls.py:159-161`). El TODO és estale.

3. **No hi ha cap col·lisió de domini que justifiqui bloquejar els eixos.** Els 27 rulesets vius conviuen amb
   combinacions target×construction×fit distintes (cada canònic n'és una variant: WOVEN/REGULAR, KNIT/SLIM…).
   La unicitat NO és per eixos sinó **per `nom`** (no hi ha `unique(size_system,nom)`, `size_map_views.py:791`).
   El serializer **ja permet escriure** construction/fit/garment_group (no són a `read_only_fields`,
   `serializers.py:214`). El que falla és la CADENA DE FRONT (modal disabled + no es cablen al create).

4. **construction/fit NULL = buits per omissió; garment_group NULL = eix vestigial (comodí de facto).**
   Cens viu (27 rulesets): construction/fit **omplerts a 22/27** i buits només als 5 client/import
   (93,104,108,111,115); **cap canònic seed té construction/fit buit**. En canvi `garment_group` és **NULL a
   24/27, inclosos els 11 canònics** — només 3 rulesets "Importació fitxa" el fixen. → construction/fit són
   discriminadors reals (cal capturar-los); garment_group **no s'ha de fer obligatori** (trencaria els 11 seeds).

5. **El filtre del picker és lenient (NULL=comodí), però la cascada de la UI obliga a triar un FIT que els
   rulesets sense fit no ofereixen** → un ruleset amb tots els eixos NULL (115) és inabastable pel seu propi
   camí. La leniència és, de fet, una **xarxa de seguretat** per als client rulesets no classificats.

6. **Blast radius acotat i DUPLICAT.** El picker (`AxesSelector`+`RuleSetPicker`+`gradingAxes.js`) l'usen
   **2 superfícies**: la fitxa de model (`ModelSheet.jsx:451`) i l'autoria d'item (`ItemAuthoring.jsx:256-260`).
   La pàgina CRUD `GradingRuleSets.jsx` té una **còpia pròpia inline** de la mateixa lògica de matching
   (`:184`, admès a `gradingAxes.js:4-6`). Tot és frontend compartit per TOTS els tenants; els 25/27 rulesets
   existents (amb construction+fit omplerts) **no canvien de comportament** si el fix es fa "capturar a l'origen".

---

## BLOC A1 — Wizard size-map: per què només fixa target

**Creació del ruleset** (`pom/size_map_views.py:816-819`):
```python
rule_set = GradingRuleSet.objects.create(
    nom=rs_nom, size_system=ss, actiu=True, target=target,
    origen=GradingRuleSet.ORIGEN_CLIENT_RUN, customer=alias_customer)
```
Només `target` (+ `targets.add(target)` a `:820-821`). **NO** passa `construction`, `fit_type` ni
`garment_group`. El `data.get(...)` del handler (`:629-644`) llegeix `target_codi, base_unit, talles,
grading, perfils, size_system_id, on_conflict, base_size, nom_variant` — **mai** `construction`/`fit` per al
ruleset.

**Però la dada existeix i es recull:**
- **Lookups del wizard** (`size_map_views.py:120-137`): `GET size-map/lookups/` retorna `targets`,
  `constructions`, `fit_types`, `garment_types` actius (amb `id`).
- **Front** (`SizeMapSetup.jsx`): estat `construction_id`, `fit_type_id`, `garment_type_id` (`:205`);
  selectors poblats pel lookup (`:493-508`); **s'envien dins `perfils`** (`:351-354`:
  `{target_codi, construction_id, fit_type_id, garment_type_id}`).
- **Backend** els resol **per al SizingProfile** (`size_map_views.py:700-708`:
  `ConstructionType.objects.filter(pk=p.get('construction_id'))`, `FitType...`), **no** per al ruleset.

> **FET:** el construction/fit del run **ja viatja al backend** (dins `perfils`) i **ja es materialitza** al
> `SizingProfile`, però el `GradingRuleSet.create()` (`:816`) l'ignora. Cablar-lo és **una línia de dades**
> del mateix payload — no cal cap dada nova ni cap endpoint nou.

**Veredicte A1:** el wizard no fixa construction/fit al ruleset per **omissió del create path**, no per manca
de dades. Fix de baix risc: llegir `perfils[0].construction_id/fit_type_id` (o un camp dedicat) i passar-los a
`GradingRuleSet.create()`. `garment_group` requeriria mapatge `garment_type→garment_group` (l'eix vestigial, veure A4).

---

## BLOC A2 — CRUD: per què target/construction/fit són disabled

**El modal** (`frontend/src/pages/GradingRuleSets.jsx:903-990`):
- Camps `target_codi_form/construction_codi_form/fit_type_codi_form` renderitzats amb `disabled`
  (`:1013-1015`).
- Motiu escrit al codi (`:909-918`): *"Target/Construction/Fit cannot be sent directly as a code because the
  backend expects IDs… (TODO) caldria endpoint per resoldre codi→id. De moment, els enviem only if the RuleSet
  being edited already has them (we pass the original ID)."*
- `handleSubmit` (`:923-943`): el payload només inclou `target/construction/fit_type` **si `form.X != null`**
  (`:941-943`), i aquests venen NOMÉS de `rs?.target/…` (FK id de l'objecte original). Per a una creació nova
  → són `null` → **mai s'envien** → el ruleset neix amb els tres eixos a NULL.
- Nota visible a l'usuari: `t('grading.modal_note')` (`:1016-1018`).

**El bloqueig NO és de domini:**
- El serializer **ja accepta** aquests FKs a l'escriptura (POST/PATCH): `construction`, `fit_type`,
  `garment_group`, `target`, `targets` són a `Meta.fields` i **NO** a `read_only_fields`
  (`pom/serializers.py:203-214`; read-only només `is_system_default, regles, regles_count`).
- El ViewSet és un `ModelViewSet` net amb lògica custom **només al `destroy`** (`pom/views.py:152-209`);
  cap validació que prohibeixi escriure eixos.
- **Els endpoints codi→id que el TODO reclama JA EXISTEIXEN** (Sprint S2, `tasks/urls.py:158-161`):
  `targets/` → `targets_list_view`, `construction-types/`, `fit-types/`, muntats sota el prefix v1
  (`urlpatterns = _s2_paths + urlpatterns`, `:170`). Serializers a `pom/s2_serializers.py:7-33`.

> **⚠️ MATÍS (gap real menor):** `FitTypeSerializer` (`s2_serializers.py:31-34`) exposa `codi, nom_en,
> display_order` **però NO `id`**. `FitType` té PK `id` autoincrement (`codi` és `unique` amb choices però NO
> `primary_key`, `pom/models.py:703-713`). El FK `GradingRuleSet.fit_type` (`:576`) és un
> `PrimaryKeyRelatedField` → **espera l'id**. Per tant, per fixar `fit_type` des del CRUD cal **afegir `id` a
> `FitTypeSerializer`** o fer que el ruleset accepti `fit_type` per codi. `targets/` i `construction-types/`
> **sí** retornen `id` (`TargetSerializer:8`, `ConstructionTypeSerializer:22`).

**Veredicte A2:** el "disabled" és **herència d'un TODO ja resolt** (endpoints S2 codi→id existeixen), no una
raó de domini. Desbloquejar-lo requereix: (a) el front carregui els lookups i enviï els FK ids; (b) afegir `id`
a `FitTypeSerializer`; (c) decidir **quan** és editable (veure A3). Cap col·lisió amb els 24 canònics.

---

## BLOC A3 — Serializer: afegir `origen` read-only + editables condicionals trenca res?

**Estat actual** (`pom/serializers.py:174-214`):
- `origen` **NO és a `Meta.fields`** → ni es llegeix ni s'escriu per l'API (per això l'API retorna el 115 sense
  `origen`, tot i ser CLIENT_RUN a BD).
- `construction/fit_type/garment_group/target/targets` **ja són escrivibles** (a `fields`, no read-only).
- `read_only_fields = ['is_system_default', 'regles', 'regles_count']` (`:214`).

**Impacte dels canvis proposats:**
- **Afegir `origen` com a read-only:** purament additiu. Els 27 rulesets es continuen serialitzant igual + un
  camp nou de lectura (11 `CANONICAL`, 2 `CLIENT_RUN`, 14 `NULL`). **Cap escriptura afectada.** ✅
- **Fer construction/fit/garment_group editables NOMÉS quan `origen=CLIENT_RUN` (o `not is_system_default`):**
  avui ja són editables per a TOTS via serializer, però **cap flux de UI els escriu** (modal disabled). Per
  tant afegir un `validate()` que **bloquegi** l'escriptura quan `is_system_default=True` (protegir els 11
  seeds) **no canvia cap comportament actual** (ningú els escriu avui) i **blinda** els canònics. ✅
- **Els 25/27 existents:** 11 `is_system_default` (protegits pel guard) · 14 NULL + 2 CLIENT_RUN
  (no-sysdefault, quedarien editables) · cap és editat pel CRUD avui → **cap regressió**. ✅

> **💡 PROPOSTA (a validar):** guard mínim `if instance.is_system_default and axis_changed: raise
> ValidationError`. Alternativa més laxa: permetre edició d'eixos si `not is_system_default` (cobreix
> CLIENT_RUN + NULL + IMPORT). La condició EXACTA (`CLIENT_RUN` estricte vs `not is_system_default`) és decisió
> Patró C — recomano `not is_system_default` perquè també desbloqueja classificar els 14 NULL sense un pas previ.

**Veredicte A3:** afegir `origen` read-only és segur i additiu. La condicionalitat d'edició NO trenca cap dels
27 (ningú els edita avui pel CRUD); el guard `is_system_default` protegeix els 11 seeds explícitament.

---

## BLOC A4 — Cens: construction/fit NULL són comodins reals o buits per omissió?

**Cens viu** (`pom_gradingruleset`, 27 files actives, verificat a BD):

| origen | n | construction SET | fit SET | garment_group SET |
|---|---|---|---|---|
| CANONICAL (sysdefault) | 11 | **11/11** | **11/11** | **0/11** |
| CLIENT_RUN | 2 | 1/2 | 1/2 | 1/2 |
| NULL (no classificat) | 14 | 10/14 | 10/14 | 2/14 |

- **construction/fit buits (5 rulesets):** `93` (Baby Months), `104` (LOS Kids), `108` (Mango, 0 regles),
  `111` (LOS TOP), `115` (BRW · Blusa, l'S10). **Tots són client/import/no-classificats; CAP és canònic seed.**
  Les variants de fit canòniques (76/77/78 Slim/Relaxed/Oversized, 80, 82, 85, 92 Flared) **sí** tenen
  construction+fit. → **construction/fit NULL = buits per omissió del camí de creació**, no comodins intencionals.
- **garment_group buit (24 rulesets):** inclou **els 11 canònics seed**. Només `107`, `110`, `116` (tots
  "Importació fitxa") el fixen (grup 4 o 7). → **`garment_group` és un eix VESTIGIAL / comodí de facto** per
  a tot el catàleg canònic.
- **Nota concurrent:** apareix el ruleset **116** (`Importació fitxa · BRW-FW27-0002`, CLIENT_RUN, 25 regles)
  amb construction=WOVEN/fit=REGULAR/group=7 — creat per una sessió concurrent DESPRÉS de l'S10; demostra que
  el camp SÍ es pot omplir (probablement via un altre camí d'import). **No creat per aquesta diagnosi.**

**Dimensionament (resposta directa al brief):**
- construction/fit **buits per omissió** → seguint la lògica del brief: **bloquejar/completar a l'ORIGEN**
  (capturar-los al create), NO afegir "Qualsevol" al desplegable per a aquests. `💡 PROPOSTA (a validar):`
  el fix net és **A1 (cablar-los al wizard) + A2 (desbloquejar el CRUD)**, no tocar el picker.
- `garment_group` **comodí de facto** → **NO** s'ha de fer obligatori (trencaria els 11 seeds, que el tenen
  NULL i avui casen per leniència). `💡 PROPOSTA (a validar):` o bé (i) treure `garment_group` de la
  cascada/gate del picker (fer-lo opcional "Any"), o (ii) deixar-lo com a comodí explícit. Requerir-lo
  divergiria del patró canònic.
- Si es decideix **bloquejar la creació sense els 4 eixos**, ha de ser sense `garment_group` (o amb un "Any"
  explícit per a ell), perquè cap canònic el té.

**Veredicte A4:** construction/fit → buits per omissió (capturar a l'origen). garment_group → vestigial
(no obligar; opció "Any" o fora del gate). El picker no s'ha de tocar per als 22 rulesets ben omplerts.

---

## BLOC A5 — Blast radius: qui usa el picker

**Consumidors del picker compartit** (`AxesSelector` + `RuleSetPicker` + `gradingAxes.js`):
1. **Fitxa de model** — `ModelSheet.jsx:451` → `RuleSetCard` (`components/model/RuleSetCard.jsx`), pas "Talles";
   `onPick` → `PATCH update-step2 {grading_rule_set_id}` (`RuleSetCard.jsx:41-48`).
2. **Autoria d'item** — `ItemAuthoring.jsx:256-260` (`AxesSelector` + `RuleSetPicker`), assigna la FK
   `grading_rule_set` a la plantilla d'item.

**Fork de lògica (⚠️):** la pàgina CRUD `GradingRuleSets.jsx` **NO** usa el mòdul compartit: té la seva
**pròpia còpia inline** del matching (`:87-90` estat d'eixos, `:184` `matchingRuleSets`, `:503` un
`RuleSetCard` DIFERENT del del model). Documentat com a deute a `gradingAxes.js:4-6` ("GradingRuleSets segueix
amb la seva còpia pròpia… DEUTE: unificar"). → **un canvi a la cascada del picker s'ha d'aplicar a DOS llocs**
(mòdul compartit + còpia de GradingRuleSets) per ser coherent. Un fix **backend** (capturar eixos a l'origen)
arregla ambdues superfícies alhora sense tocar cap dels dos fronts de matching.

**Abast multi-tenant:** tot és frontend/serializer compartit per **tots** els tenants i customers. Els 25/27
rulesets existents tenen construction+fit omplerts (excepte els 5 client/import) → **el fix "capturar a
l'origen" no els toca**. Qualsevol canvi a `matchingRuleSets`/`AxesSelector` (p.ex. opció "Any") SÍ afectaria
tots els tenants → cal marcar-ho i verificar que els 22 ben omplerts no canvien de resultat.

**Veredicte A5:** 2 consumidors del picker (model + item) + 1 còpia inline al CRUD. Fix backend (A1+A2)
= abast mínim, arregla les 3 superfícies sense tocar la lògica de matching. Fix de picker (opció "Any")
= abast ampli (tots els tenants + duplicat en 2 llocs) → només si es decideix per garment_group.

---

## TAULA FINAL — per al CTO (EXISTEIX / FALTA / DIFERENT)

| Node | Estat | Detall | Referència |
|---|---|---|---|
| Wizard recull construction/fit | **EXISTEIX** | selectors poblats pel lookup; enviats dins `perfils` | `SizeMapSetup.jsx:493-508, :351-354` |
| Wizard aplica construction/fit al **ruleset** | **FALTA** | `create()` només posa `target`; els ids van al SizingProfile | `size_map_views.py:816-819, :700-708` |
| Endpoints codi→id (target/constr/fit) | **EXISTEIX** (S2) | el TODO del modal és estale | `tasks/urls.py:159-161` |
| `id` a `fit-types/` | **FALTA** | `FitTypeSerializer` omet `id`; el FK n'exigeix | `s2_serializers.py:31-34`, `models.py:703` |
| CRUD pot escriure eixos | **DIFERENT** | serializer ja ho permet; el FRONT ho bloqueja (disabled) | `serializers.py:214` vs `GradingRuleSets.jsx:1013-1015` |
| Raó de domini per bloquejar eixos | **NO EXISTEIX** | unicitat per `nom`, no per eixos; sense col·lisió | `size_map_views.py:791` |
| `origen` a l'API | **FALTA** | no a `Meta.fields` → API retorna null | `serializers.py:203-214` |
| construction/fit NULL = intencional | **NO** (buits per omissió) | 22/27 omplerts; 0 canònics buits | cens A4 |
| garment_group com a discriminador | **DIFERENT** (vestigial) | NULL a 24/27 inclosos 11 seeds | cens A4 |
| Consumidors del picker | **EXISTEIX** (2 + 1 fork) | model + item; CRUD té còpia pròpia | `ModelSheet.jsx:451`, `ItemAuthoring.jsx:256`, `gradingAxes.js:4-6` |

---

## SÍNTESI DEL FIX (dimensionat — decisions Patró C)

> Fets i mides; la decisió és humana.

- **F-1 (mínim, backend) · Cablar construction/fit al wizard.** Passar `construction_id`/`fit_type_id` (ja al
  payload, `perfils`) al `GradingRuleSet.create()` (`size_map_views.py:816`). ~3 línies. Arregla els rulesets
  NOUS de client per als 3 fronts alhora. **No toca cap dels 27 existents.** Risc: baix.
- **F-2 (CRUD usable) · Desbloquejar el modal.** Carregar lookups S2 al front, enviar FK ids, treure
  `disabled` **quan `not is_system_default`**. Requereix **F-2a: afegir `id` a `FitTypeSerializer`**. Risc:
  baix (guard protegeix els 11 seeds; endpoints ja existeixen).
- **F-3 (visibilitat) · `origen` read-only al serializer** + (opcional) permetre'l settejable a la creació de
  CLIENT_RUN pel CRUD. Risc: additiu.
- **F-4 (picker) · Decisió garment_group:** treure'l del gate/cascada o donar-li "Any". **Ampli** (2 fronts +
  còpia CRUD, tots els tenants) → només si es vol. Els construction/fit NO necessiten "Any" (millor capturar-los).
- **Deute a assenyalar (no tocar sense decisió):** el fork de matching (mòdul compartit vs còpia inline de
  `GradingRuleSets.jsx`) — qualsevol canvi de cascada s'ha de fer a tots dos.

---

*Diagnosi Patró A tancada. Read-only respectat: cap escriptura fora d'aquest fitxer. Cada fet ancorat a
`fitxer:línia` o a `SELECT` real sobre staging (schema `fhort`, tenant id=2). Cap dada de client modificada.*
