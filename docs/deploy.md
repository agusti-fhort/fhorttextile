# Desplegament — Textile Tech

Referència factual de la configuració de desplegament del servidor de producció.

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

## Frontend

- Build: `cd frontend && npm run build` → genera `frontend/dist/` (vite neteja el `dist/` antic i
  emet hashes nous a cada build). nginx serveix aquest `dist/` directament.

## Notes operatives

- Backup temporal del block nginx original: `/tmp/fhort-textile.bak` (no permanent; recrear el
  vhort des d'aquest doc si cal).
