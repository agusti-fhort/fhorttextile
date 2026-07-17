# DIAGNOSI — el motor de factura per emetre dilluns (LOSAN)

Data: 2026-07-17 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`

**Abast:** gap list exacta entre el motor 6A existent i «factura espanyola correcta, immutable, en
PDF, emesa dilluns» per a LOSAN — **serveis amb línies manuals**, no meritació de consum.

> Convenció: cada fet porta `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi**, no especulat.
> `💡 PROPOSTA (a validar)` = disseny per decidir (Patró C), mai fet.
>
> **Lectura de PROD:** no hi ha accés SSH a PROD (verificat: `Permission denied (publickey,password)`).
> Les dades de PROD d'aquest doc surten **només de lectura** del backup diari
> `/srv/fhort-prod-backups/incoming/fhort_textile_20260717_023001.dump` (02:30 d'avui), extretes amb
> `pg_restore --data-only -f -` cap a stdout: **cap restauració, cap BD creada, cap escriptura**.

---

## Resum executiu

1. **El camí de dilluns no existeix avui.** L'únic camí de creació de factures del sistema
   (`generate_invoice`) **salta explícitament les línies manuals**: `if tipus == 'manual': continue  # D1: skip`
   (`billing_service.py:73-74`). El motor 6A només sap fer la factura AUTO de meritació — exactament
   la que LOSAN **no** necessita.
2. **La factura no té ni número ni IVA.** `Invoice` **NO TÉ** camp de número ni de sèrie (només el
   `pk`), i **NO TÉ** cap camp d'IVA: només `total` (`models.py:162-198`). Una factura espanyola
   necessita número correlatiu, base imposable, tipus i quota. Res d'això existeix.
3. **NO EXISTEIX cap PDF al backoffice** (confirmat: cap `import reportlab` a tot l'app). Ara bé,
   `reportlab==4.5.1` **sí que és instal·lat** (`requirements.lock:56`) i **el mòdul `commerce` ja té
   un generador de PDF fiscal complet de 581 línies** (`commerce/pdf_service.py`) amb emissor, IVA i
   taula vectorial. És patró copiable, **no** reutilitzable directe (viu al schema del tenant).
4. **Les dades de l'emissor JA existeixen i estan poblades a PROD** — però **l'IBAN és buit**.
   `TenantConfig` del schema `fhort` té `legal_name='FHORT MANAGEMENT, SL'`, `tax_id='B01623776'`,
   `address='Salmerón, 165'`, `postal_code='08222'`, `city='Terrassa'`, `country='ES'`,
   `email='info@fhort.cat'`, logo. `iban=''` i `payment_notes=''` (buits).
5. **Bloquejador dur per a l'alta de dilluns: a PROD hi ha ZERO Plans.** `tenants_plan` és **buida**
   al dump, i `plan` és **obligatori** a l'alta (`serializers_tenants.py:105`). Sense sembrar un pla,
   LOSAN **no es pot donar d'alta** per l'API. I `seed_free_plan` només crea **Free**
   (`seed_free_plan.py:50-51`).
6. **Incoherència de vocabulari que afecta la D4:** el model `Plan` ofereix
   *Free/Solo/Studio/Brand/Enterprise* (`tenants/models.py:13-25`), però el catàleg de preus F1 parla
   de *starter/team* (`pricing_catalog.yaml:14`). **"Team" NO EXISTEIX com a Plan.** La "quota Team
   750 €/mes" del brief no té on aterrar avui.

---

## BLOC A1 — El motor 6A tal com és

**FET · Camps de `Invoice`** (`backoffice/models.py:162-198`): `client`, `period` (CharField(7),
'YYYY-MM'), `tipus` (auto|manual), `estat`, `total`, `moneda`, `created_at`, `emesa_at`, `nota`.
- **NO TÉ `numero` ni `serie`.** La identitat de la factura és el `pk`.
- **NO TÉ cap camp d'IVA**: ni base imposable, ni tipus, ni quota. `total` és un import pelat.
- **NO TÉ PDF ni cap camp de fitxer.**

**FET · Estats** (`:169-174`): `esborrany` / `emesa` / `pagada` / `cancel·lada`. **SÍ existeixen** —
la pregunta del brief («¿DRAFT/EMESA existeix?») té resposta afirmativa. Hi ha `emesa_at` (`:184`).

**FET · Una factura emesa ES POT editar i esborrar.** `Invoice` **NO TÉ** `save()` ni `delete()`
sobreescrits, ni manager restrictiu. Res impedeix mutar una `emesa`. Contrast: al MATEIX app, F4-legal
sí que té el guard (`models.py:368-380` save, `:382-384` delete, `:292-296` `NoDeleteQuerySet`).

**FET · Numeració:** **NO EXISTEIX**. Cap `numero`, cap seqüència, cap correlatiu. Contrast: `commerce`
sí que en té un de provat — `reserve_document_number(doc_type)` (`commerce/services.py:60-77`), amb
`DocumentSequence` + `select_for_update()`, format `{PREFIX}-{YEAR}-{NNNN}` i reinici anual.

**FET · Línies manuals:** `InvoiceLine` **SÍ les suporta a nivell de dada** — `service` és nullable
(`:269-272`) i `descripcio` és text lliure (`:273`). **Però cap camí les crea**: `generate_invoice`
les salta (`billing_service.py:73-74`).

**FET · Com es crea una factura avui:** un sol endpoint, `POST facturacio/generar/`
(`urls.py:33` → `views_contracts.py:50-74`), que només accepta `{codi_client, period, dry_run}` i
crida `generate_invoice` (auto). **NO EXISTEIX** cap endpoint de creació manual, cap de llistat, cap
de detall, cap serializer d'`Invoice`, i **`Invoice` NO està registrat a l'admin** (`admin.py`, cap
menció). Avui, una factura manual només es pot fer per `shell`.

**FET · Càlcul:** `total = Σ(quantitat × preu_unit)` quantitzat a 0.01 (`billing_service.py:91-92`).
**Cap IVA en cap punt.** El tipus d'IVA **NO EXISTEIX** al backoffice (confirmat per cerca a tot l'app).

**FET · Règim d'IVA:** existeix, però al **Client**, no a la factura. `Client.regim_vat` es deriva sol
a cada `save()` (`tenants/models.py:203-220`): `pais == 'ES'` → `REGIM_ESPANYOL`. LOSAN (ES) hi cauria
automàticament. **Ningú el llegeix des de la factura.**

**FET · Relació amb TenantContract/ContractLine:** **no són illes** — `generate_invoice` beu del
contracte vigent i de les seves `ContractLine` (`billing_service.py:58-71`), i el preu real viu al
`ContractLine.preu` (`models.py:149`), no al `Plan` (comentari explícit a `:121-122`).

**Veredicte A1:** el motor 6A és un **prototip de meritació**, no un emissor de factures. Té l'esquelet
(client, línies, estats, contracte) i li falta tot el que fa que una factura sigui una factura:
número, IVA, immutabilitat i PDF.

---

## BLOC A2 — El camí de la factura de serveis (el de dilluns)

| # | Baula | Estat | Evidència | Cost |
|---|-------|-------|-----------|------|
| 1 | Alta LOSAN (fitxa F2-B) | **BLOQUEJAT** | `plan` obligatori (`serializers_tenants.py:105`) + **0 Plans a PROD** (dump) | Sembrar pla + decisió D4 |
| 2 | ServiceCatalog: implantació/TMA | **EXISTEIX** (aprofitable) | `SETUP` = *"Posada en marxa: configuració del tenant, formació inicial i migració de dades"* (PROD, 5 entrades) | 0 — ja hi és |
| 3 | ServiceCatalog: quota Team | **A-MITGES** | `QUOTA_BASE` (tier_fee) existeix, però **sense preu** (el preu és al ContractLine) | 0 codi · decisió D1 |
| 4 | TenantContract per LOSAN des de la UI | **PENDENT DE VERIFICAR** | Existeix `views_contracts.py` i UI `/contractes` (`Sidebar.jsx:35`); no he auditat el CRUD complet | — |
| 5 | Factura amb línies manuals | **FALTA** | `generate_invoice` les salta (`billing_service.py:73-74`); cap endpoint de creació manual | **El gruix de B1** |
| 6 | IVA (21% ES) | **FALTA** | cap camp ni càlcul al backoffice | Camps + càlcul |
| 7 | Numeració correlativa | **FALTA** | cap `numero`/`serie` a `Invoice` | Port de `reserve_document_number` |
| 8 | PDF | **FALTA** (però amb patró) | cap PDF al backoffice · `commerce/pdf_service.py` (581 l.) com a model | Port/adaptació |
| 9 | Marcar EMESA | **A-MITGES** | `estat='emesa'` + `emesa_at` existeixen; **cap transició ni guard** | Guard + endpoint |

**FET · Els 5 obligatoris de l'alta** (`serializers_tenants.py:103-119`): `nom`, `tipologia`, `plan`,
`moneda`, `idioma`, i a més `pais` i `email_facturacio` (D1 d'F2-B). El comentari és explícit: *"`plan`
segueix obligatori SENSE default (tria explícita de l'operador; cap injecció de Free)"* (`:110-111`).

**FET · La fitxa admet les dades fiscals del receptor:** `rao_social`, `nif`, `adreca_linia1`, `ciutat`,
`pais`, `email_facturacio`, `tipus_client` són al serializer d'alta (`:98-99`) i al model
(`tenants/models.py:136-159`). Les dades fiscals de LOSAN que aportis dilluns **tenen on anar**.

**Veredicte A2:** la cadena té dues ruptures dures: **la baula 1 (no hi ha pla a PROD)** i **la baula 5
(no hi ha camí de línies manuals)**. La resta és construïble sobre el que ja hi és.

---

## BLOC A3 — Immutabilitat mínima viable

**FET.** El patró que el brief intueix **existeix al mateix app i és copiable literalment**:
- `save()` que llegeix l'estat REAL a la BD abans de decidir (no el de la instància, que podria
  haver-se mutat en memòria) i aixeca si és immutable: `models.py:368-380`.
- `delete()` bloquejat per estat: `:382-384`.
- `NoDeleteQuerySet` per aturar l'esborrat massiu, que **no passa per `Model.delete()`**: `:292-296`.
  Aquest detall és important i ja està resolt allà.

**FET.** `Invoice` no en té cap dels tres.

**FET.** La numeració correlativa sense forats també té patró provat: `reserve_document_number`
(`commerce/services.py:60-77`) reserva amb `select_for_update()` dins de `transaction.atomic()` i
formata `{PREFIX}-{YEAR}-{NNNN}`. **Viu al schema del tenant** (`DocumentSequence` és model de
`commerce`) → per al backoffice (public) cal el **mateix patró**, no el mateix objecte.

**FET.** La rectificativa **NO EXISTEIX** enlloc: cap camp d'`Invoice` apunta a una factura anterior
(cap `rectifica`, cap `parent`).

**Veredicte A3:** el mínim viable és **port de patrons ja provats a casa**, no invenció. Gap concret:
(a) camps `serie`+`numero` + seqüència public, (b) guard `save`/`delete`/queryset a `estat='emesa'`,
(c) camp d'enllaç a la rectificada.

---

## BLOC A4 — Dades reals (PROD · SELECT-only via dump del 17/07 02:30)

**FET · LOSAN NO existeix com a Client a PROD.** `tenants_client` té **exactament 2 files**:
`SYS` (FHORT System) i `FTT` (FHORT Management). Confirma la previsió del brief: alta dilluns matí.

**FET · `tenants_plan` és BUIDA a PROD.** Cap pla. `seed_free_plan` **NO s'ha aplicat**. (Staging en
té 1: Free.)

**FET · `backoffice_servicecatalog` a PROD: 5 entrades**, idèntiques a staging —
`QUOTA_BASE` (tier_fee), `MODEL_INICIAT` (model_count), `SETUP` (manual), `FORMACIO` (manual),
`SUPORT_EXTRA` (manual). El catàleg **ja serveix** per a la factura de dilluns.

**FET · A PROD hi ha 1 factura i 1 contracte, tots dos de prova d'Sprint 6:**
`backoffice_invoice` id=1 → client_id=2 (FTT), period `2026-06`, `auto`, **`esborrany`**, total
`299.00 EUR`. `backoffice_tenantcontract` id=1 → FTT, *"Contracte inicial FTT - prova Sprint 6"*.
Cap dels dos és de LOSAN. La factura de prova **no consumeix cap número** (no n'hi ha).

**FET · Events orfes a PROD** (`backoffice_modelconsumptionevent`): **BRW 7 · LOS 3 · FTT 2**.
Els de **LOS**: **2 al període `2026-06`** i **1 al `2026-07`**. *(Anotat, no proposat: no són l'objecte
de dilluns.)* Nota: `ModelConsumptionEvent` guarda `codi_client` com a text, no com a FK — per això
sobreviuen a l'esborrat del tenant.

**FET · Dades fiscals de FHORT (emissor): JA són al sistema i poblades a PROD.** A
`accounts_tenantconfig` del schema `fhort`:

| camp | valor a PROD |
|---|---|
| `legal_name` | `FHORT MANAGEMENT, SL` |
| `tax_id` | `B01623776` |
| `address` | `Salmerón, 165` |
| `postal_code` · `city` · `country` | `08222` · `Terrassa` · `ES` |
| `email` | `info@fhort.cat` |
| `logo_file` | `tenant_logos/logo.png` |
| **`iban`** | **buit** ⚠️ |
| **`payment_notes`** | **buit** ⚠️ |
| `nom_empresa` | `FHORT TEXTILE TEXH` ⚠️ (sembla error tipogràfic de `TECH`) |

**Veredicte A4:** de les quatre incògnites del brief, tres tenen resposta i cap és la temuda: l'emissor
existeix (falta IBAN), el catàleg de serveis existeix, LOSAN no existeix (previst). **La sorpresa és el
Plan buit**, que bloqueja l'alta.

---

## TAULA FINAL — EXISTEIX / FALTA / A-MITGES

| Peça | Estat | Evidència | Bloqueja dilluns? |
|---|---|---|---|
| `Invoice`/`InvoiceLine` (esquelet) | **EXISTEIX** | `models.py:162-198`, `:263-283` | no |
| Estats esborrany/emesa/pagada | **EXISTEIX** | `:169-174` + `emesa_at` `:184` | no |
| Línies manuals (dada) | **EXISTEIX** | `service` nullable `:269-272` | no |
| Contracte + preu per tenant | **EXISTEIX** | `ContractLine.preu` `:149` | no |
| `SETUP`/`FORMACIO` al catàleg | **EXISTEIX** (PROD) | dump `backoffice_servicecatalog` | no |
| Dades de l'emissor | **EXISTEIX** (poblat) | `accounts/models.py:57-64` + dump | no · falta IBAN |
| `regim_vat` del client | **EXISTEIX** (derivat) | `tenants/models.py:203-220` | no · ningú el llegeix |
| reportlab instal·lat | **EXISTEIX** | `requirements.lock:56` | no |
| Patró PDF fiscal | **EXISTEIX** (a `commerce`) | `commerce/pdf_service.py` (581 l.) | no · cal port |
| Patró numeració atòmica | **EXISTEIX** (a `commerce`) | `commerce/services.py:60-77` | no · cal port |
| Patró immutabilitat | **EXISTEIX** (a F4-legal) | `models.py:368-384`, `:292-296` | no · cal port |
| **Creació de factura manual** | **FALTA** | `billing_service.py:73-74` (skip) | **SÍ** |
| **Número + sèrie** | **FALTA** | cap camp a `Invoice` | **SÍ** |
| **IVA (base/tipus/quota)** | **FALTA** | cap camp ni càlcul | **SÍ** |
| **PDF de la factura** | **FALTA** | cap PDF al backoffice | **SÍ** |
| **Immutabilitat de l'emesa** | **FALTA** | cap guard a `Invoice` | **SÍ** |
| **Plans a PROD** | **FALTA** | `tenants_plan` buida al dump | **SÍ (alta)** |
| Plan "Team" | **NO EXISTEIX** | `tenants/models.py:13-25` vs `pricing_catalog.yaml:14` | **SÍ (decisió D4)** |
| Llistat/detall de factures a la UI | **FALTA** | cap serializer ni vista d'`Invoice` | no (B2) |
| Rectificativa | **NO EXISTEIX** | cap camp d'enllaç | no (si no cal dilluns) |
| Verifactu | **NO EXISTEIX** | — | no (aparcat 2027) |

---

## 💡 PROPOSTES (a validar) — material per al STOP

- **P1 · Numeració (D2).** Portar `reserve_document_number` al backoffice amb un `InvoiceSequence`
  (public) i format `{SERIE}-{YEAR}-{NNNN}`. Amb sèrie `FT` → **`FT-2026-0001`**. El número es reserva
  **en EMETRE**, no en crear l'esborrany: així un esborrany descartat no forada la sèrie.
- **P2 · IVA mínim (D5).** Tres camps a `Invoice` (`base_imposable`, `tipus_iva`, `quota_iva`) +
  càlcul a l'emissió llegint `Client.regim_vat` (ja derivat). Per a LOSAN (ES) → 21%. No cal motor
  multi-règim dilluns; sí cal que el número surti del règim i no d'un literal.
- **P3 · Immutabilitat (A3).** Còpia literal del patró F4-legal sobre `estat='emesa'`: `save()` amb
  lectura de l'estat real a BD + `delete()` + `NoDeleteQuerySet`.
- **P4 · Emissor (D3).** La solució mínima que A1/A4 revelen: **llegir `TenantConfig` del schema
  `fhort`** (ja poblat) des del generador del PDF, com fa `commerce/pdf_service.py:_tenant_cfg`. Cost
  afegit: creuar public→tenant (hi ha precedent de lectura delegada). Alternativa: duplicar les dades
  a public (més aïllat, però dues fonts de veritat per al mateix NIF). **Cal omplir l'IBAN igualment.**
- **P5 · PDF.** Adaptar `generate_document_pdf` en lloc de partir de zero: el layout, les fonts, el
  logo i el bloc emissor/receptor ja estan resolts i aprovats.

---

## Riscos i observacions per al CTO

1. **El `period` és obligatori a `Invoice`** (`CharField(max_length=7)`, sense `null`/`blank`). Una
   factura de serveis (implantació) no té període natural. Caldrà decidir què s'hi posa (p.ex.
   `2026-07`) o relaxar el camp. *No bloqueja, però és una arruga del model.*
2. **La constraint d'idempotència només cobreix `tipus='auto'`** (`:189-195`). Les manuals no tenen
   guarda d'unicitat: dues factures manuals idèntiques són possibles.
3. **`nom_empresa` a PROD diu `FHORT TEXTILE TEXH`.** Si el PDF el mostra, surt el typo a la primera
   factura real del client de màxim volum.
4. **Els 3 events orfes de LOS** (2 de juny, 1 de juliol) segueixen a public sense Client. Si algun dia
   LOSAN té tenant i el motor auto corre per `2026-06`/`2026-07`, **els refacturaria**: `generate_invoice`
   compta events per `codi_client` + `period` (`billing_service.py:63-65`) sense mirar si són d'una
   encarnació anterior del tenant. *Anotat, com demana el brief.*
5. **Divergència de vocabulari Plan vs pricing** (Free/Solo/Studio/Brand/Enterprise vs starter/team).
   `QUOTA_BASE` encara descriu *"tier contractat (Solo/Studio/Brand/Enterprise)"*. Decidir el pla de
   LOSAN obliga a triar quin dels dos vocabularis mana.
