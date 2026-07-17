# DIAGNOSI — Wizard complet · Arbre de taxonomia consistent · Compatibilitat de models existents

Data: **2026-07-17** · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`, tenant `fhort`.
Abast: preparar el sprint WIZARD-COMPLET (pas 4 Graduació) + arbre únic Grup→Família→Item + backfill/watchpoints de compatibilitat previ al DEPLOY.

> Convenció: `fitxer:línia` = fet verificat al codi. `"NO EXISTEIX"` = confirmat absent (no especulat).
> Les propostes de disseny van marcades `💡 PROPOSTA (a validar)`; les decisions són humanes (Patró C).

---

## Resum executiu (les conclusions que desbloquegen la decisió)

1. **El Model ja té el contracte complet de taxonomia/graduació** (`models_app/models.py:145-199`): `garment_type`, `garment_group`, `garment_type_item`, `fit_type` (default `Regular`, mai NULL), `target`, `construction`, `size_system` i un **FK DIRECTE** `grading_rule_set`. Tots nullables llevat `fit_type`. No cal cap camp nou → **Fase B/C/D són additives, sense migració de model**.
2. **El wizard té 3 blocs hardcoded** (Identificació · Peça · Talles) a `ModelWizard.jsx`; **NO existeix pas 4 de graduació**. La graduació es tria avui a `RuleSetCard` dins `ModelSheet` amb **un sol clic sense confirmació** (`RuleSetCard.jsx:41-48`), que re-materialitza regles residents. Aquest és l'únic re-materialitzador de model de la UI.
3. **Els components de graduació ja existeixen i són reutilitzables**: `AxesSelector` + `RuleSetPicker` (`components/grading/`). El backend `update-step2` ja fa wipe-and-recreate de les regles residents (`views.py:592-620` → `services.py:147-168`). El pas 4 del wizard **només ha d'afegir `grading_rule_set_id` al payload**; la resta ja hi és.
4. **El matching de rulesets és LENIENT** (NULL = comodí) i **ignora `size_system`** (`gradingAxes.js:103-112`). El wizard demana filtrat **ESTRICTE** → cal un matcher estricte nou al context del wizard, deixant el lenient a les superfícies de gestió.
5. **CENS viu (43 models)**: només dos camps minusinformats — `garment_group` **35/43 NULL** i `grading_rule_set` **34/43 NULL**. Tota la resta plena. **`garment_group` és 100% DERIVABLE** (denormalització que el wizard ja calcula); **`grading_rule_set` NO és derivable de forma segura** (els punters Model↔Item estan desacoblats a posta; assignar-lo materialitzaria regles = inventar graduació → prohibit per D.1(b)).
6. **El «6 vs 7» són QUATRE taxonomies de grup independents, cap sincronitzada** (§BLOC 3). La font de veritat ha de ser el model `GarmentGroup` (endpoint `garment-groups`); les llistes hardcoded del frontend són el desajust.

---

## BLOC 1 — Contracte del Model (A.2)

Classe `Model` a `models_app/models.py:75`. Camps de taxonomia/graduació:

| Camp | Tipus | fitxer:línia | Nullabilitat |
|---|---|---|---|
| `garment_type` | FK→`pom.GarmentType` SET_NULL | :146-152 | null/blank |
| `garment_group` | FK→`pom.GarmentGroup` SET_NULL | :153-159 | null/blank |
| `garment_type_item` | FK→`tasks.GarmentTypeItem` SET_NULL | :161-167 | null/blank |
| `fit_type` | CharField(20) FIT_CHOICES | :183 | **default `Regular`, MAI NULL** |
| `target` | CharField(30) | :184 | null/blank |
| `construction` | CharField(20) | :185 | null/blank |
| `size_system` | FK→`pom.SizeSystem` SET_NULL | :186-192 | null/blank |
| `grading_rule_set` | FK→`pom.GradingRuleSet` SET_NULL | :193-199 | null/blank |

**Dos punters de graduació independents**: `Model.grading_rule_set` (:193) i `GarmentTypeItem.grading_rule_set` (`tasks/models.py:319`, PROTECT). `_resolve_garment_def` **NO copia** l'un a l'altre (`views.py:418-420`) — desacoblats a posta.

**Materialització de regles residents**: classe `ModelGradingRule` (`models_app/models.py:691`, ancora `model` FK :708). Servei `materialize_model_grading_rules(model, source_rules, origen)` (`services.py:147-168`) = **wipe-and-recreate idempotent** (`origen` ∈ IMPORTED/CANONICAL/MANUAL). El motor `generate_graded_specs` **NO es toca**.

### Matriu camí-de-creació × camps que queden buits

| Camí | Escriu | Deixa BUIT |
|---|---|---|
| **Wizard** (`create_model_wizard` `views.py:436`; `_resolve_garment_def` :387) | `garment_type_item` (obligatori :468), `garment_type` derivat (:403), **`garment_group` derivat** via `GarmentGroup.filter(codi=item.garment_type.grup)` (:404-406), opcionals del payload (size_system, grs, target, construction, base) | `fit_type` (→ `Regular`); grs/target/construction si no venen |
| **Import Excel** (`bulk_import_service._build_model` :563-583) | garment_type, garment_type_item, target, construction, size_system, size_run, base_size | **`garment_group` (NULL!)**, **`grading_rule_set`**, `fit_type` |
| **Clone QA** (`clone_model_for_qa.py`) | còpia per valor de tots els camps | — |

→ **Els 35 `garment_group` NULL vénen de l'import** (el wizard sí el deriva; l'import no). **Divergència de camins** (TROBALLA TRANSVERSAL): la denormalització no està sincronitzada.

**Veredicte BLOC 1:** contracte complet, cap camp nou necessari. `garment_group` derivable (pur); `grading_rule_set` NO derivable segur; `fit_type` sempre poblat.

---

## BLOC 2 — Wizard i re-materialització (A.3)

- **Estructura**: `ModelWizard.jsx` — 3 blocs per `block === n` (`useState` :37; `BLOCKS` :209; b1 Identificació :248, b2 Peça :286, b3 Talles :331; nav `Math.min(3,b+1)` :417). **Sense pas 4.** Mode edició/creació: `isEditMode = !!id` (:33); `handleSaveEdit` :196-207 crida `updateStep2` (:202) amb `skeletonPayload()` que **no inclou** grs (:164-173).
- **Pas Talles (pur)**: `selSystem` :59, `selectedSizes` :61, `baseSize` :62; `sizingResult` :72-79; `skeletonPayload` :164-173.
- **Components reutilitzables**: `AxesSelector.jsx` (props `{ruleSets,value,onChange}`, `value={target,construction,fit,garmentGroup}`) + `RuleSetPicker.jsx` (props `{ruleSets,garmentGroupCodiById,axes,onPick,actionLabel,selectedId,...}`; gate `ready` = 4 eixos plens :29). El pare carrega **tots** els rulesets (`gradingRuleSets.list({page_size:200})`) i **el matching és 100% client-side**.
- **Matching** (`gradingAxes.js:62-112`): **LENIENT** — `targets_codis` buit, `construction_codi`/`fit_type_codi`/`garment_group` NULL casen com a **comodí**. **`size_system` NO és eix del matching.** Backend `GradingRuleSetViewSet` filterset = `['actiu','garment_group','size_system','customer']` (`pom/views.py:164`) — no exposa target/construction/fit.
- **Re-materialització**: `update_model_step2` (`views.py:592-620`) → si `grading_rule_set_id` → `materialize_model_grading_rules(..., 'CANONICAL')`. Mateix servei a creació (`views.py:536-541`).

### A.3 — Punts UI que canvien `grading_rule_set` amb re-materialització
1. **RuleSetCard** (PRINCIPAL) — `RuleSetCard.jsx:41-48` (`onPick`) → `models.updateStep2(id,{grading_rule_set_id})` (`endpoints.js:42`), muntat a `ModelSheet.jsx:451`. **1-CLIC, sense confirmació.** → Fase C el converteix en LECTURA.
2. **ItemAuthoring** — `ItemAuthoring.jsx:122-146` assigna ruleset a l'**Item** (catàleg), no al model. No és re-materialitzador de model. (Comparteix `RuleSetPicker`.)
3. **Extracció/import W5** — `extraction_views.py:1881-1962` (flux, no botó).

**Veredicte BLOC 2:** pas 4 = reutilitzar `AxesSelector`+`RuleSetPicker` + matcher estricte + afegir `grading_rule_set_id` al payload. Re-materialització ja soportada al backend. `RuleSetCard` → lectura.

---

## BLOC 3 — Arbre de grup: QUATRE taxonomies (A.1 / C.2)

`GarmentGroup` (`pom/models.py:375`, `codi` unique) = nivell **Grup**, però `verbose_name`="Família de garment" (:385, invertit). `GarmentType.grup` (`pom/models.py:404`) = **CharField lliure, sense FK** a GarmentGroup.

| Font | fitxer:línia | Nº | Naturalesa |
|---|---|---|---|
| **A. Model `GarmentGroup`** (autoritat BD) | endpoint `garment-groups`, `pom/views.py:134` | **11 live** (seed JSON=6 → DRIFT) | dades reals |
| **B. Frontend grading `GARMENT_GROUPS`** | `gradingAxes.js:46-54` | **7** hardcoded | +ACCESSORIES |
| **C. Frontend selector peça `GRUPS`** | `GarmentTypeSelector.jsx:11-18` | **6** hardcoded | ACCESSORIES exclòs |
| **D. `GarmentType.grup` distinct** | derivat `GarmentTypes.jsx:124` | **6** en ús | string lliure |

**El «6 vs 7»**: el 7 és exclusivament la constant B (afegeix ACCESSORIES); els 6 són C/D (codis plans). Cap consumeix el model A de forma consistent.

**Cens viu (autoritat, staging)**: 11 `GarmentGroup` actius, però ús real:
- Amb rulesets: **TOPS=2, BOTTOMS=1**; resta 0 (**23/26 rulesets tenen `garment_group=NULL`** — els customer/contenidor casen per `garment_type_item`).
- Amb famílies (`grup`): TOPS=7, DRESSES=4, BOTTOMS=3, OUTERWEAR=2, UNDERWEAR=2, SWIMWEAR=1. **Buits**: ACCESSORIES, DRESSES-FULL, KNITWEAR, TOPS-KNIT, TOPS-WOVEN.
- **Tots els `GarmentType.grup` casen amb un `GarmentGroup.codi`** (0 orphans) → backfill de `garment_group` segur 35/35.

**Consumidors addicionals**: `GradingRuleSetSerializer` **no exposa `garment_group_codi`** (només `_nom`, `serializers.py:182`) → el front construeix el map id→codi a mà. `backfill_model_items.py:91` uneix `grup`→`codi` (perd els que no casen amb els codis de grading del seed). `GarmentTypes.jsx` és una **llista plana** (sense arbre de grup), grup editable com a `<input>` text lliure (:332).

**Veredicte BLOC 3:** font única = model `GarmentGroup` (endpoint). El frontend ha de deixar d'hardcodejar (B i C). Cal exposar `garment_group_codi` al serializer. Podar els grups buits / resoldre el drift seed↔live = **decisió de DADES d'Agus** (no codi). `GarmentTypes` necessita selector de grup (C.1).

---

## BLOC 4 — Compatibilitat: cens i política de backfill (A.2 quantitatiu / D.1)

**Cens viu (43 models, tenant fhort, 2026-07-17):**

| Camp | NULL/buit | Política |
|---|---|---|
| garment_type | 0/43 | — |
| garment_type_item | 0/43 | — |
| size_system | 0/43 | — |
| target / construction | 0/43 | — |
| fit_type | 0/43 (tots `Regular`) | — (mai NULL) |
| **garment_group** | **35/43** | **(a) DERIVABLE** — 35/35 via `garment_type.grup`→`GarmentGroup.codi`. Backfill idempotent. |
| **grading_rule_set** | **34/43** | **(b) NO DERIVABLE** — punters desacoblats; assignar = materialitzar regles = inventar. Tolerar buit (`sense graduació` és estat vàlid) + **watchpoint**. |

**Watchpoint (D.2)**: model `Watchpoint` (`models_app/models.py:925`). Convenció de **watchpoint de SISTEMA**: `dades` JSONField **no-null** + `task IS NULL` + `created_by NULL` (`models.py:938`). Precedent idempotent existent: l'import viu (`signals.py:143`, `services.model_config_missing:106`) — filtra `task__isnull=True, dades__isnull=False, estat='open'` i actualitza/resol. `model_config_missing` **ja tracta `grading_rule_set` com a config requerida**. `flag_incomplete_models` ha de mirar aquest patró: watchpoint = flag humà/persistent, **no** alerta computada de tolerància.

**💡 PROPOSTA (a validar) — política de backfill:**
- `backfill_model_taxonomy` (idempotent, `--dry-run` obligatori): omple **NOMÉS `garment_group`** derivat (mirall de `views.py:404-406`). **NO toca `grading_rule_set`** (no derivable segur).
- `flag_incomplete_models` (idempotent): crea watchpoint de SISTEMA OBERT als models amb camps no-derivables buits (grading_rule_set NULL i, si es decideix, altres), text estàndard datat; no duplica si ja n'hi ha un d'obert del mateix tipus; tancable en completar.

**Veredicte BLOC 4:** una comanda de backfill segura (garment_group) + una de watchpoints (grading pendent). Cap escriptura inventada.

---

## TAULA FINAL — EXISTEIX / FALTA / DIFERENT (per al CTO)

| Element | Estat | Nota |
|---|---|---|
| Camps de taxonomia/graduació al Model | **EXISTEIX** | tots, `grading_rule_set` FK directe. Cap migració de model. |
| Pas 4 «Graduació» al wizard | **FALTA** | reutilitzar AxesSelector+RuleSetPicker. |
| Matcher estricte (size_system + no comodí NULL) | **FALTA** | el lenient existent es queda a CRUD. |
| Re-materialització backend | **EXISTEIX** | `update-step2` wipe&recreate. Cap canvi. |
| RuleSetCard 1-clic re-materialitzador | **DIFERENT** | passa a LECTURA (Fase C). |
| Font única de grups | **FALTA** | 4 taxonomies; unificar al model `GarmentGroup`. |
| `garment_group_codi` al serializer | **FALTA** | el front el construeix a mà. |
| Selector de grup a GarmentTypes | **FALTA** | llista plana avui. |
| `garment_group` als models existents | **DERIVABLE** | 35/35, backfill segur. |
| `grading_rule_set` als models existents | **NO DERIVABLE** | 20 sense grading real; tolerar + watchpoint. |
| Tolerància de pantalles a NULL | **A VERIFICAR** | D.3 script sobre tots els models. |
| Motor `generate_graded_specs` | **INTOCAT** | zona intocable respectada. |
