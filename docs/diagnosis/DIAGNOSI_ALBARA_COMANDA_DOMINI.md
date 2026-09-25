# DIAGNOSI · DOMINI COMERCIAL: oferta → comanda → model → rondes → tasques → albarà

**Patró A · READ-ONLY.** Cap escriptura, cap fix aplicat. Protocol PROTOCOL_FASE_B.
**Data:** 2026-09-09 · **Codi:** `/var/www/ftt-staging`, branca `dev`, **HEAD `935991db`** (03/09,
ja al dia amb `origin/dev`: `git rev-list HEAD..origin/dev` = 0, cap pull necessari).
**Dades:** `ftt_staging` (cluster `postgresql@18-main`, port **5433**), schema **`fhort`**, totes les
consultes amb `PGOPTIONS='-c default_transaction_read_only=on'`.

> ⚠️ **No existeix cap BD de producció en aquesta màquina.** `pg_lsclusters` dona dos clústers (16
> `down`, 18 `online`) i al 18 les úniques bases són `ftt_staging`, `ftt_assaig_v5` i bases `test_*`.
> El tenant `fhort` d'`ftt_staging` **SÍ que conté** el client Brownie, la comanda `SO-2026-0001` i
> l'albarà `DN-2026-0001` que el brief nomena, o sigui que és la població que s'ha mesurat aquí.
> Tot número d'aquest document surt d'aquesta base.

---

## 0 · RESUM EXECUTIU — les cinc coses que decideixen l'encaix

| # | Fet mesurat | Conseqüència per a la decisió d'Agus |
|---|---|---|
| **F1** | **L'albaranable d'avui és la TASCA, no el model ni la ronda.** `get_billable_items` itera `ModelTask` (`commerce/services.py:779`) i crea **una línia per tasca**. | El canvi demanat (albaranable = model + rondes) **no és un filtre nou sobre la safata: és un altre eix d'agregació**. La ronda ja hi viatja (`_ronda_header`), però com a *etiqueta* de la tasca, no com a unitat. |
| **F2** | **El preu es multiplica per tasca.** Cada tasca proposa `wo.price_snapshot['unit_price']` sencer (`commerce/services.py:788`). Mesurat: el model `QA-M4-0001` proposa **360,00 €** (3 tasques × 120) contra una línia de comanda de **120 €/u amb `qty_allocated=1`**. | És exactament el fil trencat que el brief descriu. El preu ja *ve* de la línia de comanda, però **sense divisor**: ningú no sap que aquelles 3 tasques són 1 unitat venuda. |
| **F3** | **`rounds_included` ja existeix i el desbordament ja es resol i es desa** (`SalesOrderLine.rounds_included`, `Ronda.fora_de_comanda`/`linia_comanda`/`numeral_vigent`). | Q1 ⚑ tancat: **no cal cap camp nou** per a "voltes incl." ni per a "ronda extra". El que falta és **on es llegeix**, no on es guarda. |
| **F4** | **Els dos verds de la safata ja existeixen** (`Entrega` = ronda entregada; `Entrega.data_ok` = vist-i-plau client) **però el segon no s'ha informat mai**: 22 rondes, 3 entregues, **0 `data_ok`**. | La safata amb 2 verds, avui, tornaria **zero files**. Cal decidir si el vist-i-plau és requisit dur o segon semàfor informatiu. |
| **F5** | **El cost intern està construït i és MUT**: `internal_cost` = `internal_minutes` ÷ 60 × `TenantConfig.hourly_rate`, i `hourly_rate` **és NULL** (i els 7 `UserProfile.cost_hora` són **0,00**). | Q6: **no cal crear el camp**, cal decidir on és **editable** (avui viu a `TenantConfig`, gate `CONFIGURE`, tarifa plana d'empresa — no a l'albarà). |

---

## Q1 · MODEL DE DADES

### 1.1 Diagrama de relacions (fitxer:línia de cada FK)

```
                     ┌──────────────────────────────┐
                     │ tasks.Customer               │
                     └──────────────┬───────────────┘
                                    │ (PROTECT, a tots els documents)
  ┌─────────────────────────────────┼──────────────────────────────────┐
  │                                 │                                  │
┌─▼──────────────┐ 1:1        ┌─────▼──────────┐               ┌───────▼────────┐
│ Quote (OF)     │ source_    │ SalesOrder(SO) │               │ DeliveryNote   │
│ models.py:216  │◄──quote────│ models.py:322  │               │ (DN) :689      │
│ AbstractDoc    │  :344      │ AbstractDoc    │               │ AbstractDoc    │
└─┬──────────────┘            └─┬──────────────┘               └─┬──────────────┘
  │ lines (CASCADE)             │ lines (CASCADE)                 │ lines(CASCADE)
┌─▼──────────────┐            ┌─▼──────────────────────────┐    ┌─▼──────────────┐
│ QuoteLine :255 │            │ SalesOrderLine :369        │    │ DeliveryNote   │
│  product FK    │            │  product · quantity        │    │ Line :748      │
│  quantity      │            │  unit_price · line_total   │    │  line_kind     │
│  unit_price ⓕ  │            │  qty_allocated             │    │  unit_price ✎  │
│  line_total    │            │  ★ rounds_included :406    │    │  quantity      │
└─┬──────────────┘            └─┬────────────┬─────────────┘    │  visible       │
  │ model_intents               │ work_orders│ rondes           │  internal_min. │
┌─▼──────────────────┐          │ (PROTECT)  │ (SET_NULL)       └─┬────┬───┬─────┘
│ QuoteLineModel     │          │            │                    │    │   │
│ Intent :284        │  ┌───────▼──────────┐ │        work_order  │    │   │ model
│  quote_line·model  │  │ WorkOrder (WO)   │◄┼────────(PROTECT)───┘    │   │(SET_NULL)
│  qty · INFORMATIU  │  │ models.py:505    │ │                         │   │
└────────┬───────────┘  │  kind ORDER|COLL │ │      model_task         │   │
         │ model        │  order_line :537 │ │      (SET_NULL) ────────┘   │
         │ (CASCADE)    │  orphaned_from_  │ │                             │
         │              │    line :545     │ │      adjustment ────┐       │
  ┌──────▼─────────┐    │  price_snapshot  │ │      (SET_NULL)     │       │
  │ models_app.    │    │  recipe_snapshot │ │      expense ───┐   │       │
  │ Model          │◄───┤  model :535      │ │      (SET_NULL) │   │       │
  │                │    │  delivery_note   │ │                 │   │       │
  └───┬────────┬───┘    │    :551 SET_NULL │ │  ┌──────────────▼─┐ │       │
      │        │        └─┬─────────┬──────┘ │  │ Expense :643   │ │       │
      │ rondes │ model_    │ tasks   │ adjust.│  │  cost_price    │ │       │
      │(CASCADE)│ tasks    │(SET_NULL)│(CASCADE)│  │  sale_price    │ │       │
  ┌───▼────────▼──┐      │         │        │  └────────────────┘ │       │
  │ tasks.Ronda   │      │  ┌──────▼──────┐ │  ┌──────────────────▼─┐     │
  │ models.py:133 │      │  │ WorkOrder   │ │  │ (l'ajust és el que  │     │
  │  seq · motiu  │      │  │ Adjustment  │ │  │  l'albarà llegeix)  │     │
  │  oberta_el    │      │  │ :597 kind:  │ │  └────────────────────┘     │
  │  tancada_el   │      │  │ EXTRA_BILL  │ │                             │
  │ ★fora_de_     │      │  │ EXTRA_ABSORB│ │                             │
  │   comanda:196 │      │  │ DEDUCTION   │ │                             │
  │ ★linia_comanda│──────┘  │  amount     │ │                             │
  │   :207 SET_NULL│        └──────┬──────┘ │                             │
  │ ★numeral_vigent│               │ model_ │                             │
  │   :212        │               │ task   │                             │
  └───┬───────────┘               │(SET_NULL)                            │
      │ tasques (SET_NULL)  ┌─────▼──────────────────┐                   │
      │                     │ tasks.ModelTask :291   │───────────────────┘
      │  ┌──────────────────►  model (CASCADE)       │
      │  │ 1:1 entrega      │  task_type · status    │
  ┌───▼──▼────────┐         │  ronda :344 SET_NULL   │
  │ tasks.Entrega │         │  mare · motiu · origen │
  │ models.py:230 │         │  work_order :331 ⚠SET_NULL
  │  data         │         │  off_recipe            │
  │  destinatari  │         └────────┬───────────────┘
  │  descripcio   │                  │ timers
  │ ★data_ok      │         ┌────────▼───────────────┐
  │ ★qui_informa_ok│        │ TimerEntrada :5        │
  └───────────────┘         │  minuts · tecnic       │
                            └────────────────────────┘

 ⓕ = preu congelat (còpia, mai FK viva)   ✎ = editable pel comercial en DRAFT
 ★ = camp que el brief d'Agus necessita   ⚠ = la FK que trenca la cadena tasca→comanda
```

### 1.2 Camps que decideixen (transcrits)

**`SalesOrderLine`** — `backend/fhort/commerce/models.py:369-418`
```python
order          = FK(SalesOrder, CASCADE, related_name='lines')     # :372
product        = FK(Product, PROTECT)          # de l'abstracta, models_base.py:75
description    = CharField(300, blank)         # override lliure         models_base.py:78
quantity       = Decimal(12,2) default=1       #                         models_base.py:80
unit_price     = Decimal(12,2) default=0       # CONGELAT en crear       models_base.py:81
line_total     = Decimal(12,2)                 # quantity × unit_price   models_base.py:83
position       = PositiveInteger                                       # models_base.py:85
qty_allocated  = Decimal(12,2) default=0       # imputació de cartera    :373
rounds_included= PositiveInteger(null,blank)   # ★ VOLTES INCL.          :406
```
⚑ **"Voltes incl." viu a `SalesOrderLine.rounds_included` i només allà.** El comentari de
`models.py:376-405` ho declara explícitament ("el numeral viu a la comanda, mai al producte") i
n'estableix la semàntica de tres estats, que **no és intercanviable**:

| valor | significat | efecte |
|---|---|---|
| `NULL` | **sense límit** — el pacte no en fixa cap | cap volta desborda mai |
| `0` | **cap volta inclosa** | ja desborda la R1 |
| `n` | n voltes cobertes pel preu | desborda la R(n+1) |

És a més l'**única excepció declarada a la irreversibilitat de B3b**: la resta de la línia és
read-only per API, aquest camp és editable (`OrderDetail.jsx:117`, `commerce.orderLines.update`).

**`Ronda`** — `backend/fhort/tasks/models.py:133-231`
```python
model           = FK(models_app.Model, CASCADE, related_name='rondes')  # :177
seq             = PositiveInteger            # número de volta DINS del model, comença a 1  :179
motiu           = 'nova_mostra' | 'correccio'                                            # :181
oberta_el       = DateTime(auto_now_add)  /  tancada_el = DateTime(null)  # null = oberta :182-184
fora_de_comanda = Boolean(default=False)     # ★ FIT-12                                  :196
linia_comanda   = FK(SalesOrderLine, SET_NULL, null)   # ★ la línia que governava        :207
numeral_vigent  = PositiveInteger(null)      # ★ FOTO del numeral en obrir               :212
Meta.constraints: UniqueConstraint(['model','seq'], 'uniq_ronda_model_seq')              # :221
```

**`ModelTask`** — `tasks/models.py:291-364`: `model` (CASCADE), `task_type`, `status`
(`Pending|Paused|InProgress|Done`), `origen` (`prevista|ad_hoc`), `work_order` (**SET_NULL**,
`:331`), `off_recipe`, `ronda` (SET_NULL, `:344`), `mare`, `motiu`.

**`DeliveryNoteLine`** — `commerce/models.py:748-812`: `line_kind`
(`TASK|EXTRA|DEDUCTION|EXPENSE|MANUAL`), `unit_price`/`quantity`/`line_total`, i **cinc FK de
traçabilitat, totes nullable**: `work_order` (PROTECT), `model_task` (SET_NULL), `expense`,
`adjustment`, `model` (SET_NULL, v2, `:790`). Més `internal_minutes` (`:781`) i `visible` (`:786`).

### 1.3 ⚑ Com es calcularia "rondes fetes" — i què existeix ja

**No hi ha ni un sol comptador agregat de rondes al codi** (grep de `rondes_fetes` / `rondes.count`:
zero encerts fora de tests). El proxy és **`Ronda.seq`**: la unique `(model, seq)` i el fet que `seq`
comenci a 1 i s'incrementi a `obrir_ronda` fan que **la ronda N-èsima tingui `seq = N`**.

I **el càlcul de la ronda extra JA EXISTEIX**, resolt una sola vegada en obrir la volta:

```python
# backend/fhort/tasks/services_r.py:107-122
def resol_desbordament(ronda):
    linia, numeral = numeral_efectiu(ronda.model)
    ronda.linia_comanda  = linia
    ronda.numeral_vigent = numeral
    ronda.fora_de_comanda = numeral is not None and ronda.seq > numeral
    ronda.save(update_fields=['linia_comanda','numeral_vigent','fora_de_comanda'])
```
amb `numeral_efectiu` (`:88`) → `linia_de_comanda` (`:54`), que **resol model→línia pel pivot
`WorkOrder`** (no hi ha FK directa model→comanda): WO `kind='ORDER'` amb `order_line` no nul,
excloent comandes `CANCELLED`; mana l'OPEN, si no el més recent.

🔒 **És una FOTO i no es recalcula** (`models.py:186-195`): pujar el numeral de 2 a 3 **no** torna
endins les voltes ja obertes. Conseqüència declarada al codi: repescar-ne una és avui un acte a mà.

**Població mesurada** (`fhort`, 2026-09-09):

| | |
|---|---|
| `SalesOrderLine` amb `rounds_included` no nul | **1 de 4** (línia 15, banc `[QA-M4]`, valor 2) |
| `Ronda` amb `linia_comanda` | **3 de 22** (totes del model 1497) |
| `Ronda` amb `fora_de_comanda = true` | **1 de 22** (model 1497, R3, numeral 2) |
| `SO-2026-0001` (Brownie) | 2 línies, `rounds_included` **NULL** a totes dues, `qty_allocated` **0,00** a totes dues |

> **`SO-2026-0001` no té cap model assignat** (`qty_allocated=0`) i està `COMPLETED`. L'únic
> WorkOrder `ORDER` de tot el tenant és el del banc de QA. Vegeu Q2.

---

## Q2 · COM ES CONSTRUEIX L'ALBARÀ AVUI — **aquí és on el fil es trenca**

### 2.1 Hi ha DOS camins vius, no un

| | **v1 · `generate_delivery_note`** | **v2 · safata + `add_lines_to_draft`** |
|---|---|---|
| codi | `commerce/services.py:527-651` | `:734-853` (safata) + `:868-946` (afegir) |
| entrada | **llista de `WorkOrder` CLOSED** | **un `Customer`** |
| API | `POST delivery-notes/generate/` (`views.py:604`) | `GET delivery-notes/billable/?customer=` (`views.py:591`) + `POST {id}/add-lines/` (`:638`) |
| pantalla | modal "generar albarà" a `WorkOrderDetail.jsx:391` | safata a `DeliveryNoteDetail.jsx:466-481` |
| unitat | el **WO sencer** | la **tasca solta** (check per ítem) |

Tots dos segueixen operatius. El v2 és el que el brief descriu ("a la pantalla surten tasques amb
preu").

### 2.2 D'on surten les línies: **de `ModelTask`, no de la comanda**

```python
# backend/fhort/commerce/services.py:779-782  ← EL CODI QUE DECIDEIX QUÈ ÉS ALBARANABLE
for t in (ModelTask.objects
          .filter(model__customer=customer, status='Done',
                  delivery_note_lines__isnull=True)
          .select_related('task_type','model','work_order','ronda','ronda__linia_comanda__order')):
```

Tres condicions i cap més: **`status='Done'`**, **client**, i **cap línia d'albarà prèvia**. El
docstring (`:734-751`) ho declara: *«Parteix de ModelTask (NO de WorkOrder): així recull també la
feina amb `work_order=NULL`»*, i *«NO filtra per `facturable` (descartat)»*.

Els altres tres orígens són `WorkOrderAdjustment` (`EXTRA_BILL`/`DEDUCTION`, `:800`) i `Expense`
(`:825`). **Ni la ronda ni el model són l'eix**: la ronda entra com a *etiqueta* de cada tasca
(`_amb_ronda`, `:770`) i el model com a *bucket* de presentació (`_bucket`, `:761`).

### 2.3 Quin preu usa i d'on el treu — **el trencament, mesurat**

```python
# backend/fhort/commerce/services.py:785-789
wo = t.work_order
if wo is not None and wo.kind == 'ORDER':
    price = Decimal(str((wo.price_snapshot or {}).get('unit_price') or '0')).quantize(_CENT)
else:
    price = Decimal('0.00')   # COLLECTOR o work_order=NULL: el Salva posa preu en DRAFT
```

El preu **sí que ve de la línia de comanda**, però per un camí llarg i sense divisor:
`SalesOrderLine.unit_price` → congelat a `WorkOrder.price_snapshot['unit_price']` en assignar
(`services.py:316-317`) → **repartit sencer a cada tasca**.

**Mesura (executant `get_billable_items` en read-only sobre `fhort`):**

```
MODEL QA-M4-0001 · [QA-M4] Amb comanda · R3 desborda · items=3 · proposat=360.00 €
   - TASK  Definició POM · QA-M4-0001   120.00 €   ronda=1  fora=False
   - TASK  Definició POM · QA-M4-0001   120.00 €   ronda=2  fora=False
   - TASK  Definició POM · QA-M4-0001   120.00 €   ronda=3  fora=True
```
contra la línia de comanda real:
```
línia 15 · SO-2026-0003 · quantity 5,00 · qty_allocated 1,00 · unit_price 120,00 · rounds_included 2
```

→ **La safata proposa 360 € on la comanda ven 120 €.** Tres tasques del mateix `pom` (una per
volta) cobren cadascuna el preu unitari sencer de la línia. El comentari de `:750-755` avisa que
això és deliberat per a M4 (*«NO ES TOCA CAP PREU… una tasca d'una volta desbordada segueix
proposant el preu que li tocaria pel seu WorkOrder»*), però és exactament la conducta que la
decisió d'Agus retira.

**I el cas dominant és pitjor: el preu simplement no hi és.** De 9 WorkOrders del tenant, **8 són
`COLLECTOR`** amb `price_snapshot = {}`, i **1 és `ORDER`** (el banc de QA). De 26 ítems que la
safata proposa avui, **24 surten a 0,00 €**. Tot el diner que ha arribat mai a un albarà d'aquesta
base l'ha escrit el comercial a mà sobre el DRAFT.

### 2.4 Les línies ja emeses ho confirmen

```
DN-2026-0001 · ISSUED · Brownie · 105,00 €
  TASK  Definició POM · BRW-SS27-0001 (42 min)   qty 42,00 × 2,50 = 105,00   model_id ∅  wo 13 (COLLECTOR)
  TASK  Patró CAD · BRW-SS27-0001 (0 min)        qty  0,00 × 0,00 =   0,00   model_id ∅  wo 13
DN-2026-0002 · DRAFT · Brownie · 30,00 €
  TASK  Mesurar prenda · BRW-26-SS-0002          qty 1,00 × 30,00 =  30,00   internal_minutes 574
  TASK  Definició POM · BRW-FW26-0007            qty 1,00 ×  0,00 =   0,00   internal_minutes 488
```

Tres fets llegibles aquí:
1. **`DN-2026-0001` és format v1 de col·lector**: `quantity` són **minuts** i `unit_price` és
   preu/minut (2,50 €/min). La descripció encara arrossega el `(42 min)` que la v2 va treure.
2. **`model_id` és NULL a les 4 línies** → el PDF v2, que agrupa per `model_id`
   (`pdf_service.py:557`), les posaria totes en **un sol bloc sense capçalera de model**.
3. **`model_task_id` és NULL a les 4** (FK `SET_NULL`, les tasques origen ja no hi són) → aquestes
   línies **ja no diuen de quina feina venien**, i les 26 tasques `Done` del tenant apareixen totes
   com a no albaranades.

---

## Q3 · ENTREGABLES DEL MODEL — **els dos verds ja existeixen**

| senyal | on viu | com s'escriu | naturalesa |
|---|---|---|---|
| **ronda entregada** | `tasks.Entrega` (`models.py:230`), `OneToOne` amb `Ronda` | `informar_entrega` (`services_r.py:606`) — **declarat**, i **tanca la ronda en la mateixa transacció** (FIT-13, `:640`) | FET |
| **vist-i-plau client** | `Entrega.data_ok` + `qui_informa_ok` (`models.py:264-266`) | `informar_ok_client` (`services_r.py:643`) — manual, posterior, **un sol cop** | FET |
| *(auxiliar)* **lliurable** | derivat, no persistit | `ronda_lliurable` (`services_r.py:661`): totes les tasques amb `task_type.es_lliurable=True` a `Done` | **SENYAL PREVI**, no estat |

⚠️ **`lliurable` no és un tercer verd i no s'hi pot fer servir com a tal.** Per disseny torna
`False` quan la ronda no té cap tasca lliurable (`:672-674`: *«no hi ha res per lliurar» no és «ja
està lliurat»*), i la UI ja el va degradar a informatiu (`RondaPla.jsx:82-88`).

**Població mesurada — el segon verd no s'ha encès mai:**

| | |
|---|---|
| Rondes | **22** |
| amb `Entrega` | **3** (models 1383·R1, 1493·R1, 1495·R2) |
| amb `data_ok` (vist-i-plau) | **0** |
| Rondes obertes (`tancada_el IS NULL`) | 13 |
| `TaskType` amb `es_lliurable=True` | 5 de 15 |

🚩 **Decisió que això força:** una safata que exigeixi **els dos** verds retorna **zero files avui**.
Cal triar entre (a) requisit dur i assumir que el comercial ha de perseguir el `data_ok`, o (b) verd
1 = porta i verd 2 = semàfor informatiu a la fila. **No és una decisió tècnica** — el camp hi és i
funciona; el que no hi ha és l'hàbit d'omplir-lo.

**Exposició:** `GET /api/v1/models/<id>/rondes/` (`views_b.py:1953`) → `RondaSerializer`
(`serializers_b.py:357`), que serveix `entrega` niat + `entregada` (declarat) + `lliurable` (deduït).

---

## Q4 · TASCA NO INICIADA → NO FACTURABLE

### 4.1 Com està modelat (i no és un estat nou — confirmat)

**No hi ha cap camp "no facturable" a la instància de tasca.** El mecanisme és un **ajust**:

```python
# backend/fhort/commerce/services.py:268-275  (dins close_work_order, cancel_pending=True)
for t in pending:
    WorkOrderAdjustment.objects.create(
        work_order=work_order, model_task=t, kind='DEDUCTION', amount=Decimal('0.00'),
        description=f"Recepta no executada: {t.task_type.code}", resolved_by=user)
    t.work_order = None          # ← es DESLLIGA del WO
    t.save(update_fields=['work_order','updated_at'])
```

Noms exactes, per si el Patró B els necessita:
- **estat d'origen:** `ModelTask.status = 'Pending'` (`tasks/models.py:293`)
- **artefacte comercial:** `WorkOrderAdjustment(kind='DEDUCTION', amount=0)` (`commerce/models.py:597`)
- **etiqueta:** `"Recepta no executada: <task_code>"`
- **valoració posterior:** `apply_commercial_review` (`services.py:952`) fa `update_or_create` sobre
  `(work_order, model_task)` i **retroba el marcador d'amount 0** per fixar-hi el preu (`:961-963`).
- **`TaskType.facturable`** (`tasks/models.py:115`) existeix però **és del catàleg, no de la
  instància**, i la safata **el descarta explícitament** (`services.py:739`). 2 de 15 tipus el tenen
  a `False`. **No és la palanca d'aquesta regla.**

### 4.2 On es fa visible AVUI — en un sol lloc

Únicament al **modal de tancament d'encàrrec**, `/comercial/encarrecs/:id`:
- backend: `POST work-orders/{id}/close/` retorna `{closed, blockers, pending_proposals}` amb 409 si
  no es pot tancar (`views.py:484-498`);
- frontend: `WorkOrderDetail.jsx:372-378` llista les `pending` i `:382-384` ofereix el botó
  `close_deduct` que crida `doClose({cancel_pending: true})`.

I després, per fixar-ne l'import, al panell de revisió comercial del mateix WO
(`WorkOrderDetail.jsx:183`, `POST /review/`).

### 4.3 Què falta perquè el contenidor de ronda i la comanda ho vegin

**No falta cap dada; falta transport i lloc.** Tres forats concrets, tots mesurats:

1. **`RondaSerializer` no porta res de comerç.** `serializers_b.py:372-373` serveix exactament
   `['id','model','seq','motiu','oberta_el','tancada_el','entrega','entregada','lliurable']` —
   **sense `fora_de_comanda`, sense `linia_comanda`, sense `numeral_vigent`**.
   Grep de `fora_de_comanda` a tot el repo: **5 encerts, tots a `commerce/services.py`,
   `tasks/models.py` i `tasks/services_r.py`. Zero al frontend.** El dashboard del model **no pot**
   saber que una volta ha desbordat el pacte.
2. **`RondaPla.jsx` (el contenidor de ronda) no té cap element comercial**: pinta nom de volta,
   fase, estat, rectificacions, `lliurable`, temps, progrés, línia d'entrega i `ok_client`
   (`RondaPla.jsx:60-186`). Cap xip de comanda, cap marca de tasca deduïda, cap paperera.
3. **La comanda tampoc ho veu**: `allocation` (`views.py:331-359`) serveix les tasques amb
   `status`/`off_recipe`, però **no diu si una `Pending` ja s'ha deduït** — l'`Adjustment` viu al WO
   i no viatja en aquesta resposta.

**Població:** 7 tasques `Pending` · 23 `Paused` · 26 `Done`. **0 `WorkOrderAdjustment` a tot el
tenant** → el camí de la deducció **existeix al codi i no s'ha exercit mai a `fhort`**.

---

## Q5 · DESASSIGNAR · i el mapa per a la paperera del contenidor de ronda

### 5.1 Què fa avui el botó "Desassignar" de `/comercial/comandes/1`

**Gest:** `OrderDetail.jsx:398` (botó vermell `ti-unlink`, dins l'expansió de línia) → modal de
confirmació (`:317-347`, confirmació obligatòria *«perquè desassignar és irreversible»*) →
`commerce.workOrders.unassign(woId)` (`:169`) → `POST commerce/work-orders/{id}/unassign/`
(`views.py:500`) → `unassign_model_from_order_line` (`services.py:432-466`).

**Operació — sobre el `WorkOrder`, mai sobre les tasques:**

| pas | codi | efecte |
|---|---|---|
| guards | `services.py:441-450` | `kind='ORDER'` · `status='OPEN'` · `order_line` no nul · **cap `DeliveryNoteLine` que l'apunti** |
| cartera | `:454-457` | `order_line.qty_allocated −= 1` (clamp a 0, quantize 0,01) |
| orfandat | `:460-462` | `orphaned_from_line ← order_line`, `order_line ← None`, **mateix acte** |
| tasques | `:463-465` | **NO ES TOQUEN.** Decisió declarada (D3): *«la feina real ja executada no s'ha de revertir al col·lector»* |

**Camí invers:** `reattach_orphan_to_line` (`:469`), amb picker alimentat per
`GET work-orders/{id}/reattach-candidates/` (`views.py:516`) i informe a
`GET work-orders/orphaned/` (`views.py:444`, pantalla `OrphanedWorkOrders.jsx`).

**Visibilitat del botó:** el flag `can_unassign` el calcula el backend a `allocation`
(`views.py:349`) com a **mirall exacte del guard** — `kind=='ORDER' and status=='OPEN' and not
albaranat`. La UI amaga, l'API refusa.

### 5.2 ⚑ La tasca porta FK a línia de comanda, a WO, o a cap?

**A cap de les dues directament.** Mesurat al model:

```
ModelTask ──work_order──► WorkOrder ──order_line──► SalesOrderLine
           (SET_NULL,                (PROTECT,
            tasks/models.py:331)      commerce/models.py:537)
```

- **`ModelTask` NO té cap FK a `SalesOrderLine`.** Grep confirmat: l'única FK de `tasks` cap a
  `commerce` és `ModelTask.work_order`, i és `SET_NULL`.
- **`Ronda` SÍ que en té una**: `Ronda.linia_comanda` (`tasks/models.py:207`, `SET_NULL`) — però és
  **una foto documental**, no govern: es desa en obrir la volta i no es recalcula.
- El resolutor viu del vincle és **`linia_de_comanda(model)`** (`services_r.py:54`), que **cada cop
  torna a preguntar pel pivot WO**.

**Tasca lliure vs tasca lligada a comanda** — la distinció es llegeix així:

| cas | `work_order` | `wo.kind` | `wo.order_line` | com queda a la safata |
|---|---|---|---|---|
| lligada a comanda | no nul | `ORDER` | no nul | preu = `price_snapshot` |
| lligada a WO orfe | no nul | `ORDER` | **nul** (`orphaned_from_line` ple) | preu = `price_snapshot` (l'snapshot sobreviu) |
| feina de col·lector | no nul | `COLLECTOR` | nul per constraint | **preu 0,00** |
| **tasca lliure** | **nul** | — | — | **preu 0,00** |

**Població:** 48 tasques amb `work_order`, **8 sense**. 50 amb `ronda`, 6 sense.

### 5.3 Mapa d'operacions per a una paperera al contenidor de ronda — **la porta ja existeix**

**No cal endpoint nou.** `DELETE /api/v1/model-tasks/{id}/` ja hi és, amb el guard exacte que la
decisió d'Agus demana:

```python
# backend/fhort/tasks/views_b.py:70-86  (ModelTaskViewSet.destroy)
if instance.status != 'Pending':
    return Response({'error': 'Només es poden esborrar tasques pendents (Pending). Una tasca '
                     'iniciada, pausada o feta conserva la seva història i no s\'esborra.'},
                    status=409)
...
instance.delete()
if assignee_id is not None:
    cleanup_after_pending_delete(model_id=model_id, assignee_id=assignee_id)   # recompute + cua
```
Gate `DEFINE_TASKS` (`:64-66`) i row-level scope (`:55-63`) ja aplicats.

| operació | existeix? | on |
|---|---|---|
| esborrar tasca `Pending` | ✅ | `DELETE model-tasks/{id}/` (`views_b.py:70`) |
| refusar esborrar tasca treballada | ✅ 409 | `views_b.py:71-75` |
| netejar cua/planificació després | ✅ | `plan_service.cleanup_after_pending_delete` (`:84`) |
| **gest a la UI del contenidor de ronda** | ❌ | `RondaPla.jsx` no té cap `ti-trash` (grep: 0 encerts a `components/model/*`, excepte `MeasureGrid.jsx:915`, que és d'una altra cosa) |
| deduir en comptes d'esborrar | ✅ | `close_work_order(cancel_pending=True)` (Q4) |

⚠️ **Són DUES operacions diferents i no s'han de fondre:** esborrar (la tasca desapareix, només
`Pending`) i deduir (la tasca **es conserva** amb la seva història i es deslliga del WO amb un
`DEDUCTION`). La segona és la que el comercial ja fa servir.

---

## Q6 · PREU/HORA DE COST

### 6.1 ¿Existeix cap camp? — **dos, i tots dos estan buits**

| camp | on | tipus | valor real a `fhort` |
|---|---|---|---|
| `TenantConfig.hourly_rate` | `accounts/models.py:46` | `Decimal(10,2)` **null** | **NULL** (1 fila) |
| `UserProfile.cost_hora` | `accounts/models.py:14` | `Decimal(8,2)` default 0 | **0,00 als 7 perfils** |

`hourly_rate` és la **tarifa plana de COST de la casa** (`commerce/models.py:54,63`: *«cost = Σ
cascada(task_code, GTI) × TenantConfig.hourly_rate… són eixos separats»*), i **ja té consumidor viu**:

```python
# backend/fhort/commerce/serializers.py:520-527  (DeliveryNoteLineSerializer.get_internal_cost)
rate = self._hourly_rate()                      # TenantConfig.objects.first().hourly_rate
if rate is None or obj.internal_minutes is None:
    return None
cost = (Decimal(obj.internal_minutes) / Decimal(60) * Decimal(rate)).quantize(Decimal('0.01'))
```

🚨 **La columna de cost de l'albarà està construïda i és MUDA per dada, no per codi.** El docstring
(`:477-482`) documenta que `internal_cost` *«es podava sola quan `hourly_rate` era null; el dia que
s'omplís a PROD, hauria començat a viatjar de debò»*. **`internal_minutes` sí que està poblat**
(574 i 488 minuts a `DN-2026-0002`), o sigui que **el numerador hi és i el multiplicador no**.

### 6.2 Encaix amb la decisió d'Agus ("editable només a l'albarà")

| requisit del brief | on és avui | distància |
|---|---|---|
| preu/hora **editable a l'albarà** | `TenantConfig`, gate `CONFIGURE`, whitelist de `PATCH` a `s2_views.py:447`; **pantalla de configuració del tenant, no l'albarà** | cal decidir **l'àmbit**: global (com ara), per albarà, o per línia |
| **cost del model** | derivat per línia (`internal_cost`), **no agregat per model** enlloc | falta l'agregació; el bloc-model del PDF ja té subtotal de venda (`pdf_service.py:637`) però cap de cost |
| **relacionat amb la línia de comanda per rendibilitat** | inexistent — cap lloc compara `DeliveryNoteLine.internal_cost` amb `SalesOrderLine.line_total` | és **el forat real de Q6** |
| **no lligat a tècnic ara** | ✅ coherent: `hourly_rate` és de la casa; `UserProfile.cost_hora` (per tècnic) existeix i **ningú no el llegeix** | cap canvi; el camp per tècnic queda de reserva |
| **mai surt al client** | ✅ ja garantit **dues vegades**: `PodaEconomicaMixin` amb `CAMPS_ECONOMICS=('unit_price','line_total','internal_cost')` (`serializers.py:479`) i el PDF, que no el pinta (`pdf_service.py:497`: *«SENSE cost intern»*) | cap canvi |

**Mapa d'on cabria** (només mapa, sense recomanar):

| opció | granularitat | conseqüència |
|---|---|---|
| A · `TenantConfig.hourly_rate` (avui) | empresa | 1 valor; l'albarà només l'exhibiria, no l'editaria — **contradiu «editable a l'albarà»** |
| B · camp nou a `DeliveryNote` | document | l'albarà congela la seva tarifa com ja congela els preus (patró `unit_price`); coherent amb la família de documents |
| C · camp nou a `DeliveryNoteLine` | línia | màxima flexibilitat, però `internal_cost` ja és derivat i passaria a ser semi-persistit |
| D · `UserProfile.cost_hora` | tècnic | **exclòs pel brief** ("no lligat a tècnic ara") |

Per a la rendibilitat, el pivot de comparació ja existeix i és el mateix de Q1: cost
(`Σ internal_minutes × rate`) contra venda, unides per **`DeliveryNoteLine.work_order → order_line`**
o pel nou eix model+ronda.

---

## Q7 · PANTALLES D'ENCÀRREC

### 7.1 Llista `/comercial/encarrecs` — 6 columnes

`frontend/src/pages/WorkOrders.jsx:116-148`:

| col | camp | font |
|---|---|---|
| `number` | `r.number` | `WO-YYYY-NNNN` |
| `kind` | badge neutre | `ORDER` / `COLLECTOR` |
| `customer` | `r.customer_nom` | |
| **`target`** | `kind==='COLLECTOR' ? r.period : r.model_codi` | **una columna, dues dades** (comentari `:132-134`) |
| `status` | badge | `OPEN` / `CLOSED` |
| `n_tasks` | comptador | |

És pantalla **de consulta i sense acció primària** (`:16-18`): els encàrrecs no es creen aquí.

### 7.2 ⚑ Camps que el model TÉ i la pantalla NO pinta

El coll d'ampolla **és el serializer, no la taula**. `WorkOrderSerializer` (`serializers.py:396-419`)
exposa del model **només `model_codi`** (`= model.codi_intern`, `:406`). No hi ha `nom_prenda` ni
`collection` **al payload**, o sigui que la pantalla no els podria pintar encara que volgués.

**I la dada hi és pràcticament sempre** (mesurat sobre `models_app_model`, 43 models):

| camp | poblat |
|---|---|
| `nom_prenda` | **43 / 43 (100 %)** |
| `collection` | 30 / 43 (70 %) |
| `codi_client` | **1 / 43** |

🚨 **La llei del nom no s'aplica aquí.** El nom del model existeix a tots els models i **no arriba a
la llista d'encàrrecs**, que ensenya només el codi intern. Contrast dins del mateix fitxer de vistes:
`work-orders/orphaned/` (`views.py:462-463`) **sí que serveix `nom_prenda`**, i `allocation`
(`views.py:350-351`) també — i `OrderDetail.jsx:395` el pinta. **Tres endpoints germans, i el
principal és l'únic que no el porta.**

Al PDF d'albarà el nom **ja mana**: la franja de model pinta `codi_intern` + **`nom_prenda`** +
[ref. client si difereix] + col·lecció + temporada (`pdf_service.py:585-597`).

### 7.3 Detall `/comercial/encarrecs/67`

⚠️ **El WorkOrder 67 no existeix.** Els ids vius a `fhort` són **13, 35, 36, 39, 40, 41, 42, 43, 44**;
al schema `los` tampoc hi ha cap id 67. La pantalla es descriu igualment (`WorkOrderDetail.jsx`, 449
línies): capçalera `customer_nom · (period | model_codi)` (`:265`), botó **Tancar** (`:269`), llista
de tasques amb estat/minuts, panell de **revisió comercial** dels extres i deduccions (`:183`), i
modal **generar albarà** (`:391`). Mateix patró que la llista: **`model_codi`, mai `nom_prenda`.**

### 7.4 Files "Col·lector" (període, sense model)

- **Model:** `WorkOrder.kind='COLLECTOR'` + `period='YYYY-MM'` (`commerce/models.py:552`), amb dues
  constraints que ho blinden (`:574-583`): `uniq_collector_customer_period` (un per client i mes) i
  `collector_no_model_no_orderline` (**mai `model`, mai `order_line`**).
- **Naixement:** hook lazy, no es creen a mà (`WorkOrders.jsx:16-17`).
- **Representació:** la columna `target` mostra el `period` en lloc del codi de model
  (`WorkOrders.jsx:137-138`), i el detall fa el mateix a la capçalera (`:265`).
- **Al col·lector res és `off_recipe`** — no hi ha recepta contra què comparar (`models.py:513-514`),
  i `price_snapshot` queda `{}` → **preu 0 a la safata**.
- **Població:** **8 dels 9 WO** són col·lectors: `2026-07` ×3, `2026-08` ×3, `2026-09` ×2.

### 7.5 Bulk close: ¿existeix acció reutilitzable per lot?

**No n'hi ha cap per a encàrrecs.** `close` és `@action(detail=True)` (`views.py:484`) i el frontend
el crida d'un en un (`WorkOrderDetail.jsx:133`).

**Però el precedent d'aquesta casa ja està escrit**, a la mateixa app i per al germà del costat:

```python
# backend/fhort/commerce/views.py:679-694
@action(detail=False, methods=['post'], url_path='mark-invoiced-bulk')
def mark_invoiced_bulk(self, request):
    ids = request.data.get('ids') or []
    marked, skipped = [], []
    for dn in DeliveryNote.objects.filter(pk__in=ids):
        try:
            mark_delivery_note_invoiced(dn, user=profile); marked.append(dn.id)
        except DjangoValidationError:
            skipped.append(dn.id)
    return Response({'marked': marked, 'skipped': skipped})
```

**Cost aproximat d'un tancament múltiple** (mapa, no implementació):

| peça | esforç | per què és baix |
|---|---|---|
| endpoint `close-bulk` | **baix** | calc del `mark-invoiced-bulk`; `close_work_order` **ja retorna un dict estructurat i mai llança per bloqueig** (`services.py:230-231`) → el bucle no necessita `try/except`, només repartir `closed` / `blockers` |
| semàntica de `cancel_pending` | **mitjà — i és una decisió, no codi** | avui és un booleà **per encàrrec**, contestat a un modal que **llista quines `Pending` es deduiran** (`WorkOrderDetail.jsx:372-378`). En lot, o s'aplica a cegues a tots, o el modal ha d'agregar les pendents de N encàrrecs |
| UI de selecció | **baix-mitjà** | la llista no té checkboxes; el patró de selecció múltiple ja existeix a la safata d'albaranables (`DeliveryNoteDetail.jsx:245`) |
| resposta parcial | **baix** | `{closed:[], blocked:[{id, blockers}]}` — un tancament en lot **serà sempre parcial**: 23 tasques `Paused` al tenant bloquegen el seu WO |

---

## Q8 · DOCUMENT ALBARÀ — on es genera i què rep

**Generació:** `generate_delivery_note_pdf(delivery_note, lang=None)` —
`backend/fhort/commerce/pdf_service.py:493-676`. ReportLab (`BaseDocTemplate`, A4), **sense template
HTML**. Servit per `GET commerce/delivery-notes/{id}/pdf/?lang=` (`views.py:696-706`), amb
`resolve_pdf_lang` (`pdf_service.py:168`) que cau al `Customer.language`.

**Dades que rep** (llegides de l'objecte, sense paràmetres extra):

| bloc | font | línia |
|---|---|---|
| emissor | `TenantConfig` via `_emissor_left` | `:537` |
| meta | `document_number`, `issued_at` | `:541-543` |
| client | `customer.rao_social or .nom` + `_customer_oneliner` | `:551-556` |
| **agrupació** | **`lines.filter(visible=True)` agrupades per `model_id`** | `:560-564` |
| franja de model | `codi_intern` · **`nom_prenda`** · [`codi_client` si difereix] · `collection` · `temporada any` · **data de lliurament** (`max(model_task.finished_at)`) | `:568-597` |
| detall | descripció · data · qty · unitat · preu · import | `:600-629` |
| marca parcial | `● Feta` / `● Pendent` per línia si alguna tasca del bloc no és `Done` | `:610-613` |
| comentaris | línies `MANUAL` en cursiva gris sota el bloc | `:631-636` |
| **subtotal per model** | Σ `line_total` del bloc | `:637-643` |
| resum | `subtotal` / IVA / `total` del document | `:659-668` |
| observacions | `delivery_note.notes` | `:671-675` |

**El que el PDF NO porta, per decisió declarada:** cap venciment ni condició de pagament
(`models.py:696-698`), **cap cost intern** ni `internal_minutes` (`:497`, i `models.py:779-781`:
*«mai al PDF»*), i cap línia amb `visible=False`.

**Per al mockup, tres fets que el condicionen:**
1. **L'agrupació per model ja hi és, amb franja i subtotal propis** — l'estructura que el brief vol
   està mig construïda.
2. **La RONDA no apareix enlloc del PDF.** `_ronda_header` només viatja a la safata
   (`services.py:708`); `DeliveryNoteLine` **no té FK a `Ronda`** (la traça és indirecta:
   `model_task.ronda`). Un albarà per model+rondes **necessita aquest salt**, que avui el PDF no fa.
3. **Amb `model_id` NULL, l'agrupació col·lapsa.** Les 4 línies existents el tenen buit → totes
   caurien en un únic bloc amb `ref='—'` i `name=''` (`:571-573`).

Hi ha una mostra al disc: `/var/www/ftt-staging/albara_v2_sample.pdf`.

---

## APÈNDIX A · Població mesurada (schema `fhort`, 2026-09-09, read-only)

```
SalesOrder        3      WorkOrder         9  (ORDER 1 · COLLECTOR 8)
SalesOrderLine    4      DeliveryNote      3  (ISSUED 1 · DRAFT 2)
Quote             8      DeliveryNoteLine  4
Ronda            22      WorkOrderAdjustment 0
Entrega           3      Expense             0
ModelTask        56      (Done 26 · Paused 23 · Pending 7)
```

| pregunta | resposta mesurada |
|---|---|
| Tasques `Done` sense línia d'albarà | **26 de 26** (les 4 línies existents tenen `model_task_id` NULL) |
| Tasques sense `work_order` | 8 de 56 |
| Tasques sense `ronda` | 6 de 56 |
| `rounds_included` poblat | 1 de 4 línies de comanda |
| Rondes `fora_de_comanda` | 1 de 22 |
| Entregues amb `data_ok` | **0 de 3** |
| `TenantConfig.hourly_rate` | **NULL** |
| `UserProfile.cost_hora > 0` | **0 de 7** |
| Models amb `nom_prenda` | **43 de 43** |
| `WorkOrder` id 67 | **no existeix** (ni a `fhort` ni a `los`) |

## APÈNDIX B · Comandes de verificació (totes read-only)

```bash
PGOPTIONS='-c default_transaction_read_only=on' \
  sudo -u postgres psql -p 5433 -d ftt_staging -c "SET search_path TO fhort; <query>"

# La safata real, sense escriure res:
PGOPTIONS='-c default_transaction_read_only=on' \
  venv/bin/python manage.py tenant_command shell --schema=fhort < safata.py
```

---

## APÈNDIX C · Els sis forats, ordenats per distància

| # | forat | distància | fitxer d'entrada |
|---|---|---|---|
| 1 | `RondaSerializer` no porta `fora_de_comanda` / `linia_comanda` / `numeral_vigent` | **curta** — 3 camps a `fields` | `tasks/serializers_b.py:372` |
| 2 | `WorkOrderSerializer` no porta `nom_prenda` / `collection` | **curta** — 2 `CharField(source=…)`, com ja fa `orphaned` | `commerce/serializers.py:406` |
| 3 | paperera de tasca `Pending` al contenidor de ronda | **curta** — l'endpoint ja hi és amb el guard correcte | `components/model/RondaPla.jsx` |
| 4 | `close-bulk` d'encàrrecs | **mitjana** — calc de `mark-invoiced-bulk`; la decisió és `cancel_pending` en lot | `commerce/views.py:679` |
| 5 | **eix d'agregació: tasca → model+ronda** a la safata i a l'albarà | **llarga** — canvia la unitat, no el filtre | `commerce/services.py:734` |
| 6 | **preu: de `price_snapshot` per tasca → línia de comanda per ronda** | **llarga** — i toca `generate_delivery_note` **i** `add_lines_to_draft` **i** el PDF | `commerce/services.py:788`, `:894`, `pdf_service.py:560` |

> **Els forats 5 i 6 són el mateix moviment vist dues vegades** i no es poden separar: el dia que la
> unitat albaranable sigui el model+ronda, el preu deixa de tenir on multiplicar-se.

---

*Diagnosi read-only. Cap escriptura a BD, cap fitxer del repo modificat fora d'aquest document, cap
commit. Fets amb `fitxer:línia`; els números surten de consultes en transacció read-only.*
