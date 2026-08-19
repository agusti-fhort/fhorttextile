# REPORT · Les pantalles vives contra les maquetes aprovades

> **Data:** 2026-08-05 · branca `dev` de staging · **cap push** · **cap suite**.
> Cens complet a [`DIAGNOSI_UI_MAQUETES.md`](DIAGNOSI_UI_MAQUETES.md).

## 1 · Els commits

| # | Commit | Bloc | Fitxers |
|---|---|---|---|
| A | `97ca4520` | **Fase A** · el cens de divergència | `docs/diagnosis/DIAGNOSI_UI_MAQUETES.md` |
| B1 | `3195239e` | **M6** · el descart d'una fila en blanc es llegeix | `EditableTable.jsx` · `i18n/{ca,en,es}.json` |
| B2 | `6933fd66` | **M7b** · les dues portes que desen soles ho diuen | `EditableTable.jsx` · `i18n/{ca,en,es}.json` |
| B3 | `c1996460` | **M8+M9** · fila activa i animació de naixement | `EditableTable.jsx` · `index.css` |
| B4 | `0aa356c7` | **M11** · la capçalera del carril diu la talla | `EditableTable.jsx` · `i18n/{ca,en,es}.json` |

Tots quatre blocs viuen dins de `components/EditableTable/EditableTable.jsx` (i dos tokens +
un `@keyframes` a `index.css`). **Cap fitxer del fitting, cap del backend, cap dels que altres
trams han mogut avui.**

### Un candidat que no calia fer

**M4 · nomenclatura curta editable en or**: la maqueta la fixa i **la pantalla ja la tenia**
(`EditableTable.jsx` · `NomenInput`) — or, monospace, vora només en hover/focus, commit on blur.
El brief la llistava com a probable; el cens l'ha trobada feta i no s'hi ha tocat res.

## 2 · Verificació

**Regla del verd**, per commit: `npm run build` net als quatre.

**Checklist de pantalla** (obligatori, i un sol load no compta — lliçó del #310).
Passi nou a `scratchpad/qa_fase_b.py`: serveix `frontend/dist` **del disc** (el mateix bundle
que publica nginx) amb `taula-mesures` stubejat amb files reals — 1 informada i 2 en blanc, una
d'elles germana de folre — perquè el que es miri sigui la graella pintada i no una pantalla buida.

| Moment | Resultat |
|---|---|
| **CÀRREGA** | ✓ munta · ✓ graella pintada · ✓ M6 (2 marques) · ✓ M7 (recomptes) · ✓ M11 (etiqueta + cos ≥15 px) · ✓ M8 (fons `#fff`→`#fdf8ee`, vora `rgb(194,122,42)`) · ✓ M9 (`@keyframes ftt-neix` al bundle) · **consola 0 missatges** |
| **RECÀRREGA (F5)** | ✓ torna a muntar · ✓ els blocs sobreviuen · **consola 0 missatges** |
| **NAVEGACIÓ** Mesures→Resum→Mesures→Escalat→Mesures | ✓ pàgina viva · **consola 0 missatges** |
| **`prefers-reduced-motion: reduce`** | ✓ `animation-name: none` · **consola 0 missatges** |

**Als TRES idiomes** (`ca` · `en` · `es`): checklist complet en verd a cadascun. No és zel: la UI
de staging surt **en anglès** per defecte, i comprovar-ho només en català hauria validat un
bundle que ningú mira.

**Regressió:** `node --test src/utils/*.test.js` → **129/129**. Fum de muntatge de la casa
(`ops/qa/qa_mount_modelsheet.py`, models 164 i 165) → **verd**.

## 3 · SORPRESES

### 3.1 · 🔴 El veredicte del fitting ja es desa al backend, i el front el llença

**La sorpresa gran, i no és de maqueta.** El brief donava per fet que persistir el veredicte
demanava una migració. **No en demana cap: està tot fet des de `fd102c06`** (D-31.21).

| Peça | Estat | Àncora |
|---|---|---|
| Camp `decisio` (3 choices, `''` ≠ ACCEPTED) | ✅ | `backend/fhort/fitting/models.py:427-439` |
| Migració | ✅ | `fitting/migrations/0024_d3121_decisio_piecefittingline.py` |
| PATCH de cel·la l'accepta (mateixa porta que la nota) | ✅ | `fitting/serializers.py:206-217` |
| La graella el rep en obrir | ✅ | `fitting/serializers.py:350-351` |
| Guard: un REJECTED no sembra | ✅ | `fitting/views.py:654` |
| **El front l'usa** | ❌ | `CheckMeasureEditor.jsx:332-340` — estat local, cap PATCH |

**Efecte viu:** la modista decideix tota la graella, recarrega, i **perd tots els veredictes**.
La nota, que va per la mateixa porta, sí que sobreviu.

**Per què ningú ho havia vist:** `measureSources.jsx:75-80` encara diu
«*🚨 PENDENT DE BACKEND — … `PieceFittingLine` no té camp `decisio`*». És el text d'abans de
`fd102c06` i **ningú el va actualitzar**. `CheckMeasureEditor.jsx:325-327` el repeteix.

**Cost estimat: XS, només frontend, cap contracte** — sembrar de `line.decisio` a
`buildFittingRows` i fer que `onVeredicte` cridi `pieceFittingLines.update(lineId, { decisio })`.
**No s'ha fet:** el brief exclou explícitament tot el fitting de la Fase B. **Convé demà.**

### 3.2 · 🔴 Un comentari de 12 línies que nega el codi que encapçala

`EditableTable.jsx:398-409` jura, citant el QA del model 1302, que
«*LA GRADUACIÓ NO ES VEU AQUÍ (decisió d'Agus, 31/07)*»… i **just a sota la pinta**
(`:422-436`, `:623-662`). El comentari és de `4780945b` (que sí que la va treure) i
`ff23c7f4` la va tornar **poques hores després el mateix dia** sense actualitzar-lo. Els
`{( … )}` buits són la cicatriu de la condició `teRegles` esborrada.

**No s'ha tocat**, i és deliberat: la columna de Regla és el punt **D1** que ha de decidir
l'Agus (maqueta del 04/08 que no la porta, contra decisió seva del 31/07). Corregir el
comentari abans de la decisió seria escollir per ell.

### 3.3 · El fitting estava molt més fet del que el brief suposava

El brief demanava censar set blocs del fitting com si faltessin. **Cinc ja hi eren:** històric
paginat de dos en dos amb ‹ › i la columna de treball fixa, els tres veredictes amb les
dreceres `a`/`j`/`r`, la nota per línia, la instància dins del nom en negre, i el full PDF
**A4 apaïsat real** amb caselles AC/AD/RJ i llegenda (`FittingPrintSheet.jsx`, enllaçat des de
`SessionPanel.jsx:121`).

**Falten només tres**, i **cap toca contracte**: la persistència del veredicte (§3.1), la barra
de recomptes, i les germanes derivades amb folgança — per a les quals **el backend ja emet
`origen`** (`fitting/serializers.py:357`, amb el comentari «*la pantalla ja té tot el que cal
per etiquetar-ho*») i **el front no el llegeix**.

### 3.4 · La superfície viva del fitting no és la pàgina de fitting

Una sessió **viva** no es treballa a `FittingDetail`: es redirigeix a
`/models/:id?tab=Mesures&fitting_session=:id` (`FittingDetail.jsx:564-566`). El que queda
allà és **només el split de lectura** de sessions segellades. És la dissolució de l'Sprint Y, i
qui censi el fitting mirant `FittingDetail` censarà la pantalla equivocada.

### 3.5 · El vocabulari de capes de la maqueta v3 és erroni — i no s'ha copiat

`maqueta_fitting_v3.html:241-242` diu `Interlining / Binding / Knit / Reinforcement`.
**D-31.22 mana** i `utils/capaInstancia.js:9-13` ja ho deixa escrit: `entretela=Interfacing`,
`reforc=Underlining`, `fornitura=Trim`. **No és una divergència a corregir**, i convé que la
maqueta s'actualitzi perquè el proper cens no ho torni a obrir.

### 3.6 · La UI de staging surt en anglès

`i18n/index.js` detecta per `localStorage['fhort.lang']` (no `i18nextLng`) amb
`fallbackLng: 'ca'`, però el navegador de staging cau a `en`. Qualsevol QA de pantalla que
busqui literals catalans **falla per motius equivocats**; i `innerText` retorna el text **ja
transformat** per `text-transform: uppercase`. Les dues coses van costar una volta de fals
vermell i queden anotades al passi.

## 4 · El que NO s'ha fet, i per què

### Estructural — punt de parada del brief (documentat, no resolt)

| # | Bloc | Per què s'atura |
|---|---|---|
| **M1** | Píndoles d'instància per dimensió | **No existeix el diccionari d'instàncies.** La maqueta modela la instància com un **array** (un valor per dimensió `lat`/`st`); la BD la desa com **un slug compost**. `capaInstancia.js:22-25` ho diu: arriba amb C4-ins i la Montse. A més, el repartiment entre germanes és una regla de FAMÍLIA que avui no existeix. |
| **M2** | Modal `＋` de posició i combinacions | Mateix diccionari. |
| **M5** | Cercador amb sufixos «C.f» / «S.l» | Backend nou: `poms/cerca/` no resol capa/instància (`pom/wizard_views.py:114-148`). |
| **M5b** | Cercador agrupat per nivell (item/type/catàleg) | Mateix endpoint: no té noció de nivell. |

**Bonus del cens:** la maqueta genera el CODI amb sufixos automàtics (`L`/`R`/`RE`/`EX`), i la
llei viva és la contrària — `nom_fitxa` és text del tècnic i la invariant de BD
`instancia_exigeix_nom` obliga a nom quan hi ha instància. Adoptar els sufixos **canvia qui
bateja la mesura**: decisió, no implementació.

### Fora d'abast per ordre del brief

Tot el fitting (§3.1 i §3.3), les píndoles, el modal `＋`, la germana de capa —**inclòs el fons
propi de les files de capa no-Exterior**, que és XS però pertany a aquell bullet— i el cercador.

### Deixat expressament, i anotat

- **Vores esquerra/dreta de la columna de valor** (`td.valcell` de la maqueta): demanarien tocar
  també les cel·les del cos, i això és un altre focus (B4 ho diu al missatge).
- **Moure la barra d'estat a peu de finestra** (`position: fixed` a la maqueta; avui és una línia
  sota la taula): és **D5**, una decisió de l'Agus. La Fase B només hi ha afegit el flaix de
  desat, sense moure-la.
- **Tecla `L`** per a la germana de capa: XS i només frontend, però és del bullet exclòs.

## 5 · Què decideix l'Agus

Detall a `DIAGNOSI_UI_MAQUETES.md` §5. En una línia cadascun:

1. **D1 · La columna de Regla de graduació hi és o no hi és** — maqueta del 04/08 sense el bloc
   contra decisió seva del 31/07 (`ff23c7f4`). Mig ample de pantalla en depèn, i també si el
   comentari ranci de §3.2 s'esmena o s'esborra amb el bloc.
2. **D2 · El model d'instància** — array de dimensions (maqueta) o slug compost (BD), i **qui
   bateja** una germana: el tècnic o el sufix automàtic. Bloqueja M1 i M2, que és el que es veu
   demà amb la Montse.
3. **D3 · El cercador per nivells i sufixos** — cal confirmar la taxonomia abans d'escriure
   l'endpoint.
4. **D4 · La folgança de les germanes derivades** — ¿diferencial viu o valor declarat? La
   maqueta el cabla a `2.0` i no ho diu.
5. **D5 · La barra d'estat** — fixa a peu de finestra (maqueta) o línia sota la taula (viva).
6. **D6 · Prioritzar el veredicte del fitting** (§3.1): no és disseny, és un XS amb tot el
   backend fet que la gent està perdent avui.

---

**Cap push. Cap suite. `git add` selectiu a tots els commits.**
