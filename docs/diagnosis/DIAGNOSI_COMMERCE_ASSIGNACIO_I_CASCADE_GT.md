# DIAGNOSI — Commerce: assignació model↔comanda + cascade GarmentType

> Data: 2026-07-20 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`, schema `fhort`.
> Abast: (A) la banda COMANDA del vincle model↔comanda (anatomia, modal d'assignació, endpoint assign-model,
> camí invers, consumidors riu avall); (B) el selector en cascada GarmentType→Item i el seu "retall".
> Convenció: cada afirmació porta `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi** (no especulat).
> Complement de: `DIAGNOSI_BULK_FILTRES_I_TASQUES_PLANIFICACIO.md` (avui) que cobreix la banda Models
> (ActionsMenu "Assignar a comanda" → loop per-model contra el mateix endpoint).

> ⚠️ **Correcció de premissa del brief:** el brief parla d'`Order`/`OrderLine` i `commerce/models.py`. Al codi real
> **NO EXISTEIXEN classes `Order`/`OrderLine`**: són **`SalesOrder`** (`commerce/models.py:288`) i **`SalesOrderLine`**
> (`commerce/models.py:335`). L'endpoint `commerce/order-lines/{id}/` enruta a `SalesOrderLineViewSet` (basename
> `commerce-order-line`, `commerce/urls.py`). Els ancoratges `WorkOrderAdjustment.model_task:553` i
> `DeliveryNoteLine.model_task:706` re-verificats correctes.

---

## Resum executiu (les conclusions que desbloquegen la decisió)

1. **La línia de comanda NO té dada de producció.** `SalesOrderLine` és purament comercial (`product` + `quantity` +
   `unit_price` + `qty_allocated`); **NO té** garment_type, garment_type_item, talles, dates ni tasques
   (`commerce/models.py:335-356`). Tota la dimensió model/garment viu al **`WorkOrder`**.
2. **El vincle línia↔model és INDIRECTE via `WorkOrder`** (through de facto): `WorkOrder.order_line` +
   `WorkOrder.model`, totes dues FK PROTECT nullable (`commerce/models.py:480-485`). NO EXISTEIX cap FK directa
   `SalesOrderLine.model`. Cardinalitat: 1 línia → N WorkOrders; 1 model → N WorkOrders (amb guard anti-duplicat ORDER OPEN).
3. **`assign-model` és unitari i d'un sol sentit.** Cada crida = +1 a `qty_allocated` + 1 `WorkOrder` ORDER + migració
   de tasques. **NO EXISTEIX camí invers** (desassignar) per API — irreversible sense tocar BD.
4. **Cap coherència de garment_type imposada** a l'assignació (la línia no en té); només un **warning no bloquejant**
   si el model no té `garment_type_item` (`services.py:247-248`).
5. **`Model.has_order` NO és camp persistit** sinó anotació derivada `Exists(WorkOrder ORDER)` (`models_app/views.py:87`).
   Assignar el fa "True" per efecte lateral; coherent amb l'absència d'unassign (l'estat es recalcula sempre).
6. **El "retall" del cascade GT és una restricció per `target` sobre el NIVELL 1** (famílies/grups), introduïda a
   l'Onada 1 (`dbd5cfd`, `6bbbc67`...). El nivell 2 (Item) **sempre** s'ha filtrat pel nivell 1 i no s'ha tocat. El retall
   per target **només s'aplica on es passa `target`** (Wizard de Model + Grading Rules); **Onada 2 (6 superfícies + pàgina
   GarmentTypes) PENDENT** segons diagnosi vigent.

---

# BLOC A — Assignació model ↔ comanda (banda COMANDA)

## A1 · Anatomia de SalesOrder / SalesOrderLine (P1)

### Camps
- **`SalesOrder(AbstractDocument)`** (`commerce/models.py:288-332`). Hereta d'`AbstractDocument` (`models_base.py:15-65`):
  `document_number`, `doc_type`, `customer` (FK `tasks.Customer` PROTECT), `status`, `issued_at`, `valid_until`,
  `payment_terms`, `subtotal`, `tax_amount`, `total`, `tax_breakdown` (JSON), `notes`, `created_*`. Propis:
  `source_quote` (OneToOne `Quote` PROTECT unique → 1 oferta↔1 comanda, `:304`), `status` amb `SO_STATUS_CHOICES` (`:307`).
- **`SalesOrderLine(AbstractDocumentLine)`** (`commerce/models.py:335-356`). Hereta d'`AbstractDocumentLine`
  (`models_base.py:68-88`): `product` (FK `commerce.Product` PROTECT, `:76`), `description`, `quantity` (`:80`),
  `unit_price` (congelat, `:81`), `line_total` (`:83`), `position`. Propis: `order` (FK `SalesOrder` CASCADE,
  related_name `lines`, `:339`) i **`qty_allocated`** (Decimal default 0, `:340`).
- **FET clau:** la línia **NO té** garment_type, garment_type_item, talles/size_run, dates pròpies, tasques ni customer
  propi (el customer viu al header `order`). La dimensió producció s'enllaça NOMÉS via el `Model` del WorkOrder + el `product`.

### Cardinalitat línia↔model (NO és FK directa)
- `SalesOrderLine` **NO té camp `model`**. El vincle és **indirecte via `WorkOrder`**:
  - `WorkOrder.model` → FK `models_app.Model` PROTECT nullable, related_name `work_orders` (`commerce/models.py:480-482`).
  - `WorkOrder.order_line` → FK `SalesOrderLine` PROTECT nullable, related_name `work_orders` (`commerce/models.py:483-485`).
- 1 línia → **N WorkOrders** (`line.work_orders`, `views.py:222`). 1 model → N WorkOrders, amb guard: **un model no pot
  tenir dos WO kind=ORDER status=OPEN alhora** (`services.py:243-244`).
- Una línia amb `quantity` N espera **N assignacions**: cada `assign_model` imputa **+1** a `qty_allocated`
  (`services.py:261`); el guard bloqueja quan `qty_allocated >= quantity` (`services.py:241-242`).

### Estats/cicle de vida
- `SalesOrder.SO_STATUS_CHOICES` = OPEN / COMPLETED / CANCELLED (`:299-303`, default OPEN `:307`).
- `SalesOrderLine`: **cap estat propi**; única mutació = `qty_allocated` (`unit_price`/`quantity` read-only per API, docstring `:336-338`).
- `WorkOrder.STATUS_CHOICES` = OPEN / CLOSED (`:471-474`); `KIND_CHOICES` ORDER/COLLECTOR (`:463`); `ORIGIN_CHOICES` (`:467`).

**Veredicte A1:** la línia és un objecte comercial pur; el `WorkOrder` és el through de facto que porta model + preu
congelat + recepta. La cardinalitat real és línia→N·WorkOrder→1·Model (imputació unitària).

## A2 · Modal d'assignació des de la comanda (P2)

- Pantalla: `frontend/src/pages/OrderDetail.jsx`; modal INLINE `OrderDetail.jsx:242-315` (no és component separat).
- Disparador: botó `ti-link` a la fila (`OrderDetail.jsx:172`, `openAssign(l)` `:95-100`). Guard de visibilitat (`:171`):
  `canEdit && order.status==='OPEN' && Number(l.qty_allocated) < Number(l.quantity)` (`canEdit` = capability `configure`, `:51`).
- Càrrega de models: `modelsApi.list(params)` → `GET /api/v1/models/` (`endpoints.js:42`), dins `useEffect` amb debounce 200ms
  (`OrderDetail.jsx:109-118`), paginat `PICK_PAGE=40` (`:29`). **SINGLE-select** (`picker.modelId` únic, `:62`; clic sobreescriu, `:280`).
- Mostra per model: `codi_intern` (`:285`), `nom_prenda` (`:286`), `fase_actual` pill (`:287`). Si count>carregats → avís
  "Refina la cerca" (`:293-297`).

### Prefiltre automàtic (params a `models.list`, `OrderDetail.jsx:104-107`)
- **`customer: order.customer`** — únic prefiltre automàtic del document (sempre, `:104`).
- `ordering:'-data_entrada'` fix; `page_size:40`.
- `search`, `temporada` (SS/FW/CO/SP), `collection` — **manuals**, neixen buits (`setPq({search:'',temporada:'',collection:''})` `:97`).
- **NO passa `garment_type`/`garment_type_item` de la línia** (la línia no en té). El GTI només és **avís post-selecció**:
  si el model triat no té `garment_type_item_nom` → "El model no té garment type; comprova la compatibilitat" (`:299-305`).

### Flux línia-a-línia (P2)
- `doAssign` (`OrderDetail.jsx:134-147`): `assignModel(line.id, {model_id})` (`:137`), toast "Encàrrec {wo} creat · {n}
  tasques migrades" (`:140`), **tanca el modal** (`:141`) i **recarrega la comanda sencera** (`reload()` `:142`).
- **NO avança automàticament a la línia següent** — cap lògica "next line". Per una altra línia cal reclicar `ti-link`.
- Pendents: per línia, columna `qty_allocated/quantity` (`:158-159`) i el botó desapareix quan és plena (`:171`); a nivell
  comanda, `allocatedPct(order)%` (`:213`). Expansió lazy `LineExpansion` (`:335-372`) via `orderLines.allocation` (read-only).
  **No hi ha comptador explícit de "N línies pendents".**
- **Un model per confirmació** (single-select); per més cal reobrir. **NO permet desassignar** des d'aquí (cap crida delete/unassign).

**Veredicte A2:** picker single-select filtrat **només pel client** de la comanda; garment_type de la línia no prefiltra
(només warning). Cada confirmació = 1 model, tanca i recarrega, **no encadena**. Mirall exacte de la banda Models→Comanda
(`ActionsMenu.jsx:190`, bulk N models) contra el mateix endpoint.

## A3 · assign-model per dins (P3)

### View + servei
- View: `SalesOrderLineViewSet.assign_model` (`commerce/views.py:237-255`), `@action POST url_path='assign-model'`, gate
  CONFIGURE (`_ConfigureWriteMixin`). Body `{model_id}` → resol Model (404 `:246-247`) → `assign_model_to_order_line` →
  201 `WorkOrderSerializer` + meta, o 400 amb `ValidationError` (`:252-253`).
- Servei: `assign_model_to_order_line(model, order_line, user)` (`commerce/services.py:223-275`).

### Validacions (guards durs, ABANS de la transacció)
- `order.status != 'OPEN'` → bloqueja (`services.py:237-238`).
- `model.customer_id != order.customer_id` → bloqueja (coherència de client, `:239-240`).
- `qty_allocated >= quantity` → bloqueja (límit de cartera, `:241-242`).
- Ja existeix `WorkOrder(model, kind='ORDER', status='OPEN')` → bloqueja (anti-duplicat, `:243-244`).
- **NO EXISTEIX validació de coherència garment_type línia↔model** (la línia no en té). Únic senyal: **warning no
  bloquejant** si `model.garment_type_item_id is None` (`:247-248`).

### Efectes col·laterals
- Crea `WorkOrder` kind=ORDER, origin=MANUAL, amb `price_snapshot` (unit_price + product_code) i `recipe_snapshot`
  (task_codes de `product.recipe_lines`) **congelats** (`services.py:253-258`).
- `order_line.qty_allocated += 1` (`:261-262`).
- **Migra** les `ModelTask` del model que penjaven d'un WO COLLECTOR cap al nou ORDER, recalculant `off_recipe` contra la
  recepta congelada (`:268-273`); retorna `migrated_tasks`.
- **NO escriu `Model.has_order`** (no és camp persistit; és `Exists(WO ORDER)` a `models_app/views.py:87`, serialitzat
  read-only `serializers.py:94`). L'assignació el fa "True" DERIVAT.
- **NO dispara cap recompute de pla** dins el servei (cap crida al planner). Únic recàlcul = `off_recipe` per tasca migrada.
- **Transaccionalitat:** tot el bloc d'escriptura sota `transaction.atomic()` (`:250`); els guards durs són abans.

### Camí invers
- **NO EXISTEIX.** Cap `unassign`/`detach`/`remove_model`; `SalesOrderLineViewSet` només té `allocation` (GET) i
  `assign_model` (POST) (`views.py:200-255`); `WorkOrderViewSet` només `close` (`views.py:258-265`). Un cop assignat →
  WO ORDER, no hi ha via API per revertir ni restar `qty_allocated`.

### Consumidors riu avall (el vincle sempre es propaga via WorkOrder)
- `WorkOrderAdjustment.work_order` (CASCADE `:551`) + `.model_task` (`tasks.ModelTask` SET_NULL, **`:553`** re-verificat).
- `Expense.work_order` (CASCADE `:588`).
- `DeliveryNoteLine` (`:685-749`): 5 FK de traçabilitat nullable — `work_order` (PROTECT `:703-705`), `model_task`
  (SET_NULL **`:706`** re-verificat), `expense` (SET_NULL `:708`), `adjustment` (SET_NULL `:710`), `model` (SET_NULL `:724`).
- Propagació a facturació: `generate_delivery_note` (`:278-403`) treu preu del **snapshot del WO** (no de la línia viva);
  `add_lines_to_draft`/`get_billable_items` (`:459-633`) resolen `product`/`price` via `wo.order_line.product` + `wo.price_snapshot`
  quan `kind=='ORDER'`, i omplen `DeliveryNoteLine.model` des de `model_task.model`.
- **TROBALLA TRANSVERSAL:** `price_snapshot`/`recipe_snapshot` congelats a l'assignació (`services.py:256-258`) són l'ÚNICA
  font de preu i recepta que arriba a l'albarà. Tocar el disseny d'assignació impacta facturació (DeliveryNote) i el gate
  d'extres off_recipe, no només la comanda.

**Veredicte A3:** `assign-model` = operació unitària, atòmica, d'un sol sentit, sense coherència de garment ni recompute de
pla. El punt de fricció clar és l'**absència de camí invers** (irreversible per API).

---

# BLOC B — Cascade GarmentType → GarmentTypeItem (P4)

## B1 · Inventari dels selectors de dos nivells

- **Canònic:** `GarmentTypeSelector.jsx` (`frontend/src/components/GarmentTypeSelector/GarmentTypeSelector.jsx`). Nivell 1
  (famílies) via `useGarmentCatalog(target)` (`:29`); nivell 2 (ítems) **peresós en clicar la família**, filtrat pel nivell 1:
  `garmentTypeItems.list({ garment_type: f.id, active:'true', page_size:200 })` (`:49`, dins `openFamily` `:47-53`).
  Consumit per: ModelWizard (`ModelWizard.jsx:411`), POMBrowser (`POMBrowser.jsx:217`), GarmentPOMMapEditor (`GarmentPOMMapEditor.jsx:120`).
- **Cascada llarga (grading):** `AxesSelector.jsx` — target→construcció→fit→grup→família→ítem; ítem filtrat per família
  `garmentTypeItems.list({ garment_type: garmentTypeId, ... })` (`:41`, useEffect dep `[garmentTypeId]` `:39-45`). Muntat a
  `GradingRuleSets.jsx:93-103`.
- **Cascada d'abast:** `ScopeSelector.jsx` (GROUP/TYPE/ITEM), ítem filtrat per família (`:52`).
- Font única del nivell 1: `garmentCatalog.js` (`useGarmentCatalog`): grups de `/garment-groups/` (`:33-38`), famílies de
  `garmentTypes.list({ actiu:'true', page_size:500, ...(target?{target}:{}) })` (`:42-49`).

## B2 · Backend dels ítems
- `GarmentTypeItemViewSet` (`backend/fhort/tasks/views_b.py:864`): **`filterset_fields = ['garment_type', 'active']`**
  (`:892` — re-verificat) + SearchFilter (`code`,`name`, `:893`). Escriptura gated CONFIGURE (`:895-899`). Ruta
  `/api/v1/garment-type-items/?garment_type=<id>&active=true` (`tasks/urls.py:37`).
- Nivell 1: `GarmentTypeViewSet` (`pom/views.py:99`), `filterset_fields=['actiu','grup']` (`:113`) + **`?target`** via
  `get_queryset` (`:117-128`, retalla famílies a compatibles amb el target via `SizingProfile`).

## B3 · Estat actual del segon nivell + rastre del "retall"
- **El nivell 2 (Item) SEMPRE es filtra pel nivell 1** a les tres superfícies (`GarmentTypeSelector.jsx:49`,
  `AxesSelector.jsx:41`, `ScopeSelector.jsx:52`), honrat pel backend (`views_b.py:892`). **No hi ha mode "tots els ítems".**
- **El "es va limitar/retallar" documentat = restricció per `target` sobre el NIVELL 1** (famílies/grups), no eliminació de
  nivells. Rastre git (via `git log -S`):
  - `dbd5cfd` feat(grading): GarmentTypeViewSet accepta ?target — cascada del wizard filtra famílies per target.
  - `6bbbc67` feat(grading): GarmentTypeSelector accepta target + ModelWizard l'hi passa.
  - `44f015d` AxesSelector consumeix useGarmentCatalog (cascada filtrada per target).
  - `b6cb968` fix(model-wizard): en canviar target, neteja família/item incompatibles.
  - `12d69b5` docs(diagnosi): wizard cascada no filtra per target + grup NEWBORN absent (origen del retall).
- Diagnosi vigent `DIAGNOSI_WIZARD_CASCADA_TARGET.md`: "⚙️ ONADA 1 IMPLEMENTADA (2026-07-19, dev sense push)". Símptoma:
  amb target «Nadó nena» es mostrava el **catàleg sencer** i mancava NEWBORN → retallat per target. **Onada 2 (6 superfícies
  + pàgina GarmentTypes) PENDENT.**
- **El retall per target NO és uniforme:** només actiu on es passa `target`. `useGarmentCatalog` carrega catàleg complet quan
  `target` és null (`garmentCatalog.js:42-46`). Rastre al codi (comentaris "retallats"): `GarmentTypeSelector.jsx:13,28`,
  `AxesSelector.jsx:32`, `garmentCatalog.js:7`, `ModelWizard.jsx:94-106` (neteja família/item en canvi de target, només acció
  d'usuari). **Cap TODO/FIXME** demanant desfer el retall (grep buit).

**Veredicte B1-B3:** el selector de dos nivells és sòlid — el nivell 2 sempre es restringeix pel nivell 1
(`garment_type=<id>`) i no s'ha tocat. El "retall" és una capa addicional de restricció per `target` sobre el nivell 1,
aplicada només a Wizard de Model i Grading Rules (Onada 1); la resta de superfícies i la pàgina GarmentTypes mostren encara
el catàleg complet (Onada 2 pendent, documentada).

---

## TAULA FINAL — EXISTEIX / FALTA / DIFERENT (per al CTO)

| # | Element | Estat | Àncora |
|---|---|---|---|
| A | Classe `Order`/`OrderLine` | **NO EXISTEIX** (són SalesOrder/SalesOrderLine) | `commerce/models.py:288,335` |
| A | FK directa `SalesOrderLine.model` | **NO EXISTEIX** (via WorkOrder) | `commerce/models.py:480-485` |
| A | Dada de garment a la línia | **NO EXISTEIX** (línia = comercial pura) | `commerce/models.py:335-356` |
| A | Coherència garment_type a assign-model | **NO EXISTEIX** (només warning si GTI null) | `services.py:247-248` |
| A | Camí invers (desassignar model) | **NO EXISTEIX** | `commerce/views.py:200-255` |
| A | `Model.has_order` persistit | **NO EXISTEIX** (anotació `Exists`) | `models_app/views.py:87` |
| A | Prefiltre garment_type al modal | **NO EXISTEIX** (només `customer`) | `OrderDetail.jsx:104` |
| A | Encadenament línia-a-línia al modal | **NO EXISTEIX** (tanca i recarrega) | `OrderDetail.jsx:134-147` |
| A | Guards assign-model (status/customer/qty/dup) | EXISTEIX (atòmic) | `services.py:237-250` |
| A | Recompute de pla a assign-model | **NO EXISTEIX** (només off_recipe) | `services.py:268-273` |
| A | Snapshot preu/recepta a l'assignació | EXISTEIX (única font per facturar) | `services.py:256-258` |
| B | Filtre nivell 2 pel nivell 1 (Item←Type) | EXISTEIX (uniforme) | `views_b.py:892` |
| B | Retall per `target` del nivell 1 | **DIFERENT** (només Wizard + Grading Rules) | `garmentCatalog.js:42-46` |
| B | Retall per target a les 6 superfícies + GarmentTypes | **FALTA** (Onada 2 pendent) | `DIAGNOSI_WIZARD_CASCADA_TARGET.md` |

---

## 💡 PROPOSTES (a validar — NO són fets; decisió humana, Patró C)

> Separades expressament dels fets de dalt. Cap s'ha implementat.

- **💡 Camí invers d'assignació:** el buit més clar és no poder desassignar un model d'una línia (`commerce/views.py`).
  Un `unassign` simètric hauria de restar `qty_allocated`, decidir què fer amb el `WorkOrder` ORDER creat (tancar/anul·lar) i
  amb les `ModelTask` migrades (revertir-les al COLLECTOR d'origen), i respectar el guard "no si ja albaranat" (WO albaranat és
  PROTECT a DeliveryNoteLine, `:703-705`). Cal decidir si es permet només mentre el WO és OPEN i sense línies d'albarà.
- **💡 Prefiltre de garment al modal:** si es vol coherència de tipus de peça, la línia hauria de portar garment_type/GTI (avui
  NO en té) o derivar-lo del `product`; llavors el modal (`OrderDetail.jsx:104`) podria prefiltrar per aquest eix en lloc de
  només `customer`. Avui l'única compatibilitat és un warning post-selecció (`:299-305`).
- **💡 Encadenament línia-a-línia:** el modal podria, en confirmar, avançar automàticament a la següent línia amb
  `qty_allocated < quantity` i mostrar un comptador de línies pendents (avui el progrés només es llegeix per línia). Millora
  d'UX de càrrega de comandes grans; no toca backend.
- **💡 Completar Onada 2 del retall per target:** estendre `?target` a les 6 superfícies restants + pàgina GarmentTypes perquè
  la cascada es retalli uniformement (avui només Wizard + Grading Rules), segons el pla ja documentat a
  `DIAGNOSI_WIZARD_CASCADA_TARGET.md`. Decisió d'abast i prioritat: humana.
