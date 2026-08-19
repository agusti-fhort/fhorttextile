# REPORT · Les cinc maquetes com a especificació

> **Data:** 2026-08-05 · staging `dev` · **cap push** · **cap suite** · `git add` selectiu.
> Base: [`DIAGNOSI_UI_MAQUETES.md`](DIAGNOSI_UI_MAQUETES.md) (cens del matí) i
> [`REPORT_UI_MAQUETES.md`](REPORT_UI_MAQUETES.md) (primera tongada).

## 1 · Els commits

| # | Commit | Què tanca |
|---|---|---|
| A | `f0c852fa` | Els TRES comentaris rancis, esmenats |
| B0 | `ec0e9730` | `GET /api/v1/mesures/diccionari/` — el vocabulari d'identitat, publicat |
| B1 | `91841246` | Píndoles d'instància per dimensió (M1) |
| B2 | `3af98656` | Modal `＋` de posició i combinacions (M2) |
| B3 | `4e621f06` | Cercador: sufixos · nivells · ↓ des de l'última fila (M5·M5b·M5c) |
| B4 | `3096dfcf` | Tecla `L` i fons de les files de capa (M3b·M3c) |
| B5 | `af3e7400` | Barra d'estat fixa al peu (M7) |
| C1 | `617db73f` | **El veredicte del fitting deixa de perdre's** (D6) |
| C2 | `1a5e2c10` | Barra de recomptes + marca de germana derivada (F9 · F7 parcial) |

## 2 · A · El diccionari, llegit a BD

**El cens del matí es va equivocar, i el brief tenia raó.** El diccionari existeix des de
`b631b12d` (F2 · D-31.26) i està sembrat als **tres schemes** (`public`, `fhort`, `los`), 10
files, `is_system=True`:

| Eix | Slugs | Sufix |
|---|---|---|
| **POSICIÓ** | left · right · top · bottom · cf · cb · side | `L` · `R` · `T` · `B` · `CF` · `CB` · `S` |
| **POSICIÓ** | waistband_seam | *(cap — és un DATUM, es diu a la descripció)* |
| **ESTAT** | relaxed · extended | *(cap — usen el codi oficial del client)* |

### La diferència de format, que és el que calia escriure

**D-31.26 diu CONCATENAT sense guió** (`B`+`T` → `BT`, `FS`+`CF` → `FSCF`).
**Les dades vives de staging no ho compleixen.** L'única família d'instància que hi ha
—model 188, `fhort`— està desada així:

```
model=188  instancia='left'   capa='exterior'  nom_fitxa='AH-L'    ← amb GUIÓ
model=188  instancia='right'  capa='exterior'  nom_fitxa='AH-R'    ← amb GUIÓ
```

Segons el contracte haurien de ser `AHL` i `AHR`. **No s'ha migrat res**: `nom_fitxa` és text
lliure del patronista i reescriure-li la nomenclatura sense que ho demani seria pitjor que la
inconsistència. **Tot el que es crea a partir d'avui surt bé** (B1/B2/B3 componen amb la regla
del backend, i hi ha test que ho fixa: `assert.notEqual(codiProposat(D,'AH',['left']), 'AH-L')`).
**Decisió pendent:** migrar les dues files del 188, o deixar-les.

Altres troballes d'A:

- **`instancia` és un slug compost amb guió** (`left-relaxed`) i els dos eixos són ORTOGONALS.
  Coincideix amb el que el front ja desmuntava.
- **`capa` no entra mai al codi** (`regles.capa_al_codi: false`).
- **La constant local només tenia 4 dels 10 slugs** → `cf` es llegia «Cf». Corregit a B1.

## 3 · B · Mesures, v8.1 sencera

Els cinc blocs, fets. El que val la pena destacar:

- **B0 era invisible i bloquejava tot B.** Les dues taules estaven sembrades i **cap endpoint
  les publicava**. Sense el GET, B1/B2/B3 només es podien fer duplicant el vocabulari al front.
  L'endpoint emet també **la regla de composició com a DADA** (`sufix_separador`,
  `capa_al_codi`, `instancia_separador`), de manera que el dia que canviï no hi haurà dues
  respostes.
- **`dimState` es calcula per EIX, no per parella.** Una fila que ja sigui `top` té la POSICIÓ
  ocupada encara que ni «Esquerra» ni «Dreta» hi surtin enceses; la maqueta, amb només dues
  opcions per dimensió, no podia veure aquest cas.
- **La família és (POM + CAPA).** L'exterior i el folre del pit es parteixen per separat.
- **Partir hereta els valors; afegir una germana de capa no.** Són dos actes diferents i tenen
  dues respostes diferents (v. §6, on es diu que això contradiu un comentari viu).
- **`aplicaInstancia` és el motor comú** de les píndoles i del modal: dos camins voldrien dir
  dues identitats per a la mateixa germana, i la clau única de la BD no perdona això.

## 4 · C · Fitting

### C1 · El veredicte que es perdia — TANCAT

El defecte més seriós del cens. Verificat sobre la superfície VIVA
(`/models/<id>?tab=Mesures&fitting_session=<id>`) amb els PATCH capturats:

| | |
|---|---|
| En obrir | els veredictes desats **surten encesos** (abans: graella en blanc) |
| En decidir | **un** PATCH `{decisio: 'ADJUSTED'}`, la mateixa porta que la nota |
| Després de F5 | **els tres hi tornen a ser** |

Dos detalls que no eren obvis:

- **Se sembra també en CONSULTA.** Una sessió segellada s'ha de poder rellegir amb els colors
  amb què es va decidir; el `decisio` opt-in només afegeix les portes que escriuen.
- **El buffer es consulta amb `in`, no per veritat.** `null` hi és un valor legítim —«s'acaba de
  treure el veredicte»— i amb `||` la cel·la hauria tornat a pintar el valor desat: desmarcar no
  s'hauria pogut veure mai.
- **En fallar, el buffer es desfà i s'avisa.** Un veredicte que es pinta i no arriba és pitjor
  que un que no es pinta: la modista continua avall creient que ha decidit.

### C2 · Recomptes i germana derivada

Barra de recomptes feta (sobre les línies de la talla BASE, que són les úniques que es
decideixen). Marca `DERIVADA` feta, llegint l'`origen` que el backend ja emetia des de C4/F2 i
que el front ignorava.

## 5 · 🛑 D i E · PUNT DE PARADA

### D · Comprovació v2 — **no construïda**

La maqueta demana cinc seccions. Tres necessiten dades que **no existeixen**, i el brief mana
aturar-se i llistar-ho exactament en comptes d'inventar-ho o simular-ho.

| Secció de la v2 | Es pot fer avui? | Què falta |
|---|---|---|
| 1 · Bloquegen (fila sense valor a la base) | **SÍ** | `taula-mesures` ja serveix `base_value_cm` per fila |
| 1 · Bloquegen (POM sense regla de graduació) | **SÍ** | `taula-mesures` ja serveix `logica` per fila |
| 2 · Van quedar enrere quan la base es va moure | **PARCIAL** | `base_stages_view` emet `context` + `at`; **falta l'endpoint que compari la data de la darrera presa amb la del moviment de base i en tregui els dies** |
| 3 · Preses descartades pendents de reclamar | **NO** | `SizeCheckLine.decisio='valor_descartat'` existeix, però **no hi ha cap lectura agregada per MODEL** que en digui el valor que va arribar, el vigent i la SESSIÓ |
| 4 · Fora de tolerància al darrer fitting | **NO** | **`PieceFittingLine` no té `tol_minus`/`tol_plus`** (verificat: els camps són a `SizeCheckLine`, que és un altre flux). Sense tolerància al costat del fitting no es pot dir «fora de tolerància» |
| 5 · Famílies de mesura | **NO** | Falten DUES coses: (a) l'agregat per família (POM × capa × instància amb valor i **origen llegible**); (b) **el concepte de BUIT DECLARAT amb MOTIU** — les files `gap` de la maqueta («la germana es va proposar i es va treure: el coll passa sota l'aixella esquerra»). `desactivar_pom_view` no desa cap motiu i no hi ha cap model que el pugui guardar |

**El que falta, en una llista:**

1. `GET /api/v1/models/<id>/comprovacio/` — no existeix cap endpoint de preflight/checklist.
2. `PieceFittingLine.tol_minus` / `tol_plus` (o la font de tolerància del fitting) — camp nou.
3. Lectura agregada de preses descartades per model, amb la sessió d'origen.
4. Model per al **buit declarat amb motiu** d'una germana (avui la poda és `is_active=False` i
   prou) + la porta que l'escrigui.
5. L'agregat de famílies amb l'origen de cada cara en text llegible («Derivat de l'exterior ·
   18/07»), que avui només existeix com a slug (`origen`).

**Per què no s'ha fet a mitges:** el bloc de veredicte de dalt («La fitxa encara no pot sortir ·
2 bloquegen · 5 a revisar») és un RECOMPTE de totes les seccions. Amb tres seccions sense dades,
diria «la fitxa pot sortir» sense haver mirat la tolerància ni les preses descartades. Una
pantalla de comprovació que dona el vistiplau sense comprovar és pitjor que no tenir-la.

### E · Vista de família v1 — **no construïda, i cal decidir si existeix**

⚠️ **El propi `ops/maquetes/README.txt` la declara DESCARTADA:**

```
Descartada — NO la facis servir:
  maqueta_vista_familia_v1.html    · absorbida com a secció 5 de Comprovació
```

El brief la llista com a especificació. **Contradicció directa** entre el brief i el README de
la carpeta canònica. A més, el seu contingut **és** la secció 5 de Comprovació, que està
bloquejada pels punts 4 i 5 de la llista de dalt.

**No s'ha construït** per les dues raons alhora. Cal que l'Agus digui si la v1 de família
ressuscita com a pantalla pròpia o es queda absorbida.

## 6 · F · Wizard de model — censat, **no alineat**

⚠️ **El README diu que aquesta maqueta és «pendent de validació»**, no aprovada. El brief la
tracta com a criteri d'acceptació. Reestructurar un flux de creació que funciona contra una
maqueta que ningú ha validat és exactament el que la governança de la casa no permet, així que
s'ha fet el CENS i prou.

| Bloc de la maqueta | Estat a `ModelWizard.jsx` |
|---|---|
| 3 passos (Identificació · Peça · Talles) | **HI ÉS PARCIAL** — la viva en té **4 blocs**: el 4t hostatja `GraduacioPanel` (`491993cd`), que el brief prohibeix tocar |
| Filtres TARGET per descarte | **HI ÉS** (chips, desmarcables — el target és filtre opcional des de P6) |
| Filtres FIT | **HI ÉS** (chips `FITS`), però a la viva el FIT alimenta la GRADUACIÓ, no el filtre del catàleg |
| Filtre CONSTRUCTION | **A LA VIVA I NO A LA MAQUETA** |
| Cercador de peça per nom o codi | **HI ÉS** |
| Finder de 3 columnes (Grup · Família · Item) | **HI ÉS** — `CascadeSelector` |
| Pas 3 · sistemes de talles «per proximitat, cap amagat» | **HI ÉS PARCIAL** — es filtren per target i es descarten els que no tenen talles; **no hi ha ordenació per proximitat ni el filtre de text «escriu per filtrar»** |
| Pas 3 · talles del run | **HI ÉS** |
| Pas 3 · talla base amb ★ | **HI ÉS** |

**Divergència que val la pena decidir:** la maqueta fa del FIT un filtre del catàleg de peces; a
la viva el FIT és un eix de graduació. Són dues coses diferents amb el mateix nom.

## 7 · La maqueta de Mesures passa a v8.2

Fet, com demanava el brief: `ops/maquetes/maqueta_mesures_carril_v8_2.html`, amb el bloc
**REGLA DE GRADUACIÓ** (Règim · Δ · Δ break · Talla break) incorporat, les columnes buides (mai
pre-omplertes — lliçó del model 1302) i la nota que explica que la v8.1 no el portava perquè és
**anterior** a la decisió (`ff23c7f4`, W2/W3, 31/07, confirmada per l'Agus el 05/08).
`README.txt` actualitzat: la v8.2 és la vigent i la v8.1 queda com a històric.

**No entra en cap commit**: `ops/` és untracked per decisió pròpia del README.

## 8 · SORPRESES

1. **El cens del matí va declarar quatre divergències «estructurals» creient-se un comentari.**
   `capaInstancia.js` deia que el diccionari «encara no existeix (arriba amb C4-ins i la
   Montse)» quan feia hores que existia. Les quatre s'han fet avui en un dia. **La lliçó no és
   sobre el diccionari: és que un comentari ranci en zona sensible costa un tram sencer de
   feina mal planificada.** Tres n'hi havia; els tres ja estan esmenats (bloc A).
2. **Cap endpoint publicava les dues taules de vocabulari** tot i estar sembrades des de fa
   dies i tot i que `capaInstancia.js` ho tenia anotat com a TODO. Sense B0, B1/B2/B3 haurien
   acabat duplicant el vocabulari al front.
3. **`PieceFittingLine` no té tolerància.** El fitting mesura i decideix, però la banda de
   tolerància viu a `SizeCheckLine`. La secció 4 de Comprovació la dona per feta.
4. **Les úniques dades d'instància vives de staging incompleixen D-31.26** (`AH-L` en comptes
   de `AHL`). Dues files, model 188.
5. **`dictionary_views.py` ja existia** i és una altra cosa (la nomenclatura d'un CLIENT). El
   nom que hi anava a posar hauria trepitjat feina d'una sessió concurrent; l'endpoint nou viu
   a `identity_views.py`.
6. **Contradicció maqueta ↔ codi viu sobre l'herència de valors.** `EditableTable` té escrit
   que una germana que neixi amb el valor de la mare és «el pitjor defecte possible en una
   taula de mesures»; la v8.1 mana que **partir** hereti els valors. S'ha implementat la
   maqueta i el comentari s'ha mantingut per a l'altre gest (afegir germana de capa), que sí
   que neix buida. **Són dos actes diferents**, però convé que l'Agus ho confirmi.
7. **Dues de les cinc maquetes no són font vàlida**: la de família està DESCARTADA al README i
   la del wizard és «pendent de validació». El brief les tracta com a criteri d'acceptació.

## 9 · Què queda diferent de cada maqueta

| Maqueta | Què queda fora | Per què |
|---|---|---|
| **Mesures v8.2** | Res dels blocs demanats | — |
| **Fitting v3** | **La FOLGANÇA de la germana derivada** (`sis.folg`) | La maqueta la cabla a `2,0`; el domini **no té camp** on desar-la. Calcular-la com el diferencial viu seria decidir la D4 de l'Agus. La MARCA sí que hi és perquè no demana cap número |
| **Fitting v3** | El vocabulari de capes (Interlining/Binding/Knit/Reinforcement) | **Excepció declarada al brief**: mana D-31.22 |
| **Comprovació v2** | Tota la pantalla | §5 — 3 de 5 seccions sense dades |
| **Vista de família v1** | Tota la pantalla | §5 — descartada al README + bloquejada com la secció 5 |
| **Wizard v1** | L'alineació | §6 — maqueta no validada; cens fet |

## 10 · Verificació

- **`manage.py check`** net a cada commit de backend.
- **`npm run build`** net a cada commit de frontend.
- **`node --test`**: **140/140** (11 de nous, sobre la composició de codi i slug de D-31.26).
- **Checklist de pantalla als TRES idiomes** (`ca` · `en` · `es`), amb **consola a zero** a cada
  moment: càrrega · partir un POM · modal `＋` · cercador · tecla `L` · F5 · navegació entre
  superfícies · `prefers-reduced-motion`.
- **QA de la superfície viva del FITTING** als tres idiomes, amb els PATCH capturats.
- Passis a `scratchpad/qa_fase_b.py` i `scratchpad/qa_fitting.py`.
- Endpoint nou provat contra el tenant `fhort` amb `django.test.Client`.

## 11 · Què decideix l'Agus

1. **D · Comprovació**: aprovar els 5 punts de backend de §5, o retallar la pantalla a les dues
   seccions que sí que es poden fer avui (i llavors el bloc de veredicte no pot dir «pot sortir»).
2. **E · Vista de família**: ressuscita com a pantalla pròpia o es queda absorbida? El README diu
   descartada; el brief la demana.
3. **F · Wizard**: es valida la maqueta v1? I el FIT és filtre de catàleg (maqueta) o eix de
   graduació (viva)?
4. **D4 · La folgança** de la germana derivada: diferencial viu o valor declarat?
5. **Les dues files del model 188** amb `AH-L`/`AH-R`: es migren a `AHL`/`AHR` o es deixen?
6. **L'herència de valors en PARTIR** (§8.6): es confirma que partir hereta i afegir no?

---

**Cap push. Cap suite. `git add` selectiu a tots els commits.**

---
---

# TRAM U · SEGONA TONGADA — v8.1 manant, els dos modes, el fitting i la Comprovació

> **Data:** 2026-08-05, vespre i nit · staging `dev` · **cap push · cap suite** · `git add` selectiu.
> Aquesta part respon els dos briefs del vespre i el tancament. **Cap superfície s'hi reporta
> sense haver-la obert al navegador amb el `dist` real i comparat bloc a bloc amb el seu HTML.**

## U.1 · Els commits

| # | commit | què |
|---|---|---|
| 1 | `f2e00eac` | les dimensions de la taula surten del diccionari de BD, no del codi |
| 2 | `dda31147` | les paraules d'instància, en anglès canònic i fora d'i18n |
| 3 | `91989bf7` | la taula d'autoria a la forma v8.1 (fora la regla, fora els grisos, la capa al seu lloc) |
| 4 | `95b61cad` | la porta per fila dels dos eixos d'identitat |
| 5 | `b8cda79a` | «Mesurar prenda» passa a ser la MATEIXA taula, en mode presa |
| 6 | `20419138` | l'origen d'una mesura deixa de ser efecte secundari d'una altra escriptura |
| 7 | `75e01595` | la graella de fitting tornava buida perquè manava la càrrega que arribava tard |
| 8 | `4b99ee72` | la línia de dreceres del fitting (maqueta v3) |
| 9 | `448ee468` | la Comprovació, construïda sencera (D-31.17) |

**Gate:** `manage.py check` net · `npm run build` net · `node --test` 28 verds ·
`manage.py test fhort.models_app.test_origen_no_es_efecte_secundari fhort.models_app.test_c4_escriptura_germanes` → **20 OK**.

---

## U.2 · README de maquetes — la línia falsa, retirada

La línia «v8.2 = v8.1 + REGLA DE GRADUACIÓ… l'Agus l'ha confirmat el 05/08» **era falsa**: la va
escriure Claude Chat, no l'Agus. Retirada i substituïda per l'**ordre viva, amb data i autor**:

> **ORDRE VIVA · AGUS · 05/08/2026 vespre:** la columna de REGLA DE GRADUACIÓ (Règim · Δ ·
> Δ break · Talla break) SOBRA de la taula de mesures. La v8.1 mana en FORMA.

I la variant que sí que calia, anotada:

> **«v8.2-presa» = v8.1 + la columna BASE VIGENT · mode presa · IMPLEMENTADA.** No té fitxer HTML
> propi: és la v8.1 amb UNA columna més, en lectura, just abans del carril.

`maqueta_mesures_carril_v8_2.html` queda **DESCARTADA**. *(`ops/` és untracked: no entra en cap commit.)*

---

## U.3 · 🔴 `set-measurements` ja no reescriu `origen` — commit `20419138`

### Cens previ: qui escriu `origen='MANUAL'` per efecte secundari

| lloc | qui hi entra | estat |
|---|---|---|
| `views.py:set_measurements_view` | `EditableTable.desa()` sense `onPomSave` (branca viva per a qualsevol client amb token) | ✅ **corregit** |
| `views.py:gravar_pom_view` | `MeasuresEntryPanel.savePom` → **el camí REAL de la pantalla d'autoria** | ✅ **corregit** |
| `views.py:measurements_chat_view` (~2551) | el xat d'IA de mesures, acció `AFEGIR` | 🚩 **NO tocat** — mateix defecte, fora del que el brief demanava |
| `views.py:_write_base` · `escalat_ajustar_talla_view` | escriptura d'UNA mesura | no aplica: hi escriuen el valor i l'origen que els correspon |

Cap altre consumidor de `set-measurements` (cens a `frontend/src`, `frontend-backoffice/src`, `*/urls.py`).

### El defecte, mesurat

Les dues portes posaven `origen='MANUAL'` i **les dues toleràncies del catàleg** als `defaults`
de l'`update_or_create` — és a dir a **cada fila del payload**, hagués canviat el valor o no.
N'hi havia prou de reenviar la taula (moure una fila de capa, desar sense tocar cap xifra)
perquè una base `CHECKED` passés a `MANUAL` i les toleràncies afinades tornessin al defecte.

Trenca la precedència temporal, i no es pot desfer mirant la fila: `origen` el sobreescriu el
canvi següent; qui conserva la seqüència és `MeasurementChangeLog`, append-only.

### La regla nova (`_procedencia_de_mesura`, punt únic per a les dues portes)

- si el **payload ho diu explícitament**, mana el payload;
- si la fila **neix** → `MANUAL` + toleràncies del catàleg (no hi ha res a trepitjar);
- si la fila **ja hi és i el valor CANVIA** → `MANUAL` (algú acaba de teclejar-la);
- si la fila **ja hi és i el valor és el MATEIX** → **no es toca res**.

Un cop la fila existeix, les toleràncies no es reescriuen mai des del catàleg.

### El test que ho fixa

`backend/fhort/models_app/test_origen_no_es_efecte_secundari.py`, 5 casos: (1) `set-measurements`
amb el mateix valor **deixa la base `CHECKED`** *(el del brief)*; (2) `gravar-pom`, igual;
(3) **l'invers** — canviar el valor **sí** que passa a `MANUAL`; (4) el payload explícit mana
sempre; (5) una fila nova neix `MANUAL` amb el catàleg.

---

## U.4 · FITTING — contrastat contra `maqueta_fitting_v3`

### El blocador era un defecte de producte, no del banc — commit `75e01595`

La pantalla canvia de FONT en calent (s'obre amb `check` i passa a `fittingSource` quan la sessió
arriba); les dues càrregues viatjaven alhora i **totes dues feien `setRaw`**: manava la que
resolia l'última. Traça al banc (model 188 · sessió 147):

```
200 GET /api/v1/piece-fittings/31/      ← la del FITTING, amb 52 línies
200 GET /api/v1/size-checks/25/         ← la del CHECK, resol DESPRÉS i mana
```

La graella de fitting es quedava amb el `raw` del check —que no porta `pomRows`— i pintava
«Encara no hi ha mesures base» sobre una peça amb 52 línies, **amb la consola neta i la xarxa
tota a 200**. Un comptador de torn ho tanca (`.then`, `.catch` i `loading`). Amb el fix, **13 files**.

### El fix C1 del veredicte: **ja hi era; verificat, no refet**

Les quatre peces són a `617db73f`: `fittingGridAdapter.jsx:95-112` sembra de `line.decisio` ·
`onVeredicte` → `pieceFittingLines.update(lineId,{decisio})` · i **els dos comentaris rancis ja
estan esmenats** (`measureSources.jsx:87-89` en conserva l'acta).

### Contrast bloc a bloc

| bloc de la v3 | estat |
|---|---|
| Capa · codi en `--gold` · nom | ✅ |
| **La instància DINS del nom, en negre** («Armhole depth · Left») | ✅ |
| Els noms no es tallen mai | ✅ |
| Columna de treball `--sel`, valor en negreta amb el color del veredicte | ✅ |
| Segmented ACCEPTED · ADJUSTED · REJECTED | ✅ |
| Nota amb placeholder en cursiva | ✅ |
| Barra de recomptes amb «Sense decidir» | ✅ |
| Germana amb etiqueta i folgança | ✅ |
| Botó del full de fitting | ✅ |
| Històric paginat `‹ ›` de 2 en 2 | ✅ el codi hi és (`PaginadorHistoric`); el model 188 té **una sola presa** → apareix a partir de 3 |
| **Línia de dreceres** (`↓/Enter · ↑ · Tab · A · J · R · buit = no mesurat`) | ✅ **afegida** (`4b99ee72`); les tecles ja funcionaven i no ho deia res |
| ⚠️ Vocabulari de capes de la v3 (`Interlining/Binding/Knit/Reinforcement`) | ✅ **NO copiat**: mana D-31.22 |

**Divergències que queden — decisió d'Agus:**

1. 🚩 **La columna RÈGIM no és a la v3** i la pantalla la té (en lectura). No l'he tret: és la
   mateixa mena de decisió que la del punt 1, i la vull teva.
2. 🚩 **Etiquetes del grup:** la v3 diu grup «Fitting 04/08» + «Real · S»; la pantalla diu grup
   «S» + «BASE» / «FIT ACTUAL».

---

## U.5 · COMPROVACIÓ — construïda sencera (D-31.17) — commit `448ee468`

Abans: **cap tab, cap ruta, cap component.**

- **Entrada:** tercera subvista de Mesures (`Taula de mesures · Repàs de fittings · Comprovació`),
  que és on la maqueta la posa (`.sub2`). No és tab pròpia: el que comprova són les mesures.
- **Contracte:** `GET /api/v1/models/<id>/comprovacio/` — un de sol, perquè el veredicte de dalt
  és la suma del detall de sota i partir-ho arriscaria que no quadressin.
- **Consulta pura:** cap botó que escrigui; «veure →» porta a la taula.

### D'on surt cada secció amb el sistema d'AVUI

| secció | font real |
|---|---|
| Bloquegen l'enviament | `base_value_cm IS NULL` · POM sense `ModelGradingRule` resident |
| Van quedar enrere | només `MeasurementChangeLog`: última PRESA (`context ∈ fitting/checked`) contra l'últim canvi |
| Preses descartades | `SizeCheckLine.decisio='valor_descartat'` |
| Fora de tolerància | `PieceFittingLine` fora de la banda **de la FILA**, no la del catàleg |
| Famílies | `BaseMeasurement` per POM; folgança = exterior − folre quan totes dues hi són amb valor |

### 🚩 El que la maqueta demana i el domini NO té — **no s'ha simulat**

1. **BUIT DECLARAT AMB MOTIU** (`tr.gap`: «la germana es va proposar i es va treure: el coll passa
   sota l'aixella esquerra»). No hi ha manera de desar que una cara NO existeix ni per què. Les
   famílies ensenyen les cares que EXISTEIXEN i callen sobre les que no; el backend ho declara a
   `limitacions: ['buit_declarat_amb_motiu']` i la pantalla ho diu al peu.
   **Cal:** un `BaseMeasurementAbsent` (o `estat='DESCARTADA'` + `motiu` a `BaseMeasurement`) amb
   la seva porta d'escriptura.
2. **La nota per família** (`.fnote`). A la maqueta és text escrit a mà; no és cap dada. Omesa.
3. **El «tipus» de POM** (`Dimensió`/`Col·locació`). No existeix; s'hi ensenya `POMGlobal.categoria`,
   que és una altra taxonomia (`Upper body`, `LOSAN`).
4. **«3 de 4 cares»** implica saber quantes cares s'esperen. No existeix; s'hi diu «N cares».

---

## U.6 · Vista de família i Wizard — **NO tocats** (ordre d'Agus)

---

## U.7 · DADES · `AH-L`/`AH-R` → `AHL`/`AHR`

**Cens previ (tots els schemes de tenant):**

```
[fhort] 2 fila/es amb guió davant del sufix
    model 188 (BRW-SS27-0001) · bm 2102 · instància «left»  · 'AH-L' → 'AHL'
    model 188 (BRW-SS27-0001) · bm 2103 · instància «right» · 'AH-R' → 'AHR'
[los]   0 fila/es
TOTAL: 2 fila/es a 1 model.
```

**Script:** `backend/scripts_tmp/fix_sufix_instancia_guio.py` (untracked, com tot `scripts_tmp/`).

```
venv/bin/python manage.py shell < scripts_tmp/fix_sufix_instancia_guio.py     # cens
ACCIO=aplicar ...   |   ACCIO=desfer ...
```

- **No endevina per la forma del text:** només toca files on `nom_fitxa` acaba exactament en
  `-<sufix>` i el sufix és el que el **diccionari de BD** dona per a la instància d'aquella fila
  (un POM `T-SHIRT` no es converteix en `TSHIRT`).
- **Idempotent** (2a passada: «res a fer») i **reversible** amb `ACCIO=desfer`, que es basa en un
  rastre amb el valor d'abans i **omet** les files que algú hagi rebatejat pel mig.
- **Només toca el NOM** (`update_fields=['nom_fitxa']`).

**Executat i verificat** (cens → aplicar → idempotència → desfer → aplicar). Estat final:
`2102 'AHL'` · `2103 'AHR'`, `origen=MANUAL`, valors 23.2 i 23.0 intactes.

---

## U.8 · TANCAMENT · el contrast al navegador

**Banc:** `frontend/dist` REAL servit per un servidor propi que dona l'API des del `Client` de
test de Django amb `force_login` (el gunicorn viu rebutja els tokens del shell). **Escriptures
tallades** (eco) excepte les portes idempotents d'obertura. Idioma per `localStorage['fhort.lang']`.

| superfície | maqueta | contrast | consola | idiomes |
|---|---|---|---|---|
| Mesures `autoria_base` | v8.1 | ✅ bloc a bloc | neta | ca · es · en |
| Mesures `presa` | v8.1 + BASE VIGENT | ✅ bloc a bloc | neta | ca · es · en |
| **Fitting** (`CheckMeasureEditor` + `fittingSource`, `ModelSheet.jsx:830-836`) | fitting_v3 | ✅ bloc a bloc (13 files) | neta | ca |
| **Comprovació** | comprovacio_v2 | ✅ bloc a bloc (5 seccions · 11 famílies) | neta | ca · es · en |
| Vista de família | *descartada* | — | — | no tocada per ordre |
| Wizard de model | *pendent de validació* | — | — | no tocada per ordre |

Càrrega + F5 + navegació entre tabs amb la consola neta a tots els passos.

**Prova que el diccionari MANA les columnes:** s'ha afegit una instància a la BD
(`qa_sleeve_head`, sufix `SH`) i la píndola **«Sleeve head» apareix a la columna POSICIÓ sense
tocar cap fitxer de codi**. Esborrada després (queden 10). ⚠️ El límit: afegir una **opció** és
dada pura; afegir un **EIX nou** encara demana tocar `MeasurementInstance.EIX_CHOICES` +
`EIX_NOMS`, perquè l'eix no té taula pròpia.

**Cap escriptura del banc a la BD de staging**, verificat: sessió 147 `Oberta`, 10 instàncies,
13 mesures del model 188 amb els seus orígens.

---

## U.9 · La cua oberta

| # | què | on |
|---|---|---|
| 🚩 1 | `measurements_chat_view` té el mateix defecte d'`origen` que s'acaba de corregir a les altres dues portes | `models_app/views.py` ~2551 |
| 🚩 2 | La columna **RÈGIM del fitting** no és a la v3 — decisió d'Agus | `CheckMeasureEditor.buildLeadCols` |
| 🚩 3 | Etiquetes del grup del fitting («S / BASE / FIT ACTUAL» vs «Fitting 04/08 / Real · S») | `fittingGridAdapter` |
| 🚩 4 | **El buit declarat amb motiu** no existeix al domini: bloqueja la secció de famílies de la Comprovació i la «Vista de família» absorbida | model + endpoint nous |
| 🚩 5 | L'**EIX** d'instància no és una fila de BD (les opcions sí) | `MeasurementInstance.EIX_CHOICES` |
| 🚩 6 | El **diàleg de germana** s'ha eliminat (les dues branques tenen gest propi a la fila) | `EditableTable` |

---

**Cap push. Cap suite. `git add` selectiu a tots els commits.**
