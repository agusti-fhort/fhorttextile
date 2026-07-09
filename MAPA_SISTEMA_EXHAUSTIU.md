# MAPA_SISTEMA_EXHAUSTIU — Diagnosi READ-ONLY del sistema FTT (vell vs nou)

> Diagnosi Patró A (director + investigadors read-only + documentador) sota PROTOCOL_FASE_B.
> READ-ONLY absolut. Cap codi tocat. FETS amb `fitxer:línia`. Decisions = Agus (⚖️).
> Bloc BD: només l'orquestrador (SELECT read-only via schema_context fhort/public).
> Repo: `/var/www/ftt-staging/backend` (Django django-tenants) + `frontend/` + `frontend-backoffice/`.
> Generat: 2026-06-22.

## Llegenda
- 🔴 **VELL/NOU** — codi mort viu, dobles camins, òrfenes, documentat-no-implementat.
- 🔗 **CONNECTA AMB** — blast radius: què es trenca si ho toques.
- 🅰️/🅱️ — LÍNIA A (plataforma) / LÍNIA B (servei) / ambdós.
- ⚖️ **PER DECIDIR (Agus)** — decisió humana, no la pren l'agent.

---

## Índex dels 16 dominis (estat de la diagnosi)

- [x] 1 — Multi-tenancy i fonaments
- [x] 2 — Identitat / usuaris (capabilities, gates)
- [x] 3 — Model: entitat + CICLE DE VIDA/ESTATS **[deep-dive, node de facturació]**
- [x] 4 — Tasques / Kanban (TaskType, transition_task, gates, claim, timers)
- [x] 5 — Planning / Pla de treball
- [x] 6 — Calendari (bug replicació diària)
- [x] 7 — POM / mesures
- [x] 8 — Grading
- [x] 9 — Fitting / Size Check
- [x] 10 — Import (wizard, 2-call, "document mana", mismatch block)
- [x] 11 — Fitxa tècnica (lock TTL30, Konva, timer gap)
- [x] 12 — Size systems
- [x] 13 — Backoffice / facturació (ModelConsumptionEvent, camí comptador)
- [x] 14 — Frontend (Shell, EditableTable, tokens/KONVA_COL, i18n, Tabler outline-only)
- [x] 15 — Creuament LÍNIA A/B
- [x] 16 — Seeds / migracions / orfes

---

## 🔬 BLOC BD DE L'ORQUESTRADOR (deep-dive domini 3 — verificat a BD, read-only)

> Aquestes dades surten de SELECTs read-only de l'orquestrador (els investigadors NO tenen BD).
> Schema tenant = `fhort`; schema compartit = `public`. Únic tenant existent: `fhort`.

**Camps d'estat del Model** (`models_app/models.py:201-204`): `estat` (ESTAT_CHOICES:
Nou/EnCurs/EnRevisio/Tancat), `fase_actual` (FASE_CHOICES: Pending/Dev/Proto/SizeSet/PP/TOP,
default `Pending`), `consumption_started_at` (DateTimeField nullable — flag de meritació).

Recompte real `models_app_model` (18 models, schema fhort), agrupant `estat × fase_actual × (consumption_started_at IS NOT NULL)`:

| estat | fase_actual | merited | count |
|---|---|---|---|
| Nou | Pending | f | 12 |
| Nou | Dev | t | 4 |
| Nou | Proto | t | 1 |
| Nou | PP | t | 1 |

- **`SELECT DISTINCT estat` → només `'Nou'`.** 🔴 El camp `estat` (Nou/EnCurs/EnRevisio/Tancat)
  és **CODI MORT VIU**: cap model ha sortit mai de `Nou`. El cicle de vida real el porten
  `fase_actual` + `consumption_started_at`, NO `estat`. Hi ha doncs **definicions competidores**
  d'"estat del model": una declarada (`estat`, morta) i una efectiva (`fase_actual`+flag).
- **Meritació = fase avançada:** els 6 models merited són exactament els 6 que han sortit de
  `Pending` (Dev×4, Proto×1, PP×1). Cap model en `Pending` està merited. Consistent amb el
  trigger Pending→Dev de `tasks/services_c.py:88-108`.
- Totals: 18 models, **6 merited**, 0 amb `design_freeze_at`.

**ModelTask** (`tasks/models.py:201-234`, `status` STATUS_CHOICES Pending/Paused/Done/...):
`Pending=70, Paused=7, Done=4` (81 instàncies). `TaskTransition.to_status`:
`InProgress=29, Paused=23, Done=6`. `GateEvent` (from→to phase): Proto→SizeSet=2, SizeSet→PP=2,
TOP→PP=1, SizeSet→Proto=1, PP→TOP=1, Dev→Proto=1, PP→SizeSet=1 (transicions de fase NO lineals;
hi ha retrocessos SizeSet→Proto i PP→SizeSet).

**ModelConsumptionEvent** (schema `public`, `backoffice/models.py:63`): 11 events, 0 opaque_ref
duplicats, tots període `2026-06`, 3 codi_client (BRW=5, FTT=3, LOS=3), `merited_at` 2026-06-05 → 06-22.
- 🔴 **DISCREPÀNCIA 11 events (public) vs 6 models merited (tenant).** opaque_ref és UUID i no hi
  ha duplicats, però hi ha 5 events més que models actualment merited. Hipòtesi a verificar pels
  investigadors al codi: `clone_model_for_qa.py:83` despulla `consumption_started_at` en clonar
  (deixa events públics orfes), i/o `reconcile_consumption` reemet. ⚖️ Definir si l'event públic
  és la font de veritat de facturació o ho és el flag del tenant — quan divergeixen, quin mana.

---

## Domini 1 — Multi-tenancy i fonaments

[x] fet

I have a complete picture. Producing the report.

### Entitats i camps
- `Plan` 🅰️ — pla comercial SaaS (`nom`, `tipologia`, `preu_mensual`, `max_models_actius`, `max_usuaris`, `storage_gb`, `ia_credits_mes`, `feature_flags` JSON, `actiu`, `models_inclosos`, `preu_model_extra`, `moneda_pla`). `fhort/tenants/models.py:12-55`. Viu només a `public` (SHARED).
- `Client(TenantMixin)` 🅰️ — el tenant. Camps de provisió (`schema_name` heretat del mixin, `codi_tenant` unique 3 chars, `auto_create_schema=True`, `auto_drop_schema=False`), comercials (`plan` FK, `tipologia`, `feature_flags`), cicle de vida (`estat`, `data_alta`, `onboarding_complet`, `data_suspensio`, `data_baixa`, `motiu_baixa`, `gratis_fins`, `nota_comercial`), preferències (`moneda`, `unitats`, `idioma`), fiscals/VAT (`rao_social`, `nif`, `pais`, adreça estructurada, `vat_number`, `vat_validat`, `tipus_client`, `regim_vat`), Stripe (`stripe_customer_id`, `metode_pagament`, `stripe_payment_method_id`). `fhort/tenants/models.py:58-210`.
- `Domain(DomainMixin)` 🅰️ — domini→tenant (`domain`, `tenant`, `is_primary`); cos buit (`pass`). `fhort/tenants/models.py:213-214`.
- `TenantContacte` 🅰️ — contactes del tenant al `public` (`client` FK, `nom`, `cognom`, `carrec`, `email`, `telefon`, `principal`). `fhort/tenants/models.py:217-239`.
- `PAISOS_UE` frozenset (pivot VAT) `fhort/tenants/models.py:5-9`.

### Relacions / FK (marca cross-schema amb db_constraint=False)
- `Client.plan → Plan` (PROTECT, null) `fhort/tenants/models.py:109`. Tot dins `public`, cap problema cross-schema.
- `Domain.tenant → Client` (CASCADE) `fhort/tenants/migrations/0001_initial.py:62`. Dins `public`.
- `TenantContacte.client → Client` (CASCADE) `fhort/tenants/models.py:220`. Dins `public`.
- FKs cross-schema (app SHARED `pom` que té taula a `public` apuntant a models tenant-only) — **`db_constraint=False`**:
  - `pom.GarmentPOMMap.garment_type_item → tasks.GarmentTypeItem` `fhort/pom/models.py:421-423`.
  - `pom.ItemBaseMeasurement.garment_type_item → tasks.GarmentTypeItem` `fhort/pom/models.py:460-461`.
  - `models_app.ModelGradingRule.pom → pom.POMMaster` `fhort/models_app/models.py:646-649`.
  - `models_app.SizeCheckLine.pom → pom.POMMaster` `fhort/models_app/models.py:831-834`.
- Referència fluixa (sense FK) PUBLIC↔tenant: `backoffice.ModelConsumptionEvent.codi_client` és un CharField que iguala `Client.codi_tenant`, i `opaque_ref` (UUID) iguala el `ConsumptionRecord.opaque_ref` del tenant. `fhort/backoffice/models.py:63-77`. Aquest és el patró triat per parlar entre public i tenant SENSE FK.

### Endpoints + gating (qui pot, quina capability/gate)
- Routing per schema: `ROOT_URLCONF='fhort.urls'` (tenant) vs `PUBLIC_SCHEMA_URLCONF='fhort.urls_public'` (public). `fhort/settings.py:95-96`.
- `fhort/urls_public.py:21-36` (schema `public`): admin, JWT, schema/docs, `api/backoffice/v1/` (backoffice). NO inclou apps de producte.
- `fhort/urls.py:14-34` (schema tenant): admin, JWT, `api/v1/` → accounts, models_app, pom, fitting, tasks, planning.
- Backoffice tenants/plans: `fhort/backoffice/urls.py:12-15` registra `tenants` (ClientViewSet), `plans`, `serveis`, `contractes`.
- Gating: `ClientViewSet` és `ReadOnlyModelViewSet` ampliat; permís base `IsAuthenticated + HasBackofficeRole()`; accions mutadores (`ADMIN_ACTIONS = create, partial_update, update_estat, contactes, contacte_detail`) exigeixen rol `ADMIN`. `fhort/backoffice/views_tenants.py:27,40-44`. `PlanViewSet` tot ADMIN `fhort/backoffice/views_tenants.py:221`. `HasBackofficeRole` factory a `fhort/backoffice/views.py:58-73`.
- NO s'exposa PUT ni DELETE de tenant deliberadament (esborrar Client deixaria schema orfe). `fhort/backoffice/views_tenants.py:30-35`.

### Frontend que hi penja
- `frontend-backoffice/src/api/tenants.js` — base `/api/backoffice/v1`, crida `tenants/`, `tenants/{id}/`, `update_estat/`, `contactes/`, PATCH i POST. `frontend-backoffice/src/api/tenants.js:5-34`.
- Pàgines: `frontend-backoffice/src/pages/TenantsPage.jsx`, `TenantDetailPage.jsx`, `TenantFormPage.jsx`, `ContractFormPage.jsx`.
- El frontend de producte (`frontend/`) NO toca tenants directament: parla amb el seu propi subdomini (django-tenants resol el tenant via Host).

### Màquina d'estats / signals (PROPIETARI ÚNIC de cada estat: qui l'escriu)
- `Client.estat` (onboarding/actiu/suspes/baixa) — **propietari únic**: `ClientViewSet.update_estat` `fhort/backoffice/views_tenants.py:106-149` (segella `data_suspensio`/`data_baixa`). També editable via `ClientUpdateSerializer` (PATCH) `fhort/backoffice/serializers_tenants.py:84`.
- `Client.regim_vat` — **calculat, mai escrit a mà**: `recalcular_regim_vat()` cridat sempre des de `Client.save()` `fhort/tenants/models.py:193-210`. `ClientUpdateSerializer` no l'inclou (read-only de facto).
- Provisió de schema — propietari: `django-tenants` via `TenantMixin.save()` quan `auto_create_schema=True`; disparat per `serializer.save()` FORA de `transaction.atomic` a `ClientViewSet.create` `fhort/backoffice/views_tenants.py:56-69` (+ crea `Domain` i `BackofficeActionLog`).
- Senyal cross-schema de consum: `tasks.signals.model_consumption_started` (`fhort/tasks/signals.py:17`) s'emet a `fhort/tasks/services_c.py:108-114` dins el schema tenant; el receiver `on_model_consumption_started` salta a `public` amb `schema_context('public')` i escriu `ModelConsumptionEvent` `fhort/backoffice/receivers.py:7-18` (registrat a `backoffice/apps.py:8`).
- `UserProfile` (tenant) creat per signal `post_save` de User amb guarda d'schema (`get_public_schema_name()`): mai a `public`. `fhort/accounts/signals.py:19-33`.

### Serveis d'única entrada reaprofitables
- `Client.recalcular_regim_vat()` — única derivació del règim VAT. `fhort/tenants/models.py:193-204`.
- `Client.es_actiu` / `es_gratuit` (properties pont) — `fhort/tenants/models.py:181-191`.
- `django_tenants.utils.schema_context(schema)` — única manera correcta de creuar schemas (usat ~30 llocs: receivers, comandes pom de seed, `models_app/extraction_views.py:210`, `pom/s9_views.py:119`).
- `get_public_schema_name()` — guarda "estic a public?" (`accounts/signals.py`, `create_backoffice_admin.py:49`).
- `customer_code_for(model)` `fhort/models_app/services.py:25-35` — ÚNICA font del prefix de 3 chars; unifica camins que abans divergien (hardcode 'FTT', `schema_name[:3]='FHO'`).

### 🔴 VELL/NOU (codi mort viu · dobles camins · òrfenes · documentat-no-implementat)
- **Doble camí `Client.actiu` (bool legacy) vs `Client.estat`**: `actiu` (`fhort/tenants/models.py:112`) es conserva "per no trencar DB/codi" però NO s'escriu enlloc del codi d'app (cap `client.actiu=`); la font de veritat és `estat`, amb `es_actiu` com a pont (`models.py:181-184`). `actiu` és camp òrfe viu.
- **Camp LEGACY explícit**: `Client.adreca_fiscal` marcat "substituït per l'adreça estructurada; es buidarà via migració" `fhort/tenants/models.py:128`. Encara exposat al `ClientDetailSerializer` `serializers_tenants.py:58` → doble representació d'adreça (linia1/linia2/ciutat/... vs `adreca_fiscal`).
- **Plan.tipologia vs Client.tipologia divergents**: `Plan` té 3 valors (estudi/marca/enterprise) `models.py:27-31`; `Client` només 2 (estudi/marca) `models.py:61-64`. Possible desalineament (enterprise no assignable a Client).
- **`tenants/admin.py` i `tenants/views.py` buits** (`# Register your models here.` / `# Create your views here.`): cap admin registrat per Client/Domain/Plan/TenantContacte; tota la gestió va per API backoffice. `fhort/tenants/admin.py:1-3`, `fhort/tenants/views.py:1-3`.
- **Orfe acceptat documentat**: si falla `Domain.objects.create` després del `serializer.save()`, queda Client+schema orfe; cleanup "manual / comanda futura" — comanda inexistent (`grep` no troba cap `delete_tenant`/`drop_schema`). `fhort/backoffice/views_tenants.py:66-67`.
- **`auto_drop_schema=False`**: esborrar un Client no elimina el schema PostgreSQL → orfes per disseny. `fhort/tenants/models.py:172`.
- `tenants/tests.py` present però no inspeccionat com a font de veritat (tests, no codi viu).

### 🔗 CONNECTA AMB (blast radius: què es trenca si ho toques)
- `Client.codi_tenant` és el pivot universal: deriva `schema_name` (`serializers_tenants.py:138`), el domini (`views_tenants.py:68`), iguala `Customer.codi`/`is_self` al tenant (`models_app/services.py:9-13`) i `ModelConsumptionEvent.codi_client` a public (`backoffice/models.py:68`). Tocar-lo trenca facturació + codi_intern + routing.
- `SHARED_APPS`/`TENANT_APPS` (`settings.py:36-73`): `pom` viu a AMBDÓS (Global models a public, resta replicada a cada tenant per a FKs cross-schema); `backoffice` NOMÉS public. Moure una app entre llistes requereix re-migrar tots els schemas.
- Les 4 FK `db_constraint=False` depenen que el CASCADE l'emuli Django al collector, no la BD. Si algú hi posa constraint real, peta a `public` (taula tasks/pom no existeix igual allà).
- `MIDDLEWARE`: `CorsMiddleware` ABANS de `TenantMainMiddleware` (preflight OPTIONS de frontends cross-domini) `settings.py:81-93`. Reordenar trenca CORS o resolució de tenant.
- Senyal `model_consumption_started`: emissor a `tasks/services_c.py`, receiver a `backoffice/receivers.py`; el càlcul de facturació (`reconcile_consumption.py`) recorre tenants amb `schema_context`. Trencar el senyal trenca la meritació de models.

### 🅰️/🅱️ Línia
- Tot el domini 1 és **🅰️ (plataforma)**: `tenants` (Client/Domain/Plan/TenantContacte), `settings`, routing public/tenant, `backoffice` (registre de tenants i facturació). Infra multi-tenant comuna, no facturable per model.
- Punt de frontera 🅰️🅱️: el senyal de consum i `ModelConsumptionEvent` — neixen del treball 🅱️ (arrencar un model al tenant) però materialitzen a la capa 🅰️ de facturació al public.

### ⚖️ PER DECIDIR (Agus)
- Eliminar definitivament `Client.actiu` (bool) i `Client.adreca_fiscal` (LEGACY) amb migració de dades, o mantenir-los com a compatibilitat? Avui són pes mort exposat.
- Crear la "comanda futura" de cleanup de Client+schema orfe (creació de Domain fallida / baixa de tenant amb `auto_drop_schema=False`). Avui no existeix.
- Alinear `Plan.tipologia` (3 valors, inclou enterprise) amb `Client.tipologia` (2 valors): un Client amb pla Enterprise no pot reflectir-ho a la seva pròpia tipologia.

### Obert / dubtós
- No he inspeccionat `fhort/tenants/tests.py` (no és codi viu de domini); pot contenir asserts sobre provisió que confirmin/contradiguin el flux.
- No he confirmat com s'executa `migrate_schemas` ni l'arrencada inicial de tenants (cap comanda pròpia al repo; s'assumeix el `migrate_schemas` estàndard de django-tenants, no verificable des del codi de l'app).
- `DATABASE_ROUTERS=['django_tenants.routers.TenantSyncRouter']` (`settings.py:127`) governa a quin schema va cada model segons SHARED/TENANT; el detall de com decideix per `pom` (que és a les dues llistes) depèn de django-tenants i no del codi del repo.

---

## Domini 2 — Identitat / usuaris (capabilities, gates)

[x] fet

Tinc tot el que necessito. El `DesignFreezePanel` no comprova cap capability al front (només `disabled={loading}`), coherent amb el backend que només exigeix `IsAuthenticated`. Redacto.

### Entitats i camps
- `UserProfile` (accounts/models.py:5) — 1:1 amb `AUTH_USER_MODEL` (Django `User` estàndard, no custom). Camps: `nom_complet`, `rol_nom` (CharField lliure, NO choices — la validació de rols vàlids és a nivell de serializer/view contra `ROLE_CAPABILITIES`), `actiu`, `cost_hora`, `color_avatar`, `permisos` (JSON `{"grant":[],"revoke":[],"tasks":[]}`), `jornada_override` (JSON, Sprint A calendari). 🅰️🅱️
- `TenantConfig` (accounts/models.py:30) — config global per tenant (singleton pk=1 via `get_or_create_default`, accounts/models.py:48). Camps: `unitat_mesura`, `norma_referencia`, `nom_empresa`, `logo_url`. 🅰️
- No hi ha User model custom: `AUTH_USER_MODEL` no es redefineix (settings.py no el toca; s'usa `get_user_model()` per defecte = `auth.User`). 🅰️
- Camp d'identitat al domini de models: `Model.design_freeze_at` / `Model.design_freeze_by` (FK a `User`, `on_delete=SET_NULL`, `related_name='design_freezes'`) (models_app/models.py:283-289). 🅱️

### Relacions / FK (marca cross-schema amb db_constraint=False)
- `UserProfile.user` → OneToOne `User` (accounts/models.py:6, `on_delete=CASCADE`). User i UserProfile viuen tots dos a l'schema del tenant (el signal NO crea profile a 'public', signals.py:24). No hi ha `db_constraint=False` enlloc del domini.
- `Model.design_freeze_by` → FK `User` (models_app/models.py:284, `SET_NULL`).
- `ModelTask.assignee` → FK a `UserProfile` (NO a User) — confirmat per comentaris a serializers.py:23 i la lògica de `scope_model_task_queryset` que filtra per `assignee=profile` (capabilities.py:95). Per això `MeSerializer` exposa `profile_id` separat d'`id` (serializers.py:25).
- No s'han trobat FK cross-schema amb `db_constraint=False` dins d'aquest domini. — cap addicional —

### Endpoints + gating (qui pot, quina capability/gate)
Tots sota `/api/v1/` (accounts/urls.py). Capability via `HasCapability` + `required_capability` (capabilities.py:46):
- `POST /api/token/` → `TokenObtainPairView` SimpleJWT (urls.py:18), camp `username` però accepta email via `EmailOrUsernameBackend` (backends.py:11). 🅰️
- `GET /api/v1/me/` → `IsAuthenticated` (views.py:40). 🅰️
- `POST /api/v1/me/change-password/` → `IsAuthenticated`, autoservei sense contrasenya actual (views.py:47-64). 🅰️
- `GET/RETRIEVE /api/v1/users/` → `IsAuthenticated` (selector) (views.py:89-90). 🅰️🅱️
- `POST /api/v1/users/` (alta) → `manage_users` (views.py:91, 105). 🅰️
- `PATCH /api/v1/users/<id>/` → `manage_users` (views.py:91, serializer `UserAdminSerializer`). 🅰️
- `POST /api/v1/users/bulk/` (set_role/set_task/set_active) → `manage_users` (views.py:130). 🅰️
- `POST /api/v1/users/<pk>/reset-link/` → `manage_users`, retorna URL (NO envia mail) (views.py:179). 🅰️
- `GET /api/v1/password-reset/validate/` → `AllowAny` (views.py:204). 🅰️
- `POST /api/v1/password-reset/confirm/` → `AllowAny` (views.py:215). 🅰️
- `POST /api/v1/models/<id>/aprovar-design-freeze/` → **només `IsAuthenticated`** (pom/wizard_views.py:16-18). 🅱️
- `POST /api/v1/models/<id>/gate/` i `/regress/` i `/gates/bulk/` i `GET /gates/ready/` → `close_gates` (tasks/views_b.py:444-526). 🅱️

Mapa capability→endpoint (consumidors fora d'accounts):
- `define_tasks`: ModelTask CRUD (tasks/views_b.py:39,73,256), planning (planning/views.py:32).
- `execute_tasks`: transició/execució de tasques (tasks/views_b.py:352, models_app/views.py:1185).
- `schedule_fittings`: fitting (fitting/views.py:45), tasks (tasks/views_b.py:529), planning (planning/views.py:36).
- `close_gates`: gates (tasks/views_b.py:440).
- `configure`: pom (pom/views.py:38, pom/size_map_views.py:21), size_map, tech sheet override (models_app/tech_sheet_editor_views.py:121,190), planning config (planning/views.py:28), customer/logo (tasks/views_b.py:562,652).
- `view_team_tasks`: scope querysets ModelTask (planning/views.py:345, capabilities.py:88).
- `manage_users`: només accounts (matriu d'usuaris).

### Frontend que hi penja
- `frontend/src/store/auth.js` — store Zustand: `login` (POST /api/token/), `fetchMe`, `hasCapability(cap)` (auth.js:51, "helper cosmètic: el backend ja enforça"). Font única de capabilities al front (auth.js:7,40).
- `frontend/src/pages/UsersRoles.jsx` — matriu d'usuaris/rols; `canManage = capabilities.includes('manage_users')` (UsersRoles.jsx:61); llista de rols hardcodejada (UsersRoles.jsx:11). 🅰️
- `frontend/src/pages/UserProfilePage.jsx` — perfil/canvi de contrasenya autoservei. 🅰️
- `frontend/src/components/layout/Sidebar.jsx` — gating de menú per `manage_users`/`configure`/`define_tasks` (Sidebar.jsx:195-197). 🅰️🅱️
- `frontend/src/components/DesignFreezePanel.jsx` — botó aprovar design freeze; **NO comprova cap capability**, només `disabled={loading}` (DesignFreezePanel.jsx:65-66). 🅱️
- `frontend/src/pages/KanbanTasks.jsx` — `canCloseGates = capabilities.includes('close_gates')` (KanbanTasks.jsx:67). 🅱️
- `frontend-backoffice/src/store/authStore.js`, `pages/LoginPage.jsx`, `api/auth.js` — login del backoffice (línia A, plataforma). 🅰️

### Màquina d'estats / signals (PROPIETARI ÚNIC de cada estat: qui l'escriu)
- **Creació de `UserProfile`**: PROPIETARI = signal `post_save(User)` `create_user_profile` (signals.py:19). Crea amb `rol_nom=DEFAULT_ROLE='technician'` (capabilities.py:28) i `permisos={}`, NOMÉS dins schema de tenant (guarda `connection.schema_name != public`, signals.py:24). `UserCreateSerializer.create` NO crea profile a mà: recupera el creat pel signal i l'actualitza (serializers.py:232-238).
- **`rol_nom`/`actiu`/`permisos`**: escrits per `UserAdminSerializer.update` (serializers.py:172) i per `UserViewSet.bulk` (views.py:160-176). Ambdós gated `manage_users`.
- **`design_freeze_at`/`design_freeze_by`**: PROPIETARI = `approve_design_freeze_view` (pom/wizard_views.py:35-39); idempotent (si ja existeix retorna l'existent, wizard_views.py:28). També posa `estat='En curs'` si era 'Nou'. Es netegen al clonatge QA (clone_model_for_qa.py:83).
- **`last_login`**: SimpleJWT `UPDATE_LAST_LOGIN=True` (settings.py:196).
- Cap signal addicional al domini (només signals.py:19).

### Serveis d'única entrada reaprofitables
- `get_capabilities(user)` (capabilities.py:31) — "Font de veritat única" de capacitats efectives = base del rol `| grant - revoke`.
- `HasCapability` (capabilities.py:46) — permís DRF reaprofitat per TOTES les apps (patró `_NomCap(HasCapability)` o `perm=HasCapability(); self.required_capability=...`).
- `get_allowed_task_types(user)` (capabilities.py:57) — allow-list de `TaskType.code` executables; admin = bypass total. Usat per tasks i planning.
- `scope_model_task_queryset(qs, user)` (capabilities.py:74) — scope row-level de ModelTask (3 branques: view_team / define+null / pròpies). Usat per tasks i planning.
- `ROLE_CAPABILITIES` / `ALL_CAPABILITIES` / `DEFAULT_ROLE` (capabilities.py:20-28) — vocabulari controlat de rols i caps.

### 🔴 VELL/NOU (codi mort viu · dobles camins · òrfenes · documentat-no-implementat)
- **Doble camí de gating de design_freeze (incoherència real)**: `approve_design_freeze_view` només exigeix `IsAuthenticated` (pom/wizard_views.py:17), mentre que la resta del govern de fase (gate/regress) exigeix `close_gates` (tasks/views_b.py:444). Un `technician` (que NO té `close_gates`) pot congelar el design freeze. El front tampoc ho protegeix (DesignFreezePanel.jsx no mira capabilities). PER DECIDIR: el design freeze és un gate de govern o una aprovació de tècnic? El docstring diu literalment "The technician approves" (wizard_views.py:21), però conceptualment "qui pot congelar" és pregunta de gate.
- **Camp `permisos.grant`/`revoke` òrfenes a la UI**: `get_capabilities` suporta overrides per-usuari `grant`/`revoke` (capabilities.py:41-43), però la matriu del front (`UsersRoles.jsx`) i el `bulk` (views.py) només manipulen `rol_nom`, `actiu` i `permisos.tasks`. No s'ha trobat cap camí que escrigui `grant`/`revoke` → funcionalitat backend sense entrada d'usuari (documentat-no-implementat al front). (No verificat si l'editor individual de UsersRoles.jsx els escriu; veure Obert.)
- **`accounts/admin.py` buit** (admin.py:1-4) — UserProfile/TenantConfig no registrats a Django admin. No és mort, però és absència, no doble camí.
- **`avatar_url` sempre None** (serializers.py:46-49) — camp d'API documentat però no implementat (no hi ha ImageField); placeholder explícit.
- **`reset-link` retorna URL però no envia mail** (views.py:179) — disseny deliberat, no error; cal canal manual.
- **`TenantConfig`** (accounts/models.py:30): cal verificar consumidors (veure Obert) — té pinta de poder solapar-se amb config de `tasks`/`pom` (unitat de mesura). No confirmat aquí.

### 🔗 CONNECTA AMB (blast radius: què es trenca si ho toques)
- `get_capabilities` / `HasCapability`: si en canvies la signatura o semàntica, es trenca el gating de **tasks, fitting, pom, planning, models_app** (totes importen de `fhort.accounts.capabilities`). És el cor transversal.
- `UserProfile.rol_nom` (CharField lliure): qualsevol valor fora de `ROLE_CAPABILITIES` → `get_capabilities` retorna set buit (capabilities.py:39) → usuari sense cap permís efectiu. La integritat depèn de la validació de serializer, no de la BD.
- `ModelTask.assignee` → `UserProfile` (NO User): tocar la relació trenca `scope_model_task_queryset` i els selectors del front (que envien `profile_id`, serializers.py:77).
- Signal `create_user_profile`: si es desactiva, `UserCreateSerializer.create` peta a `UserProfile.objects.get(user=user)` (serializers.py:234).
- `design_freeze_by` (SET_NULL): esborrar un User no trenca el Model però perd l'autoria.

### 🅰️/🅱️ Línia
- 🅰️ (plataforma): `UserProfile` model + signal, `TenantConfig`, autenticació (JWT, EmailOrUsernameBackend), `me/`, change-password, password-reset, matriu d'usuaris (`manage_users`), tot el sistema `capabilities.py`. Backoffice auth.
- 🅱️ (servei): l'aplicació concreta de capabilities al flux del client — `close_gates` sobre gates, `define_tasks`/`execute_tasks` sobre ModelTask, `schedule_fittings`, design_freeze sobre Model. El motor (capabilities.py) és A; l'ús sobre entitats del client és B.
- 🅰️🅱️: `GET /users/` (selector, usat per assignar responsables de models = B, però mecanisme = A).

### ⚖️ PER DECIDIR (Agus)
- **Qui pot congelar (design_freeze)**: avui qualsevol `IsAuthenticated`, incloent technician (pom/wizard_views.py:17). Cal capability dedicada (p.ex. `close_gates` o una de nova `design_freeze`)? És el buit de gating més clar del domini.
- **`permisos.grant`/`revoke`**: mantenir-ho com a feature backend sense UI, exposar-ho a la matriu, o eliminar-ho? Avui és superfície oberta sense entrada controlada.
- **`rol_nom` com a CharField lliure** vs choices/FK a taula de rols: el vocabulari de rols viu hardcodejat en codi (`ROLE_CAPABILITIES`) i replicat al front (UsersRoles.jsx:11). Doble font.
- **`TenantConfig.unitat_mesura`/`norma`** vs config equivalent en altres dominis (talles/POM): possible solapament — cal una única font de configuració del tenant?

### Obert / dubtós (el que no he pogut determinar amb certesa)
- Si `UsersRoles.jsx` (editor individual, no el bulk) escriu `permisos.grant`/`revoke` o només `permisos.tasks` — no he llegit el formulari complet (UsersRoles.jsx:580 menciona `rol_nom`/`manage_users`).
- Qui consumeix `TenantConfig` (cap import trobat al grep del domini; cal grep ampli `TenantConfig` a totes les apps per confirmar si és òrfena o usada).
- Si existeix algun ús de `is_staff`/`is_superuser`/`is_active` com a gate alternatiu fora del que he vist (no he fet grep exhaustiu d'aquests).
- Comentari a capabilities.py:19 diu que `ROLE_CAPABILITIES` "es clona amb la plantilla del tenant" — no he localitzat on es materialitza aquesta clonació per tenant (sembla només constant en codi, no per-tenant a BD); possible documentat-no-implementat, no confirmat.

---

## Domini 3 — Model: entitat + CICLE DE VIDA/ESTATS [deep-dive]

[x] fet

Tinc tot el necessari. Redacto el deep-dive.

### Entitats i camps
- `Model` (node de facturació) — `models_app/models.py:75`. 🅱️ (treball facturable del client).
- Camp `estat` (CharField, choices `ESTAT_NOU/EnCurs/EnRevisio/Tancat`, default `ESTAT_NOU`) — `models_app/models.py:201` (constants `models_app/models.py:83-92`). **CODI MORT VIU**: BD confirma DISTINCT estat = només `'Nou'`.
- Camp `fase_actual` (choices `Pending/Dev/Proto/SizeSet/PP/TOP`, default `Pending`) — `models_app/models.py:202` (choices `models_app/models.py:94-101`). És el cicle real.
- Camp `consumption_started_at` (DateTimeField null) — `models_app/models.py:204-206`. Marca de meritació ("NULL = encara no ha consumit màquina").
- Camp `data_objectiu` (DateField null) — `models_app/models.py:226`. Despullat en clonar QA (`clone_model_for_qa.py:83`).
- Camp `design_freeze_at` + `design_freeze_by` (Sprint 7A) — `models_app/models.py:283-289`.
- Camps de slots/temps `slots_prev_*`, `slots_reals_*` — `models_app/models.py:257-260`; `data_entrada` (auto_now_add) `:216`; `data_tancament` `:227`; `darrera_activitat` (post_save) `:274`; `measurements_version` `:279`.
- `ConsumptionRecord` (albarà tenant, OneToOne amb Model) — `models_app/models.py:760-777`. Camps `code_snapshot`, `name_snapshot`, `period`, `opaque_ref` (uuid únic, default), `merited_at`. 🅱️
- `ModelConsumptionEvent` (event PUBLIC, el que FHORT factura) — `backoffice/models.py:63-77`. Camps `codi_client(3)`, `period`, `opaque_ref` (únic, SENSE default), `merited_at`. 🅰️ (plataforma factura).
- `GateEvent` (auditoria d'avanç/retrocés de fase) — `tasks/models.py:256`. 🅱️

### Relacions / FK (marca cross-schema amb db_constraint=False)
- `Model.customer` → `tasks.Customer` PROTECT, null — `models_app/models.py:125-131`. Font de `codi_client` del payload de consum.
- `ConsumptionRecord.model` → `models_app.Model` OneToOne CASCADE — `models_app/models.py:764-766`.
- `ModelConsumptionEvent` → **cap FK**; lligam fluix per `opaque_ref` (mateix UUID que el ConsumptionRecord del tenant) + `codi_client` — `backoffice/models.py:64-70`. Cross-schema deliberadament SENSE FK (tenant↔public).
- `GateEvent.model` → Model (escriu `from_phase`/`to_phase`/`kind`/`by`) — `tasks/services_d.py:46-47,71-72`.
- No s'observa cap `db_constraint=False` als camps d'aquest domini; la frontera tenant/public es travessa via `schema_context('public')` (`backoffice/receivers.py:10`), no via FK.

### Endpoints + gating (qui pot, quina capability/gate)
- `POST /api/v1/models/<id>/gate/` → `gate_model_view` — `tasks/views_b.py:444-467`. Gating `CLOSE_GATES` (`_CloseGates`, `tasks/views_b.py:440-441`; constant `accounts/capabilities.py:9`). Crida `advance_phase_gate`/`advance_phases_chain`. **ÚNIC amo de `fase_actual` cap endavant.**
- `POST /api/v1/models/<id>/regress/` → `regress_model_view` — `tasks/views_b.py:470-489`. Gating `CLOSE_GATES`. Crida `regress_phase`.
- `POST /api/v1/gates/bulk/` → `gate_bulk_view` — `tasks/views_b.py:492-511`. Gating `CLOSE_GATES`. NO exigeix `model_ready` (decisió de govern).
- `POST /api/v1/models/<id>/aprovar-design-freeze/` → `approve_design_freeze_view` (de `pom/wizard_views.py`) — `models_app/urls.py:94`. Escriu `design_freeze_at/by` + `estat`.
- ModelViewSet exposa `fase_actual`/`estat` com a filterset — `models_app/views.py:25`.

### Frontend que hi penja
- `frontend/src/pages/Models.jsx:34` (filtre `fase_actual`), `:160` (`EstatBadge estat`), `:165` (badge `fase_actual`).
- `frontend/src/components/model/ActionsMenu.jsx` — constant `PHASES=['Pending','Dev','Proto','SizeSet','PP','TOP']` (`:8`), `nextPhase/prevPhase` (`:16-17`), botons que criden `modelsApi.gate`/`modelsApi.regress` (`:168-169`).
- `frontend/src/pages/ModelSheet.jsx:390,396,534` (mostra `model.estat` i `model.fase_actual`).
- `frontend/src/components/DesignFreezePanel.jsx:10-23` (llegeix `design_freeze_at/by`, POST a `aprovar-design-freeze`); `DesignFreezeReport.jsx`.
- `Dashboard.jsx`, `KanbanTasks.jsx` consumeixen `fase_actual` (referenciats al grep).

### Màquina d'estats / signals (PROPIETARI ÚNIC de cada estat: qui l'escriu)
- **`fase_actual` té MÚLTIPLES escriptors (NO propietari únic), tot i que els docstrings proclamen "amo únic")**:
  - `tasks/services_d.py:37` (`advance_phase_gate`, endavant) i `:69-70` (`regress_phase`, enrere) — es declaren "únic amo" (`services_d.py`, `fitting/services.py:767`).
  - `tasks/services_c.py:91` — automatisme `Pending→Dev` en arrencar la primera tasca (`.filter(...fase_actual='Pending').update(fase_actual='Dev')`).
  - `models_app/tech_sheet_views.py:306` — `Model.objects.create(... fase_actual='Proto')` (camí d'import de fitxa).
  - `models_app/management/commands/clone_model_for_qa.py:81` — `clone.fase_actual='Proto'`.
  - Default a la creació normal = `'Pending'` (`models_app/models.py:202`).
  - `fitting/services.py:709` `advance_phase` ja **NO** escriu `fase_actual` (D-3 peça 3, `services.py:766-769`), tot i que el seu propi docstring `:715` encara diu "set its Model.fase_actual = nova_fase" → docstring desfasat.
- **`estat`**: escriptors = `advance_phase_gate` quan `to_phase=='TOP'` → `ESTAT_TANCAT` (`tasks/services_d.py:42-44`); `approve_design_freeze_view` → `'En curs'` (`pom/wizard_views.py:38`); creació amb `'Nou'`. BD confirma que mai surt de `'Nou'` (els camins EnCurs/Tancat no s'estan exercint o el valor escrit no quadra — vegeu VELL/NOU).
- **`consumption_started_at`**: PROPIETARI = `tasks/services_c.py:97-98` (primera tasca InProgress, idempotent via `.filter(consumption_started_at__isnull=True).update(...)`); backfill = `reconcile_consumption.py:115-118`; despullat (a None) = `clone_model_for_qa.py:83`.
- **Signal `model_consumption_started`** (`tasks/signals.py:17`): emissor a `tasks/services_c.py:108-114` (payload `codi_client, period, opaque_ref, merited_at`) i a `reconcile_consumption.py:140-146`. Receptor `backoffice/receivers.py:7-18`: `get_or_create(opaque_ref=...)` a schema `public` → **idempotent per opaque_ref**.
- `tasks/signals.py:1-11` documenta que els receivers VELLS (`after_save_model_task`/`after_delete_model_task`) que derivaven `fase_actual` des de les tasques **van ser eliminats a Sprint 0**: cap signal deriva fase avui.

### Serveis d'única entrada reaprofitables
- `advance_phase_gate(model, to_phase, by_profile, notes)` — `tasks/services_d.py:25`. Única entrada per avançar fase + GateEvent + segellar grading (`seal_model_grading`, `:50-53`) + tancar a TOP.
- `regress_phase(...)` — `tasks/services_d.py:59`. Única entrada per retrocedir.
- `model_ready_for_gate(model_id)` — `tasks/services_d.py:11`. Predicat de maduresa reutilitzable.
- La meritació (triple escriptura Model+ConsumptionRecord+event) viu DUPLICADA inline a `services_c.py:95-114` i a `reconcile_consumption.py:113-146` — **NO** hi ha una funció única de meritació (vegeu VELL/NOU).

### 🔴 VELL/NOU (codi mort viu · dobles camins · òrfenes · documentat-no-implementat)
- **Codi mort viu — camp `estat`**: tot el sistema `ESTAT_CHOICES` (Nou/EnCurs/EnRevisio/Tancat, `models_app/models.py:83-92`) és viu però la BD només té `'Nou'`. El cicle real el porten `fase_actual`+`consumption_started_at`. L'índex `['estat','fase_actual']` (`:321`) i el filterset (`views.py:25`) encara l'exposen.
- **Bug latent / valor invàlid**: `pom/wizard_views.py:38` escriu `model.estat = 'En curs'` (LABEL amb espai), però la constant és `ESTAT_EN_CURS='EnCurs'` (sense espai, `models_app/models.py:84`). El valor desat no és cap clau de `ESTAT_CHOICES`. ⚖️
- **Docstring documentat-no-implementat**: `fitting/services.py:715` afirma que `advance_phase` "set its Model.fase_actual = nova_fase", però el cos (`:757-769`) NO el toca (D-3). Docstring desfasat. A més `result` retorna `advanced/sealed` sempre buits "a posta" (`:751-752`) — forma fòssil.
- **Dobles camins de meritació**: la seqüència Model.consumption_started_at + ConsumptionRecord + signal està copiada a `services_c.py:95-114` i `reconcile_consumption.py:113-146`. Risc de divergència; no hi ha servei d'entrada única.
- **DISCREPÀNCIA 11 events públics vs 6 models merited (confirmada al codi)**: `clone_model_for_qa.py:81-86` posa `fase_actual='Proto'` i `consumption_started_at=None` SENSE esborrar el `ModelConsumptionEvent` públic preexistent (el clone copia el Model pk=None; els events públics del golden queden orfes, i en re-meritar el clon es generen events nous amb `opaque_ref` nou). El receiver és idempotent **només per opaque_ref** (`receivers.py:11`), no per (codi_client, model), de manera que clonar/reconciliar pot acumular events públics sense correlat tenant. Hipòtesi de l'orquestrador confirmada al codi.
- **Òrfena potencial**: `ModelConsumptionEvent` no té cap FK ni `model_pk`; un cop el tenant perd `consumption_started_at` (clone) l'event públic és irrecuperablement orfe (només `opaque_ref`).
- **Doble automatisme de fase a la creació**: el flux normal crea `fase_actual='Pending'` (default) i el d'import de fitxa força `'Proto'` (`tech_sheet_views.py:306`), saltant-se Dev/Pending → dos models conceptuals de "model nou".

### 🔗 CONNECTA AMB (blast radius: què es trenca si ho toques)
- Tocar `fase_actual` o el guard de TOP a `advance_phase_gate` trenca: `seal_model_grading` (fitting), `GateEvent`, el botó avançar/retrocedir del frontend (`ActionsMenu.jsx:168-169`), `services_e.has_delivered_production` (`fitting/services.py:740-749`), i `views.py:1527-1539` (càlcul de `next_phase`).
- Tocar `consumption_started_at` o el signal trenca: facturació pública (`ModelConsumptionEvent`), `reconcile_consumption`, `clone_model_for_qa`, i l'albarà tenant (`ConsumptionRecord` OneToOne → esborrar Model fa CASCADE de l'albarà).
- Tocar `estat`/choices trenca: index `:321`, filterset (`views.py:25`), `EstatBadge` i `ModelSheet` al frontend, i el guard terminal a `services_d.py:42-44`.
- `post_save sync_size_fitting` (`signals.py:83`) crea SizeFitting en crear Model amb responsable; `update_last_activity` (`signals.py:127`) escriu `darrera_activitat` a cada save → qualsevol `.save()` del Model dispara aquest signal (els `update()` directes l'esquiven).

### 🅰️/🅱️ Línia
- `Model`, `fase_actual`, `consumption_started_at`, `ConsumptionRecord`, `GateEvent`, endpoints `gate/regress` → 🅱️ (servei facturable sobre models del client).
- `ModelConsumptionEvent` (public, recompte a facturar a FHORT) i el signal cross-schema → 🅰️ (plataforma factura el client).
- El signal `model_consumption_started` és la juntura 🅰️🅱️: emès al tenant (B), consumit a public (A).

### ⚖️ PER DECIDIR (Agus)
- Retirar definitivament el camp `estat` (codi mort viu, sempre 'Nou') o reconciliar-lo amb `fase_actual`? Avui dos eixos d'estat conviuen.
- Bug `'En curs'` vs `'EnCurs'` a `pom/wizard_views.py:38` — corregir a la constant o el camp ja és per esborrar?
- Unificar la meritació en UN servei d'entrada única (avui duplicat services_c / reconcile_consumption).
- `ModelConsumptionEvent` sense lligam a model: clonar QA deixa events públics orfes i la facturació pot sobrecomptar (11 vs 6). Cal que `clone_model_for_qa` purgui també events públics, o que la idempotència sigui per (codi_client, model) i no només per opaque_ref?
- Definició canònica de "model iniciat": consolidar que = `consumption_started_at IS NOT NULL` (meritació), independent de `fase_actual != 'Pending'`.

### Obert / dubtós
- "Model iniciat" té avui DUES definicions properes però no idèntiques: (a) facturació = `consumption_started_at` (escrit a `services_c.py:97`), i (b) tècnica = sortir de `fase_actual='Pending'` (escrit a `services_c.py:91`). El mateix bloc les sincronitza en arrencar la 1a tasca, però `tech_sheet_views.py:306` i `clone_model_for_qa.py:81` posen fase `'Proto'` **sense** `consumption_started_at` → un model pot estar "iniciat" en fase però NO meritat. La BD ho confirma (6 fora de Pending = 6 merited només perquè aquests 6 van pel camí normal); no he pogut verificar si algun model importat-de-fitxa o clon viu trencaria aquesta igualtat.
- No he pogut confirmar si `data_objectiu`/`design_freeze_at` participen en cap automatisme de fase més enllà de ser despullats al clone i mostrats al frontend; no apareix cap lectura que els consumeixi per derivar estat.
- No he inspeccionat si `darrera_activitat` (post_save a cada save) interfereix amb la idempotència dels `update()` directes de `consumption_started_at`/`fase_actual` (aquests usen queryset.update i no disparen el signal, però els `model.save(update_fields=...)` de `services_d.py` sí el disparen).

---

## Domini 4 — Tasques / Kanban

[x] fet

No frontend references to `/tasques`, `/paquets-servei`, `/model-serveis`, or tipologia endpoints. The legacy `Tasca`, `PaquetServei`, `PaquetServeiTasca`, `TipologiaModel` viewsets are effectively orphan (except `PaquetServei` still referenced by `models_app.ModelServei` FK).

### Entitats i camps
- `Tasca` (catàleg tenant, fusió legacy `TascaCataleg` + metadades de procés) — `tasks/models.py:4-71`. Camps clau: `tasca_global`(FK pom), `nom_custom/nom_tasca`, `minuts_estandard`, `tipus_tasca`, `fase`, `ordre_base`, `slots_base`, `facturable`, `bloqueja_model`, `gate`, `resultat_gate`, `is_active/activa`. **Doble flag actiu** (`activa` i `is_active`).
- `TipologiaModel` (slots de càrrega per ruta) — `tasks/models.py:74-113`.
- `TimerEntrada` (comptador de temps server-side) — `tasks/models.py:116-130`: `model_task`(FK CASCADE), `tecnic`(FK PROTECT), `inici/fi/minuts/actiu`.
- `PaquetServei` / `PaquetServeiTasca` (paquets de servei) — `tasks/models.py:134-182`.
- `TaskType` (catàleg de tipus de tasca, per-tenant) — `tasks/models.py:185-198`: `code`(slug unique), `name`, `default_order`, `active`.
- `ModelTask` (instància de tasca d'un model — el card del Kanban) — `tasks/models.py:201-234`: `status`(Pending/Paused/InProgress/Done), `assignee`, `order`, `started_at/finished_at`, `estimated_minutes`(snapshot), `planned_start/planned_end/planned_locked`(motor). `unique_together(model, task_type)`.
- `TaskTransition` (log immutable de transicions; base del comptador de rectificacions) — `tasks/models.py:237-253`: `from_status/to_status/by/at`.
- `GateEvent` (log de gate; avanç/retrocés de fase) — `tasks/models.py:256-275`: `from_phase/to_phase/kind(advance|regress)/by/notes/at`.
- `Supplier` (taller/fàbrica destinatari de confecció) — `tasks/models.py:278-292`.
- `Customer` (client final servit; font del prefix de codi_intern; self-customer via `is_self`) — `tasks/models.py:295-318`: `codi`(3 chars unique), `nom`, `is_self`, `codi_global`(placeholder sense lògica), `logo`.
- `Production` (confecció: recurs extern amb cicle propi) — `tasks/models.py:321-344`: `phase`, `supplier`(PROTECT), `status`(Requested/InProgress/Delivered), `expected_at/delivered_at`, `requested_by`.
- `GarmentTypeItem` (variant de GarmentType per complexitat; node d'estimació de temps) — `tasks/models.py:347-407`: `code`, `complexity_order`, `base_size_definition`(FK pom), `grading_rule_set`(FK pom PROTECT). `clean()` constreny talla base ↔ size_system del ruleset.
- `TaskTimeEstimate` (cel·la matriu (item × task_type) → minuts; estadística Welford) — `tasks/models.py:410-428`: `estimated_minutes`(seed), `n/mean_minutes/m2`. `unique_together(garment_type_item, task_type)`.
- `PlanSnapshot` (fotografia immutable d'una previsió de campanya) — `tasks/models.py:431-456`: viu a `tasks` però l'usa exclusivament `planning/`.

### Relacions / FK (marca cross-schema amb db_constraint=False)
- `ModelTask.model` → `models_app.Model` CASCADE; `.task_type` → `TaskType` PROTECT; `.assignee` → `accounts.UserProfile` SET_NULL — `tasks/models.py:205-209`.
- `TimerEntrada.model_task` → `ModelTask` CASCADE; `.tecnic` → `UserProfile` PROTECT — `tasks/models.py:117-118`.
- `TaskTransition.model_task` → `ModelTask` CASCADE; `.by` → `UserProfile` SET_NULL — `tasks/models.py:240-243`.
- `GateEvent.model` → `models_app.Model` CASCADE; `.by` → `UserProfile` SET_NULL — `tasks/models.py:260-264`.
- `Production.model` → `Model` CASCADE; `.supplier` → `Supplier` PROTECT; `.requested_by` → `UserProfile` SET_NULL — `tasks/models.py:327-334`.
- `GarmentTypeItem.garment_type` → `pom.GarmentType` CASCADE; `.base_size_definition` → `pom.SizeDefinition` SET_NULL; `.grading_rule_set` → `pom.GradingRuleSet` PROTECT — `tasks/models.py:351,367,380`.
- `TaskTimeEstimate.garment_type_item` → `GarmentTypeItem` CASCADE; `.task_type` → `TaskType` CASCADE — `tasks/models.py:414-416`.
- `Tasca.tasca_global` → `pom.TascaGlobal` SET_NULL — `tasks/models.py:7`.
- **Entrant**: `models_app.ModelServei.servei` → `tasks.PaquetServei` PROTECT — `models_app/models.py:430`.
- **Cap FK amb `db_constraint=False`** a `tasks/models.py`. Els FK cap a `pom` són constraint REAL a posta (pom viu al mateix schema del tenant; comentaris a `tasks/models.py:360-384`). No hi ha cross-schema cap a `public` aquí.

### Endpoints + gating (qui pot, quina capability/gate)
Capabilities i rols a `accounts/capabilities.py:6-25` (technician=EXECUTE_TASKS; product_manager=+DEFINE_TASKS,SCHEDULE_FITTINGS; manager=+CLOSE_GATES,VIEW_TEAM_TASKS; admin=ALL).
- `TaskTypeViewSet` (`task-types/`) — list/retrieve: IsAuthenticated; write: `DEFINE_TASKS`; destroy 409 si PROTECT — `views_b.py:29-50`.
- `ModelTaskViewSet` (`model-task-items/`) — list/retrieve/by_model: IsAuthenticated (amb row-scope); write: `DEFINE_TASKS` — `views_b.py:53-74`. `by-model` agregador del Kanban (col.1) — `views_b.py:90-213`.
- `define_model_tasks_view` (`models/<id>/define-tasks/`) — `DEFINE_TASKS` — `views_b.py:260-292`.
- `model_task_log_view` (`models/<id>/task-log/`) — IsAuthenticated — `views_b.py:295-312`.
- `assign_model_view`/`unassign_model_view` (`models/<id>/assign|unassign/`) — `DEFINE_TASKS` — `views_b.py:315-349`.
- `transition_task_view` (`model-task-items/<pk>/transition/`) — `EXECUTE_TASKS` + allow-list de `task_type.code` per a InProgress — `views_b.py:356-384`.
- `claim_task_view` (`model-task-items/<pk>/claim/`) — `EXECUTE_TASKS` + allow-list; self-only; obté tasca DIRECTAMENT (no scopat) — `views_b.py:387-437`.
- `gate_model_view`/`regress_model_view` (`models/<id>/gate|regress/`) — `CLOSE_GATES` — `views_b.py:444-489`.
- `gate_bulk_view` (`gates/bulk/`) i `gate_ready_models_view` (`gates/ready/`) — `CLOSE_GATES` — `views_b.py:492-526`.
- `SupplierViewSet` (`suppliers/`) — write: `SCHEDULE_FITTINGS` — `views_b.py:533-551`.
- `CustomerViewSet` (`customers/`) + `upload-logo` — write/upload: `CONFIGURE` — `views_b.py:554-587`.
- `ProductionViewSet` (`productions/`, ReadOnly) — IsAuthenticated — `views_b.py:590-596`.
- `request_production_view`/`production_status_view` — `SCHEDULE_FITTINGS` — `views_b.py:599-649`.
- `GarmentTypeItemViewSet`/`TaskTimeEstimateViewSet` — write: `CONFIGURE` — `views_b.py:656-681`.
- `TimerEntradaViewSet` (`timers/`) + `/tancar/` — IsAuthenticated, scopat al propi `tecnic` — `views.py:28-72`.
- Helpers de gating: `get_allowed_task_types` (allow-list `profile.permisos["tasks"]`, admin=bypass) — `capabilities.py:57-71`; `scope_model_task_queryset` (3 branques de visibilitat) — `capabilities.py:74-95`.

### Frontend que hi penja
- `frontend/src/pages/KanbanTasks.jsx` (737 línies; ruta `/tasques/kanban`) — el Kanban viu; consumeix `by-model`, `transition`, `claim` — `frontend/src/App.jsx:151`, `frontend/src/api/endpoints.js:134,141,143`.
- `frontend/src/pages/ModelSheet.jsx`, `TechSheetEditor.jsx` — pla de treball/tasques i gates per model.
- `frontend/src/pages/GarmentTypes.jsx`, `ItemAuthoring.jsx` — `garment-type-items/` i `task-time-estimates/`.
- Sidebar enllaça NOMÉS `/tasques/kanban` i `/task-types`; NO `/tasques` — `frontend/src/components/layout/Sidebar.jsx:50,61`.
- `endpoints.js:297-303` matriu de temps; `:387-389` timers.

### Màquina d'estats / signals (PROPIETARI ÚNIC de cada estat: qui l'escriu)
- **`ModelTask.status`** — propietari únic d'escriptura: `transition_task` a `services_c.py:42-127` (taula `ALLOWED` `services_c.py:11-16`: Pending/Paused→InProgress, InProgress→{Paused,Done}, Done→InProgress). Regla "una sola InProgress per tècnic" (pausa l'altra) `services_c.py:54-65`. Ningú més escriu `status` (grep confirma: `planning/plan_service.py` només LLEGEIX amb `.exclude(status='Done')`).
- **`TimerEntrada`** (comptador de temps) — obert/tancat NOMÉS dins `transition_task` (`_open_timer`/`_close_open_timer` `services_c.py:19-31`); també tancable manualment via `TimerEntradaViewSet.tancar` `views.py:59-71`. **On viu el comptador de temps**: suma de `timers.minuts` per ModelTask (`services_i._real_minutes` `services_i.py:13-15`; mateix càlcul al dashboard `models_app/views.py:1577-1579`).
- **`Model.fase_actual`** — múltiples escriptors (documentat com a deute a `signals.py:1-11`): amo canònic = `advance_phase_gate`/`regress_phase` (`services_d.py:37,69`); a més `transition_task` fa Pending→Dev en arrencar la 1a tasca (`services_c.py:91`); fitting `advance_phase` JA NO l'escriu (D-3 peça 3, `fitting/services.py:766-769`).
- **`Model.estat`** → `ESTAT_TANCAT` quan to_phase=='TOP' (`services_d.py:42-44`).
- **`GateEvent`** — escrit només a `advance_phase_gate`/`regress_phase` (`services_d.py:46,71`).
- **`Production.status`** — `set_production_status` (`services_e.py:30-42`; Requested→InProgress→Delivered).
- **`TaskTransition`** (log immutable) — escrit només per `_log` dins `transition_task` (`services_c.py:34-35`).
- **`TaskTimeEstimate` (Welford n/mean/m2)** — escrit per `record_actual_time` en Done (`services_i.py:18-46`), cridat des de `transition_task` `services_c.py:121-125`.
- **`ModelTask.planned_*`** — escrits NOMÉS pel motor `planning/plan_service.py` (read-only al serializer `serializers_b.py:31-33`).
- Signal viu: `model_consumption_started` (meritació) emès dins `transition_task` `services_c.py:108`. Receivers legacy retirats (`signals.py:1-11`).

### Serveis d'única entrada reaprofitables
- `transition_task(task, to_status, profile)` — `services_c.py:42` — ÚNICA porta a transicions de ModelTask + timers + log + meritació + Welford.
- `rectification_count(task)` — `services_c.py:130` — comptador Done→InProgress (reusat al serializer `serializers_b.py:36`).
- `advance_phase_gate` / `regress_phase` / `advance_phases_chain` — `services_d.py:24,58,76` — única porta a fase + GateEvent + segellat grading.
- `model_ready_for_gate(model_id)` — `services_d.py:11`.
- `request_production` / `set_production_status` / `phase_passed_gate` / `has_delivered_production` — `services_e.py:11,16,30,45` — regles dures gate↔confecció↔fitting (`has_delivered_production` reusat a `fitting/services.py:740-744`).
- `lookup_estimated_minutes(model, task_type)` — `services_g.py:4` — snapshot del temps en crear ModelTask.
- `record_actual_time` / `effective_minutes` — `services_i.py:19,49` — estadística Welford.
- `get_allowed_task_types` / `scope_model_task_queryset` — `accounts/capabilities.py:57,74`.

### 🔴 VELL/NOU (codi mort viu · dobles camins · òrfenes · documentat-no-implementat)
- 🔴 **`Tasks.jsx` mort/trencat**: la pàgina (ruta `/tasques`, `App.jsx:150`) fa fetch a `/api/v1/model-tasques/` (`Tasks.jsx:34`), endpoint que **NO existeix** (cap registre `model-tasques`/`model-tasca` al backend, grep buit). El sidebar no hi enllaça (`Sidebar.jsx:50` només `/tasques/kanban`). Doble camí amb `KanbanTasks.jsx` (el viu). **PER DECIDIR**.
- 🔴 **`Tasca` / `PaquetServei` / `PaquetServeiTasca` viewsets òrfens al frontend**: `views.py:18` (`TascaViewSet` legacy), `views_sprint1c.py:12-40` (`TascaViewSet`/`PaquetServeiViewSet`). Cap referència frontend a `/api/v1/tasques`, `/paquets-servei`, `/model-serveis` (grep buit). `PaquetServei` però segueix viu com a FK des de `models_app.ModelServei` (`models_app/models.py:430`) → no esborrable lliurement.
- 🔴 **Doble registre de `tasques/`**: `urls.py:13-18` registra `sprint1c.TascaViewSet` amb fallback a `legacy TascaViewSet` (`views.py`). Dos `TascaViewSet` coexistents; el legacy és inabastable si l'import de sprint1c reïx (sempre).
- 🔴 **`TipologiaModel` òrfena**: model definit (`models.py:74`), migracions, però cap viewset/serializer/import en codi viu (grep sense ús fora migracions). Camps `slots_*` substituïts pel motor de planning. Documentat-no-connectat.
- 🔴 **`Tasca` doble flag actiu**: `activa` (`models.py:16`) i `is_active` (`models.py:59`) — redundància; el sprint1c filtra per `is_active` (`views_sprint1c.py:22`), el legacy per `activa`+`is_active` (`views.py:23`).
- 🔴 **Camps `slots_base`/`minuts_estandard`/`ordre` de `Tasca`** sense lectura en codi viu (el temps real viu a `TaskTimeEstimate`/snapshot). Òrfenes de facto.
- 🔴 **`Customer.codi_global`** — placeholder explícit "sense lògica en aquest sprint" (`models.py:306-308`). Documentat-no-implementat.
- 🔴 **Doble càlcul de "temps consumit"** (no contradictori però duplicat): `services_i._real_minutes` (`services_i.py:13`) i la query del dashboard `models_app/views.py:1577-1579` calculen el mateix `Sum(timers.minuts)` per camins separats.
- 🟡 **Tensió seed vs Welford**: el motor `scheduler_service.py:8,215` usa el SNAPSHOT `ModelTask.estimated_minutes` (congelat a la creació via `lookup_estimated_minutes`→`effective_minutes`), NO la cel·la Welford en viu. La millora Welford (`record_actual_time`) NOMÉS afecta tasques creades DESPRÉS; les ja existents conserven el seed. Coherent amb el disseny però fàcil de confondre amb "el planificador aprèn en viu".
- 🔴 **`PlanSnapshot` viu en `tasks/` però és 100% de `planning/`** (`tasks/models.py:431`, usat a `planning/views.py:24`, `plan_service.py:17`). Ubicació històrica; candidat a moure de domini.

### 🔗 CONNECTA AMB (blast radius: què es trenca si ho toques)
- `transition_task` (`services_c.py`) toca: `TimerEntrada`, `TaskTransition`, `Model.fase_actual` (Pending→Dev), `Model.consumption_started_at`+`ConsumptionRecord` (meritació, `models_app`), signal `model_consumption_started` (backoffice/reconcile), Welford `TaskTimeEstimate`. Trencar-lo afecta Kanban, facturació i estimacions.
- `advance_phase_gate` (`services_d.py`) crida `fitting.seal_model_grading` (`services_d.py:50`) → acobla tasks↔fitting↔grading. Canviar la signatura trenca el segellat.
- `has_delivered_production` (`services_e.py:45`) és precondició dura de `fitting.advance_phase` (`fitting/services.py:740-744`). Tocar Production trenca l'avanç de fitting.
- `ModelTask.assignee`/reassignació dispara cascada de planning: `cleanup_queue_order`+`recompute_for_technicians` (`views_b.py:250-253`, `claim_task_view:434-436`). Acobla a `planning/plan_service.py` i `TechnicianQueueOrder` (`planning/models.py:72`).
- `GarmentTypeItem.grading_rule_set`/`base_size_definition` (PROTECT/SET_NULL cap a `pom`) — esborrar un ruleset bloqueja; el `clean()` valida coherència size_system (`models.py:392-404`, replicat al serializer `serializers_b.py:90-104`).
- `Customer` (PROTECT des de `Model.customer`) i `Supplier`/`TaskType` (PROTECT) → destroy retorna 409 (`views_b.py:42-50,544-551,565-572`).
- Dashboard del model (`models_app/views.py:1572-1597`) llegeix `ModelTask`/`TimerEntrada`/`TaskTransition` directament (no via servei) → canvis d'estructura el trenquen.

### 🅰️/🅱️ Línia
- 🅰️ Plataforma/comú: `TaskType` (catàleg per-tenant), capabilities/gating (`accounts/capabilities.py`), `scope_model_task_queryset`, `PlanSnapshot`, motor de planning, `Customer`/`Supplier` (arxius mestres del tenant).
- 🅱️ Servei (facturable, sobre models del client): `ModelTask`, `TimerEntrada`, `TaskTransition`, `GateEvent`, `Production`, transicions/gates/confecció, meritació (`model_consumption_started`), Welford `TaskTimeEstimate`.
- 🅰️🅱️ Frontera: `GarmentTypeItem`/`TaskTimeEstimate` (configuració de plataforma 🅰️ que parametritza estimacions del servei 🅱️); `transition_task` (acció de servei 🅱️ que dispara meritació 🅱️ i marca de fase 🅱️).

### ⚖️ PER DECIDIR (Agus)
- Esborrar `Tasks.jsx` + ruta `/tasques` (`App.jsx:150`) i el seu `TascaViewSet` legacy (`views.py:18`): pàgina trencada (endpoint inexistent), sense enllaç al sidebar.
- Jubilar `views_sprint1c.TascaViewSet`/`PaquetServeiViewSet` i el doble registre `tasques/` (`urls.py:13-18`) si el frontend no els usa — però mantenir `PaquetServei` (FK viu des de `ModelServei`).
- `TipologiaModel`: confirmar si és definitivament substituïda pel motor de planning → DROP o conservar com a master-data.
- Unificar `Tasca.activa`/`is_active` (doble flag) i decidir sort dels camps `slots_base/minuts_estandard/ordre` sense ús.
- Moure `PlanSnapshot` de `tasks/` a `planning/` (domini real) — implica migració.
- Confirmar intencionalitat: el planificador NO re-aprèn sobre tasques ja creades (snapshot congelat); si es vol Welford en viu cal re-snapshot.

### Obert / dubtós
- No he verificat el contingut complet de `KanbanTasks.jsx` (737 línies) ni de `ModelSheet.jsx`/`TechSheetEditor.jsx`: confirmat QUE consumeixen els endpoints viu (by-model/transition/claim/gate) via `endpoints.js`, però no l'abast exacte d'UI ni si exposen `regress`/`gates/bulk`.
- No he traçat si `assign_batch` (`plan_service.py:216`) té endpoint propi exposat (vist a planning, fora del meu domini estricte).
- `Customer.is_self`/codi-gen: la cadena completa de generació de `codi_intern` viu a `models_app` (no inspeccionada aquí); aquí només consta com a font del prefix (`models.py:295-308`).
- No he confirmat si existeix cap consumidor de `gate_ready_models_view` (`gates/ready/`) al frontend (no aparegut als greps d'endpoints fets).

---

## Domini 5 — Planning / Pla de treball

[x] fet

No backoffice usage. I have a complete picture.

### Entitats i camps
- `CompanyCalendar` (singleton per tenant) — `planning/models.py:25`. Camps: `horaris` (JSON trams/dia mon..sun, default `default_horaris` a `planning/models.py:11`), `festius_extra` (JSON dates ISO), `creat_at`/`actualitzat_at`. Singleton via `load()` a `planning/models.py:41`. 🅰️🅱️
- `Absencia` — `planning/models.py:55`. `user_profile` (FK), `data_inici`/`data_fi` (rang inclusiu), `motiu`. 🅰️🅱️
- `TechnicianQueueOrder` — `planning/models.py:72`. `(profile, model, position)`, `unique_together (profile, model)` (`planning/models.py:87`). Ordre MANUAL d'un model dins la cua d'un tècnic. 🅱️
- `PlanSnapshot` (viu a `tasks/models.py:431`, NO a `planning/`) — fotografia immutable d'una previsió. Inputs desats: `start_date`, `technician_count`, `working_minutes_per_day` (default 420), `blocked_dates` (JSON), `model_sequence` (JSON), `campaign_filter` (JSON), `result` (JSON). Cada recàlcul en crea un de nou. 🅱️

### Relacions / FK (marca cross-schema amb db_constraint=False)
- `CompanyCalendar`: cap FK (singleton autònom). `planning/models.py:25`.
- `Absencia.user_profile` → `accounts.UserProfile` CASCADE, `related_name='absencies'`. `planning/models.py:57`.
- `TechnicianQueueOrder.profile` → `accounts.UserProfile` CASCADE (`planning/models.py:80`); `.model` → `models_app.Model` CASCADE (`planning/models.py:82`).
- `PlanSnapshot.computed_by` → `accounts.UserProfile` SET_NULL, `related_name='plan_snapshots'`. `tasks/models.py:435`.
- El motor llegeix `ModelTask` (`tasks/models.py:201`) i escriu `ModelTask.planned_start/end/locked` (`tasks/models.py:216-221`) i `Model.predicted_start/end` (`models_app/models.py:228-229`) — entitats d'altres apps, no de planning.
- Cap `db_constraint=False` al domini: totes les FK són intra-schema (tenant). — cap cross-schema —

### Endpoints + gating (qui pot, quina capability/gate)
Tots a `planning/urls.py` + `planning/views.py`:
- `GET/PUT company-calendar/` — `_Configure` (CONFIGURE). `views.py:50`.
- `GET/PUT users/<id>/jornada/` — `_ConfigureOrManageUsers` (CONFIGURE o MANAGE_USERS). `views.py:63`.
- `absencies/` (List/Create/Retrieve/Destroy) — `_ConfigureOrManageUsers`, filtrable `?user_profile`. `views.py:82`.
- `POST plan/compute/` — `_Configure`. `views.py:94`.
- `POST plan/preview/` — `_Configure`. `views.py:112`.
- `POST plan/apply/` — `_Configure`. `views.py:131`.
- `GET plan/snapshots/` — `_Configure` (últimes 50). `views.py:152`.
- `GET plan/current/` — `IsAuthenticated`; control fi per DADES via `scope_model_task_queryset` (`accounts/capabilities.py:74`). `views.py:165`.
- `GET calendar/events/` — `IsAuthenticated`; scope per `view_team_tasks`; confecció/fitting sempre visibles. `views.py:211`.
- `POST plan/reorder/` — `_DefineTasks` (DEFINE_TASKS). `views.py:492`.
- `GET plan/eligible-technicians/` — `_DefineTasks`. `views.py:529`.
- `GET plan/eligible-attendees/` — `_ScheduleFittings` (SCHEDULE_FITTINGS). `views.py:568`.
- `POST plan/assign-batch/` — `_DefineTasks`. `views.py:583`.

### Frontend que hi penja
- `Planning.jsx` — gating `canPlan = define_tasks || configure` (`frontend/src/pages/Planning.jsx:96`); crida `plan.reorder` (`Planning.jsx:213`).
- `TaskAssignWizard.jsx` — `plan.eligibleTechnicians` (`:99`), `plan.assignBatch` (`:170`).
- `PlanningCalendar.jsx` — `calendar.events({start,end})` (`:127`) + `companyCalendar` per pintar la graella; accés NO gatejat per canPlan (`App.jsx:162`).
- `CompanyCalendar.jsx` — `companyCalendar.get/update`.
- `FittingSessionList.jsx:161` i `model/ActionsMenu.jsx:58` — `plan.eligibleAttendees`.
- Endpoints definits a `frontend/src/api/endpoints.js:218-268` (`plan`, `calendar`, `companyCalendar`, `jornada`, `absencies`).

### Màquina d'estats / signals (PROPIETARI ÚNIC de cada estat: qui l'escriu)
- `ModelTask.planned_start/end` — propietari: `scheduler_service.schedule(... save=True)` (`scheduler_service.py:240-243`), i directament `plan_service.apply` per la tasca fixada (`plan_service.py:165-167`) i `assign_batch` per dates manuals (`plan_service.py:304,309`). El serializer de tasca els té com a read-only (per nota a `plan_service.py:361`).
- `ModelTask.planned_locked` — propietari: `plan_service.apply` (True, `:164`), `assign_batch` (True/False, `:300,305,310,312`), `unassign_model` (False, `:369`). El motor només LLEGEIX locked, mai l'escriu.
- `Model.predicted_start/end` — propietari ÚNIC d'escriptura positiva: `scheduler_service.schedule(save=True)` (`scheduler_service.py:245-246`). Neteja a None: `unassign_model` (`plan_service.py:374`). No els escriu cap altra app (confirmat: cap altra referència fora de planning excepte la definició del camp).
- `PlanSnapshot` — escrit només per `plan_service._save_snapshot` (`plan_service.py:79`), des de `compute_and_save` i `apply`. Immutable (mai update/delete).
- `TechnicianQueueOrder` — escrit per `plan_reorder_view` (`views.py:521`, update_or_create); esborrat per `cleanup_queue_order` (`plan_service.py:62`). Llegit per `scheduler_service._manual_positions` (`scheduler_service.py:61`).
- NO hi ha signals ni receivers ni cron al domini (`apps.py` buit, sense `ready()`; cap `@receiver`/`crontab`/`celery` a `planning/`). La derivació del pla és SÍNCRONA, disparada per crides explícites.

### Serveis d'única entrada reaprofitables
- `calendar_service` (`planning/calendar_service.py`): primitives de calendari laboral naïf — `next_working_slot` (`:81`), `add_working_minutes` (`:96`), `add_working_days` (`:119`, reusat per Size Check a `models_app/serializers_size_check.py:72`), `prev_working_slot` (`:136`), `subtract_working_minutes` (`:154`).
- `scheduler_service.schedule` (`scheduler_service.py:117`): motor determinista únic; `save=True/False`. Inclou `_collect_busy_intervals` que llegeix `FittingSession.attendees` (`scheduler_service.py:95`, import local per evitar cicle planning↔fitting).
- `plan_service`: `recompute_for_technicians` (`:48`), `cleanup_queue_order` (`:62`), `compute_and_save` (`:88`), `preview` (`:111`), `apply` (`:151`), `assign_batch` (`:215`), `assign_model` (`:177`), `unassign_model` (`:359`). `recompute_for_technicians`/`cleanup_queue_order` són el punt d'entrada que reusen tasks i fitting (vegeu blast radius).

### 🔴 VELL/NOU (codi mort viu · dobles camins · òrfenes · documentat-no-implementat)
- **Endpoints sense cap consumidor frontend (codi mort viu pràctic)**: `plan/compute/`, `plan/preview/`, `plan/apply/`, `plan/snapshots/` estan definits a `endpoints.js:218-223` però CAP component els crida (confirmat per grep a tot `frontend/` i `frontend-backoffice/`; només `reorder`, `eligibleTechnicians`, `assignBatch`, `eligibleAttendees`, `calendar.events`, `companyCalendar` tenen caller real). El flux viu d'assignació és el wizard `assign-batch` + `reorder`, no el `compute` de campanya. `compute_and_save`/`preview`/`apply` queden al backend sense UI.
- **`PlanSnapshot` parcialment documentat-no-implementat**: camps `working_minutes_per_day` (`tasks/models.py:440`), `blocked_dates` (`:441`) MAI s'escriuen amb valor real — `_save_snapshot` (`plan_service.py:81`) no els passa → sempre default 420 / `[]`. El comentari del `result` documenta `load_minutes` per model i `campaign_end` (`tasks/models.py:447-448`) que el motor NO produeix (`schedule` només omple `predicted_start/end` a `scheduler_service.py:233`). Camps i contracte documentats però no poblats.
- **Doble camí de recompute, però convergent (no duplicació real)**: `recompute_for_technicians` és cridat des de tasks (`views_b.py:253,436`), fitting (`fitting/services.py:184,268,669,806`) i reorder (`views.py:523`); tots passen pel mateix servei únic. NO és doble camí; és la única entrada correcta.
- **`Production` jubilada de banda de durada**: a `calendar_events_view` el comentari (`views.py:299-301`) anota que ja NO es pinta com a banda requested→expected sinó com a marcador d'un dia — residu de disseny anterior, ja resolt (no és codi mort, és nota històrica).
- `services_h.py` (Sprint H, plan/compute per-model-en-sèrie) ja ELIMINAT físicament (jubilat, `tasks/views_b.py:685`, `tasks/urls.py:86`); `plan_service.py:2-3` encara el cita al docstring com a referència. — no és codi mort, és menció documental d'un fitxer inexistent.

### 🔗 CONNECTA AMB (blast radius: què es trenca si ho toques)
- `scheduler_service.schedule` escriu `ModelTask.planned_*` i `Model.predicted_*`: tocar-lo afecta `plan/current/` i `calendar/events/` (pintat Gantt/agenda), i el `en_risc` de tota la UI.
- `_collect_busy_intervals` (`scheduler_service.py:95`) depèn de `FittingSession` (camps `attendees`, `data`, `start_time`, `duracio_minuts`, `estat`): canviar el model de fitting trenca el motor.
- `recompute_for_technicians`/`cleanup_queue_order` són cridats des de **tasks** (`views_b.py:250-253,434-436`, assign/unassign/reassign) i **fitting** (`fitting/services.py` x4): si canvies la seva signatura, trenques 3 apps.
- `calendar_service.add_working_days` el reusa Size Check (`models_app/serializers_size_check.py:72`): tocar-lo afecta el càlcul de data límit de Size Check.
- `calendar/events/` depèn de `Production` (`requested_at`, `expected_at`, `phase`, `status`, `supplier`) i `FittingSession` (convocatòria, attendees, started/finished_at): canvis en aquests models trenquen l'agenda.
- `plan_service.assign_batch` depèn de `TaskType`, `get_allowed_task_types` (`accounts/capabilities`), `lookup_estimated_minutes` (`tasks/services_g.py`) i `Model`.

### 🅰️/🅱️ Línia
- 🅰️🅱️ infra de calendari: `CompanyCalendar`, `Absencia`, jornada — plataforma multi-tenant però parametritza el servei. Gated `configure`/`manage_users`.
- 🅱️ servei facturable: `PlanSnapshot`, `TechnicianQueueOrder`, el motor `schedule`, `plan_service` (compute/preview/apply/assign/reorder), `plan/current`, `calendar/events` — tot opera sobre models del client.

### ⚖️ PER DECIDIR (Agus)
- Què fer amb `plan/compute`, `plan/preview`, `plan/apply`, `plan/snapshots`: backend complet i testejable però SENSE UI. ¿Es preveu UI de "planificació de campanya"/"previst-vs-real (§7)" o es jubilen com `services_h`? El previst-vs-real (la raó de ser de `PlanSnapshot`, `tasks/models.py:432-433`) no té cap lector que compari snapshot vs real.
- Camps `working_minutes_per_day` i `blocked_dates` de `PlanSnapshot` (mai poblats) i `result.load_minutes`/`campaign_end` (documentats, no produïts): netejar o implementar.
- `PlanSnapshot` viu a l'app `tasks/`, no a `planning/` — decidir si es migra al domini natural (acobla planning↔tasks).

### Obert / dubtós
- No he pogut determinar si existeix algun consumidor de `plan/snapshots`/`plan/current` fora del repo frontend inspeccionat (p.ex. scripts/management commands): grep a `frontend/` i `frontend-backoffice/` no en mostra; no he buscat management commands ni tests.
- `plan/current/` (Gantt read-only) està definit i scoped, però no he trobat el component que el consumeix (a `Planning.jsx` el Gantt sembla derivar de `modelTasks`, no de `plan.current`); l'export `plan.current` ni tan sols apareix a `endpoints.js` (no exposat) — possible endpoint backend sense client. No verificat al 100%.
- No he revisat els tests del domini (`planning/tests*`) per confirmar quins camins estan coberts.

---

## Domini 6 — Calendari (bug replicació diària)

[x] fet

Confirmat: els endpoints `jornada` i `absencies` no es consumeixen enlloc al frontend. Tinc tot el material. Redacto el lliurable.

### Entitats i camps
- `CompanyCalendar` 🅱️ — singleton per tenant: `horaris` (JSONField, trams `{dia:[[HH:MM,HH:MM]]}`, default `default_horaris`), `festius_extra` (JSONField llista ISO), `creat_at`, `actualitzat_at`. `planning/models.py:25-52`. Singleton via `load()` (get-or-create) `planning/models.py:41-47`.
- `Absencia` 🅱️ — `user_profile` (FK), `data_inici`, `data_fi` (rang inclusiu), `motiu`. `planning/models.py:55-69`.
- `TechnicianQueueOrder` 🅱️ — ordre manual de cua per tècnic: `profile` (FK), `model` (FK), `position` (PositiveInteger). `unique_together(profile,model)`. La unicitat de `position` NO és constraint de BD (duplicats transitoris). `planning/models.py:72-93`.
- `PlanSnapshot` 🅱️ (a `tasks`) — previsió immutable: `computed_at` (auto_now_add), `computed_by` (FK SET_NULL), `start_date`, `technician_count`, `model_sequence` (JSON), `campaign_filter` (JSON), `result` (JSON). `tasks/models.py:431-456`.
- Camps de calendari sobre `ModelTask` 🅱️ — `planned_start`/`planned_end` (DateTimeField, aware/UTC), `planned_locked` (Bool, punt fix). `tasks/models.py:216-220`. Snapshot de durada: `estimated_minutes`.
- `Production` 🅱️ — entra al calendari com a font `confeccio`: `phase`, `status`, `requested_at`, `expected_at` (DateField), `delivered_at`, `supplier`. `tasks/models.py:321-344`.
- Jornada per-tècnic viu a `accounts.UserProfile.jornada_override` (JSON; null→hereta empresa), NO a planning. `planning/models.py:3`, usat a `calendar_service.py:58-63`.
- `DOW_KEYS = ['mon'..'sun']` alineat amb `date.weekday()`. `planning/models.py:8`.

### Relacions / FK (marca cross-schema amb db_constraint=False)
- `Absencia.user_profile → accounts.UserProfile` CASCADE. `planning/models.py:57`.
- `TechnicianQueueOrder.profile → accounts.UserProfile` CASCADE; `.model → models_app.Model` CASCADE. `planning/models.py:80-83`.
- `PlanSnapshot.computed_by → accounts.UserProfile` SET_NULL. `tasks/models.py:435`.
- `Production.model → models_app.Model` CASCADE, `.supplier → Supplier` PROTECT, `.requested_by → accounts.UserProfile` SET_NULL. `tasks/models.py:327-335`.
- Cap FK marcada amb `db_constraint=False` en aquest domini: totes les FK són intra-schema de tenant (cap cross-schema public↔tenant aquí). — cap cross-schema —

### Endpoints + gating (qui pot, quina capability/gate)
- `GET/PUT /api/v1/company-calendar/` — gate `CONFIGURE`. `planning/views.py:50-60`.
- `GET/PUT /api/v1/users/<id>/jornada/` — `CONFIGURE` O `MANAGE_USERS`. `planning/views.py:63-79`, permís `planning/views.py:40-47`.
- `absencies/` CRUD (List/Create/Retrieve/Destroy, sense Update) filtrable `?user_profile=` — `CONFIGURE` O `MANAGE_USERS`. `planning/views.py:82-90`.
- `POST /api/v1/plan/compute/` `/preview/` `/apply/`, `GET /plan/snapshots/` — gate `CONFIGURE`. `planning/views.py:94-161`.
- `GET /api/v1/plan/current/` — `IsAuthenticated` + SCOPE per dades (`scope_model_task_queryset`): amb `view_team_tasks` veu tots, sense → només el propi perfil. `planning/views.py:165-207`.
- `GET /api/v1/calendar/events/` — `IsAuthenticated` + mateix SCOPE per tasques; confecció/fitting sempre visibles. `planning/views.py:211-488`.
- `POST /api/v1/plan/reorder/` — gate `DEFINE_TASKS`. `planning/views.py:492-525`.
- `GET /plan/eligible-technicians/`, `POST /plan/assign-batch/` — `DEFINE_TASKS`. `GET /plan/eligible-attendees/` — `SCHEDULE_FITTINGS`. `planning/views.py:529-607`.

### Frontend que hi penja
- `PlanningCalendar.jsx` (ruta `/planificacio/calendari`, ungated/autenticats) — consumeix `calendar.events()` i `companyCalendar.get()`. `frontend/src/pages/PlanningCalendar.jsx:5,105,127`.
- `CompanyCalendar.jsx` (ruta `/configuracio/calendari`) — editor d'horaris + festius_extra. `frontend/src/App.jsx:170`, `frontend/src/pages/CompanyCalendar.jsx`.
- Endpoints API definits: `companyCalendar`, `jornada`, `absencies` a `frontend/src/api/endpoints.js:250-268`.

### Màquina d'estats / signals (PROPIETARI ÚNIC de cada estat: qui l'escriu)
- **Propietari de l'estat del calendari de planificació = `scheduler_service.schedule(save=True)`** — ÚNIC que escriu `ModelTask.planned_start/end` (i `Model.predicted_start/end`) en passada normal. `planning/scheduler_service.py:237-246`.
- `planned_locked=True` només l'escriuen `plan_service.apply` (`plan_service.py:164-167`) i `assign_batch` (quan hi ha data, `plan_service.py:305,310`). Reset a `False` per `unassign_model` (`plan_service.py:369`) i a cua sense data (`plan_service.py:300,312`).
- `predicted_*` del Model: escrit per `schedule` (agregació min/max), netejat per `unassign_model`. `plan_service.py:374`.
- `CompanyCalendar.horaris/festius_extra`: escrit NOMÉS per `company_calendar_view` PUT. `planning/views.py:57-59`.
- `TechnicianQueueOrder.position`: escrit per `plan_reorder_view` dins `transaction.atomic` (`planning/views.py:519-522`); esborrat per `cleanup_queue_order` (`plan_service.py:62-76`).
- NO hi ha `signals.py` a planning; `tasks/signals.py` no toca camps de calendari (la planificació és sempre per crida explícita, no per signal).

### Serveis d'única entrada reaprofitables
- `calendar_service` — primitives NAÏVES locals reaprofitables: `next_working_slot`/`prev_working_slot`, `add_working_minutes`/`subtract_working_minutes`, `add_working_days`. `profile=None` → calendari pur d'empresa (usat per fitting `schedule_bulk`). `planning/calendar_service.py:81-175`.
- `scheduler_service.schedule(qs, now, save)` — motor determinista únic; `save=False` = preview pur. `planning/scheduler_service.py:117`.
- `plan_service` — orquestració única: `compute_and_save`, `preview`, `apply`, `assign_model`, `assign_batch`, `unassign_model`, `recompute_for_technicians`, `cleanup_queue_order`. `planning/plan_service.py`.

### 🔴 VELL/NOU (codi mort viu · dobles camins · òrfenes · documentat-no-implementat)
- **BUG DE REPLICACIÓ DIÀRIA (mecanisme encara viu al frontend).** El mecanisme que "replica una entrada dia a dia" és el render all-day per RANG: `inRange(e,d)` retorna cert per a CADA dia entre `e._start` i `e._end`, i `allDayByDay`/`monthByDay` el pinten a tots ells. `frontend/src/pages/PlanningCalendar.jsx:171-178`. Per a la **confecció** el bug ESTAVA aquí: el backend pintava una banda `requested_at→expected_at` que feia que `inRange` repliqués la confecció a tots els dies del tram; es va mitigar al BACKEND col·lapsant-la a UN sol dia (`marker_d = expected_at or requested_at`, `start==end`) `planning/views.py:296-321` (commit `34e7e62`), no arreglant el render. El mecanisme de replicació **segueix viu** i s'aplica al **fitting de convocatòria multi-dia**: `start_dt = primera.data`, `end_dt = sessions_grup[-1].data` amb `all_day=True` (`planning/views.py:447-449`) → el bloc del grup es replica a CADA dia entre la primera i l'última sessió via `inRange`. ON FALLA: render `inRange` (front) sobre un event all-day amb `_start ≠ _end`; el backend col·lapsa la confecció però NO el grup de fitting.
- **Endpoints òrfens de UI:** `jornada` i `absencies` (i `Absencia`, `UserProfile.jornada_override`) tenen API i client (`endpoints.js:256-268`) però CAP component els consumeix (`grep` de `jornada.`/`absencies.` als `.jsx` = buit). El motor sí els llegeix (`calendar_service.py:47-63`), però no hi ha pantalla per crear-los → camp viu sense entrada de dades. Coherent amb ESTAT_PROJECTE.md:1358 ("Jornada-per-tècnic i absències AJORNATS").
- **Documentat-no-implementat:** la graella del calendari NO ombreja els festius oficials de Catalunya (workalendar); `company-calendar/` només exposa `festius_extra`. `PlanningCalendar.jsx:17`, ESTAT_PROJECTE.md:1455. El motor SÍ els respecta (`calendar_service.py:43-44`) → divergència front/back.
- **Doble font de "festiu":** workalendar (oficials, al motor) vs `festius_extra` (tenant). El front només coneix `festius_extra`; pinta com a laborable un festiu oficial que el motor saltaria.
- **`Absencia` sense Update:** el ViewSet només permet Create/Destroy/Retrieve/List, no PATCH/PUT (`planning/views.py:82-84`) — editar una absència = esborrar+crear. Limitació, possiblement intencionada.
- Helpers "privats" reusats cross-mòdul: `scheduler_service._now_naive/_to_naive/_to_aware` importats per `plan_service` (`plan_service.py:19`) — acoblament a noms `_`.

### 🔗 CONNECTA AMB (blast radius: què es trenca si ho toques)
- `calendar_service` és la base de TOT: si en toques les primitives, trenques scheduler (`scheduler_service.py:27`), plan_service (`plan_service.py:18`) i fitting `schedule_bulk` (MAPA_SISTEMA.md:418).
- `schedule()` escriu `ModelTask.planned_*` i `Model.predicted_*`: ho llegeixen `plan/current`, `calendar/events`, el Gantt/agenda del front i `eligible-technicians` (annotate `Max(planned_end)`, `views.py:553`).
- `calendar/events` agrega TRES fonts (ModelTask, Production, FittingSession): tocar el contracte d'event trenca `enrich`/`inRange`/les 4 vistes de `PlanningCalendar.jsx`.
- `TechnicianQueueOrder` la llegeix `_manual_positions` dins l'ordenació del scheduler (`scheduler_service.py:61-69,201-208`): si canvies l'ordre manual, canvies tota la cua planificada del tècnic.
- `_collect_busy_intervals` importa `fitting.models.FittingSession` (import local per evitar cicle planning↔fitting, `scheduler_service.py:99`): les sessions de fitting bloquegen el calendari del tècnic assistent.

### 🅰️/🅱️ Línia
- TOT el domini Calendari és 🅱️ (servei sobre models del client: calendari laboral, scheduler, agenda). Cap entitat A.
- L'únic toc 🅰️ és l'arrel multi-tenant implícita (singleton `CompanyCalendar` per tenant, FK a `accounts.UserProfile`), però la lògica és de servei → 🅱️.

### ⚖️ PER DECIDIR (Agus)
- El BUG de replicació diària: decidir si es corregeix al FRONT (que `inRange`/render no expandeixi un all-day multi-dia quan no toca, o partir-lo en marcadors) o al BACKEND (emetre el grup de fitting de convocatòria com a UN marcador, com es va fer amb la confecció a `views.py:296-301`). Avui la confecció està mitigada al backend i el fitting-convocatòria NO.
- Construir o eliminar la UI de `jornada`/`absencies`: el motor els llegeix però no hi ha entrada de dades. Decidir si es promou (pantalla) o es marca com a deute documentat.
- Ombrejar festius oficials CAT al front (exposar-los via `company-calendar/` o endpoint nou) per eliminar la divergència front/back.

### Obert / dubtós
- No he pogut confirmar amb 100% de certesa que el "BUG conegut" al qual es refereix el brief sigui exactament el del fitting-convocatòria multi-dia i NO un altre cas històric ja eliminat: la pista parla de "replica entrades dia a dia"; l'únic mecanisme viu que ho fa és `inRange` (PlanningCalendar.jsx:171-178) sobre all-day amb `_start≠_end`, i l'únic productor actual d'all-day multi-dia és el grup de fitting de convocatòria (`views.py:447-449`). La confecció ja no el dispara (col·lapsada a un dia).
- No he revisat exhaustivament `tasks/services_*.py` (services_c..i): poden contenir altres escriptors indirectes de `planned_*`; el blindatge del scheduler (`scheduler_service.py:141`) suggereix que `schedule` n'és l'únic, però no ho he verificat fitxer per fitxer.
- `tasks/services_h.py` el comentari de `plan_service.py:2` diu que "jubila" la lògica per-model-en-sèrie d'allà — no he comprovat si `services_h.py` segueix existint com a codi mort.

---

## Domini 7 — POM / mesures

[x] fet

Confirmed: `POMGlobal` has NO `codi_intern`, `nom_cat`, `htm_metode_en`, `is_key_measure` fields (it uses `codi`, `nom_ca`, `descripcio_en`, `is_key`). The s9 `setup_tenant_from_excel_view` writes those non-existent fields → broken path (BodyMeasurementISO has `codi_intern`/`nom_cat`, not POMGlobal). `POMEstadisticaGlobal` and `POMEstadisticaTenant` have zero references outside models.py/migrations → orphan models. I have enough. Writing the report.

### Entitats i camps
- 🅰️ `POMGlobal` — catàleg global de POMs (schema `public`); camps `codi`, `nom_en/ca/es`, `categoria` (CharField), bloc S12-A "how to measure" (`abbreviation`, `start_point`, `end_point`, `scope`, `orientation`, `state`, `line`, `body_section`, `is_key`, `tol_prod_cm`, `tol_samp_cm`, `applies_woven/knit/swim`, `iso_ref`), FK `body_measure_iso`. `backend/fhort/pom/models.py:8-76`
- 🅱️ `POMMaster` — POM per-tenant (la **mesura base/catàleg del client**); `codi_client`, `nom_client`, FK `pom_global` (SET_NULL, pot ser tenant-only), FK `categoria`, `tolerancia_default_minus/plus`, `pendent_revisio`, `origen_import`. `models.py:180-252`
- 🅱️ `POMCategory` — categories POM (UPPER/LOWER/JK…); `codi`, `body_area`, `display_order`. `models.py:160-177`
- 🅱️ `ItemBaseMeasurement` — **mesures base TÍPIQUES per Item** (plantilla, Sprint Mesures Base per Item P2); clau `(garment_type_item, pom)`, `base_value_cm`, `tol_minus/plus`, `nom_fitxa`. `models.py:448-483`
- 🅱️ `GarmentPOMMap` — pertinença garment↔POM; `garment_type_item` (db_constraint=False), `pom`, `obligatori`, `is_key`, `nivell` (K/M/O/D), `ordre`, `pendent_revisio`. `models.py:414-445`
- 🅰️ `GarmentTypeGlobal` / 🅱️ `GarmentType` / 🅱️ `GarmentGroup` — tipus i famílies de prenda. `models.py:79-99,355-411`
- 🅱️ `SizeSystem` / `SizeDefinition` — sistemes i etiquetes de talla (domini Talles, no POM). `models.py:272-352`
- 🅱️ `GradingRuleSet` / `GradingRule` / `GradingException` / `GradingRuleHistory` — motor de grading (domini Grading). `models.py:486-609,822-848`
- 🅰️ `FitType`, `Target`, `ConstructionType`, `BodyMeasurementISO`, `SizingProfile` — catàleg global S1 (públic). `models.py:652-819`
- 🅱️ `ClientMesuraPerfil` — estadística Welford per `(codi_client, garment_type, pom, talla)`. `models.py:612-643`
- 🔴 `POMEstadisticaGlobal` (🅰️) i `POMEstadisticaTenant` (🅱️) — estadístiques per POM×garment×talla. `models.py:138-153,255-269`

### Relacions / FK (marca cross-schema amb db_constraint=False)
- `GarmentPOMMap.garment_type_item → tasks.GarmentTypeItem` **CROSS-SCHEMA, `db_constraint=False`** (CASCADE emulat per Django; `pom` és SHARED, `tasks` és tenant-only). `models.py:421-423`
- `ItemBaseMeasurement.garment_type_item → tasks.GarmentTypeItem` **CROSS-SCHEMA, `db_constraint=False`** (mateix motiu). `models.py:460-461`
- `POMMaster.pom_global → POMGlobal` (SET_NULL) i `POMMaster.categoria → POMCategory` (SET_NULL). `models.py:181-194`
- `GarmentPOMMap.pom → POMMaster` (PROTECT); `ItemBaseMeasurement.pom → POMMaster` (PROTECT). `models.py:424,462`
- `GradingRule.pom → POMMaster` (PROTECT); `GradingException.pom`, `ClientMesuraPerfil.pom`, `POMEstadisticaTenant.pom` (PROTECT/CASCADE). `models.py:562,597,628,256`
- `ClientMesuraPerfil.client → tenants.Client` (CASCADE, nullable legacy). `models.py:622-625`
- `GradingRuleHistory.pom → POMGlobal` (SET_NULL) — anomalia: apunta a `POMGlobal`, no `POMMaster` com la resta. `models.py:829-830`

### Endpoints + gating (qui pot, quina capability/gate)
- `POMMasterViewSet` (`poms/`) — `IsAuthenticated`, sense gate d'escriptura (CRUD obert a autenticats). `pom/views.py:44-53`
- `POMCategoryViewSet`, `GarmentGroupViewSet` — ReadOnly, `IsAuthenticated`. `views.py:119-136`
- `GarmentTypeViewSet` (`garment-types/`) — lectura `IsAuthenticated`; escriptura `CONFIGURE`. `views.py:94-116`
- `GarmentPOMMapViewSet` (`garment-pom-maps/`) — lectura `IsAuthenticated`; escriptura `CONFIGURE`. `views.py:236-264`
- `ItemBaseMeasurementViewSet` (`item-base-measurements/` + acció `upsert/`) — lectura `IsAuthenticated`; escriptura `CONFIGURE`. `views.py:267-320`
- `SizeSystem/SizeDefinition/GradingRuleSet/GradingRuleViewSet` — escriptura `CONFIGURE` (`_ConfigureWrite`). `views.py:56-233`
- Wizard POM: `poms/suggerits/`, `poms/cerca/`, `poms/crear-tenant/`, `poms/<id>/nomenclatura/` — `IsAuthenticated`. `pom/urls.py:39-44`, `pom/wizard_views.py:56-400`
- Size-map wizard: `size-map/lookups|match|preview|grading-preview|grading-preview-file|create|systems/` — `_Configure`. `pom/urls.py:59-67`, `size_map_views.py:206-207`
- s9 onboarding: `onboarding/status|setup-from-excel|config/` — `IsAuthenticated`. `tasks/urls.py:251-253`, `s9_views.py`
- `pom-global/cerca/` (s2) — `IsAuthenticated`. `tasks/urls.py:152,165`, `s2_views.py:298-334`

### Frontend que hi penja
- `frontend/src/pages/POMs.jsx` — pestanyes Browser (`POMBrowser mode="assign"`) + Catalogue (`POMCatalogue`). Ruta `poms` a `App.jsx:165`.
- `frontend/src/components/POMBrowser/POMBrowser.jsx` — **eina NOVA** (assign per item): consumeix `garment-pom-maps/?garment_type_item=`, `poms/cerca/`, POST/DELETE/PATCH `garment-pom-maps/`. Explícit "SENSE mock" (`:39,:112`).
- `frontend/src/components/POMBrowser/POMCatalogue.jsx` — vista read-only sobre `poms/` (PAS B5). `:55` "Sense mock".
- 🔴 `frontend/src/pages/GarmentPOMMapEditor.jsx` — **eina VELLA, codi mort** (vegeu VELL/NOU).
- `frontend/src/components/MeasurementTable/MeasurementTable.jsx:24-28` — conté `mock-1..5` (dades hardcoded de POMs, domini Mesures, no POMBrowser).

### Màquina d'estats / signals (PROPIETARI ÚNIC de cada estat: qui l'escriu)
- `SizeFitting.estat`/`base_tancada` — escrit per `pom/services.py` (`generate_graded_specs`→`'TallesGenerades'` `:129`; `close_base`→`'Tancat'` `:283`) i pels wizards `confirm_base_size_view` (`'BaseTancada'`/`'TallesGenerades'` `wizard_views.py:261,271`). **Doble escriptor** del mateix estat (services vs wizard_views) — vegeu VELL/NOU.
- `BaseMeasurement` (viu a `models_app`) — escrit per `save_base_size_view` (`wizard_views.py:190-213`); llegit per `_load_base_measurements` (`services.py:411-424`).
- `ClientMesuraPerfil` — únic escriptor `update_client_profile` (Welford, `services.py:304-349`).
- `GarmentPOMMap` (pertinença + `is_key` + `ordre`) — escriptor des de POMBrowser-assign via ViewSet; loader `load_garment_pom_map` (referenciat a `models.py:428`, comanda d'import).

### Serveis d'única entrada reaprofitables
- `pom/services.py:_apply_rule` (`:476`) — motor canònic de grading (LINEAR/STEP/FIXED/ZERO + forma canònica `increment_base`/break). Reusat per `generate_graded_specs` (persisteix) i `preview_graded_specs` (sense persistència, `:142`).
- `find_pom_master(code, description)` — `models_app/extraction_views.py:1070-1149` — **resolució única de POM mestre** (estratègies: exacte codi → root-prefix → sinònims `_POM_SYNONYMS` → nom_client → POMGlobal/abbrev → numèric-lining). Reusat per extraction_views (import IA) i `size_map_views` (`:217,:246,:329,:389`).
- `get_or_create_size_fitting` / `close_base` (`services.py:204,238`) — entrada única de tancament de taula (idempotent).

### 🔴 VELL/NOU (codi mort viu · dobles camins · òrfenes · documentat-no-implementat)
- **DOBLE CAMÍ POMBrowser (NOU) vs GarmentPOMMapEditor (VELL)**: el VELL `GarmentPOMMapEditor.jsx` està marcat CODI MORT a `App.jsx:20-21` ("jubilat al sprint tasca-POM… endpoints fantasma pom-map/* → 404. Substituït per POMBrowser-assign"). NO s'importa ni s'enruta. Pega contra `garment-types/{id}/pom-map/`, `…/pom-map/add/`, `…/pom-map/<id>/`, `garment-types/full/` — **cap d'aquests endpoints existeix al backend** (només existeix `pom-global/cerca/`). A més usa `p.codi_intern`/`p.nom_en` de POMGlobal (camp `codi_intern` NO existeix a POMGlobal). El seu `HTMTooltip` també hi penja. → eliminable.
- **NO se solapen en runtime**: POMBrowser treballa per **item** (`garment_type_item`, model nou), GarmentPOMMapEditor per **família/garment-type** (model vell). La migració família→item està "COMPLETADA (PAS 6)" i el FK legacy `garment_type` de `GarmentPOMMap` s'ha eliminat (migració 0016, `models.py:415-417`).
- **MOCK_POMS**: no existeix cap símbol `MOCK_POMS` al codi. POMBrowser/POMCatalogue diuen explícitament "SENSE mock". L'únic mock POM viu és l'array hardcoded `mock-1..5` a `MeasurementTable.jsx:24-28` (domini Mesures, fallback de demo).
- 🔴 **`s9_views.setup_tenant_from_excel_view` BROKEN (schema drift)**: escriu `POMGlobal.objects.update_or_create(codi_intern=…, nom_cat=…, htm_metode_en=…, htm_cat=…, htm_punt_inici_en=…, is_key_measure=…)` (`s9_views.py:179-191`) però `POMGlobal` **no té cap d'aquests camps** (té `codi`, `nom_ca`, `descripcio_en`, `is_key`; `codi_intern`/`nom_cat` viuen a `BodyMeasurementISO`). Cada fila peta i s'empassa amb `except Exception: pass` → el seed de `pom_globals` mai escriu res. Documentat-no-implementat/codi mort viu.
- 🔴 **`POMEstadisticaGlobal` i `POMEstadisticaTenant` òrfenes**: cap referència fora de `models.py` i migracions (només `ClientMesuraPerfil` s'usa de debò, a services + reseed). Taules d'estadística sense cap escriptor/lector.
- 🔴 **`POMMaster.is_key_measure` mort** (`models.py:249-252`): property que retorna sempre `False` amb comentari "no equivalent field"; les alias-properties (`pom_code`, `name_cat`, `display_order`…) avisen que NO funcionen a l'ORM (TECH_DEBT #2).
- 🔴 **Doble escriptor de tancament**: `confirm_base_size_view` (`wizard_views.py:228-288`) i `close_base`/`generate_graded_specs` (`services.py`) escriuen tots dos `SizeFitting.estat`/`base_tancada`; el wizard duplica la lògica (mín. 3 POMs, generar grading) en lloc de delegar a `close_base`. Camins paral·lels a vigilar.
- `GradingRuleHistory.pom → POMGlobal` (no POMMaster) — inconsistència respecte a la resta del domini; sospitós d'històric no usat (cap escriptor trobat al domini POM).

### 🔗 CONNECTA AMB (blast radius: què es trenca si ho toques)
- `POMMaster` és el centre: el referencien `GarmentPOMMap`, `ItemBaseMeasurement`, `GradingRule`, `GradingException`, `ClientMesuraPerfil`, `POMEstadisticaTenant`, i `BaseMeasurement`/`GradedSpec` (apps `models_app`/`fitting`). Tocar PK/`codi_client` trenca el grading i el matching (`find_pom_master` filtra per `codi_client__iexact`).
- `GarmentPOMMap` ↔ `tasks.GarmentTypeItem` (cross-schema): si es renombra/elimina `GarmentTypeItem`, el CASCADE lògic (no de BD) cau a Django; un constraint real petaria a `public`.
- `_apply_rule` el comparteixen `generate_graded_specs` i `preview_graded_specs` (run d'importació W3): canviar-ne la firma trenca el preview del wizard d'importació i el grading real alhora.
- `find_pom_master` el criden `extraction_views` (import IA de fitxes) i `size_map_views` (preview grading des de fitxer/paste): un canvi d'estratègia afecta tot el matching POM del sistema.
- POMBrowser depèn de tres endpoints (`garment-pom-maps/`, `poms/cerca/`, `poms/` per Catalogue) i del `GarmentPOMMapSerializer` flat (fallback pom_global→tenant-only); canviar els camps del serializer trenca `normalizePOMs` (`POMBrowser.jsx:40-84`).

### 🅰️/🅱️ Línia
- 🅰️ Plataforma/global (schema public): `POMGlobal`, `GarmentTypeGlobal`, `TascaGlobal`, `FitType`, `Target`, `ConstructionType`, `BodyMeasurementISO`, `SizingProfile`, `POMEstadisticaGlobal`, `find_pom_master` (lògica genèrica reusable).
- 🅱️ Servei/tenant (treball facturable sobre models del client): `POMMaster`, `POMCategory`, `GarmentPOMMap`, `ItemBaseMeasurement`, `ClientMesuraPerfil`, `POMEstadisticaTenant`, tot el motor de grading aplicat (`services.py`), POMBrowser/POMCatalogue, wizards base-size i size-map.
- 🅰️🅱️ Endpoints POM ViewSets: codi de plataforma (genèric, multi-tenant) operant sobre dades de servei per-tenant.

### ⚖️ PER DECIDIR (Agus)
- Eliminar `frontend/src/pages/GarmentPOMMapEditor.jsx` (+ el seu ús de `HTMTooltip` si no s'usa enlloc més) ja que és codi mort confirmat amb endpoints 404.
- Decidir el futur de `s9_views.setup_tenant_from_excel_view`: està trencat (escriu camps inexistents a POMGlobal) i emmascarat per `except: pass`. Reparar contra el schema real o retirar l'endpoint `onboarding/setup-from-excel/`.
- Esborrar (o implementar escriptors) `POMEstadisticaGlobal` / `POMEstadisticaTenant`: avui són taules òrfenes sense cap codi que les escrigui ni llegeixi.
- Unificar el tancament de taula: fer que `confirm_base_size_view` delegui a `close_base`/`get_or_create_size_fitting` en lloc de duplicar la màquina d'estats.
- `POMMasterViewSet` no té gate `CONFIGURE` a l'escriptura (a diferència de GarmentType/GarmentPOMMap/ItemBaseMeasurement): decidir si crear/editar/esborrar POMs del catàleg ha d'estar gated.
- Resoldre la incoherència `GradingRuleHistory.pom → POMGlobal` vs `POMMaster` a la resta del domini.

### Obert / dubtós (el que no he pogut determinar amb certesa)
- No he pogut confirmar des de la BD quants POMs orfes reals hi ha (POMMaster sense cap `GarmentPOMMap` ni `BaseMeasurement`); el codi tracta el cas (`POMMaster.pom_global=None` = "tenant-only importat per IA", marcat `incomplete` a POMCatalogue) però el recompte exacte requereix consulta a BD (prohibida).
- `load_garment_pom_map` (loader referenciat a `models.py:428`) no l'he localitzat per nom exacte dins `management/commands/`; podria viure a `load_map_inline.py` o `replace_pom_catalog.py` — no verificat amb certesa.
- Si `HTMTooltip` (importat només per GarmentPOMMapEditor segons el que he vist) s'usa en altres pàgines: no ho he comprovat exhaustivament.
- L'estat real de la sèrie "Mesures Base per Item" (P1–P5): el model i el ViewSet `ItemBaseMeasurement`+`upsert` existeixen (P2/P3), però no he verificat que la columna ASSIGN del POMBrowser (P4) ni la sembra item→model (P5) estiguin cablejades al frontend.

---

## Domini 8 — Grading

[x] fet

Tinc tot el necessari per la síntesi.

### Entitats i camps
- 🅰️ `GradingRuleSet` (joc de regles compartit, schema public) — `pom/models.py:486`; camps `nom`, `garment_group` FK, `size_system` FK, `actiu`, `is_system_default`, `parent_version` (self-FK versionat), `version_number`, `codi_sistema`; camí targets dual `target` FK legacy (`:504`) + `targets` M2M (`:509`); `construction`/`fit_type` FK (`:516-525`).
- 🅰️ `GradingRule` (regla per (rule_set, pom)) — `pom/models.py:547`; choices `LOGICA_LINEAR/STEP/FIXED/ZERO/EXCEPTION` (`:548-559`); FK `rule_set`/`pom`/`talla_base`; `increment` Decimal (`:570`), `valors_step` JSON (`:571`), forma canònica `increment_base`/`increment_break`/`talla_break_label`/`talla_break_pos` (`:574-577`), `actiu`; `unique_together (rule_set, pom)`.
- 🅰️ `GradingException` (override per (rule_set, pom, size)) — `pom/models.py:594`; `size_label`, `value_cm`, `is_active`.
- 🅰️ `GradingRuleHistory` (canvis de regla) — `pom/models.py:822`.
- 🅱️ `GradingVersion` (versió de grading d'un SizeFitting, tenant) — `fitting/models.py:62`; `size_fitting` FK, `nom`, `aprovada` (=segellat producció), `version_number`, `is_active`, `creat_per`, `aprovada_per`/`data_aprovacio` (`:81-87`).
- 🅱️ `GradedSpec` (sortida del motor: valor per (version, pom, size)) — `fitting/models.py:163`; `graded_value_cm`, `grading_type_applied`, `increment_applied_cm`, `is_active`, `generated_from_version` (link a `measurements_version`, comparació stale "NOT implemented here" `:182-186`); `unique_together (grading_version, pom, size_label)`.
- 🅱️ `ModelGradingRule` (graduació canònica RESIDENT al model, PG-0) — `models_app/models.py:623`; mateixa forma que `GradingRule` (`logica`, `increment`, `valors_step`, `increment_base/break`, `talla_break_*`), `origen` (IMPORTED/CANONICAL/MANUAL), `actiu`; `unique_together (model, pom)`.
- 🅱️ `ModelGradingOverride` (override per-model per talla, des de fitting validat, Sprint 5B.3) — `models_app/models.py:587`; `value_cm`, `size_label`, `motiu`, `fitting_ref` FK, `created_by`; `unique_together (model, pom, size_label)`.
- 🅱️ Config de grading al `Model` — `models_app/models.py:193` (`grading_rule_set` FK), `:264-271` (`size_run_model`, `base_size_label`), `:279` (`measurements_version`).

### Relacions / FK (marca cross-schema amb db_constraint=False)
- 🅱️ `ModelGradingRule.pom → pom.POMMaster` amb `db_constraint=False` (cross-schema tenant→public) — `models_app/models.py:646-649`.
- 🅱️ `ModelGradingOverride.pom → pom.POMMaster` (FK normal, sense `db_constraint=False` explícit) — `models_app/models.py:599`; `fitting_ref → fitting.PieceFitting` SET_NULL `:603`.
- 🅱️ `GradedSpec.pom → pom.POMMaster` (cross-schema, FK normal sense db_constraint=False) — `fitting/models.py:175`.
- 🅱️ `GradingVersion.size_fitting → fitting.SizeFitting` CASCADE — `fitting/models.py:63`.
- 🅱️ `Model.grading_rule_set → pom.GradingRuleSet` SET_NULL — `models_app/models.py:193`.
- 🅰️ `GarmentTypeItem.grading_rule_set` i `base_size_definition` (tasks) amb validació de coherència `size_system` — `tasks/models.py:397-398`.

### Endpoints + gating (qui pot, quina capability/gate)
- 🅱️ `POST /api/v1/models/<id>/generar-grading/` → `generate_grading_view` — `models_app/views.py:1099`; ruta `models_app/urls.py:177`. Gating: cal mirar el decorador (la funció comença sense decorador visible al fragment; el viewset proper sí). Crida `generate_graded_specs`.
- 🅱️ `POST /api/v1/models/<id>/set-size-override/` → `set_size_override_view`, gating `_ExecuteTasksCap` (capability `EXECUTE_TASKS`) — `models_app/views.py:1185-1191`; ruta `:178`. Escriu `ModelGradingOverride` + re-propaga.
- 🅱️ `POST /api/v1/models/<id>/pom/<pid>/regim/` → `set_pom_regim_view`, gating `IsAuthenticated` — `models_app/views.py:1818-1819`; ruta `:180`. UPSERT `logica` d'una `ModelGradingRule`.
- 🅱️ `GET /api/v1/models/<id>/taula-mesures/` → `measurements_table_view` (model) — ruta `models_app/urls.py:171`.
- 🅱️ `POST size-fittings/<sf_id>/tancar-base/`, `regenerar-talles/`, `GET taula-mesures/` → `close_base_view`/`regenerate_sizes_view`/`measurements_table_view`, gating `IsAuthenticated` — `pom/grading_views.py:8,28,48`; rutes a `tasks/urls.py:122-124`.
- 🅱️ `GET fitting/<sf_id>/graded-table/` → `GradedSpecTableView` — `fitting/urls.py:66`.
- 🅰️ `grading-rule-sets` + `grading-rules` routers (CRUD ViewSets) — `pom/urls.py:24-25`; `grading-versions` router `GradingVersionViewSet` gating `IsAuthenticated` — `fitting/urls.py:40`, `fitting/views.py:69-72`.
- 🅰️ Edició de regles amb història: `grading-rule-sets/<id>/regles/<pom_codi>/...` → `update_grading_rule_view` (s2), `update_grading_rule_with_history_view` + `grading_rule_history_view` + `grading_rules_with_units_view` (s4) — `tasks/urls.py:163,185-189`.
- 🅱️ `graded-specs-units` (s6) `tasks/urls.py:211`; export CSV (s8) `:229`.
- 🅱️ Preview import: `import-sessions/<token>/grading-preview/` → `import_session_grading_preview_view` — `models_app/urls.py:70`; `size-map/grading-preview[-file]/` (s catàleg) `pom/urls.py:63-64`.

### Frontend que hi penja
- 🅱️ `frontend/src/pages/ModelMeasurements.jsx:69` crida `POST generar-grading/`; llegeix `taula-mesures/` (`:76,96,138,218,385`); botó "generate_grading" `:350`.
- 🅱️ `frontend/src/pages/PropagatedEditor.jsx:25` llegeix `taula-mesures/` (editor propagat, PG-4b).
- 🅱️ `frontend/src/api/endpoints.js:40` `setPomRegim`, `:43` `setSizeOverride`.
- 🅰️ `endpoints.js:118-124` `grading-rule-sets`/`grading-rules` (list + patch regla `:120`); `:378` `grading-versions` list.
- 🅰️🅱️ Pàgines/components: `GradingRuleSets.jsx`, `GradingHistoryPanel.jsx`, `components/grading/AxesSelector.jsx`/`gradingAxes.js`/`RuleSetPicker.jsx`, `MeasurementTable.jsx`, `SizeMapSetup.jsx`.

### Màquina d'estats / signals (PROPIETARI ÚNIC de cada estat: qui l'escriu)
- 🅱️ `GradedSpec` (valor + tipus): PROPIETARI ÚNIC = motor `_upsert_graded_spec` dins `generate_graded_specs` — `pom/services.py:568,117`. Comentaris reforcen que cap altre camí l'ha d'escriure (`models_app/views.py:771-773` el grading inline "estava trencat… eliminat"; set-size-override "NO toca GradedSpec directament" `:1198`).
- 🅱️ `SizeFitting.estat='TallesGenerades'`: escrit per `generate_graded_specs` — `pom/services.py:128-131`.
- 🅱️ `GradingVersion.is_active`/creació: `_get_or_create_grading_version` — `pom/services.py:427`.
- 🅱️ `GradingVersion.aprovada` (segellat producció): PROPIETARI ÚNIC = `seal_model_grading`, conseqüència d'avanç de gate, no de tancar sessió — `fitting/services.py:563-583`.
- 🅱️ `ModelGradingOverride`: escrit NOMÉS per `set_size_override_view` (`models_app/views.py:1255`); el comentari diu que la sessió de fitting ja NO n'escriu (`fitting/services.py:394-396`).
- 🅱️ `ModelGradingRule`: escrit per `materialize_model_grading_rules` (wipe-and-recreate, `models_app/services.py:67`) i per `set_pom_regim_view` (`models_app/views.py:1841-1859`).

### Serveis d'única entrada reaprofitables
- 🅱️ `generate_graded_specs(sf_id)` — `pom/services.py:18` — ÚNIC motor de persistència de grading; cridat des de grading_views, models_app/views (generar-grading, set-size-override), fitting/services, services_size_check, extraction, clone_model_for_qa, wizard_views.
- 🅱️ `preview_graded_specs(model, base_values)` — `pom/services.py:142` — mateixa lògica sense persistir (wizard import W3).
- 🅱️ `_apply_rule(...)` — `pom/services.py:476` — ZONA INTOCABLE: nucli de càlcul LINEAR/STEP/FIXED/ZERO + forma canònica break per etiqueta (`:504-522`); STEP no gradua canònic encara que `increment_base` estigui poblat (`:502-503`).
- 🅱️ `_load_grading_rules(model)` — `pom/services.py:356` — resol el DOBLE CAMÍ: `ModelGradingRule` resident té prioritat; fallback a `GradingRule` del rule_set extern.
- 🅰️ `derive_grading_rule_set(...)` + `detect_grading(...)` — `pom/grading_utils.py:226,116` — derivació/anti-proliferació compartida import↔Size Library; `grading_rules_match` — `:29` compara resident vs canònic.
- 🅱️ `materialize_model_grading_rules(model, source_rules, origen)` — `models_app/services.py:67`.
- 🅱️ `vigent_grading_version(sf)` — `fitting/services.py:540` — criteri ÚNIC de versió per a lectors.

### 🔴 VELL/NOU (codi mort viu · dobles camins · òrfenes · documentat-no-implementat)
- DOBLE CAMÍ targets de RuleSet: `GradingRuleSet.target` FK legacy (`pom/models.py:504`, related_name `*_legacy`) coexisteix amb `targets` M2M autoritatiu (`:509`). El FK encara s'ESCRIU (`size_map_views.py:572`) i es copia en clonar (`s2_views.py:171,196`), i es llegeix per a noms (`size_map_views.py:572,691`, `s8_views.py:125`). El comentari diu "FK will be removed in a later sprint" → documentat-no-eliminat. ⚖️
- DOBLE CAMÍ de relació de regles: `ModelGradingRule` resident (NOU, PG-0) vs `GradingRule` del `GradingRuleSet` compartit (VELL). `_load_grading_rules` (`pom/services.py:356-377`) fa fallback; conviuen per disseny fins que el backfill ompli residents.
- DOBLE CAMÍ d'override per talla: `ModelGradingOverride` (per-model, NOU) vs `GradingException` (al rule_set compartit, VELL/template). El motor llegeix tots dos amb prioritat override>exception (`pom/services.py:92-100`); `ModelGradingOverride` docstring diu que `GradingException` "would leak to every model" (`models_app/models.py:591-592`).
- Camí trencat ELIMINAT (codi mort retirat, documentat): grading inline a set-measurements (`rule.increment_cm` inexistent → delta 0, clobberava overrides) — `models_app/views.py:771-773`.
- `valors_step` declarat "origen/auditoria" però NO usat per al càlcul quan `increment_base` poblat (excepte STEP) — `pom/models.py:571-573`, `services.py:498-504`. Latent.
- Documentat-no-implementat: detecció de specs stale via `generated_from_version < measurements_version` "NOT implemented here, only the link is stored" — `fitting/models.py:182-186`.
- MODELS REFORMA legacy retirats (referència històrica): `SFFitting`/`SFFittingLinia` eliminats (migration `0010_delete_sffitting.py`), reemplaçats per FittingSession/PieceFitting — `fitting/models.py:153-156`.
- `valor_base` de `GradingRule` ELIMINAT (migration `0024`), documentat com a redundant sempre 0 — `pom/models.py:566-569`.

### 🔗 CONNECTA AMB (blast radius: què es trenca si ho toques)
- Tocar `_apply_rule`/`generate_graded_specs` (`pom/services.py`) → trenca: grading_views (regenerar-talles), generar-grading, set-size-override, set_pom_regim (indirecte), fitting close, services_size_check, extraction W5, clone_model_for_qa, wizard_views, preview import. És el coll d'ampolla del domini.
- Tocar `GradedSpec` → lectors graded-table (`fitting/graded_spec_views.py`), taula-mesures (`pom/grading_views.py`), graded-specs-units (`s6_views.py`), serializers (`fitting/serializers.py:218`), PieceFittingLine clonat de specs (`fitting/services.py:296,325`), fitting-vs-spec (s10).
- Tocar `Model.size_run_model`/`base_size_label`/`grading_rule_set` → pre-checks del motor (`pom/services.py:42-58`); el run es re-parseja a múltiples llocs (motor, set-size-override `:1236`, derive `grading_utils.py:258`).
- Tocar el FK legacy `GradingRuleSet.target` → size_map create/clone i exports CSV.

### 🅰️/🅱️ Línia
- 🅰️ Plataforma (catàleg compartit public): `GradingRuleSet`, `GradingRule`, `GradingException`, `GradingRuleHistory`, ViewSets de grading-rule(-set)s, derive/detect a `grading_utils.py`.
- 🅱️ Servei (treball facturable sobre models del client, tenant): `GradingVersion`, `GradedSpec`, `ModelGradingRule`, `ModelGradingOverride`, motor `generate_graded_specs`/`_apply_rule`, endpoints generar-grading/set-size-override/regim, frontend ModelMeasurements/PropagatedEditor.
- 🅰️🅱️ Frontera: `Model.grading_rule_set` FK (tenant→public) i `_load_grading_rules` (escull entre resident 🅱️ i compartit 🅰️).

### ⚖️ PER DECIDIR (Agus)
- FK legacy `GradingRuleSet.target`: encara s'escriu i es clona (`size_map_views.py:572`, `s2_views.py:171,196`) tot i ser "legacy fins eliminar". Decidir si es retira ja o es manté el doble camí.
- Convivència de tres mecanismes de personalització per talla (resident `ModelGradingRule`, override `ModelGradingOverride`, excepció compartida `GradingException`): confirmar que `GradingException` (camí compartit/leak) es manté només per a seeds ISO o es deprecia per-model.
- `GradedSpec.pom` no porta `db_constraint=False` (`fitting/models.py:175`) tot i ser cross-schema tenant→public, a diferència de `ModelGradingRule.pom` que sí (`models_app/models.py:648`). Possible inconsistència de constraint a revisar.
- Stale-spec detection (`generated_from_version` vs `measurements_version`): documentada però mai implementada — decidir si es prioritza.

### Obert / dubtós
- El decorador de gating exacte de `generate_grading_view` (`models_app/views.py:1099`) no apareix al fragment llegit (la línia de decorador queda just abans de `:1099`); cal confirmar si és `IsAuthenticated` o una capability. No ho dono per cert.
- No he verificat el gating real del `GradingVersionViewSet` per acció (és `ModelViewSet` amb `IsAuthenticated` global, `fitting/views.py:69-72`) — podria permetre CRUD directe de versions saltant el motor; no confirmat si el frontend ho usa per escriure.
- No he resseguit si `set_pom_regim_view` (només `IsAuthenticated`) hauria d'exigir una capability més forta com els altres editors de grading; queda obert.

---

## Domini 9 — Fitting / Size Check

[x] fet

I now have full coverage. Producing the report.

### Entitats i camps

- 🅱️ `SizeFitting` — `fitting/models.py:7-59`. Camps: `model` FK, `numero`, `codi` unique, `tipus` (Proto/Fit/SizeSet/PP/TOP) `:8-14`, `sf_pare` self-FK `:27-33`, `estat` (Pendent/BaseOberta/BaseTancada/TallesGenerades/Tancat) `:15-21,35`, `data_creacio/data_tancament`, `creat_per`, `notes`, `base_tancada` + `data_tancament_base` (Sprint 1A) `:48-49`. **Aquesta és l'accepció ACTUAL de "SizeFitting": la TAULA de mesures/grading d'un model, NO una sessió de fitting.**
- 🅱️ `GradingVersion` — `fitting/models.py:62-95`. `size_fitting` FK, `version_number`, `is_active`, `aprovada` (segell de producció) + `aprovada_per`/`data_aprovacio` `:81-87`.
- 🅱️ `GradedSpec` — `fitting/models.py:163-195`. Output del motor de grading per (GradingVersion, POM, talla); `generated_from_version` (stale link, no implementat) `:186`.
- 🅱️ `POMAlert` — `fitting/models.py:98-150`. Alertes de desviació; camps S11 (`desviacio_cm`, `tolerancia_cm`, `origen`, `resolt_per_user_id` cross-schema) `:136-143`.
- 🅱️ `FittingSession` — `fitting/models.py:202-288`. **L'accepció NOVA del "fitting": l'esdeveniment de provatura.** `estat` (Programada/Oberta/Tancada/Anullada) `:209-242`, `fase` (reusa `Model.FASE_CHOICES`) `:229`, XOR `garment_set`/`model` (CheckConstraint) `:276-284`, `convocatoria` UUID `:258`, temps real `started_at`/`finished_at` `:262-267`, `attendees` M2M `:254`.
- 🅱️ `PieceFitting` — `fitting/models.py:291-334`. Una peça avaluada; **posseeix el seu propi `gate`** (Pendent/OK/NO_OK/EXCEPCIO) `:293-309`, `gate_motiu`/`gate_per`/`gate_at` `:310-318`, `unique_together (session, model)` `:331`.
- 🅱️ `PieceFittingLine` — `fitting/models.py:337-359`. `valor_teoric` (grading) vs `valor_real` (mesurat), `pom`, `size_label`.
- 🅱️ `FittingPhoto` — `fitting/models.py:362-384`.
- 🅰️🅱️ `FittingDurationStat` — `fitting/models.py:387-402`. Singleton (pk=1) Welford de durada real, agregat global del tenant.
- 🅱️ `SizeCheck` — `models_app/models.py:787-820`. **Size Check (SC-0): validació del proto a talla base, PRE-fitting. Entitat NETA, viu a models_app (no a fitting).** `estat` (Pendent/Acceptat/Rebutjat/Descartat) `:790-800`, `talla_base_label`, `missatge_fabricant`, `resolt_per`/`resolt_at`. Historial repetible (SENSE unique_together).
- 🅱️ `SizeCheckLine` — `models_app/models.py:823-854`. `valor_teoric` (snapshot del `BaseMeasurement.base_value_cm`), `valor_real`, `decisio` (tolerancia_acceptada/valor_descartat) `:840-844`, `nota`.

### Relacions / FK (marca cross-schema amb db_constraint=False)

- 🅱️ `SizeCheckLine.pom` → `pom.POMMaster` **`db_constraint=False`** (cross-schema; pom és app SHARED) — `models_app/models.py:831-834`.
- 🅱️ `GradedSpec.pom`, `POMAlert.pom`, `PieceFittingLine.pom` → `pom.POMMaster` **SENSE** `db_constraint=False` (`fitting/models.py:175,119,346`). Asimetria amb SizeCheckLine: les FK pom de l'app fitting NO declaren `db_constraint=False` tot i ser el mateix patró cross-schema → veure 🔴.
- 🅱️ `GradingVersion.size_fitting` → `SizeFitting` CASCADE (`fitting/models.py:63`).
- 🅱️ `PieceFitting.grading_version` → `GradingVersion` PROTECT (`fitting/models.py:306`); `PieceFitting.model` PROTECT (`:303`).
- 🅱️ `FittingSession.garment_set` → `models_app.GarmentSet` / `.model` → `models_app.Model` (XOR) (`fitting/models.py:216-227`).
- 🅱️ `SizeCheck.model` → `models_app.Model` PROTECT (`models_app/models.py:797`).
- 🅰️ FKs a `accounts.UserProfile` (creat_per, gate_per, aprovada_per, resolt_per) — totes mateix schema.

### Endpoints + gating (qui pot, quina capability/gate)

- 🅱️ `SizeFittingViewSet` (ModelViewSet complet) — `fitting/views.py:55-70`, router `size-fittings` — **`IsAuthenticated`** (sense capability).
- 🅱️ `FittingSessionViewSet` — `fitting/views.py:98`. Base `IsAuthenticated`; `schedule`/`schedule-bulk`/`open`/`destroy`/`discard`/`seal` → **`_ScheduleFittingsPerm` (capability `schedule_fittings`)** `:174-175,241-242,286-287,297-301`. `advance-phase` `:161-162` → només IsAuthenticated.
- 🅱️ Operacions de grup (`group_reschedule`, `group_add_model`, etc.) → **`_ScheduleFittingsPerm`** `:339,357,382,395,403`.
- 🅱️ `PieceFittingViewSet` — `fitting/views.py:419-462`. `set-gate`, `close`, `discard` → **NOMÉS `IsAuthenticated`** (cap capability). El gate de peça i el tancament no estan protegits per `schedule_fittings`.
- 🅱️ `PieceFittingLineViewSet` — `fitting/views.py:465+`. PATCH autosave + `propagar` → **`IsAuthenticated`** (`:483-490`, comentari explícit "Permís = el del viewset").
- 🅱️ `SizeCheckViewSet` (retrieve/list/`open`/`resolve`) — `models_app/views_size_check.py:29-75`, router `size-checks` (`models_app/urls.py:38`) → **`IsAuthenticated`** (cap capability). Guard de schema public → queryset buit `:38-41`.
- 🅱️ `SizeCheckLineViewSet` PATCH autosave — `models_app/views_size_check.py:78-88` → `IsAuthenticated`.
- 🅱️ `GradedSpecTableView` (F3 fitxa tècnica) — `fitting/urls.py:66`, `fitting/graded_spec_views.py`.

### Frontend que hi penja

- 🅱️ `frontend/src/pages/FittingDetail.jsx` — graella de sessió; crida `pieceFittings.close` `:188`, `fittingSessions.seal` `:197`, `createPiece` `:526`, propagar en temps real.
- 🅱️ `frontend/src/components/model/SizeCheckTab.jsx` — Size Check; `sizeChecks.open(model.id)` `:48-49`, `sizeChecks.resolve` `:91`; mode `editable` (Kanban, fa open) vs consulta (NO fa open) `:26-29`. Mapeig: descartades → Rebutjat, sense → Acceptat `:75-79`.
- 🅱️ `frontend/src/components/model/SizeCheckCell.jsx` — cel·la editable; `decisio` select, `valor_descartat` preescriu nota `:63-71`.
- 🅱️ `frontend/src/api/endpoints.js` — `fittingSessions.*` `:314-334`, `pieceFittings.{setGate,close,discard}` `:339-343`, `pieceFittingLines.propagar` `:351`, `sizeChecks.{open,resolve}` `:361-367`, `sizeCheckLines.update` `:374`.
- 🅱️ També referenciat a `KanbanTasks.jsx`, `ModelSheet.jsx`, `BaseStageTable.jsx`, `WorkPlan.jsx`.

### Màquina d'estats / signals (PROPIETARI ÚNIC de cada estat: qui l'escriu)

- 🅱️ **`SizeFitting.estat`** → PROPIETARI: **app `pom`** (el wizard de la taula), NO fitting. Escriptors: `pom/wizard_views.py:261` (`BaseTancada`), `:270` + `pom/services.py` `generate_graded_specs` (`TallesGenerades`), `pom/services.py:286` (`Tancat`). **L'app fitting MAI escriu `SizeFitting.estat`.**
- 🅱️ **`SizeFitting.base_tancada`** → PROPIETARI: `pom/wizard_views.py:259` i `pom/services.py:284`.
- 🅱️ **`FittingSession.estat`** → PROPIETARI: `fitting/services.py` — `Oberta` a `open_session` `:283`, `Tancada` a `_seal_session` `:658`, `Anullada` a `discard_session` `:876`, `Programada` a `schedule_session` `:177`.
- 🅱️ **`PieceFitting.gate`** → PROPIETARI: `fitting/services.py:set_piece_gate` `:612-616` (únic escriptor).
- 🅱️ **`GradingVersion.is_active`/`version_number`** → escrits a `close_piece_fitting` (`fitting/services.py:448-460`) i a `resolve_size_check` (`services_size_check.py:214-225`) i `generate_graded_specs`.
- 🅱️ **`GradingVersion.aprovada` (segell producció)** → PROPIETARI: `seal_model_grading` (`fitting/services.py:579-582`), cridat NOMÉS des de `tasks/services_d.py:advance_phase_gate:50-53`.
- 🅱️ **`SizeCheck.estat`** → PROPIETARI: `services_size_check.py:resolve_size_check:254` (final: Acceptat si cap descartada, Rebutjat si n'hi ha, Descartat si acció Descartar `:143-146`).
- 🅱️ **`BaseMeasurement` origen='CHECKED'** → escrit per `resolve_size_check` `:172-184`; **origen='FITTED'** → per `close_piece_fitting` `:402-411`. Tots dos disparen el signal F1 `log_measurement_change` (via `bm._changed_by`/`_motiu`).
- 🅱️🔴 **`Model.fase_actual`** → PROPIETARI ÚNIC EXPLÍCIT: **`tasks/services_d.py:advance_phase_gate:37`** (+ `GateEvent` `:46`). `fitting.advance_phase` **NO** escriu `fase_actual` ni segella (D-3, comentaris `:751-769`): `sealed`/`advanced` queden SEMPRE buits a posta.
- 🅱️ Signal/hook **brain** `on_fitting_measurement_changed` — disparat per `close_piece_fitting:472` i `set_piece_gate` (NO_OK) `:621`. STUB: només logueja, NO propaga (`fitting/brain.py`).

### Serveis d'única entrada reaprofitables

- 🅱️ `_resolve_working_size_fitting(model)` `fitting/services.py:517-527` — resol el SizeFitting de treball del model; reusat per `resolve_size_check` (`services_size_check.py:194,197`) i pom.
- 🅱️ `_active_grading_version(sf)` / `vigent_grading_version(sf)` `fitting/services.py:529-560`.
- 🅱️ `generate_graded_specs(sf.pk)` `pom/services.py` — únic motor de regraduació, cridat per `close_piece_fitting:469` i `resolve_size_check:230`.
- 🅱️ `model_te_deltes(model)` `services_size_check.py:81-95` — booleà que decideix si una correcció base propaga a talles.
- 🅱️ `seal_model_grading(model)` `fitting/services.py:563-583` — única porta del segell; cridada NOMÉS per advance_phase_gate.
- 🅰️🅱️ `update_fitting_duration_stat` `fitting/services.py:690-705` — Welford singleton.
- 🅱️ `propaga_ancoratges` (`pom/grading_utils`) — motor de propagació LINEAR en temps real, reusat per `propagar` (`fitting/views.py:493`).

### 🔴 VELL/NOU (codi mort viu · dobles camins · òrfenes · documentat-no-implementat)

- 🔴 **COL·LISIÓ DE NOM resolta — dues accepcions de "fitting":** (1) `SizeFitting` = la TAULA de mesures/grading d'un model (entitat vella, Sprint 1-3, eix pom); (2) `FittingSession`/`PieceFitting` = l'esdeveniment de provatura (entitat nova, Sprint 5B). Conviuen: `PieceFitting.grading_version.size_fitting` enllaça la nova amb la vella. NO és el mateix concepte tot i el nom; cap és mort.
- 🔴 **Brain = motor simulat (documentat-no-implementat):** `fitting/brain.py:16-32` és STUB confés ("STUB: no propagation"). Es crida des de 3 punts (`close_piece_fitting:472`, `set_piece_gate` NO_OK `:621`) però NO propaga res, NO reobre tasques, NO marca stale. `GradedSpec.generated_from_version` (`fitting/models.py:182-186`) és el link previst per la detecció de stale, també no implementat.
- 🔴 **Estats de `SizeFitting` parcialment morts:** `Pendent`/`BaseOberta` (`fitting/models.py:16-17`) gairebé no s'escriuen mai com a valor viu; `BaseOberta` només apareix com a *origen* tolerat a `_CLOSEABLE_FROM` (`pom/services.py:200`), mai com a destinació escrita. El cicle real és Pendent(default)→BaseTancada→TallesGenerades→Tancat.
- 🔴 **`SizeFitting.sf_pare`/`fills` òrfena:** definits (`fitting/models.py:27-33`) i només llegits a `select_related('sf_pare')` (`fitting/views.py:60`); cap codi els ESCRIU ni navega l'arbre. Camp sense ús funcional.
- 🔴 **`SizeFitting.tipus` incoherent:** choices Proto/Fit/SizeSet/PP/TOP (`:8-14`) però l'únic creador (`pom/services.py:234`) sempre força `'SizeSet'`. El test usa `'PRINCIPAL'` (`tests.py:57`), valor que NI tan sols és a TIPUS_CHOICES → fixture amb valor invàlid.
- 🔴 **`override_changed` mort viu:** `close_piece_fitting` retorna `override_changed` que SEMPRE és `False` (`fitting/services.py:357,384,488`); es manté "per compat. de forma". Restes del deute sessió→override retirat (PEÇA 4, `:393-398`).
- 🔴 **`advance_phase` (fitting) buidada:** `sealed`/`advanced` SEMPRE buits a posta (D-3); la funció ja no fa res tret de `_seal_session` (`fitting/services.py:751-771`). Doble camí històric amb `advance_phase_gate` resolt a favor de tasks, però l'endpoint `advance-phase` segueix exposat (`views.py:161`).
- 🔴 **Asimetria `db_constraint=False`:** `SizeCheckLine.pom` el declara (`models_app/models.py:833`) però `PieceFittingLine.pom`/`GradedSpec.pom`/`POMAlert.pom` NO (`fitting/models.py:346,175,119`), tot i ser idèntic patró cross-schema → PER DECIDIR.
- 🔴 **Deute (b) documentat:** `resolve_size_check` escriu `_motiu` "sense size_check_ref" (`services_size_check.py:183`) — el log F1 no enllaça al SizeCheck origen (a diferència de fitting que té `_fitting_ref`, `:409`).
- 🔴 **Gating asimètric:** `set_piece_gate`/`close` (mutacions fortes que regraduen i versionen) només exigeixen `IsAuthenticated`, mentre `schedule`/`open`/`seal` exigeixen `schedule_fittings`. Un technician (només `execute_tasks`) pot gatejar i tancar peces.

### 🔗 CONNECTA AMB (blast radius: què es trenca si ho toques)

- `BaseMeasurement` (models_app) — `close_piece_fitting` i `resolve_size_check` hi escriuen (origen FITTED/CHECKED). Tocar el contracte de `bm._changed_by`/`_motiu`/`_fitting_ref` trenca el signal F1 (`log_measurement_change`).
- `pom.services.generate_graded_specs` / `update_client_profile` / `_load_grading_rules` — el motor de grading i Welford; canviar la signatura trenca close_piece_fitting i resolve_size_check.
- `tasks` — `advance_phase_gate` (`services_d.py`) és l'ÚNIC amo de `fase_actual` i crida `seal_model_grading`; `resolve_size_check`/`close` finalitzen/reagenden `ModelTask` `size_check` via `transition_task` i `_reagenda_tasca_size_check` (`services_size_check.py:235-298`). `has_delivered_production` (`services_e.py`) bloqueja `fitting.advance_phase`.
- `planning` — `_seal_session` crida `recompute_for_technicians` (`services.py:668`); `_reagenda_tasca_size_check` usa `next_working_slot`/`add_working_minutes` (calendar_service).
- `GarmentSet` — XOR de FittingSession; el segellat multi-peça depèn de `session_can_advance`.
- Frontend FittingDetail / SizeCheckTab — depenen de la forma exacta dels dicts de retorn (`close_piece_fitting`, `resolve_size_check`, `propagar`).

### 🅰️/🅱️ Línia

- Tot el domini Fitting/Size Check és **🅱️ (servei)**: treball facturable sobre models del client (talles, provatures, validació proto).
- **🅰️** només: `FittingDurationStat` (agregat global del tenant, infra de planificació) i la base de capabilities (`accounts/capabilities.py`, `SCHEDULE_FITTINGS`). El gating consumeix plataforma però l'acció és servei → 🅰️🅱️ en els endpoints.

### ⚖️ PER DECIDIR (Agus)

- Gating de `set_piece_gate`/`close`/`resolve_size_check`/`propagar`: ¿han d'exigir `schedule_fittings` (o un `execute_tasks`) en lloc de només `IsAuthenticated`? Avui qualsevol usuari autenticat regradua i versiona.
- Brain stub: ¿s'implementa la propagació stale/reobertura o es retira el hook? Afecta `generated_from_version`, els 3 punts de crida i el discurs de "muscle/brain decoupled".
- `db_constraint=False` a `PieceFittingLine.pom`/`GradedSpec.pom`/`POMAlert.pom`: ¿alinear amb SizeCheckLine? Risc d'integritat cross-schema actual.
- Camps òrfens `SizeFitting.sf_pare`/`fills` i estats `Pendent`/`BaseOberta`: ¿retirar o cablejar?
- `tipus` de SizeFitting: sempre 'SizeSet' hardcoded; ¿les choices Proto/Fit/PP/TOP tenen futur o es retiren? (El test usa 'PRINCIPAL', valor inexistent.)
- `advance_phase` (fitting) buidada i endpoint `advance-phase` exposat: ¿es retira l'endpoint?
- Deute (b): afegir `size_check_ref` al log F1 per traçar l'origen del canvi base CHECKED.

### Obert / dubtós

- No he verificat si el frontend encara crida `fittingSessions.advancePhase`/endpoint `advance-phase` (la funció backend és no-op); a `endpoints.js` no apareix `advancePhase` als rangs llegits, però no he fet grep exhaustiu de tot el frontend per aquest nom concret.
- El gate de peça es descriu com a "tres o quatre" gates a la teva consigna: he trobat **TRES nivells de gate distints** — (1) `PieceFitting.gate` OK/NO_OK/EXCEPCIO (gate de peça, `set_piece_gate`); (2) `session_can_advance` derivat (gate de sessió); (3) `advance_phase_gate`/`GateEvent` a tasks (gate de FASE del model, amo de `fase_actual`). El Size Check (`SizeCheck.estat` Acceptat/Rebutjat/Descartat) funciona com un quart "gate" pre-fitting de la talla base, però és una màquina d'estats pròpia, no el mateix mecanisme. No he pogut confirmar amb certesa si la documentació canònica compta 3 o 4; ho deixo obert.
- No he llegit `tests.py` sencer ni `serializers.py` complet del fitting; els FETS de gating surten de views.py i capabilities.py.

---

## Domini 10 — Import (wizard, 2-call, "document mana", mismatch block)

[x] fet

I have the authoritative model catalog. Now I can complete the analysis. Key verification result: of the model IDs used in this domain's code:
- `claude-opus-4-7` — VALID (active model, extraction_views.py:662, 1153)
- `claude-sonnet-4-6` — VALID (active model, extraction_views.py:1156)
- `claude-opus-4-5` — VALID legacy active alias (NOT used in this domain; the domain uses `claude-opus-4-5` only inside the old `extraction_service.py:81` as `claude-opus-4-5`... let me recheck — it was `MODEL = "claude-opus-4-5"`). Valid alias.
- `thinking={'type':'adaptive'}` and `output_config={'effort':...}` — VALID params on Opus 4.7 (extraction_views.py:1337-1338).

So the AI integration uses valid current IDs and params. The one genuinely stale thing is the old `extraction_service.py` using a raw httpx call against `claude-opus-4-5` with header `anthropic-beta: pdfs-2024-09-25` and `max_tokens: 8192` — that is the OLD path. Now I have everything to write the analysis.

### Entitats i camps
- `ImportSession` (models_app/models.py:385-421) 🅱️ — wizard single-model. Camps: `token` (UUID únic, :394), `creat_per`→UserProfile (:395), `estat` (10 estats INICI→CONFIRMAT/DESCARTAT, :386-392/400), `document` FileField (:402), `model`→Model (:405), i 6 JSONField de resultats per fase: `model_detectat` (:408), `tipologia_confirmada`→GarmentTypeItem (:409), `run_conciliat` (:411), `poms_extrets` (:412), `resultat` (:413), `historia_xat` (:414), `avisos` (:415).
- `BulkCollectionImport` (models_app/models.py:702-730) 🅱️ — staging d'import massiu de col·lecció (multi-model). El prompt l'anomenava `BulkImport (models.py:706)`: el nom real és `BulkCollectionImport` i la classe comença a :702. Camps: `customer`→Customer PROTECT (:713), `document` (:715), `estat` (PUJAT→IMPORTAT/DESCARTAT, :706-712/716), `creat_per`→UserProfile PROTECT (:718), `resum` JSON (:721), `resultat` JSON cache de preview (:722).
- `BulkCollectionRow` (models_app/models.py:733-757) 🅱️ — fila de staging. `importacio`→BulkCollectionImport CASCADE (:742), `row_num` (:744), `raw_data` JSON (:745), `estat` (OK/ERROR/AVIS/DUPLICAT, :736-741/746), `errors` JSON (:747), `model_creat`→Model SET_NULL (:748).
- Constants de pipeline (no DB): `COLUMNS`/`OBLIGATORIES`/`DROPDOWN_COLS` (bulk_import_service.py:15-22), `META_SHEET`/`PLANTILLA_SHEET` (:23-24); `_TEIXIT_FIELDS` (extraction_views.py:1680).

### Relacions / FK (marca cross-schema amb db_constraint=False)
- `ImportSession.model`→`models_app.Model` SET_NULL (:405); `.creat_per`→`accounts.UserProfile` SET_NULL (:395); `.tipologia_confirmada`→`tasks.GarmentTypeItem` SET_NULL (:409).
- `BulkCollectionImport.customer`→`tasks.Customer` PROTECT (:713); `.creat_per`→`accounts.UserProfile` PROTECT (:718).
- `BulkCollectionRow.importacio`→`BulkCollectionImport` CASCADE (:742); `.model_creat`→`models_app.Model` SET_NULL (:748).
- Cap FK del domini porta `db_constraint=False` — totes les referències són intra-schema (tenant). No hi ha cap relació cross-schema declarada aquí.

### Endpoints + gating (qui pot, quina capability/gate)
Tots amb `@permission_classes([IsAuthenticated])` — NO hi ha cap gate de rol/capability més fi en cap endpoint d'aquest domini (només "autenticat"):
- `POST /api/v1/models/extract-from-file/` → `extract_from_file_view` (extraction_views.py:76, urls.py:59) — preview, no crea res.
- `POST /api/v1/models/create-from-extraction/` → `create_from_extraction_view` (:141, urls.py:60) — CAMÍ VELL (crea Model directe, gate Design Freeze a :160).
- Wizard ImportSession (urls.py:62-79): `cribratge/` (:816), `<token>/talles/` (:943), `<token>/extraccio/` (:1282), `<token>/poms/` (:1431), `<token>/grading-preview/` (:1521), `<token>/mesures/` (:1562), `<token>/library-prefill/` (:1599), `<token>/teixit/` (:1684), `<token>/confirmar/` (:1706).
- Bulk (urls.py:132-135): `bulk-import/template/` (bulk_import_views.py:28), `upload/` (:42), `<id>/commit/` (:100), `<id>/errors-report/` (:120).
- Gate de negoci (no de permís): mismatch de Customer al bulk upload bloqueja tot el lot (bulk_import_views.py:71-74); Design Freeze al camí vell (extraction_service.py:189, extraction_views.py:160).

### Frontend que hi penja
- No he pogut llegir el frontend (només tinc Read disponible; Grep/Glob no carregats i Bash prohibit per regles). Els consumidors es dedueixen dels noms d'endpoint i de les claus de resposta (`pot_continuar`, `size_map_prefill`, `suggested_valors_mode`, `grading_status`, `match_log`), però **no puc citar fitxer:línia del frontend** — ho deixo a "Obert/dubtós".

### Màquina d'estats / signals (PROPIETARI ÚNIC de cada estat: qui l'escriu)
- `ImportSession.estat` — propietari únic = els views del wizard, un estat per pas: CRIBRATGE escrit a cribratge (extraction_views.py:866/919), TALLES a talles si ready (:1007), POMS a extracció (:1267/1401), MESURES a poms (:1512), MESURES_OK a mesures (:1593), CONFIRMAT a confirmar (:1983). Cap signal el toca.
- `BulkCollectionImport.estat` — PREVISAT escrit a upload_view (bulk_import_views.py:83); IMPORTAT escrit dins `commit_import` (bulk_import_service.py:474). Cap altre lloc l'escriu.
- `BulkCollectionRow.estat` — escrit només a `validate_rows` (bulk_import_service.py:350) via bulk_create a upload_view (:88).
- Efectes laterals en confirmar (W5, extraction_views.py:1755-1984): crea `BaseMeasurement` (origen='IMPORTED'), `SizeFitting`(tipus='SizeSet', estat='Tancat'), `GradingVersion` v1, `GradedSpec`, deriva `GradingRuleSet`, materialitza regles, crea `ModelFitxer`(categoria='Document'). El bulk commit (bulk_import_service.py:411-477) crea `Model`+`GarmentSet`+`SizeFitting`(tipus='Proto') en bulk (bypassa signals → genera codi_intern manualment via `reserve_sequence_range`, :417).
- El camí vell (create_from_extraction_view) escriu `POMAlert` (origen='IMPORTACIO', :62-70) i pot enviar email a admins (:403-419).

### Serveis d'única entrada reaprofitables
- `find_pom_master(code, description)` (extraction_views.py:1070-1149) — PROPIETARI ÚNIC del matching POM; reusat pel camí vell (:325), per W2 PDF (:1374), W2 Excel (:1244) i library-prefill. 6 estratègies (exact_code, root_code, synonym, nom_client, global, numeric_lining).
- `match_size_system(target, labels, base)` (matching.py:55-125) — únic motor target+run→SizeSystem; reusat per bulk (bulk_import_service.py:270) i per W5 reconciliació (extraction_views.py:1769).
- `safe_json_parse` / `salvage_measurements` (extraction_utils.py:69/126) — parse tolerant únic, reusat per service vell, cribratge, W2, revisió Excel.
- `extract_from_file` (extraction_service.py:129) i `extract_images_from_pdf` (:234) — només els usa el camí VELL.
- `build_extraction_prompt` (extraction_prompt.py:19) + `TECH_SHEET_EXTRACTION_PROMPT` (:86); `preview_graded_specs`, `derive_grading_rule_set`, `deltes_a_absoluts`, `suggest_valors_mode` (de `pom.grading_utils`/`pom.services`) — cridats des del wizard, viuen fora del domini.

### 🔴 VELL/NOU (codi mort viu · dobles camins · òrfenes · documentat-no-implementat)
- **DOBLE CAMÍ d'import single-model (el gros).** Camí VELL = `extract_from_file_view` + `create_from_extraction_view` (extraction_views.py:76-614) amb `extraction_service.py`/`extraction_prompt.py:EXTRACTION_PROMPT`. Camí NOU = wizard ImportSession 2-call (cribratge barat + extracció completa, :816-2001) amb `TECH_SHEET_EXTRACTION_PROMPT`. Tots dos creen Model+BaseMeasurement+SizeFitting+GradingVersion+GradedSpec però amb regles diferents: el vell NO esborra plantilla buida i crea POMs auto amb email a admin; el nou aplica "el document mana" (esborra base_value_cm=None, extraction_views.py:1802) i grading TANCAT. Ambdós rutes segueixen registrades a urls.py:59-60 → **codi vell viu**.
- **`extraction_service.py` és la pila VELLA sencera** i fa servir un client httpx cru (no SDK) contra `MODEL = "claude-opus-4-5"` (extraction_service.py:81) amb `max_tokens:8192` i header `anthropic-beta: pdfs-2024-09-25` (:162). El camí nou usa el SDK `anthropic` amb `claude-opus-4-7`/`claude-sonnet-4-6`, `thinking={'type':'adaptive'}` i `output_config={'effort':'high'}` (extraction_views.py:1337-1338). **Tots els IDs i params del camí NOU són vàlids i actuals** (Opus 4.7 i Sonnet 4.6 són models actius; adaptive thinking i effort són paràmetres GA correctes per a Opus 4.7). El camí VELL apunta a `claude-opus-4-5` (alias legacy encara actiu però antic) via API REST manual → candidat clar a retir.
- **Inconsistència de prompt**: hi ha DOS prompts d'extracció complets — `EXTRACTION_PROMPT` en català dins extraction_service.py:15-77 (camí vell, format `poms`/`grading_table`) i `TECH_SHEET_EXTRACTION_PROMPT` en anglès a extraction_prompt.py:86-234 (camí nou, format `measurements`/`values`). Esquemes JSON divergents → els consumidors no són intercanviables.
- **Claus duplicades intencionades** a `_POM_SYNONYMS` (extraction_views.py:1056-1066): el mateix literal sobreescriu (p.ex. `'waist position'` a :1042 i :1058). Comentari ho marca com volgut (S19, "last wins"), però és fràgil; les entrades de :1042-1055 són codi mort efectiu (mai guanyen).
- **Òrfena potencial**: `ImportSession.historia_xat` (models.py:414) — no he vist cap escriptura ni lectura en cap dels views del domini → camp probablement sense ús (documentat-no-implementat). A confirmar.
- **`extract_images_from_pdf`** (extraction_service.py:234) només es crida des del camí vell (extraction_views.py:425-455); el wizard nou (W5) NO extreu imatges del PDF, només desa el document com a ModelFitxer (:1945-1970) → funcionalitat d'imatges perduda en el camí nou.

### 🔗 CONNECTA AMB (blast radius: què es trenca si ho toques)
- `find_pom_master` (extraction_views.py:1070): el toques i trenques els 4 camins de matching (vell, W2-PDF, W2-Excel, library-prefill) i la creació de POMMaster tenant-only. Depèn de `pom.POMMaster` (codi_client, nom_client, pom_global, actiu).
- `match_size_system` (matching.py): trenca bulk-import i W5-reconciliació; depèn de `pom.SizeSystem`/`SizeDefinition` (targets, actiu, talles, base_unit).
- W5 confirmar (extraction_views.py:1755) toca: `BaseMeasurement`, `SizeFitting`, `GradingVersion`, `GradedSpec`, `ModelFitxer`, i `pom.grading_utils` (derive_grading_rule_set, materialize_model_grading_rules, cerca_canonic_equivalent, grading_rules_match) + `models_app.services.materialize_model_grading_rules`. Canviar formats de `session.resultat` (claus `extraccio`/`mesures`/`teixit`/`valors_mode`) trenca el desament.
- Bulk `commit_import` (bulk_import_service.py:370) depèn de `models_app.services.reserve_sequence_range` i `get_self_customer`, de `Model`/`GarmentSet`/`fitting.SizeFitting`. El camí vell depèn de `models_app.services.get_self_customer` (extraction_views.py:258).
- `BaseMeasurement.nom_fitxa` és el pont entre POMs i grading al camí vell (extraction_views.py:508-509) i s'escriu també al nou (:1816) — canviar-lo trenca el mapeig grading.

### 🅰️/🅱️ Línia
- Tot el domini és 🅱️ (servei sobre models del client: import de fitxes/col·leccions concretes). Toca entitats 🅰️ del catàleg (POMMaster, SizeSystem, GarmentType, Target, Customer) en MODE LECTURA/match, però la feina facturable (crear Models, BaseMeasurements, grading) és 🅱️.
- L'única peça amb regust 🅰️ és el patró 2-call + parse tolerant (infra reaprofitable), però viu acoblat al servei d'import.

### ⚖️ PER DECIDIR (Agus)
- Retirar el camí VELL sencer: `extraction_service.py`, `extraction_prompt.py:EXTRACTION_PROMPT` (no el `TECH_SHEET_...`), `extract_from_file_view` + `create_from_extraction_view` i les 2 rutes urls.py:59-60. És el doble camí més clar; el nou wizard el cobreix amb millor model i principi "el document mana".
- Si es manté el camí vell, migrar-lo a SDK + model actual (avui `claude-opus-4-5` via httpx cru) per coherència amb el nou (`claude-opus-4-7`/`claude-sonnet-4-6`).
- Decidir si `historia_xat` (model.py:414) i les entrades mortes de `_POM_SYNONYMS` (:1042-1055) s'eliminen.
- Decidir si el wizard nou (W5) ha d'extreure imatges del PDF com feia el vell (`extract_images_from_pdf`), o si es perd a propòsit.
- Renom del model `BulkCollectionImport` vs la referència del brief (`BulkImport`): aclarir nomenclatura oficial.

### Obert / dubtós
- **Frontend**: no he pogut localitzar-ne fitxer:línia (sense Grep/Glob/Bash i sense rutes de frontend conegudes). Cal una passada específica a `frontend/` i `frontend-backoffice/` per lligar cada endpoint amb el seu consumidor.
- `ImportSession.historia_xat`: no he trobat cap ús en aquest domini, però podria escriure's des d'un endpoint de xat fora del domini 10 (no verificat).
- Gating fi: he confirmat que tots els endpoints són només `IsAuthenticated`; si hi ha middleware de tenant/rol superior (django-tenants) aplicat globalment, no és visible des d'aquests fitxers.
- No he comprovat si `create_from_extraction_view` (vell) encara es crida des d'algun client viu o si ja és òrfena de fet a nivell de UI (només sé que la ruta existeix).

---

## Domini 11 — Fitxa tècnica (lock TTL30, Konva, timer gap)

[x] fet

Tinc tot el que necessito. El "timer gap" es refereix al forat entre la caducitat del lock al servidor (TTL 30 min) i el fet que el frontend no fa cap heartbeat/refresc del lock mentre s'edita: una sessió d'edició llarga (>30 min sense desar = sense renovar locked_at) queda exposada que un altre la forci. Confirmo això inspeccionant si l'autosave renova el lock (PATCH update no toca locked_at).

El PATCH update (línia 163-165 de tech_sheet_editor_views.py) NO actualitza `locked_at` — només `template_json`, `last_editor`, `updated_at`. Per tant l'autosave NO renova el lock. Aquest és el "timer gap". Ja ho tinc tot.

### Entitats i camps
- `TechSheet` 🅱️ — fitxa persistent d'un Model existent. Camps: `model` (O2O), `estat` (choices obert/tancat, default 'obert'), `versio` (PositiveInteger, default 1), `template_json` (JSONField, format v2 clau `pages`), `locked_by` (FK user), `locked_at` (DateTime), `last_editor` (FK user), `created_at`, `updated_at`. `models_app/tech_sheet_models.py:14-54`.
- `TechSheetTemplate` 🅱️ — plantilla de fitxa per Customer (TS-3); la del Customer `is_self=True` actua de default del tenant. Camps: `customer` (O2O), `nom`, `template_json`, `actiu` (bool, default True), `created_at`, `updated_at`. `models_app/tech_sheet_models.py:57-77`.
- Camps derivats (no a BD) al serializer: `has_content`, `num_pages` calculats des de `template_json['pages']` o `['schemas']`. `models_app/tech_sheet_serializers.py:24-32,46-54`.
- Migracions: `0034_techsheet.py`, `0036_tech_sheet_template.py`. Importat a `models_app/models.py:859` (`from .tech_sheet_models import TechSheet`).

### Relacions / FK (marca cross-schema amb db_constraint=False)
- `TechSheet.model` → `models_app.Model` OneToOne CASCADE (`tech_sheet_models.py:20-24`).
- `TechSheet.locked_by` / `last_editor` → `AUTH_USER_MODEL` SET_NULL (`tech_sheet_models.py:30-44`).
- `TechSheetTemplate.customer` → `tasks.Customer` OneToOne CASCADE (`tech_sheet_models.py:61-65`).
- Cap FK amb `db_constraint=False` en aquest domini — totes intra-schema (User i Customer viuen al schema del tenant, igual que TechSheet). — cap cross-schema —

### Endpoints + gating (qui pot, quina capability/gate)
- `GET models/<model_id>/tech-sheet/` 🅱️ — `IsAuthenticated`. get_or_create + aplica plantilla si nou. `tech_sheet_editor_views.py:72-77`, ruta `urls.py:152`.
- `POST .../tech-sheet/lock/` 🅱️ — `IsAuthenticated`. Adquireix si lliure/meu/stale(>30min); si no, 409. `tech_sheet_editor_views.py:80-110`, `urls.py:153`.
- `POST .../tech-sheet/unlock/` 🅱️ — `IsAuthenticated`; allibera si ets el propietari O tens `CONFIGURE`; si no, 403. `tech_sheet_editor_views.py:113-135`, `urls.py:154`.
- `PATCH .../tech-sheet/update/` 🅱️ — `IsAuthenticated` + **gate per lock**: `sheet.locked_by_id == request.user.id`, si no 403. `tech_sheet_editor_views.py:138-166`, `urls.py:155`.
- `GET customers/<id>/tech-sheet-template/` 🅱️ — `IsAuthenticated`, get_or_create. `tech_sheet_editor_views.py:179-183`, `urls.py:157`.
- `PATCH customers/<id>/tech-sheet-template/update/` 🅱️ — gated `CONFIGURE` (403 si no). `tech_sheet_editor_views.py:186-203`, `urls.py:158`.
- (Domini veí, no editor) `POST models/extract-sheet/` i `models/create-from-sheet/` 🅱️ — `IsAuthenticated`, sense gating addicional. `tech_sheet_views.py:51,235`, `urls.py:117-118`.

### Frontend que hi penja
- `pages/TechSheetEditor.jsx` — editor full-screen Konva (motor TS-1..TS-4c). Ruta `/models/:id/fitxa` dins `ProtectedRoute` (`App.jsx:116-120`). Lazy import `App.jsx:30`.
- `pages/TechSheetTemplateEditor.jsx` — editor de plantilla per client. Ruta `/clients/:id/plantilla` (`App.jsx:122-126`); gating visual `canEdit = me.capabilities.includes('configure')` (`TechSheetTemplateEditor.jsx:33`).
- `pages/ModelSheet.jsx:229-287` — `TechSheetTab`: pestanya "Fitxa tècnica" que fa GET tech-sheet i mostra "Crear fitxa" o resum (num_pages/updated_at) → navega a `/models/:id/fitxa`.
- `api/endpoints.js:183-185` — `techSheetTemplate.detail/update`.
- Lock UI a l'editor: estats `'loading'|'owned'|'conflict'|'error'|'readonly'` (`TechSheetEditor.jsx:466`); badge segons estat (`:925-929`); overlay readonly (`:1052-1054`). Entrada en mode edició només amb `?task_id` (des del Kanban).
- Cleanup en desmuntar: transició task→`Paused` + unlock amb `keepalive` (`TechSheetEditor.jsx:554-567`).
- i18n: `tech_sheet.*` i `model_sheet.tab_tech_sheet` a `ca.json/en.json/es.json`.

### Màquina d'estats / signals (PROPIETARI ÚNIC de cada estat: qui l'escriu)
- `TechSheet.locked_by` / `locked_at`: ESCRITS NOMÉS per `TechSheetLockView` (adquirir, `:97-99`) i `TechSheetUnlockView` (alliberar → None, `:132-134`). Propietari únic = subsistema de lock de `tech_sheet_editor_views.py`.
- `TechSheet.template_json` / `last_editor`: ESCRITS NOMÉS per `TechSheetUpdateView` (`:163-165`) — i a la creació, per `_get_sheet` que hi copia la plantilla (`:42-44`).
- `TechSheet.estat` (obert/tancat): camp definit (`tech_sheet_models.py:25`) però **cap vista l'escriu mai** (vegeu VELL/NOU).
- `TechSheet.versio`: default 1, **mai incrementat per cap codi** (vegeu VELL/NOU).
- Caducitat del lock: NO és un signal ni un job; és lazy/cooperativa — es calcula `is_stale` quan algú demana el lock (`:90-94`, `LOCK_TTL=30min` a `:31`).

### Serveis d'única entrada reaprofitables
- `_get_sheet(model_id)` (`tech_sheet_editor_views.py:34-45`) — get_or_create + auto-aplicació de plantilla. Única entrada de totes 4 vistes de l'editor.
- `_resolve_template_json(customer)` (`:48-69`) — resol plantilla del customer → fallback Customer `is_self` → `{}`.
- `_get_template(customer_id)` (`:171-176`) — get_or_create de la plantilla.
- Frontend: `buildHeaderPrimitives`, `buildTablePrimitives`, `serializePages`, `renderPageToDataURL`, constants `MM_TO_PX/CANVAS_*/PAGE_FORMATS` — exportats des de `TechSheetEditor.jsx` i reutilitzats per `TechSheetTemplateEditor.jsx` (font única, evita drift canvas↔PDF).

### 🔴 VELL/NOU (codi mort viu · dobles camins · òrfenes · documentat-no-implementat)
- **Òrfena — `TechSheet.estat`**: el camp i ESTAT_CHOICES (obert/tancat) existeixen (`tech_sheet_models.py:15-25`) i s'exposen al serializer (`tech_sheet_serializers.py:17`), però CAP vista ni frontend els escriu ni els llegeix per decidir res. Estat documentat-no-implementat.
- **Òrfena — `TechSheet.versio`**: default 1, es pinta a la capçalera (`buildHeaderPrimitives`, `TechSheetEditor.jsx:202,208`) però **mai s'incrementa** en desar. El versionat de fitxa està insinuat però no implementat.
- **🔴 "Timer gap" (forat de temporitzador)**: el lock caduca a 30 min mesurats des de `locked_at`, però `TechSheetUpdateView` (autosave) NO actualitza `locked_at` — només `template_json/last_editor/updated_at` (`tech_sheet_editor_views.py:163-165`). El frontend tampoc fa heartbeat/re-lock (l'autosave només toca `/update/`, `TechSheetEditor.jsx:618-627`). Conseqüència: una sessió d'edició contínua de més de 30 min queda "stale" i un altre usuari pot **forçar el lock** (`is_stale`, `:90-96`) mentre el primer encara hi treballa → possible col·lisió/pèrdua silenciosa. No hi ha renovació de lock enlloc.
- **Comentari stale al frontend** (`TechSheetEditor.jsx:537-539`): diu que "el TechSheetSerializer actual NO exposa `template_json`" i que hydrate cau a pàgina buida en mode consulta. Però el serializer SÍ l'exposa (`tech_sheet_serializers.py:17`). El comentari (i la lògica forward-compat de `hydrate`) està desfasat respecte al codi actual; funcionalment hydrate ja rep `template_json` en mode consulta.
- **Doble camí de format de pàgina (parcial)**: `template_json` desa `pageFormat` a nivell de document (`TechSheetEditor.jsx:580,623`), però `TechSheetTemplateEditor` (plantilla) desa sense `pageFormat` (`TechSheetTemplateEditor.jsx:107`). Plantilla i fitxa no comparteixen el camp de format → una plantilla A3 no propaga el format en crear la fitxa.
- **Dos subsistemes "tech sheet" coexistents** (no és bug, però convé marcar-ho): `tech_sheet_views.py` (S17, extracció IA per CREAR un Model) vs `tech_sheet_editor_views.py` (editor persistent d'un Model existent). Comparteixen prefix de nom i poden confondre's; ho avisen els propis docstrings (`tech_sheet_models.py:7-8`, `tech_sheet_editor_views.py:3`).
- **Serializer `template_json` legacy clau `schemas`**: `get_has_content/num_pages` accepten `pages` O `schemas` (`tech_sheet_serializers.py:26,31,48,53`). `schemas` és el format pdfme antic; el motor Konva nou només escriu `pages` v2 (`TechSheetEditor.jsx:575`). El branch `schemas` és compat de dades velles (potencialment mort si no queden fitxes amb format antic — segons ESTAT_PROJECTE.md:444 a staging hi ha 0 fitxes amb format problemàtic).

### 🔗 CONNECTA AMB (blast radius: què es trenca si ho toques)
- `models_app.Model` (O2O CASCADE): esborrar un Model esborra la seva TechSheet. La fitxa llegeix `model.customer` per resoldre plantilla (`:41,300`) i el frontend llegeix camps de Model per a la capçalera (codi_intern, nom_prenda, customer_nom, customer_logo, garment_type_item_nom, size_system_nom, responsable_nom — `buildHeaderPrimitives` + `ObjectNode`).
- `tasks.Customer` (O2O CASCADE + `is_self`): la resolució de plantilla depèn d'un únic Customer `is_self=True`; si n'hi ha 0 o més d'1, el fallback cau silenciosament a `{}` (`:66-68`).
- `fhort.accounts.capabilities` (`CONFIGURE`, `get_capabilities`): governen unlock-override i edició de plantilla (`:24,121,190`). Tocar les capabilities afecta qui pot forçar locks i editar plantilles.
- Editor depèn d'endpoints d'altres dominis: `models/<id>/`, `model-fitxers/`, `size-fittings/?model=`, `fitting/<sf>/graded-table/`, `model-task-items/<task>/transition/` (`TechSheetEditor.jsx:518-565,601`). El bloc de taula graduada es regenera des de `size_fitting_id` via l'endpoint de fitting → trencar `graded-table` deixa les taules en placeholder "Sense grading actiu".
- Frontend comparteix helpers exportats entre els dos editors: canviar `buildTablePrimitives/buildHeaderPrimitives/serializePages/renderPageToDataURL` afecta editor de fitxa, editor de plantilla, export PDF i miniatures alhora.

### 🅰️/🅱️ Línia
- Tot el domini és 🅱️ (servei sobre models del client): TechSheet/TechSheetTemplate, les 6 vistes, els dos editors frontend. Treball facturable per model/client.
- L'únic component reutilitzable transversalment és el **patró de lock cooperatiu amb TTL 30 + force-if-stale + override per `configure`** (MAPA_SISTEMA.md:415 el marca "reutilitzable per qualsevol recurs d'edició col·laborativa") — vocació 🅰️ però implementació actual acoblada a TechSheet (no extret a servei comú).

### ⚖️ PER DECIDIR (Agus)
- Tancar el "timer gap": ¿l'autosave (`/update/`) ha de renovar `locked_at`? ¿O cal un endpoint heartbeat / re-lock al frontend? Tal com està, editar >30 min sense interrupció exposa a force-unlock d'un tercer.
- `TechSheet.estat` i `TechSheet.versio`: ¿s'implementen (workflow obert/tancat, increment de versió en desar) o s'eliminen com a camps morts?
- Unifició conceptual dels dos "tech sheet" (S17 extracció IA vs editor): ¿renombrar un dels dos per evitar confusió permanent?
- Format de pàgina a la plantilla: ¿la plantilla ha de desar/propagar `pageFormat` perquè la fitxa creada n'hereti el format?
- Branch legacy `schemas` al serializer: ¿es pot eliminar (migrar/confirmar 0 fitxes antigues) o es manté per compat?

### Obert / dubtós
- No he pogut confirmar amb certesa si encara existeixen fitxes amb el format pdfme antic (`schemas`) en producció; ESTAT_PROJECTE.md:444 suggereix que a staging està net, però és estat de dades, no codi (READ-ONLY, no consulto BD).
- No he verificat si algun job/cron extern toca `TechSheet` fora d'aquestes vistes; el grep de `tech_sheet`/`TechSheet` només dona els fitxers del domini, `models.py` (import) i docs — no n'he trobat cap escriptor addicional, però no he fet un grep exhaustiu de tota la base backend per cada nom de camp individual.
- El comportament exacte de la transició `model-task-items/<task>/transition/` a `Paused` en sortir de l'editor pertany al domini tasks; aquí només consta la crida (`TechSheetEditor.jsx:557-561`).

---

## Domini 12 — Size systems

[x] fet

Confirmed. The create view writes BOTH the legacy `target` FK (lines 572, 580) and the new `targets` M2M (line 583). I have all the facts needed.

### Entitats i camps
- `SizeSystem` 🅰️🅱️ — `pom/models.py:272-318`. Camps: `codi` (unique), `nom`, `descripcio`, `actiu`, `targets` (M2M), `base_unit` (choices ALPHA/NUMERIC_EU/NUMERIC_US/CM_HEIGHT/MONTHS/AGE_YEARS, `:285-296`), `norma_ref` (`:297`), `parent` (self-FK derivació client, `:302`), `customer_codi` (`:308`). És app SHARED (taula a `public` i a cada tenant).
- `SizeDefinition` 🅰️🅱️ — `pom/models.py:321-352`. Camps: `size_system` (FK), `etiqueta`, `ordre`, `valor_numeric`, mesures corporals de referència ISO (`body_height_cm`/`body_bust_cm`/`body_waist_cm`/`body_hip_cm` `:330-339`), `age_months_min`/`age_months_max` (`:340-342`). `unique_together=('size_system','etiqueta')` (`:349`).
- `GradingRuleSet` 🅱️ — `pom/models.py:486-544`. Conté `size_system` (FK PROTECT nullable, `:495`), `garment_group`, `targets` (M2M), `target` (FK legacy), `construction`, `fit_type`, `is_system_default`, `parent_version`, `version_number`, `codi_sistema`.
- `SizingProfile` 🅱️ — `pom/models.py:786-819`. Combinació target+garment_type+construction+fit_type → `size_system` + `grading_rule_set`. `unique_together=('size_system','target','construction','fit_type')` (per migració `0019`).
- `GarmentTypeItem.base_size_definition` + `.grading_rule_set` 🅱️ — `tasks/models.py:367-384`. Talla base de la plantilla de l'Item + context de grading (un sol ruleset).
- `Model.size_system` / `Model.grading_rule_set` / `Model.base_size_label` / `Model.size_run_model` 🅱️ — `models_app/models.py:186-199, 264-271`. La config de talles a nivell de model concret.
- `GarmentType.targets_recomanats` (M2M) 🅱️ — `pom/models.py:393` (consumit a `s2_views.py:350`).

### Relacions / FK (marca cross-schema amb db_constraint=False)
- `SizeDefinition.size_system` → `SizeSystem` CASCADE (`pom/models.py:322`).
- `GradingRuleSet.size_system` → `SizeSystem` PROTECT nullable (`pom/models.py:495`).
- `GradingRule.talla_base` → `SizeDefinition` PROTECT (`pom/models.py:563`); `GradingRule.rule_set` → `GradingRuleSet` CASCADE.
- `SizingProfile.size_system`/`grading_rule_set` → PROTECT (`pom/models.py:799-802`).
- `Model.size_system` → `SizeSystem` SET_NULL (`models_app/models.py:186-192`); `Model.grading_rule_set` → SET_NULL (`:193-199`).
- `GarmentTypeItem.base_size_definition` → `pom.SizeDefinition` SET_NULL — **FK NORMAL amb constraint real** (cross-app tasks→pom, però pom viu al schema del tenant) (`tasks/models.py:367-371`).
- `GarmentTypeItem.grading_rule_set` → `pom.GradingRuleSet` PROTECT — **constraint real** (`tasks/models.py:380-384`).
- `SizeSystem.parent` → self SET_NULL (derivació per client) (`pom/models.py:302`).
- **db_constraint=False (cross-schema)**: NO afecten directament SizeSystem/SizeDefinition; sí els models germans `GarmentPOMMap.garment_type_item` (`pom/models.py:421-423`) i `ItemBaseMeasurement.garment_type_item` (`pom/models.py:460-461`) cap a `tasks` (tenant-only).

### Endpoints + gating (qui pot, quina capability/gate)
- Router DRF a `pom/urls.py:20-25`: `size-systems`, `size-definitions`, `grading-rule-sets`, `grading-rules`.
- `SizeSystemViewSet` 🅰️🅱️ (`pom/views.py:56-77`): lectura `IsAuthenticated`; escriptura (create/update/partial_update/destroy) gated `_ConfigureWrite` (capability `CONFIGURE`, `views.py:38-42, 65-68`). `destroy` bloqueja si té talles (`:70-77`).
- `SizeDefinitionViewSet` (`pom/views.py:80-91`): mateix patró, escriptura `CONFIGURE`.
- `GradingRuleSetViewSet` (`pom/views.py:139-155`) i `GradingRuleViewSet` (`:199-212`): lectura autenticada, escriptura `CONFIGURE`.
- Wizard Size Map (function views, **tots gated `CONFIGURE`** via `@permission_classes([_Configure])`, `size_map_views.py:22`): `size-map/lookups|match|preview|grading-preview|grading-preview-file|create|systems/` (`urls.py:59-67`). `size_map_create_view` (`:431-433`) materialitza SizeSystem+GradingRuleSet+GradingRule+SizingProfile en `transaction.atomic`.
- `GarmentTypeItemViewSet` (write base_size_definition/grading_rule_set) a `tasks/views_b.py:659`.

### Frontend que hi penja
- `frontend/src/api/endpoints.js:77-120`: `sizeSystems`, `sizeDefinitions`, `sizeMap.*`, `gradingRuleSets.*`.
- `pages/SizeMapSetup.jsx` — wizard complet (match→preview→grading→create), backend gated CONFIGURE (comentat `:14`).
- `pages/SizeLibrary.jsx`, `pages/GradingRuleSets.jsx`, `pages/GarmentTypes.jsx`.
- `pages/ItemAuthoring.jsx:93-155` — escriu `grading_rule_set` i `base_size_definition` de l'Item; lògica d'incompatibilitat client-side (`:134-135`: si canvia ruleset i el size_system difereix, posa `base_size_definition=null`).
- Components: `SizeSystem/SizeSystemDrawer.jsx`, `SizeSetCard.jsx`, `SizeSetDetail.jsx`, `grading/RuleSetPicker.jsx`, `model/SizeCheckTab.jsx`, `model/BaseStageTable.jsx`.

### Màquina d'estats / signals (PROPIETARI ÚNIC de cada estat: qui l'escriu)
- No hi ha màquina d'estats pròpia del domini talles (`SizeSystem.actiu`/`SizeDefinition` no tenen workflow de transicions).
- Propietaris d'escriptura de `SizeSystem`/`SizeDefinition`/`GradingRuleSet`/`SizingProfile`:
  - Via API CRUD: els ViewSets (`pom/views.py`), gated CONFIGURE.
  - Via wizard: `size_map_create_view` (`size_map_views.py:431-583`) — **únic camí que crea SizeSystem derivat (parent/customer_codi) + ruleset + profile alhora**.
  - Via seed/reseed (management commands): `reseed_size_definitions.py`, `seed_commercial_size_runs.py`, `seed_baby_months_*`, `reseed_tenant_fhort.py`.
- `models_app/signals.py:87` — en duplicar un Model, els camps de config (`size_system`, etc.) NO es dupliquen (comentari explícit).

### Serveis d'única entrada reaprofitables
- `match_size_system(target_codi, labels, base_size)` — `models_app/matching.py:55-125`. **Únic motor** de matching run+target→SizeSystem (score per intersecció d'etiquetes, desempat per `base_unit` inferit, validació base_size al run). Reutilitzat per `size_map_views.py:116` (wizard match) i `bulk_import_service.py:204,270` (import de models). Retorna `MatchResult` amb classificació perfecte/parcial/error.
- `_unique_size_system_code()` (`size_map_views.py:25`), `_customer_label()` (`:44`), `derive_break_fields` de `grading_utils.py` (`:445`).

### 🔴 VELL/NOU (codi mort viu · dobles camins · òrfenes · documentat-no-implementat)
- **Camp mort (òrfena de model, viu a migració vella)**: `Model.talla_base` (FK SizeDefinition) va ser **eliminat** a `models_app/migrations/0018_remove_model_talla_base.py`. La migració `0003_alter_model_size_system_alter_model_talla_base.py:20-24` encara el referencia (és anterior). El model viu ja NO el té; el substitut és `base_size_label` (CharField, `models_app/models.py:268`). Cap codi viu llegeix `Model.talla_base`. (Nota: `GradingRule.talla_base` a `s2_views.py:186` és un model DIFERENT i és viu; no confondre.)
- **Doble camí target a GradingRuleSet (migració documentada, no completada)**: `target` (FK legacy, `pom/models.py:504-508`, related_name `*_legacy`) coexisteix amb `targets` (M2M, `:509-515`). El comentari `:501-503` diu que la FK és temporal i s'eliminarà "once the consuming code is updated". Però `size_map_create_view` encara **escriu LES DUES** (`size_map_views.py:572-573, 580` FK; `:583` M2M), i `s8_views.py:125` encara LLEGEIX la FK (`profile.target`). Doble camí actiu, no migrat del tot.
- **Doble camí target a SizeSystem (ja resolt)**: `SizeSystem.target` (FK) ja es va migrar a `targets` (M2M) i la FK **eliminada** a `migrations/0021`. Aquí el matching ja usa només M2M (`matching.py:71` `targets__codi`). Aquest és el patró net; GradingRuleSet encara no hi ha arribat.
- **Possible doble font de "context de grading per Item"**: `SizingProfile` (target+garment+construction+fit→size_system+ruleset, `pom/models.py:786`) vs el nou `GarmentTypeItem.grading_rule_set`/`base_size_definition` (`tasks/models.py:380`). SizingProfile encara es crea/llegeix al wizard i s2/s8 views; el model nou (DISSENY_MODEL_VIU) ancora el grading a l'Item. ⚠️ Convé confirmar si SizingProfile és el "vell" que el GarmentTypeItem.grading_rule_set substitueix.
- **NOT NULL pendent (documentat-no-implementat)**: `GarmentTypeItem.grading_rule_set` és nullable "de moment"; el comentari (`tasks/models.py:374-376`) promet una 2a migració post-Fase B que el farà NOT NULL. No existeix encara.

### 🔗 CONNECTA AMB (blast radius: què es trenca si ho toques)
- Tocar `SizeSystem`/`SizeDefinition` afecta: grading (`GradingRule.talla_base`, `GradingRuleSet.size_system`), `SizingProfile`, `Model.size_system`, `GarmentTypeItem.base_size_definition`, el motor `match_size_system` (matching i bulk import de models), i el wizard SizeMap.
- `match_size_system` és consumit per import de models (`bulk_import_service.py`) i pel wizard — canviar-ne la signatura/score trenca dos fluxos.
- `GarmentTypeItem.clean()` (`tasks/models.py:392-404`) imposa `base_size_definition.size_system == grading_rule_set.size_system`; re-executat al serializer (`serializers_b.py:90-104`) i replicat al frontend (`ItemAuthoring.jsx:134`). Tres llocs amb la mateixa regla → canviar-la requereix tocar els tres.
- `on_delete`: esborrar un `SizeSystem` CASCADEja les seves `SizeDefinition`; esborrar `GradingRuleSet` referenciat per un Item el **bloqueja** (PROTECT, `tasks/models.py:381`); esborrar una `SizeDefinition` referenciada per `GradingRule` el bloqueja (PROTECT, `:563`).

### 🅰️/🅱️ Línia
- `SizeSystem`/`SizeDefinition`: 🅰️🅱️ — model genèric multi-tenant (taula a public + tenant, seeds estàndard ISO `is_system_default`), però el contingut concret (sistemes derivats per client amb `parent`/`customer_codi`) és 🅱️.
- `GradingRuleSet`/`GradingRule`/`SizingProfile`/`GarmentTypeItem.*`/`Model.*`: 🅱️ — treball facturable sobre dades del client.
- Gating: capability `CONFIGURE` (`accounts/capabilities.py:10`) — rol de configuració de plataforma 🅰️.

### ⚖️ PER DECIDIR (Agus)
- `GradingRuleSet.target` (FK legacy): completar la migració a `targets` M2M (deixar d'escriure'l a `size_map_views.py:572-573,580` i de llegir-lo a `s8_views.py:125`) i eliminar la FK — replicant el que ja es va fer per `SizeSystem` a la migració 0021.
- `SizingProfile` vs `GarmentTypeItem.grading_rule_set`: decidir si SizingProfile és el camí VELL a deprecar (el grading nou s'ancora a l'Item) o si conviuen amb rols diferents. Avui els dos s'escriuen.
- `GarmentTypeItem.grading_rule_set` NOT NULL: la 2a migració promesa (`tasks/models.py:374-376`) està pendent; decidir quan tots els items tinguin ruleset.

### Obert / dubtós
- No he traçat si `SizeSystem.norma_ref` i `SizeSystem.descripcio` es mostren/escriuen en algun lloc del frontend (no apareixen als greps de pages); poden ser camps documentals sense ús de UI.
- No he confirmat si `SizingProfile` es LLEGEIX en algun flux de runtime crític (fitting/grading real) o només al wizard i exports s8; caldria seguir els consumidors a `s4_views.py`/`s2_serializers.py` per dictaminar si és viu o residual.
- No he verificat si els `GradingRuleHistory`/`GradingException` interactuen amb el size_system del ruleset més enllà de l'FK; fora del nucli del domini 12 però adjacents.

---

## Domini 13 — Backoffice / facturació

[x] fet

Tinc prou material. El backoffice es munta a `urls_public.py:35` (només schema public). El comptador té dos camins d'escriptura (hot path a services_c.py i backfill al command). Tinc tot el necessari per a l'informe.

### Entitats i camps
- `ModelConsumptionEvent` 🅰️🅱️ — `backoffice/models.py:63`. Camps: `codi_client` (CharField 3, ref fluixa a `Client.codi_tenant`), `period` ('YYYY-MM'), `opaque_ref` (UUIDField unique, **sense default** — el valor ve del tenant), `merited_at`. És el recompte que FHORT factura: total = `COUNT()` per `{codi_client, period}`. Mínim absolut: cap codi ni nom de model.
- `ServiceCatalog` 🅰️ — `backoffice/models.py:80`. `code` (unique), `nom`, `descripcio`, `tipus` (`tier_fee`/`model_count`/`manual`), `actiu`, `created_at`. Sense preu (el preu viu a `ContractLine`).
- `TenantContract` 🅰️🅱️ — `backoffice/models.py:103`. FK `client`→`tenants.Client` (PROTECT), `data_inici`, `data_fi` (null=vigent), `actiu`, `nota`, `created_at`. Múltiples per tenant (historial).
- `ContractLine` 🅱️ — `backoffice/models.py:124`. FK `contract` (CASCADE) + FK `service` (PROTECT), `preu` (Decimal 10,4), `moneda`, `inclosos` (franquícia), `actiu`. `unique_together(contract, service)`.
- `Invoice` 🅰️🅱️ — `backoffice/models.py:147`. FK `client`→`tenants.Client` (PROTECT), `period`, `tipus` (auto/manual), `estat` (esborrany/emesa/pagada/cancel·lada), `total`, `moneda`, `created_at`, `emesa_at`, `nota`. `UniqueConstraint(client, period, tipus)` condicional a `tipus='auto'` (`models.py:174-180`).
- `InvoiceLine` 🅱️ — `backoffice/models.py:186`. FK `invoice` (CASCADE) + FK `service` (PROTECT, null per a línies manuals), `descripcio`, `quantitat`, `preu_unit`, `total`, `moneda`.
- `BackofficeUser` 🅰️ — `backoffice/models.py:9`. O2O `usuari`→`AUTH_USER_MODEL` (PROTECT), `rol` (ADMIN/COMERCIAL/FACTURACIO/SUPORT), `actiu`, `data_alta`, `ultim_acces`. RBAC pròpia del personal FHORT.
- `BackofficeActionLog` 🅰️ — `backoffice/models.py:37`. FK `usuari`→`BackofficeUser` (SET_NULL), `accio`, `objecte_tipus`, `objecte_id`, `detall` (JSON), `timestamp`. **Definit però veure VELL/NOU** (cap escriptura).

### Relacions / FK (marca cross-schema amb db_constraint=False)
- `TenantContract.client` → `tenants.Client` (PROTECT) — `backoffice/models.py:108`. **Mateix schema (public): tant `tenants` com `backoffice` són SHARED_APPS** (`settings.py:36-58`), per això és una FK dura normal i no porta `db_constraint=False`.
- `Invoice.client` → `tenants.Client` (PROTECT) — `backoffice/models.py:160`. Igual: public↔public, FK dura.
- `ContractLine.contract`→`TenantContract` (CASCADE) i `ContractLine.service`→`ServiceCatalog` (PROTECT) — `models.py:128,131`.
- `InvoiceLine.invoice`→`Invoice` (CASCADE) i `InvoiceLine.service`→`ServiceCatalog` (PROTECT, null) — `models.py:189,192`.
- `ModelConsumptionEvent` → **NO té cap FK**: la unió amb el tenant és una *referència fluixa per valor* (`codi_client` = `Client.codi_tenant`, `opaque_ref` = mateix UUID que el `ConsumptionRecord` del tenant). És l'aïllament cross-schema real (event a public, l'albarà a tenant). `backoffice/models.py:68-70`.

### Endpoints + gating (qui pot, quina capability/gate)
Muntats sota `api/backoffice/v1/` a `urls_public.py:35` (només schema public; mai apps de tenant — `urls_public.py:4-6`).
- `POST facturacio/generar/` → `generate_invoice_view` 🅰️🅱️ — `views_contracts.py:48-74`, ruta a `urls.py:21`. Gate: `IsAuthenticated` + `HasBackofficeRole()` (qualsevol BackofficeUser actiu). Body `{codi_client, period, dry_run}`.
- `serveis/` (ServiceCatalogViewSet) — `views_contracts.py:18`. Gate: lectura = qualsevol BackofficeUser actiu; escriptura (`create/update/partial_update/destroy`) = **rol ADMIN** (`views_contracts.py:15,23-25`).
- `contractes/` (TenantContractViewSet) — `views_contracts.py:28`. Mateix patró ADMIN per escriptura (`views_contracts.py:32-34`).
- `auth/login/`, `auth/me/`, `health/` — `urls.py:18-20`, `views.py`. `health` és AllowAny (`views.py:16`).
- Gating implementat a la fàbrica `HasBackofficeRole(roles=...)` — `views.py:58-81`: comprova `request.user.backoffice_profile`, `actiu=True` i `rol in roles`.
- **No hi ha cap endpoint per a `Invoice`/`InvoiceLine`** (ni viewset ni serializer) ni per a `ModelConsumptionEvent`.

### Frontend que hi penja
- `frontend-backoffice` (app separada del backoffice FHORT). Base `/api/backoffice/v1` a `frontend-backoffice/src/api/contracts.js:5-16` (serveis + contractes CRUD) i `tenants.js:5-34`.
- Pàgines: `ServeisPage.jsx`, `ContractesPage.jsx`, `ContractFormPage.jsx`, `ContractDetailPage.jsx`, `TenantsPage/DetailPage/FormPage` (`App.jsx:22-31`). Sidebar a `Sidebar.jsx:31-33`.
- **Cap consum de `facturacio/generar/`**: `grep` de `generar/invoice/factura` al frontend-backoffice no troba cap crida (només `email_facturacio` com a camp de tenant). El motor de facturació no té UI.
- El **frontend de tenant** (`frontend/`) no referencia res d'aquest domini (cap match de `ModelConsumptionEvent`/`Invoice`/`billing`/`facturacio`).
- Albarà de consum vist pel client viu a l'altre costat (tenant): `models_app/views.py:1424` `consumption_delivery_view` i `:1739` llista de `ConsumptionRecord` — NO és backoffice, és la cara tenant del mateix fet.

### Màquina d'estats / signals (PROPIETARI ÚNIC de cada estat: qui l'escriu)
- Signal `model_consumption_started` definit a `tasks/signals.py:17` (domini 3/tasks). Payload: `codi_client, period, opaque_ref, merited_at`.
- **Emissors (2 camins):**
  1. Hot path: `tasks/services_c.py:108` — en arrencar la PRIMERA tasca (`to_status='InProgress'`), dins bloc try aïllat no-fatal (`services_c.py:94-119`): escriu `Model.consumption_started_at` (guard idempotent via `.update(...__isnull=True)`, `:96-98`), crea `ConsumptionRecord` (tenant) i `.send()` del signal.
  2. Backfill: `reconcile_consumption.py:140` — reconstrueix forats N10 amb `merited_at = MIN(TaskTransition→InProgress)` (`:83-87`), mateixa triple escriptura atòmica.
- **Receiver únic** (propietari de `ModelConsumptionEvent`): `on_model_consumption_started` a `backoffice/receivers.py:7`. Fa `schema_context('public')` + `get_or_create(opaque_ref=...)` → **idempotència per `opaque_ref` unique** (`receivers.py:10-18`). Registrat a `apps.py:8`.
- Propietari de `Invoice.estat`: només `billing_service.py:111` crea amb `estat='esborrany'`. Cap codi mou esborrany→emesa→pagada (veure VELL/NOU; comentaris "Sprint 7 ho farà" a `models.py:152`).
- Propietari de `Model.consumption_started_at` (marca de meritació, tenant): `services_c.py:98` i `reconcile_consumption.py:118` — sempre via `.update(...__isnull=True)` (guard de cursa).

### Serveis d'única entrada reaprofitables
- `generate_invoice(codi_client, period, dry_run)` — `billing_service.py:36`. Única entrada per generar factura auto. Idempotent (`:50-55`), busca contracte vigent (`_get_active_contract`, `:18-33`), recompta `ModelConsumptionEvent.count()` (`:63-65`), aplica franquícia (`exces = max(0, n_models - cl.inclosos)`, `:80`), salta línies `manual` (D1, `:73`), persisteix dins `transaction.atomic()` (`:109-115`).
- Receiver `on_model_consumption_started` — `receivers.py:7`: única porta d'escriptura de `ModelConsumptionEvent` (pur, no llegeix res del tenant).
- Comando `reconcile_consumption` — única entrada de backfill idempotent (`reconcile_consumption.py:28`).
- `HasBackofficeRole(roles=...)` — `views.py:58`: fàbrica de permisos reusable a tot el backoffice.

### 🔴 VELL/NOU (codi mort viu · dobles camins · òrfenes · documentat-no-implementat)
- **Documentat-no-implementat (Invoice lifecycle):** `Invoice`/`InvoiceLine` existeixen com a model + migració `0004_invoice_and_lines.py` + `billing_service.py`, però **no hi ha serializer, ni viewset, ni endpoint de consulta/llistat, ni UI**. Es generen via `facturacio/generar/` però després ningú les llegeix per API. Els estats `emesa/pagada/cancel·lada` i `emesa_at`/`Stripe` són TODO declarat ("Sprint 7", `models.py:152,158`). Camp `Invoice.nota` i `InvoiceLine` manuals sense via de creació manual (només `tipus='auto'` es genera; `manual` documentat però cap codi el crea).
- **`facturacio/generar/` sense UI (camí mort viu de cara a l'usuari):** endpoint funcional però cap crida al frontend-backoffice → només invocable per curl/test. El motor està fet, la integració no.
- **`BackofficeActionLog` òrfena:** model definit a `models.py:37` per a auditoria, però `grep` no troba **cap escriptura** (`.objects.create`/`save`) enlloc del codi. Capa 8 documentada, no cablejada.
- **`tasks/signals.py` (capçalera enganyosa):** el docstring (`signals.py:1-11`) parla de signals "retirats a Sprint 0"; l'únic signal viu del fitxer és precisament `model_consumption_started`. No és bug, però el comentari pot despistar.
- **Possible doble camí de preu:** comentari a `models.py:106-107` i `tenants/models.py:45-47` diuen que el motor llegeix `ContractLine.preu` i **NO** `Plan.preu_model_extra`. Confirmat: `billing_service.py:71-83` llegeix `cl.preu`. `Plan.preu_model_extra` queda com a camp legacy no usat pel motor (vell que conviu amb el nou ContractLine).
- **`_get_active_contract` retorna només `.first()`** (`billing_service.py:33`): si hi ha 2+ contractes vigents solapats, n'agafa un silenciosament (per `-data_inici`). No és error però és una decisió implícita no validada.

### 🔗 CONNECTA AMB (blast radius: què es trenca si ho toques)
- **Domini 3 (tasks):** `services_c.py:86-119` és l'origen del comptador. Si canvies el payload del signal o el nom `model_consumption_started`, trenques `receivers.py:8` i `reconcile_consumption.py:140`. La meritació és **no-fatal per disseny** (`services_c.py:115-119`): un error aquí no bloqueja la transició del tècnic, però deixa forat que el command reconcilia.
- **`opaque_ref` és el pont d'idempotència cross-schema:** el `ConsumptionRecord.opaque_ref` (tenant, `models_app/models.py:770`) ha de ser el MATEIX UUID que `ModelConsumptionEvent.opaque_ref` (public). A `services_c.py:112` es passa `record.opaque_ref`; al command `:130-145` es genera `ref=uuid4()` i s'usa per als dos. Si es trenca aquesta igualtat, es duplica facturació o es perd la traça.
- **`codi_client` = `Client.codi_tenant` = `Customer.codi`:** a `services_c.py:110` s'envia `model.customer.codi`; al command `:101` `model.customer.codi or tenant.codi_tenant`. `Model.codi` és camp DEPRECAT (còpia de `customer.codi`, `models_app/models.py:133-134`). El recompte de `generate_invoice` (`billing_service.py:63`) filtra per `codi_client` literal → si `customer.codi` i `Client.codi_tenant` divergeixen, la factura no quadra amb el recompte.
- **Tenant Client (domini 1/tenants):** `Invoice` i `TenantContract` tenen FK PROTECT a `Client`; no es pot esborrar un Client amb contractes/factures.
- **Frontend-backoffice:** depèn de l'esquema JSON de `serveis/` i `contractes/` (serializers a `serializers_contracts.py`). Canviar camps trenca `ServeisPage`/`Contract*Page`.

### 🅰️/🅱️ Línia
- **Infra 🅰️:** `BackofficeUser`, `BackofficeActionLog`, `ServiceCatalog`, RBAC `HasBackofficeRole`, auth/health del backoffice. Plataforma SaaS, no facturable al client final.
- **Servei/facturable 🅱️:** `ContractLine`, `InvoiceLine` (el preu i el consum concret per tenant), el camí del comptador `ModelConsumptionEvent` (recompte del treball real sobre models).
- **Ambdós 🅰️🅱️:** `TenantContract`, `Invoice`, `generate_invoice`, `ModelConsumptionEvent` (estructura de plataforma que custodia el fet facturable del servei).

### ⚖️ PER DECIDIR (Agus)
- Tancar el cicle d'Invoice o no: ¿s'implementa el lifecycle `esborrany→emesa→pagada` + Stripe (Sprint 7 declarat a `models.py:152`) o es deixa el motor com a càlcul intern? Avui genera factures que ningú llegeix per API.
- `BackofficeActionLog`: cablejar-lo (auditoria real) o eliminar-lo com a òrfena.
- `Plan.preu_model_extra` (`tenants/models.py:47`): confirmar que és legacy mort i marcar/eliminar, ja que el motor només usa `ContractLine.preu`.
- Línies `manual` del catàleg: el motor les salta (`billing_service.py:73`) i no hi ha via de creació de factura/línia manual. ¿Cal endpoint de facturació manual o es descarta el `tipus='manual'`?
- Contractes vigents solapats: ¿validar unicitat de vigència o acceptar el `.first()` silenciós (`billing_service.py:33`)?

### Obert / dubtós
- No he pogut confirmar si existeix algun **cron/scheduler** que cridi `generate_invoice`/`facturacio/generar/` mensualment (no he trobat task periòdica al backoffice; caldria mirar configuració de cron/Celery fora d'aquesta app per descartar-ho).
- No he verificat el contingut de `serializers_contracts.py` línia a línia (camps exactes exposats de contractes/serveis); l'he inferit per l'ús a views i frontend.
- `ModelConsumptionEvent` es crea via `get_or_create` en context public; no he comprovat si hi ha algun camí que l'esborri (rollback de meritació) — aparentment no n'hi ha cap (només escriptura idempotent).

---

## Domini 14 — Frontend (Shell, EditableTable, tokens, i18n)

[x] fet

Tinc tota la informació. Redacto el markdown del domini.

### Entitats i camps
El domini Frontend no té entitats de BD; els "camps" rellevants són els **design tokens CSS** (única font de veritat de l'estil) i les **estructures de navegació**:
- Tokens de color/tipografia definits a `frontend/src/index.css:3-42` (paleta `--gold #c27a2a`, `--bg-sidebar #f0dfc0` cream, `--border`, escala `--fs-caption…--fs-display`, font global `IBM Plex Mono` a `index.css:44`).
- Còpia bessona de tokens al backoffice `frontend-backoffice/src/index.css:3-32` (mateixa paleta i font).
- `navGroups` (estructura del menú, 4 seccions amb `cap` de gating) a `frontend/src/components/layout/Sidebar.jsx:45-75`.
- `PATH_TO_KEY` (mapa ruta→clau i18n del breadcrumb) a `frontend/src/components/layout/Topbar.jsx:8-23`.
- `KONVA_COL` (paleta literal per al canvas Konva, que no entén CSS vars) a `frontend/src/pages/TechSheetEditor.jsx:49`.

### Relacions / FK (marca cross-schema amb db_constraint=False)
— cap — (domini de presentació, sense FK).

### Endpoints + gating (qui pot, quina capability/gate)
Gating de UI (no és gating d'autorització real; l'autoritat és el backend — això només amaga ítems):
- Filtrat del sidebar per capability a `frontend/src/components/layout/Sidebar.jsx:227-240`; mapa de gates `plan|configure|manage_users|onboarding` a `Sidebar.jsx:228-235`.
- Capabilities llegides de l'auth store a `Sidebar.jsx:195-197` (`manage_users`, `configure`, `define_tasks||configure`→`plan`).
- `onboarding` és gate dinàmic: ítem visible només si `onboardingPct < 100`, via `GET /api/v1/onboarding/status/` a `Sidebar.jsx:214-221`.
- Guard de rutes `ProtectedRoute` (autenticat o redirect a /login) a `frontend/src/App.jsx:43-46`.
- EditableTable crida directament endpoints de mesures: `POST /api/v1/models/{id}/set-measurements/` (`EditableTable.jsx:132`), `POST .../reorder-measurements/` (`:139`), `GET /api/v1/poms/cerca/` (`:383`), `POST /api/v1/poms/crear-tenant/` (`:397`).

### Frontend que hi penja
- Shell (layout arrel: sidebar + topbar + `<Outlet/>` + banner staging) a `frontend/src/components/layout/Shell.jsx:5-47`; muntat com a element pare de totes les rutes protegides a `App.jsx:127-173`.
- Topbar `frontend/src/components/layout/Topbar.jsx`, Sidebar `frontend/src/components/layout/Sidebar.jsx`, LanguageSwitcher `frontend/src/components/layout/LanguageSwitcher.jsx`.
- EditableTable consumit per: `pages/ModelMeasurements.jsx`, `components/MeasurementBaseGrid/MeasurementBaseGrid.jsx`, `components/model/SizeCheckTab.jsx`, `components/model/SizeCheckCell.jsx` (NO per `Planning.jsx`: allà només se cita el patró @dnd-kit en un comentari, `pages/Planning.jsx:335`).
- Kit UI compartit (tots amb importadors actius): `ui/Table.jsx` (8), `ui/Modal.jsx` (9), `ui/Feedback.jsx` (8), `ui/Badge.jsx` (7), `ui/Center.jsx` (7), `ui/Card.jsx` (5), `ui/StatCard.jsx` (2), `ui/TimerWidget.jsx` (2), helpers `ui/buttons.js` (`selS`, `primaryBtn`).
- Backoffice (app separada): `Layout.jsx`, `Sidebar.jsx`, `PrivateRoute.jsx` a `frontend-backoffice/src/components/`.

### Màquina d'estats / signals (PROPIETARI ÚNIC de cada estat: qui l'escriu)
Estat purament de UI (cap màquina d'estats de domini):
- Idioma: propietari únic `i18n` amb persistència a `localStorage['fhort.lang']`, escrit per `LanguageSwitcher.change` (`LanguageSwitcher.jsx:8-11`); config detector a `frontend/src/i18n/index.js:24-28`.
- Plegat de grups del sidebar: propietari `openGroups`, persistit a `localStorage['sidebarGroups']` a `Sidebar.jsx:202-212,287-293`.
- Ruta activa / auto-expand: derivat de `location.pathname` (longest-match) a `Sidebar.jsx:256-295`.
- Estat de fila editable (dirty/saving/localRows): propietari local d'EditableTable a `EditableTable.jsx:40-44`; persisteix via els POST de mesures.

### Serveis d'única entrada reaprofitables
- Tokens CSS com a única font d'estil: `index.css` (frontend i backoffice). Helpers de botó `ui/buttons.js`.
- `i18n` centralitzat: `frontend/src/i18n/index.js` (3 idiomes, detector localStorage→navigator).
- Kit `components/ui/*` (Table, Modal, Badge, Feedback, Card, Center, StatCard, TimerWidget) — capa reutilitzable canònica.
- `KONVA_COL` com a pont CSS→canvas a `TechSheetEditor.jsx:49` (perquè Konva no llegeix `var()`).

### 🔴 VELL/NOU (codi mort viu · dobles camins · òrfenes · documentat-no-implementat)
- **Codi mort declarat (no esborrat):** `pages/GarmentPOMMapEditor.jsx` — marcat "CODI MORT (jubilat)" a `App.jsx:20-22`, no muntat a cap ruta, només referenciat al comentari i a `SPRINT_S7_INTEGRATION.txt`. Endpoints fantasma `pom-map/*`→404.
- **Component òrfena:** `components/MeasurementTable/MeasurementTable.jsx` — cap import; només surt al comentari "netejar… amb MeasurementTable.jsx" (`App.jsx:22`).
- **Component òrfena:** `components/MeasurementsChat/MeasurementsChat.jsx` — zero importadors a tot `frontend/src/`.
- **Residus de documentació dins src/:** 8 fitxers `SPRINT_S*_INTEGRATION.txt`/`SPRINT_S4_*.txt` + `placeholder.txt` (`# Sprint 5 components`) a `frontend/src/components/` — soroll de build, no codi.
- **Doble camí d'icones Tabler (backoffice):** carrega la **webfont** Tabler a `frontend-backoffice/index.html:7` (usada amb `className="ti ti-*"` a `Sidebar.jsx`, `TenantDetailPage.jsx`) **i alhora** el paquet React `@tabler/icons-react` (`IconPlus`, `IconEye`…) a `TenantsPage.jsx:3`, `ContractesPage.jsx:2`, `ServeisPage.jsx:2`, `ContractDetailPage.jsx:3`, `DashboardPage.jsx:2`. Dos sistemes d'icones a la mateixa app.
- **Violació "outline-only" (icones filled):** `ti-star-filled` a `pages/FittingDetail.jsx:338`, `pages/MeasureTable.jsx:157,189`; `ti-player-play-filled` a `components/ui/TimerWidget.jsx:31`.
- **Drift de design tokens (hex hardcoded amb token equivalent):** `#3b6d11`(=`--ok`) 29 ocurrències, `#a32d2d`(=`--err`) 26, `#f5e6d0`(=`--gold-pale`) 38, `#1d1d1b`(=`--text-main`) 15, `#c27a2a`(=`--gold`) 8 a `components/`+`pages/`. La pròpia paleta del sidebar es redefineix com a objecte JS `C` barrejant vars i hex (`Sidebar.jsx:8-17`: `active:'#f5e6d0'`, `hover:'#fdf6ee'`, `border:'#e8e8e8'`).
- **Token divergent vell↔nou entre apps:** `--gate` ja migrat a verd al frontend (`frontend/src/index.css:30-31`: `var(--ok)`, comentari "abans #534ab7 lila") però **el backoffice manté el lila vell** `--gate:#534ab7` / `--gate-bg:#eeedfe` (`frontend-backoffice/src/index.css:30-31`).
- **i18n backoffice documentat-no-implementat:** `frontend-backoffice/src/i18n.js:5` ("s'anirà ampliant en sprints posteriors") només cobreix `login.*`; tota la resta del backoffice és text en dur en català (p.ex. "Nou tenant", "Carregant tenants…" a `TenantsPage.jsx:96,108,156`).
- **i18n frontend principal: paritat SANA** — `ca/en/es.json` tenen 1961 línies i 138 namespaces top-level idèntics, sense marcadors `TODO/FIXME`.
- **Botó global "Nou model" mort:** `showNewModel = false` fix a `Topbar.jsx:32`, bloc render mai actiu (`Topbar.jsx:100-119`).
- **Ruta redirect-only legacy:** `/models/:id/size-check`→`SizeCheckRedirect` a `App.jsx:48-55,145` (Size Check "jubilat").

### 🔗 CONNECTA AMB (blast radius: què es trenca si ho toques)
- `index.css` (tokens): tocar un token impacta **tot** el frontend (66 fitxers usen `--gold`/`--cream`/`IBM Plex`). Tocar la font global `*{font-family}` (`index.css:44`) afecta tota l'app.
- `Shell.jsx`: l'amplada del sidebar (240) està **duplicada** entre `Shell.jsx:26` (`marginLeft:240`) i `Sidebar.jsx:299` (`width:240`); també l'offset staging (28px) es repeteix a Shell/Sidebar/Topbar. Canviar-ne un sense l'altre trenca el layout.
- `Sidebar.jsx navGroups`: afegir/treure rutes ha de quadrar amb `App.jsx` (rutes) i amb `Topbar.PATH_TO_KEY`; un desajust deixa breadcrumb buit (cau a `app.title`) o ítem que apunta a 404.
- `i18n/*.json`: les claus `t('…')` estan escampades per tots els components; eliminar una clau trenca el text de múltiples pantalles.
- `EditableTable.jsx`: acoblat al contracte dels endpoints `set-measurements`/`reorder-measurements`/`poms/cerca`; canviar-ne el shape trenca les 4 pantalles que el munten.
- `KONVA_COL`: només viu dins `TechSheetEditor.jsx`/`TechSheetTemplateEditor.jsx`; aïllat de la resta.

### 🅰️/🅱️ Línia
- 🅰️ `frontend-backoffice/*` sencer (panell d'administració multi-tenant: tenants, contractes, serveis fiscals) — `pages/Tenants*`, `Contract*`, `Servei*`, `config/fiscal.js`, `config/estats.js`.
- 🅰️ Infra de presentació comuna: tokens `index.css`, `i18n`, kit `components/ui/*`, `Shell/Sidebar/Topbar`, `LanguageSwitcher` (plataforma, compartit per tot servei).
- 🅱️ Pantalles de servei sobre models del client muntades dins el Shell: `ModelMeasurements`, `EditableTable`, `TechSheetEditor`, `FittingDetail`, `SizeLibrary`, `GradingRuleSets`, etc. (treball facturable sobre dades del tenant).
- 🅰️🅱️ El Sidebar i el gating de capabilities: mecanisme de plataforma (🅰️) que governa l'accés a funcions de servei (🅱️).

### ⚖️ PER DECIDIR (Agus)
- Esborrar les 3 òrfenes (`GarmentPOMMapEditor.jsx`, `MeasurementTable.jsx`, `MeasurementsChat.jsx`) i els 9 `.txt`/`placeholder.txt` de `src/components/` (passada de neteja ja anunciada al comentari `App.jsx:22`).
- Unificar el sistema d'icones del backoffice: webfont Tabler **o** `@tabler/icons-react`, no tots dos.
- Migrar `--gate` del backoffice (`#534ab7` lila) al verd canònic per alinear-lo amb el frontend, o assumir que el backoffice té tema propi.
- Política "outline-only": acceptar `ti-star-filled`/`ti-player-play-filled` com a excepcions justificades (KEY/play) o substituir-les per outline.
- Campanya de des-hardcodejar hex cap a tokens (`#3b6d11`→`--ok`, `#a32d2d`→`--err`, etc.) i centralitzar l'amplada del sidebar (240) i l'offset staging en tokens/constants compartides.
- Decidir si el botó "Nou model" del Topbar (`showNewModel=false`) es retira definitivament o es reactiva.

### Obert / dubtós (el que no has pogut determinar amb certesa)
- No he pogut fer el diff clau-a-clau profund (nivells niats) dels 3 JSON i18n del frontend per confirmar paritat al 100% (Bash de comparació JSON bloquejat per protocol read-only); la paritat estructural (1961 línies + 138 namespaces idèntics, sense `TODO`) és un indici fort però no és prova exhaustiva de valors traduïts.
- No he verificat si el kit `components/ui/*` del frontend principal es reaprofita al backoffice o si el backoffice té el seu propi kit duplicat (caldria inspeccionar `frontend-backoffice/src/components/` en detall).
- `MeasurementsChat.jsx`: és òrfena ferma a `frontend/src/`, però no he descartat una càrrega dinàmica per string (no n'he trobat cap).

---

## Domini 15 — Creuament LÍNIA A/B

[x] fet

Confirmed: `Invoice`/`InvoiceLine` have NO serializer, NO endpoint, NO frontend listing. The endpoint `generate_invoice_view` creates them but nothing reads them back. The TenantDetailPage facturació tab is a Sprint-6 placeholder. I have enough to produce the report.

### Entitats i camps
- 🅰️ `ModelConsumptionEvent` (PUBLIC, el que FHORT factura: COUNT per {codi_client, period}) — `backoffice/models.py:63-77`. Camps mínims: `codi_client` (CharField 3, ref fluixa a `Client.codi_tenant`), `period` ('YYYY-MM'), `opaque_ref` (UUID unique, SENSE default — el valor ve del tenant), `merited_at`. Deliberadament NO porta codi ni nom de model.
- 🅱️ `ConsumptionRecord` (TENANT, l'albarà que veu el client) — `models_app/models.py:760-777`. `model` (OneToOne), `code_snapshot`, `name_snapshot`, `period`, `opaque_ref` (UUID default propi), `merited_at`. És l'àncora immutable del fet "aquest model va meritar"; el detall viu es calcula sobre `TaskTransition`/timers, no es duplica.
- 🅰️ `ServiceCatalog` (catàleg global de conceptes facturables, sense preu) — `backoffice/models.py:80-100`. `code`, `nom`, `tipus` ∈ {`tier_fee`, `model_count`, `manual`}, `actiu`.
- 🅰️🅱️ `TenantContract` — `backoffice/models.py:103-121`. FK `client`, `data_inici`/`data_fi`, `actiu`. Contracte SaaS FHORT↔tenant (instrument A) que tarifa treball B.
- 🅰️🅱️ `ContractLine` — `backoffice/models.py:124-144`. FK `contract`+`service`, `preu` (decimal 4), `moneda`, `inclosos` (franquícia), `actiu`. `unique_together(contract, service)`. AQUÍ viu el preu real per tenant (no al Plan).
- 🅰️🅱️ `Invoice` — `backoffice/models.py:147-183`. FK `client`, `period`, `tipus` ∈ {`auto`,`manual`}, `estat` ∈ {`esborrany`,`emesa`,`pagada`,`cancel·lada`}, `total`, `emesa_at`. UniqueConstraint condicional (`client,period,tipus`) només per `auto` (idempotència).
- 🅰️🅱️ `InvoiceLine` — `backoffice/models.py:186-206`. FK `invoice`+`service` (nullable per línies manuals lliures), `descripcio`, `quantitat`, `preu_unit`, `total`, `moneda`.
- 🅰️ `Plan` — `tenants/models.py:12-55`. Conté `preu_mensual`, `max_models_actius`, i (Sprint 2) `models_inclosos` + `preu_model_extra` + `moneda_pla`. Vegeu VELL/NOU: aquests tres camps de facturació són via morta.
- 🅱️ `Customer` (TENANT) — `tasks/models.py:295-318`. `codi` (3 chars, font del prefix `codi_intern` i del `codi_client` de meritació), `is_self` (self-customer amb `codi = Client.codi_tenant`).

### Relacions / FK (marca cross-schema amb db_constraint=False)
- `ModelConsumptionEvent.codi_client` ↔ `Client.codi_tenant`: **ref fluixa cross-schema PER VALOR, sense FK** (`backoffice/models.py:68`). No hi ha `db_constraint=False`; simplement no hi ha ForeignKey — s'uneix per string. És el pont public↔tenant.
- `ModelConsumptionEvent.opaque_ref` ↔ `ConsumptionRecord.opaque_ref`: mateix UUID transportat pel signal, **sense FK** (`backoffice/models.py:70`, `models_app/models.py:770`). Frontera de schema travessada per valor, no per constraint.
- `ConsumptionRecord.model` → `models_app.Model` OneToOne CASCADE — `models_app/models.py:764-766` (intra-tenant).
- `TenantContract.client` → `tenants.Client` PROTECT — `backoffice/models.py:108-110` (tot public, sense cross-schema).
- `ContractLine.service` → `ServiceCatalog` PROTECT; `ContractLine.contract` → CASCADE — `backoffice/models.py:128-133`.
- `Invoice.client` → `tenants.Client` PROTECT — `backoffice/models.py:160-162`. `InvoiceLine.invoice` CASCADE, `.service` PROTECT nullable — `backoffice/models.py:189-195`.
- `model.customer.codi` és l'origen real de `codi_client` en meritar (`tasks/services_c.py:111`), amb fallback a `tenant.codi_tenant` al reconcile (`reconcile_consumption.py:101`).

### Endpoints + gating (qui pot, quina capability/gate)
- 🅰️ `POST api/backoffice/v1/facturacio/generar/` → `generate_invoice_view` — `backoffice/views_contracts.py:48-74`. Gating: `[IsAuthenticated, HasBackofficeRole()]` (qualsevol BackofficeUser actiu, sense exigir rol FACTURACIO). Body `{codi_client, period, dry_run}`.
- 🅰️ `serveis` (ServiceCatalogViewSet) — `views_contracts.py:18-25`. Lectura: qualsevol BO actiu; mutacions (`create/update/partial_update/destroy`) → només `ADMIN`.
- 🅰️🅱️ `contractes` (TenantContractViewSet) — `views_contracts.py:28-39`. Mateix patró: mutacions només `ADMIN`.
- 🅰️ `tenants`/`plans` (ClientViewSet/PlanViewSet) — `views_tenants.py:30-44`, `views_tenants.py:216-221`. Tenants ReadOnly+accions ADMIN; Plans CRUD només ADMIN.
- 🅱️ `GET api/.../registre-activitat/` → `registre_activitat_view` — `models_app/views.py:1736-1738`, ruta `models_app/urls.py:186`. Gating: `[IsAuthenticated]` (usuari de TENANT). Llista `ConsumptionRecord` + temps agregat.
- 🅱️ `GET api/.../models/<id>/albara/` → `consumption_delivery_view` — `models_app/views.py:1422-1424`, ruta `models_app/urls.py:183`. Albarà viu intra-tenant.
- Roles definits: `BackofficeUser.Rol` = ADMIN/COMERCIAL/FACTURACIO/SUPORT (`backoffice/models.py:17-21`). NOTA: el rol `FACTURACIO` existeix però CAP endpoint l'exigeix (vegeu VELL/NOU).

### Frontend que hi penja
- `frontend-backoffice` (app A, personal FHORT): rutes a `App.jsx:21-31` → dashboard, tenants, serveis, contractes. **No hi ha cap ruta de factures/facturació.**
- `ContractesPage.jsx` / `ContractDetailPage.jsx` / `ContractFormPage.jsx` / `ServeisPage.jsx` + `api/contracts.js` — gestionen ServiceCatalog i TenantContract/ContractLine.
- `TenantDetailPage.jsx:203-214` tab "FACTURACIÓ I PAGAMENTS": només info fiscal + `Placeholder "Factures i pagaments — disponible al Sprint 6"`. Tab "pagament" → Placeholder Stripe Sprint 7 (`:217-226`).
- `Sidebar.jsx:33` "Contractes" amb icona `ti-file-invoice` (única referència visual a factura).
- Frontend de tenant (`frontend/`): `registre-activitat` i `albara` són els consums que veu el client (línia B), no inspeccionats en detall aquí.

### Màquina d'estats / signals (PROPIETARI ÚNIC de cada estat: qui l'escriu)
- Signal `model_consumption_started` — declarat a `tasks/signals.py:17`. **Emissor únic en runtime**: `tasks/services_c.py:108-114` (en arrencar la PRIMERA tasca → InProgress). Segon emissor: comanda `reconcile_consumption.py:140-146` (backfill). Receptor únic: `backoffice/receivers.py:7-18`, que escriu `ModelConsumptionEvent` a public via `schema_context('public')`.
- **Propietari de `Model.consumption_started_at` (marca de meritació)**: `tasks/services_c.py:96-98` (UPDATE guardat `isnull=True` → idempotència); també `reconcile_consumption.py:115-118`. Ningú més l'escriu.
- **Propietari de `ConsumptionRecord`**: `tasks/services_c.py:101` i `reconcile_consumption.py:131` (els dos únics creadors).
- **Propietari de `ModelConsumptionEvent`**: NOMÉS `receivers.py:11` (get_or_create per `opaque_ref`).
- **Propietari de `Invoice`/`InvoiceLine`**: NOMÉS `billing_service.generate_invoice` — `billing_service.py:110-115`. L'estat `Invoice.estat` neix sempre `esborrany`; la transició esborrany→emesa→pagada està documentada com Sprint 7 (`models.py:152`) però NO implementada — cap codi escriu `emesa`/`pagada`/`emesa_at`.
- Aïllament tècnic/facturació: la fase del model (`Pending→Dev`) s'escriu a `services_c.py:91` FORA del try de facturació; la meritació és no-fatal (`services_c.py:115-119`, mai bloqueja la transició del tècnic). Disseny "món tècnic sagrat / món facturació aïllat".

### Serveis d'única entrada reaprofitables
- `billing_service.generate_invoice(codi_client, period, dry_run)` — `billing_service.py:36-118`. Única entrada de generació de factura. Idempotent (`:50-55`), llegeix contracte vigent (`_get_active_contract` `:18-33`), compta `ModelConsumptionEvent` (`:63-65`), aplica franquícia `inclosos` per `model_count` (`:80-87`), salta `manual` (D1). Atòmic.
- Triple escriptura de meritació: patró duplicat literalment a `services_c.py:95-114` i `reconcile_consumption.py:113-146` — mateixa seqüència (UPDATE guard → ConsumptionRecord → signal). NO està factoritzat en un servei comú (vegeu dobles camins).

### 🔴 VELL/NOU (codi mort viu · dobles camins · òrfenes · documentat-no-implementat)
- **Doble camí de preus (VELL viu)**: `Plan.preu_model_extra` + `Plan.models_inclosos` + `Plan.moneda_pla` (`tenants/models.py:46-48`, Sprint 2) van ser substituïts per `ContractLine.preu`/`inclosos`/`moneda` (Sprint 5). El comentari de `TenantContract` ho diu explícit: *"El motor de facturació llegirà les ContractLine, no el Plan.preu_model_extra"* (`backoffice/models.py:106-107`), i `billing_service` mai llegeix el Plan. → camps de facturació del Plan = **òrfens de lectura per al motor**.
- **Triple-escriptura duplicada (doble camí de codi)**: la lògica de meritació viu copiada a `services_c.py:95-114` i `reconcile_consumption.py:113-146`. Risc de divergència si una de les dues canvia.
- **Rol `FACTURACIO` òrfena**: definit a `backoffice/models.py:20` però CAP `HasBackofficeRole(roles=[...])` l'usa; fins i tot `facturacio/generar/` només demana BO actiu (`views_contracts.py:49`). Capability declarada, no gated.
- **Invoice/InvoiceLine documentat-no-exposat**: existeixen i es creen, però NO tenen serializer, NO tenen endpoint de lectura/llista (cap `Invoice` a views/urls), NO tenen frontend. El tab facturació és Placeholder "Sprint 6" (`TenantDetailPage.jsx:213`). Les factures generades són un cul-de-sac: ningú les pot consultar per API/UI.
- **Transició d'estat de factura documentada-no-implementada**: esborrany→emesa→pagada + Stripe descrita a `models.py:152` i `views_tenants`/frontend (Sprint 7), sense cap escriptor real.
- **`tipus='manual'` skip permanent**: `billing_service.py:73` salta sempre `manual` (D1). El catàleg admet `manual` però el motor mai el factura — concepte definit sense camí automàtic.

### 🔗 CONNECTA AMB (blast radius: què es trenca si ho toques)
- `Customer.codi` (`tasks/models.py:301`): és alhora prefix de `codi_intern` I `codi_client` de facturació (`services_c.py:111`). Tocar-lo trenca codi-gen I la unió public↔facturació.
- `opaque_ref`: pont sense FK entre tenant i public. Si canvies com es genera/propaga (`services_c.py:101-112` → `receivers.py:11`), trenques la correlació albarà↔event facturable i la idempotència.
- `model_consumption_started` signal: 2 emissors / 1 receptor. Afegir receptors o canviar payload afecta `backoffice/receivers.py` (domini 3/13).
- `generate_invoice` depèn de `_get_active_contract` + `ContractLine.actiu` + `ServiceCatalog.tipus`: canviar `tipus` choices o desactivar línies altera silenciosament factures.
- `ModelConsumptionEvent.count()` és l'única font del recompte facturable (`billing_service.py:63`); si la triple-escriptura falla i no es reconcilia (N10), s'infrafactura.

### 🅰️/🅱️ Línia
- 🅰️ PLATAFORMA (public/infra/comú): `ModelConsumptionEvent`, `ServiceCatalog`, `Plan`, `Client`, `BackofficeUser`/`Rol`, tot `backoffice/` (views, billing_service, receivers), `frontend-backoffice`. És el motor SaaS multi-tenant.
- 🅱️ SERVEI (treball facturable sobre el model del client, intra-tenant): `ConsumptionRecord`, `Customer`, `Model.consumption_started_at`, `registre_activitat_view`, `consumption_delivery_view` (albarà), i el disparador real (arrencar la 1a tasca a `services_c.py`).
- 🅰️🅱️ FRONTERA: `TenantContract`/`ContractLine`/`Invoice`/`InvoiceLine` (instruments A que tarifen treball B) i el signal + `opaque_ref` (el cable que travessa B→A sense exposar dades de B).

### ⚖️ PER DECIDIR (Agus)
- Què fer amb `Plan.preu_model_extra`/`models_inclosos`/`moneda_pla` (Sprint 2): eliminar-los (i la migració de `Plan`) o re-connectar-los com a *default* del `ContractLine`? Ara són soroll que suggereix una segona font de preus inexistent.
- Factoritzar la triple-escriptura de meritació en un únic servei compartit per `services_c` i `reconcile_consumption` (eliminar el doble camí).
- `FACTURACIO` rol: o bé es fa gating real de `facturacio/generar/` i de les factures a aquest rol, o s'elimina del `TextChoices`.
- Tancar el cul-de-sac d'`Invoice`: exposar listing/serializer + UI, o assumir que Sprint 6 encara està a mig fer i marcar-ho a TECH_DEBT.
- `tipus='manual'`: definir si entra mai al motor o queda exclusivament per a `Invoice(tipus='manual')` creades a mà (que tampoc tenen camí de creació implementat).

### Obert / dubtós
- No he pogut confirmar si existeix algun job/cron que cridi `generate_invoice` mensualment (només he vist l'endpoint manual `facturacio/generar/` i la comanda `reconcile_consumption`). No hi ha cap referència a scheduler de facturació al `backoffice/`.
- No he inspeccionat el frontend de tenant (`frontend/`) per veure com es pinta `registre-activitat`/`albara` al client final — confirmat que els endpoints existeixen (línia B) però no la UI concreta.
- No he verificat si `Invoice.tipus='manual'` té algun camí de creació (cap endpoint trobat; sembla només model + migració `0004_invoice_and_lines.py`).
- `consumption_delivery_view` (albarà) el llegeix el tenant; no he confirmat si el backoffice PUBLIC hi té accés agregat (sembla que no — public només veu el COUNT via `ModelConsumptionEvent`).

---

## Domini 16 — Seeds / migracions / orfes

[x] fet

Tinc tot el material necessari. Genero l'informe.

### Entitats i camps
- Cap entitat/camp nou definit en aquest domini: management/commands i migracions **operen sobre** entitats d'altres dominis (Model, BaseMeasurement, POMGlobal/POMMaster, GradingRuleSet/GradingRule, SizeSystem/SizeDefinition, Customer, ConsumptionRecord, ModelConsumptionEvent). El domini és el de l'eina de sembra/migració, no model de dades.
- Camp marca-de-clon QA: constant `QA_TAG = '[QA-SC]'` escrita a `Model.nom_prenda` — `models_app/management/commands/clone_model_for_qa.py:18,78`.
- Flag `is_self` de Customer, sembrat per data migration — `tasks/migrations/0020_seed_self_customer.py:34,43`.

### Relacions / FK (marca cross-schema amb db_constraint=False)
- `reconcile_consumption` fa **triple escriptura cross-schema** explícita: Model + ConsumptionRecord al schema TENANT i ModelConsumptionEvent al schema `public` via senyal `model_consumption_started` (receiver fa `schema_context('public')`) — `backoffice/management/commands/reconcile_consumption.py:60-62,113-146`. No hi ha db_constraint aquí; el pont entre schemas és el senyal, no una FK.
- `clone_model_for_qa` **reusa per valor de FK** (no clona) `grading_rule_set`, `size_system`, `garment_type` en posar `pk=None` i desar — `clone_model_for_qa.py:73-88`.
- Migració M2M mecànica `SizeSystem.target (FK) → SizeSystem.targets (M2M)` amb data migration intermèdia — `pom/migrations/0021_remove_sizesystem_target_sizesystem_targets.py:33-44`.

### Endpoints + gating (qui pot, quina capability/gate)
- — cap — (cap command exposa endpoint; són CLI `manage.py`, sense gating HTTP). El gating efectiu és l'accés a la shell del servidor.

### Frontend que hi penja
- — cap — (cap referència de frontend a aquests commands/migracions).

### Màquina d'estats / signals (PROPIETARI ÚNIC de cada estat: qui l'escriu)
- `reconcile_consumption` és **co-propietari (backfill) de `Model.consumption_started_at`**: el hook 4.2 l'escriu en temps real i aquest command el reescriu retroactivament als forats N10, amb guard d'idempotència `filter(consumption_started_at__isnull=True).update(...)` — `reconcile_consumption.py:115-118`. Replica el mateix senyal `model_consumption_started` que el hook (mateix propietari del fet PUBLIC).
- `clone_model_for_qa` **delega la creació de SizeFitting al signal** (`sync_size_fitting` crea el SF 'Proto' en desar el Model amb responsable) i només defensivament el crea si el signal no ha disparat — `clone_model_for_qa.py:80,86,106-109`. Després crea GradingVersion activa i crida `generate_graded_specs` (propietari real del grading viu a `pom.services`).
- `0027_data_fit_to_proto`: migra `Model.fase_actual='Fit'→'Proto'` i `FittingSession.fase='Fit'→'Proto'` (defensiva, en eliminar la fase Fit del choices) — `models_app/migrations/0027_data_fit_to_proto.py:6-13`.

### Serveis d'única entrada reaprofitables
- `clone_model_for_qa` és **reutilitzable i idempotent** (guard per `customer + nom_prenda startswith QA_TAG`; `--recreate` purga via `_purge`) — `clone_model_for_qa.py:59-70,148-163`. Punt únic per regenerar el model de QA de Size Check.
- `reconcile_consumption` és reutilitzable, idempotent i multi-tenant (`--tenant`, `--dry-run`) — `reconcile_consumption.py:31-50,115-128`.
- `reconcile_tenant_poms`: idempotent, dry-run per defecte, guarda "només actua si POMMaster tenant-only" — `reconcile_tenant_poms.py:18-19,39-40`.
- Família de seeds idempotents no-destructius (`update_or_create`/`get_or_create`, "mai delete"): `extend_pom_catalog`, `seed_baby_poms`, `load_map_inline`, `seed_commercial_size_runs`, `seed_baby_months_grading/profiles`, `translate_garment_families`, `restructure_garment_types_v2` (desactiva el vell sense esborrar) — capçaleres respectives (p.ex. `extend_pom_catalog.py:4,171`; `restructure_garment_types_v2.py:6,251`).

### 🔴 VELL/NOU (codi mort viu · dobles camins · òrfenes · documentat-no-implementat)
- **CODI MORT VIU declarat**: `reseed_tenant_fhort.py:2-7` marcat `OBSOLET (2026-06-17) — NO EXECUTAR`. Usa l'eix `garment_type` a GarmentPOMMap eliminat a la migració pom 0016; la creació de GarmentPOMMap (≈L284) **peta** amb l'esquema actual (cal `garment_type_item`). Es conserva només com a valor latent de sembra. Confirmat a docs — `ESTAT_PROJECTE.md:596` ("deixat MORT i marcat obsolet").
- **DOBLE CAMÍ Garment Types**: l'eix vell `garment_type` (família) vs el nou `garment_type_item` conviu: `backfill_model_items.py` migra legacy `garment_type→garment_type_item` amb taula hardcoded `BACKFILL` (10 mapes) + `REVIEW` (human-review flag per `TAILORED_PANTS`) — `backfill_model_items.py:13-29`. És el pont vell→nou; un cop tots els models migrats, queda òrfena.
- **PKs HARDCODED de PROD (fràgils, tenant-específics)**: 
  - golden `--source 162` per defecte a `clone_model_for_qa.py:32` (i a docstrings :4-5, comentari :99). La nota MEMORY diu que el QA va al pk=182 i el golden és 162/162; el default 162 lliga el command a PROD-fhort.
  - `reconcile_tenant_poms.py:30,33-36`: `DEACTIVATE_IDS=[387,388]` i 17 ids a `CLEAR_REVISIO_IDS` — POMMaster ids concrets de PROD-fhort. Hi ha guarda de seguretat (només si tenant-only) però els ids no són portables a cap altre tenant.
  - `seed_commercial_size_runs.py:60`: tupla `(10,'13/14',156,179)` — el 179 és cm corporal, no és el golden model 179; **no** és PK hardcoded de Model.
- **Migracions irreversibles de facto**: `pom/0023_complete_pom91_numeric_size_system` té reverse `migrations.RunPython.noop` (no desfà) — `pom/migrations/0023:55`. És defensiva i resol per CODI (`EU_WOVEN_WOMAN_NUMERIC`/`NUMERIC_EU_W`), no per pk — `:6-45`. Acceptable però no reversible.
- **Sense fixtures ni loaddata**: no existeix cap directori `fixtures/` ni crida `loaddata` al projecte (verificat).
- **`reconcile_consumption` documentat i implementat** (no és gap): present a `MAPA_SISTEMA.md:327`.

### 🔗 CONNECTA AMB (blast radius: què es trenca si ho toques)
- `clone_model_for_qa` toca: Model, BaseMeasurement, ModelGradingRule, SizeFitting, GradingVersion, GradedSpec, ModelTask, TaskType('size_check'), UserProfile, i `pom.services.generate_graded_specs`. Depèn del **signal** `sync_size_fitting` (si canvia la creació de SF, el clon es trenca) i de l'existència de `TaskType code='size_check'` (`raise CommandError` si falta — `:115-117`). `_purge` coneix la cadena de FKs PROTECT (SizeCheck/SizeCheckLine, GradedSpec, GradingVersion, PieceFitting, MeasurementChangeLog…) — `:150-163`; si s'afegeix un fill PROTECT nou caldrà ampliar `_purge`.
- `reconcile_consumption` depèn de `TaskTransition` (reconstrueix `merited_at=MIN(→InProgress)`), del senyal `model_consumption_started` i del seu receiver a public — `:79-146`. Si canvia la semàntica del hook 4.2 o el senyal, aquest backfill diverge.
- Seeds POM/grading depenen de rutes Excel absolutes a `/root/fhort-sessions/...xlsx` — `reseed_tenant_fhort.py:29-30`, `reseed_size_definitions.py:27`. Si el fitxer no existeix al servidor, peten/no fan res.
- `0021` (target→targets M2M): qualsevol codi que encara llegeixi `SizeSystem.target` (FK ja eliminada) es trenca — caldria mirar usos al domini talles.

### 🅰️/🅱️ Línia
- 🅰️ `tasks/migrations/0020_seed_self_customer.py` (per-schema, salta public): infraestructura de provisió de tenant (self-customer com a fallback del codi-gen). Conté pendent d'onboarding A — `:7-9`.
- 🅰️ `create_backoffice_admin.py` (usuaris de backoffice/plataforma).
- 🅱️ `clone_model_for_qa`, `reconcile_tenant_poms`, `reseed_tenant_fhort`, `reseed_size_definitions`, tots els `seed_*`/`extend_pom_catalog`/`load_map_inline`/`backfill_*`/`restructure_garment_types_v2`/`translate_garment_families`: dades de servei del client fhort (POMs, grading, talles, models).
- 🅰️🅱️ `reconcile_consumption`: és **A+B** — recorre tots els tenants (`exclude(schema_name='public')`, `--tenant`) i escriu tant al schema tenant (B, ConsumptionRecord) com al public (A, ModelConsumptionEvent / facturació) — `:46,59-146`.

### ⚖️ PER DECIDIR (Agus)
- Default `--source 162` a `clone_model_for_qa`: lligar-lo a un golden hardcoded de PROD-fhort el fa no-portable. Decidir si es treu el default (fer `--source` obligatori) o es resol per TAG/codi en lloc de pk.
- `reconcile_tenant_poms` amb 19 ids hardcoded de PROD-fhort: és un one-shot de reconciliació ja aplicat (`ESTAT_PROJECTE.md:1176`, commit `72c3d42`). Decidir si s'arxiva/elimina ara que ja s'ha executat (queda com a codi mort viu específic d'un tenant).
- `reseed_tenant_fhort` OBSOLET: decidir si s'elimina del repo o es refà des de BD viva (1.527 maps canònics, segons docstring :6-7).
- `backfill_model_items` i `0027_data_fit_to_proto`: ponts vell→nou ja consumits; decidir si es retiren un cop confirmat que no queden models legacy.
- Rutes Excel absolutes `/root/fhort-sessions/*.xlsx` dins commands de sembra: decidir si es versionen al repo o es deixen com a dependència externa del servidor.

### Obert / dubtós
- No he obert el cos complet de `reseed_tenant_fhort.py` (L80-400) ni dels seeds baby/kids (només capçaleres + help): no puc afirmar que **no** continguin altres PKs/ids hardcoded més enllà dels detectats; el grep `id=/pk=/_IDS` només va trobar els de `reconcile_tenant_poms`.
- No he verificat dins el codi viu (serializers/views) si encara hi ha lectures de `SizeSystem.target` (FK eliminada a 0021) — caldria al domini de talles per confirmar que la migració no ha deixat lectors orfes.
- No puc confirmar amb certesa quants models legacy queden sense `garment_type_item` (estat de BD), per dictaminar si `backfill_model_items` ja és definitivament òrfena.
