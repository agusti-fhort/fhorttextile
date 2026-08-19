# DIAGNOSI · Les pantalles vives contra les maquetes aprovades

> **Data:** 2026-08-05 · **Patró A (read-only)** · cap fitxer de codi modificat en aquesta fase.
> **Font canònica:** `ops/maquetes/maqueta_mesures_carril_v8_1.html` (D-31.18) i
> `ops/maquetes/maqueta_fitting_v3.html` (D-31.7/19/21), llegides senceres.
> **La maqueta mana; la pantalla viva no és la referència.**

## 0 · Per què aquest cens, i què hi ha sortit

Aquest tram existeix perquè ningú havia contrastat les dues pantalles amb la seva maqueta
des que es van aprovar (04/08). El resultat no és el que el brief esperava:

- **Mesures** s'ha apartat de la v8.1 sobretot **per defecte**: hi falten sis blocs, i quatre
  d'ells són el gruix del gest d'instància.
- **Fitting** s'ha apartat de la v3 **molt menys del que semblava**: el paginat, els tres
  veredictes, la nota per línia, la instància dins del nom i el PDF A4 apaïsat **ja hi són**.
- **La sorpresa gran no és una absència: són dos comentaris rancis que menteixen**, i tots dos
  fan que el codi sembli el contrari del que és. Un amaga que el veredicte ja es desa al
  backend; l'altre diu que un bloc de mitja pantalla no existeix quan hi és. Els dos es
  documenten a §1-bis i §2.4.

### La superfície viva del fitting NO és la pàgina de fitting

Cal dir-ho abans de qualsevol taula, perquè canvia què s'està comparant:

| | |
|---|---|
| `pages/FittingDetail.jsx:564-566` | Una sessió **viva** (Oberta/Programada) **no es treballa aquí**: `<Navigate to={/models/:id?tab=Mesures&fitting_session=:id}>`. |
| `pages/ModelSheet.jsx:830-836` | La superfície REAL del fitting és `CheckMeasureEditor` amb `source=fittingSource` i `lockRules`. |
| `pages/FittingDetail.jsx:679-708` | El que queda a `FittingDetail` és **només el split de LECTURA** de sessions segellades. |

És la dissolució de l'Sprint Y. La maqueta v3 descriu una pantalla de treball; la pantalla de
treball d'avui és el tab Mesures amb context de sessió. **El cens de §2 es fa contra aquesta**,
no contra `FittingDetail`.

---

## 1 · MESURES · pantalla viva vs maqueta v8.1

**Superfície viva:** tab Mesures del model → «Definició de POMs i talla base»
`components/model/MeasuresEntryPanel.jsx:418-481` (mode `manual`) →
`components/EditableTable/EditableTable.jsx` (1104 línies, la taula sencera).

| # | Bloc de la v8.1 | Estat | Àncora viva |
|---|---|---|---|
| M1 | **Píndoles d'instància per DIMENSIÓ** (`lat`: Left/Right · `st`: Relaxed/Extended), amb `dimState` (qui la té, qui queda deshabilitada) i tooltip per estat | **NO HI ÉS** | El gest existeix però amb una **altra forma**: botó de fila `EditableTable.jsx:668-675` → modal `GermanaDialog` `EditableTable.jsx:707-803`. No hi ha eix de dimensions, ni repartiment entre germanes, ni deshabilitat, ni tooltips d'estat. Maqueta: `dimState()` línies 235-242, píndoles 248-253. |
| M2 | **Botó `＋` de posició i combinacions** (modal complet) | **NO HI ÉS** | Cap equivalent. Maqueta: `.qmore` línia 268 + 361-363. |
| M3 | **Germana de CAPA: botó dedicat** | **HI ÉS** | `EditableTable.jsx:668-675` (icona `ti-layers-subtract`) → `GermanaDialog` mena `'capa'` `:761`. |
| M3b | **Germana de capa: tecla `L`** | **NO HI ÉS** | `CarrilInput` només escolta ↓/↑/Enter/Escape: `EditableTable.jsx:889-893`. Maqueta: `:334`. |
| M3c | **Files de capa no-Exterior amb fons propi** (`--lining`) | **NO HI ÉS** | El fons de fila només distingeix `isDragging`: `EditableTable.jsx:533`. La capa es llegeix a la columna (`:556-558`) però no tenyeix la fila. Maqueta: `tr.lin` `:45-46`. |
| M4 | **Nomenclatura curta EDITABLE, en or** (`input.nomen`) | **HI ÉS** | `NomenInput` `EditableTable.jsx:910-933` — or, monospace, vora només en hover/focus, commit on blur. Coincideix amb la maqueta `:59-62`. |
| M5 | **Cercador de POM al peu de taula** | **HI ÉS PARCIAL** | `AddPOMInline` `EditableTable.jsx:990-1104`: cerca per codi/nom + porta de creació conscient. **Falta:** la sintaxi de sufixos («C.f» folre · «S.l» left), l'agrupació per nivell (de l'item / del type / del catàleg) i el ↓ des de l'última fila. Maqueta: `filter()` `:398-413`, `paint()` `:414-427`. |
| M6 | **Files en blanc marcades «· es descartarà»** | **HI ÉS PARCIAL** | La fila **es rebaixa** (`opacity` `:572`) i el motiu viatja al `title` de l'input (`:621`, clau `editable_table.row_discarded`). **Falta el text visible al costat del nom**, que és el que la maqueta fixa: `tr.void .pomname::after` `:48`. |
| M7 | **Barra d'estat: N informats · N en blanc** | **HI ÉS** | `EditableTable.jsx:375-376` (càlcul) i `:491-493` (render). Claus `count_filled`/`count_empty` ja a ca/en/es (`i18n/*.json:3223-3224`). Diferència menor: la maqueta la fixa a peu de finestra (`.statusbar` `:140-144`); la viva és una línia sota la taula. |
| M7b | **Indicador desant… / desat** | **NO HI ÉS** | Cap indicador, tot i que la taula té **tres portes que desen immediatament**: bateig `:136-139`, regla `:146-162`, i el desat de taula `:312-348`. Maqueta: `flashSave()` `:289-291`. |
| M8 | **Fila activa ressaltada** | **NO HI ÉS** | Cap classe/estat de fila enfocada. El fons de fila és fix (`:533`). Maqueta: `tr.cur` `:44` + `markCur()` `:284`. |
| M9 | **Animació de naixement** | **NO HI ÉS** | Les files noves (germana `:219-224`, POM afegit `:181`) apareixen sense cap senyal. Maqueta: `tr.born` + `@keyframes born` + `prefers-reduced-motion` `:49-51`. |
| M10 | **Arrossegar per reordenar** | **HI ÉS** | `@dnd-kit` — sensors `:72-75`, `handleDragEnd` `:77-87`, `SortableContext` `:438-463`, nansa `:543-546`. |
| M11 | **Carril de valor: capçalera amb la talla base gran i etiquetada** | **HI ÉS PARCIAL** | La columna hi és i destaca (`--gold-pale`), però la capçalera és **només el literal de la talla**: `EditableTable.jsx:419-421`. Falta l'etiqueta «Talla base» a sobre i el cos gran. Maqueta: `th.baseh` amb `.lbl`+`.sz` `:38-42` i `:174`. |
| M12 | **El carril: ↓/Enter baixa, ↑ puja, focus dins la columna** | **HI ÉS** | `CarrilInput` `:857-904`, navegació `navVal` `:123-128`, registre per `row.id` `:116-120`. |
| M13 | **La instància dins del NOM, paraula sencera** | **HI ÉS** | `NomCanonic` `:817-845`, instància `:837`, vocabulari a `utils/capaInstancia.js:53-58`. |

### 1-bis · I A L'INREVÉS: què hi ha a la viva que NO és a la v8.1

#### La columna REGLA DE GRADUACIÓ (RÈGIM · DELTA · DELTA BREAK · TALLA BREAK)

**Ocupa quatre columnes de la meitat dreta i no surt enlloc de la v8.1.**

- **On és:** capçaleres `EditableTable.jsx:422-436`, cel·les `:623-662`, escriptura
  `handleRegla` `:146-162` (upsert de `ModelGradingRule` via `models.setPomRegla`).
- **D'on ve:** `ff23c7f4` · *«feat(mesures): les columnes de Regla es veuen sempre, i el gest
  s'obre des de la taula»* · **31/07/2026**, W2/W3 del contracte, **decisió explícita d'Agus**.
  Abans: `88df681d` les havia tornat condicionades; `4780945b` les havia tretes del tot.
- **Què fa:** deixa entrar la graduació **a mà** a qui cancel·la el wizard. Les columnes es
  mostren SEMPRE, buides si el model no gradua, i el guió diu la veritat. La protecció del
  model 1302 es manté: **mai pre-omplertes**, i `buildPayload` **no envia `rules`** (`:298-304`),
  de manera que desar mesures no fabrica cap regla.
- **Té maqueta pròpia?** **No.** No apareix ni a la v8.1, ni a `maqueta_fitting_v3`, ni a
  `maqueta_comprovacio_v2`. La seva justificació viu al missatge de commit i a `DECISIONS.md`,
  no a cap HTML aprovat.

> ⚠️ **El conflicte és de dates, i és real.** La decisió d'Agus és del **31/07**; la v8.1 es
> declara vigent i APROVADA el **04/08** (`ops/maquetes/README.txt`) i **no porta el bloc**.
> O la maqueta el va ometre per descuit, o el va superar. **No ho pot decidir un agent** → §5.

#### 🔴 Un comentari de 12 línies que diu el contrari del codi que encabeix

`EditableTable.jsx:398-409` afirma, amb tot detall i citant el QA del model 1302:

> *«LA GRADUACIÓ NO ES VEU AQUÍ (decisió d'Agus, 31/07). Fins avui aquesta taula portava el
> bloc "Regla de graduació"… El QA del model 1302 va ensenyar per què no hi pot ser…»*

I **just a sota** (`:422-436`) la taula pinta aquell bloc. El comentari és el de `4780945b`
(que sí que el va treure) i **ningú el va actualitzar** quan `ff23c7f4` el va tornar, poques
hores després el mateix dia. Els `{( … )}` buits de `:422` i `:429` són la cicatriu de la
condició `teRegles` esborrada.

**No és una divergència de maqueta: és deute de documentació dins d'una zona sensible.** Qui
llegeixi aquest fitxer buscant per què es veu la regla trobarà escrit que no s'hi veu.

#### Altres presències vives fora de la v8.1 (totes justificades)

| Element | Àncora | Origen |
|---|---|---|
| Columna **CAPA** en lectura, sempre present | `EditableTable.jsx:550-558` | D-31.22. La v8.1 la té com a `<select>` editable (`:259-263`); **la viva la fa lectura a posta** — moure de capa és partir en dues, i això és un acte propi. |
| Columna **d'accions** (germana + treure fila) | `:663-683` | F4 + poda. |
| **★ KEY** | `:567-570` | Llegat del catàleg. |
| **ⓘ de traducció** al nom | `:838-842` | v8.1 sí que la té (`:266`), amb la variant que la viva l'amaga si repeteix el nom (`:585-587`). |
| Avís de **taula importada per IA** | `:380-392` | Camí d'import. |
| Botó **Graduació** i **Importar taula** | `MeasuresEntryPanel.jsx:429-445` | 31/07. |

---

## 2 · FITTING · pantalla viva vs maqueta v3

**Superfície viva:** `ModelSheet.jsx:830-836` → `CheckMeasureEditor` amb
`components/model/measureSources.jsx:60-110` (`fittingSource`) →
`components/model/fittingGridAdapter.jsx` + `components/model/MeasureGrid.jsx`.

| # | Bloc de la v3 | Estat | Àncora viva |
|---|---|---|---|
| F1 | **Capa** | **HI ÉS** | Columna pròpia, sticky, en lectura: `MeasureGrid.jsx:583-586` (`etiquetaCapa`). |
| F2 | **Codi** | **HI ÉS** | `CodiCell` `MeasureGrid.jsx:314-355`; la nomenclatura curta del model mana sobre el catàleg (`fittingGridAdapter.jsx:135`). |
| F3 | **Nom amb la INSTÀNCIA DINS del nom, en negre** | **HI ÉS** | `NomCell` `MeasureGrid.jsx:217-224` i `:290`; `Inst` es pinta amb el color del nom (`:224`), no com a etiqueta. |
| F4 | **Històric PAGINAT de dos en dos amb ‹ ›** | **HI ÉS** | `HIST_FINESTRA = 2` `fittingGridAdapter.jsx:25`, `PaginadorHistoric` `:27-46`, `finestraHistoric` `:49-52`, finestra `:64-65`, estat `CheckMeasureEditor.jsx:341-344`. |
| F4b | **La columna de treball no es mou** | **HI ÉS** | L'activa és sempre l'última del grup: `MeasureGrid.jsx:556`. |
| F5 | **TRES veredictes ACCEPTED/ADJUSTED/REJECTED** | **HI ÉS** | `VERDICTES` `fittingGridAdapter.jsx:157`, `VerdicteCell` `:164-193`; el color va **al número** i el REJECTED el ratlla: `MeasureGrid.jsx:107` i `:133-144`, `:180-187`. |
| F5b | **Dreceres `a` / `j` / `r`** | **HI ÉS** | `TECLA_VERDICTE` `MeasureGrid.jsx:111`, escolta al camp del número `:169-179`, i només quan hi ha `onVeredicte`. |
| F5c | **🔴 El veredicte SOBREVIU a la recàrrega** | **NO HI ÉS** | **Defecte viu, i no és de maqueta.** Vegeu §2.4. |
| F6 | **Nota per línia** | **HI ÉS** | `NotaFittingCell` `fittingGridAdapter.jsx:198-217`, sempre oberta, desa on blur via `pieceFittingLines.update` (`CheckMeasureEditor.jsx:338-339`). |
| F7 | **Germanes derivades amb folgança i «NO ACTUALITZADA»** | **NO HI ÉS** | Cap ocurrència de folgança/DERIVADA/NO ACTUALITZADA a tot `frontend/src`. **El backend ja serveix el que cal**: `fitting/serializers.py:357` emet `origen` (`'DERIVAT'`) per línia, amb el comentari «*la pantalla ja té tot el que cal per etiquetar-ho*». `fittingGridAdapter.jsx` **no llegeix `origen`**. Maqueta: `SISH`/`R.sis` `:220-230`, render `:276-290`. |
| F8 | **Previsualització PDF A4 horitzontal** | **HI ÉS** | `pages/FittingPrintSheet.jsx` (276 línies): A4 apaïsat real 1123×794 `:20-21`, `@page { size: A4 landscape; margin: 12mm }` `:116`, caselles `AC/AD/RJ` `:30`, llegenda `:247-249`. Ruta fora del Shell `App.jsx:321-325`, enllaçada des de `components/model/SessionPanel.jsx:121`. |
| F9 | **Barra de recomptes** (Accepted · Adjusted · Rejected · Sense decidir) | **NO HI ÉS** | Cap recompte de veredictes enlloc. Maqueta: `.bar` `:193-198` + `counts()` `:294-298`. |
| F10 | **Res es defineix aquí** (capa en lectura, sense ordre, sense moure POMs) | **HI ÉS** | `fittingSource` no declara `supportsReorder` ni `supportsPoda` (`measureSources.jsx:60-62` vs `checkSource` `CheckMeasureEditor.jsx:187-188`); règim read-only via `lockRules` (`measureSources.jsx:107-109`). |
| F11 | **Els noms no es tallen mai** | **HI ÉS** | `whiteSpace: 'normal'` a la cel·la del nom: `MeasureGrid.jsx:277` i `:290`. |

### 2.4 · 🔴 LA SORPRESA: el veredicte ja es desa al backend, i el front no ho fa

Aquest és el defecte més seriós de tot el cens, i **no és una divergència de maqueta**: és una
funcionalitat completa al servidor que la pantalla no fa servir.

**El backend està sencer** (commit `fd102c06` · *«D-31.21 · el veredicte de la cel·la es desa, i
un REJECTED no sembra res»*):

| Peça | Àncora |
|---|---|
| Camp `decisio` amb els 3 choices + `''` ≠ ACCEPTED | `backend/fhort/fitting/models.py:427-439` |
| Migració | `fitting/migrations/0024_d3121_decisio_piecefittingline.py` |
| Serializer de cel·la: `decisio` **escriptible** pel mateix PATCH que la nota | `fitting/serializers.py:206-217` |
| La graella el rep en obrir | `fitting/serializers.py:350-351` — *«el veredicte, que la graella ha de poder tornar a pintar en obrir»* |
| Guard: un REJECTED no sembra | `fitting/views.py:654` |

**El front no l'usa.** `CheckMeasureEditor.jsx:332-340`:

```js
const [veredictes, setVeredictes] = useState({})          // :332  estat LOCAL
...
onVeredicte: (lineId, v) => setVeredictes(prev => ({ ...prev, [lineId]: v })),   // :337  cap PATCH
```

I `fittingGridAdapter.jsx:107` llegeix el veredicte de `decisio.valors[line.id]` (el mapa local),
**no de `line.decisio`** que el serializer ja envia.

**Conseqüència real:** la modista decideix tota la graella, recarrega o navega, i **tots els
veredictes desapareixen**. La nota, que va per la mateixa porta, sí que sobreviu.

**Per què ningú ho ha vist:** el comentari de `measureSources.jsx:75-80` continua dient

> *«🚨 PENDENT DE BACKEND — EL VEREDICTE NO ES DESA. `PieceFittingLine` té `valor_real` i `nota`
> però NO té camp `decisio`…»*

i el de `CheckMeasureEditor.jsx:325-327` el repeteix. **Tots dos són rancis**: descriuen l'estat
d'abans de `fd102c06`. Una sessió que llegís aquests comentaris conclouria, com el brief mateix
donava per fet, que fa falta una migració.

**Dimensionat: XS, i és NOMÉS FRONTEND.** Sembrar `veredictes` des de `line.decisio` a
`buildFittingRows` i fer que `onVeredicte` cridi `pieceFittingLines.update(lineId, { decisio })`
— la mateixa porta que ja fa servir la nota. **Cap canvi de contracte.**
**No s'implementa en aquesta Fase B**: el brief exclou explícitament tot el fitting (§6).

### 2-bis · Què hi ha a la viva que NO és a la v3

| Element | Àncora | Nota |
|---|---|---|
| Columna **Règim** (leadCol sticky, read-only en sessió) | `fittingGridAdapter.jsx:238-275` | Fora de la v3, però és **lectura** i `lockRules` la congela. |
| Fletxetes **±0.1** a la cel·la activa | `MeasureGrid.jsx:189-200` | Ajuda d'entrada. |
| **SessionPanel** i **SessionActions** | `CheckMeasureEditor.jsx:460`, `:502-505` | Context de sessió (Sprint Y); la v3 no els cobreix. |
| **Marcatge vermell** difereix-de-base | `MeasureGrid.jsx:74-81` | Anterior a la v3. |
| Indicador **candidata a poda** | `MeasureGrid.jsx:51-70` | Principi del soroll (C2). |

> ⚠️ **El vocabulari de capes de la v3 és ERRONI i no s'ha de copiar.** La maqueta diu
> `Interlining / Binding / Knit / Reinforcement` (`maqueta_fitting_v3.html:241-242`).
> **D-31.22 mana** i `utils/capaInstancia.js:9-13` ho declara: `entretela=Interfacing`,
> `reforc=Underlining`, `fornitura=Trim`. **Això no és una divergència a corregir.**

---

## 3 · DIMENSIONAT

**Llegenda:** `FE` = només frontend · `BE` = depèn de backend · **🔒 = TOCA CONTRACTE DE DADES**
(no es pot fer sense decidir res més).

### Mesures

| # | Divergència | Mida | FE/BE | 🔒 |
|---|---|---|---|---|
| M6 | Text visible «· es descartarà» | **XS** | FE | |
| M7b | Indicador desant… / desat | **S** | FE | |
| M8 | Fila activa ressaltada | **XS** | FE | |
| M9 | Animació de naixement (+ `prefers-reduced-motion`) | **XS** | FE | |
| M11 | Capçalera del carril: talla base gran i etiquetada | **XS** | FE | |
| M3c | Fons propi a les files de capa no-Exterior | **XS** | FE | |
| M3b | Tecla `L` per a la germana de capa | **S** | FE | |
| M7 | Moure la barra d'estat a peu de finestra | **S** | FE | |
| M5 | Cercador: sintaxi de sufixos «C.f» / «S.l» | **M** | **BE** | **🔒** |
| M5b | Cercador: agrupació per nivell (item / type / catàleg) | **M** | **BE** | **🔒** |
| M5c | Cercador: ↓ des de l'última fila | **XS** | FE | |
| M1 | Píndoles d'instància per dimensió (`dimState`, repartiment, tooltips) | **L** | **BE** | **🔒** |
| M2 | Modal `＋` de posició i combinacions | **L** | **BE** | **🔒** |

**Per què M1/M2/M5/M5b toquen contracte:**

- **No existeix cap registre de DIMENSIONS.** La maqueta modela la instància com un **array**,
  un valor per dimensió (`lat`, `st`) — `DIMS` `:215`, `inst:[]` `:222-227`. La viva la desa com
  **un sol slug compost** (`'left'`, `'left-relaxed'`) a `BaseMeasurement.instancia`, i
  `utils/capaInstancia.js:22-25` ho diu sense embuts: *«el diccionari d'instàncies encara no
  existeix (arriba amb C4-ins i la Montse) i inventar-ne un aquí seria fabricar la font única
  equivocada»*. Sense aquest diccionari no hi ha ni dimensions, ni opcions, ni complementària.
- **El repartiment entre germanes és una regla de FAMÍLIA** (`dimState` `:235-242`: si una
  germana té `Left`, l'altra queda deshabilitada). Avui la unicitat és la clau de BD
  `(model, pom, capa, instancia)` i el diàleg només filtra les combinacions ja preses
  (`EditableTable.jsx:715-720`). Són dues lleis diferents.
- **La maqueta genera CODI amb sufixos** (`SUF={Left:'L',…}` `:213`, `codeOf` `:232`). La llei
  viva és la contrària: `nom_fitxa` és text lliure del tècnic i la invariant de BD
  `instancia_exigeix_nom` obliga a nom quan hi ha instància (`EditableTable.jsx:694-698`).
  Adoptar els sufixos automàtics **canvia qui bateja la mesura**.
- **`poms/cerca/` no sap de nivells.** `backend/fhort/pom/wizard_views.py:114-148` retorna
  `id · codi_client · nom_client · nom_ca · nom_en · categoria_nom` — cap noció de
  «de l'item / del type / del catàleg». La sintaxi de sufixos, a més, hauria de retornar capa i
  instància pre-resoltes.

### Fitting

| # | Divergència | Mida | FE/BE | 🔒 |
|---|---|---|---|---|
| F5c | **El veredicte no sobreviu a la recàrrega** | **XS** | FE | |
| F9 | Barra de recomptes de veredictes | **S** | FE | |
| F7 | Germanes derivades: folgança + «NO ACTUALITZADA» | **M** | FE | |

**Cap divergència del fitting toca contracte.** Les tres es poden fer amb el que el backend ja
serveix (`decisio` i `origen` són a `fitting/serializers.py:351` i `:357`). F7 és M i no S
perquè la folgança **no és un camp**: la maqueta la té cablada (`sis:{folg:2.0}` `:230`) i
caldria decidir si es calcula del diferencial viu o es declara — **això sí que és una decisió**,
per bé que no de contracte.

---

## 4 · RISCOS DE COL·LISIÓ amb els trams d'avui

Fitxers tocats avui (05/08) per altres trams: `utils/destiTasca.js`, `utils/destiTasca.test.js`,
`pages/ModelSheet.jsx`, `components/model/ModalAcabarTasca.jsx`.

| Zona | Divergències que hi toquen | Risc | Lectura |
|---|---|---|---|
| `utils/destiTasca.js` | **Cap** | **Nul** | El resolutor de destí no entra ni a `EditableTable` ni a `MeasureGrid`. |
| `components/model/ModalAcabarTasca.jsx` | **Cap** | **Nul** | Frontera de sortida de tasca; cap bloc censat el travessa. |
| `pages/ModelSheet.jsx` | Cap de la Fase B | **Baix** | Cap divergència de M6/M7b/M8/M9/M11 obliga a tocar-lo: totes viuen dins de `EditableTable.jsx`. **Sí que hi tocaria F9** (barra de recomptes), si algun dia es posa a fora de la graella — **no es fa avui**. |
| `EditableTable.jsx` | M6·M7b·M8·M9·M11 | **Baix** | Últim commit `00fbca15` (F4, germana). Cap sessió concurrent l'ha tocat avui. |
| `MeasureGrid.jsx` · `fittingGridAdapter.jsx` · `measureSources.jsx` | F5c·F7·F9 | **Mitjà** | **Compartits per QUATRE superfícies** (Mesures, Escalat, Fitting, Repàs). Qualsevol canvi s'hi ha de fer per `opts` opt-in, com ja fan `hist` i `decisio`. Una raó més per no tocar-los en aquesta Fase B. |
| `pom/` i catàleg BRW-v3 | M5/M5b (cercador) | **Alt** | Dues sessions concurrents hi han treballat avui. **Cap peça de la Fase B hi entra.** |

---

## 5 · QUÈ DECIDEIX AGUS

Ordenat per bloqueig. Els cinc primers no els pot resoldre cap agent.

### D1 · La columna de Regla de graduació: hi és o no hi és? 🛑

La decisió W3 del **31/07** (`ff23c7f4`) la va posar SEMPRE visible, amb motiu escrit. La v8.1,
aprovada el **04/08**, **no la porta**. Les dues coses no poden ser certes.

- Si **mana la maqueta** → treure quatre columnes de mitja pantalla i tornar a deixar sense lloc
  qui vol entrar la graduació a mà (el problema exacte que W3 resolia).
- Si **mana la decisió** → la v8.1 s'ha d'actualitzar; deixar-la com a font canònica incompleta
  garanteix que el proper cens torni a obrir aquesta mateixa fitxa.

**Mentrestant no s'ha tocat res** i el comentari ranci de `EditableTable.jsx:398-409` es queda
tal com és: corregir-lo abans de la decisió seria escollir per ell.

### D2 · El model d'INSTÀNCIA: array de dimensions o slug compost? 🛑

M1 i M2 (el gruix de la v8.1, i el que es veu demà amb la Montse) no es poden començar sense
això. La maqueta demana dimensions ortogonals amb repartiment entre germanes; la BD té un slug
compost i una invariant que exigeix nom. **Cal el diccionari d'instàncies de C4-ins.**
Decisió associada: **qui bateja** una germana d'instància — el tècnic (avui) o el sufix
automàtic `L`/`R`/`RE`/`EX` (maqueta).

### D3 · El cercador de POM per nivells i sufixos 🛑

Requereix ampliar `poms/cerca/` amb el nivell (item/type/catàleg) i amb la resolució de sufixos.
És backend nou. **Confirmar la taxonomia abans d'escriure l'endpoint.**

### D4 · La folgança de les germanes derivades

F7 necessita saber d'on surt el número: ¿diferencial viu entre exterior i folre a la darrera
presa vàlida, o valor declarat per parella? La maqueta el cabla a `2.0` i no ho diu.

### D5 · La barra d'estat: fixa a peu de finestra o sota la taula?

Menor, però la v8.1 la fixa (`position:fixed`) i la viva és una línia sota la taula. Si es
prefereix la línia, la maqueta s'hauria d'ajustar. **La Fase B no la mou** — només hi afegeix
l'indicador de desat, sense canviar-ne la posició.

### D6 · Recordatori: el veredicte del fitting és un XS que la gent està perdent avui

No és una decisió de disseny (§2.4): és un defecte amb tot el backend fet des de `fd102c06`.
**Convé prioritzar-lo demà.** No s'ha fet aquí perquè el brief exclou el fitting.

---

## 6 · PUNT DE PARADA

**Divergències estructurals detectades i NO resoltes** (contracte de dades / diccionari
inexistent / backend nou): **M1 · M2 · M5 · M5b**. Es documenten i s'aturen aquí, com mana el
brief.

La Fase B només executa el que compleix les tres condicions (presentació o interacció local ·
cap canvi de contracte ni endpoint · maqueta inequívoca), i **no toca res del fitting**, cap
píndola, cap modal `＋`, cap germana de capa ni el cercador.

Vegeu `REPORT_UI_MAQUETES.md`.
