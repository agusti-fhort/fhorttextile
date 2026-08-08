# DIAGNOSI · «SizeFitting duplicat» — per què la columna Real neix buida i per què el sistema recupera una mesura anterior

> **Patró A · READ-ONLY ABSOLUT.** Cap escriptura a BD, cap migració, cap fitxer del repo
> modificat, cap management command, cap test executat, cap build, cap commit, cap push.
> Única escriptura: aquest document al working tree (**MAI commitejat**).
>
> **Entorn:** staging `/var/www/ftt-staging` · branca `dev` · **HEAD `55e13cab3650eb9f076b578fa4047e680e609e8a`**
> (`E5 · desactivar_pom deixa de triar la germana a l'atzar`, Sun Aug 2 23:20:51 2026 +0000).
> **BD:** `ftt_staging` @5433 · schemas `fhort` · `los` · `public`.
> **Data de la diagnosi:** 2026-08-03.
>
> Cada afirmació porta `fitxer:línia` verificat a AQUEST HEAD, o una consulta SQL amb el seu
> resultat. «NO EXISTEIX» = confirmat absent. Les propostes van al final, separades i marcades.
> **CAP PROPOSTA DE FIX** (per encàrrec).

---

## RESUM EXECUTIU — les conclusions que decideixen

**1. La sospita del brief és FALSA en la seva lletra i CERTA en el seu esperit.**
No hi ha epidèmia de `SizeFitting` duplicats. A `fhort` hi ha **46 SizeFitting per a 44 models**:
42 models en tenen 1 i **només 2 en tenen 2** (els models 163 i 174, els dos models de QA). A `los`
n'hi ha **51 per a 51 models, tots a 1**. I **cap model del corpus té més d'un SizeFitting en estat
no-tancat** (0 files). El duplicat existeix, és conegut, és deliberat i és de 2 models sobre 44.

**2. L'entitat que es duplica de debò —i que produeix el símptoma— NO és `SizeFitting`: és `SizeCheck`.**
La columna «Real (proto)» no la toca cap `SizeFitting`. La resol
`SizeCheckLine.valor_real` ([CheckMeasureEditor.jsx:238](frontend/src/components/model/CheckMeasureEditor.jsx#L238)).
I `SizeCheck` és **explícitament repetible per disseny**: [models.py:1207-1208](backend/fhort/models_app/models.py#L1207-L1208)
diu literalment *«Historial repetible: SENSE unique_together — un model pot acumular N checks»*.
A staging hi ha **12 SizeCheck per a 7 models**; un model en té 3 i un altre en té 4.

**3. El camí que fa néixer un de nou en tancar-ne un existeix, i és una sola línia.**
[services_size_check.py:103-106](backend/fhort/models_app/services_size_check.py#L103-L106) reutilitza
**només** el check amb `estat='Pendent'`. En resoldre'l deixa de ser `Pendent` → el següent `open`
cau a [services_size_check.py:116](backend/fhort/models_app/services_size_check.py#L116) i **crea un
de nou amb totes les línies a `valor_real=None`**. Això és, exactament i literalment, «en tancar-ne
un en neix un de nou amb la columna Real buida».

**4. Les dades ho confirmen amb temps de màquina, no d'humà.** Cada check nou dels models 182 i 185
va néixer **entre 117 i 145 mil·lisegons** després que el seu germà es resolgués. La cadena de codi
que ho produïa està identificada al detall (§Q4-C): `onFeedback` era una **dependència del
`useCallback` de `load`** a la versió de juny, i `doResolve` el cridava → re-render del pare → nova
identitat d'`onFeedback` → `load()` es tornava a disparar **encara en mode treball** → `open()` →
check nou buit. Avui aquesta dependència ja no hi és, però **la regla de fons no ha canviat**: un
`open` en mode treball després d'una resolució segueix creant-ne un de nou i buit.

**5. Sí que hi ha, AVUI i amb dades reals, una pantalla que mostra un valor que no és el vigent.**
Dos casos provats, tots dos a §Q7. El més net és el **model 185**: té 3 checks, **tots `Acceptat`,
cap `Pendent`**. El lector de consulta ([ModelSheet.jsx:661](frontend/src/pages/ModelSheet.jsx#L661))
ensenya el check 22 amb `valor_real = 61.1` per al POM 273; el lector de treball
([ModelSheet.jsx:652](frontend/src/pages/ModelSheet.jsx#L652)) no troba cap `Pendent`, en crea un de
nou i ensenya `60.5`. **Dues pantalles del mateix model, dos números.**

**6. Els 53 tests que peten des del 28/07 són un fenomen DIFERENT del símptoma de l'Agus**, i la seva
causa no és una constraint nova. La constraint `(model_id, numero)` viu a
[0001_initial.py:108](backend/fhort/fitting/migrations/0001_initial.py#L108) **des del 25/05/2026**
(commit `0cd24539`). El que va canviar és el **signal**: `a2d4222d` (**20/07/2026**) va treure el
`if not instance.responsable_id: return` i el signal va passar a crear el SizeFitting **SEMPRE**. Els
`setUp` que creen un `Model` i tot seguit el seu propi `SizeFitting(numero=1)` xoquen des d'aleshores.

**7. Producció NO produeix el duplicat per aquesta via.** El signal està guardat
([signals.py:114](backend/fhort/models_app/signals.py#L114): `if SizeFitting.objects.filter(model=instance).exists(): return`).
Els 53 són **higiene de fixtures**, destapada per un canvi legítim de producció.

**8. El forat d'atomicitat de `generar-grading` (Q8) és INDEPENDENT del duplicat de SizeFitting.**
Viu un nivell més avall (`GradingVersion` dins d'UN SizeFitting). Sobre el `SizeFitting` la
constraint `(model, numero)` **protegeix**: dues peticions creuades calculen totes dues `numero=1` i
una rep `IntegrityError` → 500, no un duplicat.

---

## Q1 · QUANTES N'HI HA

### Q1.1 · Recompte per schema

```sql
-- fhort
select count(*) total_sf, count(distinct model_id) models from fhort.fitting_sizefitting;
 total_sf | models_amb_sf
----------+---------------
       46 |            44

select n_sf, count(*) n_models from (select model_id, count(*) n_sf
  from fhort.fitting_sizefitting group by 1) t group by 1 order by 1;
 n_sf | n_models
------+----------
    1 |       42
    2 |        2      ← cap model amb 3 ni 4+

-- los
 total_sf | models_amb_sf      n_sf | n_models
----------+---------------     ------+----------
       51 |            51         1 |       51   ← cap duplicat a `los`
```

### Q1.2 · Distribució de `numero` i d'`estat` (fhort)

| `numero` | files |     | `estat` | files |
|---|---|---|---|---|
| 1 | 44 | | `Pendent` | 35 |
| 2 | 2 | | `TallesGenerades` | 8 |
| | | | `Tancat` | 3 |

**Models amb més d'un SizeFitting en estat NO tancat: `0`.**

```sql
select count(*) from (select model_id from fhort.fitting_sizefitting
  where estat <> 'Tancat' group by 1 having count(*)>1) t;   -- → 0
```

Aquesta xifra és la que desactiva la meitat de la sospita del brief: **no hi ha dues sessions de
talles vives competint**. Quan n'hi ha dues, la segona sempre està `Tancat`.

### Q1.3 · Els dos models que en tenen 2 — qui, quan, en quin estat, amb quina GradingVersion

```sql
select model_id, id, numero, codi, tipus, estat, data_creacio, data_tancament,
       base_tancada, sf_pare_id, creat_per_id
from fhort.fitting_sizefitting
where model_id in (select model_id from fhort.fitting_sizefitting group by 1 having count(*)>1)
order by model_id, numero;
```

| model | sf id | numero | codi | tipus | estat | data_creacio | data_tancament | base_tancada | sf_pare | creat_per |
|---|---|---|---|---|---|---|---|---|---|---|
| **163** | 53 | 1 | `BRW-FW26-0001-SF1` | Proto | `TallesGenerades` | 2026-06-10 08:55:01 | *(null)* | `f` | *(null)* | 14 |
| **163** | 79 | 2 | `IMP-163-2` | SizeSet | `Tancat` | 2026-07-13 08:13:48 | *(null)* | `t` | *(null)* | 1 |
| **174** | 64 | 1 | `BRW-FW26-0012-SF1` | Proto | `TallesGenerades` | 2026-06-10 08:55:01 | *(null)* | `f` | *(null)* | 14 |
| **174** | 186 | 2 | `IMP-174-2` | SizeSet | `Tancat` | 2026-07-21 20:33:00 | *(null)* | `t` | *(null)* | 1 |

**Diferència de temps entre germans: 33 dies (model 163) i 41 dies (model 174).** No és una
condició de cursa ni un doble clic: són dos actes separats per més d'un mes.

Tres senyals que identifiquen l'autor sense ambigüitat:
- El prefix `IMP-` només el genera **una** línia de tot el codi:
  [extraction_views.py:2625](backend/fhort/models_app/extraction_views.py#L2625) i
  [:2628](backend/fhort/models_app/extraction_views.py#L2628) (`sf_codi = f"IMP-{model.id}-{next_num}"`).
- `sf_pare_id` és **NULL** als dos: el germà nou **no declara parentiu** amb el que ja hi havia.
- `data_tancament` és **NULL** tot i `estat='Tancat'`: no s'ha tancat pel camí de tancament (que
  estampa `data_tancament_base`, [pom/services.py:545](backend/fhort/pom/services.py#L545)), sinó
  que **ha nascut ja tancat** ([extraction_views.py:2750-2756](backend/fhort/models_app/extraction_views.py#L2750-L2756):
  `estat='Tancat', base_tancada=True`).

**GradingVersion associada** — aquesta taula és la que treu el nas al risc real:

```sql
select sf.model_id, sf.numero, sf.id sf_id, sf.estat, gv.id gv_id, gv.version_number,
       gv.is_active, count(gs.id) n_specs
from fhort.fitting_sizefitting sf
left join fhort.fitting_gradingversion gv on gv.size_fitting_id = sf.id
left join fhort.fitting_gradedspec gs on gs.grading_version_id = gv.id
where sf.model_id in (163,174) group by 1,2,3,4,5,6,7 order by 1,2,6;
```

| model | numero | sf_id | estat | gv_id | version | is_active | GradedSpec |
|---|---|---|---|---|---|---|---|
| 163 | 1 | 53 | TallesGenerades | 79 | 1 | `f` | 125 |
| 163 | 1 | 53 | TallesGenerades | 80 | 2 | `f` | 100 |
| 163 | 1 | 53 | TallesGenerades | 81 | 3 | **`t`** | 96 |
| 163 | **2** | 79 | Tancat | *(cap)* | — | — | **0** |
| 174 | 1 | 64 | TallesGenerades | 82 | 1 | `f` | 168 |
| 174 | 1 | 64 | TallesGenerades | 83 | 2 | `f` | 95 |
| 174 | 1 | 64 | TallesGenerades | 84 | 3 | **`t`** | 36 |
| 174 | **2** | 186 | Tancat | *(cap)* | — | — | **0** |

**Tota la vida de grading viu al SizeFitting nº1.** El nº2 té **zero** GradingVersion i **zero**
GradedSpec: és un contenidor buit. Coherent amb el comentari de l'autor
([extraction_views.py:2745-2748](backend/fhort/models_app/extraction_views.py#L2745-L2748)):
*«el grading PROPAGAT no es reté: el projecta el motor després»*.

37 dels 46 SizeFitting de `fhort` no tenen cap GradingVersion (la majoria són `Pendent`, models
sembrats que encara no han graduat mai).

### Q1.4 · Creuament amb el corpus

| | fhort | los |
|---|---|---|
| Models | **44** | 51 |
| SizeFitting | **46** | 51 |
| BaseMeasurement | **602** | **0** |
| SizeCheck | **12** (7 models) | **0** |

**Veredicte de Q1: el patró NO és general. És d'uns pocs — de dos.** I tots dos són models de QA
(163 i 174) que han passat pel wizard d'import després de tenir ja una vida de grading. El tenant
`los` (catàleg federat, sense feina de mesures: 0 BaseMeasurement, 0 SizeCheck) no en té cap.

---

## Q2 · QUI EN CREA — cens exhaustiu

Cens obtingut amb (buscant `objects.create` / `get_or_create` / `update_or_create` / `bulk_create` /
constructor sobre `SizeFitting`, exclosos `tests`/`migrations`):

```
grep -rn "SizeFitting" --include=*.py fhort/ | grep -vE "/tests?/|test_|/migrations/" \
  | grep -E "objects\.(create|get_or_create|update_or_create|bulk_create)|SizeFitting\("
```

`get_or_create` i `update_or_create` sobre `SizeFitting`: **NO EXISTEIXEN a producció** (l'únic
`get_or_create` del corpus és [patterns/tests.py:2197](backend/fhort/patterns/tests.py#L2197), que és
un test). Cap `SizeFitting(...).save()` solt fora dels llocs de sota.

### N1 · `sync_size_fitting` — **el signal** · [signals.py:85-141](backend/fhort/models_app/signals.py#L85-L141)

| | |
|---|---|
| **Qui el crida** | `post_save` de `models_app.Model`, **només amb `created=True`** ([:110-111](backend/fhort/models_app/signals.py#L110-L111)) |
| **Acte humà o efecte lateral** | **Efecte lateral pur.** Ningú el demana; qualsevol alta de Model el dispara. |
| **Càlcul del `numero`** | **Literal `1`** ([:129](backend/fhort/models_app/signals.py#L129): `number = 1`) |
| **Comprova abans?** | **SÍ** — [:114](backend/fhort/models_app/signals.py#L114) `if SizeFitting.objects.filter(model=instance).exists(): return` |
| **Codi** | `f"{instance.codi_intern}-SF{number}"` |
| **Estat inicial** | `tipus='Proto'`, `estat='Pendent'`, `base_tancada=False` |

L'actor per satisfer el `PROTECT` de `creat_per` es resol
`responsable → created_by → UserProfile.objects.first()` ([:117-127](backend/fhort/models_app/signals.py#L117-L127)).
**Aquest fallback és l'origen dels 53 tests** (§Q6). Tot el cos va embolicat en un `try/except` que
només fa `logging.warning` ([:139-141](backend/fhort/models_app/signals.py#L139-L141)): **si aquí
salta un `IntegrityError`, en producció es perd en silenci**.

### N2 · Wizard d'import · [extraction_views.py:2622-2628 + :2750-2756](backend/fhort/models_app/extraction_views.py#L2622-L2628)

| | |
|---|---|
| **Qui el crida** | Confirmació del pas final del wizard d'import guiat |
| **Acte humà o efecte lateral** | **Acte humà** (l'usuari confirma) **amb un efecte lateral no demanat**: el SizeFitting nou no és cap cosa que l'usuari hagi demanat ni vegi |
| **Càlcul del `numero`** | **Primer lliure**: `next_num=1; while SizeFitting.objects.filter(model=model, numero=next_num).exists(): next_num += 1` ([:2622-2624](backend/fhort/models_app/extraction_views.py#L2622-L2624)) + un segon bucle per col·lisió de `codi` ([:2626-2628](backend/fhort/models_app/extraction_views.py#L2626-L2628)) |
| **Comprova abans?** | **NO — i és deliberat.** No pregunta «ja n'hi ha un de viu?»: pregunta «quin número queda lliure?». Per disseny, **sempre en crea un de nou**. |
| **Estat inicial** | `tipus='SizeSet'`, **`estat='Tancat'`, `base_tancada=True`** |

**Aquest és, i només aquest, l'autor dels 2 duplicats de staging.** El `codi` `IMP-163-2` /
`IMP-174-2` no el pot haver escrit cap altra línia del sistema.

### N3 · `get_or_create_size_fitting` · [pom/services.py:473-496](backend/fhort/pom/services.py#L473-L496)

| | |
|---|---|
| **Qui el crida** | `close_table_view` ([views.py:1587](backend/fhort/models_app/views.py#L1587)) i altres consumidors de la porta de tancament |
| **Acte humà o efecte lateral** | Acte humà (tancar la taula), amb creació **només si no n'hi ha cap** |
| **Càlcul del `numero`** | `next_num=1`, incrementat **només per col·lisió de `codi`** ([:479-481](backend/fhort/pom/services.py#L479-L481)) |
| **Comprova abans?** | **SÍ** — [:473](backend/fhort/pom/services.py#L473) `filter(model=model).order_by('numero').first()`; si n'hi ha, **retorna i no crea** |

⚠️ *Anotació (fora de scope, no és el símptoma):* el bucle de [:479](backend/fhort/pom/services.py#L479)
incrementa `next_num` per col·lisió de **`codi`**, i aquest `next_num` és el que va al camp `numero`
([:495-496](backend/fhort/pom/services.py#L495-L496)). Com que només s'arriba aquí quan el model no
té cap SizeFitting, es podria encunyar un `numero=2` sense que existeixi el `numero=1`. Latent avui
(cap fila així al corpus), però és una incoherència entre els dos eixos.

### N4 · `generate_grading_view` · [views.py:2426-2441](backend/fhort/models_app/views.py#L2426-L2441)

| | |
|---|---|
| **Qui el crida** | `POST /api/v1/models/<id>/generar-grading/` — el botó «Propagar a grading» |
| **Acte humà o efecte lateral** | Acte humà; creació només si no n'hi ha cap |
| **Càlcul del `numero`** | Idèntic a N3 (`next_num=1` + bucle per col·lisió de `codi`) |
| **Comprova abans?** | **SÍ** — [:2426](backend/fhort/models_app/views.py#L2426) `SizeFitting.objects.filter(model=model).first()` |

El `.first()` de :2426 **no és aleatori** (v. §Q3): el `Meta.ordering` fa la tria per ell.

### N5 · `bulk_import_service` · [bulk_import_service.py:536-540](backend/fhort/models_app/bulk_import_service.py#L536-L540)

| | |
|---|---|
| **Qui el crida** | Import massiu multi-peça |
| **Acte humà o efecte lateral** | Acte humà (import), creació en bloc |
| **Càlcul del `numero`** | **Literal `1`** |
| **Comprova abans?** | **NO** — però **no cal**: els Models s'han creat amb `Model.objects.bulk_create` a [:533](backend/fhort/models_app/bulk_import_service.py#L533), que **bypassa els signals** (documentat a [:531](backend/fhort/models_app/bulk_import_service.py#L531)). El signal N1 no ha corregut → no hi ha res amb què xocar. **Coherent.** |

### N6 · `clone_model_for_qa` · [clone_model_for_qa.py:106-108](backend/fhort/models_app/management/commands/clone_model_for_qa.py#L106-L108)

Management command de QA. **NO és producció.** Es cita per completesa del cens.

### Q2 · LA PREGUNTA DIRECTA — **quin camí crea un SizeFitting nou en TANCAR-NE un?**

**CAP. Confirmat, no suposat.** La porta de tancament és
[`close_table_view`](backend/fhort/models_app/views.py#L1558-L1594):

1. [views.py:1587](backend/fhort/models_app/views.py#L1587) → `get_or_create_size_fitting(model, ...)`
   → N3, que **retorna l'existent** ([pom/services.py:473-475](backend/fhort/pom/services.py#L473-L475)).
2. [views.py:1588](backend/fhort/models_app/views.py#L1588) → `close_base(sf.id, ...)`
   → [pom/services.py:519](backend/fhort/pom/services.py#L519) fa `SizeFitting.objects.get(pk=...)`
   i [pom/services.py:545](backend/fhort/pom/services.py#L545) **muta la fila existent** amb un
   `.update()`. Cap `create` en tot el recorregut.

Tot dins d'un `transaction.atomic()` ([views.py:1586](backend/fhort/models_app/views.py#L1586)).

**Per tant la columna Real buida NO ve del SizeFitting. Ve d'una altra banda, i és §Q4.**

---

## Q3 · QUI DECIDEIX QUIN ÉS EL VIGENT

### Q3.0 · La premissa que ho governa tot: el `Meta.ordering`

[fitting/models.py:56](backend/fhort/fitting/models.py#L56):

```python
class Meta:
    ordering = ['model', 'numero']
```

Django 6.0.5 (`venv/lib/python3.14/site-packages/django`), `QuerySet.first()`
(`django/db/models/query.py:1138-1144`):

```python
def first(self):
    if self.ordered:          # ← True si el model té Meta.ordering
        queryset = self
    else:
        queryset = self.order_by("pk")
```

i `QuerySet.ordered` (`query.py:1862-1876`) retorna `True` *«si té una clàusula `order_by()` **o una
ordenació per defecte al model**»*.

**Conseqüència verificada, no suposada:** `SizeFitting.objects.filter(model=m).first()` **NO queda a
mans del planner**. Emet `ORDER BY model_id, numero` i retorna sempre **el `numero` MÉS BAIX**, és a
dir **el MÉS ANTIC**. Això és determinista — i és, alhora, la forma exacta del símptoma «no ha
recuperat l'última sinó una ANTERIOR».

### Q3.1 · Taula de lectors

| # | Node | Criteri de tria | Qui guanya |
|---|---|---|---|
| L1 | [views.py:2426](backend/fhort/models_app/views.py#L2426) `generate_grading_view` | `.filter(model).first()` **sense `order_by` explícit** → `Meta.ordering` | **`numero` ASC** (el més antic) |
| L2 | [pom/services.py:473](backend/fhort/pom/services.py#L473) `get_or_create_size_fitting` | `.order_by('numero').first()` — explícit | **`numero` ASC** |
| L3 | [fitting/services.py:541-551](backend/fhort/fitting/services.py#L541-L551) `_resolve_working_size_fitting` | **Primer el que tingui una `GradingVersion` `is_active`**; si cap, `numero` ASC | **per GradingVersion activa** ← **criteri DIFERENT** |
| L4 | [wizard_views.py:177](backend/fhort/pom/wizard_views.py#L177) | `model.size_fittings.filter(numero=1)` — **literal codificat** | **només el `numero=1`** |
| L5 | [wizard_views.py:282](backend/fhort/pom/wizard_views.py#L282) | `model.size_fittings.filter(numero=1).first()` — **literal codificat** | **només el `numero=1`** |
| L6 | [views.py:1760](backend/fhort/models_app/views.py#L1760) `measurements_table_view` | `.filter(model, estat='Tancat').exists()` — **no tria cap SizeFitting: pregunta si N'HI HA ALGUN de tancat** | **qualsevol germà tancat contamina el model sencer** ← **criteri DIFERENT** |
| L7 | [fitting/views.py:58-69](backend/fhort/fitting/views.py#L58-L69) `SizeFittingViewSet` | `ordering = ['model','numero']` + `OrderingFilter` (el client pot demanar `data_creacio`) | `numero` ASC per defecte, **negociable pel client** |
| L8 | [pom/s6_views.py:146](backend/fhort/pom/s6_views.py#L146) · [pom/grading_views.py:98](backend/fhort/pom/grading_views.py#L98) · [pom/services.py:184](backend/fhort/pom/services.py#L184) · [:519](backend/fhort/pom/services.py#L519) · [:947](backend/fhort/pom/services.py#L947) | `.get(pk=sf_id)` — **el `pk` ve de fora** | no tria: hereta la tria de qui li passa l'id |
| L9 | [clone_model_for_qa.py:124](backend/fhort/models_app/management/commands/clone_model_for_qa.py#L124) | `.filter(model=src).first()` | `numero` ASC *(no és producció)* |

`_resolve_working_size_fitting` (L3) és el resolutor més utilitzat: **12 punts de crida**
(`fitting/services.py:307`, `:619`; `models_app/views.py:1649`, `:2688`, `:2772`, `:2927`, `:3329`,
`:4130`).

### Q3.2 · **Hi ha, doncs, tres criteris incompatibles conviuen sobre la mateixa pregunta**

1. **`numero` ASC** (L1, L2, L7, L9) — «el vigent és el primer que va néixer».
2. **GradingVersion activa** (L3) — «el vigent és el que té feina de grading viva».
3. **`numero=1` literal** (L4, L5) — «el vigent és, per definició, l'u».
4. **Cap tria: la disjunció** (L6) — «si algun està tancat, el model està tancat».

Sobre els models 163 i 174, **1, 2 i 3 convergeixen** al SizeFitting nº1 (perquè és el nº1 **i** és
el que té la GradingVersion activa — v. taula de §Q1.3). **4 divergeix**: v. §Q7.2.

**La convergència d'avui és una coincidència de les dades, no una garantia del codi.** N'hi ha prou
que un import creï el contenidor `Tancat` **abans** que el model hagi graduat mai (cas perfectament
possible: import guiat sobre model verge) perquè L3 i L1/L2 apuntin a SizeFitting diferents.

---

## Q4 · LA COLUMNA «REAL (PROTO)» — d'on surt exactament

### Q4-A · Cadena completa, frontend → backend

**Etiqueta.** [`ca.json:2479`](frontend/src/i18n/ca.json#L2479) `"sizecheck.col_real": "Real (proto)"`
(en: `"Actual (proto)"`). Un únic consumidor a tot el frontend:
[CheckMeasureEditor.jsx:210](frontend/src/components/model/CheckMeasureEditor.jsx#L210)
(`activeLabel: ctx.t('sizecheck.col_real')`), dins de `checkSource.buildGroups`.

**Qui l'alimenta.** [CheckMeasureEditor.jsx:238](frontend/src/components/model/CheckMeasureEditor.jsx#L238):

```js
active: line ? { lineId: line.id, value: line.valor_real ?? line.valor_teoric,
                 baseValue: line.valor_teoric, ... } : null,
```

on `line` ve de `raw.check.lines` indexat per `pom_id`
([:216-217](frontend/src/components/model/CheckMeasureEditor.jsx#L216-L217)).

**L'entitat, doncs, és `SizeCheckLine`** ([models_app/models.py:1242](backend/fhort/models_app/models.py#L1242)),
**no** `PieceFittingLine` ni `GradedSpec`. La columna germana «Mesura» ve d'un altre lloc:
`models.baseStages(model.id)` → [`base_stages_view`, views.py:3046](backend/fhort/models_app/views.py#L3046),
que llegeix `BaseMeasurement` + `MeasurementChangeLog` i **no toca `SizeFitting` en cap moment**.

**L'escriptura.** [CheckMeasureEditor.jsx:246](frontend/src/components/model/CheckMeasureEditor.jsx#L246)
→ `sizeCheckLines.update(lineId, { valor_real: value })` → `PATCH /api/v1/size-check-lines/<pk>/`
→ [views_size_check.py:78-88](backend/fhort/models_app/views_size_check.py#L78-L88).

### Q4-B · **Quin SizeFitting es fa servir per resoldre-la: CAP**

Confirmat, no suposat. `SizeCheck` i `SizeCheckLine`
([models_app/models.py:1206-1290](backend/fhort/models_app/models.py#L1206-L1290)) **no tenen cap FK
a `SizeFitting`**. Les seves FK són: `SizeCheck.model` → `models_app.Model`; `SizeCheckLine.size_check`
→ `SizeCheck`; `SizeCheckLine.pom` → `pom.POMMaster`. El comentari de capçalera
([:1204-1205](backend/fhort/models_app/models.py#L1204-L1205)) ho diu explícitament: *«Entitat NETA
(no reusa PieceFitting) … viu a `models_app` perquè toca Model + BaseMeasurement»*.

**Ni `services_size_check.py` ni `views_size_check.py` importen `SizeFitting` ni una sola vegada**
(grep exhaustiu buit sobre els dos fitxers).

> **Corol·lari que canvia el marc de la investigació:** el que l'Agus anomena «tancar un size
> fitting» **no toca cap `SizeFitting`**. És resoldre un `SizeCheck`. Per això la caça del duplicat
> de `SizeFitting` (Q1) troba només 2 models: buscava l'entitat equivocada.

### Q4-C · **Per què queda buida després d'un tancament** — la línia exacta

[services_size_check.py:103-120](backend/fhort/models_app/services_size_check.py#L103-L120):

```python
existing = (
    SizeCheck.objects.filter(model=model, estat='Pendent')   # ← [:104] EL FILTRE
    .order_by('-created_at').first()
)
if existing is not None:
    creades = _materialize_lines(existing, model)
    ...
    return existing, n

sc = SizeCheck.objects.create(                                # ← [:116] LA CREACIÓ
    model=model, estat='Pendent', ...
)
```

I `_materialize_lines` ([:64-71](backend/fhort/models_app/services_size_check.py#L64-L71)) crea cada
línia amb **`valor_real=None`** ([:70](backend/fhort/models_app/services_size_check.py#L70), amb el
comentari `# el tècnic l'anota`).

`resolve_size_check` ([:320-323](backend/fhort/models_app/services_size_check.py#L320-L323)) escriu
`sc.estat = final_estat` (`Acceptat` / `Rebutjat` / `Descartat`) — **mai `Pendent`**.

**La mecànica, doncs, és:**

> Resoldre un check el treu de `estat='Pendent'` → la propera crida a `open_size_check` **no el troba**
> → cau a [:116](backend/fhort/models_app/services_size_check.py#L116) i **en crea un de nou amb totes
> les línies a `valor_real=None`** → la columna «Real (proto)» surt buida i ensenya el
> `valor_teoric` pel `??` de [CheckMeasureEditor.jsx:238](frontend/src/components/model/CheckMeasureEditor.jsx#L238).

**Verificat que `open_size_check` és l'ÚNIC punt de creació de `SizeCheck` a producció.** Grep
exhaustiu de `SizeCheck.objects.create` / `SizeCheck(`: **9 dels 10 encerts són fitxers de test**;
l'únic de producció és [services_size_check.py:116](backend/fhort/models_app/services_size_check.py#L116).
I `open_size_check` només té **un** cridador de producció:
[views_size_check.py:55](backend/fhort/models_app/views_size_check.py#L55) ← `POST /api/v1/size-checks/open/`
([endpoints.js:699](frontend/src/api/endpoints.js#L699)) ← **una sola línia del frontend**:
[CheckMeasureEditor.jsx:195](frontend/src/components/model/CheckMeasureEditor.jsx#L195), a la branca
`readOnly === false`. `resolve_size_check` **NO crea** cap check (verificat llegint-lo sencer,
[:144-341](backend/fhort/models_app/services_size_check.py#L144-L341)).

### Q4-D · La prova a les dades: temps de màquina, no d'humà

```sql
select id, model_id, estat, created_at, resolt_at,
       (select count(*) from fhort.models_app_sizecheckline l where l.size_check_id=sc.id) n_lin,
       (select count(*) from fhort.models_app_sizecheckline l
         where l.size_check_id=sc.id and l.valor_real is not null) n_real
from fhort.models_app_sizecheck sc order by model_id, created_at;
```

| id | model | estat | created_at | resolt_at | línies | amb `valor_real` |
|---|---|---|---|---|---|---|
| 24 | 164 | Pendent | 2026-06-26 07:31:06 | — | 0 | 0 |
| 26 | 166 | Pendent | 2026-07-12 07:42:26 | — | 0 | 0 |
| 27 | 169 | Pendent | 2026-07-20 06:34:40 | — | 0 | 0 |
| 16 | **182** | Acceptat | 2026-06-16 19:10:14 | 2026-06-16 19:11:28 | 14 | 2 |
| 17 | **182** | Acceptat | 2026-06-22 07:20:29 | **2026-06-23 17:54:45.819766** | 14 | 1 |
| 20 | **182** | Acceptat | **2026-06-23 17:54:45.951750** | 2026-06-23 17:59:59.971923 | 14 | **0** |
| 21 | **182** | Pendent | **2026-06-23 18:00:00.091236** | — | 14 | 1 |
| 18 | **185** | Acceptat | 2026-06-22 15:56:25 | **2026-06-23 07:16:20.394338** | 2 | 1 |
| 19 | **185** | Acceptat | **2026-06-23 07:16:20.539456** | 2026-06-24 12:07:24.540924 | 2 | **0** |
| 22 | **185** | Acceptat | **2026-06-24 12:07:24.657800** | 2026-07-12 07:41:06 | 2 | 2 |
| 23 | 186 | Pendent | 2026-06-24 16:42:02 | — | 20 | 0 |
| 25 | 188 | Pendent | 2026-07-10 21:30:34 | — | 10 | 0 |

**Quatre naixements consecutius, quatre `resolt_at` immediatament anteriors:**

| germà resolt a | germà nou nascut a | **interval** |
|---|---|---|
| 17 → 17:54:45.819766 | 20 → 17:54:45.951750 | **+132 ms** |
| 20 → 17:59:59.971923 | 21 → 18:00:00.091236 | **+119 ms** |
| 18 → 07:16:20.394338 | 19 → 07:16:20.539456 | **+145 ms** |
| 19 → 12:07:24.540924 | 22 → 12:07:24.657800 | **+117 ms** |

**117–145 ms és una segona petició HTTP dins de la mateixa interacció.** No hi ha cap humà en aquest
interval. I dos dels quatre fills (20 i 19) van néixer amb **0 valors reals** — la columna buida,
exactament tal com l'Agus la descriu.

### Q4-E · La cadena de codi que ho produïa, identificada

La versió d'aquell moment (commit `ad10e4ad`, l'últim abans del 24/06) té:

`frontend/src/components/model/CheckMeasureEditor.jsx` @ `ad10e4ad`:
```js
const load = useCallback(() => {
  const checkP = readOnly
    ? sizeChecks.list({ model: model.id, ordering: '-created_at', page_size: 1 })...
    : sizeChecks.open(model.id).then(...)          // línia 190
  ...
}, [model.id, readOnly, onFeedback, t])            // línia 196  ← onFeedback A LES DEPS
useEffect(() => { load() }, [load])                // línia 198
...
  .then(r => { ... onFeedback?.({ type: 'ok', text }); onResolved?.() })   // línia ~220
```

`frontend/src/pages/ModelMeasurements.jsx:204` @ `ad10e4ad`:
```jsx
onFeedback={(fb) => { ... setNotice(fb.text) }}    // ← fletxa INLINE: identitat nova cada render
```

**La cadena, tancada:** `doResolve` → resposta OK → `onFeedback({type:'ok'})` → `setNotice` al pare →
**re-render del pare** → **nova identitat de la fletxa `onFeedback`** → `load` es reconstrueix →
`useEffect` es torna a disparar → `load()` **encara amb `readOnly=false`** → `sizeChecks.open()` →
no hi ha cap `Pendent` (s'acaba de resoldre) → **`SizeCheck` nou i buit**. Interval: un round-trip
HTTP. **117–145 ms.**

**Estat AVUI (HEAD `55e13cab`):** les deps s'han reduït a
[`[model.id, readOnly, src, sourceCtx?.fittingSession]`](frontend/src/components/model/CheckMeasureEditor.jsx#L327),
amb un `// eslint-disable-next-line react-hooks/exhaustive-deps` a
[:326](frontend/src/components/model/CheckMeasureEditor.jsx#L326). `onFeedback` i `t` han sortit.
El re-dispar **immediat** està tancat.

**Però la regla de fons no ha canviat.** L'`open` segueix filtrant `estat='Pendent'`
([:104](backend/fhort/models_app/services_size_check.py#L104)) i seguint creant-ne un de nou quan no
en troba ([:116](backend/fhort/models_app/services_size_check.py#L116)). **Qualsevol** entrada
posterior a la tab Mesures en mode treball ([ModelSheet.jsx:652](frontend/src/pages/ModelSheet.jsx#L652),
`readOnly={false}`) després d'haver resolt un check **crea un check nou amb la columna Real buida**.
Ja no en 120 ms, sinó el proper cop que el tècnic hi entri — que és el que l'Agus veu.

---

## Q5 · LA UNICITAT I EL 28/07

### Q5.1 · Quan va entrar la constraint `(model_id, numero)`

[`backend/fhort/fitting/migrations/0001_initial.py:108`](backend/fhort/fitting/migrations/0001_initial.py#L108):

```python
'unique_together': {('model', 'numero')},
```

```
$ git log -1 --format='%ad %h' -- backend/fhort/fitting/migrations/0001_initial.py
Mon May 25 18:01:03 2026 +0000 0cd24539
```

I al model viu: [fitting/models.py:57](backend/fhort/fitting/models.py#L57).

**La constraint és de la migració INICIAL, del 25/05/2026. Abans no hi havia «res»: no hi havia
taula.** Mai s'ha afegit, alterat ni reintroduït (cap altra migració de `fitting/` toca
`('model','numero')`; l'únic altre `unique_together` amb `numero` és
[0001_initial.py:184](backend/fhort/fitting/migrations/0001_initial.py#L184), que és
`('size_fitting','numero')` d'una altra taula).

### Q5.2 · **Resposta directa: NO, no va entrar el 28/07 ni a prop.**

La hipòtesi del brief («llavors els 53 no són una regressió de codi sinó una restricció nova que va
destapar un duplicat que ja existia») **queda descartada**. La restricció té 10 setmanes més que el
símptoma.

**El que sí que va canviar, i és la causa real:** commit **`a2d4222d`, 20/07/2026**,
*«fix(fitting): el signal crea SEMPRE el SizeFitting (forat universal B2)»*:

```diff
-    if not instance.responsable_id:
-        return  # We cannot create an SF without creat_per
-
     try:
         from fhort.fitting.models import SizeFitting
         if SizeFitting.objects.filter(model=instance).exists():
             return
+        actor_id = instance.responsable_id or instance.created_by_id
+        if actor_id is None:
+            from fhort.accounts.models import UserProfile
+            first = UserProfile.objects.first()
+            actor_id = first.id if first else None
```

**Abans del 20/07** els `Model` de fixture (que no fixen `responsable`) feien que el signal
**sortís sense crear res** → el `SizeFitting.objects.create(numero=1)` del `setUp` no xocava amb res.
**Des del 20/07** el signal cau al fallback `UserProfile.objects.first()` — i com que tots aquests
`setUp` creen el `UserProfile` **abans** del `Model`, el fallback l'hi troba i **crea el SizeFitting
nº1**. El `create` del fixture, a la línia següent, xoca.

> ⚠️ **Divergència declarada amb el brief:** la data que dona el símptoma és **28/07**; el commit que
> l'arma és del **20/07**. No he investigat què va passar el 28/07 (podria ser el dia en què es va
> córrer la suite per primer cop després del canvi, o un commit intermedi que reactivés el camí).
> **La causa mecànica queda provada per la lectura del diff i del `setUp`** (§Q6); la data exacta de
> la primera observació és un **límit declarat**.

### Q5.3 · Compatibilitat del càlcul del `numero` amb la constraint

| Node | Càlcul | Comprova `exists()` abans? | Compatible? |
|---|---|---|---|
| N1 signal ([:129](backend/fhort/models_app/signals.py#L129)) | literal `1` | **SÍ** ([:114](backend/fhort/models_app/signals.py#L114)) | **Sí** — el guard el salva |
| N2 import ([:2622-2624](backend/fhort/models_app/extraction_views.py#L2622-L2624)) | `while exists(numero=n): n+=1` — **max lliure** | *(deliberadament no)* | **Sí** — és l'únic que calcula bé el `numero` |
| N3 `get_or_create` ([:478-481](backend/fhort/pom/services.py#L478-L481)) | `1` + bump per col·lisió de **`codi`** | **SÍ** | **Sí** (amb l'anotació de §Q2-N3) |
| N4 `generate_grading` ([:2428-2432](backend/fhort/models_app/views.py#L2428-L2432)) | igual que N3 | **SÍ** | **Sí** |
| N5 `bulk_import` ([:536](backend/fhort/models_app/bulk_import_service.py#L536)) | literal `1` | **NO** | **Sí** — `bulk_create` de Models bypassa el signal ([:531](backend/fhort/models_app/bulk_import_service.py#L531)) |

**Cap `max+1` ni `count+1` a tot el corpus.** El patró és sempre «literal 1 amb guard» o «primer
número lliure». Tots dos són compatibles amb la constraint **sota concurrència zero**. Sota
concurrència, cap dels guards és un `select_for_update` → v. §Q8.

---

## Q6 · ELS 53, EXPLICATS — traçat línia a línia

Prenc **`PropagarActionTest`** ([fitting/tests.py:27](backend/fhort/fitting/tests.py#L27)), una de
les deu classes citades. El seu `setUp` ([:39-80](backend/fhort/fitting/tests.py#L39-L80)):

| línia | acció | efecte |
|---|---|---|
| [:41](backend/fhort/fitting/tests.py#L41) | `get_user_model().objects.create(username='tester')` | — |
| **[:42-43](backend/fhort/fitting/tests.py#L42-L43)** | `UserProfile.objects.get_or_create(...)` | **⚠️ ja hi ha un `UserProfile` al tenant** |
| [:45-53](backend/fhort/fitting/tests.py#L45-L53) | `SizeSystem`, `SizeDefinition`, `GradingRuleSet`, `POMMaster`, `GradingRule` | — |
| **[:55-59](backend/fhort/fitting/tests.py#L55-L59)** | `Model.objects.create(codi_intern='TST-1', ..., grading_rule_set=self.rs)` — **sense `responsable`, sense `created_by`** | **dispara `post_save` → `sync_size_fitting`** |
| ↳ [signals.py:110](backend/fhort/models_app/signals.py#L110) | `if not created: return` | `created=True` → **segueix** |
| ↳ [signals.py:114](backend/fhort/models_app/signals.py#L114) | `if SizeFitting.objects.filter(model=instance).exists(): return` | encara no n'hi ha cap → **segueix** |
| ↳ [signals.py:117](backend/fhort/models_app/signals.py#L117) | `actor_id = responsable_id or created_by_id` | tots dos `None` → **segueix** |
| ↳ [signals.py:118-121](backend/fhort/models_app/signals.py#L118-L121) | `actor_id = UserProfile.objects.first().id` | **el troba: és `self.profile` de la línia :42** |
| ↳ [signals.py:129-138](backend/fhort/models_app/signals.py#L129-L138) | `SizeFitting.objects.create(model=instance, numero=1, codi='TST-1-SF1', ...)` | ✅ **SizeFitting `(model_id=3, numero=1)` CREAT** |
| **[:60-61](backend/fhort/fitting/tests.py#L60-L61)** | `SizeFitting.objects.create(model=self.model, codi='SF-TST-1', tipus='PRINCIPAL', numero=1, creat_per=self.profile)` | 💥 **`IntegrityError: fitting_sizefitting_model_id_numero_6dc01a35_uniq · Key (model_id, numero)=(3,1) already exists`** |

**Forma idèntica a la família `pom`** (les 24 restants), a `_SegellBase`
([pom/test_g6_segell.py:44](backend/fhort/pom/test_g6_segell.py#L44)):
`UserProfile` a [:51](backend/fhort/pom/test_g6_segell.py#L51) → `Model.objects.create` a
[:68](backend/fhort/pom/test_g6_segell.py#L68) → `SizeFitting.objects.create` a
[:79](backend/fhort/pom/test_g6_segell.py#L79). `_BancSegellat`
([fitting/test_g6_estalitud.py:22](backend/fhort/fitting/test_g6_estalitud.py#L22)) i
`EstalitudTest` / `R7UnaSolaActivaTest` hereten aquest `setUp` via `super().setUp()`
([test_g6_estalitud.py:33](backend/fhort/fitting/test_g6_estalitud.py#L33)) — d'aquí que la mateixa
petada es reprodueixi a 10 classes i 53 tests, i que es reparteixi **29 a `fhort.fitting` / 24 a
`fhort.pom`** tal com diu el brief.

### Q6 · **LA PREGUNTA QUE DECIDEIX: producció o tests?**

**Resposta: el SizeFitting que ja hi és quan el test intenta crear el seu el crea CODI DE PRODUCCIÓ
(el signal, [signals.py:131](backend/fhort/models_app/signals.py#L131)). Però el DUPLICAT —el fet que
n'hi hagi dos— el crea el FIXTURE.**

**I la producció no en pot produir cap per aquesta via.** Verificat amb prova, no per eliminació:

1. **Prova positiva de codi.** El guard de [signals.py:114](backend/fhort/models_app/signals.py#L114)
   (`if SizeFitting.objects.filter(model=instance).exists(): return`) fa que el signal no en creï mai
   un segon. **El fixture no té guard.** La diferència és exactament aquesta línia.
2. **Prova positiva de dades.** Si la producció generés duplicats per aquesta via, es veurien: cada
   `Model.objects.create` (44 a `fhort`, 51 a `los`) dispararia el signal. El corpus dona
   **42/44 amb exactament 1 i 51/51 amb exactament 1**. Els 2 que en tenen 2
   porten `codi = 'IMP-…'`, i el prefix `IMP-` només el pot escriure
   [extraction_views.py:2625](backend/fhort/models_app/extraction_views.py#L2625) — **no el signal**,
   que escriu `f"{codi_intern}-SF{number}"` ([:130](backend/fhort/models_app/signals.py#L130)).
   **Zero files de producció amb dos SizeFitting d'origen-signal.**
3. **Prova de causa temporal.** El diff de `a2d4222d` (§Q5.2) treu la condició que fins al 20/07
   feia que el signal no correguéssin en tests, i **no toca el guard**.

**Conseqüència operativa: els 53 són HIGIENE DE VERIFICACIÓ.** Els fixtures declaren un
`SizeFitting` que el sistema ja els regala. La producció, en aquest punt, està bé.

> ⚠️ **Però els 53 NO són soroll del tot, i val la pena dir-ho:** són l'única cosa que en 14 dies ha
> assenyalat que el signal ha canviat de comportament universal. I hi ha un residu real que el
> signal amaga: [signals.py:139-141](backend/fhort/models_app/signals.py#L139-L141) engoleix
> **qualsevol** excepció en un `logging.warning`. Si a producció hi hagués mai un xoc d'aquesta
> constraint, **no arribaria enlloc**: ni 500, ni alerta, ni traça a l'usuari. Anotat, no tocat.

---

## Q7 · ABAST DEL DANY

### Q7.1 · El dany REAL — la columna «Real (proto)»: **PROVAT amb dades de staging**

#### CAS A · Model 185 — dos lectors, dos números, avui

Estat de les dades: **3 checks, tots `Acceptat`, CAP `Pendent`** (§Q4-D).

```sql
select l.size_check_id, l.pom_id, l.valor_teoric, l.valor_real, l.decisio,
       bm.base_value_cm as base_vigent, bm.origen, bm.updated_at
from fhort.models_app_sizecheckline l
left join fhort.models_app_basemeasurement bm
       on bm.model_id=185 and bm.pom_id=l.pom_id and bm.is_active
where l.size_check_id in (18,19,22) order by l.size_check_id, l.pom_id;
```

| check | pom | `valor_teoric` | `valor_real` | decisió | **base vigent** | origen | updated_at |
|---|---|---|---|---|---|---|---|
| 18 | 273 | 60 | 60.5 | tolerancia_acceptada | 60.5 | FITTED | 2026-07-17 08:18:26 |
| 18 | 275 | 60 | *(null)* | tolerancia_acceptada | 60.4 | FITTED | 2026-07-17 08:18:26 |
| 19 | 273 | 60.5 | *(null)* | tolerancia_acceptada | 60.5 | FITTED | 2026-07-17 08:18:26 |
| 19 | 275 | 60 | *(null)* | tolerancia_acceptada | 60.4 | FITTED | 2026-07-17 08:18:26 |
| **22** | **273** | 60.5 | **61.1** | tolerancia_acceptada | **60.5** | FITTED | 2026-07-17 08:18:26 |
| **22** | **275** | 60 | **60.5** | tolerancia_acceptada | **60.4** | FITTED | 2026-07-17 08:18:26 |

**Qui veuria què, ara mateix, POM 273:**

| pantalla | node | camí | «Real (proto)» |
|---|---|---|---|
| **Mesures · CONSULTA** | [ModelSheet.jsx:661](frontend/src/pages/ModelSheet.jsx#L661) `readOnly` | [CheckMeasureEditor.jsx:193-195](frontend/src/components/model/CheckMeasureEditor.jsx#L193-L195) → `sizeChecks.list(ordering='-created_at', page_size=1)` → **check 22** | **`61.1`** (`valor_real`) |
| **Mesures · TREBALL** | [ModelSheet.jsx:652](frontend/src/pages/ModelSheet.jsx#L652) `readOnly={false}` | [CheckMeasureEditor.jsx:195](frontend/src/components/model/CheckMeasureEditor.jsx#L195) → `open()` → **cap `Pendent`** → [services_size_check.py:116](backend/fhort/models_app/services_size_check.py#L116) **crea un de nou** amb `valor_teoric=60.5`, `valor_real=None` | **`60.5`** (pel `??` de [:238](frontend/src/components/model/CheckMeasureEditor.jsx#L238)) |

**`61.1` contra `60.5`. Mateix model, mateix POM, mateixa columna, dues pantalles.** I entrar a la
pantalla de treball **crea una fila nova a la BD** — la lectura és una escriptura.

Els dos lectors divergeixen per **criteri**, no per casualitat: **consulta agafa el més recent de
QUALSEVOL estat; treball agafa el més recent `Pendent` i, si no n'hi ha, en fabrica un.**

#### CAS B · Model 182 — el teòric és un snapshot de fa 41 dies

El check 21 és `Pendent` des del **2026-06-23 18:00** i encara ho és avui (**03/08**).
`_materialize_lines` ho documenta explícitament
([services_size_check.py:26-29](backend/fhort/models_app/services_size_check.py#L26-L29)):
*«Les línies ja existents no es toquen —ni el seu `valor_teoric`—»*.

```sql
select l.pom_id, l.valor_teoric, l.valor_real, bm.base_value_cm, bm.origen, bm.updated_at
from fhort.models_app_sizecheckline l
join fhort.models_app_basemeasurement bm on bm.model_id=182 and bm.pom_id=l.pom_id and bm.is_active
where l.size_check_id=21 order by l.pom_id;
```

13 de 14 files coincideixen. **La catorzena, no:**

| pom | `valor_teoric` (snapshot 23/06) | `valor_real` | **base vigent** | origen | updated_at |
|---|---|---|---|---|---|
| **379** | **41.7** | 41.7 | **42.6** | `CHECKED` | **2026-06-24 18:35:23** |

La base es va moure a **42.6** el **24/06**, un dia **després** que el check 21 congelés el seu
teòric a 41.7. Avui la tab Mesures del model 182 ensenya **41.7** on el valor vigent és **42.6**.
**41 dies de desfasament, en dades reals, ara mateix.**

Aquest és, literalment, el segon símptoma de l'Agus: *«en fer una mesura nova, el sistema NO ha
recuperat l'última sinó una ANTERIOR»*.

### Q7.2 · El dany LATENT del `SizeFitting` — el flag `tancat`

[views.py:1756-1761](backend/fhort/models_app/views.py#L1756-L1761), dins de
`measurements_table_view` (`GET /api/v1/models/<id>/taula-mesures/`):

```python
tancat = SizeFitting.objects.filter(model=model, estat='Tancat').exists()
```

Amb el comentari a [:1756](backend/fhort/models_app/views.py#L1756):
*«Taula tancada? (SizeFitting estat='Tancat' → vista de només lectura al frontend)»*.

**No tria cap SizeFitting: pregunta si N'HI HA ALGUN de tancat.** Per als models 163 i 174:

```sql
select model_id, string_agg(numero||':'||estat, ', ' order by numero) sfs
from fhort.fitting_sizefitting
where model_id in (select model_id from fhort.fitting_sizefitting where estat='Tancat')
group by 1;
```

| model | SizeFitting |
|---|---|
| **163** | `1:TallesGenerades`, `2:Tancat` |
| **174** | `1:TallesGenerades`, `2:Tancat` |
| 188 | `1:Tancat` |

**Per als models 163 i 174 el SizeFitting de treball (nº1, el que té la GradingVersion activa —
§Q1.3) està OBERT, i tot i així l'endpoint retorna `tancat = true`.** El germà `Tancat` que va deixar
l'import contamina el veredicte del model sencer.

**Aquest dany és LATENT, no viu.** Els consumidors de `taula-mesures` són
[PropagatedEditor.jsx:31](frontend/src/pages/PropagatedEditor.jsx#L31),
[ModelSheet.jsx:136](frontend/src/pages/ModelSheet.jsx#L136) i [:153](frontend/src/pages/ModelSheet.jsx#L153),
i [MeasuresEntryPanel.jsx:71](frontend/src/components/model/MeasuresEntryPanel.jsx#L71), [:121](frontend/src/components/model/MeasuresEntryPanel.jsx#L121), [:185](frontend/src/components/model/MeasuresEntryPanel.jsx#L185).
**Cap d'ells consumeix el camp `tancat`** (grep de `tancat` sobre `frontend/src/pages/ModelSheet.jsx`
i `frontend/src/components/model/*.jsx`: **cap encert que llegeixi aquest camp**; els 5 encerts són
`data_tancament`, la paraula dins d'un comentari, o l'`estat === 'tancat'` d'un `Badge` de
[DashboardTab.jsx:189](frontend/src/components/model/DashboardTab.jsx#L189), que ve de `fitxa.estat`,
no d'aquí). **El backend menteix; avui ningú l'escolta.**

### Q7.3 · Pantalles afectades — resum

| Pantalla | Node | Risc | Estat |
|---|---|---|---|
| **Mesures · consulta** (`Real (proto)`) | [ModelSheet.jsx:661](frontend/src/pages/ModelSheet.jsx#L661) | Ensenya el `valor_real` d'un check **resolt** que pot no ser el vigent | 🔴 **VIU** (model 185: `61.1`) |
| **Mesures · treball** (`Real (proto)`) | [ModelSheet.jsx:652](frontend/src/pages/ModelSheet.jsx#L652) | Ensenya un `valor_teoric` **congelat** en obrir el check, o en fabrica un de nou i buit | 🔴 **VIU** (model 182 POM 379: `41.7` vs `42.6`; model 185: `60.5`) |
| **Escalat** (`PropagatedEditor`) | [PropagatedEditor.jsx:31](frontend/src/pages/PropagatedEditor.jsx#L31) → [views.py:1760](backend/fhort/models_app/views.py#L1760) | `tancat=true` fals per contaminació del germà | 🟡 **LATENT** (camp no consumit) |
| **Grading / propagar** | [views.py:2426](backend/fhort/models_app/views.py#L2426) (L1) vs [fitting/services.py:544](backend/fhort/fitting/services.py#L544) (L3) | Dos criteris de tria distints sobre el mateix model | 🟡 **LATENT** (avui convergeixen: §Q3.2) |
| **Wizard de POMs** | [wizard_views.py:177](backend/fhort/pom/wizard_views.py#L177), [:282](backend/fhort/pom/wizard_views.py#L282) | `numero=1` literal: si mai el nº1 no fos el de treball, escriuria al germà equivocat | 🟡 **LATENT** |

---

## Q8 · EL QUE JA SABEM — verificació

**Premissa del brief:** *«`generar-grading` NO té transacció i `ATOMIC_REQUESTS` no existeix; cap
`select_for_update` a tot el cicle → dues peticions simultànies es poden creuar a
`pom/services.py:876-880` i violar la invariant "una sola versió activa"»*.

**VERIFICAT.** [pom/services.py:875-877](backend/fhort/pom/services.py#L875-L877):

```python
version = (GradingVersion.objects
           .filter(size_fitting=sf, is_active=True)
           .order_by('-version_number').first())
if version is None:
    num = GradingVersion.objects.filter(size_fitting=sf).count() + 1
    version = GradingVersion.objects.create(size_fitting=sf, version_number=num, is_active=True)
```

Llegir-i-crear sense `select_for_update` i sense `atomic` embolcallant-ho. El propi comentari de
[:871-874](backend/fhort/pom/services.py#L871-L874) reconeix que el fork 3 de la diagnosi del motor
és *«latent —cap SizeFitting té 2+ actives—»*.

### **La resposta a la pregunta: SÓN COSES INDEPENDENTS.**

**Tres raons, cadascuna suficient:**

1. **Nivell diferent.** El forat de `_get_or_create_grading_version` opera sobre `GradingVersion`
   **dins d'UN `SizeFitting` ja resolt** (`sf` arriba per paràmetre). No pot crear-ne un de segon:
   el `sf` ja està triat abans d'entrar.

2. **Sobre `SizeFitting`, la constraint PROTEGEIX en comptes de fallar.** Si dues peticions
   simultànies a `generar-grading` arribessin a [views.py:2426](backend/fhort/models_app/views.py#L2426)
   sobre un model **sense** cap SizeFitting, totes dues calcularien `next_num=1` i totes dues farien
   `create(numero=1)`. **`unique_together('model','numero')` en rebutjaria una amb `IntegrityError`.**
   Resultat: un 500 lleig capturat a [views.py:2442-2443](backend/fhort/models_app/views.py#L2442-L2443)
   (`return Response({'error': f'Error creant SizeFitting: {e}'}, status=500)`) — **no un duplicat**.
   La invariant de `SizeFitting` aguanta; la de `GradingVersion` no en té cap.

3. **Cronologia i autoria incompatibles.** Els duplicats reals de staging estan separats per **33 i
   41 dies** i porten `codi='IMP-…'` (§Q1.3): els va crear el wizard d'import, deliberadament. Cap
   cursa de mil·lisegons hi participa.

**El que sí que comparteixen** és el context: `generar-grading` és l'endpoint on conviuen L1
(`.first()` sobre `SizeFitting`) i el forat de `GradingVersion`, tots dos **sense transacció ni
bloqueig**. Són dos problemes veïns, no el mateix.

**El símptoma de l'Agus (§Q4, §Q7.1) tampoc hi té res a veure**: el camí del `SizeCheck` no toca ni
`GradingVersion` ni `generar-grading` en cap punt (`resolve_size_check` va deixar de propagar el
21/07, D4 — [services_size_check.py:257-259](backend/fhort/models_app/services_size_check.py#L257-L259)).

---

## TAULA DE NODES

### Escriptors (creen `SizeFitting`)

| # | Node | Crea/Llegeix | Criteri de `numero` | Guard | Risc |
|---|---|---|---|---|---|
| N1 | [signals.py:131](backend/fhort/models_app/signals.py#L131) `sync_size_fitting` | **CREA** (efecte lateral de `post_save`) | literal `1` | `exists()` [:114](backend/fhort/models_app/signals.py#L114) | 🟡 excepcions engolides [:139-141](backend/fhort/models_app/signals.py#L139-L141) |
| N2 | [extraction_views.py:2750](backend/fhort/models_app/extraction_views.py#L2750) wizard import | **CREA SEMPRE** | primer lliure [:2622-2628](backend/fhort/models_app/extraction_views.py#L2622-L2628) | **cap (deliberat)** | 🔴 **autor dels 2 duplicats**; neix `Tancat` sense `sf_pare` |
| N3 | [pom/services.py:495](backend/fhort/pom/services.py#L495) `get_or_create_size_fitting` | CREA si cap | `1` + bump per `codi` | `first()` [:473](backend/fhort/pom/services.py#L473) | 🟡 `numero` pot saltar l'1 |
| N4 | [views.py:2435](backend/fhort/models_app/views.py#L2435) `generate_grading_view` | CREA si cap | `1` + bump per `codi` | `first()` [:2426](backend/fhort/models_app/views.py#L2426) | 🟡 sense `atomic` (§Q8) |
| N5 | [bulk_import_service.py:540](backend/fhort/models_app/bulk_import_service.py#L540) | `bulk_create` | literal `1` | cap (**innecessari**) | 🟢 |
| N6 | [clone_model_for_qa.py:108](backend/fhort/models_app/management/commands/clone_model_for_qa.py#L108) | CREA | literal `1` | `first()` [:106](backend/fhort/models_app/management/commands/clone_model_for_qa.py#L106) | 🟢 no és producció |

### Lectors (resolen «el SizeFitting d'aquest model»)

| # | Node | Criteri de tria | Risc |
|---|---|---|---|
| L1 | [views.py:2426](backend/fhort/models_app/views.py#L2426) | `.first()` → `Meta.ordering` → **`numero` ASC** | 🟡 el més antic |
| L2 | [pom/services.py:473](backend/fhort/pom/services.py#L473) | `.order_by('numero').first()` | 🟡 el més antic |
| L3 | [fitting/services.py:544-551](backend/fhort/fitting/services.py#L544-L551) | **GradingVersion activa** primer, si no `numero` ASC | 🟡 **criteri divergent** (12 crides) |
| L4 | [wizard_views.py:177](backend/fhort/pom/wizard_views.py#L177) | `filter(numero=1)` literal | 🟡 |
| L5 | [wizard_views.py:282](backend/fhort/pom/wizard_views.py#L282) | `filter(numero=1).first()` literal | 🟡 |
| L6 | [views.py:1760](backend/fhort/models_app/views.py#L1760) | **`estat='Tancat'` a QUALSEVOL germà** | 🟡 **fals `tancat=true` a 163/174**, latent |
| L7 | [fitting/views.py:69](backend/fhort/fitting/views.py#L69) `SizeFittingViewSet` | `ordering=['model','numero']`, negociable pel client | 🟢 |
| L8 | [pom/s6_views.py:146](backend/fhort/pom/s6_views.py#L146) · [pom/grading_views.py:98](backend/fhort/pom/grading_views.py#L98) · [pom/services.py:184](backend/fhort/pom/services.py#L184), [:519](backend/fhort/pom/services.py#L519), [:947](backend/fhort/pom/services.py#L947) | `.get(pk=…)` — l'id ve de fora | 🟢 |

### Nodes del `SizeCheck` — **on viu el símptoma de debò**

| # | Node | Crea/Llegeix | Criteri | Risc |
|---|---|---|---|---|
| **S1** | [services_size_check.py:103-106](backend/fhort/models_app/services_size_check.py#L103-L106) `open_size_check` | LLEGEIX | `estat='Pendent'` + `-created_at` | 🔴 **un check resolt és invisible** |
| **S2** | [services_size_check.py:116](backend/fhort/models_app/services_size_check.py#L116) | **CREA** | quan S1 no troba res | 🔴 **el nou naixement amb Real buida** |
| **S3** | [services_size_check.py:64-71](backend/fhort/models_app/services_size_check.py#L64-L71) `_materialize_lines` | CREA línies | `valor_teoric` = snapshot d'ARA; **mai refresca les existents** ([:26-29](backend/fhort/models_app/services_size_check.py#L26-L29)) | 🔴 **teòric estancat 41 dies** (model 182) |
| **S4** | [services_size_check.py:320-323](backend/fhort/models_app/services_size_check.py#L320-L323) `resolve_size_check` | MUTA | `estat` → `Acceptat`/`Rebutjat`/`Descartat`, **mai `Pendent`** | 🔴 **treu el check del radar de S1** |
| **S5** | [CheckMeasureEditor.jsx:195](frontend/src/components/model/CheckMeasureEditor.jsx#L195) (treball) | LLEGEIX **escrivint** | `open()` → S1/S2 | 🔴 obrir la pantalla **crea una fila** |
| **S6** | [CheckMeasureEditor.jsx:193-194](frontend/src/components/model/CheckMeasureEditor.jsx#L193-L194) (consulta) | LLEGEIX | `list(ordering='-created_at', page_size=1)` — **qualsevol estat** | 🔴 **criteri divergent de S5** |
| **S7** | [CheckMeasureEditor.jsx:238](frontend/src/components/model/CheckMeasureEditor.jsx#L238) | RENDER | `valor_real ?? valor_teoric` | 🟡 el fallback **fa indistingible** «buit» de «mesurat» |

---

## LÍMITS DECLARATS

1. **Cap test executat, cap escriptura, cap build.** Tota conclusió surt de lectura de codi al HEAD
   `55e13cab`, de `SELECT` a `ftt_staging@5433`, i de `git show`/`git log` sobre commits existents.
   Res s'ha reproduït executant-ho.
2. **La data del 28/07 no queda explicada.** El commit que arma la col·lisió és `a2d4222d` del
   **20/07**. No he investigat què va passar el 28/07 (§Q5.2). El **mecanisme** dels 53 sí que queda
   provat; la **data de primera observació**, no.
3. **No he comptat els 53.** Prenc la xifra i el repartiment 29/24 del brief. He traçat el `setUp`
   de 2 de les 10 classes citades (`PropagarActionTest` i `_SegellBase`, del qual hereten
   `EstalitudTest` i `R7UnaSolaActivaTest` via `_BancSegellat`). Les altres 6 classes
   (`AvisAlMotorTest`, `ElsSisCaminsTest`, `ApproveActionTest`, `GateDeLesReglesResidentsTest`,
   `IntegritatDelMotorTest`, `Fork4VersioVigentTest`) **no s'han traçat una a una**;
   `IntegritatDelMotorTest` i `Fork4VersioVigentTest` deriven de `_SegellBase`/`_G6Base` per herència
   verificada, la resta són **inferència per patró, no verificació**.
4. **§Q4-E és arqueologia de codi, no reproducció.** La cadena `onFeedback` → re-render → `load()` →
   `open()` està llegida al commit `ad10e4ad` i encaixa amb els 117–145 ms observats, però **no s'ha
   executat** per confirmar-la. Que avui la dep ja no hi és, sí que està verificat
   ([CheckMeasureEditor.jsx:327](frontend/src/components/model/CheckMeasureEditor.jsx#L327)).
5. **No he fet QA de navegador.** Els «qui veuria què» de §Q7.1 estan derivats de llegir el codi del
   lector + les files de la BD. No s'ha obert cap pantalla.
6. **`los` no aporta res al cas.** 0 BaseMeasurement, 0 SizeCheck, 51 SizeFitting a 1 per model. És
   catàleg federat sense feina de mesures. Tot el diagnòstic de dades és de `fhort`.
7. **No he auditat PROD.** Tot el que es diu de dades és de staging.
8. **`ATOMIC_REQUESTS`:** no l'he re-verificat; prenc la premissa del brief tal com ve (§Q8). El que
   **sí** he verificat directament és l'absència de `select_for_update` i d'`atomic` al voltant de
   [pom/services.py:875-880](backend/fhort/pom/services.py#L875-L880).

---

## RESPOSTA DIRECTA, SENSE HEDGING

### (a) El duplicat neix a PRODUCCIÓ o als TESTS?

**Tots dos, i són DOS duplicats diferents. Cal no confondre'ls.**

**El duplicat de `SizeFitting` dels 53 tests neix als TESTS.** El signal de producció
([signals.py:131](backend/fhort/models_app/signals.py#L131)) crea el primer, i el fa correctament
—té guard `exists()` a [:114](backend/fhort/models_app/signals.py#L114)—. **El segon el crea el
fixture** ([fitting/tests.py:60](backend/fhort/fitting/tests.py#L60),
[pom/test_g6_segell.py:79](backend/fhort/pom/test_g6_segell.py#L79)), que declara un SizeFitting que
el sistema ja li regala des del commit `a2d4222d` (20/07). **Higiene de verificació. Per aquesta via,
la producció està bé:** 42/44 models a `fhort` i 51/51 a `los` tenen exactament un SizeFitting.

**El duplicat que produeix el símptoma de l'Agus neix a PRODUCCIÓ, i no és un `SizeFitting`: és un
`SizeCheck`.** El crea [services_size_check.py:116](backend/fhort/models_app/services_size_check.py#L116)
cada cop que s'obre la tab Mesures en mode treball i no hi ha cap check `estat='Pendent'` — cosa que
passa **sempre just després de resoldre'n un**, perquè
[resolve_size_check](backend/fhort/models_app/services_size_check.py#L320) el treu de `Pendent` i
[open_size_check](backend/fhort/models_app/services_size_check.py#L104) només mira els `Pendent`.
**Codi de producció, camí normal, sense cap test pel mig.** Les dades ho signen: 12 checks per a 7
models, i quatre naixements a **117–145 ms** de la resolució del seu germà.

**Els 53 no són el símptoma que ens avisava des del 28/07.** Són un fenomen veí que ha ocupat el nom.
El símptoma real no ha fet petar cap test perquè **no hi ha cap test que exerceixi la seqüència
resoldre-i-tornar-a-obrir**: `test_size_check_completa_linies.py` prova `open` repetit i `open` sobre
`Pendent`, però **no `resolve` seguit d'`open`**.

### (b) Hi ha avui, a dades reals, algun model on un lector mostra una mesura que no és la vigent?

**SÍ. Dos, i els dos són a `fhort` ara mateix.**

**MODEL 185, POM 273 — dos lectors, dos números.**
Els 3 checks estan `Acceptat`; cap `Pendent`.
- **Mesures · consulta** ([ModelSheet.jsx:661](frontend/src/pages/ModelSheet.jsx#L661) → `list('-created_at')`)
  → check **22** → «Real (proto)» = **`61.1`**.
- **Mesures · treball** ([ModelSheet.jsx:652](frontend/src/pages/ModelSheet.jsx#L652) → `open()`)
  → cap `Pendent` → **crea un check nou** → «Real (proto)» = **`60.5`** (el `valor_teoric`, pel `??`).

La base vigent és **60.5** (`FITTED`, 17/07). **La pantalla de consulta ensenya `61.1`: un valor que
no és el vigent.** I la de treball, per ensenyar el correcte, **escriu una fila nova a la BD cada cop
que s'obre**.

**MODEL 182, POM 379 — un teòric congelat des de fa 41 dies.**
El check **21** és `Pendent` des del **23/06 18:00** i encara ho és. El seu `valor_teoric` és
**41.7**. La base vigent és **42.6** (`origen='CHECKED'`, escrita el **24/06 18:35**, l'endemà).
`_materialize_lines` **no refresca mai el teòric d'una línia existent**
([services_size_check.py:26-29](backend/fhort/models_app/services_size_check.py#L26-L29)). **La tab
Mesures d'aquest model ensenya 41.7 des de fa 41 dies. El valor vigent és 42.6.**

*(Cas latent, no viu: models 163 i 174 — `measurements_table_view`
([views.py:1760](backend/fhort/models_app/views.py#L1760)) retorna `tancat=true` perquè el germà de
l'import està `Tancat`, tot i que el SizeFitting de treball —el nº1, el que té la GradingVersion
activa— està obert. El backend menteix, però cap consumidor del frontend llegeix aquest camp.)*

---

*Diagnosi Patró A · read-only · HEAD `55e13cab` · 2026-08-03. Document al working tree, **NO
commitejat**. Cap fix proposat, per encàrrec.*
