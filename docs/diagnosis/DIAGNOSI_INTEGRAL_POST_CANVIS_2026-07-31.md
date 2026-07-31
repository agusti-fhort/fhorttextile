# DIAGNOSI INTEGRAL POST-CANVIS — 2026-07-31

> **Read-only** llevat d'un model de prova propi (`QA-DIAG-0001`, id **1303**), llistat al final
> per esborrar. Cap model real tocat. Tots els canvis d'estat provocats són a §0.
> Tram analitzat: `42f2d60b..991cd7f7` (35 commits) sobre `dev` local, cap pushat.

---

## RESUM EXECUTIU

**Res del que els sprints han tocat ha trencat tasques ni fittings.** El codi de `tasks/`,
`planning/`, `fitting/services.py` i `models_app/services_size_check.py` té **zero diff** al
tram: el risc no era de codi compartit sinó de *payloads consumits*, i allà és on ha aparegut
l'únic defecte real.

**1 regressió confirmada, de presentació, en 4 superfícies de paper**: el BATEIG del POM (el
nom i la descripció que el tècnic edita al model) **no arriba a cap taula de la fitxa**. El
panell de cotes sí que l'honora. Això trenca la regla d'or que l'Agus va enunciar: *el mateix
nom a Mesures, al panell de cotes i a cada taula de paper*.

**La cadena de graduació nova funciona end-to-end**, verificada amb dades reals: model net →
proposta → acceptar (35 regles) → propagar → **12 GradedSpec** → Escalat les pinta.

**La capa (C1, 4 commits no autoritzats)**: **cap consumidor la llegeix**. És esquema pur i
inert. Revertir-la és mecànic i acotat (§T5).

| | |
|---|---|
| Regressions confirmades | **1** (bateig → taules de paper, 4 superfícies) |
| Riscos de UX trobats | **2** (missatge del 400 en la represa · cron absent) |
| Verificat VERD | tasques · fittings · size check · cadena de graduació · capa inert |

---

## §0 · CANVIS D'ESTAT QUE HE PROVOCAT (declarats)

| Què | On | Estat |
|---|---|---|
| `POST open-task/` disparat per la SPA en obrir Mesures | **model 1302** (d'Agus) | tasca **332 → `Paused`**. Benigne i reversible des de la UI. |
| Model de prova creat | `QA-DIAG-0001` **id 1303** | **PER ESBORRAR** (té 4 mesures base, 35 regles residents, 1 SizeFitting, 12 GradedSpec) |
| Bateig de prova | 1302 i 1303 | **desfet i verificat per SQL** (0 files batejades) |

---

## §T6 · VEREDICTE

### Regressions

#### R1 — El bateig del POM no arriba a CAP taula de la fitxa ⚠️ CONFIRMADA
**Símptoma**: rebateges un POM a Mesures (nom EN + descripció local). El **panell de cotes**
ensenya el nom nou; **les quatre taules de paper segueixen imprimint el del catàleg**.

**Causa**, superfície a superfície:

| Taula | Payload que la nodreix | ¿El payload porta el bateig? | Expressió que pinta el nom | Mida del fix |
|---|---|---|---|---|
| `base_measures` | `models/<id>/base-measurements/` | **SÍ** (`wizard_views.py:378`) | [TechSheetEditor.jsx:4765](../../frontend/src/pages/TechSheetEditor.jsx#L4765) `{text: bm.nom_en \|\| …, sub: bm.nom_ca}` | **XS** — front, 1 expressió |
| `T1a` | `models/<id>/base-measurements/` | **SÍ** | [TechSheetEditor.jsx:4835](../../frontend/src/pages/TechSheetEditor.jsx#L4835) `{text: rule?.pom_nom_en \|\| bm.nom_en \|\| …}` | **XS** — front, 1 expressió |
| `T1b` (grading) | `fitting/<sf>/graded-table/` | **NO** | [TechSheetEditor.jsx:4899](../../frontend/src/pages/TechSheetEditor.jsx#L4899) `{text: row.nom_en, sub: row.nom_ca}` | **S** — backend (2 camps) + front |
| `fitting_history` (Repàs) | `fitting/model/<id>/repas/` | **NO** | [TechSheetEditor.jsx:4974](../../frontend/src/pages/TechSheetEditor.jsx#L4974) `{text: row.nom_en, sub: row.nom_local}` | **S** — backend (2 camps) + front |

**Prova amb dades reals** (model 1303, POM `COL H CB` batejat com a `QA BAPTISED NAME`):
```
base-measurements  → nom_canonic_model:'QA BAPTISED NAME'  nom_traduit_model:'QA descripció batejada'   ← hi és
T1b (graded-table) → claus de nom: ['abbreviation','codi','nom_ca','nom_en','ref']
                     valors: nom_en='Collar height (CB stand)'  ← el catàleg vell
                     PORTA el bateig? False
```

El contraexemple que tanca el diagnòstic: [TechSheetEditor.jsx:6618-6619](../../frontend/src/pages/TechSheetEditor.jsx#L6618-L6619)
—el panell de cotes— **sí** que fa `bm.nom_traduit_model || bm.nom_ca` i `bm.nom_canonic_model || bm.nom_en`.
O sigui que el criteri correcte ja és escrit al mateix fitxer; simplement no s'ha propagat a
les taules.

**Fix total estimat**: 4 expressions al front + 2 camps a 2 payloads del backend. **Mig matí**,
sense decisions de domini pendents.

#### R2 — La cadena de nomenclatura CURTA encara divergeix (deute conegut, ara mesurat)
`utils/nomenclaturaPom.js` és el resolutor únic declarat (`nom_fitxa → client_alias →
pom_code_global → codi_client`) i **només el consumeix `base_measures`**. Divergeixen:
- **T1a** ([:4832](../../frontend/src/pages/TechSheetEditor.jsx#L4832)): `bm.nom_fitxa || bm.pom_abbreviation` — es salta l'àlies del client.
- **T1b** ([:4898](../../frontend/src/pages/TechSheetEditor.jsx#L4898)): `row.ref || row.abbreviation || row.codi`.
- **cotes** (`cotaLabelDe`, [:276](../../frontend/src/pages/TechSheetEditor.jsx#L276)): `nom_fitxa || codi_client || pom_code_global` — posa el codi de la casa **abans** del canònic.

El propi mòdul ja ho documenta com a «fix a part i EN CURS». **Mida: S**, i convé fer-lo
alhora que R1 (mateixes 4 expressions).

### Riscos de UX (no regressions)

- **U1 · La represa de Propagar pot acabar en el toast genèric.** Verificat: si el ruleset
  acceptat no cobreix cap POM del model, `generate_grading_view` retorna **400 amb un missatge
  excel·lent** (*«cap de les 4 mesures base té regla de grading…»*), però el front el cau al
  `.catch` genèric `grading_propagate.err`. Just després d'«Acceptar la graduació», l'usuari
  veuria «No s'ha pogut propagar» sense saber per què. **Fix XS**: ensenyar
  `e.response.data.error` com ja fa la franja de Graduació.
- **U2 · `pausa_tasques_oblidades` segueix sense cron.** La comanda existeix
  (`fhort/tasks/management/commands/`), però no hi ha cap entrada ni a `crontab -l` ni a
  `/etc/cron.d/`. Deute ja anotat el 27/07; **segueix obert**. Avui no fa mal (0 tasques
  `InProgress` de més de 2 h, 0 timers oberts), però el guard no existeix a la pràctica.

### Verificat VERD

| Àrea | Evidència |
|---|---|
| **Tasques** — codi | `backend/fhort/tasks/` i `planning/`: **0 línies de diff** al tram |
| **Tasques** — estat viu | 55 Pending · 45 Paused · 13 Done · **0 InProgress encallades >2 h** · **0 timers oberts** |
| **`pom_task_done`** | `serializers.py:271-278` intacte; llegeix `ModelTask(code='pom', status='Done').exists()` — l'estat del MODEL, no una fila d'una llista. El gate del front (`ModelSheet.jsx:170-172`) hi segueix lligat |
| **`task_id` ↔ pantalla** | `ModelSheet.jsx:107,188,287` intacte |
| **Motor de grading** | `pom/services.py` i `fitting/services.py`: **0 diff**. L'únic canvi és `grading_utils.py` (+73, FIX-STEP, ja a PROD) |
| **`resolve_size_check`** | `models_app/services_size_check.py`: **0 diff** |
| **FIX-3 (size check completa línies)** | commit `5a88ce77`, **anterior** al tram → ja a staging |
| **Calendari / convocatòria** | `planning/views.py:368-370` (partició C4) intacte; `planning/` sense diff → la regressió G7 **no pot haver tornat** |
| **Cadena de graduació** | model 1303: net → `te_regles=False` → proposta `FIXED` amb `?proposta=1` → acceptar **35 regles** → propagar **200** → **12 GradedSpec** → Escalat les pinta |
| **P4 (Mesures neta)** | sense `?proposta`, les files surten amb `logica=None` encara que l'item porti ruleset ✓ |
| **La capa** | 0 files amb `capa<>'exterior'` · 9 comportes a `fhort`, 9 a `los`, 2 a `public` · 6 capes sembrades |

### Les 3 coses que hauries de mirar amb els teus ulls

1. **R1 al natural**: bateja un POM a Mesures i insereix `base_measures` i `T1b` a la fitxa del
   mateix model. Has de veure el nom **vell** al paper i el **nou** al panell de cotes. És la
   regla d'or trencada, i és el que més et pot mossegar en un document que surt del taller.
2. **El model 1302** («Test Agus»): la seva tasca 332 ha quedat `Paused` per la meva QA, i el
   model segueix **verge** (POMs materialitzats, cap valor). Confirma que és l'estat que
   esperaves.
3. **La decisió sobre la capa** (§T5): és inert i reversible avui; cada setmana que passi amb
   més migracions a sobre, el revert és més car.

---

## §T5 · IMPACTE DE LA CAPA (els 4 commits C1 — **marcats a part**)

`e4165fb9` · `38be545d` · `1d2c6e2a` · `418bb3c5` + `07c28caa` (test).

**Què canvien de debò**
- **Esquema**: columna `capa` CharField(20) default `'exterior'` + índex a **8 taules**
  (`BaseMeasurement`, `MeasurementChangeLog`, `ModelGradingOverride`, `SizeCheckLine`,
  `POMPlacement`, `GradedSpec`, `PieceFittingLine`, `GarmentPOMMap`, `ItemBaseMeasurement`).
- **Unicitats**: 8 claus úniques reconstruïdes amb `capa` (estrictament més permissives).
- **Comportes**: 9 `CHECK (capa='exterior')` per schema de tenant, 2 a `public` (**20 en total**).
- **Catàleg nou**: taula `pom_measurementlayer` amb **6 files** a cada schema.
- **10 migracions** aplicades.

**¿Algun flux de T1-T4 hi passa?** **No.** `grep` de `\.capa\b|capa=` a tot `fhort/` fora de
migracions, models i tests: **zero resultats**. Cap serializer l'exposa (`/api/schema/` no en
té ni rastre), cap vista la filtra, el motor no la llegeix. Les taules de T1-T4 hi passen
*físicament* (llegeixen files que ara tenen una columna més) però **cap codi la consulta**.

**Si es revertís, què s'hauria de desfer**
1. `migrate models_app 0069` · `fitting 0016` · `pom 0051` (revers net: les migracions són
   `AddField`/`AlterUniqueTogether`/`AddConstraint`, totes reversibles).
2. `git revert` dels 5 commits (models + tests). El test `test_capa_comporta_c1.py` se'n va sencer.
3. `DROP TABLE pom_measurementlayer` als 3 schemas (o deixar-la: és inert i no la referencia cap FK).
4. **Res més.** Cap dada d'usuari, cap comportament, cap payload depèn de la capa.

**Cost de no revertir-la ara**: nul avui; creix amb cada migració que s'apili al damunt, perquè
el revers deixa de ser el final de la pila.

---

## §T1 · TASQUES — detall

- **Kanban / mutex / heartbeat**: cap codi tocat. Estat viu sa (§T6). El `POST open-task/` és
  MUTANT (obre `TimerEntrada` + `TaskTransition`) i es dispara **sol** en entrar a Mesures amb
  `mode=entry` — és el que va moure la tasca 332. Comportament preexistent, no regressió.
- **`pom_task_done` amb el wizard nou**: el gate no depèn del wizard sinó de l'existència d'una
  `ModelTask` de tipus `pom` en `Done`. `materialitzar-poms` (silenciós) no toca tasques, o
  sigui que **no pot obrir ni tancar el gate per efecte secundari**. Verificat al 1302: model
  verge, tasca `Paused`, i la pantalla ofereix la gènesi — coherent.
- **Bulk i individual**: `tasks/` sense diff; `task_id` a la URL segueix lligant tasca↔pantalla.

## §T2 · FITTINGS — detall

- **`FittingSession` / `resolve_size_check` / `GradingVersion` / segell**: **0 diff**. El motor
  no s'ha tocat, verificat per `git diff --stat` sobre `pom/services.py`, `fitting/services.py`
  i `services_size_check.py`.
- **Calendari**: `planning/` sense diff → la partició per convocatòria (C4) és la mateixa.
- **Repàs de fittings**: la pantalla funciona; el seu payload (`fitting/model/<id>/repas/`)
  **no porta el bateig** → R1. El criteri MANUAL-només-remesura viu a `repas_views.py`, sense
  canvis al tram.
- **Size check**: FIX-3 ja és a staging (`5a88ce77`, anterior al tram).

## §T3 · CADENA DE GRADUACIÓ — detall

Executada sobre el model **1303** amb POMs que sí que són al ruleset del catàleg (84):

```
1. te_regles inicial ................ False
2. propagar sense regla ............. 400  «El model no té regles de grading»
3. Mesures (sense ?proposta) ........ logica=None            ← P4 respectat
4. Graduació (?proposta=1) .......... logica=FIXED           ← la proposta hi és
5. acceptar ......................... 200 · 35 regles residents
6. te_regles després ................ True
7. propagar ......................... 200 · graded_count=12
8. GradedSpec ....................... 12
9. Escalat .......................... logica=FIXED           ← ara sí
```

**Nota de fixture** (no és un defecte del producte): a la primera passada, les mesures base del
model de prova eren POMs que **no** eren al ruleset, i propagar va tornar 400 amb el missatge
*«cap de les 4 mesures base té regla de grading»*. El guard fa exactament el que ha de fer i ho
diu clar — d'aquí surt U1, que és que el front no ensenya aquest missatge.

**Model vell amb regles**: `taula-mesures` sense `?proposta` retorna les regles **residents** del
model tal com sempre (comportament de `_load_grading_rules`, sense canvis). El que ha canviat és
que Mesures ja no les pinta —esperat i volgut (decisió 31/07)— i que el fallback del catàleg ja
no s'aplica si no es demana.

## §T4 · SUPERFÍCIES DE PAPER — detall

Les quatre taules s'insereixen i fan roundtrip; el defecte no és estructural sinó de
**nomenclatura** (R1 + R2). `TechSheetEditor.jsx` és el fitxer amb més moviment del tram (+674
línies, capçalera v3.3 + idioma del document), però els builders de taula no han estat tocats
per aquests sprints: la divergència de noms és **anterior** i el bateig (30/07) l'ha fet
visible en no propagar-s'hi.

---

## Fitxers de treball

- `backend/scripts_tmp/diag_t3_t4bis.py` · `diag_t3b.py` · `diag_t3c.py` — sondes d'aquesta diagnosi.
- `ops/qa/qa_mount_modelsheet.py` — fum de muntatge (comitejat el 31/07).

**Model de prova a esborrar: `QA-DIAG-0001`, id 1303.**
