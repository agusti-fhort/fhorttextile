# M4 · COMERCIAL — el numeral a la comanda i el desbordament

> **Base**: `dev` `2cdaccd5` (M1..M3 fusionats i pushejats) · worktree `/var/www/ftt-m4`,
> branca `m4-comercial` · **10 commits, CAP PUSH** · cap restart del servei compartit.
> Últim sprint de CONSTRUCCIÓ abans del retroactiu (M5).

**Les dues lleis que aquest sprint construeix**

| | |
|---|---|
| **FIT-5** (Agus + Salva, 24/08) | El numeral de rondes previstes viu **A LA COMANDA**. El servei es configura amb preu; a la comanda es marca quantes revisions admet. El producte NO en porta res. **Una sola font de lectura** per al desbordament. |
| **FIT-12** (Agus, 24/08) | Quan les voltes reals superen el numeral, **la ronda R(n) amb les seves tasques** passa a encàrrecs per ser albaranada i facturada A PART. La ronda **segueix sent R(n)**: numeració intacta, i **el tècnic NO VEU RES**. Les dates inici/fi són la clau perquè comercial informi QUAN es va fer cada volta i PER QUÈ la n va a part. |

FIT-1 segueix viu: **res d'això escriu cap `Entrega`**.

---

## 0 · NETEJA PRÈVIA — i el que hi havia a sota

**`10fb078c`** retira `frontend/node_modules` del control de versions.

El symlink (mode `120000`) que s'hi va colar al merge d'M3 **apuntava a si mateix**
(`/var/www/ftt-staging/frontend/node_modules → /var/www/ftt-staging/frontend/node_modules`).

🚨 **I això no era només brutícia al repo: el directori real ja no hi és.** El symlink va
substituir `frontend/node_modules` als CINC worktrees que el compartien (`ftt-staging`, `ftt-m1`,
`ftt-m3`, `ftt-m3cv`, `ftt-m4`), o sigui que **`npm run build` està trencat a tots ells** fins que
algú hi torni a fer `npm ci`. Aquí s'ha fet (`npm ci --prefer-offline`, 285 paquets, 8 s: la
cau de `/root/.npm` ho cobreix sense xarxa) i el build és verd. **Les altres sessions ho han de
fer al seu worktree**; el repo ja no els hi tornarà a posar.

Per què el `.gitignore` no ho va aturar: la regla era `frontend/node_modules/` **amb barra
final**, i una barra final només casa amb DIRECTORIS. El symlink hi va passar pel forat. Ara va
sense barra (casa les dues formes) i s'hi ha afegit `frontend-backoffice/node_modules`.

**`3e72d92a`** tanca la mateixa família: un worktree nou enganxa symlinks cap al `venv` i al
`.env` de `ftt-staging` (tots dos fora de git) i `git status` els ensenyava com a untracked —
exactament el camí per on va entrar el de `node_modules`. Ara `backend/venv` i `backend/.env`
també s'ignoren.

| Verificació | Resultat |
|---|---|
| `git ls-files \| grep node_modules` | **0** |
| `npm run build` al worktree | ✅ verd |

---

## 1 · FASE 0 · EL CENS

### 1.a · RECUPERACIÓ — què són les 🚩 3 i 4 d'M3 (transcrites)

Surten de `IMPLEMENTACIO_M3_CICLE_VIDA_2026-08-24.md` §10 i queden obertes després de la CODA
(§C4). **Literalment:**

> **🚩 3** — `frontend/src/components/EstatBadge.jsx`: **component sense cap importador** que el
> cens va trobar. Candidat a retirar; no s'ha tocat.
>
> **🚩 4** — La columna «Estat» de `/models` segueix pintant un guió. Ara que les VISTES filtren
> per estat, la columna és redundant: **o pinta l'estat comercial del Kanban (quan hi sigui) o
> se'n va.**

**Verificades contra el codi d'avui** (llei `ftt-acta-al-codi-pot-mentir`):

- 🚩 3 **segueix certa, i val la pena dir per què no salta a la vista**: hi ha DOS `EstatBadge`.
  El VIU és `frontend/src/components/commercial/estats.jsx` i el fan servir 4 pantalles
  (`WorkOrderDetail`, `Quotes`, `WorkOrders`, `Encarrecs`). El MORT és
  `frontend/src/components/EstatBadge.jsx`, 3.733 bytes, **zero importadors**. Un `grep EstatBadge`
  ingenu el fa semblar viu — el nom és el mateix.
- 🚩 4 segueix oberta i **no s'ha tocat**.

**Cap de les dues toca l'abast d'M4** i per tant no s'ha aturat res. La 4 s'hi acosta de nom
(«estat comercial del Kanban»), però M4 no toca ni `/models` ni el board: el desbordament és un
fet de la RONDA i del document comercial, i la seva cara és la safata d'albaranables.

### 1.b · Model ↔ comanda, AVUI

🔑 **No hi ha cap FK directa. El PIVOT és el `WorkOrder`.**

```
models_app.Model ──< commerce.WorkOrder >── commerce.SalesOrderLine ── SalesOrder
                     (kind='ORDER')          (order_line)
```

- `commerce/models.py:513` — `WorkOrder.model` → `models_app.Model` (null = col·lector)
- `commerce/models.py:516` — `WorkOrder.order_line` → `commerce.SalesOrderLine` (nullable)
- `commerce/models.py:523` — `orphaned_from_line`: **traça** d'una desassignació, mai govern
- `commerce/services.py:306` — el guard que ho fa resoluble: **«El model ja té un encàrrec (WO
  ORDER) actiu»**, o sigui *com a molt UN* WO `ORDER` amb `status='OPEN'` per model
- L'altre vincle model↔comercial, `QuoteLineModelIntent` (`models.py:284`), és **d'OFERTA i
  informatiu** («intenció pura»): no serveix per resoldre cap comanda

**Recomptes a `fhort`** (25/08), i la sorpresa:

| | `fhort` | `los` |
|---|---|---|
| `Model` | 37 | 51 |
| `WorkOrder` | 6 | 0 |
| … de tipus **`ORDER`** | **0** | **0** |
| … de tipus `COLLECTOR` | 6 | 0 |
| `SalesOrder` / `SalesOrderLine` | 2 / 3 | 0 / 0 |
| `DeliveryNoteLine` amb `model_task` | **0** | 0 |
| `Ronda` / `ModelTask` | 4 / 28 | 0 / 0 |

🚨 **CAP MODEL DE STAGING TÉ COMANDA.** Els 6 WorkOrder de `fhort` són tots col·lectors. El
substrat que el brief donava per verificat (`DeliveryNoteLine.model_task_id` existeix i el codi
que l'omple està escrit, `services.py:596` i `:835`) **és cert al CODI i buit a les DADES**: 0
files. La conseqüència pràctica és que **el desbordament no es reprodueix a staging sense
fabricar-hi una comanda** — v. §6, el banc.

### 1.c · On viuen preu i configuració a la línia de comanda

`SalesOrderLine` (`commerce/models.py:369`) hereta d'`AbstractDocumentLine`
(`commerce/models_base.py:70`): `product`, `description`, `quantity`, **`unit_price`** (còpia
CONGELADA del preu del `Product`, mai FK viva), `line_total`, `position`; i hi afegeix
`qty_allocated`.

La configuració del SERVEI viu al `Product` (`nature`, `price_mode` FIXED/TIME_BASED,
`base_price`, `sale_rate`, `markup_pct`) — que és exactament el que FIT-5 diu que NO ha de portar
el numeral.

⚠️ **La línia és IRREVERSIBLE per disseny (B3b)**: `SalesOrderLineSerializer.read_only_fields`
congela `product`/`description`/`quantity`/`unit_price`/`line_total`/`position`, i **l'únic camp
mutable per API era `qty_allocated`**. El numeral n'és el segon, i és una excepció declarada
(§2).

### 1.d · El camí `get_billable_items` → albarà

| | |
|---|---|
| **Qui el crida** | `commerce/views.py:601` — `GET /api/v1/commerce/delivery-notes/billable/?customer=` (gate CONFIGURE) |
| **Des d'on** | `frontend/src/pages/DeliveryNoteDetail.jsx:160` — la **safata** que s'obre amb el botó «Afegir ítems» d'un albarà **DRAFT** |
| **Què fa** | Parteix de `ModelTask` (no de `WorkOrder`), agrupa **per MODEL**, i exclou el que ja té línia d'albarà |
| **Escriptura** | `add_lines_to_draft` (`services.py:769`) → `DeliveryNoteLine` amb `model_task`, `model`, `line_kind`, `product` |
| **Què li faltava** | **saber de quina VOLTA parla**. Res més: ni taula nova, ni FK de ronda a l'albarà |

🚩 **UNA PRECISIÓ DE NOM, perquè el brief i el producte no es diuen igual.** «La pantalla
d'Encàrrecs (menú COMERCIAL)» és `/comercial/encarrecs` → `WorkOrders.jsx`, que llista
**contenidors `WorkOrder`**. Una volta fora de comanda **no en fabrica cap**: la seva feina són
`ModelTask` del mateix WO ORDER del model. El «camí d'encàrrecs» que el brief identifica amb
`fitxer:línia` (`get_billable_items` → `DeliveryNoteLine.model_task_id`, `services.py:596/835`)
és **la SAFATA D'ALBARANABLES**, i el brief mateix diu que «la safata és el lliurament d'aquest
sprint». **És on s'ha construït.** Fer-ho a `WorkOrders.jsx` hauria demanat fabricar un WorkOrder
per volta desbordada, que és una peça de domini que ningú no ha demanat.

### 1.e · La pregunta que el brief deixava oberta

> «Si b) revela que un model pot NO tenir comanda: el desbordament no aplica.»

**Revelat, i és el cas NORMAL** (37 de 37 models a `fhort`). Està construït com a **comportament
explícit**: `numeral_efectiu(model)` retorna `(None, None)` i cap volta es marca mai. Té test
propi (`test_model_SENSE_comanda_no_te_limit_i_no_es_un_error`) i control negatiu al banc de QA.

---

## 2 · FASE 1 · EL NUMERAL (FIT-5) · `31864e69` + `ca9947b1`

### El camp, i el nom

**`SalesOrderLine.rounds_included`** · `PositiveIntegerField(null=True, blank=True)`

El nom va en **anglès** perquè `commerce/` ho és per llei (`models_base.py`, lleis heretades de
B1: «naming BD/codi en ANGLÈS»), mentre que `tasks/` parla català (`Ronda`, `seq`, `motiu`). A la
cara es diu **«Voltes incl.»** (ca) · «Rounds incl.» (en) · «Vueltas incl.» (es).

🔑 **`null` NO és `0`, i la diferència és la peça central:**

| Valor | Vol dir |
|---|---|
| `null` | **sense límit** — el pacte no en fixa cap, cap volta desborda mai |
| `0` | **cap volta inclosa** — la primera ja desborda |
| `n` | n voltes cobertes pel preu; la n+1 va a part |

Per això neix `null` i s'omple a mà: un default de `0` convertiria **totes les comandes d'avui**
en desbordades des de la R1, i un default d'`1` seria inventar un pacte que ningú no ha signat.

### Les dues decisions que el camp arrossega

**(1) És una EXCEPCIÓ DECLARADA a la irreversibilitat de B3b.** La resta de la línia és
congelada; això no, i a posta — FIT-5 diu «i es modifica el preu si cal», o sigui que el numeral
és una **condició del pacte** que el comercial ha de poder corregir sense refer la comanda. **No
toca cap import ni cap total**, i per tant no reobre res del que la irreversibilitat protegeix. El
fum HTTP ho mesura per les dues bandes: el numeral es corregeix per `PATCH` (200) i `unit_price`
segueix sent inamovible.

**(2) VIATJA PODAT, tot i no ser un import.** Entra a `CAMPS_ECONOMICS` del serializer. FIT-12 diu
que el tècnic no veu res del desbordament, i aquesta línia la llegeixen **dues pantalles
tècniques** (`ProductionTab.jsx` i l'`ActionsMenu` del selector d'assignació): sense la poda el
pacte comercial els arribaria al payload encara que cap component el pintés. La poda és per
PAYLOAD i no per endpoint (v. `PodaEconomicaMixin`), que és la forma exacta que aquest cas demana
— les dues pantalles segueixen rebent `quantity`/`qty_allocated` i perden el numeral. Que el
mecanisme es digui «econòmica» és un nom, no un límit: el que fa és «aquest camp només per a qui
té COMERCIAL».

I una conseqüència que calia tancar: **`validate_rounds_included` tanca l'ESCRIPTURA amb el
MATEIX predicat de la poda** (`pot_veure_diner`). L'endpoint demana CONFIGURE (és la casa de la
cartera, no del comerç), i sense el guard el camp quedava **escrivible-a-cegues** per a un manager
sense COMERCIAL: PATCH acceptat, i el valor desapareixent de la resposta que ell mateix rep.

### La cara

`OrderDetail.jsx` — columna **«Voltes incl.»** a la taula de línies, editable amb el patró
**save-on-blur** de la casa. La cel·la buida diu **«Sense límit» amb paraules**, no amb un guió:
un guió al costat d'un `0` no distingeix «cap volta inclosa» de «no s'ha pactat res», i és
precisament la distinció que decideix si una volta desborda. El buit viatja com a `null` explícit.

**Migració: `commerce/0022_salesorderline_rounds_included.py`** (el cap al disc era `0021`).

---

## 3 · FASE 2 · LA COSTURA Ronda↔comercial (FIT-12) · `c85e44bc`

### Tres camps a `Ronda`, i per què tres

| Camp | Què és |
|---|---|
| `fora_de_comanda` · `BooleanField(default=False)` | **el FET**: aquesta volta supera el numeral i es factura a part |
| `linia_comanda` · FK → `commerce.SalesOrderLine`, `SET_NULL` | **quina** línia el governava (`related_name='rondes'`) |
| `numeral_vigent` · `PositiveIntegerField(null=True)` | **la foto** del numeral en obrir |

Amb `oberta_el` / `tancada_el`, que **ja hi eren**, la safata pot dir la frase sencera:
`R3 · fora de comanda · 25/08/2026 → oberta · n>2 de la comanda SO-2026-0003`. **No ha calgut cap
camp de dates nou**: FIT-12 en demanava i la `Ronda` ja les portava.

Sí, `tasks` guanya una FK cap a `commerce` (que és la costura que el brief anuncia). **No hi ha
cicle de migracions**: `tasks/0053` depèn de `commerce/0022`, i les migracions de `commerce` que
miren `tasks` són totes anteriors. `makemigrations` i `migrate_schemas` ho resolen sense tocar res.

### 🔒 Es resol UNA VEGADA, EN OBRIR, i NO es recalcula

El numeral és editable (FIT-5). Si el veredicte es tornés a calcular a cada lectura, **pujar el
numeral de 2 a 3 REESCRIURIA la història**: la R3 que es va treballar sabent que anava a part
apareixeria de sobte com a inclosa, i una safata que ja l'hagués mostrat canviaria sola. Per això
els tres camps són una FOTO, i per això `numeral_vigent` es desa al costat del booleà — el
«perquè» ha de seguir sent llegible encara que el numeral hagi canviat després.

> 🚩 **CONSEQÜÈNCIA DECLARADA, per a Agus.** Pujar el numeral **no** torna a dins les voltes ja
> obertes. Si el comercial vol repescar-ne una, avui és un acte a mà sobre la fila. És la mateixa
> disciplina de no-backfill que M1-bis i M3 ja apliquen. **Si es vol automàtic, és decisió seva.**

### Els tres resolutors (`tasks/services_r.py`)

- **`linia_de_comanda(model)`** — el pivot és el `WorkOrder`. Mana l'**OBERT** (únic per guard
  d'`_assign_model_core`); si cap no ho està, **el més recent** que encara conservi la seva línia.
  Queden fora: els WO **orfes** (`order_line=NULL` — desassignar és treure el model de la venda) i
  les comandes **CANCELLED** (una venda anul·lada no pacta res). Els `COLLECTOR` no hi entren mai
  (la constraint `collector_no_model_no_orderline` ho garanteix).
- **`numeral_efectiu(model)`** → `(linia, numeral)`, amb els tres «sense límit» distingibles.
- **`resol_desbordament(ronda)`** — escriu els tres camps. `seq > numeral` = fora.

### On es crida

| Punt | Quan |
|---|---|
| `obrir_ronda` (R2+) | **dins de la transacció**: una volta que existeix sense veredicte seria una volta que el comercial no pot classificar, i el veredicte depèn del `seq` que s'acaba de reservar |
| `ronda_del_gest` (R1) | **només quan la R1 acaba de néixer** (`get_or_create` → `creada`). Cal perquè amb `rounds_included=0` **la primera volta ja desborda**, i si només es fes a `obrir_ronda` aquell cas no el veuria ningú. El `creada` és el que evita reescriure el veredicte a cada gest que retorna una R1 que ja existia |

Són els **dos únics** punts de producte que creen una `Ronda` (censat: `Ronda.objects.create` /
`get_or_create` només hi surt, més dos tests).

### 🚨 EL TÈCNIC NO VEU RES — i ho garanteix una cosa que ja hi era

`RondaSerializer.fields` (`tasks/serializers_b.py:372`) és una **llista explícita** i no inclou
cap dels tres camps nous. **Cap canvi a la cara del Pla de treball, ni una línia.** Té test
(`test_el_serializer_de_ronda_no_serveix_cap_camp_del_desbordament`) i mesura al fum HTTP
(`/api/v1/models/{id}/rondes/` → 200 amb 3 voltes i **zero** fuites) i al de pantalla (la fitxa
sencera del model desbordat, sense la paraula ni el número de comanda).

**Migració: `tasks/0053_ronda_fora_de_comanda_ronda_linia_comanda_and_more.py`** (cap al disc: `0052`).

---

## 4 · FASE 3 · EL DESBORDAMENT ARRIBA A LA SAFATA · `9c5e7de1` + `ada361d1`

**ES CONNECTA, NO ES REESCRIU**, tal com el brief demanava. `get_billable_items` ja recollia les
tasques `Done` d'una volta desbordada (parteix de `ModelTask`), i `add_lines_to_draft` ja omplia
`DeliveryNoteLine.model_task`. El que faltava era el **saber de quina volta parla**.

### Backend

- **`_ronda_header(ronda)`** — `{id, seq, motiu, fora_de_comanda, numeral_vigent, comanda,
  oberta_el, tancada_el}`. `comanda` és el `document_number`, resolt per la línia **congelada a la
  volta** i no per un recàlcul: si el model s'ha desassignat des de llavors, el perquè ha de
  seguir dient de quina venda parlava.
- Cada ítem que penja d'una `ModelTask` porta la seva `ronda`; cada bloc-model porta l'índex
  ordenat **`rondes`**. Extres i deduccions **hereten** la volta de la tasca que resolen; despeses
  i deduccions de concepte lliure van al calaix «sense volta».
- Els ítems es reordenen perquè els d'una mateixa volta quedin **contigus**, amb el calaix sense
  volta primer (on sempre ha estat).

⚠️ **NO ES TOCA CAP PREU.** El brief ho prohibeix («cap càlcul de preu de ronda») i s'ha respectat
al peu de la lletra: una tasca d'una volta desbordada **segueix proposant el preu del seu
WorkOrder**, exactament com abans (mesurat: `120.00 €` al banc). Qui decideix què val una volta
que va a part és el comercial, sobre el DRAFT. La safata només diu QUINA volta és i PER QUÈ va a
part. **Cap albarà ni factura automàtics**: llegir la safata no crea cap document (test + fum).

### Cara

Dins de cada bloc-model, la safata reparteix per volta: capçalera `R{n}`, el badge
**`warn` «fora de comanda»** quan ho és, les **dates** `inici → fi` («oberta» si encara ho és), i
el **perquè sencer** a la línia de sota.

- El calaix **SENSE VOLTA** queda primer i **sense capçalera**: és el que la safata ja era abans
  d'M4. **No se li inventa cap ronda a la feina anterior a la llei** (`QA-M1-0005`, el model
  llegat, hi surt exactament així).
- `ItemSafata` s'ha extret perquè el calaix i els blocs pintin **exactament la mateixa fila**:
  agrupar no pot canviar què es veu de cada ítem.
- El badge és el de la casa (`ui/Badge` variant `warn`), no colors a mà. «Fora de comanda» **no és
  una classificació neutra** (decisió 3 d'`estats.jsx`): és el fet que reclama la mirada del
  comercial, i és l'única raó per la qual aquella volta surt agrupada.

---

## 5 · TRES RETOCS QUE EL FUM DE PANTALLA VA DESTAPAR · `40b1b911`

1. **La data anava amb el locale del NAVEGADOR.** `toLocaleDateString()` pelat pintava
   `8/25/2026` al Chromium headless —i el que digués el navegador de cadascú a producció— dins
   d'una pantalla que ja està en català. Ara `CapcaleraRonda` rep el locale de l'app i el format
   `dd/mm/aaaa` de la casa, com fan `Planning`, `Models` i `ModelSheet`.
2. **El rètol de la safata deia «agrupats per model».** Ara diu «per model i per volta».
3. **El de la comanda deia «les línies i els preus no es poden editar»** sense nomenar l'excepció
   que M4 hi obre. Ara la nomena.

---

## 6 · EL BANC DE QA — i per què no és sobre `[QA-M1]`

`ops/qa/banc_m4_desbordament.py` · prefix **`[QA-M4]`** · idempotent · `--remunta`.

🔑 **El brief demanava el fum sobre `[QA-M1]`, i no s'hi pot fer.** Cap model d'aquell banc té
comanda —ni cap model de `fhort`, §1.b— i **sense comanda no hi ha numeral**, o sigui que el
desbordament no existeix. Enganxar una comanda a un model de `[QA-M1]` **mutaria el banc que els
fums d'M1, M1-bis, M2 i M3 segueixen consumint**. El banc d'M4 és germà del d'M1, **amb el MATEIX
`Customer`**, i per tant surt a la **MATEIXA safata**: el fum els veu tots dos alhora (v. la
captura `m4_b3`).

| | |
|---|---|
| Comanda | `SO-2026-0003` · línia amb **`rounds_included = 2`** · producte `qa-m4-servei` |
| `QA-M4-0001` | AMB comanda · 3 voltes · **la R3 desborda** |
| `QA-M4-0002` | **SENSE comanda** · 3 voltes · **cap desborda** (el control negatiu) |
| Albarà | un `DeliveryNote` DRAFT sintètic, **buit**, per poder obrir-hi la safata |

🔑 **Tot pel camí normal**: les voltes per `obrir_ronda`/`ronda_del_gest`, els estats per
`transition_task`, i **el veredicte el resol el codi de producte en obrir** — el banc **no escriu
`fora_de_comanda` a mà enlloc**. Un banc que el forcés no provaria res.

L'última volta de cada model es deixa **OBERTA**: és l'estat real d'una volta acabada de
treballar i encara no entregada, i la safata l'ha de saber ensenyar igualment.

---

## 7 · EL GATE

### 7.1 · `manage.py check` — net després de cada commit.

### 7.2 · Bloc RONDA sencer + els tests nous · **`Ran 269 tests` · `OK`**

```
venv/bin/python manage.py test \
    fhort.tasks.test_ronda fhort.tasks.test_tasca_vigent fhort.tasks.test_contracte_f2 \
    fhort.tasks.test_m1_entrega fhort.tasks.test_m1bis_fit4 \
    fhort.tasks.test_m3_fit11 fhort.tasks.test_m3_by_model fhort.models_app.test_m3_cicle_vida \
    fhort.tasks.test_m4_desbordament \
    --settings=fhort.settings_m4 --keepdb
```

### 7.3 · Bloc COMMERCE (rutes del R13) + els tests nous · **`Ran 55 tests` · `OK`**

```
venv/bin/python manage.py test \
    fhort.commerce.test_batch_assign fhort.commerce.test_gate_comercial \
    fhort.commerce.test_intents_reattach fhort.commerce.test_orphan_iva \
    fhort.commerce.test_unassign fhort.commerce.test_m4_safata_rondes \
    --settings=fhort.settings_m4 --keepdb
```

### 7.4 · `by_model` · **`Ran 31 tests` · `OK`**

```
venv/bin/python manage.py test fhort.tasks.test_m3_by_model --settings=fhort.settings_m4 --keepdb
```

`settings_m4` només canvia el NOM de la BD de test (`test_ftt_m4_comercial`):
`test_ftt_staging` és compartida entre sessions concurrents i `test_ftt_m3_cicle` és la d'M3.

### 7.5 · Els 25 tests NOUS, i què guarda cadascun

**`fhort.tasks.test_m4_desbordament` (16)**

| | |
|---|---|
| `NumeralEfectiuTest` (8) | els TRES «sense límit» distingibles · `0` no és «sense límit» · WO **orfe**, comanda **CANCELLED** i **COLLECTOR** no governen · mana el WO **OBERT** quan n'hi ha un de tancat |
| `MarcaEnObrirTest` (6) | dins del numeral no marca · **passar-lo marca i la numeració NO es toca (R3 segueix sent R3)** · numeral `0` desborda ja la R1 · **model sense comanda: cap volta desborda mai** · **el veredicte és una FOTO** (pujar el numeral no reescriu) · una R1 que ja existia no es re-resol a cada gest |
| `LaCaraDelTecnicNoCanviaTest` (2) | `RondaSerializer` no serveix cap camp nou · les tasques d'una volta desbordada neixen exactament igual |

**`fhort.commerce.test_m4_safata_rondes` (9)** — la tasca desbordada arriba a la safata · amb la
volta, les DATES i el perquè en peces · **la feina llegada (`ronda` NULL) no s'inventa cap ronda**
· **cap preu de volta es calcula** · el camí sencer `add_lines_to_draft` → `model_task` → ronda ·
albaranada, surt de la safata · llegir la safata no crea cap document.

### 7.6 · Frontend · `npm run build` verd · `npx eslint src` **0 errors** (274 warnings, totes preexistents)

### 7.7 · Fum HTTP · `ops/qa/qa_m4_comercial_http.py` · **25 OK · 0 FAIL**

Contra el **gunicorn del worktree** (`127.0.0.1:8141`, `--chdir /var/www/ftt-m4/backend`), mai
`ftt-staging.service` — que serveix un ALTRE arbre (llei `ftt-backend-desplegat-vs-disc`).
Cobreix: les portes (401 sense token) · el numeral servit i **editat per PATCH** · **buidar-lo és
`null`, no `0`** · **la irreversibilitat de B3b intacta** (`unit_price` no es mou) · el veredicte
que **no** es recalcula després de pujar i baixar el numeral per la porta · la porta de voltes del
tècnic **sense cap fuita** · la safata amb l'índex ordenat, la marca, el perquè i les dates · cap
preu calculat · llegir la safata no crea cap albarà.

### 7.8 · Fum de pantalla · `ops/qa/qa_m4_comercial_pantalla.py` · **17 OK · 0 FAIL**

Sobre el bundle REAL de `frontend/dist` i el mateix gunicorn.

| Captura | Què hi ha |
|---|---|
| `m4_a1_comanda_numeral.png` | la fitxa de `SO-2026-0003` amb la columna **VOLTES INCL.** i la cel·la editable a `2` |
| `m4_a2_numeral_desat.png` | el numeral editat a `4` i el toast «Numeral de voltes actualitzat.» |
| `m4_b1_albara_esborrany.png` | l'albarà DRAFT del banc |
| `m4_b2_safata_per_volta.png` | la safata sencera: `[QA-M1]` i `[QA-M4]` agrupats per volta |
| **`m4_b3_ronda_desbordada.png`** | **la peça**: `R3 · fora de comanda · 25/08/2026 → oberta` + `n>2 de la comanda SO-2026-0003: aquesta volta es factura a part.` — i just a sota, `QA-M4-0002` amb les seves 3 voltes **sense cap marca** |
| `m4_c1_cara_tecnic.png` | la fitxa del model desbordat: **cap rastre del desbordament** |

Mesures que valen la pena: el bloc del model sense comanda es mesura **PER DINS** (al `body`
sencer hi són tots dos i la mesura sortiria verda digués el que digués), i l'edició del numeral es
fa **de debò** (omplir + `Tab` = save-on-blur), no simulada.

### 7.9 · Migracions declarades i **auditades a la BD**

```
commerce  [X] 0021_quotelinemodelintent          tasks  [X] 0052_m1_rastre_reobertura
          [X] 0022_salesorderline_rounds_included       [X] 0053_ronda_fora_de_comanda_…
models_app [X] 0087_m3_cicle_vida_model  (intacte, M4 no el toca)
```

Aplicades amb `migrate_schemas` (mai `--schema`) i **les columnes comprovades directament a
`information_schema`** als dos tenants (llei de `CLAUDE.md`: django-tenants pot donar un OK
enganyós):

| schema | columnes |
|---|---|
| `fhort` | `commerce_salesorderline.rounds_included` · `tasks_ronda.{fora_de_comanda, linia_comanda_id, numeral_vigent}` |
| `los` | les mateixes quatre |

Totes **nullable o amb default**: additives i innòcues per al `ftt-staging.service` que segueix
corrent amb el codi d'abans.

---

## 8 · ELS 10 COMMITS (cap push)

| | |
|---|---|
| `10fb078c` | `chore(repo)` retirar `frontend/node_modules` del control de versions |
| `31864e69` | `feat(commerce)` FIT-5 — el numeral de voltes viu a la línia de COMANDA |
| `ca9947b1` | `feat(cara)` el numeral s'edita a la fitxa de comanda |
| `c85e44bc` | `feat(tasks)` FIT-12 — la Ronda sap si cau DINS o FORA del numeral |
| `9c5e7de1` | `feat(commerce)` FIT-12 — la volta viatja amb l'ítem de la safata |
| `ada361d1` | `feat(cara)` la safata d'albaranables s'agrupa PER VOLTA |
| `1943045d` | `test(m4)` el numeral, la marca en obrir i el camí d'encàrrecs (25 tests) |
| `3e72d92a` | `chore(repo)` ignorar els symlinks de `venv` i `.env` dels worktrees |
| `40b1b911` | `fix(cara)` la data va amb el locale de l'app, i dos rètols diuen la veritat |
| `03749af2` | `qa(m4)` banc + fum HTTP (25 OK) + fum de pantalla (17 OK) |

---

## 9 · QUÈ NO S'HA FET (i el brief ho demanava així)

Cap càlcul de preu de ronda · cap factura · **cap UI nova al tècnic** · cap watchpoint automàtic
(el canal segueix sent manual del responsable) · res del planificador · `patterns/**` i el model
`1383` **intocables** · cap `Entrega` nova (FIT-1) · **cap push**.

---

## 10 · RESUM DE 🚩 I DECISIONS PENDENTS

| # | Què | On |
|---|---|---|
| 🚨 **A** | **`frontend/node_modules` està trencat als 5 worktrees que el compartien.** El symlink autoreferent va substituir el directori real. Cada sessió ha de fer `npm ci` al seu worktree (aquí ja s'ha fet). El repo ja no els hi tornarà a posar | §0 |
| 🚩 **B** | **Pujar el numeral NO torna a dins les voltes ja obertes.** Decisió de disseny (la foto no es reescriu). Si Agus el vol automàtic, és peça nova | §3 |
| 🚩 **C** | **`get_billable_items` no toca el preu d'una volta desbordada**: proposa el del WorkOrder de la comanda, que és el preu *inclòs*. El brief prohibia calcular-ne cap; qui posa el preu d'una volta que va a part és el Salva, sobre el DRAFT. Si es vol una proposta diferent, és peça de preu i vol decisió | §4 |
| 🚩 **D** | **La pantalla literalment dita «Encàrrecs» (`WorkOrders.jsx`) NO llista voltes**: llista contenidors `WorkOrder`, i una volta desbordada no en fabrica cap. El desbordament surt a la **safata d'albaranables**, que és el camí que el brief identifica amb `fitxer:línia` | §1.d |
| 🚩 **E** | **A staging no hi ha ni una comanda real assignada a cap model** (0 `WorkOrder ORDER` als dos tenants; 0 `DeliveryNoteLine.model_task`). Tot el camí comercial model→comanda→albarà està **escrit i sense estrenar**. El banc `[QA-M4]` és avui l'única població que l'exercita | §1.b |
| 🚩 3 (M3) | `frontend/src/components/EstatBadge.jsx` sense importadors — **segueix oberta**, no tocada. Ull: n'hi ha un altre amb el mateix nom que SÍ és viu (`components/commercial/estats.jsx`) | §1.a |
| 🚩 4 (M3) | La columna «Estat» de `/models` pinta un guió — **segueix oberta**, no tocada | §1.a |
| ⏳ | L'excepció pre-llei de la 4a columna del board segueix **viva fins al retroactiu d'M5**, tal com M3 la va deixar | — |
