# DISSENY — Mòdul Comercial Studio (mestre d'articles + pipeline de documents)

> **Estatus: disseny validat, pendent de diagnosi B0 i disseny fi.** Document fundacional del
> projecte "Comercial Studio". Neix del fil de catàleg de tasques (2026-07-07/08) i es
> desenvolupa en xat propi.
> **Data:** 2026-07-08 (v2 — regenerat; la còpia v1 va arribar tallada al servidor a l'Annex A).
> **Decisió:** Agus (Patró C). **Redacció:** Claude Chat.
> **Verificació d'integritat:** el document acaba amb l'Annex A de 9 punts + línia FORMAT + tancament de bloc de codi.
> **Brúixoles:** DISSENY_CATALEG_TASQUES.md · DECISIONS.md · DIAGNOSI_CATALEG_COMERCIAL_FEDERACIO_2026-07-07.md (blocs E/F) · CONTEXT_EMPRESA.md.

---

## 0. Propòsit

Donar al tier **Studio** (tenants que treballen per a tercers) un mòdul comercial complet:
catàleg d'articles i serveis → oferta → comanda → encàrrec → execució (tasques/despeses) →
albarà d'entrega → liquidació + informes. Lligat al catàleg canònic de tasques, al motor de
temps Welford/cascada i al control de marge. **No inclou factura legal**: arribem fins a
albarà + document de liquidació; cadascú factura amb el seu programa.

El tier **Brand** (treballa models propis) NO veu aquest mòdul (gate per flag de Plan,
activable des del backoffice, preu de tier diferent).

---

## 1. El cas fundacional: Brownie

Es va pressupostar a Brownie un **pack** que incloïa una tasca que finalment **no es va
executar**, i ara demanen refer el preu. Avui això és una discussió per email; el mòdul ho ha
de resoldre per construcció:

1. **Oferta ràpida**: pressupostar un pack amb preus derivats de cost estàndard (Welford ×
   tarifa) + externs (cost proveïdor + markup) en minuts, no dies.
2. **Recepta congelada**: l'oferta acceptada congela preu I recepta a la comanda/encàrrec.
3. **Delta bidireccional a l'entrega**:
   - Tasca executada FORA de recepta → **extra** (facturar / absorbir / descartar — decisió
     conscient del PM).
   - Tasca de recepta NO executada → **regularització negativa** (deducció proposada a
     l'albarà/liquidació, amb decisió conscient del PM).
4. **Test d'acceptació real del mòdul**: reproduir el cas Brownie de punta a punta i que el
   sistema proposi la regularització sola.

---

## 2. Principis i lleis aplicables (heretats, no negociables)

- **Tres eixos separats** (DECISIONS): Tasques (catàleg canònic, 14 codes) · Gates
  (GateEvent) · Espera de taller (events de calendari). **Un servei extern NO és una tasca**:
  no crea ModelTask, no entra al Kanban, no toca Welford. Crea despesa + (opcional) event de
  calendari; el lead time es mesura a la capa d'events.
- **Welford pur, llindar 5**: l'empíric només conté mostres reals. El cost estàndard d'un
  servei intern = Σ cascada(GTI, task_code de la recepta) × tarifa interna.
- **Dues facturacions separades**: backoffice→tenant (ús de plataforma, domini public,
  aparcat) ≠ studio→tercers (aquest mòdul, tenant-side). No comparteixen entitats.
- **Preu = decisió comercial, mai fórmula cega**: el sistema PROPOSA (cost + markup /
  Welford × tarifa) i informa el marge; l'humà fixa. Preu sempre editable a la línia.
- **Snapshot**: preus i receptes es congelen al document (oferta acceptada → comanda →
  encàrrec). Els canvis de catàleg no afecten documents vius.
- **Referència per code**, mai per PK, per a tot el que sigui canònic (task_codes, GTI).
- **Naming BD i codi: ANGLÈS** (afinitat developers/estàndards). Català només a UI (i18n
  ca/en/es amb i18n-gate) i documents impresos.
- **Codi mínim · additiu**: cap peça toca el nucli tècnic (mesures/grading/fitting). Únics
  camps sobre entitats existents: ModelTask (+2), Customer/Supplier (ampliació),
  TenantConfig (+1).
- **Federation-aware**: WorkOrder amb camp `origin` (MANUAL | EXTERNAL_BUS) des del dia u;
  l'albarà és el document que viatjarà Studio→Brand a la fase F2 de federació. Cap altra
  peça de federació entra aquí.

---

## 3. Mestre d'articles

### 3.1 `Product` — una taula, quatre natures

| nature | Exemple | Cost | Genera en executar |
|---|---|---|---|
| `INTERNAL_SERVICE` | Patró base, Fitting, Fitxa tècnica | Welford(recepta × GTI) × hourly_rate | WorkOrder → ModelTasks |
| `EXTERNAL_SERVICE` | Plot Manila, Tall mostra, Conversió CAD, Enviament | Preu compra proveïdor | Expense (+ event calendari si escau) |
| `GOODS` | Teixit, paper, avios | Preu compra proveïdor | Expense |
| `PACK` | "Fitting + fitxa" | Σ components | El que generin els components |

Camps nucli: `code` (slug únic), `name` (EN canònic; display i18n si escau), `nature`,
`price_mode`, `base_price`, `markup_pct`, `unit` (FK), `active`, timestamps.

### 3.2 Dos modes de preu de venda (`price_mode`)

- **`FIXED`**: preu per unitat (peça, hora, enviament, joc, metre, kg). `qty` decimal a la
  línia cobreix "3,5 hores" i "12 metres × €/m".
- **`TIME_BASED`**: preu derivat = temps estimat (cascada Welford per al GTI de la línia) ×
  tarifa de venda + markup. És el SAM×€/min del sector (v. §8) amb SAM empíric propi.
- En ambdós modes el sistema proposa i l'humà pot sobreescriure a la línia.

### 3.3 Satèl·lits

- **`ProductRecipe`**: product (INTERNAL_SERVICE) → task_codes amb qty esperada. La recepta
  és el contracte contra el qual es computen extres i regularitzacions.
- **`ProductSupplier`** (N:M): un producte extern/goods amb **diversos proveïdors i preus de
  cost diferents**. A la línia es tria proveïdor (default: més barat); el marge es calcula
  contra el cost del triat. FK al catàleg Supplier existent.
- **`ProductComponent`**: composició de PACK, **un sol nivell** (packs de packs: NO v1). Preu
  del pack: tancat (FIXED) o suma de components.
- **`ProductPriceGTI`**: matriu opcional preu per servei × GarmentTypeItem. Si no hi ha fila,
  mana `price_mode`. La pantalla mostra al costat de cada cel·la el cost estàndard Welford i
  el marge resultant.
- **`Unit`**: taula petita (no enum): peça, hora, enviament, joc, metre, kg. Separada del
  `unitat_mesura` cm/inch de TenantConfig (una altra cosa).

---

## 4. Pipeline de documents

```
QUOTE (oferta) ──acceptada──▶ SALES ORDER ──model imputat──▶ WORK ORDER ──▶ execució
  línies snapshot               (comanda, línies fermes)      (encàrrec)     tasques/despeses
                                                                   │
                                                        DELIVERY NOTE (albarà)
                                                     tasques entregades + extres
                                                     + regularitzacions negatives
                                                                   │
                                                        SETTLEMENT (liquidació)
                                                    agregat per període/client +
                                                    marca invoiced (facturat s/n)
```

- **Quote**: estats draft/sent/accepted/rejected/expired. Acceptar = **copiar** (no
  referenciar) línies a SalesOrder — preu i recepta congelats.
- **SalesOrder**: `qty_ordered` vs `qty_allocated` per línia (control de cartera: "12
  contractats, 9 imputats").
- **WorkOrder** (encàrrec): model × order line, preu snapshot, recepta snapshot, `origin`,
  estat. `ModelTask.work_order` (FK nullable) + `ModelTask.off_recipe` (bool).
- **Expense**: execució d'una línia externa — proveïdor triat, cost real, preu venda.
- **DeliveryNote**: tasques entregables + extres + **deduccions per recepta no executada**
  (cas Brownie). No es pot tancar un WorkOrder amb extres/deduccions sense resoldre.
- **Settlement**: agregat d'albarans, exportable (PDF + CSV/XLSX), camp `invoiced` manual.
  **La factura legal queda FORA** (peça pròpia futura, ben investigada: numeració, IVA,
  Verifactu).

### Decisions comercials tancades (2026-07-07/08)
1. **Cost intern v1: tarifa plana** — `TenantConfig.hourly_rate`. Per-perfil = afinament v2
   (TimerEntrada ja sap qui; no tanca portes).
2. **Fitting: per sessió** (cada convocatòria = 1 unitat; packs amb qty=N si cal).
3. **Recepta oberta amb marca**: el PM pot afegir tasca dins d'un encàrrec → `off_recipe`,
   decisió conscient al tancament (facturar/absorbir). La rigidesa mataria l'ús real.
4. **Oferta A V1 i primerenca** (correcció Agus 2026-07-08): és el dolor real amb Brownie.
5. **Preu extern: fix amb markup** + multi-proveïdor amb preus diferents per article.
6. **Benchmark: minuts** (veritat física); slots = presentació comercial futura.

---

## 5. Naming (BD/codi anglès — fixat)

| Concepte (conversa) | Model Django | Notes |
|---|---|---|
| Article | `Product` | NO "Item" (col·lisió mental amb GarmentTypeItem = GTI) |
| Recepta | `ProductRecipe` | task_codes + qty |
| Article-proveïdor | `ProductSupplier` | N:M amb cost |
| Component de pack | `ProductComponent` | 1 nivell |
| Matriu preu×GTI | `ProductPriceGTI` | opcional |
| Unitat | `Unit` | taula |
| Oferta | `Quote` / `QuoteLine` | |
| Comanda | `SalesOrder` / `SalesOrderLine` | NO "Order" sol (ambigu: ordering/default_order) |
| Encàrrec | `WorkOrder` | camp `origin` federation-aware |
| Despesa | `Expense` | |
| Albarà | `DeliveryNote` / `DeliveryNoteLine` | |
| Liquidació | `Settlement` | camp `invoiced` |
| Tarifa interna | `TenantConfig.hourly_rate` | |

⚠️ **B0 ha de verificar col·lisions** de tots aquests noms amb classes existents al codi.

---

## 6. Inventari complet del mòdul

### 6.1 Taules
**Noves (~13):** Unit · Product · ProductRecipe · ProductSupplier · ProductComponent ·
ProductPriceGTI · Quote · QuoteLine · SalesOrder · SalesOrderLine · WorkOrder · Expense ·
DeliveryNote(+Line) · Settlement.
**Ampliacions (4):** Customer (fiscals: NIF/tax_id, adreça facturació, condicions pagament,
% dte., contacte; `codi_global` ja reservat per federació) · Supplier (fiscals, condicions
compra, contacte) · ModelTask (`work_order` FK nullable + `off_recipe` bool) · TenantConfig
(`hourly_rate`).

### 6.2 Pàgines (menú nou "Comercial", gate per tier)
1. **Productes** — llista + fitxa (natura, preus, recepta, proveïdors, components) + matriu
   preu×GTI amb cost Welford i marge al costat.
2. **Clients** (ampliació de l'existent) — pestanya comercial: condicions, ofertes/comandes.
3. **Proveïdors** (ampliació) — condicions, articles que serveix.
4. **Ofertes** — llista + editor de línies + accions (enviar, acceptar→comanda, PDF).
5. **Comandes** — llista + fitxa amb línies, % imputat, marge en curs.
6. **Albarans / Liquidació** — pendents → generar → llista → liquidar → marcar facturat.
7. **Quadre de marge** — per encàrrec/comanda/client (v1 pot viure dins Comandes).

### 6.3 Modals (7)
1. Editor de línia (quote/order): producte → GTI si escau → qty → preu proposat editable.
2. Selector de proveïdor per línia externa (preus comparats).
3. Assignar línia de comanda a model (wizard + ModelSheet per a models existents).
4. Extra detectat (off_recipe): facturar / absorbir / cancel·lar.
5. Tancament de WorkOrder: resum temps/cost/marge/extres/**deduccions**.
6. Generar albarà: selecció de tasques entregables + extres + regularitzacions.
7. Convertir oferta→comanda (confirmació + congelació).

### 6.4 Documents impresos (PDF) + exports
- PDF: Oferta · Confirmació de comanda · **Albarà d'entrega** · Liquidació de període.
- Export CSV/XLSX de la liquidació i de tots els informes.
- ⚠️ B0: decidir pipeline PDF (reutilitzar el de fitxa tècnica pdf-lib vs generació backend).

### 6.5 Informes (1 motor d'export genèric + N definicions; filtres període/client/estat)
1. Ofertes: presentades/acceptades/rebutjades/caducades, ràtio conversió, imports.
2. Comandes en curs: línies, % imputat, **dates d'entrega compromeses vs real**.
3. WorkOrders: estat, temps consumit vs estimat, marge en curs.
4. Albarans entregats + **condició facturat sí/no**.
5. Extres i regularitzacions: pendents/facturats/absorbits.
6. Marge per client/servei/GTI.
7. Vendes per producte (volum, marge mitjà).

### 6.6 Gate de tier
Flag `commercial_module` al Plan (public). Gate a backend (permisos/router) i frontend
(menú+rutes). La pantalla d'administració del flag viu al **projecte backoffice**, no aquí
— v1 s'activa per BD/admin.

---

## 7. Relació amb la resta del sistema

- **Catàleg de tasques (14 codes)**: la recepta hi referencia per code. Catàleg obert (motor
  DXF ampliarà) → receptes admeten codes nous sense migració.
- **Cascada de temps (T2, construïda)**: font del cost estàndard TIME_BASED i de la matriu
  preu×GTI. Si la cascada demana captura (needs_estimate), la pantalla de preus la mostra.
- **Wizard de model**: `garment_type_item` passa a **obligatori** (forat conegut, diagnosi
  F1) + selector de línia de comanda (filtrat per GTI compatible i qty disponible; opcional
  per a models interns). Triar línia = crear WorkOrder.
- **TaskTree/Pla de treball**: marca visual dins/fora recepta (filet grana amb dada real).
- **Suppliers (existent)**: FK de ProductSupplier i Expense.
- **Events de calendari**: una Expense de servei extern amb espera de taller crea/lliga
  l'event sortida→entrada; lead time es mesura allà (mai Welford).
- **Federació (futur, NO aquí)**: WorkOrder.origin=EXTERNAL_BUS; DeliveryNote viatja
  Studio→Brand a F2. Prerequisits R5/R9/R10 pendents, fora d'aquest projecte.
- **Precedent Frappe (lliçó)**: la cohort Tasca/PaquetServei (esborrada 2026-06-26) era
  aquest mateix concepte construït ABANS de tenir catàleg canònic + Welford + encàrrec. Ara
  la maquinària existeix: es construeix ENDOLLAT des del dia u, no com a illa.

---

## 8. Referència sectorial: SAM/CMT (FHORT_Calc_SAM_CMT_v1.xlsx)

El sector preua confecció per SAM (temps estàndard per operació, taules MTM/GSD) × €/min ÷
eficiència × (1+markup). El nostre TIME_BASED és l'anàleg per a desenvolupament tècnic amb
**SAM empíric (Welford)** en lloc de taules teòriques — avantatge competitiu.
**Horitzó (NO v1):** la calculadora SAM/CMT com a mòdul d'estimació de cost de producció per
a clients del Studio (tipologia × origen → preu sortida taller). El camp `nature` deixa la
porta oberta (una futura natura d'estimació).

---

## 9. Decisions obertes (per al disseny fi al xat nou)

1. Estructura exacta de línies (camps comuns Quote/Order — herència abstracta o duplicació).
2. Numeració de documents (sèries per tipus? per any? configurable?).
3. On viu la tarifa de VENDA del TIME_BASED (≠ hourly_rate de cost): per producte, per
   tenant, o markup sobre cost — decidir amb B0.
4. UX de la matriu preu×GTI (57 items × N serveis — no pot ser graella infinita).
5. Estats exactes de WorkOrder i quan es pot tancar (política de deduccions pendents).
6. Pipeline PDF (depèn de B0).
7. Si Quote/SalesOrder viuen en app Django nova (`commerce`?) o dins d'app existent.

---

## 10. Pla de blocs (ordre fixat 2026-07-08)

| Bloc | Contingut | Sessions CC |
|---|---|---|
| **B0** | Diagnosi read-only (annex A) | 0,5 |
| **B1** | Mestre: Unit, Product + 4 satèl·lits, ampliació Customer/Supplier, pàgina Productes, hourly_rate | 1,5-2 |
| **B2** | Quote + QuoteLine + pàgina + modals 1-2-7 + PDF oferta ← **valor Brownie** | 1,5-2 |
| **B3** | SalesOrder + WorkOrder + wizard (GTI obligatori + línia) + Expense + extres (modal 4) + marca TaskTree | 1,5-2 |
| **B4** | DeliveryNote + Settlement + regularització negativa + modals 5-6 + PDFs + motor d'informes (7) | 2 |
| **B5** | Gate de tier (flag Plan + gates back/front) | 0,5 |

> **B5 depèn de**: exposar `feature_flags` a `/me` (`accounts/serializers.py:16-33`, absent
> avui). Petit però bloquejant; primer pas del brief de B5.

Total estimat: **8-10 sessions** de Claude Code (patró-b, briefs curts amb skills T0).
Cada bloc = sessió(ns) pròpia amb regla del verd; push i validació visual d'Agus entre blocs.

---

## 11. Mètode (reconfirmat 2026-07-08)

- Claude Chat: disseny, arquitectura, briefs. Agus: pont, valida, push, executa a VS Code.
  Claude Code: executa amb skills (CLAUDE.md + patro-a/patro-b + 8 agents, commit 88c472b).
- Primer investigar, després construir. Cap decisió que afecti altres parts sense investigar.
- Codi mínim per funcionalitat. Verd = continuar.
- Final de sessió: actualitzar fitxers d'estat al servidor + còpia manual al projecte.
- Diagnosis: arrel docs/diagnosis/ = vigents; arxiu/ = històric segellat, mai font de veritat.

---

## Annex A — Brief B0 (diagnosi, llest per llançar)

```
Aplica la skill patro-a.

OBJECTIU: terreny real abans del disseny fi del mòdul Comercial Studio.
Output: docs/diagnosis/DIAGNOSI_COMERCIAL_B0_<data>.md

PREGUNTES:
1. TipologiaModel (57 files, viva): què és, camps, consumidors backend/frontend.
   Solapa amb el concepte Product/tipologia comercial o és una altra cosa?
2. Customer i Supplier: TOTS els camps actuals, serializers, pàgines frontend
   que els editen. On s'ancoren les ampliacions fiscals/condicions.
3. Restes de quote/pressupost/oferta al codi (viu o fòssil): grep quote,
   budget, pressupost, oferta, proposal. També PaquetServei residual (ha de
   ser 0 post 2026-06-26).
4. Pipeline PDF actual: com genera la fitxa tècnica els PDF (pdf-lib frontend?
   backend?), és reutilitzable per a documents comercials (oferta/albarà/
   liquidació) o cal peça backend nova?
5. TenantConfig: camps actuals, on s'edita, encaix de hourly_rate.
6. Col·lisions de naming: existeixen classes/models Product, Unit, Quote,
   SalesOrder, WorkOrder, Expense, DeliveryNote, Settlement, Order (i taules
   homònimes)? Backend I frontend (components).
7. Wizard de model: punt exacte on garment_type_item es captura (fitxer:línia)
   i què cal per fer-lo obligatori + afegir selector de línia.
8. Estructura d'apps: on encaixa una app nova `commerce` (INSTALLED_APPS,
   TENANT_APPS) — llistar el patró de les apps tenant existents.
9. Gate per capability/tier existent: com es gategen avui pàgines i endpoints
   per capability (CONFIGURE etc.) — patró a reutilitzar per commercial_module.

FORMAT: veredicte per pregunta + taula de riscos. Read-only estricte.
```
