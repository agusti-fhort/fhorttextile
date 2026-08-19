# DIAGNOSI — la cadena taxonòmica Grup → Família → Item

Data: **2026-08-06** · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`, HEAD `1996e4f8`

**Abast:** la cadena `GarmentGroup → GarmentTypeGlobal/GarmentType → GarmentTypeItem` i tot el que se'n
deriva (POMs sembrats, sizing per defecte, target, fit, construcció), contrastada a totes les
superfícies que en parlen — codi, dades vives dels dos tenants (`fhort`, `los`) i ledger.

**Convenció:** cada afirmació porta `fitxer:línia`. **«NO EXISTEIX» = confirmat absent al codi/dades,
mai especulat.** Les propostes van marcades `💡 PROPOSTA (a validar)` i no són decisions.
Les xifres de BD són `SELECT` purs contra `ftt_staging` (127.0.0.1:5433).

> **Nota de nomenclatura del fitxer.** El brief demana `DIAGNOSI_TAXONOMIA.md`; la convenció de
> `patro-a` és `DIAGNOSI_<TEMA>_<DATA>.md`. S'ha seguit el brief.

---

## RESUM EXECUTIU

1. **El vocabulari del codi està desplaçat un nivell respecte del de la casa, i és el propi ORM qui ho
   fa.** `GarmentGroup.Meta.verbose_name = 'Família de garment'` (`backend/fhort/pom/models.py:639`)
   mentre `GarmentType.Meta.verbose_name = 'Tipus garment (tenant)'` (`pom/models.py:678`). El que la
   gent anomena **Grup** el codi l'anomena **Família**; el que anomena **Família** el codi l'anomena
   **Tipus**. **«Família» té 2 significats. «Tipus» en té 2. «Item» és l'únic mot estable** — i encara
   així es diu «Element» a Planning i «GTI» a Commerce.

2. **NO EXISTEIX cap camp de «run de talles per defecte» a cap nivell de la cadena.** Cens complet dels
   quatre nivells (§1.1): l'únic camp de run de tot el backend és `Model.size_run_model`
   (`backend/fhort/models_app/models.py:310-313`). **El run neix a la instància, mai al catàleg.** La
   pregunta «d'on va sortir el run kids» no té resposta al model de dades: la té al wizard.

3. **El cas del model de prova està TANCAT amb la fila real, i el mecanisme és el del pas 3 — però la
   versió VELLA del codi.** El model és `id=1307` (`BRW-SS26-0002`), creat **2026-08-04 16:43**,
   `target=KID_BOY`, `customer=BRW`, `size_system=BOY_LOS_01`, run `2·3·4·5·6·7·8·9/10·11/12`, base `6`,
   item `JERSEY_TOPS/t_shirt`. L'item **no té ni `base_size_definition` ni `grading_rule_set`**: el
   catàleg no hi va posar res. Ho va posar el wizard, amb tres línies i sense cap gest de l'usuari
   (`frontend/src/pages/ModelWizard.jsx:268,307,308`). ⚠️ **`ordenaPerProximitat` no existia el 04/08**
   (`1996e4f8`, 06/08 06:25 — 38 h després): el 04/08 el codi filtrava per target i agafava `rows[0]` en
   ordre alfabètic del backend, cosa que dona exactament `BOY_LOS_01` → `labels[4]='6'`. **Amb el bundle
   d'avui el mateix gest donaria base `7` i run d'11** (`KIDS_AGE_COM`) — el símptoma no desapareix,
   canvia de forma. 🚩 **Cal re-fer la QA sobre el bundle viu.**

4. **La fractura estructural: 12 superfícies ancoren a ITEM, 7 a FAMÍLIA, 2 a GRUP i 2 declaren els
   tres** (§3.4). El cas més car és `SizingProfile`, que decideix la compatibilitat target↔peça a
   **nivell FAMÍLIA** (`pom/models.py:1487-1488`) mentre el model tria un **ITEM**
   (`models_app/views.py:716-723`) → **dos items germans són indistingibles per a l'àmbit**.

5. **Tres premisses del brief han caigut, i cap altra eina parla l'eix vell.** `D-31.24` **NO EXISTEIX**
   (0 resultats a tot el repo, `arxiu/` inclòs); la decisió real del catàleg v2 és `DECISIONS.md:72-74`,
   sense numeració D-. `seed_pom_maps_to_items.py` **NO EXISTEIX** (ja censat). I de la migració
   `pom/0016`, **queda 1 sola eina viva amb l'eix mort i està desarmada amb un `raise` incondicional**
   (`reseed_tenant_fhort.py:313`, guard a `:82-89`). El «`:448`» del brief és un fals positiu:
   és `SizingProfile.garment_type`, camp viu i legítim.

6. **El dany real d'avui no és la migració: és el filtre excloent sobre un catàleg mig cobert.**
   **10 de les 17 famílies actives de `fhort` no tenen CAP `SizingProfile`** i, pel filtre `?target=`
   (`backend/fhort/pom/views.py:137-141`), **desapareixen del pas 2 per a qualsevol target: 31 items de
   catàleg invisibles**. I **21 dels 46 perfils (46 %) pengen de famílies desactivades**.

---

## BLOC 1 · EL MODEL DE DADES CANÒNIC (T1)

### 1.1 · La taula dels quatre nivells

| | **Grup** `GarmentGroup` | **Família global** `GarmentTypeGlobal` | **Família tenant** `GarmentType` | **Item** `GarmentTypeItem` |
|---|---|---|---|---|
| Fitxer | `pom/models.py:630` | `pom/models.py:80` | `pom/models.py:647` | `tasks/models.py:413` |
| **Clau estable** | `codi` **unique** `:633` | `codi` **unique** `:81` | `codi_client` — **NO unique, cap constraint** `:655` | `code` (Slug) — unique **només amb** `garment_type` `:461` |
| **Noms / llengües** | `nom` — **1 llengua** `:634` | `nom_en`+`nom_ca`+`nom_es`, obligatoris `:82-84` | `nom_client` `:656` + `nom_en`/`nom_ca`/`nom_es` opcionals `:661-663` | `name` — **1 llengua** `:420` |
| **Font i18n externa** | ❌ (vocabulari hardcodat al front) | ❌ | ❌ | ❌ |
| **Flag actiu** | `actiu` `:636` | `actiu` `:86` | `actiu` `:658` | 🔴 **`active`** `:423` |
| **`is_system`** | ❌ **NO EXISTEIX** | ✅ default `True` `:88` | ✅ default `False` `:664` (read-only al serializer) | ❌ **NO EXISTEIX** |
| **Ordre** | ❌ (`ordering=['codi']`) | `display_order` `:90` | ❌ **cap** (Meta sense `ordering`) | `complexity_order` `:421` |
| **`descripcio`** | ✅ `:635` | ✅ `:92` | ✅ `:675` | ❌ **NO EXISTEIX** |
| **Enllaç amunt** | — | `grup` **string** `:85` | `grup` **string** `:657` + `garment_type_global` FK SET_NULL `:648` | `garment_type` **FK CASCADE real** `:417` |
| **Construcció** | ❌ | ❌ | `construccio_habitual` text lliure `:669` | ❌ |
| **Conjunt** | ❌ | ❌ | ❌ | `is_set` `:428` + `GarmentTypeItemPart` `:483` |
| **Sizing que declara** | **RES** | **RES** | **RES** (indirecte, via `SizingProfile.garment_type`) | `base_size_definition` `:440` + `grading_rule_set` `:453` (+ satèl·lit `ItemBaseSet`) |
| **RUN de talles** | ❌ **NO EXISTEIX** | ❌ **NO EXISTEIX** | ❌ **NO EXISTEIX** | ❌ **NO EXISTEIX** |
| **Viu a `public`** | ✅ taula + **8 files** | ✅ taula + **59 files** | ✅ taula, **0 files** | 🔴 **TAULA INEXISTENT** |
| **Viu al tenant** | `fhort` 12 · `los` 0 | `fhort` 59 · `los` 0 | `fhort` 21 · `los` 1 | `fhort` 62 · `los` 1 |

Entitats satèl·lit: `GarmentTypeItemPart` (`tasks/models.py:483`, composició de conjunt, amb guard
anti-set-de-sets `:528-533`) · `GarmentPOMMap` (`pom/models.py:685`) · `SizingProfile`
(`pom/models.py:1480`) · `ItemBaseSet` (`pom/models.py:760`).

### 1.2 · La resposta binària del run

**NO EXISTEIX cap camp de run de talles per defecte a cap nivell.** Grep de
`size_run|talles_defecte|default_run|run_defecte` sobre `pom/models.py`, `tasks/models.py` i
`models_app/models.py`: l'únic camp de run del backend és **`Model.size_run_model`**
(`models_app/models.py:310-313`, `CharField(200)`, «Talles del model separades per · o ;») amb el seu
germà `base_size_label` (`:315-318`). **El run és propietat de la instància.**

### 1.3 · Els tres forats estructurals del model de dades

**(a) El pont `grup` NO és un FK i ningú el valida.** `GarmentType.grup` és `CharField(max_length=40)`
(`pom/models.py:657`), `GarmentGroup.codi` és `CharField unique` (`:633`). **Cap FK, cap `clean()`, cap
`validate_grup`** — `GarmentTypeSerializer` exposa `fields='__all__'` amb `grup` escrivible com a text
lliure (`pom/serializers.py:145-148`). La unió es fa a mà a tres llocs: `models_app/views.py:724-726`,
`pom/grading_utils.py:592` i, al front, `garmentCatalog.js:67-72`. `seed_losan_ss27.py:165` ho diu
literalment: «GarmentType.grup és CharField (codi de GarmentGroup), no FK».
**Dades:** `fhort` 0 orfes · **`los` 1 de 1 família amb `grup` ORFE** (0 `GarmentGroup` a l'schema).

**(b) L'item NO POT existir al catàleg global.** `fhort.tasks` és a `TENANT_APPS` i **no** a `SHARED_APPS`
(`settings.py:62-75` vs `:36-59`) → **la taula `tasks_garmenttypeitem` NO EXISTEIX a l'schema `public`**
(verificat a `information_schema.tables`). Conseqüències documentades al propi codi:
`GarmentPOMMap.garment_type_item` és `db_constraint=False` **precisament per això**
(`pom/models.py:689-694`: «un constraint de BD cap a tasks_garmenttypeitem petaria a 'public'»), i el
mateix patró es repeteix a `ItemBaseSet` (`:791-792`), `ItemBaseMeasurement` (`pom/0025:22`),
`GradingRuleSet` (`pom/0039:18`) i `RuleSetScopeNode` (`pom/0040:22`). **La taula
`public.pom_garmentpommap` existeix amb una columna que apunta a una taula inexistent** — avui 0 files,
o sigui **dany latent, no viu**. La sembra d'un tenant nou és per força **tenant→tenant**
(`bootstrap_tenant.py:3-6`, `--from fhort`), no `public`→tenant.

**(c) La i18n del Grup i de l'Item NO EXISTEIX a la BD.** `GarmentGroup` només té `nom` (`:634`) i
`GarmentTypeItem` només `name` (`:420`). **NO EXISTEIX cap altra font de traducció:**
`backend/fhort/i18n_content/models.py` declara `Translation` + `TranslatableMixin` (`:37-81`) però
`TRANSLATABLE_FIELDS` només el declaren dos models de `commerce` (`commerce/models.py:77` i `:402`).
Cap model de `pom` ni de `tasks` hi és. **El vocabulari del Grup viu hardcodat al frontend**:
`frontend/src/components/grading/gradingAxes.js:49-57` (`GARMENT_GROUPS`, 7 codis amb ca/en/es).

**Veredicte Bloc 1: llest.** El model de dades és conegut, i les tres decisions cares que en surten
(FK del `grup`, i18n de Grup/Item, item al catàleg global) queden aïllades a §7.4.

---

## BLOC 2 · QUÈ HERETA EL MODEL EN NÉIXER (T1b)

Porta única, compartida per creació i edició: **`_resolve_garment_def`**
(`backend/fhort/models_app/views.py:693-767`; callers `:792` i `:1029`).

### 2.1 · La llista tancada

**HERETA de l'item, sempre i automàticament — 3 coses:**

| què | com | :línia |
|---|---|---|
| `garment_type` | `= item.garment_type`. **El `garment_type_id` del payload s'IGNORA** quan hi ha item | `:714-715, :723` |
| `garment_group` | `GarmentGroup.objects.filter(codi=item.garment_type.grup).first()`, **i només si existeix** (`if grp is not None`) | `:724-726` |
| el lligam de temps | `garment_type_item` → `TaskTimeEstimate` (`tasks/models.py:547-552`), llegit per `lookup_estimated_minutes` (`tasks/services_g.py:11,19-27`) | `:722` |

**NO HERETA MAI — tot ve del PAYLOAD:**
`base_size_label` (`:765-766`) · `size_run_model` (`:747-764`) · `size_system` (`:733-737`) ·
`grading_rule_set` (`:738-742`) · `target` (`:743-744`) · `construction` (`:745-746`) · `fit_type` (ni
és a la funció) · cap `BaseMeasurement` · cap `ModelTask` · cap fitxer.

> **Confirmació negativa creuada.** `GarmentTypeItem.base_size_definition` i `.grading_rule_set`
> **existeixen** (`tasks/models.py:440-457`) però `_resolve_garment_def` **no els llegeix mai**. L'únic
> codi del backend que escriu `base_size_label`/`size_run_model` és la còpia model→model
> (`views.py:1486-1487`), l'import (`extraction_views.py:872,2259,2267`, `bulk_import_service.py:594-595`),
> la fitxa tècnica (`tech_sheet_views.py:314-315`), la federació (`federation_service.py:221-222`) i
> `patterns/adapters.py:500`. **Cap deriva de l'item.**

**L'ÚNICA EXCEPCIÓ — el camí CONJUNT.** A `create_model_wizard:952-955`, per a cada peça d'un item amb
`is_set=True`, **`base_size` i `grading_rule_set` SÍ vénen del catàleg** (de `part_item`), i **amb
prioritat sobre el payload**. Una samarreta normal no hi passa (`is_set=true` = **0 items a `fhort`**).

**HEREDARIA si es cridés Y:**
- `POST /models/<id>/materialitzar-poms/` (`views.py:1172-1372`, únic caller
  `MeasuresEntryPanel.jsx:89` — **gest conscient**) → **pertinença** de POMs sempre; **valors** només si
  la talla del BaseSet == `model.base_size_label` i la fila destí és inexistent o TEMPLATE buida.
- `POST /models/<dst>/copiar-de/<src>/` (`views.py:1384-1657`) → run+sistema+base (**només si el destí
  no té cap mesura**, `:1477-1483`), ruleset, mesures i fitxers. **No viatja cap camp taxonòmic.**

### 2.2 · La sobirania: el guard existeix i és correcte

`views.py:1319-1332` — amb fila existent, només s'omple si
`existing.origen == 'TEMPLATE' and existing.base_value_cm is None`; qualsevol altra cosa
(MANUAL/IMPORTED/FITTED, o TEMPLATE amb valor) → `skipped`. Idempotent. Guard de talla P1 a `:1263-1284`:
si la talla de la plantilla divergeix de la del model, **se sembra pertinença i CAP VALOR**, i la
resposta ho diu (`talla_verificada`, `valors_bloquejats_per_talla`, `talla_avis`, `:1360-1365`).
⚠️ El guard **s'ha mogut**: `DIAGNOSI_GTI_PLANTILLA_2026-07-21.md:252` el situava a `:827`; avui és a
`:1320`. Les línies d'aquell doc són ranci; el fons aguanta.

### 2.3 · Les dues fonts del grup — resolt

`Model` porta `garment_type` (`models.py:187-193`), `garment_group` (`:194-200`) i `garment_type_item`
(`:202-208`), **tots tres nullables i `SET_NULL`**. El serializer exposa `garment_group_nom` (de la FK,
`serializers.py:228`) i `garment_type_grup` (de `garment_type.grup`, `:232`).
**Mana `garment_type.grup`**, documentat literalment a `serializers.py:229-232`: *«Font:
garment_type.grup, que SEMPRE és present (a diferència de garment_group FK, **buit als models
importats**)»*. **La buida és la FK.** Dades: **34 de 46 models de `fhort` tenen `garment_group_id` NULL
amb `garment_type` informat** — tots de BRW, tots entre 2026-06-10 i 2026-07-16. **Els 3 models nascuts
després (1302, 1307, 1308) sí que el tenen: és deute històric, no regressió viva.**

**Veredicte Bloc 2: llest.** El backend no fabrica ni talla base ni run. La hipòtesi del brief
(«el catàleg va col·locar el run») queda **desmentida**.

---

## BLOC 3 · LA TAULA DE DIALECTES (T2) — LA PEÇA CENTRAL

> **Transposició.** El brief demanava una columna per superfície; amb 20+ superfícies la taula no és
> llegible. La informació és la mateixa, transposada: **una fila per superfície, una columna per
> nivell**. La col·lisió — que és la càrrega útil — va a §3.3 amb el format demanat.

### 3.1 · Taula de dialectes · UI principal

| superfície | **L1 Grup** (ca/en/es) | **L2 Família** (ca/en/es) | **L3 Item** (ca/en/es) | component | endpoint · origen | fitxer:línia |
|---|---|---|---|---|---|---|
| **Garment Types** (pàgina) | «Tots els grups»/«All groups»/«Todos los grupos»; al modal «Grup»/«Group»/«Grupo» | 🔴 **«Garment Types»** ×3 (títol) · «Tipus de peça» (subtítol) · «Nou tipus» | 🔴 **«Items»** ×3 · «Nou item» | `GroupPills` + llista mestre-detall | `garment-groups/`, `garment-types/`, `garment-type-items/` · `fields='__all__'` | `GarmentTypes.jsx:54,61,73,190,193,235,342` |
| **Wizard pas 2** | vegeu CascadeFinder | 🔴 **«Tipus de peça — família i model»** — UNA etiqueta per a DOS nivells | 🔴 comptador «{{n}} **peces** al catàleg» (compta items) | `CascadeFinder` | `garment-type-items/?active=true` | `ModelWizard.jsx:616,656-659,683` |
| **CascadeFinder** | «Grup»/«Group»/«Grupo» | «Família»/«Family»/«Familia» | 🔴 **«Item»**/«Item»/«Item» (ca sense traduir) | — (3 columnes) | `garment-types/` + `garment-type-items/` en 1 crida | `CascadeFinder.jsx:118,134,152,62` |
| **CascadeSelector** | 🔴 **«GRUP DE PEÇA»**/«GARMENT GROUP»/«GRUPO DE PRENDA» | «Família» — però el `node_type` del codi és **`'TYPE'`** | «Item»/«Item»/**«Ítem»** | — (6 nivells) | idem, items peresosos | `CascadeSelector.jsx:165,183,202,284-332` |
| **Fitxa del model / Resum** | — | 🔴 **«Tipus de peça»**/«Garment type»/«Tipo de prenda» | 🔴 **«Model (peça)»**/«Model (piece)»/«Modelo (pieza)» | — | `garment_type_nom` = `nom_client` **cec a l'idioma** · `garment_type_item_nom` = `name` | `ModelSheet.jsx:1503-1504` · `models_app/serializers.py:227,236` |
| **Llista de models · filtres** | 🔴 xip amb `g.nom` **cru de BD** («Tops»), no el localitzat | 🔴 3r ordre de fallback | 🔴 xip **`#{id}`** — sense nom | `CascadeSelector` multi | `models/garment-counts/` | `ModelsFilterPanel.jsx:62-64` · `filterOptions.js:48-58` · `Models.jsx:423-425` |
| **Sidebar** | — | 🔴 **«Garment Types»** ×3 · «Garment POM Map» ×3 | — | — | — | `Sidebar.jsx:36` |
| **ItemAuthoring** | «GRUP DE PEÇA» (filtre opcional, `maxLevel="group"`) | ❌ no hi baixa | «Nou item»/«New item»/«Nuevo item» | `CascadeSelector` single | `garmentTypeItems`, `gradingRuleSets` | `ItemAuthoring.jsx:229,302-307` |

Agrupador «**Peça**»/«Garment»/«Prenda» del panell de filtres (`ModelsFilterPanel.jsx:62`): **un sol nom
que cobreix els TRES nivells alhora**.

### 3.2 · Taula de dialectes · superfícies secundàries

| superfície | ancora a | etiqueta visible (ca/en/es) | fitxer:línia |
|---|---|---|---|
| **POMBrowser** | **ITEM** | 🔴 botó «Canviar **tipus**»/«Change type»/«Cambiar tipo» — però canvia l'ITEM; llista «Cap POM assignat a aquest **ítem**» | `POMBrowser.jsx:108,254`; `pom/models.py:684-690` |
| **GraduacioPanel** | GRUP (xip) + FAMÍLIA (perfil) | «Target» · «Construcció» · **«Grup»** · «Sistema de talles» | `GraduacioPanel.jsx:63,100-105` |
| **Bulk import** (reconciliació + `.xlsx`) | 🔴 **FAMÍLIA i ITEM, tots dos desplaçats** | columna `familia` = **«Família»** → `GarmentType`; columna `tipus` = **«Tipus»** → `GarmentTypeItem` | `BulkImportReconciliation.jsx:19` · `bulk_import_service.py:15-16,245,639-646` |
| **ImportWizard** (model únic) | ITEM | `garment_type_item_code` | `ImportWizard.jsx:338,1592` |
| **BaseSetPanel** · **MeasurementBaseGrid** | ITEM | **cap etiqueta de nivell** (superfícies mudes) | `BaseSetPanel.jsx:67` · `MeasurementBaseGrid.jsx:59-62` |
| **Planning · TimeTree** | 🔴 arrel FAMÍLIA, fulla ITEM | arrel **«Tipus de peça»** · fulla **«Element»**/«Item»/«Elemento» | `TimeTree.jsx:100,139,177` · `views_b.py:1183-1193` |
| **Commerce · ProductDetail** | ITEM | 🔴 «Excepcions de preu **(GTI)**» · «— **Tipus de peça (GTI)** —» (acrònim del model a la UI) | `ProductDetail.jsx:269,297-300` · `commerce/models.py:197,205` |
| **Patterns** (`PatternFile`, `POMPicker`) | ITEM (XOR amb Model) | cap etiqueta | `patterns/models.py:46,111` · `POMPicker.jsx:9` |
| **SizeMapSetup** (àmbit) | **GROUP ∪ TYPE ∪ ITEM** | «Grup» · **«Família»** (`node_TYPE`) · «Item» | `SizeMapSetup.jsx:393-403,585-587` |
| **GradingRuleSets** | GRUP (filtre) | «GRUP DE PEÇA» · «Família» | `GradingRuleSets.jsx:77,232` |
| **TechSheetEditor** | FAMÍLIA + ITEM | 🔴 **`'Garment: '` i `'Item: '` HARDCODATS, fora d'i18n, impresos al PDF**; placeholder `'{tipus de peça}'` lligat a `garment_type_item_nom` | `TechSheetEditor.jsx:1071-1072,1425` |
| **DependencyPanel** · **AssetNavigator** | FAMÍLIA→ITEM | cap etiqueta de nivell (només valors amb chevrons) | `DependencyPanel.jsx:21-27` · `AssetNavigator.jsx:29-36` |
| **FilePicker** · **PromoteToItemButton** | ITEM | «tipus de peça» / «item» | `FilePicker.jsx:60-64` · `PromoteToItemButton.jsx:50` |
| **MeasuresEntryPanel** | 🔴 FAMÍLIA al text, ITEM a la dada | `{type}` = `garment_type_nom`, fallback «aquest **tipus de peça**» | `MeasuresEntryPanel.jsx:83,390` |
| **frontend-backoffice** | — | ✅ **NO EXISTEIX cap referència a `garment`** (30 fitxers, `grep -rlni` buit) | — |

### 3.3 · 🔴 EL MATEIX MOT, NIVELLS DIFERENTS

| mot visible | designa **Grup** | designa **Família** | designa **Item** | designa **altra cosa** |
|---|---|---|---|---|
| **«Família»** | 🔴 `pom/models.py:639` (admin) | `cascade_finder.col_family` · `grading.step_family` · `scope.node_TYPE` · `bulk_import.camp_familia` · `tasks/models.py:422` | — | 🔴 `<Family>` = **agrupador del panell de filtres** (`ModelsFilterPanel.jsx:52,62`) |
| **«Tipus»** | — | `garment_types.*` · Planning «Tipus de peça» (`TimeTree.jsx:139`) · `models_app/serializers.py:227` | 🔴 `pom/models.py:678` (admin) · `bulk_import.camp_tipus` · `poms.change_type` · `products.exc_gti_ph` · `file_picker.no_item` · `TechSheetEditor.jsx:1425` | 🔴 `models_filters.task_type` = «Tipus de tasca» |
| **«Peça»** | — | 🔴 `models_filters.fam_garment` (cobreix els 3) · `model_wizard.block2` | 🔴 `model_wizard.pieces_total` (compta items) · `cascade_finder.no_items` | 🔴 `model_wizard.set_piece_name_ph` = **peça d'un CONJUNT** (`GarmentTypeItemPart`) |
| **«Model»** | — | — | 🔴 `model_sheet.field_garment_item` = «Model (peça)» | **l'entitat `Model` de projecte** (tot `Models.jsx`, `ModelSheet.jsx`) |
| **«Item»** | — | — | ✅ estable a tot arreu | — (però «Element» a Planning, «GTI» a Commerce) |

**Dos noms per a exactament el mateix:** `GarmentGroup` ≡ «Grup» ≡ «GRUP DE PEÇA» ≡ «Família de garment»
≡ `node_type:'GROUP'` · `GarmentType` ≡ «Família» ≡ «Garment Types» ≡ «Tipus de peça» ≡ «Garment:» ≡
«Tipus garment (tenant)» ≡ `node_type:'TYPE'` · `GarmentTypeItem` ≡ «Item» ≡ «Model (peça)» ≡ «peça» ≡
«Element» ≡ «GTI».

🔴 **El cas més agut és l'importador**, que desplaça **totes dues** etiquetes exactament un nivell avall
respecte de l'ORM:

```
ORM (pom/models.py)            Importador (bulk_import_service.py)
GarmentGroup    = "Família"  →  (no existeix a l'importador)
GarmentType     = "Tipus"    →  columna 'familia' = «Família»   ← desplaçat
GarmentTypeItem = —          →  columna 'tipus'   = «Tipus»     ← desplaçat
```

### 3.4 · L'ancoratge real: 12 ITEM · 7 FAMÍLIA · 2 GRUP · 2 multi-nivell

**ITEM (12):** POMBrowser · BaseSetPanel · MeasurementBaseGrid · Planning (fulla + escriptura) ·
Commerce · Patterns `PatternFile` · POMPicker · FilePicker · AssetNavigator (fulla) ·
PromoteToItemButton · TechSheetEditor (import pla) · ImportWizard.
**FAMÍLIA (7):** Bulk import (columna `familia`) · GraduacioPanel (suggeriment de perfil) ·
AssetNavigator (nivell 1) · DependencyPanel · MeasuresEntryPanel (text) · TechSheetEditor (`'Garment: '`) ·
Planning (arrel).
**GRUP (2):** GraduacioPanel (xip) · GradingRuleSets (filtratge).
**Multi-nivell declarat (2):** SizeMapSetup `applies_to` · `gradingAxes.scopeApplies`.
**Sense ancoratge (4):** POMCatalogue · PieceIdentityList · capçalera v3 de la fitxa · tot el backoffice.

### 3.5 · Els 5 resolutors divergents del MATEIX nom de família

| # | on | ordre de fallback (ca) |
|---|---|---|
| 1 | `CascadeFinder.jsx:37-41` | `nom_ca ‖ nom_client ‖ nom_en` |
| 2 | `CascadeSelector.jsx:41-45` | `nom_ca ‖ **nom_en** ‖ nom_client` |
| 3 | `filterOptions.js:48-54` | `nom_ca ‖ nom_en ‖ nom_client` (+ `#id`) |
| 4 | `GarmentTypes.jsx:200,217` | `nom_client ‖ nom_ca ‖ codi_client` — **sense mirar l'idioma** |
| 5 | `models_app/serializers.py:227` | **`nom_client` sec, cec a l'idioma** — és el que veuen ModelSheet, TechSheetEditor, TimeTree, DependencyPanel, MeasuresEntryPanel |

**Causa arrel:** `GarmentTypeSerializer` i `GarmentGroupSerializer` fan `fields='__all__'`
(`pom/serializers.py:24,147`) — **el contracte de nom no està declarat enlloc.**

### 3.6 · i18n: la paritat és perfecta, la traducció no

**0 claus sense paritat** — escaneig pla dels tres fitxers: **4.093 claus, cap absent en cap idioma**.
El problema és un altre: **29 claus dels namespaces censats tenen valor anglès dins `ca.json`**, entre
elles `nav.garment_types` («Garment Types»), `garment_types.title`, `cascade_finder.col_item` («Item»),
`model.fields.fit_type` («Fit Type»), `grading.{target,construction,fit_type,size_system}_label`.
🔴 **El castellà tradueix «Item»→«Ítem» a `grading.step_item`, `scope.items` i `scope.node_ITEM`; el
català no** → el mateix nivell surt «Item» en ca i «Ítem» en es **a la mateixa pantalla**.
**Fora d'i18n del tot:** `TechSheetEditor.jsx:1071-1072` (al PDF de client) i
`bulk_import_service.py:140,246-260` (instruccions i errors **hardcodats en català**: un tenant en
anglès rep errors en català).
**Claus mortes** (definides ×3, 0 usos): el namespace `garment_selector.*` sencer (8 claus),
`model_wizard.selected_item`, `model.fields.garment_type`, `model.fields.garment_group`,
`size_map_p_garment`.

### 3.7 · Dues generacions d'unificació vives alhora

`CascadeFinder.jsx:7-14` es declara «EL navegador… el sistema únic» i cita el veto d'Agus («dos sistemes
per triar EL MATEIX»); la maqueta que el fixa està **VALIDADA per l'Agus el 06/08/2026**
(`ops/maquetes/README.txt:35-42`). Però **ha absorbit 1 consumidor de 7**: només `ModelWizard.jsx:617`.
`CascadeSelector` en manté **6** (SizeMapSetup, GradingRuleSets ×2, ItemAuthoring, ModelsFilterPanel,
POMBrowser) — i al seu torn ja era «el component ÚNIC» que va absorbir `AxesSelector` +
`GarmentTypeSelector` + `ScopeSelector` (`CascadeSelector.jsx:12-15`).
🔴 **`GarmentTypes.jsx` — la pàgina que el comentari del `CascadeFinder` anomena explícitament — segueix
amb mestre-detall** (`:190-208`).
⚠️ **Trampa:** `GarmentTypes.jsx:236,246,254` és **l'única porta a `ItemAuthoring`** de tot el front. Si
es migra a `CascadeFinder` (que «no coneix cap acció de catàleg», `CascadeFinder.jsx:18-19`),
**l'autoria d'ítems es queda sense entrada**.

✅ **`ops/maquetes/maqueta_vista_familia_v1.html` NO és font vàlida** — confirmat a
`ops/maquetes/README.txt:44-45`: «Descartada — NO la facis servir · absorbida com a secció 5 de
Comprovació».

**Veredicte Bloc 3: llest.** El cens és complet i la col·lisió està quantificada.

---

## BLOC 4 · LA REGLA DE «PROXIMITAT» I EL PAS 3 (T3b)

### 4.1 · La frase tancada

**La proximitat és una ORDENACIÓ de 3 claus sobre TOTS els `SizeSystem` actius, calculada 100 % al
frontend a `frontend/src/pages/ModelWizard.jsx:924-929`** — 1a: el **target** de la peça contra
`SizeSystem.target_codis` (`:914-917`); 2a: **de qui és el run**, via `SizeSystem.customer_codi`
(`:919-922`); 3a: `nom‖codi` alfabètic com a desempat estable (`:928`) — **i no exclou res tret dels
sistemes amb `talles.length === 0`** (`:265`).

`PROP_TARGET = { SI: 0, SENSE: 1, ALTRE: 2 }` (`:912`) → 🔴 **un sistema sense cap target declarat es
col·loca PER DAVANT d'un que en declari d'altres.**
Els dos camps: `target_codis` és **derivat** (`SlugRelatedField` sobre l'M2M `SizeSystem.targets`,
`pom/serializers.py:113-116`); `customer_codi` és **columna real** (`pom/models.py:583-586`).

### 4.2 · NO EXISTEIX equivalent al backend — i n'hi ha tres versions divergents

`SizeSystemViewSet` ordena per `codi, id` (`pom/views.py:69`) i el wizard demana el catàleg sencer
(`ModelWizard.jsx:261`). Ordenacions anàlogues i **incompatibles** en altres llocs:

| on | ordre | :línia |
|---|---|---|
| `ModelWizard.jsx:924` | target → client → nom | — |
| `s2_views.py:104-118` | client → canònic `is_default` → resta; dins, per nom. **Sense clau de target** | — |
| `size_map_views.py:1055` | 🔴 **client PRIMER, canònic DESPRÉS** — invers al wizard | — |

**No hi ha font única de «quin sistema és més meu».**

### 4.3 · La porta que no tanca

```js
ModelWizard.jsx:268   if (rows.length && !selSystem && !isEditMode) setSelSystem(rows[0])
ModelWizard.jsx:307   setSelectedSizes(labels)                              // TOT el run del sistema
ModelWizard.jsx:308   setBaseSize(labels[Math.floor(labels.length / 2)] || labels[0] || null)
```

I **el pas 3 no bloqueja mai**: `nextBlocat = block === 1 && !block1Resolved` (`:512`). El `sizingMissing`
(`:327-329`) **es calcula i no es consumeix**. ⇒ **es pot crear un model travessant el pas 3 sense
mirar-lo, i surt amb un run i una base que ningú ha triat.**
**La talla base es DERIVA, no es tria**: és la del mig del **sistema sencer** (`:308`), no del run.
**El backend no ho atura:** `models_app/views.py:747-764` valida que el run pertanyi al `size_system`
(llei S24b), però **NO EXISTEIX cap comprovació que el `size_system` sigui compatible amb el `target`**
(grep de `size_system.targets|targets.filter|target__codi` a `models_app/views.py`: zero).

### 4.4 · El cens del filtre excloent vs anotat

Porta: `GarmentTypeViewSet.get_queryset` (`pom/views.py:124-156`) — `?target` **exclou** via
`SizingProfile` (`:137-141`); `?compat_*` **anota** amb `Exists` (`:142-155`, mode C5).

| superfície | paràmetre | mode |
|---|---|---|
| `garmentCatalog.js:51-53` (amb `compat`) | `compat_target`+`compat_construction`+`compat_fit` | ✅ ANOTAT |
| `garmentCatalog.js:56` (sense `compat`) | `target` | 🔴 EXCLOENT |
| `CascadeSelector.jsx:238` | `target` | 🔴 EXCLOENT |
| `CascadeFinder.jsx:51` (`compat` default `null`, `:45`) | — | 🔴 **EXCLOENT per defecte** |
| `ModelWizard.jsx:166` (`onPickTarget`) | `target` | 🔴 EXCLOENT |
| `GarmentTypes.jsx:54,61` · `AssetNavigator.jsx:29` | cap | sense filtre |

### 4.5 · `DerivaTarget` — una decisió invisible

`ModelWizard.jsx:1037-1053` agafa **el primer `SizingProfile` de la família que porti target**
(`perfils.map(p => p.target?.codi).find(Boolean)`, `:1046`), ordenat pel backend per `size_system.nom`
**alfabètic** (`s2_views.py:117`), i **sense enviar `customer_codi`** (`:1040`) → la baula del client es
perd. **Cap UI diu que el target s'ha derivat.** El comentari `:1034-1036` ho reconeix.

**Veredicte Bloc 4: llest.** La proximitat ordena bé el que el catàleg li dona; el forat és que
**preselecciona i deriva sense dir-ho, i cap porta ho revisa.**

---

## BLOC 5 · LES DADES VIVES (T3c)

### 5.1 · 🔑 El model de prova — la fila real

**`Model id=1307` · `BRW-SS26-0002`**

| camp | valor |
|---|---|
| created_at | **2026-08-04 16:43:43+00** |
| customer | **BRW** |
| **target** | **`KID_BOY`** |
| construction | *(buit)* · fit_type `Regular` |
| size_system | **`BOY_LOS_01`** (`customer_codi='LOS'`) |
| **size_run_model** | **`2·3·4·5·6·7·8·9/10·11/12`** (9 etiquetes) |
| **base_size_label** | **`6`** |
| família / item | `JERSEY_TOPS` / `t_shirt` (item id 8) |
| garment_group_id | 7 (`TOPS`) · grading_rule_set_id **NULL** · origen `INTERN` |

**El catàleg no hi va posar res:** l'item `t_shirt` (id 8) **no té `base_size_definition` ni
`grading_rule_set`** i **no té cap `ItemBaseSet`**. **Ho va posar el wizard.**

🔴 **Però la proximitat no existia encara.** `git log -S"ordenaPerProximitat"` → **una sola aparició:
`1996e4f8`, 2026-08-06 06:25** — **38 h DESPRÉS** del model. El codi viu el 04/08
(`git show 1996e4f8^:frontend/src/pages/ModelWizard.jsx:212-226`) filtrava per target i agafava `rows[0]`
en l'ordre del backend (`codi, id`). Candidats reals per a `KID_BOY`, en aquell ordre:

| # | codi | cust | targets | n |
|---|---|---|---|---|
| **1** | **`BOY_LOS_01`** | LOS | KID_BOY | **9** |
| 2 | `KIDS_AGE_COM` | — | KID_BOY, KID_GIRL | 11 |
| 3 | `TGIRL-EU-HEIGHT` | — | (BUIT) | 8 |

`rows[0]` = `BOY_LOS_01` → 9 etiquetes → `labels[floor(9/2)] = labels[4] = '6'`. **Coincidència exacta.**

🚩 **Amb el bundle d'avui el resultat canvia i segueix sent dolent.** `frontend/dist` porta marca
**2026-08-06 06:25** (= `1996e4f8`): la proximitat ja corre. Amb `customer='BRW'`, `proximitatOrigen`
dona `KIDS_AGE_COM`=1 (canònic) i `BOY_LOS_01`=2 (d'un altre client) → **avui el mateix gest donaria
`KIDS_AGE_COM`, 11 talles i base `labels[5]='7'`**. La 2a clau només hauria explicat `BOY_LOS_01` si el
client fos LOS, **i no ho és**. ⇒ **la QA del pas 3 s'ha de refer sobre el bundle viu.**

### 5.2 · Qui porta sizing per defecte — la llista completa

**`fhort`: 4 items dels 62** (3 amb base, 4 amb ruleset). **`los`: 0.**

| grup | família | item.code | item.name | base | base system | GRS | GRS system | mismatch |
|---|---|---|---|---|---|---|---|---|
| NEWBORN | `NEWBORN` | `baby_dress` | Vestit de nadó | **50** | `BABY_EU_CM` | 87 · EU Knit Baby Regular | `BABY_EU_CM` | no |
| TOPS | `BUTTONED_TOPS` | `blouse` | Blusa | — | — | 115 · BRW · Blusa · ALPHA_EU_W | `ALPHA_EU_W` | n/a |
| TOPS | `BUTTONED_TOPS` | `shirt_woven` | Shirt Man Regular | **L** | `ALPHA_EU_M` | 84 · EU Woven Man Regular | `ALPHA_EU_M` | no |
| TOPS | `JERSEY_TOPS` | `top_sleeveless` | Top de tirants | **M** | `WOMAN_LOS_01` | 186 · LOS Woman Knit — Tops | `WOMAN_LOS_01` | no |

**Cap mismatch** `base.size_system ≠ grs.size_system`: el forat del `clean()` (`tasks/models.py:465-477`,
que només valida si **tots dos** estan informats) **no s'ha materialitzat**. **`t_shirt` no hi és** — cap
d'aquests 4 podia col·locar el run del model 1307.

🔴 **La V2 (`ItemBaseSet`) NO és la font vigent, contra el que diu el seu docstring.**

| superfície | fhort | los |
|---|---|---|
| punter V1 `base_size_definition` | **3** | 0 |
| punter V1 `grading_rule_set` | **4** | 0 |
| **`ItemBaseSet` (V2)** | **1** | **0** |

L'única fila V2 és un **duplicat exacte** del punter V1 de `shirt_woven`. `pom/models.py:765-767` diu que
la V2 «substitueix el pointer (V1, llegat a jubilar)» — **les dades diuen el contrari**, i **no hi ha cap
migració de jubilació**. Qualsevol lector ja migrat a `resolve_item_base_set()` veu `baby_dress` i
`top_sleeveless` **sense base**.

### 5.3 · Els SizeSystem de `fhort` — la taula que reprodueix l'ordenació

25 actius. Els que importen per a la lectura:

| codi | cust | targets | n | etiquetes |
|---|---|---|---|---|
| 🚩 `MEN-SHIRT-NUM` | — | **(BUIT)** | **0** | — |
| 🚩 **`TGIRL-EU-HEIGHT`** | — | **(BUIT)** | 8 | 128·134·140·146·152·158·164·170 |
| `BOY_LOS_01` | LOS | KID_BOY | 9 | 2·3·4·5·6·7·8·9/10·11/12 |
| `GIRL_LOS_01` · `GIRL_LOS_03` | LOS | KID_GIRL | 9 | idèntiques |
| `KIDS_AGE_COM` | — | KID_BOY, KID_GIRL | 11 | 2…15/16 |
| `ALPHA_EU_W` | — | WOMAN | 8 | XXS…3XL |
| `WOMAN_BRW_01` | **BRW** | WOMAN | 5 | XXS·XS·S·M·L |

🔴 **`TGIRL-EU-HEIGHT` («Alpha EU — Grading Reference») té `targets` BUIT i 8 etiquetes** → entra a la
llista de **tots** els targets i, per `PROP_TARGET.SENSE=1`, **s'avança a qualsevol sistema d'un altre
target**. Amb un target que cap sistema declari (**`MATERNITY` i `UNISEX_ADULT`** a `fhort`), guanya ell:
**crear amb qualsevol dels dos preselecciona una escala d'alçades de nena amb base `152`**.
🚩 **5 sistemes actius amb 0 etiquetes** (invisibles al wizard pel filtre `:265`, visibles a la resta).
🚩 `BABY_EU_CM` declara només `NEWBORN_GIRL` però és la base de `baby_dress` — asimetria de targets.

### 5.4 · Cobertura de `SizingProfile` — el dany viu

46 perfils · **10 famílies cobertes de 21** · 1 amb `grading_rule_set` NULL · 19 amb `customer` · 25
`is_default`.

🔴 **21 dels 46 perfils (46 %) pengen de famílies DESACTIVADES**: `T_SHIRT` (16!), `BABY_ONEPIECES` (3),
`DRESS` (2). No arriben mai a l'usuari.
🔴 **10 de les 17 famílies ACTIVES no tenen CAP perfil** → pel filtre excloent `?target=`
(`pom/views.py:137-141`) **desapareixen del pas 2 per a qualsevol target. 31 items invisibles**:
`ACCESSORIES` (3) · `ADULT_JUMPSUITS` (3) · `BRA_SHAPEWEAR` (3) · `HEAVY_OUTERWEAR` (4) ·
`KNIT_CARDIGANS` (2) · `KNIT_SWEATERS` (2) · `LEGGINGS_TIGHTS` (2) · `SKIRTS` (2) ·
`STRUCTURED_JACKETS` (3) · `UNDERWEAR` (6).
✅ `JERSEY_TOPS` **sí** té perfil per a `KID_BOY` — per això el wizard va deixar arribar el model 1307 al
pas 3.

### 5.5 · El recompte real de `GarmentType` a `fhort` — les tres fonts, totes mig certes

| total | **actius** | inactius | `is_system` |
|---|---|---|---|
| **21** | **17** | **4** | **19** |

Els 4 inactius (tots amb **0 items**): `BABY_ONEPIECES`, `DRESS`, `BABY_SEPARATES`, **`T_SHIRT`**.
Els 2 no-`is_system`: `ACCESSORIES` (3 items) i `NEWBORN` (9 items).
⇒ El ledger («17 types») encerta **els actius**; `bootstrap_tenant.py:150` («19/19») encerta **els
`is_system`**; `translate_garment_families.py:7` («42 velles desactivades») **no es correspon amb cap
xifra viva** (només n'hi ha 4).

### 5.6 · Grups, òrfenes i deriva

**12 grups a `fhort`, tots actius. 5 no són als 7 codis canònics** de `gradingAxes.js:49-57` →
`nomLocal()` no els troba i **es pinten en una sola llengua**. Però **4 dels 5 estan BUITS**
(`DRESSES-FULL`, `TOPS-KNIT`, `TOPS-WOVEN`, `KNITWEAR`: 0 famílies, 0 items). **L'únic amb contingut és
`NEWBORN`: 1 família, 9 items** — l'únic grup que avui es veu sense traduir.

| comprovació | fhort | los |
|---|---|---|
| `GarmentPOMMap` amb item inexistent (FK sense constraint) | **0** de 1748 | 0 |
| `Model` amb `garment_group_id` NULL i `garment_type` informat | **34** de 46 (deute històric, §2.3) | — |
| `Model` amb `base_size_label` fora de `size_run_model` | **0** | — |
| `GarmentType` amb `codi_client` duplicat | 0 | 0 |
| `GarmentTypeItem` amb `code` compartit entre famílies | **0** | 0 |

🚩 **`GarmentTypeItem.code` és globalment únic AVUI** → cap de les **7 eines que fan `.filter(code=…)`
sense la família** pot agafar l'item equivocat **ara mateix**. Però el `unique_together` real és el
**PARELL** (`tasks/models.py:461`): **n'hi ha prou amb crear un segon `t_shirt` a una altra família**
perquè totes set comencin a mentir. **Bomba armada, no disparada.** Eines:
`consolidate_pom_catalog.py:209`, `validate_los_maps.py:76`, `seed_losan_ss27.py:72,150`,
`seed_losan_rules.py:114`, `seed_losan_rules_v2.py:115`, `restructure_garment_types_v2.py:255`.
L'única que ho fa bé és `load_map_inline.py:114,119-122` (avisa amb `code ambigu (N items)`).

**Veredicte Bloc 5: llest.** El fil conductor està tancat amb la fila real; queda **refer la QA sobre el
bundle d'avui** (§5.1).

---

## BLOC 6 · CONTRA EL LEDGER (T4)

### 6.1 · Veredicte per llei

| llei | veredicte | evidència |
|---|---|---|
| **Migració `pom/0016`** (eix família → item) | ✅ **COMPLEIX** al codi viu; **1 incompliment inert i confessat** | `0016:14-25` verificat (AlterModelOptions + AlterUniqueTogether + `RemoveField garment_type`). Únic infractor: `reseed_tenant_fhort.py:313`, **blindat per un `raise CommandError` incondicional a `:82-89`** amb el motiu escrit |
| **Sobirania** (`DECISIONS.md:224/700`, «el template sembra, mai posseeix») | ✅ **COMPLEIX al camí de sembra** | Guard viu i correcte a `models_app/views.py:1319-1332`. ⚠️ Els 6 forats veïns de `DIAGNOSI_GTI_PLANTILLA:329` (import de fitxa, `set-measurements`, `gravar-pom`, xat IA, CRUD REST) **no re-verificats** — són fora de la cadena taxonòmica i el doc és del 21/07 |
| **G9** (`DECISIONS.md:1054-1059`) | ⚪ **LA LLEI NO COBREIX AQUEST CAS** | El text literal parla de **`TaskType`**. **Cap cita de G9 esmenta `GarmentType` ni `GarmentTypeItem`.** La clau natural EXISTEIX (`tasks/models.py:461`) i export/bootstrap ja la fan servir (`export_losan_package.py:70`, `bootstrap_tenant.py:150,163`), però **l'API viva referencia per PK** (`models_app/views.py:715-732`; `endpoints.js:474,626,635,644,652`). **Estendre G9 a la cadena és una decisió no escrita** |
| **Catàleg v2** (`DECISIONS.md:72-74`, «8 grups·17 types·62 items») | 🔴 **INCOMPLEIX en 2 dels 3 números** — i el ledger **es contradiu ell sol** | items 62 ✓ · types: el command en fa 17+2=19 i el ledger en diu 17 (dades: **21 files, 17 actives, 19 `is_system`** §5.5) · grups: el 8è (`ACCESSORIES`) **cap seed el crea**. I `DECISIONS.md:813` diu el contrari de `:72`: «no hi ha "57 items" com a mida fixa, cada tenant crea els seus» |
| **`D-31.24`** | 🔴 **NO EXISTEIX** | `grep -rn "D-31\.24"` a tot el repo (`arxiu/` inclòs) → **0 resultats**. La sèrie D-31.x viu SENCERA a `docs/diagnosis/`, **no a `DECISIONS.md`**, i cap membre parla de catàleg. **La decisió real del catàleg v2 és `DECISIONS.md:72-74`, sense numeració D-** |

### 6.2 · El cens d'eines: 1 sola parla l'eix vell, i està desarmada

**SEGURES i parlant l'eix nou (24):** `bootstrap_tenant.py` (⭐ **contrast positiu**: clau natural de 4
camps `('garment_type_item','pom','capa','instancia')` amb el raonament escrit, `:157-167`) ·
`load_map_inline.py` (⭐ l'única amb guard d'ambigüitat de `code`) · `consolidate_pom_catalog.py` ·
`author_baby_pom_maps.py` · `validate_los_maps.py` · `restructure_garment_types_v2.py` ·
`seed_losan_ss27.py` · `backfill_model_items.py` · `backfill_model_taxonomy.py` · `seed_losan_models.py` ·
`flag_incomplete_models.py` · `recompute_welford.py` · `backfill_ruleset_scope.py` ·
`seed_scope_nodes_proposals.py` · `seed_losan_rules[_v2].py` · `seed_losan_grading_v3.py` ·
`seed_losan_master_delta.py` · `crea_sizing_profiles.py` · `seed_baby_months_profiles.py` ·
`GarmentPOMMapViewSet` (`pom/views.py:371-380`, filtre legacy retirat i documentat) · `wizard_views.py` ·
`endpoints.js` · els `scripts_tmp/`.

**TRENCADA però INERT (1):** `reseed_tenant_fhort.py:313` — l'única construcció amb l'eix mort, darrere
un `raise` incondicional.
⚠️ **Fals positiu del brief:** `reseed_tenant_fhort.py:448` és `SizingProfile(garment_type=gt)`, **camp
viu i legítim** (`pom/models.py:1487`). `garment_type` segueix sent camp correcte a `Model`,
`SizingProfile`, `GarmentTypeItem` i `GradingRule`: **l'únic eix mort és `GarmentPOMMap.garment_type`.**
**NO EXISTEIX:** `seed_pom_maps_to_items.py` (ja censat a `DIAGNOSI_BACKOFFICE_POSTREFACTOR.md:53,501,588`).

### 6.3 · 🔴 TROBALLA TRANSVERSAL — l'export entre tenants COL·LAPSA pertinences germanes

`export_losan_package.py:254-257` emet cada `GarmentPOMMap` **sense `capa` ni `instancia`**;
`load_losan_package.py:369-371` els força a `exterior`/`''`. Com que `_upsert` és lookup-first (`:86-97`),
**dues files germanes d'origen (sisa dreta i esquerra, o exterior i folre del mateix POM) arriben al destí
com UNA sola**, last-write-wins, **i sense cap avís**. `ItemBaseMeasurement` té el mateix problema
(`export:260-264`). És exactament el deute que `bootstrap_tenant.py:157-167` va tancar: **el mateix acte
—moure catàleg entre tenants— té dues implementacions amb fidelitat diferent**. El comentari de
`load:366-368` reconeix el forat («fins que en porti…») però **l'exportador no s'ha tocat**.

**Veredicte Bloc 6: llest.** La migració 0016 està neta. El deute viu és **l'export/import** i **la
contradicció interna del ledger sobre la forma del catàleg**.

---

## BLOC 7 · 💡 PROPOSTA D'ALINEACIÓ (T5) — res d'això és una decisió

> Tot aquest bloc és `💡 PROPOSTA (a validar)`. Les decisions són d'Agus (Patró C).

### 7.1 · El vocabulari únic proposat

| nivell | entitat | **ca** | **en** | **es** | per què |
|---|---|---|---|---|---|
| L1 | `GarmentGroup` | **Grup** | **Group** | **Grupo** | ja és el mot majoritari a la UI; l'única cosa a matar és «GRUP DE PEÇA» i el `verbose_name` «Família de garment» |
| L2 | `GarmentType` | **Família** | **Family** | **Familia** | ja és el mot del `CascadeFinder`, del `CascadeSelector` i de l'importador; el que cau és «Tipus (de peça)» i «Garment Types» |
| L3 | `GarmentTypeItem` | **Item** | **Item** | **Ítem** | l'únic mot ja estable; **cal traduir el ca a «Ítem»** per igualar l'es, i matar «Model (peça)», «Element», «GTI» i «peça» |

**Reserva:** «Peça» queda **prohibida com a nom de nivell** — es reserva per a `GarmentTypeItemPart`
(peça d'un conjunt), que és l'únic ús no ambigu que en fa el codi (`model_wizard.set_piece_name_ph`).

### 7.2 · (a) Canvis d'ETIQUETA — barats

| superfície | què canvia | cost |
|---|---|---|
| `nav.garment_types` · `garment_types.title` | «Garment Types» → «Famílies» / «Families» / «Familias» (avui idèntic als 3 idiomes) | **XS** |
| `grading.step_group` | «GRUP DE PEÇA» → «Grup» (alinear amb `cascade_finder.col_group`) | **XS** |
| `cascade_finder.col_item` · `scope.node_ITEM` · `grading.step_item` (ca) | «Item» → «Ítem» (l'es ja ho fa) | **XS** |
| `model_sheet.field_garment_item` | «Model (peça)» → «Ítem» | **XS** |
| `planning.time.tree.by_garment` · `.col_item` | «Tipus de peça» → «Família»; «Element» → «Ítem» | **XS** |
| `products.exceptions` · `.exc_gti_ph` | treure «GTI» de la cara de l'usuari | **XS** |
| `poms.change_type` | «Canviar tipus» → «Canviar ítem» | **XS** |
| `model_wizard.pieces_total/_match` · `gti_required` | «peces» → «ítems»; l'error d'ítem absent ha de dir «ítem» | **XS** |
| les **29 claus amb anglès dins `ca.json`** (§3.6) | traduir-les | **S** (volum, no risc) |
| `pom/models.py:639,678` + `tasks/models.py:462` (`verbose_name`) | alinear l'admin amb el vocabulari | **XS** |
| 🔴 `TechSheetEditor.jsx:1071-1072` (`'Garment: '`, `'Item: '`) | **entren a i18n** — avui van al PDF de client | **S** · ⚠️ pot ser deliberat (document comercial en anglès) → **decisió** |
| 🔴 `bulk_import_service.py:140,246-260` | errors i instruccions **hardcodats en català** → i18n | **S** |

### 7.3 · (b) Canvis de COMPONENT

| què | cost | nota |
|---|---|---|
| `GarmentTypes.jsx` → `CascadeFinder` (ja decidit; maqueta validada 06/08) | **M** | ⚠️ **Bloquejador:** `GarmentTypes.jsx:236,246,254` és **l'única porta a `ItemAuthoring`**, i el `CascadeFinder` «no coneix cap acció de catàleg» (`:18-19`). **Cal decidir on viu el gest «Nou item» abans de migrar** |
| Convergir els **5 resolutors del nom de família** (§3.5) en un de sol | **S** | l'arrel és `fields='__all__'` (`pom/serializers.py:24,147`): declarar un `nom_display` al serializer ho tanca d'un cop, front inclòs |
| Els **6 consumidors restants** de `CascadeSelector` → `CascadeFinder` | **L** | el `CascadeSelector` fa 6 nivells i mode multi; el `CascadeFinder` en fa 3 i single. **No és una substitució, és una fusió** |
| Esborrar el namespace mort `garment_selector.*` (8 claus ×3) + les 4 claus mortes | **XS** | |
| `ModelsFilterPanel`: carregar items a `filterOptions.js` perquè el xip no digui `#{id}` | **S** | avui el nom es perd en recarregar amb filtre a la URL |

### 7.4 · (c) Canvis de DADES — cap és de l'agent

| què | cost | risc |
|---|---|---|
| **Donar `SizingProfile` a les 10 famílies actives que no en tenen** (31 items invisibles, §5.4) | **M** | 🔴 **el més urgent de tot el document**; alternativa barata: passar els callers de `?target=` a `?compat_target=` (§4.4) i el problema desapareix **sense tocar dades** |
| **Decidir què fer amb `TGIRL-EU-HEIGHT`** (targets buit + 8 talles = universal de facto, §5.3) | **XS** | posar-li targets, desactivar-lo, o assumir que és universal |
| Netejar els **21 perfils de famílies desactivades** (46 %) | **S** | |
| Desactivar o esborrar els **4 grups buits** (`DRESSES-FULL`, `TOPS-KNIT`, `TOPS-WOVEN`, `KNITWEAR`) | **XS** | avui només embruten el selector |
| Traduir `nom_ca`/`nom_es` de les 2 famílies buides + el grup `NEWBORN` | **XS** | ⚠️ el grup **no té on desar-ho** → veure (d) |
| Reconciliar **V1 vs V2** del sizing d'item (`ItemBaseSet`, §5.2) | **M** | 🔴 avui la V1 mana i el docstring diu el contrari. **Cal decidir quina és la font i migrar-hi les 3 files** |
| `los`: 1 família amb `grup` orfe i 0 `GarmentGroup` | **S** | |
| 🚫 **`bulk_import`: renombrar les columnes `familia`/`tipus`** | **M** | ⚠️ **NO és un canvi d'etiqueta.** El parse llegeix per **nom de columna** (`bulk_import_service.py:209-215`) i les plantilles `.xlsx` ja estan distribuïdes → **migració de plantilla obligatòria** |

### 7.5 · (d) Canvis de MODEL DE DADES — cars, i cadascun és una decisió d'Agus

| què | cost | què desbloqueja |
|---|---|---|
| **`nom_ca`/`nom_en`/`nom_es` a `GarmentGroup` i a `GarmentTypeItem`** | **L** | mata el vocabulari hardcodat de `gradingAxes.js:49-57` i fa que un grup nou es pugui traduir. **Avui NO EXISTEIX cap manera de traduir un grup nou ni un ítem** |
| **FK real `GarmentType.grup → GarmentGroup`** (avui `CharField` sense validació) | **L** | tanca `los` (§1.3a) i el «PENDENT DE VERIFICAR» de `DIAGNOSI_ITEM_PLANTILLA_COMPLETA:491-493` |
| **`SizingProfile` ancorat a l'ITEM** (avui a la FAMÍLIA, `pom/models.py:1487`) | **L** | l'única manera de distingir dos items germans per àmbit. ⚠️ 46 files a migrar, i **NO EXISTEIX endpoint de creació de `SizingProfile`** (`DIAGNOSI_GATE_GRS_ITEM:418-423`) |
| **`unique_together` a `SizingProfile`** (Meta `:1526-1527` només té `ordering`) | **S** | els duplicats indesambiguables ja documentats |
| **`codi_client` unique a `GarmentType`** | **S** | avui 0 duplicats per sort, cap constraint |
| **`garment_type_item` NOT NULL a `Model`** | **S** | el servei ja ho exigeix (`views.py:820`); la columna segueix nullable (`models.py:202-208`), TODO obert a `:818-819` |
| **`GarmentTypeItem` al catàleg global** (moure'l de `tasks` a una app SHARED) | **XL** | 🔴 **avui NO EXISTEIX la taula a `public`**: un ítem canònic de la casa no té on viure, i 5 FKs viuen sense constraint per això (§1.3b). **És la decisió estructural gran del document** |

### 7.6 · L'ordre proposat

1. **Ara, sense tocar res més:** `?target=` → `?compat_target=` als 4 callers excloents (§4.4). **Retorna
   31 items al catàleg d'un cop i no toca dades.**
2. **Ara:** posar porta al pas 3 o fer visible que run i base són **derivats** i no triats (§4.3), i
   decidir `TGIRL-EU-HEIGHT`.
3. **Refer la QA del pas 3 sobre el bundle d'avui** (§5.1) abans de qualsevol conclusió sobre la
   proximitat.
4. Etiquetes (a) — totes XS/S, cap depèn de res.
5. Resolutor únic del nom al serializer (b) — desbloqueja tota la resta del front.
6. `GarmentTypes.jsx` → `CascadeFinder`, **un cop resolt on viu «Nou item»**.
7. Dades (c) segons prioritat d'Agus.
8. Model de dades (d) — **només el que Agus signi**, i la i18n de Grup/Item primer, que és la que més
   deute mata per menys diners.

---

## TAULA FINAL DE RISCOS

| # | risc | estat | evidència |
|---|---|---|---|
| R1 | **31 items de catàleg invisibles al pas 2** per a qualsevol target (10 famílies actives sense `SizingProfile` + filtre excloent) | 🔴 **VIU** | §5.4 · `pom/views.py:137-141` |
| R2 | **El pas 3 preselecciona run i talla base sense cap gest ni cap porta**; el backend no valida target↔sistema | 🔴 **VIU** | §4.3 · `ModelWizard.jsx:268,307,308,512` |
| R3 | **La QA del símptoma es va fer sobre codi que ja no corre** — avui donaria base 7 i run d'11, no base 6 | 🔴 **CAL REFER** | §5.1 · `1996e4f8` vs `created_at` 04/08 |
| R4 | **`TGIRL-EU-HEIGHT`** (targets buit + 8 talles) és universal de facto i guanya per a `MATERNITY`/`UNISEX_ADULT` | 🔴 VIU | §5.3 · `ModelWizard.jsx:912-917` |
| R5 | **V1 vs V2 del sizing d'item**: el docstring diu que la V2 mana, les dades diuen que la V1 | 🔴 VIU | §5.2 · `pom/models.py:765-767` |
| R6 | **L'export entre tenants col·lapsa pertinences germanes** (capa/instància), sense avís | 🔴 VIU | §6.3 · `export_losan_package.py:254-257` |
| R7 | **`GarmentTypeItem.code` tractat com a únic per 7 eines** quan la clau és el parell | 🟡 **ARMAT, NO DISPARAT** (0 col·lisions avui) | §5.6 · `tasks/models.py:461` |
| R8 | **NO EXISTEIX manera de traduir un grup nou ni un ítem** (sense camps i18n a BD) | 🟡 VIU, mitigat | §1.3c · només `NEWBORN` afectat avui |
| R9 | **`GarmentType.grup` sense FK ni validació** | 🟡 VIU | §1.3a · `los` ja té 1 orfe |
| R10 | **`public.pom_garmentpommap` amb FK a una taula inexistent** | 🟢 **LATENT** (0 files) | §1.3b |
| R11 | **34 models sense `garment_group_id`** | 🟢 **DEUTE HISTÒRIC** (cap posterior al 31/07) | §2.3 |
| R12 | **1 eina amb l'eix mort de `pom/0016`** | 🟢 **INERT** (`raise` incondicional) | §6.2 |
| R13 | **Errors de l'importador hardcodats en català** — un tenant en anglès els rep en català | 🟡 VIU | `bulk_import_service.py:140,246-260` |
| R14 | **`familia`/`tipus` opcionals a l'import massiu** → un model pot néixer sense cap nivell taxonòmic | 🟡 VIU | `bulk_import_service.py:139-140,590-591` |

**Correccions a docs vigents detectades de passada** (no s'han tocat):
- `DIAGNOSI_GATE_GRS_ITEM_2026-07-23.md:353-356,428-431,499` afirma que `SizingProfile` exigeix
  `grading_rule_set` NOT NULL. **Ja no és cert**: `pom/migrations/0045_sizingprofile_grading_nullable.py:14-18`
  (23/07) el va fer nullable. `size_system` **sí** que segueix NOT NULL.
- `DIAGNOSI_COMMERCE_ASSIGNACIO_I_CASCADE_GT.md:159` cita `AxesSelector.jsx` — **NO EXISTEIX**; el
  component viu és `CascadeSelector.jsx`.
- `DIAGNOSI_GTI_PLANTILLA_2026-07-21.md:252` situa el guard de sobirania a `:827`; avui és a `:1320`.

---

## QUÈ DECIDEIX AGUS

1. **El vocabulari.** ¿Es fixa **Grup · Família · Ítem** (§7.1) com a única nomenclatura a les tres
   llengües, amb «Peça» reservada per a les peces de conjunt? Sense aquesta signatura, cap canvi
   d'etiqueta té criteri.
2. **R1 — els 31 items invisibles.** ¿Es passa `?target=` a `?compat_target=` (barat, no toca dades) o
   es donen perfils a les 10 famílies (car, però és el model «correcte»)?
3. **R2 — la porta del pas 3.** ¿El wizard pot seguir preseleccionant run i base sense que ningú els
   triï? Si no: ¿porta dura, o senyal visible de «derivat»?
4. **R4 — `TGIRL-EU-HEIGHT`.** Targets, desactivació, o universal declarat.
5. **R5 — V1 vs V2 del sizing d'item.** Quina és la font vigent, i qui migra les 3 files.
6. **`GarmentTypes.jsx` → `CascadeFinder`.** Ja està decidit el component; **falta decidir on viu el gest
   «Nou item»**, perquè avui aquella pàgina és l'única porta a `ItemAuthoring`.
7. **La forma del catàleg al ledger.** `DECISIONS.md:72` i `:813` es contradiuen; les dades diuen 21
   files / 17 actives / 19 `is_system`. ¿Quina xifra és la doctrina?
8. **G9.** ¿S'estén la llei de «referències per `code`, mai per PK» a `GarmentType`/`GarmentTypeItem`?
   La clau natural ja existeix i export/bootstrap ja la fan servir; l'API viva, no.
9. **La i18n de Grup i Ítem a BD** (§7.5). És el canvi de model de dades que més deute mata per menys
   diners. ¿Entra?
10. **`GarmentTypeItem` al catàleg global** (§7.5, XL). La decisió estructural gran: avui un ítem canònic
    de la casa **no té on viure a `public`**, i 5 FKs viuen sense constraint per aquesta raó.
11. **`TechSheetEditor` `'Garment: '` / `'Item: '`.** ¿Deliberadament en anglès (document comercial) o
    entren a i18n?
12. **Les columnes `familia`/`tipus` de l'import massiu.** Alinear-les amb el vocabulari **trenca les
    plantilles `.xlsx` ja distribuïdes**. ¿Es fa, amb migració de plantilla, o es congela el dialecte de
    l'importador?
