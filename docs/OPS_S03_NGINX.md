# OPS · S03a — bloc nginx per a la descàrrega gated

> **PENDENT D'APLICAR PER L'AGUS.** Els agents no toquen nginx.
> Servidor: `staging.fhorttextile.tech` · fitxer: `/etc/nginx/sites-enabled/ftt-staging`.

## Per què

Avui `location /media/` serveix els bytes amb `alias` directe: **Django no veu mai la
petició**, per tant no hi ha cap comprovació d'autenticació, de tenant ni d'accés al model
(`DIAGNOSI_S03_ARXIUS_2.md` Q1.4, taula #3). L'única cosa que hi ha al davant és l'`auth_basic`
del bloc servidor, que és una protecció d'**entorn**, no de producte: a PROD no hi és.

L'endpoint `GET /api/v1/model-fitxers/<id>/download/` (S03a · P2b, `models_app/views.py`)
autentica, resol el `FileField` dins el schema del tenant i delega els bytes a nginx amb
`X-Accel-Redirect`. Perquè això funcioni cal un `location` **intern**.

## El bloc a afegir

Dins el `server { server_name staging.fhorttextile.tech; ... }`, al costat del `location /media/`:

```nginx
    # Servei intern per a X-Accel-Redirect (endpoint gated de Django).
    # `internal` = inabastable des de fora; només Django el pot invocar per capçalera.
    location /protected-media/ {
        internal;
        alias /var/www/ftt-staging/backend/media/;
    }
```

Aplicar amb:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

## Sobre el `location /media/` existent

**Es deixa tal com està, de moment.** Encara el fan servir les superfícies de frontend que no
s'han migrat a l'endpoint gated (`FittingDetail.jsx:84`, els previews de `ModelSheet.jsx`,
`addModelFitxer` a `TechSheetEditor.jsx`). Queda **per jubilar** quan totes hi hagin migrat;
mentre hi sigui, els bytes segueixen sent accessibles per URL directa.

## ⚠️ Ordre obligatori al deploy

`P2a` ha canviat el path físic del media a `MEDIA_ROOT/<schema>/…`. Les URLs i els paths que
Django genera ja apunten a la nova arrel, però **els bytes encara són a la vella**. Per tant:

```
1. git pull
2. python manage.py migrate_schemas
3. python manage.py move_media_tenant --apply      ← NOU. Sense això, tot el media dona 404.
4. systemctl restart <servei gunicorn>
5. sudo nginx -t && sudo systemctl reload nginx    (un cop afegit el bloc de dalt)
```

Si es reinicia gunicorn **abans** del pas 3, tot el media (logos, PDFs, `.ftt`, previews) dona
404 fins que s'executi. El pas 3 és idempotent i verifica ell mateix el resultat.

### El pas 3 ja fa el `chown` (D19, S03c · C1.4)

**Història (es conserva, no s'esborra):** fins a S03c, `move_media_tenant --apply` creava els
directoris de destí amb `os.makedirs`, és a dir **amb l'owner del procés** — `root` al deploy.
Com que gunicorn corre com `www-data`, tot upload posterior fallava amb
`500 [Errno 13] Permission denied`. És la causa provada de l'incident del 2026-07-10
(`docs/diagnosis/INCIDENT_2026-07-10_STAGING.md`), i calia reparar-ho a mà amb un
`chown -R www-data:www-data backend/media/` després del pas 3.

**Ara és automàtic.** El pas 3 normalitza l'owner de **cada** directori que crea (no només de
la fulla: `model_fitxers/2026/06` són tres nivells nous) i de cada fitxer que mou. Es configura
amb `--owner` (per defecte `www-data:www-data`) i només actua amb `--apply`. Si la comanda no
corre com a root, el `chown` falla amb un **avís clar i no bloqueja** el trasllat: en aquest cas
cal aplicar el `chown` a mà, com deia el runbook antic.

El pas manual genèric per a subdirectoris de media **segueix vigent** per a tot el que NO mou
aquesta comanda (p.ex. `mkdir` d'un directori d'upload nou): vegeu `docs/deploy.md`, § owner de
`backend/media/`.

## Nota: staging corre amb `DEBUG=true`

`backend/.env` de staging té `DEBUG=true`, per tant l'endpoint `download/` hi agafa el
**fallback `FileResponse`** i NO exercita mai la branca `X-Accel-Redirect`. La branca s'ha
verificat forçant `DEBUG=False` (capçalera generada:
`X-Accel-Redirect: /protected-media/fhort/model_fitxers/2026/07/…`, cos buit).
A PROD (`DEBUG=false`) el camí real és el de nginx, i **sense el bloc `location /protected-media/`
la descàrrega retornarà una resposta buida**. El bloc i el codi han d'anar junts.
