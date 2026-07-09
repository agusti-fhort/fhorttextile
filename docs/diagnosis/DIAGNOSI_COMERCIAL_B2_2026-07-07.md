# DIAGNOSI — Comercial Studio B2: terreny per a Quote/QuoteLine, numeració i PDF

Data: **2026-07-07** · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`.

**Abast:** terreny real abans del disseny fi de **B2** (documents del mòdul Comercial):
estructura de línies (Quote/QuoteLine), generació de número de document, pipeline PDF,
estat del git de B1, i patró de wizard oferta→comanda. B1 (mestre d'articles) ja és a
`origin/dev`; B2 encara **NO EXISTEIX** al codi (`commerce/models.py:4-5`).

**Convenció:** `fitxer:línia` = ancorat i verificat · `"NO EXISTEIX"` = confirmat absent al
codi (no especulat) · `💡 PROPOSTA (a validar)` = disseny, decisió humana (Patró C).

---

## Resum executiu (director)

1. **B1 pujat net — no hi ha bloquejador (gate del punt 4 superat).** Tip autoritari del
   remot (`git ls-remote origin refs/heads/dev`) = `8731d8d`; els dos extrems de la cadena
   `a10f39f`(B1-P1)..`95a17ab`(B1-P6) són a `origin/dev`, més 3 commits size-map a sobre.
   Cap unmerged path. **⚠️ Únic residu:** `frontend/public/CALLIE.svg` és **untracked (no a
   git)**; l'usa una pàgina POC (`PaperKonvaPoc.jsx`), **no** B1-P6 → risc menor, no bloca B2.

2. **El repo NO té cap herència abstracta ni mixin — sempre duplica camps comuns.**
   `grep "abstract = True"` a tot el backend → **zero** (`NO EXISTEIX`). Ja hi ha 5 parelles
   header+línia (Invoice/InvoiceLine, TenantContract/ContractLine, Contracte/LiniaContracte,
   SizeCheck/SizeCheckLine, PieceFitting/PieceFittingLine), totes per duplicació + FK
   `related_name='lines'/'linies'`. Quote/QuoteLine encaixa en aquest patró de la casa.

3. **Existeix un comptador atòmic reutilitzable (`ModelSequence` + `reserve_sequence_range`
   amb `select_for_update`), però acoblat a (customer, any, temporada)** i sense generador
   genèric de número de document. A més ja hi ha **dos formats divergents** de codi al mateix
   repo (signal `BRW-26-SS-0002` vs views `BRW-SS26-0002`). B2 necessita **peça nova** de
   sèrie per tipus+any, calcada del patró segur de `ModelSequence`.

4. **No hi ha cap generador de PDF al backend** (només `Pillow`; `reportlab` és al `.lock`
   però mai importat). El pipeline B0 (fitxa tècnica) és **client-side Konva→PNG→pdf-lib**,
   raster pur sense text vectorial ni taules paginables, i el propi B0 el declara **NO
   reutilitzable** per a documents comercials estructurats (`DIAGNOSI_COMERCIAL_B0…:40-42,
   315-316`). B2 necessita **motor PDF nou** (decisió pendent de l'Agus).

5. **El wizard oferta→comanda NO EXISTEIX**, però hi ha precedents forts de
   confirmació+congelació reaprofitables: `ModelWizard` (stepper amb gate), `clone_model_for_qa`
   (clona registre + fills amb `pk=None`), `close_base`/`'Tancat'`, `bump_grading_version`,
   `seal_model_grading` (`aprovada`) i `PlanSnapshot` (previsió immutable).

---

## BLOC 1 — Estructura de línies (Quote/QuoteLine vs SalesOrder/SalesOrderLine)

**El patró de la casa és DUPLICACIÓ, no herència.**
- `grep -rn "abstract = True" backend/fhort` → **cap resultat**. Base abstracta / mixin propi
  (TimeStamped/Auditable/Base*) a tot el backend: **NO EXISTEIX**. L'únic mixin usat és extern
  (django-tenants): `Client(TenantMixin)` `tenants/models.py:58`, `Domain(DomainMixin)` `:213`.
- Cada model gran declara els camps comuns inline, amb **naming inconsistent entre apps**:
  `created_at/updated_at` (anglès, `commerce/models.py:78-79`, `tasks/models.py:88-89`),
  `creat_at/actualitzat_at` (`accounts/models.py:43-44`, `planning/models.py:31-32`),
  `data_creacio/darrera_actualitzacio` (`fitting/models.py:37`, `pom/models.py:602`). Tres
  variants del mateix concepte. `created_by` també copiat per-model (`models_app/models.py:218,
  488,547,591,787,856`). No hi ha camp `tenant` (aïllament per esquema).

**Parelles header+línia ja existents (precedent directe per Quote/QuoteLine):**
| Header | Línia | FK + related_name |
|---|---|---|
| `Invoice` `backoffice/models.py:147` | `InvoiceLine` `:186` | `invoice`→CASCADE `related_name='lines'` `:189` |
| `TenantContract` `backoffice/models.py:103` | `ContractLine` `:124` | `contract`→CASCADE `related_name='lines'` `:128` |
| `Contracte` `models_app/models.py:14` | `LiniaContracte` `:29` | `contracte`→CASCADE `related_name='linies'` `:30` |
| `SizeCheck` `models_app/models.py:770` | `SizeCheckLine` `:806` | `size_check`→CASCADE `related_name='linies'` `:808` |
| `PieceFitting` `fitting/models.py:291` | `PieceFittingLine` `:337` | `piece_fitting`→CASCADE `related_name='linies'` `:342` |
| `Product` `commerce/models.py:37` | 4 satèl·lits (recipe/suppliers/components/price) | `product`→CASCADE `related_name='…_lines'` `:97,123,146,177` |

- El mestre B1 ja fixa la llei de naming: **BD/codi en ANGLÈS** (`commerce/models.py:8`) → per
  a B2, `lines` (anglès) i no `linies`.

**💡 PROPOSTA (a validar) — dues vies, amb pros/contres concrets:**

*Via A — seguir la casa: models concrets duplicats (Quote+QuoteLine, i demà SalesOrder+…).*
- ✅ Consistent amb 100% del repo; zero risc de paradigma; migracions trivials; cada doc pot
  divergir camps sense trencar germans.
- ❌ Duplicació multiplicada per 5 tipus de document (Quote/SalesOrder/WorkOrder/DeliveryNote/
  Settlement, `commerce/models.py:5`): capçalera (número, dates, customer, estat, totals) i
  línia (product, qty, preu, descripció) es re-declararan ~5 cops → deriva de naming/camps.

*Via B — introduir la PRIMERA abstracta del repo: `AbstractDocument` + `AbstractDocumentLine`.*
- ✅ Els 6 documents comparteixen capçalera/línia des d'un sol lloc; el pipeline
  oferta→comanda→albarà (que copia línies entre docs, §BLOC 5) treballa contra una interfície
  única; talla la deriva de naming d'arrel.
- ❌ **Trenca el paradigma actual** (cap abstracta existeix) → requereix decisió humana
  explícita (Patró C); una abstracta mal dimensionada és cara de desfer un cop hi ha 6
  subclasses i dades.

**Recomanació de terreny (a validar):** com que B2-B5 obriran **una família de 6 documents amb
capçalera+línia gairebé idèntica**, és l'únic lloc del repo on una abstracta es paga sola.
Proposta: `AbstractDocument`/`AbstractDocumentLine` **només dins `commerce/`** (no toca el nucli
tècnic), amb Quote/QuoteLine com a primera subclasse i SalesOrder/SalesOrderLine (B3) com a
segona. Si es prefereix minimitzar risc a B2, Via A per a Quote i extreure l'abstracta quan
entri el 2n document. Decisió de l'Agus.

**Veredicte BLOC 1:** patró header+línia **llest i sobradament precedit**; l'única decisió
oberta és *duplicar (Via A) vs primera abstracta `commerce`-local (Via B)*. Naming: `lines`
(anglès), FK CASCADE, `related_name='lines'`.

---

## BLOC 2 — Numeració de documents

**Ja hi ha generació de codi, en TRES camins i DOS formats incompatibles:**

1. **Signal manual** `models_app/signals.py:16-80` → format **`{CUST}-{YY}-{TT}-{NNNN}`**
   (p.ex. `BRW-26-SS-0002`): `codi_intern = f"{client_code}-{year2}-{temporada}-{seq4}"` `:80`.
   Comptador = `SELECT MAX(sequencial) WHERE customer,any,temporada` `:59-68`. **NO
   concurrency-safe** (scan MAX sense `select_for_update`; el propi codi ho admet a
   `services.py:47-48`). El tag `[QA-SC]` **no** és part del codi (va a `nom_prenda`,
   `clone_model_for_qa.py:78`).
2. **Endpoints API** `models_app/views.py:238,354` → format **`{CUST}-{SS}{YY}-{NNNN}`**
   (season abans de l'any, `BRW-SS26-0002`) — **discrepància de fet** amb el signal.
   Comptador per regex `+1` `:363-376`, també **no-safe**.
3. **Import bulk** `bulk_import_service.py:426-466` → mateix format que (2), i **únic camí
   atòmic**.

**Peça reutilitzable que SÍ existeix (el patró bo a copiar):**
- `class ModelSequence` `models_app/models.py:664-682`: comptador `last_seq` amb
  `unique_together=[('customer','year','season')]` `:677`.
- `reserve_sequence_range()` `services.py:38-64`: `transaction.atomic()` +
  `ModelSequence.objects.select_for_update().get_or_create(...)` `:56-59` → **concurrency-safe**
  (mateix patró que `tasks/services_i.py:31`).
- Generador genèric de número de document (factura/albarà/comanda) reutilitzable, o model
  `*Counter`/`*Series`/`*Numbering`: **NO EXISTEIX**. `ModelSequence` està acoblat a
  (customer, any, temporada).
- El mestre B1 (`commerce`) **no minta cap code/SKU**: `Unit.code` `commerce/models.py:24` i
  `Product.code` `:65` són `SlugField(unique)` d'**entrada manual** (sense `save()` override,
  sense signal, no a `read_only_fields` `serializers.py:80`).

**💡 PROPOSTA (a validar):** B2 necessita **peça nova** de numeració de document, perquè
l'escòping d'una oferta **no** és (customer, any, temporada) sinó **(tipus de document, any)**
—o (tipus, any, tenant si es vol reiniciar per empresa)— i vol un format estable propi
(p.ex. `OF-2026-0001`, `PO-2026-0001`). Recomanació: replicar exactament el patró segur de
`ModelSequence`/`reserve_sequence_range` (un `DocumentSequence` amb
`unique_together=('doc_type','year')` + `select_for_update`), **no** el signal MAX del camí
manual (no-safe). Decidir amb l'Agus: reinici anual sí/no, i si el comptador és per-tipus o
compartit.

**Veredicte BLOC 2:** **cal peça nova**, però amb patró intern ja provat a copiar
(`ModelSequence`). Evitar el signal MAX (no concurrency-safe) i unificar format (el repo en té
dos). Escòping i format = decisió humana.

---

## BLOC 3 — Pipeline PDF

**Backend — NO genera PDF:**
- `requirements.txt:34` → `Pillow==12.2.0` (única lib d'imatge). `reportlab==4.5.1` **només a
  `requirements.lock:52`** (transitiva) i **mai importat** en cap `.py`. `PyMuPDF` (`.lock:44`)
  s'usa per **llegir** PDFs (extracció), no generar.
- `weasyprint`, `xhtml2pdf`, `pdfkit/wkhtmltopdf`, `fpdf/fpdf2`, `borb`, `cairosvg`:
  **NO EXISTEIXEN** (ni a `.txt` ni a `.lock`).

**Frontend — pipeline B0 (fitxa tècnica), client-side:**
- `frontend/package.json`: `konva ^10.3.0` `:22`, `react-konva ^19.2.5` `:29`, `pdf-lib ^1.17.1`
  `:24`. **NO** hi ha `jspdf`, `html2canvas`, `@react-pdf/renderer`, `canvas`.
  `frontend-backoffice/package.json`: **cap** lib de dibuix/PDF.
- Export real: `onExport` `TechSheetEditor.jsx:3009-3046` → `PDFDocument.create()` `:3012` ·
  `renderPageToDataURL(...)` `:3016` · `pdf.embedPng(dataUrl)` `:3017` · `page.drawImage(png,
  {x:0,y:0,width,height})` `:3019` (el PNG ocupa **tota** la pàgina) · `pdf.save()`→`Blob` ·
  descàrrega `a.click()` `:3039-3043`.
- Rasterització: `renderPageToDataURL` `:907-925` → `Konva.Stage` **offscreen** +
  `stage.toDataURL({pixelRatio:3.5, mimeType:'image/png'})` `:922`. **És una foto PNG, sense
  text vectorial.**
- **Fonts incrustades: NO EXISTEIX** (`grep embedFont|StandardFonts` → zero). Les fonts es
  pinten al canvas i queden rasteritzades (`FONT='IBM Plex Mono'` `:46`).
- **Peces de layout/branding aprofitables (conceptualment, no codi directe):**
  `buildHeaderPrimitives()` `:514-540` (capçalera 2 bandes 20+12 mm, ample 277 mm),
  `HeaderBlock` `:605-614` (logo real), càrrega de logo de client `customerLogoUrl =
  model.customer_logo` `:1356`, i constants `PAGE_FORMATS` `:39-44` (A4/A3 en mm + punts PS).
- **Client vs server:** **CLIENT-SIDE** (navegador). El backend només **desa** el PDF que rep
  (`FttDocumentExportView`, veure B0 doc `:149-152`); no hi ha generador Python.

**Decisions ja escrites als docs vigents:**
- `DIAGNOSI_COMERCIAL_B0_2026-07-08.md:40-42` — "El pipeline PDF actual **NO és reutilitzable**…
  foto (PNG) del canvas Konva… sense text vectorial, sense taules paginables."
- `…B0…:315-316` — "El Konva actual queda **descartat** per a documents estructurats"; motor PDF
  nou = **decisió B-fi pendent** (backend reportlab/weasyprint vs frontend @react-pdf/pdfmake).
- `DIAGNOSI_LLENÇ_B2.md:6,143` — Konva segueix sent el **llenç** de dibuix (decisió tancada);
  però el render és raster (`KonvaImage`), no vector.

**💡 PROPOSTA (a validar) — viabilitat multi-tenant (django-tenants) + Hetzner:**
| Opció | Text vector/taules | Multi-tenant | Hetzner / cost | Nota |
|---|---|---|---|---|
| **reportlab** (ja al `.lock`) | ✅ natiu (Platypus taules) | ✅ cap problema (render dins request, schema ja actiu) | ✅ pure-python, footprint mínim, 0 deps natives | ❌ baix nivell, més codi de layout |
| **weasyprint** (HTML→PDF) | ✅ excel·lent (CSS) | ✅ (render en context de request) | ⚠️ **deps natives pesades** (cairo/pango) a instal·lar a Hetzner; CPU per request | plantilles HTML còmodes |
| **@react-pdf / pdfmake** (frontend) | ✅ vector | ✅ **0 càrrega servidor**, cap concern de tenant | ⚠️ cal instal·lar + rebuild frontend | coherent amb B0 client-side |
| Konva→PNG (actual) | ❌ raster | ✅ | ✅ | **descartat** per docs estructurats (B0) |

Recomanació de terreny: per a documents comercials (oferta amb taula de línies, totals,
condicions) cal **text vectorial + taules paginables** → l'actual queda fora. Les peces
reutilitzables de B0 són **de disseny** (capçalera 2 bandes, logo de client per `customer_logo`,
formats A4/A3), no de codi. Motor concret = decisió de l'Agus; `reportlab` és el candidat de
menys fricció d'infra (ja al lock, pure-python, cap problema amb django-tenants ni Hetzner).

**Veredicte BLOC 3:** pipeline actual **DIFERENT i no reutilitzable** per a B2 (raster).
**Cal motor nou**; branding/layout de B0 aprofitable com a referència. Fonts: no n'hi ha
d'incrustades. Decisió de motor pendent (Patró C).

---

## BLOC 4 — Estat real del git (GATE)

**Resultat del gate: ✅ B1 pujat net → NO és bloquejador, es continua.**

- Tip autoritari del remot: `git ls-remote origin refs/heads/dev` = **`8731d8d`** (= HEAD local
  de `dev`). `git fetch --dry-run` no reporta cap ref nou → remote-tracking al dia.
- Cadena B1 `a10f39f`..`95a17ab` (B1-P1…B1-P6) **tota a `origin/dev`** (`git branch -r
  --contains` d'ambdós extrems → `origin/dev`). A sobre, 3 commits size-map (`75a232c`,
  `84e4653`, `8731d8d`) també pujats.
- **Conflicte git resolt:** `git ls-files -u` **buit** (cap unmerged path). `SizeMapSetup.jsx`
  net, últim toc `84e4653` (ja a `origin/dev`).
- **⚠️ Residu (no bloca):** `frontend/public/CALLIE.svg` és **`??` untracked** — **no és a git ni
  a `origin/dev`**. L'única referència al codi és una pàgina **POC**
  (`frontend/src/pages/PaperKonvaPoc.jsx:16,301`), **no** la pàgina Productes de B1-P6. En un
  clon net o worktree nou, aquell POC no trobaria l'asset. Recomanació: commitar-lo o eliminar
  la referència (fora d'scope B2, s'anota).

**Veredicte BLOC 4:** **B1 confirmat net a `origin/dev`. Sense bloquejador.** El "conflicte
SizeMapSetup.jsx + CALLIE.svg" està resolt a nivell git; queda només l'asset CALLIE.svg
untracked (POC, no B1).

---

## BLOC 5 — Wizard de conversió oferta→comanda (modal 7)

**El wizard i els documents NO EXISTEIXEN encara** (`commerce/models.py:4-5`: Quote/SalesOrder/…
"arriben a B2-B5"). No hi ha models `Offer`/`Order`/`Quote`, ni endpoint de conversió, ni wizard
frontend. Però hi ha **patrons reaprofitables**:

**Wizard existent (UI de confirmació multi-pas):** `ModelWizard.jsx:29`, rutejat
`App.jsx:224,228`. Stepper amb **gate** (`ModelWizard.jsx:228-246`): passos 2-3 bloquejats
(🔒) fins resoldre bloc 1 (`block1Resolved` `:217`). Handler final `handleCreate` `:181` (POST
`models.createWizard` `:187-192`). → patró de modal amb passos + gate reutilitzable per al
"modal 7" (confirmar conversió).

**Congelació / snapshot (el nucli de "línies congelades"):**
- **Clonar registre + fills** (anàleg directe de congelar les línies d'una oferta a una comanda):
  `clone_model_for_qa.py:72-88` clona el pare amb `pk=None`; `:91-103` itera fills
  (`BaseMeasurement`, `ModelGradingRule`) re-`pk=None` per fila; reusa FK compartides `:86`.
  **És el patró exacte** de "copiar capçalera + línies a un document nou immutable". No hi ha
  `clone` genèric ni `deepcopy` (`NO EXISTEIX`) — és command específic, però replicable.
- **Flag de tancament:** `close_base()` `pom/services.py:238-290` posa `estat='Tancat'`
  (`CLOSED_STATE` `:197`) + `base_tancada=True`, idempotent `:262-269`. Model d'estat
  "segellat" per copiar.
- **Segellat immutable + guard de reobertura:** `seal_model_grading()` `fitting/services.py:547`
  (`aprovada=True`, `aprovada_per`, `data_aprovacio` `:563-566`); després
  `bump_grading_version_and_generate()` `pom/services.py:461` exigeix reobertura explícita
  (guard D-1 `:492-500`). → patró "un cop acceptada, l'oferta queda bloquejada; reobrir és
  explícit".
- **Transició accept→lock:** `approve_design_freeze_view` `pom/wizard_views.py:18-40` (segella
  `design_freeze_at`, transiciona estat, idempotent). `PlanSnapshot` `tasks/models.py:330` +
  `_save_snapshot` `planning/plan_service.py:98-100` = precedent de "previsió immutable".

**💡 PROPOSTA (a validar):** el "convertir oferta acceptada → comanda amb línies congelades"
es pot compondre de peces existents: (a) modal de confirmació estil `ModelWizard` (stepper +
gate); (b) servei de conversió calcat de `clone_model_for_qa` (copia capçalera Quote + QuoteLines
a SalesOrder + SalesOrderLines amb `pk=None`, congelant preus/quantitats); (c) flag d'estat
`acceptada/convertida` + guard de reobertura estil `aprovada`/guard D-1. Decisió d'estat i
d'irreversibilitat = humana.

**Veredicte BLOC 5:** wizard/documents **NO EXISTEIXEN**, però el patró confirmació+congelació
està **sobradament precedit** (clone_model_for_qa + seal/aprovada + close_base + ModelWizard).
Reaprofitable de dalt a baix.

---

## TAULA FINAL de riscos (per al CTO)

| # | Àrea | Estat | Ancoratge | Risc / decisió pendent |
|---|---|---|---|---|
| R1 | **B1 push (gate)** | ✅ NET a `origin/dev` | `ls-remote`=`8731d8d`; `branch -r --contains a10f39f/95a17ab` | Cap. Gate superat. |
| R2 | **CALLIE.svg** | ⚠️ untracked, no a git | `frontend/public/CALLIE.svg` `??`; ref a `PaperKonvaPoc.jsx:16` | POC trencat en clon net. Baix (no B1/B2). Commitar o treure ref. |
| R3 | **Herència línies** | Patró = duplicació, 0 abstractes | `grep abstract=True`→0; 5 parelles header+línia | Decidir Via A (duplicar) vs Via B (1a abstracta `commerce`-local) per família de 6 docs. |
| R4 | **Naming timestamps** | 3 variants al repo | `created_at`/`creat_at`/`data_creacio` | B2 ha de fixar-ne una (anglès, per llei B1). Deriva si no. |
| R5 | **Numeració** | Peça segura existeix però acoblada | `ModelSequence` `models_app/models.py:664`; `reserve_sequence_range` `services.py:38-64` | Cal `DocumentSequence` nou (tipus+any). NO usar el signal MAX (no concurrency-safe, `signals.py:59-68`). |
| R6 | **Formats de codi** | Dos formats incompatibles | `signals.py:80` (`-YY-TT-`) vs `views.py:238` (`-SS YY-`) | Fixar format únic de document a B2 abans de mintar. |
| R7 | **PDF backend** | Cap generador | `requirements.txt:34` només Pillow; `reportlab` només `.lock:52` | Cal instal·lar/decidir motor. `reportlab` = menys fricció infra. |
| R8 | **PDF pipeline B0** | Raster, no reutilitzable | `TechSheetEditor.jsx:3009-3046,907-925`; `…B0…:40-42,315-316` | Konva→PNG descartat per taules/text. Aprofitar només branding/layout. |
| R9 | **PDF multi-tenant/Hetzner** | Client-side avui, cap concern | B0 doc `:149-152` (backend només desa) | Si es passa a weasyprint: deps natives (cairo/pango) a Hetzner. reportlab/frontend = sense. |
| R10 | **Wizard oferta→comanda** | NO EXISTEIX; patrons sí | `commerce/models.py:4-5`; `clone_model_for_qa.py:72-103`; `seal_model_grading` `fitting/services.py:547` | Cap peça a construir de zero; compondre de precedents. Estat/irreversibilitat = decisió humana. |

---

*Patró A · read-only · cap fitxer de codi tocat. Les 💡 PROPOSTA són disseny a validar per
l'Agus (Patró C); els documents Quote/SalesOrder/… i el pipeline oferta→comanda encara NO
EXISTEIXEN al codi (bloc B2-B5).*
