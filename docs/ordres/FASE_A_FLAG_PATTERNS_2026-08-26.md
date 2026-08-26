# FASE A — `FTT_PATTERNS_ENABLED`: un interruptor, dos panys

**Data:** 26/08/2026 · **Branca:** `fase-a-flag-patterns` (worktree `/var/www/ftt-flagpat`, des de `dev` 3b862810)
**Push:** CAP. El farà l'Agus, probablement amb el veredicte P1 del motor.

---

## PAS −1 · l'entorn

| | |
|---|---|
| hostname | `fhort-assessment` ✅ |
| `WorkingDirectory` d'`ftt-staging.service` | `/var/www/ftt-staging/backend` ✅ |
| gunicorn compartit | `127.0.0.1:8001`, `--workers 2` — **no tocat en cap moment** |

**Coordinació amb la sessió del motor.** `git status --porcelain` a l'arbre principal abans de
començar: quatre fitxers tracked bruts —`DECISIONS.md`, `docs/ordres/IMPLEMENTACIO_SOBIRANIA_POM_2026-08-22.md`,
`ops/maquetes/REPORT_CODA_BLOC_B.md`, `ops/qa/qa_f22_vocabulari_captures.py`— i **cap** interseca
amb el que aquesta fase toca. Tampoc no hi ha res brut dins de `backend/fhort/patterns/`.

Això va decidir, més que el permís de continuar, **on va el pany**: cap dels sis fitxers d'aquesta
fase és de l'app `patterns`. La sessió del motor hi pot treballar sense creuar-se amb res d'aquí.

---

## A1 · el mecanisme REAL de visibilitat del menú de model

### Com es decideix avui

**No es decideix: està escrit.** La llista és una constant estàtica.

| | |
|---|---|
| llista canònica | `frontend/src/utils/modelSeccions.js:16-19` — `SECCIONS_MODEL`, 9 cadenes literals |
| qui la pinta | `frontend/src/pages/ModelSheet.jsx:54` → `PageMenu` (`ModelSheet.jsx:1173`) |
| ruta a pantalla completa | `frontend/src/App.jsx:433` — `/models/:id/patro/taller`, FORA del Shell |
| segon consumidor | cap avui: `TechSheetEditor.jsx` ja no crida `pindolesDeModel` (`items={[]}`, línia 7477) |

No hi ha capability, ni config de servidor, ni cap condicional. El tab «Patró» hi és sempre.

### Les vies servidor→front que SÍ existeixen, i per què cap serveix

Es van censar les tres abans d'escriure res.

**1. `user.capabilities`** — `store/auth.js:86` (`fetchMe`) ← `MeSerializer.get_capabilities`
(`accounts/serializers.py:67`) ← `get_capabilities()` (`accounts/capabilities.py:47`). La consumeix
`RutaAmbCapacitat` (`App.jsx:143`), que és el patró que gateja tot el mòdul comercial.

És un canal real i viu, i **no és aquest**. Una capability és per PERSONA: surt del rol
(`ROLE_CAPABILITIES`), s'atorga i es revoca individualment per `permisos.grant`/`revoke`, i la
tupla `CAPABILITIES` és, literalment, **l'ordre de les columnes** de la matriu de
`/configuracio/usuaris` (el comentari de `capabilities.py:15-19` ho declara: «l'ordre és dada»).
Un interruptor de desplegament no és res d'això. Posar-l'hi obriria una columna falsa a la matriu
que un admin podria commutar per error, i a PROD el motor s'ha d'apagar per a tothom alhora, no
usuari per usuari.

**2. `tenant-config`** (`api/endpoints.js:18`, `TenantConfig`) — és per TENANT i viu a la BD. El
que s'apaga a PROD s'apaga per a tot PROD, i posar-ho aquí voldria una migració i una fila per
tenant que algú hauria de mantenir en sincronia.

**3. `import.meta.env` (build-time)** — la casa ja el fa servir **per a exactament aquesta classe
de dada**: `VITE_STAGING` (`layout/Sidebar.jsx:263,268`) distingeix staging de producció i
`VITE_API_URL` (`api/base.js:21`) diu on és l'API.

### Veredicte d'A1 — i la declaració que el brief demana

> **L'única via que existeix per a una dada de DESPLEGAMENT és la de build. La variable del front
> ha d'anar a l'`.env` de PROD ABANS del `npm run build`.**

No se n'ha inventat cap: s'ha fet servir la que la casa ja té per a `VITE_STAGING`.

### 🔑 El fet que va decidir el default (i que ja era veritat abans d'aquesta fase)

`npm run build` és `vite build` a seques (`package.json`), o sigui **mode `production`**, que
carrega `.env` i `.env.production`. **Cap dels dos existeix al repo.** `.env.staging` (`VITE_STAGING=true`)
existeix però `vite build` **no el llegeix mai** — voldria `--mode staging`.

I es pot mesurar al producte servit: al `dist` viu d'staging, la línia de `Sidebar.jsx:263` va
quedar compilada com `height:` `` `100vh` `` — el ternari plegat pel costat fals. **`VITE_STAGING`
no estava definida quan es va construir el bundle que hi ha ara mateix a producció d'staging.**

Conseqüència directa per a A3-bis: «flag absent» no és un cas de laboratori, **és l'estat normal
d'un build d'aquesta casa**. Per això el default ENCÈS no és una comoditat sinó la condició per
no perdre el motor per descuit.

---

## A2 · implementació

### Cens exacte de les rutes de patterns

Tota l'API del motor penja d'**UN sol `include`**. Es va verificar que cap altre `urls.py` importa
l'app: l'únic `grep` que hi torna són els `urlpatterns` d'altres mòduls (fals positiu de la
paraula) i, dins de la pròpia app, tests, migracions i un management command.

| # | ruta | file:line |
|---|---|---|
| — | **el punt d'entrada únic** | `backend/fhort/urls.py:53` (abans del canvi) |
| 1 | `api/v1/patterns/pattern-files/` | `backend/fhort/patterns/urls.py:15` |
| 2 | `api/v1/patterns/piece-roles/` | `backend/fhort/patterns/urls.py:17` |
| 3 | `api/v1/patterns/pattern-poms/` | `backend/fhort/patterns/urls.py:19` |
| 4 | `api/v1/patterns/pattern-segments/` | `backend/fhort/patterns/urls.py:20` |
| 5 | `api/v1/patterns/sew-relations/` | `backend/fhort/patterns/urls.py:22` |
| 6 | `api/v1/patterns/sew-proposal-rejections/` | `backend/fhort/patterns/urls.py:25` |
| 7 | `api/v1/patterns/sew-tolerance-acceptances/` | `backend/fhort/patterns/urls.py:29` |

Les set són `DefaultRouter.register`, i totes les `@action` hi pengen a sota (`render.svg`,
`geometry`, `download-links`, `identificar`, `identitat`, `model-poms`, `export`, `export-rul`,
`export-preview`, `grading-versions`, `metodes`, `propostes`, `pinces-proposades`, `bulk-delete`…).
**Comptades pel resolutor de Django: 74 rutes**, més les 2 de l'`api-root` del router del mòdul.

El **taller i el visor no són rutes de backend**: el taller és la ruta de front `App.jsx:433` i el
visor és un component dins del tab. **Els imports tampoc**: la pujada d'un `.ftt`/DXF és
`POST /api/v1/patterns/pattern-files/` (`api/endpoints.js:985`), o sigui la ruta 1 — no n'hi ha cap
de separada.

### El pany del backend

`backend/fhort/settings.py` — el flag, al costat de l'altre flag d'entorn de la casa:

```python
FTT_PATTERNS_ENABLED = os.environ.get('FTT_PATTERNS_ENABLED', 'true').lower() not in ('0', 'false', 'no')
```

Va **al revés** que `IMPORT_REVISIO_SONNET` (línia 138), i és deliberat: aquell apaga per omissió
perquè encendre'l costa diners; aquest encén per omissió perquè apagar-lo fa desaparèixer pantalles
que avui existeixen. Es nega la llista de FALSOS en lloc d'afirmar la de certs.

`backend/fhort/urls.py` — el pany, **entre `commerce` i `tenants`, a la posició exacta d'abans**:

```python
*([path('api/v1/', include('fhort.patterns.urls'))] if settings.FTT_PATTERNS_ENABLED else []),
```

Tres raons perquè visqui aquí i no dins de l'app:

1. **És UN sol punt** — les 76 rutes hi pengen.
2. **Dona un 404 DE VERITAT.** Un permís de DRF donaria 403, que és una altra frase: diria «això
   existeix i no hi pots entrar» quan el que volem dir és «això aquí no hi és».
3. **No toca cap vista del motor** — que és, a més, on hi ha una altra mà treballant.

S'escriu desplegant una llista i no amb un `if` que faci `append` al final del fitxer perquè la
**posició** s'ha de conservar (v. la prova de l'A3).

### El pany del frontend

| fitxer | què |
|---|---|
| `frontend/src/utils/flags.js` **(nou)** | `PATTERNS_ENABLED` — l'únic lector d'`import.meta.env` |
| `frontend/src/utils/modelSeccions.js` | `seccionsVisibles(patternsEnabled)`, **pura**; `pindolesDeModel` accepta `seccions` |
| `frontend/src/pages/ModelSheet.jsx:57` | `const TABS = seccionsVisibles(PATTERNS_ENABLED)` |
| `frontend/src/App.jsx:442` | el taller rebota a l'arrel amb el flag apagat |

`SECCIONS_MODEL` **no es toca**: segueix sent la llei sobre quines seccions té un model i en quin
ordre. `seccionsVisibles` diu una altra cosa —què es pinta AQUÍ—, i la diferència entre les dues és
exactament el que l'interruptor decideix. És pura i rep el booleà en lloc de llegir-lo, perquè
`node --test` no sap què és `import.meta.env`.

**Filtrar la llista tanca també el deep-link `?tab=Patró`**, i no per casualitat: `ModelSheet` només
accepta el paràmetre si la secció hi és (`TABS.includes(tabParam)`, línies 213 i 223), de manera que
un enllaç antic cau al tab per defecte en lloc d'obrir una pantalla que aquí no existeix.

El rebot del taller és a l'arrel i no a `/login` pel mateix motiu que `RutaAmbCapacitat` documenta:
qui hi arriba TÉ sessió. La diferència amb aquell guard és que allà el tall de veritat és un 403 i
aquí és un 404 — sense aquesta línia la pantalla es muntaria per omplir-se d'errors.

### i18n

**Cap clau nova**, com el brief esperava. L'etiqueta ja existia (`model_sheet.tab_pattern`,
`modelSeccions.js:28`) i el que es fa és no pintar-la. Paritat ca/en/es intacta.

---

## A3 · verificació proporcional (cap suite)

### El que s'ha mesurat

| control | resultat |
|---|---|
| `manage.py check` · flag ABSENT | `System check identified no issues (0 silenced)` |
| `manage.py check` · `=true` | `no issues` |
| `manage.py check` · `=false` | `no issues` |
| `npm run build` × 3 (absent · true · false) | `✓ built in 1.2–1.7s`, exit 0 |
| `npx eslint` dels 5 fitxers tocats | **0 errors**, 15 warnings |
| `npx eslint` dels mateixos a `dev` HEAD | **0 errors, 15 warnings** — idèntic: no n'he afegit cap |
| `node --test src/utils/modelSeccions.test.js` | **5/5** |

Build i lint s'han corregut en **còpia aïllada** (el worktree), mai in situ: a staging es
serveix `frontend/dist`, o sigui que construir-hi **és desplegar**. `node_modules` s'hi ha **copiat**
(`cp -a`), mai enllaçat — un symlink amb `npm ci` ja va destruir cinc worktrees el 25/08.

### El banc nou, vist VERMELL

`frontend/src/utils/modelSeccions.test.js` (5 casos). Un test de regressió només val si l'has vist
caure: amb el filtre substituït per un `return SECCIONS_MODEL` inert, **3 dels 5 cauen**; restaurat,
5/5. La prova es va fer sobre una còpia i es va revertir.

### Prova que amb TRUE no canvia RES (backend)

Es va bolcar el mapa d'URLs sencer i comparar contra el fitxer original de `dev` HEAD:

| | rutes |
|---|---|
| `dev` HEAD (sense flag) | **645** |
| amb el flag `=true` | **645** — `diff` buit, **idèntics** |
| amb el flag `=false` | **569** (−76) |

Les 76 que cauen són les 74 del motor **més les 2 de l'`api-root` del seu propi `DefaultRouter`**.
Es va comprovar expressament que això no s'endugués `/api/v1/`: hi ha 18 entrades `api-root` (dues
per cada un dels 9 routers) i amb el flag apagat en queden 16 — `/api/v1/` **segueix resolent**.

### Prova que amb TRUE no canvia RES (frontend)

`diff -r` dels `dist/` complets: **build ABSENT vs build TRUE → idèntics byte a byte.**

Es va verificar al bundle que Vite substitueix de debò a través de l'`?.` (no es va donar per fet):
la lectura queda plegada a una constant literal.

| build | com queda al bundle | → |
|---|---|---|
| ABSENT | `` [`0`,`false`,`no`].includes(`true`) `` | encès |
| `=true` | `` [`0`,`false`,`no`].includes(`true`) `` | encès |
| `=false` | `` [`0`,`false`,`no`].includes(`false`) `` | apagat |

### Smoke HTTP — gunicorn PROPI, mai el compartit

Tres gunicorns d'un worker als ports **8711 / 8712 / 8713**, un per estat, aturats en acabar.
(El 8099 estava ocupat per un `runserver` del 04/08 d'una altra mà: el meu procés **va refusar
arrencar sol** sense tocar-lo, i es va canviar de port.)

Autenticat amb un JWT del tenant `fhort`:

| ruta | absent | `=true` | `=false` |
|---|---|---|---|
| `/api/v1/patterns/pattern-files/` | **200** | **200** | **404** |
| `/api/v1/patterns/piece-roles/` | 200 | 200 | 404 |
| `/api/v1/patterns/pattern-poms/` | 200 | 200 | 404 |
| `/api/v1/patterns/pattern-segments/` | 200 | 200 | 404 |
| `/api/v1/patterns/sew-relations/` | 200 | 200 | 404 |
| `/api/v1/patterns/sew-proposal-rejections/` | 200 | 200 | 404 |
| `/api/v1/patterns/sew-tolerance-acceptances/` | 200 | 200 | 404 |
| `/api/v1/models/` (control) | **200** | **200** | **200** |
| `/api/v1/me/` (control) | 200 | 200 | 200 |

Sense token, les mateixes rutes donen **401 amb el flag encès i 404 amb l'apagat** — o sigui que el
404 és del resolutor i no del permís: la ruta no hi és, no és que no s'hi pugui entrar.

### Smoke de PANTALLA — `ops/qa/qa_fase_a_flag_patterns.py` (nou)

Patró de `qa_mount_modelsheet.py`: es serveix el bundle REAL del disc i s'stubeja `/api/` sencera
des del procés. Es corre contra els tres `dist/`.

```
· absent: 46 entrades · «Patró» = True  · /patro/taller → /models/1383/patro/taller
· true  : 46 entrades · «Patró» = True  · /patro/taller → /models/1383/patro/taller
· false : 45 entrades · «Patró» = False · /patro/taller → /

✓ true: «Patró» ÉS al menú                    ✓ true: /patro/taller s'obre
✓ ABSENT: el menú és idèntic al de true       ✓ ABSENT: /patro/taller s'obre
✓ false: «Patró» NO és al menú                ✓ false: /patro/taller rebota a l'arrel
✓ false: el flag es queda UNA entrada i és la de patrons → ['Pattern']
✓ false: no n'apareix cap de nova → []
```

**🚨 El primer intent d'aquest fum va donar vermell als tres casos alhora** —senyal que el defecte
era la sonda—: portava els noms de les seccions escrits en català i el menú es pinta en l'idioma que
el detector del navegador tria (`Summary`, `Grading`, `Pattern`). Una llista d'etiquetes escrita a mà
mesura l'idioma del headless, no el flag. L'asserció es va reescriure per **comparar builds entre
ells**, que és independent de l'idioma i és, a més, exactament la propietat que la fase promet:
entre `true` i `false` la diferència ha de ser d'UNA entrada, i entre `absent` i `true`, de CAP.

### El que això NO prova

- **No s'ha corregut cap suite** (llei del gate proporcional), i en particular **cap test de
  `patterns`, `aama_reader` ni `writer`** — la sessió del motor hi és a sobre.
- El **model 1383 no s'ha tocat**: el fum de pantalla en fa servir el número com a URL, però tota
  l'API va stubejada i el servidor viu no hi intervé.
- El smoke HTTP fa **lectures** (`GET`); no s'ha exercit cap escriptura del motor.

---

## Per a l'`.env` de PROD — les DUES variables

Són dues perquè viuen en dos processos diferents; el mateix nom no hi arriba sol.

### 1 · Backend → `/var/www/<prod>/backend/.env`

El fitxer que `settings.py:15` carrega amb `load_dotenv(BASE_DIR / '.env')`. Està gitignorat
(`.gitignore:19`): és artefacte de desplegament, no de repo.

```
FTT_PATTERNS_ENABLED=false
```

Efecte immediat: **cap**. `gunicorn` serveix el codi de quan va arrencar → **`systemctl restart`**
del servei de PROD.

### 2 · Frontend → **VITE_, i ABANS del build**

`vite build` corre en mode `production` i llegeix `.env` i `.env.production` dins de `frontend/`.
**Cap dels dos existeix avui al repo**, o sigui que a PROD **cal crear-ne un**:

```
# frontend/.env.production
VITE_FTT_PATTERNS_ENABLED=false
```

> 🚨 **És build-time.** El valor queda cuit dins del bundle: escriure la variable després del
> `npm run build` no mou el `dist` ja construït. L'ordre és **posar la variable → `npm run build`**.
> El prefix `VITE_` és obligatori (`envPrefix` per defecte); sense ell Vite no l'exposa i el front
> es queda amb el default ENCÈS sense dir res.

### Ordre de desplegament a PROD

1. `frontend/.env.production` amb `VITE_FTT_PATTERNS_ENABLED=false`
2. `npm run build`
3. `backend/.env` amb `FTT_PATTERNS_ENABLED=false`
4. `systemctl restart <servei>`

Fer només el 3+4 deixa el menú visible damunt d'una API que ja dona 404 — el pitjor dels dos mons.
Fer només l'1+2 amaga la porta però deixa l'API oberta.

### Staging

**No es toca res.** Cap de les dues variables s'hi declara i el motor queda ENCÈS pel default.

---

## Commits (branca `fase-a-flag-patterns`, CAP push)

| sha | què |
|---|---|
| `ec010835` | `feat(fase-a)`: el flag i el pany del backend |
| `162421a0` | `feat(fase-a)`: el pany del front + el banc pur |
| `abf481f8` | `test(fase-a)`: el fum de pantalla dels tres builds |
| *(aquest commit)* | `docs(fase-a)`: aquesta acta — la sha no s'hi pot escriure a si mateixa |

## Fitxers

**Modificats (5)** · `backend/fhort/settings.py` · `backend/fhort/urls.py` ·
`frontend/src/App.jsx` · `frontend/src/pages/ModelSheet.jsx` · `frontend/src/utils/modelSeccions.js`

**Nous (3)** · `frontend/src/utils/flags.js` · `frontend/src/utils/modelSeccions.test.js` ·
`ops/qa/qa_fase_a_flag_patterns.py`

Cap és de l'app `patterns`. Cap toca el motor.
