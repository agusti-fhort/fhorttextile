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
| ⑥ | FIXED → columna inerta | `f4bis_6_fixed.png` |
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

### 4.1 · La pantalla — `ops/qa/qa_f4bis_columna_breaks.py` · **27/27** ✅

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

### 4.2 · El payload, per les portes reals — `ops/qa/qa_f4bis_staging.py` · **18/18** ✅

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
| `node --test` · `gradingRegime.test.js` | **15/15** (9 casos nous: el llegat, l'ordre, les talles lliures, el sostre) |
| `node --test` · tots els bancs de `src/utils` i `src/components` | verds |
| `npx eslint src` | **0 errors** (270 warnings preexistents) |
| `npm run build` | net |
| `manage.py check` | net |
| `banc_paritat_1383.py` | ✅ A=105 · B=525 · C=4 · els dos hashos idèntics |

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

*Acta del 2026-08-21. Cada xifra d'aquest document surt d'una correguda que hi ha al repo i es
pot repetir; les dues divergències respecte de l'ordre (§5.1 i §5.2) estan dites amb el motiu
al davant i cap de les dues s'ha tapat.*
