# DIAGNOSI — Desassignació/orfandat de WorkOrder + Product i multiplicador de preu

> Data: 2026-07-20 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`, schema `fhort`.
> Abast: (A) mecànica de desassignar un model d'una comanda (orfandat `WorkOrder.order_line=None`): què ho
> permet/bloqueja, què passa amb les ModelTask migrades i amb `qty_allocated`, orfes reals a staging, pèrdua
> de referència; (B) anatomia de `Product` i si existeix vincle temps→preu→garment (multiplicador).
> Convenció: cada afirmació porta `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi** (no especulat).
> Complement de: `DIAGNOSI_COMMERCE_ASSIGNACIO_I_CASCADE_GT.md` (avui) — assign-model és unitari, sense camí invers.

> ⚠️ **Correcció de premissa del brief:** el brief assumeix que `WorkOrderAdjustment.work_order`,
> `.model_task` i `Expense.work_order` són **PROTECT**. **NO ho són.** Reals: `WorkOrderAdjustment.work_order`
> = **CASCADE** (`:551`), `.model_task` = **SET_NULL** (`:553`), `Expense.work_order` = **CASCADE** (`:588`).
> Els únics PROTECT cap a WorkOrder són `WorkOrder.order_line` (`:483`) i `DeliveryNoteLine.work_order` (`:703`).

---

## Resum executiu (les conclusions que desbloquegen la decisió)

1. **Orfandat `order_line=None` és NET** a BD i Django per a un WO `kind=ORDER`: nullable (`:484`), cap constraint
   ho bloqueja (el CheckConstraint `collector_no_model_no_orderline` només afecta COLLECTOR, `:517-520`), i el
   PROTECT de `DeliveryNoteLine.work_order` bloqueja **esborrar** el WO, no **mutar** `order_line`.
2. **CAP punt del codi petaria** amb `order_line=None`: totes les dereferències de `wo.order_line` estan
   guardades per `if wo.order_line_id` o `default=None` (`services.py:357,581,602`; `serializers.py:269`).
3. **Conseqüència SEMÀNTICA (no crash):** un ORDER orfe albararia a **IVA 0%** (`order_product` → None → línies
   sense product → `compute_document_totals` a 0%). El **preu contractat sobreviu** (ve del `price_snapshot` congelat).
4. **`qty_allocated -= 1` és l'únic efecte necessari** sobre la línia; `allocatedPct` es deriva EN VIU
   (`Orders.jsx:27-33`), i **NO EXISTEIX auto-complete** de `SalesOrder.status` per cap llindar.
5. **Estat real a staging: 3 WorkOrder, tots `COLLECTOR`, 0 orfes ORDER.** La desassignació no existeix al codi;
   no hi ha cap escenari d'orfe materialitzat.
6. **Pèrdua de referència:** `order_line` (FK PROTECT) és l'ÚNIC rastre cap a la comanda origen; el `price_snapshot`
   només guarda `unit_price`+`product_code` (cap `order_id`/`line_id`). **NO EXISTEIX flag d'orfe** ni camp d'origen.
7. **Bloc B: NO EXISTEIX multiplicador de preu** per garment/temps. El pont temps→preu (`price_mode=TIME_BASED`)
   està **documentat als docstrings però NO cablejat**: cap codi de `commerce/` llegeix el temps (`TaskTimeEstimate`).

---

# BLOC A — Mecànica d'orfandat

## A1 · Què permet/bloqueja order_line=None (P1)

### on_delete de la cadena WorkOrder (reverificat)
| FK | on_delete REAL | null/blank | fitxer:línia |
|---|---|---|---|
| `WorkOrder.order_line` → SalesOrderLine | **PROTECT** | null=True, blank=True | `commerce/models.py:483-485` |
| `WorkOrderAdjustment.work_order` | **CASCADE** | — | `commerce/models.py:551` |
| `WorkOrderAdjustment.model_task` | **SET_NULL** | null=True | `commerce/models.py:553` |
| `Expense.work_order` | **CASCADE** | — | `commerce/models.py:588` |
| `DeliveryNoteLine.work_order` | **PROTECT** (únic PROTECT cap a WO) | null=True | `commerce/models.py:703-705` |
| `ModelTask.work_order` | **SET_NULL** | null=True | `tasks/models.py:92-93` |

Aquests on_delete diuen què passa si s'ESBORRA el WO — **cap afecta la mutació d'`order_line`**.

### Nullable + constraints
- `WorkOrder.order_line` = `null=True, blank=True` (`:484`) → `order_line=None` és un UPDATE net.
- CheckConstraints (`:511-521`): `uniq_collector_customer_period` (no depèn d'order_line); `collector_no_model_no_orderline`
  = `~Q(kind='COLLECTOR') | (model__isnull & order_line__isnull)` (`:517-520`). Per un WO **ORDER**, `~Q(kind='COLLECTOR')`
  ja és certa → la check passa amb order_line None o no. **Cap constraint bloqueja order_line=None en un ORDER.**
- PROTECT de `DeliveryNoteLine.work_order` (`:703`) bloqueja el **DELETE** del WO, no `wo.order_line=None; wo.save()`
  (cap FK apunta a `order_line` des de DeliveryNoteLine). → Orfandat **net amb albarà o sense**.

### Flag d'orfe
- **NO EXISTEIX.** Camps de WorkOrder (`:448-505`): number, customer, model, order_line, kind, origin, period, status,
  delivery_note, price_snapshot, recipe_snapshot, closed_*, created_*, updated_at. STATUS = OPEN/CLOSED (`:471-474`),
  KIND = ORDER/COLLECTOR (`:463`), ORIGIN = MANUAL/EXTERNAL_BUS (`:467`). **Cap `orphaned_at`/flag.** Un ORDER orfe seria
  **indistingible** d'un ORDER natiu sense comanda (cas que el help de `:485` contempla com a vàlid).

**Veredicte A1:** orfandat net per a un ORDER; cap constraint ni PROTECT ho impedeix; no hi ha manera de marcar-lo com a orfe.

## A2 · ModelTask migrades en desassignar (P2)

- Migració a l'assignar (`services.py:268-273`): itera `ModelTask.objects.filter(model=model, work_order__kind='COLLECTOR')`
  i fa `task.work_order = wo(ORDER)` + `task.off_recipe = _is_off_recipe(...)` + save. Reassignació directa de la FK.
- Si l'ORDER s'orfandés (order_line=None), **les ModelTask es quedarien apuntant al WO orfe**; **NO EXISTEIX cap reversió**
  cap al COLLECTOR. L'únic punt que buida `task.work_order` és `close_work_order` per Pending cancel·lades
  (`services.py:211-212`) i el SET_NULL si s'esborra el WO (`tasks/models.py:92`).
- **Punts que dereferencien `wo.order_line` — TOTS guardats:**

| Ús | Guard | fitxer:línia |
|---|---|---|
| `wo.order_line.product if wo.order_line_id else None` | `if wo.order_line_id` | `services.py:357` |
| `wo.order_line.product if wo.order_line_id else None` | `if wo.order_line_id` | `services.py:581` |
| `wo.order_line.product if (kind=='ORDER' and wo.order_line_id)` | idem | `services.py:602` |
| `source='order_line.order.document_number', default=None` | DRF captura AttributeError | `serializers.py:269` |
| `select_related('order_line...')` | join, no peta amb null | `views.py:222,356`; `services.py:575,597` |

**Veredicte A2:** cap crash amb order_line=None. **Conseqüència semàntica:** `order_product=None` → línies d'albarà
TASK/EXTRA/DEDUCTION sense product → `compute_document_totals` a **0% IVA**. El preu ve del `price_snapshot` (sobreviu).
Les ModelTask migrades queden penjades del WO orfe sense reversió.

## A3 · Impacte a qty_allocated i comanda (P3)

- Imputació: `order_line.qty_allocated = (Decimal(qty_allocated or 0) + 1).quantize(_CENT)` + `save(update_fields=['qty_allocated'])`
  (`services.py:261-262`). **`qty_allocated` és l'ÚNIC camp que es toca de la línia** en assignar; `line_total` ve de
  `quantity*unit_price` (`models.py:351`), no de qty_allocated; la línia no té cap altre camp d'al·locació (`models.py:335-356`).
  → **Restar 1 a `qty_allocated` seria l'únic efecte necessari** per alliberar una unitat.
- `allocatedPct(order)` (`Orders.jsx:27-33`) es **deriva EN VIU** (`Σqty_allocated / Σquantity`); l'endpoint `allocation`
  (`views.py:213-235`) recalcula `pct` cada crida (`:220-221`). **Cap camp persistit** → restar qty_allocated es reflecteix
  automàticament a tot arreu (`Orders.jsx:71`, `OrderDetail.jsx:213,343`).
- **Auto-complete de `SalesOrder.status`: NO EXISTEIX.** Cap assignació de `status='COMPLETED'` fora del choice (`models.py:301`);
  les úniques transicions de status a `services.py` toquen quote/work_order/delivery_note, mai SalesOrder; `signals.py` buit.
  L'únic camí per canviar `SalesOrder.status` és el serializer (`serializers.py:236`, "únic camp editable"). Cap llindar tanca la comanda.

**Veredicte A3:** `qty_allocated -= 1` és suficient i segur; el % i l'estat de la comanda es comporten sols; res auto-completa.

## A4 · Orfes reals + pèrdua de referència (P4)

### Query real (schema fhort, READ-ONLY executat)
| Mètrica | Valor |
|---|---|
| Total WorkOrder | **3** |
| WO amb `order_line IS NULL` (general) | **3** |
| WO orfes `order_line NULL, status=OPEN, model NOT NULL` | **0** |
| WO `kind='ORDER'` amb order_line null | **0** |
| Per `kind` | **`{'COLLECTOR': 3}`** |

→ Els 3 WO són tots **COLLECTOR** (order_line null és el seu estat legítim i forçat pel CheckConstraint). **Zero orfes
ORDER**; la desassignació no existeix al codi i no hi ha cap escenari materialitzat.

### Pèrdua de referència
- `price_snapshot` (`services.py:256-257`) = `{'unit_price':..., 'product_code':...}`. **NO conté** `order_id`, `line_id`
  ni número de comanda. `recipe_snapshot` = `{'task_codes':[...]}`.
- La FK `order_line` (PROTECT, `:483`) és l'**ÚNIC** rastre estructural cap a la línia/comanda origen. Amb order_line=None
  es perd tota la traça; **NO es podria reconstruir** la comanda (product_code no és clau: pot coincidir amb N línies/comandes).
- Efecte funcional de nul·lificar: el WO **surt** de la relació inversa `line.work_orders` (`views.py:222`) → desapareix del
  desplegable `allocation` de la fitxa de comanda.

### Opcions per no perdre la traça (FET, sense triar)
| Opció | Cal migrar | Consumidors de order_line afectats | Cost |
|---|---|---|---|
| **(a) Camp nou `WorkOrder.orphaned_from_line`** (FK SalesOrderLine, null) | columna FK nova | cap (segueixen veient order_line null + guard) | Baix a la lògica; duplica semànticament la línia origen (2 FK a la mateixa taula → risc divergència); decidir on_delete (PROTECT torna a bloquejar esborrat de línia) |
| **(b) NO nul·lificar; booleà/estat `detached`** | columna `detached` o ampliar STATUS | **tots**: `line.work_orders` (`views.py:222`), albarà/agregacions (`services.py:357,581,602`), guard doble-ORDER (`:243-244`), imputació — han d'afegir filtre `detached=False` | Alt: toca cada lector que assumeix "WO amb order_line ⇒ viu"; preserva FK i PROTECT intactes |
| **(c) `line_id`/`order_id` al `price_snapshot`** (JSON) | cap (JSONField) | cap; però cap lector el llegeix avui → cal escriure el reconstructor; els 3 COLLECTOR existents no el tindrien retroactiu | Molt baix d'esquema; id "tou" sense integritat referencial (pot quedar penjat) |

**Veredicte A4:** avui 0 orfes reals. La FK `order_line` és l'única traça; nul·lificar-la la perd. Tres opcions amb cost creixent
de disruptivitat als lectors (c < a < b en esquema; b toca més lògica viva). Decisió humana.

---

# BLOC B — Product i multiplicador de preu

## B1 · Anatomia de Product (P5)

- `class Product(TranslatableMixin, models.Model)` (`commerce/models.py:47`). Camps: `code` (slug unique `:79`), `name`/`description`
  (traduïbles `:80-81`), `nature` (INTERNAL_SERVICE/EXTERNAL_SERVICE/GOODS/PACK `:82`), `price_mode` (FIXED/TIME_BASED, default
  FIXED `:83`), `base_price` (`:84`), `sale_rate` (tarifa venda per minut `:86`), `markup_pct` (`:88`), `tax_rate` (default 21 `:92`),
  `unit` (FK Unit PROTECT `:94`), `active` (`:96`), created/updated. **NO té** camp garment_type ni minuts.
- `recipe_lines` = **`ProductRecipe`** (`:109`): FK `product` CASCADE related_name `recipe_lines` (`:116`), `task_code` (slug, "referència
  a `TaskType.code`, mai PK" `:117`), `qty` (`:118`), unique `(product, task_code)` (`:123`); `clean()` només si `nature=INTERNAL_SERVICE`.
  **La resolució de task_codes és per STRING-code, no FK viva a ModelTask/TaskType.**
- **Product↔garment: NO EXISTEIX FK directa.** El vincle viu en taula satèl·lit `ProductPriceGTI` (`:187`): FK `product` (`:196`)
  + FK `garment_type_item` (`:197`), unique `(product, garment_type_item)` (`:204`) — taula d'**EXCEPCIONS de preu absolut**, no graella densa.

## B2 · Consum de l'estadística de temps (Welford) (P6)

- Taula: **`TaskTimeEstimate`** (`tasks/models.py:349`), clau `unique_together (garment_type_item, task_type)` (`:362`); camps
  `estimated_minutes` (seed `:356`), `n`, `mean_minutes` (Welford `:358`), `m2`. → matriu **(GarmentTypeItem × TaskType) → minuts**.
- `lookup_estimated_minutes(model, task_type)` (`services_g.py:11`): cascada — (1) cel·la pròpia per `garment_type_item_id`
  (`:19-27`), (2) mitjana de cel·les madures per task_type (`:31-35`), (3) `TimeSeed` per code/fase (`:39-43`), (4) None (`:45`).
  Clau de lectura sempre per **task_type**; el garment entra per **garment_type_item** (mai garment_type directe).
- **Consumidors reals:** `tasks/views_b.py:328,525` (snapshot de ModelTask) i `planning/plan_service.py:72,314` (planificació).
  **Cap consumidor a `commerce/`** (grep de `lookup_estimated_minutes|estimated_minutes|mean_minutes` sobre commerce → 0).
- **Ni Product ni ProductRecipe tenen camp de temps/minuts.** El temps viu NOMÉS a la banda tasques, desacoblat de preu.

## B3 · Multiplicador de preu (P7)

- **NO EXISTEIX.** grep `multipli|factor|coefficient|coeficient|weight|pes` sobre `commerce/` → cap mecanisme. El preu és sempre
  `line_total = quantity × unit_price` sense coeficient (QuoteLine `:272`, SalesOrderLine `:351`, DeliveryNoteLine `:741`).
- `ProductPriceGTI.price` (`:199`) és **preu absolut d'excepció** per (product, GTI), no un factor sobre base_price.
- `price_snapshot` (JSONField `:497`) desa `{'unit_price':...}` i es llegeix tal qual (`services.py:358,487,582`), sense factor.
- **Pont temps→preu documentat però NO cablejat:** els docstrings de Product descriuen `TIME_BASED → temps (cascada Welford del
  GTI) × sale_rate + markup_pct` (`:59-62`) i `ProductPriceGTI` diu "si no hi ha fila, mana el preu derivat de price_mode/sale_rate"
  (`:194`). Els camps hi són (`price_mode`, `sale_rate`, `markup_pct`), **PERÒ cap codi de commerce llegeix el temps**; l'única
  congelació implementada (QuoteLine serializer `:171-175`) copia **només `base_price`**, mai el càlcul TIME_BASED×sale_rate.

**Veredicte B:** avui hi ha temps↔garment (`TaskTimeEstimate`, banda tasques) i preu↔garment (`ProductPriceGTI`, excepcions
absolutes), però **NO hi ha pont temps→preu operatiu**: només l'esquelet de camps i la intenció als docstrings. Cap multiplicador.

---

## TAULA FINAL — EXISTEIX / FALTA / DIFERENT (per al CTO)

| # | Element | Estat | Àncora |
|---|---|---|---|
| A | `order_line=None` bloquejat per constraint (ORDER) | **NO** (net; constraint només afecta COLLECTOR) | `commerce/models.py:517-520` |
| A | PROTECT bloqueja mutar order_line | **NO** (bloqueja DELETE del WO, no la mutació) | `commerce/models.py:703` |
| A | Adjustment/Expense.work_order = PROTECT | **NO** (són CASCADE) | `commerce/models.py:551,588` |
| A | Punt que peta amb order_line=None | **NO EXISTEIX** (tot guardat) | `services.py:357,581,602` |
| A | Orfe ORDER albara amb IVA correcte | **NO** (product=None → 0% IVA) | `services.py:357` + compute_totals |
| A | Reversió de ModelTask migrades | **NO EXISTEIX** (queden al WO orfe) | `services.py:268-273` |
| A | Flag/estat d'orfe al WorkOrder | **NO EXISTEIX** | `commerce/models.py:448-505` |
| A | `qty_allocated -= 1` suficient per alliberar | EXISTEIX (únic camp) | `services.py:261-262` |
| A | `allocatedPct` persistit | **NO** (derivat en viu) | `Orders.jsx:27-33` |
| A | Auto-complete de SalesOrder.status | **NO EXISTEIX** | `commerce/services.py` (grep) |
| A | Orfes ORDER reals a staging | **0** (3 WO, tots COLLECTOR) | query fhort |
| A | Traça a la comanda origen al price_snapshot | **NO EXISTEIX** (només unit_price+code) | `services.py:256-257` |
| B | FK Product→garment_type | **NO EXISTEIX** (via ProductPriceGTI) | `commerce/models.py:187-204` |
| B | Camp de temps a Product/ProductRecipe | **NO EXISTEIX** (temps a TaskTimeEstimate) | `tasks/models.py:349-362` |
| B | Consumidor de temps a commerce/ | **NO EXISTEIX** | grep commerce |
| B | Multiplicador de preu per garment/temps | **NO EXISTEIX** | grep commerce |
| B | Pont TIME_BASED cablejat | **DIFERENT** (documentat, no implementat) | `commerce/models.py:59-62` |

---

## 💡 PROPOSTES (a validar — NO són fets; decisió humana, Patró C)

> Separades expressament dels fets de dalt. Cap s'ha implementat.

- **💡 Desassignar (camí invers):** un `unassign` simètric hauria de (1) `qty_allocated -= 1` (`services.py:261`), (2)
  decidir el destí del WO ORDER — tancar-lo (status=CLOSED) o orfandar-lo (order_line=None) —, (3) decidir el destí de les
  ModelTask migrades (revertir-les al COLLECTOR d'origen o deixar-les), (4) **corregir l'IVA 0% de l'orfe** (avui product=None
  → albarà a 0%): o bé no permetre orfandar si ja hi ha DeliveryNoteLine, o bé conservar el tipus d'IVA al snapshot. Restringir
  a WO OPEN sense albarà seria el cas net.
- **💡 Traça de l'origen:** si es vol l'informe (data/comanda/línia/total/WO), l'opció **(c)** — afegir `line_id`/`order_id`
  al `price_snapshot` (JSON, sense migració) — és la menys disruptiva d'esquema; l'opció **(a)** (camp FK `orphaned_from_line`)
  dona integritat referencial a canvi d'un 2n camp; l'opció **(b)** (no nul·lificar + `detached`) preserva la FK però obliga a
  filtrar `detached` a tots els lectors. Cost creixent (c<a<b). Cal també un **flag/estat d'orfe** (avui inexistent) per
  distingir orfe d'ORDER natiu sense comanda.
- **💡 Pont temps→preu (TIME_BASED):** l'esquelet ja hi és (`price_mode`, `sale_rate`, `markup_pct`, `:83-88`) i la cascada
  de temps existeix (`lookup_estimated_minutes`, `services_g.py:11`), però desacoblats. Connectar-los seria: en congelar el
  preu d'un producte TIME_BASED, llegir `lookup_estimated_minutes(GTI, task_type)` × `sale_rate` + `markup_pct` en lloc de
  copiar `base_price`. És una capa NOVA (avui el serializer només copia base_price, `serializers.py:171-175`), no un retall.
- **💡 Multiplicador per garment:** si el que es vol és un factor (no un preu absolut), avui NOMÉS existeix `ProductPriceGTI`
  com a **preu absolut** per (product, GTI). Un multiplicador seria un mecanisme nou; cal decidir si substitueix o complementa
  `ProductPriceGTI`. NO EXISTEIX res reutilitzable com a factor avui.
