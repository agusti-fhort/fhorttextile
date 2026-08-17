# ACTA E2 — les tres correccions de la QA d'E1, tancades

> **Patró B** · staging `dev` · **cap push** · 2026-08-17.
> Substrat: [`DIAGNOSI_E2_CORRECCIONS_QA.md`](DIAGNOSI_E2_CORRECCIONS_QA.md).
> 5 commits, un per concern. **1 migració** (decisió d'Agus, Patró C).

---

## VERMELL → VERD, amb números

| Banc | Abans | Després |
|---|---|---|
| `fitting.test_e2_b1_marca_de_presa` (7 tests) | 🔴 impossible d'escriure: **el camp no existia** | 🟢 **7/7** |
| `utils/cellaEscalat.test.js` | 🔴 **2 de 8** (afirmaven la llei vella «surt BUIDA») | 🟢 **9/9** |
| `utils/taulaPresaPerTalla.test.js` | 🔴 1 de 18 (la fàbrica es menjava `presa_at`) | 🟢 **18/18** |
| `fhort.fitting` (suite sencera) | — | 🟢 **178 tests OK** |
| Gates | — | `check` net · `makemigrations --check` «No changes» · `npm run build` net · **eslint 0 errors** · i18n **0/0** · restart amb `ActiveEnterTimestamp` mogut |

**El vermell d'E2b s'acredita DINS del banc** i no per una reversió temporal:
`test_confirmar_la_TEORICA_tal_qual_ES_una_presa` calcula el **predicat exacte d'abans** sobre
la mateixa línia i assereix que diu **FALS**. Si algun dia el predicat vell ja ho veiés, el
test cau i el camp sobra.

---

## E2a · fusió de columnes

TEÒRICA i PROPAGADA mostraven el mateix valor **per construcció**
([`cellaEscalat`](../../frontend/src/utils/cellaEscalat.js): `teorica = presa?.teoric ?? vigent`).
Ara: **Mesura · Fit actual**.

**El que no s'ha tocat**: `active.baseValue` segueix sent la teòrica → el vermell R1 no canvia
de significat i no s'encén sol després d'una propagació. Té banc que ho fixa.
`propagada` també surt del payload: només la llegia el seu propi banc.

i18n `escalat.col_mesura`: ca «Mesura» · en «Size» · es «Medida».

---

## E2b · pre-omplert fantasma — **la troballa del tram**

El brief demanava «confirmar sense canvi crea presa i `liniaTeContingut` la distingeix».
**Era impossible**: `PieceFittingLine` no tenia cap marca de gest i el predicat s'infereix de
`valor_real != valor_teoric` — i una línia **neix amb els dos iguals**. Confirmar la teòrica tal
qual produeix **exactament l'estat del naixement**.

→ Decisió d'Agus: camp **`presa_at`** (migració `0028`, additiva, **sense backfill**).
`linia_te_contingut` mira la marca **primera** i deixa la inferència **darrere** per a les files
velles. Auditat: **510 línies, 0 marcades, cap veredicte canviat**.

### 🚨 La trampa que això obria, tancada al mateix commit

La GUARDA-RAIL d'`onGridSave` («reescriure el valor que la cel·la ja té és un NO-OP») compara
amb `info.vigent`, i **amb el fantasma `info.vigent` ÉS la teòrica**. Confirmar hauria estat
engolit en silenci, amb l'usuari convençut que havia confirmat. La guarda ara distingeix:
**sense presa no hi ha res a estalviar**.

---

## E2c · la decisió dins d'Escalat — **VIA A**

El component de decisió **no és una pàgina**: és `CheckMeasureEditor` + `fittingSource`, i res
hi està clavat a la ruta. Es munta a `PropagatedEditor` amb els **mateixos props** i les
**mateixes portes de servidor**. Cap component nou, cap contracte paral·lel.

La sessió va **prima** (`{id}` i prou): `resolvePieceFitting` només llegeix `fittingSession.id`.
L'únic que la pantalla aporta de nou és el **rellotge** (`open-task` de `size_check`, un sol
cop); si falla, el panell es queda obert i es diu — el que es perd és el compta-temps, no la feina.

La barra R5 deixa de navegar; el chevron passa de **destí** (dreta) a **plec** (avall/amunt) amb
`aria-expanded`.

### El bug del deep-link, i per què s'ha arreglat en comptes de retirar-lo

`?tab=Mesures&fitting_session=<id>` **sense `task_id`** dispara **dos efectes independents**
—resoldre la sessió i obrir la tasca + `setEditing`— i el render queia a
`source={fittingSession ? … : null}`. Si guanyava el segon, es pintava la font `check` en mode
treball: **la taula de Definició POM amb els deltes**, amb el rellotge de `size_check` al damunt.
Sense error i sense res que ho digués.

La llei ja era escrita **370 línies més amunt** al mateix fitxer («val més no entrar que entrar
a una ALTRA taula que se li assembla») i s'aplicava **només al botó ③**. Ara també al camí per
URL — que és el que fan servir **la fulla de convocatòria i el redirect de `/fittings/<id>`**.
**El forat era més ample que la porta que el va destapar**, i per això no s'ha retirat: s'ha
tancat.

---

## VERIFICACIÓ CONTRA EL SERVEI DESPLEGAT (banc 1380, peça 45)

Presa oberta amb 6 línies, totes nascudes amb `valor_real == valor_teoric` i `presa_at = NULL`.

| línia | talla | garment | teòric | real | marca | què és |
|---|---|---|---|---|---|---|
| 1398 | M | mare | 60 | 60 | **f** | 🫥 naixement — **NO és presa** |
| 1397 | M | `02` | 60 | 60 | **t** | ✅ **confirmada sense canvi** |
| 1400 | S | mare | 58 | 50 | **t** | ✅ tocada amb un valor diferent |
| 1399·1401·1402 | — | — | — | =teòric | f | 🫥 fantasma |

**Dues files amb números idèntics (60/60) i significat oposat, distingides només per `presa_at`.**
És exactament el cas que abans no existia, mesurat contra el gunicorn desplegat.

Lectura de tancament: `n_preses = 2 de 6`, i el payload serveix `real: null` als fantasmes i
`real` + `desviacio` a les preses (`desv=0.0` a la confirmada — **desviació zero ≠ no mesurat**).

---

## LÍMITS I DEUTE

1. **El panell d'E2c no té banc automàtic**: `node --test` no pot importar `.jsx`. Està cobert
   per `npm run build`, eslint i pel fet de ser **el mateix component** que el tab Mesures ja
   exercita. El cicle sencer (decidir → close → propagar) el cobreix `fhort.fitting` a nivell de
   servei, no de pantalla. **QA visual pendent d'Agus.**
2. **El bug del deep-link no s'ha reproduït en viu** (és una cursa entre dos efectes). El fix
   aplica una llei ja escrita al mateix fitxer; la causa és lectura de codi.
3. **No s'ha verificat** si la fulla de convocatòria i el redirect de `/fittings/<id>` passen
   `task_id`: l'acta de `ModelSheet:752` diu que no i s'ha pres per bona.
4. 🚩 **Queda al banc 1380**: sessió 156, peça 45, amb 2 preses. És el banc viu d'aquesta
   verificació. Esborrar-lo és decisió d'Agus.
5. **`presa_at` no s'emet al payload de la cel·la**: la pantalla el dedueix de `real == null`.
   Funciona i és el contracte mínim, però el dia que una superfície vulgui dir **quan** es va
   prendre, caldrà emetre'l. Anotat, no fet.
