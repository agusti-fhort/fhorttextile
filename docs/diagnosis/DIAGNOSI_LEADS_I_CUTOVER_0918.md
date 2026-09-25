# DIAGNOSI — Leads (backoffice) + Pre-cut-over de l'apex

Data: 2026-09-18 · **Patró A (READ-ONLY)** · `178.105.48.204`, repo `/var/www/ftt-staging`,
branca `dev`. Cap escriptura de codi, BD ni config. La consulta a BD ha estat només `SELECT`
sobre `ftt_staging` (127.0.0.1:5433).

**Convenció:** cada afirmació porta `fitxer:línia`. `"NO EXISTEIX"` = confirmat absent al codi
(grep mostrat), no especulat. `💡 PROPOSTA (a validar)` = opció tècnica, no decisió.

## PAS -1 — Nota sobre `FTT-Brain/ESTAT_BACKOFFICE.md`

**No existeix enlloc del sistema** (`find / -xdev -iname "ESTAT_BACKOFFICE.md"` i
`-iname "FTT-Brain"` → buit als dos). `ESTAT_BACKOFFICE.md` SÍ està referenciat a `.gitignore:26`
(és un fitxer d'estat que, segons `CLAUDE.md`, "viu al servidor com a memòria de treball, no com
a codi") però **no hi és present en disc** — a diferència d'`ESTAT_PROJECTE.md`, que sí existeix
a l'arrel. El document viu més proper que sí existeix i confirma el principi rector citat al
brief ("backoffice = SHARED_APP sobre public") és `docs/diagnosis/DIAGNOSI_BACKOFFICE_POSTREFACTOR.md`
(2026-07-10): `settings.py:57-58` — `'fhort.backoffice'` dins `SHARED_APPS` amb el comentari
"NOMÉS public (mai a TENANT_APPS)". És on m'he basat per al context de fons; l'estat concret
(migracions, SPA, etc.) l'he reverificat avui perquè aquell doc té 2 mesos (veure A8).

---

# A · LEADS

## A1 — Patró `/api/backoffice/v1/pricing/public/`

**View** — `backend/fhort/backoffice/views_pricing.py`, function-based amb `@api_view`:
- `pricing_view` (línies 40-43): `@api_view(['GET'])` + `@permission_classes([IsAuthenticated])` (:41).
- `pricing_public_view` (línies 46-49): `@api_view(['GET'])` + `@permission_classes([AllowAny])` (:47).
- Helper comú `_pricing_response(request)` (línies 23-37) — la view pública i la privada criden
  la mateixa lògica.
- `authentication_classes`: **no sobreescrit** — hereta el `DEFAULT_AUTHENTICATION_CLASSES` global.
- `throttle_classes`/`throttle_scope`: **NO EXISTEIX** al fitxer (grep de "Throttle" → 0).
- Cache: **no és a la view**, és al servei — `backoffice/pricing_service.py:17` (`from django.core.cache
  import cache`), `:121-122` (`_cache_key`), `:125-152` `resolve_pricing()` → `cache.get` (:134),
  `cache.set(..., settings.PRICING_CACHE_TTL)` (:149), còpia "stale" sense TTL (:151) per degradar
  si Stripe cau (`PricingUnavailable`, :50-51).

**Muntatge**: `backoffice/urls.py:10` import; `:37` `path('pricing/public/', pricing_public_view,
...)`; `:39` `path('pricing/', pricing_view, ...)`. Aquest `urls.py` es munta a
`fhort/urls_public.py:51` → `path('api/backoffice/v1/', include('fhort.backoffice.urls'))`.
URL final: `/api/backoffice/v1/pricing/public/`.

## A2 — Resolució de tenant: nginx `Host: backoffice.fhorttextile.tech` → cau a public?

**Mecànica exacta** (llegida directament, no de memòria):
- `settings.py:97` `ROOT_URLCONF = 'fhort.urls'` (tenant) · `:98` `PUBLIC_SCHEMA_URLCONF =
  'fhort.urls_public'`.
- `settings.py:83-95` `MIDDLEWARE`; `:87` `django_tenants.middleware.main.TenantMainMiddleware`
  (just després de CORS, comentari `:84-85` explica per què: les preflight OPTIONS d'un origen
  diferent no s'han de bloquejar abans que hi arribi CORS).
- Codi del middleware (`backend/venv/lib/python3.14/site-packages/django_tenants/middleware/main.py`):
  `hostname_from_request` (:21-26) fa `request.get_host()` — el **Host header real que rep
  gunicorn**, sense normalitzar més enllà de treure `www.` i el port. `get_tenant` (:28-30) fa
  `Domain.objects.select_related('tenant').get(domain=hostname)` — **match EXACTE** contra la
  taula `tenants_domain`. `setup_url_routing` (:73-96) assigna `PUBLIC_SCHEMA_URLCONF` **només
  si** `tenant.schema_name == 'public'` (:94-96).
- `urls_public.py:51` munta `fhort.backoffice.urls`. `urls.py` (ROOT_URLCONF, tenant) **NO** munta
  `backoffice` — confirmat llegint el fitxer sencer (76 línies): cap `include('fhort.backoffice...')`.

**Estat viu de `tenants_domain` avui** (SELECT, `ftt_staging`, 127.0.0.1:5433):
```
              domain               | is_primary | schema_name |      nom
------------------------------------+------------+-------------+------------------
 178.105.217.125                    | f          | fhort       | FHORT Management
 backoffice.fhorttextile.tech       | f          | public      | FHORT System
 fhorttextile.tech                  | t          | fhort       | FHORT Management
 localhost                          | t          | public      | FHORT System
 los.fhorttextile.tech               | t          | los         | LOSAN
 stagingbackoffice.fhorttextile.tech | f          | public      | FHORT System
 staging.fhorttextile.tech           | f          | fhort       | FHORT Management
```
⚠️ **Això és la BD d'staging**; no tinc accés a la BD de PROD des d'aquí (fora d'abast del Patró
A i de les màquines a les quals arribo). Trec-ne l'ARQUITECTURA (compartida entre entorns via el
mateix `settings.py`), no l'estat literal de PROD — cal repetir aquest `SELECT` a PROD abans
d'executar cap peça.

**Resposta a la pregunta 2, amb el rastre:**
- **`backoffice.fhorttextile.tech`, avui, JA resol a `public`** — hi ha Domain amb aquest nom
  exacte → `urls_public.py` → `backoffice/urls.py` inclòs. Si nginx a l'apex fa
  `proxy_set_header Host backoffice.fhorttextile.tech;` (literal, no `$host`) en la ubicació
  `/api/`, la petició **SÍ** cauria a `public` i trobaria les rutes del backoffice, exactament
  igual que fa avui `stagingbackoffice` (vegeu vhost sota).
- **PERÒ si nginx passa el Host real (`fhorttextile.tech`, com fa `$host` a tots els vhosts
  existents del repo — `ftt-staging:28`, `stagingbackoffice:...`) SENSE reescriure'l**, la petició
  cauria sobre `fhorttextile.tech`, que **avui és `is_primary=True` → tenant `fhort`** (NO
  `public`). Amb `ROOT_URLCONF='fhort.urls'`, que no munta `backoffice` → **404** al Lead. Aquest
  és el conflicte real del Patró B: el domini apex, tal com està configurat avui, no és `public`.

**Precedent al mateix repo** (mateix problema, ja resolt un cop): `docs/diagnosis/
DIAGNOSI_LOGIN_CENTRAL_TENANT_DISCOVERY.md` — la "porta única" (`login.*`) necessitava exactament
això: (1) DNS del host nou, (2) `Domain.objects.get_or_create(domain=<host>, tenant=<public>)`
(runbook :219-227), (3) vhost nginx amb `/api/` → gunicorn:8001. El vhost real actual que ja fa
aquest patró és `/etc/nginx/sites-available/stagingbackoffice` (existeix des del 07/2026, el
07-10 el doc `DIAGNOSI_BACKOFFICE_POSTREFACTOR.md` deia que NO EXISTIA — **ha canviat des
d'aleshores**): `root /var/www/ftt-staging/frontend-backoffice/dist; location /api/ {
proxy_set_header Host $host; proxy_pass http://127.0.0.1:8001; }` — usa `$host` real perquè el
Domain de `stagingbackoffice.fhorttextile.tech` ja apunta a `public` directament (no calia
reescriure Host). Al contrast, `/etc/nginx/sites-available/backoffice` **NO és aquest entorn** —
és `backoffice.webiafy.com` → Next.js a `:4324` (trampa de noms, ja detectada al 07/10, encara
vigent avui). Cap vhost nginx serveix `backoffice.fhorttextile.tech` en aquest servidor avui —
el Domain de BD existeix, però és "orfe" d'nginx.

**Alternatives** (💡 PROPOSTA, no decisió):
1. **Reescriure el Host només a la ubicació `/api/leads/`** del vhost nou de l'apex:
   `proxy_set_header Host backoffice.fhorttextile.tech;` (literal). Reutilitza el Domain que ja
   existeix (`public`, avui orfe d'nginx), sense tocar `is_primary` ni res del tenant `fhort`.
   Més quirúrgic. Efecte secundari: dins la view del Lead, `request.get_host()`/
   `build_absolute_uri()` retornarien `backoffice.fhorttextile.tech`, no l'apex real — irrellevant
   per un POST que respon JSON, però a anotar si mai es construeix un enllaç absolut des d'aquí.
2. **Moure `is_primary` de l'apex** (`fhorttextile.tech`) cap a `public` i deixar que `app.
   fhorttextile.tech` sigui la porta del tenant `fhort` (això és, de fet, el que ja demana el
   Patró B — vegeu B10). Si es fa, cal Domain nou `fhorttextile.tech → public` (pot coexistir amb
   `is_primary=False`, ja que la unicitat de schema resolution és pel `domain` exacte, no per
   `is_primary` — aquest camp només l'usa `get_primary_domain()`/`resol_host()`, vegeu B10) I un
   Domain `app.fhorttextile.tech → fhort` (avui **NO EXISTEIX** — cap fila amb aquest nom). Aquesta
   opció acobla LEADS amb el cut-over sencer (B); l'opció 1 no.
3. Muntar l'endpoint del Lead directament sota `urls.py` (tenant `fhort`) en lloc de `backoffice`
   — descartat: trenca la llei "backoffice NOMÉS public" i duplica el Lead per tenant sense
   necessitat (un Lead de marketing no és d'un tenant concret).

## A3 — Throttling DRF

- `settings.py` bloc `REST_FRAMEWORK` (~:298-319): `DEFAULT_AUTHENTICATION_CLASSES` (299-307),
  `DEFAULT_PERMISSION_CLASSES=[IsAuthenticated]` (308-310), `DEFAULT_FILTER_BACKENDS` (311-315),
  paginació (316-317), `DEFAULT_SCHEMA_CLASS` (318). **`DEFAULT_THROTTLE_CLASSES`/
  `DEFAULT_THROTTLE_RATES` NO EXISTEIXEN** (grep "THROTTLE" a `settings.py` → 0 resultats).
- Tampoc hi ha `CACHES` configurat a `settings.py` (grep → 0) → cache backend per defecte
  (`LocMemCache`, per procés — rellevant per A1, la cache de `pricing_service` no sobreviu a un
  restart ni és compartida entre workers gunicorn).
- Usos existents (`grep -rn "Throttle" backend/fhort`, exclosos tests/migracions):
  - `tenants/views_auth_central.py:56` `AuthCentralRateThrottle(SimpleRateThrottle)`, `scope=
    'auth_central'` (:67), `get_rate()` retorna `'20/hour'` HARDCODED (:69-70, comentari explícit
    "sense dependre de DEFAULT_THROTTLE_RATES, que el projecte no defineix"). Usat a
    `AuthCentralView` (:96) i `AuthCentralTriaView` (:135).
  - `tenants/views_discovery.py:25` `DiscoveryRateThrottle(SimpleRateThrottle)`, `scope='discovery'`
    (:28), `get_rate()` → `'10/hour'` (:30-31). Usat a `TenantDiscoveryView` (:39).
- **`pricing_public_view` NO té throttle** — no és el patró a seguir per Leads (formulari públic,
  exposat a spam/abús). El patró correcte és el de discovery/auth-central: subclasse pròpia de
  `SimpleRateThrottle`, `scope` + `get_rate()` fix.

## A4 — Correu

- `EMAIL_BACKEND`: **NO EXISTEIX a `settings.py`** (grep → 0; l'únic resultat de "mail" al fitxer
  és `:206`, `'fhort.accounts.backends.EmailOrUsernameBackend'`, que és backend d'AUTENTICACIÓ,
  no de correu). Sense override, Django cau al `smtp.EmailBackend` per defecte, sense host/port/
  credencials enlloc.
- `DEFAULT_FROM_EMAIL`: **NO EXISTEIX** com a setting (grep → 0). Únic rastre: comentari a
  `tenants/discovery_service.py:76` `from_email=None,   # DEFAULT_FROM_EMAIL` — delega a un
  setting que tampoc està definit (cauria al `webmaster@localhost` per defecte de Django).
- `backend/.env.example` (19 línies, llegit sencer): `SECRET_KEY, DEBUG, ALLOWED_HOSTS, DB_NAME,
  DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, ANTHROPIC_API_KEY`. **Cap variable `EMAIL_*` ni
  `DEFAULT_FROM_EMAIL`** (grep "mail" al fitxer → 0).
- `send_mail(`: **únic ús a tot el repo** — `tenants/discovery_service.py:73-79`, dins
  `send_discovery_email(email, workspaces)` (:66): `subject="El teu accés a FHORT Textile Tech"`
  (:74), cos de `build_discovery_email()` (:47-63), `from_email=None` (:76), `fail_silently=True`
  (:78), tot dins `try/except Exception` (:72, :81-83) perquè un fallo SMTP no alteri la resposta
  HTTP uniforme (privadesa — capçalera del fitxer :4-7).
- `EmailMessage(`: **NO EXISTEIX** cap ús (grep combinat `send_mail(\|EmailMessage(` → només la
  línia de dalt).
- **El pas "SMTP real" de la porta única NO consta com a fet enlloc.** Apareix com a ítem 4 de
  "PENDENT (manual, a PROD)" tant a `DECISIONS.md:612` com al snapshot citat al brief,
  `docs/ordres/DECISIONS_snapshot_2026-08-22.md:1234` (mateix text literal): *"SMTP real — sense
  ell el correu és fum (resposta uniforme funciona, però ningú rep res)"*. Ho confirmen també, de
  forma independent, dues diagnosis de disseny anteriors: `docs/diagnosis/
  DIAGNOSI_LOGIN_UNIC_2026-07-22.md:197,444,560` ("SMTP: EMAIL_* NO EXISTEIX... NO EXISTEIX") i
  `docs/diagnosis/DIAGNOSI_LOGIN_CENTRAL_TENANT_DISCOVERY.md:146,261-263` (mateixa conclusió,
  2026-07). **Cap d'aquests tres documents, en cap data, diu que s'hagi fet.** El patró de correu
  a reutilitzar per Leads és el de `discovery_service.py`: `send_mail` + `from_email=None` +
  `try/except` que no faci fallar la resposta pública — però primer cal decidir `EMAIL_BACKEND`/
  `DEFAULT_FROM_EMAIL` reals (avui cap dels dos formularis públics existents en depèn de veritat).

## A5 — IP real del client

Helper únic: `backend/fhort/backoffice/legal_service.py:7-17`, `client_ip(request)`:
- `:12-16` llegeix `X-Forwarded-For`, pren la PRIMERA entrada (`xff.split(',')[0].strip()`).
- `:17` fallback a `REMOTE_ADDR`.
- Docstring (:8-11) documenta explícitament l'assumpció: nginx és l'únic proxy de confiança
  (`proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for` estàndard).
- Consumit a `legal_service.py:54` dins `record_acceptance()` (`ip=client_ip(request)`).
- `grep -rn "X-Forwarded-For\|REMOTE_ADDR\|get_client_ip" backend/fhort` → **totes** les
  ocurrències són en aquest únic fitxer. Cap altre helper `get_client_ip` al repo. **Reutilitzar
  `fhort.backoffice.legal_service.client_ip` directament per al Lead** si es vol registrar IP
  (p. ex. consentiment RGPD del formulari).

## A6 — `LegalDocumentVersion` vigent i endpoint públic

Model — `backend/fhort/backoffice/models.py`:
- `LegalDocument` (:577-601, `actiu` :594).
- `LegalDocumentVersion` (:604-669): `ESTAT_DRAFT`/`ESTAT_PUBLICADA` (:609-611), `numero_versio`
  (:617), `estat` (:620), `data_publicacio` (:621). Immutable un cop publicada: `save()` (:638-650)
  i `delete()` (:652-656) llancen si `estat==PUBLICADA`. `publica()` (:658-669) calcula `sha256` i
  segella.
- `VersionQuerySet` (:569-574) bloqueja esborrat massiu si el conjunt conté cap versió PUBLICADA
  (:572).
- `LegalAcceptance` (:672-712, `UniqueConstraint` :696-698).

Query de "vigent" — `legal_service.py:20-28`, `vigents_publicades()`: per cada `LegalDocument`
`actiu=True`, l'última versió amb `estat=ESTAT_PUBLICADA` ordenada per `-numero_versio`.

**Endpoint públic que la serveixi: NO EXISTEIX.** Verificat:
- `LegalDocumentVersionViewSet` (`urls.py:31` com a `legal/versions`, `views_legal.py:29-64`) →
  `permission_classes` (:33) = `ADMIN` (`ADMIN = [IsAuthenticated, HasBackofficeRole(['ADMIN'])]`,
  :19). No públic.
- `LegalActionViewSet.pending` (`views_legal.py:83-89`, `urls.py:43`) també `ADMIN` (:81) i exigeix
  un `client` de backoffice (:84-87) — no serveix a un visitant anònim.
- `views_legal_tenant.py:18-39` (`legal_accept_tenant_view`) és `IsAuthenticated` de TENANT i
  només ACCEPTA, no llegeix contingut.
- `grep -rn "AllowAny" backend/fhort/backoffice/views_legal*.py` → 0 resultats.

**Conclusió:** hi ha model+query sòlids, però cap peça pública per mostrar la versió vigent d'un
document legal a un formulari anònim. **Cal construir-la** si el Lead ha de citar/enllaçar la
versió de privacitat acceptada.

## A7 — SPA `frontend-backoffice/`: com afegir-hi "Leads"

- **Router** — `frontend-backoffice/src/App.jsx`: imports (2-14, p. ex. `TenantsPage` :5); rutes
  dins `<Routes>` (19-41), les privades dins `<Route element={<Layout/>}>` (23-38); exemple
  `<Route path="/tenants" element={<TenantsPage/>}/>` (:25). Per afegir Leads: nou
  `src/pages/LeadsPage.jsx`, import (~:14), `<Route path="/leads" .../>` (~:34, abans del
  tancament :38). Comentaris a :26/:35 avisen que les rutes estàtiques (`/new`) han d'anar SEMPRE
  abans de les dinàmiques (`:id`).
- **Sidebar** — `frontend-backoffice/src/components/Sidebar.jsx`: array `SECTIONS` (26-43),
  secció "GESTIÓ" (29-37, p. ex. `{to:'/tenants', label:'Tenants', icon:'ti-building-store'}`
  :31). Afegir un ítem nou (~:37). Renderitzat automàtic per `SECTIONS` (128-135) + `NavLeaf`
  (45-72) — no cal tocar res més.
- **i18n**: `i18next`+`react-i18next` (package.json). **Un ÚNIC fitxer** `src/i18n.js` (NO hi ha
  `locales/` ni JSON per idioma) amb tres objectes literals `ca`/`es`/`en` (9-27/29-47/49-67);
  `DEFAULT_LANGUAGE='ca'` (:7), `SUPPORTED_LANGUAGES` (:6). **Ús real molt limitat**: només el
  namespace `login.*` existeix i només `LoginPage.jsx` crida `useTranslation` — `TenantsPage.jsx`,
  `Sidebar.jsx`, `LegalDocsPage.jsx` tenen text pla en català, sense `t()`. ⚠️ Contrast: la llei
  d'`CLAUDE.md` arrel ("i18n-gate ca/en/es a tota UI nova") cita explícitament
  `frontend/src/i18n/{ca,en,es}.json` — el patró de la SPA **de client**, no del backoffice. El
  backoffice té mecanisme propi i la majoria de pantalles ja existents NO el segueixen. Ho anoto
  com a inconsistència a decidir (Patró C), no la "corregeixo" silenciosament aquí.
- **Pàgina a clonar — `TenantsPage.jsx`** (223 línies): `load()` (`useCallback`, 57-83) crida
  `getTenants(params)` de `api/tenants.js`; fallback mock NOMÉS en `import.meta.env.DEV` (67-74,
  comentari :76 "mai dades inventades" en staging/PROD real); `useEffect` disparador (:85);
  estats loading/error/buit/taula (160-219); tabs de filtre des de `config/estats.js` (:11,
  136-157); files amb navegació a detall (:191) i acció "Veure detall" (200-213); `Badge({estat})`
  (32-43) és etiqueta d'ESTAT de fila, no comptador; capçalera amb "Refrescar" + "Nou tenant"
  condicionat a rol ADMIN (93-116). API: `api/tenants.js:7-8`
  (`client.get('/api/backoffice/v1/tenants/', {params})`).
- **Badge/comptador al sidebar: NO EXISTEIX.** `grep -rn "badge\|Badge\|counter\|unread\|pending"
  src` dins `frontend-backoffice` → cap ocurrència a `Sidebar.jsx`; els únics `Badge` són
  etiquetes d'estat per fila a `TenantsPage.jsx:32`, `TenantDetailPage.jsx:78`,
  `LegalDocsPage.jsx:22` (no comptadors). Sense polling ni query de "pendents" enlloc del
  backoffice. Si es vol un badge de "Leads nous" caldrà construir-lo de zero (patró net-new).

## A8 — Migracions `backoffice`

Directori `backend/fhort/backoffice/migrations/` (11 fitxers, ordenats): `0001_backoffice_users`,
`0002_model_consumption_event`, `0003_service_catalog_and_contracts`, `0004_invoice_and_lines`,
`0005_seedprofile`, `0006_legaldocument_legaldocumentversion_legalacceptance_and_more` (**aquí
neix el model legal d'A6**), `0007_invoiceserie_vatrate`, `0008_invoice_base_imposable_invoice_num
_seq_and_more`, `0009_modelconsumptionevent_exclos_and_more`, `0010_modelconsumptionevent_actor
_schema`, `0011_backfill_actor_schema_fhort`.

`python manage.py showmigrations backoffice` (executat, read-only):
```
backoffice
 [X] 0001_backoffice_users
 [X] 0002_model_consumption_event
 [X] 0003_service_catalog_and_contracts
 [X] 0004_invoice_and_lines
 [X] 0005_seedprofile
 [X] 0006_legaldocument_legaldocumentversion_legalacceptance_and_more
 [X] 0007_invoiceserie_vatrate
 [X] 0008_invoice_base_imposable_invoice_num_seq_and_more
 [X] 0009_modelconsumptionevent_exclos_and_more
 [X] 0010_modelconsumptionevent_actor_schema
 [X] 0011_backfill_actor_schema_fhort
```
**Totes 11 `[X]`, cap pendent.** (Nota: la diagnosi de 07/10 citada al PAS -1 en veia només 4 —
l'app ha crescut 7 migracions des d'aleshores, incloent-hi tot el mòdul legal i de facturació.
Confio en aquesta lectura d'avui, no en aquella.)

---

# B · PRE-CUT-OVER DE L'APEX (SPA `frontend/`)

## B9 — Inventari localStorage/sessionStorage/IndexedDB a `frontend/src`

**Cap ús d'IndexedDB** (grep → 0). Només `localStorage`/`sessionStorage`.

| Clau | Tipus | Escriu | Llegeix/esborra | Classificació |
|---|---|---|---|---|
| `access_token` | localStorage | `api/sessio.js:39`, `store/auth.js:62,77` | ~28 fitxers en lectura (App.jsx:223, authFetch.js:31, client.js:17, store/auth.js:49, etc.); esborrat `sessio.js:54`, `auth.js:43-44,127-128` | Credencial JWT — **NO és feina d'usuari** |
| `refresh_token` | localStorage | `sessio.js:43,` `auth.js:63,78` | `sessio.js:37`, `AvisSessio.jsx:43`; esborrat `sessio.js:55`, `auth.js:44,128` | Credencial — **NO és feina d'usuari** |
| `sidebarGroups` (JSON) | localStorage | `layout/Sidebar.jsx:166,252` | `layout/Sidebar.jsx:160` | Preferència d'UI cosmètica — sense impacte |
| `sessio_caducada` | sessionStorage | `api/sessio.js:58` | `pages/Login.jsx:49-50` (llegeix+esborra) | Senyal transitori de navegació; `sessionStorage` ja és per pestanya |
| `ftt_guard_llindar_min` / `ftt_guard_gracia_min` | localStorage | (extern, QA) | `GuardTascaOblidada.jsx:73-74` (`consumeixOverride`, llegeix+esborra d'un sol ús) | Override manual de QA, documentat com a d'un sol ús (:38-53) |

**⚠️ Claus de FEINA D'USUARI: CAP.** Revisió expressa de tots els editors amb estat potencialment
llarg (`TechSheetEditor.jsx`, `ModelSheet.jsx`, `CustomerDetail.jsx`, `EditorIntervals.jsx`,
`POMCataleg.jsx`, `SizeSystemDrawer.jsx`, `GraduacioSuperficie.jsx`, `JocsDeRegles.jsx`,
`PieceEdgeRoleList.jsx`, `fittingShared.jsx`): tot l'estat d'edició en curs viu en `useState` de
React i es persisteix per PATCH/autosave contra el backend (debounce 800ms-2s) — mai en storage
del navegador. `GuardTascaOblidada.jsx:38-43` documenta explícitament un cas on un override SÍ
va persistir més del compte en `localStorage` — tractat com a BUG a l'època, no com a disseny;
reforça que la convenció del projecte és "no localStorage per a estat de treball".

**Conclusió B9: el cut-over apex→`app.` NO fa perdre feina d'usuari.** Efectes reals: (a)
tancament de sessió — `access_token`/`refresh_token` són per-origen, cal re-login; (b) reset de
`sidebarGroups` (cosmètic). Cap pèrdua de dades.

## B10 — Usos del domini primari al backend

| Fitxer:línia | Ús | Depèn d'`is_primary`→apex? |
|---|---|---|
| `tenants/discovery_service.py:38` | `descobreix_workspaces`: `tenant.domains.filter(is_primary=True).first() or tenant.domains.first()` — decideix quin host s'ofereix al correu/resposta de discovery | **SÍ.** Si `is_primary` passa a `app.fhorttextile.tech`, el correu oferirà `app.` — és el comportament VOLGUT post-cutover, no un trencament |
| `tenants/auth_central_service.py:103` (`resol_host`, context :88-103) | Login central cross-tenant: si el host d'entrada no fa match exacte amb cap domini del tenant destí, cau a `is_primary` (o al primer domini). Comentari explícit (:89-91) sobre `staging.fhorttextile.tech is_primary=False` i el flux des de `login.*` caient al primari a PROD | **SÍ, el punt més sensible.** És el que decideix a quin host es redirigeix algú que entra per un host "neutre" (`login.*`). Si `is_primary` es mou abans que `app.fhorttextile.tech` serveixi realment la SPA, el redirect per defecte trenca (apunta a un host que no serveix res) |
| `tenants/auth_central_service.py:85` | `descriu_workspace` crida `resol_host(schema, request.get_host())` | Indirecta, mateixa nota |
| `backoffice/views_tenants.py:91` | Alta de tenant nou: `Domain.objects.create(domain=f'{codi}.fhorttextile.tech', ..., is_primary=True)` | **NO relacionat** — és el subdomini PER-TENANT (`<codi>.fhorttextile.tech`), no l'apex ni `app.`; a no confondre |

**Construcció d'URLs absolutes** (`grep -rn "build_absolute_uri\|request.get_host\|Domain.objects"
backend/fhort`): `accounts/views.py:219` (enllaç reset password), `tenants/views_auth_central.py:
85,126`, `patterns/serializers.py:55,399`, `models_app/ftt_document_views.py:51`,
`pom/s2_serializers.py:255`, `models_app/serializers.py:22,392`, `models_app/views.py:2865`.
**Totes són per-petició** (reflecteixen el `Host` real de la crida actual, no un valor de BD) —
**cutover-safe, cap canvi de codi necessari**, sempre que nginx a `app.` enviï `X-Forwarded-Proto`
igual que a la resta de vhosts (`settings.py:221`, `SECURE_PROXY_SSL_HEADER` — si no, `https://`
es tornaria `http://` dins pàgines servides per HTTPS).

**Conclusió B10:** només `resol_host` (i indirectament `discovery_service.py:38`) estan realment
acoblats a `is_primary`. Els dos passen a ser CORRECTES després del cutover — **amb una condició
de seqüència**: `app.fhorttextile.tech` ha de servir efectivament la SPA (vhost + Domain +
`root frontend/dist`) ABANS o AL MATEIX MOMENT que es mogui `is_primary`, si no el login central
per host neutre redirigeix a un lloc buit.

Nota afegida (no demanada explícitament però rellevant): `frontend/.env` (comentari :1-9) diu
que `VITE_API_URL` està **deliberadament sense valor** — el front per defecte és SAME-ORIGIN
(`client.js: import.meta.env.VITE_API_URL || ''`), **un sol build serveix qualsevol domini**
(django-tenants resol pel Host). És a dir: el build de `frontend/dist` **no necessita
recompilar-se** per servir-se des d'`app.` en lloc de l'apex — només cal el vhost+Domain nous.

## B11 — Ruta `/api/webhook`

**NO EXISTEIX.** `grep -rn "webhook" backend/fhort --include=*.py` → 0 resultats, revisats també
`urls.py` i `urls_public.py` directament (cap `path`/`re_path`/`router.register` amb "hook"). Cap
impacte en el cutover.

---

## Riscos

1. **A2 — el conflicte central.** L'apex `fhorttextile.tech` és avui `is_primary=True → fhort`
   (no `public`), a staging; cal verificar el mateix a PROD abans de dissenyar res. Sense
   resoldre'l (opció 1 o 2 d'A2), el POST del Lead a `/api/` des de l'apex cauria sobre el tenant
   equivocat i donaria 404 — **no és un forat de permisos, és un forat de resolució de tenant**
   (coherent amb la llei de memòria "PODA i no 403").
2. **B10 — seqüència del cut-over.** Moure `is_primary` sense que `app.fhorttextile.tech` ja
   serveixi la SPA trenca el redirect per defecte del login central (`resol_host`). Cal fer-ho en
   un ordre concret, no simultani a l'atzar.
3. **A4 — SMTP fictici.** Cap dels dos formularis públics existents (`discovery`) prova mai un
   enviament real (`fail_silently=True`). Si el Lead necessita AVISAR per correu de veritat
   (el brief ho demana: "avís per correu"), aquesta peça d'infra (EMAIL_BACKEND/DEFAULT_FROM_EMAIL
   reals) és un prerequisit, no un detall — porta 2+ mesos pendent sense moure's (22/08→18/09).
4. **A6 — cap endpoint públic legal.** Si el Lead ha de citar la versió de privacitat acceptada,
   cal construir la lectura pública abans de poder-la guardar amb sentit al model.
5. **A3 — sense throttle global.** Un Lead sense `SimpleRateThrottle` propi (patró discovery/
   auth-central) queda exposat a spam il·limitat — no hi ha cap xarxa de seguretat per defecte.
6. **Domain `backoffice.fhorttextile.tech` orfe d'nginx** (existeix a BD, cap vhost el serveix
   en aquest servidor) — irrellevant si s'usa l'opció 1 d'A2 (reescriptura de Host), rellevant si
   algú n'espera accés directe extern.

## Preguntes obertes (per al Patró C)

- A2: opció 1 (Host rewrite quirúrgic) vs. opció 2 (moure `is_primary`, acoblat al cut-over
  sencer)? Quin s'aplica primer, Leads (A) o el cut-over (B)?
- A4: qui proveeix les credencials SMTP reals i a on es desen (`.env` de PROD, gestor de secrets)?
  Quin `DEFAULT_FROM_EMAIL` (domini `fhorttextile.tech`)?
- A6: cal el Lead lligat a `LegalDocumentVersion` des del primer dia, o es pot ajornar (guardar
  només `ip`+`data` i afegir la versió acceptada en una peça posterior)?
- A7: s'adopta i18n complet per a "Leads" (trencant la pràctica actual majoritàriament sense
  `t()` al backoffice) o es manté consistent amb la resta de pantalles (català pla)?
- B10: confirmar a PROD (no verificable des d'aquí) l'estat real de `tenants_domain` abans de
  planificar l'ordre exacte dels passos.

## Estimació de peces per al Patró B (sense codi, només abast)

1. **Model `Lead`** (app `backoffice`, SHARED/public): camps mínims email+missatge+ip+data+
   versió-legal-acceptada (opcional, depèn d'A6); migració pròpia.
2. **Endpoint públic `POST`** a `backoffice/urls.py`, muntat via `urls_public.py` (patró A1: FBV
   `@api_view(['POST'])` + `AllowAny`), amb throttle propi (patró A3) i correu best-effort (patró
   A4, un cop hi hagi SMTP real).
3. **(Si s'aborda A6) Endpoint públic de lectura** de `LegalDocumentVersion` vigent — peça nova,
   no reutilitza res existent.
4. **Pantalla "Leads"** a `frontend-backoffice/` (patró A7: clonar `TenantsPage.jsx`, ruta+sidebar,
   sense badge existent a reutilitzar — si es vol comptador, és peça net-new).
5. **Infra manual (fora de codi, Patró C/Agus):** vhost nginx de l'apex a PROD servint l'Astro +
   `/api/` amb la decisió d'A2 aplicada; SMTP real; si s'opta per moure `is_primary`, Domain nou
   `app.fhorttextile.tech` + seqüenciar amb B10.
6. **NO cal tocar** `frontend/` (build same-origin ja fet, B10) ni `frontend/src` (B9, sense
   feina d'usuari en risc) ni res relacionat amb webhooks (B11, no existeixen).
