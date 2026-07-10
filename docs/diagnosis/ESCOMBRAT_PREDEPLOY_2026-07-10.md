# ESCOMBRAT PRE-DEPLOY — 2026-07-10

> **Patró A (READ-ONLY).** Staging `/var/www/ftt-staging`, branca `dev`, HEAD `02aa0b4`.
> Cap escriptura de codi, cap migració, cap restart. Convenció: `fitxer:línia`.
> **"NO EXISTEIX" = confirmat absent al codi**, no especulat. Propostes només com `💡`.

---

## Resum executiu — ordenat per risc de deploy

| # | Troballa | Surt a client? | Estat | Esforç |
|---|---|---|---|---|
| **B1** | **CP + ciutat duplicats a la capçalera de TOTS els documents comercials** | 🔴 **SÍ** | Confirmat amb evidència | trivial (dada) |
| **B2** | **Un client sense adreça imprimeix una línia solitària `ES`** | 🔴 **SÍ** | Confirmat amb evidència | trivial |
| **A2** | `media/<schema>/items/` de root a **PROD** → tot upload de catàleg dona 500 | ⚠️ funcional | **NO verificable des d'aquí** | trivial |
| **A4** | D14 · `FittingPhoto` servida per `/media/` cru, **sense cap gate** | 🔴 fuga de bytes | Pendent, intacte | sprint propi |
| **A5** | `validate_upload` cobreix **2 de 6** camins que escriuen bytes | ⚠️ | Pendent | curt |
| **A3** | Obrir la fitxa encadena una versió nova del `.ftt` (cadenes de v90) | ⚠️ intern | Causa **confirmada** | curt |
| **A6** | 2 idiomes d'esborrat de bytes; **cap tercer nou** aquesta setmana | — | Estable | — |
| **A1** | Fantasma id=6 · 8 orfes · cadena 32-36 | — | ✅ **Resolts, re-verificats** | — |

**Els dos únics ítems que afecten paper que arriba al client són B1 i B2, i tots dos són al mateix
fitxer.** Tots dos són corregibles avui.

---

# BLOC B — El cas del CP / ciutat

## B0 — Correcció de partida: no és un client, és l'EMISSOR

El brief parlava d'un client (*"BROADO"*). **Cap client té adreça a staging**: els tres `Customer`
tenen `adreca_linia1`, `adreca_linia2`, `ciutat` i `codi_postal` **buits**. La duplicitat que s'ha
vist en un document imprès és a la **capçalera de l'emissor** (FHORT MANAGEMENT SL), que surt a
tots els documents.

```
Customer BRW «Textiles y Confecciones Brownie SL» → l1='' l2='' cp='' ciutat='' pais='ES'
Customer LOS «LOSAN IBERIA SA»                    → l1='' l2='' cp='' ciutat='' pais='ES'
Customer FTT «FHORT Textile Tech»                 → l1='' l2='' cp='' ciutat='' pais='ES'
```

## B1 — 🔴 Duplicitat per DOBLE FONT (la hipòtesi del brief, confirmada)

**No és un bug de bucle ni de plantilla. És doble font de dades.** `TenantConfig.address` ja conté
el CP i la ciutat sencers, i el generador hi torna a concatenar `postal_code` + `city`:

**Dada real** (`TenantConfig`, schema `fhort`):
```
address     = 'Salmerón 165, 08222 Terrassa'   ← ja porta CP + ciutat
postal_code = '08222'
city        = 'Terrassa'
country     = 'ES'
```

**Codi** — `backend/fhort/commerce/pdf_service.py:135-140`:
```python
def _emissor_oneliner(cfg):
    loc = ' '.join(x for x in [(cfg.postal_code or '').strip(), (cfg.city or '').strip()] if x)
    return ', '.join(x for x in [(cfg.address or '').strip(), loc, (cfg.country or '').strip()] if x)
```

**Sortida real, executada contra la BD de staging:**
```
'Salmerón 165, 08222 Terrassa, 08222 Terrassa, ES'
                └──── de address ────┘  └─ de postal_code+city ─┘
```

### Abast: sistèmic, una sola capçalera base

`_emissor_oneliner` es crida un sol cop, des de la capçalera compartida
`backend/fhort/commerce/pdf_service.py:179` (dins `_emissor_header`, docstring a `:170-171`:
*"Compartida per generate_document_pdf i _delivery_note"*). Per tant afecta **els tres documents**
que el sistema imprimeix, tots amb la mateixa línia duplicada:

| Document | Generador | Crida |
|---|---|---|
| Pressupost | `generate_quote_pdf` → `generate_document_pdf(doc_title='Pressupost')` | `pdf_service.py:201-203`, invocat a `commerce/views.py:144-145` |
| Comanda | `generate_document_pdf(order, doc_title='Comanda')` | `commerce/views.py:193-194` |
| Albarà | `generate_delivery_note_pdf` | `pdf_service.py:385`, invocat a `commerce/views.py:447-448` |

**Es corregeix en UN lloc, no en diversos.**

### Per què la dada és així: la UI ho convida

`frontend/src/pages/GeneralConfig.jsx:143-155` presenta tres camps independents amb etiquetes
`config_general.address` = **"Adreça"**, `postal_code` = "Codi postal", `city` = "Ciutat".
"Adreça", sense qualificar, convida a escriure-hi l'adreça sencera. No hi ha cap validació ni cap
pista que digui "només carrer i número".

### 💡 Proposta (NO aplicada)

Tres nivells, del més barat al més robust. **El primer sol ja treu la duplicitat del deploy d'avui.**

1. **Dada (trivial, zero codi, zero risc):** `TenantConfig.address = 'Salmerón 165'`. La capçalera
   passa a `'Salmerón 165, 08222 Terrassa, ES'`, que és el que es volia.
2. **Etiqueta (trivial):** `config_general.address` → "Adreça (carrer i número)" a ca/en/es, perquè
   no torni a passar. Cap canvi de model.
3. **Codi (curt):** ⚠️ **no recomano** "detectar si `address` ja acaba amb el CP i no repetir-lo":
   és una heurística sobre text lliure i falla amb `08222 Terrassa` vs `Terrassa 08222` vs accents.
   Si es vol defensa al codi, la manera honesta és **partir el camp** (`address_linia1`/`linia2`,
   com ja fan `Customer` i `Supplier` a `tasks/models.py:169-171` i `:211-213`) i migrar la dada.
   Això és **sprint propi**, no feina de pre-deploy.

## B2 — 🔴 Segon bug, independent: la línia solitària `ES`

`_customer_oneliner` (`backend/fhort/commerce/pdf_service.py:116-125`) filtra els buits amb `if x`,
però **`pais` mai és buit**: té `default='ES'` (`tasks/models.py:172` per a `Supplier`,
`tasks/models.py:216` per a `Customer`).

Amb un client sense dades fiscals — **els tres de staging, avui** — el resultat és:

```python
_customer_oneliner(Customer.objects.get(codi='BRW'))  →  'ES'
```

I com que `pdf_service.py:276` fa `if oneliner:` (i `'ES'` és truthy), sota el nom del client
s'imprimeix una línia grisa que diu, literalment, **`ES`**:

```
Per a:
Textiles y Confecciones Brownie SL
ES                                  ← això surt al PDF
```

Punts d'impressió: `pdf_service.py:275-277` (Pressupost i Comanda) i `pdf_service.py:439-441`
(Albarà) — el mateix bloc duplicat literalment a dos llocs.

> **Aquest bug afecta ARA MATEIX tots els documents de tots els clients de staging**, perquè cap
> client té adreça. És més visible que B1 i no s'havia reportat.

### 💡 Proposta (NO aplicada)

El país no hauria de sortir sol quan no hi ha adreça. Mínim honest, a `_customer_oneliner`:
construir `addr` amb els camps d'adreça i **afegir-hi `pais` només si `addr` ja té contingut**.
Mateix criteri a `_emissor_oneliner` (`:140`), on `country` té el mateix problema latent.

Nota addicional: `pais`/`country` són codis ISO-3166 alpha-2 (`tasks/models.py:172`), i s'imprimeixen
en cru (`ES`). Mostrar el codi en lloc del nom del país és una decisió de producte, no un bug —
**s'anota, no es toca**.

---

# BLOC C — Escombrat de "sortida cap a client"

## C1 — Altres duplicitats de camp: **cap més**

Revisats tots els punts on `pdf_service.py` compon text a partir de més d'un camp:

| `fitxer:línia` | Què compon | Duplicitat? |
|---|---|---|
| `pdf_service.py:119-120` | adreça del client | **B2** (país solitari) |
| `pdf_service.py:139-140` | adreça de l'emissor | **B1** (CP+ciutat) |
| `pdf_service.py:185-186` | `email · phone` de l'emissor | ✅ net |
| `pdf_service.py:358` | `%IVA · data de venciment` | ✅ net |
| `pdf_service.py:459` | `temporada + any` del model (albarà) | ✅ net |

- **NIF:** s'imprimeix un sol cop per entitat — emissor a `:182-184`, client dins l'oneliner a `:123-124`. Sense duplicitat.
- **Nom:** `legal_name or nom_empresa` (`:180`) i `rao_social or nom` (`:274`, `:438`) — fallback, no duplicitat.
- **Telèfon:** només a `:185`.
- **Referència de comanda / adreça d'enviament:** **NO EXISTEIX** cap segona adreça al model
  d'albarà (`grep` sobre `commerce/models.py`: cap camp `shipping`/`delivery_address`).

## C2 — Exports PDF de la fitxa tècnica: intactes

Els 7 commits d'avui (`5c9a7a2`..`02aa0b4`) toquen `TechSheetEditor.jsx` (+70/-4), però
**cap línia afegida o treta toca l'export PDF** (`exportPdf` / `pdf-lib` / `PDFDocument`):
verificat amb `git diff 5c9a7a2~1..02aa0b4 -- frontend/src/pages/TechSheetEditor.jsx`.
`npm run build` net. Res a re-diagnosticar.

## C3 — Concatenació manual per a documents

Els únics llocs on es construeix text de document per concatenació (en lloc de plantilla) són els
cinc de la taula C1. **Dos dels cinc són precisament els dos bugs de Bloc B** — el patró és fràgil
exactament allà on el brief sospitava. Cap altre generador de documents al backend:
`fhort/backoffice/` no té cap PDF (`Invoice`/`ContractLine` són només dades, `billing_service.py`),
i `pom/s2_views.py:322` només parla de reportlab en un comentari.

---

# BLOC A — Inventari de pendents coneguts

## A1 — Fantasma id=6 · 8 orfes · cadena 32-36 → ✅ **RESOLTS** (re-verificat avui)

Comprovat contra la BD i el disc, no de memòria:

```
ModelFitxer id=6                     → no existeix
ids 32-36 (cadena BRW-FW26-0004)     → cap
media/model_fitxers/ (arrel antiga)  → no existeix
directori de quarantena              → cap
audit_fitxers --schema fhort         → 228 a BD, 228 a disc, 0 fantasmes, 0 orfes, 0 cadenes invàlides
```

`audit_fitxers` és de fiar des del commit `0a71cc5` d'avui (abans comparava dos espais de noms i
donava 100% de falsos positius).

## A2 — 🔴 `media/<schema>/items/` a PROD — **NO VERIFICABLE DES D'AQUÍ**

A staging el directori era de `root`, i com que gunicorn corre com `www-data`, **tot upload de
fitxer de catàleg donava 500 `PermissionError`**. Aquesta és la raó per la qual `ItemFitxer` tenia
**0 files des de sempre**: el camí no havia funcionat mai. Corregit avui a staging (`chown`).

**PROD no és abastable des d'aquest host** (`/var/www/` només conté staging i altres projectes;
no hi ha entrada de PROD a `~/.ssh/config`). Per tant **no puc confirmar ni desmentir** que hi
tingui el mateix forat. Com que ningú no ha pujat mai un fitxer de catàleg amb èxit, **el més
probable és que el directori ni tan sols existeixi a PROD** i es creï amb l'owner del procés que
el creï primer.

**💡 Comanda per a l'Agus, des de PROD, abans del deploy:**
```bash
ls -ld <MEDIA_ROOT>/<schema>/items 2>/dev/null || echo "no existeix (es crearà)"
# si existeix i és de root:
sudo chown -R www-data:www-data <MEDIA_ROOT>/<schema>/items
```
`move_media_tenant` ja fa `chown` dels directoris que crea des de S03c-1 · C1.4 (`ace8922`), però
això **no cobreix un directori creat abans** d'aquell commit.

## A3 — Cadena v1→v13 en obrir la fitxa: **causa confirmada** (i la meva hipòtesi d'ahir era falsa)

La sospita anotada ahir (*"`documentToV2` muta `pages`"*) és **FALSA**: `documentToV2` és pur
(`TechSheetEditor.jsx:286-301`), i `convertLegacySketchSvgs` retorna la mateixa referència quan no
hi ha SVG legacy (`:1265`). Tampoc hi ha remuntatge: el PATCH reapunta el cap in-place
(`:1969`), sense `navigate`.

**La causa real és l'ORDRE DELS DOS GUARDS de l'effect d'autosave**
(`TechSheetEditor.jsx:1955-1957`):

```python
useEffect(() => {
  if (skipSave.current) { skipSave.current = false; return }   # ← :1956  es consumeix SEMPRE
  if (!locked) return                                          # ← :1957  ...encara que no hi hagi lock
  ...
}, [pages, locked, pageFormat])                                # ← :1974
```

Seqüència exacta:

1. `skipSave = true` (`:1400`). L'effect corre en muntar → **consumeix `skipSave`** i retorna.
2. L'effect de càrrega (`:1827`) llança **dues** fetch independents: GET del document (`:1846`) i
   POST del lock (`:1861`).
3. Arriba el GET → `hydrate` reposa `skipSave = true` (`:1918`) i fa `setPages` (`:1925`) →
   l'effect corre → **torna a consumir `skipSave`** i retorna (encara no hi ha lock).
4. Arriba el POST del lock, **en un tick separat** → `setLockState('owned')` (`:1864`) →
   `locked` passa a `true` (`:1364`) → l'effect corre un cop més.
5. Ara `skipSave` ja està consumit i `locked` és `true` → **passa** i programa el PATCH,
   **sense que l'usuari hagi tocat res**.
6. El backend encadena versió **incondicionalment**: `FttDocumentDetailView.patch`
   (`backend/fhort/models_app/ftt_document_views.py:104-125`) crida `svc.save_document` (`:122`)
   → `save_model_file(..., versio_anterior=head)` (`services_ftt_document.py:342-347`).
   **No hi ha cap comparació de contingut.**

### Abast real a staging (mesurat, no estimat)

| model | versions `.ftt` | `versio` màx |
|---|---|---|
| 174 | **90** | 90 |
| 167 | **86** | 86 |
| 162 | 26 | 26 |
| 188 | 18 | 18 |
| 182 | 2 | 2 |
| 186 | 2 | 2 |

**224 dels 228 `ModelFitxer` (98%) són versions de fitxa tècnica**, i **218 són versions superades**.
Impacte a disc: **2,8 MB** de 12,1 MB totals — molest, no crític (els `.ftt` són petits; els 9 MB
restants són 2 PDF i 1 xlsx). El dany real és **semàntic**: la fitxa mostra "v90" a l'usuari, i les
files creixen sense sostre.

> Hi ha **dos amplificadors** i cal no confondre'ls:
> **(a)** obrir la fitxa sense editar crea una versió — el bug de l'ordre dels guards;
> **(b)** cada autosave (cada 2 s d'edició) crea una versió — **és el disseny actual**
> (`ftt_document_views.py:122` encadena sempre). Una sessió d'edició de 5 minuts pot crear desenes
> de versions encara que (a) es corregeixi.

### 💡 Proposta (NO aplicada)

- **(a) — curt, quirúrgic:** intercanviar les línies `:1956` i `:1957`. Amb `if (!locked) return`
  primer, els renders anteriors al lock ja no consumeixen el flag, i el primer render *amb* lock el
  consumeix i no desa. Funciona també si el lock arriba abans que el document.
- **(b) — sprint propi, decisió de producte:** decidir si tot autosave ha de crear versió, o si la
  versió s'ha de crear en fites conscients (tancar, exportar, "Desar versió") amb autosave in-place
  al cap de cadena. **No és feina de pre-deploy** i toca `save_document`, que és font única.
- Cap de les dues corregeix les cadenes ja existents; una neteja d'històric seria una tercera peça,
  i `audit_fitxers` ja garanteix que no hi ha ni orfes ni fantasmes.

## A4 — D14 · `FittingPhoto`: el forat de servei **segueix OBERT**

La sessió de fitting paral·lela **no l'ha tocat**: `git log -8 -- backend/fhort/fitting/` no conté
cap commit sobre `FittingPhoto`, el seu serializer ni el servei de bytes.

- Model: `backend/fhort/fitting/models.py:362`, camp `fitxer = models.ImageField(upload_to='fitting_photos/%Y/%m/')` a `:374`.
- El serializer exposa la **URL crua**: `backend/fhort/fitting/serializers.py:68` (camp `fitxer` dins `fields`).
- nginx serveix `/media/` **en cru, sense auth**: `/etc/nginx/sites-enabled/ftt-staging:51`
  (`location /media/ { alias ...; }` — no és `internal`). El camí gated `/protected-media/` (`:56`)
  **sí** és `internal` i només s'hi arriba per `X-Accel-Redirect` des de `serve_fitxer`.
- `FittingPhotoViewSet` (`backend/fhort/fitting/views.py:571-582`) **no té** `download` ni
  `download_signed`, i **no crida mai** `serve_fitxer`.

**Conseqüència:** qualsevol foto de fitting és descarregable per `https://…/media/fitting_photos/AAAA/MM/<nom>`
sense JWT, sense token signat i sense aïllament de tenant al servei de bytes. És exactament el forat
que D13 va tancar per a `ModelFitxer`/`ItemFitxer`.

**Esforç: sprint propi** (endpoint gated + `download_signed` amb salt propi + canviar el consumidor
del frontend perquè deixi d'usar la URL crua). Té dependència amb A5 (tampoc valida l'upload).

## A5 — `validate_upload`: cobreix **2 de 6** camins que escriuen bytes

`validate_upload` viu a `backend/fhort/models_app/services_fitxers.py:54` (guard D12/D18: whitelist
d'extensió + sostre de 20 MB). Grep exhaustiu de `request.FILES`, `FileField`/`ImageField`
escrivibles i `parser_classes`:

### Escriuen bytes a un FileField

| Punt d'entrada | `validate_upload`? | Gate |
|---|---|---|
| `models_app/views.py:1204` `upload_file_view` (validate a `:1225`) | ✅ **SÍ** | `IsAuthenticated` |
| `models_app/item_fitxer_views.py:57` `create` (validate a `:69`) | ✅ **SÍ** | **CONFIGURE** |
| `fitting/views.py:571` `FittingPhotoViewSet.create` | ❌ **NO** | `IsAuthenticated` |
| `tasks/views_b.py:732` `upload_logo` (logo de Customer) | ❌ **NO** | CONFIGURE |
| `pom/s2_views.py:298` `tenant_config_view` (logo del tenant) | ⚠️ **parcial** | `IsAuthenticated` |
| `models_app/ftt_document_views.py:175` `save-export` | ❌ **NO** | `IsAuthenticated` |
| `models_app/extraction_views.py:289` cribratge | ❌ **NO** | `IsAuthenticated` |

- El logo del tenant passa per `normalize_logo` (`accounts/logo.py:31`), que comprova que és una
  imatge decodificable i acota la dimensió, però **no** aplica ni la whitelist d'extensió ni el
  sostre de mida de `validate_upload`. Per això "parcial", no "sí".
- El comentari de `services_fitxers.py:38` ja avisava de **no copiar el forat de
  `Customer.upload_logo`, que no valida res**. Segueix sense validar (`tasks/views_b.py:732`).

### Llegeixen bytes però NO persisteixen a FileField (risc menor)

`bulk_import_views.py:57`, `tech_sheet_views.py:63`, `chat_views.py:52`, `pom/s9_views.py:87`,
`pom/size_map_views.py:450`, `pom/dictionary_views.py:58`. Alguns duen check ad-hoc propi
(`.xlsx/.xls`, o content-type + 20 MB), cap reutilitza `validate_upload`.

**NO EXISTEIX** cap backoffice amb backend propi: tots els punts d'upload viuen dins `backend/fhort/`.

**Esforç: curt** per als tres que escriuen a FileField sense cap validació
(`FittingPhoto`, `upload_logo`, `save-export`) — és endollar-hi el guard que ja existeix.

## A6 — Asimetria de neteja de bytes: **2 idiomes, cap de nou**

| Idioma | Ocurrències |
|---|---|
| `default_storage.delete(name)` | `models_app/services_fitxers.py:221` (dins `delete_fitxer_bytes`, font canònica, amb guard `exists()` i `try/except`) · `models_app/extraction_views.py:70` (directe) |
| `<FieldFile>.delete(save=False)` | `tasks/views_b.py:740` (logo de Customer) · `pom/s2_views.py:329` (logo del tenant) |

`delete_fitxer_bytes` la criden els dos `perform_destroy` de fitxers
(`item_fitxer_views.py:54`, `views.py:165`).

**Cap tercer idioma nou aquesta setmana.** Verificat: **NO EXISTEIX** cap `os.remove`,
`shutil.rmtree` ni `pathlib.unlink` sobre `media` (l'únic `os.unlink`, `pom/s9_views.py:200`, opera
sobre un `NamedTemporaryFile`), i **cap senyal `post_delete` esborra fitxers** (els dos que hi ha,
`commerce/signals.py:24` i `:42`, només recalculen totals).

L'asimetria resta acotada als logos i és **pre-existent**. S'anota, no urgeix.

---

## Què faria abans del deploy d'avui, i què no

**Sí, ara (minuts):**
1. **B1** — corregir la dada: `TenantConfig.address = 'Salmerón 165'`. Treu la duplicitat dels tres documents.
2. **B2** — el fix del país solitari a `_customer_oneliner`. És l'únic canvi de codi que recomano
   per a avui, i és de dues línies. Sense ell, **tots** els PDF de client segueixen imprimint `ES`.
3. **A2** — comprovar `items/` a PROD amb la comanda de dalt.

**No, ara:** A3(b), A4 i A5 són peces pròpies. A4 és el més greu dels tres (fuga de bytes sense
gate), però no es tapa amb una línia i no s'ha de fer a corre-cuita el mateix dia del deploy.

**Anotat, sense tocar:** el codi ISO del país imprès en cru; els 218 `.ftt` superats a staging;
l'asimetria de logos (A6).
