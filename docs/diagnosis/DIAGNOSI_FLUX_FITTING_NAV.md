# DIAGNOSI — Flux de fitting: navegació + integritat de dades

> Data: 2026-07-10 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`.
> HEAD de la investigació: `b08baaf`. Cap línia de codi tocada.
> Convenció: `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi (no especulat).**
> Cap proposta d'implementació. Les decisions van a §PER DECIDIR.

**Nota de mètode (desviació conscient):** el brief demanava la sortida a
`/root/fhort-sessions/`. `CLAUDE.md` §Diagnosis mana que les diagnosis viuen a
`docs/diagnosis/` (arrel = vigents) i que SÍ es commiten. S'ha seguit la llei del repo.

---

## Resum executiu

1. **🔴 El tall de flux existeix i és total.** Tota edició de cel·la de la graella de fitting
   —base o no-base— escriu a `PieceFittingLine.valor_real`. En tancar, **només les línies de la
   talla base** es promocionen a `BaseMeasurement`. Les no-base **no tenen cap lector fora de la
   pròpia graella**: moren amb la sessió.
2. **🔴 El tancament no avisa de la pèrdua.** `hasSaveChanges` compta com a "hi ha canvis"
   qualsevol talla, inclosa una no-base. Si el tècnic només ha tocat no-base: es crida `close`,
   `consolidate_base_from_fitting` no consolida res, `changed=0`, **no es crea versió nova**, i
   la sessió **es segella igualment**. Silenci total.
3. **La graella de fitting SÍ és `MeasureGrid`** (convergència G1 aplicada), però amb **un grup per
   TALLA**. `CheckMeasureEditor` (Mesures) usa **un sol grup `base`**. Mateix component, dos eixos:
   l'eix del fitting és exactament el que la llei §2 declara jubilat.
4. **La mateixa matemàtica, dos destins.** `piece-fitting-lines/propagar` i
   `escalat/ajustar-talla` criden tots dos `propaga_ancoratges`. El primer escriu
   `PieceFittingLine.valor_real` (mor); el segon escriu `BaseMeasurement` i re-deriva (sobreviu).
5. **El règim és l'única escriptura de la graella de fitting que persisteix**: escriu
   `ModelGradingRule`, patrimoni del model. És una escriptura al motor de grading des d'una
   pantalla jubilada.
6. **"Gravar el fitting" NO és un botó**: és el títol de la pantalla de revisió. El botó real és
   "Gravar i tornar".
7. **La convocatòria no existeix com a recurs de backend.** No hi ha GET de grup, i
   `fitting-sessions/` **ni tan sols filtra per `convocatoria`**. L'agrupació la fa el client.
8. **Cap retorn de context.** Tota sortida és `navigate(-1)` o `navigate('/fittings')`, sense
   `state`. Filtres, grups desplegats i scroll es perden.

---

# F1 — Integritat de dades de la graella (PRIORITAT MÀXIMA)

## F1.a — Què escriu cada control editable

| # | Control | Crida frontend | Endpoint | Escriu |
|---|---|---|---|---|
| 1 | Cel·la, règim ≠ STEP | `fittingGridAdapter.jsx:148` | `POST /piece-fitting-lines/<id>/propagar/` | `PieceFittingLine.valor_real` (ancorada + germanes) |
| 2 | Cel·la, règim STEP | `fittingGridAdapter.jsx:147` | `PATCH /piece-fitting-lines/<id>/` | `PieceFittingLine.valor_real` (només la cel·la) |
| 3 | Règim (LINEAR/STEP) | `endpoints.js:58` | `POST /models/<id>/pom/<pom>/regim/` | **`ModelGradingRule`** (patrimoni del model) |
| 4 | "Gravar i tornar" | `FittingDetail.jsx:193,202` | `POST /piece-fittings/<id>/close/` + `.../seal/` | `BaseMeasurement` (només base) + `GradingVersion` |
| 5 | "Descartar canvis" | `FittingDetail.jsx:212-226` | `POST /piece-fittings/<id>/discard/` | `valor_real := valor_teoric` |
| 6 | "Tornar a revisió" | `FittingDetail.jsx:713-716` | — | res (toggle de client pur) |

**F1-1.** El botó "propagar" com a control independent **NO EXISTEIX** a la graella de fitting: la
propagació és un **efecte de desar una cel·la** amb règim LINEAR/canònic
(`fittingGridAdapter.jsx:144-150`). Buscat a `FittingDetail.jsx` i `MeasureGrid.jsx`.

**F1-2.** La columna **"FIT ACTUAL"** és la cel·la activa editable de cada grup-talla
(`fittingGridAdapter.jsx:22`, `activeLabel`); les columnes `Base`/`Fit N` són `historyCols`
read-only (`fittingGridAdapter.jsx:21`), reconstruïdes des de `evolucio`
(`fitting/serializers.py:238-250`).

**F1-3.** `set_pom_regim_view` (`models_app/views.py:2493`) fa **UPSERT de `ModelGradingRule`**
(règim + deltes + break). Docstring `:2494-2505`: *"patrimoni VIU del MODEL"*. És l'única
escriptura de la graella de fitting que **sobreviu al tancament de la sessió**.

## F1.b — Què acaba a `BaseMeasurement` + log F1

**F1-4.** `close_piece_fitting` (`fitting/services.py:379`) delega a
`consolidate_base_from_fitting` (`fitting/services.py:341-376`).

**F1-5.** Per cada `PieceFittingLine` (`services.py:358`):
- `:359-360` salta si `valor_real is None`.
- `:361-362` salta si `|valor_real − valor_teoric| < 1e-6` (cap rectificació).
- **`:363-364` salta si `line.size_label.strip() != base_size`** ← el tall.
- `:365-374` escriu `BaseMeasurement(model, pom)`: `base_value_cm = valor_real`,
  `origen='FITTED'`, `_changed_by`, `_fitting_ref` (→ `SizeFitting`), `_motiu`.

**F1-6.** El senyal F1 és `log_measurement_change` (`models_app/signals.py:215`), amb
`capture_old_measurement_value` (`signals.py:196`) al `pre_save`. Escriu `MeasurementChangeLog`
si el valor canvia (`signals.py:238-240`) i si `base_value_cm is not None` (`signals.py:235-236`).

**F1-7.** Si hi ha línies consolidades (`services.py:439`), `bump_grading_version_and_generate`
(`pom/services.py:505`) crea `GradingVersion v+1`, incrementa `measurements_version` i re-propaga.
Si **cap** línia base ha canviat, `changed=0` → **cap versió nova**.

## F1.c — 🔴 Inventari d'escriptures que NO arriben a la taula de mesures

**F1-8.** `PieceFittingLine.valor_real` de **totes les talles no-base**.
- Escrit per `PATCH` (`fitting/views.py:476-481` → `serializers.py:184`).
- Escrit per `propagar`, tant la cel·la ancorada (`views.py:516-517`) com **les germanes**
  (`views.py:543-545`).
- **Lectors (cens complet, grep a `backend/fhort/`):** només
  `PieceFittingGridSerializer.get_lines` (`fitting/serializers.py:265`), que és la pròpia graella.
  Cap servei, cap motor, cap altra vista.
- **Destí final: cap.** No arriben a `BaseMeasurement`, ni a `ModelGradingOverride`, ni a
  `GradedSpec`.

**F1-9.** 🔴 **El tancament no distingeix.** `hasSaveChanges` (`FittingDetail.jsx:146-150`) marca la
peça com a "amb canvis" si **qualsevol** línia difereix, sense mirar `size_label`. Conseqüència
exacta, si el tècnic només ha editat no-base:
1. `doSave` crida `close` (`FittingDetail.jsx:193`).
2. `consolidate_base_from_fitting` salta totes les línies (`services.py:363-364`) → `consolidated=[]`.
3. `changed=0` → cap Welford, cap `GradingVersion` nova (`services.py:439`).
4. `_seal_session` segella igualment (`services.py:467`, i de nou `FittingDetail.jsx:202`).
5. `onSaved()` → `navigate(-1)` (`FittingDetail.jsx:207,648`).
**Cap error, cap avís, cap traça. La feina s'ha perdut i la sessió és `Tancada`.**

**F1-10.** La via **legítima** per a una talla no-base existeix i és `set_size_override_view`
(`models_app/views.py:1666`), que escriu `ModelGradingOverride` i re-propaga
(`generate_graded_specs`). Docstring `:1673-1675`: *"NO toca GradedSpec directament … ni
PieceFittingLine"*. Gate: `_ExecuteTasksCap` (`views.py:1665`).
**El client la té definida (`endpoints.js:63-64`) i NO la crida ningú** (grep de `setSizeOverride(`
a `frontend/src/`, exclòs `endpoints.js`: **buit**).

**F1-11.** La superfície d'Escalat sí que té camí viu: `PropagatedEditor.jsx:47` →
`models.escalatAjustarTalla` → `escalat_ajustar_talla_view` (`models_app/views.py:1780`). El seu
docstring (`:1783-1794`) declara la **convergència explícita amb el fitting**: fa
`propaga_ancoratges` igual, però *"el magatzem que sobreviu la re-derivació és la BASE
(BaseMeasurement)"* i re-deriva amb `generate_graded_specs`.

> **Contrast net (mateixa matemàtica, dos destins):**
> `propaga_ancoratges` (`pom/grading_utils.py:560`) el criden els dos.
> · fitting `propagar` (`fitting/views.py:538`) → escriu `PieceFittingLine.valor_real` (`:543-545`) → **mor al close**.
> · escalat `ajustar-talla` (`models_app/views.py:1780`) → escriu `BaseMeasurement` → **sobreviu**.

## F1.d — Què fa exactament `close_piece_fitting` avui

| Pas | Línia | Acció |
|---|---|---|
| 1 | `services.py:399-401` | Carrega `PieceFitting` (+model, grading_version, size_fitting) |
| 2 | `services.py:408-411` | Resol `UserProfile` → `auth_user` (per al log F1) |
| 3 | `services.py:419` | `consolidate_base_from_fitting` → **única escriptura de mesures** |
| 4 | `services.py:423-436` | Welford `update_client_profile` per línia consolidada (no-fatal) |
| 5 | `services.py:439-453` | Si `changed`: `bump_grading_version_and_generate` → `GradingVersion v+1` |
| 6 | `services.py:456-462` | `on_fitting_measurement_changed` (brain stub, sense propagació) |
| 7 | `services.py:467` | **`_seal_session(pf.session)`** — el close ja segella |
| 8 | `services.py:469-476` | Retorna `{changed, base_changed, override_changed(sempre False), new_version}` |

**F1-12.** `override_changed` és **sempre `False`** (`services.py:413,472`); es manté per compat. de
forma. Docstring `:395`.

**F1-13.** Guard de sessió segellada: `fitting_line_is_locked` (`fitting/services.py:24-27`) →
409 a `partial_update` (`views.py:479-480`) i a `propagar` (`views.py:499-500`).

**F1-14.** `discard_piece_fitting` (`services.py:479-496`) fa
`valor_real := valor_teoric` per a **totes** les línies, atòmicament. No toca sessió ni grading.

## F1.e — Camí PG-4 (edició de cel·la no-base): estat real

**F1-15.** **Existeix i funciona dins la sessió.** L'endpoint `propagar`
(`fitting/views.py:483-546`) és PG-4b:
- `:513-517` desa sempre la cel·la ancorada; `:518-519` treure ancoratge → no propaga.
- `:522-524` resol la regla resident (`_load_grading_rules`); sense regla → no propaga.
- `:526-532` **STEP MAI propaga**, encara que `increment_base` estigui poblat (`:526-527`).
- `:534-545` propaga el delta a les germanes (`valor_teoric` intacte).

**F1-16.** Per tant PG-4 està **complet a la capa de sessió i absent a la capa de model**: cap
d'aquestes escriptures creua cap a `BaseMeasurement`/`ModelGradingOverride` (F1-8).

## TAULA DE CADENES (node → escriptors → destí)

| Node | Escriptors | Destí final | Estat |
|---|---|---|---|
| `PieceFittingLine.valor_real` (talla BASE) | `views.py:517`, `:545`, `serializers.py:184` | `BaseMeasurement` (`services.py:365-374`) → `MeasurementChangeLog` (`signals.py:215`) | ✅ TANCADA |
| `PieceFittingLine.valor_real` (talla NO-BASE) | `views.py:517`, `:543-545`, `serializers.py:184` | **cap** (només `serializers.py:265`, la pròpia graella) | 🔴 **CUL-DE-SAC** |
| `ModelGradingRule` (règim) | `models_app/views.py:2493` | motor: `_load_grading_rules` → `generate_graded_specs` | ✅ TANCADA |
| `ModelGradingOverride` | `models_app/views.py:1666`, `:1780` | motor (precedència màxima), `pom/services.py:448` | ⚠️ **SENSE CRIDADOR** des del fitting |
| `GradingVersion` (v+1) | `pom/services.py:505` via `services.py:445` | `GradedSpec` re-propagats | ✅ TANCADA |
| `GradingVersion.aprovada` | `fitting/services.py:547-567` | només `tasks/services_d.py:47` (`advance_phase_gate`) | ⚠️ **ORFE** del gravat |
| `FittingSession.estat → Tancada` | `services.py:467` (close) + `services.py:949` (seal) | — | ⚠️ **DOBLE** (idempotent) |

---

# F2 — Entrada des de la llista (`/fittings`)

**F2-1.** Component: `FittingSessionList` (`FittingSessionList.jsx:62`), ruta `fittings`
(`App.jsx:255`). Una sola `<table>` (`:346`) amb files de grup i files individuals.

**F2-2.** Partició client-side per `s.convocatoria` (`FittingSessionList.jsx:108-124`).

**F2-3.** Sub-fila de model dins d'un grup (`FittingSessionList.jsx:418-439`): `onClick` fa
`navigate('/fittings/' + s.id)` (`:420`). **Sense `state`.** El UUID de convocatòria **no viatja**.

**F2-4.** Fila individual (`FittingSessionList.jsx:445-465`): `onClick` fa
`navigate('/fittings/' + r.id)` (`:447`). Idèntic, sense `state`.

**F2-5.** La capçalera de grup **no navega**: `toggleGrup(uuid)` (`:367`, `:126-130`). L'entrada és
**sempre per sessió**, mai per convocatòria.

**F2-6.** L'estat **no canvia la navegació**; només la cel·la d'accions (`:243-258`):
`Programada|Oberta` → descartar (`:245-250`); `Programada` → a més, eliminar (`:251-256`);
`Tancada|Anullada` → cap acció. Enum: `['', 'Oberta', 'Programada', 'Tancada', 'Anullada']` (`:12`).

**F2-7.** 🔴 En entrar, una sessió `Programada` **es converteix en `Oberta` automàticament**:
`useEffect` (`FittingDetail.jsx:497-507`) crida `fittingSessions.open` (`endpoints.js:518`).
Obrir per mirar ja muta l'estat.

---

# F3 — Landing actual

**F3-1.** Component `FittingDetail` (`FittingDetail.jsx:470`), ruta `fittings/:id` (`App.jsx:257`).

**F3-2.** `reviewMode` neix a `true` (`:482`) → la landing és `ReviewScreen`, no la graella.

**F3-3.** `readOnly = session.estat === 'Tancada' || session.estat === 'Anullada'` (`:534`).

**F3-4 — branques de render:**
- **A** `reviewMode && !readOnly` (`:643-655`): `ReviewScreen` sol.
- **B** `reviewMode && readOnly` (`:658-687`): split 40/60, `MeasureGrid editable={false}` (`:678-683`).
- **C** `!reviewMode` (`:689-744`): selector de peça + `MeasureGrid editable` (`:734-740`).
  **No hi ha guard de `readOnly` a la branca C**; només `reviewMode` la governa.

**F3-5.** 🔴 **"Gravar el fitting" NO EXISTEIX com a botó** (confirmat absent). `fitting.save.title`
= `'Gravar el fitting'` (`ca.json`) i s'usa **una sola vegada, com a `<span>` de títol**
(`FittingDetail.jsx:286`). La clau bessona `fitting.save.open` (mateix text) **no s'usa enlloc**
(grep de `save.open` a `frontend/src/`: buit).

**F3-6.** Card "Taula de mesures" (`:294`), visible només si `!readOnly`. Dins:
- `hasPieces` → botó **"Veure / editar taula"** (`:297-300`), `onClick={onShowGrid}` =
  `() => setReviewMode(false)` (`:650`, `:668`). Cap endpoint.
- `!hasPieces` → botó **"Registrar mesures"** (`:306-309`) → `registrarMesures` (`:237-247`) →
  `createPiece` (`:519-525`) → `POST /fitting-sessions/<id>/create-piece/` (`endpoints.js:513`).

**F3-7.** Botons del `ReviewScreen` si `!readOnly` (`:429-463`): "Gravar i tornar" (`:431-434`,
`doSave`), "Descartar canvis" (`:435-440`, `doDiscard`), "Descartar sessió" (`:442-461`).
Si `readOnly`: cap botó, només `fitting.save.read_only` (`:425-428`).

---

# F4 — La graella

**F4-1.** ✅ **És `MeasureGrid`** (convergència G1): importat a `FittingDetail.jsx:8`, renderitzat a
`:734` (editable) i `:678` (lectura). **`MeasureTable.jsx` NO EXISTEIX** (`ls` de
`components/model/`); només se'n parla en comentaris.

**F4-2.** `MeasureGrid` **no té prop `mode`**. L'eix el construeix `fittingGridAdapter`:
`buildFittingGroups` (`fittingGridAdapter.jsx:15-25`) fa **un `group` per TALLA**, amb
`historyCols` = versions (`Base`, `Fit N`) i `activeLabel = "Fit actual"` (`:21-23`).
Props reals: `FittingDetail.jsx:734-740` (`editable`, `rows`, `groups`,
`leadCols={[regimeLeadCol(...)]}`, `onSave`, `onNomSave`).

**F4-3.** 🔴 **Pinta la taula PROPAGADA, no estadis de la base.** Cadena:
`create_piece_fitting` (`fitting/services.py:292-338`) clona **cada `GradedSpec` actiu**
(`:325-335`) —sortida del motor de grading per (versió, POM, talla)— a una `PieceFittingLine`.
El serializer les serveix totes (`fitting/serializers.py:210-277`); el front deriva `sizeLabels`
de totes les línies presents (`FittingDetail.jsx:547-548`).

**F4-4 — DIVERGÈNCIA AMB LA LLEI (FET, no opinió).** `DECISIONS.md §2` declara: *"El fitting com a
PANTALLA convocada amb totes les talles propagades QUEDA JUBILAT"* i *"tot el treball sobre totes
les talles → Grading/Escalat"*. El codi manté aquesta pantalla **viva i editable per talla**
(`fittingGridAdapter.jsx:39-42` cel·la activa per talla; `:144-150` desar per talla).
Contrast: `CheckMeasureEditor` (superfície Mesures) construeix **un sol group `base`**
(`CheckMeasureEditor.jsx:248-255`), coherent amb la llei.

**F4-5.** "Tornar a revisió" (`FittingDetail.jsx:713-716`): `setReviewMode(true)`. **Toggle de
client pur**: cap handler async, cap endpoint, cap navegació.

---

# F5 — Tancament i navegació de sortida

**F5-1.** Botó real: **"Gravar i tornar"** (`fitting.save.save_and_back`, `FittingDetail.jsx:431-434`),
handler `doSave` (`:183-209`).

**F5-2.** Seqüència: `toClose = grids.filter(hasSaveChanges)` (`:186`) → bucle
`pieceFittings.close(g.id)` (`:193`, `POST /piece-fittings/<id>/close/`, `endpoints.js:534`, sense
body) → `fittingSessions.seal(session.id)` (`:202`, `POST /fitting-sessions/<id>/seal/`,
`endpoints.js:522`) → `onSaved()` (`:207`).

**F5-3.** Backend: `close` → `views.py:450-456` → `close_piece_fitting`. `seal` → `views.py:327-334`
→ `seal_session` (`services.py:942-951`) → `_seal_session` (`services.py:634-656`).

**F5-4.** `_seal_session` (`services.py:634-656`): idempotent (`:638-639`); **GarmentSet: no tanca si
`session_can_advance` és fals** (`:640-641`); escriu `estat='Tancada'` + `finished_at` (`:642-647`);
`recompute_for_technicians` (no-fatal, `:648-655`); `_capture_duration` (`:656`).

**F5-5.** ⚠️ **Doble segellat.** `close_piece_fitting` ja segella (`services.py:467`) i el frontend
torna a cridar `/seal/` (`FittingDetail.jsx:202`). El segon és no-op. Si `toClose` és buit, el
segellat el fa **només** la crida del frontend.

**F5-6.** ⚠️ **Segellat parcial sense rollback.** Si el `close` d'una peça falla enmig del bucle
multi-peça, `doSave` fa `return` (`:195-198`) **sense segellar**: queden peces tancades i
`GradingVersion v+1` creades, i la sessió `Oberta`. Cap compensació.

**F5-7.** ⚠️ **Sortida silenciosa amb GarmentSet.** Si `_seal_session` retorna sense tancar
(`:640-641`), el frontend igualment fa `onSaved()` → `navigate(-1)` (`:207`). L'usuari marxa
creient que ha gravat i la sessió segueix `Oberta`.

**F5-8.** **Navegació:** `onSaved` = `() => navigate(-1)` (`:648`, `:665`) — enrere del navegador,
no una ruta fixa. La fletxa de capçalera sí té ruta: `EditorHeader onBack={() => navigate('/fittings')}`
(`:605`). `onDone` (descartar) **no navega** (`:649`, `:666`).
**No hi ha navegació distinta "després de segellar"**: peça i sessió es tanquen dins el mateix
`doSave` abans de navegar.

**F5-9.** **El segellat de GRADING (`aprovada=True`) no és part d'aquest flux.**
`seal_model_grading` (`fitting/services.py:547-567`) el crida **només** `advance_phase_gate`
(`tasks/services_d.py:47`). Gravar deixa una `GradingVersion v+1` **no aprovada**.

**F5-10.** 🔴 **Retorn de context: NO EXISTEIX (confirmat absent).** Cap `navigate` porta `state`
(`FittingDetail.jsx:605,648,665`; `FittingSessionList.jsx:420,447`). La llista no llegeix
`location.state`, ni `useSearchParams`, ni `sessionStorage`: filtres són `useState('')`
(`FittingSessionList.jsx:67-68`) i `openGroups` és `useState(new Set())` (`:70`).
En tornar amb `navigate(-1)`, **filtres, grups desplegats i scroll es reinicialitzen**.

---

# F6 — Divergència repo vs desplegat

**F6-1.** `HEAD` de staging = `b08baaf` (branca `dev`). `origin/dev` = `0eae56e`.
**`dev` va 2 commits per davant del remot** (`bae36c7`, `b08baaf`, bootstrap P1/P2), sense pushar.

**F6-2.** `main` = `685c944`. **`dev` i `main` han DIVERGIT**: `dev` va **657 endavant**, però
`main` té **14 commits que `dev` no té**.

**F6-3.** Les cadenes de convergència G1 **són a `origin/dev` i a `dev`, i cap és a `main`**:

| Commit | Data | `dev` | `origin/dev` | `main` |
|---|---|---|---|---|
| `9a370c1` P0 BackButton | 2026-06-23 12:22 | SÍ | SÍ | **NO** |
| `b12b36b` P0-fix | 2026-06-23 13:12 | SÍ | SÍ | **NO** |
| `90ed4fa` P1 Escalat→MeasureGrid | 2026-06-23 13:55 | SÍ | SÍ | **NO** |
| `f3300f1` P4 botó Editar | 2026-06-23 14:01 | SÍ | SÍ | **NO** |

**F6-4.** **Què serveix staging ara mateix:** nginx serveix **estàtic** des de
`/var/www/ftt-staging/frontend/dist` (`/etc/nginx/sites-enabled/ftt-staging:14,18`, `try_files` `:22`);
l'API va a `127.0.0.1:8001` (`:28,39,47`).

**F6-5.** **Datació del bundle:** `dist/index.html` = **2026-07-10 07:05:42 UTC**. L'últim commit que
toca `frontend/src` és `507aff9` (2026-07-10 06:58:38). **El bundle correspon a HEAD del frontend**
— les captures de l'Agus mostren codi actual, no un bundle ranci. Els 2 commits per davant
(`bae36c7`, `b08baaf`) són backend-only.

---

# F7 — Superfície Mesures com a destí

**F7-1.** Ruta: `models/:id` → `ModelSheet` (`App.jsx:243`), tab via `?tab=Mesures`
(`ModelSheet.jsx:413`). La ruta standalone `models/:id/mesures` **està jubilada** i només
redirigeix (`App.jsx:246`, `MesuresRedirect`).

**F7-2.** La graella real de Mesures és `CheckMeasureEditor` (`ModelSheet.jsx:475` treball, `:478`
consulta) → `MeasureGrid` (`CheckMeasureEditor.jsx:311`). Eix: **un sol group `base`**
(`CheckMeasureEditor.jsx:248-255`), `historyCols` = estadis (import/manual/checked),
`activeLabel` = "Real". **No existeix cap `MeasureGrid` "mode fitting" en aquesta superfície**
(confirmat absent: `groups` és sempre `[{key:'base'}]`).

**F7-3.** **Context que accepta avui** (`ModelSheet.jsx:96-100`):
- `tab` (`:96`), **`task_id` (`:97`)**, `mode=entry` (`:100`).
- **`session` / `fitting`: NO EXISTEIX (confirmat absent).** Cap `useLocation`, cap `location.state`
  a `ModelSheet.jsx` ni a `CheckMeasureEditor.jsx`.

**F7-4 — EL SEAM (localització, sense construir res).** Tres punts, i el codi ja els anomena:
- **Parse:** `ModelSheet.jsx:96-100`. El comentari `:95` diu literalment: *"El task_id/session
  entrants (J1b) es plomaran a sobre d'aquest mateix mecanisme més endavant."*
- **Consum:** efecte J1b `ModelSheet.jsx:252-266` (`activeTab==='Mesures' && taskParam` →
  `setEditTaskId`, `activeTaskRef`, `setEditing('Mesures')`).
- **Pas a la graella:** `ModelSheet.jsx:475` (`taskId={editTaskId}` a `CheckMeasureEditor`;
  props reals a `CheckMeasureEditor.jsx:173`: `model, onFeedback, onResolved, onBack, readOnly, taskId`).

**F7-5.** La branca de sessió de fitting **no té ni escriptor (origen) ni lector (destí)**: cap punt
del codi emet un enllaç `?tab=Mesures&session=…`.

---

# F8 — Matèria primera per a la fulla de convocatòria

Concepte: una **convocatòria** = conjunt de `FittingSession` amb el mateix `convocatoria` (UUID),
`fitting/models.py:258-260`, `db_index=True` (`:259`). Es crea a `schedule_bulk`.

## F8.a — Projecció de convocatòria

**F8a-1.** `GET /api/v1/fitting-sessions/` (`fitting/urls.py:43`, `views.py:97`), serializer
`FittingSessionListSerializer` (`serializers.py:90-116`). Camps (`:101-106,112-116`): `id`, `data`,
`fase(_display)`, `estat(_display)`, `model`, `garment_set`, `target{type,id,label}`,
`responsable(_nom)`, `n_peces` (annotat, `views.py:109`), `created_at`, **`convocatoria`**,
**`start_time`**, **`duracio_minuts`**, **`attendees_info`**.
Cobreix: model + hora + durada + estat + assistents + UUID, **per sessió**.

**F8a-2.** 🔴 **NO EXISTEIX cap endpoint que retorni UNA convocatòria com a unitat.**
`group_urls` (`fitting/urls.py:50-62`) té `reschedule`, `add-model`, `remove-model` i `attendees`.
El path `fitting-sessions/group/<uuid>/` **sí existeix** (`urls.py:60-61`) però mapeja a
`group_remove`, que és **`@api_view(['DELETE'])`** (`fitting/views.py:402-404`): un GET hi dona 405.
**Cap lectura de grup, per tant.**

**F8a-3.** 🔴 **La llista ni tan sols filtra per `convocatoria`.**
`filterset_fields = ['model','garment_set','fase','estat','data','responsable']` (`views.py:100`).
L'agrupació es fa **100% al client** (`FittingSessionList.jsx:108-124`).

**F8a-4.** `GET /api/v1/calendar/events/` (`planning/urls.py:23`, `views.py:214`) **ja agrupa per
convocatòria al backend** (`views.py:370-374`). Emet events amb `meta` = `{convocatoria, n_models,
model_id, model_ids, fase, lloc, estat/tancada, duracio_minuts, durada_real}` (`views.py:444,468`),
`titol` = `'Fitting · N models · fase'` (`:476`), `link='/fittings'`.
**No cobreix:** `model_ids` són **ids crus** (sense `codi_intern`/`nom`); cap estat de gate de peces;
cap watchpoint. Scope: sense `view_team_tasks`, només sessions on ets `attendees` (`:353-355`).

**F8a-5.** `GET /api/v1/plan/gantt/` (`planning/urls.py:30`, `views.py:647`): per model,
`fites` inclou `{tipus:'fitting', data, estat}` (`views.py:711-713`). Eix per **model**, sense hores
ni convocatòria.

**F8a-6.** Creació: `POST /api/v1/fitting-sessions/schedule-bulk/` (`views.py:241-242`, gated
`schedule_fittings`) → `schedule_bulk` (`services.py:190-274`). Retorna
`{convocatoria, n_sessions, created[], skipped, warnings}` (`views.py:274-284`).
Cridador: `ActionsMenu.jsx:156`.

## F8.b — Watchpoints per model

**F8b-1.** `GET /api/v1/watchpoints/` (`models_app/urls.py:48`, `views.py:291`), serializer
`WatchpointSerializer` (`models_app/serializers.py:226-240`). Camps: `id`, `model`, `task`,
`task_type_code`, `text`, `estat`, `dades` (JSON, read-only), `created_by(_nom)`, `created_at`,
`resolved_by(_nom)`, `resolved_at`, `resolution_note`.

**F8b-2.** Filtre: `filterset_fields = ['model','estat','task']` (`views.py:296`). Ús real:
`?model=<id>` (`ModelSheet.jsx:724`, `WatchpointsPanel.jsx:23`).
Estat: `ESTAT_CHOICES = [('open','Oberta'),('resolved','Resolta')]` (`models.py:926`).
Transicions: `POST .../resolve/` (`views.py:303-312`) i `.../reopen/` (`:314-322`),
cridades des de `WatchpointsPanel.jsx:37-38`.
**Model:** `Watchpoint` (`models_app/models.py:921-951`); `dades` no-null = watchpoint de sistema
(`:931-935`).

**F8b-3.** 🔴 **Watchpoint i convocatòria estan desconnectats.** El `Watchpoint` s'ancora a `model`
i opcionalment a `task` (`models.py:927-930`); **cap FK ni relació a `FittingSession` ni a
`convocatoria`** (grep a `models_app/`: cap referència a fitting/session/convocatoria).
Per a una fulla, s'han de consultar **model a model** via `?model=<id>`.

## F8.c — Incorporar models sobre la marxa

**F8c-1.** `POST /api/v1/fitting-sessions/group/<ciuuid:conv_uuid>/add-model/`
(`fitting/urls.py:53-54`), view `group_add_model` (`views.py:356-378`), servei `add_model_to_group`
(`services.py:868-910`). Body `{model_id, fase?, force?}`.
Cridador: `FittingSessionList.jsx:187` (modal `doAddModel`, `:182-194`), `endpoints.js:524`.

**F8c-2. Gating:** `_ScheduleFittingsPerm` (`views.py:357`) → capability `schedule_fittings`
(`views.py:45-46`, `accounts/capabilities.py:8`). Rols: `product_manager`, `manager`
(`capabilities.py:22-23`).

**F8c-3. Guards existents:**
- Convocatòria inexistent → `ValueError` (`services.py:875-876`) → 400 (`views.py:375-376`).
- Model ja al grup amb sessió viva → `SessionActionConflict` (`services.py:877-880`) → **409**
  (`views.py:367-368`).
- Solapament: `_skip_guard=False` (`services.py:906`) → `SessionOverlapError` → 409 amb `conflicts`
  (`views.py:369-371`); conflicte suau sense `force` → 200 `requires_confirmation` (`views.py:372-374`).
- Encadena l'hora al final de l'última sessió viva, per calendari d'empresa (`services.py:891-896`).
- Hereta `fase`, `data`, `duracio`, `responsable_id`, `attendee_ids` (`services.py:882-899`).

**F8c-4. Límits: NO EXISTEIXEN (confirmat absent).** Cap quota ni màxim de models per convocatòria
a `add_model_to_group` (`services.py:868-910`).

**F8c-5.** 🔴 **Cap gating per estat de la convocatòria.** `_group_live_qs` busca l'última sessió
**viva** (`services.py:882`; exclou `Tancada`/`Anullada`, `:775-781`). Si **totes** les germanes són
mortes, `last = None` → afegeix igualment amb `data = today`, `start_time = None`
(`services.py:883-890`). **Es pot afegir un model a una convocatòria totalment segellada**, i la
sessió nova neix `Programada` (`services.py:177`).
L'única barrera d'estat és sobre el **model** que s'afegeix, no sobre el grup.

---

# P0 — CENS DE L'HISTÒRIC DEL CUL-DE-SAC (2026-07-10, read-only)

Query read-only sobre `fhort`: `PieceFittingLine` amb `size_label != model.base_size_label`
i `|valor_real − valor_teoric| > 1e-6` (el criteri exacte de `services.py:359-364`).

| | n |
|---|---|
| `PieceFitting` | 5 |
| `PieceFittingLine` (totes) | 153 |
| **Línies NO-BASE rectificades (CO-1)** | **5** |
| (context) línies BASE rectificades | 3 |

**Totes 5 pertanyen a UN sol model:** `182 · BRW-26-SS-0002 · "[QA-SC] OLIVIA DRESS"`
(base `S`), el model dedicat a QA de Size Check. Sessions `136` i `137`, **totes dues
`Tancada`**.

| Sessió | POM | Talla | Teòric | Real | Δ |
|---|---|---|---|---|---|
| 137 | WA | M | 35.5 | 37.5 | +2.00 |
| 137 | WA | XS | 35.5 | 34.5 | −1.00 |
| 136 | HI | M | 49.0 | 49.5 | +0.50 |
| 136 | SS | M | 106.75 | 107.25 | +0.50 |
| 136 | SS | XS | 105.25 | 105.75 | +0.50 |

> **Veredicte del cens:** el cul-de-sac és **estructural, no massiu**. L'històric afectat són
> **5 línies de dades de QA**, cap de client, en sessions ja segellades. **No cal peça de
> migració a `ModelGradingOverride`**: es documenta i es descarta. Això tanca el punt
> "PER DECIDIR 1" amb dades, però la decisió d'esborrar-les (o deixar-les mortes on són)
> segueix sent de l'Agus. Aquesta diagnosi **no n'ha esborrat cap**.

---

# CADENES OBERTES (declarades)

| # | Cadena | On s'escapa |
|---|---|---|
| CO-1 | `PieceFittingLine.valor_real` no-base → **cap destí** | `fitting/services.py:363-364` |
| CO-2 | `ModelGradingOverride` té endpoint (`views.py:1666`) i **cap cridador** al front | `endpoints.js:63-64` |
| CO-3 | `GradingVersion.aprovada` orfe del gravat; només via gate | `tasks/services_d.py:47` |
| CO-4 | Segellat parcial sense rollback si el bucle de `close` falla | `FittingDetail.jsx:195-198` |
| CO-5 | GarmentSet: `_seal_session` pot no tancar i el front no ho detecta | `fitting/services.py:640-641` |
| CO-6 | Convocatòria: cap GET de grup, cap filtre `convocatoria` | `fitting/views.py:100`, `urls.py:50-62` |
| CO-7 | Watchpoint ↔ convocatòria sense relació | `models_app/models.py:927-930` |
| CO-8 | Context de sessió cap a Mesures: ni escriptor ni lector | `ModelSheet.jsx:96-100` |
| CO-9 | El motor (`propaga_ancoratges`, `generate_graded_specs`) NO s'ha auditat: zona intocable | `pom/grading_utils.py:560` |

---

# PER DECIDIR (Agus)

1. **Els valors no-base ja escrits a `PieceFittingLine` de sessions passades.** Existeixen a BD i no
   són a cap taula de mesures. ¿Es descarten en silenci, es migren a `ModelGradingOverride`, o es
   llisten abans de decidir? (No s'ha comptat quants n'hi ha: seria una query, no lectura de codi.)

2. **Què ha de passar quan el tècnic edita una cel·la no-base a la graella de fitting**, mentre la
   graella existeixi: ¿bloquejar la cel·la, redirigir l'escriptura a `set-size-override`, o avisar i
   descartar? Avui: escriu i perd, sense avís (F1-9).

3. **`hasSaveChanges` compta talles no-base** (`FittingDetail.jsx:146-150`). ¿El "Gravar" ha de
   distingir entre "hi ha canvis base" i "hi ha canvis que es perdran"?

4. **L'obertura automàtica en entrar** (`Programada → Oberta`, `FittingDetail.jsx:497-507`)
   és compatible amb el cicle aprovat (fulla → superfície de mesura)? Entrar a mirar muta l'estat.

5. **Doble segellat i segellat parcial** (F5-5, F5-6, F5-7): ¿el segellat de sessió l'ha de fer el
   `close` (backend) o el frontend? Avui el fan tots dos.

6. **La convocatòria com a recurs.** Per a la fulla cal decidir si s'exposa
   `GET /fitting-sessions/group/<uuid>/` (agregat), o només s'afegeix `convocatoria` a
   `filterset_fields` (`views.py:100`) i s'ensambla al client com ara.

7. **Watchpoints a la fulla.** No hi ha relació amb la sessió (F8b-3): la fulla els haurà de
   demanar model a model (N crides) o caldrà un agregat. Decisió d'arquitectura, no de volum.

8. **Afegir models a una convocatòria segellada** avui és possible (F8c-5). ¿És la "flexibilitat,
   cap regla dura" que vols, o és un forat?

9. **`main` i `dev` han divergit** (F6-2): `main` té 14 commits que `dev` no té. Cal reconciliar-ho
   abans de qualsevol deploy.

---

# FRONTERES (què NO s'ha de tocar en implementar)

**Aquest sprint (flux/navegació):**
- Entrada des de la llista i pas de context (F2, F5-10).
- Landing i branques de render (F3).
- El seam de `ModelSheet.jsx:96-100` per acceptar context de sessió (F7-4).
- Projecció de la fulla a partir del que ja existeix (F8a-1, F8a-4).

**Motor de grading (G6) — NO tocar aquest sprint:**
- `generate_graded_specs` (`pom/services.py:18`), `propaga_ancoratges`
  (`pom/grading_utils.py:560`), `bump_grading_version_and_generate` (`pom/services.py:505`),
  `_apply_rule`, `derive_break_fields`.
- `GradingVersion`, `GradedSpec`, `ModelGradingOverride`, `ModelGradingRule`.
- **Jubilar la graella propagada del fitting** i el destí de `PieceFittingLine` és feina de G6, no
  d'aquest sprint. `DECISIONS.md §2` ho declara **condició bloquejant**: *"No es jubila res del
  fitting fins que el seu equivalent és viu a Grading"*.
- `close_piece_fitting:469` i `resolve_size_check:230` estan marcats a `DECISIONS.md §2` com a
  *"codi a JUBILAR/RECONSTRUIR dins el zoom-out, NO a retocar ara"*.

**Relació amb el pendent G1 ("edició via tasca / gating de `/mesures`"):**
- El consum de `task_id` (`ModelSheet.jsx:252-266`) ja existeix i registra `activeTaskRef` per
  pausar la tasca en sortir. Qualsevol context de sessió de fitting s'ha de **plomar sobre aquest
  mateix mecanisme** (el comentari `:95` ho anticipa), no crear-ne un de paral·lel.
- La ruta standalone `/models/:id/mesures` ja està jubilada (`App.jsx:246`): no ressuscitar-la.

**Zones intocables per `CLAUDE.md`:** POMs, grading engine, motor de patrons.

---

*Cap línia de codi tocada en aquesta sessió. Tots els FETS verificats llegint el fitxer citat;
les afirmacions d'alt risc dels investigadors han estat re-verificades pel director.*
