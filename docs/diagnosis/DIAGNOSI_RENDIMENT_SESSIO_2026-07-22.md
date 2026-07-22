# DIAGNOSI — RENDIMENT I SESSIÓ (expulsions de login + percepció de lentitud)

> ## ⚠️ PARCIALMENT IMPLEMENTADA — 2026-07-22 (sprint de rendiment, Patró B)
>
> **NO es mou a `arxiu/`**: el bloc 🟡 CAPACITAT segueix VIGENT i sense decidir. Es
> segella només el que s'ha construït.
>
> | Punt del veredicte | Estat | Commit |
> |---|---|---|
> | **1** refresh JWT mai cridat | ✅ FET | `3ce17ba` |
> | **2** JS/CSS sense gzip | ✅ FET | `3ec5dca` |
> | **3** N+1 de grading-rule-sets | ✅ FET (3.683 → 10 queries) | `d7a6386` |
> | **4** paginació sense ordre | ✅ FET | `7a1e5fd` |
> | **5** N+1 de models/ | ✅ FET (407 → 7) | `d7a6386` |
> | **6** vendor-konva al preload | ✅ FET | `5d176cd` |
> | **7** N+1 de size-systems/ | ✅ FET (35 → 8) | `d7a6386` |
> | **12** config sense versionar | ✅ FET (`ops/nginx/`) | `3ec5dca` |
> | **20** cap `log_format` amb temps | ✅ FET | `3ec5dca` |
> | **8-11** CAPACITAT (workers, Anthropic síncron, CONN_MAX_AGE, shared_buffers) | 🟡 **VIGENT** — fora d'abast del sprint, pendent de decisió | — |
> | **21** gunicorn-error.log d'assessment sense rotar | 🟡 **VIGENT** — no és FTT | — |
> | **13-19** 🟢 soroll | — confirmats com a soroll, res a fer | — |
>
> **Correcció a la capçalera d'aquesta diagnosi:** les «dues premisses que cauen» (§⚠️)
> contenen una confusió de dominis sobre què hi ha desplegat en aquesta màquina. No afecta
> cap de les mesures ni cap de les peces implementades —totes són de codi i de config, i
> valen igual a qualsevol entorn— però **no s'ha de citar aquell bloc com a font**.
>
> **Troballa nova de la implementació** (no era a la diagnosi): amb el `prefetch_related`
> ben posat, `targets.values_list()` i `targets.first()` del serializer **encara** feien
> 1 query per fila cadascun — construeixen un queryset NOU i per tant ignoren la cache del
> prefetch. Eren 45 de les 55 queries que quedaven. Amb `.all()`: 10.

> **Data:** 2026-07-22 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
> **Abast:** separar PERCEPCIÓ / BUG / CAPACITAT amb dades, per als dos símptomes reportats:
> **S1** *"de tant en tant t'expulsa i et fa tornar a logar"* (Salva, comercial, ús normal) i
> **S2** *"a vegades sembla que vagi lent"* (Agus, percepció general, sense endpoint concret).
> Objectiu de negoci: saber ON invertir davant del creixement d'usuaris.
>
> **Convenció:** tota afirmació porta `fitxer:línia` o una xifra mesurada. **"NO EXISTEIX" = confirmat
> absent** (grep exhaustiu, no especulat). Les propostes van marcades `💡 PROPOSTA (a validar)` i
> **no** són decisions: les decisions són humanes (Patró C).
>
> **Guardes complertes:** cap escriptura de codi, cap commit, cap migració, **cap restart de cap
> servei** · BD només `SELECT`/`EXPLAIN` · peticions HTTP només `GET` (test client in-process) ·
> `migrate_schemas --list` no usat · **cap valor de secret llegit ni imprès** (només l'existència de
> les variables) · únic fitxer creat: aquest.
> No s'ha tocat res del radi de la **Sessió A paral·lela** (Camí A, promoció model→item).

---

## ⚠️ DUES PREMISSES DEL BRIEF QUE CAUEN

**1. `/var/www/fhort-textile` NO EXISTEIX, i `fhort.service` NO és FTT.** `fhort.service` és
*"FHORT Assessment Gunicorn"* — una app **Flask** a `/var/www/assessment` (`wsgi:app`), servida a
`assessment.fhort.cat`. **No hi ha cap desplegament de PROD de l'ERP FTT en aquesta màquina.**

**2. Per tant el Salva NO treballa a PROD: treballa a staging.** L'evidència és concloent —
`assessment.fhort.cat` té **104 peticions i 0 respostes 401 en 14 dies**, mentre que
`staging.fhorttextile.tech` en té **1.096 de 401 d'app** i **104 re-logins** repartits entre
**dos** usuaris humans reals (IPs `79.155.56.127` i `79.155.57.244`).

Això encaixa amb el que ja sabíem: no hi ha SSH a PROD i el seu estat es llegeix del backup diari.
**Conseqüència pràctica: tot el que segueix es mesura sobre l'entorn on la gent treballa de veritat.**

---

## RESUM EXECUTIU

1. **S1 no és intermitent ni misteriós: és determinista, i la causa és una peça que existeix i mai
   es fa servir.** L'access token dura **1 hora** (`backend/fhort/settings.py:226`), el refresh token
   dura **7 dies** (`:227`)... i **el frontend no crida MAI l'endpoint de refresh**. Existeix al
   backend (`urls.py:19`, `urls_public.py:28`) i té **zero cridadors** al frontend. L'interceptor de
   resposta (`frontend/src/api/client.js:14-24`) tracta **qualsevol** 401 com a fi de sessió: esborra
   **els dos** tokens —inclòs el refresh, vàlid 6 dies i 23 hores més— i fa
   `window.location.href='/login'`, un **hard reload** que es menja la feina en curs.

2. **Els logs ho confirmen amb precisió de rellotge.** El 20/Jul, l'usuari `79.155.56.127`:
   login a **05:32:47** → següent login a **06:34:13**. **61 minuts i 26 segons.** I la signatura és
   inconfusible: ràfegues de **6-11 respostes 401 al mateix segon** (totes les XHR de la pantalla
   morint alhora) seguides d'un `POST /api/token/`. En 14 dies: **0 peticions a `/api/token/refresh`**
   contra **104 logins nous**. `GET /api/v1/me/` té **719 401 vs 653 200** — falla el **52 %** de les
   vegades.

3. **S2 no es pot mesurar avui, i això és en si mateix la troballa.** No existeix cap `log_format`
   personalitzat a `/etc/nginx/` (grep → **cap resultat**): el vhost usa `combined`, que **no porta
   `$request_time` ni `$upstream_response_time`**. **El p95 per endpoint és literalment incalculable.**
   Estem cecs a la latència real, i qualsevol conversa sobre "va lent" serà d'opinions mentre això no
   canviï.

4. **Però el culpable de S2 s'ha trobat igualment, mesurant-lo directament: `GET
   /api/v1/grading-rule-sets/?page_size=200` fa 3.682 queries, 526 KB i 4,1 segons.** És la crida
   literal del frontend (`GradingRuleSets.jsx:65`). És **N+1 pur** —3,2 queries per regla— i no manca
   d'índex: cada query individual triga 0,05 ms i usa índex. La prova que és evitable és que
   `GradingRuleViewSet` fa servir **el mateix serializer** amb `select_related` i costa **5 queries i
   25 ms**: mateixes dades, **736× menys queries**.

5. **El frontend es serveix SENSE COMPRIMIR, i això degrada cada càrrega de tothom, avui.**
   `/etc/nginx/nginx.conf:46` té `gzip on;` però **la línia `gzip_types` està comentada** (`:53`). El
   default d'nginx per a `gzip_types` és **només `text/html`** → **els `.js` i `.css` viatgen en cru**.
   La càrrega inicial real són **1,06 MB** en comptes de **342 KB**: **3,2× més del que caldria**, per
   una línia de config.

6. **La capacitat NO és el coll d'ampolla avui — però la configuració és de joguina.** 8 nuclis i
   9,2 Gi de RAM lliures per a un servei amb **2 workers sync** (l'11,8 % de la recomanació `2×CPU+1`
   = 17), sense `preload`, sense `max_requests`, amb `timeout 300`. La BD sencera fa **42 MB** i la
   taula més gran de `fhort` **1,1 MB**: optimitzar índexs aquí no serveix de res. **El primer límit
   que es tocarà és la concurrència de gunicorn**, no la BD ni la RAM.

7. **La intersecció dels punts 4 i 6 és el que fa mal de veritat.** Amb **2 workers sync**, un sol
   usuari obrint la pantalla de Grading Rule Sets ocupa **el 50 % de tota la plataforma durant 4
   segons**. Dos usuaris alhora la deixen a zero. No és teoria de creixement: són dos usuaris.

---

## BLOC B1 — CICLE DE VIDA JWT (la causa de S1)

### B1.1 Config real de SimpleJWT

Bloc únic: `backend/fhort/settings.py:225-232`.

| Clau | Valor real | Origen | `ruta:línia` |
|---|---|---|---|
| `ACCESS_TOKEN_LIFETIME` | **`timedelta(hours=1)`** | explícit | `settings.py:226` |
| `REFRESH_TOKEN_LIFETIME` | **`timedelta(days=7)`** | explícit | `settings.py:227` |
| `ROTATE_REFRESH_TOKENS` | `True` | explícit | `settings.py:228` |
| `BLACKLIST_AFTER_ROTATION` | `False` | explícit | `settings.py:229` |
| `AUTH_HEADER_TYPES` | `('Bearer',)` | explícit (= default) | `settings.py:230` |
| `UPDATE_LAST_LOGIN` | `True` | explícit | `settings.py:231` |
| **`SIGNING_KEY`** | **NO ESPECIFICAT** → `settings.SECRET_KEY` | default de la llibreria | `venv/…/rest_framework_simplejwt/settings.py:20` |
| `ALGORITHM` | no especificat → `HS256` | default | `…/simplejwt/settings.py:19` |
| **`LEEWAY`** | no especificat → **`0`** | default | `…/simplejwt/settings.py:26` |

`grep -n "SIGNING_KEY" backend/fhort/settings.py` → **cap resultat**. `LEEWAY=0` vol dir **zero
tolerància** de desfasament de rellotge en validar `exp`.

### B1.2 La `SECRET_KEY` és estable — l'escenari "deploy" queda descartat

- `SECRET_KEY = os.environ['SECRET_KEY']` (`settings.py:18`), accés **per clau dura**, sense fallback.
- `grep -rn "get_random_secret_key" backend/fhort/` → **cap resultat**: no es genera mai al vol.
- `.env` carregat a `settings.py:15`; el fitxer `backend/.env` **existeix** (600, www-data) i la
  variable `SECRET_KEY` **hi consta 1 vegada**. *Valor no llegit ni imprès.*

> **Un `systemctl restart` NO invalida cap token.** I malgrat que hi ha hagut **43 restarts de
> staging en 7 dies**, els 401 **no hi correlacionen** (§B2.3).

### B1.3 El frontend, baula a baula

| Baula | `ruta:línia` | Què fa |
|---|---|---|
| Login (component) | `frontend/src/pages/Login.jsx:47,79` | `await login(username, password)` |
| Login (store) | `frontend/src/store/auth.js:38` | `client.post('/api/token/', …)` |
| Desa access | `frontend/src/store/auth.js:40` | `localStorage.setItem('access_token', …)` |
| Desa refresh | `frontend/src/store/auth.js:41` | `localStorage.setItem('refresh_token', …)` |
| Injecta el token | `frontend/src/api/client.js:8-12` | interceptor de **request**: `Authorization: Bearer …` |
| **Davant d'un 401** | **`frontend/src/api/client.js:14-24`** | **§B1.4 — LA baula** |
| Logout del store | `frontend/src/store/auth.js:72-77` | neteja + `AUTH_INVALID` + `window.location.href` |
| `fetchMe()` amb 401 | `frontend/src/store/auth.js:64` | `get().logout()` |
| Guard de rutes | `frontend/src/App.jsx:72-78` | `AUTH_INVALID` → `<Navigate to="/login">` |

**On viu el token: `localStorage`** — persistent i **compartit entre pestanyes** del mateix origen.
Cap cookie, cap `sessionStorage`.

### B1.4 Què passa davant d'un 401 — el codi literal

```js
client.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)
```
— `frontend/src/api/client.js:14-24`

**NO EXISTEIX cap refresh. NO EXISTEIX cap retry.** Confirmació exhaustiva:

```
grep -rn "refresh_token|token/refresh|refreshToken" frontend/src frontend-backoffice/src
→ frontend/src/api/client.js:19   (removeItem)
→ frontend/src/store/auth.js:41   (setItem)
→ frontend/src/store/auth.js:74   (removeItem)
```

**Tres resultats: es desa i s'esborra, mai s'usa.** Cap `_retry`, cap cua de peticions, cap
`isRefreshing`. I `window.location.href` (no `navigate`) força una **recàrrega completa de l'SPA**:
es perd tot l'estat en memòria i qualsevol feina no desada.

**Dos agreujants:**

- **`initAuth` no mira l'`exp`** (`store/auth.js:26-35`): marca `AUTH_VALID` **només per la presència
  del string** al `localStorage`. Amb un access caducat l'app es pinta, `fetchMe()` rep 401
  (`auth.js:64`) i expulsa → **flaix d'aplicació seguit d'expulsió** en fer F5.
- **108 crides `fetch()` crues en 26 fitxers** (p.ex. `App.jsx:118`, `ModelSheet.jsx:94`) munten la
  capçalera a mà i **no passen per cap interceptor de resposta**: amb el token mort **fallen en
  silenci** (la dada simplement no apareix). L'expulsió arriba després, a la primera crida axios.

### B1.5 Multi-pestanya i rotació: descartats com a causa

- `grep -rn "addEventListener('storage'"` → **cap resultat**: **NO EXISTEIX** sincronització entre
  pestanyes.
- `ROTATE_REFRESH_TOKENS=True` però `BLACKLIST_AFTER_ROTATION=False` (`settings.py:228-229`) → encara
  que es fes refresh, el token antic **seguiria essent vàlid**.
- `token_blacklist` **NO EXISTEIX a INSTALLED_APPS** (`settings.py:36-58,62-74`): les taules
  `token_blacklist_*` no s'han migrat mai.
- I sobretot: **el refresh no es crida mai** → la rotació **no s'exerceix a la pràctica**.

> El que **sí** passa entre pestanyes: un 401 en una pestanya buida el `localStorage` **compartit** →
> les altres queden sense token → **expulsió en cascada** al primer clic. Sense l'esdeveniment
> `storage`, ni se n'assabenten fins llavors.

### B1.6 Endpoints d'auth: existeixen, i un no el crida ningú

| Endpoint | urlconf tenant | urlconf public | El frontend el crida? |
|---|---|---|---|
| login `api/token/` | `backend/fhort/urls.py:18` | `urls_public.py:27` | **SÍ** (`endpoints.js:13`, `auth.js:38`) |
| **refresh `api/token/refresh/`** | `backend/fhort/urls.py:19` | `urls_public.py:28` | **MAI** |
| verify `api/token/verify/` | `backend/fhort/urls.py:20` | `urls_public.py:29` | **MAI** |

### B1.7 La cadena exacta de l'expulsió

```
t=0      Login → POST /api/token/ → access(1h) + refresh(7d) a localStorage   [auth.js:38-41]
t=0..1h  Cada petició porta Bearer access                                     [client.js:9-10]
t=1h     L'access expira (LEEWAY=0 → sense marge)
t=1h+ε   Primera petició axios posterior → 401
         → esborra access_token I refresh_token                               [client.js:17-19]
         → window.location.href='/login'  ← HARD RELOAD                       [client.js:20]
         → El comercial perd la pantalla i el que estigués escrivint.
         → El refresh token, vàlid 6 dies i 23 h més, es llença sense haver-lo usat mai.
```

**Per què es percep com "de tant en tant" i no "cada hora":** el rellotge corre des del **LOGIN**, no
des de l'última activitat — **no hi ha sliding window**. I si l'usuari està en una pantalla que només
fa `fetch()` cru, l'expulsió es **retarda** fins a la primera crida axios. D'aquí que els intervals
reals mesurats siguin 61, 86, 92 min… i no exactament 60.

> **Veredicte B1:** escenari **(i) caducitat de l'access sense refresh**, sense cap ambigüitat.
> Rotació multi-pestanya **(ii)** i canvi de clau per deploy **(iii)** queden **descartats amb
> evidència**. El sistema té la peça per evitar-ho —un refresh token de 7 dies i un endpoint que el
> consumeix— i **no la connecta mai**.

---

## BLOC B2 — LOGS (evidència dura)

### B2.1 Finestra realment coberta

| Log | Política | Finestra REAL |
|---|---|---|
| `/var/log/nginx/*.log` (`/etc/logrotate.d/nginx`) | `daily`, `rotate 14`, `compress` | **08/07 00:00 → 22/07 07:15 = 14 dies** ✔ |
| journald | `journald.conf` tot comentat → defaults, persistent (2,2 GB) | des de **04/05**; unit `ftt-staging` des de **11/06** = **41 dies** ✔ |
| `/var/www/assessment/gunicorn-error.log` | **cap entrada a `/etc/logrotate.d/`** | **NO ROTA MAI** (1,5 MB i creixent) |

Els 7 dies demanats hi són sencers, sense forats.

### B2.2 `journalctl -u ftt-staging.service` (7 dies)

| Fet | Comptes 7d |
|---|---|
| Reinicis del servei (`Stopping…/Started`) | **43** (16 Jul 6 · 17 Jul 11 · 18 Jul 3 · 19 Jul 12 · 20 Jul 6 · 21 Jul 3 · 22 Jul 2) |
| `Permission denied: '/var/www/.gunicorn'` | **43** (exactament **1 per boot**) |
| **`WORKER TIMEOUT`** | **0** (i 0 en tot l'històric del unit) |
| OOM kill / `Out of memory` | **0** |
| `Main process exited` / `Failed` / `Scheduled restart` | **0** |
| `Traceback` | 10 |

**Tots els reinicis són manuals** (deploy / `systemctl restart`). Cap caiguda.

**Què és `/var/www/.gunicorn`** — resolt: `ftt-staging.service` corre com `User=www-data`, el **home
de `www-data` és `/var/www`**, i **gunicorn 26.0.0** arrenca un *control server* que vol crear el seu
directori d'estat a `$HOME/.gunicorn`. `/var/www` és `drwxr-xr-x root:root` → `EPERM`. El servei
arriba igualment a `"Gunicorn arbiter booted"`, escolta a `127.0.0.1:8001` i serveix normalment;
l'únic que es perd és una funció **opcional** de control en runtime. → **SOROLL PUR, zero impacte.**
(PROD/assessment no el té: gunicorn 23.0.0, sense control server.)

### B2.3 nginx — els 401, i per què no són culpa dels deploys

**Codis d'estat (14 dies, 69.568 línies):** 301 → 30.382 · 200 → 14.839 · 404 → 14.597 ·
**401 → 3.224** · **499 → 1.817** · 400 → 1.147 · 302 → 1.077 · 304 → 1.010 · **5xx → 51**.

**Separació senyal/soroll dels 3.224 401:**

| Tipus | Comptes | Naturalesa |
|---|---|---|
| **401 a `/api/…` (JWT de l'app)** | **1.096** | **SENYAL** |
| 401 fora de `/api/` (`/`, `/.env`, `/.git/config`…) | 2.128 | `auth_basic` d'nginx: bots i scanners. SOROLL |

**401 d'app per dia:** 08→3 · 09→10 · 10→25 · 12→2 · 13→17 · 14→26 · 15→5 · 16→22 ·
**17→798** · 18→5 · 19→35 · 20→61 · 21→86 · 22→1.

El pic del **17 Jul** és artificial: **762 dels 798 en l'hora 10:00**, tots des de
`178.105.48.204` (IP del propi servidor) amb UA `HeadlessChrome/149.0.7827.55` — una **tirada E2E**.
Els restarts d'aquell dia són a 04:43, 06:12, 07:03, 07:22, 08:15, 12:55, 12:59, 13:00, 17:54,
18:02: **cap a les 10:xx**.

**401 d'app per hora, excloent el 17 Jul (baseline real):** distribució **plana les 24 h** — hi ha
401 de matinada (00h→6, 02h→6, 04h→19, 05h→21), quan no hi ha ningú treballant.

> **Correlació 401 ↔ restart: NEGATIVA. Correlació 401 ↔ caducitat de token: POSITIVA i exacta.**

### B2.4 La signatura de l'expulsió, en cru

Usuari `79.155.56.127` (l'humà més actiu: 8.595 respostes 200, **508 401**):

```
[20/Jul/2026:16:55:37] /api/v1/me/                        401
[20/Jul/2026:16:55:37] /api/v1/onboarding/status/         401
[20/Jul/2026:16:55:37] /api/v1/customers/                 401
[20/Jul/2026:16:55:37] /api/v1/calendar/events/           401  (×2)
[20/Jul/2026:16:55:37] /api/v1/tenant-config/             401
[20/Jul/2026:16:55:37] /api/v1/model-task-items/by-model/ 401  (×2)
[20/Jul/2026:16:55:37] /api/v1/models/fase-counts/        401
        …11 respostes 401 al MATEIX SEGON…
[20/Jul/2026:16:55:54] /api/token/                        200   ← re-login manual, 17 s després
```

Bursts idèntics: 20/Jul 06:34:08 (7 · 401), 12:43:27 (6), 16:55:37 (11).

**Cadència dels re-logins del 20/Jul** (`POST /api/token/`): 05:32:47 → 06:34:13 (**61 min 26 s**) →
11:11:28 (4 h 37 m) → 12:43:32 (**92 min**) → 15:29:57 (2 h 46 m) → 16:55:54 (**86 min**) →
18:16:35 (**80 min**).

| Mètrica (14 dies) | Valor |
|---|---|
| Peticions a `/api/token/refresh…` | **0** |
| `POST /api/token/` (logins nous) | **104** (64 d'un usuari, 38 de l'altre) |
| `/api/v1/me/`: 200 vs **401** | 653 vs **719** → **52 % de fallada** |

**Sonda fantasma:** `79.155.56.127` va fer `POST /api/v1/ftt-documents/335/lock/` → 401 **cada 10
minuts exactes** des del 20/Jul 19:24 fins al 21/Jul 04:xx (**68 respostes 401**): una pestanya
oberta amb el token mort, fent polling per sempre sense refrescar mai.

### B2.5 El punt cec: no es pot mesurar la latència

`grep -rn "log_format" /etc/nginx/` → **cap resultat.** El vhost `sites-enabled/ftt-staging` **no té
`access_log` ni `error_log` propis** → cau al default (`nginx.conf:40`), format **`combined`**, que
**no porta `$request_time`, ni `$upstream_response_time`, ni `$host`**.

> **Top-10 endpoints més lents (p95/max): IMPOSSIBLE DE CALCULAR amb la config actual.** I com que
> tampoc hi ha `$host`, els logs de staging estan **barrejats** amb els d'`assessment.fhort.cat` i
> `stagingbackoffice`, separables només per path/referer/IP.

**El millor proxy disponible és `$body_bytes_sent`:**

| Endpoint | Bytes 14d | Crides | **Mitjana/resposta** |
|---|---|---|---|
| `/api/v1/ftt-documents/{id}/asset/…bin/` | 42,9 MB | 4 | **10,7 MB** |
| `/api/v1/patterns/pattern-files/{id}/geometry/` | 58,3 MB | 254 | **230 KB** |
| **`/api/v1/grading-rule-sets/`** | **50,1 MB** | **118** | **425 KB** |
| `/api/v1/model-fitxers/{id}/download-signed/` | 17,3 MB | 4 | 4,3 MB |
| `/api/schema/` | 5,8 MB | 10 | 580 KB |

> **TROBALLA TRANSVERSAL:** els **425 KB de mitjana** de `grading-rule-sets/` mesurats als logs
> **confirmen independentment** els **526 KB** que B3 va mesurar in-process (§B3.2). Dues
> metodologies, el mateix endpoint.

**Endpoints més cridats (14d):** `/api/v1/me/` 1.620 · `onboarding/status/` 955 ·
`calendar/events/` 847 · `tenant-config/` 732 · `customers/` 598 · `watchpoints/` 538 ·
`models/{id}/` 461 · `models/` 409 · `ftt-documents/{id}/` 401 · `suppliers/` 377.

### B2.6 Els 499 i el silenci dels errors

| Dia | 499 |
|---|---|
| 09→1 · 10→9 · 11→2 · 16→5 | |
| **17 Jul** | **1.795** ← la mateixa tirada HeadlessChrome |
| 19→4 · 20→1 | |

**Fora del 17 Jul: 22 en 13 dies → ~1,7 499 humans/dia.**

`error.log` d'nginx (14d): `upstream timed out` → **0** · 502/504 → **0** · `worker_connections` →
**0**. El fitxer actual fa **0 bytes**. Els 51 5xx en 14 dies inclouen 2 a `/api/token/` (500).

### B2.7 PROD (assessment) — sa i buit

| Mètrica | Valor |
|---|---|
| Uptime del servei | des del **08/07 06:52** — **2 setmanes sense reiniciar** |
| Restarts 7d / 30d | **0** / **1** |
| `WORKER TIMEOUT` / OOM / crash | **0** |
| Tràfic 14d | **104 peticions** |
| **401** | **0** |
| **5xx** | **0** |

> **Veredicte B2:** per a **S1 hi ha evidència dura i causa identificada** — 0 crides de refresh
> contra 104 re-logins, ràfegues de 401 simultanis seguides de `POST /api/token/`, i un interval
> mesurat de 61 min 26 s. Els 43 restarts **no** hi correlacionen. Per a **S2 no hi ha evidència
> dura i no se'n pot tenir** amb la config actual: sense `$request_time`, el p95 per endpoint és
> incalculable; els indicadors indirectes són tranquils (0 `WORKER TIMEOUT`, 0 timeouts d'upstream,
> 0 OOM, ~1,7 499 humans/dia). El `Permission denied: '/var/www/.gunicorn'` és **soroll pur**
> (1 per boot, servei plenament funcional).

---

## BLOC B3 — ELS ENDPOINTS PESATS (mesurats, no assumits)

**Metodologia:** `TenantClient` (django-tenants) sobre `fhort`, usuari real, `DEBUG=True` +
`CaptureQueriesContext`. **Només GET.** Temps = mediana de 3 execucions després d'un warm-up,
in-process (sense xarxa ni serialització HTTP real → els temps reals de l'usuari són **pitjors**).

### B3.1 El N+1 de garment-types: ja arreglat — s'ha mudat als MODELS

El deute anotat a `DIAGNOSI_S03C_NAVEGACIO.md:503` (`get_poms_count`) **està resolt**:
`GarmentTypeItemViewSet` (`tasks/views_b.py:857-864`) i `GarmentTypeViewSet` (`pom/views.py:108-111`)
ja anoten els comptadors.

| Endpoint | queries | items | bytes | ms |
|---|---|---|---|---|
| `GET /api/v1/garment-types/` | **5** | 21 de 21 | 9.471 | 15 |
| `GET /api/v1/garment-type-items/?page_size=200` | **5** | 62 | 15.422 | 36 |

**Però el llistat de MODELS fa 2 queries per fila:**

| Query repetida | Origen |
|---|---|
| `tasks_garmenttypeitem` × N | `models_app/serializers.py:90` (`source='garment_type_item.name'`) |
| `tasks_customer` × N | `models_app/serializers.py:92` (`source='customer.nom'`) |

El `select_related` de `models_app/views.py:146-148` porta `garment_type, garment_group, responsable,
responsable__user, size_system, grading_rule_set` — **hi manquen `garment_type_item` i `customer`**,
tots dos FK directes de `Model` i tots dos **amb índex a la BD**.

| Petició | queries | fórmula |
|---|---|---|
| `/api/v1/models/` (page_size=25) | **57 per 25 items** | `7 + 2N` |
| `/api/v1/models/?page_size=200` | **407 per 200 items** | `7 + 2N` |

### B3.2 Els quatre sospitosos, amb xifres

| # | Endpoint | queries | items | bytes | ms | Paginació REAL? |
|---|---|---|---|---|---|---|
| **a'** | **`grading-rule-sets/?page_size=200`** | **3.682** | 45 / 1.148 regles | **538.345 (526 KB)** | **4.145** | **De facto NO** |
| a | `grading-rule-sets/` (page_size=25) | **1.978** | 25 de 45 | 284.785 | 2.371 | Sí (25) |
| a'' | `…?amb_regles=1&page_size=200` | 3.678 | 43 | 537.811 | 3.810 | igual |
| b | `models/` | 57 | 25 de **1005** | 16.115 | 90 | **Sí, real** |
| b' | `models/?page_size=200` | 407 | 200 | 128.395 | 502 | Sí |
| **c** | **`models/163/taula-mesures/`** | **12 (constant)** | 321 GradedSpec | 9.926 | **23** | N/A |
| c' | `models/268/taula-mesures/` | **12** | — | 16.937 | 18 | N/A |
| c'' | `size-fittings/53/taula-mesures/` | **6** | 321 GradedSpec | 8.450 | 27 | N/A |

**`max_page_size=200` ≥ catàleg sencer (45 rulesets) → la paginació d'(a) no pagina res a la
pràctica.** I el frontend demana exactament `page_size=200` (`GradingRuleSets.jsx:65`).

**Anatomia de l'N+1 d'(a).** `GradingRuleSetViewSet` (`pom/views.py:169-174`) fa
`prefetch_related('regles')` **sense `select_related` dins del prefetch**. El `GradingRuleSerializer`
(`pom/serializers.py:130-166`) toca 3 relacions per regla:

| Query repetida | vegades (page_size=200) | Origen |
|---|---|---|
| `pom_pommaster` | **1.148** (1 per regla) | `serializers.py:143,151,155,159,163` |
| `pom_sizedefinition` | **1.148** | `serializers.py:165` (`talla_base.etiqueta`) |
| `pom_pomglobal` | **1.091** | `serializers.py:145,150,154,158,162` |
| `pom_target` (M2M + method field) | 90 + 45 | `serializers.py:193-194` |
| `pom_rulesetscopenode` | 45 | `serializers.py:205-214` |
| `pom_constructiontype` / `pom_fittype` | 43 + 43 | `serializers.py:195-196` |

**Ràtio: 3,2 queries per regla.** I la prova que és plenament evitable: **`GradingRuleViewSet`
(`views.py:239-241`) fa servir el MATEIX serializer** amb
`select_related('pom__pom_global','talla_base','rule_set')`, i
`GET /api/v1/grading-rules/?page_size=200` costa **5 queries / 90.413 bytes / 25 ms**.
**Mateixes dades, 736× menys queries.**

### B3.3 Altres catàlegs sense filtre

| Endpoint | queries | bytes | Diagnòstic |
|---|---|---|---|
| `size-systems/?page_size=200` | **34** (25 × `pom_target`) | 39.909 | N+1 a `serializers.py:113-114`; falta `prefetch_related('targets')` a `views.py:62` |
| `garment-pom-maps/?page_size=200` | 5 | **167 KB** | 1.748 files; sense filtre retorna mitja taula en una pàgina |
| `poms/?page_size=200` | 5 | 148 KB | 364 files; OK |
| `customer-pom-aliases/?page_size=200` | 5 | 98 KB | 310 files; OK |

### B3.4 🔴 Bug col·lateral trobat: **paginació sense ordre garantit**

DRF emet `UnorderedObjectListWarning` per a **`GradingRuleSet`, `SizeSystem` i `CustomerPOMAlias`**:
l'atribut `ordering` (p.ex. `pom/views.py:179`) és **inert** perquè `filter_backends`
(`pom/views.py:176`) **no inclou `OrderingFilter`** i el `Meta.ordering` del model és buit.

> **Conseqüència: la paginació d'aquests tres endpoints pot repetir o saltar files entre pàgines.**
> No és rendiment — és **correcció de dades**. És exactament el problema que ja es va corregir a
> `GarmentTypeViewSet` (comentari a `pom/views.py:104-107`) i a `GarmentTypeItemViewSet`
> (`tasks/views_b.py:854-856`), i que aquí no es va aplicar.

### B3.5 Índexs i mides: no hi ha res a optimitzar

| Taula (`fhort`) | files | mida |
|---|---|---|
| `patterns_patternpoint` | 4.655 | **1.168 kB** |
| `models_app_model` | **1.005** | 712 kB |
| `fitting_gradedspec` | 1.827 | 552 kB |
| `pom_gradingrule` | **1.148** | 480 kB |
| `pom_garmentpommap` | 1.748 | 440 kB |
| `pom_gradingruleset` | **45** | 200 kB |

**Cap taula passa d'1,2 MB. Tota la BD del tenant cap folgadament a la `shared_buffers`.**

`EXPLAIN (ANALYZE, BUFFERS)` de les queries principals:

| Query | Pla | Temps |
|---|---|---|
| `models_app_model ORDER BY prioritat DESC LIMIT 25` | **Seq Scan** + top-N heapsort (`shared hit=39`) | **2,06 ms** |
| `pom_gradingrule WHERE rule_set_id IN (…)` | Index Scan `…_rule_set_id_90e5a4da` | 0,047 ms |
| `pom_pommaster WHERE id=?` | Index Scan pkey | 0,076 ms |
| `fitting_gradedspec WHERE grading_version_id=53` | Index Scan `…_grading_version_id_0928a72f` | 0,093 ms |
| `pom_garmentpommap LIMIT 200` | Seq Scan (3 buffers) | 0,089 ms |

- **Cap FK sense índex** a les taules implicades (verificat a `models_app_model`, `pom_gradingrule`,
  `fitting_gradedspec`).
- **Únic Seq Scan sobre taula "gran"**: `models_app_model` en ordenar per `prioritat` (camp sense
  índex) → **2 ms de 90 ms totals (2,2 %)**. Irrellevant.
- Les 3.682 queries d'(a) són **totes Index Scan de 0,05-0,08 ms**.

> **El cost no és la base de dades: és l'overhead de round-trip Python↔Postgres multiplicat per
> 3.682.** Afegir índexs no arreglaria absolutament res.

> **Veredicte B3:** el pitjor endpoint és **`grading-rule-sets/?page_size=200`** — 3.682 queries,
> 526 KB, **4,1 s** — i el problema és **N+1 pur**, no manca d'índex ni de paginació. Segon:
> `models/`, amb 2 queries per fila per dos `select_related` absents. **La `taula-mesures` de
> l'Escalat, sospitosa a priori, és l'endpoint més sa del lot**: 6-12 queries constants i 18-27 ms
> fins i tot sobre el model amb més `GradedSpec` del tenant. **El "va lent" es correspon amb la
> pantalla de Grading Rule Sets, no amb el board de models ni amb l'escalat.**

---

## BLOC B4 — CAPACITAT

### B4.1 Gunicorn: 2 workers sync sobre 8 nuclis

| Servei | Projecte | Workers | Class | Threads | Timeout | `max_requests` | `preload` |
|---|---|---|---|---|---|---|---|
| **`ftt-staging.service`** | **FTT staging** | **2** | **sync** (cap `-k`) | 1 | **300 s** | **no** (∞) | **no** |
| `fhort.service` | Assessment (Flask) | 3 | sync | 1 | 30 | no | no |
| `trading.service` | Trading (Flask) | 3 | sync | 1 | 120 | no | no |

**NO EXISTEIX cap `gunicorn.conf.py`** en cap projecte: tota la config viu a la línia `ExecStart`.
`Type=notify`, `Restart=on-failure`, `User=www-data`, bind `127.0.0.1:8001`. Nginx davant:
`proxy_read_timeout 300s`, `client_max_body_size 25M` (`sites-enabled/ftt-staging:31-33`).

**Hardware real:** `nproc` = **8** · RAM **15 Gi** (6,1 usats / **9,2 disponibles**) · swap 451 Mi de
2,0 Gi · load 1,07/0,45/0,41 · uptime **75 dies**.
*(El load d'1,07 en el moment de mesurar era un `manage.py test` a 89 % de CPU, no tràfic.)*

Consum de FTT staging (cgroup): **197,4 MB** els 3 processos (arbiter 28 MB + workers 174 i 56 MB).

**L'aritmètica del bloqueig.** Recomanació estàndard `2×CPU+1` = **17 workers**. Estem a **2** →
**11,8 % de la capacitat recomanada**, amb 8 nuclis pràcticament ociosos.

| Escenari (2 workers sync) | Capacitat consumida | Efecte |
|---|---|---|
| **1 petició de 4,1 s** (Grading Rule Sets, §B3.2) | **50 %** durant 4,1 s | **Un sol usuari, avui** |
| 1 petició de **30 s** (import de fitxa, propagació) | **50 %** durant 30 s | Queda 1 worker per a *tot* |
| **2 peticions de 30 s alhora** | **100 %** | **Servei aturat; tothom veu spinner** |
| Petició mitjana ~100 ms | throughput ≈ **20 req/s** | — |
| Amb 1 worker ocupat 30 s | **10 req/s** → ~300 peticions diferides | — |
| Amb 17 workers, la mateixa petició de 30 s | **5,9 %** | Impacte invisible |

**Quatre agreujants concrets:**

1. **`--timeout 300`**: gunicorn no mata un worker penjat fins als **5 minuts**. Un bug de propagació
   en bucle → mig servei mort 5 minuts, no 30 s.
2. **Sense `--max-requests`**: cap reciclatge; qualsevol fuita de memòria s'acumula indefinidament.
3. **Sense `--preload`**: cada worker carrega Django sencer (~87 MB × N en comptes de copy-on-write).
4. **Worker `sync`**: zero paral·lelisme intra-worker. Qualsevol espera d'I/O bloqueja el worker
   sencer — i `extraction_service.py` fa **crides a l'API d'Anthropic dins d'una request**.

### B4.2 El veïnatge de la màquina

**32 serveis systemd `running`. No hi ha cap Frappe/ERPNext corrent** (zero processos `frappe`/`bench`).

| Procés | Projecte | RSS |
|---|---|---|
| **VS Code Server ×2 + Pylance ×2 + tsserver ×2 + Claude ×3** | **Eines de dev (root)** | **~3,9 GB** |
| `trading.service` (gunicorn ×4) | Trading | 402 MB |
| `webiafy-backoffice` + `webiafy-web` | Webiafy | 271 MB |
| `fhort.service` (gunicorn ×4) | Assessment | 219 MB |
| **`ftt-staging.service` (gunicorn ×3)** | **FTT** | **197 MB** |
| `postgresql@18-main` | BD | ~123 MB + backends |
| `textile-tech.service` (Astro SSR) | Web corporativa | 93 MB |

> **El consumidor dominant de RAM de la màquina no és cap aplicació: són les eines de
> desenvolupament (~3,9 GB, com a root).** Les 6 apps web juntes fan **~1,2 GB**. **La RAM no és el
> coll d'ampolla.**

### B4.3 Postgres: defaults de fàbrica, i una BD minúscula

| Paràmetre | Valor | Comentari |
|---|---|---|
| Versió | **PostgreSQL 18.4**, cluster `18-main`, **port 5433** | (el cluster 16 al 5432 està **inactiu**) |
| `max_connections` | **100** | default |
| **`shared_buffers`** | **128 MB** | **default de compilació**, en una màquina de 15 Gi |
| `work_mem` | 4 MB | default |
| `effective_cache_size` | 4 GB | default |
| pgbouncer / pool extern | **no instal·lat** | — |
| Connexions actives ara | **11 backends**, 8 dels quals interns de Postgres | staging sense tràfic |
| **Mida de `ftt_staging`** | **42 MB** | — |

**Django:** el bloc `DATABASES` (`backend/fhort/settings.py:118-127`) porta `ENGINE`, `NAME`, `USER`,
`HOST`, `PORT` **i res més**. **`CONN_MAX_AGE` NO EXISTEIX** al fitxer (grep → 0 coincidències) → val
el **default de Django, `0`**:

- Django obre i tanca una connexió TCP+auth **a cada petició HTTP** (~1-5 ms + **fork real** d'un
  backend de Postgres, que és process-per-connection).
- Amb `django_tenants`, cada connexió nova ha de fer a més el `SET search_path` → **una anada i
  tornada addicional per petició**.
- Sostre dur sense pool: **workers gunicorn totals ≤ ~90**. Amb 2 workers, el límit el marcarà
  gunicorn molt abans que Postgres.

`shared_buffers=128 MB` és el paràmetre més clarament infra-dimensionat (la recomanació és ~25 % de
RAM ≈ 3,8 GB), **però avui la BD sencera (42 MB) hi cap dins**: no fa mal fins als ~120 MB de dades.

### B4.4 Frontend: 1,06 MB servits en cru

Build a `frontend/dist` (servit per nginx, `sites-enabled/ftt-staging:18`). Total **3,3 MB** en 91
fitxers. **No hi ha `.gz` ni `.br` precomprimits.**

**Càrrega inicial REAL** (segons els `<script type=module>` + `modulepreload` de `dist/index.html`):

| Fitxer | Cru | gzip |
|---|---|---|
| `index-Clj-vKsq.js` | 446.096 | 144.514 |
| `vendor-react-DdwBTl41.js` | 317.725 | 102.011 |
| **`vendor-konva-44T8MLO7.js`** | **317.577** | **95.818** |
| `endpoints-BI4SRFcd.js` | 20.008 | 4.049 |
| `rolldown-runtime-aKtaBQYM.js` | 1.084 | 652 |
| `index-ruNwdUY2.css` | 9.900 | 3.014 |
| **TOTAL INICIAL** | **1.112.390 B (1,06 MB)** | **350.058 B (342 KB)** |

*(El chunk més gros del build, `vendor-pdf` de 510 KB, **no** és a la càrrega inicial: està ben
carregat en lazy.)*

**🔴 Dos problemes concrets:**

1. **nginx NO comprimeix JS ni CSS.** `/etc/nginx/nginx.conf:46` té `gzip on;` **però la línia
   `gzip_types` està comentada** (`:53`), igual que `gzip_vary`, `gzip_proxied` i `gzip_comp_level`.
   El default d'nginx per a `gzip_types` és **només `text/html`** → **els `.js` i `.css` viatgen
   sense comprimir**. La càrrega inicial real per xarxa és **1,06 MB i no 342 KB**: **3,2× més**.
2. **`vendor-konva` (317 KB) és al `modulepreload` de l'`index.html`** → es baixa a **cada** càrrega,
   encara que l'usuari només vagi al Dashboard. Konva només el necessiten les pàgines de canvas. És
   **~28 % de la càrrega inicial crua** que sobra per a la majoria de sessions.

A més, el `<head>` carrega **`@tabler/icons-webfont` sencer des de jsDelivr** i **Google Fonts**
(2 famílies, 5+4 pesos): **CDN de tercers al camí crític del render**.

**El code-splitting, en canvi, està ben fet:** `frontend/src/App.jsx:9-52` té **44 crides a
`lazy(() => import(...))`**, una per pàgina, i `frontend/vite.config.js:19-38` separa explícitament
`vendor-konva`, `vendor-paper`, `vendor-pdf` i `vendor-react`. **La intenció és correcta; el que
falla és que konva acaba igualment al preload de l'entry.**

> **Veredicte B4:** la capacitat **no és el coll d'ampolla avui** —8 CPU i 9,2 Gi lliures, BD de
> 42 MB, zero connexions actives— **però la configuració és de joguina i el marge no s'aprofita**:
> 2 workers sync sobre 8 nuclis, sense `preload`, sense `max_requests`, `timeout 300`. **El primer
> límit que es tocarà és la concurrència de gunicorn**, no la BD ni la RAM. **El segon límit ja fa
> mal ARA a cada usuari**: 1,06 MB de JS sense gzip per una línia comentada a `nginx.conf:53`.

---

## VEREDICTE FINAL — PERCEPCIÓ / BUG / CAPACITAT

Ordenat per **impacte real en l'experiència del Salva i de l'Agus**.

### 🔴 BUG — arreglable ja, amb cost conegut

| # | Què | Evidència | Qui ho pateix | Cost |
|---|---|---|---|---|
| **1** | **Expulsió cada ~1 h: el refresh token existeix i no es fa servir mai.** Interceptor que davant de qualsevol 401 esborra els dos tokens i fa hard reload | `client.js:14-24` · `settings.py:226-227` · **0 crides de refresh vs 104 re-logins en 14 d** · interval mesurat **61 min 26 s** | **Salva** (i tothom) | **PETIT** — interceptor amb refresh+retry i cua de peticions; l'endpoint ja existeix (`urls.py:19`) |
| **2** | **JS i CSS servits SENSE gzip**: `gzip_types` comentat → default = només `text/html`. 1,06 MB en comptes de 342 KB a cada càrrega | `nginx.conf:46` vs `:53` · `dist/index.html` | **Tothom, a cada càrrega** | **TRIVIAL** — descomentar 1 línia de config. **La millor relació esforç/impacte de tota la diagnosi** |
| **3** | **`grading-rule-sets/?page_size=200`: 3.682 queries, 526 KB, 4,1 s.** N+1 pur (3,2 queries/regla) | `pom/views.py:169-174` sense `select_related` intern · `serializers.py:130-166` · **confirmat pels logs: 425 KB × 118 crides** | **Agus** (és "el va lent") | **PETIT** — el patró correcte ja existeix al fitxer del costat: `views.py:239-241` fa 5 queries amb el **mateix serializer** |
| **4** | **Paginació sense ordre garantit** a `GradingRuleSet`, `SizeSystem`, `CustomerPOMAlias`: poden **repetir o saltar files** entre pàgines | `UnorderedObjectListWarning` de DRF · `pom/views.py:176,179` | Silenciós, i és **correcció de dades, no rendiment** | **PETIT** — ja resolt a `views.py:104-107` i `views_b.py:854-856`; només cal aplicar-hi el mateix |
| **5** | **`models/`: 2 queries per fila** (`garment_type_item` i `customer` fora del `select_related`) → 407 queries amb `page_size=200` | `models_app/views.py:146-148` vs `serializers.py:90,92` | Agus (board de models) | **TRIVIAL** — 2 noms a una llista |
| **6** | **`vendor-konva` (317 KB) al preload inicial** de totes les pàgines, quan només el fan servir les de canvas | `dist/index.html` · `vite.config.js:19-38` | Tothom | **PETIT** |
| **7** | `size-systems/`: N+1 de 25 queries per `targets` | `pom/serializers.py:113-114` · `views.py:62` | Menor | **TRIVIAL** |

### 🟡 CAPACITAT — inversió a planificar segons creixement

| # | Què | Estat AVUI | Quan mossegarà |
|---|---|---|---|
| **8** | **2 workers sync sobre 8 nuclis** (11,8 % de `2×CPU+1`), sense `preload`, sense `max_requests`, `timeout 300` | **Ja mossega**: un sol usuari a Grading Rule Sets ocupa el **50 %** de la plataforma 4 s | **És el PRIMER límit.** Dos usuaris fent un import alhora = servei a zero fins a 300 s |
| **9** | **Crides a l'API d'Anthropic dins d'una request síncrona** amb worker `sync` | `extraction_service.py` | Fa el punt 8 molt pitjor: `gthread`/`gevent` no és opcional si això es manté |
| **10** | **`CONN_MAX_AGE=0`** → connexió nova + `SET search_path` a cada petició | Invisible amb 42 MB de BD | Amb tràfic sostingut |
| **11** | **`shared_buffers=128 MB`** (default de fàbrica en una màquina de 15 Gi) | Invisible: la BD sencera hi cap | Quan la BD passi dels ~120 MB |
| **12** | **`gzip_types`, `preload`, `max_requests` i el `log_format` viuen tots a config sense versionar** | — | Cada re-provisió del servidor els torna a perdre |

### 🟢 PERCEPCIÓ / SOROLL — no cal fer res

| # | Què | Per què no cal |
|---|---|---|
| **13** | `Permission denied: '/var/www/.gunicorn'` — 43 en 7 dies | **1 per boot.** Gunicorn 26 vol el dir del *control server* a `$HOME` de `www-data` (`/var/www`, root:root). El servei arrenca i serveix igualment; només es perd una funció opcional |
| **14** | Els **43 restarts** de staging en 7 dies | Tots **manuals** (deploy). Cap caiguda: 0 `WORKER TIMEOUT`, 0 OOM, 0 `Failed` en tot l'històric del unit |
| **15** | El pic de **798 401 i 1.795 499** del 17/Jul | Una tirada **HeadlessChrome** des de la IP del propi servidor. Fora d'aquell dia: **~1,7 499 humans/dia** |
| **16** | Els **2.128 401 fora de `/api/`** | `auth_basic` d'nginx contra bots i scanners (`/.env`, `/.git/config`) |
| **17** | La **`taula-mesures`** de l'Escalat, sospitosa a priori | **L'endpoint més sa del lot**: 6-12 queries constants, 18-27 ms sobre el model amb 321 `GradedSpec` |
| **18** | **Índexs i mida de dades** | Cap FK sense índex; la taula més gran fa 1,1 MB; l'únic Seq Scan costa **2 ms de 90**. **No hi ha res a optimitzar aquí** |
| **19** | **PROD (assessment)** | 0 restarts en 30 d, 0 401, 0 5xx, 104 peticions en 14 d |

### ⚫ EL PUNT CEC — no és cap de les tres columnes, i condiciona totes

| # | Què | Conseqüència |
|---|---|---|
| **20** | **No existeix cap `log_format` personalitzat** (`grep -rn "log_format" /etc/nginx/` → 0). El vhost usa `combined`: **sense `$request_time`, sense `$upstream_response_time`, sense `$host`** | **El p95 de latència per endpoint és incalculable**, i els logs de staging estan barrejats amb els d'assessment i el backoffice. Mentre això no canviï, cada conversa sobre "va lent" serà d'opinions. **Aquesta diagnosi ha hagut de mesurar els endpoints in-process precisament per això** |
| **21** | `/var/www/assessment/gunicorn-error.log` **no rota mai** (cap entrada a `/etc/logrotate.d/`) | 1,5 MB i creixent. Higiene, no urgent |

---

## 💡 PROPOSTES (a validar — NO són decisions)

- **L'ordre natural sembla 2 → 1 → 3**, no per gravetat sinó per relació esforç/impacte: el gzip és
  una línia i el nota tothom a la següent càrrega; el refresh és la peça que treu el dolor diari del
  Salva; l'N+1 de grading-rule-sets és el que l'Agus percep com "va lent".
- **El punt 20 (el `log_format`) probablement hauria d'anar primer de tot** encara que no arregli res
  per si sol: sense ell no es podrà verificar que cap de les altres peces ha funcionat, ni detectar
  la propera regressió. Mesurar abans d'optimitzar.
- **Els punts 3, 5 i 7 són el mateix defecte tres vegades** (serialitzar relacions sense
  `select_related`/`prefetch_related`), i el repo ja conté el patró correcte a
  `pom/views.py:239-241`. Val la pena mirar si és una peça sola.
- **El punt 8 (workers) i el punt 3 (4,1 s) es multipliquen entre si.** Arreglar l'N+1 baixa la
  pressió sobre els workers molt més barat que apujar-ne el nombre — però amb 8 nuclis ociosos,
  quedar-se a 2 workers sync és deixar la màquina sense fer servir.
- **Cap d'aquestes propostes és una decisió.** Les decisions són humanes (Patró C).

---

*Diagnosi Patró A. Cap línia de codi tocada, cap servei reiniciat, cap secret llegit. Les propostes
marcades `💡` no són decisions.*
