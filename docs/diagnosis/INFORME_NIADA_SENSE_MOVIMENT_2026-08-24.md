# Per què la niada del 1383 no mou cap punt (PF20 v3 · GV201 v9)

**Patró A estricte · read-only.** Cap escriptura a BD (tota la sondeja va dins un
`transaction.atomic()` amb `set_rollback(True)`), cap fitxer del repo tocat fora d'aquest,
cap suite executada. Clon `ftt-staging`, branca `dev`, schema `fhort`.

---

## VEREDICTE

**La hipòtesi de treball és FALSA: la projecció SÍ s'executa** — s'executa cada vegada que
s'obre l'ExportModal, i s'ha executat per a la GV201. Calcula bé els deltes, els converteix
bé en ordres de moviment i els lliura bé a `move_points`.

**El moviment es perd DINS de `move_points`, en una sola línia**, i per una raó concreta i
mesurable: **els 14 ancoratges de POM d'aquest patró seuen tots a la línia de COSIT
(`vora=1`, rol `SEW`), i `_propagar_al_cosit` reescriu el desplaçament de tota la línia de
cosit a partir del contorn de TALL** — que no ha rebut cap ordre. El resultat és una
geometria idènticament igual a la base.

Una sola causa explica **els dos símptomes alhora**: el «1/1 regles idèntiques» i el
`−delta` a totes les caselles. **No hi ha segona causa independent.**

---

## 1. INVOCACIÓ — on i quan s'executa la projecció

`GradeRule` **no és cap taula**: la projecció és **en memòria i efímera**, part del pipeline
d'exportació. No hi ha ni segell, ni gest, ni endpoint que la persisteixi.

- Únic punt d'invocació: [`patterns/export.py:179`](../../backend/fhort/patterns/export.py#L179)
  · `projeccio = project(doc, snapshot, specs, sews)`, dins de `build_export`
  ([`export.py:144`](../../backend/fhort/patterns/export.py#L144)).
- `build_export` té exactament **tres** cridadors, tots tres HTTP:
  - [`patterns/views.py:780`](../../backend/fhort/patterns/views.py#L780) — `POST …/export-preview/`
    (**la taula de pre-reconeixement de l'ExportModal**)
  - [`patterns/views.py:825`](../../backend/fhort/patterns/views.py#L825) — `POST …/export/` (DXF)
  - [`patterns/views.py:856`](../../backend/fhort/patterns/views.py#L856) — `POST …/export-rul/` (RUL)
- El segell (`seal_grading_version`) **no la crida**. Cap management command tampoc.

> Conseqüència: la taula ⚠ que l'Agus té a la pantalla **és** la sortida de la projecció.
> Ja s'ha executat, i el que ha donat és zero.

---

## 2. ESTAT A BD — quants GradeRule/deltes de punt hi ha ara mateix

**Zero, i no perquè faltin: perquè aquesta entitat no existeix a la BD.** El que hi ha són
dues coses diferents, cap de les quals és el resultat de la projecció:

| Superfície | Fitxer:línia | PF20 v3 |
|---|---|---|
| `PatternFile.grade_table` (JSON — el RUL **del client**, tal com venia) | [`patterns/models.py:95`](../../backend/fhort/patterns/models.py#L95) | **NULL** (PF20 no porta RUL) |
| `PatternPoint.grade_rule_num` (el número de regla **del DXF d'origen**) | [`patterns/models.py:299`](../../backend/fhort/patterns/models.py#L299) | **180 punts**, tots ≠ 0 |

Desglossat per peça (recompte real, lectura d'avui):

```
PF20 v3 · grade_table = NULL
  837.CUELLO       punts=1224   amb grade_rule_num=24
  837.DELANTERO    punts= 984   amb grade_rule_num=62
  837.ESPALDA      punts= 928   amb grade_rule_num=52
  837.MANGA        punts= 612   amb grade_rule_num=22
  837.TAPETA       punts=  92   amb grade_rule_num=20
                                          TOTAL = 180
(comparativa PF18 v1, que SÍ porta RUL: grade_table = JSON amb 1 regla, 100 punts amb número)
```

Els 180 números són els que el CAD d'origen va numerar (els «~158» del brief). **No són
deltes**: el RUL germà que els donava contingut no existeix en aquesta versió, o sigui que
són punteros a un no-res. I, sobretot, **no els llegeix ningú per moure res** (§3).

---

## 3. CADENA DE L'EXPORT — d'on treu els deltes el writer

**El writer no mou cap punt, i no ho ha de fer.** El lliurable AAMA és *una sola geometria*
(la talla mostra) + *un número de regla assegut a cada punt* + *el RUL amb els deltes*. Qui
reconstrueix les talles és el CAD del client, fent `punt_base + delta(regla, talla)`.

La cadena, en ordre:

1. `project()` calcula `regles_per_punt` i `grade_table` **en memòria**
   ([`grading_projection.py:231`](../../backend/fhort/patterns/engine/grading_projection.py#L231)).
2. `_assignar_regles` ([`grading_projection.py:398-426`](../../backend/fhort/patterns/engine/grading_projection.py#L398-L426))
   **sobreescriu `grade_rule` a TOTS els punts de gir i a TOTS els piquets** del document.
3. [`export.py:189-192`](../../backend/fhort/patterns/export.py#L189-L192) —
   `grade_table=projeccio.grade_table` **substitueix** la taula que venia del client.
4. `AAMAWriter().write(doc_final, …)` ([`export.py:216`](../../backend/fhort/patterns/export.py#L216))
   i `RULWriter().write(projeccio.grade_table)` ([`export.py:225`](../../backend/fhort/patterns/export.py#L225),
   writer a [`engine/rul_writer.py:38-67`](../../backend/fhort/patterns/engine/rul_writer.py#L38-L67)).

> **Resposta explícita a la pregunta: NO.** Les regles del DXF d'origen (els 180
> `grade_rule_num`) **no arriben mai al fitxer emès** — el pas 2 les esborra i les
> reescriu totes. **No hi ha segona causa independent per aquesta banda.**

---

## 4 i 5. LA PROJECCIÓ S'HA EXECUTAT I DONA ZERO — traça completa del POM A a la talla M

Reproducció read-only del pipeline exacte sobre PF20 + GV201 (`project()` és pura;
`load_from` és lectura, [`adapters.py:203-209`](../../backend/fhort/patterns/adapters.py#L203-L209)):

```
SNAPSHOT approved=True  base=S  size_run=('XS','S','M','L','XL')  deltas=105
POMSpec que entren a la niada: 14      (6 exclosos, tots de mode 'projeccio')
INTERSECCIÓ ancoratges ∩ GradedSpec: 14 de 14   ← la matriu NO té forats
REGLES a la taula: 1   regles_actives: 0
regles_per_punt: 202 punts, cap amb regla ≠ 0
punts moguts:  XS=0  S=0  M=0  L=0  XL=0
```

### La traça, baula a baula

| # | Baula | Fitxer:línia | Què hi arriba (talla M, POM A) |
|---|---|---|---|
| 1 | `GradedSpec` GV201 / pom 904 / M | `fitting/models.py:200` | `increment_applied_cm = +3.00`, `LINEAR` ✅ |
| 2 | Snapshot del port | [`adapters.py:495-510`](../../backend/fhort/patterns/adapters.py#L495-L510) | `GradedPOMDelta(delta_cm=3.0)` ✅ |
| 3 | Escalar → vector, repartiment simètric | [`grading_projection.py:277`](../../backend/fhort/patterns/engine/grading_projection.py#L277), [`:297-298`](../../backend/fhort/patterns/engine/grading_projection.py#L297-L298) | `delta_mm=30.0` → `(DELANTERO,1,370) += (−3.92, +15.73)` i `(DELANTERO,1,104) += (−0.01, −15.00)` ✅ |
| 4 | `move_points` → `_desplacaments_vora` | [`operations.py:286-293`](../../backend/fhort/patterns/engine/operations.py#L286-L293) | 17 punts amb delta explícit + 3.635 de corba reflowats ✅ |
| 5 | **`_propagar_al_cosit`** | [`operations.py:296`](../../backend/fhort/patterns/engine/operations.py#L296) → [`:450`](../../backend/fhort/patterns/engine/operations.py#L450) | **☠️ AQUÍ ES PERD** (avall) |
| 6 | Aplicar desplaçaments | [`operations.py:301-307`](../../backend/fhort/patterns/engine/operations.py#L301-L307) | geometria **idèntica** a la base |
| 7 | `deltes_resultants` | [`operations.py:765`](../../backend/fhort/patterns/engine/operations.py#L765) | `{}` (cap punt amb delta ≠ 0) |
| 8 | `deltes_per_talla[M]` | [`grading_projection.py:224`](../../backend/fhort/patterns/engine/grading_projection.py#L224) | buit |
| 9 | `_regles_des_dels_deltes` | [`grading_projection.py:387-388`](../../backend/fhort/patterns/engine/grading_projection.py#L387-L388) | tot zero → **`REGLA_ZERO` als 202 candidats** |
| 10 | `grade_table` → RUL → autovalidació | [`export.py:225`](../../backend/fhort/patterns/export.py#L225), [`:319`](../../backend/fhort/patterns/export.py#L319) | 1 regla escrita, 1 rellegida → **«1/1 regles idèntiques»** ✅ (el comparador no menteix: compara res amb res) |
| 11 | `preview_per_talla` | [`grading_projection.py:501-509`](../../backend/fhort/patterns/engine/grading_projection.py#L501-L509) | `deltes = {}` → geometria = base → `delta_llegit = 0` → **`desviament = 0 − 3.00 = −3.00`** ⚠ |

### ☠️ La baula 5, al detall

[`operations.py:509-518`](../../backend/fhort/patterns/engine/operations.py#L509-L518):

```python
for j, k in parelles.items():
    desplacaments[i][j] = desplacaments[idx_tall][k]      # ← 510: SOBREESCRIU
    propagats += 1

refluits, _, _, _ = _desplacaments_vora(                  # ← 514: i després
    boundary, i, piece.nom_block,
    {PointRef(piece.nom_block, i, j): desplacaments[i][j] for j in parelles},
)
desplacaments[i] = refluits                               # ← 518: DESCARTA la llista sencera
```

Dues pèrdues, no una:

- **`:510`** — cada punt de GIR de la línia de cosit hereta el desplaçament del seu company
  del TALL. El tall no ha rebut cap ordre → hereta `(0, 0)`, esborrant els ±15 mm.
- **`:514-518`** — la llista de desplaçaments de la vora de cosit es **reconstrueix des de
  zero** a partir *només* de les parelles de gir. Qualsevol delta explícit que visqués sobre
  un punt de **CORBA** de la línia de cosit (el cas del `ref_b` del POM A, ordre 104)
  desapareix aquí, encara que `:510` no l'hagués tocat.

La condició d'entrada és **`piece.has_sew`** ([`operations.py:296`](../../backend/fhort/patterns/engine/operations.py#L296)),
i **les 5 peces del 837 la tenen a `True`**.

### On seuen els ancoratges (el que ho tanca)

```
837.CUELLO    has_sew=True   vora0=CUT(566)  vora1=SEW(650)
837.DELANTERO has_sew=True   vora0=CUT(498)  vora1=SEW(474)
837.ESPALDA   has_sew=True   vora0=CUT(462)  vora1=SEW(458)
837.MANGA     has_sew=True   vora0=CUT(280)  vora1=SEW(324)
837.TAPETA    has_sew=True   vora0=CUT( 38)  vora1=SEW( 46)

Ancoratges: E7 A B C D E F S SLT E1 S2 J1 U → tots dos extrems a SEW
            G1 → ref_a a CUT, ref_b a SEW      (14 POMs, 27 extrems, 26 sobre SEW)

Ordres emeses a la talla M, per (peça, vora):
   ('837.DELANTERO', 1): 12   ('837.ESPALDA', 1): 3   ('837.MANGA', 1): 2
   → 17 de 17 ordres cauen sobre la línia de COSIT. Cap sobre el tall.
```

### Contraprova (en memòria, cap escriptura)

El mateix document i les mateixes ordres, amb l'únic interruptor de `_propagar_al_cosit`
(`has_sew`) neutralitzat en una còpia de la dataclass:

```
AMB propagació al cosit (el que passa avui):  punts moguts=0    A=44.284  B=46.093  C=53.570
SENSE propagació (contraprova):               punts moguts=499  A=47.358  B=49.093  C=56.570
Base llegida de la geometria:                                   A=44.284  B=46.093  C=53.570
Delta que el grading mana a M:                                  A=+3.00   B=+3.00   C=+3.00
```

B i C aterren **exactament** al que el grading manava. La causa és aquesta i prou.

---

## 6. LA TAULA DE PRE-RECONEIXEMENT — amb quina geometria re-mesura

[`grading_projection.py:501-509`](../../backend/fhort/patterns/engine/grading_projection.py#L501-L509):

```python
deltes = {ref: regla_delta
          for ref, num in projeccio.regles_per_punt.items()
          if (regla_delta := projeccio.grade_table.regles[num].delta(talla)) != (0.0, 0.0)}
res = move_points(doc, deltes, poms=poms, sews=sews)
```

Re-mesura la geometria **reconstruïda a partir de LES REGLES** — el camí invers, tal com ho
faria el CAD del client. **No** és el patró base per disseny.

Però com que les 202 regles són `REGLA_ZERO`, `deltes` surt **buit**, `move_points(doc, {})`
retorna la base, i la taula acaba mesurant el patró base a totes les talles.

> **Els ⚠ són el MATEIX símptoma, no una segona causa.** `delta_llegit = 0` sempre, i per
> tant `desviament = 0 − delta_spec = −delta_spec` a cada cel·la amb delta ≠ 0.
> Les cel·les amb `delta_spec = 0` (E7, SLT, G1 i U a la talla M) surten netes — que és
> exactament el que la pantalla ensenya.

---

## ANOMALIES (sense fix, per ordre de gravetat)

**A1 — El moviment del grading es perd sencer a la línia de cosit.**
[`operations.py:509-518`](../../backend/fhort/patterns/engine/operations.py#L509-L518).
`_propagar_al_cosit` tracta la vora `SEW` com a **derivada pura** del `CUT`: no comprova si
la vora de cosit portava deltes propis. Un POM ancorat sobre la línia de cosit no és cap
raresa —és el cas del 837 sencer, 26 extrems de 27— i avui el seu moviment s'esborra en
silenci. **Cap avís ho diu**: el `MoveReport` informa `punts_moguts=17` i
`punts_cosit_propagats>0`, i totes dues xifres són certes; el que no diu ningú és que la
segona ha anul·lat la primera.

**A2 — Cap test cobreix aquest cas, i per això el gate és verd.**
L'únic test de `has_sew` (`patterns/tests.py:2843` · `SewCosidorAMBTallTest`) mou
`PointRef('P', 0, 2)` — **vora 0, el TALL**. I tot el banc d'escalat (`EscalatTestBase`,
`patterns/tests.py:2889+`) ancora els POMs sobre `boundary_index=0`, també el TALL. **Cap
test ancora mai un POM sobre la vora `SEW`**, que és el 100 % del cas real.

**A3 — L'autovalidació no pot veure això, i és correcte que no ho vegi.**
`compare_grade_tables` ([`export.py:319`](../../backend/fhort/patterns/export.py#L319))
compara *el que hem escrit* amb *el que rellegim*. Amb una taula d'una sola regla nul·la,
«1/1 idèntiques» és un verd honest. La porta demostra reproductibilitat, **no** que la niada
digui res. Avui l'única superfície que canta el problema és la taula de pre-reconeixement,
i el canta amb la gramàtica d'un desviament de mesura (`−delta`), no amb la d'un motor
aturat.

**A4 — Els 180 `grade_rule_num` de PF20 apunten a un RUL que no existeix.**
PF20 v3 té `grade_table = NULL` (no s'hi va pujar RUL) i 180 punts amb número de regla del
CAD d'origen. Avui és **inofensiu** (§3: s'esborren tots a l'emissió), però és una
incoherència viva a la fila: un número de regla sense taula que el resolgui. PF18 v1 sí que
porta les dues coses.

**A5 (segon ordre, observació) — dos POMs tenen un extrem sobre un punt de CORBA.**
A (`ref_b` = corba), C (`ref_a` = corba) i S2 (`ref_a` = corba). El motor ho diu en veu alta
(`delta_sobre_corba`), però `_regles_des_dels_deltes`
([`grading_projection.py:375-381`](../../backend/fhort/patterns/engine/grading_projection.py#L375-L381))
només fa candidats a portar regla els punts de **GIR** i els **piquets**: un punt de corba
que s'ha mogut no rep número de regla i, al fitxer emès, tornarà a fluir. A la contraprova
això es veu com el residu del POM A (+3,074 en comptes de +3,000, mentre B i C claven el
+3,000). **No és la causa d'aquest informe** i no s'ha investigat més enllà; queda anotat
perquè apareixerà tan bon punt A1 estigui resolta.

---

## APÈNDIX — inventari de PF20 v3

```
Model 1383 · TRV-SS27-0001 · 837 VESTIT · base='S' · size_run='XS·S·M·L·XL' · fase=Dev
PF18 v1  is_current=False  5 peces  RUL='837  VESTIT s opcio cost.RUL'  grade_table=SI
PF19 v2  is_current=False  5 peces  RUL=''                              grade_table=NO
PF20 v3  is_current=True   5 peces  RUL=''                              grade_table=NO   ← l'actiu

20 PatternPOM ancorats · 14 entren a la niada · 6 exclosos amb motiu (adapters.py:613-627):
   E5, EK, EK1, EK2, SF, I  →  mode='projeccio'
   Aquests 6 NO surten a la taula de pre-reconeixement (la taula itera els POMSpec):
   surten a la llista de «problemes» del modal.

GV201 · 105 GradedSpec actives · 21 POMMaster × 5 talles
   Els 7 'spec_sense_pom' de l'informe són els 6 de projecció + el POM J (no ancorat enlloc).
```
