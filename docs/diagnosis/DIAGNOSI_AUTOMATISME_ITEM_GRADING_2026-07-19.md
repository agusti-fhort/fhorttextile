# DIAGNOSI — Automatisme Item ↔ Grading (FASE A · Patró A, read-only)

> Brief: AUTOMATISME ITEM ↔ GRADING · FASE A (Patró A). Objectiu: entendre com es
> resol AVUI el `grading_rule_set` d'un model nou, abans de decidir la Via B.
> Data: 2026-07-19 · Branca `dev` · Read-only absolut (cap línia tocada).

## TL;DR

En **cap** dels tres camins de creació de model el `grading_rule_set` es proposa a
partir de `GarmentTypeItem.grading_rule_set` **ni** de `SizingProfile`:

| Camí | D'on surt el `grading_rule_set` |
|------|--------------------------------|
| **Wizard manual** (ModelWizard) | **Selecció 100% manual** del tècnic (opció c), filtrada pels eixos target+construction+fit+grup+size_system. |
| **Import (W5)** | **Contenidor de client** `cerca_contenidor_client(customer, size_system, garment_type_item, fit_type)` — GradingRuleSet `origen=CLIENT_RUN`. Si no existeix: tria conscient (`create`/`no_container`), 409 si falta. |
| **Massiu (bulk)** | **Res** — es crea amb `grading_rule_set = NULL` i es marca «incomplet» després. |

- `GarmentTypeItem.grading_rule_set` existeix com a camp però **mai** es propaga a un
  Model en runtime (només s'edita/serveix a la pàgina d'autoria d'items).
- `SizingProfile` segueix **desacoblat en runtime**: tots els seus lectors viuen a la
  Size Library (browse/detall/clon/versió/CSV) o al Size-Map; cap proposa grading per a un model.
- `base_size_definition` és un camp **independent**, no s'omple sol en assignar el ruleset.
- El selector de ruleset **SÍ ofereix contenidors amb 0 regles** (no hi ha cap filtre que els exclogui).

---

## 1. Wizard manual — d'on surt el `grading_rule_set` proposat

**Resposta: de cap dels dos (selecció 100% manual, opció c).** Ni de
`GarmentTypeItem.grading_rule_set` ni de `SizingProfile`.

Frontend `frontend/src/pages/ModelWizard.jsx`:
- Estat inicial a `null`; comentari explícit «Aquí NO s'arrossega grading_rule_set_id»
  — [ModelWizard.jsx:70](../../frontend/src/pages/ModelWizard.jsx#L70),
  [:80](../../frontend/src/pages/ModelWizard.jsx#L80).
- En entrar al bloc 4 carrega TOTS els rulesets (`gradingRuleSets.list({ page_size: 200 })`);
  cap proposta per-item/per-profile — [ModelWizard.jsx:202](../../frontend/src/pages/ModelWizard.jsx#L202).
- L'usuari tria un **fit** i després un ruleset via `RuleSetPicker`; només `onPick` fixa
  `gradingRuleSetId` — [ModelWizard.jsx:516-524](../../frontend/src/pages/ModelWizard.jsx#L516-L524).
  Existeix casella «Sense graduació» explícita.
- El payload de creació posa `grading_rule_set_id` = el triat (o `null` explícit / `undefined`)
  — [ModelWizard.jsx:240](../../frontend/src/pages/ModelWizard.jsx#L240),
  [:249](../../frontend/src/pages/ModelWizard.jsx#L249).
- La `l.145` (`if (d.grading_rule_set) setGradingRuleSetId(...)`) només **hidrata** el
  ruleset d'un model **ja existent** en edició; no és una proposta — [ModelWizard.jsx:145](../../frontend/src/pages/ModelWizard.jsx#L145).

Filtre d'eixos (estricte, no proposta): `frontend/src/components/grading/gradingAxes.js`
- `matchingRuleSetsStrict` exigeix target+construction+fit+grup+size_system coincidents;
  comentari «cap arrossegament implícit ni fals positiu» —
  [gradingAxes.js:146-162](../../frontend/src/components/grading/gradingAxes.js#L146-L162).

Backend `backend/fhort/models_app/views.py` (`create_model_wizard`, POST):
- `_resolve_garment_def`: quan arriba `garment_type_item_id`, en deriva **només**
  `garment_type` i `garment_group`; **NO** llegeix `item.grading_rule_set` ni
  `item.base_size_definition` — [views.py:396-406](../../backend/fhort/models_app/views.py#L396-L406).
- El ruleset ve **només** del payload `grading_rule_set_id` —
  [views.py:418-422](../../backend/fhort/models_app/views.py#L418-L422).

## 2. Import (W5) i creació massiva

### Import W5 → contenidor de client
Endpoint `import_session_confirmar_view` a
[extraction_views.py:1645](../../backend/fhort/models_app/extraction_views.py#L1645).
Bloc «GRADING segons la LLEI DEL CONTENIDOR (2026-07-16)» a
[extraction_views.py:1814](../../backend/fhort/models_app/extraction_views.py#L1814):
- Detecció de forma de graduació (pura, sense persistir): `derive_rules_from_fitxa(...)`
  — [extraction_views.py:1829](../../backend/fhort/models_app/extraction_views.py#L1829)
  (`grading_utils.py:450`). L'antic auto-creador `derive_grading_rule_set` està **JUBILAT**.
- **Font del ruleset**: `container = cerca_contenidor_client(model.customer, model.size_system, gti, rs_fit)`
  amb `gti = model.garment_type_item` — [extraction_views.py:1835-1837](../../backend/fhort/models_app/extraction_views.py#L1835-L1837).
  Definició: filtra `GradingRuleSet` per `origen=CLIENT_RUN, actiu, customer, size_system,
  garment_type_item, fit_type` — [grading_utils.py:535-549](../../backend/fhort/pom/grading_utils.py#L535-L549).
- Desenllaços (tots escriuen `model.grading_rule_set`):
  - Contenidor existeix → SEMBRA/AMPLIA i assigna — [extraction_views.py:1950](../../backend/fhort/models_app/extraction_views.py#L1950).
  - Absent + `create` → crea nou `GradingRuleSet` (CLIENT_RUN) i assigna — [extraction_views.py:1907](../../backend/fhort/models_app/extraction_views.py#L1907).
  - Absent + `no_container` → `grading_rule_set = None` (regles residents al model) — [extraction_views.py:1890](../../backend/fhort/models_app/extraction_views.py#L1890).
  - Falta decisió → **409 + rollback** — [extraction_views.py:1846](../../backend/fhort/models_app/extraction_views.py#L1846).

### Massiu / bulk
- `BulkCollectionImport._build_model` posa garment_type/item, size_system, target,
  construction, run/base — però **NO** posa `grading_rule_set` (queda NULL) —
  [bulk_import_service.py:563-583](../../backend/fhort/models_app/bulk_import_service.py#L563-L583).
- `flag_incomplete_models` només MARCA els models amb `grading_rule_set` buit; no l'assigna
  — [flag_incomplete_models.py:51](../../backend/fhort/models_app/management/commands/flag_incomplete_models.py#L51).
- `clone_model_for_qa` reusa el FK del model origen per valor (clon), no és derivació —
  [clone_model_for_qa.py:86](../../backend/fhort/models_app/management/commands/clone_model_for_qa.py#L86).
- Cap management command construeix un `Model(...)` amb ruleset derivat.

## 3. Els 18 SizingProfile LOS — es llegeixen en runtime per proposar grading?

**No.** Segueix «desacoblat en runtime». Tots els lectors de `SizingProfile` viuen a la
Size Library o al Size-Map; cap proposa un `grading_rule_set` per a un Model:
- Llista/detall/clon Size Library — [s2_views.py:74-243](../../backend/fhort/pom/s2_views.py#L74-L243).
- Versions/regles de perfil — [s4_views.py:162-302](../../backend/fhort/pom/s4_views.py#L162-L302).
- Export CSV — [s8_views.py:99](../../backend/fhort/pom/s8_views.py#L99).
- Size-Map crea SizingProfile com a artefacte **downstream** (WRITE), no el rellegeix per
  proposar — [size_map_views.py:944](../../backend/fhort/pom/size_map_views.py#L944).
- L'antic endpoint `?target`-via-SizingProfile està «buit i jubilat, 0 cridadors» —
  [s2_views.py:378](../../backend/fhort/pom/s2_views.py#L378).
- Frontend: `SizingProfileSelector` només l'importa `SizeLibrary.jsx`.

⚠️ Matís: `SizingProfile` **té** un FK `grading_rule_set` i el serializer l'exposa
([s2_serializers.py:98](../../backend/fhort/pom/s2_serializers.py#L98)), però és per a
preview dins la Size Library; el wizard i l'import **no** el consumeixen com a proposta.

## 4. `GarmentTypeItem.base_size_definition` — s'omple sol o és camp a part?

**Camp independent, NO auto-omplert en assignar el ruleset.**
- Definició FK a `pom.SizeDefinition`, `null/blank`, `SET_NULL` —
  [tasks/models.py:306-310](../../backend/fhort/tasks/models.py#L306-L310).
  `grading_rule_set` FK a `pom.GradingRuleSet`, `PROTECT` — [tasks/models.py:319-323](../../backend/fhort/tasks/models.py#L319-L323).
- **No hi ha `save()` override ni signal** a `GarmentTypeItem`. `clean()` només VALIDA la
  coherència (la talla base ha de ser del mateix `size_system` que el ruleset), mai la
  **fixa** — [tasks/models.py:331-343](../../backend/fhort/tasks/models.py#L331-L343).
- El serializer d'autoria tracta els dos camps com a escrivibles independents i només
  revalida via `clean()` — [tasks/serializers_b.py:116-140](../../backend/fhort/tasks/serializers_b.py#L116-L140).
- A la UI d'items, en triar un ruleset incompatible es **neteja** `base_size_definition` a
  null; la talla base es fixa per acció d'usuari separada — `ItemAuthoring.jsx:133-135, 152`.
- Per tant, que `top_sleeveless` mostri «Talla base M» a la captura és perquè l'Agus l'ha
  assignada **manualment**, no perquè l'assignació del ruleset la derivi.

## 5. El selector de ruleset ofereix contenidors amb 0 regles?

**Sí — cap filtre els exclou, ni backend ni frontend.**

Editor d'item = `frontend/src/pages/ItemAuthoring.jsx` (rutes a `App.jsx:304-305`); el
selector és `RuleSetPicker` — [ItemAuthoring.jsx:260-269](../../frontend/src/pages/ItemAuthoring.jsx#L260-L269).
El text «… · 0 regles» és la píndola de recompte de `RuleSetPicker`
(`reglesCount = rs.regles_count ?? rs.regles?.length ?? 0`) —
[RuleSetPicker.jsx:79](../../frontend/src/components/grading/RuleSetPicker.jsx#L79),
[:118](../../frontend/src/components/grading/RuleSetPicker.jsx#L118).

- **Backend** `GradingRuleSetViewSet` — queryset `.all()`, `filterset_fields = ['actiu',
  'garment_group', 'size_system', 'customer']`, cap `Count('regles')`/`filter(...__gt=0)` —
  [pom/views.py:170-178](../../backend/fhort/pom/views.py#L170-L178). El serializer exposa
  `regles_count` (`source='regles.count'`) però NOMÉS per mostrar —
  [pom/serializers.py:190](../../backend/fhort/pom/serializers.py#L190).
- **Frontend** `matchingRuleSets`/`matchingRuleSetsStrict` filtren només per eixos
  (target/construction/fit/grup/system) + `actiu`; mai inspeccionen el recompte de regles —
  [gradingAxes.js:135-162](../../frontend/src/components/grading/gradingAxes.js#L135-L162).

**On aniria el filtre** (si es decideix excloure buits):
- Backend: `pom/views.py:170` — `annotate(n_regles=Count('regles')).filter(n_regles__gt=0)`,
  idealment darrere un flag perquè les pantalles de CRUD/gestió encara vegin els buits.
- Frontend: `gradingAxes.js:138-143` i `:154-161` — afegir
  `&& (rs.regles_count ?? rs.regles?.length ?? 0) > 0`.

---

## Radi / notes per a la decisió de la Via B

- La Via A del brief (command `assign_item_default_grading`) escriuria a
  `GarmentTypeItem.grading_rule_set` + `base_size_definition` — un camp que **avui cap camí
  de creació de model consumeix**. Perquè tingués efecte de proposta caldria, a més, cablar
  la lectura (wizard i/o `_resolve_garment_def` / import) o assumir que és només documentació
  de l'item. Decisió humana (CTO).
- `base_size_definition` i `grading_rule_set` han de compartir `size_system` (validat a
  `clean()`): el command haurà de posar-los coherents o fallarà la validació.
- El «0 regles» del selector és ortogonal a la Via A però toca la mateixa superfície; anotat.
