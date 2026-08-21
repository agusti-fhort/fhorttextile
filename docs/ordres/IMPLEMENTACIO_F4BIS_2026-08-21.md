# IMPLEMENTACIÓ F4-BIS · LA COLUMNA «BREAKS» AMB XIPS D'INTERVAL

**Data:** 2026-08-21 · staging, branca `dev` · **cap push**
**Abast:** UI-only. El motor no es toca, la porta no es toca, cap migració, cap camp nou.
**Disseny llei:** `docs/ordres/proposta_ux_intervals_mesures.html` (adaptat, no redissenyat).
**Substrat:** `IMPLEMENTACIO_EF_MOTOR_2026-08-21.md` §F4 — les sub-línies que això jubila.
**Gate:** `ops/qa/banc_paritat_1383.py` (3 blocs) abans i després.

---

## 0 · EL GATE, ABANS I DESPRÉS

```
ABANS   A=✔(105)  B=✔(525)  C=✔(4)
        HASH JOC       096990db404b778a2140fffd8327c54294849b73d42ec67b3265247f9840989f
        HASH RESIDENTS 6e55bc1360630b9e3019c7c2d2265df445adffddef16a4780ae8c9a1f1f8b6b4

DESPRÉS A=✔(105)  B=✔(525)  C=✔(4)   ·  ELS DOS HASHOS IDÈNTICS
```

**Cap cel·la moguda, cap STOP.** Era el que havia de passar —això és UI— i el banc ho
ratifica: la columna canvia de DIBUIX, no de VALOR.

---

## 1 · QUÈ CANVIA, I ON

Les **dues** superfícies d'autoria de regla substitueixen dues columnes per una:

| Superfície | Fitxer | Abans | Ara |
|---|---|---|---|
| **Graduació del model** (Mesures) | `GraduacioSuperficie.jsx` | 9 columnes · `Δ BREAK` + `TALLA BREAK` + sub-línies | **8 columnes · `BREAKS`** |
| **Generar regles** (joc del catàleg) | `JocsDeRegles.jsx` | 8 columnes · idem | **7 columnes · `BREAKS`** |

El component és **un de sol** (`ColumnaBreaks`, a `EditorIntervals.jsx`), com ho era
`BotoAfegirInterval`/`FilesIntervals`, que es jubilen. Les sub-línies del tram F desapareixen:
la fila torna a ser una fila.

**La CONSULTA (`EditableTable`) es queda com estava** —les seves dues columnes de lectura i la
talla en convenció de DOCUMENT— i és a posta: allà no s'edita res, la lectura compacta hi cap,
i és la pantalla que el client reconeix del seu propi full.

### Per què una columna i no dues

«Δ break» i «Talla break» eren **la meitat cadascuna d'UN sol trencament**: s'havien de llegir
juntes, no en sabien dir més d'un, i parlaven en convencions diferents (la talla en convenció
de DOCUMENT, el delta cru). El xip diu el trencament **sencer** —«de la M a la XL creix 3»— i
en diu N.

I hi ha un guany que no és d'espai: **amb la columna de la talla fora d'aquestes dues
pantalles, l'ambigüitat de convenció desapareix d'aquí**. Ja no hi ha cap control al costat que
parli en convenció de document i pugui contradir el xip. El risc que `breakConvention.js:18`
avisa —«una superfície que en faci servir només una menteix»— es tanca per construcció en
comptes de per disciplina.

---

## 2 · ELS SIS ESTATS

Els sis del mockup, tal qual, i amb captura de cadascun
(`ops/qa/captures/f4bis_*.png` — fora de git per `.git/info/exclude`):

| | Estat | Captura |
|---|---|---|
| ① | LINEAR sense relleu → només `[+]` | `f4bis_1_sense_relleu.png` |
| ② | break d'1 tram desat → xip `M → XL +3` | `f4bis_2_break_llegat.png` |
| ③ | dos intervals → dos xips + `[+]` | `f4bis_3_dos_intervals.png` |
| ④ | xip en edició → dos selectors + Δ + ✓/✕ | `f4bis_4_edicio_inline.png` |
| ⑤ | al màxim → tres xips + «màx. 3», sense `[+]` | `f4bis_5_maxim.png` |
| ⑥ | FIXED → columna **buida del tot** (⚠️ esmena de §8.2: el mockup hi deixava un `[+]` apagat) | `f4bis_6_fixed.png` |
| — | la taula sencera (Graduació) | `f4bis_0_taula_sencera.png` |
| — | la MATEIXA columna a «Generar regles» | `f4bis_7_generar_regles.png` |

**Tokens reals en lloc dels placeholder del mockup, i cap color nou:**
`--border` · `--white` (era `--card`) · `--text-soft`/`--text-muted` (era `--soft`) · `--gold`
· `--sel` · `--ok` · `--err` (era `--danger`) · `--r-pill` (era `999px`) · `--r-ctrl` (era
`6px`). Icones Tabler outline (`ti-plus`, `ti-check`, `ti-x`), com mana la casa.

**Detalls del comportament que valen la pena:**

- **inici=final es pinta AMB fletxa igualment** («XL → XL · +4»): gramàtica única, com demana
  l'ordre. Si la Montse ho vol compacte, és una línia.
- **El xip és un `span` amb DOS botons germans**, mai un botó dins d'un botó: és HTML invàlid i
  el clic de dins queda mort. És el defecte exacte que QA-TALLER-C va caçar a la llista de POMs
  amb la «i».
- **Al màxim el `[+] `desapareix i ho diu** («màx. 3»). Un control apagat que ningú pot fer
  servir ocupa el lloc d'una explicació.
- **L'esborrany NO és la regla.** El xip que s'edita viu a l'estat del component; només el ✓ el
  fa entrar a la llista. Conseqüència volguda: **un interval a mitges ja no pot bloquejar el
  «Gravar»** —no hi arriba mai—. `intervalsIncomplets` es queda com a xarxa per a llistes que
  vinguin d'un altre camí.
- **Els intervals confirmats s'ORDENEN** com els desarà `valida_breaks` (per posició d'inici).
  La pantalla no pot dir un ordre i la BD guardar-ne un altre; sense això, un xip afegit al
  final d'una llista que comença per la S es llegia com si el relleu anés a salts.

---

## 3 · LES DUES DECISIONS QUE NO ERAN COSMÈTIQUES

### 3.1 · Un break d'1 tram es LLEGEIX com un interval — i no és cap conversió

`intervalsVisibles(rule, run)` (`utils/gradingRegime.js`) és el **mirall de
`grading_utils.intervals_de`**: torna el relleu com a llista d'intervals vingui de `breaks` o
de `talla_break_label` + `increment_break`, que es llegeix com `[label .. última talla del
run]`. Amb les dues formes mana `breaks`, com al motor.

🚨 **L'etiqueta NO es desplaça.** La BD desa convenció de MOTOR i el xip la diu tal qual.
Desplaçar-la a convenció de document mouria la corba **una talla sencera** — 33 de les 105
cel·les del banc, que és el contra-experiment que el tram F ja va fer i deixar escrit.

Això vol dir que **pintar el xip no toca res**: la BD no es mou fins que un gest humà edita
aquell xip. Les 21 regles d'1 break del banc canvien de dibuix i de res més.

### 3.2 · Una regla no pot quedar-se amb DUES formes

L'ordre diu «editar-la escriu la forma nova (breaks)». S'ha implementat literalment:
`escriuBreaks` envia `breaks` **i buida `increment_break` + `talla_break_label`** a la mateixa
crida, però **només quan el relleu que es veia sortia NOMÉS de la forma vella**
(`relleuLlegat`).

**Per què buidar-los i no deixar-los.** El motor sabria què fer-ne (`breaks` mana), però els
dos camps seguirien dient un trencament que ja no governa i que **altres superfícies encara
llegeixen** —la consulta, la fitxa, un import futur—. Un fòssil així no és inofensiu: és una
segona veritat sobre la mateixa regla.

**Per què això no és una migració.** Cap regla que ningú toqui es mou. És la conseqüència d'un
gest humà sobre aquella regla concreta — i el banc, verd amb els dos hashos intactes, ho
ratifica sobre 142 regles i 630 cel·les.

**I està PROVAT que no mou cap valor** (§4, prova ①): es gradua un break d'1 tram, s'envia el
payload de F4-BIS i es torna a graduar; les cinc talles surten idèntiques. Sense aquesta prova,
«editar el xip escriu la forma nova» seria indistingible de reescriure graduació en silenci.

### 3.3 · El solapament no es pot TECLEJAR

Els dos selectors només ofereixen **talles lliures**: l'inici, les que cap altre interval
cobreix; el final, des de l'inici **endavant** i fins al primer tram ocupat. Amb això
`BREAKS_SOLAPAMENT` i `BREAKS_ORDRE` deixen de ser errors possibles d'aquesta pantalla — no és
que es validin millor, és que no es poden construir.

**La porta del servidor es queda igualment**, i quan parla, parla **al mateix control**: un
`BREAKS_*` es pinta sota els xips de la fila que el va provocar, no a la barra de peu (patró de
la porta de `valors_step` a la columna «Mesura» de l'Escalat). Amb el missatge només al peu, qui
havia tocat sis files havia d'endevinar quina.

---

## 4 · QA

### 4.1 · La pantalla — `ops/qa/qa_f4bis_columna_breaks.py` · **27/27** ✅ *(30/30 amb l'addenda, §8.3)*

Sense JWT (l'agent no en pot emetre; els dos del disc són de juliol i del 6 d'agost). Reusa el
patró de `qa_mount_modelsheet.py`: serveix el **bundle REAL de `frontend/dist`** —el mateix que
nginx publica— i stubeja només el payload. El component, el CSS i els tokens són els de
producció.

Cobreix els **sis estats a les DUES superfícies**, condueix el gest sencer (obrir · escriure Δ ·
✓ · ✕) i comprova el que més importa:

```
🚨 l'inici NOMÉS ofereix talles lliures (XS)         ← amb S→L i XL→XL ocupats
🚨 el final s'atura abans del tram ocupat (XS)
🚨 «Generar regles»: l'inici només ofereix les talles lliures (XS)
```

**Un defecte de veritat caçat a la primera correguda:** el ✓ era alhora *enabled* i *not
visible*. Un botó només-icona sense `minWidth`/`minHeight` mesura **0 d'alçada** mentre el
webfont Tabler (que ve d'un CDN, `index.html:8`) no ha carregat — i llavors no té diana.
Corregit al component, no al test. *(El fum també hi va caure: el catch-all de `page.route`
servia `index.html` a la petició del CDN i deixava el bundle sense cap glif.)*

### 4.2 · El payload, per les portes reals — `ops/qa/qa_f4bis_staging.py` · **18/18** ✅ *(30/30 amb l'addenda, §8.3)*

Sobre el model de prova **1384** (`QA-TRAMF-0001`). **El banc 1383 no s'hi toca.**

| | Prova | Resultat |
|---|---|---|
| ① | break d'1 tram graduat → payload F4-BIS → re-graduat | 🚨 **CAP CEL·LA S'HA MOGUT** · `XS 98 · S 100 · M 103 · L 106 · XL 109` abans i després |
| ② | la regla queda amb UNA forma | `breaks` poblat · `increment_break` i `talla_break_label` a **NULL** |
| ③ | afegir · editar · treure | dos intervals → `XS 98 · S 100 · M 103 · L 105 · XL 109` · llista buida → es desa **NULL** · sense relleu torna al Δ general |
| ④ | les cinc portes | 400 amb el codi exacte: `BREAKS_SOLAPAMENT` · `BREAKS_ORDRE` · `BREAKS_TALLA_FORANA` · `BREAKS_DELTA_REDUNDANT` · `BREAKS_MAX` |
| ⑤ | el banc | 0 regles amb intervals nous · les 103 d'1 break senceres |
| ⑥ | **el mirall front↔motor sobre les 21 files VIVES del banc** | **21/21 idèntiques** |

**⑥ és la prova que un banc de JS no pot fer sol.** `intervalsVisibles` declara ser el mirall
d'`intervals_de`; un banc de JS el prova contra fixtures que he escrit jo. Això el prova contra
les 21 regles que la pantalla pintarà demà, amb el motor real a l'altre costat. Si els dos
deixessin de dir el mateix, la columna dibuixaria un relleu i el motor en graduaria un altre —
en silenci, i sense que cap build ho pogués veure.

### 4.3 · La resta del verd

| Control | Resultat |
|---|---|
| `node --test` · `gradingRegime.test.js` | **15/15** (9 casos nous: el llegat, l'ordre, les talles lliures, el sostre) — **21/21** amb l'addenda |
| `node --test` · tots els bancs de `src/utils` i `src/components` | verds |
| `npx eslint src` | **0 errors** (270 warnings preexistents) |
| `npm run build` | net |
| `manage.py check` | net |
| `banc_paritat_1383.py` | ✅ A=105 · B=525 · C=4 · els dos hashos idèntics *(⚠️ el segell de residents es mou més tard, per una escriptura que no és d'aquesta sessió: §8.4)* |

---

## 5 · 🚩 EL QUE CAL SABER, I QUE L'ORDRE NO PODIA PREVEURE

### 5.1 · Les 21 del banc es pinten «M → **3XL** +d», no «M → XL +d»

L'ordre esperava «X → XL · +d». **El que surt és `M → 3XL`**, i és correcte:

> `run_sistema` de 1383 és **`ALPHA_EU_W`**, que va de la **XXS a la 3XL**. El run del MODEL
> (XS·S·M·L·XL) n'és un subconjunt. El motor resol el relleu en **espai de SISTEMA** (llei
> S24b) i per tant el final d'un break d'1 tram llegit com a interval és **l'última talla del
> sistema**, no la del model. Va quedar escrit al tram F: «un interval acabat a 3XL (la forma
> canònica de tota regla d'1 break llegida com a interval)».

O sigui: `M → 3XL` és **el que el motor llegeix de debò**, i pintar `M → XL` seria dir una cosa
que el motor no fa. La conseqüència pràctica —el xip menciona dues talles que aquell model no
fabrica— és real i **és decisió d'Agus** si es vol acotar la presentació al run del model. No
s'ha tocat: acotar-ho voldria dir que el xip i el picker parlessin d'espais diferents, que és
exactament el forat que el tram F va tancar.

El mateix parany em va enxampar a mi escrivint la QA: la primera versió esperava un **400
`BREAKS_TALLA_FORANA`** per a un interval acabat a `XXL` sobre 1383, i el **200 tenia raó ell**.
«Forana» és respecte del sistema, no del run.

### 5.2 · La TERCERA superfície segueix escrivint la forma vella

`CheckMeasureEditor.jsx` (l'editor de regles del Size Check) **encara autora
`increment_break` + `talla_break_label`** (`:152-153`) i no coneix els intervals. El tram F ja
ho havia anotat com a seguiment; després de F4-BIS pesa una mica més, perquè ara les dues
superfícies principals parlen intervals i aquesta segueix creant regles d'1 tram.

**No s'ha tocat** (l'ordre nomena exactament dues superfícies). No és una avaria: el motor
llegeix les dues formes i F4-BIS pinta les dues igual. És **paritat d'autoria pendent**.

### 5.3 · QA de navegador contra staging: segueix pendent

L'agent no pot emetre el JWT (classificador de permisos; els dos tokens del disc són
caducats). El que s'ha pogut mesurar sense navegador autenticat s'ha mesurat amb el **bundle
real** (§4.1) i amb les **vistes reals** (§4.2), que travessen la porta sencera menys nginx.
🚩 **El passi visual d'Agus a les dues pantalles queda obert**, com a W5.

---

## 6 · EL QUE NO S'HA TOCAT (i per què)

- **El motor, la porta i les migracions.** F4-BIS és UI: `valida_breaks`, `intervals_de`,
  `increment_de_l_aresta` i les quatre portes segueixen exactament com les va deixar el tram F.
  **Cap endpoint nou** — es va censar primer, com demanava l'ordre: `set_pom_regim_view` i
  `GradingRuleSerializer` ja acceptaven `breaks` des de F3+F5.
- **`EditableTable`** (la consulta i la gènesi) conserva `Δ break` + `Talla break`. L'únic canvi
  és una entrada nova a `AMPLADES` (`breaks: 200`), que és el registre compartit d'amplades i
  per tant on toca.
- **`G5`**: en mode fitting el règim segueix ocult i els xips no hi apareixen. La columna només
  la munten les dues superfícies d'autoria.
- **`resumBreakQ8` i la taula d'Escalat de la fitxa** (Q8b): intactes. La frase compacta
  (`+2,0 · S→L +3,0`) surt d'`etiquetaRegla`/`taulesQ8`, que no s'han tocat i els bancs dels
  quals segueixen verds.
- **`talla_break_pos`**: segueix sent columna morta. Els intervals no en tenen equivalent i no
  se n'ha fabricat cap.
- **`DECISIONS.md`**: no s'hi ha escrit res (llei §1, i en aquest moment el toca una altra
  sessió). La llei d'aquest tram viu al codi (`ColumnaBreaks`, `intervalsVisibles`) i aquí.

---

## 7 · COMMITS (locals, `dev`, **cap push**)

| Commit | Concern |
|---|---|
| `af6f42b2` | **utils** · `intervalsVisibles` (mirall d'`intervals_de`) + l'aritmètica de talles lliures + 15 proves de `node --test` |
| `93b85ccc` | **UI** · `ColumnaBreaks` a les dues superfícies · les dues columnes velles fora · i18n ca/en/es |
| `7b702ddc` | **QA** · el fum dels 6 estats (27) i la QA del payload sobre staging (18) |

`1.304 insercions · 233 supressions · 11 fitxers.`

**⚠️ El `npm run build` del verd ja ha desplegat la SPA a staging** (nginx serveix
`frontend/dist`). El que hi ha en viu a `staging.fhorttextile.tech` és aquesta columna.

---

# 8 · ADDENDA (mateix dia) · EL PASSI VISUAL D'AGUS

Dues ordres seguides després del passi visual sobre el banc 1383: **el guard cec als intervals**
i **la regla del silenci dels xips**. La segona resol el símptoma; la primera, com es veurà, no
tenia el diagnòstic que semblava.

## 8.1 · 🚨 EL GUARD NO ERA CEC — i cal dir-ho, perquè el fix hauria estat al lloc equivocat

L'ordre deia: «Causa: el guard llegeix els camps vells; F4-bis els BUIDA en editar i escriu
breaks — el guard no mira breaks». **Mesurat, i és fals.**

`es_linear_degenerada` **ja llegia `breaks` des del tram F** (`grading_regime.py:336-338`), i
els **SIS** cridadors ja li passaven `rule.breaks` (les quatre portes + les dues sembres). La
matriu, en fred:

| cas | guard | `valida_breaks` |
|---|---|---|
| **`ib=0` · `brk=None` · intervals vius** | **ok** | **ok** |
| `ib=0` · `brk=2` (llegat) · sense breaks | ok | ok |
| `ib=0` · `brk=0` (llegat) · sense breaks | DEGEN | ok |
| `ib=0` · breaks tot a zero | DEGEN | `BREAKS_DELTA_REDUNDANT` |
| `ib=0` · sense res | DEGEN | ok |

I per la porta REAL, sobre la F del 1383 amb el payload exacte de F4-BIS: **200**, amb els
intervals desats i els camps llegats a NULL. El gest sencer conduït sobre el bundle real
(editar el xip → afegir-ne un → Gravar) **també passa**, i el POST que surt és el correcte.

**No he pogut reproduir el 400 amb el codi al disc, i ho dic en comptes de tapar-ho.** El que
sí que he trobat és el que el fa versemblant, i és el que la segona ordre ataca (§8.2): la
pantalla pintava xips que no diuen res, tocar-ne un fa entrar la fila al lot del Gravar, i el
missatge de degenerada **no deia quina fila era** — de manera que barrava el lot mentre el que
tenies a la mà era una ALTRA regla. Això últim ja està arreglat: ara el missatge les nomena.

**Sí que hi havia una cosa a arreglar al front, i era estructural:** hi havia **TRES**
implementacions d'una sola llei — el backend, el mirall declarat (`gradingRegime.js`) i una
**còpia local transcrita a mà** dins `GraduacioSuperficie.jsx`. Cap mentia avui; la tercera és
la que un dia diria una altra cosa. Retirada: la fila consulta el punt únic. La llei queda
escrita, amb la formulació d'Agus, al docstring del guard (cap canvi de comportament: la matriu
és idèntica abans i després).

## 8.2 · LA REGLA DEL SILENCI — el que Agus tenia a pantalla

Al banc 1383 hi ha **vuit** files —`E5`, `E7`, `EK`, `EK1`, `EK2`, `G1`, `SLT`, `U`— que són
**`FIXED` amb `brk=0 · break M` residuals** de quan eren LINEAR. Cadascuna pintava un
`M → 3XL +0` amb el seu ✕.

| | Regla | On viu |
|---|---|---|
| ① | Sota un règim que no gradua, **cap interval i cap `[+]`** — la columna calla sencera | `intervalsVisibles` + `ColumnaBreaks` |
| ② | Un tram que **repeteix el delta que ja mana** no és un trencament i no es pinta | `intervalsVisibles` |
| ③ | El `[+]` segueix a **LINEAR** encara que no hi hagi cap xip | `ColumnaBreaks` |
| ④ | **Desar un FIXED neteja el relleu** (intervals + els dos camps llegats) | `relleuResidual` a les dues superfícies |

**ABANS / DESPRÉS de la mateixa franja** (`ops/qa/captures/f4bis_8_silenci_abans.png` i
`f4bis_9_silenci_despres.png`, capturades amb DOS bundles reals — el de l'«abans» construït a
`/tmp` per no tocar mai `frontend/dist`, que **és** staging):

```
ABANS                          DESPRÉS
E5  FIXED   M → 3XL +0         E5  FIXED   (buit)
EK  FIXED   M → 3XL +0         EK  FIXED   (buit)
EK2 FIXED   M → 3XL +0         EK2 FIXED   (buit)
G1  FIXED   M → 3XL +0         G1  FIXED   (buit)
F   LINEAR  M → 3XL +2  ✕ +    F   LINEAR  M → 3XL +2  ✕ +
A   LINEAR  M → 3XL +3  ✕ +    A   LINEAR  M → 3XL +3  ✕ +
```

**Tres decisions que van amb això, i el motiu:**

- ⚠️ **El silenci és del LLEGAT, no dels intervals explícits.** Un interval desat expressament a
  `breaks` es pinta SEMPRE encara que sembli redundant. La porta ja el rebutja en néixer
  (`BREAKS_DELTA_REDUNDANT`); si malgrat això n'hi ha un a la BD, amagar-lo el faria **invisible
  i inesborrable**. Una ⓘ muda no vol dir «no hi ha dada».
- ⚠️ **No s'ha tocat `grading_utils.intervals_de`.** L'ordre deia «el mirall `intervals_de` només
  emet trams que CANVIEN el delta», i el mirall és el del **front**. `intervals_de` és el MOTOR i
  és el node que el banc mesura: silenciar-hi un tram amb el delta del general no mouria cap
  xifra —dona el mateix valor calculat— però mouria el node del gate per un canvi de **dibuix**.
- ⚠️ **La neteja mai sota STEP.** Allà el relleu és LATENT per llei (PG-4b-3a, el pas
  STEP↔LINEAR no-destructiu). Un STEP està de pas; un FIXED és una destinació.

## 8.3 · QA de l'addenda

| Prova | Resultat |
|---|---|
| `node --test gradingRegime` | **21/21** (6 casos nous: el silenci ①②, l'excepció de l'interval explícit, el cas F, la llei sencera, `relleuResidual`) |
| `qa_f4bis_columna_breaks.py` | **30/30** · dos estats nous a les dues superfícies + ⑧ que captura el **cos del POST** per comprovar que la neteja VIATJA |
| `qa_f4bis_staging.py` | **30/30** · ⑦ el cas F i ⑧ el LINEAR→FIXED→LINEAR |
| `npx eslint src` · `npm run build` · `manage.py check` | 0 errors · net · net |

**⑦ · EL CAS F, tal com Agus el té a pantalla** (en transacció REVERTIDA — v. §8.4):

```
ⓐ punt únic: general 0 + intervals vius NO és degenerada         ✅
ⓐ tot a zero amb breaks informats SEGUEIX degenerada             ✅
ⓐ regla vella d'1 break amb ib=0 i brk=2 SEGUEIX legal           ✅
ⓑ porta ① `set_pom_regim_view`: la F es DESA                     ✅
ⓒ porta ③ `GradingRuleSerializer`: la mateixa forma passa        ✅
ⓓ propagat (base 110,5):  XS 110,5 · S 110,5 · M 112,5 · L 114,5 · XL 117,5
   → passos 0 · 0 · 2 · 2 · 3, que és el que l'ordre demanava     ✅
```

**⑥ · EL MIRALL, REESCRIT.** Amb el silenci el front ja no emet la mateixa LLISTA que el motor,
o sigui que la comparació de llistes hauria donat vermell **per disseny**. El que el mirall
declara és «la pantalla diu el mateix que el motor CALCULARÀ», i això es mesura comparant
**CORBES** — el delta que mana a cada posició del run. Sobre les 21 files vives del banc:

```
21 regles · 21 amb relleu al motor · 9 trams callats per la regla del silenci · CAP corba mòbil
```

Callar no perd cap xifra, i està mesurat sobre dades vives, no sobre fixtures meves.

## 8.4 · 🚩 EL BANC · deriva anotada, i NO és d'aquesta sessió

```
A=✔(105)  B=✔(525)  C=✔(4)   ·  HASH JOC 096990db…989f IDÈNTIC
HASH RESIDENTS  6e55bc13…b6b4  →  50982bbe…1f08
```

**El segell de residents s'ha mogut i la feina d'aquesta sessió no l'ha mogut.** L'evidència:

1. **La QA d'aquesta sessió és hash-estable**: banc → `qa_f4bis_staging.py` sencer (30/30) →
   banc, i el hash surt **idèntic** a banda i banda. Mesurat expressament en veure la deriva.
2. La prova que toca el banc (⑦, la F) va **en transacció revertida**, i el propi script ho
   verifica després: `la F del banc segueix com era (breaks NULL)`. Confirmat també a la BD —
   la F té `updated_at` del **20/08**.
3. Les files que s'han mogut són les **vuit** `FIXED` degenerades, totes amb `updated_at`
   `2026-08-21 18:53:53–54` (una segona sencera, escriptura de màquina) — **després** de
   l'últim commit d'aquesta sessió (18:47) i sense que cap script meu escrigui al 1383 fora de
   la transacció revertida. És la normalització LINEAR+0 → FIXED que el tram E+F ja va anotar
   com a conseqüència de segon ordre de `normalitza_logica`, i hi ha sessions concurrents a
   `dev`.

**Cap cel·la s'ha mogut** (A=105/105) i el **HASH JOC és idèntic**, que és el que diu que el
catàleg no s'ha tocat. El banc mateix declara que aquest segell canvia legítimament quan algú
edita una regla del banc — «per això és segell, no asserció»— i l'acta d'E+F ja en va registrar
dues derives pel mateix motiu (`5715f4a2…` → `59b84241…` → `6e55bc13…`). Aquesta és la tercera.

## 8.5 · Commits de l'addenda

| Commit | Concern |
|---|---|
| `47709102` | **la regla del silenci** a `intervalsVisibles` + `relleuResidual` + la llei escrita al punt únic + 6 proves noves |
| `72e801a1` | **UI** · la columna calla sota FIXED · la neteja en desar · l'error diu quina fila · **cau la tercera còpia del predicat** |
| `0d25f610` | **QA** · el cas F, el LINEAR→FIXED→LINEAR, i el mirall que compara CORBES |

---

# 9 · REOBERTURA · L'ESBORRANY NO ÉS LA REGLA

Amb l'evidència del navegador d'Agus (captura de les 21:22) el símptoma es reprodueix. §8.1
seguia sent cert —la porta dona 200 i el guard no és cec— i alhora insuficient: **la
divergència era al front, i no al predicat sinó a QUIN ESTAT es jutja.**

## 9.1 · El gest, i les DUES cares del mateix defecte

Reproduït conduint tres seqüències sobre el bundle real (`/tmp/probe_draft.py`, el patró del
fum):

| | Gest | Abans |
|---|---|---|
| **G1** | editar el xip llegat → **✓** → `[+]` → escriure Δ → **Gravar sense ✓** | grava **i llença el xip en silenci** |
| **G2** | **✕** el xip llegat → `[+]` → escriure Δ → **Gravar sense ✓** | **«no gradua res (F)»** amb un `+2` a la pantalla |
| G3 | tot confirmat (control) | grava ✅ |

**G2 és la captura d'Agus, literalment.** Treure el xip llegat deixa la regla sense relleu
DESAT (`breaks: []` + els llegats a null); el xip nou viu **només** a l'estat de
`ColumnaBreaks`. El guard mirava la regla; la persona mirava la pantalla. Tècnicament cert,
pràcticament una mentida.

**G1 és el mateix defecte per la cara bona, i ningú l'havia vist perquè no es queixa:** amb un
xip ja confirmat i un segon a mig escriure, «Gravar» funcionava i **el segon desapareixia sense
dir res**. Un guard que et barra és molest; una pèrdua muda de feina escrita és pitjor.

De les tres hipòtesis de l'ordre, **(a) i (b) alhora** —el mirall jutja la fila sense el draft,
i el payload es serialitza sense ell—. La **(c)** queda descartada: el nom «F» era correcte, la
fila era F de debò; el que era fals era el *motiu*.

## 9.2 · El fix

`ColumnaBreaks` avisa cap amunt que té un xip pendent (`onEsborrany`, cridat des dels **gestos**
i no des d'un efecte — un `setState` dins d'un efecte encadena renders i el lint ho canta), i el
«Gravar» de les **dues** superfícies el barra **NOMENANT LA FILA**, i **abans** dels altres dos
guards:

```
Hi ha un interval a mig escriure: confirma'l amb ✓ o cancel·la'l amb ✕ abans de gravar. (F)
```

Va primer a posta: és el que la persona pot resoldre amb un clic, i és el que **explica** per
què el que té escrit a pantalla encara no consta enlloc.

**El ✓ segueix sent el gest.** No s'auto-confirma res: escriure el que ningú ha confirmat seria
guanyar comoditat pagant amb la llei que sosté tota la casa. Amb el ✓ premut, la mateixa
pantalla i la mateixa fila graven — el guard és un recordatori, no una paret.

## 9.3 · QA

| Prova | Abans | Ara |
|---|---|---|
| **G1** (confirmat + draft) | POST que llença el xip | **cap POST** · missatge amb el gest ✅ |
| **G2** (✕ + draft) | «no gradua res (F)» | **cap POST** · missatge amb el gest ✅ |
| **G3** (control) | grava | grava ✅ |
| Amb el ✓ premut | — | la MATEIXA fila grava amb el Δ escrit ✅ |

Al banc de fum com a **⑨** (`qa_f4bis_columna_breaks.py`, **27 → 30 → 33** en tres addendes del
mateix dia), amb tres assercions: cap POST · el missatge diu el gest **i no** «no gradua res»
—comprovat pels dos costats, perquè dir la frase bona no serveix si l'altra segueix sortint— i
el desat després del ✓. Captura: `ops/qa/captures/f4bis_11_esborrany_obert.png`.

> 🔑 **PER QUÈ AIXÒ NO ES PODIA CAÇAR AMB EL PORT.** El defecte no és del payload —el payload
> directe dona 200— sinó de l'**estat que viu entre les tecles i el botó**. Només existeix
> mentre algú té un xip obert, i només un navegador conduït pot tenir-lo obert. És exactament
> la classe de defecte que `qa_mount_modelsheet.py` va néixer per caçar, i la raó per la qual
> el fum ha de conduir GESTOS i no només comprovar píxels.

## 9.4 · Gate i commits

```
A=✔(105)  B=✔(525)  C=✔(4)  ·  HASH JOC IDÈNTIC  ·  HASH RESIDENTS 50982bbe…1f08 (estable)
node --test 21/21 · fum 33/33 · staging 30/30 · eslint 0 errors · build i check nets
```

| Commit | Concern |
|---|---|
| `0955e606` | **el fix** · `onEsborrany` + el guard que nomena la fila, a les dues superfícies · i18n |
| `88523ec6` | **⑨ al fum** · el gest que cap QA de port veu mai |

---

*Acta del 2026-08-21. Cada xifra d'aquest document surt d'una correguda que hi ha al repo i es
pot repetir; les divergències respecte de les ordres (§5.1, §5.2, §8.1 i §9.1) estan dites amb
el motiu al davant i cap d'elles s'ha tapat.*
