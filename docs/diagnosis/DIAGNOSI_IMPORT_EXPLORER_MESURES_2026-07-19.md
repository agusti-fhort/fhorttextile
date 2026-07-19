# DIAGNOSI — Import Explorer no reté mesures (model L27SBB0901 / LOS-SS27-0122)

Data: 2026-07-19 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`

Abast: 1r import real post-M3. El wizard mostrava POMs i grading, però el model **no reté valors
de talla base ni deltes**. Determinar l'estat real a BD, la causa, i si el re-import és segur.
Read-only estricte: cap re-import, cap arranjament, cap esborrat. Convenció: `fitxer:línia` +
"NO EXISTEIX" = confirmat absent.

---

## Resum executiu

**El model SÍ té 20 files BaseMeasurement, però totes amb `base_value_cm = NULL`** (l'estructura —
quins POMs, toleràncies, nom_fitxa— va persistir; els VALORS, no). Hi ha **DOS defectes
independents**, tots dos reals:

1. **DEFECTE PRINCIPAL (viola la llei de sobirania de mesures) — rollback per decisió de grading.**
   Tot el confirm viu en **un sol `transaction.atomic()`** (`extraction_views.py:1692`). Les
   BaseMeasurement s'escriuen a `:1779`, **abans** del bloc de grading (`:1814`). Dues sortides del
   grading —`container_ambigu` (`:1856`) i `container_absent`/no_container (`:1865`)— criden
   `transaction.set_rollback(True)` i retornen 409. Com que comparteixen l'atomic, **fan rollback de
   les mesures ja escrites**. És el "1r intent fallit": confirm sense `container_choice` → 409 "Vols
   crear el contenidor?" → **0 mesures desades**.

2. **DEFECTE SECUNDARI (commit amb valors buits) — desalineació d'etiqueta de talla base.** El model
   parla en etiquetes-tenant **zero-padded** (`03/06`, `06/09`, `09/12`…); els valors importats van
   quedar indexats en etiquetes-document **sense padding** (`3/6`, `6/9`, `9/12`…). A `:1764`
   `base_val = valors.get(pid, {}).get(base_size)` amb `base_size='03/06'` no troba res → `None` per
   a **tots** els POMs. És el "2n intent que va importar bé": commit OK, `n_bm=20`, però
   `base_value_cm=NULL` a tot arreu. La normalització que ho arreglaria (`canonical_size_label`)
   **NO col·lapsa `3/6`≡`03/06`** i, a més, només s'aplicaria en una reconciliació perfecta (100%),
   que aquest cas (match 50%) es va saltar.

**El re-import és transaccionalment segur** (idempotent, sense residus), **però no resoldrà els
valors** fins que es corregeixi la normalització d'etiquetes (àmbit F2): tornaria a deixar
`base_value_cm=NULL` perquè la base seguirà sent `03/06` i els valors seguiran indexats a `3/6`.

---

## §1 — Estat real del model a BD (schema `fhort`)

`Model` id=**396**, `codi_client='L27SBB0901'`, `codi_intern='LOS-SS27-0122'`, `customer=6` (LOS),
**`estat='Nou'`**, `target='TODDLER_BOY'`, `size_system='BABY_LOS_01'` (id 63), `garment_type_item=59`.

| Element | Valor real | Esperat si tot anés bé |
|---|---|---|
| **BaseMeasurement** | **20 files, TOTES `base_value_cm=NULL`** (origen `IMPORTED`, `is_active=True`, creades **17:28:38**) | ~24 POMs amb valor a talla base |
| `model.grading_rule_set` | **NULL** (cap contenidor per a la cel·la) | — |
| ModelGradingRule residents | **0** | — |
| ModelGradingOverride | **0** | — |
| MeasurementChangeLog | **0** | — |
| GradingVersion / GradedSpec (per model) | sense FK `model` directe · no censat per aquesta via | — |
| `base_size_label` | **`'03/06'`** | ha de casar amb el run dels valors |
| `size_run_model` | `'03/06·06/09·09/12·12/18·18/24·24/36'` (tenant, zero-padded) | — |

**FET clau:** les 20 files són d'**una sola escriptura** (totes `created_at=17:28:38`, = la sessió 57
CONFIRMAT). No hi ha residu d'escriptura del 1r intent (coherent amb el rollback del DEFECTE 1). Les
20 (no 24) surten del matching: 2 POMs sense match al catàleg + 2 col·lisions many-to-one no
auto-vinculades (vegeu §2), no és un altre bug.

## §2 — Les sessions d'import (5 per al model 396)

| Sessió | estat | creada→actualitzada | decisió/observació |
|---|---|---|---|
| 54 | POMS | 17:07→17:09 | extracció IA; 5 POMs many-to-one sense vincular |
| 55 | POMS | 17:12→17:13 | íd.; 23 poms_extrets |
| 56 | **MESURES** | 17:20→17:24 | va quedar a MESURES (confirm no completat → coherent amb 409 rollback del 1r intent) |
| **57** | **CONFIRMAT** | 17:25→**17:28:38** | **el commit real**: `container_choice='no_container'`, 20 poms, 120 valors |
| 58 | CRIBRATGE | 17:35 | nova sessió, 0 poms (reobertura posterior) |

**Sessió 57 — la que va gravar** (`run_conciliat.estat='RESOLT'`, `sistema='age_months'`):
- `resultat.valors_mode = 'absoluts'`; `resultat.mesures` = **120 entrades** (20 POMs × 6 talles),
  indexades per `talla_label` **`['3/6','6/9','9/12','12/18','18/24','24/36']`** (sense padding).
  Ex.: `{"valor":21.5,"talla_label":"6/9","pom_master_id":685}`.
- **Avisos decisius** (24 parells idèntics, un per POM):
  - `"Size system no reconciliat automàticament (match 50% per target 'TODDLER_BOY'): es manté la
    classificació manual."` → la reconciliació NO va ser perfecta → **no es va remapejar cap
    etiqueta** (vegeu §3, branca `:1707`).
  - `"POM C.4: Talla base '03/06' no és al run de talles."` (i C.1, D.11-M79, HI PA, T.1, T.2, …
    TOTS els POMs) → la talla base `03/06` no existeix entre les etiquetes dels valors (`3/6`…).
  - `"POM …: grading no detectat; regla omesa."` + `"Cap regla de grading derivada dels valors."`

**Contrast d'etiquetes (l'arrel del DEFECTE 2):**
- `BABY_LOS_01` SizeDefinition (ordre): **`03/06`**, `06/09`, `09/12`, `12/18`, `18/24`, `24/36`.
- Valors de la sessió 57: `3/6`, `6/9`, `9/12`, `12/18`, `18/24`, `24/36`.
- Les **tres primeres** difereixen només pel zero-padding (`03/06`↔`3/6`, `06/09`↔`6/9`,
  `09/12`↔`9/12`); les tres últimes casen. La **talla base és `03/06`** → no casa amb cap valor.

## §3 — Traça del codi (`fhort/models_app/extraction_views.py`)

Vista de confirm: `import_session_confirmar_view` (`:1645`), tot dins **un únic**
`with transaction.atomic():` (`:1692`). Ordre: reconciliació talles (`:1693-1734`) → `base_size`
(`:1737`) → deltes→absoluts (`:1744-1751`) → **DELETE buides** (`:1754`) → **CREATE BaseMeasurement**
(`:1759-1783`) → identificador SF (`:1804`) → **BLOC GRADING** (`:1814-1993`) → SizeFitting/PDF/estat
(`:1995-2048`).

### DEFECTE 1 — el grading pot fer rollback de les mesures (llei violada)
Les mesures s'escriuen a `:1779` (`BaseMeasurement.objects.update_or_create(...)`), **abans** del
grading. Després, **dins el mateix atomic**:
- `:1855-1857` — `if res_cont['motiu']=='ambiguous': transaction.set_rollback(True); return 409`.
- `:1864-1876` — `if container is None and container_choice not in ('create','no_container'):
  transaction.set_rollback(True); return 409 (container_absent, "Vols crear el contenidor?")`.

`set_rollback(True)` marca l'atomic exterior (`:1692`): en sortir el `with`, **es descarten les
BaseMeasurement de `:1779` i el DELETE de `:1754`**. Cap mesura sobreviu → viola la llei "les mesures
són sobirania del MODEL i s'escriuen SEMPRE". A més, les crides `derive_rules_from_fitxa` (`:1829`),
`resolve_grading_container` (`:1840`) i `classifica_fitxa_vs_contenidor` (`:1881`) queden FORA del
`try/except` intern (que comença a `:1888`): si llancessin, també farien rollback de les mesures
(capturen `TypeError/ValueError` internament, així que és improbable, però estan fora de la xarxa).
El `try/except` de `:1888-1992` SÍ protegeix l'aplicació de regles (restaura i continua, no fa
rollback) — el problema són **només** els dos `set_rollback` de `:1856` i `:1865`.

### DEFECTE 2 — `base_val=None` per etiqueta base desalineada (silenciós)
`:1764` `base_val = valors.get(pid, {}).get(base_size)` amb `base_size = model.base_size_label`
(`:1737`) = `'03/06'`, i `valors` indexat per les etiquetes-document (`'3/6'`…). Resultat: `None`
per a tots. El remapatge d'etiquetes que ho evitaria viu a `:1705-1726`, però **només s'executa si el
match és perfecte**: `if mr.ok and mr.score == 1.0 and mr.base_ok:` (`:1707`). Aquest cas (match 50%)
cau a l'`else` (`:1727`), que **només afegeix un avís tou** i deixa `base_size` i les claus de
`valors` en llengües diferents. I encara més: el normalitzador `canonical_size_label` (`:1715,:1718`)
**NO col·lapsa el zero-padding** — verificat: `canonical_size_label('3/6') != canonical_size_label
('03/06')` → fins i tot amb match perfecte el remapatge no alinearia `3/6`→`03/06`. Cap `raise` per
desalineació base↔size_system: el mal és **silenciós** (`base_val=None`), no una excepció (Q5
confirmada: NO EXISTEIX validació que abortí).

**Nota:** l'endpoint informa `'base_measurements': n_bm` comptant **files creades** (`:1783`), no
valors no-nuls → per això el 2n intent "importa OK" tot i deixar 20 valors buits.

## §4 — Report: estat · causa · seguretat del re-import

- **Estat:** model 396 amb 20 BaseMeasurement estructurals però **0 valors** (`base_value_cm=NULL`),
  sense contenidor (`grading_rule_set=NULL`), sense regles/overrides/changelog. El commit va ser la
  sessió 57 (no_container). El 1r intent (sessió 56, MESURES) va quedar sense confirmar — coherent
  amb el 409+rollback del DEFECTE 1.
- **Causa probable (doble):**
  1. **DEFECTE 2 (el que explica els NULL committats):** etiqueta de talla base `03/06` (tenant,
     zero-padded) vs valors indexats a `3/6` (document) → `base_val=None`. Àmbit **F2** (normalització
     d'etiquetes). El remap de `:1707` és condicionat a match perfecte i `canonical_size_label` no
     col·lapsa el padding.
  2. **DEFECTE 1 (latent, més greu, camí M3):** `set_rollback(True)` a `:1856`/`:1865` fa rollback de
     les mesures escrites a `:1779` quan el grading retorna 409 (ambigu / contenidor absent). Viola
     la sobirania de mesures. En aquest model no és el que va deixar els NULL (el 2n intent va fer
     no_container → commit), però és el que va buidar el 1r intent i buidaria qualsevol confirm que
     topi amb el 409 sense triar create/no_container.
- **Re-import segur?** **Sí, transaccionalment.** El confirm és atòmic (`:1692`); les
  BaseMeasurement s'escriuen amb `update_or_create` per `(model, pom)` (`:1779`, idempotent) i el
  DELETE de `:1754` només elimina files `base_value_cm__isnull=True` (les 20 buides actuals) abans de
  recrear. No hi ha risc de duplicats ni de residu orfe. **PERÒ** un re-import tal qual **tornarà a
  deixar `base_value_cm=NULL`** mentre la base sigui `03/06` i els valors `3/6` (DEFECTE 2 sense
  resoldre). Perquè el re-import ompli valors cal, primer, **corregir F2** (normalitzar etiquetes /
  aplicar el remap independentment del score, i estendre `canonical_size_label` perquè col·lapsi el
  zero-padding dels rangs d'edat) i, en paral·lel, **treure les mesures del rollback del grading**
  (DEFECTE 1): escriure-les en un atomic propi que faci commit abans del bloc de grading, o impedir
  que el grading cridi `set_rollback` sobre l'atomic que conté les mesures.

## TAULA de defectes (per al CTO)

| # | Defecte | Ancoratge | Efecte | Àmbit |
|---|---|---|---|---|
| D1 | Grading fa rollback de mesures ja escrites | `extraction_views.py:1856`, `:1865` (`set_rollback` dins l'atomic de `:1692`, mesures a `:1779`) | 409 container_absent/ambigu → **0 mesures** (viola sobirania) | camí M3 (fix: atomic propi de mesures / commit abans del grading) |
| D2 | Etiqueta talla base desalineada → `base_val=None` | `:1764` (`base_size='03/06'` vs valors `'3/6'`); remap condicionat a `:1707`; `canonical_size_label` no col·lapsa padding (`:1715,:1718`) | commit OK però `base_value_cm=NULL` a tots els POMs | F2 (normalització etiquetes) |
| D3 | `n_bm` compta files, no valors | `:1783`/`:2055` | "importa OK" enganyós amb 0 valors | menor (senyal a l'usuari) |
| — | 20 POMs (no 24) | avisos sessió 57 (2 sense match + 2 col·lisions many-to-one) | menys POMs confirmats | esperat, no bug |

---

*Read-only: cap escriptura fora d'aquest doc. Cap re-import, cap arranjament. Les correccions D1/D2
són decisió del CTO (Patró C).*
