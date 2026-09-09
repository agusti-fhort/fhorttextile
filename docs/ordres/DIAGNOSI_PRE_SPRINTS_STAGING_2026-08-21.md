# DIAGNOSI PRE-SPRINTS · RE-ANCORATGE I FORATS (fix A · J · H · E+F)

**Data:** 2026-08-21 · **Entorn:** staging `178.105.48.204`, `/var/www/ftt-staging`, branca `dev`
**HEAD:** `506716b1` (bloc 3+D verificat: `1e5449c7` → `506716b1`, 8 commits, cap push)
**Banc:** model **1383** (`TRV-SS27-0001`), tenant `fhort` — **no tocat**
**Mode:** READ-ONLY estricte. Cap escriptura a BD (`PGOPTIONS=-c default_transaction_read_only=on`)
ni a cap fitxer versionat. Els dos scripts d'aquesta sessió viuen a `docs/ordres/`, que és
**untracked**.

> **Àncores.** Totes les `file:line` d'aquest document són **sobre `dev` a `506716b1`**. On
> difereixen de `DIAGNOSI_BUGS_PROD_837_2026-08-21.md` es diu explícitament.

---

## ÍNDEX

- [§0 · El banc com a artefacte](#s0) — ✅ **OK=105 · DISCREPA=0 · joc intacte**
- [§1 · Re-ancoratge del fix A](#s1) — 🚨 **el fallback del llegat són DOS, no un**
- [§2 · Tram J — consulta vs treball](#s2) — 🔑 **el senyal ja existeix i es diu `batec_escriptura`**
- [§3 · H — taula de mesures base a la fitxa](#s3) — 🚨 **la diagnosi es va equivocar de font**
- [§4 · E+F contra la forma d'intervals](#s4) — ✅ **equivalència provada 105/105 · 🚨 l'off-by-one de la migració**
- [CONTRADICCIONS](#contra)

---

<a id="s0"></a>
## §0 · EL BANC COM A ARTEFACTE

**Fitxer:** `docs/ordres/banc_paritat_1383.py` (FORA del repo versionat; entrarà com a peça
pròpia al sprint del fix A).

```bash
cd /var/www/ftt-staging/backend
PGOPTIONS='-c default_transaction_read_only=on' \
  venv/bin/python ../docs/ordres/banc_paritat_1383.py [-v] [--model 1383] [--tenant fhort]
```

Recalcula **en memòria** les cel·les del 1383 amb el motor REAL —`escala_del_model`,
`_load_grading_rules_per_garment`, `_regla_de`, `_load_model_overrides`, `_poms_amb_override`,
`_load_base_measurements`, `_apply_rule`— i les contrasta amb els `GradedSpec` de la
`GradingVersion` vigent. **No crida `generate_graded_specs`**: n'és un espill del bucle
(`pom/services.py:229-311`). Codi de sortida 0 només si hi ha paritat perfecta **i** el hash del
joc és el de referència.

### Resultat de la correguda d'avui

```
BANC DE PARITAT · model pk=1383 `TRV-SS27-0001` · tenant `fhort`
  sistema ALPHA_EU_W · run XS·S·M·L·XL · base S
  size_run     ['XS', 'S', 'M', 'L', 'XL']
  run_sistema  ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL']   base_idx=2
  regles       142  ·  bases 21  ·  overrides 0
  SizeFitting #371 `TRV-SS27-0001-SF1` · GradingVersion #129 (v6) vigent

  OK=105  DISCREPA=0  ABSENT=0  SOBRER=0  |  specs a la taula=105  |  files base=21

  HASH JOC        096990db404b778a2140fffd8327c54294849b73d42ec67b3265247f9840989f
                  (142 regles · `BRW-CATALEG-v3` pk=219) — IDÈNTIC al de referència
  HASH RESIDENTS  5715f4a2a4663bead1c8b870936c75be3aa8923ebeee5b10ca747c57d403144e
                  (142 ModelGradingRule)

  VEREDICTE: ✅ PARITAT · joc intacte
```

**El hash del joc quadra amb el que va segellar la sembra** (`SEMBRA_837_STAGING §5`):
`096990db…989f`. El banc és viu i comparable.

**El hash de les residents és NOU** (no n'hi havia cap de declarat). Fórmula: per fila
`[codi_client, garment, logica, increment, increment_base, increment_break, talla_break_label,
talla_break_pos, valors_step, actiu, origen, derivat_de_rule_set_id]`, numèrics a 4 decimals,
ordenat i sha256. **Hi entra `garment`** (eix propi de les residents que el joc del catàleg no
té) i **no hi entra `updated_at`**: el gate mesura la LLEI, no quan es va desar. Anoteu-lo:
`5715f4a2a4663bead1c8b870936c75be3aa8923ebeee5b10ca747c57d403144e`.

### El contracte del gate

| Quan | Què ha de dir |
|---|---|
| **abans** de cada canvi de motor | `OK=105 DISCREPA=0` + els dos hashos intactes |
| **després** | idèntic, **o** una llista de discrepàncies **explicades una a una** |
| si el HASH JOC canvia | ⛔ **stop**: el joc sota el banc s'ha mogut; res del que hi havia abans és comparable |
| si el HASH RESIDENTS canvia sense que ningú hagi editat regles | ⛔ **stop**: algú ha escrit al banc |

⚠️ **El banc és un ESPILL, no una crida.** Si el bucle de `generate_graded_specs` canvia de
forma (no de valor), el banc s'ha de moure amb ell — i que ho canti és **exactament la seva
feina**, no un defecte.

🚩 **El banc NO cobreix STEP-sense-valors.** A staging hi ha **0** regles STEP amb `valors_step`
buit (v. §4·E): el fix E necessitarà **fixture propi**, el banc no el veurà.

---

<a id="s1"></a>
## §1 · RE-ANCORATGE DEL FIX A (sobre `dev` post-bloc 3+D)

### 1.1 · Què ha mogut el bloc 3+D · **cap fitxer del motor**

```
git diff --stat 13614d48..506716b1
```
Els **5 fitxers de backend del camí** (`pom/services.py`, `pom/grading_utils.py`,
`pom/grading_regime.py`, `models_app/views.py`, `models_app/services.py`) **no hi són**. Últim
commit que els va tocar:

| Fitxer | Últim commit | Data |
|---|---|---|
| `models_app/views.py` | `62d5f714` (Q8-ter/T4) | 18/08 |
| `pom/services.py` | `0c0b3314` (SET-2/PRED-3) | 12/08 |
| `pom/grading_utils.py` | `ab78b14f` | 07/08 |
| `pom/grading_regime.py` | `4808589e` | 22/07 |
| `models_app/services.py` | `49b1200f` (SET-2/T3) | 10/08 |
| **`GraduacioSuperficie.jsx`** | **`b0066c3c` (S45/G)** | **21/08** |
| **`ModelSheet.jsx`** | **`308b7506` (S45/B)** | **21/08** |

→ **El backend del fix A és byte a byte el que la diagnosi va llegir.** El que s'ha mogut és el
**front**, i només de línia.

### 1.2 · Àncores noves

| Node | Diagnosi | **dev `506716b1`** | Moviment |
|---|---|---|---|
| Botó «Propagar» | `ModelSheet.jsx:1324-1331` | **`ModelSheet.jsx:1333-1341`** | +9 (S45/B) |
| `onPropagarClick` | `:937-951` | **`:944-957`** | +7 (S45/B) |
| `execPropagar` | `:986-997` | **`:995-1004`** | +9 (S45/B) |
| `models.generarGrading` | `endpoints.js:158` | **igual** | — |
| URL `generar-grading/` | `urls.py:235` | **igual** | — |
| `generate_grading_view` | `views.py:3003` | **igual** (decorador `@bat_escriptura(SUP_ESCALAT)` a `:3002`) | — |
| `bump_grading_version_and_generate` | `services.py:1058` | **igual** | — |
| `generate_graded_specs` | `services.py:166` | **igual** | — |
| `_load_grading_rules_per_garment` | `services.py:828` | **igual** | — |
| `_apply_rule` | `services.py:1144` | **igual** | — |
| **fallback del llegat** | `services.py:1197-1198` | **`services.py:1197-1198`** | — |
| `set_pom_regim_view` | `views.py:5121` | **`views.py:5122`** (`:5121` = `@bat_escriptura(SUP_ESCALAT)`) | 0 real |
| lookup sense `actiu` (defecte 2) | `views.py:5173` | **igual** | — |
| escriptures del règim | `views.py:5202-5220` | **`:5202-5217`** | — |
| `gravar_pom_view` | `views.py:2325` | **igual**; regla a **`:2534-2569`** | — |
| `_sembra_step_des_dels_specs` | `views.py:5073` | **igual** | — |
| payload `taula-mesures` | `views.py:2141-2144` | **igual** | — |
| `GraduacioSuperficie` payload | `:220-226` | **`:222-226`** | +2 |
| `GraduacioSuperficie` degenerada | `:114-118` | **`:105-110`** (`esLinearDegenerada`) | −9 |
| `GraduacioSuperficie` cel·les | `:323-380` | **`:361-385`** | +38 (G1/G2/G3) |

**Els sis defectes de §A.5 segueixen vius, verificats un a un sobre `dev`:**

1. `set_pom_regim_view:5202-5217` escriu `logica`/`increment_base`/`increment_break`/
   `talla_break_label`/`_pos` i **mai `increment`**. `GraduacioSuperficie.jsx:223` envia
   `num(camps.increment_base)` → **`null` si el camp es buida**.
2. `views.py:5173` i `views.py:2534` filtren **sense `actiu=True`**.
3. `views.py:2534` filtra `(model, pom_id)` **sense `garment`**.
4. `es_linear_degenerada` (`grading_regime.py:58-65`) segueix retornant `False` amb break informat.
5. `talla_break_pos` es calcula contra `model.size_run_model` (`views.py:5216-5217`) i el motor
   resol per etiqueta contra `run_sistema` (`grading_utils.py:992-1004`).
6. Dos criteris de SizeFitting: `views.py:3027` vs `fitting/services.py:_resolve_working_size_fitting`.

### 1.3 · 🚨 EL FALLBACK DEL LLEGAT SÓN **DOS**, I LA DIAGNOSI NOMÉS EN VA VEURE UN

Aquest és el retorn més important d'aquest re-ancoratge.

```python
# ① pom/services.py:1197-1198  —  _apply_rule, branca LINEAR
if grading_type == 'LINEAR':
    return base_val + (steps * increment), 'LINEAR'      # increment = el del JOC ANTIC

# ② pom/grading_utils.py:1016-1019  —  increment_de_l_aresta
ib_raw = getattr(rule, 'increment_base', None)
if ib_raw is None:                          # LINEAR pur legacy: pas uniforme
    inc_raw = getattr(rule, 'increment', None)
    return float(inc_raw) if inc_raw is not None else 0.0
```

**No són el mateix node i no els arriba la mateixa gent.** ① el travessa el motor de propagació
(Escalat → `GradedSpec`). ② el travessa **`propaga_ancoratges`**
(`grading_utils.py:1051-1103`), que **no** té el guard `increment_base is not None` a sobre —
és el seu cridador qui decideix— i que serveix **dues superfícies més**:

| Cridador de `propaga_ancoratges` | Superfície |
|---|---|
| `fitting/views.py:722` (import a `:650`) | la **presa** — E1 «Mesurar prenda» / «Mesurar set» |
| `models_app/views.py:3459` (import a `:3367`) | derivació de **BaseMeasurement** des d'una talla no-base |

`propaga_ancoratges:1092-1096` només avisa quan **totes dues** (`increment_base` **i**
`increment`) són `None` — o sigui que amb `ib=None` i `increment=2.00` propaga en silenci amb el
delta del joc antic, igual que ①.

🚨 **Conseqüència per al sprint:** retirar el fallback **només a ① deixaria les dues superfícies
divergint**: Escalat diria una cosa i la presa una altra sobre la mateixa regla. **Els dos nodes
van al mateix commit, i el banc §0 NO ho veu** (el banc mesura `GradedSpec`, no la propagació per
ancoratge). El fix A necessita **una segona prova** sobre `propaga_ancoratges`.

### 1.4 · Cens de backfill a STAGING (les guardes)

Mesurat per schema amb `PGOPTIONS` read-only. **Cap xifra és la de PROD.**

| Schema · taula | LINEAR actives | `increment ≠ increment_base` | `increment_base IS NULL` | totes |
|---|---:|---:|---:|---:|
| **`fhort`.ModelGradingRule** | **335** | **14** | **0** | 503 (144 FIXED · 335 LINEAR · 24 STEP) |
| **`los`.ModelGradingRule** | 0 | 0 | 0 | **0** |
| **`fhort`.GradingRule** (catàleg) | **98** | **0** | **0** | 142 (44 FIXED · 98 LINEAR) |
| **`los`.GradingRule** | 0 | 0 | 0 | 0 |
| **`public`.GradingRule** | 0 | 0 | 0 | 0 |
| `public`.ModelGradingRule | — | — | — | **taula absent** (és TENANT) |

**🔑 LES 14 DIVERGENTS SÓN TOTES DEL 1383, I TOTES `origen='MANUAL'`.**

```
model 1383 TRV-SS27-0001   n=14  (MANUAL=14)     ← única fila del GROUP BY de tot fhort
```

Això no és una curiositat: **és la prova empírica del mecanisme del defecte 1**. La divergència
no la fabrica la materialització (que copia els dos camps, `models_app/services.py:374-375`), la
fabrica **l'edició manual** — l'única porta que escriu `increment_base` i no `increment`. En un
schema amb 8 models i 503 residents, el 100% de la divergència viu al model que algú ha editat
a mà.

**Les 14 del 1383** (de 21 `MANUAL`; les altres 7 casen per coincidència):

| POM | logica | `increment` (llegat) | `increment_base` | `increment_break` | break |
|---|---|---:|---:|---:|---|
| `C` | LINEAR | 1.50 | 2.00 | 3.00 | M |
| **`D`** | LINEAR | **2.00** | **0.50** | 0.50 | M |
| `E` | LINEAR | 1.00 | 0.00 | 0.60 | M |
| `E1` | LINEAR | 0.25 | 0.00 | 0.30 | M |
| `E7` | LINEAR | 0.15 | 0.00 | 0.00 | M |
| `EK` | LINEAR | 0.50 | 0.00 | 0.00 | M |
| `EK1` | LINEAR | 0.25 | 0.00 | 0.00 | M |
| `F` | LINEAR | 1.00 | 0.00 | 2.00 | M |
| `I` | LINEAR | 0.70 | 0.00 | 1.00 | M |
| `J` | LINEAR | 0.60 | 0.30 | 0.75 | M |
| `J1` | LINEAR | 0.30 | 0.25 | 0.25 | M |
| `S` | LINEAR | 0.70 | 0.00 | 0.80 | M |
| `S2` | LINEAR | 0.70 | 0.00 | 0.80 | M |
| `SF` | LINEAR | 0.70 | 0.00 | 0.50 | M |

**Nota sobre les 39 FIXED del 1383:** totes tenen `increment=0.00` i `increment_base=NULL`. En
SQL cru `increment IS DISTINCT FROM increment_base` també les compta (dona 53 en comptes de 14).
**No entren al backfill:** amb `logica='FIXED'` i `ib=NULL`, `_apply_rule:1186` no agafa la
branca canònica i cau a `elif grading_type == 'FIXED': return base_val` — el llegat no s'hi
llegeix mai. **La guarda del backfill ha de ser `logica='LINEAR' AND increment_base IS NOT NULL`.**

**`increment_base IS NULL` a LINEAR: 0 a tot arreu** → el defecte segueix **armat i no disparat**,
igual que a PROD.

**Per a `los`:** la migració hi ha de córrer igual (schema per schema), però **el backfill de
dades hi és un no-op**: 0 files.

### 1.5 · ESCRIPTORS de `increment` / `increment_base` / `increment_break`

Cens complet dels camins vius (tests i migracions fora).

**A · escriuen els DOS mons (correctes avui, i han de seguir-ho sent):**

| # | Node | Àncora | Nota |
|---|---|---|---|
| 1 | `materialize_model_grading_rules` | `models_app/services.py:372-382` | joc → residents. **Origen de la divergència ZERO** |
| 2 | `..._from_specs` | `models_app/services.py:414-428` | specs → residents |
| 3 | `sembra/actualitza regles del contenidor` | `models_app/services.py:516-525` | `GradingRule.update_or_create` |
| 4 | **Federació** | `tenants/federation_service.py:735-747` (emet) · **`:899-903`** (crea) | ⚠️ **contracte entre cases**: viatgen els 7 camps |
| 5 | `gravar_pom_view` — **creació** | `models_app/views.py:2536-2547` | copia de `src` (el joc) |
| 6 | `set_pom_regim_view` — **creació** | `models_app/views.py:5184-5192` | copia de `src` (el joc) |
| 7 | `backfill_grading_break` (command) | `pom/management/commands/backfill_grading_break.py:102-103` | ja existeix un backfill germà |
| 8 | `sembra_model_837` | `models_app/management/commands/sembra_model_837.py:677-678` | el banc |
| 9 | seeds LOSAN / v4 | `seed_losan_rules_v2.py`, `reseed_tenant_fhort.py:403`, `seed_losan_master_delta.py` | 6 fitxers |

**B · 🚨 ESCRIUEN NOMÉS EL CANÒNIC (mai `increment`) → fabriquen divergència:**

| # | Node | Àncora | Superfície que hi entra |
|---|---|---|---|
| 10 | **`set_pom_regim_view`** — **actualització** | **`models_app/views.py:5202-5217`** | Graduació · Mesures (`CheckMeasureEditor`) · Escalat |
| 11 | **`gravar_pom_view`** — **actualització** | **`models_app/views.py:2550-2558`** | «Gravar POM» (taula de gènesi) |
| 12 | **`GradingRuleSerializer`** via `JocsDeRegles` | `JocsDeRegles.jsx:794-830` → `gradingRules.update` → `pom/serializers.py:294-303` | **catàleg de jocs** — el mateix forat, a l'altra taula |

**C · 🚨 ESCRIUEN NOMÉS EL LLEGAT (mai el canònic) → el forat SIMÈTRIC, i és NOU:**

| # | Node | Àncora | Ruta viva? |
|---|---|---|---|
| 13 | **`update_grading_rule_with_history_view`** (S4) | **`pom/s4_views.py:78-85`** — `rule.save(update_fields=['increment','logica'])` | **SÍ** · `tasks/urls.py:196` · **la crida `SizeSetDetail.jsx:63`** amb `{increment: …}` |
| 14 | **`update_grading_rule_view`** (S2) | **`pom/s2_views.py:323-326`** — idem | **SÍ** · `tasks/urls.py:176` · sense consumidor al front |
| 15 | **`restore_version_view`** (S4) | **`pom/s4_views.py:303-307`** — restaura `increment`+`logica` i prou | **SÍ** · `tasks/urls.py` |
| 16 | **`clone_sizing_profile_view`** (S2) | **`pom/s2_views.py:230-238`** — **el clon PERD `increment_base`, `increment_break`, `talla_break_label`, `talla_break_pos`** | **SÍ** · `endpoints.js:355` (`sizingProfiles.clone`) |

> **#16 és una pèrdua de dades silenciosa que ja existeix avui**, independent del fix A: clonar
> un perfil de talles fabrica un joc amb els breaks **esborrats** i el mateix `increment` llegat.
> Amb el llegat retirat, aquestes regles clonades quedarien **planes a delta 0**.

**Veredicte per al sprint:** el backfill **no es pot desplegar sol**. Els 4 escriptors del bloc C
tornarien a obrir la divergència a la primera edició, i #16 la fabricaria per lots. **Cadascun és
una línia** (afegir `increment_base` al costat de `increment`, o al `update_fields`), però **han
d'entrar al mateix commit que el backfill**.

### 1.6 · LECTORS del llegat `increment`

| # | Lector | Àncora | Què passa quan el llegat es retiri |
|---|---|---|---|
| 1 | `_apply_rule` LINEAR | `pom/services.py:1178, 1197-1198` | **el fallback ①** |
| 2 | `increment_de_l_aresta` | `pom/grading_utils.py:1016-1019` | **el fallback ②** (§1.3) |
| 3 | `propaga_ancoratges` (avís) | `pom/grading_utils.py:1092-1096` | condició a revisar |
| 4 | **`grading_rules_match`** | `pom/grading_utils.py:68-118` — compara **només** `logica`+`increment`+`valors_step` | 🚩 declara EQUIVALENTS dues regles amb breaks diferents. **Sense cap cridador viu** avui (només citada a `pom/serializers.py:386` en comentari) → deute latent, no bloquejant |
| 5 | **`export_grading_csv_view`** | `pom/s8_views.py:82` i `:147` | **CSV amb la columna «Increment/talla» = el llegat**. Ruta viva (`tasks/urls.py:232`), sense consumidor a `endpoints.js` → s'hi arriba per URL |
| 6 | `rule_to_spec` | `pom/grading_utils.py:754` | serveix `increment` al dict d'specs |
| 7 | `export_losan_package` | `pom/management/commands/export_losan_package.py:336` | exporta **tots dos** — correcte |
| 8 | `GradingRuleSerializer` | `pom/serializers.py:302` | exposa **tots dos** — correcte |
| 9 | `detecta_regla` / import | `pom/grading_utils.py:200-259, 456-459`; `pom/size_map_views.py:326-350, 561-589, 990-996` | el llegat és la **sortida del detector**; el canònic el deriva `backfill_grading_break` |
| 10 | federació | `tenants/federation_service.py:741` | contracte |

**Pantalles a migrar (les que un tècnic veu):** la **#5** (CSV d'export de regles) i la **#13/#16**
del bloc C. La resta són interns.

### 1.7 · SUPERFÍCIES vs CAMPS — taula definitiva

| # | Superfície | Àncora dev | Font | Camps que llegeix | Estat |
|---|---|---|---|---|---|
| 1 | **Mesures** (consulta, 4 col. de regla) | `EditableTable.jsx:59-77` (`AMPLADES` + `COLS_GRADING`) | `taula-mesures` | `logica` · `increment_base` · `increment_break` · `talla_break_label` | ✅ **canònics** (verificat Agus, en viu) |
| 2 | **Escalat** (`escalatRuleLeadCols`) | `fittingGridAdapter.jsx:421-450` | `taula-mesures` | idem | ✅ **canònics** (verificat Agus) |
| 3 | **Graella de fitting** | `measureSources.jsx` · `FittingDetail.jsx` | — | **CAP** — G5 li va treure la columna RÈGIM (bloc 3+D) | ✅ (verificat Agus) |
| 4 | **Graduació** (editable) | `GraduacioSuperficie.jsx:361-385` (cel·les) · `:222-226` (payload) | `taula-mesures` | idem | ✅ canònics |
| 5 | **`CheckMeasureEditor`** | `CheckMeasureEditor.jsx:151-230` | `taula-mesures` | idem | ✅ canònics |
| 6 | **Fitxa tècnica Q8b** | `taulesQ8.js:212-215` → `TechSheetEditor.jsx:5404-5457` | `taula-mesures` | `logica`→`regla`, `increment_base`→`delta`, `increment_break`→`delta_break`, `talla_break_label`→`talla_break` | ✅ **canònics** — comprovat avui |
| 7 | **Export PDF de la fitxa** | `TechSheetEditor.jsx` (pdf-lib, `buildTableCellPrimitives`) | **el `snapshot` de l'objecte taula** | cap camp de regla directe | ✅ **cap camí propi** — imprimeix el que Q8b hi va desar |
| 8 | **API pública** | `pom/serializers.py:294-303` (`GradingRule`) | ORM | **tots dos mons** | ⚠️ exposa el llegat |
| 9 | **API pública** (residents) | — | — | **no hi ha `ModelGradingRuleSerializer`** | ✅ res a migrar |
| 10 | **Wizard — preview** | `pom/wizard_views.py:625-628` | `GradingRule` | `logica` · `increment_base` · `increment_break` · `talla_break_label` | ✅ **canònics** — comprovat avui |
| 11 | **Jocs de regles** (catàleg, editable) | `JocsDeRegles.jsx:302-303, 769-830` | `gradingRuleSets.get` | canònics per editar; `deltaLlegit:302` cau al llegat en LECTURA | ⚠️ **mixt** |
| 12 | **CSV d'export de regles** | `pom/s8_views.py:82, 147` | ORM | **només el llegat** | 🚨 **a migrar** |
| 13 | **Size Set (perfil de talles)** | `SizeSetDetail.jsx:63` | s4 | **escriu només el llegat** | 🚨 **a migrar** |

**Resum:** dels 7 punts que quedaven per verificar, **6 llegeixen el canònic** (fitxa Q8, export
PDF, API de residents, wizard, i les tres ja verificades per l'Agus). Els **dos que no** són els
que ningú havia mirat: **el CSV d'export** i **la pantalla de Size Set**.

### 1.8 · La peça «Presa declara versió»

**El racó** viu a `frontend/src/pages/PropagatedEditor.jsx:340-351` — el prop `dreta` de
`<SubTabs>`, que pinta `t('escalat.presa_del', {data})` o `escalat.presa_tancada_del`. La llarga
nota de `:315-330` explica per què hi és i per què **ja no és un gest** (E3a). L'estat el deriva
`utils/estatPresa.js` (`estatDeLaPresa`, `PropagatedEditor.jsx:90-92`) des del payload de
`GET /api/v1/fitting/model/<id>/presa/` (`presaEscalat.get`, `:74`).

**D'on es llegeix la GradingVersion d'origen: FK DIRECTA, i ja està serialitzada.**

```python
# backend/fhort/fitting/models.py:395-397
grading_version = models.ForeignKey(GradingVersion, on_delete=models.PROTECT,
                                    related_name='piece_fittings')
```

```python
# backend/fhort/fitting/serializers.py:223-232  ·  PieceFitting
grading_version_num = serializers.IntegerField(source='grading_version.version_number',
                                               read_only=True)
fields = (..., 'grading_version', 'grading_version_num', ...)
```

**Cost: una línia de backend i una de front.** El payload de `presa/`
(`fitting/escalat_presa_views.py:147-163`) **no la porta encara** — hi entra al costat de
`piece_fitting_id`:

```python
# backend/fhort/fitting/escalat_presa_views.py:150
'piece_fitting_id': pf.id,
'grading_version': {'id': pf.grading_version_id,
                    'num': pf.grading_version.version_number},   # ← això és tot
```

🔑 **I el banc ja té el cas viu:** al 1383, `PieceFitting` pk=52 penja de la **v2** i pk=53 de la
**v6** (`SEMBRA §8`). Una presa que declari la seva versió diria, sobre el mateix model, dues
coses diferents — que és exactament el que la peça vol fer visible.

---

<a id="s2"></a>
## §2 · TRAM J — CONSULTA vs TREBALL (cens complet, sense diagnosi prèvia)

### 2.1 · El modal «Has acabat?»

**Component:** `frontend/src/components/model/ModalAcabarTasca.jsx` (129 línies).
**i18n:** bloc `acabar_tasca` (`ca.json:4786-4796`, + `en`/`es`).

| Node | Àncora | Detall |
|---|---|---|
| Estats oferts | `ModalAcabarTasca.jsx:23-24` | **exactament DOS**: `ACABAR`→`'Done'`, `PAUSAR`→`'Paused'`. Premarcat `ACABAR` (`:30`) |
| Transició | `:52-56` | `modelTasks.transition(taskId, {to_status})` |
| Text | `:93-107` | *«Has acabat {{tasca}}?»* · *«Els canvis ja estan desats. El que decideixes ara és l'estat de la tasca.»* · temps de la sessió i total |
| Tolerància al 400 | `:60-63` | un `400 /transici/i` es tracta com a **èxit**: la intenció ja és certa |

**Quan es dispara:** en **sortir** d'una superfície de treball, via `exitEdit`
(`ModelSheet.jsx:593-611`) i el `setAcabant({taskId, tasca})` de `:606`. La condició, escrita
com a llei a `:587-592`:

> *«es demana la tasca **FRESCA** i el modal només surt si segueix `InProgress`»*

I, tres línies més avall (`ModelSheet.jsx:590-592`), **la decisió que el tram J ha de respectar**:

> ⚠️ **«EL CRITERI NO ÉS LA DURADA.** "No hi ha hagut sessió" no vol dir "ha durat poc": una
> sessió de dos minuts amb la tasca oberta ensenya el modal igual que una de dues hores
> (decisió d'Agus). El que el fa callar és que no hi hagi res obert.»

→ **Un gating J per llindar de temps contradiria una decisió ja presa.** El predicat ha de ser
**«hi ha hagut escriptura?»**, no **«quant ha durat?»**.

### 2.2 · El cicle d'entrada i de sortida

**ENTRAR** — `POST /api/v1/models/<id>/open-task/` → `tasks/views_b.py:536-660`:

| Pas | Àncora | Efecte |
|---|---|---|
| guard allow-list | `views_b.py:568-573` | 403 amb `code='task_type_not_allowed'` |
| **crea-si-falta** | `views_b.py:578-587` | `tasca_vigent(model, code)`; si no n'hi ha, **crea una `ModelTask` `Pending`/`prevista`** |
| **posa En curs** | `views_b.py:590-592` → `services_c.transition_task` | ↓ |
| — exclusió un-InProgress | `services_c.py:283` (`_aplica_exclusio_tecnic`) | **pausa l'altra tasca oberta del tècnic, a qualsevol model** |
| — **obre TimerEntrada** | `services_c.py:285` → `_open_timer` a `:22-30` | **incondicional. Cap comprovació d'escriptura** |
| — `started_at` | `services_c.py:286-287` | primer inici |
| handoff | `views_b.py:597-611` | `traspassa_tram` + reassigna `assignee` + `recompute_for_technicians` |
| **reancoratge del pla** | `views_b.py:618-628` | `recompute_for_technicians` + `model.reanchored_by_start = True` |
| fase del model | `services_c.py:307-310` | `Pending` → **`Dev`** |
| encàrrec | `services_c.py:330-336` | `assign_work_order(task, now)` |
| **canal de federació** | `services_c.py:352-357` | `sync_estat_segur(model, SENTIT_MADURESA)` → **publica al bessó de la marca** |

**SORTIR** — `transition_task(task, 'Paused', …)`:
`services_c.py:293-296` → `_close_open_timer` (`:33-41`) tanca el tram i escriu `minuts`;
després `_log` (`:55-58`), i **un segon `sync_estat_segur`** (`:352-357`).

🚨 **El preu d'una consulta avui, mesurat:** *fins a* una `ModelTask` **creada**, la tasca oberta
d'un altre model **pausada**, un `TimerEntrada` amb minuts reals, dues files a `TaskTransition`,
el model mogut de `Pending` a `Dev`, `reanchored_by_start=True`, una possible línia d'encàrrec, i
**dues publicacions d'estat a l'altra casa**.

### 2.3 · 🔑 ON ES POT SABER «HI HA HAGUT ESCRIPTURA EN AQUESTA SESSIÓ»

**El senyal ja existeix, ja està cablat, i es diu `batec_escriptura`.**

`backend/fhort/tasks/services_batec.py` — capçalera: *«"en curs" vol dir "s'hi escriu" (D-2)»*.
La meritació SaaS **ja va fer aquest mateix viatge**: `services_c.py:314-327` explica que el fet
facturable era «algú ha obert una porta» i ara és **«algú hi ha ESCRIT»**, perquè *«tocar una
porta tres segons per error facturava»*. **El tram J és el mateix moviment, aplicat al temps en
comptes de a la factura.**

Els **emissors ja cablats** (cada un és un punt on hi ha hagut escriptura de debò):

| Superfície | Àncores |
|---|---|
| `SUP_MESURES` | `models_app/views.py:544, 1901, 2324, 3875, 3959, 5002` |
| `SUP_ESCALAT` | `models_app/views.py:3002` (propagar) · `:3341` · `:5121` (**`set_pom_regim_view`**) |
| `SUP_PRESA` | `fitting/views.py:548, 572, 579, 637` · `fitting/escalat_presa_views.py:225` · `models_app/views_size_check.py:78, 98` |
| `SUP_FITXA` | `models_app/ftt_document_views.py:250` |

**Les tres opcions per fer-lo durable, i el seu cost:**

| Opció | Cost | Perill |
|---|---|---|
| **(a)** camp nou a `TimerEntrada` (p. ex. `te_escriptura` bool), escrit per `batec_escriptura` | migració trivial + 1 línia al batec | cap; és additiu i el batec ja té l'obertura a la mà |
| **(b)** reutilitzar `last_heartbeat` | **zero** | 🚨 **NO ES POT.** `tasks/models.py:14-18` ho diu en lletra: *«Hi ha **dos emissors i UN sol camp**: el guard (presència) i l'escriptura (activitat)»*. `last_heartbeat` no distingeix «sóc davant la pantalla» de «he escrit» |
| **(c)** recomptar `MeasurementChangeLog` des de `TimerEntrada.inici` | zero de dades | ⚠️ **cobreix una superfície de quatre**: `models_app/signals.py:254-283` només registra canvis de `base_value_cm` de `BaseMeasurement`. Escalat, presa i fitxa hi són invisibles |
| **(d)** senyal de frontend (recompte de `save` a `ModelSheet`) | baix | 🚨 el client és el testimoni menys fiable; i la sessió pot morir sense sortir pel botó |

→ **(a) és la de menys radi i la que honra el ganxo que el propi model ja declara.**

### 2.4 · Welford, TimerEntrada i **la llei d'higiene**

| Node | Àncora | Detall |
|---|---|---|
| Obertura del tram | `tasks/services_c.py:22-30` | `TimerEntrada.objects.create(..., actiu=True, origen=…)` |
| Tancament | `tasks/services_c.py:33-41` | `minuts = max(0, int((now-inici).total_seconds()//60))` |
| Temps real de la tasca | `tasks/services_i.py:41-44` (`_real_minutes`) | `timers.filter(TRAMS_SANS).aggregate(Sum('minuts'))` |
| **Welford** | `tasks/services_i.py:47-75` (`record_actual_time`) | **només a `→Done`** (`services_c.py:338-342`) |
| Guarda del Welford | `services_i.py:57-59` | `x <= 0 → return None` |

**🔒 LA LLEI D'HIGIENE, i és UNA constant compartida** — `tasks/services_i.py:12-24`:

```python
MAX_MINUTS_TRAM = 24 * 60
TRAMS_SANS = Q(fi__isnull=False, minuts__lte=MAX_MINUTS_TRAM)
```

amb el seu mirall Python `tram_compta` (`:27-30`) i l'agregador únic `minuts_per_model_task`
(`:33-38`). El comentari mana el criteri: **EXCLUSIÓ, no retall** — *«un tram de 3.710 min no és
una jornada llarga que calgui podar: és una fuita, i no sabem quant s'hi va treballar»*.
Consumidors: `services_r.py:282, 313`, `recompute_welford`, l'albarà i el registre de consum.

**Com es descartaria el temps d'una consulta, i què no es pot fer:**

| Camí | Veredicte |
|---|---|
| **no crear `TimerEntrada`** | 🚨 **trenca invariants**: `_open_timer` tanca trams previs (`:28`), l'exclusió un-InProgress mira **trams oberts** (`_aplica_exclusio_tecnic`), i el guard de tasca oblidada compta des d'`inici`/`last_heartbeat`. Sense tram, un tècnic pot acabar amb dues tasques obertes |
| **marcar-lo** (`origen` nou, o el camp de (a)) i **afegir una clàusula a `TRAMS_SANS`** | ✅ **el camí net**: `TRAMS_SANS` és **el punt únic**; una clàusula allà tapa Welford, albarà, consum i tots els agregadors **alhora**. `TimerEntrada.ORIGEN_CHOICES` (`tasks/models.py:24-27`) ja té el precedent: `mesurat` vs `declarat` |
| **per llindar de durada** | 🚨 **contradiu la decisió d'Agus** de `ModelSheet.jsx:590-592` (§2.1), i xocaria amb `MAX_MINUTS_TRAM`, que és un llindar **de fuita**, no de plausibilitat de feina |

⚠️ **Qui afegeixi una clàusula a `TRAMS_SANS` ha d'afegir-la també a `tram_compta`**: són
germans declarats (*«Ha de dir SEMPRE el mateix que el filtre ORM»*) i cap gate els compara.

### 2.5 · «Tornar a consulta» — **no és mitja G1: és el gallet**

```jsx
// frontend/src/pages/ModelSheet.jsx:1256-1260   (Mesures)
{editing === 'Mesures' ? (
  <button type="button" onClick={exitEdit} style={btnAccio()}>
    <i className="ti ti-eye" /> {t('model_sheet.back_to_consult')}
// frontend/src/pages/ModelSheet.jsx:1403-1408   (Escalat) — el mateix `onClick={exitEdit}`
```

**És literalment `exitEdit`**, el mateix handler que qualsevol altra sortida. No conté cap
predicat propi i no distingeix res: **avui és, exactament, el botó que obre el modal**. El
gating G1 no hi és a mitges — el que hi ha és **el punt únic on ha d'entrar**: un predicat a
`exitEdit` (`ModelSheet.jsx:593-611`), just al costat del `tasca?.status !== 'InProgress'` de
`:600`, que és el germà exacte de la pregunta nova.

### 2.6 · Riscos censats

| # | Risc | Àncora | Estat real |
|---|---|---|---|
| **R1** | **S4 play sobre Feta** | `ALLOWED` a `services_c.py:11-19`: `'Done': {'InProgress'}` · `WorkPlan.jsx:44` *«play = Pending/Paused/**Done** (start/resume/**reopen**)»* · `:261-265` | 🚨 **VIU.** Entrar en consulta a una tasca `Done` la **REOBRE** (rectificació), i si té albarà emès rebota amb 409 `tasca_albaranada` (`services_c.py:255-262`). **Una consulta no pot reobrir res** |
| **R2** | **Exclusió un-InProgress** | `services_c.py:283` → `_aplica_exclusio_tecnic:61+` | 🚨 **VIU.** Consultar el model B **pausa la feina real del model A**. El tram J ha de decidir si una consulta entra a l'exclusió (i, si hi entra, la feina real es perd el rellotge per una mirada) |
| **R3** | **Handoff de federació** | `services_c.py:597-611` (`open-task`) + `traspassa_tram` a `services_c.py:367+` | 🚨 **VIU i és el més sever.** Consultar una tasca `InProgress` **d'un altre tècnic** dispara el **claim**: `traspassa_tram` + `task.assignee = profile`. **Una consulta ENDÚ LA TASCA.** «Pausada conserva la mà» es refereix a l'estat; això no és pausar, és **prendre-la** |
| **R4** | **Canal d'estat cap a la marca** | `services_c.py:352-357` (`sync_estat_segur`, `SENTIT_MADURESA`) → `federation_service.py:436-491` | ⚠️ Cada consulta publica **dues** vegades `{fase_actual, federacio_estat}` al bessó. Cap dany de dades; sí, soroll a l'altra casa |
| **R5** | La consulta **crea** la tasca | `views_b.py:578-587` | ⚠️ Obrir per mirar una tasca que no existeix **la crea** (`Pending`/`prevista`). Té ordre al final i estimació — entra al pla |
| **R6** | `reanchored_by_start` / fase `Dev` | `views_b.py:624-626` · `services_c.py:310` | ⚠️ Una consulta treu el model de `Pending` i el reancora al present del planificador |

**On viu la porta que els tanca tots.** R1, R2, R3, R5 i R6 neixen **abans** del modal: neixen a
`open_model_task_view`. El gating de sortida (G1) **no en tanca cap**. El tram J necessita, com a
mínim, **una segona porta d'entrada** (una consulta que no transiciona) o un paràmetre explícit a
`open-task`. Això és una decisió d'arquitectura, no de sprint, i **la censo sense decidir-la**.

---

<a id="s3"></a>
## §3 · H — TAULA DE MESURES BASE A LA FITXA

### 3.1 · `insertTableBaseMeasures` — el cos REAL de la versió retirada

Recuperat de `git show d15e198b^:frontend/src/pages/TechSheetEditor.jsx`, **línies 5700-5749**
(la funció; despatx a `:5998`).

🚨 **La diagnosi §H.2 va citar la versió del NAIXEMENT (`38a0761e`), no la de la MORT.** No són
la mateixa taula:

| | `38a0761e` (naixement, citat a la diagnosi) | **`d15e198b^` (el que hi havia en morir)** |
|---|---|---|
| Columnes | **5**: `ref` · `pom` · `base` · **`tol`** · **`coment`** | **3**: `ref` (22) · `pom` (46) · `base` (24) |
| Capçalera de `ref` | `tbl_col_nomenclatura` | **`''`** — el títol va caure (decisió d'Agus, 31/07) |
| Capçalera de `base` | `tbl_col_base_cm` | **`tbl_col_base_cm_talla`, amb la talla interpolada**, amb *fallback* a la sense talla |
| Idioma | `t(...)` (idioma de qui insereix) | **`tDoc(...)`** (idioma del **document**) |
| Eix de peça | absent | **`garmentId: GARMENT_MARE`** ja hi era |
| Nom de POM | `bm.nom_en \|\| bm.nom_client \|\| …` | **`nomDeTaula(bm, dicc, docLang)`** |

**El que assumia:**
- **Eix:** cap. `garmentId: GARMENT_MARE` **cablat**, amb el seu propi comentari admetent-ho:
  *«SET-2/T9 — la taula surt de TOTES les mesures del model, o sigui de la prenda mare. Quan la
  partició per peça tingui més d'una branca, cada objecte portarà la seva.»*
- **Font:** `GET /api/v1/models/<id>/base-measurements/` (crua, `fetch` + `authHeaders`).
- **Files:** **totes** les mesures vives, **inclosos els POM sense valor** — a posta: *«La cel·la
  buida en una fitxa impresa és on el tècnic anota a mà; podar les files en silenci seria decidir
  per ell què no li importa.»* **Aquesta llei s'ha de conservar.**
- **Sense partició per ample** (3 columnes fixes, no creix amb el run) i **sense paginació**
  (`addObject` directe, no `inserirGrupPaginat`).
- Porta: `if (!locked) return` + `if (!bms.length) flash(empty)`.

**El que cal portar a l'eix de prenda (llei Q8):**

| # | Què | Com ho fan les germanes |
|---|---|---|
| 1 | Files amb `garment` propi | el constructor ha d'emetre `garment` per fila, com `filesGrading` (`taulesQ8.js:212-215`) |
| 2 | Repartiment per peça | `grupsQ8(files)` (`TechSheetEditor.jsx:5263`) + `nomesLaPeca(grups, garment)` (`:5266`) |
| 3 | Un objecte per peça | `garmentId: g.garment` + `titol: g.titol` a la 1a banda |
| 4 | Amplada de POM | `ampladaPomQ8(files)` (`:5273`) |
| 5 | Inserció | `inserirGrupPaginat(entrades)` (`:5120`) — el que fa el sostre A4 |
| 6 | Capçaleres | **`tEn`** (`:5233`, `i18n.getFixedT('en')`), **no `tDoc`** — la llei Q8 és anglès fix |
| 7 | Fila de títol | `nomTaula` + `data: dataDoc(...)` (Q8-ter/T4) |
| 8 | Estil | `{fontSize: 9, capcaleraFina: true, zebra: true}` — **sòl 8pt** (`:892`, `:935`, `:5103`) |
| 9 | `snapshot` | `{model_id, talla_base, garment, snapshot_at}` |
| 10 | Partició per talles | **no cal** — la taula no creix amb el run |

### 3.2 · 🚨 LA FONT — la diagnosi §H.4 es va equivocar

> **Deia:** *«`base-measurements/` **no** serveix `garment` i faria caure totes les files a la
> mare — el mateix motiu que `taulesQ8.js:16-18` dona per no fer servir `graded-table/`»*

**Totes dues meitats són falses.**

1. **`taulesQ8.js:16-18` parla de `graded-table/`, no de `base-measurements/`.** Text literal:
   *«`graded-table/` NO serveix `garment` i faria caure totes les files a la mare.»* La frase es
   va traslladar a un altre endpoint.

2. **`base-measurements/` SÍ que serveix `garment`**, i des de SET-2/F1:

```python
# backend/fhort/models_app/serializers.py:476   ·   BaseMeasurementSerializer.Meta.fields
'capa', 'instancia', 'garment',
'base_value_cm', 'is_active', 'notes',
'nom_fitxa', 'origen',
```

   El comentari de `:465-475` documenta que era **exactament** el forat que F1 va tancar
   (*«una fila de la peça 02 NEIXIA A LA MARE»*), i `filterset_fields` ja l'exposava en lectura.

**Conclusió operativa: hi ha DUES fonts vàlides, i tenen preus diferents.**

| Font | Àncora | A favor | En contra |
|---|---|---|---|
| **`taula-mesures`** | `models_app/views.py:1982` · ja carregada per `taulaMesuresDelModel` (`TechSheetEditor.jsx:5389-5398`) | ✅ una crida ja escrita · porta `garment` + `base_value_cm` + `graded` + règim + **`grading_version_data`** per a la fila de títol · **el mateix contracte que Q8b i Q8c** | porta molt més del que la taula necessita |
| **`base-measurements/`** | `models_app/urls.py:123` | ✅ porta `garment`, `nom_fitxa`, **`origen`** (diu si el valor ve d'un fitting) · és el que la versió retirada feia servir | ❌ **no exposa tolerància** (`tol_minus`/`tol_plus` **no són a `fields`**) — la columna `tol` del naixement **no és recuperable per aquí** · una crida nova · sense data de versió per a la fila de títol |

**Recomanació (no decisió):** **`taula-mesures`**, pel motiu que la diagnosi tenia raó a donar
encara que l'argument fos l'equivocat — **és el contracte que les altres tres taules de Q8 ja
comparteixen**, i tenir-ne dues per a la mateixa fitxa és tenir-ne dues versions. 🚩 **Si algú
vol la columna `Tol±` de la versió del naixement, cap de les dues fonts la serveix: cal afegir
`tol_minus`/`tol_plus` a un serializer.**

### 3.3 · «Últim fit vàlid» — ✅ confirmat, cap camí nou

`BaseMeasurement.base_value_cm` **ÉS** l'últim fit vàlid, materialitzat:

```python
# backend/fhort/fitting/services.py:669-698  ·  consolidate_base_from_fitting
linies = (PieceFittingLine.objects.filter(piece_fitting=pf)
          .exclude(decisio=PieceFittingLine.DECISIO_REJECTED)...)
```

Dos moments l'escriuen: en **tancar** el fitting (`close_piece_fitting`,
`fitting/services.py:740`) i en **propagar** (`models_app/views.py:3090-3095`, amb
`origen='FITTED'`).

→ **La taula NOMÉS ha de llegir la base.** `taula-mesures` la porta a `base_value_cm` i
`base-measurements/` a `base_value_cm` + `origen`. **Cap endpoint nou, cap camí nou.**

### 3.4 · `TechSheetEditor.jsx` — mida i zones a reservar

**8.620 línies.** 🚨 **Regla del monòlit: qui obri H reserva el fitxer sencer.**

| Zona | Àncora | Què hi passa |
|---|---|---|
| Geometria Q8 | `:5089-5120` | `MARGE_GRUP=10` · `AMPLE_UTIL_MAX=270` · **sòl 8pt** · `inserirGrupPaginat` |
| Helpers Q8 | `:5233` (`tEn`) · `:5263` (`grupsQ8`) · `:5266` (`nomesLaPeca`) · `:5273` (`ampladaPomQ8`) · `:5279` (`ampleUtilQ8`) | **reutilitzables tal qual** |
| Font consolidada | `:5389-5398` (`taulaMesuresDelModel`) | **reutilitzable tal qual** |
| **Constructors** | `:5329` fitting · `:5404` grading · `:5478` size set · `:5558` notes | ← **la taula base hi entra com a cinquè, entre `:5478` i `:5558`** |
| **Despatx** | `:5641-5653` (`onPickTableVariant`) | ← **una branca `if (variant === 'q8_base')`** |
| **Catàleg del panell** | `:5915-5924` (`Q8_TAULES`) + porta `baseMeasuresOk` a **`:5885`** | ← **una entrada més** |
| Renderitzat del panell | `:7609`, `:7634` | ja itera `Q8_TAULES × pecesDelPanell` |
| Constructor de files | **`frontend/src/utils/taulesQ8.js`** (220 línies), al costat de `filesGrading:202` | ← **la peça nova** |

**Porta:** `baseMeasuresOk` (`:5885`, `pomRows.some(r => r.base_value_cm != null)`) **ja existeix
i ja la fan servir Q8b i Q8c** (`:5919`, `:5921`).

**Ordre al panell.** `Q8_TAULES` (`:5915-5924`) va avui `fitting · grading · size_set · notes`.
La base **hauria d'anar primera** (és l'origen de la corba) o entre `grading` i `size_set`. La
decisió és d'Agus; el codi és una posició a l'array.

**i18n:** les 18 claus × 3 idiomes van caure a `d15e198b`. Les que calen ara són menys —tres
columnes— i han de seguir la família `q8_col_*`/`q8_taula_*`, no la família `tbl_col_*`
(esborrada): `q8_taula_base`, `q8_col_base`, i el rètol de la variant.

**Banc:** `backend/fhort/fitting/test_q8_banc_taules_fitxa.py` + `ops/qa/q8_taules_fitxa.mjs` —
el bolcat de payloads és el contracte backend↔front i la taula nova hi ha d'entrar.

**Cost:** **MITJÀ-BAIX**, i **més baix que el que deia la diagnosi**: el renderitzador és
intacte, la porta hi és, els 5 helpers de repartiment són reutilitzables, i **la font ja està
carregada al fitxer**. El nou de debò segueix sent l'eix de prenda — que és el motiu pel qual la
versió antiga es va retirar.

---

<a id="s4"></a>
## §4 · E+F CONTRA LA FORMA DECIDIDA (INTERVALS)

> **La decisió MULTI-BREAK v2 NO és a `DECISIONS.md`.** Hi ha S24/S10 sobre el break **únic**
> (`DECISIONS.md:714-721`), però cap entrada d'intervals. **Viu només a l'ordre.** V. Contradiccions.

### 4.1 · Model de dades — **DIMENSIONAT, no decidit**

**Estat d'avui** — un sol parell escalar, idèntic a les dues taules:

| Camp | `pom.GradingRule` | `models_app.ModelGradingRule` |
|---|---|---|
| `increment` (llegat) | `pom/models.py:1512` | `models_app/models.py:1196` |
| `increment_base` | `pom/models.py:1516` | `models_app/models.py:1201` |
| `increment_break` | `pom/models.py:1517` | `models_app/models.py:1202` |
| `talla_break_label` | `pom/models.py:1518` | `models_app/models.py:1203` |
| `talla_break_pos` | `pom/models.py:1519` | `models_app/models.py:1204` (**cache, mai llegida**) |
| `garment` | **no, i mai** | `models_app/models.py:1241-1246` |

**Corpus a migrar, a staging:** 335 + 98 = **433 files LINEAR actives** (fhort), **0** a `los`,
**0** a `public`. A PROD la xifra és un ordre de magnitud més gran (1332 + 525).

| Opció | Consumidors que hi paguen | A favor | En contra |
|---|---|---|---|
| **(a) taula filla** `GradingRuleBreak(rule, ordre, talla_inici, talla_final, increment)` **×2** | **motor** ✅ una query més, `prefetch_related` · **serializers** ⚠️ nested writable ×2 · **import** ⚠️ `size_map_views` escriu per lots (`:328, 355, 563, 594, 1001`) · **fitxa** ✅ el payload de `taula-mesures` ja és un dict construït a mà (`views.py:2141-2144`) · **federació** 🚨 `federation_service.py:735-747` + `:899-903` — **una llista dins d'una fila del manifest** | unicitat i ordre a la BD · sense límit artificial · `CHECK` d'ordre possible | **duplica model i migració**: `models_app` és TENANT (×N schemas) i `pom` és **SHARED** (`public` **i** tenant, `models_app/models.py:1184-1189`) · N+1 a tot arreu |
| **(b) `JSONField intervals=[{inici, fi, delta}]`** ×2 | **motor** ✅ zero queries · **serializers** ✅ un camp · **import** ✅ un camp · **fitxa** ✅ · **federació** ✅ el manifest ja és JSON | **la més barata a tot arreu**; el precedent és **`valors_step`, que ja és `JSONField` i ja el travessa tot** | cap unicitat ni ordre a la BD → **validació a l'aplicació**, i ha de viure a `grading_regime.py` (punt únic) + mirall `gradingRegime.js` |
| **(c) 3 parells plans** (`_2`, `_3`) | tots ✅ trivial | migració mecànica, zero canvi estructural | **6 columnes × 2 taules**, tanca la porta a un 4t break, i **cada consumidor ha d'enumerar-los** — el forat del defecte 1 multiplicat per tres |

**El fet que decideix, i el poso al davant:** **`valors_step` ja és un `JSONField` que travessa
el motor, els dos serializers, l'import, la federació, la fitxa i les 6 comandes de sembra, i mai
ha calgut res més.** L'opció (b) no introdueix cap patró nou en aquesta casa; (a) sí, i el preu
és **doble migració SHARED+TENANT**. **No decideixo.**

**Compatibilitat enrere obligatòria:** el parell `(increment_break, talla_break_label)` ha de
seguir llegint-se mentre hi hagi una sola fila sense migrar, **i mentre la federació parli amb
una casa que no tingui la forma nova** — v. §4.5.

### 4.2 · Mapatge sobre el codi actual

**El node crític és UN**, i està aïllat:

```python
# backend/fhort/pom/grading_utils.py:1006-1031  ·  increment_de_l_aresta
aresta   = min(i, j)                              # l'aresta viu entre `aresta` i `aresta+1`
exterior = aresta + 1 if aresta >= base_idx else aresta
return brk if exterior >= break_idx else ib       # ← DOS trams, UN llindar
```

**La forma d'intervals hi encaixa sense tocar res més:**

```python
for (idx_ini, idx_fi, delta) in intervals:        # ordenats, no solapats
    if idx_ini <= exterior <= idx_fi:
        return delta
return general
```

| Node | Canvi | Cost |
|---|---|---|
| `_break_idx_de` (`grading_utils.py:992-1004`) | → llista d'`(ini, fi, delta)` en índexs de sistema | Baix |
| **`increment_de_l_aresta`** (`:1006-1031`) | **el node crític** — dues línies | **Mitjà** (la semàntica) |
| `desnivell_entre_talles` (`:1034-1049`) | **ZERO** — només suma arestes | — |
| `propaga_ancoratges` (`:1051-1103`) | **ZERO** — comparteix la mateixa aresta | — |
| `_apply_rule` (`pom/services.py:1186-1195`) | **ZERO** — ja delega | — |
| `es_linear_degenerada` / `te_break` (`grading_regime.py:41-65`) | han de mirar N intervals | Baix |

**On viu la traducció del conveni vell:** `frontend/src/utils/breakConvention.js` — `aDocument`
(`:47-50`) just abans de pintar, `aMotor` (`:57-61`) just abans de desar, `opcionsDocument`
(`:66-69`) per a les opcions del picker. **CINC superfícies hi passen**, re-ancorades a `dev`:

| Superfície | Àncora de l'import |
|---|---|
| `GraduacioSuperficie.jsx` | **`:11`** |
| `EditableTable.jsx` | **`:25`** (i `COLS_GRADING:75-76`) |
| `JocsDeRegles.jsx` | **`:11`** |
| `CheckMeasureEditor.jsx` | **`:9`** |
| `fittingGridAdapter.jsx` | **`:17`** |
| Q8b — **crua a posta** | `taulesQ8.js:193-195`, traduïda a `TechSheetEditor.jsx:5447` |

**La traducció NO té bessó a backend.** És **pura presentació**, i el motor mai la veu.

### 4.3 · ✅ VERIFICACIÓ DE L'EQUIVALÈNCIA — provada, no argumentada

**Script:** `docs/ordres/equiv_intervals_1383.py` (read-only). Implementa la forma d'intervals
**des de zero** (no crida `increment_de_l_aresta` per calcular la banda nova) i contrasta cel·la
a cel·la amb el motor d'avui, sobre les **21 regles amb mesura base** del 1383.

**Regla de lectura provada:**
> *una aresta pren el delta de l'interval que conté el seu **EXTREM EXTERIOR** (la talla de
> l'aresta més allunyada de la BASE); si cap interval no el conté, el **GENERAL**.*

**Migració provada:** `general = increment_base` · `interval = [talla_break_label .. 3XL]`
(**l'última talla del SIZESYSTEM**) · `delta = increment_break` · **etiqueta SENSE desplaçar**.

```
model 1383 · size_run ['XS','S','M','L','XL'] · run_sistema ['XXS','XS','S','M','L','XL','XXL','3XL'] · base_idx 2
MIGRACIÓ: interval = [talla_break_label .. 3XL] (última del SIZESYSTEM)

CEL·LES  IDÈNTIQUES=105  DIVERGENTS=0   (21 regles LINEAR/FIXED amb base)
```

**Els tres exemples demanats:**

| POM | Avui | Intervals | XS | S | M | L | XL | |
|---|---|---|---|---|---|---|---|---|
| **A** | ib=2.00 · brk=3.00 · break M | general Δ=2.0 · `[M..3XL]` Δ=3.0 | 42.0 | 44.0 | 47.0 | 50.0 | 53.0 | **IDÈNTIC** |
| **C** | ib=2.00 · brk=3.00 · break M<br>*(llegat `increment`=1.50 — orfe)* | general Δ=2.0 · `[M..3XL]` Δ=3.0 | 52.0 | 54.0 | 57.0 | 60.0 | 63.0 | **IDÈNTIC** |
| **D** | ib=0.50 · brk=0.50 · break M<br>*(llegat `increment`=**2.00** — la mina)* | general Δ=0.5 · `[M..3XL]` Δ=0.5 | 58.5 | 59.0 | 59.5 | 60.0 | 60.5 | **IDÈNTIC** |

L'asimetria **−2.0 / +3.0** d'`A` i `C` cau sola de la forma nova: l'aresta `XS↔S` té extrem
exterior `XS`, que **no** és a `[M..3XL]` → general 2.0; l'aresta `S↔M` té extrem exterior `M`,
que **sí** hi és → 3.0. **La semàntica del break és, literalment, un interval.**

### 4.4 · 🚨 L'OFF-BY-ONE DE LA MIGRACIÓ — **la migració de l'ordre desplaça 33 cel·les**

L'ordre especifica:

> *«migració 1-break → interval X→última talla del SIZESYSTEM amb l'off-by-one traduït:
> l'etiqueta vella marca l'ÚLTIMA talla del delta petit → inici de l'interval = la SEGÜENT en
> ordre de sistema»*

**Això és cert de la convenció de DOCUMENT i FALS de la BD.** La BD ja desa la **PRIMERA talla
del tram gran** (convenció de MOTOR, `breakConvention.js:1-24`, `grading_utils._break_idx_de`).
Aplicar el desplaçament al valor de la BD **el desplaça una segona vegada**.

**Contra-experiment del mateix script, sobre el mateix banc:**

```
── CONTRA-EXPERIMENT · interval que comença a la talla SEGÜENT ──
   cel·les que es MOUEN si l'inici de l'interval es desplaça +1: 33
```

**33 cel·les de 105.** No és un matís: és un terç de la taula.

**La regla correcta, en una línia:**

| Si la migració llegeix… | Inici de l'interval |
|---|---|
| **`ModelGradingRule.talla_break_label` / `GradingRule.talla_break_label`** (la BD) | **la MATEIXA etiqueta, sense desplaçar** |
| l'etiqueta que el tècnic veu a la pantalla (convenció de document) | **la SEGÜENT** — o, millor, passar-la abans per `aMotor()` i caure al cas de dalt |

🔒 **I el corol·lari que això obre per a la forma nova:** si els intervals es desen en **espai de
motor** (com el break d'avui), la volta `aDocument`/`aMotor` s'ha de fer **N vegades** a cada
superfície. Si es desen en **espai de document**, cal traduir-los a l'entrada del motor. **La
decisió no s'ha pres i és de les que fan mal en silenci** — `breakConvention.js:18` ja avisa que
*«una superfície que en faci servir només una menteix»*, i amb N intervals és N vegades.

**Frontera que s'agreuja:** el motor resol per etiqueta contra `run_sistema`, però la UI ofereix
`opcionsDocument(data.size_run)` — el run del **MODEL** (`GraduacioSuperficie.jsx:385`). Un
interval que acaba a `3XL` (que el sistema té i el model no) **no és triable a la pantalla**.
Amb un break és una asimetria; amb intervals `[X..última del sistema]` és **la forma canònica de
la migració**, i per tant **cada regla migrada quedaria amb un final d'interval que la seva
pròpia UI no sap oferir**. 🚩 **Decisió pendent d'Agus.**

### 4.5 · Superfícies del multi-break — cens re-ancorat a `dev`

| # | Superfície | Àncora **dev** | Mostra | Edita | Canvi amb intervals |
|---|---|---|---|---|---|
| 1 | **Jocs de regles** (catàleg) | `JocsDeRegles.jsx:302-303` (lectura) · **`:769-830`** (edició) · desa a `:503-515` | ✔ | ✔ | **Mitjà** — 4 columnes fixes → N |
| 2 | **Graduació** (editable) | `GraduacioSuperficie.jsx:361-385` · payload **`:222-226`** · `esLinearDegenerada` **`:105-110`** | ✔ | ✔ | **Mitjà-alt** — el payload va **per presència de clau**; amb intervals ha d'enviar **la llista sencera** |
| 3 | **Mesures — consulta** | `EditableTable.jsx:59-77` (`AMPLADES` + `COLS_GRADING`) | ✔ | ✘ | **Baix** — 4 columnes declarades en un sol lloc |
| 4 | **`CheckMeasureEditor`** | `CheckMeasureEditor.jsx:151-230` | ✔ | ✔ | **Mitjà** |
| 5 | **Escalat** (`escalatRuleLeadCols`) | `fittingGridAdapter.jsx:421-450` | ✔ | règim | **Mitjà** — `width: 54` per columna, carril sticky |
| 6 | **Graella de fitting** | — | **✘ RETIRADA** | ✘ | 🔑 **G5 (bloc 3+D): la columna RÈGIM ja no hi és** — ni a la sessió VIVA (`measureSources.jsx`) ni a la SEGELLADA (`FittingDetail.jsx`). **L'interval NO hi apareixerà, i és correcte**: «en mode sessió els deltes s'editen a Escalat, no en presa». `regimeLeadCol` (`fittingGridAdapter.jsx:289`) **es queda sencer i exportat** |
| 7 | **Fitxa Q8b** | `taulesQ8.js:202-227` + `TechSheetEditor.jsx:5404-5457`; ample a **`:5416`** (`16+wPom+18+14+14+18`) | ✔ | ✘ | **Mitjà-alt** — l'ample està calculat amb **sis columnes fixes** i es reparteix en bandes per no passar l'A4; cada interval menja ample de talles. **Mai A3** |
| 8 | **`gravar_pom_view`** | `models_app/views.py:2550-2558` | — | ✔ | Mitjà |
| 9 | **`set_pom_regim_view`** | `models_app/views.py:5202-5217` · resposta `:5250-5254` | — | ✔ | Mitjà |
| 10 | **Serialització del joc** | `pom/serializers.py:294-303` | ✔ | ✔ | Baix |
| 11 | **Payload `taula-mesures`** | `models_app/views.py:2141-2144` | ✔ | — | Baix — **el punt d'entrada de 5 de les 7 superfícies visuals** |
| 12 | **Federació** | `tenants/federation_service.py:735-747` · **`:899-903`** | — | ✔ | 🚨 **contracte entre cases**: una casa amb intervals i l'altra sense **perd els intervals en silenci** |
| 13 | **Import / detecció** | `pom/grading_utils.py:413-462` · `pom/size_map_views.py:328, 355, 563, 594, 1001` | — | ✔ | Mitjà |
| 14 | **Wizard — preview** | `pom/wizard_views.py:625-628` | ✔ | — | Baix |
| 15 | **CSV d'export** | `pom/s8_views.py:82, 147` | ✔ | — | 🚨 **avui ni tan sols mostra el break** (§1.6·#5) |
| 16 | **Size Set** | `SizeSetDetail.jsx:63` | — | ✔ | 🚨 **escriu només el llegat** (§1.5·#13) |

**La fila expandible del signe `+`** (Mesures i «generar regles»):

Les dues taules on hauria de viure tenen **amplades fixes declarades**:

```js
// frontend/src/components/EditableTable/EditableTable.jsx:59-62
export const AMPLADES = {
  capa: 104, codi: 90, nom: 236, base: 100,
  regim: 96, delta: 84, delta_break: 96, talla_break: 96,
}
```

i les 4 columnes es declaren un sol cop a `COLS_GRADING` (`:66-77`) **a posta**: *«afegir-ne o
treure'n una no vulgui dir tocar dos llocs i que ballin»*. `escalatRuleLeadCols`
(`fittingGridAdapter.jsx:421-450`) fa el mateix amb `width: 54`.

→ **N intervals no caben en columnes.** Cal **fila expandible** (una `<tr>` filla per interval)
o un editor en calaix. **`COLS_GRADING` i `escalatRuleLeadCols` són els dos punts únics on
entra**, i el fet que ja siguin punts únics és el que fa el cost **mitjà i no alt**.

### 4.6 · E — REGLA STEP SENSE VALORS

**Comportament actual, exacte, re-ancorat:**

```python
# backend/fhort/pom/services.py:1186   — la branca canònica NO agafa STEP
if grading_type != 'STEP' and getattr(rule, 'increment_base', None) is not None: ...

# backend/fhort/pom/services.py:1200-1207
elif grading_type == 'STEP':
    vs = rule.valors_step
    if not isinstance(vs, dict) or not vs:
        _add_warning(warnings, f"Regla STEP del POM {pom_codi}: valors_step buit o invàlid; "
                               "cap cel·la calculada.")
        return None, 'STEP'
```

`generate_graded_specs:301-303` recull el `None` amb un `continue`. → **cap `GradedSpec`, cap
cel·la, la fila desapareix.** El POM **no entra a `sense_regla`** (en té, de regla), o sigui que
**tampoc surt a l'avís de cobertura parcial** (`:334-339`). El senyal viu **només** a `warnings`.
Si el POM és l'únic del model, la propagació peta amb `ValueError` (`:322-331`).

**A l'edició:** `set_pom_regim_view:5224-5225` sembra des dels specs vigents, i
`_sembra_step_des_dels_specs` (`views.py:5073-5117`) **retorna `{}`** si el model no té
`GradingVersion` vigent (`:5100-5102`), si no hi ha specs (`:5111-5112`) o si la geometria és
incompleta (`:5114-5116`). → **el forat: un model que encara no ha propagat mai.**

**🚩 CENS A STAGING: el cas NO ÉS REPRODUÏBLE AQUÍ.**

| Schema · taula | STEP | **STEP sense `valors_step`** |
|---|---:|---:|
| `fhort`.ModelGradingRule | 24 | **0** |
| `fhort`.GradingRule | 0 | 0 |
| `los`.* | 0 | 0 |

A PROD n'hi ha **1** (`MGR#82`, model `LOS-SS26-0001`, POM `S.R6`). **A staging, cap.** El sprint
E necessita **fixture propi**; ni el banc §0 ni el corpus de staging el veuran.

**On s'implementaria «valor base a totes les talles, en vermell + avís»:**

| Capa | Node | Cost / risc |
|---|---|---|
| **Motor** (que la branca STEP emeti `base_val`) | `pom/services.py:1200-1207` | 🚨 **ALT · zona intocable** + **xoca de cara amb la llei D2 de cel·la absent** (`:270-284`), que existeix precisament perquè el motor **no fabriqui** un FIXED que sembli graduació (el model 163: 225 specs 100% FIXED amb 200 OK) |
| **Alternativa sense tocar el motor** | `models_app/views.py:5224-5225` — sembrar `valors_step` amb **zeros** quan la sembra des dels specs torni buida | **BAIX**, i la corba plana és exactament la demanada. **Però la marca es queda sense lloc** |

**On viu la MARCA — 🔒 `GradedSpec` NO té camp d'origen.** Verificat sobre `dev`,
`fitting/models.py:209-255`: `grading_version` · `pom` · `size_label` · `graded_value_cm` ·
**`grading_type_applied`** · `increment_applied_cm` · `is_active` · `generated_from_version` ·
`capa` · `instancia` · `garment`. **L'únic camp semàntic és `grading_type_applied`**
(`STEP`/`LINEAR`/`FIXED`/`ZERO`/`EXCEPTION`).

**Alternatives censades — CAP DECISIÓ:**

| | Alternativa | Cost | Radi |
|---|---|---|---|
| **(a)** | Nova opció a `GRADING_TYPE_CHOICES` (p. ex. `STEP_PENDENT`) | migració de choices + **tots** els lectors de `grading_type_applied`: `fitting/graded_spec_views.py:143`, `frontend/src/utils/cellaEscalat.js`, Q8 | **el més ample** |
| **(b)** | Camp nou a `GradedSpec` | migració + **trenca la llei «GradedSpec no té origen»** | ample i **canvia una llei** |
| **(c)** | **Derivar-ho al LECTOR** | **zero dades.** La marca no és de l'spec sinó **de la REGLA** (`logica=='STEP'` i `valors_step` buit/tot-zero), i **`taula-mesures` ja serveix `logica`** (`models_app/views.py:2141`) | **el més estret** |
| **(d)** | `Watchpoint` per POM | `models_app.Watchpoint`, ja usat a `models_app/views.py:3115-3124` | mitjà; és el mecanisme d'avís que ja existeix |

⚠️ **El cost seriós no és la marca, és el SIZE SET.** `create_piece_fitting`
(`fitting/services.py:530-538`) clona cada spec en una `PieceFittingLine` amb
`valor_teoric = valor_real = graded_value_cm`. Amb la proposta, la presa **naixeria amb el valor
base repetit a totes les talles com a TEÒRICA**: (1) `Dif = 0` a totes → la Q8c diria «va arribar
clavada» a tot arreu; (2) `linia_te_contingut` (`fitting/esdeveniments.py:28`) i el Repàs canvien
de resposta; (3) `consolidate_base_from_fitting` només consolida la base → **no contamina
`BaseMeasurement`**, però la teòrica falsa **sí que arriba al PDF de la fitxa**. 🚩 **Decisió
d'Agus, i és la que mana sobre tota la resta d'aquest apartat.**

**UI (vermell + avís):** `frontend/src/utils/cellaEscalat.js` (cel·la d'escalat) ·
`EditableTable.jsx:1423` (regla en lectura) · `GraduacioSuperficie.jsx:361-385`.
**Tokens obligatoris (llei G8):** `--err`/`--err-bg` o `--warn-state`/`--warn-state-bg`/
`--warn-ink`. **Mai hex.** i18n × 3.

---

<a id="contra"></a>
## CONTRADICCIONS

### Amb `DIAGNOSI_BUGS_PROD_837_2026-08-21.md`

| # | On deia | Què és realment (mesurat a `dev` / staging) |
|---|---|---|
| **1** | §A.5·1 — el fallback del llegat és `pom/services.py:1197-1198` | 🚨 **N'HI HA DOS.** El segon és `grading_utils.py:1016-1019` dins `increment_de_l_aresta`, i el travessen la **presa** (`fitting/views.py:722`) i la **derivació de base** (`models_app/views.py:3459`) via `propaga_ancoratges`, que **no té el guard `ib is not None` a sobre**. Tocar-ne un i no l'altre fa divergir Escalat de la presa |
| **2** | §H.4 — *«`base-measurements/` no serveix `garment`… el mateix motiu que `taulesQ8.js:16-18` dona per no fer servir `graded-table/`»* | 🚨 **DOBLEMENT FALS.** (i) `taulesQ8.js:16-18` parla de **`graded-table/`**, no de `base-measurements/`; (ii) `base-measurements/` **SÍ serveix `garment`** des de SET-2/F1 (`models_app/serializers.py:476`). El que **no** serveix és **tolerància** — i això sí que treu la columna `Tol±` del naixement |
| **3** | §H.2 — el cos citat de `insertTableBaseMeasures` (5 columnes: `ref`·`pom`·`base`·`tol`·`coment`) | ⚠️ **és la versió del NAIXEMENT** (`38a0761e`). **La que es va retirar en tenia 3** (`ref`·`pom`·`base`), amb capçalera de `ref` buida, títol de `base` amb la talla interpolada, `tDoc` en comptes de `t`, i `garmentId: GARMENT_MARE` ja present |
| **4** | §A.5·1 — *«137 de 1332 LINEAR actives amb `increment != increment_base`»* | ⚠️ **és PROD-`fhort`.** A staging: **14 de 335**, i **les 14 són del model 1383 i totes `MANUAL`**. `los` en té **0** perquè **no té cap `ModelGradingRule`**. Les guardes del backfill han de ser **per entorn i per schema** |
| **5** | §A.5 — cens d'escriptors de règim | ⚠️ **incomplet en el sentit contrari.** Hi ha **4 escriptors que poblen NOMÉS el llegat**, cap censat: `s4_views.py:78-85` (viu, el crida `SizeSetDetail.jsx:63`), `s2_views.py:323-326`, `s4_views.py:303-307`, i **`s2_views.py:230-238`, que en clonar un perfil PERD `increment_base`/`increment_break`/`talla_break_label`/`_pos`** |
| **6** | §F.2·6 — «Graella de fitting: mostra ✔» | ✅ **ja no.** G5 del bloc 3+D li va treure la columna RÈGIM a les **dues** superfícies (viva i segellada). El cens F queda superat en aquest punt |
| **7** | §F.3 «Paritat QA — a `fhort` de PROD no hi ha banc; **BLOQUEJANT**» | ✅ **desbloquejat**: el banc existeix a staging (model 1383) i **corre verd avui** (§0). 🚩 Segueix sense existir **a PROD** |
| **8** | §E.1 — «cas viu a PROD: `MGR#82`, l'única STEP sense valors» | 🚩 **a staging n'hi ha ZERO.** El sprint E no té corpus aquí: **cal fixture** |
| **9** | §A.5·5 — `talla_break_pos` és columna morta | ✅ **confirmat, i amb un tercer actor:** `set_pom_regim_view:5216-5217` la calcula contra `model.size_run_model`, `gravar_pom_view:2558` amb `_break_pos`, i el motor no la llegeix mai (`grading_utils.py:992-1004` resol per etiqueta contra `run_sistema`) |
| **10** | §F.2 — 12 superfícies | ⚠️ **en són 16**: hi falten el CSV d'export (`s8_views.py:82,147`), Size Set (`SizeSetDetail.jsx:63`), el payload de `taula-mesures` (`views.py:2141-2144` — **el punt d'entrada de 5 de les 7 superfícies visuals**) i `grading_rules_match` (`grading_utils.py:68-118`, sense cridador viu) |

### Amb l'ordre d'aquesta sessió

| # | On deia | Què és realment |
|---|---|---|
| **11** | *«migració 1-break → interval X→última talla del SIZESYSTEM **amb l'off-by-one traduït**: l'etiqueta vella marca l'ÚLTIMA talla del delta petit → inici de l'interval = la SEGÜENT»* | 🚨 **desplaça 33 de 105 cel·les del banc.** L'off-by-one és de la convenció de **DOCUMENT**; la BD ja desa la **PRIMERA talla del tram gran**. Amb **l'etiqueta sense desplaçar**, l'equivalència és **105/105 exacta** (§4.3-4.4). El desplaçament només s'aplica si la migració llegeix l'etiqueta **de la pantalla** |
| **12** | *«Rellegeix la decisió MULTI-BREAK v2 (DECISIONS.md)»* | 🚩 **no hi és.** `DECISIONS.md` porta S24/S10 sobre el break **únic** (`:714-721`) i cap entrada d'intervals. La decisió viu **només a l'ordre**. **Cal baixar-la a `DECISIONS.md`** o el proper que la busqui no la trobarà |
| **13** | *«Les 142 del 1383 (quantes divergeixen? el D segur)»* | **14 divergeixen** amb el criteri del backfill (LINEAR amb `ib` poblat). En SQL cru en surten **53**, però les altres **39 són FIXED amb `ib=NULL`** i **no entren al backfill**: `_apply_rule:1186` no els agafa la branca canònica |
| **14** | *«"Tornar a consulta" … és la meitat del gating G1 ja construïda?»* | ❌ **no.** És literalment `onClick={exitEdit}` (`ModelSheet.jsx:1257`, `:1404`), el mateix handler de qualsevol sortida i sense cap predicat propi. **És el GALLET del modal, no mitja porta.** El que sí que hi ha construït —i és molt més— és **`batec_escriptura`**, el senyal «hi ha hagut escriptura» que la meritació SaaS ja fa servir per a la mateixa distinció (§2.3) |
| **15** | *«handoff federació (PAUSADA CONSERVA LA MÀ — el tram J no pot alliberar la mà per una consulta)»* | ⚠️ **el perill real és més gran i va en l'altre sentit**: `open-task` sobre una tasca `InProgress` **d'un altre** dispara `traspassa_tram` + `task.assignee = profile` (`views_b.py:597-611`). **Una consulta no allibera la mà: l'ENDÚ.** I `transition_task` publica `sync_estat` a la casa bessona **dues vegades** per consulta (`services_c.py:352-357`) |
| **16** | §2 · *«el modal … si es descarta el temps sense escriptura, per on es descarta (… llindar?)»* | ⚠️ **el llindar està vetat per una decisió ja presa.** `ModelSheet.jsx:590-592`: *«EL CRITERI NO ÉS LA DURADA … una sessió de dos minuts amb la tasca oberta ensenya el modal igual que una de dues hores (decisió d'Agus)»* |

---

## ARTEFACTES D'AQUESTA SESSIÓ

| Fitxer | Què és | Estat git |
|---|---|---|
| `docs/ordres/banc_paritat_1383.py` | **EL GATE** de paritat dels sprints de motor | **untracked** — entra al repo al sprint del fix A |
| `docs/ordres/equiv_intervals_1383.py` | Prova d'equivalència 1-break → intervals + contra-experiment de l'off-by-one | **untracked** |
| `docs/ordres/DIAGNOSI_PRE_SPRINTS_STAGING_2026-08-21.md` | aquest document | **untracked** |

**Escriptures a staging aquesta sessió: CAP.** Totes les lectures de BD amb
`PGOPTIONS='-c default_transaction_read_only=on'`. Cap `git add`, cap commit, cap `npm run build`,
cap `systemctl restart`.
