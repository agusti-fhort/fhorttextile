# DIAGNOSI — S03c · Navegació d'arxius

> Data: 2026-07-10 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`.
> Abast: 6 preguntes per desbloquejar el disseny de l'AssetNavigator, la derivació model→model
> i els pendents intercalats. Cap escriptura: només `SELECT` a la BD i lectura de codi.
> Convenció: `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi (no especulat).**
> Propostes només com `💡 PROPOSTA (a validar)`.
> No es re-cobreix el que ja és a `DIAGNOSI_S03_ARXIUS_2.md`.

**Dues correccions de partida (FETS):**
- El HEAD real és **`cc48ca8`** (commit de l'incident del 2026-07-10), no `655c325` com deia el brief.
  `655c325` és el seu pare, l'últim commit d'S03b.
- Ha aparegut `docs/diagnosis/DIAGNOSI_BACKOFFICE_POSTREFACTOR.md` sense trackejar, que no és
  d'aquesta sessió: hi ha una **sessió concurrent** treballant al repo.

---

## Resum executiu

1. **`generat_des_de` NO es pot reutilitzar per a model→model.** No perquè trenqui res —**no té
   cap lector, és write-only**— sinó perquè ja existeix el patró paral·lel (`derivat_de_item`) i
   barrejar "export derivat" amb "còpia importada" sota un sol camp amaga dues semàntiques.
   Cal FK nou `derivat_de_model`.
2. **🔴 La premissa de P5 ("un `.ftt` es copia tal qual") és FALSA per a model→model.** És certa
   per a catàleg→model (un `ItemFitxer` no porta dades de model). Un `.ftt` d'un model A porta
   **quatre coses materialitzades de A**: text congelat dels `field` de plantilla, l'asset
   `field_customer_logo.*` amb els bytes del logo de A, un objecte `image kind:'logo'` amb la URL
   de A, i `metadata{}`. Sense reescriptura, el document importat mostraria dades del model A.
3. **La capçalera, en canvi, es reescriu sola.** El `data_block kind:'header'` no desa cap valor:
   es reconstrueix a cada render des de `modelData`. Aquesta és la distinció que governa tot el
   disseny de la reescriptura.
4. **NO EXISTEIX cap endpoint d'agregació facetada** (clients amb comptador, temporades,
   col·leccions). L'únic precedent és `fase-counts`. Però amb **20 models · 2 clients · 3
   temporades · 2 col·leccions**, l'agregació server-side seria per correcció d'arquitectura, no
   per volum: avui es pot facetar al client.
5. **El contracte d'inserció al canvas és estret i clar:** tot acaba a `addObject`. Un navegador
   nou només ha de produir un objecte amb `id` (o `url_extern`) i cridar `addModelFitxer`.
6. **🔴 Endollar `validate_upload` a `upload_file_view` REBUTJARIA dades reals:** hi ha **1 fitxer
   `.xlsx`** pujat per aquesta via, i `.xlsx` no és a la whitelist.

---

# Q1 — Cerca facetada de models

## Q1.1 — Endpoints que llisten models

| Endpoint | Def | Paginat | N+1 |
|---|---|---|---|
| `GET /api/v1/models/` (`ModelViewSet`) | `models_app/views.py:43` | sí (`DefaultPagination`) | **controlat** (`select_related` + 3 `Subquery` + `Exists` + `prefetch_related`, `views.py:52-90`) |
| `GET /api/v1/model-task-items/by-model/` | `tasks/views_b.py:79-240` | sí | **controlat** (tot `values+annotate` a la BD) |
| `GET /api/v1/models/fase-counts/` | `models_app/views.py:97-133` | — | agregació pura |
| `GET /api/v1/plan/gantt/` | `planning/views.py:645-679` | **NO paginat** | `prefetch_related` (`:665-667`), però carrega totes les files |

Resposta de `ModelViewSet.list` (`ModelListSerializer`, `serializers.py:58-125`): `id, codi_intern,
codi_client, nom_prenda, collection, temporada, any, customer, customer_nom, has_order, created_at,
garment_type, garment_type_item_nom, fase_actual, responsable, prioritat, data_objectiu,
predicted_start/end, entrada_prod, arribada_proto, fitting_prev, tecnics[], slots_*`.

Resposta de `by-model` (`views_b.py:215-235`): `{model_id, model_codi, model_nom, fase,
counts:{pending,paused,in_progress,done}, kanban_state, prioritat, temporada, estat, data_objectiu,
responsable_id}`. **No és una llista de models**: és un agregador de `ModelTask` per model.

## Q1.2 — Facetes: què existeix

| Faceta | `ModelViewSet` | `by-model` | Tipus |
|---|---|---|---|
| `customer` | ✅ `views.py:39-40` | ✅ `views_b.py:156-158` | exacte (FK) |
| `temporada` | ✅ `views.py:39` | ✅ `views_b.py:120-122` | exacte |
| `collection` | ✅ `views.py:34` | ✅ `views_b.py:159-161` | **icontains**, no llista de valors |
| `any` | ✅ `views.py:39` | ✅ `views_b.py:146-148` | exacte |
| `garment_type` | ✅ `views.py:39` | ✅ `views_b.py:143-145` | exacte (FK id) |
| `fase_actual` | ✅ `views.py:39` | ✅ `views_b.py:126-128` | exacte |
| `estat` | ❌ **NO EXISTEIX** al `ModelFilter` (`views.py:39`) | ✅ `views_b.py:123-125` | asimetria |

## Q1.3 — Agregació per a drill-down

- Precedent existent: `fase-counts` (`views.py:97-133`), `.values('fase_actual').annotate(Count)`,
  respectant els mateixos filtres que el board.
- **Agregació per `customer`, `temporada`, `collection`, `any` o `garment_type`: NO EXISTEIX.**
  Cap `.values(<facet>).annotate(Count)` a cap view (grep confirmat). L'únic `.distinct()`
  (`views.py:2352,2358`) és a `registre_activitat_view`, sobre `ConsumptionRecord`.

## Q1.4 — Cerca de text lliure: dos mecanismes DIFERENTS

- `ModelViewSet`: `SearchFilter` de DRF, `search_fields = ['codi_intern','codi_client','nom_prenda']`
  (`views.py:45,47`).
- `by-model`: implementació **manual** amb `Q` (`views_b.py:109-114`), `icontains` sobre
  `model__codi_intern` OR `model__nom_prenda` — **només dos camps: no busca `codi_client`**.

## Q1.5 — Dades reals (schema `fhort`)

| | n |
|---|---|
| Models | **20** |
| Customers referenciats pels models | 2 (3 a `tasks_customer`) |
| Temporades distintes | 3 |
| Collections distintes | 2 |
| Anys distints | 2 |

> **Veredicte Q1:** el navegador facetat es pot construir **sense endpoint nou**: 20 models caben
> en una sola pàgina i les facetes es deriven al client. L'agregació server-side (`NO EXISTEIX`)
> és una decisió d'arquitectura, no una necessitat de volum. La faceta `estat` només existeix a
> `by-model`, i les dues cerques de text no cobreixen els mateixos camps.

---

# Q2 — Arbre del catàleg (GT → GTI → fitxers)

## Q2.1 — Jerarquia

- `GarmentType` — `pom/models.py:385-424`. Camps: `garment_type_global`, `codi_client`,
  `nom_client`, `grup` (CharField, **no** FK), `actiu`, `nom_en/ca/es`, `is_system`, etc.
- `GarmentTypeItem` — `tasks/models.py:280-339`. Pare:
  `garment_type = FK('pom.GarmentType', CASCADE, related_name='items')` (`:284-285`).
  `unique_together = ('garment_type','code')` (`:321`).
- `ItemFitxer.garment_type_item` → `related_name='fitxers'` (`models_app/models.py:454-455`).

Cadena completa: `GarmentType.items` → `GarmentTypeItem.fitxers` → `ItemFitxer`.

## Q2.2 — Endpoints

| Endpoint | Def | Filtres | Cerca | Comptadors |
|---|---|---|---|---|
| `GET /api/v1/garment-types/` | `pom/views.py:96-118` | `actiu`, `grup` (`:100`) | `codi_client,nom_client` (`:101`) | **`items_count`: NO EXISTEIX** |
| `GET /api/v1/garment-type-items/` | `tasks/views_b.py:812-824` | `garment_type`, `active` (`:818`) | **NO EXISTEIX** (`filter_backends` només `DjangoFilterBackend`, `:817`) | `poms_count` ✅ (`serializers_b.py:106,122-124`) · **`fitxers_count`: NO EXISTEIX** |

⚠️ `poms_count` fa `obj.pom_maps.count()` per fila sense prefetch (`serializers_b.py:122-124`) →
**N+1**: 57 items = 57 queries.

## Q2.3 — `ItemFitxerViewSet` i el que necessita un Finder

ViewSet: `models_app/item_fitxer_views.py:28-38`. Filtres: `['garment_type_item','tipus','is_current']`
(`:36`). Ordering: `data_pujada`, defecte `-data_pujada` (`:37-38`). Serializer:
`models_app/serializers.py:38-55`, `fields='__all__'` **tot read-only** (`:44-50`) + `download_url`.

| Camp de Finder | Estat |
|---|---|
| `download_url` (signada, D13) | ✅ `serializers.py:40,52-55` |
| `nom_fitxer`, `tipus`, `versio`, `is_current`, `mida_bytes`, `data_pujada`, `mimetype`, `checksum` | ✅ |
| `pujat_per` | ⚠️ s'emet com a **id (PK)**, no el nom del perfil (`models.py:465`) |
| `updated_at` / data de modificació | ❌ **el model no en té** |
| extensió / icona | ❌ derivable de `nom_fitxer`/`mimetype`, no emès |

## Q2.4 — Dades reals

| | n |
|---|---|
| `GarmentType` | 19 |
| `GarmentTypeItem` | 57 |
| **`ItemFitxer`** | **0** |
| (context) `ModelFitxer` | 218 |

> **Veredicte Q2:** l'arbre és construïble amb el que hi ha, però **sense comptadors** (ni items
> per GT, ni fitxers per GTI) i **sense cerca de text a GTI**. `ItemFitxer` té **0 files**:
> qualsevol vista de catàleg no té dades reals amb què validar-se avui.

---

# Q3 — Derivació model→model

## Q3.1 — `generat_des_de`: semàntica exacta

- Definició `models_app/models.py:385-391`. Comentari (`:382-384`): *"Enllaç (no cadena): per a
  artefactes generats des d'un altre fitxer, p.ex. un PDF EXPORT generat des d'una versió concreta
  del document .ftt."* Apunta del **fill** cap al **pare**.
- **Escriptor únic:** `services_ftt_document.py:238-239` (`save_export`), cridat des de
  `ftt_document_views.py:182` i, al front, `TechSheetEditor.jsx:3037`.
- **Lectors: NO EXISTEIX CAP.** Cap serializer l'exposa; cap view, admin ni `select_related` el
  llegeix; el `related_name='exports_generats'` no s'usa enlloc; al frontend només hi ha un
  **comentari** (`TechSheetEditor.jsx:3031`). **Camp write-only.**
- **BD:** `count(generat_des_de_id IS NOT NULL)` = **2**. Els dos són `fill=EXPORT, pare=TECHSHEET`.

**VEREDICTE (fets, no opinió).** Reutilitzar-lo per a "importat d'un altre model" **no trencaria
res tècnicament**, perquè no hi ha cap consumidor. El que passaria:

1. Contradiria el comentari del model (`models.py:382-384`) i el docstring de `save_export`
   (`services_ftt_document.py:224-229`), que declaren l'enllaç com a "artefacte generat des d'un
   altre fitxer".
2. **Ja existeix el canal paral·lel** per a còpies importades: `derivat_de_item` (Q3.2). Un germà
   model→model té el seu lloc natural allà, no a `generat_des_de`.
3. Les 2 files existents assumeixen implícitament `fill=EXPORT`. Un primer lector futur (p.ex.
   "llista els PDFs generats d'aquest `.ftt`" via `exports_generats`) rebria soroll.

## Q3.2 — `derivat_de_item`

- Definició `models.py:395-401` (FK `ItemFitxer`, `SET_NULL`, `related_name='usos_a_models'`).
- **Escriptor únic:** `item_fitxer_views.py:161-162,167` (`usar_al_model`).
- **Lectors: NO EXISTEIX CAP** (mateix patró). Al front, només un comentari a `endpoints.js:108`.
- **BD:** 0 files.

## Q3.3 — `usar-al-model`, per dimensionar el germà

`item_fitxer_views.py:120-170`. `POST /api/v1/item-fitxers/<pk>/usar-al-model/`, body `{model_id}`,
gate `IsAuthenticated` (`:135-137`). Passos: `get_object()` (`:142`) → 400 si l'origen no té bytes
(`:143-144`) → 400 sense `model_id` (`:146-148`) → `get_object_or_404(Model)` (`:149`) → reobre els
bytes i `save_model_file(model, origen.fitxer, tipus=origen.tipus, origen='upload',
nom=origen.nom_fitxer)` (`:154-159`, cadena nova `versio=1`) → `derivat_de_item = origen` (`:161`)
+ `pujat_per` (`:163-166`) → **201** amb `ModelFitxerSerializer` (`:169-170`).

> **Veredicte Q3: cal FK nou `derivat_de_model`.** No per col·lisió funcional (no n'hi ha: 0
> lectors) sinó perquè `generat_des_de` i `derivat_de_item` ja codifiquen **dues relacions
> diferents** (derivació d'artefacte vs procedència de còpia), i model→model és de la segona
> família. La forma de l'endpoint germà està completament dimensionada per `usar-al-model`.
> ⚠️ Però la còpia de bytes **no pot ser literal**: vegeu Q4.

---

# Q4 — Capçalera del `.ftt` i reescriptura en importar

## Q4.1 — Com s'identifica la capçalera

`document.json` = `{ftt_schema, metadata{}, pageFormat, pages:[{id, objects:[]}]}`
(`services_ftt.py:44-55`). Els objectes es discriminen per **`type`**, i els blocs de dades per
**`kind`** (no hi ha camp `field` com a discriminador: **`'field'` és un valor de `type`**).

- **`type:'data_block'` + `kind:'header'`** → la capçalera. Es crea a `TechSheetEditor.jsx:2995`;
  es renderitza amb `buildHeaderPrimitives()` (`:515-543`), via `HeaderBlock` (`:606-611`) en viu i
  el render offscreen (`:862-864`).
- **`type:'field'`** → xip individual de camp (placeholder). Render: `FieldChipNode`
  (`ObjectNode`, `:1041-1043`) i `buildFieldChipPrims` (`:499-510`).
- Altres `data_block`: `kind ∈ {graded_table, pom_fitting, pom_grading, bom, custom}`.

Al backend, la instanciació de plantilla (`services_ftt_document.py:140-170`) discrimina
`o.get('type') == 'field'` i, dins, `o.get('key') == 'customer_logo'`. **No toca mai els
`data_block kind:'header'`.**

## Q4.2 — Els camps lligats al model: dues famílies

**(A) `type:'field'` — catàleg `FIELD_CATALOG` a `TechSheetEditor.jsx:110-127`**, mirall de
`_placeholder_values` (`services_ftt_document.py:100-108`). 14 claus:
`nom_prenda`, `codi_intern`, `codi_client`, `customer_nom`, `collection`, `temporada_any`,
`color_referencia`, `descripcio`, `responsable_nom`, `data_entrada`, `base_size_label`,
`size_system_nom`, `fabric_main`, `fabric_composition`, `data_avui`.
En instanciar plantilla, `_resolve_obj` (`services_ftt_document.py:148-154`) els **congela**:
`{'type':'text', …, 'text': vals.get(key)}`. Queden **materialitzats com a text** dins `document.json`.

Més `customer_logo` (`services_ftt_document.py:123-129`): `_resolve_logo_obj` (`:111-137`) el
converteix de `field` a `image` amb `src:'assets/field_customer_logo.<ext>'` i **empaqueta els
bytes del logo dins el ZIP**.

**(B) `data_block kind:'header'`** (`TechSheetEditor.jsx:515-543`): `codi_intern`, `nom_prenda`,
`temporada`, `collection`, `garment_type_item_nom`, `size_system_nom`, `responsable_nom`, `versio`,
`customer_nom` i el logo. **Cap d'aquests es desa**: `serializeObject` (`:163-166`) elimina fins i
tot `src` dels `data_block`, i les primitives es reconstrueixen des de `modelData` a cada render.

**(C) Objecte `image` amb `kind:'logo'`** inserit a mà (`TechSheetEditor.jsx:2645`): `src` és la URL
del logo del model. `serializeObject` no en treu el `src` (només ho fa amb `data_block`), i
`_extract_inline_objects` (`services_ftt.py:144-156`) només reescriu `src` si és un `data:` dataURL
→ **la URL es desa literal**.

## Q4.3 — `_placeholder_values` corre UNA sola vegada

`services_ftt_document.py:95-108`. Construeix el mapa des de `ModelDetailSerializer(model).data`
(`:99`), amb `temporada_any` (`:106`) i `data_avui` (`:107`) derivats. `customer_logo` n'és absent a
propòsit (`:108`).

**Quan s'executa:** només `resolve_placeholders` el crida (`:164`), i `resolve_placeholders` només
s'invoca a `ftt_document_views.py:69-71` (`FttDocumentCreateView.post`, **quan hi ha `template_id`**).
**NO s'executa en desar** (`save_document`, `:197-220`, no el crida) ni enlloc més. Un cop congelat a
la v1, el text queda fix per sempre.

## Q4.4 — 🔴 Què cal reescriure en importar un `.ftt` de A a B

**(a) Es reescriuen SOLS (no cal tocar el document):** tota la capçalera `data_block kind:'header'`.
`buildHeaderPrimitives(m, …)` (`TechSheetEditor.jsx:515-543`) llegeix de `m = ctx.modelData = model`
(`:1019,3019,1024`). En obrir el `.ftt` sota el model B, mostra dades de B automàticament. El logo
de la capçalera també (`customerLogoUrl`, `:1358,863`).

**(b) Queden OBSOLETS amb dades de A → cal reescriure'ls:**

| # | Què | On es materialitza | Conseqüència |
|---|---|---|---|
| 1 | Text congelat dels `field` de plantilla | `services_ftt_document.py:148-154` | El `.ftt` mostraria codi/nom/client/temporada **de A** |
| 2 | Asset `assets/field_customer_logo.<ext>` | `services_ftt_document.py:123-128` | Bytes del logo del **client de A** dins el ZIP |
| 3 | Objecte `image kind:'logo'` amb URL | `TechSheetEditor.jsx:2645` + `services_ftt.py:148` (no el reescriu) | Apunta al logo **de A** |
| 4 | `document.json.metadata{}` | `services_ftt.py:52,180` | Metadades **de A** |

**Implicació directa:** l'afirmació de `usar-al-model` que *"un `.ftt` es copia tal qual… no cal
reescriure cap referència"* (`item_fitxer_views.py:129-131`) **és certa per a catàleg→model** (un
`ItemFitxer` no porta dades de model) i **és falsa per a model→model**.

> **Veredicte Q4: la llavor de la reescriptura ja existeix i és `resolve_placeholders`**
> (`services_ftt_document.py:140-170`). Però avui només sap anar de `field` → `text` (congelar).
> Per a l'import model→model caldria el camí invers o una re-resolució: descongelar (o re-resoldre)
> els 14 camps + regenerar l'asset del logo + purgar `metadata`. La capçalera no s'ha de tocar.

---

# Q5 — Punts d'inserció UI

## Q5.1 — Pàgina de GT / GTI

- `frontend/src/pages/GarmentTypes.jsx` — mestre-detall, **sense tabs**. `return` a `:101`; columna
  MESTRE `:119-148`; columna DETALL `:150-202` (capçalera `:154-172`, barra d'items `:174-180`,
  graella de cards `:182-199`). Navega a l'editor amb `navigate('/garment-type-items/<id>/editar')`
  (`:195`).
- `frontend/src/pages/ItemAuthoring.jsx` — **wizard de 2 passos**, sense tabs. Rutes a
  `App.jsx:265-266`. PAS 1 `:228-290`, PAS 2 `:292-330`. **Slot d'import inert: `:272-288`** (no tocar).

**Sistema de tabs reutilitzable: NO EXISTEIX com a component.** És un patró in-line, el de
referència a `ModelSheet.jsx`: array `TABS` (`:23`), etiquetes i18n separades (`TAB_LABELS`,
`:29-32`), estat sincronitzat amb `?tab=` (`:95,101`), banda de pestanyes (`:343-366`), commutació
(`:377-531`).

**Punt d'inserció d'una secció "Fitxers" de consulta d'un GTI:** dins la columna DETALL de
`GarmentTypes.jsx`, després de la graella de cards i abans de tancar el bloc (`:200`). Raons: aquella
columna ja és el lloc de consulta agregada del type i els seus items; no toca el wizard ni el slot
inert. Alternativa menys neta: una secció al PAS 2 d'`ItemAuthoring` (després de
`MeasurementBaseGrid`, `:328`) — barreja consulta dins un wizard d'autoria.

**Ja existeix el patró de llista de fitxers a nivell de MODEL:** tab "Fitxers" a `ModelSheet.jsx:528`
(`TabFiles`, definit a `:1209`), amb llista, pujada, versionat i esborrat.

## Q5.2 — FilePicker (S03b · P7)

`frontend/src/components/model/FilePicker.jsx` (195 línies).
Props (`:38`): `{modelId, garmentTypeItemId, onInsert, onClose}`. Estat (`:40-45`).
Pestanyes `TABS = ['model','catalog','import']` (`:21`), render `:159-165`.
Càrregues: `loadModel` (`:47-51`), `loadCatalog` (`:53-58`). Accions: `usarAlModel` (`:62-73`),
`importar` (`:75-98`). Drawer `<aside>` `position:absolute; right:0; width:340` (`:139-147`).

**Contracte amb `addModelFitxer`** (`TechSheetEditor.jsx:2773-2791`): l'objecte `f` necessita
`f.url_extern` **o** `f.id` (per construir `/api/v1/model-fitxers/<id>/download/` amb `uploadHeaders`,
`:2779,2782`); sense cap dels dos, `return` silenciós (`:2780`). Muntatge:
`onInsert={(f) => { addModelFitxer(f); setFilePicker(false) }}` (`TechSheetEditor.jsx:3598`).

| Element | Rigidesa |
|---|---|
| `onInsert(f)` amb `f.id`/`f.url_extern` | **RÍGID** — és l'endoll real |
| Drawer `width:340`, ancorat dins `<main>` (`TechSheetEditor.jsx:3589,3594`) | **RÍGID** (o cal retocar el contenidor) |
| `TABS` (`:21`), `renderFiles` (`:100`), les 3 càrregues (`:47-58`) | **FLEXIBLE**, tot local |

## Q5.3 — Picker de fitxa tècnica (S03b · P6)

`frontend/src/pages/TechSheetEntry.jsx`. Cerca amb debounce 250 ms (`:59-62`), càrrega
`modelsApi.list({ordering:'-data_entrada', page_size:12, search})` (`:46-57`), **llista plana**
(`:148-169`). Contracte de sortida: `obrir(model)` (`:66-93`) i `obrirConsulta` (`:64`), que només
necessiten `model.id` (+ `codi_intern`/`nom_prenda` per mostrar). **Endoll:** substituir el bloc
`items.map` (`:157-168`); els handlers es mantenen intactes.

## Q5.4 — El botó d'import de garment i el punt d'inserció final

**FET, contra l'enunciat del brief:** el botó "Importar Garment" **no** està marcat "(aviat)": és
actiu. `ribbonTool key:'import-flat'` a `TechSheetEditor.jsx:3409` (i al menú Fitxer, `:3462`),
`onClick: () => openImport('garment')` (`openImport` a `:3293`).

Camí "La meva màquina" (`handleImportInsert`, `:3296-3310`):
- `importMode==='image'` → `handleFile(importFile)` (`:3299`)
- SVG → `handleFlatSvgFile` (`:3305`) → `:2707-2715` → `importFlatSvgText` (`:2673-2706`)
- **DXF → `flash(t('tech_sheet.import_dxf_soon'))` (`:3308`)** ← *aquest* és el "aviat" real

**Punt d'inserció terminal: `addObject`.** Hi arriben:
- imatges: `addImageFromDataURL` (`:2625-2628`) → `addObject` (`:2627`)
- SVG de garment: `importFlatSvgText` → `addObject` (`:2704`)
- FilePicker: `addModelFitxer` (`:2773`) → `addImageFromDataURL` → `addObject`

Un navegador nou ha d'acabar exactament aquí: `addImageFromDataURL(dataURL)` per a imatges o
`importFlatSvgText(svgText)` per a SVG editables.

**Botons "(aviat)" relacionats amb import:**

| Element | fitxer:línia | Contracte anunciat |
|---|---|---|
| `import-measures` (`disabled:true`) | `TechSheetEditor.jsx:3411` | importar mesures |
| DXF dins `handleImportInsert` | `TechSheetEditor.jsx:3308` | DXF anunciat, no suportat |
| Slot inert d'`ItemAuthoring` | `ItemAuthoring.jsx:272-288` | import de garment a nivell de GTI (Fase C) — **no tocar** |

---

# Q6 — Pendents intercalats (verificació de zona)

## Q6.1 — DELETE i bytes

- `ModelFitxerViewSet` (`views.py:146`) hereta `destroy` de `mixins.DestroyModelMixin`
  (`rest_framework/mixins.py:89-95`): `perform_destroy → instance.delete()`. Des de Django 1.3 el
  `FileField` no s'engancha a `post_delete` → **esborra la fila, no els bytes**.
- `ItemFitxerViewSet` (`item_fitxer_views.py:28-30`): idèntic, tampoc sobreescriu `perform_destroy`.
- **Precedent correcte:** `extraction_views.py:66-75` (`delete_model_view`) fa
  `default_storage.delete(fitxer.fitxer.name)` amb guard `default_storage.exists(...)` dins un
  `try/except` que no bloqueja.
- Altres esborrats de bytes al backend: `tasks/views_b.py:740` i `pom/s2_views.py:312`, tots dos amb
  `field.delete(save=False)` (logos) — **idioma diferent** del precedent; `pom/s9_views.py:200`
  (`os.unlink` d'un temporal, no és media).

**Conclusió: cap dels dos ViewSets de fitxers esborra bytes.** Confirma l'origen dels orfes.

## Q6.2 — 🔴 `validate_upload` a `upload_file_view`: hi ha un obstacle real

- `upload_file_view` (`views.py:1130-1179`): `request.FILES.get('fitxer')` (`:1136`),
  `nom = request.data.get('nom') or uploaded_file.name` (`:1145`), i passa **directe** a
  `save_model_file` (`:1152`). **No crida `validate_upload`.**
- `validate_upload(file, nom=None)` (`services_fitxers.py:47-60`) només llegeix `file.name` i
  `file.size`, tots dos amb `getattr` defensiu. `ItemFitxerViewSet.create` ja el crida
  (`item_fitxer_views.py:66`). **Els dos endpoints reben el mateix tipus** (`UploadedFile`).
  **Tècnicament s'hi endolla tal qual.**

**Però les dades reals ho impedeixen.** Extensions a `fhort.models_app_modelfitxer` (218 files,
**totes `origen='upload'`**):

| ext | n | dins la whitelist? |
|---|---|---|
| `.ftt` | 213 | ✅ |
| `.pdf` | 4 | ✅ |
| **`.xlsx`** | **1** | 🔴 **NO** |

`ALLOWED_UPLOAD_EXTENSIONS` (`services_fitxers.py:33-41`) = `.ftt .pdf .dxf .svg .rul .txt .png .jpg
.jpeg .webp .gif`. **Endollar `validate_upload` tal qual faria que un `.xlsx` (que avui s'accepta i
existeix a la BD) rebés un 400.**

## Q6.3 — `serve_fitxer` i la fila fantasma

- Guard: `services_fitxers.py:198` → `if not fitxer.fitxer:` → `JsonResponse(…, status=404)` (`:200`).
- `FileResponse` (DEBUG): `services_fitxers.py:205`.
- Branca X-Accel: `:209` (`os.path.relpath(fitxer.fitxer.path, …)`) i `:211` (capçalera).

**Per què la fantasma passa el guard:** un `FieldFile` és *falsy* només si no té `name`. Una fila
fantasma **té nom** i no té bytes → `bool(fitxer.fitxer) == True` → el guard de `:198` no dispara.
El guard comprova **existència de nom, no de bytes**.

**On peta, segons l'entorn:**
- **DEBUG** → línia **205**, `fitxer.fitxer.open('rb')` → `FileNotFoundError` → **500 no controlat**.
- **Producció (X-Accel)** → línia `:209` no toca el disc i `:211` emet la capçalera; **Python no
  llança**. El **404 el genera nginx** en no trobar el fitxer a `/protected-media/`, sense el JSON
  del contracte de `:200`. El símptoma difereix per entorn.

## Q6.4 — `move_media_tenant` i els owners

- `os.makedirs(os.path.dirname(dst), exist_ok=True)` → **línia 102**.
- `shutil.move(src, dst)` → **línia 103**. Totes dues dins `if apply:` (`:101`).

**Evidència de la stdlib** (`/usr/lib/python3.14/shutil.py`): `shutil.move` (`:876`) intenta primer
`os.rename` (`:924`). Si és el **mateix filesystem**, mou l'inode → **preserva owner, mode, mtime**.
Si és **cross-filesystem**, cau a `copy2` + `os.unlink` (`:942-943`); i `copy2` (`:493`) crida
`copystat` (`:440`), que copia `utime`, `chmod`, xattr i flags — **però NO fa `chown`**.

**Owners esperats després d'un `--apply` com a root:**

| | Owner |
|---|---|
| (a) Directoris nous (`os.makedirs`, `:102`) | **root**, sempre |
| (b) Fitxers moguts, mateix FS (`os.rename`) | preserven l'origen (`www-data`) |
| (b') Fitxers moguts, cross-FS (`copy2`) | **root** (`copy2` no fa `chown`) |

**Estat actual** de `media/fhort/`: `www-data:www-data`, 0 fitxers i 0 directoris fora de `www-data`.
Com advertia el brief, **això no prova res**: ja s'hi va aplicar un `chown -R` a l'incident del
2026-07-10. El raonament des del codi confirma la causa: `os.makedirs` (`:102`) va crear els
directoris com a **root**, que és exactament el que va trencar tota escriptura a media.

---

# TAULA FINAL — per al CTO

| # | Fet | Estat | Referència | Impacte |
|---|---|---|---|---|
| 1 | Agregació facetada (customer/temporada/collection/any/GT) | **NO EXISTEIX** | grep a views | 🟢 20 models: facetable al client |
| 2 | Faceta `estat` al `ModelViewSet` | **NO EXISTEIX** (sí a `by-model`) | `views.py:39` vs `views_b.py:123` | 🟠 asimetria |
| 3 | Les dues cerques de text cobreixen camps diferents | **DIFERENT** | `views.py:47` vs `views_b.py:109-114` | 🟠 `codi_client` només al ViewSet |
| 4 | Comptadors `items_count` / `fitxers_count` | **NO EXISTEIXEN** | `pom/serializers.py:110`, `serializers_b.py:100` | 🟠 l'arbre no pot mostrar-los |
| 5 | Cerca de text a `garment-type-items/` | **NO EXISTEIX** | `views_b.py:817` | 🟠 |
| 6 | `poms_count` fa N+1 (57 queries) | **EXISTEIX** | `serializers_b.py:122-124` | 🟠 fora d'scope |
| 7 | `ItemFitxer` a la BD | **0 files** | `SELECT count(*)` | 🟠 res per validar |
| 8 | `pujat_per` s'emet com a id, no nom | **EXISTEIX** | `serializers.py:38-55` | 🟢 Finder ho vol resolt |
| 9 | `generat_des_de`: lectors | **NO EXISTEIXEN** (write-only, 2 files EXPORT→TECHSHEET) | `models.py:385-391` | 🟢 no trenca, però no s'ha de reutilitzar |
| 10 | `derivat_de_item`: lectors | **NO EXISTEIXEN** (write-only, 0 files) | `models.py:395-401` | 🟢 |
| 11 | **`.ftt` model→model NO és copiable tal qual** | **4 punts materialitzats de A** | Q4.4 | 🔴 **Alt** |
| 12 | La capçalera `kind:'header'` es reescriu sola | **EXISTEIX** | `TechSheetEditor.jsx:515-543,163-166` | 🟢 |
| 13 | `resolve_placeholders` corre **només** a instanciar plantilla | **EXISTEIX** | `ftt_document_views.py:69-71` | 🟠 llavor de la reescriptura |
| 14 | Sistema de tabs reutilitzable | **NO EXISTEIX** (patró in-line a `ModelSheet.jsx:23,343-366`) | | 🟢 |
| 15 | Contracte d'inserció: tot acaba a `addObject` | **EXISTEIX** | `TechSheetEditor.jsx:2627,2704` | 🟢 endoll clar |
| 16 | `onInsert(f)` exigeix `f.id` o `f.url_extern` | **EXISTEIX** | `TechSheetEditor.jsx:2779-2782` | 🟢 |
| 17 | El botó d'import de garment **no** és "(aviat)" | **EXISTEIX i és actiu** | `TechSheetEditor.jsx:3409` | 🟢 el "aviat" és el DXF (`:3308`) |
| 18 | `destroy()` dels dos ViewSets no esborra bytes | **CONFIRMAT** | `mixins.py:89-95` | 🟠 origen dels orfes |
| 19 | Precedent correcte d'esborrat de bytes | **EXISTEIX** | `extraction_views.py:66-75` | 🟢 |
| 20 | **`.xlsx` a la BD (1 fila) fora de la whitelist** | **CONFIRMAT** | `services_fitxers.py:33-41` | 🔴 **bloqueja endollar `validate_upload` tal qual** |
| 21 | Guard de `serve_fitxer` mira nom, no bytes | **CONFIRMAT** | `services_fitxers.py:198` | 🟠 500 en DEBUG (`:205`), 404-nginx en prod |
| 22 | `os.makedirs` crea dirs amb l'owner del procés | **CONFIRMAT (codi + stdlib)** | `move_media_tenant.py:102` | 🔴 causa provada de l'incident |
| 23 | `shutil.move` preserva owner només same-FS | **CONFIRMAT** | `shutil.py:924,942-943,493,440` | 🟠 |

---

## 💡 PROPOSTES (a validar — NO són decisions)

1. **FK nou `derivat_de_model`** (paral·lel a `derivat_de_item`), no reutilitzar `generat_des_de`
   (taula #9). Cap dels tres camps té lectors: val la pena decidir alhora **qui els llegirà**
   (un badge de procedència al Finder?) abans d'afegir-ne un tercer write-only.
2. **La còpia model→model necessita una passada de reescriptura** (taula #11). La llavor és
   `resolve_placeholders`; caldria decidir si els `field` congelats es **re-resolen** contra el
   model B o es **descongelen** a `type:'field'` per re-resoldre's en el proper desat.
3. **Endollar `validate_upload` a `upload_file_view` exigeix decidir sobre `.xlsx`** (taula #20):
   afegir-lo a la whitelist, o acceptar que aquell fitxer històric ja no es podria re-pujar.
4. **`move_media_tenant` hauria de fer `chown` dels directoris que crea** (taula #22), o el runbook
   ha d'exigir-lo. La causa està provada des del codi, no és conjectura.
5. **Facetar al client** (taula #1): amb 20 models no cal endpoint nou. Si un dia cal, `fase-counts`
   (`views.py:97-133`) és el patró a clonar.
6. Si l'AssetNavigator ha de servir alhora `model-fitxers` i `item-fitxers`, convindria **convergir**
   amb `TabFiles` (`ModelSheet.jsx:1209`) en lloc de duplicar-lo — llei "no més pedaços" del
   `CLAUDE.md`.

---

## TROBALLES TRANSVERSALS (anotades, NO investigades — fora d'scope)

- `GarmentTypeItemSerializer.get_poms_count` (`serializers_b.py:122-124`) fa N+1 sobre 57 items.
- Dos idiomes de neteja de bytes conviuen: `default_storage.delete` (`extraction_views.py:70`) vs
  `field.delete(save=False)` (`views_b.py:740`, `s2_views.py:312`).
- `GarmentTypes.jsx:41-46` vs `:48-55`: dues càrregues gairebé idèntiques de `garmentTypes.list`.
- El sistema pot tenir **bytes-sense-fila** (Q6.1) i **fila-sense-bytes** (Q6.3) alhora: asimetria
  estructural, cap dels dos costats té guard.
- Sessió concurrent al repo: `docs/diagnosis/DIAGNOSI_BACKOFFICE_POSTREFACTOR.md` sense trackejar.

Cap línia de codi tocada en aquesta sessió.
