# DIAGNOSI — NOMENCLATURA EDITABLE AL MODEL (Decisió 7)

**Data:** 2026-08-28 · **Patró:** A (read-only) · **Cap fix, cap escriptura, cap suite.**

## PAS -1 · L'entorn, declarat

| | |
|---|---|
| `hostname` | **fhort-assessment** ✅ |
| `ftt-staging.service` → `WorkingDirectory` | **/var/www/ftt-staging/backend** ✅ · `active (running)` |
| gunicorn arrencat | **2026-08-28 06:08:16 UTC** (posterior a tot el codi d'aquest cens: el desplegat i el disc coincideixen) |
| HEAD de `dev` | **b48c0793** · 2026-08-27 05:47:46 · *«merge: la invariant dels landmarks i l'acta completa»* |
| fil motor viu | **cap** (`ps` net d'`exam_*`, `rosetta`, `manage.py test`) |

> Tot el que segueix és lectura de `/var/www/ftt-staging` a `b48c0793`. Cap worktree: no calia.

---

# 🚨 EL TITULAR: LA LLEI JA ESTÀ CONSTRUÏDA A MITGES, I LA MEITAT QUE HI HA ÉS LA DIFÍCIL

El brief demana un camp nou. **No en cal cap.** La nomenclatura per model existeix
(`BaseMeasurement.nom_fitxa`), **ja és editable a la graella**, ja resideix només al model, ja
és per peça, i el resolutor del front **ja la fa manar per damunt del catàleg**.

El que NO hi ha és: **la unicitat**, i **la porta única** (el llapis edita el nom per un endpoint
i la nomenclatura s'edita per un altre control i un altre endpoint). I hi ha **un forat viu** que
el brief no preveia: **l'import esborra l'override sense dir res.**

---

## Q1 · QUÈ EDITA EL LLAPIS AVUI

### Fets

| | |
|---|---|
| Component | `frontend/src/components/EditableTable/EditableTable.jsx:1364` — el botó `data-llapis="1"` |
| Què obre | l'editor del **NOM**, `EditableTable.jsx:1355` (`value={row.nom_canonic_model}`) |
| Camps que escriu | **`nom_canonic_model`** i **`nom_traduit_model`**, i cap més |
| Endpoint | `PATCH /api/v1/base-measurements/<bm_id>/noms/` (`EditableTable.jsx:367`, `onBateig` → `EditableTable.jsx:1359`) |
| Vista | `backend/fhort/models_app/views.py:4095` `base_measurement_noms_view` |
| Reixa de camps | `views.py:4090` `NOMS_POM_CAMPS = ('nom_canonic_model', 'nom_traduit_model')` |
| Taula/columna | `models_app_basemeasurement.nom_canonic_model` / `.nom_traduit_model` (`models_app/models.py:792` i `:797`) |
| Identitat de l'escriptura | **per `bm_id`** — una fila, i la fila és `(model, pom, capa, instancia, garment)` |

**El llapis NO escriu `nom_fitxa`.** La vista és deliberadament estreta i ho diu ella mateixa
(`views.py:4101-4104`): *«Endpoint PROPI i petit, no el serializer genèric… aquí només s'hi ha de
poder tocar la PRESENTACIÓ. Un camp qualsevol que hi entri de passada seria una mesura canviada
sense que ningú ho hagi demanat.»*

### 🚨 Però la nomenclatura JA és editable — per un altre camí

`EditableTable.jsx:1272-1274`:

```jsx
<NomenInput value={row.nom_fitxa} placeholder={row.client_code || row.pom_code || ''}
  onCommit={v => onCellChange(row.id, 'nom_fitxa', v)} />
```

- És un camp **sempre obert** (`EditableTable.jsx:1880`), no darrere del llapis.
- Escriu per `frontend/src/components/model/measureSources.jsx:119`:
  `baseMeasurements.update(bmId, { nom_fitxa: value || null })` — el **PATCH genèric** del
  `BaseMeasurementViewSet`, no l'endpoint de noms.
- `nom_fitxa` és a `fields` del serializer genèric: `models_app/serializers.py:513`.

### Lectura

Hi ha **dues portes d'escriptura amb dues lleis diferents** sobre la mateixa fila: el nom passa
per una vista petita, auditada i amb tope de 160 caràcters; la nomenclatura passa pel serializer
gros, que obre *tota* la fila (valor base, `origen`, `is_active`, toleràncies…). El propi
comentari de `views.py:4101` argumenta per què això és un risc — i és exactament el que la
nomenclatura fa servir avui.

---

## Q2 · ON VIU LA NOMENCLATURA QUE ES PINTA

### Fet: hi ha DUES cadenes de resolució, i no diuen el mateix

**Cadena A — el resolutor del FRONT** (`frontend/src/utils/nomenclaturaPom.js:33`
`nomenclaturaDePom(bm)`):

```
nom_fitxa → client_alias → codi_client → pom_abbreviation|abbreviation → pom_code|codi → pom_code_global
```

🔑 **El `nom_fitxa` del model va PRIMER.** L'override ja mana per damunt de l'àlies del client i
del catàleg. Provat a `frontend/src/utils/nomenclaturaPom.test.js:20-52`.

**Cadena B — el resolutor del BACKEND** (`backend/fhort/pom/nomenclatura.py:270` `codi_de` i
`:284` `abreviatura_de`):

```
àlies del client → codi_client del tenant → codi/abbreviation global
```

🚨 **No hi ha nivell de MODEL en aquesta cadena.** `codi_de` rep un `pom`, no una
`BaseMeasurement`: estructuralment no pot veure el `nom_fitxa`.

### Fet: quina superfície fa servir quina

| superfície | d'on surt el codi | fitxer:línia | veu l'override? |
|---|---|---|---|
| **Graella del model** | `nom_fitxa` (camp propi) + `pom_code`/`abbreviation` de la cadena B com a *placeholder* | `EditableTable.jsx:1272` · `models_app/serializers.py:465,474` | ✅ |
| **Fitxa tècnica (editor + PDF)** | `nomenclaturaDePom` (cadena A) | `TechSheetEditor.jsx:5292` · `:782` | ✅ |
| **Full d'impressió de fitting** | `l.nom_fitxa \|\| l.codi` | `FittingPrintSheet.jsx:295` | ✅ |
| **Size check** | `bm.nom_fitxa` → fallback `pom.pom_code` | `models_app/serializers_size_check.py:118` | ✅ |
| **Fitting (croquis)** | `nom_fitxa_map` → fallback `pom.pom_code` | `fitting/serializers.py:385,388` | ✅ |
| **Repàs** | `nom_fitxa_map` → fallback `pom.pom_code` | `fitting/repas_views.py:416` | ✅ |
| **Escalat / graduació** | `row['ref'] = nom_fitxa_map.get(ident) or row['abbreviation']` | `fitting/graded_spec_views.py:176` | ✅ |
| **Import (matching)** | **NO llegeix `nom_fitxa`** — v. Q-final | `models_app/extraction_views.py:3379` | — |
| **Catàleg / wizard / S2·S4·S8·S10** | cadena B (`codi_de`/`abreviatura_de`) | `pom/serializers.py:153,165,711,723,788,800` · `pom/s4_views.py:262` · `pom/s8_views.py:35` · `pom/s10_views.py:30` · `pom/s2_serializers.py:127` | ❌ (i és correcte: són nivell catàleg) |

### Lectura

La cobertura de lectura **ja és pràcticament completa** a les superfícies de model. Els fallbacks
NO són homogenis (`pom.pom_code` en tres llocs, `row['abbreviation']` a l'escalat, la cascada
llarga al front), però tots tenen `nom_fitxa` al davant, que és el que la llei demana.

---

## Q3 · EL CAMP BESSÓ EXISTEIX?

### Fet: sí, i és més antic que el del nom

`backend/fhort/models_app/models.py:748`:

```python
nom_fitxa = models.CharField(
    max_length=20, blank=True, default='',
    help_text='Nomenclatura de la fletxa al croquis (ex: A, 1, CH). '
              'Per defecte: abbreviation del POMGlobal.')
```

El propi docstring del bateig (`models.py:783-786`) el declara com la **segona** de tres
aplicacions del mateix patró canònic+bateig:

> 2. `nom_fitxa` (S14-A, just aquí a sobre): **codi canònic del POM + nomenclatura curta que el
>    model escriu al croquis**;
> 3. aquests dos camps: nom del catàleg + nom que el model (i el seu client) fa servir.

I la llei de no-contaminació ja hi és escrita (`models.py:787-789`): *«El catàleg NO es toca mai
des d'aquí: rebatejar una mesura d'un model no pot reescriure com l'anomenen els altres 900
models de la casa.»*

**Mateixa fila, mateixa identitat que el nom.** Hi ha un bessó a la banda de plantilla —
`ItemBaseMeasurement.nom_fitxa`, `backend/fhort/pom/models.py:1459`, declarat *«còpia LITERAL de
BaseMeasurement.nom_fitxa»* — que **no és** el del model i no entra en aquest abast.

### Lectura

Q3 no té resposta de disseny perquè no hi ha res a dissenyar: **la llar natural ja està
habitada**. El deute anotat a `pom/models.py:1458` (*«renombrar nom_fitxa→anglès a les DUES
taules»*) és cosmètic i aliè a la Decisió 7.

---

## Q4 · ELS LECTORS I EL RADI

### Fet: lectors de nivell model (llegirien l'override automàticament)

Tots els de la taula de Q2 marcats ✅ — **ja el llegeixen avui**. No caldria tocar-los.

Al front, els fitxers que citen `nom_fitxa`: `EditableTable.jsx` · `TechSheetEditor.jsx` ·
`FittingPrintSheet.jsx` · `FittingDetail.jsx` · `GraduacioSuperficie.jsx` ·
`MeasurementBaseGrid.jsx` · `ModelPomList.jsx` · `ImportWizard.jsx` ·
`components/model/fittingGridAdapter.jsx` · `components/model/measureSources.jsx` ·
`utils/taulesQ8.js:341`.

### Fet: ¿hi ha un `_nom_resolt()` equivalent per al codi?

**Al front, sí i ja porta el model:** `nomenclaturaPom.js:33` `nomenclaturaDePom()`. És
literalment el patró de la tanda 1 —`extraction_views.py:1152` `_nom_resolt(pom)`— aplicat al codi.

**Al backend, sí però NO porta el model:** `pom/nomenclatura.py:270` `codi_de(pom, alias)` i
`:284` `abreviatura_de(pom, alias)`. La signatura rep un `pom`; el `nom_fitxa` viu a la
`BaseMeasurement`, i **cap dels dos el podria llegir sense canviar-los la signatura**.

### Lectura

El radi de lectura és **petit** perquè la feina ja es va fer. Si mai es volgués que la cadena B
també conegués el model, seria una signatura nova (`codi_de(pom, alias, bm=None)`) i **23 punts de
crida** a re-visitar (`grep -rn 'codi_de(\|abreviatura_de(' backend/fhort --include=*.py`, exclosos
la definició i els tests; els de model són a la taula de Q2). ⚠️ **No fa falta per a la Decisió 7**: cap superfície de model
passa per la cadena B per pintar el codi.

---

## Q5 · UNICITAT I COL·LISIONS

### Fets

1. **La unique de la taula és d'IDENTITAT, no de nomenclatura**:
   `models_app/models.py:220` → `unique_together = [('model','pom','capa','instancia','garment')]`.
2. **Sobre `nom_fitxa` NO hi ha cap UNIQUE**, a cap àmbit. L'única constraint que l'esmenta és un
   **CHECK**: `models_app/migrations/0074_instancia_unicitats_comportes.py:75` →
   `models_app_basemeasurement_instancia_exigeix_nom` (*una fila amb `instancia` no buida ha de
   tenir `nom_fitxa` no buit*). Es declara viva a `pom/identity_views.py:128-129`.
3. **El front ja proposa codis per evitar xocs, sense fer-los complir**: `EditableTable.jsx:610,
   720, 1605` (`codiBase` / `codiProposat`) i la proposta visible a `:1665`.
4. 🚨 **La fitxa tècnica ja ASSUMEIX la unicitat que ningú garanteix.** `TechSheetEditor.jsx:6046-6047`:
   *«hi ha un text amb aquell `nom_fitxa`. És exacte per al cas real (els nom_fitxa són curts i
   únics dins un model) i no obliga a inventar cap binding.»*
5. **`colisio_de_codi` és d'un ALTRE nivell**: `pom/nomenclatura.py:109`
   `colisio_de_codi(customer_id, codi, excloent_pom_id)` — vigila el **catàleg del CLIENT**
   (`CustomerPOMAlias`), no les files d'un model. Cridat des de `models_app/views.py:2498` i
   `pom/wizard_views.py:862`.

### Lectura — què hi ha i què hi falta

- **Hi ha:** un CHECK que obliga a *tenir* nomenclatura quan hi ha instància; una proposta
  automàtica al front; un guard de col·lisió **un nivell amunt** (client).
- **Falta:** qualsevol comprovació que dues files del **mateix model** (o de la mateixa peça) no
  comparteixin `nom_fitxa`. Ni constraint, ni serializer, ni servei.
- 🚨 **I la falta ja té conseqüència construïda**: el binding de la fitxa tècnica (fet 4) resol
  per *text del croquis*. Dues files amb el mateix `nom_fitxa` no donen error enlloc — donen una
  fletxa lligada a la fila equivocada, en silenci.
- Els tres llocs on es podria fer complir són els tres que existeixen al projecte i no en falta
  cap: **constraint** (com la `0074`), **`validate()` del serializer** (`serializers.py`, on ja
  viu la validació de la clau única a `models_app/serializers.py:518+`), o **servei**. *No es
  proposa cap dels tres aquí.*

---

## Q6 · ABAST PEÇA vs MODEL

**Resposta curta: la pregunta és trivial — l'abast per peça surt sol.**

El fet que ho sustenta: `models_app/models.py:220`, `unique_together = [('model','pom','capa',
'instancia','garment')]`. **El `garment` ja és part de la identitat de la fila** (SET-2/T2), i el
llapis i el `NomenInput` escriuen **per `bm_id`**, és a dir sobre *una* fila. Una fila ÉS d'una
peça. No cal afegir `garment` a cap clau ni a cap payload: escriure `nom_fitxa` en una fila ja
és, per construcció, escriure'l per a aquella peça.

---

## TANCAMENT · VEREDICTE PER PREGUNTA

| | veredicte |
|---|---|
| **Q1** | El llapis edita **només el nom** (`nom_canonic_model`/`nom_traduit_model`) per `PATCH …/noms/`. La nomenclatura ja s'edita, però per un **control i un endpoint diferents** (`NomenInput` → PATCH genèric del viewset). |
| **Q2** | Dues cadenes. La del **front** (`nomenclaturaDePom`) ja posa `nom_fitxa` **primer**; la del **backend** (`codi_de`) **no té nivell de model** i serveix el catàleg. Totes les superfícies de model ja veuen l'override. |
| **Q3** | **El camp bessó existeix des d'S14-A**: `BaseMeasurement.nom_fitxa`, mateixa fila i mateixa identitat que el nom. No cal camp nou. |
| **Q4** | Radi de lectura **≈ zero**: els lectors ja el llegeixen. Hi ha `_nom_resolt()` equivalent al front (`nomenclaturaDePom`) i **no** al backend. |
| **Q5** | **Cap unicitat, a cap nivell.** Només un CHECK que exigeix *tenir* nomenclatura amb instància. `colisio_de_codi` és del catàleg de client, un nivell amunt. |
| **Q6** | **Trivial**: `garment` ja és a la clau de la fila; escriure per `bm_id` ja és per peça. |

## RADI DEL FIX (no s'implementa)

**Fitxers que la Decisió 7 tocaria**

- `backend/fhort/models_app/views.py:4090` — `NOMS_POM_CAMPS` (afegir-hi `nom_fitxa`) i `:4133`
  (el tope de 160 no val: la columna és `max_length=20`, `models.py:749`).
- `backend/fhort/models_app/views.py:4147` — el cos de resposta.
- `frontend/src/components/EditableTable/EditableTable.jsx:1272` i `:1355` — unificar les dues
  portes darrere el llapis, si es vol una sola.
- On es decideixi fer complir la unicitat: `models_app/serializers.py` (`validate()`) o una
  migració de constraint a `models_app/migrations/`.

**Endpoints**

- `PATCH /api/v1/base-measurements/<id>/noms/` (`views.py:4095`).
- `PATCH /api/v1/base-measurements/<id>/` (viewset genèric) — la porta que `nom_fitxa` fa servir avui.

**Tests que ja cobreixen la zona**

- `backend/fhort/models_app/test_f_formacio_1.py:127-137` — `_nom_resolt`, el patró de la tanda 1.
- `backend/fhort/fitting/test_f7_identitat_linia_garment.py` (tot) — 🔑 el més valuós: prova que
  `nom_fitxa` **distingeix la fila per peça** (bm 3344 `G1` mare vs bm 3354 `M1` peça 02) i que
  el bug de col·lapse ja es va patir un cop.
- `backend/fhort/patterns/tests.py:4609-4645` — `nom_fitxa` a la resposta de la graella.
- `frontend/src/utils/nomenclaturaPom.test.js:20-52` — la cascada de resolució, cas per cas.
- `backend/fhort/models_app/test_desat_fitxa_poda.py` — la poda del desat de fitxa.

---

## RISCOS · EL QUE PASSA AVUI (lectura, no opinió)

### 🚨 RISC 1 — L'IMPORT ESBORRA L'OVERRIDE. I no és el risc que el brief temia.

`backend/fhort/models_app/extraction_views.py:3385` (dins el bloc `_defaults`, obert a `:3382`):

```python
_defaults = {
    'base_value_cm': base_val,
    'nom_fitxa': p.get('codi_fitxa') or '',      # ← el codi DEL DOCUMENT
    ...
```

…i aquests `_defaults` van a un **`update_or_create`** (`extraction_views.py:3417`) la clau del
qual és `(model, pom, capa, instancia, garment)` — **`nom_fitxa` és als DEFAULTS, no a la clau**.

**Conseqüència, avui:** si el tècnic posa una nomenclatura pròpia a una fila i **després es torna
a importar el document del client**, l'override queda **substituït pel `codi_fitxa` del document**,
sense avís i sense entrada al `MeasurementChangeLog` (que només registra `base_value_cm`,
`views.py:4116`).

⚠️ **L'única fila que se salva** és la que el tècnic hagi marcat com a valor manual respectat
(`extraction_views.py:3373`, branca `respectats_idents`; el conjunt es construeix a `:3202`), que fa `continue` abans dels `_defaults`.

### ✅ RISC 2 — El matching NO es trenca. Mesurat.

La pregunta del brief era: *si l'override canvia el codi, el document del client encara casa?*

**Sí.** El matching del document **no llegeix `nom_fitxa` en cap moment**. Va del `codi_fitxa` del
document al **POM** per la via del catàleg de client (`maybe_learn_customer_alias`,
`extraction_views.py:3379`; resolutor invers `pom/nomenclatura.py:99` `pom_del_codi`), i un
cop té el POM, la fila es troba per la **clau d'identitat**, no pel codi. Canviar `nom_fitxa` és
invisible per al matcher.

🔑 El perill real és el simètric del que es temia: **el document no deixa de trobar la fila —
la troba i li reescriu el codi.**

### 🚩 RISC 3 — El PDF ja fa el que ha de fer, però hereta la manca d'unicitat.

La fitxa tècnica i el seu PDF llegeixen per `nomenclaturaDePom` (`TechSheetEditor.jsx:5292`), o
sigui que **un override es veuria immediatament al paper** — que és el que la llei vol.

El que hereta és el fet 4 de Q5: el binding fletxa↔fila es resol **pel text** del `nom_fitxa`
(`TechSheetEditor.jsx:6046-6047`), amb la unicitat com a **supòsit declarat i no garantit**. Obrir
l'edició de la nomenclatura sense unicitat fa que el supòsit sigui més fàcil de trencar del que és
avui, perquè avui el valor el sembra l'import (i el document del client rarament repeteix codi) i
demà el sembraria una persona.

### Nota de frontera

`tech_sheet_views.py:376` també escriu `nom_fitxa`, però amb **`get_or_create`**
(`tech_sheet_views.py:367`): només el posa en **crear** la fila. No trepitja overrides.
