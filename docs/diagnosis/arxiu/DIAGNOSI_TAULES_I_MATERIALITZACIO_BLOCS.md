> ⚠️ SUPERADA 2026-07-21 — implementada pel sprint Patró B end-to-end (fases 1-7, commits
> 73babdb→254eaa8). Consulta només com a històric.

# DIAGNOSI — Taules de mesures i materialització de blocs

Data: 2026-07-21 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev` (HEAD `a71b95c`)

**Abast.** Estendre a les TAULES el patró que la diagnosi germana
[`DIAGNOSI_CAMI_B_INPLACE_I_SUPERFICIE_UNICA.md`](DIAGNOSI_CAMI_B_INPLACE_I_SUPERFICIE_UNICA.md)
(§P4) va establir per a la capçalera — materialitzar prims → objectes reals amb `type:'field'` +
`group` + l'`ungroupObject` existent — i preparar la implementació: inventari fi de materialització,
base de fets per a les maquetes Q1/Q3, i inventari de neteges.

**Convenció.** Cada afirmació porta `fitxer:línia`. `"NO EXISTEIX"` = confirmat absent al codi, no
especulat. Les propostes van al final, marcades `💡 PROPOSTA (a validar)`. Camins relatius a
`/var/www/ftt-staging/`. `TSE.jsx` = `frontend/src/pages/TechSheetEditor.jsx`.

**Verificació del documentador** (re-grep independent dels builders i del catàleg): confirmats
`buildTablePrimitives:412`, `buildTableCellPrimitives:473`, `buildFieldChipPrims:529`,
`buildHeaderV2Primitives:573`, `buildMasterHeaderPrimitives:712`, `buildHeaderPrimitives:804`,
`buildPendingRibbonPrims:1143`; el `bold` de cel·la a `:509` i `:512`; el `return isBreak` a **`:3455`**
(l'informe de camp deia `:3458` — corregit aquí); el `*` de talla base a `:3445`; `FIELD_CATALOG`
`:130-147` (16 claus) i `_placeholder_values` `services_ftt_document.py:95-108` (14 claus + 2
construïdes).

---

## Resum executiu

1. **Les taules vives són 100 % congelades i cap d'elles és editable.** Els valors s'escriuen com a
   literals dins `rows` en el moment d'inserir i **mai es re-llegeixen** (llei explícita al comentari
   `TSE.jsx:3368-3370`). El panell d'edició només serveix `kind:'bom'|'custom'` (`:4977`) → **T1a
   (`pom_fitting`) i T1b (`pom_grading`) no tenen CAP control**. Un valor caducat només es corregeix
   esborrant i tornant a inserir.

2. **El bug del bold té explicació exacta i no és un bug de render: és criteri de domini.** L'únic
   codi que posa `cell.bold` és `cellForSize` a `TSE.jsx:3448-3455`: **negreta = "break de grading"**
   (el delta d'aquesta talla difereix del de l'anterior). Cap capçalera de columna és negreta
   (`:497`), cap primera columna ho és (`:512`). Per això la negreta surt escampada per l'interior de
   la graella i no on l'ull la busca. Només passa a T1b.

3. **La talla base es va perdre pel camí.** El realçat visual **existeix** — fons gold a la capçalera
   i fons de columna sobre les files — però al builder **LEGACY** (`:425-430`, `:439-441`), que és
   **inabastable des de la UI** (`setPickFitting(true)` no es crida enlloc). Al builder viu només
   sobreviu el sufix `*` a l'etiqueta de columna (`:3445`). Tractament visual de la talla base a la
   taula viva: **NO EXISTEIX**.

4. **La materialització de la capçalera és viable, i el creuament amb el catàleg dona el cost exacte:**
   dels 12 valors de model del header, **7 ja tenen `field_key` exacte**, **1 té clau amb format
   diferent** (`data_avui` és ISO, el header pinta `DD-MM-YYYY`), **3 no existeixen** (garment×2,
   grading×3, size_run) i **1 no és materialitzable de cap manera** (PAGE, ve de `pageCtx`). El
   `SIZE RUN` és el cas dur: **N prims amb bold+underline selectiu per segment** que un sol `text`
   de Konva no pot expressar.

5. **Per a la taula, el patró `field` per cel·la NO escala i a més seria inútil**: una T1b té
   `n_POM × (n_talles+3)` cel·les sense cap límit al codi (només `custom` està clampat a 20×20,
   `:5227`, `:5231`), i el sistema `field` congela a **UN text pla per objecte**
   (`services_ftt_document.py:178-183`). §P2.C exposa tres opcions amb cost, sense triar.

6. **Les neteges estan confirmades i són petites**: PaperKonvaPoc són **5 punts** (fitxer, import,
   ruta, 24 claus i18n alineades línia a línia als tres idiomes `:3294-3319`, i l'asset `CALLIE.svg`
   que ja està trencat — referencia 3 PNG inexistents). Del menú de text, **28 de 33 entrades són
   duplicats retirables** i **5 no tenen cap altra superfície visible** (undo/redo/copy/paste/duplicate).
   S'hi troba, pel camí, **un bug de closure real al panell Capes** (§P4.D).

---

## BLOC P1 — Taules de mesures: anatomia completa

### P1.A — Com entra una taula

Un sol camí viu: **ribbon Inserir → Taula** (`TSE.jsx:4093`, `onClick: () => setTablePicker({})`,
`disabled: !locked`) → modal picker (`:5197-5250`) amb **4 variants**: `t1a` (`:5203`), `t1b`
(`:5207`), `t2` (`:5213`), `custom` (`:5217`). `t1a`/`t1b` es desactiven si no hi ha SizeFittings; si
n'hi ha més d'un es demana quin (`:5236-5243`), si n'hi ha exactament un s'insereix directe (`:3521`).

Enrutament: `onPickTableVariant` (`:3517-3523`) → `runTableVariant` (`:3513-3516`) → `insertTableT1a`
(`:3381`), `insertTableT1b` (`:3431`), `insertTableT2` (`:3474`), `insertTableCustom` (`:3495`).

- **Importació de mesures: NO EXISTEIX.** El botó és un placeholder permanent sense handler i amb
  `disabled: true` literal (`:4102-4103`), tooltip "coming soon".
- **Camí LEGACY** `data_block kind:'graded_table'`: `insertGradedTable` (`:3342-3365`), invocat només
  des del modal `pickFitting` (`:5155`). **`setPickFitting(true)` no es crida enlloc** (només
  `setPickFitting(false)` a `:5150` i `:5155`) → **camí mort per a documents nous**; el render es
  conserva per a docs antics (comentaris `:3340-3341`, `:3366-3367`).
- Cap altre fitxer del frontend crea objectes `type:'table'`.

### P1.B — Model de dades

**Dos tipus d'objecte diferents conviuen.**

**(a) `type:'table'`** — el viu. `addObject` literals a `:3420-3426` (T1a), `:3463-3469` (T1b),
`:3484-3490` (T2), `:3501-3507` (custom):

```js
{ id, type:'table', layer:'free', x:10, y:14,
  kind: 'pom_fitting' | 'pom_grading' | 'bom' | 'custom',
  columns: [{ key, label, width }],        // width en MM
  rows: [[cell, …]],                       // cell = string | { text, sub?, bold? }
  style: { fontSize: 9, headerFill: TBL.HDR_BG, zebra: true },
  snapshot: { model_id, size_fitting_id?, snapshot_at } }
```

`fitTableObj` (`:3372-3377`) hi afegeix `scale`, `width`, `height` (mm, calculats **un sol cop**).
`handleTransformEnd` (`:2797-2800`) hi afegeix `rotation`, `scaleX`, `scaleY` i sobreescriu `scale`.
El backend hi pot afegir `pendent_vincle:true` (`services_ftt_document.py:237`). Contracte de cel·la
documentat a `:480-483`.

**(b) `data_block kind:'graded_table'`** — legacy: `:3357-3360`, només `size_fitting_id`,
`layer:'data'`, `x`, `y`, `scale`, `width`, `height`. **Les dades NO són a l'objecte**: viuen a
l'estat `tableData[objId]` (`:1749`), amb refetch a cada obertura (`:2402-2412`) contra
`/api/v1/fitting/<sf>/graded-table/`. `serializePages` ho documenta (`:1319-1320`).

### P1.C — Render: sí, exactament com la capçalera

- Builder viu: **`buildTableCellPrimitives(obj)`** (`:473-524`), memoïtzat per `obj` (`:875`),
  retorna `{prims, totalW, totalH}` — **mateix patró de prims que el header**.
- Builder legacy: **`buildTablePrimitives(d)`** (`:412-469`).
- **Live**: `TableNode` (`:874-886`) → `prims.map(p => <PrimNode/>)`; `GradedTableNode` (`:863-871`).
- **Export/miniatures**: `addObjectToLayer` — `type:'table'` a `:1254-1260`
  (`buildTableCellPrimitives` + `addPrimsToGroup`), `kind:'graded_table'` a `:1228-1235`.
- **CONFIRMAT: mateix builder, mateixes prims, mateix `dataBlockGroupProps`** (`:1237`, `:1255`) →
  camí compartit live/PDF real, inclosos els rètols "pendent de vincle" (`:878` vs `:1258`).
- **`listening`**: `PrimNode` (`:838-851`) — els `Text` **sempre** `listening={false}` (`:849`), les
  línies també (`:843`); només els `Rect` **amb fill** escolten (`:841`). **Cap cel·la és clicable
  individualment.**
- Els texts porten `ellipsis` + `wrap:'none'` (`:849`) → el contingut que no cap es talla amb "…",
  no fa salt de línia.

**Quatre `kind` sobre UN sol builder.** Les diferències són només de dades i de permisos:

| kind | inserció | forma |
|---|---|---|
| `pom_fitting` (T1a) | `:3400-3419` | 8 columnes fixes (REF/POM/base/rule/break/tol/nova/coments); 3 buides per omplir en paper (`:3416`); `tol` sempre buida (motiu a `:3379-3380`) |
| `pom_grading` (T1b) | `:3442-3462` | REF · POM · N talles · Δ |
| `bom` (T2) | `:3477-3483` | 5 columnes, 4 files buides |
| `custom` | `:3496-3500` | N×M genèriques |

El builder legacy `:412` sí que és estructuralment diferent: amplades constants (`:352-355`), columna
Δ fixa, i **realçat de talla base**.

### P1.D — EL BUG D'AGUS (1): el bold

**Exactament dos punts** posen `bold` al builder viu, i tots dos llegeixen el mateix camp:
`:509` (cel·la amb subtítol) i `:512` (cel·la normal), tots dos `bold: !!cell.bold`.

**No hi ha cap altra heurística**: la capçalera de columna **NO és bold** (`:497` — el `Text` de
capçalera no passa `bold`; només és blanc sobre `#111827`), la primera columna **NO és bold**, i no
hi ha criteri per fila ni per contingut.

Qui posa `cell.bold = true` — **només T1b**, a `cellForSize` (`TSE.jsx:3448-3455`, verificat):

```js
const isBreak = prevSl != null && d != null && dPrev != null && d !== dPrev
return isBreak ? { text, bold: true } : text
```

És a dir: **una cel·la de valor va en negreta si el seu delta de grading difereix del de la talla
immediatament anterior** (canvi d'increment = "break"). Comentari a `:3447`.
T1a (`:3410-3418`), T2 (`:3481`) i custom (`:3500`): **cap cel·la bold**. El panell d'edició escriu
strings plans (`:4998`, `:5000`) → **mai genera `bold`, i el destruiria si s'edités una cel·la que
en tingués**.

**Conseqüència literal de la "barreja sense criteri aparent"**: a una T1b les negretes cauen
escampades per l'interior de la graella allà on el grading canvia d'increment — **no** a les
capçaleres ni a la columna REF, que és on la convenció tipogràfica les espera. Idèntic al PDF
(`addPrimsToGroup:858` aplica el mateix `p.bold ? 'bold' : …`).

Al builder LEGACY el criteri era un altre: `:449` la columna REF va **sempre** `bold: true`.

Discrepància UI/canvas anotada: els inputs de capçalera del panell es pinten `fontWeight: 600`
(`:4989`), però la capçalera al canvas no és negreta (`:497`).

### P1.E — EL BUG D'AGUS (2): la talla base

- **La dada existeix i arriba**: `Model.base_size_label` (`backend/fhort/models_app/models.py:273`),
  servida dins el payload `graded-table` com a `base_size`
  (`backend/fhort/fitting/graded_spec_views.py:76-78`, `:97`). També `modelData.base_size_label`
  (`TSE.jsx:141`, `:652`, `:787`).
- **Tractament visual a la taula viva: NO EXISTEIX.** L'únic rastre és el **sufix `*` a l'etiqueta de
  columna** (`:3445`, verificat): `label: sl === data.base_size ? \`${sl}*\` : sl`.
  `buildTableCellPrimitives` (`:473-524`) **no conté cap referència** a `base`, `base_size` ni
  `is_base`. Cap cel·la de dades de la columna base es distingeix de les altres.
- **Al builder LEGACY sí que existeix**: `:425-430` capçalera de la base amb fons `TBL.OUTER` (gold)
  i text blanc + `${sl}*`; `:439-441` `prims.push({t:'r', … fill: TBL.BASE_BG})` pinta **tota la
  columna base** sobre les files. Aquest codi és inabastable des de la UI (§P1.A).
- A T1a la talla base **no és una columna** (la taula és POM×regla, no POM×talla); `base_value_cm` hi
  és una columna de valor (`:3414`).
- `talla_mapping` / `is_base` / `size_base` a `TSE.jsx`: **NO EXISTEIX** (l'únic `talla_base` és
  l'etiqueta del botó de picker, `:5241`).

### P1.F — Edicions permeses i, sobretot, les que no

**Guarda del bloc del panell**: `:4977` — `selObj.type === 'table' && (kind === 'bom' || kind === 'custom')`.
Llei explícita al comentari `:4978`. **T1a i T1b: cap control.**

| línia | control | escriu |
|---|---|---|
| `:4986-4990` | input de text per columna | `columns[i].label` |
| `:4996-5001` | input de text per cel·la (graella completa) | `rows[r][ci]` (string pla) |
| `:5002-5005` | afegir fila | `rows` += fila de strings buits |
| `:5006-5014` | afegir columna | `columns` += `{key:'c'+len, label, width:28}` + `''` a cada fila |
| `:5015-5019` | esborrar fila (disabled si ≤1) | `rows.slice(0,-1)` |
| `:5020-5025` | esborrar columna (disabled si ≤1) | `columns.slice(0,-1)` + retall de cada fila |

Genèrics que sí l'afecten: X/Y (`:4837-4844` → `moveObjectTo:2185`) i el `Transformer` (`:4595`,
`type==='table'` entra a `keepRatio`) → `handleTransformEnd:2797-2800`.

**NO EXISTEIX** (llista explícita, tot verificat):
1. Editar una cel·la clicant-la al canvas — `TableNode` (`:874-886`) no té `onDblClick`, i els texts
   són `listening={false}` (`:849`).
2. Qualsevol edició de T1a/T1b (guarda `:4977`).
3. Amplada de columna des de la UI (`columns[i].width`) — cap input l'escriu; només literals a la
   inserció (`:3401-3408`, `:3444-3446`, `:3477-3482`, `:3497-3499`) i `28` per a columna afegida
   (`:5010`).
4. Tipografia per cel·la (família/mida/color/alineació) — el bloc `textObj` (`:4849-4915`) només val
   per a `type:'text'`; el builder cabla `fill: TBL.VAL`/`TBL.NOM` i `size: fontPx` (`:509-512`).
5. Bold/italic per cel·la des de la UI (§P1.D).
6. Color de fons de fila o de cel·la — només zebra global (`style.zebra`, `:502`) i `style.headerFill`
   (`:495`), **cap dels dos amb control al panell**; `style.fontSize` tampoc s'edita (ve de la
   inserció `:3424`, mínim forçat 8 pt a `:477`).
7. Inserir/esborrar fila o columna **al mig** — només al final (`:5002`, `:5015`, `:5020`).
8. Reordenar files/columnes, fusionar cel·les, alçada de fila.
9. Control `scale %` — existeix **només** per a `data_block` (`:4972-4976`), no per a `type:'table'`.
10. **Els inputs W/H del panell no fan res sobre una taula**: `dimensionInfo:2182` diu
    `canResize:true`, però `resizeObjectTo` (`:2209-2249`) **no té branca `'table'`** (cobreix
    rect/image/sketch_svg/pattern_piece/text `:2217`, ellipse `:2221`, data_block/group `:2225`, path
    `:2232`) → surt sense escriure res.
11. **`obj.width`/`obj.height` no es recalculen** en afegir/treure files o columnes (el panell no
    crida `fitTableObj`) → els bounds que fan servir alinear/distribuir (`objectBounds:288-290`)
    queden desfasats respecte de la geometria real del builder.

### P1.G — Cel·les vives vs congelades i ordre de magnitud

- **`type:'table'`: 100 % CONGELADES.** Valors escrits com a literals a la inserció (T1a `:3409-3419`
  des de `/models/<id>/base-measurements/` i `/grading-rules/`; T1b `:3455-3462` des de
  `/fitting/<sf>/graded-table/`) i mai re-llegits. Llei al comentari `:3368-3370`: «valors CONGELATS
  a la inserció … cap binding viu; `obj.snapshot` només serveix per traçabilitat».
- **`graded_table` legacy: VIU.** No desa cap valor (`:1319-1320`), refetch a cada obertura
  (`:2402-2412`), resolució en render (`:864`) — **exactament com el header**. Confirmat al backend:
  `services_ftt_document.py:249-250` («és l'únic objecte amb un binding VIU»).
- En descongelar per canvi de host, el backend **buida les cel·les** de `type:'table'` conservant la
  graella (`services_ftt_document.py:239-240`) i marca `pendent_vincle` (`:237`); per a
  `graded_table` posa `size_fitting_id=None` (`:256`). El front ho pinta amb prims compartits
  live/PDF (`isPendentVincle:1124`, `buildPendingRibbonPrims:1143`).

**Magnitud**: T1b = `2 + n_talles + 1` columnes (`:3443-3447`) × 1 fila per POMMaster amb GradedSpec
actiu (`graded_spec_views.py:38-42`) ≈ **`n_POM × (n_talles+3)` cel·les**. T1a = 8 × n_BaseMeasurement.
T2 = 5×4 fix. **Límits al codi: només `custom`**, clampat a 1..20 files i columnes (`:5227`, `:5231`)
→ màx 400 cel·les. **Per a T1a/T1b/T2 no hi ha cap límit ni paginació**: `totalH = hdrH +
rows.length*rowH` (`:490`) creix sense topall; l'única mitigació és l'auto-fit d'una sola vegada
(`fitTableObj:3374-3375`), que encongeix la taula sencera. **Tall de taula entre pàgines: NO EXISTEIX.**

### P1.H — Coordenades de la taula

- L'objecte viu en **mm**: `x:10, y:14` (`:3421`), `width`/`height` en mm (`:3376`).
- Conversió: `MM_TO_PX = 2.4` (`:42`), `toPx` (`:124`), aplicada a `dataBlockGroupProps` (`:1098-1101`),
  el mateix helper per al live (`:1463`) i l'export (`:1255`).
- **Dins del builder les prims són en px, no en pt relatius**: `cw = cols.map(c => Math.max(6,
  c.width||24) * MM_TO_PX)` (`:480`) — o sigui `column.width` és **mm**. La mida de lletra sí que fa
  pt→mm→px: `fontPx = Math.round(pt * 0.3528 * MM_TO_PX)` (`:478`).
- **El builder de taula NO usa `gx()` ni `_hdrP()`** (helpers del header): **NO EXISTEIX** aquesta
  compartició. La taula té la seva pròpia aritmètica.

**Veredicte P1: cal X.** El bold i la talla base són dos defectes independents i tots dos petits: el
bold és un criteri de domini pintat sense jerarquia tipogràfica (falta el bold de capçalera/REF que
l'ull espera), i el realçat de la talla base **ja existeix escrit** al builder legacy i només cal
portar-lo al viu. L'edició de taules, en canvi, és un forat estructural: T1a/T1b són read-only totals.

---

## BLOC P2 — Materialització: inventari fi per implementar

### P2.A — La llista completa de prims de la capçalera

Constants: `MM_TO_PX = 2.4` (`TSE.jsx:42`) · `P = _hdrP() = 0.3528 · MM_TO_PX = 0.84672` px/pt (`:674`)
· `ASC = 0.8` (`:672`) · `KONVA_COL` (`:90`). Totes les `x/y/w/h/size` són **px en l'espai LOCAL del
bloc**. Els valors de sota són el càlcul literal de les expressions amb cos 9 pt (si el text no cap,
el cos baixa a 8 pt i `y` es recalcula, `:735-737`).

| # | Línia | t | x | y | w | text / expressió | estil | **Classe** |
|---|---|---|---|---|---|---|---|---|
| 1 | `:720` | `r` | 0 | 0 | 664.42 (h 76.37) | — | fill `#ffffff`, stroke `#1d1d1b`, sw 0.423 | **DECORACIÓ** (marc) |
| 2 | `:721` | `l` | — | — | — | points `[119.98, 0, 119.98, 76.37]` | stroke `#1d1d1b`, sw 0.423 | **DECORACIÓ** (divisòria D1) |
| 3 | `:722` | `l` | — | — | — | points `[392.20, 0, 392.20, 76.37]` | ídem | **DECORACIÓ** (divisòria D2) |
| 4 | `:741` | `t` | 5.08 | 41.24 | 54.91 | `'DATE'` | 5.080 px, gray `#777776` | **DECORACIÓ** |
| 5 | `:742` | `t` | 5.08 | 47.67 | 54.91 | `_hdrDate(new Date())` → `DD-MM-YYYY` | 7.620 px, ink | **VALOR** (data sistema) |
| 6 | `:743` | `t` | 65.07 | 41.24 | 49.83 | `'PAGE'` | 5.080 gray | **DECORACIÓ** |
| 7 | `:744` | `t` | 65.07 | 47.67 | 49.83 | `${pageCtx.index+1} / ${pageCtx.total}` | 7.620 ink | **VALOR** (context pàgina) |
| 8 | `:745` | `t` | 5.08 | 60.29 | 109.82 | `'TECHNICIAN'` | 5.080 gray | **DECORACIÓ** |
| 9 | `:746` | `t` | 5.08 | 66.72 | 109.82 | `m?.responsable_nom` | 7.620 ink | **VALOR MODEL** |
| 10 | `:749` | `t` | 125.06 | 3.13 | 131.03 | `'INTERNAL REFERENCE'` | 5.080 gray | **DECORACIÓ** |
| 11 | `:750` | `t` | 125.06 | 9.57 | 131.03 | `m?.codi_intern` | 7.620 ink | **VALOR MODEL** |
| 12 | `:751` | `t` | 261.17 | 3.13 | 125.95 | `'SEASON'` | 5.080 gray | **DECORACIÓ** |
| 13 | `:752` | `t` | 261.17 | 9.57 | 125.95 | `[m?.temporada, m?.any].filter(Boolean).join(' ')` | 7.620 ink | **VALOR MODEL** (compost ×2) |
| 14 | `:753` | `t` | 125.06 | 22.18 | 262.06 | `'CLIENT REFERENCE'` | 5.080 gray | **DECORACIÓ** |
| 15 | `:754` | `t` | 125.06 | 28.62 | 262.06 | `m?.codi_client` | 7.620 ink | **VALOR MODEL** |
| 16 | `:755` | `t` | 125.06 | 41.24 | 262.06 | `'MODEL'` | 5.080 gray | **DECORACIÓ** |
| 17 | `:756` | `t` | 125.06 | 47.67 | 262.06 | `m?.nom_prenda` | 7.620 ink | **VALOR MODEL** |
| 18 | `:757` | `t` | 125.06 | 60.29 | 262.06 | `'COLLECTION'` | 5.080 gray | **DECORACIÓ** |
| 19 | `:758` | `t` | 125.06 | 66.72 | 262.06 | `m?.collection` | 7.620 ink | **VALOR MODEL** |
| 20 | `:761` | `t` | 397.28 | 3.13 | 262.06 | `'GARMENT TYPE \| ITEM'` | 5.080 gray | **DECORACIÓ** |
| 21 | `:762` | `t` | 397.28 | 9.57 | 262.06 | `join([garment_type_nom, garment_type_item_nom])` (sep `' \| '`, `:725`) | 7.620 ink | **VALOR MODEL** (compost ×2) |
| 22 | `:763` | `t` | 397.28 | 22.18 | 262.06 | `'TARGET \| FIT TYPE \| CONSTRUCTION'` | 5.080 gray | **DECORACIÓ** |
| 23 | `:764` | `t` | 397.28 | 28.62 | 262.06 | `join([grading_target_nom, grading_fit_nom, grading_construction_nom])` | 7.620 ink | **VALOR MODEL** (compost ×3) |
| 24 | `:765` | `t` | 397.28 | 41.24 | 262.06 | `'SIZE SYSTEM'` | 5.080 gray | **DECORACIÓ** |
| 25 | `:766` | `t` | 397.28 | 47.67 | 262.06 | `m?.size_system_nom` | 7.620 ink | **VALOR MODEL** |
| 26 | `:767` | `t` | 397.28 | 60.29 | 262.06 | `'SIZE RUN'` | 5.080 gray | **DECORACIÓ** |
| 27..N | `:768` → `_pushSizeRun` `:775-799` | `t` | **variable** | 66.72 | `len·9·0.6·P + 4` | **un prim PER SEGMENT** | 7.620 ink; `bold+underline` **només** si `lab === base_size_label` (`:795-796`) | **VALOR MODEL** (N prims) |

**Recompte: 15 prims de decoració** (1 rect + 2 línies + 12 etiquetes) i **12 + N prims de valor**
(N = 2·len(labels) − 1 del size run).

**El bloc SIZE RUN no és un prim, és una seqüència** (`_pushSizeRun`, `:775-799`): `raw =
m?.size_run_model` partit per `/[·;,]/` (`:786`); un prim per etiqueta i un prim `'·'` entre etiquetes
(`:797`) que **mai** es subratlla (D6); avanç manual del cursor amb mètrica mono `charW = 9·0.6` pt
(`:788`, `:792`). Si `raw` és buit → **cap prim** (`:785`); en `placeholderMode` → **un sol prim**
`'{size run}'` (`:781`).

**Origen de `m`**: prop `modelData` de `HeaderBlock` (`:903`, `:909`) ← `ObjectNode` (`:1440`) ←
`modelData={model}` (`:4529`); a l'export, `ctx.modelData` (`:2448`, `:3593`, consumit a `:1227`).
`model` es carrega a `:2284-2286` (`GET /api/v1/models/<id>/`), serialitzat per
`ModelDetailSerializer` (`backend/fhort/models_app/serializers.py:169-222`).

**Tres layouts, tres builders** (`buildHeaderPrimitives`, `:804-834`): `masterFtt` → `:712-771` (l'únic
que crea `insertHeader`, `:3536-3539`); `blocks4` → `buildHeaderV2Primitives` (`:573-641`); sense
`config` → LEGACY inline (`:807-833`).

### P2.B — El catàleg de `field_key` i el creuament

**Frontend** — `FIELD_CATALOG` (`TSE.jsx:130-147`), **16 claus**, consumit a `:5064-5070` (cada clic
crea `{id, type:'field', key, label, layer:'free', x:20, y:20, style:{fontSize:11}}`).
**Backend** — `_placeholder_values` (`services_ftt_document.py:95-108`): **14 claus** llegides del
serializer + `temporada_any` construït (`:106`) + `data_avui = timezone.localdate().isoformat()`
(`:107`). `customer_logo` **intencionadament absent** del mapa (`:108`): es resol com a imatge.

> ⚠️ **Bandera de mètode.** El comentari del catàleg (`TSE.jsx:127-129`) diu literalment:
> «Únics vàlids — **NO n'afegim d'altres** (marca/dissenyador/patronista NO existeixen al model)».
> Ampliar el catàleg contradiu aquesta anotació → **decisió de CTO**, no d'implementació.

#### TAULA DE CREUAMENT — prim VALOR ↔ `field_key` (producte central del bloc)

| # | Prim | Expressió al header | `field_key` | Veredicte |
|---|---|---|---|---|
| 9 | TECHNICIAN | `m?.responsable_nom` | `responsable_nom` (`:139`) | ✅ **JA EXISTEIX** — exacte |
| 11 | INTERNAL REF | `m?.codi_intern` | `codi_intern` (`:132`) | ✅ **JA EXISTEIX** — exacte |
| 13 | SEASON | `[temporada, any].join(' ')` | `temporada_any` (`:136`) | ✅ **JA EXISTEIX** — equivalent (`f"{temporada} {any}".strip()`, `:106`) |
| 15 | CLIENT REF | `m?.codi_client` | `codi_client` (`:133`) | ✅ **JA EXISTEIX** — exacte |
| 17 | MODEL | `m?.nom_prenda` | `nom_prenda` (`:131`) | ✅ **JA EXISTEIX** — exacte |
| 19 | COLLECTION | `m?.collection` | `collection` (`:135`) | ✅ **JA EXISTEIX** — exacte |
| 25 | SIZE SYSTEM | `m?.size_system_nom` | `size_system_nom` (`:142`) | ✅ **JA EXISTEIX** — exacte |
| 5 | DATE | `_hdrDate(new Date())` → `DD-MM-YYYY` (`:709`) | `data_avui` (`:146`) | ⚠️ **PARCIAL** — la clau existeix però el **format difereix**: catàleg = ISO `YYYY-MM-DD` (`services_ftt_document.py:107`), header = `DD-MM-YYYY`. Materialitzar canvia el format visible |
| 21 | GARMENT TYPE \| ITEM | `join([garment_type_nom, garment_type_item_nom])` | — | ❌ **NO EXISTEIX** — calen 2 claus noves (o 1 composta). Dades ja al serializer (`serializers.py:171`, `:180`) |
| 23 | TARGET \| FIT \| CONSTRUCTION | `join([grading_target_nom, grading_fit_nom, grading_construction_nom])` | — | ❌ **NO EXISTEIX** — 3 claus noves (o 1 composta). Dades a `serializers.py:188-208` |
| 27..N | SIZE RUN | `size_run_model` segmentat + `base_size_label` en bold/underline | `base_size_label` (`:141`) existeix; `size_run_model` **no** | ❌ **NO EXISTEIX com a unitat** — dos forats: (a) clau `size_run_model` absent; (b) **cap `field` pot expressar marcatge per segment** (congela a UN text pla, `services_ftt_document.py:178-183`) |
| 7 | PAGE | `${pageCtx.index+1} / ${pageCtx.total}` | — | ⛔ **NO ÉS DE MODEL** — ve de `pageCtx`; ni el catàleg ni el backend tenen concepte de paginació. **Materialitzar-lo congela el número de pàgina** |
| logo | KonvaImage | `customerLogoUrl = model?.customer_logo` (`:1797`) | `customer_logo` (`:145`) | ⚠️ té clau, **però geometria pròpia** — §P2.B-logo |

**Resum del cost**: 7 exactes · 1 amb canvi de format · 3 grups de claus noves (garment ×2, grading
×3, size_run ×1 = **6 claus noves**) · 1 impossible (PAGE) · logo a part.

#### El logo: tres camins, i el que pinta avui no és cap dels dos "oficials"

| camí | on | què fa |
|---|---|---|
| **1 · `field key:'customer_logo'`** | `services_ftt_document.py:169-174` → `_resolve_logo_obj:136-164` | Llegeix `model.customer.logo`, n'obre els bytes, **empaqueta l'asset dins el ZIP** (`LOGO_ASSET_STEM`, `:119`) i emet `{type:'image', width:40, height:16, src:'assets/…', field_key:'customer_logo'}` (`:150-155`) — **mida FIXA 40×16 mm, aspect ratio ignorat**. Si no hi ha logo, emet un `text` buit amb la marca (`:159-164`). Porta marca → `unfreeze_document` el descongela i purga l'asset (`:300-309`, `:354-359`) |
| **2 · `image kind:'logo'`** | `services_ftt_document.py:202-212`; el crea `insertLogo` (`TSE.jsx:3132-3137`) | `{type:'image', kind:'logo', x:10, y:8, width:40, height:20, src: customerLogoUrl}` — **`src` és una URL http(s) absoluta**. El backend no el reescriu mai i, en descongelar, **l'ELIMINA sencer** (`:299-308`) |
| **3 · el que pinta avui** | `TSE.jsx:920` + `headerMasterLogoRect:694-705` (export: `:1243-1248`) | **No és un objecte del document**: és un `KonvaImage` fill del Group del `HeaderBlock`, amb rect derivat de l'aspecte real dins la zona 129.7×39.1 pt (`:693`), **contain preservant l'aspecte i sense clamp a la mida natural** (`:699`, pot fer upscale), alineat esquerra i centrat vertical (`:704`), fallback aspecte 2.4 (`:702`) |

**Fet decisiu**: el camí 1 és **l'únic portable** (bytes al ZIP, descongelable), però la seva geometria
és 40×16 mm rígida — **incompatible amb el camí 3**, que és el que dona el resultat visual actual. El
camí 2 no sobreviu a un canvi de host. Cap dels tres reprodueix els altres sense canvi de codi.

### P2.C — La taula: el patró `field` per cel·la NO escala

Fets que ho determinen:

1. **Magnitud sense sostre**: `n_POM × (n_talles+3)` cel·les, sense límit al codi per a T1a/T1b/T2
   (§P1.G). Un `field` per cel·la vol dir **un objecte del document per cel·la**, amb `id`, `x`, `y`
   i entrada a `objectBounds` — i, un cop materialitzada, **cada cel·la seria clicable i
   arrossegable** (§P2.D fet 2).
2. **El `field` congela a UN text pla** (`services_ftt_document.py:178-183`): **no pot expressar
   `bold` condicional** (el break de grading, `:3455`) ni el `sub` bilingüe de T1a (`:509`).
3. **No cal**: les cel·les de `type:'table'` **ja són congelades** (§P1.G). El `field` resol un
   problema — el binding viu — que la taula viva **no té**. L'únic que en té és el legacy
   `graded_table`, que és inabastable.
4. El backend **ja té** un mecanisme propi per a la taula: buidar cel·les + `pendent_vincle`
   (`services_ftt_document.py:237-240`), amb rètol pintat als dos camins (`:878`, `:1258`).

**Tres opcions amb cost (sense triar):**

| opció | què fa | cost | conseqüències |
|---|---|---|---|
| **T-1 · Materialització plana** | Cada prim → objecte real (`rect`/`line`/`text`), zero `field`; la taula queda "explotada" com un dibuix editable | **M** al codi, **L** en objectes al document (centenars) | Editable a fons (bold i talla base per cel·la surten gratis) · es perd tota estructura de taula (afegir fila = feina manual) · el document creix molt · `objectBounds` per objecte × N |
| **T-2 · Enriquir el builder, no materialitzar** | Afegir al model de cel·la els atributs que falten (`fill` de cel·la, `bold` de capçalera/REF, marca de columna base) i pintar-los al builder | **S** | Resol el bug del bold i el de la talla base **sense tocar l'arquitectura**; no fa la taula editable per cel·la; conserva live=PDF per construcció |
| **T-3 · Materialització estructurada** | La taula es converteix en un `group` amb un objecte per cel·la **que conserva `row`/`col` a l'objecte**, i un "re-agrupar" que torna a `type:'table'` | **L** | Editable i reversible · exigeix un tipus d'objecte nou o convenció de camps · cap precedent al codi (`ungroupObject:2111` no sap re-agrupar) |

### P2.D — Coordenades i el pont a `globalizeObject`

**Cadena de la capçalera**: coordenades literals de l'SVG canònic en **pt absoluts** (viewBox A4L,
`docs/spec/plantilla_capcalera_ftt.svg`, `:662-667`) → `gx(sx) = (sx − OX)·P` (`:717`) i
`y = (by − OY)·P − ASC·f` (`:729`, `:737`) → **relatives a l'origen del bloc, ja en px**.
`MASTER_HEADER_GEOM` (`:682-687`) és en **mm** (`_mm2 = pt·0.3528` arrodonit a 2 decimals, `:681`):
`x=10.09, y=13.76, w=276.84, h=31.82`.

**Fórmula per materialitzar un prim a mm globals:**

```
mm_local  = px_prim / MM_TO_PX          (= pt_relatiu · 0.3528)
mm_global = MASTER_HEADER_GEOM.{x|y} + mm_local
          = pt_absolut_SVG · 0.3528     (mòdul l'arrodoniment de _mm2, ±0.005 mm)
```

**Cadena de la taula** (diferent): les prims ja són en **px derivats de mm** (`column.width` en mm ×
`MM_TO_PX`, `:480`), sense pt pel mig. `mm_local = px_prim / MM_TO_PX` directe. **No comparteix cap
helper amb el header** (§P1.H).

**⚠️ Trampa del cos de lletra**: els prims porten `size` en **px** (5.080 / 7.620), i `textProps`
(`:943-950`) passa `fontSize: obj.fontSize || 11` **crua, sense `toPx`** → un `type:'text'`
materialitzat ha de portar `fontSize` **en px**, igual que el prim. En canvi `buildFieldChipPrims:532`
converteix `style.fontSize` de **pt** a px. **El mateix nom de camp té dues unitats segons el tipus.**

**`globalizeObject` (`:219-247`)** llegeix del child: `scaleX`, `scaleY`, `rotation`, `width`,
`height`, `rx`, `ry`, `scale`, `x`, `y`, `points`, `x2`/`y2`, `type`. Multiplica escales (`:220-221`),
suma rotacions (`:222`), escala dimensions (`:223-229`), i passa els punts per `groupPointToGlobal`
(`:207-217`: escala → rotació → translació). **Tots els defaults són tolerants** (`|| 1`, `|| 0`) → un
child sense `rotation`/`scaleX` funciona. Efecte secundari: la sortida **sempre** porta `rotation`,
`scaleX`, `scaleY` explícits.

**`groupSelection` (`:2090-2110`)** crea `{id, type:'group', layer:'free', x, y, rotation:0, children:
[localizeObject(o, origin)]}` amb `origin` = mínim d'`objectBounds` en mm (`:2094-2095`), **sense**
`scaleX/scaleY`. **Exclou els objectes `layer === 'template'`** (`:2092`) — **i la capçalera és
`layer:'template'`** (`:3537`).

**Camps mínims perquè `ungroupObject` funcioni sense tocar-lo**: `id` únic · `type` · `x`,`y` en **mm**
(o `points` en mm si `line` — `lineProps:971` **força `x/y` a 0**) · `layer` · opcionalment
`rotation`/`scaleX`/`scaleY` · `width`/`height` si el tipus els usa.
⚠️ **`objectBounds` (`:249-291`)** cau al cas genèric (`:288-290`) per a `text` i `rect`, i usa
`obj.width || 10` / `obj.height || 10` → **un `text` sense `height` mesurarà 10 mm d'alt**.

**Requisits de render per tipus** (`ObjectNode:1421-1534`), amb les diferències que trenquen una
materialització 1:1:

| type | props | trampes |
|---|---|---|
| `text` (`:1470-1483`, `textProps:943-950`) | `text`, `width` (mm), `fontSize` **px cru**, `fontFamily`, `fontStyle`, `fill`, `align`, `textDecoration` | **No posa `verticalAlign`, `ellipsis` ni `wrap:'none'`** — els prims sí (`:846-850`) → un text materialitzat **farà wrap** si `width` és curt |
| `rect` (`:1484-1486`, `rectProps:952-959`) | `width`/`height` mm, `fill`, `stroke`, `strokeWidth` px, `cornerRadius` | **`stroke` per defecte és GOLD** `#c27a2a` si absent — el marc del header és `#1d1d1b`, cal fer-lo explícit. **No propaga `dash`** |
| `line` (`:1490-1494`, `lineProps:969-975`) | `points[]` en mm, `stroke`, `strokeWidth` px, `dash` | `x`/`y` **ignorats** (forçats a 0) |
| `field` (`:1466-1469`, `FieldChipNode:891-899`) | `key`/`label`, `style.fontSize` **en pt**, `x`,`y` mm | **Amplada i alçada són CALCULADES** (`:533-534`), no configurables → **mai coincidiran amb la geometria d'un prim del header** |

**Veredicte P2: cal X, i el bloqueig no és tècnic sinó de política de dades.** La geometria és
resoluble amb una fórmula d'una línia; el que costa és (a) **6 claus noves al catàleg contra una
anotació explícita que ho prohibeix**, (b) el `SIZE RUN` que cap `field` pot expressar, (c) el PAGE
que és impossible, i (d) el logo, on el camí portable i el camí que es veu bé són incompatibles.

---

## BLOC P3 — Base per a les maquetes: fets de ribbon i barra

### P3.A — Ribbon: estructura exacta

**Tabs** (`TSE.jsx:4010-4015`): **4, en aquest ordre**, `id` + `label`, **sense icona** (el botó
només pinta `{tab.label}`, `:4390`):
`file` · `page` · `insert` · `organize` — claus `tech_sheet.ribbon_{file,page,insert,organize}`
(`i18n/{ca,en,es}.json:2459-2462`, paritat confirmada).
Estat: `ribbonGroup` (`:1778`), per defecte `'file'`; canvi a `:4388`.

**Estil de tab** — `ribbonTabStyle(active)` (`:4016-4022`):
`minWidth:86, height:28, border:1px (gold|transparent), borderBottomColor:(gold|border),
borderRadius:'5px 5px 0 0', background:(goldPale|transparent), color:(gold|textMain),
fontSize:var(--fs-body), fontWeight:(700|500)`.

**DOM** (`:4384-4400`), tres nivells:
- Contenidor (`:4385`): `flexShrink:0, background:COL.sidebar, borderBottom:1px COL.border`
  (`CTX_BG/CTX_BORDER/CTX_TEXT` a `:3666`).
- **Fila 1 — tabs** (`:4386`): `display:flex, alignItems:'flex-end', gap:2, minHeight:31,
  padding:'3px 12px 0'`. A la dreta (`marginLeft:'auto'`, `:4393-4395`) un **indicador d'estat
  contextual** `color:COL.textMuted, fontSize:var(--fs-label)` amb prioritat: mode nodes →
  multiselecció → 1 objecte → eina activa → idle (`:4394`).
- **Fila 2 — comandaments** (`:4397`): `display:flex, alignItems:'center', gap:6, minHeight:64,
  padding:'6px 12px 8px', overflowX:'auto'`; únic fill `{renderRibbonContent()}` (`:4398`).

**Alçada total del ribbon ≈ 96 px** (31 + 64 + 1 border).

**`renderRibbonContent()`** (`:4063-4135`) — **no és un `switch`, són `if` encadenats amb `return`**:
1. `if (!locked)` → avís de només-lectura (`:4064-4066`)
2. `if (editingFlatId) return renderNodeEditTools()` (`:4067`)
3. `if (ribbonGroup === 'file')` → 4 items (`:4068-4075`)
4. `if (ribbonGroup === 'page')` → 7 items (`:4076-4088`)
5. `if (ribbonGroup === 'insert')` → 9 items (`:4089-4109`)
6. **fall-through = `organize`** → 17 botons + separador + 4 buscatraços (`:4110-4134`)

**Injectar una tab NOVA: exactament 3 punts d'edició** —
(1) afegir l'entrada a `ribbonTabs` (`:4010-4015`);
(2) afegir un bloc `if (ribbonGroup === '<nou>') { return [...] }` **abans de `:4110`** — atenció:
`organize` ocupa avui el `return` sense guarda, així que una tab nova col·locada després quedaria
inaccessible;
(3) afegir la clau `ribbon_<nou>` als tres `i18n` (~línia 2462).
**No cal tocar el DOM del ribbon** (`:4384-4400`), que itera `ribbonTabs` i delega.

**Helper de botó**: **`ribbonTool({key, icon, label, onClick, disabled, active, title})`**
(`:4037-4043`). No és un component React (per això rep `key` com a propietat). Tooltip = `title` natiu
amb fallback al `label` (`:4038`).
`ribbonToolStyle` (`:4023-4029`): **`width:72, minHeight:50`**, `flexDirection:'column'`, `gap:3`,
`padding:'5px 3px'`, `border:1px (gold|border)`, `borderRadius:5`, `background:(goldPale|field)`,
`fontSize:var(--fs-caption)` (**8 px**), `lineHeight:1.1`, `opacity: disabled ? 0.42 : 1`.
Icona interior **18 px** (`:4040`); etiqueta amb clamp a 2 línies (`ribbonLabelStyle`, `:4031`).
`ribbonSelectStyle` (`:4032-4036`, l'únic control no-botó): `height:50, minWidth:86`.

**Separadors**: **només UN a tot el ribbon**, inline, sense helper (`:4129`):
`{width:1, height:50, background:COL.border, flexShrink:0}`. **Cap altra agrupació visual dins una
fila: NO EXISTEIX** — els botons van seguits amb `gap:6`.

### P3.B — Barra contextual de nodes

Muntatge: `{editingFlatId && (…)}` (`:4278`). **Viu ENTRE la barra de menús i el ribbon** (`:4277` vs
`:4384`), no sota.

Contenidor (`:4279`): `flexShrink:0, display:flex, alignItems:'center', gap:6, **minHeight:34**,
background:COL.sidebar, borderBottom:1px COL.border, padding:'0 10px', **flexWrap:'wrap'**`.
Separador de grup — `nodeBarSep` (`:5330`): `{width:1, height:18, background:COL.border}`, usat **9
vegades** (`:4287, 4294, 4300, 4304, 4318, 4340, 4355, 4366`).

| # | Grup | Línies | Visibilitat | Controls |
|---|---|---|---|---|
| 1 | Indicador de mode | `:4281-4286` | sempre | 1 span (icona 14 px + text `--fs-label` gold 600) |
| 2 | Dos cursors (`SHAPE_TOOL_ITEMS` `:5318-5321`) | `:4289-4293` | sempre | 2 botons (V / A) |
| 3 | Sub-eines (`NODE_TOOL_ITEMS` `:5323-5328`) | `:4295-4299` | sempre | 4 botons (+ / − / B / C) |
| 4 | Topologia close/open/split | `:4301-4303` | sempre | 3 botons |
| 5 | Booleanes | `:4307-4320` | `mode==='shape' && shapeCount>=2` | 4 botons |
| 6 | Alinear + distribuir | `:4323-4342` | `mode==='shape' && shapeCount>=2` | 6 + 2 (aquests 2 amb `opacity:0.4` si `<3`) |
| 7 | Mirall / rotar / escalar | `:4345-4357` | `mode==='shape' && shapeCount>=1` | 2 botons + 2 inputs |
| 8 | Z-ordre dins el compost | `:4360-4368` | `mode==='shape' && shapeCount>=1` | 4 botons |
| 9 | Pintura | `:4370-4380` | sempre | 2 ColorPicker + 1 input |

**Mides literals**: botó d'icona `nodeBarBtn` (`:5329`) = **28×26**, `borderRadius:6`, icona interior
**15 px**. Inputs numèrics: rotació **44×24** (`:4351`), escala **48×24** (`:4354`), gruix **52×24**
(`:4380`), tots `fontSize:var(--fs-label)`, `padding:'0 6px'`; `°`/`%` s'apliquen amb **Enter** i es
buiden, el gruix amb `onChange`.
**`ColorPicker`** (`:5289-5307`) **no té mida configurable**: 1 swatch "cap color" 18×18 + 6 swatches
18×18 (`QUICK_COLORS`, `:5288`) + `<input type="color">` 22×22 → **≈176 px cadascun**, **≈400 px el
grup de pintura**.

⚠️ **La barra fa `flexWrap:'wrap'`**: amb els 9 grups visibles (~30 controls + 2 ColorPickers)
**creix a 2 files**; el `minHeight:34` no és l'alçada real en el pitjor cas.

**`renderNodeEditTools()`** (`:4049-4062`): **només 2 botons, empesos a la dreta** (`marginLeft:'auto'`,
`:4051`). "Fet" (`:4052-4055`): `height:34, padding:'0 12px', background:COL.gold, color:white,
fontWeight:600, borderRadius:6`, icona `ti-check`, `disabled={!flatCanCommit}` amb `opacity:0.45`.
"Cancel·la" (`:4056-4059`): mateixa mida, `border:1px COL.border, background:COL.field`, icona `ti-x`.
La fila 2 del ribbon (64 px) queda **buida a l'esquerra**. Comentari a `:4044-4048`: la fila d'eines
redundant es va retirar a G4 — **hi ha precedent de la neteja**.

### P3.C — Tokens i mides per dibuixar

`COL` (`:73-85`) → valors reals a `frontend/src/index.css`:

| token | var() | hex | ús |
|---|---|---|---|
| `COL.sidebar` | `--white` | `#ffffff` | topbar, menús, barra contextual, ribbon |
| `COL.gold` | `--gold` | `#c27a2a` | accent, actiu, acció principal |
| `COL.goldPale` | `--gold-pale` | `#f5e6d0` | fons d'estat actiu |
| `COL.border` | `--border` | `#e0d5c5` | filets, vores, separadors |
| `COL.textMain` | `--text-main` | `#1d1d1b` | text principal |
| `COL.textMuted` | `--text-muted` | `#868685` | text secundari, icones inactives |
| `COL.bg` | `--bg-card` | `#fafafa` | paleta, panell dret, cortines |
| `COL.work` | `--gray-l` | `#f0f0f0` | fons de treball |
| `COL.field` | `--white` | `#ffffff` | interior de controls |

`FONT = 'IBM Plex Mono, monospace'` (`:59`). Escala (`index.css:47-49`): `--fs-caption:8px` ·
`--fs-label:10px` · `--fs-body:12px`.
**Icones**: sempre `<i className={\`ti ${icon}\`}/>`, mai component. Mides: ribbon **18**, barra
contextual **15**, etiquetes **14**, paleta **17**.

**Cadena vertical de l'editor** (de dalt a baix):
`<header>` (fins `:4258`) → **barra de menús 26 px** (`:4261`) → **[barra contextual 34 px,
condicional]** (`:4279`) → **ribbon ~96 px** (`:4385`) → `<main>` `flex:1` (`:4405`) =
**paleta 46 px** (`:4428`) │ **regles 18 px** (`RULER_SIZE`, `:102`) + viewport (`padding:24`,
`:4507-4509`) │ **aside 270 px** (`:4637`).

### P3.D — MAQUETES (Q1 i Q3)

> Descripció visual per validar VEIENT (llei del vault). **No és codi de producció.** Mides preses
> dels literals de §P3.A-C. Els 96 controls (33 barra nodes + 21 ribbon organitzar + 42 panell) es
> reindexen **per ABAST**, no per superfície d'origen.

#### Reindexació per abast (base comuna de les 4 maquetes)

| Abast | Eines | Origen actual |
|---|---|---|
| **OBJECTE** | alinear ×6 · distribuir ×2 · agrupar · desagrupar · mirall ×2 · z-ordre ×4 · booleanes ×4 · eliminar · duplicar | ribbon Organitzar (21) + menú Objecte |
| **FORMA** (subpath) | alinear ×6 · distribuir ×2 · mirall ×2 · z-ordre ×4 · booleanes ×4 · rotar° · escalar% · tancar/obrir · partir/extreure · eliminar | barra nodes (grups 4-8) + panell mini `:4917-4931` |
| **NODE / SEGMENT** | cursor forma · cursor directe · afegir · treure · convertir · tisores · nanses | barra nodes (grups 2-3) |
| **APARENÇA** (transversal als 3 abasts) | emplenat · color de traç · gruix · puntes · dash | barra nodes (grup 9) + panell `:4935-4969` |
| **GEOMETRIA NUMÈRICA** (només objecte) | W/H · X/Y · rotació absoluta · bloqueig de proporció | panell `:4819-4844`, `:5044-5047` |
| **CONTINGUT** (per tipus) | text (10 controls) · taula (6) · polígon · SVG | panell `:4863-4906`, `:4977-5039` |

**La clau de la fusió**: les tres primeres files són **la mateixa llista d'eines amb tres abasts**.
Una sola barra que canvia d'abast segons el mode elimina 3 de cada 4 duplicats sense treure cap
capacitat.

---

#### PARELLA (a) — Transacció vs continu

**(a1) AMB Fet/Cancel·lar — l'edició de nodes és una TRANSACCIÓ**

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ Fitxer  Edició  Objecte  Visualització                                            26 px  │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ ◆ EDITANT VECTOR · Formes · 2          ← estat modal, gold, fons goldPale         34 px  │
│ ┌────┬────┐│┌───┬───┬───┬───┐│┌───┬───┬───┐│┌───┬───┬───┬───┐│  fons #f5e6d0 tènue      │
│ │ ▲  │ ▷  │││ + │ − │ B │ C │││⚯ │⚮ │⤪ │││ ∪ │ ∩ │ ⊖ │ ⊕ ││  = "ets en una sessió"   │
│ └────┴────┘│└───┴───┴───┴───┘│└───┴───┴───┴───┘│└───┴───┴───┴───┘│                       │
│  28×26      15px icona                                                                   │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│  Fitxer │ Pàgina │ Inserir │ Organitzar │ Editar │             ◆ mode edició     31 px   │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│                                                          ┌─────────┐ ┌──────────┐        │
│   (fila buida — les eines són a la barra de dalt)        │ ✓ Fet   │ │ ✕ Cancel │  64 px │
│                                                          └─────────┘ └──────────┘        │
│                                                           34px gold   34px border        │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```
Lectura: hi ha un **estat visible de sessió** (fons goldPale a tota la barra + etiqueta "EDITANT
VECTOR"). L'usuari sap que està "dins" i que en surt amb un dels dos botons. ⌘Z desfà **dins** la
sessió (`:3240` → història interna `PaperFlatEditor.jsx:238-266`). Cancel·lar descarta tot **excepte
els objectes creats per un split** (`:3280-3291`, forat conegut). Correspon exactament al
comportament d'avui.

**(a2) SENSE Fet/Cancel·lar — edició CONTÍNUA amb l'undo del document**

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ Fitxer  Edició  Objecte  Visualització                                            26 px  │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│  Fitxer │ Pàgina │ Inserir │ Organitzar │ ▸Editar◂ │        ◆ Formes · 2        31 px    │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ ┌────┬────┐│┌───┬───┬───┬───┐│┌───┬───┬───┐│┌───┬───┬───┬───┐│┌──┬──┬──┬──┐│           │
│ │ ▲  │ ▷  │││ + │ − │ B │ C │││⚯ │⚮ │⤪ │││ ∪ │ ∩ │ ⊖ │ ⊕ │││⇤ │⇥ │⇧ │⇩ ││   64 px   │
│ └────┴────┘│└───┴───┴───┴───┘│└───┴───┴───┴───┘│└───┴───┴───┴───┘│└──┴──┴──┴──┘│           │
│  fons normal (COL.sidebar) — cap estat modal; sortir = clicar fora o canviar de tab      │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```
Lectura: **no hi ha sessió**. Cada gest escriu al model i entra a `useDocumentHistory`
(`ftt/history.js:13-88`, debounce 500 ms, límit 50) → ⌘Z desfà **una acció**, no "tota l'edició".
Desapareixen: els botons Fet/Cancel·lar (`:4052-4059`), `commit` i `onCanCommitChange`
(`PaperFlatEditor.jsx:803-856`), i `historyRef` (`:238-266`). **La barra guanya 2 files d'espai** i el
ribbon recupera la seva fila 2. Cost: cal decidir què passa amb els gestos intermedis d'un drag
(avui, 1 snapshot per gest, `:695`).

---

#### PARELLA (b) — "Editar" com a tab vs com a barra contextual

**(b1) TAB del ribbon — persistent, previsible**

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│  Fitxer │ Pàgina │ Inserir │ Organitzar │ ▸Editar◂ │              ◆ Formes · 2   31 px   │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ ┌──────┐┌──────┐│┌──────┬──────┬──────┬──────┐│┌──────┬──────┬──────┐│┌──────┬──────┐   │
│ │  ▲   ││  ▷   │││  +   │  −   │  B   │  C   │││  ⚯   │  ⚮   │  ⤪   │││  ∪   │  ∩   │   │
│ │forma ││direct│││afegir│treure│conv. │tisor.│││tancar│obrir │partir│││ unir │inters│   │
│ └──────┘└──────┘│└──────┴──────┴──────┴──────┘│└──────┴──────┴──────┘│└──────┴──────┘   │
│   72×50 ribbonToolStyle · icona 18px · etiqueta 8px  ← MIDA GRAN, amb text        64 px  │
└──────────────────────────────────────────────────────────────────────────────────────────┘
     ▲ ABAST segons selecció: cap → gris · objecte → eines d'objecte · forma → eines de forma
```
Lectura: l'"Editar" viu **sempre al mateix lloc**, com Organitzar. Botons de **72×50 amb etiqueta
llegible** (mida ribbon). Cost: `overflowX:'auto'` (`:4397`) obligarà a scroll horitzontal amb ~30
eines a 72 px = ~2160 px. **Punts d'edició: 3** (§P3.A) i **cap canvi al DOM del ribbon**.

**(b2) BARRA CONTEXTUAL per selecció — compacta, apareix i desapareix**

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ ◆ Formes · 2  │▲│▷│ │+│−│B│C│ │⚯│⚮│⤪│ │∪│∩│⊖│⊕│ │⊨│⊫│⊩│⊪│ │↔│↕│ │ 45°││120%│    34 px │
│                28×26 · icona 15px · sense etiqueta      ← MIDA PETITA, densa              │
│ ▓▓▓ amb 9 grups visibles fa WRAP a 2a fila (flexWrap:'wrap', :4279) ▓▓▓            +34 px │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│  Fitxer │ Pàgina │ Inserir │ Organitzar │                                          31 px  │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│  [contingut de la tab activa — el ribbon segueix disponible]                       64 px  │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```
Lectura: apareix només quan hi ha alguna cosa editable seleccionada; **el ribbon no es perd** (pots
inserir una taula sense sortir de l'edició). Cost: **el wrap a 2 files ja passa avui** (§P3.B) i
empeny el llenç cap avall de manera intermitent — moviment vertical de la pàgina cada cop que canvia
la selecció.

**Comparació en un cop d'ull:**

| | (b1) Tab | (b2) Barra contextual |
|---|---|---|
| Mida de botó | 72×50 amb etiqueta | 28×26 sense etiqueta |
| Posició | fixa, previsible | apareix/desapareix |
| El ribbon segueix accessible | ❌ (ocupa la fila) | ✅ |
| Salt vertical del llenç | mai | a cada canvi de selecció |
| Overflow amb ~30 eines | scroll horitzontal | wrap a 2a fila |
| Punts d'edició al codi | 3 (§P3.A) | ja existeix (`:4277-4382`) |

**Veredicte P3: llest.** Els tres punts d'injecció d'una tab estan identificats, tots els literals
d'estil recollits, i les quatre maquetes són dibuixables a partir de fets. Falta la decisió humana.

---

## BLOC P4 — Neteges confirmades (inventari, no tocar)

### P4.A — PaperKonvaPoc: 5 punts

| # | Punt | Ubicació | Altres consumidors |
|---|---|---|---|
| 1 | Fitxer | `frontend/src/pages/PaperKonvaPoc.jsx` (486 l.) | cap |
| 2 | Import lazy | `frontend/src/App.jsx:54` | únic |
| 3 | Ruta | `frontend/src/App.jsx:341` (`disseny/poc-paper`) | única |
| 4 | Bloc i18n `poc_paper` (**24 claus**) | `i18n/ca.json:3294-3319` · `en.json:3294-3319` · `es.json:3294-3319` | **cap fora del PoC**; els tres blocs són **byte-alineats** (mateixes línies) |
| 5 | Asset | `frontend/public/CALLIE.svg` (310 KB), referenciat a `PaperKonvaPoc.jsx:16`, `:301-303` | cap altre consumidor de codi |

- **Entrada de navegació: NO EXISTEIX** (grep de `poc-paper` a `frontend/src` → només `App.jsx`).
- **`paper` i `react-konva` NO es poden desinstal·lar**: els consumeixen `PaperFlatEditor.jsx:2` i
  `ftt/paperbool.js:6`. **Cap neteja de `package.json`.**
- ⚠️ **L'asset ja està trencat**: `CALLIE.svg:206,217,228` referencia `CALLIE-1/2/3.png` via
  `xlink:href`, i **aquests PNG no existeixen** a `frontend/public/`.
- `TSE.jsx:4239` conté "Blusa CALLIE" com a text d'exemple del breadcrumb — **no és l'asset**, no es
  toca.

### P4.B — Superfícies mortes

**`PALETTE_SWATCHES`** — definició `TSE.jsx:3896-3900` (3 entrades), render `:4484-4489` amb
`disabled` **literal sense expressió** (`:4485`) i **sense `onClick`**. Grep del símbol → només `:3896`
i `:4484`; **no hi ha cap estat de color global** que els pugui governar. Comentari honest a `:3895`.
i18n exclusives: `tech_sheet.swatch_{fill,stroke,swap}` → `{ca,en,es}.json:2495-2497`.

**`import-measures`** — `TSE.jsx:4102-4103`. Li falten **les dues coses alhora**: **no té `onClick`**
(paràmetre absent a la crida a `ribbonTool`, definit a `:4037`) **i** té `disabled: true` literal.
Comentari `:4102`: «R1: placeholder … (sense handler)». i18n exclusiva:
`tech_sheet.import_measurements` → `{ca,en,es}.json:2663`.

**Altres controls morts:**

| Línia | Control | Naturalesa |
|---|---|---|
| `:4072` | `autosave` (`disabled:true`, sense `onClick`) | **NO és mort per error**: és un indicador d'estat disfressat de botó. Intencional |
| `:4073` | `version` (`v{n}`, `disabled:true`) | ídem — indicador, no acció |
| `:4666-4668` | `import_from_ftt` amb `disabled` literal i `title=import_soon` | **placeholder mort** al panell d'importació; conviu amb el germà **viu** `:4663` que usa la mateixa clau |
| `:4436`, `:4451`, `:4465` (+ estils `:4437`, `:4452`, `:4466`) | branques `it.soon ? … : …` de la paleta | **codi mort per condició sempre falsa**: grep `soon: true` → **0 coincidències**; cap entrada de `PALETTE` (`:3820-3894`) porta `soon` |
| `:3663` | `paletteBtnSoon` | un cop retirats els swatches, només el consumeixen les 3 branques mortes anteriors |

**Cap** `onClick={() => {}}` buit ni `TODO` al fitxer. Els "no implementat" restants són missatges
honestos: `flash(t('tech_sheet.import_dxf_soon'))` (`:3926`, `:3954`).
⚠️ `tech_sheet.coming_soon` (`{ca,en,es}.json:2498`) **NO és exclusiva**: la comparteixen
`import-measures` (`:4103`) i les branques `soon` (`:4436`, `:4451`, `:4465`) — queda òrfena **només
si cauen totes**.

### P4.C — Menú de text: què cau i què no

`menuItem` (`:4139-4147`) accepta només `{label, shortcut, onClick, disabled}` → **cap entrada té
icona**: l'única aportació expressiva del menú sobre el ribbon són **les dreceres anunciades**.
Guard comú del menú Objecte: `objDisabled` (`:4152`) = `!locked || !!editingFlatId || cond`.

**33 entrades · 28 duplicades · 5 úniques.**

#### Menú FITXER (`:4153-4157`) — 3 entrades, **0 úniques**

| id | acció | on més | ÚNICA? |
|---|---|---|---|
| `mf-export` | `onExport` (`:3587`) | ribbon `:4070` · **botó gold de la topbar** `:4252` | NO (×3) |
| `mf-save-tpl` | `setSaveAsTpl` (`:4155`) | ribbon `:4071` | NO |
| `mf-import` | `openImport('garment')` (`:3911`) | ribbon `:4101` | NO |

#### Menú EDICIÓ (`:4164-4172`) — 6 entrades, **5 ÚNIQUES** ⚠️

| id | drecera | handler | on més | ÚNICA? |
|---|---|---|---|---|
| `me-undo` | ⌘Z | `undo` (`:1895`) | **només teclat** `:2521-2524` | **SÍ** |
| `me-redo` | ⇧⌘Z | `redo` (`:1895`) | **només teclat** `:2523`, `:2526-2529` | **SÍ** |
| `me-copy` | ⌘C | `copySelection` (`:3792`) | **només teclat** `:2531-2535` | **SÍ** |
| `me-paste` | ⌘V | `pasteClipboard` (`:3797`) | **només teclat** `:2537-2541` | **SÍ** |
| `me-dup` | ⌘D | `duplicateSelection` (`:3803`) | **només teclat** `:2543-2547` | **SÍ** |
| `me-delete` | ⌫ | `deleteSelection` (`:3739`) | ribbon `:4127` · teclat `:2482-2504` | NO |

**Aquestes 5 són l'única superfície VISIBLE de desfés/refés/copiar/enganxar/duplicar.** Si es retira
el menú sense reubicar-les, les accions només existiran com a drecera invisible.

#### Menú OBJECTE (`:4173-4206`) — 24 entrades, **0 úniques per acció**

| id(s) | acció | on més | ÚNICA? |
|---|---|---|---|
| `mo-group` / `mo-ungroup` | `groupSelection` `:2090` / `ungroupObject` `:2111` | ribbon `:4119`/`:4120` | NO |
| `mo-fwd` / `mo-bwd` | `moveSelectionInFreeLayer` `:2055` | ribbon `:4125`/`:4124` · Capes `:4749`/`:4751` | NO (×3) |
| `mo-front` / `mo-back` | `moveSelectionToFreeLayerEdge` `:2078` | ribbon `:4126`/`:4123` | NO |
| `mo-align-*` (×6) | `alignSelection` `:2121` | ribbon `:4111-4116` | NO |
| `mo-dist-h` / `mo-dist-v` | `distributeSelection` `:2145` | ribbon `:4117-4118` | NO ⚠️ **llindar diferent** |
| `mo-mirror-h` / `mo-mirror-v` | `mirrorObjects` `:2001` | ribbon `:4121-4122` | NO ⚠️ **àmbit diferent** |
| `mo-pf-*` (×4) | `applyPathfinder` `:3745` | ribbon `:4130-4133` | NO |
| `mo-lock-sel` | `selectedIds.forEach(toggleLock)` `:3816` | Capes `:4746` (**per objecte**, no batch) | NO per l'acció · **SÍ per la forma batch** |
| `mo-hide-sel` | `selectedIds.forEach(toggleVisible)` `:3811` | Capes `:4743` (per objecte) | ídem |
| `mo-hdr-delete` / `mo-hdr-detach` | `deleteHeaderOnPage` `:3562` / `detachHeaderOnPage` `:3569` | clic dret `:5103`/`:5104` | NO |

#### Menú VISUALITZACIÓ (`:4207-4212`) — 4 entrades, **0 úniques** (totes ×3: ribbon Pàgina + barra d'estat)

`mv-in` (`:4084`, `:5138`) · `mv-out` (`:4083`, `:5134`) · `mv-100` (`:4085`, `:5141`) · `mv-fit`
(`:4086`, `:5142`). ⚠️ `mv-100` usa el **literal `'100%'` sense clau i18n** (`:4210`), replicat a
`:4085` i `:5141`.

**Conclusió operativa**: **23 entrades es poden retirar sense cap pèrdua**. Han de sobreviure en algun
lloc: **les 5 d'Edició** (undo/redo/copy/paste/duplicate) i, si es vol conservar el batch, **lock/hide
sobre selecció múltiple** (avui Capes només ho fa per objecte).

### P4.D — Panell Capes: un bug real trobat pel camí

Controls (`:4728-4759`, tots dins `dockTab === 'layers'`): seleccionar (`:4737`, `selectOnly:1967`) ·
visibilitat (`:4743-4745`) · bloqueig (`:4746-4748`) · z-ordre endavant/enrere (`:4749-4752`), tots
condicionats a `locked && o.layer === 'free'` (`:4741`).
**No hi ha "portar al davant / enviar al fons"** (`moveSelectionToFreeLayerEdge:2078` no s'hi crida).

⚠️ **BUG DE CLOSURE** (`:4749`, `:4751`): el handler fa
`selectOnly(o.id); moveSelectionInFreeLayer(dir)` **al mateix tick**. Però `selectOnly` és
`setSelectedIds([objId])` (`:1967`), un `setState` **asíncron**, i `moveSelectionInFreeLayer` és un
`useCallback` que **captura `selectedIds` per closure** (`:2056`, deps a `:2077`).
→ **El botó de z-ordre del panell Capes mou la selecció ANTERIOR, no l'objecte de la fila clicada.**
Si no hi havia res seleccionat, `ids` és buit i no fa res.
A més, **els botons de Capes no tenen `disabled`**: no comproven `nodeMode`/`editingFlatId`, a
diferència del ribbon (`:4124`) i del menú (`objDisabled`, `:4152`) → són clicables en mode edició de
nodes.

**Veredicte P4: llest.** Les neteges són petites i tancades. S'hi afegeixen **dues troballes que no
eren a l'encàrrec** i que valen més que la neteja: el bug de closure de Capes i les 5 entrades
d'Edició que no tenen cap altra superfície visible.

---

## TAULA FINAL — EXISTEIX / FALTA / DIFERENT

| # | Peça | Estat | Àncora |
|---|---|---|---|
| 1 | Taula de mesures amb binding viu | **NO EXISTEIX** al camí viu — 100 % congelada | `TSE.jsx:3368-3370`, `:3455-3462` |
| 2 | Taula amb binding viu (legacy) | **EXISTEIX però inabastable** — `setPickFitting(true)` no es crida | `:3342-3365`, `:5155` |
| 3 | Builder de taula compartit live/PDF | **EXISTEIX** — mateixa funció als dos camins | `:875` vs `:1256` |
| 4 | Criteri del bold a les cel·les | **DIFERENT del que sembla** — és "break de grading", no jerarquia tipogràfica; només T1b | `:3448-3455` |
| 5 | Bold a capçalera de columna o columna REF (viu) | **NO EXISTEIX** | `:497`, `:512` |
| 6 | Realçat visual de la talla base (viu) | **NO EXISTEIX** — només el sufix `*` | `:3445`; builder `:473-524` sense cap ref |
| 7 | Realçat visual de la talla base (legacy) | **EXISTEIX escrit** — fons gold a capçalera + fons de columna | `:425-430`, `:439-441` |
| 8 | Dada `base_size` al frontend | **EXISTEIX i arriba** | `graded_spec_views.py:76-78`; `TSE.jsx:141` |
| 9 | Edició de T1a/T1b | **NO EXISTEIX** — cap control | guarda `:4977` |
| 10 | Edició de cel·la al canvas | **NO EXISTEIX** — texts `listening={false}`, cap `onDblClick` | `:849`, `:874-886` |
| 11 | W/H del panell sobre taules | **DIFERENT** — control mort: `resizeObjectTo` no té branca `'table'` | `:2182` vs `:2209-2249` |
| 12 | `obj.width/height` de taula després d'afegir files | **DIFERENT** — no es recalcula, els bounds queden desfasats | `:5002`, `:5006` vs `:288-290` |
| 13 | Límit de mida / paginació de taula | **NO EXISTEIX** (excepte `custom` 20×20) | `:5227`, `:5231`; `:490` |
| 14 | Importació de mesures | **NO EXISTEIX** — placeholder sense handler | `:4102-4103` |
| 15 | `field_key` per als 12 valors del header | **7 exactes · 1 amb format diferent · 3 grups absents (6 claus) · 1 impossible** | taula §P2.B |
| 16 | Ampliar el catàleg de `field_key` | **PROHIBIT per anotació** al codi | `TSE.jsx:127-129` |
| 17 | `field` amb marcatge per segment (SIZE RUN) | **NO EXISTEIX** — congela a UN text pla | `services_ftt_document.py:178-183`; `:775-799` |
| 18 | PAGE com a camp materialitzable | **IMPOSSIBLE** — ve de `pageCtx`, no del model | `:744`, `:2448` |
| 19 | Camí de logo portable i amb bona geometria alhora | **NO EXISTEIX** — camí 1 és 40×16 rígid, camí 3 és el que es veu però no és objecte | `services_ftt_document.py:150-155` vs `TSE.jsx:694-705` |
| 20 | `groupSelection` sobre la capçalera | **BLOQUEJAT** — exclou `layer==='template'`, i el header ho és | `:2092` vs `:3537` |
| 21 | `fontSize` amb unitat coherent | **DIFERENT** — `text` en px (`:946`), `field` en pt (`:532`) | — |
| 22 | `text` materialitzat amb `ellipsis`/`wrap:'none'` | **NO EXISTEIX** — `textProps` no els posa; els prims sí → farà wrap | `:943-950` vs `:846-850` |
| 23 | `rect` materialitzat sense `stroke` explícit | **DIFERENT** — el default és **gold**, no ink | `rectProps:952-959` |
| 24 | Injecció d'una tab nova al ribbon | **EXISTEIX, 3 punts**; `organize` és el fall-through | `:4010-4015`, `:4110`, i18n `:2462` |
| 25 | Separadors/grups visuals al ribbon | **NO EXISTEIX** — un únic separador inline | `:4129` |
| 26 | Barra contextual sense wrap | **NO EXISTEIX** — `flexWrap:'wrap'`, creix a 2 files | `:4279` |
| 27 | PaperKonvaPoc: punts de retirada | **5** (fitxer, import, ruta, 24 claus ×3 idiomes, asset) | `App.jsx:54`, `:341`; i18n `:3294-3319` |
| 28 | `CALLIE.svg` | **ja trencat** — referencia 3 PNG inexistents | `CALLIE.svg:206,217,228` |
| 29 | Branques `soon` de la paleta | **CODI MORT per condició** — cap `PALETTE` declara `soon` | `:4436`, `:4451`, `:4465` vs `:3820-3894` |
| 30 | Entrades del menú de text retirables | **23 de 33**; 5 (Edició) no tenen cap altra superfície visible | §P4.C |
| 31 | Z-ordre del panell Capes | **DEFECTUÓS** — bug de closure: mou la selecció anterior | `:4749-4752` vs `:1967`, `:2056` |
| 32 | Guard de mode node coherent | **DIFERENT ×3** — menú `editingFlatId`, ribbon `nodeMode`, Capes **cap** | `:4152` vs `:4111` vs `:4741` |
| 33 | ⌘G anunciat al menú Agrupar | **NO CABLAT** — el handler només tracta z/y/c/v/d | `:4174` vs `:2512-2552` |

---

## 💡 PROPOSTA (a validar)

> Tot el que segueix és proposta, no fet. Les decisions són humanes (Patró C).

### 1 · Els dos bugs de la taula són barats i independents de tot

**Bold** (S): afegir jerarquia tipogràfica al builder — capçalera de columna en bold (`:497`) i
columna REF en bold (com ja fa el legacy a `:449`) — i **conservar** el bold de break com a **segona
senyal diferent** (subratllat, o color, o una marca `▸`), perquè avui les dues coses comparteixen
codificació i es confonen. Punt únic: `buildTableCellPrimitives:473-524`.

**Talla base** (S): portar al builder viu el que el legacy ja fa (`:425-430`, `:439-441`). La dada ja
hi és (`data.base_size`, usada a `:3445`); només cal marcar la columna al model de cel·la i pintar-la.
**Cau als dos camins alhora** (live i PDF) per construcció.

Tots dos són **T-2** de §P2.C: enriquir el builder, no materialitzar. **Cost total ≈ S+S, risc nul,
i no depenen de cap decisió d'arquitectura.** Es poden fer abans que res.

### 2 · La materialització de la capçalera té un ordre natural

```
   ┌─────────────────────────────────────────────┐
   │ D1 · Decisió CTO: ampliar FIELD_CATALOG?    │  ← bloqueja tot el camí "amb binding"
   │      (6 claus noves, contra l'anotació :127)│
   └──────────┬──────────────────────────────────┘
              │ SÍ                        │ NO
   ┌──────────▼──────────┐     ┌──────────▼───────────────────┐
   │ M-A materialització │     │ M-B materialització PLANA    │
   │  amb `field` (7+6   │     │  (tot a `text`; es perd el   │
   │  claus) · cost M    │     │  binding en canviar de host) │
   └──────────┬──────────┘     └──────────────────────────────┘
              │
   ┌──────────▼──────────────────────────────────────────────┐
   │ M-C casos irreductibles — cal decisió per cadascun:     │
   │  · SIZE RUN → N texts separats? un text sense marcatge? │
   │  · PAGE → es congela? es deixa fora del desagrupat?     │
   │  · LOGO → camí 1 (portable, 40×16) o camí 3 (aspecte)?  │
   └──────────┬──────────────────────────────────────────────┘
              │
   ┌──────────▼──────────┐   ┌────────────────────────────────┐
   │ M-D aixecar el guard│   │ M-E reutilitzar ungroupObject  │
   │ layer==='template'  │──▶│ (:2111) — ja existeix, cost S  │
   │ a groupSelection    │   └────────────────────────────────┘
   └─────────────────────┘
```

### 3 · Per a les taules, la recomanació de fet és NO materialitzar

Els fets de §P2.C apunten a **T-2**: el `field` resol un problema que la taula viva no té (ja és
congelada), no pot expressar el `bold` condicional ni el `sub` bilingüe, i la magnitud (centenars
d'objectes clicables) és desproporcionada. **T-1/T-3 només tenen sentit si el que Agus vol és
"explotar" una taula concreta per retocar-la a mà** — cas d'ús que caldria confirmar abans de pagar-ne
el cost.

### 4 · Preguntes de disseny per a Agus

1. **Q1 (transacció vs continu)** — les maquetes (a1)/(a2) de §P3.D. La resposta decideix si
   `commit`, `onCanCommitChange`, `historyRef` i els botons Fet/Cancel·lar desapareixen.
2. **Q3 (tab vs barra contextual)** — maquetes (b1)/(b2). Comparació a la taula de §P3.D.
3. **Ampliar `FIELD_CATALOG`?** L'anotació `:127-129` ho prohibeix explícitament. Sense això, la
   capçalera materialitzada perd el binding en canviar de host (degradació que
   `services_ftt_document.py:338-342` ja documenta com a coneguda).
4. **Bold de break: es conserva?** Si es conserva, cal una segona codificació visual perquè no es
   confongui amb la jerarquia de capçalera.
5. **"Explotar" una taula: cas d'ús real?** Si no ho és, T-2 tanca el tema i T-1/T-3 no s'escriuen.
6. **Les 5 entrades d'Edició** (undo/redo/copy/paste/duplicate): on van si es retira el menú de text?
   Avui no tenen cap altra superfície visible.
7. **El bug de Capes (`:4749-4752`)**: es corregeix en aquest àmbit o s'anota per a un altre?
8. **`import-measures`**: es retira el placeholder o es manté com a promesa visible?
