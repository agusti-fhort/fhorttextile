# DIAGNOSI — El gate de GradingRuleSet al wizard d'ITEM, el cens del camp i el target duplicat

**Data:** 2026-07-23 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
(HEAD `0fd3f2c`) · símptomes observats a PROD (`main`).

**Abast:** A3' (on és l'obligatorietat del GRS a l'item i qui consumeix
`GarmentTypeItem.grading_rule_set`), A4' (revertir el dany fet a PROD), A6 (cartografia del target
al wizard d'item), A5' (talls proposats). **Substitueix A3/A4 del brief anterior.**

**Convenció:** cada afirmació porta `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi**
(cercat, no especulat). Les propostes van marcades `💡 PROPOSTA (a validar)` i són separades dels fets.

**Decisió Patró C que mana sobre aquesta diagnosi** (Agus, 2026-07-23): *el GTI NO porta GRS
assignat; el GRS s'assigna AL MODEL. Un item pot tenir N combinacions — les superfícies
col·lideixen al model.* Aquesta diagnosi NO discuteix la decisió: en mesura el cost.

---

## Resum executiu

1. **L'obligatorietat és 100% de frontend, i és més dura del que sembla.** El gate viu a
   `ItemAuthoring.jsx:161` (`canNext = !!chosenRulesetId`), però el bloqueig real és a
   `ItemAuthoring.jsx:122-136`: **l'item només es CREA dins de `assignRuleset()`**. Sense triar un
   ruleset no hi ha «Següent» *i tampoc hi ha item*. El backend **no exigeix res**: el camp és
   `null=True, blank=True` (`tasks/models.py:329-331`), el serializer no el fa obligatori
   (`serializers_b.py:110-118`) i el ViewSet és un `ModelViewSet` pla sense hooks
   (`views_b.py:842-877`). **Cap signal** al tenant (`tasks/signals.py` només declara un `Signal`
   de consum, sense receivers).

2. **Des del 2026-06-22** (commit `43baffa`, Sprint Llibreria d'Items B3-fix; el camp havia entrat
   el mateix dia amb `2ef87b4` / migració `tasks/0023`). El comentari del model anunciava «una 2a
   migració (post-Fase B) la farà NOT NULL» (`tasks/models.py:324-325`) — **aquesta migració NO
   EXISTEIX**: cap migració posterior toca el camp. La porta no s'ha endurit mai a BD.

3. **El cens de lectors és petit: 2 consumidors reals, i cap es trenca amb NULL.** (a) la promoció
   model→item el llegeix només per resoldre el `size_system` de la talla, i **ja té el camí de
   NULL escrit i cobert per test** (`models_app/views.py:2926-2941`,
   `tests_sembra_grading.py:877-891`); (b) el wizard de model el llegeix per **SUGGERIR** un
   ruleset (ordre del picker, mai assignació: `ModelWizard.jsx:289-296`, `:733`). La sembra de
   models NOU **NO el llegeix** (va per `GarmentPOMMap`/`ItemBaseMeasurement`). Cens complet a §2.

4. **El dany a PROD és petit i confinat al catàleg.** Al backup de PROD de les 02:30 d'avui, **les
   57 files de `tasks_garmenttypeitem` tenen `grading_rule_set_id` NULL i `base_size_definition_id`
   NULL** — l'assignació de l'Agus és l'ÚNICA del tenant. I **cap dels 52 models de PROD apunta a
   l'item 16 (`hoodie`)**: 0 models afectats. La reversió és un `UPDATE … SET NULL` d'una fila,
   sense cascades (§3).

5. **A6 — al wizard d'ITEM no hi ha cap "assignació múltiple de targets"; el que hi ha és pitjor:
   el target no es persisteix ENLLOC.** Hi ha exactament **dues** superfícies que parlen de target
   (`ItemAuthoring.jsx:256` cascada interactiva i `RuleSetPicker.jsx:131-141` etiqueta de la card),
   i la primera **no escriu res**: `axes` és estat local que només filtra el picker
   (`ItemAuthoring.jsx:59`), i en reobrir es **re-deriva del ruleset assignat**
   (`ItemAuthoring.jsx:95-101`). La sensació de duplicat és real: preguntes el target a dalt i a
   baix reapareix, en plural, a la card que has de clicar per «Assignar». El "múltiple" és
   `GradingRuleSet.targets` (M2M, `pom/models.py:592-598`), propietat del RULESET, no de l'item.
   **`GarmentType.targets_recomanats` NO REVIU**: retirat per `pom/0041`, l'única vista que el
   consumia està jubilada (`pom/s2_views.py:379`).

6. **Conseqüència no òbvia de treure el GRS de l'item: se n'enduu 5 coses més.** Amb el ruleset
   fora, l'item es queda sense: els 4 eixos del pas Context (target/construcció/fit/grup — tots
   existeixen NOMÉS per filtrar rulesets, `gradingAxes.js:105-125`), la font del `size_system` del
   pas 2 (`ItemAuthoring.jsx:108-119`) i, per tant, la manera de triar `base_size_definition` — que
   és la talla en què s'expressen TOTES les `ItemBaseMeasurement` (`pom/models.py:473`). Això no
   contradiu la decisió, però diu que el tall (a) no és una línia: és una peça petita amb una
   pregunta de disseny al darrere (§5.1).

7. **A5'(b) confirmat i pitjor a PROD que a staging.** La compatibilitat target↔família viu a
   `SizingProfile` (`pom/views.py:121-132`). A PROD hi ha **33 perfils que cobreixen 8 famílies** i
   `SWEATSHIRTS_MIDLAYERS` **no en té cap** → amb qualsevol target, la família de la dessuadora
   **no apareix** al pas Peça del wizard de model. A staging n'hi ha 45 i la família existeix per a
   BOY/GIRL/TODDLER_BOY/TODDLER_GIRL, **però no per a WOMAN ni MAN**. I **NO EXISTEIX cap endpoint
   de creació de `SizingProfile`** (§5.2).

---

## BLOC 1 — A3'a · On és l'obligatorietat, i des de quan

### 1.1 El gate visible

| Peça | `fitxer:línia` | Fet |
|---|---|---|
| Condició del botó | `frontend/src/pages/ItemAuthoring.jsx:161` | `const canNext = step === 1 ? !!chosenRulesetId : false` |
| Botó «Següent» | `frontend/src/pages/ItemAuthoring.jsx:337-340` | `disabled={!canNext \|\| busy}` |
| Wizard de 2 passos | `frontend/src/pages/ItemAuthoring.jsx:19` | `STEPS = ['step1_context', 'step2_construction']` |

### 1.2 El gate REAL (més dur): sense ruleset no neix l'item

`ItemAuthoring.jsx:122-146` — `assignRuleset(rs)` fa dues coses en la mateixa acció:

```
127-132   if (!id) { … garmentTypeItems.create({garment_type, code, name, active}) … }   ← CREA l'item
133-136   payload = { grading_rule_set: rs.id }; await garmentTypeItems.update(id, payload)
```

És **l'única crida a `garmentTypeItems.create` de tota la pàgina** (cercat: no n'hi ha cap altra).
`goNext()` (`:163-174`) només fa `update` i **només si `itemId` ja existeix**. Per tant, en el camí
de CREACIÓ, no triar ruleset no vol dir «item sense graduació»: vol dir **cap item**.

En el camí d'EDICIÓ (el cas de l'Agus, «Editar item · hoodie») l'item ja existeix, però el pas 2
(talla base + mides) queda **inabastable** fins que s'assigna un GRS.

### 1.3 El backend no obliga a res

| Capa | `fitxer:línia` | Fet |
|---|---|---|
| Camp | `backend/fhort/tasks/models.py:329-333` | `FK('pom.GradingRuleSet', on_delete=PROTECT, null=True, blank=True)` |
| Intenció declarada | `backend/fhort/tasks/models.py:322-325` | *«de moment NULLABLE … una 2a migració (post-Fase B) la farà NOT NULL»* |
| Migració NOT NULL | — | **NO EXISTEIX**. Només `tasks/0023` (AddField) i `tasks/0024` (que només la referencia com a dependència). |
| Serializer | `backend/fhort/tasks/serializers_b.py:110-118` | `grading_rule_set` a `fields`, sense `required=True` |
| `validate()` | `backend/fhort/tasks/serializers_b.py:127-140` | només crida `clean()` per validar coherència amb `base_size_definition`; **cas NULL = skip** (`models.py:341-353`) |
| ViewSet | `backend/fhort/tasks/views_b.py:842-877` | `ModelViewSet` pla (queryset + anotacions + permisos). Cap `perform_update`, cap validació extra |
| Signals | `backend/fhort/tasks/signals.py:1-17` | **cap receiver**; només declara `model_consumption_started` |

**Conclusió:** el camp és opcional a BD, a l'ORM i a l'API. **L'obligatorietat és una sola línia de
React.**

### 1.4 Des de quan

| Commit | Data | Què |
|---|---|---|
| `2ef87b4` | 2026-06-22 | `tasks/0023` — FK Item→GradingRuleSet + constrenyiment de `base_size_definition` |
| `d0dca2c` | 2026-06-22 | B3 — pàgina d'autoria d'Item (4 passos) |
| `43baffa` | 2026-06-22 | **B3-fix — 4 passos → 2; entra `canNext` (el gate)** |
| `57e1075` | 2026-07-19 | flag `?amb_regles=1` al picker (no toca el gate) |
| `46f4df0` | 2026-07-20 | ItemAuthoring passa a `CascadeSelector` (no toca el gate) |

*(`git log -S "const canNext = step === 1" -- frontend/src/pages/ItemAuthoring.jsx` → `43baffa`.)*

**Veredicte BLOC 1:** el gate és **frontend-only, d'un mes d'antiguitat, i mai es va endurir a BD**.
Treure'l no requereix cap migració ni cap canvi de contracte d'API.

---

## BLOC 2 — A3'b · Cens COMPLET de consumidors de `GarmentTypeItem.grading_rule_set`

Mètode: `grep -rn` de `grading_rule_set` + `garment_type_items` (related_name, `models.py:331`) a
`backend/` i `frontend/src/` (exclosos `node_modules/` i `dist/`), separant els encerts que són
**`Model.grading_rule_set`** (un camp diferent, del model, que NO és aquest) dels que són del GTI.

### 2.1 ESCRIPTORS (qui hi escriu)

| # | Superfície | `fitxer:línia` | Fet |
|---|---|---|---|
| W1 | Wizard d'item (pas Context) | `ItemAuthoring.jsx:133-136` | PATCH `{grading_rule_set: rs.id}` — **l'únic escriptor de producte** |
| W2 | `bootstrap_tenant` (sembra de tenant nou) | `tasks/management/commands/bootstrap_tenant.py:300-312` | copia el valor origen→destí; **si la FK nullable apunta a un bloc no seleccionat, la posa a NULL i compta `nulled`** (cas Free sense grading, `:304`) |
| W3 | Tests | `models_app/tests_sembra_grading.py:742`, `:879`; `pom/test_p4_scope_proposals.py:66`; `fitting/tests.py:58` | fixtures |

**NO EXISTEIX** cap altre escriptor: ni l'import de size-map (`pom/size_map_views.py:978-1010` crea
`SizingProfile` i posa `GradingRuleSet.garment_type_item`, **mai** l'invers), ni cap data-migration
de backfill (cercat a `*/migrations/*.py`), ni cap comanda de seed.

### 2.2 LECTORS REALS (els que canvien el comportament del producte)

| # | Qui | `fitxer:línia` | Què en fa | Es trenca amb NULL? |
|---|---|---|---|---|
| **R1** | **Promoció model→item** (flux GTI-plantilla del 21-22/07) | `models_app/views.py:2926-2941` | `ss_item_id = getattr(item.grading_rule_set, 'size_system_id', None)`; serveix per resoldre en quin `SizeSystem` buscar la talla base que s'escriurà a l'item | **NO.** El camí de NULL ja existeix i és explícit: retorna 200, promou els valors i deixa `base_size_definition` com estava amb un `talla_motiu` que ho diu (`:2930-2934`). **Cobert per test:** `tests_sembra_grading.py:877-891` (`test_item_sense_ruleset_promou_valors_pero_no_toca_la_talla`) |
| **R2** | **Wizard de MODEL — suggeriment del pas 4** | `ModelWizard.jsx:289-296` (llegeix) → `:733` (`suggestedId`) → `RuleSetPicker.jsx:35-37,88,123-125` → `gradingAxes.js:185-190` | **NOMÉS ORDENA**: puja el ruleset suggerit al capdamunt i el marca amb un pill. La llei escrita al codi és «SUGGERIR ≠ ARROSSEGAR» (`RuleSetPicker.jsx:16-18`) | **NO.** `if (!item?.id) setItemSuggestedRsId(null)` i `.catch(() => null)`; amb `null`, `orderWithSuggestedFirst` retorna `matches` intacte (`gradingAxes.js:186`) |

> El comentari de `ModelWizard.jsx:286-288` diu textualment: *«És el primer lector real d'aquesta
> FK: fins ara ningú la consumia i només feia de semàfor al catàleg d'items.»*

### 2.3 LECTORS DE PRESENTACIÓ (semàfor, no comportament)

| # | Qui | `fitxer:línia` | Què |
|---|---|---|---|
| P1 | Serializer del GTI | `tasks/serializers_b.py:104,120-121` | `grading_rule_set_nom` (SerializerMethodField, read-only) |
| P2 | Card d'item a Garment Types | `GarmentTypes.jsx:384,398-407` | termòmetre de 3 punts (POMs · grading · talla base); sense ruleset → punt apagat i «—» |
| P3 | Wizard d'item (rehidratació) | `ItemAuthoring.jsx:93-101` | recupera el ruleset i **en deriva els 4 eixos** de la cascada |
| P4 | `select_related` (rendiment) | `tasks/views_b.py:858` | — |

### 2.4 El que NO el llegeix (verificat, contra les sospites del brief)

| Sospita | Veredicte | Prova |
|---|---|---|
| Sembra de models nous (`materialitzar-poms`) | **NO el llegeix** | `models_app/views.py` (funció `materialize_poms_view`, ~`:900-1050`): l'única menció d'item és `GarmentPOMMap` (`:929`). La sembra va per `GarmentPOMMap` + `ItemBaseMeasurement` |
| Creació de model (wizard) arrossega el ruleset de l'item | **NO** | `_resolve_garment_def` (`models_app/views.py:594-596`) només mira `d['grading_rule_set_id']` del payload; `ModelWizard.jsx:106-108` ho declara: *«LLEI 5 CAPES … Aquí NO s'arrossega grading_rule_set_id»* |
| Motor de graduació | **NO** | `pom/services.py:651-706` i `models_app/views.py:744-867` treballen tots amb **`Model.grading_rule_set`**, un camp diferent |
| Federació / `instantiate_external_models` | **NO** | `tenants/management/commands/instantiate_external_models.py:79-164` va per `Model.grading_rule_set` |
| Constraint del CONTENIDOR de client | **camp DIFERENT** | La identitat del contenidor és `GradingRuleSet.garment_type_item` (`pom/models.py:569-572`), FK **invers**. El comentari `pom/models.py:566-568` diu que «es reconcilien al backfill» — **aquest backfill NO EXISTEIX** com a migració |

### 2.5 Acoblament intern que sí que s'ha de mirar

`GarmentTypeItem.clean()` (`tasks/models.py:341-353`) lliga `base_size_definition` al
`size_system` del ruleset. Amb ruleset NULL fa **skip** (no peta). Però la **UI** en depèn de veritat:
`ItemAuthoring.jsx:108-119` construeix la llista de talles del pas 2 des de
`chosenRuleset.size_system`. **Sense ruleset, el pas 2 no té d'on treure talles** i
`GarmentTypeItem` **no té cap altre camp de sistema de talles** (camps reals:
`garment_type, code, name, complexity_order, active, base_size_definition, grading_rule_set` —
`tasks/models.py:296-333`).

**Veredicte BLOC 2:** **2 lectors reals, cap bloquejant.** El camp pot passar a opcional avui sense
trencar cap flux. Retirar-lo del tot (tall (d)) costa: R1 perd la resolució de talla, R2 perd el
suggeriment, i el pas 2 del wizard d'item perd la font del `size_system`.

---

## BLOC 3 — A4' · Reversió del dany a PROD

### 3.1 Efectes en cascada d'assignar/netejar `item.grading_rule_set` (verificat a staging)

| Possible cascada | Veredicte | Prova |
|---|---|---|
| Signals `post_save`/`pre_save` | **CAP** | `tasks/signals.py:1-17` (cap receiver); `grep post_save\|pre_save\|post_delete backend/fhort/tasks/*.py` → 0 encerts |
| Hook al ViewSet/serializer | **CAP** | `views_b.py:842-877`; `serializers_b.py:127-140` (només `clean()`) |
| Materialització de regles a cap model | **CAP** | L'única materialització (`materialize_model_grading_rules`) es dispara des de `update_model_step2` / creació de model (`models_app/views.py:744-867`), sempre des de **`Model.grading_rule_set`**. Assignar-lo a l'ITEM no toca cap model |
| `on_delete=PROTECT` | **només a la inversa** | Bloqueja esborrar un `GradingRuleSet` mentre un item hi apunti (`tasks/models.py:330`). **Netejar el pointer allibera aquest bloqueig**; no destrueix res |
| `base_size_definition` | **acoblat** | Si en el mateix acte es va triar talla base, queda un `base_size_definition` que ja no té ruleset que el validi. `clean()` fa skip amb ruleset NULL → **no peta**, però és estat orfe respecte de la línia base |

### 3.2 La línia base de PROD (oracle read-only: backup del 2026-07-23 02:30)

Font: `/srv/fhort-prod-backups/incoming/fhort_textile_20260723_023001.dump`, llegit amb
`/usr/lib/postgresql/18/bin/pg_restore -a -n fhort -t <taula> -f -` (cap escriptura, cap restore).

| Fet | Valor |
|---|---|
| Files a `fhort.tasks_garmenttypeitem` | **57** |
| Files amb `grading_rule_set_id` NO NULL | **0** |
| Files amb `base_size_definition_id` NO NULL | **0** |
| L'item de la dessuadora | `id=16`, `code=hoodie`, «Dessuadora (amb/sense caputxa)», `garment_type_id=67` (`SWEATSHIRTS_MIDLAYERS`) |
| Models a PROD | **52** (tots amb `garment_type_item` informat) |
| **Models que apunten a l'item 16** | **0** |
| Models amb `grading_rule_set` propi | 19 |

> El backup és de les **02:30 d'avui**, o sigui **anterior** a l'acció de l'Agus. És exactament la
> foto que cal: **la línia base correcta de tot el catàleg d'items de PROD és NULL a les dues
> columnes**, i cap model penja de l'item tocat.

### 3.3 Procediment de reversió per a PROD — **NO EXECUTAT** (proposta per a l'Agus)

> ⚠️ Patró A: aquí no s'executa res. Això és el guió perquè l'Agus el corri des de SSH a PROD.
> El pas 1 és obligatori: la foto de §3.2 és de les 02:30 i no sap què s'ha tocat després.

**1) Constatar (read-only) — quines files han canviat respecte de la línia base:**

```sql
-- PROD, schema fhort
SELECT id, code, name, garment_type_id, grading_rule_set_id, base_size_definition_id
FROM   tasks_garmenttypeitem
WHERE  grading_rule_set_id IS NOT NULL
    OR base_size_definition_id IS NOT NULL;
-- Esperat segons el backup de les 02:30: NOMÉS la/les fila/es tocades avui (base = 0 files).
```

**2) Constatar que no hi ha dany a la capa d'instància (ha de donar 0):**

```sql
SELECT count(*) FROM models_app_model WHERE garment_type_item_id = 16;   -- 0 al backup
-- I, per si de cas, que cap model ha rebut regles noves avui:
SELECT count(*) FROM models_app_modelgradingrule
WHERE  created_at::date = CURRENT_DATE;   -- ajustar al nom real de la columna de data
```

**3) Revertir (una fila, dues columnes), dins d'una transacció:**

```sql
BEGIN;
UPDATE tasks_garmenttypeitem
SET    grading_rule_set_id = NULL,
       base_size_definition_id = NULL
WHERE  id = 16;      -- o els ids que hagi retornat el pas 1
-- verificar que retorna 0 files:
SELECT id FROM tasks_garmenttypeitem
WHERE grading_rule_set_id IS NOT NULL OR base_size_definition_id IS NOT NULL;
COMMIT;
```

**4) Comprovar que no queda res penjat:** el `GradingRuleSet` que s'havia assignat torna a ser
esborrable (cau el `PROTECT`) i la card de l'item a Garment Types torna a «Grading: —»
(`GarmentTypes.jsx:407`). **Cap altra acció**: no hi ha caches, ni denormalitzacions, ni regles
materialitzades a desfer.

**Alternativa via UI: NO EXISTEIX.** La pàgina d'autoria no ofereix «treure el ruleset»: `onPick`
sempre envia un id (`ItemAuthoring.jsx:133`) i no hi ha cap botó de desassignació. Per UI, el dany
és **irreversible** — un argument més per al tall (a).

**Veredicte BLOC 3:** dany **confinat al catàleg**, 1 fila, 0 models, 0 cascades. Reversió =
`UPDATE … SET NULL`. Cal fer-la per SQL perquè la UI no la sap fer.

---

## BLOC 4 — A6 · Cartografia del target al wizard d'ITEM

### 4.1 (a) Quantes superfícies pregunten target dins `ItemAuthoring`

**Dues** — i només una és interactiva:

| # | Superfície | `fitxer:línia` | Cardinalitat | Interactiva? |
|---|---|---|---|---|
| T1 | `CascadeSelector` (pas 1 de la cascada, «Target») | `ItemAuthoring.jsx:256` → `CascadeSelector.jsx:106-120` | **ÚNIC** (`pick({target: tg.codi, …})`, `:115`) | **SÍ** |
| T2 | Etiqueta «Targets: …» de cada card de ruleset | `RuleSetPicker.jsx:131-141` | **MÚLTIPLE** (`rs.targets_codis.map`) | **NO** — és text; el botó del costat és «Assignar» del *ruleset* (`:155-166`) |

**NO EXISTEIX cap tercer bloc de target al wizard d'item**, ni cap «assignació múltiple al final»:
el pas 2 és talla base + `MeasurementBaseGrid` (`ItemAuthoring.jsx:293-330`), sense targets.

> **L'aparença de duplicat, explicada:** T1 pregunta el target en singular a dalt; T2 el retorna en
> plural a baix, dins la card que l'usuari ha de clicar per continuar. Semànticament són coses
> diferents (T1 = filtre; T2 = propietat del ruleset), però la pantalla no ho diu enlloc: la
> segona sembla la confirmació —o la contradicció— de la primera.

**I hi ha 3 preguntes més del mateix tipus, no només el target.** `ItemAuthoring.jsx:256` passa
`maxLevel="group"`, així que la cascada demana **target → construcció → fit → grup**
(`CascadeSelector.jsx:106-172`). Els quatre eixos surten del catàleg de rulesets, no del catàleg
d'items: `availableTargetCodes` recorre `rs.targets_codis` (`gradingAxes.js:105-109`),
`availableConstructions` i `availableFits` filtren rulesets (`gradingAxes.js:112-125`).

### 4.2 (b) On es persisteix cada resposta — **el mapa és el buit**

| Resposta | Es persisteix a… | Prova |
|---|---|---|
| T1 (target «principal») | **ENLLOC** | `axes` és `useState` local (`ItemAuthoring.jsx:59`); els únics PATCH de la pàgina són `{grading_rule_set}` (`:133`), `{base_size_definition}` (`:152`) i `{name, active}` (`:167`). `GarmentTypeItem` **no té cap camp de target** (`tasks/models.py:296-333`) |
| T1 en reobrir | **es re-deriva del ruleset** | `ItemAuthoring.jsx:95-101`: `target: rsObj.targets_codis?.[0]`, i igual construcció/fit/grup. Si l'item no té ruleset, els 4 eixos neixen a `null` |
| T2 (targets múltiples) | `GradingRuleSet.targets` (M2M) | `pom/models.py:592-598`. S'edita a la pàgina de Grading Rules, no a l'item: `GradingRuleSets.jsx:691-716` (`TargetPills`, multi) i `:796-801` |
| `GarmentType.targets_recomanats` | **RETIRAT — no reviu** | Camp eliminat per `pom/migrations/0041_remove_garmenttype_targets_recomanats.py`; nota a `pom/models.py:413`; l'única vista consumidora està jubilada (`pom/s2_views.py:379`). Cercat a tot `backend/` i `frontend/src/`: **0 usos vius** |
| `SizingProfile` (target×família×construcció×fit) | **existeix, però l'item no hi entra** | `pom/models.py:938-948`: la clau és **`garment_type`** (família), **no `garment_type_item`**. Cap superfície del wizard d'item hi escriu |

> ⚠️ **`GradingRuleSets.jsx:801` encara envia `payload.target = tIds[0]`** — el FK legacy `target`
> es va RETIRAR a `pom/0043` (`pom/models.py:587-591`) i el serializer no el té
> (`pom/serializers.py:181-204`). DRF ignora el camp desconegut: és **inert**, però és una mentida
> al codi. *(Fora d'abast; s'anota.)*

### 4.3 (c) Qui consumeix cada resposta

| Resposta | Consumidors | Prova |
|---|---|---|
| **T1** | **NOMÉS el filtre del `RuleSetPicker` de la mateixa pantalla.** Res més: no viatja al servidor, no el llegeix cap altra pàgina | `ItemAuthoring.jsx:263` (`axes={axes}`) → `RuleSetPicker.jsx:30-50` |
| **T2** (`GradingRuleSet.targets`) | Matching d'eixos back i front: `gradingAxes.js:88-125`, `pom/grading_utils.py:558-575`; filtre de models `models_app/views.py:60`; pickers de model i de grading | — |
| Compatibilitat target↔**família** (el filtre del pas Peça, d'A1) | `SizingProfile` — **no** el target de l'item | `pom/views.py:121-132` (`?target=` → `SizingProfile.filter(target__codi=…).values('garment_type')`), consumit per `garmentCatalog.js:39-48` i per tant per `CascadeSelector` i per Garment Types |
| Size Library / `CustomerDetail` | `SizingProfile` per `customer_codi` | `s2_views.py:64-127`, `CustomerDetail.jsx:184` |

**Resposta directa a la pregunta del brief:** sí — **T1 no el llegeix ningú fora del picker que
volem fer opcional**. Amb el gate del GRS fora, T1 (i construcció, i fit, i grup) **es queden sense
cap consumidor**: són candidats a desaparèixer amb ell, no a sobreviure-hi.

### 4.4 (d) 💡 PROPOSTA (a validar) — una sola pregunta de target

> Va dins d'A5' com a tall (a'), i **només té sentit si el CTO vol que l'item conservi un àmbit
> d'aplicabilitat propi**. Si no el vol, l'opció més barata i més coherent amb la decisió Patró C
> és **no preguntar el target al wizard d'item en absolut** (l'àmbit ja el porta el ruleset, i el
> ruleset marxa de l'item).

Si es vol conservar-lo:

- **UNA pregunta**, al pas Context, amb semàntica «un o més»: pills multi-selecció, el **primer**
  triat fa de principal. Component ja existent i provat: `TargetPills` de
  `GradingRuleSets.jsx:691-716` (multi, vocabulari únic de `gradingAxes`).
- **Persistència:** avui **NO EXISTEIX** on posar-ho. Cal decidir entre:
  - **(i) M2M `GarmentTypeItem.targets`** — 1 migració AddField M2M + serializer + UI. És el mirall
    exacte de `GradingRuleSet.targets` i **expressa el cas Dona+Adolescent nena sense trampa**.
    ⚠️ Ressonància: `GarmentType.targets_recomanats` era exactament això i **es va jubilar el
    2026-07-19 per estar buit i no tenir consumidors** (`pom/models.py:413`). Reintroduir-lo un
    nivell més avall demana **un consumidor declarat abans de construir-lo**, o repetirem la
    història.
  - **(ii) `SizingProfile`** — NO serveix tal com està: la seva clau és `garment_type` (família),
    no l'item (`pom/models.py:938-948`), i cada fila **exigeix `size_system` i `grading_rule_set`
    NOT NULL** (`:946-949`), o sigui que declarar «aquest item aplica a Dona» obligaria a triar una
    graduació — **exactament el que la decisió Patró C treu de l'item**.
- **Eliminar la duplicació percebuda** sense tocar dades: fer que la card del picker deixi de
  semblar una segona pregunta (etiqueta explícita del tipus «aquest joc de regles cobreix: …»).
  Això és cosmètic i **independent** de tot l'anterior.

**Veredicte BLOC 4:** no hi ha duplicat de dades — **hi ha una pregunta fantasma**. El target de
l'item no existeix com a dada; és un filtre efímer del picker de rulesets. Quan el picker deixi de
ser obligatori, la pregunta es queda sense motiu.

---

## BLOC 5 — A5' · Talls proposats (dimensionats)

### 5.1 Tall (a) — GRS opcional/absent al wizard d'item + estat «sense graduació» legítim

**Mida: PETITA amb UNA decisió de disseny al mig.** Frontend només; **cap migració, cap canvi
d'API** (§1.3).

Peces mecàniques (petites):

| # | Canvi | `fitxer:línia` |
|---|---|---|
| a1 | Desacoblar la **creació** de l'item de l'assignació del ruleset: moure `garmentTypeItems.create` d'`assignRuleset` a `goNext` (o a un «Crear item» explícit) | `ItemAuthoring.jsx:122-146`, `:163-174` |
| a2 | `canNext` deixa de dependre del ruleset (passa a `!!name.trim()`) | `ItemAuthoring.jsx:161` |
| a3 | Permetre **desassignar**: acció «Sense graduació» que envie `{grading_rule_set: null}` (avui NO EXISTEIX cap camí de UI) | `ItemAuthoring.jsx:133` |
| a4 | El termòmetre de la card deixa de comptar «grading» com a mancança | `GarmentTypes.jsx:384-390` |
| a5 | i18n ca/en/es de les claus noves (el bloc `item_authoring` té 27 claus; no n'hi ha cap de «sense graduació») | `frontend/src/i18n/{ca,en,es}.json` |

**Precedent que ja existeix al producte:** el wizard de MODEL ja té «Sense graduació» explícit
(`ModelWizard.jsx:97`, `:681-686`, `:363`) i **no bloqueja mai** la creació del model
(`:753-762`: l'únic gate del footer és `block1Resolved` i `baseSizeInvalid`). El tall (a) fa que
l'item es comporti com el model. Avui la incoherència és flagrant: **el model, que SÍ que ha de
portar graduació, no l'exigeix; l'item, que segons la decisió NO n'ha de portar, sí.**

🚩 **La decisió de disseny (bandera CTO):** sense ruleset, el pas 2 no té `size_system` i per tant
**no es pot triar `base_size_definition`** (§2.5) — i aquesta és la talla en què s'expressen totes
les `ItemBaseMeasurement` (`pom/models.py:473`). Tres sortides:

1. **Item sense talla base** → les mides base de la plantilla queden **mudes** (no diuen a quina
   talla estan). Cost 0 avui, deute demà. *(És, de fet, l'estat de les 57 files de PROD.)*
2. **`GarmentTypeItem.size_system`** (FK propi, nullable) → 1 migració petita; el pas 2 llista
   talles del sistema de l'item i `clean()` passa a validar contra ell. **És la peça que fa
   autònom l'item**, i encaixa amb «el catàleg proposa».
3. **Deixar el ruleset com a atall OPCIONAL** només per a triar talla («d'on trec les talles?»),
   sense assignar-lo. Barat però manté viva la confusió que volem matar.

*(La 2 és la que deixa l'item complet sense graduació. Decisió humana.)*

### 5.2 Tall (b) — perfil `SWEATSHIRTS × WOMAN` (fix de dades a PROD)

**CONFIRMAT independentment en aquesta diagnosi.** El mecanisme: `pom/views.py:121-132` filtra les
famílies per `SizingProfile.target`; `garmentCatalog.js:39-48` és qui hi crida; el consumeixen el
pas Peça del wizard de model (`ModelWizard.jsx:556-563`) **i** el pas Context del wizard d'item
(nivell «grup»).

Cens (staging, `psql -p 5433 ftt_staging`, i PROD via dump):

| Entorn | `SizingProfile` totals | Famílies cobertes | `SWEATSHIRTS_MIDLAYERS` |
|---|---|---|---|
| **staging** | 45 | 10 | `BOY, GIRL, TODDLER_BOY, TODDLER_GIRL` — **sense WOMAN ni MAN** |
| **PROD** | **33** | **8** (`BABY_ONEPIECES, BUTTONED_TOPS, DRESS, DRESSES, JERSEY_TOPS, TAILORED_PANTS, T_SHIRT` + …) | **CAP PERFIL** → la família **no apareix mai**, amb cap target |

**Mida: PETITA en volum, MITJANA en camí.** ⚠️ **NO EXISTEIX endpoint de creació de
`SizingProfile`**: les rutes viuen a `tasks/urls.py:165-167,194-196` i només exposen GET llista
(`s2_views.py:64`, `@api_view(['GET'])`), GET detall (`:133`), clonar (`:162`) i restaurar
(`s4_views.py`). Els únics creadors són l'import de size-map
(`size_map_views.py:1004`) i comandes de seed (`seed_baby_months_profiles.py:76`,
`seed_losan_master_delta.py:189`, `seed_losan_grading_v3.py:199`). Vies possibles:

- **management command idempotent** (el patró de la casa: `get_or_create`), corregut a PROD;
- o data-migration.

🚩 **Bandera d'arquitectura:** `SizingProfile` exigeix `size_system` **i** `grading_rule_set` NOT
NULL (`pom/models.py:946-949`). O sigui: **avui, per fer visible una família per a un target, cal
inventar-li una graduació.** Això contradiu frontalment la decisió Patró C (l'àmbit del catàleg no
hauria de dependre de la graduació). El fix de dades desbloqueja avui; la contradicció queda oberta.

### 5.3 Tall (c) — construcció/fit al filtre del pas Peça del wizard de MODEL

**Estat actual** (`ModelWizard.jsx`, bloc 2): l'ordre és **target → PEÇA → construcció**
(`:556-563` el `CascadeSelector` rep NOMÉS `target={target}`; `:570-579` les chips de construcció
es pinten **després**). El **fit** no es tria fins al bloc 4 (`:696-712`), per la LLEI 5 CAPES
(«el pas Talles és escala pura», `:106-108`).

Les dues opcions, dimensionades:

| Opció | Què | Cost |
|---|---|---|
| **(c1) Filtrar de veritat** | Moure construcció **abans** de la peça i passar-la al filtre. Requereix ampliar el backend: `GarmentTypeViewSet.get_queryset` avui **només** entén `?target` (`pom/views.py:121-132`); cal afegir-hi `?construction` → `SizingProfile.filter(construction__codi=…)` | **PETITA** (≈6 línies de backend + reordenar 2 blocs de UI) — però **hereta el problema de (b)**: com més eixos, més buida queda la llista amb 33 perfils. Amb les dades d'avui, filtrar per construcció deixaria el pas Peça pràcticament buit |
| **(c2) No filtrar: informar** | Deixar l'ordre com està i marcar les peces incompatibles en comptes d'amagar-les | **MOLT PETITA**, i és la doctrina ja escrita al repo: *«les eines del tècnic s'ofereixen senceres i s'acoten amb informació, no amb ocultació»* (`ModelWizard.jsx:614-616`, F1.4, arran del model 174) |

💡 **PROPOSTA (a validar):** (c2) ara, (c1) **només després** de sanejar `SizingProfile` (b). Fer
(c1) primer amb 33 perfils és construir un filtre que amaga més del que troba — la mateixa forma
del bug que ha portat l'Agus fins aquí.

### 5.4 Tall (d) — retirada de `GarmentTypeItem.grading_rule_set`

**Viable, i el cens el permet** (§2). Estil G6 (deixar d'escriure → retirar després), en 3 onades:

| Onada | Què | Peces | Mida |
|---|---|---|---|
| **D1 — deixar d'escriure** | És el tall (a). L'únic escriptor de producte és `ItemAuthoring.jsx:133` | + `bootstrap_tenant` ja tolera NULL (`:300-312`) | PETITA |
| **D2 — deixar de llegir** | R1: substituir `item.grading_rule_set.size_system_id` per la font que decideixi (a) — si és `GarmentTypeItem.size_system`, és un canvi d'una línia i el test `tests_sembra_grading.py:877-891` ja cobreix el camí NULL. R2: decidir si el suggeriment del wizard de model mor o canvia de font (§5.5) | `models_app/views.py:2928`; `ModelWizard.jsx:289-296,733`; `RuleSetPicker.jsx:16-18,35-37,88,123-125`; `gradingAxes.js:185-190` + el seu test `gradingAxes.test.js` | PETITA-MITJANA |
| **D3 — retirar** | `RemoveField` + netejar `clean()` (`tasks/models.py:341-353`), serializer (`serializers_b.py:104,117-121`), `select_related` (`views_b.py:858`), termòmetre (`GarmentTypes.jsx:384,407`), rehidratació d'eixos (`ItemAuthoring.jsx:95-101`) i fixtures de 4 tests | 1 migració `tasks/00XX` | PETITA |

⚠️ **Guarda abans de D3:** `pom/models.py:566-568` diu que aquest pointer i
`GradingRuleSet.garment_type_item` (identitat del CONTENIDOR de client) «es reconcilien al
backfill». **Aquest backfill NO EXISTEIX** com a migració. Abans de retirar el camp cal confirmar
que ningú l'usa com a **mirall** del contenidor — a staging hi ha **4 items amb ruleset** (ids
4, 5, 10, 58) i cal saber si algun és mirall d'un contenidor de client (rs 115 és el del contenidor
CLIENT_RUN de l'S10 Brownie). A PROD la pregunta no existeix: **0 files**.

### 5.5 💡 On viu el suggeriment després del tall (a)

La decisió Patró C diu que el suggeriment ha de viure al `SizingProfile` (preset per
target×construcció×fit). Estat del codi:

- `SizingProfile` **ja** porta `grading_rule_set` NOT NULL (`pom/models.py:948`) i **ja** s'exposa
  per `GET /api/v1/sizing-profiles/?target&construction&fit&garment_type` amb prioritat de client
  (`s2_views.py:64-127`). **La font existeix i està servida.**
- El wizard de model **ja** llegeix `SizingProfile` al pas Talles (`ModelWizard.jsx:109-118`,
  `sizingResult`), però **només n'agafa l'escala** (sistema/run/base) per la LLEI 5 CAPES; el
  `grading_rule_set` del perfil **es descarta a posta** (`:106-108`).
- Per tant, el tall «el suggeriment ve del perfil» = **canviar la font de `suggestedId`**
  (`ModelWizard.jsx:733`) de `garmentTypeItems.get(item.id).grading_rule_set` a
  `sizing-profiles/?target&construction&fit&garment_type` → `.grading_rule_set`. **Cap camp nou,
  cap migració.** Mida: PETITA. ⚠️ Depèn del mateix cens de perfils que (b): amb 33 files a PROD,
  el suggeriment serà buit gairebé sempre fins que (b) es faci.

---

## Taula final per al CTO

| # | Fet / risc | On | Impacte | Bloqueja avui? |
|---|---|---|---|---|
| 1 | El gate del GRS és **una línia de React**; el backend no obliga a res i mai s'ha endurit a BD | `ItemAuthoring.jsx:161`; `tasks/models.py:329-331` | Treure'l no costa migració | — |
| 2 | **Sense ruleset no es pot ni CREAR l'item** (la creació viu dins `assignRuleset`) | `ItemAuthoring.jsx:122-136` | El tall (a) ha de moure la creació, no només relaxar `canNext` | **SÍ** |
| 3 | **No hi ha camí de UI per desassignar** un ruleset d'un item | `ItemAuthoring.jsx:133` | El dany de PROD s'ha de desfer per SQL | **SÍ** |
| 4 | Només **2 lectors reals** del camp, **cap bloquejant amb NULL** (un ja té test del camí NULL) | `models_app/views.py:2926-2941`; `ModelWizard.jsx:289-296` | Passar a opcional és segur avui | — |
| 5 | Dany a PROD **confinat**: 1 fila de catàleg, **0 models** apunten a l'item 16, **0 cascades** | backup 2026-07-23 02:30 | Reversió = `UPDATE … SET NULL` | — |
| 6 | El **target de l'item no es persisteix enlloc**: és un filtre efímer del picker | `ItemAuthoring.jsx:59,95-101` | El "duplicat" és una pregunta fantasma, no dues dades | — |
| 7 | Amb el GRS fora, **4 eixos** (target/construcció/fit/grup) es queden sense consumidor | `CascadeSelector.jsx:106-172`; `gradingAxes.js:105-125` | El tall (a) és també un tall d'UI, no només d'una FK | — |
| 8 | 🚩 Sense ruleset, l'item **no té d'on treure el `size_system`** → no pot fixar la talla base de les seves mides | `ItemAuthoring.jsx:108-119`; `pom/models.py:473` | **Decisió humana** entre 3 sortides (§5.1) | **SÍ** (de disseny) |
| 9 | 🚩 `SizingProfile` exigeix `grading_rule_set` NOT NULL → **declarar un àmbit de catàleg obliga a inventar una graduació** | `pom/models.py:946-949` | Contradiu la decisió Patró C | — |
| 10 | PROD té **33 perfils / 8 famílies**; `SWEATSHIRTS_MIDLAYERS` **cap** → la dessuadora no surt al pas Peça amb cap target | `pom/views.py:121-132` | És el bloqueig funcional d'avui | **SÍ** |
| 11 | **NO EXISTEIX endpoint de creació de `SizingProfile`** (només llistar/clonar/restaurar) | `pom/s2_views.py:64-230` | El fix (b) va per comanda o data-migration | — |
| 12 | El **model** no exigeix graduació però **l'item** sí — incoherència de paradigma | `ModelWizard.jsx:681-686,753-762` vs `ItemAuthoring.jsx:161` | Argument de fons per al tall (a) | — |
| 13 | El suggeriment pot canviar de font a `SizingProfile` **sense cap camp nou** | `s2_views.py:64-127`; `ModelWizard.jsx:733` | Fa viable el tall (d) | — |
| 14 | ⚠️ El «backfill que reconcilia» item↔contenidor **NO EXISTEIX** | `pom/models.py:566-568` | Guarda abans de D3; a PROD la pregunta és nul·la (0 files) | — |
| 15 | *(Anotat, fora d'abast)* `GradingRuleSets.jsx:801` envia `payload.target`, FK retirat a `pom/0043`: inert però mentider | `GradingRuleSets.jsx:796-801` | Higiene | — |

---

## Resposta a la pregunta d'urgència

> *«(a) i (b) desbloquegen treball real d'avui — si són petits, digues-ho per autoritzar Patró B
> immediat.»*

- **(b) és PETIT i independent: es pot fer ja.** És un fix de dades (comanda idempotent
  `get_or_create` de `SizingProfile`) + córrer-la. Cap canvi de contracte. ⚠️ Cal decidir **quin
  `size_system` i quin `grading_rule_set`** porta el perfil nou, perquè el model els exigeix
  (risc 9). Amb això, la dessuadora torna a ser visible al pas Peça.
- **(a) és PETIT en codi (5 peces, tot frontend, cap migració) però porta UNA decisió humana al
  mig** (risc 8: d'on surt la talla base d'un item sense graduació). Amb la sortida 1 («item sense
  talla base», que és l'estat real de les 57 files de PROD) el tall és immediat i totalment
  frontend. Amb la sortida 2 s'hi afegeix una migració petita.
- **La reversió del dany (A4') es pot fer abans que res**, és independent de tot, i **no es pot fer
  per UI** (risc 3).

*Fi de la diagnosi. Cap fitxer de codi tocat; cap comanda d'escriptura executada.*
