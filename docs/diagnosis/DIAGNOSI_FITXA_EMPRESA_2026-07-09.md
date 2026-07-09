# DIAGNOSI — Fitxa Empresa (Sistema/General · TenantConfig): camps fiscals + logo

Data: 2026-07-09 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
Abast: per què (1) camps fiscals no persisteixen via formulari i (2) el logo no puja, a la
pantalla Sistema→General (`GeneralConfig.jsx` → `tenant_config_view`).
Convenció: `fitxer:línia` = fet verificat al codi · "NO EXISTEIX" = confirmat absent (no especulat).

---

## Resum executiu

1. **LOGO — causa EXACTA trobada (defecte viu a HEAD).** `tenantConfig.uploadLogo()` envia un
   `FormData` però **NO sobreescriu la capçalera `Content-Type`**; hereta el default global del
   client axios `Content-Type: application/json` (`client.js:5`). Amb això el navegador NO posa el
   `boundary` multipart → el servidor no pot parsejar el fitxer → `request.FILES['logo_file']`
   arriba buit → el logo no es desa mai. Tots els altres uploads multipart de la casa SÍ posen
   `headers: { 'Content-Type': undefined }` (`endpoints.js:154-156`, `:236`, `:254`); `uploadLogo`
   (`endpoints.js:14-17`) és l'única excepció. → **fix a FASE B**.

2. **CAMPS FISCALS — cap defecte a disc.** El camí JSON és correcte extrem a extrem: el `save()`
   construeix el payload amb els 15 camps (`GeneralConfig.jsx:65-73`), el client fa PATCH JSON net
   (`endpoints.js:12`), el backend `allowed` els accepta tots (`s2_views.py:297-299`), el model té
   les columnes (`models.py:57-64`), el serializer les exposa (`s2_serializers.py:178-185`) i
   `hydrate()` les rellegeix (`GeneralConfig.jsx:36-49`). Noms coincidents camp a camp (snake_case
   idèntic a banda i banda; cap camelCase, cap àlies). **No hi ha desajust de noms.**

3. **Desplegament coherent (no és stale).** L'únic tenant amb taula és `fhort` i té **TOTES** les
   columnes fiscals. El servei `ftt-staging` va arrencar 08:56:53, **posterior** al commit que
   afegeix els camps fiscals al backend (`81cca2c`, 08:40:11) → el procés en marxa té el codi
   actual. El bundle servit `GeneralConfig-BFKXa3Yz.js` **conté** `postal_code`/`city`/`phone`/
   `uploadLogo`, i el `index-*.js` servit referencia exactament aquest hash (cap bundle vell).

4. **Conclusió operativa.** El **logo** és un bug real i viu (FASE B el corregeix). Per als **camps
   fiscals** no hi ha causa a disc: el símptoma reportat s'ha de **reproduir amb crида HTTP real**
   (no harness) a FASE B; si persisteix, apunta a estat del procés/desplegament del moment de la
   prova de l'usuari, no a la font. Hipòtesi de treball: ja resolt per `81cca2c` + restart 08:56 +
   rebuild del bundle; la prova de l'usuari precedia un d'aquests.

---

## BLOC 1 — Camps fiscals (camí JSON PATCH)

**Frontend.**
- Estat inicial amb els 15 camps, snake_case: `GeneralConfig.jsx:25-29`.
- Inputs → `set('postal_code'|…)`; `set` fa merge immutable: `GeneralConfig.jsx:32`,
  `:122` (postal_code), `:127` (city), `:144` (phone). Cap input mal cablejat.
- `save()` payload amb TOTS els camps (nom_empresa, legal_name, tax_id, address, postal_code,
  city, country, email, phone, unitat_mesura, norma_referencia, hourly_rate, iban, payment_notes):
  `GeneralConfig.jsx:65-73`.
- Client: `update(data) → client.patch('/api/v1/tenant-config/', data)`, JSON (default
  `Content-Type: application/json`, `client.js:5`), Bearer via interceptor (`client.js:8-12`):
  `endpoints.js:12`.
- `hydrate()` rellegeix els 15 camps de la resposta/GET: `GeneralConfig.jsx:34-52`. `save()` NO
  re-hidrata (mostra toast verd i prou): `GeneralConfig.jsx:74-76`.

**Backend.**
- View: `allowed` inclou els 15 camps; setattr per cada camp present a `request.data` + `save()`:
  `s2_views.py:297-315`. Només `IsAuthenticated` (`s2_views.py:279-280`).
- Model: columnes `legal_name/tax_id/address/postal_code/city/country/email/phone` (+ iban,
  payment_notes, hourly_rate, logo_file): `accounts/models.py:57-64`, `:50-51`, `:46`, `:42`.
- Serializer (plain `Serializer`) exposa tots aquests camps: `s2_serializers.py:162-185`.
- Migració que afegeix les columnes: `accounts/migrations/0007_tenantconfig_address_tenantconfig_city_and_more.py`.

**Estat de dades (SELECT read-only a `information_schema`).**
- Tenants amb taula `accounts_tenantconfig`: només `fhort` (public no en té — app TENANT).
- `fhort`: `missing = CAP` — totes les columnes fiscals hi són.

**Veredicte Bloc 1: sense defecte a disc.** El símptoma (postal_code/city/phone no persisteixen)
NO es reprodueix per inspecció de codi ni per estructura de dades. Cal **reproducció HTTP real**
(FASE B) per confirmar si encara passa; si no passa, era estat stale ja resolt.

---

## BLOC 2 — Logo (camí multipart) — CAUSA EXACTA

- `onLogoPick`: llegeix el fitxer i crida `tenantConfig.uploadLogo(file)`; en OK re-hidrata i toast,
  en error toast d'error genèric: `GeneralConfig.jsx:79-88`. Input file amb accept SVG/PNG/JPG i
  `onChange={onLogoPick}`: `GeneralConfig.jsx:102`; botó que obre l'input: `:156-160`.
- `uploadLogo`: **`FormData` amb `logo_file` però sense override de `Content-Type`**:
  `endpoints.js:14-17`. → hereta el default `application/json` (`client.js:5`).
- **Patró correcte de la casa (contrast):** tots els altres uploads multipart passen
  `headers: { 'Content-Type': undefined }` perquè axios/el navegador calculin el `boundary`:
  `endpoints.js:154-156` (grading-preview-file), `:236`, `:254`.
- Efecte: el cos multipart viatja amb `Content-Type: application/json` sense boundary → DRF no
  activa el `MultiPartParser` → `request.FILES['logo_file']` **buit** → el bloc
  `if 'logo_file' in request.FILES` (`s2_views.py:303-313`) no s'executa → cap logo desat, cap
  crida a `normalize_logo`. Coherent amb el símptoma: preview "–", cap logo a BD ni PDF.
- `normalize_logo` (destí correcte un cop arribi el fitxer): SVG via cairosvg, ràster via Pillow:
  `accounts/logo.py:30-56`. La seva correcció és independent d'aquest bug (el fitxer ni hi arriba).

💡 PROPOSTA (a validar, FASE B): confirmar `import cairosvg` al venv de staging abans de donar el
logo SVG per bo (si `libcairo2` no hi és, hi hauria un **segon** bug de logo, latent fins ara
perquè el fitxer no arribava mai a `normalize_logo`).

**Veredicte Bloc 2: causa confirmada** = `uploadLogo` sense `Content-Type: undefined`
(`endpoints.js:14-17`). Fix trivial i alineat amb el patró existent.

---

## BLOC 3 — Desplegament (bundle · procés · proxy)

- Bundle servit: `frontend/dist/assets/GeneralConfig-BFKXa3Yz.js` conté `postal_code`(8×),
  `city`(9×), `phone`(8×), `uploadLogo`(1×), `logo_file`(1×) — grep del fitxer servit.
- `index-*.js` servit referencia `GeneralConfig-BFKXa3Yz.js` (únic hash, cap bundle vell orfe).
- nginx: `location /api/ → proxy_pass http://127.0.0.1:8001`; `client_max_body_size 25M` (el logo
  hi cap): `/etc/nginx/sites-enabled/ftt-staging:26-28`, `:3`.
- gunicorn: `--workers 2`, **sense** `--preload` ni `--reload`; `ExecMainStartTimestamp` 08:56:53 →
  codi de disc actual (posterior a `81cca2c` 08:40 i a `b26d5ec`).

**Veredicte Bloc 3: desplegament al dia.** Ni bundle vell, ni procés stale, ni límit de mida. El
logo no falla per desplegament sinó per la capçalera (Bloc 2).

---

## TAULA FINAL (per al CTO)

| Element | Estat | Font |
|---|---|---|
| `uploadLogo` posa boundary multipart | **FALTA** (`Content-Type` heretat = json) | `endpoints.js:14-17` vs `:154-156` |
| Payload JSON dels 15 camps al `save()` | EXISTEIX (correcte) | `GeneralConfig.jsx:65-73` |
| `allowed` backend amb els 15 camps | EXISTEIX | `s2_views.py:297-299` |
| Columnes fiscals al tenant `fhort` | EXISTEIXEN (totes) | `information_schema` (SELECT) |
| Serializer exposa els 15 camps | EXISTEIX | `s2_serializers.py:162-185` |
| Bundle servit amb el fix de camps | EXISTEIX | grep `GeneralConfig-BFKXa3Yz.js` |
| Procés backend amb codi actual | EXISTEIX (restart 08:56 > 08:40) | `systemctl show` |
| Toast d'èxit validat contra la resposta | **FALTA** (verd a qualsevol 200) | `GeneralConfig.jsx:74-76` |
| `import cairosvg` al venv de staging | PENDENT DE VERIFICAR (FASE B) | — |
| Camps fiscals via HTTP real | PENDENT DE REPRODUIR (FASE B, no harness) | — |

**Accions FASE B (patró B):** (1) `uploadLogo` → `headers: { 'Content-Type': undefined }`;
(2) toast verd només si la resposta 200 conté els valors enviats, altrament error amb els camps no
desats; (3) logo: preview des de la URL de la resposta, error visible amb el motiu del backend;
(4) verificació HTTP REAL (curl amb token / APIClient) de camps + upload SVG; (5) rebuild frontend +
`systemctl restart ftt-staging.service`.

---

## FASE B — REPRODUCCIÓ, RESOLUCIÓ I VERIFICACIÓ (contra el servidor real)

Reproducció amb **curl real** al gunicorn en marxa (`127.0.0.1:8001`, `Host: staging.fhorttextile.tech`,
Bearer SimpleJWT d'un usuari `fhort`) — NO harness. Resultats:

- **CAMPS:** `PATCH json {postal_code,city,phone}` → **200**; `GET` → els tres valors hi consten.
  → **El símptoma de camps NO es reprodueix al servidor real.** Confirmat: la versió d'abans
  (`eba5c7f`, payload incomplet) era el bug; ja resolt per `81cca2c` + restart. La prova de l'usuari
  precedia el desplegament corregit. **Cap canvi de codi per als camps.**
- **LOGO — bug 1 (frontend, HEAD):** el camí buggy (cos multipart + `Content-Type: application/json`)
  → **500** (DRF ParseError). Coincideix amb el símptoma. → **corregit** a `endpoints.js`.
- **LOGO — bug 2 (infra, ocult sota el bug 1):** amb multipart CORRECTE (`curl -F`) el backend
  retornava **500 `[Errno 13] Permission denied: media/tenant_logos/logo.png`**. Causa:
  `backend/media/` és de `www-data:www-data` però `backend/media/tenant_logos/` era de **`root:root`
  (755)** i gunicorn corre com `www-data` → no hi podia escriure. → **corregit** amb
  `chown www-data:www-data` + `chmod 775` del directori (fix d'infra, sense commit).
- `import cairosvg` al venv de staging: **OK 2.9.0** (la rasterització SVG funciona; el problema
  eren les capçaleres i els permisos, no cairosvg).

**Correccions aplicades:**
- `41fd1d8` — `uploadLogo` envia `headers: { 'Content-Type': undefined }` (boundary multipart).
- `e35382d` — `save()` mostra toast d'èxit NOMÉS si la resposta 200 confirma els valors enviats
  (`unsavedFields`), altrament error amb els camps; `onLogoPick` mostra el motiu del backend
  (`response.data.error`). i18n `config_general.save_mismatch` (ca/en/es).
- Infra (sense commit): `chown www-data:www-data backend/media/tenant_logos` + `chmod 775`.
- Rebuild frontend + `systemctl restart ftt-staging.service` (actiu 09:52:45).

**Verificació final (curl real contra el servidor reiniciat):**
- Camps: `PATCH` 200 → `GET` `postal_code=08201 · city=Sabadell · phone=+34 937 111 222`. ✅
- Logo SVG: `PATCH` 200 → `GET` `logo_file=…/media/tenant_logos/logo.png` + fitxer a disc
  (`www-data`, 3482 B, rasteritzat de l'SVG). ✅
- Estat de `fhort` restaurat després de cada prova (no destructiu).

**Nota per al CTO:** el missatge de commit que suggeries ("no enviava els camps fiscals ni el logo")
descrivia la hipòtesi prèvia; la causa real dels camps NO era el payload (ja correcte a HEAD), i el
logo tenia DUES causes (capçalera + permisos). Els commits reflecteixen les causes reals. El fix de
permisos del directori `media/tenant_logos/` és d'infra (fora de git): si es recrea l'entorn o es
reinstal·la, cal assegurar que `media/` i subdirectoris són de `www-data`.
