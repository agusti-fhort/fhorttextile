# REPORT F1 · EL CICLE DE TASCA, RECONSTRUÏT

Data: **2026-08-05** · **Patró B** · staging `/var/www/ftt-staging`, branca `dev`
Base: `733024f8` → **HEAD `9d59dd0f`** · **8 commits · CAP PUSH**
Diagnosi font: `docs/diagnosis/DIAGNOSI_PREF1_CICLE_TASCA.md`
Decisions: D-1…D-10 (Agus, Patró C, 05/08/2026)

**Verificació:** estreta per fase, mai cap suite sencera. Total corregut: **157 tests, tots
verds**, en 14 fitxers concrets. `manage.py check` net abans de cada commit de backend;
`npm run build` net abans de cada commit de frontend.

---

## 0 · ELS VUIT COMMITS

| Fase | Commit | Títol |
|---|---|---|
| F1.0 | `463f9924` | un sol criteri per a «la tasca del model» |
| F1.1 | `5aaf0d3d` | la volta següent té nom, número i mare |
| F1.2 | `d63b7d6e` | desar deixa de tancar la tasca |
| F1.3 | `43d67283` | escriure és el senyal |
| F1.4 | `c06e5c79` | el fet facturable deixa de ser obrir una porta |
| F1.5 | `fd633753` | l'exclusió mira qui treballa, i el relleu deixa rastre |
| F1.6 | `4ecd3dae` | el catàleg de tasques, posat al dia |
| F1.7 | `9d59dd0f` | les tres costures que quedaven |

---

## 1 · F1.0 · EL RESOLUTOR ÚNIC

**Peça nova:** `backend/fhort/tasks/services_r.py` → `tasca_vigent(model, code, *, ronda=None)`.

Tres punts resolien «la tasca `<code>` d'aquest model» amb tres criteris, i dos amb l'ordre
**invertit**. La taula abans → després:

| Call-site | Criteri vell | Ara |
|---|---|---|
| `tasks/views_b.py:563` (`open-task`) | `filter(origen='prevista').first()` | `tasca_vigent(model, code)` |
| `models_app/views.py:1703` (desat de POM) | `order_by('id').first()` → la més **ANTIGA** | `tasca_vigent(model, 'pom')` |
| `models_app/services_size_check.py` | `.exclude(status='Done').order_by('-id')` → la més **NOVA** | (el bloc sencer mor a F1.2) |

**Regla, a `services_r.py:44-71`:** ronda oberta → la seva tasca · si no (o si la ronda no cobreix
el code) → la prevista · dins del conjunt triat, mai una `Done` si n'hi ha una de viva.

**Verificació:** `tasks/test_tasca_vigent.py` (7) + `models_app/test_gate_mesures_pom_task` +
`tasks/test_stop_encadenat` (15). ✅

---

## 2 · F1.1 · RONDA I GENEALOGIA

**Migració `tasks/0044`** — additiva, tot nullable, **cap backfill**:

| Operació | Detall |
|---|---|
| `CreateModel Ronda` | `model` FK CASCADE · `seq` · `motiu` (`nova_mostra`\|`correccio`) · `oberta_el` · `tancada_el` |
| `AddConstraint` | `uniq_ronda_model_seq` UNIQUE (`model_id`, `seq`) |
| `AddField ModelTask.ronda` | FK SET_NULL, `related_name='tasques'` |
| `AddField ModelTask.mare` | self-FK SET_NULL, `related_name='filles'` |
| `AddField ModelTask.motiu` | varchar(20) null |

**Auditoria a Postgres** (no l'OK de Django):

```
tasks_ronda        → fhort ✅ · los ✅ · public NULL ✅ (app de tenant)
ronda_id/mare_id/motiu → nullable als DOS tenants ✅
uniq_ronda_model_seq   → índex únic viu als DOS ✅
```

Tota la feina històrica és la **ronda 1 implícita** (`ronda IS NULL`). Inventar-li una fila seria
escriure història.

**Serveis** (`services_r.py`): `obrir_ronda` · `tancar_ronda` · `ronda_lliurable` ·
`rondes_lliurables`. Les tasques de ronda neixen `origen='ad_hoc'` — que és exactament el que la
unique **parcial** `uniq_prevista_model_tasktype` deixa conviure amb la prevista.

**Verificació:** `tasks/test_ronda.py` (12 a F1.1, 34 amb F1.2/F1.6), amb **§S-4 com a test
positiu**: «Gravar POM» de la ronda 2 resol la ronda 2 i deixa el `updated_at` de la ronda 1
intacte. ✅

---

## 3 · F1.2 · DESAR NO TANCA (D-2)

La diagnosi va trobar **tres** punts de tancament automàtic, no un:

| Punt | Abans | Ara |
|---|---|---|
| `models_app/views.py` `_close_pom_task_for_model` | `→InProgress` + **`→Done`** | **`_assegura_pom_task_oberta`**: només assegura `InProgress` |
| `services_size_check.py` `resolve_size_check` | `→InProgress` + `→Done` dins d'un `try/except Exception` | **bloc eliminat sencer** |
| `SessionActions.jsx:44` | `transition(Done)` dins d'un `catch {}` buit | **eliminat** |

Les dues portes de desat (`gravar-pom`, `tancar-taula`) hereten el canvi. `finishPomEntry`
(`ModelSheet.jsx`) perd l'optimisme que escrivia `status:'Done'` i `pom_task_done:true` en local
— ara mentiria, i el `reloadModel()` de tres línies més avall el desmentiria.

**§S-5 mor aquí.** Aquell `except Exception` s'empassava el `TransitionError('tasca_albaranada')`
i `resolve` retornava èxit igualment. `_assegura_pom_task_oberta` ara **retorna el `code`** perquè
la porta pugui oferir la sortida de D-5.

**Consumidors de `Done`, comprovats un per un:**

- `model_ready_for_gate` i les consultes d'albarà: **NO tocats** — el seu comportament nou és el
  desitjat (D-10: «albarà només Done» ja hi era).
- Gate de Mesures: `pomDone || hasBaseValue` → no se'n ressent.
- **Cap test hi depenia** (verificat a la diagnosi i reconfirmat corrent-los).

**Verificació:** `tasks/test_ronda` + `models_app/test_gate_mesures_pom_task` (23) ·
`models_app/test_c4_escriptura_germanes` + `pom/test_guarda_rang_mesura` (22) · build net. ✅

---

## 4 · F1.3 · EL BATEC D'ESCRIPTURA (D-1 · D-2)

**Peça nova:** `tasks/services_batec.py`.

```
Pending/Paused → InProgress (obre tram)   ← el batec FORT
InProgress     → renova last_heartbeat    ← el batec normal
sense tasca    → no-op
```

**UN SOL BATEC.** El ganxo que `models.py` deixava escrit —*«qui escrigui aquí haurà d'escriure
els dos alhora, no inventar-se un segon batec»*— s'ha honrat: el guard (presència) i l'escriptura
(activitat) escriuen **el mateix camp**.

**Cobertura** (mapa superfície → `TaskType.code`):

| Com | Quantes | Superfícies |
|---|---|---|
| Decorador `bat_escriptura` (model_id al camí, bat només en 2xx) | 7 | `gravar-pom` · `tancar-taula` · `reorder` · `desactivar-pom` · `generar-grading` · `ajustar-talla` · `regim` |
| Crida explícita (model des de la fila) | 8 | graella `PATCH base-measurements` · bateig `noms` · `size-checks/resolve` · `size-check-lines` · `piece-fitting-lines` · `set-gate` · `close` · `discard` |
| **Autosave `.ftt`** | 1 | `PATCH ftt-documents/<id>/` — **D-1 per a la fitxa** |
| **Sense batec, per decisió** | 1 | `upload-fitxer`: cap `TaskType` reclama els adjunts; triar-ne un imputaria a la tasca equivocada (documentat a la vista) |
| Batec des del client (§S-1) | 2 | `pom-placements` POST · `fitting-photos` POST |

**El batec no crea tasques** i **mai llança**: la paret d'albarà torna com `accio='refusada'` amb
el `code`, no com a excepció que tomba el `PATCH`.

**Verificació:** `tasks/test_batec_escriptura.py` (8: renova · reobre · no-op · sense perfil ·
code inexistent · tram d'un altre · paret d'albarà) + build. ✅

---

## 5 · F1.4 · LA MERITACIÓ, AL SEU LLOC (D-10 · §S-9)

**El gallet es MOU; la meritació no es redissenya.** `_meritar_model`, `_meritar_conjunt` i
`_emetre_meritacio` **no s'han tocat ni una línia** — la frontera de billing s'ha respectat.

| Peça | Abans | Ara |
|---|---|---|
| Gallet de meritació | `transition_task`, 1a `→InProgress` | `services_batec._meritar_si_cal`, 1r batec d'escriptura |
| `fase_actual='Dev'` | `transition_task` | **es queda** (món tècnic, sagrat) |
| `assign_work_order` | `transition_task` | **es queda** (encàrrec ≠ facturació SaaS) |
| Criteri de `reconcile_consumption` | tasca `InProgress`/`Done`/`Paused` | **`TimerEntrada.last_heartbeat IS NOT NULL`** (les dues branques: model sol i conjunt) |

**Correcció trobada construint:** el batec **d'obertura** no estampava `last_heartbeat`, de manera
que el runtime i el reconcile haurien discrepat sobre el mateix fet — el segon mira precisament
aquell camp. Ara el tram neix amb el segell posat: qui obre una tasca **escrivint** ja ha escrit.

**Tests actualitzats (no trencats):** `test_set1_meritacio` protegeix «SET = 1 mèrit», que segueix
igual de cert — se n'ha canviat el **trigger**, no la llei. `tests_actor_schema` prova la
propagació d'`actor_schema` — se n'ha actualitzat el **fixture**.

**Verificació:** `tasks/test_meritacio_batec.py` (7), amb el **negatiu explícit**
`test_obrir_la_porta_sense_escriure_NO_merita` — el cas «tocar una porta 3 s factura» convertit en
garantia. ✅

---

## 6 · F1.5 · EXCLUSIÓ I HANDOFF (D-6 · D-7 · D-8)

**D-6** — `services_c.py:218-241`: l'exclusió deixa de mirar `assignee` (camp de *planificació*) i
mira els **trams oberts** (`TimerEntrada.tecnic`, `fi IS NULL`). La invariant torna a ser certa per
construcció: el que tanca l'exclusió és exactament el que el rellotge considera obert.

**D-7** — `services_c.traspassa_tram(task, profile)`: tanca el tram de qui la tenia, n'obre un per
a qui l'agafa i escriu un `TaskTransition` amb `auto='handoff'`. Les **dues** portes de relleu
(`claim_task_view` i la branca de claim d'`open-task`) hi passen.

**D-8** — cap mutex de model construït, i no en calia: «mateixa tasca mai» surt sola del fet que un
tram obert és d'un sol tècnic.

**Verificació:** `tasks/test_exclusio_handoff.py` (10), amb el **cas real de la BD** com a test:
`test_EL_CAS_REAL_actor_diferent_d_assignee_ja_no_esquiva_l_exclusio` (timers 116/117). Regressió:
`test_guard_tasca_oblidada` + `test_stop_encadenat` + `test_higiene_temps` (34). ✅

---

## 7 · F1.6 · EL CATÀLEG (§S-8)

**Migracions `tasks/0045`** (`TaskType.es_lliurable`, bool default False) i **`tasks/0046`**
(sembra idempotent, `RunPython` amb reversa).

**Auditoria a Postgres, els dos tenants:**

```
fhort: 15 codes   los: 15 codes   divergència en els DOS sentits: 0 ✅
sample_check      order 47 · eina escalat · mode presa · facturable ✅ · als DOS
es_lliurable=t    tech_sheet · pattern_cad · pattern_digit · scaling · marking (5) · als DOS
patronatge        0 files a fhort · 0 a los ✅
```

`es_lliurable` no és `facturable`: definir POMs es cobra i no s'entrega. La migració escriu **els
dos sentits** — ha de deixar el catàleg en un estat conegut, no només afegir-hi marques.

El delete de `patronatge` va guardat per `count() == 0` (`TaskType.instances` és `PROTECT`).

El pont `_tasktype_te_es_lliurable` **mor**, com deia el seu propi avís.
`Model.lliurable_ronda_n` exposa **només el fet consultable**; l'avís visual és F2.

**Verificació:** `tasks/test_ronda.py` (34, amb `RondaLliurableTest`) + auditoria SQL. ✅

---

## 8 · F1.7 · LES TRES COSTURES

**§S-2** — `transition_task_view` retorna **409** quan el `TransitionError` porta `code` (mateix
codi que `open-task`); els rebuigs sense codi segueixen sent 400, que és el que són.

**§S-3** — l'acció `tancar` **jubilada** (`tasks/views.py`), amb el seu `endpoints.js` i el botó de
`TimeTracking.jsx`. Tancava sense passar per la màquina d'estats i deixava la tasca «En curs» sense
tram — l'anomalia «òrfena». Era l'última escriptura pública del viewset: el pas a
`ReadOnlyModelViewSet` (`89009858`) va tancar el router, però les `@action` no en depenen.
El test que **asseverava que sobrevivia** ara asseveura el contrari.

**D-2, tercera pota** — **migració `tasks/0047`**: `TimerEntrada.origen` (`mesurat`|`declarat`).
Endpoint `POST /api/v1/model-tasks/<pk>/temps-declarat/` amb `{minuts}` XOR `{inici, fi}`.
Guard dur: **només `Externa-lliure`**. Sostre `MAX_MINUTS_TRAM` rebutjat **a la cara**, no acceptat
i ignorat després en silenci.

**Auditoria:** columna als dos tenants · **218 trams existents a `mesurat`** ✅

**Verificació:** `tasks/test_temps_declarat.py` (13) + `test_guard_tasca_oblidada` (23) + build. ✅

---

## 9 · MIGRACIONS — LLISTA I AUDITORIA

| # | Fitxer | Operacions | Auditat a `information_schema`/`pg_indexes` |
|---|---|---|---|
| 0044 | `..._modeltask_mare_modeltask_motiu_ronda_modeltask_ronda_and_more` | 3 AddField + CreateModel Ronda + AddConstraint | ✅ taula als 2 tenants, absent de public, 3 cols nullable, índex únic viu |
| 0045 | `tasktype_es_lliurable` | AddField bool | ✅ |
| 0046 | `cataleg_f1_sample_check_lliurables` | RunPython (sembra + reversa) | ✅ 15/15 codes, 0 divergència, patronatge a 0 |
| 0047 | `timerentrada_origen` | AddField varchar(10) | ✅ als 2 tenants, 218 files a `mesurat` |

Totes aplicades amb **`migrate_schemas`** (mai `--schema`), 3 passades cadascuna
(public + fhort + los).

---

## 10 · SORPRESES

> Coses que el terreny ha dit i la diagnosi no deia. Anotades, no resoltes.

### 🚨 S-11 · El batec d'obertura no estampava el segell — i això partia D-10 en dos

Trobat construint F1.4: `transition_task` obre el tram amb `last_heartbeat = NULL`. Si el gallet de
meritació és «primer batec» i el criteri del reconcile és `last_heartbeat IS NOT NULL`, un model on
l'única activitat fos **el primer desat** hauria meritat en runtime i **no** hauria estat visible
per al reconcile: dos components discrepant sobre el mateix fet.
**Resolt dins de F1.4** (el tram neix amb el segell posat), però val la pena saber-ho: qualsevol
peça futura que llegeixi «hi ha hagut feina» ha de mirar `last_heartbeat`, no l'estat de la tasca.

### ⚠️ S-12 · `ronda_lliurable` sobre el buit retorna **False**, no True

El brief deia «retorna sobre queryset buit», que en Python vol dir `all([]) is True`. S'ha
implementat **al revés a posta**: una ronda sense cap tasca lliurable retorna `False`. «No hi ha
res per lliurar» no és «ja està lliurat», i un avís al PM que salta sobre el buit és soroll.
**Desviació conscient del brief** — si la intenció era la contrària, és una línia.

### ⚠️ S-13 · Hi ha un QUART resolutor divergent, fora de l'abast del brief

`tasks/services_scheduling.py:24-26` (`reagenda_tasca`) resol amb
`.exclude(status='Done').order_by('-id').first()` — el criteri antic de `resolve_size_check`. El
brief en nomenava **tres** i la diagnosi §S-4 també. **No s'ha tocat** (scope creep → s'anota).
Amb una ronda oberta, reagendar apuntaria a la tasca equivocada. És una línia:
`task = tasca_vigent(model, task_type_code)`.

### ⚠️ S-14 · `resolve_size_check` retorna `tasca_finalitzada` sempre `False`

Es conserva al contracte d'API (F1.2 no el podia treure sense tocar consumidors). El
`CheckMeasureEditor` que l'ensenyi deixarà d'ensenyar-ho tot sol — que és el que ara és veritat—,
però el camp és **codi mort amb forma de contracte**. Candidat a retirar quan es netegi la
signatura, junt amb `allow_reopen_sealed`, que ja hi era declarat com a inert.

### 🔵 S-15 · Sessions concurrents: HEAD s'ha mogut dues vegades durant el tram

`1f07faaa` → `b9323ce0` → `733024f8`, tot de `pom/management` i `pom/seed_data` (catàleg Brownie
d'una altra sessió). **Cap col·lisió** amb els fitxers d'aquest tram, però les àncores de la
diagnosi s'han re-verificat per `grep` abans de cada fase, mai picat a cegues.

### 🔵 S-16 · La BD de test estava ocupada per una altra sessió

`test_ftt_staging` tenia una correguda activa (regla del repo: **mai dues corregudes alhora**).
Els tests d'aquest tram s'han corregut sobre una BD pròpia via
`backend/fhort/settings_f1_tmp.py` (`test_ftt_f1_tmp`), mateix patró que el
`settings_step_tmp.py` que ja hi havia. **Fitxer temporal, NO commitat.**

---

## 11 · EL QUE NO S'HA TOCAT (fronteres respectades)

- Motor de grading (`generate_graded_specs`) · G1 · G6 · motor de patrons.
- `TechSheetEditor.jsx` serialització (només s'hi ha afegit el batec de `pom-placements`).
- Billing: `ConsumptionRecord` **s'ha mogut de gallet, no redissenyat** — les tres funcions de
  meritació estan byte a byte com eren.
- `model_ready_for_gate` i les consultes d'albarà: el seu comportament nou és el desitjat.

---

## 12 · PENDENT DECLARAT (no és d'aquest brief)

- **F2 · UI**: modal de 3 cares · gest de Stop · formulari de temps declarat · refeta de `/temps`
  (§S-3: la pàgina llegeix camps que el servidor no emet) · avís al PM sobre `lliurable_ronda_n` ·
  UI d'obrir ronda (el servei hi és, la porta HTTP i el gest no).
- **F3**: `recompute_welford` amb semàntica nova + `--apply` · **cron del guard (D-9)** al runbook ·
  neteja de PROD post-deploy.
- **S-13**: el quart resolutor de `services_scheduling.py`.

---

## 13 · ACCIONS DE DESPLEGAMENT

1. **4 migracions** (`tasks/0044` → `0047`) amb `migrate_schemas`, mai `--schema`.
2. `0046` és una **data migration**: auditar el catàleg als tenants de destí després d'aplicar-la
   (el `patronatge` de PROD pot tenir `ModelTask` penjades — el guard `count()==0` no l'esborrarà i
   caldrà decidir-ho a mà).
3. **Cap push fet.** Tots els commits són locals a `dev`.
4. Esborrar `backend/fhort/settings_f1_tmp.py` (temporal de test, no commitat).

---

*Patró B · 8 commits locals · cap push · cap suite sencera · 157 tests verds.*
