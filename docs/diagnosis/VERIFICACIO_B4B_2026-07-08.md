# Verificació runtime B4b — separació de departaments, Expense, assignació, GTI (2026-07-08)

Gate del bloc B4b. Execució en `schema_context('fhort')` dins `transaction.atomic()` revertida
(**cap dada persistida**). Codi verificat: commits `573c150`, `55c314c`, `7e07440`, `d157778`,
`78b0dc3`, `08cc305`. `manage.py check` net i `npm run build` net a cada peça.

**Decisió Patró C (Agus, 2026-07-08) — SEPARACIÓ DE DEPARTAMENTS:** el TÈCNIC tanca el
WorkOrder (feina feta); el COMERCIAL revisa després en preu de VENDA (no cost). Dos actes,
dos moments, dues persones. Conseqüència: els extres NO bloquegen el close; el gate d'extres
es mou a l'emissió de l'albarà (B4c).

## P1 — Close bloqueja només per feina inacabada (`573c150`)
Rectificació de B4a-P5: `close_work_order` treu el bloqueig d'extres i el paràmetre
`resolve_extras`. Bloqueja NOMÉS InProgress/Paused. TODO al codi: el gate d'extres viu a
`generate_delivery_note()` (B4c).

| # | Comprovació | Resultat |
|---|---|---|
| 1 | extra off_recipe sense resoldre | ✅ ARA TANCA |
| 2 | tasca Paused | ✅ bloqueja llistant-la |
| 3 | Pending → proposa; cancel_pending | ✅ tanca + DEDUCTION (reté FK a ModelTask) |
| 4 | mixt Done+extra+InProgress | ✅ bloqueja només per InProgress |

## P2 — Endpoint /review/ comercial (`55c314c`)
`POST work-orders/{id}/review/` (gate CONFIGURE): el comercial fixa el PREU DE VENDA. NO toca
cap cost. `get_or_create` per (work_order, model_task, kind) — retroba la DEDUCTION marcador
del close i li fixa preu.

| # | Comprovació | Resultat |
|---|---|---|
| 1 | revisar un WO OPEN | ✅ ValidationError (només CLOSED) |
| 2 | DEDUCTION marcador del close reté FK | ✅ model_task ancorat, amount=0 |
| 3 | review fixa preu extra + repreua deducció | ✅ EXTRA_BILL=12,50 · DEDUCTION=8,00 |
| 4 | amount=0 vàlid a EXTRA_ABSORB | ✅ (la intenció la porta el kind) |
| 5 | re-review idempotent (mateix wo,task,kind) | ✅ 1 fila, amount actualitzat |
| 6 | tasca que no pertany al WO | ✅ ValidationError |

## P2-bis — WorkOrderAdjustment reté FK a ModelTask
**Ja correcte a B4a**: `WorkOrderAdjustment.model_task = FK(tasks.ModelTask, SET_NULL)`
(`commerce/models.py:537`). El close crea la DEDUCTION amb `model_task=t` i la reté malgrat
deslligar la tasca del WO (`work_order=NULL`). **Cap migració** — només documentat.

## P3 — Expense (`7e07440`)
Model `Expense` (línia externa: EXTERNAL_SERVICE/GOODS, guard a `clean()`). cost_price (cost
real) + sale_price (preu venda). NO és tasca. `ExpenseViewSet` CRUD gated CONFIGURE, satèl·lit
`?work_order=`. Migració `commerce/0014`.

| # | Comprovació | Resultat |
|---|---|---|
| 1 | Expense EXTERNAL_SERVICE | ✅ creat, cost/venda/qty |
| 2 | nature INTERNAL_SERVICE | ✅ `clean()` ValidationError |
| 3 | serializer replica el guard | ✅ 400 |
| 4 | proveïdor per defecte (ProductSupplier.is_default) | ✅ proposat |
| 5 | Expense no genera ModelTask | ✅ 0 tasques |

## P4 — Assignació model↔línia + WorkOrder ORDER (`d157778`)
`assign_model_to_order_line` (atomic): crea WO ORDER amb price/recipe_snapshot congelats,
+1 a qty_allocated, i MIGRA les tasques del col·lector al nou ORDER amb off_recipe recalculat.

| # | Comprovació | Resultat |
|---|---|---|
| 1 | WO ORDER amb snapshots congelats | ✅ recipe={task_codes}, price={unit_price,product_code} |
| 2 | migració col·lector→ORDER, off_recipe recalculat | ✅ dins-recepta False · fora True · 2 migrades |
| 3 | qty_allocated += 1 | ✅ 1,00 |
| 4 | col·lector buit NO s'esborra | ✅ conservat (rastre) |
| 5 | model amb ORDER actiu | ✅ ValidationError |
| 6 | qty_allocated ≥ quantity | ✅ ValidationError |
| 7 | model i comanda de clients diferents | ✅ ValidationError |

> ⚠️ **REGLA DE MIGRACIÓ DEL COL·LECTOR (a confirmar per l'Agus):** implementada tal com la
> descriu el brief — TOTES les tasques del model que pengen d'un COLLECTOR es migren al nou
> ORDER (cap albarà existeix a B4b, la feina contractada no s'ha de facturar al calaix
> mensual). S'ha deixat un **TODO B4c** al codi: quan existeixi l'albarà, cal EXCLOURE de la
> migració les tasques ja albaranades. És reversible (dev, sense push).

## P5 — GTI obligatori al wizard (`78b0dc3`)
Guard al frontend (`ModelWizard.handleCreate` → salta al pas 2) + guard de servei al backend
(`create_model_wizard` → 400 si falta `garment_type_item_id`). **BD sense canvi** (columna
nullable; 0 models amb GTI null al tenant → cap backfill; TODO NOT NULL futur). i18n. Gate:
`manage.py check` + `npm run build` nets.

## P6 — Frontend (`08cc305`)
Fitxa Encàrrec: bloc **Despeses** (alta amb proposta de proveïdor/preus comparats
ProductSupplier + preu de venda des de base_price/markup) i bloc **Revisió comercial**
(visible si CLOSED: taula extres/deduccions amb kind + import, zero permès → `/review/`). Es
simplifica el modal de tancament (els extres ja no bloquegen). **Modal 3** a la fitxa de
Comanda: assigna un model (filtrat per client, `?customer=`) a una línia → crea WO ORDER i
migra el col·lector; avís GTI (via `garment_type_item_nom`) + nota de migració. i18n
`workorders`/`orders` ca/en/es. `npm run build` net.

## Anomalia observada (no és un leak dels tests)
Al tenant `fhort` hi ha **1 WorkOrder persistit**: `WO-2026-0001 COLLECTOR (client 7,
2026-07)` amb **2 tasques reals** lligades (256 `pom`, 272 `pattern_cad`, Paused). És el hook
lazy de B4a funcionant en ús real de dev (no el generen els tests, que corren en txn revertida
i deixen 0 adjustments/0 expenses). No s'ha tocat.

## Notes de mètode (refinaments conscients)
- **P2 — clau de l'adjustment:** es fa servir `get_or_create(work_order, model_task, kind)`
  tal com el brief; retroba la DEDUCTION del close. Cas límit (re-kind d'un extra BILL→ABSORB)
  deixaria una fila òrfena; el frontend n'envia una per tasca, així que no es dispara a la
  pràctica. Anotat per si B4c hi vol una garantia dura.
- **P3 — endpoint "niat":** `commerce/expenses/?work_order=` (satèl·lit pla, patró order-lines)
  en lloc d'una ruta niada literal; convenció existent del mòdul.

## Fora d'abast (conscient)
DeliveryNote/albarà i el gate d'extres a l'emissió (B4c) · Settlement (B5) · gate de tier (B5)
· informes (B6) · Expense amb event de calendari · fer `Model.garment_type_item` NOT NULL a BD.

## Pendent de l'Agus
Revisar amb `git show <hash>` i **push des de SSH**. Migracions a aplicar a PROD: `commerce/
0014` (Expense). Confirmar la **regla de migració del col·lector** (P4). Els commits estan
intercalats amb commits `pom:`/`docs:` d'una sessió concurrent (mateixa identitat git),
íntegres i independents.
