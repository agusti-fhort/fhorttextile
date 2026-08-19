# DIFF RULESET BRW ↔ CATÀLEG POM DEPURAT — 🚨 **BLOQUEJADA: falten LES DUES entrades**

Data: 2026-08-03/04 · **Patró A — EN SEC, cap escriptura** · staging `/var/www/ftt-staging`, branca `dev`
HEAD: `923c4c16` · BD: `ftt_staging` @ 5433, schema `fhort`

**Res tocat.** Cap escriptura a `ftt_staging`. Cap fitxer de producció modificat. Cap commit.
Aquest document viu al working tree i **no es commiteja**.

---

## 0 · EL BLOQUEIG, EN UNA LÍNIA

La Fase 3 demanava creuar un fitxer contra quatre rulesets. **Cap de les dues bandes del diff
existeix en aquesta màquina.** Protocol STOP-i-SALTA: anotat i saltat, sense inventar-ne cap.

| entrada que el brief demana | estat mesurat |
|---|---|
| `BROWNIE_CATALEG_POM_DEPURAT_v1.xlsx` (full `CATALEG`, 90 POMs amb LÒGICA i 4 salts) | 🚨 **NO EXISTEIX** enlloc del sistema de fitxers |
| Rulesets **RS146** tops · **RS147** faldilles · **RS148** pantalons · **RS149** exteriors | 🚨 **NO EXISTEIXEN** al corpus: la seqüència de `GradingRuleSet` salta de **124** a **175** |

### 0.1 · Com s'ha comprovat (no és una suposició)

**El fitxer.** Escombrat de tot el sistema de fitxers per nom i per data:

```bash
find / -iname "*BROWNIE*CATALEG*POM*DEPURAT*" -not -path "/proc/*"     # cap resultat
find / -iname "*DEPURAT*" -o -iname "*brownie*"                        # cap .xlsx de catàleg
find / -iname "*.xlsx" -newermt "2026-07-25"                           # 5 fitxers, cap és aquest
```

Els cinc `.xlsx` recents que hi ha són fixtures de test (`dalia_losan_3seccions`,
`smoke_multipeca_2fulls_3seccions`, `brownie_rosalia_spec_sheet`, `brownie_tate_spec_sheet`) i
dos documents d'import de LOS (`L27WKG0612_VEGA_GRADING`, `LOS-SS27-0274_DOCUMENT_001`). El
`brownie_20.xlsx` que hi ha en un scratchpad d'una altra sessió (14/07) és **la plantilla d'alta
de MODELS** (fulls `Instruccions`/`Plantilla`/`_families`…), no un catàleg de POMs: no té ni
columna de lògica ni de salts.

**Els rulesets.** Cens sencer de `GradingRuleSet` a `fhort` — **46 contenidors**, aquests PKs:

```
75-93, 98, 104, 107, 108, 110, 115, 124, 175-188, 210-214, 217
```

**146, 147, 148 i 149 no hi són**, i tampoc hi és cap forat que suggereixi que hi hagin estat:
el salt de `124` a `175` és net. Els rulesets del client BRW (`customer_id=7`) a staging són
exactament **dos**, i cap dels dos té la forma «tops / faldilles / pantalons / exteriors».

---

## 1 · LA BANDA QUE SÍ ES POT MESURAR — els rulesets BRW vius, en sec

Perquè demà el diff sigui **un sol pas** quan arribi el fitxer, aquí queda la banda del ruleset
ja llegida i normalitzada. Lectura pura (`GradingRuleSet` + `GradingRule`), cap escriptura.

### 1.1 · RS 115 · `BRW · Blusa · ALPHA_EU_W` — 34 regles · `size_system` 29 · actiu

| POM | lògica | increment base | break | @talla | salts (`valors_step`) |
|---|---|---|---|---|---|
| A.2 | LINEAR | 1.00 | 1.50 | XS | — |
| AH DEP | LINEAR | 0.70 | 1.00 | XS | — |
| BIC | LINEAR | 0.60 | 0.80 | XS | — |
| BT | LINEAR | 0.50 | — | — | — |
| CH | LINEAR | 2.00 | 3.00 | XS | — |
| CUF H | FIXED | 0.00 | — | — | — |
| E2 | LINEAR | 1.00 | 1.50 | XS | — |
| E4 | FIXED | 0.00 | — | — | — |
| E7 | FIXED | 0.00 | — | — | — |
| E8 | FIXED | 0.00 | — | — | — |
| EK1 | LINEAR | 0.25 | 0.40 | XS | — |
| EK2 | FIXED | 0.00 | — | — | — |
| EP | FIXED | 0.00 | — | — | — |
| F | LINEAR | 1.00 | — | — | — |
| FF | LINEAR | 1.00 | — | — | — |
| G1 | FIXED | 0.00 | — | — | — |
| I3 | FIXED | 0.00 | — | — | — |
| J | LINEAR | 0.60 | 0.80 | XS | — |
| JJ | LINEAR | 0.80 | — | — | — |
| K.2 | LINEAR | 1.00 | 1.50 | XS | — |
| L | LINEAR | 0.50 | — | — | — |
| NK W | LINEAR | 0.50 | 0.75 | XS | — |
| P | LINEAR | 0.50 | — | — | — |
| P1 | LINEAR | 0.50 | — | — | — |
| S | LINEAR | 0.70 | 1.00 | XS | — |
| S2 | LINEAR | 0.70 | 1.00 | XS | — |
| SH | LINEAR | 0.25 | 0.40 | XS | — |
| SH DR | FIXED | 0.00 | — | — | — |
| SK SW | LINEAR | 2.00 | 3.00 | XS | — |
| SL | LINEAR | 1.00 | — | — | — |
| SL OP | LINEAR | 0.30 | 0.50 | XS | — |
| U2 | LINEAR | 0.25 | — | — | — |
| U3 | LINEAR | 0.25 | — | — | — |
| WA | LINEAR | 3.00 | — | — | — |

### 1.2 · RS 124 · `Prova BRW ALPHA UE` — 21 regles · `size_system` 53 · actiu

Mateixos increments que el 115 als POMs compartits, **però amb `valors_step` materialitzats**
(la forma de «4 salts» que el brief menciona): `{XXS, XS, M, L}` per regla. Exemple canònic —
`CH`: `base=2.00`, `break=3.00 @XS`, salts `{XXS: 2, XS: 3, M: 3, L: 3}`.

| POM | lògica | base | break | @ | salts |
|---|---|---|---|---|---|
| A.2 | LINEAR | 1.00 | 1.50 | XS | XXS 1 · XS 1.5 · M 1.5 · L 1.5 |
| AH DEP | LINEAR | 0.70 | 1.00 | XS | XXS 0.7 · XS 1 · M 1 · L 1 |
| BIC | LINEAR | 0.60 | 0.80 | XS | XXS 0.6 · XS 0.8 · M 0.8 · L 0.8 |
| CH | LINEAR | 2.00 | 3.00 | XS | XXS 2 · XS 3 · M 3 · L 3 |
| CUF H | FIXED | 0.00 | — | — | — |
| E2 | LINEAR | 1.00 | 1.50 | XS | XXS 1 · XS 1.5 · M 1.5 · L 1.5 |
| E4 | FIXED | 0.00 | — | — | — |
| EK1 | LINEAR | 0.25 | 0.40 | XS | XXS 0.25 · XS 0.4 · M 0.4 · L 0.4 |
| EK2 | FIXED | 0.00 | — | — | — |
| F | LINEAR | 1.00 | — | — | — |
| FF | LINEAR | 1.00 | — | — | — |
| I | LINEAR | 1.00 | — | — | — |
| J | LINEAR | 0.60 | 0.80 | XS | XXS 0.6 · XS 0.8 · M 0.8 · L 0.8 |
| K.2 | LINEAR | 1.00 | 1.50 | XS | XXS 1 · XS 1.5 · M 1.5 · L 1.5 |
| NK W | LINEAR | 0.50 | 0.75 | XS | XXS 0.5 · XS 0.75 · M 0.75 · L 0.75 |
| S | LINEAR | 0.70 | 1.00 | XS | XXS 0.7 · XS 1 · M 1 · L 1 |
| S2 | LINEAR | 0.70 | 1.00 | XS | XXS 0.7 · XS 1 · M 1 · L 1 |
| SH | LINEAR | 0.25 | 0.40 | XS | XXS 0.25 · XS 0.4 · M 0.4 · L 0.4 |
| SH DR | FIXED | 0.00 | — | — | — |
| SK SW | LINEAR | 2.00 | 3.00 | XS | XXS 2 · XS 3 · M 3 · L 3 |
| SL OP | LINEAR | 0.30 | 0.50 | XS | XXS 0.3 · XS 0.5 · M 0.5 · L 0.5 |

### 1.3 · El que aquesta banda ja diu, sense el fitxer

- **Els dos rulesets BRW cobreixen 35 POMs distints en total**, no 90. Si el catàleg depurat en
  porta 90, **la majoria del diff seran NOVES**, no divergències — i això canvia la pregunta de
  «es pot ampliar el ruleset sense tocar res?» a «quin dels dos contenidors s'amplia, i amb quin
  `size_system`?», que és **decisió humana** (els dos vius tenen sistemes de talla diferents:
  29 i 53).
- **`RS 124` és una duplicació enriquida de `RS 115`**: mateixos increments, mateix break, mateixa
  talla de break, i a més els salts materialitzats. Els POMs que el 115 té i el 124 no (`BT`, `E7`,
  `E8`, `EP`, `G1`, `I3`, `JJ`, `L`, `P`, `P1`, `SL`, `U2`, `U3`, `WA`) i el que el 124 té i el 115
  no (`I`) són el diff intern del client, i és previ a qualsevol ampliació.
- ⚪ **Anotat, fora d'abast:** cap dels dos porta `capa`/`instancia`, i és a posta —
  `pom/services.py:723-730`, decisió de domini amb acta: «mateix POM, mateix increment a totes les
  capes i a totes les instàncies». C4 **no ha de tocar aquestes taules**.

---

## 2 · QUÈ CAL PER DESBLOQUEJAR

1. **El fitxer.** `BROWNIE_CATALEG_POM_DEPURAT_v1.xlsx` en una ruta llegible d'aquesta màquina.
2. **Quins són els rulesets de debò.** Els PKs 146-149 no existeixen. Cal saber si el diff va
   contra els dos BRW vius (**115** i **124**), contra quatre contenidors que encara s'han de
   crear, o contra un altre entorn (PROD, on el cens pot ser un altre — i a PROD no hi ha SSH
   des d'aquí).

Amb les dues coses, el diff és mecànic: per a cada POM del full `CATALEG`, **COINCIDEIX** /
**DIFEREIX** (amb els dos valors al costat) / **NOVA**, i cap escriptura.

---

*Diagnosi en sec. Cap escriptura a `ftt_staging`, cap migració, cap commit, cap push, cap deploy.*
