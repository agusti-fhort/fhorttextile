# DIAGNOSI — Login únic (pantalla d'entrada central + redirecció al tenant)

> Data: 2026-07-22 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`, HEAD `0f49e36`.
> Abast: què cal per a una porta d'entrada ÚNICA on l'usuari posa email+contrasenya **un sol cop** i
> acaba DINS del seu tenant, amb sessió activa. Arqueologia del primer intent (vetat el 20/07),
> mecànica real de JWT × django-tenants, i encaix amb el baseURL same-origin d'avui.
> Convenció: cada afirmació porta `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi**
> (no especulat). Les propostes van marcades `💡 PROPOSTA (a validar)` i són decisió d'Agus.
> Entorn: aquesta màquina és **staging** (`178.105.48.204`). **PROD és una altra màquina**
> (`178.105.217.125`) sense SSH des d'aquí → tot el que digui de PROD va marcat
> **PENDENT DE VERIFICAR**.

---

## Resum executiu

1. **🔴 Hi ha un forat de seguretat VIU, avui, independent del login únic.** El JWT no porta cap
   claim de tenant (payload verificat: `{token_type, exp, iat, jti, user_id}`), la `SIGNING_KEY` és
   la `SECRET_KEY` global, i `JWTAuthentication` fa un `.get(pk=user_id)` cru sobre l'schema que ha
   fixat el **Host**. Prova executada: un token emès al tenant `fhort` per l'usuari id=1 **és
   acceptat al schema `public` com un usuari DIFERENT — el superusuari**. La regla real és
   *col·lisió de PK = suplantació*; avui només ho amorteix que `los` tingui 0 usuaris. Això
   s'agreuja amb cada tenant nou i **s'ha de tancar abans o alhora que el login únic**, no després.

2. **La variant (b) decidida per l'Agus no és desplegable amb el que hi ha: falta la peça central.**
   `/api/token/` SÍ existeix al schema public (`urls_public.py:27`) — però és el
   `TokenObtainPairView` de la llibreria sense subclassar, i autentica contra l'`auth_user` **del
   public** (usuaris de backoffice). Les contrasenyes dels usuaris de tenant no hi són. Una vista
   d'autenticació que validi credencials cross-schema **NO EXISTEIX**. És codi nou.

3. **Del primer intent no s'ha de "recuperar" res: hi és tot, i s'està servint.** No hi ha cap
   commit de reversió (`git log --diff-filter=D -- Entrar.jsx` → buit); els 3 commits del disseny
   (`7d71f2a`, `aff1452`, `af37b20`) són a `dev` **i a `origin/main`**. La reversió del 20/07 va ser
   **només d'infra a PROD**. `Entrar.jsx` viu, la ruta `/entrar` és a `App.jsx:244`, i el build
   d'staging la conté: **`staging.fhorttextile.tech/entrar` renderitza avui la pantalla vetada.**

4. **L'arquitectura que vol l'Agus (login com a RUTA dins l'únic build) ja està construïda al 95 %,
   i el que la bloqueja és una línia de backend.** `/entrar` és ruta pública fora del guard
   (`App.jsx:244`), amb i18n ca/en/es complet. Però `/api/discovery/` només viu a
   `urls_public.py:32` → des d'un host de tenant fa **404** (verificat per curl). Per tant **avui la
   pantalla es pinta però el submit peta**, i la llei S19 (validació visual a staging) **no es pot
   complir** sense això. Amb el baseURL same-origin d'avui (`e18b2de`), a PROD el vhost `login.*`
   pot servir el MATEIX `dist/` sense cap build addicional.

5. **`dist-login/` NO EXISTEIX** — enlloc del sistema de fitxers (`find /` → buit). **`dist-tenants/`
   tampoc** existeix a staging; és un concepte documentat que `e18b2de` fa innecessari. A
   `/etc/nginx/` d'aquesta màquina **no hi ha cap `location = /login` ni `location /login`**, ni
   actiu ni comentat, ni cap vhost de losan. El `location=/login` desactivat del brief ha de ser de
   **PROD** → **PENDENT DE VERIFICAR**.

6. **El correu del discovery és fum i sempre ho ha estat.** No hi ha cap `EMAIL_*` a `settings.py`
   (grep = 0); els valors efectius són els defaults de Django (`localhost:25`, sense listener). El
   flux acaba en un `connection refused` empassat per `fail_silently=True`
   (`discovery_service.py:78`). Això afecta també el reset de contrasenya.

7. **Contradicció documental a reconciliar (3 vies).** `DECISIONS.md:437` diu "✅ RESOLTA — porta
   neutra `login.fhorttextile.tech`"; `DECISIONS.md:294-304` diu "MORT… **Mor:** Entrar.jsx + ruta
   /entrar + **subdomini login**"; i el brief d'avui ressuscita `login.fhorttextile.tech`. A més la
   diagnosi del 20/07 **no està segellada** (segueix a l'arrel = vigent) tot i documentar un disseny
   mort, contra el que exigeix `CLAUDE.md`.

---

# BLOC B1 — Arqueologia del primer intent

## B1.1 — No hi ha reversió a git; el codi vetat és íntegre

| Hash | Data | Missatge | Fitxers |
|---|---|---|---|
| `7d71f2a` | 20/07 09:13 | `feat(tenants): endpoint públic de tenant-discovery (porta única) — FASE 3a` | `discovery_service.py`, `tests_discovery.py`, `views_discovery.py`, `urls_public.py` |
| `aff1452` | 20/07 09:23 | `feat(frontend): pantalla neutra "Entrar" (tenant-discovery) — FASE 3b` | `App.jsx`, `endpoints.js`, i18n ×3, `pages/Entrar.jsx` |
| `af37b20` | 20/07 09:25 | `docs(diagnosis): login central + tenant-discovery` | la diagnosi del 20/07 |

`git branch -a --contains aff1452` → `dev`, `origin/dev`, **`origin/main`** (hi van entrar pel merge
`0546eee`). `git log --all --diff-filter=D -- frontend/src/pages/Entrar.jsx` → **buit**: mai esborrat.

Viu avui a l'arbre: `frontend/src/pages/Entrar.jsx` (71 línies, `:10` `export default function Entrar()`,
`:21` crida `tenantDiscovery.submit`); ruta a `frontend/src/App.jsx:244` amb el comentari `:243`
*"Porta ÚNICA (tenant-discovery): pantalla neutra, se serveix al host neutre (→public)"*;
`frontend/src/api/endpoints.js:45-47`; claus i18n `discovery.*` a `frontend/src/i18n/ca.json:390-402`
amb paritat en/es; entrada a `docs/architecture/ARCHITECTURE_MAP.json:4249-4252`.

**Ningú hi navega:** `grep -rn "/entrar"` sobre `frontend/src`, `frontend-backoffice/src` i `backend`
retorna **només** la declaració de `App.jsx:244`. `Login.jsx` no hi té cap enllaç. És una **ruta
òrfena**, accessible només per URL directa.

**I s'està servint:** `frontend/dist/assets/index-*.js` (build del 22/07) conté `discovery.sent_title`.

## B1.2 — Per què es va revertir

Font única (no hi ha missatge de commit): `DECISIONS.md:294-312`.

- Motiu: **de producte/UX, no tècnic.** `:296-297` *"desplegat a PROD i revertit el mateix dia per
  ordre d'Agus **en veure'l en viu**"*. `:298-300` *"CAP pantalla prèvia, CAP fricció d'entrada…
  email+password com sempre → el sistema descobreix el tenant per sota → l'usuari arriba al seu
  espai AUTENTICAT. Zero passos nous."*
- **BO i reutilitzable** (`:302`): *"discovery_service (lookup cross-schema), throttle, tests"*.
- **MORT** (`:303-304`): *"Entrar.jsx + ruta /entrar + subdomini login. (revertit a PROD; retirar el
  codi en sprint de neteja)"* — **aquest sprint de neteja no s'ha fet**; d'aquí B1.1.
- Condicions per reimplementar (`:306-308`): Patró A propi (*"JWT emès per quin schema; seguretat del
  flux"* — exactament el BLOC B3 d'aquest doc) + **validació visual a staging**.
- **Llei S19** (`:310-312`, també citada a `:250`): *"tota decisió que afecti el FLUX D'ENTRADA o
  creï una PANTALLA sencera nova es valida VISUALMENT a staging abans de qualsevol pas a PROD. El
  vet sobre un informe escrit NO és vet sobre el producte — una UX no es pot vetar llegint."*

Nota de mètode que explica l'incident: a `DIAGNOSI_LOGIN_CENTRAL_TENANT_DISCOVERY.md:175-177` la
decisió es va marcar *"PRESA PER DEFECTE — PENDENT DE VET D'AGUS"* i es va implementar per no
bloquejar. El vet va arribar **després** del deploy.

## B1.3 — `dist-login/`, `dist-tenants/`, vhosts

- **`dist-login/` NO EXISTEIX**: `find / -maxdepth 6 -name "dist-login*"` → buit. Cap fitxer del repo
  el nomena. **`dist-tenants/` NO EXISTEIX** al filesystem (`frontend/` només té `dist/`).
- Referències documentals vives: `DECISIONS.md:513`, `docs/deploy.md:123`, `client.js:11`.
- `grep -rin "login" /etc/nginx/` (arbre sencer, inclosos `backups/` i `conf.d/`) → **3 línies, totes
  el mateix comentari** `auth_basic off; # el Django admin té el seu propi login`. Per tant a
  staging: `location = /login` **NO EXISTEIX**, `location /login` **NO EXISTEIX**, vhost de losan
  **NO EXISTEIX**.
- **PENDENT DE VERIFICAR (PROD):** el `location=/login` desactivat que apunta a `dist-login/` al
  vhost losan. No auditable des d'aquí.

## B1.4 — `login.fhorttextile.tech`

| Peça | Estat | Prova |
|---|---|---|
| DNS | **EXISTEIX** | `dig +short login.fhorttextile.tech A` → `178.105.217.125` (PROD) |
| vhost (staging) | **NO EXISTEIX** | absent de `sites-available/`, `sites-enabled/`, `backups/` |
| Certificat | **NO EXISTEIX** | `ls /etc/letsencrypt/live/` no en té cap `login.*` |
| Fila `Domain` (staging) | **NO EXISTEIX** | les 7 files són `localhost`, `backoffice.*`, `stagingbackoffice.*` → public; `fhorttextile.tech`, `staging.*`, `178.105.217.125` → fhort; `los.fhorttextile.tech` → los |
| Fila `Domain` (PROD) | **PENDENT DE VERIFICAR** | pendent nº1 de `DECISIONS.md:451` |

Sense fila `Domain`, `TenantMainMiddleware` (`settings.py:87`) llança **`Http404`**
(`SHOW_PUBLIC_IF_NO_TENANT_FOUND` **NO EXISTEIX** a settings). Verificat:
`curl -H "Host: login.fhorttextile.tech" .../api/schema/` → **404**.

> **Veredicte B1: no cal recuperar res — cal DECIDIR què es jubila.** El disseny vetat és sencer a
> `dev` i a `main`, servit a staging, i el deute de neteja de `DECISIONS.md:303-304` segueix obert.

---

# BLOC B2 — El backend de discovery, tal com és

## B2.1 — El flux

`POST /api/discovery/` (`urls_public.py:32` → `views_discovery.py:37`). `AllowAny`,
`authentication_classes = []`, `throttle_classes = [DiscoveryRateThrottle]` (`views_discovery.py:37-40`).

**NO EXISTEIX cap serializer**: `request.data.get('email')` en cru (`views_discovery.py:43`), **sense
cap validació de format** ni límit de longitud.

Nucli anti-enumeració (`views_discovery.py:48-55`, literal):

```python
try:
    workspaces = find_workspaces_for_email(email)
    if workspaces:
        send_discovery_email(email, workspaces)
except Exception:   # noqa: BLE001 — cap error intern pot alterar la resposta uniforme
    logger.exception("discovery: fallada interna (empassada per uniformitat)")
# SEMPRE la mateixa resposta, hi hagi 0, 1 o N workspaces.
return Response({'detail': DISCOVERY_UNIFORM_DETAIL}, status=status.HTTP_200_OK)
```

Verificat al codi (no assumit): el `return` és fora del `try` i de tota branca; un sol punt de sortida
amb constant de mòdul (`views_discovery.py:22`). Codis possibles: `200` sempre, `400` (email buit),
`429` (throttle).

**Fuga per timing (residual):** `send_mail` és **síncron dins la request** i **només** a la branca
"existeix". El cos és uniforme; el temps no.

## B2.2 — El lookup cross-schema

`discovery_service.py:22-44`. **NO EXISTEIX cap taula al public que indexi email→tenant**: és
iteració en viu amb `schema_context` sobre tots els tenants, **sense early-out a posta** (mitigació
de timing, comentat a `:24-26`):

```python
for tenant in Client.objects.exclude(schema_name=public):
    with schema_context(tenant.schema_name):
        exists = User.objects.filter(email__iexact=email, is_active=True).exists()
```

- Cost: **`1 + 3N + M`** sentències SQL (N = tenants no-public, M = matches). Avui **N = 2** →
  ~7-8 sentències per POST. A 100 tenants, ~300 sentències síncrones per petició **anònima**.
  Amb el throttle inefectiu (B2.3), és el vector de DoS del disseny.
- Camp: `email__iexact` + `is_active=True` (`:36`). Model d'usuari estàndard (`AUTH_USER_MODEL`
  **NO EXISTEIX** a settings). `username == email` és **convenció, no constraint**
  (`accounts/backends.py:14-22`) → un usuari amb l'adreça només al `username` seria invisible.
- **Cap filtre per estat del tenant** (`:34` només exclou public): un tenant en `onboarding` (avui
  `los`), `suspes` o `baixa` genera igualment enllaç. `Client.es_actiu` existeix i **no s'usa aquí**.
- Domini del correu: **de la BD**, `tenant.domains.filter(is_primary=True).first()` (`:38`).
  Conseqüència real: a staging el primari de `fhort` és `fhorttextile.tech` (`staging.*` és
  `is_primary=False`) → **des de staging el correu enviaria enllaços a PROD**.

## B2.3 — Els tres forats del backend

1. **SMTP: `EMAIL_*` NO EXISTEIX a `settings.py`** (grep = 0), ni a `.env`. Valors efectius en
   runtime: `EMAIL_BACKEND=smtp.EmailBackend`, `EMAIL_HOST=localhost`, `EMAIL_PORT=25`,
   `DEFAULT_FROM_EMAIL=webmaster@localhost`. **No hi ha listener al port 25.** El correu **mai
   s'envia**. Afecta igualment el reset de contrasenya (`PASSWORD_RESET_TIMEOUT`, `settings.py:145`).
2. **Throttle inefectiu:** `CACHES` **NO EXISTEIX** a settings → `LocMemCache` per defecte → el
   comptador de `10/hour` (hardcoded a `views_discovery.py:29`) és **per procés gunicorn**. Amb N
   workers el límit real és `10·N/h` per IP, i es reseteja a cada reload.
3. **Fallada silenciosa parcial:** si un `schema_context` peta (tenant en creació, schema absent),
   l'excepció puja i el `except Exception` de `views_discovery.py:52` se l'empassa **sencera** → el
   bucle mor a mig recorregut i es perden els workspaces restants, amb 200 uniforme i sense correu.

## B2.4 — Tests

`backend/fhort/tenants/tests_discovery.py`, **9 tests** (coincideix amb `DECISIONS.md:447`): servei
1/0/>1 (`:71-81`), `iexact` (`:83-85`), **resposta indistingible** (`:88-96`, el requisit dur), 400
(`:98-100`), correu només si existeix (`:103-109`), selector amb >1 (`:111-115`), throttle 429
(`:118-122`).

Buits: cap test del **contingut de la URL** del correu (la lògica primari-vs-fallback de `:38` no
està coberta), cap test de `is_active=False`, cap del camí d'excepció, i **cap de la ruta URL** (el
`_post` de `:66-68` ataca la vista directament, no passa per l'urlconf).

> **Veredicte B2: el SERVEI és bo i reutilitzable; el FLUX (correu) és fum.** `find_workspaces_for_email`
> és exactament la peça que la variant (b) necessita. Tot el que depèn del correu està mort fins
> que hi hagi SMTP real.

---

# BLOC B3 — Mecànica d'autenticació (el nucli)

## B3.1 — 🔴 El JWT no sap de quin tenant és — VERIFICAT EMPÍRICAMENT

Payload real, descodificat d'un token emès dins `schema_context('fhort')`:

```
HEADER:  {'alg': 'HS256', 'typ': 'JWT'}
PAYLOAD: {'token_type': 'access', 'exp': …, 'iat': …, 'jti': …, 'user_id': '1'}
```

**Cap claim de tenant ni d'schema.** `SIGNING_KEY` = `SECRET_KEY` global (verificat en runtime:
`api_settings.SIGNING_KEY == settings.SECRET_KEY` → `True`; `SIMPLE_JWT` de `settings.py:225-232`
no en defineix cap). Cap clau per tenant, cap `audience`/`issuer`.

`django.contrib.auth` és a **SHARED_APPS (`settings.py:41`) I a TENANT_APPS (`settings.py:64`)** →
hi ha una `auth_user` per schema, amb **PKs independents**.

`JWTAuthentication` (llibreria, `authentication.py:120-136`) fa un `.get(pk=user_id)` pelat sobre
l'schema **ja fixat pel Host** per `TenantMainMiddleware`, que és el **2n middleware**
(`settings.py:87`), abans que DRF miri el token.

**Prova executada (read-only, en procés):**

```
TOKEN emès a schema=fhort per user id=1 (a.devant@fhort.cat)
  -> validat a schema=los:    REBUTJAT (user_not_found)
  -> validat a schema=public: ACCEPTAT com a user id=1 username='fhort'
                              is_staff=True is_superuser=True
```

El rebuig a `los` **no és protecció**: `los` té **0 usuaris** (B3.4). La regla real és **col·lisió de
PK = suplantació**, i tots els `auth_user` comencen a l'id 1.

Atenuants d'avui (contingents, no estructurals): `urls_public` no exposa cap app de producte, i
`/api/backoffice/v1/` està gated per `HasBackofficeRole` (`backoffice/views.py:23-33`) — l'usuari
public id=1 no té perfil de backoffice. L'admin de Django va per sessió, no per JWT.

## B3.2 — Cap token es pot revocar

`SIMPLE_JWT` (`settings.py:225-232`): access 1 h, refresh 7 dies, `ROTATE_REFRESH_TOKENS: True`,
`BLACKLIST_AFTER_ROTATION: False`. **`token_blacklist` NO EXISTEIX a `INSTALLED_APPS`** (verificat en
runtime → `False`; absent de SHARED_APPS i de TENANT_APPS).

- Rotar sense blacklist **no revoca**: el refresh vell segueix vàlid. La rotació allarga, no protegeix.
- El `logout` (`store/auth.js:72-77`) és **només client-side**.
- Canviar la contrasenya **no** invalida cap JWT (`CHECK_REVOKE_TOKEN` no activat;
  `accounts/views.py:236-250` només fa `set_password`).

## B3.3 — Com podria viatjar la sessió entre orígens

**Estat actual:** dues claus i prou, `access_token` i `refresh_token` a `localStorage`
(`store/auth.js:40-41`; lectura a `:27` i `client.js:28`; esborrat a `:73-74` i `client.js:71-72`;
refresh a `client.js:108-113`). `localStorage` és **per-origen** → un token escrit a `login.*` **no
és llegible** des de `los.*`. **NO EXISTEIX** cap `postMessage`, iframe ni cookie que ho salvi.

**Cookies: NO EXISTEIX res.** Grep de `SESSION_COOKIE*`, `CSRF_COOKIE*`, `set_cookie`, `SameSite`,
`withCredentials`, `document.cookie` sobre `backend/fhort` i `frontend/src` → **0 resultats**.
`CORS_ALLOW_CREDENTIALS = True` (`settings.py:258`) és **lletra morta** avui.
Ja hi són: `CSRF_TRUSTED_ORIGINS` amb `https://*.fhorttextile.tech` (`settings.py:29-32`),
`SECURE_PROXY_SSL_HEADER` (`:167`), i `ALLOWED_HOSTS` amb `.fhorttextile.tech` (`:26`) → **un
subdomini nou no obliga a tocar settings**; el coll d'ampolla és nginx + DNS + fila `Domain`.

**Precedents de ticket signat a la casa (3 usos en producció):**
`signing.dumps(obj.id, salt=salt)` a `patterns/serializers.py:52`, consumit a `patterns/views.py:754-757`
amb `signing.loads(..., max_age=DOWNLOAD_TTL)` i captura de `SignatureExpired`/`BadSignature`; mateix
patró a `models_app/views.py:372-375` i `item_fitxer_views.py:113-116`. TTL 900 s
(`patterns/tests.py:1195`). Les vistes que el consumeixen van `AllowAny` amb
`authentication_classes=[]` a posta (`models_app/views.py:350`): **el permís ÉS el token**.
Signat amb la `SECRET_KEY` global → **es verifica igual des de qualsevol schema**, i a diferència del
JWT **el payload el decideixes tu (hi pots posar l'schema)**. Limitació: `signing.loads` **no és
d'un sol ús**, només caduca; **NO EXISTEIX** cap taula de nonces consumits.

**Precedent (b) — reset de contrasenya** (`accounts/views.py:196-206`): l'schema hi viatja **com a
HOST de la URL**, no dins el token (`url = f"{request.scheme}://{request.get_host()}/reset-password/{uid}/{token}"`,
comentat a `:199-201`). L'`uid` és una PK crua resolta contra l'schema del Host (`:210-220`) — el
**mateix defecte** que B3.1; que el `check_token` falli en un altre schema és **accident, no disseny**.

## B3.4 — Multi-workspace: l'estat real

```
public: 2 usuaris — id=1 'fhort' (superuser, email a.devant@fhort.cat)
                    id=2 'a.devant@fhort.cat'
fhort:  4 usuaris — id=1 a.devant@fhort.cat · id=13 Montse · id=14 Salva · id=15 Marta
los:    0 usuaris
```

- **`a.devant@fhort.cat` existeix a `public` (dos cops) i a `fhort`** → el cas multi-workspace és
  real avui, encara que sigui pel compte del CTO.
- **`los` no té cap usuari**: LOSAN està sembrat de dades però **sense ningú que hi pugui entrar**.
- Duplicat dins de public: `EmailOrUsernameBackend` captura `MultipleObjectsReturned`
  (`accounts/backends.py:20-22`) → al public **el login per email d'aquest compte no funciona**.
  El discovery usa `.exists()`, que no en pateix → **el correu prometria un accés que falla**.
- **Selector de workspace al frontend: NO EXISTEIX.** Cap component, cap ruta, cap estat. L'únic
  "selector" és la llista d'enllaços dins el correu (`discovery_service.py:50-55`).

## B3.5 — Signup: no existeix self-service

Cap ruta de registre públic a cap `urls.py`. L'inventari complet d'`AllowAny` és: discovery,
`password-reset/validate` i `/confirm` (`accounts/views.py:221,232`), `backoffice/health`,
`backoffice/pricing/public` i les descàrregues signades. **Cap crea usuaris ni tenants.**

L'alta de tenant va per backoffice amb rol **ADMIN** (`backoffice/views_tenants.py:52,64-67`):
`create()` (`:78-107`) desa el `Client` (dispara `auto_create_schema`), crea el `Domain`
`{codi}.fhorttextile.tech` (`:92-93`) i, si el pla és Free, llança `provision_free_tenant` en
**subprocés detached** (`:34-50`) → `bootstrap_tenant` + `create_tenant_admin`. El front fa polling
de `Client.estat`. `onboarding/status` (`pom/s9_views.py:11`) **no és alta de res**: és el checklist
de sembra d'un tenant ja existent.

> **Veredicte B3: la variant (b) és construïble, però NO amb el que hi ha.** Falten tres peces, i una
> d'elles (el claim de tenant) és un forat de seguretat que ja és viu avui.

---

# BLOC B4 — Encaix amb el build únic same-origin

## B4.1 — El router de la SPA

Rutes **públiques** (fora del guard): `/login` (`App.jsx:242`), **`/entrar` (`App.jsx:244`)**,
`/reset-password/:uid/:token` (`App.jsx:246`). Guard a `App.jsx:72-79`:

```
76:  if (estatAuth === AUTH_DESCONEGUT) return <PantallaEspera />
77:  if (estatAuth === AUTH_VALID) return children
78:  return <Navigate to="/login" replace state={{ from: location }} />
```

Estat de 3 valors a `store/auth.js:16-18`, `initAuth` a `:26-35`, disparat un sol cop a
`App.jsx:233-235`. `Login.jsx:57-59` recupera el `from`. Catch-all a `App.jsx:348` → tot el
desconegut va a `/` → guard → `/login`.

**`path="/"` està reclamat pel Shell protegit (`App.jsx:267`).** Per tant la idea "detectar `login.*`
i pintar la pantalla a l'arrel" xoca frontalment: caldria condicionar l'element de `:267`, i llavors
el `Dashboard` (`index`, `:272`) queda inabastable en aquell host.

**Detecció per host al frontend: NO EXISTEIX.** Grep de `window.location.hostname|host|origin` sobre
`frontend/src` → **una sola ocurrència**, i no decideix res (`ModelMilestones.jsx:67`, resol un enllaç
relatiu). El patró vigent és l'oposat: `client.js:3-19` documenta que el front **no ha de saber en
quin domini viu**.

## B4.2 — 🔴 El blocador de la validació visual a staging

`/api/discovery/` **només** existeix a `urls_public.py:32`; **NO és a `fhort/urls.py`**. Verificat
per curl contra gunicorn:8001:

| Host | schema | `POST /api/discovery/` | `POST /api/token/` |
|---|---|---|---|
| `staging.fhorttextile.tech` | fhort (tenant) | **404** | existeix (`urls.py:18`) |
| `stagingbackoffice.fhorttextile.tech` | public | **200** | **401** (vista viva) |
| `login.fhorttextile.tech` | — | **404** (host no resol) | 404 |

La ruta `/entrar` viu a la SPA **de tenant** (servida per `sites-enabled/ftt-staging` des de
`frontend/dist`), i la SPA del public és una altra (`frontend-backoffice/dist`) que **no té cap
pàgina Entrar** (grep de `entrar|discovery` a `frontend-backoffice/src` → cap resultat).

→ **`staging.fhorttextile.tech/entrar` pinta la pantalla i el submit fa 404.** Amb la restricció "cap
subdomini `staginglogin.*`", **la llei S19 no es pot complir sense tocar això.**

## B4.3 — Les rutes, host per host

`urls_public.py:23-41` (public): `admin/`, **`api/token/` (`:27`)**, `token/refresh/` (`:28`),
`token/verify/` (`:29`), **`api/discovery/` (`:32`)**, `schema/docs/redoc` (`:35-37`),
`api/backoffice/v1/` (`:40`).

`fhort/urls.py:14-36` (tenant): `admin/`, `api/token/` (`:18`), refresh (`:19`), verify (`:20`),
schema/docs/redoc (`:23-25`), `api/v1/` × 8 includes (`:28-35`). **`api/discovery/` NO HI ÉS.**

**El punt crític del brief, respost:** `/api/token/` **SÍ** existeix al public (`urls_public.py:27`)
— però és la vista de la llibreria sense subclassar, i autentica contra l'`auth_user` **del public**.
Un usuari de LOSAN no hi existeix. Per tant `login.*` **pot** servir el *discovery*, però **no pot ser
una pantalla de login real cross-tenant** tal com està. No és un bug: és el disseny
(`urls_public.py:4-6` ho diu explícitament).

## B4.4 — Vhosts i infra

`location /api/` real (`/etc/nginx/sites-enabled/ftt-staging:32-41`):

```nginx
location /api/ {
    auth_basic off;   # l'API ja té auth JWT pròpia; l'auth bàsica trencava les XHR
    proxy_pass http://127.0.0.1:8001;
    proxy_set_header Host $host;
    …
}
```

`proxy_set_header Host $host` → el Host real arriba a Django. **Un vhost `login.*` que copiés aquest
bloc funcionaria igual, i amb el baseURL same-origin (`e18b2de`) serviria el MATEIX `dist/` sense cap
build addicional.**

⚠️ `auth_basic` està actiu a `/` (`ftt-staging:12-13`) → validar `/entrar` a staging demanarà
l'htpasswd primer (no bloqueja, però cal saber-ho).

🔴 **TROBALLA D'INFRA (risc de runbook):** `/etc/nginx/sites-enabled/ftt-staging` **NO és un symlink**
— és un fitxer real (2845 B, 22/07) que ha **divergit** de `sites-available/ftt-staging` (2303 B,
6/07). A l'actiu hi ha `client_max_body_size 25M`, els logs `ftt_timing` i tot el bloc
`/protected-media/` (X-Accel-Redirect); al de `sites-available` no. **Editar `sites-available` no fa
res, i restaurar-lo com a symlink trencaria el media protegit.**

> **Veredicte B4: l'arquitectura "login com a ruta dins l'únic build" NO té cap blocador estructural
> — té un blocador d'una línia.** El que sí que és nou de trinca és la detecció per host (i és
> evitable: veure la proposta P2).

---

# Les dues variants, dimensionades

## Variant (a) — email → correu amb enllaços · **fallback**

Decidida per l'Agus com a enllaç secundari ("no sé el meu workspace").

**Ja construïda al 100 % en codi.** El que li falta **no és codi**, és operativa:

| Peça | Estat | Cost |
|---|---|---|
| Endpoint + servei + throttle + 9 tests | **FET** (`views_discovery.py`, `discovery_service.py`, `tests_discovery.py`) | 0 |
| Pantalla + i18n ca/en/es | **FET** (`Entrar.jsx`, `App.jsx:244`, `ca.json:390-402`) | 0 |
| Enllaç des de `/login` | **NO EXISTEIX** (ruta òrfena, B1.1) | ~1 h |
| `/api/discovery/` accessible des d'un host de tenant | **404** (B4.2) | 1 línia |
| **SMTP real** | **NO EXISTEIX** (B2.3) | infra — **sense això la variant (a) NO funciona** |
| Filtre d'estat de tenant + `CACHES` compartit | forats B2.3 | ~2-3 h |

## Variant (b) — email+contrasenya → autenticació → redirecció amb sessió · **decidida**

Aquesta és la que l'Agus vol com a camí principal. **No és desplegable avui**; li falten tres peces,
i cap és trivial:

| # | Peça que falta | Per què | Estat |
|---|---|---|---|
| 1 | **Vista d'autenticació cross-schema al public** | `/api/token/` del public valida contra l'`auth_user` del public (B4.3); les contrasenyes de tenant no hi són | **NO EXISTEIX** |
| 2 | **Claim de tenant al JWT + validació** contra `connection.schema_name` | sense això el token és intercanviable entre schemas (B3.1) — i això **ja és un forat viu** | **NO EXISTEIX** |
| 3 | **Trasllat de sessió entre orígens** | `localStorage` és per-origen (B3.3) | **NO EXISTEIX** |

### Les dues formes de fer viatjar la sessió (riscos)

**Opció β1 — cookie de domini pare (`.fhorttextile.tech`).**
- *Encaix:* **zero infraestructura existent** — cap cookie a tot el projecte (B3.3). El front viu de
  `localStorage` i l'interceptor Bearer de `client.js:28`; caldria repensar-ho sencer.
- *Riscos:* la cookie viatja a **tots** els subdominis, inclosos els de tenants aliens → un XSS a
  qualsevol tenant exposa la sessió de tots; obliga a CSRF real (avui l'API no en fa servir, va per
  Bearer); `SameSite`/`Secure`/`HttpOnly` a decidir de zero.
- *Veredicte:* canvi de paradigma d'auth. Car i ample.

**Opció β2 — ticket de bescanvi signat a la URL de redirecció.** `💡 PROPOSTA (a validar)`
- *Encaix:* **tres precedents en producció** (B3.3), mateixa `SECRET_KEY` global → verificable des de
  qualsevol schema, i **el payload el decideixes tu → hi pots posar l'schema**, que és justament el
  que li falta al JWT.
- *Forma:* login.* autentica → emet `signing.dumps({'schema','user_id','jti'}, salt='login-handoff')`
  amb `max_age` molt curt (30-60 s) → redirigeix a `https://<tenant>/entrada?t=…` → la SPA el
  bescanvia immediatament per un JWT normal contra el host del tenant → `history.replaceState` per
  treure'l de la URL.
- *Riscos:* **el ticket viatja per URL** → queda als logs d'nginx (`ftt-staging` té `access_log` amb
  format `ftt_timing`) i a l'historial del navegador; mitigat per TTL curt + un sol ús. **Però
  `signing.loads` NO és d'un sol ús** (B3.3): cal una taula de nonces consumits, que **NO EXISTEIX**.
  I sense blacklist (B3.2) un ticket bescanviat no es pot revocar.
- *Veredicte:* és el camí que millor encaixa amb la casa, però **no és gratis**: nonce d'un sol ús +
  claim de tenant són prerequisits, no extres.

### Multi-workspace (tria DESPUÉS d'autenticar, com decideix l'Agus)

Encaixa net amb β2: el ticket es pot emetre **després** de la tria. Falta tot el frontend
(**selector: NO EXISTEIX**, B3.4) i que la resposta d'autenticació retorni la llista de workspaces —
`find_workspaces_for_email` ja la sap calcular (`discovery_service.py:22-44`).

---

# 💡 PROPOSTA d'arquitectura (a validar per l'Agus)

**P1 — Tancar el forat del JWT ABANS del login únic.** Afegir `schema` al payload (subclassant
`TokenObtainPairSerializer`, patró que ja existeix a `backoffice/serializers.py:7`) i validar-lo
contra `connection.schema_name` a l'autenticació. És independent del login únic, arregla un forat
viu, i és **prerequisit** de β2. Els tokens existents caducarien en 1 h / 7 dies.

**P2 — Login com a RUTA, sense detecció per host.** En comptes de "si som a `login.*`, pinta X a
`/`", el vhost `login.fhorttextile.tech` pot fer que **`/` serveixi la pantalla d'entrada** amb un
`try_files` o un `rewrite` cap a la ruta de la SPA. Així el frontend **no ha de saber en quin domini
viu** (coherent amb `client.js:3-19`), s'evita el xoc amb `App.jsx:267`, i la ruta és validable a
staging com a `staging.fhorttextile.tech/<ruta>`. Cost: 0 línies de frontend nou, 1 directiva
d'nginx a PROD.

**P3 — Desbloquejar la validació visual (llei S19) amb una línia.** Muntar `api/discovery/` també a
`fhort/urls.py`. **Decisió de l'Agus:** exposa el lookup cross-schema des de qualsevol host de tenant.
El risc de privadesa és **el mateix** que a public (resposta uniforme `views_discovery.py:54-55` +
throttle `:25-33`); l'objecció és conceptual, no de seguretat — però **arreglar el throttle
(`CACHES`) hauria d'anar-hi junt**, perquè avui no reté (B2.3).

---

# Pla de deploy del vespre

**El login únic (variant b) NO pot entrar al deploy d'aquest vespre.** Li falten tres peces de codi
que no existeixen (B3/variant b) i una d'elles és un canvi de seguretat que vol el seu propi verd. El
que sí que pot viatjar aquest vespre és **l'Opció A (same-origin) sola**, que ja està verificada, i
que és precisament el que **desbloqueja** el login únic per a un sprint propi.

## Seqüència exacta — Opció A

1. **Push de `dev`** (el fa l'Agus des d'SSH; els agents no pushen). Pas 0 de `docs/deploy.md:13-19`:
   `git log --oneline origin/dev..dev` ha de tornar **BUIT** després. Ara mateix retorna
   `0f49e36` i `e18b2de` — **els 2 commits d'avui NO han viatjat**, i PROD desplega d'`origin/dev`.
   ⚠️ `dev` té sessions concurrents: revisar `git log --format='%h %an' origin/dev..dev` abans.
2. **A PROD, buidar `frontend/.env`.** `frontend/.env` és **gitignored** → **no viatja amb git**.
   Sense aquest pas el canvi no fa absolutament res a PROD. Comprovació: `grep VITE_API_URL
   frontend/.env` ha de sortir buit o comentat.
3. **Rebuild:** `cd frontend && npm run build`.
4. **Verificar** (ha de tornar **0**):
   `grep -rho "https://[a-z0-9.-]*fhorttextile.tech" frontend/dist/assets/ | wc -l`
5. **Repuntar el domini de tenant a `dist/`** (jubilació de `dist-tenants/`) — **PENDENT DE
   VERIFICAR** l'estat real del vhost a PROD abans de tocar-lo.
6. **Prova visual a PROD:** login i navegació a `fhorttextile.tech` i al domini de LOSAN.

## Per a l'sprint del login únic (no aquest vespre)

Ordre proposat, cada peça amb el seu verd: **P1** (claim de tenant + validació) → **P3** (discovery
al tenant urlconf + `CACHES`) → **validació visual a staging de la pantalla** (llei S19: sense això
no es toca PROD) → vista d'autenticació cross-schema + ticket β2 amb nonce d'un sol ús → selector de
workspace → infra de PROD (fila `Domain`, vhost, certbot, **SMTP**).

---

# TAULA FINAL — EXISTEIX / FALTA / RISC

| # | Peça | Estat | Font |
|---|---|---|---|
| 1 | Servei de lookup cross-schema | **EXISTEIX** | `discovery_service.py:22-44` |
| 2 | Endpoint `/api/discovery/` + throttle + 9 tests | **EXISTEIX** (només al public) | `urls_public.py:32`, `views_discovery.py`, `tests_discovery.py` |
| 3 | Pantalla d'entrada + i18n ca/en/es | **EXISTEIX** (òrfena) | `Entrar.jsx`, `App.jsx:244`, `ca.json:390-402` |
| 4 | Build únic que serveix qualsevol domini | **EXISTEIX** (avui) | `client.js:20`, commit `e18b2de` |
| 5 | `/api/token/` al schema public | **EXISTEIX** però valida contra l'`auth_user` del public | `urls_public.py:27` |
| 6 | Claim de tenant al JWT | **NO EXISTEIX** | payload verificat, B3.1 |
| 7 | Autenticació cross-schema des del public | **NO EXISTEIX** | B4.3 |
| 8 | Trasllat de sessió entre orígens | **NO EXISTEIX** | B3.3 |
| 9 | Selector de workspace (UI) | **NO EXISTEIX** | B3.4 |
| 10 | Blacklist / revocació de tokens | **NO EXISTEIX** | `INSTALLED_APPS` verificat, B3.2 |
| 11 | Nonce d'un sol ús per a tickets signats | **NO EXISTEIX** | B3.3 |
| 12 | SMTP real | **NO EXISTEIX** | B2.3 |
| 13 | `CACHES` compartit (throttle efectiu) | **NO EXISTEIX** | B2.3 |
| 14 | `dist-login/` · `dist-tenants/` | **NO EXISTEIXEN** (staging) | `find /` buit, B1.3 |
| 15 | vhost / cert / fila `Domain` de `login.*` | **NO EXISTEIXEN** (staging) · PROD **PENDENT** | B1.4 |
| 16 | Self-service de signup | **NO EXISTEIX** | B3.5 |

| # | RISC | Gravetat | Detall |
|---|---|---|---|
| R1 | **Token d'un schema acceptat en un altre com un usuari diferent** | 🔴 **Viu avui** | Verificat: token de `fhort` id=1 → acceptat a `public` com a superusuari (B3.1) |
| R2 | Cap token es pot revocar (ni per logout ni per canvi de contrasenya) | 🔴 | B3.2 |
| R3 | El correu de discovery mai s'envia | 🟠 | B2.3 — la variant (a) no funciona sense això |
| R4 | Throttle de 10/h inefectiu (LocMemCache per procés) | 🟠 | B2.3 — l'endpoint és anònim i fa 3N queries |
| R5 | Ticket signat a la URL → logs d'nginx + historial | 🟠 | mitigable amb TTL curt + un sol ús (que falta) |
| R6 | `sites-enabled/ftt-staging` no és symlink i ha divergit | 🟠 | B4.4 — risc real en qualsevol runbook d'nginx |
| R7 | Discovery no filtra per estat de tenant | 🟡 | `discovery_service.py:34` — tenants en baixa reben enllaç |
| R8 | Email duplicat: discovery promet accés que el login rebutja | 🟡 | `.exists()` vs `.get()`, B2.2/B3.4 |
| R9 | La pantalla vetada es serveix a staging i el codi és a `main` | 🟡 | B1.1 — deute de neteja de `DECISIONS.md:303` obert |

---

# Per a l'Agus — les decisions que aquest doc deixa a taula

1. **R1 s'arregla ara o s'arregla amb el login únic?** (recomanació del doc: ara, i és prerequisit).
2. **β1 (cookie de domini pare) o β2 (ticket signat)?** El doc dimensiona totes dues; β2 té
   precedents a la casa, β1 és canvi de paradigma.
3. **P3: s'exposa `/api/discovery/` des dels hosts de tenant?** Sense això la llei S19 no es pot
   complir amb la restricció de no crear `staginglogin.*`.
4. **El codi vetat del 20/07: es jubila o es recicla?** Avui és a `main` i es serveix a staging.
5. **Reconciliar `DECISIONS.md`**: `:437` ("✅ RESOLTA", porta neutra) contradiu `:294-304`
   ("MORT… mor el subdomini login"), i el brief d'avui ressuscita `login.fhorttextile.tech`. A més
   `DIAGNOSI_LOGIN_CENTRAL_TENANT_DISCOVERY.md` **no està segellada** tot i documentar un disseny
   mort — `CLAUDE.md` exigeix segellar-la i moure-la a `arxiu/`.
