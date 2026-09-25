# DIAGNOSI — Nomenclatura d'instància/capa, corpus de cotes i fitxa (croquis/veredicte/taules)

**Data:** 2026-09-24 · **Patró A (READ-ONLY)** · Staging `/var/www/ftt-staging`, branca `dev` @ `4e7c5a14` (host `fhort-assessment`).
**Abast:** verificar a staging els fets de la diagnosi PROD del 24/09 (main `6af581cd`) sobre: (1) divergència dev/main, (2) vocabulari de sufixos d'instància i de capa i les seves col·lisions, (3) l'estat real del corpus de cotes LOSAN a `/root/sembra_ai/`, (4) el substrat de fitxa (croquis, veredicte, inserció de taules, nomenclatura, precedents A2) com a base del Patró B.
**Convenció:** `fitxer:línia` per a tota afirmació de codi. `"NO EXISTEIX"` = confirmat absent al codi (no especulat). `💡 PROPOSTA (a validar)` marca qualsevol suggeriment; la resta és fet verificat.

---

## Resum executiu (director)

1. **Els 17 commits `dev`→`main` (23/09, consentiment de germanes + `ModelInstanceOffset` + etiqueta de veredicte) ja són a PROD** (confirmat per l'Agus: PROD main = `6af581cd` = merge de `dev@4e7c5a14`). El que SÍ és un fet nou i verificat: **`origin/main` a GitHub no els conté** — `6af581cd` no és cap objecte conegut al repo local i `origin/main@91933221` no té `4e7c5a14` com a ancestre. És deute d'higiene de refs (PROD es va desplegar des d'un merge que mai es va empènyer a `origin/main`), no un risc de contingut.
2. **El vocabulari de sufixos d'instància EXISTEIX i és una llei deliberada, no un forat**: `MeasurementInstance` (10 POSICIONS amb sufix + 2 ESTATS sense sufix) és idèntic a `public`/`fhort`/`los`, sembrat des de `seed_measurement_instances.py` amb la llei explícita "els ESTATS no componen sufix" i "`waistband_seam` es diu a la descripció, no al codi". **Les tres propostes de sufix d'estat del brief (estat A, estat B) contradiuen aquesta llei ja escrita**, no l'omplen.
3. **Col·lisió real confirmada**: el codi `BW` ja existeix a `fhort` com a POM actiu ("Fold width", `pom_pommaster` id 912) i com a àlies de client (id 860). Qualsevol esquema de sufix que componés `waistband_seam→W` sobre una base `B` xocaria amb ell.
4. **El corpus de `/root/sembra_ai/` és només FASE 1 (informe, sense escriure res) i està desactualitzat**: `sembra_ai_report.py` calcula geometria però no la persisteix enlloc (ni fitxer ni BD); `POMPlacement` existeix a `fhort` i `los` però és **buit a les dues**. Una mostra de 17 codis de l'informe (26/07) mostra que **el 47% ja no resol** contra el catàleg viu d'avui (24/09) — el catàleg ha canviat substancialment pel mig (sembra v4/v5).
5. **A la fitxa, el substrat del Patró B ja hi és majoritàriament**: `useEtiquetaVeredicte` i la columna VERDICT existeixen i tenen un patró de cel·la multilínia ja provat (NAME, `wrap:true`) que el veredicte encara no fa servir; la inserció de taules és consistent (`inserirGrupPaginat` + `Y_INICI`); l'A2 (`capa='exterior', instancia=''` fix) és deute reconegut explícitament al propi codi.
6. **🚨 Troballa transversal nova, no prevista al brief**: el judici d'homonímia (`germanes_homonimes`) només es crida en DUES portes de tot el backend (gènesi via `gravar_pom_view` i rebateig via `base_measurement_noms_view`). **Una germana creada des de la pantalla de PRESA (tecla L o partició d'instància) neix via `BaseMeasurementViewSet.perform_create`, un `ModelViewSet` genèric sense cap judici d'homonímia** — pot xocar de nom amb una altra fila i el sistema no ho dirà mai.

---

## BLOC 1 — DEV vs MAIN

### 1.1 Commits
`git fetch origin` fet. `origin/main` estava a `d0877bc5`→`91933221` (moviment durant la sessió). `git log --oneline origin/main..origin/dev` = `git log --oneline origin/main..dev` = **17 commits**, tots `Agusti Fhort`, tots **23/09**, cap sense pujar (`dev` = `origin/dev`).

Tots 17 són sobre **consentiment de germanes** (`FittingSisterDecision`, `fitting/migrations/0029`), **`ModelInstanceOffset`** (`models_app/migrations/0088`) i **etiqueta de veredicte OK/ADJUSTED/NO OK**. Fitxers tocats: `fitting/{models,services,services_consentiment,views}.py`, `models_app/{models,vocabulari_views}.py`, `models_app/management/commands/repara_base_des_de_fitting.py`, `frontend/src/{components/model/*,pages/TechSheetEditor.jsx,utils/etiquetaVeredicte.js,i18n/*}`.

**Confirmat per l'Agus: aquests 17 commits ja són a PROD** (main PROD = `6af581cd`, merge de `dev@4e7c5a14`, desplegat 23/09). No es tracten com a novetat d'aquesta diagnosi.

**Deute d'higiene de refs (nou, verificat):**
- `git log -1 --oneline origin/main` → `91933221 Merge remote-tracking branch 'origin/dev'`.
- `git branch -r --contains 6af581cd` → `error: malformed object name 6af581cd` — **`6af581cd` no és cap objecte conegut en aquest repo (ni al `git log --all`)**.
- `git merge-base --is-ancestor 4e7c5a14 origin/main` → **NOT ancestor**. Verificat també per contingut: `git cat-file -e origin/main:backend/fhort/fitting/services_consentiment.py` i `...frontend/src/utils/etiquetaVeredicte.js` → **cap dels dos fitxers existeix a `origin/main`**.
- **Veredicte: `origin/main` (GitHub) està per darrere del que corre a PROD.** El merge que va generar `6af581cd` es va fer/desplegar sense empènyer-se a `origin/main`; els commits posteriors a `origin/main` (`db3207cc`, `0767b99f`, `91933221`) no en deriven.

### 1.2 Migracions
Consulta SQL a `django_migrations` per schema (`public`, `fhort`, `los`), apps `models_app` i `fitting`: **les tres schemes tenen exactament el mateix conjunt aplicat** (`models_app` fins `0088_modelinstanceoffset_relacio_instancies`, `fitting` fins `0029_fittingsisterdecision_consentiment_germanes`, totes aplicades 2026-09-23). **Sense divergència entre schemes ni respecte del repo.**

`0064` aclarit: a staging i al repo, `0064 = basemeasurement_origen_copied` (aplicada 2026-07-27). **No hi ha cap taula `PlacementProposal` a staging** (ni al codi ni a la BD — `information_schema.tables` amb `table_name ilike '%placement%'` només retorna `fhort.models_app_pomplacement` i `los.models_app_pomplacement`). El "`0064` fantasma" de PROD sembla exclusiu de PROD; a staging no hi ha res a netejar en aquest punt.

### 1.3 Dades de configuració staging vs PROD
**PENDENT DE VERIFICAR** — no és accessible en read-only des d'aquesta sessió (zona PROD intocable, sense dump disponible aquí). El contingut de configuració present a staging es documenta al BLOC 2 (és el mateix a `public`/`fhort`/`los`, sembrat per `update_or_create`, `is_system=True`).

**Veredicte BLOC 1: llest.** Sense divergència de migracions ni de codi entre `dev` i el que corre a PROD; l'únic residu és higiene de `origin/main` (no bloqueja res d'aquesta diagnosi).

---

## BLOC 2 — Vocabulari d'instància i capa

### 2.1 `MeasurementInstance` / `MeasurementLayer` a staging
`pom_measurementinstance`, idèntic a `public`/`fhort`/`los` (12 files, `is_system=t`, `origen=SEED`):

| slug | sufix | eix | ordre |
|---|---|---|---|
| relaxed | *(buit)* | ESTAT | 1 |
| extended | *(buit)* | ESTAT | 2 |
| left | L | POSICIO | 1 |
| right | R | POSICIO | 2 |
| top | T | POSICIO | 3 |
| bottom | BM | POSICIO | 4 |
| cf | CF | POSICIO | 5 |
| cb | CB | POSICIO | 6 |
| side | S | POSICIO | 7 |
| waistband_seam | *(buit)* | POSICIO | 8 |
| front | F | POSICIO | 9 |
| back | B | POSICIO | 10 |

`pom_measurementlayer` (schema `public`, 6 files, idem `is_system`/`SEED`): `exterior, folre, entretela, farciment, reforc, fornitura` — **el model NO té cap camp `sufix`** (`backend/fhort/pom/models.py:265-274`: només `slug, nom_en, nom_ca, nom_es, is_system, pendent_revisio, origen, display_order`). No hi ha "sufix de relaxed/extended/waistband_seam" enlloc del repo ni en cap commit de `dev` no fusionat (els 17 commits no toquen `pom/models.py` ni els fitxers de sembra).

### 2.2 Vocabulari ja fixat — rastres trobats
- `backend/fhort/pom/management/commands/seed_measurement_instances.py:30-37`: **"El sufix... va buit allà on el full diu que no en porta: waistband_seam és un DATUM... i es diu a la descripció, no al codi; cap ESTAT no en porta: fan servir el codi oficial del client si en té... o la descripció."** És llei explícita i deliberada, no un oblit.
- `backend/fhort/pom/models.py:305-310` (docstring `MeasurementInstance`): **"EL SUFIX ÉS DE LA POSICIÓ, MAI DE L'ESTAT... Per això `sufix` és buit als dos estats i no és un oblit."**
- `docs/ordres/INSTANCIES_POSICIO_V2_2026-08-23.md:46-48`: acta que fixa els 10 slugs de POSICIÓ i confirma `sufixos únics: True` a `public`/`fhort`/`los` — **només cobreix l'eix POSICIÓ, mai ESTAT ni CAPA**.
- `DECISIONS.md`: **NO EXISTEIX cap menció** a sufix d'estat, sufix de capa, `waistband_seam`, `relaxed` ni `extended` (grep sense coincidències).
- `docs/diagnosis/DOSSIER_INSTANCIA_POM.md`: secció "Fase C — collita del diccionari" existeix (índex, línia 39) però les úniques mencions de "sufix" (línies 1138, 3879) són sobre "sufix de secció al codi" (0 casos trobats), no sobre el vocabulari d'instància/capa.
- `frontend/src/utils/capaInstancia.js:99-129`: **`etiquetaCapa`/`etiquetaInstancia` SÍ consulten el diccionari de BD** (`dicc.capes`/`dicc.instancies`) i tenen fallback local (`NOM_INSTANCIA`, línia 63) — és el humanitzador real i ja construït, DIFERENT del de `services_consentiment.py` (v. aclariment).

**Aclariment del punt 2 (services_consentiment.py:28-31):** el comentari **"NO EXISTEIX vocabulari d'instància avui (DIAGNOSI BLOC Q2)"** cita `docs/diagnosis/DIAGNOSI_CONSENTIMENT_GERMANES.md:103-126` (secció "BLOC Q2 — Les germanes"), que diagnostica un problema DIFERENT i local: **no hi ha cap generador de la FRASE HUMANA del modal de consentiment** ("extended = relaxed + 18"); el més a prop és el `motiu` de `MeasurementChangeLog` (`services_derivacio.py:196-199`), que parla en termes de capa/instància d'origen, no de la germana resultant. Per això `etiqueta_instancia()` (`services_consentiment.py:28-33`) fa una neteja de slug ingènua en lloc de consultar `MeasurementInstance.nom_ca/en/es` — **és un forat local d'aquest punt de crida concret, no una afirmació que el vocabulari de sufixos no existeixi** (aquest SÍ existeix i està ple, v. 2.1). El frontend ja té l'equivalent correcte fet (`capaInstancia.js:115-120`), que el backend d'aquest modal no reutilitza.

### 2.3 Col·lisions de les propostes

| Proposta | fhort | los |
|---|---|---|
| estat A: `waistband_seam→W` (p.ex. `B`+`W`=`BW`) | **🚨 COL·LISIÓ**: `BW` ja existeix com a `pom_pommaster.codi_client` (id 912, POM global `B8` "Fold width") i com a `pom_customerpomalias.client_code` (id 860, pom 1002, customer 7) | sense coincidència |
| estat A: `extended→E` (p.ex. `B`+`E`=`BE`, `Y`+`E`=`YE`) | sense coincidència exacta de `BE`/`YE` | sense coincidència |
| estat B: `RX`/`EX`/`WS` (`BRX`, `BEX`, `BWS`) | sense coincidència exacta | sense coincidència |
| capa: `·LN` (`FSCF·LN`) | sense coincidència exacta; **però** `MeasurementLayer` no té camp `sufix` (2.1) — un sufix de capa exigiria migració d'esquema, no és només una qüestió de col·lisió de dades | — |

Consulta ampliada (regex `(E|W|RX|EX|WS)$` sobre tots els `codi_client`/`client_code` de `fhort`): 13 coincidències parcials (`BW, E, FE, HW, QW, RW, W`×2 cadascun aprox.) que caldria repassar cas a cas si es tria un sufix curt d'una lletra — el risc de col·lisió és més ampli que els 6 candidats exactes provats. **`los` no té cap coincidència ni parcial ni exacta** amb cap dels candidats.

**💡 PROPOSTA (a validar):** cap de les tres propostes (estat A, estat B, capa `·LN`) és compatible tal qual amb la llei ja escrita a `seed_measurement_instances.py:32-37` ("ESTAT mai compon sufix"); adoptar-ne una implicaria canviar aquesta llei explícitament, no només afegir dades.

Sobre l'àlies BRW del POM B i la interacció alias↔`nom_fitxa`: **no s'ha pogut verificar en aquest bloc** (fora de l'abast de temps assignat; els 6 models BRW de PROD no existeixen a staging, v. 2.4, així que no hi ha fila concreta a inspeccionar).

### 2.4 Els 6 models de PROD a staging
`SELECT count(*) FROM {fhort,los}.models_app_model` = **43 (fhort) + 51 (los)**. Cerca per `codi_intern ~ '(208|1179|197|1185|1186|1210)'` i per `codi_intern ilike '%canet%'` a les dues schemes: **0 resultats a totes dues.** **NO EXISTEIX cap dels 6 models BRW (208 CANET, 1179, 197, 1185, 1186, 1210) a staging** — el dataset de staging és més petit i diferent; cap fila real de la nomenclatura repetida documentada a PROD es pot inspeccionar aquí.

**Veredicte BLOC 2: cal decisió humana abans de construir.** El vocabulari de sufixos EXISTEIX i està sembrat consistentment; el que falta no és "omplir un buit" sinó **triar entre estendre una llei que avui diu explícitament el contrari** (ESTAT sense sufix) i gestionar almenys una col·lisió real coneguda (`BW`). Sense les files reals dels 6 models de PROD, cap prova de la solució es pot fer contra staging.

---

## BLOC 3 — Corpus de cotes a staging

### 3.1 Inventari `/root/sembra_ai/`
30 fitxers, `root:root`. **27 `.ai`** (lot LOSAN, datats 26/07 19:30–19:36, 2,0–113,8 MB, permisos `-rwx------`). **3 `.md`**: `FTT_DISSECCIO_LOT_AI_LOSAN.md` (10.243 B), `FTT_POC_B_MODIFICAT_LOSAN.md` (14.683 B), `INFORME_SEMBRA_AI.md` (31.121 B, l'únic amb `-rw-r--r--`), tots del 26/07.

Codi relacionat: **només `backend/fhort/pom/management/commands/sembra_ai_report.py`** (708 línies, únic commit `52b5974e`). **NO EXISTEIX** cap `sembra_ai_write.py` ni cap altre command/patch amb "sembra_ai" al nom. Docstring (`:1-33`): informe **NOMÉS LECTURA** — extracció (`pdftotext -bbox`), red-gate (`pdftocairo -png`), resolució contra catàleg viu (mateix camí que F1: àlies→POMMaster, `__iexact`), detecció de col·lisions, geometria (aparellament golós etiqueta↔cota), `GTI_HINT`. Explícit a `:30`: **"FORA D'ABAST (Fase 2, no aquí): cap escriptura a POMPlacement."**

### 3.2 `PlacementProposal`/`POMPlacement`
`PlacementProposal` **NO EXISTEIX** al codi (consistent amb 1.2). `POMPlacement` **SÍ EXISTEIX**: `backend/fhort/models_app/models.py:1759-1856`. Docstring (`:1760-1774`): precedent de col·locació geomètrica sobre sketch de catàleg, extrems normalitzats 0..1, **"MAI escriu cap valor de mesura"**. Camps: `item_fitxer` (FK CASCADE), `pom` (FK PROTECT), `view_slot`, `x1,y1,x2,y2`, `label_dx/dy`, `source_kind`, `capa` (default `'exterior'`), `instancia` (default `''`). `UniqueConstraint(item_fitxer, pom, view_slot, capa, instancia)` (`:1822-1854`).

`SELECT count(*)` → **`fhort=0`, `los=0`. La taula existeix a les dues schemes però és buida a totes dues.**

### 3.3 Regeneració de coordenades
`sembra_ai_report.py` **calcula** geometria real per etiqueta (`extrems()`, `associate()`, ~`:349-373`) però **només l'agrega en comptadors del report; no la persisteix enlloc** (cap `.save()`/`.objects.create()`/CSV al fitxer — únic `open()` és per escriure el markdown de sortida, `:481, 605-606`). Sortida per defecte: `/root/sembra_ai/INFORME_SEMBRA_AI.md` + resum a stdout.

**Temps estimats: NO EXISTEIXEN.** Cap dels 3 `.md` conté cap xifra de temps/cost; `FTT_DISSECCIO_LOT_AI_LOSAN.md:133` diu literalment **"Tot mesurat, res estimat."** `INFORME_SEMBRA_AI.md` acaba (l.322): *"FASE 1 · cap escriptura a cap BD... Fase 2 (escriptura a POMPlacement) es briefa DESPRÉS de llegir aquest informe"* — **aquest briefing de Fase 2 no s'ha trobat enlloc del repo**.

Xifres de l'informe (26/07, `INFORME_SEMBRA_AI.md:267-272`): 2.782 codis extrets · 2.739 resolen net (98,5%) · 2.410 VERD · 329 GROC · 43 ÒRFE · 1.497 lligam segur · 2.286 lligam ampli.

### 3.4 Pont de vocabulari — 🚨 desactualitzat
Mostra de 17 codis (12 "DUPLICAT" + 5 "ÒRFE" de l'informe) contra `fhort.pom_pommaster.codi_client`/`pom_customerpomalias.client_code` (SQL `upper(...)=upper(...)`, avui):
- **Resolen** (directe o via àlies): `D, E4, J1, S, S2, U, U1` (7/17) i, només a `pom_pommaster`: `E7, L1` (2/17).
- **NO resolen per res** (0 a les dues taules): `BJ, C1, H, A1.2, AS, B9, D12, E4.2` — **8/17 = 47%**.

**El catàleg ha canviat substancialment entre el 26/07 (data de l'informe) i avui**: `BJ`, `C1`, `H` estaven marcats "DUPLICAT ×2" (VERD) i avui **no existeixen enlloc** al catàleg; `D` avui té exactament 1 fila (no 2 com deia l'informe). Coherent amb la neteja de catàleg v4/v5 (09/08→23/08, memòria de sessió). Nota secundària: totes les etiquetes "DUPLICAT" de l'informe porten literalment `"(família BJ)"` fins i tot per a codis sense relació — sembla bug d'etiquetatge del generador, no dada real.

`los.pom_pommaster`/`pom_customerpomalias`: **existeixen però buides** (0 files a totes dues) davant de 146/156 files a `fhort` — coherent amb `sembra_ai_report.py:13-14` ("el schema `los` és buit") i amb la llei de memòria de sessió.

**Veredicte BLOC 3: NO llest per a Fase 2.** El corpus és només un informe de lectura sense Fase 2 escrita ni briefada, i la resolució que conté ja no és de fiar (47% de la mostra ha caducat). Qualsevol regeneració de coordenades hauria de re-executar la resolució contra el catàleg d'avui, no reutilitzar l'informe del 26/07.

---

## BLOC 4 — Fitxa a dev HEAD (substrat del Patró B)

### 4.1 Croquis
Única via d'escriptura de `ModelFitxer`: `save_model_file` (`backend/fhort/models_app/services_fitxers.py:319-364`) i `save_item_file` (`:376-417`) — `ModelFitxerViewSet` és `ReadOnlyModelViewSet` + `DestroyModelMixin` (`views.py:345-348`, docstring explícit: única via d'escriptura és `save_model_file`). `tipus=tipus or 'ALTRES'` **encara vigent** (`:355`, `:400`); `'ALTRES'` és el `default` del camp (`models.py:495,599`).

Panell «Croquis i flats»: `TIPUS_GEOMETRIA = ['SKETCH_SVG','SKETCH_NET','SKETCH_FLETXES']` (`TechSheetEditor.jsx:69`), partició `fitxersSketch`/`fitxersAltres` a `:6167-6177` — **confirmat sense moure's**. **NO EXISTEIX** cap endpoint de reclassificar `tipus` d'un `ModelFitxer` ja pujat (només lectures a `views.py`).

**Obert:** no s'ha localitzat amb certesa el punt de pujada del croquis que fixi `tipus='SKETCH_SVG'` explícit — caldria seguir el flux concret d'upload del canvas per confirmar si el croquis pujat cau a `'ALTRES'` per defecte (cas en què el panell mai el trobaria).

### 4.2 Veredicte
Única taula impresa amb el veredicte com a TEXT: taula Q8a (`insertTaulaFitting`, `TechSheetEditor.jsx`). `useEtiquetaVeredicte()` cridat a `:5254`; forma CURTA usada a `:5554` (`etiquetaVeredicte(f.veredicte, true)`). Columna `verdict`: `width: 22` (`:5545`). La llegenda "NO OK = follow spec" ve de i18n (`q8_nota_no_ok`, `ca.json:3327`), no de codi dur; el `push` de la nota és a `:5573` (correcció: és la llegenda de peu, no la cel·la).

**`FittingPrintSheet.jsx:16`: el full de fitting NO imprimeix veredicte com a text — són caselles per marcar.** Q8a és, doncs, l'ÚNIC lloc imprès amb text de veredicte.

**Patró NAME ja fet i reutilitzable**: `cellaPom`/`cellaCodi` (`:5331`, `:5338`) construeixen `{text, wrap:true}`; `buildTableCellPrimitives` (`:910`) i `liniesQueOcupa` (`:976`) fan multilínia amb alçada per fila (patró C2, `:967-980`). **La cel·la `verdict` d'avui és un string pla** (`:5554`), no `{text, wrap:true}` — el mateix mecanisme de NAME no s'hi aplica encara.

**💡 PROPOSTA (a validar):** convertir la cel·la `verdict` a `{text: etiquetaVeredicte(f.veredicte, false), wrap:true}` reutilitzant el mecanisme de `:910-980` permetria la forma llarga sense desbordar, igual que NAME.

### 4.3 Inserció de taules
`inserirGrupPaginat` (`TechSheetEditor.jsx:5138`), cridada des de 5 punts (`:5484,5574,5655,5761,5805`). `Y_INICI = 14` (mm, `:5141`). **NO EXISTEIX** cap `fitTableObj` literal; la taula personalitzada/BOM passa per `insertTableCustom`, que també acaba a `inserirGrupPaginat` (`:5761/5805`).

Geometria de capçalera: `MASTER_HEADER_GEOM` (`:1386-1391`, `x=10.09mm, y=13.76mm, width=276.84mm, height=24.84mm`), `masterHeaderGeomFor(fmtKey)` (`:1394-1397`), objectes `kind:'header'` creats a `insertHeader` (`:5888`). **Cap literal `y=38` al codi** (valor real `y=39pt≈13.76mm`). **`Y_INICI` (14mm) i la `y` de capçalera (13.76mm) NO estan enllaçats per codi** — són constants independents, casualment properes.

### 4.4 Nomenclatura
`aplicaInstancia`: `EditableTable.jsx:658-706`. `germanaCapaRapida` (tecla L): `EditableTable.jsx:554-581`. `gravar_pom_view`: `views.py:2384`. `germanes_homonimes`: `pom/nomenclatura.py:650-685` (`germanes_de_rebateig` fins `:712`).

**Mapa complet de qui crida `germanes_homonimes`/`germanes_de_rebateig` (cerca exhaustiva, backend):**
1. `gravar_pom_view` (`views.py:2540`) — jutja tot el payload de la pantalla de gènesi en desar.
2. `base_measurement_noms_view` (PATCH, `views.py:4123`, crida a `:4201-4206`) — **NOMÉS quan `nom_fitxa` canvia** (guarda `:4198`).

**🚨 Troballa transversal — forat de cobertura confirmat:** quan la germana neix des de la pantalla de PRESA (`esPresa`, `CheckMeasureEditor.jsx`), el camí **no passa per cap dels dos punts d'entrada**:
- `germanaCapaRapida`+`esPresa` → `presa.onNova` → `baseMeasurements.create` (`CheckMeasureEditor.jsx:764-773`) → `POST /api/v1/base-measurements/` → `BaseMeasurementViewSet.perform_create` (`views.py:536-538`), `ModelViewSet` genèric **sense cap crida a `germanes_homonimes`**.
- `aplicaInstancia`/`parteix`+`esPresa` → `presa.onParteix` (`:721-738`): la germana nova neix amb `baseMeasurements.create` directe, mateix `perform_create` sense judici.

**Import i tancament de fitting: NO criden `germanes_homonimes` enlloc** (cerca exhaustiva fora de tests). Cap comentari al codi (`onNova`/`onParteix`) esmenta aquest forat.

### 4.5 A2
`_desar_precedent`: `pom_placement_views.py:132-181`; l'`update_or_create` amb eixos fixos a `:173-176`: **`capa=MeasurementLayer.SLUG_DEFECTE, instancia=''`** — confirmat literal, `SLUG_DEFECTE='exterior'` (`pom/models.py:263`). Comentari propi (`:165-171`) reconeix el deute explícitament: "el body no porta eixos fins a C4-ins."

Portes del front: `desarUnaPrecedent` (`TechSheetEditor.jsx:6415-6422`) i `escriurePrecedentSilent` (`:6427-6434`), totes dues via `construirPrecedentCota`, que **mai envia `capa`/`instancia`** al body — coherent amb el fet que el backend els ignora sempre.

**Veredicte BLOC 4: substrat majoritàriament llest, amb 3 peces concretes pendents.** (a) croquis: falta confirmar/fixar el `tipus` en pujar; (b) veredicte: falta aplicar el patró `wrap:true` ja provat; (c) nomenclatura: el forat de PRESA és un risc real i no documentat, més greu que els 3 punts originals del brief perquè no té cap mitigació parcial (Import/rebateig almenys en tenen alguna).

---

## Q1-Q5 — Resposta directa

**Q1. Commits i migracions de `dev` que no són a `main`, rellevants:** cap — els 17 commits ja són a PROD (confirmat per l'Agus). L'única cosa rellevant que en queda és la desconnexió `origin/main`↔`6af581cd` (BLOC 1.1, higiene de refs, no bloqueja). Migracions: sense divergència a cap schema (BLOC 1.2).

**Q2. El vocabulari de sufixos d'estat i de capa ja existia?** El d'INSTÀNCIA (POSICIÓ) sí, complet i sembrat (`seed_measurement_instances.py`, `pom/models.py:305-310`, acta `INSTANCIES_POSICIO_V2_2026-08-23.md`). El d'ESTAT i el de CAPA **deliberadament no en tenen** (llei explícita, no buit accidental) — `seed_measurement_instances.py:32-37`. `MeasurementLayer` ni tan sols té camp `sufix` (`pom/models.py:265-274`). El comentari a `services_consentiment.py:28-31` que sembla dir el contrari és sobre un forat local i diferent (frase humana del modal de consentiment, `DIAGNOSI_CONSENTIMENT_GERMANES.md` BLOC Q2), no sobre aquest vocabulari.

**Q3. Propostes lliures de col·lisió:** cap de les tres (estat A, estat B, capa `·LN`) és lliure de conflicte amb la llei ja escrita (contradiuen "ESTAT sense sufix"). A més, `BW` (estat A) col·lideix de fet a `fhort` amb un POM actiu ("Fold width") i un àlies de client. `los` no té cap col·lisió de dades detectada, però hereta el mateix conflicte de llei.

**Q4. On és el corpus i què caldria per tenir coordenades reals:** `/root/sembra_ai/` (27 `.ai` + 3 `.md`), FASE 1 només-lectura (`sembra_ai_report.py`), que calcula geometria però no la desa (BLOC 3.3). `POMPlacement` existeix i és buit a `fhort`/`los`. Caldria: (1) una Fase 2 que escrigui `POMPlacement` — no existeix ni com a command ni com a briefing escrit; (2) re-executar la resolució de codis contra el catàleg d'avui, no confiar en l'informe del 26/07 (47% de la mostra ja no resol).

**Q5. Mapa fitxer:línia dels punts a tocar:**
- SVG=croquis: `services_fitxers.py:319-364/376-417` (escriptura), `TechSheetEditor.jsx:69,6167-6177` (lectura). Falta: confirmar el punt de pujada del croquis (obert).
- Veredicte sencer sense nota: `TechSheetEditor.jsx:5254,5545,5554` (aplicar patró `wrap:true` de `:5331,910,976`).
- Taules sota la capçalera: `TechSheetEditor.jsx:5138,5141` (`Y_INICI`) i `:1386-1391,5888` (capçalera) — avui NO enllaçats, caldria decidir si es lliga `Y_INICI` a `MASTER_HEADER_GEOM.y+height`.
- Sufix proposat + avís en crear: `diccionariMesures.js:242-262` (compondre), `pom/nomenclatura.py:650-685` (judici), portes que el criden: `views.py:2540` (gènesi) i `:4201-4206` (rebateig) — **falta una tercera porta a `BaseMeasurementViewSet.perform_create` (`views.py:536-538`) per cobrir la PRESA**.
- A2: `pom_placement_views.py:173-176` (backend), `TechSheetEditor.jsx:6415-6422,6427-6434` (front) — tots dos costats ignoren `capa`/`instancia` avui.

---

## Taula final de riscos

| Àrea | Estat | Detall |
|---|---|---|
| dev↔main (contingut) | ✅ SENSE RISC | 17 commits ja a PROD; `origin/main` només desactualitzat de refs |
| Migracions (3 schemes) | ✅ SENSE RISC | Sincronitzades, sense `0064` fantasma a staging |
| Vocabulari sufix POSICIÓ | ✅ EXISTEIX | Sembrat, idèntic a les 3 schemes |
| Vocabulari sufix ESTAT/CAPA | 🚩 FALTA (per LLEI, no oblit) | Contradiu llei escrita; decisió humana abans de construir |
| Col·lisió `BW` (estat A, `fhort`) | 🚩 CONFIRMAT | POM actiu + àlies existents amb aquest codi |
| 6 models BRW de PROD | 🚩 NO REPRODUÏBLE A STAGING | No existeixen; cap prova directa possible aquí |
| Corpus `/root/sembra_ai/` | 🚩 NOMÉS FASE 1 | Cap coordenada persistida; Fase 2 no briefada |
| Pont de vocabulari LOSAN | 🚩 DESACTUALITZAT | 47% de la mostra ja no resol contra el catàleg d'avui |
| `POMPlacement` a BD | ⚠️ BUIT | Taula i model llestos, 0 files a `fhort`/`los` |
| Croquis SVG → tipus | ⚠️ OBERT | Punt d'upload amb `tipus` explícit no localitzat |
| Veredicte llarg a taula | ⚠️ FALTA APLICAR PATRÓ | Mecanisme `wrap:true` ja existeix per a NAME, no per a VERDICT |
| Taules sota capçalera | ⚠️ NO ENLLAÇAT | `Y_INICI` i geometria de capçalera són constants independents |
| Avís d'homonímia en CREAR (gènesi/rebateig) | ✅ EXISTEIX | 2 portes cobertes |
| **Avís d'homonímia en CREAR (PRESA)** | **🚨 FORAT REAL, NO DOCUMENTAT** | `BaseMeasurementViewSet.perform_create` sense judici; descobert en aquesta diagnosi |
| A2 (`capa`/`instancia` fixos) | 🚩 DEUTE RECONEGUT AL CODI | Backend i front ignoren els eixos; pendent "C4-ins" |
| 1.3 (config staging vs PROD) | ⏳ PENDENT DE VERIFICAR | Sense accés PROD des d'aquesta sessió read-only |
