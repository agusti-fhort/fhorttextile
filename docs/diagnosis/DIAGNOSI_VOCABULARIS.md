# DIAGNOSI · ELS VOCABULARIS I EL DESACOBLAMENT DE POM SYSTEM

> **Data** 2026-08-06 (nit) · **Patró A — READ-ONLY.** Cap línia d'aquest document s'ha
> implementat: és l'entregable de diagnosi que acompanya la nit de N1-N4, i el T2 és el que
> l'Agus demanava per a demà.
> **Base:** `origin/dev` = `3a0123a3` (push d'Agus del vespre). Tenant de dades: `fhort`
> (i `los` on s'indica). Tots els números són `SELECT` read-only d'aquesta nit.
>
> **Convenció:** cada afirmació porta `fitxer:línia`. **«NO EXISTEIX» = confirmat absent al
> codi**, no especulat. Les propostes van marcades `💡 (a validar)` i estan separades dels fets.

---

## 0 · EL TITULAR, EN TRES FRASES

1. **El vocabulari de GRUP correcte és `GarmentGroup`** (`backend/fhort/pom/models.py:639`), i la
   decisió de l'Agus és la que el codi ja practica. El vocabulari que s'hi assembla i **no**
   s'ha de fer servir és `POMCategory` (`pom/models.py:359`): descriu **àrees de cos**
   (Upper body, Sleeve, Collar…), no famílies de peça.
2. **«POM System» no és un model.** No existeix cap classe `POMSystem`, cap camp `pom_system`,
   cap taula. És el **rètol d'una pantalla** (`i18n/ca.json:3382`, `nav.poms_list`), i la cosa
   real que hi ha a sota és **el conjunt de `GarmentPOMMap` que pengen d'un `GarmentTypeItem`**
   (`pom/models.py:694-712`). **`GarmentPOMMap` no té cap FK a `GarmentGroup`, ni a
   `SizeSystem`, ni a `SizeDefinition`.**
3. **Per tant el model ja està desenganxat; el que està enganxat és l'edifici.** L'acoblament és
   de tres menes i cap és una FK: **empaquetat** (grup i talles viuen dins l'app `fhort.pom`),
   **navegació** (el Navegador obliga a passar pel grup) i **vocabulari** (hi ha dues fonts de
   veritat de què és un grup, i la factura ja s'està pagant).

---

# T1 · LES FONTS DELS 4 VOCABULARIS

## 1.1 · La taula

| Capa | Model (font única) | Camp d'identitat | Codis REALS a `fhort` | Endpoint | Consumidors frontend |
|---|---|---|---|---|---|
| **TARGET** | `Target` — `pom/models.py:1385` | `codi` (unique + `CODI_CHOICES` `:1394-1401`) | **13**: WOMAN · MAN · UNISEX_ADULT · NEWBORN_{GIRL,BOY,UNISEX} · BABY_{GIRL,BOY} · KID_{GIRL,BOY} · TEEN_{GIRL,BOY} · MATERNITY | `GET /api/v1/targets/` — `pom/s2_views.py:16` | `api/endpoints.js:268` · `SizeSystemDrawer.jsx:51` · `GradingRuleSets.jsx:789` · `SizeMapSetup.jsx:526` · còpia JS `TARGETS` a `grading/gradingAxes.js:15` |
| **CONSTRUCCIÓ** | `ConstructionType` — `pom/models.py:1429` | `codi` (unique + choices `:1431-1436`) | **4**: WOVEN · KNIT · STRETCH_KNIT · TECHNICAL | `GET /api/v1/construction-types/` — `s2_views.py:33` | `endpoints.js:276` → `SizingProfileSelector.jsx:84` · `GradingRuleSets.jsx:789` · còpia JS `CONSTRUCTIONS` a `gradingAxes.js:31` |
| **FIT** | `FitType` — `pom/models.py:1349` | `codi` (unique + choices `:1351-1357`) | **10**: REGULAR · SLIM · RELAXED · OVERSIZED · FLARED · TAPERED · STRAIGHT · BODYCON · ATHLETIC · CUSTOM | `GET /api/v1/fit-types/` — `s2_views.py:49` | `endpoints.js:272` → `SizingProfileSelector.jsx:89`, `BaseSetPanel.jsx:90` · còpia JS `FITS` a `gradingAxes.js:37` |
| **GRUP** | **`GarmentGroup`** — `pom/models.py:639` | `codi` (unique) | **12**: ACCESSORIES · BOTTOMS · DRESSES · DRESSES-FULL · KNITWEAR · NEWBORN · OUTERWEAR · SWIMWEAR · TOPS · TOPS-KNIT · TOPS-WOVEN · UNDERWEAR | `GET /api/v1/garment-groups/` (**ReadOnly**) — `pom/views.py:175` | `endpoints.js:249` → `grading/garmentCatalog.js:38,102` · `GraduacioPanel.jsx:46` · `ModelWizard.jsx:337` · `ItemAuthoring.jsx:98` · còpia JS `GARMENT_GROUPS` a `gradingAxes.js:49` |

## 1.2 · El patró de tag que la casa JA fa servir (i que N1 ha replicat)

N'hi ha **tres vius**, i **cap és un JSON de tags lliures**:

1. **M2M al vocabulari, exposat i escrit per CODI (`SlugRelatedField`)** — el patró madur:
   - `SizeSystem.targets = M2M('Target')` — `pom/models.py:565-568` (migrat de FK→M2M a
     `pom/migrations/0021_…`).
   - `GradingRuleSet.targets = M2M('Target')` — `pom/models.py:1136-1142` (el FK llegat `target`
     es va RETIRAR a la migració `0043`, per D-CONS «un rol, un vincle»).
   - Contracte: `SizeSystemSerializer.target_codis = SlugRelatedField(slug_field='codi')` —
     `pom/serializers.py:113-116`. Escriptor: `SizeSystemDrawer.jsx:75` (`PATCH {target_codis}`).
2. **FK simple** per als eixos de cardinalitat 1 — `GradingRuleSet.construction`
   (`pom/models.py:1143-1147`) i `.fit_type` (`:1148-1152`), tots dos `SET_NULL`.
3. **Tag per CODI en CharField, sense FK** — `GarmentType.grup` (`pom/models.py:666`) i
   `GarmentTypeGlobal.grup` (`:85`). La integritat és **per convenció**, no per constraint.

**Precedent multi-node** per si algun dia cal àmbit heterogeni: `RuleSetScopeNode`
(`pom/models.py:1183`), amb `node_type ∈ {GROUP, TYPE, ITEM}` i exactament un FK poblat
(validat a `clean()`, `:1223-1230`).

> **El que N1 ha fet aquesta nit** és el patró (1), literal, per a les tres capes que faltaven:
> `construccions` → `ConstructionType`, `fits` → `FitType`, `grups` → `GarmentGroup`, amb
> `SlugRelatedField(slug_field='codi')` a `pom/serializers.py`. Zero vocabularis nous.

## 1.3 · VEREDICTE sobre GRUP

**`GarmentGroup`, camp `codi`.** La decisió de l'Agus coincideix amb el que el codi ja practica:

- **Qui l'escriu:** només sembres i imports controlats — `bootstrap_tenant.py:57,132,143`
  (clonatge public→tenant per `codi`), `load_losan_package.py:290`, `seed_losan_*`. **L'API és
  read-only** (`GarmentGroupViewSet(ReadOnlyModelViewSet)`, `pom/views.py:175`). Ningú el crea
  des de la UI.
- **Qui el llegeix:** `garmentCatalog.js:16-18` ho declara explícitament — *«El registre de BD
  mana la DISPONIBILITAT; el vocabulari només aporta ordre i noms ca/en/es»*.
- **Relació amb GarmentType:** **no hi ha FK.** `GarmentType.grup` (`:666`) i
  `GarmentTypeGlobal.grup` (`:85`) porten el `codi` com a text.

### El vocabulari alternatiu que NO s'ha de fer servir

`POMGlobal.categoria` (`pom/models.py:36`) amb el seu catàleg `POMCategory` (`:359`). Els seus
valors a `fhort` són àrees de cos: `Upper body · Sleeve · Collar / Neckline · Lower body ·
Waistband · Rise · Skirt / Dress · Hem / Finish · Knitwear-specific · Swimwear-specific ·
Closure / Detail · Jacket / Coat · Placement · Accessories · Technical / Workwear · LOSAN`.

L'únic lloc on es fa passar per «grup» és el diccionari cablejat `GROUP_POM_CATEGORIES`
(`pages/GradingRuleSets.jsx:22-31`, usat a `:304-306`), i **no és un vocabulari de grup: és un
filtre de visualització de files de POM**.

🚩 A més, la taula `POMCategory` de `fhort` està **bruta**: **28 files per a ~15 conceptes**, amb
duplicats del tipus `codi='CAT-UB'` i `codi='Upper body'` per a la mateixa cosa. Un motiu més.

## 1.4 · Divergències BD ↔ JS que s'han de saber

| # | Divergència | Detall | Impacte |
|---|---|---|---|
| **D1** | **FIT: BD ↔ `CODI_CHOICES`** | `FitType.CODI_CHOICES` (`pom/models.py:1351-1357`) declara **5** codis i inclou `LOOSE`, que **no existeix a cap BD**. La BD en té **10**, i la constant JS `FITS` (`gradingAxes.js:37-48`) coincideix amb la BD, no amb els choices. | Els `choices` són **codi mort desactualitzat**. Un `full_clean()` sobre un `FitType` real petaria. Font de veritat = **la BD**. |
| **D2** | **GRUP: BD ↔ JS** | `GARMENT_GROUPS` (`gradingAxes.js:49-57`) té **7** codis; `fhort` en té **12**. Falten: `KNITWEAR · NEWBORN · DRESSES-FULL · TOPS-KNIT · TOPS-WOVEN`. | 🔴 **`NEWBORN` té 162 `GarmentPOMMap` vius i es pinta amb el nom cru de BD i l'ÚLTIM de la fila de pills** (`garmentCatalog.js:22-24,76,107`). Els altres 4 tenen 0 GarmentType i 0 GradingRuleSet: són codis morts al registre. |
| **D3** | TARGET i CONSTRUCCIÓ | Sense divergència: BD = choices = JS (13 i 4). | El contracte és manual i està declarat a `gradingAxes.js:12-14`. |
| **D4** | `GradingRuleSet.garment_group` és **FK simple**, no M2M (`pom/models.py:1095-1101`) | 18 de 47 rulesets el porten. | N1 dona **multi-grup** al run (`grups` M2M): cardinalitat NOVA respecte del ruleset. Anotat, no resolt. |

🚩 **Llei que s'ha d'arrossegar a les 4 capes:** «**buit NO vol dir universal**» — ho declara
`pom/serializers.py:110-112` per a `targets`, i `ModelWizard`/`proximitatRun.js` ho apliquen
com a `SENSE` (queda al mig, ni primer ni últim). N1 l'ha replicada literalment.

---

# T2 · POM SYSTEM DESVINCULAT — com està lligat, què vol dir soltar-lo, i el pla

## 2.0 · Què és «POM System» en aquest codi

**FET.** El grep del repo sencer retorna dues aparicions del terme, i totes dues són rètols:
`i18n/{ca,en}.json:3382` (`poms.title`) i `i18n/ca.json:594` (`nav.poms_list`) →
`layout/Sidebar.jsx:37`.

**La pantalla** és `pages/POMs.jsx:9-49`, muntada a `App.jsx:402`, amb dues pestanyes
(`POMs.jsx:7`): **Navegador** → `components/POMBrowser/POMBrowser.jsx` (el «Navegador de POM
Systems» que citen `pages/GarmentTypes.jsx:187` i `GroupPills.jsx:6`) i **Catàleg** →
`POMBrowser/POMCatalogue.jsx:59`.

**La cosa real** és `GarmentPOMMap` (`pom/models.py:694-712`), servida per
`GET /api/v1/garment-pom-maps/?garment_type_item=<id>` (`pom/urls.py:28` → `pom/views.py:353-382`).

**Cens de relacions via `_meta` (tenant `fhort`):**

```
GarmentPOMMap  FKs: [garment_type_item → tasks.GarmentTypeItem, pom → pom.POMMaster]   reverse: []
POMMaster      FKs: [pom_global → POMGlobal, categoria → POMCategory]
```

→ **Desenganxar POM System no requereix tocar cap FK del domini POM.**

## 2.1 · Com està lligat — el cens dels acoblaments

### A · EMPAQUETAT (el més gros i el més invisible)

El vocabulari de grup i **tot el domini de talles** viuen dins l'app `fhort.pom`:

| Model | Àncora | Què és realment |
|---|---|---|
| `GarmentGroup` | `pom/models.py:639-653` | Vocabulari de GRUP (`verbose_name='Família de garment'`) |
| `GarmentType` | `pom/models.py:656-691` | FAMÍLIA de peça |
| `GarmentTypeGlobal` | `pom/models.py:80-100` | Catàleg canònic (schema `public`) |
| `SizeSystem` / `SizeDefinition` | `pom/models.py:556` / `:605` | El domini de talles |
| `Target` / `FitType` / `ConstructionType` | `:1385` / `:1349` / `:1429` | Els eixos |
| `GradingRuleSet` / `GradingRule` / `RuleSetScopeNode` | `:1068` / `:1239` / `:1183` | La graduació |
| `SizingProfile` | `:1489-1541` | Compatibilitat target↔família |

⚠️ **Restricció dura:** `fhort.pom` és **l'única app declarada alhora a `SHARED_APPS` i
`TENANT_APPS`** (`fhort/settings.py:53-55` i `:68`, amb comentari explícit). Qualsevol partició
ha de preservar la dualitat o els models desapareixen de `public`.

**Conseqüència:** 40+ imports creuats `from fhort.pom.models import GarmentGroup/SizeSystem/…`
des d'apps que no tenen res a veure amb POMs — `models_app/models.py:188-240`,
`tasks/models.py:417-459`, `models_app/matching.py:65`, `bootstrap_tenant.py:57,132,143`…

✅ **El matís que abarateix tot el problema:** **les URL NO estan prefixades per `pom`**.
`fhort/urls.py:48` munta `fhort.pom.urls` sota `api/v1/` pla. `/api/v1/garment-groups/`,
`/api/v1/size-systems/` i `/api/v1/garment-types/` **ja són rutes neutres**: només la propietat
del codi és de `pom`, no el contracte HTTP.

### B · API — el router de POM registra el vocabulari

`pom/urls.py:19-31`: `:20 poms` · `:21 pom-categories` · `:22 size-systems` ·
`:23 size-definitions` · `:24 garment-groups` · `:25 garment-types` · `:26 grading-rule-sets` ·
`:28 garment-pom-maps`. Tot al **mateix `DefaultRouter`**.

### C · NAVEGACIÓ — aquest és el que crema

**L'única porta d'entrada al POM System d'un item és el vocabulari de GRUP.**
`POMBrowser.jsx:217-227`:

```jsx
<CascadeSelector mode="single" minLevel="group" maxLevel="item" stopPolicy="require-item" … />
```

`minLevel="group"` força grup → família → item abans de veure cap POM, i `POMBrowser.jsx:216` és
un `if (!selectedItem) return <CascadeSelector/>` incondicional: **no hi ha cerca directa d'item
ni deep-link**.

Cadena arrossegada: `POMBrowser.jsx:13` → `CascadeSelector.jsx:10` → `GroupPills.jsx:2` →
`gradingAxes.js:49-57` (**llista cablejada de 7 grups**). I un lector directe més:
`POMBrowser.jsx:14,262` fa servir `groupLabel` per al **breadcrumb**.

### D · DOMINI DE TALLES (indirecte, via germans de l'item)

`GarmentPOMMap` no toca talles, però l'ITEM sí, per tres camins: `ItemBaseSet`
(`pom/models.py:769-857`), `GarmentTypeItem.base_size_definition` (`tasks/models.py:441-446`,
declarat «a jubilar» a `pom/models.py:774-776`) i `GarmentTypeItem.grading_rule_set`
(`tasks/models.py:454-459`, que constreny el primer via `clean()` a `:465-470`).

I `GradingRuleSet` barreja **els dos dominis en una sola fila**: `garment_group`
(`pom/models.py:1095-1101`) + `size_system` (`:1102`).

### E · Bonus de namespace

La pantalla de Grading Rules viu **sota la ruta de POMs**: `App.jsx:403` (`poms/grading`),
`Sidebar.jsx:39`, `Topbar.jsx:18`, i literals a `CustomerDetail.jsx:336,341` i
`ItemAuthoring.jsx:336`. **La graduació no és un POM, però la URL diu que sí.**

## 2.2 · Què vol dir soltar-lo

| # | Acoblament | Si el tallem | Font alternativa | Tall |
|---|---|---|---|---|
| 1 | App-packaging (`pom/models.py:556,605,639,656`) | Moure l'estat de migracions + ~40 imports. **Cap URL canvia.** Cap taula es mou si es preserva `db_table`. | Apps `fhort.taxonomy` + `fhort.sizing` | **Additiu** amb `SeparateDatabaseAndState` i `db_table` fixat · **DESTRUCTIU** si es deixa que Django renombri taules |
| 2 | Router de POM (`pom/urls.py:22-25`) | Es pot registrar el mateix viewset des d'un `urls.py` nou en paral·lel (DRF ho tolera amb `basename` únic). | `taxonomy/urls.py`, `sizing/urls.py` | **Additiu pur** |
| 3 | `minLevel="group"` (`POMBrowser.jsx:220`) | Avui és l'ÚNICA porta. Amb una segona (cerca d'item / `?item=<id>`), res es trenca. | `/api/v1/garment-type-items/?search=` (ja existeix, `endpoints.js:480`) | **Additiu pur** |
| 4 | `groupLabel` al breadcrumb (`POMBrowser.jsx:14,262`) | El breadcrumb pren el nom de BD. NEWBORN ja hi surt amb nom cru avui. | `GarmentGroup.nom` del registre | **Additiu** |
| 5 | `GARMENT_GROUPS` cablejat (`gradingAxes.js:49-57`) | Es perden **ordre canònic** i **etiquetes ca/es** — les úniques dues coses que aporta. Regressió visible a 15+ superfícies. | Un `display_order` + `nom_ca/nom_es` a `GarmentGroup` (**avui NO existeixen**: `:640-643` només té `codi/nom/descripcio/actiu`) | **DESTRUCTIU sense font substituta.** Cal migració additiva primer |
| 6 | `GarmentType.grup` CharField (`pom/models.py:666`) | Guanya integritat referencial; mata el join per string de `models_app/views.py:724`. | FK a `GarmentGroup` | **DESTRUCTIU** (migració de dades + `GarmentTypeSerializer` usa `fields='__all__'` → `grup` passaria de string a id) |
| 7 | `GradingRuleSet.garment_group` (`:1095-1101`) | El camí de sortida **ja està obert**: `serializers.py:225-228` escriu `garment_group=None` quan arriba `applies_to` («convergència per atrició»). | `RuleSetScopeNode` | **Additiu** — és atrició, no tall |
| 8 | Talles enganxades a l'item (`pom/models.py:801-816`, `tasks/models.py:441`) | `GarmentPOMMap` no en depèn: es poden separar sense tocar cap POM. | `ItemBaseSet` (ja és la font canònica) | **Additiu** el pas 1 · **destructiu** dropear el camp |
| 9 | Ruta `/poms/grading` (`App.jsx:403`) | 4 literals + un redirect. | Ruta `/grading` pròpia | **Additiu** |

## 2.3 · Cost per lector — el cens

### Frontend · vocabulari de GRUP

| Lector | Àncora | Cost | Per què |
|---|---|---|---|
| `gradingAxes.GARMENT_GROUPS` | `gradingAxes.js:49-57` | **L** | És l'arrel. Sense donar ordre+i18n de BD abans, tots els altres regressionen. |
| `garmentCatalog` (`ORDER`/`VOCAB`/`normGroup`) | `garmentCatalog.js:18-24,76,107` | **M** | 3 punts de fusió BD↔vocabulari; el fallback ja funciona (NEWBORN n'és la prova viva). |
| `GroupPills` | `GroupPills.jsx:2,16,28` | **S** | Rep `groups` per prop a **totes** les crides reals (`GarmentTypes.jsx:190`, `CascadeSelector.jsx:294`): el default `PECA_GRUPS` és mort de facto. |
| `CascadeSelector` / `CascadeFinder` | `CascadeSelector.jsx:8,10,76,238,294` · `CascadeFinder.jsx:4,51` | **S** / **XS** | Ja beuen de `useGarmentCatalog`. |
| **`POMBrowser`** | `POMBrowser.jsx:13,14,218-227,262` | **S** | 2 punts: `minLevel` i el breadcrumb. **Cap lògica de POM en depèn.** |
| `GarmentTypes` | `GarmentTypes.jsx:12,13,39,190,312` | **S** | Ja usa la BD explícitament (comentari a `:39`). |
| `ModelWizard` | `ModelWizard.jsx:4,15,337` | **M** | Camí crític de creació de model. |
| `GradingRuleSets` | `GradingRuleSets.jsx:15,77` | **L** | `:15` documenta un **fork tancat**: còpia pròpia dels enums i del matching. Migrar-lo és unificar el fork. |
| `ItemAuthoring` · `GraduacioContenidor` · `GraduacioPanel` | `:5,98` · `:3,45` · `:4,46` | **S** | Consum de llista / mapa id→codi. |
| `filterOptions` · `ModelsFilterPanel` · `SizeMapSetup` | `filterOptions.js:7,19,33` · `:3` · `SizeMapSetup.jsx:8` | **XS** | Llista plana, delegació. |
| Matching de rulesets | `gradingAxes.js:96-99,112-127,154-163,212-224` | **M** | Lògica pura i testejable, però és el cor del matching: cal test de no-regressió abans de tocar. |

### Backend · vocabulari de GRUP

| Lector | Àncora | Cost |
|---|---|---|
| `GarmentGroupViewSet` + serializer | `pom/views.py:175-183` · `pom/serializers.py:22-25` | **XS** (moure de fitxer; ruta i `basename` no canvien) |
| `GradingRuleSet.garment_group` | `pom/models.py:1095-1101` | **M** (FK `PROTECT`, 18 files vives; té substitut) |
| `RuleSetScopeNode.garment_group` | `pom/models.py:1200-1201` | **S** (1 fila viva) |
| `apply_scope_nodes` | `pom/grading_utils.py:583,592` | **XS** (resol per **codi**, no per PK — llei G9) |
| `Model.garment_group` | `models_app/models.py:194-200` | **M**, però **0 files vives a `fhort`** → migrable sense dades |
| `_resolve_garment_def` | `models_app/views.py:710,724` | **S** (join per string) |
| `bootstrap_tenant` | `bootstrap_tenant.py:57,132,143` | **M** — llista literal de models a sembrar; qualsevol moviment d'app l'ha d'acompanyar o el bootstrap de tenant nou peta |
| Paquets LOSAN (5 eines) | `load_losan_package.py:290,415,435` · `export_losan_package.py:209` · `seed_losan_*` | **M** en bloc (mecànic però ampli) |
| `import_master` · `backfill_*` · `s9_views` | `data/import_master.py:22,130-134,244` · `backfill_model_taxonomy.py:40,65-67` · `pom/s9_views.py:122` | **S** / **XS** |

### Backend · domini de TALLES ancorat a `pom`

`SizeSystemViewSet`/`SizeDefinitionViewSet` (`pom/views.py:62-104`) **XS** · `ItemBaseSet`
(`pom/models.py:803-816`) **S** · `GarmentTypeItem.base_size_definition` (`tasks/models.py:441-446`,
amb `clean()` acoblat a `:465-470`) **M** · `Model.size_system` (`models_app/models.py:227-233`) **S**
· `matching.py:65` **XS** · **motor de graduació en «espai de sistema»** (`pom/services.py:105,124,242,416,979`)
**L — no es toca** (raona sobre l'ordre de `SizeDefinition`, llei S24b) · Size Map wizard
(`pom/size_map_views.py`, rutes a `pom/urls.py:57-65`) **M**.

## 2.4 · El pla per passos `💡 (a validar)`

> Cada pas és verd tot sol i cap necessita el següent per no regressionar. Els passos 0-4 són
> additius i reversibles amb un `git revert`. Del 5 endavant hi ha migració.

**PAS 0 — Congelar els fets (0 codi).** L'Agus signa que «POM System» = `GarmentPOMMap` per
`GarmentTypeItem`, i que el model ja està net.
**Verd:** aquest document acceptat com a referència.

**PAS 1 — Segona porta al Navegador.** Afegir a `POMBrowser.jsx:216-227` una entrada per cerca
d'item (i acceptar `?item=<id>`), **sense treure** la cascada.
**Verd:** es pot obrir el POM System d'un ítem sense clicar cap pill de grup; el camí antic
idèntic. **Reversible:** sí.

**PAS 2 — Enriquir `GarmentGroup` a BD. 🚩 DECISIÓ D'AGUS.** Camps additius i nullables
(`display_order`, `nom_ca`, `nom_es`, `nom_en`), sembrats amb els valors d'avui de
`gradingAxes.js:50-56` i amb ordre explícit per als 5 grups que el codi no coneix.
**La decisió que cal:** *el vocabulari de grup és propietat de la BD (per tenant) o del codi
(canònic de la casa)?* **Tota la resta del pla en depèn.**
**Verd:** `GET /api/v1/garment-groups/` retorna ordre i noms trilingües per als 12 grups,
`NEWBORN` inclòs. Cap consumidor canvia encara.

**PAS 3 — `garmentCatalog` beu de la BD.** `garmentCatalog.js:18-24,76,107` usa `display_order`
i `nom_*` de BD, amb el vocabulari com a **fallback** (inversió de prioritat, no eliminació).
**Verd:** `NEWBORN` es pinta localitzat i en posició a `/poms`, `/garment-types` i el wizard
(captura abans/després). **Reversible:** sí.

**PAS 4 — Desenganxar el breadcrumb i el rètol.** `POMBrowser.jsx:14,262` pren el nom del
registre. Opcionalment, treure `/poms/grading` del namespace de POMs amb redirect.
**Verd:** el breadcrumb de POM Systems no importa res de `components/grading/`.

**PAS 5 — Partició de l'app. 🚩 DECISIÓ D'AGUS.** `fhort.taxonomy` (`GarmentGroup`,
`GarmentType`, `GarmentTypeGlobal`) + `fhort.sizing` (`SizeSystem`, `SizeDefinition`, `Target`,
`FitType`, `ConstructionType`), amb `SeparateDatabaseAndState` i **`db_table` explícit
conservat**. Les apps noves han d'anar **alhora a `SHARED_APPS` i `TENANT_APPS`**.
**Verd:** `makemigrations --check` net · `migrate` idempotent a `public`, `fhort` i `los` ·
`bootstrap_tenant` crea un tenant nou complet · el contracte `/api/v1/garment-groups/` idèntic
byte a byte. **Punt de no retorn:** el primer `makemigrations` que renombri una taula.

**PAS 6 — `GarmentType.grup` → FK. 🚩 DECISIÓ D'AGUS.** Amb una propietat pont `grup` que
retorni el codi, perquè `GarmentTypeSerializer` (`fields='__all__'`) no canviï de contracte.
**DESTRUCTIU sense el pont.**

**PAS 7 — Atrició de `GradingRuleSet.garment_group`.** Ja en marxa per disseny
(`serializers.py:225-228`); només cal completar el backfill de `applies_to` per als 18 rulesets.
**Verd:** `filter(garment_group__isnull=False).count() == 0` i el matching estricte
(`gradingAxes.js:212-224`) dona els mateixos resultats.

## 2.5 · Dades vives (tenant `fhort`, 2026-08-06)

| Taula / model | Files | Nota |
|---|---|---|
| `POMGlobal` (`public`) | 274 | Catàleg canònic |
| `GarmentTypeGlobal` (`public`) | 59 | |
| `POMMaster` · `POMCategory` · `CustomerPOMAlias` | 396 · **28** · 390 | `POMCategory` bruta (~15 conceptes) |
| **`GarmentPOMMap` (= els POM Systems)** | **1.748** | 0 orfes |
| `GarmentGroup` · `GarmentType` · `GarmentTypeItem` | 12 · 21 (17 actius) · 62 | **55 items tenen POM System**; 7 no |
| `SizeSystem` · `SizeDefinition` | 28 · 175 | |
| `GradingRuleSet` · `GradingRule` · `RuleSetScopeNode` | 47 · 1.288 · 11 (ITEM 9 · TYPE 1 · GROUP 1) | |
| `SizingProfile` · `ItemBaseSet` · `ItemBaseMeasurement` | 37 · **1** · 37 | |
| `Model` (`models_app`) | **0** | ⚠️ `fhort` no té models vius (V4, 06/08) |

**Referències creuades REALS:** `GradingRuleSet.garment_group` informat **18/47** (TOPS 8 ·
BOTTOMS 6 · SWIMWEAR 1 · DRESSES 1 · NEWBORN 1 · OUTERWEAR 1) · `.size_system` informat **40/47**
· `RuleSetScopeNode.garment_group` **1** · `Model.garment_group` **0** ·
`GarmentTypeItem.base_size_definition` **2/62** · `.grading_rule_set` **3/62** ·
`SizeSystem` sense cap ús **8/28**.

**Els 1.748 POM Systems per grup:** TOPS 517 · BOTTOMS 296 · OUTERWEAR 292 · DRESSES 281 ·
**NEWBORN 162** ← *absent del vocabulari del frontend* · UNDERWEAR 122 · SWIMWEAR 78.

**Estat del vocabulari:** només a BD (5): `DRESSES-FULL · KNITWEAR · NEWBORN · TOPS-KNIT ·
TOPS-WOVEN`. Només al codi: **0**. `GarmentGroup` sense cap `GarmentType` (4): `DRESSES-FULL ·
KNITWEAR · TOPS-KNIT · TOPS-WOVEN`. `GarmentType.grup` amb valor inexistent a `GarmentGroup`:
**0** — *per sort, no per constraint*.

## 2.6 · Les tres decisions que necessiten l'Agus

1. **Qui és l'amo del vocabulari de grup, la BD o el codi?** (PAS 2 — en depèn tota la resta.)
2. **Es parteix l'app `fhort.pom`** en `taxonomy` + `sizing` + `pom`? (PAS 5 — recordar que `pom`
   és l'única app SHARED+TENANT, `settings.py:53-55`.)
3. **`GarmentType.grup` passa de string a FK?** (PAS 6 — l'únic pas destructiu de veritat.)

---

# T3 · CENS DE LA BIBLIOTECA DE TALLES

> El cens complet (30 runs amb totes les columnes, els 37 `SizingProfile`, la classificació en
> cubells i la proposta de depuració) viu a **[`CENS_BIBLIOTECA_TALLES.md`](CENS_BIBLIOTECA_TALLES.md)**,
> perquè és una taula de treball i aquest document és de lleis. Aquí, el titular.

**30 runs** (28 a `fhort` + 2 a `los`), i **cap s'ha tocat**: el cens és una PROPOSTA.

| cubell | fhort | los | total |
|---|---|---|---|
| CANÒNIC (present a `public`) | 12 | 0 | 12 |
| CANÒNIC AMB DEFECTE → Agus | 2 | 0 | 2 |
| DE CLIENT REAL | 10 | 0 | 10 |
| DE CLIENT, dubtós → Agus | 2 | 0 | 2 |
| **BROSSA DE STAGING** | **2** | 0 | **2** |
| INCLASSIFICABLE → Agus | 0 | 2 | 2 |

🔑 **El discriminador dur és la pertinença al schema `public`** (14 codis = el catàleg de la
casa), **no** el nom ni el recompte. Els dos runs que proposo esborrar —`MEN-SHIRT-NUM` (26) i
`TGIRL-EU-HEIGHT` (6)— són **els únics dos de `fhort` que no existeixen a `public`**, i tots dos
tenen **les 6 FKs entrants a zero**: cap `SizingProfile`, cap `GradingRuleSet`, cap `ItemBaseSet`,
cap `Model`.

⚠️ **Els ids NO són els mateixos entre schemes.** `ALPHA_EU_W` és **29** a `fhort`, **1** a
`public` i **1** a `los`. Qualsevol creuament ha d'anar **per `codi`**, mai per `id`.

**Els 4 canònics** (no hi ha cap document al repo que els enumeri; aquests són els 4 amb
`SizeDefinition` completes *amb mesures corporals* + ús viu + presència a `public`):
`ALPHA_EU_W` (29) · `ALPHA_EU_M` (30) · `NUMERIC_EU_W` (32) · `BABY_EU_CM` (35).
**«BRW Run 01»** = `WOMAN_BRW_01` (**53**), `Dona ALPHA — Textiles y Confecciones Brownie SL Run 01`.

🚩 **Deute estructural que el cens ha destapat** (disseny, no depuració):

1. **`parent`/`derived_systems` és codi mort en dades**: `parent_id = NULL` a les 30 files, 0
   derivats. La derivació per client (`pom/models.py:585-598`) **mai s'ha estrenat**; l'eix
   client viu 100% a `customer_codi`. O s'usa o es jubila.
2. **`SizingProfile` no té `unique_together`**: P539/540/541 comparteixen la clau lògica
   (target+gt+constr+fit+ss) i només canvien de ruleset. Sense clau natural, la proliferació no
   té fre.
3. **`base_unit` no està validat contra les etiquetes**: **1 error de 24** ja viu (`TODDLER_EU`
   diu `AGE_YEARS` i porta alçades en cm). N1 hi ha posat l'algorisme
   (`pom/size_labels.py:dedueix_tipus_escala` + `conflicte_tipus_escala`); **falta el check**.
4. **`SizeDefinition.ordre` no és únic per `size_system`**: els runs 34 i 36 tenen `ordre`
   duplicats i **es llegeixen desordenats**. Un run desordenat és un grading incorrecte.
5. **7 runs de 30 no tenen cap `SizeDefinition`**, i dos d'ells (`los.1`, `los.2`) tenen **30
   Models a sobre** que, per tant, **no poden graduar**.

---

## APÈNDIX · el que la nit de N1-N4 ja ha consumit d'aquesta diagnosi

| Troballa | Qui la consumeix |
|---|---|
| T1.2 · el patró M2M + `SlugRelatedField(slug_field='codi')` | N1 — les 3 capes noves de `SizeSystem` |
| T1.3 · el veredicte GRUP = `GarmentGroup` | N1 — `SizeSystem.grups` apunta a `GarmentGroup`, no a `POMCategory` |
| T1.4 · «buit NO vol dir universal» | N3 — `proximitatCapa` retorna `SENSE`, ni primer ni últim |
| T3 · l'algorisme de deducció i els seus 3 indeduïbles | N1 — `size_labels.dedueix_tipus_escala` i la data migration `0063` |
| T3 · els 4 canònics i el BRW Run 01 | N3 — els fixtures de `proximitatRun.test.js` |
| T2 · **res** | 🛑 **Per ordre expressa: la desvinculació de POM System és NOMÉS Patró A aquesta nit.** Cap pas del §2.4 s'ha executat. |
