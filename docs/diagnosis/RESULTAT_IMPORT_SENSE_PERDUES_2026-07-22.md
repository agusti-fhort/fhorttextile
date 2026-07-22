# RESULTAT — Import complet sense pèrdues silencioses (2026-07-22)

Sprint Patró B sobre `dev` a staging. **7 commits, cap push.** Base: `865c566`.

Decisions que manen: D1 (contenidor intocable + proposta de promoció), D2 (sobirania del
model: els overrides graduen), D3 (normalització a 0,1 mm), i l'annex d'IA (cribratge només
quan cal + log de cost).

---

## Els commits

| # | hash | focus |
|---|------|-------|
| 1 | `a038e09` | MOTOR · el POM només-override deixa de sortir coix per la talla base (D2) |
| 2 | `680a874` | un sol punt de normalització a 0,1 mm per als tres camins d'entrada (D3) |
| 3 | `b487f95` | re-classificació: la hipòtesi del soroll queda REFUTADA (verificació) |
| 4 | `147690e` | PROPOSTA DE PROMOCIÓ · els POMs que no entren al catàleg deixen de perdre's |
| 5 | `8d5ad89` | i18n ca/en/es de la proposta |
| 6 | `08b365c` | un xlsx parsejable deixa de pagar cribratge i revisió d'IA |
| 7 | `bce0e18` | AIUsage · tota crida a Anthropic deixa rastre del que ha costat (+ migració 0059) |

---

## Q1 · PARITAT DEL MOTOR (condició dura) — **VERDA**

El motor és zona intocable: la condició era que els golden fossin idèntics abans i després.

Comparar contra els `GradedSpec` **desats** no serveix: molts són ranços (escrits per
versions anteriors del motor) i la diferència mesuraria l'antiguitat de la fila, no el canvi.
La comparació bona és **A/B del motor vell contra el nou sobre les mateixes dades**,
regenerant dins de transaccions tombades. El «motor vell» es reprodueix exactament fent que
`_poms_amb_override` retorni `set()`: amb el conjunt buit la branca nova és inabastable i el
flux de control queda idèntic al de HEAD.

```
                                        VELL      NOU   sha vell / sha nou
model 268 · SF 158                       100      100   e6cf183f9ab2 / e6cf183f9ab2  ✅
model 269 · SF 159                       125      125   6b759387cb1a / 6b759387cb1a  ✅
model 163 · SF  53                   SEGELLADA SEGELLADA  (refusa igual als dos costats)
model 163 · SF  79                        96       96   cef7936716dd / cef7936716dd  ✅
TOTAL 321 cel·les · cap canvi de valor, tipus ni increment
```

Re-verificada després dels 7 commits: segueix verda.

> ⚠️ **El brief deia 269 = 125 i el cens desat en deia 120.** El brief tenia raó: les 120
> desades eren estat ranci. Regenerat, el 269 dona 125 pels dos costats.

---

## Q2 · CAS MEREDITH E2E — **VERD**

Model `[QA] MEREDITH-Q2` + contenidor `[QA-PROMO]` **clonat de prova** (mai el 115 real ni
cap contenidor de producció). Tota la prova va dins d'una transacció tombada: staging no
queda amb cap residu `[QA]`.

Estat reproduït: 17 POMs que coincideixen amb el catàleg + 9 que no hi són o hi divergeixen.

```
── CLASSIFICACIÓ ──
  sembra (hereten del catàleg): 17
  amplia + conflicte (només model): 9 + 0

── TAULA DEL MODEL [QA] ──
  POMs visibles: 26/26   (cel·les: 130)
  D1 (EG):            53.5 / 55.5 / 58.5 / 61.5 / 64.5
  D1 esperat:         53.5 / 55.5 / 58.5 / 61.5 / 64.5
  heretat (CH):       38.0 / 39.0 / 40.0 / 41.0 / 42.0   (LINEAR +1 del catàleg)

── PROPOSTA DE PROMOCIÓ ──
  watchpoint #868 · estat open
  items: 9 (amplia=9, conflicte=0) · tots en estat {'nomes_model'}
  contenidor tocat? regles al catàleg = 17 (n'hi havia 17)   ← INTOCABLE, complert
```

**A/B que demostra que el resultat depèn del fix** (mateix guió, amb el rescat D2 desactivat):

```
  POMs visibles: 26/26   (cel·les: 121)     ← 9 cel·les menys
  D1 (EG): 53.5 / 55.5 / None / 61.5 / 64.5 ← la BASE, buida
```

121 vs 130 = exactament les 9 cel·les de talla base, una per POM només-model. Això confirma
també la forma exacta del bug: **els 9 POMs ja es veien** (26/26 als dos costats); el que
faltava era la cel·la del centre de cada fila.

---

## Q3 · NORMALITZACIÓ — **VERD**

`fhort.pom.test_d3_normalitzacio` (11 verds): soroll de float mor (16.749999999999999 →
16.75), coma decimal entesa, i **el pas de 0,25 sobreviu** (2 decimals, mai 1 — arrodonir a
un decimal destruiria mig domini de confecció).

---

## Q4 · REGRESSIÓ SENCERA

Els 24 vermells preexistents de `SizeFitting` no compten, i s'han identificat: totes les
fallades del bloc són la mateixa `IntegrityError` de
`fitting_sizefitting_model_id_numero_uniq` **dins del `setUp` dels tests aliens** (un signal
de `Model` ja sembra el `SizeFitting numero=1` i el fixture n'hi crea un altre). No toquen
`pom/services.py` ni cap fitxer d'aquest sprint. El fixture propi d'aquest sprint sí que ho
contempla (reutilitza el SF sembrat).

Tests NOUS del sprint, tots verds:

| fitxer | verds |
|---|---|
| `fhort.pom.test_d2_nomes_override` | 7 |
| `fhort.pom.test_d3_normalitzacio` | 11 |
| `fhort.pom.test_d3_reclassificacio` | 6 |
| `fhort.models_app.test_d1_proposta_promocio` | 13 |
| `fhort.models_app.test_ia_routing_i_cost` | 11 |

Regressió dels camins tocats (parser xlsx + size_map + Meredith S24 + D2): **62 verds**.

---

## Q5 · CRIDES D'IA — de 2 a 0 per a un xlsx parsejable

`_cribratge_determinista` sobre un xlsx REAL (construït amb openpyxl, no un parser
mockejat) retorna resultat → la crida a Opus del pas 1 no es fa. La revisió Sonnet passa a
opt-in (`IMPORT_REVISIO_SONNET`, per defecte OFF) → la crida del pas 2 tampoc.

PDF, imatge i xlsx on el parser abdica segueixen anant a Opus igual que abans (verificat als
tests: pocs registres coherents, bytes corruptes i `.pdf` cauen tots a la IA).

> ⚠️ **Matís honest:** el fitxer Meredith real no és al repo (no hi ha cap fixture
> `*meredith*`). La verificació és sobre el PREDICAT del routing amb un xlsx real de la
> mateixa forma, no sobre aquell fitxer concret.

---

## Q6 · LOG DE COST — **VERD, amb crida real**

`AIUsage` + migració `0059` (additiva: una taula nova, cap alteració). Aplicada amb
`migrate_schemas` i **auditada directament a la BD** (13 columnes + 6 índexs al schema
`fhort`).

Camí que SÍ crida IA, executat de debò pel codi de producció:

```
  files abans: 0
  fila registrada → cami=revisio model=claude-sonnet-4-6 in=157 out=38 ok=True @21:17:31
  files després: 1
```

I la pregunta del brief, amb una sola consulta:

```
  cribratge  claude-opus-4-7    n=1  in=900   out=120
  extraccio  claude-opus-4-7    n=1  in=4210  out=1875
```

> Nota: la fila `revisio` de dalt és una crida REAL i queda a la BD de staging com a
> evidència. És l'única fila d'`AIUsage` que hi ha.

---

## Banderes per al CTO

1. **Àlies I4→SL (fora d'abast, decisió de catàleg d'Agus/Montse).** Verificat que **cap
   normalització el desinflarà**: el soroll de float no arribava mai al classificador
   (`detect_grading` ja arrodonia el delta a 2 decimals). Els conflictes que hi ha són
   conflictes reals de catàleg. L'únic fals conflicte que el commit 2 desinfla de debò és el
   dels valors que arriben com a **cadena amb coma decimal** (sortida d'IA, enganxat d'Excel
   europeu), que abans petava dins de `detect_grading` i es fabricava una divergència.

2. **UI òrfena trobada, NO tocada** (`ImportWizard.jsx:1180-1240`): un selector per-POM
   `keep_catalog / update_catalog / model_resident` amb i18n als tres idiomes, que envia
   `conflict_resolutions`. **Cap endpoint del backend l'emet ni el llegeix** — codi mort. La
   proposta d'aquest sprint viu al Watchpoint, que sobreviu al tancament del wizard (que és
   justament on abans es perdia tot). Decisió pendent: jubilar l'òrfena o convergir-hi.

3. **`promocionar-poms` esborra els `ModelGradingOverride` del POM promocionat.** És
   deliberat i necessari (l'override guanya a qualsevol regla; sense esborrar-lo la regla
   promocionada no s'aplicaria mai), però és una escriptura destructiva sobre dades
   d'import. Val la pena que l'Agus la validi abans del push.

4. **Anotat de passada, no tocat:** `n_ovr` a `extraction_views` es compta i es llença; el
   bloc d'URLs de l'import viu dins d'un `try/except Exception` que convertiria un error
   d'import en «totes les rutes desapareixen en silenci» (per això la ruta nova es va
   verificar amb `resolve()`).

---

## Què ha de fer el CTO

`git show <hash>` dels 7 commits (`a038e09` … `bce0e18`) i **push des de SSH**. Cap push fet
des de l'agent. La migració `0059` ja és aplicada a staging; a PROD caldrà `migrate_schemas`
al deploy.
