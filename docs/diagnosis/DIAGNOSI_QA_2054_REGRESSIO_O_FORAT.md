# DIAGNOSI · QA d'Agus 20:54–20:56 sobre staging/1379 — regressió o forat destapat

> Patró A curt · **READ-ONLY**, cap fix aplicat. 17/08/2026.
> Font primària: `/var/log/nginx/ftt-staging-access.log` (la QA hi és sencera), la BD del
> tenant `fhort` (SELECT), i `git log`. El rellotge del servidor és **UTC**; la QA d'Agus
> (20:54–20:56, Europe/Madrid) són les **18:54–18:56 UTC**.

---

## D0 · ESTAT DE DESPLEGAMENT — QUÈ VEIA L'AGUS EXACTAMENT

### El front: `index-DhXW1r5u.js`

| hora UTC | bundle servit |
|---|---|
| 18:44:12 | `index-BoOUJsdb.js` |
| **18:48:25** | **`index-DhXW1r5u.js`** ← el de la QA |
| 18:53:56 | `index-DhXW1r5u.js` (304) |
| 18:54:34 | `index-DhXW1r5u.js` (200) |
| **19:03:08** | build nou → `index-BnuPo3kk.js` (**el que hi ha al disc ARA**) |

🚨 **El dist del disc NO és el que l'Agus va provar**: es va reconstruir a les 19:03:08,
**7 minuts DESPRÉS** de la QA. Tot Q8-bis (`acabe1bf` 19:01 · `932def89` 19:03) queda **fora**
del que l'Agus va veure. Qualsevol comprovació visual d'aquells dos commits està PENDENT.

**Contenia DhXW1r5u l'E2c-bis/C1+C4?** `e39f618d` (sub-tabs «Presa | Decisió») es va commitar a
les **18:48:41**, 16 s DESPRÉS que el bundle es servís. Per la regla del verd (`npm run build`
net **abans** del commit) el build va córrer amb aquell codi ja al disc → **sí, el conté**, i la
descripció que fa l'Agus del racó ho corrobora. ⚠️ **Ho dic per inferència, no per mesura**: vite
buida `dist/` i els bundles vells ja no existeixen.

### El backend: sense skew

- `ftt-staging` (gunicorn) `ActiveEnterTimestamp = 18:15:27 UTC`, `running` des de llavors.
- Últim `.py` de producte tocat avui: **17:22** (`fitting/services.py`, `esdeveniments.py`,
  `models.py`) — **anterior** a l'arrencada. `escalat_presa_views.py` és de les 11:32.
- Els commits de 18:24→19:03 són **tots de front** (`TechSheetEditor.jsx`, `PropagatedEditor.jsx`,
  `ModelSheet.jsx`, `MeasureGrid.jsx`, i18n) excepte `45ec9d3b`, que només afegeix un banc de test.
- **0 migracions al disc sense aplicar** al schema `fhort`.

→ **El backend que responia és el codi del disc.** Cap 409 d'aquesta QA s'explica per skew.

⚠️ **Anotat, fora d'scope**: el dist de les 19:03 s'ha construït amb
`frontend/src/utils/repartimentTaules.js` **modificat i NO commitat** (`git status: M`).

---

## D1 · L'ESTAT DE LA PRESA DEL 1379 — **TANCADA**

```
FittingSession 155 | estat = 'Tancada' | creada 2026-08-16 16:30:05 UTC
  └ PieceFitting 40 | 90 línies | 90 amb valor_real | 2 amb decisió
```

I el log diu **qui la va tancar i quan** — la mateixa QA, cinc minuts abans dels 409:

```
18:50:21  POST /api/v1/piece-fittings/40/close/    200
18:50:21  POST /api/v1/fitting-sessions/155/seal/  200
   …
18:55:44  POST /api/v1/fitting/model/1379/presa/   409
18:55:45  POST /api/v1/fitting/model/1379/presa/   409
18:56:04  POST /api/v1/fitting/model/1379/presa/   409
```

`SEALED_SESSION_ESTATS = ('Tancada','Anullada')` i `peca_de_presa_del_model` filtra per
`SESSIONS_VIVES` ([services.py:142](../../backend/fhort/fitting/services.py#L142)) → la presa ja
no és viva → `PresaNoObertaError` → 409 `sense_presa_oberta`
([escalat_presa_views.py:180](../../backend/fhort/fitting/escalat_presa_views.py#L180)).

🔑 **EL 409 ÉS CORRECTE I EL POST DE PRESA NO ESTÀ TRENCAT.** El que la QA va destapar és que
**l'Agus mateix va segellar la presa a les 18:50:21** i la pantalla no se'n va assabentar mai.

---

## D2 · «Obrir la presa» → Definició POM amb diàleg de tasca (captura 5)

### La ruta que compon el racó

[PropagatedEditor.jsx:322](../../frontend/src/pages/PropagatedEditor.jsx#L322):

```jsx
<button onClick={() => navigate(`/models/${modelId}?tab=Mesures`)}>
  {t('escalat.porta_obrir')}   // ca: «Obrir la presa»
</button>
```

**No és nou d'E2c-bis.** El botó i aquest destí neixen amb `4c4499dc` (**E1/B3c, 17/08 11:41**), a
`BarraPresaEscalat.jsx`, i amb la **mateixa condició** (`e.estat === SENSE_PRESA`, línies 92-93 de
la versió esborrada). `e39f618d` només el **trasllada** al racó dret del `SubTabs`. Destí idèntic,
condició idèntica.

🚨 **PER QUÈ ARA I NO ABANS**: el botó només es pinta en estat `SENSE_PRESA`. Fins a les 18:50:21
la presa era viva → el botó **no existia a la pantalla**. **El segell d'aquesta mateixa QA és el
que el va encendre per primer cop.** És a dir: el gest MAI havia estat exercit.

### Per què acaba a Definició POM — **EL SALT DE SUPERFÍCIE**, no una cursa d'efectes

1. `models/:id/escalat` = `<ModelSheet defaultTab="Escalat" autoEdit="Escalat" />`
   ([App.jsx:456](../../frontend/src/App.jsx#L456)) i `models/:id` = `<ModelSheet />`
   ([App.jsx:450](../../frontend/src/App.jsx#L450)) → **el MATEIX tipus de component**. React
   Router reconcilia en comptes de remuntar: **l'estat sobreviu al `navigate`** i `editing` es
   queda a `'Escalat'` (l'hi havia posat `autoEdit`,
   [ModelSheet.jsx:683-686](../../frontend/src/pages/ModelSheet.jsx#L683)).
2. [ModelSheet.jsx:664-675](../../frontend/src/pages/ModelSheet.jsx#L664) — F2.4 · D-1:
   ```js
   const sortia = (editing && editing !== activeTab) || …   // 'Escalat' !== 'Mesures' → true
   exitEdit()                                               // ← D'AQUÍ SURT EL DIÀLEG DE TASCA
   const code = CODE_PER_TAB['Mesures']                     // = 'pom'
   if (!saltDeSuperficie('Mesures', tasca_pom, jo, cara)) return
   obreDeDebo('Mesures', 'pom')                             // → openTask + setMesuresEntry(true)
   ```
   `CODE_PER_TAB = { Mesures: 'pom', Escalat: 'grading' }`
   ([sessioActiva.js:78](../../frontend/src/utils/sessioActiva.js#L78)). La tasca `pom` del 1379
   (id **371**) és `Paused`, cara `CAP` → **el salt s'autoritza**.
3. `aterraSegonsTipus('Mesures','pom')` → `setMesuresEntry(true)`
   ([ModelSheet.jsx:423](../../frontend/src/pages/ModelSheet.jsx#L423)) → es munta
   `MeasuresEntryPanel` = **Definició POM**.

**El log ho corrobora línia per línia** (referer `/models/1379?tab=Mesures`):

```
18:56:36  POST /api/v1/models/1379/open-task/        200   (×2, StrictMode)
18:56:36  GET  /api/v1/model-task-items/371/         200   ← 371 = tasca `pom`
18:56:36  GET  /api/v1/models/1379/poms-suggerits/   200   ← només el crida MeasuresEntryPanel
18:57:38  POST /api/v1/model-task-items/371/transition/ 200
```

### Comparació amb la llei del deep-link arreglada a E2

**NO s'hi aplica.** La cursa d'efectes d'E2 (`DIAGNOSI_E2_CORRECCIONS_QA.md` §BLOC 2) és el camí
`?tab=Mesures&fitting_session=<id>`: dos efectes asíncrons i el perdedor cau a la font `check`. El
fix d'E2 s'ancora a `fittingSessionParam`. **`porta_obrir` no porta CAP paràmetre** → mai entra en
aquella cursa; cau per un mecanisme diferent i determinista (el salt de superfície). La llei
d'E2 no el cobreix i no el cobrirà.

---

## D3 · Sub-tab «Decisió» sense presa

[PropagatedEditor.jsx:130-134](../../frontend/src/pages/PropagatedEditor.jsx#L130):

```js
const triaVista = useCallback((k) => {
  if (k !== 'decisio') { setVista(k); return }
  const sid = presa?.session?.id
  if (!sid) { setErr(t('escalat.sense_presa_oberta')); return }   // ← NO commuta
  …
```

**No és un no-op del tot silenciós**: `err` es pinta en `var(--err)` a
[:293](../../frontend/src/pages/PropagatedEditor.jsx#L293) i la clau existeix als tres idiomes.
Però **es llegeix com un no-op**, i per tres motius alhora:

- el missatge surt **per SOBRE de la fila de sub-tabs**, lluny d'on ha clicat el dit;
- el sub-tab **no commuta** i el badge és **0** (`pendents_base = 0` → `SubTabs` no pinta res),
  o sigui que res no havia advertit que allà no hi hagués feina;
- el text diu «obre-la per anotar-hi les mesures» però **el sub-tab no ofereix el gest**.

🔑 **ARREL COMUNA AMB S1/S3, i és la de debò**: el GET de presa serveix `session: null` +
`presa_oberta: false` per a una sessió **segellada**, exactament igual que per a un model que no
n'ha tingut mai cap. I `estatDeLaPresa` només té **quatre** estats
(`SENSE_PRESA · BUIDA · MESURANT · DECIDIDA`) — **cap d'ells és «TANCADA»**.

> **Una presa segellada és indistingible d'una presa que no ha existit mai.** D'aquí surten els
> tres símptomes: el 409 a les cel·les, el sub-tab que no obre, i el botó «Obrir la presa» que
> apareix on hauria de dir «Presa del 16/08 · tancada».

---

## D4 · Play sobre tasca Feta → diàleg «Has acabat?» (captura 2)

### `git log` dels fitxers del cicle de tasca — **CAP tocat avui**

| fitxer | últim commit |
|---|---|
| `components/model/ModalAcabarTasca.jsx` | `57dc3683` **09/08** |
| `components/model/ObrirTascaDialog.jsx` | `57dc3683` **09/08** |
| `components/model/WorkPlan.jsx` | `81bbfa1f` **08/08** |
| `components/model/TaskTree.jsx` | `b811df79` **08/08** |
| `backend/fhort/tasks/models.py` | `471b38bf` **09/08** |
| `backend/fhort/tasks/views.py` | `9d59dd0f` **05/08** |
| `backend/fhort/tasks/services.py` | `04e09b9d` **31/05** |

`ModelSheet.jsx` sí que s'ha tocat avui, però només per `3a6a53b2` (E2c-bis/C1a), que és el
**trasllat literal** del commutador de sub-tabs a `ui/SubTabs` — cap canvi de comportament.

### El mecanisme (vell)

`caraObrirTasca({status:'Done', es_lliurable:false}, jo) → CARA_CAP`
([caraObrirTasca.test.js:69](../../frontend/src/utils/caraObrirTasca.test.js#L69)) = **cap
diàleg, s'obre directament**. Prémer Play sobre una tasca Feta no-lliurable la **reobre en
silenci** (`InProgress`); en sortir, `exitEdit` la troba `InProgress`
([ModelSheet.jsx:586](../../frontend/src/pages/ModelSheet.jsx#L586)) i munta
`ModalAcabarTasca` → **«Has acabat …?»**. El diàleg no és el bug: és el símptoma que la reobertura
no ha preguntat res.

⚠️ **Límit honest**: cap de les 4 tasques del 1379 és avui `Done` (371 `pom`, 372 `size_check`,
373 `grading`, 374 `tech_sheet` — **totes `Paused`, `finished_at` NULL**), o sigui que **no puc
reproduir des de la BD sobre quina tasca l'Agus va prémer Play**. El veredicte s'aguanta sobre el
`git log`, que és inequívoc.

---

## VEREDICTES

| # | Símptoma | Veredicte | Tram |
|---|---|---|---|
| **S1** | Sub-tab «Decisió» no fa res sense presa | **Forat destapat** (E1/B3 + E2c-bis) | E2c-bis |
| **S2** | «Obrir la presa» → Definició POM + diàleg | **Forat destapat**, nascut a E1/B3c 11:41; el salt F2.4·D-1 és **deute vell** (05→08/08) | E2c-bis (racó) + Kanban (salt) |
| **S3** | 409 en anotar a les cel·les | **Forat destapat — el 409 és LEGÍTIM** | E1/B3 |
| **S4** | Play sobre tasca Feta → «Has acabat?» | **Deute vell** (≤ 09/08) | Sprint Kanban |

**CAP REGRESSIÓ D'AVUI.** Ni `e39f618d` ni cap commit de la tarda han trencat res del que la QA
ensenya. El que va canviar l'escenari va ser un **acte de la mateixa QA**: el segell de les
18:50:21, que va posar el model en un estat que aquestes pantalles no saben nomenar.

---

## FIXOS MÍNIMS PROPOSATS (**no aplicats** — esperen el vistiplau d'Agus)

### F-A · El cinquè estat: `TANCADA` — arrel de S1 i S3 · tram **E2c-bis**

*Backend* — que el GET sàpiga dir-ho. `EscalatPresaView.get` només mira la presa **viva**; li
falta la darrera **segellada** quan no n'hi ha cap de viva:

```
{ presa_oberta: false, presa_tancada: {id, data, estat}, … }
```

*Front* — `estatDeLaPresa` estrena `TANCADA`, i d'aquí en pengen tres coses **de franc**:
1. el racó diu **«Presa del 16/08 · tancada»** en comptes d'oferir obrir-ne una;
2. la graella de presa passa a **read-only** → **els 409 deixen d'existir** (avui es teclegen 90
   cel·les que el servidor rebutjarà una a una);
3. el sub-tab «Decisió» queda **inert amb `title`** que diu per què, en comptes de commutar-no.

Codi mínim, un focus. **És el fix que tanca S1 i S3 alhora**, i els tanca a l'arrel i no a la cara.

### F-B · «Obrir la presa» ha d'obrir la presa — S2 · tram **E2c-bis**

Avui el botó **navega** a `?tab=Mesures` i deixa que el salt de superfície decideixi on cau. El
gest que de debò obre una presa ja existeix i és `sessioDeFitting()` +
`aterraSegonsTipus('Mesures','size_check')` — el botó ③ «Mesurar prenda»
([ModelSheet.jsx:393](../../frontend/src/pages/ModelSheet.jsx#L393)).

**Mínim que no toca el salt**: navegar amb el **destí explícit** que ja té repartidor —
`?tab=Mesures&task_id=<size_check>` o `?mode=…`— en comptes del `?tab=Mesures` pelat. Amb
`taskParam` a la URL, [:668](../../frontend/src/pages/ModelSheet.jsx#L668)
(`if (taskParam || fittingSessionParam) return`) **atura el salt de superfície** i mana el
context entrant. Cap llei nova: s'usa la que ja hi és.

⚠️ **Cal decisió d'Agus**: si el botó ha de **crear** la sessió (i, doncs, aterrar directament a
la presa oberta), això reobre la **decisió D5 de la diagnosi E1, que segueix OBERTA** («la
pantalla d'Escalat no crea sessions»). No ho toco sense veredicte.

### F-C · S4 — **NO TOCAR ARA**

Deute datat al sprint Kanban. El fix natural és que `caraObrirTasca` tingui **cara pròpia per a
`Done` no-lliurable** («aquesta tasca està feta — vols reobrir-la?») en comptes de `CARA_CAP`.
Toca `utils/caraObrirTasca.js` + `ObrirTascaDialog.jsx` + i18n×3 + el banc de `caraObrirTasca`.
**Fora de tots dos trams d'avui.**

---

## ANOTACIONS FORA D'SCOPE (vistes, no tocades)

- 🚩 **Q8-bis sense QA**: `acabe1bf` i `932def89` s'han desplegat a les 19:03, **després** de la
  QA. Ningú els ha vist córrer.
- 🚩 El dist viu conté `frontend/src/utils/repartimentTaules.js` **no commitat**.
- 🚩 **Bufada de 401 a mitja QA**: 18:50:49→18:50:58 (6 crides) i 18:53:53 (3, entre elles
  `POST model-task-items/374/transition/` i `POST ftt-documents/812/unlock/`), amb
  `POST /api/token/refresh/` 200 a 18:51:14. El refresc funciona, però **hi ha gestos que es
  perden abans**: el `transition` i el `unlock` del 374 van morir amb 401 i ningú els va
  reintentar. V. `ftt-k1k6-sessio-jwt-refresh`.
- 🚩 `PieceFitting 40` té **`garment = None`** amb un model de **2 prendes**. No és d'aquest
  tram, però és la FAMÍLIA DE TRES rondant (`ftt-s2-fixes-s36-pell`).
