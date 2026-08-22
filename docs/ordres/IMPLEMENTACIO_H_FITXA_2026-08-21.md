# H · TAULA DE MESURES DE TALLA BASE A LA FITXA TÈCNICA

> **21/08/2026 · ✅ TRAM TANCAT · 3 commits a `dev`, CAP PUSH.**
> Substrat: `DIAGNOSI_BUGS_PROD_837_2026-08-21.md` §H · `DIAGNOSI_PRE_SPRINTS_STAGING_2026-08-21.md` §3.
> QA real sobre staging (models 1383 i 1379) amb captures a `ops/qa/captures/h_taula_base/`.

---

## 0 · EL RESULTAT EN UNA LÍNIA

La fitxa tècnica torna a poder documentar **la base del model** —o, quan n'hi ha, la de l'últim
fit vàlid— i ara ho fa **per prenda**, que és exactament el que la versió retirada no feia i el
motiu pel qual es va retirar. Font única: `base-measurements/`. **Cap endpoint nou, cap serializer
nou, cap segona veritat.**

---

## 1 · 🚨 DUES CORRECCIONS AL SUBSTRAT — la font JA HO SERVIA TOT

L'ordre autoritzava ampliar el serializer «si la tolerància no és a la resposta de
`base-measurements/`». **La condició és FALSA i no s'ha hagut de tocar cap serializer.**

| Què deia el substrat | Què diu el CODI | Àncora |
|---|---|---|
| «`base-measurements/` no serveix `garment`» (§H.4) | **el serveix**, des de SET-2/F1 | `pom/wizard_views.py:674` |
| «no exposa tolerància; `tol_minus`/`tol_plus` no són a `fields`» (§3.2) | **els exposa, i JA RESOLTS** per `_tol_vigent` (mesura → catàleg → 0.6) | `pom/wizard_views.py:697-698` |

La segona és la interessant, perquè el RE-ANCORATGE ja havia caçat la primera i va caure a la
mateixa trampa un pis més avall: va mirar **`BaseMeasurementSerializer`**
(`models_app/serializers.py:432`), que és el ViewSet del router —**un altre endpoint**— i que a
més diu els camps `tolerancia_minus`/`tolerancia_plus`. El que el front crida és la vista de
funció de `urls.py:123`, i allà la tolerància hi és amb un altre nom i amb la cascada ja feta.

**LLEI CONFIRMADA (una altra vegada): una acta al codi diu què era veritat el dia que es va
escriure.** Els dos errors surten del mateix comentari datat, que trenta línies per sota del
lloc on la vista serveix `'garment': bm.garment` encara deia *«per això no hi ha cap clau
`garment`»*. D'aquell paràgraf en va sortir la recomanació de fer beure la taula d'un altre
endpoint. **Els dos comentaris —el del backend i el seu bessó a `TechSheetEditor.jsx`— queden
corregits en aquest tram**, amb la lliçó escrita al costat, en lloc de deixar-hi una acta falsa.

---

## 2 · EL QUE S'HA CONSTRUÏT

| Peça | Fitxer:línia | Què és |
|---|---|---|
| Constructor de files | `frontend/src/utils/taulesQ8.js:258` · `filesBase` | emet `garment` per fila (com `filesGrading`) → `grupsDelFull` la sap repartir |
| Cel·la de tolerància | `TechSheetEditor.jsx:5316` · `cellaTol` | `± n` si és simètrica, `+p / −m` si no; buida si no n'hi ha |
| Constructor de taula | `TechSheetEditor.jsx:5353` · `insertTaulaBase` | un objecte per peça, sense cap `fetch` nou |
| Despatx | `TechSheetEditor.jsx:5743` | branca `q8_base` |
| Catàleg del panell | `TechSheetEditor.jsx:6023` | entrada **PRIMERA** del grup, porta `baseMeasuresOk` |
| Payload | `pom/wizard_views.py:707` | `updated_at` additiu (0 queries de més) |
| i18n | `q8_taula_base` · `q8_col_tol` × 3 idiomes | |

**Reutilitzat tal qual, sense tocar-ho:** `grupsQ8` · `nomesLaPeca` · `ampladaPomQ8` ·
`inserirGrupPaginat` · `tEn` · `dataDoc` · `capaQ8` · `cellaPom` · `xifra` · `baseMeasuresOk` ·
`nomenclaturaDePom` · `nomsDePom` · el **renderitzador sencer**.

### Les columnes

`Layer · POM · ‹nomenclatura› · Base · Tol ±`

- **Base** porta l'etiqueta REAL de la talla al capçal (`S`, no la paraula «Base») i la **franja
  grisa** (`base: true`, `TBL.BASE_BG`), la mateixa marca que el builder ja pinta a l'escalat.
- **La nomenclatura va SENSE títol**, com a la versió retirada: *el que hi ha sota és com el
  client anomena la mesura, i etiquetar-ho «Nomenclatura» era posar nom a una columna que
  s'explica sola* (Agus, 31/07). 🚩 **És l'única lectura interpretativa del brief** (`[nom]`):
  si Agus vol capçalera, és **una línia** a `:5372`.
- Capçaleres **sempre en anglès** (`tEn`), fila de títol amb **data + nom de taula**, sòl 8pt,
  salt de pàgina amb capçalera repetida i **sense fila tallada**. Partició per talles **no hi
  entra**: cinc columnes fixes que no creixen amb el run.

### La data de cada taula

**L'escriptura més recent del SEU grup**, no una data de document. És el que la llei del domini
declara vigent, i es veu al 1379: la mare data del **17/08** i la peça 02 del **16/08**, perquè
són dues escriptures diferents. Sense `updated_at`, la fila de títol hauria anat muda.

---

## 3 · 🚨 EL FORAT QUE NOMÉS VA CANTAR MESURANT: `nom_client`

`filesBase` va néixer copiant les claus de noms de `filesGrading`. **Amb això la columna POM
sortia BUIDA per a un model sencer** —les 21 files del banc 1383—, i el `build` era verd.

Un POM **tenant-only** (sense `pom_global`) no té ni `nom_en` ni `nom_ca`: el catàleg d'un client
importat el bateja **NOMÉS a `POMMaster.nom_client`**, que és l'últim graó de la cadena de
`nomsDePom`. `filesGrading` no l'arrossega perquè **beu de `taula-mesures`**, que resol els noms
per una altra banda; copiar-ne les claus va copiar-ne també un supòsit que aquí no val.

**Llei: dos constructors germans que beuen de FONTS diferents no poden compartir la llista de
camps per analogia.** El defecte no és detectable per `build`, ni per `eslint`, ni pel banc de
payloads: només mirant una cel·la.

---

## 4 · QA — 4 casos reals sobre staging, per HTTP i UI

Script: `ops/qa/qa_h_taula_base.py` (patró de `qa_s45_captures.py`: bundle des de
`frontend/dist` al disc, `/api/` proxyat a `127.0.0.1:8001` amb el Host del tenant, o
l'`auth_basic` d'nginx torna un 401 i la captura surt en blanc).

| # | Cas | Resultat | Captura |
|---|---|---|---|
| 1 | **1383 · peça única** (21 mesures, totes amb xifra) | ✅ una taula, 21 files, capçal `S` gris, `± 0.6`, data 20/08 | `1383_una_peca_2_inserida.png` |
| 2 | **1379 · MULTIPEÇA** (mare 11 + peça 02 amb 7) | ✅ **dues** taules, títols `RUFFLES` i `Short`, dates 17/08 i 16/08 | `1379_multipeca_2_inserida.png` |
| 3 | **Ordre al panell** | ✅ `Mesures talla base · Fitting · Escalat · Size set · Notes` a **cada** grup de peça | `*_1_panell.png` |
| 4 | **Export PDF == live** | ✅ idèntic, i **per construcció**: l'export embeda el PNG de `renderPageToDataURL`, el mateix que pinta el llenç | `pdf_1383-1.png` · `pdf_1379-1.png` |
| 5 | **REGRESSIÓ · fitxa vella amb els `kind` RETIRATS** | ✅ `.ftt` 771 (model 1320) porta `pom_fitting`, `base_measures`, `pom_grading` i `fitting_history` i **pinta idèntica**, 3 pàgines, **cap error de pàgina** | `legacy_771_kinds_retirats.png` |

**Round-trip verificat a la BD, no només a la pantalla.** El `.ftt` desat (876, model 1379) porta
els dos objectes amb `garmentId` `''`/`'02'`, `titol` `RUFFLES`/`Short`, les cinc columnes amb
`base: true` a la de la talla, i les files amb `{'centrat': True, 'text': '± 0.6'}`.

**`errors de pàgina: cap`** a les dues corregudes.

---

## 5 · CENS — vist i NO tocat

- 🚩 **El banc de payloads no s'ha pogut córrer.** `fitting/test_q8_banc_taules_fitxa.py` demana
  la BD de test i **hi havia una suite completa d'una altra sessió corrent-hi**
  (`fhort.pom fhort.fitting fhort.tasks fhort.models_app`, PID 3462871). Llei de la casa: mai
  dues corregudes alhora. **Queda pendent afegir-hi la taula nova i córrer-lo.**
- 🚩 **Dues insercions cauen l'una damunt de l'altra.** `inserirGrupPaginat` col·loca sempre a
  `Y_INICI = 14`, o sigui que inserir la taula de la mare i després la de la 02 les apila al
  mateix punt (es veu al PDF del 1379: la `Short` tapa la `RUFFLES`). **No és d'aquest tram: és
  de tota la família Q8** —passa igual amb fitting, escalat i size set— i és per disseny que
  cada clic sigui un objecte arrossegable. Si molesta, és una decisió d'Agus sobre l'offset.
- 🚩 **`ModelFitxer` 873 (model 1383) apunta a un fitxer que NO és al disc**
  (`media/fhort/model_fitxers/2026/08/TRV-SS27-0001_fitxa_CGuFcJV.ftt`). L'editor l'obre igual i
  hi treballa, però l'autosave no hi persisteix. Dany viu, aliè a aquest tram.
- 🚩 **Churn de versions.** Obrir + inserir + exportar va crear `ModelFitxer` 874-877. Ja censat
  a `ftt-ftt-version-churn`; aquesta QA l'engreixa.
- ℹ️ **La QA escriu.** Obrir l'editor pren el lock i inserir dispara l'autosave (debounce 2 s):
  els `.ftt` dels dos models de banc porten ara les taules inserides. Era inevitable per fer la
  QA que l'ordre demanava per UI real; s'ha fet sobre `.ftt` **existents**, mai per
  `/models/:id/fitxa` (que resol-o-CREA i materialitza tasca).

---

## 6 · COMMITS (cap push)

| Commit | Què |
|---|---|
| `2bd95354` | **H/1** · `updated_at` additiu a `base-measurements/` + correcció del comentari que mentia |
| `f8fde9c4` | **H/2** · `filesBase`, `insertTaulaBase`, despatx, panell, i18n × 3, fix `nom_client` |
| *(següent)* | **H/3** · l'script de QA |

**Porta verda:** `manage.py check` net · `npm run build` ✓ · `npx eslint` **0 errors** (64
warnings, totes preexistents) · `systemctl restart ftt-staging` fet (el payload el demanava).
