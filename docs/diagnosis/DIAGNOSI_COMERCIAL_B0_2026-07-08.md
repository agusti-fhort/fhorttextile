# DIAGNOSI — Terreny real per al mòdul Comercial Studio (B0)

**Data:** 2026-07-08 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`.
**Abast:** verificar el terreny (models, serializers, frontends, apps, gating, PDF) abans del
disseny fi del mòdul Comercial Studio (v. `DISSENY_MODUL_COMERCIAL.md`, Annex A = aquest brief).
**Convenció:** cada afirmació porta `fitxer:línia` (relatiu a `backend/` o `frontend/`).
`"NO EXISTEIX"` = confirmat absent al codi (verificat, no especulat). `💡 PROPOSTA` = a validar (Patró C).

---

## Resum executiu (el que desbloqueja la decisió)

1. **Terreny d'articles/oferta VERGE, però facturació SaaS OCUPADA.** No existeix cap entitat
   viva de `Quote/Budget/Oferta/SalesOrder/WorkOrder/DeliveryNote/Settlement` (naming lliure).
   PERÒ el domini "facturació" ja el té l'app **`backoffice`** (SaaS plataforma→tenant:
   `Invoice`, `InvoiceLine`, `ServiceCatalog`, `TenantContract`, `ContractLine`, motor
   `generate_invoice`, UI `/contractes` `/serveis`). Són **públic-only**, no comparteixen entitats
   amb el mòdul tenant→tercer — coherent amb la llei "dues facturacions separades". Cap barreja,
   però ull amb la confusió de domini al parlar de "factura".

2. **`TipologiaModel` NO EXISTEIX (esborrat 2026-06-26).** La premissa "TipologiaModel 57 files
   viva" del brief és **falsa**. L'entitat viva és la parella `GarmentType` (família) →
   `GarmentTypeItem` / GTI (variant de complexitat). És **definició TÈCNICA de peça**, no un article
   comercial: no té preus, ni proveïdors, ni línies. El `Product` comercial és entitat NOVA que
   *referenciarà* el GTI (matriu preu×GTI, cost Welford), no el substitueix.

3. **Cap col·lisió exacta de naming** per als 15 noms nous (backend ni frontend). Alerta només
   per **proximitat**: `Production`/`ProductionTab` (arrel "Product…") i `Invoice`/`InvoiceLine`
   (domini facturació al backoffice). `Supplier` i `Customer` **ja existeixen** i s'han de
   **reutilitzar**, no duplicar.

4. **Les ampliacions fiscals són construcció NOVA sobre `Customer`/`Supplier`** (avui esquelètics,
   0 camps fiscals). El **vocabulari fiscal canònic ja existeix** a `tenants.Client` (NIF, adreça,
   VAT, mètode pagament…) → reusar-ne els noms. `codi_global` ja hi és al Customer (federació).
   `% descompte` NO EXISTEIX enlloc.

5. **`hourly_rate` encaixa net a `TenantConfig`** (app `accounts`) — 3 punts additius, cap obstacle.
   `TimeBased`/venda és un altre eix (decisió oberta, no bloqueja B0).

6. **El pipeline PDF actual NO és reutilitzable.** La fitxa tècnica exporta una **foto (PNG) del
   canvas Konva** incrustada en pdf-lib: sense text vectorial, sense taules paginables. Documents
   comercials (oferta/albarà amb línies variables + totals) requereixen **peça nova**.

7. **Gating: patró madur = capability; flag de tier = mig construït.** Les capabilities estan
   totalment cablejades back+front (patró a copiar). El flag de Plan (`feature_flags` JSON) existeix
   a dades i backoffice però **NO s'exposa a `/me`** → l'únic pont nou a construir per gatejar per tier.

8. **App nova `commerce` a TENANT_APPS**: encaixa net, cap col·lisió de label; 1 línia a `settings.py`.

---

## BLOC Q1 — TipologiaModel vs Product

- **`TipologiaModel` NO EXISTEIX viu.** Cap `class TipologiaModel` a cap `models.py` (grep buit,
  verificat). Creat a `tasks/migrations/0002_tipologiamodel.py:16`, **esborrat** a
  `tasks/migrations/0029_delete_tipologiamodel.py:13` (`DeleteModel`, 2026-06-26). L'única referència
  al nom és un script d'import trencat: `backend/data/import_master.py:31` (importaria classe morta).
  Nota històrica: aquell model **sí** tenia camps de cost/slots (`0002_tipologiamodel.py:25-30`) — era
  el germà del difunt PaquetServei, concepte de servei/costing pre-Welford.
- **Entitat viva (taxonomia tècnica, 3 nivells):**
  - `GarmentType` (família, tenant) — `pom/models.py:336`; camps `:337-368` (codi_client, nom_client,
    nom_en/ca/es, grup, construccio_habitual, targets_recomanats M2M…).
  - `GarmentTypeItem` / **GTI** (variant de complexitat) — `tasks/models.py:213`; FK→GarmentType
    (`:217`, CASCADE), `code` slug, `base_size_definition` (`pom.SizeDefinition`), `grading_rule_set`
    (`pom.GradingRuleSet`).
  - `GarmentTypeGlobal` (catàleg SHARED) — `pom/models.py:79`.
- **Consumidors GTI (per què és tècnic, no comercial):** `TaskTimeEstimate.garment_type_item`
  (`tasks/models.py:280`, motor Welford), `GarmentPOMMap.garment_type_item` (`pom/models.py:385`),
  `Model.garment_type_item` (`models_app/models.py:161`), `Model.tipologia_confirmada`
  (`models_app/models.py:442`). Serializers/views: `pom/serializers.py:109`, `pom/views.py:94`;
  `tasks/serializers_b.py:68`, `tasks/views_b.py:745`.
- **Frontend:** CRUD `GarmentTypes.jsx`, autoria `ItemAuthoring.jsx`, selector
  `GarmentTypeSelector/GarmentTypeSelector.jsx`; lectura a `ModelWizard.jsx`, `ModelSheet.jsx`, etc.

**Veredicte Q1:** GTI ≠ Product. És taxonomia tècnica (alimenta temps/POM/grading). El `Product`
comercial és NOU i *referencia* el GTI (matriu `ProductPriceGTI`, cost estàndard via cascada). **Cap
solapament** — construir de zero, endollant al GTI per code. La premissa "TipologiaModel 57 files" cau.

---

## BLOC Q2 — Customer i Supplier (ancoratge de les ampliacions fiscals)

- **Dues entitats "client" DIFERENTS (no confondre):**
  - `Customer` (app `tasks`) — `tasks/models.py:161` — **client comercial del tenant** = subjecte de
    l'ampliació fiscal. Camps ACTUALS (verificat): `codi` CharField(3, unique) `:167`, `nom` `:168`,
    `active` `:169`, `is_self` `:170`, **`codi_global`** CharField(3, null/blank, reservat federació)
    `:174`, `logo` ImageField `:176`. **Cap camp fiscal.**
  - `Client` (app `tenants`) — `tenants/models.py` — registre de tenants (django-tenants). **Ja té
    tota la fiscalitat** (referència de vocabulari, no és el client comercial).
- **Serializer/view/frontend de Customer:** `CustomerSerializer` (`tasks/serializers_b.py:49`, exposa
  `id,codi,nom,active,is_self,logo`); `CustomerViewSet` (`tasks/views_b.py:643`, escriptura gated
  **CONFIGURE**, destroy 409 si té models); router `customers` `tasks/urls.py:30` → `/api/v1/customers/`.
  Frontend: `pages/Customers.jsx` + `components/CustomerModal.jsx` (només codi/nom/active,
  `CustomerModal.jsx:14-16`), `CustomerSelector.jsx`; endpoints `endpoints.js:204`.
- **Supplier** — `tasks/models.py:144`; camps `name` `:147`, `type` (workshop/factory) `:148`,
  `active` `:150`. Docstring "esquelètic ara; creix cap a fitxa de proveïdor" `:145-146`. **Cap camp
  fiscal.** `SupplierSerializer` `serializers_b.py:43`; `SupplierViewSet` `views_b.py:622` (escriptura
  gated **SCHEDULE_FITTINGS**); router `suppliers` `tasks/urls.py:22`. Frontend `pages/Suppliers.jsx`.
- **Vocabulari fiscal canònic ja existent** (a reusar per als noms): `tenants.Client`
  (`tenants/models.py:126-154`): `rao_social`, `nif`, `adreca_linia1/2`, `ciutat`, `codi_postal`,
  `pais`, `email_facturacio`, `vat_number`, `regim_vat`, `metode_pagament`… + contacte estructurat
  `TenantContacte` (`backoffice/serializers_tenants.py:10`). **`% descompte` NO EXISTEIX** (seria nou).

**Veredicte Q2:** ampliació fiscal = camps NOUS a `Customer` (`tasks/models.py:161`) i `Supplier`
(`:144`) + propagació a serializer (`serializers_b.py:49/43`) + modal (`CustomerModal.jsx`,
`SupplierModal`). Reutilitzar noms de `tenants.Client`. `codi_global` ja hi és. Escriptura de Customer
ja gated CONFIGURE; la de Supplier gated SCHEDULE_FITTINGS (revisar si el mòdul vol una capability pròpia).

---

## BLOC Q3 — Restes quote/oferta/PaquetServei (viu vs fòssil)

- **Verge (0 entitats vives):** `quote`, `budget`, `pressupost`, `proposal`, `cotitzaci`,
  `liquidaci`, `settlement` → cap model/view/component. **NO EXISTEIXEN.** Cap clau i18n
  `oferta/pressupost/quote/proposal/invoice` al frontend (grep buit).
- **Fòssils confirmats esborrats (0 codi viu):** `PaquetServei`, `PaquetServeiTasca`, `Tasca`,
  `TascaGlobal`, `ServicePackage`, `ModelServei`. Esborrats a `tasks/migrations/0026_*:34-41`,
  `pom/migrations/0027_delete_tascaglobal.py:18`. Restes NOMÉS a migracions antigues, fixtures
  d'import Frappe (`backend/data/import_ops/*.json`) i docs — cap consumidor de runtime.
- **⚠️ Domini facturació OCUPAT (VIU, backoffice/públic):** `Invoice` (`backoffice/models.py:147`),
  `InvoiceLine` `:186`, `ServiceCatalog` `:80`, `TenantContract` `:103`, `ContractLine` `:124`,
  `ModelConsumptionEvent` `:63`; motor `billing_service.py:36` (`generate_invoice`); UI
  frontend-backoffice `ContractesPage.jsx`/`ServeisPage.jsx`, `/contractes` `/serveis`
  (`backoffice/urls.py:14-21`). És SaaS **plataforma→tenant**, no tenant→tercer.
- **⚠️ Albarà de consum VIU (tenant-side, no comercial):** `ConsumptionRecord`
  (`models_app/models.py:743`, "albarà de consum viu al tenant"); endpoint `/albara/`
  (`models_app/urls.py:209`); frontend `RegistreActivitatTab.jsx`; claus i18n `albara.*`
  (`i18n/{ca,en,es}.json:49`, NO òrfenes). `Contracte`/`LiniaContracte` de slots
  (`models_app/models.py:14,29`).
- **Falsos positius:** `"oferta"` a `MeasuresEntryPanel.jsx:14,130` = oferta de mesures (fitting);
  `facturable` a `TaskType` (`tasks/models.py:50`) = flag de procés tècnic.

**Veredicte Q3:** cap entitat d'oferta/comanda viva (naming lliure). PERÒ el mot "albarà" i "factura"
ja tenen amo (`ConsumptionRecord` + backoffice `Invoice`). El nou `DeliveryNote` comercial ha de
**conviure** amb `ConsumptionRecord` (semàntica diferent: entrega a tercer vs consum de plataforma) —
distingir-los per naming i UI, no fusionar.

---

## BLOC Q4 — Pipeline PDF

- **Tot al frontend (Konva + pdf-lib).** `frontend/package.json`: `konva`, `react-konva`, `pdf-lib`.
  `TechSheetEditor.jsx:4-6` (imports), `TechSheetTemplateEditor.jsx:8-9`.
- **Flux = foto del canvas:** `renderPageToDataURL` (`TechSheetEditor.jsx:907-925`) pinta un
  `Konva.Stage` offscreen i fa `stage.toDataURL({mimeType:'image/png'})` (`:922`); `onExport`
  (`:3009-3046`) fa `PDFDocument.create()` + `embedPng` + `drawImage` per pàgina (`:3016-3019`). PDF =
  **PNG per pàgina**, sense text seleccionable ni taules natives. Plantilla `template_json`
  (`TechSheetTemplateEditor.jsx:87,111`), primitives de disseny lliure (`TechSheetEditor.jsx:560-903`).
- **Backend NO genera PDF, només el desa:** `FttDocumentExportView` rep el PDF del client
  (`ftt_document_views.py:162-185`); `save_export` persisteix (`services_ftt_document.py:217-235`).
  `reportlab==4.5.1` al `requirements.lock` però **NO** a `requirements.txt` ni importat enlloc.
  `weasyprint`/`xhtml2pdf`/`fpdf` NO EXISTEIXEN.
- **Altres exports:** CSV natiu backend (`pom/s8_views.py:55-125`, `ExportButton.jsx:67-95`); XLSX
  només com a INPUT (bulk import, `openpyxl==3.1.5`).

**Veredicte Q4:** **peça NOVA** per a documents comercials (capçalera fiscal + taula de línies +
totals + paginació). El pipeline Konva és exclusiu de la fitxa (disseny raster lliure). 💡 PROPOSTA (a
validar B-fi): backend amb `reportlab` (ja al lock) o `weasyprint` (HTML→PDF), coherent amb el patró
d'exports backend (`openpyxl`/CSV); alternativa frontend `@react-pdf/renderer`/`pdfmake`.

---

## BLOC Q5 — TenantConfig i `hourly_rate`

- **Model `TenantConfig`** (app `accounts`) — `accounts/models.py:30` (1 fila/tenant, `pk=1`,
  `get_or_create_default()` `:48`). Camps: `unitat_mesura` (CM/INCH) `:35`, `norma_referencia` `:36`,
  `nom_empresa` `:37`, `logo_url` `:38`, timestamps `:39-40`.
- **Edició:** `TenantConfigSerializer` (`pom/s2_serializers.py:150`, `Serializer` manual, no
  ModelSerializer); `tenant_config_view` GET/PATCH (`pom/s2_views.py:270`), endpoint
  `/api/v1/tenant-config/` (`tasks/urls.py:166`); PATCH amb **allowlist** explícita (`s2_views.py:287`).
  Frontend: `UnitToggle.jsx`, `OnboardingWizard.jsx:104-121`.
- **`hourly_rate` NO EXISTEIX** (ni al model, ni serializer, ni frontend). L'únic camp econòmic proper
  és `UserProfile.cost_hora` (`accounts/models.py:14`, per tècnic — reserva per al v2 per-perfil).
  `unitat_mesura` (cm/inch) SÍ hi viu (mètric, ≠ futur `Unit` comercial).

**Veredicte Q5:** afegir `hourly_rate = DecimalField` a `TenantConfig` encaixa net. 3 punts additius:
(1) camp + migració a `accounts`; (2) al serializer manual `s2_serializers.py:150`; (3) a l'allowlist
`s2_views.py:287` (si s'oblida → read-only silenciós). Cap obstacle estructural.

---

## BLOC Q6 — Col·lisions de naming

Cap col·lisió EXACTA (classe/taula/component) per als 15 noms nous. Cap `db_table` explícit amb
aquests noms (grep buit).

| Nom nou | Backend | Frontend |
|---|---|---|
| Product · Unit · Quote · QuoteLine · SalesOrder(+Line) · WorkOrder · Expense · DeliveryNote(+Line) · Settlement · ProductRecipe · ProductComponent · ProductPriceGTI | NO EXISTEIX | NO EXISTEIX |
| ProductSupplier | NO (però `Supplier` sí: `tasks/models.py:144`) | NO EXISTEIX |
| **Order** (sol) | NO (`class Order` no; només `TechnicianQueueOrder` `planning/models.py:72`) | NO (cap component `Order`) |

**Proximitats a vigilar (no bloquegen):**
- `Production` / `ProductionSerializer` / `ProductionTab.jsx` (`tasks/models.py:187`) — arrel "Product…"
  → soroll d'autocompletat/cerca amb `Product*`.
- `Invoice`/`InvoiceLine`/`ServiceCatalog`/`ContractLine`/`Plan` (backoffice/tenants) — domini
  facturació SaaS; patró `*Line` ja usat (referència per a `QuoteLine`/`SalesOrderLine`).
- `Supplier` (`tasks/models.py:144`) i `Customer` (`:161`) → **reutilitzar, no duplicar**.

**Veredicte Q6:** els 15 noms es poden crear. ⚠️ B-fi ha de **reusar** `Supplier`/`Customer` existents
(FK des de `ProductSupplier`/`Expense`/`Quote`) i evitar confusió `Product`↔`Production` i
`DeliveryNote`(comercial)↔`ConsumptionRecord`(consum)↔`Invoice`(SaaS).

---

## BLOC Q7 — Wizard de model i `garment_type_item`

- **Wizard:** `frontend/src/pages/ModelWizard.jsx` (3 blocs; el vell flux redirigeix aquí,
  `App.jsx:224`). Captura del GTI: estat `item` (`ModelWizard.jsx:54`) via `GarmentTypeSelector`
  `onSelect` (`:313-316`); s'envia com `garment_type_item_id` a `skeletonPayload()` (`:172`).
- **NO és obligatori avui:**
  - Frontend: només avís visual no bloquejant `{!item && ...no_item_warn}` (`:413-417`); el botó Crear
    fa `disabled={saving || baseSizeInvalid}` (`:428`, NO comprova `item`); úniques validacions dures
    = `season` i `customerId` (`:182-183`).
  - Backend: `Model.garment_type_item` FK `null=True, blank=True` (`models_app/models.py:161`);
    `_resolve_garment_def` tracta el camp com OPCIONAL (`models_app/views.py:257-301`, docstring `:259`);
    `create_model_wizard` (`views.py:304`) valida base_size/season/multi-peça però **no** el GTI.
- **Punts a tocar per fer-lo obligatori + selector de línia de comanda:**
  - Frontend guard: `ModelWizard.jsx:181-183` (afegir `if(!item)`) i/o `:428` (`!item` al disabled).
  - Backend guard: `models_app/views.py:328-330` o dins `_resolve_garment_def` `:266`.
  - Selector "línia de comanda": nou estat a prop de `:54`, render dins Bloc 2 (`:313-320`), camp a
    `skeletonPayload()` (`:170-179`), acceptació a `_resolve_garment_def` (`:257-301`).
    **⚠️ El concepte "línia de comanda"/order-line NO EXISTEIX avui** (cap model/camp; grep buit) →
    depèn que B2/B3 creïn `SalesOrderLine`/`WorkOrder`.

**Veredicte Q7:** fer el GTI obligatori = 2 guards petits (front `:181`/`:428` + back `:328`/`:266`),
additiu i barat. El selector de línia és B3 (necessita l'entitat comanda primer). Ordre correcte al pla:
la línia de comanda arriba a B3, no a B1.

---

## BLOC Q8 — Estructura d'apps

- **`settings.py`:** SHARED_APPS `:36-59` (inclou `fhort.tenants` `:38`, `fhort.pom` `:55`,
  `fhort.backoffice` `:58` "NOMÉS public"); TENANT_APPS `:62-72` (`accounts` `:66`, `models_app` `:67`,
  `pom` `:68`, `fitting` `:69`, `tasks` `:70`, `planning` `:71`); INSTALLED_APPS derivat `:74`.
  `pom` és híbrida (Global a public + replicada per tenant).
- **Patró app tenant (`tasks/`):** `apps.py` (`class TasksConfig(AppConfig): name='fhort.tasks'`,
  `tasks/apps.py:4-5`), `models.py`, `serializers*.py`, `views*.py`, `urls.py`, `migrations/`. URLs
  muntades a `backend/fhort/urls.py` (ROOT_URLCONF `settings.py:94`). Cap `apps.py` fixa `label=` custom.

**Veredicte Q8:** app nova **`commerce` → TENANT_APPS** (dades per-tenant). Punt exacte:
**`settings.py:62-72`** (afegir `'fhort.commerce'`, p.ex. després de `:71`); INSTALLED_APPS l'hereta.
Cap col·lisió de label (`commerce` lliure). Cal `apps.py` (`CommerceConfig`, name `'fhort.commerce'`) +
muntar urls a `backend/fhort/urls.py`.

---

## BLOC Q9 — Gating per capability/tier

- **Capabilities (patró MADUR, cablejat back+front):** definició `accounts/capabilities.py:6-17`
  (`EXECUTE_TASKS`, `DEFINE_TASKS`, `SCHEDULE_FITTINGS`, `CLOSE_GATES`, `CONFIGURE`, `VIEW_TEAM_TASKS`,
  `MANAGE_USERS`); matriu rol→caps `:20-26`; resolució `get_capabilities` `:31-43`. Permission class
  `HasCapability` `:46-54`. Ús backend (exemple a copiar): `tasks/views_b.py:283`
  (`required_capability = DEFINE_TASKS`), imperatiu `:651`/`:756`. Exposició al client:
  `/me` retorna `capabilities` (`accounts/serializers.py:21` + `get_capabilities` `:67`, verificat).
  Guard frontend: menú `Sidebar.jsx:180-183` + switch `:216-227`; component `ModelWizard.jsx:35`
  (`me?.capabilities?.includes('configure')`). Rutes: `ProtectedRoute` (`App.jsx:40`) només mira auth.
- **Flag de Plan/tier (MIG construït):** model `Plan` (`tenants/models.py:12-55`, noms Solo/Studio/
  Brand/Enterprise, `feature_flags = JSONField` `:40`); `Client.plan` FK (`:109`) + `Client.feature_flags`
  JSON (`:111`). Editable NOMÉS al backoffice (`backoffice/serializers_tenants.py:59`,
  `views_tenants.py:37`, `PlanViewSet` `backoffice/urls.py:13`). **`feature_flags` NO s'exposa a `/me`**
  (verificat: `accounts/serializers.py` fields acaba en `capabilities`, cap flag). `commercial_module`
  NO EXISTEIX (seria una clau dins el JSON).

**Veredicte Q9:** el mòdul comercial és **doble eix**:
1. **Activació per tier/contracte → `feature_flags['commercial_module']`** a `Plan`/`Client`
   (`tenants/models.py:40/111`), editable des del backoffice. **Pont nou a construir:** estendre el
   serializer `/me` (`accounts/serializers.py:16-33`) amb un `SerializerMethodField` que llegeixi
   `connection.tenant.feature_flags`/`plan.feature_flags` — únic tros que falta.
2. **Accés per rol → capability nova** (ex. `MANAGE_COMMERCE`) a `capabilities.py:6-26`, patró backend
   `tasks/views_b.py:283`, patró frontend `Sidebar.jsx:180-183`+`:216-227`.
💡 PROPOSTA (a validar): flag de Plan encén el mòdul per tenant + capability decideix quins usuaris hi
entren. El B5 del pla (gate) ha d'incloure el **pont `/me`** com a peça pròpia (avui inexistent).

---

## TAULA FINAL — EXISTEIX / FALTA / DIFERENT (per al CTO)

| # | Element | Estat | Àncora | Implicació per al disseny fi |
|---|---|---|---|---|
| Q1 | TipologiaModel | **NO EXISTEIX** (esborrat) | `tasks/migrations/0029:13` | La premissa cau; Product és nou, endolla al GTI |
| Q1 | GarmentType / GTI | EXISTEIX (tècnic) | `pom/models.py:336` · `tasks/models.py:213` | `ProductPriceGTI` referencia GTI per code |
| Q2 | Customer (fiscal) | **FALTA** (0 camps fiscals) | `tasks/models.py:161` | Ampliació nova; reusar noms de `tenants.Client` |
| Q2 | `codi_global` a Customer | EXISTEIX | `tasks/models.py:174` | Federació ja té ganxo |
| Q2 | Supplier (fiscal) | **FALTA** (esquelètic) | `tasks/models.py:144` | Ampliació nova; FK des de ProductSupplier |
| Q2 | `% descompte` | **NO EXISTEIX** | (grep buit) | Camp nou |
| Q3 | Quote/Order/Settlement… | **NO EXISTEIX** (verge) | (grep buit) | Naming lliure |
| Q3 | Facturació SaaS (Invoice…) | EXISTEIX (backoffice, públic) | `backoffice/models.py:147` | **No barrejar**; domini separat |
| Q3 | `ConsumptionRecord` (/albara/) | EXISTEIX (consum tenant) | `models_app/models.py:743` | `DeliveryNote` comercial ≠ aquest; distingir |
| Q3 | PaquetServei/Tasca | **NO EXISTEIX** (esborrat) | `tasks/migrations/0026` | Confirmat net (0 codi viu) |
| Q4 | Pipeline PDF | DIFERENT (raster Konva) | `TechSheetEditor.jsx:3016` | **Peça nova** per a docs comercials |
| Q4 | reportlab | present al lock, no usat | `requirements.lock` | Candidat backend (decidir B-fi) |
| Q5 | `hourly_rate` | **FALTA** | `accounts/models.py:30` | 3 punts additius, net |
| Q6 | 15 noms nous | sense col·lisió exacta | (grep buit) | OK; vigilar Product↔Production |
| Q7 | GTI obligatori al wizard | FALTA (opcional avui) | `ModelWizard.jsx:428` · `views.py:328` | 2 guards petits |
| Q7 | Selector línia de comanda | **NO EXISTEIX** (depèn B3) | (grep buit) | Arriba a B3, no B1 |
| Q8 | App `commerce` | encaixa TENANT_APPS | `settings.py:62-72` | 1 línia + apps.py + urls |
| Q9 | Capability gating | EXISTEIX (madur) | `capabilities.py:46` · `views_b.py:283` | Copiar patró (nova cap) |
| Q9 | `feature_flags` a `/me` | **FALTA** (pont) | `accounts/serializers.py:16-33` | Peça pròpia a B5 |
| Q9 | `commercial_module` flag | **NO EXISTEIX** | `tenants/models.py:40` | Clau nova al JSON |

---

## Notes per al disseny fi (💡 PROPOSTES, a validar — Patró C)

- **Reemmarcar el brief:** eliminar la premissa "TipologiaModel 57 files". El substrat tècnic viu és
  `GarmentType`/GTI, ja usat pel motor de temps — el `Product` comercial hi endolla, no el reemplaça.
- **Convivència de dominis (crític):** tres "documents d'entrega/factura" ja tenen amo —
  `Invoice`/`InvoiceLine` (SaaS, backoffice, públic), `ConsumptionRecord`/`/albara/` (consum, tenant),
  i el nou `DeliveryNote`/`Settlement` (comercial tenant→tercer). El disseny fi ha de blindar la
  separació (naming EN + UI + apps diferents) per no repetir la trampa Frappe.
- **B5 (gate) creix:** inclou el **pont `feature_flags`→`/me`** (avui inexistent) + capability nova. No
  és només "posar un flag": cal el serializer.
- **PDF = decisió de B0/B-fi pendent:** backend (reportlab/weasyprint) vs frontend (@react-pdf/pdfmake).
  El Konva actual queda descartat per a documents estructurats.
- **Reús obligat:** `Customer`, `Supplier`, `TenantConfig` (hourly_rate), catàleg de tasques per code,
  cascada Welford. Cap duplicació.
</content>
</invoke>
