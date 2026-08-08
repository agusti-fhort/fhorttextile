# INFORME DE LA TARDA · TRAM INSTÀNCIA DE POM · 2026-08-02

**23 commits locals a `dev`. CAP PUSH.** El sistema sap dir, per primera vegada, que la sisa
dreta i la sisa esquerra són dues mesures i no una. Encara no ho deixa dir a ningú —les
comportes segueixen tancades— però l'esquema, tots els lectors i tots els escriptors ja el
parlen.

HEAD d'inici: **`2ee55200`** → HEAD final: **`e8848258`**.

---

## 1 · TAULA DE FASES

| fase | estat | commits | PENDENTs |
|---|---|---|---|
| **FASE_0 · PREVOL** | 🟢 **VERDA** | — (cap: eines fora de git) | 0 |
| **FASE_1 · C1-ins (esquema)** | 🟢 **VERDA** | 5 | 0 |
| **FASE_2 · top-up de lectors** | 🟢 **VERDA AMB PENDENTS** | 8 | 3 |
| **FASE_3 · Onada 2 (escriptors)** | 🟢 **VERDA AMB PENDENTS** | 10 | 2 |
| **FASE_4 · informe** | 🟢 aquest document | — | — |

### Green flags, fase a fase

| flag | F1 | F2 | F3 |
|---|---|---|---|
| `manage.py check` net a cada commit | ✅ | ✅ | ✅ |
| pin `base_stages` 13/13 | ✅ | ✅ | ✅ |
| `test_capa_comporta_c1` intacte i verd | ✅ | ✅ | ✅ |
| fumeig = T0 byte-idèntic | ✅ | ✅ | ✅ |
| dump de superfícies = T0 | ✅ 18/18 | ✅ 18/18 | ⚠️ **16/18** (v. §2) |
| OpenAPI sense `instancia` | ✅ | ✅ | ✅ |
| comportes vives, dues famílies × 3 schemas | ✅ | ✅ | ✅ |
| harness propi de la fase | 12/12 | 7/7 | 9/9 |
| **grep d'estampat** | — | — | ✅ **0 forats** |

### Els commits

**FASE_1 — l'esquema**
| hash | assumpte |
|---|---|
| `e8db78e2` | C1-ins · la columna `instancia`: el segon eix entra a l'esquema de `models_app` |
| `442d4889` | C2-ins · les claus de `models_app` s'obren a la instància i les comportes la tanquen |
| `cb191283` | C3-ins · la instància arriba a `fitting`: l'spec generat i la línia mesurada |
| `c768d787` | C4-ins · la instància a `pom`: on la plantilla declara quantes vegades reclama un POM |
| `3d8878f6` | C5-ins · el pin de la comporta, i la prova que «instància ⇒ nom» rebutja |

**FASE_2 — els lectors**
| hash | assumpte |
|---|---|
| `94f64f7e` | F2-1 · les quatre superfícies de `pom` llegeixen amb la clau completa |
| `91bb74d8` | F2-2 · l'àncora dels overrides tapava una capa i deixava passar una instància |
| `6e28ef72` | F2-3 · la taula de mesures: tres diccionaris per `pom_id`, dues portes, dos eixos |
| `f4c6af24` | F2-4 · `fitting`: la graella, la taula de la fitxa i el repàs llegeixen els dos eixos |
| `de49a5a2` | F2-5 · el size check i la cascada de cotes: la clau completa a les dues bandes |
| `7cd1e854` | F2-6 · el node del pin: la cadena d'estadis creix als dos eixos |
| `e733b7ce` | F2-7 · els dos forats: la llista del taller i el patrimoni que viatja |
| `d5f98b2a` | F2-8 · harness de files germanes v2: tres files, i cap lector les barreja |

**FASE_3 — els escriptors**
| hash | assumpte |
|---|---|
| `e33f3ff7` | F3-1 · desarmat: l'upsert de `GradedSpec` deia tres columnes d'una clau de cinc |
| `dd2b274f` | F3-2 · la línia de fitting clona l'spec: també n'ha de clonar els dos eixos |
| `25628518` | F3-3 · el signal F1 estampa els dos eixos: es tanca el forat que ve de l'Onada 1 |
| `4eca4ffb` | F3-4 · el pitjor cas del cens: la primera germana bloquejava totes les altres |
| `d3999ab1` | F3-5 · les dues cotes del mateix croquis, i el valor típic de l'item |
| `b41286b5` | F3-6 · `models_app`: la sembra hereta, la còpia copia, la resta declara — i la poda és per fila |
| `d8e740c9` | F3-7 · les tres portes d'entrada de document declaren on escriuen |
| `f53eb725` | F3-8 · la clau natural de la federació creix a quatre trams, i el paquet es versiona |
| `79314af5` | F3-9 · els sembradors: la clau natural del bootstrap i les quatre portes de catàleg |
| `e8848258` | F3-10 · harness d'escriptors, i els dos asserts que ara es poden estrènyer |

---

## 2 · LES XIFRES DE TANCAMENT

### Termòmetres

| artefacte | T0 (07:30) | T-final | veredicte |
|---|---|---|---|
| fumeig `base-stages` (md5, sense 1a línia) | `a14ce3ec1d47c1555fd8f3e59cae9a5f` | `a14ce3ec1d47c1555fd8f3e59cae9a5f` | ✅ **byte-idèntic** |
| OpenAPI generat des del codi (md5) | `9d0ec949e7d7e378ff488d1b681687ec` | `9d0ec949e7d7e378ff488d1b681687ec` | ✅ **byte-idèntic** |
| ocurrències de `instancia` a OpenAPI | 1 | 1 | ✅ (l'homònim català de `materialitzar-poms`, no cap camp) |
| dump de superfícies (18 blocs) | `fd2eaebed9ad576ca52246b400cce265` | **16/18 idèntics** | ⚠️ **explicat** |

**⚠️ L'ÚNICA DIFERÈNCIA DE TOTA LA TARDA**, i és l'encàrrec explícit de FASE_3: els blocs
`D6_federacio_patrimoni` i `D7_federacio_clau_natural`. La clau natural del paquet de federació
passa de 2 a 4 trams i el paquet guanya `"format": 2`. És el format **INTERN** entre cases:
cap contracte d'usuari, cap endpoint, cap byte d'OpenAPI. Els altres **16 blocs** —les 8
superfícies d'Onada 1 i les 8 de FASE_2/3 que s'hi van afegir a FASE_0— són byte-idèntics.

### Auditoria SQL final (3 schemas)

**Files amb `instancia = ''`: 100 %. Cap NULL. Cap excepció.**

| schema | taula | files | `instancia=''` |
|---|---|---|---|
| `fhort` | `models_app_basemeasurement` | 760 | **760** |
| `fhort` | `models_app_measurementchangelog` | 289 | **289** |
| `fhort` | `models_app_sizecheckline` | 92 | **92** |
| `fhort` | `models_app_pomplacement` | 2 | **2** |
| `fhort` | `fitting_gradedspec` | 2 061 | **2 061** |
| `fhort` | `fitting_piecefittingline` | 153 | **153** |
| `fhort` | `pom_garmentpommap` | 1 748 | **1 748** |
| `fhort` | `pom_itembasemeasurement` | 37 | **37** |
| `fhort` | `models_app_modelgradingoverride` | 0 | 0 |
| `los` · `public` | (les seves) | 0 | 0 |
| **`models_app_modelgradingrule`** | fhort 510 · los 0 | — | **columna ABSENT ✅** |

`information_schema`: **20 columnes `instancia`**, totes `is_nullable = NO`,
`character_maximum_length = 60`, **`column_default` buit** — el parany de C1 confirmat: el
default viu al MODEL, no a Postgres.

**Comportes vives, les dues famílies:**

| schema | `*_capa_gate_c1` | `*_instancia_gate_cins` |
|---|---|---|
| `fhort` | **9** | **9** |
| `los` | **9** | **9** |
| `public` | **2** | **2** |

\+ el CHECK que **no és bastida**: `models_app_basemeasurement_instancia_exigeix_nom`
(`NOT (instancia > '' AND nom_fitxa = '')`), viu a `fhort` i `los`. Decisió D1: una mesura amb
instància i sense nom de fitxa és il·legal per construcció, i això sobreviu a C4-ins.

\+ les **8 unicitats** amb els dos eixos al final, als 3 schemas, **sense cap resta de la clau
vella**.

### Tests

| mòdul | resultat |
|---|---|
| `models_app.test_base_stages_no_regressio` (**el pin**) | **13/13** |
| `models_app.test_capa_comporta_c1` (intacte) | ✅ |
| `models_app.test_instancia_comporta_cins` (**nou**) | **12/12** |
| `models_app.test_lectors_capa_onada1` (asserts estrets) | ✅ |
| `models_app.test_lectors_instancia_cins` (**nou**) | **7/7** |
| `models_app.test_escriptors_instancia_cins` (**nou**) | **9/9** |
| `pom.test_ordre_taula_mesures` · `models_app.test_size_check_completa_linies` | ✅ |
| **conjunt de la tarda** | **Ran 63 tests · OK** |
| suite ampla `patterns` + `tenants` + `fitting` | **584 tests · 29 errors PREEXISTENTS** (v. §5) |

**3 fitxers de test nous, 28 casos nous.**

### Grep d'estampat (el green flag de FASE_3)

```
escriptors sobre les 9 taules: 29 · SENSE els dos eixos: 1
   → pom/management/commands/reseed_tenant_fhort.py:320 `bulk_create(maps, …)`
     FALS POSITIU: els objectes de `maps` porten els eixos al constructor, 8 línies amunt.
constructors directes: 5 · sense els dos eixos: 2
   → tots dos, PROSA de docstring («PieceFittingLine (per PieceFitting = …)»)
```

**El fet estructural del dossier —«cap escriptor del repo estampa `capa` avui»— està mort.**

---

## 3 · ESTAT DE `dev`

23 commits, cap pushat. `git log --oneline 2ee55200..HEAD` és la llista de §1.
Revisió recomanada: `git show <hash>` en aquest ordre —

1. **`e8db78e2` → `3d8878f6`** (esquema): mira els `sqlmigrate` enganxats a `REPORT_FASE_1.md`
   abans dels fitxers; les migracions ja estan **aplicades als 3 schemas** i el servei
   reiniciat.
2. **`94f64f7e` → `d5f98b2a`** (lectors): cada commit diu FORMA A o FORMA B i per què.
3. **`e33f3ff7` → `e8848258`** (escriptors): comença per `25628518` (el signal) i `4eca4ffb`
   (la materialització) — són els dos que canvien més comportament latent.

**Estat del servidor:** `ftt-staging.service` **active** · `/api/schema/` **200** ·
`git status` net excepte `DECISIONS.md` (fitxer d'estat, mai commitat) i els 5
`docs/diagnosis/REPORT_*.md` nous, que **no** entren a cap commit per la regla de la tarda.

---

## 4 · PENDENTS CONSOLIDATS

| # | node | fase | motiu | on és al dossier |
|---|---|---|---|---|
| P1 | **`pom/services.py` `preview_graded_specs`** (`out[pom_id] = row`) | F2 + F3 | **arrossegament d'INTOCABLE**: la seva clau la dicta `_load_base_measurements`, zona de motor amb decisió humana. Tocar-la aquí voldria dir inventar els eixos dins del motor | §II.10 bloc D · exclosos d'Onada 1 |
| P2 | **`models_app/services_size_check.py` `_materialize_lines`** | F2 → **fet a F3** | FASE_3 el reclamava explícitament amb el seu propi commit i test. **Ja no és pendent**: `4eca4ffb` | §II.10 bloc D |
| P3 | **`pom/nomenclatura.py` `alies_per_pom`** | F2 | **fora del contracte**: llegeix `CustomerPOMAlias`, que no és cap de les 9 taules i no té cap eix. Un àlies és nomenclatura de client per POM, no per instància. **Proposta: treure'l del cens del dossier** | §II.10 bloc D |
| P4 | **`reorder`/`ordering` dins-de-capa** (`views.py:2018` + `MeasureGrid.jsx:274-282`) | F3 | implica **migració d'`ordering` amb efecte visible** i toca un `.jsx`; la maqueta v2 (files ordenades per capa) és C4 | §C2 Onada 2, punt 7 |
| P5 | **Blocs E i F de §II.10** (11 comptadors + 6 lectors de llista) | F2 | **no són diccionaris**: E compta files (canviar-los vol decidir si «5 mesures» són 5 POMs o 5 files — producte, no refactor); F emet dues files i el problema és del consumidor de frontend, que és C4-ins | §II.10 blocs E i F |
| P6 | **La BD de test no es pot construir des de zero** | F1 | peta a `pom/0013_garmenttype_descripcio_…` (`column "descripcio" … already exists`), 43 migracions per sota de les d'aquesta tarda. **Preexistent**; resolt per avui reconstruint-la des de l'estructura de staging (recepta a `REPORT_FASE_1.md`) | — (infra) |

---

## 5 · DESCOBERTES

**🔴 El vermell preexistent de `fitting`, confirmat i acotat.** La suite ampla dona **29
errors**, tots `UniqueViolation: fitting_sizefitting_model_id_numero_uniq`, tots dins de
`fhort.fitting.tests` i `fhort.fitting.test_g6_estalitud`. És el vermell **documentat el
28/07**: `models_app/signals.py` crea sempre un `SizeFitting numero=1` en crear un Model, i els
`setUp` d'aquests dos mòduls encara en creen un explícitament. **Fix d'una línia**
(`SizeFitting.objects.filter(model=…).first() or create(…)`, el patró de `test_repas.py`).
`fhort.patterns` i `fhort.tenants`: **verds**.

**🟠 34 nodes que el dossier de 487 no tenia**, trobats pels dos censos executables:
- **5 escriptors que SÍ pertanyien al bloc A** i han entrat a la feina: `resolve_size_check` ·
  la consolidació de fitting · la còpia model→model · `gravar_pom_view` · l'escriptura al bessó
  de federació.
- **`ordre_pom` + `clau_ordre_taula`** (`pom/grading_views.py`) — novè i desè germà del cens de
  diccionaris per `pom_id`. Fets a F2-3.
- **~27 lectors/escriptors** censats i **NO tocats** (són `top-up-lectors` residual, C4-ins o
  `F2-patrons`). Els tres que val la pena mirar abans que ningú:
  - **`fitting/views.py:665-668`** — la propagació fa `.update()` massiu **per `pom` sol**:
    escriuria a **totes** les instàncies del POM, i no peta.
  - **`models_app/views.py:2789-2793`** — l'`id` sintètic de la línia és `f'{pom.id}:{talla}'`:
    **col·lisió d'ids entre instàncies** al payload.
  - **`models_app/views.py:3927-3929`** — `desactivar_pom_view` desactiva **una instància
    arbitrària** de la família.

**🟢 Dos bugs del dossier ja estaven tancats** pel delta del matí (re-cens de FASE_0):
`patterns/views.py` (B-1, el dict `ancorats`) i `cleanup_losan_old.py` (B-2). I una **inexactitud
del dossier**: §II.14 B-2 diu que `'base_for_items'` no existeix — **sí que existeix**
(`tasks/models.py:354`); el que hi faltava era `base_set_for_items`.

**🟢 El dossier ja no pot dir «C7 revertit»** (§II.10:3933): el commit `2ee55200` del matí el va
reaplicar, amb àncora de capa a les dues portes.

**🔵 Una conseqüència de mètode que val la pena tenir escrita.** Quan el signal F1 va començar a
estampar, **13 casos de test van petar de cop**: crear una germana no-canònica ara escriu una
fila no-canònica al log, i aquella taula té la seva pròpia comporta. Els harnesses han hagut
d'alçar-la també. **Que això calgués és la prova que el forat s'ha tancat de debò.**

**🔵 I un incident de procés, per no repetir-lo.** El commit F2-1 va canviar una clau de mapa i
es va validar amb `manage.py check` + dump byte-idèntic —tots dos verds— **però no amb la
suite**. Un test d'Onada 1 va quedar vermell tres commits. **El dump byte-idèntic NO substitueix
el harness: per construcció, amb les comportes tancades no pot veure un canvi de clau.** Els
harnesses de files germanes són l'única cosa que sí que el veu. (I: **dues execucions de
`manage.py test --keepdb` alhora es trepitgen** — deixen el schema `test` a mitges.)

---

## 6 · PROPOSTA DE SEGÜENTS PASSOS

1. **Agus:** revisar la cadena (`git show`, ordre a §3) i **fer el push des de SSH**. Cap deploy
   a PROD fins acabar el tram (P1 del pla, ratificat 31/07).
2. **C3 · motor, sessió diürna amb Agus:** `_load_base_measurements` → `{(pom, capa, instancia):
   valor}`. Desbloqueja P1 i el `preview_graded_specs`. Bloquejat encara per P3/P4 (norma de
   folgança + receptes Montse).
3. **Onada 3 · import/wizard:** les 3 regles de 3b + inversió dels 7 guards de §II.13, amb
   409-amb-candidats. **Necessita maqueta del pas 2 abans del brief** (llei 3c.5).
4. **C4-ins · contractes i UI:** 203 nodes, 158 de frontend. **Necessita maquetes** (columna
   capa/instància a Mesures, subcontenidors a la fitxa, impressió). L'últim commit del tram
   retira les 18 comportes.
5. **Montse:** el diccionari d'instàncies (les 3 ambigüitats de §I.C4) i la consolidació de
   catàleg. Sense ell, C4-ins no té vocabulari per validar.

---

## ÚLTIMA COMPROVACIÓ

✅ `git status` net (només `DECISIONS.md` modificat —fitxer d'estat— i els 5 `REPORT_*.md`
nous, cap commitat) · ✅ `ftt-staging.service` **active** · ✅ `/api/schema/` **200** ·
✅ migracions aplicades als 3 schemas i servei reiniciat · ✅ **cap push**.

**Staging queda exactament com s'ha trobat, més 23 commits locals.**
