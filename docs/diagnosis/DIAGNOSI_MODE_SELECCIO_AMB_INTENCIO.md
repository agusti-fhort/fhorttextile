# DIAGNOSI — mode "selecció amb intenció" (llista de Models com a superfície universal de selecció)

Data: 2026-07-20 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`.

**Abast:** dimensionar el Sprint C — arribar a la llista de Models amb propòsit
(`?select_for=order_line:123 / quote_line:456`), multi-seleccionar fins a N, confirmar,
tornar a l'origen i saltar a la següent línia pendent; jubilant els dos pickers inline
(modal d'OrderDetail + picker de QuoteDetail/E6) units a la superfície nova.

**Base de fets:** ÚLTIM COMMIT de `dev` = `ba71c49` (hi ha una sessió Patró B en paral·lel
editant `Models.jsx`/`ModelFilter` SENSE commitar; els seus canvis NO es llegeixen). Tots els
`fitxer:línia` són del **blob de HEAD** (`git show HEAD:`), no del working tree.

**Convenció:** cada afirmació porta `fitxer:línia` (de HEAD). `"NO EXISTEIX"` = confirmat
absent al codi committat (no especulat). Propostes només al bloc `💡` final; les decisions
són humanes (Patró C).

---

## Resum executiu (les conclusions que desbloquegen el disseny)

1. **NO existeix cap precedent de "tornar d'on venies amb resultat"** fora del flux d'auth
   (`App.jsx:79` desa `state.from` → `Login.jsx:57` hi torna). El sistema té una preferència
   arquitectònica **explícita i documentada contra `location.state`/`navigate(-1)`** per a
   context (`FittingDetail.jsx:530-538`): el propòsit viatja per **query param** i el destí es
   reconstrueix de dades del servidor, no de l'historial. → la superfície nova ha d'usar
   query params (`?select_for=`, `?return=`), no `location.state`.

2. **El multi-select de Models ja té la infraestructura d'ids** (`selected` Set, toggle,
   comptador unificat `selCount`), però **NO té límit N, ni comptador "x/N", ni concepte de
   propòsit** — tot això NO EXISTEIX (`Models.jsx`). El mode conjunt "Gmail" (`selectAllFilter`,
   il·limitat) és **conceptualment oposat** a "limitat a N" i s'haurà de capar/ocultar en mode
   intenció.

3. **Els dos pickers són dues còpies inline del MATEIX patró** (QuoteDetail es declara rèplica
   d'OrderDetail), **sense cap component compartit** (`ModelPicker` NO EXISTEIX). Prefiltre idèntic
   (`customer` + `GET /api/v1/models/`), però **dues cardinalitats i dos endpoints** diferents:
   OrderDetail = single terminal → `assign-model`; QuoteDetail = multi-add amb exclusió de
   duplicats → `quote-line-intents`. La superfície nova ha de cobrir totes dues.

4. **"Pendent" està definit i és sòlid per a COMANDA** (`qty_allocated < quantity`, camps reals +
   guard), però **NO ESTÀ DEFINIT enlloc per a PRESSUPOST** (`QuoteLine` no té `qty_allocated`;
   ningú compta `intents vs quantity`). → **pregunta oberta per a l'Agus** (bloc P4).

5. **NO existeix cap batch d'assignació a comanda**: `assign-model` és estrictament single-model,
   transacció aïllada per crida, `qty_allocated` en read-modify-write **sense bloqueig de fila**,
   no idempotent. Confirmar N models = N crides en loop, amb risc de lost-update i assignació
   parcial. → un batch transaccional és el candidat natural si N pot ser gran (bloc P5).

---

## BLOC P1 · Navegació i estat de retorn

### Router i hooks
- **react-router-dom `^7.15.1`** (`frontend/package.json`, línia `react-router-dom`), muntat en
  **mode declaratiu clàssic** (NO data router): `App.jsx:240-242` usa `<BrowserRouter>` +
  `<Routes>`/`<Route>`, no `createBrowserRouter`/`RouterProvider`. Implica: `useNavigate`/
  `useLocation`/`useSearchParams` disponibles; `navigate(path,{state})` i `location.state` van sobre
  la History API (sobreviuen SPA + F5); NO hi ha `loader`/`action`/`useLoaderData`.

### `location.state` — ús mínim i deliberadament evitat
- Navegació amb `state` a tot el codi: NOMÉS `ResetPassword.jsx:33` (`navigate('/login',{state:{resetOk:true}})`)
  i `App.jsx:79` (`<Navigate to="/login" state={{from:location}}>`, guard d'auth).
- Lectors de `location.state`: NOMÉS `Login.jsx:57-58` (`state.from` → reconstrueix `pathname+search`)
  i `Login.jsx:61` (`state.resetOk`).
- **Rebuig explícit del patró**: `FittingDetail.jsx:530-538` reconstrueix el destí de sortida des de
  `session.convocatoria` (dades del servidor) i el comentari (`:534`) diu que **NO** usa `location.state`
  ni `navigate(-1)` a propòsit ("depenia de l'historial… i no transportava res").
- Retorn cec: `BackButton.jsx:10` (`navigate(-1)` per defecte), `PlanningCalendar.jsx:210`.

### Query param = patró canònic de propòsit/context
- `Models.jsx:39,42-46` — "URL = FONT DE VERITAT dels filtres… recarregar conserva l'estat".
- `ModelSheet.jsx:101-109` (`sp.get('tab')`, `task_id`, `fitting_session`, `mode`), `ModelWizard.jsx:37`
  (`?block=4`), `CustomerDetail.jsx:41` (`?tab=`), `TallerPatro.jsx:38-39`, `TechSheetEditor.jsx:1722`.
- **Patró "consumir el propòsit"**: `SizeLibrary.jsx:22-31` obre un drawer des de `?prefill=` i llavors
  **esborra el param** amb `setSearchParams(next,{replace:true})` (`:31`) perquè no es re-obri.
- Deep-link "arriba amb propòsit, actua, NO torna" (one-way per decisió explícita): `ImportWizard.jsx:230-232`
  navega a `/size-library?prefill=…`, comentari "decisió (ii): sense represa".
- Infraestructura `returnTo`/`?next=`/`?return=`/`redirect=`: **NO EXISTEIX** (cap coincidència).

**Veredicte P1:** el patró net i coherent amb el sistema és **query param** per al propòsit
(`?select_for=`) i, per al retorn, un `?return=<url>` explícit (o `location.state` a l'estil `Login`),
consumit amb `setSearchParams(replace:true)`. NO hi ha infraestructura de retorn reutilitzable: cal
crear-la. `navigate(-1)` està desaconsellat pel propi codebase.

---

## BLOC P2 · Anatomia del multi-select a Models.jsx (post-C2b, HEAD)

Fitxer `frontend/src/pages/Models.jsx` (433 línies al blob de HEAD).

### Selecció individual
- Estat: `const [selected, setSelected] = useState(() => new Set())` (`Models.jsx:33`) — Set d'ids.
- Toggle: `toggle(id)` (`:139`); models derivats `selectedModels = items.filter(m => selected.has(m.id))` (`:132`).
- Fila: `rowChecked(id)` (`:143`), checkbox a `ModelRow` (`:352`), marcat via `selected={rowChecked(m.id)}` (`:260`).

### Mode conjunt "Gmail" (C2/C2b)
- `selectAllFilter` (`:36`), `excludeIds` Set (`:37`).
- Comptadors: `filterCount = count − excludeIds.size` (`:136`); `selCount = selectAllFilter ? filterCount : selected.size` (`:137`).
- Banda "seleccionar els N del filtre" (`:228-259`), condició `(allOnPage||selectAllFilter) && hasMoreThanPage` (`hasMoreThanPage = count > items.length`, `:134`).
- Contracte a ActionsMenu: `selectionSet={selectAllFilter ? { filters: filterParams, excludeIds:[…], count: filterCount } : null}` (`:179`); `targets={selectAllFilter ? [] : selectedModels}` (`:178`).

### Convivència individual ↔ conjunt
- `rowChecked` (`:143`): en mode conjunt, marcat = NO exclòs. `rowToggle` (`:144-147`): edita `excludeIds` o `selected`. `toggleAll` (`:148-155`). Reset a `clearConjunt` (`:140`) i `afterAction` (`:156`); canvi de filtre invalida la selecció via `useEffect([filterKey])` (`:128`).

### Comptador visible
- Únic, a la capçalera (`:172`): `selCount>0 ? t('…selected',{n:selCount}) : t('…count',{n:count})`. **NO hi ha comptador "x/N"**.

### Què FALTA per a "selecció limitada a N"
- **NO EXISTEIX límit de selecció**: `toggle`/`rowToggle`/`toggleAll` afegeixen sense sostre (`:139,144,148`).
- **NO EXISTEIX comptador "x/N"** (el de `:172` és absolut, sense denominador).
- **NO EXISTEIX cap concepte de propòsit/destí**: cap `select_for`/`limit`/`max`/`purpose`/`pendent` al fitxer (grep buit). La selecció va genèrica a `ActionsMenu` (`:177-180`); `afterAction` (`:156`) només neteja i recarrega — cap "tancar i retornar a un origen".

### `?select_for=` conviuria amb els filtres
- `useSearchParams` (`:42`), `FILTER_KEYS` (`:15-21`), `filterParams` recull els keys presents (`:63-68`),
  `setParams` fa merge no destructiu (`:52-62`). Un `?select_for=`/`?select_max=`/`?return=` es llegiria
  amb `sp.get(...)` (com `:43-46`) i s'exclouria de `FILTER_KEYS` perquè no s'enviï al backend de list.

**Veredicte P2:** reutilitzable la maquinària d'ids i el punt únic de comptador (`:172`, fàcil →
"x/N"). Cal construir: límit N, comptador x/N, lectura del propòsit de la URL, i **desactivar el mode
Gmail** (banda `:228-259` + checkbox tota-la-pàgina `:220-223`) en mode intenció (és l'oposat de "limitat a N").

---

## BLOC P3 · Els dos pickers a jubilar (inventari fi per a paritat)

**Cap component compartit**: `ModelPicker` **NO EXISTEIX** (grep buit). Són dues còpies **inline**;
QuoteDetail es declara rèplica d'OrderDetail (`QuoteDetail.jsx:17,23,386`).

### A) Modal d'assignació — OrderDetail.jsx (SalesOrderLine)
- Obertura `openAssign(line)` (`OrderDetail.jsx:95-99`): reseteja filtres `pq{search,temporada,collection}` + `setAssign({line})`.
- **Prefiltre** server-side per client: `params={ customer: order.customer, ordering:'-data_entrada', page_size: PICK_PAGE }` (`:104`; `PICK_PAGE=40` `:29`) + search/temporada/collection opcionals (`:105-107`). **NO prefiltra per garment.**
- Fetch `modelsApi.list(params)` debounce 200 ms (`:110`), deps `[assign,pq,order?.customer]` (`:102-119`).
- **Single-select**: fila `setPicker(p=>({…,modelId:m.id}))` (`:329`); `sel` per `modelId` (`:327`). Un sol id.
- **Confirmació**: `doAssign()` (`:153-165`) → `commerce.orderLines.assignModel(line.id,{model_id})` → **`POST /api/v1/commerce/order-lines/{id}/assign-model/`** (`endpoints.js:463`). Crea WO ORDER + migra col·lector.
- **Refresc**: èxit → `setAssign(null)` (tanca) + `reload()` (recarrega comanda/qty_allocated) + feedback `work_order.number`+warnings (`:158-162`). Avís "+N més" si `picker.count>models.length` (`:342-344`); sense paginació navegable.

### B) Picker d'intents — QuoteDetail.jsx (QuoteLine, E6)
- Modal inline dins `LinesSection`; estat `intentLineId` + `picker{models,count,loading,modelId}` (`:238-240`).
- Obertura `openIntent(lineId)` (`:268-272`); **prefiltre** `customer: quote.customer` (`:276`), mateix `PICK_PAGE=40` (`:36`), mateixos opcionals.
- Fetch `modelsApi.list` debounce 200 ms (`:282`), deps `[intentLineId,pq,quote.customer]` (`:274-291`).
- **Single-click però multi-add**: fila `setPicker(…modelId:m.id)` (`:419`); la llista **exclou els ja intencionats** via `existingIds` (`:320`, filtrat `:414-416`) perquè `unique_together` no admet duplicats.
- **Confirmació**: `addIntent()` (`:294-299`) → `commerce.quoteLineIntents.create({quote_line,model})` → **`POST /api/v1/commerce/quote-line-intents/`** (`endpoints.js:447`). Esborrar: `delIntent` → `DELETE …/quote-line-intents/{id}/` (`endpoints.js:449`; UI `:301-303`).
- **Refresc**: èxit → `reload()` i **manté el modal obert** netejant només `modelId` (`:298`) per encadenar; tanca manual (`setIntentLineId(null)`, `:435`).

### C) Comparativa (per a paritat)
- Patró comú idèntic: forma d'estat `picker`, `PICK_PAGE=40`, `modelsApi.list` amb `customer`+`ordering:'-data_entrada'`+debounce 200 ms+search/temporada/collection, estils inline duplicats.
- Divergències: (1) **cardinalitat** — Order = single terminal (assigna 1, tanca, crea WO); Quote = multi-add persistent amb exclusió de duplicats; (2) **endpoint** — `assign-model {model_id}` vs `quote-line-intents {quote_line,model}` (+DELETE); (3) **refresc** — Order tanca, Quote manté obert.

**Veredicte P3:** la superfície nova ha de suportar **les dues cardinalitats** (single terminal +
multi-add amb exclusió de duplicats) i **els dos endpoints de confirmació**, sobre el mateix prefiltre
`customer` + `GET /api/v1/models/`. Jubilar = esborrar dues còpies inline, cap component compartit a mantenir.

---

## BLOC P4 · "Següent línia pendent" — definició exacta

### Comanda (SalesOrder) — definit i NO ambigu
- `SalesOrderLine` (`commerce/models.py:369-390`) hereta `AbstractDocumentLine` (`commerce/models_base.py:68`):
  - `quantity` `DecimalField(default=1)` (`models_base.py:80`) — comandada, MAI editable per API (B3b).
  - `qty_allocated` `DecimalField(default=0)` (`commerce/models.py:374-375`) — imputada (≤ quantity), única mutació.
- **`qty_allocated` es mou només per servei** (cap signal): +1 assignar (`commerce/services.py:323-324`), −1 desassignar (`:362-364`), +1 reattach (`:410-411`), sempre en passos d'1.
- **"Pendent" (comanda) = `qty_allocated < quantity`, CONFIRMAT al codi**: guard dur `services.py:299-300`
  ("ja té tota la quantitat imputada"); `reattach-candidates` ho documenta literalment (`views.py:374`) i
  ho calcula (`:382`); el detall de línia exposa `pct_allocated` (`views.py:235,254-255`).

### Pressupost (Quote) — NO DEFINIT (ambigu)
- `QuoteLine` (`commerce/models.py:255-282`) hereta `AbstractDocumentLine` → **TÉ `quantity`** (`models_base.py:80`),
  però **NO té `qty_allocated`** (confirmat al docstring `commerce/models.py:287`: "NO toca qty_allocated (que ni existeix a QuoteLine)").
- `QuoteLineModelIntent` (`commerce/models.py:284-315`): FK `quote_line` `related_name='model_intents'` (`:298`),
  FK `model` (`:299-300`), camp `qty` informatiu default 1 (`:301-302`), `unique_together=[('quote_line','model')]` (`:310`).
  Intenció pura: no crea WO, no toca cartera (`:284-287`). **0..N models diferents per línia.**
- **"Pendent" (pressupost) = NO DEFINIT AL CODI.** No hi ha CAP càlcul `count(intents) vs quantity` a
  `views.py`/`services.py`/`serializers.py`. El `QuoteLineModelIntentViewSet` és CRUD pla (`views.py:174-185`),
  sense `@action` de "pendents". El serializer de `QuoteLine` exposa `model_intents` com a llista sense flag
  de completitud (`serializers.py:162-173`). Les dues lectures del brief — (a) línies sense CAP intent, o
  (b) `count(intents) < quantity` — **cap està implementada**.

**Veredicte P4:** comanda = "pendent" sòlid i reutilitzable (`qty_allocated < quantity`). Pressupost =
**pregunta oberta per a l'Agus** (vegeu 💡/❓): cal DECIDIR la semàntica de "pendent" (sense intents vs
intents<quantity) abans de construir el "salt a la següent línia" per a ofertes.

---

## BLOC P5 · Confirmació de selecció (loop vs batch)

- **Endpoint únic (single)**: `SalesOrderLineViewSet.assign_model` (`commerce/views.py:258-276`),
  `@action(url_path='assign-model')`, gate CONFIGURE, body `{model_id}` (un sol model, `:266-269`),
  delega a `assign_model_to_order_line(model,line,user)` (`commerce/services.py:281`), retorna 201 + WO.
- **NO EXISTEIX batch d'assignació a comanda**: l'únic `assign` és el single (`views.py:258`); l'únic
  `*-bulk` del mòdul és `mark-invoiced-bulk` de DeliveryNote (`views.py:531-533`), no relacionat.
  Assignar N models = **N crides single en loop des del client**.
- **Cost/risc del loop** (fets sobre `assign_model_to_order_line`):
  1. **Transacció per crida, no global**: cada crida obre el seu `transaction.atomic()` (`services.py:310`);
     N crides = N transaccions → si la 3a falla, les 2 primeres queden compromeses (assignació parcial).
  2. **`qty_allocated` read-modify-write sense bloqueig**: llegeix, +1, desa (`services.py:323-324`); sense
     `select_for_update` → risc de **lost update** si el client envia amb `line` ranci o en paral·lel.
  3. **Guard de saturació per crida**: talla a `qty_allocated >= quantity` (`services.py:299-300`); no hi ha
     pre-validació de "cabrien N alhora".
  4. **No idempotent**: cada èxit crea un WO nou i +1; reintentar duplica. Fre indirecte: bloqueig si el
     **mateix model** ja té WO ORDER OPEN (`services.py:301-302`).
  5. **Efecte secundari ×N**: cada assignació migra tasques del col·lector al nou WO (`services.py:326-337`).

**Veredicte P5:** avui single-model, aïllat, no idempotent, sense bloqueig de fila. Per a N gran, el loop
client és fràgil (parcial + lost-update). Un **batch transaccional** (N models → 1 línia, una transacció,
`select_for_update`, validació de capacitat conjunta) NO EXISTEIX i seria el candidat natural.

---

## TAULA FINAL — EXISTEIX / FALTA / DIFERENT (per al CTO)

| Tema | Estat | Àncora (HEAD) |
|---|---|---|
| Retorn "amb resultat" a l'origen | **NO EXISTEIX** (només auth `from`) | `App.jsx:79` · `Login.jsx:57` |
| `location.state` per a context | **DESACONSELLAT pel codebase** | `FittingDetail.jsx:530-538` |
| Query param de propòsit (patró canònic) | **EXISTEIX** | `Models.jsx:39` · `SizeLibrary.jsx:22-31` |
| Infra `?return=`/`?next=` | **NO EXISTEIX** | (grep buit) |
| Multi-select per ids | **EXISTEIX** | `Models.jsx:33,139,132` |
| Límit de selecció N | **NO EXISTEIX** | `Models.jsx:139,144,148` |
| Comptador "x/N" | **NO EXISTEIX** (només absolut) | `Models.jsx:172` |
| Concepte de propòsit/`select_for` | **NO EXISTEIX** | `Models.jsx` (grep buit) |
| Mode Gmail vs "limitat a N" | **DIFERENT (oposats)** | `Models.jsx:228-259,220-223` |
| Component picker compartit | **NO EXISTEIX** (2 còpies inline) | `OrderDetail.jsx` · `QuoteDetail.jsx:17` |
| Picker Order: single + `assign-model` | **EXISTEIX** | `OrderDetail.jsx:153-165` · `endpoints.js:463` |
| Picker Quote: multi-add + `quote-line-intents` | **EXISTEIX** | `QuoteDetail.jsx:294-299` · `endpoints.js:447` |
| "Pendent" comanda (`qty_allocated<quantity`) | **EXISTEIX i sòlid** | `commerce/models.py:374` · `services.py:299` |
| "Pendent" pressupost | **NO DEFINIT (ambigu)** ❓ | `commerce/models.py:287` · `views.py:174-185` |
| Batch d'assignació a comanda | **NO EXISTEIX** | `commerce/views.py:258,531` |
| Assignació idempotent / amb bloqueig | **NO EXISTEIX** | `commerce/services.py:310,323` |

---

## ❓ PREGUNTA BLOQUEJANT PER A L'AGUS (Patró C)

**Què és una "línia de PRESSUPOST pendent"?** El codi no ho defineix (`commerce/models.py:287`,
`views.py:174-185`). Dues semàntiques possibles, cap implementada:
- (a) **Sense cap intent**: `count(model_intents) == 0` → "pendent" fins que hi ha ≥1 model vinculat.
- (b) **Intents < quantity**: `count(model_intents) < quantity` → "pendent" fins a omplir la quantitat.

La comanda usa (b) de fet (`qty_allocated < quantity`), però el pressupost és intenció pura (multi-model
sense sostre de quantity avui). **Cal la decisió abans de construir el "salt a la següent línia pendent"
per a ofertes.**

---

## 💡 PROPOSTES (a validar — decisió humana, Patró C)

> Hipòtesis de disseny derivades dels fets. Res decidit.

1. **💡 Propòsit i retorn per query param** (coherent amb el patró canònic, P1):
   `?select_for=<order_line|quote_line>:<id>&select_max=<N>&return=<url>`. Llegir amb `sp.get(...)` a
   `Models.jsx` (com `:43-46`), excloure'ls de `FILTER_KEYS`, i **consumir-los amb `setSearchParams(replace)`**
   com fa `SizeLibrary.jsx:31`. Evitar `location.state`/`navigate(-1)` (desaconsellats, P1).

2. **💡 Mode intenció al Models.jsx** derivat de `select_for`: quan és actiu, (a) **capar `selected` a N**
   (`select_max`) al `toggle`/`rowToggle` (`:139,144`), (b) convertir el comptador de `:172` en **"x/N"**,
   (c) **ocultar el mode Gmail** (banda `:228-259` + checkbox tota-la-pàgina `:220-223`) perquè és l'oposat
   de "limitat a N", (d) mostrar una barra de confirmació "Confirmar (x/N)".

3. **💡 Prefiltre del propòsit**: en mode `select_for`, injectar `customer=<de la línia>` als filtres (paritat
   amb els pickers, P3) — probablement com a filtre bloquejat/prefixat a la URL, reutilitzant el panell de
   filtres avançats que ja existeix.

4. **💡 Un sol camí de confirmació amb dues cardinalitats** (paritat P3): `order_line` → assignació terminal;
   `quote_line` → multi-add amb exclusió dels ja-intencionats (`QuoteDetail.jsx:320,414-416`). En confirmar,
   tornar a `return` i que l'origen (OrderDetail/QuoteDetail) calculi i salti a la següent línia pendent.

5. **💡 Batch d'assignació a comanda** (mitiga P5): un endpoint `POST order-lines/{id}/assign-models`
   `{model_ids:[…]}` en UNA transacció amb `select_for_update` sobre la línia i validació de capacitat
   conjunta (`sum ≤ quantity − qty_allocated`), reusant `assign_model_to_order_line` per model dins la
   transacció. Evita el loop client fràgil (parcial + lost-update) quan N és gran. Per a intents de
   pressupost, un batch anàleg de `quote-line-intents` és menys crític (no toca cartera) però simètric.

6. **💡 Definició de "següent línia pendent"** (depèn de la ❓): comanda = primera línia amb
   `qty_allocated < quantity` (P4, ja calculable); pressupost = segons la decisió (a)/(b) de l'Agus. El càlcul
   de "següent" pot viure a l'origen (OrderDetail/QuoteDetail ja tenen les línies carregades) o exposar-se com
   a `@action` de la comanda/oferta si es vol server-side.
