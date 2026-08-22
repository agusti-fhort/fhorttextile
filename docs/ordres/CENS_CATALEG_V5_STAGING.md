# CENS CATÀLEG v5 · STAGING — **FASE 1 (CODI)**

**Data:** 2026-08-22 · **Entorn:** `/var/www/ftt-staging`, branca `dev`, schemes `fhort` + `public`
**Patró A · READ-ONLY** · Venv: `backend/venv/bin/python`

> **BARANA PROVADA ABANS DE COMENÇAR.** Tota consulta va amb
> `PGOPTIONS='-c default_transaction_read_only=on'`, i la barana s'ha verificat amb una
> escriptura que **havia de petar**:
> ```
> llegir SÍ: pk=57 codi='A'
> ✅ BARANA VIVA — InternalError: cannot execute UPDATE in a read-only transaction
> ```
> Cap escriptura · cap `manage.py shell` que escrigui · cap command · cap migració · cap
> restart · cap push · cap fitxer del repo tocat fora de `docs/ordres/`.

---

# 🛑 ATURADA REGLAMENTÀRIA — LA PREMISSA DE C7 HA CANVIAT

El brief diu: *«Tota la forma del pla penja d'aquesta frase: si ha canviat, PARA i reporta abans
de fer res més.»* **Ha canviat el 2026-08-12** (SET-2/PRED-3). La Fase 2 i la Fase 3 **no s'han
executat**. El que segueix és la Fase 1 sencera.

---

## PREMISSES QUE NO ES CONFIRMEN (al davant, com mana el brief)

### ① C7 — «all-or-nothing» segueix sent cert, però **el SUBJECTE del predicat ha canviat**

No és *«si un model té residents»*: és **«si LA PEÇA MARE en té»**. I hi ha **un cas de
convivència** que abans era impossible.

### ② 🚨 CORRECCIÓ D'UN CENS PROPI D'AHIR (`CENS_FAMILIES_POM_2026-08-22.md`)

Ahir vaig escriure que `bootstrap_tenant` copia `POMCategory` **de `public`** i que per tant *«un
tenant nou neix amb les 15 categories de sector en anglès»*. **És FALS.** L'argument és
`--from`, i el seu **default és `fhort`** (`bootstrap_tenant.py:196`), no `public`:

```python
parser.add_argument('--from', dest='source', type=str, default='fhort',
                    help='Schema del tenant origen (default: fhort).')
```

O sigui que **un tenant nou hereta les 25 famílies de LLETRA de `fhort`**, no les 15 de sector.
La conclusió del cens d'ahir sobre «dos vocabularis incompatibles» **es manté** (segueixen sent
dos i no es parlen), però la frase sobre què rep un tenant nou era equivocada i s'ha de corregir
allà. Ho anoto aquí i **no toco aquell fitxer** (fora de `docs/ordres/`, i el brief ho prohibeix).

### ③ El paquet LOSAN **no transporta `breaks`** (els intervals del TRAM F)

`grep -c breaks` = **0** a `export_losan_package.py` **i** a `load_losan_package.py`. El camp
existeix a `GradingRule` des de la migració `0077` i, des del 21/08, **és el punt únic del
relleu**. Un cicle export→load **perd els intervals en silenci** (i també `talla_break_pos`, que
tampoc és als `defaults` de `_load_rules`). No és el que el brief preguntava; surt del C6 i
s'anota.

---

# C7 · `_load_grading_rules` — ÉS ALL-OR-NOTHING, PERÒ DE LA **MARE**

**Fitxer:** `backend/fhort/pom/services.py`
**La decisió és a `_load_grading_rules_per_garment`, línies 929-948** (`_load_grading_rules`,
828-879, només n'és una VISTA: filtra `garment == ''`).

```python
929    from fhort.models_app.models import ModelGradingRule
930    rules = ModelGradingRule.objects.filter(model_id=model.id, actiu=True)
931    out = {(r.pom_id, r.garment): r for r in rules}
932    # El subjecte del predicat: LA MARE, no el model. Es llegeix del `out` ja materialitzat
933    # per no fer una segona consulta que pogués divergir de la primera.
934    te_residents_la_mare = any(garment == '' for (_pom_id, garment) in out)
935    if not te_residents_la_mare and model.grading_rule_set_id:
936        from fhort.pom.models import GradingRule
...
945        out.update({(r.pom_id, ''): r for r in GradingRule.objects.filter(
946            rule_set_id=model.grading_rule_set_id, actiu=True
947        )})
948    return out
```

I la vista pública (828-879):

```python
877    return {pom_id: regla
878            for (pom_id, garment), regla in _load_grading_rules_per_garment(model).items()
879            if garment == ''}
```

## La resposta, en tres frases

1. **SÍ, és all-or-nothing, i per MODEL — mai per POM.** Si la peça mare té **una sola**
   `ModelGradingRule` activa, el contenidor compartit **no es llegeix gens**. Els POMs que les
   residents no cobreixin cauen a `rule is None` → **llei de cel·la absent: cap cel·la emesa**.
   No hi ha barreja per POM enlloc.

2. **El SUBJECTE ha canviat el 12/08 (SET-2/PRED-3).** Abans el predicat era `rules.exists()`
   —*té residents el MODEL?*—; ara és `te_residents_la_mare` —*en té la PEÇA MARE?*—. La
   docstring (906-927) ho documenta i diu per què: amb `rules.exists()`, un model amb residents
   **només a una filla** (p. ex. la `02`) feia que el contenidor no es llegís mai i **la mare es
   quedava sense graduació sencera**.

3. **I ara hi ha CONVIVÈNCIA**, que abans era impossible: `out.update(...)` i no `return`
   (941-947, i el comentari ho subratlla). Amb **filla amb residents + mare sense**, el
   contenidor entra com a llei de la mare **i les residents de la filla es queden**. Les dues
   branques ja **no s'exclouen**.

## La taula d'estats (el que el pla ha de mirar)

| Mare té residents | Filla té residents | Contenidor (`model.grading_rule_set`) | Qui governa |
|---|---|---|---|
| **Sí** | — | **IGNORAT del tot** | només residents; POM no cobert → **cap cel·la** |
| No | No | **LLEGIT** | contenidor, com a llei de la mare |
| **No** | **Sí** | **LLEGIT** *(cas nou, 12/08)* | contenidor a la mare **+** residents a la filla |

⚠️ **Matís operatiu que el pla ha de tenir en compte:** amb les comportes `*_garment_gate_set2`
vives, `garment` és `''` a **tot** el corpus, i llavors `te_residents_la_mare == rules.exists()`
— *«comportament idèntic, byte a byte, per al 100% del corpus d'avui»* (docstring, 925-927). O
sigui: **el canvi de subjecte encara no és observable a les dades d'staging**, però ja és al codi
i s'activarà el dia que caigui una comporta. **Confirmar-ho contra les dades és Fase 2, i no
s'ha executat.**

## Una segona cosa que el pla hauria de saber d'aquesta funció

`_load_grading_rules` (la de clau `pom_id` pelat) **té sis consumidors fora del motor** i la seva
docstring (829-875) els llista amb fitxer i línia, amb l'acta de quan canviar-li el contracte els
va trencar tots sis **en silenci**. Cinc llegeixen la llei de la mare **a posta** (pinten rètols);
un —`fitting/views.py`, la propagació— ja està adaptat a l'eix perquè **escriu**.

---

# C6 · CENS D'ESCRIPTORS-CREADORS (llei S45)

Tot node que **CREA o fa UPSERT** dels sis models. Els LECTORS (`filter`, `get`, mapes per
`codi`) **no hi són**, com demana el brief.

## ▸ Els cinc obligatoris

### 1. `pom/management/commands/load_losan_package.py`

Motor genèric `_upsert(model, lookup, defaults)` (86-107): crea si falta; si existeix,
**assigna camp a camp i desa només si algun ha canviat**. Mai `delete`.

| Model | Línia | Lookup | Camps que reescriuria |
|---|---|---|---|
| `POMGlobal` | 242 | `{'codi'}` | **tots** els del JSON menys `codi` i `body_measure_iso` |
| `POMMaster` | 282 / 284 | `{'pk'}` (via `_resolve_pom`) · si no, `{'pom_global__codi','codi_client'}` · si no, **create** | `pom_global`, `codi_client`, `nom_client`, `categoria`, `notes`, `actiu`, `pendent_revisio`, `origen_import`, `tolerancia_default_minus/plus` |
| `CustomerPOMAlias` | 302 | `{'customer','client_code'}` | `pom`, `client_description`, `description_en`, `description_local`, `language`, `origen`, `pendent_revisio` |
| `GradingRuleSet` | 444 | `{'nom'}` | `origen`, `actiu`, `customer`, `size_system`, `garment_group`, `garment_type_item`, `construction`, `fit_type`, `target`, `version_number`, `codi_sistema`, `pendents_vincular` + **M2M `targets` (`.set()`)** |
| `GradingRule` | 475 | `{'rule_set','pom'}` | `talla_base`, `logica`, `increment`, `valors_step`, `increment_base`, `increment_break`, `talla_break_label`, `actiu` — **🚩 `breaks` i `talla_break_pos` NO hi són** |
| `POMCategory` | — | **no l'escriu** (només el llegeix, :251, per `codi`) | — |

🔒 Porta el **pany de sobirania** (22/08): un `POMMaster` amb `separat_de_global` es **reporta i
no es toca**.

### 2. `pom/management/commands/extend_pom_catalog.py`

| Model | Línia | Lookup | Camps que reescriuria |
|---|---|---|---|
| `POMGlobal` | 181 | `{'codi'}` · **a `public` I al tenant** | `nom_en`, `nom_ca`, `nom_es`, `categoria`, `descripcio_en/ca`, `unitat`, `actiu`, `abbreviation`, `start_point`, `end_point`, `reference_point`, `scope`, `orientation`, `state`, `line`, `body_section`, `is_key`, `tol_prod_cm`, `tol_samp_cm`, `applies_woven/knit/swim`, `notes`, `iso_ref` |
| `POMMaster` | 213 | **`{'pom_global'}`** | `codi_client`, `nom_client`, `actiu`, `categoria`, `notes` |

🔒 Porta el **pany de sobirania** (22/08): busca `separat_de_global=pg.codi` i **salta i reporta**.
🚩 El lookup per **FK** (`pom_global=pg`), no per clau natural, és l'excepció del cens.

### 3. `tasks/management/commands/bootstrap_tenant.py` — v. **C8-codi**

### 4. `pom/management/commands/reseed_tenant_fhort.py` — ☠️ **MORT**

`handle()` **avorta a la primera línia** (`:86`, `CommandError`) amb el guard OBSOLET del bloc 4c:
usa l'eix `garment_type` de `GarmentPOMMap`, **eliminat a la migració `pom/0016`**, i abans de
petar faria `DELETE`s destructius. **No pot escriure res.** El codi mort que hi ha a sota
escriuria: `POMMaster` (bulk_create: `pom_global`, `codi_client=pg.abbreviation or pg.codi`,
`nom_client=pg.nom_en`, `actiu`, `categoria`, `notes`) · `GradingRuleSet` (create: `nom`,
`codi_sistema`, `target`, `construction`, `fit_type`, `size_system`, `is_system_default`,
`version_number`, `actiu`, `origen=CANONICAL`) · `GradingRule` (bulk_create amb
`ignore_conflicts=True`: `rule_set`, `pom`, `talla_base`, `logica`, `increment`,
`increment_base`, `valors_step`, `actiu`).

### 5. `pom/management/commands/seed_baby_months_grading.py`

| Model | Línia | Lookup | Camps que reescriuria |
|---|---|---|---|
| `GradingRuleSet` | 84 | `{'nom','size_system'}` | `actiu`, `version_number=1`, `origen=CANONICAL` |
| `GradingRule` | 99 | `{'rule_set','pom'}` | `logica`, `increment_base`, `increment` *(mirall del llegat)*, `talla_base`, `actiu` |

## ▸ La resta d'escriptors-creadors trobats

| Fitxer | Model | Línia | Lookup |
|---|---|---|---|
| `sembra_cataleg_v4.py` | `POMCategory` | 105 | **create** `codi=familia`, `nom_ca=seccio` |
| | `POMMaster` | 114 | **create** `codi_client`, `nom_client`, `categoria`, `pom_global=None`, `actiu`, `pendent_revisio`, `notes` |
| | `CustomerPOMAlias` | 163 | **create** |
| | `GradingRule` | 187 | **create** |
| `replace_pom_catalog.py` | `POMCategory` | 758 | `{'codi'}` → `nom_en`, `nom_ca`, `display_order`, `descripcio`, `actiu` |
| | `POMGlobal` | 777/805 | **`delete()` de tots + `bulk_create`** ⚠️ destructiu |
| `seed_brownie_cataleg.py` | `POMMaster` | 135 | `get_or_create` |
| | `CustomerPOMAlias` | 181 | `update_or_create` |
| `seed_brownie_germans.py` | `CustomerPOMAlias` | 125 | `update_or_create` |
| `seed_brownie_ruleset.py` | `GradingRuleSet` | 131 | `update_or_create` |
| | `GradingRule` | 157 | `update_or_create` |
| `seed_master_delta_catalog.py` | `CustomerPOMAlias` | 71 / 91 | `get_or_create` |
| | `POMMaster` | 78 | `get_or_create` |
| | `POMGlobal` | 83 | **create** |
| `seed_losan_master_delta.py` | `GradingRuleSet` | 154 | `get_or_create` |
| | `GradingRule` | 179 | `get_or_create` |
| `seed_losan_ss27.py` | `GradingRuleSet` | 154 | `get_or_create` |
| `seed_losan_grading_v3.py` | `GradingRuleSet` | 161 | `update_or_create` |
| | `GradingRule` | 187 | `update_or_create` |
| `seed_losan_rules.py` | `GradingRule` | 151 | `update_or_create` |
| `seed_losan_rules_v2.py` | `GradingRule` | 155 | `{'rule_set','pom'}` |
| `seed_baby_poms.py` | `POMGlobal` | 253 | `update_or_create` |
| | `POMMaster` | 260 | `update_or_create` |
| `consolidate_pom_catalog.py` | `POMGlobal` | 156 / 238 | `get_or_create` / **create** `LOSPOM-{pom.id}` |
| | `POMMaster` | 236 | **create** |
| | `CustomerPOMAlias` | 241 | `get_or_create` |
| `models_app/…/sembra_model_837.py` | `ModelGradingRule` | 676/684 | `bulk_create` *(resident, no de catàleg)* |
| **MIGRACIONS** | `CustomerPOMAlias` | `0031:53`, `0032:58` | **create** (dades, no esquema) |

🔴 **Escriptors per API** (fora de l'abast literal del brief però del mateix vocabulari):
`POST /api/v1/onboarding/setup-from-excel/` (`pom/s9_views.py:162`, **només `IsAuthenticated`**)
fa `update_or_create` de `POMCategory` per `{'codi'}` sobre `nom_en`, `nom_ca`, `display_order`.

---

# C8-codi · `bootstrap_tenant` i `POMCategory`

**D'ON:** del schema `--from`, **default `fhort`** (`:196`) — **no `public`**.
**QUAN:** bloc `base` de `SEED_BLOCKS` (`:57`), amb `--profile` o sense (sense perfil, tot).
**LOOKUP:** clau natural **`('codi',)`** (`:142`).

```python
142        (POMCategory,        ('codi',), {}, (), None),
```

**QUÈ COPIA:** `_concrete()` (`:211-213`) = **tots els camps del model menys la pk** →
`codi`, `nom_en`, `nom_ca`, `descripcio`, `body_area`, `display_order`, `actiu`.
Sense FK a resoldre, sense M2M, sense transform.

**COM ESCRIU** (`:341-356`), i són **dos comportaments segons `--additive`**:

| Mode | Destí buit | Destí amb 1 fila | Destí amb ≥2 files |
|---|---|---|---|
| **sense `--additive`** | `create` | **`update_or_create` → SOBREESCRIU** els 6 camps | idem sobre la que retorni el planner |
| **`--additive`** | `create` | **SALTA intacte** (`skipped_existents`) | SALTA i **reporta com a AMBIGU** |

🚩 **Conseqüència que el pla ha de saber:** `bootstrap_tenant <destí>` **sense `--additive`**
reescriu les etiquetes i l'ordre de les famílies que ja hi hagi al destí amb les de `fhort`. La
llei del destí poblat (`--additive`) existeix precisament per això.

---

# ESTAT DE LES FASES

| Fase | Estat |
|---|---|
| **1 · CODI** (C7 · C6 · C8-codi) | ✅ **feta — aquest document** |
| **2 · DADES** (C1–C5, C8-dades) | ⏸️ **NO EXECUTADA** — aturada per C7 |
| **3 · EMPREMTA** (C9-staging) | ⏸️ **NO EXECUTADA** — aturada per C7 |

🚩 **Contradicció del brief, per decidir:** la capçalera prohibeix *«tocar cap fitxer del repo
fora de `docs/ordres/`»* i la Fase 3 demana *«deixar-ho com a SCRIPT REUTILITZABLE a `ops/`»*.
Quan es reprengui, cal dir on va l'script.

**Cap reparació proposada. Les decisions són d'Agus.**
