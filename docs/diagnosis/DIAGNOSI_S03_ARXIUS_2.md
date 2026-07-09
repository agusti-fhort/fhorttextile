# DIAGNOSI — S03 Arxius, lectura quirúrgica 2

> Data: 2026-07-09 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`.
> Abast: 6 preguntes quirúrgiques (Q1–Q6) per desbloquejar P1, P2, P5, P6 i el cicle ① catàleg→model.
> Equip: director-investigacio + investigador-codi×3 + documentador.
> Convenció: `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi (no especulat).**
> Propostes només com `💡 PROPOSTA (a validar)`. Cap escriptura, cap migració, cap consulta de BD
> que escrigui. Zones intocables respectades. Continua `DIAGNOSI_S03_ARXIUS_2026-07-09.md`.

---

## Resum executiu

1. **`path_servidor` és un camp escrit per ningú llegit.** S'escriu sempre
   (`services_fitxers.py:79`) i **NO EXISTEIX cap lector** al backend ni al frontend. `get_url()`
   tampoc té cap consumidor. El trasllat de media (P2) **no ha de tocar `path_servidor`**: tot
   l'accés a bytes va per `.fitxer` (FileField).
2. **Hi ha DOS règims de servei de fitxers, i només un passa per Django.** El `.fitxer` de
   `ModelFitxer` el serveix **nginx directament** (`alias`, cap check de permisos); els assets de
   dins el `.ftt` els serveix **Django** (`FttDocumentAssetView`). P2 ha de decidir sobre el primer.
3. **El `.ftt` és un ZIP auto-contingut.** Les referències d'imatge són `src="assets/<sha16>.<ext>"`,
   **noms interns del propi zip** — mai un id d'un altre `ModelFitxer`, mai una URL persistida.
   **Conseqüència directa per al cicle ① catàleg→model: no cal reescriure cap `src`.** N'hi ha prou
   de copiar les entrades `assets/` al nou `.ftt`.
4. **Excepció que trenca la premissa anterior:** les imatges NOVES afegides a l'editor es desen
   **inline com a dataURL base64 dins `document.json`**, no com a asset (extracció "diferida —
   Fase 1", `TechSheetEditor.jsx:294-296`). Qualsevol import que assumeixi "els binaris viuen a
   `assets/`" és fals per a aquestes.
5. **`addModelFitxer` NO és codi mort:** és la llavor exacta del FilePicker. Es va retirar només de
   la UI al commit `0fff085`, amb el comentari explícit *"es conserven al codi per al futur tab
   Components"*. El seu contracte encaixa amb el motor d'assets actual sense cap adaptació.
6. **El gate de permisos de `tech_sheet` viu al backend a `open-task`, no a la navegació.** El camí
   de menú (P6) està protegit **només si passa per `models.openTask`**; una navegació directa a
   `/models/:id/fitxa?task_id=…` no té gate propi.
7. **NO EXISTEIX cap endpoint "tasques d'un model filtrades per code".** El patró viu és llegir
   `tasques` del dashboard i filtrar per `task_type_code` al client, o cridar `open-task`.
8. **El grup "Marcades" de `FittingDetail` està mort per construcció:** filtra `tipus='MARCADA'`, i
   **cap escriptor del backend emet mai aquest `tipus`**.

**Dues rutes del brief no existeixen tal com s'indiquen** (el brief es basa en un mapa desactualitzat):
- `backend/fhort/tasks/capabilities.py` → **NO EXISTEIX**. El real és `backend/fhort/accounts/capabilities.py`.
- `backend/fhort/commerce/views_b.py` → **NO EXISTEIX**. `upload-logo` de Customer viu a `backend/fhort/tasks/views_b.py:724`.
- `FttDocumentAssetView` és a `ftt_document_views.py:211-227` (el brief deia `227-240`).

---

# Q1 — SERVEI DE FITXERS (per a P2, trasllat de media)

## Q1.1 — Lectors de `path_servidor`

- Definició: `backend/fhort/models_app/models.py:359`.
- Únic **escriptor**: `backend/fhort/models_app/services_fitxers.py:79` →
  `fitxer.path_servidor = fitxer.fitxer.name` (còpia del nom d'emmagatzematge just abans del `save()`).
  Inicialitzat buit a `services_fitxers.py:70`.
- **Lectors: NO EXISTEIX cap.** Cap `.path_servidor` es llegeix al backend ni al frontend. Fora de
  la definició del model, només apareix a migracions (`models_app/migrations/0001_initial.py:87`).

> **Fet per a P2:** `path_servidor` és un camp d'escriptura pura. Un trasllat de media el pot deixar
> desincronitzat sense que res se n'assabenti — o pot ignorar-lo del tot.

## Q1.2 — Com es construeix la URL que arriba al navegador

- `get_url()` — `models_app/models.py:395-400` (prioritat `url_extern` › `fitxer.url` › `None`).
  **Cap consumidor: NO EXISTEIX** ni al backend ni al frontend.
- Únic lector backend de `.fitxer.url`: `models_app/views.py:1116` →
  `'url': request.build_absolute_uri(mf.fitxer.url) if mf.fitxer else None` (endpoint d'upload manual).
- `ModelFitxerSerializer` (`serializers.py:6-10`, `fields='__all__'`) exposa `fitxer` com a DRF
  `FileField`. DRF només fa `build_absolute_uri` si rep `context={'request': …}`. A
  `ftt_document_views.py:79`, `:97` i `:184` es fa `ModelFitxerSerializer(fitxer).data`
  **SENSE context** → el camp `fitxer` surt **RELATIU**: `/media/model_fitxers/AAAA/MM/…`
  (`MEDIA_URL='/media/'`, `settings.py:161`).
- **El frontend hi prefixa la base.** Patró literal a `TechSheetEditor.jsx:2773-2774`:
  ```js
  let url = f.url_extern
  if (!url && f.fitxer) url = f.fitxer.startsWith('http') ? f.fitxer : `${API}${f.fitxer}`
  ```
  amb `const API = import.meta.env.VITE_API_URL || ''` (`TechSheetEditor.jsx:24`).
  Mateix patró a `FittingDetail.jsx:84,398,400` i `ModelSheet.jsx:1355,1425,1494`.
- **Els assets del `.ftt` són l'excepció: sempre URL ABSOLUTA**, construïda al backend a
  `ftt_document_views.py:40-46` `_asset_urls()` →
  `request.build_absolute_uri("/api/v1/ftt-documents/%s/asset/%s/" % (fitxer.id, name))`,
  injectada a la resposta GET sota la clau `assets` (`ftt_document_views.py:100`).

**Els dos règims, en clar:**

| Què | Qui el serveix | URL | Check de permisos |
|---|---|---|---|
| `ModelFitxer.fitxer` (bytes del fitxer) | **nginx**, `alias` directe | relativa `/media/…` + prefix `API` al client | **CAP** (Django no hi intervé) |
| Asset de dins un `.ftt` | **Django** (`FttDocumentAssetView`) | absoluta `/api/v1/ftt-documents/<id>/asset/<nom>/` | `IsAuthenticated` |

## Q1.3 — `FttDocumentAssetView` (`ftt_document_views.py:211-227`)

- Ruta: `GET ftt-documents/<fitxer_id>/asset/<asset_name>/`.
- Autorització: `permission_classes = [IsAuthenticated]` (`:214`). **Cap check de tenant, model ni ownership.**
- Identifica el fitxer: `get_object_or_404(ModelFitxer, pk=fitxer_id, tipus=ModelFitxer.TIPUS_TECHSHEET)` (`:217-219`).
- **No llegeix cap path de disc de l'asset.** Fa `svc.load_document(fitxer)` (`:220`) → obre el
  FileField del `.ftt`, en llegeix el blob i el desempaqueta (`services_ftt_document.py:188-195` →
  `services_ftt.unpack`). L'asset és `data["assets"].get(asset_name)` (`:221`): **bytes extrets del
  zip a memòria**. 404 si no hi és (`:222-225`).
- Content-type: `mimetypes.guess_type(asset_name)[0] or "application/octet-stream"` (`:226`).
- Resposta: `HttpResponse(blob, content_type=ctype)` (`:227`). **Sense streaming, sense capçaleres de
  cache.** Cada asset demanat re-obre i re-descomprimeix el zip sencer.

## Q1.4 — Config nginx de staging per a `/media/`

`/etc/nginx/sites-enabled/ftt-staging` (llegit, no tocat):

```nginx
server_name staging.fhorttextile.tech;          # :2
client_max_body_size 25M;                       # :3
auth_basic "FTT Staging";                       # :6   ← nivell servidor
auth_basic_user_file /etc/nginx/.htpasswd-staging;

location /api/   { auth_basic off; proxy_pass http://127.0.0.1:8001; }   # :26-35
location /admin/ { auth_basic off; proxy_pass http://127.0.0.1:8001; }   # :37-44
location /static/ {              proxy_pass http://127.0.0.1:8001; }     # :46-49
location /media/ { alias /var/www/ftt-staging/backend/media/; }          # :51-53
```

Fets rellevants per a P2:

- **`/media/` el serveix nginx directament amb `alias`** (`:52`). **Django no veu mai la petició** →
  no hi ha cap comprovació d'autenticació, de tenant ni d'accés al model. Qualsevol fitxer de
  `backend/media/` és descarregable per URL directa.
- `/media/` **NO té `auth_basic off`**, per tant **hereta l'`auth_basic` del servidor** (`:6`). A
  staging això el tapa darrere l'htpasswd; **és una protecció d'entorn, no del producte**.
- Límit de pujada: **`client_max_body_size 25M`** (`:3`).
- `grep -rln "location /media/" /etc/nginx/sites-enabled/` → **només `ftt-staging`**. Cap altre site
  del servidor serveix `/media/`.

## Q1.5 — `save_export`: d'on venen els bytes

Ubicació real: `services_ftt_document.py:217-235`.

**Els bytes del PDF venen del client. El servidor no reconstrueix res ni re-renderitza cap imatge.**

- Frontend (`TechSheetEditor.jsx:3009-3033`, `onExport`): el PDF es genera al navegador amb
  `pdf-lib` (`PDFDocument.create()`, `:3012`), rasteritzant cada pàgina a PNG via
  `renderPageToDataURL(p, 3.5, ctx)` (`:3016`) i `pdf.embedPng` (`:3017`). Es puja com a `FormData`
  camp `file` (`:3028-3033`).
- Backend: `FttDocumentExportView.post` (`ftt_document_views.py:171-185`) → `request.FILES.get("file")`
  (`:175`) → `svc.save_export(source, upload, nom=nom)` (`:182`).
- `save_export` (`services_ftt_document.py:225-235`) desa el file object rebut **tal qual** via
  `save_model_file(...)` amb `tipus=EXPORT`, `categoria='Document'`, i enllaça l'origen amb
  `export.generat_des_de = source_ftt`. No toca el `.ftt` origen.

> **Veredicte Q1: llest, amb una decisió pendent.** El trasllat de media només afecta `.fitxer`
> (FileField); `path_servidor` i `get_url()` són inerts. Però el trasllat toparà amb el fet que
> **/media/ avui no passa per Django**: qualsevol esquema de permisos o d'aïllament per tenant
> exigeix canviar el règim de servei, no només el path.

---

# Q2 — ANATOMIA DEL `.FTT` (per al cicle ① catàleg→model)

## Q2.1 — Format intern

Definit a `backend/fhort/models_app/services_ftt.py` (241 línies, llegit sencer).

**És un ZIP estàndard** (`zipfile.ZIP_DEFLATED`) amb extensió `.ftt`
(`ModelFitxer.FTT_EXTENSION='.ftt'`, `models.py:350`). Documentat a `services_ftt.py:1-13`.

Estructura interna (constants `services_ftt.py:30-33`, empaquetat `pack` a `:58-98`):

| Entrada | Contingut | Línia |
|---|---|---|
| `manifest.json` | `{magic:"FTT", schema_version:1, app_version, kind:"document"\|"template", checksums:{path→sha256}}` | `:79-85`, escrit a `:89-91` |
| `document.json` | El document lògic, minificat, `sort_keys=True` | `:69-71`, escrit a `:93` |
| `assets/<nom>` | Binaris referenciats (prefix `ASSETS_PREFIX="assets/"`, `:33`) | `:94-95` |
| `preview.png` | PNG opcional | `:96-97` |

- `FTT_MAGIC="FTT"` (`:22`), `FTT_SCHEMA_VERSION=1` (`:23`), `FTT_DOCUMENT_SCHEMA=1` (`:36`).
- Forma de `document.json`: `{ftt_schema, metadata{}, pageFormat, pages:[{id, objects:[]}]}`
  (`new_empty_document`, `:50-55`).
- `unpack` (`:185-240`) valida `magic=="FTT"` i `schema_version==1`; retorna
  `{manifest, document_json, assets:{nom→bytes}, preview, kind}`.
- Nota clau del propi codi (`services_ftt.py:12`): **el client mai rep el zip**; rep `document.json`
  + un mapa d'URLs d'assets.

## Q2.2 — Serialització de `pages` (frontend)

- Cos del PATCH: `TechSheetEditor.jsx:1953-1955` →
  `body: JSON.stringify({ document_json: v2ToDocument(serializePages(pages), pageFormat, fttMeta.current, fttUrlToName.current) })`
- `serializePages` (`:929-935`): `pages.map(p => ({ id, objects: p.objects.map(serializeObject), guides }))`.
- `v2ToDocument` (`:297-312`): produeix `{ftt_schema:1, metadata, pageFormat, pages:[{id, objects, guides}]}`
  — forma idèntica al `document.json` del backend.
- Backend receptor: `FttDocumentGetView.patch` (`ftt_document_views.py:104-122`) pren
  `request.data.get("document_json")` (`:116`) i crida `svc.save_document(head, document_json)` (`:122`)
  → nova versió encadenada (`services_ftt_document.py:198-214`), **reusant els assets existents per
  fusió** (`:205-208`). El PATCH **no envia assets nous**.

## Q2.3 — PREGUNTA CLAU: ¿incrustats o referenciats?

**Les dues coses coexisteixen, segons l'origen de la imatge.** Aquest és el fet central de Q2.

**(a) Assets ja empaquetats al `.ftt` → REFERENCIATS.** L'objecte porta `src="assets/<nom>"` i els
bytes viuen a l'entrada `assets/<nom>` del zip.
- En desar, la URL carregable es reescriu de tornada a la referència:
  `TechSheetEditor.jsx:305-306` → `urlToName[obj.src] ? { ...obj, src: 'assets/' + urlToName[obj.src] } : obj`
- En carregar, la inversa: `TechSheetEditor.jsx:285-286` (`documentToV2` / `urlOf`),
  `src.startsWith('assets/')` → URL servida pel backend.
- Equivalents backend: `services_ftt.document_to_v2` (`:162-182`) i `v2_to_document` (`:130-159`).

**(b) Imatges NOVES afegides a l'editor → INCRUSTADES inline (base64) dins `document.json`.**
- Comentari explícit: `TechSheetEditor.jsx:294-296` → *"les imatges noves (dataURL) es desen inline
  (extracció a assets diferida — vegeu nota Fase 1)"*.
- Mecànica: `v2ToDocument` només reescriu a `assets/<nom>` **si `urlToName[obj.src]` existeix** (`:305`).
  Una imatge nova té `src = "data:image/png;base64,…"`, que no és al mapa → es desa tal qual.
- L'extracció dataURL→asset (`services_ftt._decode_dataurl` `:117-127`, `v2_to_document` `:143-150`)
  **només s'executa al camí de plantilles (v2), no al PATCH de `save_document`**.

## Q2.4 — Forma EXACTA de la referència

- Camp: `src` de cada objecte imatge → `pages[].objects[].src` (i fills, recursivament via `mapObjectTree`).
- Format: **`"assets/" + <nom>`** (prefix literal `ASSETS_PREFIX="assets/"`, `services_ftt.py:33`).
- Nom generat des de dataURL: `"%s.%s" % (_sha256(data)[:16], ext)` — sha256 dels bytes truncat a
  16 hex + extensió del MIME (`services_ftt.py:148`; taula `_MIME_EXT` a `:107-114`).
- **Exemple literal:** `src = "assets/a1b2c3d4e5f6a7b8.png"` → entrada `assets/a1b2c3d4e5f6a7b8.png` del zip.
- Cas especial del logo de client en instanciar plantilla: nom `field_customer_logo<ext>`,
  `src: 'assets/' + name` (`services_ftt_document.py:123-129`).

> **Veredicte Q2: llest, i la notícia és bona.** La referència és **un nom d'asset intern al mateix
> zip** — no un id de `ModelFitxer`, no una URL, no un FK. **Un `.ftt` és auto-contingut.** Per
> importar un document d'un model a un altre n'hi ha prou de copiar les entrades `assets/<nom>`:
> **cap `src` s'ha de reescriure.** L'única complicació és (b): les imatges inline base64 viatgen
> soles dins `document.json` i **no** són a `assets/`. Un import que iteri `assets/` les perdria de
> vista (encara que viatgin correctament dins el JSON).

---

# Q3 — ASSETS AL CANVAS (per al FilePicker)

## Q3.1 — Com s'afegeix avui una imatge a una pàgina

**Tres vies d'entrada, un sol embut** (`TechSheetEditor.jsx`):

| Via | fitxer:línia |
|---|---|
| Botó ribbon "Imatge" → panell d'import | `:3406` (`openImport('image')`) → inserció a `:3290-3296` |
| Input file ocult | `:3637` (`<input type="file" accept="image/*" hidden>`), i el d'import a `:3834` |
| Drag & drop sobre el llenç | `:3673` (`onDrop`), handler a `:2633-2638` |

Embut comú (`TechSheetEditor.jsx:2627-2632`):
```js
const handleFile = (file) => {
  if (!file || !locked) return
  const fr = new FileReader()
  fr.onload = () => addImageFromDataURL(fr.result)   // fr.result = dataURL base64
  fr.readAsDataURL(file)
}
```

Forma de l'objecte al state (`TechSheetEditor.jsx:2623-2626`):
```js
const obj = { id: uid(), type: 'image', layer: 'free', x: 50, y: 50, width: 120, height: 80, src: dataURL }
```
- Camps: `type:'image'`, `src` (dataURL), `x/y/width/height`, `layer:'free'`, `id`.
  **No hi ha `assetId`.**
- Node Konva: **`Konva.Image` natiu** — `TechSheetEditor.jsx:888-893`
  (`layer.add(new Konva.Image({ ...imageProps(obj), image: el }))`), imatge carregada pel hook
  `useImage(src)` (`:330`).
- El logo del client fa servir el mateix `type:'image'` amb `kind:'logo'` (`:2643`).

**On acaben els bytes: inline base64 dins `document_json`.** No hi ha upload a cap endpoint ni
desat com a asset del `.ftt` en el moment d'inserir (vegeu Q2.3(b)). El mecanisme d'assets
referenciats existeix (`documentToV2`/`v2ToDocument`, `:277-311`) però **el flux d'inserció d'avui
no l'utilitza**.

## Q3.2 — La funció òrfena `addModelFitxer` (`TechSheetEditor.jsx:2771-2786`)

```js
const addModelFitxer = async (f) => {
  if (!locked) return
  let url = f.url_extern
  if (!url && f.fitxer) url = f.fitxer.startsWith('http') ? f.fitxer : `${API}${f.fitxer}`
  if (!url) return
  try {
    const blob = await fetch(url).then(r => { if (!r.ok) throw new Error('fetch'); return r.blob() })
    const dataURL = await new Promise((res, rej) => { const fr = new FileReader(); fr.onload = () => res(fr.result); fr.onerror = () => rej(new Error('fr')); fr.readAsDataURL(blob) })
    addImageFromDataURL(dataURL)
  } catch { /* silenci */ }
}
```

**Contracte:**
- **Param:** un objecte `f` amb `{ id, nom_fitxer, fitxer, url_extern }` — exactament la forma que
  retorna l'API `model-fitxers` (`ModelFitxerSerializer`, `fields='__all__'`).
- **Endpoint:** cap de propi. Fa `fetch(url)` sobre la URL del fitxer del model i el converteix a
  blob → dataURL.
- **Node que crea:** delega a `addImageFromDataURL` → mateix `type:'image'` base64 inline de Q3.1.

**Per què es va retirar de la UI.** Comentari al codi (`TechSheetEditor.jsx:3408-3410`):
```
// NOTA (R1): els botons de "Fitxers del model" s'han retirat del ribbon; addModelFitxer i la
// càrrega de `fitxers` es conserven al codi per al futur tab Components.
```
Commit **`0fff085`** — *"feat(editor): ribbon Inserir — treure fitxers model, renombrar, +Importar
Mesures (R1)"* (2026-06-29). El diff elimina només el bloc que l'invocava:
```js
-  ...fitxers.slice(0, 4).map(f => ribbonTool({
-    key: `fitxer-${f.id}`, icon: 'ti-file-plus', label: f.nom_fitxer || t('tech_sheet.model_file'),
-    onClick: () => addModelFitxer(f), disabled: !(f.url_extern || f.fitxer), title: f.nom_fitxer,
-  })),
```
`grep -rn "addModelFitxer" frontend/src/` → només la definició (`:2771`) i el comentari (`:3408`).

> **Veredicte Q3: és llavor del FilePicker, no codi mort.** El contracte encaixa amb el motor
> d'assets actual sense adaptació: pren un `ModelFitxer` (la forma que ja serveix l'API i que ja
> consumeix `FittingDetail`), en descarrega els bytes i els injecta pel **mateix camí que qualsevol
> imatge d'avui**. L'únic que li falta és un punt d'entrada a la UI. Hereta, això sí, la limitació
> de Q3.1: el resultat és base64 inline, no un asset referenciat.

---

# Q4 — RESOLUCIÓ DE TASCA (per a P6, fitxa des del menú)

## Q4.1 — Com WorkPlan i TaskTree obtenen la ModelTask de `tech_sheet`

**Cap dels dos la demana pel seu compte.** Tots dos consumeixen l'array `tasques` del **compositor
del dashboard**:

- `WorkPlan` rep `tasques` com a **prop** del pare: fetch `GET /api/v1/models/<id>/dashboard/` a
  `DashboardTab.jsx:66`, extracció a `:113`, injecció a `DashboardTab.jsx:130`.
- `TaskTree` rep `tasks` des de `TasksTab.jsx`: fetch a `TasksTab.jsx:15`, `d.tasques` a `:17`,
  injecció a `:27`. A més crida el **catàleg de tipus**: `taskTypes.list({active:true, page_size:200})`
  a `TaskTree.jsx:73` (`GET /api/v1/task-types/`, `endpoints.js:196`), i creua `TaskType.code` amb la
  ModelTask existent a `TaskTree.jsx:132-134`.

La ModelTask de `tech_sheet` és, doncs, **l'element de `tasques` amb `task_type_code === 'tech_sheet'`**,
filtrat al client.

**Forma de cada task** (compositor, `backend/fhort/models_app/views.py:2113-2128`; array sota la clau
`'tasques'` a `:2159`): `id`, `task_type`, `task_type_code`, `task_type_name`, `default_order`,
`status`, `assignee_id`, `assignee_nom`, `temps_consumit_min`, `obertures`, `order`, `origen`, `off_recipe`.

## Q4.2 — La transició abans de navegar

La ruta de l'eina és `/models/${modelId}/fitxa?task_id=${task.id}` (`WorkPlan.jsx:30`, `TaskTree.jsx:42`).

- **WorkPlan** (`playMine`, `:235-262`): `models.openTask(modelId, task.task_type_code)` (`:240`) →
  `POST /api/v1/models/<id>/open-task/` amb body `{ code }` (`endpoints.js:48`). En èxit construeix
  `openedTask` amb `res.data.task_id`/`res.data.status` (`:242-246`) i **després** navega (`:249`).
  En error (`catch`, `:254-261`): `403` → toast `not_allowed`; altrament `transition_error`; sempre
  `onRefresh()`. **No navega.**
- **Play sobre tasca d'altri:** `handlePlay` obre diàleg de handoff (`:265-268`); `confirmHandoff`
  (`:273-290`) crida `modelTasks.claim(task.id)` → `POST /api/v1/model-task-items/<id>/claim/`
  (`endpoints.js:189`) i, si va bé, `playMine(...)`. `403` → toast `claim_denied`, sense navegar (`:284-287`).
- **TaskTree** (`start`, `:107-125`): `models.openTask(modelId, tt.code)` (`:109`); navega només si
  hi ha ruta (`:113-118`). `catch`: `403` → `tree_no_permission`, altrament `tree_start_error` (`:120-123`).

**Punt clau:** la creació/transició la fa el **backend** a `open-task` (idempotent: crea-si-falta +
InProgress + auto-assign). El frontend navega **només després d'un `open-task` OK**.

## Q4.3 — Allow-list: qui pot fer una `tech_sheet`

⚠️ El fitxer és `backend/fhort/accounts/capabilities.py` (**no** `tasks/capabilities.py`).

La decisió **no és per rol** sinó per una **allow-list de `TaskType.code` per usuari** —
`accounts/capabilities.py:57-71` `get_allowed_task_types(user)`:
- Admin (rol `admin` o capability `MANAGE_USERS`) → **bypass total**: tots els codes actius (`:64-68`).
- Altrament → `set(profile.permisos["tasks"])`; **sense la clau `"tasks"` → set buit (default DENY)** (`:71`).

A sobre hi ha la porta de **capacitat**: `transition`, `claim` i `open-task` exigeixen `EXECUTE_TASKS`
via `_ExecuteTasks(HasCapability)` (`tasks/views_b.py:420-421`; decoradors a `:424-425`, `:455-456`,
`:508-509`). `EXECUTE_TASKS` el tenen tots els rols base (`capabilities.py:21-25`).

**Calen les DUES coses:** `EXECUTE_TASKS` **i** `'tech_sheet' ∈ get_allowed_task_types(user)`.

**Què retorna exactament el backend si no té `tech_sheet` permès:**

| Endpoint | fitxer:línia | HTTP | Cos |
|---|---|---|---|
| `open-task` | `views_b.py:537-539` | **403** | `{'error': "No pots obrir una tasca del tipus 'tech_sheet' (no és a la teva allow-list)."}` |
| `transition` → InProgress | `views_b.py:443-447` | **403** | `{'error': "No tens permès executar el tipus de tasca 'tech_sheet'."}` |
| `claim` | `views_b.py:488-492` | **403** | `{'error': "No pots agafar una tasca del tipus 'tech_sheet' (no és a la teva allow-list d'execució)."}` |
| Sense `EXECUTE_TASKS` | `capabilities.py:46-54` | **403** | genèric de DRF (sense clau `error`) |
| Sense perfil al tenant | `views_b.py:534-535` | **403** | `{'error': 'Usuari sense perfil en aquest tenant.'}` |

**Comportament esperable del camí de menú (P6).** Qui bloqueja és el **backend**, no la navegació.
Avui el flux sempre passa per `models.openTask` abans del `navigate` (`WorkPlan.jsx:240`→`:249`;
`TaskTree.jsx:109`→`:117`), i el `catch` impedeix el `navigate`.

> ⚠️ **Aquesta protecció depèn de passar per `open-task`.** Si un menú navega **directament** a
> `/models/:id/fitxa?task_id=…`, no hi ha cap gate client-side, i **la pàgina de la fitxa no té gate
> propi** (cap check d'allow-list a `App.jsx:81` `FttResolver` ni a `TechSheetEditor`). El backend
> seguiria protegint la transició de temps (`transition`, `TechSheetEditor.jsx:1862`), però l'editor
> **s'obriria i deixaria desar** (el lock del `.ftt` no consulta l'allow-list). P6 ha de decidir si
> el menú crida `open-task` o si la ruta guanya un gate propi.

## Q4.4 — ¿Existeix un endpoint "tasques d'un model filtrades per code"?

**NO EXISTEIX cap endpoint que filtri per `task_type` *code*.** El que hi ha:

- **`GET /api/v1/model-task-items/`** (`ModelTaskViewSet`, `views_b.py:42`). Filtres reals
  (`endpoints.js:174-176`): `?model & status & task_type & assignee`. **`task_type` és per `id` (FK),
  no per `code`.** Resposta: llista paginada de ModelTask (`ModelTaskSerializer`).
- **`GET /api/v1/model-task-items/by-model/`** (`by_model`, `views_b.py:79-240`). **No és "tasques
  d'un model"**: és un **agregador per model** (columna 1 del Kanban), amb comptadors per estat.
  Query params (`views_b.py:87-97`): `?all`, `?search`, `?ordering` (whitelist), i filtres exactes
  `temporada, estat, fase_actual, garment_type, any, prioritat, responsable(=id|me), customer,
  collection, data_objectiu_after/before`. **Cap filtre per `task_type` ni per `code`.**
  Forma de resposta (paginada, `views_b.py:215-235`):
  ```json
  { "model_id": …, "model_codi": …, "model_nom": …, "fase": …,
    "counts": {"pending":…, "paused":…, "in_progress":…, "done":…},
    "kanban_state": …, "prioritat": …, "temporada": …, "estat": …,
    "data_objectiu": …, "responsable_id": … }
  ```
- La via viva per anar d'un `code` a la ModelTask concreta és **`POST /api/v1/models/<id>/open-task/`
  amb `{code}`** (idempotent, crea-si-falta) — `views_b.py:508-569`, ruta a `tasks/urls.py:59`.

> **Veredicte Q4: llest, amb un forat identificat.** El camí de menú de P6 necessita, o bé cridar
> `open-task` (i heretar el gate del backend), o bé un gate propi a la ruta de la fitxa.

---

# Q5 — ITEMAUTHORING (per a P5)

## Q5.1 — Estructura de la pàgina i punt d'inserció

Wizard de **2 passos** (`STEPS = ['step1_context','step2_construction']`, `ItemAuthoring.jsx:19`).
Render (`return` a `:182`):

| Secció | fitxer:línia |
|---|---|
| Capçalera (títol + tancar) | `:184-192` |
| Stepper (2 pastilles) | `:194-219` |
| Bloc d'error | `:221-226` |
| **PAS 1 · CONTEXT** | `:228-290` |
| ├ Identitat (nom + codi auto-slug + actiu) | `:231-254` |
| ├ `<AxesSelector>` | `:256` |
| ├ pick ruleset + `<RuleSetPicker>` | `:258-270` |
| └ **SLOT D'IMPORT INERT** (Fase C) | `:272-288` |
| **PAS 2 · CONSTRUCCIÓ** | `:292-330` |
| ├ Confirmació de talla base (targetes `sizeDefs`) | `:295-325` |
| └ Títol "measurements" + `<MeasurementBaseGrid garmentTypeItemId={itemId} />` | `:327-328` |
| Footer de navegació (Enrere / Següent / Finalitza) | `:332-346` |

**No hi ha botó "desar"**: el desat és incremental (`garmentTypeItems.update` a cada acció —
`assignRuleset` `:136`, `pickBaseSize` `:152`, `goNext` `:167`). "Finalitza" només fa
`navigate('/garment-types')` (`:176`, `:342-344`).

**Punt d'inserció natural per a una secció "Fitxers":** **després de `<MeasurementBaseGrid>` (`:328`)
i abans del tancament del bloc del PAS 2 (`:330`)**, com a secció germana amb el mateix patró
(`<p style={sectionTitle}>…</p>` + component). Raons factuals:
- No toca el slot inert (`:272-288`), que a més viu al **PAS 1**.
- Garanteix `itemId != null` (al PAS 2 l'item ja s'ha creat al PAS 1) — necessari per adjuntar.
- Reutilitza l'estil `sectionTitle` ja definit (`:39-42`).

Alternativa si "Fitxers" ha de ser visible abans de construir: entre `:325` i `:327`. Menys coherent
amb "artefactes d'un item ja creat".

## Q5.2 — Precedent d'upload gated CONFIGURE: `upload-logo` de Customer

⚠️ Ruta real: **`backend/fhort/tasks/views_b.py:724-737`** (el model `Customer` viu a l'app `tasks`,
no a `commerce`; `commerce/views_b.py` **NO EXISTEIX**).

**Backend:**
- Definició: `@action(detail=True, methods=['post'], url_path='upload-logo', parser_classes=[MultiPartParser, FormParser])`
  (`views_b.py:724-725`) → `POST /api/v1/customers/<pk>/upload-logo/`.
- Recepció: `logo_file = request.FILES.get('logo')` (`:730`) — **FormData, camp `logo`**. Si buit →
  `400 {'detail': 'logo requerit.'}` (`:731-732`).
- Desat: esborra l'anterior `customer.logo.delete(save=False)` (`:733-734`), assigna
  `customer.logo = logo_file` i `customer.save(update_fields=['logo'])` (`:735-736`).
- **Validacions: NOMÉS presència del fitxer** (`:731`). **No hi ha validació de mida ni de mimetype**
  (només la implícita de l'`ImageField` de Django en desar).
- **Gating:** via `get_permissions` del `CustomerViewSet` (`views_b.py:709-713`): `list`/`retrieve` →
  `IsAuthenticated`; **qualsevol altra acció** (inclòs `upload-logo`) → `HasCapability` amb
  `self.required_capability = CONFIGURE` (`:712`). No hi ha decorador separat: el gate és
  `get_permissions` + `HasCapability.has_permission` (`accounts/capabilities.py:46-54`).
- El camp `logo` és `read_only` al serializer i **només s'escriu per aquesta acció**
  (`tasks/serializers_b.py:64-66,75`).

**Frontend:** `frontend/src/pages/Customers.jsx:44-61` (`handleLogoUpload`) —
`const fd = new FormData(); fd.append('logo', file)` (`:50`) i **`fetch` cru** (no via `endpoints.js`)
a `` `${API}/api/v1/customers/${customerId}/upload-logo/` `` amb `Authorization: Bearer …` (`:51-55`).
En error mostra `clients.error` (`:56-60`).

> Nota de precisió: `endpoints.js:16-17` té un `uploadLogo` **diferent** (logo del tenant/config,
> camp FormData `logo_file`). No confondre'ls.

> **Veredicte Q5: llest.** Punt d'inserció net i precedent d'upload gated identificat — amb la
> reserva que el precedent **no valida ni mida ni mimetype**.

---

# Q6 — FITTINGDETAIL (per a P1)

## Q6.1 — Els 3 grups

Càrrega (`FittingDetail.jsx:57-71`): tres crides paral·leles a `modelFitxers.list(...)` →
`GET /api/v1/model-fitxers/` (`endpoints.js:100-102`, read-only). Estat únic `groups` (`:54`),
poblat a `:65-69`.

| Grup | Filtre (`:59-61`) | State | Render | Clau i18n → valor `ca.json` |
|---|---|---|---|---|
| Patrons | `categoria:'Patro'` | `groups.patterns` | `:108` | `fitting.info.patterns` → **"Patrons"** (`ca.json:1764`) |
| Marcades | `tipus:'MARCADA'` | `groups.markers` | `:109` | `fitting.info.markers` → **"Marcades"** (`ca.json:1765`) |
| Documents | `categoria:'Document'` | `groups.documents` | `:110` | `fitting.info.documents` → **"Documents"** (`ca.json:1766`) |

Bloc i18n complet a `frontend/src/i18n/ca.json:1762-1769` (`title:"Info del model"`,
`no_files:"Sense fitxers"`, `download:"Descarregar"`).

**Què es fa amb cada fitxer** — idèntic als tres grups, via `renderGroup(label, files)` (`:75-99`):
- Icona + `f.nom_fitxer` (`:88`).
- **Link de descàrrega i prou:** `:84` `const url = f.fitxer || f.url_extern || null`; si n'hi ha,
  `:90-93` `<a href={url} target="_blank" rel="noopener noreferrer">↓ Descarregar</a>`.
- **Cap preview, cap comptador, cap càlcul.** Grup buit → "Sense fitxers" (`:79-80`).

**Ús posterior: cap.** `groups` no es passa a cap fill ni es compta; només es consumeix dins el
render d'aquest component (`Card`, `:102-113`). Panell merament informatiu (comentari
`fitting info panel 5B.6-B1` a `endpoints.js:99`).

> ⚠️ Nota per a P2: `:84` usa `f.fitxer` **relatiu** com a `href` directe, sense prefixar `API`.
> Funciona avui perquè el frontend i `/media/` comparteixen origen a staging (nginx).

## Q6.2 — Fets per decidir el re-apuntat `categoria` → `tipus`

**Model** (`models_app/models.py:328-355`):
- `categoria` — CharField **amb choices** (`:329-334`): `'Patro'`, `'Disseny'`, `'Fitting'`, `'Document'`.
- `tipus` — CharField **lliure, sense choices**, `default='ALTRES'` (`:355`). Comentari `:344-347`:
  *"són convencions de codi, no constraints de BD"*.

**Valors de `tipus` realment emesos pel backend:**
- `'TECHSHEET'` / `'EXPORT'` (`models.py:348-349`; assignats a `services_ftt_document.py:182,229`).
- `'DOCUMENT'` (`extraction_views.py:1509`, junt amb `categoria='Document'`).
- `'ALTRES'` (default, `services_fitxers.py:67`).
- Conjunt de patró/sketch **llegit però mai escrit pel backend**: `views.py:1144` →
  `tipus__in=['PATRO','ESCALAT','SKETCH_FLETXES','SKETCH_NET']`.

**FET CRÍTIC:** el valor `'MARCADA'` **no s'assigna com a `tipus` enlloc del backend**.
`grep -rn "MARCADA" backend/fhort --include=*.py` (excloent migracions) només troba
`('ia_marcada','IA de marcada')`, que és un valor del camp **`origen`** (`models.py:340`), **no de
`tipus`**. Per tant el grup "Marcades" (`FittingDetail.jsx:60`) **retorna sempre buit** amb les dades
que el backend genera avui.

**Fets que informen el re-apuntat (sense decidir):**
- **Patrons:** `categoria:'Patro'` és un choice vàlid. L'equivalent per `tipus` seria `'PATRO'`
  (o `tipus__in=['PATRO','ESCALAT']`, per `views.py:1144`). ⚠️ `PATRO` (tipus) i `Patro` (categoria)
  difereixen en majúscules i accent.
- **Marcades:** **cap `tipus` de marcada s'emet mai**. El candidat semànticament més proper és
  `origen='ia_marcada'`, o un `tipus` nou encara no produït. Amb els valors actuals, cap opció el
  pobla.
- **Documents:** `categoria:'Document'` i `tipus:'DOCUMENT'` **coexisteixen al mateix registre**
  (`extraction_views.py:1509`) → aquest grup funcionaria per qualsevol dels dos eixos.

> **Veredicte Q6: cal decisió del CTO.** Re-apuntar a `tipus` arregla "Patrons" (amb el canvi de
> caixa) i és neutre per a "Documents", però **no salva "Marcades"**: aquell grup no té emissor. La
> decisió real no és quin eix filtrar, sinó **qui escriurà `tipus='MARCADA'`** (o si el grup ha de
> filtrar per `origen`).

---

# TAULA FINAL — per al CTO

| # | Fet | Estat | Referència | Impacte |
|---|---|---|---|---|
| 1 | Lectors de `path_servidor` | **NO EXISTEIXEN** (només escriptor) | `services_fitxers.py:79` | 🟢 P2 pot ignorar-lo |
| 2 | Consumidors de `get_url()` | **NO EXISTEIXEN** | `models.py:395-400` | 🟢 Codi mort |
| 3 | `/media/` servit per nginx amb `alias` | **EXISTEIX** | `sites-enabled/ftt-staging:51-53` | 🔴 **Django no hi intervé: cap check de permís ni de tenant** |
| 4 | `auth_basic` cobreix `/media/` | **EXISTEIX** (heretat del server) | `ftt-staging:6` (i `:27` l'apaga per `/api/`) | 🟠 Protecció d'entorn, no de producte |
| 5 | Límit de pujada nginx | **25 MB** | `ftt-staging:3` | 🟠 Sostre per a P5 |
| 6 | `fitxer` serialitzat RELATIU (sense `request` al context) | **EXISTEIX** | `ftt_document_views.py:79,97,184` | 🟠 El client hi prefixa `API` |
| 7 | `.ftt` = ZIP amb `manifest.json` + `document.json` + `assets/` | **EXISTEIX** | `services_ftt.py:30-33,58-98` | — |
| 8 | Referència d'asset = `"assets/<sha16>.<ext>"`, **nom intern del zip** | **EXISTEIX** | `services_ftt.py:33,148` | 🟢 **Import ①: cap `src` a reescriure** |
| 9 | Imatges noves desades **inline base64** dins `document.json` | **EXISTEIX** | `TechSheetEditor.jsx:294-296,305` | 🟠 Trenca "tot binari viu a `assets/`" |
| 10 | `FttDocumentAssetView` re-descomprimeix el zip sencer per asset | **EXISTEIX** | `ftt_document_views.py:220-227` | 🟠 Sense cache ni streaming |
| 11 | `FttDocumentAssetView` només `IsAuthenticated` | **EXISTEIX** | `ftt_document_views.py:214` | 🟠 Sense check de tenant/model |
| 12 | `save_export`: bytes del PDF venen **del client** (pdf-lib) | **EXISTEIX** | `TechSheetEditor.jsx:3012-3033` → `services_ftt_document.py:225-235` | 🟢 El servidor no re-renderitza |
| 13 | Inserció d'imatge → `Konva.Image` + `src` dataURL, sense `assetId` | **EXISTEIX** | `TechSheetEditor.jsx:2623-2626,888-893` | — |
| 14 | `addModelFitxer` = **llavor del FilePicker**, no codi mort | **EXISTEIX òrfena** | `TechSheetEditor.jsx:2771-2786`; retirada a `0fff085` | 🟢 Reutilitzable tal com és |
| 15 | ModelTask de `tech_sheet` s'obté filtrant `tasques` del dashboard al client | **EXISTEIX** | `views.py:2113-2128,2159`; `TaskTree.jsx:132-134` | — |
| 16 | Endpoint "tasques d'un model per `code`" | **NO EXISTEIX** | `views_b.py:79-240` (`by-model` és agregador) | 🟠 P6 ha d'usar `open-task` |
| 17 | Gate de `tech_sheet` = allow-list per usuari + `EXECUTE_TASKS` | **EXISTEIX** | `accounts/capabilities.py:57-71`; `views_b.py:420-421` | — |
| 18 | Sense permís, `open-task` → **403** amb `{'error': …}` | **EXISTEIX** | `views_b.py:537-539` | 🟢 Backend bloqueja |
| 19 | Navegació directa a `/models/:id/fitxa` **sense gate propi** | **EXISTEIX el forat** | `App.jsx:81`; cap check a `TechSheetEditor` | 🔴 **P6: el menú ha de cridar `open-task`** |
| 20 | Punt d'inserció "Fitxers" a `ItemAuthoring` | `:328` → `:330` (PAS 2) | `ItemAuthoring.jsx:292-330` | 🟢 No toca el slot inert |
| 21 | `upload-logo` gated per `CONFIGURE` via `get_permissions` | **EXISTEIX** | `tasks/views_b.py:709-713,724-737` | 🟢 Precedent |
| 22 | `upload-logo` valida mida/mimetype | **NO EXISTEIX** | `tasks/views_b.py:730-736` | 🟠 No copiar el forat |
| 23 | `tipus='MARCADA'` emès per algun escriptor | **NO EXISTEIX** | grep a `backend/fhort/**/*.py` | 🔴 Grup "Marcades" sempre buit |
| 24 | `FittingDetail` usa `f.fitxer` relatiu com a `href` directe | **EXISTEIX** | `FittingDetail.jsx:84` | 🟠 Depèn del mateix origen |

---

## 💡 PROPOSTES (a validar — NO són decisions)

> Patró C: dissenya el CTO. S'anoten per no perdre-les.

1. **P2 — el trasllat de media és una decisió de règim, no de path.** Mentre `/media/` el serveixi
   nginx per `alias` (taula #3), cap esquema de permisos ni d'aïllament per tenant s'aplica als bytes.
   Les opcions són servir-los per Django (com ja fa `FttDocumentAssetView`) o per `X-Accel-Redirect`.
2. **Cicle ① — l'import de `.ftt` entre models és barat** (taula #8): copiar entrades `assets/`, no
   tocar cap `src`. L'únic cas a cobrir són les imatges inline base64 (#9).
3. **Considerar tancar el deute de #9** (extracció dataURL→`assets/` en desar) abans de construir
   l'import: sanejaria alhora el `document.json` i el cicle ①.
4. **P6 — el menú ha de cridar `models.openTask(modelId, 'tech_sheet')`** i navegar només en èxit,
   exactament com fan `WorkPlan.jsx:240-249` i `TaskTree.jsx:109-118`. Altrament cal un gate propi a
   la ruta `/models/:id/fitxa` (taula #19).
5. **P1 — decidir l'emissor de "Marcades"** abans de re-apuntar l'eix: re-apuntar a `tipus` no salva
   el grup si ningú escriu mai `tipus='MARCADA'` (taula #23).
6. **P5 — el precedent `upload-logo` no valida mida ni mimetype** (taula #22). Si es copia el patró
   de gating (`get_permissions` + `CONFIGURE`), val la pena no copiar-ne el forat, tenint present el
   sostre de `client_max_body_size 25M` (taula #5).
7. **FilePicker — `addModelFitxer` s'aprofita tal com és** (taula #14); només li cal el punt d'entrada
   a la UI que el comentari `TechSheetEditor.jsx:3408` ja anticipa ("futur tab Components").

---

## TROBALLES TRANSVERSALS (anotades, NO investigades — fora d'scope)

- **`FttDocumentAssetView` i la resta de vistes `ftt-documents/` només comproven `IsAuthenticated`**
  (`ftt_document_views.py:214-219`): qualsevol usuari autenticat pot llegir assets de qualsevol
  `fitxer_id` de tipus TECHSHEET, sense comprovació de tenant ni de model.
- **`path_servidor` és candidat a poda** (escriptura pura, zero lectors).
- **`upload-logo` de Customer sense validació de bytes/content-type** (`tasks/views_b.py:730-736`).
- **Discrepància de rutes al brief** (`capabilities.py` a `accounts/`, no `tasks/`; `upload-logo` a
  `tasks/`, no `commerce/`; `FttDocumentAssetView` a `:211-227`, no `:227-240`): el mapa de partida
  del brief està desactualitzat en aquests tres punts.
- **`DIAGNOSI_FITXERS.md` (2026-06-27)** continua sense segellar tot i estar superada (ja assenyalat a
  `DIAGNOSI_S03_ARXIUS_2026-07-09.md`).

Cap línia de codi tocada en aquesta sessió.
