# REPORT F2.2 · FRONTEND · matar els duplicats de domini — 🛑 STOP

**Data:** 08/08/2026 · **Commits:** 152 · 153 · 154 · **CAP PUSH** · HEAD `e515c124`

> **El titular:** el cens final NO dóna zero, i el motiu és que **el cens de la Fase 1 era curt**.
> Deia «~20 enumeracions en 17 fitxers»; el grep exhaustiu d'avui en treu **més del doble**, i
> **~25 no tenen cap endpoint d'on llegir-se**. F2.1 en va exposar quatre perquè l'ordre en
> nomenava quatre. Arribar a zero demana una segona ronda de backend.

---

## Fet

### 152 · La font (`utils/vocabulariDominiFont.js`)

Germà exacte de `diccionariMesuresFont.js`: cache de mòdul, promesa compartida, i **cap llista de
reserva** — si l'endpoint no contesta, `voc` és `null`, `error` és cert, i qui ho consumeix ho ha
de dir. `codisDe()` torna `null` i no `[]`, perquè `[]` afirmaria «aquesta enumeració és buida».

### 153 · `PhaseStepper.jsx` esborrat

Codi mort (ningú el muntava) que **empalmava tres vocabularis**: `'Nou'`/`'Tancat'` són
d'`ESTAT_CHOICES`, cinc eren fases de TASCA, i `'Tècnic'` **no existeix** (la real és
`'Dev. tècnic'`). Cap era `Model.FASE_CHOICES`. Se'n va amb ell el grup i18n `model_phases`
(8 claus × 3 idiomes), mirall de la invenció.

### 154 · Les capes surten del diccionari

Hi havia **dues** còpies: la constant `CAPES` i el mapa i18n `capa.<slug>` (6 literals × 3
idiomes). Les dues fora. `etiquetaCapa(slug, dicc, lang)` i `sufixIdentitat(fila, dicc, lang)`.
**Les 3 còpies de reserva** que l'ordre demanava matar (`EditableTable:169`,
`TaulaPOMsCataleg:76` i `:450`, totes amb `dicc?.capes?.length ? … : CAPES`) ara són
`dicc?.capes || []`: sense diccionari no s'ofereix cap capa.

7 consumidors adaptats; 3 no tenien diccionari i ara el demanen amb el hook — sense cap petició
extra, perquè la font memoritza a nivell de mòdul. **El paper segueix en anglès** (D-31.22): el
full de fitting demana `lang='en'` i l'editor `.ftt` l'idioma del DOCUMENT.

⚠️ **El build no ho hauria vist.** La primera passada va deixar `lang`/`dicc` en el component
equivocat de quatre fitxers: `npm run build` passava verd i a l'execució hauria petat amb
`ReferenceError`. Ho va caçar **`eslint` (`no-undef`)**. Aquí el control que compta és el lint.

---

## 🛑 CENS FINAL — no dóna zero, i aquí és per què

### (a) Domini amb endpoint viu → es poden matar ja

| Enumeració | Còpies | Endpoint |
|---|---|---|
| **Fases del model** | **7**: `Dashboard:35` · `DashboardGovPanel:15` · `InformesPanel:15` · `ActionsMenu:9` · `AddModelToGroupModal:16` · `FittingSessionList:14` · `ProjectGantt:28` | `/vocabulari/` → `fases_model` |
| **Fases de tasca** | 1: `TaskTree:24` | `/vocabulari/` → `fases_tasca` |
| **Règims** | 2: `SizeMapSetup:21` (4 valors) · `GraduacioSuperficie:85` (3) | `/vocabulari/` → `regims_graduacio` |
| **Targets · construccions · fits · grups** | **`components/grading/gradingAxes.js:13,29,36,49`** — un fitxer sencer de quatre enumeracions | `/targets/` · `/construction-types/` · `/fit-types/` · `/garment-groups/` (tots existien ja) |

`gradingAxes.js` **no era al cens de la Fase 1** i és el més gros: són exactament els quatre
vocabularis que les maquetes de size library i grading rules també dupliquen.

### (b) Domini SENSE endpoint → no es poden matar sense backend

Estats de comanda (`Orders:18`, `OrderDetail:21`) · d'oferta (`Quotes:21`) · d'albarà
(`DeliveryNotes:18`) · d'encàrrec (`WorkOrders:18,19`) · natures de producte (`Products:145`) ·
rols i capabilities (`UsersRoles:11,13`) · unitats i normes (`GeneralConfig:13,14`) ·
`BASE_UNITS` (`SizeMapSetup:20`) · règim fiscal i mètodes de pagament (`CustomerForm:7,8`) ·
estats de sessió de fitting (`FittingSessionList:15`, `FittingDetail:164`,
`FittingConvocatoriaSheet:69`) · veredictes (`fittingGridAdapter:168`, `FittingPrintSheet:31`) ·
nivells de proximitat (`EditableTable:1883`, `CascadeSelector:38`) · tipus de geometria
(`TechSheetEditor:54`).

**≈25 enumeracions.** Per a totes, la llei diu que la UI ho ha de dir i no oferir opcions —
però avui **són l'única font que hi ha**, i buidar-les deixaria pantalles sense poder filtrar
ni desar. **No les toco.**

### (c) No és domini (es queden, amb motiu)

Pestanyes i passos d'UI (`DASH_TABS`, `TABS`, `STEPS`, `GOV_TABS`, `BOARD_COLS`, `COLS`) ·
eines i àncores del canvas (`RECT_TOOLS`, `ANCORES_*`, `PATH_TOOLS`…) · **`KONVA_COL` i
`PALETTE`/`QUICK_COLORS`**, que són pintura de canvas i l'excepció ja registrada (Konva no
resol `var()`) · idiomes de la interfície (`SUPPORTED_LANGUAGES`, `DOC_LANGS`, `PDF_LANGS`) ·
dies de la setmana · `YEARS` (calculat) · claus de filtre i de query.

---

## 🛑 Dues coses que necessiten decisió teva

**1 · `EXCEPTION` no és un règim d'autoria.** `pom/services.py:177`: té «a single source:
`ModelGradingOverride`» — és una **petja que escriu el motor**, no una opció que un tècnic triï.
Dades vives: només `LINEAR` (1034) i `FIXED` (233). Si substitueixo els selects pel que dóna
l'endpoint, un tècnic podrà marcar una regla com a override sense ser-ho: **canvi de
comportament, no mort d'un duplicat**. ¿L'endpoint ha de marcar quins són autorables (p.ex. un
camp `autorable` per element), o els filtro per llista al client —cosa que tornaria a ser una
constant escrita?

**2 · Les ≈25 sense endpoint.** ¿Segona ronda de backend que les exposi (i llavors F2.2 es tanca
de debò), o s'accepta el cens amb aquestes marcades i es tanquen pantalla a pantalla?

## Verificació

| Control | Resultat |
|---|---|
| `npm run build` | ✅ verd als 3 commits |
| `eslint` | ✅ **1254 — idèntic a la línia base**, delta 0 (i és qui va caçar els 12 errors reals) |
| `node --test` | ✅ **218/218** · tests de `capaInstancia` reescrits contra un diccionari de prova |
| i18n | ✅ cap clau nova; **16 claus retirades** (`model_phases` ×8 + `capa.<slug>` ×6, × 3 idiomes) |

## 🛑 STOP

Fet el que es podia tancar sense decisió. Amb la resposta als dos punts, el bloc (a) —**11
còpies amb endpoint viu, `gradingAxes.js` inclòs**— cau seguit.
