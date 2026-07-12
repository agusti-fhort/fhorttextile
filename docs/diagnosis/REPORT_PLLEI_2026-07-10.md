# REPORT — P-LLEI: commerce fora del camí de meritació (D1 + D2)

Data: 2026-07-10 · **Patró B (IMPLEMENTACIÓ)** · staging `/var/www/ftt-staging`, branca `dev`
Base: `docs/diagnosis/DIAGNOSI_BACKOFFICE_POSTREFACTOR.md` (T1, T2)
Llei: **DUES FACTURACIONS SEPARADES** (`DECISIONS.md §4`, 2026-07-07)

**2 commits, sense push.** Regla del verd completa. Cap migració, cap canvi de model,
cap escriptura persistida a la BD durant la verificació.

| Peça | Commit | Estat |
|---|---|---|
| P1 — `assign_work_order` fora de l'atomic de meritació | `51a113e` | ✅ VERD |
| P2 — `reconcile_consumption` = meritació pura + `reconcile_work_orders` nou | `a09ab20` | ✅ VERD |

---

## P1 — D1: separació transaccional dels dos mons

**Fitxer:** `backend/fhort/tasks/services_c.py`, bloc `if to_status == 'InProgress':`

### El que hi havia

Un sol `try / with transaction.atomic()` contenia **les dues facturacions**: l'update de
`consumption_started_at`, el `ConsumptionRecord`, el `send()` del senyal (el receiver del
qual escriu `ModelConsumptionEvent` a `public` sobre la **mateixa transacció**) i, al final,
`assign_work_order(task, now)` — codi del mòdul comercial. Tot sota un `except Exception`
que **no re-llança**.

Conseqüència (T1): un error de `commerce` feia **rollback silenciós d'una meritació ja
escrita**. El tècnic veia la transició feta; el llibre de facturació SaaS perdia l'apunt, i
només el `logger.exception` en deixava rastre fins al següent reconcile.

### El que hi ha ara

Dos **savepoints independents**, en aquest ordre:

1. **Meritació SaaS** (`backoffice→tenant`) — `atomic()` + `try/except` N10, sense re-raise.
   Conté exactament el que hi havia: guard `consumption_started_at IS NULL`, `ConsumptionRecord`,
   `send()`. **Cap línia de commerce.**
2. **Encàrrec** (`studio→tercers`) — `assign_work_order(task, now)` amb `atomic()` i
   `except Exception: logger.exception` **propis**, sense re-raise.

Els missatges de log s'han separat (`meritacio fallida` / `assignacio work_order fallida`),
i cadascun apunta a la seva comanda de reconciliació.

### Detall que ho fa correcte (i que no era obvi)

`transition_task` ja està decorada amb **`@transaction.atomic`** (`services_c.py:95`). Els
`atomic()` interns són, per tant, **savepoints**, no transaccions noves. Això és el que
permet capturar l'excepció a fora sense corrompre la transacció externa: sense el savepoint
propi, un `except` que empassa deixaria la transacció de `transition_task` en estat avortat i
la transició del tècnic cauria. **Per això l'assignació necessita el seu `atomic()`, no només
el seu `try`.**

### Frontera respectada

No s'ha tocat `assign_work_order` per dins, ni `_resolve_work_order`, ni el senyal, ni el
receiver. Repassats **tots** els cridadors de `transition_task` (llista de la diagnosi B2):
`views_b.py:449`, `views_b.py:559`, `models_app/views.py:737,739`,
`services_size_check.py:221-222`, `retype_scaling_to_grading.py:66-67`. Cap depèn de l'ordre
antic: tots consumeixen el `dict` de retorn, que és idèntic. L'ordre relatiu
(meritació → encàrrec) també es conserva.

---

## P2 — D2: cada facturació té la seva comanda de backfill

### `backoffice/management/commands/reconcile_consumption.py`

Retirats l'import d'`assign_work_order` i la branca B4a sencera; amb ells, el comptador
`total_wo` i l'import `timezone`, que quedava orfe. La línia de resum ja no menciona
work_orders.

**Zero dependència de `fhort.commerce`**, verificat no per `grep` sinó recorrent l'AST del
fitxer i llistant-ne els mòduls importats:

```
mòduls importats: ['django.core.management.base', 'django.db', 'django.db.models',
                   'django_tenants.utils', 'fhort.models_app.models',
                   'fhort.tasks.models', 'fhort.tasks.signals', 'logging', 'uuid']
DEPENDÈNCIA COMMERCE: CAP ✓
```

Els imports de `tasks`/`models_app` **es mantenen**, com indicava el brief: el llibre de
meritació es construeix llegint l'activitat del tenant. La llei prohibeix `commerce`, no
llegir el tenant.

### `commerce/management/commands/reconcile_work_orders.py` (nou)

Paquet `commerce/management/commands/` creat (no existia). La lògica B4a moguda **tal qual**:
mateixos flags `--dry-run` / `--tenant`, mateix càlcul
`when = MIN(TaskTransition.at where to_status='InProgress')` amb fallback a `started_at` i
`timezone.now()`, mateix recorregut per-tenant amb `schema_context`.

Afegit només el que la comanda necessitava per viure sola: `atomic()` propi per assignació,
reporting per tasca (`OK` / `SKIP` amb el motiu / `ERROR`) i un `No gaps found.` simètric al
del germà.

### Docstrings

Totes dues comandes citen la llei i n'enumeren les **4 fronteres**: entitats · imports ·
transacció · reconciliació. Cadascuna nomena el seu germà a l'altra banda.

---

## Verificació

Lliçó S03b respectada: **tota** prova d'escriptura dins `transaction.atomic()` amb rollback
explícit, sobre el model QA `[QA-SC] BRW-26-SS-0002` (pk=182). El golden 162 mai s'ha tocat.
Arnès a `scratchpad/verify_pllei.py` (fora del repo).

| # | Escenari | Resultat |
|---|---|---|
| 1 | Transició feliç | transició **OK** · meritació **OK** (`ConsumptionRecord`=1, `ModelConsumptionEvent` a public=1) · `work_order=13` **OK** |
| 2 | `assign_work_order` forçat a petar | transició **OK** · **meritació PERSISTEIX** · `work_order=None` · log `assignacio work_order fallida` |
| 2b | Meritació forçada a petar | transició **OK** · meritació revertida + log `meritacio fallida` · **`work_order=13` assignat igualment** |
| 3 | `reconcile_consumption --dry-run` | `No gaps found.` → `0 merited, 0 skipped, 0 errors.` **Cap menció de work_orders** |
| 4 | `reconcile_work_orders --dry-run` | `30 work_orders assigned, 0 errors` — exactament els 30 pendents que la diagnosi ja havia comptat |

Estat real de la BD després de totes les proves: `consumption_started_at=2026-06-16
19:10:11.566582+00`, `records=1`, `events_public=1` — **idèntic al d'abans**.

**L'escenari 2b és la prova que el bug ha mort.** Amb el codi antic, un error de meritació
avortava l'atomic compartit i l'assignació no s'arribava a intentar mai. Ara els dos mons
fallen i tenen èxit de manera independent. El brief demanava verificar aquest invariant, no
assumir-lo; per això s'ha afegit com a escenari propi.

**Grep de frontera** (`grep -rn "commerce" backend/fhort/backoffice/`): els únics encerts són
les línies del docstring que el propi brief demanava escriure. Cap import, cap ús de símbol
(`assign_work_order`, `WorkOrder`): confirmat amb un grep específic i amb l'AST.

**Regla del verd:** `manage.py check` → `System check identified no issues (0 silenced)`
després de cada peça. Frontend no tocat → `npm run build` no aplica (i, per la diagnosi B1,
`frontend-backoffice` no és construïble sense `npm install`).

---

## Estat final del backoffice (per al vault — `ESTAT_BACKOFFICE.md`)

> No s'ha tocat cap fitxer d'estat: al servidor no hi ha vault i, per llei del `CLAUDE.md`,
> `ESTAT_BACKOFFICE.md` no es commiteja. Aquest bloc és el que cal abocar-hi.

- **Cadena de meritació: VIVA i ara AÏLLADA.** Emissor únic (`transition_task`), guard
  d'idempotència, N10 no-fatal i receiver a `public` intactes. La novetat és que la meritació
  ja no comparteix transacció amb res de `commerce`.
- **Llei DUES FACTURACIONS SEPARADES: complerta a les 4 fronteres.** Entitats i FK ja eren
  netes (diagnosi B3); imports i transacció ho són des d'avui; la reconciliació està partida
  en dues comandes germanes.
- **`reconcile_consumption`** = meritació pura (app `backoffice`, SHARED/public).
  **`reconcile_work_orders`** = encàrrecs (app `commerce`, TENANT). Cap de les dues sap de
  l'altra.
- **Deute obert conegut:** 30 tasques amb activitat i sense `work_order` esperant
  `reconcile_work_orders` (sense `--dry-run`). **No s'ha executat**: és una escriptura i
  aquest brief no l'autoritzava.
- **Sense canvis** a migracions, models, endpoints ni frontend.

---

## Anotacions fora d'scope (vistes, no tocades)

1. **Premissa del brief inexacta ×2.** `DECISIONS.md` **no té** cap subsecció "§4 REPRESA
   BACKOFFICE": §4 és *"Decisions d'abast vives"* i allotja la llei
   `DUES FACTURACIONS SEPARADES` (`DECISIONS.md:105-107`). I la llei **no enumera** "4
   fronteres" — el text són 3 línies (*"No comparteixen entitats. Cap barreja de models"*).
   Les 4 fronteres dels docstrings són les que es dedueixen de la diagnosi (T1/T2) i queden
   **proposades** per pujar a `DECISIONS.md`. 💡 Decisió del CTO.
2. **`.gitignore:13` conté `backoffice/`** (a més de dues línies duplicades `backoffice/dist/`).
   Regla ampla: qualsevol fitxer **nou** sota `backend/fhort/backoffice/` neix ignorat i pot
   passar desapercebut en un `git add` de paths explícits. Els fitxers actuals ja són tracked
   i no en pateixen. Val la pena ancorar-la (`/backoffice/dist/`) abans de tornar a treballar
   l'app. **No tocat.**
3. **`transition_task` és `@transaction.atomic` sencera** (`services_c.py:95`), de manera que
   qualsevol `except` que empassi sense savepoint propi corromp la transacció del tècnic. És
   una trampa latent per a futurs afegits dins aquest bloc. Documentat aquí; el codi actual
   és correcte.
4. **Treball d'altres sessions al working tree** (branca `dev` és concurrent): `DECISIONS.md`,
   `docs/OPS_S03_NGINX.md` i `frontend-backoffice/.env` estaven modificats i
   `frontend-backoffice/.env.prod.bak` sense trackejar **abans** d'aquesta sessió. **No s'han
   tocat ni commitejat.** L'índex de tots dos commits conté exclusivament els 4 fitxers meus.
5. **El col·lector de BRW/2026-07 està `CLOSED`**, així que `_resolve_work_order` retorna
   `None` per disseny (`services_c.py:77-78`) i el camí feliç de l'escenari 1 només s'exercita
   reobrint-lo dins la transacció rebobinada. Comportament esperat, no un bug — però explica
   per què part dels 30 forats pendents podrien no resoldre's sols en executar
   `reconcile_work_orders`: els mesos ja tancats requereixen resolució manual.

---

## Què ha de fer el CTO

1. Revisar la cadena: `git show 51a113e` i `git show a09ab20`.
2. **Push des de SSH** (cap agent ha fet push).
3. Decidir sobre les anotacions 1 (pujar les 4 fronteres a `DECISIONS.md`) i 2 (ancorar el
   `.gitignore`).
4. Quan toqui, executar `manage.py reconcile_work_orders` **sense** `--dry-run` per tancar els
   30 forats d'encàrrec — sabent que els de mesos amb col·lector `CLOSED` en quedaran fora
   (anotació 5).
5. Abocar el bloc *"Estat final del backoffice"* a `ESTAT_BACKOFFICE.md` al vault.
