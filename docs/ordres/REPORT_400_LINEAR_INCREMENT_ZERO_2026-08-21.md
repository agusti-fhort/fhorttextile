# EL 400 DE LA F — `LINEAR_INCREMENT_ZERO` · report de causa i tancament
**Data:** 2026-08-21 · **Gate:** `ops/qa/banc_paritat_1383.py` (3 blocs) abans i després
**Veredicte del gate:** ABANS `A=✔(105) B=✔(525) C=✔(4)` · DESPRÉS **idèntic** ·
HASH RESIDENTS `50982bbe5ede14f285a4b3e7349ae8b15e2e9b67a3aaf1167e112a80b35f1f08` (l'estable
vigent, sense moure) · HASH JOC `096990db…` intacte.

---

## 0 · LA CORRECCIÓ AL DIAGNÒSTIC D'ENTRADA

L'ordre deia: «hi ha una SEGONA validació dins de `set_pom_regim_view` (o el seu serializer) amb
codi propi `LINEAR_INCREMENT_ZERO`, anterior al punt únic, que jutja *increment 0* sense mirar
breaks». **L'espècie era exacta i la conclusió operativa també** —hi havia dues mesures del
mateix fet i la vella manava en silenci—, **però el segon porter no és al codi: és al BINARI.**

El cens ho tanca amb noms. `LINEAR_INCREMENT_ZERO` es declara **una sola vegada** a tot el
backend (`pom/grading_regime.py:28`, `CODI_LINEAR_ZERO`) i té **quatre** consumidors, tots
delegant al punt únic i **tots passant `breaks`**:

| porta | fitxer:línia | passa `breaks`? |
|---|---|---|
| `set_pom_regim_view` | `models_app/views.py:5486` | ✅ |
| `gravar_pom` (taula de gènesi) | `models_app/views.py:2630` | ✅ |
| porta S2 | `pom/s2_views.py:388` | ✅ |
| porta S4 | `pom/s4_views.py:117` | ✅ |

Cap serializer no en declara cap altre. **No hi havia res a retirar per aquesta banda.**

---

## 1 · LA CAUSA REAL, AMB HORES

```
gunicorn ftt-staging arrencat ......... 2026-08-21 12:37:55 UTC   → codi de `ea03184e` (12:33:52)
TRAM F/F2 (el motor llegeix intervals)  2026-08-21 15:49:46 UTC   c07b1d5a   ← DESPRÉS
TRAM F/F3+F5 (la porta dels intervals)  2026-08-21 17:11:51 UTC   a4d179eb   ← DESPRÉS
TRAM E (porta del valor vermell) ...... 2026-08-21 17:44:39 UTC   bbbc05e6   ← DESPRÉS
regla del SILENCI ..................... 2026-08-21 19:13:46 UTC   47709102   ← DESPRÉS
```

El procés que servia el 400 corria el codi de **`ea03184e`**, on:

* `set_pom_regim_view` **no coneix el camp `breaks`**: no hi ha `has('breaks')`, no hi ha
  `valida_breaks`, no hi ha `rule.breaks = nets`. El camp del payload **s'ignorava sencer**.
* `es_linear_degenerada` tenia **cinc** paràmetres —sense `breaks`— i el cos era:

  ```python
  if (logica or '').strip().upper() != 'LINEAR': return False
  if te_break(increment_break, talla_break_label): return False
  return delta_base_efectiu(increment_base, increment) == 0.0
  ```

Contra el payload d'Agus (`increment_break: null`, `talla_break_label: null`, la fila amb
general **0** desat, i els intervals **M→L 2 · XL→XL 3** que aquella versió no mira):
`te_break` → `False`; `delta_base_efectiu` → `0.0` → **`True` → 400 `LINEAR_INCREMENT_ZERO`**.

És, literalment, **«un judici d'increment 0 que no mira breaks, anterior al punt únic»** — la
descripció de l'ordre és correcta fins a l'última paraula. El que no és, és una segona còpia
escrita: és **la còpia VELLA DE LA MATEIXA funció, viva dins d'un procés que no s'havia
reiniciat**. Mateixa espècie que el camp llegat del fix A, un pis més avall: no dues
implementacions al repo, sinó dues **en execució simultània** —una al disc i una a la memòria
del gunicorn—, i la vella manant en silenci.

**FIX:** `systemctl restart ftt-staging` → arrencat **20:01:31 UTC**, actiu. Els dos fitxers que
manen tenen mtime **anterior** a l'arrencada (`grading_regime.py` 19:13:16 ·
`models_app/views.py` 19:59:47), o sigui que els workers d'ara **han carregat el guard de sis
paràmetres que llegeix intervals**. Cap migració pendent a `public`, `fhort` ni `los` abans de
reiniciar (comprovat), i la columna `breaks` ja existia als tres esquemes.

### Per què la porta provada donava 200 — la divergència, amb noms
**Perquè no era la mateixa porta.** Els fums del tram F
(`fhort/pom/test_tram_f_intervals.py`) i els QA de staging (`ops/qa/qa_tram_ef_staging.py`)
criden `set_pom_regim_view` **en procés**, amb `APIRequestFactory` + `force_authenticate`:
importen el mòdul **del disc** en el moment de córrer. Agus travessava **nginx → gunicorn**, que
és l'únic camí que passa per la còpia carregada a les 12:37. Cap dels dos mentia: mesuraven
**codis diferents**. Aquesta és exactament la forma de la llei que ja teníem escrita —«el
gunicorn serveix el codi de quan va arrencar»— i el que hi afegeix el cas d'avui és que **un
guard n'és una víctima especialment cruel**: el rebuig arriba amb un codi de domini ben format i
un missatge sensat, i sembla una decisió del sistema quan és un fòssil.

---

## 2 · CENS DE GERMANS — codis de validació de règim declarats fora del punt únic

Grep de `'codi':`/`'code':` literals a les vistes i serializers de règim
(`models_app/views.py`, `pom/s2_views.py`, `pom/s4_views.py`, `pom/views.py`):

| codi literal | on | veredicte |
|---|---|---|
| **`'STEP_TALLA_BASE'`** | `models_app/views.py` (porta del valor vermell) | 🔴 **DUPLICAT — RETIRAT** |
| `'STEP_SENSE_REGLA'` | id. | ✅ fet propi (no hi ha regla resident): el punt únic no el pot dir, no en rep la fila |
| `'STEP_SENSE_BASE'` | id. | ✅ fet propi (no hi ha `BaseMeasurement`): idem |
| `CODI_STEP_CAMI_INCOMPLET` | id. | ✅ ja ve del punt únic; el judici el fa `step_delta_acumulat`, que és qui sap quina talla falta |
| `'GRADING_RULESET_EMPTY'`, `'GRADING_SIZE_SYSTEM_MISMATCH'`, `'GRADING_CUSTOMER_MISMATCH'`, `'GRADING_RESIDENTS_WIPE'` | `models_app/views.py` | ✅ són d'**assignació de joc**, no de forma de la regla: cap fet compartit amb `grading_regime` |
| `'regla_sense_delta'` | `models_app/views.py:3547` | ✅ és un **avís de lectura** (la fila no emet), no una porta d'autoria |
| `'base_set_*'` | `pom/views.py`, `models_app/views.py` | ✅ fora de règim (base set) |

### El duplicat retirat
`'STEP_TALLA_BASE'` deia **el mateix fet** que `valida_valor_step` acaba de dir quatre línies més
amunt —i **amb el mateix codi de rebuig, escrit a mà**— però el **mesurava d'una altra manera**:

* punt únic: compara **ETIQUETES** (`_norm_label(talla) == _norm_label(model.base_size_label)`),
* la vista: comparava **ÍNDEXS** (`_pos(talla) == base_idx`, i `base_idx` surt de
  `escala_del_model`, que el deriva **del mateix `base_size_label`**).

Mentre coincideixin, la branca de la vista **no s'assoleix mai**; el dia que divergissin, mana la
primera. O sigui: no protegeix de res i només fabrica la il·lusió que sí. **Se n'ha anat el
judici i s'hi ha quedat la feina** (`idx`, que fa falta per trobar el veí cap a la base) —
exactament el criteri de l'ordre. Els dos comprovants que hi apuntaven
(`test_la_talla_BASE_no_entra_per_aquesta_porta` i `qa_tram_ef_staging.py:173`) miren
`status==400` i `codi=='STEP_TALLA_BASE'`, i el punt únic segueix servint tots dos.

---

## 3 · EL MISSATGE

`MISSATGE_LINEAR_ZERO` conserva el text bo, sense tocar: *«Una regla LINEAR amb increment 0 no
gradua res. Si aquesta mesura no ha de canviar entre talles, fes-la FIXED; si no aplica a aquest
model, esborra-la.»* I **nomena la fila** al consumidor: `GraduacioSuperficie.jsx` empaqueta el
rebuig com a `${fila.pom_code}: ${detail}` (§9 del F4-BIS). Sense canvis.

---

## 4 · FUM ⑩ — el gest EXACTE d'Agus

`fhort/pom/test_tram_f_intervals.py :: IntervalsPerLaPortaHTTPTest ::
test_FUM_10_el_gest_dAgus_general_0_amb_intervals_confirmats`

No una versió neta del gest, **el gest**: la fila **ja existeix** amb general 0 i un interval
(que és el que Agus tenia a la taula), i el payload és el que la pantalla envia de debò
(`GraduacioSuperficie.jsx:301-312`, per presència de clau) — **sense** `increment_base` ni
`logica`, i **amb** `increment_break: null`, `talla_break_label: null`, `garment: ''`:

```json
{"breaks": [{"inici":"M","final":"L","delta":2}, {"inici":"XL","final":"XL","delta":3}],
 "increment_break": null, "talla_break_label": null, "garment": ""}
```

**→ 200**, la resposta torna el relleu sencer, i es **propaga**: `XS 100 · S 100 · M 102 ·
L 104 · XL 107`, que són els deltes **0 / 0 / 2 / 2 / 3** que Agus volia escriure. La porta que
això travessa (`set_pom_regim_view`, la de `models.setPomRule`) **entra al banc per sempre**: si
algú torna a llegir «increment 0» sense mirar els intervals, aquí peta.

Suite `test_tram_f_intervals` (47 tests) + `test_fix_a_p1_escriptors_llegat`: **OK**.

---

## 5 · LA LLIÇÓ, PER SI TORNA

Un **400 amb codi de domini ben format no prova que el codi que el diu sigui el del disc**.
Abans de buscar el porter duplicat al repo, comparar **l'hora d'arrencada del procés** amb
**l'hora del commit** que va canviar el guard: si el commit és posterior, el porter que et
rebutja **ja no existeix a cap fitxer** i cap grep te'l trobarà mai.

I la seva germana operativa: **un fum en procés no verifica una porta HTTP**. Mentre l'agent no
pugui emetre el JWT de QA, tot el que aquesta casa mesura de `set_pom_regim_view` mesura el
DISC; el gest per HTTP el segueix havent de fer Agus, i qualsevol desacord entre els dos s'ha de
llegir primer com **procés ranci**, no com bug de lògica.
