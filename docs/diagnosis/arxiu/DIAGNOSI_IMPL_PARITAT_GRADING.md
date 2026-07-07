> ⚠️ SUPERADA 2026-07-07 — implementada (6 peces paritat grading; helper bump_grading_version_and_generate; 66161e2/423853a/96e7fc8/b495442). Consulta només com a històric.

# DIAGNOSI PER A IMPLEMENTACIÓ — PARITAT GRADING (les 6 peces)

**Patró A · read-only · branca `dev` · 2026-06-24**
Entorn: `/var/www/ftt-staging` (backend Django + frontend React). Dades schema **`fhort`** (verificat:
`{fhort,public}`, clients `(1,public),(2,fhort)`, **no id=6**). `venv/bin/python` sempre. Cap fitxer tocat.

**Mandat:** tornar el **COM exacte** de cada peça (on tocar, què reusar, què trencaria, migració/dada,
ordre de dependència) per implementar el flux **Mesures (base) → PROPAGAR conscient (crea VERSIÓ NOVA,
repetible) → Grading (totes les talles, tasca+temps)**. Cada propagació = versió nova; l'anterior queda
d'històric. Segellat (`aprovada`) a part, lligat a `advance_phase_gate`. **NO s'implementa res.**

> **Titular:** la infraestructura hi és quasi tota. El **cor** és la Peça 1 (fer v+1 conscient sense
> trencar el motor compartit) → solució neta = **extreure un helper `bump_grading_version_and_generate`**
> que ja existeix inline a `close_piece_fitting`, i cridar-lo des de l'acte conscient; **els altres 6
> callers de `generate_graded_specs` no es toquen**. **Cap migració d'esquema.** Grading **ja és tasca
> amb temps** (`scaling`). El flag "Mesures tancat" i els watchpoints **ja existeixen**. El que falta és
> **fontanteria** (botó + endpoint param + alimentar la graella amb l'historial).

---

## PEÇA 1 (la gran) — VERSIONAT v+1 A GRADING

### 1A · El bloc que crea v+1 (a extreure com a helper)
[`fitting/services.py:428-478`](../../backend/fhort/fitting/services.py#L428) (dins `close_piece_fitting`,
`if changed:`): guard D-1 (`:430-445`) → **desactiva totes les actives** (`:448`) → `max+1` (`:449-451`)
→ `GradingVersion.objects.create(...)` (`:452-459`) → `measurements_version++` si `base_changed`
(`:462-465`) → `generate_graded_specs(sf.pk)` (`:469`) → brain stub (`:471-478`). **No** té
`@transaction.atomic` propi (el posa el caller/vista). El **mirall** és `resolve_size_check`
([`services_size_check.py:191-231`](../../backend/fhort/models_app/services_size_check.py#L191)), idèntic.

### 1B · Per què el motor reutilitza, i qui espera què
[`_get_or_create_grading_version`](../../backend/fhort/pom/services.py#L427) (`pom/services.py:427-460`):
`filter(size_fitting=sf, is_active=True).last()`; **només crea si `None`**. El criden **tots** els
callers de `generate_graded_specs` (via `:78`). Classificats:

| Caller | ruta:línia | Què espera |
|---|---|---|
| `close_piece_fitting` | `fitting/services.py:469` | **crea v+1 ABANS**, motor reutilitza la nova |
| `resolve_size_check` | `services_size_check.py:230` | **crea v+1 ABANS**, motor reutilitza la nova |
| `generate_grading_view` | `models_app/views.py:1175` | **reutilitza** vigent (o crea la 1a) |
| `set_size_override_view` | `models_app/views.py:1321` | **reutilitza** (edició dins versió) |
| `regenerate`/`close_base` | `pom/grading_views.py:37`, `pom/services.py:280` | **reutilitza** |
| `confirm_base_size` (wizard) | `pom/wizard_views.py:269` | **reutilitza** (crea 1a en import) |
| `clone_model_for_qa` | `clone_model_for_qa.py:111` | crea v1 a part, reutilitza |

⇒ **Només 2 camins creen v+1** (fitting, size_check). La resta **reutilitza i NO s'ha de tocar**.

### 1C · La decisió de disseny (cor) — opcions mapejades
- **(i) flag a `generate_grading_view`/`generate_graded_specs` (`force_new_version`)** — caldria moure el
  guard D-1 + creació dins el motor; risc de duplicar lògica i de tocar un punt que comparteixen 8 callers.
- **(ii) ⭐ nou servei `bump_grading_version_and_generate(sf_id, profile, allow_reopen_sealed, nom, notes)`**
  a `pom/services.py`: guard D-1 + desactiva + `max+1` + create + `generate_graded_specs`. El criden
  **només** els camins conscients (fitting, size_check i el **nou propagar**). Els altres 6 segueixen
  cridant `generate_graded_specs` directe. **És DRY** (el bloc ja existeix a `:448-459`), centralitza el
  guard D-1 i **no trenca cap reutilitzador**.
- **(iii) `force_new` a `_get_or_create_grading_version`** — funciona però encadena paràmetres
  (`force_new`/`nom`/`notes`) a través de `generate_graded_specs`; embruta la firma del motor compartit.

**Recomanació (a validar nosaltres): opció (ii).** `close_piece_fitting` i `resolve_size_check` es
**refactoritzen** per cridar el helper (elimina la duplicació actual entre tots dos); l'**acte conscient**
(Peça 2) crida el mateix helper. Risc: cap caller de reutilització canvia.

### 1D · Migració i poblat — CAP canvi d'esquema
`GradedSpec.grading_version` és **FK per-versió** (`unique_together=(grading_version,pom,size_label)`,
[`fitting/models.py:191`](../../backend/fhort/fitting/models.py#L191)) ⇒ una v+1 neix **buida** i
`generate_graded_specs` la pobla. `GradedSpec.generated_from_version` (`models.py:184`) **ja existeix**
(staleness; el motor el posa). **No cal camp nou ni migració.** `measurements_version` (Model) s'incrementa
avui **només en canvi de base** (`fitting/services.py:462`, `services_size_check.py:227`).
**Pregunta de disseny (no decidir):** el propagar conscient *sense* canvi de base ¿ha d'incrementar
`measurements_version`? Probablement **no** (és comptador de base; el comptador de propagació és
`GradingVersion.version_number`). El helper hauria de rebre `base_changed` i decidir-ho al caller.

---

## PEÇA 2 — LLAR DEL "PROPAGAR CONSCIENT"

### 2A · L'endpoint existent
[`generate_grading_view`](../../backend/fhort/models_app/views.py#L1135) (`views.py:1135-1220`,
`@api_view(['POST'])`, `IsAuthenticated`, ruta `models/<id>/generar-grading/` a `urls.py:177`): body buit;
obté/crea `SizeFitting`; crida `generate_graded_specs(sf.id)` (`:1175`); retorna `{graded_count, rows,
size_run, base_size}`. **Per disparar v+1:** afegir param (body `{new_version:true}`) que faci cridar el
helper de 1C en lloc de `generate_graded_specs` directe. **Avui no crea v+1** (reutilitza vigent).

### 2B · On va el botó (i confirmació que està orfe)
- L'endpoint **no el crida cap component** (verificat: única menció = comentari
  [`ModelMeasurements.jsx:89-90`](../../frontend/src/pages/ModelMeasurements.jsx#L89)). No va quedar a
  Escalat. `endpoints.js` **no té** `models.generarGrading` → cal afegir-la.
- **Lloc natural del botó:** [`PropagatedEditor.jsx`](../../frontend/src/pages/PropagatedEditor.jsx)
  (editor d'Escalat editable, ruta `/escalat?task_id=`), a la barra d'accions, al costat de
  `setPomRegim`/`setSizeOverride`. Quan `readOnly=false`.

### 2C · UX conscient — components a reusar
- Modal genèric [`components/ui/Modal.jsx`](../../frontend/src/components/ui/Modal.jsx) (title/subtitle/
  confirm/cancel) per a "això crea la versió vX i et porta a treballar les talles".
- Patró de decisió conscient ja existent: `gradingConflict` a
  [`ImportWizard.jsx:457`](../../frontend/src/components/ImportWizard/ImportWizard.jsx#L457) (banner
  d'opcions). Reusar el patró, no el copy. **Tot reús; res nou de component.**

---

## PEÇA 3 — GRADING TASCA+TEMPS + PRESA SOBRE TALLES

### 3A · Grading JA és tasca amb temps (CONFIRMAT — corregeix sospita)
Catàleg `TaskType` (schema `fhort`) conté **`scaling`** ("Escalat CAD", **15 ModelTask**) — i `/escalat
?task_id=` l'obre via `scaling` ([`WorkPlan.jsx:31`](../../frontend/src/components/model/WorkPlan.jsx#L31),
[`KanbanTasks.jsx:615`](../../frontend/src/pages/KanbanTasks.jsx#L615),
[`ModelSheet.jsx:247`](../../frontend/src/pages/ModelSheet.jsx#L247)). El temps es compta:
`transition_task` ([`tasks/services_c.py:43`](../../backend/fhort/tasks/services_c.py#L43)) →
`started_at`/`finished_at` + `TimerEntrada` (`:20`) + Welford `record_actual_time` (`:125`).
⇒ **Grading ja és tasca amb temps; no cal construir-ho.**
⚠️ **Ambigüitat a netejar:** existeix també `TaskType code='grading'` ("Escalat", **1 ModelTask**),
*duplicat* del concepte d'escalat però **no** és el que obre `/escalat`. Decidir si es jubila/funde amb
`scaling` (no bloqueja les peces grans, però cal aclarir-ho per no obrir la tasca equivocada).

### 3B · "Presa" = versió a PROPAGAR; edició de talles = dins la versió
Dos mecanismes vius: (a) **crea versió** → `close_piece_fitting`/`resolve_size_check` (canvi de base);
(b) **edita dins la versió vigent** → `set_size_override_view` (`views.py:1227`, NO versiona, re-propaga).
Alineat amb l'arquitectura: **la versió es crea a l'acte PROPAGAR** (Peça 1/2); la *presa de mesures sobre
talles* (ajustos) viu **dins** la versió activa via override. No cal que cada edició versioni.

### 3C · GAP: no hi ha "valor real mesurat" per talla no-base
[`ModelGradingOverride`](../../backend/fhort/models_app/models.py#L587) (`models.py:587-620`): `value_cm`
és **ajust teòric** (`motiu`, `fitting_ref`, origen model), **no** mesura física de mostra. El
`valor_real` només existeix a `PieceFittingLine` (fitting). ⇒ Si el *size set* (mostres físiques de totes
les talles) ha de registrar **valor real per talla no-base**, **no té lloc avui**. Opcions (no decidir):
camp nou a `ModelGradingOverride`, o model nou paral·lel a `BaseMeasurement`. **GAP de domini, no
bloquejant** de les 5 grans; cal decisió abans de portar el size-set real fora del fitting.

---

## PEÇA 4 — EIX DE VERSIONS A LA GRAELLA

### 4A/4C · `MeasureGrid` JA suporta l'eix de versions (REÚS pur)
[`fittingGridAdapter.jsx`](../../frontend/src/components/model/fittingGridAdapter.jsx): `buildFittingGroups`
(`:15-25`) genera `historyCols` per versió (`v1`=Base, `v2`=Fit 1…) + `activeLabel`; `buildFittingRows`
(`:30-52`) omple `cells[talla] = {history:{vN:valor}, active:{lineId,value}}` des de `line.evolucio[]`.
[`MeasureGrid.jsx`](../../frontend/src/components/model/MeasureGrid.jsx) (`:234-283`) pinta **N
`historyCols` + activa** → **ja suporta versions** (s'usa al fitting). **Feina = alimentar-lo, NO
modificar-lo.**

### 4B · El que falta a Escalat (dada + endpoint)
`PropagatedEditor` alimenta avui amb `buildEscalatGroups`/`buildEscalatRows` (1 sola columna `vigent`) des
de `taula-mesures` ([`views.py:626`](../../backend/fhort/models_app/views.py#L626)). Per a l'eix de
versions cal **historial GradingVersion + GradedSpec per model**. **No existeix endpoint que el torni
agregat:** hi ha `GradingVersionViewSet` (`/grading-versions/`, llista lleugera, sense specs) i
`taula-mesures` (1 versió). ⇒ **NOU** (read-only, només identificat): un endpoint
`models/<id>/grading-history/` (o ampliar `taula-mesures` amb `grading_versions[]` + `graded_by_version`)
i una variant `buildEscalatRowsWithVersions`. **Reús:** `MeasureGrid` + adapter base; **Nou:** endpoint
d'historial + builder amb versions.

---

## PEÇA 5 — "TANCAR MESURES" (senyal + watchpoint)

### 5A · El flag JA existeix
`SizeFitting.estat` inclou **`'Tancat'`** (i `BaseTancada`, `TallesGenerades`) —
[`fitting/models.py:15-20`](../../backend/fhort/fitting/models.py#L15). El posa la funció de tancament de
taula a [`pom/services.py:246-290`](../../backend/fhort/pom/services.py#L246) (`estat='Tancat',
base_tancada=True`). El llegeix `measurements_table_view`
([`views.py:732`](../../backend/fhort/models_app/views.py#L732)) → retorna `tancat` → frontend read-only.
⇒ **Senyal "Mesures tancat" ja modelat i no bloquejant** (només commuta a read-only; reobrir = tornar
l'estat enrere).

### 5B · Watchpoint — CRUD complet ja existeix
[`Watchpoint`](../../backend/fhort/models_app/models.py#L857) (`models.py:857-883`: `model`, `task`,
`text`, `estat` open/resolved, traça). ViewSet `views.py:86-117` (`POST /watchpoints/`, `resolve/`,
`reopen/`); `endpoints.js` `watchpoints.{list,create,resolve,reopen}`. **Creable des de backend i
frontend.** Vehicle d'avís llest.

### 5C · On viu la comprovació de reobertura amb risc
El punt natural és allà on ja es detecta el risc de segellat: guard D-1 a
[`fitting/services.py:430-440`](../../backend/fhort/fitting/services.py#L430) (i el mirall a
`services_size_check.py:199`). En reobrir Mesures (tornar `SizeFitting.estat` de `Tancat`) o en superar
una versió aprovada amb `allow_reopen_sealed`, **crear un `Watchpoint` informatiu** (no bloca). Lloc:
dins el helper de Peça 1 (centralitza el guard) o al servei de reobertura de Mesures.

---

## PEÇA 6 — SITUAR (parcials)

### 6A · 1D — propagar LINEAR a germanes (PARCIAL)
[`PieceFittingLineViewSet.propagar`](../../backend/fhort/fitting/views.py#L483) (`fitting/views.py:483-546`):
desa l'àncora i, si la regla és LINEAR/canònica (no STEP), crida `propaga_ancoratges`
([`pom/grading_utils.py:546`](../../backend/fhort/pom/grading_utils.py#L546)) per propagar el delta a les
talles germanes. **Per replicar a Escalat:** nova acció sobre `ModelGradingOverride` que reusi
`propaga_ancoratges` (motor PUR ja existent). **PARCIAL — després de les 5 grans.**

### 6B · 1G — gate i fotos (DECISIÓ A PART)
`set_piece_gate` ([`fitting/services.py:594`](../../backend/fhort/fitting/services.py#L594), OK/NO_OK/
EXCEPCIO) i `FittingPhoto` **no tenen llar a Grading**. Destí probable: **watchpoint** per a gate=NO_OK,
**Fitxers** per a fotos. **Aparcables sense bloquejar** les 5 grans.

---

## TRANSVERSAL

### T1 · Risc de dades (ids concrets) — essencialment NUL
| Sessió Oberta | Model | Peces | Línies divergents |
|---|---|---|---|
| **138** | 185 | 1 (`piece_fitting=18`) | 0 |
| **120** | 165 | 0 | 0 |

Les **8 línies amb `valor_real` divergent** són **totes en sessions TANCADES** (sessió 13/model162: 1;
136/model182: 4; 137/model182: 3) → **ja propagades** (van passar per `close_piece_fitting`). Les 2
Obertes **no tenen dades divergents**. ⇒ **Cap pèrdua real.** Acció de neteja recomanada abans de jubilar:
**tancar o descartar les sessions 138 i 120** (138 té 1 peça sense divergència; 120 és buida) — read-only:
només identificades, no tocades.

### T2 · Ordre de dependència (seqüència de commits proposada)
1. **Peça 1 (backend)** — helper `bump_grading_version_and_generate` + refactor de `close_piece_fitting`
   i `resolve_size_check`. *Prerequisit de tot.* (no UI)
2. **Peça 2 (backend+frontend)** — param `new_version` a `generate_grading_view` (crida el helper) +
   `endpoints.js.generarGrading` + botó a `PropagatedEditor` + Modal. *Depèn de 1.*
3. **Peça 5 (backend, petit)** — watchpoint informatiu en reobrir/superar segellat (reusa Watchpoint).
   *Depèn de 1 (mateix punt de guard).*
4. **Peça 4 (backend+frontend)** — endpoint d'historial + `buildEscalatRowsWithVersions` (alimenta
   `MeasureGrid`). *Depèn de 1 (necessita v+1 reals per mostrar història).*
5. **Peça 3** — aclarir `scaling` vs `grading` (catàleg) i decidir GAP 3C (valor real per talla). *Decisió
   abans del size-set real; la tasca+temps ja existeix.*
6. **Peça 6 (1D, 1G)** — parcials, després de les 5.

### T3 · Frontera paritat-ara vs zoom-out-després
- **Paritat-ara (amb ModelSheet/Escalat actuals):** Peça 1, Peça 2, Peça 5, Peça 4. Totes viuen sobre
  `/escalat` (tasca `scaling`, ja amb temps) i ModelSheet existents — **no necessiten el Pla de treball
  intern reconstruït**.
- **Zoom-out-després:** Peça 3 (size-set real per talla = GAP 3C, nova superfície de presa) i Peça 6
  (1D/1G) encaixen amb la reconstrucció del Pla de treball intern; **no bloquegen** la jubilació de la
  pantalla-fitting un cop fetes 1/2/4/5.

---

## VEREDICTE

- **Peça 1 (v+1):** tocar `pom/services.py` (nou `bump_grading_version_and_generate`, reusa el bloc de
  `fitting/services.py:448-465`) + refactor `close_piece_fitting:428-478` i `services_size_check.py:191-231`.
  **Reusar** el guard D-1 i la creació existents; **no tocar** els 6 callers de reutilització de
  `generate_graded_specs`. **Trencaria** si es posés `force_new` dins `_get_or_create_grading_version`
  (afecta 8 callers) → evitar. **Migració: CAP** (FK per-versió, `generated_from_version` ja hi és).
  **Backend.** Dimensió: petita-mitjana (~1 helper + 2 refactors aprimadors).
- **Peça 2 (botó conscient):** `generate_grading_view:1135` (+param `new_version`→helper) +
  `endpoints.js` (`generarGrading`) + `PropagatedEditor.jsx` (botó + `handlePropagar` + `Modal`).
  **Reusar** Modal + patró conscient d'ImportWizard. **Backend+frontend.** Dimensió: petita.
- **Peça 3 (tasca+temps / presa):** **ja feta** (tasca `scaling` amb temps, confirmat). **Reusar** tot.
  Pendent: aclarir duplicat `grading` al catàleg i el **GAP 3C** (valor real per talla no-base — sense
  llar avui). **Decisió de domini**, no codi immediat.
- **Peça 4 (eix de versions):** **reusar** `MeasureGrid` (ja suporta versions) + adapter; **nou** endpoint
  d'historial GradingVersion+GradedSpec (no existeix agregat) + `buildEscalatRowsWithVersions`.
  **Backend+frontend.** Dimensió: mitjana.
- **Peça 5 (Tancar Mesures + avís):** **tot reusable** — flag `SizeFitting.estat='Tancat'`
  (`fitting/models.py:20`, escrit a `pom/services.py:246`, llegit a `views.py:732`) + Watchpoint CRUD
  complet. **Nou:** crear el watchpoint en reobrir (al punt de guard D-1). **Backend (petit).**
- **Peça 6 (1D/1G):** 1D = reusar `propaga_ancoratges` sobre `ModelGradingOverride` (PARCIAL); 1G =
  watchpoint/Fitxers (decisió a part). **Després de les 5.**

**El cor (Peça 1):** opció (ii) — un helper que envolta la creació de v+1 (ja existent inline) + el motor;
els reutilitzadors no es toquen perquè segueixen cridant `generate_graded_specs` directe, que reutilitza
la versió que el helper acaba de crear. **Cap migració.**

**Ordre de commits:** 1 → 2 → 5 → 4 → (3 decisió) → 6. **Paritat-ara:** 1,2,4,5 (sobre Escalat/ModelSheet
actuals). **Zoom-out-després:** 3 (size-set real) i 6.

**Risc de dades T1:** NUL real (8 línies divergents ja en sessions tancades/propagades). Neteja prèvia:
tancar/descartar sessions **138** (model 185) i **120** (model 165).

*Fi de la diagnosi. No s'ha implementat res. Atura't aquí.*
