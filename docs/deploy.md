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
- **Dominis:** `fhorttextile.tech` (apex, i `www.`) i `app.fhorttextile.tech` (segona porta de
  l'app, Fase 1+2 dominis, 2026-07-12) — ÚNIC projecte d'aquest servidor.
- **Stack:** Django (Gunicorn via socket Unix) + nginx servint el `dist/` del frontend React.

> Nota: el codi/regla d'aïllament per a `assessment` / `trading` / `webs` és d'un **altre**
> servidor (ERP Frappe) i **no aplica** aquí. Aquest servidor només és Textile Tech.

## nginx

> ⚠️ **Els fitxers d'nginx viuen FORA del repo i no viatgen amb git.** El que es versiona aquí és
> la **documentació de què serveix cada domini**, no el vhost. Per tant aquest apartat pot quedar
> desfasat sense que cap test ho detecti: davant d'un dubte, mana `nginx -T`, no aquest text.

### Quants vhosts serveixen FTT (enumerar-los SEMPRE, mai suposar-ne un)

**FTT no es serveix des d'un sol vhost.** A l'apex s'hi sumen els **dominis de tenant**
(`<tenant>.fhorttextile.tech`), i històricament cadascun podia tenir un `root` propi. Donar per
fet que "només hi ha un fitxer d'nginx que toca aquest domini" és precisament el que va amagar el
vhost de `losan.fhorttextile.tech` durant dos dies (2026-07-22 → 07-24).

Cens abans de qualsevol deploy de frontend — la configuració **efectiva**, no els fitxers:

```bash
nginx -T | grep -nE 'server_name|root '     # què serveix cada domini, de debò
ls -la /etc/nginx/sites-enabled/            # ⚠️ n'hi pot haver de FITXER REGULAR, no symlink:
                                            #    editar sites-available/ no els toca
```

- **Fitxer del vhost de l'apex:** `/etc/nginx/sites-available/fhort-textile` (symlink a
  `sites-enabled/`). **No és l'únic fitxer d'nginx que serveix FTT** — vegeu el cens.
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
  emet hashes nous a cada build). **`npm run build` escriu NOMÉS a `dist/`.**

### ⚠️ La regla d'or del deploy de frontend

> **Un build que no toca el directori que serveix un domini deixa aquell domini enrere EN SILENCI,
> i la verificació post-deploy dona verd igualment.**

Per això **no es verifica «que `dist/` estigui bé»**: es verifica **quin `root` serveix el vhost de
CADA domini afectat, i es comprova CONTRA AQUELL**. Si un domini té un `root` que `npm run build`
no escriu, aquell domini no ha rebut el deploy per molt verd que surti tot.

Ordre correcte, per a cada domini del cens de l'apartat nginx:

```bash
# 1) quin root serveix aquest domini (la config EFECTIVA)
nginx -T | awk '/server_name <domini>/,/}/' | grep -m1 'root '

# 2) el chunk d'entrada que serveix, vs el que hi ha al root
curl -s https://<domini>/index.html | grep -o 'assets/index-[A-Za-z0-9_-]*\.js'
grep -o 'assets/index-[A-Za-z0-9_-]*\.js' <root>/index.html

# 3) han de coincidir. Si no, aquell domini serveix un build congelat.
```

Mesura complementària quan el hash no basta (p.ex. per confirmar que hi ha arribat un fix concret):
buscar un **marcador del codi recent** dins del bundle servit. Compte: amb code-splitting el
marcador pot viure en un chunk peresós (`assets/<Pagina>-*.js`), no al `index-*.js` d'entrada —
cal buscar-lo a tot `assets/`, no només al chunk d'entrada.

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
  tenant nou pot apuntar directament a `dist/` com qualsevol altre. **✅ Migració FETA a PROD el
  2026-07-24:** el vhost de `losan.fhorttextile.tech` va passar de `frontend/dist-tenants` a
  `frontend/dist`, i el `dist-tenants/` duplicat va quedar retirat (`.bak` datat; la neteja dels
  `.bak` es fa en fred, mai el mateix dia). Fins llavors aquell vhost servia un build congelat del
  22/07 i **cap `npm run build` l'actualitzava** — vegeu la regla d'or de l'apartat Frontend.
  A **staging** no calia migrar res: `dist-tenants/` no hi ha existit mai i l'únic vhost d'SPA
  (`staging.fhorttextile.tech`) ja apunta a `dist/` (cens verificat el 2026-07-24; ja constava a
  `docs/diagnosis/DIAGNOSI_LOGIN_UNIC_2026-07-22.md` §B1.3).
- **El CORS cap als dominis d'app.** El trànsit normal passa a ser same-origin i no en depèn.
  `settings.py:249-258` es manté de moment com a xarxa de seguretat (el dev local a `:5173` sí
  que el necessita); retirar-ne la part de `*.fhorttextile.tech` és feina d'un sprint d'infra.

**Quan SÍ s'ha de definir `VITE_API_URL`:** només si el front i l'API **no comparteixen origen**.
És el cas del dev local (front a `:5173`, back a `:8000`), que ja el porta `frontend/.env.development`.
Definir-lo a `frontend/.env` torna a cablejar el build a un domini — no fer-ho sense un motiu.

> `frontend/.env` està al `.gitignore`: **no viatja amb git**. En un entorn nou (o en un restore)
> cal comprovar-ho a mà: `grep VITE_API_URL frontend/.env` ha de sortir buit o comentat.

Verificació ràpida després d'un build (ha de tornar **0**). Es corre sobre el **`root` de cada
domini** del cens, no sobre `dist/` per defecte: si un domini en servís un altre, mirar `dist/`
donaria verd sense dir res d'aquell domini.

```bash
for r in $(nginx -T | grep -oP '(?<=root )\S+(?=;)' | sort -u | grep frontend); do
  echo "$r → $(grep -rho 'https://[a-z0-9.-]*fhorttextile.tech' "$r"/assets/ 2>/dev/null | wc -l)"
done
```

> El `root` del **backoffice** (`frontend-backoffice/dist`) hi surt amb un valor **≠ 0** i és
> correcte: serveix un domini únic (`backoffice.` / `stagingbackoffice.`) i sí que porta
> `VITE_API_URL` cablejat. La regla del same-origin és per a la **SPA de tenants**, que és
> l'única que ha de servir dominis diferents amb un sol build.

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

## Segona porta de l'app — `app.fhorttextile.tech` (Fase 1+2 dominis, 2026-07-12)

L'app és accessible pels **dos** dominis (`fhorttextile.tech` i `app.fhorttextile.tech`);
l'apex NO s'ha tocat (mateix vhost, mateix comportament). Peces afegides:

- **Vhost nginx nou:** `/etc/nginx/sites-available/fhort-app` (symlink a `sites-enabled/`).
  És un clon del block `:443` de `fhort-textile` amb `server_name app.fhorttextile.tech`
  (mateix `root frontend/dist`, mateix `proxy /api/ → unix:/run/fhort.sock`, mateixos
  `/static/`, `/media/`, `/protected-media/`), més un block `:80` que redirigeix a HTTPS.
- **Certificat:** el MATEIX lineage `/etc/letsencrypt/live/fhorttextile.tech/`, expandit a
  **4 SANs** (`fhorttextile.tech`, `www.`, `backoffice.`, `app.`) via
  `certbot certonly --nginx --expand --cert-name fhorttextile.tech`. NO és un lineage nou.
- **Tenant (django-tenants):** fila nova a `public.tenants_domain` →
  `domain='app.fhorttextile.tech'`, `tenant_id=2` (schema `fhort`), **`is_primary=False`**
  (el swap de primari és Fase 3, encara no fet). Es crea via `manage.py shell`, no SQL a mà.
- **Frontend:** `frontend/.env` → `VITE_API_URL=https://app.fhorttextile.tech` (abans l'apex).
  El `baseURL` d'axios és absolut, així que el bundle apunta a `app.*` per als DOS dominis;
  quan s'accedeix per l'apex, les crides a l'API van cross-origin a `app.*` (cobert per CORS:
  `CORS_ALLOWED_ORIGINS` + regex de subdominis a `settings.py`). Cal **rebuild** després de
  canviar `.env` (`npm run build`); verificar el `.env` ABANS del build (lliçó dels `.env` creuats).

Rollback: retirar el symlink `sites-enabled/fhort-app` + `nginx -t && systemctl reload nginx`;
esborrar la fila `Domain` d'`app.*` pel shell; revertir `frontend/.env` + rebuild. El cert amb
4 SANs és inofensiu encara que es reverteixi la resta.

## Notes operatives

- Backup temporal del block nginx original: `/tmp/fhort-textile.bak` (no permanent; recrear el
  vhort des d'aquest doc si cal).
