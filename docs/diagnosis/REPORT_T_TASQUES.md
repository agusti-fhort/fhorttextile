# REPORT T · EL CATÀLEG DE TASQUES I ELS DESTINS DE LA UI

> Staging `/var/www/ftt-staging`, branca `dev`, base `9560b290` (+ `7215ffdc`).
> T0 = diagnosi read-only. Cap escriptura a staging durant el cens.

---

## T0.1 · EL CATÀLEG REAL, ELS DOS TENANTS

`fhort` i `los` tenen **exactament el mateix catàleg**: 15 TaskType, tots `active=True`,
mateixos valors camp a camp. Cap divergència entre tenants.

| code | nom | tipus | eina | mode | fase | ordre | fact. | lliur. |
|---|---|---|---|---|---|---|---|---|
| `design_review` | Revisió de disseny | Externa-lliure | — | — | Disseny | 5 | ✔ | — |
| `design_clarify` | Aclariments amb disseny | Externa-lliure | — | — | Disseny | 6 | — | — |
| `pattern_digit` | Patró digitalització | Interna | `patro` | `digitalitzar` | Dev. tècnic | 10 | ✔ | ✔ |
| `pattern_cad` | Patró CAD | Interna | `patro` | `disseny_base` | Dev. tècnic | 20 | ✔ | ✔ |
| `pattern_hand` | Patró a mà | Externa-lliure | — | — | Dev. tècnic | 30 | ✔ | — |
| `pom` | Definició POM | Interna | `mesures` | `autoria_base` | Dev. tècnic | 40 | ✔ | — |
| `size_check` | Mesurar prenda | Interna | `mesures` | `presa` | Dev. tècnic | 45 | ✔ | — |
| `grading` | Escalat | Interna | `escalat` | `propagacio` | Dev. tècnic | 46 | ✔ | — |
| `sample_check` | Sample check | Interna | `escalat` | `presa` | Dev. tècnic | 47 | ✔ | — |
| `tech_sheet` | Fitxa tècnica | Interna | `fitxa` | `document` | Dev. tècnic | 50 | ✔ | ✔ |
| `pattern_review` | Revisió de patró CAD | Interna | `patro` | `revisio` | Dev. tècnic | 55 | ✔ | — |
| `bom` | Definició BOM | Interna | `fitxa` | `bom` | Dev. tècnic | 70 | ✔ | — |
| `scaling` | Escalat CAD | Interna | `patro` | `escalat` | Dev. tècnic | 81 | ✔ | ✔ |
| `marking` | Marcada | Interna | `patro` | `marcada` | Dev. tècnic | 82 | ✔ | ✔ |
| `audit` | Auditoria de model | Externa-lliure | — | — | Dev. tècnic | 90 | — | — |

**El brief tenia raó: el catàleg NO és el problema.** `tipus`, `eina` i `mode` hi són, poblats i
coherents entre ells (tota Interna té eina+mode; tota Externa-lliure els té a null). I `tipus`,
`eina` i `mode` **ja s'exposen** al `TaskTypeSerializer`
(`backend/fhort/tasks/serializers_b.py:15`) des de B1/F2.0. L'únic camp que falta de debò és
`visible`.

**Vocabulari real d'`eina`/`mode`** (CharField lliures, sense `choices`: el vocabulari viu a la
sembra, no al model — `backend/fhort/tasks/models.py:67-71`):

- `patro` → `digitalitzar` · `disseny_base` · `revisio` · `escalat` · `marcada`
- `mesures` → `autoria_base` · `presa`
- `escalat` → `propagacio` · `presa`
- `fitxa` → `document` · `bom`

---

## T0.2 · CENS DELS DESTINS CABLEJATS AL FRONTEND

Hi ha **dos** mapes hardcodats, i són bessons declarats (l'un diu que emmiralla l'altre):

| # | fitxer:línia | què és |
|---|---|---|
| 1 | [TaskTree.jsx:39-51](../../frontend/src/components/model/TaskTree.jsx#L39-L51) | `toolRoute(code, taskId, modelId)` + `toolTab(code)` — **el panell de Tasques del model** (les targetes d'«Iniciar») |
| 2 | [WorkPlan.jsx:25-55](../../frontend/src/components/model/WorkPlan.jsx#L25-L55) | `toolRoute(task, modelId)` + `toolTab(task)` — el Pla de treball del Dashboard (transport Play/Pause/Stop) |

Tots dos són un `switch` sobre `task_type_code` amb **sis casos** (`pom`, `tech_sheet`,
`size_check`, `grading`, `pattern_digit`, `pattern_cad`) i `default: null`. Cap dels dos llegeix
`eina` ni `mode`.

Tres detalls que importen per a T2:

- `TaskTree.jsx:101-108` **ja té una auditoria** que avisa per consola quan un TaskType té `eina`
  i no hi ha ruta mapejada. O sigui: el forat estava detectat i documentat, només no resolt.
- El comentari de `WorkPlan.jsx:22-24` diu que el mapa emmirallava el del Kanban. **El Kanban ja
  no existeix** (jubilat a `fc98cab6`, confirmat al cens C5-UI A11): no hi ha res amb què
  sincronitzar, i la «duplicació mínima conscient» avui és duplicació i prou.
- `models.openTask()` es crida SEMPRE abans de decidir si es navega
  (`TaskTree.jsx:112`, `WorkPlan.jsx:266`).

---

## T0.3 · ON HAURIA D'ANAR vs ON VA · LA LLISTA DE FEINA DE T2

Cens **empíric**, no llegit del codi: s'ha obert el panell de Tasques del model 188 a un
navegador real amb el bundle de `dist`, i s'ha premut «Iniciar» de les 15 targetes amb el
`POST .../open-task/` interceptat al navegador (resposta falsa) — **zero escriptures a staging**.
El que hi ha a la columna «on va DE FET» és la URL que la SPA va carregar.

| # | targeta | eina/mode | on va DE FET | veredicte |
|---|---|---|---|---|
| 1 | Revisió de disseny | Externa | **no navega** (però obre rellotge) | 🔴 rellotge orfe |
| 2 | Aclariments amb disseny | Externa | **no navega** (però obre rellotge) | 🔴 rellotge orfe |
| 3 | Patró digitalització | `patro`/`digitalitzar` | `/models/188/patro/taller?task_id=` | ✅ |
| 4 | Patró CAD | `patro`/`disseny_base` | `/models/188/patro/taller?task_id=` | ✅ |
| 5 | Patró a mà | Externa | **no navega** (però obre rellotge) | 🔴 rellotge orfe |
| 6 | Definició POM | `mesures`/`autoria_base` | `/models/188?tab=Mesures&mode=entry` | ✅ |
| 7 | Mesurar prenda | `mesures`/`presa` | `/models/188?tab=Mesures&task_id=` | ✅ |
| 8 | Escalat | `escalat`/`propagacio` | `/models/188/escalat?task_id=` | ✅ |
| 9 | Sample check | `escalat`/`presa` | **no navega** | ⚠️ pantalla APARCADA (sense maqueta) |
| 10 | Fitxa tècnica | `fitxa`/`document` | `/models/188/ftt/756?task_id=` | ✅ |
| 11 | Revisió de patró CAD | `patro`/`revisio` | **no navega** | 🔴 té eina i no hi va |
| 12 | Definició BOM | `fitxa`/`bom` | **no navega** | → `visible=False` (T1) |
| 13 | Escalat CAD | `patro`/`escalat` | **no navega** | 🔴 té eina i no hi va |
| 14 | Marcada | `patro`/`marcada` | **no navega** | 🔴 té eina i no hi va |
| 15 | Auditoria de model | Externa | **no navega** (però obre rellotge) | → `visible=False` (T1) |

**La feina de T2, en tres línies:**

1. Les **4 Externes** (1, 2, 5, 15) criden `open-task`, que fa `transition_task(...,'InProgress')`
   i **obre un `TimerEntrada` real** (`backend/fhort/tasks/views_b.py:585`). Rellotge en marxa,
   cap superfície on treballar i cap batec que el sostingui: és literalment «rellotges que no
   poden funcionar».
2. Les **4 Internes amb `eina` i sense ruta** (9, 11, 13, 14) no fan res: el `switch` no les té.
3. Les **2 que sobren** (12, 15) han de desaparèixer de la vista (T1: `visible=False`).

**⚠️ Divergència del brief que has de decidir tu.** El brief diu «INTERNA amb `eina` → navega a la
superfície que digui `eina`+`mode`». Per a 11/13/14 l'eina és `patro`, o sigui **el Taller**, que
existeix i és viu; el que NO existeix és el seu *mode*: el Taller no sap què és `revisio`,
`escalat` ni `marcada`, i no té maqueta aprovada per a cap d'ells. Dues lectures possibles:

- **(A)** portar-les al Taller amb el `mode` a la URL, que hi arribi i el Taller l'ignori de moment;
- **(B)** deixar-les sense destí amb estat explicat, fins que hi hagi maqueta del mode.

**He implementat (B)** i ho dic aquí en comptes de fer-ho en silenci: (A) porta el tècnic a una
pantalla que no fa el que la targeta promet, que és exactament el defecte que aquest tram ve a
tancar. La UI queda preparada per a (A) amb una línia per parell (`eina`,`mode`) al resolutor.

---

## T0.4 · SUPERFÍCIES D'ESCALAT VIVES

Tres, i **cap morta** — el que hi ha és una peça compartida, no un duplicat:

| superfície | fitxer | què fa | estat |
|---|---|---|---|
| `PropagatedEditor` | [PropagatedEditor.jsx](../../frontend/src/pages/PropagatedEditor.jsx) · muntat inline a `ModelSheet.jsx:835` | els VALORS graduats per talla (tab Escalat, consulta ↔ edició) | **viva i vigent** |
| `GraduacioPanel` | [GraduacioPanel.jsx](../../frontend/src/components/grading/GraduacioPanel.jsx) | el PAS de graduació: triar joc de regles | **viva**, i la mateixa peça serveix els DOS hostes |
| `ModelWizard` (pas 4) | [ModelWizard.jsx:769](../../frontend/src/pages/ModelWizard.jsx#L769) | l'editor del MODEL, que hostatja `GraduacioPanel` al seu pas 4 | **viu**, però com a editor del model |

**El «wizard antic» ja no és el destí de Graduació.** El calaix de Graduació encastava
`ModelWizard` obert al pas 4 fins **ahir**: `491993cd` (F1c · P11, 2026-08-04) el va substituir per
`GraduacioPanel`. Avui l'única porta al wizard sencer és el botó explícit «editar el model».
Veure §SORPRESES: això apunta a bundle ranci, no a codi.

---

## T0.5 · `sample_check` — NO EL TOCO, I EL MOTIU

Valors actuals (idèntics als dos tenants): `tipus=Interna` · `eina=escalat` · `mode=presa` ·
fase `Dev. tècnic` · ordre 47 · facturable · no lliurable.

Neix a F1.6 (`4ecd3dae`, 2026-08-04), després del catàleg canònic. Els valors **no són
internament incoherents**: `escalat`+`presa` és un parell únic i llegible («prendre mesures contra
l'escalat»), diferent de `mesures`+`presa` de `size_check` («mesurar la prenda contra la fitxa»).

**Per tant NO el corregeixo**, contra el que T1 autoritzava condicionalment:

1. No tinc accés al vault FTT-Brain, o sigui que **no puc contrastar-lo amb el disseny canònic**;
   i el brief mana aturar-se abans que suposar.
2. La seva pantalla (Sample size check) està **aparcada i sense maqueta aprovada**. Fixar
   `eina`/`mode` és decidir a quina pantalla anirà, i aquesta decisió és del disseny, no meva.

Queda a la targeta, visible, sense destí i amb estat explicat — com la resta d'Internes sense
superfície.

---

## MAQUETES · QUINS DESTINS EN TENEN

Llegit `ops/maquetes/` (5 fitxers, 2026-08-04):

| destí de tasca | maqueta aprovada |
|---|---|
| Mesures (`pom`, `size_check`) | ✅ `maqueta_mesures_carril_v8_1.html` |
| Comprovació | ✅ `maqueta_comprovacio_v2.html` (pantalla encara no construïda — D-31.17) |
| Fitting | ✅ `maqueta_fitting_v3.html` |
| Vista família | ✅ `maqueta_vista_familia_v1.html` |
| Wizard de model | ✅ `maqueta_wizard_model_v1.html` |
| **Taller de patró** (`pattern_digit`, `pattern_cad`) | ❌ **cap** |
| **Fitxa tècnica / editor .ftt** (`tech_sheet`) | ❌ **cap** |
| **Escalat / PropagatedEditor** (`grading`) | ❌ **cap** |
| **Sample size check** (`sample_check`) | ❌ cap — aparcada a posta |

T2 només toca el **transport** (qui decideix on va el botó), no cap d'aquestes pantalles. Però
tres destins vius que no tenen maqueta aprovada és un fet que val la pena tenir escrit.

---

## SORPRESES

### 🚨 S-1 · Staging serveix `frontend/dist` directament, i el `dist` s'ha reconstruït avui

`/etc/nginx/sites-enabled/ftt-staging:24` té `root /var/www/ftt-staging/frontend/dist`. No hi ha
pas de desplegament entremig: **el que hi ha a `dist` és el que veu qui entra a staging**. Els
`npm run build` de verificació d'avui (el fix de React #310 i la ⓘ del ruleset) han reescrit
aquell `dist`, o sigui que staging ja serveix `dev` HEAD. No és cap decisió meva de desplegar:
és que en aquest muntatge **construir ÉS desplegar**. Cal saber-ho.

### 🔑 S-2 · El recorregut d'Agus i el codi d'avui no diuen el mateix — i la diferència és el bundle

Dues de les tres queixes **no es reprodueixen** contra `dev` HEAD:

- «Patró CAD i Patró digitalització porten a Fitxa tècnica» → avui porten al **Taller**. El destí
  `?tab=Patró` va morir a `f3523b24` (W2) i el mapa hi porta des de llavors.
- «Graduació al wizard antic» → avui el calaix és `GraduacioPanel` des de `491993cd` (**ahir**).

Les altres dues **sí** es reprodueixen exactament: «Revisió de patró CAD i Patró a mà no fan res»
i «les externes obren rellotges que no poden funcionar».

La lectura més probable és que el `dist` que hi havia a staging durant el recorregut era anterior
a W2/P11. No ho puc provar: el bundle d'aleshores ja no existeix (v. S-1). El que sí que és cert
és que les dues queixes reproduïbles són reals i són el gruix de T2.

### 🚩 S-3 · L'auditoria de `TaskTree` ja cridava, i ningú l'escoltava

`TaskTree.jsx:101-108` escriu a la consola, a cada càrrega del panell, la llista de TaskTypes amb
`eina` i sense ruta. El forat de T2 estava **detectat, escrit i ignorat** des de B1. Un
`console.warn` no és un canal: no el llegeix ningú.

### 🚩 S-4 · `sample_check` no té clau i18n

`i18n/{ca,en,es}.json` tenen 14 claus `tasktype.*` i el catàleg en té 15: `sample_check` cau al
`defaultValue` i es pinta amb el nom del backend («Sample check», igual als tres idiomes). No es
resol en aquest tram perquè el nom definitiu depèn de la pantalla aparcada.

### 🔵 S-5 · Els dos tenants són bessons

`fhort` i `los` tenen catàlegs idèntics camp a camp. Qualsevol data migration del catàleg ha de
córrer igual als dos i no ha de raonar per tenant.

---

# T1 · EL CATÀLEG · `42a87909`

**Una migració (`tasks/0048`)**: `TaskType += visible` (bool, default True) + data migration.

`visible` **no és `active`**, i la distinció és tota la peça. Desactivar un tipus el RETIRA: les
seves tasques vives queden penjades d'un tipus mort i cap porta les torna a obrir. El que calia
és més fluix — *vàlid, però la UI encara no l'ofereix*.

Amagades, amb els codes del dump de T0.1 (mai inventats): **`bom`** (Definició BOM) i **`audit`**
(Auditoria de model). Cap de les dues té pantalla on treballar. **No s'esborren i no es
desactiven**: tornaran.

La migració és explícita als dos sentits (les dues a False, la resta a True), com la 0046: tornar-la
a córrer deixa el catàleg igual.

**Verificació**
- `migrate_schemas` (sense `--schema`) → OK als dos tenants.
- **SQL directe** (la migració pot donar un OK enganyós): la columna `visible` existeix a
  `fhort` i a `los`, i les 15 files diuen el mateix als dos schemes — `bom` i `audit` a False,
  les altres 13 a True, `active` intacte a True. `public.tasks_tasktype` segueix sent NULL.
- `manage.py check` net · `fhort.tasks.test_cataleg_visible` → **3/3 OK** (default, sortida al
  serializer, i que amagar NO desactiva).

Al `TaskTypeSerializer` només hi entra `visible`: `tipus`, `eina` i `mode` ja hi eren des de
B1/F2.0. **El catàleg no era el problema.**

**No s'ha tocat `sample_check`** (v. T0.5): els seus valors no són incoherents i la decisió és
d'Agus, no meva.

---

# T2 · LA UI LLEGEIX EL CATÀLEG · `a140c751`

Resolutor únic nou: [`utils/destiTasca.js`](../../frontend/src/utils/destiTasca.js). L'eina diu
ON i el mode diu EN QUIN CONTEXT; `SUPERFICIES` només conté els **sis parells amb pantalla viva**.
Els dos `switch` cablejats (T0.2) han marxat dels dos fitxers.

Quatre gestos, i només el primer navega:

| gest | qui | què fa la targeta |
|---|---|---|
| `GEST_EINA` | interna amb pantalla | obre la tasca i **hi navega** |
| `GEST_SENSE_PANTALLA` | interna amb eina, mode sense pantalla | obre la tasca, **no navega**, i diu per què |
| `GEST_SENSE_EINA` | interna sense eina | obre la tasca, **no navega**, transport manual |
| `GEST_DECLARAT` | externa-lliure | **no obre res**: el temps es declara (T3) |

**El canvi que més importa**: les externes ja no criden `open-task`. Aquella crida posa la tasca
En curs i obre un `TimerEntrada` real; sense pantalla on treballar i sense batec que el sostingui,
quedava un rellotge corrent sol —i embrutant el corpus de D-3, que és el que alimenta Welford.

**Verificació de pantalla** (bundle de `dist` + API viva, model 188 · ROSALIA, `open-task`
interceptat al navegador → **zero escriptures a staging**):

| | abans | després |
|---|---|---|
| targetes pintades | 15 | **13** (`bom` i `audit` fora) |
| naveguen a la seva pantalla | 6 | **6** (les mateixes, amb `task_id`) |
| no naveguen i no ho expliquen | 5 | **0** |
| no naveguen i **ho expliquen** | 0 | **4** |
| externes que obren rellotge | 4 | **0** ✔ |

El Pla de treball del Dashboard segueix navegant igual (Patró CAD → Taller · Definició POM →
Mesures/entry · Mesurar prenda → Mesures amb `task_id`), ara pel mateix resolutor.
`node --test destiTasca.test.js` → **13/13**. `npm run build` net. Zero errors de consola.

**⚠️ Divergències anotades i NO implementades** (regla de pantalles):

1. **`patro`/`revisio`, `patro`/`escalat`, `patro`/`marcada`** — l'eina existeix (el Taller), el
   *mode* no. No s'hi porta ningú fins que hi hagi maqueta del mode. Decisió d'Agus: implementar
   el mode al Taller, o fer que aquests tres modes resolguin al Taller genèric.
2. **`escalat`/`presa` (`sample_check`)** — pantalla aparcada, sense maqueta. Igual.
3. **Tres destins vius sense maqueta aprovada**: Taller de patró, editor de fitxa `.ftt` i
   `PropagatedEditor`. T2 no els toca; queda escrit.
4. **El gest de declarar temps des del panell no existeix** (és T3). Fins llavors, una tasca
   externa que JA existeixi es pot cronometrar i declarar des del Pla de treball del Dashboard
   (F2.5); una que no existeixi, no es pot crear des d'aquí. És el preu conscient de no deixar
   córrer rellotges orfes.

**T3 i T4 no s'han començat** (ordre d'Agus: les seves pantalles s'estan dibuixant).

---

# T3 · EL CRONO DE TEMPS DECLARAT · `984f027e` (backend) + `9b3ee38d` (pantalla)

> Desbloquejat perquè la maqueta va arribar: `ops/maquetes/maqueta_temps_declarat_i_modal_v1.html`
> (05/08, 13:19). Llegida ABANS de tocar res, com mana la regla de pantalles.

## El que la maqueta fixa, i com s'ha complert

| la maqueta diu | com s'ha fet |
|---|---|
| «Viu al servidor: sobreviu a recarregar, canviar de pestanya i tancar el navegador» | `engegar` obre un `TimerEntrada` **real** amb `origen='declarat'`. **Zero `localStorage`** al component. |
| «Sempre declarat, també quan ve del crono» | l'`origen` viatja per la porta (`transition_task(..., origen=…)`, kwarg amb default `mesurat`) |
| «El guard d'inactivitat no els toca» | `pausa_tasques_oblidades` exclou `origen='declarat'` |
| «Engegar el crono merita el model» | `_meritar_si_cal(task)` — les tres funcions de facturació **no s'han tocat** |
| «Desar temps no tanca la tasca» | `aturar` deixa la tasca **Paused**; tancar-la és T4 |
| «Descartar esborra el tram» | `descartar` fa `delete()`, i només sobre trams declarats i ja tancats |

## Decisions de disseny que no eren òbvies

- **El crono s'engega per la MATEIXA porta que tota la resta** (`transition_task`). Així hereta
  l'exclusió un-InProgress-per-tècnic, el log de transicions i l'auto-assignació. L'alternativa
  —una via pròpia per a les externes— hauria estat una segona màquina d'estats a mantenir.
- **`engegar` és idempotent**, i això és el que fa que obrir el crono i re-enganxar-s'hi després
  d'un F5 siguin **el mateix gest**. Sense això caldria un endpoint de lectura i un estat local
  que mentiria a la primera cursa.
- **La porta és per `(model, code)`**, no per id de tasca: quan el tècnic prem el botó d'una
  externa, la tasca sovint encara no existeix (igual que `open-task`, i per la mateixa raó).

## Verificació

- 11 tests nous (`test_crono_declarat`), amb la **contraprova** del guard: un tram declarat de 5 h
  sobreviu, un de mesurat de 5 h cau. Els quatre fitxers veïns (guard · temps declarat ·
  meritació · exclusió) segueixen verds: **53**.
- **A pantalla, contra la BD de staging** —l'únic lloc on la promesa es pot provar—: crono obert →
  **F5** → segueix corrent amb el temps acumulat → «Aturar» → «Confirma el temps abans de desar».
- Els 3 trams de 0 min que la prova va deixar s'han **esborrat**: entrarien al corpus que F3.1 ha
  de mesurar com si fossin feina real.

---

# T4 · EL MODAL D'ACABAR · `336d5682`

La píndola flotant de F2.3 marxa; l'indicador de sessió es queda (maqueta §2). El gest es fa
**en sortir** d'una superfície de treball, amb les dues sortides escrites i el temps dit en veu
alta: `Aquesta sessió: X · total de la tasca: Y`. En confirmar, es reposiciona al panell de
Tasques del model — **el Kanban no existeix i queda aparcat**.

Dos camps additius al `ModelTaskSerializer` (`temps_consumit_min`, `sessio_inici`): el modal els
necessitava i **no podia obrir un tercer sondeig de `timers.list`** quan justament F3.2 va a
convergir els dos que ja hi ha.

**Verificació a pantalla** (model 163): entrar en edició d'Escalat → sortir → modal amb «L'he
acabat» premarcat → «La pauso, hi seguiré» → la tasca queda **Pausada** i la vista salta a
**Tasques**. La píndola apareix **sense cap botó d'acabar**. Staging s'ha deixat com estava: 3
trams i 6 transicions de la prova, esborrats.

## ⚠️ El que T4 NO cobreix, i per què

**La Fitxa tècnica no té el modal.** El seu «desar i sortir» viu a `TechSheetEditor.jsx`, que és
**frontera declarada** en aquest tram. La peça hi encaixaria amb quatre línies (el component ja
és independent), però tocar aquell fitxer no toca. **Queda pendent i explícit**: avui, sortir de
la fitxa segueix sense preguntar res.

## 🚩 Les quatre decisions que la maqueta declara pendents

La maqueta les llista com a «coses que he decidit jo i que has de confirmar». **S'han implementat
tal com hi són**; si en canvies alguna, són canvis petits:

1. **«L'he acabat» ve preseleccionat.** Alternativa: cap opció premarcada, i obligar a triar.
2. **El modal surt sempre** en desar i sortir, també si la sessió ha durat dos minuts.
3. **«Descartar» esborra el tram** i no deixa rastre. Si en vols traça (qui i quan), cal desar-lo
   marcat en comptes d'esborrar-lo.
4. **El crono no es pot pausar**, només aturar.
