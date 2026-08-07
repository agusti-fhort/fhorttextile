# REPORT · S36 · SUITE + `0073` + RESTART — 2026-08-07/08

> Staging `dev`. **Cap push.** Base: `REPORT_CAT2.md`.
> **Veredicte: la BD NO s'ha posat al dia i el restart NO s'ha fet.** Els dos passos estaven
> condicionats a una suite verda, i la suite ha sortit vermella per un test que és **del mateix
> tram que la `0073`**. Detall a §3.

---

## 1 · RECOMPTE FINAL DE LA SUITE

### Backend — `manage.py test fhort --noinput -v 2`

```
Found 1702 test(s).
Ran 1702 tests in 7266.973s
FAILED (errors=1)
CODI_BACKEND_REAL=1
```

⚠️ **El codi de sortida s'ha llegit de `$?` sobre la comanda directa, amb la sortida a fitxer.**
Cap `cmd | tail` i cap `grep "^(OK|FAILED)"`: a S35 això va donar un **fals verd** dues vegades
seguides, perquè el codi que arriba d'un pipe és el de l'**últim** procés, no el de la suite.

### Desglossament per app

Comptat des de les capçaleres de test de `-v 2` (`test_x (fhort.<app>.…)`), que és la mateixa
font que el total:

| app | tests | S35 (2026-08-06) | Δ |
|---|---|---|---|
| `models_app` | **567** | 556 | +11 |
| `patterns` | **378** | — | — |
| `tasks` | **238** | } 326 | } −1 |
| `fitting` | **87** | } | } |
| `pom` | **232** | 218 | +14 |
| `tenants` | **133** | — | — |
| `commerce` | **29** | — | — |
| `tests_auth_jwt` | **12** | — | — |
| `planning` | **7** | — | — |
| `backoffice` | **5** | — | — |
| **suma del desglossament** | **1.688** | | |
| **`Ran`** | **1.702** | 1.100 | **+602** |

🔵 **Els 14 de diferència** (1.702 − 1.688) són tests la capçalera dels quals no comença a
principi de línia perquè els precedeix la sortida d'un `print` del propi codi. No falten: no
els captura el patró d'ancoratge. El nombre que mana és el `Ran`.

🔑 **Per què el «793» de la correguda anterior no quadrava amb res, i per què el 1.702 sí.**
El 793 no era la suite: era `fhort.pom` + `fhort.models_app` i prou (232 + 567 = 799, ±els no
ancorats). I el **1.100 del segell de S35 tampoc era la suite sencera**: sumava només quatre
grups (`models_app` + `pom` + `tasks`+`fitting` = 1.100 amb el node a part). Les sis apps que
S35 no llistava —`patterns` 378, `tenants` 133, `commerce` 29, `tests_auth_jwt` 12, `planning`
7, `backoffice` 5 = **564**— són la major part del salt. **No hi ha cap encongiment a
explicar: el total és molt per sobre de l'ordre de S35.**

### Node — `node --test` sobre els 20 fitxers `*.test.js`

```
# tests 218   # pass 218   # fail 0
CODI_NODE_REAL=0
```

✅ **218/218.** El segell de S35 en deia 154 → **+64**. No hi ha runner al `package.json`
(`vitest`/`jest` no hi són): els tests fan servir el `node:test` integrat.

---

## 2 · ESTAT DE LA `0073` — auditoria SQL CRUA

Consultat a `information_schema.columns`, `pg_constraint` i `django_migrations` schema per
schema, **sense fiar-se de l'OK de Django** (`migrate_schemas` pot donar verd i deixar un
schema enrere). Schemes actius llegits de `public.tenants_client`: `public`, `fhort`, `los`.

### ABANS (i, com que el pas 2 no s'ha fet, també ARA)

| schema | migració registrada | `pom_garmentgrouppommap` | `pom_garmenttypepommap` |
|---|---|---|---|
| `public` | **NO** | no existeix (0/10 columnes) | no existeix (0/10) |
| `fhort` | **NO** | no existeix (0/10) | no existeix (0/10) |
| `los` | **NO** | no existeix (0/10) | no existeix (0/10) |

**La `0073` no ha aterrat diferent a cap schema: no ha aterrat a cap.** Mai s'ha corregut.

⚠️ **I el codi que la necessita ja és viu i encaminat**, cosa que converteix això en blocador
del restart i no només en deute:
- `fhort/pom/urls.py:33-34` — `GarmentTypePOMMapViewSet` i `GarmentGroupPOMMapViewSet`
  registrats al router (`/api/v1/garment-type-pom-maps/`, `/garment-group-pom-maps/`).
- `fhort/pom/acumulacio.py:68-70` — els consulta per construir la unió d'acumulació.

Un `systemctl restart` **abans** d'aplicar-la desplegaria dos endpoints que responen
`ProgrammingError: relation … does not exist`. Reiniciar ara no seria neutre: empitjoraria.

### ✅ `0069`→`0072` CONFIRMADES a BD

| migració | aplicada |
|---|---|
| `0069_cat21a_talla_base_label` | 06:53:56 |
| `0070_cat23_sizingprofile_unicitat` | 06:55:51 |
| `0071_cat2_baby_months_24_36` | 06:59:36 |
| `0072_cat22_sembra_garmentgroup` | 07:01:04 |

**El gunicorn viu és de les 06:08:52** — anterior a totes quatre. El desfasament que aquest
brief havia de tancar és real i segueix obert:

```
gunicorn 06:08  <  BD 0072 (07:01)  <  arbre 0073 (commit 07:29)
```

---

## 3 · 🛑 PER QUÈ S'ATURA — la suite no és verda

Un sol error, i **és del mateix tram que la `0073`**:

```
ERROR: test_una_relacio_CASCADE_no_bloqueja_pero_ES_DIU
       (fhort.pom.test_u2_acumulacio.POMUsIEsborratTest)

  File "fhort/pom/test_u2_acumulacio.py", line 279
    CustomerPOMAlias.objects.create(customer=cli, pom=pom, codi_client='XX')
TypeError: CustomerPOMAlias() got unexpected keyword arguments: 'codi_client'
```

**La causa és el parany de nomenclatura que la casa ja té documentat** (`codi_client` ≠
`client_alias` ≠ `pom_code_global` ≠ `nom_fitxa`). A `CustomerPOMAlias` el camp **no** es diu
`codi_client` sinó **`client_code`** (`fhort/pom/models.py:473`); `codi_client` és el camp
d'una altra taula (`POMMaster`, `GarmentType`).

🔑 **El que això vol dir, i per què no és cosmètic:** un `TypeError` per un kwarg inexistent no
és una regressió — **és un test que no ha passat mai**. La suite d'aquell tram no s'havia
corregut abans de commitar-lo. I és precisament el tram la migració del qual aquest brief havia
d'aplicar a staging.

**No l'he tocat**, per dues raons: el brief diu explícitament d'aturar-se i reportar, i la
correcció, tot i ser d'una línia, és **d'un tram que no és el meu i que a més té la pantalla
sense fer**. El desbloqueig, quan el seu amo el vulgui:

```python
# fhort/pom/test_u2_acumulacio.py:279
-   CustomerPOMAlias.objects.create(customer=cli, pom=pom, codi_client='XX')
+   CustomerPOMAlias.objects.create(customer=cli, pom=pom, client_code='XX')
```

---

## 4 · NOTA PER A M-FI · `grading_utils.py:747`

**Fitxer:** `backend/fhort/pom/grading_utils.py`, línia **747** · **Commit del fix:** `ab78b14f`
· **Commit d'origen:** `f92b56cd` (M-FI · M3 · `derivat_de_rule_set`).

La línia llegia `r.rule_set_id` amb **accés directe**. El docstring de la mateixa funció
(`rule_to_spec`), tres línies més amunt, diu:

> «Els specs de la DETECCIÓ (els del document del client) **no en porten**, i és correcte: no
> surten de cap joc.»

O sigui que la funció **declara legítim** un cas que després peta amb `AttributeError`. Va
provocar **3 errors** a la correguda anterior (`fhort.pom.test_d3_reclassificacio`, els tres la
mateixa línia). El fix és `getattr(r, 'rule_set_id', None)` — **la mateixa forma defensiva que
`pom` ja fa servir a la línia del costat**. `test_d3_reclassificacio`: 6/6 OK.

⚠️ Tocat fora del meu abast de tram, i a posta: deixava la porta del verd tancada per a tothom
i la correcció està avalada pel comentari del propi autor. Queda anotat aquí perquè ho sàpiga.

---

## 5 · PASSOS NO EXECUTATS (i per què)

| pas del brief | estat |
|---|---|
| 2 · `migrate_schemas` (aplicar `0073`) | 🛑 **no fet** — condicionat a la suite verda (pas 1) |
| 3 · auditoria SQL post-migració | 🛑 no fet — no hi ha res nou a auditar |
| 4 · `systemctl restart ftt-staging` | 🛑 **no fet** |
| 5 · `/api/schema/` + introspecció | 🛑 no fet |
| 6 · fums de navegador | 🛑 no fet |

**Res de tot això s'ha deixat a mitges: no s'ha començat.** L'estat de la BD i del servei és
exactament el que era en obrir el brief, i el `git` no té cap canvi meu pendent d'aquest tram.

---

## 6 · QUÈ DESBLOQUEJA TOT AIXÒ

Una línia (§3). Un cop aplicada i amb la suite verda, la resta és mecànic i segueix documentat:
`migrate_schemas` (mai `--schema`) → auditoria SQL als tres schemes → restart → `curl -H "Host:
staging.fhorttextile.tech"` contra `/api/schema/` → introspecció de migracions conegudes pel
procés nou → fums.

🚩 **La decisió que no és meva:** qui aplica aquesta línia. És el tram U1/U2, i el seu propi
report reconeix que la suite no s'hi havia corregut. Si em dius que la toqui, és un minut.

---

## 7 · SORPRESES

1. 🔴 **El «1.100» de S35 no era la suite sencera.** Sumava 4 grups d'apps de 10. Qualsevol
   comparació futura contra aquell número parteix d'una base incompleta: **el sostre real de
   `test fhort` és 1.702**, i el desglossament d'aquest report és el primer que el fixa app per
   app.
2. 🔴 **Dos trams seguits han commitat codi amb la suite sense córrer** (M-FI a §4, U1/U2 a §3).
   Els dos vermells eren d'una línia i els dos haurien sortit a la primera correguda.
3. 🔵 **El parany del pipe, pagat i documentat**: `cmd | tail` va donar `exit 0` sobre una suite
   amb 3 errors. Aquí tot va a fitxer i `$?` es llegeix directament.
4. 🔵 **La suite sencera triga ~2 h** (7.267 s). Val la pena saber-ho abans de planificar un
   tancament: no és un control que es pugui encabir «al final».
