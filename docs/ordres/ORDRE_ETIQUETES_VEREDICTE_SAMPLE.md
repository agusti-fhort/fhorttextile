# ORDRE ETIQUETES VEREDICTE + SAMPLE — report d'implementació

> **Patró B · staging (`/var/www/ftt-staging`, branca `dev`) · 2026-09-23**
> **3 commits locals, cap push.** Cap migració. Equip fet per una sola sessió (implementador +
> verificador + guardia-i18n + guardia-ui + revisor-diff, tots aplicats manualment — l'entorn
> d'aquesta sessió no exposa els subagents natius `.claude/agents/*` com a tipus invocables).
> Precedent: `docs/diagnosis/DIAGNOSI_ETIQUETES_VEREDICTE_SAMPLE.md` (mateixa sessió, no committat).

**COMMIT 1 (veredicte): FET, 2 SHA.** **COMMIT 2 (REAL→SAMPLE): FET SENCER, 2 SHA** (2a capçaleres
germanes + 2b·update-23/09 la capçalera de la fitxa tècnica, desbloquejada — v. §5). Sortida
esperada deia «2 SHA» pel conjunt; n'hi ha 5 perquè `CLAUDE.md` exigeix un commit per
concern/subsistema (backend i frontend de CANVI 1 no comparteixen porta de verd: `manage.py
check` ≠ `npm run build`) — la casa ja treballa així arreu (v. `ORDRE_FIX_NOMENCLATURA_M1194.md`).

---

## 0 · Abans de res

**Cap sessió concurrent activa.** `git status` a l'inici mostrava fitxers pre-existents modificats/
no seguits (`DECISIONS.md`, `ops/qa/qa_f22_vocabulari_captures.py`, `backend/scripts_tmp/*`) amb
`mtime` de fa setmanes (21/08–27/08) — feina vella d'una altra sessió, no un procés viu. `git add`
sempre amb paths explícits, mai tocats.

`dev` ja era a `db3207cc` (= `origin/dev`); cap `git pull` necessari.

---

## 1 · COMMIT 1 — veredicte OK · ADJUSTED · NO OK, FOLLOW SPEC

### 1a · backend — `44b0174b`

`PieceFittingLine.DECISIO_ETIQUETES` + `etiqueta_decisio(codi, curta=False)`
(`backend/fhort/fitting/models.py:482-497`, just sota el camp `decisio`): mapa `codi → (llarga,
curta)`. **El codi de BD/API no es toca** (`DECISIO_ACCEPTED`/`ADJUSTED`/`REJECTED`, D-31.21
intacte). S'exposa de manera **additiva** a `/api/v1/vocabulari/` (`veredictes_fitting`,
`backend/fhort/models_app/vocabulari_views.py:199-206`): cada element passa de `{codi, etiqueta}`
a `{codi, etiqueta, etiqueta_llarga, etiqueta_curta}` — `etiqueta` (la frase catalana de l'admin)
no canvia de forma, per si algun consumidor futur la llegeix.

```
OK: {'codi': 'ACCEPTED',  'etiqueta_llarga': 'OK',                  'etiqueta_curta': 'OK'}
    {'codi': 'ADJUSTED',  'etiqueta_llarga': 'ADJUSTED',            'etiqueta_curta': 'ADJUSTED'}
    {'codi': 'REJECTED',  'etiqueta_llarga': 'NO OK, FOLLOW SPEC',  'etiqueta_curta': 'NO OK'}
```
Verificat amb `manage.py shell` (read-only, no fixture ni escriptura).

**⚠️ Desviament explícit del brief — «via i18n».** El brief demanava la forma via i18n; **no ho he
fet així**, i cal que ho confirmis. Hi ha una llei escrita i datada al mateix repo que diu el
contrari per a exactament aquest tipus de dada:

> `frontend/src/utils/vocabulariDominiFont.js:12-14` — *«Llei d'Agus (08/08): cap enumeració de
> domini es declara al frontend; una constant al client que dupliqui uns `choices` és una segona
> font de veritat que ningú actualitza el dia que la primera canvia.»*

i el mateix mòdul documenta que un vocabulari germà (les capes de mesura) **es va treure d'i18n
expressament** pel mateix motiu (`utils/capaInstancia.js:33-38`, «aquests literals ja NO són a
`i18n/*.json`: hi eren, i s'han tret»). He seguit aquesta llei en lloc del literal «via i18n» del
brief: el mapatge viu NOMÉS al backend (`DECISIO_ETIQUETES`) i el frontend el consumeix via
`/vocabulari/` (secció 1b), no via una clau `t()` duplicada. Si volies literalment i18next (p.ex.
perquè el vocabulari no és fiable abans del primer fetch, o per un altre motiu que no conec),
digues-ho i ho giro — és un canvi petit i localitzat a `etiquetaVeredicte.js`.

### 1b · frontend — `af7c202a`

Nou `frontend/src/utils/etiquetaVeredicte.js`: `useEtiquetaVeredicte()` → `(codi, curta) =>
etiqueta`, llegit de `useElements('veredictes_fitting')` (el mateix vocabulari de dalt). Sense
vocabulari encara, torna el codi cru (mateix mode de fallada degradada que la resta de consumidors
d'aquest vocabulari — **CAP llista de reserva al client**, també per llei del mateix mòdul).

Aplicat als **4 llocs** on el codi cru era el TEXT visible (inventari exhaustiu a la diagnosi
§1.3), amb la forma que pertoca segons si el contenidor és estret:

| lloc | fitxer:línia | forma | per què |
|---|---|---|---|
| Botons A/J/R de la graella de fitting | `components/model/fittingGridAdapter.jsx:236` | **curta** | toggle compacte, `padding:'4px 9px'` sense amplada fixa — la curta el manté igual d'estret que abans (ADJUSTED ja era el més llarg, 8 car., i segueix sent-ho: cap eixamplament) |
| Panell Comprovació | `components/model/ComprovacioPanel.jsx:255` | **llarga** | `<td>` sense `nowrap`, embolica sol si cal — panell de lectura, no toggle |
| Comptador per veredicte (peu de la graella de fitting) | `components/model/CheckMeasureEditor.jsx:417` | **llarga** | `<span>` en flux lliure |
| Taula impresa Q8 (fitxa tècnica, columna «Veredicte» 22mm) | `pages/TechSheetEditor.jsx:5549` | **curta** + llegenda | columna d'amplada FIXA (Konva): mesurat, 9 car./línia — «NO OK» (5) hi cap, «NO OK, FOLLOW SPEC» (19) no |

**La llegenda del peu** (`TechSheetEditor.jsx:5565-5566`, nova clau `tech_sheet.q8_nota_no_ok` =
«NO OK = follow spec», idèntica als 3 idiomes): reutilitza el mecanisme JA EXISTENT d'«una línia de
text solta» (`entrades.push({nota: …})`, el mateix que ja feia servir «peça sense sessió» dues
línies més amunt) — cap funció compartida tocada, `fontSize: 9` (> 8pt, sòl de la casa), 1 línia,
amplada de tota la pàgina (~250mm útils): hi cap sobrat.

### 1c · Mesures (Q3 de la diagnosi, reconfirmades)

Cap lloc de pantalla desborda (cap contenidor d'amplada fixa entre els 3 consumidors "llarga"/
"curta" no-Konva). La columna Konva de 22mm, amb la mateixa aritmètica de caràcters del
renderitzador (font monoespaiada IBM Plex Mono, `cw=52.8px`, `hdrCharW=4.62px` → **9 car./línia**):
«NO OK» (5) ✅ 1 línia · «NO OK, FOLLOW SPEC» (19) hauria necessitat 3 línies — per això la forma
CURTA hi va i la llarga es trasllada a la llegenda.

### 1d · Consumidors del valor cru — llistats, NO tocats

Cap exporta a Excel/CSV/DXF/RUL (confirmat NO EXISTEIX a la diagnosi §1.2, reconfirmat pels dos
agents d'inventari). Consumidors interns que llegeixen `ACCEPTED`/`ADJUSTED`/`REJECTED` com a
VALOR (lògica, no text) i que es queden EXACTAMENT com estaven:

- Backend: `fitting/views.py:691`, `fitting/services.py:738,729` (`if line.decisio ==
  DECISIO_REJECTED`, `.exclude(decisio=…)`).
- Backend: `fitting/serializers.py:215-216,396` (camp `decisio`, API), `fitting/repas_views.py:451,
  467,489` (clau `veredicte`), `fitting/escalat_presa_views.py:76` (clau `estat`) — les tres API,
  el valor hi viatja cru, tal com ha de ser.
- Frontend: `utils/taulaPresaPerTalla.js:24-28` (constants + `if (estat === REJECTED) return
  teorica` — lògica de negoci, no text).
- Frontend: `utils/taulesQ8.js:109,143,172` (`veredicte: v.estat`, pas intermedi cap a
  `TechSheetEditor.jsx` — el valor hi arriba cru i es tradueix just abans de pintar-se, a 1b).
- `pages/FittingPrintSheet.jsx:44` (`CASELLES = ['AC','AD','RJ']`): **no toca `decisio` en cap
  forma** — és un full en blanc per omplir a mà, les sigles són constants pròpies independents.

**🔎 Troballa fora d'abast, ANOTADA i NO TOCADA** (revisor-diff): `utils/cellaEscalat.js:94` calcula
i propaga un camp `estat` (el mateix `decisio`, via `escalat_presa_views.py`) cap a la graella
d'Escalat, però `MeasureGrid.jsx:249` hi llegeix `active.veredicte` — un nom diferent. Sembla que
el veredicte a la pantalla d'Escalat **mai arriba a pintar-se** (inert per un mismatch de nom de
camp, anterior a aquesta peça). No l'he tocat: no n'hi ha cap ús visible avui i no és del abast
d'aquesta ordre. Si interessa, és una peça pròpia.

### 1e · Verd

`manage.py check`: net (les 2 vegades, backend i final). `npx eslint` sobre els 5 fitxers tocats:
0 errors (79 warnings, totes preexistents i alienes als canvis — verificat que cap esmenta
`etiquetaVeredicte` ni cap símbol nou). `npm run build`: ✓ (1.29s). i18n: 0 claus que falten a cap
dels 3 idiomes (comprovat amb un script propi, no hi ha checker dedicat al repo).

---

## 2 · COMMIT 2 — REAL → SAMPLE

### 2a · Capçaleres germanes (render en viu) — FET, `d9ff667f`

`sizecheck.col_real` (`Real (proto)`/`Actual (proto)`/`Real (proto)` → **`Sample (proto)`** als 3)
i `comprovacio.col_real` (`Real`/`Actual`/`Real` → **`Sample`** als 3). Aquestes dues NO són
Konva: `<th>` HTML (`fittingShared.jsx:38-42`, `whiteSpace:'nowrap'`, sense `width` fixa) que
creix si cal — verificat que el text nou fa la MATEIXA longitud que el «Actual (proto)»/«Actual»
anglès que ja hi havia (14 i 6 caràcters respectivament): zero risc d'amplada nou. **NO** s'ha
tocat `planning.time.tree.col_real` (mateixa clau visual, domini diferent: hores reals vs
planificades — confirmat a la diagnosi §2.3, no és «mesura vs mostra»).

`npm run build` ✓, JSON vàlid als 3 fitxers, 0 claus que falten.

### 2b · La capçalera «REAL» de la fitxa tècnica (Q8, Konva) — 🛑 ATURAT (2026-09-23, matí)

> ✅ **DESBLOQUEJAT i FET la mateixa tarda — v. §5.** Agus va confirmar l'abast (només la
> plantilla d'inserció, cap migració de `.ftt`) i aquesta peça es va tancar amb `6ff24d74`.
> Es deixa el raonament de l'aturada tal com es va escriure, sense retocar-lo: és l'acta de
> per què es va parar, i l'acta no es reescriu.

**No l'he tocada (en aquell moment).** Motiu, amb la mateixa precisió que demanava el brief:

`tech_sheet.q8_col_actual` (el «REAL» de la fitxa) **NO es calcula al vol en cada pintat**: es
resol UNA vegada quan s'insereix la taula (`TechSheetEditor.jsx:5539,5724`, `label: tEn(...)`) i
el resultat —l'string «Real», no la clau— queda escrit dins l'objecte `taula` que
`inserirGrupPaginat` (:5137) posa a `pages[…].objects`. Aquest mateix objecte (amb `columns[].label`
i `columns[].width` ja resolts a valors concrets) és el que `services_ftt.pack(document_json, …)`
(`backend/fhort/models_app/services_ftt.py:90`) empaqueta i desa com a fitxer `.ftt` — confirmat
els dos costats, frontend i backend. **És, literalment, dada serialitzada de la fitxa**, no una
propietat de render que es torni a calcular cada vegada que s'obre el document.

Per l'ATURADA explícita del brief («si la capçalera forma part de les dades serialitzades →
ATURA»), m'aturo aquí i no toco `width: 13`/`18` ni `tech_sheet.q8_col_actual`.

**El que això vol dir en la pràctica, tant si es desbloqueja com si no:** només les taules Q8
que s'insereixin de nou a partir del canvi tindrien el text/amplada nous — qualsevol fitxa tècnica
ja generada (ja empaquetada a `.ftt`) es queda per sempre amb «REAL»/13mm tal com era, perquè és
un document històric, no una plantilla que es torna a resoldre. Això és consistent amb com ja es
comporta TOT el sistema de `snapshot` de Q8 (les xifres i veredictes d'una fitxa vella tampoc
«es posen al dia» soles) — no és un efecte nou d'aquesta peça, és com funciona la casa. Ho dic
igualment perquè és el fet rellevant per decidir.

**No sé si això és «F5».** No he trobat cap diagnosi ni memòria amb aquest nom lligada
específicament a la serialització de `TechSheetEditor`; «F5» apareix moltes vegades al repo per a
sprints sense relació (import multipeça, POM LEG OPENING, cost intern…). Si «F5» és una iniciativa
concreta que conec amb un altre nom, o si el que demanaves era només «no reescriguis fitxes ja
fetes» (que ja ho complia sense necessitat d'aturar-me), digues-m'ho i faig 2b en un commit propi:
la implementació seria trivial (canviar `width: 13` → `18` a :5539,5724 i la clau
`tech_sheet.q8_col_actual` als 3 idiomes a «Sample», mateix mecanisme que 2a) i ja tinc la mesura
feta (§1c de la diagnosi: a 18mm hi caben 7 car./línia, «SAMPLE» (6) hi cap).

**Amplada, per quan es faci:** eixamplar la columna `actual` de 13→18mm (com demana el brief, «com
la germana») es menja 5mm d'alguna altra columna de les 8 de la taula `q8_size_set`
(`layer` 16 · `pom` variable · `nom` variable · talla-base 13 · `_act` 13→18 per talla). No cal
baixar cap font (el sòl ja hi és, 8pt a la capçalera fina) — el repartidor `trossosDeTalles`
(`:5698`) ja calcula l'ample disponible per bandes de talles, així que l'eixamplament de 5mm/talla
el paga l'ample lliure de la pàgina abans de forçar-hi una banda més, no una columna concreta; NO
ho he verificat al detall perquè no he tocat el codi.

---

## 3 · Guardians — resum

- **i18n (paritat)**: VERD. 0 claus que falten als 3 idiomes en cap dels 2 commits de frontend
  (verificat dues vegades, abans i després de 2a). Cap literal cablejat nou fora d'i18n.
- **UI (tokens/criteri)**: VERD. Cap color, icona ni component nou — es reutilitzen íntegrament
  `VERDICTE_TO`/`VERDICTE_COL`/`RECOMPTE_COL` (mapes de color per codi, sense tocar) i el mecanisme
  ja existent de «línia de text solta» per a la llegenda. NORMA_LAYOUT §7 («text «Accepted/
  Adjusted/Rejected», mateix color, mateix estil») ja anticipava aquest patró.
- **revisor-diff**: 1 bandera anotada, no tocada (§1d, `cellaEscalat.js`/`MeasureGrid.jsx`
  mismatch `estat`/`veredicte`, sembla inert, fora d'abast). Cap migració, cap signal, cap canvi de
  valor a BD. Canvi additiu a `/vocabulari/` (verificat que només 2 hooks el consumien i tots dos
  són a l'abast d'aquesta peça).
- **verificador**: VERD als 3 commits (`manage.py check` net ×2, `npm run build` ✓ ×2, `eslint`
  0 errors, diff fa exactament el que tocava a cadascun — verificat `git show --stat` contra
  l'esperat abans de cada commit).

---

## 4 · Per a Agus

1. **Confirma o corregeix la decisió «via i18n» de l'1a** (backend+vocabulari en lloc de claus
   i18n dobles) — argumentat contra la Llei d'Agus 08/08 del propi repo, però és un desviament
   explícit del literal del brief i mereix un sí/no teu. *(Encara pendent — no es va tocar a la
   continuació de §5.)*
2. ~~Digues si 2b és realment «F5» aturat~~ — **resolt**: vas confirmar l'abast (§5), fet a
   `6ff24d74`.
3. Revisa la cadena (`git show 44b0174b`, `af7c202a`, `d9ff667f`, `6ff24d74`) i fes el push des de
   SSH quan toqui — **cap dels 4 s'ha pujat**.
4. `frontend/dist` s'ha reconstruït a cada peça de frontend (1b, 2a, 2b): **staging serveix ja el
   codi nou** (regla de la casa: `npm run build` és desplegar). Backend: **no** he fet `systemctl
   restart ftt-staging` en cap moment — els canvis backend d'1a (mètode nou al model + endpoint)
   no necessiten reiniciar gunicorn per a res que aquesta ordre verifiqui per si sola, però si vols
   provar `/api/v1/vocabulari/` en calent cal el restart (és una acció que altera estat compartit,
   no l'he fet jo).
5. **Tests escrits del §5 no s'han executat** (consigna explícita del brief de continuació): si
   vols que corrin de veritat (`cd frontend && node --test src/pages/techSheetQ8Header.test.js`),
   dic-ho i ho verifico — la meva lectura manual diu que passarien tots.

---

## 5 · Continuació 2026-09-23 (tarda) — 2b desbloquejat: «SAMPLE» a 18mm, `6ff24d74`

Ordre de continuació d'Agus: abast confirmat (només la plantilla d'inserció; `.ftt` existents
intocats, cap migració) i llum verda per fer 2b sencer.

### 5a · El canvi

`TechSheetEditor.jsx:5741` (la taula `q8_size_set`, l'única de les dues amb amplada 13mm —
`q8_fitting:5543` ja tenia 18mm de sempre i no s'ha tocat): `width: 13 → 18`. `tech_sheet.
q8_col_actual` (ca/en/es) `"Real" → "Sample"` — clau ÚNICA compartida per les dues taules Q8, així
que el canvi de text els afecta totes dues alhora amb una sola edició. **Cap altra línia tocada**:
ni `services_ftt.pack`, ni `inserirGrupPaginat`, ni l'estructura de l'objecte `taula` (segueix
sent `{key, label, width}` per columna, mateixa forma d'abans).

### 5b · Retrocompatibilitat — per què els `.ftt` vells no es toquen (verificat, no assumit)

`buildTableCellPrimitives(obj)` (`TechSheetEditor.jsx:910` i endavant) llegeix `obj.columns[i].
label`/`.width` **directament de l'objecte que rep**, sense cap referència externa a la plantilla
d'avui, a la clau i18n ni a cap versió: és una funció pura de l'`obj` serialitzat. Un `.ftt` vell
conserva els seus `columns[].label="Real"`/`width=13` (couen's en el moment de la inserció
original) i seguirà pintant-se exactament igual, per sempre — no hi ha cap pas de «migració» ni
«actualització en obrir» que calgui escriure perquè no n'hi ha cap que ho toqui.

### 5c · Mesura + rasterització (rèplica fidel, no la app sencera)

Konva/pdf-lib són browser-only i arrencar tot `TechSheetEditor` (auth, API, sessió tancada, un
model real) per una captura és desproporcionat per a un canvi d'una xifra i una clau i18n. S'ha
seguit el mateix mètode que la memòria `ftt-mesurar-impressio-i-no-login` demana per a diagnosi
sense navegador de l'Agus: **rèplica fidel + Chromium headless**.

- Constants i fórmula copiades verbatim de `TechSheetEditor.jsx:74,786,913-914,952-958` (`MM_TO_PX
  =2.4`, `T_PAD=2·MM_TO_PX`, `hdrPt=max(8,pt·0.85)`, `hdrFontPx=round(hdrPt·0.3528·MM_TO_PX)`,
  `hdrCharW=hdrFontPx·0.6+hdrLS`) — mateix mètode que la diagnosi original (§1.5/2.2), amb el
  propi comentari del codi com a garantia: *«la font és monoespaiada, així que comptar caràcters
  n'és una mesura exacta, no una estimació»* (`:925-926`).
- Renderitzat amb **Konva real** (`frontend/node_modules/konva/konva.min.js`, el mateix paquet que
  fa servir l'app) dins Chromium headless (Playwright, `/tmp/qa-venv`), no només la fórmula: es
  demana a `Konva.Text` que dibuixi «REAL» a 13mm i «SAMPLE» a 18mm amb els mateixos `fontSize`,
  `fontFamily` (IBM Plex Mono), `letterSpacing` i `wrap:'word'` que l'app declara, i es llegeix
  quantes línies hi surten de debò (`txt.textArr.length`), no només la predicció.
- **Resultat (fórmula i Konva real coincideixen als dos):**

  | | amplada | caben/línia | text | línies (fórmula) | línies (Konva real) |
  |---|---|---|---|---|---|
  | Document VELL (`.ftt` ja fet) | 13mm | 4 car. | REAL | 1 | 1 |
  | Document NOU (a partir d'ara) | 18mm | 7 car. | SAMPLE | 1 | 1 |
  | *(referència, no es fa)* | 13mm | 4 car. | SAMPLE | 2 | — |

- Captura: `q8_header_replica.png` (scratchpad de la sessió) — dues caixes rotulades «DOCUMENT
  VELL» i «DOCUMENT NOU» amb el text real dibuixat dins la caixa a escala i el número de línies
  imprès al costat. Enviada inline al xat de la sessió; no forma part del repo (és una prova
  d'aquesta ordre, no un artefacte de producte).

### 5d · Tests escrits, NO executats

`frontend/src/pages/techSheetQ8Header.test.js` (`node --test`, patró de la casa —
`taulaPresaPerTalla.test.js` n'és el precedent: sense vitest, funcions pures). Com que
`buildTableCellPrimitives` no és `export`ada (viu dins d'un fitxer amb Konva/react-i18n que
`node --test` no pot resoldre en sec), el test declara la fórmula com a **MIRALL documentat**
(comentari a l'capçalera del fitxer explicant-ho i apuntant a les línies font exactes) en lloc
d'important-la — si algú toca `MM_TO_PX`/`T_PAD`/la fórmula de `hdrCharW` a `TechSheetEditor.jsx`,
aquest mirall s'ha d'actualitzar a mà. Casos: SAMPLE cap en 1 línia a 18mm · SAMPLE hauria
desbordat a 13mm (el motiu del canvi) · REAL segueix en 1 línia a 13mm (retrocompatibilitat) · sòl
de 8pt respectat · les dues definicions de columna de la plantilla usen la mateixa clau i totes
dues valen 18mm (llegit del codi font amb regex, no una suposició) · els 3 idiomes valen «Sample»
· forma mínima d'una columna vella (cap camp nou obligatori). `eslint`: 0 errors. **No s'han
corregut amb `node --test`**, per la consigna explícita del brief.

### 5e · Verd

`npx eslint` sobre els 5 fitxers tocats: 0 errors. `npm run build`: ✓ (1.15s). i18n: 0 claus que
falten. `git show --stat 6ff24d74` verificat contra l'esperat abans del commit (5 fitxers: 1 jsx +
3 json + 1 test nou).
