# DIAGNOSI — Etiquetes de veredicte (ACCEPTED/ADJUSTED/REJECTED → OK/ADJUSTED/NO OK, FOLLOW SPEC) i capçalera REAL → SAMPLE

Data: 2026-09-23 · **Patró A (READ-ONLY)** · staging (`/var/www/ftt-staging`), branca `dev`, HEAD `db3207cc` (= `origin/dev`, cap pull necessari).
Abast: inventari exhaustiu de dos canvis d'etiqueta proposats (CANVI 1: veredicte de mesura; CANVI 2: capçalera de columna REAL→SAMPLE), amb cens de BD i amplades mesurades contra el codi real (no estimades).
Convenció: `fitxer:línia` + `"NO EXISTEIX" = confirmat absent al codi (no especulat)`.

---

## Resum executiu

1. **El veredicte viu en UN sol lloc de domini**: `PieceFittingLine.decisio` (`backend/fhort/fitting/models.py:469-481`), taula `fhort.fitting_piecefittingline`, columna `decisio`. Cens a staging: **`''` (sense decidir)=850 · ADJUSTED=11 · ACCEPTED=3 · REJECTED=0** (14 files decidides en total — mida trivial si mai calgués migrar, però **cap migració és necessària** per aquest canvi).
2. **Hi ha DOS falsos amics amb el mateix nom que NO s'han de tocar**: `SizeCheckLine.decisio` (`backend/fhort/models_app/models.py:1537`, vocabulari `tolerancia_acceptada`/`valor_descartat`, domini diferent) i `AbstractDocument.STATUS_CHOICES` de `commerce` (`backend/fhort/commerce/models_base.py:31-36`, ACCEPTED/REJECTED sense ADJUSTED, domini de pressupostos comercials).
3. **🚨 TROBALLA CRÍTICA (CANVI 1):** la premissa "canviar NOMÉS les etiquetes (i18n+PDF) i deixar els valors a BD/API" **no es pot aplicar de manera uniforme**, perquè en com a mínim 4 llocs el codi cru (`ACCEPTED`/`ADJUSTED`/`REJECTED`) **ÉS el text que es pinta a l'usuari**, per decisió documentada explícitament al codi (D-31.21: "dada de domini, com LINEAR/STEP; traduir-los a pantalla i no al paper faria que les dues superfícies parlessin diferent"). Canviar l'etiqueta només als llocs que passen per `t()` deixaria l'aplicació amb **dos vocabularis simultanis pel mateix concepte** (veure Bloc 1.3).
4. **🚨 TROBALLA CRÍTICA (CANVI 2):** ja hi ha un precedent EXACTE i mesurat al propi codi (comentari "M1", `TechSheetEditor.jsx:5720-5723`) d'aquest mateix desbordament: la paraula **"ACTUAL" (6 caràcters) ja va trencar a dues línies** a la columna de 13 mm on avui hi cap "REAL" (4 caràcters), i es va revertir. **"SAMPLE" també té 6 caràcters** i la família és monoespaiada (IBM Plex Mono) — la matemàtica del propi renderer (no una estimació) diu que **també trencaria**. Detall numèric al Bloc 2.2.
5. La "PDF de la fitxa (reportlab)" que demanava el brief **NO EXISTEIX**: la fitxa tècnica NO es genera amb reportlab. Es genera al navegador amb **Konva (canvas) + `pdf-lib`** (`TechSheetEditor.jsx`), i el mateix renderer serveix la pantalla i l'exportació PDF ("paritat pantalla=PDF es manté per construcció", comentari `TechSheetEditor.jsx:235-240`). reportlab només s'usa per a factures/albarans (`commerce/pdf_service.py`, `backoffice/invoice_pdf.py`) — cap dels dos toca el veredicte ni "REAL".
6. Excel/CSV/DXF/RUL: **NO EXISTEIX** cap exportació que toqui `decisio`/ACCEPTED/ADJUSTED/REJECTED ni la capçalera REAL. Els mòduls amb `openpyxl` són d'importació de catàlegs; els de `ezdxf`/`.rul` són del motor de patrons (zona intocable, CLAUDE.md), domini separat.
7. La capçalera "REAL" **no és un literal cablejat**: és la clau i18n `tech_sheet.q8_col_actual`, que —curiosament— val **"Real" en els TRES idiomes** (ca/en/es), sempre forçada a anglès (`tEn()`) perquè la taula viatja al fabricant. Hi ha una **inconsistència de nomenclatura ja existent** amb dues altres claus germanes del mateix concepte (`sizecheck.col_real`, `comprovacio.col_real`) que en anglès ja diuen **"Actual"**, no "Real" (Bloc 2.3/Q6).

---

## BLOC 1 · CANVI 1 — ACCEPTED/ADJUSTED/REJECTED → OK/ADJUSTED/NO OK, FOLLOW SPEC

### 1.1 · El camp de domini

- `PieceFittingLine.decisio` — `backend/fhort/fitting/models.py:469-481`. Constants `DECISIO_ACCEPTED='ACCEPTED'` (:469), `DECISIO_ADJUSTED='ADJUSTED'` (:470), `DECISIO_REJECTED='REJECTED'` (:471); `DECISIO_CHOICES` amb etiquetes EN CATALÀ (:472-476, p.ex. `'Acceptada — la mesura real es dona per bona'`); camp `decisio = CharField(max_length=10, choices=..., blank=True, default='', db_index=True)` (:477-481). `''` és explícitament "sense decidir" i **no** és `ACCEPTED` (comentari :465-468) — invariant que cap canvi d'etiquetes pot trencar.
- Migració `backend/fhort/fitting/migrations/0024_d3121_decisio_piecefittingline.py:16` porta els tres choices literals "cuits" (`AddField`). Si mai es canviessin els VALORS (no és el pla), caldria una migració nova; canviar només les etiquetes de `DECISIO_CHOICES` (les catalanes, internes) **no** exigeix migració perquè Django no persisteix el `label` a BD, només el `value`.
- BD staging: `fhort.fitting_piecefittingline.decisio` és `varchar(10) NOT NULL` amb índex `fitting_piecefittingline_decisio_2a8a207a`. **Cens (2026-09-23, `psql -p 5433 -d ftt_staging`):**

  | `decisio` | files |
  |---|---|
  | `''` (sense decidir) | 850 |
  | `ADJUSTED` | 11 |
  | `ACCEPTED` | 3 |
  | `REJECTED` | 0 |

  Cap altra taula de la BD té una columna `verdict`/`veredicte` (`information_schema.columns` filtrat per `column_name ILIKE '%verdict%'` → 0 files). El veredicte de mesura viu en un únic lloc.

### 1.2 · Inventari BACKEND — `fitxer:línia · text · VALOR/ETIQUETA · idioma · context`

| fitxer:línia | text | tipus | idioma | context |
|---|---|---|---|---|
| `fitting/models.py:469-471` | `DECISIO_ACCEPTED/ADJUSTED/REJECTED = '...'` | VALOR (BD) | en (constant) | constants del choice |
| `fitting/models.py:473-475` | `DECISIO_CHOICES` (codi + etiqueta llarga) | VALOR+ETIQUETA | ca (etiqueta) | `choices=` del camp; l'etiqueta és NOMÉS català, no es fa servir enlloc del front (veure 1.3) |
| `fitting/models.py:479-480` | help_text del camp | comentari dev | ca | documentació, no runtime |
| `fitting/migrations/0024_d3121_decisio_piecefittingline.py:16` | choices baked-in | VALOR (BD) | ca (etiquetes) | migració aplicada |
| `fitting/serializers.py:215-216` | `fields=[...,'decisio']` (`PieceFittingLineSerializer`) | VALOR (API) | n/a | PATCH d'autosave de cel·la |
| `fitting/serializers.py:396` | `'decisio': line.decisio` (`PieceFittingGridSerializer`) | VALOR (API) | n/a | graella sencera |
| `fitting/repas_views.py:451,467,489` | clau `'veredicte'` = `l.decisio or ''` | VALOR (API), renombrat | n/a | pantalla "Repàs" |
| `fitting/escalat_presa_views.py:76` | clau `'estat'` = `linia.decisio or ''` | VALOR (API), renombrat | n/a | pantalla "Escalat/presa" |
| `models_app/vocabulari_views.py:199-201` | `'veredictes_fitting': _llista(PieceFittingLine.DECISIO_CHOICES)` | VALOR+ETIQUETA (API) | ca (etiqueta, no usada pel front) | endpoint `/vocabulari/`; **no** hi posa el buit (a posta) |
| `fitting/views.py:691` | `if line.decisio == DECISIO_REJECTED` | VALOR (BD) | n/a | lògica de negoci |
| `fitting/services.py:738` | `.exclude(decisio=DECISIO_REJECTED)` | VALOR (BD) | n/a | "una REJECTED es desa i es veu, però no sembra" |
| `fitting/esdeveniments.py:18` | comentari | — | ca | documentació |
| 9 fitxers de test (`test_d3121_veredicte.py`, `test_e1_cicle_complet.py`, `test_e1_guard_partit.py`, `test_e1_presa_escalat.py`, `test_e3_cicle_mesurar_set.py`, `test_e3_presa_tancada.py`, `test_repas.py`, `test_q8_banc_taules_fitxa.py`, `models_app/test_vocabulari_marques.py:133`) | `decisio='ACCEPTED'` etc., i `assertEqual(codis, ['ACCEPTED','ADJUSTED','REJECTED'])` | VALOR (BD, testejat) | en (literal)/ca (comentaris) | confirmen per test que són VALORS estables, no etiquetes |

**PDF (reportlab):** `NO EXISTEIX`. Fitxers amb `reportlab` al backend (`backoffice/invoice_pdf.py`, `accounts/logo.py`, `accounts/capabilities.py`, `commerce/pdf_service.py`, `commerce/views.py`, `pom/s2_views.py`) — cap conté `decisio`/`veredicte`/ACCEPTED/ADJUSTED/REJECTED. **El full imprès de fitting NO es genera amb reportlab**; és 100% frontend (Bloc 1.3).
**Excel/CSV/DXF/RUL:** `NO EXISTEIX` cap referència en cap dels mòduls d'exportació/importació revisats.
**Missatges d'error/validació:** `NO EXISTEIX` cap missatge d'usuari (excepcions, 4xx) que citi els tres valors literalment; els guards (`SEALED_SESSION_DETAIL` etc.) són genèrics.

### 1.3 · Inventari FRONTEND — `fitxer:línia · text/clau · tipus · idioma · component`

**i18n (`frontend/src/i18n/{ca,en,es}.json`, línies 2434-2436):**

| clau | ca | en | es | ús |
|---|---|---|---|---|
| `fitting.grid.verdicte.accepted` | "Acceptada — la mesura real es dona per bona" | "Accepted — the measured value stands" | "Aceptada — la medida real se da por buena" | `title`/`aria-label` del botó (NO text visible) |
| `fitting.grid.verdicte.adjusted` | "Ajustada — s'ha rectificat i val el valor rectificat" | "Adjusted — rectified; the rectified value stands" | "Ajustada — se ha rectificado y vale el valor rectificado" | ídem |
| `fitting.grid.verdicte.rejected` | "Rebutjada — la presa no val: no sembra res" | "Rejected — the reading does not stand: it seeds nothing" | "Rechazada — la toma no vale: no siembra nada" | ídem |
| `fitting.grid.col_verdict` | "Veredicte" | "Verdict" | "Veredicto" | capçalera de columna (SÍ traduïda) — no és el text del valor |

`frontend-backoffice/src/i18n.js` — confirmat sense cap contingut de fitting/mesures (només `login.*`).

**🚨 Llocs on el CODI CRU es pinta com a TEXT VISIBLE (sense passar per `t()`), per disseny documentat:**

| fitxer:línia | codi | tipus | idioma | component |
|---|---|---|---|---|
| `components/model/fittingGridAdapter.jsx:191-194` | `VERDICTE_TO = {ACCEPTED:{...}, ADJUSTED:{...}, REJECTED:{...}}` | mapa de color (no text) | — | crom, indexat pel codi |
| `components/model/fittingGridAdapter.jsx:236` | `>{v}</button>` | **LITERAL, el propi codi** | cap (sempre anglès/codi) | `VerdicteCell` — els 3 botons A/J/R de la graella de fitting. El `title`/`aria-label` (:222-223) SÍ passen per `t()`, però el text del botó no |
| `components/model/ComprovacioPanel.jsx:255` | `{p.veredicte \|\| '—'}` | **LITERAL, sense `t()` ni tooltip** | cap | pantalla "Comprovació" |
| `components/model/CheckMeasureEditor.jsx:391,416` | `RECOMPTE_COL={ACCEPTED:...}` + `{clau} <b>{n[clau]}</b>` | **LITERAL** | cap | `RecomptesFitting` — recompte per veredicte al peu de la graella |
| `pages/TechSheetEditor.jsx:5541,5549` | `label: tEn('tech_sheet.q8_col_verdict')` (capçalera, SÍ traduïda però forçada a EN) + `f.veredicte \|\| ''` (valor, **cru**) | capçalera=i18n forçat EN / valor=LITERAL | capçalera: en fix · valor: cap | taula `q8_fitting` — la que viatja impresa/exportada cap al fabricant. Comentari explícit :5547: *"no es tradueixen ni s'abrevien aquí"* |
| `utils/taulaPresaPerTalla.js:24-28` | constants `ACCEPTED/ADJUSTED/REJECTED` | VALOR intern | — | comentari: "DADA DE DOMINI: no es tradueixen mai" |
| `utils/taulesQ8.js:109,143,172` | `veredicte: v.estat` | propagació del codi cru | — | banc de dades de la taula Q8 |

Justificació al codi (repetida en 3 llocs diferents, backend i frontend): `fitting/models.py:458-463`, `models_app/vocabulari_views.py:169`, `fitting/repas_views.py:465-467`, `fittingGridAdapter.jsx:178-179`, `ComprovacioPanel.jsx:250-253` — tots citen **la mateixa raó**: el veredicte és "dada de domini" com LINEAR/STEP, ha de coincidir literalment entre pantalla i full imprès i el que es diu en veu alta a la sala.

**FittingPrintSheet.jsx — matís important:** aquest full (A4 apaïsat, imprès per omplir A MÀ) **NO pinta el valor de `decisio`**. Té tres caselles fixes `CASELLES = ['AC','AD','RJ']` (:44) que la modista marca amb bolígraf — són abreviatures FIXES independents del valor de BD, no una representació d'una fila ja decidida. No és, doncs, un lloc on canviar l'etiqueta d'`ACCEPTED` afecti res: la sigla ve d'una constant pròpia, no d'`i18n` ni del codi de BD.

NORMA_LAYOUT §7 ja documenta i anticipa aquest patró: *"El color PLE el porta el RESULTAT (text «Accepted/Adjusted/Rejected» + el número...)"* — la norma sap que el text del control és el codi en anglès sencer, no una abreviatura ni una etiqueta traduïda.

### 1.4 · Resposta Q2 — recomanació i mateixa cadena etiqueta=valor

**La recomanació "canviar només l'etiqueta (i18n+PDF), deixar el valor a BD/API intacte" és aplicable NOMÉS als 2 llocs que ja passen per `t()` com a text visible: cap trobat** (avui `col_verdict`/tooltips ja són traduïts, però no porten el text ACCEPTED/ADJUSTED/REJECTED en si — són metadades del control). **Per als 4+ llocs on el valor cru ÉS el text visible (1.3), la recomanació topa amb una decisió de disseny explícita i documentada (D-31.21) que caldria trencar conscientment**, no una simple substitució d'etiqueta. Si es fa el canvi només on hi ha `t()` disponible i es deixa la resta intacta, l'aplicació acabaria amb **dos vocabularis pel mateix concepte** segons la pantalla: "OK/NO OK, FOLLOW SPEC" en uns llocs i "ACCEPTED/REJECTED" en d'altres (botons de la graella, Comprovació, recompte, taula impresa). Això és exactament el tipus de trencament que el propi codi diu que volia evitar ("que les dues superfícies no parlin diferent") — ara séria "que les pantalles no parlin diferent entre elles".

**Sí, hi ha llocs on l'etiqueta i el valor són la mateixa cadena** (Bloc 1.3: `VerdicteCell`, `ComprovacioPanel`, `RecomptesFitting`, taula `q8_fitting`): allà caldria decidir explícitament si es trenca la paritat pantalla=paper (introduint per primer cop una traducció visible en aquests 4 llocs) o si es manté el codi cru mentre la resta de l'app parla amb l'etiqueta nova — decisió d'Agus/CTO, no tècnica.

**Cens** (repetit del Bloc 1.1 per completesa de Q2): `''`=850 · ADJUSTED=11 · ACCEPTED=3 · REJECTED=0.

### 1.5 · Resposta Q3 — amplada de "NO OK, FOLLOW SPEC" (19 car.) vs "REJECTED" (8 car.)

Mesurat contra el layout real de cada component (no CSS estimat):

- **`VerdicteCell` (`fittingGridAdapter.jsx:211-237`)** — grup de 3 botons `inline-flex` **sense amplada fixa ni `overflow:hidden`**; cada botó té `padding:'4px 9px'` i creix amb el contingut. **No hi ha desbordament/clipping** — el grup simplement es faria molt més ample (de ~3 sigles de 8-9 car. a un text de 19 car.), trencant l'estètica compacta de toggle que documenta NORMA_LAYOUT §7 ("botons neutres... el color el porta el resultat").
- **`ComprovacioPanel.jsx:255`** — `<td>` amb estil `tdS` (`ComprovacioPanel.jsx:46`), que **no porta `whiteSpace:nowrap`** (a diferència de `tdNum`, línia 48) → el text embolicaria (wrap) dins la cel·la sense trencar el layout, només faria la fila més alta si calgués.
- **`RecomptesFitting` (`CheckMeasureEditor.jsx:407-424`)** — `<span>` dins un `flex-wrap` lliure: creix, no desborda.
- **🔴 Taula impresa `q8_fitting` (`TechSheetEditor.jsx:5527-5551`, Konva)** — AQUÍ SÍ hi ha amplada fixa i wrap per caràcters, mesurat exactament (mateixa font monoespaiada IBM Plex Mono, mateixa matemàtica que el Bloc 2.2): columna `verdict` width=**22mm** → `cw=52.8px`, `hdrCharW=4.62px` (fontSize 9, capçalera fina 8pt) → **9 caràcters per línia**. "REJECTED" (8 car.) hi cap just; "NO OK, FOLLOW SPEC" (19 car., amb espais) necessitaria **3 línies** i inflaria l'alçada de capçalera de TOTA la taula (14 columnes en depenen). **Avui aquesta columna pinta el codi cru per disseny (1.3), així que aquest desbordament NOMÉS es materialitzaria si el canvi d'etiqueta s'apliqués també aquí** — cosa que el propi comentari del codi (`:5547`) diu explícitament que no s'ha de fer.

**Conclusió Q3:** cap lloc actual trenca (clip/tall) amb el text nou perquè cap contenidor de pantalla és d'amplada fixa per aquest control; el que trencaria és l'ESTÈTICA (toggle compacte → botó llarg) i, únicament si es decidís traduir també la taula impresa, l'ALÇADA DE CAPÇALERA d'aquesta (desbordament real, mesurat: 3 línies enlloc d'1).

---

## BLOC 2 · CANVI 2 — capçalera REAL → SAMPLE

### 2.1 · Resposta Q4 — on es pinta "REAL" com a capçalera

| fitxer:línia | clau/literal | ca | en | es | és clau i18n? |
|---|---|---|---|---|---|
| `pages/TechSheetEditor.jsx:5539` | `tEn('tech_sheet.q8_col_actual')`, taula `q8_fitting` (width 18mm) | — | "Real" (forçat) | — | clau i18n, però `tEn()` força SEMPRE anglès independentment de l'idioma actiu de l'usuari |
| `pages/TechSheetEditor.jsx:5724` | mateixa clau, taula `q8_size_set` (width 13mm) | — | "Real" (forçat) | — | ídem — mateixa clau, dues taules |
| `i18n/{ca,en,es}.json:3319` | `tech_sheet.q8_col_actual` | "Real" | "Real" | "Real" | **valor idèntic als 3 idiomes** (l'anglès no es diferencia perquè aquesta taula sempre es renderitza en anglès, sigui quin sigui l'idioma de qui l'obre — és la mateixa convenció que les capes del full de fitting, D-31.22) |

**Aquesta és la capçalera que descriu el brief**: viu a la fitxa tècnica (Konva), a les DUES taules Q8 que en depenen (`q8_fitting` i `q8_size_set`), i és EL MATEIX render tant a pantalla (l'editor) com al PDF exportat (mateix mecanisme Konva+`pdf-lib`, "paritat per construcció" — Bloc resum executiu punt 5). **No hi ha una capçalera "REAL" separada per a PDF versus pantalla: és una de sola.**

Cap altra "fitxa tècnica (pantalla)" / "PDF" / "exports" fora d'aquestes dues taules Q8 porta la paraula "REAL" com a capçalera (confirmat per grep exhaustiu backend+frontend, cap literal `'REAL'`/`"REAL"` cablejat fora d'aquest i18n).

### 2.2 · Resposta Q5 — amplada mesurada (no estimada)

**Font de la mesura: el propi algorisme del renderer** (`buildTableCellPrimitives`, `TechSheetEditor.jsx:909-960`), no una aproximació externa — el comentari del propi codi (:925-926) diu *"La font és monoespaiada, així que comptar caràcters n'és una mesura exacta, no una estimació"*. Constants confirmades al codi: `MM_TO_PX=2.4` (:74), `T_PAD=2*MM_TO_PX=4.8px` (:786), font `IBM Plex Mono` (:102, .ttf confirmat a `backend/assets/fonts/IBMPlexMono-*.ttf`).

Per a la columna de 13mm (`q8_size_set`, `TechSheetEditor.jsx:5719-5724`, on viu el comentari **M1** :5720-5723 sobre l'intent previ amb "ACTUAL"):

```
pt        = max(8, style.fontSize=9)              = 9
hdrPt     = max(8, pt*0.85) = max(8, 7.65)         = 8
hdrFontPx = round(hdrPt * 0.3528 * MM_TO_PX)
          = round(8 * 0.3528 * 2.4) = round(6.77)  = 7 px
hdrLS     = max(0.4, hdrFontPx*0.06) = max(.4,.42) = 0.42
hdrCharW  = hdrFontPx*0.6 + hdrLS = 4.2+0.42        = 4.62 px/car.
cw[col]   = 13mm * MM_TO_PX = 31.2 px
caben/línia = floor((31.2 - 2*4.8) / 4.62)
            = floor(21.6/4.62) = floor(4.675)       = 4 caràcters
```

- **"REAL"** (4 car., majúscules — `etiquetaCol` fa `.toUpperCase()` quan `capcaleraFina`) → **4 ≤ 4 → hi cap en 1 línia.** ✅ (confirma el comentari M1 tal qual).
- **"ACTUAL"** (6 car.) → ceil(6/4) = **2 línies** — exactament el que el comentari M1 diu que va passar i es va revertir.
- **"SAMPLE"** (6 car., mateixa longitud que "ACTUAL") → ceil(6/4) = **2 línies — el mateix desbordament, numèricament idèntic al d'"ACTUAL".**

Per a la columna de 18mm (`q8_fitting`, `TechSheetEditor.jsx:5539`): `cw=18*2.4=43.2px` → `caben/línia = floor((43.2-9.6)/4.62) = floor(7.27) = 7 caràcters`. **"SAMPLE" (6 car.) SÍ hi cap en 1 línia** aquí — la taula ampla no es veu afectada, només la de 13mm.

**El que cedeix, si es manté "SAMPLE" a la columna de 13mm:** NO la mida de font (ja al sòl `hdrPt=8` per `capcaleraFina`, que iguala el mínim absolut de NORMA_LAYOUT §2 — "caption/TH 10/12, MÍNIM ABSOLUT, mai 8px llegible" parla de pantalla normal; aquest 8 és ja el pis documentat per aquesta capçalera fina concreta, `TechSheetEditor.jsx:945-947`, i no es pot baixar més sense trencar aquest sòl). El que cedeix és **l'alçada de la fila de capçalera de TOTA la taula** (`hdrH = max(...hdrLines)*hdrFontPx + padding`, :960) — puja per a les 14 columnes perquè UNA sola en necessita 2 línies, exactament el mode de fallada que el comentari M1 ja documenta com a resolt cap enrere.

**Alternativa que sí cap:** eixamplar la columna de 13mm a ≥15mm (com la resolució original per "ACTUAL" hauria necessitat: 15,5mm segons el comentari M1) — però això "es menja" amplada d'altres columnes de la mateixa taula (14 columnes en total, ample útil compartit), o requereix revisar el repartidor `ampleUtilQ8()`/`trossosDeTalles` (:5698) que reparteix l'amplada entre bandes de talles.

### 2.3 · Resposta Q6 — altres llocs amb la mateixa afectació

Cercats tots els `col_real`/equivalents de "valor real de mesura" (contrast amb teòric/base), amb les seves traduccions als 3 idiomes:

| clau | ca | en | es | fitxer:línia | contrast amb | dins abast del brief? |
|---|---|---|---|---|---|---|
| `tech_sheet.q8_col_actual` | Real | **Real** | Real | `TechSheetEditor.jsx:5539,5724` | teòric/base | **SÍ — és el cas del Bloc 2.1/2.2** |
| `sizecheck.col_real` | Real (proto) | **Actual (proto)** | Real (proto) | `CheckMeasureEditor.jsx:275` | `historyCols` (preses anteriors) | Mateix concepte semàntic (mesura sobre la mostra/prototip), pantalla de "Comprovació de talla" — **NO esmentat explícitament al brief**, però si l'objectiu és "REAL→SAMPLE en el sentit de mesura sobre la mostra", aquesta capçalera hi encaixa igual |
| `comprovacio.col_real` | Real | **Actual** | Real | `ComprovacioPanel.jsx:237` | `comprovacio.col_teoric` | Mateix concepte — pantalla "Comprovació". **NO esmentat al brief** |
| `planning.time.tree.col_real` | Real | **Actual** | Real | `components/planning/TimeTree.jsx:179,277` | `col_estimate` (hores planificades) | **FORA D'ABAST** — "real" hi vol dir "hores efectivament treballades", no "mesura sobre la mostra"; contrast temporal, no de sastre |

**🚨 Inconsistència ja existent al repo, independent del canvi proposat:** pel MATEIX concepte ("valor mesurat" en contrast amb un valor teòric/objectiu), l'app ja té **dues traduccions angleses diferents avui**: `sizecheck.col_real`/`comprovacio.col_real` diuen **"Actual"** en anglès, mentre que `tech_sheet.q8_col_actual` (nom de clau que suggereix "actual" però el VALOR és) diu **"Real"** als tres idiomes. És a dir, el nom de la clau i el contingut del valor estan encreuats entre si en aquestes dues famílies. Si CANVI 2 només toca `tech_sheet.q8_col_actual` → "SAMPLE", l'app quedaria amb **tres paraules diferents** per al mateix concepte segons la pantalla: "SAMPLE" (fitxa tècnica), "Actual" (Comprovació/SizeCheck), "Real" (cap lloc després del canvi, si es fes consistent). 💡 PROPOSTA (a validar): si l'objectiu de fons és normalitzar el vocabulari "mesura sobre la mostra" a tota l'app, val la pena que Agus decideixi si `sizecheck.col_real`/`comprovacio.col_real` també passen a "SAMPLE" en el mateix tram, o si es queden fora deliberadament (són pantalles internes de comprovació, no documents que viatgen al fabricant).

Cap d'aquestes dues capçaleres germanes (`sizecheck`/`comprovacio`) és Konva: són `<th>`/`<td>` HTML normals sense amplada fixa (`ComprovacioPanel.jsx` usa un component `<Taula>` sense `width` per columna; `CheckMeasureEditor.jsx:275` alimenta una capçalera de `MeasureGrid` en CSS grid — no s'ha trobat cap `width` fix en px per aquesta columna concreta) — "SAMPLE"/"Actual (proto)" hi embolicarien sense trencar, a diferència de la taula Konva del Bloc 2.2.

---

## TAULA FINAL

| Àrea | Estat | Detall |
|---|---|---|
| Model/camp del veredicte | EXISTEIX, únic | `PieceFittingLine.decisio`, `fitting/models.py:469-481` |
| Cens BD (staging) | MESURAT | `''`=850 · ADJUSTED=11 · ACCEPTED=3 · REJECTED=0 |
| PDF reportlab del veredicte/REAL | NO EXISTEIX | fitxa tècnica = Konva+pdf-lib, no reportlab |
| Excel/CSV/DXF/RUL del veredicte/REAL | NO EXISTEIX | cap exportació els toca |
| Etiqueta=valor (mateixa cadena) | EXISTEIX, 4 llocs | `VerdicteCell`, `ComprovacioPanel`, `RecomptesFitting`, taula `q8_fitting` |
| Overflow "NO OK, FOLLOW SPEC" a pantalla | NO desborda (creix) | cap contenidor d'amplada fixa als 3 controls de pantalla revisats |
| Overflow "NO OK, FOLLOW SPEC" a taula impresa (si s'hi apliqués) | DESBORDARIA (mesurat) | 22mm → 9 car./línia; 19 car. → 3 línies |
| Capçalera "REAL" (CANVI 2) | EXISTEIX, 1 clau, 2 usos | `tech_sheet.q8_col_actual`, `TechSheetEditor.jsx:5539,5724` |
| "SAMPLE" a la columna de 13mm | DESBORDARIA (mesurat, repeteix M1) | 4 car./línia; 6 car. → 2 línies |
| "SAMPLE" a la columna de 18mm | Hi cap (mesurat) | 7 car./línia; 6 car. → 1 línia |
| Capçaleres germanes REAL/Actual fora d'abast literal del brief | EXISTEIX, inconsistent ja avui | `sizecheck.col_real`/`comprovacio.col_real` (en="Actual") vs `tech_sheet.q8_col_actual` (en="Real") |

**Cap canvi s'ha fet al codi ni a la BD.** Aquest document és 100% lectura.
