# F4-QUATER · Presentació unificada dels breaks a totes les superfícies de lectura

**Data:** 21/08/2026 · **Branca:** `dev` (staging) · **Commits:** 5, **cap push**
**Abast:** UI-only. El motor no es toca, cap porta, cap migració, cap camp nou de BD.
**Gate:** `ops/qa/banc_paritat_1383.py` (3 blocs) abans i després.

> **Cap cel·la moguda, cap hash mogut.** A=105 · B=525 · C=4, `HASH JOC` i
> `HASH RESIDENTS` **idèntics** a banda i banda — i el de residents és el
> `50982bbe…1f08` que l'ordre declarava vigent. Era el que havia de passar: això és
> dibuix, i el banc ho certifica.

---

## 1 · PAS 0 — El cens de pintors

Grep de `delta_break`/`talla_break`/`increment_break` i de les claus i18n de break sobre
tot `frontend/src`. Deu fitxers en parlen; **cinc** en PINTEN en lectura.

| | Superfície | On | Com pintava | Veredicte |
|---|---|---|---|---|
| ① | **Mesures-consulta** | `EditableTable.jsx` `COLS_GRADING` | 2 col. (96+96). Amb intervals: la del Δ **en blanc** i la de la TALLA amb `S→L +3 +N` | **SUBSTITUÏDA** |
| ② | **Escalat** (Presa + Decisió talla base) | `fittingGridAdapter.jsx` `escalatRuleLeadCols` | 2 col. (54+56), mateix apany però amb una gramàtica DIFERENT | **SUBSTITUÏDA** |
| ③ | **fitxa Q8b Grading** | `taulesQ8.resumBreakQ8` + `TechSheetEditor` | 2 col. (14+18 mm), el tram partit entre etiqueta i Δ — una TERCERA gramàtica | **FOSA → 1** |
| ④ | **Resum de propagació** (wizard Size Map) | `SizeMapSetup.jsx:840` | frase `+2 · +3 des de M`, **cega als intervals** | **SUBSTITUÏDA** |
| ⑤ | **Etiqueta compacta de regla** | `etiquetaRegla` ← Escalat (lead) i check | ja deia intervals, però amb gramàtica pròpia i **sense la regla del silenci** | **UNIFICADA** |

I el que el cens diu que **no** es toca, amb el motiu:

- **`CheckMeasureEditor` (autoria)** — els seus `<select>` no PINTEN, TRIEN una talla sola,
  i mentre escriguin `talla_break_label` la volta de document hi ha de ser. És el deute ②.
  El que sí que hi entra és la seva **etiqueta** de lectura (⑤) i un forat (§4).
- **`SizeSetDetail.jsx:314`** — pantalla morta, poda pendent. No tocada.
- **`RuleSetPicker.jsx:141`** — només COMPTA regles amb break (`with_break`); no pinta cap
  valor. No és un pintor.
- **`GraduacioSuperficie` / `JocsDeRegles`** — autoria, ja unificades per F4-BIS.

---

## 2 · La regla única, i on viu

`gradingRegime.fraseBreaks(rule, run, {delta, max})` → **`M→XL +3`**, múltiples amb ` · `.
Va al costat d'`intervalsVisibles`, que ja era qui sabia llegir les dues formes de relleu i
qui porta la **regla del silenci** (F4-BIS). Que el silenci visqui en UN sol node és el que
fa que les tres captures d'Agus callin alhora.

**UNA SOLA IMPLEMENTACIÓ, i el bessó de la fitxa és DECLARAT:** `fraseBreakQ8` no
reimplementa res — hi posa la unitat de la fitxa i el pressupost de mm sobre el formatador
comú. Cap tercera transcripció a mà.

### 2.1 · L'off-by-one de document mor de les lectures

Amb rang explícit inclusiu es pinta **convenció de MOTOR tal qual**. Un rang amb els dos
extrems dits no és ambigu; traduir-ne l'inici sense el final —o els dos, que voldria dir
sortir del run per dalt— donaria una etiqueta que no casa ni amb la BD ni amb el picker.

**Conseqüència visible:** el break llegat de les 21 regles vives del banc 1383 passa de
dir-se `trencament S +3` (document) a `M→XL +3` (motor). **La dada no s'ha mogut** — el
motor sempre ha graduat `M..XL`; el que hi havia era una etiqueta desplaçada una posició a
posta, i ara el rang la fa innecessària.

`breakConvention.js` queda amb **dos lectors** d'`aDocument`: el `<select>` del break llegat
(deute ②) i `SizeSetDetail` (morta). **Candidat a retirar-lo sencer** el dia que caigui el
primer — 🚩 anotat, **NO fet**: retirar-lo avui deixaria l'editor del check sense com desar
el que ja té a la BD.

### 2.2 · On divergeixen les superfícies, i per què és a posta

`max` **no és una opinió, és un pressupost d'amplada**:

| Superfície | Ample | `max` | Tres trams es veuen com |
|---|---|---|---|
| Consulta | 200 px | — | `XS→S +0.5 · M→L +1 · XL→XL +1.5` |
| Escalat | 110 px (= 54+56) | 1 | `XS→S +0,5 +2`, sencer al `title` |
| Fitxa Q8b | 26 mm | 1 | `XS→XS +3.0 +1`, corba sencera a les columnes de talla |

La fusió de l'Escalat **no pren ni un píxel al carril de talles**. I on hi ha `max` hi ha
tooltip: una dada retallada sense on anar-la a veure seria una dada perduda.

---

## 3 · El pressupost de mm de la fitxa (l'encàrrec de T3)

`Break` (14) + `B.Size` (18) = 32 → **«Breaks» 26 mm**. **Allibera 6 mm.**

Els 26 són **mesurats**: a 9 pt monoespaiat (`charW = fontPx·0.6`, `T_PAD = 2 mm`) la cel·la
en cap **11 caràcters**. `M→XL +3.0` (9) hi entra d'una línia; `2XL→3XL +3.0` (12) parteix
en dues amb `wrap` i la fila creix — al paper que va al fabricant, res no es talla en silenci.

**Què compra:** el repartiment en bandes paga 14 mm per talla.

| `codi`/`nom` | abans | ara |
|---|---|---|
| als mínims (14/34) | 10 talles/banda | **11** |
| corpus ample (20/44) | 9 talles/banda | 9 (el residu se l'endú el nom) |

**⚠️ L'A4 VERTICAL NO ES RECUPERA, i per 2 mm.** `q8_taules_fitxa.mjs` mesura la Q8b de 5
talles: **198 → 192 mm**, i el sostre de l'A4P és 190. La recuperació que T3 volia queda a
**dos mil·límetres**. Es podrien guanyar posant la columna a **24 mm** (→ 190 exactes), però
llavors la cel·la només en cap 10 caràcters i tota frase d'11 (`XL→3XL +3.0`, gens rara)
partiria en dues línies. **No ho he fet: és una tria de producte, no de maquetació** —
canviar-ho és una línia (`width: 26` a `TechSheetEditor:5608` i l'aritmètica de bandes de
`:5591`). 🚩 **Decisió d'Agus.**

---

## 4 · 🚨 Un forat de lectura que no era d'aquest sprint

`reglaPerPom` (`CheckMeasureEditor:610`) és un **CLON** de la regla i copia camp a camp. El
tram F va afegir `breaks` a la fila **i no aquí**. Conseqüència: una regla amb intervals
explícits arribava a Mesures-consulta amb `breaks: undefined` i la pantalla la pintava com
si no trenqués enlloc — **mentre la corba de talles del costat sí que creixia amb els trams**.
La pantalla es contradeia a si mateixa.

Cap gate ho veia: el build compila, el banc de motor no mira dibuixos, i la columna vella
tenia codi per a intervals que **mai s'executava** en aquesta superfície.

És la llei que ja havia cremat abans: **un camp nou de la regla vol línia pròpia a cada
clon.** Reparat amb el tram.

---

## 5 · La QA

### 5.1 · Pantalla — `ops/qa/qa_f4quater_lectura.py` · **24/24** ✅

Patró de `qa_f4bis_columna_breaks`: bundle **REAL** de `frontend/dist` i només el payload
stubejat (la QA de navegador contra staging vol un JWT que l'agent no pot emetre).

Mesura, a la consulta **i** a l'Escalat: que les dues columnes velles han marxat · que el
break llegat diu `M→XL +3` · **que l'inici NO s'ha desplaçat a S** · la regla del silenci a
les dues formes (FIXED amb residu, i llegat = Δ general) · el Δ negatiu amb signe · i la
divergència deliberada de `max` amb el tooltip sencer.

Captures: `ops/qa/captures/f4quater_{1_mesures_consulta,2_escalat}.png`.

**Dues coses que la primera correguda va ensenyar**, escrites al fum perquè no es tornin a
pagar:

- **La consulta NO es dibuixa amb `taula-mesures`.** Les files surten de `base-stages` i la
  regla se'ls ajunta per `(pom, garment)`. Stubejant només `taula-mesures` sortia la
  capçalera i **cap fila** — i les cinc proves de capçalera haurien donat **verd** sense
  haver mesurat una sola cel·la.
- **L'índex de la columna es busca dins la FILA de `thead` que la conté.** Amb els `th` en
  pla, la fila de grups de l'Escalat el desplaçava tres i la prova mesurava una columna de
  mesures. No petava com un error: deia «44.0», que és símptoma d'índex, no de dibuix.

### 5.2 · Fitxa — `ops/qa/q8_taules_fitxa.mjs` · **29** ✅ (26 + 3)

La fitxa no es pot muntar des de node (Konva + React), però **sí la juntura**, que és on això
es pot trencar en silenci: `filesGrading` → `fraseBreakQ8` sobre la sortida REAL del
constructor amb el payload real del servidor. Si algú desfés el rebateig de camps, la fitxa
sortiria sense cap relleu i **tot seguiria verd**; ara no.

**Export PDF == live, per construcció:** els dos únics punts que pinten una taula
(`:1622` llenç viu i `:2115` export) criden `buildTableCellPrimitives(obj)` sobre el
**mateix objecte**. El que aquest tram canvia són les `columns`/`rows` que hi entren.

### 5.3 · Els controls

| Control | Resultat |
|---|---|
| `banc_paritat_1383.py` abans i després | ✅ A=105 · B=525 · C=4 · **els dos hashos idèntics** |
| `node --test src/utils/*.test.js` | **428/428** (30 al banc de `gradingRegime`, 25 al de `taulesQ8`) |
| `npx eslint src` | **0 errors** (271 warnings preexistents) |
| `npm run build` | net |
| `manage.py check` | net (backend no tocat) |
| i18n ca·en·es | **paritat exacta**, 0 claus desaparellades |

---

## 6 · Els 5 commits (cap push)

| | |
|---|---|
| `c43a9611` | el formatador ÚNIC de la frase d'un relleu |
| `1cc87ea0` | les etiquetes de la columna «Breaks» de lectura (ca·en·es) |
| `703c1897` | la consulta, l'Escalat i el resum diuen el relleu amb UNA columna |
| `12c92a0a` | la fitxa fon `Break` + `B.Size` en «Breaks» i recupera 6 mm |
| `e0569761` | la QA de les tres superfícies |

⚠️ **`npm run build` ÉS DESPLEGAR**: staging serveix `frontend/dist`. El que hi ha en viu a
`staging.fhorttextile.tech` és ja aquesta presentació. El codi **no** està pushat.

---

## 7 · El que queda obert

- 🚩 **La decisió dels 24 mm** (§3): a dos mil·límetres de l'A4 vertical de la Q8b, al preu
  que les frases d'11 caràcters parteixin en dues línies. **D'Agus.**
- 🚩 **Deute ②** — l'AUTORIA del break llegat a `CheckMeasureEditor` segueix en convenció de
  document. Mentre hi sigui, la mateixa pantalla té les dues convencions: lectura en motor,
  autoria en document. **És per què el deute existeix, no un descuit.**
- 🚩 **`breakConvention.js` candidat a retirar-se sencer** quan caigui el deute ② (§2.1).
- 🚩 **Deu claus i18n orfes** — `editable_table.col.{delta,talla}_break`,
  `measuregrid.regla_{delta,talla}_break`, `tech_sheet.q8_col_break{,_size}`,
  `size_map_g_break_from`, `fitting.grid.break`, i les ja mortes
  `editable_table.col.break_{delta,size}`. No retirades: no aporta res funcional i eixampla
  la finestra de xoc amb les sessions concurrents sobre tres fitxers compartits.
- **`SizeSetDetail`** segueix pintant el break vell en convenció de document. És pantalla
  morta i la poda ja estava pendent; **quan es podi, no cal migrar-la**.
