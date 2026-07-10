# VERIFICACIÓ POST-DEPLOY — S03a (staging)

> Data: 2026-07-09 · **Patró A (verificació, no implementació)** · staging
> `/var/www/ftt-staging`, branca `dev`, HEAD `6dc7347`.
> Proves REALS contra l'entorn desplegat (gunicorn `127.0.0.1:8001` i nginx
> `https://staging.fhorttextile.tech`), no lectura de codi — excepte on s'indica.
> Cap canvi de codi, cap migració, cap edició de nginx. **Cap escriptura a la BD**: no ha
> calgut crear cap `ModelFitxer` de prova; hi havia fitxers reals suficients.
> Estat abans i després idèntic: **214 files a BD · 221 fitxers a disc**.

**Convenció:** `fitxer:línia`. Les discrepàncies s'anoten com a **FET**, mai com a proposta.

## Entorn confirmat abans de provar

| Comprovació | Evidència |
|---|---|
| Codi desplegat | `git log -1` → `6dc7347` (P3), working tree net excepte `DECISIONS.md` (fitxer d'estat, no es commiteja) |
| gunicorn actiu | `ss -tlnp` → `127.0.0.1:8001` (3 workers), `systemctl is-active` → `active` |
| Trasllat de media fet | `media/fhort/` amb **222 fitxers**; els 5 subdirs (`model_fitxers`, `import_sessions`, `bulk_imports`, `customer_logos`, `tenant_logos`) |
| `DEBUG=true` a staging | Confirmat pel comportament: cap capçalera `X-Accel-Redirect` a les respostes; s'exercita el **fallback `FileResponse`** (`services_fitxers.py:121`) |

**Fitxers reals usats** (tots dos amb bytes verificats a disc):
- `A` = id **39**, `TECHSHEET`, `BRW-26-SS-0002_fitxa.ftt`, 473 bytes, model 182.
- `B` = id **13**, `DOCUMENT`, `FTT-CO27-0001_DOCUMENT_001.pdf`, 690.815 bytes.

---

## Taula de resultats

| # | Prova | Resultat | Evidència |
|---|---|---|---|
| **1a** | `GET /download/` amb JWT vàlid | ✅ | `HTTP 200`, 473 bytes, `Content-Type: application/octet-stream` |
| **1b** | `GET /download/` sense token | ✅ | `HTTP 401` |
| **1c** | `GET /download/` amb id inexistent (5243) | ✅ | `HTTP 404`, `Content-Type: application/json`, cos `{"detail":"No ModelFitxer matches the given query."}` — **JSON, no HTML** |
| **2a** | `GET /download-signed/` amb token real de l'API | ✅ | `HTTP 200`, 473 bytes, sha256 idèntic al camí autenticat |
| **2b** | Token alterat (últim caràcter → `X`) | ✅ | `HTTP 403` |
| **2c** | Token del fitxer 39 usat a la URL del 13 | ✅ | `HTTP 403`, cos `El token no correspon a aquest fitxer.` |
| **2d** | Sense token | ✅ | `HTTP 403` |
| **2e** | `max_age` desplegat (per lectura de codi, no per espera) | ✅ | `DOWNLOAD_TTL = 900` a `services_fitxers.py:19`; consumit a `views.py:203` (`signing.loads(..., max_age=DOWNLOAD_TTL)`) |
| **3a** | Bytes rebuts == bytes a disc (fitxer A) | ✅ | 4 checksums idèntics (disc / autenticat / signat / `checksum` a BD) |
| **3b** | Bytes rebuts == bytes a disc (fitxer B, PDF 690 KB) | ✅ | 3 checksums idèntics |
| **3c** | El `.ftt` baixat és un ZIP íntegre | ✅ | `zipfile.namelist()` → `['document.json', 'manifest.json']` |
| **4a** | `download_url` a la resposta de `list` | ✅ | 214/214 registres (200 + 14 en 2 pàgines), **0 amb `null`** |
| **4b** | `download_url` absoluta i amb token | ✅ | Via nginx: `https://staging.fhorttextile.tech/api/v1/model-fitxers/39/download-signed/?token=…` |
| **5a** | `/protected-media/` és `internal` | ✅ | `HTTP 404` en accés directe per nginx |
| **5b** | Descàrrega signada end-to-end via nginx (TLS) | ✅ | `HTTP 200`, 473 bytes, sha256 correcte |

### Checksums (bloc 3)

Fitxer A — `model_fitxers/2026/06/BRW-26-SS-0002_fitxa_Q5Ya3Z1.ftt`:

```
disc   : db8bca452b8e03fcc17e1f3ad846e05751e596834361f1b12e080570b15c19a0
autent : db8bca452b8e03fcc17e1f3ad846e05751e596834361f1b12e080570b15c19a0
signat : db8bca452b8e03fcc17e1f3ad846e05751e596834361f1b12e080570b15c19a0
BD     : db8bca452b8e03fcc17e1f3ad846e05751e596834361f1b12e080570b15c19a0
```

Fitxer B — `model_fitxers/2026/06/FTT-CO27-0001_DOCUMENT_001.pdf` (690.815 bytes):

```
disc   : 7f9f310f033c1d9c7db6be85b4cef4e9f3bca88f7071e233fb03c2196bd39fbe
autent : 7f9f310f033c1d9c7db6be85b4cef4e9f3bca88f7071e233fb03c2196bd39fbe
signat : 7f9f310f033c1d9c7db6be85b4cef4e9f3bca88f7071e233fb03c2196bd39fbe
```

---

## Discrepàncies trobades (FETS, no propostes)

### FET 1 — la fila FANTASMA retorna **500**, no 404

`GET /api/v1/model-fitxers/6/download/` (fila `BRW-SS26-0001_DOCUMENT_001.pdf`, coneguda com a
fantasma: té `fitxer` informat però **no té bytes a disc**) retorna:

```
HTTP 500   Content-Type: text/html
FileNotFoundError at /api/v1/model-fitxers/6/download/
```

Causa (lectura de codi): el guard de `serve_model_file` és
`services_fitxers.py:114` → `if not fitxer.fitxer:`. Per a la fila fantasma el `FileField`
té **nom** (truthy), per tant el guard NO dispara i s'arriba a
`services_fitxers.py:121` → `FileResponse(fitxer.fitxer.open('rb'), …)`, que peta amb
`FileNotFoundError`. El guard comprova que hi hagi *nom*, no que hi hagi *bytes*.

Abast del fet:
- Amb `DEBUG=true` (staging, avui) → **500 HTML**.
- Amb `DEBUG=false` (PROD) el camí seria `services_fitxers.py:126` (`X-Accel-Redirect`), que
  **no toca el disc**: nginx trobaria l'`alias` inexistent i respondria **404**. És a dir, el
  símptoma difereix per entorn.
- Afecta **1 fila** de 214 al tenant `fhort` (l'única fantasma coneguda).

### FET 2 — la branca `JsonResponse` del 404 no s'exercita amb les dades actuals

El fix del revisor-diff de la sessió anterior (404 en JSON, no HTML) viu a
`services_fitxers.py:116` → `JsonResponse({'error': 'El fitxer no té bytes associats.'}, status=404)`.
Aquesta branca només s'assoleix amb `fitxer` **buit** (`''`/`NULL`), i a la BD n'hi ha **0**:

```sql
SELECT count(*) FILTER (WHERE fitxer='' OR fitxer IS NULL), count(*) FROM fhort.models_app_modelfitxer;
→ 0 | 214
```

El 404 JSON observat a la prova **1c** (id inexistent) **NO ve d'aquesta línia**: ve del
`get_object()` de DRF (`{"detail": "No ModelFitxer matches the given query."}`). Tots dos són
JSON, per tant la prova 1c passa; però convé no confondre les dues portes.

### FET 3 — `Content-Disposition` difereix entre les dues branques

Amb `DEBUG=true` la capçalera observada és la de `FileResponse`:

```
Content-Disposition: attachment; filename="BRW-26-SS-0002_fitxa.ftt"
```

La branca X-Accel (`services_fitxers.py:128-129`) emet el format RFC 5987
(`attachment; filename*=UTF-8''…`). Els dos són vàlids; el nom ASCII d'aquest fitxer no permet
distingir-los en el resultat. Anotat perquè la forma de la capçalera **canvia amb `DEBUG`**.

---

## Conclusió

**S03a verificat end-to-end a staging.** Els quatre blocs de proves demanats passen sense
excepcions (14/14 comprovacions ✅), amb bytes idèntics per checksum entre disc, BD, endpoint
autenticat i endpoint signat, i amb el gate funcionant als quatre casos negatius (sense token,
token alterat, token creuat, sense autenticació).

Reserves explícites, cap de les quals invalida la verificació:

1. La branca **`X-Accel-Redirect` no s'ha exercitat en aquesta sessió**, perquè staging corre
   amb `DEBUG=true` i s'agafa el fallback `FileResponse`. La branca es va verificar per separat
   durant la implementació forçant `DEBUG=False`, i el `location /protected-media/` s'ha
   confirmat avui com a `internal` (404 en accés directe). El camí complet
   *Django → X-Accel → nginx serveix els bytes* **només es podrà provar amb `DEBUG=false`**.
2. El **FET 1** (500 en la fila fantasma) és una discrepància real del codi desplegat, no de la
   infraestructura. No s'ha tocat, per instrucció.
