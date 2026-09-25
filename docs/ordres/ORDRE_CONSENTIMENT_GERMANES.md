# ORDRE — Consentiment de germanes en aplicar el fitting a la base

Data 2026-09-24 · Patró B (implementació) · Staging `/var/www/ftt-staging`, branca `dev`.
**Estat: FET. 8 commits locals, cap push.** (5 previstos a l'encàrrec + 3 trobats necessaris
durant la implementació — v. «Commits addicionals», sota.)

---

## Part 1 — PAS 0, ATURADES i la seva resolució

La sessió es va aturar a PAS 0 amb tres troballes (document original conservat més avall,
secció «Historial»). Resposta d'Agus (23/09, mateix dia):

1. **Maqueta**: la del disc era la 1a versió; Agus va pujar la bona. **Verificat de nou abans
   del COMMIT 5**: `md5sum ops/maquetes/maqueta_consentiment_germanes_v1.html` =
   `b70027f8a637776c52a345349900c89f` — coincideix amb l'encàrrec. ✅
2. **2a migració APROVADA** (Montse informada): `ModelInstanceOffset`, model nou i petit, SENSE
   tocar `ModelGradingRule` ni `ModelGradingOverride`.
3. **Regeneració de talles: FORA de l'encàrrec.** Es manté D4 §2. «Aplicar» escriu la base i la
   relació d'instàncies i prou; «Propagar a grading» segueix sent l'únic gest que regenera
   talles. Eliminat el punt (d) del COMMIT 4.

Amb això, cap de les tres troballes seguia bloquejant i la implementació va continuar.

---

## Part 2 — Els 8 commits

| # | SHA | Missatge | Fitxers |
|---|---|---|---|
| 1 | `06abac5b` | fix(fitting): criteri únic de «mesurat» — sense mirar desviació ni decisio (cas 2578) | 4 |
| 2 | `bd0e2ff2` | feat(fitting): model `FittingSisterDecision` — rastre del consentiment de germanes (migració 1/2) | 2 |
| 2b | `0366db1d` | feat(models_app): model `ModelInstanceOffset` — sobirania del model (migració 2/2) | 2 |
| — | `547df0c9` | **fix addicional**: «mesurat» és `linia_te_contingut`, no `valor_real` present | 4 |
| 3 | `f3705214` | feat(fitting): endpoint de PROPOSTA de consentiment (sense escriure) | 4 |
| 4 | `4ccdc358` | feat(fitting): endpoint d'APLICAR amb consentiment de germanes | 4 |
| — | `c634ec0a` | **fix addicional**: proposta exposa el nom del POM (cascada canònica) | 1 |
| 5 | `65e93f45` | feat(fitting): modal de consentiment de germanes a «Gravar i tornar» | 5 |

Total: 17 fitxers tocats, +1438/−92 línies (`git diff --stat 0bbfd08a..65e93f45`). **2
migracions** (les úniques aprovades) aplicades als 3 schemas i auditades amb `\d` contra la
BD real. `manage.py check` i `makemigrations --check --dry-run` nets a cada pas. `systemctl
restart ftt-staging` després de cada commit de BE. `npm run eslint` i `npx vite build
--outDir <scratch>` nets al COMMIT 5 (build a un directori fora de `dist` per no publicar a
mig d'una revisió — llei de l'arbre compartit; **cal un `npm run build` real per desplegar,
que no he fet jo**).

### Commits addicionals (no previstos a l'encàrrec original)

**`547df0c9` — una correcció sobre el meu propi COMMIT 1.** En arribar al COMMIT 4 i córrer
la suite pel camí REAL (`close_piece_fitting`, que crida `reconcilia_linies` primer), 5 tests
van fallar: una germana que hauria de quedar disponible per a la derivació sortia sempre
«mesurada» i mai es proposava res. Arrel: `reconcilia_linies` pre-omple CADA germana no
tocada amb una línia fantasma (`valor_real = valor_teoric`, còpia) cada vegada que la presa
s'obre — i el meu criteri d'ahir («porta un `valor_real`, punt») ho complia SEMPRE, tocada o
no. El predicat correcte ja existia a la casa: `fitting/esdeveniments.py::linia_te_contingut`
(`presa_at` primer, `decisio`/`nota` després, la desviació NOMÉS de reserva per a files
anteriors al camp) — el mateix que decideix si el Repàs compta un fitting com a fet. Corregit
i verificat amb la suite passant pel camí real, no només per la crida directa.

**`c634ec0a` — la proposta necessitava el nom del POM** per a la capçalera «B · Waist width»
de la maqueta; el payload de COMMIT 3 només portava el codi. Afegit via la cascada canònica
(`pom.nomenclatura.codi_de`/`noms_de`, ÀLIES > TENANT > GLOBAL), no una lectura directa de
`pom.nom_client`.

---

## Part 3 — Migracions (llegides i auditades)

- `fitting/migrations/0029_fittingsisterdecision_consentiment_germanes.py` — `FittingSisterDecision`
  (`piece_fitting`, `base_measurement`, `valor_actual_abans`, `valor_proposat`, `regla_text`,
  `valor_final`, `decisio` ∈ {MANTINGUT, PROPOSTA, MANUAL}, `created_by`, `created_at`). Unique
  `(piece_fitting, base_measurement)`.
- `models_app/migrations/0088_modelinstanceoffset_relacio_instancies.py` — `ModelInstanceOffset`
  (`model`, `pom`, `capa`, `instancia_origen`, `instancia_desti`, `delta`, `origen='FITTING'`,
  `piece_fitting`, `created_by`, `created_at`, `updated_at`). Unique
  `(model, pom, capa, instancia_origen, instancia_desti)` — es desa a LES DUES BANDES.

Auditades amb `\d fhort.fitting_fittingsisterdecision` i `\d fhort.models_app_modelinstanceoffset`
contra la BD real (columnes i FK confirmats un a un, no només `migrate_schemas OK`).

---

## Part 4 — Verificació (substitut dels curls: aquest agent no pot emetre el JWT de QA,
`ftt-qa-token-jwt-bloquejat`)

Cada endpoint provat via `APIRequestFactory` + `force_authenticate` contra el ViewSet real
(routing → permisos → view → transacció → serialització), banc CANET-like (B relaxed +
extended + seam):

- **Proposta** (`test_proposta_consentiment.py`, 11 tests): 200 amb germanes i defectes
  correctes per origen, PUR (cap escriptura verificada), delta confirmat de
  `ModelInstanceOffset` guanya al càlcul en viu, `buit=True` quan no toca res.
- **Aplicar** (`test_aplicar_consentiment.py`, 5 tests): els 3 casos (mantenir/proposta/manual)
  amb `origen` correcte per cas, override reescrit a les dues bandes (directe i invers),
  idempotència (2a aplicació sense línies noves = 0 germanes decidides), camí sense
  `decisions` intacte.
- **Regressió**: `test_consolidacio_instancies_multiples.py`, `test_repara_base_des_de_fitting.py`,
  `test_d3121_veredicte.py` — verds als 3 punts de control (post-COMMIT 1, post-fix predicat,
  post-COMMIT 4).

Total acumulat de la sessió: **37 tests** al punt final (`test_ftt_c4final`), tots verds.

---

## Part 5 — Bidireccional contra la maqueta (md5 verificat)

Substitut de les captures: aquest agent no té navegador amb sessió autenticada (mateix
blocador del JWT). Comparació ESTRUCTURAL element a element contra
`maqueta_consentiment_germanes_v1.html`, 3 estats coberts pel component (buit→sense modal,
obert amb defectes, post-interacció Usar/editar):

**16 casos comprovats · 1 desviació** (documentada i deliberada):

| Element de la maqueta | Implementació | Veredicte |
|---|---|---|
| Títol «Aplicar el fitting a la base» | `t('fitting.save.consent_title')` | ✅ |
| Subtítol «N germanes afectades · M POMs» | `consent_subtitle` interpolat | ✅ |
| Taula 4 columnes 28/12/14/46% | mateixos amples inline | ✅ |
| Capçaleres majúscules, `--fs-caption`, tracking | mateix | ✅ |
| Fila de POM: fons `--sel`, codi `--gold` negreta, nom negreta | mateix | ✅ |
| «mesurat al fitting: X V (era Y)» | construït client-side (`etiquetaInstancia`+`formatNum`) | ✅ |
| Indentació de la instància (28px) | `paddingLeft: 28` | ✅ |
| Badge «mesurat»/«derivat» | component `Badge` de la casa (`gray`/`gold`) | ⚠️ fons difereix (`--bg-page`/`--sel` vs `--sel`/`--white` de la maqueta) — **deliberat**: `Badge` ja reconcilia aquesta llei a tot el producte (v. el seu propi docstring) i una còpia local divergent seria pitjor que la diferència de fons |
| Input Actual (76px, dreta, negreta, vora `--line`) | mateix | ✅ |
| «era X» sota l'input, només si canvia | mateix (comparació amb epsilon) | ✅ |
| Proposta: valor negreta + regla + botó Usar/Usada | mateix, `regla_text` ve del backend | ✅ |
| Botó Usada: vora/fons/tinta `--ok`/`--ok-bg` | mateix | ✅ |
| Peu: Usar totes / Restablir / Cancel·lar / Aplicar (únic blau) | `boto('sec')`/`boto('ter')`/`boto('pri')` — tokens IDÈNTICS, classes CSS diferents | ✅ |
| Modal 860px, radi `--r-card` | mateix | ✅ |
| Format decimal amb coma | `utils/num.js` (formatNum/parseNum), política ja establerta | ✅ |
| Cap text d'ajuda a pantalla | confirmat, cap s'ha afegit | ✅ |
| Cancel·lar NO truca `close` | confirmat al codi i als tests | ✅ |

**guardia-i18n**: 15 claus noves, paritat ca/en/es verificada per script (`nombre de claus
consent_*: 15` als tres fitxers, cap manca).

**revisor-diff**: `services_size_check.py` (`resolve_size_check:230-264`) **NO s'ha tocat** —
té el mateix mecanisme de trepitjada que el fix del 23/09 tancava per al fitting, sense
consentiment ni la correcció d'avui. Deute obert, mateix nom, sprint propi (ja anotat a
`DIAGNOSI_CONSENTIMENT_GERMANES.md` BLOC Q7).

---

## Part 6 — El que l'Agus ha de fer

1. Revisar els 8 commits (`git log 0bbfd08a..65e93f45 --stat` / `git show <sha>` cadascun).
2. `npm run build` real (jo he construït a un directori fora de `dist` a posta) i push des
   de SSH.
3. Decidir si `resolve_size_check` entra a un sprint propi amb la mateixa llei (Q7 de la
   diagnosi).
4. Provar el modal en viu (aquest agent no ho pot fer — JWT).

**Cap ATURADA activa.** Cap escriptura de germana fora del modal. Cap segona migració fora
de les dues aprovades.

---

## Historial — el document original de PAS 0 (conservat, no esborrat)

### Estat original: ATURAT abans d'escriure cap línia de codi

Tres troballes de PAS 0 van aturar la cadena, dues d'elles exactament les que el propi
encàrrec demanava vigilar («si l'override o la regeneració NO existeixen com a servei
reutilitzable → digues-ho abans d'escriure»).

#### 1 · La maqueta NO tenia el md5 esperat (RESOLT — v. Part 1.1)

`ops/maquetes/maqueta_consentiment_germanes_v1.html` existia (6063 bytes) però amb md5
`25e772059500185d2167ee6123efb65f` ≠ l'esperat `b70027f8a637776c52a345349900c89f`.

#### 2 · NO existia cap «override d'instància/folgança del model» reutilitzable (RESOLT — v. Part 1.2, COMMIT 2b)

`ModelGradingRule` (`models_app/models.py:1188-1234`) és, per decisió de domini deliberada
(«Decisió Montse», comporta `C1-ins`), SENSE `capa` ni `instancia`. `ModelGradingOverride`
és un valor ABSOLUT per talla no-base, no una folgança entre germanes. La folgança no es
persistia enlloc, per disseny (`services_derivacio.py` docstring). Resolt amb `ModelInstanceOffset`,
migració nova aprovada per Agus (Montse informada).

#### 3 · Regenerar talles a «Aplicar» contradeia D4 §2 (RESOLT — v. Part 1.3, eliminat del COMMIT 4)

`DECISIONS.md:790-793` i `fitting/services.py:890-894` (D4, 21/07): «ni tancar un fitting
propaga». Agus va confirmar: fora de l'encàrrec, es manté D4, eliminat el punt (d).
