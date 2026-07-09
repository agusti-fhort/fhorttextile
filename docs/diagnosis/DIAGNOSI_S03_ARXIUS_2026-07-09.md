# DIAGNOSI — S03 Arxius (gestió unificada d'arxius)

> Data: 2026-07-09 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`.
> Abast: verificar 4 fets abans de dissenyar la gestió unificada d'arxius (FTT 07 S03).
> Convenció: cada afirmació porta `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi
> (no especulat).** Les idees van marcades `💡 PROPOSTA (a validar)` i no són decisions.
> Cap escriptura, cap migració, cap comanda d'estat. `migrate_schemas --list` no s'ha usat.

**Precedent:** `docs/diagnosis/DIAGNOSI_FITXERS.md` (2026-06-27) va mapejar el mateix terreny
**abans** de la jubilació de l'app `files`. Els seus punts 1 i el cens de disc ("8 fitxers reals")
han quedat **superats pels fets** que consten aquí (§1 i §2f). No s'ha tocat: segellar-la
correspon al sprint que la superi.

---

## Resum executiu

1. **`files.FitxerVersio` és MORT i ja enterrat.** No és un esquelet pendent de treure: es va
   jubilar el 2026-06-27 (commit `dfee1b3`). Zero codi, zero taula a la BD, cap `/storage/`.
   L'únic residu són **2 files a `django_migrations`** i **1 comentari** de docstring. **No hi ha
   res a migrar ni cap dada a rescatar.**
2. **`ModelFitxer` és el contenidor únic i viu**, però amb **dos eixos de classificació que no
   estan alineats**: `categoria` (4 choices reals) i `tipus` (string lliure, sense choices, 7+
   valors de facto). A la BD de staging **només s'usa `categoria='Document'`**: les categories
   `Patro`, `Disseny` i `Fitting` tenen **0 files** tot i tenir consumidors frontend que hi
   filtren. Aquesta és la fractura central que S03 ha de resoldre.
3. **El versionat té dos escriptors amb algoritmes divergents** (un encadena `versio_anterior`,
   l'altre no) i la invariant `is_current` **no té constraint a la BD**, només documentació.
   L'estat real ho reflecteix: 209 `TECHSHEET` amb només **4 `is_current`**.
4. **El media NO està aïllat per tenant.** Cap `TenantFileSystemStorage`, cap
   `MULTITENANT_RELATIVE_MEDIA_ROOT`: tots els schemas escriuen al mateix path físic. Avui hi ha
   1 tenant (`fhort`), per tant no hi ha col·lisió — però és una bomba de rellotgeria per al
   segon tenant.
5. **El disc i la BD ja han divergit:** 8 fitxers orfes a disc i 1 fantasma a BD (§2f).
6. **`TechSheetEditor` degrada net sense `task_id`** (guard explícit): obrir la fitxa des del
   Model consulta i desa, i simplement **no imputa temps**. No hi ha risc de crash.
7. **El slot d'import de B3 és una reserva visual deliberada**, no un bug: botó `disabled`, sense
   handler, amb comentari *"inert. NO construir lògica"* i endpoint backend inexistent.

---

# BLOC 1 — `files.FitxerVersio`: ¿VIU o MORT?

## 1a) Veredicte de codi: MORT, i ja eliminat del repo

L'app sencera `fhort/files/` va ser eliminada al commit **`dfee1b3`** (2026-06-27 08:16:28 +0000):

```
chore(files): Z — jubila l'app files (esquelet mort FitxerVersio, 0 consumidors)
 backend/fhort/files/models.py                  | 66 ----------
 backend/fhort/files/migrations/0001_initial.py | 45 ----------
 backend/fhort/settings.py                      |  1 -
 9 files changed, 126 deletions(-)
```

- `grep -rn "FitxerVersio" backend/ frontend/src/ frontend-backoffice/src/` → **1 sol hit**, i és
  un comentari: `backend/fhort/fitting/models.py:363` →
  `"""Autonomous photo (FileField pattern like ModelFitxer, not FitxerVersio).`
- **Consumidors: NO EXISTEIXEN.** Cap view, cap serializer, cap url, cap import, cap referència
  frontend. El directori `backend/fhort/files/` **NO EXISTEIX**.
- `'fhort.files'` **NO EXISTEIX** a `INSTALLED_APPS` (`backend/fhort/settings.py:76`).

## 1b) Veredicte de BD (staging, schema `fhort`)

Consultes read-only executades:

| Comprovació | Resultat |
|---|---|
| `SELECT to_regclass('fhort.files_fitxerversio')` | `NULL` → **la taula NO EXISTEIX** |
| `SELECT to_regclass('public.files_fitxerversio')` | `NULL` → **NO EXISTEIX** |
| Schemas del tenant | només `public` i `fhort` (1 tenant) |

`SELECT count(*) FROM fhort.files_fitxerversio` **no es pot executar**: la relació no existeix.
Per tant, **no hi ha dades**. La migració `files.0002_delete_fitxerversio` consta aplicada.

**Residu (l'únic que en queda):** 2 files a `fhort.django_migrations`:

| app | name | applied |
|---|---|---|
| `files` | `0001_initial` | 2026-05-25 12:11:49 |
| `files` | `0002_delete_fitxerversio` | 2026-06-27 08:14:09 |

Són inofensives (Django ignora migracions d'apps desinstal·lades). Netejar-les és opcional.

## 1c) Contingut físic a `/storage/`

- `/var/www/ftt-staging/storage/` → **NO EXISTEIX**.
- L'únic `/var/www/*/storage` del servidor és `/var/www/assessment/storage` (conté `reports/`),
  que pertany a un **altre projecte** (assessment), no a FTT.

> **Veredicte Bloc 1: MORT i enterrat. Llest.** S03 no ha de fer cap migració de dades ni cap
> esborrat de codi per aquest front. L'única acció possible (opcional, cosmètica) és eliminar les
> 2 files de `django_migrations`.

---

# BLOC 2 — `ModelFitxer`: inventari complet

## 2a) Definició — `backend/fhort/models_app/models.py:328`

Camps:

| Camp | Tipus | Línia |
|---|---|---|
| `model` | `FK(Model, CASCADE, related_name='fitxers')` | `models.py:352` |
| `nom_fitxer` | `CharField(255)` | `353` |
| `categoria` | `CharField(20, choices=CATEGORIA_CHOICES)` | `354` |
| `tipus` | `CharField(30, default='ALTRES', blank=True)` — **sense choices** | `355` |
| `versio` | `PositiveIntegerField(default=1)` | `356` |
| `is_current` | `BooleanField(default=True, db_index=True)` | `358` |
| `path_servidor` | `CharField(500)` | `359` |
| `versio_anterior` | `FK('self', SET_NULL, related_name='versions_posteriors')` | `360` |
| `generat_des_de` | `FK('self', SET_NULL, related_name='exports_generats')` | `370` |
| `accessible_portal` | `BooleanField(default=False)` | `377` |
| `pujat_per` | `FK('accounts.UserProfile', SET_NULL)` | `378` |
| `data_pujada` | `DateTimeField(auto_now_add=True)` | `384` |
| `mida_bytes` | `BigIntegerField()` | `385` |
| **`fitxer`** | **`FileField(upload_to='model_fitxers/%Y/%m/')`** | **`388`** |
| `url_extern` | `URLField(null, blank)` | `389` |
| `descripcio` | `TextField(null, blank)` | `393` |
| `enviat_ia` | `BooleanField(default=False)` | `402` |
| `resultat_ia_path` | `CharField(500)` | `403` |
| `checksum` | `CharField(64, blank)` | `406` |
| `mimetype` | `CharField(100, blank)` | `407` |
| `origen` | `CharField(20, choices=ORIGEN_CHOICES, default='upload')` | `408` |

Mètode `get_url()` a `models.py:395` (prioritat `url_extern` › `fitxer.url` › `None`).

**`CATEGORIA_CHOICES` — literal exacte, `models.py:329-334`:**

```python
('Patro', 'Patró'), ('Disseny', 'Disseny'), ('Fitting', 'Fitting'), ('Document', 'Document')
```

**`ORIGEN_CHOICES` — `models.py:337-342`:** `'upload'`, `'ia_escalat'`, `'ia_marcada'`, `'ia_ocr'`.

**Constants `.ftt` — `models.py:348-350`:** `TIPUS_TECHSHEET='TECHSHEET'`, `TIPUS_EXPORT='EXPORT'`,
`FTT_EXTENSION='.ftt'`.

**El segon eix (`tipus`) no té choices.** Els valors que circulen de facto (convenció de codi, no
validats per Django): `ALTRES`, `DOCUMENT`, `TECHSHEET`, `EXPORT`, `PATRO`, `ESCALAT`,
`SKETCH_FLETXES`, `SKETCH_NET`, `MARCADA`. Els 4 últims els consumeix el filtre d'anàlisi IA a
`backend/fhort/models_app/views.py:1142-1145`.

**La invariant `is_current` NO té constraint a la BD** — `Meta` a `models.py:410-412` només té
`verbose_name`. Està documentada, no imposada.

## 2b) On desa el FileField

- `upload_to='model_fitxers/%Y/%m/'` (`models.py:388`), **storage per defecte** (no s'especifica
  `storage=`).
- `MEDIA_URL = '/media/'` — `backend/fhort/settings.py:161`
- `MEDIA_ROOT = BASE_DIR / 'media'` — `backend/fhort/settings.py:162`
- Path físic real: `/var/www/ftt-staging/backend/media/model_fitxers/YYYY/MM/`

**⚠️ Aïllament per tenant: NO EXISTEIX.** Confirmat per grep a tot `backend/` (fora de `venv/`):
- `TenantFileSystemStorage` → **NO EXISTEIX**
- `MULTITENANT_RELATIVE_MEDIA_ROOT` → **NO EXISTEIX**
- `DEFAULT_FILE_STORAGE` / `STORAGES = ` → **NO EXISTEIXEN**

Tot i ser projecte django-tenants (`settings.py:37,86,119`), **tots els schemas escriurien al
mateix path físic**. Avui només hi ha 1 tenant (`fhort`), per tant no hi ha col·lisió observable.

**Migracions que l'han tocat:** `0001_initial.py:81` (creació; `versio` era `CharField(10)`) ·
`0005_sprint1b_new_models.py:18-30` (afegeix `descripcio`, `fitxer`, `url_extern`) ·
`0016_modelfitxer_tipus.py` · `0045_modelfitxer_versionat_invariant.py` (afegeix `is_current`,
`checksum`, `mimetype`, `origen`; backfill + `versio` string→int) · `0047_modelfitxer_generat_des_de.py` ·
`0050_delete_techsheet.py:30` (**data migration que escriu registres** via `create_document`).

## 2c) Punts d'ESCRIPTURA (backend)

**Escriptor canònic de la invariant:** `services_fitxers.save_model_file()` —
`backend/fhort/models_app/services_fitxers.py:36-86` (construcció a `:63`, INSERT a `:80`, posa el
predecessor a `is_current=False` a `:82-84`).

| # | Punt d'escriptura | fitxer:línia | Endpoint | Què desa |
|---|---|---|---|---|
| 1 | Upload manual (Finder) | `views.py:1064-1117` (crida `save_model_file` a `:1095`) | `POST /api/v1/models/<id>/upload-fitxer/` (`urls.py:197`) | `categoria`/`tipus` **opcionals del request**, `origen='upload'` |
| 2 | **ViewSet CRUD genèric** | `views.py:135` `ModelFitxerViewSet(ModelViewSet)` | router `model-fitxers` (`urls.py:42`) — `POST/PUT/PATCH/DELETE` | ⚠️ **NO passa per `save_model_file`**: escriu via serializer `fields='__all__'`, sense invariant |
| 3a | Crear document `.ftt` | `services_ftt_document.py:179` `create_document` | `POST /api/v1/models/<id>/ftt-document/` (`urls.py:174`) | `categoria='Document'`, `tipus='TECHSHEET'` |
| 3b | Desar versió `.ftt` | `services_ftt_document.py:209` `save_document` | `PATCH /api/v1/ftt-documents/<id>/` (`urls.py:175`) | encadena `versio_anterior=head`; requereix lock |
| 3c | Export PDF | `services_ftt_document.py:226` `save_export` (`:233-234`) | `POST /api/v1/ftt-documents/<id>/export/` (`urls.py:178`) | `tipus='EXPORT'`, escriu `generat_des_de` |
| 4 | **Import guiat (wizard W5 → confirmar)** | `extraction_views.py:1490-1514` (`save_model_file` a `:1507`) | `POST /api/v1/import-sessions/<token>/confirmar/` (`urls.py:84`) | `categoria='Document'`, `tipus='DOCUMENT'`, naming `{codi}_DOCUMENT_{NNN}`, **encadena `versio_anterior`** |
| 5 | Esborrat físic + cascade | `extraction_views.py:66-75` (`default_storage.delete` a `:70`) | `DELETE /api/v1/models/<id>/delete/` (`urls.py:67`) | esborra bytes + FK CASCADE |
| 6 | Data migration | `models_app/migrations/0050_delete_techsheet.py:30` | — | crea documents `.ftt` per TechSheets v2 |

**NO EXISTEIXEN:** cap signal (`post_save`/`pre_delete`) sobre `ModelFitxer`, cap management
command que l'escrigui, cap `ModelFitxer.objects.create()` directe fora de `save_model_file`.
El mòdul `fitting` **NO** crea `ModelFitxer` (`fitting/models.py:363` només l'esmenta com a patró).

**Divergència d'algoritmes de versionat (FET):** l'import W5 (#4) i el desat `.ftt` (#3b) encadenen
`versio_anterior`; el **ViewSet genèric (#2)** no passa per `save_model_file` i pot escriure
`is_current=True` sense apagar el predecessor. No hi ha constraint que ho impedeixi (§2a).

## 2d) Punts de LECTURA (backend)

- `ModelFitxerSerializer` — `serializers.py:6-10`, `fields='__all__'`,
  `read_only_fields=('data_pujada',)`.
- **Anidat al detall del model:** `serializers.py:96` → `fitxers = ModelFitxerSerializer(many=True, read_only=True)`.
- Cadena de versions: `services_fitxers.py:89-109` `get_version_chain`; exposada a
  `views.py:144-149` (acció `versions`).
- Contingut `.ftt`: `services_ftt_document.py:188-195` `load_document`, servit per
  `ftt_document_views.py:95-105` i `FttDocumentAssetView` (`ftt_document_views.py:227-240`).
- Anàlisi IA: `views.py:1142-1145` filtra `tipus__in=['PATRO','ESCALAT','SKETCH_FLETXES','SKETCH_NET']`
  i llegeix bytes a `:1152` → `POST /api/v1/models/<id>/analisi-ia/` (`urls.py:198`).
- Locks: `ftt_models.py:21` (`FttDocumentLock` → FK a `'models_app.ModelFitxer'`).

## 2e) Consumidors FRONTEND

**`frontend-backoffice/src/`: cap hit.** (grep `model-fitxers|modelFitxer|ModelFitxer|upload-fitxer|ftt-document` → buit.)

**`frontend/src/`:**

| Fitxer:línia | Acció |
|---|---|
| `api/endpoints.js:100-102` | `modelFitxers.list()` — **només llista** (comentari "read-only") |
| `pages/ModelSheet.jsx:549` | llista TECHSHEET current |
| `pages/ModelSheet.jsx:1216` | llista tots els current (`?model=&is_current=true&ordering=-data_pujada`) |
| `pages/ModelSheet.jsx:1224-1249` | **upload** (`POST models/<id>/upload-fitxer/`, multipart) |
| `pages/ModelSheet.jsx:1251-1260` | llegeix cadena de versions |
| `pages/ModelSheet.jsx:1262-1268` | **esborra** (`DELETE model-fitxers/<id>/`) |
| `pages/FittingDetail.jsx:59-61` | llista 3 grups: `categoria:'Patro'`, `tipus:'MARCADA'`, `categoria:'Document'` |
| `App.jsx:96` | **crea** document `.ftt` |
| `App.jsx:113` | llista TECHSHEET current per decidir redirecció |
| `pages/TechSheetEditor.jsx:1823` | llista current |
| `pages/TechSheetEditor.jsx:1834,1843` | llegeix document; `versio` ve de `ModelFitxer.versio` |
| `pages/TechSheetEditor.jsx:1849,1868,1881,1893` | lock / unlock |
| `pages/TechSheetEditor.jsx:1954` | **desa** versió nova (`PATCH`) |
| `pages/TechSheetEditor.jsx:3031` | export PDF |
| `pages/TechSheetEditor.jsx:3052` | save-as-template |
| `pages/TechSheetEditor.jsx:2771` vs `:3408` | `addModelFitxer` **definida però òrfena**: `:3408` documenta que els botons "Fitxers del model" del ribbon **s'han retirat** |

⚠️ **`FittingDetail.jsx:59-61` filtra per `categoria='Patro'` i `tipus='MARCADA'`, que a la BD de
staging tenen 0 files** (§2f). Aquest panell està buit per construcció avui.

## 2f) Estat REAL a la BD i al disc (staging, schema `fhort`)

Cens de `fhort.models_app_modelfitxer` (214 files):

| categoria | tipus | n | is_current | sense FileField | amb url_extern |
|---|---|---|---|---|---|
| Document | DOCUMENT | 3 | 3 | 0 | 0 |
| Document | EXPORT | 2 | 2 | 0 | 0 |
| Document | TECHSHEET | **209** | **4** | 0 | 0 |

- **Les categories `Patro`, `Disseny` i `Fitting` tenen 0 files.** El sistema real només usa
  `Document`. L'eix `categoria` és, avui, constant.
- 209 TECHSHEET / 4 `is_current` → cadenes de versions llargues (autosave del `.ftt`).
- `url_extern` no s'usa mai (0 files).

Disc — `/var/www/ftt-staging/backend/media/`: 33 MB totals; `model_fitxers/` = **16 MB, 221 fitxers**
(210 `.ftt`, 6 `.jpeg`, 4 `.pdf`, 1 `.xlsx`). Altres subdirs: `bulk_imports/`, `customer_logos/`,
`import_sessions/`, `tenant_logos/`.

**Divergència BD ↔ disc (FET):**

- **1 fantasma** (fila a BD, bytes absents a disc):
  `model_fitxers/2026/06/BRW-SS26-0001_DOCUMENT_001.pdf`
- **8 orfes** (bytes a disc, cap fila a BD):
  `BRW-FW26-0004_fitxa_zzLptcX.ftt`, `FTT-FW27-0001_DOCUMENT_001.pdf`,
  `LOS-FW27-0001_DOCUMENT_00{1..5}.jpeg`, `LOS-FW27-0002_DOCUMENT_001.jpeg`

> **Veredicte Bloc 2: cal decisió del CTO abans de dissenyar.** El contenidor és únic i sa, però
> (i) l'eix `categoria` està mort a la pràctica mentre `tipus` fa la feina sense choices;
> (ii) el ViewSet genèric és una porta del darrere que salta la invariant de versionat;
> (iii) el media no està aïllat per tenant; (iv) BD i disc ja han divergit.

---

# BLOC 3 — `TechSheetEditor`: entrada i vincle amb la tasca

## 3a) Com rep `model id` i `task id`

Component: `frontend/src/pages/TechSheetEditor.jsx:1293` (lazy import a `frontend/src/App.jsx:42`).

**Ruta:** `frontend/src/App.jsx:225` → `<Route path="/models/:id/ftt/:fitxerId" .../>`.
**No hi ha `task_id` al path**: sempre viatja com a **query param**.

Lectures dins el component:
- `TechSheetEditor.jsx:1293` → `const { id, fitxerId } = useParams()` (model id = `id`)
- `TechSheetEditor.jsx:1295-1296` → `const taskId = searchParams.get('task_id')`
- `TechSheetEditor.jsx:1298-1299` → `fttMode = !!fitxerId` · `isEditMode = !!taskId`
- `location.state`: **NO EXISTEIX** cap lectura.

**Cadena de navegació (endarrere).** Ningú navega directament a `/ftt/:fitxerId` des del Kanban.
El patró és `/models/:id/fitxa?task_id=…` → **`FttResolver`** (`App.jsx:81`) resol o crea el `.ftt`
i redirigeix **conservant el `task_id`**:
- `App.jsx:87` llegeix `sp.get('task_id')`
- `App.jsx:101` i `App.jsx:118` → `navigate(\`/models/${id}/ftt/${f.id}${taskId ? \`?task_id=${taskId}\` : ''}\`, {replace:true})`

| Origen | fitxer:línia | Passa `task_id`? |
|---|---|---|
| WorkPlan (pla de treball) | `components/model/WorkPlan.jsx:30` → `case 'tech_sheet'`; navega a `:249` | ✅ sí |
| TaskTree (arbre/tauler) | `components/model/TaskTree.jsx:42` → `case 'tech_sheet'`; navega a `:117` | ✅ sí |
| ModelSheet, tab Fitxers | `pages/ModelSheet.jsx:1428` → `navigate('/models/<id>/ftt/<fitxerId>')` | ❌ no |
| ModelSheet, botons "Fitxa" | `pages/ModelSheet.jsx:583,617,622` → `navigate('/models/<id>/fitxa')` | ❌ no |

El comportament és **intencionat i documentat** a `ModelSheet.jsx:538-539`:
*"Consulta des del Model obre sense task_id → mode consulta. L'edició registrada es fa des del
Kanban (que passa ?task_id=…)"*.

## 3b) Què passa sense `task_id`: **degrada net, no es trenca**

La imputació de temps és la transició d'estat de la tasca. Únic punt d'emissió a l'editor:

- `TechSheetEditor.jsx:1862` (cleanup del `useEffect` de càrrega):
  `if (taskId) { fetch(\`${API}/api/v1/model-task-items/${taskId}/transition/\`, { … body: {to_status:'Paused'}, keepalive:true }) }`

**El guard `if (taskId)` de la línia 1862 protegeix l'única crida.** Sense `task_id` no s'emet cap
transició → **no s'imputa ni s'atura temps**, i **no hi ha cap fetch amb `undefined`**.

L'inici a `InProgress` **no** el fa l'editor: el fan WorkPlan/TaskTree abans de navegar. L'editor
només emet el `Paused` de sortida.

L'edició segueix funcionant sense tasca perquè depèn de `fttMode`/`locked`, no de `taskId`:
`fttMode = !!fitxerId` (`:1298`, sempre cert en aquesta ruta) → adquireix lock (`:1849`),
`locked = lockState==='owned'` (`:1352`), i l'autosave depèn de `locked` (`:1946+`), no de `taskId`.

**Conseqüència:** obrir la fitxa des del Model **desa canvis reals sense deixar rastre de temps**.
És una degradació silenciosa, no un error.

## 3c) TaskType — el catàleg canònic té **14 codes, no 9**

- Model: `backend/fhort/tasks/models.py:21` · camp `code = SlugField(50, unique=True)` a `:38`.
- Seed canònic: `backend/fhort/tasks/migrations/0025_seed_canonical_task_types.py` (llista `CATALEG`
  a `:8-24`, funció `seed` a `:26`).

| ordre | code | name | eina/mode |
|---|---|---|---|
| 5 | `design_review` | Revisió de disseny | — |
| 6 | `design_clarify` | Aclariments amb disseny | — |
| 10 | `pattern_digit` | Patró digitalització | patro/digitalitzar |
| 20 | `pattern_cad` | Patró CAD | patro/disseny_base |
| 30 | `pattern_hand` | Patró a mà | — |
| 40 | `pom` | Definició POM | mesures/autoria_base |
| 45 | `size_check` | Mesurar prenda | mesures/presa |
| 46 | `grading` | Escalat | escalat/propagacio |
| **50** | **`tech_sheet`** | **Fitxa tècnica** | **fitxa/document** |
| 55 | `pattern_review` | Revisió de patró CAD | patro/revisio |
| 70 | `bom` | Definició BOM | fitxa/bom |
| 81 | `scaling` | Escalat CAD | patro/escalat |
| 82 | `marking` | Marcada | patro/marcada |
| 90 | `audit` | Auditoria de model | — |

**Resposta a la pregunta del brief:** el code de la fitxa tècnica és **`tech_sheet`**
(`0025_seed_canonical_task_types.py:17`, `eina='fitxa'`, `mode='document'`).

**Discrepància amb el brief (FET):** el brief demana "els 9 TaskType"; el catàleg viu en té **14**.
Cap seed/fixture amb exactament 9: **NO EXISTEIX**.

Ús dels codes literals al frontend: `WorkPlan.jsx:29,30,33,36,53-56` i `TaskTree.jsx:31-35,41-44`.
(Els `t('tech_sheet…')` d'`App.jsx:139,143` i `TechSheetTemplateEditor.jsx` són **claus i18n**, no
task codes.)

Nota transversal: `backend/fhort/tasks/management/commands/retype_scaling_to_grading.py:37` re-tipa
`ModelTask` de `scaling` → `grading`. Els dos codes coexisteixen al catàleg.

> **Veredicte Bloc 3: llest.** L'entrada està ben definida i el degradat sense tasca és net i
> intencionat. L'únic fet a decidir és si "desar sense imputar temps" és acceptable.

---

# BLOC 4 — Slot d'import inert de B3 (autoria d'items)

**Ubicació exacta:** `frontend/src/pages/ItemAuthoring.jsx:272-288`, al PAS 1 · CONTEXT, just
després del `RuleSetPicker`.

```jsx
{/* SLOT D'IMPORT — previst (Fase C), inert. NO construir lògica. */}   // :272
<div style={{ marginTop: 20, paddingTop: 16, borderTop: '0.5px dashed var(--border)' }}>
  <button type="button" disabled title={t('item_authoring.import_tooltip')}   // :274
    style={{ … cursor: 'not-allowed', opacity: 0.7 }}>                        // :279
    <i className="ti ti-file-import" />
    {t('item_authoring.import_soon')}
    <span>{t('item_authoring.coming_soon')}</span>
  </button>
</div>
```

Proves que és inert: `disabled` **sense cap `onClick`** (`:274`); `cursor:'not-allowed'` (`:279`);
comentari explícit `:272`. El propòsit ja s'anuncia a la capçalera del fitxer:
`ItemAuthoring.jsx:14` → `// viu, onPick=assignar FK via serializer B3a). [Slot d'import previst, inert.]`

**Quin contracte esperava** (segons i18n, paritat ca/en/es a `:2436-2438` de cada fitxer):
- `frontend/src/i18n/ca.json:2436` → `"import_soon": "Importar fitxa"`
- `frontend/src/i18n/ca.json:2437` → `"import_tooltip": "Disponible properament (Fase C)"`
- `frontend/src/i18n/ca.json:2438` → `"coming_soon": "properament"`

És a dir: **"Importar fitxa"**, explícitament diferit a **Fase C**. **No hi ha endpoint, ni forma de
dades, ni handler cablejats: només la reserva visual.**

**Backend: l'endpoint d'import-a-ITEM NO EXISTEIX.** Els imports vius aterren tots a capa **MODEL**:
- `import-sessions/…` (wizard d'extracció) — `backend/fhort/models_app/urls.py:52-85`
- `tech-sheet` (via API Anthropic) — `backend/fhort/models_app/urls.py:119-121`
- `bulk-import/…` (Excel massiu) — `backend/fhort/models_app/urls.py:131-141`
- `backend/fhort/commerce/urls.py`: cap ruta amb `import` (grep buit).

Cap endpoint escriu sobre `GarmentTypeItem` / `ItemBaseMeasurement`.

**Documentació que el descriu** (fora de `docs/diagnosis/`, però vigent):
- `docs/LECTURA_IMPORT_FORMA_SORTIDA.md:14` → *"L'import escriu AVUI a taules de MODEL, no d'ITEM."*
- `docs/LECTURA_IMPORT_FORMA_SORTIDA.md:229-232` i `:275-278` → el destí-catàleg de l'import és
  *"Decisió de Fase C"*.
- `docs/DIAGNOSI_SEAM_TALLES_GRADING_ITEM.md:152` → *"💡 Commutador de destí de l'import. Afegir un
  selector `destinacio ∈ {model, cataleg}`… El destí catàleg escriuria `GradingRuleSet`/`GradingRule`
  + `GarmentPOMMap` + `ItemBaseMeasurement`"* ← aquest és el contracte backend que el slot espera.

Nota: la referència a "B3" de `DISSENY_MODUL_COMERCIAL.md:275` (`SalesOrder + WorkOrder + wizard`)
és **un B3 diferent** (fase comercial), no el B3 d'autoria d'items. No documenta aquest slot.

> **Veredicte Bloc 4: llest.** El slot és una reserva deliberada amb contracte ja esbossat a
> `DIAGNOSI_SEAM_TALLES_GRADING_ITEM.md:152`. No és deute ni bug.

---

# TAULA FINAL — EXISTEIX / FALTA / DIFERENT (per al CTO)

| # | Fet | Estat | Referència | Risc per a S03 |
|---|---|---|---|---|
| 1 | `files.FitxerVersio` (model, app, taula) | **NO EXISTEIX** (jubilat `dfee1b3`) | commit `dfee1b3` · `to_regclass`=NULL | Cap. Res a migrar |
| 2 | Files `django_migrations` app `files` | **EXISTEIXEN** (2) | `fhort.django_migrations` | Nul; neteja opcional |
| 3 | `/var/www/ftt-staging/storage/` | **NO EXISTEIX** | fs | Cap |
| 4 | `ModelFitxer` com a contenidor únic | **EXISTEIX** | `models_app/models.py:328` | — |
| 5 | Eix `categoria` (4 choices) | **DIFERENT**: 0 files a `Patro`/`Disseny`/`Fitting` | cens BD §2f | 🔴 **Alt** — dissenyar sobre un eix mort |
| 6 | Eix `tipus` (9 valors de facto) | **DIFERENT**: `CharField` **sense choices** | `models.py:355` | 🔴 **Alt** — cap validació |
| 7 | `FittingDetail` filtra `Patro`/`MARCADA` | **EXISTEIX** però retorna 0 | `FittingDetail.jsx:59-61` | 🟠 Panell buit avui |
| 8 | Invariant `is_current` a la BD | **NO EXISTEIX** (només documentada) | `models.py:410-412` | 🟠 209 TECHSHEET / 4 current |
| 9 | ViewSet CRUD que salta `save_model_file` | **EXISTEIX** | `views.py:135` + `urls.py:42` | 🔴 **Alt** — porta del darrere del versionat |
| 10 | Dos algoritmes de versionat divergents | **EXISTEIXEN** | `extraction_views.py:1507` vs `views.py:1095` | 🟠 Naming i encadenat diferents |
| 11 | Aïllament de media per tenant | **NO EXISTEIX** | `settings.py:161-162` | 🟠 Inert amb 1 tenant; 🔴 amb 2 |
| 12 | Coherència BD ↔ disc | **DIFERENT**: 8 orfes + 1 fantasma | §2f | 🟠 Cal decidir política |
| 13 | `addModelFitxer` al ribbon de l'editor | **EXISTEIX òrfena** (invocació retirada) | `TechSheetEditor.jsx:2771` vs `:3408` | 🟢 Codi mort |
| 14 | `TechSheetEditor` sense `task_id` | **EXISTEIX** guard net | `TechSheetEditor.jsx:1862` | 🟢 Degrada, no trenca |
| 15 | Code de la fitxa tècnica | **`tech_sheet`** | `0025_seed_canonical_task_types.py:17` | — |
| 16 | "9 TaskType" del brief | **DIFERENT**: n'hi ha **14** | `0025_seed_canonical_task_types.py:8-24` | 🟢 Corregir la premissa |
| 17 | Slot d'import a `ItemAuthoring` | **EXISTEIX inert** (Fase C) | `ItemAuthoring.jsx:272-288` | 🟢 Reserva deliberada |
| 18 | Endpoint d'import cap a `GarmentTypeItem` | **NO EXISTEIX** | `commerce/urls.py` (grep buit) | 🟢 Diferit a Fase C |
| 19 | Consumidors de fitxers al backoffice | **NO EXISTEIXEN** | grep buit a `frontend-backoffice/src/` | 🟢 Superfície única |

---

## 💡 PROPOSTES (a validar — NO són decisions)

> Marcades segons Patró C: dissenya el CTO, no l'agent. S'anoten aquí per no perdre'ls.

1. **Unificar els dos eixos** (`categoria` + `tipus`) en un de sol amb `choices`, en comptes
   d'arrossegar-ne dos, un dels quals no valida res i l'altre no s'usa (§2a, §2f, taula #5/#6).
2. **Tancar la porta del darrere:** fer el `ModelFitxerViewSet` read-only (o forçar-lo a passar per
   `save_model_file`) perquè l'única via d'escriptura sigui la que manté la invariant (taula #9).
3. **Imposar la invariant `is_current`** amb un `UniqueConstraint` condicional a la BD (taula #8).
4. **Aïllar el media per tenant** abans que entri el segon tenant (taula #11).
5. **Política de reconciliació disc↔BD** i comanda de verificació, abans de construir el Finder
   sobre dades que ja divergeixen (taula #12).
6. Decidir si "desar la fitxa sense imputar temps" (obertura des del Model) és acceptable o si la
   consulta ha de ser read-only de veritat (§3b).

Cap d'aquestes s'ha tocat. Aquesta sessió no ha escrit ni una línia de codi.
