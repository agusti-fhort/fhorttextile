# DIAGNOSI — ITEM-PLANTILLA-COMPLETA (import→item + consolidació item↔ruleset)

> **Data:** 2026-07-22 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
> **Abast:** (B1) el camí d'alimentació de la plantilla d'item des de l'import de fitxa i l'acte de
> PROMOCIÓ model→item; (B2) la consolidació dels vincles item↔`GradingRuleSet` en un sol mecanisme
> (llei D4); (B3) cost i ordre de dependència.
>
> **Convenció:** tota afirmació porta `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi**
> (verificat per grep exhaustiu, no especulat). Les propostes van marcades `💡 PROPOSTA (a validar)`
> i **no** són decisions: les decisions són humanes (Patró C).
>
> **Guardes complertes:** cap escriptura de codi, cap commit, cap migració, cap restart · BD només
> `SELECT` (schemes `fhort` i `los`) · `migrate_schemas --list` no usat · únic fitxer creat: aquest.
> No s'ha tocat res del radi de la **Sessió A paral·lela** (import/mesures/regles).
>
> **⚠️ Nota normativa — `DECISIONS.md §MELÓ` NO EXISTEIX.** El brief el cita com a font de les
> decisions tancades del 2026-07-22 i del paquet nou obert. Verificat: `grep -rn "MEL[ÓO]"` sobre tot
> el repo i sobre `/root/fhort-sessions/` → **0 hits**; `DECISIONS.md` (working tree, 462 línies
> afegides i **no commitades**) es declara *"Última actualització: 2026-07-16"* (`DECISIONS.md:14`).
> Existeixen §1, §2, §3, §4, §5, §6 i una "LLEI — Resolució de codi de client → POM" a `:812`, però
> cap §MELÓ. **El text del brief és, doncs, la font normativa d'aquesta diagnosi** — mateix precedent
> que la llei de les 5 capes (`DIAGNOSI_5CAPES_PROCES.md:9-12`). → **DECISIONS PENDENT:** escriure
> §MELÓ a `DECISIONS.md`.
>
> **⚠️ Deriva de línies post-S22b:** les referències de `DIAGNOSI_GTI_PLANTILLA_2026-07-21.md` han
> desplaçat. `materialize_poms_view` viu ara a `models_app/views.py:877-979` (no 766-843); les
> "NORMES INAMOVIBLES" a `extraction_views.py:1721-1731` (no 1722-1725). Tot el que segueix està
> re-verificat contra el codi d'avui.

---

## RESUM EXECUTIU

1. **La plantilla d'item no té cap alimentació automàtica, i això és per disseny explícit.** Cap camí
   de l'import escriu mai `ItemBaseMeasurement` — verificat per grep exhaustiu (24 hits al repo, cap
   a `extraction_views.py`). Els **únics dos escriptors** són el ViewSet `CONFIGURE`
   (`pom/views.py:304-360`) i el loader CLI del paquet LOSAN (`load_losan_package.py:356`).
   `bootstrap_tenant.py:132-160` **ni tan sols l'inclou** al cens de còpia. La norma inamovible 1 de
   l'import ho diu amb totes les lletres: *"NO materialitza la plantilla de l'item"*
   (`extraction_views.py:1721-1731`). **La visió d'Agus no demana desfer un accident: demana obrir
   una porta que mai s'ha obert.**

2. **El punt d'ancoratge barat de la PROMOCIÓ ja existeix — i és el bessó especular d'una funció que
   ja hi és sencera.** `materialize_poms_view` (`models_app/views.py:877-979`) ja té el guard d'item
   (`:895-908`), el mapa de `GarmentPOMMap` (`:911-924`), el dict `ibms` d'`ItemBaseMeasurement`
   (`:926-927`), el patró de subconjunt `pom_ids` i la resposta `{materialized, seeded, skipped}`.
   El seu invers (model→item) és la peça de **menor cost** de les tres superfícies inventariades. El
   preu real no és el codi: és el **gate** (§B1.3) i la **direcció de la sobirania** (§B1.4).

3. **El gate CONFIGURE que la decisió exigeix NO el compleix cap de les dues superfícies de model.**
   `confirmar/` de l'import (`extraction_views.py:1717`) i `materialize_poms_view`
   (`models_app/views.py:876`) són tots dos **`IsAuthenticated` pelat**. La capa d'item, en canvi, ja
   és `CONFIGURE` sencera (`pom/views.py:320-325`, `tasks/views_b.py:874-878`). **Penjar la promoció
   del camí del model importa el seu gate fluix a la capa de catàleg.**

4. **La talla en què s'expressen els valors d'item és avui una convenció no verificada — i ja hi ha
   una fuga silenciosa.** `GarmentTypeItem.base_size_definition` és **NULL a 59 dels 62 GTI** de
   `fhort` (`los`: taula buida) i **cap codi de negoci el llegeix**: 0 hits a `models_app/`,
   `fitting/`, `patterns/` i als views de `pom/`. Els seus únics lectors són display, `clean()` i
   l'export LOSAN. **`materialize_poms_view` copia item→model sense comparar-la mai amb
   `Model.base_size_label`** (`views.py:930-968`): els valors poden aterrar com a `ITEM_STANDARD`
   expressats en una talla diferent de la del model, **en silenci**. El `blouse` (gti=5) té
   `grading_rule_set=115` però `base_size_definition` NULL.

5. **Els vincles item↔ruleset no són tres: en són CINC, i cap dels dos `RuleSetPicker` no llegeix els
   dos que el brief creia decisius.** V1 (`GarmentTypeItem.grading_rule_set`) i V2
   (`GradingRuleSet.garment_type_item`) **no generen cap llista**. La llista la generen **V3**
   (`targets` M2M) + **V4** (`RuleSetScopeNode`/`garment_group`) sobre un endpoint **sense cap filtre
   d'item** (`pom/views.py:170-188`; tot el filtratge és 100% frontend). Per al `blouse`, els
   candidats genèrics hi entren **per comodí d'eix NULL** (`gradingAxes.js:77-80`), no per pertinença.

6. **V1 queda confirmada com a fulla morta aigües avall, i R21 s'ha de reclassificar a la baixa.**
   `grep` del `related_name` de V1 → **zero consumidors**; els seus únics lectors són un semàfor de
   completesa (`GarmentTypes.jsx:384`) i la re-hidratació de la seva pròpia pàgina. I
   `pom/grading_utils.py:339` **ja no és el lector decisori de res**: `derive_grading_rule_set` **no
   té cap cridador viu** (l'única menció a `extraction_views.py:1844` és un comentari). Les 10
   divergències FK↔M2M i les 8 no representables segueixen intactes, però són **deute mort**, no
   risc viu. El camí d'import real ja va per M2M (`grading_utils.py:641`).

7. **El backfill LOSAN de `garment_type_item` és, en la seva forma literal, IMPOSSIBLE — i la dada ho
   demostra.** 20 de 20 rulesets LOSAN tenen el camp NULL; només **2** (rs 182→item 4, rs 185→item
   43) tenen un item únic derivable. **13 de 20** serveixen 3+ items diferents: no hi ha *un* item,
   hi ha un **conjunt**. I quatre d'ells (175,176,177,178) **ja porten el conjunt real a
   `RuleSetScopeNode`**, que sí el sap expressar. Pitjor: backfillar-los faria **col·lidir la
   constraint** `uniq_client_container_identity` en sis grups que avui comparteixen
   `(customer=6, size_system, fit=REGULAR)`, i **trauria els 20 del NIVELL 2 del matcher**
   (`grading_utils.py:632-635`), que és l'únic nivell pel qual són accessibles avui.

---

## BLOC B1 — EL CAMÍ D'ALIMENTACIÓ IMPORT→ITEM

### B1.1 On escriu l'import, avui (traça exacta)

#### (a) Deltes / breaks → `GradingRuleSet`

| Pas | `ruta:línia` | Fet |
|---|---|---|
| Endpoint | `models_app/extraction_views.py:1716-1718` | `import_session_confirmar_view`, `@permission_classes([IsAuthenticated])` |
| Deltes→absoluts | `extraction_views.py:1841-1854` | `deltes_a_absoluts(valors, base_size, run_ordenat_conv)` si `valors_mode=='deltes'` |
| **DETECCIÓ (pura)** | `extraction_views.py:1897-1899` → `pom/grading_utils.py:450` | `derive_rules_from_fitxa(...)` — **no persisteix res** |
| ~~`derive_grading_rule_set`~~ | `pom/grading_utils.py:251` | **NO el crida l'import.** Declarat JUBILAT com a creador a `grading_utils.py:430`; l'única menció a `extraction_views.py:1844` és un **comentari mort** |
| MATCHER de contenidor | `extraction_views.py:1903-1907` → `grading_utils.py:577` | `resolve_grading_container(...)` — N1 identitat / N2 ampli (item NULL) / N3 cap |
| Classificació | `extraction_views.py:1941` → `grading_utils.py:685` | `classifica_fitxa_vs_contenidor` → `{sembra, conflicte, amplia}` |
| Gates 409 | `extraction_views.py:1917-1939` | `container_ambigu`, `container_absent` — **abans** de qualsevol escriptura |
| **CREA `GradingRuleSet` CLIENT_RUN** | `extraction_views.py:2007-2014` | `create(..., garment_type_item=None, origen=ORIGEN_CLIENT_RUN, customer=model.customer)` — només si `container_choice=='create'` |
| Regles al contenidor nou | `extraction_views.py:2017` → `models_app/services.py:214` | `afegeix_regles_al_contenidor(container, fitxa_specs, base_def_id)` |
| Contenidor ESQUELET (0 regles) | `extraction_views.py:2025-2029` | sembrar-lo des de la fitxa és LEGÍTIM |
| **Contenidor AMB regles → INTOCABLE (llei M3)** | `extraction_views.py:2032-2078` | no escriu al ruleset; la divergència va a `ModelGradingOverride` (`:2065-2070`) + watchpoint |
| Sense contenidor (decisió del tècnic) | `extraction_views.py:1995-2002` | `model.grading_rule_set = None`; regles residents pròpies |
| Regles residents del MODEL | `extraction_views.py:2087-2089` → `services.py:192` | `materialize_model_grading_rules_from_specs(model, resident_specs, origen='IMPORTED')` |

Altres creadors de `GradingRuleSet` CLIENT_RUN **fora** de l'import de fitxa: `pom/size_map_views.py:856-859`,
`pom/s2_views.py:192-198`.

#### (b) Mides → `BaseMeasurement` del MODEL

| `ruta:línia` | Fet |
|---|---|
| `extraction_views.py:1948` | `BaseMeasurement.objects.filter(model=model, base_value_cm__isnull=True).delete()` — purga de plantilla buida |
| `extraction_views.py:1951-1967` | `for i, p, pm in resolved:` → `update_or_create(model=model, pom=pm, defaults=...)` amb `origen='IMPORTED'`, `ordre=i`, `nom_fitxa`, `notes`; toleràncies **només si el document en porta** (`:1962-1965`) |
| `extraction_views.py:1953` | `base_val = valors.get(pom_master_id, {}).get(base_size)` — **el valor ve de la columna de la talla base** |
| `extraction_views.py:1969-1974` | `maybe_learn_customer_alias(...)` — biblioteca de nomenclatura del client |
| `extraction_views.py:2110-2115` | avís C3 si `n_bm and not n_bm_valors` |

#### (c) `ItemBaseMeasurement` — **CAP camí automàtic hi escriu mai. CONFIRMAT.**

`grep -rn "ItemBaseMeasurement" --include=*.py --include=*.jsx .` (exclosos migracions i `node_modules`)
→ **24 hits, cap a `extraction_views.py`**.

| `ruta:línia` | Escriptor | Gate |
|---|---|---|
| `pom/views.py:304-329` | `ItemBaseMeasurementViewSet` (create/update/destroy) | `get_permissions` `:320-325` — list/retrieve `IsAuthenticated`; **la resta `HasCapability` + `CONFIGURE`** |
| `pom/views.py:331-360` | acció `upsert` → `update_or_create` a `:354-355` | **`CONFIGURE`** |
| `pom/management/commands/load_losan_package.py:356` | `_upsert(ItemBaseMeasurement, {...})` | cap (CLI) |
| `models_app/tests_sembra_grading.py:112,115` | tests | — |

**Lectors** (mai escriuen): `models_app/views.py:902,926` (`materialize_poms_view`),
`pom/management/commands/export_losan_package.py:151,245`.
**`bootstrap_tenant.py:132-160` NO l'inclou** al cens de còpia → **NO EXISTEIX** camí de bootstrap que l'escrigui.

> **TROBALLA TRANSVERSAL:** `ItemBaseMeasurement` té **una sola** superfície d'escriptura de producte
> (el ViewSet `CONFIGURE`) i **un sol** consumidor (`materialize_poms_view`). El flux d'import és
> **unidireccional model-only**: no hi ha cap retorn cap a la capa Item enlloc del repo.

### B1.2 On viu la talla base del document durant l'import

| Moment | `ruta:línia` | Camp |
|---|---|---|
| Extracció Excel | `extraction_views.py:426` (`meta['base_size']`), `:1237-1238` | `base_size = meta.get('base_size') or sizes[0]` |
| Persistit a la sessió | `extraction_views.py:1267`, `:1433` | `ImportSession.resultat['extraccio']['base_size']` (JSON) |
| Confirmació humana (Pas 1) | `extraction_views.py:634` | payload `base_size_label` de `PATCH /import-sessions/<token>/talles/` |
| **Escriptura al MODEL** | `extraction_views.py:689-691` | `model.base_size_label = base_in; model.save(update_fields=['base_size_label'])` |
| Guard bloquejant | `extraction_views.py:696-700` | la talla base ha de tenir columna del document aparellada |
| Reconciliació al confirmar | `extraction_views.py:1773`, `:1798`, `:1830` | `meta_update_fields=['size_system','base_size_label','size_run_model']` |
| Font de veritat | `extraction_views.py:1837-1840` | comentari literal: *"base_size = etiqueta tenant del model (mai document)"* |
| Aparellament doc→model | `extraction_views.py:1774-1782` | `session.run_conciliat['talla_mapping']` |

**Persistència més enllà de `Model.base_size_label`: NO EXISTEIX.**
- `GradingVersion`: cap camp de talla base (grep sobre `fitting/models.py` → 0 hits).
- `ModelTask`: cap camp de talla base (grep sobre `tasks/models.py` → 0 hits).
- L'única altra persistència és **`GradingRule.talla_base`** (FK `SizeDefinition`), escrita per
  `afegeix_regles_al_contenidor(container, specs, base_def_id)` amb
  `base_def_id = fitxa_specs[0]['talla_base_id']` (`extraction_views.py:1900`).
- **`GarmentTypeItem.base_size_definition` NO s'escriu MAI des de l'import** (§B1.5).

### B1.3 Les tres superfícies candidates per a l'acte de PROMOCIÓ

#### (a) Final del flux `confirmar/` de l'import

| `ruta:línia` | Què hi ha |
|---|---|
| `extraction_views.py:1716-1718` | entrada; **`IsAuthenticated`** |
| `extraction_views.py:1765` | `with transaction.atomic():` que cobreix tot el cos |
| `extraction_views.py:2129-2144` | pas 4: document → `ModelFitxer` |
| `extraction_views.py:2146-2154` | pas 5: teixit → camps del model |
| `extraction_views.py:2156-2158` | pas 6: `session.estat='CONFIRMAT'` (últim acte dins l'atòmica) |
| `extraction_views.py:2160-2177` | `return Response({...}, status=201)` amb `base_measurements`, `graded_specs`, `grading_rule_set`, `grading_avisos` |

**Cost mecànic: BAIX.** Totes les dades ja hi són en memòria (`resolved`, `valors`, `base_size`,
`model.garment_type_item` a `:1906`). **Fricció: ALTA** — el gate és `IsAuthenticated`, i escriure a
la capa Item des d'aquí **contradiu frontalment la norma inamovible 1** (`:1721-1731`).

> ⚠️ **I xoca amb el REQUISIT ja decidit:** *"mai automàtic a cada import"*. Enganxar la promoció al
> final de `confirmar/` és exactament el lloc on és més fàcil que esdevingui automàtica per omissió.

#### (b) Acció separada a la fitxa del model — **el bessó especular**

| `ruta:línia` | Què hi ha JA |
|---|---|
| `models_app/views.py:875-877` | `materialize_poms_view`, **`IsAuthenticated`** — la simètrica inversa (item→model) |
| `models_app/views.py:895-908` | guard `if not model.garment_type_item_id` |
| `models_app/views.py:902` | ja importa `GarmentPOMMap, ItemBaseMeasurement` |
| `models_app/views.py:911-924` | patró `pom_ids` (subconjunt) + `desconeguts` |
| `models_app/views.py:926-927` | `ibms = {i.pom_id: i for i in ItemBaseMeasurement.objects.filter(garment_type_item=...)}` |
| `models_app/views.py:930-968` | crea/omple + guard de sobirania |
| `pom/views.py:331-360` | l'escriptor legítim de destí (`upsert`, `CONFIGURE`) |
| `frontend/src/api/endpoints.js:535-538` | `itemBaseMeasurements.{list,upsert,remove}` **ja existeix al client** |

**Cost relatiu: EL MÉS BAIX.** L'esquelet complet ja hi és; la promoció n'és la imatge especular.
**Superfície UI: NO EXISTEIX** cap botó equivalent avui (`grep "materialitzar-poms" frontend/src` → 0 hits).

#### (c) Wizard d'autoria d'item, pas Construcció

| `ruta:línia` | Què hi ha JA |
|---|---|
| `frontend/src/pages/ItemAuthoring.jsx:328` | `<MeasurementBaseGrid garmentTypeItemId={itemId} />` dins del pas 2 |
| `ItemAuthoring.jsx:94,135,141,152,155` | ja llegeix/escriu `base_size_definition` |
| `MeasurementBaseGrid.jsx:56` | `itemBaseMeasurements.list({garment_type_item, page_size: 500})` |
| `MeasurementBaseGrid.jsx:147-176` | `handleSave`: `remove` (`:152`), `garmentPomMaps.create/update` (`:158-162`), `upsert` (`:164-171`) |
| `frontend/src/api/endpoints.js:375-381` | `garmentTypeItems` CRUD |

**Botó "importar del model X": NO EXISTEIX.** Confirmat per
`grep -rn "importar del model\|import_from_model\|fromModel" frontend/src` → 0 hits; cap crida a
`models.*` dins `MeasurementBaseGrid.jsx`; **no hi ha endpoint backend que llisti `BaseMeasurement`
per servir un selector de model dins l'autoria d'item**.

**Cost relatiu: EL MÉS ALT en frontend** (selector de model + endpoint de lectura nou),
**EL MÉS BAIX en permís** (aquesta superfície ja és tota `CONFIGURE`).

#### Matriu de gates — el requisit CONFIGURE (perfil 13, Montse)

| Superfície | `ruta:línia` | Gate ACTUAL | Compleix CONFIGURE? |
|---|---|---|---|
| `confirmar/` de l'import | `extraction_views.py:1717` | `IsAuthenticated` | ❌ **NO** |
| `materialize_poms_view` | `models_app/views.py:876` | `IsAuthenticated` | ❌ **NO** |
| `ItemBaseMeasurementViewSet` (write + `upsert`) | `pom/views.py:320-325` | `HasCapability` + `CONFIGURE` | ✅ |
| `GarmentTypeItemViewSet` (write) | `tasks/views_b.py:874-878` | `HasCapability` + `CONFIGURE` | ✅ |

> **Lectura:** la capa Item **ja té la porta que la decisió demana**. Les dues superfícies de model
> no. Qualsevol promoció ancorada a (a) o (b) ha de **portar el seu propi gate `CONFIGURE`**, no
> heretar el de l'endpoint amfitrió.

### B1.4 El conflicte de promoció: què hi ha AVUI

**Codi específic de promoció model→item: NO EXISTEIX.** Cap `update_or_create` cap a
`ItemBaseMeasurement` fora de `pom/views.py:354`, i **aquest no té cap guard**: `defaults` es
construeix pla a `:350-352` i sobreescriu incondicionalment tot camp present al body.

**Taula de precedència d'orígens per a `ItemBaseMeasurement`: NO EXISTEIX — i no pot existir avui.**
El model (`pom/models.py:464-501`) **no té camp `origen`**, a diferència de `BaseMeasurement`
(`TEMPLATE`/`ITEM_STANDARD`/`MANUAL`/`IMPORTED`/`FITTED`/…, `models_app/models.py:550-559`). Tampoc
té `created_at`/`updated_at` ni `created_by` — **un valor de plantilla no diu ni qui ni quan**
(ja anotat com a risc 9 a `DIAGNOSI_GTI_PLANTILLA_2026-07-21.md`).

**Precedents vius que sí resolen col·lisions** (material per a la decisió, no decisió):

| `ruta:línia` | Precedent | Forma |
|---|---|---|
| `models_app/views.py:886-892` | docstring *"SOBIRANIA DEL MODEL (idempotent): NOMÉS sembra on no hi ha res o on hi ha un TEMPLATE BUIT… a partir del primer valor, el Model és sobirà"* | **llei escrita** |
| `models_app/views.py:956-968` | `is_empty_template = existing.origen == 'TEMPLATE' and existing.base_value_cm is None`; `else: skipped += 1` | **no-trepitjar** |
| `extraction_views.py:1721-1731` | NORMES INAMOVIBLES: *"Mana el document… NO materialitza la plantilla de l'item"* | **direcció única** |
| `extraction_views.py:2032-2078` | **llei M3** — CONTENIDOR AMB REGLES → INTOCABLE: la divergència no trepitja el catàleg, es desa com a `ModelGradingOverride` + watchpoint (`:2065-2078`) | **desviació registrada** |
| `extraction_views.py:2025-2029` | CONTENIDOR ESQUELET (0 regles) → sembrar-lo des de la fitxa és LEGÍTIM | **buit ≠ ocupat** |
| `extraction_views.py:964-1010` | `_apply_many_to_one_guard` — dues files cap al mateix POM col·lapsarien | **guard d'unicitat** |
| `models_app/views.py:823-833` | `if n_regles == 0` → `logging.warning` + traça a la resposta | **degradació sorollosa** |
| `extraction_views.py:2090-2095` | `except` → restaura `prev_grs_id` i avisa | **rollback amb gràcia** |
| `pom/dictionary_service.py:158` | `preserve_manual = (ex.origen == 'MANUAL')` | **guard per origen** (l'únic del repo) |

**Les opcions naturals, exposades sense decidir:**

| Opció | Forma | Precedent que la sosté | Què exigeix a l'esquema |
|---|---|---|---|
| **Sobreescriure amb confirmació** | dry-run que retorna el diff (POMs que canvien, que s'afegeixen, que sobrarien) + segona crida amb `confirm=true` | el patró `{materialized, seeded, skipped}` de `views.py:930-968` | **res** |
| **Merge per POM** | només omple els forats (`base_value_cm IS NULL`), mai trepitja un valor existent | `is_empty_template` (`views.py:956-968`), llei "esquelet és sembrable" (`:2025-2029`) | **res** |
| **Versionar** | la plantilla guarda històric i es pot revertir | cap directe; l'anàleg és la cadena `versio/is_current/versio_anterior` d'`ItemFitxer` (`models_app/models.py:481-486`) | **taula nova o camps de versió** — la peça més cara |
| **Registrar la divergència** (variant M3) | la promoció no trepitja: escriu la proposta i deixa un watchpoint per a la Montse | **llei M3 sencera** (`extraction_views.py:2032-2078`) | camp o taula de proposta |

> **⚠️ LA TENSIÓ DE FONS, per a Patró C.** Les dues lleis vives apunten en direcció contrària a la
> promoció:
> - *"la plantilla sembra; el model POSSEEIX"* (`DECISIONS.md §2`), implementada com a
>   **copy-at-the-moment sense FK de retorn** (`models_app/models.py:558`).
> - *"la biblioteca ven forma, el model ven mides"* (`PLA_IMPLEMENTACIO_MOTOR_PATRONS.md:1107-1109`).
>
> La promoció **inverteix la direcció de la sobirania**. Això **no la invalida** —el que Agus demana
> és precisament que el taller pugui fixar el seu estàndard a partir d'un model real—, però obliga a
> escriure la llei que hi falta: *la sobirania és del model per als VALORS D'AQUELL MODEL; l'estàndard
> del taller és un acte separat, explícit, `CONFIGURE`, i mai un efecte secundari d'un import.*
> Sense aquesta llei escrita, la promoció i la norma inamovible 1 es contradiuen com ja es contradiuen
> l'auto-propagació i la llei §2 des del 23/06 (R13, `DIAGNOSI_REFACTOR_GRADING_2026-07-21.md`).

### B1.5 `GarmentTypeItem.base_size_definition` — la talla base de l'ITEM

**Definició:** `tasks/models.py:306-310` — FK `pom.SizeDefinition`, `SET_NULL`, `null=True`,
`related_name='base_for_items'`; constraint de BD REAL (comentari `:298-302`). Migracions
`tasks/migrations/0022_garmenttypeitem_base_size_definition.py:17`, alterada a `0023_…:22`.
**Validació:** `tasks/models.py:336-343` — `clean()` exigeix
`base_size_definition.size_system_id == grading_rule_set.size_system_id`; skip si algun és NULL.

| Rol | `ruta:línia` | Què fa |
|---|---|---|
| ESCRIPTOR | `tasks/views_b.py:842-878` | `GarmentTypeItemViewSet` PATCH/POST, gate `CONFIGURE` a `:874-878` |
| ESCRIPTOR | `tasks/serializers_b.py:117` + `:128-139` | camp escrivible; `validate()` invoca `clean()` via `probe` (`:134`) |
| ESCRIPTOR | `frontend/src/pages/ItemAuthoring.jsx:152` | `garmentTypeItems.update(itemId, {base_size_definition: sd.id})` |
| ESCRIPTOR | `ItemAuthoring.jsx:135` | `if (incompatible) payload.base_size_definition = null` — neteja en canviar de ruleset |
| ESCRIPTOR | `load_losan_package.py:447-462` | 2a passada del loader (`obj.base_size_definition = bsd`, `:461`) |
| LECTOR | `tasks/serializers_b.py:123-124` | `get_base_size_label` → `.etiqueta` (**display**) |
| LECTOR | `tasks/models.py:336-337` | `clean()` (**validació**) |
| LECTOR | `tasks/views_b.py:858` | `select_related` (**perf**) |
| LECTOR | `export_losan_package.py:220-226` | export |
| LECTOR | `ItemAuthoring.jsx:94,141,155` | UI d'autoria |

**NO EXISTEIX cap lector de negoci.** Grep sobre `models_app/`, `fitting/`, `patterns/` i
`pom/{views,grading_views,grading_utils,s2_views,s6_views,s8_views,s10_views,s11_views}.py` →
**0 hits**. En particular **cap motor de grading el llegeix**.

**Estat de dades (SELECT read-only):**

| schema | GTI totals | amb `base_size_definition` | amb `grading_rule_set` |
|---|---|---|---|
| `fhort` | **62** | **3** | **4** |
| `los` | **0** | 0 | 0 |

Els 3 informats a `fhort`: gti=4 `shirt_woven` (bsd=88, grs=84), gti=10 `top_sleeveless` (bsd=325,
grs=186), gti=58 `baby_dress` (bsd=109, grs=87).
**El gti=5 `blouse` té `grading_rule_set=115` però `base_size_definition` NULL.**
`pom_itembasemeasurement`: `fhort` **37 files sobre 1 sol GTI (gti=4)**; `los` **0**.

**Coherència amb `ItemBaseMeasurement`: documental, no verificada.** `pom/models.py:472` diu
literalment *"La talla a la qual s'expressen aquests valors és `GarmentTypeItem.base_size_definition`
(P1)"*, però **no hi ha FK, ni constraint, ni cap codi que ho validi** (`pom/models.py:475-488`
només té `garment_type_item`, `pom`, `base_value_cm`, `tol_minus`, `tol_plus`, `nom_fitxa`). Les 37
files de gti=4 estan cobertes **per casualitat de dades** (bsd=88 informat), no per invariant. Si
`base_size_definition` fos NULL amb `ItemBaseMeasurement` poblat, **res al codi ho detectaria**.

> **TROBALLA TRANSVERSAL (risc viu, ja avui):** `materialize_poms_view`
> (`models_app/views.py:930-968`) copia valors item→model **sense comprovar mai** que
> `GarmentTypeItem.base_size_definition.etiqueta == Model.base_size_label`. Els valors poden aterrar
> a `BaseMeasurement` amb `origen='ITEM_STANDARD'` **expressats en una talla base diferent de la del
> model, en silenci**. Amb 37 files en 1 item el dany actual és nul; amb la plantilla poblada per
> promoció, deixa de ser-ho.

**Qui hauria d'escriure `base_size_definition` i quan: NO EXISTEIX resposta al codi.** Avui és
**acció manual d'usuari a `ItemAuthoring`** (confirmat també a
`DIAGNOSI_AUTOMATISME_ITEM_GRADING_2026-07-19.md §4`: no hi ha `save()` override ni signal; `clean()`
valida però mai fixa). La promoció és el moment natural on el sistema **sap** la talla
(`Model.base_size_label`) — però l'escriptura toparia amb `clean()`
(`tasks/models.py:336-343`), que exigeix el mateix `size_system` que el `grading_rule_set` de l'item.

> **Veredicte B1:** l'import escriu **només** a la capa Model —`BaseMeasurement`
> (`extraction_views.py:1948-1974`) i `GradingRuleSet`/`GradingRule` CLIENT_RUN o
> `ModelGradingOverride` (`:2007-2078`)—, `derive_grading_rule_set` és codi mort, i **cap camí
> automàtic escriu mai `ItemBaseMeasurement`**. El punt d'ancoratge de menor cost per a la promoció
> és el bessó invers de `materialize_poms_view` (`models_app/views.py:877`), però **aquest i
> `confirmar/` estan gated només a `IsAuthenticated`** mentre la capa Item exigeix `CONFIGURE`. I
> `base_size_definition` (59/62 NULL a `fhort`) **no el llegeix cap codi de negoci**: la talla en què
> s'expressen els valors d'item és avui una **convenció no verificada**.

---

## BLOC B2 — CONSOLIDACIÓ ITEM↔RULESET

> **⚠️ Dada dura prèvia (confirma R25):** el schema `los` és **completament buit** — 0 GTI, 0
> `GradingRuleSet`, 0 `SizingProfile`, 0 files M2M, 0 scope-nodes. **Tot LOSAN viu al schema `fhort`**
> com a `tasks_customer id=6, codi='LOS'`. Tots els recomptes d'aquest bloc són de `fhort`.

### B2.1 Cens: no en són tres, en són CINC

| # | Vincle | Definició | Dades `fhort` |
|---|---|---|---|
| **V1** | `GarmentTypeItem.grading_rule_set` (FK → pom) | `tasks/models.py:319-325` | **4 / 62** GTI |
| **V2** | `GradingRuleSet.garment_type_item` (FK → tasks, invers) | `pom/models.py:544-547` | **1 / 45** rulesets |
| **V3** | `GradingRuleSet.targets` (M2M) + `target` (FK legacy) | `pom/models.py:566-577` | **56** files M2M / **44** FK |
| **V4** | `RuleSetScopeNode` (`applies_to`, multi-node GROUP/TYPE/ITEM) | `pom/models.py:621-659`, migració `pom/migrations/0040_rulesetscopenode.py` | **11** nodes sobre **6** rulesets |
| **V5** | `SizingProfile` (cascada de 4 eixos → ruleset) | `pom/models.py:912-947` | **45** perfils |

`GradingRuleSet.garment_type_item` **SÍ EXISTEIX** — migració
`pom/migrations/0039_gradingruleset_garment_type_item_and_more.py:15-22`, que hi afegeix també
`UniqueConstraint(customer, size_system, garment_type_item, fit_type) WHERE origen='CLIENT_RUN'`
→ `uniq_client_container_identity` (`:20-23`).

### B2.2 (a) `GarmentTypeItem.grading_rule_set` — FK singular

Migració `tasks/migrations/0023_garmenttypeitem_grading_rule_set_and_more.py:15-19` — **additiva, cap
data-migration, cap `NOT NULL` posterior**.

| Rol | `ruta:línia` | Què fa |
|---|---|---|
| ESCRIPTOR (únic real) | `tasks/serializers_b.py:117` + `:126-140` | PATCH `/api/v1/garment-type-items/{id}/` |
| ESCRIPTOR (frontend) | `ItemAuthoring.jsx:122-140` (`assignRuleset`, `payload={grading_rule_set: rs.id}`) | **única UI que l'escriu** |
| ESCRIPTOR (sembra) | `tasks/management/commands/bootstrap_tenant.py:280-295` | copia la FK; si el bloc no se selecciona, la posa a NULL |
| LECTOR | `tasks/serializers_b.py:121` (`grading_rule_set_nom`) | **display** |
| LECTOR | `tasks/views_b.py:858` (`select_related`) | **perf** |
| LECTOR (frontend) | `GarmentTypes.jsx:384,407` (`hasGrading`, StatusLine) | **semàfor de completesa** |
| LECTOR (frontend) | `ItemAuthoring.jsx:91,93` | **re-hidratació de la pròpia pàgina** |
| LECTOR (tests) | `fitting/tests.py:58`, `pom/test_g6_grading_gates.py:55` | fixtures |

**"Fulla morta aigües avall" — RE-VERIFICAT I CONFIRMAT.** Cap motor de grading, cap propagació, cap
materialització i cap matcher la llegeix:
`grep -rn "garment_type_items\b\|garment_type_item__grading\|item\.grading_rule_set"` → **només** la
`related_name` a `tasks/models.py:321` i la migració 0023. **Zero consumidors del related_name.**
El motor llegeix exclusivament `Model.grading_rule_set` (`models_app/models.py:193`; lectors a
`models_app/services_size_check.py:90-93`, `extraction_views.py:719-720,1550`, `pom/services.py:124`).

**Dades:** 4/62 — gti 4 `shirt_woven`→rs 84, **gti 5 `blouse`→rs 115**, gti 10 `top_sleeveless`→rs 186,
gti 58 `baby_dress`→rs 87. **3 de les 4 (84, 186, 87) no tenen el pointer invers V2** → V1 i V2
divergeixen en 3 de 4 casos.

### B2.3 (b) `GradingRuleSet.targets` (M2M)

Through **implícit** (auto-taula `fhort.pom_gradingruleset_targets`) — no hi ha model through explícit.
Migració `pom/migrations/0009_gradingset_targets_m2m_decimal2.py:14-18` (afegeix M2M) i `:29-33`
(renomena el `related_name` del FK a `*_legacy`). **NO hi ha cap data-migration FK→M2M** — contrast
directe: `pom/migrations/0021_remove_sizesystem_target_sizesystem_targets.py:20-25` **sí** la va fer
per a `SizeSystem`.

| Rol | `ruta:línia` |
|---|---|
| ESCRIPTOR | `pom/size_map_views.py:862`, `:869` (`rule_set.targets.add`) |
| ESCRIPTOR | `pom/grading_utils.py:400` (`new_rule_set.targets.add`) — **dins funció morta** (§B2.5) |
| ESCRIPTOR | `models_app/extraction_views.py:2023` (`container.targets.add`) |
| ESCRIPTOR | `pom/serializers.py:287` (`targets` escrivible via API) |
| ESCRIPTOR (seeds) | `seed_losan_grading_v3.py:169`, `seed_losan_master_delta.py:159`, `load_losan_package.py:378-379` |
| LECTOR | `pom/serializers.py:239` (`targets_codis`), `:242` (`target_codi = targets.first()`), `:275` (guard system_default) |
| LECTOR | `pom/serializers.py:114`, `models_app/serializers.py:197` |
| LECTOR (matcher backend) | `pom/grading_utils.py:115` (`targets=tgt`), **`:641` (`base_qs.filter(targets__codi=target)`)** |
| LECTOR (frontend) | `gradingAxes.js:72-73` (`matchesTarget`), `:105-108`, `:155`, `:172` |

**Distribució de targets per ruleset (45):** 0 targets → **1** (rs 98) · 1 target → **36** ·
2 targets → **4** (88, 89, 90, 178) · 3 targets → **4** (87, 175, 176, 177).

### B2.4 (c) `SizingProfile` — la cascada

**Model:** `pom/models.py:912-947`. Identitat *de fet* =
`target + garment_type + construction + fit_type` (+ `size_system`, `customer`). **Cap unique constraint.**

**Resolució:** `pom/s2_views.py:70-128` (`sizing_profiles_view`, `GET /api/v1/sizing-profiles/`) —
filtres per `target__codi`/`construction__codi`/`fit_type__codi|fit_type_id`/`garment_type_id`
(`:96-105`), i **ordenació per prioritat de client** a `_grup()` (`:107-116`): **0** = perfil del
client (FK `customer_id` o senyal indirecte `size_system.customer_codi`) · **1** = canònic genèric
(`is_default and customer is None`) · **2** = la resta. **Dins d'un mateix grup no desempata** més
enllà de `size_system.nom` (`:117-120`).
Altres punts de resolució: `pom/size_map_views.py:931-950` (identitat d'escriptura),
`pom/s2_views.py:221-235` (clon), `pom/s4_views.py:164-185`.

**Duplicats indesambiguables per la cascada, avui: 2 col·lisions / 5 perfils.**

| target | garment_type | constr. | fit | perfils | rulesets | system | customer |
|---|---|---|---|---|---|---|---|
| BABY_GIRL | Newborn | KNIT | REGULAR | **539, 540, 541** | 175, 176, 177 | 62 | 6 (LOS) |
| WOMAN | T-shirt | STRETCH_KNIT | SLIM | 288, 510 | 81, 98 | 29 | NULL |

539/540/541 **confirma R20**: `is_default=false` totes tres, mateix client, mateix sistema → `_grup()`
les posa totes al grup 0 i **l'ordre final és arbitrari**. 288/510 sí es desempaten (`is_default` /
`parent_profile`: 510 és versió 2 de 288).
**12 rulesets de 45 no tenen cap `SizingProfile`** (inclou rs 214 — R20).

### B2.5 Punt 7 — qui alimenta el `RuleSetPicker`

**Component únic:** `frontend/src/components/grading/RuleSetPicker.jsx` (`:19-25` props; `:27-31`
tria el matcher segons `strict`).
**Endpoint únic per als DOS wizards:** `GET /api/v1/grading-rule-sets/?page_size=200&amb_regles=1`
(`frontend/src/api/endpoints.js:203`).
**Queryset backend:** `pom/views.py:170-175` —
`GradingRuleSet.objects.select_related('garment_group','size_system').prefetch_related('regles').all()`;
**cap filtre per item, ni per target, ni per client**. L'únic filtre és a `views.py:181-188`:
`?amb_regles=1` → `annotate(n_regles=Count('regles')).filter(n_regles__gt=0)`.

> **TROBALLA TRANSVERSAL:** **tot el filtratge real és 100% frontend.** El backend serveix el catàleg
> sencer i el navegador decideix. (Nota d'evolució: el `amb_regles=1` que
> `DIAGNOSI_AUTOMATISME_ITEM_GRADING_2026-07-19.md §5` demanava com a proposta **ja està implementat**
> a `pom/views.py:181-188`.)

| | (a) Wizard de MODEL | (b) Wizard d'ITEM |
|---|---|---|
| Pàgina | `ModelWizard.jsx:689-698` | `ItemAuthoring.jsx:260-269` |
| Càrrega | `ModelWizard.jsx:252` | `ItemAuthoring.jsx:81` |
| Matcher | **`strict`** → `gradingAxes.js:151-163` (`matchingRuleSetsStrict`) | **lenient** → `gradingAxes.js:134-144` (`matchingRuleSets`) |
| Eixos | `ModelWizard.jsx:274-279` (`nodeAxes` amb `garmentTypeId` **i** `garmentTypeItemId`) + `:288` fit | `ItemAuthoring.jsx:59` + `CascadeSelector maxLevel="group"` (`:256`) → `garmentTypeId`/`garmentTypeItemId` **sempre null** |
| **Vincles que generen la llista** | **V3** (`targets_codis`, `gradingAxes.js:155`) + **V4/`garment_group`** (`scopeApplies`, `:88-102`) + `size_system` (`:161`) | **V3** + **V4/`garment_group`** (`scopeApplies` lenient) |
| Acció | `onPick` → `gradingRuleSetId` → `Model.grading_rule_set` (`ModelWizard.jsx:339,348`) | `onPick` → **V1** (`ItemAuthoring.jsx:135-136`) |

**Cap dels dos pickers llegeix V1 ni V2 per construir la llista.** V1 només hi apareix com a
**destinació** de l'escriptura i per ressaltar `selectedId`. **V2 no hi apareix mai.**

**El cas real del `blouse`** (gti=5, `garment_type` 63 «Buttoned Tops», `grup='TOPS'`; V1→115; V2 de
115→5). Aplicant literalment `matchingRuleSets` (lenient, `amb_regles=1`) amb eixos
`{WOMAN, WOVEN, REGULAR, garmentGroup:'TOPS'}` sobre les dades d'avui surten **4**:

| rs | nom | per què entra |
|---|---|---|
| 75 | EU Woven Woman Regular | **comodí**: `garment_group IS NULL`, cap scope-node → `matchesGarmentGroup` retorna `true` (`gradingAxes.js:77-80`) |
| 91 | EU Woven Woman Numeric | **comodí** (íd.) |
| 124 | Prova BRW ALPHA UE | **comodí** (íd.) |
| **115** | **BRW · Blusa · ALPHA_EU_W** | **V4** — scope-node `GROUP TOPS` (id 32) |

- **Tres de quatre candidats no tenen res a veure amb l'item**: hi entren per absència d'eix.
- **El contenidor correcte (115) hi entra per V4**, no per V1 ni V2.
- **108 queda fora** per `amb_regles=1` (0 regles) — la porta que va causar el símptoma del 163 ja
  no és oberta al picker.
- Si el grup triat fos `TOPS-WOVEN` (codi 5, existent a `pom_garmentgroup`) en comptes de `TOPS`
  (codi 7), la llista seria **exactament 3: 75, 91, 124** — i **el contenidor correcte
  desapareixeria**, perquè l'únic node de grup de 115 és `TOPS`. És l'única combinació que reprodueix
  els "3 candidats" de la pantalla. **PENDENT DE VERIFICAR** sense la traça de la sessió d'Agus.
- En mode **strict** (wizard de model, `size_system=29`) la llista per al blouse és **1** (només 115):
  75/91/124 cauen perquè `scopeApplies(strict)` exigeix `garment_group` explícit
  (`gradingAxes.js:90-92`).

> **La lectura incòmoda:** la pertinença real del ruleset correcte al `blouse` penja d'**un sol
> `RuleSetScopeNode`**, i el ventall que veu el tècnic està dominat per **rulesets que hi entren per
> no tenir eix**. El ventall no s'ha de "consolidar" perquè sigui redundant, sinó perquè **avui és
> alhora massa ample (comodins) i massa fràgil (un node)**.

### B2.6 Punt 8 — R21 refrescat

**Divergències FK `target` ↔ M2M `targets` a `fhort`, avui: 10** (idèntic al 21/07).

| rs | nom | FK `target_id` | M2M | no representable per FK |
|---|---|---|---|---|
| 87 | EU Knit Baby Regular | 6 | {4,5,6} | ✅ |
| 88 | EU Knit Toddler Regular | 8 | {7,8} | ✅ |
| 89 | EU Knit Kids Regular | 10 | {9,10} | ✅ |
| 90 | EU Knit Teen Regular | 12 | {11,12} | ✅ |
| 93 | EU Knit Baby Months | **NULL** | {6} | — (FK buida, M2M plena) |
| 98 | Custom Alpha EU — Women | 1 | **{}** | — (FK plena, M2M buida) |
| 175 | LOS New Born Knit — Tops | 4 | {4,5,6} | ✅ |
| 176 | LOS New Born Knit — Bottoms | 4 | {4,5,6} | ✅ |
| 177 | LOS New Born Knit — Onepieces | 4 | {4,5,6} | ✅ |
| 178 | LOS Baby Knit — Tops | 7 | {7,8} | ✅ |

**8 no representables** per una FK singular (>1 target). `los`: 0 files, res a migrar.

#### **«`grading_utils.py:339` és l'únic lector decisori» — DESMENTIT**

`derive_grading_rule_set` (`pom/grading_utils.py:251`), que conté el filtre `target=rs_target` a
`:339`, **no té CAP cridador viu**:

```
grep -rn "derive_grading_rule_set" --include=*.py --include=*.js --include=*.jsx .
→ grading_utils.py:20,90,93,129 (docstrings) · :251 (def) · :430,456 (comentaris) ·
  models_app/extraction_views.py:1844 (COMENTARI, no crida)
```

El seu propi capçal ho declara: `grading_utils.py:430` — *"`derive_grading_rule_set` (sobre) queda
**JUBILAT** com a CREADOR automàtic"*. El camí d'import viu és
`extraction_views.py:1889,1907` → `resolve_grading_container` (`grading_utils.py:577-651`), que
**ja filtra per M2M** (`:641`).

> **R21 es reclassifica: de "FK legacy que encara decideix" a "codi mort amb un filtre obsolet a
> dins".** Baixa de 🟡 Mitjà a 🟢 Baix com a **risc**, però continua sent deute: el FK segueix
> **rebent escriptures** des de 4 punts vius.

**Lectors/escriptors REALS del FK legacy `GradingRuleSet.target`:**

| `ruta:línia` | Rol | Viu? |
|---|---|---|
| `pom/models.py:566-570` | definició FK (`related_name='grading_rule_sets_legacy'`) | sí |
| `pom/grading_utils.py:329,339` | **lector decisori** (`filter(target=rs_target)`) | ❌ **MORT** (sense cridadors) |
| `pom/size_map_views.py:842-843` | **ESCRIPTOR** `rule_set.target = target` + `save(update_fields=[...])` | ✅ |
| `pom/size_map_views.py:858` | **ESCRIPTOR** `create(..., target=target, ...)` | ✅ |
| `pom/s2_views.py:195` | **ESCRIPTOR** clon de perfil: `target=original_rs.target` | ✅ |
| `models_app/extraction_views.py:2005-2006,2022` | **ESCRIPTOR** `create(..., target=rs_target...)` — hi **conviu** amb `targets.add` a `:2023` | ✅ |
| `pom/serializers.py:194,241-243` | `target_codi` **ja es calcula des de `targets.first()`**, no del FK | ✅ |
| **Frontend** | `grep -rn "\.target\b\|target_codi" frontend/src` → **cap ús del FK**; el front només consumeix `targets_codis` i el `target_codi` serialitzat des del M2M | — |

*(Nota anti-fals-positiu: `pom/s2_views.py:222`, `pom/size_map_views.py:996`,
`export_losan_package.py:334` i `extraction_views.py:706,744,1662,1789,1908,2005` són
`SizingProfile.target` o `Model.target` — **no** el FK del ruleset.)*

**Què costaria completar la migració FK→M2M (fets, no proposta):**

1. **Data-migration inexistent** — `pom/migrations/0009_…py` no en va fer cap. Patró disponible:
   `pom/migrations/0021_remove_sizesystem_target_sizesystem_targets.py:16-30`. Ha de cobrir els 2
   casos asimètrics: rs 98 (FK→M2M) i rs 93 (ja només M2M).
2. **Reescriure 4 punts d'escriptura** a `targets.set/add`: `pom/size_map_views.py:842-843`, `:858`;
   `pom/s2_views.py:195`; `models_app/extraction_views.py:2005-2006` (aquest ja fa `targets.add` a `:2023`).
3. **Esborrar codi mort**: `pom/grading_utils.py:251-423` sencer (inclou `:329`, `:339`, `:400`) i el
   DEUTE anotat a `:93-95`.
4. `RemoveField` de `pom/models.py:566-570`.
5. **Frontend: res a tocar** — ja va per M2M.

### B2.7 Punt 9 — rulesets LOSAN sense `garment_type_item`

**Estat exacte:** al schema `los` **NO EXISTEIX cap ruleset** (schema buit sencer). Els rulesets LOSAN
són a `fhort` amb `customer_id=6`: **20 de 20 amb `garment_type_item IS NULL` (0 backfillats)**. A
tot `fhort`, **només 1 ruleset de 45** té el camp informat (rs 115, client BRW).

| rs | nom | size_system | scope-nodes ITEM | models | items dels models |
|---|---|---|---|---|---|
| 104 | LOS Kids Knit Regular 2Y-12Y | GIRL_LOS_03 | — | **0** | — |
| 175 | LOS New Born Knit — Tops | NEWBORN_LOS_01 | **56, 57** | 5 | 12, 16 |
| 176 | LOS New Born Knit — Bottoms | NEWBORN_LOS_01 | **55, 59** | **0** | — |
| 177 | LOS New Born Knit — Onepieces | NEWBORN_LOS_01 | **53, 54, 72** | 24 | 58 |
| 178 | LOS Baby Knit — Tops | BABY_LOS_01 | **56, 57** | 53 | 9, 12, 16, 57 |
| 179 | LOS Kids Girl — Dresses | GIRL_LOS_01 | — (grup DRESSES) | 32 | 28 |
| 180 | LOS Kids Boy Woven — Bottoms | BOY_LOS_01 | — (BOTTOMS) | 40 | 18, 20, 21 |
| 181 | LOS Teen Boy Knit — Tops | YOUTH_BOY_LOS_01 | — (TOPS) | 42 | 8, 9, 16 |
| **182** | LOS Teen Boy Woven — Shirts | YOUTH_BOY_LOS_01 | — (TOPS) | 4 | **4** (únic) |
| 183 | LOS Teen Boy Woven — Bottoms | YOUTH_BOY_LOS_01 | — (BOTTOMS) | 30 | 18, 20, 21 |
| 184 | LOS Teen Girl — Bottoms | YOUTH_GIRL_LOS_01 | — (BOTTOMS) | 45 | 18, 20, 21, 26 |
| **185** | LOS Teen Girl Stretch — Swimwear | YOUTH_GIRL_LOS_01 | — (SWIMWEAR) | 13 | **43** (únic) |
| 186 | LOS Woman Knit — Tops | WOMAN_LOS_01 | — (TOPS) | 42 | 8, 9, 12 |
| 187 | LOS Woman Woven — Bottoms | WOMAN_NUM_LOS_01 | — (BOTTOMS) | 49 | 18, 20, 21, 26 |
| 188 | LOS Man Woven — Bottoms | MAN_NUM_LOS_01 | — (BOTTOMS) | 35 | 18, 20, 21 |
| 210 | LOS Man Knit — Tops | MAN_LOS_01 | — (TOPS) | 48 | 8, 9, 16 |
| 211 | LOS Teen Girl Knit — Tops | YOUTH_GIRL_LOS_01 | — (TOPS) | 39 | 8, 9, 12, 16 |
| 212 | LOS Kids Boy Knit — Tops | BOY_LOS_01 | — (TOPS) | 41 | 8, 9, 12, 16 |
| 213 | LOS Kids Girl Knit — Tops | GIRL_LOS_01 | — (TOPS) | 38 | 8, 12, 16 |
| 214 | LOSAN IBERIA SA · Newborn · LOS Baby 3-36M | BABY_LOS_01 | — (NEWBORN) | 1 | 58 |

*(tots amb `fit_type=REGULAR` excepte rs 104, que el té **NULL**)*

**Deduïbilitat de l'item — els fets:**
- **2 de 20** (182→item 4, 185→item 43) tenen un item **únic** derivable dels models.
- **13 de 20** tenen **3+ items** als seus models: no hi ha *un* item, hi ha un **conjunt**.
- **2** (104, 176) no tenen cap model **ni** cap senyal fora del nom (176 sí té scope-nodes).
- **4** (175, 176, 177, 178) **ja porten l'abast real a `RuleSetScopeNode`**, i el conjunt **no cap en
  una FK singular** (175→2 items, 177→3, 178→2).

**Què implicaria backfillar-los** (`ruta:línia` dels llocs que en dependrien):

| `ruta:línia` | Efecte del backfill |
|---|---|
| `pom/grading_utils.py:614-624` | NIVELL 1 del matcher (`garment_type_item=` exacte): avui **mai s'activa** per LOSAN |
| `pom/grading_utils.py:632-635` | NIVELL 2 filtra `garment_type_item__isnull=True` → **el backfill trauria els 20 rulesets del NIVELL 2**, l'únic pel qual són accessibles avui |
| `pom/models.py:544-547` + `pom/migrations/0039_…py:20-23` | la constraint `uniq_client_container_identity` és avui **inert** (Postgres `NULLS DISTINCT`). Backfillada, **col·lidiria** en 6 grups que comparteixen `(customer=6, size_system, fit=REGULAR)`: NEWBORN {175,176,177} · BABY {178,214} · YOUTH_BOY {181,182,183} · YOUTH_GIRL {184,185,211} · GIRL {179,213} · BOY {180,212} — només es compleix si l'item assignat és **diferent** dins de cada grup |
| `pom/grading_utils.py:535-555` | `cerca_contenidor_client` (**DEPRECADA**), cridada des de `pom/size_map_views.py:718,731` |
| `pom/size_map_views.py:829-831,860` | escriptor de `garment_type_item` (des del payload) |
| `models_app/extraction_views.py:2018-2022` | **crea contenidors amb `garment_type_item=None` per defecte** (comentari «AMPLI»): el camí que **continua generant** rulesets sense item |

> **Veredicte B2:** de les tres vies del brief n'hi ha **cinc**, i **cap dels dos `RuleSetPicker` no
> llegeix V1 ni V2**: la llista la generen **V3 + V4** sobre un endpoint sense filtre
> (`pom/views.py:170-188`), i per al `blouse` els candidats genèrics hi entren **per comodí d'eix
> NULL**. **V1 queda confirmada com a fulla morta aigües avall** (zero consumidors del
> `related_name`). **R21 es reclassifica**: les 10 divergències són intactes però
> `grading_utils.py:339` **ja no decideix res** — el FK `target` només sobreviu com a **escriptura** a
> 4 punts. I **el backfill LOSAN literal és impossible**: 13 de 20 rulesets serveixen un **conjunt**
> d'items, no un item.

---

## PUNT 10 — 💡 PROPOSTA DE CONSOLIDACIÓ (a validar — NO és decisió)

### La restricció d'Agus, traduïda a requisits verificables

> *"El PM ha de poder definir assignacions múltiples sense trencar cap lògica, i el tècnic les troba
> al model."*

| Requisit | Quin vincle el compleix AVUI |
|---|---|
| **R-a** · un ruleset pot aplicar a **N** items | **V4** (`RuleSetScopeNode`, multi-node) — únic. V2 és FK singular; V1 és a l'altra banda |
| **R-b** · un item pot oferir **N** rulesets | **V4** (N nodes de N rulesets apunten al mateix item) — únic. V1 és FK singular |
| **R-c** · el tècnic els troba **al model** | el `RuleSetPicker` del wizard de model — que consumeix **V3 + V4** |
| **R-d** · un **suggerit per defecte** per item | **V1** — l'únic amb la cardinalitat correcta (1 item → 1 ruleset preferent) |
| **R-e** · **identitat** del contenidor de client (no ventall) | **V2** + `uniq_client_container_identity` + matcher N1/N2 (`grading_utils.py:614-635`) |

**Els cinc vincles no competeixen pel mateix rol: en compleixen tres de diferents.** El que hi ha
avui no és redundància — és **un rol sense amo declarat** (el ventall) i **dos camps que fan de
documentació** (V1, V2).

### 💡 Proposta principal — «un rol, un vincle»

| Vincle | Rol proposat | Per què |
|---|---|---|
| **V4 `RuleSetScopeNode`** | **FONT ÚNICA DEL VENTALL** | és l'únic amb cardinalitat N↔N (R-a + R-b); **ja alimenta els dos pickers** (`gradingAxes.js:88-102`); ja és la llei d'aplicabilitat multi-node vigent; té granularitat GROUP/TYPE/ITEM, que és exactament l'eix del PM |
| **V1 `GarmentTypeItem.grading_rule_set`** | **SUGGERIT PER DEFECTE** (es queda, canvia de sentit) | cardinalitat correcta per a "el preferent"; **ja s'escriu des d'`ItemAuthoring` amb gate `CONFIGURE`**; avui no el llegeix ningú → donar-li el seu **primer lector real** és additiu i no trenca res |
| **V2 `GradingRuleSet.garment_type_item`** | **IDENTITAT del contenidor de client** — **NO es jubila, però surt del ventall** | forma part de `uniq_client_container_identity` i del NIVELL 1 del matcher (`grading_utils.py:614-624`). Jubilar-lo trencaria la llei del contenidor acumulatiu. **El que cal és declarar que no és un mecanisme de ventall** |
| **V3 FK legacy `target`** | **JUBILAR** | codi mort aigües avall (§B2.6); el M2M `targets` es queda com a **eix de filtre**, no com a vincle a l'item |
| **V5 `SizingProfile`** | **fora del ventall** (preset de biblioteca) | ja decidit a `DIAGNOSI_5CAPES_PROCES.md` §2: el pas Talles és escala pura i el perfil no ha d'arrossegar graduació. Els 5 perfils indesambiguables (R20) són higiene, no ventall |

**El que aquesta proposta canvia de veritat, en una frase:** avui el ventall el determina
**l'absència d'eixos** (comodins `garment_group=NULL`); amb V4 com a font única el determina la
**pertinença declarada**.

**Cost per peça:**

| Peça | Dimensió | Detall |
|---|---|---|
| Declarar V4 com a font del ventall | **PETIT** | ja hi és; és sobretot **llei escrita** + treure el comodí de `gradingAxes.js:77-80` en mode lenient |
| **Poblar V4** (només 6 rulesets de 45 tenen nodes) | **MITJÀ** | **la peça real**. Sense nodes, endurir el comodí **buida** els pickers. Cal sembrar nodes abans de tancar el comodí — mai al revés |
| Donar lector a V1 (suggerit per defecte) | **PETIT** | preseleccionar al `RuleSetPicker` del wizard de model; l'eco natural de `ModelWizard.jsx:70` («aquí NO s'arrossega») és que **suggerir ≠ arrossegar** |
| Jubilar el FK `target` | **PETIT-MITJÀ** | els 5 passos de §B2.6 |
| Higiene V5 (R20) | **PETIT** | desempatar 539/540/541 |
| Backfill V2 LOSAN | **veure punt 11** | **no fer-lo en la forma literal** |

### 💡 Alternatives, per completesa

| Opció | Què implica | Cost | Risc |
|---|---|---|---|
| **B · V1 passa a M2M** (`GarmentTypeItem.grading_rule_sets`) | el ventall viu al costat de l'item | **MITJÀ** (migració + backfill des de V4 + UI) | **duplica V4**: dues taules N↔N per al mateix concepte. Contradiu D4 el mateix dia que la invoca |
| **C · V2 passa a M2M** | el ventall viu al costat del ruleset | **GRAN** | **trenca `uniq_client_container_identity`** i el NIVELL 1 del matcher. Radi: la llei del contenidor acumulatiu |
| **D · no consolidar; documentar els rols** | zero codi | **NUL** | el ventall segueix determinat per comodins; el `blouse` seguirà mostrant 3 candidats aliens i el ruleset correcte seguirà penjant d'un sol node |

> **Per què B i C no es recomanen:** V4 ja és la resposta N↔N i **ja està cablat als dos pickers**. B
> i C construeixen un segon mecanisme per al mateix rol el mateix dia que la llei D4 diu «un sol
> mecanisme».

### ⚠️ El guard que la consolidació ha de portar de sèrie

**Endurir el comodí sense poblar V4 buidaria els pickers.** Amb 6 rulesets de 45 amb scope-nodes, si
`matchesGarmentGroup` (`gradingAxes.js:77-80`) deixa de retornar `true` per a `garment_group=NULL`, el
wizard de model passa a oferir **només els rulesets amb node**. **L'ordre és inamovible: primer
poblar V4, després tancar el comodí, i mai el contrari** — la mateixa classe d'error que R1 (esborrar
sense saber què es crearà, `models_app/services.py:156,168`).

---

## PUNT 11 — COST I ORDRE (BLOC B3)

### 11.1 Dimensió per peça

| # | Peça | Dimensió | Per què |
|---|---|---|---|
| **P0** | **Gate `CONFIGURE` a la porta de la promoció** | **PETIT** | el patró ja existeix a 2 llocs (`pom/views.py:320-325`, `tasks/views_b.py:874-878`). *No* proposa re-gatejar `materialize_poms_view` ni `confirmar/` (radi fora d'abast): només que **l'endpoint nou neixi gated** |
| **P1** | **Guard de coherència de talla** (`base_size_definition` ↔ `Model.base_size_label`) | **PETIT** | 1 comparació a `models_app/views.py:930-968` + 1 a la promoció. **Tanca una fuga silenciosa que ja és viva** |
| **P2** | **Acte de PROMOCIÓ model→item** (endpoint + dry-run/diff + UI) | **MITJÀ** | l'esquelet backend és especular de `views.py:877-979`; el cost és el **diff + confirmació** i la superfície UI, que **no existeix** |
| **P3** | **`base_size_definition` escrita a la promoció** | **PETIT** (dins P2) | ha de passar per `clean()` (`tasks/models.py:336-343`): coherència amb el `size_system` del ruleset de l'item |
| **P4** | **Poblar `RuleSetScopeNode` (V4)** | **MITJÀ** | 6 de 45 rulesets tenen nodes; 20 LOSAN en tenen 4. És **dades + criteri de domini**, no codi |
| **P5** | **Endurir el comodí de `garment_group`** | **PETIT de codi, ALT de risc si va abans de P4** | `gradingAxes.js:77-80`, `:88-102` |
| **P6** | **V1 com a suggerit per defecte** (donar-li lector) | **PETIT** | preselecció al picker del wizard de model |
| **P7** | **Jubilar el FK `target`** (R21) | **PETIT-MITJÀ** | 5 passos de §B2.6; frontend intacte |
| **P8** | **Backfill LOSAN de V2** | **NO FER en forma literal** → **PETIT** com a **higiene de V4** | 13/20 serveixen un conjunt; 4 ja tenen nodes; el backfill col·lidiria amb `uniq_client_container_identity` en 6 grups i trauria els 20 del NIVELL 2 |
| **P9** | **Camp `origen` + timestamps a `ItemBaseMeasurement`** | **PETIT** (migració additiva) | condició tècnica de qualsevol política de conflicte que no sigui "sobreescriure tot" |
| **P10** | **Cobertura de test d'`ItemBaseMeasurement`** | **PETIT-MITJÀ** | **NO EXISTEIX cap test** del model ni de l'endpoint (re-verificat) |

### 11.2 Ordre de dependència

```
  ┌─ CAMÍ A · LA PLANTILLA S'ALIMENTA ──────────────────────────────────────┐
  │                                                                         │
  │  P1 guard de talla        ← independent, PETIT, tanca una fuga VIVA      │
  │      │                       (fer-lo primer encara que P2 no es faci)   │
  │      ▼                                                                  │
  │  D-PROM · LA DECISIÓ (§B1.4)   ← Patró C. BLOQUEJA P2                    │
  │      │      política de conflicte + la llei que falta                    │
  │      ▼                                                                  │
  │  P9 origen/timestamps  ──►  P0 gate  ──►  P2 promoció  ──►  P3 talla base│
  │  (només si la política                          │                       │
  │   escollida ho exigeix)                         ▼                       │
  │                                            P10 tests                    │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─ CAMÍ B · EL VENTALL ES CONSOLIDA ──────────────────────────────────────┐
  │                                                                         │
  │  D-CONS · LA DECISIÓ (§punt 10)   ← Patró C. BLOQUEJA P4/P5/P6          │
  │      │                                                                  │
  │      ▼                                                                  │
  │  P4 poblar V4  ──────►  P5 endurir comodí   ← ORDRE INAMOVIBLE          │
  │      │                       (al revés = pickers buits)                 │
  │      ├──► P6 V1 suggerit                                                │
  │      └──► P8 higiene LOSAN via V4 (NO backfill de V2)                   │
  │                                                                         │
  │  P7 jubilar FK target   ← independent de tot; deute mort                │
  └─────────────────────────────────────────────────────────────────────────┘
```

**Els dos camins són independents entre si.** No comparteixen cap fitxer: A viu a
`models_app/views.py` + `pom/views.py` + `MeasurementBaseGrid.jsx`; B viu a `gradingAxes.js` +
`pom/models.py` + `grading_utils.py`. **Es poden fer en paral·lel o en qualsevol ordre relatiu.**

**Justificació dels tres punts durs:**

1. **P1 primer i sol.** És l'únic defecte d'aquesta diagnosi que **ja fa mal avui**, i és una
   comparació. Mentre visqui, poblar la plantilla (que és tot l'objectiu del paquet) **n'amplifica el
   dany**: amb 37 files en 1 item el risc és teòric; amb la plantilla poblada, no.
2. **Cap escriptura a la capa Item abans de D-PROM.** No per prudència: perquè la política de
   conflicte **determina l'esquema** (P9). Escriure la promoció amb "sobreescriure tot" i després
   decidir "merge per POM" obliga a refer-la.
3. **P4 abans de P5, sense excepció.** Endurir el comodí amb 6/45 rulesets amb node buida els pickers
   — mateixa classe d'error que R1.

---

## TAULA FINAL — EXISTEIX / FALTA / DIFERENT

| Peça | Estat | Evidència |
|---|---|---|
| Escriptura automàtica a `ItemBaseMeasurement` (import o qualsevol camí) | **NO EXISTEIX** | grep 24 hits; cap a `extraction_views.py`; `bootstrap_tenant.py:132-160` no l'inclou |
| Escriptors reals d'`ItemBaseMeasurement` | **EXISTEIX** — 2 (ViewSet `CONFIGURE` + loader CLI) | `pom/views.py:304-360`, `load_losan_package.py:356` |
| `derive_grading_rule_set` com a creador de l'import | **DIFERENT — JUBILAT** (i sense cap cridador) | `grading_utils.py:430`; `extraction_views.py:1844` és comentari |
| Camí d'import viu de grading | **EXISTEIX** — `resolve_grading_container` N1/N2/N3 | `extraction_views.py:1903-1907` → `grading_utils.py:577-651` |
| Talla base del document persistida fora del model | **NO EXISTEIX** | només `Model.base_size_label` (`extraction_views.py:689-691`) + `GradingRule.talla_base` |
| Acte de PROMOCIÓ model→item (codi) | **NO EXISTEIX** | cap `update_or_create` cap a `ItemBaseMeasurement` fora de `pom/views.py:354` |
| Botó "importar del model X" al wizard d'item | **NO EXISTEIX** | grep `importar del model\|import_from_model\|fromModel` → 0 hits |
| Gate `CONFIGURE` a `confirmar/` i `materialize_poms_view` | **DIFERENT — `IsAuthenticated`** | `extraction_views.py:1717`, `models_app/views.py:876` |
| Guard de conflicte a l'`upsert` d'`ItemBaseMeasurement` | **NO EXISTEIX** | `pom/views.py:350-355`, `defaults` pla |
| Camp `origen` / timestamps / autoria a `ItemBaseMeasurement` | **NO EXISTEIX** | `pom/models.py:464-501` |
| Taula de precedència d'orígens (qualsevol capa) | **NO EXISTEIX** | únic guard per origen del repo: `dictionary_service.py:158` |
| `GarmentTypeItem.base_size_definition` — lector de negoci | **NO EXISTEIX** (0 hits) | només display, `clean()`, export, UI |
| Guard talla item ↔ talla model a la sembra | **NO EXISTEIX** | `models_app/views.py:930-968` |
| Vincles item↔ruleset | **DIFERENT — en són 5, no 3** | V1..V5, §B2.1 |
| `GarmentTypeItem.grading_rule_set` (V1) com a fulla morta | **CONFIRMAT** | 0 consumidors del `related_name`; lectors = semàfor + hidratació |
| `GradingRuleSet.garment_type_item` (V2) | **EXISTEIX** i és **identitat**, no ventall | `pom/models.py:544-547` + `uniq_client_container_identity` |
| Font real del ventall del `RuleSetPicker` | **DIFERENT — V3 + V4**, amb comodí d'eix NULL | `pom/views.py:170-188`, `gradingAxes.js:77-80,88-102` |
| Filtre `amb_regles=1` al picker | **EXISTEIX** (era proposta el 19/07) | `pom/views.py:181-188`, `endpoints.js:203` |
| `grading_utils.py:339` com a lector decisori (R21) | **DESMENTIT — codi mort** | `derive_grading_rule_set` sense cridadors |
| Escriptures vives al FK legacy `target` | **EXISTEIX** — 4 punts | `size_map_views.py:842,858`, `s2_views.py:195`, `extraction_views.py:2005` |
| Data-migration FK→M2M de `targets` | **NO EXISTEIX** | patró disponible a `pom/migrations/0021_…py:16-30` |
| Backfill LOSAN de `garment_type_item` (forma literal) | **IMPOSSIBLE** — 13/20 serveixen un conjunt | §B2.7 |
| Schema `los` | **BUIT** (0 GTI, 0 rulesets, 0 perfils) — confirma R25 | SELECT |
| Tests d'`ItemBaseMeasurement` | **NO EXISTEIX** | re-verificat |

### Riscos per al CTO

| # | Risc | `ruta:línia` | Gravetat |
|---|---|---|---|
| 1 | **La sembra item→model no comprova la talla**: valors `ITEM_STANDARD` poden aterrar expressats en una talla base diferent de la del model, **en silenci** | `models_app/views.py:930-968` vs `tasks/models.py:306-310` | **ALTA** (latent avui: 37 files / 1 item; **activa el dia que la plantilla es pobli**) |
| 2 | **L'`upsert` d'`ItemBaseMeasurement` sobreescriu sense cap guard**, i el model no té `origen` ni timestamps → una promoció mal dirigida és **irrecuperable i anònima** | `pom/views.py:350-355`, `pom/models.py:464-501` | **ALTA** (si es construeix la promoció sense P9) |
| 3 | **Els dos camins candidats de la promoció estan gated a `IsAuthenticated`** mentre la capa Item exigeix `CONFIGURE` | `extraction_views.py:1717`, `models_app/views.py:876` | **MITJANA** |
| 4 | **El ventall del picker el determinen els comodins**: 3 de 4 candidats del `blouse` hi entren per `garment_group=NULL`, i el correcte penja d'**un sol scope-node** | `gradingAxes.js:77-80`; rs 115 node id 32 | **MITJANA** |
| 5 | **Endurir el comodí abans de poblar V4 buidaria els pickers** (6 rulesets de 45 tenen nodes) | `gradingAxes.js:88-102` | **MITJANA** (d'execució) |
| 6 | **El FK legacy `target` segueix rebent escriptures** des de 4 punts vius mentre el seu únic lector és codi mort → les divergències creixen | `size_map_views.py:842,858`, `s2_views.py:195`, `extraction_views.py:2005` | **BAIXA** (R21 reclassificat) |
| 7 | **`extraction_views.py:2018-2022` continua creant contenidors amb `garment_type_item=None`** → el forat de V2 s'eixampla a cada import amb `create` | `extraction_views.py:2018-2022` | **BAIXA** |
| 8 | **5 `SizingProfile` indesambiguables** (539/540/541 + 288/510) — l'ordre de la cascada és arbitrari | `pom/s2_views.py:107-120` | **BAIXA** (R20, ja conegut) |
| 9 | `ItemBaseMeasurement` **sense cap test** — la promoció seria la primera escriptura massiva sobre codi sense xarxa | grep sobre `test*.py` | **BAIXA** |

---

## LES DECISIONS (Patró C — per a l'Agus, **no decidides aquí**)

### D-PROM · La política de conflicte de la promoció (§B1.4)

Avui **no hi ha res**: cap codi de promoció, cap `origen` a la plantilla, cap precedència. Les quatre
formes possibles són a §B1.4 amb el seu precedent viu i el que exigeixen a l'esquema. El que aquesta
diagnosi hi aporta:

- **cap de les quatre és cara de codi** — la cara és **versionar** (taula/camps nous); les altres tres
  són guards;
- **la política determina l'esquema** (`origen`/timestamps, P9) → decidir **abans** de construir;
- **la promoció inverteix la direcció de la sobirania** i obliga a escriure la llei que hi falta:
  *l'estàndard del taller és un acte separat, explícit i `CONFIGURE`; mai un efecte secundari d'un
  import*. Sense escriure-la, la promoció i la norma inamovible 1
  (`extraction_views.py:1721-1731`) es contradiuen exactament com R13;
- **i hi ha una decisió germana amagada**: la promoció ha d'escriure també
  `base_size_definition` (P3)? És el moment on el sistema **sap** la talla; si no la fixa aquí,
  segueix sent una convenció no verificada (59/62 NULL).

### D-CONS · La consolidació del ventall (punt 10)

La proposta principal —**V4 = ventall · V1 = suggerit · V2 = identitat · FK `target` = jubilar ·
V5 = fora**— i les tres alternatives són a §punt 10 amb el seu cost. El que la diagnosi hi aporta:

- **els cinc vincles no competeixen: compleixen tres rols diferents.** El problema no és redundància,
  és **un rol sense amo** (el ventall) i dos camps que fan de documentació;
- **la restricció d'Agus (assignacions múltiples) només la satisfà V4**: V1 i V2 són FK singulars, i
  13 dels 20 rulesets LOSAN serveixen un **conjunt** d'items — la dada ja ho demostra;
- **el cost real no és declarar V4: és poblar-lo** (6 de 45), i l'ordre P4→P5 és inamovible;
- **V2 no es pot jubilar** sense trencar `uniq_client_container_identity` i el NIVELL 1 del matcher —
  el que cal és **declarar que no és un mecanisme de ventall**;
- **el backfill LOSAN en forma literal està descartat per la dada**, no per criteri.

---

*Diagnosi Patró A. Cap línia de codi tocada. Les propostes marcades `💡` no són decisions.*
