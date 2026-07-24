# RESULTAT — P0b: vocabulari de targets + franja d'edat (2026-07-24)

> Sprint executat a `dev` (staging). **Cap toc a PROD.** Commits locals, **SENSE push**
> (CLAUDE.md § Governança: els pushes els fa l'Agus).

**Veredicte: LLEST PER MERGE A MAIN**, amb 4 banderes per decidir (cap d'elles bloqueja el
merge; totes són decisions de producte, no defectes).

---

## 1. El rename

    BOY          → KID_BOY          GIRL         → KID_GIRL
    TODDLER_BOY  → BABY_BOY         TODDLER_GIRL → BABY_GIRL
    BABY_BOY     → NEWBORN_BOY      BABY_GIRL    → NEWBORN_GIRL
    BABY_UNISEX  → NEWBORN_UNISEX

`MAN` · `WOMAN` · `TEEN_BOY` · `TEEN_GIRL` · `UNISEX_ADULT` · `MATERNITY` — sense canvi.

### El mapa no és una preferència de nom: les dades ja el deien

`sembra_models_losan_ss27.csv` porta dues columnes que parlen del mateix: la nostra `target` i
la de LOSAN, `seccio_client`. Casen **1:1, amb comptes exactes**:

| `seccio_client` (LOSAN) | `target` (vell) | files | → nou |
|---|---|---:|---|
| NEW BORN BOY / GIRL | BABY_BOY / BABY_GIRL | 19 / 26 | `NEWBORN_*` |
| BABY BOY / GIRL | TODDLER_BOY / TODDLER_GIRL | 78 / 88 | `BABY_*` |
| KIDS BOY / GIRL | BOY / GIRL | 104 / 139 | `KID_*` |

La franja que LOSAN anomena «BABY» és la que nosaltres dèiem TODDLER, i el que nosaltres dèiem
BABY és NEWBORN. El desajust era nostre, i la sembra ja el documentava sense que ningú ho llegís.

---

## 2. PAS 0 — Patró A (read-only). Cap condició de STOP

**`Target` ÉS una taula neta, replicada per schema.** `pom` viu a `SHARED_APPS`
(`settings.py:55`) **i** a `TENANT_APPS` (`settings.py:68`), així que `pom_target` existeix a
cada schema. Estat trobat abans de tocar res:

| schema | files a `pom_target` |
|---|---:|
| `public` | 13 (ids 1–13) |
| `fhort` | 13 (ids 1–13, idèntiques) |
| `los` | **0 (buit)** |

**Cap FK apunta a `codi`.** Els tres referrers apunten a `id`:
`SizingProfile.target` FK (`models.py:938`), `SizeSystem.targets` M2M (`:303`),
`GradingRuleSet.targets` M2M (`:593`). Per tant el rename és un canvi de **valor** dins d'una
columna, no una re-identificació: cap fila es despenja, cap CASCADE es dispara. **Sense STOP.**

**Staging SÍ té el tenant LOS** (schema `los`, `tipologia=marca`, id 13) — ha canviat des del
cens de juliol —, però el seu catàleg és **buit**: els 1056 models viuen a `fhort`. La
validació visual s'ha fet contra `fhort`.

**El patró POM de 2 línies** és `components/POMBrowser/POMBrowser.jsx:504-512` (primari
`--text-main` pes 500 · secundari `--text-muted` cursiva, i la 2a línia **no es pinta** si és
buida). S'ha copiat, no reinventat.

---

## 3. Fitxers tocats

### Backend — commit `3993838`
| fitxer | què |
|---|---|
| `backend/fhort/pom/models.py` | `Target.CODI_CHOICES` amb els 7 renames |
| `backend/fhort/pom/migrations/0046_alter_target_codi.py` | `AlterField` de `choices` (cap SQL) |
| `backend/fhort/pom/management/commands/rename_targets_p0b.py` | **NOU** — el rename de dades |
| `backend/fhort/pom/test_p0b_rename_targets.py` | **NOU** — 8 tests |

### Backend seeds — commit `97a5e2d`
`grading_rules_master_delta_v1.json` · `losan_ss27.py` · `losan_grading_v3.py` ·
`losan_package/{07_size_systems,08_rulesets,10_profiles}.json` ·
`seed_kids_baby_target_map.py` · `seed_baby_months_profiles.py` ·
`sembra_models_losan_ss27.csv` (454 files, **només** la columna `target`; verificat columna a
columna: **0 canvis fora de `target`**).

### Frontend + i18n — commit `b91cc83`
| fitxer | què |
|---|---|
| `frontend/src/components/grading/TargetLabel.jsx` | **NOU** — el patró de 2 línies, font única |
| `frontend/src/components/grading/gradingAxes.js` | `TARGETS` amb codis nous + `targetLabel`/`targetFranja` |
| `frontend/src/i18n/{ca,en,es}.json` | 13 noms + 13 franges per idioma |
| `frontend/src/pages/ModelWizard.jsx` | consumidor 1 |
| `frontend/src/pages/GradingRuleSets.jsx` | consumidor 2 (`TargetPills`) |
| `frontend/src/components/SizingProfileSelector.jsx` | consumidor 3 |
| `frontend/src/components/CascadeSelector/CascadeSelector.jsx` | consumidor 4 (`TargetCard`) |

---

## 4. Decisions d'implementació que val la pena saber

**El rename va a un management command, no a `scripts_tmp/rename_targets_p0b.py`.** El brief el
donava per escrit i validat; **no existia enlloc del servidor** (ni ell ni
`DIAGNOSI_CENS_TENANT_LOS_2026-07-24.md`). S'ha escrit a l'especificació descrita, però com a
`manage.py rename_targets_p0b` perquè entra a git i es pot executar a PROD amb el mateix
`manage.py` que tota la resta, en comptes de viure com a fitxer solt no versionat.

**Per què cal ordre.** És una permutació amb col·lisions sobre una columna `UNIQUE`: `BABY_GIRL`
és alhora origen (→`NEWBORN_GIRL`) i destí (`TODDLER_GIRL`→). Es fa en dos temps dins d'**una**
transacció: A/B mouen els que col·lisionen a `_TMP_*`, C renombra els lliures, D aterra els
temporals. Si res falla, cap schema queda a mitges.

**La idempotència no és trivial i era un bug real que ha caçat el dry-run.** Com que `BABY_*`
existeix **abans i després**, la seva presència no diu res sobre si el rename ja s'ha fet. El
primer guard que vaig escriure llegia això com a «estat mixt» i petava en sec. Els testimonis
fiables són els codis que viuen a **un sol** vocabulari: `KID_*`/`NEWBORN_*` només després;
`BOY`/`GIRL`/`TODDLER_*`/`BABY_UNISEX` només abans. Sense aquesta distinció, una segona passada
tornaria a moure `BABY_*`→`NEWBORN_*` i **buidaria la franja BABY**.

**La franja viu a i18n, no al component** (`model_wizard.target_franja_<CODI>`), coherent amb
`tasktype.<code>` (DECISIONS.md §3). Buida per als adults, i llavors la 2a línia **no es pinta
gens** — ni guió ni espai reservat, que faria ballar l'alçada dels pills entre la fila d'adults
i la d'infantil. `targetFranja` també es defensa de la config d'i18next: si `returnEmptyString`
es desactivés, `t()` tornaria la clau en cru i pintaríem `model_wizard.target_franja_MAN` dins
un pill; si el valor és buit **o igual a la clau**, no hi ha 2a línia.

**Dos ajustos que la 2a línia obliga.** `TargetPills` baixa de `borderRadius: 999` a `8` (una
càpsula rodona al voltant d'un bloc de dues línies es llegeix com un error de layout), i el xip
seleccionat del `ModelWizard` passa el seu propi color de franja (té fons `--warn` ple amb text
blanc, i el gris per defecte hi quedaria il·legible).

---

## 5. PAS 5 — Validació visual (llei S18)

Feta amb Playwright contra el **bundle real de `frontend/dist`** (el mateix que publica nginx),
amb `/api/` estubejat. **Cap credencial**: el client només comprova que hi hagi un token al
localStorage, i els pills es pinten del vocabulari estàtic + i18n. Captures a
`docs/diagnosis/captures-p0b/` (no commitades).

| checklist del brief | resultat |
|---|---|
| Pills amb nom + franja a les **4** superfícies | ✅ ModelWizard · GradingRuleSets/TargetPills · SizingProfileSelector · CascadeSelector |
| Franja oculta a MAN/WOMAN sense guió ni buit estrany | ✅ `Dona`/`Home`/`Unisex adult`/`Maternitat` en 1 línia neta |
| 3 idiomes amb la franja traduïda | ✅ `mesos/anys` · `months/years` · `meses/años` (12 cadenes al bundle) |
| Cap superfície amb BOY/GIRL/TODDLER_*/BABY_* antic | ✅ 0 ocurrències al codi font i al bundle servit |
| `matchesTarget` segueix casant | ✅ **provat de veritat**, no només per lectura |

**La prova del matching.** A `/poms/grading` la cascada sencera resol amb els codis nous:
target `Nadó nena` → construcció `Punt` → fit `Regular` → grup `Tops` → família `Jersey Tops`
→ **apareix la fitxa «RS Newborn — Targets: Nadó nena · Nadó nen · Nadó unisex»**. I al pas 1,
els 8 targets coberts pels rulesets surten vius mentre `Unisex adult`/`Adolescent nena`/
`Adolescent nen`/`Maternitat` surten **atenuats** — que és `availableTargetCodes` →
`matchesTarget` funcionant sobre els codis nous d'extrem a extrem.

---

## 6. Estat de staging

- `manage.py check` net · `npm run build` net · `migrate_schemas` aplicada als 3 schemas.
- `rename_targets_p0b --apply` executat: **7 files a `public`, 7 a `fhort`, `los` no-op** (buit).
  Backup previ de les 3 taules a l'scratchpad de la sessió.
- **Els ids s'han conservat exactes** (1–13) i totes les relacions sobreviuen — comprovat
  comptant perfils/rulesets/size-systems per target després del rename.
- `ftt-staging.service` reiniciat · `/api/schema/` **200**.

### Tests
- **8/8** els nous de `test_p0b_rename_targets` · **11/11** els de `gradingAxes`.
- Suite sencera `fhort.pom`: **139 tests, 115 verds, 24 en error**.
  Els 24 són **PREEXISTENTS**, no meus: fallen **idènticament** al commit `b1c63b8` (abans de
  P0b), verificat en un worktree a part. Són `test_g6_segell` + `test_g6_grading_gates`, tots
  amb `IntegrityError: duplicate key ... fitting_sizefitting_model_id_numero_uniq`, i cap dels
  dos fitxers menciona `Target`. **0 regressions de P0b.**

---

## 7. Banderes per al CTO

**B1 — Les franges del brief NO casen amb `age_min_months`/`age_max_months` de la BD.**

| target | franja (brief, i18n) | BD (mesos) | equival a |
|---|---|---|---|
| `NEWBORN_*` | 0-24 mesos | 0–24 | ✅ casa |
| `BABY_*` | 3-36 mesos | 24–60 | ❌ 2–5 anys |
| `KID_*` | 2-12 anys | 60–144 | ❌ 5–12 anys |
| `TEEN_*` | 8-16 anys | 144–192 | ❌ 12–16 anys |

El brief diu explícitament que la franja va a i18n i **no** es deriva de la BD, així que
**no he tocat les columnes d'edat**. Però ara conviuen dues veritats sobre el mateix: la que
es pinta i la que el backend fa servir (`Target.is_baby` mira `age_max_months <= 36`, i amb les
dades actuals `BABY_*` té max 60 → `is_baby` és **False** per als BABY). Decideix quina mana.

**B2 — El brief llista 11 targets; la BD en té 13.** `UNISEX_ADULT` i `MATERNITY` no surten al
brief. Els he **conservat** amb franja buida. Si han de desaparèixer, és una decisió de
producte a part (i `UNISEX_ADULT` té 1 size-system lligat).

**B3 — 11 llocs del front resolen `model_wizard.target_<codi>` pel seu compte.** Són
one-liners de lectura (breadcrumbs, resums «target · construcció · fit», un `<option>`):
`ModelSheet.jsx:953` · `SizeSetCard.jsx:44` · `SizeSetDetail.jsx:115` · `ModelWizard.jsx:630,712`
· `SizeMapSetup.jsx:526,896` · `GradingRuleSets.jsx:415` · `RuleSetPicker.jsx:157` ·
`EditorHeader.jsx:25` · `RuleSetCard.jsx:53`. **Funcionen correctament** (mateix namespace, noms
nous), i no han de portar franja perquè són resums d'una línia. Però no passen per
`targetLabel()`. Scope creep vist i **anotat, no tocat** (CLAUDE.md).

**B4 — Cosmètica: dins d'una mateixa fila, els xips amb franja són més alts que els d'adult.**
Es veu a `ca-wizard.png`. Es resol amb un `alignItems: 'stretch'` al contenidor, però llavors
els adults queden amb un buit sota. No ho he tocat: és criteri teu.

---

## 8. Què queda per fer (tu, amb tu present)

1. `git push origin dev` — **no l'he fet**: CLAUDE.md diu que els pushes els fas tu.
2. Merge `dev` → `main`.
3. A PROD, i **en aquest ordre**: desplegar codi → `migrate_schemas` → `manage.py
   rename_targets_p0b` (mira el dry-run primer) → `--apply`.
   Si el codi arribés **abans** que el rename de dades, el front demanaria `KID_BOY` a una BD
   que encara diu `BOY` i cap ruleset infantil casaria. La finestra entre els dos passos és
   d'incompatibilitat: fes-los seguits.
4. El command és idempotent i **atura's sol** si troba estat mixt, així que un segon `--apply`
   per si de cas és segur.
