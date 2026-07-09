# DIAGNOSI — Albarà v2 (safata per model · selecció per check) + lligam assignació↔planificació

Data: **2026-07-09** · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`.
Abast: terreny per al redisseny de l'albarà (composició per MODEL, selecció d'ítems per check,
DRAFT manual, estat INVOICED, exclusió de facturació) i per lligar l'assignació a comanda amb
la pestanya Pendents de Planificació. **Cap decisió es reobre** (context ja decidit pel CTO).

Convenció: cada afirmació sobre el codi porta `fitxer:línia`. **"NO EXISTEIX" = confirmat absent
al codi** (no especulat). Les propostes de disseny van marcades `💡 PROPOSTA (a validar)` —
les decisions són humanes (Patró C). Xifres de BD = query read-only real contra schema `fhort`
(tenant "FHORT Management"), executada el 2026-07-09.

---

## Resum executiu (director)

1. **La infraestructura de línia per a la v2 JA EXISTEIX a mitges.** `DeliveryNoteLine` ja pot
   apuntar per FK a `model_task`, `expense`, `adjustment`, `work_order` i `product`, amb un
   `line_kind` (TASK/EXTRA/DEDUCTION/EXPENSE/MANUAL) — `commerce/models.py:681-693`. El que NO
   existeix és la **safata** (llistar albaranables d'un client) ni la **composició per model**:
   avui l'albarà es genera passant `work_order_ids` explícits i itera WorkOrders sencers
   (`services.py:278-397`). La unitat actual és el **WorkOrder**, no el model ni la tasca.

2. **"Albaranat" avui es detecta a nivell de WorkOrder, no de tasca.** El marcador és
   `WorkOrder.delivery_note` (FK, `commerce/models.py:483`); **NO EXISTEIX** cap flag `invoiced`/
   `billed` a `ModelTask` (`tasks/models.py:61-95`). La v2 (selecció per tasca) haurà de mirar la
   relació inversa `model_task.delivery_note_lines` per saber si una tasca ja està en un albarà.

3. **La safata és de densitat BAIXA i el `codi_client` està gairebé buit.** Foto real de Brownie:
   **3 tasques albaranables** en 3 models, i les tres tenen `work_order = NULL` (no passen pel
   flux WO actual). Només **2 de 20 models** (10%) tenen `codi_client` informat de veritat.
   → **PDF vertical suficient**; el header de bloc no es pot recolzar en `codi_client` (§2).

4. **L'estat INVOICED NO EXISTEIX.** El cicle de l'albarà és només DRAFT→ISSUED
   (`commerce/models.py:625-629`). Cal afegir-lo (i el marcatge individual/massiu).

5. **El guard de reobertura té un únic choke-point net.** Totes les transicions passen per
   `transition_task` (`tasks/services_c.py:96`); injectar "no reobrir si té línia en albarà
   ISSUED" és 3 línies en un sol lloc, amb risc BAIX (§4).

6. **L'exclusió "no facturar mai" ja té precedent de casa per als extres** (`EXTRA_ABSORB`,
   `commerce/models.py:537`) i un camp **latent no consumit** (`TaskType.facturable`,
   `tasks/models.py:50`). Per tasques cal decidir entre flag, taula d'ajust o activar el latent (§5).

7. **El lligam assignació↔planificació és quasi tot reutilització.** El servei
   `assign_model_to_order_line` (`commerce/services.py:223`), l'endpoint `assign-model`
   (`commerce/views.py:208`) i el menú d'accions massives de Models (`ActionsMenu.jsx`) ja
   existeixen; falta la query "models actius sense encàrrec" (la pestanya Pendents avui NO mira
   comandes) i una acció "Assignar a comanda" al menú (§6, §7).

---

## BLOC 1 — LA SAFATA D'ALBARANABLES

### 1.1 · Model d'albarà (el que ja hi ha)

- **`DeliveryNote`** (`commerce/models.py:615`), subclasse d'`AbstractDocument`. `status` PROPI amb
  choices **DRAFT/ISSUED** (`:625-629`, default DRAFT). `issued_by` (`:630`). **NO EXISTEIX INVOICED**
  ni cap FK a factura (Settlement/B5 és TODO, `models_base.py:29`).
- **`DeliveryNoteLine`** (`commerce/models.py:666`): cada línia pot apuntar a **quatre orígens**
  (tots nullable) + product: `work_order` PROTECT (`:684`), `model_task` SET_NULL (`:687`),
  `expense` SET_NULL (`:689`), `adjustment` SET_NULL (`:691`), `product` PROTECT null (`:681`).
  `line_kind` ∈ TASK/EXTRA/DEDUCTION/EXPENSE/MANUAL (`:693`). Les DEDUCTION porten import negatiu.
- Edició bloquejada fora de DRAFT: `DeliveryNoteLine._assert_editable()` (`:700-703`), patró de
  segellat idèntic a `QuoteLine` (`:257-260`). Un albarà ISSUED no s'esborra (`:658-659`).

**Lectura v2:** l'esquema de línia ja suporta la selecció per check d'orígens heterogenis
(tasca/extra/expense/deducció). La v2 no necessita canviar `DeliveryNoteLine`; necessita una
capa de **safata** que reculli candidats i una composició **agrupada per model** (avui inexistent).

### 1.2 · Com es detecta "albaranat" avui

- **NO EXISTEIX** cap camp `delivery_note_line`/`invoiced`/`billed` a `ModelTask`
  (`tasks/models.py:61-95`, enumerat sencer).
- Marcador real = **`WorkOrder.delivery_note` IS NOT NULL** (`commerce/models.py:483`, comentari
  literal "marca 'aquest WO ja està albaranat'").
- La relació ítem→línia és **la línia qui apunta a l'ítem** (FKs concretes, **NO** GenericFK).
  Relació inversa des de la tasca: `task.delivery_note_lines` (related_name, `commerce/models.py:688`).
- Guard de doble inclusió a `generate_delivery_note`: rebutja qualsevol WO amb `delivery_note_id`
  no nul (`services.py:318-319`).

### 1.3 · Enumeració precisa d'"albaranable" (per tipus)

| Tipus | On viu | Condició d'albaranable avui (via WO) | Import |
|---|---|---|---|
| **Tasca** | `tasks.ModelTask` (`models.py:61`) | `status='Done'` + `off_recipe=False` + `wo.status='CLOSED'` + `wo.delivery_note IS NULL` (`services.py:359-360`) | preu de recepta |
| **Extra facturable** | `commerce.WorkOrderAdjustment` (`models.py:523`) | `kind='EXTRA_BILL'` (`services.py:371`) | `amount` (+) |
| **Extra absorbit** | id. | `kind='EXTRA_ABSORB'` → **mai genera línia** (`services.py:292,371`) | — |
| **Deducció** | id. | `kind='DEDUCTION'` → línia negativa (`services.py:377`) | `amount` (−) |
| **Expense** | `commerce.Expense` (`models.py:569`) | totes les del WO (`services.py:388`) | `sale_price × quantity` |

Tots tres conceptes comercials **pengen del WorkOrder** (no del customer/model directament); el
lligam a client/model és transitiu via `WorkOrder.customer`/`.model` (`commerce/models.py:467,469`).

**`facturable` a nivell instància = latent.** `TaskType.facturable` existeix (`tasks/models.py:50`)
però **no es llegeix enlloc** del pipeline d'albarà (només declarat). El filtre TASK actual no el
consulta (`services.py:359-360`).

### 1.4 · La safata com a query: **NO EXISTEIX**

No hi ha endpoint ni query dedicada que llisti "albaranables d'un client". `WorkOrderViewSet`
(`views.py:229-236`) filtra per `kind/status/customer/period` però **no** exposa
`delivery_note__isnull`. El flux actual és invers: el frontend tria `work_order_ids` i els passa a
`generate` (`views.py:308-327`). Confirmat absent a `views.py`/`services.py`/`urls.py`/`serializers.py`.

### 1.5 · FOTO DE DENSITAT REAL — Brownie (schema `fhort`, 2026-07-09)

Customer = `BRW · Textiles y Confecciones Brownie SL` (id=7). **18 models**, **1 sol WorkOrder**.

```
WorkOrders de Brownie:  WO-13  kind=COLLECTOR  model=None  status=CLOSED  delivery_note=5 (ISSUED)
Albarans de Brownie:    DN-5   ISSUED   2 línies (kind=TASK, tasks 256+272, totes del model 188)
ModelTask Done facturables (models Brownie):  5 total
  · ja en albarà ISSUED:  2   (les de DN-5)
  · ALBARANABLES (Done facturable, cap DeliveryNoteLine):  3
```

| model | codi_intern | nom | tasques albaranables | task_type | work_order |
|---|---|---|---|---|---|
| 162 | BRW-SS26-0001 | OLIVIA DRESS | 1 | size_check | **NULL** |
| 169 | BRW-FW26-0007 | Top AMELIA | 1 | pom | **NULL** |
| 182 | BRW-26-SS-0002 | [QA-SC] OLIVIA DRESS | 1 | size_check | **NULL** |

Extres (WorkOrderAdjustment) de Brownie: **0**. Expenses: **0**.

**Troballes de densitat que decideixen el layout:**
- La safata real ARA són **3 tasques soltes en 3 models** (densitat baixíssima). El **PDF vertical
  n'hi ha prou**; no cal horitzontal.
- ⚠️ **Les 3 tasques albaranables tenen `work_order = NULL`** → **el flux v1 (per WorkOrder) NO les
  pot albaranar**. Aquesta és exactament la bretxa que la v2 (composició per model, selecció per
  check de tasques) resol: hi ha feina facturable que avui és inaccessible perquè no penja de cap WO.
- ⚠️ El precedent històric (DN-5) demostra la pèrdua d'identitat de model del flux actual: WO-13 és
  un **COLLECTOR amb `model=None`** que va agrupar tasques del model 188; l'albarà no sap "de quin
  model" és cada línia si no mira `model_task.model_id`. La safata per model és el remei directe.

> **Veredicte BLOC 1:** *cal construir la safata i la composició per model.* La capa de dades
> (`DeliveryNoteLine` multi-origen) és llesta; el que falta és (a) una query de candidats per
> client agrupada per model que inclogui **tasques Done facturables sense línia d'albarà**
> —incloent-hi les de `work_order=NULL`— i extres/expenses/deduccions; (b) canviar la detecció
> d'"albaranat" de nivell-WO a nivell-línia (`model_task.delivery_note_lines`). Densitat real
> baixa → PDF vertical.

💡 **PROPOSTA (a validar) — safata v2 per model, orientada a línia (no a WO):**
```python
# Tasques albaranables d'un client, agrupades per model (independent de si tenen WO):
ModelTask.objects.filter(
    model__customer_id=CID, status='Done', task_type__facturable=True,
    delivery_note_lines__isnull=True,          # cap línia d'albarà encara
).values('model_id','model__codi_intern','model__nom_prenda').annotate(n=Count('id'))
# + WorkOrderAdjustment (EXTRA_BILL/DEDUCTION) i Expense filtrats per client i delivery_note_lines__isnull=True
```
(Nota: canviar `delivery_note_lines__isnull=True` per `...__delivery_note__status='ISSUED'` si es
vol que un ítem en DRAFT no torni a la safata però un DRAFT esborrat sí — decisió de producte.)

---

## BLOC 2+3 — CAMPS DE CAPÇALERA DE BLOC-MODEL (la "ref client" del PDF)

Model principal: `models_app.models.Model`. Camps exactes per al header de cada bloc-model:

| Concepte | Camp | Definició | fitxer:línia | Editable a |
|---|---|---|---|---|
| **Ref interna** | `codi_intern` | CharField(40) unique, read-only API | `models.py:117` · `serializers.py:114` | (auto, no editable) |
| **Codi client** (ref client) | `codi_client` | CharField(80) blank default='' | `models.py:120` | ModelWizard.jsx:281 · ModelSheet.jsx:935 |
| **Nom** | `nom_prenda` | CharField(200) | `models.py:140` | wizard/sheet |
| **Col·lecció** | `collection` | **EXISTEIX** · CharField(120) **text lliure** (NO FK) | `models.py:144` | ModelWizard.jsx:281 · ModelSheet.jsx:877 |
| **Any** | `any` | PositiveSmallInt (obligatori) | `models.py:136` | wizard |
| **Temporada** | `temporada` | CharField(4) choices SS/FW/CO/SP | `models.py:137` (`:76-81`) | wizard |
| Client | `customer` | FK tasks.Customer PROTECT (font del prefix de codi_intern) | `models.py:125` | — |
| Grup peça | `garment_group` | FK pom.GarmentGroup SET_NULL | `models.py:153` | — |
| Versió | `versio` | CharField(20) null | `models.py:254` | — |

⚠️ **Matís crític del `codi_client`** (afecta el disseny del header): quan és buit, el flux l'omple
amb `codi_intern` com a fallback (`ModelSheet.jsx:821`). Per això la UI el mostra **només si**
`codi_client && codi_client !== codi_intern` (`ModelSheet.jsx:669,778,976`). "Informat de veritat"
= no buit **i** diferent de `codi_intern`.

**Cobertura real (schema `fhort`, 2026-07-09):**
```
codi_client informat de veritat:  2 / 20 models  (10%)
collection informada:            15 / 20 models  (75%)
```

> **Veredicte BLOC 2+3:** *camps disponibles i confirmats.* `collection` **existeix** (text lliure,
> 75% informat) i serveix per agrupar. Però **`codi_client` només cobreix el 10%**: el header del
> bloc-model del PDF ha de tenir fallback net a `codi_intern` i **no pot presentar-se com a "ref
> del client" fiable**. 💡 PROPOSTA: header de bloc = `codi_intern` sempre + `codi_client` només si
> difereix (mateixa regla que la UI); nom + `collection`+`temporada`+`any` com a subtítol.

---

## BLOC 4 — GUARD DE REOBERTURA (Done→InProgress)

- **Estructura ALLOWED** (`tasks/services_c.py:11-16`):
  ```python
  ALLOWED = {'Pending':{'InProgress'}, 'Paused':{'InProgress'},
             'InProgress':{'Paused','Done'}, 'Done':{'InProgress'}}  # Done→InProgress = rectificació
  ```
- **Funció única** que valida i aplica: `transition_task(task, to_status, profile)`
  (`services_c.py:96`, `@transaction.atomic`). Validació a `:101`; reset de `finished_at` en reobrir
  a `:121-123`. No hi ha `change_status`/`set_status` alternatius.
- **5 call-sites** de `transition_task` (grep backend, exclòs `_legacy_archive`):
  1. `tasks/views_b.py:448` — endpoint genèric `POST /model-task-items/<pk>/transition/` (única
     reobertura d'usuari amb `to_status` lliure).
  2. `tasks/views_b.py:552` — claim/quick (força InProgress).
  3. `models_app/services_size_check.py:221-222` — InProgress→Done intern.
  4. `models_app/views.py:671,673` — tancament taula POM.
  5. `tasks/management/commands/retype_scaling_to_grading.py:64-65` — command de migració.
- **Condició per saber si la tasca ja està albaranada** (relació inversa):
  `task.delivery_note_lines.filter(delivery_note__status='ISSUED').exists()`.
- **Patró de guard replicable** ja consolidat: `_assert_editable()` (bloqueja si estat != DRAFT) a
  `DeliveryNoteLine` (`commerce/models.py:700-703`) i `QuoteLine` (`:257-260`). Però **al món tasques
  NO EXISTEIX cap guard que impedeixi reobrir per estar albaranada** — la transició Done→InProgress
  està oberta sense condició més enllà d'ALLOWED.

> **Veredicte BLOC 4:** *choke-point net, risc BAIX.* Injectar el guard dins `transition_task`
> després de la validació ALLOWED, limitat estrictament a `frm=='Done' and to=='InProgress'`,
> cobreix els 5 call-sites sense tocar cap view (reutilitza `TransitionError`→400 ja existent a
> `views_b.py:449`). Únic vector de regressió: les rutines internes (3)(4)(5) si mai reprocessen una
> tasca ja albaranada. 💡 PROPOSTA (dimensionament, NO implementar):
> ```python
> if frm == 'Done' and to_status == 'InProgress':
>     if task.delivery_note_lines.filter(delivery_note__status='ISSUED').exists():
>         raise TransitionError('No es pot reobrir una tasca ja albaranada (albarà emès).')
> ```
> Si es vol immunitzar les rutines internes: afegir `force=False` a la signatura i passar-lo
> explícit als 3 call-sites tècnics (cost: +1 kwarg, 3 edicions). Encaixa amb la decisió ja presa
> ("rectificació = extra nova que genera línia al proper albarà encara que sigui a 0").

---

## BLOC 5 — ON ANCORAR "NO FACTURAR MAI" (excloure de facturació)

- `ModelTask` **NO té** cap camp de facturació/exclusió (`tasks/models.py:61-95`). Flags binaris
  existents: `off_recipe` (`:95`), `planned_locked` (`:86`). Estat d'execució: `status`
  Pending/Paused/InProgress/Done (`:63-64`).
- **Patró de casa (tres modismes):**
  - (a) **BooleanField al model** — `off_recipe` (`tasks/models.py:95`), `base_tancada` +
    `data_tancament_base` (`fitting/models.py:48-49`).
  - (b) **Choices de `status`/`estat`** (cicle de vida) — `SizeFitting` estat terminal `'Tancat'`
    (`fitting/models.py:15-21`), `WorkOrder` OPEN/CLOSED + `closed_at/by` (`commerce/models.py:460`).
  - (c) **Taula pròpia amb auditoria** — `Watchpoint` open/resolved (`models_app/models.py:840-870`);
    **`WorkOrderAdjustment`** amb `resolved_by/at` (`commerce/models.py:549-551`).
- **El cas bessó ja resolt:** els extres tenen "no facturar" via `kind='EXTRA_ABSORB'`
  (`commerce/models.py:537`), que **mai genera línia** (`services.py:371`, comentari `:292`). O sigui,
  la casa ja modela "no facturar un extra" com a **fila d'Adjustment**, no com a flag a la tasca.
- **Expenses NO tenen** camp d'exclusió; l'única via avui és `sale_price=0` (línia a 0, no exclosa).
- Punts on una exclusió s'ha de respectar: filtre TASK (`services.py:359-360`), gate d'extres
  (`services.py:321-330`), detecció de pendents al tancament (`services.py:194`), i qualsevol
  superfície de "pendents de facturar".

> **Veredicte BLOC 5:** *no usar `status` (via B descartada — barreja eix execució i eix
> facturació i trenca les queries de cicle de vida i el log `TaskTransition`).* Dues vies vives:

💡 **PROPOSTA (a validar) — comparativa:**
| Via | Descripció | A favor | En contra |
|---|---|---|---|
| **A** | `BooleanField exclude_from_billing` a `ModelTask` | mínim codi; patró (a) de casa; ortogonal a status; 1 `.exclude()` als 2-3 filtres | sense auditoria (qui/quan/per què); deixa Expenses fora |
| **C** | fila a `WorkOrderAdjustment` amb `kind` nou (`TASK_NOBILL`) | **patró que la casa JA aplica al cas idèntic** (EXTRA_ABSORB); auditoria de sèrie; el gate d'extres ja tracta una tasca amb Adjustment com "resolta"; unifica | depèn que la tasca visqui sota un WO (les 3 albaranables de Brownie tenen `work_order=NULL` → no tindrien on ancorar) |
| ~~B~~ | nou valor de `status` | — | **anti-patró**, descartada |

> Observació transversal (fora d'scope, anotada): activar el camp latent `TaskType.facturable`
> (`tasks/models.py:50`) al filtre de `generate_delivery_note` cobriria "certs TIPUS mai es
> facturen" (regla estructural), complementari a A/C (decisió per-instància). ⚠️ Tensió amb la
> foto de Brownie: si s'activa, les tasques `size_check`/`pom` desapareixerien de la safata segons
> el `facturable` del seu TaskType — cal verificar-ne el valor abans d'activar-lo.

---

## BLOC 6 — PLANIFICACIÓ "Pendents": què llista avui

- **NO EXISTEIX endpoint dedicat.** La pestanya es calcula 100% al client des de l'agregador genèric
  `by-model` de l'app **tasks**: `@action url_path='by-model'` a `ModelTaskViewSet`
  (`tasks/views_b.py:78`). Query: agrupa `ModelTask` per model i compta per estat
  (`views_b.py:175-181`). Per defecte només models amb ≥1 tasca no-Done (`:196-198`).
- ⚠️ `by-model` **parteix de files `ModelTask`**: un model **sense cap ModelTask no hi apareix mai**,
  ni amb `?all=true`.
- Frontend: `Planning.jsx:482` → `<PlanificacioPanel mode="pending" />`. Crida `by-model?all=true`
  + `model-task-items` + users (`:124-127`); classifica client-side: descarta models sense tasca
  no-Done (`:140`), i `folder = techIds.length ? 'assigned' : 'pending'` (`:152`).
- **Definició real d'avui** (comentari `Planning.jsx:23`): *"Pendents = models que TENEN ≥1 tasca
  no-Done PERÒ cap amb tècnic assignat."* **No té res a veure amb comandes.**
- Cadena comercial: `SalesOrder` (`commerce/models.py:281`) → `SalesOrderLine` (`:328`). **No hi ha
  FK directa Model→OrderLine**; el lligam és via `WorkOrder` (`.model` `:469` + `.order_line` `:472`
  + `.kind` ORDER/COLLECTOR `:475`). **"Model amb encàrrec" = té `WorkOrder(kind='ORDER')`** (el
  guard del servei usa `status='OPEN'`, `services.py:243`).
- "Model actiu" = `Model.estat != 'Tancat'` (choices Nou/EnCurs/EnRevisio/Tancat,
  `models_app/models.py:83-91,201`). No hi ha booleà `is_active` al Model.

> **Veredicte BLOC 6:** *la pestanya Pendents actual respon a una pregunta diferent* (models amb
> feina no assignada a un tècnic), **no** "models sense encàrrec/comanda". Per llistar aquests
> últims cal una **query nova** (no derivable de `by-model`, que ignora models sense tasques).

💡 **PROPOSTA (a validar) — "models actius sense encàrrec", amb acció d'assignar:**
```python
amb_encarrec = WorkOrder.objects.filter(kind='ORDER', status='OPEN').values_list('model_id', flat=True)
pendents_de_comanda = Model.objects.exclude(estat='Tancat').exclude(pk__in=amb_encarrec)
```
Reutilitza el mateix criteri del guard `assign_model_to_order_line` (`services.py:243`) per
coherència. Decisió de producte: si aquesta llista viu com a **sub-pestanya nova** de Planificació
o com a **filtre a la pàgina Models** (que ja té la selecció i el menú d'accions del BLOC 7).

---

## BLOC 7 — ASSIGNACIÓ BULK des de Models

- **Selecció múltiple i menú d'accions JA existeixen** a `Models.jsx`: `selected` Set (`:26`),
  `selectedModels` (`:50`), "seleccionar tot" (`:106`), i `<ActionsMenu targets={selectedModels}>`
  (`:80`). El menú viu a `components/model/ActionsMenu.jsx`, array `items` (`:176-184`): accions
  actuals `assign`(tasques)/`production`/`fitting`/`convene_fitting`/`advance`/`back`.
- **Patró per afegir acció nova** (clar): entrada a `items` + bloc `{modal==='key' && <Modal>}` +
  handler via `runBulk(perModel)` (`ActionsMenu.jsx:74-85`), helper que **ja itera model per model**
  amb feedback agregat "X fet · Y omesos" i recull errors 400 per-model.
- **Servei B4b:** `assign_model_to_order_line(model, order_line, user)` (`commerce/services.py:223`).
  **Un a un** (NO llista). Guards durs: comanda OPEN (`:237`), mateix client model↔comanda (`:239`),
  línia no plena `qty_allocated < quantity` (`:241`), model sense `WorkOrder(ORDER,OPEN)` actiu
  (`:243`). Crea el WO ORDER amb snapshots (`:253-258`), imputa `+1` a `qty_allocated` (`:261`),
  **migra les tasques del COLLECTOR** al nou ORDER (`:267-273`). Ja porta un `TODO B4c: excloure les
  tasques albaranades` a la migració (`services.py:275`-zona).
- **Endpoint ja exposat:** `POST /api/v1/commerce/order-lines/{id}/assign-model/` — `@action
  detail=True 'assign-model'` a `SalesOrderLineViewSet` (`commerce/views.py:208`), body `{model_id}`,
  gate CONFIGURE, tradueix ValidationError→400. Frontend ja cablejat:
  `commerce.orderLines.assignModel(id, {model_id})` (`endpoints.js:~409`).

> **Veredicte BLOC 7:** *quasi tot reutilització; zero backend nou.* Una sola línia amb `quantity=N`
> pot absorbir N models (una crida per model, cada crida imputa +1). El helper `runBulk` encaixa
> exactament amb el patró un-a-un del servei.

💡 **PROPOSTA (a validar) — "Assignar a comanda" al menú massiu:**
1. Entrada a `items` (`ActionsMenu.jsx:176`): `{key:'assign_order', label:t('...'), icon:'ti-clipboard-list', enabled:list.length>0}` (+ claus i18n ca/en/es per l'i18n-gate).
2. Modal nou amb selector **client → comanda OPEN → línia amb quantitat lliure**. ⚠️ Com que
   `assign_model_to_order_line` exigeix mateix client (`services.py:239`) i la selecció pot barrejar
   clients, el modal ha d'agrupar per `customer_id` o exigir un sol client (warning si no). Poblar
   amb `commerce.orders.list({customer,status:'OPEN'})` + `commerce.orderLines.list({order})` (ja existents).
3. Execució: `runBulk(m => commerce.orderLines.assignModel(form.line_id, {model_id:m.id}))`. Els
   guards del servei (model ja amb ORDER, línia plena, client diferent) cauen a "omesos" via el 400.
4. Codi nou net: 1 entrada `items` + 1 `<Modal>` (3 selects) + 1 handler + 3 claus i18n. **Cap
   migració, cap servei, cap endpoint nou.**

---

## TAULA FINAL DE RISCOS (per al CTO)

| # | Àrea | Estat | Risc / Bretxa | Sever. |
|---|---|---|---|---|
| R1 | Composició per model | **FALTA** | L'albarà v1 itera WorkOrders sencers (`services.py:278`); no hi ha agrupació per model ni safata. Cal construir-ho sobre `DeliveryNoteLine` (que ja és multi-origen). | **Alta** |
| R2 | Tasques albaranables sense WO | **BRETXA CONFIRMADA** | Les 3 tasques albaranables de Brownie tenen `work_order=NULL`: **inaccessibles al flux v1**. La safata v2 ha de partir de `ModelTask`, no de WO. | **Alta** |
| R3 | Estat INVOICED | **NO EXISTEIX** | Cicle només DRAFT/ISSUED (`models.py:625`). Cal afegir INVOICED + marcatge individual/massiu. | Mitjana |
| R4 | Detecció "albaranat" | **CANVI DE NIVELL** | Avui a nivell WO (`WorkOrder.delivery_note`, `models.py:483`); la v2 (per tasca) ha d'usar `model_task.delivery_note_lines`. Coexistència dels dos criteris durant la transició. | Mitjana |
| R5 | `codi_client` al header PDF | **DADES ESCASSES** | Només 10% (2/20) informat de veritat. Header no pot dependre'n; fallback a `codi_intern`. | Mitjana |
| R6 | Guard reobertura | **A INJECTAR** | 1 choke-point (`transition_task`, `services_c.py:96`); risc BAIX si es limita a Done→InProgress; vigilar rutines internes (3)(4)(5). | Baixa |
| R7 | Exclusió "no facturar" | **DECISIÓ OBERTA** | Via A (flag) vs C (Adjustment). ⚠️ Via C no ancora tasques amb `work_order=NULL` (cas real Brownie). `TaskType.facturable` és latent. | Mitjana |
| R8 | Pestanya Pendents | **RESPON ALTRA PREGUNTA** | Avui = "tasques no assignades a tècnic" (`Planning.jsx:23`), no "sense comanda"; i ignora models sense cap ModelTask (`views_b.py:196`). Cal query nova. | Mitjana |
| R9 | Bulk assign | **REUTILITZABLE** | Servei/endpoint/menú ja existeixen; només acció nova + modal. Vigilar selecció multi-client (`services.py:239`). | Baixa |
| R10 | Densitat/PDF | **FAVORABLE** | Safata real baixíssima (3 ítems); PDF vertical suficient, no horitzontal. | Baixa |

---

*Fi de la diagnosi. Read-only estricte respectat (única escriptura: aquest document). Equip: 1
director + 5 investigadors-codi en paral·lel + documentador, orquestrats en una sessió. Queries de
BD read-only executades pel documentador contra schema `fhort`. Les decisions són humanes (Patró C).*
