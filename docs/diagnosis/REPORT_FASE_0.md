# REPORT FASE_0 · PREVOL — TRAM INSTÀNCIA · 2026-08-02

**Veredicte: «FASE_1 POT ARRENCAR».**

---

## 0.1 · ENTORN

| Control | Resultat |
|---|---|
| `git log -1` | **`2ee5520064c58356efbe360594d6b7f0ccccf27f`** · 2026-08-01 07:14:53 +0000 · *«F4b · C7 reaplicat: la taula de mesures torna a ancorar les seves DUES fonts a l'exterior»* |
| branca | `dev` |
| `git status` | **cap fitxer de codi brut**. Modificat: `DECISIONS.md` (fitxer d'estat, mai a cap commit per llei del `CLAUDE.md`). Untracked: `AUDITORIA_DE_MODEL.md`, `MOTOR_DE_PATRONS_V2.md`, `PLA_IMPLEMENTACIO_MOTOR_PATRONS.md`, `backend/fhort/settings_step_tmp.py`, `backend/scripts_tmp/`, 12 docs de `docs/diagnosis/`, `docs/ordres/`, `fhort/`, `frontend/dist-tenants/`, `ops/*`. **Cap entrarà a cap commit d'aquesta tarda.** |
| `ftt-staging.service` | **active** |
| `/api/schema/` | **200** (743 057 bytes) |

## 0.2 · LECTURA FETA

`PLA_EXECUCIO_TRAM_C.md` sencer (93 línies) · `DOSSIER_INSTANCIA_POM.md` §I.A1, §II.10, §II.13, §II.14, §II.15, §II.16 · `MAPA_TOC_INSTANCIA.md` (índex) · `CLAUDE.md` + skill `patro-b`.

**Decisions retingudes que governen FASE_1** (no es reobren): columna `instancia` = `CharField(60)`, default `''`, NOT NULL, `db_index`, slug compost, **mai FK, mai choices** · va a **les mateixes 9 taules** que `capa` (§I.A1 #1-8 + `MeasurementChangeLog`) · **NO** a `ModelGradingRule` ni `GradingRule` (Montse: «graduen igual») · el default és **del MODEL, no de Postgres** (parany de C1).

## 0.3 · RE-CENS DELTA · `72d2e579` → `2ee55200`

**5 commits**, tots del 2026-08-01, tots dins del mateix tram de qualitat:

| hash | assumpte |
|---|---|
| `8bc9000b` | F1 · quina regla de graduació s'edita ja no el decideix el pla de Postgres |
| `2ef3cba5` | F2 · la llista de treball ja no perd l'ancoratge de la segona peça |
| `2d70b673` | F3 · el guard de la neteja LOSAN mirava cap a una altra banda davant d'un PROTECT |
| `864c8513` | F4a · l'ordre de la taula de mesures és una decisió, no el pla de Postgres |
| `2ee55200` | F4b · C7 reaplicat: la taula de mesures torna a ancorar les seves DUES fonts a l'exterior |

**9 fitxers de `backend/` tocats · 0 fitxers de `frontend/src/`.**

### Re-localització dels nodes del dossier

| Node | dossier | AVUI | veredicte |
|---|---|---|---|
| `patterns/views.py` · `BaseMeasurement.filter(model_id=fp.model_id, is_active=True)` **sense àncora capa** (forat #1 d'Onada 1) | `:552-556` | **`:590-595`** (`.filter` a `:592`) | **MOGUT** — forma idèntica; el forat segueix obert → node viu de FASE_2 |
| `patterns/views.py` · `ancorats = {p.pom_master_id: p …}` (bug viu B-1) | `:544-549` | `:576-587` | **CANVIAT — B-1 TANCAT** per `2ef3cba5`: `defaultdict(list)` + `order_by('pattern_piece_id','pk')` |
| `patterns/views.py` · comptador (FORA) | `:714` | `:739` | MOGUT |
| `patterns/views.py` · `_alies_unics_del_customer` (precedent de mètode) | `:135-146` | def `:151`, cos `:168-179` | MOGUT |
| `pom/grading_views.py` · mapa per `pom_id` (bloc D, «C7 revertit») | `:119-140` | **`:151-177`** | **CANVIAT** — C7 **reaplicat**: àncora `capa=SLUG_DEFECTE` a les dues portes (`:122-125` GradedSpec, `:154-156` BaseMeasurement). **Segueix sent node de FASE_2** (la clau de `cells`/`poms_seen`/`ordre_pom` continua sent `pom_id` sol) |
| `pom/s2_views.py` clonatge de regles (FORA) | `:221-231` | `:221-231` | IGUAL |
| `pom/s2_views.py` `.first()` sense ordre | `:282-288` | `:304-312` | CANVIAT (ordre determinista); segueix FORA |
| `pom/s4_views.py` `original_rules` (FORA) | `:292-300` | `:295-303` | MOGUT |
| `cleanup_losan_old.py` `SIZEDEF_EXTERNAL` (bug B-2) | `:32` | `:37` | **CANVIAT — B-2 TANCAT** per `2d70b673` |
| `models_app/test_lectors_capa_onada1.py` harness `comporta_alcada()` | `:35,:43-52,:84` | `:35-51`, `:84` | **IGUAL** — el diff és **purament additiu a partir de `:188`**; el harness queda més validat, no alterat |

### Nodes NOUS (no censats al dossier)

| fitxer:línia | tipus | per què importa |
|---|---|---|
| **`pom/grading_views.py:56-77` `clau_ordre_taula(pom, capa)`** | CONTRACT-order | 🟡 la clau d'ordre **ja porta `capa` dins**; amb instància la tupla ha de créixer o l'ordre torna a ser ambigu |
| **`pom/grading_views.py:111,:133,:161,:180` `ordre_pom`** | READ-dict per `pom_id` | 🔴 **novè germà** del cens de diccionaris per `pom_id` de la mateixa vista (germà de `cells` i `poms_seen`) — col·lapsa igual → **FASE_2** |
| `pom/grading_views.py:122-125` i `:154-156` | READ-list | 🟢 àncores `capa=exterior` NOVES (C7) |
| `pom/grading_views.py:184` | CONTRACT-api | 🟡 re-projecció de `cells` per `pom_id` |
| `patterns/views.py:74-101` `SENSE_ANCORATGE` / `_mesura_ancorada()` | HELPER-read | ⚪ extracció, cap clau nova |
| `patterns/views.py:636-640` camp `'ancoratges'` | CONTRACT-api | 🟡 ampliació compatible del payload |
| `pom/test_ordre_taula_mesures.py`, `pom/test_ordre_regla_grading.py`, `patterns/tests.py:3378-3410`, `test_lectors_capa_onada1.py:190-248` | tests | ⚪ no producció |

**Trampa B5 controlada:** `base_measurements` no apareix a cap dels 9 fitxers tocats. Els noms `base_for_items` / `base_set_for_items` de `cleanup_losan_old.py` són accessors inversos de **`SizeDefinition`**, no d'`ItemBaseMeasurement`.

### Veredicte del re-cens

**Cap node CANVIAT/DESAPAREGUT afecta l'esquema de FASE_1.** Els tres canvis de forma viuen fora de les 9 taules (`PatternPOM`, `GradingRule`) o **reforcen** la premissa (`grading_views` afegeix àncora de capa, i el propi codi declara a `:114-118` que la clau `pom_id` és contracte fins a C4). Els dos nodes tancats pel delta (B-1, B-2) eren precisament els que el dossier marcava «no tocar».

**Deltes a anotar per a FASE_2** (no bloquen): `ordre_pom` s'afegeix al bloc D · `clau_ordre_taula` ha de créixer amb instància · les línies de `patterns/views.py` i `grading_views.py` s'han de re-verificar al moment de tocar-les.

**Correccions al dossier (anotades, no aplicades):** §II.10:3933 ja no pot dir «C7 revertit» · §II.14 B-2:4268-4269 diu que `'base_for_items'` no existeix — **és inexacte**: existeix (`tasks/models.py:354`, `SizeDefinition`→`GarmentTypeItem`); el que hi faltava era `base_set_for_items` (`pom/models.py:672`, `ItemBaseSet`, PROTECT).

## 0.4 · EINES CLONADES (a `backend/scripts_tmp/`, fora de git)

| eina | origen | què s'ha canviat |
|---|---|---|
| `cins_audit_counts.sql` | `c1_audit_counts.sql` | columna `capa`→`instancia`, valor `'exterior'`→`''`; **+ bloc nou** `information_schema` (nullabilitat, default, longitud) per verificar que `ModelGradingRule` **NO** rep la columna |
| `cins_audit_constraints.sql` | `c1_audit_constraints.sql` | 6 blocs: **les DUES famílies de comportes** (`_capa_gate_c1` + `_instancia_gate_cins`) · recompte per schema i família · el CHECK «instància⇒nom» · les unicitats de les 8 taules amb eix · `ModelGradingRule`/`GradingRule` han de sortir **sense** instància · els índexs `db_index` |
| `onada1_dump_superficies.py` | **ampliat en el mateix fitxer** | +7 blocs `D1-D7` amb les superfícies de FASE_2/3 que l'Onada 1 no exercitava |

**Els 7 blocs nous del dump** (tots read-only, cap escriu):

| bloc | superfície | per què |
|---|---|---|
| `D1` | `pom/s6_views.pom_htm_view` | node de catàleg no cobert |
| `D2` | `pom/s8_views.export_fitting_csv_view` | node §II.10-A `s8_views.py:184-207` |
| `D3` | `pom/s11_views.model_alerts_view` | node §II.10-B `s11_views.py:165-171` |
| `D4` | `pom/nomenclatura.alies_per_pom` | node §II.10-D `nomenclatura.py:29-42` |
| **`D5`** | `patterns` `model-poms` | 🚨 **FORAT DE CAPA #1** de FASE_2 |
| **`D6`** | `tenants/federation_service._llegeix_patrimoni` | 🚨 **FORAT DE CAPA #2** de FASE_2 |
| `D7` | `federation_service._clau_natural_pom` × 40 POMs | FASE_3 la fa créixer a 4-tupla |

Execució de prova: **18/18 blocs presents, 0 `EXCEPCIO`**.

## 0.5 · CAPTURA T0 DE LA TARDA

| artefacte | fitxer | md5 |
|---|---|---|
| fumeig `base-stages` (models 467/548/182, **sense la 1a línia**) | `cins_fumeig_base_stages_T0_20260802.txt` | **`a14ce3ec1d47c1555fd8f3e59cae9a5f`** |
| dump de superfícies C1-C8 + D1-D7 (**sense la 1a línia**) | `cins_dump_superficies_T0_20260802.txt` (9 232 línies) | **`fd2eaebed9ad576ca52246b400cce265`** |
| OpenAPI | `cins_openapi_T0_20260802.yaml` | `4c950e1ba21668677c899f5503a981e2` |

**Nota sobre el md5 del fumeig:** el T0' del 31/07 era `6e3a980f624215f121ef6abe7ed7a8ae`. Difereix perquè la BD de staging ha rebut dades entremig — **no és una regressió**: el termòmetre d'aquesta tarda és `a14ce3ec…`, i és contra ell que es comparen T-final de cada fase.

**⚠️ Matís del green flag «OpenAPI: 0 ocurrències de `instancia`»:** a T0 ja n'hi ha **1**, i és un **homònim**: `openapi.yaml:9294`, dins d'un docstring en català (*«— instancia la pertinença de POMs de l'item»*, verb, no camp). El green flag s'ha de llegir com a **«segueix havent-hi exactament 1 ocurrència, i és aquesta»**.

### Pin i tests a T0

| control | resultat |
|---|---|
| `manage.py check` | net (implícit: el servei corre) |
| `test_base_stages_no_regressio` | **13/13 OK** ← el pin |
| `test_capa_comporta_c1` | OK |
| `test_lectors_capa_onada1` | OK |
| **total dels 3 mòduls** | **Ran 25 tests · OK** |

---

## VEREDICTE

**FASE_1 POT ARRENCAR.** Cap contradicció de paradigma, cap green flag vermell, cap node d'esquema mogut. Zero PENDENTs a FASE_0.
