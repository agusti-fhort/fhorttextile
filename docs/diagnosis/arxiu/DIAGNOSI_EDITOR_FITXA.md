> ⚠️ SUPERADA 2026-07-07 — estructura eliminada (model TechSheet O2O, migració 0050); substituïda per DIAGNOSI_EDITOR_ESTAT. Consulta només com a històric.

# DIAGNOSI — Editor de fitxa tècnica + integració .ftt

> Sessió de diagnosi (Patró B), **READ-ONLY absolut**. Cap codi tocat, cap migració, cap push.
> Staging `/var/www/ftt-staging`, branca `dev`. Data: 2026-06-27.
> Regla: FETS amb referència `fitxer:línia`. Idees només com `💡 PROPOSTA (a validar)`.
> Decisions finals = de l'Agus (`⚖️`).

Objectiu: mapejar l'editor de fitxa tècnica actual i tots els punts d'integració per **fixar el
contracte `.ftt`** (zip propietari guardat al Finder del Model com a `ModelFitxer` tipus `TECHSHEET`,
versionat amb la invariant `is_current`/`save_model_file`) **sense endevinar**. No es construeix res.

---

## RESUM EXECUTIU (per a l'Agus)

- **El document actual NO és un fitxer.** És el model `TechSheet` (O2O amb `Model`), amb el dibuix
  dins `template_json` (JSONField). Migrar O2O→fitxer és **barat**: a la BD del tenant `fhort` només
  hi ha **5 files TechSheet, 4 d'elles buides (`{}`), i només 1 amb contingut real v2** (taula a baix).
- **El format v2 ja està de facto definit pel frontend** (`{version:2, pages:[{id, objects:[...]}], pageFormat}`)
  i el backend és **opac** (no valida res). Mapejar `template_json` → `document.json` del `.ftt` és gairebé
  una renomenada de l'arrel + decidir on van els binaris (imatges) dins el zip.
- **L'export ja produeix un PDF** (Konva offscreen → PNG → `pdf-lib`) però **es descarrega al navegador;
  NO es puja al Finder**. Falta exactament l'últim pas (upload via `save_model_file`).
- **El lock cooperatiu existeix i funciona** (TTL 30 min, force-if-stale, override CONFIGURE a l'unlock),
  però té el **timer-gap confirmat**: l'autosave NO renova `locked_at` i el frontend NO fa heartbeat.
- **El backend ja encaixa un `tipus='TECHSHEET'` sense tocar la invariant** (`tipus` és CharField lliure;
  `save_model_file` és agnòstic al tipus). Falta exposar `tipus` al serializer del Finder i un botó "Edita".
- **Orfes confirmats per dades:** `estat` (mort, 0 files ≠ 'obert'), `versio` (mort d'escriptura, sempre 1),
  clau `schemas` legacy (0 files l'usen → fallback retirable).

---

## DADES DE BD (tenant `fhort`, read-only · psql :5433)

| Mètrica | Valor | Implicació |
|---|---|---|
| Files `models_app_techsheet` | **5** | Migració O2O→fitxer trivial |
| …amb clau `pages` (v2) | **1** | Només 1 fitxa amb contingut real |
| …amb `template_json = {}` | **4** | 4 fitxes buides (mai editades) |
| …amb clau `schemas` (legacy) | **0** | Fallback `schemas` mai s'activa → retirable |
| …amb `estat <> 'obert'` | **0** | `estat` mort (sempre 'obert') |
| …amb `versio > 1` | **0** | `versio` mai incrementada (sempre 1) |
| Files `models_app_techsheettemplate` | **0** | Cap plantilla per Customer creada |

---

# FETS

## BLOC 1 — MODEL I FORMAT DEL DOCUMENT ACTUAL

### 1.1 Model `TechSheet` — O2O amb Model, dibuix a `template_json`

`backend/fhort/models_app/tech_sheet_models.py:14-54` (migració `0034_techsheet.py`):

| Camp | Tipus | Línia |
|---|---|---|
| `model` | `OneToOneField(Model, CASCADE, related_name='tech_sheet')` | `tech_sheet_models.py:20-24` |
| `estat` | `CharField(10, choices=[obert,tancat], default='obert')` | `:25` (choices `:15-18`) |
| `versio` | `PositiveIntegerField(default=1)` | `:26` |
| **`template_json`** | **`JSONField(default=dict, blank=True)`** | **`:27`** |
| `locked_by` | `FK(User, SET_NULL, null, related_name='tech_sheets_locked')` | `:30-35` |
| `locked_at` | `DateTimeField(null, blank)` | `:36` |
| `last_editor` | `FK(User, SET_NULL, null, related_name='tech_sheets_edited')` | `:39-44` |
| `created_at` / `updated_at` | `auto_now_add` / `auto_now` | `:46-47` |

Existeix també `TechSheetTemplate` (O2O amb `tasks.Customer`), **mateix format v2**, declarat "opac per al backend"
— `tech_sheet_models.py:57-77` / migració `0036_tech_sheet_template.py`. **0 files a BD.**

### 1.2 Estructura REAL de `template_json` v2 — definida pel frontend, opaca al backend

El backend **no valida ni defineix** l'estructura: no hi ha cap `get('pages')`/`get('type')`/`get('elements')`
als views ni al model; l'únic accés és el serializer comptant pàgines (BLOC 4). L'estructura la fixa i
serialitza `frontend/src/pages/TechSheetEditor.jsx`:

- **Arrel v2**: `{ version: 2, pages: serializePages(pages), pageFormat }` — `TechSheetEditor.jsx:623`.
  Lectura condicionada a `tj.version === 2 && Array.isArray(tj.pages)` — `:575`.
- **Pàgina**: `{ id, objects: [...] }` — `serializePages`, `:355-363`.
- **Objecte** (camp comú `layer` ∈ `template`|`data`|`free`, `LAYER_ORDER` `:51`; coords en mm, `toMm`/`toPx` `:56-57`).
- **TIPUS D'ELEMENT** (`type`):

| `type` | variants / camps | creació | render live | render export |
|---|---|---|---|---|
| `text` | text_box (`bgFill`,`bgPadding`); `fontSize,fontFamily,fill,width,height` | `:735-740` | `:404-412` | `:284-289` |
| `rect` | `rect_round` (`cornerRadius`); `fill,stroke,strokeWidth` | `:771` | `:419-422` | `:295` |
| `ellipse` | `rx,ry,fill,stroke,strokeWidth` | `:774` | `:424-427` | `:301` |
| `line` | `line_dot` (`dash`); `points[],stroke,strokeWidth` | `:776,781` | `:429-432` | `:307` |
| `arrow` | `arrow2`; `x,y,x2,y2,stroke,fill` | `:779` | `:434-439` | `:312` |
| `image` | `kind:'logo'`; `src` (dataURL) | `:801,820` | `:441-442` | `:335` |
| `data_block` | `kind:'header'` / `kind:'graded_table'` (`size_fitting_id,scale`) | `:855-859,878-881` | `:388-400` | `:318-325` |

Dos motors de render coherents: **React-Konva live** (switch `ObjectNode` `:387-444`) i **Konva offscreen**
(if-chain a `renderPageToDataURL` `:283-346`). Les taules/capçaleres es despleguen a primitives
`{t:'r'|'l'|'t'}` via `buildTablePrimitives` (`:126-182`) i `buildHeaderPrimitives` (`:187-215`).

> Nota de serialització: `serializePages` **elimina `src`** dels `data_block` abans de desar (dataURL volàtil)
> — `:359`. Les imatges (`type:'image'`) SÍ desen `src` com a dataURL dins el JSON.

### 1.3 Serializer `TechSheetSerializer` — `tech_sheet_serializers.py:8-32`

- **Camps exposats** (`Meta.fields` `:17-19`): `id, model_id, estat, versio, template_json, locked_by_id,
  locked_by_username, updated_at, num_pages, has_content`. → **SÍ exposa `template_json`** (rellevant per BLOC 4).
- **read_only**: `model_id` `:9`, `locked_by_id` `:10`, `locked_by_username` `:11,21-22`, `has_content` `:12,24-27`,
  `num_pages` `:13,29-32`.
- **El serializer mai desa**: no té `update()`/`create()`; només s'usa per RESPONDRE (`TechSheetSerializer(sheet).data`).
  La persistència de `template_json` és **manual** al view (BLOC 3).

### 1.4 Endpoints de l'editor — `tech_sheet_editor_views.py` (rutes `urls.py:147-162`)

| Verb | Ruta | Vista (línia) | Funció |
|---|---|---|---|
| GET | `models/<id>/tech-sheet/` | `TechSheetDetailView.get` `:75-77` | `get_or_create` + serialitza; aplica plantilla si nova i buida (`_get_sheet` `:34-45`) |
| POST | `models/<id>/tech-sheet/lock/` | `TechSheetLockView.post` `:83-110` | Adquireix lock; 409 si ocupat vigent |
| POST | `models/<id>/tech-sheet/unlock/` | `TechSheetUnlockView.post` `:116-135` | Allibera; 403 si no propietari ni CONFIGURE |
| **PATCH** | `models/<id>/tech-sheet/update/` | `TechSheetUpdateView.patch` `:145-166` | **Desa `template_json`**; 403 sense lock propi |
| GET | `customers/<id>/tech-sheet-template/` | `get_or_create_template` `:179-183` | Plantilla per Customer |
| PATCH | `customers/<id>/tech-sheet-template/update/` | `update_template` `:186-203` | Desa plantilla; gated CONFIGURE |

Extracció IA (CREAR model, no editor): `models/extract-sheet/` (`tech_sheet_views.py:62`) i
`models/create-from-sheet/` (`:245`) — fora de l'editor.

### 1.5 Frontend: càrrega i desat de `template_json`

- **Càrrega consulta**: `GET .../tech-sheet/` → `setSheet(data)` + `hydrate(data)` — `TechSheetEditor.jsx:530-541`.
- **Càrrega edició** (`?task_id=`): la hidratació ve de la **resposta del `POST .../lock/`**, no del GET — `:543-552`.
- `hydrate()` `:572-582`: accepta v2 (`pages` array), reposa `id` per pàgina/objecte, restaura `pageFormat` (fallback `A4L`).
- **Desat únic = autosave**: `PATCH .../tech-sheet/update/` amb `{template_json:{version:2,pages,pageFormat}}`,
  debounce **2000 ms**, només amb lock — `:613-627`. No hi ha botó "desar" explícit.

---

## BLOC 2 — PIPELINE D'EXPORT (PDF)

`onExport` — `TechSheetEditor.jsx:899-921`. Cadena document→PDF:

1. `PDFDocument.create()` (`pdf-lib`, import `:6`) — `:902`.
2. Per pàgina: **`renderPageToDataURL(p, 3.5, ctx)`** — `:906`. Aquesta funció (`:273-351`) crea un
   **`Konva.Stage` OFFSCREEN** (div desacoblat del DOM `:276-279`), pinta fons blanc, ordena per `layer`,
   afegeix objectes imperativament (if-chain `:283-346`, `await loadImageEl` per imatges), `layer.draw()` `:347`
   i retorna **`stage.toDataURL({pixelRatio, mimeType:'image/png'})`** `:348` (PNG a pixelRatio 3.5).
3. `pdf.embedPng(dataUrl)` — `:907`.
4. `pdf.addPage([pdfW,pdfH])` (mides en punts del format, `fmt.pdf`) — `:904,908`.
5. `page.drawImage(png, {x:0,y:0,width:pdfW,height:pdfH})` — `:909`.
6. `pdf.save()` → `bytes` — `:911`.

**Destí del PDF: descàrrega al NAVEGADOR** — `Blob` → `URL.createObjectURL` → `<a download>` sintètic
`a.click()` → `revokeObjectURL` — `:912-918`. Nom: `${model.codi_intern||id}_fitxa_v${sheet.versio}.pdf` `:916`.
**Cap `fetch`/upload al backend ni cap referència a "Finder" en tot l'export.**

> 🎯 Punt d'enganxament B5: aquí (`:911-918`) és on s'inserta l'upload al Finder en comptes (o a més) de la descàrrega.

---

## BLOC 3 — LOCK COOPERATIU + TIMER-GAP

### 3.1 Mecànica backend — `tech_sheet_editor_views.py`

- Camps: `locked_by` (`tech_sheet_models.py:30-35`), `locked_at` (`:36`). TTL = constant de mòdul
  `LOCK_TTL = timedelta(minutes=30)` — `tech_sheet_editor_views.py:31` (NO és camp de BD).
- **Adquisició** (`TechSheetLockView.post` `:83-110`): `is_free`/`is_mine`/`is_stale`
  (`locked_at < now - LOCK_TTL`, `:90-94`) → reassigna `locked_by`+`locked_at` `:96-100`; sinó **409** `:103-110`.
- **Override CONFIGURE**: NOMÉS a l'**unlock** (`TechSheetUnlockView.post` `:116-135`):
  `can_override = CONFIGURE in get_capabilities(user)` `:121`; 403 si no propietari ni override `:123-130`.

### 3.2 TIMER-GAP — CONFIRMAT (fet, no hipòtesi)

- **Backend**: `TechSheetUpdateView.patch` `:145-166` desa amb
  `sheet.save(update_fields=['template_json','last_editor','updated_at'])` `:165`.
  **`locked_at` NO apareix a `update_fields` ni s'assigna enlloc del mètode.** L'únic codi que toca `locked_at`
  és l'adquisició (`:99`) i l'unlock (`:134`).
- **Frontend**: `grep` a `TechSheetEditor.jsx` → `setInterval` **0**, `heartbeat` **0**, `locked_at` **0**,
  `renew` **0**. `keepalive` només a `:560,564` (opció `fetch(keepalive:true)` de la **neteja al desmuntatge**,
  no renovació). Lock = un `POST lock/` al muntar (`:544`) + un `POST unlock/` al desmuntar (`:563-565`).
  L'autosave (`:613-629`) envia exclusivament `{template_json}` (`:623`) — no toca el lock.

> **Conseqüència real:** un usuari editant activament (autosaves cada 2 s) **NO renova el seu lock**.
> Als 30 min des de l'**adquisició inicial**, un altre usuari pot fer force-if-stale (`:90-94`) i prendre-li
> el lock tot i que estigui treballant. El frontend de la víctima no se n'assabenta (no rellegeix el lock).

---

## BLOC 4 — 🔴 VELL/ORFE (a jubilar)

| Element | Escriptor backend | Lector | Dades BD | Veredicte |
|---|---|---|---|---|
| `TechSheet.estat` `:25` | **CAP** (sempre `default='obert'`) | serializer `:17`; front **no** l'usa (0 occ.) | 0 files ≠ 'obert' | **RETIRABLE** |
| `TechSheet.versio` `:26` | **CAP** (mai `+=`) | front el pinta (header, nom PDF, badge) `:202,635,877,903,916,1025,1067` | 0 files > 1 | **mort d'escriptura**; jubilació coordinada front+back (no unilateral) |
| `schemas` (serializer) | CAP (només fallback lectura `:26,31,48,53`) | 4 línies serializer | **0 files l'usen** | **RETIRABLE** (confirmat per dades) |
| Comentari `TechSheetEditor.jsx:536-539` | — | — | — | **OBSOLET/FALS** (veure sota) |

**Comentari stale `TechSheetEditor.jsx:536-539`** (literal): afirma que «el `TechSheetSerializer` actual NO
exposa `template_json`… `data.template_json` és undefined… hydrate cau a pàgina buida». **És fals avui**: el
serializer SÍ exposa `template_json` (`tech_sheet_serializers.py:17-19`). El comentari descriu un estat passat
del backend. **Retirable** (només comentari; cap risc).

> Matís `versio`: retirar-lo unilateralment al backend faria que el front mostrés `undefined → ?? 1`. Com que
> sempre val 1, és cosmètic. ⚖️ Decisió: jubilar del tot o reconvertir-lo en el versionat real del `.ftt`
> (que SÍ tindrà versions via `ModelFitxer.versio`).

---

## BLOC 5 — INTEGRACIÓ AMB EL FINDER

### 5.1 `ModelFitxer` — `backend/fhort/models_app/models.py:328-397`

- `model = FK(Model, CASCADE, related_name='fitxers')` `:344`.
- **`tipus = CharField(max_length=30, default='ALTRES', blank=True)` — SENSE choices** `:347`. Valors emesos
  en codi: `'ALTRES'` (`services_fitxers.py:67`), `'DOCUMENT'` (`extraction_views.py:1410`). **No existeix `TECHSHEET`.**
- `categoria = CharField(20, choices=CATEGORIA_CHOICES)` `:346` — choices `Patro,Disseny,Fitting,Document` `:329-334`.
- `versio = PositiveIntegerField(default=1)` `:348`; `is_current = BooleanField(default=True, db_index=True)` `:350`
  (invariant doc. `:349`); `versio_anterior = FK('self', SET_NULL, related_name='versions_posteriors')` `:352-358`.
- `fitxer = FileField(upload_to='model_fitxers/%Y/%m/')` `:370`; `get_url()` `:377-382`; `mimetype` `:389`;
  `checksum`/`mida_bytes`/`origen` `:388,367,390`.

### 5.2 `save_model_file` — `backend/fhort/models_app/services_fitxers.py:36-86`

Signatura `save_model_file(model, file, *, versio_anterior=None, categoria=None, tipus=None, origen='upload', nom=None)`
`:37-38`, `@transaction.atomic` `:36`.
- Sense `versio_anterior`: `versio=1`, cadena nova `:60-61`. Amb: `versio=pred.versio+1` `:54-55` i **hereta
  `categoria`/`tipus` del predecessor** si no s'especifiquen `:56-59`.
- **Invariant**: crea amb `is_current=True` `:63-76` i marca el predecessor `is_current=False` `:82-84`. És
  **l'únic punt** que escriu `is_current`/`versio`.

> ✅ **CONFIRMAT**: un `tipus='TECHSHEET'` encaixa **sense tocar la invariant ni migrar**: `tipus` és lliure i
> la cadena es defineix per `versio_anterior`, agnòstica al tipus. ⚠️ `categoria` SÍ té choices → cal triar-ne
> una existent (p.ex. `'Document'`).

### 5.3 Finder (`TabFiles`) — `frontend/src/pages/ModelSheet.jsx`

- Muntatge: `ModelSheet.jsx:518` (`activeTab==='Fitxers' → <TabFiles modelId/>`); rutes `App.jsx:142,150`.
- `TabFiles` `:1199-1441`: llistat via `GET /api/v1/model-fitxers/?model=${id}&is_current=true&ordering=-data_pujada` `:1213`
  (només caps de cadena). Files `<FileRow>` `:1413-1416/1444-1470`; detall `<FileDetail>` `:1483-1548`.
- **Barra d'accions per fitxer** (`FileDetail` `:1527-1544`): Veure `:1528-1530`, Nova versió `:1531-1536`,
  Historial `:1537-1539`, Eliminar `:1540-1543`. Handlers: `handleUpload` `:1221-1246`, `openHistory` `:1248-1257`.
- `accept` d'upload **NO inclou `.ftt`** avui — `:1386,1534` (`.pdf,.png,.jpg,.jpeg,.svg,.webp,.gif,.dxf`).

### 5.4 Llançament de l'editor de fitxa avui — `App.jsx` + `TechSheetEditor.jsx`

- Ruta full-screen FORA del Shell: `App.jsx:121-125` (`/models/:id/fitxa`), lazy `App.jsx:27`. Germana
  `/clients/:id/plantilla` `:127-131`.
- Rep `id` per `useParams` i mode per query `?task_id` (`isEditMode`) — `TechSheetEditor.jsx:450-454`.
- Navegació des de `TechSheetTab` (`ModelSheet.jsx:530-642`): `navigate('/models/${id}/fitxa')` `:571,615,620`.
- ⚠️ Aquest editor opera sobre **`TechSheet`** (per model), **NO sobre `ModelFitxer`**. Avui **cap ruta obre un
  `ModelFitxer` en un editor**.

### 5.5 Llibreries — `frontend/package.json`

✅ `konva ^10.3.0` `:21`, `react-konva ^19.2.5` `:27`, `pdf-lib ^1.17.1` `:23`.
❌ **Cap lib de ZIP** (`jszip`/`fflate`/`adm-zip`) ni a `package.json` ni a `node_modules`.

---

## BLOC 6 — MENÚ LATERAL (grup "Disseny")

`frontend/src/components/layout/Sidebar.jsx` (dins `Shell.jsx`, `App.jsx:132-134`).

- Estructura: array **`navGroups`** `:45-75`; cada grup `{sectionKey, items[]}`. 4 grups existents
  (`section_projectes`, `section_config_tecnica` `:55-60`, `section_technical_studio`, `section_sistema`).
- Entrada leaf (`NavLeaf` `:144-175`): `to` (ruta) `:149,163`, `labelKey` (i18n) `:164`, `icon` (classe `ti-*`) `:163`,
  opcionals `cap` (capability) `:49,228-242`, `badgeKey` `:146`, `children` (submenú) `:178`.
- i18n: `frontend/src/i18n/{ca,es,en}.json`, namespace `nav` (`:230-271` als tres). Convenció `nav.section_<x>` /
  `nav.<x>`. **Cal afegir claus als TRES fitxers.**
- Icones: **Tabler webfont** via CDN (`index.html:8`), s'usen com `<i className={`ti ${item.icon}`}/>` `:163`
  (l'array porta `'ti-*'`). El paquet `@tabler/icons-react` `:18` existeix però NO s'usa al sidebar.

---

# 💡 PROPOSTA (a validar)

### P1 · Mapatge `template_json` v2 → `document.json` del `.ftt`
El v2 actual (`{version, pages:[{id,objects}], pageFormat}`) és pràcticament ja el `document.json`. Proposta:
- `document.json` = el v2 tal qual, amb `version` bumpat a un esquema `.ftt` (p.ex. `ftt: 1`).
- **Binaris fora del JSON**: avui `image.src` i les miniatures van com a dataURL dins el JSON (pesat). Dins el
  zip `.ftt`, moure-los a `assets/<hash>.png` i deixar `image.src = "assets/<hash>.png"`. Així el `document.json`
  queda lleuger i diffable.
- Estructura zip proposada: `document.json` + `assets/*` + opcional `preview.pdf` (l'export ja existent) + `meta.json`.

### P2 · On enganxar "Edita" al Finder
Botó condicional a la barra d'accions de `FileDetail` (`ModelSheet.jsx:1527-1544`), visible només si
`fitxer.tipus === 'TECHSHEET'` (o extensió `.ftt`). Requereix: (a) **exposar `tipus` al serializer** del Finder
(verificar `serializers.py`), (b) ampliar `accept` a `:1386,1534` amb `.ftt`, (c) navegar a una ruta d'editor nova.

### P3 · Ruta d'editor sobre `ModelFitxer`
Nova ruta full-screen `App.jsx` tipus `/models/:id/fitxers/:fitxerId/editar` (patró de `:121-125`), o reusar
`TechSheetEditor` parametritzat per llegir un `ModelFitxer` `.ftt` en comptes del `TechSheet`. Reutilitza tot el
motor Konva i `renderPageToDataURL`.

### P4 · Tancar el timer-gap (B... lock nou)
Opcions no excloents: (a) backend renova `locked_at` dins `TechSheetUpdateView.patch` (afegir `locked_at=now` i
a `update_fields`); (b) frontend afegeix heartbeat (`setInterval` → `POST lock/` periòdic < TTL). Decidir si
l'autosave actua com a heartbeat implícit (opció a, mínima).

### P5 · Export → Finder (B5)
A `onExport` (`TechSheetEditor.jsx:911-918`), després de `pdf.save()`, en comptes de (o a més de) descarregar,
`POST` del `.ftt` (zip) i/o del PDF al Finder via un endpoint nou que cridi `save_model_file(model, file,
tipus='TECHSHEET', categoria='Document', versio_anterior=<cap actual>)`.

### P6 · Grup "Disseny" al sidebar (F11)
A `Sidebar.jsx`, inserir entre `section_config_tecnica` (`:60`) i `section_technical_studio` (`:63`):
```js
{ sectionKey: 'nav.section_disseny', items: [
  { to: '/disseny/documents', labelKey: 'nav.documents', icon: 'ti-file-text' },
  { to: '/disseny/patro-dxf', labelKey: 'nav.patro_dxf', icon: 'ti-vector' },
]},
```
+ claus `nav.section_disseny`/`nav.documents`/`nav.patro_dxf` als 3 i18n + `<Route>` a `App.jsx:132-182`.

---

# ⚖️ PER DECIDIR (Agus)

1. **Forma final de `document.json`**: v2 tal qual amb arrel renombrada? binaris a `assets/` dins el zip o
   inline dataURL? incloure `preview.pdf` i `meta.json` al `.ftt`?
2. **Desempaquetat `.ftt`: backend vs client.** Si és al client, cal afegir lib de ZIP (`fflate` recomanat per
   pes, o `jszip`). Si és al backend, Python `zipfile` ja hi és i el client només rep `document.json` + URLs d'assets.
3. **Camp `metadata` denormalitzat al `ModelFitxer`**: afegir columna/JSON amb metadades del `.ftt` (nº pàgines,
   format, etc.) per al Finder, o llegir-les desempaquetant? (impacta migració vs cost de lectura).
4. **Destí de `TechSheet.versio` i `estat`**: jubilar-los del tot, o reconvertir `versio` en el versionat real
   via `ModelFitxer.versio`/`versio_anterior` i eliminar `estat`?
5. **Coexistència `TechSheet` (O2O) ↔ `ModelFitxer` `.ftt`**: amb només 5 files (1 amb contingut), migrar l'única
   fitxa real i deprecar el model `TechSheet`, o mantenir-lo com a esborrany i materialitzar `.ftt` només a l'export?
6. **Lock al nou món**: el lock viu al `TechSheet`/editor; en passar a `.ftt`/`ModelFitxer`, on viu el lock
   cooperatiu (taula de locks per `ModelFitxer`?), i s'aprofita la mateixa mecànica TTL+CONFIGURE?

---

*Generat en sessió de diagnosi read-only. Cap fitxer de codi/migració/config modificat. Cap push.*
