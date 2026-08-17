# DIAGNOSI Q8 · LES TAULES DE LA FITXA TÈCNICA (fitting · grading · size set)

> 17/08/2026 · Patró A curt, abans de cap bloc. Substrat: E1+E2 aterrats (fins a `33fa3e8c`),
> `garmentFitxa.js`/T9, `taulaPresaPerTalla.js` (constructor B2).
> Territori amb mines datades: tot el que hi ha aquí sota s'ha VERIFICAT avui, no rellegit.

---

## D1 · TechSheetEditor: on són T0 i T3 post-E1/E2

**S42 seguia vigent.** Verificat al fitxer d'avui:

| Taula | Constructor | Eix |
|---|---|---|
| T0 · mesures talla base | [`TechSheetEditor.jsx:5066`](../../frontend/src/pages/TechSheetEditor.jsx#L5066) | `garmentId: GARMENT_MARE` **clavat** |
| T1a · fitting | [`:5132`](../../frontend/src/pages/TechSheetEditor.jsx#L5132) | `garmentId: g.garment` (partit) |
| T1b · grading | [`:5191`](../../frontend/src/pages/TechSheetEditor.jsx#L5191) | `garmentId: g.garment` (partit) |
| T3 · repàs | [`:5263`](../../frontend/src/pages/TechSheetEditor.jsx#L5263) | `garmentId: GARMENT_MARE` **clavat** |
| T2 · BOM · custom | `:5286` · `:5303` | `GARMENT_MARE` (correcte: no tenen eix) |

T0 i T3 segueixen fora de partició. **No és scope d'aquest tram** (Q8 són tres taules NOVES);
s'anota. La LLEI es respecta: `partirTaules` reparteix i cada objecte neix amb el seu
`garmentId`; l'eix va a l'OBJECTE.

## D2 · `hidratarPagines`: el mode de fallada, confirmat

[`paginesFtt.js:19-25`](../../frontend/src/utils/paginesFtt.js#L19) reconstrueix la PÀGINA
**camp a camp** (`id`, `objects`, `guides`, i `format` per `ambFormat`). Qualsevol clau NOVA de
pàgina es perd en silenci al round-trip.

**No afecta l'estratègia de N taules apilades per peça**, i el motiu és exacte: els objectes hi
passen per `{ ...o, id }` — spread OPAC. Un grup de N taules és N **objectes**, cadascun amb el
seu `garmentId`, i tots sobreviuen. **Cap clau de pàgina nova en tot el tram.**

## D3 · L'espec tipogràfica real del full de fitting descarregable

Font: [`FittingPrintSheet.jsx`](../../frontend/src/pages/FittingPrintSheet.jsx) (+ `ThPr`/`TdPr`).

| Element | Valor real |
|---|---|
| Família | `IBM Plex Mono, ui-monospace, monospace` |
| Cos de dades | **8.5pt** |
| Cos de capçalera | **7.5pt**, MAJÚSCULES, `letter-spacing .05em` |
| Fila-títol de prenda | 8.5pt, `font-weight 700`, filet inferior 1px tinta forta |
| Filet de fila | 1px `--border` · filet de capçalera 1px `--text-main` |
| Encoixinat | capçalera `5px 4px` · dades `2px 5px`, `line-height 1.3` |
| Salt de pàgina | `thead { display: table-header-group }` + `tr { break-inside: avoid }` |

**Sòl de 8pt:** el builder del canvas ja el guarda (`Math.max(8, style.fontSize)`,
[`:914`](../../frontend/src/pages/TechSheetEditor.jsx#L914)). ⚠️ **Però `fitTableObj`
([`:4945`](../../frontend/src/pages/TechSheetEditor.jsx#L4945)) ESCALA l'objecte sencer per
fer-lo cabre a la pàgina** — el sòl del builder no sobreviu a l'escala. Una taula llarga avui
no es parteix: s'encongeix. **Aquest és el forat que el requisit de salt de pàgina tanca.**

**LAYER com a columna: ja hi ha precedent.** El full descarregable la porta —`col_layer`,
resolta amb `etiquetaCapa(slug, dicc, 'en')`— i la col·loca **`#` · LAYER · CODE · NAME**.
→ **Proposta (Q8): LAYER just ABANS del POM**, coherent amb el full. Amplada 18 mm.

## D4 · Acta falsa a `CheckMeasureEditor.jsx:723`

**Confirmada falsa i ja censada** (`CENS_PODA_PLATAFORMA.md` §ítem 17): `ItemAuthoring` està
retirat de rutes ([`App.jsx:61`](../../frontend/src/App.jsx#L61), `:483`, substituït per
`CatalegPecesItem`) i `PromoteToItemButton` no té cap consumidor.
**Q8 NO toca `CheckMeasureEditor.jsx`** → la condició del brief («si aquest tram toca aquell
fitxer») no es compleix i el comentari **no s'esmena en aquest tram**. Queda al report.

---

## LES FONTS DE LES TRES TAULES (i cap contracte paral·lel)

### Q8a · fitting, per peça
`GET /api/v1/piece-fittings/<id>/` → `grid`. Les línies porten els TRES eixos
(`capa`/`instancia`/`garment`, [`serializers.py:375-381`](../../backend/fhort/fitting/serializers.py)),
`valor_teoric`, `valor_real`, `decisio`, `nota`, `nom_fitxa`, `nom_en`, `nom_local`, `size_label`.

**Lectura de la columna `[<TALLA BASE>]`**: `valor_teoric` de la línia de la talla base de la
**darrera sessió TANCADA**. No és una tria de comoditat: `valor_teoric` és l'estat de l'spec
**a l'obertura** de la sessió, o sigui la darrera mesura vàlida aprovada per precedència
temporal — amb dos fittings, el teòric del segon ja és la consolidació del primer
(`consolidate_base_from_fitting`). Qualsevol altra font seria una segona veritat per a la
mateixa cel·la. **`Actual` = `valor_real` només si `liniaTeContingut`** (existir no és haver
mesurat, `taulaPresaPerTalla.js:43`).

### Q8b · grading, per peça
`GET /api/v1/models/<id>/taula-mesures/` — **una sola font, i les porta TOTES**:
`garment`, `capa`, `instancia`, noms, `logica`, `increment_base`, `increment_break`,
`talla_break_label` i **`graded`** (valor per talla), més `size_run`
([`models_app/views.py:2093-2160`](../../backend/fhort/models_app/views.py#L2093)).
No cal fusionar-la amb `graded-table/` — que a més **no serveix `garment`** i faria caure totes
les files a la mare ([acta a `:5187`](../../frontend/src/pages/TechSheetEditor.jsx#L5187)).

🔒 **`Break size` passa per `utils/breakConvention.aDocument(label, run)`**: la BD desa en
convenció de MOTOR i el document es llegeix en convenció de DOCUMENT (±1 posició). Sense run
o sense traducció possible → `—`, mai una etiqueta inventada.

### Q8c · size set, per peça
`construeixTaulaPresaPerTalla(grid)` de [`taulaPresaPerTalla.js`](../../frontend/src/utils/taulaPresaPerTalla.js)
— **font única, cap contracte paral·lel**. Q8 el consumeix NOMÉS per import i no toca cap
predicat (`liniaTeContingut` és d'E2).

### Els noms de peça
`GET /models/<id>/peces/` + `nomDeLaPeca` + **`grupsDelFull(files, peces, etiquetaMare)`**
([`grupsDelFull.js`](../../frontend/src/utils/grupsDelFull.js)) — ja resol l'ordre (mare
primer, del contracte) i el títol. Es REUTILITZA: no es reescriu la llei de partir.

---

## EL QUE FALTA CONSTRUIR AL BUILDER (i per què és additiu)

`buildTableCellPrimitives` ([`:910`](../../frontend/src/pages/TechSheetEditor.jsx#L910)) pinta
capçalera + files i res més. L'espec demana tres coses que avui no sap fer:

1. **Títol de taula** (nom de peça + unitat declarada). L'acta de T0 (`:5013`) deia que
   afegir-ne un «canviaria el render de TOTES les variants» — cert **si fos obligatori**.
   Amb `obj.titol` OPCIONAL, una taula sense títol surt amb geometria idèntica al pixel.
2. **Cel·la en vermell negreta** (`Actual ≠ base`, `Dif ≠ 0`). Avui l'únic color per cel·la és
   `cell.bold` → vermell **+ subratllat**, i és LEGACY de break pre-S4. Clau nova `alerta`,
   que no col·lisiona amb cap snapshot ja inserit.
3. **Tall per pàgina**: qui talla no pot ser el navegador (això és Konva). El tall es fa a
   la INSERCIÓ: les files es reparteixen en blocs que caben a l'alçada útil, i cada bloc és un
   objecte `table` complet —amb capçalera i títol— a la seva pàgina. **Cap fila partida**, i el
   sòl de 8pt es respecta perquè ja no cal encongir res.

**L'export PDF surt de franc**: el render offscreen fa servir el MATEIX
`buildTableCellPrimitives` ([`:2004`](../../frontend/src/pages/TechSheetEditor.jsx#L2004)).

**Undo atòmic**: `useDocumentHistory` coalesciona per ràfega de 500 ms
([`ftt/history.js:11`](../../frontend/src/pages/ftt/history.js#L11)). N insercions síncrones ja
són UN pas; les pàgines noves s'afegiran en **un sol `setPages`** perquè ho segueixin sent.

---

## BANC DE QA — estat real, verificat avui (tenant `fhort`)

| Model | Codi | `garment` a BM | PieceFitting | Sessió |
|---|---|---|---|---|
| **1379** | `BRW-FW26-0002` | `['', '02']` · 18 BM | pf=40, 90 línies, 5 talles, 2 prendes | sessió 155 **Oberta**, gate Pendent, **0 decisions** |
| **1380** | `QA-F1-GARMENT` | `['', '02']` · 2 BM | **cap** | — |

🚨 **No hi ha cap model amb fitting TANCAT i multi-peça.** 1379 és lectura-només (llei) i la
seva sessió ni tan sols està tancada; 1380 és **d'escriptura d'E2** (nota de concurrència).
→ **El banc de Q8 serà SINTÈTIC i propi** (model nou `QA-Q8-*` + sessió tancada + preses per
talla), i els tests unitaris dels constructors corren amb `node --test`, sense BD.

## Unitat i idioma — dues excepcions declarades

- **Unitat**: no existeix cap toggle *de document*; `useUnit()` és la llei d'unitat del
  **tenant** (CM|INCH), i és la que totes les taules ja fan servir. La capçalera de taula la
  DECLARA («Measurements in cm» / «in inches»).
- **i18n**: capçaleres de columna **sempre en anglès** (`i18n.getFixedT('en')`, el mateix
  mecanisme que el full descarregable fa servir per a les capes). Les claus s'afegeixen igualment
  a `ca`/`en`/`es` amb paritat: el gate es compleix, i qui les pinta demana la fixa `en`.
  **Excepció conscient, declarada aquí i al report.**
