# FIX F2 · el `garment` al `set_size_override_view` · 2026-08-25

> Worktree **`/var/www/ftt-f2`**, branca `f2-garment-override`, base `dev` `55e76c5d`
> (M4+M5-dia ja fusionats, `64832c43`). **2 commits, CAP PUSH.**
> PAS -1: `hostname` = `fhort-assessment` · `WorkingDirectory=/var/www/ftt-staging/backend`. ✅

---

## 🚨 0 · UNA CORRECCIÓ AL CENS, ABANS DE RES

El brief parteix de la fila 9 del `CENS_INSTANCIES_POM_2026-08-25.md`, i **aquella fila
exagerava el defecte en dues coses**. Totes dues s'han descobert construint el banc, i totes
dues estan mesurades.

### (a) La ruta és JUBILADA: el defecte no és abastable per HTTP

`set-size-override/` **no té ruta** des de D5 (21/07): `models_app/urls.py:238` la declara
retirada i `fitting/test_e1_r2_estructural.py` és un **guardià de frontera** que comprova que
segueix sense resoldre (5 tests, verds avui). El cens va escriure un gest d'usuari —«torna a la
taula propagada i edita la mateixa talla»— que **no existeix**: aquella columna va canviar de
porta a E1/B4 i ara anota una PRESA.

La vista viu com a **vehicle de bancs** (ja la fa servir `pom/test_g6_segell.py:117`), i els
seus únics cridadors avui són tests. És la lliçó de `ftt-acta-al-codi-pot-mentir` aplicada al
meu propi cens d'aquest matí: **no en vaig verificar la ruta**.

### (b) El símptoma NO és el 500 — és mut, i n'hi ha tres

El cens deia «`MultipleObjectsReturned` → 500». Mesurat amb el lookup revertit, el que passa
de debò és, per ordre de probabilitat:

| # | Condició prèvia | Què passa SENSE el fix | Mesurat |
|---|---|---|---|
| 1 | la mare té fila, s'escriu a la **02** | `update_or_create` casa la fila de la MARE i **li reescriu el valor**. Una fila, cap error, **200 OK** | `AssertionError: 1 != 2` |
| 2 | només la **02** té fila, s'escriu a la **mare** | li fa UPDATE **a la fila de la 02**: la mare no arriba a tenir fila i la 02 es queda amb el número de la mare | `self._ovr(MARE)` és `None` |
| 3 | les **DUES** files ja escrites | `get() returned more than one ModelGradingOverride -- it returned 2!` | `MultipleObjectsReturned` |

**El 500 és el cas 3, i és el menys assolible**: aquesta porta tota sola **no pot fabricar mai**
la segona fila (el cas 1 se n'encarrega). Les dues files només les pot deixar l'ALTRE camí, el
germà `escalat_ajustar_talla_view` — que **també té la ruta jubilada**. O sigui que el cens
també s'equivocava en dir que el pas 1 del seu «cas concret» era assolible.

**La conseqüència real, doncs, és corrupció silenciosa creuant peces**, no una caiguda. Que és
el mode de fallada dolent: una caiguda es veu.

---

## 1 · EL FIX · `48088b27`

Un sol fitxer de producció, `backend/fhort/models_app/views.py`, i el `garment` entra als
**QUATRE** punts del camí — no a un:

| punt | línia | per què |
|---|---|---|
| lookup de l'`update_or_create` | `:3415` | és el que alinea la clau amb la unicitat real (6 col.) |
| lectura de `prev` | `:3409` | el valor d'abans ha de ser el D'AQUESTA peça |
| `MeasurementChangeLog.create` | `:3430` | taula **APPEND-ONLY i sense unicitat**: una fila mal atribuïda no es pot corregir després |
| lectura de retorn del `GradedSpec` | `:3459` | tenia **tres** columnes de sis: amb una germana viva, el `.first()` sense `order_by` podia servir el `graded_value_cm` d'una ALTRA mesura amb un 200 OK |

El valor surt del punt únic **`_identitat_de_mesura`** (`models_app/views.py:2246`), que és qui
decideix què rep qui no el diu i qui ja tracta un `None` explícit com el valor buit (la columna
és `NOT NULL` amb default). **Se'n pren només el tercer eix.**

**Contracte:** `Body: {pom_id, size_label, valor, garment?}`. Qui no l'envia rep `''`, la peça
MARE — el comportament d'avui **byte a byte** per a tot model d'una sola peça i per a tot client
antic, que no el sabrà enviar mai.

**Additiu:** la resposta ara diu `'garment'`, perquè qui l'envia pugui comprovar on ha aterrat.

### ⚠️ Què NO fa aquest fix, i és deliberat

`capa` i `instancia` **segueixen sent literals** en aquesta porta. No és un oblit: el fix obre
UN eix, el que tenia el defecte, i amb el `garment` al lookup la clau ja és la `unique` sencera
—cap `update_or_create` d'aquest camí pot tornar a casar dues files—. Que aquesta porta no
sàpiga adreçar una GERMANA D'INSTÀNCIA és una limitació coneguda i separada (mateix cens, files
12-13). Obrir-la és una altra decisió i un altre tram.

**Tampoc es re-endolla la ruta.** El guardià segueix verd.

---

## 2 · EL BANC · `models_app/test_f2_garment_override.py`

**13 tests**, `TenantTestCase`, i crida la **VISTA** —no una URL— per la raó de §0(a). La
fixture és la forma exacta dels tres parells vius de `fhort` (1320/904, 1379/962, 1380/962): un
model amb el MATEIX POM mesurat a DUES peces, versió **no** segellada, i **valors base
diferents** a cada peça (40 i 30) perquè una trepitjada no es pugui confondre amb un encert.

| classe | què tanca |
|---|---|
| `DuesPecesDuesFilesTest` (6) | el cas del brief + **els tres símptomes** de §0(b), un test per cadascun |
| `ElContracteDelSentinellaTest` (3) | `''` per defecte · `None` explícit val com absent · la resposta diu la peça |
| `ElRastreParlaDeLaPecaCorrectaTest` (3) | el log porta el garment · `valor_anterior` és el D'AQUESTA peça · la lectura de retorn no torna el graded de la germana |
| `UnaSolaPecaComportamentIdenticTest` (2) | **el 100% del corpus d'avui**: idempotència d'una fila, i dues talles conviuen |

### 🔑 El banc està VERIFICAT VERMELL, no només verd

Un test de regressió que passa abans i després no val res. Amb el lookup revertit
(`DuesPecesDuesFilesTest`): **4 failures + 2 errors de 6**, i l'error del cas 3 és literalment
`ModelGradingOverride.MultipleObjectsReturned: get() returned more than one ... it returned 2!`.
Restaurat el fix: verd.

---

## 3 · EL GATE — proporcional, i què s'hi ha inclòs

| control | resultat |
|---|---|
| `manage.py check` | **net** (0 issues) |
| `fhort.models_app.test_f2_garment_override` (el nou) | inclòs |
| `fhort.pom.test_g6_segell` (l'altre usuari de la vista) | inclòs |
| `fhort.fitting.test_e1_r2_estructural` (**el guardià de la ruta**) | inclòs |
| `fhort.models_app.test_base_stages_no_regressio` | inclòs |
| `fhort.tasks.test_ronda` (**bloc RONDA**) | inclòs |
| **TOTAL** | **111 tests · OK · 426 s** |

**CAP SUITE.** La de nit és el gate del tren i el validarà sencer. La correguda ha anat amb
`FTT_TEST_DB=test_ftt_f2` (`settings_test`, M5) perquè no xoqui amb cap altra sessió, i amb
`setsid nohup` perquè el wrapper de background mata a 10 min.

> ⚠️ La BD `test_ftt_f2` va quedar mig creada per un primer intent que va topar amb el límit de
> 2 min del wrapper; es va **esborrar i refer** abans de la correguda bona (la lliçó de la suite
> morta a mitges, que deixa `schema_name='test'` i dona errors aliens).

---

## 4 · QUÈ QUEDA PER A L'AGUS

1. **El merge a `dev`** — cap push des d'aquí, tal com mana el brief.
2. **La correcció del cens ja està aplicada** a
   `/var/www/ftt-staging/docs/ordres/CENS_INSTANCIES_POM_2026-08-25.md` (fila 9 + el §I2), que
   és el document que anirà a la formació. Sense això, el brief de demà arrossegaria un «500»
   que no existeix i un gest d'usuari que tampoc.
3. **La decisió de fons que aquest fix NO pren:** si `set-size-override/` ha de tornar a tenir
   ruta mai. Avui és una vista sense porta que es manté per als bancs; el fix la deixa correcta
   per si algú l'endolla, però **endollar-la és exactament el que R2-estructural prohibeix**.
4. 🚩 **La germana d'instància segueix sense porta** en aquest camí (cens, files 12-13), i
   `MeasurementBaseGrid` continua amb el seu defecte viu (cens, fila 10) — que **sí** té
   pantalla i **sí** és el gest de la formació. Aquell no s'ha tocat.
