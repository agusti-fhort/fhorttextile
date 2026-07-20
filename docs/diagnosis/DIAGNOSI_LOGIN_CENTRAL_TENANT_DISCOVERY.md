# DIAGNOSI — Login central amb tenant-discovery

> Data: 2026-07-20 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`, schemes `fhort`/`public`.
> Abast: com fer que un usuari entri per una porta ÚNICA (sense teclejar subdomini) i el sistema el
> desviï al seu tenant. django-tenants resol l'schema pel HOST **abans** del login.
> Convenció: cada afirmació porta `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi** (no especulat).
> Nota: la secció "LOGIN CENTRAL AMB TENANT-DISCOVERY" de `DECISIONS.md` **NO és al repo** (ni a
> `/root/fhort-sessions/`); s'ha treballat amb l'enunciat resumit del brief.

---

## Resum executiu (conclusions que desbloquegen la decisió)

1. **El HOST mana abans que res.** `TenantMainMiddleware` (2n middleware del stack, `settings.py:87`) resol
   l'schema fent `Domain.objects.get(domain=<host>)` i, si el host **no té fila `Domain`**, llança **`Http404`**
   (FHORT no configura ni `DEFAULT_NOT_FOUND_TENANT_VIEW` ni `SHOW_PUBLIC_IF_NO_TENANT_FOUND`). Per tant una
   "porta neutra" només funciona si el seu host té una fila `Domain` → schema **public**.
2. **Els usuaris finals viuen DINS de cada tenant** (`django.contrib.auth` és a TENANT_APPS, `settings.py:64`):
   `auth_user` existeix per-schema. **El mateix email pot existir a >1 schema** de forma independent. No hi ha
   model d'usuari custom (`django.contrib.auth.models.User`), i `username == email` per convenció.
3. **NO EXISTEIX cap lookup email→tenant cross-schema** avui. PERÒ els tres blocs necessaris ja estan provats:
   enumerar tenants (`get_tenant_model().objects.exclude(schema_name='public')`), entrar-hi (`schema_context`),
   i buscar l'usuari (`User.objects.filter(email__iexact=…)`). Combinar-los és codi NOU.
4. **El schema public ja se serveix** (hosts `backoffice.` i `stagingbackoffice.` → public) amb el seu urlconf
   propi `fhort.urls_public` (`settings.py:98`). El discovery hi encaixa (endpoint public, cross-schema).
5. **Privadesa: cap throttling/rate-limit a tot el backend (NO EXISTEIX)** i **cap endpoint públic email→res**
   avui (cap oracle d'enumeració existent). El patró segur ja usat és el del password-reset: resposta uniforme,
   missatges genèrics (`accounts/views.py:220-249`). El discovery serà el PRIMER endpoint públic per email →
   ha de néixer enumeration-resistant i amb throttle propi.
6. **DNS/nginx: cap wildcard.** Tots els `server_name` són explícits; qualsevol host nou (porta neutra) exigeix
   **vhost nginx nou + registre DNS + fila Domain**. Django (`ALLOWED_HOSTS` inclou `.fhorttextile.tech`) i CORS
   (regex `^https://[a-z0-9-]+\.fhorttextile\.tech$`) **ja accepten qualsevol subdomini** — el coll d'ampolla és
   nginx + DNS + Domain, no el backend.

---

# BLOC P1 — Middleware de tenants (host → schema)

- **Stack:** `MIDDLEWARE` (`settings.py:83-95`); `django_tenants.middleware.main.TenantMainMiddleware` és el **2n**
  (`settings.py:87`), just després de CORS i abans de tota la resta (auth, sessions, csrf).
- **Resolució:** `TenantMainMiddleware.process_request` (`venv/.../django_tenants/middleware/main.py:32-53`):
  `connection.set_schema_to_public()` → `hostname_from_request` → `get_tenant(domain_model, hostname)` que fa
  `Domain.objects.select_related('tenant').get(domain=hostname)` (`main.py:28-30`) → `connection.set_tenant`.
- **Host desconegut:** `Domain.DoesNotExist` → `no_tenant_found` (`main.py:55-71`). Sense
  `DEFAULT_NOT_FOUND_TENANT_VIEW` ni `SHOW_PUBLIC_IF_NO_TENANT_FOUND` (cap dels dos a `settings.py` — confirmat
  absent) → **`raise Http404`** (`main.py:71`). `DisallowedHost` → `HttpResponseNotFound` (`main.py:39-41`).
- **URLconf per schema:** `ROOT_URLCONF='fhort.urls'` (tenant, `settings.py:97`) vs
  `PUBLIC_SCHEMA_URLCONF='fhort.urls_public'` (public, `settings.py:98`). El discovery ha de viure a `urls_public`.
- `TENANT_MODEL='tenants.Client'`, `TENANT_DOMAIN_MODEL='tenants.Domain'` (`settings.py:79-80`); `Domain` és stock
  (`tenants/models.py:223` `class Domain(DomainMixin): pass`).

**Veredicte P1:** el host és el discriminador dur. La porta neutra **necessita una fila `Domain`→public**; sense
ella, `Http404` abans de qualsevol vista.

# BLOC P2 — Auth actual (JWT, on viu l'usuari)

- **Login = SimpleJWT stock** `TokenObtainPairView` a `/api/token/`, registrat a **tots dos** urlconfs:
  `urls.py:18` (tenant) i `urls_public.py:25` (public). Sense serializer custom al camí de tenant.
- **Backend d'auth:** `AUTHENTICATION_BACKENDS` (`settings.py:147-149`) = `EmailOrUsernameBackend` custom +
  `ModelBackend`. `EmailOrUsernameBackend` (`accounts/backends.py:11-25`): prova `User.objects.get(username=…)`,
  sinó `email__iexact=…, is_active=True` — **només dins l'schema actual** (cap iteració de schemes).
- **Usuaris per-schema:** `django.contrib.auth` ∈ TENANT_APPS (`settings.py:64`) → `auth_user` a cada tenant.
  `fhort.accounts` és TENANT-only (`settings.py:66`), `UserProfile` = `OneToOne(User)` (`accounts/models.py:5-10`).
  `username=email, email=email` en crear (`create_tenant_admin.py:84`; API `accounts/views.py:121-134`).
- **Public ≠ usuaris de tenant:** `accounts/views.py:137-138` retorna `User.objects.none()` si schema='public'
  (guard). Els admins de backoffice són un concepte separat (`BackofficeProfile` sobre `auth.User` de public,
  `backoffice/models.py:26`), amb login propi (`BackofficeTokenObtainView`, `backoffice/views.py:22`).
- **Email multi-schema:** cap constraint global; un email pot ser usuari a `fhort` i a `los` alhora, independents.
- **SIMPLE_JWT** (`settings.py:225-232`): access 1h, refresh 7d, `UPDATE_LAST_LOGIN=True`. `DEFAULT_PERMISSION_CLASSES
  = IsAuthenticated` (`settings.py:210`) → un endpoint públic ha de posar `AllowAny` explícit.
- **Frontend:** el login viu a `store/auth.js:37-42` (`POST /api/token/ {username,password}`); `client.js:4`
  `baseURL=VITE_API_URL` (`frontend/.env:1 = https://staging.fhorttextile.tech`) → la SPA parla amb l'API del
  SEU host. Ruta `/login` i `/reset-password/:uid/:token` són **públiques** a la SPA (`App.jsx:245,247`).

**Veredicte P2:** login estàndard per-schema. Per desviar l'usuari cal saber en QUIN(s) schema(s) viu el seu email
— informació que avui no calcula ningú.

# BLOC P3 — DNS / nginx / hosts

- **Domains vius** (SELECT read-only a `tenants_domain ⋈ tenants_client`):

  | host | schema | primary |
  |---|---|---|
  | `fhorttextile.tech` | fhort | ✓ |
  | `staging.fhorttextile.tech` | fhort | — |
  | `178.105.217.125` | fhort | — |
  | `los.fhorttextile.tech` | **los** | ✓ |
  | `localhost` | **public** | ✓ |
  | `backoffice.fhorttextile.tech` | **public** | — |
  | `stagingbackoffice.fhorttextile.tech` | **public** | — |

- **nginx (tots explícits, CAP wildcard `*.fhorttextile.tech` — NO EXISTEIX):**
  - `/etc/nginx/sites-enabled/ftt-staging:2,75` `server_name staging.fhorttextile.tech;` → `root
    frontend/dist` (SPA), `location /api/` → `proxy_pass 127.0.0.1:8001` (gunicorn, `auth_basic off`); tota la
    vhost rere `auth_basic` excepte `/api/`, `/admin/`.
  - `/etc/nginx/sites-available/stagingbackoffice:3,9` `stagingbackoffice.fhorttextile.tech` → `root
    frontend-backoffice/dist`, `/api/` → `8001` (django-tenants resol per Host).
  - `los.fhorttextile.tech` té fila Domain però **cap vhost nginx** → inabastable via nginx de staging.
- **Backend permissiu a subdominis:** `ALLOWED_HOSTS` inclou `.fhorttextile.tech` (`settings.py:25`);
  `CSRF_TRUSTED_ORIGINS=['https://*.fhorttextile.tech']` (`settings.py:29-32`); CORS regex
  `^https://[a-z0-9-]+\.fhorttextile\.tech$` + `CORS_ALLOW_CREDENTIALS=True` (`settings.py:256-258`).
  `DEBUG=True` a staging (`.env:2`).
- **Domain rows es creen a l'onboarding:** `backoffice/views_tenants.py:90-91`
  `Domain.objects.create(domain=f'{codi_tenant.lower()}.fhorttextile.tech', tenant=…, is_primary=True)`.
  **NO EXISTEIX** fixture/seed de Domain.

**Veredicte P3:** una porta neutra nova (opció b) demana **3 peces manuals fora del meu límit**: registre DNS
(Nominalia) + vhost nginx + fila `Domain`→public. El codi/BD del discovery, en canvi, és provable ara mateix
apuntant a un host public ja existent amb `curl -H "Host: stagingbackoffice.fhorttextile.tech"` a `127.0.0.1:8001`.

# BLOC P4 — Precedent de lookup cross-schema

- **Backoffice NO entra mai als schemes de tenant** per llegir dades: `views_tenants.py:5` ("MAI s'entra al schema
  d'un tenant existent"); llegeix el registre public (`Client.objects…`, `views_tenants.py:59`). Únic
  `schema_context` a backoffice = schema emissor de factures (`invoice_pdf.py:21,50`) i `public` (`receivers.py:10`).
- **El patró "enumera tenants i entra a cada schema" SÍ existeix, però només a management commands:**
  `backoffice/management/commands/reconcile_consumption.py:55-70` — `TenantModel=get_tenant_model();
  tenants=TenantModel.objects.exclude(schema_name='public'); for t in tenants: with schema_context(t.schema_name):`.
  Mateix patró a `commerce/…/reconcile_work_orders.py:54,68`, `tasks/…/bootstrap_tenant.py:367,417`, etc.
- **Creació d'usuari dins schema:** `tasks/management/commands/create_tenant_admin.py:63,84`
  (`with schema_context(schema): User.objects.create_user(username=email, email=email, …)`), idempotent per
  `username=email` (`:68`), rebutja `public` (`:50-52`). El signal `create_user_profile`
  (`accounts/signals.py:19-33`) crea el `UserProfile` si `connection.schema_name != 'public'`.
- **Helper email→tenant: NO EXISTEIX** (cap grep de discover/resolve tenant per email). El password-reset és
  estrictament per-tenant, mai cross-schema (`accounts/views.py:195-249`).
- **`tenant_context` NO EXISTEIX** al codebase (s'usa `schema_context` sempre); `connection.set_schema` tampoc
  com a crida.

**Veredicte P4:** hi ha un patró canònic reutilitzable (enumerar+`schema_context`+match), avui només en commands.
El discovery el porta a una vista HTTP pública per primera vegada.

# BLOC P5 — Privadesa (rate-limit / enumeració)

- **Throttling/rate-limit/lockout: NO EXISTEIX** enlloc (`settings.py:204-220` sense `DEFAULT_THROTTLE_*`; cap
  `axes`/`ratelimit` a `requirements.txt`; l'únic `RateLimitError` és de l'API d'Anthropic,
  `tech_sheet_views.py:210`). → **Endevinar contrasenyes és il·limitat avui.**
- **`/api/token/` stock:** mateix missatge per usuari-desconegut i contrasenya-incorrecta ("No active account…") →
  no distingeix (bo), però sense throttle.
- **Backoffice login FILTRA:** `serializers.py:24-27` — creds vàlides però sense `backoffice_profile` actiu →
  missatge DIFERENT ("Accés no autoritzat"). Petita fuita (revela que un usuari+pass és compte vàlid de
  plataforma). Model a **no** copiar al discovery.
- **Password reset = patró segur a mirar:** `accounts/views.py:220-228` (`{'valid': bool}` i prou),
  `:231-249` (missatges genèrics, no revela existència; `_user_from_uid` retorna `None` en silenci `:208-217`).
- **Cap endpoint públic email→envia-link (NO EXISTEIX):** el `reset_link` és admin-side i retorna la URL a
  l'admin, no envia correu (`accounts/views.py:195-205`). → cap oracle d'email existent avui.
- **Email no cablejat:** cap `EMAIL_*` a `settings.py` (→ backend SMTP default `localhost:25`) i **cap `send_mail`
  a tot el codi**. Enviar correu real a staging és incert; el discovery ha d'enviar **best-effort** (una fallada
  d'SMTP MAI pot canviar la resposta uniforme ni filtrar).

**Veredicte P5:** el discovery és el primer email→acció públic; neix amb (1) resposta uniforme calcada del
password-reset, (2) enviament best-effort, i (3) throttle propi (net-new, perquè no n'hi ha cap).

---

## TAULA FINAL — EXISTEIX / FALTA / DIFERENT (per al CTO)

| # | Element | Estat | Àncora |
|---|---|---|---|
| P1 | Host desconegut → resposta | **Http404** (cap fallback public) | `django_tenants/middleware/main.py:71` |
| P1 | Porta neutra sense Domain | **404 abans de la vista** | `settings.py` (cap SHOW_PUBLIC_IF_NO_TENANT_FOUND) |
| P2 | Usuaris finals | per-tenant (`auth_user` per schema) | `settings.py:64` · `accounts/models.py:5-10` |
| P2 | Email a >1 schema | **possible** (cap unicitat global) | `backends.py:11-25` |
| P3 | Wildcard nginx `*.fhorttextile.tech` | **NO EXISTEIX** | `/etc/nginx/sites-enabled/*` |
| P3 | Django/CORS accepta subdominis | **SÍ** (`.fhorttextile.tech` + regex) | `settings.py:25,256` |
| P3 | Domain `los.` sense vhost nginx | **DIFERENT** (inabastable) | live DB + nginx |
| P4 | Helper email→tenant cross-schema | **NO EXISTEIX** | (grep buit) |
| P4 | Patró enumerar+schema_context | EXISTEIX (només commands) | `reconcile_consumption.py:55-70` |
| P5 | Throttling / rate-limit | **NO EXISTEIX** | `settings.py:204-220` |
| P5 | Endpoint públic email→link | **NO EXISTEIX** (cap oracle) | `accounts/views.py:195-205` |
| P5 | Patró resposta uniforme | EXISTEIX (password-reset) | `accounts/views.py:220-249` |
| P5 | Email cablejat (send_mail) | **NO EXISTEIX** | `settings.py` (cap EMAIL_*) |

---

## ⚠️ DECISIÓ PRESA PER DEFECTE — PENDENT DE VET D'AGUS

> Separada expressament dels fets. Decisió humana (Patró C); implementada per no bloquejar, revisable/vetable.

**Tria: OPCIÓ (b) — porta neutra NOVA (`login.`/`entrar.`) → schema public.** NO reassignar `staging.`/`app.`.

**Raonament (recolzat en la Fase 1):**
- Reassignar `staging.fhorttextile.tech` (opció a) el trauria del tenant **fhort**, al qual apunta avui (P3): la
  SPA es serveix des d'aquell host i `VITE_API_URL` hi està cablejat (`frontend/.env:1`). Migraria l'entrada VIVA
  del tenant fhort → trencaria bookmarks/hàbits + exigiria re-cablejar el frontend. Disruptiu.
- L'opció (b) és **additiva**: fhort manté `staging.fhorttextile.tech`; s'afegeix un host neutre nou → public.
  El backend JA accepta qualsevol subdomini (`ALLOWED_HOSTS .fhorttextile.tech`, CORS regex) → no toca settings.
- El cost de (b) és 3 peces manuals (DNS + vhost + Domain), **iguals** que caldrien per moure fhort a un subdomini
  nou en l'opció (a) — però sense trencar res viu. Cap dada de la Fase 1 inverteix la conveniència.

**Host neutre proposat:** producció `login.fhorttextile.tech`; staging `login.staging.fhorttextile.tech` (o
`entrar.staging.fhorttextile.tech`). El discovery viu a `fhort.urls_public` i es prova ara via host public existent.

---

## 💡 PROPOSTES (a validar — NO són fets)

- **💡 Contracte del discovery:** `POST /api/discovery/` (públic, `AllowAny`, a `urls_public`). Body `{email}`.
  Resposta SEMPRE uniforme (p.ex. `200 {"detail":"Si l'adreça està registrada, rebràs un correu amb l'accés."}`)
  idèntica per a 0, 1 o >1 tenants. Si l'email existeix a ≥1 schema → enviar correu (best-effort) amb el/s
  enllaç/os de workspace (per >1 = selector dins el correu). L'única revelació és al propi correu (només el
  titular de la bústia). Throttle `ScopedRateThrottle` propi (net-new). Reusa el patró
  enumerar+`schema_context`+`User.objects.filter(email__iexact=…, is_active=True)`.
- **💡 Frontend neutre:** ruta pública nova a la SPA (p.ex. `/entrar`) amb un sol camp email → POST discovery →
  pantalla de confirmació "revisa el correu" (uniforme, sense fuga). i18n ca/en/es.
- **💡 Passos manuals pendents (fora del límit dur — per a l'Agus):** (1) DNS a Nominalia del host neutre;
  (2) vhost nginx nou servint `frontend/dist` + `/api/`→8001; (3) `Domain.objects.create(domain=<host neutre>,
  tenant=<Client public>, is_primary=False)`. Fins llavors, provable només amb host header simulat.

---

## 🔧 RUNBOOK — PASSOS MANUALS PENDENTS (documentats, NO aplicats — límit dur)

> El codi/BD/tests d'FASE 3 estan fets i verds. Perquè la porta neutra funcioni **end-to-end cross-subdomini**
> calen aquestes 3 peces d'infra, que el brief prohibeix aplicar. Ordre suggerit i comandes exactes:

**1) DNS (Nominalia) — host neutre.** Alta d'un registre pel host neutre de staging apuntant a la mateixa IP
que la resta (`178.105.217.125`):
```
login.staging.fhorttextile.tech.   A   178.105.217.125
# (producció, quan toqui: login.fhorttextile.tech)
```

**2) Fila Domain → schema public** (a la BD de PROD/staging; el discovery viu a `urls_public`, que només se
serveix si el host resol al tenant `public`). Comanda de shell Django:
```python
# python manage.py shell
from fhort.tenants.models import Client, Domain
public = Client.objects.get(schema_name='public')
Domain.objects.get_or_create(domain='login.staging.fhorttextile.tech',
                             defaults={'tenant': public, 'is_primary': False})
```
> Sense aquesta fila, `TenantMainMiddleware` llança **Http404** (diagnosi P1) abans de la vista.

**3) vhost nginx** — esborrany (NO aplicat). Serveix la SPA (`frontend/dist`, la mateixa build; la ruta neutra
és `/entrar`) i proxia `/api/` a gunicorn:8001. django-tenants resol l'schema pel `Host` (→ public per la fila
del pas 2). Fitxer suggerit `/etc/nginx/sites-available/login-staging`:
```nginx
server {
    listen 80;
    server_name login.staging.fhorttextile.tech;

    root /var/www/ftt-staging/frontend/dist;
    index index.html;

    # La SPA (mateixa build). L'usuari arriba a /entrar.
    location / { try_files $uri $uri/ /index.html; }

    # API same-origin → gunicorn; el Host el resol django-tenants (→ public).
    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    # (afegir el bloc TLS/acme equivalent al de ftt-staging quan es certifiqui)
}
```
Després: `ln -s ../sites-available/login-staging /etc/nginx/sites-enabled/`, `nginx -t`, `systemctl reload nginx`.

**4) (recomanació) SMTP.** L'enviament del correu de discovery és **best-effort**; sense un `EMAIL_*` real
(diagnosi P5, avui cap `EMAIL_*` → SMTP `localhost:25`) el correu no sortirà, però la resposta uniforme i els
tests no en depenen. Per a producció, configurar `EMAIL_BACKEND`/SMTP i `DEFAULT_FROM_EMAIL`.

**Verificació sense infra (feta):** `curl -H "Host: stagingbackoffice.fhorttextile.tech"` a
`127.0.0.1:8099/api/discovery/` → 200 uniforme; el mateix a `Host: staging.fhorttextile.tech` (tenant fhort)
→ 404 (confirma que és public-only).
