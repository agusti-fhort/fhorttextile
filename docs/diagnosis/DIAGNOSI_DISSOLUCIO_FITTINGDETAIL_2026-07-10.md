# DIAGNOSI — Dissolució de FittingDetail cap a Mesures + bug gravat (Bloc X)

> Data: 2026-07-10 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`.
> HEAD de la investigació: `772c846`. **Cap línia de codi tocada.**
> Convenció: `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi (no especulat).**
> Base: `DIAGNOSI_FLUX_FITTING_NAV.md` + sprint P0-P5 (`bdb5fc0..1a5f57b`).
> Equip: director-investigacio + investigador-codi ×4 + documentador.

**Nota de mètode (desviació conscient, declarada).** El brief demanava *reproduir* el bug a
staging. Sota Patró A, clicar "Gravar i tornar" és una **escriptura irreversible** (close +
seal muten la sessió 139 i el grading del model). El Bloc X s'ha resolt sense tocar res:
**logs reals** del fallo que ja va provocar l'Agus (`journalctl -u ftt-staging.service`),
**anàlisi estàtica** del camí, i **SELECTs** sobre el tenant `fhort`. Cap POST/PATCH emès.
La causa és determinista i està provada amb dades de BD, no inferida.

---

## Resum executiu

1. **🔴 El bug X NO té res a veure amb el sprint P0-P5.** El 400 el llança el **guard D-1**
   (`pom/services.py:540-544`), que és **preexistent**. El model `FTT-FW27-0001` (185) té la
   seva `GradingVersion` activa **`v5 aprovada=True`** (segellada per un gate de fase). Qualsevol
   `close` amb canvis a la base → `ValueError` → `views.py:457-458` → **400**.
2. **🔴 El 400 no és net: deixa dades escrites.** `close_piece_fitting` (`fitting/services.py:406`)
   **no té `transaction.atomic`** i `ATOMIC_REQUESTS` **NO EXISTEIX** al projecte. Quan D-1 peta,
   `BaseMeasurement` **ja s'ha escrit** i el Welford **ja s'ha alimentat**. Provat a BD.
3. **🔴 Conseqüència: la base i el grading han DIVERGIT en silenci.** `BaseMeasurement` pom 273
   = **60.7** (`origen=FITTED`), però el `GradedSpec` actiu de la talla base = **60.5**.
   `model.measurements_version` segueix a **2**. Tot el que llegeix grading (fitxa tècnica,
   Escalat, producció) veu el valor vell. Cap avís.
4. **🔴 Cada reintent contamina l'estadística.** L'Agus va clicar **5 vegades**; el Welford
   (`ClientMesuraPerfil`) té **`n_mostres=5`** per a una sola presa real. `consolidate_base_from_fitting`
   compara contra `valor_teoric` de la línia, no contra `BaseMeasurement`, i per això torna a
   "consolidar" a cada intent.
5. **🔴 El client amaga la causa.** El backend retorna `{'error': "GradingVersion v5 està aprovada…"}`,
   però el `catch` de `doSave` (`FittingDetail.jsx:204-211`) **ignora el body sencer** i pinta un text
   fix, "Error en gravar la peça FTT-FW27-0001". Per això el missatge no diu res.
6. **Segon bug independent, també als logs (9 ocurrències): `create-piece` → 500.** El botó
   "+ Afegir peça" (`FittingDetail.jsx:750-755`) es pinta sempre que `session.model`, sense mirar si
   la peça ja existeix; `create_piece_fitting` fa `create` nu (`services.py:345-350`) contra un
   `unique_together = [('session','model')]` (`fitting/models.py:331`), i la view no captura
   `IntegrityError`. **Això respon Y6: l'endpoint viu, el botó viu, el guard no existeix.**
7. **Radi del bloqueig D-1: 2 models** (182 i 185). El 185 té **2 sessions vives**. Un cop un model
   passa el gate de fase, **cap fitting seu es pot tornar a gravar** fins que algú reobri el grading.
8. **La dissolució és viable amb el que ja hi ha.** El seam de `task_id` és el patró literal a copiar
   (`MesuresRedirect`, `App.jsx:74-79`); `regimeLeadCol` **ja té el 3r arg `readOnly`**; el nom es fa
   read-only passant `onNomSave={undefined}` (patró ja usat a `CheckMeasureEditor.jsx:312`).
   Falta un flag de granularitat: avui `readOnly` a Mesures és **tot-o-res**.
9. **Y2 respost: els Watchpoints "Cap" són DADA REAL, no crida trencada.** El client envia
   `?estat=open` i la choice del backend és `'open'` (`models_app/models.py:926`). A BD hi ha **0
   watchpoints oberts** per als 5 models de la convocatòria.

---

# BLOC X — Bug "Error en gravar la peça" (causa exacta)

## X0 — L'escena, amb dades

| Fet | Valor | Font |
|---|---|---|
| Sessió | `139`, estat **Oberta** | BD |
| Model | `185` · `FTT-FW27-0001` · `base_size_label='L'` | BD |
| Peça | `PieceFitting 19` · `closed_at=None` · `gate='Pendent'` | BD |
| GradingVersion | `65` = **v5**, `is_active=True`, **`aprovada=True`**, `size_fitting=76` | BD |
| Línies base amb canvi | `line680` pom 273: 60.5→**60.7** · `line687` pom 275: 60.0→**60.2** | BD |
| Intents de gravat | **5** × `Bad Request: /api/v1/piece-fittings/19/close/` | `journalctl` |

## X1 — Quina crida falla, amb status i body

**X1-1.** La crida que falla és **`POST /api/v1/piece-fittings/19/close/`** → **400**.
`journalctl -u ftt-staging.service`: `Bad Request: /api/v1/piece-fittings/19/close/`, **5 ocurrències**
(14:52:33, 14:52:41, 14:52:42, 14:52:44, 14:54:39).

**X1-2.** No falla el `seal`. `doSave` (`FittingDetail.jsx:192-232`) fa `return` dins el `catch` del
bucle de `close` (`:210`) i **mai arriba** a `fittingSessions.seal` (`:216`). La sessió queda `Oberta`
— coherent amb la BD.

**X1-3.** Hi ha **una sola peça** (`PieceFitting 19`); no és un problema de "quina de N".

**X1-4. Body de la resposta:** `views.py:457-458` →
```python
except ValueError as e:
    return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
```
Contingut real: `{"error": "GradingVersion v5 està aprovada (segellada a producció); cal reobertura explícita per superar-la."}`

**X1-5. 🔴 El client no el llegeix.** `FittingDetail.jsx:204-211`:
```js
} catch (e) {
  setError(done
    ? t('fitting.save.partial_close', { done, total: toClose.length })
    : t('fitting.save.save_error', { piece: g.model?.codi || g.id }))
  setBusy(false); return
}
```
`e` **es captura i mai es llegeix**. `fitting.save.save_error` (`ca.json:1902`) = *"Error en gravar la
peça {{piece}}."*. El mateix fitxer **sí** sap llegir el body en altres llocs: `:265`
(`e?.response?.data?.error`) i `:638` (`err?.response?.data?.detail`). `doSave` no usa cap dels dos.
El client HTTP és axios (`api/client.js:1-26`); l'interceptor només tracta el 401, així que
`err.response.data` és accessible i ningú el consumeix.

## X2 — Log del servei a l'instant del fallo

**X2-1.** `Bad Request` és un log de `django.request` de **nivell WARNING sense traceback**: el
`ValueError` **el captura la view**, no arriba a `handler500`. Per això **no hi ha traceback** del bug X
als logs. Confirmat: cap `Traceback` als segons 14:52:33-14:54:39 associat a `close/`.

**X2-2.** Els únics tracebacks de la finestra són del **segon bug** (`create-piece`, §X6), amb
`django.db.utils.IntegrityError`.

**X2-3.** El senyal F1 sí va deixar rastre a BD, amb la marca de temps del **primer 400**:

| Log | POM | Canvi | Motiu | `created_at` |
|---|---|---|---|---|
| `log237` | 273 | 60.5 → 60.7 | `Fitting · sessió 139 · peça 19` | **14:52:33.235787** |
| `log238` | 275 | 60.0 → 60.2 | `Fitting · sessió 139 · peça 19` | **14:52:33.249230** |

`Bad Request` al log del servei: **14:52:33**. **Les mesures es van gravar, i acte seguit la crida va
respondre 400.**

## X3 — Contrast amb el sprint P0-P5: el guard P1a **no** hi té part

**X3-1.** Hi ha **dos 400 diferents** al mateix flux i el client no els distingeix:

| Guard | Origen | Clau del body | Estat |
|---|---|---|---|
| P1a — eix no-base | `fitting/services.py:41-54` → `views.py:489-492` | `detail` | **no dispara aquí** |
| D-1 — grading aprovat | `pom/services.py:540-544` → `views.py:457-458` | `error` | **és el que dispara** |

**X3-2. ¿Pot P1b generar encara un PATCH/propagar a una talla no-base? NO.** Revisat
`fittingGridAdapter.jsx` sencer (1-152) i `FittingDetail.jsx:570-590`:
- **(a)** `buildFittingRows` (`fittingGridAdapter.jsx:32-55`) només construeix `cells[baseLabel]`
  (`:35-44`). `active.lineId` és **sempre** la línia de la talla base. No hi ha cel·la activa per a cap germana.
- **(b)** La propagació a germanes la fa el **backend** (`fitting/views.py:561-568`). El client
  (`makeFittingOnSave`, `fittingGridAdapter.jsx:146-152`) fa **una sola crida** amb el `lineId` de la
  base: STEP → `PATCH`; LINEAR → `propagar`. **El client no fa cap PATCH a germanes.**
- **(c)** `buildEscalatGroups`/`buildEscalatRows` només els usa `PropagatedEditor.jsx:7,37-38`, i
  **mai** amb `makeFittingOnSave`. `FittingDetail.jsx:10` només importa les 3 funcions de fitting.
- **(d)** La subtaula "Canvis" (`FittingDetail.jsx:340-392`) és render pur; **cap crida**.
- **(e)** `onNomSave` (`:621`) escriu `nom_fitxa` a `baseMeasurements.update`; no toca `valor_real` ni el `close`.

> **Veredicte X3: el 400 NO ve de P1a.** No existeix cap camí viu client→PATCH no-base. Els
> commits `bf61c95`/`77e3c2f` són correctes i no han introduït el bug.

**X3-3 — el que P1 SÍ va fer (matís important).** Abans de P1b, la graella pintava totes les talles. Si
el tècnic només tocava no-base, `changed=0` → `bump` **no es cridava** → D-1 **no saltava** → 200 mut
(i pèrdua silenciosa: F1-9 de la diagnosi anterior). Amb P1b la graella **només** ofereix la base, així
que tota edició és base → `changed≥1` → `bump` → **D-1 salta sempre**. El sprint no va crear el guard:
va **fer-lo abastable**. Va convertir una pèrdua silenciosa en un error dur — que és millor, però ara
el error dur és el que bloqueja l'Agus.

## X4 — `hasSaveChanges`: correcte, no és la causa

**X4-1.** `FittingDetail.jsx:153-159`:
```js
function hasSaveChanges(grid) {
  const base = (grid.model?.base_size_label || '').trim()
  return (grid.lines || []).some(
    l => (!base || l.size_label === base) &&
      l.valor_real != null && Math.abs(Number(l.valor_real) - Number(l.valor_teoric)) > 1e-6)
}
```

**X4-2.** `grid.model` **sí** existeix al payload: `PieceFittingGridSerializer.get_model`
(`fitting/serializers.py:206-211`) serveix `base_size_label` i `size_run_model`; el camp `model` és a
`fields` (`:203`). Per al model 185, `base='L'` i el filtre funciona.

**X4-3.** El `close` es crida **legítimament**: la línia base `L` té `valor_real ≠ valor_teoric`. El filtre
no deixa passar cap PATCH orfe. **`hasSaveChanges` no és la causa.**

**X4-4 — bug latent anotat (no dispara avui).** Si un model no tingués `base_size_label`, `base===''` i
`(!base || …)` deixaria passar **totes** les talles. Però en aquest cas el guard backend P1a també es
desactiva (`services.py:52-53`), i **avui cap model és així**. Anotat, no tocat.

## X5 — 🔴 La troballa que el brief no demanava: el 400 no és atòmic

**X5-1.** `close_piece_fitting` (`fitting/services.py:406`) **no té `@transaction.atomic` ni
`with transaction.atomic()`**. Al fitxer n'hi ha a `:246`, `:515`, `:719`, `:1002` — **cap embolcalla el
close**. `ATOMIC_REQUESTS`: **NO EXISTEIX** (grep a `backend/fhort/`: buit). `bump_grading_version_and_generate`
tampoc n'obre cap (`grep -n "atomic" pom/services.py`: buit).

**X5-1b — no és estil de casa, és un descuit.** El veí `propagar` **sí** embolcalla la seva escriptura:
`with transaction.atomic():` a `fitting/views.py:561`, just abans d'actualitzar les germanes (`:562-568`).
I `discard_piece_fitting` també (`services.py:515`). L'escriptura més cara del mòdul — la que promociona a
`BaseMeasurement` i versiona el grading — és **l'única sense transacció**.

**X5-2. Ordre real d'execució i punt de trencament:**

| Pas | Línia | Acció | Estat després del 400 |
|---|---|---|---|
| 1 | `services.py:419` | `consolidate_base_from_fitting` → escriu `BaseMeasurement` | ✅ **COMMITED** |
| 2 | `signals.py:215` | senyal F1 → `MeasurementChangeLog` | ✅ **COMMITED** |
| 3 | `services.py:423-436` | Welford `update_client_profile` | ✅ **COMMITED** |
| 4 | `services.py:439-445` | `bump_grading_version_and_generate` | 💥 **ValueError (D-1)** |
| 5 | — | `GradingVersion v+1` | ❌ mai creada |
| 6 | — | `measurements_version++` | ❌ mai incrementat |
| 7 | — | `generate_graded_specs` (re-propagació) | ❌ mai executat |
| 8 | `services.py:467` | `_seal_session` | ❌ mai arribat |

**X5-3. 🔴 Prova a BD — la base i el grading han divergit:**

| Objecte | POM 273 | POM 275 |
|---|---|---|
| `BaseMeasurement` (`origen=FITTED`) | **60.7** | **60.2** |
| `GradedSpec` v65 talla `L` (`is_active=True`) | **60.5** | **60.0** |
| `model.measurements_version` | **2** | **2** |
| `GradedSpec.generated_from_version` | **2** | **2** |

El model diu que la seva base és 60.7; el grading actiu — que és el que llegeixen fitxa tècnica,
Escalat i producció — encara diu 60.5. **Sense cap avís i sense cap versió nova.**

**X5-4. 🔴 Prova a BD — el Welford està contaminat.** `ClientMesuraPerfil` (`codi_client=''`,
`garment_type=63`, talla `L`): **`n_mostres=5`** per als POMs 273 i 275, `desviacio=0.0`.
Hi va haver **5 intents de close** i **una sola presa real**. `consolidate_base_from_fitting`
(`services.py:368`) compara `valor_real` vs **`valor_teoric` de la `PieceFittingLine`** (`:388-389`),
que no canvia mai; per tant a cada reintent torna a "consolidar" les mateixes 2 línies i torna a
alimentar el Welford. **El log F1 sí és idempotent** (`signals.py:238-240` només escriu si el valor
canvia: per això només hi ha 2 logs, no 10). **El Welford no ho és.**

**X5-5.** `PieceFitting 19` segueix `closed_at=None`, `gate='Pendent'`, i la sessió `Oberta`.
Consistent: el pas 8 mai s'executa.

## X6 — Segon bug als logs: `create-piece` → 500 (respon Y6)

**X6-1.** `Internal Server Error: /api/v1/fitting-sessions/139/create-piece/`, **9 ocurrències**.
`django.db.utils.IntegrityError: duplicate key value violates unique constraint
"fitting_piecefitting_session_id_model_id_8766b0c1_uniq"` · `DETAIL: Key (session_id, model_id)=(139, 185) already exists.`

**X6-2. Cadena completa:**
- Constraint: `PieceFitting.Meta.unique_together = [('session','model')]` (`fitting/models.py:331`).
  Sense `name=` explícit → el nom el genera Django.
- `create_piece_fitting` (`fitting/services.py:319-365`) fa **`PieceFitting.objects.create(...)` nu**
  (`:345-350`), **no** `get_or_create`. **Cap guard previ d'existència** (confirmat absent al rang).
- La view `create_piece` (`fitting/views.py:151-162`) **només captura `ValueError`** (`:159`);
  `IntegrityError` propaga → **500**, no un 400 net. `grep -n "IntegrityError"` a `views.py`/`services.py`: buit.

**X6-3. Qui el dispara (dos botons, un protegit i un no):**
- `registrarMesures` (`FittingDetail.jsx:260-270`) → el seu botó (`:329-332`) només es pinta si
  `!hasPieces` (`hasPieces = pieces.length > 0`, `:175`). **Protegit.**
- **"+ Afegir peça"** (`FittingDetail.jsx:750-755`, clau i18n `fitting.piece.create`, `ca.json:1859`) →
  es pinta **sempre que `session.model` sigui truthy** (`:750`), sense mirar si la peça ja existeix.
  Crida `createPiece` (`:562-568`). **Aquest és el que peta.**

> **Veredicte Y6: l'endpoint respon i el botó crida.** No és mort de cap costat. És **viu i sense guard**:
> a la segona pulsació dona 500. La peça ja existia (PF 19).

## X7 — Radi del bloqueig D-1

**X7-1.** `GradingVersion` amb `is_active=True AND aprovada=True`: **2** (de 4 actives totals).
Models afectats: **182** (`BRW-26-SS-0002`, el model de QA de Size Check) i **185** (`FTT-FW27-0001`).

**X7-2.** El model **185 té 2 sessions vives**; el 182, cap.

**X7-3. Qui posa `aprovada=True`:** `seal_model_grading` (`fitting/services.py:574`), cridat
**únicament** per `advance_phase_gate` (`tasks/services_d.py:46-47`). Coherent amb F5-9 de la diagnosi
anterior.

**X7-4. La regla estructural que se'n deriva:** **un cop un model passa el gate de fase, cap fitting
seu es pot tornar a gravar.** `close_piece_fitting` sempre passa `allow_reopen_sealed=False`
(paràmetre per defecte, `services.py:406-407`; el `close` de la view no el passa mai, `views.py:456`).
No hi ha cap UI que ofereixi la reobertura explícita: **`allow_reopen_sealed=True` NO té cap cridador
des del frontend** (grep a `frontend/src/`: buit).

## X8 — Conclusió del Bloc X (causa exacta)

> **Causa primària:** `backend/fhort/pom/services.py:540-544` — guard D-1 llança `ValueError` perquè
> la `GradingVersion` activa del `SizeFitting` 76 és `v5 aprovada=True`. Es converteix en HTTP 400 a
> `backend/fhort/fitting/views.py:457-458`.
>
> **Causa que el fa invisible:** `frontend/src/pages/FittingDetail.jsx:204-211` — el `catch` descarta
> `e` i pinta `fitting.save.save_error` (`ca.json:1902`) sense llegir `err.response.data.error`.
>
> **Agreujant (dany real, no cosmètic):** `backend/fhort/fitting/services.py:406` — `close_piece_fitting`
> no és atòmic; el pas 1 (`BaseMeasurement`) i el pas 3 (Welford) **commiten** abans que el pas 4 peti.
> Resultat viu a staging: `BaseMeasurement` 60.7 vs `GradedSpec` 60.5, i `n_mostres=5` per 1 presa.
>
> **Bug independent, mateixa pantalla:** `backend/fhort/fitting/services.py:345-350` (`create` nu) +
> `backend/fhort/fitting/views.py:159` (no captura `IntegrityError`) + `frontend/src/pages/FittingDetail.jsx:750`
> (botó sense guard) → 500 a `create-piece`.
>
> **NO s'ha arreglat res** (Patró A). **NO s'ha esborrat ni corregit cap dada de staging**, inclosos el
> Welford contaminat i la divergència base↔grading.

---

# BLOC Y — Cens per a la dissolució (FittingDetail → Mesures)

## Y1 — Inventari de `FittingDetail.jsx` (791 línies)

Destí: **SOBREVIU** (ja existeix a Mesures) · **ES MOU** (cal portar-lo) · **MOR** (desapareix amb la pàgina)
· **ES QUEDA** (només a la vista read-only de sessions Tancades).

| Bloc UI | `FittingDetail.jsx` | Endpoint / crida | Edit? | Destí |
|---|---|---|---|---|
| `EditorHeader` | `645-679` | `fittingSessions.get` (`endpoints.js:516`) | RO | **SOBREVIU** — `CheckMeasureEditor.jsx:309` ja l'usa |
| ↳ franja context sessió (gate, estat, col·lecció, client, responsable, lloc) | `651-675` | del detall de sessió | RO | **ES MOU** — no té equivalent a CME |
| ↳ `EditableContextField` (persona, lloc) | `31-49` def · `655,657` | `fittingSessions.update` PATCH (`endpoints.js:519`) | **Editable** | **ES MOU** |
| ↳ icones Info/Foto/Nota | `659-675` | Info→`ModelFilesPanel`; Foto/Nota `wired:false` (stubs) | mixt | Info **ES MOU** · stubs **MOREN** |
| `ModelFilesPanel` (patrons/marcades/docs) | `52-118` def · `682` | `modelFitxers.list` ×3 | RO | **ES MOU** (CME té `DependencyPanel`, ≠) |
| **Selector de peça** (chips + "+ Afegir peça") | `732-760` | `session.piece_fittings`; `createPiece` (`endpoints.js:521`) | Editable | **ES MOU** (Y9: és la clau del GarmentSet) |
| **MeasureGrid** (graella base) | `767-786` | `pieceFittings.get` (`endpoints.js:540`); save: `pieceFittingLines.update`/`.propagar` (`:549,552`) | **Editable** | **SOBREVIU** (mateix component; adapter diferent) |
| ↳ leadCol règim | `627-639` · `781` | `models.setPomRegim` (`endpoints.js:58`) | Editable | **SOBREVIU read-only** (Y5) |
| ↳ nomenclatura (`onNomSave`) | `621` · `782` | `baseMeasurements.update` (`endpoints.js:86`) | Editable | **SOBREVIU read-only** (Y4) |
| **ReviewScreen** (contenidor) | `161-491` def · `686-715` | — | mixt | **MOR com a pantalla** |
| ↳ card "Taula de mesures" | `316-337` | `onShowGrid` local / `createPiece` | acció | **MOR** (P2 ja va fer landing directe) |
| ↳ card **CANVIS** (POM×talla) | `339-392` (`changedRows` `126-143`) | grids de `pieceFittings.get` | RO | **ES MOU** — cap equivalent a CME |
| ↳ card **OBSERVACIONS** (textarea) | `394-407` | `fittingSessions.update({notes})` | **Editable** | **ES MOU** — cap equivalent |
| ↳ card **IMATGES** | `409-431` | `client.post('/api/v1/fitting-photos/')` (`:289`); `fittingPhotos.list` (`endpoints.js:557`) | **Editable** | **ES MOU** (Y3) |
| ↳ card "Enviar a" (stub mail) | `433-436` | `{false && …}` codi mort | — | **MOR** |
| **Gravar i tornar** (`doSave`) | `192-232` · `454-457` | `pieceFittings.close` (`:542`) + `fittingSessions.seal` (`:530`) | acció | **ES MOU** (és el "close+seal" del disseny) |
| **Descartar canvis** (`doDiscard`) | `235-249` · `458-463` | `pieceFittings.discard` (`:544`) | acció | **ES MOU** |
| **Descartar sessió** (`doDiscardSession`) | `251-257` · `464-484` | `fittingSessions.discardSession` (`:529`) | acció | **ES MOU** |
| **Registrar mesures** | `260-270` · `329-332` | `createPiece` (`:521`) | acció | **MOR** (fusiona amb "+ Afegir peça") |
| **Veure/editar taula** | `320-323` | local (`setReviewMode(false)`) | acció | **MOR** |
| **Tornar a revisió** | `756-759` | local (`setReviewMode(true)`) | acció | **MOR** |
| **Split 40/60 lectura** (segellada) | `700-730` | `pieceFittings.get` | RO | **ES QUEDA** (Y10) |

**Y1-1.** Blocs **sense cap equivalent** a `CheckMeasureEditor.jsx`: franja de context de sessió,
selector de peça, ReviewScreen sencer (Canvis · Observacions · Imatges) i tots els botons de cicle de
vida de sessió.

**Y1-2.** A l'inrevés, `CheckMeasureEditor` aporta blocs que el fitting **no té**: `DependencyPanel`
(`:310`), `WatchpointsPanel` (`:324`), `RegleEditCell` (`:295`), slot Decisió/Nota (`:274`), columna
Tolerància, i la resolució Acceptat/Descartat. **Cadena oberta CO-Y1:** en mode sessió, ¿què passa amb
aquests blocs? No està decidit.

## Y2 — Watchpoints "Cap": **dada real**, no crida trencada

**Y2-1.** Ruta `App.jsx:259` → component `FittingConvocatoriaSheet.jsx:27`.

**Y2-2.** La fulla **no usa `WatchpointsPanel`**. Fa una crida per model (dedup per `modelId`):
`FittingConvocatoriaSheet.jsx:45-49` → `watchpoints.list({ model: id, estat: 'open' })`
(`endpoints.js:93`) → `GET /api/v1/watchpoints/?model=<id>&estat=open`.
Render de "Cap": `:105-106` (`wps.length === 0` → `t('fitting.sheet.no_watchpoints')`).

**Y2-3.** Backend: `WatchpointViewSet` (`models_app/views.py:291`), `filterset_fields = ['model','estat','task']`
(`:296`). `ESTAT_CHOICES = [('open','Oberta'),('resolved','Resolta')]` (`models_app/models.py:926`),
`default='open'` (`:936`).

**Y2-4. El mismatch sospitat NO EXISTEIX.** El client envia el **valor** `open`, no el label `Oberta`.
El filtre casa.

**Y2-5. Verificació a BD.** Convocatòria de la sessió 139 = `79e06e8a-bb93-480f-a1d4-ed80a713c9fe`,
5 sessions → models **162, 168, 169, 170, 185**. Watchpoints oberts per model: **162→0, 168→0 (1 resolt),
169→0, 170→0, 185→0**. Totals del tenant: `open=3`, `resolved=2` — els 3 oberts són d'altres models.

> **Veredicte Y2: "Cap" és cert. No hi ha bug.** Cadena tancada.

## Y3 — Imatges (`FittingPhoto`)

**Y3-1. Model:** `fitting/models.py:362`. Camps: `session` FK→`FittingSession` `CASCADE`
`related_name='photos'` (`:367-369`); **`piece_fitting` FK→`PieceFitting` `SET_NULL, null=True, blank=True`**
(`:370-373`); `fitxer = ImageField(upload_to='fitting_photos/%Y/%m/')` (`:374`); `caption` (`:375`);
`created_at` (`:376`).
**Penja de la SESSIÓ (obligatori); el vincle a la peça és OPCIONAL.** No penja del model.

**Y3-2. Endpoint:** `POST /api/v1/fitting-photos/` → `FittingPhotoViewSet` (`fitting/views.py:571-582`),
mixins List/Create/Retrieve/Destroy (**sense update**). Permission `[IsAuthenticated]` (`:576`) — **cap
gate de sessió ni de fase**. Parsers `[MultiPartParser, FormParser]` (`:578`). `filterset_fields =
['session','piece_fitting']` (`:580`). Serializer `fitting/serializers.py:63-69`.

**Y3-3. Qui el crida:** pujada inline a `FittingDetail.jsx:281-294` — `client.post('/api/v1/fitting-photos/', fd)`
(`:289`) amb `fd.append('session', session.id)` + `fd.append('fitxer', f)` (`:287-288`). **No adjunta
`piece_fitting` ni `caption`.** Un POST per fitxer (`Promise.all`, `:285-290`). Llista: `fittingPhotos.list({session})`
(`:181`, `:277`). Miniatures: `:419-430`.

**Y3-4. Component dedicat: NO EXISTEIX (confirmat absent).**
`grep -rln "Photo\|Foto\|fittingPhotos\|fitting-photos" frontend/src/components/ frontend/src/pages/` →
només `FittingDetail.jsx`. Tota la lògica és inline dins `ReviewScreen`.

**Y3-5. 🔴 TROBALLA TRANSVERSAL.** `endpoints.js:555-558` documenta `fittingPhotos` com *"pujada ajornada
a B2"* i **només exposa `list`**. La pujada real **es salta el mòdul** amb un `client.post` cru.
**En dissoldre la pàgina, la pujada es perd si no es porta explícitament**: no hi ha helper a `endpoints.js`.

**Y3-6. Contracte a preservar** (mateixa dada, nou lloc): payload multipart `{session, fitxer}`; resposta
`{id, session, piece_fitting, fitxer(URL), caption, created_at}`; llistat `GET ?session=<id>`, el front
llegeix `r.data.results || r.data`.

**Cadena oberta CO-Y3:** la foto s'ancora a `session`, però la superfície nova s'ancora a `model` +
`fitting_session_id`. El `piece_fitting` opcional **ja permetria** ancorar per peça i ningú l'omple.
**PER DECIDIR.**

## Y4 — Nomenclatura editable

**Y4-1. L'endpoint `poms/<id>/nomenclatura/` EXISTEIX però NO és el que fa servir la graella.**
View `pom/wizard_views.py:377` (`edit_pom_nomenclature_view`, PATCH); URL `pom/urls.py:45`.
Edita `POMMaster.codi_client`/`nom_client` — **el POM tenant COMPARTIT**.
**A `endpoints.js`: NO EXISTEIX (confirmat absent)** — `grep -rn "nomenclatura/" frontend/src/`: buit.
**És codi backend orfe des del front.**

**Y4-2. `DIAGNOSI_P7_NOMENCLATURA.md`: NO EXISTEIX** (ni a l'arrel ni a `arxiu/`;
`find docs/diagnosis -iname "*P7*NOMENCL*"` → buit). La vigent relacionada és
`docs/diagnosis/DIAGNOSI_NOMENCLATURA_ALIES_2026-07-08.md`.

**Y4-3. El contracte REAL de la graella** és `nom_fitxa` **per-model**, no el POM compartit:
- `FittingDetail.jsx:621` → `baseMeasurements.update(bmId, { nom_fitxa: value || null })`, passat a `:782`.
- `CheckMeasureEditor.jsx:238-241` → **idèntic** (+ `.then(load)`), passat a `:312`.
- Tots dos → `PATCH /api/v1/base-measurements/<id>/` (`endpoints.js:86`). **Mateix contracte.**

**Y4-4. Component i guard exacte.** `MeasureGrid` **no té prop `readOnly`**. La nomenclatura és editable
si i només si hi ha `onNomSave`:
- `NomCell` (`MeasureGrid.jsx:124`), guard `canEdit` a `:129` = `editable && bmId != null && onNomSave && !editCodi` (camí del fitting).
- `CodiCell` (`MeasureGrid.jsx:168`), guard `canEdit` a `:170` = `editable && editCodi && bmId != null && onNomSave` (camí de Mesures).

> **Guard read-only exacte (component + prop):** passar **`onNomSave={undefined}`**.
> El patró **ja existeix**: `CheckMeasureEditor.jsx:312` fa `onNomSave={readOnly ? undefined : onNomSave}`.
> `FittingDetail.jsx:782` avui passa `onNomSave={onNomSave}` **sense cap guard**.

**Y4-5. TROBALLA TRANSVERSAL.** `edit_pom_nomenclature_view` toca el POM **compartit del tenant**;
`nom_fitxa` és **per-model**. Confondre'ls trencaria l'aïllament per model.

## Y5 — Règim (`ModelGradingRule`)

**Y5-1. El control.** `regimeLeadCol` — `fittingGridAdapter.jsx:71`:
```js
export function regimeLeadCol(t, onRegimChange, readOnly = false)
```
Render `:76-92`: si `readOnly` → text pla `row.logica` (`:77`); si no → `<select>` LINEAR/STEP (`:79-91`).
**El 3r argument JA és el guard read-only.**

**Y5-2. Crida.** `endpoints.js:58` → `POST /api/v1/models/<id>/pom/<pom>/regim/` → URL
`models_app/urls.py:208` → view `set_pom_regim_view` (`models_app/views.py:2493`), UPSERT de
`ModelGradingRule`. **Confirmat.**

**Y5-3. Cridadors al frontend (cens complet):**
| Fitxer:línia | Superfície | Guard |
|---|---|---|
| `FittingDetail.jsx:630` (`onRegimChange` `:627`) | fitting, graella de treball | `regimeLeadCol(t, onRegimChange, **false**)` a `:781` |
| `FittingDetail.jsx` (mateix handler) | fitting, review read-only | `regimeLeadCol(t, onRegimChange, **true**)` a `:725` |
| `PropagatedEditor.jsx:53` (leadCol a `:58`) | **Escalat** | `regimeLeadCol(t, onRegimChange, readOnly)` — respecta el seu |
| `CheckMeasureEditor.jsx:136` | Mesures | usa **`models.setPomRule`**, NO `setPomRegim`; leadCols inline propis (`:285-296`) via `RegleEditCell` (`:125-146`) |

**Y5-4. El punt exacte del guard:** **el 3r argument de `regimeLeadCol` a `FittingDetail.jsx:781`**
(`false` → `true`). `leadCols` a `MeasureGrid.jsx:214` accepta qualsevol node, per tant el read-only viu
dins el render de `regimeLeadCol` i **no cal tocar `MeasureGrid`**. L'edició legítima a Escalat
(`PropagatedEditor.jsx:58`) queda intacta perquè passa el seu propi `readOnly`.

**Y5-5. Deltes.** `regimeLeadCol` **sí** els mostra, via `regleLabel` (`fittingGridAdapter.jsx:59-66`,
usat a `:93-97`), llegint `row.increment_base`, `row.increment_break`, `row.talla_break_label`. Però al
fitting els deltes són **sempre etiqueta de lectura**, fins i tot en mode editable. L'edició real de
deltes viu **només** a `RegleEditCell` (`CheckMeasureEditor.jsx:125-165` → `models.setPomRule` `:136`).
**Al fitting no hi ha editor de deltes.**

**Y5-6. 🔴 TROBALLA TRANSVERSAL (bloquejant per al disseny).** A `CheckMeasureEditor`, **`readOnly` és
tot-o-res**: el mateix prop governa règim (`:286-296`), deltes, nom i preses (`:311-313`).
**No existeix granularitat "preses editables + règim/deltes/nom read-only"**, que és exactament el que
el disseny validat demana per al mode sessió. Cal un flag nou (p.ex. `lockRules`). **Avui NO EXISTEIX.**

**Y5-7.** Anotat: `regleLabel` està **triplicat** (el propi codi ho diu a `fittingGridAdapter.jsx:57-58`):
còpia idèntica a `MeasureTable` i `CheckMeasureEditor.jsx:108-114`.

## Y6 — "Afegir peça"

**Respost al Bloc X, §X6.** Resum: **viu dels dos costats i sense guard.**
- Endpoint viu: `views.py:151-162` → `services.py:319-365`.
- Botó viu: `FittingDetail.jsx:750-755`, condició `session.model` (`:750`), handler `:562-568`.
- Sense guard: `create` nu (`services.py:345-350`) vs `unique_together` (`models.py:331`);
  `IntegrityError` no capturat (`views.py:159`) → **500**, 9 cops als logs.
- I18n: `fitting.piece.create` (`ca.json:1859` "Afegir peça" / `en:1859` / `es:1859`); estat
  `fitting.piece.creating` (`:1860`). El bessó de ReviewScreen és `fitting.save.register_measures` (`ca.json:1916`).

## Y7 — `CheckMeasureEditor` com a superfície de referència

**Y7-1. Contracte de props avui** (`CheckMeasureEditor.jsx:173`):
```js
export default function CheckMeasureEditor({ model, onFeedback, onResolved, onBack = null, readOnly = false, taskId = null })
```

| Prop | Tipus | Usos |
|---|---|---|
| `model` | object (req.) | Àncora: `model.id` a `load` (`:187,190,191`), deps (`:232,234,241`), `RegleEditCell modelId` (`:295`), `WatchpointsPanel modelId` (`:324`), `model.size_run_model` (`:280`); objecte sencer a `EditorHeader` (`:309`) i `DependencyPanel` (`:310`) |
| `onFeedback` | fn | `:194,221,224,234,241` + propagat a `:295` |
| `onResolved` | fn | `:222` (post `sizeChecks.resolve`); a ModelSheet lligat a `exitEdit` (`ModelSheet.jsx:476`) |
| `onBack` | fn\|null | `:309` → `EditorHeader` |
| `readOnly` | bool | branca de `load` (`:186-190`), `editable={!readOnly}` (`:311`), `onSave/onNomSave/onReorder` (`:312-313`), trail (`:274`), leadCols (`:286-295`) |
| `taskId` | any | **ÚNIC ús: `:324`** → `<WatchpointsPanel modelId taskId editable={!readOnly} />` |

**Y7-2. 🔴 Fet clau, contra la intuïció del brief.** `CheckMeasureEditor` **no fa res de cicle de vida
amb `taskId`**: no obre, no pausa, no compta temps, no dispara cap crida. `taskId` només viatja fins a
`WatchpointsPanel` com a **provinença** dels watchpoints creats. Tot el lifecycle (obrir/pausar,
`activeTaskRef`, `pauseActiveTask`) viu a `ModelSheet.jsx:174-267`. **L'editor és apàtrida respecte a la
tasca.** Un `fitting_session_id` hauria de seguir la mateixa divisió: **el cicle de vida a `ModelSheet`,
l'editor només rep l'identificador.**

**Y7-3. Origen de dades.** `load()` (`:183-196`) fa dues crides: `models.baseStages(model.id)` (columnes
d'historial + files POM) i, segons `readOnly`, `sizeChecks.list(...)+get` o `sizeChecks.open(model.id)`.
`groups` (`:248-255`): **un sol group `key:'base'`**, `activeLabel = t('sizecheck.col_real')`,
`trailCols=[{key:'dn'}]`. `rows` (`:256-277`): join per `lineByPom[r.pom_id]` (`:246-247`);
`cells.base.active = { lineId, value, baseValue, tol }` (`:273`).

**Y7-4. Desat, comparat amb el fitting:**

| | Mesures | Fitting |
|---|---|---|
| Signatura | `onSave(lineId, value)` | `onSave(lineId, value)` — **idèntica** |
| Escriptura | `sizeCheckLines.update(lineId,{valor_real})` (`:228`) → `PATCH /size-check-lines/<id>/` (`endpoints.js:575`) | `makeFittingOnSave` (`fittingGridAdapter.jsx:146-152`): STEP → `PATCH /piece-fitting-lines/<id>/`; LINEAR → `POST .../propagar/` |
| Despatx per règim | **No** | **Sí** (`lineRegimeMap`) |
| Propagació | **Diferida** al `sizeChecks.resolve` (`:213`) | **Immediata**, al backend, retorna `{linies}` per refrescar germanes |
| Identitat de `lineId` | `SizeCheckLine.id` | `PieceFittingLine.id` |
| Diana del règim | `models.setPomRule` (`:136`) | `models.setPomRegim` (`FittingDetail.jsx:630`) |

**Y7-5. Punts de decisió que canviarien d'origen** (CENS, no proposta). Són **exactament els 4 seams que
`fittingGridAdapter.jsx` ja duplica**:
(a) `load()` (`:183-196`) — el fitting llegeix `pieceFittings.get`, forma `grid.lines` amb `evolucio`/`size_label`;
(b) constructor `groups`+`rows` (`:248-277`) → `buildFittingGroups`/`buildFittingRows`;
(c) `onSave` (`:228`) → `makeFittingOnSave(lineRegimeMap)`;
(d) `leadCols`/règim (`:285-305`) + botons de resolució + trail Decisió·Nota (`:274`, `:316-321`), que al
fitting no existeixen (allà hi ha gate + close/discard).

## Y8 — Detecció de sessió Oberta en entrar per una altra porta

**Y8-1. `ModelSheet.jsx` no sap res de fitting.**
`grep -n "FittingSession\|fitting\|fittingSessions" frontend/src/pages/ModelSheet.jsx` → **0 resultats**.

**Y8-2. El serializer del Model tampoc l'exposa.** L'únic camp "fitting-ish" a `models_app/serializers.py`
és `fitting_prev = DateField(read_only=True)` (`:98`, llistat a `:128`) — és una **data**, no id ni estat,
i viu a **`ModelListSerializer`**. El **`ModelDetailSerializer`** (`:169`), que és el que carrega
`GET /models/<id>/` (`ModelSheet.jsx:114/137`), **no té cap camp de fitting**.

**Y8-3. Es pot saber AVUI sense codi de backend nou:**
`GET /api/v1/fitting-sessions/?model=<id>&estat=Oberta`.
`filterset_fields` (`fitting/views.py:102-103`) = `['model','garment_set','fase','estat','data','responsable','convocatoria']`
→ inclou `model` i `estat`. Literals d'estat: `fitting/models.py:209-214` = `'Programada'`, `'Oberta'`,
`'Tancada'`, `'Anullada'`.

> Nota: `convocatoria` **ja és a `filterset_fields`**. Això supera el punt CO-6 / "PER DECIDIR 6" de la
> diagnosi anterior (`fitting/views.py:100` deia el contrari). Va entrar amb P4a (`1b59fd2`).

**Y8-4. Cridadors de `fittingSessions.list`:** `FittingConvocatoriaSheet.jsx:38`,
`FittingSessionList.jsx:84,93-96` i **`FittingTab.jsx:20`**.

**Y8-5. 🔴 TROBALLA TRANSVERSAL: `FittingTab.jsx` ja existeix i és codi ORFE.** Fa exactament
"llista les sessions de fitting d'aquest model" (`fittingSessions.list({model: model.id, ordering:'-data', page_size:200})`,
`:20`). `grep -rn "FittingTab" frontend/src/` → **només la seva pròpia definició** (`:12`). Ningú
l'importa, no és a `TABS` (`ModelSheet.jsx:24`). **Comprovar què ja s'ha construït abans de construir
(llei CLAUDE.md).**

**Y8-6. Estat a BD:** `Oberta=4`, `Programada=17`, `Tancada=3`, `Anullada=0`.
Models amb sessió **Oberta**: 165 (1), 168 (1, + 1 Programada), **185 (2)**.

## Y9 — GarmentSet

**Y9-1. Modelatge.** `FittingSession.garment_set` FK→`models_app.GarmentSet` (`fitting/models.py:216-221`),
en **XOR** amb `model` (`CheckConstraint 'fittingsession_set_xor_model'`, `:276-284`).

**Y9-2. `GarmentSet`** (`models_app/models.py:43-72`): `codi_base`, `nom_comercial`, `num_pieces`, `created_at`.
**No té M2M a peces.** Les peces són `Model`s via `Model.garment_set` FK (`models_app/models.py:173-179`,
`related_name='peces'`) + `Model.piece_number` (`:180`). Per tant `garment_set.peces` = els Models-peça.

**Y9-3. `session_can_advance`** (`fitting/services.py:648-658`): `True` **iff** hi ha ≥1 `PieceFitting`
**i** tots tenen `gate ∈ {OK, EXCEPCIO}` (`_GATE_ADVANCEABLE`). `False` si no n'hi ha cap o si algun és
`Pendent`/`NO_OK`. **Frontera dura: no es toca.**

**Y9-4. 🔴 Ningú materialitza les peces del set.** `create_piece_fitting` (`services.py:319-365`) crea
**UNA `PieceFitting` per crida, per a UN `model_id`**; **no itera `garment_set.peces`**. Es crida des de
`views.py:151-162`, que pren `model_id` del request. `schedule_session` només fixa
`duracio_minuts = 10 × num_pieces` (`services.py:180-182`), no materialitza res.

**Y9-5. 🔴 I no hi ha camí de UI.** `createPiece` (`FittingDetail.jsx:562-568`) fa
`createPiece(session.id, session.model)` i **surt d'hora si `!session?.model`**. Per a una sessió de
GarmentSet, `session.model` és `null` → **cap camí a FittingDetail per crear les peces del set**, ni cap
selector de quin model-peça.

**Y9-6. Ni la fulla ni la llista desglossen el set.**
`FittingConvocatoriaSheet.jsx` llista **sessions** per convocatòria (`:38`), una fila per model
(`:94,99`). `FittingSessionList.jsx` mostra `n_peces` (`:419,445`, agregat `:371`) però **no desglossa**.
Llistat de peces d'un GarmentSet: **NO EXISTEIX.**

**Y9-7. A BD: `FittingSession` amb `garment_set` no-null = 0.** Tot el camí GarmentSet↔sessió és
estructuralment present i **sense cap fila**. El XOR sempre resol a `model`.

> **Punt d'inserció peça-a-peça (Y9):** el **selector de peça** (`FittingDetail.jsx:732-760`), que és
> l'únic lloc del sistema que ja pensa en N peces. Però hauria de llegir `garment_set.peces` en comptes de
> `session.piece_fittings`, i `createPiece` hauria d'acceptar un `model_id` que **no és `session.model`**.
> **Cadena oberta CO-Y9.**

## Y10 — Redirecció de `/fittings/<id>`

**Y10-1. Ruta:** `App.jsx:260` → `<Route path="fittings/:id" element={<FittingDetail />} />`.

**Y10-2. Càrrega:** `loadSession` (`FittingDetail.jsx:514-521`) via `fittingSessions.get(id)`; efecte de
càrrega `:523-539`.

**Y10-3. Estat i `readOnly`:** estat a `session` (`:497`, set a `:516`/`:529`).
**`readOnly` es calcula a `:577`** (no `:534`, corregeix F3-3 de la diagnosi anterior):
`const readOnly = SEALED_ESTATS.includes(session.estat)`, amb `SEALED_ESTATS = ['Tancada','Anullada']` (`:146`).
El mateix predicat governa `reviewMode` a `:536`.

**Y10-4. Obertura automàtica** (`:527-530`, no `:497-507` — corregeix F2-7):
```js
// D2 — en entrar a una sessió Programada, obrir-la automàticament (→ Oberta + started_at).
if (s && s.estat === 'Programada') {
  return fittingSessions.open(s.id).then(r => { setSession(r.data); return r.data }).catch(() => s)
}
return s
```
Dispara a la primera càrrega, sempre que `estat === 'Programada'`.

**Y10-5. Punt MÍNIM per a la redirecció:** el `.then(s => {…})` de l'efecte de càrrega,
**`FittingDetail.jsx:533-537`** — l'únic lloc que ja branca per `estat` per fixar `reviewMode`/`readOnly`.
La redirecció "Oberta/Programada → Mesures amb context" hi aniria **abans** de `setReviewMode`; la branca
segellada es queda i renderitza el split 40/60 existent (`:701-730`), intacte.
Nota: l'auto-open de `:528` ja converteix Programada→Oberta, així que **post-open els dos casos vius són
`Oberta`**.

**Y10-6. Precedents de redirecció al projecte (cens):**
- `<Navigate … replace />`: `ProtectedRoute` (`App.jsx:59`), `SizeCheckRedirect` (`:68`),
  **`MesuresRedirect` (`:74-79`, ruta `:247`)**, i a nivell de ruta (`:243`, `:312`).
- `navigate(…, {replace:true})`: `FttResolver` (`App.jsx:103,107,120`).

> **El precedent literal és `MesuresRedirect` (`App.jsx:74-79`):** llegeix `id` + `task_id` i retorna
> `<Navigate to={/models/${id}?tab=Mesures${taskId ? '&task_id='+taskId : ''}} replace />`.
> És exactament el patró per a un `fitting_session_id`.

**Y10-7. El seam receptor.** `ModelSheet.jsx:95` ja llegeix `sp.get('task_id')`; l'efecte J1b que el
consumeix és `:257-267` (registra `activeTaskRef`, `setEditing('Mesures')`). El comentari de `:95`
anticipa literalment el plom. **`fitting_session_id` a `ModelSheet.jsx`: NO EXISTEIX**
(`grep -n "fitting_session_id" frontend/src/pages/ModelSheet.jsx` → 0).

---

# CADENES OBERTES (declarades)

| # | Cadena | On s'escapa |
|---|---|---|
| **CO-X1** | `close_piece_fitting` no atòmic: `BaseMeasurement` + Welford commiten abans que D-1 peti | `fitting/services.py:406` (cap `atomic`) |
| **CO-X2** | `BaseMeasurement` 60.7 vs `GradedSpec` actiu 60.5 · `measurements_version` no incrementat | dada viva a staging, model 185 |
| **CO-X3** | Welford `n_mostres=5` per 1 presa: `consolidate_base_from_fitting` compara vs `valor_teoric`, no vs `BaseMeasurement` | `fitting/services.py:388-389` |
| **CO-X4** | `doSave` descarta el body d'error del servidor | `FittingDetail.jsx:204-211` |
| **CO-X5** | `allow_reopen_sealed=True` **no té cap cridador** al frontend → un model amb gate passat no es pot tornar a gravar mai | `pom/services.py:540`; grep a `frontend/src/`: buit |
| **CO-X6** | `create-piece`: `create` nu + `IntegrityError` no capturat + botó sense guard → 500 | `services.py:345-350` · `views.py:159` · `FittingDetail.jsx:750` |
| **CO-Y1** | `DependencyPanel`, `WatchpointsPanel`, `RegleEditCell`, Decisió/Nota, Tolerància: què fan en mode sessió? | `CheckMeasureEditor.jsx:274,295,310,324` |
| **CO-Y3** | La pujada de fotos es salta `endpoints.js` (`client.post` cru); `piece_fitting` opcional mai s'omple | `FittingDetail.jsx:289` · `endpoints.js:555-558` |
| **CO-Y5** | `readOnly` a Mesures és **tot-o-res**: no hi ha "preses editables + regles read-only" | `CheckMeasureEditor.jsx:286-296,311-313` |
| **CO-Y8** | `FittingTab.jsx` fa ja la feina de Y8 i **no el munta ningú** | `FittingTab.jsx:12,20` |
| **CO-Y9** | GarmentSet: ningú materialitza les peces; `createPiece` surt d'hora si `!session.model`; 0 files a BD | `services.py:319-365` · `FittingDetail.jsx:562-568` |
| **CO-Y4** | `edit_pom_nomenclature_view` viu al backend i **cap cridador** al front | `pom/urls.py:45` |
| CO-9 (heretada) | El motor (`propaga_ancoratges`, `generate_graded_specs`) **no s'ha auditat**: zona intocable | `pom/grading_utils.py:560` |

**Correccions a la diagnosi anterior** (`DIAGNOSI_FLUX_FITTING_NAV.md`, àncores desplaçades pel sprint):
`readOnly` és a `:577` (deia `:534`); l'auto-open és a `:527-530` (deia `:497-507`); `hasSaveChanges` és a
`:153-159` (deia `:146-150`); `filterset_fields` **ja inclou `convocatoria`** (`views.py:102-103`), cosa
que **tanca CO-6**. `MesuresRedirect` es defineix a `App.jsx:74-79` (la ruta és `:247`).

---

# PER DECIDIR (Agus)

**Del Bloc X — urgent, hi ha dades vives afectades:**

1. **Les dades de staging del model 185.** `BaseMeasurement` diu 60.7/60.2 i el `GradedSpec` actiu diu
   60.5/60.0. El Welford té 5 mostres d'una sola presa. ¿Es reparen (regenerar grading + corregir
   `n_mostres`), es deixen com a evidència, o s'esborra la sessió 139 sencera? **Aquesta diagnosi no ha
   tocat res.**

2. **El guard D-1 vs el fitting.** Un model que ha passat el gate de fase **no pot tornar a gravar cap
   fitting**. ¿És la intenció (el grading segellat és intocable i cal reobertura explícita) o és un
   forat (el fitting hauria de poder reobrir)? Avui `allow_reopen_sealed` existeix i **no el crida ningú**
   (CO-X5). Sense decisió, el bug de l'Agus torna a la primera.

3. **Atomicitat del `close`.** ¿`close_piece_fitting` s'embolcalla en `transaction.atomic` (el 400 no deixa
   rastre) o es deixa com està i el guard D-1 es mou **abans** de la consolidació? Són dues peces
   diferents; la segona és més barata i tanca CO-X1 i CO-X3 alhora.

4. **El missatge d'error.** ¿`doSave` llegeix `err.response.data.error || .detail` i el mostra? És una línia
   i és el que hauria estalviat aquesta sessió.

5. **`create-piece` 500** (CO-X6). ¿`get_or_create` al servei, guard al botó, o `IntegrityError → 409` a la
   view? Les tres tanquen el forat; només una és la que vols.

**Del Bloc Y — dissenya la dissolució:**

6. **Granularitat del read-only** (CO-Y5). El disseny demana "preses editables · règim/deltes/nomenclatura
   read-only". A `CheckMeasureEditor` el `readOnly` és tot-o-res. ¿Flag nou (`lockRules`) o es deriva del
   context de sessió dins el component?

7. **On viuen Canvis · Observacions · Imatges.** No tenen equivalent a Mesures (Y1-1). ¿Panell lateral,
   franja plegable, o pestanya pròpia dins el mode sessió?

8. **L'àncora de les fotos** (CO-Y3). `FittingPhoto.session` és obligatori i `piece_fitting` opcional i
   sempre buit. ¿La superfície nova omple `piece_fitting`? ¿La pujada puja a `endpoints.js` com a helper?

9. **`FittingTab.jsx` orfe** (CO-Y8). Ja fa la detecció de Y8. ¿Es munta com a font de la franja de retorn,
   es refà, o es borra?

10. **GarmentSet** (CO-Y9). No hi ha cap fila a BD i no hi ha camí de UI per crear-ne les peces.
    ¿Es dissenya ara (el selector de peça és el punt d'inserció) o es declara fora d'abast fins que
    existeixi el primer conjunt real?

11. **L'obertura automàtica `Programada → Oberta`** (Y10-4, heretat de "PER DECIDIR 4"). Amb la redirecció,
    entrar a Mesures per la porta del fitting **muta l'estat abans de saber si l'usuari volia editar**.

---

# FRONTERES (què NO s'ha de tocar)

**Fronteres dures d'aquest sprint:**
- **Motor de grading (G6):** `generate_graded_specs` (`pom/services.py:18`), `propaga_ancoratges`
  (`pom/grading_utils.py:560`), `_apply_rule`, `derive_break_fields`. `GradingVersion`, `GradedSpec`,
  `ModelGradingOverride`, `ModelGradingRule`.
- **`close_piece_fitting` i `_seal_session` com a FUNCIONS: es criden, no es reescriuen.**
  ⚠️ **Matís:** el Bloc X demostra que `close_piece_fitting` **té un defecte d'atomicitat**. Reparar-lo és
  una peça pròpia (PER DECIDIR 3), **no part de la dissolució**. La dissolució el segueix cridant tal com és.
- **`session_can_advance`** (`fitting/services.py:648-658`): intacte, el segellat de GarmentSet en depèn.
- **`bump_grading_version_and_generate`** (`pom/services.py:505`) i el guard D-1: **zona de motor**.
  Qualsevol canvi (moure el guard, exposar la reobertura) és decisió humana, no efecte lateral d'un sprint de UI.
- **`PieceFittingLine` com a magatzem de treball**: la seva jubilació és G6, no aquest sprint
  (`DECISIONS.md §2`: *"No es jubila res del fitting fins que el seu equivalent és viu a Grading"*).

**Fronteres heretades de `CLAUDE.md`:** POMs, grading engine, motor de patrons.

**Superfícies que aquest sprint SÍ pot tocar:**
- `FittingDetail.jsx` (dissolució), `ModelSheet.jsx:95-100` (seam), `CheckMeasureEditor.jsx` (mode sessió),
  `fittingGridAdapter.jsx` (adapter), `App.jsx:260` (redirecció), i la fulla de convocatòria.
- **Cap d'aquests fitxers és zona intocable.**

---

*Cap línia de codi tocada. Cap dada de staging modificada — inclosos el Welford contaminat i la
divergència base↔grading, que es deixen tal com estan per a la decisió de l'Agus. Tots els FETS
verificats llegint el fitxer citat o consultant la BD amb SELECTs. Les afirmacions d'alt risc del Bloc X
(atomicitat, divergència, contaminació del Welford, radi del bloqueig) han estat re-verificades pel
director contra la BD, no només contra el codi.*
