# P0.5d — LA GRADUACIÓ ÉS UNA SUPERFÍCIE PRÒPIA

> Tram del 06/08. Decisió d'Agus a pantalla: graduar no és la taula de Gravar POM amb quatre
> columnes més. Triar joc al contenidor (P0.5a) no porta a Definició POM: porta a una pantalla
> pròpia. Cap push — els commits són locals a `dev`.

## Commits

| # | hash | què |
|---|---|---|
| 36 | `577e66f7` | `taula-mesures` diu d'on ve la regla de cada fila (`regla_origen`) |
| 39 | `36db7e55` | la superfície: `GraduacioSuperficie.jsx` + navegació `?mode=graduacio` + i18n ×3 |
| 40 | `06eeb4f2` | P0.5d.4 · les columnes de graduació surten de Definició POM |
| 41 | `0f18e149` | el fum de navegador de la superfície + el fixture (model 169) |

Els commits 37 i 38 (`3d53d8d6`, `68b7cee7`) són d'una **sessió concurrent** que corria alhora
(P0.3 · les quatre accions del tab Mesures). Es va rellegir el fitxer abans de cada edició, tal
com la frontera del brief demanava; el commit 37 va deixar el botó «Graduació» entrant pel
circuit de tasca i una nota que deia *«quan la pantalla nova de P0.5d existeixi, el que canvia
és on porta —no com s'hi entra»*. És exactament el que s'ha fet: no s'ha tocat l'entrada.

---

## 🔴 EL PUNT QUE L'AGUS HA DE DECIDIR — el criteri de verificació del brief no es pot complir

El brief demanava, com a test anti-31/07:

> Gravar → F5 → només les 2 tocades són residents (SELECT a BD per confirmar que **NO hi ha 12
> residents**)

**Aquest recompte no és assolible, i no per res que faci aquesta pantalla.** Assignar un joc ja
materialitza regles residents abans que ningú obri la superfície:

`update_model_step2` (`backend/fhort/models_app/views.py:1067-1088`) crida
`materialize_model_grading_rules` (`backend/fhort/models_app/services.py:264`), que fa
**wipe-and-recreate: una `ModelGradingRule` resident per CADA regla del joc**, tinga el model
aquell POM o no. Comprovat a la BD de staging: **tots** els models amb `BRW-CATALEG-v3` assignat
tenen exactament **114 residents**, que són les 114 regles del joc. El MILEY (1308) inclòs.

Conseqüència per a la lectura del brief:

- «fila resolta pel joc» és, a la BD, **una resident materialitzada des del joc** — no una regla
  del joc llegida en directe. `_load_grading_rules` (`backend/fhort/pom/services.py:722`) és
  **tot-o-res**: si el model té una sola resident activa, el joc queda completament fora.
- per tant «una fila no tocada resolta pel joc segueix sent del joc (cap resident nou)» ja es
  compleix per una altra via: la fila **ja era** resident, i el que cal és **no tocar-la**.

**L'observable correcte, que sí que mesura la llei, és `origen`.** Els dos escriptors de regla
posen `origen='MANUAL'` en editar; la sembra des del joc posa `CLIENT_RUN`/`CANONICAL`/`IMPORTED`.
O sigui: *després de gravar, les regles amb `origen='MANUAL'` han de ser exactament les files que
l'usuari ha tocat, i cap més ha de canviar*. És un test **més estricte** que el recompte, perquè
també detecta que se n'hagi tocat una que no tocava.

Executat (`backend/scripts_tmp/p05d_anti3107.py`, model 169, dins d'un `atomic` que es desfà —
zero residu):

```
residents: 114 → 115        (+1: només la fila que no en tenia)
origen MANUAL: 2 → [273, 279]   (exactament les 2 tocades)
CLIENT_RUN: 113                 (la resta, intacta)
✓ VERD · cap regla sembrada a cap fila no tocada
```

🚩 **Decisió per a l'Agus:** el wipe-and-recreate de l'assignació de joc és de disseny (el 409
D-31.4 hi està construït a sobre) i **no s'ha tocat** — queda fora de l'abast d'aquest tram. Si
el que es volia de debò és que assignar un joc **no** materialitzi res i que el model gradui pel
joc fins que algú n'editi una fila, això és un canvi de paradigma al motor, no a la pantalla.

---

## 🔴 ERROR MEU, JA REVERTIT: vaig escriure al MILEY

El brief acabava amb «MAI el MILEY». Vaig fer el primer test end-to-end **sobre el model 1308,
que és el MILEY**, abans de llegir-ho a `ops/qa/qa_p02_fixture.py:6` (que ho diu explícitament).
Dues escriptures reals: `pom 420` (delta 1,00 → 1,25) i `pom 440` (regla nova).

**Revertit a l'estat exacte de partida** (`backend/scripts_tmp/p05d_revert.py`), incloent-hi
`updated_at`, i verificat per l'API:

```
MILEY 1308 · files: 12 · plenes: 7 · buides: 5 · origens: ['CLIENT_RUN']
  pom=420 A.2 → LINEAR db=1.0 brk=1.5 @XS origen=CLIENT_RUN   (original)
  pom=440 U1  → sense regla                                    (original)
residents: 114 · {'CLIENT_RUN': 114}
```

El test es va refer sobre el model **169**, i des d'aleshores tota la QA d'aquest tram corre
amb transacció que es desfà o amb l'API estubejada. El fixture nou (`qa_p05d_fixture.py`) porta
el mateix guard que el de P0.2: es nega a tocar el 1308.

---

## Què s'ha construït

### La pantalla · `frontend/src/components/grading/GraduacioSuperficie.jsx`

Mateixa família de taula que la v8.1 (la tipografia 9,5/12,5 px i els mateixos tokens), amb la
feina d'aquí:

- **files**: capa · POM · **nom amb el valor de talla base enganxat**, en lectura. Aquí no es
  canvien mesures: cap carril editable de valor, cap columna d'instància.
- **germanes**: hi surten com a files amb el seu nom compost, però **la regla és del POM** —
  `ModelGradingRule` no porta capa ni instància (decisió de domini amb acta). Les edicions
  s'agrupen per `pom_id`: **una sola crida** encara que la germana ocupi tres files.
- **a partir del valor**: RÈGIM · DELTA · DELTA BREAK · TALLA BREAK, editables.
- **columna «Ve de»**: «del joc» o «del model», llegint el `regla_origen` del commit 36.
- **capçalera de context**: model · joc assignat · talla base · run, amb el botó que obre el
  contenidor de tria (P0.5a).
- **«Gravar Graduació»**, paral·lel a «Gravar POM».

**L'escriptura no estrena res.** Va per `set_pom_regim_view`
(`POST /models/<id>/pom/<pom_id>/regim/`), que ja era un upsert amb actualització selectiva per
presència de camp. Cap circuit nou: el que faltava era la pantalla.

**La llei del 31/07, al codi.** El payload surt del Map `edicions`, que neix buit i on només hi
entra el que un gest humà ha canviat. Es recorren **les edicions, mai les files** — que és la
diferència exacta amb el bug del 1302, on el payload es construïa recorrent les files pintades.
Una fila no tocada no té entrada al Map i no genera cap crida.

**LINEAR degenerada** es mira al front (mirall de `es_linear_degenerada`) perquè es vegi a la
fila i no en un toast després d'haver premut Gravar.

### Navegació

`?mode=graduacio`, dins del paràmetre `mode` que ja existia en comptes d'estrenar-ne un. Això li
dona l'F5 i la porta per on P0.4 hi farà arribar la tasca. El comentari de `ModelSheet.jsx:45`
que deia que la graduació *«no té paràmetre d'URL»* s'ha actualitzat.

**L'entrada manual deixa d'amagar-se.** Ja no encén cap bandera de sessió (`graduacioManual`,
que un F5 perdia): porta a la superfície **sense joc assignat**, amb totes les files editables
des de zero. Que no hi hagi joc *és* el que vol dir «a mà», i això sí que sobreviu l'F5.

### P0.5d.4

Se'n va de Definició POM tot el que P0.5b hi havia posat: la prop `mostraGrading` i el seu pas a
`SortableRow`, capçaleres, cel·les, el sumand de `colCount` i `COLS_GRADING`. **La consulta
(Taula de mesures) les manté en lectura**, exactament com P0.5b la va deixar.

---

## Verificació

| control | resultat |
|---|---|
| `manage.py check` | net |
| `npm run build` | net |
| `eslint` (fitxers tocats) | **0 errors** |
| i18n ca/en/es | paritat · 22 claus × 3, idèntiques |
| `qa_p05d_graduacio.py` (nou) | ✓ 3 idiomes · consola neta · 29 files · 13 amb règim · comptador «1 de 29» |
| `qa_mount_modelsheet.py` | ✓ |
| `qa_p01_valors.py` | ✓ |
| `qa_p02_definicio_pom.py` | ✓ |
| `qa_p02b_cercador.py` | ✓ |
| `qa_p03_consulta_mesures.py` | ✓ (ja no és vermell: el va tornar a verd el commit 38 de la sessió concurrent) |
| `qa_p06_botons_mesures.py` | ✓ |
| anti-31/07 contra BD | ✓ 114→115 · 2 MANUAL · 113 intactes · zero residu |
| `test_g1_graduacio` (el test-pin del 31/07) | ✓ **Ran 7 tests · OK**, inclòs `test_desar_mesures_dun_model_sense_graduacio_no_len_inventa_cap` |

| `fhort.pom` (suite sencera) | ✓ **Ran 208 tests · OK** (825 s) |

Dues trampes de mètode que van costar temps i que val la pena deixar escrites:

- **`cmd | tail` amaga el codi de sortida.** Una correguda de tests que havia mort per
  `timeout` va donar `exit 0` perquè el codi que arriba és el del `tail`. Es va repetir amb
  redirecció a fitxer i `echo $?` abans de creure-se-la.
- **Dues corregudes de test alhora es trepitgen el `--keepdb`** (llei ja coneguda). La primera
  va morir per `timeout 900` i va deixar la BD de test a mitges → `relation
  "pom_rulesetscopenode" already exists`. Se'n surt amb `--noinput`, que la recrea.

El fum va **caçar un error d'expectativa meu** abans que cap humà el veiés: en anglès la columna
és «Delta break», no «Break delta».

---

## Anotat, fora d'abast (no s'ha tocat)

1. 🚩 **`es.json` diu «Talla break»** a `editable_table.col.talla_break` — català dins del
   castellà. Ve de P0.5b, no d'aquest tram. En anglès sí que està bé («Break size»).
2. 🚩 **`set_pom_regim_view` no toca `actiu`.** Si una resident té `actiu=False`, l'endpoint
   retorna 200 però `_load_grading_rules` la filtra: l'edició no arriba al motor. La germana del
   joc (`GradingRuleViewSet.update`, `backend/fhort/pom/views.py:308-330`) tanca aquest cas amb
   un 409 explícit; aquí no hi ha el guard.
3. 🚩 **`RegleEditCell`** (`CheckMeasureEditor.jsx:153`) envia sempre `logica:'LINEAR'` i desa a
   l'`onBlur`, canviï o no el valor: tabular per un camp pot flipar un règim. És l'altra
   superfície que escriu regles i no s'ha tocat.
4. **STEP**: la superfície deixa triar el règim però no edita `valors_step` (una llista per
   talla). Les cel·les de delta es desactiven i ho diuen. Si cal editar-los, és pantalla a part.

## Què ha de fer el CTO

- Revisar la cadena amb `git show 577e66f7 36db7e55 06eeb4f2 0f18e149`.
- **Decidir el punt 🔴 de dalt**: el recompte de residents del brief contra el que fa
  l'assignació de joc.
- Push des d'SSH quan doni el vistiplau.
