# ORDRE · LOT 09/09 — nom · ronda-comerç · reactivitat Salva · 25' · paperera · encàrrecs

**Patró B · IMPLEMENTACIÓ A STAGING.** Protocol PROTOCOL_IMPLEMENTACIO.
**Base:** `935991db` · **branca:** `dev` · **19 commits locals, CAP PUSH.**
**Migracions:** **0** — cap fitxer sota `migrations/` al diff.
**Zones intocables:** `assessment/`, `trading/`, `webs/`, nginx — **cap tocada** (verificat al `git diff --name-only`).
**Precedents llegits:** `DIAGNOSI_ALBARA_COMANDA_DOMINI.md` · `DIAGNOSI_REACTIVITAT_FRONT.md`.

---

## PAS 0 · VERIFICACIÓ (sense escriure)

### 0a · Estat de partida
```
git pull → Already up to date
HEAD     → 935991db  merge(f43): costures assistides…
branca   → dev
```

### 0b · ⚑ ¿Existeix «desassignar de ronda»? ¿És nul·lable? ¿Hi ha porta?

| pregunta | resposta | evidència |
|---|---|---|
| `ModelTask.ronda` és NUL·LABLE? | **SÍ** | `tasks/models.py:337` — `ForeignKey('Ronda', on_delete=SET_NULL, null=True, blank=True)` |
| ¿Cal migració per buidar-la? | **NO** | el camp ja admet `NULL` |
| ¿Existeix l'operació? | **NO** | cap servei ni acció la buida (`grep` de `ronda = None` → 0 encerts fora de tests) |
| ¿Es pot fer per PATCH? | **NO** | `ronda` és a `read_only_fields` (`serializers_b.py:93`, *«La genealogia l'escriu obrir_ronda, mai el client»*) — un PATCH la **descartaria en silenci amb 200 OK** |

> **VEREDICTE 0b: POSITIU amb matís.** El camp és nul·lable → **cap migració** → el commit 6
> segueix. Però la porta **no existia** i calia fer-la, cosa que el brief ja autoritzava
> («si cal endpoint nou de desassignar → fes-lo mínim»).
>
> 🚨 **El parany que hi havia:** la primera lectura del `read_only_fields` va sortir TRUNCADA i
> semblava que `ronda` fos escrivible. Si m'ho hagués quedat així, hauria cablejat un
> `PATCH {ronda: null}` que **retorna 200 i no escriu res** — la família de defectes silenciosos
> que aquesta casa ja té documentada. Es va veure rellegint el bloc sencer.

### 0c · Els dos ancoratges del fix de reactivitat

| | esperat | trobat |
|---|---|---|
| `planChanged` | `endpoints.js:7` | ✅ `endpoints.js:7-10`, pass-through de la resposta |
| `openTask` l'emet | — | ✅ `endpoints.js:99-101`, `.then(planChanged)` |
| `refrescaTot()` | `WorkPlan.jsx:248` | ✅ exactament a `:248` |

---

## ELS 11 COMMITS

| # | sha | concern |
|---|---|---|
| 1 | `36b81ff1` | BE · `WorkOrderSerializer` → `model_nom` + `model_collection` |
| 2 | `89a49def` | BE · `RondaSerializer` → `fora_de_comanda`, `linia_comanda`, `numeral_vigent`, `comanda` |
| 3 | `48a63624` | FE · **el cas d'en Salva** (C1 + C2 + C3 + la quarta peça) |
| 4 | `982ac6a2` | FE · xip «fora de comanda» al contenidor de ronda |
| 5 | `dff735fb` | FE · 25' per defecte a la captura d'estimació |
| 6 | `e8df2a16` | BE · `desassignar-ronda` + vincle comercial al compositor |
| 7 | `5c3df895` | FE · la paperera del contenidor de ronda |
| 8 | `9abbf388` | BE · `search_fields` a la llista d'encàrrecs |
| 9 | `c9372584` | FE · pantalla d'encàrrecs (llista + detall) |
| 10 | `d3d53e82` | BE · `close-bulk` |
| 11 | `bc5ada4f` | FE · «Tancar seleccionats» |
| 12 | `cf134e53` | FE · conformitat de pell (guàrdia UI) |
| 13 | `470f27c5` | BE · poda del número de comanda + validació d'`ids` (revisor-diff) |
| 14 | `4555a15e` | FE · la regressió del model ranci i la passada seca (revisor-diff) |
| 15 | `194ca6d9` | FE · la llista d'encàrrecs s'obre pels OBERTS (§8e) |
| 16 | `1291b168` | FE · la fila torna a UNA línia (§8e) |
| 17 | `f26f91e8` | QA · l'instrument: àncores de senyal + corredor bidireccional |
| 18 | `79bb2f2d` | FE · els dos defectes de crom que la bidireccional ha mesurat |
| 19 | `f2c3e9bd` | QA · els dos diàlegs de paperera entren a la mesura |

Els commits 12-14 surten de la revisió (§GUARDIANS); el 15 i el 16 són l'**esmena** que tanca
les dues coses que aquell report deixava a decisió d'Agus; el 17-19 són la **mesura** que la §8d
exigeix i que fins ara no s'havia pogut fer.

---

## COMMIT 3 · EL CAS D'EN SALVA — i una correcció a la meva pròpia diagnosi

### 🚨 CORRECCIÓ A `DIAGNOSI_REACTIVITAT_FRONT.md` §Q2

La diagnosi afirmava que el contenidor no apareixia **fins a l'F5**. Implementant-ho he trobat
un forat en aquell raonament: `DashboardTab.load()` posa `loading=true`, i el retorn primerenc
`if (loading)` (`DashboardTab.jsx:133` a la base) **desmuntava el `WorkPlan` a cada refresc**.
En remuntar-se, el `WorkPlan` tornava a demanar `/rondes/` sol.

**Què vol dir això:**
- La part de la diagnosi sobre **el mecanisme** (dues fonts, dos canals, i el creuador que
  s'empassa files) **és correcta i està verificada amb tests**.
- La part sobre **la permanència** estava sobredimensionada: pels gestos que passen DINS del
  `WorkPlan`, el símptoma era un **parpelleig i un desquadrament transitori**, no un estat
  ranci fins a l'F5. La permanència real es queda als camins que escriuen des de **fora** del
  Dashboard (`ModelSheet:483/525/811`, `TallerPatro`, `PropagatedEditor`), que és el que tanca C1.

**El fix no canvia, però guanya una quarta peça sense la qual les altres tres eren INERTS:**
`if (loading && !data)`. Sense això, el bump de `versio` i l'oient nou arribaven a un component
que ja no existia — i l'usuari perdia el col·lapse de les voltes a cada gest.

### Les quatre peces

**C1 · oients de `plan:changed`** — `DashboardTab` era un LECTOR PUR sense cap nansa
d'invalidació (`load` no s'exporta; l'únic que la rebia era el fill). `wpVersion` ho *semblava* i
només re-clavava el `WatchpointsPanel`. Ara els dos hi estan subscrits, cadascun refrescant
**només la seva font**, amb el mateix patró que els tres oients que ja hi havia.

**C2 · els cinc gestos de tasca** passen de `onRefresh?.()` a `refrescaTot()`. Hi convivien dos
vocabularis: els tres gestos de VOLTA feien les dues fonts, els cinc de TASCA només una. No era
descuit — són de P3/P4a i van néixer **abans** que M2 afegís la segona font.

> 🔑 **LLEI:** *afegir una segona font a una pantalla obliga a reobrir els gestos que ja hi vivien.*

**C3 · `agrupaPerRonda` no s'empassa cap fila** (`utils/rondes.js:158-171`). Els blocs es
construeixen des de `voltes`: una fila amb `ronda_seq = N` absent de la llista no queia a
`orfes` (la guarda mira `== null`) ni tenia bloc → **desapareixia amb 200 OK**. Ara va al bloc
`orfes`, ordenada per seq.

### Els tests, vistos VERMELLS

`utils/rondes.test.js` — 10 tests amb `node:test` (el que fa la casa; **no hi ha vitest** al
`package.json`, cosa que la primera versió del fitxer donava per feta i era falsa).

```
contra el codi de 935991db :  5 pass · 5 fail
contra el codi del commit  : 10 pass · 0 fail
```

Els 5 vermells són exactament els dos casos d'en Salva i les seves vores. Els 5 que ja eren
verds hi segueixen: cap contracte antic s'ha mogut.

---

## CURLS (staging · `Host: staging.fhorttextile.tech` · JWT amb claim `tenant_schema`)

### Commit 1 — el nom a l'encàrrec
```
GET /api/v1/commerce/work-orders/            → 9 WO
  WO-2026-0007  ORDER      model_nom='[QA-M4] Amb comanda · R3 desborda'  model_collection=''
  WO-2026-0001..0009 (8×)  COLLECTOR  model_nom=None  model_collection=None   ← correcte:
      la constraint `collector_no_model_no_orderline` els prohibeix tenir model
```

### Commit 2 — el veredicte de numeral
```
GET /api/v1/models/1497/rondes/     (model amb comanda, numeral 2)
  R1  fora_de_comanda=False  numeral_vigent=2  linia_comanda=15  comanda='SO-2026-0003'
  R2  fora_de_comanda=False  numeral_vigent=2  linia_comanda=15  comanda='SO-2026-0003'
  R3  fora_de_comanda=TRUE   numeral_vigent=2  linia_comanda=15  comanda='SO-2026-0003'

GET /api/v1/models/{1383,1499}/rondes/   → tot null/False, sense soroll
```

### Commit 6 — les dues portes
```
POST model-task-items/687/desassignar-ronda/     (wo=40 COLLECTOR, ronda=121)
  → 200  {"id":687,"ronda":null,"ja_fora":false,"encarrec":40}
  rellegida: ronda=None · work_order=40 · status=Pending      ← NO s'ha esborrat
  2a crida → 200 {"ja_fora":true}                             ← idempotent
  ESTAT RESTAURAT a ronda=121 en acabar

POST model-task-items/362/desassignar-ronda/     (Paused)
  → 409  {"code":"task_not_pending"}

GET  /api/v1/models/1496/dashboard/   → task 707  encarrec=None  comanda=None
DELETE model-task-items/707/          → 204   ·   rellegida → 404
GET  /api/v1/models/1494/dashboard/   → task 687  encarrec=40  comanda=None (un col·lector no té venda)
```
> La 707 era una tasca **d'usar i llençar** creada per al curl. **Cap dada real esborrada.**

### Commit 8 — la cerca
```
?search=desborda            → 1   (WO-2026-0007, pel NOM del model)
?search=FHORT Textile Tech  → 4   (pel client)
```

### Commit 10 — el lot
```
[40,41,99999] cancel_pending=false → 200
  40 blocked  blockers=[685 Paused, 675 Paused]  pending_proposals=[687,700]
  41 blocked  blockers=[376,690,691 Paused]
  99999 not_found  ·  tancats=[]              ← res destruït, i el parcial es diu per ítem

[45,46] cancel_pending=false → 45 ok · 46 pending (amb la seva proposta)
[45,46] cancel_pending=true  → 45 ok ja_tancat=true (idempotent) · 46 ok
  verificat a la BD: DEDUCTION creat sobre la tasca 708, tasca deslligada
  (work_order=None) i encara Pending   ← esborrar i deduir NO s'han fos
[47] amb 2 Pending → deduides: 2
```
> **`deduides` s'ha vist MENTINT abans de commitar.** Comptava
> `len(pending_proposals)` de la resposta, que ve **buit** quan el WO tanca de debò → deia
> sempre 0 mentre deduïa. Es compta ara **abans** de tancar, i re-mesurat dona 2.
>
> Els WO 45/46/47 eren **d'usar i llençar**; s'han esborrat amb els seus adjustments.
> Estat final: **els 9 WO de sempre**, cap adjustment ni tasca efímera.

---

## ⚑ ATURADA DEL BRIEF VERIFICADA I DESCARTADA (commit 8)

> *«Si `cancel_pending` en lot té efecte no previst (p. ex. tasques d'altres WO) → ATURA.»*

**No n'hi ha.** `close_work_order` parteix de `tasks = list(work_order.tasks…)`
(`commerce/services.py:249`) i `cancel_pending` només recorre les `Pending` **d'aquesta llista**.
Cap camí toca tasques d'un altre encàrrec. **El commit segueix.**

---

## LA PORTA DEL VERD

*(mesurada de nou al final de l'esmena, sobre els 19 commits)*

| control | resultat |
|---|---|
| `manage.py check` | **net** — 0 issues |
| `npm run build` | **verd** |
| `node --test utils/rondes.test.js` | **10 / 10** |
| `eslint` sobre els fitxers JS/JSX del lot | **0 errors · 6 warnings** |
| **auditoria de computats + bidireccional** | **17 casos · 1 desviació** (i és de la maqueta) |
| migracions | **0** |
| zones intocables | **cap tocada** |

**Els 6 warnings són EXACTAMENT els 6 que ja hi havia a `935991db`** — mesurat llançant
l'eslint sobre les versions base dels mateixos quatre fitxers: mateixes regles, mateixos
fitxers, només desplaçats de línia per les insercions.

```
935991db : 6 warnings   ·   HEAD : 6 warnings   ·   introduïts pel lot: 0
```

Un warning **sí que era meu** i es va tancar abans del commit 9: un
`useEffect(() => setTriats(new Set()), [...])` a `WorkOrders.jsx`. La correcció no va ser
silenciar-lo sinó moure el buidat **al gest** (`setParams`), que a més és més correcte: la tria
s'ha de perdre quan canvia el conjunt, i això ho ha de dir el gest, no un efecte que ho endreci
després.

### El desplegat és el commitat (les dues lleis de la casa)

> *«el gunicorn serveix el codi de quan va arrencar»* i *«staging serveix `frontend/dist`:
> `npm run build` ÉS desplegar»*. Les dues, mesurades i no suposades:

```
gunicorn reiniciat   : 2026-09-09 08:00:00   ·  últim canvi BE al disc : 07:59:58  → OK
frontend/dist/ escrit: 2026-09-09 08:05:36   ·  últim commit FE        : 08:02:40  → OK
```

---

## GUARDIANS — què han vetat i què s'ha corregit

### 🟢 guàrdia-i18n · **VERD**, cap veto
4.926 claus idèntiques als tres fitxers. Cap literal de cara a l'usuari; `title`, `aria-label` i
`placeholder` també per `t()`. Els codis de domini (`ORDER`/`COLLECTOR`, `OPEN`/`CLOSED`,
`Pending`) segueixen sent tokens en cru.
**Va trobar una clau morta que jo no havia vist:** `workorders.col_target` (v. §ANOTAT).
Ratifica la reutilització de les tres claus de `deliverynotes` via helper compartit, amb un
avís que faig meu: *el nom del namespace ara menteix* — la frase la pinta el Pla, no la safata.
El dia que es reanomeni a `rondes.*` ha de ser **al mateix commit que els dos lectors**, mai una
còpia que deixi dues veritats.

### 🟡 guàrdia-ui · **BLOQUEJAT per manca de mesura** — 4 incompliments corregits (`cf134e53`)
No ha pogut córrer l'auditoria de computats ni la bidireccional (calen token de QA i pantalles
vives). **Sense això no hi ha VERD possible per la §8d, i el lot NO el reclama.** De la lectura
del diff, però, van sortir quatre coses reals, totes al gest destructiu:

| | què deia la NORMA | què hi havia |
|---|---|---|
| 🔴 | §8e: «Paperera per fila: **icona destructiva 14**, hover `--err-bg`» | la paperera reusava `TransportMini` tal qual: `--text-soft` a 11px, **la mateixa pell que Play/Pause/Stop** a la mateixa línia |
| 🔴 | §5.5: «el vermell ple **només a la confirmació final**» | «Esborrar la tasca» i «Tancar i deduir» sortien **blaus**: `Modal` cablejava `botoPri` i no exposava variant |
| 🟠 | §8e: «Checkbox amb accent `--gold`» | caselles amb el blau del sistema operatiu |
| 🟠 | §1: `--sel` va amb **filet d'or a l'esquerra** | la barra de selecció portava vora `--gold-border` de la volta sencera (llenguatge de *porta*, no de selecció) |

Les dues citacions dures són verbatim de `ops/maquetes/NORMA_LAYOUT.md:131` i `:78`.
🔑 La cara **lligada** de la paperera es queda blava a posta: treure una tasca de la volta la
conserva sencera i no és destructiu.

**I em va enxampar un comentari que mentia:** deia que els tabs «fixen quin ordre tenen a la
barra» i el `map` no en fixava cap — prenia el que tornés `/vocabulari/`, o sigui que la barra
podia dir «Tancats · Oberts» sense que res fallés.

### 🔴 revisor-diff · dues 🔴, dues 🟠 i una 🟡 — totes corregides (`470f27c5` + `4555a15e`)

**1 · 🔴 UNA REGRESSIÓ MEVA, la més greu del lot.** El `if (loading && !data)` del commit 3
—sense el qual la resta d'aquell tram era inert— obria una finestra que no havia vist: la ruta
`models/:id` **no porta `key`** (`App.jsx:457`) i `DashboardTab` tampoc. Anar de `/models/100` a
`/models/200` canvia la **prop** `modelId` sense desmuntar res, i amb `data` encara ple de
l'anterior la condició era falsa: **la fitxa del 200 pintava el «On sóc», els artefactes i el
Pla del 100**, i el `WorkPlan` rebia les tasques del 100 amb `modelId=200` — un Play hi hauria
operat sobre la tasca d'un altre model.
La pregunta correcta no era «hi ha dades?» sinó «hi ha dades **d'aquest** model?».

**2 · 🔴 EL LOT ERA MÉS DESTRUCTIU QUE EL GEST QUE DEIA REPLICAR.** El tancament individual no
dedueix mai a la primera: va sense `cancel_pending`, el backend respon 409 amb
`pending_proposals` i **la fitxa ensenya quines tasques es deduiran** abans que ningú confirmi.
El lot tenia `cancel_pending:true` cablejat: marcar la casella de capçalera i prémer volia dir
deduir totes les Pending de N encàrrecs **sense haver dit mai quantes**, i el número només
sortia al toast, quan ja no hi ha marxa enrere.
Ara el diàleg fa primer la **mateixa crida amb `cancel_pending:false`** —que no escriu res— i
diu **tres números mesurats**: quants es tancaran, quants no i per què, i quantes tasques
quedaran deduïdes. Si la passada seca falla, confirmar es queda apagat.
*Verificat contra la BD que la passada seca no escriu: WO 40/41 segueixen `OPEN`, 0 DEDUCTIONs.*

**3 · 🚨 UNA TRAMPA QUE C3 I LA PAPERERA VAN OBRIR JUNTES**, i que cap dels dos tenia sol. Des
de C3, una tasca que reclama una volta que no ens ha arribat cau al bloc «SENSE VOLTA» —que és
el que volem— i aquell bloc **no és `segellada`** perquè no té ronda. Amb la paperera oberta
allà, una tasca **viva** de la R3 es llegia com a brossa d'un model llegat i, com que el seu
`encarrec` ve del **mateix payload que sospitem ranci**, el diàleg oferia «esborrar» dient «no
la reclama ningú»: un DELETE real sobre una premissa que la pantalla acabava de declarar
incerta. **Al bloc orfe ja no hi ha paperera.**

**4 · 🟠 EL NÚMERO DE COMANDA VIATJAVA A TOT USUARI AUTENTICAT.** `comanda` és el
`document_number` d'una venda i el compositor és `IsAuthenticated`. És el patró exacte de la
llei de lectura comercial sense gate, i la sortida de la casa és **podar el camp**, no tancar la
porta. Mesurat: admin → `'SO-2026-0003'`; Marta (`execute_tasks`+`schedule_fittings`, sense
COMERCIAL) → `None`, amb `encarrec=42` als dos casos. `encarrec` no es poda: és l'id intern del
contenidor de feina i és el que la cara necessita per triar el camí del gest.

**5 · 🟠 L'oient de `plan:changed` llençava la nansa de cancel·lació** de `load()`, o sigui que
cap fetch obert per un esdeveniment no es podia avortar mai.

**6 · 🟡 `close-bulk` no validava `ids`.** `{"ids":["12"]}` trobava el WO al queryset però
`trobats.get("12")` fallava (claus int) → deia `not_found` **d'un encàrrec que el mateix request
acabava de llegir**: una mentida amb 200 OK. Un escalar petava amb 500. Ara valida com el germà
`assign_models`, amb sostre de 200. Mesurat: `{"ids":["40"]}` → `id=40, WO-2026-0005, blocked`.

**El revisor confirma, i ho recullo:** cap migració necessària (els tres camps de `Ronda` són a
`tasks/migrations/0053`, anterior al lot) · permisos de `desassignar-ronda` i `close-bulk`
**correctes** i idèntics als seus germans · cap `addEventListener` sense el seu `remove` · cap
bucle de hooks · **cap regressió al Registre d'activitat** (l'altre consumidor d'`agrupaPerRonda`):
els passos que abans desapareixien ara surten sota «sense volta», que és millor.

**Un punt seu que NO faig meu:** marca com a *scope creep* que el commit 9 porti els tabs i la
meitat frontend de la cerca. No ho és — el brief posava explícitament «cercador a
l'encapçalament · tabs Oberts/Tancats · caselles» **dins del commit 7**. El revisor no tenia el
brief al davant.

---

## ESMENA · les dues decisions que el report anterior deixava obertes

Totes dues eren desviacions de la §8e que jo havia deixat com a «cal ratificació d'Agus». La
resposta ha estat aplicar la norma:

**15 · La llista s'obre pels OBERTS.** §8e: «els elements ACABATS no es llisten per defecte
(embruten la cerca)». Un encàrrec tancat ja no admet cap gest d'aquesta pantalla —ni tancar-lo,
ni triar-lo per al lot— i el seu lloc és a l'historial.
🔑 «Totes» necessita un valor EXPLÍCIT: `setParams` esborra els paràmetres buits, o sigui que
triar-la amb `''` hauria esborrat el paràmetre i tornat al defecte — la safata s'hauria negat a
obrir-se **sense que res fallés**.

**16 · La fila torna a UNA línia.** §8e: «MAI salt de línia». Nom i codi comparteixen línia; el
`whiteSpace: 'normal'` que anul·lava el `nowrap` de `TaulaLlista` se'n va.
🔑 **Qui s'escurça és el NOM, no el codi.** El codi té amplada estable i curta; escurçar-lo
deixaria un identificador a mitges —pitjor que no tenir-lo, perquè sembla sencer—, mentre que un
nom amb ellipsis segueix sent llegible. El `title` porta els dos sencers.

---

## MESURA · auditoria de computats + bidireccional (§8d)

> El report anterior deia «BLOQUEJAT per manca de mesura». **Ja no ho està.**

`ops/qa/qa_lot0909_bidireccional.py`, contra **`FTT_QA_DIST`** (el bundle construït, no el codi
font) i amb l'API viva de staging.

### 🛑 El senyal és obligatori

Cada cas porta el seu `data-ftt-screen` i, sense ell, **no es mesura: es crida**. Una pantalla
que no s'ha muntat dona ZERO incompliments, i zero és exactament el que volem veure. Els modals
ho necessiten més que ningú: es munten i es desmunten amb el gest, i sense senyal es mesuraria
la pantalla de sota creient que és el diàleg. Quatre àncores noves: `encarrecs-llista`,
`encarrec-detall`, `pla-treball` i `modal-<nom>`.

### RESULTAT

```
17 casos mesurats · 1 desviació
0 senyals absents · 0 gestos fallits · 0 elements absents
```

**Part 1 · auditoria de computats — 9 superfícies, totes netes:**

| cas | superfície | vores fora de paleta | mides sobre el sostre |
|---|---|---:|---:|
| L1 | Encàrrecs · llista (OBERTS, el defecte) | 0 | 0 |
| L2 | Encàrrecs · llista · safata TANCATS | 0 | 0 |
| L3 | Encàrrecs · llista · amb SELECCIÓ | 0 | 0 |
| L4 | Encàrrecs · llista · CERCA activa | 0 | 0 |
| D1 | Encàrrec · detall | 0 | 0 |
| R1 | Pla de treball · contenidors de ronda (model 1497) | 0 | 0 |
| M1 | Diàleg · tancament en LOT | 0 | 0 |
| M2 | Diàleg · paperera · tasca LLIURE | 0 | 0 |
| M3 | Diàleg · paperera · tasca LLIGADA | 0 | 0 |

Cap `rgb(29, 29, 27)` en cap vora — cap `var()` sense resoldre. Cap badge per sobre de 10px.

**Part 2 · bidireccional** de la llista contra `NORMA_LLISTA_canonica.html` (no és «la maqueta
d'encàrrecs» —no n'hi ha cap— sinó la **llei de la forma** per a qualsevol llista canònica),
element per element i amb computats a les **dues** bandes: capçalera en repòs · capçalera
ordenant · cel·la del NOM · cel·la secundària · caixa de la llista · casella · fila triada ·
badge neutre.

### Dos defectes de crom, VISTOS EN VERMELL i corregits (`79bb2f2d`)

```
sense els fixos : 15 casos · 4 desviacions
amb els fixos   : 15 casos · 1 desviació
```

1. **El pes de la dada reina vivia al lloc equivocat.** Estava a un `span` de dins; la llista
   canònica el declara al `td`. **A ull era idèntic** —el nom es veia en 600 igualment— però el
   computat de la cel·la deia 400. Dos llocs per a la mateixa regla és com neixen les dues
   veritats de crom.
2. **Les caselles no declaraven la seva caixa.** `.chk{width:14px;height:14px}` a la maqueta;
   sense mida pròpia el navegador en pintava 13. Invisible al diff, perquè el que hi ha escrit
   no diu res: la mida la posava el navegador.

### 🚩 LA DESVIACIÓ QUE QUEDA ÉS DE LA MAQUETA, i es deixa oberta

`td.c-col{font-size:11px}` per a les columnes secundàries (la maqueta l'usa 4 vegades).
**11px NO és a l'escala de la casa**: els tokens són 10 / 12 / 14 / 18 / 22 / 32
(`frontend/src/index.css:161-167`) i la §2 diu «cos 12/16 · caption/TH 10/12 — MÍNIM ABSOLUT».
Posar un 11px literal a la pantalla seria ficar al producte un valor fora d'escala per casar amb
una maqueta que tampoc no la compleix.
**Decisió d'Agus:** o la maqueta baixa a 10 (caption) o puja a 12 (cos). Les dues són a
l'escala; la tria és de producte.

### 🔒 Cap escriptura, amb una excepció declarada i verificada

```
ESCRIPTURES BLOQUEJADES (0): cap
ESCRIPTURES DEIXADES PASSAR (1): POST …/close-bulk/ (passada seca)
```

La passada seca (`cancel_pending:false`) **és condició per veure el diàleg**: sense la seva
resposta el modal es queda a «Comptant…» amb el botó apagat, i mesuraríem un estat de càrrega
creient que mesurem la confirmació. Que **no escriu** està comprovat contra la BD: els WO
segueixen `OPEN` i amb 0 DEDUCTIONs. Obrir els diàlegs de paperera tampoc escriu: l'escriptura
és al confirmar i allà no s'hi prem mai.

### Tres defectes DEL PROPI ARNÈS, vistos abans de donar cap número

Els dic perquè un instrument que no s'audita a si mateix dona verds de qualsevol cosa:
1. `:has-text()` és sintaxi de Playwright i `document.querySelector` no l'entén → es mesura
   sobre el **locator**, no sobre el document.
2. Comparar `width`/`height` per defecte donava **deu desviacions que no eren de crom** sinó
   d'amplada de text: la maqueta té onze columnes i dades inventades, la pantalla en té set i
   les de staging. Ara es demanen cas per cas, on sí que decideixen (la caixa d'una casella).
3. Un cas meu comparava peres amb pomes: `th.c-nom` de la maqueta porta també `.sorted`. Ara es
   mesuren els **dos** estats, cadascun contra el seu igual.

### El que aquesta mesura NO cobreix

- **El llenç no hi entra** (ordre d'Agus: «crom, MAI llenç»); cap pantalla del lot en té.
- **La bidireccional només cobreix la LLISTA.** El contenidor de ronda i els diàlegs passen
  l'auditoria de computats però **no tenen maqueta al disc** contra la qual comparar-se: la que
  el codi anomena (`proposta_A_v2_pla_treball.html`) no hi és. Per a aquelles superfícies la
  conformitat és «dins de la paleta i dels sostres», no «igual a la maqueta».
- **Un sol viewport** (1600×1000). El desbordament horitzontal que el guàrdia va anotar (suma de
  `min` de columnes) no s'ha mesurat en pantalla estreta.

---

## 🚩 ANOTAT, NO TOCAT (fora d'scope)

1. **Dues claus i18n han quedat sense lector** i no s'han esborrat (netejar claus mortes és una
   passada pròpia): **`workorders.filter_status_all`** (la substitueixen els tabs del commit 9) i
   **`workorders.col_target`** (`ca/en/es.json:1622`, el seu únic consumidor era la columna
   «Model/Període» que el commit 9 retira). La segona **la va trobar el guàrdia i18n, no jo**.
   ⚠️ No confondre `col_target` amb `size_map_col_target`, que sí que és viva.
2. **`desfa_avis_plural`** (i18n) fa servir la forma d'**i18next v3** (`_plural`) amb una v26
   instal·lada → **no dispara mai**. El vaig veure buscant el meu propi error del mateix tipus.
   No és del lot i no l'he tocat.
3. **`reattach-candidates`** cau al gate `DEFINE_TASKS` per defecte tot i ser una lectura
   comercial — incoherència **anterior** al lot, ja anotada al codi (`commerce/views.py`).
4. **La política foto / recàlcul / híbrid del numeral** segueix sent **decisió pendent d'Agus**.
   El commit 2 exposa la FOTO tal com la BD la té i **no recalcula res**, com manava el brief.
5. **La FK `Ronda` a `DeliveryNoteLine`** (bloc A) segueix pendent i **no és d'aquest lot**.
