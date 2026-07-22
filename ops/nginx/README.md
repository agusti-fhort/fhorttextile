# ops/nginx — config d'nginx versionada

La config d'nginx viu fora del repo (`/etc/nginx/`), així que **cada re-provisió del
servidor la perd**. Això era el punt **12** del veredicte de
`docs/diagnosis/DIAGNOSI_RENDIMENT_SESSIO_2026-07-22.md`:

> *«gzip_types, preload, max_requests i el log_format viuen tots a config sense
> versionar → cada re-provisió del servidor els torna a perdre»*

Aquest directori és la font de veritat. Si es reconstrueix la màquina, es reinstal·la
d'aquí.

## Fitxers i on van

| Fitxer del repo | Destí a la màquina | Context |
|---|---|---|
| `ftt-log-format.conf` | `/etc/nginx/conf.d/ftt-log-format.conf` | `http` (via `include conf.d/*.conf`) |
| `gzip.conf` | bloc `http { }` de `/etc/nginx/nginx.conf` | `http` (in-place, no és un include) |
| `ftt-staging.vhost.conf` | `/etc/nginx/sites-enabled/ftt-staging` | `server` |

`gzip.conf` **no** és un include: nginx.conf ja porta les directives `gzip` de fàbrica
(comentades) i duplicar-les en un include seria confús. El fitxer és la plantilla exacta
del bloc que hi ha d'haver.

El vhost porta trossos gestionats per Certbot (`listen 443 ssl`, certificats). Després de
copiar la plantilla, **comprovar que les rutes dels certificats existeixen** abans de
recarregar.

## Instal·lació

```bash
cp ops/nginx/ftt-log-format.conf /etc/nginx/conf.d/
# gzip.conf: enganxar el bloc dins del http { } de /etc/nginx/nginx.conf
cp ops/nginx/ftt-staging.vhost.conf /etc/nginx/sites-enabled/ftt-staging
nginx -t && systemctl reload nginx
```

`nginx -t` **abans** de cada `reload`, sempre. Un `reload` amb config invàlida no aplica
res (bé), però un `restart` amb config invàlida deixa el servei caigut.

## Mesurar la latència (per a què serveix el log_format)

`ftt_timing` afegeix `$host`, `$request_time` i `$upstream_response_time` al log del
vhost (`/var/log/nginx/ftt-staging-access.log`). Amb això ja es pot calcular el p95 per
endpoint, cosa que amb `combined` era **impossible**.

```bash
# Top-10 endpoints més lents per temps mitjà d'upstream
awk -F'urt=' '/urt=/{split($2,a," "); split($0,b,"\""); print a[1], b[4]}' \
  /var/log/nginx/ftt-staging-access.log \
  | awk '{gsub(/\?.*/,"",$3); s[$2" "$3]+=$1; n[$2" "$3]++} END {for(k in s) printf "%.3f %5d %s\n", s[k]/n[k], n[k], k}' \
  | sort -rn | head -10
```

`rt` (total) molt més gran que `urt` (app) = el temps se'n va en xarxa/client, no a
Django. Els dos iguals = el temps és de l'app.
