# DIAGNOSI — Sistema de fitxers del Model

> Sessió de diagnosi (Patró A) — READ-ONLY absolut. Cap codi tocat, cap migració, cap push, cap PROD.
> Staging `/var/www/ftt-staging` (branca `dev`). Backend amb apps sota `fhort/`; frontends a `frontend/` i `frontend-backoffice/`.
> Regla: FETS amb referència `fitxer:línia`. Idees només com **💡 PROPOSTA (a validar)**. Decisions = de l'Agus (⚖️).
> Data: 2026-06-27.

**Objectiu:** mapejar la realitat de fitxers del Model i resoldre el fork de contenidors abans de redissenyar la pujada cap a un gestor tipus Finder/elFinder. **No es construeix res aquesta sessió.**

---

## TL;DR (per a l'Agus)

1. **El fork està resolt com a FET:** `models_app.ModelFitxer` és el contenidor **de facto canònic** (2 escriptors vius, múltiples lectors, endpoint, serializer, consum als frontends, 8 fitxers reals a disc). `files.FitxerVersio` és **esquelet mort**: 0 escriptors, 0 lectors, cap endpoint/serializer/admin, i la carpeta `/storage/...` que prometia **no existeix**.
2. **La previsualització JA EXISTEIX** per imatge (`<img>`) i PDF (`<iframe>`) — la premissa "si és barat afegir-la" està parcialment desfasada: el barat ja hi és.
3. **Hi ha dos eixos de classificació convivint i inconsistents:** `categoria` (4 valors, backend) i `tipus` (7 rols, el que de fet segmenta la UI). El frontend del tab no envia mai `categoria`.
4. **Dos algoritmes de versionat divergents:** l'import W5 **encadena** `versio_anterior` i usa naming `{codi}_DOCUMENT_{NNN}`; l'upload manual **NO encadena** i versiona per `tipus` amb format de versió diferent.
5. Forats respecte un Finder: **cap ordenació, cap filtre, cap navegació de la cadena de versions**, i **N peticions GET (una per tipus)** en lloc d'una.

---

# 1) EL FORK DE CONTENIDORS

## 1a) FETS — `ModelFitxer` (`fhort/models_app/models.py:328-382`)

**Camps reals:**

| Camp | Tipus | Línia |
|---|---|---|
| `model` | FK→`Model`, CASCADE, `related_name='fitxers'` | models.py:336 |
| `nom_fitxer` | CharField(255) | models.py:337 |
| `categoria` | CharField(20, choices=CATEGORIA_CHOICES) | models.py:338 |
| `tipus` | CharField(30, default='ALTRES', blank) | models.py:339 |
| `versio` | **CharField(10)** (string!) | models.py:340 |
| `path_servidor` | CharField(500) | models.py:341 |
| `versio_anterior` | FK→`self`, SET_NULL, `related_name='versions_posteriors'` | models.py:342-348 |
| `accessible_portal` | BooleanField(default=False) | models.py:349 |
| `pujat_per` | FK→`accounts.UserProfile`, SET_NULL | models.py:350-355 |
| `data_pujada` | DateTimeField(auto_now_add) | models.py:356 |
| `mida_bytes` | BigIntegerField | models.py:357 |
| `fitxer` | **FileField(upload_to='model_fitxers/%Y/%m/', null, blank)** | models.py:360 |
| `url_extern` | URLField(null, blank) | models.py:361-364 |
| `descripcio` | TextField(null, blank) | models.py:365 |
| `enviat_ia` | BooleanField(default=False) | models.py:374 |
| `resultat_ia_path` | CharField(500, null, blank) | models.py:375 |
| `get_url()` | retorna `url_extern` o `fitxer.url` | models.py:367-372 |

**CATEGORIA_CHOICES (verbatim)** — models.py:329-334:
```python
('Patro', 'Patró'),
('Disseny', 'Disseny'),
('Fitting', 'Fitting'),
('Document', 'Document'),
```

**Naming `{codi}_CATEGORIA_{NNN}`:** construït **només** a un lloc — `extraction_views.py:1404`:
```python
nom = f"{model.codi_intern}_DOCUMENT_{num:03d}{ext}"
```
És l'únic punt que aplica el patró canònic (doc a `extraction_views.py:1146`). En disc només existeixen fitxers `_DOCUMENT_`. L'altre escriptor (`upload_file_view`) **NO** aplica el patró: desa el nom original (`path_servidor=uploaded_file.name`, `views.py:1086`).

**`versio` / `versio_anterior` EN PRÀCTICA** — dos escriptors, tots dos **encadenen** (cap sobreescriu), però de forma divergent:

1. **`upload_file_view`** (`views.py:1046-1097`; ruta `POST models/<id>/upload-fitxer/` a `urls.py:179`):
   - Últim del mateix `tipus`: `...filter(model, tipus).order_by('-id').first()` (`views.py:1063`).
   - `version = str(prev_num + 1)` → versió string `"1"`,`"2"`… (`views.py:1068`).
   - `ModelFitxer.objects.create(...)` (`views.py:1078`). **NO omple `versio_anterior`** (queda NULL) → cadena trencada.
2. **Import W5 confirmar** (`extraction_views.py:1391-1416`):
   - Anterior per `categoria='Document'` (`:1394-1396`).
   - `num = int(anterior.versio)+1`, format `f'{num:03d}'` → `"001"`,`"002"` (`:1400`).
   - **Crea amb `versio_anterior=anterior`** (CHAIN correcta) (`:1410-1412`).
   - Escriptura física: `doc_fitxer.fitxer.save(nom, ContentFile(doc_bytes), save=True)` (`:1416`).

⚠️ **Inconsistència de fet:** format de `versio` divergent (`"2"` vs `"002"`) i `upload_file_view` **no encadena** `versio_anterior`.

**Endpoint + ViewSet + ruta:**
- `ModelFitxerViewSet(viewsets.ModelViewSet)` — `views.py:132-139`. CRUD complet, `IsAuthenticated`, `filterset_fields=['model','categoria','tipus','enviat_ia']`.
- `ModelFitxerSerializer` (`fields='__all__'`) — `serializers.py:6-10`.
- Registre: `router.register('model-fitxers', ModelFitxerViewSet, basename='model-fitxer')` — **`fhort/models_app/urls.py:41`** → `/api/v1/model-fitxers/`.
- Rutes funció addicionals: `upload-fitxer/` (`urls.py:179`), `analisi-ia/` (`urls.py:180`).

## 1b) FETS — `files.FitxerVersio` (`fhort/files/models.py:5-65`)

**Camps** (disseny "net", numèric): `model` FK→`models_app.Model` (`:20-26`), `nom_original` (`:27`), `nom_intern` (`:28`), `categoria` (`:29`), **`versio` PositiveIntegerField** (`:30`), `versio_anterior` FK→self (`:31-37`), `path_relatiu` (`:39`), `mida_bytes` (`:40`), `mimetype` (`:41`), **`checksum` CharField(64)** (`:42`), **`origen`** (ORIGEN_CHOICES, default `'upload'`) (`:44`), `prompt_ia` (`:45`), `model_ia` (`:46`), `pujat_per` (`:48-54`), `data_creacio` (`:55`), `accessible_portal` (`:56`), `notes` (`:57`).
- CATEGORIA_CHOICES (minúscules, **inclou `ia_output`**): `patro/disseny/fitting/document/ia_output` (`:6-12`).
- ORIGEN_CHOICES: `upload/ia_escalat/ia_marcada/ia_ocr` (`:13-18`).

**QUI ESCRIU / QUI LLEGEIX → NINGÚ.** Evidència exhaustiva:
- grep `FitxerVersio` a tot el backend `.py` → **4 ocurrències, cap consumidora**: definició (`files/models.py`), migració (`files/migrations/0001_initial.py`), i un **comentari** a `fitting/models.py:363` (`"FileField pattern like ModelFitxer, not FitxerVersio"`). → **0 writers, 0 readers** vius.
- App `files` a INSTALLED_APPS (`'fhort.files'`, `settings.py:71`) PERÒ: `files/views.py` = stub buit; `files/admin.py` = stub buit; `files/serializers.py` = **no existeix**; `files/urls.py` = **no existeix** → cap router, cap endpoint.
- grep als DOS frontends per `FitxerVersio`/`fitxer_versions`/`files` → **0 resultats**.

**Veredicte 1b:** `FitxerVersio` és **esquelet abandonat**. La taula DB existeix (migració 0001) però res hi accedeix.

## 1c) FETS — Emmagatzematge físic

- **MEDIA_ROOT real:** `BASE_DIR / 'media'` (`settings.py:161`); `MEDIA_URL='/media/'` (`settings.py:160`) → `/var/www/ftt-staging/backend/media/`.
- **`/storage/{schema}/{model_codi}/{versio}/`: NO EXISTEIX.** El comentari `files/models.py:4` promet `/var/www/fhort-textile/storage/{schema}/{model_codi}/{versio}/` però ni `/var/www/fhort-textile/storage` ni `backend/storage` existeixen.
- **On guarda realment `ModelFitxer.fitxer`** (`upload_to='model_fitxers/%Y/%m/'`): `media/model_fitxers/2026/06/` amb **8 fitxers reals** (p.ex. `FTT-CO27-0001_DOCUMENT_001.pdf`, `LOS-FW27-0001_DOCUMENT_001..005.jpeg`). Altres subcarpetes de `media/`: `import_sessions/`, `bulk_imports/`.
- → El layout versionat per directori que descriu `FitxerVersio` **mai s'ha implementat**; el de facto és el layout pla per data de Django (`%Y/%m/`).

## 1d) 🔴 VEREDICTE DEL FORK (fet, no decisió)

**El contenidor de facto canònic és `models_app.ModelFitxer`.**

| Criteri | `ModelFitxer` | `files.FitxerVersio` |
|---|---|---|
| Writers vius | **2** (`views.py:1078`; `extraction_views.py:1410`) | **0** |
| Readers vius | múltiples (ViewSet `views.py:132`; `ai_analysis_view` `views.py:1122`; export `extraction_views.py:66`; serializer niuat `serializers.py:89`) | **0** |
| Endpoint/router | Sí `/api/v1/model-fitxers/` (`urls.py:41`) + 2 rutes funció | **Cap** |
| Serializer | Sí (`serializers.py:6`) | **Cap** |
| Consum frontends | Sí (`endpoints.js:86`, `ModelSheet.jsx`, `TechSheetEditor.jsx`, `FittingDetail.jsx`) | **0** |
| Fitxers reals en disc | Sí (8 a `media/model_fitxers/2026/06/`) | **0** (`/storage` inexistent) |

`FitxerVersio` és millor **sobre el paper** (versió numèrica neta, `checksum`, `mimetype`, `origen` IA amb `prompt_ia`/`model_ia`, categoria `ia_output`, layout físic versionat) però **mai connectat**. `ModelFitxer` és lleig però **viu i amb dades**, amb defectes coneguts (versió string inconsistent, `versio_anterior` no omplert a l'upload manual, naming canònic només a la branca `_DOCUMENT_`).

---

# 2) ESCRIPTORS I LECTORS REALS de `ModelFitxer` (blast radius)

## Wizard d'importació W5 — CONFIRMAT
- `import_session_confirmar_view(request, token)` — `extraction_views.py:1135` (docstring "Pas W5 — desament definitiu"). Ruta `POST /api/v1/import-sessions/<token>/confirmar/`.
- Creació: `extraction_views.py:1410-1416`. Naming `{codi}_DOCUMENT_{NNN}` (`:1404`), `versio=f'{num:03d}'` (`:1412`).
- **Encadena `versio_anterior`** (`:1394-1412`). Només escriu `categoria='Document'`, `tipus='DOCUMENT'`, i només si `session.document` existeix (`:1393`).

## Fitxa editor (`TechSheetEditor.jsx`)
- `frontend/src/pages/TechSheetEditor.jsx:522` — `GET /api/v1/model-fitxers/?model=${id}&ordering=-data_pujada`. **No filtra per categoria/tipus** (llegeix TOTES). 
- Ús read-only de fet: el llistat es pinta com a botons (`:1119-1132`); en clicar, `addModelFitxer(f)` (`:822-836`) descarrega i insereix com a imatge al llenç. **No escriu cap ModelFitxer.**

## Taula completa de consumidors

| # | file:line | Rol | Categoria/tipus | Què fa |
|---|---|---|---|---|
| 1 | `views.py:132` `ModelFitxerViewSet` | reader+writer (CRUD/DELETE) | totes | API REST `model-fitxers/`; el frontend hi fa DELETE |
| 2 | `views.py:1078` `upload_file_view` | **writer** | `Patro`/`Disseny`/`Document` via `categoria_map` (`:1071-1076`); tipus lliure | Upload manual; versiona per tipus; **sense `versio_anterior`** |
| 3 | `views.py:1122` `ai_analysis_view` | reader | tipus `PATRO,ESCALAT,SKETCH_FLETXES,SKETCH_NET` `[:5]` | Llegeix fitxers físics → Claude; **no escriu res de tornada** |
| 4 | `extraction_views.py:1410` wizard W5 | **writer** | `Document` | Crea PDF doc; **encadena `versio_anterior`**; naming canònic |
| 5 | `extraction_views.py:66` `delete_model_view` | reader + esborrat físic | totes | `default_storage.delete(...)` abans del cascade |
| 6 | `serializers.py:89` `ModelDetailSerializer.fitxers` | reader (niuat) | totes | `GET models/<id>/` retorna `fitxers[]` |
| 7 | `frontend/.../ModelSheet.jsx:1191` `TabFiles` | reader + writer (upload/delete) | per `tipus` (7 de `TIPUS_CONFIG`) | Gestió de fitxers per tipus |
| 8 | `frontend/.../TechSheetEditor.jsx:522` | reader | totes (sense filtre) | Insereix fitxers com a imatge a la fitxa |
| 9 | `frontend/.../FittingDetail.jsx:59-61` `ModelFilesPanel` | reader | `categoria='Patro'`, `tipus='MARCADA'`, `categoria='Document'` | Panell info read-only al fitting |
| 10 | `frontend/.../endpoints.js:86` `modelFitxers.list` | reader (helper) | params lliures | Helper consumit per FittingDetail |

- **Frontend backoffice:** **CAP referència** (grep `ModelFitxer`/`model-fitxers`/`upload-fitxer`/literals categoria → 0). Sense acoblament des del backoffice.
- **Camps morts:** categoria `'Fitting'` (`models.py:332`) i `enviat_ia`/`resultat_ia_path` (`models.py:374-375`) **no els escriu cap writer**; `enviat_ia` només viu al `filterset_fields` (`views.py:137`).

## Punts d'acoblament si es convergís a un únic contenidor
1. **Doble eix `categoria`+`tipus`.** `FittingDetail.jsx:59-61` barreja els dos en la mateixa consulta; `upload_file_view:1071-1076` deriva `categoria` de `tipus`. Cal preservar tots dos camps o reescriure aquestes consultes + el `categoria_map`.
2. **Dos algoritmes de versionat** (W5 encadena per `categoria`; upload manual no encadena, versiona per `tipus`). Cal unificar clau de versionat i decidir si tota escriptura encadena.
3. **Lectors sense filtre** (`TechSheetEditor.jsx:522`, `serializers.py:89`) retornen totes les files; barrejar categories abans separades els exposaria fitxers nous (p.ex. PDFs com a "imatge a inserir").
4. **Literals al frontend** (`TIPUS_CONFIG` `ModelSheet.jsx:1181-1189`; `FittingDetail.jsx:59-61`) han de seguir vàlids amb el `filterset_fields`.
5. **Esborrat físic** (`delete_model_view:66-68`) itera tots els `fitxers`; cal mantenir compatible el bucle i `default_storage.delete`.
6. **Camps morts retirables** sense trencar lectors (`enviat_ia`, `resultat_ia_path`, categoria `'Fitting'`).

---

# 3) EL TAB ACTUAL DE PUJADA (frontend)

Fitxer únic: `frontend/src/pages/ModelSheet.jsx`.

## On viu
- Es renderitza inline quan `activeTab === 'Fitxers'`: `<TabFiles modelId={parseInt(id)} />` (`:518`).
- `TabFiles` **NO és component separat** — funció inline `function TabFiles({ modelId })` (`:1191`). Companys al mateix fitxer: `TIPUS_CONFIG` (`:1181`), `handleUpload` (`:1215`), `handleDelete` de fitxers (`:1243`), `FileCard` (`:1333`).
- (Atenció: el `handleDelete` de `:310` esborra el **model sencer**, no fitxers.)

## Què mostra
- Agrupació **per `tipus`** (no per categoria): una secció per cada clau de `TIPUS_CONFIG` via `Object.entries(TIPUS_CONFIG).map(...)` (`:1289`).
- `TIPUS_CONFIG` verbatim (`:1181-1189`), 7 tipus: `SKETCH_FLETXES`, `SKETCH_NET`, `PATRO`, `MARCADA`, `ESCALAT`, `FITXA`, `ALTRES` (cadascun amb `label`, `icon`, `color`; el títol real surt d'i18n `model_sheet.file_type.${tipus}` a `:1294`, del config només s'usen `icon`+`color`).
- Càrrega: **N peticions paral·leles, una per tipus** — `GET /api/v1/model-fitxers/?model=${modelId}&tipus=${tipus}` (`:1204`), `Promise.all` sobre les claus de `TIPUS_CONFIG`, estat `{ [tipus]: items }` (`:1208-1211`).

## Què permet
- **Upload:** sí. `<input type="file">` per secció (`:1298-1309`), `onChange → handleUpload(tipus, file)` (`:1308`). Endpoint `POST /api/v1/models/${modelId}/upload-fitxer/` (`:1222`), FormData `{fitxer, tipus, nom=file.name}` (`:1217-1220`). El `tipus` es tria **implícitament** prement el botó de la secció; **cap selector de categoria/tipus**; **mai s'envia `categoria`**. `accept=".pdf,.png,.jpg,.jpeg,.svg,.dxf"` (`:1306`).
- **Versions:** **NO es naveguen.** Únic ús: badge `v{versio}` si `versio > 1` (`:1355-1363`). Cada upload s'insereix al davant (`[d, ...prev[tipus]]`, `:1231`), sense agrupar versions d'un mateix fitxer.
- **Delete:** sí, `handleDelete(fitxerId, tipus)` amb `window.confirm` (`:1243-1252`), `DELETE /api/v1/model-fitxers/${fitxerId}/` (`:1245`).
- **Download explícit:** NO (només "view"/preview).

## Sorting / filtering / preview avui
- **Sorting:** NO (el GET no porta `ordering`; només `model`+`tipus`, `:1204`). Ordre = el del backend amb nous uploads forçats al davant.
- **Filtering:** NO interactiu; l'única segmentació és l'agrupació fixa per tipus.
- **Preview:** **SÍ** — modal full-screen (`:1263-1286`): si URL acaba en `.jpg/.jpeg/.png/.svg` → `<img>` (`:1277-1279`); altrament → `<iframe>` (PDF) (`:1281-1282`).

## Render de cada entrada (`FileCard`, `:1333-1392`)
- Targeta 140px. Zona superior clicable (preview): **thumbnail `<img>`** si imatge i hi ha URL (`:1348-1350`), si no **icona del tipus** (`config.icon`/`config.color`, `:1351-1354`). Badge `v{versio}` si `>1` (`:1355-1363`).
- Zona inferior: nom truncat amb `title` complet (`:1366-1373`); botó **View** (`:1375-1381`); botó **delete** (`:1382-1387`).
- URL amb fallback `fitxer.fitxer || fitxer.url` (`:1321`,`:1348-1349`) — coherent amb `get_url()` (FileField o `url_extern`).

---

# 4) PREVISUALITZACIÓ — què és barat

## Descobriment clau (corregeix la premissa)
**El gestor JA TÉ previsualització** (no cal "afegir-la"; com a molt ampliar-la): popup `ModelSheet.jsx:1263-1286` + thumbnail `:1333-1364`.

## Tipus de fitxer reals avui
- **Taxonomia:** categories `Patro/Disseny/Fitting/Document` (`models.py:329-334`); `TIPUS_CONFIG` (rols, no extensions) `:1181-1189`.
- **`accept` de l'upload** (`:1306`): `.pdf,.png,.jpg,.jpeg,.svg,.dxf` (NO accepta xlsx/webp/gif tot i que l'importador processa Excel).
- **Extensions REALS a disc** (`media/model_fitxers/2026/06/`): **6 × `.jpeg`, 2 × `.pdf`**. Zero dxf/png/svg/xlsx avui.
- **Importador/extracció** (`extraction_views.py`, `_cribratge_content_block` `:206-240`): PDF→base64 document (`:211-219`); Excel `.xlsx/.xls`→**textualitzat** via `_excel_to_text` (`:220-222`, helper `:121`), NO desat com a visualitzable; imatge jpeg/png/webp→base64 (`:225-232`). El document origen es desa amb `ContentFile` (`:296`/`:1416`).

## Visors reutilitzables
- **`renderPageToDataURL`** (`TechSheetEditor.jsx:273-360`): renderitza el **model de pàgina propi de l'editor** sobre `Konva.Stage` offscreen → **NO reutilitzable** per a PDFs/imatges externs arbitraris (lligat a l'estructura de dades de l'editor).
- **Llibreries instal·lades** (`frontend/package.json`): `konva ^10.3.0` (`:24`), `react-konva ^19.2.5` (`:29`), `pdf-lib ^1.17.1` (`:25`, **escriptura** de PDF, no renderitzat). **NO instal·lats:** `pdfjs-dist`, `react-pdf`, `xlsx`/sheetjs, cap parser DXF. Backoffice tampoc.
- **Previews existents:** `ModelSheet.jsx:1278/1281/1349`; `FittingDetail.jsx:400` `<img>`; thumbnails interns editor `TechSheetEditor.jsx:1039`, `TechSheetTemplateEditor.jsx:332`.

## Conclusió de cost
- **BARAT (zero lib, ja funciona):** imatges (jpg/jpeg/png/svg) via `<img>`; PDF via `<iframe>` natiu. Afegir **webp/gif** = trivial (ampliar regex `:1277`/`:1335`).
- **CAR (lib nova / treball real):** **DXF** (al `accept` però sense visor; `<iframe>` no el pinta → caldria `dxf-parser`/`three-dxf`); **Excel** (ni al `accept`; caldria sheetjs per render a taula). Avui **no n'hi ha cap a disc** dels dos.

---

# 🔴 VELL / NOU (dobles camins, òrfenes, documentat-no-implementat)

| Tema | VELL/VIU | NOU/PROMÈS | Estat |
|---|---|---|---|
| **Contenidor de fitxers** | `ModelFitxer` (viu, amb dades) | `files.FitxerVersio` (disseny net amb checksum/origen IA) | **Esquelet mort** — 0 consumidors |
| **Layout físic** | `media/model_fitxers/%Y/%m/` (pla per data) | `/storage/{schema}/{model_codi}/{versio}/` (`files/models.py:4`) | **Mai implementat** (carpeta inexistent) |
| **Eix de classificació** | `tipus` (7 rols, segmenta la UI) | `categoria` (4 valors, backend filter) | **Conviuen, inconsistents** — el tab no envia mai `categoria` |
| **Versionat** | upload manual: NO encadena `versio_anterior`, versió `"2"` | W5: encadena, versió `"002"`, naming canònic | **Dos algoritmes divergents** |
| **Versió numèrica** | `ModelFitxer.versio` = CharField (string) | `FitxerVersio.versio` = PositiveIntegerField | string inconsistent al viu |
| **Previsualització** | `<img>`+`<iframe>` JA al tab | (premissa: "afegir si és barat") | **Ja existeix** per imatge+PDF |
| **Camps morts** | categoria `'Fitting'`, `enviat_ia`, `resultat_ia_path` | — | Declarats, **cap writer** |
| **Cadena de versions a la UI** | badge `v{N}` | navegació de versions | **No navegable** (forat Finder) |

---

# ⚖️ PER DECIDIR (Agus)

1. **El fork de contenidor.** FET: `ModelFitxer` és el canònic; `FitxerVersio` és esquelet mort. Decisió oberta:
   - (A) Partir de `ModelFitxer` i **evolucionar-lo** absorbint les bones idees de `FitxerVersio` (checksum, `origen` IA, versió numèrica, layout `/storage`), i **eliminar `files.FitxerVersio`** per tancar l'ambigüitat; o
   - (B) Migrar de debò a `FitxerVersio` (cost: migració de dades dels 8 fitxers + reescriure 2 writers + ~10 consumidors + frontends). 
   - 💡 PROPOSTA (a validar): l'opció (A) té molt menys blast radius (el backoffice no hi toca; els acoblaments són els 6 punts del bloc 2). La decisió de la **clau de versionat unificada** (per `tipus`? per `categoria`? per arrel-categoria del Finder?) és prèvia a qualsevol redisseny.

2. **Eix de classificació del Finder.** Avui hi ha `categoria` (4) i `tipus` (7) i el tab només usa `tipus`. ⚖️: quina és "l'arrel/categoria" del gestor Finder — `tipus`, `categoria`, o un eix nou? Això determina naming, agrupació i filtres.

3. **Abast de previsualització.** FET: imatge+PDF ja funcionen barat. ⚖️: ampliar a webp/gif (trivial) sí/no; i **DXF/Excel** (cars, sense fitxers reals avui) — diferir fins que apareguin a disc, o invertir ja?

4. **Què fer amb `files.FitxerVersio`.** ⚖️: eliminar-lo (recomanat per tancar el fork) o conservar-lo com a referència de disseny? Mantenir-lo sense consum perpetua l'ambigüitat.
