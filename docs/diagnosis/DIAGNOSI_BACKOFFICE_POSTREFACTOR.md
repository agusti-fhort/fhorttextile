# DIAGNOSI — Backoffice post-refactor (represa, peça 1)

Data: 2026-07-10 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`

**Abast:** estat real de l'app `backoffice` (SHARED sobre `public`) i de la SPA
`frontend-backoffice` després del refactor G1-G8 + mòdul `commerce` + S01-S03, que no la
van tocar conscientment. Inclou l'entorn `stagingbackoffice.fhorttextile.tech` i el cens
de seed d'onboarding per a la fase 2 (desplegar tenants).

**Convenció:** cada afirmació porta `fitxer:línia` o sortida literal de comanda.
`"NO EXISTEIX"` = confirmat absent al codi/BD (no especulat). Les propostes van marcades
`💡 PROPOSTA (a validar)` i no són decisions.

**Verificació:** BD `ftt_staging` (127.0.0.1:5433), només `SELECT`. Cap escriptura de codi,
BD, config ni servei. `reconcile_consumption --dry-run` executat **després** de verificar al
codi que cap branca d'escriptura s'hi arriba (`reconcile_consumption.py:81-86,134-140`).

---

## Resum executiu

1. **El backoffice no s'ha trencat, però tampoc s'ha quedat quiet.** El codi de dev està
   *per davant* de main en exactament 1 commit (`333b5d7`), i el que hi va entrar és
   precisament lògica del **mòdul comercial dins la comanda de reconciliació de la
   facturació SaaS**. Migracions 4/4 aplicades, sense drift.

2. **La cadena de meritació és VIVA i està al dia.** Tots els camins que posen una tasca a
   `InProgress` passen per `transition_task`; el senyal, el receiver, el guard
   d'idempotència i el no-fatal N10 són intactes. `reconcile --dry-run` → **0 forats de
   meritació**. La por central (que el refactor de `transition_task` hagués creat un camí
   que no emet el senyal) **no s'ha materialitzat**.

3. **⚠️ CONTRADICCIÓ DE PARADIGMA (STOP).** La llei "dues facturacions separades" es
   respecta a nivell d'imports, noms i schemes — però es **viola a nivell transaccional**:
   `assign_work_order` (commerce) corre *dins* del mateix `transaction.atomic()` que la
   meritació SaaS. **Un error del mòdul comercial fa rollback d'una meritació que ja havia
   tingut èxit.** Detall a B3 · T1. **No s'ha tocat res.**

4. **`stagingbackoffice.fhorttextile.tech` NO EXISTEIX com a entorn.** No hi ha vhost
   nginx, ni certificat, ni fila a `tenants_domain`, ni build de la SPA. El domini resol i
   cau al `default_server`, que serveix una app Flask aliena (`assessment`). L'API del
   backoffice, en canvi, respon 200 pels hostnames que sí tenen Domain.

5. **La SPA del backoffice no és construïble ni servida avui.** No hi ha `node_modules`,
   no hi ha `dist`, no hi ha symlink, i **Django no serveix la SPA en cap punt** (només
   API sota `api/backoffice/v1/`).

6. **L'onboarding d'un tenant nou està a mig camí.** Neixen sols amb el tenant: TaskType
   (14), self-Customer, unitats i condicions de pagament de commerce. **No neix res del
   catàleg de patronatge** (GarmentType 17/57, POMGlobal 125, GarmentPOMMap 1529,
   SizingProfile 26): tot viu en scripts amb `'fhort'` hardcoded. Dues correccions a les
   premisses del brief: `reseed_tenant_fhort.py` ja és **inert** (aborta amb `CommandError`),
   i `seed_pom_maps_to_items.py` **NO EXISTEIX**.

---

## B1 — Integritat del codi a dev

### Divergència git

`git log --oneline main..dev -- backend/fhort/backoffice/ frontend-backoffice/` → **1 commit**:
`333b5d7 commerce: collector lazy + assignacio work_order + reconcile`.

`git log --oneline dev..main -- <mateixos paths>` → **sortida buida**. No hi ha res del
backoffice a main que falti a dev.

`git diff --stat main dev -- backend/fhort/backoffice/ frontend-backoffice/`:
```
 .../management/commands/reconcile_consumption.py | 35 ++++++++++++++++++++--
 1 file changed, 33 insertions(+), 2 deletions(-)
```

**Veredicte direccional: el backoffice de dev està PER DAVANT de main**, per un sol fitxer.
`frontend-backoffice/` és **idèntic** entre main i dev (zero diff; el commit no el toca).

**Què va entrar** a `backoffice/management/commands/reconcile_consumption.py`: la regla
d'assignació retroactiva **B4a — ENCÀRREC**. Purament additiu (33 insercions, 2 modif.),
no elimina lògica. Afegeix `from fhort.tasks.services_c import assign_work_order`
(`reconcile_consumption.py:64`) i una branca que busca `ModelTask` amb
`work_order__isnull=True` i status en `['InProgress','Done','Paused']`, calcula
`period = MIN(→InProgress)` via `TaskTransition` i crida `assign_work_order` respectant
`--dry-run` (`reconcile_consumption.py:65-91`). Vegeu B3 · T2: això fa que la comanda de
reconciliació **SaaS** depengui de `commerce`.

### Els 14 commits que dev NO té de main

`git rev-list --left-right --count main...dev` → `14  634`.
`git log --oneline dev..main -- backoffice/ commerce/ tasks/ frontend-backoffice/` retorna
**només** `2f127da feat(size): SizingProfileSelector + fit-types endpoint (SIZE-1B-1)`, i
d'aquest només toca `tasks/urls.py` (ruta `fit-types/`). **Cap dels 14 toca el backoffice.**
Dev està endarrerit respecte main, però no en res que afecti aquesta represa.

### Migracions

Fitxers a `backend/fhort/backoffice/migrations/`: `0001_backoffice_users`,
`0002_model_consumption_event`, `0003_service_catalog_and_contracts`, `0004_invoice_and_lines`.

`manage.py showmigrations backoffice` → les 4 amb `[X]`. Confirmat per SELECT sobre
`public.django_migrations` (4 files, aplicades entre 2026-06-05 i 2026-06-07).

- Migracions al disc no aplicades: **cap**.
- Registres a la BD sense fitxer: **cap**.
- `makemigrations --check --dry-run backoffice` → `No changes detected in app 'backoffice'`
  (exit 0). **Sense drift de model.**

Backoffice és SHARED_APP: `settings.py:57-58` (`'fhort.backoffice'` dins `SHARED_APPS`, amb
el comentari "NOMÉS public (mai a TENANT_APPS)").

### Frontend-backoffice

`frontend-backoffice/` **EXISTEIX** (React 19, react-router 7, vite 8, tailwind 4, axios,
zustand, react-query, i18next). Però:

- `frontend-backoffice/node_modules/` → **NO EXISTEIX**.
- `frontend-backoffice/dist/` → **NO EXISTEIX**.
- `npm run build` → `sh: 1: vite: not found`, exit 127. **NO es pot construir sense
  `npm install`** (escriptura a disc) → **NO EXECUTAT** per la línia dura del Patró A.
- Symlink `backend/fhort/backoffice/dist` → **NO EXISTEIX**. `find backend -maxdepth 4 -name dist`
  → cap resultat.
- **Django no serveix la SPA.** `backoffice/urls.py` només munta rutes DRF; muntat a
  `urls_public.py:35` com `path('api/backoffice/v1/', include('fhort.backoffice.urls'))`.
  Grep de `TemplateView|index.html|serve(|frontend-backoffice|dist` a tot `backend/**.py`
  → **cap coincidència**.

> **Veredicte B1:** codi i migracions **llestos i verds**. El frontend és un projecte viu
> però **no construït ni servit**: cal `npm install` + `npm run build` + decidir qui serveix
> el `dist` (avui ningú). Res d'això és un trencament del refactor; és feina no feta.

---

## B2 — La cadena de meritació

### Emissor → senyal → receiver → escriptura a public

| Node | Ubicació | Estat |
|---|---|---|
| Definició del senyal | `tasks/signals.py:17` `model_consumption_started = Signal()` | VIU |
| Emissor (runtime) | `tasks/services_c.py:172`, dins `transition_task` | VIU |
| Emissor (backfill) | `backoffice/management/commands/reconcile_consumption.py:171` | VIU |
| Receiver | `backoffice/receivers.py:7-18` `on_model_consumption_started` | VIU |
| Registre | `backoffice/apps.py:8` → `ready()` importa `receivers` | VIU |
| Escriptura | `schema_context('public')` → `ModelConsumptionEvent.get_or_create(opaque_ref=…)` | VIU |

`grep -rn "model_consumption_started" backend/` → només aquests dos emissors i el receiver.

### El risc central: ¿algun camí de transició no emet el senyal?

**No.** Tots els camins que posen `status='InProgress'` travessen `transition_task`
(`services_c.py:96`), i l'emissió viu dins el seu bloc `if to_status == 'InProgress':`
(`services_c.py:150-178`). Cridadors auditats:

- `tasks/views_b.py:449` `transition_task_view` (POST `.../transition/`) → crida.
- `tasks/views_b.py:559` `open_model_task_view` (open-task) → crida si no és ja InProgress;
  si ja ho és d'un altre tècnic només fa *claim* (`views_b.py:562`), i el model ja va meritar
  a la seva **primera** InProgress. Correcte.
- `tasks/views_b.py:495-505` `claim_task_view` → **no toca `status`** (documentat a
  `views_b.py:474`); correctament no ha d'emetre.
- `models_app/views.py:737,739`, `models_app/services_size_check.py:221-222`,
  `tasks/management/commands/retype_scaling_to_grading.py:66-67` → tots reusen `transition_task`.
- `tasks/views_b.py:268` (endpoint `extra`) crea una `ModelTask` **ad-hoc amb `status='Pending'`**
  → meritarà quan passi a InProgress. No és un bypass.

**NO EXISTEIX** cap ruta de transició a InProgress que ometi el senyal. `_legacy_archive/`
no conté cap transició viva.

### Guard d'idempotència — INTACTE

`services_c.py:160-162`:
`Model.objects.filter(pk=…, consumption_started_at__isnull=True).update(consumption_started_at=now)`;
només si `rows` (`:163`) es crea el `ConsumptionRecord` i s'emet el senyal.
Camp: `models_app/models.py:204` `consumption_started_at = DateTimeField(null=True, blank=True)`.
El mateix guard es repeteix defensivament al backfill (`reconcile_consumption.py:146-149`).

### N10 (no-fatal) — INTACTE, sense re-raise

`services_c.py:158` obre `try: with transaction.atomic():`; `services_c.py:183-186` fa
`except Exception: logger.exception(...)`; `services_c.py:187` porta el comentari explícit
**"NO re-raise: el tecnic ja te la transicio feta; el forat es reconcilia despres."**
El `.send()` (`:172`) és dins d'aquest try → una excepció del receiver no tomba la transició.

**Nota de registre:** el receiver usa `@receiver(...)` **sense `dispatch_uid`**
(`receivers.py:7`). Un doble import el registraria dues vegades, però
`get_or_create(opaque_ref=…)` amb `opaque_ref` UNIQUE (`backoffice/models.py:70`) el fa
idempotent → sense impacte real. Ho anoto, no ho arreglo.

### `reconcile_consumption` — executable, `--dry-run` verificat no-escriptura

Imports vius, models existents. Cada branca d'escriptura queda darrere `if dry_run: … continue`
**abans** de qualsevol `.update()`/`.create()`/`.send()` (`:81-86` work_order, `:134-140` meritació).
Executat:
```
[DRY-RUN] Tenant: fhort (FTT)
  ... 30 × [DRY-RUN] WOULD ASSIGN work_order ...
  No gaps found.
[DRY-RUN] Done: 0 merited, 0 skipped, 0 errors, 30 work_orders assigned.
```

**0 forats de meritació.** Els 30 `WOULD ASSIGN work_order` són backfill B4a d'encàrrecs
(commerce), **no** meritació — 30 tasques amb activitat sense `work_order`. Scope separat.

### Traça de dades real (la cadena està viva en runtime, no només en codi)

- `public.backoffice_modelconsumptionevent`: **21 files**, `merited_at` de 2026-06-05 09:42
  a 2026-07-06 13:58. Per client/període: BRW 2026-06 = 13, BRW 2026-07 = 1, FTT 2026-06 = 4,
  LOS 2026-06 = 3.
- `fhort.models_app_consumptionrecord`: **16 files** (2026-06-08 → 2026-07-06).
- `fhort.models_app_model`: 16/20 amb `consumption_started_at` no-null.
- Última transició →InProgress: **2026-07-08 17:22** (166 transicions InProgress totals).
- **Models amb activitat (InProgress/Done/Paused) sense `consumption_started_at` = 0.**

Integritat bidireccional de `opaque_ref`:
- Registres del tenant **sense** event a public: **0** → cada meritació té el seu event.
- Events a public **sense** registre al tenant `fhort`: **5** → orfes de tenants ja
  eliminats (BRW, LOS ja no tenen schema; `tenants_client` només té `fhort` i `public`).
  Coherent amb el disseny de referència fluixa (`backoffice/models.py:65-67`: public és el
  llibre de facturació i sobreviu a la baixa del tenant). Explica el desfàs 21 vs 16.

Entre 2026-07-06 i 2026-07-08 hi ha transicions →InProgress sense meritació nova: **no és
trencament**, és el guard actuant (només merita la *primera* InProgress de cada model).

> **Veredicte B2: VIU i al dia.** Els cinc nodes existeixen, estan connectats i s'exerciten.
> Cap peça "NO EXISTEIX". Zero forats.

---

## B3 — Frontera amb el mòdul `commerce`

### El que està net

**Imports creuats directes: CAP**, en cap direcció.
`grep -rn "backoffice" backend/fhort/commerce/` → buit.
`grep -rn "commerce" backend/fhort/backoffice/` → només `reconcile_consumption.py:64` (via `tasks`, vegeu T2).

**Col·lisió de noms de model: CAP.** Cap `db_table` ni `app_label` explícits → labels i
taules per defecte. Els noms "perillosos":

| Nom | commerce | backoffice |
|---|---|---|
| `Invoice` / `InvoiceLine` | — | `models.py:147,186` |
| `DeliveryNote` | `models.py:626,685` | — |
| Contracte | — | `TenantContract`/`ContractLine` `models.py:103,124` |
| `Client` / `Customer` / `Plan` | — | — (viuen a `tenants` i `tasks`) |

**Separació de schemes: CORRECTA.** `settings.py:58` → `fhort.backoffice` a `SHARED_APPS`;
`settings.py:72` → `fhort.commerce` a `TENANT_APPS`.

**FK creuada tenant↔public: CAP.** FKs de `commerce/models.py` apunten només a
`accounts.UserProfile`, `models_app.Model`, `tasks.{Customer,GarmentTypeItem,ModelTask,Supplier}`
i a si mateix — tots TENANT. FKs de `backoffice/models.py` apunten a `tenants.Client`
(SHARED, `:108,160`) i a si mateix; `grep -E "commerce|tasks\.|models_app|accounts"` sobre
`backoffice/models.py` → **buit**. El bug estructural de django-tenants **no hi és**.

### 🛑 T1 — TROBALLA TRANSVERSAL (afecta B2) · CONTRADICCIÓ DE PARADIGMA

**Fet, verificat llegint `services_c.py:150-189` directament:**

`assign_work_order(task, now)` (`services_c.py:182`) — lògica del **mòdul comercial** — s'executa
**dins del mateix `with transaction.atomic()`** (obert a `services_c.py:159`) que:
- fa `Model...update(consumption_started_at=now)` (`:160-162`),
- crea el `ConsumptionRecord` (`:164-170`),
- emet `model_consumption_started` (`:172-176`), l'entrega del qual és **síncrona** i escriu
  `ModelConsumptionEvent` a `public` (`receivers.py:10-18`) sobre **la mateixa connexió i
  transacció** (`schema_context` només canvia el `search_path`, no la connexió).

Tot plegat sota l'`except Exception:` no-fatal (`:183-186`) que **no re-llança**.

**Conseqüència:** si `assign_work_order` llança —p. ex. una carrera sobre
`uniq_collector_customer_period` al `get_or_create` del col·lector (`_resolve_work_order`,
`services_c.py:73-75` + constraint a `commerce/models.py:515`), o qualsevol error del
WorkOrder— l'`except` **empassa l'error** i el `atomic()` fa **ROLLBACK de la meritació que
ja havia tingut èxit**: es desfan `consumption_started_at`, el `ConsumptionRecord` i l'event
de `public`. La transició del tècnic queda committed; **la meritació SaaS es perd**.

És a dir: **un bug del mòdul comercial (tenant) pot revertir la facturació SaaS (public)** —
exactament l'acoblament que la llei "dues facturacions separades" existeix per evitar.

**Atenuants (per calibrar el risc, no per descartar-lo):** el forat és recuperable via
`reconcile_consumption`, i avui `--dry-run` reporta **0 forats de meritació**. El dany seria
silenciós (només `logger.exception`) fins al següent reconcile.

**Segons el brief: STOP. Anotat, no arreglat.** Requereix decisió Patró C (vegeu D1).

### T2 — `reconcile_consumption` (SHARED) depèn de `commerce` (TENANT)

`backoffice/management/commands/reconcile_consumption.py:64` importa `assign_work_order`,
que al seu torn fa `from fhort.commerce.models import WorkOrder` (`services_c.py:65`). La
comanda que reconstrueix la meritació FHORT→client executa, al mateix bucle per-tenant,
l'assignació d'encàrrecs del mòdul comercial (`:79-91`). Un error o un import trencat de
`commerce` impacta el reconcile de la facturació SaaS.

### T3 — Import invers `tasks → commerce` i cicle

`services_c.py:65`, `views_b.py:268` i `models_app/views.py:73` fan
`from fhort.commerce.models import WorkOrder`; `commerce/services.py:234` fa
`from fhort.tasks.models import ModelTask`. **Cicle `commerce ↔ tasks`.** Tots dos són
TENANT (no viola schemes), però és el vector pel qual la lògica comercial s'ha filtrat
dins el camí de meritació.

### Rutes de commerce que toquen tasques — no trenquen B2

- `commerce/services.py:224` `assign_model_to_order_line`: reassigna `work_order`/`off_recipe`
  de ModelTask existents (`:272` `save(update_fields=[...])`), **no crea tasques ni canvia
  `status`** → no s'espera meritació. Cap bypass.
- `commerce/services.py:164` `close_work_order`: posa `task.work_order=None` (`:211`), tampoc
  toca `status`.

> **Veredicte B3:** la frontera **estructural** (imports, noms, taules, FK, schemes) està
> **neta**. La frontera **transaccional** està **trencada** (T1). La barreja no és
> `commerce ↔ backoffice` sinó `commerce → tasks (transition_task) → senyal → backoffice`.

---

## B4 — Entorn `stagingbackoffice.fhorttextile.tech`

**Veredicte anticipat: l'entorn NO EXISTEIX funcionalment.** El DNS resol a aquest servidor
(`178.105.48.204`, mateix host que `staging.fhorttextile.tech`), però no hi ha cap peça muntada.

### nginx

`grep -rn "stagingbackoffice" /etc/nginx/` → **exit 1, cap coincidència. NO EXISTEIX server block.**

`sites-enabled/`: `assessment`, `backoffice`, `fhort`, `ftt-staging`, `post-me`, `trading`, `webiafy`.

- ⚠️ **`sites-enabled/backoffice` NO és aquest entorn**: és `server_name backoffice.webiafy.com`
  → `proxy_pass http://127.0.0.1:4324` (Next.js de webiafy). Trampa de noms.
- `sites-enabled/ftt-staging` (`server_name staging.fhorttextile.tech`): `listen 443 ssl`,
  cert `/etc/letsencrypt/live/staging.fhorttextile.tech/fullchain.pem`,
  `root /var/www/ftt-staging/frontend/dist` (SPA de **tenant**), `auth_basic` amb
  `.htpasswd-staging` (desactivat a `/api/`, `/admin/`, acme), `location /api/|/admin/|/static/`
  → `proxy_pass http://127.0.0.1:8001`, `/media/` → `alias .../backend/media/`.
  **No hi ha upstream diferenciat**: el backoffice compartiria el mateix gunicorn `:8001`.

**Qui atén el domini avui:** sense server block, nginx cau al `default_server` de `:443`, que
és `assessment` (`server_name assessment.fhort.cat`, `proxy_pass unix:/var/www/assessment/assessment.sock`).
Empíricament: `curl -skI https://stagingbackoffice.fhorttextile.tech/` → `302 FOUND`,
`Location: /login?next=/`, `Set-Cookie: session=…` — **és l'app Flask d'assessment, no FTT**.
Només respon amb `-k`: el cert presentat és el d'`assessment.fhort.cat`, invàlid per aquest host.

**Certificat:** `ls /etc/letsencrypt/live/` → `assessment.fhort.cat`, `backoffice.webiafy.com`,
`fhort.cat`, `post-me.net`, `staging.fhorttextile.tech`, `trading.fhort.cat`, `webiafy.com`.
**`stagingbackoffice.fhorttextile.tech` → NO EXISTEIX.**
(El de `staging.fhorttextile.tech` és vigent: `notAfter=Sep 9 15:56:54 2026 GMT`.)

**`root` per a la SPA:** no n'hi ha (no hi ha vhost). I encara que n'hi hagués,
`frontend-backoffice/dist` **NO EXISTEIX** (B1).

### Django / django-tenants

- `settings.py:97` → `PUBLIC_SCHEMA_URLCONF = 'fhort.urls_public'` (**EXISTEIX**);
  `settings.py:96` → `ROOT_URLCONF = 'fhort.urls'`.
- `fhort/urls_public.py` **sí** inclou el backoffice (`:35`), però aquest urlconf només
  s'activa quan el tenant resolt és el schema `public`.
- `SHOW_PUBLIC_IF_NO_TENANT` → **NO EXISTEIX** a `settings.py` → default de django-tenants:
  404 si no hi ha Domain.
- `settings.py:78-79` → `TENANT_MODEL='tenants.Client'`, `TENANT_DOMAIN_MODEL='tenants.Domain'`.

**`public.tenants_domain × tenants_client` (SELECT read-only):**
```
          domain              | is_primary | schema_name |      nom
------------------------------+------------+-------------+------------------
 178.105.217.125              |     f      | fhort       | FHORT Management
 backoffice.fhorttextile.tech |     f      | public      | FHORT System
 fhorttextile.tech            |     t      | fhort       | FHORT Management
 localhost                    |     t      | public      | FHORT System
 staging.fhorttextile.tech    |     f      | fhort       | FHORT Management
```

- **Domain per `stagingbackoffice.fhorttextile.tech` → NO EXISTEIX.** Confirmat empíricament:
  `curl -H "Host: stagingbackoffice.fhorttextile.tech" http://127.0.0.1:8001/...` → **404**
  `No tenant for hostname "stagingbackoffice.fhorttextile.tech"`.
- ⚠️ `staging.fhorttextile.tech` pertany al schema **`fhort`**, no a `public`. Per això
  `curl -H "Host: staging.fhorttextile.tech" .../api/backoffice/v1/health/` també dona **404**
  (fa servir `ROOT_URLCONF`, sense backoffice). El backoffice **no és accessible** pel domini
  de staging actual, per disseny.
- `ALLOWED_HOSTS` efectiu inclou `.fhorttextile.tech` (`settings.py:25`) → el 404 és **per
  tenant, no per host**. Afegir el Domain seria suficient per aquesta capa.

**Infra:** `.env` → `DB_NAME=ftt_staging`, `DB_USER=ftt_staging`, `DB_HOST=127.0.0.1`,
**`DB_PORT=5433`**, `DEBUG=True`, `ALLOWED_HOSTS=staging.fhorttextile.tech,localhost,127.0.0.1`.
`/etc/systemd/system/ftt-staging.service` → `gunicorn --workers 2 --bind 127.0.0.1:8001`,
`User=www-data`, `WorkingDirectory=/var/www/ftt-staging/backend`. **Un sol gunicorn serveix
tenants i public.**

### ¿Es pot fer login-flow avui?

**Pel domini `stagingbackoffice`: NO** (cau a l'app assessment / 404 de tenant).

**Prova de control — la capa d'aplicació funciona:**
`curl -H "Host: localhost" http://127.0.0.1:8001/api/backoffice/v1/health/` → **200**
`{"status":"ok","scope":"backoffice"}`. Igual amb `Host: backoffice.fhorttextile.tech` → 200.

**Usuaris a `public.auth_user`:**
```
 id |      username      | is_staff | is_superuser | is_active |        last_login
  1 | fhort              |    t     |      t       |     t     | 2026-05-25 12:16:12+00
  2 | a.devant@fhort.cat |    f     |      f       |     t     | 2026-06-07 17:09:21+00
```

**Gate de login:** `backoffice/serializers.py:23-28` (`BackofficeTokenObtainSerializer.validate`)
rebutja qualsevol user sense `backoffice_profile` actiu (`AuthenticationFailed('Accés no autoritzat')`).
`public.backoffice_backofficeuser` té **1 fila**: `usuari_id=2` (`a.devant@fhort.cat`), `rol=ADMIN`,
`actiu=t`. → **Només `a.devant@fhort.cat` pot entrar**; el superuser `fhort` (id 1) seria rebutjat.

**Endpoint:** `POST api/backoffice/v1/auth/login/` → `BackofficeTokenObtainView` (SimpleJWT),
payload `{"username": "...", "password": "..."}` (`AUTH_USER_MODEL` no redefinit → `USERNAME_FIELD=username`),
retorna `{access, refresh}` amb claims `rol`/`nom`. Perfil: `GET .../auth/me/`. Health obert: `GET .../health/`.

**POST de login: NO EXECUTAT** — credencials no disponibles a la sessió. La resta de la
cadena està verificada (health 200 + gate llegit + fila de perfil existent), de manera que
el login és el **únic** pas sense evidència directa.

> **Veredicte B4: cal muntar-ho sencer.** Quatre peces absents, cap d'elles bloquejada per
> codi: (1) vhost nginx, (2) certificat LE, (3) fila `tenants_domain` → tenant `public`,
> (4) build de la SPA. A més, `frontend-backoffice/.env` apunta
> `VITE_API_URL=https://backoffice.fhorttextile.tech` (**PROD**), no a staging.

---

## B5 — Inventari de seed d'onboarding

### La distinció que ho governa tot

`settings.py:36-74`. **El que se sembra via `RunPython` en una migració de TENANT_APP neix
sol a cada schema nou** (django-tenants aplica les migracions en provisionar). **El que se
sembra via management command, no.**

Nota de topologia: `fhort.pom` viu a **totes dues** llistes (`settings.py:53-55`) → les seves
taules existeixen físicament al `public` i a cada tenant. `tasks`/`accounts` només a TENANT.

Tenants reals: `public.tenants_client` → `fhort|FTT|actiu` i `public|SYS|actiu`. **Un sol
tenant operatiu.**

### Catàlegs

| Peça | On viu | Qui la sembra | Reutilitzable? | Comptatge a `fhort` |
|---|---|---|---|---|
| `GarmentTypeGlobal` | SHARED + rèplica tenant (`pom/models.py:79`) | script | **NO** | 59 (public i fhort) |
| `GarmentType` | TENANT (`pom/models.py:385`) | script | **NO** | 19 (17 actius + 2 inactius) |
| `GarmentTypeItem` | TENANT (`tasks/models.py:280`) | script | **NO** | **57** ✓ |
| `POMGlobal` | SHARED + rèplica (`pom/models.py:8`) | script | **NO** | 125 (public i fhort) |
| `GarmentPOMMap` | TENANT (`pom/models.py:427`) | script | **NO** | 1529 |
| `TaskType` | TENANT (`tasks/models.py:21`) | **migració** `tasks/0025` | **SÍ** | **14** ✓ |
| `TimeSeed` | TENANT (`tasks/models.py:392`) | **migració** `tasks/0032` | **parcial** | 8 |
| `SizingProfile` | TENANT (`pom/models.py:809`) | script | **NO** | 26 |

- Les **17 famílies** esperades = els 17 `GarmentType` actius (els 2 inactius són el catàleg
  vell desactivat). **57 items** ✓. `grep` de creació de `GarmentType(`/`GarmentTypeItem(`/
  `POMGlobal(` a `*/migrations/` → **buit**: cap migració els sembra.
- Els sembra `pom/management/commands/restructure_garment_types_v2.py` (capçalera L1-14:
  "17 famílies + 57 items"; crea GarmentTypeGlobal + GarmentType + GarmentTypeItem + matriu
  `TaskTimeEstimate`). **`restructure_garment_types_v2.py:18` fixa `TENANT = 'fhort'` hardcoded**
  i les famílies/perfils són literals (`FAMILIES`, `PROFILES`, L28-45).
- **G9 confirmat:** `tasks/models.py:38` → `code = SlugField(max_length=50, unique=True)`.
  `tasks/migrations/0025_seed_canonical_task_types.py:2-3` documenta *"Idempotent:
  update_or_create PER CODE (mai per PK) → no remapeja les FK existents"*; el seed usa
  `update_or_create(code=code, …)` (`:29`) i `unseed` és noop (`:38-40`). El catàleg té **14**
  entrades i coincideix amb la BD.
- `TimeSeed`: `tasks/0032_distill_time_seeds.py` (RunPython `:54`) **destil·la** cel·les
  teòriques de `TaskTimeEstimate` via `update_or_create` (`:24`). La migració corre sola al
  tenant nou, però només produeix seeds si ja hi ha `TaskTimeEstimate` — que les sembra el
  script. **En un tenant nou net → 0 TimeSeed.**

### Config

- **`TenantConfig`** (`accounts/models.py:30`, TENANT, singleton). **Ningú el crea a
  l'onboarding**: es crea **lazy** via `get_or_create_default()` (`accounts/models.py:74-77`,
  `get_or_create(pk=1)`) al primer accés des de les vistes (`pom/s2_views.py:290`, s6/s8/s9/s10/s11…).
  Cap seed a cap migració. (`fhort.accounts_tenantconfig = 1`, creat pel primer accés.)
- **Perfils/rols:** `class Role` → **NO EXISTEIX**; tampoc s'usen `auth.Group` per als rols de
  tenant. El rol és un string lliure `UserProfile.rol_nom` (`accounts/models.py:12`) + `permisos`
  JSON (`:16`); el catàleg de capacitats viu en codi (`accounts/capabilities.py:28`,
  `DEFAULT_ROLE = "technician"`). El `UserProfile` es crea per **signal** en crear un `User`
  dins un tenant (`accounts/signals.py:20-33`, `post_save` → `get_or_create`, salta `public`).
  ⚠️ **No hi ha seed d'un primer admin**: un tenant acabat de néixer **no té cap usuari** fins
  que algú n'hi crea un fora de banda. (A `fhort`: admin=2, manager=1, technician=1.)
- **`Plan`** (`tenants/models.py:12`) → **SHARED (public)**, no per-tenant. Cap seed: es
  gestiona per CRUD des del backoffice (`backoffice/views_tenants.py:216` `PlanViewSet`, ADMIN).
  `Client.plan` és FK **nullable** (`tenants/models.py:109`) → un tenant pot néixer sense pla.

### Scripts (només llegits, mai executats)

**⚠️ Correcció a la premissa del brief — `reseed_tenant_fhort.py` ja és INERT.**
`pom/management/commands/reseed_tenant_fhort.py:84-87` → `handle()` fa `raise CommandError(...)`
**abans de tocar cap dada** (guard `:80-83`, capçalera `:1-7`). No pot fer mal avui.

Si es tragués el guard, **sí que és destructiu**: dins `transaction.atomic()` (`:216`), STEP 0
esborra en cascada `GradingException, GradingRule, SizingProfile, GradingRuleSet,
ClientMesuraPerfil, GarmentPOMMap, POMMaster` amb `.all().delete()` (`:228-239`); STEP B/C/D
en fan més (`:279`, `:315-316`, `:399`). Ordre: STEP 0 neteja → A `POMMaster` (1 per POMGlobal,
`:242-267`) → B `GarmentPOMMap` des d'Excel (`:276-306`) → C `GradingRuleSet`+`GradingRule`
des d'Excel (`:311-390`) → D `SizingProfile` expandint per grup (`:396-450`).

**Eix família mort confirmat:** crea `GarmentPOMMap(garment_type=gt, …)` (`:299-304`), eix
eliminat a la migració `pom/0016` (comentari `:3`, `:80-82`); l'eix viu és `garment_type_item`.
Petaria en crear.

Per què **no** és reutilitzable: (1) `--tenant default='fhort'` (`:73`) i llegeix Excels amb
rutes absolutes de fhort (`/root/fhort-sessions/…`, `:29-30`); (2) eix mort; (3) destructiu i
no idempotent-additiu.

**⚠️ Correcció a la premissa del brief — `seed_pom_maps_to_items.py` NO EXISTEIX**
(`find` → buit). Els fitxers propers són `pom/management/commands/author_baby_pom_maps.py` i
`load_map_inline.py`. La seva idempotència **PENDENT DE VERIFICAR** (fora d'abast d'aquesta peça).

### Seeds dins de migracions — inventari

De `grep -rn "RunPython" backend/fhort/*/migrations/`:

**Sembren catàleg i neixen sols amb el tenant nou** (app TENANT):
- `tasks/0020_seed_self_customer.py` → `Customer(is_self=True)` amb `codi=Client.codi_tenant`;
  salta `public` (`:14`). ⚠️ La capçalera (`:7-8`) avisa que **encara no està enganxat a
  l'onboarding com a pas independent** — només s'aplica perquè és migració.
- `tasks/0025_seed_canonical_task_types.py` → 14 `TaskType` (per `code`).
- `tasks/0032_distill_time_seeds.py` → `TimeSeed` (depèn de dades prèvies; vegeu sobre).
- `commerce/0002_seed_units.py`, `0005_seed_minute_unit.py`, `0007_seed_payment_terms.py` →
  unitats / minut / condicions de pagament.

**RunPython que NO són seeds** (transformacions): `pom/0021,0023,0030,0031,0032,0034,0035`,
`models_app/0027,0045,0050`, `tasks/0030`.

> **Frontera neta de l'onboarding:** neixen sols → **TaskType (14), self-Customer, unitats i
> payment-terms de commerce**. NO neixen sols → **tot el patronatge**: GarmentTypeGlobal /
> GarmentType / GarmentTypeItem, POMGlobal, GarmentPOMMap, SizingProfile, GradingRuleSet+Rule,
> matriu de temps. **Un tenant nou neix amb tasques però sense catàleg de peces.**

### Deute: schemes orfes

**On es crea un tenant:** `backoffice/views_tenants.py:56-79` (`ClientViewSet.create`). El
provisioning real és `serializer.save()` (`:67`) → `Client.save()` → `TenantMixin.save()` amb
`auto_create_schema = True` (`tenants/models.py:171`). No hi ha `create_schema` explícit ni
`Client.objects.create` fora d'aquí.

**`transaction.atomic()`: NO EXISTEIX** al voltant de la creació — i és **deliberat**.
Comentari explícit a `views_tenants.py:59-66`: *"la creació del tenant NO va dins
transaction.atomic… Compromís acceptat: si falla la creació del Domain, queda un Client +
schema orfe (cleanup manual)"*. El `Domain` es crea **després** del save (`:69`), fora de tota
transacció. `auto_drop_schema = False` (`tenants/models.py:172`) → esborrar un Client **no**
neteja el schema; el ViewSet ni tan sols exposa DELETE (`views_tenants.py:33-34`).

**Orfes reals a `ftt_staging`: CAP.** `pg_namespace` (excloent `pg_*`, `information_schema`,
`public`) → només `fhort`. Contrast amb `tenants_client` → cap schema sense fila, cap fila
sense schema. El risc estructural existeix; la BD està neta.

### Identitat canònica

- **`Customer.codi_global` — placeholder INERT, no un bug.** `tasks/models.py:201` →
  `codi_global = CharField(max_length=3, null=True, blank=True)`, amb comentari (`:199-200`)
  *"Ganxo per al registre global de codis del backoffice futur… Placeholder sense lògica en
  aquest sprint."* BD: `SELECT count(*), count(codi_global) FROM fhort.tasks_customer` →
  **3 total, 0 poblats**. Constraints de `tasks_customer`: només `UNIQUE(codi)` i PK. **Cap
  constraint sobre `codi_global`.**
- **`Client.codi_tenant` — VIU, poblat, únic.** `tenants/models.py:120` →
  `CharField(max_length=3, unique=True)`; constraint `tenants_client_codi_tenant_key`.
  `count=2, count(codi_tenant)=2` (`fhort=FTT`, `public=SYS`). És la font del self-customer:
  el `Customer(is_self=True)` de fhort té `codi='FTT'` (pont a `tasks/0020`, `:20`/`:43`).
  *(Nota menor: el docstring de `0020` posa `'FHT'` d'exemple; el real és `'FTT'`.)*

> **Veredicte B5:** el registre global cross-tenant **encara no està construït**. `codi_tenant`
> és l'eix canònic viu; `codi_global` és un ganxo declarat i buit.

---

## B6 — Resum executiu

### Taula d'estat

| Peça | Estat | Evidència | Risc per a la represa |
|---|---|---|---|
| Codi backoffice a dev | **VIU** (per davant de main, +1 commit) | `git diff --stat main dev` → només `reconcile_consumption.py` | Cap |
| Migracions backoffice | **VIU** | 4/4 `[X]`; `makemigrations --check` → `No changes detected` | Cap |
| Cadena de meritació | **VIU** | `services_c.py:150-178` → `receivers.py:7-18`; `--dry-run` → 0 forats | Cap **avui** (però vegeu T1) |
| Guard idempotència | **VIU** | `services_c.py:160-162`; camp a `models_app/models.py:204` | Cap |
| N10 no-fatal | **VIU** | `services_c.py:183-187` (`# NO re-raise`) | Cap |
| `reconcile_consumption` | **VIU** | `--dry-run` verificat no-escriptura (`:81-86,134-140`) i executat | Cap |
| Frontera commerce↔backoffice (estructural) | **VIU** | Cap import creuat, cap col·lisió, cap FK tenant↔public | Cap |
| **Frontera transaccional (T1)** | **🛑 TRENCAT** | `assign_work_order` a `services_c.py:182` dins l'atomic de meritació (`:159`) | **ALT** — un error de commerce reverteix la meritació SaaS, en silenci |
| `reconcile` depèn de commerce (T2) | **TRENCAT (llei)** | `reconcile_consumption.py:64` → `assign_work_order` → `commerce.models` | MITJÀ |
| Cicle d'imports `tasks ↔ commerce` (T3) | **VIU però lleig** | `services_c.py:65` ↔ `commerce/services.py:234` | BAIX |
| SPA `frontend-backoffice` | **TRENCAT (no construït)** | `npm run build` → `vite: not found`; no `node_modules`, no `dist` | MITJÀ — bloqueja tota UI |
| Django serveix la SPA | **NO EXISTEIX** | Grep `TemplateView\|index.html\|dist` a `backend/**.py` → cap | MITJÀ — cal decidir qui la serveix |
| vhost `stagingbackoffice` | **NO EXISTEIX** | `grep -rn stagingbackoffice /etc/nginx/` → exit 1 | **ALT** — bloqueja B4 sencer |
| Cert `stagingbackoffice` | **NO EXISTEIX** | `ls /etc/letsencrypt/live/` | ALT |
| `Domain` a `tenants_domain` | **NO EXISTEIX** | SELECT; `curl -H Host:` → `No tenant for hostname` | ALT |
| Login-flow a staging | **DESCONEGUT** | health 200 ✓, gate llegit ✓, perfil existeix ✓; **POST no executat** | BAIX (única baula sense prova directa) |
| Seed: TaskType / self-Customer / units | **VIU i reutilitzable** | migracions TENANT `tasks/0025`, `0020`, `commerce/0002,0005,0007` | Cap |
| Seed: catàleg de patronatge | **TRENCAT per a tenant nou** | cap migració el sembra; `restructure_garment_types_v2.py:18` `TENANT='fhort'` | **ALT** — un tenant nou neix sense peces |
| `reseed_tenant_fhort.py` | **INERT** (i destructiu si es desarma) | `raise CommandError` a `:84-87`; eix mort `:299-304` | BAIX (no pot córrer) |
| `seed_pom_maps_to_items.py` | **NO EXISTEIX** | `find` → buit | — (premissa del brief incorrecta) |
| Primer admin del tenant nou | **NO EXISTEIX** | cap seed; `UserProfile` només per signal en crear User | ALT — tenant nou sense ningú qui hi entri |
| `TenantConfig` a l'onboarding | **NO EXISTEIX** (es crea lazy) | `accounts/models.py:74-77` `get_or_create(pk=1)` | BAIX |
| Atomic a la creació de tenant | **NO EXISTEIX** (deliberat) | `views_tenants.py:59-66`, comentari de compromís acceptat | MITJÀ — 0 orfes avui |
| `Client.codi_tenant` | **VIU** | `tenants/models.py:120`, unique, 2/2 poblats | Cap |
| `Customer.codi_global` | **NO EXISTEIX (funcionalment)** | `tasks/models.py:199-201`; 0/3 poblats, cap constraint | MITJÀ — bloqueja registre global |

### 🛑 STOP declarats (segons el brief: anotats, no arreglats)

1. **T1 — contradicció de paradigma.** La llei "dues facturacions separades" es viola
   transaccionalment: codi de `commerce` (tenant) corre dins l'`atomic()` que merita la
   facturació SaaS (public), sota un `except` que empassa. `services_c.py:159-186`.
2. **Premissa del brief incorrecta ×2.** `reseed_tenant_fhort.py` ja està desarmat amb un
   `CommandError`; `seed_pom_maps_to_items.py` no existeix.

### Decisions Patró C necessàries abans de la fase 2

- **D1 (T1, urgent) — Desacoblar `assign_work_order` de l'atomic de meritació.**
  💡 PROPOSTA (a validar): treure la crida fora del `with transaction.atomic()` de meritació i
  donar-li el seu propi `try/atomic/except` — de manera que un error comercial deixi el forat
  d'encàrrec (recuperable pel reconcile B4a) **sense** revertir la meritació. Alternativa:
  `transaction.on_commit(...)`. Cal decisió humana; toca el node més sensible del sistema.
- **D2 (T2) — On viu el backfill d'encàrrecs.** ¿`reconcile_consumption` (SHARED) ha de seguir
  cridant lògica de `commerce`, o cal una comanda germana `reconcile_work_orders` al tenant?
  Avui una app `public` importa una app `tenant`.
- **D3 — Qui serveix la SPA del backoffice.** Django no la serveix i no hi ha symlink. Opcions:
  vhost nginx amb `root` al `dist` (com `ftt-staging`), o servir-la des de Django. Decideix
  també si `frontend-backoffice/.env` ha de deixar d'apuntar a **PROD**.
- **D4 — Muntar `stagingbackoffice`**: vhost + cert LE + fila `tenants_domain` → tenant `public`.
  Sub-decisió: ¿mateix gunicorn `:8001` (avui compartit) o procés separat? ¿`auth_basic` com a
  staging de tenant?
- **D5 — Estratègia de seed del catàleg per a tenants nous.** El patronatge no neix amb el
  tenant. Cal decidir: migració de dades TENANT idempotent (neix sol), o un command
  `bootstrap_tenant <schema>` parametritzat (substitut net de `reseed_tenant_fhort`). Inclou
  d'on surten les dades (avui: Excels a `/root/fhort-sessions/`).
- **D6 — Primer usuari d'un tenant nou.** Avui neix sense cap `User` → ningú hi pot entrar.
  ¿El crea el backoffice en provisionar? ¿Amb quin rol i quin flux de credencials?
- **D7 — `Customer.codi_global` i el registre global.** El ganxo és buit i sense constraint.
  Definir-ne semàntica, unicitat cross-tenant i qui l'assigna abans de desplegar el 2n tenant.
- **D8 (menor) — `atomic` a la creació de tenant.** El compromís està documentat i acceptat
  (`views_tenants.py:59-66`) i avui hi ha 0 orfes. Confirmar que segueix sent acceptable quan
  el provisioning creixi (seed de catàleg + primer usuari el fan molt més llarg → més
  superfície per a orfes).
