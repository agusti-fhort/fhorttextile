# DIAGNOSI — MOTOR DE PATRONS · S0 (cens del terreny)

> **Data:** 2026-07-12 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
> **Abast:** cens verificat del terreny que el motor de patrons trepitjarà (pipeline de fitxers,
> biblioteca d'item, material real, fitxa del model, límits d'upload, render, contracte del
> grading, TaskTypes, convencions d'app), abans que S1 escrigui la primera línia.
> **Encàrrec:** S0 de `PLA_IMPLEMENTACIO_MOTOR_PATRONS.md` (§S0, B1–B9).
>
> **Convenció:** tota afirmació porta `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi**
> (verificat, no especulat). Les propostes van marcades `💡 PROPOSTA (a validar)` i **no** són
> decisions: les decisions són humanes (Patró C).
>
> **Guardes:** branca `dev` ✅ · cap escriptura de codi, cap migració, cap seed, cap restart ·
> BD només `SELECT` (schema `fhort`) · únic fitxer creat: aquest.

---

## RESUM EXECUTIU

1. **S1 ARRENCA COIX: falta material.** L'únic fitxer de patró al servidor és
   `AMELIA_AZUL_prova.DXF` (31 KB, 4 peces). **NO EXISTEIX cap fitxer `.RUL`** ni **el fitxer
   Polypattern** enlloc del filesystem (cerca exhaustiva, B3). S1-T4 (reader RUL) i S1-T6
   (fixtures Polypattern) es queden sense material. **FLAG VERMELL — l'Agus els ha de pujar.**

2. **L'AMELIA real difereix del que el pla assumeix.** Té la **capçalera BUIDA** (`HEADER` i
   `TABLES` sense contingut): **no hi ha `$INSUNITS` ni `$MEASUREMENT`**, així que la
   normalització d'unitats *per capçalera* que descriu S1-T3 **és impossible** — cal deduir-les
   per geometria. I **no té capa 14 (cosit)** ni capa 6 (mirall): només porta línia de **tall**.
   La re-derivació "tall per offset del cosit" (S7-T1) **no té font de cosit** en aquest fitxer.

3. **Les tasques del motor JA EXISTEIXEN: S6-T4 sobra.** `pattern_digit`, `pattern_cad` i
   `scaling` són al seed canònic i a la BD, amb `eina='patro'`
   (`tasks/migrations/0025_seed_canonical_task_types.py:11,12,20`). El pla preveia sembrar-los;
   **no cal**. En canvi apareix un bloqueig que el pla no preveia: l'**allow-list
   `permisos["tasks"]`** — `open-task` retorna **403** si el code no és al perfil de l'usuari
   (`tasks/views_b.py:541-546`).

4. **El contracte del grading és nítid i el pinçament funciona.** `GradedSpec` és **una fila per
   `(grading_version, pom, size_label)`** amb **absolut** (`graded_value_cm`) **i delta signat**
   (`increment_applied_cm`, **+ = talla més gran**) — `fitting/models.py:163-195`. Donat un
   `grading_version_id` explícit, la lectura **és determinista i esquiva tots els forks de G6**
   (B7 §5.c). **Amb dues condicions dures:** la **talla base NO és inferible** del delta==0 (ve
   de `Model.base_size_label`), i **`aprovada` ≠ `is_active`** (3 de 4 versions aprovades reals
   **no** són l'activa) — amb **cap constraint** que impedeixi dues aprovades per SizeFitting.

5. **`GarmentTypeItemAsset` NO EXISTEIX** (mai ha existit al codi: `git log -S` → cap commit).
   La seva funció la compleix íntegrament **`ItemFitxer`** (`models_app/models.py:459-496`) +
   `GarmentTypeItem` (`tasks/models.py:286-329`) + el cicle `usar-al-model` → `derivat_de_item`.
   El `source_asset` FK de `PatternFile` ha d'apuntar a **`models_app.ItemFitxer`**.

6. **El pipeline de fitxers és reutilitzable gairebé sense fricció**: `.dxf` i `.rul` **ja són a
   la whitelist** d'upload (`services_fitxers.py:36-47`), l'storage per-tenant és automàtic, i la
   porta de descàrrega gated (X-Accel + token signat) està **viva a staging** (verificat al vhost
   que corre). El sostre real d'upload és **20 MiB** (codi), sota els 25M d'nginx.

---

## B1 — PIPELINE DE FITXERS (l'espina que el motor replica)

### B1.1 · Models i patró de versionat

**`ModelFitxer`** — `backend/fhort/models_app/models.py:328-450`. Camps rellevants per al calc:

| Camp | Definició | Línia |
|---|---|---|
| `model` | `FK(Model, CASCADE, related_name='fitxers')` | `models.py:368` |
| `nom_fitxer` | `CharField(255)` | `models.py:369` |
| `tipus` | `CharField(30, choices=TIPUS_CHOICES, default='ALTRES')` — **eix únic viu** | `models.py:371` |
| `categoria` | `CharField(20, choices)` — **DEPRECAT** ("ningú l'escriu ni el llegeix", `models.py:329-331`) | `models.py:370` |
| `versio` | `PositiveIntegerField(default=1)` | `models.py:372` |
| `is_current` | `BooleanField(default=True, db_index=True)` | `models.py:373-374` |
| `versio_anterior` | `FK('self', SET_NULL, related_name='versions_posteriors')` | `models.py:375-381` |
| `derivat_de_item` | `FK('models_app.ItemFitxer', SET_NULL, related_name='usos_a_models')` | `models.py:395-401` |
| `derivat_de_model` | `FK('self', SET_NULL, related_name='derivats')` | `models.py:412-418` |
| `generat_des_de` | `FK('self', SET_NULL, related_name='exports_generats')` — enllaç, **no** cadena | `models.py:385-391` |
| `mida_bytes` | `BigIntegerField()` — **obligatori, sense default** | `models.py:427` |
| `fitxer` | `FileField(upload_to='model_fitxers/%Y/%m/')` | `models.py:430` |
| `checksum` / `mimetype` / `origen` | sha256 · guessat · `ORIGEN_CHOICES` (`upload`, `ia_*`) | `models.py:441-443` |

`TIPUS_CHOICES` (`models.py:350-362`) **ja conté** `PATRO`, `ESCALAT`, `MARCADA`, `RUL`,
`SKETCH_SVG`. **Meta** (`models.py:445-447`): només verbose_names — **cap `ordering`, cap
`unique_together`, cap constraint**.

**`ItemFitxer`** — `models.py:459-496`: mirall reduït, ancorat a
`garment_type_item = FK('tasks.GarmentTypeItem', CASCADE, related_name='fitxers')`
(`models.py:471-472`), `upload_to = item_fitxer_upload_to` → `items/<gti_id>/<filename>`
(`models.py:453-456`). Reutilitza `ModelFitxer.TIPUS_CHOICES` (`models.py:474`). Camps
**deliberadament absents** (`models.py:466-469`): `categoria`, `url_extern`, `origen`,
`generat_des_de`, `accessible_portal`.

**Patró de versionat — font única:** `backend/fhort/models_app/services_fitxers.py:1-7`:
"en tota cadena hi ha EXACTAMENT UN registre amb `is_current=True`; `save_model_file` i
`save_item_file` són els únics llocs que toquen aquesta invariant".

`save_model_file(model, file, *, versio_anterior=None, tipus=None, origen='upload', nom=None)` —
`services_fitxers.py:89-135`, `@transaction.atomic` (`:89`):
1. calcula `checksum` sha256 per chunks (`:103`, `:70-79`), `mida` (`:104`), `mimetype` (`:105`);
2. **encadena**: si hi ha `versio_anterior` → `versio = versio_anterior.versio + 1` i **el `tipus`
   s'hereta** del predecessor si no s'especifica (`:107-111`); si no → `versio = 1`;
3. escriu bytes i fila: `fitxer.fitxer.save(nom, file, save=False)` + `fitxer.save()` (`:127-129`);
4. **apaga el cap anterior**: `versio_anterior.is_current = False` amb
   `save(update_fields=['is_current'])` (`services_fitxers.py:131-133`).

`save_item_file` (`:138-178`) és el mirall exacte sense `origen`; la decisió de **no** extreure un
helper genèric està raonada a `services_fitxers.py:142-146`.
`get_version_chain(fitxer)` (`:283-303`) recorre la cadena amunt i avall (duck-typing: serveix els
dos models).

> ⚠️ **Risc heretat (FET):** la invariant `is_current` viu **només al codi**, no a la BD (cap
> `unique_together` ni `UniqueConstraint` a `models.py:445-447` ni `:491-493`). Un escriptor que
> no passi per `save_*_file` la trenca en silenci. `get_version_chain` només segueix
> `versions_posteriors.first()` (`services_fitxers.py:298`) → si una cadena **bifurca**, en veu
> una sola branca. `PatternFile` calcaria aquest risc si copia el patró literalment.

### B1.2 · Views d'upload, permisos i `validate_upload`

- **`ModelFitxer`**: FBV `upload_file_view` — `models_app/views.py:1201-1259`, ruta
  `models/<int:model_id>/upload-fitxer/` (`models_app/urls.py:199`). `@api_view(['POST'])`,
  `@permission_classes([IsAuthenticated])`, `@parser_classes([MultiPartParser, FormParser])`
  (`views.py:1201-1203`). `UploadRejected` → **400** (`views.py:1224-1227`); resposta **201**
  (`:1251-1259`). El ViewSet **no** té create/update a propòsit: és
  `ReadOnlyModelViewSet + DestroyModelMixin` perquè el genèric **saltava la invariant**
  (`views.py:146-149`).
- **`ItemFitxer`**: `ItemFitxerViewSet.create` — `models_app/item_fitxer_views.py:57-89`
  (registrat a `urls.py:44`). **`create`/`destroy` exigeixen `CONFIGURE`**
  (`HasCapability`, `item_fitxer_views.py:40-50`); `list/retrieve/download` només
  `IsAuthenticated`; `download_signed` → `AllowAny`. El serializer és **tot read-only**
  (`serializers.py:71-79`).

**`validate_upload(file, nom=None)`** — `services_fitxers.py:54-67`:
- **`MAX_UPLOAD_BYTES = 20 * 1024 * 1024`** (**20 MiB**) — `services_fitxers.py:31`. Deliberadament
  **més estricte** que els 25M d'nginx (`:28-30`).
- **Whitelist per EXTENSIÓ, mai per mimetype** (`:33-35`: els formats de domini arriben com a
  `application/octet-stream`). `ALLOWED_UPLOAD_EXTENSIONS` (`:36-47`):
  **`.ftt .pdf .dxf .svg .rul .txt .png .jpg .jpeg .webp .gif .xlsx .xls`**.
- ⇒ **`.dxf` i `.rul` JA hi són: el motor no ha de tocar la whitelist.**

### B1.3 · Storage dels binaris

`STORAGES['default'] = 'django_tenants.files.storage.TenantFileSystemStorage'`
(`settings.py:184-191`), `MEDIA_ROOT = BASE_DIR/'media'` (`settings.py:169`),
`MULTITENANT_RELATIVE_MEDIA_ROOT = '%s'` (= `schema_name`, `settings.py:182`).
Path físic real: `MEDIA_ROOT/<schema>/model_fitxers/YYYY/MM/x.dxf`.

**FET clau** (`settings.py:176-178`): **`FileField.name` és relatiu al TENANT, no a `MEDIA_ROOT`**
— el prefix del schema viu a `location`, no al `name`. Corroborat a `models.py:454-455` i
`services_fitxers.py:271-273` (l'X-Accel reconstrueix el path amb `os.path.relpath(...path,
MEDIA_ROOT)`, que **sí** porta el prefix). Un `FileField` nou hereta l'storage tenant-aware
**sense configuració addicional** (`settings.py:180-181`).

### B1.4 · Descàrrega gated — com s'endolla un tipus nou

Font única de bytes: **`serve_fitxer(fitxer, *, as_attachment=True)`** — `services_fitxers.py:227-280`.
Serveix `ModelFitxer` i `ItemFitxer` per **duck-typing**; en PROD emet `X-Accel-Redirect:
/protected-media/<rel>` (`:273-275`) + `Content-Disposition` RFC 5987 (`:277-278`); en DEBUG,
`FileResponse` (`:268-269`).
**Contracte duck-type** que ha de complir un model nou: atributs `fitxer` (FileField),
`nom_fitxer`, `mimetype` (i opcionalment `url_extern`).

Dues portes: **`download/`** (gate per capçalera `Authorization`, `views.py:240-252`) i
**`download-signed/?token=`** (`TimestampSigner` via `signing.dumps/loads`, `AllowAny` +
`authentication_classes=[]`). Constants a `services_fitxers.py:20-26`:
`DOWNLOAD_SALT='model_fitxer_download'`, `ITEM_DOWNLOAD_SALT='item_fitxer_download'`,
**`DOWNLOAD_TTL = 900`** (15 min). **Dos salts distints a propòsit** (`:22-23`): el payload és
només l'id, i amb un sol salt un token de `ModelFitxer id=5` validaria a `ItemFitxer id=5`.

**Per endollar-hi `PatternFile` (llista tancada):** (a) un **salt propi** al costat dels dos de
`services_fitxers.py:24-25`; (b) `get_download_url` al serializer via `_signed_download_url(...,
ruta='pattern-files')` (`serializers.py:7-21`); (c) accions `download` + `download_signed` que
criden `serve_fitxer`; (d) `perform_destroy` → `delete_fitxer_bytes` (`services_fitxers.py:203-224`).
**nginx NO s'ha de tocar**: l'`alias` de `/protected-media/` cobreix tota l'arrel de media
(verificat viu, B5).

### B1.5 · Migracions 0054-0056 i el cicle de sembra item→model

- **`0054_itemfitxer.py`**: una sola `CreateModel(ItemFitxer)` (`:17-38`). Cap índex compost, cap
  unique.
- **`0055_modelfitxer_derivat_de_item.py`**: una sola `AddField` del FK a `ItemFitxer` (`:14-18`).
- **`0056_modelfitxer_derivat_de_model.py`**: una sola `AddField` del FK a self (`:14-18`).
- Les tres són **purament estructurals** (cap `RunPython`). **Aplicades al schema `fhort`**
  (SELECT a `django_migrations`: `0054_itemfitxer | 0055_modelfitxer_derivat_de_item |
  0056_modelfitxer_derivat_de_model` ✅).

**El cicle de sembra (el patró que la biblioteca GTI reutilitzarà), pas a pas** —
`POST /api/v1/item-fitxers/<id>/usar-al-model/` amb `{model_id}` — `item_fitxer_views.py:130-176`:
1. `origen = self.get_object()` (l'`ItemFitxer`); 400 si no té bytes (`:154-155`).
2. `model = get_object_or_404(Model, pk=model_id)` (`:160`).
3. **Còpia de bytes**: `origen.fitxer.open('rb')` → `save_model_file(model, origen.fitxer,
   tipus=origen.tipus, origen='upload', nom=origen.nom_fitxer)`, dins `try/finally` que tanca
   l'origen (`:165-170`).
4. `marcar_procedencia(nou, request.user, derivat_de_item=origen)` (`:173`) —
   `services_fitxers.py:181-200`: un sol UPDATE amb `update_fields`, **no toca `is_current`/`versio`**.
5. **201** amb `ModelFitxerSerializer` (`:175-176`).

**Els bytes es DUPLIQUEN físicament** (FET): `save_model_file` escriu un fitxer nou sota
`model_fitxers/%Y/%m/` (`models.py:430`), **no** sota `items/<gti_id>/`; no hi ha FileField
compartit ni symlink. Recalcula checksum/mida/mimetype sobre el contingut real
(`services_fitxers.py:103-105`). La còpia **arrenca cadena pròpia** (`versio=1`, `is_current=True`,
`versio_anterior=NULL`, `:111,120-121`) i **l'origen no es toca mai** (`models.py:392-394`).
Gate: **`IsAuthenticated`, NO `CONFIGURE`** — "l'escriptura va al MODEL, no al catàleg"
(`item_fitxer_views.py:45-47`).

> **Matís de contracte:** l'`origen` que es passa és `'upload'` (`item_fitxer_views.py:167`) —
> l'eix `ORIGEN_CHOICES` **no** codifica "importat": la procedència viu **exclusivament** a
> `derivat_de_item`.

**Veredicte B1: LLEST.** El patró és clar, la whitelist ja admet `.dxf`/`.rul`, l'storage i la
descàrrega gated s'hereten. Dos riscos heretats a decidir si es calquen (invariant `is_current`
sense constraint de BD; bifurcació de cadena).

---

## B2 — `GarmentTypeItemAsset`

### **NO EXISTEIX.** Ni com a model, ni com a codi, ni ha existit mai.

- `grep -rn "GarmentTypeItemAsset" .` → **8 hits, tots en 2 fitxers Markdown de planificació**
  (`MOTOR_DE_PATRONS_V2.md:38,68,168,191,235,376,408` i
  `PLA_IMPLEMENTACIO_MOTOR_PATRONS.md:126`). **Cap `.py`, cap migració, cap `.js`.**
- `git log --all -S "GarmentTypeItemAsset"` → **cap commit**. El nom no ha existit mai al codi
  versionat.
- El document de disseny del 29/06 que el cita **no és al repo** (ni a `docs/`, ni a
  `docs/diagnosis/`, ni a `arxiu/`): viu fora del repositori.

### `ItemFitxer` **ÉS** la materialització de facto — demostració

1. El model d'item existeix: **`GarmentTypeItem`** — `backend/fhort/tasks/models.py:286-329`
   (`unique_together = [('garment_type','code')]`, `:325-329`).
2. Els fitxers hi pengen directament: `ItemFitxer.garment_type_item` FK CASCADE,
   `related_name='fitxers'` (`models_app/models.py:471-472`).
3. És literalment "la biblioteca d'actius per item": docstring d'`ItemFitxer`
   (`models.py:460`): *"Fitxer del **CATÀLEG**, ancorat a un GarmentTypeItem (S03b · P4)"*. Els
   tipus disponibles ja inclouen `PATRO`, `ESCALAT`, `MARCADA`, `RUL`, `SKETCH_SVG`
   (`models.py:350-362`, heretats a `:474`) → **"sketch base + DXF de patró" ja hi caben sense
   tocar res**.
4. El patró **"catàleg sembra, Model posseeix" ja està implementat**: `usar_al_model`
   (`item_fitxer_views.py:130-176`) + `derivat_de_item` (`models.py:395-401`, migració 0055). El
   comentari del model usa el llenguatge exacte del disseny (`models.py:392-394`): *"és una
   **CÒPIA** importada… **no és una edició compartida** — l'origen no es toca mai"*.

**Estat de les dades (SELECT, schema `fhort`):** `models_app_itemfitxer` → **0 files**;
`ModelFitxer` amb `derivat_de_item` → **0**; cap `ModelFitxer` de tipus `PATRO`/`RUL`/`ESCALAT`.
⇒ **la infraestructura d'item existeix i està desplegada, però és buida**: la biblioteca GTI és un
esquema sense contingut.

**Veredicte B2: RESOLT.** `GarmentTypeItemAsset` és nomenclatura de disseny sense codi.
**Correcció per a S3-T1:** el `source_asset` FK de `PatternFile` ha d'apuntar a
**`models_app.ItemFitxer`**, i el FK d'item del XOR a **`tasks.GarmentTypeItem`**.

---

## B3 — MATERIAL REAL 🔴 (bloquejant per a S1)

**Cerca exhaustiva** a tot el filesystem (`find /` amb poda de `node_modules`/`venv`/`.git`;
un sol filesystem real, `/dev/sda1` — `df -hT`), per extensió (`*.dxf`, `*.rul`) i per nom
(`*amelia*`, `*poly*pattern*`, `*tuka*`).

### L'únic fitxer que existeix

`backend/media/fhort/import_sessions/2026/06/AMELIA_AZUL_prova.DXF`

| Propietat | Valor |
|---|---|
| Mida | **31 344 bytes** (31 KB) · 6 062 línies |
| md5 | `2ae0006e003ebe17326187d79bb587d5` |
| Propietari / data | `www-data:www-data` · 2026-06-23 |
| Ubicació lògica | `media/<schema fhort>/import_sessions/2026/06/` → és el `FileField` d'un **`ImportSession`** (`models_app/models.py:516`, `upload_to='import_sessions/%Y/%m/'`), **no** un fixture |
| Sota git? | **NO** — `backend/media/` és a `.gitignore:1` |

**Estructura (lectura pura):** 4 seccions — `HEADER`, `TABLES`, `BLOCKS`, `ENTITIES` — amb
**`HEADER` i `TABLES` BUIDES** (línies 1-12 del fitxer: `SECTION/HEADER/ENDSEC`,
`SECTION/TABLES/ENDSEC`). **4 `BLOCK`** = 4 peces + 4 `INSERT` a `ENTITIES`.

**Peces i geometria (bounding box calculat sobre els vèrtexs):**

| Peça | Vèrtexs | W × H (unitats natives) | Si mm |
|---|---|---|---|
| `BACK` | 65 | 524.7 × 695.0 | **52.5 × 69.5 cm** |
| `FRONT` | 109 | 542.1 × 704.1 | **54.2 × 70.4 cm** |
| `BACK_LINI` | 25 | 474.7 × 692.0 | **47.5 × 69.2 cm** |
| `FRONT_LINI` | 63 | 492.0 × 695.7 | **49.2 × 69.6 cm** |

**Capes presents** (recompte d'entitats): `3` (curve) 192 · `1` (tall) 171 · `8` (internes) 160 ·
`2` (turn) 132 · `4` (piquets) 16 · `7` (grain) 4 · **`15`** 4.
**Tipus d'entitat:** 266 `POINT` · 262 `VERTEX` · 123 `TEXT` · 16 `POLYLINE` · 4 `LINE` ·
4 `INSERT`. **Cap `ARC`, `SPLINE`, `ELLIPSE` ni `LWPOLYLINE`.**

**Metadades per peça (TEXT de capa 1):** `Piece Name: <nom>` · `Size: M` · `Quantity: 1,0` ·
`Material: SHL|LINING`. Capa 4: `TEXT '# 1'` (numeració de piquets). **Capa 15: `TEXT 'BROWNEI RAM
NARESH'`** (×4, una per peça) — capa **no prevista** al pla.

### Les quatre troballes que canvien S1

1. 🔴 **NO EXISTEIX cap fitxer `.RUL`** al servidor. **S1-T4 (reader RUL) no té material**, i el
   fitxer d'AMELIA conté **una sola talla** (`Size: M` a les 4 peces) → **cap niada, cap grading**
   dins el DXF. *(Coherent amb la Q6 oberta del V2 §4.4-E3: "cap RUL real poblat verificat encara".)*
2. 🔴 **NO EXISTEIX el fitxer Polypattern.** S1-T6 (fixtures), S2-T1 (perfil `polypattern`) i el
   round-trip de S2 es queden **sense la segona font d'empremta**.
3. 🟠 **`HEADER` buida → NO hi ha `$INSUNITS` ni `$MEASUREMENT`.** La normalització d'unitats
   *per capçalera* que descriu S1-T3 **és impossible en aquest fitxer**. L'evidència dimensional
   (una esquena de talla M de 52.5 × 69.5 cm és plausible; 5.2 × 7.0 cm és absurd) indica
   **mil·límetres, factor 1.0**, però **es dedueix per geometria, no es llegeix**.
   `TABLES` buida implica també que **no hi ha taula de LAYERS**: els noms de capa són numèrics purs.
4. 🟠 **NO hi ha capa 14 (línia de cosit)** ni capa 6 (mirall). AMELIA porta **només línia de
   tall**. Això toca S7-T1, que preveu "re-derivació (tall per **offset del cosit**)": **no hi ha
   cosit d'on derivar** — el marge de costura no viatja al fitxer.
5. 🟡 **Separador decimal COMA dins els TEXT** (`Quantity: 1,0`) **en un fitxer Tuka**, mentre les
   **coordenades usen PUNT** (`613.500`). El pla atribuïa la coma a Polypattern (§S1-T3): és un
   matís d'empremta **per camp**, no per fitxer.

**Veredicte B3: 🔴 BLOQUEJANT.** S1 pot arrencar el reader AAMA amb AMELIA (que és material real i
suficient per a T1-T3), però **T4 (RUL) i la meitat de T6 (fixtures) no tenen material**, i S2
(round-trip Polypattern) tampoc. **L'Agus ha de pujar el `.RUL` d'AMELIA i el fitxer Polypattern
abans de S1** (o acceptar explícitament que S1 tanca sense ells i S2 queda a mitges).

💡 **PROPOSTA (a validar):** en pujar-los, copiar-los al repo com a **fixtures versionats**
(p.ex. `backend/fhort/patterns/tests/fixtures/`), perquè avui l'únic exemplar viu a
`backend/media/`, que **no és a git** (`.gitignore:1`) i es perdria en qualsevol reconstrucció de
l'entorn.

---

## B4 — FITXA DEL MODEL (on viurà el tab Patró)

**`frontend/src/pages/ModelSheet.jsx`** (1 758 línies). Els tabs es declaren com a **array literal
de strings** + mapa de labels — **no** hi ha registre de config ni switch:

- `ModelSheet.jsx:25` — `const TABS = ['Dashboard','Resum','Mesures','Escalat','Fitxa tècnica',
  'Fitxers',"Registre d'activitat",'Tasques']`
- `ModelSheet.jsx:27-36` — `TAB_LABELS` (id → clau i18n).
- **La clau de lògica és el string català literal** (`activeTab === 'Mesures'`), no un slug —
  explicitat a `ModelSheet.jsx:26`.
- Render de la banda: `ModelSheet.jsx:390-413` (`TABS.map`). Render del cos: **condicionals JSX
  encadenats**, `ModelSheet.jsx:423-585`.
- *(Curiositat que ho prova: `Anàlisi IA` té branca de render (`:583`) però **no és a `TABS`** →
  mai s'activa. La porta d'entrada real d'un tab és **ser dins `TABS`**.)*

**Mecanisme exacte per afegir el tab "Patró" (4 punts + 1 opcional):**
1. `ModelSheet.jsx:25` — afegir `'Patró'` a `TABS` (la posició = ordre visual).
2. `ModelSheet.jsx:27-36` — `'Patró': 'model_sheet.tab_pattern'` a `TAB_LABELS` (si falta,
   `t(undefined)` → label buit).
3. `ModelSheet.jsx:423-585` — una línia condicional:
   `{activeTab === 'Patró' && <PatternTab modelId={parseInt(id)} model={model} />}`.
4. `frontend/src/i18n/{ca,en,es}.json` — clau `model_sheet.tab_pattern` als **tres** (al costat de
   `ca.json:590-595`). *(Els labels de tab estan repartits en dos namespaces — `model_sheet.*` i
   `model.tabs.*` — per deute històric; el majoritari i actiu és `model_sheet.*`.)*
5. *(Opcional)* import estàtic a la capçalera `ModelSheet.jsx:1-17`.

**Rutes i deep-link:** ruta plana `models/:id` (`App.jsx:244`); **els tabs són estat local**
seleccionat per **query param `?tab=`** (`ModelSheet.jsx:94,97-105`), llegit **només al muntatge**
(`useState` inicial, `:107`) i filtrat per **`TABS.includes(tabParam)`** → **un `?tab=Patró` no
funcionarà fins que 'Patró' sigui a `TABS`**. El deep-link és **unidireccional**: clicar un tab
**no** canvia la URL (no hi ha `setSearchParams` enlloc del fitxer).
Patró canònic tab+tasca: **`?tab=Mesures&task_id=<id>`** — emès per `App.jsx:68,78` i consumit a
`ModelSheet.jsx:265-275` (`autoTaskRef`, un sol cop: fixa `editTaskId` i entra en mode treball
**sense encunyar una tasca nova**). Rutes dedicades que premunten tab:
`ModelSheet({defaultTab, autoEdit})` (`ModelSheet.jsx:87`; usos a `App.jsx:250,252`).

**Lazy-loading:** els tabs **no** són lazy (imports estàtics, `ModelSheet.jsx:1-17`; cap
`React.lazy`/`Suspense` al fitxer). El lazy viu una capa amunt: `App.jsx:42`
(`lazy(() => import('./pages/ModelSheet'))`).

**Com arriba el model al tab:** no hi ha context ni store — **props**. El pare carrega amb
`Promise.all` (`ModelSheet.jsx:138-160`) i **la majoria de tabs només reben `modelId` i refan el
seu propi fetch** (`TabFiles` `:581`, `TechSheetTab` `:582`, `RegistreActivitatTab` `:584`);
`TabSummary` rep l'objecte sencer (`:449-454`). ⇒ **convenció per a Patró:**
`modelId={parseInt(id)}` (+ `model={model}` si cal metadata) amb fetch propi.

**Bonus S5 (només ubicació):** `frontend/src/pages/TechSheetEditor.jsx` (4 480 línies, monòlit;
Konva a `:4-5`), amb mòduls extrets a `frontend/src/pages/ftt/`: `history.js`, `snapping.js`,
`paperbool.js`. Zoom/pan: `MM_TO_PX` `:38`, `clampZoom` `:143`, `setZoomClamped` `:1463-1465`,
`fitZoomToViewport` `:1466-1471`.

**Veredicte B4: LLEST.** Quatre punts d'edició, tots al mateix fitxer + i18n. Cap arquitectura nova.

---

## B5 — LÍMITS D'UPLOAD

### La cicatriu és real — i està al fitxer que **no** corre

**`/etc/nginx/sites-enabled/ftt-staging` NO és un symlink: és un fitxer regular**
(`-rw-r--r-- root root 2511`, 9 jul), i **divergeix** de `sites-available/ftt-staging`:

| | `sites-ENABLED` (el que **corre**) | `sites-available` (el que un editaria) |
|---|---|---|
| `client_max_body_size 25M` | **línia 3** → dins el `server{}` del **443** ✅ | **línia 65** → dins el `server{}` del **redirect-80** ❌ (inútil) |
| `location /protected-media/` (internal, `auth_basic off`) | **línies 55-61** ✅ **VIU** | **absent** ❌ |

`nginx -t` → OK. El bloc `server` de 443 comença a `:1` (`listen 443 ssl` a `:62`); el de redirect
a `:69` (`listen 80` a `:74`).

⇒ **FET 1:** el límit real de pujada a staging és **25 MB** i el **gate de descàrrega X-Accel està
viu** (això tanca el "Gate 2 🔴" que `docs/diagnosis/PREDEPLOY_2026-07-12.md:231` donava per obert).
⇒ **FET 2 (risc operatiu):** `sites-available` està **desfasat i conté la cicatriu**. Qui l'editi i
en refaci el symlink **trencarà alhora el límit de 25M i les descàrregues gated**.

### Django / DRF

- **NO EXISTEIX cap override** de `DATA_UPLOAD_MAX_MEMORY_SIZE` ni `FILE_UPLOAD_MAX_MEMORY_SIZE`
  a `settings.py` (grep buit) → valen els defaults de Django (2.5 MB, que és el **llindar
  memòria→fitxer temporal**, no un límit de mida d'upload).
- `REST_FRAMEWORK` (`settings.py:203-219`): JWT + Session, `IsAuthenticated` per defecte,
  paginació `DefaultPagination` (PAGE_SIZE 25). **Cap setting de mida.**
- **El límit dur efectiu de l'aplicació és `MAX_UPLOAD_BYTES = 20 MiB`** (`services_fitxers.py:31`),
  per sota dels 25M d'nginx.

**Cadena real:** nginx **25 MB** → Django (sense límit propi) → `validate_upload` **20 MiB**.
AMELIA fa 31 KB: **folgat per a la traçadora**.

**Veredicte B5: LLEST**, amb un avís operatiu (divergència `sites-available` ↔ `sites-enabled`).
💡 **PROPOSTA (a validar):** si un DXF de niada real (moltes talles) superés els 20 MiB, el punt
únic a apujar és `services_fitxers.py:31` **i** el `client_max_body_size` del **bloc 443** de
`sites-enabled`.

---

## B6 — RENDER SVG

### Estat verificat de les dependències

**matplotlib NO és a `requirements.lock`. Tampoc `ezdxf`, `shapely`, `numpy` ni `pyclipper`.**
I **cap de les cinc està instal·lada al venv** (`backend/venv/bin/python -c "importlib.util.find_spec"`
→ **ABSENT** × 5). El venv només té, del nostre interès: `pillow 12.2.0`, `CairoSVG 2.9.0`,
`cairocffi 1.7.1`.

> ⚠️ **Desviació respecte del que el pla assumeix:** `MOTOR_DE_PATRONS_V2.md:116` marca shapely
> com a *"✅ Verificat executant aquí"*. **No ho està al venv de staging.** S1 haurà d'instal·lar
> ezdxf (i S7 shapely) com a **acció de deploy del CTO**, no com a pas silenciós del sprint.

**Nota transversal:** hi ha **DOS `requirements.lock` divergents** — l'arrel
(`requirements.lock`, amb `cairosvg`/`reportlab`, coherent amb `backend/requirements.txt`) i
`backend/requirements.lock` (**antic**: porta `celery`, `redis`, `pandas`, `PyMuPDF`, `numpy==2.4.6`
— res d'això és a `requirements.txt`). Cal saber quin mana abans d'afegir-hi res.

### Cost real d'ezdxf i de l'add-on `drawing` (PyPI, ezdxf 1.4.4)

- **ezdxf core (obligatori, S1):** `pyparsing`, `typing_extensions`, **`numpy`**, `fonttools`.
  Cost inevitable i acceptable — és el nucli del parser.
- **Add-on `drawing` → extra `draw`:** `matplotlib` **+ PySide6 + PyMuPDF + Pillow**. L'extra
  oficial **arrossega Qt (PySide6) al servidor**. Encara que s'instal·lés només `matplotlib` (el
  backend matplotlib de l'add-on no necessita Qt), afegeix igualment `contourpy`, `cycler`,
  `kiwisolver`, `packaging`, `python-dateutil` — una cua de ~6 paquets per **dibuixar línies rectes**.

### Evidència que decideix: el fitxer real no necessita un motor de render

L'AMELIA conté **només** `POLYLINE`/`VERTEX`, `LINE`, `POINT` i `TEXT` (B3). **Zero `ARC`, `SPLINE`,
`ELLIPSE`.** Les "corbes" del patró són **polilínies de punts densos** (192 punts de capa 3 =
curve), no corbes paramètriques. ⇒ **el render és una traducció directa punt→`<path d="M…L…">`.**

💡 **PROPOSTA (a validar; la decisió es pren a S3):** **render SVG propi** des del model geomètric
intern, **no** matplotlib.
- **A favor:** ~80 línies de codi; zero dependències noves; l'SVG surt del **nostre** model (no del
  DXF cru), que és exactament el que S4/S5 han de mostrar; control total de la paleta de document
  (llei del pla: "l'SVG servidor és DOCUMENT, paleta pròpia fixa"); i el projecte **ja té precedent
  de generar documents** sense matplotlib (`reportlab` per a PDF, `cairosvg` per al logo).
- **En contra:** perdem el render "gratis" d'entitats exòtiques (ARC/SPLINE) si un CAD futur les
  emet — però llavors **el parser ja les hauria de suportar igualment**, i el render en surt.
- **matplotlib només es justificaria** si volguéssim renderitzar el **DXF cru** sense passar pel
  nostre model — cosa que contradiu l'arquitectura hexagonal del pla (engine pur → dataclasses).

**Veredicte B6: RECOMANACIÓ = render propi.** ezdxf **sí** (nucli, S1); matplotlib **no**.

---

## B7 — CONTRACTE DEL GRADING (el port `GradingSource`)

### B7.1 · `GradingVersion` — `backend/fhort/fitting/models.py:62-95`

**No penja del Model: penja de `SizeFitting`.**
`size_fitting = FK(SizeFitting, CASCADE, related_name='grading_versions')` (`:63`); el Model
s'assoleix per `size_fitting.model` (`fitting/models.py:23`). **NO EXISTEIX cap FK directa a Model.**

Camps: `nom` (`:64`), **`aprovada = BooleanField(default=False)`** (`:65`), `data` (`:66`),
`creat_per` (`:67-72`), `notes` (`:73`), `version_number` (`:76`), **`is_active`** (`:77`),
`aprovada_per` (`:81-86`), `data_aprovacio` (`:87`).
**Meta** (`:89-92`): `ordering=['size_fitting','-data']`. **CAP `unique_together`, CAP constraint**
(BD: només PK, 3 índexs de FK i `CHECK (version_number >= 0)`).

🔴 **`aprovada` ≠ `is_active` — són ortogonals.** Dades reals al schema `fhort`: **21**
GradingVersion, **4 `aprovada=True`**, 4 `is_active=True`, i **només 1 fila té les dues**.
⇒ **3 de les 4 versions aprovades NO són l'activa** (són segellades i després superades).
"La versió aprovada" i "la versió que serveix la UI" **són entitats diferents avui**.

🔴 **Es poden acumular múltiples aprovades per SizeFitting.** `seal_model_grading`
(`fitting/services.py:596-599`) marca `aprovada=True` **sense desmarcar-ne cap d'anterior**;
`bump_grading_version_and_generate` (`pom/services.py:552`) desactiva les actives però
**explícitament no toca `aprovada`** (`pom/services.py:520`). Avui cap SizeFitting en té 2 (query
`HAVING count(*) FILTER (WHERE aprovada) > 1` → 0 files), però **res no ho impedeix**.
⇒ **Un port que faci `GradingVersion.objects.get(size_fitting=sf, aprovada=True)` petarà amb
`MultipleObjectsReturned`** el dia que se segelli dos cops el mateix SizeFitting.

### B7.2 · `GradedSpec` — FORMA EXACTA — `fitting/models.py:163-195`

**Una fila per `(grading_version, pom, size_label)`.** **NO EXISTEIX cap JSON `values_by_size`.**

| Camp | Tipus | Notes |
|---|---|---|
| `grading_version` | `FK(GradingVersion, CASCADE, related_name='graded_specs')` (`:172-174`) | |
| `pom` | `FK('pom.POMMaster', PROTECT, related_name='graded_specs')` (`:175`) | FK al **master**, no al codi |
| `size_label` | `CharField(20)` (`:176`) | **STRING lliure, NO FK a Size**; ve de fer split de `model.size_run_model` (`pom/services.py:52`) |
| `graded_value_cm` | `FloatField()` (`:177`) | **VALOR ABSOLUT en cm**, arrodonit a 2 decimals (`pom/services.py:114`) |
| `increment_applied_cm` | `FloatField(default=0.0)` (`:179`) | **DELTA** vs la talla base |
| `grading_type_applied` | `CharField(20)` (`:178`) | `LINEAR/STEP/FIXED/ZERO/EXCEPTION` (`:165-171`) — petja de la regla aplicada |
| `is_active` | `BooleanField(default=True)` (`:180`) | tots els lectors hi filtren |
| `generated_from_version` | `IntegerField(null)` (`:186`) | `= model.measurements_version` en generar; detector de *stale* **no implementat** (`:183-185`) |

**Meta** (`:188-192`): **`unique_together = [('grading_version','pom','size_label')]`** — **existeix
també a BD** (`fitting_gradedspec_grading_version_id_pom_i_47a6101c_uniq`).

**SIGNE del delta** — `pom/services.py:115`: `increment = round(graded_val - base_val, 2)`
⇒ **positiu = talla més gran**. Comprovat amb dades reals (gv 69, pom 273, base `L`):
`XS = 55.1 / −6` · `M = 59.1 / −2` · `L = 61.1 / 0` · `XL = 63.1 / +2` · `3XL = 68.1 / +7`.

🔴 **La TALLA BASE no és identificable des de `GradedSpec`.** La fila de la base **no té cap flag**;
només té `increment_applied_cm = 0.0` **per coincidència aritmètica** — i **un POM amb regla `ZERO`
té increment 0 a TOTES les talles**. ⇒ **inferir la base per `increment == 0` és incorrecte.**
La base viu al **Model**: `Model.base_size_label` (`models_app/models.py:268-270`) i l'ordre de
talles a `Model.size_run_model` (`:264`); el motor les resol així a `pom/services.py:53-60`.

🟠 **La matriu POM×talla POT tenir forats**: les cel·les amb `graded_val is None` (STEP invàlid)
**se salten** i no generen fila (`pom/services.py:110-112`). I `generate_graded_specs` fa **upsert
pur, sense esborrar** (`_upsert_graded_spec`, `:685-711`) → poden quedar files **òrfenes** si el
size run s'encongeix.

### B7.3 · `generate_graded_specs` (només llegit — zona intocable)

`pom/services.py:18` → `def generate_graded_specs(size_fitting_id: int) -> int:` — rep **només**
l'id del SizeFitting; deriva model, regles i base measurements; escriu `GradedSpec` per upsert i
posa `SizeFitting.estat='TallesGenerades'` (`:129-131`); **retorna el nombre de specs**. Bessó pur
sense persistència: `preview_graded_specs(model, base_values, warnings)` (`pom/services.py:142`).

### B7.4 · Pseudo-dataclass del port (transcripció del contracte)

```python
# patterns/engine/ports.py — GradingSource (contracte, NO ORM)
# Entrada: grading_version_id EXPLÍCIT (guard dur: aprovada=True o error).

@dataclass(frozen=True)
class GradedPOMDelta:
    pom_id: int              # fitting_gradedspec.pom_id → pom.POMMaster (PK, NO el codi)
    pom_code: str            # llegible: POMMaster.pom_code / codi_client (fitting/graded_spec_views.py:57-58)
    size_label: str          # STRING lliure (NO FK). Ve de Model.size_run_model
    value_cm: float          # graded_value_cm — ABSOLUT en cm
    delta_cm: float          # increment_applied_cm — DELTA vs base. + = talla MÉS GRAN
    rule_applied: str        # LINEAR | STEP | FIXED | ZERO | EXCEPTION

@dataclass(frozen=True)
class GradingSnapshot:
    grading_version_id: int
    approved: bool           # GradingVersion.aprovada — el port EXIGEIX True
    # ── context OBLIGATORI: NO és derivable de GradedSpec, ve del Model ──
    base_size_label: str     # Model.base_size_label (models_app/models.py:268-270)
    size_run: list[str]      # Model.size_run_model, ORDENAT (models_app/models.py:264)
    # ── la matriu (pot tenir FORATS: STEP invàlid no genera fila) ──
    deltas: list[GradedPOMDelta]

class GradingSource(Protocol):
    def snapshot(self, grading_version_id: int) -> GradingSnapshot: ...
```

**Camí de resolució del context (únic i sense fork, però s'ha de recórrer explícitament):**
`GradingVersion.size_fitting.model` (`fitting/models.py:63` → `:23`).

### B7.5 · Ambigüitats dual-path G6 (enumerades, NO resoltes)

**Forks d'ESCRIPTURA** (dins del motor, ja congelats a la fila un cop escrita):
precedència **`ModelGradingOverride` (abast model) > `GradingException` (abast rule set) > regla >
FIXED**, `pom/services.py:92-108`; i **un quart fork** a `_load_grading_rules`
(`pom/services.py:411-421`): prefereix **`ModelGradingRule`** (resident al model) i **només si el
model no en té cap** recau a `GradingRule` del `GradingRuleSet` extern. Això és literalment "quin
ruleset mana". *(Referenciat com a dual-path a `docs/diagnosis/DIAGNOSI_MOTOR_FRONTERES.md:126`
i `:159-161`; frontera G1↔G6 a `DECISIONS.md:204-207`.)*

**Forks de LECTURA** — **quatre criteris diferents en producció** per triar la versió des d'un
`sf_id`/`model_id`:
1. `vigent_grading_version(sf)` — `is_active` prioritari, desempat `-version_number`
   (`fitting/services.py:557-577`).
2. `_active_grading_version(sf)` — **estrictament** `is_active=True` (`fitting/services.py:546-554`).
3. `filter(size_fitting=sf, is_active=True).last()` — **`.last()` sobre l'ordering `-data`**, no per
   `version_number` (`pom/services.py:475-477`, `pom/grading_views.py:71-73`) → **criteri diferent
   del 2**.
4. `order_by('-data','-id').first()` **ignorant `is_active`** (`pom/s6_views.py:137-139`) → pot
   servir una versió **desactivada**.
5. `fitting/serializers.py:217-221` llegeix **tots** els GradedSpec del SizeFitting **sense filtrar
   versió** → **barreja versions**.
6. Fork previ a nivell de Model: `_resolve_working_size_fitting(model)`
   (`fitting/services.py:534-543`) tria "el SizeFitting de treball" arbitràriament si n'hi ha 2+
   (permès per `unique_together ('model','numero')`, `fitting/models.py:56`; avui **0 models** en
   tenen 2).
7. **Cap lector de GradedSpec filtra per `aprovada`** (v. B7.1).

### **CONFIRMAT: el pinçament per `grading_version_id` explícit els esquiva tots** — amb 2 condicions

Donat un `grading_version_id`, `GradedSpec.objects.filter(grading_version_id=X, is_active=True)`
retorna un **conjunt tancat i determinista**, amb unique `(grading_version, pom, size_label)`
**garantit a BD**. Els forks d'escriptura ja estan **congelats** dins de cada fila
(`grading_type_applied` en deixa la petja) i els forks de lectura són **de selecció de versió**,
que el paràmetre explícit **curtcircuita**.

**Condicions (a complir a S7-T2):**
- **C1** — el **context** (`base_size_label`, `size_run`) **NO** és determinista des del
  `grading_version_id` sol: cal recórrer `grading_version.size_fitting.model` explícitament.
  **Mai inferir la base per `delta == 0`.**
- **C2** — el guard `aprovada=True` ha de ser **`filter(pk=explicit)` + comprovació del flag**,
  **mai `get(aprovada=True)`** (múltiples aprovades són estructuralment possibles).

**Veredicte B7: LLEST i el pinçament es confirma.** El contracte és transcrivible tal com queda
sobre; G6 no s'ha de tocar ni es trepitja.

---

## B8 — TASKTYPES `pattern_*`

### **Els tres EXISTEIXEN. S6-T4 (seed) és INNECESSARI.**

Font única del catàleg: la migració de dades
**`backend/fhort/tasks/migrations/0025_seed_canonical_task_types.py`** (llista `CATALEG`, `:8-23`).
**NO EXISTEIX** cap fixture ni cap command `seed_task_types`. `bootstrap_tenant.py:25` ho confirma:
*"`TaskType` NO es copia (neix sol)"*.

Els codes del motor, **al seed i a la BD** (SELECT a `fhort.tasks_tasktype`, 14 files, coincidència
exacta 14/14):

| pk | code | name | eina | mode | ModelTasks vives |
|---|---|---|---|---|---|
| 8 | **`pattern_digit`** | Patró digitalització | `patro` | `digitalitzar` | **0** |
| 9 | **`pattern_cad`** | Patró CAD | `patro` | `disseny_base` | **16** |
| 11 | **`scaling`** | Escalat CAD | `patro` | `escalat` | **0** |
| 19 | `pattern_review` | Revisió de patró CAD | `patro` | `revisio` | 0 |
| 12 | `marking` | Marcada | `patro` | `marcada` | 0 |
| 21 | `grading` | Escalat | `escalat` | `propagacio` | 18 |

*(El pla no coneixia `pattern_review` ni `marking`: també són slots del motor, eina `patro`.)*
Els **pks són desordenats (8-23, amb forats)** — prova que el catàleg s'ha construït per `code` i
que **mai s'ha de referenciar per pk**.

🟠 **`scaling` és ambigu amb `grading`**: el command
`tasks/management/commands/retype_scaling_to_grading.py:1-15` va **re-tipar totes les ModelTask de
`scaling` → `grading`** perquè *"estava mal cablejat"* (l'eina `/escalat` és la regla de gradació,
no el CAD). `WorkPlan.jsx:35` ho documenta: *"scaling ('Escalat CAD' = aplicar al patró) és tasca
diferent, eina futura → null"*. ⇒ **`scaling` és el slot reservat del motor**, avui buit.

### Compliment de G9 — **VERIFICAT ✅**

- **Cap escriptor tenant-side:** `TaskTypeViewSet` és **`ReadOnlyModelViewSet`**
  (`tasks/views_b.py:30-40`, docstring: *"POST/PUT/PATCH/DELETE retorna 405 per a tothom, inclòs
  admin"*). **NO EXISTEIX** serializer d'escriptura (`serializers_b.py:7-12`, que cita G9
  literalment) ni registre a l'admin (`tasks/admin.py:1-3`, buit). Al frontend,
  `endpoints.js:216`: *"create/update/remove retirats (G8-2)"*.
- **Referència per slug:** `open-task` resol `TaskType.objects.get(code=code, active=True)`
  (`views_b.py:530`); `bootstrap_tenant.py:25-27` re-resol per `code` en copiar entre schemes
  (*"llei G9: la referència canònica és el slug, mai el pk"*).
- **Seed idempotent:** `update_or_create(code=code, defaults=...)` (`0025:29-35`), reverse noop
  (`:38-40`). *(Matís: en ser una migració, per re-sembrar cal una migració nova amb el mateix
  patró — no hi ha command.)*
- **Excepció que el matisa (no el viola):** `define_model_tasks_view` (`views_b.py:329-338`) accepta
  `{"task_type_ids": [...]}` — **pks sobre el fil**. Un sprint nou **no hi hauria de basar res**.

### Mecanisme frontend per obrir/pausar un `ModelTask` (S6-T5 el reutilitza tal qual)

**Obrir/reprendre:** `POST /api/v1/models/<model_id>/open-task/` amb **`{"code": "<slug>"}`**
(**el code, no el pk**) — ruta `tasks/urls.py:59`, endpoint `tasks/views_b.py:509-598`
(`@permission_classes([_ExecuteTasks])`). És **idempotent** ("porta-menú"): **crea-si-falta** la
ModelTask `(model, task_type, origen='prevista')` (`:548-557`) i la posa **`InProgress`** via
`transition_task` (obre `TimerEntrada`, auto-assigna, **pausa l'altra InProgress del mateix
tècnic**). Resposta **200**: `{task_id, code, created, status, missing_config}` (`:596-598`).
Client: `frontend/src/api/endpoints.js:49-50` → `models.openTask(id, code, fittingSessionId=null)`.

**Pausar/tancar:** `POST /api/v1/model-task-items/<pk>/transition/` amb
`{"to_status": "Paused"|"InProgress"|"Done"}` (`tasks/urls.py:55`, `views_b.py:426-452`).
⚠️ `Paused→Paused` **no** és a `ALLOWED` → **400**; el front s'hi defensa amb un ref d'un sol ús
(`ModelSheet.jsx:197-205`, `pauseActiveTask`).

**El patró exacte a calcar** (edició inline amb tasca) — `ModelSheet.jsx:207-221`:
`enterEdit(tab, code)` → `openTask(code)` → desa `res.data.task_id` a `editTaskId` **i a
`activeTaskRef`** → commuta el tab a mode edició **sense canviar de ruta**; `exitEdit`
(`:222-227`) → `pauseActiveTask()`.

🔴 **BLOQUEIG NOU, no previst al pla — l'allow-list `permisos["tasks"]`:** `open-task` retorna
**403 `{"code": "task_type_not_allowed"}`** si el code **no és a `get_allowed_task_types(user)`**
(`views_b.py:541-546`), que llegeix `UserProfile.permisos["tasks"]` (llista de **codes**), amb
bypass total només per a **admin** (`accounts/capabilities.py:57-71`).
⇒ **`pattern_digit`/`pattern_cad` no seran executables per cap tècnic** fins que els codes
s'afegeixin a `permisos["tasks"]` dels perfils. **És dada, no codi** — acció del CTO a S6.

🟠 **`toolRoute` està duplicat a DOS llocs** (conscientment): `WorkPlan.jsx:24-37` i
`TaskTree.jsx:38-47`. Per donar **eina** a un code (p.ex. `pattern_cad`) cal editar **les dues**
funcions + els mapes `TASK_ICON` (`WorkPlan.jsx:53-56`, `TaskTree.jsx:30-34`) + les 3 claus i18n
`tasktype.<code>` (`{ca,en,es}.json:2059-2074`). Avui **cap dels codes `patro` té ruta**: la tasca
s'obre, el rellotge corre, però **no es navega enlloc** (`TaskTree.jsx:98-105` ja n'emet un
`console.warn` d'auditoria).

**Veredicte B8: LLEST — i el pla s'alleugereix.** S6-T4 desapareix; a canvi apareixen dues accions
petites: allow-list de perfils (dada) i `toolRoute` × 2 (codi).

---

## B9 — CONVENCIONS D'APP (motlle `commerce/`)

**Estructura de `backend/fhort/commerce/`:** `__init__.py` · `apps.py` (`CommerceConfig`,
`name='fhort.commerce'`, `:4-8`) · `models.py` · `models_base.py` (abstractes) · `serializers.py` ·
`views.py` · `urls.py` · `services.py` (**fitxer pla, no paquet**) · `pdf_service.py` ·
`signals.py` · `management/commands/` · `migrations/` (0001-0019, amb data-migrations de seed:
`0002_seed_units.py`).
**NO EXISTEIXEN a commerce:** `admin.py`, `tests.py`, `tests/`, `permissions.py`, `filters.py`.

- **Alta de l'app:** `TENANT_APPS` — `settings.py:62-74` (commerce a `:72`, com `'fhort.commerce'`).
  `SHARED_APPS` (`:36-59`) és el schema `public`. `INSTALLED_APPS = list(SHARED_APPS) + [...]`
  (`:76`) → n'hi ha prou d'afegir-la a **una** llista. **`patterns/` és tenant-level → només
  `TENANT_APPS`.**
- **URLs:** `backend/fhort/urls.py:34` → `path('api/v1/', include('fhort.commerce.urls'))`. El
  prefix del mòdul **viu dins el register**, no a l'`include`: `router.register(r'commerce/units',
  ...)` (`commerce/urls.py:13`) → `/api/v1/commerce/<recurs>/`. Patró: **`DefaultRouter`** amb
  `basename='commerce-<recurs>'` i `urlpatterns = router.urls` (`commerce/urls.py:12-35`); les
  operacions no-CRUD són `@action`.
- **Permisos:** **no hi ha `permissions.py` a cap app** — font única
  `backend/fhort/accounts/capabilities.py`. Classe `HasCapability(BasePermission)` (`:46-54`), que
  llegeix `view.required_capability`. Capacitats a `:6-17`
  (`EXECUTE_TASKS, DEFINE_TASKS, SCHEDULE_FITTINGS, CLOSE_GATES, CONFIGURE, VIEW_TEAM_TASKS,
  MANAGE_USERS`); rols a `:20-26`. Patró dominant a commerce: mixin local `_ConfigureWriteMixin`
  (`views.py:31-37`) → lectura `IsAuthenticated`, **escriptura `CONFIGURE`**.
- **Tenant:** **no es determina a la view** — ho fa `TenantMainMiddleware` (`settings.py:86`) pel
  host; els querysets són `Model.objects.all()` (ja viuen dins el schema).
- **Views/serializers:** `ModelViewSet` (+ `ReadOnlyModelViewSet`); zero `APIView`. Exemple:
  `ProductViewSet` (`commerce/views.py:56-60`). Serializers: `ModelSerializer` amb `Meta` sempre.
- **Tests:** ⚠️ **NO EXISTEIX `pytest.ini`, `conftest.py`, `pyproject.toml` ni `setup.cfg`.**
  **El projecte NO fa servir pytest.** Els tests són **`tests.py` pla dins de cada app**
  (`tasks/tests.py`, `fitting/tests.py`) i s'executen amb **`python manage.py test fhort.<app>`**
  des de `backend/`. El tenant es gestiona amb **`django_tenants.test.cases.TenantTestCase`**
  (`tasks/tests.py:12`) + `APIRequestFactory`/`force_authenticate` (`:14`).
- **Migracions:** a `<app>/migrations/`, amb dependències cross-app declarades
  (`commerce/migrations/0001_initial.py:11-13` → `('tasks','0032_…')`). Aplicació: **`migrate_schemas`
  sense `--schema`** + auditoria directa a la BD (`CLAUDE.md:46-48`).

### El directori `patterns/` està **LLIURE** ✅

`ls backend/fhort/` → `accounts, backoffice, commerce, fitting, i18n_content, models_app, planning,
pom, tasks, tenants`. **Cap `patterns/`.** `grep -rn "patterns"` (fora de venv) → només
`urlpatterns` i un comentari irrellevant (`models_app/extraction_views.py:115`).

**Motlle per a l'app nova** (2 edicions fora de l'app):
1. `settings.py:73` → afegir `'fhort.patterns',` a `TENANT_APPS`.
2. `backend/fhort/urls.py:35` → `path('api/v1/', include('fhort.patterns.urls')),`.

**Veredicte B9: LLEST.** El motlle és clar i `patterns/` no col·lisiona amb res.

---

## TAULA FINAL — EXISTEIX / FALTA / DIFEREIX (per al CTO)

| # | Element | Estat | Evidència | Impacte |
|---|---|---|---|---|
| 1 | **`.RUL` real (qualsevol)** | 🔴 **FALTA** | `find /` exhaustiu → cap resultat | **S1-T4 sense material** |
| 2 | **Fitxer Polypattern** | 🔴 **FALTA** | idem | **S1-T6 / S2 sense 2a empremta** |
| 3 | AMELIA DXF | ✅ EXISTEIX | `media/fhort/import_sessions/2026/06/` (31 KB, 4 peces) | material de S1-T3, **fora de git** |
| 4 | `$INSUNITS`/`$MEASUREMENT` a AMELIA | 🔴 **NO EXISTEIX** (HEADER buida) | B3 | **S1-T3 DIFEREIX**: unitats per geometria, no per capçalera |
| 5 | Capa 14 (cosit) a AMELIA | 🔴 **NO EXISTEIX** | B3 (capes: 1,2,3,4,7,8,15) | **S7-T1 DIFEREIX**: no hi ha cosit d'on derivar el tall |
| 6 | ezdxf / shapely / matplotlib al venv | 🔴 **FALTA** (les 3) | `find_spec` → ABSENT ×5 | **acció de deploy del CTO abans de S1** |
| 7 | `GarmentTypeItemAsset` | 🔴 **NO EXISTEIX** (mai) | `git log -S` → 0 commits | `source_asset` → **`models_app.ItemFitxer`** |
| 8 | `pattern_digit`/`pattern_cad`/`scaling` | ✅ **JA EXISTEIXEN** | `0025_seed…:11,12,20` + BD | **S6-T4 SOBRA** |
| 9 | Allow-list `permisos["tasks"]` | 🟠 **BLOQUEIG NOU** | `views_b.py:541-546` | 403 per a tothom (excepte admin) fins que el CTO hi afegeixi els codes |
| 10 | `.dxf`/`.rul` a la whitelist d'upload | ✅ EXISTEIX | `services_fitxers.py:36-47` | res a tocar |
| 11 | Gate X-Accel `/protected-media/` | ✅ **VIU** | `sites-enabled/ftt-staging:55-61` | tanca el "Gate 2 🔴" del PREDEPLOY |
| 12 | `sites-available` ↔ `sites-enabled` | 🟠 **DIVERGEIXEN** | B5 | editar `sites-available` **trencaria** límit + descàrregues |
| 13 | `aprovada` vs `is_active` | 🟠 **DIFEREIX** del que el pla suposa | 3 de 4 aprovades **no** actives; cap constraint | guard de S7-T2: `filter(pk=…)`, **mai `get(aprovada=True)`** |
| 14 | Talla base a `GradedSpec` | 🔴 **NO és inferible** | `pom/services.py:110-115` | ve de `Model.base_size_label`; **mai per `delta==0`** |
| 15 | pytest | 🔴 **NO EXISTEIX** al projecte | cap `pytest.ini`/`conftest.py` | **S1 DIFEREIX**: `manage.py test`, no pytest |
| 16 | `backend/fhort/patterns/` | ✅ **LLIURE** | `ls backend/fhort/` | ubicació confirmada |
| 17 | Dos `requirements.lock` divergents | 🟠 ATENCIÓ | arrel vs `backend/` | aclarir quin mana abans d'afegir ezdxf |

---

## CONCLUSIÓ (10 línies)

**(a) BLOQUEJOS PER A S1.** Dos de durs i un de tou. **(1)** No hi ha **cap `.RUL`** ni el fitxer
**Polypattern** al servidor: S1-T4 i la meitat de S1-T6 **no tenen material** (l'Agus els ha de
pujar, o S1 tanca explícitament sense ells). **(2)** **ezdxf no està instal·lat** (ni shapely):
cal una acció de deploy abans de la primera línia de motor. **(3)** L'AMELIA que sí que tenim té la
**capçalera buida** (unitats **no** declarades → deduïbles per geometria: mm) i **no porta capa 14
(cosit)** → la re-derivació tall↔cosit de S7-T1 es queda sense font en aquest fitxer.

**(b) DESVIACIONS RESPECTE DEL QUE EL PLA ASSUMEIX.** **S6-T4 desapareix**: `pattern_digit`,
`pattern_cad` i `scaling` **ja són al seed** (i n'hi ha dos més, `pattern_review` i `marking`); a
canvi cal **desbloquejar l'allow-list `permisos["tasks"]`**, que el pla no preveia. **S1 no pot
tancar amb "pytest verd"**: el projecte **no té pytest** (és `manage.py test` + `TenantTestCase`) —
tot i que l'engine, en ser pur, es pot testejar amb `unittest` sense Django. **`GarmentTypeItemAsset`
no existeix i mai ha existit**: el `source_asset` de `PatternFile` ha d'apuntar a
**`models_app.ItemFitxer`** i el XOR a **`tasks.GarmentTypeItem`**. Del grading: **`GradingVersion`
penja de `SizeFitting`, no del Model**; **aprovada ≠ activa** i poden ser **múltiples** (guard per
`filter`, mai `get`); i la **talla base no s'infereix del delta 0**. Per a B6, la recomanació és
**render SVG propi** (el DXF real només té polilínies, línies i punts: matplotlib arrossegaria Qt i
sis paquets per dibuixar rectes).

**(c) UBICACIÓ `patterns/engine/` — CONFIRMADA.** `backend/fhort/patterns/` **està lliure** i el
motlle de `commerce/` s'hi aplica sense fricció: alta a **`TENANT_APPS` (`settings.py:73`)**,
`include` a **`fhort/urls.py:35`**, `DefaultRouter` amb prefix dins el register
(`/api/v1/patterns/…`), permisos via `HasCapability` + `CONFIGURE` (`accounts/capabilities.py`), i
**tests a `patterns/tests.py`** (no `tests/`, que no és la convenció del repo). La frontera
hexagonal `patterns/engine/` com a paquet pur és compatible amb tot això: cap convenció del projecte
l'impedeix.
