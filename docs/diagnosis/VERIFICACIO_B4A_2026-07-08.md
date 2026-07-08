# Verificació runtime B4a — WorkOrder + extres + tancament (2026-07-08)

Gate del bloc B4a. Tota l'execució en `schema_context('fhort')` dins `transaction.atomic()`
revertida (**cap dada persistida**). Codi verificat: commits `ca124b6`, `7f5b559`,
`333b5d7`, `0d1e46b`, `4346bdc`, `600192d`. `manage.py check` net i `npm run build` net a
cada peça. Decisions Patró C (Agus, 2026-07-08) implementades tal com es van tancar.

## P1 — Constraint parcial `origen='prevista'` (`ca124b6`)
`UniqueConstraint(fields=[model,task_type], condition=Q(origen='prevista'),
name='uniq_prevista_model_tasktype')` — migració `tasks/0036`. Els 4 consumidors
(define-tasks, open-task, assign-batch, QA clone) filtren/creen amb `origen='prevista'`.

| # | Comprovació | Resultat |
|---|---|---|
| 1 | prevista + extra ad_hoc del MATEIX task_type | ✅ conviuen |
| 2 | segona ad_hoc del mateix tipus | ✅ OK (constraint no cobreix ad_hoc) |
| 3 | segona PREVISTA del mateix tipus | ✅ IntegrityError (`uniq_prevista_model_tasktype`) |
| 4 | canònica prevista trobada pels 4 camins | ✅ count=1 (total (model,tt)=3) |

## P2 — Model WorkOrder + camps ModelTask (`7f5b559`)
WorkOrder (contenidor d'execució, NO AbstractDocument): `kind` ORDER/COLLECTOR, numeració
`WO` (`reserve_document_number`), `price/recipe_snapshot`, `status` OPEN/CLOSED. Migracions
`commerce/0012`, `tasks/0037`. FK `ModelTask.work_order` per string (sense cicle).

| # | Comprovació | Resultat |
|---|---|---|
| 1 | COLLECTOR: numeració automàtica | ✅ WO-2026-0001 |
| 2 | 2n COLLECTOR mateix (customer, period) | ✅ IntegrityError (`uniq_collector_customer_period`) |
| 3 | COLLECTOR amb model | ✅ CHECK `collector_no_model_no_orderline` |
| 4 | ORDER amb model | ✅ WO-2026-0002 |
| 5 | ModelTask.work_order + off_recipe + `related_name='tasks'` | ✅ |

## P3 — Col·lector lazy al hook + reconcile (`333b5d7`)
Assignació a `transition_task` (primera InProgress de CADA tasca, idempotent, dins l'atomic
no-fatal `if rows`/germà). Branca nova a `reconcile_consumption` (period = MIN(→InProgress)).

| # | Comprovació | Resultat |
|---|---|---|
| 1 | hook: tasca de model sense encàrrec → col·lector (customer, mes) + assignada | ✅ WO-2026-0001 COLLECTOR |
| 2 | segona tasca mateix mes | ✅ mateix col·lector |
| 3 | tasca mes següent | ✅ col·lector nou (2026-08) |
| 4 | ORDER: off_recipe segons `recipe_snapshot` | ✅ dins-recepta False · fora-recepta True |
| 5 | col·lector del mes CLOSED | ✅ no assigna (queda per al reconcile) |
| — | `reconcile_consumption --dry-run --tenant fhort` | ✅ 31 tasques amb work_order proposat, 0 errors |

## P4 — Extres ad_hoc + WorkOrderAdjustment (`0d1e46b`)
Endpoint `POST model-task-items/extra/` (gate DEFINE_TASKS). Entitat `WorkOrderAdjustment`
(EXTRA_BILL/EXTRA_ABSORB/DEDUCTION). Migració `commerce/0013`.

| # | Comprovació | Resultat |
|---|---|---|
| 1 | crear extra | ✅ 201, origen=ad_hoc, off_recipe=True, work_order lligat |
| 2 | extra a WO CLOSED | ✅ 409 |
| 3 | model no coincident amb WO ORDER | ✅ 400 |
| 4 | camps incomplets | ✅ 400 |
| 5 | WorkOrderAdjustment resol l'extra | ✅ wo.adjustments=1 |

## P5 — Tancament amb política de bloquejos (`4346bdc`)
`close_work_order` (atòmic, recull TOTS els bloquejos, resposta estructurada). Endpoint
`POST work-orders/{id}/close/`. WorkOrderViewSet (lectura + close, filtres kind/status/
customer/period). **Sense venciments** (DocumentDueDate NO tocat, segons decisió).

| # | Comprovació | Resultat |
|---|---|---|
| 1 | tasca Paused | ✅ bloqueja (blockers=['Paused']) |
| 2 | extra off_recipe sense adjustment | ✅ bloqueja; amb `resolve_extras` → tanca |
| 3 | Pending | ✅ proposa; `cancel_pending` → tanca + DEDUCTION + deslliga |
| 4 | tot Done | ✅ tanca (status=CLOSED, closed_by) |
| 5 | re-tancar un ja tancat | ✅ idempotent (`already_closed`) |

## P6 — Frontend Encàrrecs + marca off_recipe (`600192d`)
Pàgina Encàrrecs (menú Comercial): llista filtrable + fitxa amb tasques (estat + minuts de
timer agregats), extres marcats i botó Tancar amb modal (blockers vermell · extres
facturar/absorbir · pendents amb deducció). Marca off_recipe (filet grana) al WorkPlan:
**es cabla la marca ja existent** (abans el board no emetia `origen`/`off_recipe`) i es fa
dependre de `off_recipe`. i18n `workorders` ca/en/es (paritat). `npm run build` net.

## Notes de mètode (refinaments conscients sobre el brief)
- **P3 — assignació per-tasca:** el brief situava el get_or_create "dins `if rows:`" (que
  només dispara a la primera InProgress del MODEL). Per correcció, l'assignació corre a
  CADA primera InProgress de tasca (superset); el col·lector segueix sent per-model×mes via
  get_or_create idempotent. Es va escollir un bloc `try/atomic` germà del de meritació
  (mateix patró N10 no-fatal) en lloc de compartir-lo, per desacoblar-ne les fallades.
- **P5 — resolució al tancament:** els `WorkOrderAdjustment` que resolen extres es creen
  DINS el `close` (via `resolve_extras`), fidel a "la resolució de l'extra és del tancament"
  (nota de P4). No es va afegir cap endpoint d'ajust separat (codi mínim).
- **Deducció de Pending:** es crea `DEDUCTION` amb `amount=0` (marcador) i es deslliga la
  tasca del WO; l'import real el posarà l'albarà (B4c) des del `price_snapshot`. La tasca NO
  s'esborra (no hi ha estat 'Cancelled' a ModelTask; s'evita tocar la màquina d'estats).

## Fora d'abast (conscient, per mantenir la sessió acotada)
Expense (bloc següent) · DeliveryNote/albarà i preu real dels adjustments (B4c) · assignació
model↔order_line des del wizard (B4b, necessita modal 3) · Settlement/venciments · gate de tier.

## Pendent de l'Agus
Revisar la cadena amb `git show <hash>` i **fer push des de SSH** (l'agent no fa push). Els
6 commits estan intercalats amb commits `pom:` d'una sessió concurrent (mateixa identitat
git), però són íntegres i independents (fitxers separats). Aplicar migracions a PROD en
desplegar: `tasks/0036`, `commerce/0012`, `tasks/0037`, `commerce/0013`.
