# FIX PROD — Talles (XXL↔2XL) · Toleràncies · Base des de fitting

**Data:** 2026-07-07 · **Patró B** (backend) · branca `dev` (staging) · **SENSE push**
**Origen:** 3 problemes de PROD amb ús real (fitxa Losan "BERG") diagnosticats a la DIAGNOSI PATRÓ A prèvia (BLOC 1/2/3).
**Ritual:** `manage.py check` net a cada commit · `git add` selectiu · cap migració (tots els camps existien) · servei reiniciat i `/api/schema/` 200.

---

## Commits

| Commit | Bloc | Concern |
|---|---|---|
| `d3bf3c6` | B1 | Canonicalització de talles X-repetides (XXL≡2XL) a la frontera d'import |
| `b41743b` | B2 | Captura de toleràncies del document extrem a extrem |
| `df0fbd6` | B3 | Consolida la base des de fittings oberts abans de propagar grading |

---

### B1 — `d3bf3c6` canonicalització de talles

**Arrel:** XXL i 2XL són la mateixa talla però es comparaven per igualtat literal (`.strip().upper()`) → el gate `sense_desti` i `match_size_system` bloquejaven quan el document i el tenant feien servir notacions diferents. Cap capa d'àlies existia.

**Fix:**
- Helper **pur** nou `fhort/pom/size_labels.py::canonical_size_label` — col·lapsa X-repetides a numèric (XXL→2XL, XXXL→3XL, XXS→2XS); una sola X (XL/XS), numèriques (2XL) i no-alfabètiques (34, 6M, T2) queden intactes (només case-fold).
- Gate `sense_desti` (`extraction_views.py`) i `match_size_system` (`matching.py`) comparen en forma **canònica**.
- **Reconcile d'import:** quan el match és canònic, es GUARDA sempre l'etiqueta del **tenant** (SizeDefinition), remapant run+base+`valors` → el model no parla mai la notació del document. **Motor de grading no tocat** (llegeix el run internament, de forma consistent).
- `services.py`/`grading_utils.py` `_norm` **NO** tocats (evita canviar el comportament del motor amb dades existents): la canonicalització viu només a la frontera d'import.

**Verificació runtime** (SizeSystem real `ALPHA_EU_M`, tenant amb `XXL`):
```
doc run 2XL → MATCH score 1.0 · base_ok True · GATE ready True · run guardat = XXL (tenant)
CONTROL (antic, cru): unmatched=['2XL'] → bloquejaria
```

### B2 — `b41743b` toleràncies extrem a extrem

**Arrel:** el prompt demanava `tol_minus`/`tol_plus` però es perdien a `poms_extrets` (les 3 vies) i mai s'escrivien a `BaseMeasurement`; la via xlsx determinista fins i tot **descartava** expressament la columna Tol.

**Fix:**
- `_parse_excel_poms`: deixa de descartar `tol`; detecta `Tol-`/`Tol+` (o `min`/`max`/`plus`) i una sola `Tol` (→ simètrica minus=plus); llegeix per fila amb `_num`.
- Els 3 muntatges de `poms_extrets` (xlsx-determinista, PDF-Opus, xlsx-IA via Opus) conserven `tol_minus`/`tol_plus`.
- `BaseMeasurement.update_or_create`: escriu `tolerancia_minus`/`plus` **només si el document en porta** (asimètrica — contracte de Size Check `-tol_minus ≤ Δ ≤ tol_plus`); si no, no inclou les claus → `null` → fallback al catàleg (comportament actual preservat).

**Verificació runtime** (xlsx en memòria):
```
Tol-/Tol+ → tol_minus=0.5 tol_plus=0.8 (asimètrica)
'Tol' única → 0.6/0.6 (simètrica) · sense Tol → None/None
defaults inclou tolerancia_* només si presents
```

### B3 — `df0fbd6` consolida la base des de fitting en propagar (decisió b1)

**Arrel:** el motor llegeix `BaseMeasurement.base_value_cm`, però una rectificació via l'àncora de fitting (`propagar`) només escriu `PieceFittingLine.valor_real` i no consolida fins al `close` → en propagar sense tancar, es propagava sobre la base **original**.

**Decisió (Patró C, costat b1):** la rectificació ha de consolidar a base. **NO es toca el motor** (`pom/services.py`); s'afegeix un pas ABANS d'invocar-lo.

**Fix:**
- Helper nou `fitting/services.py::consolidate_base_from_fitting(pf)` — extreu la consolidació de talla base que **ja feia** el `close` (`valor_real≠teòric` → `base_value_cm`, `origen='FITTED'`, senyal F1). El `close` ara el crida (**refactor behavior-preserving**; Welford i versionat es queden al close sobre les línies consolidades).
- `generate_grading_view` (`new_version=True`, l'acte conscient de propagar): abans del motor, consolida les línies de talla base rectificades dels **fittings OBERTS** (`session.estat='Oberta'`) del model. Resposta amb `base_consolidada_des_de_fitting: N`.

**Verificació runtime** (model **QA-SC 182**, mai el golden 162; **transacció revertida — res persistit**):
```
POM 275 · base original 36.0 (origen FITTED)
→ simula fitting OBERT + valor_real rectificat 36.7
→ consolidate_base_from_fitting: 1 POM · base_value_cm=36.7 · origen=FITTED
→ MOTOR _load_base_measurements[pom]=36.7  ✓ propagaria sobre 36.7, no 36.0
POST-ROLLBACK: base=36.0 (res persistit)
```
Tests `fhort.fitting`: **12/13**. La fallada `test_regim_sense_fallback_400` és **PRE-EXISTENT** (idèntica amb i sense aquest canvi, verificat per stash).

---

## Estat final

- `manage.py check`: net als 3 commits. **Cap migració** (`makemigrations --check` → No changes).
- Servei `ftt-staging.service`: reiniciat, **active**. `curl -H "Host: staging.fhorttextile.tech" /api/schema/` → **200**.
- Doc no commitejat (ops/ untracked).

## Smokes de navegador (per a Agus)

1. **B1** — Importar una fitxa (PDF o xlsx) amb run en notació `2XL...` (o `XXL...`) contra un model amb SizeSystem en l'altra notació → l'import **ja no bloqueja** al pas de talles (gate `ready`); el model queda amb les talles en la notació del **tenant** (p. ex. `XXL`), no la del document. Revisar grading/DXF coherents.
2. **B2** — Importar una fitxa amb columna de tolerància (`Tol-`/`Tol+` o `Tol`) → obrir Size Check / graella de mesures: les toleràncies del document hi surten (no el default 0.6 del catàleg). Import sense tolerància → segueix el fallback del catàleg.
3. **B3** — Amb un fitting **obert**: rectificar el `valor_real` d'un POM de **talla base** (àncora `propagar`) SENSE tancar la peça → prémer **Propagar grading** (acte conscient) → la nova versió de grading parteix del valor **rectificat** (la columna base mostra el valor mesurat nou, no l'original); `BaseMeasurement.origen='FITTED'`. La resposta porta `base_consolidada_des_de_fitting > 0` (el frontend encara no ho pinta — Patró B backend-only).

## Límits coneguts / deute

- B1: la canonicalització cobreix formes X-repetides ↔ numèriques. Altres equivalències (p. ex. XS↔0, EU↔UK) segueixen sense àlies; el pont manual `mapeig_talles` es manté.
- B1: `_norm` de `services.py`/`grading_utils.py` (motor) NO canonicalitza — intencionat (no tocar el motor amb dades existents).
- B2: `strokeWidth`/asimetria — el model manté minus/plus separats (contracte Size Check); el "deute simètric" reportat no és al backend.
- B3: es consolida des de **totes** les línies base rectificades de fittings oberts del model; si hi hagués una sessió oberta amballada amb `valor_real` espuri, entraria. La decisió b1 assumeix "última mesura escrita = veritat".
- Test pre-existent `test_regim_sense_fallback_400` (fallava abans d'aquest run) — fora d'abast.
