# REPORT — Fix del desat de fitxa (.ftt): desat idempotent + poda

Data: **2026-08-02** · Fase B de `DIAGNOSI_DESAT_FITXA.md` · staging `/var/www/ftt-staging`, branca `dev`
Base: HEAD `277cb9e0` · **Cap push** (el fa l'Agus).

## 🔑 COMMIT ÚNIC PER AL CHERRY-PICK A PROD

```
2fac0fcaaa7a7a957e0ffb6aecac4dc7ade7d768
fix(ftt): desat idempotent + poda de la cadena de versions .ftt
```

**4 fitxers, tots de backend, cap del tram instància / C1:**

```
backend/fhort/models_app/services_ftt.py           +43 −3
backend/fhort/models_app/services_ftt_document.py  +150 −5
backend/fhort/models_app/test_desat_fitxa_poda.py  +291   (nou)
backend/fhort/models_app/test_ftt_n_fitxes.py      +10 −4
```

**Cap migració.** `makemigrations --check` → «No changes detected». El cherry-pick no arrossega
esquema ni cap dependència de C1/instància.

---

## B0 · VERIFICACIÓ PRÈVIA — el `confdeltype` real

La diagnosi ho deixava com a sospita. **Confirmada: totes NO ACTION.**

```sql
SELECT c.conname, c.confdeltype FROM pg_constraint c
JOIN pg_class t ON t.oid=c.conrelid JOIN pg_namespace n ON n.oid=t.relnamespace
WHERE c.contype='f' AND n.nspname='fhort'
  AND pg_get_constraintdef(c.oid) LIKE '%models_app_modelfitxer(id)%';
```

| FK entrant | ORM diu | **BD diu** |
|---|---|---|
| `models_app_modelfitxer.versio_anterior_id` | `SET_NULL` | **`a` = NO ACTION** |
| `models_app_modelfitxer.generat_des_de_id` | `SET_NULL` | **`a` = NO ACTION** |
| `models_app_modelfitxer.derivat_de_model_id` | `SET_NULL` | **`a` = NO ACTION** |
| `models_app_fttdocumentlock.document_root_id` | `CASCADE` | **`a` = NO ACTION** |

Totes `DEFERRABLE INITIALLY DEFERRED`. Idèntic a `fhort` i a `los`.

**Per què**: Django **no declara mai** `ON DELETE` a l'esquema — emula `SET_NULL`/`CASCADE` al
collector de l'ORM. Un `DELETE` en cru (o un `queryset.delete()` massiu amb ordre equivocat)
peta. Per això el sanejament de PROD d'avui va necessitar deslligar primer, i per això el codi
de poda **no confia en l'ORM**: re-enganxa, deslliga i després esborra, explícitament.

**Decisió B0:** l'ordre d'esborrat és 1) re-enganxar la frontera a l'arrel · 2) `UPDATE ... = NULL`
de TOTES les referències entrants · 3) `DELETE` de les files · 4) esborrar els bytes.

---

## Decisions preses (i per què)

### D1 · Sense camp nou i sense migració
El brief obria la porta a afegir un `CharField(64)`. **No cal:** el manifest del `.ftt` **ja
persisteix** l'empremta lògica (`manifest['checksums']`, `services_ftt.py:73-85`) i
`save_document` **ja feia** `load_document(head)` per fusionar assets. La comparació no costa ni
una lectura de més. Menys superfície i cherry-pick sense coordinació d'esquema amb PROD.

### D2 · L'empremta és LÒGICA, mai el blob
`services_ftt.empremta_logica()` reutilitza el càlcul que `pack` ja feia (cap hash duplicat).
La raó, que és la troballa central de la Fase A: `zipfile.writestr` estampa la data-hora a cada
entrada → el sha del blob **no es pot repetir**. Fixat amb un test que ho explica
(`test_el_checksum_del_blob_no_serveix_per_comparar`) perquè ningú no "simplifiqui" la
comparació cap a `ModelFitxer.checksum` en el futur.

### D3 · La poda va a `save_document`, no a `save_model_file`
`save_model_file` el comparteixen imatges, PDFs, patrons, exports i federació. Posar-hi poda de
TECHSHEET seria mal escopat i arriscat. `save_document` és l'únic punt que encadena versions
de fitxa des de l'editor.

### D4 · L'ARREL no es poda I la cadena es re-enganxa ⚠️ *(fora del brief; necessari)*
El brief deia «conserva qualsevol amb `fttdocumentlock`». Però el lock penja de l'**arrel**
(la v1, via `document_root()`), i **protegir-la com a fila no serveix de res si la cadena es
trenca**: `document_root()` camina `versio_anterior` i s'aturaria a la versió conservada més
antiga. El lock es perdria i **el desat següent seria un 403** per a qui està editant.
Per això la frontera es re-enganxa a l'arrel.

**Conseqüència aritmètica:** el sostre real és **21 recents + arrel = 22 files**, i el primer
esborrat arriba a la 23a, no a la 22a com deia el brief. Fixat a la constant `SOSTRE` del test.

### D5 · La poda no pot tombar un desat
Va dins d'un `try/except` que loga `ERROR` (mai en silenci). El desat de l'usuari ja és a la BD
i no se li pot fer perdre per una fallada de manteniment; la cadena es podarà al desat següent.

### D6 · `test_el_desat_PRESERVA_el_nom_al_llarg_de_la_cadena` — actualitzat
Verificat: el seu 2n desat reenviava **el mateix `doc`**, sense canvi → amb el fix no crearia la v3.
**Triat: afegir-hi un canvi real**, no rebaixar l'expectativa a 1. El seu docstring diu que
defensa que **el nom sobreviu la cadena**, no el recompte de versions; amb un 2n canvi real
segueix provant els DOS salts. Rebaixar-lo hauria convertit un test de noms en un test
d'idempotència duplicat, i la idempotència ja té 7 tests propis. Documentat al seu docstring.

**Un altre que semblava en risc i NO ho està:** `test_ftt_asset_embut.py:139` fa un 2n desat
sense bytes, però només assereix que **l'asset sobreviu** — cert igualment amb el desat
idempotent (mateixa fila, mateixos assets). No s'ha tocat.

---

## GREEN FLAGS

| Control | Resultat |
|---|---|
| `manage.py check` | ✅ «System check identified no issues (0 silenced)» |
| `makemigrations --check --dry-run` | ✅ «No changes detected» (cap migració) |
| `test_desat_fitxa_poda` (nou) | ✅ **19/19** |
| Pin `test_base_stages_no_regressio` | ✅ **13/13** |
| **Suite completa, des de ZERO (sense `--keepdb`)** | ⚠️ **1367 tests · 53 errors · 0 fallades** |

### La frase per al deploy

> **Suite = 1314 passats · 53 vermells = preexistent `SizeFitting numero=1` (28/07) · 0 vermells
> atribuïbles al fix.**

**Els 53 tenen TOTS la mateixa signatura** (106 línies al log = 53 errors × 2, psycopg2 + wrapper):

```
psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint
"fitting_sizefitting_model_id_numero_6dc01a35_uniq"
DETAIL:  Key (model_id, numero)=(3, 1) already exists.
```

Repartits en **29 a `fhort.fitting`** (el compte documentat el 28/07) i **24 a `fhort.pom`**
(`test_g6_grading_gates` + `test_g6_segell`, que també creen SizeFittings — no surten quan es
corre `fhort.fitting` sol, per això la xifra coneguda era 29).

**Els 24 de `pom` verificats A/B, no argumentats:**

```
amb el canvi:  Ran 24 tests ... FAILED (errors=24)
git stash push -- (els 3 fitxers modificats)
sense el canvi: Ran 24 tests ... FAILED (errors=24)
git stash pop
```

Idèntic → preexistent.

**Llista nominal dels 29 de `fhort.fitting`:**
`test_g6_estalitud.EstalitudTest` ×7 · `test_g6_estalitud.AvisAlMotorTest` ×3 ·
`test_g6_estalitud.R7UnaSolaActivaTest` ×3 · `tests.PropagarActionTest` ×16.

**Dues signatures més al log que NO són errors de test** (comprovat: cap `ERROR:` associat):
`models_app_aiusage does not exist` (8 línies — logs `ERROR` de `extraction_utils`, capturats
dins de tests que passen; taula absent al schema de test, deute d'infra a part) i
`models_app_model_codi_intern_key` (2 línies, també dins de tests verds).

**Cap dels meus tests apareix com a error a la suite** (`test_desat_fitxa_poda`,
`test_ftt_n_fitxes`, `test_ftt_asset_embut`: cap `ERROR:`).

---

## ⚠️ NOTA DE MÈTODE — tota execució de test tallada ENVERINA la BD de test

Això m'ha costat **tres execucions** i val la pena que quedi escrit.

`TenantTestCase` crea el tenant `test` a `setUpClass` i el destrueix a `tearDownClass`. Si el
procés mor a mig camí (SIGTERM per `timeout`, per límit d'entorn, per `kill`), **la fila queda**.
L'execució següent no falla de manera òbvia: **menteix ràpid i barat** — 400 tests en 48 s amb
165 errors, tots a `setUpClass`, tots

```
UniqueViolation: duplicate key ... "tenants_client_schema_name_key"
DETAIL:  Key (schema_name)=(test) already exists.
```

**El parany de lectura:** consultar `tenants_client` i veure `test | 1` sembla net («un de cada,
cap duplicat»). **No ho és.** El tenant `test` és efímer per disseny: **en repòs no hi ha d'haver
CAP fila**. La pregunta correcta no és «hi ha duplicats?» sinó «hi ha cap fila `test`?».

**Recepta (sobre `test_ftt_staging`, MAI `ftt_staging`), a executar ABANS de córrer, no després
de sospitar:**

```sql
DELETE FROM public.tenants_client WHERE schema_name='test';
DROP SCHEMA IF EXISTS test CASCADE;
-- verificar: 0 files i cap schema 'test'
```

**Dades de durada, per no repetir el diagnòstic erroni:** la suite completa honesta són
**1367 tests en 5.171 s (86 min)** perquè cada `TenantTestCase` reconstrueix el schema `test`
sencer. Els «400 tests en 48 s» d'una execució enverinada són ràpids **precisament perquè**
tots els `setUpClass` peten a l'instant i cap schema arriba a construir-se. **Velocitat sobtada
= sospita d'enverinament, no de bon rendiment.**

Cal llançar-la **desacoblada** (`setsid nohup ... &`): un `timeout` propi o el límit de la
sessió la mataran, i cada mort torna a enverinar la BD.

**Bonus verificat:** la construcció des de ZERO (`--noinput`, sense `--keepdb`) **ja NO peta a
`pom/0013`** — va completar les 1367. El deute d'infra anotat a `REPORT_FASE_1.md` sembla
resolt; val la pena reconfirmar-ho abans de donar-lo per tancat.

---

## Radi i límits declarats

- **NO s'ha tocat** `TechSheetEditor.jsx`: **B3 queda pendent** (el client segueix disparant un
  PATCH per gest; ara la majoria seran no-ops barats, però el desat en va segueix creuant la
  xarxa). És el següent pas natural i **no** és a aquest commit.
- **La poda actua en desar.** Les cadenes ja acumulades **no es poden soles**: es podaran al
  primer desat de cada document. Les fitxes que ningú torni a obrir es queden com estan —
  a PROD ja s'ha sanejat a mà avui, però **staging encara té 604 files TECHSHEET / 665 MB**
  (model 163 amb 113 versions).
- **No s'ha executat res contra dades reals de staging**: tota la verificació és sobre la BD de
  test. La poda no s'ha provat contra una cadena de 495 versions com la del model 205 de PROD;
  el test més llarg n'encadena 35.
- **`FTT_VERSIONS_A_CONSERVAR = 20`** viu al mòdul (`services_ftt_document.py`), no a settings.
  Si es vol per-entorn, és un canvi a part.
