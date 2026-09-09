# B3 · `ModelGradingRule` — el canvi de clau a `('model','element','pom')`

**Mode:** lectura pura. Cap escriptura, cap migració, cap `manage.py migrate`.
**Data:** 2026-08-07 · **Repo:** `/var/www/ftt-staging/backend` (branca `HEAD`, worktree net)
**Mètode:** `ModelGradingRule._meta.related_objects` via `manage.py shell` + grep ample pel nom del
model (`ModelGradingRule`), pel `related_name` (`grading_rules`, `model_grading_rules`) i pel nom
físic de la taula (`models_app_modelgradingrule`). **No** s'ha fet servir `information_schema` per
baixar per les FK (les dues FK d'aquesta taula tenen `db_constraint=False` i no hi surten).

---

## 0 · Nota prèvia que condiciona tot l'informe

**`element` NO existeix avui.** Verificat: cap classe, cap camp i cap `related_name` amb aquest nom a
`fhort/models_app/models.py` ni a `fhort/pom/models.py`. El que hi ha de més proper és
`Model.garment_type_item` (FK, `models.py:202`) i la pertinença a conjunt
(`Model.garment_set` + `Model.piece_number`, `models.py:211-221`), que és **una peça = un Model
sencer**, no un element dins d'un model. Per tant tot l'apartat 4 descriu l'impacte d'una entitat
que encara no té definició; on la resposta depèn de com es defineixi (nullable?, `on_delete`?,
`element` per defecte?) queda dit explícitament a §7.

---

## 1 · Definició LITERAL del model

**Fitxer:** `/var/www/ftt-staging/backend/fhort/models_app/models.py` · **línies 994-1100**

```python
994  class ModelGradingRule(models.Model):
995      """PG-0 — Graduació canònica RESIDENT al model (una regla per (model, POM)).
996
997      Materialitza dins el tenant la mateixa forma canònica que pom.GradingRule, però
998      penjant del Model en lloc d'un GradingRuleSet compartit extern. NO duplica la base
999      (viu a BaseMeasurement) ni la config de run (model.size_run_model /
1000     model.base_size_label ja la porten): el break es resol per ETIQUETA contra el run
1001     del model, igual que fa _apply_rule avui.
1002
1003     PG-0 només crea l'entitat — RES la consumeix encara. Cap canvi de comportament.
1004
1005     ⚠️ **SENSE `capa`, PER DECISIÓ DE DOMINI (C1 · §3c).** Aquesta és l'ÚNICA taula del cicle
1006     de mesura que la capa de C1 no travessa, i no és un oblit. Una regla de graduació és una
1007     llei d'INCREMENTS, no un valor: el folre d'un pit creix el mateix que l'exterior d'aquell
1008     pit —«mateixos deltes»— perquè la peça és la mateixa peça. Donar-li capa voldria dir
1009     demanar a algú que declari sis vegades el mateix delta i mantenir-les sincronitzades a mà.
1010     Els VALORS sí que en porten (`BaseMeasurement`, `GradedSpec`, `ModelGradingOverride`…):
1011     la regla és compartida, el resultat d'aplicar-la és per capa. Qui vulgui revisar-ho: és
1012     decisió d'arquitectura (Patró C), no una peça d'sprint.
1013
1014     ⚠️ **I TAMPOC SENSE `instancia` (C1-ins), pel mateix motiu i amb la mateixa acta.**
1015     Decisió Montse: la sisa dreta i l'esquerra **gradúen igual**. Són dues mesures diferents
1016     —dos valors, dues fletxes al croquis, dues caselles a la fitxa— però una sola llei
1017     d'increments, com ho són l'exterior i el folre. Aquesta taula és, doncs, l'única del
1018     cicle que **no** travessa CAP dels dos eixos, i és a posta a les dues bandes. El pin que
1019     ho vigila: `test_instancia_comporta_cins.py` (columna absent a `information_schema`),
1020     germà del que ja hi ha per a `capa`. El mateix val per a `pom.GradingRule`.
1021     """
1022     # R8 (2026-07-21) — 'CLIENT_RUN' hi faltava. El vocabulari de GradingRuleSet.origen
1023     # (CANONICAL/CLIENT_RUN/IMPORT) i el d'aquí no s'alineaven, i el wizard resolia la
1024     # diferència escrivint sempre 'CANONICAL': 104 regles residents de 4 models deien que
1025     # eren canòniques quan venien d'un run de client (DIAGNOSI_REFACTOR_GRADING_2026-07-21,
1026     # R8). Sense aquest valor, la provinença real no era ni expressable.
1027     ORIGEN_CHOICES = [
1028         ('IMPORTED', 'Importat de fitxa externa'),
1029         ('CANONICAL', 'Derivat canònicament'),
1030         ('CLIENT_RUN', 'Derivat de run de client'),
1031         ('MANUAL', 'Introduït manualment'),
1032         # RETORN-1 — mateixa raó que a BaseMeasurement: la regla resident ve de l'altra casa,
1033         # i cap dels quatre valors anteriors ho sabia dir.
1034         ('FEDERAT', "Arribat de l'altra casa (federació)"),
1035     ]
1036
1037     model = models.ForeignKey(
1038         'models_app.Model', on_delete=models.CASCADE, related_name='grading_rules',
1039     )
1040     # db_constraint=False: 'pom' és app SHARED (taula també a 'public'), però aquest model
1041     # és tenant-only → un constraint de BD cap a pom_pommaster petaria a 'public'. L'FK és
1042     # lògic (ORM). Mateix patró cross-schema que pom.GarmentPOMMap.garment_type_item.
1043     pom = models.ForeignKey(
1044         'pom.POMMaster', on_delete=models.PROTECT, related_name='model_grading_rules',
1045         db_constraint=False,
1046     )
1047
1048     logica = models.CharField(max_length=20, choices=GradingRule.LOGICA_CHOICES)
1049
1050     # Legacy LINEAR/FIXED: _apply_rule té una branca de fallback que llegeix `increment`
1051     # quan increment_base és NULL. Sense aquest camp, una regla no-canònica no graduaria.
1052     increment = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
1053     valors_step = models.JSONField(null=True, blank=True)  # STEP origen/auditoria
1054
1055     # Forma canònica d'aplicació (break ancorat per ETIQUETA, resolt al run del model).
1056     # valors_step roman com a origen/auditoria. NULL = no canònic → fallback a `increment`.
1057     increment_base = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
1058     increment_break = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
1059     talla_break_label = models.CharField(max_length=30, null=True, blank=True)
1060     talla_break_pos = models.IntegerField(null=True, blank=True)  # cache opcional (run del model)
1061
1062     origen = models.CharField(max_length=20, default='CANONICAL', choices=ORIGEN_CHOICES)
1063     # ── M3 (2026-08-07) · LA TRAÇABILITAT: DE QUIN JOC VE AQUESTA FILA ────────────────────────
1064     # L'arrel del parany de la decisió 6.1. `origen` diu «algú hi ha tocat», NO «aquest valor és
1065     # seu»: els dos escriptors de pantalla estampen `MANUAL` encara que la regla sigui una còpia
1066     # literal de la del joc, i `origen_mgr_des_de_ruleset` també estampa `MANUAL` a tot el que
1067     # surt d'un `GradingRuleSet` sense classificar. Amb això, «autoria» i «còpia» es deien igual
1068     # i el wipe només podia INFERIR-HO mirant l'estat del joc ANTERIOR del model sencer.
1069     # Aquest camp ho deixa dit per FILA, i a la font: qui la materialitza sap d'on la treu.
1070     #
1071     #   informat  → la fila VE d'aquest joc (encara que després l'hagin editada a mà).
1072     #   NULL      → no ve de cap joc, o no se sap. Autoria de pantalla des de zero, federació
1073     #               (el joc d'origen viu a l'altra casa i el seu id aquí no vol dir res) i
1074     #               TOTES les files anteriors a M3: **no hi ha backfill, i és a posta** —
1075     #               d'on venien no es pot saber, i inventar-ho seria tornar a mentir.
1076     #
1077     # NO canvia cap política: 6.1 i M1 segueixen decidint com ahir. És senyal, no llei; la
1078     # política que el llegeixi vindrà quan hi hagi dades (v. `poms_manual_a_preservar`).
1079     #
1080     # db_constraint=False i SET_NULL pel mateix motiu que `pom` (sobre): 'pom' és app SHARED
1081     # (taula també a 'public') i aquest model és tenant-only. Esborrar un joc del catàleg no ha
1082     # d'endur-se la regla resident del model —el patrimoni és del model—, només el rastre d'on
1083     # va néixer.
1084     derivat_de_rule_set = models.ForeignKey(
1085         'pom.GradingRuleSet', on_delete=models.SET_NULL, null=True, blank=True,
1086         db_constraint=False, related_name='regles_residents_derivades',
1087         help_text="Joc del qual es va materialitzar aquesta fila. NULL = autoria de pantalla, "
1088                   "federació, o fila anterior a M3 (sense backfill: no es pot saber).",
1089     )
1090     actiu = models.BooleanField(default=True)
1091     created_at = models.DateTimeField(auto_now_add=True)
1092     updated_at = models.DateTimeField(auto_now=True)
1093
1094     class Meta:
1095         verbose_name = 'Regla grading (model)'
1096         verbose_name_plural = 'Regles grading (model)'
1097         unique_together = [('model', 'pom')]
1098
1099     def __str__(self):
1100         return f'{self.model} · {self.pom.codi_client} ({self.logica})'
```

### `_meta` viu (consultat, no llegit del codi)

```
DB TABLE: models_app_modelgradingrule
unique_together: (('model', 'pom'),)
constraints: []            ← CAP CheckConstraint / UniqueConstraint declarat
Meta.indexes: []           ← CAP índex explícit
Meta.ordering:  (absent)   ← aquesta taula NO té ordering (la germana ModelGradingOverride sí)
```

### `on_delete` de cada FK (les tres)

| camp | destí | `on_delete` | `db_constraint` | `related_name` |
|---|---|---|---|---|
| `model` | `models_app.Model` | **CASCADE** | `True` (constraint real a BD) | `grading_rules` |
| `pom` | `pom.POMMaster` | **PROTECT** | **`False`** (FK lògic ORM, cross-schema) | `model_grading_rules` |
| `derivat_de_rule_set` | `pom.GradingRuleSet` | **SET_NULL** | **`False`** (FK lògic ORM, cross-schema) | `regles_residents_derivades` |

### `related_objects` (fills que pengen d'aquesta taula)

```
--- RELATED OBJECTS (fills) ---
(cap)
```

**`ModelGradingRule` no té CAP fill.** Ningú l'apunta amb una FK. El canvi de clau **no** arrossega
cap taula filla — l'única cascada que la toca és `Model → CASCADE`, cap amunt.

---

## 2 · La clau única ACTUAL, exactament

```
unique_together = [('model', 'pom')]
```

A BD: un índex únic sobre `(model_id, pom_id)` de `models_app_modelgradingrule`, per esquema de
tenant. **No hi ha cap altra unicitat, cap `UniqueConstraint`, cap `CheckConstraint` i cap índex
declarat.** La `Meta` d'aquesta classe és tres línies (`verbose_name`, `verbose_name_plural`,
`unique_together`) — vegeu-ho contrastat amb la germana `ModelGradingOverride`
(`models.py:973-989`), que sí que porta clau de 5 (`model, pom, size_label, capa, instancia`),
`ordering` i bloc `constraints`.

**La taula NO existeix a `public`** (app `models_app` és tenant-only) — verificat contra
`pg_stat_user_tables`: present només a `fhort` i `los`.

---

## 3 · Cens COMPLET del que toca aquesta taula

Ordenat per perillositat. `✍️` = escriu · `🗑️` = esborra · `👁️` = només llegeix.

### 3.1 · `poms_manual_a_preservar` — on és i què fa

**`fhort/models_app/services.py:273-303`**

```python
273  def poms_manual_a_preservar(model, joc_anterior):
...
301      if motiu_no_preserva(joc_anterior):
302          return set()
303      return set(model.grading_rules.filter(origen='MANUAL').values_list('pom_id', flat=True))
```

Retorna un **`set` de `pom_id` pelats**. Ho fa servir la materialització per (a) decidir si el wipe
és `exclude(origen='MANUAL')` o `all()`, i (b) filtrar les regles del joc nou que cauen sobre un POM
preservat. El seu propi docstring diu per què (`services.py:296-300`):

> «La preservació no és gratuïta: `ModelGradingRule` té `unique_together('model','pom')`, i el
> `bulk_create` de sota no porta conflict-handling. Per això la materialització SALTA les regles del
> joc nou que cauen sobre un POM preservat — si no, el que surt d'aquí no és una regla salvada, és
> un `IntegrityError`.»

**Funcions germanes de la mateixa política** (tota la lògica de preservació MANUAL viu aquí):

| fitxer:línia | símbol | paper |
|---|---|---|
| `services.py:240-244` | `_ORIGEN_RS_A_MGR` | diccionari de traducció `GradingRuleSet.origen` → `ModelGradingRule.origen` |
| `services.py:247-253` | `origen_mgr_des_de_ruleset` | joc sense classificar → estampa `MANUAL` (l'origen del parany) |
| `services.py:256` | `JOC_ANTERIOR_NO_INFORMAT` | sentinella; ≠ `None` |
| `services.py:262-271` | `joc_classificat` | el joc declara provinença? |
| `services.py:273-303` | **`poms_manual_a_preservar`** | el set de POMs que sobreviuen |
| `services.py:306-322` | `motiu_no_preserva` | `'no_informat'` / `'joc_sense_classificar'` / `None` |

**Consumidors de `poms_manual_a_preservar`** (5, tots verificats):
1. `services.py:342` — dins `materialize_model_grading_rules`
2. `services.py:382` — dins `materialize_model_grading_rules_from_specs`
3. `views.py:1135-1136` — `update_model_step2`, per passar `preservades=` al validador D1
4. `views.py:1706+1712` — còpia model→model (`n_preservades_dst`)
5. `management/commands/migra_brownie_ruleset.py:33+147` — per al recompte del dry-run

### 3.2 · Les 6 crides a `materialize_*` — **CONFIRMAT: en són 6**

| # | fitxer:línia | funció | superfície | `joc_anterior` informat? |
|---|---|---|---|---|
| 1 | `models_app/views.py:943` | `materialize_model_grading_rules` | creació de model (cas B, mono-peça) | **NO** (`JOC_ANTERIOR_NO_INFORMAT`) |
| 2 | `models_app/views.py:1016` | `materialize_model_grading_rules` | creació **multi-peça** (bucle per peça) | **NO** |
| 3 | `models_app/views.py:1161` | `materialize_model_grading_rules` | `update_model_step2` (canvi de joc) | SÍ (`grs_abans_obj`) |
| 4 | `models_app/views.py:1716` | `materialize_model_grading_rules` | còpia **model→model** (`copy_grading`) | SÍ (`grs_dst_abans`) |
| 5 | `models_app/extraction_views.py:2748` | `materialize_model_grading_rules_**from_specs**` | import W5 (sembra selectiva, `origen='IMPORTED'`) | SÍ (`prev_grs_obj`) |
| 6 | `models_app/management/commands/migra_brownie_ruleset.py:194` | `materialize_model_grading_rules` | comanda de migració Brownie | SÍ (`venia_de`) |

Definicions: `services.py:326-369` (des de `GradingRule`) i `services.py:372-408` (des de specs).
Les dues fan `bulk_create` **sense** `ignore_conflicts` ni `update_conflicts`
(`services.py:368` i `services.py:406`).

3 crides més **només a tests**: `tests_sembra_grading.py:421`, `:1690`, `:1951`.

### 3.3 · Els deletes CRUS — **el brief en deia 2; n'hi ha 2 a codi d'app + 2 més que el grep habitual NO veu**

| # | fitxer:línia | forma | comentari |
|---|---|---|---|
| **A** | `models_app/views.py:1118` | `model.grading_rules.all().delete()` | «Sense graduació» (`desacobla_joc`) al pas 2 del wizard. **No preserva MANUAL, a posta** (`views.py:1078-1082`) |
| **B** | `models_app/extraction_views.py:2712` | `model.grading_rules.all().delete()` | import W5, branca «contenidor amb regles» — l'únic camí de wipe que 6.1 declara obertament **no** tancat (`extraction_views.py:2706-2711`) |
| **C** | `pom/management/commands/consolidate_pom_catalog.py:257` | `getattr(m, rel).all().delete()` | fase FIXCOLL. `rel` itera `CFG.FUSIO_MOVE_RELS`, que inclou **`'model_grading_rules'`** (`pom/seed_data/consolidate_pom_los.py:31`). **Invisible a un grep per `grading_rules.all().delete()`**: el nom de la relació és una cadena en una llista de config |
| **D** | `pom/management/commands/consolidate_pom_catalog.py:117` | `type(obj).objects.filter(pk=obj.pk).update(pom=dest)` | **UPDATE CRU D'UNA COLUMNA DE LA CLAU.** Mou files d'un POM a un altre esperant `IntegrityError` com a senyal de col·lisió (`:119-120`) |

A més, deletes **a `scripts_tmp/`** (fora de l'app, però corren contra dades vives):
`scripts_tmp/diag_t3c.py:32`, `scripts_tmp/p05d_prova_fallback.py:13`,
`scripts_tmp/p05d_tres_casos.py:33`, `scripts_tmp/p05d_revert.py:11` (delete) i
`scripts_tmp/p05d_revert.py:9` (`.update(**ORIG_420)` per `(model_id, pom_id)`).

I la cascada implícita: **`Model.delete()` → CASCADE** s'endú totes les regles del model. És el camí
pel qual el wipe de 46 models del 06/08 va deixar `fhort` a zero.

### 3.4 · Els escriptors PER FILA (els que la constraint C4 va ensenyar a censar)

| fitxer:línia | superfície | forma |
|---|---|---|
| `models_app/views.py:2364-2399` | `gravar_pom` (la taula de gènesi de mesures) | `filter(model=model, pom_id=pom_id).first()` → si `None`, construeix `ModelGradingRule(model=…, pom_id=…)`; `rule.origen='MANUAL'`; `rule.save()` |
| `models_app/views.py:4802-4865` | `set_pom_regim_view` (`POST /api/v1/models/<id>/pom/<pom_id>/regim/`, `urls.py:240`) | **idèntic patró**: lookup per `(model, pom_id)`, upsert, `origen='MANUAL'` |
| `tenants/federation_service.py:810-820` | recepció de federació | guard `filter(model=twin, pom=pom).exists()` → `ModelGradingRule.objects.create(...)` |
| `models_app/management/commands/clone_model_for_qa.py:101-102` | clonatge QA | `r.pk = None; r.id = None; r.model = clone; r.save()` — **còpia de fila crua, camp a camp implícit** |
| `pom/management/commands/fix_brownie_break_enrere.py:108-109` | fix puntual | `.filter(id__in=ids_res).update(talla_break_label=new)` (no toca la clau) |
| `pom/migrations/0042_linear_zero_to_fixed.py:80-93` | migració de dades | `.filter(id__in=ids_resident).update(logica='FIXED')` (no toca la clau) |

Els dos primers són **les dues úniques portes d'escriptura de pantalla** i tots dos fan el mateix
lookup de dos camps. Són els germans exactes de «CLONAR amb 500» i «Afegir talla mut» de C4.

### 3.5 · `derivat_de_rule_set` i la migració `0079`

**Camp:** `models.py:1084-1089` (definició sencera enganxada a §1).
**Migració:** `/var/www/ftt-staging/backend/fhort/models_app/migrations/0079_m3_derivat_de_rule_set.py`
— literal, sencera:

```python
# Generated by Django 6.0.5 on 2026-08-07 04:52
import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('models_app', '0078_c4_g3_retira_comportes'),
        ('pom', '0063_n1_classifica_tipus_escala'),
    ]
    operations = [
        migrations.AddField(
            model_name='modelgradingrule',
            name='derivat_de_rule_set',
            field=models.ForeignKey(blank=True, db_constraint=False, help_text='Joc del qual es va materialitzar aquesta fila. NULL = autoria de pantalla, federació, o fila anterior a M3 (sense backfill: no es pot saber).', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='regles_residents_derivades', to='pom.gradingruleset'),
        ),
    ]
```

`0079` és l'**última** migració de `models_app`. És un `AddField` pur, **sense backfill i a posta**
(`models.py:1074-1075`). Escriptors del camp (4): `services.py:359`
(`derivat_de_rule_set_id=getattr(r,'rule_set_id',None)`), `services.py:403`
(`s.get('rule_set_id')`), `views.py:2378` i `views.py:4822` (`src.rule_set_id if src else None`).
Font del valor al camí dels specs: `pom/grading_utils.py:752` (`rule_to_spec`).

> ⚠️ **`0079` no consta com a aplicada a cap tenant.** El dump pre-wipe de `fhort` (06/08 17:57)
> encara porta la taula **sense** la columna `derivat_de_rule_set_id` — vegeu §6. No s'ha corregut
> `showmigrations` (seria lectura, però no s'ha fet: no era a l'encàrrec i el `migrate` que hi ha
> pendent és de la sessió U1/U2, `0073`). Punt obert a §7.

### 3.6 · Lectors (👁️) — la superfície que la clau nova canviaria de forma

**El punt únic i el que decideix tota la resta:**

`fhort/pom/services.py:722-755` · **`_load_grading_rules(model) -> dict`**

```python
749      return {r.pom_id: r for r in rules}
```

Retorna **`{pom_id: rule}`**. El seu comentari de capçalera (`services.py:723-729`) és una acta
explícita de que aquesta clau **no ha de créixer** — escrita per a `capa`/`instancia`, no per a
`element`. Consumidors del diccionari (tots resolen `rules.get(pom_id)` amb el `pom_id` **extret**
de la identitat de la mesura):

| fitxer:línia | què fa |
|---|---|
| `pom/services.py:209` + `:239` | `generate_graded_specs` — el motor de graduació. `rule = rules.get(pom_id)` amb el `pom_id` extret de la clau `(pom_id, capa, instancia)`. El comentari `:234-238` avisa que passar-hi la tupla deixaria el motor **mut** |
| `pom/services.py:399` + `:413` | `preview` de la graduació — mateix patró |
| `models_app/views.py:1937-1938` + `:2028` | taula de mesures/escalat. Emet `regla_es_resident` = `isinstance(rule, ModelGradingRule)` |
| `models_app/views.py:3220` | `ajustar-talla` — decideix si l'edició d'una cel·la PROPAGA per regla |
| `fitting/views.py:676` | fitting: `_load_grading_rules(pf.model).get(line.pom_id)` |
| `fitting/serializers.py:264` | serializer de fitting |
| `fitting/graded_spec_views.py:142-143` | taula de specs graduats |
| `models_app/serializers_size_check.py:97` | Size Check |

**Lectors directes de la taula (no via `_load_grading_rules`):**

| fitxer:línia | què fa |
|---|---|
| `pom/services.py:711-712` | `_te_regles` — la **porta d'entrada del motor** (`exists()` per model) |
| `models_app/services_size_check.py:133-134` | `model_te_deltes` — booleà que decideix si una correcció de base propaga |
| `models_app/views.py:586-589` | `comptar_regles_residents` — `values('origen').annotate(Count('id'))`; alimenta els 409 |
| `models_app/comprovacio_views.py:230-232` | `poms_amb_regla` = `set(values_list('pom_id'))` (Comprovació, D-31.17) |
| `pom/wizard_views.py:476-486` | `regla_by_pom = {r.pom_id: {...}}` — alimenta **tot** `TechSheetEditor.pomRows` |
| `pom/cataleg_views.py:69` i `:76` | fitxa del POM: `models_vius` i comptador `rules` |
| `pom/cataleg_views.py:29-52` | `_cens_relacions` — recorre `POMMaster._meta.related_objects`; `ModelGradingRule` hi surt com a **bloquejant** (PROTECT) en esborrar un POM |
| `pom/grading_utils.py:68-115` | `grading_rules_match(model_rules, canonical_rules)` — `m_by = {r.pom_id: r}` vs `c_by = {r.pom_id: r}` |
| `tenants/federation_service.py:672-686` | **export** de patrimoni: itera regles actives, emet `_clau_natural_pom(r.pom)` |
| `models_app/management/commands/migra_brownie_ruleset.py:90-92` | `residents = set(values_list('pom_id'))` vs `del_joc` |
| `models_app/extraction_views.py:2756` | `n_rules = model.grading_rules.count()` |
| `models_app/serializers.py:282` | només comentari (precedència de capçalera); no consulta la taula |

### 3.7 · Senyals — **cap**

`fhort/models_app/signals.py` té 8 receivers, tots `@receiver(pre_save)` / `@receiver(post_save)`
**globals** (sense `sender=`), però tots surten per la porta a la primera línia:

```
signals.py:31   if sender is not Model: return
signals.py:106  if sender is not Model: return
signals.py:157  if sender is not Model: return
signals.py:188  if sender is not Model: return
signals.py:241  if sender is not BaseMeasurement: return
signals.py:266  if sender is not BaseMeasurement: return
signals.py:386  if sender is not Model ...
signals.py:405  if sender is not Model ...
```

**Cap senyal es dispara per `ModelGradingRule`.** Cap `pre_delete`/`post_delete` en tot el projecte
la toca.

### 3.8 · Serializers — **cap serializer d'aquesta taula**

Verificat: no existeix cap `ModelGradingRuleSerializer`. Les regles residents s'exposen **a mà**,
com a dicts, a `pom/wizard_views.py:477-486` i `models_app/views.py:2027-2028`. El front les consumeix
per `pom_id`.

### 3.9 · Frontend (escaneig superficial, no exhaustiu)

`frontend/src/api/endpoints.js:100-109` — tres helpers apunten a la **mateixa** URL de dos segments:

```js
100  setPomRegim: (modelId, pomId, logica) => client.post(`/api/v1/models/${modelId}/pom/${pomId}/regim/`, { logica }),
106    client.post(`/api/v1/models/${modelId}/pom/${pomId}/regim/`, camps || {}),
109  setPomRule: (modelId, pomId, payload) => client.post(`/api/v1/models/${modelId}/pom/${pomId}/regim/`, payload),
```

Consumidors identificats (per grep de `regim|regla_es_resident|regla_origen`): `PropagatedEditor.jsx`,
`FittingDetail.jsx`, `GradingRuleSets.jsx`, `EditableTable.jsx`, `measureSources.jsx`,
`CustomerForm.jsx`, `GraduacioSuperficie.jsx`, `fittingGridAdapter.jsx`, `CheckMeasureEditor.jsx`.

---

## 4 · Impacte per punt del cens si la clau passa a `('model','element','pom')`

*(descripció d'impacte, no de solució)*

### 4.1 · El punt de col·lapse: `_load_grading_rules` (`pom/services.py:749`)

La clau del diccionari és `pom_id` pelat. Amb dues regles del mateix POM en dos elements, el dict
**se'n queda una** i la segona desapareix en silenci — el mateix mode de fallada que
`federation_service.py:645-646` descriu per als eixos i que `_load_model_overrides` va haver de
resoldre creixent la clau (`pom/services.py:758-774`). Els 8 consumidors de §3.6 hereten el defecte
sencer: motor, preview, taula d'escalat, `ajustar-talla`, fitting (×3) i Size Check.

I el revers, que és pitjor: el comentari de `services.py:234-238` documenta que si a `rules.get(...)`
se li passa la **tupla** en comptes del `pom_id`, `rule` és `None` per a tots els POMs, el motor
cau a la branca «sense regla» i **no emet cap cel·la**. Qualsevol adaptació d'aquest lookup té les
dues fallades a un caràcter de distància, i cap de les dues peta: una calla, l'altra menteix.

**Precondició no resolta:** perquè el lookup pugui créixer, la **identitat de la mesura** (la clau de
`_load_base_measurements`, avui `(pom_id, capa, instancia)`) hauria de saber a quin element pertany
cada mesura. `BaseMeasurement` **no té** cap camp d'element (verificat a §0). Sense això, el motor no
té amb què triar entre dues regles del mateix POM.

### 4.2 · `poms_manual_a_preservar` (`services.py:303`)

Retorna un `set` de `pom_id`. Amb la clau nova, un POM preservat en un element **preservaria també**
el mateix POM a tots els altres elements del model — la preservació es tornaria més ampla del que
la decisió 6.1 diu, i el filtre de `services.py:347` / `:387`
(`[r for r in source_rules if r.pom_id not in preservats]`) faria **caure regles legítimes** d'altres
elements sense que ningú se n'assabenti (no és `IntegrityError`: és una regla que no es crea).
Simètricament, `views.py:1144` (`preservades=len(poms_preservats)`) passaria al validador D1 un
recompte que ja no és el de files. La llei de F1-bis («el permís i la destrucció miren el mateix»)
es trencaria pel costat del permís.

### 4.3 · Les 6 `materialize_*`

- **`bulk_create` sense conflict-handling** (`services.py:368`, `:406`): amb la clau nova, el `pom_id`
  ja no basta per garantir que no hi hagi duplicats dins del lot — depèn de si el lot pot portar el
  mateix POM per a dos elements.
- **La FONT de les regles no té element.** Els casos 1, 2, 3, 4 i 6 alimenten la materialització amb
  `GradingRuleSet.regles.all()` — objectes `pom.GradingRule`, que **no tenen** cap noció d'element
  (mateixa acta que per a `capa`/`instancia`, `pom/models.py:1500`). El constructor de
  `services.py:349-366` i `:389-405` no té d'on treure el tercer camp de la clau.
- **Cas 2 (multi-peça, `views.py:1016`)** és el que més xoca conceptualment: avui una «peça» ÉS un
  `Model` sencer amb el seu `garment_type_item` i el seu `grading_rule_set`
  (`views.py:948-953`). Amb `element` dins del model, hi hauria **dos** eixos de peça i caldria dir
  quin mana; el codi actual no expressa la diferència.
- **Cas 4 (còpia model→model, `views.py:1713-1719`)**: `dst` rep les regles del **joc** de `src`, no
  les de `src`. Els elements de `dst` no tenen per què existir ni coincidir amb els de `src`.
- **Cas 5 (specs, `extraction_views.py:2748`)**: els specs vénen de `derive_rules_from_fitxa` i de
  `rule_to_spec` (`grading_utils.py:738-757`) — cap dels dos porta element. `classifica_fitxa_vs_contenidor`
  (`grading_utils.py:789`) indexa `cont_by = {r.pom_id: r}`: mateix col·lapse que §4.1.

### 4.4 · Els deletes crus

- **A (`views.py:1118`)** i **B (`extraction_views.py:2712`)** són `all().delete()` per model: **no
  canvien de comportament** amb la clau nova (esborren tot el model, elements inclosos). El que sí
  canvia és el **recompte** que els acompanya: `comptar_regles_residents` (`views.py:586-589`) segueix
  comptant files, però el missatge del 409 (`views.py:1110-1115`) parla de «regles de graduació
  pròpies» sense dir de quin element — un usuari amb 3 elements veuria un número que no sap col·locar.
- **C (`consolidate_pom_catalog.py:257`)**: esborra per `related_name` des d'una llista de config.
  Cap canvi funcional, però és el punt que un cens per grep no veu.
- **D (`consolidate_pom_catalog.py:117`)**: `update(pom=dest)` sobre una columna de la clau. La seva
  detecció de col·lisions **depèn de la constraint** (`except IntegrityError → coll += 1`,
  `:119-120`). Canviar la clau canvia què compta com a col·lisió: dues regles del mateix POM en
  elements diferents deixarien de col·lidir, i el recompte de `_fuse_one` diria una altra cosa
  sense que ningú hagi tocat aquest fitxer.

### 4.5 · Els escriptors per fila (les dues portes de pantalla)

- **`views.py:2364`** (`gravar_pom`) i **`views.py:4803`** (`set_pom_regim_view`) fan
  `filter(model=…, pom_id=…).first()`. Amb la clau de 3, aquest `.first()` **retorna una fila
  arbitrària** entre els elements (no hi ha `ordering` a la `Meta` — §1) i la sobreescriu. No peta:
  edita la regla de l'element equivocat. Aquest és, literalment, el mode de fallada del precedent C4.
- La **URL** de la porta de pantalla és de dos segments
  (`urls.py:240`: `models/<model_id>/pom/<pom_id>/regim/`). No hi ha lloc on dir l'element, i el
  front la crida des de 3 helpers i ≥9 components (§3.9).
- **`federation_service.py:810`**: el guard `filter(model=twin, pom=pom).exists()` col·lapsaria els
  elements — la segona regla del mateix POM no viatjaria mai i comptaria com a `saltat['regles']`.
  El **paquet** (`:678`) porta `_clau_natural_pom(r.pom)` sense element; el docstring de `:645-651`
  ja diu que ampliar la clau natural és **FASE_3**. Un element nou reobre exactament aquest punt.
- **`clone_model_for_qa.py:102`**: `r.pk = None; r.model = clone; r.save()` copia **tots** els altres
  camps sense mirar-los. Amb un camp `element` a la fila, el clon naixeria apuntant a l'element del
  model **origen** — una FK creuada entre dos models, que la constraint no atura perquè la constraint
  només mira unicitat. És el segon germà exacte del «CLONAR amb 500» de C4.

### 4.6 · `derivat_de_rule_set` / `0079`

`derivat_de_rule_set` no forma part de cap clau i **no queda afectat** per la unicitat nova. Els seus
4 escriptors (§3.5) sí que quedarien afectats indirectament: viuen dins dels mateixos constructors
que hauran de saber posar `element`. `0079` és `AddField` pur; una migració de clau hi dependria
per ordre, no per contingut.

### 4.7 · Els lectors de recompte i de cens

- `comptar_regles_residents` (`views.py:586`) agrupa per `origen` i prou → el número deixa de ser
  interpretable sense element (§4.4).
- `comprovacio_views.py:230` (`poms_amb_regla`, un `set` de `pom_id`) → un POM amb regla a l'element
  A faria semblar «cobert» el mateix POM a l'element B, i `_seccio_bloquegen` (`:234`) deixaria de
  bloquejar el que hauria de bloquejar.
- `wizard_views.py:477` (`regla_by_pom`) → col·lapse en un dict per `pom_id`; el comentari
  `wizard_views.py:496-500` documenta que aquest mateix problema ja va passar amb les germanes de
  capa/instància a `TechSheetEditor` (`new Map(...)` es queda l'última entrada).
- `grading_utils.py:87-88` (`grading_rules_match`) → `m_by`/`c_by` per `pom_id`; la comparació
  «mateix conjunt de POMs» donaria falses divergències i falses coincidències.
- `cataleg_views.py:76` (`regles`) → compta files; segueix sent correcte però deixa de ser
  «àncores distintes», que és el que el docstring de `:56-59` promet.
- `cataleg_views.py:29-52` (`_cens_relacions`) → **no cal tocar-lo**: recorre `related_objects` de
  l'ORM, i `ModelGradingRule` hi seguirà sortint amb `PROTECT` sigui quina sigui la clau. És l'únic
  cens del cens que ja està a prova de la lliçó TGIRL.
- `_te_regles` (`pom/services.py:712`) i `model_te_deltes` (`services_size_check.py:134`) són
  `exists()` per model: **cap canvi**. Però deixen de ser el mirall de `_load_grading_rules` que el
  seu docstring promet (`pom/services.py:709`) si el motor passa a resoldre per element — un model
  amb regles només a l'element A passaria la porta i el motor no graduaria l'element B.

---

## 5 · Estat de `tests_sembra_grading`

**Fitxer:** `/var/www/ftt-staging/backend/fhort/models_app/tests_sembra_grading.py` · **2.038 línies** ·
13 classes · 106 tests.

### 5.1 · Els tests que cobreixen la clau AVUI

**Un de sol la toca com a clau:**

- **`Decisio61PreservaManualTest.test_porta1_una_MANUAL_sobre_el_MATEIX_POM_que_el_joc_nou_no_peta_i_mana`**
  (`:1729`) — docstring literal a `:1730`:
  > «🔴 El cas que hauria estat un IntegrityError: `unique_together('model','pom')`.»

  És l'únic test que exercita la col·lisió de clau, i **hi entra per la porta de la preservació**, no
  per la constraint: comprova que la materialització SALTA el POM preservat. **No** hi ha cap
  `assertRaises(IntegrityError)` en tot el fitxer (verificat: l'única aparició de `IntegrityError` a
  `tests_sembra_grading.py` és dins d'un docstring, `:1633`).

**La declara però no la prova** — docstring de classe `Decisio61PreservaManualTest` (`:1611-1633`):
> «`ModelGradingRule` té `unique_together('model','pom')` i la materialització fa `bulk_create`…»

**La depenen implícitament** (assumeixen «una fila per (model, pom)» via `.get()` o comptatges):
`:301`, `:309` (`UpdateStep2GradingTest`), `:1273`/`:1300`/`:1338`/`:1356`
(`EsborratResidentsD314Test`), `:1470`/`:1475` (`PermisIDestruccioMirenElMateixTest`),
`:1661`/`:1666` (`Decisio61…`), `:1910` (`M3DerivatDeRuleSetTest`).

### 5.2 · Les 13 classes i el seu grau d'exposició

| classe (línia) | nº tests | toca `ModelGradingRule`? |
|---|---|---|
| `MaterialitzarPomsTest` (116) | 9 | no (sembra de POMs, no regles) |
| `UpdateStep2GradingTest` (239) | 6 | **sí** (`.get(model, pom)` a `:301`, `:309`) |
| `LinearZeroEsFixedTest` (337) | 4 | **sí** (`materialize_…` a `:421`) |
| `PodaSoftTest` (429) | 5 | no |
| `ImportSorollTest` (489) | 10 | no |
| `GuardDeTallaSembraTest` (640) | 8 | no |
| `PromocioModelItemTest` (786) | 13 | no |
| `ActeCanonicBaseSetTest` (1053) | 5 | no |
| `ItemBaseMeasurementBasicsTest` (1130) | 7 | no |
| `EsborratResidentsD314Test` (1240) | 7 | **sí** (crea per `(model, pom)`, `:1273`) |
| `PermisIDestruccioMirenElMateixTest` (1413) | 7 | **sí** (`:1470`, `:1475`) |
| `Decisio61PreservaManualTest` (1611) | 12 | **sí** — la classe de la clau |
| `M3DerivatDeRuleSetTest` (1870) | 7 | **sí** (`:1910`) |

### 5.3 · El que NO cobreix cap test, ni aquí ni enlloc

1. **Cap test prova la constraint com a constraint.** Enlloc del projecte hi ha un
   `assertRaises(IntegrityError)` en crear dues `ModelGradingRule` amb el mateix `(model, pom)`.
   La constraint és l'única llei d'aquesta taula i **no té pin**.
2. **Cap test mira l'índex a BD.** Contrast directe: `capa` i `instancia` **sí** que tenen pins
   d'`information_schema` (`test_capa_comporta_c1.py:127-137` i
   `test_instancia_comporta_cins.py:203-219`), i tots dos afirmen l'**absència** de columna a
   `models_app_modelgradingrule`. **Aquests dos tests fallarien** el dia que la taula rebi una
   columna nova? No — miren `capa` i `instancia` pel nom, i `element` no hi és. Però són l'acta
   escrita que aquesta taula «no travessa cap eix», i afegir-n'hi un les contradiu en esperit.
3. **Cap test cobreix les 4 crides de `materialize_*` de `views.py:943`, `:1016`, `:1716` i
   d'`extraction_views.py:2748`** *des de la clau*. Els camins existeixen als tests (còpia
   model→model a `test_copia_model_a_model.py:230`, federació a `tests_enviament_feina.py:164-165`)
   però comptant files, no provant unicitat.
4. **Cap test de `consolidate_pom_catalog`** (els deletes/updates crus C i D).
5. **Cap test de `clone_model_for_qa`** (la còpia crua de fila).
6. `test_u2_acumulacio.py:289-300` prova que **el cens de relacions de `POMMaster` recorre l'ORM i
   no una llista a mà**, i cita `models_app.ModelGradingRule` per nom. És el pin de la lliçó TGIRL i
   **sobreviu** a qualsevol canvi de clau.

---

## 6 · Recompte de files per esquema

### 6.1 · Avui (staging, 07/08)

| esquema | taula present? | files `ModelGradingRule` | `models_app_model` | `pom_gradingrule` |
|---|---|---|---|---|
| `public` | **NO** (`models_app` és app tenant-only) | — | — | (compartida) |
| `fhort` | sí | **0** | **0** | 1.267 |
| `los` | sí | **0** | **51** | 0 |

Esquemes existents a la BD: `fhort`, `los`, `public` (i prou).

**Els zeros no volen dir el mateix:**
- `fhort` = 0 perquè **no queda cap model** (wipe de 46 models del 06/08, ja registrat a memòria).
  És conseqüència del `CASCADE` de `Model`, no un estat de la taula.
- **`los` = 0 amb 51 models vius**: aquests 51 models **no tenen cap regla resident**. Graduen (si
  graduen) pel `grading_rule_set` extern, i `los` també té `pom_gradingrule = 0` → **cap dels 51
  models de `los` pot graduar avui** per cap de les dues branques de `_load_grading_rules`. Això no
  és una conclusió sobre B3; és una observació que surt del recompte i que no s'ha investigat.

### 6.2 · L'evidència REAL: el dump pre-wipe de `fhort`

Com que 0 no diu res, s'ha llegit el darrer estat conegut amb dades:
`/root/backups/ftt_staging_fhort_pre_V4_20260806_175759.dump` (custom PGDMP 18.4; cal
`/usr/lib/postgresql/18/bin/pg_restore`, el del sistema és 16.14 i no el sap obrir).

```
FILES: 4783
per origen: {'CLIENT_RUN': 4724, 'MANUAL': 24, 'CANONICAL': 35}
models distints: 45   ·   poms distints: 152
parells duplicats (model,pom): 0
actiu = f: 0
```

Columnes del `COPY` al dump (línia 26 del volcat):

```
id, logica, increment, valors_step, increment_base, increment_break,
talla_break_label, talla_break_pos, origen, actiu, created_at, updated_at,
model_id, pom_id
```

Tres lectures que compten:
1. **4.783 files a migrar** en el cas realista, no 0. ~106 regles per model.
2. **Cap `IMPORTED` i cap `FEDERAT`**; les `MANUAL` (les que 6.1 i M1 protegeixen) són **24**, un
   0,5 % — i són exactament les que qualsevol backfill d'`element` no pot inventar.
3. **`derivat_de_rule_set_id` NO hi és.** El dump és de 06/08 17:57 i `0079` és de 07/08 04:52.
   Confirma que quan es va prendre l'snapshot la migració M3 no existia; **no** confirma que
   avui estigui aplicada (§7).

---

## 7 · Què NO s'ha pogut determinar en lectura

1. **La definició d'`element`.** No existeix cap entitat, camp ni migració amb aquest nom. Sense
   saber si serà FK nullable, si tindrà valor per defecte («element únic», com `instancia=''`) i
   quin `on_delete` portarà, no es pot dir si la clau nova és una ampliació compatible o una
   partició. Tota la §4 assumeix «hi haurà un tercer camp»; res més.
2. **Si `0079` està aplicada.** No s'ha corregut `showmigrations` ni s'ha inspeccionat
   `django_migrations` (queda pendent el `migrate` de `0073` de la sessió U1/U2, segons memòria).
   El dump pre-wipe demostra que **no ho estava** el 06/08; l'estat d'avui és desconegut.
3. **PROD.** Sense SSH. No s'ha llegit el backup diari de producció; els 4.783 del §6.2 són de
   **staging**. La memòria registra ~1.444 regles i 35 models a PROD (D-31.4), xifra que **no s'ha
   verificat en aquesta sessió**.
4. **Si dues regles del mateix POM en elements diferents són un cas REAL.** El dump no en pot dir res
   (0 duplicats, però tampoc hi havia elements). És una pregunta de domini per a l'Agus/Montse, del
   mateix ordre que les dues actes de `capa` i `instancia` enganxades a `models.py:1005-1020`, que
   diuen **exactament el contrari** per als altres dos eixos: «la regla és una llei d'increments,
   compartida». Si `element` travessa la regla i `capa`/`instancia` no, la taula tindrà **un** eix i
   la seva pròpia docstring haurà de deixar de dir «no travessa CAP dels dos eixos».
5. **`BaseMeasurement` sense element.** La identitat de mesura que el motor fa servir
   (`(pom_id, capa, instancia)`) no sap d'elements. Fins que ho sàpiga, `_load_grading_rules` no té
   amb què triar entre dues regles. **No s'ha censat `BaseMeasurement`** — era fora de l'encàrrec B3,
   però la §4.1 hi depèn del tot.
6. **El front.** L'escaneig de `frontend/src` ha estat superficial (grep per `regim|regla_es_resident|
   regla_origen`): 9 fitxers identificats, **cap llegit**. Quants d'ells munten mapes per `pom_id`
   —el patró que `wizard_views.py:496-500` documenta com a font de bugs amb les germanes— està
   sense mesurar.
7. **La suite no s'ha corregut.** Cap test executat (mode lectura pura). Segons memòria, la suite
   ve d'abans amb feina pendent (`0073` sense aplicar) i `… | tail` es menja el codi de sortida.

---

## 8 · Resum del cens en una taula

| # | Punt | Fitxer:línia | Tipus | Impacte de la clau nova |
|---|---|---|---|---|
| 1 | Definició | `models_app/models.py:994-1100` | — | `unique_together` de 2 → 3; nou camp; `Meta` sense `constraints`/`indexes`/`ordering` |
| 2 | `poms_manual_a_preservar` | `models_app/services.py:273-303` | 👁️ | retorna `set(pom_id)` → preservació massa ampla; filtra regles legítimes en silenci |
| 3 | `motiu_no_preserva` / `joc_classificat` / `origen_mgr_des_de_ruleset` | `services.py:247-322` | 👁️ | cap impacte directe |
| 4 | `materialize_model_grading_rules` | `services.py:326-369` | ✍️🗑️ | `bulk_create` sense conflictes; la font (`GradingRule`) no té element |
| 5 | `materialize_..._from_specs` | `services.py:372-408` | ✍️🗑️ | ídem; specs sense element (`grading_utils.py:752`) |
| 6 | crida 1/6 · creació mono-peça | `models_app/views.py:943` | ✍️ | `joc_anterior` no informat |
| 7 | crida 2/6 · creació multi-peça | `models_app/views.py:1016` | ✍️ | dos eixos de «peça» en conflicte conceptual |
| 8 | crida 3/6 · `update_model_step2` | `models_app/views.py:1161` | ✍️ | recompte del 409 deixa de ser interpretable |
| 9 | crida 4/6 · còpia model→model | `models_app/views.py:1716` | ✍️ | elements de `dst` ≠ de `src`; porta MUDA |
| 10 | crida 5/6 · import W5 | `models_app/extraction_views.py:2748` | ✍️ | `classifica_fitxa_vs_contenidor` indexa per `pom_id` |
| 11 | crida 6/6 · comanda Brownie | `management/commands/migra_brownie_ruleset.py:194` | ✍️ | `residents` és `set(pom_id)` (`:90`) |
| 12 | delete CRU A · «Sense graduació» | `models_app/views.py:1118` | 🗑️ | comportament igual; missatge del 409 incomplet |
| 13 | delete CRU B · import contenidor | `models_app/extraction_views.py:2712` | 🗑️ | ídem |
| 14 | delete CRU C · FIXCOLL | `pom/management/commands/consolidate_pom_catalog.py:257` | 🗑️ | invisible al grep (relació per cadena) |
| 15 | **update CRU de la clau** · fusió POM | `consolidate_pom_catalog.py:117` | ✍️ | la detecció de col·lisions **depèn** de la constraint |
| 16 | escriptor pantalla 1 · `gravar_pom` | `models_app/views.py:2364-2399` | ✍️ | `.first()` sobre 2 camps → edita l'element equivocat |
| 17 | escriptor pantalla 2 · `set_pom_regim_view` | `models_app/views.py:4802-4865` | ✍️ | ídem + URL de 2 segments (`urls.py:240`) |
| 18 | federació · export | `tenants/federation_service.py:672-686` | 👁️ | clau natural sense element (FASE_3 declarada) |
| 19 | federació · recepció | `tenants/federation_service.py:810-820` | ✍️ | guard `.exists()` col·lapsa elements |
| 20 | clon QA | `management/commands/clone_model_for_qa.py:101-102` | ✍️ | `pk=None` + `save()` → FK d'element creuada |
| 21 | fix break Brownie | `pom/management/commands/fix_brownie_break_enrere.py:108` | ✍️ | no toca la clau |
| 22 | migració 0042 | `pom/migrations/0042_linear_zero_to_fixed.py:80-93` | ✍️ | no toca la clau |
| 23 | migració 0079 (M3) | `models_app/migrations/0079_m3_derivat_de_rule_set.py` | — | `AddField` pur; dependència d'ordre |
| 24 | **`_load_grading_rules`** | `pom/services.py:722-755` | 👁️ | **el punt de col·lapse**; 8 consumidors |
| 25 | motor `generate_graded_specs` | `pom/services.py:209`, `:239` | 👁️ | `rules.get(pom_id)` extret de la identitat |
| 26 | preview | `pom/services.py:399`, `:413` | 👁️ | ídem |
| 27 | taula escalat | `models_app/views.py:1937`, `:2028` | 👁️ | `regla_es_resident` per `isinstance` |
| 28 | `ajustar-talla` | `models_app/views.py:3220` | 👁️ | decideix la propagació |
| 29 | fitting (3 punts) | `fitting/views.py:676`, `fitting/serializers.py:264`, `fitting/graded_spec_views.py:143` | 👁️ | per `pom_id` |
| 30 | Size Check | `models_app/serializers_size_check.py:97` + `services_size_check.py:134` | 👁️ | `exists()` per model |
| 31 | porta del motor `_te_regles` | `pom/services.py:711-712` | 👁️ | deixa de ser mirall del motor |
| 32 | `comptar_regles_residents` | `models_app/views.py:586-589` | 👁️ | recompte sense element |
| 33 | Comprovació | `models_app/comprovacio_views.py:230-232` | 👁️ | `set(pom_id)` → deixa de bloquejar |
| 34 | fitxa (`TechSheetEditor`) | `pom/wizard_views.py:476-486` | 👁️ | dict per `pom_id` → col·lapse |
| 35 | fitxa del POM | `pom/cataleg_views.py:69`, `:76` | 👁️ | comptadors |
| 36 | cens d'esborrat de POM | `pom/cataleg_views.py:29-52` | 👁️ | **a prova de canvi** (recorre l'ORM) |
| 37 | `grading_rules_match` | `pom/grading_utils.py:68-115` | 👁️ | `{pom_id: r}` ×2 |
| 38 | senyals | `models_app/signals.py` (8 receivers) | — | **cap es dispara**; verificat pel `sender` |
| 39 | serializers | — | — | **no n'hi ha cap** per aquesta taula |
| 40 | `scripts_tmp` (5 punts) | `diag_t3c.py:32`, `p05d_prova_fallback.py:13`, `p05d_tres_casos.py:33`, `p05d_revert.py:9`,`:11` | ✍️🗑️ | fora de l'app, contra dades vives |
| 41 | tests | 20 fitxers (§5 i llista completa a §3) | ✍️ | 1 sol test toca la clau com a clau |
