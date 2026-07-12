# PRE-DEPLOY PROD — 2026-07-12

Data: 2026-07-12 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
Abast: dimensionar el merge `origin/dev` → `main`, les migracions que entren, l'estat real de
PROD i els riscos funcionals del salt. Cap escriptura: cap commit, cap checkout, cap migració,
cap restart, cap connexió d'escriptura a cap BD.

Convenció: `fitxer:línia` · "NO EXISTEIX" = confirmat absent al codi (no especulat) ·
💡 PROPOSTA = a validar pel CTO, no és un fet.

**Font de veritat de PROD:** no s'ha pogut entrar per SSH (la clau d'aquesta màquina no està
autoritzada a `178.105.217.125`). En comptes d'inferir, s'ha llegit **el backup real de PROD
d'avui** — `/srv/fhort-prod-backups/incoming/fhort_textile_20260712_023001.dump`
(2026-07-12 02:30 UTC, rèplica per rsync a PROJECTES) — amb `pg_restore -l` / `-a … -f -`, que
només llegeix el fitxer. Tot el que es diu de la BD de PROD és **mesurat**, no deduït. El poc
que segueix requerint SSH està aïllat al § 6.

---

## 0. Resum executiu — la premissa del brief era falsa

1. **PROD no corre `origin/main`.** PROD té **195 migracions aplicades**, entre elles l'app
   `commerce` sencera (0001→0019) i `i18n_content`. `origin/main` **no conté ni tan sols
   aquestes apps**. El `main` de GitHub porta parat des del 2026-07-07 i el `main` **local** va
   **467 commits endarrerit** — cap dels dos descriu PROD.
2. **PROD no és del 27/06: va rebre un desplegament gran el 2026-07-09** (43 migracions
   aplicades: 11:17 i 17:47 UTC). El bundle del frontend és del mateix dia (11:19).
3. **El salt real és petit.** No són 196 commits: PROD ja porta gairebé tota la línia `dev`.
   El delta real són **~31 commits / 55 fitxers / +5.161 −214** (del 09/07 al 10/07).
4. **Migracions pendents: només 4, totes additives.** Cap destructiva, cap que toqui dades. Les
   perilloses del lot (`pom/0027 delete_tascaglobal`, `models_app/0052 drop column`,
   `tasks/0032 distill_time_seeds`, `tasks/0036 unique constraint`) **ja estan aplicades a PROD
   des del 09/07** — el seu risc és passat, no futur.
5. **El merge no té conflictes.** `git merge-tree` retorna exit 0 i un arbre idèntic al d'`origin/dev`:
   `origin/main` no aporta cap delta propi. Intersecció de fitxers tocats per les dues bandes = **∅**.
6. **Els riscos funcionals que preocupaven són nuls a PROD** (mesurat al dump): 0 sessions de
   fitting vives, 0 divergències base↔grading, 1 sol model amb grading segellat.
7. 🔴 **El risc real és un altre i no surt al brief:** el salt canvia **on viuen els bytes del
   media** i **com se serveixen les descàrregues**. Cap de les dues coses viatja amb `git`. Sense
   dos passos manuals, PROD queda amb el media trencat. Vegeu § 5 — és l'únic motiu de NO-GO.

---

## 1. P1 — Dimensió del merge

### Referències (post `git fetch origin`)

| Ref | Commit | Data | Nota |
|---|---|---|---|
| `origin/main` | `da4ddd2` | 2026-07-07 10:15 | tip = merge d'`origin/dev`; **el seu tree és idèntic al de la merge-base** |
| `origin/dev` | `0eae56e` | 2026-07-10 07:19 | el que es desplegaria |
| `dev` (local) | `34f0efa` | 2026-07-10 22:01 | **33 commits NO pushats** |
| `main` (local) | `685c944` | 2026-06-16 | **467 commits endarrerit — inservible com a referència** |
| merge-base | `912911f` | 2026-07-07 09:28 | |

> ⚠️ El brief demanava `git log main..origin/dev`. Amb el `main` local 467 commits enrere, aquesta
> comanda dona una xifra sense sentit. Tot aquest document usa **`origin/main`**.

### Conflictes del merge `--no-ff`: CAP

| Comprovació | Resultat |
|---|---|
| `git diff --name-only 912911f origin/main` | **0 fitxers** — main no toca res des de la base |
| `git diff --name-only 912911f origin/dev` | 292 fitxers |
| Intersecció (candidats a conflicte) | **∅ (buida)** |
| `git merge-tree --write-tree origin/main origin/dev` | **exit 0**, tree `d947d19…` = `tree(origin/dev)`, sense secció de conflictes |

Els fitxers que el brief marcava com a punts calents (`App.jsx`, `endpoints.js`, i18n `ca/en/es`,
`settings.py`, `requirements`) els toca **només la banda dev**; main hi aporta 0 línies. Risc de
conflicte **BAIX per a tots, sense excepció**. La config d'nginx **no és al repo** → el merge no
la toca (però vegeu § 5).

Els "~14 commits de backoffice" que es recordaven són en realitat **22 commits (14 de feina + 8 de
deploy/merge) i són de FITTING + SIZE/POM**, no de backoffice. El seu contingut ja és dins l'arbre
de `dev` (verificat fitxer a fitxer); `git cherry` els marca com a absents només per patch-id.
**No es perd res.**

### 🟠 Els 33 commits locals no pushats

`dev` local va 33 commits per davant d'`origin/dev`. **Si el merge es fa d'`origin/dev`, aquests
33 NO hi entren.** Inclouen coses que algú podria donar per fetes:

- `backend/fhort/tasks/migrations/0038_modeltask_fitting_session.py` — la migració 0038 **no va a PROD**.
- Sprint Y (dissolució de `FittingDetail`, redirect Y7), sprint X (`allow_reopen_sealed`, `code=grading_sealed`, modal de reobertura), i el command de reparació `repair_fitting_20260710`.

**Decisió del CTO, no de l'agent:** o es fa push de `dev` abans del merge (i llavors sí que apliquen
els riscos Y7/reobertura del § 4), o es desplega `origin/dev` i tot això queda per a la propera.

**Veredicte P1: merge net, sense conflictes. Cal decidir explícitament si es puja `dev` abans.**

---

## 2. P2 — Migracions que entren

Baseline **mesurat** (no inferit): taula `django_migrations` del dump de PROD de 2026-07-12 02:30.
PROD té **2 schemas**: `public` (tenant 1) i `fhort` (tenant 2, domini `fhorttextile.tech`).
Els dos estan al mateix nivell. `migrate_schemas` aplicarà cada migració **×2**.

### Onades de desplegament ja aplicades a PROD

| Dia | Migracions aplicades |
|---|---|
| 2026-06-11 … 06-17 | 17 |
| **2026-06-27** | 16 |
| 2026-06-29 | 5 |
| 2026-07-07 | 1 |
| **2026-07-09** | **43** ← el gran salt: `commerce` 0001-0019, `i18n_content` 0001, `pom` 0027-0035, `models_app` 0052-0053 |

### Pendents d'aplicar: 4

| # | App | Migració | Operació | Tipus | Toca dades? | Risc |
|---|---|---|---|---|---|---|
| 1 | `models_app` (tenant) | `0054_itemfitxer` | CreateModel `ItemFitxer` | **ADDITIVA** | no | 🟢 |
| 2 | `models_app` (tenant) | `0055_modelfitxer_derivat_de_item` | AddField FK (null) | **ADDITIVA** | no | 🟢 |
| 3 | `models_app` (tenant) | `0056_modelfitxer_derivat_de_model` | AddField FK self (null) | **ADDITIVA** | no | 🟢 |
| 4 | `pom` (**shared + tenant**) | `0036_gradingruleset_origen` | AddField `origen` (null) | **ADDITIVA** | no | 🟢 |

**Cap destructiva. Cap RunPython. Cap taula gran recorreguda.** Dependències satisfetes
(`0054` depèn d'`accounts.0007` i `tasks.0037`, tots dos ja aplicats). Temps d'execució: segons.

### Coses que ja NO són un risc (perquè ja van córrer el 09/07)

`pom/0027_delete_tascaglobal` (DROP TABLE), `models_app/0052_remove_modelfitxer_path_servidor`
(DROP COLUMN), `tasks/0032_distill_time_seeds` (esborrava `estimated_minutes`),
`tasks/0036` (UniqueConstraint que podia avortar el deploy), i totes les data-migrations de `pom`
(0030/0031/0032/0034/0035). **Estan aplicades i PROD ha viscut tres dies amb elles.**

### Anomalies (no bloquejants)

- 🟡 **`files/0001_initial` aplicada a PROD però l'app `files` NO EXISTEIX** ni a `origin/dev` ni a
  `origin/main`. Fila òrfena a `django_migrations` d'una app retirada fa temps. Inert: Django només
  se'n queixaria si l'app tornés a `INSTALLED_APPS`. **No tocar.**
- 🟡 **`tasks/0025_seed_canonical_task_types.py` ha estat EDITADA després d'aplicar-se**
  (`'Audit'` → `'audit'`, línia 22). Django no verifica hash → el deploy **no petarà**; la fila ja
  consta com a aplicada i no es reexecutarà. La correcció real sobre dades la va fer `tasks/0030`,
  ja aplicada. Queda com a deute cosmètic (la migració "menteix" sobre el que es va executar).

**Veredicte P2: 4 migracions additives. 🟢 El pas de migració és el tram més segur del deploy.**

---

## 3. P3 — Estat de PROD

| Comprovació | Resultat | Com s'ha verificat |
|---|---|---|
| Servei viu | 🟢 **`GET /api/schema/` → 200** (580.471 bytes) | HTTPS avui 2026-07-12 |
| Bundle actual | 🟡 `index.html` **Last-Modified 2026-07-09 11:19:37 GMT** | capçalera HTTP |
| Backend (migracions) | Codi del **2026-07-09 17:47** | `django_migrations` del dump |
| Backup més recent | 🟢 **2026-07-12 02:30** — `fhort_textile_20260712_023001.dump` (1,4 MB) + `globals` + `media` (9,9 MB) | present a PROJECTES |
| Cadena de backup | 🟢 Viva i diària (cron 02:30 + rsync), 30 dies de retenció, sense forats | `ls` de `/srv/fhort-prod-backups/incoming/` |
| Tenants | `public` (tenant 1) + `fhort` (tenant 2 → `fhorttextile.tech`) | dump |
| Espai de disc a PROD | ⚪ **PENDENT — requereix SSH** (§ 6) | — |
| Commit exacte de PROD | ⚪ **PENDENT — requereix SSH** (§ 6) | — |

### 🟡 Skew backend ↔ frontend

Les migracions `models_app/0052-0053` es van aplicar a les **17:47** del 09/07, però el bundle és de
les **11:19** del mateix dia. És a dir: **al segon desplegament del 09/07 es va migrar el backend
però (aparentment) no es va reconstruir el frontend.** PROD serveix un bundle potencialment més
antic que el seu backend. No sembla haver causat cap incident (l'API respon 200), però convé
saber-ho: el `npm run build` del proper deploy ho corregirà de passada.

**Veredicte P3: PROD viu, backup d'avui verificat. Falten 2 dades menors que només dona el SSH.**

---

## 4. P4 — Riscos funcionals del salt

Mesurat sobre el dump de PROD del 2026-07-12 (no sobre staging: **la BD de staging es va refrescar
per última vegada des de PROD el 2026-06-12** — porta un mes de divergència i no és un proxy vàlid).

| Risc del brief | A PROD | Semàfor |
|---|---|---|
| Models amb `GradingVersion` activa **i** aprovada → candidats al **modal de reobertura** | **1 model**: `169` (`BRW-FW26-0007`), grading v1 | 🟢 |
| `FittingSession` vives (Programada/Oberta) → les reubica el **redirect Y7** | **0** — l'única sessió de la taula (id 94, "Dev", model 178) està **Tancada** des del 2026-06-18 | 🟢 |
| Sessions vives sense `model_id` (anirien a `/models/null`) | **0** | 🟢 |
| Divergència base↔grading tipus **XE** | **0 files divergents**, comprovat sobre **totes** les `GradingVersion` actives (no només les dels models amb sessió) | 🟢 |

**El patró XE és staging-only, confirmat.** La causa (`repair_fitting_20260710.py:3-10`) és el
`close_piece_fitting` no atòmic: el guard D-1 saltava *després* que la consolidació a
`BaseMeasurement` hagués commitat. A PROD **ningú ha gravat cap presa contra un grading segellat**
(0 sessions vives, 1 sessió tancada al juny), per tant el patró no s'hi ha pogut produir.
**Cap dada de PROD necessita reparació.**

> Context que relativitza tot el bloc: PROD té **28 models, 1 sessió de fitting, 170
> BaseMeasurement**. És una producció **encara molt poc carregada**. Els riscos de volum
> (data-migrations amb loop, constraints sobre duplicats) són irrellevants a aquesta escala.

> 💡 PROPOSTA (a validar): els riscos Y7 i modal-de-reobertura només existeixen **si es puja `dev`
> abans del merge** — el codi que els introdueix són els 33 commits locals no pushats (§ 1). Si es
> desplega `origin/dev`, ni tan sols entren al sistema.

**Veredicte P4: 🟢 cap risc funcional sobre les dades de PROD. Cap reparació prèvia necessària.**

---

## 5. 🔴 Els dos gates que NO viatgen amb git

Això no era al brief i és **l'únic motiu real de NO-GO**. El delta del 09/07→10/07 conté l'sprint
S03a (aïllament del media per tenant + descàrrega gated). Les dues peces necessiten una acció
manual a PROD **que cap `git pull` ni cap `migrate_schemas` farà**.

### 🔴 Gate 1 — El media canvia d'arrel: cal moure els bytes

`origin/dev` introdueix a `backend/fhort/settings.py:184-187`:

```python
STORAGES = {'default': {'BACKEND': 'django_tenants.files.storage.TenantFileSystemStorage'}}
```

El codi que corre **ara** a PROD **NO TÉ aquest bloc `STORAGES`** (verificat: `git show
82702bf:backend/fhort/settings.py` no en conté cap) → PROD escriu i llegeix el media **pla**, a
`MEDIA_ROOT/<name>`. Amb el codi nou, el storage resol `MEDIA_ROOT/<schema>/<name>`.

**Conseqüència si es desplega sense fer res:** tots els fitxers existents (9,9 MB de media a PROD)
queden **fora de l'arrel que el codi buscarà** → logos, fitxers de model i adjunts deixen de
resoldre's. La BD no cal tocar-la: `FileField.name` ja és relatiu a l'arrel del tenant
(`move_media_tenant.py:6-9`).

**Pas obligatori, entre el `git pull` i el restart:**

```bash
python manage.py move_media_tenant            # dry-run: ensenya què mouria
python manage.py move_media_tenant --apply    # mou els bytes; normalitza owner a www-data (D19)
```

És idempotent i no escriu a la BD. `--apply` també fa el `chown www-data:www-data` del que crea
(decisió D19) — sense això, gunicorn (que corre com `www-data`) donaria `500 Permission denied` als
uploads.

### 🔴 Gate 2 — nginx: sense el bloc `/protected-media/`, les descàrregues tornen buides

El delta afegeix l'endpoint de descàrrega *gated* per `X-Accel-Redirect`. PROD té `DEBUG=false`, i
en aquest camí Django **no serveix els bytes**: emet la capçalera i delega a nginx. El vhost de PROD
(`/etc/nginx/sites-available/fhort-textile`, segons `docs/deploy.md:15-25`) **no té el bloc
`location /protected-media/`** — la config d'nginx no és al repo, per tant el merge no l'hi posa.

Citació literal de `docs/OPS_S03_NGINX.md:93-94`:

> *"A PROD (`DEBUG=false`) el camí real és el de nginx, i **sense el bloc `location
> /protected-media/` la descàrrega retornarà una resposta buida**. El bloc i el codi han d'anar
> junts."*

**Pas obligatori, al vhost 443 de PROD, abans (o alhora) del restart:**

```nginx
location /protected-media/ {
    internal;
    auth_basic off;
    alias /var/www/fhort-textile/backend/media/;   # ⚠️ path de PROD, no el de staging
}
```

```bash
nginx -t && systemctl reload nginx
```

**Veredicte § 5: 🔴 dos passos manuals obligatoris. Sense ells el deploy és tècnicament "verd"
(migra i arrenca) però funcionalment trencat en media i descàrregues.**

---

## 6. El que encara demana SSH (4 comandes, read-only)

Tot el pes de la diagnosi està cobert amb el dump i el repo. Queden 4 comprovacions que només dona
el servidor:

```bash
ssh root@178.105.217.125

# (1) Quin commit corre PROD exactament? (esperat: entre 82702bf i 6dc7347, del 2026-07-09)
git -C /var/www/fhort-textile log -1 --format='%h %ad %s' --date=iso
git -C /var/www/fhort-textile status -sb | head -1

# (2) Espai de disc (el deploy fa npm run build + migracions)
df -h /

# (3) El servei
systemctl is-active fhort.service && systemctl status fhort.service --no-pager | head -5

# (4) Confirmar els dos gates del § 5
grep -n "protected-media" /etc/nginx/sites-available/fhort-textile || echo "GATE 2: bloc ABSENT (esperat)"
ls /var/www/fhort-textile/backend/media/            # si NO hi ha subdir 'fhort/' → GATE 1 pendent
find /var/www/fhort-textile/backend/media/ ! -user www-data | head   # ha de sortir buit
```

---

## 7. Taula final de riscos

| # | Risc | Semàfor | Fet |
|---|---|---|---|
| 1 | Conflictes del merge `--no-ff` | 🟢 | `merge-tree` exit 0, intersecció ∅, tree resultant = `tree(origin/dev)` |
| 2 | Migracions destructives / lentes | 🟢 | Només **4 pendents, totes additives**; les destructives ja van córrer el 09/07 |
| 3 | Dades de PROD que calgui reparar (XE) | 🟢 | **0 divergències** base↔grading a tot PROD |
| 4 | Sessions de fitting reubicades pel redirect Y7 | 🟢 | **0 sessions vives** a PROD |
| 5 | Models que dispararan el modal de reobertura | 🟢 | **1** (model 169) |
| 6 | Servei / backup | 🟢 | `/api/schema/` 200 · backup d'avui 02:30 verificat |
| 7 | Skew bundle (09/07 11:19) vs backend (09/07 17:47) | 🟡 | El `npm run build` del deploy ho resol |
| 8 | Migració `tasks/0025` editada post-aplicació | 🟡 | Inert; deute cosmètic |
| 9 | Fila òrfena `files/0001` a `django_migrations` | 🟡 | Inert; no tocar |
| 10 | **Els 33 commits locals no pushats** | 🟠 | Decisió pendent: `tasks/0038` i tot l'sprint X/Y no entren si es desplega `origin/dev` |
| 11 | **Media: cal `move_media_tenant --apply`** | 🔴 | Sense això, els 9,9 MB de media existents queden orfes |
| 12 | **nginx: cal el bloc `/protected-media/`** | 🔴 | Sense això, les descàrregues tornen una resposta buida |
| 13 | Espai de disc a PROD | ⚪ | No verificable sense SSH (§ 6) |

---

## 8. GO / NO-GO

### 🟠 **GO CONDICIONAL** — condicionat als dos gates del § 5.

**Per què GO:** el merge és net (zero conflictes, zero contingut perdut); les migracions són 4 i
additives; les dades de PROD estan netes i no necessiten cap reparació; el backup d'avui està
verificat i és restaurable; el salt real de codi és petit (31 commits), no els 196 que semblava.

**Per què condicional:** el deploy passarà en verd (migrarà i arrencarà) i **tot i així deixarà PROD
funcionalment trencat** en media i descàrregues si no s'executen els dos passos manuals. Són el
tipus de pas que "un dia s'oblida" — precisament el que va motivar la decisió D19.

### Ordre de deploy proposat

> 💡 PROPOSTA (a validar pel CTO):

0. **Decidir abans de res:** es fa push de `dev` (33 commits, +`tasks/0038`, sprints X/Y) o es
   desplega `origin/dev` tal com està? *Tot el que segueix assumeix `origin/dev`.*
1. Backup manual addicional (el de les 02:30 ja hi és, però el deploy és a mig dia).
2. `git pull` a `main` a PROD.
3. **`python manage.py move_media_tenant` (dry-run) → revisar → `--apply`.** ← Gate 1
4. `python manage.py migrate_schemas` (mai `--schema`) → aplica les 4 additives ×2 schemas.
5. **Afegir el bloc `location /protected-media/` al vhost + `nginx -t && systemctl reload nginx`.** ← Gate 2
6. `cd frontend && npm run build` (corregeix també el skew del § 3).
7. `systemctl restart fhort.service`.
8. Verificar: `/api/schema/` → 200 · descàrrega d'un fitxer existent → bytes, no resposta buida ·
   `find backend/media/ ! -user www-data` → buit.

---

*Diagnosi Patró A. Cap fitxer del sistema modificat; l'única escriptura és aquest document.*
