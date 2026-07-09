# DIAGNOSI_P0_1_PLA_TREBALL — contracte de dades de P1 (temps + obertures per ModelTask)

> **Patró A · READ-ONLY ABSOLUT.** Cap fitxer de producte tocat, cap migració, cap escriptura,
> cap push. Branca `dev`, NOMÉS `/var/www/ftt-staging`, tenant `fhort`. L'únic fitxer escrit és
> aquest. Continuació de `docs/DIAGNOSI_P0_PLA_TREBALL.md` (ordre canònic = `TaskType.default_order`;
> contracte de `transition`). Aquí es tanca d'on surten **temps consumit** i **obertures** per
> `ModelTask`, abans d'escriure P1. Models de prova: 182 i 162. Data: 2026-06-21.

---

## 0. Com llegir

- **FET** = afirmació amb `fitxer:línia` (rutes relatives a `/var/www/ftt-staging`) i/o dada real
  (consulta executada dins `schema_context('fhort')`). **💡 PROPOSTA** = només a la secció final.
- Totes les consultes de BD d'aquest doc s'han executat amb el tenant actiu (la trampa que va
  buidar P0). Models 182 i 162 tenen vida.

---

## Titulars

- **Temps consumit per tasca = `Sum(timers.minuts)`** — derivable, sense camp nou. `TimerEntrada.minuts`
  es **materialitza en tancar** el timer; ja existeix l'helper canònic `_real_minutes` i el patró ja
  s'usa a l'albarà (`steps[].minutes`).
- **Obertures per tasca = `count(TaskTransition, to_status='InProgress')`** — derivable, sense camp
  comptador (no n'hi ha cap a `ModelTask`). Cada Play hi deixa una fila (confirmat amb dades reals).
- **assignee_nom NO se serveix avui** (el compositor dona només `assignee_id`); és derivable de
  `assignee.nom_complet` amb `select_related`, **sense migració**.
- El compositor `model_dashboard_view` ja serveix una **llista plana de tasques (Q4 de F1)** ordenada
  per `ModelTask.order` (NO canònic) amb `{id, task_type, task_type_code, status, assignee_id, order}`.
  P1 l'amplia (temps/obertures/assignee_nom/default_order, ordre canònic) i P2 la retira.

---

# PREGUNTA A — TEMPS CONSUMIT per ModelTask

## A.1 `TimerEntrada` (FET)
`tasks/models.py:116-130`. Camps: `model_task` FK→ModelTask **`related_name='timers'`** (`:117`),
`tecnic` FK→UserProfile (`:118`), `inici` DateTime (`:119`), `fi` DateTime null (`:120`),
**`minuts` PositiveIntegerField null** (`:121`), `actiu` Bool (`:122`). `Meta.ordering=['-inici']`.
→ La durada **queda MATERIALITZADA** al camp `minuts` (no es recalcula de inici/fi a la lectura);
és null mentre el timer és obert.

## A.2 Obertura/tancament a `transition_task` (FET)
- Obrir: `_open_timer(task, profile)` crea `TimerEntrada(inici=now, actiu=True)` (`tasks/services_c.py:19-21`);
  es crida en entrar a `InProgress` (`services_c.py:65`).
- Tancar: `_close_open_timer(task)` (`services_c.py:24-31`) busca el timer obert (`fi__isnull=True, actiu=True`)
  i, si n'hi ha, escriu `fi=now`, **`minuts = max(0, int((now-inici).total_seconds()//60))`**, `actiu=False`
  (`services_c.py:27-31`). Es crida en `InProgress→{Paused,Done}` (`services_c.py:72-73`) i en pausar
  l'altra tasca per exclusió (`services_c.py:59`). → **En tancar SÍ escriu la durada** (`minuts`).

## A.3 `record_actual_time` i camps de temps de `ModelTask` (FET)
- `record_actual_time(model_task)` (`tasks/services_i.py:19+`), cridat en `Done` (`services_c.py:121-125`),
  **NO escriu cap temps sobre `ModelTask`**: alimenta l'estadística Welford de la cel·la
  `TaskTimeEstimate (garment_type_item × task_type)` (`services_i.py:20-31`). Salta si el model no té
  `garment_type_item`.
- Helper canònic de temps real PER tasca: **`_real_minutes(model_task) = model_task.timers.aggregate(Sum('minuts'))['s'] or 0`** (`tasks/services_i.py:14-15`). És exactament "temps consumit per tasca".
- **`ModelTask` (camp per camp, `tasks/models.py:201-223`)** — marcats els de temps:
  - `model` FK (`:205`), `task_type` FK (`:206`), `status` (`:207`), `assignee` FK null (`:208-209`),
    `order` (`:210`).
  - `started_at` DateTime null (`:211`) — **temps** (marca d'inici, no acumulat).
  - `finished_at` DateTime null (`:212`) — **temps** (marca de fi, no acumulat).
  - `estimated_minutes` PositiveInt null (`:213`) — **temps** (snapshot d'ESTIMACIÓ en crear, NO real).
  - `planned_start`/`planned_end` DateTime null (`:216-219`) — **temps** (previsió del motor, no real).
  - `planned_locked` Bool (`:220`), `created_at`/`updated_at` (`:222-223`).
  → **NO existeix cap camp de temps REAL acumulat sobre `ModelTask`.** El temps consumit s'ha de
  DERIVAR sumant `timers.minuts`.

## A.4 Agregat de temps per tasca ja servit en algun lloc? (FET)
- **SÍ, a l'albarà** `consumption_delivery_view` (`models_app/views.py:1164`): construeix `steps[]` amb
  **un element per `ModelTask`** que inclou els seus minuts (bucle `for tm in mt.timers.all()` sumant
  `tm.minuts`, `models_app/views.py:1189-1201`); també `per_technician` (suma per tècnic, `:1199-1201`)
  i `history` (transicions). → L'agregació "minuts per ModelTask" **ja té precedent viu** a l'albarà.
- Altres sumes de `TimerEntrada`: `_real_minutes` (`services_i.py:15`, per tasca); registre d'activitat
  agrega per tècnic (`models_app/views.py:1465-1473`, per `tecnic_id`, no per tasca).
- El **compositor del dashboard NO serveix temps per tasca avui** (la seva llista plana no en porta — veure D.3).

## A.5 Dada real (FET, `schema_context('fhort')`) — temps = `Sum(timers.minuts)` calculat en viu

| model | task_id | code | status | Σ minuts |
|---|---|---|---|---|
| 182 | 246 | size_check | Done | 1 |
| 162 | 149 | pom | Done | 7 |
| 162 | 236 | size_check | Done | 80 |
| 162 | 150 | tech_sheet | Done | 895 |

→ La suma surt **calculada en viu** de `timers.minuts` (materialitzat per timer); cap camp acumulat
a `ModelTask`. Model 182 té 1 sola tasca amb timer; 162 en té 3 amb temps real significatiu.

---

# PREGUNTA B — OBERTURES per ModelTask

## B.1 Camp comptador a `ModelTask`? (FET)
**NO existeix** cap camp `times_opened`/`reopen_count`/`n_obertures` a `ModelTask`
(llista completa de camps a A.3, `tasks/models.py:201-223`). Cap escriptor n'incrementa cap.

## B.2 Derivació via `TaskTransition` (FET)
`TaskTransition` (`tasks/models.py:237-253`): `model_task` FK **`related_name='transitions'`** (`:240`),
`from_status` null (`:241`), **`to_status`** (`:242`), `by` FK UserProfile null (`:243`), `at` auto
(`:245`). Log **immutable**, una fila per transició.
- Cada Play escriu una fila amb `to_status='InProgress'`: `transition_task` registra sempre
  `_log(task, frm, to_status, profile)` (`services_c.py:83`); els Play vàlids són `Pending→InProgress`,
  `Paused→InProgress`, `Done→InProgress` (`ALLOWED`, `services_c.py:11-16`) → tots deixen
  `to_status='InProgress'`. → **Obertures = `transitions.filter(to_status='InProgress').count()`**, derivable.
- Relacionat però DIFERENT: `rectification_count` = `from_status='Done', to_status='InProgress'`
  (`services_c.py:130-133`) → reobertures ⊂ obertures (el serializer ja exposa `rectifications`).

## B.3 Dada real (FET, `schema_context('fhort')`) — count(to_status='InProgress')

| model | task_id | code | obertures (InProgress) |
|---|---|---|---|
| 182 | 246 | size_check | 1 |
| 162 | 149 | pom | 1 |
| 162 | 236 | size_check | 2 |
| 162 | 150 | tech_sheet | 7 |

→ Coherent amb el temps (la tech_sheet de 162, 895 min i 7 obertures, és la tasca treballada en moltes
sessions). No hi ha camp comptador amb què comparar (B.1) → la derivació és l'única font. **Quadra.**

---

# PREGUNTA C — ASSIGNEE servible per al rendering "d'altri"

## C.1 (FET)
`ModelTask.assignee` FK→`accounts.UserProfile`, `on_delete=SET_NULL`, **nullable** (`tasks/models.py:208-209`).
`UserProfile.nom_complet` existeix i `__str__ = nom_complet or user.get_username()` (`accounts/models.py:11,25-26`).

## C.2 (FET)
- `ModelTaskSerializer` (`tasks/serializers_b.py:13-37`) exposa **`assignee`** (l'id), NO el nom
  (camps: `id, model, model_codi, task_type, task_type_code, task_type_name, status, assignee, order,
  created_at, updated_at, started_at, finished_at, estimated_minutes, rectifications, planned_*`).
- El compositor del dashboard dona només **`assignee_id`** (veure D.3).
- → **El nom NO és servible avui sense afegir-lo.** Però és derivable de `assignee.nom_complet` amb
  `select_related('assignee')`, **sense migració** (dada ja existent; confirmat real: 246→"Agustí Devant",
  149/150→"Salvador Devant"). Per pintar "Escalat · Montse" cal afegir un camp `assignee_nom` a la
  forma servida (no és camp nou de BD).

---

# PREGUNTA D — El COMPOSITOR (endollar P1 additiu)

## D.1 (FET)
`model_dashboard_view` — `models_app/views.py:1243`. Ruta `GET models/<int:model_id>/dashboard/` —
`models_app/urls.py:180`. `@api_view(['GET'])` + `IsAuthenticated`, dict construït a mà.

## D.2 Estructura ACTUAL de la resposta (FET) — claus top-level (`models_app/views.py:1313-1318`):
- `model_id` (int).
- `on_soc` (Q1 "on sóc": fase/estat/ready_for_gate/next_phase/blockers) — bloc construït a la view.
- `artefactes_vigents` (fitxa/grading/base) — Q1 artefactes.
- `tasques` (Q4, **llista plana de tasques** — veure D.3).
- `atencio` (Q3: `{alertes, n_pendents}`, alertes POM pendents) — afegit a B3.

## D.3 La llista plana de tasques actual (FET) — la que el Pla de treball ABSORBEIX
Construïda a `models_app/views.py:1304-1311`, sobre `tasks = sorted(model.model_tasks.all(),
key=lambda t: (t.order, t.id))` (`:1264`) → **ordenada per `ModelTask.order`, NO pel canònic
`default_order`**. Forma de cada element:
```
{ 'id': int,
  'task_type': str|null,        # t.task_type.name
  'task_type_code': str|null,   # t.task_type.code
  'status': str,                # Pending|InProgress|Paused|Done
  'assignee_id': int|null,
  'order': int }                # ModelTask.order (ordre d'inserció)
```
→ NO porta temps, NO obertures, NO assignee_nom, NO default_order, i **ordena per `order` (inserció)**,
no pel canònic. P1 amplia aquesta forma; P2 la retira quan el Pla de treball la cobreixi.

## D.4 status choices (FET)
`ModelTask.STATUS_CHOICES = [('Pending'),('Paused'),('InProgress'),('Done')]` (`tasks/models.py:203-204`).

---

# 💡 PROPOSTA (secció final, separada) — contracte de dades de P1

> Disseny, no implementació. A partir dels FETS anteriors.

## Forma proposada de cada element "tasca de l'encàrrec" (dins el compositor)
Ordenats per `task_type__default_order, task_type__code` (clau canònica de P0, mateixa que el motor):

| camp | derivació | tipus |
|---|---|---|
| `id` | `ModelTask.id` | (a) directe |
| `task_type_code` | `task_type.code` | (a) directe |
| `task_type_name` | `task_type.name` | (a) directe |
| `default_order` | `task_type.default_order` | (a) directe — l'ordre canònic, per pintar esquerra→dreta |
| `status` | `ModelTask.status` | (a) directe (Pending/InProgress/Paused/Done) |
| `assignee_id` | `ModelTask.assignee_id` | (a) directe |
| `assignee_nom` | `assignee.nom_complet` (select_related) | (a) derivable **sense migració** |
| `temps_consumit_min` | `Sum(timers.minuts)` (== `_real_minutes`) | (a) derivable **sense migració** |
| `obertures` | `count(transitions, to_status='InProgress')` | (a) derivable **sense migració** |

**Cap camp requereix migració (cap (b)).** Tot és (a): camp directe o agregat/count ja existent.
`temps_consumit` i `obertures` són **derivables nets** (helpers/precedents vius: `_real_minutes`,
`rectification_count`, i l'agregació de l'albarà). → poden entrar a v1 sense risc d'esquema.

## Com servir-ho sense N+1 (nota d'eficiència, a validar a P1)
- `select_related('task_type', 'assignee')` cobreix code/name/default_order/assignee_nom.
- Per a `temps_consumit` i `obertures` evitar N+1 amb **annotate** al queryset:
  `annotate(temps=Sum('timers__minuts'), obertures=Count('transitions', filter=Q(transitions__to_status='InProgress')))`.
  ⚠️ Combinar dos agregats sobre relacions diferents en un sol `annotate` pot inflar files (join
  cartesià Timer×Transition) → **RISC tècnic a validar a P1**: si passa, fer-ho en dues passades
  (dos querysets agregats indexats per task_id, o `.distinct()`/subqueries). No és un risc d'esquema,
  sí de correcció de la query; P1 ha de verificar els números contra les dades reals d'aquest doc
  (162/tech_sheet=895min,7 obertures) abans de tancar.
- Ordre final: `order_by('task_type__default_order', 'task_type__code')` (canònic), **no** `ModelTask.order`.

## Encaix al compositor (additiu)
- Afegir una clau nova (p.ex. `pla_treball` o ampliar `tasques`) amb la forma de dalt; mantenir Q1/Q3
  intactes. P2 retira la `tasques` plana actual (D.3) quan el frontend del Pla de treball la cobreixi.
- Reordenar per `default_order` és un **canvi d'ordre percebut** respecte al kanban/llista actual (que
  usa `ModelTask.order`) — com ja advertia P0 §A; convé que l'Agus ho validi visualment (no és bug).

---

# Apèndix — fora d'scope detectat (anotat, no tocat)

- **Dos ordres coexistents** (ja anotat a P0): la llista plana del compositor ordena per
  `ModelTask.order` (inserció) mentre el canònic és `task_type.default_order`. P1 ha de passar al
  canònic; el deute de "quin ordre mana a cada lectura" segueix obert (kanban i llistes REST per
  defecte usen `order`, el motor usa `default_order`). No tocat.
- **`estimated_minutes` és snapshot congelat** (`tasks/models.py:213`; D-6 de la diagnosi Fase B):
  no s'actualitza per maduresa. Si el Pla de treball mostra estimació al costat del consumit, mostrarà
  el snapshot de creació, no una estimació viva. Decisió de producte, no tocat.
- **`TimerEntrada.minuts` truncat a minuts sencers** (`//60`, `services_c.py:29`): tasques de < 1 min
  compten 0 (model 182: 1 min amb 1 obertura és el cas límit). Anotat, no és bug de P1.

---

*Document de diagnosi. READ-ONLY respectat: l'únic fitxer escrit és aquest. Cap codi de producte,
migració ni config modificats. Totes les dades reals consultades dins `schema_context('fhort')`;
anclatges amb fitxer:línia verificats pel documentador.*
