# DIAGNOSI — F2-A P-FITXA: la fitxa de client i el menú de decisió D-P1

> Data: 2026-07-14 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging` branca `dev`.
> Abast: censar què té avui la fitxa de client (Client + TenantContacte + serializers +
> SPA), contrastar-ho amb el que el pla exigeix, i deixar a l'Agus els formularis per
> tancar **D-P1** (quins camps obligatoris a l'alta vs diferits a onboarding). **No s'ha
> tocat cap línia de codi.**
> Convenció: cada afirmació porta `fitxer:línia`. `"NO EXISTEIX"` = confirmat absent al
> codi, no especulat. `💡 PROPOSTA (a validar)` separa disseny de fets.
>
> ⚠️ Docs de base (`PLA_IMPLEMENTACIO_BACKOFFICE.md`, `PLA_MESTRE`, `REGLES_FREE_TIERS`)
> viuen al vault de l'Agus, **no al servidor** — el contrast d'A2 s'ha fet contra la llista
> del brief (Bloc 0.1), no contra el text original.

---

## Resum executiu (les conclusions que desbloquegen D-P1)

1. **La fitxa ja és rica**: `Client` té ~40 camps (identitat, fiscal, adreça estructurada,
   VAT internacional, cicle de vida, referències Stripe, gratuïtat) — `tenants/models.py:118-179`.
   El que falta no són camps fiscals, sinó **relacions vives**: contracte/tarifa i legal.
2. **L'alta ja és gairebé mínima**: al backend només `codi_tenant` + `nom` són tècnicament
   imprescindibles (deriven schema + domini); `plan/tipologia/moneda/idioma` són `required`
   al serializer però tenen default al model; tota la fiscalitat és **opcional** avui
   (`serializers_tenants.py:102-115`).
3. **El hook Free de F3 encara NO existeix**: `SeedProfile.is_default_free` no es consumeix
   enlloc i res llegeix `plan`/`email_facturacio` a l'alta (agent F3). La premissa "el hook
   llegirà plan i email a l'alta" és **intenció futura** → decidir ara si es fan obligatoris.
4. **`tipologia` no és cap frontera dura**: cap `if Client.tipologia` viu; només filtre i
   display (`views_tenants.py:39`). Coherent amb REGLES_FREE_TIERS §9 (perfil conceptual).
5. **Tres forats de coordinació estructurals**: (a) pricing per país no llegeix `Client.pais`
   (només query param, `views_pricing.py:25`); (b) el contracte actiu i la tarifa NO es
   veuen des de la fitxa (mòdul `/contractes` separat, sense enllaç); (c) `idioma` és
   stored-only, cap contracte/factura/email el llegeix.
6. **Realitat de dades**: 3 tenants (FTT, SYS, TST), tots amb `plan=None`, `email_facturacio=''`,
   `onboarding_complet=False`, `es_gratuit=True`; 0 contactes; 1 Plan (Free, sembrat per F3).

---

## BLOC A1 — Cens del que hi ha

### A1.1 Camps de `Client` (`tenants/models.py`)
| Camp | Tipus (línia) | Oblig. avui | Qui l'escriu | On es mostra a la SPA | Poblat als 3 tenants? |
|---|---|---|---|---|---|
| `codi_tenant` | Char(3) unique (`:130`) | **Sí a l'alta** (`serial.:96`, valida `:117-135`); immutable a edició (`serial.:76`) | Create | LIST+DETAIL (`TenantsPage.jsx:188`, `TenantDetailPage.jsx:152`) | Sí (FTT/SYS/TST) |
| `nom` (comercial) | Char(200) (`:118`) | **Sí** (`serial.:103`) | Create+Update | LIST+DETAIL (`:189`,`:153`) | Sí |
| `plan` FK→Plan | nullable (`:119`) | `required` al serial. (`:105`) però **null al model** | Create+Update | LIST + tab Condicions (`TenantDetailPage.jsx:417-420`) | **No — tots `None`** |
| `tipologia` | Char estudi/marca (`:120`) | `required` serial. (`:104`) | Create | LIST + form + display (`TenantsPage.jsx:190`) | Sí (tots `estudi`) |
| `moneda` | Char default EUR (`:126`) | `required` serial. (`:106`) | Create | form + tab Condicions | Sí (EUR) |
| `idioma` | Char default ca (`:128`) | `required` serial. (`:107`) | Create | form (`TenantFormPage.jsx:269`) | Sí (ca) — **stored-only** (A2.6) |
| `unitats` | Char cm/inch (`:127`) | No | Create | form (`:321`) | — |
| `estat` | Char lifecycle (`:133`) | default `onboarding` | `update_estat` (`views:106`) | Badge (`:154`) — **sense UI de canvi** (A3) | FTT/SYS actiu, TST onboarding |
| `onboarding_complet` | Bool (`:124`) | default False | — (cap escriptor viu) | — | **tots False** |
| `rao_social` | Char blank (`:136`) | No | Update (`serial.:81`) | tab Dades fiscals (`TenantDetailPage.jsx:249`) | buit |
| `nif` | Char blank (`:137`) | No | Update | tab Dades fiscals | buit |
| `pais` | Char2 default ES (`:139`) | No (default ES) | Create+Update | tab Adreça | ES |
| `email_facturacio` | Email blank (`:140`) | No (`serial.:113`) | Create+Update | tab Dades fiscals | **buit tots** |
| adreça estruct. (`adreca_linia1/2, ciutat, estat_provincia, codi_postal`) | Char blank (`:143-147`) | No | Create(parcial)+Update | tab Adreça (`:257-264`) | buit |
| `vat_number`,`vat_validat`,`tipus_client`,`regim_vat` | (`:150-159`) | No; `regim_vat` **calculat** (`:203-214`) | Update (`tipus_client`); regim auto | tab Facturació (`:206-211`) | buit / b2b default |
| `stripe_customer_id`,`metode_pagament`,`stripe_payment_method_id` | (`:162-164`) | No | — (cap flux real) | bool-only + placeholder pagament (`:217-227`) | buit |
| `data_suspensio/baixa`,`motiu_baixa` | (`:167-169`) | No | `update_estat` | condicional a DETAIL (`:270-272`) | null |
| `gratis_fins`,`nota_comercial` | (`:172-179`) | No | Update (`serial.:86-87`) | — (LIST serial. exposa, `serial.:34`) | null |
| `feature_flags` | JSON (`:121`) | No | Create+Update | form textarea JSON (`:321`) | {} |
| `actiu` (legacy) | Bool (`:122`) | default True | — | — (`es_actiu` pont, `:191-194`) | — |
| `data_alta` | Date auto (`:123`) | auto | — | LIST (`:193`) | auto |

### A1.2 `TenantContacte` (`tenants/models.py:227-246`)
Camps: `client` FK, `nom`, `cognom`, `carrec`, `email`, `telefon`, `principal`. Constraint:
un sol `principal=True` per client (`:240-245`). Escriptura via acció `contactes`
(`views_tenants.py:152-184`), esborrat via `contacte_detail` (`:186-213`). SPA:
`ContactesSection` (`TenantDetailPage.jsx:288-383`). **0 contactes reals** als 3 tenants.

### A1.3 Sprint 5 (TenantContract / tarifa) — com es llegeix des de la fitxa
`TenantContract` (`backoffice/models.py:103`), `ContractLine.preu` per-tenant (`:134`),
`ServiceCatalog` (`:80`). `billing_service._get_active_contract` (`:18-33`) i
`generate_invoice` (`:36`) els llegeixen. **Des de la fitxa NO es llegeixen**:
`serializers_tenants.py`/`views_tenants.py` no referencien `TenantContract` (grep buit);
la SPA `TenantDetailPage.jsx` tampoc (grep buit). El mòdul `/contractes`
(`App.jsx:28-31`, `api/contracts.js`) és **separat i no enllaçat** a la fitxa.

**Veredicte A1: llest.** Cens complet i ancorat. La fitxa té molt camp; el buit és de
relacions (contracte, legal) i de dades poblades (tot fiscal buit als 3 tenants).

---

## BLOC A2 — El que el pla exigeix i (no) hi és

| Exigència (brief Bloc 0.1) | Estat | Evidència |
|---|---|---|
| País de contractació (per F1-pricing i F5-IVA) | **PARCIAL** | `Client.pais` existeix (`:139`) però és **pivot fiscal** (`recalcular_regim_vat:205-207`); **pricing NO el llegeix** (query param, `views_pricing.py:25`). Cap camp separat de país de contractació (grep buit). |
| Entitat facturable separada del tenant | **FALTA (objecte) / PARCIAL (camps)** | `Invoice.client → Client` directe (`models.py:160`, `billing_service.py:110`). Receptor = camps plans al mateix Client (`rao_social:136`,`nif:137`,`vat_number:150`). Emissor separat a `accounts` TenantConfig (`accounts/models.py:57-59`). No hi ha objecte `BillingEntity`. |
| Referència a mètode de pagament (placeholder F6) | **PARCIAL/placeholder** | Camps declarats (`:162-164`); serial. només exposa `bool()` (`serial.:40-42,66-67`); cap flux Stripe real escriu; tab pagament és placeholder "Sprint 7" (`TenantDetailPage.jsx:217-227`). |
| Historial d'acceptacions legals (placeholder F4) | **FALTA — NO EXISTEIX** | Cap model/camp de consentiment/terms/RGPD (agent greps). Els hits `accept/legal` són d'altres dominis (patró `texts_shown`, `quotes_accepted`). |
| Contracte actiu + tarifa visible/editable des de la fitxa | **FALTA** | Models i billing existeixen (A1.3) però la fitxa no els llegeix; mòdul separat. Editar tarifa avui = anar a `/contractes`. |
| Idioma del client (contractes/factures/emails) | **PARCIAL** | `Client.idioma` existeix (`:128`) però **stored-only**: cap lectura de comportament; `billing_service` fixa `EUR` i no llegeix idioma; el PDF usa `i18n_content` (mecanisme a part), no `Client.idioma`. |
| `tipologia`: ¿s'usa com a gate viu? | **NO (només informatiu)** | Cap `if Client.tipologia`. Usos: filtre (`views_tenants.py:39`), serialització i display. L'únic `if ...tipologia` és `extraction_views.py:584` (tipus de peça, domini diferent). Coherent amb REGLES_FREE_TIERS §9. |

**Veredicte A2: cal decisió.** Cinc de set exigències són FALTA/PARCIAL. Cap és un bug;
són ganxos no cablejats. Alimenten D2 (país), D3 (entitat), D4 (tipologia), D5 (idioma), D6 (layout).

---

## BLOC A3 — El flux d'alta real

**Seqüència SPA** (`TenantFormPage.jsx`, component únic alta+edició, `:50`; ADMIN-only `:204-213`):
demana identitat (`codi_tenant`,`nom`,`tipologia`,`plan`,`moneda`,`idioma` `:238-273`),
dades fiscals i adreça (**cap `required` d'UI**, `:277-318`), configuració
(`unitats`,`feature_flags` `:321-338`). Validació client-side (`validateLocal:128-141`):
només `codi_tenant` (regex `^[A-Z0-9]{3}$`, alta), `nom` no buit, `plan` obligatori,
`feature_flags` JSON parsejable. **La fiscalitat i l'adreça no es validen: buits permesos.**

**Backend** (`ClientCreateSerializer` + `ClientViewSet.create`):
- Tècnicament imprescindibles per crear el tenant: **`codi_tenant`** (deriva `schema_name`
  minúscules `:138` i el `Domain` `{codi}.fhorttextile.tech` `views:68-69`) i **`nom`**.
- `required` al serializer però amb default al model: `plan` (`:105`, però model nullable
  `:119`), `tipologia`/`moneda`/`idioma` (defaults `:120,126,128`).
- Comercials/diferibles (tots `required:False`): `rao_social,nif,adreca_linia1,ciutat,pais,
  email_facturacio,tipus_client` (`serial.:108-114`).
- ⚠️ **Divergència serializer↔realitat**: `plan` és `required` a l'alta SPA, però els 3
  tenants existents tenen `plan=None` (creats per `bootstrap_tenant`, no per l'alta SPA).
  Vol dir que el camí "alta SPA" i el camí "bootstrap" no imposen les mateixes regles.

**Contrast amb el flux objectiu** (alta mínima + completar a onboarding): l'alta ja permet
ometre gairebé tot excepte codi/nom (i els 4 amb default). El que falta per al "clic fàcil"
no és treure camps, sinó **decidir el default de `plan`** (Free automàtic?) i si `email` és
imprescindible per al hook Free. `onboarding_complet` existeix (`:124`) però **cap codi
l'escriu** — no hi ha màquina d'onboarding que el tanqui (candidat a deute F2-B).

**Veredicte A3: llest per decidir.** El terreny tècnic (codi+nom) i el comercial (la resta)
estan clarament separats; falta la política de defaults (D1).

---

## BLOC A4 — Encreuament amb F3 (Free-seed)

- **Estat real F3** (commits `b931d6b` SeedProfile, `e1fcc44` Free-choice, `b7b048f`
  bootstrap `--profile`, `seed_free_plan.py`): `SeedProfile` (`backoffice/models.py:186`)
  guarda una **selecció de blocs de catàleg** + marca `is_default_free`. El Plan Free està
  **sembrat** (`seed_free_plan.py:46-59`: preu 0, `stripe_lookup_*=None`, quotes provisionals).
- **El hook d'alta NO està cablejat**: `is_default_free` no es consumeix enlloc; `bootstrap`
  només aplica perfil via `--profile <id>` explícit (`bootstrap_tenant.py:158-160,350-380`);
  **cap codi llegeix `plan`/`email_facturacio` a la creació del tenant** per disparar la
  sembra. Els reads de `email_facturacio` són els serializers CRUD normals (`serial.:57,99,113`).
- **Conseqüència per a D1**: si el hook Free (futur) ha de llegir `plan` i `email_facturacio`
  a l'alta, avui l'alta SPA **sí** demana `plan` (required) però **no** `email_facturacio`
  (opcional) → `email_facturacio` és **candidat a obligatori-a-l'alta** (o a diferir el hook
  fins a onboarding). Cal coordinar-ho amb F3 abans de cablejar el hook.

**Veredicte A4: cal decisió coordinada.** El ganxo de dades (plan al model, seed command)
hi és; el disparador no. D1 ha de fixar si `email_facturacio` entra a l'alta.

---

# ✅ D-P1 — DECISIONS TANCADES (Agus, 2026-07-14)

> Els formularis originals queden més avall com a **traça** (`💡 PROPOSTA`). Aquesta és la
> **resolució vinculant** i l'input directe del brief de **F2-B**.

| # | Decisió | Matís vinculant per a F2-B |
|---|---|---|
| **D1** | **B** — obligatoris a l'alta: `codi_tenant, nom, plan, pais, email_facturacio` | ⚠️ **`plan` obligatori SENSE default Free silenciós.** L'alta la fa un **operador** al backoffice; un default Free callat significaria que un descuit dispararia la sembra automàtica sencera quan el hook de F3 existeixi. Tria explícita de l'operador. El default Free només tindrà sentit amb **auto-registre públic (self-service)**, altra fase. **Promoure `email_facturacio` a `required`** (coordinació amb el hook F3 tancada). |
| **D2** | **A** — reutilitzar `Client.pais` | Deute real = **connector**: F2-B ha d'incloure que l'endpoint de pricing de F1 **rebi el país de la fitxa** quan es calcula per a un client concret (el `?country=` ja existeix a `views_pricing.py:25`; falta que algú l'alimenti des de `Client.pais`). |
| **D3** | **A** — camps al mateix `Client` (YAGNI total) | Objecte facturable separat **només** el dia que un Enterprise real ho demani, ni un abans. |
| **D4** | **A** — `tipologia` informatiu, cap gate | El perfil derivat de Multi-Customer queda **anotat com a evolució**, no com a feina. |
| **D5** | **A** — camp `idioma` mantingut | Deute de **consum** anotat amb nom: li arriba l'hora amb **F4-legal** i **F7-factures** (els primers documents que s'emeten en un idioma). |
| **D6** | Reaprofitar tabs: ampliar **Condicions** amb contracte/tarifa + tab **Legal** nou (F4) | La **decisió fina de layout** es pren al **Patró B amb captura de l'actual al davant** (premissa d'estil). El brief de F2-B ho ha de demanar **com a primer pas**. |

**Scope resultant per a F2-B (Patró B):**
1. `ClientCreateSerializer`: `pais` i `email_facturacio` → `required` (avui `:112-113`); `plan`
   segueix `required` **sense** injectar default Free. Reflectir-ho a la validació de la SPA
   (`TenantFormPage.jsx:128-141`).
2. **Connector pricing↔fitxa**: quan es calcula pricing per a un client concret, alimentar
   `?country=` de F1 amb `Client.pais` (avui pricing és cec al client).
3. Fitxa (D6): enllaçar el `TenantContract` vigent + tarifa a la tab **Condicions**; afegir
   tab **Legal** (placeholder F4). **Layout fi decidit a Patró B amb captura.**
4. Deutes anotats (no feina d'F2-B): consum de `Client.idioma` (F4/F7), `tipologia`→perfil
   Multi-Customer, `BillingEntity` separat (Enterprise), màquina que tanca `onboarding_complet`,
   i18n de la fitxa.

---

# ⛔ STOP-AGUS — FORMULARIS DE DECISIÓ (traça · resolts a dalt)

> Resolts per l'Agus 2026-07-14 (veure bloc "D-P1 — DECISIONS TANCADES"). Es conserven com a
> traça del raonament i els costos.

### D1 — Camps OBLIGATORIS a l'alta vs diferits a onboarding
| Opció | Obligatoris a l'alta | Cost | Nota |
|---|---|---|---|
| **A · mínim tècnic** | `codi_tenant`, `nom` (plan→default Free auto) | Baix | Cal decidir default `plan=Free` automàtic; la resta a onboarding |
| **B · mínim + comercial essencial** ⭐ | `codi_tenant`, `nom`, `plan`, `pais`, `email_facturacio` | Mitjà | Alinea amb hook Free (A4) i pricing per país (D2); `email` cal per a factura/hook |
| **C · fiscal complet a l'alta** | B + `rao_social`, `nif`, adreça | Alt | Fricció d'alta; enterra el "clic fàcil" |

**Recomanació: B.** És el mínim que fa útil l'alta sense fricció: `plan` ja és required avui,
`pais` ja existeix (default ES), i `email_facturacio` és el que el hook Free i la facturació
necessiten. La resta (fiscal, adreça, VAT, contacte) es completa a onboarding. Cost real de B
= fer `email_facturacio` `required` al `ClientCreateSerializer` + reflectir-ho a la SPA
(1 canvi de flag + 1 regla de validació). Decideix també el **default de `plan`**: Free
automàtic si no s'informa (recomanat, ja hi ha la fila).

### D2 — País de contractació: on i com
| Opció | Cost | Efecte |
|---|---|---|
| **A · reutilitzar `Client.pais`** ⭐ | 0 codi | `pais` (ja existent, default ES) serveix alhora de pivot fiscal i de país de pricing; cal que F1-pricing passi `Client.pais` com a `?country=` (avui no ho fa, `views_pricing.py:25`) |
| **B · camp nou `pais_contractacio`** | Migració + form + omplir 3 tenants (ES) | Separa semànticament pricing (contractació) de VAT (fiscal), per si divergeixen |

**Recomanació: A ara.** Els dos conceptes coincideixen en el 100% dels casos reals actuals
(3 tenants ES). El deute concret és **connectar pricing a `Client.pais`** (avui pricing és
cec al client). Reserva B per si mai apareix un client que contracta des d'un país i factura
des d'un altre. Default per als 3 existents: **ES** (ja hi és, cap acció de dades).

### D3 — Entitat facturable: mateix Client o objecte separat
| Opció | Cost | Quan cal |
|---|---|---|
| **A · camps al mateix `Client`** ⭐ | 0 | Un tenant = una raó social (cas actual) |
| **B · objecte `BillingEntity` separat (1..N)** | Alt: model+FK+migració+refactor `Invoice.client`+SPA | Un client amb múltiples raons socials/filials facturables |

**Recomanació: A (YAGNI).** Avui `Invoice.client→Client` i el receptor viu com a camps del
Client; no hi ha cap cas de N entitats. Reconsiderar B quan entri **Enterprise** (grups amb
filials). Documentar-ho com a deute, no construir-ho ara.

### D4 — `tipologia`: mantenir / deprecar / substituir
Base: **REGLES_FREE_TIERS §9.2** (Brand/Studio = perfil conceptual, NO frontera dura) — i el
codi ho confirma: cap gate viu (A2, `views_tenants.py:39` només filtre).
| Opció | Cost | Nota |
|---|---|---|
| **A · mantenir informatiu** ⭐ | 0 | Segueix com a filtre/etiqueta; no promet cap comportament |
| **B · deprecar el camp** | Migració + treure de form/serial./SPA | Neteja, però perd l'etiqueta útil |
| **C · substituir per perfil derivat de Multi-Customer** | Depèn de Multi-Customer (no existeix encara) | Alinea amb §9.2 quan Multi-Customer defineixi el perfil |

**Recomanació: A a curt termini**, marcat com a **candidat a C** quan Multi-Customer aterri.
No és un gate, així que no urgeix; deprecar-lo ara només mou soroll sense guany.

### D5 — Idioma del client: ara o diferit
`Client.idioma` **ja existeix** (`:128`) però és stored-only (A2.6).
| Opció | Cost | Nota |
|---|---|---|
| **A · mantenir el camp, cablejar el consum després** ⭐ | 0 ara | F4/F6 (contractes/factures/emails) el llegiran; el deute és el **consum**, no el camp |
| **B · treure'l fins que hi hagi consumidor** | Treure del form/serial. | Evita prometre el que no fa |

**Recomanació: A.** El camp ja hi és i no fa mal; el problema real és que res el llegeix.
Deixar-lo i **anotar el deute de consum** (documentar que factures/contractes/emails han de
respectar `Client.idioma`). Treure'l seria feina per tornar-lo a posar.

### D6 — Layout de la fitxa (croquis a validar amb captura de l'actual)
Tabs **ja existents** (`TenantDetailPage.jsx:13-20`): `dades · condicions · facturacio ·
pagament(placeholder) · activitat(placeholder) · tiquets`.

💡 PROPOSTA (a validar) — reaprofitar, no refer:
```
┌─ FITXA CLIENT [codi · nom · badge estat] ────────────────────────┐
│ [Dades] [Condicions] [Facturació] [Legal*] [Activitat]           │
├──────────────────────────────────────────────────────────────────┤
│ Dades        · identitat + fiscal + adreça + contactes  [EXISTEIX]│
│ Condicions   · pla + CONTRACTE actiu + tarifa negociada           │
│                └ AMPLIAR: enllaçar TenantContract (avui NO hi és)  │
│ Facturació   · VAT/règim + mètode pagament + factures emeses      │
│                └ AMPLIAR: mètode pagament és placeholder Sprint 7  │
│ Legal*       · historial d'acceptacions              [NOU · F4]   │
│ Activitat    · log real (avui placeholder Sprint 10)              │
└──────────────────────────────────────────────────────────────────┘
* Legal = tab nou (placeholder) quan entri F4.
```
Canvis mínims respecte a l'actual: (1) a **Condicions**, portar el `TenantContract` vigent i
la seva tarifa (avui viu només a `/contractes`); (2) afegir tab **Legal** (placeholder) per a
F4; (3) fusionar `pagament` dins **Facturació** o mantenir-lo com a subsecció. **Agus decideix
amb la captura de l'actual al costat.**

---

## TAULA FINAL — EXISTEIX / FALTA / PARCIAL (per al CTO)

| Element | Estat | On queda decidit |
|---|---|---|
| Camps fiscals/adreça/VAT a la fitxa | **EXISTEIX** | `tenants/models.py:136-159` |
| Contactes del tenant | **EXISTEIX** | `TenantContacte:227`, SPA `:288-383` |
| Alta mínima (codi+nom deriven schema/domini) | **EXISTEIX** | `serial.:117-139`, `views:67-69` |
| `plan` FK + quotes a la fitxa | **EXISTEIX** (però `plan=None` als 3 tenants) | tab Condicions `:417-420` |
| País de contractació per a pricing | **PARCIAL** (pais fiscal ≠ llegit per pricing) | **D2** |
| Entitat facturable separada | **FALTA** (camps al Client) | **D3** |
| Mètode de pagament operatiu | **PARCIAL/placeholder** | placeholder F6/Sprint 7 |
| Historial d'acceptacions legals | **FALTA — NO EXISTEIX** | placeholder F4 |
| Contracte actiu + tarifa des de la fitxa | **FALTA** (mòdul separat) | **D6** |
| Idioma que dirigeix contractes/factures/emails | **PARCIAL** (stored-only) | **D5** |
| `tipologia` com a frontera dura | **NO EXISTEIX** (només informatiu) | **D4** |
| Hook Free que llegeix plan/email a l'alta | **FALTA** (no cablejat) | **D1 + A4** |
| Màquina que tanca `onboarding_complet` | **FALTA** (cap escriptor) | deute F2-B |
| i18n a la fitxa (ca/en/es) | **FALTA** (només login traduït) | deute (guardià frontend) |

**Cap Patró B fins que l'Agus respongui D1–D6.**
