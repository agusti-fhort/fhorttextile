# DIAGNOSI MOTOR — FRONTERES A (segellat) i B (propagar-conscient) + PANTALLES

**Patró A · read-only · branca `dev` · 2026-06-24**
Entorn: `/var/www/ftt-staging` (backend Django + frontend React). Dades al schema `fhort`.
Mètode: ancoratge per **ruta:línia de codi real** (els D-números i les línies del prompt han derivat
entre sessions; aquí es corregeixen). Cap fitxer modificat.

> ⚠️ **CORRECCIÓ DE PREMISSA (llegir abans que res).** El prompt descriu les dues fronteres com a
> *forats a dissenyar/omplir*. La inspecció del codi real diu una altra cosa: **les dues ja estan
> parcialment construïdes.** La Frontera A (guard de segellat) **JA EXISTEIX i és completa** als dos
> camins (no és un forat: és un *audit*). La Frontera B (propagar-conscient) té **l'acte conscient ja
> construït** (endpoint `generar-grading` + botó pla retirat de Mesures, D-10) i **només queda
> desacoblar una crida d'auto-propagació residual** al camí del size check. Tot el detall, sota.

---

## BLOC 1 — FRONTERA A: GUARD DE SEGELLAT

### 1A · `close_piece_fitting` — el guard JA HI ÉS
**Ruta:** [`fhort/fitting/services.py`](../../backend/fhort/fitting/services.py) · funció `close_piece_fitting`
(la creació de v+1 és a **:452-459**, dins del bloc `if changed:` que obre a **:429**).

El tram que crea la GradingVersion v+1 **està precedit pel guard "D-1"** (`:430-445`):

```python
428  new_version_number = None
429  if changed:
430      # D-1 guard: no superar silenciosament una GradingVersion ja segellada a
431      # producció (aprovada=True). Un canvi tardà ha de ser una reobertura EXPLÍCITA
432      # i registrada (allow_reopen_sealed=True), per disseny §3.1.
433      sealed_active = (GradingVersion.objects
434                       .filter(size_fitting=sf, is_active=True, aprovada=True)
435                       .order_by('-version_number').first())
436      if sealed_active is not None and not allow_reopen_sealed:
437          raise ValueError("GradingVersion v… està aprovada (segellada a producció); "
438                           "cal reobertura explícita per superar-la.")
...
446      # Functional versioning: deactivate ALL active versions (handles the
447      # legacy multi-active anomaly), then create the new active one.
448      GradingVersion.objects.filter(size_fitting=sf, is_active=True).update(is_active=False)
```

- **Comprova `aprovada` abans de superar la versió vigent?** SÍ — `:433-436`. Si hi ha una versió
  `is_active=True, aprovada=True` i `allow_reopen_sealed` és fals (per defecte), **llança `ValueError`**.
- **On caldria el guard si no hi fos?** Just a `:429` (entrada del bloc `if changed:`), abans del
  `update(is_active=False)` de `:448`. **Ja és exactament on és.**
- **Comentari "legacy multi-active anomaly"** (`:446-447`, literal a dalt): documenta que el codi
  desactiva **TOTES** les versions actives abans de crear la nova, per reparar una invariant violada
  històricament (diversos `is_active=True` alhora). És defensa preventiva; vegeu 1E — avui no es manifesta.

### 1B · `resolve_size_check` — camí espill amb el MATEIX guard
**Ruta:** [`fhort/models_app/services_size_check.py`](../../backend/fhort/models_app/services_size_check.py)
· funció `resolve_size_check`. El camí espill que crea v+1 + incrementa `measurements_version` +
crida `generate_graded_specs` és a **:191-231**, dins `if base_changed and te_deltes:`.

Guard idèntic a **:199-208** (mateixa forma, mateix `allow_reopen_sealed`):

```python
199  # D-1 guard (mirror de close_piece_fitting): no superar una GradingVersion
200  # aprovada (segellada a producció) sense reobertura explícita registrada.
201  sealed_active = (GradingVersion.objects
202                   .filter(size_fitting=sf, is_active=True, aprovada=True)
203                   .order_by('-version_number').first())
204  if sealed_active is not None and not allow_reopen_sealed:
205      raise ValueError(…)
```

- **Mateix forat tapat als DOS llocs:** confirmat. Són els dos únics camins que muten base → v+1.
- **Tercer camí?** `grep "GradingVersion.objects.create"` → **només dos** (`services.py:452`,
  `services_size_check.py:218`). `generate_grading_view` (1135, vegeu 2B) **NO crea GradingVersion**;
  només omple `GradedSpec` sobre la versió vigent. ⇒ **No hi ha tercer escriptor de v+1.**

### 1C · Únic escriptor de `aprovada=True`, lligat al GATE
`grep "aprovada = True"` → **un sol punt real:** `seal_model_grading`
([`services.py:579`](../../backend/fhort/fitting/services.py#L579)):

```python
563  def seal_model_grading(model, *, user_profile_id=None, now=None):
579      version.aprovada = True
580      version.aprovada_per_id = user_profile_id
581      version.data_aprovacio = now
```

Cridat **únicament** per `advance_phase_gate`
([`fhort/tasks/services_d.py:50-51`](../../backend/fhort/tasks/services_d.py#L50)) → el segellat és
**conseqüència de l'avanç de GATE** (decisió humana de maduresa), tal com mana la llei de domini.

> 🔧 **CORRECCIÓ D'ÀNCORA.** El prompt diu «advance_phase (fitting/services.py:707-710)» com a
> escriptor de segellat. **És fals avui.** A `:708` hi ha `advance_phase` (fitting), i el seu cos de
> bucle (`:757-769`) és **buit a posta**: el comentari D-3 (`:763-769`) diu que «el segellat ja NO es
> fa en tancar la sessió de fitting». A més, el **docstring d'`advance_phase` (`:714-715`) encara DIU
> que segella** → **drift de documentació viu** (docstring stale; codi correcte). L'escriptor real és
> `seal_model_grading:579` via `advance_phase_gate`. Aquesta és l'àncora bona.

### 1D · Conseqüència del guard — vies de re-grading legítim
- `regress_phase` **existeix** ([`tasks/services_d.py:58-73`](../../backend/fhort/tasks/services_d.py#L58)):
  retrocedeix `fase_actual` + `GateEvent(kind='regress')`, però **NO toca `aprovada`** (no dessegella).
- `grep "dessegell|desaprov|aprovada = False"` → **CAP**. No hi ha dessegellament explícit.
- **Opcions (sense decidir), totes ja viables amb el codi actual:**
  - **(i) bloqueig dur + regress abans** — funciona, però `regress_phase` no dessegella ⇒ tot sol no
    desbloqueja; cal combinar-lo amb (ii).
  - **(ii) reobertura explícita** — `allow_reopen_sealed=True` **ja implementat** als dos serveis;
    registra la decisió a `GradingVersion.notes`. És la via conscient que ja existeix.
  - **(iii) dessegellar (aprovada=False)** — **no existeix**; caldria construir-lo si es vol regress
    que reverteixi el segell.

### 1E · Estat real a la BD (read-only, schema `fhort`)
> El prompt diu «tenant id=6». **No existeix:** només hi ha `Client(1, public)` i `Client(2, fhort)`.
> Les dades viuen al schema **`fhort`**. Xifres allà:

| Mètrica | Valor |
|---|---|
| `GradingVersion` total | **13** |
| `aprovada=True` | **2** |
| `is_active=True` | **4** |
| `is_active=True AND aprovada=True` (segellades vigents) | **1** |
| **Anomalia multi-activa** (>1 activa per `size_fitting`) | **CAP** |
| `SizeFitting` total | 19 |

⇒ El guard i el `update(is_active=False)` de `:448` mantenen la invariant: **avui no hi ha cap
anomalia multi-activa**. La defensa "legacy" és preventiva, no correctiva d'un estat present.

### 4A · Frontera amb G6
Ni `close_piece_fitting` ni `resolve_size_check` toquen `GradingException` ni `ModelGradingOverride`
(comentari explícit a `services_size_check.py:5-6`: «NOMÉS la base, no toca deltes/Rule/Override»).
⇒ **El guard de segellat (Frontera A) és INDEPENDENT de G6** (dual-path Exception/Override). Scopes
disjunts. Aquí no s'hi entra.

---

## BLOC 2 — FRONTERA B: PROPAGAR-CONSCIENT

### 2A · Auto-propagació residual al size check
**Punt exacte:** [`services_size_check.py:230`](../../backend/fhort/models_app/services_size_check.py#L230)
— `generate_graded_specs(sf.pk)`, dins `if base_changed and te_deltes:` (`:191`).

```python
227  Model.objects.filter(pk=model.pk).update(measurements_version=F('measurements_version') + 1)
230  generate_graded_specs(sf.pk)   # ← auto-propaga sol
```

- Salta **NOMÉS** en *accept-amb-deltes* (`base_changed and te_deltes`).
- **Reject / Descartat:** `final_estat in ('Rebutjat','Descartat')` (`:251`) → **NO entra al bloc, NO
  propaga**; la tasca queda viva i pot reagendar-se (`:251-252`).

### 2B · L'acte conscient JA existeix — `generar-grading`
**Backend:** `generate_grading_view` ([`models_app/views.py:1135`](../../backend/fhort/models_app/views.py#L1135)),
rutat a `models/<id>/generar-grading/` ([`models_app/urls.py:177`](../../backend/fhort/models_app/urls.py#L177)).
Crida `generate_graded_specs(sf.id)` (`:1175`) sobre la SizeFitting vigent. **NO crea GradingVersion
nova ni segella** — només (re)omple `GradedSpec`.

**Frontend:** [`ModelMeasurements.jsx:89-90`](../../frontend/src/pages/ModelMeasurements.jsx#L89) ho
documenta literalment:
> «P5 — "Generar grading automàtic" RETIRAT d'aquesta superfície: la propagació és conscient (D-10),
> no un botó pla. L'endpoint generar-grading es CONSERVA per a la projecció conscient.»

⇒ El **botó pla d'auto-grading ja es va treure** de Mesures (feina D-10 feta); l'endpoint conscient
es conserva. Altres superfícies de propagació relacionades:
- `set-size-override` ([`views.py:1239`](../../backend/fhort/models_app/views.py#L1239), botó de l'Escalat /
  `PropagatedEditor.jsx:45`): edita un `ModelGradingOverride` per cel·la i **re-propaga**
  (`generate_graded_specs`, `:1321`). És territori G6 (override), no la base.
- `piece-fitting-lines/<id>/propagar/` ([`endpoints.js:364`](../../frontend/src/api/endpoints.js#L364)):
  re-escalat LINEAL de talles germanes **dins** una línia de fitting.

**Matís clau:** `generar-grading` **(re)omple GradedSpec però NO crea v+1**. La creació de v+1 viu només
a `close_piece_fitting:452` i `resolve_size_check:218`. ⇒ Si es desacobla `resolve` (treure `:230`)
**conservant** la creació de v+1 (`:218`), la v+1 queda creada amb GradedSpec *stale* fins que algú
premi `generar-grading`. Si a més es tragués el bloc sencer, **ningú crearia la v+1** (generar-grading
no ho fa). Aquesta és la decisió de disseny a tancar (no es decideix aquí).

### 2C · GAP temporal del desacoblament
Si `resolve_size_check` deixa d'executar `:230`:

| Moment | `BaseMeasurement` | `measurements_version` (`:227`) | `GradedSpec` |
|---|---|---|---|
| Accept del check | **escrit** (`origen='CHECKED'`, `:180-184`) | depèn (vegeu sota) | **stale** |
| Abans de premre Propagar | escrit | — | stale |
| `generar-grading` premut | — | (no l'incrementa!) | **regenerat** |

- `measurements_version` s'incrementa **avui a `resolve` (`:227`)** i a `close_piece_fitting (:463)`;
  **`generar-grading` NO l'incrementa**. ⇒ Si es desacobla, cal decidir si `:227` es treu amb `:230`
  (i es mou a generar-grading) o es manté a resolve. Sense decisió, el comptador i el GradedSpec
  divergeixen en el GAP.
- **Estat del model entre "check acceptat" i "propagat":** base nova gravada, GradedSpec antic. El
  model queda *consistent en base, stale en escalat* fins a l'acte conscient.

### 2D · MIRALL — el fitting també auto-propaga (`:469`) [PREGUNTA DE FRONTERA, no decidida]
`close_piece_fitting` auto-propaga a [`services.py:469`](../../backend/fhort/fitting/services.py#L469)
(`generate_graded_specs(sf.pk)`), sempre que `changed`, amb `measurements_version++` si `base_changed`
(`:462-464`). **No hi ha botó Propagar posterior al tancament de fitting.**

Diferència de domini observable al codi:
- **Size check** = validació *pre-fitting* (l'usuari decideix acceptar/rebutjar/descartar; pot quedar
  «acceptat sense propagar»). Encaixa amb propagació diferida.
- **Fitting** = maduració amb model real; el tancament és transaccional i propaga dins.

⇒ **Pregunta oberta (exposada, no resolta):** el desacoblament conscient ¿aplica només al check, o
també al fitting? El codi suggereix que el fitting *pot* legítimament propagar en tancar (és l'acte de
maduració), mentre que el check no. **Decisió de domini per a la sessió d'implementació.**

### 2E · `brain.on_fitting_measurement_changed` = stub pur
[`fhort/fitting/brain.py:16-32`](../../backend/fhort/fitting/brain.py#L16): només fa `logger.info(...)`
i `return None`. Cridat des de `close_piece_fitting:473`. **No afecta cap de les dues fronteres; no
s'hi toca.**

### 4B · Gate→segellat no es trenca
El segellat (`aprovada=True`) es fa a `advance_phase_gate` → `seal_model_grading` (1C),
**independent de la propagació**. Desacoblar `:230` no toca aquesta cadena. La integritat
versió-aprovada es manté pels guards durs (1A/1B), no per l'ordre temporal de propagació.

---

## BLOC 3 — PANTALLES QUE CONVIUEN AMB MESURES

### 3A · Inventari de superfícies de mesura/escalat
| Superfície | Ruta | Component | Dada / acció | Estat |
|---|---|---|---|---|
| Mesures (model) | `/models/:id/mesures` | `ModelMeasurements.jsx` (`App.jsx:139`) | base + wizard manual/import + sembra | **ACTIU** (sospitosa "4/5") |
| Escalat (tasca) | `/models/:id/escalat` | `EscalatTask` → `PropagatedEditor.jsx` | `ModelGradingOverride` per cel·la, re-propaga | **ACTIU** |
| ModelSheet · tab Mesures | `/models/:id` | `ModelSheet.jsx:221-240` → `CheckMeasureEditor.jsx` | base + size_check (read-mostly) | **ACTIU** |
| ModelSheet · tab Escalat | `/models/:id` | `ModelSheet.jsx:243-255` → `PropagatedEditor` | escalat vigent (read-only) | **ACTIU** |
| Fitting | `/fittings/:id` | `FittingDetail.jsx` → `MeasureGrid.jsx` | `FittingPieceSize` (talles×versions) | **ACTIU** |
| Size-check antic | `/models/:id/size-check` | `SizeCheckRedirect` | redirigeix a `/mesures` | **JUBILAT** (redirect) |

La superfície convergida (24/06) és **`MeasureGrid.jsx`** (`components/model/`), reutilitzat per
FittingDetail, PropagatedEditor i CheckMeasureEditor.

### 3B · La pantalla "4/5" = `ModelMeasurements.jsx` (redundant, jubilable amb matís)
- **Existeix i està rutada:** `App.jsx:26` (lazy) + `App.jsx:139` (`<Route models/:id/mesures>`).
  **No** és al menú (`Sidebar.jsx`); s'hi entra per navegació contextual (vegeu enllaços avall).
- **Què mostra que ja sigui a un altre lloc:** la *taula de mesures base* i el *mode resultat* (read)
  ja els cobreix ModelSheet · tab Mesures (`CheckMeasureEditor`). **Redundància neta** en visualització.
- **Què té d'ÚNIC (es perdria si es jubila pla):** el **flux d'entrada** — selector manual/import
  (`:253-301`), oferta de **sembra/seed** (`:231-245`), **ImportWizard** PDF/IA (`:383-398`). Això és
  *flux*, no dada; caldria **migrar-lo** a dins ModelSheet, no perdre'l.
- **Enllaços entrants (caldria reapuntar-los si es jubila):** `KanbanTasks.jsx:691`,
  `ModelSheet.jsx:232` («Editar mesures»), `WorkPlan.jsx:26,29`, `SizeMapSetup.jsx:126`,
  `ModelFabric.jsx:286` — tots cap a `/models/:id/mesures?...`. Alguna pantalla ha de seguir atenent
  `/mesures` (o reapuntar tots aquests).

### 3C · Germans orfes
- `grep "MeasureTable|MeasurementTable"` → **0 imports vius** (jubilats el 24/06, confirmat).
- **Orfe nou trobat:** `components/MeasurementsChat/MeasurementsChat.jsx` — **0 imports** a tot
  `frontend/src` (prototip mort; jubilable net, sense relació amb les fronteres).
- Vius i NO duplicats de MeasureGrid: `CheckMeasureEditor` (ModelSheet), `MeasurementBaseGrid`
  (ItemAuthoring, llibreria d'ítems), `EditableTable` (l'usa ModelMeasurements — cau si es jubila 3B).

### 3D · Conseqüència de jubilar `ModelMeasurements`
**Treure:** `App.jsx:26` (lazy import) + `App.jsx:139` (Route); claus i18n `model_measurements.*` del
*wizard/intro* (`title`…`continue_fabric`, `notice_no_item`) als 3 `*.json`; revisar si `EditableTable`
i `ImportWizard` queden orfes.
**NO tocar:** claus `model_measurements.propagated_*` (les usa `PropagatedEditor`); `CheckMeasureEditor`
(ModelSheet); rutes `/escalat`, `/size-check`, `/models/:id`; els enllaços entrants — **abans** cal
decidir on aterren (migrar flux a ModelSheet vs. mantenir `/mesures` aprimat).
**Jubilació diferida a P4** (com sospitava el prompt): no és neta del tot perquè arrossega el flux
d'entrada i 5 enllaços entrants.

---

## VEREDICTE

- **FRONTERA A — guard de segellat: NO és un forat, és un AUDIT.** El guard ja existeix i és complet a
  `close_piece_fitting` (`services.py:436-440`, bloc `if changed:` `:429`) **i** al seu espill
  `resolve_size_check` (`services_size_check.py:204-208`). Únic escriptor de segellat:
  `seal_model_grading` (`services.py:579`) via `advance_phase_gate` (`tasks/services_d.py:51`) — lligat
  al GATE, no al fitting. **L'àncora del prompt (advance_phase:707-710) és stale**, i el docstring
  d'`advance_phase` (`:714-715`) descriu segellat que ja no fa (drift de doc a corregir). Opcions de
  re-grading: (ii) `allow_reopen_sealed=True` **ja existeix**; dessegellar (`aprovada=False`) **no
  existeix**. **Estat BD (`fhort`):** 13 versions, 2 aprovades, 4 actives, **anomalia multi-activa: NO**.
- **FRONTERA B — propagar-conscient: l'acte conscient JA existeix; queda treure UNA crida.**
  L'auto-propagació residual és `generate_graded_specs` a `resolve_size_check:230` (només
  accept-amb-deltes; reject/descartat no propaga). El "botó Propagar" conscient és
  `generar-grading` → `generate_grading_view` (`views.py:1135`), que **(re)omple GradedSpec però NO crea
  v+1 ni segella**; el botó pla d'auto-grading ja es va retirar de Mesures (D-10,
  `ModelMeasurements.jsx:89`). **Desacoblar = treure `:230`** (i decidir si `measurements_version++`
  de `:227` es mou amb ell). **GAP temporal:** entre accept i Propagar, base nova gravada però
  GradedSpec/escalat *stale*. **Aplica al check; al fitting NO (pregunta oberta):** `close_piece_fitting`
  auto-propaga a `:469` com a acte de maduració — exposat, **no decidit**.
- **PANTALLES:** la redundant és `ModelMeasurements.jsx` (`/models/:id/mesures`, `App.jsx:139`);
  **jubilable amb matís** — perdria el flux d'entrada (selector/seed/import) i 5 enllaços entrants, que
  cal migrar a ModelSheet o mantenir `/mesures` aprimat (diferir a P4). Orfe net nou:
  `MeasurementsChat.jsx` (0 imports). `MeasureTable`/`MeasurementTable` ja jubilats (0 imports).
- **FRONTERES:** A és **d'aquesta sessió** (no toca GradingException/Override ⇒ no és G6); ja resolta
  ⇒ degenera en *verificació*. Desacoblar la propagació **NO trenca** gate→segellat (cadenes
  independents).
- **DIMENSIÓ (estimació):** Frontera A ≈ **0 línies de motor** (ja fet) + ~3 de neteja de docstring
  stale (`services.py:714-715`). Frontera B ≈ **1-4 línies backend** (treure `:230`, decidir `:227`) +
  decisió de domini check-vs-fitting. Pantalles ≈ **~30-60 línies** de retirada (App.jsx + i18n) **+
  migració del flux d'entrada** (la part real de feina, no trivial). **Ordre suggerit:** (1) Frontera B
  desacoblament — petit i d'alt valor; (2) audit/segellat de Frontera A + neteja docstring; (3) pantalla
  ModelMeasurements diferida a P4 amb migració de flux prèvia.

*Fi de la diagnosi. No s'ha implementat res. Atura't aquí.*
