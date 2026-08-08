# DIAGNOSI · LA COLUMNA DE MESURA — quan neix, quina és vigent, i què passa amb les descartades

> **Patró A · READ-ONLY.** Cap escriptura a BD, cap migració, cap fitxer del repo modificat, cap
> management command, cap test executat, cap build, cap commit, cap push.
> Única escriptura: aquest document al working tree, **MAI commitejat**.
>
> **Entorn:** `/var/www/ftt-staging` · branca `dev` · **HEAD `55e13cab3650eb9f076b578fa4047e680e609e8a`**
> (`E5 · desactivar_pom deixa de triar la germana a l'atzar`, Sun Aug 2 23:20:51 2026 +0000) —
> el mateix HEAD que la diagnosi d'entrada. **BD:** `ftt_staging`@5433 · `fhort` · `los`.
> **Data:** 2026-08-03.
>
> **Entrada:** `docs/diagnosis/DIAGNOSI_SIZEFITTING_DUPLICAT.md` (d'avui). **No es repeteix.**
> Se'n dona per tancat: el duplicat de `SizeFitting` és de 2 models sobre 44 i és obra del wizard
> d'import; l'entitat que produïa el símptoma és `SizeCheck`; el naixement el fa
> `open_size_check` quan no troba cap `Pendent`; els 53 tests són una col·lisió de fixtures.
> Aquest document **parteix** d'allà i mira l'altra meitat: **la columna**.
>
> **CAP PROPOSTA DE FIX.** Fets amb `fitxer:línia` o SQL amb resultat. «NO EXISTEIX» = confirmat
> absent (grep exhaustiu buit o `information_schema` amb 0 files).

---

## RESUM EXECUTIU — les conclusions que decideixen

**1. La regla decidida ja és, en part, la que el sistema aplica — però només a UN dels dos nivells,
i per una via que ningú va dissenyar per fer-ho.** Les columnes de la taula de Mesures **no
neixen d'obrir cap pantalla**: les construeix `base_stages_view`
([views.py:3080-3092](backend/fhort/models_app/views.py#L3080-L3092)) agrupant
`MeasurementChangeLog` per **`(context, segon)`**. I el signal F1 ja té el guard de materialitat:
[signals.py:310-311](backend/fhort/models_app/signals.py#L310-L311) — `if not created and
old_value == instance.base_value_cm: return`. **Un desat que no canvia cap valor ja no pinta
columna avui.** La premissa del brief («si s'escriu sempre, tornaríem al problema per l'altra
porta») **és falsa per a la columna**: el filtre no és al camí de desar, és al signal.

**2. El vocabulari d'origen ja distingeix els tres disparadors, i el registre també.** Entrada de
POMs → `origen='MANUAL'` → `context='manual'`; consolidació de fitting → `'FITTED'` → `'fitting'`;
resolució de check → `'CHECKED'` → `'checked'`. El mapa és declarat i complet
([signals.py:200-226](backend/fhort/models_app/signals.py#L200-L226), tancat per C3/C el 02/08).
**Sí que es pot distingir una escriptura d'Entrada de POMs d'una de check.** El vocabulari
**no** és insuficient: en sobra, fins i tot (11 valors d'`origen`, 11 contextos).

**3. Però la unitat de columna és el SEGON, no l'acte.** Això produeix el símptoma contrari al que
buscàvem: **proliferació**. El model 182 té **12 columnes** d'estadi, de les quals **8 són
`checked` i 7 porten una sola xifra**, escrites entre les 18:08:49 i les 18:35:23 del 24/06 — 7
columnes per a 27 minuts d'una mateixa feina. No és una columna que neix en obrir: és una columna
per cada `resolve` del bucle de checks que la diagnosi d'entrada ja va descriure.

**4. El descartat NO TÉ ON VIURE. Aquesta és la conclusió que canvia l'abast del treball.**
- A nivell de **check**: el vocabulari existeix (`SizeCheckLine.decisio` ∈
  {`tolerancia_acceptada`, `valor_descartat`, NULL}) i el valor **es conserva** a la línia. Però
  **`valor_descartat` té ZERO files a tot el corpus** — mai s'ha exercit —, i sobretot: **una sola
  línia descartada converteix el check sencer en `Rebutjat` i llavors NO S'ESCRIU NI UNA de les
  acceptades** ([services_size_check.py:200-211](backend/fhort/models_app/services_size_check.py#L200-L211)).
  És tot-o-res per check, no per línia.
- A nivell de **fitting**: **NO EXISTEIX.** `PieceFittingLine` té **9 columnes a Postgres i cap
  s'anomena `decisio`** (`information_schema`, resultat literal a §R3.2). No hi ha manera de dir
  «aquesta presa és dolenta».
- I sobretot, a **tots dos nivells**: **un valor descartat no arriba mai a `BaseMeasurement` → no
  arriba mai a `MeasurementChangeLog` → no arriba mai a ser columna.** El model de columnes
  d'avui **no pot representar una columna descartada**, perquè la columna es deriva del registre
  d'escriptures a la base, i una presa descartada no és cap escriptura.

**5. «Vigent = l'última NO DESCARTADA» no és un canvi de criteri: és un concepte que avui no
existeix.** Cap lector tria columna. `BaseMeasurement.base_value_cm` **és** el vigent —una fila,
sobreescrita in situ— i les columnes són una **reconstrucció read-only per carry-forward** feta a
posteriori ([views.py:3094-3099](backend/fhort/models_app/views.py#L3094-L3099)). El propi
docstring ho diu: *«l'últim estadi coincideix amb la base vigent»*
([views.py:3051-3052](backend/fhort/models_app/views.py#L3051-L3052)). **No hi ha res a saltar,
perquè no hi ha res a triar.**

**6. Sobre la GRAELLA, la llei de columnes no divergeix: no hi és.** El sample fitting materialitza
línies per a **totes** les talles ([services.py:337-348](backend/fhort/fitting/services.py#L337-L348)
— 42 línies × 3 talles al model 182, dades reals), però:
- la superfície de Mesures en mode fitting **només pinta la talla base**
  ([fittingGridAdapter.jsx:5-8](frontend/src/components/model/fittingGridAdapter.jsx#L5-L8),
  `buildFittingGroups` retorna **un sol group**);
- la consolidació **només toca la talla base**
  ([services.py:379-380](backend/fhort/fitting/services.py#L379-L380): `if line.size_label.strip()
  != base_size: continue  # PEÇA 4`);
- l'escriptura de les cel·les no-base està **bloquejada amb un 400**
  ([views.py:583-586](backend/fhort/fitting/views.py#L583-L586), `fitting_line_is_non_base`).

**Les línies no-base d'un sample fitting existeixen a la BD, no es poden editar, no es pinten
enlloc i no es consoliden en lloc.** I les «columnes» que sí que pinta el fitting **no són preses:
són GradingVersions** (`Base`, `Fit 1`, `Fit 2`… — [fittingGridAdapter.jsx:14-16](frontend/src/components/model/fittingGridAdapter.jsx#L14-L16)),
és a dir **teoria, no mesura**.

**7. El «cas dolent» d'ahir no és un: són DOS.** Igual que `sizeChecks.open()`, la superfície de
fitting **escriu en obrir**: `resolvePieceFitting`
([measureSources.jsx:35-54](frontend/src/components/model/measureSources.jsx#L35-L54)) crea la
`PieceFitting` i les seves 42 línies si no existeix — comentat explícitament com
*«Materialització EN OBRIR (decisió 6)»*. Dues superfícies, el mateix patró.

**8. Els 53 tenen UNA causa i viuen a TRES línies.** Verificades les 6 classes que ahir van quedar
per patró: totes cauen al mateix xoc. I els recomptes quadren exactament — 16+13 = **29 a
`fhort.fitting`**, 17+7 = **24 a `fhort.pom`**, total **53**. La causa viu a **3 peces de fixture**
([tests.py:60](backend/fhort/fitting/tests.py#L60), [test_g6_segell.py:79](backend/fhort/pom/test_g6_segell.py#L79),
[test_g6_grading_gates.py:60](backend/fhort/pom/test_g6_grading_gates.py#L60)), no a 53 llocs.
**Es netegen d'un cop.** I de passada es tanca el límit declarat d'ahir: **la data del 28/07 està
documentada dins el repo**, en 5 fitxers.

---

## R1 · QUI ESCRIU BASE, I AMB QUIN ORIGEN

### R1.1 · Cens dels camins de producció que escriuen `BaseMeasurement`

Cens obtingut de `grep -rn "BaseMeasurement.objects\.\|\.base_value_cm\s*="` sobre `fhort/`,
exclosos tests i migracions. Agrupat pel criteri del brief.

#### (a) ENTRADA DE POMs — el disparador nou hi aplica

| # | Node | `origen` | Rastre al registre | Notes |
|---|---|---|---|---|
| **A1** | [views.py:1955-1963](backend/fhort/models_app/views.py#L1955-L1963) `gravar_pom_view` | **`'MANUAL'`** | ✅ `_motiu='gravar_pom'` ([:1962](backend/fhort/models_app/views.py#L1962)), `_changed_by=request.user` | **LA porta principal.** `bm.save()` incondicional |
| **A2** | [views.py:1810](backend/fhort/models_app/views.py#L1810) `set_measurements_view` | *(no l'estampa; hereta)* | ✅ via signal | `update_or_create` |
| **A3** | [wizard_views.py:242](backend/fhort/pom/wizard_views.py#L242) | *(no l'estampa)* | ✅ via signal | Wizard de POMs (pas 2) |
| **A4** | [wizard_views.py:212](backend/fhort/pom/wizard_views.py#L212) | *(posa `base_value_cm=None`)* | ❌ el signal retorna a [:306-307](backend/fhort/models_app/signals.py#L306-L307) | Buidatge |
| **A5** | [views.py:2072](backend/fhort/models_app/views.py#L2072) reordenació | — | ❌ `.update(ordre=…)`: no passa per `save()` | No és canvi de valor |

#### (b) CONSOLIDACIÓ DE FITTING — el disparador nou hi aplica

| # | Node | `origen` | Rastre al registre |
|---|---|---|---|
| **B1** | [fitting/services.py:383-394](backend/fhort/fitting/services.py#L383-L394) `consolidate_base_from_fitting` | **`'FITTED'`** ([:392](backend/fhort/fitting/services.py#L392)) | ✅ **el més ric de tots**: `_fitting_ref=sf` (FK a `SizeFitting`, [:395](backend/fhort/fitting/services.py#L395)) + `_motiu=f'Fitting · sessió {pf.session_id} · peça {pf.pk}'` ([:396](backend/fhort/fitting/services.py#L396)) |

**És l'ÚNIC escriptor que deixa un punter estructural** (`MeasurementChangeLog.fitting_ref`,
[models.py:861-864](backend/fhort/models_app/models.py#L861-L864)). Tots els altres deixen text
lliure al `motiu`.

#### (c) RESOLUCIÓ DE CHECK — el disparador nou **NO** hi ha d'aplicar (segons la regla decidida)

| # | Node | `origen` | Rastre al registre |
|---|---|---|---|
| **C1** | [services_size_check.py:230-245](backend/fhort/models_app/services_size_check.py#L230-L245) `resolve_size_check` | **`'CHECKED'`** ([:242](backend/fhort/models_app/services_size_check.py#L242)) | ⚠️ `_motiu=f'Size check · check {sc.pk}'` amb un **deute anotat al propi codi**: `# deute (b): sense size_check_ref` ([:244](backend/fhort/models_app/services_size_check.py#L244)) — **no hi ha FK cap al `SizeCheck`, a diferència del fitting** |

#### (d) ALTRES

| # | Node | `origen` | Rastre |
|---|---|---|---|
| D1 | [extraction_views.py:2575](backend/fhort/models_app/extraction_views.py#L2575) import guiat | `'IMPORTED'` | ✅ `context='import'` |
| D2 | [bulk_import_service](backend/fhort/models_app/bulk_import_service.py) / [views.py:1195-1218](backend/fhort/models_app/views.py#L1195-L1218) materialització item | `'TEMPLATE'` / `'ITEM_STANDARD'` | parcial (TEMPLATE sense valor no loga) |
| D3 | [views.py:1445-1463](backend/fhort/models_app/views.py#L1445-L1463) còpia model→model | `'COPIED'` | ✅ `context='copied'` |
| D4 | [federation_service.py:769-791](backend/fhort/tenants/federation_service.py#L769-L791) | `'FEDERAT'` | ✅ `context='federat'` |
| D5 | [services_derivacio.py:144](backend/fhort/models_app/services_derivacio.py#L144) derivació de germanes (C3) | `'DERIVAT'` | ✅ `context='derivat'` |
| D6 | [views.py:2345-2358](backend/fhort/models_app/views.py#L2345-L2358) accions IA | variable | ✅ |
| D7 | [views.py:2901-2905](backend/fhort/models_app/views.py#L2901-L2905), [tech_sheet_views.py:367](backend/fhort/models_app/tech_sheet_views.py#L367) | variable | ✅ |

### R1.2 · **LA PREGUNTA QUE DECIDEIX: es pot distingir Entrada-de-POMs d'una resolució de check?**

**SÍ. Dues vegades, i en dos llocs independents.**

**(i) A la fila viva.** `BaseMeasurement.origen`
([models.py:591-627](backend/fhort/models_app/models.py#L591-L627)) — 11 valors. `MANUAL`
(«Introduït manualment») ≠ `CHECKED` («Validat en size check») ≠ `FITTED` («Modificat en
fitting»). Estampats literalment a [views.py:1958](backend/fhort/models_app/views.py#L1958),
[services_size_check.py:242](backend/fhort/models_app/services_size_check.py#L242),
[fitting/services.py:392](backend/fhort/fitting/services.py#L392).

**(ii) Al registre append-only.** `_ORIGEN_TO_CONTEXT`
([signals.py:200-226](backend/fhort/models_app/signals.py#L200-L226)) tradueix cada `origen` al
`context` de la fila de log. **El mapa és complet des del 02/08** (C3/C va tancar els quatre que
queien al fallback silenciós — `TEMPLATE`, `CHECKED`, `ITEM_STANDARD`, `FEDERAT`,
[signals.py:216-225](backend/fhort/models_app/signals.py#L216-L225)).

I es veu a les dades:

```sql
select context, count(*), count(distinct model_id) models
from fhort.models_app_measurementchangelog group by 1 order by 2 desc;
```

| `context` | files | models |
|---|---|---|
| `import` | 133 | 7 |
| **`manual`** | **34** | 4 |
| **`checked`** | **17** | 3 |
| **`fitting`** | **7** | 3 |
| `item_standard` | 2 | 1 |

**Els tres disparadors de la regla decidida ja arriben al registre separats i comptables.**

### R1.3 · El que SÍ que falta (no el vocabulari)

**El vocabulari no és insuficient. El que falta és el PUNTER.** El fitting deixa
`MeasurementChangeLog.fitting_ref` → `SizeFitting`
([models.py:861-864](backend/fhort/models_app/models.py#L861-L864)); el check **no deixa cap FK
cap al `SizeCheck`** — el propi codi ho anota com a *«deute (b): sense `size_check_ref`»*
([services_size_check.py:244](backend/fhort/models_app/services_size_check.py#L244)). Confirmat
per `information_schema`: **`models_app_measurementchangelog` no té cap columna `size_check`**
(les seves FK són `model_id`, `pom_id`, `base_measurement_id`, `fitting_ref_id`, `created_by_id`).

Conseqüència per a la regla decidida: es pot saber **de quin TIPUS** d'acte ve una columna
(`context`), però només al fitting es pot saber **de QUIN acte concret**.

> ⚠️ **Nota sobre C3 i les derivades** (el brief demana mirar-ho): **`DERIVAT`/`derivat` és
> vocabulari NOU i CORRECTE, i ja funciona.** El comentari del model
> ([models.py:614-627](backend/fhort/models_app/models.py#L614-L627)) argumenta per què cap valor
> anterior servia. **Però no és el que fa falta aquí**: una derivació no és una presa, i la regla
> decidida parla de preses. **A les dades, `derivat` té 0 files** — les comportes C4/C4-ins encara
> el fan no-op. **El vocabulari serveix; la peça que falta és la del descartat (§R3), que no hi
> és.**

---

## R2 · QUÈ ÉS UN CANVI «MATERIAL»

### R2.1 · Es pot saber si el desat ha canviat res? **SÍ — però no on es buscava**

**Al camí de desar: NO hi ha comparació.** [views.py:1949-1963](backend/fhort/models_app/views.py#L1949-L1963):

```python
bm.base_value_cm = value
bm.notes = m.get('notes', '') or ''
bm.nom_fitxa = m.get('nom_fitxa', '') or ''
bm.origen = 'MANUAL'
bm.is_active = True
bm.tolerancia_minus = pom.tolerancia_default_minus
bm.tolerancia_plus = pom.tolerancia_default_plus
bm._changed_by = request.user
bm._motiu = 'gravar_pom'
bm.save()                    # ← INCONDICIONAL. Cap `if value != bm.base_value_cm`.
```

**Al signal: SÍ, i és exactament la comparació que la regla necessita.** El parell
`pre_save`/`post_save`:

- [signals.py:235-250](backend/fhort/models_app/signals.py#L235-L250) `capture_old_measurement_value`
  desa el valor persistit a `instance._old_value` amb un `SELECT` addicional.
- [signals.py:306-311](backend/fhort/models_app/signals.py#L306-L311):

```python
if instance.base_value_cm is None:
    return                                        # materialització buida → cap log
old_value = getattr(instance, '_old_value', None)
if not created and old_value == instance.base_value_cm:
    return  # value unchanged → nothing to log     # ← EL GUARD DE MATERIALITAT
```

**Per tant la premissa de risc del brief no aplica a la columna.** Un desat d'Entrada de POMs que
no canviï cap xifra escriu 5 camps a `BaseMeasurement` (`notes`, `nom_fitxa`, `origen`,
toleràncies) però **no genera cap fila de log**, i com que `base_stages_view` es construeix
**només** del log ([views.py:3080-3083](backend/fhort/models_app/views.py#L3080-L3083)),
**no neix cap columna**. Ja avui.

⚠️ **La contrapartida, i és la que sorprèn:** el guard és **per FILA**, no per acte. Un desat que
canviï 1 POM de 20 genera **1 fila de log**, i aquesta fila **sí que pinta una columna sencera** —
amb 19 cel·les omplertes per carry-forward des de la columna anterior
([views.py:3094-3099](backend/fhort/models_app/views.py#L3094-L3099)). Visualment és una columna
nova amb 20 valors; materialment n'hi ha canviat un.

### R2.2 · La unitat de columna: el SEGON

[views.py:3086-3092](backend/fhort/models_app/views.py#L3086-L3092):

```python
bucket = c.created_at.replace(microsecond=0).isoformat()
key = f'{c.context}@{bucket}'
```

**Un event = `(context, segon)`.** No hi ha cap identificador d'acte: ni `request_id`, ni
`transaction_id`, ni `size_check_ref`. **La unitat de columna la fa el rellotge.**

Dues conseqüències, totes dues comprovades a les dades:

**(a) PROLIFERACIÓ — real, i és el símptoma dominant avui.**

```sql
select model_id, context, date_trunc('second',created_at) seg, count(*) n_files
from fhort.models_app_measurementchangelog
where base_measurement_id is not null and model_id in (182,162)
group by 1,2,3 order by 1,3;
```

| model | context | segon | files |
|---|---|---|---|
| 162 | import | 2026-06-08 08:05:45 | 14 |
| 162 | fitting | 2026-06-08 08:12:33 | 1 |
| 162 | checked | 2026-06-16 15:12:35 | 1 |
| 162 | import | 2026-06-16 15:18:32 | 1 |
| 162 | checked | 2026-06-16 15:55:34 | 1 |
| 162 | import | 2026-06-16 16:20:51 | 1 |
| 162 | checked | 2026-06-16 16:36:55 | 1 |
| 162 | import | 2026-06-16 16:58:16 | 1 |
| 162 | checked | 2026-06-16 17:00:22 | 1 |
| 162 | import | 2026-06-16 19:02:24 | 1 |
| 182 | import | 2026-06-16 19:02:35 | **14** |
| 182 | checked | 2026-06-16 19:11:27 | 2 |
| 182 | fitting | 2026-06-17 11:19:47 | 1 |
| 182 | fitting | 2026-06-18 06:37:03 | 1 |
| 182 | checked | 2026-06-23 17:54:45 | 1 |
| **182** | **checked** | **2026-06-24 18:08:49** | **1** |
| **182** | **checked** | **2026-06-24 18:08:55** | **1** |
| **182** | **checked** | **2026-06-24 18:08:58** | **1** |
| **182** | **checked** | **2026-06-24 18:35:03** | **1** |
| **182** | **checked** | **2026-06-24 18:35:16** | **1** |
| **182** | **checked** | **2026-06-24 18:35:20** | **1** |
| **182** | **checked** | **2026-06-24 18:35:23** | **1** |

**Set columnes `checked` en 27 minuts, cadascuna amb UNA xifra.** El model 182 acumula **12
columnes** ([§R2.3](#r23--recompte-de-columnes-per-model)). Aquest **no** és el símptoma de
«neix en obrir la pantalla»: és **una columna per cada `resolve`** del bucle de checks que la
diagnosi d'entrada va documentar. La regla decidida («el check TANCA la seva columna, no n'obre
una altra») **atacaria exactament això**.

**(b) FRAGMENTACIÓ — risc estructural, ZERO instàncies observades.** Si un sol acte tardés a
travessar una frontera de segon, les seves files caurien en dos buckets → **dues columnes per un
desat**. A les dades no ha passat mai: el bloc més gran és de 14 files en **76 ms**
(162 @ 08:05:45.447→.523) i el segon de 14 files en **52 ms** (182 @ 19:02:35.112→.164). El risc
és real i no exercit.

### R2.3 · Recompte de columnes per model

```sql
select model_id, count(distinct context||'@'||date_trunc('second',created_at)) n_columnes, count(*) n_logs
from fhort.models_app_measurementchangelog where base_measurement_id is not null
group by 1 order by 2 desc limit 12;
```

| model | columnes | files de log |
|---|---|---|
| **182** | **12** | 26 |
| **162** | **10** | 23 |
| 185 | 5 | 9 |
| 1302 | 2 | 6 |
| 268 | 2 | 20 |
| 186 · 188 · 163 · 269 · 174 | 1 | 20 · 10 · 25 · 25 · 21 |

Els models que han passat per un import i prou tenen **1 columna amb 20-25 valors** (sa). Els que
han passat pel bucle de checks en tenen **10-12, la majoria amb una xifra** (patològic).

### R2.4 · **Afegir un POM i canviar un valor: MATEIX camí, i NO són separables avui**

Tots dos passen per **`gravar_pom_view`** ([views.py:1851](backend/fhort/models_app/views.py#L1851)),
i dins seu pel **mateix bucle**. La distinció existeix... **però només com a comptador, no com a
senyal**:

[views.py:1941-1948](backend/fhort/models_app/views.py#L1941-L1948):
```python
bm = BaseMeasurement.objects.filter(model=model, pom=pom, capa=…, instancia='').first()
if bm is None:
    bm = BaseMeasurement(model=model, pom=pom, …, created_by=request.user)
    created += 1        # ← es COMPTA…
else:
    updated += 1        # ← …i es compta
```

`created` i `updated` es retornen a la resposta HTTP, però **cap dels dos arriba al signal ni al
log**. La fila de log d'un POM nou i la d'un valor canviat són **indistingibles**: totes dues
tenen `context='manual'` i `base_measurement` no nul. L'única diferència és que la nova té
`valor_anterior IS NULL`, cosa que el signal sí que registra (`created=True` →
[signals.py:310](backend/fhort/models_app/signals.py#L310) no filtra) — **però `base_stages_view`
no la mira**: el seu bucle només llegeix `valor_nou`
([views.py:3084-3085](backend/fhort/models_app/views.py#L3084-L3085)).

**Conseqüència directa per a la regla «s'afegeix LÍNIA a la columna vigent quan només s'afegeix un
POM»:** el senyal per distingir-ho (`valor_anterior IS NULL`) **ja existeix al registre**; el que
no existeix és cap lector que el faci servir. Avui, afegir un POM crea una **columna** nova, no una
línia. **La regla i el comportament divergeixen, i el senyal per tancar la divergència ja hi és.**

---

## R3 · EL DESCARTAT — ¿TÉ ON VIURE?

### R3.1 · Nivell CHECK — vocabulari sí, semàntica a mitges, ús zero

**El camp existeix.** [models.py:1263-1270](backend/fhort/models_app/models.py#L1263-L1270):

```python
DECISIO_CHOICES = [
    ('tolerancia_acceptada', 'Tolerància acceptada'),
    ('valor_descartat', 'Valor descartat'),
]
decisio = models.CharField(max_length=24, choices=DECISIO_CHOICES, null=True, blank=True)
nota = models.CharField(max_length=200, blank=True, default='')
```

**Tres estats**: `tolerancia_acceptada` · `valor_descartat` · **NULL** («sense decidir encara»,
[:1266](backend/fhort/models_app/models.py#L1266)).

**El valor ES CONSERVA.** `valor_real` és un camp propi de la línia
([:1256](backend/fhort/models_app/models.py#L1256)) i `resolve_size_check` **no el toca mai** —
només llegeix. Una línia `valor_descartat` conserva la seva xifra a la BD indefinidament.

**Però la resolució és TOT-O-RES per check, no per línia.**
[services_size_check.py:196-211](backend/fhort/models_app/services_size_check.py#L196-L211):

```python
if estat == 'Acceptat':
    final_estat = 'Rebutjat' if descartades > 0 else 'Acceptat'
...
propagat = (final_estat == 'Acceptat')
...
if propagat:
    SizeCheckLine.objects.filter(size_check=sc, decisio__isnull=True).update(
        decisio='tolerancia_acceptada')
    lines = list(SizeCheckLine.objects.filter(size_check=sc, decisio='tolerancia_acceptada')…)
```

**Una sola línia descartada → `final_estat='Rebutjat'` → `propagat=False` → NO S'ESCRIU RES.** Ni
les acceptades. El docstring ho declara com a llei: *«alguna línia 'valor_descartat' →
estat='Rebutjat': NO promou, NO CHECKED, NO Done (proto a refer)»*
([:161-162](backend/fhort/models_app/services_size_check.py#L161-L162)).

Això **no** és el que demana la regla decidida. La regla diu: *«el valor es GUARDA i es mostra
marcat, i el real vigent segueix sent l'anterior»* — per línia. Avui és: *el check sencer no
propaga i tot el model es queda com estava*.

### R3.2 · Nivell FITTING — **NO EXISTEIX**

`PieceFittingLine` a Postgres, confirmat per `information_schema` (no per lectura de codi):

```sql
select column_name, data_type from information_schema.columns
where table_schema='fhort' and table_name='fitting_piecefittingline' order by ordinal_position;
```

| # | columna | tipus |
|---|---|---|
| 1 | `id` | bigint |
| 2 | `size_label` | varchar |
| 3 | `valor_teoric` | double precision |
| 4 | `valor_real` | double precision |
| 5 | `nota` | varchar |
| 6 | `piece_fitting_id` | bigint |
| 7 | `pom_id` | bigint |
| 8 | `capa` | varchar |
| 9 | `instancia` | varchar |

**Nou columnes. Cap `decisio`. Cap `acceptat`. Cap `descartat`.** El model Django ho confirma
([fitting/models.py:390-417](backend/fhort/fitting/models.py#L390-L417)) i el seu propi docstring
declara l'abast: *«Only the two current values are stored»*
([:391-395](backend/fhort/fitting/models.py#L391-L395)).

**L'únic que hi ha és `nota`** — text lliure, 200 caràcters, sense semàntica. `PieceFitting.gate`
(∈ `Pendent`/`OK`/`NO_OK`/`EXCEPCIO`, [:302-307](backend/fhort/fitting/models.py#L302-L307)) és
un veredicte **de la peça sencera**, no de la presa.

**I un forat propi, més greu que la falta de camp:** la línia neix amb `valor_real` **ja omplert**
amb el teòric ([services.py:346](backend/fhort/fitting/services.py#L346):
`valor_real=spec.graded_value_cm,  # copy, editable before close`). **Un valor no mesurat i un
valor mesurat-igual-al-teòric són indistingibles.** Es veu a les dades: les 5 peces de staging
tenen **el 100% de línies amb `valor_real`** (42/42, 41/41, 14/14 — §R5.4). Al check, en canvi,
`valor_real` neix `NULL` ([services_size_check.py:70](backend/fhort/models_app/services_size_check.py#L70)).
**Dues entitats germanes amb convencions oposades per al mateix concepte.**

### R3.3 · Es distingeix «descartat» de «rebutjat» de «acceptat dins de tolerància»?

| Concepte | On viu | Granularitat | Existeix? |
|---|---|---|---|
| «acceptat dins de tolerància» | `SizeCheckLine.decisio='tolerancia_acceptada'` | **línia** | ✅ |
| «valor descartat» | `SizeCheckLine.decisio='valor_descartat'` | **línia** | ✅ *(mai usat)* |
| «sense decidir» | `SizeCheckLine.decisio IS NULL` | **línia** | ✅ |
| «el check sencer no val» | `SizeCheck.estat='Rebutjat'` | **check** | ✅ |
| «no s'ha mesurat ara» | `SizeCheck.estat='Descartat'` | **check** | ✅ |
| **al FITTING, qualsevol dels anteriors** | — | — | ❌ **NO EXISTEIX** |

Els tres nivells **es distingeixen al check**. Però `Rebutjat` (check) i `valor_descartat` (línia)
estan **acoblats**: el segon força sempre el primer.

### R3.4 · «Aquesta mesura va arribar malament i el vigent segueix sent l'anterior»

**El sistema només sap substituir.** Tres verificacions:

1. **La base és una fila, no una pila.** `BaseMeasurement` té `unique_together = ('model','pom',
   'capa','instancia')` i `base_value_cm` és un `FloatField` únic. Cada escriptura **trepitja**
   l'anterior. No hi ha versionat de la base.
2. **El motor llegeix la fila, no la història.** `_load_base_measurements`
   ([pom/services.py:815-841](backend/fhort/pom/services.py#L815-L841)) retorna
   `{(pom_id, capa, instancia): bm.base_value_cm}` directament de `BaseMeasurement`. **No consulta
   `MeasurementChangeLog` ni una vegada.**
3. **El descartat no arriba mai a ser columna.** Cadena verificada: valor descartat → no entra a
   `BaseMeasurement` (§R3.1) → el signal F1 no s'executa mai per ell → cap fila a
   `MeasurementChangeLog` → `base_stages_view` no el veu → **cap columna**.

**Conclusió: la frase «el vigent segueix sent l'anterior» és, avui, el comportament per defecte —
però per omissió, no per decisió.** No perquè el sistema sàpiga marcar res: perquè el valor dolent
no s'escriu i, per tant, **desapareix de tota superfície**. El tècnic no pot muntar la taula ni
reclamar al fabricant, perquè la xifra que li han enviat malament **no es pot ensenyar enlloc**:
viu només dins d'un `SizeCheck` resolt, i el lector de consulta només ensenya el **més recent**
([CheckMeasureEditor.jsx:193-194](frontend/src/components/model/CheckMeasureEditor.jsx#L193-L194)).
Un cop neix un check posterior, **la xifra descartada és inabastable des de la UI**.

### R3.5 · Dades reals

```sql
select decisio, count(*) total, count(*) filter (where valor_real is not null) amb_valor,
       count(*) filter (where nota <> '') amb_nota
from fhort.models_app_sizecheckline group by 1 order by 2 desc;
```

| `decisio` | total | amb `valor_real` | amb `nota` |
|---|---|---|---|
| `tolerancia_acceptada` | 48 | 6 | 4 |
| *(NULL)* | 44 | 1 | 0 |
| **`valor_descartat`** | **0** | **0** | **0** |

**Zero descartades a tot el corpus.** El camí mai s'ha exercit — ni per un tècnic, ni per un test
de dades. La branca `Rebutjat` de `resolve_size_check` **no té cap evidència d'execució a
staging**.

### R3.6 · **RESPOSTA DIRECTA: el descartat és una PEÇA NOVA**

No és un fix. Cinc coses hi falten, i tres d'elles són estructurals:

| # | Què falta | On | Tipus |
|---|---|---|---|
| 1 | `PieceFittingLine.decisio` — **la columna no existeix a Postgres** | `fitting_piecefittingline` (9 col.) | **migració + model** |
| 2 | Un lloc on el valor descartat sigui **visible fora del seu check** | cap entitat el projecta | **estructural** |
| 3 | Que una columna pugui existir **sense escriure la base** | `base_stages_view` deriva del log d'escriptures | **estructural** |
| 4 | Desacoblar `valor_descartat` (línia) de `Rebutjat` (check) | [services_size_check.py:196-211](backend/fhort/models_app/services_size_check.py#L196-L211) | lògica |
| 5 | Un marcatge de presentació (vermell) per a un valor **no vigent però real** | `MeasureGrid` marca «difereix de base», no «descartat» | UI |

El **3** és el que decideix. Avui **columna ⟺ escriptura a la base**. La regla decidida demana una
columna que **es vegi i no escrigui**. Això no és un paràmetre del lector: és un concepte que el
model de dades no té.

---

## R4 · QUI DECIDEIX QUINA COLUMNA ÉS VIGENT

### R4.1 · La troballa que reemmarca la pregunta

**Cap lector tria columna, als dos nivells.** «Vigent» i «columna» són coses diferents al sistema
d'avui:

- **El vigent és una FILA:** `BaseMeasurement.base_value_cm`, sobreescrita in situ. És el que
  llegeix el motor ([`_load_base_measurements`, pom/services.py:815-841](backend/fhort/pom/services.py#L815-L841)),
  el que serveix `base_stages_view` a `rows[].base_value_cm`
  ([views.py:3134](backend/fhort/models_app/views.py#L3134)), i el que copia `_materialize_lines`
  com a `valor_teoric` ([services_size_check.py:69](backend/fhort/models_app/services_size_check.py#L69)).
- **Les columnes són una RECONSTRUCCIÓ read-only**, feta a posteriori del log per carry-forward
  ([views.py:3094-3099](backend/fhort/models_app/views.py#L3094-L3099)), i **coincideixen amb el
  vigent per construcció**: *«l'últim estadi coincideix amb la base vigent (BaseMeasurement)»*
  ([views.py:3051-3052](backend/fhort/models_app/views.py#L3051-L3052)).

**Per tant «l'última NO DESCARTADA» no és un criteri alternatiu que calgui substituir a N lectors:
és un concepte que no existeix.** Zero lectors hi sobreviurien, perquè zero lectors trien.

### R4.2 · Taula de lectors — nivell TALLA BASE

| # | Node | Què resol | Criteri | Sobreviu a «l'última no descartada»? |
|---|---|---|---|---|
| B1 | [pom/services.py:815-841](backend/fhort/pom/services.py#L815-L841) `_load_base_measurements` | el valor que gradua el motor | **`BaseMeasurement` directe**; filtres `is_active`, no-null, `≠0`; `order_by('ordre')` | **N/A — no tria columna** |
| B2 | [views.py:3080-3110](backend/fhort/models_app/views.py#L3080-L3110) `base_stages_view` | la llista de columnes | **totes** les `(context, segon)` amb `base_measurement` no nul, per `created_at, id` | **No: no en descarta cap** |
| B3 | [views.py:3111-3117](backend/fhort/models_app/views.py#L3111-L3117) filtre FaseD | quines columnes es pinten | descarta les **buides per a les files mostrades** | Únic filtre existent; **no mira decisions** |
| B4 | [views.py:3134](backend/fhort/models_app/views.py#L3134) | la xifra «vigent» de cada fila | **`bm.base_value_cm`** — la fila, no cap columna | **N/A** |
| B5 | [CheckMeasureEditor.jsx:236-239](frontend/src/components/model/CheckMeasureEditor.jsx#L236-L239) | la cel·la «Real (proto)» | `line.valor_real ?? line.valor_teoric` d'**un sol check** | **No** |
| B6 | [CheckMeasureEditor.jsx:195](frontend/src/components/model/CheckMeasureEditor.jsx#L195) (treball) | **quin check** | l'últim **`Pendent`**; si cap, **en crea un** | *(diagnosi d'entrada)* |
| B7 | [CheckMeasureEditor.jsx:193-194](frontend/src/components/model/CheckMeasureEditor.jsx#L193-L194) (consulta) | **quin check** | l'últim de **qualsevol estat** | *(diagnosi d'entrada)* |
| B8 | [pom/services.py:369-410](backend/fhort/pom/services.py#L369-L410) `preview_graded_specs` | preview del wizard | cos HTTP o mateix criteri que B1 | **N/A** |

### R4.3 · Taula de lectors — nivell GRAELLA (fitting)

**El mateix patró es repeteix, i amb una divergència pròpia:**

| # | Node | Què resol | Criteri | Divergent? |
|---|---|---|---|---|
| G1 | [fitting/services.py:553-561](backend/fhort/fitting/services.py#L553-L561) `_active_grading_version` | versió on s'escriu | `is_active=True`, desempat `-version_number` | — |
| G2 | [fitting/services.py:564-580](backend/fhort/fitting/services.py#L564-L580) `vigent_grading_version` | versió que llegeixen les **superfícies** | `_active_grading_version`; **si cap activa → fallback a `-version_number`, `-data`** | ⚠️ **criteri PROPI de lectura**, documentat com a tal ([:566-567](backend/fhort/fitting/services.py#L566-L567)) |
| G3 | [pom/services.py:86-97](backend/fhort/pom/services.py#L86-L97) `sealed_active_version` | el guard del segell | `is_active AND aprovada`, `-version_number` | — |
| G4 | [pom/services.py:875-877](backend/fhort/pom/services.py#L875-L877) `_get_or_create_grading_version` | versió on s'escriu | `is_active`, `-version_number`; **si cap → en crea una** | *(forat d'atomicitat, diagnosi d'entrada §Q8)* |
| G5 | [serializers.py:286-299](backend/fhort/fitting/serializers.py#L286-L299) | les **columnes** de la graella | **TOTES** les GradingVersion amb spec per a la línia | **Les columnes són VERSIONS, no preses** |
| G6 | [fittingGridAdapter.jsx:41-47](frontend/src/components/model/fittingGridAdapter.jsx#L41-L47) | la cel·la activa | `line.valor_real ?? ''`; `baseValue = evolucio[0].valor_cm` | **No** |
| G7 | [measureSources.jsx:38-39](frontend/src/components/model/measureSources.jsx#L38-L39) | **quina PieceFitting** | la del model a la sessió, **o `[0]` si no la troba** | ⚠️ **fallback silenciós a la primera peça de la sessió** |

**G7 és el bessó exacte de la divergència del check** que la diagnosi d'entrada va trobar (B6/B7):
si la sessió no té peça per a aquest model, agafa la **primera de la sessió** — que és la peça
**d'un altre model**. Latent avui (les 5 peces de staging estan en sessions d'un sol model), però
és el mateix patró de «tria el que sigui abans que dir que no».

### R4.4 · Comptatge

| | lectors que trien columna per data/estat | lectors que agafen «l'última a seques» | lectors que sobreviurien a «l'última no descartada» |
|---|---|---|---|
| **Talla base** | **0** | **0** *(agafen la FILA vigent)* | **0 — no hi ha res a triar** |
| **Graella** | **0** *(trien VERSIÓ, no presa)* | **0** | **0 — no hi ha preses històriques** |

---

## R5 · EL SAMPLE FITTING SOBRE LA GRAELLA — què hi ha ja construït

### R5.1 · Com es materialitzen les línies

[fitting/services.py:292-351](backend/fhort/fitting/services.py#L292-L351) `create_piece_fitting`:

1. `sf = _resolve_working_size_fitting(model)`; si no n'hi ha, **el crea en l'acte**
   ([:307-315](backend/fhort/fitting/services.py#L307-L315)).
2. `version = _active_grading_version(sf)`; si no n'hi ha → `ValueError`
   ([:317-322](backend/fhort/fitting/services.py#L317-L322)).
3. `PieceFitting.objects.create(session, model, grading_version=version)` — clau
   `unique_together ('session','model')` ([models.py:303-304](backend/fhort/fitting/models.py#L303-L304)).
4. **Una `PieceFittingLine` per cada `GradedSpec` actiu de la versió**
   ([:337-348](backend/fhort/fitting/services.py#L337-L348)) — és a dir **una línia per
   `(pom, size_label, capa, instancia)`**, per a **TOTES** les talles.

**El teòric de cada cel·la surt de `GradedSpec.graded_value_cm`**
([:345](backend/fhort/fitting/services.py#L345)) — la taula de grading de la versió activa **en el
moment de crear la peça**.

### R5.2 · **El teòric ES CONGELA. Mateixa malaltia que el check.**

`grep -rn "valor_teoric\s*=" --include=*.py fhort/` (exclosos tests i migracions) dona **9
encerts**, i **cap** és una reescriptura:

| encert | què és |
|---|---|
| [fitting/models.py:401](backend/fhort/fitting/models.py#L401) | declaració del camp |
| [fitting/services.py:345](backend/fhort/fitting/services.py#L345) | **l'ÚNICA escriptura** (el clonatge) |
| [fitting/services.py:296](backend/fhort/fitting/services.py#L296) | docstring |
| [models_app/models.py:1243](backend/fhort/models_app/models.py#L1243), [:1254](backend/fhort/models_app/models.py#L1254) | el bessó del check |
| [services_size_check.py:4](backend/fhort/models_app/services_size_check.py#L4), [:19](backend/fhort/models_app/services_size_check.py#L19), [:69](backend/fhort/models_app/services_size_check.py#L69), [:81](backend/fhort/models_app/services_size_check.py#L81) | el bessó del check |

**Cap camí actualitza `PieceFittingLine.valor_teoric` mai.** Confirmat també per l'única porta
d'escriptura de línia, que ho declara: `propagar` diu literalment **«`valor_teoric` NO es toca
mai»** ([fitting/views.py:598](backend/fhort/fitting/views.py#L598)) i ho repeteix a
[:614](backend/fhort/fitting/views.py#L614).

**Per tant sí: si el graduat canvia després d'obrir la peça, el teòric de la graella queda
enrere**, exactament com els 41 dies del model 182 al check. **La diferència és que aquí el
desfasament és INVISIBLE**, perquè `valor_real` neix igual al teòric (§R3.2) i la cel·la ensenya
`valor_real`.

### R5.3 · Concepte de «columna» a la graella: **n'hi ha un, i no és el de la regla**

Les `historyCols` del fitting són **GradingVersions**, no preses:

[fittingGridAdapter.jsx:14-16](frontend/src/components/model/fittingGridAdapter.jsx#L14-L16):
```js
const versionLabel = (vn, idx, t) =>
  idx === 0 ? t('fitting.grid.base') : t('fitting.grid.fit', { n: vn - 1 })
```
[:25](frontend/src/components/model/fittingGridAdapter.jsx#L25): `historyCols: versionNumbers.map(...)`,
i `versionNumbers` surt de `line.evolucio`
([measureSources.jsx:29-31](frontend/src/components/model/measureSources.jsx#L29-L31)), que el
backend omple **amb els `GradedSpec` de cada versió**
([serializers.py:286-299](backend/fhort/fitting/serializers.py#L286-L299)).

**Les etiquetes diuen «Base, Fit 1, Fit 2»** — semblen preses — **però els valors són teòrics de
grading.** I `PieceFittingLine` ho declara: *«Only the two current values are stored. The evolution
across versions is read dynamically from the GradingVersion history, NOT materialised here.»*
([fitting/models.py:391-395](backend/fhort/fitting/models.py#L391-L395)).

**Cada `PieceFitting` és una taula independent**, lligada a `(session, model)`. **No hi ha cap
concepte de sèrie de preses sobre la graella.** El `valor_real` és un camp únic, sobreescrit in
situ, sense història.

### R5.4 · Dades reals

```sql
select pf.id, pf.model_id, pf.gate, pf.grading_version_id, s.data, s.fase, s.estat,
       count(l.id) n_linies, count(distinct l.size_label) n_talles, count(l.valor_real) n_reals
from fhort.fitting_piecefitting pf join fhort.fitting_fittingsession s on s.id=pf.session_id
left join fhort.fitting_piecefittingline l on l.piece_fitting_id=pf.id group by 1,2,3,4,5,6,7;
```

| pf | model | gate | gv | data | fase | estat sessió | línies | talles | amb `valor_real` |
|---|---|---|---|---|---|---|---|---|---|
| 10 | **162** | Pendent | 30 | 2026-06-08 | Proto | Tancada | 42 | **3** | **42** |
| 15 | **182** | Pendent | 46 | 2026-06-17 | SizeSet | Tancada | 42 | **3** | **42** |
| 16 | **182** | Pendent | 47 | 2026-06-18 | PP | Tancada | 41 | **3** | **41** |
| 18 | **185** | Pendent | 51 | 2026-06-22 | Dev | Tancada | 14 | **7** | **14** |
| 19 | **185** | Pendent | 65 | 2026-07-11 | Proto | Tancada | 14 | **7** | **14** |

**5 sample fittings · 3 models (162, 182, 185) · 3 a 7 talles · 24 `FittingSession` en total** (les
altres 19 no han materialitzat cap peça). **El 100% de les línies té `valor_real`** — coherent amb
§R3.2: neixen omplertes.

I el contrast que ho tanca: **el fitting va produir només 7 files de log `context='fitting'` a tot
el corpus** (§R1.2), sobre **153 línies materialitzades**. La resta —incloent-hi **totes** les
no-base— no ha arribat mai a la base.

### R5.5 · **La llei de columnes hi val igual? — On coincideix, on divergeix, on NO EXISTEIX**

| Punt de la regla decidida | Talla base (check) | Graella (sample fitting) |
|---|---|---|
| «Neix columna en desar canvi MATERIAL» | ✅ **ja hi coincideix** (guard [signals.py:310-311](backend/fhort/models_app/signals.py#L310-L311)) | ❌ **NO EXISTEIX**: cap columna de presa |
| «Neix columna en consolidar un FITTING» | ✅ **ja hi coincideix** ([fitting/services.py:394](backend/fhort/fitting/services.py#L394) → `context='fitting'`) | ❌ **NO EXISTEIX** |
| «NO neix en obrir pantalla» | ✅ per a la columna · ❌ **el CHECK sí que neix en obrir** | ❌ **la PEÇA neix en obrir** ([measureSources.jsx:42](frontend/src/components/model/measureSources.jsx#L42)) |
| «NO neix en resoldre un check» | ❌ **divergeix**: cada `resolve` que escriu base pinta columna (7 al model 182) | N/A |
| «NO neix en canviar només DELTES» | ✅ els deltes van a `ModelGradingRule`, no a `BaseMeasurement` | ✅ *(però les columnes SÓN versions de grading → un regrade SÍ que en pinta)* ⚠️ **invertit** |
| «S'afegeix LÍNIA quan només s'afegeix un POM» | ❌ **divergeix**: crea columna. *(El senyal `valor_anterior IS NULL` ja existeix, §R2.4)* | ❌ **NO EXISTEIX** |
| «Vigent = l'última NO DESCARTADA» | ❌ **NO EXISTEIX**: ningú tria columna (§R4) | ❌ **NO EXISTEIX** |
| «Descartat = dada guardada i marcada» | ⚠️ **a mitges**: vocabulari sí, tot-o-res per check, 0 files | ❌ **NO EXISTEIX**: cap camp de decisió |
| «Sample fitting = sobre la TOTALITAT de columnes de talles» | N/A | ❌ **CONTRADIU una llei vigent**: PEÇA 4 el limita a la base |

### R5.6 · ⚠️ La contradicció que decideix l'abast

La regla decidida diu: **«sample fitting = sobre la TAULA DE GRADING, o sigui la TOTALITAT DE
COLUMNES DE TALLES»**.

El sistema d'avui té la llei **contrària**, escrita en tres llocs i amb nom propi (**PEÇA 4** /
**P1**):

1. **Consolidació:** [fitting/services.py:379-380](backend/fhort/fitting/services.py#L379-L380) —
   `if line.size_label.strip() != base_size: continue  # PEÇA 4: la sessió de fitting toca NOMÉS
   la talla base`.
2. **Escriptura:** [fitting/views.py:583-586](backend/fhort/fitting/views.py#L583-L586) —
   `fitting_line_is_non_base(line)` → **400**, amb el comentari *«no és conflicte d'estat sinó
   escriptura fora de l'eix del fitting»*.
3. **Pintat:** [fittingGridAdapter.jsx:5-8](frontend/src/components/model/fittingGridAdapter.jsx#L5-L8)
   — *«Eix (P1): UN sol GROUP, la TALLA BASE … El fitting és un ESTADI de la taula base
   (DECISIONS.md §2); el treball multi-talla viu a Escalat»*.

**Les 153 línies no-base materialitzades a staging són, avui, dades mortes: existeixen, no es
poden editar (400), no es pinten enlloc i no es consoliden mai.** Estendre la llei de columnes a la
graella **no és afegir columnes: és revertir una llei de domini vigent i documentada**. Això és
decisió humana (Patró C), no d'implementació.

---

## R6 · LES TRES PANTALLES — mesura de l'ona

### R6.1 · Els tres rols, i on viuen avui

| Rol volgut | Component/i avui | Estat |
|---|---|---|
| **(1) POMs + talla base** | [MeasuresEntryPanel.jsx](frontend/src/components/model/MeasuresEntryPanel.jsx) (alta) + [CheckMeasureEditor.jsx](frontend/src/components/model/CheckMeasureEditor.jsx) `checkSource` (taula) | **barrejat amb (2)** |
| **(2) Graduació (base + deltes)** | **DINS del mateix `CheckMeasureEditor`**: `RegleCell` ([:150-177](frontend/src/components/model/CheckMeasureEditor.jsx#L150-L177)) + `regimeLeadCol` ([fittingGridAdapter.jsx:80](frontend/src/components/model/fittingGridAdapter.jsx#L80)) | **barrejat amb (1)** |
| **(3) Graduació propagada** | [PropagatedEditor.jsx](frontend/src/pages/PropagatedEditor.jsx), tab **Escalat** ([ModelSheet.jsx:686](frontend/src/pages/ModelSheet.jsx#L686)) | ✅ **JA SEPARAT** |

**Els tabs vius** ([ModelSheet.jsx:34](frontend/src/pages/ModelSheet.jsx#L34)):
`['Dashboard','Resum','Mesures','Escalat','Patró','Fitxa tècnica','Fitxers',"Registre d'activitat",'Tasques']`.

### R6.2 · On es barregen (1) i (2)

Al tab **Mesures**, el mateix `CheckMeasureEditor` pinta:
- la **columna de mesura** (rol 1): `historyCols` dels estadis + `activeLabel` «Real (proto)»
  ([:203-211](frontend/src/components/model/CheckMeasureEditor.jsx#L203-L211));
- i les **regles de graduació** (rol 2): `RegleCell` amb inputs de **Δ delta**, **Δ break** i
  selector de **talla de trencament** ([:155-176](frontend/src/components/model/CheckMeasureEditor.jsx#L155-L176)).

Que això sigui un problema **ja està reconegut al codi**. `MeasureGrid`
([:296-303](frontend/src/components/model/MeasureGrid.jsx#L296-L303)) porta un pegat d'UI amb
l'incident sencer documentat:

> *«FIX-4 (DIAGNOSI_MESURES_TEA_205) — MESURA i DELTA no es poden confondre. […] Al 205 algú va
> escriure l'increment `1` a la cel·la de talla d'un POM amb base 46; el camp Δ i la cel·la de
> mesura eren dos números iguals a pocs píxels, sense res que digués que són coses diferents.»*

La resposta va ser `leadGroupLabel` / `groupsLabel` — **títols per separar-los visualment**, amb
l'anotació explícita **`OPT-IN: sense leadGroupLabel la capçalera és exactament la de sempre (check
i fitting intactes)`** ([:301-302](frontend/src/components/model/MeasureGrid.jsx#L301-L302)).
**Un incident real de dades ja va sortir d'aquesta barreja, i la mitigació va ser cosmètica i
opcional.**

### R6.3 · Cost de la separació — **re-rutar, no refer**

L'arquitectura **ja té la costura**. `CheckMeasureEditor` està parametritzat per **fonts** (§Sprint
Y): un objecte amb 4 *seams* — `load` · `buildGroups`/`buildRows` · `makeOnSave` · `buildLeadCols`
([measureSources.jsx:3](frontend/src/components/model/measureSources.jsx#L3)). N'hi ha **tres
implementades**: `checkSource` ([CheckMeasureEditor.jsx:181](frontend/src/components/model/CheckMeasureEditor.jsx#L181)),
`fittingSource` ([measureSources.jsx:56](frontend/src/components/model/measureSources.jsx#L56)) i
l'adapter de repàs ([repasGridAdapter.jsx](frontend/src/components/model/repasGridAdapter.jsx)).

I la separació **ja s'exerceix avui, per un altre motiu**: el flag `lockRules`
([ModelSheet.jsx:655](frontend/src/pages/ModelSheet.jsx#L655)) posa les regles en read-only quan hi
ha sessió de fitting, via el **tercer argument de `regimeLeadCol`**
([measureSources.jsx:90-92](frontend/src/components/model/measureSources.jsx#L90-L92):
`return [regimeLeadCol(ctx.t, () => {}, true)]`).

**Mesura de l'ona:**

| Peça | Ona |
|---|---|
| Rol (3) | **0** — `PropagatedEditor` ja és un component i un tab propis |
| Rol (2) fora de Mesures | **petita** — treure `RegleCell`/`regimeLeadCol` dels `leadCols` de `checkSource`. La font ja controla `buildLeadCols`; hi ha precedent exacte a `fittingSource` |
| Rol (1) net | **petita** — `checkSource` sense `leadCols` de regla |
| **Nova pantalla per al rol (2)** | **mitjana** — cal decidir d'on beu (`ModelGradingRule` per model, o el `GradingRuleSet` del contenidor). **`MeasureGrid` es reusa; el que es refà és el contenidor** |
| Rutes i tabs | **petita** — `TABS` és un array literal ([ModelSheet.jsx:34](frontend/src/pages/ModelSheet.jsx#L34)) + `TAB_LABELS` |

**Veredicte: és re-rutar components existents, no refer-los.** El component compartit
(`MeasureGrid`, 20+ props documentades) és **agnòstic del rol**: rep `groups`, `rows`, `leadCols`.
El cost real no és de codi, és de **decidir quin backend alimenta la pantalla del rol (2)** — i
això travessa `ModelGradingRule` vs `GradingRuleSet`, que és zona intocable per CLAUDE.md.

*(No dissenyo la UI, per encàrrec: només la mesura.)*

---

## R7 · L'ONA DEL CANVI DE DISPARADOR

### R7.1 · Precisió necessària: **hi ha DOS disparadors, no un**

El brief parla d'«obrir → desar». Cal separar dues coses que avui es confonen:

| | Què neix | On | Neix en obrir? |
|---|---|---|---|
| **La COLUMNA** (estadi de `base_stages`) | fila de `MeasurementChangeLog` | [signals.py:335+](backend/fhort/models_app/signals.py#L335) | **NO. Ja neix en desar un canvi material.** |
| **El CONTENIDOR de treball** (`SizeCheck` / `PieceFitting`) | fila de `SizeCheck` o `PieceFitting` + línies | [services_size_check.py:116](backend/fhort/models_app/services_size_check.py#L116) · [fitting/services.py:326](backend/fhort/fitting/services.py#L326) | **SÍ. Els dos.** |

**El canvi de disparador que demana la regla no és sobre la columna: és sobre el contenidor.**

### R7.2 · Nodes que es toquen

| # | Node | Rol | Què canvia |
|---|---|---|---|
| N1 | [services_size_check.py:103-120](backend/fhort/models_app/services_size_check.py#L103-L120) `open_size_check` | **crea el contenidor del check** | l'`open` hauria de deixar de crear |
| N2 | [views_size_check.py:48-60](backend/fhort/models_app/views_size_check.py#L48-L60) `POST /size-checks/open/` | **única porta HTTP de N1** | el verb `POST` + el nom `open` deixarien de dir la veritat |
| N3 | [CheckMeasureEditor.jsx:195](frontend/src/components/model/CheckMeasureEditor.jsx#L195) | **únic cridador de N2** | passaria a llegir |
| N4 | [measureSources.jsx:35-54](frontend/src/components/model/measureSources.jsx#L35-L54) `resolvePieceFitting` | **crea el contenidor del fitting** | *«Materialització EN OBRIR (decisió 6)»* — el bessó de N3 |
| N5 | [fitting/views.py:184-205](backend/fhort/fitting/views.py#L184-L205) `create-piece` | porta HTTP de N4 | ja retorna **409 `piece_exists`** ([:196-203](backend/fhort/fitting/views.py#L196-L203)) — **la idempotència ja hi és** |
| N6 | [signals.py:306-311](backend/fhort/models_app/signals.py#L306-L311) | el guard de materialitat | **no cal tocar-lo: ja fa el que la regla demana** |
| N7 | [views.py:3086-3092](backend/fhort/models_app/views.py#L3086-L3092) | agrupació `(context, segon)` | caldria si la columna ha de ser **per acte** i no per segon |
| N8 | [views.py:1941-1948](backend/fhort/models_app/views.py#L1941-L1948) | `created` vs `updated` | la distinció línia/columna hi és **com a comptador**, no com a senyal (§R2.4) |

### R7.3 · El cas dolent — **no és un, són dos**

La diagnosi d'entrada va deixar establert que obrir la pantalla de Mesures en mode treball
**escriu** (crea un `SizeCheck`). **La mateixa peça existeix al fitting, i és més cara.**

[measureSources.jsx:35-43](frontend/src/components/model/measureSources.jsx#L35-L43):
```js
// Resol la PieceFitting d'aquesta sessió per al model. Materialització EN OBRIR (decisió 6): si la
// sessió encara no té peça, la crea (create-piece és idempotent des de XD: 409 si ja existeix).
async function resolvePieceFitting(model, fittingSession) {
  const existing = (fittingSession?.piece_fittings || []).find(p => p.model === model.id …)
    || (fittingSession?.piece_fittings || [])[0]
  if (existing) return existing.id
  try {
    const res = await fittingSessions.createPiece(fittingSession.id, model.id)
```

**Obrir la tab Mesures amb una sessió de fitting resolta i sense peça crea una `PieceFitting` i
CLONA cada `GradedSpec` actiu en una `PieceFittingLine`** — **42 files** als models de staging
([fitting/services.py:337-348](backend/fhort/fitting/services.py#L337-L348)). Una lectura que
escriu 43 files.

**Diferència a favor del fitting:** té `unique_together ('session','model')` i un **409 explícit**
([fitting/views.py:196-203](backend/fhort/fitting/views.py#L196-L203)) que fa la crida idempotent.
**El check no té cap constraint equivalent** — `SizeCheck` és `SENSE unique_together` per disseny
([models_app/models.py:1207-1208](backend/fhort/models_app/models.py#L1207-L1208)). Per això el
check en va acumular 12 i el fitting només 5.

### R7.4 · Tests que afirmen el comportament actual (per nom)

Verificats per lectura, no per execució:

| Fitxer | Test / classe | Què afirma |
|---|---|---|
| [test_size_check_completa_linies.py:100](backend/fhort/models_app/test_size_check_completa_linies.py#L100), [:112](backend/fhort/models_app/test_size_check_completa_linies.py#L112), [:116](backend/fhort/models_app/test_size_check_completa_linies.py#L116) | crides directes a `open_size_check` | **`open` crea/completa**. 16 invocacions al fitxer |
| [test_size_check_completa_linies.py:116-124](backend/fhort/models_app/test_size_check_completa_linies.py#L116-L124) | `sc2, n2 = open_size_check(...)` | **reutilització del `Pendent`** — l'afirmació que el canvi tocaria de ple |
| [test_base_stages_no_regressio.py](backend/fhort/models_app/test_base_stages_no_regressio.py) | tot el fitxer | **el node del PIN** de `base_stages_view`. Capçalera: *«Decisió d'Agus (28/07, innegociable): la taula de mesures és l'eina d'IMPRESSIÓ»* |
| [test_g6_estalitud.py](backend/fhort/fitting/test_g6_estalitud.py) `EstalitudTest` | usa `resolve_size_check` **real** ([:9](backend/fhort/fitting/test_g6_estalitud.py#L9): *«amb el codi de debò, no amb una imitació»*) | el 7è camí. **En vermell des del 28/07** (§R8) |
| [fitting/test_repas.py:178](backend/fhort/fitting/test_repas.py#L178) | `UN FITTING NO ÉS SEMPRE UNA FittingSession` | decisió Agus 28/07 |

⚠️ **`base_stages_view` és «el node del pin»: 13 tests el vigilen** (declarat a
[views.py:3111-3113](backend/fhort/models_app/views.py#L3111-L3113) via el comentari de FASE_2).
Qualsevol canvi a l'agrupació `(context, segon)` (N7) hi passa per sobre.

### R7.5 · Què es trencaria

| Node | Trencament |
|---|---|
| N1/N2 | Si `open` deixa de crear, **`_materialize_lines` deixa de córrer** i es reobre FIX-3 (DIAGNOSI_MESURES_TEA_205): un POM nascut després del check queda com a **fila inerta** — es veu, no es pot anotar ([services_size_check.py:22-29](backend/fhort/models_app/services_size_check.py#L22-L29)). El codi ho declara com la raó de posar-ho a `open`: *«l'editor la crida SEMPRE en obrir-se»* ([:90-91](backend/fhort/models_app/services_size_check.py#L90-L91)) |
| N4 | Sense peça materialitzada, la superfície de fitting **no té graella** i cau al `catch` de [CheckMeasureEditor.jsx:312-322](frontend/src/components/model/CheckMeasureEditor.jsx#L312-L322) amb el missatge de `no_grading` |
| N7 | Els **13 tests del pin** de `base_stages_view` |
| — | Els **53 vermells** (§R8) tapen avui `EstalitudTest`, `ElsSisCaminsTest` i `GateDeLesReglesResidentsTest`: **la xarxa de verificació d'aquest tram no s'executa des del 28/07** |

---

## R8 · ELS 53, TANCATS

### R8.1 · Les 6 classes que ahir van quedar per patró — **traçades**

| Classe | Fitxer:línia | Base | Punt de xoc | Traçat |
|---|---|---|---|---|
| **AvisAlMotorTest** | [test_g6_estalitud.py:154](backend/fhort/fitting/test_g6_estalitud.py#L154) | `_BancSegellat` → `_SegellBase` | `_SegellBase.setUp:79` | ✅ herència verificada ([:22](backend/fhort/fitting/test_g6_estalitud.py#L22), [:33](backend/fhort/fitting/test_g6_estalitud.py#L33) `super().setUp()`) |
| **ElsSisCaminsTest** | [test_g6_segell.py:103](backend/fhort/pom/test_g6_segell.py#L103) | `_SegellBase` | `_SegellBase.setUp:79` | ✅ **sense `setUp` propi** |
| **IntegritatDelMotorTest** | [test_g6_segell.py:156](backend/fhort/pom/test_g6_segell.py#L156) | `_SegellBase` | `_SegellBase.setUp:79` | ✅ **sense `setUp` propi** |
| **ApproveActionTest** | [test_g6_segell.py:253](backend/fhort/pom/test_g6_segell.py#L253) | `_SegellBase` | `_SegellBase.setUp:79`, **abans que el seu propi cos** ([:256-260](backend/fhort/pom/test_g6_segell.py#L256-L260) comença amb `super().setUp()`) | ✅ |
| **Fork4VersioVigentTest** | [test_g6_grading_gates.py:66](backend/fhort/pom/test_g6_grading_gates.py#L66) | `_G6Base` | **`_G6Base._sf():60`**, cridat des de [:73](backend/fhort/pom/test_g6_grading_gates.py#L73) | ✅ **camí DIFERENT** |
| **GateDeLesReglesResidentsTest** | [test_g6_grading_gates.py:122](backend/fhort/pom/test_g6_grading_gates.py#L122) | `_G6Base` | **`_G6Base._sf():60`**, cridat des de [:134](backend/fhort/pom/test_g6_grading_gates.py#L134) **i des del cos de [:174](backend/fhort/pom/test_g6_grading_gates.py#L174)** | ✅ **camí DIFERENT + 2n punt** |

**El traçat de `_G6Base` (el camí que ahir no s'havia mirat):**

[test_g6_grading_gates.py:40-63](backend/fhort/pom/test_g6_grading_gates.py#L40-L63):
```python
def setUp(self):
    self.user = get_user_model().objects.create(username='g6')
    self.profile, _ = UserProfile.objects.get_or_create(...)   # :43 ← ja hi ha un perfil
    ...                                                        # NO crea cap Model aquí
def _model(self, codi, *, rule_set=None):
    return Model.objects.create(codi_intern=codi, …)           # :53 ← DISPARA EL SIGNAL → SF nº1
def _sf(self, model, codi, estat='Pendent'):
    return SizeFitting.objects.create(model=model, numero=1, …)  # :60 ← 💥 IntegrityError
```

`Fork4VersioVigentTest.setUp` ([:69-73](backend/fhort/pom/test_g6_grading_gates.py#L69-L73)):
`super().setUp()` → `self._model('TST-162')` (**:72**, signal crea SF nº1) → `self._sf(...)`
(**:73**, xoca). **Idèntic mecanisme, altre fitxer.**

### R8.2 · **Totes 53 tenen la mateixa causa?** — SÍ, i el recompte quadra exactament

| Fitxer | `def test_` | Classes | Punt de xoc |
|---|---|---|---|
| [fitting/tests.py](backend/fhort/fitting/tests.py) | **16** | `PropagarActionTest` | **`setUp:60`** |
| [fitting/test_g6_estalitud.py](backend/fhort/fitting/test_g6_estalitud.py) | **13** | `EstalitudTest`, `AvisAlMotorTest`, `R7UnaSolaActivaTest` (+`_BancSegellat`) | **`_SegellBase.setUp:79`** |
| [pom/test_g6_segell.py](backend/fhort/pom/test_g6_segell.py) | **17** | `ElsSisCaminsTest`, `IntegritatDelMotorTest`, `CrudDelSegellTest`, `ApproveActionTest` (+`_SegellBase`) | **`_SegellBase.setUp:79`** |
| [pom/test_g6_grading_gates.py](backend/fhort/pom/test_g6_grading_gates.py) | **7** | `Fork4VersioVigentTest`, `GateDeLesReglesResidentsTest` (+`_G6Base`) | **`_G6Base._sf():60`** |

- **`fhort.fitting`: 16 + 13 = 29** ✅ *(el brief diu 29)*
- **`fhort.pom`: 17 + 7 = 24** ✅ *(el brief diu 24)*
- **TOTAL: 53** ✅
- **10 classes de test**, exactament les 10 del brief.

**Els 53 són EXACTAMENT aquests 4 fitxers, ni un test més ni un menys.** Cap causa pròpia; cap
tercera família.

### R8.3 · **UNA causa, TRES línies. Es netegen d'un cop.**

| # | Peça de fixture | Tests que en depenen |
|---|---|---|
| 1 | [fitting/tests.py:60-61](backend/fhort/fitting/tests.py#L60-L61) | **16** |
| 2 | [pom/test_g6_segell.py:79-81](backend/fhort/pom/test_g6_segell.py#L79-L81) | **30** (17 + 13 per herència) |
| 3 | [pom/test_g6_grading_gates.py:59-63](backend/fhort/pom/test_g6_grading_gates.py#L59-L63) `_G6Base._sf()` | **7** |

⚠️ **Un matís que decideix el «com»:** `_G6Base._sf()` **no és només de `setUp`** — també es crida
des del **cos d'un test** ([test_g6_grading_gates.py:174](backend/fhort/pom/test_g6_grading_gates.py#L174),
dins `test_un_model_SENSE_regles_enlloc_continua_sense_poder_graduar`). Netejar només els `setUp`
deixaria aquell viu. **La peça a tocar és l'helper, no el `setUp`.**

### R8.4 · **La data del 28/07 — el límit declarat d'ahir queda TANCAT**

Ahir vaig deixar declarat que el commit que arma la col·lisió és del **20/07** (`a2d4222d`) i que
no havia investigat què va passar el **28/07**. **La resposta és al repo, en 5 fitxers**, escrita
per sprints anteriors:

| Fitxer:línia | Text |
|---|---|
| [pom/test_g6_grading_gates.py:155-157](backend/fhort/pom/test_g6_grading_gates.py#L155-L157) | *«⚠️ Aquest test estava en **VERMELL PREEXISTENT** quan es va fer el canvi (col·lisió `fitting_sizefitting_model_id_numero`, **28/07**), o sigui que el seu cos no s'executava»* |
| [pom/test_c3_a1_buidatge_wizard.py:94-95](backend/fhort/pom/test_c3_a1_buidatge_wizard.py#L94-L95) | *«…la col·lisió `fitting_sizefitting_model_id_numero` que té **53 tests** de la suite en vermell des del **28/07**»* |
| [pom/test_c3_b_dues_germanes.py:91-92](backend/fhort/pom/test_c3_b_dues_germanes.py#L91-L92) | idem |
| [models_app/test_c3_a2_transaccio_grading.py:60-61](backend/fhort/models_app/test_c3_a2_transaccio_grading.py#L60-L61) | idem |
| [models_app/test_base_stages_no_regressio.py:3](backend/fhort/models_app/test_base_stages_no_regressio.py#L3) | *«Decisió d'Agus (**28/07**, innegociable)»* |

**El 28/07 és la data d'OBSERVACIÓ documentada, no la de la causa.** La causa segueix sent
`a2d4222d` (20/07). Entre les dues dates la suite no es va córrer sencera, o no es va anotar. **La
xifra «53» ve d'aquests comentaris i coincideix exactament amb el recompte de §R8.2** — són la
mateixa observació, ara verificada.

⚠️ **I el cost real de tenir-los en vermell, ara comptable:** el docstring de
[test_g6_grading_gates.py:155-158](backend/fhort/pom/test_g6_grading_gates.py#L155-L158) diu que
un canvi de clau de C3/B *«és CORRECTE PER CONSTRUCCIÓ però no s'ha pogut observar en verd»*.
**Hi ha codi de producció fusionat el 02/08 la verificació del qual no s'ha executat mai.**

---

## TAULA DE NODES

### Escriptors de `BaseMeasurement` (el que fa néixer columna)

| Node | Grup | `origen` | Punter al registre | Guard de materialitat |
|---|---|---|---|---|
| [views.py:1955-1963](backend/fhort/models_app/views.py#L1955-L1963) `gravar_pom_view` | (a) | `MANUAL` | `motiu='gravar_pom'` | ❌ al camí · ✅ al signal |
| [views.py:1810](backend/fhort/models_app/views.py#L1810) `set_measurements_view` | (a) | hereta | — | ✅ al signal |
| [wizard_views.py:242](backend/fhort/pom/wizard_views.py#L242) | (a) | hereta | — | ✅ al signal |
| [fitting/services.py:383-396](backend/fhort/fitting/services.py#L383-L396) | (b) | `FITTED` | **`fitting_ref` → `SizeFitting`** | ✅ **+ `abs(Δ)<1e-6` propi** ([:377](backend/fhort/fitting/services.py#L377)) |
| [services_size_check.py:230-245](backend/fhort/models_app/services_size_check.py#L230-L245) | (c) | `CHECKED` | ⚠️ **cap FK** (deute anotat) | ✅ **+ guard propi** ([:238-240](backend/fhort/models_app/services_size_check.py#L238-L240)) |
| [extraction_views.py:2575](backend/fhort/models_app/extraction_views.py#L2575) | (d) | `IMPORTED` | — | ✅ al signal |
| [services_derivacio.py:144](backend/fhort/models_app/services_derivacio.py#L144) | (d) | `DERIVAT` | — | ✅ al signal · **0 files** |
| [federation_service.py:769-791](backend/fhort/tenants/federation_service.py#L769-L791) | (d) | `FEDERAT` | — | ✅ al signal |
| [views.py:1445-1463](backend/fhort/models_app/views.py#L1445-L1463) | (d) | `COPIED` | — | ✅ al signal |

### Constructors i lectors de columna

| Node | Rol | Criteri | Risc |
|---|---|---|---|
| [signals.py:235-250](backend/fhort/models_app/signals.py#L235-L250) | captura `_old_value` | `SELECT` per PK | 🟢 |
| [signals.py:306-311](backend/fhort/models_app/signals.py#L306-L311) | **el guard de materialitat** | `old == new → return` | 🟢 **ja és la regla** |
| [signals.py:282-302](backend/fhort/models_app/signals.py#L282-L302) | log de PODA | gated per `_desactivat` | 🟢 |
| [views.py:3086-3092](backend/fhort/models_app/views.py#L3086-L3092) | **defineix la columna** | `(context, segon)` | 🔴 **proliferació**: 12 columnes al 182 |
| [views.py:3094-3099](backend/fhort/models_app/views.py#L3094-L3099) | carry-forward | snapshot acumulat | 🟡 1 canvi → columna de 20 valors |
| [views.py:3111-3117](backend/fhort/models_app/views.py#L3111-L3117) | poda de columnes buides | «cap valor displayable» | 🟢 únic filtre; **no mira decisions** |
| [pom/services.py:815-841](backend/fhort/pom/services.py#L815-L841) | **el que gradua** | `BaseMeasurement` directe | 🟢 **no llegeix el log mai** |

### Nodes del sample fitting

| Node | Rol | Comportament | Risc |
|---|---|---|---|
| [fitting/services.py:337-348](backend/fhort/fitting/services.py#L337-L348) | materialitza línies | **totes** les talles, `valor_real = valor_teoric` | 🔴 buit ≡ mesurat |
| [fitting/services.py:345](backend/fhort/fitting/services.py#L345) | teòric | **única escriptura de `valor_teoric`** | 🔴 **congelat** |
| [fitting/services.py:379-380](backend/fhort/fitting/services.py#L379-L380) | consolida | **només talla base** (PEÇA 4) | 🔴 **contradiu la regla decidida** |
| [fitting/views.py:583-586](backend/fhort/fitting/views.py#L583-L586) | guard d'escriptura | no-base → **400** | 🔴 idem |
| [fittingGridAdapter.jsx:20-29](frontend/src/components/model/fittingGridAdapter.jsx#L20-L29) | pinta | **un sol group** (base); cols = **versions** | 🔴 idem |
| [measureSources.jsx:35-54](frontend/src/components/model/measureSources.jsx#L35-L54) | resol la peça | **crea en obrir**; fallback a `[0]` | 🔴 **escriu llegint** + tria cega |
| [fitting/views.py:196-203](backend/fhort/fitting/views.py#L196-L203) | idempotència | **409 `piece_exists`** | 🟢 el check no en té equivalent |

---

## LÍMITS DECLARATS

1. **Cap test executat, cap escriptura, cap build.** Tot surt de lectura al HEAD `55e13cab`, de
   `SELECT` a `ftt_staging`@5433, i de `git show`/`git log`. Res s'ha reproduït executant-ho.
2. **`information_schema` per a les absències clau.** L'absència de `PieceFittingLine.decisio` i
   de `MeasurementChangeLog.size_check` està confirmada per `information_schema.columns`, no per
   lectura de model. **La resta de «NO EXISTEIX» són `grep` exhaustius**, i els cito amb el
   comandament.
3. **No he auditat la BD de `los`.** Té 0 `BaseMeasurement`, 0 `SizeCheck` i 0 `MeasurementChangeLog`
   rellevant: és catàleg federat sense feina de mesures. Tot el diagnòstic de dades és de `fhort`.
4. **Cap QA de navegador.** Els «qui veuria què» estan derivats de llegir el lector + les files de
   la BD.
5. **R6 no és un disseny.** He mesurat quins components barregen rols i quin tipus d'obra suposa
   separar-los. **No he dissenyat cap pantalla ni proposat cap ruta**, per encàrrec.
6. **La fragmentació de columna per frontera de segon (§R2.2b) és un risc estructural sense cap
   instància observada.** No l'he provocada.
7. **Els 53 no s'han comptat executant la suite** — s'han comptat amb `grep -c "def test_"` sobre
   els 4 fitxers. Coincideixen exactament amb el 29/24 del brief i amb els comentaris del repo,
   però **la coincidència no és la mateixa cosa que veure'ls fallar**.
8. **`DECISIONS.md §2`** el cito per la referència que en fa el codi
   ([fittingGridAdapter.jsx:6](frontend/src/components/model/fittingGridAdapter.jsx#L6)); no he
   obert el fitxer (és fitxer d'estat fora de git i pot haver derivat).
9. **No he auditat PROD.** Tot és staging.

---

## TRES RESPOSTES DIRECTES, SENSE HEDGING

### (a) El descartat és un FIX o una PEÇA NOVA?

**PEÇA NOVA.** No hi ha discussió possible en tres dels cinc fronts:

1. **Al fitting el camp no existeix a Postgres.** `fitting_piecefittingline` té **9 columnes** i cap
   és de decisió (`information_schema`, §R3.2). Fa falta migració i model.
2. **El model de columnes no pot representar un descartat.** Avui **columna ⟺ escriptura a
   `BaseMeasurement`**: `base_stages_view` es construeix del registre d'escriptures a la base
   ([views.py:3080-3092](backend/fhort/models_app/views.py#L3080-L3092)). Un valor descartat **no
   s'escriu**, per tant no genera log, per tant **no pot ser columna**. La regla demana una columna
   que **es vegi i no escrigui**: és un concepte que el model de dades no té.
3. **On existeix el vocabulari, la semàntica és la contrària.** `valor_descartat` no marca una
   línia: **converteix el check sencer en `Rebutjat` i impedeix escriure fins i tot les
   acceptades** ([services_size_check.py:196-211](backend/fhort/models_app/services_size_check.py#L196-L211)).
   Passar de tot-o-res-per-check a decisió-per-línia és canviar la llei del servei, no un paràmetre.

I la prova que el camí no està madur: **`valor_descartat` té ZERO files a tot el corpus**. Ningú
l'ha exercit mai — ni un tècnic ni un test de dades. La branca `Rebutjat` no té cap evidència
d'execució a staging.

L'única part que **sí** és un fix és el marcatge visual: `MeasureGrid` ja sap pintar en vermell una
cel·la que difereix de la base.

### (b) La llei de columnes val igual sobre la graella, o el sample fitting funciona amb una lògica diferent que caldria unificar?

**Ni una cosa ni l'altra: sobre la graella la llei de columnes NO EXISTEIX, i el que hi ha al seu
lloc és una llei de domini VIGENT I CONTRÀRIA.**

Sobre la talla base hi ha columnes de presa (estadis del registre). **Sobre la graella no n'hi ha
cap.** El que sembla columna al fitting són **GradingVersions** — teoria, no mesura
([serializers.py:286-299](backend/fhort/fitting/serializers.py#L286-L299),
[fittingGridAdapter.jsx:14-16](frontend/src/components/model/fittingGridAdapter.jsx#L14-L16)). El
valor mesurat viu en **un sol `valor_real` per línia, sobreescrit in situ, sense cap història** —
declarat al propi model: *«Only the two current values are stored»*
([fitting/models.py:391-395](backend/fhort/fitting/models.py#L391-L395)).

I la regla decidida —**«sample fitting = sobre la TOTALITAT DE COLUMNES DE TALLES»**— xoca de front
amb **PEÇA 4 / P1**, escrita en tres llocs i amb nom propi:
- consolidació: [fitting/services.py:379-380](backend/fhort/fitting/services.py#L379-L380) —
  *«PEÇA 4: la sessió de fitting toca NOMÉS la talla base»*;
- escriptura: [fitting/views.py:583-586](backend/fhort/fitting/views.py#L583-L586) — no-base → **400**;
- pintat: [fittingGridAdapter.jsx:5-8](frontend/src/components/model/fittingGridAdapter.jsx#L5-L8) —
  *«Eix (P1): UN sol GROUP, la TALLA BASE … el treball multi-talla viu a Escalat»*.

**Les 153 línies no-base materialitzades a staging són dades mortes**: existeixen, no es poden
editar, no es pinten enlloc, no es consoliden mai. Portar la llei de columnes a la graella no és
unificar dues lògiques: **és revertir una llei de domini vigent i documentada**, i això és decisió
humana (Patró C), no d'implementació.

### (c) El canvi de disparador (obrir → desar) es pot fer sense tocar el contracte HTTP?

**NO. Cauen dos endpoints, i un d'ells és `POST` per força.**

**El que sí que es pot fer sense tocar res:** la **columna** no cal moure-la. **Ja neix en desar un
canvi material**, gràcies al guard [signals.py:310-311](backend/fhort/models_app/signals.py#L310-L311).
Aquesta meitat de la regla ja és el comportament d'avui.

**El que no:** el que neix en obrir és el **CONTENIDOR**, i els seus dos punts de naixement són
endpoints HTTP amb la creació al nom i al verb:

1. **`POST /api/v1/size-checks/open/`** ([views_size_check.py:48-60](backend/fhort/models_app/views_size_check.py#L48-L60))
   — *«obre o reutilitza el check Pendent»*. Si deixa de crear, **el verb `POST` i el nom `open`
   deixen de dir la veritat**, i la resposta canvia de forma (avui retorna sempre un
   `SizeCheckGridSerializer`; hauria de poder retornar «no n'hi ha cap»). El seu únic cridador és
   [CheckMeasureEditor.jsx:195](frontend/src/components/model/CheckMeasureEditor.jsx#L195).

2. **`POST /api/v1/fitting-sessions/<id>/create-piece/`**
   ([fitting/views.py:184-205](backend/fhort/fitting/views.py#L184-L205)) — cridat en OBRIR des de
   [measureSources.jsx:42](frontend/src/components/model/measureSources.jsx#L42), retorna **201**
   i clona 42 files. Aquí el contracte **ja és honest** (diu `create`); el que hauria de canviar és
   **qui el crida i quan** — cosa que és frontend, no contracte.

**El resum operatiu:** el fitting es pot arreglar **sense tocar el contracte** (el 409
`piece_exists` ja hi és, [fitting/views.py:196-203](backend/fhort/fitting/views.py#L196-L203); el
que cal és deixar de cridar-lo en obrir). **El check, no**: `open` és l'únic punt on corre
`_materialize_lines`, i el codi ho declara com la seva raó de ser — *«l'editor la crida SEMPRE en
obrir-se»* ([services_size_check.py:90-91](backend/fhort/models_app/services_size_check.py#L90-L91)).
Treure-li la creació **sense** reubicar la materialització reobre FIX-3 (files inertes: es veuen,
no es poden anotar).

---

*Diagnosi Patró A · read-only · HEAD `55e13cab` · 2026-08-03. Document al working tree, **NO
commitejat**. Cap fix proposat, per encàrrec.*
