# INCIDENT — staging inoperant (2026-07-10, 04:47–05:0x UTC)

> Staging `/var/www/ftt-staging`, branca `dev`, HEAD `655c325`. **PROD no afectat**
> (S03b no hi és desplegat, i viu en un altre servidor).
> Resolució: **restart del servei + `chown` de `media/fhort/`**. **Cap canvi de codi.**

## TL;DR

Dos problemes independents, cap dels dos un bug de codi:

1. **Procés enverinat** (causava el 500 generalitzat). Els workers de gunicorn duien 11 h en
   marxa amb el mòdul `models` d'abans d'S03b en memòria; en carregar l'URLconf *mandrosament*
   a la primera petició, van llegir del disc el `services_fitxers.py` **nou** contra aquell
   `models` **vell**. → `ImportError`. **No hi ha cap import circular.**
2. **`media/fhort/` de root** (causava el 500 concret que patia l'Agus a la fitxa tècnica).
   El va crear `move_media_tenant --apply` corrent com a root al deploy d'S03a (17:05 del dia 9).
   gunicorn corre com `www-data` → `PermissionError` a **tota** escriptura a media des d'aleshores.

---

## Q1 — Diagnosi

### La hipòtesi del brief (import circular) queda DESCARTADA

| Comprovació | Resultat |
|---|---|
| `manage.py check` ara mateix | **net** |
| `from fhort.wsgi import application; import fhort.urls` (procés fresc, root) | **OK** |
| El mateix, com a `www-data`, amb el cwd del servei | **OK** |
| Els 6 commits d'S03b, un per un, WSGI + `fhort.urls` en procés fresc | **`fa5df92` OK · `db5bfff` OK · `0f35b9a` OK · `59e3b5d` OK · `655c325` OK** |
| `grep` d'imports a `models.py` cap a `services_fitxers` | **cap** (només `tech_sheet_models` i `ftt_models`, línies 940/943) |
| `"circular import"` al journal | **0 ocurrències** |

**Prova negativa decisiva:** quan Python detecta un cicle, el missatge és
`cannot import name X from partially initialized module … (most likely due to a circular import)`.
El log diu, literalment:

```
ImportError: cannot import name 'ItemFitxer' from 'fhort.models_app.models'
             (/var/www/ftt-staging/backend/fhort/models_app/models.py)
```

Mòdul **plenament inicialitzat**, sense el nom. Això no és un cicle: és un mòdul **vell**.

### La causa real, amb la línia de temps

| Hora (UTC) | Fet | Evidència |
|---|---|---|
| 09/07 17:05 | Deploy d'S03a: `move_media_tenant --apply` com a root | `media/fhort/` propietari `root:root`, mtime 17:05 |
| 09/07 17:39:52 | Arrenca `ftt-staging.service`. Els workers importen `models.py` (**sense `ItemFitxer`**) | `ps -o lstart` PIDs 3593717/3593720/3593722 |
| 09/07 18:55:49 | Commit `fa5df92` introdueix `ItemFitxer` a `models.py` | `git log --date=iso` |
| 09/07 19:33 | Les proves d'S03b (com a root) creen `media/fhort/model_fitxers/2026/07/`, també de root | mtime del dir |
| 10/07 01:49 | Bots demanen `/api/.env`. Un worker carrega l'URLconf ara → codi **coherent** en memòria | `access.log`: 404 (no 500) |
| 10/07 04:47 | L'Agus entra. El **segon** worker carrega l'URLconf per primer cop → llegeix el `services_fitxers.py` nou contra el seu `models` vell | `access.log`: 200 i 500 **barrejats** al mateix minut |

L'interleaving 200/500 és la signatura del diagnòstic: **un worker sa i un d'enverinat**, servint
en round-robin. `ImportError` deixa `fhort.models_app.views` fora de `sys.modules`, i cada petició
posterior al worker malalt torna a fallar igual.

**Cadena de l'import** (`journalctl`):
`fhort/urls.py:29` → `models_app/urls.py:4` → `models_app/views.py:16`
(`from .services_fitxers import DOWNLOAD_SALT, DOWNLOAD_TTL`) → `services_fitxers.py:15`
(`from .models import ItemFitxer, ModelFitxer`) → **ImportError**.

### Per què el verd nocturn no ho va caçar (i no és un fals verd)

No hi havia res a caçar **al codi**. `manage.py check` i tots els imports corren en un **procés
fresc**; cap dels 6 commits falla. El que el verd no cobria era **l'estat del procés que ja
corria**: el servei mai es va reiniciar (regla "MAI deploy" dels agents), i el
`services_fitxers.py` del disc va acabar convivint amb un `models` en memòria de 76 minuts
abans. Verificar contra un servei que corre codi vell és verificar el passat.

---

## Q2 — Fix

**No hi ha fix de codi, perquè no hi ha bug de codi.** Aplicar un `import` mandrós o moure
`item_fitxer_upload_to` hauria estat "arreglar" un cicle inexistent, i el segon (moure la funció)
hauria trencat la migració `0054`, que la grava per path
(`fhort.models_app.models.item_fitxer_upload_to`, verificat a `0054_itemfitxer.py:27`).

Dues accions d'operació:

1. `systemctl restart ftt-staging.service` → l'API torna (401 sense token, `/api/schema/` 200).
2. `chown -R www-data:www-data media/fhort` → 0 directoris i 0 fitxers fora de `www-data`.

Únic commit de la sessió: `cc48ca8`, i **només toca `METODE_AGENTS.md`**.

---

## Q3 — Smoke complet, contra el servei viu

| Prova | Resultat |
|---|---|
| `GET /api/schema/` | **200** |
| `GET /api/v1/` sense token (×10) | **401** ×10 (cap 500) |
| `POST /api/token/` amb credencials falses | **401** (endpoint viu, no 500) |
| `GET /api/v1/models/?page_size=1` | **200**, `count: 20` |
| `GET /api/v1/model-fitxers/?model=188` | **200** |
| `GET /api/v1/item-fitxers/` | **200** |

### El cas de l'Agus: `BRW-SS27-0001` (model 188, sense `.ftt` previ)

És exactament el model dels 500 del log (`POST /api/v1/models/188/ftt-document/`, tres intents).

```
POST /api/v1/models/188/ftt-document/   →  201
   ModelFitxer 249 · tipus TECHSHEET · versio 1 · is_current True
   name a BD : /media/fhort/model_fitxers/2026/07/BRW-SS27-0001_fitxa.ftt
```

Bytes al disc, **amb prefix de tenant**:

```
media/fhort/model_fitxers/2026/07/BRW-SS27-0001_fitxa.ftt
   owner: www-data:www-data   mida: 451 b
   ZIP vàlid: ['document.json', 'manifest.json']
   manifest: magic=FTT  schema_version=1  kind=document
```

El document creat **es queda** (és el que l'Agus intentava fer; creació legítima, no residu).

### Descàrrega (D13) segueix operativa

| Prova | Resultat |
|---|---|
| `GET /model-fitxers/249/download/` (autenticat) | **200**, 451 b, sha256 idèntic al disc |
| `GET /model-fitxers/249/download-signed/?token=…` | **200**, 451 b, sha256 idèntic al disc |
| El mateix amb token invàlid | **403** |

---

## Q4 — Regles de mètode afegides (`METODE_AGENTS.md`, commit `cc48ca8`)

- **§2.1 — El verd d'una cadena backend acaba al servei viu**, no al `check`. Restart + smoke
  contra el servei. Si l'agent no pot reiniciar (regla "MAI deploy"), ho ha de declarar com a
  **acció pendent del CTO**, no donar la peça per verificada.
- **§2.2 — En verificació, tot endpoint mutant va dins `atomic()` amb rollback.** Un endpoint és
  mutant fins que es demostri el contrari: `open-task` és idempotent en el *resultat*, no en els
  *efectes* (obre timers, escriu transicions). [Incident del 2026-07-09.]
- **§4 — Tot `mkdir` dins `media/` va seguit de `chown www-data:www-data`.** Ja havia passat amb
  els logos del tenant; ara amb `move_media_tenant --apply` corrent com a root.

---

## Accions pendents per al CTO

1. **PROD: comprovar els permisos de `media/<schema>/`.** Allà també s'hi va córrer
   `move_media_tenant --apply` al deploy d'S03a. Si es va fer com a root, **tota escriptura a
   media hi està trencada des d'aleshores** (logos, PDFs, `.ftt` nous) i encara no s'ha notat
   perquè ningú n'ha pujat cap. Aquest servidor no té accés a PROD; no ho he pogut verificar.
   Comprovació: `find <media>/<schema> -type d ! -user www-data | head`.
2. **`move_media_tenant` hauria de fer `chown` dels directoris que crea**, o el runbook ha
   d'exigir-lo com a pas explícit després de l'`--apply`. Peça pròpia, no tocada aquí.
3. Revisar si convé `--preload` a gunicorn: amb `--preload`, un `ImportError` de l'URLconf mata
   l'arbiter en arrencar (fallada sorollosa i immediata) en comptes d'enverinar un worker en
   silenci hores després. Decisió d'operació, no de codi.
