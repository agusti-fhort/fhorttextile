# IMPLEMENTACIÓ · FIXOS DE LA FORMACIÓ, 1a TANDA (T1+T2+T4+T5) · 2026-08-26

> **5 commits a `fixos-formacio-1`, CAP PUSH.** Substrat:
> `docs/ordres/DIAGNOSI_FORMACIO_2026-08-26.md` (806 línies). Les línies hi eren: això és
> implementació, no diagnosi.

## PAS -1 · IDENTITAT, BASE I COORDINACIÓ

| Fet | Valor |
|---|---|
| `hostname` | `fhort-assessment` ✅ |
| `ftt-staging.service` · `WorkingDirectory` | `/var/www/ftt-staging/backend` ✅ |
| **HEAD de `dev` en començar** | **`cb23382e`** — *«merge: F4.1 · reconeixedor de peces v1»* (l'últim conegut del brief) |
| Worktree propi | `/var/www/ftt-form1`, branca **`fixos-formacio-1`**, creada des de `cb23382e` |
| Fil motor (`ftt-f41`) | worktree a `37339906`; **cap procés viu** en començar (`ps` net) |

### Intersecció amb l'arbre brut — VERIFICADA ABANS DE TOCAR RES

L'arbre de `/var/www/ftt-staging` tenia 4 fitxers modificats:
`DECISIONS.md` · `docs/ordres/IMPLEMENTACIO_SOBIRANIA_POM_2026-08-22.md` ·
`ops/maquetes/REPORT_CODA_BLOC_B.md` · `ops/qa/qa_f22_vocabulari_captures.py`.

**Intersecció amb els fitxers d'aquesta tanda: ZERO.** I res s'ha tocat des d'allà: tota la
feina va al worktree, que té índex propi. Tots els commits amb pathspec explícit.

### Divergència report ↔ codi: CAP

Les 12 citacions del report s'han verificat una a una contra `cb23382e`. Totes casen.
Única desviació: `etiqueta_casa` és a `wizard_views.py:**892**` (el report deia 891) — off-by-one
de citació, no de substància.

---

# F1 · T1 — ELS NOMS ARRIBEN I ES PINTEN

**Commit `e8af988f`.**

## Backend — un punt únic per als TRES camins

`_nom_resolt()` ([extraction_views.py](../../backend/fhort/models_app/extraction_views.py)), per
`noms_de` (la font única ÀLIES > TENANT > GLOBAL). Hi entren les files del pas 2, el suggeriment
feble i els candidats del 409: **resoldre'n uns i no els altres faria que la mateixa mesura es
digués de dues maneres segons la confiança del match.**

⚠️ **I les DUES consultes que el fan sostenible.** `_candidats_de_codi` passa a
`select_related('pom_global')`, i el camí d'**àlies** de `find_pom_master` —**l'ÚNIC de la funció
que no prefetchava el global**, mentre la resta de branques ja hi anaven— hi afegeix
`pom__pom_global`. Sense això, el fix comprava una query per fila.

## Front — la nomenclatura a DUES LÍNIES

`nomsDePom` a `ImportWizard.jsx`, el mateix resolutor que la fitxa i la taula de mesures. La
segona línia només surt si diu una cosa diferent (`nomsDePom` ja hi torna `''` quan repetiria la
primera): un gris que repeteix és soroll.

Cada secció del picker alimenta el resolutor amb **els seus** camps: a la del CLIENT mana la
seva nomenclatura —és la que el document porta escrita— i el canònic de la casa queda a sota; a
la de la casa, la de la casa.

I els noms resolts **viatgen amb la tria** (`onPick` · `onVincula` · «afegir del catàleg»): es
perdien allà, i el rètol «Es vincularà a {codi} · {nom}» tornava a quedar-se amb el codi pelat
encara que la llista acabés de pintar-lo bé.

**Cap canvi de dada.** Els 103 `nom_client` buits són dada legítima i no s'han tocat.

---

# F2 · T2 — LA POLÍTICA DE NÚMEROS

**Commit `3b769f0e`.**

## L'arrel: no era la funció, era el MOMENT

```jsx
value={esborrany.delta}                                 // el NÚMERO pinta el camp
onChange={e => toca({ delta: num(e.target.value) })}    // …i es parseja a cada tecla
```

`Number('1.')` és `1` → el camp es repinta «1» → **l'estat intermedi «1.» no és representable** i
no s'arriba mai al decimal. `num()` **ja acceptava la coma**: no era ella.

## El mòdul: `frontend/src/utils/num.js`

**Hi havia embrió i es diu `utils/format.js`** — té `formatLenNum` (locale-aware via
`toLocaleString`), `localeDeIdioma`, i **22 fitxers l'importen**. És, de fet, ja un punt únic per
a la PRESENTACIÓ DE LONGITUDS.

**Per què un fitxer nou i no allà dins:** `format.js` importa l'i18n, i per tant **no es pot
provar amb `node --test`**. Les regles pures han de poder córrer fora del navegador — la mateixa
raó per la qual `diccionariMesures.js` no importa res. `num.js` no importa res; `format.js` hi
beu i hi posa l'idioma actiu.

| Regla | Què fa |
|---|---|
| **R1** | `parseNum` — punt i coma indistintament, l'espai fi/no-separable d'un copiar-i-enganxar, i el separador de miler (amb dos separadors mana el de més a la dreta; amb un de sol **sempre és decimal**, perquè aquí els números són mesures i no imports). **Buit → `null`, mai zero.** |
| **R2** | `formatNum(v, {dec, lang})` — `ca`/`es` → coma, `en` → punt. **Sense separador de miler a posta**: un Δ amb un punt enmig es tornaria a llegir com un decimal en reentrar al camp. |
| **R3** | **NO s'hi entra en aquest sprint.** `formatNum(v, {lang:'en'})` és el que hi hauran de cridar. Inventari a l'annex. |

I `esNumeroEnCurs()`, que és el que permet **no pintar de vermell el que només està a mitges**:
`''`, `'-'`, `'1.'`, `'1,'`, `'-0,'`.

## Migrats

| Fitxer | Què |
|---|---|
| `EditorIntervals.jsx` | L'esborrany porta `delta_txt`; `confirma`, `potConfirmar` i l'avís al pare deriven el número del text |
| `JocsDeRegles.jsx` | El text va **a part** de `edicions` —que és el PATCH i el que llegeixen `relleuResidual` i els guards, i aquells volen el número—. Es retiren `num()` i `valorCamp()`, ja morts |
| `MeasureGrid.jsx` | Deixa de ser la implementació de **referència** (que és com es va arribar a set còpies) i passa a ser consumidor |
| `EditableTable.jsx` | Els tres punts d'entrada. Eren `parseFloat`, que de «12px» en treu 12 |
| `format.js:76` | El signe del delta es decidia amb `Number(abs.replace(',', '.'))`, i `toLocaleString` hi pot haver posat miler: `'1.234,5'` → `NaN` → **signe al costat fals per a qualsevol delta de quatre xifres** |

### ⚠️ UN MATÍS QUE LA FORMA DEL `NaN` AMAGAVA

`MeasureGrid.toNum` deia `null` al BUIT i `NaN` a la BROSSA, i **dos llocs es recolzaven en
aquella diferència**. `parseNum` diu `null` als dos casos —que és la resposta correcta a «quin
número és això?»—, o sigui que allà on la diferència importa ara es diu amb una condició escrita:

* `esBrossa()` al commit — **el buit ESBORRA la mesura, la brossa no ha de desar res**. Amb el
  canvi cec, teclejar brossa hauria esborrat la mesura.
* `v === null` a la tolerància — `null < x` es llegiria com `0 < x` i hauria pintat **fora de
  tolerància** una entrada a mitges (amb `NaN` tota comparació era falsa i queia sola).

---

# F3 · T4 — EL REFÚS ACCIONABLE

**Commit `684a007b`.**

## El backend ja ho sabia tot i ho llençava en un `return`

`pom_del_codi` feia la consulta sencera —`select_related('pom')` inclòs— i es quedava **només
amb `alias.pom`**. Ara la consulta és `alies_del_codi()` i `colisio_de_codi` en torna el CONTEXT:
`client_code` (amb la caixa del client), `pom_id`, `pom_codi`, `pom_nom` resolt, `origen`,
`origen_llegible`, `pendent_revisio`, `es_instancia`, descripcions, `editat_at`.

⚠️ **La signatura passa de `(pom, etiqueta)` a `(pom, etiqueta, context)` i els DOS cridadors
s'han tocat alhora a posta**: és justament el que fa que el missatge sigui **un de sol** vingui
d'on vingui.

## La tautologia — l'arrel compartida amb T1

`_etiqueta` començava per `pom.nom_client`. A `gravar-pom` hi havia fallback al global i se
salvava per poc; als **7 POMs sense cap nom enlloc** queia a `codi_client` i el refús es llegia
**«BT» ja és BT**. I la porta germana era pitjor: `create_model_pom_view` feia
`(ja_hi_es.nom_client or codi_casa)` **sense cap fallback** — tautològic per als 103 sempre.

## La frase, una i compartida

`frase_de_colisio()` viu a `nomenclatura.py` i **no a cap vista**, perquè les dues portes que
refusen per aquest motiu han de dir el mateix:

> «BT» ja és Leg opening girth del diccionari del client BRW, pendent de revisió. Fes-lo servir
> des del cercador, revisa'l al catàleg, o dona-li una nomenclatura diferent.

* **Diu amb què xoca I què es pot fer** — la doctrina que `create_model_pom_view` ja tenia
  escrita al seu propi comentari i que `gravar-pom` no havia rebut.
* La sortida «revisa'l» **només s'ofereix si hi ha res a revisar**: oferir una sortida que no
  porta enlloc és pitjor que no oferir-ne cap.
* El codi es diu **amb la caixa del CLIENT** (la comparació és `iexact`, la unique és
  `upper(codi_client)`): qui ha escrit «bt» ha de veure que el que hi ha es diu «BT», o el refús
  sembla que no parli del que acaba de fer.

## El 400 i el modal

400 estructurat (`codi: NOMENCLATURA_OCUPADA` + `colisions[]`) imitant el 409 germà, **amb
`errors[]` conservat** perquè cap lector antic es quedi mut.

Front: **el modal ja no es tanca**. És un conflicte amb una dada que ja hi és, no una fallada del
desat. Cada col·lisió és una **fila llegible**; res d'aplanar amb `' · '`. El payload es conserva
per reintentar — per això la neteja de `confirmRef`/`pendingPayloadRef` surt del `finally` i es
fa a **cada sortida menys aquesta**.

**i18n:** 2 claus noves amb paritat `ca`/`es`/`en`.
**Cap consulta nova:** el nom del client es demana **un cop per petició**, no per fila.

---

# F4 · T5 — LA TRADUCCIÓ EN LOT

**Commit `cf494f7c`.**

## Front — trossejat a la cua

`buida()` agafava el `Set` sencer d'un idioma i el passava en UNA crida. Ara trosseja
(`MAX_PER_PETICIO = 200`) i els lots van **seqüencials**: cada petició ja dispara diverses crides
al proveïdor al servidor (50 textos per crida), i obrir-ne dues alhora multiplicaria la ràfega
contra un tercer sense guanyar res a una pantalla que pinta la ⓘ a mesura que arriba.

**200 i no 300 a posta:** el client no ha de saber el número exacte del servidor, només quedar-hi
per sota amb marge.

⚠️ **I el `catch` deixa de reintentar els 4xx.** Es desmarcaven SEMPRE els ids —correcte per a un
tall de xarxa—, però per a un refús de la porta era una repetició garantida a cada entrada a la
pantalla, sempre amb el mateix resultat i **sempre en silenci**.

## Backend — UNA política

La vista rebutjava per sobre de `MAX_IDS` **i** el servei truncava amb `[:MAX_IDS]`: dues
respostes per al mateix sostre, cap decidida. La del servei era codi mort, però deia el contrari
de la porta — i si algun dia hagués manat, hauria respost **200 OK amb un terç de la resposta que
falta i sense dir-ho**.

**Decisió:** s'accepta fins a `MAX_IDS` (inclusiu) i es refusa per sobre amb un error que parla
(`codi: MASSA_POMS`, `max`, `rebuts`, i un `detail` que **diu el número** perquè un client el
pugui trossejar sense endevinar-lo). El truncat silenciós desapareix. *Un número que menteix és
pitjor que un error que parla* — la mateixa llei que va motivar `totesLesPagines`.

I es corregeix el comentari de `MAX_IDS`, que deia «l'univers real són 142 POMs»: `/poms` **és**
la pàgina sencera del catàleg, legítimament, i algun tenant ja ha passat de 300.

⚠️ **No es reprodueix a staging** (`fhort` 144 POMs · `los` 0): cal un catàleg de >300. Per això
els tests van amb **ids sintètics** i **contra la vora**.

---

# GATE (proporcional)

| Bloc | Resultat |
|---|---|
| `manage.py check` (backend tocat) | **no issues** |
| Suite dirigida — `test_tram_i_traduccio` · `test_sobirania_nomenclatura` · `test_sobirania_copy_on_write` · `test_guarda_rang_mesura` · `test_c4_escriptura_germanes` · `test_set2_t5_escriptors` · `test_origen_no_es_efecte_secundari` | **Ran 90 tests · OK** |
| Tests NOUS de backend — `test_f_formacio_1` + `test_tram_i_traduccio` | **Ran 35 tests · OK** |
| `node --test` (num · cua · wizard · diccionari · nomenclatura · gradingRegime) | **130 tests · 130 pass · 0 fail** |
| `npx eslint` (11 fitxers tocats) | **0 errors** |
| `npx vite build` | **✓ built** |
| Fum F1 · wizard amb noms a dues línies | **15 ✓ · 0 ✗** |
| Fum F2 · break amb decimals | **9 ✓ · 0 ✗** |

**Cap suite sencera.** Cap correguda simultània (mai dues alhora). `FTT_TEST_DB=test_ftt_form1`.

## 🚨 ELS DOS FUMS S'HAN VIST VERMELLS ABANS DE DONAR-LOS PER BONS

Contra el component d'abans del fix, amb el bundle reconstruït i restaurat després:

| Fum | En vermell deia |
|---|---|
| F2 | teclejant «0,75» el camp retenia **«75»** — el separador engolit i els dígits concatenats |
| F1 | les files del desplegable sortien **sense cap nom**; 7 de 15 assercions vermelles |

## 🚨 I LES DUES SONDES VAN NÉIXER MENTINT

Queda escrit al costat de la línia que ho arregla, a cada script:

* **F2** agafava `input[inputmode="decimal"]` amb `.first` i queia sobre el **Δ BASE** de la fila
  (que ja porta el 2 del payload): teclejar-hi «0,75» donava «0,752» — **un vermell que semblava
  del defecte i era de la sonda**. Ara es localitza per `aria-label`.
* **F1** mesurava sobre el `body` sencer, i «Foot width» hi surt **també** per la llista del pas 2
  (que ve de la meitat backend de F1): la prova del nom canònic **passava amb el front vell**. Ara
  es mesura dins del desplegable i fila a fila. En tancar aquell forat en va aparèixer un segon
  —el localitzador de files només casava dos dels tres noms— i el tercer no es mesurava.

## Captures

`ops/qa/captures/` és a `.git/info/exclude` (evidència, no font). Generades:
`f1_00_pas2.png` · `f1_01_dues_linies.png` · `f2_00_graduacio.png` · `f2_01_coma.png` ·
`f2_02_punt.png` · `f2_03_confirmable.png`.

---

# FORA D'ABAST (declarat)

* **T3** — taxonomia de famílies: espera les 3 decisions d'Agus (on van CF/CB · l'ordre de la
  tupla `SUBEIXOS` · quina família gira la complementària).
* **R3** — documents tècnics (fitxa/PDF/Konva): només inventari (annex).
* **POMBrowser** (`page_size: 1000`) — 2a pantalla exposada a T5, però és morta (G4).
* **Cap push.**

## 🚩 QUEDA OBERT, I NO ÉS D'AQUESTA TANDA

* **L'ordre canònic d'instància el decideix un atzar alfabètic** (`'ESTAT' < 'POSICIO'`),
  load-bearing per a 10 uniques. És independent de T3 i es pot tancar sol.
* `format.js` i `num.js` **encara són dos punts** per a la presentació: el primer per a longituds
  (amb decimals per unitat i conversió), el segon per a números en general. Convergeixen a la 2a
  passada; avui `format.js` ja beu de `num.js` per al parseig.

---
---

# ANNEX · D0 — INVENTARI DE NÚMEROS AL FRONT

> Cens per `grep` sobre `frontend/src`. **El tall de la 2a passada es declara al final.**

## (a) ENTRADA

### a1 · `type="number"` — **38 ocurrències / 16 fitxers**

`type=number` **rebutja la coma segons locale abans d'arribar a `onChange`**: és la primera cosa
que la política R1 prohibeix.

| Fitxer | n | Què són | Acció |
|---|---:|---|---|
| `pages/TechSheetEditor.jsx` | 14 | geometria del llenç (mides, angles, fontSize) | **2a passada** (R3) |
| `pages/WorkOrderDetail.jsx` | 4 | imports i quantitats | **2a passada** (comercial) |
| `components/ImportWizard/ImportWizard.jsx` | 4 | 1 mesura (`step 0.1`) + 3 encongiment | **2a passada** |
| `pages/ModelFabric.jsx` | 3 | encongiment (`step 0.5`) | **2a passada** |
| `pages/DeliveryNoteDetail.jsx` | 2 | quantitat i preu | **2a passada** (comercial) |
| `SizeSetDetail` · `OrderDetail` · `CustomerForm` · `TaskAssignWizard` · `TimeTree` · `SewEditor` · `TempsDeclaratForm` · `ModelsFilterPanel` · `CronoDeclarat` · `ActionsMenu` · `TechSheetTemplateEditor` | 1 c/u | quantitats, durades, fontSize | **2a passada** |

### a2 · Parsers locals — **10 ocurrències**

| Fitxer:línia | Acció |
|---|---|
| `components/grading/EditorIntervals.jsx:102` | ✅ **migrat ara** |
| `components/grading/JocsDeRegles.jsx:300` | ✅ **migrat ara** |
| `components/model/MeasureGrid.jsx:53` | ✅ **migrat ara** |
| `components/EditableTable/EditableTable.jsx:279 · 302 · 1838` | ✅ **migrats ara** |
| `utils/format.js:76` | ✅ **migrat ara** (i era un bug latent) |
| `components/grading/GraduacioSuperficie.jsx:121` | **conforme** — ja desa el text cru i parseja al submit (`:309`). Consolidar a la 2a passada |
| `utils/gradingRegime.js:63` · `utils/plausibilitatMesura.js:30` | **conforme** — no són inputs, són validadors de domini |

## (b) PRESENTACIÓ

### b1 · `toLocaleString` (idioma-aware) — **2 ocurrències, totes a `utils/format.js`**

`formatLenNum:55` · `formatDelta:72`. **Conforme**: ja és un punt únic i ja respecta l'idioma.
🚩 Convergeix amb `num.js` a la 2a passada (avui difereixen en el separador de miler).

### b2 · `toFixed` (SEMPRE punt) — **33 ocurrències / 22 fitxers**

| Grup | Fitxers | Acció |
|---|---|---|
| **Documents tècnics** (R3) | `ExportModal` · `FittingPrintSheet` · `TechSheetEditor` · `PatternViewer` · `PieceList` · `PieceIdentityList` · `DartProposalsPanel` · `fittingShared` | **conforme a R3** — el punt hi és correcte. No es toquen |
| **Comercial** (imports) | `QuoteDetail`(4) · `OrderDetail`(3) · `WorkOrderDetail`(2) · `Quotes` · `Orders` · `DeliveryNotes` · `DeliveryNoteDetail` · `PaymentTerms` · `CustomerDetail` | **2a passada** — és una política de MONEDA sencera, no de separador |
| **Ni decimal ni locale** | `fileMeta`(2) · `FileDropCard`(2) · `UnitToggle` · `OnboardingWizard` · `taulesQ8` | **conforme** — mides en MB, percentatges de progrés |

## 🔪 EL TALL DE LA 2a PASSADA — DECLARAT

**Aquesta tanda migra NOMÉS l'entrada de la família graduació/mesura**: els inputs on el defecte
diagnosticat viu, més els seus germans directes. **6 fitxers, 8 punts.**

**Queda fora, i per què:**

1. **La flota de `type="number"` (38)** — cada un vol decidir si el seu camp admet decimals i amb
   quina precisió (una quantitat en unitats no és un preu ni un encongiment). Migrar-los en bloc
   seria canviar 16 pantalles a cegues.
2. **La presentació comercial (`toFixed` d'imports)** — és una política de MONEDA (símbol,
   posició, decimals per divisa, arrodoniment), no de separador decimal. Barrejar-la amb R2 aquí
   faria una decisió de negoci per la porta del darrere.
3. **R3 (documents)** — el brief l'exclou explícitament.
4. **`GraduacioSuperficie.jsx:121`** — ja compleix la política; consolidar-lo és neteja, no fix, i
   arrossegar-lo aquí eixamplaria el diff sense arreglar res.

**El criteri del tall:** en aquesta tanda entra el que **el defecte de la formació toca** i el que
**s'hi assembla prou per tornar a petar demà** (el Δ base dels jocs de regles, que no era al brief
i tenia el defecte exacte). La resta és una passada pròpia amb decisions pròpies.
