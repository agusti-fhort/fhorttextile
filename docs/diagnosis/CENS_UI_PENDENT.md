# CENS D'UI PENDENT — què li falta a cada pantalla per ser «la nova»

> **Patró A · NOMÉS LECTURA.** Cap commit, cap fitxer del producte tocat, cap suite corregut.
> Data: **2026-08-04** · HEAD `3692db68` (branca `dev`, 0 pushes) · bundle `frontend/dist` construït
> el **04/08 16:45**, posterior a tot `src/` → **el que hi ha a staging ÉS aquest codi**.
>
> Per a demà al matí: cada pantalla amb **estat · què li falta exactament · UI pura o espera
> backend · fitxer:línia**. El bloc final (Q6) és la llista per ordre de treball.

---

## 0 · Com s'ha verificat (i què no s'ha pogut)

**Eines reals emprades, no lectura de codi a seques:**

| Prova | Resultat |
|---|---|
| **ROSALIA · model 188** (`BRW-SS27-0001`) | 13 mesures base · **4 germanes**: pom **273** `exterior`/`A` (bm 1285) + `folre`/`A-FOL` (bm 2101) · pom **284** `exterior·left`/`AH-L` (bm 2102) + `exterior·right`/`AH-R` (bm 2103). Run `XXS·XS·S·M`, base `S` |
| `GET models/188/taula-mesures/` (executat) | **13 files, 13 deltes**, claus `273\|exterior\|` · `273\|folre\|` · `284\|exterior\|left` · `284\|exterior\|right`. Cap col·lapse |
| `GET models/188/base-measurements/` (executat) | **13 files** amb `capa`, `instancia`, `nom_canonic_model`, `nom_traduit_model` **al payload** |
| `GET calendar/events/` juliol (executat) | 20 events de fitting, **tots amb `start`==`end` de dia**. Cap rèplica |
| **Sessió 147** | model 188 · fase `SizeSet` · estat `Oberta` · 04/08 18:05 · `convocatoria=None` · 10 min |
| **Model 1307** (`BRW-SS26-0002`) | **0 mesures base** → és el cas BUIT del cens (pantalla de gènesi) |
| Maquetes `ops/maquetes` (md5 preses) | `mesures_carril_v8_1` `5754…5c62` · `fitting_v3` `cb89…e549` · `comprovacio_v2` `7303…dffba` · `vista_familia_v1` `0e0b…d0d13` (DESCARTADA) · `wizard_model_v1` `0ac9…53aff` (sense validar) |

**El que NO s'ha pogut mesurar en viu, i per què (RESOLT mentre es tancava el cens):**
Durant el cens, una **sessió de backend paral·lela** tenia la **D-31.21** a mig fer
(`fitting/{models,serializers,services,views}.py` sense commit + migració `0024` sense aplicar),
i **tota lectura de `PieceFittingLine` petava** amb
`ProgrammingError: column fitting_piecefittingline.decisio does not exist`. Els apartats que en
depenen (Repàs, T3 de la fitxa) s'han censat **per codi i per contracte**, no per execució.
**Ja està tancat**: `fd102c06` (D-31.21, columna aplicada i verificada) i `33451704` (D-31.22).
Res del cens canvia per això — el que canvia és el bloc B1, que passa a ✅.
**⚠️ Aquest cens és del FRONTEND a `3692db68`; els dos commits posteriors són de backend i no
toquen cap fitxer de `frontend/src`.**

---

## Q1 · LES PANTALLES DEL MODEL, una a una

Les pestanyes viuen a **[ModelSheet.jsx:34](frontend/src/pages/ModelSheet.jsx#L34)**:
`Dashboard · Resum · Mesures · Escalat · Patró · Fitxa tècnica · Fitxers · Registre d'activitat · Tasques`.
**Watchpoints NO és una pestanya**: és una pastilla ancorada a la dreta de la banda, visible des
de qualsevol tab ([ModelSheet.jsx:500-504](frontend/src/pages/ModelSheet.jsx#L500-L504)).

| # | Pantalla | Estat | Què li falta | Naturalesa |
|---|---|---|---|---|
| 1 | **Dashboard** | 🟡 | No té POMs, o sigui que la identitat no hi aplica. Li falta **la llista de sessions de fitting del model** (v. Q3.4) i **les alertes de POM** (v. Q5.4). Les fites només miren **14 dies endavant** ([ModelMilestones.jsx:11](frontend/src/components/model/ModelMilestones.jsx#L11)) → un fitting d'ahir no hi és | UI pura |
| 2 | **Resum** | ✅ | Fitxa de camps del model + `RuleSetCard`. Res de POMs. Complet | — |
| 3 | **Mesures** | 🟡 | **La graella és nova i correcta** (v. detall sota). Falten: **el gest de crear una germana**, **el tint de fila no-exterior**, i **la 3a subvista «Comprovació»** | UI pura + 1 decisió |
| 4 | **Escalat** | ✅ | `PropagatedEditor` → `MeasureGrid` amb capa+instància i `rowKey` propi ([fittingGridAdapter.jsx:318](frontend/src/components/model/fittingGridAdapter.jsx#L318)). P2 tancat (`2a08d645`) | — |
| 5 | **Patró** (Taller) | 🔴 | El backend **ja serveix** `capa`/`instancia` a `model-poms` ([patterns/views.py:635-636](backend/fhort/patterns/views.py#L635-L636)) i la fila es clava per `base_measurement`. **El front no en pinta cap dels dos** ([ModelPomList.jsx:92,134,143](frontend/src/components/pattern/ModelPomList.jsx#L92)) → a ROSALIA surten dues files «CH · Chest width» i dues «AH DEP · Armhole depth», distingibles NOMÉS pel codi curt del client | **UI pura** |
| 6 | **Fitxa tècnica** | 🔴 | Tot el bloc Q2 | **UI pura** |
| 7 | **Fitxers** | ✅ | `TabFiles`. Sense POMs | — |
| 8 | **Registre d'activitat** | ✅ | `RegistreActivitatTab`. Sense POMs | — |
| 9 | **Tasques** | ✅ | `TasksTab` + `TaskTree` | — |
| — | **Watchpoints** | ✅ | Pastilla + calaix, viu des de qualsevol tab | — |
| — | **Comprovació** | 🔴 **NO EXISTEIX** | Maqueta **APROVADA** (D-31.17, `maqueta_comprovacio_v2.html`). Cap tab, cap ruta, cap component. Zero línies escrites | v. Q6 |

### 3-bis · MESURES: els dos gestos, i on parteix exactament

**Una sola pantalla, tres règims, i el que els separa NO és `task_id`: és el CODI de la tasca.**
El bloc sencer és [ModelSheet.jsx:551-670](frontend/src/pages/ModelSheet.jsx#L551-L670):

| Règim | Component | Com s'hi entra | Punt de partició |
|---|---|---|---|
| **DEFINICIÓ** (quins POMs té el model) | `MeasuresEntryPanel` → `EditableTable` | `enterEdit('Mesures','pom')` o `?mode=entry` | **[ModelSheet.jsx:235](frontend/src/pages/ModelSheet.jsx#L235)** — `if (tab==='Mesures' && code==='pom') setMesuresEntry(true)` |
| **PRESA** (quant fa cada mesura) | `CheckMeasureEditor` editable → `MeasureGrid` | `?task_id=` (codi `size_check`) o `?fitting_session=` | [ModelSheet.jsx:291-300](frontend/src/pages/ModelSheet.jsx#L291-L300) i [:318-331](frontend/src/pages/ModelSheet.jsx#L318-L331) |
| **CONSULTA / REPÀS** | `CheckMeasureEditor readOnly` · `FittingRepasPanel` | Per defecte; commutador `taula ↔ repas` | [ModelSheet.jsx:598-613](frontend/src/pages/ModelSheet.jsx#L598-L613) |

> `task_id` sol **sempre vol dir PRESA**. La definició s'obre pel codi de tasca `pom`, no per un
> paràmetre d'URL. Val la pena saber-ho perquè és el que fa que «obrir Mesures des del Kanban»
> i «obrir Mesures des del botó» acabin en pantalles diferents.

### 3-ter · Amb ROSALIA obert: les tres preguntes d'Agus

**① Es veuen les 4 germanes?** → **SÍ, a totes les graelles del model.** Verificat contra el
payload real: 13 files i 13 deltes, cap col·lapse. La columna Δ ja no és cega — llegeix per
`row.clau`, no per `pom_id` ([EditableTable.jsx:198-201](frontend/src/components/EditableTable/EditableTable.jsx#L198-L201)),
i el bug que la buidava a **tots** els models (també els de zero germanes) està tancat.

**② Hi és la identitat (Layer + instància al nom + ⓘ)?**

| Superfície | Columna CAPA | Instància dins el nom | ⓘ |
|---|---|---|---|
| Mesures · **definició** (`EditableTable`) | ✅ [:503-505](frontend/src/components/EditableTable/EditableTable.jsx#L503-L505) | ✅ [:539,656](frontend/src/components/EditableTable/EditableTable.jsx#L539) | ✅ [:657-661](frontend/src/components/EditableTable/EditableTable.jsx#L657-L661) |
| Mesures · presa/consulta · Escalat · Repàs · Fitting (`MeasureGrid`) | ✅ [:583-586](frontend/src/components/model/MeasureGrid.jsx#L583-L586) | ✅ [:223-224](frontend/src/components/model/MeasureGrid.jsx#L223-L224) | ✅ [:280-284](frontend/src/components/model/MeasureGrid.jsx#L280-L284) |
| Full de fitting imprès (`FittingPrintSheet`) | ✅ | ✅ [:210](frontend/src/pages/FittingPrintSheet.jsx#L210) | n/a (paper) |
| **Taller de patró** (`ModelPomList`) | ❌ | ❌ | ❌ |
| **Fitxa tècnica** — les 4 taules i el panell de cotes | ❌ | ❌ | ❌ |

El vocabulari és **font única** i compleix el gate i18n: `utils/capaInstancia.js` amb les claus
`capa.*` i `instancia.*` presents i **paritàries a ca/en/es** (verificat). Els literals erronis
de les maquetes («Interlining», «Binding», «Knit», «Reinforcement») **no s'han copiat**, per
D-31.22 ([capaInstancia.js:9-13](frontend/src/utils/capaInstancia.js#L9-L13)).

**③ El nom del POM es pinta sencer i amb la caixa correcta?** → **SÍ a les dues graelles.**
Text que embolcalla, mai un `<input>` que talli («ACROSS FRONT WIDTH (11 CM FROM HPS)» hi cap):
[EditableTable.jsx:624-663](frontend/src/components/EditableTable/EditableTable.jsx#L624-L663) i
[MeasureGrid.jsx:277,290](frontend/src/components/model/MeasureGrid.jsx#L277). La columna del nom
és de 160 px a `MeasureGrid` ([:28](frontend/src/components/model/MeasureGrid.jsx#L28)); el
`stickyTd` genèric porta `nowrap` ([:491](frontend/src/components/model/MeasureGrid.jsx#L491))
però les cel·les de CAPA i de NOM el sobreescriuen a `normal`. **La que NO se'l sobreescriu és
la columna POM** (`CodiCell`, 78 px): avui no fa mal perquè `nom_fitxa` és curt, però el fallback
`pom_code` s'hi tallaria.

---

## Q2 · LA FITXA TÈCNICA I LES SEVES TAULES (petició expressa d'Agus)

> **Veredicte curt: 🔴 la fitxa tècnica és la pantalla MÉS endarrerida del sistema, i tot el que
> li falta és UI PURA.** Els quatre payloads ja porten `capa`, `instancia`, `nom_canonic_model` i
> `nom_traduit_model`. **No espera res del backend.**

### 2.1 · Què pinten avui les taules, i d'on treuen el nom

| Taula | `kind` | Fila | Columna «ref» | Columna «POM» | Capa/Inst | Bateig |
|---|---|---|---|---|---|---|
| Mesures base | `base_measures` | [:4934-4938](frontend/src/pages/TechSheetEditor.jsx#L4934-L4938) | `nomenclaturaDePom(bm)` ✅ | `nom_en \|\| nom_client \|\| pom_code_global` | ❌ | ❌ |
| Fitxa de fitting (T1a) | `pom_fitting` | [:5002-5012](frontend/src/pages/TechSheetEditor.jsx#L5002-L5012) | `nom_fitxa \|\| pom_abbreviation` ❌ | `rule?.pom_nom_en \|\| bm.nom_en \|\| …` | ❌ | ❌ |
| Graduació final (T1b) | `pom_grading` | [:5068-5072](frontend/src/pages/TechSheetEditor.jsx#L5068-L5072) | `row.ref \|\| abbreviation \|\| codi` ❌ | `row.nom_en` / `row.nom_ca` | ❌ | ❌ |
| Repàs de fittings (T3) | `fitting_history` | [:5140-5145](frontend/src/pages/TechSheetEditor.jsx#L5140-L5145) | `row.codi \|\| row.pom_code` ❌ | `row.nom_en` / `row.nom_local` | ❌ | ❌ |

**Col·lapsen germanes?** → **NO.** Les quatre iteren la llista sencera del seu payload i el
backend ja les desancorà (`base-measurements` A3, `graded-table` `2c672aae`, `repas` `d4f97b8c`).
**Però surten indistingibles**: a ROSALIA la fitxa imprimeix

```
A       CHEST WIDTH / Ample de pit          49,0
A-FOL   CHEST WIDTH / Ample de pit          47,0     ← només el codi del client les separa
AH-L    ARMHOLE DEPTH / Profunditat de sisa 23,2
AH-R    ARMHOLE DEPTH / Profunditat de sisa 23,0
```

Amb D-31.25 haurien de dir **`Chest width` / capa `Folre`** i **`Armhole depth · Esquerra`**.

**El bateig (R1) segueix a mitges, i ara ja no hi ha excusa.** `utils/nomenclaturaPom.js` declara
`nomsDePom(bm) → {canonic, local}` com a resolutor únic **i no el consumeix NINGÚ**: l'única
referència viva a tot `src/` és un comentari. `nomenclaturaDePom()` només l'usa `base_measures`
([:4935](frontend/src/pages/TechSheetEditor.jsx#L4935)). El **panell de cotes SÍ que honora el
bateig** ([:6785-6786](frontend/src/pages/TechSheetEditor.jsx#L6785-L6786)) i les quatre taules
no → **la regla d'or d'Agus segueix trencada, exactament on estava el 31/07.**

### 2.2 · La caixa de POMs per cotar

**Porta totes les files?** → **SÍ**: `pomRows.map(bm => …)` amb `key={bm.id}`
([:6772,6801](frontend/src/pages/TechSheetEditor.jsx#L6772)). Les 13 files de ROSALIA hi són.
**Amb la seva identitat?** → **NO**: etiqueta = `cotaLabelDe(bm)` = `nom_fitxa || codi_client ||
pom_code_global` ([:304](frontend/src/pages/TechSheetEditor.jsx#L304)) — un codi curt, sense capa
ni instància ni ⓘ.

**🔴 I hi ha tres defectes durs, perquè TOT l'estat del panell està clavat a `pom_id`:**

1. **Una germana marca l'altra com a col·locada.** `cotesColocades` és un `Set` de `pomId`
   ([:5513-5521](frontend/src/pages/TechSheetEditor.jsx#L5513-L5521)) i la fila el consulta a
   [:6788](frontend/src/pages/TechSheetEditor.jsx#L6788). Posar la cota d'`A` deixa `A-FOL` amb
   el ✓ verd i **sense casella** → **el folre no es pot acotar mai**.
2. **El comptador i la selecció compten doble.** `pomsSenseCota` fa `.map(bm => bm.pom_id)`
   ([:5619-5621](frontend/src/pages/TechSheetEditor.jsx#L5619-L5621)) sense deduplicar: amb dues
   germanes sense cota, el botó diu «col·loca'n 2» quan n'hi ha una de sola a col·locar, i la
   casella d'una marca les dues (`propSel` és per `pomId`, [:6809-6810](frontend/src/pages/TechSheetEditor.jsx#L6809-L6810)).
3. **L'automàtic pot escriure un número al croquis.** `colocarCotes` cau a
   `bmUnicPerPom.get(pomId)`, que **per disseny torna `undefined` per a un POM amb germanes**
   ([:3526-3530](frontend/src/pages/TechSheetEditor.jsx#L3526-L3530)) → l'etiqueta es resol a
   `String(pomId)` i el croquis rep una cota que diu **«273»**
   ([:5654-5658](frontend/src/pages/TechSheetEditor.jsx#L5654-L5658)).

`bmUnicPerPom` **no és el bug**: és el guard conscient que va evitar lligar una cota (i desar-la
al `.ftt`) a una germana triada a l'atzar, i la seva capçalera ja diu que **què ha de fer la
col·locació automàtica amb un POM de dues cares és una decisió de producte**
([:3522-3525](frontend/src/pages/TechSheetEditor.jsx#L3522-L3525)). Va a Q6 · DECISIÓ.

### 2.3 · El PDF exportat: diu el mateix que la pantalla?

**SÍ, i és estructural.** L'export renderitza les MATEIXES pàgines Konva a PNG i les encasta amb
`pdf-lib` ([:5323-5342](frontend/src/pages/TechSheetEditor.jsx#L5323-L5342)); les files de la
taula són **cadenes congelades** al `.ftt` en el moment d'inserir-la. **Conclusió: el PDF no té
cap defecte propi — hereta exactament els de la pantalla.** Arreglar les 4 expressions arregla el
paper el mateix dia, **però només per a les taules que s'insereixin a partir d'aleshores**: les
ja col·locades porten el text congelat i s'han de tornar a inserir.

---

## Q3 · FITTING — EL CICLE COMPLET DE PROGRAMACIÓ (petició expressa d'Agus)

### 3.1 · Programar: on es crea la convocatòria i què es pot triar

**Dues portes, cap d'elles a la pestanya del model:**

| Porta | Fitxer | Què fa |
|---|---|---|
| Menú **⋯ Accions** del model | [ActionsMenu.jsx:433-482](frontend/src/components/model/ActionsMenu.jsx#L433-L482) | 1 model → `schedule` · N models → `schedule-bulk` amb **UUID de convocatòria** ([:176-186](frontend/src/components/model/ActionsMenu.jsx#L176-L186)) |
| **+ Fitting aquí i ara** a `/fittings` | [FittingSessionList.jsx:549](frontend/src/pages/FittingSessionList.jsx#L549) | `schedule-now`: un clic, cap formulari |

**Què es pot triar al formulari** ([ActionsMenu.jsx:443-482](frontend/src/components/model/ActionsMenu.jsx#L443-L482)):
fase · **data** · hora d'inici · durada (min) · **assistents** (multi-selecció de perfils, el
primer premarcat) · `expected_at`. Amb N models, les sessions surten **encadenades** (la i+1 on
acaba la i).

**Què NO es pot triar en programar:**
- **La peça.** No hi ha concepte de peça en programar: 1 sessió = 1 model, i el `PieceFitting` es
  **materialitza en obrir** ([measureSources.jsx:39-58](frontend/src/components/model/measureSources.jsx#L39-L58)).
- **El lloc** (`lloc`) i **qui es prova la peça** (`model_persona`). Els camps existeixen al
  model de dades i només s'editen **després**, a la capçalera de la sessió (`SessionPanel`).
  Programar un fitting sense poder dir on és, és el forat més visible d'aquest formulari.

**On es veu al calendari:** `/planificacio/calendari` → `PlanningCalendar`, font
`GET /api/v1/calendar/events/` ([planning/views.py:214](backend/fhort/planning/views.py#L214)).
Bloc horari **per assistent**, color del tècnic; sense hora, marcador de dia.

### 3.2 · 🟢 G7 — la convocatòria replicada cada dia: **MORTA, i verificada morta**

El fix viu a [planning/views.py:429-497](backend/fhort/planning/views.py#L429-L497): per cada
(convocatòria × assistent) s'emet **un marcador per sessió REAL**, cadascun al seu dia, `start`
== `end`. El vell rang «primera→última» ha desaparegut. El mateix criteri s'ha aplicat a
`confeccio` ([:302-307](backend/fhort/planning/views.py#L302-L307)).

**Prova executada avui** sobre la convocatòria real `79e06e8a…` (5 sessions, 4 assistents,
2026-07-11 i 07-13): 20 events, **20 de 20 amb dia d'inici == dia de fi**. Cap dia buit ocupat.

**Però queden dues coses que Agus ha de saber:**

- 🚩 **La maquinària de rèplica segueix viva al front.** `inRange` escampa qualsevol event
  *all-day* de `_start` a `_end` ([PlanningCalendar.jsx:171-178](frontend/src/pages/PlanningCalendar.jsx#L171-L178)).
  Avui és inofensiva perquè el backend emet `start==end`; el dia que algú torni a emetre un rang,
  G7 reneix sense tocar el front. **No és urgent; és un rastrell al terra.**
- 🔴 **Els marcadors de convocatòria no diuen de quin model són.** El títol és
  `Fitting · {n} models · {fase}` per a tots ([:476](backend/fhort/planning/views.py#L476)) i
  l'enllaç va a `/fittings`, no a la sessió ([:485,495](backend/fhort/planning/views.py#L485)).
  Mesurat: el 13/07 el calendari ensenya **4 pastilles idèntiques** de 10 min consecutius, cap
  amb el codi del model. **Això sí que és el que la Montse veurà i no entendrà.**

### 3.3 · El flux sencer: quins passos tenen pantalla i quins no

| Pas | Pantalla? | On |
|---|---|---|
| **Programar** | ✅ | `ActionsMenu` (⋯ del model) · `+ Fitting aquí i ara` (`/fittings`) |
| **Convocar** | 🟡 **a mitges** | `FittingConvocatoriaSheet` (`/fittings/convocatoria/:uuid`) és una **fulla de LECTURA** (models del dia, hora, estat, watchpoints oberts). **No convoca ningú**: no hi ha avís, ni correu, ni notificació. `assistents` és a més un **camp de text lliure** al costat del M2M `attendees` real — dues nocions d'assistent conviuen |
| **Obrir sessió** | ❌ **cap botó** | La transició `Programada → Oberta` **no té gest propi**. Passa de rebot quan s'entra a Mesures amb `?fitting_session=`: `open-task` obre la sessió pel darrere ([tasks/views_b.py:614-615](backend/fhort/tasks/views_b.py#L614-L615)). `fittingSessions.open()` està declarat a [endpoints.js:653](frontend/src/api/endpoints.js#L653) i **no el crida ningú** |
| **Mesurar** | ✅ | `/models/:id?tab=Mesures&fitting_session=:sid`. `/fittings/:id` d'una sessió VIVA **redirigeix** allà ([FittingDetail.jsx:564-566](frontend/src/pages/FittingDetail.jsx#L564-L566)) |
| **Tancar** | ✅ | `SessionActions`: «Gravar i tornar» = `close` peça → `seal` sessió → tasca `Done` ([SessionActions.jsx:28-45](frontend/src/components/model/SessionActions.jsx#L28-L45)) |
| **Revisar el tancat** | ✅ | `/fittings/:id` en mode lectura (split 40/60) |
| **Full de paper** | ✅ | `FittingPrintSheet` (P5, `effef65f`) — **amb identitat sencera** |

### 3.4 · 🔴 La llista de sessions d'un model: **NO es veu enlloc**

- No hi ha pestanya «Fitting» al model ([ModelSheet.jsx:34](frontend/src/pages/ModelSheet.jsx#L34)).
- El **Repàs** ensenya les sessions **com a columnes** de la graella, sense estat, sense enllaç, i
  només les que tenen preses ([FittingRepasPanel.jsx](frontend/src/components/model/FittingRepasPanel.jsx)).
- Les **fites del Dashboard** només miren 14 dies **endavant**.
- **El component que fa exactament el que Agus demana ja existeix i està DESCONNECTAT:**
  **[FittingTab.jsx](frontend/src/components/model/FittingTab.jsx)** — taula fase · data · **estat**
  · enllaç al detall, `fittingSessions.list({model:id})`. **Cap fitxer l'importa.** 46 línies
  escrites, provades i òrfenes.

### 3.5 · El veredicte del fitting — ✅ tancat mentre es feia aquest cens

La interacció sencera (color al número, tecles A/J/R, botons) ja era a la pantalla; el que faltava
era **on desar-lo**. La sessió de backend paral·lela ho va tancar amb **`fd102c06`** (camp
`PieceFittingLine.decisio`, migració aplicada i verificada). **La UI no s'ha hagut de tocar**: el
pendent estava anotat a [measureSources.jsx:75-80](frontend/src/components/model/measureSources.jsx#L75-L80)
i s'hi ha endollat sol. **Queda una sola cosa: mirar-ho a pantalla** — que el veredicte sobrevisqui
a recarregar la sessió 147.

---

## Q4 · LES LLISTES I EL GLOBAL

| Pantalla | Estat | Nota |
|---|---|---|
| **Llista de models** (`/models`) | ✅ | Filtres avançats, URL font de veritat. **No mostra POMs** → cap qüestió de germanes |
| **Kanban** | ✅ | El global està **jubilat**; el board per model viu a `Dashboard.jsx` (`/`) ([App.jsx:355](frontend/src/App.jsx#L355)) |
| **Planificació** (`/planificacio`) | ✅ | Gantt + cua per tècnic. Sense POMs |
| **Calendari** (`/planificacio/calendari`) | 🟡 | Q3.2: G7 mort, però les pastilles de convocatòria no diuen el model |
| **Fittings** (`/fittings`) | ✅ | Grups de convocatòria plegables + individuals; estat amb badge, assistents amb punts de color, accions per fila i per grup. **És pantalla nova** |
| **Fulla de convocatòria** | ✅ | Lectura + watchpoints oberts per model |
| **Cercadors** | ✅ | `CascadeSelector` unificat; `poms/cerca/` per al catàleg |
| **Catàleg de POMs** (`/poms`) | ✅ | És el catàleg (`POMMaster`), no mesures de model: capa i instància **no hi apliquen** per definició |

**Cap llista global col·lapsa germanes**, perquè cap llista global baixa al nivell de la mesura.
El col·lapse viu tot dins del model (Q1.5 i Q2).

**🔵 Trobat de passada:** [ModelFabric.jsx:120](frontend/src/pages/ModelFabric.jsx#L120) navega a
`/tasques/kanban`, **ruta que no existeix** → el `*` de l'`App.jsx` reboteja l'usuari a l'arrel.
Una línia.

---

## Q5 · ELS DETALLS QUE JA SABEM I ELS QUE HE TROBAT

1. **Botó Graduació → el wizard del model (P11 pendent).** [ModelSheet.jsx:703-724](frontend/src/pages/ModelSheet.jsx#L703-L724)
   obre `ModelWizard` amb `initialBlock={4}` en calaix lateral. **No és cap pantalla morta**: el
   pas 4 renderitza `GraduacioPanel`, que és el component viu ([ModelWizard.jsx:776-780](frontend/src/pages/ModelWizard.jsx#L776-L780)).
   El que queda és que graduar segueixi passant per la pell del «wizard d'editar model».
   **UI pura, però és re-enquadrar, no arreglar.**

2. **🔴 El tint de fila no-exterior: no existeix, i el token tampoc.** La maqueta v8.1 el declara
   —`--lining:#fbf6ee` i `tbody tr.lin td{background:var(--lining)}` (`maqueta_mesures_carril_v8_1.html:12,45`)—.
   A l'app: **cap token `--lining`** a [index.css](frontend/src/index.css), i
   **`esGermanaDeCapa()` ([capaInstancia.js:61](frontend/src/utils/capaInstancia.js#L61)) té ZERO
   consumidors**. La funció es va escriure «per si cal marcar-la» i mai s'ha cridat. **UI pura:
   token nou + una línia a cada graella.**

3. **🔴 No hi ha cap gest per CREAR una germana.** `AddPOMInline`
   ([EditableTable.jsx:809-900](frontend/src/components/EditableTable/EditableTable.jsx#L809-L900))
   afegeix una fila des del catàleg **sense capa ni instància** → el backend hi posa
   `('exterior','')`. La columna de capa és **lectura per decisió explícita**
   ([:497-505](frontend/src/components/EditableTable/EditableTable.jsx#L497-L505)): «moure una
   mesura de capa és partir-la en dues, i això és un acte propi». **Aquest acte no s'ha construït.**
   La maqueta v8.1 sí que el té: botó per fila «Germana de capa · tecla **L**» i cercador amb
   drecera `«C.f» folre · «S.l» left`. Les 4 germanes de ROSALIA hi són perquè algú les va sembrar
   per script.
   **Tot el que hi ha sota ja està preparat**: el payload d'escriptura porta els dos eixos
   ([:230-231](frontend/src/components/EditableTable/EditableTable.jsx#L230-L231)) i la poda també
   ([:252-254](frontend/src/components/EditableTable/EditableTable.jsx#L252-L254)). **UI pura.**

4. **🔴 `POMAlert` no té UI. Cap.** El model té capa i instància des de la migració `0021`
   ([fitting/models.py:149-155](backend/fhort/fitting/models.py#L149-L155)) i el commit `d53a31a8`
   («una alerta per germana, no una per POM»). Al front, `pomAlerts` està declarat a
   [endpoints.js:723-725](frontend/src/api/endpoints.js#L723-L725) i **no l'importa ningú**. Una
   funcionalitat de backend sencera, ja adaptada a C4, **sense cap superfície on es vegi**.

5. **La caixa de frase i els acrònims (CF/CB/HPS).** Dues coses diferents:
   - **Els acrònims es pinten BÉ** allà on hi ha graella: el nom embolcalla i no es talla mai
     (Q1.3-ter ③). Les maquetes els porten dins de frases llargues («ACROSS FRONT WIDTH (11 CM
     FROM HPS)», «WAIST POSITION FROM HPS») i les dues graelles hi caben.
   - **Les frases de coherència són MORTES.** `coherence.chest_waist` / `back_front_rise` /
     `sleeve_cb` existeixen als tres idiomes ([i18n/ca.json:3104-3108](frontend/src/i18n/ca.json#L3104-L3108))
     i **no les consumeix ningú, ni al front ni al backend**. La caixa que les hauria de pintar no
     s'ha escrit. **Encaixa a la secció «a revisar» de la Comprovació** (Q6).
   - 🚩 Frase relacionada: `RelationsPanel` i `ProposalsPanel` del Taller reconstrueixen el text al
     client **perquè el backend l'escriu en català pla** ([RelationsPanel.jsx:15](frontend/src/components/pattern/RelationsPanel.jsx#L15)).
     Funciona; queda anotat com a patró a no repetir.

6. **El bateig de traducció:** v. Q2.1. `nomsDePom()` escrit i **no consumit per ningú**.

7. **🟢 Llei que NO s'ha de tocar (i que la UI hauria de dir).** `ModelGradingRule` **no té capa ni
   instància, per decisió de domini amb acta** (C1 §3c / C1-ins), i hi ha tests que **vigilen que
   la columna no hi sigui** ([models_app/models.py:1005-1020](backend/fhort/models_app/models.py#L1005-L1020)).
   Per tant `setPomRegim(modelId, pom_id, …)` ([endpoints.js:96](frontend/src/api/endpoints.js#L96))
   **és correcte**: la regla és compartida per les germanes a posta. **El que la UI no diu és
   això**: qui editi el règim a la fila del folre està editant també el de l'exterior i res no
   l'avisa. Un peu de cel·la, no un canvi de model. El mateix val per a `PatternPOM`
   ([patterns/views.py:605-610](backend/fhort/patterns/views.py#L605-L610)).

8. **`FittingTab.jsx` òrfena** (Q3.4) i **`/tasques/kanban` inexistent** (Q4).

---

## Q6 · LA LLISTA DE DEMÀ

> Ordenada **pel que la Montse tocarà el primer dia**: definir mesures → mirar la fitxa → anar al
> fitting. Dins de cada bloc, de més amunt a menys.

### 🟩 BLOC A · UI PURA — es pot fer sense tocar el backend

| # | Feina | On | Mida |
|---|---|---|---|
| **A1** | **Les 4 taules de la fitxa diuen la capa i la instància.** Els payloads ja les porten (verificat en viu) | `TechSheetEditor.jsx:4934 · 5002 · 5068 · 5140` | **M** |
| **A2** | **Consumir `nomsDePom()` a les 4 taules** (tanca R1: el bateig arriba al paper) i convergir-hi `cotaLabelDe` i el `pom_abbreviation` de la T1a. **Mateixes 4 expressions que A1 → fer-ho el mateix dia** | ídem + `TechSheetEditor.jsx:304` | **S** |
| **A3** | **El panell de cotes deixa de clavar-se al `pom_id`**: `cotesColocades`, `propSel` i `pomsSenseCota` han de treballar per `bm.id`. Tanca les tres: germana marcada per l'altra, comptador doble, i la cota que diu «273» | `TechSheetEditor.jsx:5513 · 5619 · 6788 · 6809` | **M** ⚠️ depèn de D1 |
| **A4** | **El gest de crear una germana** a la taula de Mesures: botó de fila «Germana de capa» + instància, tecla `L`, drecera al cercador. Tot el que hi ha sota ja hi és | `EditableTable.jsx:809` + `MeasuresEntryPanel` | **M** |
| **A5** | **El tint de fila no-exterior**: token `--lining` a `index.css` + `esGermanaDeCapa()` a les dues graelles (avui la funció no la crida ningú) | `index.css` · `EditableTable.jsx:487` · `MeasureGrid.jsx:583` | **XS** |
| **A6** | **El Taller de Patró pinta capa i instància.** El backend ja les serveix; a més, un peu que digui que els ancoratges són compartits (llei `PatternPOM`) | `ModelPomList.jsx:92,134,143` | **S** |
| **A7** | **Reconnectar `FittingTab`** com a llista de sessions del model (fase·data·**estat**·enllaç). Ja escrita | `ModelSheet.jsx:34` + `FittingTab.jsx` | **XS** |
| **A8** | **Les pastilles de convocatòria diuen el model i enllacen a la sessió** (avui totes diuen «Fitting · 5 models · Proto» i van a `/fittings`) | `planning/views.py:476,485,495` | **S** |
| **A9** | **Peu de cel·la al règim**: «aquesta regla la comparteixen les N germanes d'aquest POM» | `CheckMeasureEditor.jsx:284-297` | **XS** |
| **A10** | **Un gest explícit d'«Obrir sessió»** (avui s'obre de rebot). `fittingSessions.open()` ja existeix i no el crida ningú | `FittingSessionList.jsx` · `endpoints.js:649` | **S** |
| **A11** | **Netejar `/tasques/kanban`** (ruta inexistent) | `ModelFabric.jsx:120` | **XS** |
| **A12** | **`lloc` i `model_persona` al formulari de programar** (avui només s'editen després) | `ActionsMenu.jsx:443-482` | **S** |
| **A13** | **Treure `inRange` dels all-day** o assegurar-lo per contracte, perquè G7 no pugui renéixer | `PlanningCalendar.jsx:171-178` | **XS** |

### 🟨 BLOC B · ESPERA BACKEND — amb QUÈ espera, exactament

| # | Feina | Espera QUÈ | Estat |
|---|---|---|---|
| **B1** | **Veredicte del fitting (D-31.21)** — A/J/R al costat del número | Camp `PieceFittingLine.decisio` + serializer + PATCH | **✅ TANCAT durant el cens** (`fd102c06`, columna aplicada i verificada). La UI ja hi era i **no s'ha hagut de tocar**: el pendent estava anotat a [measureSources.jsx:75-80](frontend/src/components/model/measureSources.jsx#L75-L80) i s'hi ha endollat sol. **Queda comprovar-ho a pantalla** |
| **B2** | **Llegir el catàleg de capes en comptes de la constant** | Un **endpoint** que publiqui `pom.MeasurementLayer` (avui no n'hi ha cap) + confirmar la sembra **a PROD** | 🟡 **Mig resolt**: `33451704` va comprovar que el catàleg **ja està sembrat** amb les sis capes als tres schemas de staging i que **no hi ha cap fila òrfena** (9 taules escombrades). La premissa «el catàleg és buit» de [capaInstancia.js:15-20](frontend/src/utils/capaInstancia.js#L15-L20) **ja no val per a staging**; queda **PROD** i **el lector**. Sense pressa: la constant del front funciona |
| **B3** | **Diccionari d'instàncies** | Avui `left-relaxed` es desmunta per guions i els trams desconeguts surten crus. El diccionari arriba amb C4-ins | 🚩 Decisió + dades, no codi de front |
| **B4** | **Pantalla de Comprovació** (v. C1) | Un agregador que digui **què bloqueja** i **què s'ha de mirar**: mesures sense valor, mesures que van quedar enrere quan la base es va moure, preses descartades, fora de tolerància, i famílies incompletes | **🔴 no existeix ni al backend ni al front** |
| **B5** | **Pantalla d'alertes de POM** | Res: `POMAlert` ja és complet i ja distingeix germanes. **El que falta és la UI** — però la decisió d'on va (tab? watchpoints? Comprovació?) és d'Agus | v. D3 |

### 🟥 BLOC C · EL QUE NO EXISTEIX I ÉS GROS

| **C1** | **La pantalla de COMPROVACIÓ (D-31.17).** Maqueta **aprovada**, zero línies escrites. És la 3a subvista de Mesures (`Taula · Repàs · Comprovació`); avui el commutador només en té dues ([ModelSheet.jsx:598-613](frontend/src/pages/ModelSheet.jsx#L598-L613)). La maqueta diu que **«les tres primeres seccions funcionen amb el sistema actual»** i que la de famílies neix quan hi ha germanes — i ja n'hi ha. **És l'única peça del cens que és una pantalla sencera, no un retoc.** |
|---|---|

### 🔵 BLOC D · DECISIÓ D'AGUS — formulades com a pregunta

**D1 · Un POM de dues cares al croquis: una cota o dues?**
És el bloqueig d'A3 i està anotat al codi ([TechSheetEditor.jsx:3522-3525](frontend/src/pages/TechSheetEditor.jsx#L3522-L3525)).
- **(a)** *Una cota per germana*, cadascuna amb la seva identitat («A» i «A-FOL»). Diu la veritat, però omple el croquis: ROSALIA passaria de 12 a 13 cotes i el folre no es dibuixa.
- **(b)** *Una sola cota per POM*, la de l'exterior, i la germana no s'acota mai. És el que passa avui **per accident**; convertir-ho en llei el fa previsible.
- **(c)** *Una cota per POM amb l'exterior com a titular i les altres cares al tooltip.* El croquis no canvia i la informació no es perd. **Recomanació**, però és la que costa més.

**D2 · L'automàtic de cotes, què fa amb un POM de germanes?**
Avui col·loca **dues** cotes i n'etiqueta almenys una amb el número del POM. Cau sol si es tria (a) o (c) a D1; si es tria (b), l'automàtic ha de **saltar-se** les germanes en silenci o **dir-ho**.

**D3 · On viuen les alertes de POM?** Existeixen, distingeixen germanes, i no es veuen.
- **(a)** Dins de **Comprovació** (secció «fora de tolerància al darrer fitting» — la maqueta ja hi té el forat).
- **(b)** Al calaix de **Watchpoints**, amb la resta d'avisos del model.
- **(c)** Pestanya pròpia. **Recomanació: (a)** — és el motiu pel qual la Comprovació existeix.

**D4 · «Convocar» vol dir avisar algú?** Avui la fulla de convocatòria **no notifica ningú**, i
conviuen dos conceptes d'assistent: `attendees` (M2M de perfils, el que va al calendari) i
`assistents` (text lliure). Cal (a) unificar-los i deixar el text lliure per als externs, o
(b) mantenir-los i dir a la pantalla què és cadascun.

**D5 · La regla de graduació compartida entre germanes: es diu o no es diu?**
La llei és ferma i té tests que la vigilen. La pregunta és només d'UI: **A9** (un peu que ho digui)
o **res** (qui hi treballi ja ho sap). Recomanació: **dir-ho** — és exactament el tipus de cosa
que la Montse descobrirà editant el folre i veient moure's l'exterior.

---

## Annex · el que es podria dir «ja està fet» i convé no re-obrir

- **Δ de Mesures**: llegeix per `row.clau`, no per `pom_id` ([EditableTable.jsx:198-201](frontend/src/components/EditableTable/EditableTable.jsx#L198-L201)). El bug que la buidava **a tots els models** és mort.
- **Clau de React per fila**: `rowKey` a `CheckMeasureEditor:237`, `repasGridAdapter:130`, `fittingGridAdapter:142,318`. Cap col·lisió amb germanes.
- **Escriptura i poda de Mesures**: porten els dos eixos (`EditableTable:230-231, 252-254`).
- **`patterns/model-poms`**: l'àncora **ja ha caigut** (`6c71004d`) — la nota de sessions anteriors que la donava per oberta ha quedat enrere. El pendent és **només de front**.
- **i18n**: `capa.*` i `instancia.*` complets i paritaris a ca/en/es.
- **G7**: mort al backend i **verificat avui amb dades reals**.
- **PDF de la fitxa**: no té defecte propi; hereta el de la pantalla.
