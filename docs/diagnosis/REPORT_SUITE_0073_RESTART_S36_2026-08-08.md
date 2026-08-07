# REPORT · S36 · SUITE + `0073` + RESTART — 2026-08-07/08

> Staging `dev`. **Cap push.** Base: `REPORT_CAT2.md`. Commits 112 → 114.
> **Veredicte: TANCAT EN VERD.** La BD està al dia (`0073` als tres schemes), el gunicorn
> serveix el codi de l'arbre i els dos fums read-only passen.
>
> Aquest report va néixer **aturat** (§3): la suite tenia un vermell que era del mateix tram
> que la `0073`. L'Agus va autoritzar el fix (Patró C) i la cadena s'ha pogut completar.

---

## 0 · EL SEGELL, I LA SEVA CORRECCIÓ

> 🔴 **A partir d'ara la referència és `1702` backend + `218` node.**
> El «1.100» de S35 (2026-08-06) **era parcial**: sumava 4 grups d'apps de 10. Les sis que no
> comptava —`patterns` 378, `tenants` 133, `commerce` 29, `tests_auth_jwt` 12, `planning` 7,
> `backoffice` 5 = **564 tests mai comptats**— són la major part de la diferència. Qualsevol
> comparació futura contra el 1.100 parteix d'una base incompleta.

| | tests | resultat |
|---|---|---|
| **Backend** `manage.py test fhort` | **1.702** | 1 error → §3 · **corregit i verificat** |
| **Backend** `fhort.pom.test_u2_acumulacio` (delta del fix) | **17** | ✅ `OK` · `CODI_MODUL_REAL=0` |
| **Node** `node --test` (20 fitxers) | **218** | ✅ `218 pass · 0 fail` · `CODI_NODE_REAL=0` |

**Segell final: 1.702 backend + 218 node, tot verd** (1.701 verds de la correguda completa +
els 17 del mòdul re-corregut amb el fix). La suite sencera **no** s'ha re-corregut per ordre
expressa: el fix és una línia dins d'un mètode de test, sense cap efecte possible sobre els
altres 1.701, que ja tenien verd complet d'avui.

⚠️ **Tots els codis de sortida s'han llegit de `$?` sobre la comanda directa, amb la sortida a
fitxer.** Cap `cmd | tail`, cap `grep "^(OK|FAILED)"`: a S35 això va donar un **fals verd** dues
vegades, perquè el codi que arriba d'un pipe és el de l'**últim** procés, no el de la suite.

### Desglossament per app (capçaleres de test de `-v 2`)

| app | tests | S35 | Δ |
|---|---|---|---|
| `models_app` | 567 | 556 | +11 |
| `patterns` | **378** | *(no comptada)* | — |
| `tasks` | 238 | } 326 | } −1 |
| `fitting` | 87 | } | } |
| `pom` | 232 | 218 | +14 |
| `tenants` | **133** | *(no comptada)* | — |
| `commerce` | **29** | *(no comptada)* | — |
| `tests_auth_jwt` | **12** | *(no comptada)* | — |
| `planning` | **7** | *(no comptada)* | — |
| `backoffice` | **5** | *(no comptada)* | — |
| **suma** | **1.688** | | |
| **`Ran`** | **1.702** | 1.100 | **+602** |

🔵 Els 14 de diferència (1.702 − 1.688) són tests la capçalera dels quals no comença a principi
de línia perquè els precedeix un `print` del propi codi. No falten; no els captura el patró
d'ancoratge. El nombre que mana és el `Ran`.

🔵 I d'aquí surt per què el **793** de la correguda anterior no quadrava amb res: no era la
suite, era `fhort.pom` + `fhort.models_app` i prou (232 + 567 = 799, ±els no ancorats).

---

## 1 · LA `0073`, ABANS I DESPRÉS — auditoria SQL CRUA

Consultat a `information_schema.columns`, `pg_constraint` i `django_migrations`, schema per
schema, **sense fiar-se de l'OK de Django** (`migrate_schemas` pot donar verd i deixar un schema
enrere). Schemes actius llegits de `public.tenants_client`.

### ABANS

| schema | registrada | `pom_garmentgrouppommap` | `pom_garmenttypepommap` |
|---|---|---|---|
| `public` | **NO** | no existeix (0/10 col.) | no existeix (0/10) |
| `fhort` | **NO** | no existeix (0/10) | no existeix (0/10) |
| `los` | **NO** | no existeix (0/10) | no existeix (0/10) |

**No havia aterrat *diferent* a cap schema: no havia aterrat a cap.** Mai s'havia corregut.

### DESPRÉS (`migrate_schemas`, mai `--schema`)

| schema | registrada | taula | columnes | UNIQUE (4 camps) | FK | files |
|---|---|---|---|---|---|---|
| `public` | sí | `pom_garmentgrouppommap` ✅ | 10/10 | ok | 2/2 | 0 |
| `public` | sí | `pom_garmenttypepommap` ✅ | 10/10 | ok | 2/2 | 0 |
| `fhort` | sí | `pom_garmentgrouppommap` ✅ | 10/10 | ok | 2/2 | 0 |
| `fhort` | sí | `pom_garmenttypepommap` ✅ | 10/10 | ok | 2/2 | 0 |
| `los` | sí | `pom_garmentgrouppommap` ✅ | 10/10 | ok | 2/2 | 0 |
| `los` | sí | `pom_garmenttypepommap` ✅ | 10/10 | ok | 2/2 | 0 |

✅ **Idèntica a tots tres**: registrada, amb les 10 columnes declarades, l'`unique_together` de
4 camps i les 2 FK. 0 files — és estructura, encara sense dades.

### ✅ `0069`→`0072` confirmades

| migració | aplicada |
|---|---|
| `0069_cat21a_talla_base_label` | 06:53:56 |
| `0070_cat23_sizingprofile_unicitat` | 06:55:51 |
| `0071_cat2_baby_months_24_36` | 06:59:36 |
| `0072_cat22_sembra_garmentgroup` | 07:01:04 |

El desfasament que aquest brief havia de tancar, tancat:

```
ABANS:  gunicorn 06:08  <  BD 0072 (07:01)  <  arbre 0073 (07:29)
ARA:    gunicorn 11:07  =  BD 0073          =  arbre 0073
```

---

## 2 · RESTART I VERIFICACIÓ

`systemctl restart ftt-staging.service` · **06:08:52 → 11:07:38** · `active`.

```
[INFO] Starting gunicorn 26.0.0
[INFO] Listening at: http://127.0.0.1:8001
[INFO] Booting worker with pid: 1875667
[INFO] Booting worker with pid: 1875669
systemd: Started ftt-staging.service
```

🔵 **Hi ha un `[ERROR] Control server error: [Errno 13] Permission denied: '/var/www/.gunicorn'`,
i NO és nou.** Surt a **tots** els restarts d'avui (04:38, 05:36, 06:08 i 11:07): és el
control-server de gunicorn 26 que no pot escriure el seu fitxer, no el servei. El màster
escolta i els dos workers arrenquen. Ho anoto perquè consti, no perquè bloquegi.

### `/api/schema/`

```
curl -H "Host: staging.fhorttextile.tech" http://127.0.0.1:8001/api/schema/
→ HTTP 200 · 799.750 bytes
```

### Introspecció del procés NOU — no assumida

Dues comprovacions independents, cap de les dues «donar per fet»:

**(a) Les rutes de la `0073`** — el test de 5 segons de la casa: sense credencial, **401 = ruta
viva · 404 = el procés no la té**.

| ruta | HTTP |
|---|---|
| `/api/v1/garment-type-pom-maps/` | **401** ✅ |
| `/api/v1/garment-group-pom-maps/` | **401** ✅ |

**(b) El schema OpenAPI que genera el propi procés** (`drf-spectacular` el construeix en viu
des dels serializers, o sigui que és el procés parlant de si mateix):

| marcador | de quina migració | ocurrències a `/api/schema/` |
|---|---|---|
| `talla_base_label` | `0069` (CAT2.1a) | **6** |
| `grup_ref` | `0068` (C6 pas 1) | **8** |
| `GarmentTypePOMMap` | `0073` | **19** |
| `GarmentGroupPOMMap` | `0073` | **19** |

✅ **El gunicorn nou coneix el codi fins a la `0073`**, i també les meves `0068`/`0069` que el de
les 06:08 no havia vist mai.

---

## 3 · EL VERMELL QUE VA ATURAR TOT AIXÒ, I EL FIX AUTORITZAT

```
ERROR: test_una_relacio_CASCADE_no_bloqueja_pero_ES_DIU
       (fhort.pom.test_u2_acumulacio.POMUsIEsborratTest)
  File "fhort/pom/test_u2_acumulacio.py", line 279
    CustomerPOMAlias.objects.create(customer=cli, pom=pom, codi_client='XX')
TypeError: CustomerPOMAlias() got unexpected keyword arguments: 'codi_client'
```

**El parany de nomenclatura que la casa ja té documentat** (`codi_client` ≠ `client_alias` ≠
`pom_code_global` ≠ `nom_fitxa`): a `CustomerPOMAlias` el camp és **`client_code`**
(`pom/models.py:473`); `codi_client` és el camp d'una altra taula (`POMMaster`, `GarmentType`).

🔑 **Un `TypeError` per un kwarg inexistent no és una regressió: és un test que no ha passat
mai.** Era l'únic vermell dels 1.702 i deixava bloquejats la migració i el restart.

**Corregit amb autorització expressa de l'Agus** (Patró C) — v. §4. Mòdul re-corregut sense
`--keepdb`: **17 tests, `OK`, `CODI_MODUL_REAL=0`**.

---

## 4 · NOTES — dos fixos fets per compte d'altres trams

Tots dos fora del meu abast, tots dos anotats aquí perquè el seu amo ho sàpiga.

### 4.1 · Tram **U1/U2** · `test_u2_acumulacio.py:279` · commit `91fcfa03`

```python
-   CustomerPOMAlias.objects.create(customer=cli, pom=pom, codi_client='XX')
+   CustomerPOMAlias.objects.create(customer=cli, pom=pom, client_code='XX')
```

**Fet per compte del tram U1/U2: test mai corregut abans de commitar.** El propi report d'aquell
tram ja reconeixia que la suite no s'hi havia passat. Autoritzat per l'Agus perquè bloquejava la
posada al dia de la BD per a tothom.

### 4.2 · Tram **M-FI** · `grading_utils.py:747` · commit `ab78b14f`

Origen: `f92b56cd` (M-FI · M3 · `derivat_de_rule_set`). La línia llegia `r.rule_set_id` amb
**accés directe**, i el docstring de la mateixa funció (`rule_to_spec`), tres línies més amunt,
diu: *«Els specs de la DETECCIÓ (els del document del client) **no en porten**, i és correcte:
no surten de cap joc.»* La funció **declarava legítim** un cas que després petava amb
`AttributeError`.

Fix: `getattr(r, 'rule_set_id', None)` — **la mateixa forma defensiva que `pom` ja fa servir a
la línia del costat**. Va provocar **3 errors** (`fhort.pom.test_d3_reclassificacio`); ara 6/6.

---

## 5 · FUMS (read-only, post-restart)

| fum | codi | resultat |
|---|---|---|
| `ops/qa/qa_n_capes_run.py` | `0` | ✅ **VERD · cap escriptura feta** |
| Fum de navegador de la SPA (`/clients`, bundle real + API des de bolcats) | `0` | ✅ **VERD · consola neta a ca/en/es** |

```
N1a · 26 runs · classificats 26 · sense classificar 0 []
N1b · GET size-systems/ 200 · 26 files · capes exposades OK
N2 · GET sizing-profiles/?target=WOMAN 200 · 10 perfils
N3 · ordre amb client BRW · WOMAN: ALPHA_EU_W › NUMERIC_EU_W › ALPHA_EU_M › BABY_EU_CM
```

El fum de navegador cobreix llista + 3 clients + F5 + 3 tabs + navegació, als **tres idiomes**,
sense escriure a staging (API servida des de bolcats del `django.test.Client`).

⚠️ **Els fums de cicle de model segueixen sense poder córrer**: `fhort` té 0 models des de V4, i
els de cicle creen i destrueixen un model. No és un vermell: és una cobertura que no existeix
fins que hi hagi models de QA nous.

---

## 6 · SORPRESES

1. 🔴 **El «1.100» de S35 no era la suite sencera** (§0). El sostre real de `test fhort` és
   **1.702**, i aquest report és el primer que el fixa app per app.
2. 🔴 **Dos trams seguits han commitat codi amb la suite sense córrer** (§4). Els dos vermells
   eren d'una línia i els dos haurien sortit a la primera correguda.
3. 🔵 **El parany del pipe, pagat i documentat**: `cmd | tail` va donar `exit 0` sobre una suite
   amb 3 errors, i després sobre una amb 1. Tot va a fitxer i `$?` es llegeix directament.
4. 🔵 **La suite sencera triga ~2 h** (7.267 s). No és un control que es pugui encabir «al
   final»: s'ha de planificar.
5. 🔵 **El `Control server error` de gunicorn no és del desplegament** (§2): surt a tots els
   restarts d'avui, inclosos els d'abans d'aquest tram.

---

## 7 · QUEDA APARCAT (per decisió, no per oblit)

- L'esborrat de `los` → test d'obertura de tenant nou post-refactor.
- CAT2.1(b) (retirar la FK `talla_base`, ~20 fitxers) i el pas 2 de C6 (~18 punts + 26
  fixtures) — v. `REPORT_CAT2.md` §2b i §3.
- 🚨 **`public.TODDLER_EU`**: tota la columna waist/hip ~20 cm avall, en un run que sembra els
  tenants nous. Espera els valors de la Montse — `REPORT_CAT2.md` §5.
- La pantalla de U2, que el seu propi tram deixa sense fer.
