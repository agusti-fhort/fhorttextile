# DIAGNOSI_DASHBOARD_FONTS — lectura quirúrgica de les 8 fonts del dashboard del model

> **Patró A · READ-ONLY ABSOLUT.** Cap fitxer de producte tocat, cap migració, cap escriptura.
> Staging (`fhort`), branca `dev`, `/var/www/ftt-staging`. Equip DIAGNOSI: director + investigadors
> en paral·lel + documentador. Protocol: `.claude/PROTOCOL_FASE_B.md`.
> Objectiu: portar al CTO les **FORMES REALS** (camp per camp, amb tipus) de cada font que alimentarà
> el contracte de `models/<id>/dashboard/` + `models/<id>/timeline/`. **No es decideix res aquí.**
> Taxonomia de referència: `.claude/TAXONOMIA_FLUX_MODEL.md`.
> Data: 2026-06-20.

---

## 0. Com llegir aquest document

- **FET** = afirmació sobre el codi, sempre amb `fitxer:línia`. **💡 PROPOSTA** = disseny a validar, sempre marcat i separat.
- Cada font porta un **flag**: `VIU` (endpoint REST operatiu i serveix la dada) · `PARCIAL` (la dada/model existeix i és viva, però l'exposició REST és incompleta o no idiomàtica) · `NO-EXISTEIX` (no hi ha endpoint REST que serveixi la dada; cal construir-lo).
- **Nota sobre exemples:** TOTS els endpoints rellevants són `IsAuthenticated`. **No s'ha obtingut cap resposta HTTP real** (no teníem token de tenant). Els exemples JSON són **estructura verificada al codi (serializer/view), valors il·lustratius** — NO captures reals. Allà on un investigador va dir "exemple real de BD", es reescriu aquí com a il·lustratiu perquè no es va poder confirmar com a resposta HTTP.
- Verificació documentador: els anclatges crítics de Q1/Q2 (F1 `shape()`, F4 absència d'endpoint, F5 classes i `task-log`, F6 enums, F3 ruta i choices) s'han re-grepat a mà; les discrepàncies trobades estan anotades.

---

## Mapa ràpid (resum executiu de vitalitat)

| # | Font | Fitxer clau | Endpoint REST | Flag | Alimenta |
|---|---|---|---|---|---|
| 1 | `by_model` (comptadors de tasques) | `tasks/views_b.py:91` | `GET model-task-items/by-model/` | **VIU** | Q4 / Q1 (estat de tasques) |
| 2 | `consumption_delivery_view` (albarà d'esforç) | `models_app/views.py:1164` | `GET models/<id>/albara/` | **VIU** | Q1 esforç (⑤ M) + history |
| 3 | `pom-alerts` (alertes tècniques) | `fitting/views.py:78` | `GET pom-alerts/` | **VIU** | Q3 (atenció tècnica) |
| 4 | `MeasurementChangeLog` | `models_app/models.py:535` | **cap** | **NO-EXISTEIX** | Q2 timeline (peça clau) |
| 5a | `TaskTransition` | `tasks/models.py:237` | `GET models/<id>/task-log/` | **PARCIAL** | Q2 timeline |
| 5b | `GateEvent` | `tasks/models.py:256` | **cap GET** (només POST de creació) | **NO-EXISTEIX** | Q2 timeline (fases/regrés) |
| 6 | fase + estat del Model | `models_app/models.py:75` | (via detall del Model) | **VIU** (model) | Q1 "on sóc" |
| 7 | Artefactes vigents (fitxa/grading/base) | divers | 3 endpoints separats | **VIU** (dispers) | Q1 artefactes vigents |
| 8 | `FittingSession` + `group_*` | `fitting/models.py:202` | `GET fitting-sessions/` | **VIU** | projecció convocatòria |

**Titular per al CTO:** el **timeline Q2 NO existeix com a font servible**. De les tres fonts del timeline (taxonomia §3 `a`), només `TaskTransition` té un GET (i ad-hoc, sense serializer); `MeasurementChangeLog` i `GateEvent` **no tenen cap endpoint de lectura** tot i ser models vius i poblats. Aquesta és la construcció nova principal (coincideix amb taxonomia §5.5 punt 2: "el merge del timeline"). La resta (Q1, Q3, Q4, esforç, convocatòria) ja té fonts vives, encara que **disperses en endpoints separats**.

---

# FETS — font per font

## Font 1 — `by_model` (comptadors de tasques per model) · **VIU**

**Ruta:** `GET /api/v1/model-task-items/by-model/`
**View:** `ModelTaskViewSet.by_model()` — `tasks/views_b.py:91` (`@action(detail=False, methods=['get'], url_path='by-model')`).
**Registre:** `tasks/urls.py:33` (`router.register(r'model-task-items', ModelTaskViewSet, ...)`).
**Serializer:** **cap.** La resposta es construeix a mà amb la funció inline `shape(row)` a `tasks/views_b.py:190-208` sobre un queryset agregat (`tasks/views_b.py:163-188`).
**Auth:** `IsAuthenticated`. **Paginació:** `PageNumberPagination` DRF (`count/next/previous/results`).

**Naturalesa:** és **multi-model** (una fila per model, llista paginada), NO el detall d'un model. Útil per a la vista zoom-out o per agregar; per al dashboard del model concret se'n llegeix la fila d'aquell model.

**Forma camp-per-camp** (cada element de `results`, via `shape()`):

| Camp | Tipus | Origen (fitxer:línia) |
|---|---|---|
| `model_id` | int | `model_id` — views_b.py:193 |
| `model_codi` | str | `model__codi_intern` — views_b.py:163 |
| `model_nom` | str | `model__nom_prenda` |
| `fase` | str (FASE_CHOICES) | `model__fase_actual` — views_b.py:195 |
| `counts` | dict | views_b.py:196 |
| `counts.pending` | int | `Count(filter=Q(status='Pending'))` |
| `counts.paused` | int | `Count(filter=Q(status='Paused'))` |
| `counts.in_progress` | int | `Count(filter=Q(status='InProgress'))` — views_b.py:170,199 |
| `counts.done` | int | `Count(filter=Q(status='Done'))` |
| `prioritat` | int | `model__prioritat` |
| `temporada` | str | `model__temporada` |
| `estat` | str (ESTAT_CHOICES) | `model__estat` — views_b.py:205 |
| `data_objectiu` | str ISO date \| null | `model__data_objectiu` — views_b.py:206 |
| `responsable_id` | int \| null | `model__responsable_id` |

**Filtres acceptats** (views_b.py:134,137): `?estat=`, `?fase=`. **Ordre per defecte** (views_b.py:88): `-in_progress, -pending, -paused, model__codi_intern`. Per defecte filtra files amb alguna tasca activa (views_b.py:188).

**Esquema JSON il·lustratiu** (estructura verificada; valors d'exemple, NO captura real):
```json
{
  "count": 3, "next": null, "previous": null,
  "results": [
    {"model_id": 168, "model_codi": "BRW-FW26-0006", "model_nom": "Vestido LEXI",
     "fase": "Pending", "counts": {"pending": 5, "paused": 0, "in_progress": 0, "done": 0},
     "prioritat": 3, "temporada": "FW", "estat": "Nou", "data_objectiu": null, "responsable_id": 14}
  ]
}
```
> ⚠️ L'investigador va reportar valors "des de la BD"; com que no es va poder confirmar com a resposta HTTP autenticada, es marquen com a **il·lustratius**.

---

## Font 2 — `consumption_delivery_view` (albarà d'esforç) · **VIU**

**Ruta:** `GET /models/<int:model_id>/albara/` — `models_app/urls.py:177`.
**View:** `consumption_delivery_view` — `models_app/views.py:1164` (`@api_view(['GET'])` + `IsAuthenticated`).
**Serializer:** **cap.** Tots els dicts es construeixen a mà a la view (`models_app/views.py:1224-1238`).

**Cas no-meritat:** si el model encara no té `ConsumptionRecord`, retorna només `{"merited": false, "model_id": <int>}` (`models_app/views.py:1181`).

**Forma completa (cas meritat)** — esquema literal amb tipus:
```json
{
  "merited": true,
  "model_id": 168,
  "header": {
    "code": "str",        // ConsumptionRecord.code_snapshot (max 40)
    "name": "str",        // ConsumptionRecord.name_snapshot (max 200)
    "period": "YYYY-MM",  // ConsumptionRecord.period
    "merited_at": "ISO-8601 datetime",
    "opaque_ref": "uuid-str"
  },
  "steps": [
    {"task_type": "str|null", "status": "Pending|Paused|InProgress|Done",
     "minutes": 0, "started_at": "ISO|null", "finished_at": "ISO|null"}
  ],
  "totals": {"total_minutes": 0, "rectifications": 0},
  "per_technician": [
    {"technician_id": 14, "label": "str (nom_complet|username)", "minutes": 0}
  ],
  "history": [
    {"task_type": "str|null", "from": "str|null", "to": "str",
     "by": "str|null (nom_complet|username)", "at": "ISO-8601 datetime"}
  ]
}
```

**Detall de fonts per bloc** (verificat):
- `steps[]` → una fila per `ModelTask`; `minutes` = suma de `TimerEntrada.minuts` **excloent timers oberts (minuts NULL)** (`models_app/views.py:1204`, regla a ~1193).
- `totals.rectifications` = comptador de transicions `Done→InProgress` (`models_app/views.py:1235`, lògica a ~1209).
- `per_technician[]` → agregació de minuts per `TimerEntrada.tecnic_id` (`models_app/views.py:1236`). **Aquesta és la lectura ⑤ M (cost per model, agnòstic a qui)** de la taxonomia §2.
- `history[]` → iteració de `mt.transitions.all()` (reverse de `TaskTransition`, `models_app/views.py:1208`); camps `from/to/by/at`. **És la mateixa dada que Font 5a `TaskTransition`, aquí ja exposada per model.** Ordenat per `at` asc amb NULLs al davant (~1222).

**Exemple HTTP:** no obtingut (`IsAuthenticated`).

---

## Font 3 — `pom-alerts` (alertes tècniques) · **VIU** (backend viu, frontend retirat A3)

**Ruta:** `GET/POST/PATCH/DELETE /api/v1/pom-alerts/` — `fitting/urls.py:41` (`router.register('pom-alerts', POMAlertViewSet, basename='pom-alert')`).
**ViewSet:** `POMAlertViewSet` — `fitting/views.py:78` (`viewsets.ModelViewSet`, `IsAuthenticated`).
**Serializer:** `POMAlertSerializer` — `fitting/serializers.py:38` (`fields = '__all__'`, `read_only_fields = ('data_creacio',)`).
**Model:** `POMAlert` — `fitting/models.py:98`.

> **Confirmació de vitalitat (FET):** la ruta segueix registrada i el ViewSet existeix tot i la retirada del frontend a A3. Verificat per codi (`fitting/urls.py:41`, `fitting/views.py:78`). L'investigador va reportar un `HTTP 401` a `https://staging.fhorttextile.tech/api/v1/pom-alerts/` (ruta viva, auth requerida) — coherent, però es marca com a report (no re-executat pel documentador).

**Camps del model `POMAlert`** (serialitzats tots per `__all__`), `fitting/models.py:99-143`:

| Camp | Tipus | Detall |
|---|---|---|
| `id` | int | PK |
| `model` | FK→models_app.Model | CASCADE, `related_name='pom_alerts'`, **null=True** (models.py:111) |
| `size_fitting` | FK→SizeFitting | SET_NULL, null=True, `related_name='pom_alerts'` (112) |
| `pom` | FK→pom.POMMaster | PROTECT, null=True, `related_name='alerts'` (119) |
| `tipus` | CharField(20), choices | `desviacio`/`fora_rang`/`manca`/`conflicte`, default `desviacio` (99-104,120) |
| `valor_detectat` | Decimal(10,4) \| null | (121) |
| `valor_esperat` | Decimal(10,4) \| null | (122) |
| `z_score` | Decimal(6,3) \| null | (123) |
| `estat` | CharField(20), choices | **`Pendent`/`Acceptat`/`Corregit`**, default `Pendent` (105-109,124) |
| `creat_per` | CharField(100) | default `'sistema'` (125) |
| `data_creacio` | DateTime auto_now_add | read-only (126) |
| `resolt_per` | FK→accounts.UserProfile | SET_NULL, null=True, `related_name='pom_alerts_resoltes'` (127) |
| `data_resolucio` | DateTime \| null | (134) |
| `desviacio_cm` | Decimal(6,2) \| null | Sprint S11 (137) |
| `tolerancia_cm` | Decimal(6,2) \| null | Sprint S11 (138) |
| `missatge` | TextField | (139) |
| `origen` | CharField(20) | default `'FITTING'`, **sense choices** (140) |
| `nota_resolucio` | TextField | (141) |
| `resolt_per_user_id` | int \| null | id cross-schema S11 (142) |

**Camps extra del serializer** (read-only, `fitting/serializers.py:39-41`): `pom_codi` (`pom.codi_client`), `model_codi` (`model.codi_intern`), `resolt_per_nom` (`resolt_per.nom_complet`).

**Filtres/ordre** (segons report investigador, view `fitting/views.py:78-89`): filtrable per `estat`, `tipus`, `model`, `pom`; ordre default `-data_creacio`. (Anclatge de la view no re-verificat camp a camp pel documentador; els camps del model i serializer SÍ.)

**Disparadors (què crea una alerta)** — segons report investigador, marcats com a **report (no tots re-verificats)**:
- Origen FITTING: comparació real vs teòric a `pom/s10_views.py` (~60-148), tolerància asimètrica de `BaseMeasurement` amb fallback 0.6 cm.
- Origen MANUAL: `pom/s11_views.py` (~144-196), `POST models/<id>/check-tolerances/`.
- Imports: `models_app/extraction_views.py` (~44-62), tipus `manca`/`conflicte`.

> ⚠️ **Discrepància anotada:** l'investigador va afirmar que els disparadors fixen `estat='Obert'`. Els `ESTAT_CHOICES` reals **no inclouen `'Obert'`** (només `Pendent/Acceptat/Corregit`, `fitting/models.py:105-109`, default `Pendent`). El valor exacte que fixa el disparador **no s'ha verificat**; tractar com a obert fins a llegir s10/s11.

**Esquema JSON il·lustratiu** (estructura verificada, valors d'exemple):
```json
{"id": 123, "model": 45, "model_codi": "BRW-FW26-0006", "size_fitting": 12,
 "pom": 234, "pom_codi": "ALT", "tipus": "desviacio",
 "valor_detectat": "89.5000", "valor_esperat": "88.0000", "z_score": "1.234",
 "estat": "Pendent", "creat_per": "sistema", "data_creacio": "2026-06-15T10:30:45Z",
 "resolt_per": null, "resolt_per_nom": null, "data_resolucio": null,
 "desviacio_cm": "1.50", "tolerancia_cm": "0.60",
 "missatge": "Fitting peça 456: ALT talla L desvia +1.50cm (tol ±0.60cm)",
 "origen": "FITTING", "nota_resolucio": "", "resolt_per_user_id": null}
```

---

## Font 4 — `MeasurementChangeLog` · **NO-EXISTEIX** (model viu, SENSE endpoint) — peça clau de Q2

**Model:** `MeasurementChangeLog` — `models_app/models.py:535-584`. Append-only (overrides de `save()`/`delete()` que prohibeixen UPDATE/DELETE, ~576-583).

**Camps (tots), `models_app/models.py:546-566`:**

| Camp | Tipus | Detall |
|---|---|---|
| `model` | FK→Model | CASCADE, `related_name='measurement_changes'` (546) |
| `pom` | FK→pom.POMMaster | PROTECT, `related_name='measurement_changes'` (547) |
| `base_measurement` | FK→BaseMeasurement | SET_NULL, null=True, `related_name='change_log'` (548) |
| `valor_anterior` | FloatField \| null | null si és creació (552) |
| `valor_nou` | FloatField | **obligatori** (553) |
| `motiu` | CharField(255) | blank, default `''` (554) |
| `context` | CharField(50) | **obligatori**; valors: import/manual/fitting/calculated/standard (555) |
| `fitting_ref` | FK→fitting.SizeFitting | SET_NULL, null=True, `related_name='measurement_changes'` (557) |
| `fora_de_tolerancia` | BooleanField | default False (561) |
| `created_at` | DateTime auto_now_add | timestamp immutable (562) |
| `created_by` | FK→AUTH_USER_MODEL | SET_NULL, null=True, `related_name='measurement_changes'` (563) |

**`Meta.ordering`:** `['model', 'pom', 'created_at']` (report investigador, ~571).

**CONFIRMACIÓ CLAU (FET, re-grepat pel documentador):**
`grep -rn "MeasurementChangeLog" --include=*.py | grep -iE "serializ|views|urls"` → **0 resultats.**
Les úniques referències són: definició del model (`models_app/models.py:535,579,583`), el signal que el poblà (`models_app/signals.py:149,186,210,220` — `post_save` de `BaseMeasurement`), un comentari a `fitting/services.py:399`, el command `clone_model_for_qa.py:150,160`, i la migració `0020`.
**Conclusió:** **NO hi ha serializer, ViewSet, ruta ni admin.** El model és viu i es poblà sol, però **és invisible a l'API REST.** Confirma la sospita de la diagnosi ("NO com a timeline").

**Com es consultaria per-model ordenat per temps** (si hi hagués endpoint):
`MeasurementChangeLog.objects.filter(model=<id>).order_by('-created_at')` o `model.measurement_changes.all()`.

---

## Font 5 — `TaskTransition` (5a) + `GateEvent` (5b) · les altres dues fonts del timeline Q2

### 5a — `TaskTransition` · **PARCIAL** (té GET ad-hoc, sense serializer)

**Model:** `tasks/models.py:237-254`. **Camps:**

| Camp | Tipus | Detall |
|---|---|---|
| `model_task` | FK→ModelTask | CASCADE, `related_name='transitions'` |
| `from_status` | CharField(20) \| null | sense choices (valors Pending/Paused/InProgress/Done) |
| `to_status` | CharField(20) | sense choices |
| `by` | FK→accounts.UserProfile | SET_NULL, null=True, `related_name='task_transitions'` |
| `at` | DateTime auto_now_add | |

`Meta.ordering = ['at']`. **FK al model: indirecta** (via `model_task__model`).

**Endpoint de lectura (FET, re-verificat):** `GET /api/v1/models/<model_id>/task-log/` → `model_task_log_view` (`tasks/views_b.py:297`; ruta `tasks/urls.py:72`). Serialització **manual** dins la view, ordre `-at`. Forma reportada: `{"log": [{"id","task_type","from_status","to_status","by","at"}, ...]}`.
**Serializer/ViewSet:** **cap** (només la view ad-hoc). També es llegeix per reverse `mt.transitions.all()` dins l'albarà (Font 2, `models_app/views.py:1208`).

### 5b — `GateEvent` · **NO-EXISTEIX** (cap GET; només POST de creació)

**Model:** `tasks/models.py:256-276`. **Camps:**

| Camp | Tipus | Detall |
|---|---|---|
| `model` | FK→models_app.Model | CASCADE, `related_name='gate_events'` (260) — **FK directa al model** |
| `from_phase` | CharField(20) \| null | sense choices |
| `to_phase` | CharField(20) | valors = FASE_CHOICES |
| `kind` | CharField(10), choices | **`advance`/`regress`**, default `advance` |
| `by` | FK→accounts.UserProfile | SET_NULL, null=True, `related_name='gate_events'` (265) |
| `notes` | TextField \| null | |
| `at` | DateTime auto_now_add | |

`Meta.ordering = ['at']`.

**Endpoints (FET, re-verificat):** només **POST de creació** —
`POST models/<id>/gate/` (`gate_model_view`, `tasks/views_b.py:393`), `POST models/<id>/regress/` (`regress_model_view`, `tasks/views_b.py:419`), i bulk segons report.
**NO hi ha cap GET** que retorni els `GateEvent` d'un model. Creació viva a `tasks/services_d.py` (advance/regress); lectura interna a `tasks/services_e.py:13` (`.filter(...).exists()`). **Cap serializer, ViewSet ni admin.**
**Com es llegiria:** `model.gate_events.all()` (ordering `at`) — però avui no exposat.

> **Síntesi timeline Q2:** de les 3 fonts `a` del timeline, **2 no tenen lectura REST** (`MeasurementChangeLog`, `GateEvent`) i 1 té lectura ad-hoc sense serializer (`TaskTransition` via `task-log`). El merge del timeline és construcció nova.

---

## Font 6 — fase + estat del Model · **VIU** (model)

**Classe:** `Model` — `models_app/models.py:75`.

**Enums reals (literals, FET):**
- `estat` (`models_app/models.py:201`, default `Nou`), `ESTAT_CHOICES` (87-92): **`Nou` · `EnCurs` · `EnRevisio` · `Tancat`** (labels: Nou / En curs / En revisió / Tancat).
- `fase_actual` (`models_app/models.py:202`, default `Pending`), `FASE_CHOICES` (94-101): **`Pending` · `Dev` · `Proto` · `SizeSet` · `PP` · `TOP`**.
- `measurements_version`: IntegerField default 1 (~279).
- `base_size_label`: CharField(20) null/blank (~268).
- `design_freeze_at`: DateTime null/blank (~283). `design_freeze_by`: FK→AUTH_USER_MODEL null/blank (~284).
- Índex compost `['estat','fase_actual']` (`models_app/models.py:321`).

> Els camps de freeze del nucli (`design_freeze_at/by`) **existeixen** com a camps, però el **flux de freeze de 2 senyals** queda diferit a D-7 (taxonomia §5.4); el dashboard llegeix l'estat, no el força.

**related_names que pengen del Model** (FET, font: report Font 6, anclatges verificats parcialment):

| Origen | Camp | related_name | fitxer:línia |
|---|---|---|---|
| TechSheet | `model` (O2O) | `tech_sheet` | tech_sheet_models.py:20 |
| BaseMeasurement | `model` | `base_measurements` | models_app/models.py:491 |
| MeasurementChangeLog | `model` | `measurement_changes` | models_app/models.py:546 |
| SizeCheck | `model` | `size_checks` | models_app/models.py:797 |
| ModelGradingRule | `model` | `grading_rules` | models_app/models.py:640 |
| ModelGradingOverride | `model` | `grading_overrides` | models_app/models.py:597 |
| ConsumptionRecord | `model` (O2O) | `consumption_record` | models_app/models.py:763 |
| ModelTask | `model` | `model_tasks` | tasks/models.py:205 |
| GateEvent | `model` | `gate_events` | tasks/models.py:260 |
| Production | `model` | `productions` | tasks/models.py:327 |
| SizeFitting | `model` | `size_fittings` | fitting/models.py:23 |
| PieceFitting | `model` | `piece_fittings` | fitting/models.py:304 |
| POMAlert | `model` | `pom_alerts` | fitting/models.py:111 |
| FittingSession | `model` | `fitting_sessions` | fitting/models.py:222 |
| TechnicianQueueOrder | `model` | `queue_orders` | planning/models.py:82 |

> Tots amb `related_name` explícit (cap usa default `_set`). Els 5 crítics per Q1 (tech_sheet, base_measurements, size_checks, fitting_sessions, model_tasks) confirmats.

---

## Font 7 — Artefactes vigents (per a Q1) · **VIU** però **dispers** (3 endpoints separats)

> Report Font 7; anclatges del costat model verificats per la Font 6. Els fitxer:línia d'endpoints són report (no re-grepats un a un pel documentador).

### 7a — Fitxa (TechSheet)
- **Model:** `models_app/tech_sheet_models.py:14`. **O2O amb Model** (`related_name='tech_sheet'`). Camp `versio` (PositiveInteger default 1, ~26), `estat` (`obert`/`tancat`).
- **Regla "vigent":** una sola fitxa per model (O2O); `get_or_create(model=...)` (`tech_sheet_editor_views.py:39`). No hi ha versions múltiples enfilades.
- **Endpoint:** `GET /api/v1/models/<id>/tech-sheet/` (`models_app/urls.py:148`), view `TechSheetDetailView` (`tech_sheet_editor_views.py:72`), serializer `TechSheetSerializer` (`tech_sheet_serializers.py:8`).
- **Forma:** `{id, model_id, estat, versio, template_json(dict), locked_by_id|null, locked_by_username|null, updated_at, num_pages, has_content}`.

### 7b — GradingVersion activa
- **Model:** `fitting/models.py:62`. **FK a SizeFitting** (no a Model directe). `version_number` (PositiveInteger default 1), `is_active` (Bool default True), `aprovada` (Bool, segell producció).
- **Regla "vigent":** `_active_grading_version(sf)` filtra `is_active=True` i pren `version_number` màxim (`fitting/services.py:531`); en crear-ne una de nova, desactiva l'anterior (`fitting/services.py:450`).
- **Endpoints:** CRUD `GET /api/v1/fitting/grading-versions/` (filtrable `?size_fitting=&is_active=true`), ViewSet `GradingVersionViewSet` (`fitting/views.py:69`), serializer `GradingVersionSerializer` (`fitting/serializers.py:29`, `__all__`). Taula resolta: `GET /api/v1/fitting/<sf_id>/graded-table/` (`GradedSpecTableView`, `fitting/graded_spec_views.py:22`) que ja filtra `is_active=True` internament i retorna `{size_fitting_id, grading_version_id, base_size, size_labels[], rows[{pom_id, codi, valors{}, deltas{}, ...}]}`.
- ⚠️ **Aresta:** la versió vigent es resol **per SizeFitting, no per Model**. Per al dashboard del model cal el pont model→size_fitting (un model pot tenir-ne); a confirmar quin SizeFitting és "el del model" a la pràctica.

### 7c — Taula base vigent (BaseMeasurement)
- **Model:** `models_app/models.py:478`. **FK a Model** (`related_name='base_measurements'`). `is_active` (Bool default True), `base_value_cm` (Float null), `origen` (STANDARD/IMPORTED/MANUAL/FITTED/CALCULATED/TEMPLATE/CHECKED), `unique_together(model,pom)`.
- **Regla "vigent":** `filter(model=, is_active=True, base_value_cm__isnull=False)` (`models_app/views.py:499`; `services_size_check.py:26`). Soft-delete via `is_active=False` (auditat a Font 4).
- **Endpoint:** `GET /api/v1/models_app/base-measurements/?model=<id>&is_active=true` — ViewSet `BaseMeasurementViewSet` (`models_app/views.py:84`), serializer `BaseMeasurementSerializer` (`models_app/serializers.py:116`, ~14 camps incl. `pom_code`, `nom_fitxa`, `origen`, `updated_at`).

---

## Font 8 — `FittingSession` + `group_*` (projecció convocatòria) · **VIU**

**Model:** `FittingSession` — `fitting/models.py:202`. **Camps rellevants:**

| Camp | Tipus | Detall |
|---|---|---|
| `model` | FK→Model | null=True, `related_name='fitting_sessions'` (222) — XOR amb `garment_set` |
| `garment_set` | FK→GarmentSet | null=True (216) |
| `fase` | CharField (FASE_CHOICES) | (229) |
| `data` | DateField | (230) |
| `start_time`/`end_time` | TimeField \| null | (231-232) |
| `attendees` | **M2M→UserProfile** | `related_name='fitting_sessions'` a UserProfile (254-257) — **font de veritat dels assistents** |
| `assistents` | CharField(300) | text lliure **DEPRECAT** (234) |
| `responsable` | FK→UserProfile | null, `related_name='fitting_sessions_responsable'` (236) |
| `estat` | CharField | `Programada`/`Oberta`/`Tancada`/`Anullada` (242) |
| `convocatoria` | UUIDField \| null | db_index; agrupa sessions en bloc (NULL=individual) (258) |
| `started_at`/`finished_at` | DateTime \| null | marques reals (262-267) |
| `duracio_minuts` | PositiveInteger \| null | (251) |
| `created_at`/`created_by` | DateTime / FK | (244-245) |

**Camí ORM "aquest model està convocat a quines sessions, amb quins assistents"** (FET):
`model.fitting_sessions.all()` → per sessió `session.attendees.all()` (M2M a UserProfile) i `session.convocatoria` (UUID grup).

**Serializers:** `FittingSessionListSerializer` (`fitting/serializers.py:90`) exposa `attendees_info` (SerializerMethodField → `[{id, nom, color_avatar}]`, ~112-116), `target`, `responsable_nom`, `n_peces`, `convocatoria`, etc. `FittingSessionDetailSerializer` (~119) afegeix `piece_fittings`, `photos`, `can_advance`.

**Accions `group_*`** (report investigador, `fitting/views.py:337-417` / `fitting/services.py:762-974`): `group_reschedule` (PATCH), `group_add_model` (POST), `group_remove_model` (DELETE), `group_attendees` (PATCH `{attendee_ids:[...]}`), `group_remove` (DELETE bloc). Operen per `convocatoria` UUID → **el PM pot operar per-model dins el grup** (coincideix amb taxonomia §5.2).

> ✅ La convocatòria al dashboard del model és una **projecció read** d'`model.fitting_sessions` amb `attendees_info` — no cal construir res. ⚠️ `assistents` (text) és deprecat; usar `attendees` (M2M).

---

# 💡 PROPOSTA (a validar pel CTO) — què s'agrega directe vs què necessita endpoint nou

> Tot el que segueix és **proposta de disseny**, separada dels fets. No s'ha implementat res.

## A. Fonts que el dashboard pot AGREGAR DIRECTAMENT (ja són servibles)

| Font | Com agregar | Per a |
|---|---|---|
| F1 `by_model` | llegir la fila del model (o un detall anàleg) | Q4 comptadors de tasques |
| F2 `albara` | cridar `models/<id>/albara/` | Q1 esforç ⑤ M + `per_technician` + `history` |
| F3 `pom-alerts` | `GET pom-alerts/?model=<id>&estat=Pendent` | Q3 atenció tècnica |
| F6 estat/fase | del detall del Model + related_names | Q1 "on sóc" |
| F7a fitxa | `models/<id>/tech-sheet/` | Q1 artefacte vigent (fitxa vN) |
| F7c taula base | `base-measurements/?model=<id>&is_active=true` | Q1 taula base vigent |
| F8 convocatòria | `model.fitting_sessions` + `attendees_info` | projecció sessió |

→ **💡 PROPOSTA d'agregació:** un endpoint **read compositor** `GET models/<id>/dashboard/` que faci el fan-in d'aquestes 7 fonts vives en una sola resposta (estalvia 5-7 rodades del frontend). Cap dada nova; només composició. Respecta el **doble abast** (taxonomia nota 1): part és abast-model (esforç, comptadors) i part és abast-espectador (handoffs dirigits a mi) — els endpoints han de saber qui pregunta.

## B. Fonts que NECESSITEN endpoint nou (el "timeline merge", Q2)

| Font | Què falta | Proposta |
|---|---|---|
| F4 `MeasurementChangeLog` | **cap** serializer/view/url | crear lectura read-only per model, ordre `-created_at` |
| F5b `GateEvent` | **cap GET** (només POST creació) | crear lectura read-only per model (`model.gate_events`) |
| F5a `TaskTransition` | té `task-log` ad-hoc **sense serializer** | normalitzar o incloure al merge |

→ **💡 PROPOSTA endpoint nou:** `GET models/<id>/timeline/` que faci **merge ordenat per temps** de les 3 fonts `a` (canvis de mesura + gates + transicions de tasca), normalitzant a un esdeveniment comú `{at, kind, actor, payload}`. És **l'única construcció backend nova essencial** que la taxonomia ja anticipa (§5.5 punt 2). Decisió Q2 ja presa a la taxonomia §7: **v1 = "últims canvis"**, sense last-seen per-usuari (no cal taula nova de vist/no-vist).

→ **💡 PROPOSTA (handoff lleuger, F absent):** la taxonomia §5.1 demana una primitiva nova de handoff dirigit (Q3 entrant + Q4 sortint). **Cap de les 8 fonts la cobreix** — no existeix avui. És construcció nova de coordinació (④), independent del timeline. Confirmat per absència: cap font investigada conté un objecte emissor→destinatari amb estat pendent/resolt.

## C. Arestes per al CTO (descobertes, no resoltes aquí)

1. **Grading vigent és per `SizeFitting`, no per `Model`** (F7b). Cal definir quin SizeFitting és "el del model" per pintar "DXF/grading vN vigent" a Q1.
2. **Discrepància F3:** verificar el valor d'`estat` que fixen els disparadors a `pom/s10_views.py`/`s11_views.py` (el report deia `'Obert'`, que **no és un choice vàlid**).
3. **`TaskTransition` es serveix dos cops** amb formes diferents: dins `albara` (`from/to/by/at`) i dins `task-log` (`+id, task_type, from_status/to_status`). El merge del timeline hauria d'unificar.
4. **`assistents` (text) deprecat** vs `attendees` (M2M) a FittingSession — el dashboard ha de llegir només `attendees`.

---

# Apèndix — fora d'scope detectat (ANOTAT, no tocat)

- `models_app/admin.py` està **buit** (report Font 4): `MeasurementChangeLog`, `GateEvent`, `TaskTransition` no són ni inspeccionables per admin Django. Deute menor d'observabilitat; no s'ha tocat.
- Diversos endpoints de lectura crítics serialitzen **a mà dins la view** (F1 `shape`, F2 albarà, F5a `task-log`) en lloc d'un serializer reutilitzable. Deute de consistència; el merge del timeline és l'ocasió natural per normalitzar-ho. No s'ha tocat.

---

*Document de diagnosi. READ-ONLY respectat: l'únic fitxer escrit és aquest. Cap codi de producte,
migració ni config modificats. Exemples JSON il·lustratius (cap resposta HTTP autenticada obtinguda).
Anclatges crítics de Q1/Q2 re-verificats pel documentador; la resta marcada com a report d'investigador.*
