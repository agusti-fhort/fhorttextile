> ⚠️ SUPERADA 2026-07-07 — implementada (4 GAPS tancats; botó generar-grading cablejat + versionat compartit). Consulta només com a històric.

# DIAGNOSI DE PARITAT — FITTING ↔ GRADING/ESCALAT

**Patró A · read-only · branca `dev` · 2026-06-24**
Entorn: `/var/www/ftt-staging` (backend Django + frontend React). Dades al schema **`fhort`**
(verificat: `\dn` → `{fhort, public}`; clients = `(1,public),(2,fhort)`; **no existeix tenant id=6**).
Motor de grading: `venv/bin/python` sempre. Cap fitxer modificat.

**Mandat (DECISIONS.md §2):** el fitting com a *pantalla convocada amb totes les talles propagades*
queda jubilat; es dissol en (1) presa de mesura base dins Mesures (FITTED) i (2) treball sobre **totes
les talles** → funcionalitat de **Grading/Escalat**. **CONDICIÓ BLOQUEJANT:** tota la maquinària del
fitting ha d'existir, viva i accessible a Grading, **ABANS** de jubilar res. Aquesta diagnosi **NO
proposa jubilar ni implementar res**: només **inventaria i compara paritat**.

> **Resum d'una línia:** el **motor** de grading és compartit i té paritat; els **GAPS** són
> (a) ❌ el **versionat funcional v+1 per canvi conscient** (history de fits) no existeix a Grading;
> (b) ⚠️ el **botó "Propagar conscient"** (`generar-grading`) existeix al backend però **està orfe**
> (cap pantalla el crida); (c) ⚠️ la **visualització multi-versió** i (d) ⚠️ l'**ajust ancorat
> per talla** són més pobres o semànticament diferents a Grading. **Sense risc de pèrdua de dades a
> nivell de model**, però 2 sessions obertes amb 8 línies divergents s'han de tancar primer.

---

## BLOC 1 — CAPACITATS DEL FITTING (columna "Fitting")

| # | Capacitat | On viu (ruta:línia) | Què fa |
|---|---|---|---|
| 1A | **Propagació / re-escalat de totes les talles** | `fitting/services.py:469` (dins `close_piece_fitting`) → `generate_graded_specs(sf.pk)` | Regenera `GradedSpec` (POM×talla) sobre la GradingVersion vigent |
| 1B | **Règim LINEAR/STEP** | front `fittingGridAdapter.jsx:69-99` (`regimeLeadCol`), `FittingDetail.jsx:581-593` (`onRegimChange`→`setPomRegim`) → back `models_app/views.py:1856` (`set_pom_regim_view`) | Mostra i **canvia** el règim del POM; persisteix a `ModelGradingRule` |
| 1C | **Breaks** | front `fittingGridAdapter.jsx:48-49,55-64` (read-only display) · back `pom/grading_utils.py:198` (`derive_break_fields`) | El fitting **mostra** `increment_break`/`talla_break_label` però **no els edita** |
| 1D | **Ajust puntual per talla (prenda real)** | model `PieceFittingLine` (`valor_real` vs `valor_teoric`); `PATCH /piece-fitting-lines/<id>/` (1 cel·la); `POST /piece-fitting-lines/<id>/propagar/` → `fitting/views.py:483-546` | Edita la mesura **física** per cel·la; **propaga LINEAR** a les talles germanes des d'una àncora (STEP no propaga) |
| 1E | **Cicle GradingVersion (v+1)** | `fitting/services.py:448-459` (desactiva totes les actives, crea `max+1`) | **Versionat funcional:** cada tancament amb canvi crea v+1 nova activa (history de fits). NO segella (1G) |
| 1F | **Visualització de totes les talles** | front `MeasureGrid.jsx` via `fittingGridAdapter.jsx:15-53` | Graella **POM × talla × VERSIÓ** (Base, Fit 1, Fit 2… + columna activa editable) |
| 1G | **Cerimònia de sessió** (no-grading) | attendees `services.py:944`; notes `FittingDetail.jsx:370`; fotos `FittingPhoto`/`views.py`; **gate per peça** `services.py:594-634` (`set_piece_gate` OK/NO_OK/EXCEPCIO); durada `services.py:675-705`; convocatòria/grup `services.py:791-994`; brain stub `brain.py:16-32`; cicle de vida sessió | Treball de **sessió presencial**, no de grading. Es jubila amb la pantalla (vegeu nota 1G avall) |

**Confirmació 1E (clau):** `close_piece_fitting` és, amb `resolve_size_check:218`, **l'únic camí que crea
v+1**. Desactiva *totes* les actives (`services.py:448`) i crea `version_number=max+1, is_active=True`
(`:452`). El fitting **ja NO segella** (`aprovada=True`): el cos del bucle a `advance_phase:757-769` és
buit a posta (D-3); el segellat viu a `seal_model_grading:579` via `tasks.advance_phase_gate`.

**Nota 1G (cerimònia):** attendees, fotos, notes, convocatòria, durada, cicle de vida són part de la
*pantalla-sessió* que es jubila per disseny — **no són capacitats de grading** i no requereixen paritat.
**Excepcions a vigilar:** (i) **gate per peça** OK/NO_OK/EXCEPCIO (`set_piece_gate`) = decisió de
validació per talla/peça; (ii) **fotos** = evidència visual del fit. Cap de les dues té llar a Grading;
queden fora de l'abast de "maquinària de talles" però es perden com a *registre* si no es decideix on van.

---

## BLOC 2 — EQUIVALENTS A GRADING/ESCALAT (columna "Grading")

| # | Capacitat | Equivalent Grading (ruta:línia) | Observació |
|---|---|---|---|
| 2A | **Propagació** | `models_app/views.py:1135` (`generate_grading_view`, endpoint `models/<id>/generar-grading/`) → `generate_graded_specs`; i `views.py:1321` (re-propaga dins `set_size_override_view`) | **Motor compartit** (`pom/services.py:18`). Acte conscient = `generar-grading` |
| 2B | **Règim LINEAR/STEP** | `views.py:1856` (`set_pom_regim_view`, endpoint `models/<id>/pom/<id>/regim/`) → upsert `ModelGradingRule.logica`; front `PropagatedEditor.jsx` (`regimeLeadCol`, editable quan no read-only) | **MATEIX endpoint que el fitting.** `detect_grading` (`grading_utils.py:116`) només detecta en import |
| 2C | **Breaks** | `grading_utils.py:198` (`derive_break_fields`) auto-deriva; editable per API via `set_pom_regim_view` (`talla_break_label` al body, `views.py:1919`) | **Cap UI dedicada** d'edició de breaks (ni a Grading ni al fitting) |
| 2D | **Ajust per talla** | `views.py:1239` (`set_size_override_view`, endpoint `set-size-override/`) → upsert `ModelGradingOverride(model,pom,size_label)` amb `fitting_ref=None` + re-propaga (`:1321`); front `PropagatedEditor.jsx:45` | Override a **nivell de model** (no prenda física). Prioritat màxima al motor (`pom/services.py:92-96`) |
| 2E | **GradingVersion v+1** | `pom/services.py:427` (`_get_or_create_grading_version`): **reutilitza** la `is_active=True`; només crea si no n'hi ha cap | **NO fa v+1 per canvi:** sobreescriu la versió vigent in-place |
| 2F | **Visualització totes les talles** | front `PropagatedEditor.jsx` → `MeasureGrid.jsx` (mateix component); dada `taula-mesures` (`views.py:626`) amb `graded`+`deltes`+règim | Graella **POM × talla** d'**una sola** versió (snapshot). Sense eix de versions |

**Confirmació 2E (el GAP gros):** `_get_or_create_grading_version` (`pom/services.py:431-441`) fa
`filter(size_fitting=sf, is_active=True).last()` i **només crea** si retorna `None`. ⇒ `generar-grading`
i `set-size-override` **sobreescriuen** el `GradedSpec` de la versió activa; **no preserven historial**.
El versionat funcional (v+1 amb la versió anterior desada com a `is_active=False`) **només existeix als
camins fitting/size_check** (`services.py:452`, `services_size_check.py:218`).

---

## BLOC 3 — MATRIU DE PARITAT

| Capacitat | Fitting (on) | Grading equivalent (on) | Estat |
|---|---|---|---|
| **1A Propagar totes les talles** | `services.py:469` | `generate_grading_view` `views.py:1135` + re-propaga `views.py:1321` | **⚠️ PARCIAL** — *motor* idèntic i viu, però l'acte conscient (`generar-grading`) **està orfe al frontend** (vegeu 4B) |
| **1B Règim LINEAR/STEP** | `fittingGridAdapter.jsx:69` → `setPomRegim` | `set_pom_regim_view` `views.py:1856`; `PropagatedEditor` editable | **✅ PARITAT** — mateix endpoint; accessible des de `/escalat` editable |
| **1C Breaks** | display read-only `fittingGridAdapter.jsx:48` | auto-derivat `grading_utils.py:198` + API `set_pom_regim_view` | **✅ PARITAT** (igual de limitada: cap UI d'edició a cap dels dos; el fitting tampoc edita breaks) |
| **1D Ajust per talla** | `PieceFittingLine.valor_real` + `propagar` `views.py:483` | `ModelGradingOverride` `views.py:1239` (`set-size-override`) | **⚠️ PARCIAL** — Grading té override per cel·la, **però** (i) semàntica distinta (model vs prenda física), (ii) **no té l'acció "ancorar i propagar LINEAR a germanes"** del fitting (`propagar`), (iii) la via model (`fitting_ref=None`) **mai s'ha usat** (5/5 overrides reals vénen del fitting) |
| **1E Versionat v+1 (history fits)** | `services.py:448-459` (crea v+1, desactiva anterior) | `_get_or_create_grading_version` `pom/services.py:427` **reutilitza** activa | **❌ ABSENT** — Grading **no crea versió nova** en un canvi conscient; sobreescriu. Sense camí per "aquesta propagació = nova versió, l'anterior queda d'històric" fora del fitting/size_check |
| **1F Visualització totes les talles** | `MeasureGrid` POM×talla×**versió** | `MeasureGrid` POM×talla (1 versió) | **⚠️ PARCIAL** — mateix component, però Grading no pinta l'**eix de versions** (history de fits) |
| **1G.gate Decisió per peça (OK/NO_OK/EXC)** | `set_piece_gate` `services.py:594` | — (gate de fase a `tasks.advance_phase_gate`, no per talla/peça) | **❌ ABSENT** (com a decisió per peça/talla) — *cerimònia*; fora d'abast de talles però sense llar |
| **1G.* Cerimònia sessió** (attendees, fotos, notes, convocatòria, durada) | `services.py` diversos | — | **n/a** — es jubila amb la pantalla per disseny; només *fotos* són evidència sense llar |

**Detall del que cal construir (⚠️ i ❌):**
- **❌ 1E — Versionat funcional a Grading:** caldria que l'acte conscient de propagar pogués **crear una
  GradingVersion v+1** (desactivant l'anterior) en comptes de sobreescriure, per conservar history. Lloc
  natural: dins/al costat de `generate_grading_view` (`views.py:1135`) o un nou acte "Propagar com a nova
  versió". Avui `pom/services.py:427` ho impedeix (reutilitza activa).
- **⚠️ 1A — Llar del botó "Propagar conscient":** l'endpoint `generar-grading` existeix però cap pantalla
  el crida; cal donar-li una entrada a la superfície supervivent (ModelSheet/Escalat).
- **⚠️ 1D — Ajust ancorat + propagació LINEAR a germanes:** `set-size-override` re-propaga **tota** la
  taula via motor; no replica l'acció "edita aquesta talla i propaga el delta a les germanes" (`propagar`,
  `views.py:483`). Si es vol paritat funcional, cal exposar-la a Escalat.
- **⚠️ 1F — Eix de versions a la graella d'Escalat:** `MeasureGrid` ja ho suporta (s'usa al fitting); cal
  alimentar-lo amb l'historial de `GradingVersion`/`GradedSpec` des de PropagatedEditor.

---

## BLOC 4 — ACCESSIBILITAT DES DE LA SUPERFÍCIE QUE SOBREVIU

### 4A · Entrades a Grading des de ModelSheet
- **Tabs de ModelSheet** (`ModelSheet.jsx:20`): Dashboard, Resum, Mesures, **Escalat**, Fitxa tècnica,
  Fitxers, Registre.
- **Tab Escalat** (`ModelSheet.jsx:243-255`): mostra `PropagatedEditor` **read-only** (`readOnly=true`);
  l'edició real passa pel botó "Editar escalat" → `/models/:id/escalat?task_id=…` (`EscalatTask`), on
  `PropagatedEditor` és editable: **override per cel·la** (`setSizeOverride`) + **canvi de règim**
  (`setPomRegim`) + re-propaga. ⇒ Règim i ajust per cel·la **SÍ** són accessibles.
- **Pla de treball / Kanban** (`WorkPlan.jsx:24-34`, `KanbanTasks.jsx:29-35`): tasca `scaling` →
  `/escalat`; tasca `size_check` → `/mesures`. ⇒ entrada via tasques OK.

### 4B · "Propagar conscient" (`generar-grading`) — **ORFE (GAP)**
`grep` a tot `frontend/src`: l'única menció de `generar-grading` és el **comentari** a
`ModelMeasurements.jsx:89-90` («RETIRAT… l'endpoint es CONSERVA per a la projecció conscient»).
**Cap component crida `models/<id>/generar-grading/`.** El botó d'ImportWizard (`ImportWizard.jsx:783`,
`handleGenerarGrading`) crida un endpoint **diferent** (`import-sessions/<token>/grading-preview/`,
`:315`), que omple columnes buides de l'staging d'import — **no** és el grading del model.
⇒ **L'acte conscient de propagar existeix al backend però NO té entrada a cap pantalla supervivent.**

### 4C · Capacitats només a pantalles jubilables
- **`/fittings/:id` (FittingDetail):** ajust de `valor_real` de **prenda física**; **`propagar` LINEAR
  ancorat** a germanes; **evolució multi-versió** (comparar fits); **gate per peça**; tancar/descartar
  peça. Cap d'aquestes (excepte règim, que sí és a Escalat) té equivalent **accessible** a ModelSheet.
- **`/models/:id/mesures` (ModelMeasurements):** tasca **size_check integrada**, seed/import des de
  prototip, selector de POMs. La tab Mesures de ModelSheet és read-only + botó cap a aquesta pantalla.

---

## BLOC 5 — DADES REALS (schema `fhort`, read-only)

| Mètrica | Valor |
|---|---|
| FittingSession | **19** (Programada 14 · Oberta **2** · Tancada 3 · Anullada 0) |
| PieceFitting / PieceFittingLine | 4 / 139 |
| PieceFittingLine amb `valor_real` ≠ `valor_teoric` | **8** (mesura real divergent, en vol) |
| GradedSpec | 547 |
| GradingVersion (aprovades) | 13 (2) |
| ModelGradingOverride (amb `fitting_ref` no null) | **5 (5)** — *tots* d'origen fitting; via model **mai usada** |
| SizeFitting / Model | 19 / 19 |
| Models amb PieceFitting / amb GradedSpec | 3 / 4 |
| **Models amb fitting SENSE GradedSpec (risc de pèrdua)** | **[] — CAP** |

**Risc de pèrdua de dades:** **NUL a nivell de model** — els 3 models amb fitting tenen GradedSpec
propagat. **Risc residual acotat:** **2 sessions Obertes** + **8 línies amb `valor_real` divergent** =
feina de fitting en vol no encara propagada a `GradedSpec`; s'han de **tancar (propagar) abans** de
jubilar res, o es perdrien aquestes 8 mesures concretes. **Dada reveladora:** els 5 `ModelGradingOverride`
existents tenen `fitting_ref` no null ⇒ tots els ajustos per talla reals han entrat **pel fitting**; la
via conscient `set-size-override` (origen model) està construïda però **verge** en producció.

**5B — Entorn:** schemas = `{fhort, public}`; clients = `(1,public),(2,fhort)`. **Cap tenant id=6.**

---

## VEREDICTE

Per capacitat (Fitting → Grading → estat):

- **1A Propagar totes les talles** → Fitting `services.py:469` → Grading `generate_grading_view`
  `views.py:1135` (motor compartit `pom/services.py:18`) → **⚠️ PARCIAL** (motor viu; botó orfe, 4B).
- **1B Règim LINEAR/STEP** → `fittingGridAdapter.jsx:69`/`setPomRegim` → `set_pom_regim_view`
  `views.py:1856` (mateix endpoint, accessible a `/escalat`) → **✅ PARITAT**.
- **1C Breaks** → display `fittingGridAdapter.jsx:48` → auto-derivat `grading_utils.py:198` + API →
  **✅ PARITAT** (igual de limitada als dos; cap UI d'edició).
- **1D Ajust per talla** → `PieceFittingLine`+`propagar` `views.py:483` → `set-size-override`
  `views.py:1239` → **⚠️ PARCIAL** (override existeix però semàntica distinta i sense l'acció "ancorar+
  propagar LINEAR a germanes"; via model verge a producció).
- **1E Versionat v+1 / history de fits** → Fitting `services.py:448-459` → Grading
  `_get_or_create_grading_version` `pom/services.py:427` **reutilitza, no crea** → **❌ ABSENT**.
- **1F Graella totes les talles** → `MeasureGrid` ×versió → `MeasureGrid` ×1 versió → **⚠️ PARCIAL**
  (mateix component, sense eix de versions a Escalat).
- **1G gate per peça / fotos** → `set_piece_gate` `services.py:594` / `FittingPhoto` → — → **❌ ABSENT**
  (cerimònia; fora d'abast de talles però sense llar com a registre).

**El que cal construir ABANS de poder jubilar (condició bloquejant):**
1. **❌ Versionat funcional a Grading (1E)** — l'acte conscient ha de poder crear **v+1** (no
   sobreescriure) per conservar history de fits. *La peça més gran.*
2. **⚠️ Llar del "Propagar conscient" (1A/4B)** — donar entrada a `generar-grading` a ModelSheet/Escalat
   (avui orfe).
3. **⚠️ Ajust ancorat + propagació LINEAR a germanes (1D)** i **⚠️ eix de versions a la graella (1F)** —
   exposar a Escalat la riquesa que avui només té el fitting.
4. *(Cerimònia)* decidir destí de **gate per peça** i **fotos** (1G) — fora de "talles" però són
   decisió/evidència sense llar.

**Risc de pèrdua de dades:** **NO a nivell de model** (0 models fitting sense GradedSpec). Risc acotat:
**2 sessions Obertes + 8 línies divergents** a tancar abans de jubilar.

**Dimensió de la reconstrucció (orientativa):** 1E ≈ canvi de motor + nou acte (mitjà, backend
`pom/services.py` + `views.py` + UI); 1A/4B ≈ petit (botó + crida endpoint existent); 1D ≈ mitjà
(endpoint `propagar`-equivalent a model + UI Escalat); 1F ≈ petit-mitjà (alimentar `MeasureGrid` amb
historial, component ja preparat); 1G ≈ decisió de domini, no de codi. **Ordre de dependència:** 1E i
1A són prerequisit de la jubilació; 1D/1F milloren paritat funcional; 1G és decisió a part.

*Fi de la diagnosi. No s'ha implementat res. Atura't aquí.*
