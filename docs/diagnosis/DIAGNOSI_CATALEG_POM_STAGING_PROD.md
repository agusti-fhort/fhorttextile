# DIAGNOSI — CENS DE CATÀLEG POM: STAGING vs PROD (bandera fhort/los per a Fase 2 de sembra)

Data: 2026-07-26 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging` branca `dev` · cap escriptura, cap migració.
Abast: resoldre COLD contra quin schema (`public`/`fhort`/`los`) viu el catàleg POM real de LOSAN i on
opera LOSAN, a STAGING i a PROD, per decidir contra quin schema ha de **resoldre** i **escriure** la Fase 2 de sembra.
Convenció: cada fet porta la seva font (schema.taula + entorn). Font PROD = dump diari replicat
`/srv/fhort-prod-backups/incoming/fhort_textile_20260726_023001.dump` (02:30, pg_restore v18, read-only, sense restaurar).
`0` = confirmat buit (comptat), no especulat.

---

## Resum executiu (les conclusions que desbloquegen la decisió)

1. **STAGING i PROD DIVERGEIXEN de ple en on viu LOSAN.** A **PROD**, LOSAN opera al seu propi schema
   `los` (**961 models**, catàleg POM propi de **262 masters / 261 globals / 212 àlies**, mesures que creixen).
   A **STAGING**, `los` és una **closca parcial** (51 models, **0 catàleg POM, 0 mesures**); el catàleg + models
   de LOSAN encara viuen a `fhort` (l'estudi, Customer LOS pk=6). **Staging va endarrerit respecte a PROD en la federació.**
2. **La identitat dels schemas és la mateixa als dos entorns** (confirmada COLD a `public.tenants_client`):
   `public`=tenant 1 (FHORT System, compartit) · `fhort`=tenant 2 (FHORT Management, **estudi**, multi-client) ·
   `los`=tenant 13 (LOSAN, **marca**, alta 19/07). LOSAN existeix **dues vegades**: com a **Customer** dins l'estudi
   (`fhort.tasks_customer` codi=LOS, is_self=f) i com a **tenant propi** (`los`, on LOSAN és is_self=**t**).
3. **El catàleg VIU amb dades que l'informe de sembra F1 va trobar (368/229) és el de `fhort` de STAGING** — perquè
   staging `los` és buit. **Aquest 368/229 és un artefacte de staging, no la realitat de PROD.** A PROD el catàleg
   operatiu de LOSAN és el de `los` (262/212).
4. **`los` NO és el mateix catàleg que `fhort`-LOS.** A PROD, resoldre contra `los` (318 codis normalitzats
   resolubles) en lloc de `fhort`-LOS (413) **perd ~97 codis** (molts són codis d'altres clients de l'estudi, però
   n'hi ha de rellevants per LOSAN). → **El cens 98,5% net / 43 òrfes de la F1 és un número de `fhort`-staging i
   NO és vàlid per a `los`-PROD.**
5. **DECISIÓ (secció final):** a PROD la sembra ha de **resoldre contra `los` i escriure els POMPlacement a `los`**
   (on són els 961 models i el catàleg propi). A STAGING no es pot provar la Fase 2 fidelment fins que la federació
   pobli `los` (catàleg + rulesets); mentrestant, provar contra `fhort` (Customer LOS pk=6) és un **proxy**, no el destí.

---

## BLOC 1 — Identitat dels schemas (COLD, `public.tenants_client` + `tenants_domain`)

Font: staging `public.tenants_client` (query directa). Idèntica estructura a PROD (dump TOC: SCHEMA fhort, los, public).

| schema | tenant id | nom | codi_tenant | tipologia | estat | domini primari |
|---|---|---|---|---|---|---|
| `public` | 1 | FHORT System | SYS | estudi | actiu | localhost / backoffice |
| `fhort` | 2 | FHORT Management | FTT | estudi | actiu | fhorttextile.tech / staging |
| `los` | 13 | **LOSAN** | LOS | **marca** | **onboarding** (alta 2026-07-19) | los.fhorttextile.tech |

- **`fhort` = l'ESTUDI.** `fhort.tasks_customer` (PROD): FTT (is_self=**t**), + clients VYT (Vytex), **LOS (LOSAN IBERIA SA, pk=6, is_self=f)**, BRW (Brownie), SAR (Sanruiz). Staging: 3 clients (FTT, LOS pk=6, VYT).
- **`los` = la MARCA.** `los.tasks_customer` (PROD i staging): **una sola fila** codi=LOS, **is_self=t**, pk=1 — LOSAN com a client de si mateixa (mateix patró que FTT dins `fhort`).
- ⇒ LOSAN viu **dues vegades**: com a Customer de l'estudi (`fhort`, pk=6) i com a tenant propi (`los`, self pk=1). Són schemas i abstraccions diferents.

**Veredicte BLOC 1:** identitat confirmada i estable als dos entorns. `los` és la marca amb schema propi des del 19/07; `fhort` és l'estudi que la té com a client. **La bandera «per què el catàleg és a fhort» = perquè el va CONSTRUIR l'estudi per al seu client LOS; el traspàs a la marca és una fase de federació posterior.**

---

## BLOC 2 — Cens de catàleg POM per schema i entorn

Font STAGING: `count(*)` directe per schema. Font PROD: recompte de files COPY del dump 2026-07-26 (pg_restore -a per schema/taula).

| taula | STA `public` | STA `fhort` | STA `los` | PROD `public` | PROD `fhort` | PROD `los` |
|---|---|---|---|---|---|---|
| pom_pommaster | 0 | **368** | **0** | 0 | **423** | **262** |
| pom_pomglobal | 125 | 274 | 0 | 125 | 290 | 261 |
| pom_customerpomalias | 0 | **325** (LOS=229) | **0** | 0 | **289** (LOS cust6=183) | **212** (self) |
| pom_pomcategory | 15 | 28 | 0 | — | — | — |

- **On viu el catàleg REAL de LOSAN amb dades:** a **STAGING → `fhort`** (368/229); a **PROD → tots dos**, però l'operatiu de la marca és **`los`** (262/212). Staging `los` = **buit de catàleg** (0/0/0).
- `pom_pomglobal` existeix a `public` (125, plantilla/canònic compartit) i es materialitza per tenant (fhort 274/290, los PROD 261).

**Veredicte BLOC 2:** el 368/229 que la F1 va resoldre **és el `fhort` de staging**. A PROD el catàleg de la marca és `los` (262/212), no idèntic al de `fhort`.

---

## BLOC 3 — On OPERA LOSAN (models, mesures, rulesets)

Font: STAGING `count(*)`; PROD dump 2026-07-26 (files COPY).

| taula | STA `fhort` | STA `los` | PROD `fhort` | PROD `los` |
|---|---|---|---|---|
| models_app_model | 1056 | **51** | **52** | **961** |
| models_app_basemeasurement | 647 | 0 | 313 | **46** |
| pom_gradingruleset | 46 | 0 | 47 | 20 |

- **PROD: LOSAN opera a `los`** — **961 models** (sembra SS27, command idempotent), catàleg propi, i **46 basemeasurements que creixen** (coherent amb «les 37 mesures + shirt_woven del deploy d'avui a `los` de PROD»). `fhort` de PROD ha quedat amb 52 models (l'estudi i altres clients): **els models de LOSAN es van moure/sembrar cap a `los`.**
- **STAGING: LOSAN encara opera a `fhort`** — 1056 models (inclou LOS); `los` només té 51 models de prova i **cap catàleg ni mesura**. El traspàs de federació NO s'ha fet complet a staging.
- Coincideixen schema d'operació i schema de catàleg? **PROD: SÍ** (operació i catàleg tots dos a `los`). **STAGING: NO** (operació i catàleg tots dos a `fhort`, i `los` és una closca).

**Veredicte BLOC 3:** a PROD, operació + catàleg de LOSAN conviuen a `los`. A staging conviuen a `fhort`. Cap entorn té la divergència operació↔catàleg *dins seu*; la divergència és **entre entorns**.

---

## BLOC 4 — `los` ≠ `fhort`-LOS: quant es perd resolent contra `los` (PROD)

Font: dump PROD 2026-07-26. Codis normalitzats (casefold + treure puntuació, com el resolver de F1).
`B` = resoluble contra `fhort` (àlies customer LOS=6 ∪ tot el master de l'estudi). `A` = resoluble contra `los` (àlies self ∪ master de `los`).

- **|B| (fhort-LOS) = 413** codis · **|A| (los) = 318** codis.
- **En fhort-LOS però NO a `los`: 97 codis.** Molts són d'altres clients/peces de l'estudi (BELTHS, BIBH, KANGW, VISORL, THUMB, STRAPW…), però n'hi ha de plausiblement LOSAN (`H11`, `SR8`, `B9`, `V1`, `G`, `G1`, `G3`, `E6`, `SR11`…), alguns coincidents amb la llista d'ÒRFES de la F1.
- **A `los` però NO a fhort-LOS: només 2** (`GL`, `H12`).

⇒ `los` és essencialment un **subconjunt** de `fhort`-LOS. Resoldre la sembra contra `los` (el destí correcte a PROD) **produirà MÉS òrfes** que el 43 mesurat contra `fhort`-staging.

**Veredicte BLOC 4:** el cens de resolució de la F1 (98,5% net · 43 òrfes) **és específic de `fhort`-staging i no és transferible a `los`-PROD**. Cal **re-córrer el cens contra el schema destí real** abans d'escriure res.

---

## TAULA FINAL — EXISTEIX / FALTA / DIFERENT (per al CTO)

| Pregunta | STAGING | PROD |
|---|---|---|
| Schema on OPERA LOSAN (models) | `fhort` (los = 51 de prova) | **`los`** (961 models) |
| Schema del CATÀLEG POM de LOSAN | `fhort` (368/229) | **`los`** (262/212) — i còpia estudi a `fhort` (423) |
| `los` utilitzable per a Fase 2? | **NO** (0 catàleg, 0 mesures) | **SÍ** (catàleg + 961 models + mesures) |
| Customer de resolució | `fhort`.Customer LOS **pk=6** (is_self=f) | `los`.Customer LOS **pk=1** (is_self=t) |
| Cens F1 (98,5%/43 òrfes) vàlid aquí? | sí, però és número de `fhort` | **NO** — cal re-córrer contra `los` (−97 codis vs fhort) |
| Divergència operació↔catàleg dins l'entorn | no (tots dos a `fhort`) | no (tots dos a `los`) |

---

## DECISIÓ PER A FASE 2

**FET (no és proposta):**
- A **PROD**, el destí correcte de la sembra és **`los`**: resoldre els codis contra el catàleg de `los`
  (àlies del self-customer LOS **pk=1** → POMMaster de `los`, mateix camí F1) i **escriure els POMPlacement a `los`**,
  lligats als **961 models** que hi viuen. Escriure a `fhort` seria escriure a l'estudi, no a la marca operativa.
- El cens 98,5%/43 òrfes de la F1 **és de `fhort`-staging** i **no descriu `los`-PROD** (−97 codis resolubles).

**💡 PROPOSTA (a validar per l'Agus — Patró C):**
1. **El command d'escriptura de Fase 2 ha de ser `--schema`-parametritzat** (com ja ho és `sembra_ai_report`), amb
   resolució explícita del Customer per schema: `fhort`→`codi=LOS` (pk=6, is_self=f) · `los`→self-customer (pk=1, is_self=t).
   Default operatiu a PROD = `los`.
2. **Re-córrer el cens de resolució (F1) contra el schema destí REAL abans d'escriure.** A PROD, córrer
   `sembra_ai_report --schema los` per obtenir el VERD/GROC/ÒRFE i el nombre real d'òrfes de `los` (previsiblement > 43).
   Aquest és el número que ha de prioritzar la neteja de la Montse per al destí real.
3. **Staging no pot validar la Fase 2 de forma fidel mentre `los` sigui una closca.** Dues vies (decisió humana):
   - (a) **Poblar staging `los`** amb la federació/traspàs de catàleg (com es va fer a PROD: load del paquet LOSAN +
     sembra de models) i llavors provar `--schema los` — validació fidel al destí PROD.
   - (b) Provar `--schema fhort` (Customer LOS pk=6) com a **proxy** a staging, sabent que NO és el schema destí i que
     els números (òrfes, lligams) diferiran dels de `los`-PROD.
   La via (a) és l'única que valida el camí que farà servir l'usuari a PROD (llei de mètode: verificar contra EL CAMÍ REAL).
4. **Watchpoint federació:** que PROD tingui `los` poblat i staging no, vol dir que **staging no és una fotografia
   fidel de PROD per a LOSAN**. Qualsevol prova de sembra a staging contra `fhort` mesura un catàleg (368/229) que a
   PROD ja no és l'operatiu de la marca. Vegeu la cadena de federació v2 (P1/P2/P7/P8) i el traspàs de catàleg.

---
*Patró A · READ-ONLY · cap codi tocat, cap BD escrita, cap dump restaurat. Fonts: staging live (read-only) + dump PROD 2026-07-26 02:30 via pg_restore v18.*
