# REPORT FASE_3 · ONADA 2 — ELS ESCRIPTORS ESTAMPEN ELS DOS EIXOS · 2026-08-02

**Veredicte: «FASE_4 POT ARRENCAR».** 10 commits · **el fet estructural del dossier està
mort** · 1 canvi de forma, declarat i mandatat · 2 PENDENTs.

---

## EL FET ESTRUCTURAL QUE AQUESTA FASE MATA

El dossier (§II.10) deia: *«cap escriptor de tot el repo passa mai `capa` a un lookup ni a un
`defaults`. Els únics 6 hits de `capa=` fora de `models.py` són filtres de LECTURA. Tot
escriptor viu del default del model, protegit només per les comportes.»*

El cens executable d'aquesta fase el va confirmar sense excepcions: **34 escriptors, 0 amb
`capa`, 0 amb `instancia`.** Avui:

```
escriptors trobats sobre les 9 taules: 29
SENSE els dos eixos: 1   ← fals positiu: `bulk_create(maps, …)`, i els objectes de `maps`
                            porten els dos eixos al constructor, 8 línies més amunt
constructors directes sobre les 9 taules: 5 · sense els dos eixos: 2   ← tots dos, PROSA
                            de docstring («PieceFittingLine (per PieceFitting = …)»)
```

**Cap escriptor de les 9 taules deixa cap dels dos eixos al default implícit.**

---

## ELS 10 COMMITS

| # | hash | què desarma |
|---|---|---|
| F3-1 | **`e33f3ff7`** | 🚨 **l'accident de C4**: `_upsert_graded_spec` deia 3 columnes d'una clau de 5 |
| F3-2 | **`dd2b274f`** | la línia de fitting clona l'spec → també n'ha de clonar els eixos; + `consolidate_base_from_fitting` |
| F3-3 | **`25628518`** | 🚨 **el signal F1**: el forat que arrossega des de l'Onada 1, i la taula és append-only |
| F3-4 | **`4eca4ffb`** | 🚨 **el pitjor cas del cens**: `_materialize_lines` + `resolve_size_check` |
| F3-5 | **`d3999ab1`** | l'upsert de `POMPlacement` i el d'`ItemBaseMeasurement` manual |
| F3-6 | **`b41286b5`** | `models_app`: sembra, promoció, còpia, altes manuals, overrides, i **la poda per FILA** |
| F3-7 | **`d8e740c9`** | les tres portes d'entrada de document (import, fitxa de proveïdor, wizard) |
| F3-8 | **`f53eb725`** | 🚨 **la federació**: clau natural a 4 trams + versionat del paquet |
| F3-9 | **`79314af5`** | els sembradors: `bootstrap_tenant` (el deute de C1) + les 4 portes de catàleg |
| F3-10 | **`e8848258`** | harness d'escriptors + **els dos asserts que ara es poden estrènyer** |

**CAP PUSH.** Cap fitxer de `docs/` dins de cap commit. `git add` de paths explícits a tots deu.

## EL CONTRACTE, APLICAT

**COPIA quan hi ha d'on copiar.** El signal F1 (de la `instance`, que ÉS la `BaseMeasurement`
que ha canviat) · la línia de fitting (de l'spec) · la consolidació i el veredicte del check
(de la línia) · les línies del check (de la mesura) · la sembra item→model (del
`GarmentPOMMap`, que és el portador de la pertinença) · la còpia model→model (de la font) · la
promoció model→item (de la mesura que la justifica) · el `bootstrap_tenant` (de la fila
d'origen, per `_concrete()`).

**DECLARA amb el literal del cas** quan el contracte d'entrada no els porta: tot el que rep
`pom_id` per HTTP (alta manual, `set-measurements`, acció IA, overrides de talla i els seus dos
rastres al log, l'acte canònic, la cota, el valor típic d'item) i tot el que llegeix un format
que encara no en sap (import, fitxa de proveïdor, wizard, paquet LOSAN, mapa inline,
consolidació de catàleg).

**L'argument sencer viu UNA vegada**, al docstring de `_write_base` (`models_app/views.py`), i
els altres punts del fitxer hi apunten amb una línia. La diferència amb el que hi havia no és
cosmètica: amb el lookup curt, un `update_or_create` sobre una família de dues germanes o bé
n'agafa una a l'atzar o bé peta amb `MultipleObjectsReturned`; amb el lookup complet sap
exactament sobre quina escriu — i quan C4-ins obri el contracte, el lloc on posar el valor real
ja hi és: només canvia d'on ve.

**LA PODA I L'ESBORRAT SÓN PER FILA, no per POM.** `keep_pom_ids` (les dues podes bessones) i
el `delete()` d'overrides s'ancoren: amb dues germanes vives, podar per POM en mataria una que
ningú no ha tret de la taula — un esborrat silenciós, que és el mode de fallada que tot el tram
existeix per matar.

### Els tres nodes de disseny, no de mecànica

1. **`_upsert_graded_spec`** — els eixos són **paràmetres amb default explícit**, no literals
   amagats dins del cos, per la **frontera C3**: l'únic cridador recorre el dict de
   `_load_base_measurements` —intocable— que indexa per POM sol i no els sap dir. Amb la
   signatura oberta, el dia que C3 doni eixos al motor només cal passar-los-hi.
2. **`_materialize_lines`** — l'`exclude` no és expressable per tupla amb l'ORM (no hi ha
   `__in` de tuples): el filtre passa a **Python**. El cost és una consulta per check, i
   l'alternativa (un `Q` gegant) diria pitjor el que fa.
3. **La promoció model→item** — les files de treball porten claus internes (`_capa`,
   `_instancia`) perquè el bucle d'aplicació ha de retrobar la fila EXACTA i el `next(...)` no
   les pot deduir del `pom_id`. **Es netegen en un sol lloc abans de respondre**: el payload
   d'aquest endpoint no canvia ni un byte.

### La federació, en detall

`_clau_natural_pom` passa a **`(codi del diccionari, codi de client, capa, instància)`**, i és
l'argument que el seu propi docstring ja feia: *«les dues cases parlen el mateix sistema i
endevinar seria posar una mesura sobre el POM equivocat»*. Amb la clau de 2, dues mesures
germanes n'emetien una de sola — i col·lapsar-les és pitjor que endevinar, perquè **ni tan sols
hi ha un POM equivocat a què assenyalar**.

Els eixos **no es resolen al catàleg del destí** (`_resol_pom_al_desti`): no són del
`POMMaster`, són de la fila de mesura. Viatgen dins de la clau i s'escriuen tal qual.

**El paquet es versiona** (`FORMAT_PATRIMONI = 2`). Els paquets de format 1 es completen a la
porta d'entrada (`_clau_amb_eixos`) amb el parell canònic: parlen, de fet i sense excepció, de
l'única cosa que el sistema sabia escriure. La **regla** no té eixos (decisió Montse) i viatja
amb el parell canònic com a farciment, perquè les dues cases parlin una sola forma de clau.

---

## ⚠️ L'ÚNIC CANVI DE FORMA DEL TRAM (declarat i mandatat)

El bolcat de superfícies **NO** és byte-idèntic a T0. **16 dels 18 blocs sí que ho són**; els
dos que canvien són:

| bloc | superfície | què canvia |
|---|---|---|
| `D6_federacio_patrimoni` | `_llegeix_patrimoni` | + `"format": 2` · les claus passen de 2 a 4 trams |
| `D7_federacio_clau_natural` | `_clau_natural_pom` × 40 POMs | 2 → 4 trams |

**No és una regressió: és l'encàrrec explícit de la fase** (`FASE_3_ONADA2.md`, ABAST ESPECIAL:
*«Federació: `_clau_natural_pom` creix a 4-tupla … + versionat del paquet»*). És el format
**INTERN** del paquet entre cases; **cap contracte d'usuari, cap endpoint, cap byte d'OpenAPI**.
Els blocs `D6`/`D7` es van afegir al bolcat a FASE_0 precisament per fer aquest canvi visible en
comptes de silenciós.

```
blocs idèntics a T0: 16/18
  C1_s10_vs_spec · C1_s6_base_units · C1_s6_graded_units · C2_model_overrides
  C3_graded_table · C4_repas · C5a_sizefitting_serializer · C5b_sizecheck_serializer
  C6_pom_placements · C7_measurements_table · C8_sembra_step · D1_s6_pom_htm
  D2_s8_export_fitting_csv · D3_s11_model_alerts · D4_nomenclatura_alies
  D5_patterns_model_poms
```

## GREEN FLAGS

| flag | resultat |
|---|---|
| `manage.py check` | **net** abans de cada commit |
| **grep d'estampat** | **29 escriptors, 0 sense els dos eixos** (1 fals positiu de `bulk_create`, 2 de prosa) |
| harness d'escriptors (nou) | **9/9 OK** |
| harness de files germanes v2 | **7/7 OK** |
| `test_lectors_capa_onada1` (asserts estrets) | **OK** |
| pin `base_stages` 13/13 | **OK** |
| `test_capa_comporta_c1` · `test_instancia_comporta_cins` · `test_ordre_taula_mesures` · `test_size_check_completa_linies` | **OK** |
| **conjunt de la fase** | **Ran 63 tests · OK** |
| **fumeig `base-stages` = T0** | **`a14ce3ec1d47c1555fd8f3e59cae9a5f`** ✅ |
| dump de superfícies | **16/18 idèntics** · D6/D7 pel motiu de dalt |
| OpenAPI (des del codi) | **`9d0ec949e7d7e378ff488d1b681687ec`** = T0, **byte-idèntic**. 1 ocurrència de `instancia`, l'homònim de sempre |
| comportes de les dues famílies | vives, verificades al catàleg de PG dins de rollback pels dos harnesses |

### Els dos asserts estrets, i el que demostren

`test_lectors_capa_onada1` (cas C9) i `test_lectors_instancia_cins` arrossegaven una nota des
del 31/07: *«l'assert és `assertNotIn` i no una igualtat perquè la fila d'exterior encara veu
el 98.0 de la BASE del folre; no hi arriba per aquest lector sinó pel SIGNAL de F1. Quan
l'Onada 2 passi, aquesta igualtat es pot estrènyer.»*

Ha passat:
- la fila d'**exterior** ara veu **només** `{100.0}` — la seva presa;
- la de **folre** en veu **dues**: `{98.0, 7.0}` — la seva **alta** i la seva **presa**.

**Que el 98.0 hagi APAREGUT a la fila de folre és exactament la prova que el forat s'ha
tancat**: fins avui aquella alta vivia a la fila de l'altra capa.

### Una conseqüència que val la pena tenir escrita

Els harnesses ara han d'alçar **també la comporta del `MeasurementChangeLog`** per crear una
germana no-canònica: el signal hi escriu una fila amb els eixos de la mesura, i aquella taula
té la seva pròpia comporta. Van petar 13 casos fins a adonar-me'n. **Que això calgui és, de
fet, la prova que el signal estampa de debò** — abans, la fila del log queia a `exterior`/`''`
i passava per la porta sense tocar-la.

## PENDENTS (2, tots dos amb fase assignada)

| node | motiu | va a |
|---|---|---|
| **`reorder`/`ordering` dins-de-capa** (`views.py:2018` + `MeasureGrid.jsx:274-282`) | l'ordre del pla del dossier el condiciona a que el canvi sigui invisible amb una sola capa; **aquí implica migració d'`ordering` amb efecte visible i toca un `.jsx`**, que aquesta fase té prohibit. La maqueta v2 (files ordenades per capa) és C4 | **C4-ins, amb Agus** |
| **`pom/services.py` `preview_graded_specs`** | segueix el PENDENT de FASE_2: la clau la dicta `_load_base_measurements`, zona de motor amb decisió humana | **C3, sessió diürna** |

**NO TOCATS, com mana l'ordre:** els 7 guards de §II.13 (la seva inversió és Onada 3/C4-ins,
amb UI i 409-amb-candidats) · `_load_base_measurements` i `_load_grading_rules` · cap `.jsx`.

## DESCOBERTES (anotades, MAI arreglades)

**5 escriptors que el dossier no tenia i que SÍ pertanyien al bloc A** — trobats pel cens
executable i inclosos a la feina: `services_size_check.py` (el `get_or_create` de
`resolve_size_check`) · `fitting/services.py` (la consolidació) · `views.py` (la còpia
model→model i `gravar_pom_view`) · `federation_service.py` (l'escriptura al bessó).

**`reseed_tenant_fhort.py` és codi mort.** Construeix `GarmentPOMMap(garment_type=…)`, una FK
que es va retirar de la taula: peta abans d'arribar a la BD. Ha rebut els eixos igualment —si
algú el ressuscita, que neixi dient la veritat— però **el seu deute real és un altre i no s'ha
tocat**. És, a més, l'únic `bulk_create(ignore_conflicts=True)` del repo sobre les 9 taules:
amb els eixos fixats al parell canònic segueix saltant-se exactament el mateix que abans.

**Lectors amb clau curta que aquesta fase topa de cara i no toca** (són `top-up-lectors` o
C4-ins, i ja consten al report de FASE_2): `views.py:1637-1642` (la taula de mesures principal)
· `:2789-2793` (l'`id` sintètic `f'{pom.id}:{talla}'` — **col·lisió d'ids entre instàncies**) ·
`fitting/views.py:665-668` (la propagació escriu a **totes** les instàncies del POM amb un
`.update()` massiu) · `patterns/adapters.py:484-488` (frontera amb el motor de patrons) ·
`clone_model_for_qa.py:128-131`.

**Vermell PREEXISTENT confirmat, no del tram.** La suite ampla (`fhort.patterns` +
`fhort.tenants` + `fhort.fitting`, **584 tests**) dona **29 errors**, tots
`UniqueViolation: fitting_sizefitting_model_id_numero_uniq`, tots dins de `fhort.fitting.tests`
i `fhort.fitting.test_g6_estalitud`. **És el vermell documentat el 28/07** (memòria
`ftt-repas-fittings-model`): `models_app/signals.py` crea SEMPRE un `SizeFitting numero=1` en
crear un Model, i els `setUp` d'aquests dos mòduls encara en creen un explícitament. Fix d'una
línia, i fora d'abast d'aquesta tarda. **`fhort.patterns` i `fhort.tenants` verds.**

---

## VEREDICTE

**FASE_4 POT ARRENCAR.**
