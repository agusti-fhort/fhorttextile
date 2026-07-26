# DIAGNOSI — EL TERRENY DEL `.FTT` I LA BIBLIOTECA DE SKETCHES

> **Data:** 2026-07-14 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
> **Abast:** el terreny real que trepitjaran quatre peces de disseny: **bifurcació-primer**,
> **sketches `.ftt` a GTI**, **promoció model→GTI amb selecció** i **porta-picker del Taller**.
> **Encàrrec:** brief TERRENY .FTT + BIBLIOTECA (blocs a–f).
>
> **Convenció:** tota afirmació porta `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi**
> (verificat, no especulat). Les propostes van marcades `💡 PROPOSTA (a validar)`: les decisions
> són humanes (Patró C).
>
> **Guardes:** cap escriptura de codi, cap migració, cap restart · BD només `SELECT` · `.ftt` del
> disc oberts en **lectura** (zipfile) · únic fitxer creat: aquest.
>
> ⚠️ **Nota de concurrència:** una sessió germana (F1) està escrivint a `TechSheetEditor.jsx`.
> Les àncores d'aquest fitxer són de l'estat **pre-F1** (working tree net, `git log` a `bf35a0b`) i
> **es poden desplaçar** quan F1 aterri. Les de backend no es mouen.

---

## RESUM EXECUTIU

1. **La llei de bifurcació-primer no lluita contra el sistema: el corregeix.** Avui l'autoguardat
   (debounce 2 s a **cada** canvi, `TechSheetEditor.jsx:1953-1973`) **crea una versió NOVA a cada
   desat** — sempre, sense branca condicional (`services_ftt_document.py:342-347`). Resultat mesurat
   a la BD: **225 files `TECHSHEET` per a 6 documents reals**; el model 174 en té **90 versions en
   dos dies**, encadenades a 5-40 segons de distància. **El versionat actual no versiona: fa soroll.**

2. **El "Path 2" (matxacar el vell) NO EXISTEIX, i el que l'impedeix és una sola funció.**
   `save_model_file` és **l'únic escriptor de bytes** de tot el backend (`services_fitxers.py:128`;
   grep de `.fitxer.save(` només retorna aquesta i la seva bessona d'item) i **sempre INSERTA** una
   fila nova degradant l'anterior (`:107-133`). El punt mínim d'intervenció són **2 llocs**, i cap
   dels dos toca `save_model_file` (zona declarada intocable).

3. **El motor de la bifurcació JA EXISTEIX, i està prohibit per una línia.**
   `usar_al_model` (`views.py:169-231`) ja fa exactament "duplicar cap a…": descongela el `.ftt`, el
   **re-resol contra el model destí** (`reescriure_ftt_per_model`, `services_ftt_document.py:274-289`)
   i crea una **cadena NOVA v1** al destí. L'única cosa que impedeix fer-ho **dins el mateix model**
   és el guard de `views.py:201-203` ("El model destí és el mateix que el del fitxer origen").

4. **🔴 EL FET MÉS GREU DE LA DIAGNOSI: la re-resolució del `.ftt` és INCOMPLETA — i ningú se
   n'havia adonat perquè encara no s'ha exercitat.** `unfreeze_document` desfà quatre coses del
   model A (camps congelats, asset del logo, imatge-logo, metadata — `services_ftt_document.py:233-271`),
   però **NO toca les taules snapshot**: `_unfreeze_mapper` només actua sobre objectes amb marca
   `field_key` i «sense marca, es deixa tal qual» (`:202-205`). Als `.ftt` reals del disc hi ha
   **`table.snapshot.model_id`** (verificat: 167, 188) i **`table.rows` amb POMs i mesures
   congelades**, i **`data_block.size_fitting_id`** (verificat: 52) que fa **re-fetch en viu**
   contra el fitting del model origen. **Copiar una fitxa del model A al model B hi portaria les
   mesures d'A en silenci.** ✅ **Encara no ha passat:** `SELECT` confirma **0 files** amb
   `derivat_de_model` o `derivat_de_item` — el bug és **latent, no consumat**. Però és **la mateixa
   funció** que la promoció ha de fer servir: **s'ha d'arreglar abans, no després.**

5. **El `.ftt` a l'item ja s'aguanta a mitges — i els tres forats tenen nom.** `.ftt` i `.svg` **ja
   són a la whitelist** (`services_fitxers.py:37,40`) i `usar-al-model` **ja importa** un fitxer
   d'item a un model. Però: (a) el camí d'item **no descongela** el `.ftt` (asimetria amb el de
   model — `item_fitxer_views.py:165-170` vs `views.py:208-218`), i la docstring que ho justifica
   (`item_fitxer_views.py:140-142`: "el ZIP és auto-contingut") **és falsa**, i el mateix repo la
   refuta a `views.py:176-181`; (b) un `.ftt` pujat a un item queda amb `tipus='ALTRES'` → la còpia
   **no s'obre com a fitxa** (404 a `ftt_document_views.py:87-90`); (c) **no hi ha cap superfície
   `.ftt` al costat item** (ni detail, ni lock, ni `asset/`).

6. **El picker de dues branques ja està construït — només està apagat.** `AssetNavigator` ja navega
   **Models | Catàleg (família→item)** (`AssetNavigator.jsx:271-285`, jerarquia a `:28-38`,
   `:232-241`), però el fork de tabs viu **dins `{mode === 'files' && …}`**: en `mode='models'` (el
   de la porta de Fitxa tècnica) **no es pinta**. No cal reescriure'l: cal **desbloquejar-lo**.

7. **Ordre honest:** el **fix de `unfreeze_document`** és **prerequisit** de la promoció i de la
   bifurcació cap a un altre host. Fer la promoció abans seria construir sobre una funció que menteix.

---

# BLOC A — EL DESAT ACTUAL

## A.1 Autoguardat: real, a cada canvi, i sense "Desa" manual

| fet | fitxer:línia |
|---|---|
| únic efecte d'autosave | `TechSheetEditor.jsx:1953-1973` |
| **trigger** | deps `[pages, locked, pageFormat]` → **qualsevol mutació** (moure un objecte, escriure una lletra). **No és un timer periòdic** |
| debounce | `setTimeout(…, 2000)` (`:1959`, `:1971`) amb `clearTimeout` previ (`:1958`) |
| guarda del primer load | `skipSave.current` (`:1399`, `:1917`, `:1955`) |
| gate | `if (!locked) return` (`:1956`) |
| endpoint | `PATCH /api/v1/ftt-documents/${fttHeadId.current}/` (`:1965-1967`) |
| re-apuntada al nou cap | `fttHeadId.current = nh.id` (`:1968`) |

**NO EXISTEIX botó de Desa manual:** el de la cinta és un indicador mort (`disabled: true`,
`TechSheetEditor.jsx:3423`). **L'autosave és l'única via d'escriptura del document.**

Cadena backend: `urls.py:177` → `FttDocumentDetailView.patch` (`ftt_document_views.py:104-125`;
409 si no `is_current` a `:106`, 403 si no té el lock a `:111`, `renew_lock` a `:124`) →
`save_document` (`services_ftt_document.py:324-347`).

## A.2 Versionat: cada desat = una fila nova + un ZIP nou al disc

`save_document` (`services_ftt_document.py:324-347`), sense cap branca condicional:
`extract_document_assets` (`:336`) → fusiona assets vells i nous (`:337-340`) → `pack()` (`:341`) →
**`save_model_file(..., versio_anterior=head_fitxer, ...)`** (`:342-347`).

Qui mou `is_current` — `services_fitxers.py:90-135` (`save_model_file`, declarat "l'ÚNIC punt que
escriu `is_current`/`versio`", `:98-99`): `versio = anterior.versio + 1` (`:107-112`) · instància
nova `is_current=True` (`:114-121`) · **bytes nous al disc** (`:128`) · degrada el predecessor
(`:131-133`). La docstring del mòdul ho diu: *"El «Desa» de l'editor = una versió nova encadenada…
no una sobreescriptura"* (`services_ftt_document.py:8-9`).

## A.3 🔴 El churn, mesurat

`SELECT` al schema `fhort`: **225 files `TECHSHEET` · 6 caps · 6 models.**

| model | nom_fitxer | versions | max |
|---|---|---|---|
| 174 | `BRW-FW26-0012_fitxa.ftt` | **90** | 90 |
| 167 | `BRW-FW26-0005_fitxa.ftt` | **86** | 86 |
| 162 | `BRW-SS26-0001_fitxa.ftt` | 26 | 26 |
| 188 | `BRW-SS27-0001_fitxa.ftt` | 19 | 19 |
| 182 / 186 | — | 2 / 2 | 2 / 2 |

Evidència que és churn d'autosave i **no** d'usuari: al model 188 les versions 12→18 s'encadenen en
**100 segons** (5-40 s de distància). **Cada versió és un ZIP sencer al disc**: 225 fitxers `.ftt`
a `backend/media/fhort/model_fitxers/` per a 6 fitxes reals. Coherent amb la memòria
`ftt-version-churn` (v1→v13 en 13 obertures), i ara **quantificat**.

## A.4 "Path 2" (sobreescriure): **NO EXISTEIX**

- L'únic escriptor de bytes de `ModelFitxer` és `services_fitxers.py:128` (dins `save_model_file`).
  Grep de `.fitxer.save(` a tot `backend/fhort` → **només** `:128` i `:171` (la bessona d'item).
- `ModelFitxerViewSet` és **ReadOnly + Destroy** (`views.py:147-150`: "NO exposa create/update").
- `FttDocumentDetailView.patch` no té cap flag alternatiu (`ftt_document_views.py:122`).

**Què ho impedeix exactament:** `services_ftt_document.py:342-347` passa **incondicionalment**
`versio_anterior=head_fitxer`.

💡 **PROPOSTA (a validar) — punt mínim d'intervenció (2 llocs, cap toca `save_model_file`):**
1. **Funció germana** a `services_ftt_document.py` (p.ex. `overwrite_document(head, document_json)`)
   que repackegi igual (`:336-341`) i escrigui **sobre `head_fitxer`** actualitzant només
   `fitxer`/`mida_bytes`/`checksum` (sense tocar `versio`/`is_current`/`versio_anterior`).
   ⚠️ **Parany real:** `FileField.save()` sobre una instància existent **crea un fitxer nou al disc
   amb sufix aleatori i deixa el vell orfe** → cal esborrar els bytes previs (`delete_fitxer_bytes`
   ja existeix i s'usa a `views.py:163-167`). Sense això, canviaries churn de BD per churn de disc.
2. `ftt_document_views.py:104-125` — la PATCH tria entre les dues, **mantenint** els gates de
   `is_current` (`:106`) i de lock (`:111`).

## A.5 El nom del fitxer

- Camp: `ModelFitxer.nom_fitxer` (`models_app/models.py:369`).
- Assignació: `_doc_filename(model)` (`services_ftt_document.py:90-92`) →
  `"{codi_intern}_fitxa.ftt"` → **`BRW-FW26-0005_fitxa.ftt`**. **Compost però no descriptiu:** codi
  estructural + sufix fix. **Cap component lliure.**
- Es propaga: `save_document` reusa `head_fitxer.nom_fitxer` (`:344`, `:346`) → **les 90 versions
  comparteixen nom idèntic** (confirmat: 1 sol `nom_fitxer` per cadena).
- **Editable des de l'editor: NO EXISTEIX** (cap endpoint de rename — ViewSet ReadOnly+Destroy; cap
  input de nom al frontend).
- Els sufixos del disc (`..._fitxa_RX1lv7B.ftt`) són de l'storage de Django per col·lisió, **no**
  del `nom_fitxer` de BD.

→ **El disseny de "noms composts [codi automàtic] + [nom descriptiu lliure]" no xoca amb res: el
segon component simplement no existeix encara.**

## A.6 `FttDocumentLock`

OneToOne a **l'ARREL de la cadena** (`ftt_models.py:11-36`, `:20-24`) → el lock **sobreviu a
l'avanç de versions** (identitat lògica: `document_root`, `services_ftt_document.py:28-33`).
**TTL 30 min** (`FTT_LOCK_TTL`, `:25`), amb force-if-stale (`acquire_lock:36-58`). Endpoints
`lock`/`unlock` (`ftt_document_views.py:128-159`; override només amb `CONFIGURE`, `:152`);
`renew_lock` a cada PATCH (`:124`). Frontend: adquireix a l'obrir (`TechSheetEditor.jsx:1858-1867`),
**heartbeat cada 10 min** (`:1886-1896`), unlock al desmuntar i a `beforeunload` (`:1879-1912`).
`locked` (`:1363`) governa **tota** l'edició i l'autosave.

**Veredicte A: el terreny és favorable.** El versionat automàtic és soroll mesurable (225/6), i la
llei de bifurcació-primer el converteix en el que hauria de ser. El lock ja té la noció d'identitat
lògica (arrel de cadena) que la bifurcació necessita.

---

# BLOC B — LA CREACIÓ (Path 1 actual)

## B.1 El flux real: la porta no crea res; crea el **resolutor de ruta**

1. `TechSheetEntry.jsx` (la porta del menú) **només navega** a `/models/:id/fitxa` (`:38`, `:54`).
2. `FttResolver` (`App.jsx:108-170`): busca
   `GET /model-fitxers/?model=<id>&tipus=TECHSHEET&is_current=true` (`:139-141`) → si n'hi ha,
   **redirigeix a l'existent** (`:144-147`).
3. Si no n'hi ha: llegeix `document-templates` (`:151-153`) → si el tenant en té, **mostra un
   selector "blanc | plantilla"** (`:156-186`); si no, crea en blanc.
4. `createDoc` (`:123-137`): `POST /api/v1/models/<id>/ftt-document/` → navega a
   `/models/:id/ftt/<f.id>`.
5. Backend `FttDocumentCreateView` (`ftt_document_views.py:49-79`): sense template →
   `new_empty_document()`; amb template → `unpack` + **`resolve_placeholders`** (congela els `field`
   amb dades del model, `:69-71`); plantilla corrupta → degrada a buit (`:73-76`) →
   `create_document` → `save_model_file` **sense `versio_anterior`** → **cadena NOVA, v1**.

🔑 **Clau per a la bifurcació:** `FttDocumentCreateView` **no comprova** si el model ja té un
TECHSHEET — la deduplicació la fa **el frontend** (`App.jsx:139-147`). És a dir: **el primitiu
"crear una cadena nova de `.ftt`" ja existeix i és cridable avui**. I ja hi ha **precedent d'UI que
ramifica ABANS del canvas**: el selector "blanc | plantilla" (`App.jsx:165-186`).

## B.2 "Desar com a" / duplicar: **NO EXISTEIX** — però el germà real sí

- **Duplicar dins del mateix model: NO EXISTEIX**, i està **explícitament prohibit**:
  `views.py:201-203` → 400 *"El model destí és el mateix que el del fitxer origen."*
- **`save-as-template` SÍ existeix** (`ftt_document_views.py:188-208`; UI a
  `TechSheetEditor.jsx:3057-3068`): `load_document` → `pack(kind=FTT_KIND_TEMPLATE)` → crea un
  **`DocumentTemplate`** (`.fttpt`). **NO crea cap `ModelFitxer`, no toca la cadena.** És un altre
  magatzem: dona el patró `load → pack → persistir`, però **no** serveix de base directa.
- **El germà real d'un "duplicar" és `usar_al_model`** (`views.py:169-231`): per a un `.ftt` fa
  `reescriure_ftt_per_model` (`:210`) → `save_model_file` **sense `versio_anterior`** (`:214-215`)
  → **cadena NOVA v1 al destí** + `marcar_procedencia` (`:224`). L'origen no es toca (`:174`).

## B.3 Plantilles

`DocumentTemplate` (`ftt_models.py:38-72`): blob `.fttpt`, `origen` (`sistema`|`tenant`), `actiu`.
CRUD a `ftt_template_views.py:25-32`; `fitxer_template` és **read-only** al serializer (`:20-22`):
**només s'omple via `save-as-template`**. Instanciació: `resolve_placeholders`
(`services_ftt_document.py:153-185`) congela cada `type:'field'` → `type:'text'` **deixant la marca
`field_key`** (`:168`) — i l'invers (`unfreeze_document`, `:233-271`) és el que fa possible
reassignar un `.ftt` a un altre model.

**Veredicte B: els dos primitius de la bifurcació ja existeixen** (crear cadena nova ·
copiar-amb-re-resolució). Falta **l'UI que els combina i demana destí+nom abans del canvas**, i
**treure el guard d'un sol model** (`views.py:201-203`) si es vol bifurcar dins el mateix model.

---

# BLOC C — `ItemFitxer` + `.ftt`

## C.1 La whitelist ja accepta `.ftt` i `.svg` (cap fix)

`services_fitxers.py:36-47` — literal: `.ftt` (**`:37`**, comentari `# TECHSHEET`), `.pdf`, `.dxf`,
`.svg` (**`:40`**, `# SKETCH_SVG`), `.rul`, `.txt`, imatges, `.xlsx`/`.xls`.
Mida màxima **20 MiB** (`:31`). Guard únic `validate_upload` (`:54-67`), cridat per l'item a
`item_fitxer_views.py:68-71`. **Cap validació de contingut** (no s'obre el ZIP).
Mirall al frontend: `frontend/src/utils/uploads.js:14-15` (ja inclou tots dos).

## C.2 El viatge `derivat_de_item`, pas a pas (`item_fitxer_views.py:130-176`)

Gate: **`IsAuthenticated`**, no `CONFIGURE` (`:45-47` — "l'escriptura va al MODEL, no al catàleg").

1. **Origen** (`:152-155`): `get_object()`; 400 si no té bytes.
2. **Destí** (`:157-160`): `model_id` obligatori → `get_object_or_404(Model)`.
3. **Còpia de bytes** (`:165-170`): `save_model_file(model, origen.fitxer, tipus=origen.tipus,
   origen='upload', nom=origen.nom_fitxer)` → **ModelFitxer nou, cadena pròpia v1, `is_current`**,
   checksum/mida/mimetype recalculats. **L'ItemFitxer origen no es toca mai.**
4. **Procedència** (`:173`): `marcar_procedencia(nou, user, derivat_de_item=origen)`
   (`services_fitxers.py:181-200`) — un sol `save(update_fields=[...])`, **no toca `is_current`**.
5. **Resposta** (`:175-176`): 201 amb `ModelFitxerSerializer`. **Sense camp `avis`** (a diferència
   del germà model→model).

`derivat_de_label` (`serializers.py:34`, getter `:48-61`): mostra el **codi del model origen** o el
**codi del GTI origen**; l'usuari el veu com a segona línia sota el nom (`FileList.jsx:92-97`).
`ItemFitxerSerializer` **no en té** — coherent: *"un ItemFitxer no té origen: és la font"*
(`FileList.jsx:90-91`).

## C.3 🔴 Funcionaria tal qual amb un `.ftt`? **NO. Tres forats amb nom.**

**(a) ASIMETRIA D16 — el camí d'item no descongela.** Compara:
- model→model: `if ftt_svc.es_ftt(origen): blob, report = reescriure_ftt_per_model(...)`
  (`views.py:208-211`).
- item→model: **cap crida a `es_ftt` ni a `reescriure_ftt_per_model`** (`item_fitxer_views.py:165-170`).

La docstring que ho justifica (`item_fitxer_views.py:140-142`: *"Un `.ftt` es copia tal qual: el ZIP
és auto-contingut"*) **només és certa si el `.ftt` de l'item no ve d'un model**. I l'única via
d'entrada d'un `.ftt` al catàleg avui **és pujar bytes** — típicament **descarregats d'un model**.
El mateix repo la refuta a `views.py:176-181`: *"Aquí **és fals**: un `.ftt` d'un model A porta text
congelat, l'asset del logo del seu client, un objecte image amb la URL del logo i metadata, tot de A."*
**Fix:** el codi ja existeix i és duck-typed (`es_ftt` llegeix `.tipus`/`.nom_fitxer`,
`services_ftt_document.py:292-297`) → funciona sobre un `ItemFitxer` **sense tocar-lo**.

**(b) `tipus='ALTRES'` → la còpia no s'obre com a fitxa.** `save_item_file` posa `tipus or 'ALTRES'`
(`services_fitxers.py:168`) i `GarmentTypes.jsx:103-106` **no envia mai `tipus`**. La còpia hereta el
tipus (`item_fitxer_views.py:167`) → el `ModelFitxer` resultant és `ALTRES` → **404** a
`FttDocumentDetailView._get_techsheet` (`ftt_document_views.py:87-90`, que exigeix
`tipus=TECHSHEET`), i **no apareix** als llistats `?tipus=TECHSHEET` (`App.jsx:143`,
`ModelSheet.jsx:607`).
**Fix mínim:** `ItemFitxerViewSet.create` **ja accepta `tipus`** (`item_fitxer_views.py:83`, perquè
`create` no passa pel serializer) → n'hi ha prou amb enviar-lo des de la UI **o** inferir-lo de
l'extensió al backend.

**(c) NO EXISTEIX superfície `.ftt` al costat item.** Tots els paths estan ancorats a `ModelFitxer`:
`models/<id>/ftt-document/` i `ftt-documents/<fitxer_id>/{detail,lock,unlock,export,asset}`
(`urls.py:176-182`). **Un sketch `.ftt` d'item no es pot ni previsualitzar ni editar al catàleg**:
només descarregar-ne els bytes. En particular **no hi ha endpoint `asset/` per a `ItemFitxer`** →
un `.ftt` amb imatges **no en podria pintar cap** des del catàleg.

## C.4 Promoció inversa model→item: **NO EXISTEIX** (i està anotada)

Declarat al codi: `item_fitxer_views.py:144` — *"NO existeix la promoció inversa (② model→catàleg):
forat amb nom, diferit."* I al report d'sprint: `docs/diagnosis/REPORT_S03b_2026-07-09.md:143-147`
(*"quina versió, qui pot, què passa si l'item ja té un fitxer d'aquell tipus"*). `ItemFitxer` **no té
cap FK de procedència** (`models.py:459-496`).

## C.5 Camins d'UI cap a `usar-al-model` avui

Tots dins `FilePicker.jsx` (el panell lateral de l'editor):
1. **Tab "Catàleg"** → botó "Usar al model" per fitxer (`:158-161` → `:68-79`). **No filtra per
   tipus** → **un sketch `.ftt` d'item ja seria importable des d'aquí avui**, amb els forats de §C.3.
2. **AssetNavigator dins FilePicker** (`:204-209`, `:239-249`) → `triarDelNavegador` (`:91-109`)
   imposa la sobirania (catàleg → `itemFitxers.usarAlModel`; altre model → `modelFitxers.usarAlModel`;
   sempre la **còpia**, mai l'original). **Però** `pickable={isImage}` (`:246`) → **un `.ftt` no és
   seleccionable** per aquesta via.
3. `TechSheetEditor.jsx:3320-3352` (`importarDelTenant`) importa **bytes** (SVG→paths, imatge→dataURL)
   i **no** fa `usar-al-model`; **un `.ftt` no hi està contemplat**.

A `GarmentTypes.jsx` (secció Fitxers del catàleg, `:255-287`) **no hi ha cap acció `usar-al-model`**:
només llistar i pujar (gated per `CONFIGURE`, `:272-280`).

**Veredicte C: el pont existeix i aguanta bytes, però no aguanta encara un `.ftt` com a document.**
Tres fixos petits i localitzats: descongelar al camí d'item · `tipus` correcte a l'upload ·
(si es vol editar al catàleg) una superfície `.ftt` per a item.

---

# BLOC D — ANATOMIA DEL `.FTT` (el menú del diàleg de promoció)

## D.1 El contenidor

`services_ftt.py:1-13` (docstring normatiu) — ZIP amb:
`manifest.json` (`{magic:"FTT", schema_version, app_version, kind, checksums}`, construït a
`:79-85`; `kind ∈ {document, template}`, `:27-28`) · `document.json` · `assets/<nom>` · `preview.png`
(opcional). `pack()` a `:58-98`, `unpack()` a `:227-282`.
`document.json` = `{ftt_schema, metadata, pageFormat, pages:[{id, objects, guides}]}` (`:50-55`).

## D.2 Els `.ftt` REALS del disc (verificat, lectura amb `zipfile`)

**225 fitxers.** Entrades reals: **només `manifest.json` + `document.json`**. **CAP té `assets/`.
CAP té `preview.png`.** Manifest real verificat (sense cap `model_id`):
`{"app_version":"0.1.0","checksums":{...},"magic":"FTT","schema_version":1}`.

Inventari real de tipus (arbre sencer, fills inclosos): `text` 146 · `path` 95 · **`field` 67** ·
`group` 54 · `arrow` 54 · `rect` 46 · `line` 44 · **`data_block` 24** (header 3, **graded_table 21**)
· `sketch_svg` 21 · **`table` 11** (bom 1, custom 8, **pom_fitting 2**) · `image` 3 · `ellipse` 1.
`metadata`: `{}` en 199 fitxers; `{reference, season, description}` en 26.

## D.3 🔴 Com es resolen els camps dinàmics — **això ho decideix tot**

| objecte | resolució | evidència |
|---|---|---|
| `data_block kind='header'` | **VIU.** No desa **cap** valor; es reconstrueix a cada render des del `modelData` **de l'host** → **es re-resol sol en canviar de host** | `TechSheetEditor.jsx:1030-1031` → `buildHeaderPrimitives:522-551`; `modelData` de `GET /models/<id>/` (`:1830`). Confirmat a `services_ftt_document.py:244-246` |
| `data_block kind='graded_table'` | **VIU PERÒ PER ID.** Re-fetch a l'obrir: `GET /api/v1/fitting/{size_fitting_id}/graded-table/` | `TechSheetEditor.jsx:1934-1951` (fetch a `:1942`). **El `size_fitting_id` és del model ORIGEN** → en canviar de host: **404 o dades del model equivocat** |
| `table` (bom/custom/**pom_fitting**) | **CONGELAT.** `rows` materialitzades a la inserció; `snapshot` només és traçabilitat, **mai es re-llegeix** | `TechSheetEditor.jsx:2833-2835` (llei explícita: *"valors CONGELATS a la inserció… cap binding viu"*) |
| `field` | **MAI resolt en viu** (es pinta com a xip `{label}`). Es congela a `text` **només** en instanciar des de plantilla | xip: `buildFieldChipPrims:506-514`; congelació: `services_ftt_document.py:153-172` |
| `text` amb marca `field_key` | congelat però **reversible** | `FIELD_MARK` (`services_ftt_document.py:116`), escrit a `:168`, desfet a `:201-217`. **0 ocurrències al disc avui** |

## D.4 🔴 `unfreeze_document` NO cobreix el que el disc realment porta

`unfreeze_document` (`services_ftt_document.py:233-271`) desfà **quatre** coses del model A
(docstring `:236-246`): text congelat dels `field` · asset `field_customer_logo` · objecte
`image kind:'logo'` amb URL absoluta · `metadata{}`.

Però `_unfreeze_mapper` **només actua si l'objecte porta la marca `field_key`** — *"Sense marca, es
deixa tal qual"* (`:202-205`). I `_unfreeze_objects` (`:220-230`) només filtra, a més, les imatges de
logo. **Per tant NO toca:**
- **`table.snapshot.model_id`** — verificat al disc: **167**, **188** (escrit a
  `TechSheetEditor.jsx:2889, 2932, 2953, 2970`).
- **`table.rows`** amb **POMs i mesures base congelades** del model origen (verificat al disc:
  `["A", {"text":"Chest width","sub":"Ample de pit"}, "37", …]`).
- **`data_block.size_fitting_id`** — verificat al disc: **52** (21 ocurrències) → **re-fetch viu**
  contra el fitting del model origen.

**Conseqüència:** `reescriure_ftt_per_model` (`:274-289`), que és unfreeze + resolve, **és incompleta
per als documents que el sistema genera avui**. El seu docstring diu que el resultat "és
indistingible d'instanciar la plantilla directament sobre B" (`:278-279`) — **i no ho és**.
La causa és cronològica i benigna: `unfreeze_document` **es va escriure abans de les taules snapshot
S3**. Ningú ha mentit; el codi s'ha quedat enrere.

✅ **Encara no ha fet mal:** `SELECT ... WHERE derivat_de_model_id IS NOT NULL OR derivat_de_item_id
IS NOT NULL` → **0 files**. **La maquinària de còpia no s'ha exercitat mai amb dades reals.** El bug
és **latent**. Però **és la mateixa funció que la promoció i la bifurcació-cap-a-un-altre-host han de
fer servir** → **s'arregla abans de construir-hi a sobre**, no després.

## D.5 Assets

Empaquetat: `assets/<sha16>.<ext>` (`services_ftt.py:144-158`), extret al desar
(`services_ftt_document.py:336`). El backend **no serveix el ZIP**: retorna `document_json` + mapa
`{nom → URL}` (`_asset_urls`, `ftt_document_views.py:40-46`) cap a
`/api/v1/ftt-documents/<fitxer_id>/asset/<name>/` (`:216-227`, exigeix `ModelFitxer` TECHSHEET).
Reescriptura al client: `documentToV2` (`TechSheetEditor.jsx:285-300`) ↔ `v2ToDocument` (`:305-320`).

**Viatgen sols?** Els **bytes sí** (van dins el ZIP). Però **l'endpoint que els serveix està lligat a
un `ModelFitxer` TECHSHEET** → per a un `ItemFitxer` **NO EXISTEIX** (§C.3c).
**Risc teòric avui, real demà:** cap `.ftt` del disc té assets encara (les 3 imatges són dataURL
inline i els 21 croquis són `sketch_svg` inline).

## D.6 TAULA DE DECISIÓ — el menú del diàleg de promoció

| **SELECCIONABLE** (valor del model: el tècnic tria si viatja) | **REFERÈNCIA FRÀGIL** (es trenca en canviar de host) | **ESTRUCTURA PURA** (viatja sense problema) |
|---|---|---|
| `table kind='pom_fitting'` → `rows` amb **POMs i mesures congelades** (`TechSheetEditor.jsx:2889,2932`) | **`table.snapshot.model_id`** (167, 188) — `TechSheetEditor.jsx:2889,2932,2953,2970` | `path` (95), `rect` (46), `line` (44), `arrow` (54), `ellipse` (1) |
| `table kind='bom'` → `rows` (materials/proveïdors) — `:2938-2953` | **`data_block.size_fitting_id`** (52) → re-fetch viu a `/fitting/{id}/graded-table/` — `:1936,1942`. **Sense el model: 404** | `text` (146) — textos lliures |
| `table kind='custom'` → `rows` lliures — `:2970` | `table.snapshot.size_fitting_id` (78) | **`sketch_svg`** (21) — **SVG inline, auto-contingut** ← *el cor de la biblioteca* |
| `text` amb marca `field_key` — `services_ftt_document.py:116,168` *(0 al disc avui)* | `image kind='logo'` amb **URL absoluta** al logo del client origen — `services_ftt_document.py:188-198` | `group` (54) + `children` — `_map_object_tree` (`services_ftt.py:130-141`) |
| `document.metadata` `{reference, season, description}` — 26 fitxers | asset `assets/field_customer_logo.<ext>` — `services_ftt_document.py:119,136-141` | **`field`** (67) — **xip sense valor**; **es resol al destí** (`buildFieldChipPrims:506-514`) |
| — | URL d'asset lligada a `fitxer_id` de `ModelFitxer` TECHSHEET (**no existeix per a item**) — `ftt_document_views.py:40-46, 216-227` | **`data_block kind='header'`** (3) — **no desa cap valor**; es reconstrueix des de l'host |

🎁 **La bona notícia per al disseny "sketches a GTI":** el que el disseny vol promocionar
(**`sketch_svg` = 21 al disc, `path`, `field`, `header`**) cau **sencer** a la columna
**ESTRUCTURA PURA**. La columna fràgil és tota de **taules i logo** — precisament el que un sketch de
biblioteca **no** ha de portar. **El diàleg de selecció és viable i el seu defecte natural és
"estructura sí, taules no".**

**Veredicte D: la promoció és dimensionable, però NO és trivial** — i el seu prerequisit no és UI,
és **completar `unfreeze_document`**.

---

# BLOC E — EL PICKER CANÒNIC

## E.1 `TechSheetEntry.jsx` (124 l.) és una **closca prima** sobre `AssetNavigator`

La llista pròpia de models va ser **substituïda** per l'AssetNavigator en mode `models`, inline
(comentari `TechSheetEntry.jsx:18-22`). Estat: `busyId` (`:30`), `error` (`:31`), `consultaModel`
(`:33`) i `nav` (memòria de camí de pàgina, `:36`) — que **ja porta `gtId`/`gtiId`**, camps de
catàleg que aquesta pàgina **no fa servir mai**.
Selecció: `<AssetNavigator mode="models" inline nav onNav onPick={obrir} actionLabel=… />`
(`:114-121`). Navegació: `obrir(model)` (`:40-68`) → `openTask(model.id,'tech_sheet')` →
`/models/:id/fitxa?task_id=…`; si 403 `task_type_not_allowed` → ofereix **"obrir en consulta"**
(`:38`, `:101`). **No hi ha selecció de destí ni de nom:** el model triat **és** el destí.

## E.2 🎁 `AssetNavigator`: **les dues branques JA existeixen** — apagades per `mode`

`components/assets/AssetNavigator.jsx` (370 l.). Props (`:83-86`): `mode='files'|'models'`,
`filterTipus`, `onPick`, `onClose`, `inline`, `actionLabel`, `pickable(f)`, `nav`/`onNav`.

- **El fork de tabs `['models','catalog']` és a `:271-285`… dins de `{mode === 'files' && (…)}`.**
  En `mode='models'` (el de la porta de Fitxa tècnica) **no es pinta**.
- **Branca Models:** facetes derivades al client (D20) Client ▸ Any ▸ Temporada ▸ model
  (`:150-158`, `:216-231`).
- **Branca Catàleg: família → item → fitxers** — **exactament la jerarquia demanada**
  (`CARREGA:28-38`; render `:232-241`).
- Cerca global amb debounce 250 ms que travessa **els dos mons** (`:101-121`, `:191-215`).
- Consumidors (3): `TechSheetEntry.jsx:114` (models, inline) · `FilePicker.jsx:240-248` (files,
  modal) · `TechSheetEditor.jsx:3639-3648` (files, modal, amb `filterTipus`).

**Límit real:** `CARREGA` (`:28-38`) està **hardcodat** a `garmentTypes`/`garmentTypeItems`/
`modelFitxers`/`itemFitxers`. **No sap llistar `PatternFile`** i no hi ha prop per injectar
carregadors. I el peu **només ofereix UN botó d'acció** (`:317-325`).

## E.3 `FilePicker` i el menú Disseny

`FilePicker.jsx` — panell lateral de l'editor amb tabs propis `model | catalog | import` (`:23`,
`:195-201`), on `catalog` és **només l'ítem del model actual** (`garmentTypeItemId`, passat des de
`TechSheetEditor.jsx:3633`). El botó "Explora tot el tenant" (`:204-208`) obre l'**AssetNavigator en
modal**. Duplicació coneguda i assumida.

**Menú Disseny** — `components/layout/Sidebar.jsx:41-49`: entrades `NavLink` declaratives (`to:`):
`/fitxa-tecnica` (`:44`) i `/disseny/documents` (`:45`). "Patró DXF" es va **retirar a S5**
(comentari `:46-48`). **Afegir "Biblioteca de patrons"/"Taller" = 1 línia + clau i18n + 1 `<Route>`.**
**NO EXISTEIX cap porta-menú del Taller** (s'hi entra només des de `PatternTab.jsx:178`,
`WorkPlan.jsx:41`, `TaskTree.jsx:47`).

## E.4 Rutes (`App.jsx`)

`/models/:id/fitxa` → `FttResolver` (`:249-253`) · editor `.ftt` `/models/:id/ftt/:fitxerId` **fora
del Shell** (`:255-259`) · porta `/fitxa-tecnica` → `TechSheetEntry` **dins el Shell** (`:275`) ·
Taller `/models/:id/patro/taller` **fora del Shell** (`:263-267`).

## E.5 Cost d'afegir

**(a) Segona branca (Catàleg família→item) a la porta — COST BAIX.** La branca ja està escrita:
1. `AssetNavigator.jsx:271` — treure el fork de sota `{mode==='files'}` (prop `branques=[…]` o mode nou).
2. `AssetNavigator.jsx:133-137` — `clauNode` retorna `null` sec quan `mode==='models'`: la fulla del
   catàleg no carrega res.
3. `:246-248` (`potConfirmar`) i `:308-325` (peu + `onPick`) assumeixen `mode==='models' → onPick(model)`:
   cal que `onPick` pugui tornar també un `GarmentTypeItem`.
4. `:172-183` (breadcrumb) i `:199-222` (doble clic) — retocs paral·lels.
5. `TechSheetEntry.jsx:40-68` — `obrir` té `model.id` **hardcodat** a `openTask`.

⚠️ **Bloqueig conceptual, no tècnic:** *una fitxa de catàleg no té model destí*. Per això **(a) i (b)
són la mateixa peça**: triar catàleg **obliga** a demanar destí.

**(b) "Obrir com a base d'un de nou" (destí + nom abans del canvas) — COST MITJÀ, motor ja fet.**
1. **Nom:** `usar_al_model` **hereta el nom de l'origen** (`views.py:214`,
   `nom=origen.nom_fitxer`) → cal acceptar un `nom` opcional al body (**1 línia**).
2. **Destí:** un segon pas d'UI (mini-form o segon `AssetNavigator`) → `usarAlModel(origen, destí)` →
   `navigate('/models/<destí>/ftt/<nouId>')`. **Precedent viu:** el selector "blanc | plantilla"
   (`App.jsx:165-186`) ja ramifica **abans** del canvas.
3. **Un tercer verb** a `TechSheetEntry` (`obrirComABase`) hi cap sense refactor. **Límit:**
   l'AssetNavigator **només té un botó d'acció** (`:317-325`) → o una prop `actions=[…]`, o
   **decidir l'acció FORA del navegador** (segmented control a `TechSheetEntry`) — 💡 aquesta segona
   **no toca `AssetNavigator` gens**.

**(c) Per al Taller, específicament:** el backend és viable (XOR ja fet), **però**
(i) **NO EXISTEIX cap `usar-al-model` per a `PatternFile`** (la llista d'`@action` de
`patterns/views.py:347-645` no en té cap de còpia); (ii) **`AssetNavigator` no sap llistar
`PatternFile`** (`CARREGA` hardcodat) → 💡 **PROPOSTA:** que el picker del Taller retorni
**model/ítem** (no fitxer) i deixi que `TallerPatro` resolgui el `PatternFile` **com ja fa**
(`TallerPatro.jsx:120-135`) — així **no cal tocar `AssetNavigator`**; (iii) cal crear la porta-menú,
calcant `TechSheetEntry`.

**Veredicte E: el picker de dues branques no s'ha de construir: s'ha de desbloquejar.**

---

# BLOC F — L'ESPAI D'ACCIONS DE L'EDITOR

*(àncores pre-F1; poden desplaçar-se)*

## F.1 Tres capes d'accions, dues amb array de config

| capa | línia | com es declara |
|---|---|---|
| **Topbar** (56 px) | pintat `:3564-3590` | JSX inline. Conté `saveLabel` (`:3582`) i **una única acció gold: Exportar PDF** (`:3583`) |
| **Barra de menús** (Fitxer/Edició/Objecte/Visualització) | `menuBar:3545-3550`; pintat `:3592-3606` | **array de config** + factory `menuItem(key,{label,shortcut,onClick,disabled})` (`:3484`), `menuSep` (`:3493`) |
| **Ribbon** (SolidWorks-like) | `ribbonTabs:3353-3358`; `renderRibbonContent():3414-3481`; pintat `:3608-3623` | **array de config** + factory `ribbonTool({key,icon,label,onClick,disabled,active,title})` (`:3380`) |

Grups del ribbon: **`file` · `page` · `insert` · `organize`** (`:3353-3358`) — **no hi ha grup
"format"** (viu al dock dret, `:4020+`). Ribbon i menú **comparteixen handlers** (comentari `:3483`).

## F.2 Accions de FITXER existents

Grup `file` del ribbon (`:3419-3426`) — només 4: **Exportar PDF** (`:3421` → `onExport:3018-3054`) ·
**Desar com a plantilla** (`:3422` → modal + `submitSaveAsTpl:3058-3068`) · **Autoguardat**
(indicador **mort**, `disabled:true`, `:3423`) · **Versió `v{n}`** (indicador, `:3424`).
Menú Fitxer (`menuFileItems:3496-3500`) — **només 3, i no coincideix amb el ribbon**: Exportar PDF ·
Desar com a plantilla · **Importar (croquis del tenant)** (`:3499`).
Al grup `insert` (`:3440-3453`): importar croquis (`:3446`), inserir imatge (`:3449`), **Fitxers del
model/catàleg** (`:3452` → `setFilePicker(true)`).

**Bloquejar/desbloquejar document: NO EXISTEIX com a acció d'usuari** — el lock és automàtic
(`:1860`, heartbeat `:1886-1896`, release `:1879`, `:1898-1912`).

## F.3 Patrons de diàleg reutilitzables (per al diàleg de promoció)

**Dropdowns:** sí — menú desplegable (`:3592-3606`, `menuOpen` + `data-menu`) i flyouts de la paleta
(`:3666-3697`).
**Modal:** **no hi ha component compartit** — la mateixa estructura (overlay `fixed inset-0` +
card, radius 12, `maxWidth 360`) està **copy-pasted 3 cops**:
- `pickFitting` (`:4336-4350`)
- `tablePicker` (`:4352-4409`) — **dues fases (tria de tipus → tria de destí)**: el més proper a un
  diàleg de promoció amb selecció
- **`saveAsTpl` (`:4413-4441`)** — form **nom + descripció** amb botó gold `disabled={!nom.trim()}`
  → 💡 **el patró exacte** per a "Duplicar cap a…" i "Desar com a sketch de família"

**Selectors d'entitat ja fets:** `AssetNavigator` (drawer amb tabs models/catàleg, arriba a
`garment_type_item`) i `FilePicker` (tabs `model|catalog|import`).

## F.4 Indicador de desat: existeix i es pinta a **tres** llocs

`saveState` (`null|'saving'|'saved'|'error'`, `:1321`) → `saveLabel` (`:3078`) → topbar (`:3582`),
ribbon (`:3423`), barra d'estat del peu (`:4318`). Badge de lock (`readonly|editing|locked_by|error`)
a `:3070-3077`, pintat al peu (`~:4305`).
**NO hi ha estat "canvis pendents"/dirty explícit:** passa a `'saving'` immediatament a cada canvi
(`:1957`). → **La bifurcació-primer haurà d'afegir la noció de "on estic desant"**, que avui no
existeix perquè la resposta sempre és òbvia.

## F.5 El que cal commutar en un "Duplicar cap a…"

| estat/ref | línia | rol |
|---|---|---|
| `{ id, fitxerId } = useParams()` | `:1301` | ruta model + document |
| `fttMode = !!fitxerId` | `:1306` | mode .ftt |
| **`fttHeadId = useRef(fitxerId)`** | **`:1404`** | **LA peça clau**: "cap de cadena vigent"; l'autosave hi fa PATCH i **s'hi reapunta** (`:1968`) |
| `sheet` / `setSheet` | `:1313` | ModelFitxer viu (d'ell surt `sheet.versio`) |
| `fttAssets` / `fttUrlToName` / `fttMeta` | `:1401-1403` | **s'han de reconstruir** en canviar de fitxer destí |
| `lockState` / `locked` | `:1320`, `:1363` | governa tota l'edició |
| `skipSave` | `:1399` | **caldrà tocar-lo** per no re-desar just després de commutar |

Un "duplicar cap a…" ha de: reassignar `fttHeadId.current` + `setSheet(nou)`, **alliberar el lock del
document antic i adquirir-lo al nou** (`ftt-documents/<id>/lock|unlock/`), i reconstruir els refs
d'assets. **NO EXISTEIX cap endpoint de "duplicar"/"promoure a item"** (`urls.py:177-182`).

## F.6 i18n

Bloc `tech_sheet` a `frontend/src/i18n/{ca,en,es}.json:2232-2512` — **279 claus, paritat exacta als
tres idiomes**. Ja existeixen `save_as_template*`, `autosave`, `saving`, `saved`, `save_error`,
`menu_file`. ⚠️ **`menu_duplicate` ja existeix però és duplicar OBJECTES (⌘D, `:3507`)** — no
reutilitzar la clau.

**Veredicte F: hi ha lloc i patró per a les dues accions noves.** El `saveAsTpl` és el motlle del
diàleg; el `tablePicker` és el motlle de la selecció en dues fases; `fttHeadId` és l'interruptor.

---

# TAULA FINAL — RISCOS I FIXOS MÍNIMS

| # | Fet | Gravetat | Evidència |
|---|---|---|---|
| 1 | **`unfreeze_document` no descongela les taules snapshot** (`table.snapshot.model_id`, `table.rows` amb POMs, `data_block.size_fitting_id`) → una còpia `.ftt` porta les mesures del model A al model B **en silenci** | 🔴 **BUG LATENT — prerequisit de tot** | `services_ftt_document.py:202-205` vs disc (`model_id:188`, `size_fitting_id:52`) |
| 2 | Encara **no ha fet mal**: 0 files amb `derivat_de_model`/`derivat_de_item` | ✅ marge per arreglar-ho abans | `SELECT` (0 rows) |
| 3 | El camí **item→model no descongela** el `.ftt` (asimetria amb model→model) i la docstring que ho justifica és **falsa** | 🔴 **fix mínim, codi ja existent** | `item_fitxer_views.py:140-142,165-170` vs `views.py:176-181,208-218` |
| 4 | Un `.ftt` pujat a un item queda `tipus='ALTRES'` → la còpia **no s'obre com a fitxa** (404) | 🟠 **fix mínim** (`create` ja accepta `tipus`) | `services_fitxers.py:168`, `ftt_document_views.py:87-90`, `item_fitxer_views.py:83` |
| 5 | **Churn de versions: 225 files / 6 documents** (90 en 2 dies) | 🟠 el problema que la bifurcació-primer resol | `SELECT` + `services_ftt_document.py:342-347` |
| 6 | **Sobreescriure (Path 2): NO EXISTEIX** — 2 punts d'intervenció, cap toca `save_model_file` | 🟡 dimensionat | `services_fitxers.py:128`, `views.py:147-150` |
| 7 | ⚠️ `FileField.save()` in-place **deixa els bytes vells orfes** → cal `delete_fitxer_bytes` | 🟠 **parany del Path 2** | `views.py:163-167` |
| 8 | Duplicar dins el mateix model: **prohibit per 1 línia** | 🟢 fix trivial | `views.py:201-203` |
| 9 | Nom del `.ftt`: **no editable, sense component descriptiu** | 🟡 el disseny de noms composts no xoca amb res | `services_ftt_document.py:90-92` |
| 10 | **Promoció model→item: NO EXISTEIX** (forat amb nom, diferit) | 🟡 a construir | `item_fitxer_views.py:144` |
| 11 | **Cap superfície `.ftt` per a item** (ni detail, ni lock, ni `asset/`) → un sketch d'item **no es pot editar ni pintar imatges** al catàleg | 🟠 decisió d'abast | `urls.py:176-182` |
| 12 | `.ftt` i `.svg` **ja a la whitelist** | ✅ cap fix | `services_fitxers.py:37,40` |
| 13 | **Les dues branques del picker ja existeixen**, apagades per `mode` | ✅ desbloquejar, no construir | `AssetNavigator.jsx:271-285` |
| 14 | `AssetNavigator` **no sap llistar `PatternFile`**; el peu **només té 1 botó d'acció** | 🟡 esquivable (que el picker torni model/ítem) | `AssetNavigator.jsx:28-38, 317-325` |
| 15 | **Cap `usar-al-model` per a `PatternFile`** | 🟡 a construir si el Taller-GTI ho vol | `patterns/views.py:347-645` |
| 16 | El que el disseny vol promocionar (`sketch_svg`, `path`, `field`, `header`) **és tot ESTRUCTURA PURA** | 🎁 **la promoció de sketches és viable i neta** | taula §D.6 |

---

# DIMENSIÓ HONESTA (sessions)

> Una "sessió" = un sprint de Patró B amb el verd (check + build + lint) a cada peça.

### 🔴 SESSIÓ 0 — **FIX PREREQUISIT: que la re-resolució no menteixi** (~1 sessió)
Estendre `unfreeze_document` a les taules snapshot i al `graded_table` (`services_ftt_document.py:233-271`)
+ **simetritzar el camí d'item** (`item_fitxer_views.py:165-170` → cridar `es_ftt`/`reescriure_ftt_per_model`
com fa `views.py:208-218`) + `tipus` correcte a l'upload d'item.
**Per què primer:** la promoció i el "duplicar cap a un altre host" **es basen en aquesta funció**.
Amb 0 còpies a la BD, ara és gratis; després de la primera promoció, ja no.
**Decisió (Patró C):** ¿què fa `unfreeze` amb una taula snapshot — **l'esborra**, la **buida deixant
l'estructura**, o la **marca com a òrfena** perquè el tècnic la reompli al destí? 💡 Recomanació:
**buidar deixant l'estructura** (és el que un sketch de biblioteca vol: la graella, no les xifres).

### (1) BIFURCACIÓ-PRIMER (~1,5-2 sessions)
Backend: `overwrite_document` germà + tria a la PATCH (⚠️ amb `delete_fitxer_bytes`) · treure el
guard de `views.py:201-203` · `nom` opcional a `usar_al_model`.
Frontend: commutació de `fttHeadId`/`sheet`/lock/assets · acció "Duplicar cap a…" (motlle `saveAsTpl`)
· **indicador de "on estic desant"** (avui no existeix perquè mai calia) · i18n×3.

### (2) SKETCHES `.ftt` A GTI (~2 sessions, o ~1 si es retalla)
Pujar extern SVG: **ja funciona** (whitelist ✅). Importar a model: **funciona després de la Sessió 0**.
**El cost real és la decisió d'abast:** ¿els sketches d'item només s'han de **descarregar/importar**
(barat: 0 endpoints nous) o també **editar dins el catàleg** (car: cal tota la superfície `.ftt` per a
item — detail, lock, `asset/`)? 💡 **Recomanació: la versió barata primer** — la biblioteca dona valor
encara que el sketch només s'editi dins un model.

### (3) PROMOCIÓ MODEL→GTI AMB SELECCIÓ (~1,5 sessions, **després de la Sessió 0**)
Endpoint nou model→item + diàleg de selecció (motlle `tablePicker`, dues fases). **La taula §D.6 és el
menú literal.** Defecte natural: **estructura sí, taules no**.

### (4) PORTA-PICKER DEL TALLER (~1 sessió)
**Desbloquejar** el fork de branques de `AssetNavigator` (`:271`) + `clauNode` (`:133-137`) + `onPick`
d'ítem + entrada al Sidebar (1 línia) + ruta + porta calcada de `TechSheetEntry`.
💡 **Esquiva recomanada:** que el picker torni **model/ítem** (no fitxer) i deixi que `TallerPatro`
resolgui el `PatternFile` **com ja fa** → **no cal tocar `CARREGA` ni ensenyar `PatternFile` a
l'AssetNavigator**.

**Ordre:** **0 → (1) → (4) → (2) → (3)**. La Sessió 0 desbloqueja (1) i (3); (4) és independent i
barata; (3) és l'única que **exigeix** que (0) estigui feta.

---

*Fi de la diagnosi. Cap línia de codi tocada. Les decisions són humanes (Patró C).*
