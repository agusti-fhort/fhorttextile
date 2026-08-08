# REPORT FASE_1 · C1-ins — LA COLUMNA `instancia` · 2026-08-02

**Veredicte: «FASE_2 POT ARRENCAR».** 5 commits · 0 PENDENTs · tots els green flags verds.
1 incident d'infraestructura resolt (§INCIDENT) · 0 canvis visibles.

---

## ELS 5 COMMITS

| # | hash | assumpte |
|---|---|---|
| C1 | **`e8db78e2`** | la columna `instancia`: el segon eix entra a l'esquema de `models_app` |
| C2 | **`442d4889`** | les claus de `models_app` s'obren a la instància i les comportes la tanquen |
| C3 | **`cb191283`** | la instància arriba a `fitting`: l'spec generat i la línia mesurada |
| C4 | **`c768d787`** | la instància a `pom`: on la plantilla declara quantes vegades reclama un POM |
| C5 | **`3d8878f6`** | el pin de la comporta d'instància, i la prova que «instància ⇒ nom» rebutja |

**CAP PUSH.** Cap fitxer de `docs/` dins de cap commit. `git add` de paths explícits a tots cinc.

## EL CAMP

```python
instancia = models.CharField(
    max_length=60, default='', db_index=True,
    help_text="Instància del POM dins la capa: slug compost canònic (p.ex. 'left-relaxed'). "
              "'' és la instància única. Fins a C4-ins només s'admet '' (comporta CHECK a BD).",
)
```

Declaració canònica a `models_app/models.py` (`BaseMeasurement`); les altres vuit taules hi apunten.
Mai FK, mai `choices` — com `capa`, i per la mateixa llei G9. `''` és la instància única, mai NULL.

## LES MIGRACIONS (`sqlmigrate` enganxat)

Els fitxers sencers són als commits. Aquí, l'SQL que emeten (executat amb el schema fixat a
`fhort`; `sqlmigrate` contra `public` retorna `BEGIN; COMMIT;` buit per a les apps TENANT-only
— és el comportament esperat de django-tenants, no un error).

### `models_app/0073_instancia_mesures` — ADD COLUMN + DROP DEFAULT

```sql
ALTER TABLE "models_app_basemeasurement"      ADD COLUMN "instancia" varchar(60) DEFAULT '' NOT NULL;
ALTER TABLE "models_app_basemeasurement"      ALTER COLUMN "instancia" DROP DEFAULT;
ALTER TABLE "models_app_measurementchangelog" ADD COLUMN "instancia" varchar(60) DEFAULT '' NOT NULL;
ALTER TABLE "models_app_measurementchangelog" ALTER COLUMN "instancia" DROP DEFAULT;
ALTER TABLE "models_app_modelgradingoverride" ADD COLUMN "instancia" varchar(60) DEFAULT '' NOT NULL;
ALTER TABLE "models_app_modelgradingoverride" ALTER COLUMN "instancia" DROP DEFAULT;
ALTER TABLE "models_app_pomplacement"         ADD COLUMN "instancia" varchar(60) DEFAULT '' NOT NULL;
ALTER TABLE "models_app_pomplacement"         ALTER COLUMN "instancia" DROP DEFAULT;
ALTER TABLE "models_app_sizecheckline"        ADD COLUMN "instancia" varchar(60) DEFAULT '' NOT NULL;
ALTER TABLE "models_app_sizecheckline"        ALTER COLUMN "instancia" DROP DEFAULT;
-- + 10 CREATE INDEX (b-tree + varchar_pattern_ops, 2 per taula)
```

**El parany confirmat a la BD:** `column_default` és **buit** a les 20 files de
`information_schema` (§AUDITORIA). El default viu al MODEL, no a Postgres → codi vell +
esquema nou = `NotNullViolation`. Per això el reinici del servei és part de la peça, no un extra.

### `models_app/0074_instancia_unicitats_comportes`

```sql
ALTER TABLE "models_app_pomplacement" DROP CONSTRAINT "uniq_pomplacement_item_pom_view_capa";
ALTER TABLE "models_app_basemeasurement" DROP CONSTRAINT "models_app_basemeasureme_model_id_pom_id_capa_5d54f2ba_uniq";
ALTER TABLE "models_app_basemeasurement" ADD CONSTRAINT "models_app_basemeasureme_model_id_pom_id_capa_ins_8405ced0_uniq" UNIQUE ("model_id", "pom_id", "capa", "instancia");
ALTER TABLE "models_app_modelgradingoverride" DROP CONSTRAINT "models_app_modelgradingo_model_id_pom_id_size_lab_82f07c3b_uniq";
ALTER TABLE "models_app_modelgradingoverride" ADD CONSTRAINT "models_app_modelgradingo_model_id_pom_id_size_lab_2b3deedb_uniq" UNIQUE ("model_id", "pom_id", "size_label", "capa", "instancia");
ALTER TABLE "models_app_sizecheckline" DROP CONSTRAINT "models_app_sizecheckline_size_check_id_pom_id_cap_850869dc_uniq";
ALTER TABLE "models_app_sizecheckline" ADD CONSTRAINT "models_app_sizecheckline_size_check_id_pom_id_cap_499924ad_uniq" UNIQUE ("size_check_id", "pom_id", "capa", "instancia");
ALTER TABLE "models_app_basemeasurement"      ADD CONSTRAINT "models_app_basemeasurement_instancia_gate_cins"      CHECK ("instancia" = '');
ALTER TABLE "models_app_basemeasurement"      ADD CONSTRAINT "models_app_basemeasurement_instancia_exigeix_nom"    CHECK (NOT ("instancia" > '' AND "nom_fitxa" = ''));
ALTER TABLE "models_app_measurementchangelog" ADD CONSTRAINT "models_app_measurementchangelog_instancia_gate_cins" CHECK ("instancia" = '');
ALTER TABLE "models_app_modelgradingoverride" ADD CONSTRAINT "models_app_modelgradingoverride_instancia_gate_cins" CHECK ("instancia" = '');
ALTER TABLE "models_app_pomplacement"         ADD CONSTRAINT "uniq_pomplacement_item_pom_view_capa_instancia" UNIQUE ("item_fitxer_id", "pom_id", "view_slot", "capa", "instancia");
ALTER TABLE "models_app_pomplacement"         ADD CONSTRAINT "models_app_pomplacement_instancia_gate_cins"         CHECK ("instancia" = '');
ALTER TABLE "models_app_sizecheckline"        ADD CONSTRAINT "models_app_sizecheckline_instancia_gate_cins"        CHECK ("instancia" = '');
```

### `fitting/0020_instancia_cins`

```sql
ALTER TABLE "fitting_gradedspec" DROP CONSTRAINT "fitting_gradedspec_grading_version_id_pom_i_631abad1_uniq";
ALTER TABLE "fitting_piecefittingline" DROP CONSTRAINT "fitting_piecefittingline_piece_fitting_id_pom_id__9bbf8b9c_uniq";
ALTER TABLE "fitting_gradedspec"       ADD COLUMN "instancia" varchar(60) DEFAULT '' NOT NULL;
ALTER TABLE "fitting_gradedspec"       ALTER COLUMN "instancia" DROP DEFAULT;
ALTER TABLE "fitting_piecefittingline" ADD COLUMN "instancia" varchar(60) DEFAULT '' NOT NULL;
ALTER TABLE "fitting_piecefittingline" ALTER COLUMN "instancia" DROP DEFAULT;
ALTER TABLE "fitting_gradedspec"       ADD CONSTRAINT "fitting_gradedspec_grading_version_id_pom_i_2dd89ac9_uniq"     UNIQUE ("grading_version_id", "pom_id", "size_label", "capa", "instancia");
ALTER TABLE "fitting_piecefittingline" ADD CONSTRAINT "fitting_piecefittingline_piece_fitting_id_pom_id__da11fdd0_uniq" UNIQUE ("piece_fitting_id", "pom_id", "size_label", "capa", "instancia");
ALTER TABLE "fitting_gradedspec"       ADD CONSTRAINT "fitting_gradedspec_instancia_gate_cins"       CHECK ("instancia" = '');
ALTER TABLE "fitting_piecefittingline" ADD CONSTRAINT "fitting_piecefittingline_instancia_gate_cins" CHECK ("instancia" = '');
-- + 4 CREATE INDEX
```

### `pom/0056_instancia_cins` — **SHARED + TENANT**

Verificat amb `sqlmigrate` **schema per schema abans d'aplicar**: emet el MATEIX SQL a
`public`, `fhort` i `los` (30 sentències `ALTER TABLE` en total, 10 per schema).

```sql
ALTER TABLE "pom_garmentpommap" DROP CONSTRAINT "pom_garmentpommap_garment_type_item_id_pom_…_uniq";
ALTER TABLE "pom_itembasemeasurement" DROP CONSTRAINT "pom_itembasemeasurement_base_set_id_pom_id_capa_…_uniq";
ALTER TABLE "pom_garmentpommap"       ADD COLUMN "instancia" varchar(60) DEFAULT '' NOT NULL;
ALTER TABLE "pom_garmentpommap"       ALTER COLUMN "instancia" DROP DEFAULT;
ALTER TABLE "pom_itembasemeasurement" ADD COLUMN "instancia" varchar(60) DEFAULT '' NOT NULL;
ALTER TABLE "pom_itembasemeasurement" ALTER COLUMN "instancia" DROP DEFAULT;
ALTER TABLE "pom_garmentpommap"       ADD CONSTRAINT "pom_garmentpommap_garment_type_item_id_pom_e89888d8_uniq"       UNIQUE ("garment_type_item_id", "pom_id", "capa", "instancia");
ALTER TABLE "pom_itembasemeasurement" ADD CONSTRAINT "pom_itembasemeasurement_base_set_id_pom_id_capa__2bef584f_uniq" UNIQUE ("base_set_id", "pom_id", "capa", "instancia");
ALTER TABLE "pom_garmentpommap"       ADD CONSTRAINT "pom_garmentpommap_instancia_gate_cins"       CHECK ("instancia" = '');
ALTER TABLE "pom_itembasemeasurement" ADD CONSTRAINT "pom_itembasemeasurement_instancia_gate_cins" CHECK ("instancia" = '');
```

## EXECUCIÓ A BD

`migrate_schemas` (**MAI `--schema`**) → **4 migracions × 3 schemas, 12 OK**, sense una sola
advertència. `systemctl restart ftt-staging.service` → **active**, `/api/schema/` **200**.

### AUDITORIA · `cins_audit_counts.sql`

**100 % de files amb `instancia = ''` als 3 schemas. Cap NULL. Cap excepció.**

| schema | taula | files | instancia='' |
|---|---|---|---|
| fhort | `models_app_basemeasurement` | 760 | **760** |
| fhort | `models_app_measurementchangelog` | 289 | **289** |
| fhort | `models_app_modelgradingoverride` | 0 | 0 |
| fhort | `models_app_sizecheckline` | 92 | **92** |
| fhort | `models_app_pomplacement` | 2 | **2** |
| fhort | `fitting_gradedspec` | 2 061 | **2 061** |
| fhort | `fitting_piecefittingline` | 153 | **153** |
| fhort | `pom_garmentpommap` | 1 748 | **1 748** |
| fhort | `pom_itembasemeasurement` | 37 | **37** |
| los | (les 9) | 0 | 0 |
| public | `pom_garmentpommap`, `pom_itembasemeasurement` | 0 | 0 |
| **fhort/los** | **`models_app_modelgradingrule`** | 510 / 0 | **columna ABSENT ✅** |

`information_schema`: **20 files**, totes `is_nullable = NO`, `character_maximum_length = 60`,
`column_default` **buit** (el parany, confirmat).

### AUDITORIA · `cins_audit_constraints.sql`

| schema | comportes `_capa_gate_c1` | comportes `_instancia_gate_cins` |
|---|---|---|
| `fhort` | **9** | **9** |
| `los` | **9** | **9** |
| `public` | **2** | **2** |

Les **dues famílies vives i separades**, cap absorbida per l'altra.

**El CHECK de D1, a `fhort` i `los`:**
```
models_app_basemeasurement_instancia_exigeix_nom
  CHECK ((NOT (((instancia)::text > ''::text) AND ((nom_fitxa)::text = ''::text))))
```

**Les 8 unicitats**, als 3 schemas, totes amb `instancia` a l'últim tram i **cap resta de la
clau vella**. `models_app_modelgradingrule` segueix a `(model_id, pom_id)` i `pom_gradingrule`
a `(rule_set_id, pom_id)` — intactes, com mana la decisió Montse.

## GREEN FLAGS

| flag | resultat |
|---|---|
| `manage.py check` | **net** (0 issues) abans de cada commit |
| `makemigrations --check --dry-run` | **No changes detected** (models ↔ migracions sincronitzats) |
| migracions aplicades ×3 amb auditoria SQL | **12 OK** · auditoria de files i de constraints **verda** |
| pin `base_stages` | **13/13** |
| `test_capa_comporta_c1` intacte i verd | **intacte** (0 bytes tocats) i **6/6 OK** |
| `test_lectors_capa_onada1` | **verd** |
| `test_instancia_comporta_cins` (nou) | **12/12 OK** |
| **total dels 4 mòduls** | **Ran 37 tests · OK** |
| fumeig = T0 byte-idèntic | **`a14ce3ec1d47c1555fd8f3e59cae9a5f`** = T0 ✅ |
| dump de superfícies = T0 | **`fd2eaebed9ad576ca52246b400cce265`** = T0 ✅ (18 blocs, 0 excepcions) |
| OpenAPI · ocurrències de `instancia` | **1, i és la de T0** — l'homònim català de `materialitzar-poms`. Schema generat des del codi **byte-idèntic** a T0 (`9d0ec949e7d7e378ff488d1b681687ec`) |

## PENDENTS

**Cap.** Els 74 nodes del bloc `C1-ins` del dossier han entrat sencers.

---

## INCIDENT · LA BD DE TEST (resolt, però cal saber-ho)

En executar C5 vaig topar amb dos estats trencats **preexistents** de `test_ftt_staging`:

1. Amb `--keepdb`, aplicar qualsevol migració nova peta amb
   `relation "commerce_quotelinemodelintent" already exists` — la BD conservada tenia
   migracions de `commerce` **sense registrar** però amb les taules ja creades. A T0 no es va
   veure perquè, sense migracions pendents, `migrate` era un no-op.
2. Reconstruir-la des de zero peta abans, a
   **`pom/0013_garmenttype_descripcio_…`**: `column "descripcio" of relation
   "pom_garmenttype" already exists`. **Aquesta migració és de `0cd24539`, 43 migracions per
   sota de les meves**, i cap dels 5 commits d'aquesta fase toca cap migració anterior a
   `0056`/`0074`/`0020` — el planificador de migracions no llegeix `models.py`, o sigui que
   FASE_1 no hi pot ser causa. **La construcció des de zero de la BD de test ja estava trencada.**

**Com s'ha resolt** (i com s'ha de repetir si torna a passar): reconstruir `test_ftt_staging`
des de l'ESTRUCTURA de staging, no des de les migracions —

```bash
pg_dump -d ftt_staging --schema-only --no-owner --no-privileges     > staging_schema.sql
pg_dump -d ftt_staging --data-only --no-owner \
        -t 'public.django_migrations' -t 'fhort.django_migrations' -t 'los.django_migrations' \
        -t 'public.tenants_*' -t 'public.django_content_type'       > staging_migrations.sql
# CREATE DATABASE test_ftt_staging; psql -f staging_schema.sql; psql -f staging_migrations.sql
# després: manage.py test --keepdb   (aplica només les migracions noves)
```

Resultat: 274/273/271 migracions registrades a `public`/`fhort`/`los`, les 4 migracions noves
aplicades netes sobre la BD de test, **37 tests verds**. `pg_dump` és read-only: la BD de
staging no s'ha tocat en cap moment.

**🚩 Per a l'Agus:** la reconstrucció des de zero de la BD de test segueix trencada a
`pom/0013`. No bloqueja aquest tram, però és deute d'infra i val la pena mirar-lo abans que
algú necessiti una BD de test neta de debò.

---

## DESCOBERTES DEL REVISOR-DIFF (anotades, MAI arreglades)

Cap bandera ALTA. Els green flags es sostenen. Verificat empíricament que **cap serializer de
les 9 taules fa servir `fields = '__all__'`** (les 5 que existeixen tenen llista explícita; 4
de les 9 taules no tenen serializer), que **els tres `admin.py` són buits**, que **no hi ha cap
`values()`/`values_list()` de QuerySet sense arguments ni cap `.defer()`**, que **cap
consumidor referencia `uniq_pomplacement_item_pom_view_capa` pel nom**, i que **cap dels 11
noms de constraint nous passa de 51 caràcters** (límit 63).

**MITJA · l'accident del segon eix ja està armat als mateixos punts que el de la capa.** Cap
peta avui — la comporta ho garanteix — però la clau natural d'aquests set no coneix cap dels
dos eixos. **És el radi de FASE_3, amb dades:**

| fitxer:línia | clau que usa |
|---|---|
| `pom/services.py:1033` `_upsert_graded_spec` | `(grading_version_id, pom_id, size_label)` |
| `models_app/pom_placement_views.py:135` | `update_or_create(item_fitxer, pom_id, view_slot)` — i la **lectura germana** de la mateixa vista (`:74-76`) **ja** indexa per `(pom_id, capa)`: l'escriptura s'hi ha quedat enrere |
| `tenants/federation_service.py:689` | `filter(model=twin, pom=pom).first()` |
| `load_losan_package.py:363` i `:379` | `{gti, pom}` · `{base_set, pom}` |
| `bootstrap_tenant.py:162` | clau natural `('garment_type_item','pom')` |
| `fitting/serializers.py:246-249` | `spec_map[(gv_id, pom_id, size_label)]` (lector) |
| `fitting/repas_views.py:105-112` | `fora[(size_check_id, pom_id)]` (lector) |

**MITJA · `MeasurementChangeLog` rebrà `instancia=''` per a mesures que no ho seran.**
`models_app/signals.py:267` i `:299`, `models_app/views.py:2603` i `:2768` creen l'entrada de
log copiant només `model` i `pom`. És el mateix forat que la memòria ja té obert per a `capa`,
ara duplicat al segon eix — i la taula és **append-only**: escrita malament, la fila no es pot
corregir. **FASE_3 ha de tapar els dos eixos alhora al mateix punt.**

**MITJA · asimetria als tres camins de sortida.** `federation_service.py:596-603` i
`export_losan_package.py:254-265` construeixen dicts explícits **sense `instancia`**;
`bootstrap_tenant.py:208` itera `_meta.fields` i **se l'emporta sola**. Avui donen el mateix
perquè el valor és constant. La decisió «la instància viatja o no viatja?» no està presa
enlloc, i el camí que la conserva ho fa per introspecció, no per elecció.

**BAIXA · `reseed_tenant_fhort.py:303`** — `bulk_create(..., ignore_conflicts=True)` sobre
`GarmentPOMMap`: quan s'obri la clau, un reseed crearà duplicats en comptes de saltar-los.

**BAIXA · docstrings que ara menteixen sobre la clau** (fora de scope, no tocats):
`models_app/models.py:655` (*«la clau segueix sent `[('model','pom')]`»* — i el text següent,
*«separar-les de debò vol tocar la clau, que travessa 5 taules més»*, **descriu exactament el
que aquests 4 commits acaben de fer**) · `:697` · `fitting/serializers.py:255` ·
`extraction_views.py:1151,:1160` · `pom/models.py:181` · `pom/s10_views.py:69` ·
`pom/s8_views.py:164` · `fitting/services.py:349` · `models_app/views.py:2798`.

**BAIXA · 18 índexs sobre una columna de cardinalitat 1.** `db_index=True` genera b-tree +
`varchar_pattern_ops` per taula. `capa` es va declarar exactament igual, i la coherència amb el
germà val més que els bytes; si mai es reconsidera, s'han de reconsiderar **els dos eixos
alhora**.

**BAIXA · el T0 d'OpenAPI del servei viu porta 48 línies de deriva aliena** (l'sprint
d'imatges, ja a l'historial des de `d690a020`): el servei corria codi anterior a HEAD. Per això
s'ha capturat **un segon baseline generat des del CODI** (`manage.py spectacular`), que és el
que certifica el green flag i que ha sortit byte-idèntic abans i després.

**Confirmat com a ben resolt:** el CHECK de D1 **no té forat de NULL** — `nom_fitxa` és
`NOT NULL` (`models_app/models.py:636-640`); si fos nullable, `NOT (instancia > '' AND NULL)`
donaria `NULL` i Postgres deixaria passar la fila per la porta del darrere.

---

## VEREDICTE

**FASE_2 POT ARRENCAR.**
