# Cens de `MEMORY.md` — poda proposada

**Data:** 2026-08-25 · Patró A + proposta · **manteniment d'infraestructura de sessions**
**Proposta de fitxer podat:** `MEMORY_PROPOSTA_2026-08-25.md`

> **Read-only absolut.** `MEMORY.md` **no s'ha tocat**: la poda es PROPOSA, no s'aplica.
> Cap escriptura al repo, cap a la BD (només `SELECT`), cap servei, cap `systemctl`.
> Els dos lliurables es deixen **sense commitar**, com els informes d'aquest fil.
> L'apply és un gest d'Agus: validar §4 → substituir → les sessions carreguen sencer.

---

## 0 · El resum en sis línies

1. **`MEMORY.md` fa 31 210 B; el límit de càrrega són 24,4 KiB (24 986 B).** El tall cau a
   la **línia 134**: **6 224 B (19,9 %) no es carreguen mai**.
2. 🚨 **El que cau fora inclou SET seccions senceres**, i entre elles la titulada
   **«Mètode i infra (llegir abans de tocar res)»** i **«Motor de patrons / taller»** —
   el tema d'aquest fil sencer. **La secció que diu «llegir abans de tocar res» no es
   llegeix mai.**
3. **La causa és una sola secció.** «Sessions recents» té **81 entrades i 18 817 B: el
   60,3 % del fitxer** — i és precisament la que la regla pròpia del fitxer (línia 3,
   *«El ganxo, no el contingut»*) diu que ha de ser més curta.
4. Cens complet: **145 entrades** → **21 LLEI · 34 FET-V · 3 FET-X · 87 CRÒNICA**.
   LLEI + FET-V = **10 748 B (34,5 %)**: tot el que val cap de sobres al pressupost.
5. **La proposta fa 13,1 KB** (sense la capçalera), un **58 % menys**, i queda al **54 %
   del límit** — marge per créixer mesos. **Zero punters trencats** (105 verificats).
6. **Cap fitxer de memòria no s'esborra.** 95 perden el punter d'índex; segueixen a
   `memory/` i segueixen sent recuperables per la seva `description`. §4.3.

---

## 1 · El problema, mesurat

| | valor |
|---|---:|
| mida actual | **31 210 B** |
| límit de càrrega | 24,4 KiB = **24 986 B** |
| **no es carrega** | **6 224 B · 19,9 % · 44 línies** |
| el tall cau a | **línia 134** |
| entrades totals | **145** |

### 1.1 Mida per secció — la causa és una sola

| secció | entrades | bytes | % |
|---|---:|---:|---:|
| **Sessions recents · 04→17/08** | **81** | **18 817** | **60,3 %** |
| 🚨 LLEIS | 19 | 3 603 | 11,5 % |
| Sprints i diagnosis 28/07 i anteriors | 8 | 1 930 | 6,2 % |
| C4 i el tram de la germana | 12 | 1 240 | 4,0 % |
| Mètode i infra | 4 | 827 | 2,6 % |
| Federació / multi-tenant / LOSAN | 4 | 801 | 2,6 % |
| Grading, talles i mesures | 3 | 779 | 2,5 % |
| Comercial, plataforma i planificació | 3 | 635 | 2,0 % |
| Altres projectes | 3 | 579 | 1,9 % |
| Sprints oberts 30-31/07 | 5 | 553 | 1,8 % |
| Editor de fitxa (.ftt) | 2 | 365 | 1,2 % |
| Motor de patrons / taller | 1 | 258 | 0,8 % |

Les entrades de sessió han crescut fins a **970, 814, 560 caràcters** (línies 44, 45, 46):
ja no són ganxos, són actes. **Cadascuna té el seu fitxer propi**, on el detall ja hi és.

---

## 2 · 🚨 Verificació del tall: què queda fora ARA MATEIX

**Set seccions senceres** comencen dins del tros perdut i, per tant, **no es carreguen mai**:

| línia | secció perduda sencera | per què fa mal |
|---:|---|---|
| 143 | Federació / multi-tenant / LOSAN | l'únic lloc on consta que **el Model no és particionable** |
| 149 | Grading, talles i mesures | `talla_mapping` és llei; paritat fitting↔grading |
| 154 | **Motor de patrons / taller** | **AMELIA = PolyPattern**, llindar 22°, màscara de piquets — el tema d'aquest fil |
| 157 | Editor de fitxa (.ftt) | la fitxa **no és reportlab** |
| 161 | Comercial, plataforma i planificació | B5 pendent; 2 accions de deploy |
| 166 | **Mètode i infra (llegir abans de tocar res)** | 🚨 **el JWT de QA bloquejat, els ports, el Host del tenant, on van les diagnosis** |
| 172 | Altres projectes | webiafy, web, `frappe-cleanup` pendent |

I **27 entrades**, entre les quals aquestes, que són cost real i **la poda ha de salvar**:

- **L.134 · PENDENTS D'INFRA** — `pip install` de la dep HEIC en desplegar · cron capa 2
  del JWT · cron del guard de tasca oblidada. **Tres coses sense instal·lar que ningú no
  veu.** És el contingut més valuós del tros perdut.
- **L.135** — 4 taules T1b congelades (163, 166, 177, 195).
- **L.145** — 🚩 `los` sense POMMaster *(confirmat avui per SQL: 0)*.
- **L.167** — 🚩 l'agent no pot emetre el JWT de QA; el `goto` directe captura el 401 d'nginx.
- **L.169** — ports, `pg_restore`, tenants, i el **Host del tenant** (sense el qual tot dona 404).

> **La ironia que ho resumeix:** la línia 9 —la llei que aquesta setmana ha costat una
> diagnosi errònia sencera— es carrega perquè és a dalt. La secció **«llegir abans de
> tocar res»** no es carrega perquè és a baix. **L'ordre del fitxer decideix què se sap.**

---

## 3 · Cens complet — 145 entrades, cap omissió

**Classes:** `LLEI` regla viva d'aplicació general · `FET-V` fet vigent i verificable ·
`FET-X` caducat/fals/superat · `CRÒNICA` narració que ja viu al fitxer del tema ·
`DUPLICAT` repetició.
🔻 = **cau fora del tall de càrrega actual**.

| classe | entrades | bytes | % del fitxer |
|---|---:|---:|---:|
| **CRÒNICA** | **87** | **19 324** | **61,9 %** |
| FET-V | 34 | 6 823 | 21,9 % |
| LLEI | 21 | 3 925 | 12,6 % |
| FET-X | 3 | 315 | 1,0 % |
| DUPLICAT | 0 | 0 | — |

### 3.1 Els 3 FET-X, verificats avui per SQL

| línia | deia | mesura del 25/08 | veredicte |
|---:|---|---|---|
| 47 | «`ExportAcknowledgement`=0: **el motor no ha exportat MAI**» i `PatternPOM`=3 | `fhort`: ExportAck = **2**, PatternPOM = **21** | 🚨 **FALS avui.** El motor **sí** que ha exportat |
| 77 | «**142** POMMaster canònics» | `fhort.pom_pommaster` = **144** | caducat — guanya la l.40, que ja deia 144 |
| 116 | «🟢 **1 449 tests** · `test fhort` = 12 apps» | — | foto d'un dia; el recompte creix a cada tram |
| 120 | «dany viu (**185**, **182**)» | cap dels dos models existeix a `fhort` | resolt o era PROD |
| 46 | «banc `QA-TRAMF-0001` **pk 1384**» | 1384 **no existeix**; 1383 **sí** | el banc F ja no hi és |

*(Les línies 116/120/46 són CRÒNICA que conté un FET-X; es compten a CRÒNICA.)*

### 3.2 Dubtes marcats — conservats com a FET-V per prudència

| línia | dubte | tractament |
|---:|---|---|
| 144 | «962 models LOS viuen a `fhort`» — avui `fhort`=39 i `los`=51 | **conservat** amb la nota «a verificar» a la proposta |
| 152 | QA al 182 · model 185 resolt — **cap dels dos existeix a `fhort`** | conservat: probablement PROD, no staging |
| 113 | «35 models i 1.444 regles a **PROD**» | conservat: PROD no es pot mesurar des d'aquí |

> Llei inline aplicada: **davant del dubte, FET-V i marca el dubte.** La poda conservadora
> es corregeix; l'agressiva perd informació.

### 3.3 La taula, entrada per entrada

| # | mida | fil/origen | classe | entrada (retallada) | motiu / rastre |
|---:|---:|---|---|---|---|
| 9 | 256 | `ftt-bd-staging-com-sinterroga` | **LLEI** | 🚨 ftt-bd-staging-com-sinterroga — **la BD viva és `postgresql@18-main` al port 5433**: la uni… |  |
| 10 | 216 | `ftt-verd-proporcional` | **LLEI** | 🚨 ftt-verd-proporcional — **el gate d'un tram és PROPORCIONAL**: check + build + NOMÉS l'app … |  |
| 11 | 260 | `ftt-consulta-no-es-mostra-fixtures` | **LLEI** | 🚨 ftt-consulta-no-es-mostra-fixtures — **des de J/R2 una fixture que obre i tanca una tasca s… |  |
| 12 | 183 | `ftt-backend-desplegat-vs-disc` | **LLEI** | ftt-backend-desplegat-vs-disc — **el gunicorn serveix el codi de quan va arrencar**: 404 amb … |  |
| 13 | 159 | `ftt-traduccio-domini-no-va-a-bd` | **LLEI** | 🔒 ftt-traduccio-domini-no-va-a-bd — **la traducció de domini NO viu a la BD** (VIGENT); ✅ ja … | invariant d'arquitectura; el «ja CONSTRUIDA 13/08» es cronica -> retallar |
| 14 | 139 | `ftt-dev-concurrent-git` | **LLEI** | ftt-dev-concurrent-git — sessions concurrents a `dev`; **MAI `git stash`**, `git add` de path… |  |
| 15 | 171 | `ftt-commit-sense-pathspec-endu-el-stage-alie` | **LLEI** | 🚨 ftt-commit-sense-pathspec-endu-el-stage-alie — **`git add` explícit NO n'hi ha prou**: l'ín… |  |
| 16 | 139 | `ftt-tram-t-n-cataleg-i-neteja` | **LLEI** | ftt-tram-t-n-cataleg-i-neteja — **staging serveix `frontend/dist`: `npm run build` ÉS despleg… |  |
| 17 | 193 | `ftt-migracions-es-commiten-en-aplicar-se` | **LLEI** | 🚨 ftt-migracions-es-commiten-en-aplicar-se — **una migració aplicada i no commitada és una di… |  |
| 18 | 151 | `ftt-suite-apt-mata-la-correguda` | **LLEI** | ftt-suite-apt-mata-la-correguda — **l'`unattended-upgrades` reinicia Postgres a ~06:39 UTC i … |  |
| 19 | 173 | `ftt-nom-local-que-repeteix-tapa-la-traduccio` | **LLEI** | 🚨 ftt-nom-local-que-repeteix-tapa-la-traduccio — **una ⓘ muda no vol dir «no hi ha dada»**; s… |  |
| 20 | 168 | `ftt-lectura-comercial-sense-gate` | **LLEI** | 🚨 ftt-lectura-comercial-sense-gate — ✅ CONSTRUÏT 14/08: el forat era **el PAYLOAD, no el menú… | la llei es «PODA i no 403»; el «CONSTRUIT 14/08» es cronica -> retallar |
| 21 | 140 | `ftt-fitxa-multipeca-ja-construida` | **FET-V** | 🚨 ftt-fitxa-multipeca-ja-construida — **la fitxa JA reparteix per peça** (falta la PÀGINA) | estat de construccio viu: la fitxa reparteix per peca, falta la PAGINA |
| 22 | 170 | `ftt-mesurar-impressio-i-no-login` | **LLEI** | ftt-mesurar-impressio-i-no-login — **un desbordament es MESURA amb Chromium headless**; una d… |  |
| 23 | 170 | `ftt-s2-fixes-s36-pell` | **LLEI** | 🚨 ftt-s2-fixes-s36-pell § FAMÍLIA DE TRES — **cada pantalla que entra al patró de peces s'hi … |  |
| 24 | 166 | `ftt-lectura-que-arma-escriptures` | **LLEI** | 🚨 ftt-lectura-que-arma-escriptures — **obrir una lectura ARMA les escriptures que ningú no as… |  |
| 25 | 255 | `ftt-acta-al-codi-pot-mentir` | **LLEI** | 🚨 ftt-acta-al-codi-pot-mentir — **una acta d'FTT diu què era veritat el dia que es va escriur… |  |
| 26 | 260 | `ftt-camp-nou-de-forma-vol-getattr` | **LLEI** | 🚨 ftt-camp-nou-de-forma-vol-getattr — **un camp nou de la REGLA vol `getattr` als tres lector… |  |
| 27 | 234 | `ftt-presa-segellada-indistingible` | **LLEI** | 🚨 ftt-presa-segellada-indistingible — **una presa TANCADA és indistingible d'una que no ha ex… |  |
| 30 | 217 | `ftt-fil-desplegat-tancat · 25/08` | **CRONICA** | ✅ ftt-fil-desplegat-tancat · 25/08 — **DESPLEGAT TANCAT** (8 peces, fix a l'import, 16 tests,… | fil TANCAT 25/08; salvar nomes: xor_model_item admet GTI + els 3 pendents de Patro C |
| 31 | 269 | `ftt-m5-retroactiu-r1-i-tren · 25/08` | **CRONICA** | 🚨 ftt-m5-retroactiu-r1-i-tren · 25/08 — ✅ **RETROACTIU R1 APLICAT: població pre-llei = 0** · … | salvar: `settings_test` amb FTT_TEST_DB (metode) |
| 32 | 328 | `ftt-m4-numeral-i-desbordament · 25/08` | **CRONICA** | 🚨 ftt-m4-numeral-i-desbordament · 25/08 — ✅ **M4: numeral a la COMANDA · desbordament marca l… | salvar: el symlink de node_modules DESTRUEIX el directori real (llei de worktrees) |
| 33 | 313 | `ftt-m3-cicle-vida-model · 24/08` | **CRONICA** | 🚨 ftt-m3-cicle-vida-model · 24/08 — ✅ **M3 + CODA: TRES ESTATS · TANCAR/REOBRIR/JUBILAR · la … | narracio de sessio; el detall ja viu al fitxer propi |
| 34 | 267 | `ftt-m2-cara-rondes · 24/08` | **CRONICA** | 🚨 ftt-m2-cara-rondes · 24/08 — ✅ **M2: PLA I REGISTRE PER RONDA** (7 commits) · 🚨 el brief do… | narracio de sessio; el detall ja viu al fitxer propi |
| 35 | 248 | `ftt-sembra-v5-dos-vocabularis · 23/08` | **CRONICA** | 🚨 ftt-sembra-v5-dos-vocabularis · 23/08 — ✅ **SEMBRA_V5 A+B** · 🚨 tenant i v5 usen les MATEIX… | narracio de sessio; el detall ja viu al fitxer propi |
| 36 | 167 | `ftt-cataleg-v5-forat-esquema · 23/08` | **FET-V** | 🚩 ftt-cataleg-v5-forat-esquema · 23/08 — **4 columnes del r2 sense camp a POMGlobal**: pre-tr… | PENDENT VIU: 4 columnes del r2 sense camp a POMGlobal, pre-tren d'Agus |
| 37 | 203 | `ftt-poms-tabs-actius-inactius · 23/08` | **CRONICA** | 🚨 ftt-poms-tabs-actius-inactius · 23/08 — ✅ **TABS a /poms** (6 commits) · 🔑 la pantalla ja e… | narracio de sessio; el detall ja viu al fitxer propi |
| 38 | 219 | `ftt-instancies-dos-eixos-posicio · 23/08` | **CRONICA** | 🚨 ftt-instancies-dos-eixos-posicio · 23/08 — ✅ **POSICIÓ AMB DOS SUB-EIXOS** (6 commits) · 🚨 … | narracio de sessio; el detall ja viu al fitxer propi |
| 39 | 216 | `ftt-tren-panys-sembres · 22/08` | **CRONICA** | 🚨 ftt-tren-panys-sembres · 22/08 — ✅ **TREN DE PANYS** (6 commits) · 🚨 el `fitxer:línia` del … | narracio de sessio; el detall ja viu al fitxer propi |
| 40 | 574 | `ftt-sobirania-pom-font-unica · 22/08` | **CRONICA** | 🚨 ftt-sobirania-pom-font-unica · 22/08 — ✅ **SOBIRANIA DEL POM** (9 commits, cap push) · 🚨 **… | salvar el fet: fhort te 144 POMMaster (mesurat avui: 144) -> guanya sobre la l.77 |
| 41 | 407 | `ftt-test-que-compara-amb-migracio-congelada · 22/08` | **CRONICA** | 🚨 ftt-test-que-compara-amb-migracio-congelada · 22/08 — ✅ **l'ÚNIC VERMELL DE LA NOCTURNA TAN… | narracio de sessio; el detall ja viu al fitxer propi |
| 42 | 506 | `ftt-escalat-subtab-vigent · 21/08` | **CRONICA** | 🚨 ftt-escalat-subtab-vigent · 21/08 — ✅ **SUB-PESTANYA «VIGENT»** (3 commits, cap push) · 🚨 *… | narracio de sessio; el detall ja viu al fitxer propi |
| 43 | 540 | `ftt-400-linear-zero-era-el-proces · 21/08` | **CRONICA** | 🚨 ftt-400-linear-zero-era-el-proces · 21/08 — ✅ **EL 400 DE LA F TANCAT** (3 commits, cap pus… | narracio de sessio; el detall ja viu al fitxer propi |
| 44 | 1025 | `ftt-f4quater-lectura-unificada · 21/08` | **CRONICA** | 🚨 ftt-f4quater-lectura-unificada · 21/08 — ✅ **F4-QUATER: UNA columna «Breaks», UN TRAM PER L… | salvar 2 pendents: taules Q8 congelades sense versio; fitxa a 2 mm de l'A4 |
| 45 | 866 | `ftt-interval-viu-en-espai-de-sistema · 21/08` | **CRONICA** | 🚨 ftt-interval-viu-en-espai-de-sistema · 21/08 — ✅ **F4-BIS: la columna «Breaks» amb xips** (… | narracio de sessio; el detall ja viu al fitxer propi |
| 46 | 596 | `ftt-ef-intervals-i-step-prestat · 21/08` | **CRONICA** | 🚨 ftt-ef-intervals-i-step-prestat · 21/08 — ✅ **TRAM E+F TANCAT** (7 commits, cap push) · 🔑 *… | conte FET-X: banc pk 1384 NO existeix a fhort (mesurat avui) |
| 47 | 501 | `ftt-dues-forces-construides-sense-us · 21/08` | **CRONICA** | 🚨 ftt-dues-forces-construides-sense-us · 21/08 — **DIMENSIONAMENT F1+F2**: totes dues CONSTRU… | conte DOS FET-X: ExportAcknowledgement=0 (ara 2) i PatternPOM=3 (ara 21) |
| 48 | 538 | `ftt-jbis-ftt-al-disc-i-transicio-guardada · 21/08` | **CRONICA** | 🚨 ftt-jbis-ftt-al-disc-i-transicio-guardada · 21/08 — ✅ **TRAM J-BIS TANCAT** (4 commits, cap… | narracio de sessio; el detall ja viu al fitxer propi |
| 49 | 557 | `ftt-j-consulta-no-es-treball · 21/08` | **CRONICA** | 🚨 ftt-j-consulta-no-es-treball · 21/08 — ✅ **TRAM J TANCAT** (5 commits, cap push) · 🚨 **un b… | narracio de sessio; el detall ja viu al fitxer propi |
| 50 | 412 | `ftt-hbis-columnes-identitat-fitxa · 21/08` | **CRONICA** | 🚨 ftt-hbis-columnes-identitat-fitxa · 21/08 — ✅ **H-bis TANCAT AL CODI** (4 commits, cap push… | salvar FET-V: cap fitxer del 1383 al disc (re-verificat avui: 0 fitxers) |
| 51 | 507 | `ftt-h-taula-base-fitxa · 21/08` | **CRONICA** | 🚨 ftt-h-taula-base-fitxa · 21/08 — ✅ **TRAM H TANCAT** (3 commits, cap push): la taula de mes… | narracio de sessio; el detall ja viu al fitxer propi |
| 52 | 587 | `ftt-fix-a-font-unica-regla · 21/08` | **CRONICA** | 🚨 ftt-fix-a-font-unica-regla · 21/08 — ✅ **FIX A** (11 commits, cap push): el camp llegat `in… | salvar FET-V: el banc 1383 ja no es el de la sembra |
| 53 | 471 | `ftt-pre-sprints-s45-diagnosi · 21/08` | **CRONICA** | 🚨 ftt-pre-sprints-s45-diagnosi · 21/08 — 🚨 el **fallback del llegat són DOS nodes** (`_apply_… | narracio de sessio; el detall ja viu al fitxer propi |
| 54 | 317 | `ftt-s45-bloc3d-gating-pickers · 21/08` | **CRONICA** | 🚨 ftt-s45-bloc3d-gating-pickers · 21/08 — ✅ **TRAM TANCAT** (8 commits, cap push) · 🔑 «mesura… | narracio de sessio; el detall ja viu al fitxer propi |
| 55 | 313 | `ftt-sembra-837-banc-s45 · 21/08` | **CRONICA** | 🚨 ftt-sembra-837-banc-s45 · 21/08 — ✅ **BANC S45 VIU: model pk=1383 a staging** · 🚨 un signal… | salvar FET-V: model pk=1383 VIU a staging (re-verificat avui) |
| 56 | 188 | `ftt-e3-tancada-i-mesurar-set · 17/08` | **CRONICA** | 🚨 ftt-e3-tancada-i-mesurar-set · 17/08 — ✅ **TRAM TANCAT** (6 commits): **crear és del GEST, … | narracio de sessio; el detall ja viu al fitxer propi |
| 57 | 254 | `ftt-q8-taules-fitxa-per-peca` | **CRONICA** | 🚨 ftt-q8-taules-fitxa-per-peca · 17→18/08 — ✅ **TRAM TANCAT** (24 commits, cap push) · 🚨 «exi… | narracio de sessio; el detall ja viu al fitxer propi |
| 58 | 174 | `ftt-e1-escalat-presa-dos-passos · 17/08` | **CRONICA** | 🚨 ftt-e1-escalat-presa-dos-passos · 17/08 — **«Mesurar prenda» NO és el Size Check**: és `fit… | narracio de sessio; el detall ja viu al fitxer propi |
| 59 | 128 | `ftt-s42-f1-escriptura-garment · 17/08` | **CRONICA** | 🚨 ftt-s42-f1-escriptura-garment · 17/08 — ✅ **TRAM TANCAT** (6 commits, cap push) | narracio de sessio; el detall ja viu al fitxer propi |
| 60 | 153 | `ftt-s42-q9-full-thead-i-geometria · 17/08` | **CRONICA** | 🚨 ftt-s42-q9-full-thead-i-geometria · 17/08 — **Chrome NO sap numerar pàgines** (x/N → pagina… | narracio de sessio; el detall ja viu al fitxer propi |
| 61 | 110 | `ftt-s42-q5q6-full-fitting · 16/08` | **CRONICA** | 🚨 ftt-s42-q5q6-full-fitting · 16/08 — ✅ F7 (`acfc3f24`, sense push) | narracio de sessio; el detall ja viu al fitxer propi |
| 62 | 167 | `ftt-s42-escalat-i-mesurar · 16/08` | **CRONICA** | 🚨 ftt-s42-escalat-i-mesurar · 16/08 — **una condició de revisió escrita en un docstring és fe… | narracio de sessio; el detall ja viu al fitxer propi |
| 63 | 177 | `ftt-import-no-esborra-i-nom-canonic · 16/08` | **CRONICA** | 🚨 ftt-import-no-esborra-i-nom-canonic · 16/08 — **«l'import esborra» era FALS i el `Measureme… | narracio de sessio; el detall ja viu al fitxer propi |
| 64 | 170 | `ftt-onada3-identitat-fila-import · 14/08` | **CRONICA** | ftt-onada3-identitat-fila-import · 14/08 — ✅ **TRAM TANCAT: la Brumà s'importa** (30·31·40 a … | narracio de sessio; el detall ja viu al fitxer propi |
| 65 | 117 | `ftt-familia-graella-import · 14/08` | **CRONICA** | ftt-familia-graella-import · 14/08 — Patró A: 5 parents i CAP comparteix codi | narracio de sessio; el detall ja viu al fitxer propi |
| 66 | 147 | `ftt-tram-i-traduccio-poms · 13/08` | **CRONICA** | ftt-tram-i-traduccio-poms · 13/08 — ✅ TRAM ⓘ: `/api/v1/translate/pom/` + `TranslationCache` a… | narracio de sessio; el detall ja viu al fitxer propi |
| 67 | 112 | `ftt-s2-fixes-s36-pell · 12/08` | **CRONICA** | ftt-s2-fixes-s36-pell · 12/08 — 🚨 «sense vora» era **la TARGETA de dins** | narracio de sessio; el detall ja viu al fitxer propi |
| 68 | 132 | `ftt-s2-t8-import-per-prenda · 12/08` | **CRONICA** | ftt-s2-t8-import-per-prenda · 12/08 — 🚨 **el confirm té poda PRÒPIA: la TERCERA porta** | narracio de sessio; el detall ja viu al fitxer propi |
| 69 | 166 | `ftt-s2-t7-b3b4-porta-peces` | **CRONICA** | ftt-s2-t7-b3b4-porta-peces · 11→12/08 — ☠️ **el wrapper de background mata a 10 min: una suit… | narracio de sessio; el detall ja viu al fitxer propi |
| 70 | 146 | `ftt-s2-blocb-logica-mesures · 10/08` | **CRONICA** | ftt-s2-blocb-logica-mesures · 10/08 — 🚨 **4 xifres de 7 eren bones per CASUALITAT DEL PLA DE … | narracio de sessio; el detall ja viu al fitxer propi |
| 71 | 165 | `ftt-break-convencio-document · 10/08` | **CRONICA** | 🔒 ftt-break-convencio-document · 10/08 — el break es **PRESENTA en convenció de DOCUMENT (±1)… | narracio de sessio; el detall ja viu al fitxer propi |
| 72 | 154 | `ftt-break-per-regla-i-traduccio · 10/08` | **CRONICA** | ftt-break-per-regla-i-traduccio · 10/08 — 🚨 «Talles que cobreix» era un SETTER MASSIU: 98 reg… | narracio de sessio; el detall ja viu al fitxer propi |
| 73 | 127 | `ftt-carril-cercador-poms-v4 · 09/08` | **CRONICA** | ftt-carril-cercador-poms-v4 · 09/08 — 🚨 `len(q)<2` amagava els 22 codis d'UNA lletra | narracio de sessio; el detall ja viu al fitxer propi |
| 74 | 138 | `ftt-graduacio-insitu-i-pom-duplicat · 09/08` | **CRONICA** | ftt-graduacio-insitu-i-pom-duplicat · 09/08 — 🔑 el picker va `eliminatiu`, MAI `strict` | narracio de sessio; el detall ja viu al fitxer propi |
| 75 | 178 | `ftt-quart-estat-shorthand-longhand · 09/08` | **CRONICA** | ftt-quart-estat-shorthand-longhand · 09/08 — 🚨 **una LONGHAND per spread sobre una SHORTHAND … | narracio de sessio; el detall ja viu al fitxer propi |
| 76 | 148 | `ftt-neteja-rulesets-buits · 09/08` | **CRONICA** | ftt-neteja-rulesets-buits · 09/08 — `fhort` 44→**1 ruleset** · 🚨 29 `SizingProfile` a NULL, n… | narracio de sessio; el detall ja viu al fitxer propi |
| 77 | 109 | `ftt-sembra-v4-cataleg-canonic · 09/08` | **FET-X** | ftt-sembra-v4-cataleg-canonic · 09/08 — **142 POMMaster canònics** | «142 POMMaster canonics»: avui n'hi ha 144 -> guanya la l.40 |
| 78 | 155 | `ftt-coda-models-seleccio-conjunt · 09/08` | **FET-V** | ftt-coda-models-seleccio-conjunt · 09/08 — 🔑 el banc MULTI-PÀGINA és el tenant `los` (51), no… | los=51 models CONFIRMAT avui; «fhort (1)» ja no val: fhort en te 39 |
| 79 | 158 | `ftt-coda-c1c2-media-daurat · 09/08` | **CRONICA** | ftt-coda-c1c2-media-daurat · 09/08 — 🚨 `safe_makedirs` fa `chmod` DESPRÉS del `mkdir` i mata … | narracio de sessio; el detall ja viu al fitxer propi |
| 80 | 156 | `ftt-s2-fitxa-patrons-crom · 09/08` | **CRONICA** | ftt-s2-fitxa-patrons-crom · 09/08 — 🚨 «no s'obre» era `media/…/2026/08` root:root: **el mes n… | narracio de sessio; el detall ja viu al fitxer propi |
| 81 | 138 | `ftt-bloc-b-cami-model · 08/08` | **CRONICA** | ftt-bloc-b-cami-model · 08/08 — 🚨 **`?mode=entry` és un GEST: una QA que hi entri ESCRIU AL D… | narracio de sessio; el detall ja viu al fitxer propi |
| 82 | 172 | `ftt-bloc-a-conformitat-mesurada · 08/08` | **CRONICA** | ftt-bloc-a-conformitat-mesurada · 08/08 — 🔑 **LA CONFORMITAT ES MESURA**: `qa_auditoria_compu… | narracio de sessio; el detall ja viu al fitxer propi |
| 83 | 158 | `ftt-f22-vocabulari-marques · 08/08` | **CRONICA** | ftt-f22-vocabulari-marques · 08/08 — 🔑 la MARCA viatja DINS de l'element · 🔵 el control és **… | narracio de sessio; el detall ja viu al fitxer propi |
| 84 | 132 | `ftt-u2-pantalla-s37-aturada · 07/08` | **CRONICA** | ftt-u2-pantalla-s37-aturada · 07/08 — 🚨 un camp amb `default` NO arriba a DRF amb default | narracio de sessio; el detall ja viu al fitxer propi |
| 85 | 159 | `ftt-s37-vet-c5-chip · 07/08` | **CRONICA** | ftt-s37-vet-c5-chip · 07/08 — 🔑 quan el fons de marca no pot canviar, canvia la TINTA · 🔵 no … | narracio de sessio; el detall ja viu al fitxer propi |
| 86 | 140 | `ftt-diagnosi-pre-sembra-v4 · 07/08` | **CRONICA** | ftt-diagnosi-pre-sembra-v4 · 07/08 — 🔑 **una FK nullable a la clau trenca la unicitat EN SILE… | narracio de sessio; el detall ja viu al fitxer propi |
| 87 | 127 | `ftt-u1u2-catalegs · 07/08` | **CRONICA** | ftt-u1u2-catalegs · 07/08 — 🔑 l'acumulació són DUES TAULES GERMANES i una UNIÓ A LA LECTURA | narracio de sessio; el detall ja viu al fitxer propi |
| 88 | 116 | `ftt-revisio-c1c6 · 07/08` | **CRONICA** | ftt-revisio-c1c6 · 07/08 — 🚨 3 bloquejants a C4 · 🚨 `public.TODDLER_EU` corrupte | narracio de sessio; el detall ja viu al fitxer propi |
| 89 | 131 | `ftt-cataleg-talles-c1c6 · 07/08` | **CRONICA** | ftt-cataleg-talles-c1c6 · 07/08 — 🔑 el dany era d'ACOBLAMENT · 🛑 CAT2.1(b) i pas 2 de C6 | narracio de sessio; el detall ja viu al fitxer propi |
| 90 | 146 | `ftt-m-fi-m1m2m3 · 07/08` | **CRONICA** | ftt-m-fi-m1m2m3 · 07/08 — ✅ un model SENSE JOC preserva les MANUAL · 🚨 esborrar el JOC deixa … | narracio de sessio; el detall ja viu al fitxer propi |
| 91 | 152 | `ftt-310-customerdetail-porta-de-lint · 07/08` | **CRONICA** | ftt-310-customerdetail-porta-de-lint · 07/08 — 🔑 `rules-of-hooks` és ERROR i ningú executa el… | narracio de sessio; el detall ja viu al fitxer propi |
| 92 | 117 | `ftt-nit-capes-run-n1n6 · 06/08` | **CRONICA** | ftt-nit-capes-run-n1n6 · 06/08 — el GRUP surt de `GarmentGroup`, MAI `POMCategory` | narracio de sessio; el detall ja viu al fitxer propi |
| 93 | 150 | `ftt-diagnosi-vocabularis-pom-system` | **CRONICA** | ftt-diagnosi-vocabularis-pom-system — 🔑 «POM System» NO és un model: rètol sobre `GarmentPOMMap` | narracio de sessio; el detall ja viu al fitxer propi |
| 94 | 110 | `ftt-vespre-forats-v1v6 · 06/08` | **CRONICA** | ftt-vespre-forats-v1v6 · 06/08 — 🚨 els fums contra dades vives no corren | narracio de sessio; el detall ja viu al fitxer propi |
| 95 | 172 | `ftt-arquitectura-06-08-tarda` | **CRONICA** | ftt-arquitectura-06-08-tarda — 🚨 el wipe mata les MANUAL per DOS predicats divergents (el 409… | narracio de sessio; el detall ja viu al fitxer propi |
| 96 | 146 | `ftt-q1q4-presa-reconciliada-i-acta · 06/08` | **CRONICA** | ftt-q1q4-presa-reconciliada-i-acta · 06/08 — 🚨 la sessió 148 del MILEY queda amb els POMs vells | narracio de sessio; el detall ja viu al fitxer propi |
| 97 | 149 | `ftt-poms-cataleg-client` | **CRONICA** | ftt-poms-cataleg-client — 🔑 `codi_client` és el codi de la CASA; el catàleg del client ÉS `Cu… | narracio de sessio; el detall ja viu al fitxer propi |
| 98 | 146 | `ftt-p05d-graduacio-superficie` | **CRONICA** | ftt-p05d-graduacio-superficie — 🔑 assignar un joc JA materialitza residents: l'observable és … | narracio de sessio; el detall ja viu al fitxer propi |
| 99 | 108 | `ftt-taxonomia-i-consulta-mesures` | **CRONICA** | ftt-taxonomia-i-consulta-mesures 🚨 31 items invisibles al pas 2 | narracio de sessio; el detall ja viu al fitxer propi |
| 100 | 94 | `ftt-p0-mati-diccionari-i-cercador` | **CRONICA** | ftt-p0-mati-diccionari-i-cercador 🛑 P0.5-parcial | narracio de sessio; el detall ja viu al fitxer propi |
| 101 | 112 | `ftt-w2-wizard-finder-proximitat` | **CRONICA** | ftt-w2-wizard-finder-proximitat 🔑 els eixos són de la FAMÍLIA 🚩 | narracio de sessio; el detall ja viu al fitxer propi |
| 102 | 91 | `ftt-modal-sortida-i-batec` | **CRONICA** | ftt-modal-sortida-i-batec 🚩 el guard pausa per DURADA | narracio de sessio; el detall ja viu al fitxer propi |
| 103 | 109 | `ftt-comprovacio-i-origen-guard` | **CRONICA** | ftt-comprovacio-i-origen-guard 🚩 `measurements_chat_view` NO tocat | narracio de sessio; el detall ja viu al fitxer propi |
| 104 | 120 | `ftt-mesures-dos-modes-v81` | **CRONICA** | ftt-mesures-dos-modes-v81 🚨 `set-measurements` reescriu `origen` de TOT el payload | narracio de sessio; el detall ja viu al fitxer propi |
| 105 | 63 | `ftt-cens-maquetes-ui` | **CRONICA** | ftt-cens-maquetes-ui 🚩 D-31.26 | pendent D-31.26 sense context llegible: destinar a vault o eliminar |
| 106 | 98 | `ftt-f3-corpus-cron-runbook` | **CRONICA** | ftt-f3-corpus-cron-runbook 🔴 «cauen al TimeSeed» és FALS | narracio de sessio; el detall ja viu al fitxer propi |
| 107 | 130 | `ftt-f28-hook-310-i-target-id` | **CRONICA** | ftt-f28-hook-310-i-target-id — 🔑 **React #310 = un hook sota el `return` de `loading`** | narracio de sessio; el detall ja viu al fitxer propi |
| 108 | 112 | `ftt-c5ui-execucio-nocturna` | **CRONICA** | ftt-c5ui-execucio-nocturna 🚨 `instancia_exigeix_nom` mana el gest 🚩 P8 | narracio de sessio; el detall ja viu al fitxer propi |
| 109 | 89 | `ftt-cicle-tasca-diagnosi` | **CRONICA** | ftt-cicle-tasca-diagnosi 🚨 Welford ja mana i menteix | narracio de sessio; el detall ja viu al fitxer propi |
| 110 | 137 | `ftt-cens-ui-pendent · 04/08` | **CRONICA** | ftt-cens-ui-pendent · 04/08 — 🚨 el folre no s'acota mai · 🚨 `POMAlert` i `FittingTab.jsx` sen… | narracio de sessio; el detall ja viu al fitxer propi |
| 113 | 131 | `ftt-d3121-veredicte-i-dues-diagnosis` | **CRONICA** | ftt-d3121-veredicte-i-dues-diagnosis — 🚨 D-31.4: 35 models i 1.444 regles a PROD | 02-04/08; el detall ja viu al fitxer propi |
| 114 | 115 | `ftt-c4-regressio-bloc-comportes` | **CRONICA** | ftt-c4-regressio-bloc-comportes 🚨 els 4 commits G mai van córrer l'app | 02-04/08; el detall ja viu al fitxer propi |
| 115 | 117 | `ftt-c4-bloc1-desancorar-lectors` | **CRONICA** | ftt-c4-bloc1-desancorar-lectors 🚨 cap dels 6 lectors passa per serializer | 02-04/08; el detall ja viu al fitxer propi |
| 116 | 105 | `ftt-nit-c4-segell-20260803` | **FET-X** | ftt-nit-c4-segell-20260803 🟢 1 449 tests · `test fhort` = 12 apps | «1 449 tests» es una foto d'un dia; el recompte creix a cada tram |
| 117 | 100 | `ftt-textbox-redimensionable` | **CRONICA** | ftt-textbox-redimensionable ✅ `bgFill:'transparent'` ES QUEDA | 02-04/08; el detall ja viu al fitxer propi |
| 118 | 64 | `ftt-cua-prec4-abc` | **CRONICA** | ftt-cua-prec4-abc 🚩 B1/B2 aturades | 02-04/08; el detall ja viu al fitxer propi |
| 119 | 114 | `ftt-columna-mesura-diagnosi` | **CRONICA** | ftt-columna-mesura-diagnosi 🚩 obrir la pantalla escriu a DUES superfícies | 02-04/08; el detall ja viu al fitxer propi |
| 120 | 101 | `ftt-sizefitting-duplicat-diagnosi` | **FET-X** | ftt-sizefitting-duplicat-diagnosi 🚨 dany viu (185, 182) | «dany viu (185, 182)»: cap dels dos models existeix a fhort (mesurat avui) |
| 121 | 97 | `ftt-c3-motor-derivacio` | **CRONICA** | ftt-c3-motor-derivacio 🚨 escriptor cec a `wizard_views.py:193` | 02-04/08; el detall ja viu al fitxer propi |
| 122 | 96 | `ftt-tram-instancia-20260802` | **LLEI** | ftt-tram-instancia-20260802 🚩 mai dues corregudes alhora | «mai dues corregudes alhora» es metode, no cronica |
| 123 | 109 | `ftt-instancies-pom-diagnosi` | **CRONICA** | ftt-instancies-pom-diagnosi el FK de POMMaster → `fhort.pom_pomglobal` | 02-04/08; el detall ja viu al fitxer propi |
| 124 | 91 | `ftt-mapa-toc-instancia` | **CRONICA** | ftt-mapa-toc-instancia 🚨 el green flag d'OpenAPI és CEC | 02-04/08; el detall ja viu al fitxer propi |
| 127 | 156 | `ftt-embut-adjunts-coll` | **FET-V** | ftt-embut-adjunts-coll — 🚨 bug destructiu (`update_fields` sense `'fitxer'`) · 🚩 **reprocessa… | pendent obert, accionable |
| 128 | 112 | `ftt-sprint-fitxa-imatges` | **FET-V** | ftt-sprint-fitxa-imatges 🚩 `save_document`/`importarDelTenant` sense assets | pendent obert, accionable |
| 129 | 97 | `ftt-bateig-no-arriba-a-les-taules` | **FET-V** | ftt-bateig-no-arriba-a-les-taules 🚨 **R1 a MITGES** | pendent obert, accionable |
| 130 | 104 | `ftt-g1g2-graduacio-porta-propia` | **FET-V** | ftt-g1g2-graduacio-porta-propia 🚩 409 `ruleset_altre_client` | pendent obert, accionable |
| 131 | 84 | `ftt-editor-tancament-seleccio` | **FET-V** | ftt-editor-tancament-seleccio 🚩 QA pendent | pendent obert, accionable |
| 134 🔻 | 315 | `ftt-heic-fotos-fitting` | **FET-V** | PENDENTS D'INFRA: 🚨 ftt-heic-fotos-fitting **dep nova al lock: `pip install` en desplegar** ·… | PENDENTS D'INFRA: 3 crons/pip sense installar — el mes valuos del tall |
| 135 🔻 | 200 | `ftt-fletxa-curva-sortides` | **FET-V** | ALTRES PENDENTS: 🚩 ftt-fletxa-curva-sortides QA · 🚩 ftt-delta-break-t1b-regla **4 taules T1b … | PENDENTS: QA fletxa + 4 taules T1b congelades |
| 136 🔻 | 197 | `ftt-nomenclatura-pom-camps` | **FET-V** | REFERÈNCIA: ftt-nomenclatura-pom-camps codi_client ≠ client_alias ≠ pom_code_global ≠ nom_fit… | referencia agrupada |
| 137 🔻 | 198 | `ftt-gate-mesures-pom-task-done` | **FET-V** | POM/TASQUES: ftt-gate-mesures-pom-task-done l'estat del model és del MODEL · ftt-conflicte-po… | referencia agrupada |
| 138 🔻 | 247 | `ftt-sprint-import-multipeca-f1f6` | **FET-V** | IMPORT: multipeça base del parser = etiqueta del DOCUMENT · hotfix beach + el guard talla no-… | referencia agrupada |
| 139 🔻 | 285 | `ftt-size-systems-cardinalitat` | **FET-V** | TALLES: ftt-size-systems-cardinalitat rigidesa = DADES+UX · cotes · ftt-baseset-implementat +… | referencia agrupada |
| 140 🔻 | 176 | `ftt-diagnosi-refactor-grading-163` | **FET-V** | GRADING: ftt-diagnosi-refactor-grading-163 ruleset buit → FIXED amb 200 · melo LINEAR+0 = FIXED | referencia agrupada |
| 141 🔻 | 312 | `ftt-self-customer-marca` | **FET-V** | MARCA/ITEM: ftt-self-customer-marca `tipologia` discrimina la UI · gate GRS LLEI C5 · ftt-pro… | referencia agrupada |
| 144 🔻 | 259 | `ftt-federacio-v2-cami-critic` | **FET-V** | ftt-federacio-v2-cami-critic 962 models LOS viuen a `fhort` · P1P2 TenantLink + origen EXTERN… | DUBTOS: «962 models LOS viuen a fhort» — avui fhort=39 i los=51. A VERIFICAR |
| 145 🔻 | 183 | `ftt-federacio-patro-c-retorn` | **FET-V** | 🚩 ftt-federacio-patro-c-retorn `los` sense POMMaster · 🚩 ftt-fase1-losan-cataleg neteja LOS a… | CONFIRMAT avui: los.pom_pommaster = 0 |
| 146 🔻 | 218 | `ftt-federacio-interactivitat` | **FET-V** | ftt-federacio-interactivitat Patró A: el Model no és particionable · P7 · ftt-login-unic-f1f2… | referencia tematica agrupada |
| 147 🔻 | 141 | `ftt-sembra-losan-ss27` | **FET-V** | ftt-sembra-losan-ss27 · ftt-paquet-losan-fasea — 961 models SS27 + export/load | referencia tematica agrupada |
| 150 🔻 | 251 | `ftt-silenci-grading-done` | **FET-V** | ftt-silenci-grading-done golden path 163 · s10 brownie break extrem-petit · ftt-5capes-proces… | referencia tematica agrupada |
| 151 🔻 | 233 | `ftt-size-refactor` | **FET-V** | ftt-size-refactor · ftt-aparellament-talles-done `talla_mapping` llei · PARITAT: diagnosi · l… | referencia tematica agrupada |
| 152 🔻 | 295 | `ftt-fitting-3fixes-robustesa` | **FET-V** | ftt-fitting-3fixes-robustesa el crash era bundle ranci · explorer · ftt-size-check-qa-model Q… | DUBTOS: models 182/185 no existeixen a fhort (potser PROD). A VERIFICAR |
| 155 🔻 | 258 | `ftt-motor-patrons-s0` | **FET-V** | ftt-motor-patrons-s0 AMELIA = PolyPattern · W2 · QA A · `operations.py:717` menteix · ftt-tra… | referencia tematica agrupada |
| 158 🔻 | 239 | `ftt-editor-estat-faseb` | **FET-V** | ftt-editor-estat-faseb mapa REAL · 7 fases fix save-as-template · zones ABCD · dos modes de f… | referencia tematica agrupada |
| 159 🔻 | 126 | `ftt-fitxa-tecnica-motor` | **FET-V** | ftt-fitxa-tecnica-motor NO és reportlab (Konva+pdf-lib) · churn | referencia tematica agrupada |
| 162 🔻 | 265 | `ftt-comercial-modul-bchain` | **FET-V** | ftt-comercial-modul-bchain commerce B1→B4c; B5 pendent · validació P1-P7 · ftt-empresa-fiscal… | referencia tematica agrupada |
| 163 🔻 | 235 | `ftt-f1-price-done` | **FET-V** | ALTA I LEGAL: F1 Stripe · F2 alta mínima · ftt-dashboard-manager-gantt · M1 · planning | referencia tematica agrupada |
| 164 🔻 | 135 | `ftt-mode-seleccio-intencio-done` | **FET-V** | ftt-mode-seleccio-intencio-done · filtres URL font de veritat | referencia tematica agrupada |
| 167 🔻 | 215 | `ftt-qa-token-jwt-bloquejat` | **LLEI** | 🚩 ftt-qa-token-jwt-bloquejat — **l'agent NO pot emetre el JWT de QA** (classificador); Playwr… | metode de QA; ARA MATEIX CAU FORA DEL TALL |
| 168 🔻 | 151 | `ftt-metode-com-a-skills` | **LLEI** | ftt-metode-com-a-skills mètode versionat · ubicació diagnosis a `docs/diagnosis/` | metode i ubicacio de diagnosis; ARA MATEIX CAU FORA DEL TALL |
| 169 🔻 | 228 | `ftt-staging-infra` | **FET-V** | ftt-staging-infra + Host del tenant ports, pg_restore, tenants · ftt-vhost-root-per-domini ve… | ports/tenants/pg_restore; ARA MATEIX CAU FORA DEL TALL |
| 170 🔻 | 233 | `ftt-prod-estat-via-dump` | **FET-V** | estat PROD sense SSH: el backup diari · ftt-media-uploads-permisos + namespace · e2e real a s… | estat PROD sense SSH + permisos media; ARA MATEIX CAU FORA DEL TALL |
| 173 🔻 | 165 | `ftt-web-journey-motor · 12/08` | **FET-V** | ftt-web-journey-motor · 12/08 — 🚨 el bloc `prefers-reduced-motion` **es menjava 7 de 8 imatge… | referencia tematica agrupada |
| 174 🔻 | 230 | `ftt-web-landing-portes-tecnic` | **FET-V** | ftt-web-landing-portes-tecnic 🔑 **l'overlay de cotes MANA i la camisa s'hi encaixa a sota** ·… | referencia tematica agrupada |
| 175 🔻 | 184 | `webiafy-project` | **FET-V** | webiafy-project · concurrents webiafy (Astro SSR híbrid) · frappe-cleanup-fhort pendent DROP BD | referencia tematica agrupada |

---

## 4 · Llista de BAIXES — **això és el que cal validar, no el diff**

### 4.1 Baixes per classe, amb motiu i destí

| classe | entrades | destí proposat | motiu |
|---|---:|---|---|
| **CRÒNICA** | **87** | **el fitxer del tema** (ja hi és) + `ESTAT_PROJECTE.md` / `DECISIONS.md` | narració de feina feta; l'índex ha de portar el ganxo, no l'acta. **Cap contingut es perd: cada línia té el seu `.md`** |
| **FET-X** | 3 | **enlloc** | caducats o falsos, verificats §3.1 |
| **DUPLICAT** | 0 | — | — |
| LLEI · FET-V | 55 | **es queden** (reescrits més densos) | — |

### 4.2 Les úniques supressions SENSE destí (3) — validar una per una

| línia | entrada | motiu de la supressió |
|---:|---|---|
| 77 | «142 POMMaster canònics» | **superada per mesura**: avui 144, i la l.40 ja ho deia. El fitxer `ftt-sembra-v4-cataleg-canonic` es queda |
| 116 | «1 449 tests · `test fhort` = 12 apps» | **foto d'un dia**: el recompte creix a cada tram; conservar-la és conservar un número fals |
| 120 | «dany viu (185, 182)» | **els dos models no existeixen a `fhort`**: o s'ha resolt o era PROD |

> ⚠️ **Les tres es poden conservar sense cost** si prefereixes el criteri mínim: sumen
> 315 B i la proposta té 11 KB de marge. **Les trec perquè un fet fals a l'índex és pitjor
> que una línia de menys** — però és decisió teva, no meva.

### 4.3 Els 95 fitxers que perden el punter d'índex

**95 fitxers perden el punter d'índex.** Cap no s'esborra: segueixen a
`memory/` i segueixen sent **recuperables per la seva `description`** — el que perden
és el punter carregat a cada sessió, no l'existència.

| fitxer | motiu de la baixa |
|---|---|
| `ftt-310-customerdetail-porta-de-lint` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-400-linear-zero-era-el-proces` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-arquitectura-06-08-tarda` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-baseset-condicionat-diagnosi` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-bloc-a-conformitat-mesurada` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-break-per-regla-i-traduccio` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-c3-motor-derivacio` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-c4-bloc1-desancorar-lectors` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-c4-regressio-bloc-comportes` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-capcalera-fitxa-retrat` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-carril-cercador-poms-v4` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-cataleg-talles-c1c6` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-cens-ui-pendent` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-cicle-tasca-diagnosi` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-coda-c1c2-media-daurat` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-coda-models-seleccio-conjunt` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-columna-mesura-diagnosi` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-conflicte-pom-pas2-r1r4` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-d3121-veredicte-i-dues-diagnosis` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-dashboard-manager-gantt` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-diagnosi-cotes-pom-sketch` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-diagnosi-pre-sembra-v4` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-dues-forces-construides-sense-us` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-e1-escalat-presa-dos-passos` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-e3-tancada-i-mesurar-set` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-ef-intervals-i-step-prestat` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-escalat-subtab-vigent` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-f1-price-done` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-f2-fitxa-dp1` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-f28-hook-310-i-target-id` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-f3-corpus-cron-runbook` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-familia-graella-import` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-federacio-interactivitat` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-filtres-avancats-done` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-fitting-3fixes-robustesa` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-fix-wizard-sembra-done` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-ftt-version-churn` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-graduacio-insitu-i-pom-duplicat` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-h-taula-base-fitxa` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-hotfix-beach-talla-descarta` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-import-explorer-mesures-bug` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-instancies-dos-eixos-posicio` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-instancies-pom-diagnosi` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-j-consulta-no-es-treball` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-m-fi-m1m2m3` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-m1-dashboard-done` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-m2-cara-rondes` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-m3-cicle-vida-model` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-mapa-toc-instancia` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-mesures-dos-modes-v81` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-modal-sortida-i-batec` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-mode-seleccio-intencio-done` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-neteja-rulesets-buits` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-nit-c4-segell-20260803` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-onada3-identitat-fila-import` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-p0-mati-diccionari-i-cercador` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-p7-superficie-brand` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-paquet-losan-fasea` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-patro-b-editor-7fases-done` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-poms-tabs-actius-inactius` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-pre-sprints-s45-diagnosi` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-promocio-model-item` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-q1q4-presa-reconciliada-i-acta` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-quart-estat-shorthand-longhand` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-revisio-c1c6` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-s10-grading-brownie` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-s2-blocb-logica-mesures` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-s2-t8-import-per-prenda` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-s42-escalat-i-mesurar` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-s42-f1-escriptura-garment` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-s42-q5q6-full-fitting` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-s45-bloc3d-gating-pickers` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-sembra-losan-ss27` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-sembra-v4-cataleg-canonic` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-sembra-v5-dos-vocabularis` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-size-check-qa-model` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-size-refactor` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-sizefitting-duplicat-diagnosi` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-staging-dades-model185-corruptes` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-sub-editor-dos-modes-done` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-taxonomia-i-consulta-mesures` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-test-que-compara-amb-migracio-congelada` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-textbox-redimensionable` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-tram-i-traduccio-poms` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-tren-panys-sembres` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-u1u2-catalegs` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-u2-pantalla-s37-aturada` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-validacio-comercial-done` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-vespre-forats-v1v6` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-viab-matcher-unificat` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-w2-wizard-finder-proximitat` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-web-editorial-contrast` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-web-planning-porta-01` | crònica de sessió: el detall ja és al fitxer propi |
| `ftt-zones-editor-abcd-done` | crònica de sessió: el detall ja és al fitxer propi |
| `webiafy-concurrent-sessions` | crònica de sessió: el detall ja és al fitxer propi |

### 4.4 El que la poda SALVA del tros perdut (§2) i de dins de les cròniques

Cap d'aquests no es carrega avui, o està enterrat en una crònica. **Tots pugen a una
secció pròpia a la proposta:**

| salvat | d'on venia |
|---|---|
| **3 crons/pip d'infra sense instal·lar** | L.134, fora del tall |
| **JWT de QA bloquejat · Playwright a `/tmp/qa-venv`** | L.167, fora del tall |
| **Host del tenant · ports · `pg_restore`** | L.169, fora del tall |
| **AMELIA = PolyPattern · llindar 22°** | L.155, fora del tall |
| **La fitxa no és reportlab (Konva+pdf-lib)** | L.159, fora del tall |
| **`los` sense POMMaster** *(reconfirmat per SQL avui: 0)* | L.145, fora del tall |
| **`settings_test` amb `FTT_TEST_DB`** | dins la crònica L.31 |
| **El symlink de `node_modules` DESTRUEIX el directori real** | dins la crònica L.32 |
| **Taules Q8 congelades sense versió · fitxa a 2 mm de l'A4** | dins la crònica L.44 |
| **El banc 1383 ja no és el de la sembra · cap fitxer seu al disc** | dins les cròniques L.50/L.52 |
| **Els 3 pendents de Patró C (motor)** | dins la crònica L.30 |
| **`patternfile_xor_model_item` admet GTI** | dins la crònica L.30 |

---

## 5 · La proposta, en xifres

| | actual | proposta |
|---|---:|---:|
| mida | 31 210 B | **13 108 B** *(sense la capçalera de proposta)* |
| % del límit (24 986 B) | **125 %** 🚨 | **52 %** ✅ |
| es carrega | 80,1 % | **100 %** |
| entrades | 145 | 61 |
| punters | 197 | 105 · **0 trencats** |
| marge per créixer | **−6 224 B** | **+11 878 B** |

**Criteri d'ordre aplicat:** LLEIS DE DIAGNOSI (les que eviten conclusions falses) →
LLEIS DEL GEST → PENDENTS VIUS → FETS VIGENTS per àmbit (infra/BD · POM-talles-grading ·
motor-fitxa-editor · federació-comercial-altres). **Res més.**

**Reescriptura per densitat:** mateixa informació, l'estil telegràfic de la línia 9. Les
cròniques que aportaven una llei hi entren **com a llei d'una línia**, no com a acta.

---

## 6 · Rastre

| mesura | com |
|---|---|
| mida i tall | bytes reals (`len(línia)+1`), no caràcters: el fitxer és ple de multibyte |
| mida per secció / classe | recompte programàtic sobre `MEMORY.md`, 145 entrades |
| FET-X i dubtes | `sudo -u postgres psql -p 5433 -d ftt_staging` — **només `SELECT`** |
| punters | extracció de `](*.md)` i `os.path.exists` sobre `memory/` |

Consultes fetes (totes de lectura): `tenants_client` · `pom_pommaster` (fhort/los) ·
`models_app_model` (fhort/los, per `origen` i per id) · `patterns_*` (file/piece/point/pom/
exportacknowledgement) · `information_schema.columns`.

**`MEMORY.md` no s'ha modificat.** Comprovable: cap escriptura al directori `memory/`.
