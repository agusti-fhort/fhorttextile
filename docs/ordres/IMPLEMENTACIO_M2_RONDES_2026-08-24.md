# M2 · LA CARA DE LES RONDES — el Pla de treball i el Registre, per volta

> **Patró B · IMPLEMENTA.** Sprint FRONTEND: pinta el que el nucli (M1 + M1-bis + CODA) ja fa.
> **Deliverable únic**: aquest fitxer. **Cap push** — el fa l'Agus.
> Els dos contractes visuals són `docs/maquetes/proposta_A_v2_pla_treball.html` i
> `proposta_B_v3_registre.html`, i **el mockup mana**: les desviacions FUNCIONALS són **zero**
> (§9 les llista totes, amb el motiu i la mida).

---

## 0 · CAPÇAL

| Fet | Valor |
|---|---|
| Worktree | **`/var/www/ftt-m1`** (reutilitzat), branca nova **`m2-cara-rondes`**, creada de `dev` a **`131f8c5b`** |
| Com s'ha posat al dia | `git checkout -b m2-cara-rondes 131f8c5b`. **No calia rebase**: `m1bis-fit4` (l'HEAD que hi havia) ja és dins de `131f8c5b` — comprovat amb `git merge-base --is-ancestor`, no assumit. L'arbre estava net |
| HEAD d'arribada | `2a00d6e2` — **6 commits**, cap push |
| Fitxers | **18** · `+1809 −30` |
| Migracions noves | **CAP** (i cap camp nou a cap taula: les tres addicions de backend són claus de payload) |
| `node_modules` | **enllaçat** al tree principal (`ln -s`), com el `venv`. `package.json` verificat IDÈNTIC abans d'enllaçar |
| Zones intocables | `pattern/**`: **cap fitxer tocat**. Model **1383**: no s'ha obert ni al navegador ni per l'ORM. QA sencera sobre el banc `[QA-M1]` |
| Servei | ⚠️ **`ftt-staging.service` NO reiniciat** (serveix `/var/www/ftt-staging`, un altre arbre). Gunicorn propi del worktree a `127.0.0.1:8124`, **aturat al tancament** |

---

## 1 · 🚨 TRES COSES QUE EL BRIEF DONAVA PER FETES I NO HO ESTAVEN

Cap de les tres ha bloquejat l'sprint —tot s'ha entregat sencer—, però totes tres canvien el que
la propera sessió ha de creure.

### 1.1 · `model_task_log_view` **NO és la font del registre d'activitat**

El brief diu: *«SUBSTITUINT la graella del registre actual (`model_task_log_view` n'és la font —
cap canvi backend)»*. A la pantalla viva **no ho és**:

| Qui | Font | Qui el munta |
|---|---|---|
| **`RegistreActivitatTab.jsx`** ← el tab «Registre d'activitat» | **`/api/v1/models/<id>/albara/`** (`consumption_delivery_view`) | `ModelSheet.jsx:1597` |
| `TaskLog.jsx` ← consumeix `model_task_log_view` | `task-log/` | **NINGÚ**: `grep` a tot `frontend/src` no en troba cap importador |

I no és només una qüestió de qui munta què: **un log de TRANSICIONS no pot dibuixar el mockup B
v3**, que demana temps · inici · fi **per tasca**. El `task-log/` no en porta cap dels tres.

**El que s'ha fet:** la graella nova substitueix la de passos de `RegistreActivitatTab` i la font
segueix sent `/albara/`. `TaskLog.jsx` **no s'ha tocat** (queda com el codi mort que ja era —
🚩 candidat a retirar, fora d'M2).

### 1.2 · La meitat B **no es podia provar al banc**: cap model d'M1 estava meritat

`/albara/` respon `{'merited': False}` quan el model no té `ConsumptionRecord`, i el tab
ensenya *«Aquest model encara no ha iniciat activitat»* i res més. **Els quatre models del banc
`[QA-M1]` hi eren** (mesurat abans de tocar res). Sense això, la meitat B de l'sprint s'hauria
entregat sense haver-la vist mai.

### 1.3 · El rastre d'FIT-8 s'escrivia i **no sortia per cap porta**

M1 · §6 escriu `TaskTransition.nota` i diu que la cara és M2. Però `model_task_log_view` servia
sis camps i **cap era `nota`**. La dada existia i no es podia llegir des d'enlloc. V. §3.3.

---

## 2 · MAPATGE DE TOKENS · mockup → sistema real

El cens D-9 deia que `--paused` / `--progress` / `--soft` / `--sel` / `--gold` del mockup no
existeixen al sistema. **Dels cinc, dos SÍ que existeixen pel nom** (`--sel` i `--gold`, a
`index.css:66` i `:24`) amb valors i semàntica pròpies. Es fa servir el token VIU en tots dos
casos i s'anota la diferència. **Cap token nou. Cap hex.**

| Mockup | Valor del mockup | → Token real | Valor real | Per què aquest |
|---|---|---|---|---|
| `--bg` | `#f7f5f1` | **`--bg-page`** | `#fbfaf8` | fons de pàgina; és el que la fila-resum de ronda fa servir (`tr.r-cap td{background:var(--bg)}`) |
| `--card` | `#ffffff` | **`--panel`** | `#ffffff` | superfície de targeta/contenidor |
| `--border` | `#e5e0d6` | **`--line`** | `#e8e5e0` | vores i separadors. Filet intern de taula → **`--line-soft`**, com fa `ui/Table` |
| `--ink` | `#1c1b19` | **`--text-main`** | `#1d1d1b` | — |
| `--soft` | `#8a8478` | **`--text-soft`** | `#6e6a64` | secundari. El del mockup no arriba a AA sobre blanc; el viu sí (5.37:1) |
| `--gold` | `#b8722c` | **`--gold`** | `#c27a2a` | existeix. Icona de l'entrega i accent |
| `--gold-bg` | `#f7ecdc` | **`--sel`** + filet `--gold-border` | `#f7f5f2` | 🚨 **`--gold-pale` està ELIMINAT del sistema** (NORMA §1, escrit al capdamunt de `ui/Badge`). La «forma de la casa» per a la superfície daurada és `--sel` amb filet `--gold-border`, i és la que s'usa |
| `--sel` | `#faf3e8` | **`--sel`** + filet `--gold-border` | `#f7f5f2` | mateixa forma. El token real és més neutre que el del mockup; **el filet daurat és el que hi posa el que el color hi perdia**, i és exactament el que la §1 reserva per al «contenidor triat» |
| `--ok` · `--ok-bg` | `#3d7a44` · `#eef5ef` | **`--ok`** · **`--ok-bg`** | `#2e7d32` · `#e9f3ea` | 1:1 |
| `--paused-bg` · `--paused-ink` | `#f7ecdc` · `#a06a2c` | **`--warn-state-bg`** · **`--warn-ink`** | `#ffedd9` · `#96500c` | la §1b(d) parteix el warn així a posta: `--warn-state` per a VORES i farciments, `--warn-ink` per al TEXT (5.32:1, AA) |
| `--progress` | `#2e5f36` | **`--ok`** | `#2e7d32` | és el que la barra del Pla ja feia servir abans d'M2: *la barra diu quant s'ha fet, i el fet és verd a tot el sistema* |

**Pastilles.** Cap `.pill-*` del mockup es reescriu: totes van pel `Badge` de la casa.
`pill-feta`/`pill-entregada` → `variant="ok"` · `pill-pausada`/`pill-espera` → `variant="warn"` ·
`pill-encurs`/`pill-fase` → `variant="gray"`.

**Icones · Tabler outline, cap `-filled`.** `▸`/`▾` → `ti-chevron-right`/`ti-chevron-down` ·
`➤` (entrega) → **`ti-package-export`**, que és la icona d'entrega que la casa ja feia servir a
`BadgeLliurable` · `▶`/`⏸`/`■` → `ti-player-play`/`-pause`/`-stop`, els del transport de sempre ·
l'avís del diàleg → `ti-alert-triangle` · els KPI → `ti-clock`, `ti-rotate-clockwise`,
`ti-package-export`, `ti-rotate`, `ti-clock-play`.

---

## 3 · LES TRES ADDICIONS READ-ONLY AL BACKEND

**Cap camp nou a cap taula, cap migració, cap escriptura.** Són tres claus de payload, i totes
tres perquè la dada existia i el compositor no la deia. Abans de cadascuna es va mirar si es
podia **derivar al client**; les que sí (la fase de la volta) no en van necessitar cap.

### 3.1 · `model_dashboard_view` → `ronda` i `ronda_seq` a cada tasca del pla

El Pla s'agrupa per volta i el compositor era l'únic lloc que no ho deia.

> 🚨 **I NO ES POT LLEGIR DE `/model-task-items/`**, que ja porta `ronda`/`ronda_seq` des d'F2.0.
> Aquell endpoint té **ABAST PER FILA** (`scope_model_task_queryset`): *«sense `VIEW_TEAM_TASKS`
> l'usuari només veu les SEVES tasques»*. Fer-lo servir hauria fet que un tècnic sense aquella
> capability veiés **menys tasques al Pla de les que hi veu avui**, i **en silenci** — una poda,
> no un 403. El compositor no scopa, i per això la volta ha de sortir d'allà.

### 3.2 · `consumption_delivery_view` → `ronda_seq` i `qui` a cada pas

- **`ronda_seq`**: creuar la volta pel `task_type` seria ambigu **justament amb rondes**, que és
  quan el mateix code apareix un cop per volta i les files no es poden distingir.
- **`qui`**: el tècnic amb **més minuts SANS** d'aquell pas, no l'`assignee`. És la lliçó d'F1.5
  que `ModelTaskSerializer.obert_per` ja repeteix: *`assignee` és planificació i el rellotge és
  realitat*, i un registre d'ACTIVITAT ha de dir qui la va fer. Sense cap tram sa → `null`:
  «ningú no hi ha treballat» és una dada, no un forat a omplir amb el nom de qui la tenia
  assignada. **Els dos costats tenen asserció al fum** (§7.2).

### 3.3 · `model_task_log_view` → `nota` i `ronda_seq` (la cara d'FIT-8)

`nota` **només** no és null quan la tasca pertany a una volta amb entrega informada
(`_nota_reobertura_post_entrega`): la seva PRESÈNCIA ja és el marcador. Per això el comptador
«/ rectificació m» **es compta**, no es dedueix parsejant la frase catalana — i `ronda_seq`
l'agrupa per volta sense haver de llegir el text. Aquesta és l'addició que fa que el brief tingués
raó a mitges sobre `task-log/`: no és la font de la graella, però sí la del rastre.

**Cap consumidor existent canvia** en cap de les tres: totes són claus noves en dicts ja servits.

---

## 4 · EL QUE ES DERIVA AL CLIENT (i que per tant NO va al backend)

| Dada del mockup | D'on surt |
|---|---|
| **Pastilla de FASE de la volta** | La ronda no té camp `fase` i **no se n'hi ha inventat cap**. La fase viu al catàleg (`TaskType.fase`, que `TaskTypeSerializer` ja serveix i que `WorkPlan` ja carregava per al resolutor de destins). `faseDeTasques` tria la **majoritària** de les tasques de la volta; l'empat el desfà el `default_order` més baix — **dada del catàleg, no una llista de fases escrita al front** (i18n-gate: cap enumeració de domini) |
| **inici · fi de la volta** | `Ronda.oberta_el` / `tancada_el`, que el `RondaSerializer` ja servia. **No** és el mín/màx de les tasques: una volta comença quan s'obre encara que ningú no hi hagi tocat res |
| **temps · recompte · progrés** | Suma i recompte de les tasques de la volta, al client (`agrupaPerRonda`) |
| **estat de la volta** | `entregada` (hi ha `Entrega`) → `tancada_el` → oberta. **Tres estats, no dos**: v. §9.3 |
| **col·lapse per defecte** | Derivat de l'estat (entregada = plegada). **Cap `localStorage`** |
| **es pot obrir volta nova?** | `potObrirVolta(rondes)` = cap oberta, que és el guard d'`obrir_ronda` llegit abans de pintar el botó |

---

## 5 · CLAUS i18n NOVES — bloc `rondes.*`, **54 claus, paritat ca/en/es al mateix commit**

Verificada per programa (`set(ca) == set(en) == set(es)`), no a ull. Cap enumeració de domini:
els estats de tasca segueixen sortint de `model_sheet.dashboard.task_status.*` amb
`defaultValue`, i les fases es pinten **tal com les serveix el catàleg**.

`nom` · `sense_volta` · `estat_entregada` · `estat_tancada` · `estat_oberta` · `inici` · `fi` ·
`temps` · `n_tasques_one/other` · `rectificacions_one/other` · `rectificacions_titol` · `plega` ·
`desplega` · `volta_buida` · `peu_segellades` · `marcar_entregable` · `nova` · `nova_ok` ·
`nova_replicats_one/other` · `nova_adoptats_one/other` · `nova_omesos` · `nova_error` ·
`entrega_titol` · `entrega_destinatari(_ph)` · `entrega_descripcio(_ph)` · `entrega_avis` ·
`entrega_avis_viues_one/other` · `entrega_confirma` · `entrega_error` · `entrega_ok` ·
`entrega_linia` · `entrega_per` · `ok_client_pendent` · `ok_client_fet` · `ok_client_titol` ·
`ok_client_cos` · `ok_client_data(_nota)` · `ok_client_confirma` · `ok_client_error` ·
`ok_client_ok` · `reg_titol` · `reg_kpi_rondes` · `reg_kpi_entregues` · `reg_col_qui` ·
`reg_entrega_a` · `reg_buit`.

Els plurals van amb el `_one`/`_other` que la casa ja fa servir (48 parells previs) i **amb
`count`**, no amb `n`.

---

## 6 · VÀLVULES D'ESCAPAMENT USADES — **una**

**La graella del registre no munta `ui/Table`.** La taula de la casa serveix llistes PLANES: no
té `colgroup` d'amplades fixes, ni files de tipus diferent (resum / detall / entrega), ni una
fila clicable enmig de files que no ho són. S'ha duplicat la capa de **PRESENTACIÓ**
(`RegistreRondes.jsx`) amb la mateixa pell —mateixos `th` de 10px en majúscules amb tracking
.08em, mateixos filets `--line`/`--line-soft`— i s'ha compartit la **LÒGICA** de debò:
`utils/rondes.js` és el mateix mòdul que fa servir el Pla de treball.

**La que NO ha calgut:** la targeta de tasca del Pla. La versió «compacta» del mockup és
presentació, i `TaskCard` s'ha reutilitzat sencera com a `children` de `RondaPla` — amb una sola
prop nova (`segellada`). Cap gest de transport, cap camí de Play i cap regla de handoff s'han
tocat.

---

## 7 · GATE CORREGUT

### 7.1 · `npm run build` · **VERD** · `eslint` sobre els fitxers tocats · **0 errors**

Dues *warnings*, totes dues **preexistents** i a línies que M2 no ha escrit: la dependència
`token` del `useEffect` del `/me/` (`WorkPlan`) i el `setLoading` dins de l'efecte de l'albarà
(`RegistreActivitatTab`).

### 7.2 · Fum HTTP · `ops/qa/qa_m2_cara_http.py` · **41 OK · 0 FAIL**

Per socket, `Host:` de tenant, JWT real, gunicorn **del worktree** a `:8124`. La primera asserció
és **401, no 200**: un 404 voldria dir que el backend servit no porta aquest codi.

Cobreix, per aquest ordre: el pla agrupa per volta · el model de dues voltes les separa · el
registre diu la volta i **QUI** (i que un pas amb minuts NOMENA algú i un sense minuts **no
nomena ningú**) · el verge segueix sent el control negatiu · l'entrega tanca la volta (FIT-13) i
no hi deixa feina viva (FIT-6) · l'OK del client és un fet i no un interruptor · **`Done→InProgress`
sobre feina entregada segueix sent LEGAL** (el segell és tou, FIT-2) i el log ho rastreja amb la
volta · «+Ronda» amb la llista buida diu què ha replicat.

🔑 **El fum es remunta el banc ell mateix.** Corregut dos cops seguits sense remuntar, el segon
donava 400 a l'entrega i **semblava trencat** quan el que passava és que la volta ja s'havia
entregat. (M'hi vaig entrebancar abans d'arreglar-ho.)

### 7.3 · Fum de PANTALLA · `ops/qa/qa_m2_cara_pantalla.py` · **24 OK · 0 FAIL**

`build verd ≠ front viu`. Bundle REAL de `frontend/dist` + **backend REAL** (no stubejat: aquesta
sessió sí que pot emetre JWT). Captures a `ops/qa/captures/m2_*.png` (gitignorades, al disc).

Va trobar **quatre defectes que cap build veia** (§8) i va néixer mentint dues vegades: servia
`index.html` al webfont d'icones —captures sense cap icona— i comparava capçaleres que el CSS
pinta en majúscules.

### 7.4 · Backend · `manage.py check` net + bloc RONDA **sencer**

Es toquen dos fitxers de backend, o sigui que corre el gate proporcional sencer d'M1-bis:

```
venv/bin/python manage.py test \
    fhort.tasks.test_ronda fhort.tasks.test_tasca_vigent fhort.tasks.test_contracte_f2 \
    fhort.tasks.test_m1_entrega fhort.tasks.test_m1bis_fit4 \
    --settings=fhort.settings_m1 --keepdb
```

**`Ran 176 tests in 619.347s` · `OK`** — els mateixos 176 d'M1-bis, cap tocat, cap de nou (M2 no
canvia cap comportament de backend: només diu més coses del que ja hi havia).

`manage.py check` net després de **cada** commit.

---

## 8 · EL QUE LA QA DE PANTALLA VA TROBAR

### 🚨 8.1 · Cada tasca de la R2 en amunt es pintava «FORA D'ENCÀRREC», amb el filet grana

`WorkPlan.isOutOfCharge` sumava `origen === 'ad_hoc'`. Des d'M1-bis, **totes** les tasques que
crea `obrir_ronda` neixen `ad_hoc` **a posta** —és el que les deixa conviure amb la `prevista`
del mateix tipus sota la unique parcial—, o sigui que **el joc REPLICAT sencer** hi entrava: cada
volta nova sortia marcada en vermell com si fos tota ella un extra fora de recepta.

Retirat `origen` del predicat. **No és una excepció que M2 s'inventi:** és el mateix raonament que
el backend ja va escriure a `_NO_ES_REPLICA` (*«l'únic camp que literalment vol dir això no és de
la recepta és `off_recipe`»*) i el que les dues superfícies comercials —`WorkOrderDetail`,
`OrderDetail`— ja feien soles. Aquesta era **l'única lectura de la casa** que hi sumava `origen`.

### 8.2 · Les altres tres

- El KPI «Inici activitat» embolicava a **tres línies** a `--fs-display` i desalineava la fila
  sencera de KPI. El mockup ja hi baixava el cos a mà (`font-size:14px` només en aquella
  targeta); `StatCard` guanya un **`valueStyle` opcional** — additiu, mateix precedent que
  `subColor`, cap muntatge existent canvia.
- La columna «Qui» tallava els noms («Agustí …»). El 8% del mockup compta amb 100vw i l'app hi té
  la barra lateral al davant. Els 8 punts surten d'INICI i FI, que porten data curta i en tenien
  de sobres; **la columna ampla del mockup (TASCA, 34%) no es toca**.
- El registre **no alimentava** el rastre d'FIT-8: el comptador hi era pintat i el log no hi
  arribava mai. Ara el llegeix, com el Pla.

---

## 9 · DIVERGÈNCIES RESPECTE AL MOCKUP

### ✅ Funcionals: **ZERO**. Les que hi ha són d'ABAST o de DADA INEXISTENT, i totes van amb motiu.

### 9.1 · Elements del mockup que **NO es pinten** (3)

| Element | Per què |
|---|---|
| **«objectiu 28/08»** a la capçalera de la R2, i **«Data de tancament projectada: 04/09»** al peu | Són dades de **PLANIFICACIÓ** (`ModelTask.planned_*`). El brief enumera què porta la capçalera de ronda i no hi són, i el §C treu Planning d'M2 explícitament. 🚩 **Decisió d'Agus** si les vol: són dues addicions read-only més |
| El botó **«···»** de la capçalera de ronda | El mockup el dibuixa i **no en diu cap acció**. Un menú amb accions inventades hauria estat redisseny; un botó buit, soroll. 🚩 **Digues què hi va** |
| Els **enllaços** de la línia d'entrega (*«Fitxa tècnica v1»* · *«Patró + escalat»* com a `<a>`) | 🔒 **La dada no existeix i no ha d'existir**: FIT-1 va decidir que l'Entrega **no té cap FK a cap artefacte** (*event informat, no artefacte controlat*), i hi ha un test d'M1 que ho guarda (`test_l_entrega_no_lliga_cap_artefacte`). El que hi ha és `descripcio`, TEXT LLIURE, i és el que es pinta. El brief mateix ho resol així a la seva línia d'FIT-1 |

### 9.2 · Un cas que el mockup no dibuixa i que **és el més freqüent de tots**: la feina SENSE volta

`ronda_seq` null vol dir feina d'abans del canvi de llei (M1-bis · FIT-4, la prohibició de
backfill és vigent fins al retroactiu de M5) o nascuda al buit entre voltes. **És la forma sencera
de tot model llegat.** Dues regles, i cap fa desaparèixer res:

1. **Un model sense CAP volta es pinta PLA, exactament com abans d'M2.** Embolicar-lo en una
   ronda que no existeix seria dibuixar una volta que ningú no ha obert.
2. **Un model amb voltes i tasques òrfenes** les posa en un bloc propi al final, retolat «SENSE
   VOLTA». Fer-les desaparèixer perquè el mockup no les dibuixa hauria fet que la pantalla
   n'ensenyés menys que abans de l'sprint.

### 9.3 · Un estat de ronda que el mockup no té: **«Tancada»**

El mockup en té dos (Entregada / En curs) i la BD en pot donar **tres**: una volta pot estar
**tancada sense entrega** (`tancar_ronda` és un servei, i l'entrega no n'és l'únic cridador
possible). El banc `[QA-M1]` en té una de viva. Pintar-la «En curs» hauria estat mentir sobre
feina que ja no admet ningú, i pintar-la «Entregada» hauria estat mentir a seques. Va amb
`variant="gray"`: no és ni un èxit ni una alerta.

### 9.4 · Adaptacions de presentació, mesurades (2)

Les dues de §8.2: el cos del KPI de data i el repartiment d'amplades de la columna «Qui». Cap de
les dues canvia què es diu; totes dues eviten que una dada quedi il·legible.

---

## 10 · CHECKLIST VISUAL — mockup ↔ codi ↔ captura

Per contrastar pantalla contra maqueta. Captures a `ops/qa/captures/`.

### A · Pla de treball (`proposta_A_v2`) — `m2_pla_entregada.png` · `m2_pla_segellada_oberta.png` · `m2_pla_dues_voltes.png`

| # | Element del mockup | On és | ✓ |
|---|---|---|---|
| A1 | Contenidor per ronda, filet `--line`, radi de targeta | `RondaPla.jsx` (arrel) | ✅ |
| A2 | Xebró de col·lapse | `RondaPla` · `ti-chevron-*` | ✅ |
| A3 | «RONDA n» (en `--text-soft` si és segellada) | `RondaPla` · `rondes.nom` | ✅ |
| A4 | **FIT-8** · «/ rectificació m» al costat del nom | `RondaPla` · `rondes.rectificacions`, de `rectificacionsPerVolta` | ✅ |
| A5 | Pastilla de FASE | `RondaPla` · `faseDeTasques` (catàleg) | ✅ |
| A6 | Pastilla d'ESTAT (Entregada / En curs / **Tancada**) | `RondaPla` · `ESTAT_VARIANT` | ✅ |
| A7 | Resum: inici · fi · temps · N tasques | `RondaPla` · `formatDataHora` + `formatMinutes` | ✅ |
| A8 | Progrés: fets/total · % + barra de 110px | `RondaPla` · farciment `--ok` | ✅ |
| A9 | Botó **«Marcar entregable»** quan `lliurable` | `RondaPla` → `EntregaDialog` | ✅ |
| A10 | **Línia d'entrega**, fons `--sel`, icona daurada | `RondaPla` (bloc `entrega`) | ✅ |
| A11 | …amb data · destinatari · **qui informa** · descripció | `rondes.entrega_linia` + `entrega_per` | ✅ |
| A12 | Pastilla **«OK client pendent»** → acció (PATCH) | `RondaPla` → `OkClientDialog` | ✅ |
| A13 | …i «OK client {data}» quan ja hi és | `Badge variant="ok"` | ✅ |
| A14 | Ronda entregada **col·lapsada per defecte** | `agrupaPerRonda.obertPerDefecte` (derivat) | ✅ |
| A15 | Tasques de volta segellada **en fade** | `RondaPla` · `opacity .62` | ✅ |
| A16 | …i **sense transport** | `TaskCard segellada` — el transport **se'n va**, no s'apaga | ✅ |
| A17 | Ronda vigent oberta, targetes de tasca **de sempre** | `TaskCard` reutilitzada | ✅ |
| A18 | Botó **«+ Nova ronda»** de vora discontínua | `WorkPlan` · només si cap volta oberta | ✅ |
| A19 | Frase del peu sobre el segell | `rondes.peu_segellades` | ✅ |
| A20 | «objectiu» i «tancament projectat» | **NO** — §9.1 | 🚩 |
| A21 | Botó «···» | **NO** — §9.1 | 🚩 |

### B · Registre d'activitat (`proposta_B_v3`) — `m2_registre.png` · `m2_registre_amb_entrega.png`

| # | Element del mockup | On és | ✓ |
|---|---|---|---|
| B1 | KPI **Temps total** | `RegistreActivitatTab` · `totals.total_minutes` | ✅ |
| B2 | KPI **Rondes** | recompte de la porta de voltes | ✅ |
| B3 | KPI **Entregues** | `rondes.filter(r => r.entregada)` | ✅ |
| B4 | KPI **Inici activitat** | `header.merited_at` (ja es deia així a l'i18n abans d'M2) | ✅ |
| B5 | **UNA sola graella**, capçalera única a dalt | `RegistreRondes.jsx` · un sol `<table>` | ✅ |
| B6 | Sis columnes: Tasca · Estat · Temps · Inici · Fi · Qui | `<colgroup>` (amplades: §9.4) | ✅ |
| B7 | **Fila-resum per ronda**, plegable, fons `--bg-page` | `tr.r-cap` equivalent | ✅ |
| B8 | …que agrega als **MATEIXOS eixos** (temps · inici · fi) | `agrupaPerRonda` | ✅ |
| B9 | …i el recompte de tasques a l'última columna | `rondes.n_tasques` | ✅ |
| B10 | Detall columnat a sota, **sagnat** | `paddingLeft: 34` | ✅ |
| B11 | Detall de volta segellada **en fade** | `color: --text-soft` | ✅ |
| B12 | **Fila d'ENTREGA dins del detall**, fons `--sel` | `RegistreRondes` (bloc `entrega`) | ✅ |
| B13 | …amb «Entrega a {client}» + OK client + qui | `rondes.reg_entrega_a` | ✅ |
| B14 | Rondes velles **tancades per defecte**, vigent oberta | derivat, no persistit | ✅ |
| B15 | Peu **«Historial complet (transicions)»** | el col·lapsable que ja hi era | ✅ |
| B16 | El rastre «/ rectificació m» també a la fila-resum | `RegistreRondes` | ✅ |

**Fora del mockup i conservat a posta:** la capçalera immutable de l'albarà, el repartiment per
tècnic i el KPI «Rectificacions». El mockup no els substitueix i treure'ls hauria estat un
redisseny. **«Passos» sí que se'n va** com a KPI: la graella ja diu quantes tasques té cada volta.

---

## 11 · EL BANC `[QA-M1]`, ampliat

`ops/qa/banc_m1_rondes.py` segueix sent idempotent i amb `--remunta`. Dues coses noves:

- **`_merita_sintetic`** — `ConsumptionRecord` + la marca del model, **escrivint només la fila
  local**. 🔒 **Mai pel camí normal**: la meritació de producte emet `model_consumption_started` a
  `public`, i aquell event **ÉS la unitat facturable del SaaS** (`recurring_service` en fa el
  `.count()` del període). Meritar un model sintètic pel camí normal hauria ficat feina inventada
  a la facturació d'algú. El model **verge es queda sense**: és el control negatiu.
- **`_dona_temps_real`** — els trams del banc es tanquen dins del mateix segon i sense escriptura,
  i `_close_open_timer` els marca `consulta=True`, que és el que `TRAMS_SANS` exclou: **tot el
  banc sortia a `0h 00m` i amb «Qui» buit**, i les dues columnes no es podien revisar. S'escriuen
  els camps del TRAM directament (mai simulant un batec, que dispararia la meritació).

Estat viu a `fhort` al tancament (els pk canvien a cada `--remunta`):

| Model | Rondes | Nota |
|---|---|---|
| `QA-M1-0001` | R1 **entregada** (+ OK client + 1 rectificació) · R2 oberta | el que ensenya la línia d'entrega i el rastre |
| `QA-M1-0002` | R1 oberta | tot fet |
| `QA-M1-0003` | **cap** | verge · control negatiu (sense volta i sense albarà) |
| `QA-M1-0004` | R1 **tancada sense entrega** · R2 replicada | el que ensenya l'estat «Tancada» i les dues voltes |

---

## 12 · COMMITS (branca `m2-cara-rondes`, **cap push**)

| Hash | Concern |
|---|---|
| `19a73835` | `feat(models_app)`: el pla i el registre saben de quina VOLTA és cada tasca |
| `4db6819e` | `feat(tasks)`: el rastre de la reobertura post-entrega SURT per la porta (FIT-8) |
| `be20fcd1` | `feat(model)`: el Pla de treball s'agrupa per VOLTA (mockup A v2) |
| `bb24cdb0` | `feat(model)`: el Registre d'activitat passa a UNA graella per rondes (mockup B v3) |
| `239d2fae` | `chore(qa)`: el banc dona albarà i temps reals, i el fum d'M2 es remunta sol |
| `2a00d6e2` | `fix(model)`: el que la QA de PANTALLA va trobar, i que cap build veia |

`git log -1 --stat` verificat després de cada commit; `git add` sempre de **paths explícits**.
L'arbre de sortida és net (només el symlink `backend/venv` i el de `frontend/node_modules`, cap
dels dos a git).

**Res per pushejar per part meva.** `m2-cara-rondes` surt de `131f8c5b` i vol un **merge** a `dev`.

---

## 13 · PENDENTS I DECISIONS D'AGUS

| # | Cosa | Estat |
|---|---|---|
| 🚩 1 | **«objectiu» i «data de tancament projectada»** del mockup A: dades de planificació, fora de l'abast d'M2 (§9.1) | **decisió**: les vols? Són dues addicions read-only més |
| 🚩 2 | **El menú «···»** de la capçalera de ronda: el mockup el dibuixa i no en diu cap acció (§9.1) | **decisió**: què hi va |
| 🚩 3 | **`isOutOfCharge` sense `origen`** (§8.1): correcció necessària, però és un canvi de lectura d'una superfície que no era a l'abast literal d'M2 | **ratifica-la** (o digues-me que la torni enrere i que el filet grana es quedi a totes les voltes ≥2) |
| 🚩 4 | **`TaskLog.jsx` és codi mort**: cap importador a tot `frontend/src` (§1.1). Ara consumeix una porta que M2 ha enriquit | retirar-lo és un tram propi |
| ⚠️ 5 | **`ObrirTascaDialog` / cara LLIURADA no s'ha tocat** i segueix sent coherent: obre volta per la mateixa porta. Però el seu text promet **una** tasca i, des d'M1-bis, els codes són ADDITIUS i la volta neix amb el joc replicat sencer. El diàleg no menteix, però **diu de menys** (ja era el ⚠️5 de l'acta d'M1-bis) | **anotat, no tocat** |
| ℹ️ 6 | Gunicorn de QA del `:8124` **aturat** al tancament. ⚠️ No el matis amb `pkill -f 8124`: el patró es troba a si mateix i et mata la sessió | resolt |
| ℹ️ 7 | **Cap migració, cap escriptura de domini nova.** M2 no canvia cap comportament de backend: només en diu més coses | declarat |

### Vist fora d'scope — **anotat, no tocat**

- `ui/Table` segueix sense poder expressar files de tipus diferent. Si M3 (kanban/board) en torna
  a necessitar, la conversa és si la taula de la casa guanya un `rowStyle`/`rowKind` o si la
  graella per rondes es promou a component compartit.
- El KPI «Rectificacions» de l'albarà compta **totes** les `Done→InProgress` del model; el rastre
  d'FIT-8 només les **post-entrega**. Són dues xifres diferents amb noms semblants i ara conviuen
  a la mateixa pantalla. No he unificat res: la primera és d'abans i té consumidors.

---
---

# CODA · fidelitat al mockup al Dashboard

> Annex al mateix document (no és un fitxer nou). Mateixa branca **`m2-cara-rondes`**, mateix
> worktree, **cap push**, **cap fitxer de backend** i per tant **cap test** (llei del gate).
> **Decisió d'ubicació d'Agus, fixada: el contenidor de rondes viu AL DASHBOARD.**
> Contracte visual: el mateix `docs/maquetes/proposta_A_v2_pla_treball.html`.

Quatre retocs demanats. **Tres han demanat codi; el quart ja estava fet** — v. C4.

---

## C1 · ① LA TARGETA COMPACTA DE TASCA

`frontend/src/components/model/TaskCardCompacta.jsx` — la `.tasca` del mockup: nom ·
temps/obertures · transport petit · pastilla d'estat. Prou més densa que la gran perquè quatre o
cinc hi càpiguen en una fila sota la capçalera de la volta, que és el que fa llegible el pla per
rondes.

### La vàlvula d'escapament, aplicada tal com mana la llei

| Capa | Què s'ha fet |
|---|---|
| **PRESENTACIÓ** | **DUPLICADA.** Fitxer nou amb el seu JSX i les seves mides, i un `TransportMini` propi de 20×20 |
| **LÒGICA** | **COMPARTIDA de debò** a **`frontend/src/utils/tascaPla.js`**: `TASK_ICON`, `STATUS_VARIANT`, `TRANSPORT`, `isOutOfCharge` i `lecturaDeTasca(task, {mine, hasToolRoute})` — les quatre preguntes que totes dues targetes han de respondre igual (quins botons tenen sentit · si el Play és viu · si és d'altri · si és fora d'encàrrec) |

🔒 **La targeta gran NO s'ha tocat.** Mesurat, no afirmat: el `git diff` de `WorkPlan.jsx` entre
l'acta d'M2 i aquest HEAD **no conté ni una línia del JSX de `TaskCard`**. Els únics canvis del
fitxer són l'import nou, el punt de crida de dins del contenidor de ronda, i que els mapes ara
li arriben del mòdul en comptes d'estar declarats a sobre. Segueix pintant **el pla PLA** dels
models sense voltes.

**Per què no s'ha extret res:** unificar les dues targetes hauria volgut una sola amb un mode
`compacta`, i aquell component ja embolica el handoff, el temps declarat, el segell i tres
renderings (§5). Un booleà més per damunt seria justament el que la llei prohibeix forçar.

**Mides.** Del mockup, amb els tokens de la casa: farciment `8px 10px`, mínim 190px, nom a
`--fs-body` en pes 600, meta a `--fs-caption` en `--text-soft`, transport de 20×20.
⚠️ **El radi 8 del mockup no és de l'escala de la casa** (6 · 12 · 999) i baixa a **`--r-ctrl`**
(6), que és el veí i el que ja porten els controls. És l'única mida del mockup que no es pot
seguir al peu de la lletra sense inventar un valor fora d'escala.

**Una regla que NO ha canviat:** el mockup posa el nom del tècnic a la línia de meta. La targeta
compacta el diu **amb la mateixa condició que la gran** (només quan la tasca no és meva i té
assignat), no amb una de nova: la compactació és presentació i no havia de moure cap llei.

---

## C2 · ② FORA LA BARRA DE PROGRÉS GLOBAL

Se'n va el peu sencer del pla: «n/m tasques fetes · %» **i la seva barra**. Amb el pla repartit
per voltes, un percentatge sobre TOTES les tasques del model **barrejava voltes entregades amb la
vigent** i no responia cap pregunta que la capçalera de cada ronda no respongui ja millor.

El **temps acumulat sobre el model** es queda —és un fet del model sencer, no d'una volta— i puja
a la `.sec` del mockup: rètol a l'esquerra, temps a la dreta, alineats a la línia de base.
**Mesurat al fum**, no mirat: les dues caixes comparteixen `y` (198 ≡ 198) i el temps és a la
dreta del rètol.

`model_sheet.dashboard.workplan.progress_label` queda òrfena i **se'n va dels tres idiomes
alhora**: la paritat ca/en/es es manté per retirada igual que es manté per addició.

### ⚠️ Conseqüència declarada, i és MESURADA

Un model **sense cap volta** es pinta pla i **ara no té cap indicador de progrés al Dashboard**:
no hi ha capçaleres de ronda que el diguin i la barra global ja no hi és. A `fhort`, avui:

| Models amb tasques | Sense cap `Ronda` (es pinten PLANS) | Amb almenys una |
|---|---|---|
| **7** | **4** | 3 |

La població s'apaga sola —tot model que rebi un gest neix amb R1 (M1-bis · FIT-4)— però **avui és
majoria**. 🚩 Si el vols conservar en aquest cas, és **una condició d'una línia**
(`{!perVoltes && <peu/>}`); no l'he posada perquè el retoc demana retirar la barra sense
condicions.

---

## C3 · ③ «+ NOVA RONDA» SEMPRE VISIBLE

Banda puntejada a sota de l'última ronda, **sense condició de client**. Abans es pintava només si
cap volta era oberta —el guard d'`obrir_ronda` llegit per endavant— i el botó **desapareixia
sense dir per què**: qui no el trobava no sabia si li faltava permís, si la pantalla s'havia
trencat o si el gest no tocava.

Ara el gest s'ofereix sempre i **qui el refusa és el servidor, amb el seu motiu**: `obrir_ronda`
respon `400 ronda_invalida` amb *«aquest model ja té una ronda oberta; tanca-la abans d'obrir-ne
una altra»*, i `obreVolta` ja portava el missatge del servidor al toast (no ha calgut clau nova).

**Segueix vivint dins del pla PER VOLTES**, i això no és una condició amagada: «a sota de
l'última ronda» demana que n'hi hagi alguna. En un model sense cap volta la R1 **neix sola del
primer gest** (M1-bis · FIT-4) i un botó allà faria creure que s'ha de declarar.

`potObrirVolta` es queda sense cap lector i **se'n va d'`utils/rondes.js`**: un helper que ja no
s'usa és una regla esperant que algú la torni a aplicar.

---

## C4 · ④ EL MENÚ «···» — **ja no hi era**

**Cap codi. Cap commit.** El menú «···» del mockup **no s'ha construït mai**: M2 el va deixar
fora i ho va declarar a §9.1 d'aquesta acta (*«el mockup el dibuixa i no en diu cap acció; un menú
amb accions inventades hauria estat redisseny, un botó buit, soroll»*). La decisió de la sessió 9
—cap menú buit, tornarà amb M3— **ratifica el que ja hi havia**, i el que canvia és l'estat de la
pregunta oberta: 🚩 el punt 2 del §13 (*«digues què hi va»*) queda **TANCAT**: hi anirà quan M3
porti accions.

Ho verifica el fum igualment (`④ cap menú «···» a les capçaleres de ronda`), perquè una absència
que ningú no mesura és una absència que torna sola.

---

## C5 · GATE

| Control | Resultat |
|---|---|
| `npm run build` | **VERD** |
| `eslint` sobre els fitxers tocats | **0 errors** · 1 warning **preexistent** (la dependència `token` del `useEffect` del `/me/`) |
| Fitxers de backend tocats | **CAP** → **cap test**, com mana el brief |
| Fum de pantalla · `ops/qa/qa_m2_cara_pantalla.py` | **30 OK · 0 FAIL** (26 abans + **4 nous, un per retoc**) |
| Fum HTTP · `ops/qa/qa_m2_cara_http.py` | **41 OK · 0 FAIL** (cap contracte tocat; corregut per no deixar-lo sense mesurar) |
| Banc | `[QA-M1]`, remuntat. **Model 1383: no s'hi ha entrat** |
| Servei | `ftt-staging.service` **NO reiniciat**. Gunicorn propi a `:8124`, **aturat al tancament** |

### Les quatre assercions noves, i com mesuren

| # | Asserció | Com |
|---|---|---|
| ① | *dins de la volta, el transport és el COMPACTE (20px, no 26)* | **`bounding_box()` de cada botó de transport**: la mida és l'única diferència entre les dues targetes que no es pot confondre amb res més. Mesurat: tots a **20** |
| ② | *la barra global ja no hi és* · *el temps segueix dit* · *a la MATEIXA fila que el rètol i a la seva dreta* | absència del text + **comparació de `y` i `x` de les dues caixes** (198 ≡ 198). Que el text hi sigui no prova que sigui on el mockup el posa |
| ③ | *«+ Nova ronda» es pinta encara que hi hagi una volta OBERTA* | sobre el model del banc amb **R2 viva**, que és exactament l'estat en què abans desapareixia |
| ④ | *cap menú «···» a les capçaleres de ronda* | absència mesurada |

**Captures** (a `ops/qa/captures/`, gitignorades): `m2_pla_dues_voltes.png` ← **la del retoc**,
amb les dues voltes en targeta compacta, el temps a la capçalera, la banda puntejada i cap
«···» · `m2_pla_entregada.png` · `m2_pla_segellada_oberta.png` · `m2_registre.png` ·
`m2_registre_amb_entrega.png`.

---

## C6 · COMMITS

| Hash | Retoc | Concern |
|---|---|---|
| `ccda7b3b` | ① | `feat(model)`: la targeta COMPACTA de tasca dins dels contenidors de ronda |
| `0d2681e9` | ② | `refactor(model)`: fora la barra de progrés GLOBAL del pla; el temps puja a la capçalera |
| `b2076276` | ③ | `feat(model)`: «+ Nova ronda» sempre visible; qui refusa el gest és el servidor |
| *(HEAD)* | ④ + acta | `docs(ordres)`: la CODA d'M2 — **aquest annex** |

**Tres commits de codi i no quatre**, perquè el retoc ④ no en demanava cap (C4). `git add` de
paths explícits; arbre de sortida net.

---

## C7 · ESTAT DEL §13 DESPRÉS DE LA CODA

| # | Estat ara |
|---|---|
| 🚩 1 · «objectiu» i «tancament projectat» | ⏳ **segueix obert** — dades de planificació, fora d'M2 |
| 🚩 2 · el menú «···» | ✅ **TANCAT** — cap menú buit; tornarà amb M3 (C4) |
| 🚩 3 · `isOutOfCharge` sense `origen` | ⏳ **segueix pendent de ratificar**. El predicat ha canviat de casa (ara viu a `utils/tascaPla`) i el segueixen les DUES targetes: ratificar-lo val ara per les dues |
| 🚩 4 · `TaskLog.jsx` és codi mort | ⏳ obert |
| ⚠️ 5 · `ObrirTascaDialog` diu de menys | ⏳ obert |
| 🚩 **NOU** · el pla PLA es queda **sense cap progrés** (C2) | **decisió teva**: una línia si el vols |
