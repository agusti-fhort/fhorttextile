> ⚠️ SUPERADA 2026-07-07 — triage puntual tancat (causa 401/token, no bug de codi; capa d'import reworked després). Consulta només com a històric.

# DIAGNOSI — 403 a la pujada de l'Import Wizard

**Patró:** A (read-only — cap canvi, cap push, cap migrate, cap restart)
**Branca:** dev · **Entorn:** staging (staging.fhorttextile.tech) · **Data:** 2026-06-24
**Equip:** director-investigació + investigador-codi (×3 blocs paral·lels) + documentador (PROTOCOL_FASE_B)
**Sospita inicial:** regressió de la poda d'ahir (`8048e77`) a `extraction_views.py` / urls d'import.

---

## TL;DR (per als impacients)

- **L'endpoint de pujada (pas 1) és** `POST /api/v1/import-sessions/cribratge/` → [extraction_views.py:278](backend/fhort/models_app/extraction_views.py#L278).
- **Gating efectiu:** `JWTAuthentication + SessionAuthentication` (DEFAULT) + `IsAuthenticated`. **Cap permís custom. Cap `@csrf_exempt` (no cal: `@api_view` ja és csrf_exempt a Django; CSRF només s'activaria via SessionAuth).**
- **REPRODUCCIÓ (la prova decisiva): aquest endpoint retorna `401`, MAI `403`, davant qualsevol problema de token** — ho he comprovat a les DUES capes (gunicorn:8001 i nginx:443).
- **La poda `8048e77` queda EXONERADA:** només va esborrar dos endpoints MORTS (`extract-from-file`, `create-from-extraction`) sense cap consumidor al frontend; el gating de `cribratge` és intacte i idèntic. **A més, la poda ni tan sols està desplegada** (el gunicorn en marxa encara serveix els endpoints esborrats → corre codi ranci pre-poda).
- **Veredicte:** el bloqueig que viu l'usuari és de tipus **AUTH-token absent/expirat → 401**, no PERMÍS ni CSRF, i **fora de l'àmbit de la poda**. Si l'usuari veu literalment un `403` amb un token vàlid fresc, NO el pot generar aquest endpoint (vegeu §Veredicte, punt obert).

---

## BLOC 1 — FRONTEND: quin endpoint crida la pujada

### 1A. Component del wizard de 5 passos
Hi ha DOS wizards diferents; cal no confondre'ls:

| Component | Passos | Endpoint pas 1 | És el del 403? |
|---|---|---|---|
| [ImportWizard.jsx](frontend/src/components/ImportWizard/ImportWizard.jsx) | **5** (sizes·poms·measures·fabric·save) | `/api/v1/import-sessions/cribratge/` | **SÍ** — el prompt diu "5 passos" |
| [BulkImportWizard.jsx](frontend/src/pages/BulkImportWizard.jsx) | 4 | `/api/v1/bulk-import/upload/` | No (és el bulk de 4 passos) |

Passos definits a [ImportWizard.jsx:12-16](frontend/src/components/ImportWizard/ImportWizard.jsx#L12). Pas 1 = pujada + cribratge.

### 1B. Endpoint EXACTE de la pujada
[ImportWizard.jsx:135-150](frontend/src/components/ImportWizard/ImportWizard.jsx#L135) — `handleUpload()`:
```javascript
const fd = new FormData()
fd.append('document', file)
fd.append('model_id', model.id)
fd.append('garment_type_item_code', model.garment_type_item_code || '')
const res = await fetch(`${API}/api/v1/import-sessions/cribratge/`, {
  method: 'POST', headers: authHeaders, body: fd,
})
```
- **URL final:** `https://staging.fhorttextile.tech/api/v1/import-sessions/cribratge/` (`API = VITE_API_URL`, [.env](frontend/.env): `VITE_API_URL=https://staging.fhorttextile.tech`)
- **Mètode:** POST · **Content-Type:** `multipart/form-data` (FormData → el browser posa el boundary; NO es força Content-Type)
- **Camps:** `document` (fitxer), `model_id`, `garment_type_item_code`

### 1C. Headers / autenticació
[ImportWizard.jsx:81-82](frontend/src/components/ImportWizard/ImportWizard.jsx#L81):
```javascript
const token = localStorage.getItem('access_token')
const authHeaders = { Authorization: `Bearer ${token}` }
```
- **`Authorization: Bearer <JWT>`** (de `localStorage.access_token`). **Cap cookie de sessió** (fetch sense `credentials:'include'`). **Cap capçalera CSRF.**
- ⚠️ Aquest component usa **`fetch()` pelat**, NO la instància axios `client`. Per tant **NO té l'interceptor de resposta-401 que fa auto-logout** ([client.js:18-26](frontend/src/api/client.js#L18)). Si el token caduca, la crida rep el codi d'error i el wizard mostra `import_wizard.err_status {status}` ([ImportWizard.jsx:148](frontend/src/components/ImportWizard/ImportWizard.jsx#L148)) sense renovar sessió.
- **Comparació amb la resta de l'app:** totes les altres crides usen la mateixa autenticació JWT (`Bearer` de `localStorage`), via l'axios `client` amb interceptor que injecta el token. Mateix esquema d'auth; només canvia el transport (fetch vs axios).

---

## BLOC 2 — BACKEND: la vista i el seu gating

### 2A. View → [extraction_views.py:275-278](backend/fhort/models_app/extraction_views.py#L275)
```python
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def import_session_cribratge_view(request):
    # POST /api/v1/import-sessions/cribratge/
    # multipart: document (fitxer), model_id, garment_type_item_code
```
El cos llegeix `request.FILES.get('document')` i retorna `400` (falta fitxer / falta model_id), `404` (model inexistent), `500` (sense ANTHROPIC_API_KEY). **Cap branca retorna `403`.**

### 2B. Auth + permission EFECTIVES
DEFAULT de [settings.py:169-176](backend/fhort/settings.py#L169):
```python
'DEFAULT_AUTHENTICATION_CLASSES': (JWTAuthentication, SessionAuthentication),
'DEFAULT_PERMISSION_CLASSES': (IsAuthenticated,),
```
- **Autenticació:** JWT (primari) + Session (secundari).
- **Permís:** `IsAuthenticated` explícit. **Cap capability custom** (no CONFIGURE/EXECUTE_TASKS, no `HasCapability`). Qualsevol usuari autenticat del tenant id=6 (Montse, Marta) passa el permís.
- **CSRF:** `@api_view` aplica `csrf_exempt` a nivell Django; el `CsrfViewMiddleware` ([settings.py:89](backend/fhort/settings.py#L89)) no afecta la view. CSRF només s'activaria DINS de `SessionAuthentication.enforce_csrf`, i això requereix que JWT torni `None` (cap header Bearer) i que una cookie de sessió Django autentiqui un usuari — escenari que la SPA (només-JWT) no produeix.

### 2C. Registre d'URL — NO és 404 emmascarat
[urls.py:62-63](backend/fhort/models_app/urls.py#L62): `path('import-sessions/cribratge/', import_session_cribratge_view, name='import-session-cribratge')`. La ruta existeix i respon (no és catch-all ni redirect). Rutes d'import vives post-poda: `cribratge/`, `<token>/talles/`, `<token>/extraccio/`, `<token>/poms/`, `<token>/grading-preview/`, `<token>/mesures/`, `<token>/library-prefill/`, `<token>/teixit/`, `<token>/confirmar/`.

---

## BLOC 3 — LA PODA D'AHIR (`8048e77`, 2026-06-23 15:43 UTC)

### 3A. Diff
`-541` línies a `extraction_views.py`, `±6` a `urls.py`. El que va treure d'`urls.py`:
```diff
-        extract_from_file_view,
-        create_from_extraction_view,
...
-        path('models/extract-from-file/', extract_from_file_view),
-        path('models/create-from-extraction/', create_from_extraction_view),
+        # P6 — camí d'import VELL retirat (0 consumidors al frontend; el wizard nou és l'únic camí).
```
Les dues views esborrades tenien gating **idèntic** al de cribratge:
```python
-@api_view(['POST'])
-@permission_classes([IsAuthenticated])
-@parser_classes([MultiPartParser, FormParser])
-def extract_from_file_view(request): ...
```
Commits `5ded3d4` i `1ed8f84` (24h) **no toquen** `extraction_views.py` gating.

### 3B. ABANS/DESPRÉS del gating de l'endpoint de pujada VIU
| Aspecte | Abans (`8048e77^`) | Després (`8048e77`) | Canvi? |
|---|---|---|---|
| View pujada | `extract_from_file_view` | `import_session_cribratge_view` | ruta sí, **gating no** |
| Auth | DEFAULT (JWT+Session) | DEFAULT (JWT+Session) | **NO** |
| Permís | `IsAuthenticated` | `IsAuthenticated` | **NO** |
| Parser | `MultiPartParser,FormParser` | `MultiPartParser,FormParser` | **NO** |
| `@csrf_exempt` | (no en té) | (no en té) | **NO** |

**La poda NO va canviar el gating.** `import_session_cribratge_view` ja existia abans i va sobreviure intacta. La poda només va retirar el camí VELL (mort).

---

## BLOC 4 — GERMANS: pujades multipart que SÍ funcionen

| Endpoint | Fitxer:línia | Auth | Permís | Parser | CSRF |
|---|---|---|---|---|---|
| **cribratge (el del 403)** | extraction_views.py:278 | DEFAULT | `IsAuthenticated` | MultiPart,Form | exempt (JWT) |
| upload_file (ModelFitxer) | views.py:841 | DEFAULT | `IsAuthenticated` | MultiPart,Form | exempt |
| TechSheetExtractView | tech_sheet_views.py:51 | DEFAULT | `IsAuthenticated` | MultiPart | exempt |
| bulk-import/upload | bulk_import_views.py:45 | DEFAULT | `IsAuthenticated` | MultiPart,Form | exempt |
| FittingPhotoViewSet | fitting/views.py:549 | DEFAULT | `IsAuthenticated` | MultiPart,Form | exempt |
| size-map/grading-preview-file | pom/size_map_views.py:317 | DEFAULT | `HasCapability(CONFIGURE)` | DRF default | exempt |

**Divergència de gating: CAP** (excepte size-map, que és MÉS estricte amb capability i tot i així funciona). El cribratge té exactament el mateix esquema que els germans vius. No hi ha cap asimetria que expliqui un 403 propi.

---

## BLOC 5 — REPRODUCCIÓ (read-only, sense escriure dades)

Curl amb `-H "Host: staging.fhorttextile.tech"`, contra gunicorn (`127.0.0.1:8001`) i nginx (`https://127.0.0.1`):

| # | Petició | Resultat | Cos exacte |
|---|---|---|---|
| A | POST multipart, **sense** `Authorization` | **HTTP 401** | `{"detail":"Credencials d'autenticació no disponibles."}` |
| B | POST multipart, `Authorization: Bearer null` | **HTTP 401** | `{"detail":"Given token not valid for any token type","code":"token_not_valid",...}` |
| D | POST, sense Bearer + cookie `sessionid` falsa | **HTTP 401** | `{"detail":"Credencials d'autenticació no disponibles."}` |
| 443 | Igual que A però via nginx (port 443) | **HTTP 401** | mateix cos → **nginx no injecta 403** (`auth_basic off` a `location /api/`) |

**Cap variant produeix un 403.** Per a generar un `403` net amb `IsAuthenticated` caldria: (a) usuari autenticat però permís fals → impossible aquí (cap permís custom), o (b) `SessionAuthentication` + CSRF Failed → inabastable en el flux SPA només-JWT (sempre envia `Bearer`, mai cau a SessionAuth). DRF retorna `401` (no `403`) perquè el primer autenticador (JWT) posa capçalera `WWW-Authenticate: Bearer`.

### Troballa col·lateral — DESPLEGAMENT RANCI
- L'endpoint **esborrat per la poda** `POST /api/v1/models/extract-from-file/` **encara respon `401`** (route viva) al gunicorn en marxa (PID 1541953, arrencat 2026-06-23 17:32) → **el procés corre urls.py PRE-poda**. Al disc, [urls.py](backend/fhort/models_app/urls.py) ja NO l'importa (post-poda). ⇒ **la poda no està desplegada; falta restart de gunicorn** (operativa, no causa del 403).
- El build desplegat `frontend/dist` (2026-06-23 17:32) ja crida `import-sessions/cribratge` (frontend nou). Backend ranci però `cribratge` també hi és (preexisteix la poda) → no hi ha mismatch que generi 403.

---

## VEREDICTE

1. **Endpoint de pujada:** `POST /api/v1/import-sessions/cribratge/` → [extraction_views.py:278](backend/fhort/models_app/extraction_views.py#L278), cridat per `fetch()` amb `Authorization: Bearer <JWT>` des de [ImportWizard.jsx:143](frontend/src/components/ImportWizard/ImportWizard.jsx#L143).
2. **Gating efectiu:** JWT+Session (DEFAULT) + `IsAuthenticated`. Sense permís custom, sense CSRF aplicable a la SPA.
3. **Tipus de bloqueig REAL reproduït:** **AUTH-token absent/expirat → `401`** (cos `"Credencials d'autenticació no disponibles"` o `"token_not_valid"`), a les dues capes. **NO és PERMÍS** (no n'hi ha de custom) **ni CSRF** (inabastable en flux JWT).
4. **Origen:** **NO és la poda.** `8048e77` només va jubilar dos endpoints morts amb 0 consumidors; el gating de `cribratge` és idèntic i intacte, i a més la poda ni està desplegada (gunicorn ranci). **El cas és FORA de l'àmbit de la poda.**
5. **Fix mínim recomanat (NO implementat):**
   - **Causa més probable del que l'usuari percep com a "bloqueig":** el `access_token` de `localStorage` ha caducat. Com que [ImportWizard.jsx](frontend/src/components/ImportWizard/ImportWizard.jsx) usa `fetch` pelat sense l'interceptor 401→logout de [client.js](frontend/src/api/client.js), no renova ni redirigeix: **re-loguejar-se** (token JWT fresc) hauria de desbloquejar. Millora de codi opcional: encaminar aquesta pujada per l'axios `client` perquè hereti el maneig de 401.
   - **Higiene operativa (no és la causa):** **reiniciar gunicorn de staging** perquè carregui el codi post-poda del disc.
6. **Punt obert / honestedat:** en mode read-only sense credencials no he pogut encunyar un JWT vàlid per provar el camí "token bo → 403". Tanmateix, **és lògicament tancat:** amb `IsAuthenticated` i un usuari autenticat, DRF no pot retornar `403` en aquesta view (no hi ha permís que falli ni CSRF abastable). **Si l'usuari veu literalment `403` amb un token vàlid i fresc, NO l'origina aquest endpoint** → caldria capturar el cos exacte de la resposta del Network tab del navegador i mirar una capa d'infra/WAF; però amb l'evidència actual, el camí real és `401`, no `403`.

**Atur aquí (Patró A).**
