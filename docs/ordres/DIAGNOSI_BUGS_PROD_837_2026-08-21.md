# DIAGNOSI READ-ONLY A PROD — bugs del model «837 VESTIT» + cens LOSAN

> **Patró A · PROTOCOL_FASE_B.** 2026-08-21 · PROD `178.105.217.125` · `/var/www/fhort-textile`
> · branca `main` @ `f9efe255` · schema `fhort`.
> **Cap escriptura.** Totes les lectures de BD via ORM amb
> `PGOPTIONS="-c default_transaction_read_only=on"` (verificat: `SHOW transaction_read_only` → `on`)
> dins de `schema_context('fhort')`. Cap `psql -c` solt, cap migració, cap restart, cap `git` que escrigui.
>
> **Model de referència:** `TRV-SS27-0001` · `nom_prenda = '837 VESTIT'` · **`Model.id = 1215`**
> (client TRV · TROVELS, id 11). Joc assignat: `GradingRuleSet #152 · GRADING BROWNIE 2026`.
> Sistema `ALPHA_EU_W` (#29) · run `XS·S·M·L·XL` · base `S` · `measurements_version = 1` · origen `INTERN`.

---

## Índex

- [A. Re-propagació i regles manuals](#a)
- [B. Gating de «Mesurar prenda»](#b)
- [C. Selector de joc de graduació](#c)
- [D. Crear POM nou al catàleg](#d)
- [E. Regla STEP sense valors](#e)
- [F. Multi-break](#f)
- [G. UI (localització)](#g)
- [H. Fitxa tècnica — taula de mesures de talla base](#h)
- [I. Cens LOSAN a PROD](#i)
- [CONTRADICCIONS AMB EL BRIEF](#contradiccions)

---

<a id="a"></a>
## A. BUG GREU — «la re-propagació ignora les regles manuals del model»

### A.0 · ⚠️ ATURADA DE MÈTODE — el símptoma NO es reprodueix a les dades de PROD

Aquest tram s'atura i es reporta, tal com mana la nota de mètode del brief: **la premissa del
símptoma no es sosté contra la BD**. Ho dic amb la mesura al davant abans de traçar res més.

He recalculat **totes** les cel·les del model amb el motor real (funcions pures
`escala_del_model` + `_load_grading_rules_per_garment` + `_regla_de` + `_apply_rule`, cap
escriptura) i les he contrastades amb els `GradedSpec` de la versió vigent:

```
size_run: ['XS','S','M','L','XL'] · run_sistema: ['XXS','XS','S','M','L','XL','XXL','3XL'] · base_idx=2
versió vigent: GV#92 (v6)
OK=105  DISCREPA=0  ABSENT=0  |  specs a la taula=105  |  files base=21
```

**Zero discrepàncies.** Els números que hi ha a l'escalat són exactament els que produeixen les
regles residents d'ARA, edicions manuals incloses.

La cronologia forense ho confirma. Diferència de valors entre versions consecutives contra
l'hora de cada edició manual (`ModelGradingRule.updated_at`):

| GradingVersion | data | cel·les | POMs amb valor canviat |
|---|---|---|---|
| GV#87 v1 | 17:08:23 | 95 | (base) |
| GV#88 v2 | 17:12:10 | 100 | `SLT` (nou) |
| GV#89 v3 | 17:21:45 | 105 | `J` (nou) |
| GV#90 v4 | 17:50:28 | 105 | — |
| GV#91 v5 | 17:59:16 | 105 | `F`, `E1`, `EK` |
| **GV#92 v6** | **18:17:22** | **105** | `E`,`S`,`S2`,`I`,`C`,`D`,`EK`,`EK1`,`E7`,`J`,`J1`,`SF` |

Edicions manuals: `F·E1·A·B` a les **17:58:44-45** → recollides a v5 (17:59:16). Bloc
`G1·SLT·EK·EK1·EK2·E5·E·SF·S·S2·I·J·J1·U·E7` a les **18:12:29-31**, `C` a les **18:13:09** i
`D` a les **18:14:09** → **totes recollides a v6 (18:17:22)**.

El cas literal del brief, POM **D** (`MGR#3195`, pom 1001, `origen=MANUAL`, editat 18:14:09 amb
`increment_base=0.50 · increment_break=0.50 · talla_break_label='M'`):

| talla | v1…v5 (regla vella: ib=2 / brk=3 @M) | **v6 (regla d'ara)** |
|---|---|---|
| XS | 57.0 (−2.0) | **58.5 (−0.5)** |
| S (base) | 59.0 | 59.0 |
| M | 62.0 (+3.0) | **59.5 (+0.5)** |
| L | 65.0 (+6.0) | **60.0 (+1.0)** |
| XL | 68.0 (+9.0) | **60.5 (+1.5)** |

La re-propagació **sí** ha aplicat la regla manual. Els POMs `A` i `B` no van moure cap número a
v5 perquè es van re-desar amb els mateixos valors que ja tenien (`ib=2 · brk=3 · break M`), no
perquè s'ignoressin; i `G1·SLT·EK2·E5·U` no van moure res a v6 perquè es van desar a
`ib=0 · brk=0` (v. §A.5, defecte 3), que produeix la mateixa taula plana que ja hi havia.

**No resolc això pel meu compte.** Cal que l'Agus digui **quina propagació concreta** (hora) i
**quin POM** van donar el número vell, perquè amb l'estat d'avui el camí és correcte. El que sí
he fet és traçar el camí sencer i censar els **defectes reals i verificables** que hi viuen i que
poden produir exactament aquest símptoma (§A.5) — un d'ells és, literalment, «propagar amb el
valor del joc antic».

### A.1 · El camí complet de «Propagar», del front al motor

| # | Node | Àncora |
|---|---|---|
| 1 | Botó «Propagar» del stepper de Mesures | `frontend/src/pages/ModelSheet.jsx:1324-1331` |
| 2 | `onPropagarClick` → mira abans (`grading-status`) | `frontend/src/pages/ModelSheet.jsx:937-951` |
| 3 | `execPropagar` → `POST` amb `{new_version: true}` | `frontend/src/pages/ModelSheet.jsx:986-997` |
| 4 | `models.generarGrading` | `frontend/src/api/endpoints.js:158` |
| 5 | URL | `backend/fhort/models_app/urls.py:235` |
| 6 | `generate_grading_view` | `backend/fhort/models_app/views.py:3003` |
| 6a | gate «té regles?» (`_te_regles`) | `models_app/views.py:3014` |
| 6b | tria del SizeFitting: **`.filter(model=model).first()`** | `models_app/views.py:3027` |
| 6c | guard de segell (409 si `aprovada` i sense `allow_reopen_sealed`) | `models_app/views.py:3061-3070` |
| 6d | **llenç net**: esborra tots els `ModelGradingOverride` del model | `models_app/views.py:3084` |
| 6e | consolida la base des dels fittings OBERTS | `models_app/views.py:3090-3095` |
| 7 | `bump_grading_version_and_generate` | `pom/services.py:1058` |
| 7a | desactiva TOTES les actives i crea la v+1 | `pom/services.py:1101-1113` |
| 8 | `generate_graded_specs` | `pom/services.py:166` |
| 8a | **font de regles**: `_load_grading_rules_per_garment(model)` | `pom/services.py:209` → `:828` |
| 8b | overrides per cel·la | `pom/services.py:211` → `:922` |
| 8c | mesures base | `pom/services.py:215` → `:980` |
| 8d | versió on s'escriu (porta única + guard de segell) | `pom/services.py:222` → `:1020` |
| 8e | busca de la regla per peça | `pom/services.py:238` → `:897` |
| 8f | càlcul | `pom/services.py:295` → `:1144` |
| 8g | escriptura | `pom/services.py:311` → `:1241` |

**Quina font de regles llegeix el motor, i on es decideix.** A `pom/services.py:875-891`:

```python
rules = ModelGradingRule.objects.filter(model_id=model.id, actiu=True)      # :876
out = {(r.pom_id, r.garment): r for r in rules}                             # :877
te_residents_la_mare = any(garment == '' for (_pom_id, garment) in out)     # :880
if not te_residents_la_mare and model.grading_rule_set_id:                  # :881
    out.update({(r.pom_id, ''): r for r in GradingRule.objects.filter(      # :886
        rule_set_id=model.grading_rule_set_id, actiu=True)})
```

→ **Les residents (`ModelGradingRule`) manen sempre.** El `GradingRule` del joc via FK només entra
com a **fallback** i **només si la peça mare no té cap resident activa**. La decisió és aquesta
línia i cap altra. El gate d'entrada (`_te_regles`, `pom/services.py:731`) fa la mateixa pregunta.

**Segon camí de propagació que existeix i que el brief no cita:** `gravar_pom_view`
(`models_app/views.py:2325`) crida `generate_graded_specs` **in-place** (sense bump) al final del
desat de POM — `models_app/views.py:2602-2607`. És idempotent i reutilitza la versió vigent.

### A.2 · Estat mesurat del model (POM D i context)

**Regles residents:** 142 files, **142 actives**, totes `garment=''`, totes amb
`derivat_de_rule_set_id=152`. 21 amb `origen='MANUAL'`; la resta, `CLIENT_RUN` (materialitzades
en assignar el joc, 16:50:53).

```
MGR#3195  pom=1001 'D'  garment=''  actiu=True  logica=LINEAR
          increment=2.00   increment_base=0.50   increment_break=0.50
          talla_break_label='M'  talla_break_pos=2  valors_step=None
          origen=MANUAL  derivat_de_rule_set=152  updated_at=2026-08-20 18:14:09.604436+00
```

**Mesura base de D:** `BaseMeasurement#2354` · capa `exterior` · instància `''` · garment `''` ·
`base_value_cm=59.0` · activa · ordre 3.

**SizeFitting i versions:** un sol `SizeFitting#1099` (`TRV-SS27-0001-SF1`, tipus `Proto`, estat
`TallesGenerades`). Sis `GradingVersion` (v1…v6); **cap segellada** (`aprovada=False` a totes
sis); **v6 = GV#92 és l'única activa**, amb 105 `GradedSpec`. `ModelGradingOverride` del model: **0**.

**Quina regla justifica els números de la taula:** la de MGR#3195, la manual, amb la mecànica
d'arestes de `grading_utils.increment_de_l_aresta` (`pom/grading_utils.py:1006`): base `S`
(idx 2 en espai de sistema), break `M` (idx 3). Aresta `S↔M` → extrem exterior `M` ≥ break →
`increment_break=0.5`. Aresta `XS↔S` → extrem exterior `XS` < break → `increment_base=0.5`.
Com que `ib == brk` la corba surt uniforme a ±0.5/pas. **Casa exactament.**

### A.3 · Veredicte sobre les quatre hipòtesis del brief

| Hip. | Enunciat | Veredicte | Evidència |
|---|---|---|---|
| **(a)** | el motor llegeix el ruleset i no les residents | **REFUTADA** | `pom/services.py:876-888`: les residents s'hi posen primer i el joc només entra si la mare no en té cap. El model 1215 té 142 residents actives → el joc **no s'arriba a llegir mai** en aquesta propagació. |
| **(b)** | la re-propagació reutilitza una GradingVersion existent | **REFUTADA** pel camí del botó | `models_app/views.py:3057` envia `new_version=True` (el front sempre l'envia: `ModelSheet.jsx:988`) → `pom/services.py:1101-1113` desactiva totes i **crea** la v+1. Mesurat: sis versions per a sis propagacions. **⚠️ Matís:** el camí `new_version=False` (`models_app/views.py:3129-3145`) i `gravar_pom_view` (`:2607`) **sí** escriuen in-place sobre la vigent; però hi escriuen amb `update_or_create`, o sigui que tampoc no conserven un valor vell d'un POM que el motor emeti. |
| **(c)** | l'edició manual escriu on el motor no llegeix | **REFUTADA en l'estat d'avui, PERÒ el forat existeix** | `set_pom_regim_view` (`models_app/views.py:5173`) fa `ModelGradingRule.objects.filter(model=..., pom_id=..., garment=...)` **sense `actiu=True`**, mentre el motor filtra `actiu=True` (`pom/services.py:876`). Una resident amb `actiu=False` rebria l'edició i el motor no la veuria mai → cauria al joc = *«la regla vella»*. A `fhort` no hi ha avui cap `ModelGradingRule` inactiva (142/142 actives al 1215), i **cap camí de codi posa `actiu=False`** (grep sense resultats fora de tests) → forat **latent**, no actiu. |
| **(d)** | `materialize_model_grading_rules` sobreescriu la manual abans de propagar | **REFUTADA per al camí de propagar** | Cens de cridadors: `models_app/views.py:981, 1054, 1204, 1807` i `extraction_views.py:3571`. **Cap** és a `generate_grading_view` ni a `bump_grading_version_and_generate`. Els cridadors són: assignar/canviar joc (`update-step2`), sembra del wizard, i import. A més, quan hi passa, `poms_manual_a_preservar` (`models_app/services.py:~300`) **preserva** les `origen='MANUAL'` si el joc anterior està classificat. |

### A.4 · main vs origin/dev en aquest camí

```
main       f9efe255
origin/dev 98b4d7bf
merge-base 98b4d7bf      → origin/dev és ANCESTRE de main
git diff --stat main origin/dev  → 2 fitxers (una management command + docs/deploy.md)
```

`git diff main origin/dev` sobre `pom/services.py`, `pom/grading_utils.py`, `pom/grading_regime.py`,
`models_app/views.py`, `models_app/services.py` i `frontend/src/components/grading/GraduacioSuperficie.jsx`
és **buit**: els sis fitxers del camí són **idèntics byte a byte**.

→ **El comportament de dev és exactament el de main.** El que es trobi aquí, hi és igual. Compte:
`dev` va **enrere** de `main` (20+ commits); un fix fet sobre `dev` no arriba a PROD fins que
`main` el reculli.

### A.5 · Defectes REALS trobats en aquest camí (censats, no tocats)

**Defecte 1 — `increment` és una segona veritat oculta que cap superfície actualitza.**
`set_pom_regim_view` només escriu `logica`, `increment_base`, `increment_break`,
`talla_break_label`/`_pos` (`models_app/views.py:5202-5220`); **mai `increment`**. El payload de
la taula tampoc el serveix (`models_app/views.py:2141-2144`) i la UI tampoc l'envia
(`GraduacioSuperficie.jsx:220-226`). Per tant `increment` es queda per sempre amb el valor
**materialitzat del joc** (`models_app/services.py:~370`, `increment=r.increment`).

`_apply_rule` (`pom/services.py:1186`) entra a la branca canònica **només si
`increment_base is not None`**; si és `None`, cau a `pom/services.py:1197-1198`:

```python
if grading_type == 'LINEAR':
    return base_val + (steps * increment), 'LINEAR'     # ← `increment` = el del JOC ANTIC
```

Buidar el camp «Δ base» a la pantalla envia `increment_base: null`
(`GraduacioSuperficie.jsx:114-118` + `:222`) i **passa la validació** si hi ha break
(`pom/grading_regime.py:63`, `te_break`). Resultat: es desa amb 200 OK, la pantalla ensenya la
cel·la buida, i **el motor gradua amb el delta del joc**. **Això és, literalment, «propagar amb
la regla vella».**

Magnitud a `fhort` avui:
- `ModelGradingRule` LINEAR actives: **1332**
- amb `increment != increment_base`: **137** (p. ex. `MGR#2270` BRW-SS26-0004 `A.2`:
  `increment=1.2` vs `increment_base=1.0`; `MGR#2112` BRW-FW26-0016 `F~1`: `0.0` vs `1.0`)
- amb `increment_base IS NULL`: **0** → el defecte és **armat però encara no disparat**.
- Al 1215, POM `D`: `increment=2.00` contra `increment_base=0.50`.

**Defecte 2 — el lookup d'edició no filtra `actiu`.** V. hipòtesi (c) a §A.3.
`models_app/views.py:5173` i `models_app/views.py:2534`.

**Defecte 3 — `gravar_pom_view` escriu la regla SENSE l'eix `garment`.**
`models_app/views.py:2534`: `ModelGradingRule.objects.filter(model=model, pom_id=pom_id).first()`,
i el constructor de `:2535-2547` no informa `garment` (cau al default `''`). La germana
`set_pom_regim_view` sí que el resol (`models_app/views.py:5170`, SET-2/#12d). Amb una sola peça
és un no-op; el dia que hi hagi un `'02'`, desar la taula de POM des de la 02 escriurà sobre la
regla de la mare — el vermell exacte que #12d va tancar a l'altra porta.

**Defecte 4 — LINEAR amb `ib=0 · brk=0` i break informat passa la validació i no gradua res.**
`es_linear_degenerada` (`pom/grading_regime.py:58-65`) retorna `False` si hi ha
`talla_break_label`, encara que tots dos deltes siguin 0. Al 1215 hi ha **5** regles així
(`G1`, `SLT`, `EK2`, `E5`, `U`: `LINEAR ib=0.00 brk=0.00 break M`). Produeixen una taula
**plana** —el valor base repetit— però es presenten com a LINEAR. És exactament la mentida que
la llei d'A3 volia tancar, entrant per la porta del break.

**Defecte 5 — `talla_break_pos` és una columna morta i divergent.**
`set_pom_regim_view` la calcula contra `model.size_run_model` (`models_app/views.py:5216-5220`),
però el motor resol el break **per etiqueta** contra el **run del SISTEMA**
(`grading_utils._break_idx_de:992` cridada des de `increment_de_l_aresta:1025` amb `run=run_sistema`).
Cap lector del motor la consulta. Al 1215 conviuen files amb `break_pos=2` i files amb
`break_pos=None` per al mateix break.

**Defecte 6 — dos criteris per triar el SizeFitting.** Propagar fa
`SizeFitting.objects.filter(model=model).first()` (`models_app/views.py:3027`, ordering
`['model','numero']` → el de numero més baix). Els lectors i el gate de presa fan
`_resolve_working_size_fitting` (`fitting/services.py:877`), que **prefereix el que té versió
activa**. Amb un sol SF coincideixen (cas del 1215); amb dos poden divergir i propagar escriuria
en un SF que la pantalla no llegeix. A `fhort` hi ha models amb 2 SF (p. ex. `LOS-SS27-0001`:
SF#71 i SF#72; `LOS-SS27-0834`: SF#1050 i SF#1057).

---

<a id="b"></a>
## B. GATING «MESURAR PRENDA» EXIGEIX PROPAGAT

### B.1 · El guard dur (backend) — un de sol

```python
# backend/fhort/fitting/services.py:503-507
version = _active_grading_version(sf)
if version is None:
    raise ValueError(
        f"El model {model.codi_intern} no té cap GradingVersion activa. "
        "Cal generar les talles primer.")
```

Viu a `create_piece_fitting` (`fitting/services.py:480`), exposat com
`POST /api/v1/fitting-sessions/<pk>/create-piece/` (`fitting/views.py:186-192`).

**Què comprova exactament:** `GradingVersion` **activa** del SizeFitting de treball
(`_active_grading_version`, `fitting/services.py:889`). No comprova `SizeFitting` (el crea si
falta, `fitting/services.py:496-501`) ni `GradedSpec` (si no n'hi ha, la peça neix amb 0 línies i
`reconcilia_linies` la posa al dia). No comprova `SizeFitting.estat`.

### B.2 · El guard tou (frontend) — el mateix predicat, dit abans

```js
// frontend/src/utils/motiuPasPresa.js:41-47
export function motiuPasPresa(estatPas) {
  if (estatPas == null) return null
  if (estatPas.te_taula) return null
  if (!estatPas.te_mesures) return 'model_sheet.pas_sense_mesures'
  if (!estatPas.te_regles) return 'model_sheet.pas_sense_regles'
  return 'model_sheet.pas_sense_propagacio'
}
```

`te_taula` el serveix `grading_status_view` (`models_app/views.py:3802`), definit a
`models_app/views.py:3858-3859`:

```python
te_taula = bool(gv and gv.is_active and GradedSpec.objects.filter(
    grading_version=gv, is_active=True).exists())
```

→ **el front és MÉS estricte que el backend**: exigeix a més que hi hagi `GradedSpec` actives.

### B.3 · Cens complet de qui comparteix aquest guard

| Superfície | Àncora | Predicat |
|---|---|---|
| Botó ③ «Mesurar prenda» del stepper | `frontend/src/pages/ModelSheet.jsx:1300-1313` | `motiuPresa != null` (= `!te_taula`) |
| Botó «Mesurar set» (tab Escalat) | `frontend/src/pages/ModelSheet.jsx:822-833` (mateix `estatPas`) | idem — nota E3b: «la MATEIXA dependència que el ③» |
| `create-piece` (API) | `fitting/views.py:186` → `services.py:503` | versió activa |
| `resolvePieceFitting` (obre la peça de la sessió) | `frontend/src/components/model/measureSources.jsx:53-68` | propaga el 400 del backend |
| `CheckMeasureEditor` (traducció del 400) | `frontend/src/components/model/CheckMeasureEditor.jsx:494-508` | `/GradingVersion\|talles/i` → `fitting.save.no_grading` |
| `seal_model_grading` | `fitting/services.py:958` | versió activa (segellar, no mesurar) |
| Panell de govern del model | `models_app/views.py:4271` | només informa |

### B.4 · Frontera E1–E3: la presa **sí** depèn d'especs propagades. Documentat.

`create_piece_fitting` **clona cada `GradedSpec` en una `PieceFittingLine`**:

```python
# backend/fhort/fitting/services.py:517-539
specs = GradedSpec.objects.filter(grading_version=version, is_active=True)...
for spec in specs:
    PieceFittingLine.objects.create(
        piece_fitting=pf, pom=spec.pom, size_label=spec.size_label,
        capa=spec.capa, instancia=spec.instancia, garment=spec.garment,
        valor_teoric=spec.graded_value_cm,
        valor_real=spec.graded_value_cm)     # còpia, editable
```

Tot seguit `reconcilia_linies(pf)` (`fitting/services.py:546` → `:579`) posa la peça al dia amb el
model viu.

I la porta de presa de l'Escalat **no crea línies**: `desa_presa_escalat`
(`fitting/services.py:~187`) busca la línia i, si no hi és, alça `PresaSenseLiniaError`
(`fitting/services.py:135-138`); sense peça viva, `PresaNoObertaError` (`:131`).

→ **La presa del set és, literalment, la corba propagada convertida en fulls de treball.** Sense
`GradedSpec` no hi ha línies i no hi ha on anotar. Aquesta és la dependència estructural, no un
`if` que es pugui afluixar.

El guard de l'eix base **ja està partit** (E1/B1): PRENDRE es permet a qualsevol talla, DECIDIR
només a la base (`fitting/services.py:100-107`, `fitting/test_e1_guard_partit.py:1-32`).

### B.5 · Cens del cost de relaxar-lo a «propagar exigeix graduació; mesurar prenda NO exigeix propagat»

**No proposo el fix** (ordre del brief). El cost, per capes:

| Capa | Què s'hi ha de decidir | Àncora | Cost |
|---|---|---|---|
| **Domini** | D'on surt `valor_teoric` d'una línia si no hi ha `GradedSpec`? Avui la línia **és** una còpia de l'spec. Les opcions són: (a) línies només de talla base des de `BaseMeasurement`; (b) línies amb `valor_teoric=NULL`; (c) generar els specs en obrir la presa. Cap és neutra. | `fitting/services.py:517-539` | **Decisió d'Agus. Bloquejant.** |
| **Backend** | `create_piece_fitting` ha de saber néixer sense versió: crear la `GradingVersion` buida o admetre `grading_version=NULL`. `PieceFitting.grading_version` és FK **no nul·lable** (`fitting/models.py:~440`) → **migració**. | `fitting/services.py:503-515` | Mitjà + migració |
| **Backend** | `reconcilia_linies` ja sap crear línies que l'spec no porta (`fitting/services.py:640-660`), però es recolza en la talla base o l'spec: cal revisar el `continue` de `:640`. | `fitting/services.py:579-668` | Baix-mitjà |
| **Backend** | `consolidate_base_from_fitting` (`fitting/services.py:669`) i `close_piece_fitting` (`:740`) llegeixen `pf.grading_version.size_fitting` (`:685`) → petarien amb versió nul·la. | | Mitjà |
| **API estat** | `te_taula` deixa de ser el predicat del pas ③; caldria un `te_presa_possible` nou (o `te_mesures && te_regles`). Dos predicats per a la mateixa porta és el que `grading_status_view` diu explícitament que no vol (`models_app/views.py:3833-3837`). | `models_app/views.py:3858` | Baix |
| **Front** | `motiuPasPresa` i el seu banc (`frontend/src/utils/motiuPasPresa.test.js`); `ModelSheet.jsx:1300`; `ModelSheet.jsx:822` (Mesurar set); traducció del 400 a `CheckMeasureEditor.jsx:498-506`. | | Baix |
| **Q8 / fitxa** | `filesFitting`/`filesSizeSet` (`frontend/src/utils/taulesQ8.js:89, 118`) llegeixen el grid; una presa sense teòrica deixa `Aprovada`/`Dif` buides. Cal decidir si això és legítim al document. | | Baix, però visible al PDF |
| **Regla d'Agus «propagar exigeix graduació»** | **ja es compleix**: `generate_grading_view` refusa amb 400 si `not _te_regles(model)` (`models_app/views.py:3014-3016`), i el front hi porta abans (`ModelSheet.jsx:944`). **Cap canvi.** | | Zero |

---

<a id="c"></a>
## C. SELECTOR DE JOC DE GRADUACIÓ — SCROLL INFINIT

### C.1 · El component és un de sol, i no acota res

`frontend/src/components/grading/RuleSetPicker.jsx` (208 línies). El render és:

```jsx
// frontend/src/components/grading/RuleSetPicker.jsx:96-113
return (
  <div style={{ marginTop: 8 }}>            {/* ← cap maxHeight, cap overflow */}
    {matches.map(({ rs, compatible, motius }) => (
      <PickCard ... />
    ))}
  </div>
)
```

- **No pagina.** Cap `page`, cap `slice`, cap virtualització.
- En mode `eliminatiu` **no exclou res**: `classifyRuleSets` només reordena i atenua
  (`RuleSetPicker.jsx:38-44`).
- **Cap contenidor amb alçada.** El `<div>` de `:97` no porta `maxHeight` ni `overflowY`.

### C.2 · Cens de TOTS els punts on es tria joc de regles

| # | Superfície | Component / muntatge | Endpoint i params | Pagina? | Filtra actiu? | Filtra client? | `size_system`? | Alçada |
|---|---|---|---|---|---|---|---|---|
| 1 | **Graduació del model** (contenidor central, «Triar joc» / «Canviar de joc») | `components/grading/GraduacioContenidor.jsx:110` (muntat a `pages/ModelSheet.jsx:14`) | `gradingRuleSets.list({page_size:200, amb_regles:1})` — `GraduacioContenidor.jsx:44` | **No** (1 pàgina de 200) | **NO** | **NO** al servidor; només **ORDENA** pel client del model — `:59-67` | **NO** (mode `eliminatiu`) | **CAP** |
| 2 | **Resum partit** («Canviar joc» des del Resum) | `components/model/ResumWizardPartit.jsx:1230` | `gradingRuleSets.list({page_size:200, amb_regles:1})` — `:1188` | **No** | **NO** | **NO** | **NO** (`eliminatiu`) | **CAP** (el `maxHeight:320` de `:1042` és de la llista de **sistemes de talles**, no d'aquest picker) |
| 3 | **Wizard de model, pas 4** | `components/grading/GraduacioPanel.jsx:149` (muntat a `pages/ModelWizard.jsx:866`) | `gradingRuleSets.list({page_size:200, amb_regles:1})` — `GraduacioPanel.jsx:46` | **No** | **NO** | **NO** | **SÍ** (`strict` + `sizeSystemId`, `:153-154`) | **CAP** |
| 4 | **Autoria d'ítem** (llibreria) | `pages/ItemAuthoring.jsx:328` | `gradingRuleSets.list({page_size:200, amb_regles:1})` — `:97` | **No** | **NO** | **NO** | **NO** (`eliminatiu`) | **CAP** |
| 5 | **Fitxa de client** (llista informativa, no picker) | `pages/CustomerDetail.jsx:304` | `gradingRuleSets.list({customer: customer.id})` | Paginació DRF per defecte | **NO** | **SÍ** | — | `maxHeight:160, overflowY:auto` (`:722`) |
| 6 | **Gestió de jocs** (CRUD, no assignació) | `components/grading/JocsDeRegles.jsx:954` | `gradingRuleSets.list({page_size:200, page})` — **amb bucle de pàgines** | **SÍ** | **NO** | **NO** | — | pròpia |
| 7 | **Targeta del joc assignat** (lectura) | `components/model/RuleSetCard.jsx:20` | `gradingRuleSets.get(id)` | — | — | — | — | — |

**Backend:** `GradingRuleSetViewSet` (`backend/fhort/pom/views.py:223`).
`filterset_fields = ['actiu','garment_group','size_system','customer']` (`pom/views.py:251`) —
**els filtres HI SÓN, i cap dels quatre pickers els fa servir**. L'únic opt-in que s'usa és
`?amb_regles=1` (`pom/views.py:255-262`), que només amaga els contenidors buits.

### C.3 · Magnitud real a PROD (`fhort`)

```
GradingRuleSet totals: 52   ·   actius: 34   ·   jubilats (actiu=False): 18
amb regles (>0): 51         ·   d'aquests, actius: 33
clients distints amb joc propi: 3 (BRW, LOS, i NULL/catàleg)
```

→ Els quatre pickers en mode `eliminatiu` pinten **51 targetes** en un `<div>` sense sostre.
**18 d'elles són jocs JUBILATS** (`actiu=False`), i s'ofereixen com a triables:
`#103 BRW EU ALPHA TOP KNIT`, `#102 BRW WOMEN WOVEN REGULAR BLUSA`, `#150 Custom Alpha EU — Women`,
`#93 EU Knit Baby Months`, `#80 EU Knit Woman Slim`, `#82 EU Stretch Woman Bodycon`,
`#92 EU Woven Dress Flared`, `#85 EU Woven Man Slim`, `#78/#77/#76 EU Woven Woman *`,
`#96/#98 Importació fitxa · LOS-*`, `#149/#147/#146/#148 Textiles y Confeccions Brownie SL · *`,
`#105 Textiles … Tops · BRW`.

I dels 51, **24 són jocs LOS** (v. §I.3) que a un model de TRV o BRW no li serveixen de res.

### C.4 · Relació amb el deute conegut «el selector del wizard no filtra ni actiu ni client»

**Confirmat i ampliat: no és el wizard, són els QUATRE punts.** El deute és més gran del que deia.
El wizard (punt 3) és, de fet, l'**únic** que acota alguna cosa (`strict` + `sizeSystemId`).
Els punts 1, 2 i 4 van en `eliminatiu`, que per llei C5 (`RuleSetPicker.jsx:25-28`) **ordena i no
amaga** — decisió deliberada, però pensada per a un catàleg petit.

### C.5 · Llista unificada de punts a tocar (cens, sense proposta de fix)

1. `frontend/src/components/grading/RuleSetPicker.jsx:96-113` — l'únic lloc on afegir sostre
   d'alçada i/o virtualització; el toc arriba als 4 pickers de cop.
2. `frontend/src/components/grading/RuleSetPicker.jsx:36-53` — `useMemo` de `matches`: on entraria
   un sedàs d'`actiu` sense trencar `classifyRuleSets`.
3. `frontend/src/components/grading/GraduacioContenidor.jsx:44` — params de la crida.
4. `frontend/src/components/model/ResumWizardPartit.jsx:1188` — params de la crida.
5. `frontend/src/components/grading/GraduacioPanel.jsx:46` — params de la crida.
6. `frontend/src/pages/ItemAuthoring.jsx:97` — params de la crida.
7. `frontend/src/components/grading/gradingAxes.js` — `classifyRuleSets`/`matchingRuleSets`:
   on viuria un eix de **client** com a criteri d'atenuació (avui `GraduacioContenidor.jsx:59-67`
   se'l fa a mà i els altres tres no el tenen).
8. `backend/fhort/pom/views.py:251-262` — el `filterset` ja ho suporta tot; només caldria decidir
   si `?actiu=true` es passa des del client o si `?amb_regles=1` s'amplia.
9. **Cap toc de dades.** No cal jubilar ni esborrar cap joc per a aquest tram.

---

<a id="d"></a>
## D. CREAR POM NOU AL CATÀLEG

### D.1 · Existeix l'API? **SÍ — i n'hi ha TRES.**

| # | Endpoint | Vista | Permisos | Efectes |
|---|---|---|---|---|
| 1 | `POST /api/v1/poms/` (ViewSet REST) | `POMMasterViewSet` — `backend/fhort/pom/views.py:54-63` | **`[IsAuthenticated]` sec** (sense `_ConfigureWrite`, a diferència de `SizeSystemViewSet:87-90`) | Crea `POMMaster` pelat. Cap àlies, cap validació de col·lisió. |
| 2 | `POST /api/v1/poms/crear-tenant/` | `create_tenant_pom_view` — `pom/wizard_views.py:729-767`; URL `pom/urls.py:52` | `IsAuthenticated` | Crea `POMMaster` amb `codi_client`, `nom_client`, `categoria_id`, `notes`. Valida només duplicat exacte de `codi_client` (`:748`). **No crea àlies.** |
| 3 | `POST /api/v1/models/<id>/pom-propi/` | `create_model_pom_view` — `pom/wizard_views.py:772-905`; URL `models_app/urls.py:127` | `IsAuthenticated` | **La porta bona.** Valida col·lisió al catàleg del client (409 `NOMENCLATURA_OCUPADA`, `:820-828`) i al catàleg de la casa (409 `CODI_CASA_OCUPAT`, `:848-857`); crea `POMMaster` + **`CustomerPOMAlias`** amb `origen='MODEL'` (`:889-897`). |

### D.2 · Què falta exactament

**Només la UI del POMBrowser.** El `POMBrowser` (`frontend/src/components/POMBrowser/POMBrowser.jsx`,
700 línies) té:
- cercador al catàleg + **assignar** un POM existent a l'ítem (`:140`, `:305-331`),
- treure (`:169-176`), marcar KEY (`:183-190`), reordenar (`:203-216`),
- **cap botó de crear.** Cap referència a `poms.crearTenant` ni a `pomPropi` a tot el fitxer.

Els clients vius de la creació són:
- `frontend/src/api/endpoints.js:254` — `poms.crearTenant` → **sense cap cridador al front**.
- `frontend/src/api/endpoints.js:267` — `pom-propi` → cridat des de
  `frontend/src/components/EditableTable/EditableTable.jsx:1049-1053` (modal `pomPropi`, la taula
  de **Mesures**, amb `modelId` obligatori).

→ **El gest existeix, però només des d'un model.** Al catàleg pelat (POMBrowser, 645 POMs) no hi
ha porta, i la que hi hauria (`crear-tenant`) no crea àlies, o sigui que el POM naixeria **sense
existir per a cap client**.

### D.3 · Camps obligatoris per néixer

**Model `POMMaster`** (`pom/models.py`, camps: `id, pom_global, categoria, codi_client, nom_client,
notes, actiu, tolerancia_default_minus, tolerancia_default_plus, pendent_revisio, origen_import`).

| Camp | Obligatori? | Qui l'imposa |
|---|---|---|
| `codi_client` | **SÍ** (i únic case-insensitive: constraint `uniq_pommaster_codi_client_ci`) | `wizard_views.py:742-743` i `:848-857` |
| `nom_client` | **SÍ** | `wizard_views.py:742-743` / `:801-803` |
| `categoria` | **NO** (nullable) — però 319 dels 645 POMs de `fhort` la tenen a `NULL` | — |
| `pom_global` | **NO** — sense ell el POM és *tenant-only* (no lliga amb el catàleg canònic de `public`, 290 `POMGlobal`) | — |
| `pendent_revisio` | el posa a `True` la porta bona | `wizard_views.py:866` |
| `origen_import` | referència d'origen (`model:<codi_intern>`) | `wizard_views.py:879` |
| **`CustomerPOMAlias`** | **el que el fa EXISTIR per al client**: `customer`, `pom`, `client_code`, `description_en`, `origen='MODEL'` | `wizard_views.py:889-897` |
| **capes / instàncies** | **NO en néixer.** El POM no porta capa ni instància: les porten les MESURES (`BaseMeasurement.capa/instancia/garment`). | `models_app/models.py` (unicitat de 5 camps) |

### D.4 · Efectes col·laterals d'un POM nou

| Efecte | Passa? | Àncora |
|---|---|---|
| **Àlies de client** | Sí per la porta 3; **no** per les portes 1 i 2 | `wizard_views.py:889-897` |
| **Validació de col·lisió** | Sí per la porta 3 (dos 409 distints); **no** per les 1 i 2 | `wizard_views.py:820-857` |
| **Cua de revisió de la Montse** | Sí: `POMMaster.pendent_revisio=True` + `CustomerPOMAlias.pendent_revisio=True` | `wizard_views.py:866`, `:896` |
| **GTI / sembres** (`GarmentPOMMap`, `GarmentTypePOMMap`, `GarmentGroupPOMMap`) | **CAP** automàtic. El POM neix fora de tota sembra; s'hi entra pels ViewSets `pom/urls.py:31-33` o pel POMBrowser. | — |
| **Acumulació** (`pom/acumulacio.py`) | El POM no apareixerà a cap acumulació d'ítem/tipus/grup fins que algú el mapegi | — |
| **Regla de graduació** | **CAP.** Un POM nou no té ni `GradingRule` ni `ModelGradingRule` → llei D2 de cel·la absent: si algú li dona base sense regla, **no emet cap cel·la** (`pom/services.py:257-290`) i queda al log de cobertura parcial (`pom/services.py:334-339`) | |
| **Traducció / nomenclatura** | Sense `pom_global`, `nom_ca`/`nom_en` queden buits i les pantalles cauen a `codi_client` | `models_app/views.py:2130-2135` |
| **Esborrar-lo després** | `GradedSpec.pom` és **PROTECT** (`fitting/models.py:212`) i `ModelGradingRule.pom` també (`models_app/models.py:1186`) → un cop usat, no s'esborra | |

**Orfes ja existents a `fhort` (senyal del cost d'una porta sense àlies):** dels 645 `POMMaster`,
**153 no els cita ni cap joc ni cap model**.

---

<a id="e"></a>
## E. REGLA STEP SENSE VALORS A L'ESCALAT

### E.1 · Comportament actual, traçat

**Al motor.** `_apply_rule` (`pom/services.py:1144`), branca STEP:

```python
# pom/services.py:1186 — la branca canònica NO agafa STEP, encara que increment_base hi sigui
if grading_type != 'STEP' and getattr(rule, 'increment_base', None) is not None: ...

# pom/services.py:1200-1207
elif grading_type == 'STEP':
    vs = rule.valors_step
    if not isinstance(vs, dict) or not vs:
        _add_warning(warnings,
            f"Regla STEP del POM {pom_codi}: valors_step buit o invàlid; cap cel·la calculada.")
        return None, 'STEP'
```

`generate_graded_specs` recull aquest `None` a `pom/services.py:301-303`:

```python
if graded_val is None:
    # Hard STEP validation failed for this cell: leave it uncomputed.
    continue
```

→ **Cap `GradedSpec` per a aquell POM. Cap cel·la a l'escalat.** El POM no entra a `sense_regla`
(té regla; el que no té són valors), o sigui que **tampoc surt a l'avís de cobertura parcial**
(`pom/services.py:334-339`). El senyal viu **només** a `warnings`, que
`generate_graded_specs` retorna al final i que el payload de propagar arrossega — però la fila
desapareix i el tècnic no veu per què.

Si el POM és l'únic del model, la propagació peta amb `ValueError` (`pom/services.py:322-331`);
si no, **desapareix en silenci visual**.

**A l'edició.** `set_pom_regim_view` intenta evitar-ho sembrant els deltes des dels specs vigents:

```python
# backend/fhort/models_app/views.py:5224-5225
if rule.logica == 'STEP' and not rule.valors_step:
    rule.valors_step = _sembra_step_des_dels_specs(model, rule.pom_id) or None
```

`_sembra_step_des_dels_specs` (`models_app/views.py:5073-5117`) **retorna `{}`** si el model
encara no té `GradingVersion` vigent (`:5100-5102`) o si no hi ha specs de l'exterior/instància
única (`:5111-5112`) o si la geometria és incompleta (`:5114-5116`).

→ **El forat exacte del brief:** un POM que té mesures de talla base però el model **encara no ha
propagat mai** (o aquell POM no té specs) passa a STEP amb `valors_step = NULL`, i la propagació
següent no emet **cap** cel·la per a ell.

**Cas viu a PROD:** `MGR#82` — model `LOS-SS26-0001` (178), POM `S.R6` (441),
`logica=STEP`, `valors_step=None`, `origen=MANUAL`, `increment=0.00`, `increment_base=0.00`.
Base: `('exterior','', 0.0, True)` — a més val **0.0**, que la llei D2 exclou de la propagació
(`pom/services.py:1010-1013`). És l'única regla STEP sense valors de tot `fhort`
(45 `GradingRule` STEP al catàleg, **totes** amb `valors_step` informat; 27 `ModelGradingRule`
STEP, **1** sense).

### E.2 · Cens del cost de la proposta d'Agus (NO implementada)

> «portar el valor de talla base a totes les talles, marcat en vermell + avís *posar a mà*»

| Capa | Què caldria | Àncora | Cost / risc |
|---|---|---|---|
| **Motor** | Que la branca STEP-sense-valors deixi d'emetre `None` i emeti `base_val` a totes les talles | `pom/services.py:1200-1207` | **ALT · zona intocable** (CLAUDE.md «Zones intocables»). I xoca de cara amb la llei D2 de cel·la absent (`pom/services.py:257-290`), que existeix precisament perquè el motor **no fabriqui** un FIXED que sembli graduació (el cas del model 163: 225 specs 100% FIXED, delta 0, 200 OK). |
| **Alternativa sense tocar el motor** | Sembrar `valors_step` amb zeros en el moment del pas a STEP quan la sembra des dels specs torni buit | `models_app/views.py:5224-5225` | **BAIX.** Un delta 0 per talla dona exactament la corba plana demanada, i el motor no es toca gens. **Però** deixa la marca sense lloc (v. sota). |
| **On viu la MARCA** | **`GradedSpec` NO té camp d'origen** (llei). Camps reals: `grading_version, pom, size_label, graded_value_cm, grading_type_applied, increment_applied_cm, is_active, generated_from_version, capa, instancia, garment` — `fitting/models.py:209-255`. L'únic camp semàntic és `grading_type_applied` (`STEP/LINEAR/FIXED/ZERO/EXCEPTION`). | | — |
| **Alternatives per a la marca (censades, no decidides)** | **(a)** nova opció a `GRADING_TYPE_CHOICES` (p. ex. `STEP_PENDENT`) → migració de choices + tots els lectors que llegeixen `grading_type_applied` (`fitting/graded_spec_views.py:143`, `frontend/src/utils/cellaEscalat.js`, Q8). **(b)** camp nou a `GradedSpec` → migració + trencar la llei «GradedSpec no té origen». **(c)** **derivar-ho al lector**: la marca no és una dada de l'spec sinó de la REGLA (`logica='STEP'` i `valors_step` buit/tot-zero), i el payload de `taula-mesures` ja serveix `logica` (`models_app/views.py:2141`) → **cost zero de dades**. **(d)** `Watchpoint` per POM (`models_app.Watchpoint`, ja usat a `models_app/views.py:3115-3124`). | | (c) és la de menys radi |
| **UI (vermell + avís)** | Cel·la de l'escalat: `frontend/src/utils/cellaEscalat.js`; taula de mesures: `EditableTable.jsx:1416`; graduació: `GraduacioSuperficie.jsx:323`. Tokens obligatoris (llei G8): `--err`/`--err-bg` o `--warn-state`/`--warn-state-bg`/`--warn-ink`. **Mai hex.** | | Baix |
| **i18n** | Clau nova × 3 idiomes (`frontend/src/i18n/{ca,en,es}.json`) | | Baix |
| **Efecte sobre el SIZE SET posterior** | **Aquest és el cost seriós.** `create_piece_fitting` clona cada spec en una `PieceFittingLine` amb `valor_teoric = valor_real = graded_value_cm` (`fitting/services.py:530-538`). Amb la proposta, la presa naixeria amb **el valor base repetit a totes les talles com a TEÒRICA**. Conseqüències mesurables: (1) `Dif` = 0 a totes les talles → la taula Q8c de size set diria «va arribar clavada» a tot arreu (`taulesQ8.js:118-142`, `cellaDif` a `TechSheetEditor.jsx:5283-5291` pinta buit quan Dif=0); (2) `linia_te_contingut` (`fitting/esdeveniments.py:28`) i el Repàs canviarien de resposta; (3) `consolidate_base_from_fitting` només consolida la talla base (`fitting/services.py:~700`) → no contamina `BaseMeasurement`, **però** una teòrica falsa a les altres talles sí que arriba al PDF de la fitxa. | | **ALT · cal decisió d'Agus** |
| **Paritat** | Qualsevol toc del motor exigeix banc. **A PROD el banc no existeix** (v. §Contradiccions §3). | | Bloquejant si es toca el motor |

---

<a id="f"></a>
## F. MULTI-BREAK (FINS A 3 BREAKS PER POM) — CENS

### F.1 · Forma canònica actual

**Camps** (idèntics a les dues taules):

| Camp | `pom.GradingRule` | `models_app.ModelGradingRule` | Àncora |
|---|---|---|---|
| `logica` | ✔ (`LOGICA_CHOICES`) | ✔ | `models_app/models.py:1191` |
| `increment` (legacy uniforme) | ✔ | ✔ `DecimalField(6,2) null` | `models_app/models.py:1195` |
| `valors_step` | ✔ | ✔ `JSONField null` | `models_app/models.py:1196` |
| **`increment_base`** | ✔ | ✔ `DecimalField(6,2) null` | `models_app/models.py:1200` |
| **`increment_break`** | ✔ | ✔ `DecimalField(6,2) null` | `models_app/models.py:1201` |
| **`talla_break_label`** | ✔ | ✔ `CharField(30) null` | `models_app/models.py:1202` |
| `talla_break_pos` | ✔ `pom/models.py:1519` | ✔ (cache, **mai llegida**) | `models_app/models.py:1203` |
| `garment` | **NO, i mai** (llei: el joc és del catàleg) | ✔ `CharField(20) default=''` | `models_app/models.py:1240-1245` |
| Unicitat | — | `('model','pom','garment')` | `models_app/models.py:1252` |

→ **UN sol break per regla, i és un parell escalar `(label, increment_break)`.** No hi ha cap
estructura de llista.

**`_apply_rule`** (`pom/services.py:1144`) delega tot el relleu a
`grading_utils.desnivell_entre_talles`:

```python
# pom/services.py:1186-1195
if grading_type != 'STEP' and getattr(rule, 'increment_base', None) is not None:
    from fhort.pom.grading_utils import desnivell_entre_talles
    if size_idx == base_idx:
        return base_val, grading_type
    return (base_val + desnivell_entre_talles(
        rule, size_run, base_idx, base_idx, size_idx), grading_type)
```

**`break_idx`** — el punt únic (`pom/grading_utils.py:992-1004`):

```python
def _break_idx_de(rule, run):
    tbl = getattr(rule, 'talla_break_label', None)
    if not tbl or not run: return None
    norm = [_norm(x) for x in run]; tn = _norm(tbl)
    return norm.index(tn) if tn in norm else None
```

**Mecànica d'arestes** (`pom/grading_utils.py:1006-1031`) — **el node que el multi-break ha de
generalitzar**:

```python
aresta   = min(i, j)                                  # l'aresta viu entre `aresta` i `aresta+1`
exterior = aresta + 1 if aresta >= base_idx else aresta
return brk if exterior >= break_idx else ib           # ← DOS trams, un llindar
```

**Espai de sistema (llei S24b).** `run` és **sempre el run del SISTEMA**, no el del model:
`escala_del_model` (`pom/services.py:164-...`) retorna `run_sistema` i `_apply_rule` el rep com a
`size_run` (`pom/services.py:296-298`). El break, doncs, es resol per etiqueta contra el sistema
sencer (al 1215: `XXS·XS·S·M·L·XL·XXL·3XL`), encara que el model només en fabriqui cinc.

### F.2 · Superfícies que mostren o editen la regla

| # | Superfície | Àncora | Mostra | Edita | Convenció de break |
|---|---|---|---|---|---|
| 1 | **Generar/editar regles del joc** | `components/grading/JocsDeRegles.jsx:769-830` | ✔ | ✔ (`gradingRuleSets.editRule` / `gradingRules.update`) | `aDocument`/`aMotor` — `:772`, `:829` |
| 2 | **Graduació del model** (superfície editable) | `components/grading/GraduacioSuperficie.jsx:443-470` (capçaleres) i `:323-380` (cel·les) | ✔ | ✔ → `models.setPomRule` → `set_pom_regim_view` (`models_app/views.py:5121`) | `aDocument`/`aMotor`/`opcionsDocument` — `:370-375` |
| 3 | **Mesures — consulta** (4 columnes en lectura) | `components/EditableTable/EditableTable.jsx:74-76` (`COLS_REGLA`) | ✔ | ✘ (retirada per ordre d'Agus 05/08, `EditableTable.jsx:29-42`) | `aDocument` — `:76` |
| 4 | **Mesures — `CheckMeasureEditor`** | `components/model/CheckMeasureEditor.jsx:130-230` | ✔ | ✔ → `models.setPomRule` (`:193`) | `aDocument`/`aMotor`/`opcionsDocument` — `:218-223` |
| 5 | **Escalat propagat** | `pages/PropagatedEditor.jsx:267` + `components/model/fittingGridAdapter.jsx:17,162` | ✔ (`etiquetaRegla`) | règim només (`setPomRegim`) | `aDocument`/`etiquetaRegla` |
| 6 | **Graella de fitting** | `components/model/MeasureGrid.jsx` (via `fittingGridAdapter`) | ✔ | ✘ | idem |
| 7 | **Fitxa tècnica Q8b** «Rule · Δ · Break · B.Size» | `frontend/src/utils/taulesQ8.js:202-227` (`filesGrading`) + `pages/TechSheetEditor.jsx:5404-5470` | ✔ | ✘ | **crua** al constructor (`taulesQ8.js:193-195`), traduïda just abans de pintar |
| 8 | **Gravar POM** (segona porta d'escriptura) | `models_app/views.py:2521-2569` | — | ✔ | `_break_pos` |
| 9 | **Serialització del joc** | `backend/fhort/pom/serializers.py:303` | ✔ | ✔ | — |
| 10 | **Federació** | `tenants/federation_service.py:733-746` i `:898-903` | — | ✔ (copia els 4 camps) | — |
| 11 | **Import / detecció** | `pom/grading_utils.py:413-462` (`forma canònica PEÇA A`), `pom/size_map_views.py:328,355,563,594,1001` | — | ✔ | — |
| 12 | **Preview del wizard** | `pom/wizard_views.py:607-640` | ✔ | — | — |

### F.3 · Cost estimat per capes

**① Model de dades (N breaks ordenats · unicitat de talla · només LINEAR)**

| Node | Cost | Nota |
|---|---|---|
| Forma de la dada | **ALT — decisió d'arquitectura, no de sprint** | Tres opcions incompatibles entre elles: **(a)** taula filla `GradingRuleBreak(rule, ordre, talla_label, increment)` ×2 (una per `GradingRule`, una per `ModelGradingRule`) — la neta, però duplica model i migració a `public` i a tots els tenants; **(b)** `JSONField breaks=[{talla, increment}]` a les dues taules — barata, però sense unicitat ni ordre a la BD; **(c)** tres parells plans (`_2`, `_3`) — 6 columnes noves × 2 taules, i tanca la porta a un quart break. |
| Migració | Mitjà | `models_app` (tenant, ×N schemas) + `pom` (SHARED: `public` **i** tenant, v. `models_app/models.py:1184-1189`) |
| Compatibilitat enrere | Obligatòria | 1332 `ModelGradingRule` LINEAR actives + 525 `GradingRule` de jocs LOS + la resta. El parell `(increment_break, talla_break_label)` ha de seguir llegint-se. |
| Restricció «només LINEAR» | Baix | El guard viu a `pom/grading_regime.py` (punt únic) + mirall `frontend/src/utils/gradingRegime.js` |
| Unicitat de talla entre breaks | Baix (a) / a mà (b,c) | |

**② Motor**

| Node | Cost |
|---|---|
| `_break_idx_de` (`grading_utils.py:992`) → ha de tornar una **llista ordenada** d'índexs | Baix |
| `increment_de_l_aresta` (`grading_utils.py:1006-1031`) → de «un llindar» a «tram per extrem exterior»: `for (idx_i, inc_i) in trams: if exterior >= idx_i: candidat = inc_i` | **Mitjà — és el node crític.** Cal conservar exactament la semàntica actual quan hi ha un sol break, i el sentit descendent (extrem exterior = l'etiqueta INFERIOR sota la base) |
| `desnivell_entre_talles` (`:1034`) | **Zero** — només suma arestes |
| `_apply_rule` (`services.py:1186`) | **Zero** — ja delega |
| `propaga_ancoratges` (`:1051`) | **Zero** — comparteix la mateixa aresta (és el que garanteix que propagar des de qualsevol talla reprodueixi la mateixa corba, `grading_utils.py:986-989`) |
| `es_linear_degenerada` / `te_break` (`grading_regime.py:43-65`) | Baix — ha de mirar N breaks |
| **Paritat QA** | **BLOQUEJANT · v. §Contradiccions §3**: a `fhort` de PROD **no hi ha banc**. `BANC-*`: 0 models. Models 1320/1322 (golden viu `scripts_tmp/golden_set2_T0_2026-08-10.json`, 280 cel·les): **no existeixen**. Models 268/269 («POP»): **no existeixen**. Model 163 (`BRW-FW26-0001`) **sí** existeix. Abans de tocar el motor cal reconstruir el banc a staging (`manage.py sembra_banc_paritat`, `scripts_tmp/golden_c3_snapshot.py`). |

**③ UI**

| Node | Cost |
|---|---|
| Signe `+` a la fila per afegir un break (màx. 3) | Mitjà — la fila de `GraduacioSuperficie` és una `<tr>` de columnes fixes (`AMPLADES` a `EditableTable.jsx:59`); N breaks vol dir **files expandibles o columnes dinàmiques** |
| `GraduacioSuperficie.jsx:220-226` — el payload per presència de clau | Mitjà — ha d'enviar la llista sencera, no camps solts |
| `CheckMeasureEditor.jsx:218-223` | Mitjà |
| `JocsDeRegles.jsx:769-830` | Mitjà |
| `EditableTable.jsx:74-76` (`COLS_REGLA`, lectura) | Baix — 4 columnes fixes → N |
| Validació «no repetits» + «ordenats» + «dins del run» | Baix (mirall de `grading_regime.js`) |
| Q8b (`taulesQ8.js:202-227` + `TechSheetEditor.jsx:5417`) | **Mitjà-alt** — l'amplada de la taula ja està calculada amb **sis columnes fixes** (`16 + wPom + 18 + 14 + 14 + 18`, `TechSheetEditor.jsx:5417`) i es reparteix en bandes per no passar l'A4; afegir columnes de break menja ample de talles |
| i18n × 3 | Baix |
| Tokens CSS (llei G8) | — |

**④ Serialització**

| Node | Cost |
|---|---|
| `pom/serializers.py:303` (`GradingRuleSerializer`) | Baix |
| `models_app/views.py:2141-2144` (payload de `taula-mesures`) | Baix |
| `models_app/views.py:5241-5254` (resposta de `set_pom_regim_view`) | Baix |
| `pom/wizard_views.py:607-640` (preview) | Baix |
| `pom/grading_utils.py:742-760` (`rule_to_spec`) i `models_app/services.py:390-430` (`..._from_specs`) | Mitjà |
| `tenants/federation_service.py:733-746`, `:898-903` | Mitjà — **contracte entre cases**: una casa amb multi-break i l'altra sense es perdria breaks en silenci |
| Comandes de sembra (`seed_losan_rules*.py`, `sembra_cataleg_v4*.py`, `seed_losan_master_delta.py`) | Baix, però són 6 fitxers |

### F.4 · Interacció amb el break conveni off-by-one

**L'estat exacte, verificat:**

```
DOCUMENT   l'ÚLTIMA talla del tram petit    ← com ho escriu el full del client
MOTOR      la PRIMERA talla del tram gran   ← com ho desa la BD (grading_utils._break_idx_de)
```
(`frontend/src/utils/breakConvention.js:1-24`)

La traducció és **només de presentació** i té acta de mesura: `aDocument`
(`breakConvention.js:47-50`) just abans de pintar, `aMotor` (`:57-61`) just abans de desar;
contrastat el 10/08 amb `ops/qa/qa_contrast_sembra3.py` — **142/142 casen, 0 divergències**
(`breakConvention.js:13-16`).

Les **cinc** superfícies que hi passen: `GraduacioSuperficie.jsx:11`, `EditableTable.jsx:25`,
`JocsDeRegles.jsx:11`, `CheckMeasureEditor.jsx:9`, `fittingGridAdapter.jsx:17`.
Q8b la deixa **crua** al constructor a posta (`taulesQ8.js:193-195`).

**Ho hereta o és l'ocasió de sanejar-ho? — CENSO, NO DECIDEIXO.**

*Arguments per HERETAR-HO:*
- El desplaçament és **pura presentació**; la dada no s'ha mogut mai i està mesurada.
- `opcionsDocument` (`breakConvention.js:66-69`) ja exclou l'última talla del run, que en
  convenció de document no és representable. Amb N breaks la regla es repeteix N vegades sense
  cap cas nou.
- Sanejar-ho vol dir **moure `talla_break_label` una posició a la BD** per a **98 regles LINEAR
  amb break** només al corpus mesurat el 10/08 (i 1332 LINEAR actives avui a `fhort`), amb
  regeneració obligada de tots els `GradedSpec`. `breakConvention.js:14-16` ho diu en lletra:
  *«moure la dada desplaçaria la graduació una talla sencera per a 98 regles»*.

*Arguments per SANEJAR-HO ARA:*
- Amb 3 breaks, cada superfície ha de fer la volta **3 vegades**, i «una superfície que en faci
  servir només una menteix» (`breakConvention.js:18`) passa de ser un risc a ser-ne tres.
- `opcionsDocument` retalla el run: amb 3 breaks el conjunt de combinacions vàlides
  (ordenades, no repetides, totes traduïbles) s'ha de validar **en convenció de document** i
  desar **en convenció de motor** — la finestra d'error creix quadràticament.
- Hi ha ja **un tercer** actor divergent: `talla_break_pos` es calcula contra el run del **MODEL**
  (`models_app/views.py:5216-5220`) mentre el motor resol contra el run del **SISTEMA**
  (§A.5, defecte 5). Amb multi-break això es multiplica per N.

**Frontera addicional a documentar:** el motor admet un break a una talla que el **sistema** té i
el **model** no (resol per etiqueta sobre `run_sistema`), però la UI només ofereix
`opcionsDocument(data.size_run)` — el run del **model** (`GraduacioSuperficie.jsx:375`). Amb un
sol break això ja és una asimetria; amb tres, cal decidir-la explícitament.

---

<a id="g"></a>
## G. UI — LOCALITZACIÓ (cap fitxer tocat)

### G.1 · Color de la columna de talla base «més fort del normal»

| Punt | Àncora | Valor actual |
|---|---|---|
| Capçalera de la columna base (Taula de Mesures) | `frontend/src/components/EditableTable/EditableTable.jsx:884` | `background: 'var(--sel)'` |
| Cel·la de la columna base (Taula de Mesures) | `frontend/src/components/EditableTable/EditableTable.jsx:1388` | `background: 'var(--sel)'` |
| Capçalera de la columna base (**Graduació**) | `frontend/src/components/grading/GraduacioSuperficie.jsx:447` | `background: 'var(--gold-pale)'` |
| Cel·la de la columna base (**Graduació**) | `frontend/src/components/grading/GraduacioSuperficie.jsx:323` | `background: 'var(--gold-pale)'` |

**⚠️ Ja hi ha divergència entre les dues taules germanes:** Mesures fa servir `--sel` (`#f7f5f2`)
i Graduació `--gold-pale` (`#f5e6d0`). Si el que es vol és «més fort a Graduació», el pas
`--sel` → `--gold-pale` **ja està fet allà** i el que falta és decidir el següent graó.

**Tokens disponibles per pujar de to** (`frontend/src/index.css`, tots ja definits — llei G8, mai hex):
`--sel #f7f5f2` (66) · `--fila-activa #fdf8ee` (44) · `--fila-capa #fbf6ee` (48) ·
`--fila-capa-activa #f7efdf` (49) · `--gold-pale #f5e6d0` (26) · `--model-band #f7efe1` (34) ·
`--bg-muted #f5f0e8` (14) · `--fila-neix #fdf2da` (45) · `--gold-border #e0c8a0` (31) ·
`--base-hairline #e3cfa3` (40, *«filet de la columna de talla base (graella fitting)»* — el token
fet exactament per a això, avui sense consumidor a EditableTable).

### G.2 · Inventari de divergències d'alineació per columna

| Taula | Columna | `textAlign` | Àncora |
|---|---|---|---|
| **Mesures** (`EditableTable`) | capçalera genèrica (`thS`) | `left` | `:83` |
| | banda de dimensions | `center` | `:843` |
| | nom / bateig | `right` | `:860` |
| | **talla base** | **`center`** | `:884` (th) · `:1388` (td) |
| | columnes configurables (`c.ample`) | `right` | `:902` |
| | dimensions | `center` | `:916` |
| | accions | `center` | `:921` |
| | cel·les de dimensió | `center` | `:1351`, `:1363` |
| | valor numèric | `right` | `:1378`, `:1416` (+`tabular-nums`) |
| | input de valor | `right` | `:1807` |
| **Graduació** (`GraduacioSuperficie`) | capçalera genèrica (`thS`) | `left` | `:62` |
| | **talla base** | **`right`** | `:447` (th) · `:323` (td) |
| | Δ / Δ break | `right` | `:468`, `:469` |
| | inputs numèrics | `right` | `:250` |
| | select de règim i de break | `left` | `:339`, `:372` |
| **Graella de fitting** (`MeasureGrid`) | cel·la de valor | `right` + `tabular-nums` | `:38` |
| | input | `right` | `:205` |
| | capçalera de nom | `left` | `:562` |
| | capçaleres de grup i de talla | `center` | `:597`, `:602`, `:606`, `:627`, `:634` |
| | subcapçalera de valor | `right` | `:642` |
| | subcapçalera de cua (`trailCols`) | `center` | `:648` |
| | peu | `center` | `:737` |

**Les tres divergències reals:**
1. **Talla base:** `center` a Mesures (`EditableTable.jsx:884/1388`) vs **`right`** a Graduació
   (`GraduacioSuperficie.jsx:447/323`). Són **la mateixa columna de la mateixa família de taules**
   (`AMPLADES` compartides, `EditableTable.jsx:59`).
2. **Columna de nom:** `right` a `EditableTable.jsx:860` vs `left` a `MeasureGrid.jsx:562`.
3. **`fontVariantNumeric: 'tabular-nums'`** hi és a `EditableTable.jsx:1416`,
   `MeasureGrid.jsx:38` i `GraduacioSuperficie.jsx:251`, **però no** a `EditableTable.jsx:1378`
   ni a `GraduacioSuperficie.jsx:323` — els números de la columna base **no** ballen igual que la resta.

### G.3 · Columna «Ve de»

| Node | Àncora |
|---|---|
| Clau i18n | `frontend/src/i18n/ca.json:140` → `"graduacio.superficie.col_origen": "Ve de"` (+ `origen_joc` `:141`, `origen_model` `:142`) i paritat a `en.json` / `es.json` |
| Capçalera | `frontend/src/components/grading/GraduacioSuperficie.jsx:463` |
| Càlcul del valor (`delJoc`) | `frontend/src/components/grading/GraduacioSuperficie.jsx:296-298` |
| Font del payload | `backend/fhort/models_app/views.py:2163-2164` (`regla_origen` + `regla_es_resident`) |

**Cost de retirar-la:**
- Front: treure `<th>` (`:463`), el `<td>` corresponent i el `const delJoc` (`:296-298`).
  **Vigilar `no-unused-vars`**: al repo és **error** de lint (v. l'acta de
  `docs/diagnosis/DIAGNOSI_Q8TER_RETIRADA_PANELL.md`), i `delJoc` quedaria orfe.
- i18n: 3 claus × 3 idiomes (`col_origen`, `origen_joc`, `origen_model`). **Compte:**
  `col_origen` existeix **també** a `grading.jocs.*` (`JocsDeRegles.jsx:1151`) i a
  `comprovacio.*` (`ComprovacioPanel.jsx:362`) — són **claus diferents**, no s'han de tocar.
- Backend: `regla_origen` i `regla_es_resident` **es queden** — `GraduacioSuperficie.jsx:296` no
  n'és l'únic lector potencial i són camps additius; retirar-los seria un segon tram.
- Amplades: la taula és `width:100%` amb totes les columnes fixades menys `#`; treure'n una fa que
  el sobrant se'n vagi a `#` (el forat documentat a `EditableTable.jsx:53-58`). **Cal revisar
  `AMPLADES`** (`EditableTable.jsx:59-61`).
- **Cost total: BAIX**, amb la vigilància de lint i d'amplades.

### G.4 · Taula de Mesures — color més suau + centrat

**Component:** `frontend/src/components/EditableTable/EditableTable.jsx`
(muntat a `components/model/MeasuresEntryPanel.jsx:3` i `components/model/CheckMeasureEditor.jsx:13`).

| Què | Àncora | Valor actual |
|---|---|---|
| Fons de la columna base | `:884` (th) i `:1388` (td) | `var(--sel)` (`#f7f5f2`) |
| Banda de dimensions | `:843` | `var(--gold-pale)` |
| Fila activa | via `--fila-activa` | `#fdf8ee` |
| Fila de capa germana | via `--fila-capa` / `--fila-capa-activa` | `#fbf6ee` / `#f7efdf` |
| Alineació de la base | `:884`, `:1388` | **ja `center`** |
| Alineació del valor | `:1378`, `:1416` | `right` |

→ **El «centrat» que falta no és el de la talla base (ja hi és): és el de les columnes de
VALOR** (`:1378`, `:1416`, `:1807`), avui a `right`. I «més suau» que `--sel` (#f7f5f2) només ho
és `--panel`/`--white` (#ffffff) o `--line-soft` (#f0eeea, que és MÉS fosc). **Cal que l'Agus
digui quina de les dues coses vol**, perquè el token més suau que `--sel` no existeix al sistema
sense estrenar-ne un — i estrenar token és decisió de disseny, no de sprint.

---

<a id="h"></a>
## H. FITXA TÈCNICA — TAULA DE MESURES DE TALLA BASE

### H.1 · Què emet avui el generador de taules

Constructor de dades: `frontend/src/utils/taulesQ8.js`. Pàgina i geometria:
`frontend/src/pages/TechSheetEditor.jsx`.

| Taula | Constructor | Inserció | Font | Columnes |
|---|---|---|---|---|
| **Q8a Fitting** | `filesFitting` — `taulesQ8.js:89` | `TechSheetEditor.jsx:5329` | `PieceFittingLine` de l'**última sessió TANCADA**, via `piece-fittings/<id>/` + `construeixTaulaPresaPerTalla` | Layer · POM · … · `base` · Actual · Dif (`:5349-5357`) |
| **Q8b Grading** | `filesGrading` — `taulesQ8.js:202` | `TechSheetEditor.jsx:5404` | **`GET /models/<id>/taula-mesures/`** (`models_app/views.py:1982`) | Layer · POM · **Rule · Δ · Break · B.Size** + una per talla (`:5417`) |
| **Q8c Size set** | `filesSizeSet` — `taulesQ8.js:118` | `TechSheetEditor.jsx:5478` | grid de la sessió tancada | totes les talles |
| **Q8c-consolidat** | `filesSizeSetConsolidat` — `taulesQ8.js:159` | `TechSheetEditor.jsx:5496` | `taula-mesures` (sense sessió) | idem, amb Actual/Dif buits |
| **Q8d Notes** | `filesNotes` — `taulesQ8.js:176` | `TechSheetEditor.jsx:5558` | grid de la sessió tancada | notes de la talla base |
| Personalitzada / BOM / capçalera | — | `:5616`, `insertHeader` | — | — |

Despatx del panell: `TechSheetEditor.jsx:5641-5653` (`onPickTableVariant`).
Repartiment per peça: `grupsQ8` (`TechSheetEditor.jsx:5263`) → `grupsDelFull` →
`agrupaPerGarment` (`frontend/src/utils/garmentFitxa.js`).

### H.2 · 🔑 La taula que falta **JA VA EXISTIR i es va retirar per RUTA**

`insertTableBaseMeasures` va viure a `TechSheetEditor.jsx` amb `kind: 'base_measures'` i es va
retirar el **18/08/2026** al commit **`d15e198b`** («Q8-ter/T5 · fora del panell les quatre taules
substituïdes, per RUTA»), amb acta a `docs/diagnosis/DIAGNOSI_Q8TER_RETIRADA_PANELL.md`.
Va néixer al commit `38a0761e` («feat(fitxa): taula "Mesures talla base" — la base sola, sense
graduació»).

El que feia (recuperable de `git show 38a0761e:frontend/src/pages/TechSheetEditor.jsx`, línies
4608-4645):

```js
const r = await fetch(`${API}/api/v1/models/${model.id}/base-measurements/`, {headers: authHeaders})
const columns = [
  { key: 'ref',    label: t('tech_sheet.tbl_col_nomenclatura'), width: 22 },
  { key: 'pom',    label: t('tech_sheet.tbl_col_pom'),          width: 46 },
  { key: 'base',   label: t('tech_sheet.tbl_col_base_cm'),      width: 18 },
  { key: 'tol',    label: t('tech_sheet.tbl_col_tol'),          width: 16 },
  { key: 'coment', label: t('tech_sheet.tbl_col_comments'),     width: 60 },
]
const rows = bms.map(bm => [
  nomenclaturaDePom(bm),
  { text: bm.nom_en || bm.nom_client || bm.pom_code_global || '', sub: bm.nom_ca || '' },
  fmtMeasure(bm.base_value_cm, unit) ?? '',
  fmtTolerancia(bm.tol_minus, bm.tol_plus, unit),
  '',
])
addObject(fitTableObj({ ..., kind: 'base_measures', columns, rows,
  snapshot: { model_id: model.id, talla_base: model?.base_size_label || null, snapshot_at: ... } }))
```

**El renderitzador segueix viu i no mira mai el `kind`** (`DIAGNOSI_Q8TER_RETIRADA_PANELL.md`
§«LA CONDICIÓ ES COMPLEIX»): les fitxes ja desades amb una `base_measures` es continuen pintant.
El que va caure és **la manera de crear-ne de noves**.

Van caure amb ella (i caldria **recuperar o reescriure**): `runTableVariant`, el modal
sub-selector de size fitting, `nomDeTaula` (+ l'import de `nomenclaturaDePom`), `seccionsDeFiles`,
`partirEnTaules`, `inserirTaules`, `escalonat`, `partirTaules`, l'estat `tablePicker`,
`partirPerSeccio`, `t1aOk`, `t1aMotiu`, `sfAmbGrading`, `nRepas`, `nSpecs`, i **18 claus i18n × 3
idiomes**. `baseMeasuresOk` **es va quedar** (el fan servir les portes de Q8b i Q8c).

### H.3 · D'on es llegiria «l'últim fit vàlid»

**Ja hi és, i no cal cap font nova.** La llei *«l'última mesura escrita és la veritat — temporal,
no d'origen»* està **materialitzada a `BaseMeasurement.base_value_cm`**:

```python
# backend/fhort/fitting/services.py:669-698  · consolidate_base_from_fitting
# «la darrera mesura VÀLIDA escrita». Una línia REJECTED es desa i es veu, però NO sembra
linies = (PieceFittingLine.objects.filter(piece_fitting=pf)
          .exclude(decisio=PieceFittingLine.DECISIO_REJECTED)...)
```

Dos moments l'escriuen:
- en **tancar** el fitting — `close_piece_fitting` (`fitting/services.py:740`);
- en **propagar** — `generate_grading_view` la consolida **abans** que el motor llegeixi la base
  (`models_app/views.py:3090-3095`), amb `origen='FITTED'`.

→ `GET /api/v1/models/<id>/base-measurements/` (`models_app/urls.py:123`) **ja serveix l'últim
fit vàlid**. Cap endpoint nou. (I `BaseMeasurement.origen` diu si el valor ve d'un fitting.)

**Alternativa si es vol la base d'una talla que no és la base del model:** llavors sí que cal
`taula-mesures` (`models_app/views.py:1982`), que porta `base_value_cm` **i** `graded` per talla.

### H.4 · On s'inseriria al panell agrupat per peça

| Node | Àncora | Què cal |
|---|---|---|
| Despatx de variants | `TechSheetEditor.jsx:5641-5653` | una branca `if (variant === 'q8_base') { insertTaulaBase(garment); return }` |
| Constructor de files | **nou**, a `frontend/src/utils/taulesQ8.js` al costat de `filesGrading:202` | ha d'emetre `garment` per fila (com fa `filesGrading`) perquè `grupsDelFull` la sàpiga repartir |
| Font | `taula-mesures` (ja la carrega `taulaMesuresDelModel`, `TechSheetEditor.jsx:5390-5398`) **o** `base-measurements/` (la del builder retirat) | **`taula-mesures` és la bona**: `base-measurements/` **no** serveix `garment` i faria caure totes les files a la mare — el mateix motiu que `taulesQ8.js:16-18` dona per no fer servir `graded-table/` |
| Agrupació per peça | `grupsQ8` — `TechSheetEditor.jsx:5263` | reutilitzable tal qual |
| Amplada de la columna POM | `ampladaPomQ8` — `TechSheetEditor.jsx:5273` | reutilitzable |
| Partició per ample | `trossosDeTalles` / `ampleUtilQ8` — `TechSheetEditor.jsx:5279`, `:5417` | **no cal**: la taula de base té columnes fixes i **no creix amb el run** |
| Porta | `baseMeasuresOk` | **ja existeix i ja es fa servir** per Q8b i Q8c |
| i18n | `tech_sheet.tbl_col_nomenclatura`, `tbl_col_pom`, `tbl_col_base_cm`, `tbl_col_tol`, `tbl_col_comments`, i el rètol de la variant | **esborrades a `d15e198b`** (18 claus × 3 idiomes) → cal tornar-les a posar |
| Banc | `backend/fhort/fitting/test_q8_banc_taules_fitxa.py` + `ops/qa/q8_taules_fitxa.mjs` | el bolcat de payloads és el contracte entre backend i front; una taula nova hi ha d'entrar |

**Cost estimat: MITJÀ-BAIX.** El gruix ja està escrit (constructor recuperable de `38a0761e`,
agrupació per peça reutilitzable, porta existent, renderitzador intacte). El que és **nou de debò**
és portar-lo a l'eix de la **prenda**, que és el que la versió retirada no tenia — i que és
exactament el motiu pel qual es va retirar.

---

<a id="i"></a>
## I. CENS LOSAN A PROD (schema `fhort`) — NOMÉS CENS, CAP ESBORRAT

> **NO S'HA ESBORRAT RES.** Tot el que segueix és lectura. Cap `DELETE`, cap `UPDATE`.

### I.0 · Marc

```
Total models a fhort: 84   ·   INTERN 83   ·   EXTERN 1
per client:  BRW 80  ·  LOS 3  ·  TRV 1
Tenants (public.tenants_client): public/SYS (estudi) · fhort/FTT (estudi) · los/LOS (marca)
```

### I.1 · Els 3 models LOS i totes les seves FK

| id | codi_intern | nom | **origen** | client | `federacio_estat` | joc | sistema |
|---|---|---|---|---|---|---|---|
| **178** | `LOS-SS26-0001` | Margarita | **INTERN** | LOS | NULL | #96 | #44 `GIRL_LOS_01` |
| **190** | `LOS-SS27-0001` | BERG Polo | **INTERN** | LOS | NULL | #101 | #45 `MAN_LOS_01` |
| **1183** | `LOS-SS27-0834` | DALIA | **EXTERN** | LOS | NULL | — | #70 `NEWBORN_LOS_01` |

→ **Dos INTERN i un EXTERN.** El 1183 és el bessó de `los`.834 (l'únic model que queda al schema
`los`), conservat com a testimoni de federació a la purga del 04/08.

**FK entrants a `models_app.Model`, mesurades una a una** (recompte per model; `—` = 0):

| Taula · camp | `on_delete` | Total | 178 | 190 | 1183 |
|---|---|---|---|---|---|
| `models_app.ModelFitxer.model` | CASCADE | **21** | 2 | 5 | 14 |
| `models_app.ImportSession.model` | SET_NULL | **11** | 3 | 3 | 5 |
| `models_app.BaseMeasurement.model` | CASCADE | **73** | 21 | 17 | 35 |
| `models_app.MeasurementChangeLog.model` | CASCADE | **75** | 23 | 17 | 35 |
| `models_app.ModelGradingOverride.model` | CASCADE | **9** | 9 | — | — |
| `models_app.ModelGradingRule.model` | CASCADE | **73** | 21 | 17 | 35 |
| `models_app.ConsumptionRecord.model` | CASCADE | **3** | 1 | 1 | 1 |
| **`models_app.SizeCheck.model`** | **PROTECT** | **3** | 1 | 1 | 1 |
| `models_app.Watchpoint.model` | CASCADE | **3** | 1 | 1 | 1 |
| `models_app.AIUsage.model` | SET_NULL | **7** | — | — | 7 |
| `fitting.SizeFitting.model` | CASCADE | **5** | 1 | 2 | 2 |
| `fitting.FittingSession.model` | CASCADE | **1** | 1 | — | — |
| **`fitting.PieceFitting.model`** | **PROTECT** | **1** | 1 | — | — |
| `tasks.ModelTask.model` | CASCADE | **9** | 4 | 3 | 2 |
| `tasks.GateEvent.model` | CASCADE | **4** | 4 | — | — |
| `models_app.BulkCollectionRow`, `models_app.ModelGarment`, `fitting.POMAlert`, `tasks.Ronda`, `tasks.Production`, `planning.TechnicianQueueOrder`, `commerce.QuoteLineModelIntent`, **`commerce.WorkOrder`** (PROTECT), `commerce.DeliveryNoteLine`, `patterns.PatternFile`, `patterns.SewRelation`, `patterns.SewProposalRejection`, `patterns.DartProposalRejection`, `patterns.SewToleranceAcceptance` | vari | **0** | — | — | — |

**⚠️ TRES `PROTECT` en total, DOS amb files:** `SizeCheck` (3 files, una per model) i
`PieceFitting` (1 fila, del 178). `commerce.WorkOrder` és PROTECT però té 0 files.

**Segon nivell:**

```
SizeFitting / GradingVersion / GradedSpec
  SF#69   LOS-SS26-0001  IMP-178-1            SizeSet  TallesGenerades  GV=3  specs=559  aprovades=2 ⚠️
  SF#71   LOS-SS27-0001  IMP-190-1            SizeSet  TallesGenerades  GV=2  specs=306  aprovades=0
  SF#72   LOS-SS27-0001  IMP-190-2            SizeSet  Tancat           GV=0  specs=0
  SF#1050 LOS-SS27-0834  LOS-SS27-0834-SF1    Proto    TallesGenerades  GV=1  specs=175  aprovades=0
  SF#1057 LOS-SS27-0834  IMP-1183-2           SizeSet  Tancat           GV=0  specs=0

PieceFitting
  PF#13   LOS-SS26-0001  sessió 94  gv=35  →  189 PieceFittingLine

ModelTask + timers/transicions
  MT#233 178 pom            Done    · TimerEntrada=1 · TaskTransition=2
  MT#234 178 size_check     Done    · TimerEntrada=1 · TaskTransition=2
  MT#235 178 tech_sheet     Done    · TimerEntrada=5 · TaskTransition=8
  MT#236 178 pattern_review Done    · TimerEntrada=2 · TaskTransition=2
  MT#258 190 pom            Done    · TimerEntrada=2 · TaskTransition=4
  MT#259 190 size_check     Paused  · TimerEntrada=1 · TaskTransition=2
  MT#298 190 audit          Pending · (cap)
  MT#302 1183 pom           Done    · TimerEntrada=5 · TaskTransition=10
  MT#303 1183 grading       Paused  · TimerEntrada=4 · TaskTransition=8
   → TOTAL: 21 TimerEntrada · 38 TaskTransition
```

**⚠️ SF#69 té DUES GradingVersion SEGELLADES (`aprovada=True`).** Esborrar-les és destruir un
segell de producció. Cal decisió explícita.

**Fitxers (`ModelFitxer`, 21):**
```
178:  DOCUMENT LOS-SS26-0001_DOCUMENT_001.pdf · TECHSHEET LOS-SS26-0001_fitxa.ftt
190:  DOCUMENT ×2 · TECHSHEET LOS-SS27-0001_fitxa.ftt + _nozd4fW.ftt + _oGfuCEn.ftt
1183: ALTRES Dalia_01.png, Dalia_02.png · DOCUMENT LOS-SS27-0834_DOCUMENT_001.xlsx
      · TECHSHEET LOS-SS27-0834_fitxa.ftt + _ocb0lh5 + _aXNIBTx + _xz3cA44 + _pyT7iBr
        + _5GosE4j + _3E4TnQz + _ZIwADfp  (8 .ftt)
      · EXPORT LOS-SS27-0834_fitxa_v19.pdf, _v22.pdf, _v27.pdf
```
→ **12 fitxers `.ftt`** i 3 PDF d'export. El `FileField` **no esborra el binari de disc** en
esborrar la fila: `media/fhort/model_fitxers/2026/{06,07}/` queda amb els fitxers orfes.

**Watchpoints (3, tots `open`):** WP#87 (178), WP#99 (190), WP#112 (1183) — tots
*«Migració al món nou (S43): cal reconstruir la relació del model (Garme…»*.

**Meritació — DUES bandes, i la de `public` NO cau amb el model:**

| Banda | Taula | Files LOS | `on_delete` |
|---|---|---|---|
| Tenant `fhort` | `models_app.ConsumptionRecord` | 3 (`0f96148e…` 2026-07 / 1183 · `f5986539…` 2026-07 / 190 · `02033683…` 2026-06 / 178) | CASCADE amb el model |
| **`public`** | **`backoffice.ModelConsumptionEvent`** | **6 amb `actor_schema='fhort'`** | **cap FK al model — NO cau** |

Events LOS a `public` (53 en total al sistema): ids 31, 28, 25, 24, 16, 12, 8 amb
`actor_schema='fhort'` i ids 30, 29 amb `actor_schema='los'`. **Tres dels de `fhort`**
(`4bd35230…`, `8e9e2936…`, `dd322744…`, `a29a1076…`) **ja no tenen `ConsumptionRecord`**: són
rastre de la purga del 04/08. **L'esdeveniment és la unitat facturable**
(`backoffice/recurring_service.py:87` en fa el `.count()`) → esborrar els models **no** desfà cap
facturació, i **no s'ha de tocar** sense decisió comercial explícita.

### I.2 · Queden models EXTERN de LOSAN a `fhort`? — **NO. Només 1, i és el testimoni.**

```
Model.objects.filter(origen='EXTERN')  →  [(1183, 'LOS-SS27-0834', 'LOS')]
Model.objects.filter(id__in=[1178,1180,1181,1182])  →  []
Model.objects.filter(codi_intern__startswith='LOS').count()  →  3
schema `los`:  models=1 (id 834, LOS-SS27-0834, INTERN, federacio_estat poblat)
```

**La pantalla en mostra 3 i el recompte real és 3.** Els 960 models del 23/07 vivien al schema
**`los`**, no a `fhort`, i es van esborrar el 04/08
(`/root/diagnosi_losan/PURGA_MODELS_LOS_FASE3_20260804.md`, backup a
`/root/backups/los_models_pre_purga_20260804.dump`). Els quatre bessons `EXTERN` que aquell report
deia que quedaven vius a `fhort` (1178, 1180, 1181, 1182) **tampoc hi són** — algú els va retirar
després del 04/08 i **no ho he trobat documentat a `/root/diagnosi_losan/`**. 🚩 Ho reporto.

### I.3 · Jocs de regles LOS a `fhort` — **24 jocs · 525 regles**

| # | Nom | actiu | regles | client | sistema | models que hi apunten |
|---|---|---|---|---|---|---|
| 95 | LOS EU YEARS KID WOVEN | ✔ | **0** | LOS | GIRL_LOS_01 | 0 |
| **96** | Importació fitxa · LOS-SS26-0001 | ✘ | 21 | LOS | GIRL_LOS_01 | **1 (178)** |
| 98 | Importació fitxa · LOS-SS27-0001 | ✘ | 17 | — | ALPHA_EU_M | 0 |
| **101** | Importació fitxa · LOS-SS27-0001 · IMP-190-2 | ✔ | 17 | LOS | MAN_LOS_01 | **1 (190)** |
| 125 | LOS Baby Knit — Tops | ✔ | 17 | — | BABY_LOS_01 | 0 |
| 126 | LOS Kids Boy Knit — Tops | ✔ | 17 | — | BOY_LOS_01 | 0 |
| 127 | LOS Kids Boy Woven — Bottoms | ✔ | 25 | — | BOY_LOS_01 | 0 |
| 128 | LOS Kids Girl — Dresses | ✔ | 19 | — | GIRL_LOS_01 | 0 |
| 129 | LOS Kids Girl Knit — Tops | ✔ | 17 | — | GIRL_LOS_01 | 0 |
| 130 | LOS Man Knit — Tops | ✔ | 35 | — | MAN_LOS_01 | 0 |
| 131 | LOS Man Woven — Bottoms | ✔ | 23 | — | MAN_NUM_LOS_01 | 0 |
| 132 | LOS New Born Knit — Bottoms | ✔ | 31 | — | NEWBORN_LOS_01 | 0 |
| 133 | LOS New Born Knit — Onepieces | ✔ | 49 | — | NEWBORN_LOS_01 | 0 |
| 134 | LOS New Born Knit — Tops | ✔ | 46 | — | NEWBORN_LOS_01 | 0 |
| 135 | LOS Teen Boy Knit — Tops | ✔ | 19 | — | YOUTH_BOY_LOS_01 | 0 |
| 136 | LOS Teen Boy Woven — Bottoms | ✔ | 19 | — | YOUTH_BOY_LOS_01 | 0 |
| 137 | LOS Teen Boy Woven — Shirts | ✔ | 23 | — | YOUTH_BOY_LOS_01 | 0 |
| 138 | LOS Teen Girl — Bottoms | ✔ | 12 | — | YOUTH_GIRL_LOS_01 | 0 |
| 139 | LOS Teen Girl Knit — Tops | ✔ | 24 | — | YOUTH_GIRL_LOS_01 | 0 |
| 140 | LOS Teen Girl Stretch — Swimwear | ✔ | 11 | — | YOUTH_GIRL_LOS_01 | 0 |
| 141 | LOS Woman Knit — Tops | ✔ | 18 | — | WOMAN_LOS_01 | 0 |
| 142 | LOS Woman Woven — Bottoms | ✔ | 24 | — | WOMAN_NUM_LOS_01 | 0 |
| 143 | LOSAN IBERIA SA · Newborn · LOS Baby 3-36M | ✔ | 12 | — | BABY_LOS_01 | 0 |
| 145 | LOS Woman Woven — Bottoms (Alpha) | ✔ | 29 | — | WOMAN_LOS_01 | 0 |

**`Model.grading_rule_set` és `SET_NULL`** (verificat per ORM) → esborrar un joc **no** esborra
models, els deixa sense punter. Però:

**🔴 `SizingProfile.grading_rule_set` és `PROTECT`** (verificat) — **25 `SizingProfile` bloquegen
l'esborrat**:

| Joc | SizingProfiles que hi apunten |
|---|---|
| **#95** | SP#507, 508, 509, 510, 511, 512, 513 (**7**) |
| #125 | SP#539 |
| #126 | SP#542 |
| #127 | SP#543 |
| #128 | SP#540 |
| #129 | SP#541 |
| #131 | SP#537 |
| #134 | SP#538, 554, 555 (**3**) |
| #135 | SP#548 |
| #136 | SP#549 |
| #137 | SP#547 |
| #138 | SP#546 |
| #139 | SP#544 |
| #140 | SP#545 |
| #141 | SP#535 |
| #142 | SP#536 |
| #145 | SP#556 |

→ **17 dels 24 jocs estan PROTEGITS.** Els jocs #96, #98, #101, #130, #132, #133, #143 **no** en
tenen cap. El `destroy` del ViewSet ja ho sap i retorna 409 amb els recomptes
(`pom/views.py:269-302`), amb `?force=1` per a la cascada controlada.

**Toc de la purga:** el joc #146 (`Textiles y Confeccions Brownie SL · Tops · Alph…`) té **9
models BRW** i el #102 en té 5 — **no són LOS i no s'han de tocar**.

### I.4 · SizeSystems LOS a `fhort` — **11**

| id | codi | nom | talles | **models** | perfils | jocs |
|---|---|---|---|---|---|---|
| **44** | GIRL_LOS_01 | Nena AGE_YEARS — LOSAN IBERIA | 9 | **1 (178)** | 9 | 4 |
| **45** | MAN_LOS_01 | ALPHA EU LOSAN KNIT MAN REGULAR | 9 | **1 (190)** | 0 | 2 |
| 66 | BABY_LOS_01 | LOS Baby 3-36M | 6 | 0 | 1 | 2 |
| 67 | BOY_LOS_01 | LOS Kids Boy 2-12Y | 9 | 0 | 2 | 2 |
| 68 | GIRL_LOS_03 | Nena AGE_YEARS — LOSAN IBERIA | 9 | 0 | 0 | 0 |
| 69 | MAN_NUM_LOS_01 | LOS Man Numeric 38-58 | 11 | 0 | 1 | 1 |
| **70** | NEWBORN_LOS_01 | LOS New Born 0-24M | 7 | **1 (1183)** | 3 | 3 |
| 71 | WOMAN_LOS_01 | LOS Woman Alpha XS-3XL | 7 | 0 | 2 | 2 |
| 72 | WOMAN_NUM_LOS_01 | LOS Woman Numeric 36-52 | 9 | 0 | 1 | 1 |
| 73 | YOUTH_BOY_LOS_01 | LOS Teen Boy 8-16Y | 5 | 0 | 3 | 3 |
| 74 | YOUTH_GIRL_LOS_01 | LOS Teen Girl 8-16Y | 5 | 0 | 3 | 3 |

**Qui els apunta:** 3 models · **25 SizingProfile** · **23 GradingRuleSet** · **86 `SizeDefinition`**.
`Model.size_system` és **SET_NULL** (verificat). `SizeSystemViewSet.destroy` refusa amb 400 si
queden talles (`pom/views.py:92-99`).

**#68 `GIRL_LOS_03` és un òrfena total:** 0 models, 0 perfils, 0 jocs. Duplicat de nom del #44.

### I.5 · Catàleg materialitzat del bootstrap LOSAN

**`POMMaster` a `fhort`: 645.** El camp `origen_import` és el marcador i **sí, són
identificables**:

| `origen_import` | n | Comentari |
|---|---|---|
| `''` (buit) | **309** | sense marca — no atribuïbles |
| **`diccionari:LOS:2026-07-17`** | **114** | ← bootstrap LOSAN |
| `diccionari:BRW:2026-07-14` | 53 | Brownie — **no tocar** |
| **`diccionari:LOS:2026-07-18`** | **19** | ← bootstrap LOSAN |
| **`LOS diccionari 4B-bis`** | **16** | ← bootstrap LOSAN |
| `màster v3 P1/P2b 2026-07-24` | 13 | catàleg canònic v3 |
| `SS26 TROUSERS TWILL (14-26-SS-0002)` | 13 | import de fitxa |
| UUIDs de sessió d'import + `REPARACIO_PR_357_…` + `CARREGA_SUZIE_1196_…` | resta | |

→ **149 POMs porten marca LOS explícita.** (No són «1035»: aquella xifra és del bootstrap sencer
del 23/07, la major part del qual mai va viure a `fhort` — v. §Contradiccions §5.)

**Anàlisi d'ús real (el criteri que importa per esborrar):**

```
POMs citats per jocs LOS ................................. 148
POMs citats per jocs NO-LOS .............................. 281
POMs NOMÉS-LOS (ni altre joc, ni cap BaseMeasurement,
                ni cap ModelGradingRule de cap model) ....  56   ← candidats nets
POMs orfes totals (cap joc, cap model) ................... 153
```

**`POMGlobal` (a `public`, compartit): 290 — CAP no s'ha de tocar** (és el catàleg canònic de la
casa, no de LOSAN).

**⚠️ `GradedSpec.pom` i `ModelGradingRule.pom` són `PROTECT`** (`fitting/models.py:212`,
`models_app/models.py:1186`) → cap POM citat per un spec o una regla és esborrable fins que
l'spec/regla caigui.

### I.6 · TenantLink LOS ↔ FTT — **VIU**

```python
# public.tenants_tenantlink
{'id': 1, 'brand_codi_tenant': 'LOS', 'studio_codi_tenant': 'FTT',
 'token': 'I95I7TrPEXZrD1wSpQ1ar51attltjxDS2qiN2nfIZlg',
 'estat': 'ACTIU', 'created_at': 2026-07-23 09:16:58 UTC,
 'aturat_at': None, 'nota': ''}
```

**Estat: `ACTIU`, un de sol.** Llei del pont (`tenants/models.py:321-340`): *«el token governa el
PONT, mai la capacitat de treballar; aturar-lo o revocar-lo NO destrueix cap dada»*. Els 3 estats
legítims són **sense vincle / viu (`ACTIU`) / aturat (`ATURAT`)**, més `REVOCAT`.

**Conseqüència per a la finestra:** el 1183 és `origen='EXTERN'` i el seu bessó `los`.834 té
`federacio_estat` poblat. Esborrar el 1183 a `fhort` **trenca el costat estudi d'una federació
viva** — el mateix dany que la fase 2 del 04/08 va fer sense voler amb quatre parelles. **Cal
decidir el pont ABANS del model**, no després.

### I.7 · Ordre d'esborrat proposat, respectant PROTECT

> **DRY-RUN. Cap ordre s'ha executat.** Tot per ORM (llei). Recomptes exactes per a la guarda.

**Guarda d'entrada (ha de donar EXACTAMENT això abans de començar):**

```
Model.objects.filter(codi_tenant='LOS').count()                     == 3
Model.objects.filter(origen='EXTERN').count()                       == 1
GradingRuleSet.objects.filter(id__in=LOS_RS).count()                == 24
GradingRule.objects.filter(rule_set_id__in=LOS_RS).count()          == 525
SizingProfile.objects.filter(grading_rule_set_id__in=LOS_RS).count()== 25
SizeSystem.objects.filter(codi__contains='LOS').count()             == 11
SizeDefinition.objects.filter(size_system__in=LOS_SS).count()       == 86
POMMaster.objects.count()                                           == 645
Model.objects.count()                                               == 84   (→ 81 al final)
```

**FASE 0 — decisions humanes prèvies (bloquejants, NO tècniques):**
1. **TenantLink #1 (ACTIU)**: es manté, s'atura o es revoca? Afecta el 1183.
2. **Les 2 GradingVersion SEGELLADES de SF#69**: s'accepta destruir un segell de producció?
3. **6 `backoffice.ModelConsumptionEvent` a `public`**: es conserven (recomanat: són la unitat
   facturable i no tenen FK al model) o es purguen?
4. **Fitxers de disc** (12 `.ftt`, 3 PDF, 2 PNG, 1 XLSX, 3 PDF/DOC): s'esborren de
   `media/fhort/model_fitxers/2026/{06,07}/` o es deixen orfes?
5. **Backup previ obligatori**, com al 04/08.

**FASE 1 — desbloquejar els dos PROTECT del model** (sense això, `Model.delete()` peta):

| Pas | Acció | Recompte esperat |
|---|---|---|
| 1.1 | `PieceFittingLine` de PF#13 | **189** |
| 1.2 | `PieceFitting` PF#13 (PROTECT) | **1** |
| 1.3 | `FittingSession` #94 | **1** |
| 1.4 | `SizeCheck` #1, #2, #5 (PROTECT) — i abans, les seves FK entrants | **3** |

**FASE 2 — el cicle de mesura i graduació** (CASCADE les faria soles, però es fan explícites per
tenir recompte):

| Pas | Acció | Recompte |
|---|---|---|
| 2.1 | `GradedSpec` dels 3 models | **1040** (559+306+175) |
| 2.2 | `GradingVersion` | **6** (3+2+0+1+0) ⚠️ 2 aprovades |
| 2.3 | `SizeFitting` | **5** |
| 2.4 | `ModelGradingOverride` | **9** |
| 2.5 | `ModelGradingRule` | **73** |
| 2.6 | `MeasurementChangeLog` | **75** |
| 2.7 | `BaseMeasurement` | **73** |

**FASE 3 — tasques, temps i rastre:**

| Pas | Acció | Recompte |
|---|---|---|
| 3.1 | `TimerEntrada` de les 9 ModelTask | **21** |
| 3.2 | `TaskTransition` | **38** |
| 3.3 | `ModelTask` | **9** |
| 3.4 | `GateEvent` | **4** |
| 3.5 | `Watchpoint` | **3** |
| 3.6 | `AIUsage` (SET_NULL — o esborrar) | **7** |
| 3.7 | `ImportSession` (SET_NULL — o esborrar) | **11** |
| 3.8 | `ConsumptionRecord` | **3** |
| 3.9 | `ModelFitxer` (+ binaris de disc si s'ha decidit) | **21** |

**FASE 4 — els models:**

| Pas | Acció | Recompte |
|---|---|---|
| 4.1 | `Model` 178, 190, 1183 | **3** → `Model.objects.count() == 81` |

**FASE 5 — el rastre LOS del catàleg** (només després que la fase 4 hagi commitat):

| Pas | Acció | Recompte | Nota |
|---|---|---|---|
| 5.1 | `SizingProfile` que apunten a jocs LOS | **25** | **obligatori abans de 5.2** (PROTECT) |
| 5.2 | `GradingRule` dels 24 jocs | **525** | cauen per CASCADE amb 5.3, però es compten |
| 5.3 | `GradingRuleSet` (els 24) | **24** | només quan 5.1 ha commitat |
| 5.4 | `SizeDefinition` dels 11 sistemes | **86** | `SizeSystem.destroy` ho exigeix (`pom/views.py:94-98`) |
| 5.5 | `SizeSystem` LOS | **11** | verificar abans que cap model hi apunti |
| 5.6 | `POMMaster` **només-LOS** | **56** | 🔴 **NO els 149 marcats**: 93 dels marcats són citats per jocs no-LOS o per models de BRW/TRV. El criteri d'esborrat és **l'ús**, no `origen_import`. |
| 5.7 | `CustomerPOMAlias` del customer LOS (id 6, `LOSAN IBERIA SA`) | **212** | 🔴 revisar un a un: un àlies pot apuntar a un POM que BRW/TRV també fan servir |
| 5.8 | `tasks.Customer` LOS (id **6**) | 1 | **decisió**: esborrar-lo trenca l'històric de facturació |

**FASE 6 — verificació dins la mateixa transacció, abans del COMMIT:**

```
Model.objects.filter(codi_tenant='LOS').count()                == 0
Model.objects.count()                                          == 81
GradingRuleSet.objects.filter(id__in=LOS_RS).count()           == 0
SizeSystem.objects.filter(codi__contains='LOS').count()        == 0
SizingProfile.objects.filter(grading_rule_set__isnull=True)    == (valor de partida, sense créixer)
POMMaster.objects.count()                                      == 589
POMGlobal.objects.count()                                      == 290   (INTACTE)
Model.objects.filter(customer__codi='BRW').count()             == 80    (INTACTE)
Model.objects.filter(customer__codi='TRV').count()             == 1     (INTACTE)
GradingRuleSet.objects.count()                                 == 28    (52 − 24)
```

**Total de files a esborrar (fases 1-5, sense 5.7/5.8): 2 322.**
(F1 194 + F2 1 281 + F3 117 + F4 3 + F5 727; amb els 212 `CustomerPOMAlias` de 5.7 serien 2 534.)

**🔴 El que aquesta finestra NO ha de tocar, i que cal escriure a l'ordre:**
`POMGlobal` (290, a `public`) · els 80 models BRW · el model TRV 1215 · els jocs #146 (9 models),
#102 (5), #79 (3), #81 (5), #75 (2), #152 (2) · els `backoffice.ModelConsumptionEvent`
(sense decisió comercial) · el schema `los` sencer (277 POMMaster, 20 jocs, 1 model).

---

<a id="contradiccions"></a>
## CONTRADICCIONS AMB EL BRIEF

**1. «Model 837 VESTIT (TRV-SS27-0001)» — el 837 no és cap id.**
`Model.objects.filter(id=837)` → **cap fila**. `TRV-SS27-0001` és **`Model.id = 1215`**; «837
VESTIT» és el valor de `Model.nom_prenda`. Sense conseqüències per a la feina (he treballat sobre
el model correcte), però el número no serveix per adreçar-lo.

**2. Tram A — el símptoma no es reprodueix a les dades de PROD.** ⚠️ **ATURADA DE MÈTODE.**
V. §A.0: 105 cel·les contrastades, **0 discrepàncies**; les 21 edicions manuals del 20/08 estan
totes recollides a la versió vigent. Les quatre hipòtesis del brief queden **refutades** en
l'estat d'avui (§A.3). El que **sí** he trobat són sis defectes reals i verificables al mateix
camí (§A.5), i un d'ells —`increment` mai actualitzat, `models_app/views.py:5202-5220` +
`pom/services.py:1197-1198`— produeix **exactament** el símptoma descrit el dia que algú buidi el
camp «Δ base». **No l'he resolt.** Cal que l'Agus digui hora i POM del cas observat.

**3. Tram F — «paritat QA obligatòria: golden POP 105/105 + path 163».
El banc no existeix a PROD.**
- Models **268/269** («Blusa POP» / «POP», `docs/diagnosis/DIAGNOSI_CONTENIDOR_GRADING_CLIENT.md:288-289`):
  **no existeixen** a `fhort`.
- Models **1320/1322** (el golden VIU, `scripts_tmp/golden_set2_T0_2026-08-10.json`, 280 cel·les):
  **no existeixen** a `fhort`.
- `Model.objects.filter(codi_intern__startswith='BANC-')` → **0**: el banc de paritat de 27 fitxes
  Brownie (`manage.py sembra_banc_paritat`) **mai s'ha sembrat a PROD**.
- **Model 163 `BRW-FW26-0001` sí existeix** (i 174, 182, 186 també).
- L'acta de `sembra_banc_paritat.py:4-8` diu que el corpus vell (162·163·174·182·186·268·269) el
  va endur la sembra v4 del 09/08 i que l'empremta `165d6701…` *«parla d'un banc mort»*.
→ **La xifra «105/105» no correspon a cap artefacte que hagi pogut localitzar.** El 105 que sí
existeix són les 105 cel·les del model 1215. Qualsevol toc del motor (trams E i F) **queda
bloquejat** fins que el banc es reconstrueixi a staging.

**4. Tram I.2 — «n'hi va haver 960 el 23/07; la pantalla només en mostra 3».
La pantalla diu la veritat.** Els 960 vivien al schema **`los`** (esborrats el 04/08,
`PURGA_MODELS_LOS_FASE3_20260804.md`), no a `fhort`. A `fhort` només hi ha hagut els 3 actuals
més els 4 bessons EXTERN 1178/1180/1181/1182, **que tampoc hi són avui** i el retir dels quals
**no consta a cap document de `/root/diagnosi_losan/`**. 🚩 Reportat.

**5. Tram I.5 — «les ~1035 files del 23/07» no es corresponen amb el corpus de `fhort`.**
`POMMaster` a `fhort`: **645** en total, dels quals **149** porten marca LOS explícita
(`diccionari:LOS:2026-07-17` 114 · `diccionari:LOS:2026-07-18` 19 · `LOS diccionari 4B-bis` 16) i
**56** són esborrables sense tocar res del catàleg propi. El schema `los` en té 277. La xifra 1035
no casa amb cap dels dos.

**6. Tram G.4 — «taula de Mesures: color més suau».** La columna base de la Taula de Mesures ja
és `var(--sel)` (`#f7f5f2`), el to més clar del sistema per sota de blanc; **no hi ha cap token
més suau**. I el «centrat» que demana el brief **ja hi és** a la columna de talla base
(`EditableTable.jsx:884`, `:1388`). Cal que l'Agus precisi si el que vol centrar són les columnes
de **valor** (avui `right`, `:1378`/`:1416`) i quin to concret vol — estrenar token és decisió de
disseny.

**7. Tram A.3(d) — el brief situa `materialize_model_grading_rules` «en algun pas previ a
propagar».** No hi és: els seus 5 cridadors (`models_app/views.py:981, 1054, 1204, 1807`;
`extraction_views.py:3571`) són **assignar/canviar joc**, **sembra del wizard** i **import**. El
que sí que fa el camí de propagar és un **llenç net d'overrides**
(`ModelGradingOverride.objects.filter(model=model).delete()`, `models_app/views.py:3084`) — que
esborra els **ajustos per cel·la**, no les regles.

---

*Diagnosi read-only. Cap escriptura a BD, cap fitxer del repo modificat, cap migració, cap restart.*
*Scripts de lectura efímers a `/tmp/claude-0/.../scratchpad/`, fora del repo.*
