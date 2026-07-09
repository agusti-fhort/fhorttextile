# DIAGNOSI — Seam catàleg: SizeSystem ↔ GradingRuleSet ↔ GarmentTypeItem + motor d'import + inventari d'escriptura al Model

> **Tipus:** diagnosi READ-ONLY (Patró A). Cap canvi de codi, cap migració, cap commit, cap restart.
> `git status` net. DB només SELECT (PG18:5433, `ftt_staging`, schema `fhort`).
> **Mètode:** director + 6 investigadors paral·lels (A–F), citacions `fitxer:línia` verificades.
> **Convenció:** **FET** = comprovat al codi/BD · **💡 PROPOSTA** = a validar (Patró C posterior; aquí NO es decideix arquitectura).
> **Objectiu:** mapar el seam per dissenyar SENSE DUPLICATS l'ancoratge dels valors base per Item.

---

## 0. Resum executiu — les 5 tesis

| # | Tesi | Veredicte | Evidència nucli |
|---|------|-----------|-----------------|
| **T1** | Item = base de patronatge sobirana amb UN sol context de grading | **REFUTADA (avui)** · MATISADA com a intenció | `GarmentTypeItem` NO té FK a `GradingRuleSet`; el grading es tria a nivell de **Model**, no d'Item. [tasks/models.py:347-366], [models_app/views.py create_model_wizard] |
| **T2** | SizeSystem = run pur, target-agnòstic | **MATISADA** | És un run ordenat pur SENSE construcció/fit, però **SÍ porta `targets` M2M** (audiència). [pom/models.py:272-318, 281] |
| **T3** | target/fit/construcció viuen al GradingRuleSet, NO al SizeSystem | **CONFIRMADA** (amb matís d'audiència) | `construction` i `fit_type` són FK NOMÉS a `GradingRuleSet`; el `target` audiència és compartit als dos. [pom/models.py:478-487] |
| **T4** | Els valors base han de penjar de l'Item amb clau (item, pom) — no del Model ni de GarmentPOMMap | **CONFIRMADA (estructuralment viable)** | `GarmentPOMMap` és pertinença pura (sense valor); `BaseMeasurement` penja del **Model**; una `ItemBaseMeasurement(item,pom)` aterra net com a germà de `GarmentPOMMap`. [pom/models.py:414-446], [models_app/models.py:478-532] |
| **T5** | L'ancoratge de l'Item deixa lloc GERMÀ net per a la geometria (DXF) futura | **CONFIRMADA** | Zero entitats `Pattern*`, zero `ezdxf`/`shapely`; el "DXF base" és blob mort (`ModelFitxer.categoria='Patro'`). L'Item és punt d'ancoratge net per a un futur `PatternBase`. [models_app/models.py:328-334] |

**Lectura de fons:** el catàleg actual modela **run** (SizeSystem) i **grading** (GradingRuleSet/GradingRule) amb riquesa, però **l'Item (GarmentTypeItem) és prim** — només pertinença de POM (GarmentPOMMap) + matriu de temps (TaskTimeEstimate). NO és avui un context de grading ni porta valors base. El disseny posterior (Patró C) ha de decidir si l'Item PASSA a ser aquest context. La diagnosi confirma que hi ha **lloc net** per fer-ho sense duplicar ni trencar FK.

---

## A · SizeSystem — run pur o contaminat?

**FET — camps de `SizeSystem`** ([pom/models.py:272-318](../backend/fhort/pom/models.py#L272)):
- `codi` (unique, 273) · `nom` (274) · `descripcio` (275) · `actiu` (276)
- **`targets`** M2M → `Target` (281-284) — *"target FK migrat a M2M (harmonitza amb GradingRuleSet.targets)"*
- `base_unit` enum (285-296): ALPHA / NUMERIC_EU / NUMERIC_US / CM_HEIGHT / MONTHS / AGE_YEARS
- `norma_ref` (297) · `parent` FK→self (302, derivació per client) · `customer_codi` (308)

**FET — el RUN ordenat** viu a `SizeDefinition` ([pom/models.py:321-349](../backend/fhort/pom/models.py#L321)): `size_system` FK (322) · `etiqueta` (323, p.ex. "M","40","3M") · **`ordre`** (324, ordinal del run) · `valor_numeric` (325) · referències corporals `body_height/bust/waist/hip_cm` (330-339) · `age_months_min/max` (340-342). `Meta.ordering=['size_system','ordre']` (348), `unique_together(size_system, etiqueta)` (349). **NO hi ha flag de talla base** a `SizeDefinition` — la base es declara al grading (vegeu B).

**FET — NO porta construcció ni fit.** `SizeSystem` i `SizeDefinition` no tenen cap camp `construction`/`fit_type`. Sí porta `targets` (audiència).

**FET — comptatge BD (schema fhort, SELECT):** `SizeSystem` = **19** files; `SizeDefinition` = **111** files. No hi ha multiplicació teixit×fit a nivell de SizeSystem (cada run guardat un cop). *(Detecció: els 19 codis són runs diferents — ALPHA_EU_W, NUMERIC_EU_W, BABY_MONTHS, KIDS_EU, GIRL_LOS_01..03, etc.; la multiplicació teixit/fit que es veu a la Size Library viu al grading, no aquí.)*

**FET — els "POM ±cm" de la UI de talles NO surten del SizeSystem.** Vénen de `GradingRule.increment` / `valor_base` (vegeu B), servits per `/api/v1/grading-rule-sets/` ([frontend/src/api/endpoints.js gradingRuleSets.list]). El `/api/v1/size-systems/` retorna NOMÉS run + talles. → cap grading colat dins el run.

**Veredicte T2 — MATISADA.** Run ordenat pur, sense construcció/fit, però **NO 100% target-agnòstic**: porta `targets` M2M (audiència). El run "és per a dona/home/baby" és part de la seva identitat; el que NO porta és construcció ni fit (això és grading).

---

## B · GradingRuleSet — identitat, talla base, vincle a SizeSystem

**FET — camps de `GradingRuleSet`** ([pom/models.py:448-499](../backend/fhort/pom/models.py#L448)):
- `nom` (449) · `garment_group` FK (450) · **`size_system`** FK→SizeSystem PROTECT, null=True (457)
- **`target`** FK legacy (466) + **`targets`** M2M autoritatiu (471-477) — *"un RuleSet pot aplicar a múltiples targets"*
- **`construction`** FK→ConstructionType (478-482) · **`fit_type`** FK→FitType (483-487)
- `is_system_default` (488) · `parent_version` FK→self (490, versionat) · `version_number` (496) · `codi_sistema` (497, p.ex. `EU_WOVEN_WOMAN_REGULAR`)
- **`Meta`** (501-503): **cap `unique_together`** — la identitat (target+construcció+fit+sistema) NO té clau natural única forçada; es desambigua per `nom`/`codi_sistema`/versió. *(inferit: la unicitat és convencional, no de BD.)*

**FET — talla base = per-REGLA, no per-set.** `GradingRule.talla_base` FK→`SizeDefinition` PROTECT **NOT NULL** ([pom/models.py:525](../backend/fhort/pom/models.py#L525)). NO existeix un camp de talla base únic al `GradingRuleSet`; cada `GradingRule` la repeteix. *(inferit: totes les regles d'un set solen compartir `talla_base`, però el model no ho imposa.)*

**FET — vincle a SizeSystem = FK directe** (1→N), `GradingRuleSet.size_system` (457), opcional.

**FET — `valor_base` és camp REAL, no UI-only.** `GradingRule.valor_base` DecimalField(7,2) default=0 ([pom/models.py:528](../backend/fhort/pom/models.py#L528)); serialitzat a `GradingRuleSerializer`; la UI el pinta buit ("—") quan `valor_base ≤ 0` (render condicional `Number(r.valor_base) > 0 ? ... : '—'` a `GradingRuleSets.jsx`). → **la columna BUIDA és valors a 0, no un camp inexistent.**

**FET — entitat de regla per POM** `GradingRule` ([pom/models.py:509-545](../backend/fhort/pom/models.py#L509)): `rule_set` FK (523) · `pom` FK→POMMaster (524) · `talla_base` FK (525) · `logica` enum LINEAR/STEP/FIXED/ZERO/EXCEPTION (515-526) · `valor_base` (528) · `increment` (529) · `valors_step` JSON (530) · forma canònica Peça A: `increment_base` (533) + `increment_break` (534) + `talla_break_label` (535) + `talla_break_pos` (536) · `actiu` (537). `unique_together(rule_set, pom)` (542).

**Veredicte T3 — CONFIRMADA.** `construction` i `fit_type` són FK NOMÉS al `GradingRuleSet` (478-487); SizeSystem no els té. Matís: el `target` (audiència) viu als DOS (run i grading) — el que distingeix grading de run és **construcció + fit + valors/increments**, no l'audiència.

---

## C · GarmentTypeItem ↔ GradingRuleSet — el lligam clau (pregunta central)

**FET — camps de `GarmentTypeItem`** ([tasks/models.py:347-366](../backend/fhort/tasks/models.py#L347)): `garment_type` FK→pom.GarmentType (351) · `code` slug (353) · `name` (354) · `complexity_order` (355) · `active` (357). **CAP FK a `GradingRuleSet`.** (Ni a `GarmentType`, [pom/models.py:372-411].)

**FET — el grading es resol a nivell de MODEL, no d'Item.** A `create_model_wizard` ([models_app/views.py ~223-371]): `grading_rule_set_id` ve **del payload del wizard** (tria explícita de l'usuari), NO derivat de l'Item. L'Item (`garment_type_item`) i el ruleset es desen com a camps **independents** del `Model`. Guarda: si hi ha `base_size` sense `grading_rule_set_id` → 400.

**FET — `materialize_model_grading_rules`** ([models_app/services.py ~67-88], *citació de la investigació*): còpia `rule_set.regles.all()` → taula resident **`ModelGradingRule`** (tenant), wipe-and-recreate, `origen='CANONICAL'`. Disparat a la creació del model si `grading_rule_set_id` (i a l'update step2, i a l'import confirmar).

**FET — FK vives cap a `GarmentTypeItem`** (l'Item ja és àncora de plantilla): `Model.garment_type_item` ([models_app/models.py:161-167]) · `GarmentPOMMap.garment_type_item` (db_constraint=False, [pom/models.py:421-423]) · `TaskTimeEstimate.garment_type_item` ([tasks/models.py:373]) · `ImportSession.tipologia_confirmada` ([models_app/models.py:409-410]).

**Veredicte T1 — REFUTADA (estat actual) / MATISADA (com a intenció).** Avui l'Item NO és un context de grading: és node de complexitat per a temps (TaskTimeEstimate) + pertinença de POM (GarmentPOMMap). El grading és **tria de Model** (1 Item → N Models amb rulesets possiblement diferents). Per fer T1 certa caldria **un FK nou Item→GradingRuleSet** (patró cross-schema `db_constraint=False`, com GarmentPOMMap) i que `Model.grading_rule_set` passés a derivar-se de l'Item. → és un **canvi de disseny** (Patró C), no un estat existent. NO bloqueja: cap col·lisió estructural amb les FK vives.

---

## D · Aterratge d'ItemBaseMeasurement + porta germana de geometria

**FET — `GarmentPOMMap` = pertinença pura** ([pom/models.py:414-446](../backend/fhort/pom/models.py#L414)): `garment_type_item` FK (db_constraint=False, 421) · `pom` FK (424) · `obligatori` (425) · `is_key` (426) · `nivell` K/M/O/D (429) · `ordre` (433) · `pendent_revisio` (435). `unique_together(garment_type_item, pom)` (441). **CAP valor de mesura.**

**FET — `BaseMeasurement` penja del MODEL** ([models_app/models.py:478-532](../backend/fhort/models_app/models.py#L478)): `model` FK CASCADE (491) · `pom` FK PROTECT (492) · `base_value_cm` null (495, NULL=TEMPLATE) · `is_key` (497) · `is_active` (498) · `tolerancia_minus/plus` (511-512, **copy-at-the-moment** des de `POMMaster.tolerancia_default_*`, no live-link) · `nom_fitxa` (515) · `origen` (520) · `ordre` (523). `unique_together(model, pom)` (528).
**`ORIGEN_CHOICES` complet** (481-489): `STANDARD` · `IMPORTED` · `MANUAL` · `FITTED` · `CALCULATED` · `TEMPLATE` · `CHECKED`. *(Llista plana — additiva: cap blocador estructural per a un futur valor `'ITEM_STANDARD'`.)* Escriptura sempre via `update_or_create(model, pom, defaults)` (wizard_views, extraction_views, views set-measurements, size_check resolve).

**FET — migració família→item (pom 0016):** va eliminar el FK legacy `garment_type` de `GarmentPOMMap` i el seu `unique_together`, deixant **`garment_type_item` com a àncora única**. → el punt d'ancoratge de plantilla està consolidat i net.

**FET — verificació de l'aterratge d'`ItemBaseMeasurement` (NO creada):** una taula `ItemBaseMeasurement(garment_type_item FK, pom FK, base_value_cm, tolerancia±)` amb `unique_together(item, pom)` penjaria **directament de `GarmentTypeItem`** com a **germà de `GarmentPOMMap`**, mirall de `BaseMeasurement(model,pom)` però a la capa plantilla. NO passa pel Model ni per GarmentPOMMap, NO trenca FK, NO xoca amb 0016 (mateix patró `db_constraint=False` cross-schema pom↔tasks). → **estructuralment net.**

**FET — geometria (mirar sense construir):** zero models `Pattern*` (PatternFile/Piece/Point/Segment/POM/SewRelation/GradeRule) al codi; **zero `ezdxf`/`shapely`** a `requirements`. El "DXF base" és **blob mort**: `ModelFitxer.categoria='Patro'` ([models_app/models.py:328-334](../backend/fhort/models_app/models.py#L328)) — slot de metadada passiu, cap motor el llegeix. L'Item queda com a **punt net on penjarà un futur `PatternBase(garment_type_item → DXF)`** com a germà de GarmentPOMMap/ItemBaseMeasurement, sense tocar el disseny de mesures.

**Veredicte T4 — CONFIRMADA (viable).** **Veredicte T5 — CONFIRMADA.**

---

## E · Motor d'IMPORT — destí commutable (model | catàleg)

**FET — `ImportSession`** ([models_app/models.py:385-419](../backend/fhort/models_app/models.py#L385)): màquina d'estats `INICI→CRIBRATGE→TALLES→EXTRACCIO→POMS→MESURES→MESURES_OK→IMPORT→CONFIRMAT/DESCARTAT` (386-392). Desa: `document` (402) · **`model`** FK destí (405) · `model_detectat` JSON (408) · **`tipologia_confirmada`** FK→**tasks.GarmentTypeItem** (409-410) · `run_conciliat` JSON (411) · `poms_extrets` JSON (412) · `resultat` JSON (413) · `historia_xat`/`avisos` (414-415).

**FET — fases del flux** (*extraction_views.py, citacions de la investigació*): cribratge (`import_session_cribratge_view`) → talles (`..._talles_view`) → extracció (`..._extraccio_view`) + confirmació POMs (`..._poms_view`) → mesures (`..._mesures_view`) → teixit (`..._teixit_view`) → **confirmar (`import_session_confirmar_view`, ~línia 1708)**.

**FET — extracció híbrida 2-calls:** call barat de cribratge (Opus, max_tokens petit) + call ric d'extracció (Opus 16k amb `TECH_SHEET_EXTRACTION_PROMPT`); per Excel, parse determinista + revisió Sonnet. Reconciliació nomenclatura client→POM: `find_pom_master(code, description)` amb cascada exact-code → root-prefix → sinònim → nom_client → POMGlobal/abbreviation → numeric+lining, retornant `(pom_master, match_type, confidence)`.

**FET — JUNTURA DE COMMUTACIÓ DE DESTÍ (localitzada, no resolta):**
- **On diposita avui:** `import_session_confirmar_view` escriu el resultat al **Model** (`session.model`): `BaseMeasurement.update_or_create(model=model, …, origen='IMPORTED')` (~1801-1824) + `SizeFitting`/`GradingVersion`/`GradedSpec`/`ModelGradingRule` (~1826-1869), tot en una transacció.
- **La decisió de destí NO existeix:** la variable `model` (de `session.model`) està **cablejada** com a destí; no hi ha cap flag ni condicional. *(inferit dels write-points.)*
- **La juntura exacta a interceptar:** entre el fetch de sessió/model i el primer write (just abans de `BaseMeasurement.update_or_create(model=model, …)`). Un destí "catàleg" escriuria a `GradingRuleSet`/`GradingRule` + `GarmentPOMMap` + (futur) `ItemBaseMeasurement` en comptes de `BaseMeasurement(model)`.
- **Facilitador clau (FET):** la sessió **ja porta l'Item** (`tipologia_confirmada` FK→GarmentTypeItem, [models_app/models.py:409]). → l'àncora del destí catàleg **ja és present** a la sessió; commutar no requereix re-resoldre l'item, només triar la branca d'escriptura.

> **Resum E:** el `resultat` JSON és **prou desacoblat** (POMs + valors per talla + grading); el que falta per commutar és un **selector de destí** a la juntura del confirmar i una branca d'escriptura cap a catàleg. La diagnosi **localitza** la juntura; NO la resol (Patró C).

---

## F · INVENTARI — endpoints que escriuen mesura/grading/POM a nivell de MODEL

> Mapa de "qui escriu al Model" → per saber quins tindran germà "qui escriu al catàleg". Rutes i línies de la investigació; taules confirmades pels models de §A-D.

| Endpoint (ruta · mètode) | View (fitxer:línia) | Escriu què | Taula | Origen |
|---|---|---|---|---|
| `/api/v1/models/create-wizard/` · POST | models_app/views.py:223 | Model + materialitza grading | `Model`, `ModelGradingRule` | CANONICAL (si ruleset) |
| `/api/v1/models/<id>/materialitzar-poms/` · POST | models_app/views.py:~444 | BaseMeasurement buides de plantilla | `BaseMeasurement` | **TEMPLATE** |
| `/api/v1/models/<id>/set-measurements/` · POST | models_app/views.py:~656 | Valors base (upsert) | `BaseMeasurement` | **MANUAL** |
| `/api/v1/models/<id>/reorder-measurements/` · POST | models_app/views.py:~721 | `ordre` | `BaseMeasurement` | — (no canvia origen) |
| `/api/v1/models/<id>/guardar-talla-base/` · PATCH | pom/wizard_views.py:~153 | Valors base (upsert/clear) | `BaseMeasurement` | (defecte STANDARD) |
| `/api/v1/models/<id>/confirmar-talla-base/` · POST | pom/wizard_views.py:~230 | Tanca base + grading | `SizeFitting`, `GradedSpec` | (motor) |
| `/api/v1/models/<id>/generar-grading/` · POST | models_app/views.py:~1039 | GradedSpec | `GradedSpec` | (motor) |
| `/api/v1/models/<id>/tancar-taula/` · POST | models_app/views.py:~485 | Tanca base | `SizeFitting`, `GradedSpec` | (motor) |
| `/api/v1/models/<id>/update-step2/` · PATCH | models_app/views.py:~376 | Re-materialitza grading si canvia ruleset | `Model`, `ModelGradingRule` | CANONICAL |
| `/api/v1/models/<id>/pom/<pom_id>/regim/` · POST | models_app/views.py:~1560 | Canvi de lògica per POM | `ModelGradingRule` | MANUAL/CANONICAL |
| `/api/v1/size-checks/open/` · POST | models_app/views_size_check.py:48 | Línies des de BaseMeasurement (snapshot) | `SizeCheckLine` | — (valor_teoric snapshot) |
| `/api/v1/size-checks/<id>/resolve/` · POST | models_app/views_size_check.py:62 | Valors validats (accept) + regrade | `BaseMeasurement`, `GradedSpec` | **CHECKED** |
| `/api/v1/size-check-lines/<id>/` · PATCH | models_app/views_size_check.py:~78 | Autosave cel·la (valor_real/decisio) | `SizeCheckLine` | — |
| `/api/v1/import-sessions/<token>/mesures/` · PATCH | models_app/extraction_views.py:~1564 | Valors a `resultat` JSON (staging) | `ImportSession` | — (encara no a taules finals) |
| `/api/v1/import-sessions/<token>/confirmar/` · POST | models_app/extraction_views.py:~1708 | **Diposita el resultat al Model** | `BaseMeasurement`, `SizeFitting`, `GradingVersion`, `GradedSpec`, `ModelGradingRule`, `ModelFitxer`, `Model` | **IMPORTED** |
| `/api/v1/models/create-from-extraction/` · POST | models_app/extraction_views.py:~143 | Model + mesures + POMMaster nous | `Model`, `BaseMeasurement`, `POMMaster` | IMPORTED |
| `/api/v1/base-measurements/` (ViewSet) · POST/PATCH | models_app/views.py:~84 | CRUD directe | `BaseMeasurement` | (del payload; defecte STANDARD) |
| *(servei)* `materialize_model_grading_rules` | models_app/services.py:~67 | bulk recreate regles resident | `ModelGradingRule` | CANONICAL/IMPORTED/MANUAL |
| *(servei)* `generate_graded_specs` | pom/services.py:~18 | GradedSpec per POM×talla | `GradedSpec` | (motor) |

**Observacions FET:** (a) tota mesura base passa per **`BaseMeasurement(model,pom)`** amb `origen` com a rastre; (b) **`ModelGradingRule`** només s'escriu via `materialize_model_grading_rules` (4 crides); (c) **`GradedSpec`** sempre via motor, mai endpoint directe; (d) el confirmar de l'import és l'únic punt que escriu **atòmicament** Model+mesures+grading sencer.

---

## 💡 PROPOSTA — a validar (Patró C posterior, NO decidit aquí)

> Tot el següent és hipòtesi de disseny derivada dels FET; cap és decisió presa.

1. **💡 ItemBaseMeasurement com a germà net de GarmentPOMMap.** Taula nova `ItemBaseMeasurement(garment_type_item, pom, base_value_cm, tolerancia_minus, tolerancia_plus)` `unique(item, pom)`, `db_constraint=False` (cross-schema), mirall de `BaseMeasurement` a la capa plantilla. Penja de l'Item, NO del Model ni de GarmentPOMMap (que segueix pertinença pura). *(Suportat per T4.)*
2. **💡 Origen additiu `ITEM_STANDARD`** a `BaseMeasurement.ORIGEN_CHOICES` per rastrejar valors sembrats des de l'Item quan es materialitzin al Model (la sembra ja existeix buida via `materialitzar-poms`; només caldria copiar el valor). *(Cadena de sobirania "última veritat mana" ja vigent via `update_or_create(model,pom)`.)*
3. **💡 Decisió T1 — Item com a context de grading.** Si es vol, afegir FK `GarmentTypeItem.grading_rule_set` (db_constraint=False) i fer que `Model.grading_rule_set` en derivi. Caldria revisar els 4 punts que avui trien ruleset a nivell de Model (wizard, update-step2, import-confirmar, regim). *(REFUTA actual de T1 → cal canvi explícit.)*
4. **💡 Commutador de destí de l'import.** Afegir un selector `destinacio ∈ {model, cataleg}` a `ImportSession`/request i una branca al confirmar (juntura localitzada a §E). El destí catàleg escriuria GradingRuleSet/GradingRule + GarmentPOMMap + ItemBaseMeasurement, usant `session.tipologia_confirmada` (ja present). *(Estira menys IA: molts models nous partirien de l'Item-base sense interpretar fitxa.)*
5. **💡 PatternBase germà de geometria.** Quan toqui el Motor de Patrons, `PatternBase(garment_type_item → DXF/PatternFile)` penjaria de l'Item com a tercer germà (GarmentPOMMap = pertinença, ItemBaseMeasurement = mesures base, PatternBase = geometria base), reaprofitant el `ModelFitxer.categoria='Patro'` mort. *(Suportat per T5; NO construir ara.)*

---

## Tancament

- **5 tesis resoltes** amb `fitxer:línia` (T1 REFUTADA·MATISADA · T2 MATISADA · T3 CONFIRMADA · T4 CONFIRMADA · T5 CONFIRMADA).
- **6 àrees A–F documentades**, FET separat de 💡 PROPOSTA.
- **Juntura de commutació de l'import LOCALITZADA** (§E: `import_session_confirmar_view`, just abans del primer write `BaseMeasurement(model=...)`; àncora `tipologia_confirmada` ja present) — no resolta.
- **Inventari F complet i taulat** (endpoint · escriu · taula · origen).
- **READ-ONLY respectat:** `git status` net (aquest doc untracked com els altres DIAGNOSI_*), cap fitxer de codi tocat, cap migració, DB només SELECT, staging intacte.

*Aquesta diagnosi alimenta una decisió de disseny (Patró C). Aquí NO es decideix arquitectura.*
