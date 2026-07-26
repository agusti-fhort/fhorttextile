# DIAGNOSI — S10 · GRADING BROWNIE (diccionari POM ja pujat → primera GradingRuleSet real de client sobre la blusa POP)

> **Data:** 2026-07-16 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev` (HEAD `d57c888`)
> **Abast:** dir QUÈ HI HA abans de crear la primera `GradingRuleSet` real de client sobre el run
> XXS-XS-S-M-L (base S) de la blusa **POP** de Brownie i traçar-ne el comportament fins al final
> (taules → fitxa tècnica → motor de patrons). **Aquesta diagnosi no construeix res.**
>
> **Convenció:** tota afirmació porta `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi**
> (verificat, no especulat). Les xifres venen de `SELECT` reals sobre staging (schema `fhort`, tenant id=2).
> Les propostes van marcades `💡 PROPOSTA (a validar)` i **no** són decisions (Patró C).
>
> **Guardes:** cap escriptura de codi, cap migració, cap restart, cap fixture. BD només `SELECT`.
> Únic fitxer creat: aquest.

---

## RESUM EXECUTIU

1. **El diccionari Brownie ÉS pujat i viu, i cobreix el spec POP tant com s'esperava.** 92 àlies a
   `pom_customerpomalias.client_code` (86 `DICCIONARI` + 4 `IMPORT` + 2 FTT). Dels **43 codis del spec POP,
   36 casen i 7 no** — i els 7 forats són **EXACTAMENT** els esperats `[D1, M1, M2, I4, J4, I1, L1]`
   (hipòtesi confirmada amb dades). El diccionari entra al matching **només per codi** (camí àlies,
   `extraction_views.py:773`), NO per descripció: el docstring del model que promet matching per descripció
   **menteix** (`pom/models.py:266-269` vs `:770-819`).

2. **Dues pèrdues silencioses en col·lisió que cal reconciliar amb la Montse abans de crear res.** El codi
   `U` va quedar-se amb **CRUCE DELANTE** i **TAPETA ANCHO va caure sense traça** (`update_or_create`
   last-wins). Els codis `B4`/`B6` (zones ARRIBA/ABAJO) **mai van entrar** (0 files). Cap mecanisme els captura.

3. **Customer Brownie existeix (id=7 / BRW) amb 38 models; 10 són blusas — però CAP es diu "POP" i CAP té
   grading assignat.** "POP" és el nom del *document font*, no d'un model creat (0 files a tota la taula). Les
   blusas (163-167, 173-177; golden = **163 Blusa TATE**) tenen mesures parcials i `grading_rule_set=NULL`.
   → El pendent antic "esborrar-repujar models Brownie" es pot decidir amb noms i cognoms (§DECISIONS D-1).

4. **NO existeix un run XXS-XS-S-M-L exacte: el run canònic és el superconjunt `ss=29 ALPHA_EU_W`
   (XXS…3XL).** El matching el resol **1.0** (el score només mesura etiquetes d'entrada reconegudes,
   `matching.py:92`) i la base S és seleccionable. Decisió: crear un run acotat XXS-L **o** treballar sobre
   ss=29 amb break (§DECISIONS D-3). L'item blusa gti=5 està a mitges (37 GarmentPOMMap sí; ruleset, base i **ItemBaseMeasurement=0** no).

5. **El camí net per crear la primera GradingRuleSet REAL de client és el wizard size-map
   (`pom/size_map_views.py:816`)** — l'ÚNIC que escriu `ORIGEN_CLIENT_RUN` + `customer`. El CRUD/UI genèric
   (`GradingRuleSets.jsx`) **no pot fixar `origen` ni `customer`** (no són a `Meta.fields`) → naixeria
   `NULL/NULL`, indistingible d'un canònic. Les 25 files actuals tenen `origen=NULL`.

6. **El motor resol la coexistència ModelGradingRule↔GradingRuleSet de manera determinista, però PER-SET:
   resident guanya, el set és fallback només si no hi ha CAP resident** (`pom/services.py:539-563`). Si el
   model té regles residents, **el ruleset assignat s'ignora sencer**. PERÒ assignar el ruleset (update-step2)
   **re-materialitza** les regles del set com a residents (`views.py:616-621`) — per tant l'assignació SÍ té
   efecte perquè planta residents. `GradingException` està **jubilada** (taula eliminada, `0038`); l'única
   excepció viva és `ModelGradingOverride` (BD=0 files).

7. **El node graduat travessa fins al final, i el motor de patrons NO és només disseny.** `GradedSpec` té
   **tres destinacions vives**: Escalat mode-model (§5.3), TechSheet/PDF via snapshot `graded-table` (§5.4) i
   **Motor de Patrons** (`export`→`grading_projection.py:156`, llegint GradedSpec pel port `adapters.py:432`).
   L'import respecta la llei SOBIRANIA (reté base+deltes+breaks, no materialitza versió/specs, `:1936-1943`).

8. **⚠️ El forat que bloqueja ingerir el POP pel wizard és d'ENTRADA, no de persistència.** Ni
   l'`EXTRACTION_PROMPT` ni el toggle W3 (absoluts XOR deltes) modelen "base + 2 columnes d'increment
   (break)"; el codi la declara "peça NOVA no coberta" (`grading_utils.py:412-418`). El break intern SÍ
   existeix i és robust (`nb==1`→LINEAR-amb-break), però només si l'entrada arriba com a absoluts-per-talla.

---

## BLOC 0 — Estat fred de l'entorn

### 0.1 Identitat tenant/BD (foto canònica — verificació pendent des de 2026-06-24, ARA TANCADA)

Connexió real (de `backend/.env`): **`DB_HOST=127.0.0.1`, `DB_PORT=5433`, `DB_NAME=ftt_staging`,
`DB_USER=ftt_staging`**. El settings llegeix `os.environ['DB_NAME']` a `backend/fhort/settings.py:121`.

**Bases de dades** (`pg_database`): `ftt_staging` + `test_ftt_staging` (BD de test de Django). No n'hi ha d'altra amb `ftt`.

**Schemas** (`information_schema.schemata`): només **`fhort`** i **`public`**. El schema de tenant real és **`fhort`**.

**Tenants** (`public.tenants_client` — django-tenants, NO `clients_client`):

| id | schema_name | nom |
|----|-------------|-----|
| 1  | `public`    | FHORT System |
| 2  | `fhort`     | FHORT Management |

**Dominis** (`public.tenants_domain`):

| domain | tenant_id | is_primary |
|--------|-----------|------------|
| `localhost` | 1 | ✔ |
| `backoffice.fhorttextile.tech` / `stagingbackoffice.fhorttextile.tech` | 1 | |
| `fhorttextile.tech` | 2 | ✔ |
| `178.105.217.125` | 2 | |
| **`staging.fhorttextile.tech`** | **2** | |

> **Foto canònica confirmada:** el tenant de treball és **id=2, schema `fhort`**, servit pel domini
> `staging.fhorttextile.tech` (per això tot `curl` va amb `-H "Host: staging.fhorttextile.tech"`).
> Queda **desmentit** qualsevol "tenant id=6": no existeix. El schema `fhort` té **114 taules**.

### 0.2 git — cens del que hi ha SENSE push (input per al deploy de l'Agus)

- Branca: **`dev`**. HEAD: **`d57c888`** (`QA-TALLER: acceptar/desacceptar un desajust des de la fila` · sprint H · T3).
- `origin/dev` = **`f7ef6c6`** (fetch d'avui 2026-07-16 09:14). `origin/main` → `HEAD`.
- **`origin/dev..dev` = 4 commits SENSE push** (tot l'sprint **H · QA-TALLER**, el semàfor de desajustos):

  ```
  d57c888 QA-TALLER: acceptar/desacceptar un desajust des de la fila, amb rastre visible (H · T3 · UI)
  be79b56 QA-TALLER: el tècnic accepta un desajust, amb rastre auditable (H · T2 · registre)
  224410c QA-TALLER: el panell pinta el semàfor, no el dins/fora (H · T1 · presentació)
  3549653 QA-TALLER: el veredicte és un semàfor, no un dins/fora sec (H · T1 · motor de grau)
  ```

- `dev..origin/dev` = **0** (dev no està darrere; `origin/dev` és avantpassat directe de `dev`).
- `origin/main..dev` = **53 commits** (tot el treball acumulat des de l'últim deploy a `main`).

> **Nota de mètode:** `origin/main` NO descriu PROD ni staging desplegat; és només la referència de deploy.
> Els 4 commits de l'sprint H són el pendent immediat de push. La resta d'sprints "sense push" que
> figuren a la memòria de sessió **ja són a `origin/dev`** (l'Agus va pujar fins a `f7ef6c6` avui).

**Veredicte BLOC 0:** llest. Foto canònica tancada (tenant 2 / schema `fhort` / port 5433); pendent de push = 4 commits sprint H.

---

## BLOC 1 — El diccionari Brownie ja pujat

> Font de veritat = BD ACTUAL. L'auditoria `docs/diagnosis/AUDITORIA_CUSTOMERPOMALIAS_COMPLETA_2026-07-08.md`
> descriu un estat ANTIC (8 àlies); avui el diccionari ja és pujat (**92 àlies**).

### 1.1 On viu el diccionari

Tres models (`backend/fhort/pom/models.py`):

- `POMGlobal` — catàleg canònic global (schema public). `codi` (`models.py:31`), `nom_en:32`, `abbreviation:42`. **No conté codis Brownie.**
- `POMMaster` — catàleg per-tenant (`models.py:144`). Codi canònic del tenant a `codi_client` (`models.py:159`), `nom_client:160`, FK `pom_global:145`.
- **`CustomerPOMAlias` — AQUÍ viu el diccionari Brownie** (`models.py:236`):
  - `customer` FK → `tasks.Customer` (`models.py:249`)
  - `pom` FK → `POMMaster`, **nullable** (`models.py:257`; àlies sense POM = vocabulari pendent de mapar)
  - **`client_code`** (`models.py:260`) — **AQUÍ viuen els codis Brownie** (A, EK, SF, U, B, 0…)
  - `description_en` (`:268`), `description_local` (`:269`), `language` (`:270`), `origen` (`:271`, choice `DICCIONARI` afegit a migració 0035), `pendent_revisio` (`:272`)
  - `client_description` (`:264`) — **OBSOLET**, no s'hi escriu
  - Unicitat: `UniqueConstraint(customer, client_code)` (`models.py:279-282`)

**Loader:** `pom/dictionary_views.py:163` — `CustomerPOMAlias.objects.update_or_create(customer, client_code, defaults={pom, description_en, description_local, language, origen='DICCIONARI'})`. POMs nous es creen a `:146` amb `pendent_revisio=True`, `origen_import="diccionari:BRW:<data>"`.

**Recompte a BD (92 àlies):** BRW `DICCIONARI` = **86** · BRW `IMPORT` = 4 (F, FF, U2, U3) · FTT `MIGRACIO` = 2 (T.1, T.2). Els 6 BRW `MIGRACIO` antics (migració 0031) ja no existeixen: el diccionari ha reescrit l'espai de codis per lletra.

> **Resposta exacta:** els codis Brownie viuen a la taula **`pom_customerpomalias`**, columna **`client_code`**.
> Descripcions a `description_en`/`description_local`. El POM canònic resolt és la FK `pom` → `pom_pommaster`.

### 1.2 find_pom_master — camins de matching en ordre

Ubicació: **`backend/fhort/models_app/extraction_views.py:728`** (`def find_pom_master(code, description, customer=None)`).

| # | Camí | fitxer:línia | Taula/columna llegida | match_type / conf |
|---|---|---|---|---|
| (a) | **Àlies exacte del customer** | `extraction_views.py:770-780` | `CustomerPOMAlias` amb `customer=` + `client_code__iexact` (contra `code` i `desc_clean`) + `pom__isnull=False` + exigeix `alias.pom.actiu` | `alias_match` / HIGH |
| (b) | Sinònim curat | `:782-795` | dict Python `_POM_SYNONYMS` (`:704`) → `POMMaster.nom_client` / `POMGlobal.nom_en` | `synonym_match` HIGH |
| — | Descripció per nom_client | `:797-804` | `POMMaster.nom_client` | `exact_description` HIGH / `description_match` MEDIUM |
| — | Descripció per POMGlobal | `:806-819` | `POMGlobal.nom_en`, `.abbreviation` | `global_*` / `abbreviation_match` |
| (c) | Codi numèric + 'lining' | `:821-828` | `POMMaster.nom_client` | `numeric_lining_match` MEDIUM |
| (c-bis) | Àlies pendent revisió (suggeriment) | `:835-836` | `CustomerPOMAlias` | `alias_pendent_revisio` LOW |
| (d) | Fallback `codi_client` exacte | `:841-844` | `POMMaster.codi_client__iexact` | `legacy_code_match` LOW |
| (d) | Fallback root-prefix de lletres | `:846-856` | `POMMaster.codi_client` (arrel `^[A-Za-z]+`) | `root_code_match` LOW |

> **El diccionari entra pel camí (a) ÀLIES, via `client_code` (`:773`), NO pel camí "synonym" (b).**
> El camí (b) llegeix el dict hardcodejat `_POM_SYNONYMS`, que **no conté res del diccionari Brownie**.

### 1.3 Cobertura dels 43 codis del spec "POP"

Creuament read-only de `pom_customerpomalias` (BRW) per `client_code`: **36/43 MATCH · 7/43 NO-MATCH**.

| spec_code | result | origen | pom canònic | | spec_code | result | origen | pom canònic |
|---|---|---|---|---|---|---|---|---|
| A | ✔ | DICCIONARI | CH (273) | | J | ✔ | DICCIONARI | BIC (295) |
| BT | ✔ | DICCIONARI | BT (467) | | **J4** | **✗** | — | — |
| B | ✔ | DICCIONARI | WA (275) | | JJ | ✔ | DICCIONARI | JJ (468) |
| D | ✔ | DICCIONARI | SK SW (326) | | J1 | ✔ | DICCIONARI | SL OP (297) |
| **D1** | **✗** | — | — | | J2 | ✔ | DICCIONARI | J (459) |
| G1 | ✔ | DICCIONARI | G1 (453) | | J3 | ✔ | DICCIONARI | CUF H (299) |
| E2 | ✔ | DICCIONARI | E2 (465) | | I3 | ✔ | DICCIONARI | I3 (461) |
| E3 | ✔ | DICCIONARI | A.2 (420) | | **I1** | **✗** | — | — |
| E | ✔ | DICCIONARI | K.2 (431) | | P2 | ✔ | DICCIONARI | P (441) |
| E5 | ✔ | DICCIONARI | SH DR (286) | | P1 | ✔ | DICCIONARI | P1 (442) |
| E1 | ✔ | DICCIONARI | SH (277) | | L | ✔ | DICCIONARI | L (484) |
| E4 | ✔ | DICCIONARI | E4 (455) | | **L1** | **✗** | — | — |
| EK | ✔ | DICCIONARI | NK W (301) | | 0 | ✔ | DICCIONARI | I3 (461) |
| EK1 | ✔ | DICCIONARI | EK1 (463) | | F | ✔ | IMPORT | F (437) |
| EK2 | ✔ | DICCIONARI | EK2 (464) | | FF | ✔ | IMPORT | FF (438) |
| E7 | ✔ | DICCIONARI | E7 (475) | | F1 | ✔ | DICCIONARI | F (437) |
| EP | ✔ | DICCIONARI | EP (456) | | **M1** | **✗** | — | — |
| E8 | ✔ | DICCIONARI | E8 (476) | | **M2** | **✗** | — | — |
| U2 | ✔ | IMPORT | U2 (498) | | SF | ✔ | DICCIONARI | AH DEP (284) |
| U3 | ✔ | IMPORT | U3 (499) | | S | ✔ | DICCIONARI | S (457) |
| I | ✔ | DICCIONARI | SL (292) | | S2 | ✔ | DICCIONARI | S2 (458) |
| **I4** | **✗** | — | — | | | | | |

> **Els 7 forats són EXACTAMENT `[D1, M1, M2, I4, J4, I1, L1]` → HIPÒTESI DELS 7 FORATS CONFIRMADA amb dades.**
> Cap dels 7 esperats casa; tots els altres 36 casen (tots via `client_code`). Nota: `0` i `I3` resolen al
> **mateix** POM 461; `F1` (DICCIONARI) i `F` (IMPORT) resolen al **mateix** POM 437.

### 1.4 Col·lisions

Unicitat `(customer, client_code)` (`models.py:279`) + loader `update_or_create` (last-wins) → **cap
`client_code` duplicat pot coexistir** (verificat: `HAVING count>1` = 0 files).

- **Codi U** (segons Agus apuntava a TAPETA ANCHO **i** CRUCE DELANTE): una sola fila `U → pom 439
  (FRONT OVERLAP / CRUCE DELANTE)`. **CRUCE DELANTE ha guanyat; TAPETA ANCHO va caure sense traça**
  (`update_or_create` last-wins, no crea 2 files). L'únic "TAPETA" a BD és `TR → 489 PLACKET HEIGHT`, una
  altra mesura. **TAPETA ANCHO perdut silenciosament** (POMMaster 343 PLCK W sense àlies).
- **Codis B4 / B6** (suposada duplicació ARRIBA/ABAJO): **0 files — NO van entrar**. Existeixen `B → WA (275)`
  i `B1 → WA (275)` (tots dos DICCIONARI, `pendent_revisio=f`). Sense rastre de si B4/B6 van col·lisionar o mai van arribar.
- **Col·lisions de destí legítimes** (>1 codi de client → 1 POM, patró vàlid `models.py:239-240`): pom 437←{F,F1,F2},
  pom 275←{B,B1}, pom 484←{L,P}, pom 461←{0,I3}, etc. No són duplicats il·legals.

### OBERT/DUBTÓS — BLOC 1

1. **⚠️ El docstring del model MENT:** `models.py:266-269` diu que `description_en`/`description_local`
   "alimenten find_pom_master com a senyal addicional". **FALS al codi:** `find_pom_master` (`:770-819`)
   només llegeix `client_code__iexact` (contra `code` i `desc_clean` de la línia d'extracció), **mai** les
   columnes `description_en`/`description_local` de l'àlies. **El diccionari resol EXCLUSIVAMENT per codi.**
2. **TAPETA ANCHO perdut sense traça** (col·lisió codi U). Cap "pendents_vincular" ho captura en aquest camí. Cal mirar l'Excel origen.
3. **B4/B6 inexistents:** no es pot confirmar si van col·lisionar o mai van arribar; cal l'Excel origen.
4. **F1→437 vs F→437** (descripcions diferents, mateix destí): possible mapatge lossy, no verificat contra intenció de domini.

**Veredicte BLOC 1:** el diccionari és pujat i **cobreix 36/43 codis del spec POP** (els 7 forats són els
esperats). Viu a `pom_customerpomalias.client_code` i entra al matching **només per codi** (camí àlies), no
per descripció. Dues pèrdues silencioses en col·lisió (TAPETA ANCHO; B4/B6) que cal reconciliar amb la Montse.

---

## BLOC 2 — Customer i models Brownie

**Ubicació canònica dels models** (columnes verificades): `Customer` → `tasks/models.py:194`
(`codi`, `nom`, `active`, `is_self`); `Model` → `models_app/models.py:75` (`codi_intern`,
`codi_client`, `nom_prenda`, `customer_id`, `estat`, `fase_actual`, `garment_type_item_id`,
`grading_rule_set_id`, `size_system_id`); `BaseMeasurement` → `models_app/models.py:542` (FK `model`).

### 2.1 Customer Brownie — EXISTEIX

`Customer` **id=7**, `codi=**BRW**`, `nom='Textiles y Confecciones Brownie SL'`, `active=t`, `is_self=f`.

**Cens: 38 models amb `customer_id=7`.** Fets:

- **Tots apunten a `size_system_id=29`** (ALPHA_EU_W). Cap excepció.
- **Cap té `grading_rule_set` EXCEPTE 3:** model **162** (grs=75), **182** (grs=75, `[QA-SC] OLIVIA DRESS`)
  i **188** (grs=79, ROSALIA). **La resta = `grs=NULL`.**
- **10 blusas** amb `garment_type_item_id=5` (blouse): ids **163-167 i 173-177**
  (TATE, CLIMENTA, RUFUS, MEREDITH, OWEN, DERECK, CALLIE, LLOYD, KAYCE, JAMIE). Més blusas addicionals en
  fase Pending amb gti=5 (256-260…). **Cap blusa Brownie té `grading_rule_set` (totes NULL).**
- Mesures base per model (`BaseMeasurement`): els treballats tenen 16-37 (164/165/166/167/175 = 37;
  163 = 25); molts Pending = 0. Estat: **tots `estat='Nou'`**; fases variades (Dev/Proto/Pending/SizeSet/TOP).

### 2.2 Model "POP" o blusa Brownie

**⚠️ NO EXISTEIX cap model "POP"** — cerca `codi_intern`/`nom_prenda`/`codi_client ILIKE '%pop%'` →
**0 files a tota la taula** (no només Brownie). El nom "POP" del brief **no correspon a cap model creat**;
és el nom del *spec/document font*, no d'un model existent.

Sí existeixen **10 models "Blusa …"** (llistats a 2.1), tots gti=5, ss=29, **grs=NULL**. El més treballat
és el **163 (Blusa TATE)** — el "golden" de patrons/taller a les memòries.

**Veredicte BLOC 2:** Customer Brownie existeix (id=7 / BRW). Hi ha 10 blusas però **cap amb grading
assignat i cap anomenada POP**. → Alimenta la decisió "esborrar-repujar models Brownie" (§DECISIONS): el
cens diu amb noms i cognoms que les blusas estan **a mitges** (mesures parcials, sense ruleset).

---

## BLOC 3 — Run de talles i item blusa

**Ubicació:** `SizeSystem` → `pom/models.py:292`; `SizeDefinition` → `pom/models.py:341`;
`GarmentTypeItem` → `tasks/models.py:286`; `GarmentPOMMap` → `pom/models.py:434`;
`ItemBaseMeasurement` → `pom/models.py:468`; matching → `models_app/matching.py`.

### 3.1 Run de talles + matching

**Run alfa dona:** `SizeSystem id=29`, `codi=ALPHA_EU_W`, `nom='Alpha EU — Women'`, `base_unit=ALPHA`,
`actiu=t`, target **WOMAN** (target_id=1), **8 talles: `XXS, XS, S, M, L, XL, XXL, 3XL`** (ordre 1-8,
tots amb `valor_numeric=NULL`).

> **⚠️ Matís clau:** **NO existeix un run amb EXACTAMENT `XXS-XS-S-M-L`.** El ss=29 és un
> **superconjunt** (arriba fins a 3XL). No hi ha cap altre run alfa de dona (els altres alfa són ss=30
> Men XS-3XL i ss=38 Teen XS-XL).

**Score del matching** — `match_size_system()` a `models_app/matching.py:57`, càlcul a `matching.py:92`:

```python
score = len(input_canon & etiquetes_canon) / len(input_canon)
```

És **fracció d'etiquetes d'ENTRADA reconegudes** — **no penalitza que el run tingui talles de més**.
Candidats = sistemes `actiu=True` del target amb `n_talles>0` (`matching.py:71-77`); desempat per
`base_unit` inferit (`matching.py:99-106`); llindar d'error si `score<0.5` (`matching.py:114`).

**Lectura per input `XXS,XS,S,M,L` + target WOMAN:** ss=29 → `{XXS,XS,S,M,L} ∩ {XXS…3XL}` = 5 →
**score = 5/5 = 1.0 (PERFECTE)**; ss=32 (numèric) → 0. Guanyador net ss=29, sense empat.
**Base S seleccionable:** `base_ok` (`matching.py:112`) comprova `canonical('S') in input_canon` → True;
la talla S és `SizeDefinition id=79` (ordre 3) del ss=29.

### 3.2 GarmentTypeItem blusa

**Item blusa ÚNIC:** `id=5`, `code=blouse`, `name=Blusa`, `active=t`, `garment_type_id=63`
(família BUTTONED_TOPS / grup TOPS). Estat dels lligams:

| camp / taula | valor | referència |
|---|---|---|
| `grading_rule_set_id` | **NULL** — l'item NO té ruleset | `tasks/models.py:319` |
| `base_size_definition_id` | **NULL** — sense talla base de plantilla | `tasks/models.py:306` |
| `GarmentPOMMap` | **37 mapes** poblats (quadra amb els 37 basemeas dels blusas treballats) | `pom/models.py:434` |
| `ItemBaseMeasurement` | **0 files** — plantilla de valors base BUIDA | `pom/models.py:468` |

> **Conseqüència:** la sembra item→model (origen `ITEM_STANDARD`, `pom/models.py:468-479`) **no pot
> funcionar avui** per la blusa: no hi ha ni valors base ni ruleset a nivell d'item. Els models blusa van
> omplir mesures **per una altra via** (import/manual), no per còpia item→model.
> ⚠️ `db_constraint=False` als FK de GarmentPOMMap/ItemBaseMeasurement cap a `tasks.GarmentTypeItem`
> (`pom/models.py:441`, `:480`): els counts per gti són fiables via ORM però sense FK real de BD.

**Veredicte BLOC 3:** el run canònic per a la blusa POP **no és XXS-L exacte sinó el superconjunt ss=29**
(el matching el resol 1.0, base S ok). L'item blusa gti=5 està **a mitges** (POMMaps sí, ruleset/base/
ItemBaseMeasurement no). → Decisió pendent: crear un run XXS-L acotat **o** treballar sobre ss=29 amb break.

---

## BLOC 4 — Camí de creació d'una GradingRuleSet de client

### 4.1 Com es crea AVUI una GradingRuleSet

**Model i camps del break:** `class GradingRuleSet` a `pom/models.py:506`. Els camps canònics del break
**NO viuen al set** sinó a la regla filla `GradingRule` (FK `rule_set`, `pom/models.py:602-616`):
`increment_base`, `increment_break`, `talla_break_label`, `talla_break_pos`. **La mateixa forma canònica
també viu a `ModelGradingRule`** (resident al model): `increment_base` `models_app/models.py:728`,
`increment_break:729`, `talla_break_label:730`, `talla_break_pos:731`.

**Camp `origen`** (migració `pom/migrations/0036_gradingruleset_origen.py:13-17`, 2026-07-10). Definició
`pom/models.py:520-530`. Choices:
- `CANONICAL` — catàleg propi FHORT, viatja a tenant nou.
- **`CLIENT_RUN`** ('Derivat de run de client') — **derivat de client**; ve d'un run/fitxa importat o d'autoria manual per a un client. **MAI viatja** (`pom/models.py:515-518`).
- `IMPORT` — font externa sense client.
- `null=True` = no classificat (files anteriors a la llei PROVINENÇA); el tanca `manage.py set_grading_origen` (existeix: `pom/management/commands/set_grading_origen.py`).
- **BD (fhort): les 25 files de `pom_gradingruleset` tenen `origen = NULL`** (cap classificada).

**Write path — DOS camins de creació amb validacions molt diferents:**

**A) CRUD genèric `GradingRuleSetViewSet`** (`pom/views.py:152`, serializer `pom/serializers.py:174`):
`ModelViewSet` per defecte → **cap validació de negoci al `create`**. Lògica custom només al `destroy`
(`pom/views.py:171-209`: 403 si `is_system_default`; 409 amb recomptes si hi ha SizingProfile/Model
dependents; `?force=1`). **⚠️ `origen` NO és a `Meta.fields`** (`serializers.py:203-213`) → per aquest
endpoint `origen` no és settable i queda NULL; `customer` tampoc s'omple.

**B) Camí RUN de client — wizard size-map** (`pom/size_map_views.py:816-819`) — **el veritable
"GradingRuleSet de client":**
```python
rule_set = GradingRuleSet.objects.create(
    nom=rs_nom, size_system=ss, actiu=True, target=target,
    origen=GradingRuleSet.ORIGEN_CLIENT_RUN, customer=alias_customer)
```
És l'**ÚNIC lloc** que escriu `ORIGEN_CLIENT_RUN` i lliga `customer`. Al voltant (`size_map_views.py:790-825`):
`filter().first()` (no hi ha unique `(size_system,nom)`); `on_conflict ∈ {update,new}`; si
`alias_customer is None` **no bloqueja** (crea "run genèric" amb warning, `:812-815`, confiant que `origen`
tanca la fuita); desa `pendents_vincular` (`:823-825`).

**UI `frontend/src/pages/GradingRuleSets.jsx`:** la pàgina declara *"Creació centralitzada a la Size
Library; aquí només consulta/edita/esborra"* (`:260`). Tot i així el `RuleSetModal` (`:902`) fa POST a
`/api/v1/grading-rule-sets/` sense `rs.id` (`:927-930`). Camps: `nom` (obligatori), `codi_sistema`,
`actiu`; target/construction/fit renderitzats **`disabled`** (`:1013-1015`). **El formulari NO demana
`customer` ni `origen`** → un set creat des d'aquesta UI neix `customer=NULL, origen=NULL`.

### 4.2 Foto G6 actual (CENS)

- **`targets` M2M** (`pom/models.py:564-570`): CONFIRMAT M2M, apunta a **`Target`** (NO SizeSystem/SizeRun).
  FK antic `target` es manté legacy (`:559-563`); `targets` és l'autoritatiu (S16-A). BD:
  `pom_gradingruleset_targets` = **28 files**. (Nota: la migració 0021 migrà `SizeSystem.target→targets`, no el ruleset; la M2M del ruleset és additiva S16-A.)
- **SizingProfile:** el motor llegeix **`model.grading_rule_set` directe** — `generate_graded_specs`
  `select_related('model__grading_rule_set')` (`pom/services.py:124`), `_load_grading_rules` cau a
  `GradingRule.filter(rule_set_id=model.grading_rule_set_id)` (`pom/services.py:555-559`), gate `_te_regles`
  mira `model.grading_rule_set_id` (`:536`). **`SizingProfile` (`pom/models.py:837`) NO és a la ruta del
  motor** — és objecte de biblioteca; només compta al `destroy` (`views.py:185,207`).
- **GradingException JUBILADA:** làpida a `pom/models.py:649-660`; **taula eliminada** per
  `pom/migrations/0038_delete_gradingexception.py` (verificat: `to_regclass('fhort.pom_gradingexception')`
  = NULL). Cap escriptor viu.
- **`ModelGradingOverride`** (`models_app/models.py:651`): override per-`(model,POM,size_label)` d'un
  fitting validat en talla no base; `unique_together` (`:684`), FK `fitting_ref→PieceFitting` (`:669-674`).
  El motor el llegeix amb **PRIORITAT sobre les regles** (`pom/services.py:183-190`). **BD fhort: 0 files.**
- **Guard de segellat:** `GradingVersion` a `fitting/models.py:62`, camp `aprovada:80`. Predicat únic
  `sealed_active_version(sf_id)` = versió amb `is_active AND aprovada` (`pom/services.py:86-97`). Porta
  d'escriptura única `_get_or_create_grading_version` (`pom/services.py:595-630`): si segellada →
  `raise SealedGradingVersionError` (`:613-615`), **cap auto-bump**. `bump_grading_version_and_generate(
  allow_reopen_sealed=False)` (`:633-634`), guard D-1 `:666-669`. `allow_reopen_sealed` entra per HTTP:
  `fitting/views.py:516` (`close` de PieceFitting) i `:79` (payload del 409).

### 4.3 ModelGradingRule i la PRECEDÈNCIA del motor (FET CRÍTIC)

`class ModelGradingRule` a `models_app/models.py:691` — regla canònica **RESIDENT al model**, una per
`(model,POM)` (`unique_together:741`). Camps: `logica:719`, `increment:723` (fallback legacy), `valors_step:724`,
forma canònica del break `increment_base:728 / increment_break:729 / talla_break_label:730 / talla_break_pos:731`,
`origen:733` (default CANONICAL; IMPORTED/CANONICAL/MANUAL), `actiu:734`. `pom` FK `db_constraint=False`
(cross-schema, `:711-717`). Es materialitza via `materialize_model_grading_rules(model, source_rules, origen)`
(`models_app/services.py:147-168`): wipe-and-recreate (`:156`), copia deltes+breaks però NO base ni talla_base.
**BD fhort: 191 files de `models_app_modelgradingrule`** (front actiu); contrast: **només 5 models** tenen `grading_rule_set_id`.

**Precedència — `_load_grading_rules(model)` (`pom/services.py:539-563`):**
```python
rules = ModelGradingRule.objects.filter(model_id=model.id, actiu=True)
if rules.exists():
    return {r.pom_id: r for r in rules}                    # ← RESIDENT GUANYA
if model.grading_rule_set_id:
    return {r.pom_id: r for r in GradingRule.objects.filter(
        rule_set_id=model.grading_rule_set_id, actiu=True)} # ← fallback al set
return {}
```

> **RESPOSTA: el motor llegeix PRIMER `ModelGradingRule` (resident). El `GradingRuleSet` assignat és
> FALLBACK, consultat NOMÉS si el model no té CAP regla resident activa.** `if/elif` mutu-excloent
> **per set complet, no per POM** (`pom/services.py:553`). El gate `_te_regles` (`:534-536`) fa la mateixa
> pregunta en el mateix ordre (G6/0b `:517-521`). **No hi ha doble font de veritat al mateix punt de decisió.**
>
> **⚠️ MATÍS CLAU (no és conflicte però és decisiu per a l'sprint):** la precedència és **per-set, no
> per-POM**. Si un model té *alguna* `ModelGradingRule` activa, el `GradingRuleSet` **s'IGNORA SENCER** —
> inclosos els POMs que el set cobriria i les residents no (aquests cauen a FIXED = base, `:191-193`, no a
> la regla del set). **Assignar un ruleset a un model que ja té regles residents NO aporta res al càlcul.**

**Fork complet per cel·la POM×talla** (`generate_graded_specs`, `pom/services.py:183-198`):
1. `ModelGradingOverride` (fitting) → guanya, petja `EXCEPTION` (`:183-190`).
2. regla de `_load_grading_rules` (resident O set, ja resolt) → `_apply_rule` (`:194-198`).
3. sense regla per aquell POM → FIXED = base (`:191-193`).

`_apply_rule` (`pom/services.py:719`) llegeix la regla per `getattr` (`:747`) → `ModelGradingRule` i
`GradingRule` són intercanviables. Forma «Peça A»: si `increment_base` poblat i `logica != 'STEP'`, gradua
per acumulació amb break resolt **per etiqueta contra el `size_run` DEL MODEL** (`:747-765`).

### OBERT/DUBTÓS — BLOC 4

1. **`origen`/`customer` inabastables pel CRUD/UI:** cap dels dos fronts els pot fixar en crear (no a
   `Meta.fields`, `serializers.py:203-213`; el modal no els demana). Un set creat manualment per a un
   client des de la UI neix `origen=NULL, customer=NULL` — indistingible d'un canònic fins que
   `set_grading_origen` el classifiqui a mà. Les 25 files NULL a BD ho confirmen. **El camí net és el B (wizard size-map).**
2. **Precedència per-set enfosqueix:** cap avís a la UI que, si un model té `ModelGradingRule`, el
   `grading_rule_set` assignat quedi inert. Risc de confusió d'operador (assignar un ruleset "que no fa res").
3. Escriptor exacte de `ModelGradingOverride` no traçat (BD=0 files, cap avui).

**Veredicte BLOC 4:** hi ha **dos camins de creació**; només el **B (wizard size-map,
`size_map_views.py:816`)** produeix un ruleset ben classificat (`ORIGEN_CLIENT_RUN` + `customer`). El motor
resol la coexistència de manera determinista **resident > set**, però **per-set**: cal decidir si la primera
GradingRuleSet real de Brownie s'assigna a un model **sense** regles residents perquè el set tingui efecte.

---

## BLOC 5 — Traçar el node fins al final

### 5.1 Assignació ruleset→model (què re-materialitza)

**Cadena front:** `RuleSetCard.jsx:44` → `models.updateStep2(model.id, {grading_rule_set_id: rs.id})` →
`endpoints.js:42` fa `PATCH /api/v1/models/${id}/update-step2/`. **Handler:** `update_model_step2`
(`models_app/views.py:596`, ruta `models_app/urls.py:193`).

**Què re-materialitza EXACTAMENT** (`views.py:616-621`):
```python
if model.grading_rule_set_id:
    with transaction.atomic():
        materialize_model_grading_rules(model, model.grading_rule_set.regles.all(), origen='CANONICAL')
```
Wipe-and-recreate de la **CONFIGURACIÓ, no de la sortida**: esborra les `ModelGradingRule` residents prèvies
(`services.py:156`) i en recrea una per cada `GradingRule` del ruleset (`:157-167`, `origen='CANONICAL'`).

> **Assignar un ruleset NO esborra ni recrea `GradedSpec`, NO recalcula, NO crea `GradingVersion`.** Només
> re-materialitza les regles residents (`ModelGradingRule`). Ho diu el comentari a `RuleSetCard.jsx:10-11`
> ("NO toca el motor generate_graded_specs") i `views.py:613`. La re-graduació és acte posterior i separat (§5.2).
>
> **⚠️ Casa amb el matís de 4.3:** en re-materialitzar amb `origen='CANONICAL'`, el ruleset assignat es
> converteix en `ModelGradingRule` residents. Aquí NO és inert (a diferència del cas "el model ja tenia
> residents pròpies"): l'assignació sí que planta les regles del set com a residents, sobreescrivint-ne les prèvies.

### 5.2 `generate_graded_specs` — el motor

**Signatura:** `pom/services.py:104` → `def generate_graded_specs(size_fitting_id: int) -> int`. Entrada única:
l'id d'un `SizeFitting`; retorna el nombre de `GradedSpec` creats/actualitzats. Carrega: `_load_grading_rules(model)`
(`:155`), `_load_model_overrides` (`:157`), `_load_base_measurements` (`:160`), `_get_or_create_grading_version(sf)` (`:169`).

**Precedència REAL per cel·la POM×talla** (`services.py:183-198`):
1. **override** (`:184`) → `graded_val = override`, petja `'EXCEPTION'`.
2. **~~exception~~ JUBILADA:** NO és un esglaó separat (G6/1a, `:186-188`); l'override porta l'etiqueta `'EXCEPTION'`.
3. **regla nul·la → FIXED** (`:191-193`) → `graded_val = base_val`.
4. **regla** (`:194-198`) → `_apply_rule`.

> **⚠️ Divergència doc↔codi:** l'ordre efectiu és **override → (regla-nul·la=FIXED) → regla** — **3 esglaons,
> no 4**. L'"exception" que el brief D-10 cita com a esglaó independent ja no existeix (és el disfressa de l'override).

**On es resol el break:** dins `_apply_rule` (`services.py:719`), forma canònica (`increment_base` poblat,
`:747-765`), **per etiqueta contra el `size_run` del MODEL, no del ruleset** (`:752-757`); acumula `brk` a partir de
`break_idx` (`:762-764`). El run del model surt de `model.size_run_model` (`:144`), talla base `model.base_size_label` (`:145`).

**GradedSpec = model Django** (`fitting/models.py:181`): FK `grading_version`, FK `pom`, `size_label`,
`graded_value_cm`, `grading_type_applied` (LINEAR/STEP/FIXED/ZERO/EXCEPTION), `increment_applied_cm`, `is_active`,
`generated_from_version`; `unique_together = (grading_version, pom, size_label)` (`:209`). Escriptura via
`_upsert_graded_spec` (`services.py:811`) amb guard dur: cap spec aterra sobre `GradingVersion` `aprovada=True`
(`:829-834`, `SealedGradingVersionError`).

**Qui crida `generate_graded_specs` AVUI** — els **3 canònics d'usuari** (D-10):
1. `views.py:1608` dins `generate_grading_view` (POST `generar-grading`).
2. `views.py:1759` dins `set_size_override_view` (POST override de talla).
3. `views.py:1895` dins `escalat_ajustar_talla_view` (l'`onGridSave` d'Escalat, §5.3).

> **⚠️ Però hi ha 5 cridadors runtime ADDICIONALS** (D-10 desactualitzat si diu "només 3"):
> `pom/grading_views.py:42` (regenerar-talles), `pom/services.py:369` (close_base), `pom/services.py:700`
> (bump_grading_version_and_generate), `pom/wizard_views.py:273` (wizard import), `clone_model_for_qa.py:111` (comanda QA).

### 5.3 Superfície Escalat (cadena fins a MeasureGrid, mode model)

1. **Endpoint:** `GET /api/v1/models/<id>/taula-mesures/` → `measurements_table_view` (`models_app/views.py:807`,
   ruta `urls.py:198`). Carrega `GradedSpec` de la versió vigent (`:838`) → cada fila `'graded': graded_by_pom.get(pom.id,{})`
   (`:878`); talla base de `base_value_cm` (`:874`); règim per POM via `_load_grading_rules` (`:853`, camps a `:880-883`).
2. **Fetch:** `PropagatedEditor.jsx:28` → `client.get('/api/v1/models/${modelId}/taula-mesures/')`.
3. **Adapter:** `PropagatedEditor.jsx:40-41` → `buildEscalatGroups`/`buildEscalatRows` (`fittingGridAdapter.jsx:108`/`:120`);
   `buildEscalatRows` llegeix `s === baseLabel ? row.base_value_cm : row.graded?.[s]` (`:124`), cel·les `lineId=${pom_id}:${s}` (`:128`).
4. **MeasureGrid:** `PropagatedEditor.jsx:149-155`; escriptura `onGridSave` (`:45-60`) → `models.escalatAjustarTalla` →
   `escalat_ajustar_talla_view` que re-crida `generate_graded_specs` (tanca el cicle).

### 5.4 Fitxa tècnica / PDF — hi arriben els GradedSpec?

**SÍ hi arriben** — però per una **porta paral·lela** (snapshot de SizeFitting), no pel front d'escalat mode-model:

- **Endpoint:** `GET /api/v1/fitting/<sf_id>/graded-table/` → `GradedSpecTableView` (`fitting/graded_spec_views.py:22`, ruta `fitting/urls.py:66`).
- **TechSheet:** insereix un `data_block` `kind:'graded_table'` amb `size_fitting_id` i re-llegeix aquell endpoint
  (`TechSheetEditor.jsx:2114/2984/3073`, render `:955`).
- **PDF/`.ftt`:** `services_ftt_document.py:249-250` — el `graded_table` és **"l'únic objecte amb binding VIU"**
  que re-llegeix `/api/v1/fitting/<sf_id>/graded-table/`. En clonar/desvincular → `size_fitting_id=None` (`:253`, `:324`).

> **Conclusió:** el node graduat SÍ travessa fins al PDF, però via el snapshot `graded-table` del SizeFitting
> (serializer `fitting/serializers.py:235`), **NO** via el `GradedSpec` que consumeix l'Escalat mode-model.
> **No és forat:** és una segona porta alimentada de la mateixa taula `GradedSpec`.

### 5.5 Motor de Patrons — QUÈ HI HA REALMENT A CODI

**EXISTENT-EN-CODI (verificat i CABLEJAT):**
- **Models `derivat_de`:** `ModelFitxer` (`models_app/models.py:328`) amb `derivat_de_item` (`:395`) i
  `derivat_de_model` (`:412`); `ItemFitxer` (`:459`). ViewSets `ItemFitxerViewSet` (`item_fitxer_views.py:28`),
  `ModelFitxerViewSet` (`views.py:147`), accions de derivació (`marcar_procedencia`). Migracions 0055/0056.
- **App `patterns/`:** engine complet a `patterns/engine/` (`aama_reader/writer`, `rul_reader/writer`,
  `grading_projection`, `dart_detection`, `natural_segments`, `sew`, `operations`, `seam_matching`, `geometry`,
  `roundtrip`, `ftt_pom_layer`). Dependència `ezdxf==1.4.4` (`requirements.txt:48`). Fitxers DXF/RUL reals a
  `media/fhort/pattern_files/` (fixtures AMELIA, TATE).
- **Endpoints/ganxos DXF-RUL:** `patterns/urls.py:15` `PatternFileViewSet` + `pattern-poms`, `pattern-segments`,
  `sew-relations`, `sew-proposal-rejections`, `sew-tolerance-acceptances`. `create` (`patterns/views.py:296-355`):
  upload `fitxer_dxf` (obligatori) + `fitxer_rul` (opcional), `AAMAReader().read()` (`:325`), `RULReader().read()`
  (`:335`), `coherencia_dxf_rul` (`:343`). Descàrrega signada (`:286`, `:243`).
- **El node graduat ARRIBA al motor de patrons:** acció `export` (`patterns/views.py:42` importa `build_export`
  de `export.py`; `export.py:61` importa `engine.grading_projection`). `grading_projection.py:156` connecta
  GradedSpec (via port `GradingSource`) + POMs ancorats → `GradeRuleData` del CAD aplicant el DELTA (`:19`, `:441`).
  Port lector de `GradedSpec`: `patterns/adapters.py:432` (`:460-479`).

> **Tercera destinació del node graduat:** `GradedSpec → adapters.py (port) → grading_projection.py →
> export.py (build_export) → PatternFileViewSet.export`. A més d'Escalat (§5.3) i TechSheet (§5.4).

**DISSENYAT-EN-DOCUMENT (no confirmat com a producte):** `MOTOR_DE_PATRONS_V2.md` i
`PLA_IMPLEMENTACIO_MOTOR_PATRONS.md` (arrel) descriuen el disseny; la memòria (S0/S1, taller W2..W4b) marca
fets però "build verd ≠ producte verd". No barrejat amb el codi viu llistat a dalt.

### OBERT/DUBTÓS — BLOC 5

1. **§5.1:** dins el tram llegit, `update_model_step2` re-materialitza `if model.grading_rule_set_id` però
   **no assigna explícitament** `model.grading_rule_set_id` des de `request.data`; ha de venir de
   `_resolve_garment_def(d)` (`views.py:604`). Cal confirmar que aquest resolutor pobla el FK del ruleset.
2. **§5.2:** l'esglaó "exception" del brief D-10 **ja no existeix** (jubilat G6/1a) → codi = 3 esglaons.
3. **§5.2:** "3 punts de crida" (D-10) = 3 endpoints d'usuari, però **hi ha 5 cridadors runtime addicionals** → D-10 desactualitzat si diu "només 3".
4. **§5.4:** el TechSheet fa `fetch` directe amb `authHeaders` a `graded-table/` (`TechSheetEditor.jsx:2114`), fora del client axios comú — segona via d'auth a vigilar (no forat).

**Veredicte BLOC 5:** el node graduat està **complet de punta a punta** i té **tres destinacions vives** que
beuen de la taula `GradedSpec`: Escalat (mode model), TechSheet/PDF (snapshot `graded-table`) i **Motor de
Patrons (`export` → `grading_projection`)**. El motor de patrons NO és només disseny: està cablejat i llegeix GradedSpec.

---

## BLOC 6 — Ingesta del POP pel wizard

> El "wizard de 5 passos" real és **`ImportWizard`** (fitxa de model): front
> `frontend/src/components/ImportWizard/ImportWizard.jsx`, backend `models_app/extraction_views.py`.
> **NO** és el `SizeMapSetup` (`pom/size_map_views.py`, wizard de runs de client) — camí paral·lel que
> comparteix `detect_grading`/`derive_grading_rule_set`.

### 6.1 Pot ingerir el SIZE SET amb 2 columnes de grading (=break)?

**EXTRACTION_PROMPT** (`models_app/extraction_service.py:15`; bessó de fitxa `extraction_prompt.py:86`):
el contracte de grading és **un valor absolut per talla** — `extraction_service.py:52-53`:
`"grading_table":[{"code":"B","values_by_size":{"S":22.5,"M":23.5}}]`. **⚠️ No hi ha CAP concepte de "dues
columnes de grading" ni de "break" al prompt.** La forma nativa del Pop Spec (base + 2 columnes d'increment)
**no té ranura pròpia**: o el LLM la reconstrueix a absoluts-per-talla, o es perd. No hi ha fallback explícit per a 2 columnes.

**detect_grading** (`pom/grading_utils.py:119`): opera sobre **absoluts per talla**; calcula deltes veí-a-veí
(`:151-168`), classifica per nombre de canvis de pas `nb` (`:176-191`): `nb==0`→LINEAR; **`nb==1`→'LINEAR' amb
break** (`:186-189`); `nb>=2`→STEP. El break el materialitza `derive_break_fields` (`:201`) →
`increment_base/increment_break/talla_break_label/talla_break_pos`, escrit a `GradingRule` a `:384-397`.

> **La representació INTERNA del break existeix i és robusta** (un sol break = LINEAR-amb-break), **PERÒ
> només si l'entrada ja són absoluts-per-talla** que el codifiquen. El risc viu **a l'entrada** (que
> l'extracció produeixi els absoluts correctes des de 2 columnes), no al detector.

**W1 (gating del run XXS-XS-S-M-L)** — `import_session_talles_view` (`extraction_views.py:606`). Gating
(`:653-659`): una talla té "destí" si la forma **canònica** (`canonical_size_label`, XXL≡2XL) coincideix amb
el run del model, amb una talla del `size_system`, o amb mapeig manual; `ready = bool(talles_sel) and not
sense_desti` (`:659`). El run XXS-L **passaria** si el model ja té aquest run o un `size_system` amb aquestes
talles; si no, `accio='alinear'` (`:641-644`) fa que el document adopti el run. Si alguna talla queda
`sense_desti` → bloqueja (PENDENT) i ofereix `size_map_prefill` (`:676-689`). **No hi ha rebuig per longitud** (5 talles); el gating és per cobertura d'etiquetes.

**W3 (toggle absoluts/deltes)** — front `ImportWizard.jsx:109` (`valorsMode`, default `'absoluts'`, botons
`:774-781`, pre-selecció `data.suggested_valors_mode` `:221-222`); backend `import_session_mesures_view`
(`extraction_views.py:1501`, desa `valors_mode` si `∈{absoluts,deltes}` `:1531-1535`); suggeriment
`suggest_valors_mode` (`grading_utils.py:404`). El cas ABSOLUTS per talla està **cobert i és el default**.
El mode `deltes` = base absoluta + deltes; a W5 es converteixen amb `deltes_a_absoluts` (`extraction_views.py:1735-1745`).

> **⚠️ DUBTÓS per al Pop Spec:** el toggle és binari (absoluts XOR deltes) per a TOTA la taula. La forma
> "base + 2 columnes d'increment (break)" **no és cap dels dos modes purs**. El contracte de `deltes` diu
> explícitament (`grading_utils.py:412-418`) que "deltes PURS sense base absoluta NO es contemplen" i que una
> fitxa nova amb aquesta forma "és una peça NOVA, no un cas que aquest codi cobreixi". **Les 2 columnes de
> grading cauen fora del contracte del toggle.**

### 6.2 Norma "mana el document" (llei SOBIRANIA)

Handler de finalització: `import_session_confirmar_view` (`extraction_views.py:1645`, Pas W5). Docstring com a
norma inamovible (`:1651-1662`).

- **(a) BaseMeasurement només dels POMs del document:** neteja files buides i crea NOMÉS els confirmats amb
  `base_value_cm` = valor de la talla base (`:1780-1815`, `update_or_create` `:1806`). CONFORME.
- **(b) ModelGradingRule (deltes+breaks):** `derive_grading_rule_set` (`:1852-1866`) +
  `materialize_model_grading_rules(model, ..., origen='IMPORTED')` (`:1889`). `services.py:147` copia
  `increment_base/increment_break/talla_break_label/talla_break_pos` → **els breaks es retenen**. CONFORME.
- **NO GradingVersion / NO GradedSpec durant l'import:** al cos de `import_session_confirmar_view` no n'hi ha
  cap (només comentaris `:1653/1741/1826`). Es crea un `SizeFitting` **contenidor buit** (`:1936-1942`,
  `estat='Tancat'`, `n_specs=0` `:1943`); resposta `graded_specs:0` (`:1988`), "grading propagat pendent de
  projecció conscient" (`:1998-1999`). **CONFORME a la llei SOBIRANIA.**

> **Cap violació de la llei SOBIRANIA al codi de finalització.** L'import reté base + deltes + breaks i NO
> materialitza versió ni specs graduades.

### OBERT/DUBTÓS — BLOC 6

1. **⚠️ Forat d'entrada per al Pop Spec (2 columnes de grading):** el pipeline intern
   (detect_grading→derive_break_fields→ModelGradingRule) representa correctament UN break, però **cap camí
   d'ingesta llegeix "dues columnes de grading" com a tals**. Depèn que el LLM (`extraction_service.py:52`)
   endevini i converteixi a `values_by_size` absoluts. El prompt no ho instrueix; el parser determinista
   (`extraction_views.py:237-386`) mapeja columnes per **etiqueta de talla** → dues columnes retolades com a
   increments NO són talles → no entren com a valor. **Alt risc que el break del Pop Spec es perdi o s'interpreti malament a l'extracció.**
2. **El toggle W3 no té estat per a "base + 2 increments"** (absoluts XOR deltes globals). El propi codi la
   declara "peça NOVA no coberta" (`grading_utils.py:412-418`). Cal decisió de producte (Patró C).
3. **DUBTÓS positiu:** si el tècnic converteix manualment les 2 columnes a absoluts-per-talla (mode
   `absoluts`) i XXS-L té UN canvi de pendent, `detect_grading` recupera el break automàticament
   (`grading_utils.py:186-189`) i queda ben desat. El sistema **pot** ingerir el break — però només si l'entrada arriba com a absoluts-per-talla ben formats, cosa que avui l'extracció automàtica no garanteix.

**Veredicte BLOC 6:** la persistència (llei SOBIRANIA) és **neta**: l'import reté base+deltes+breaks sense
materialitzar versió/specs. El **forat és d'INGESTA de la forma de 2 columnes** (no de persistència): ni el
prompt ni el toggle W3 modelen "base + 2 increments"; el break del POP depèn que algú (LLM o tècnic) el
converteixi a absoluts-per-talla abans que `detect_grading` el pugui recuperar.

---

## TAULA FINAL — EXISTEIX / FALTA / DIFERENT (per al CTO)

| Node | Estat | Detall | Referència |
|---|---|---|---|
| Diccionari Brownie pujat | **EXISTEIX** | 92 àlies (`pom_customerpomalias.client_code`); 86 DICCIONARI | `pom/models.py:236`, `dictionary_views.py:163` |
| Cobertura spec POP | **EXISTEIX (36/43)** | 7 forats = els esperats `[D1,M1,M2,I4,J4,I1,L1]` | BLOC 1.3 |
| Matching per descripció d'àlies | **DIFERENT (docstring menteix)** | només casa per `client_code`, mai per `description_en/local` | `pom/models.py:266-269` vs `extraction_views.py:770-819` |
| TAPETA ANCHO (codi U) | **FALTA (perdut)** | col·lisió last-wins amb CRUCE DELANTE, sense traça | BLOC 1.4 |
| B4/B6 (ARRIBA/ABAJO) | **FALTA** | 0 files; mai van entrar | BLOC 1.4 |
| Customer Brownie | **EXISTEIX** | id=7, codi BRW, 38 models | `tasks/models.py:194` |
| Model "POP" | **NO EXISTEIX** | 0 files a tota la taula; "POP" = nom del document | BLOC 2.2 |
| Blusas Brownie amb grading | **FALTA** | 10 blusas gti=5, totes `grading_rule_set=NULL` | BLOC 2.1 |
| Run XXS-XS-S-M-L exacte | **DIFERENT** | només superconjunt ss=29 (XXS…3XL); matching 1.0, base S ok | `pom/models.py:292`, `matching.py:92` |
| Item blusa (gti=5) complet | **DIFERENT (a mitges)** | 37 GarmentPOMMap sí; ruleset/base/ItemBaseMeasurement (=0) no | `tasks/models.py:286`, `pom/models.py:468` |
| Camí net GradingRuleSet de client | **EXISTEIX (només wizard size-map)** | únic que fixa `ORIGEN_CLIENT_RUN`+`customer` | `pom/size_map_views.py:816` |
| `origen`/`customer` via CRUD/UI | **FALTA** | no a `Meta.fields`; neix NULL/NULL | `pom/serializers.py:203-213`, `GradingRuleSets.jsx` |
| Precedència motor resident vs set | **EXISTEIX (determinista, per-set)** | resident guanya; set fallback; assignar re-materialitza residents | `pom/services.py:539-563`, `views.py:616-621` |
| GradingException | **NO EXISTEIX (jubilada)** | taula eliminada `0038`; única excepció viva = ModelGradingOverride (0 files) | `pom/migrations/0038_*`, `models_app/models.py:651` |
| Guard de segellat | **EXISTEIX** | `sealed_active_version`+`SealedGradingVersionError`; `allow_reopen_sealed` per HTTP | `pom/services.py:86-97,595-630` |
| GradedSpec → Escalat | **EXISTEIX** | mode model, `taula-mesures` → buildEscalatRows | `models_app/views.py:807`, `fittingGridAdapter.jsx:120` |
| GradedSpec → TechSheet/PDF | **EXISTEIX** | via snapshot `graded-table` (porta paral·lela) | `fitting/graded_spec_views.py:22`, `TechSheetEditor.jsx:2114` |
| GradedSpec → Motor de Patrons | **EXISTEIX (cablejat)** | `export`→`grading_projection.py:156`, port `adapters.py:432` | `patterns/views.py:42` |
| Import respecta SOBIRANIA | **EXISTEIX (conforme)** | reté base+deltes+breaks; no materialitza versió/specs | `extraction_views.py:1645,1936-1943` |
| Ingesta POP "2 columnes de grading" | **FALTA (forat d'entrada)** | ni prompt ni toggle W3 modelen "base + 2 increments" | `extraction_service.py:52`, `grading_utils.py:412-418` |
| D-10 "override→exception→regla→FIXED" | **DIFERENT (3 esglaons)** | exception jubilada; override porta l'etiqueta EXCEPTION | `pom/services.py:183-198` |
| D-10 "3 punts de crida" | **DIFERENT** | 3 d'usuari + 5 cridadors runtime addicionals | BLOC 5.2 |

---

## DECISIONS PER PATRÓ C (per a l'Agus / disseny)

> Fets sense proposta d'implementació. Cada decisió és humana.

- **D-1 · Esborrar-repujar models Brownie sí o no.** Cens: 38 models BRW, 10 blusas amb mesures parcials i
  `grading_rule_set=NULL`, golden = **163 Blusa TATE**. Cap es diu POP. Decidir si es netegen i es reimporten
  amb el diccionari nou, o si es treballa sobre el 163 existent com a primer node. (BLOC 2)

- **D-2 · On viuen els àlies nous i com resoldre les pèrdues de col·lisió.** Confirmar amb la **Montse**:
  (a) el codi **U** → TAPETA ANCHO va desaparèixer sota CRUCE DELANTE; cal un segon codi per a TAPETA ANCHO?
  (b) **B4/B6** (ARRIBA/ABAJO) mai van entrar — el diccionari original els contenia? Decidir si el loader ha
  de detectar col·lisions en comptes de fer last-wins silenciós. (BLOC 1.4)

- **D-3 · Run XXS-L acotat vs superconjunt ss=29 amb break.** No existeix run XXS-L exacte; ss=29 arriba a
  3XL. El matching el resol 1.0 igualment. Decidir si es crea un run acotat per a la blusa POP o es gradua
  sobre ss=29 amb la talla break dins el run del model. (BLOC 3.1)

- **D-4 · ½ amplades vs canònic.** _(PENDENT DE VERIFICAR — no cobert explícitament pels investigadors;_
  _es planteja perquè el brief el llista.)_ Cal decidir si els POMs d'amplada del spec POP són ½-amplada (mig
  contorn) o amplada canònica sencera abans de fixar els valors base — no s'ha trobat cap normalització
  ½↔sencer automàtica al camí d'import. **Requereix una micro-diagnosi o confirmació de la Montse.**

- **D-5 · GradingRuleSet vs ModelGradingRule quan coexisteixen.** El motor és determinista (resident guanya,
  **per-set**). Decidir: la primera GradingRuleSet real de Brownie s'assigna via **update-step2** (que la
  re-materialitza com a residents `origen='CANONICAL'`) o es crea pel **wizard size-map** (que la deixa com a
  ruleset de client `ORIGEN_CLIENT_RUN`+`customer`, actiu com a fallback només si el model no té residents)?
  Tenir present que un ruleset assignat a un model amb residents pròpies **no aporta res al càlcul** fins que
  es re-materialitza. (BLOC 4.3, 5.1)

- **D-6 · Ingesta del break de 2 columnes del POP.** Forat d'entrada: ni `EXTRACTION_PROMPT` ni el toggle W3
  modelen "base + 2 columnes d'increment". Decidir com el document expressa el break i com el wizard el recull
  (instruir el prompt? un tercer mode al toggle? conversió manual del tècnic a absoluts-per-talla?). La
  representació interna (LINEAR-amb-break) ja existeix i és robusta. (BLOC 6.1)

- **D-7 · Classificar les 25 GradingRuleSet `origen=NULL`.** Existeix `manage.py set_grading_origen`. Decidir
  quan córrer-lo (i el mapatge) perquè la llei PROVINENÇA (què viatja a tenant nou) sigui efectiva abans de
  crear la primera de client. (BLOC 4.1)

### Notes de deute anotades (fora d'scope, no tocar)

- Docstring de `CustomerPOMAlias` menteix sobre matching per descripció (`pom/models.py:266-269`).
- D-10 desactualitzat: la precedència són 3 esglaons (no 4) i hi ha 8 cridadors de `generate_graded_specs` (no 3).
- `update_model_step2` no assigna visiblement `grading_rule_set_id` des de `request.data` (ha de venir de `_resolve_garment_def`); confirmar (§5.1 OBERT).
- TechSheet fa `fetch` a `graded-table/` fora del client axios comú (segona via d'auth).

---

*Diagnosi Patró A tancada. Read-only respectat: cap escriptura fora d'aquest fitxer. Font de cada fet
ancorada a `fitxer:línia` o a `SELECT` real sobre staging (schema `fhort`, tenant id=2).*
