# Desplegament — Textile Tech

Referència factual de la configuració de desplegament del servidor de producció.

## Pas 0 — abans de tocar PROD: que tot hagi VIATJAT (es corre a STAGING)

PROD desplega des d'`origin/dev`. Els agents **committen en local i no pushen mai** (llei de
`CLAUDE.md`), així que a staging hi pot haver feina **commitada però no viatjada**: existeix,
és verda, la vas veure funcionar… i `origin/dev` no en sap res. Un deploy en aquest estat no
falla — fa una cosa pitjor: se'n va a PROD **sense** aquella feina, en silenci, i el que arriba
no és el que vas validar.

Abans del pas 1 del runbook del sprint, a **staging** (`/var/www/ftt-staging`):

```bash
cd /var/www/ftt-staging
git fetch origin
git log --oneline origin/dev..dev     # ha de tornar BUIT
```

- **Buit** → tot el que hi ha commitat és a `origin/dev`. Endavant.
- **Surt res** → això és exactament la feina que PROD **no** rebria. Push des d'SSH i repeteix
  la comprovació abans de continuar. Revisa'n els autors (`git log --format='%h %an' origin/dev..dev`):
  `dev` té sessions concurrents i el push s'emporta **tot** el que hi hagi al davant, no només
  el teu sprint.

> No és disciplina de push (els agents segueixen sense pushar): és la xarxa de seguretat que
> converteix «no viatjat» en un pas que falla a staging, no en una sorpresa a PROD.

## Servidor

- **IP:** 178.105.217.125
- **Domini:** `fhorttextile.tech` (i `www.fhorttextile.tech`) — ÚNIC projecte d'aquest servidor.
- **Stack:** Django (Gunicorn via socket Unix) + nginx servint el `dist/` del frontend React.

> Nota: el codi/regla d'aïllament per a `assessment` / `trading` / `webs` és d'un **altre**
> servidor (ERP Frappe) i **no aplica** aquí. Aquest servidor només és Textile Tech.

## nginx

- **Fitxer del vhost:** `/etc/nginx/sites-available/fhort-textile` (symlink a `sites-enabled/`).
  És l'únic fitxer d'nginx que toca aquest domini.
- **Block 80:** redirigeix a HTTPS.
- **Block 443:**
  - `root /var/www/fhort-textile/frontend/dist;`
  - `location / { try_files $uri $uri/ /index.html; }` — fallback SPA.
  - `location /api/` → `proxy_pass http://unix:/run/fhort.sock;` (backend Django).
  - `location /static/` → `alias /var/www/fhort-textile/backend/staticfiles/;`
  - `location /media/` → `alias /var/www/fhort-textile/backend/media/;`

### Cache (afegit per evitar el *chunk stale* a cada redeploy)

El fallback SPA feia que un chunk amb hash antic (esborrat del `dist/` al rebuild) caigués a
`/index.html` i el navegador rebés `Content-Type: text/html` per a un `.js` → error MIME
("Failed to load module script"). Mitigació, confinada al block 443:

```nginx
# index.html: revalida sempre → els redeploys s'agafen sense hard-refresh manual.
location = /index.html {
    add_header Cache-Control "no-cache";
}

# Assets amb hash al nom (immutables): cacheables 1 any. A més, en ser una location pròpia
# (no passa pel try_files de "/"), un /assets/* inexistent torna 404 REAL en lloc del fallback
# SPA a index.html → s'evita l'error MIME confús del chunk stale.
location /assets/ {
    add_header Cache-Control "public, max-age=31536000, immutable";
}
```

- `index.html` → `Cache-Control: no-cache` (revalida sempre).
- `/assets/` → `Cache-Control: public, max-age=31536000, immutable` (segur perquè el hash és al nom).
- `/assets/*` inexistent → **404 real** (no fallback SPA → evita l'error MIME confús).

Aplicar canvis d'nginx: `nginx -t && systemctl reload nginx`.

## Backend

- **Servei:** `fhort.service` (Gunicorn).
- Després de canvis al backend: `sudo systemctl restart fhort.service`.
- Comprovació prèvia recomanada: `python manage.py check` (des de `backend/`, venv activat).

## Permisos de `media/` (uploads de fitxers)

Els directoris sota `backend/media/` (`tenant_logos/` i qualsevol subdirectori d'upload futur —
p.ex. DXF del motor de patrons) han de ser propietat de **`www-data:www-data`**, no de `root:root`.
Gunicorn corre com `www-data`; si un directori d'upload és de root, l'escriptura falla amb
`500 [Errno 13] Permission denied` i el fitxer no es desa (trobat 2026-07-09, fitxa Empresa/logo).

Aquest pas **NO viatja amb git ni amb cap migració**: si es recrea l'entorn (servidor nou, tenant
nou, restore de backup) o es crea un subdirectori d'upload nou, cal repetir-lo explícitament —
**després de qualsevol `mkdir` de `media/` i abans del primer restart**:

```bash
mkdir -p backend/media/<nou_directori>
chown www-data:www-data -R backend/media/<nou_directori>
chmod 775 backend/media/<nou_directori>
```

Verificació ràpida (ha de tornar buit; si surt algun path, aplicar-hi el `chown`):

```bash
find backend/media/ ! -user www-data
```

## Frontend

- Build: `cd frontend && npm run build` → genera `frontend/dist/` (vite neteja el `dist/` antic i
  emet hashes nous a cada build). nginx serveix aquest `dist/` directament.

### `VITE_API_URL` — SAME-ORIGIN per defecte (un sol build per a tots els dominis)

**El defecte és relatiu.** `client.js` exporta `apiBaseURL = import.meta.env.VITE_API_URL || ''`;
amb `''` cada crida cau sobre **l'origen que ha servit la pàgina**, el `Host` real viatja tal qual
i django-tenants resol el tenant per aquest `Host`. Conseqüència: **un sol `dist/` serveix
qualsevol domini/tenant**.

Fins al 2026-07-22 el `baseURL` era `VITE_API_URL` a seques i `frontend/.env` hi posava un domini
**absolut**. Això CABLEJAVA el build a un host: qualsevol altre domini que servís el mateix `dist/`
enviava igualment les crides al domini cablejat — amb el `Host` equivocat, és a dir el **tenant
equivocat**. D'aquí naixien dues coses que ara deixen de ser necessàries:

- **`dist-tenants/`** (un build per domini). Amb el `dist/` sense cap domini a dins, un domini de
  tenant nou pot apuntar directament a `dist/` com qualsevol altre. *Migració pendent a PROD: no
  la fa aquest sprint.*
- **El CORS cap als dominis d'app.** El trànsit normal passa a ser same-origin i no en depèn.
  `settings.py:249-258` es manté de moment com a xarxa de seguretat (el dev local a `:5173` sí
  que el necessita); retirar-ne la part de `*.fhorttextile.tech` és feina d'un sprint d'infra.

**Quan SÍ s'ha de definir `VITE_API_URL`:** només si el front i l'API **no comparteixen origen**.
És el cas del dev local (front a `:5173`, back a `:8000`), que ja el porta `frontend/.env.development`.
Definir-lo a `frontend/.env` torna a cablejar el build a un domini — no fer-ho sense un motiu.

> `frontend/.env` està al `.gitignore`: **no viatja amb git**. En un entorn nou (o en un restore)
> cal comprovar-ho a mà: `grep VITE_API_URL frontend/.env` ha de sortir buit o comentat.

Verificació ràpida després d'un build (ha de tornar **0**):

```bash
grep -rho "https://[a-z0-9.-]*fhorttextile.tech" frontend/dist/assets/ | wc -l
```

### Uploads multipart des del frontend — `Content-Type`

Qualsevol client HTTP del frontend que pugi fitxers amb `FormData` ha de **sobreescriure
explícitament el `Content-Type` a `undefined`** per a aquella crida concreta. El client axios base
té un `Content-Type: application/json` fixat a nivell global; si l'upload l'hereta, el navegador
**no** afegeix el `boundary` multipart, el fitxer **mai** arriba a `request.FILES` del servidor i
falla amb un `ParseError` silenciós (trobat 2026-07-09, upload de logo). Patró correcte:

```js
client.patch(url, formData, { headers: { 'Content-Type': undefined } })
```

Comprovar aquest patró en **qualsevol upload nou** (p.ex. DXF del motor de patrons).

## Notes operatives

- Backup temporal del block nginx original: `/tmp/fhort-textile.bak` (no permanent; recrear el
  vhort des d'aquest doc si cal).
