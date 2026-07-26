# DIAGNOSI — Quote, conversió a comanda i vincle preparatori model↔QuoteLine

Data: 2026-07-20 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`, schema `fhort`
Abast: anatomia de `Quote`/`QuoteLine`, la conversió pressupost→comanda actual, on viuria un vincle
*preparatori* (informatiu) model↔línia d'oferta, i el camí invers d'`unassign` (re-adopció d'un WO orfe).
Convenció: cada afirmació porta `fitxer:línia`. `"NO EXISTEIX"` = confirmat absent al codi (grep), no especulat.
Context previ (vigent): `DIAGNOSI_COMMERCE_ASSIGNACIO_I_CASCADE_GT.md` + `DIAGNOSI_UNASSIGN_ORFANDAT_I_PRODUCT.md`.

---

## Resum executiu

1. **`QuoteLine` és avui una línia purament comptable-fiscal.** Hereta `AbstractDocumentLine`
   (`product`, `description`, `quantity`, `unit_price`, `line_total`, `position`) i afegeix només la FK
   `quote` (`models.py:257`). **NO té `qty_allocated`, NO té cap FK/M2M a `Model` ni a `WorkOrder`, i cap
   taula del sistema l'apunta** (grep de FK a `QuoteLine` = buit). Tot el vincle amb l'execució viu una
   capa més avall, a `SalesOrderLine` (`models.py:483` i `489`).
2. **La conversió pressupost→comanda EXISTEIX i és automàtica**: `convert_quote_to_order`
   (`services.py:132`), exposada a `POST commerce/quotes/{id}/convert/` (`views.py:150`) i al botó de
   `QuoteDetail.jsx:91,122`. Congela les línies camp a camp (`services.py:163-166`), és **irreversible** i
   protegida per triple guard (SENT · ≥1 línia · `source_quote` unique).
3. **El vincle preparatori model↔oferta és terreny verge**: no hi ha cap estructura d'intenció/reserva
   reutilitzable. Cal camp o taula nova. Dues opcions netes exposades a §P3 (💡), totes dues informatives i
   sense cap efecte col·lateral (ni WO, ni `qty_allocated`, ni snapshots).
4. **La re-adopció d'un WO orfe NO EXISTEIX** (grep de `reattach`/`reassign`/`adopt` = només comentaris i
   l'informe read-only `orphaned`). El camí invers exacte d'`unassign_model_from_order_line`
   (`services.py:292`) és construïble amb simetria estricta; l'únic punt de decisió obert és el dels
   **snapshots** (conservar el congelat vs re-congelar contra el `product` de la línia nova) — §P4.
5. **Punt d'entrada UI ja madur**: `OrderDetail.jsx` té el patró exacte reutilitzable — botó `RowBtn`
   `ti-link` per línia que obre el picker d'assignació (`OrderDetail.jsx:191`), i la pàgina
   `OrphanedWorkOrders.jsx` ja llista els orfes "pendents de reassignar" però **sense cap acció de
   reassignació** (`OrphanedWorkOrders.jsx:53` només navega a la comanda).

---

## BLOC P1 — Anatomia de `Quote` i `QuoteLine`

### `Quote` (`commerce/models.py:216-252`)
Subclasse de `AbstractDocument` (`models_base.py:15-65`); no afegeix cap camp propi (`models.py:224` només
`Meta` + `save`/`recalculate_totals`). Camps heretats de l'abstracta:

| Camp | fitxer:línia | Nota |
|---|---|---|
| `document_number` (unique, blank) | `models_base.py:38` | Generat a `save()` via `reserve_document_number('quote')` (`models.py:234-235`); mai editable. |
| `doc_type` | `models_base.py:41` | Forçat a `'quote'` a `save()` (`models.py:231-232`). |
| `customer` → `tasks.Customer` (PROTECT) | `models_base.py:42` | related_name `quotes`. |
| `status` | `models_base.py:44` | Choices de l'abstracta (§estats, sota). Default `DRAFT`. |
| `issued_at`, `valid_until` (date, null) | `models_base.py:45-46` | |
| `payment_terms` → `PaymentTerms` (SET_NULL) | `models_base.py:49` | Override per document; si null → el del customer. |
| `subtotal`, `tax_amount`, `total` (Decimal) | `models_base.py:51-54` | Calculats per `recalculate_totals` (`models.py:238-249`). |
| `tax_breakdown` (JSON) | `models_base.py:57` | Desglossament fiscal `[{rate,base,tax}]`. |
| `notes` (text) | `models_base.py:58` | |
| `created_at`/`updated_at`/`created_by` | `models_base.py:59-62` | |

### `QuoteLine` (`commerce/models.py:255-281`)
Subclasse d'`AbstractDocumentLine` (`models_base.py:68-88`). **Camps totals:**

| Camp | Origen | fitxer:línia |
|---|---|---|
| `quote` → `Quote` (CASCADE, related_name `lines`) | propi | `models.py:257` |
| `product` → `commerce.Product` (PROTECT) | heretat | `models_base.py:76` |
| `description` (char 300, blank) | heretat | `models_base.py:78` |
| `quantity` (Decimal 12,2, default 1) | heretat | `models_base.py:80` |
| `unit_price` (Decimal 12,2) — **còpia congelada** del preu del Product | heretat | `models_base.py:81-82` |
| `line_total` (Decimal 12,2, guardat) | heretat | `models_base.py:83` |
| `position` (int, ordre manual) | heretat | `models_base.py:85` |

**FETS decisius per al brief:**
- **`QuoteLine` NO té `qty_allocated`.** Aquest camp existeix **només** a `SalesOrderLine`
  (`models.py:340-341`); és control de cartera de la comanda, no de l'oferta.
- **`QuoteLine` NO té cap vincle amb `Model` ni `WorkOrder`** — ni FK, ni M2M, ni JSON. Grep de FK/M2M/OneToOne
  a `QuoteLine` sobre tot `fhort/` = **buit** (NO EXISTEIX). L'única cosa que apunta cap a `Model`/`WorkOrder`
  a la família de línies és `SalesOrderLine`, referenciada per `WorkOrder.order_line` (`models.py:483`) i
  `WorkOrder.orphaned_from_line` (`models.py:489`).
- **`line_total` es recalcula a cada `save()`** (`models.py:272-273`), amb guard de segellat: només editable
  mentre `quote.status == 'DRAFT'` (`_assert_editable`, `models.py:264-267`, cridat a `save` i `delete`).

### Estats / cicle de vida de `Quote`
Choices heretades: `DRAFT · SENT · ACCEPTED · REJECTED · EXPIRED` (`models_base.py:31-37`). **Transicions
realment implementades al codi:**
- `DRAFT → SENT`: `POST quotes/{id}/send/` (`views.py:122-138`); guard `status==DRAFT` (409 si no) +
  ≥1 línia; materialitza venciments (`views.py:136-137`).
- `SENT → ACCEPTED`: **només** com a efecte lateral de la conversió (`services.py:168`).
- `REJECTED` i `EXPIRED`: existeixen com a choice però **cap transició els assigna** al codi (grep
  `status = 'REJECTED'|'EXPIRED'` = buit → NO EXISTEIX cap flux que hi porti avui).

**Veredicte P1: llest.** `QuoteLine` és una línia fiscal pura; sense `qty_allocated` ni cap vincle a
`Model`/`WorkOrder`. Qualsevol vincle preparatori és estructura nova (§P3).

---

## BLOC P2 — Conversió pressupost→comanda (actual)

### Existeix i on
- Servei: `convert_quote_to_order(quote, user)` (`services.py:132-171`).
- Endpoint: `@action POST commerce/quotes/{pk}/convert/` (`views.py:150-161`), gated `CONFIGURE`
  (`_ConfigureWriteMixin`); retorna la `SalesOrder` serialitzada (201) o 400 amb el missatge del guard.
- Frontend: `commerce.quotes.convert(id)` (`endpoints.js:433`) cridat a `QuoteDetail.jsx:91`; botó visible
  quan `canConvert = canEdit && quote.status === 'SENT'` (`QuoteDetail.jsx:103,122-124`), amb modal de
  confirmació (`QuoteDetail.jsx:142-145`).

### Còpia de línies (camp a camp) i què congela
Dins `transaction.atomic()` (`services.py:155`):
1. Crea la `SalesOrder` (`services.py:156-162`): `customer=quote.customer`,
   `payment_terms=effective_payment_terms(quote)` **congelat com a override**, `issued_at=avui`,
   `source_quote=quote`, `created_by`. Número SO nou via `save()` (`models.py:317-319`).
2. Clona cada `QuoteLine → SalesOrderLine` amb **pk nou** i valors congelats (`services.py:163-166`):
   `product`, `description`, `quantity`, `unit_price`. `line_total` es recalcula al `save` de la línia
   (`models.py:351-352`); `qty_allocated` neix a 0 (default, `models.py:340`).
3. `order.recalculate_totals()` (`services.py:167`) → `compute_document_totals` + `generate_due_dates`.
4. **Segella l'oferta**: `quote.status = 'ACCEPTED'` (`services.py:168-169`); a partir d'aquí el guard
   `DRAFT-only` de `QuoteLine` (`models.py:264-267`) bloqueja tota edició posterior de línies.

**El que es congela** (còpia de valors, cap FK viva a preus): `unit_price`, `quantity`, `description`,
`product` de cada línia, i `payment_terms` efectius al header. Coherent amb la llei d'`AbstractDocumentLine`
(`models_base.py:70-74`): "`unit_price` és una CÒPIA CONGELADA... si el preu del Product canvia demà, els
documents ja emesos no han de canviar".

### Guards de conversió (tots abans de tocar res, `services.py:148-154`)
- `quote.status != 'SENT'` → ValidationError (`services.py:148-149`). **Només SENT**, no DRAFT ni ACCEPTED.
- `not lines` → ValidationError (`services.py:150-152`).
- `SalesOrder.objects.filter(source_quote=quote).exists()` → ValidationError (`services.py:153-154`),
  reforçat pel **unique de BD** de `source_quote` (OneToOne, `models.py:304-306`): **1 oferta → com a molt
  1 comanda**. Doble conversió impossible tant a nivell de servei com de BD.

### Irreversibilitat
No hi ha reversió per disseny (`models.py:288-297`, `services.py:143-144`): l'única sortida d'una comanda és
`status=CANCELLED`, que **NO reobre** l'oferta. Les línies de `SalesOrderLine` no són editables en preu/quantitat
per API (irreversibilitat imposada al serializer, `models.py:335-338`, `views.py:200-206`).

**Veredicte P2: llest.** La conversió és automàtica, atòmica, congela camp a camp i és irreversible amb
guard de doble conversió a BD. No cal cap enllaç manual de `source_quote` (el fa el servei).

---

## BLOC P3 — On viuria el vincle preparatori model↔`QuoteLine`

### FET pur
`QuoteLine` **no pot apuntar models avui** (P1: cap FK/M2M/JSON a `Model`; grep buit). No hi ha cap
estructura d'intenció/reserva reutilitzable al mòdul: grep de `intent`/`reservation`/`reserve` sobre models
comercials = **NO EXISTEIX** (l'únic `reserve_*` és `reserve_document_number`, numeració, `services.py:70`).
El vincle línia↔model **només** apareix a la capa d'execució: `WorkOrder.model` + `WorkOrder.order_line`
(`models.py:480-485`), creat per `assign_model_to_order_line` (`services.py:233`) **sobre la comanda, no
sobre l'oferta**.

> 💡 PROPOSTA (a validar) — **opcions per al vincle preparatori (informatiu, sense efectes col·laterals)**
>
> Premissa comuna: aquest vincle és **intenció comercial en fase d'oferta** (quins models es pensen produir
> per a cada línia), independent de l'execució. **No** ha de crear `WorkOrder`, **no** ha de tocar
> `qty_allocated` (que no existeix a `QuoteLine`, P1), **no** congela snapshots. En convertir a comanda,
> hauria de poder-se **propagar** com a suggeriment d'assignació (fora d'abast d'aquesta diagnosi).
>
> **(a) FK directa `QuoteLine.model` (o M2M `QuoteLine.models`).**
> - Cost: 1 camp + 1 migració. Simplicitat màxima.
> - Límit: una FK simple només modela 1 model per línia. Si la línia té `quantity > 1` i es volen
>   diversos models (un per unitat), cal M2M — però l'M2M perd la **quantitat per model** i l'ordre.
> - Efecte col·lateral: cap si es deixa `on_delete=SET_NULL`.
>
> **(b) Taula through pròpia `QuoteLineModelIntent` (FK `quote_line`, FK `model`, `qty`, `position`).**
> - Cost: 1 model nou + 1 migració + serializer/endpoint satèl·lit (patró `QuoteLineViewSet`, `views.py:164`).
> - Guanya: **quantitat i ordre per model**, i espai per a metadades futures (nota, estat de la intenció)
>   sense tocar `QuoteLine`. És el mirall preparatori de com `WorkOrder` lliga model↔línia a l'execució.
> - És l'opció alineada amb el patró satèl·lit del mòdul (recipe-lines, order-lines, quote-lines).
>
> Cap de les dues té efecte sobre WO ni `qty_allocated`; totes dues viuen íntegrament dins `commerce`.
> **La tria és humana (Patró C).**

**Veredicte P3: cal estructura nova.** No hi ha res reutilitzable; el vincle és verge. Opcions (a)/(b)
exposades amb cost, sense triar.

---

## BLOC P4 — Re-adopció d'un WO orfe (camí invers d'`unassign`)

### FET: NO EXISTEIX cap reattach avui
Grep de `reattach`/`re_attach`/`reassign`/`re_assign`/`adopt` sobre `commerce/`:
- `views.py:284-285`, `services.py:323`, `models.py:486`: apareixen només com a **text** ("pendents de
  reassignar", "fins que es reassigni") — **cap funció ni endpoint**.
- L'únic tractament actual dels orfes és l'**informe read-only** `GET work-orders/orphaned/`
  (`views.py:282-306`), que llista els WO amb `orphaned_from_line` no null; no reassigna res.
- Conclusió: **la re-adopció NO EXISTEIX** (ni servei, ni endpoint, ni UI d'acció).

### El punt de partida a invertir: `unassign_model_from_order_line` (`services.py:292-326`)
Guards (abans de la transacció): `kind=='ORDER'` (`:302`), `status=='OPEN'` (`:304`), `order_line` no null
(`:306`), no albaranat (`:308`). Efecte atòmic: allibera 1 unitat de `qty_allocated` amb clamp a 0 (`:314-316`),
mou la traça a `orphaned_from_line` i buida `order_line` (`:318-320`, `:324`). Les `ModelTask` migrades **no
es toquen** (`:321-323`).

### FET: què caldria per al camí invers (simetria estricta)
Un `reattach_orphan_to_line(work_order, new_line, user)` seria el mirall exacte. Guards proposats (mirall
d'assign+unassign):

| Guard invers | Mirall de | fitxer:línia origen |
|---|---|---|
| `work_order.kind == 'ORDER'` | unassign `:302` | només WO d'encàrrec |
| `work_order.status == 'OPEN'` | unassign `:304` / assign `:247` | un CLOSED no es re-adopta |
| `work_order.order_line_id is None` (és orfe: `orphaned_from_line` no null) | invers d'unassign `:306` | ha d'estar desassignat |
| `new_line.order.status == 'OPEN'` | assign `:247-248` | la comanda destí ha d'estar oberta |
| `work_order.customer_id == new_line.order.customer_id` | assign `:249-250` (`model.customer==order.customer`) | **coherència de client** |
| `qty_allocated < quantity` a `new_line` | assign `:251-252` | quantitat disponible a la línia nova |
| `not DeliveryNoteLine.objects.filter(work_order=wo).exists()` | unassign `:308` | un WO albaranat no es remou |

Efecte atòmic simètric: `new_line.qty_allocated += 1` (mirall d'assign `:274-276`), `work_order.order_line =
new_line`, i **`orphaned_from_line = None`** (neteja de la traça — **DECISIÓ JA PRESA per l'Agus**: l'orfandat
és transitòria, no història).

### El PUNT DE DECISIÓ OBERT: els snapshots
En l'assignació original es congelen `price_snapshot` (`unit_price`, `product_code`, `tax_rate`) i
`recipe_snapshot` (`task_codes`) del `product` de la línia (`services.py:266-272`). L'albarà els llegeix:
`snap_price = wo.price_snapshot.get('unit_price')` (`services.py:409`) i, crucialment,
`order_product = wo.order_line.product if wo.order_line_id else None` (`services.py:408`) — per a un WO
**re-adoptat** `order_line` ja no és null, de manera que la línia d'albarà agafaria el **`product` de la línia
NOVA** però el **preu del snapshot VELL**.

> 💡 PROPOSTA (a validar) — **conservar vs re-congelar el snapshot en re-adoptar**
>
> **Opció 1 — CONSERVAR el snapshot original.**
> - Conseqüència de facturació: l'albarà cobra el **preu contractat originalment** (el de la línia d'on el WO
>   va néixer), independentment del preu de la línia nova. Fidel a "el preu es congela quan es contracta la
>   feina". Però obre una **incoherència**: `product` de la línia d'albarà = producte de la línia NOVA
>   (`services.py:408`), preu = producte VELL → dos articles barrejats en una mateixa línia si els productes
>   difereixen. El `tax_rate` del snapshot vell (`services.py:53`, càlcul fiscal) pot no coincidir amb el
>   `tax_rate` del producte nou.
>
> **Opció 2 — RE-CONGELAR contra el `product` de la línia nova** (recomanada per coherència).
> - En re-adoptar, refer `price_snapshot`/`recipe_snapshot` exactament com `assign_model_to_order_line`
>   (`services.py:262-272`): `unit_price = new_line.unit_price`, `product_code`/`tax_rate` del producte nou,
>   `task_codes` de la recepta del producte nou.
> - Conseqüència: l'albarà cobra el preu **de la línia a què s'ha re-adoptat** i el producte, el tipus d'IVA
>   i la recepta queden alineats (cap barreja). Risc: si els extres/deduccions ja registrats (`Adjustment`,
>   `services.py:435-436` usen `snap_price`) es valoraven contra el preu vell, el seu import de referència
>   canvia. Cal decidir si els Adjustments existents es re-valoren o es respecten.
>
> Un tercer híbrid possible (re-congelar `product_code`/`tax_rate`/recepta però conservar `unit_price`) evita
> la barreja d'article però manté el preu contractat; s'anota com a variant, no es recomana per complexitat.
>
> **La tria és humana (Patró C).** L'única part ja decidida (neteja d'`orphaned_from_line`) queda fora d'aquest 💡.

**Veredicte P4: cal construir.** El reattach no existeix; és construïble amb simetria estricta i guards
espill. L'únic node de decisió pendent són els snapshots (2 opcions + 1 variant, amb conseqüència de
facturació explícita).

---

## BLOC P5 — Punt d'entrada UI del pressupost

### Pantalla de `Quote` actual
`frontend/src/pages/QuoteDetail.jsx` (297 línies) — equivalent de l'`OrderDetail`. Composició:
`DocumentHeader` + accions de header (`send` `QuoteDetail.jsx:116`, `pdf` `:120`, `convert` `:122`) +
`LinesSection` (`:135,177-`) que llista línies amb `LineTable` i, en DRAFT (`editable`), permet
afegir/esborrar línia (`quoteLines.create` `:195`, `remove` `:204`; botó `RowBtn` `ti-trash` `:217`).
**Les accions per línia d'oferta són avui només CRUD de línia; cap acció d'assignació de model.**

### El patró de botó reutilitzable (des d'`OrderDetail`)
`OrderDetail.jsx` ja té exactament el patró que un vincle preparatori replicaria:
- Per línia, un `RowBtn icon="ti-link"` que obre el modal d'assignació:
  `OrderDetail.jsx:191` → `onClick={() => openAssign(l)}`.
- Modal picker de models (cerca codi/nom + temporada/col·lecció) `OrderDetail.jsx:290-`; en confirmar,
  `commerce.orderLines.assignModel(line.id, {model_id})` (`OrderDetail.jsx:156`, `endpoints.js:453`).
- Desplegable read-only per línia amb els models assignats i el botó de desassignar
  (`OrderDetail.jsx:243`, `doUnassign` `:142-148`, `endpoints.js:465`).

**El patró `ti-link` d'`OrderDetail` és replicable tal qual a `QuoteDetail`** per obrir un picker de "models
que es pensen produir" per línia d'oferta (el vincle preparatori de §P3), amb el picker ja fet
(`OrderDetail.jsx:290-357`) com a plantilla.

### Entrada UI per als orfes (rellevant a P4)
`frontend/src/pages/OrphanedWorkOrders.jsx` (73 línies) llista els WO orfes ("pendents de reassignar",
`:9-10`) des de `workOrders.orphaned()` (`endpoints.js:467`). L'única acció per fila és **navegar a la
comanda** (`OrphanedWorkOrders.jsx:53`); **NO hi ha botó de reassignació** (NO EXISTEIX). És el lloc natural
on penjaria l'acció de re-adopció de P4.

**Veredicte P5: llest.** El patró de botó `ti-link` + picker d'`OrderDetail` és directament reutilitzable
tant per al vincle preparatori (§P3, a `QuoteDetail`) com per a l'entrada de re-adopció (§P4, a
`OrphanedWorkOrders`).

---

## TAULA FINAL per al CTO — EXISTEIX / FALTA / DIFERENT

| # | Element | Estat | Font |
|---|---|---|---|
| 1 | `QuoteLine` amb `qty_allocated` | **NO EXISTEIX** (només a `SalesOrderLine`) | `models.py:340`; grep buit |
| 2 | Vincle `QuoteLine`↔`Model`/`WorkOrder` | **NO EXISTEIX** (cap FK/M2M/JSON) | grep FK a QuoteLine = buit |
| 3 | Estructura d'intenció/reserva reutilitzable | **NO EXISTEIX** | grep `intent`/`reserve` = només numeració |
| 4 | Conversió pressupost→comanda | **EXISTEIX**, atòmica + irreversible + guard doble-conversió a BD | `services.py:132`; `views.py:150`; `models.py:304` |
| 5 | Congelació camp a camp a la conversió | **EXISTEIX** (`product`/`qty`/`unit_price`/`description` + `payment_terms`) | `services.py:163-169` |
| 6 | Transicions `REJECTED`/`EXPIRED` de Quote | **NO EXISTEIX** (choice sense flux) | grep buit; `models_base.py:35-36` |
| 7 | Re-adopció / reattach d'un WO orfe | **NO EXISTEIX** (ni servei, ni endpoint, ni UI d'acció) | grep `reattach/reassign/adopt` = comentaris |
| 8 | Informe read-only d'orfes | **EXISTEIX** (sense acció) | `views.py:282`; `OrphanedWorkOrders.jsx` |
| 9 | Simetria `unassign` per invertir | **EXISTEIX** (guards + efecte atòmic clars) | `services.py:292-326` |
| 10 | Snapshot llegit per l'albarà (preu+producte) | **EXISTEIX** — `order_product` de la línia viva, `snap_price` del congelat | `services.py:408-409` |
| 11 | Patró UI `ti-link` + picker de model per línia | **EXISTEIX** a `OrderDetail`, replicable | `OrderDetail.jsx:191,290-357` |
| DEC | Neteja d'`orphaned_from_line` en re-adoptar | **DECIDIT** (Agus): torna a null (orfandat transitòria) | brief |

---

## Verificació del documentador

- **Re-grep `Quote`/`QuoteLine`**: `QuoteLine` = `AbstractDocumentLine` + FK `quote` (`models.py:255-281`);
  cap FK entrant (grep FK a QuoteLine sobre `fhort/` = buit). `Quote` sense camps propis (`models.py:216-252`).
- **Re-grep conversió**: un únic camí, `convert_quote_to_order` (`services.py:132`) ↔ `quotes/{id}/convert/`
  (`views.py:150`) ↔ `quotes.convert` (`endpoints.js:433`) ↔ botó `QuoteDetail.jsx:91,122`. Guard de BD:
  `source_quote` OneToOne unique (`models.py:304-306`).
- **Re-grep absència de reattach**: `reattach|re_attach|reassign|re_assign|adopt` sobre `commerce/` retorna
  **només** comentaris/help_text (`views.py:284`, `services.py:323`, `models.py:486`) i la migració/l'informe
  `orphaned`; **cap funció, cap endpoint d'acció, cap botó** → re-adopció confirmada **NO EXISTENT**.
