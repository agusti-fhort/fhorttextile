# TANCAMENT — S24b: l'ordre i la distància de talles els mana el SizeSystem

**Data:** 2026-07-22 vespre · **Patró B** · staging `/var/www/ftt-staging`, branca `dev`
**Llei:** `DECISIONS.md:20-39` (S24b, Agus) · **Diagnosi base:** `DIAGNOSI_ORDRE_RUN_MODEL_2026-07-22.md`
**7 commits locals. CAP PUSH** — els fa l'Agus des d'SSH.

---

## Pre-vol

Aquest sprint anava darrere del Patró B «referent-document». En arrencar, aquell sprint havia
crescut de 3 a **8 commits** i l'últim havia aterrat 4 minuts abans, amb el ritual de tancament
incomplet i la llei encara absent del `DECISIONS.md` → **STOP i report**. Un cop l'Agus va abocar
la llei S24b al `DECISIONS.md` (16:15), els dos blocadors van quedar resolts: la llei hi és
textual, i l'actualització del `DECISIONS.md` és el ritual de tancament de sessió d'aquell sprint
(tots 7 talls aterrats, arbre sense canvis de codi pendents).

⚠️ **Queda pendent d'aquell sprint, no d'aquest:** `DIAGNOSI_REFACTOR_WIZARD_RUN_CLIENT_2026-07-22.md`
segueix a l'arrel de `docs/diagnosis/` sense segellar ni moure a `arxiu/`, tot i estar implementada.

---

## Els 7 commits

| # | Hash | Focus |
|---|---|---|
| 1 | `e7a55fd` | Helper únic `run_del_model` — germà de `run_del_document`. Pur, sense cridadors. 13 tests. |
| 2 | `99abf76` | Porta única d'escriptura: `_resolve_garment_def` (cobreix create-wizard **i** update-step2), extraction, tech_sheet, bulk_import. Etiqueta fora del sistema = 400 amb llista. 7 tests. |
| 3 | `092bcdd` | Tanca la via 7: `ModelDetailSerializer.validate()`. El CRUD genèric ja no accepta un run cru. 4 tests. |
| 4 | `224b88d` | **MOTOR en espai de sistema**: `escala_del_model` + `_apply_rule` amb el run del SISTEMA. 25 tests. |
| 5 | `33f4359` | Frontend: el toggle de chips deixa de ser ordre de clic; `orderedSizes` deixa de viure duplicat. |
| 6 | `5b4b03f` | Command `normalitza_size_run` (dry-run per defecte) + categoria `NO_CONTIGU` al cens. |
| 7 | `a137111` | i18n-gate: `model_wizard.unknown_sizes` amb paritat ca/en/es. |

20 fitxers, +1419/−54. `manage.py check` net i `npm run build` net a cada commit.

---

## Q1 — PARITAT (condició dura del permís de motor)

**✅ VERDA: 745 cel·les comparades, ZERO diferències.**

Mètode: `generate_graded_specs` executat **abans** i **després** del commit 4 sobre tots els models
del tenant `fhort` que graduen, cada un dins `transaction.atomic()` amb rollback forçat, bolcant
`(pom_id, size_label) → (valor, tipus_aplicat, increment)` a JSON i comparant clau a clau.

| model | codi | run | cel·les |
|---|---|---|---|
| 162 | BRW-SS26-0001 | XS·S·M | 42 |
| 163 | BRW-FW26-0001 | XS·S·M·L | 96 |
| 174 | BRW-FW26-0012 | XS·S·M·L | 36 |
| 185 | FTT-FW27-0001 | XS·S·M·L·XL·XXL·3XL | 14 |
| 186 | FTT-CO27-0001 | S·M·L·XL·XXL | 100 |
| 188 | BRW-SS27-0001 | XXS·XS·S·M | 40 |
| 268 | BRW-FW27-0001 (Blusa POP) | XXS·XS·S·M·L | 100 |
| 269 | BRW-FW27-0002 (POP) | XXS·XS·S·M·L | 125 |
| 396 | LOS-SS27-0122 | 03/06 … 24/36 | 120 |
| 467 | LOS-SS27-0193 | 03/06 … 24/36 | 72 |
| | | **TOTAL** | **745** |

Els 10 tenen el run **ordenat i contigu** (verificat contra `SizeDefinition.ordre`), i per això la
paritat ha de ser exacta **per construcció**: sobre un run contigu, les talles del sistema que el
camí travessa són exactament les del run, i el break es desplaça igual als dos costats de la
comparació. El càlcul no ha canviat; només el referent.

**Risc de paritat detectat i acotat abans d'escriure:** 60 regles dels models 162 i 188 tenen
`talla_break_label='XXL'`, una talla que és al SISTEMA però no al run. Abans el motor no la trobava
al run → cap break. En espai de sistema sí que la troba, però queda a l'índex 6 i tot el recorregut
d'aquests runs és per sota → el llindar no dispara ni abans ni després. Zero cel·les afectades.

> Nota sobre el brief: el golden «267 / [QA-S10], 105 cel·les» **no existeix com a tal** — el model
> 267 no té cap `BaseMeasurement` i per tant no gradua. Els models POP reals són el **268** (100
> cel·les) i el **269** (125), tots dos dins el conjunt de paritat. El 267 sí s'ha fet servir per a
> la reproducció de Q3, que és el que demanava.

## Q2 — Casos nous del motor

**✅ 25 tests nous** (`fhort/pom/test_espai_de_sistema.py`), purs i sense BD:

- **Robustesa a l'ordre**: el run `XS·S·L·XXS·M` dona resultats **idèntics** al canònic
  `XXS·XS·S·M·L` per a LINEAR, LINEAR canònic (`increment_base`), LINEAR-amb-break i STEP.
- **El símptoma concret**: XXS = 94.0 (abans 106.0, amb el signe invertit); amb break a L, XXS =
  94.0 i L = 109.0 (abans 112.0 i 106.0).
- **No contigu**: `XS·S·L` amb `increment_base=3` i base S → **L = 106.0** (DOS passos).
- **Break a una talla que el model no fabrica**: break a M sobre `XS·S·L` → L = 112.0 (el camí la
  travessa; el llindar és un concepte del sistema).
- **Guards de `escala_del_model`**: etiqueta fora del sistema, base fora del run i sistema sense
  talles peten amb missatge clar; el run desordenat **no peta**, es normalitza en memòria.
- El test de retrocompatibilitat que ja existia (`test_propaga.py::test_retrocompat_vs_apply_rule`)
  segueix verd.

### Criteri STEP sobre run no contigu (decisió tècnica delegada al brief)

**El camí es recorre sobre les talles del SISTEMA.** Un model amb run `XS·S·L` que gradua cap a L
travessa la M, i per tant **necessita el delta de la M encara que no la fabriqui**. Si el delta hi
falta, la cel·la queda **ABSENT** (`None` + warning), mai a zero ni col·lapsada.

El raonament: la llei diu que la distància la mana el sistema. Si acceptéssim STEP sense el delta de
la talla travessada, hauríem de decidir què val aquell tram — i qualsevol tria (zero, interpolar,
reutilitzar el veí) seria inventar-se un número que ningú ha declarat. És exactament la llei D2 de
cel·la absent que ja regia aquí: **una regla que no cobreix un tram no gradua aquell tram; no
n'emet**. La conseqüència pràctica és que un STEP sobre un run no contigu demana els deltes de totes
les talles del tram — que és el que ja demanava el costat de la derivació després de la S24.

## Q3 — Reproducció del 166

**✅** Sobre el model de QA **267** (`[QA-S10] Blusa RUFUS STARS`, run `XS·S·L`, base S), executant
la vista real `update_model_step2` dins `transaction.atomic()` amb rollback forçat:

```
PAYLOAD: {'size_system_id': 29, 'size_run': 'XS·S·L·XXS', 'base_size': 'S'}
HTTP   : 200
PERSISTIT (dins tx): XXS·XS·S·L          ← ordenat, no apendat
MOTOR  : run=['XXS','XS','S','L'] base_idx=2 steps={XXS:-2, XS:-1, S:+0, L:+2}
5XL    : HTTP 400 {'error': '…: 5XL', 'codi': 'talles_desconegudes',
                   'etiquetes_desconegudes': ['5XL']}
>> ROLLBACK fet
DESPRÉS: run=XS·S·L base=S  (intacte)
```

Els dos defectes de la diagnosi, morts a la mateixa línia: **XXS ara és `-2`** (abans `+2`, amb el
signe invertit) i **L ara és `+2`** (abans `+1`, distància col·lapsada pel forat de la M).

## Q4 — Regressió

**Vermells PREEXISTENTS, no d'aquest sprint** (verificat amb `git stash`, arbre net, mateixa
falla): 24 errors a `fhort.pom.test_g6_grading_gates` i `fhort.pom.test_g6_segell`, tots amb la
mateixa causa —
`IntegrityError: duplicate key value violates unique constraint "fitting_sizefitting_model_id_numero_6dc01a35_uniq"`
en el muntatge dels tests. Cap relació amb l'ordre del run. **🚩 Bandera: algú els ha de mirar.**

Resultat de la suite sencera: vegeu §Q4-final al peu d'aquest document.

---

## Estat de les dades a staging

| | |
|---|---|
| Cens (`fhort`, 1004 models amb run) | **990 OK · 14 NO_CONTIGU · 0 DESORDENAT · 0 ETIQUETA_FORA** |
| `normalitza_size_run --schema=fhort` (dry-run) | 1004 ja ordenats · 0 desordenats · res a fer |

Els **14 NO_CONTIGU** són tots `XS·S·L` del lot Brownie (models **164-175**, inclòs el **166**).
Són runs **legítims** i no s'han de reparar. Però fins avui graduaven amb la distància col·lapsada,
i per tant **els seus `GradedSpec` anteriors al commit 4 són incorrectes**: la L els va sortir a un
pas de la S en comptes de dos. La re-propagació és decisió per model (D-10) i aquest sprint no n'ha
tocat cap.

---

## 🚩 Banderes per al CTO

1. **Els 14 models `XS·S·L` volen re-propagació conscient.** El motor ja els compta bé, però ningú
   ha regenerat les seves cel·les. Cal decidir model a model, mirant abans si tenen `GradingVersion`
   aprovada (el command ho marca a l'informe).
2. **24 tests vermells preexistents** a `test_g6_grading_gates` / `test_g6_segell` per una violació
   d'unicitat de `SizeFitting` al setup. No són d'aquest sprint i no s'han tocat.
3. **`propaga_ancoratges`** (`grading_utils.py`) camina el run que li passen i arrossega **el mateix
   supòsit de contigüitat** que acabem de treure del motor. Fora d'abast del brief; anotat.
4. **`talla_break_pos`** segueix sent un cache derivat de la posició dins el run i pot mentir.
   Inert avui (el motor resol el break per etiqueta), com deia la diagnosi. Fora d'abast.
5. **`tech_sheet_views` crea models sense `SizeSystem`** i per tant la porta única hi degrada a
   «conserva l'ordre del document». El dia que aquest camí assigni sistema, s'ordenarà sol.
6. **Deute de presentació**: `orderedSizes` ordena pel run desat, no pel sistema. Equivalent avui
   (el backend garanteix el run ordenat), però una API que exposés les etiquetes del `SizeSystem` a
   `fitting/serializers.py::get_model` ho faria correcte per construcció.
7. **Sistema amb dues etiquetes que canonicalitzen igual** (p. ex. un `SizeSystem` que tingués
   alhora `XXL` i `2XL`): el mapa `canonical_size_label → posició` les col·lapsa i guanya
   l'última. `run_del_document` (S24) té exactament el mateix comportament, i
   `extraction_views` sí que en porta detecció explícita (`_canon_ambig`). Cap sistema del
   tenant hi cau avui. No s'ha tocat: unificar-ho demanaria moure la detecció d'ambigüitat al
   pont, i això afecta els dos eixos alhora.
8. **PROD**: el cens (§4.2 de la diagnosi) i `normalitza_size_run` estan llestos i **no s'han
   executat contra PROD**, on viu el 166 real amb `XS·S·L·XXS·M`.

---

## Per a l'Agus

```bash
git log --oneline dee7998..HEAD        # els 7 commits d'aquest sprint
git show 224b88d                       # el del motor — el que vol més ull
git push                               # des d'SSH, quan la cadena et convenci
```
