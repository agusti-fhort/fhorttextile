# DIAGNOSI — Instrumentació R4 muda + desalineació d'etiquetes de talla (XXL vs 2XL)

**Data:** 2026-07-08 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
**Substrat:** `DIAGNOSI_POM_RESOLUCIO_RUN_2026-07-08.md` · instrumentació R4 (`8731d8d`) · cas BERG (LOSAN).
**Objectiu:** (1) per què el log R4 no emet; (2) per què `values_by_size` (extracció) i el run del tenant es desalineen (`XXL` vs `2XL`).

> Convenció: `fitxer:línia` relatiu a l'arrel (backend a `backend/`). **"NO EXISTEIX" = confirmat absent al codi.**

---

## 0. Resum executiu (director)

1. **R4 no emet perquè NO hi ha cap `LOGGING` a `settings.py`** i `DEBUG=False`: el logger `fhort.*`
   cau al *lastResort* de Python (llindar **WARNING**), i el `logger.info` de R4 queda per sota.
   A més, el handler `console` per defecte de Django està filtrat per `require_debug_true`. **Fix
   mínim: afegir un bloc `LOGGING` amb un `StreamHandler` i el logger `fhort` a `INFO`** (BLOC 1).
2. **La normalització d'etiquetes JA EXISTEIX** (`canonical_size_label`, bridge `XXL≡2XL`) **però el
   camí del run de client NO la fa servir.** Hi ha **TRES normalitzadors** i només un pont: el camí
   d'import de model i el *matching* usen `canonical_size_label`; `detect_grading` usa `_norm`
   (upper+strip); el motor de grading usa `_norm_label` (upper+strip) (BLOCs 2-4).
3. **La causa de la desalineació és doble i acumulativa:** (a) l'extracció del run de client es crida
   **sense `wizard_context`**, així que Opus retorna les etiquetes LITERALS del document (`XXL`), no
   les del run del tenant (`2XL`), tot i que el prompt SAP fer-ho si se li diu (BLOC 5); (b) abans de
   `detect_grading` **no es re-clau** `values_by_size` a les etiquetes del tenant (com sí fa el camí
   d'import a `extraction_views.py:1250`), i `_norm` no salva `XXL`↔`2XL` (BLOC 3).
4. **Risc de break perdut CONFIRMAT:** quan una talla queda sense valor (desalineada), `detect_grading`
   avisa i **deriva la regla amb els deltes restants**; si el break requeia en aquella talla,
   **desapareix i la regla degrada a LINEAR** en silenci de forma (només un `warning`) (BLOC 6).

**Recomanació de rumb (💡):** la normalització ha de viure **a la frontera d'extracció** (dir-li el run
al prompt → retorna etiquetes del run + `size_discrepancy`) i, com a cinturó, **re-clavar
`values_by_size` amb `canonical_size_label` abans de `detect_grading`** (reusant l'helper existent, no
un quart normalitzador). Convergir els tres normalitzadors en `canonical_size_label`.

---

## BLOC 1 — Per què el log R4 no surt a journalctl [Q1]

- **NO EXISTEIX cap `LOGGING` a `settings.py`** (`grep LOGGING fhort/settings.py` = 0 ocurrències) ni
  cap `dictConfig`/`basicConfig` al projecte. `DEBUG = os.environ.get('DEBUG','False')...`
  ([settings.py:20](../../backend/fhort/settings.py#L20)) → **False** en servei.
- **El log R4 és `logger.info`** ([size_map_views.py:416](../../backend/fhort/pom/size_map_views.py#L416),
  logger `fhort.pom.size_map_views` via `getLogger(__name__)` a `:21`).
- **Conseqüència (config per defecte de Django):** el `LOGGING` per defecte només configura els loggers
  `django`/`django.server`; el handler `console` porta el filtre `require_debug_true` → **mut amb
  DEBUG=False**. Un logger `fhort.*` sense config propaga a *root*, que **no té handler** → actua el
  `logging.lastResort` de Python, que **només emet WARNING+**. `INFO` < `WARNING` → **res**. (Un
  `logger.warning` SÍ sortiria per *lastResort*; per això `logger.error` de l'extracció sí es veu,
  `extraction_service.py:170`.)

**Veredicte BLOC 1: cal X (config).** El log és correcte; el que falta és `LOGGING`. 💡 **Fix mínim:**
```python
LOGGING = {'version':1,'disable_existing_loggers':False,
           'handlers':{'console':{'class':'logging.StreamHandler'}},
           'loggers':{'fhort':{'handlers':['console'],'level':'INFO'}}}
```
(gunicorn captura stdout/stderr → journald). Alternativa ràpida-i-lletja: pujar R4 a `logger.warning`.

---

## BLOC 2 — On viuen les etiquetes canòniques i quina normalització hi ha [Q2]

- **Les etiquetes del run viuen a `SizeDefinition.etiqueta`** (per `SizeSystem`, ordenades per `ordre`,
  [pom/models.py:323](../../backend/fhort/pom/models.py#L323)). **NO EXISTEIX un model `SizeRun`**: el
  "run" és la llista d'etiquetes de `SizeDefinition` d'un `SizeSystem`, ordenada.
- **SÍ existeix normalització d'equivalència `XXL≡2XL`:** `canonical_size_label`
  ([pom/size_labels.py:13](../../backend/fhort/pom/size_labels.py#L13)) — col·lapsa la forma X-repetida
  a numèrica (`XXL→2XL`, `XXS→2XS`, `XXXL→3XL`; `XL/XS` i les ja numèriques queden igual; la resta
  només `upper`). Comparació, **no** persistència (sempre es guarda l'etiqueta del tenant).
- **⚠️ Hi ha TRES normalitzadors, i només un fa el pont:**
  | Normalitzador | Fitxer:línia | Bridge XXL≡2XL? | On s'usa |
  |---|---|---|---|
  | `canonical_size_label` | `pom/size_labels.py:13` | **SÍ** | import de model + *matching* (`matching.py:85`, `extraction_views.py:444-449,1250`) |
  | `_norm` | `pom/grading_utils.py:9` | NO (upper+strip) | `detect_grading` (camí run de client) |
  | `_norm_label` | `pom/services.py:534` | NO (upper+strip) | motor de grading `_apply_rule`/STEP |

**Veredicte BLOC 2: la peça existeix, mal repartida.** El pont `XXL≡2XL` ja està escrit, però el
consumeixen el camí d'import i el matching — **no** el `detect_grading` del run de client ni el motor.

---

## BLOC 3 — On (no) es casen `values_by_size` amb el run [Q3]

- Al camí run-client de fitxer, el `run` es construeix de **les etiquetes del tenant**
  (`SizeDefinition.etiqueta` si hi ha `size_system_id`, [size_map_views.py:435-437](../../backend/fhort/pom/size_map_views.py#L435));
  si no, de les claus de `values`.
- **L'alineació passa DINS `detect_grading`** ([grading_utils.py:135-165](../../backend/fhort/pom/grading_utils.py#L135)):
  `run_norm = [_norm(x) …]` i `valors = {_norm(k): v …}` → casa per **`_norm` (upper+strip)**. Per tant
  `XXL` (document) vs `2XL` (run) → `'XXL' != '2XL'` → **la talla del run no rep valor** → el delta
  d'aquella talla s'omet amb `warning` (`:160-163`).
- **El camí run-client NO re-clava `values_by_size` a les etiquetes del tenant** abans de
  `detect_grading` (`_pdf_extracted_to_poms` només mapeja per `code`, manté les claus del document,
  `size_map_views.py:335`). **Contrast:** el camí d'import de model SÍ ho fa, amb un
  `_canon_to_tenant = {canonical_size_label(e): e …}` ([extraction_views.py:1250-1253](../../backend/fhort/models_app/extraction_views.py#L1250)).

**Veredicte BLOC 3: cal X.** L'alineació és per `_norm` (case-insensitive però **no** format-aware); el
run-client no aplica `canonical_size_label` ni re-clava com el camí d'import → `XXL/2XL` es desalineen.

---

## BLOC 4 — Radi de consumidors d'etiquetes de talla [Q4]

- **Motor de grading `_apply_rule`** ([services.py:584-585,614,623](../../backend/fhort/pom/services.py#L584)):
  usa `_norm_label` per alinear el run **i per localitzar el break** (`tl in norm`). Si el
  `talla_break_label` d'una regla i el run difereixen de format (`XXL` vs `2XL`), **el break no es
  troba** i el càlcul degrada. Mateix forat que BLOC 3, al motor.
- **`GradedSpec` / size-check / fitting / PDF:** consumeixen l'etiqueta **ja emmagatzemada** del
  tenant (`SizeDefinition.etiqueta` / `size_label`), que és **coherent** internament. El problema NO
  és intern: és a la **frontera document→tenant** (extracció), on entren etiquetes alienes (`XXL`).
- **On hauria de viure la normalització (per no duplicar-la):** una sola funció
  (`canonical_size_label`) a la frontera d'entrada; `detect_grading` i `_apply_rule` haurien de
  **convergir-hi** (avui tenen `_norm`/`_norm_label` propis, dèbils).

**Veredicte BLOC 4: convergir.** La desalineació mossega a la frontera d'extracció i, secundàriament,
a la localització de break del motor. Un sol normalitzador (`canonical_size_label`), no tres.

---

## BLOC 5 — El prompt: literal o normalitzat? Se li pot dir el run? [Q5]

- **El prompt DEMANA etiquetes LITERALS del document** per defecte: l'esquema retorna
  `values_by_size` amb les etiquetes tal com surten (`{"S":…,"M":…}`,
  [extraction_service.py:53](../../backend/fhort/models_app/extraction_service.py#L53)).
- **PERÒ se li pot dir el run:** `extract_from_file(..., wizard_context)` accepta `size_run`/`base_size`
  ([extraction_service.py:129-135](../../backend/fhort/models_app/extraction_service.py#L129)) i
  `build_extraction_prompt` els injecta amb instruccions explícites:
  **"Map the grading table to the sizes: {size_run}"** i **"Flag any discrepancy … in
  `size_discrepancy`"** ([extraction_prompt.py:52,54-56](../../backend/fhort/models_app/extraction_prompt.py#L52)).
- **⚠️ El camí run-client NO passa `wizard_context`:** `extract_from_file(file_bytes, f.name)`
  ([size_map_views.py:410](../../backend/fhort/pom/size_map_views.py#L410)) — sense el run que el
  wizard JA coneix. Per tant Opus retorna les etiquetes del document (`XXL`), no les del run (`2XL`).

**Veredicte BLOC 5: cal X (fàcil).** El mecanisme per obtenir etiquetes del run (i un
`size_discrepancy` explícit) ja existeix; només cal **passar el `wizard_context` amb `size_run`** a
`extract_from_file` des del run-client.

---

## BLOC 6 — Break perdut quan es descarta una talla [Q6]

- **Confirmat.** A `detect_grading`, si falta el valor d'una talla → `warning` + **`continue`** (el
  delta d'aquella talla s'omet, [grading_utils.py:160-163](../../backend/fhort/pom/grading_utils.py#L160)).
- La decisió LINEAR/FIXED/STEP i el **compte de breaks (`nb`)** es fan **només amb els deltes
  supervivents** (`:167-188`). Si el break requeia a la talla descartada, **els dos deltes que la
  toquen s'ometen tots dos** → la transició de pas desapareix → `nb=0` → **derivat com a LINEAR
  uniforme** (o break mal posicionat). `derive_break_fields` treballa sobre `valors_step` (deltes
  supervivents) → **no recupera** el break perdut.

**Veredicte BLOC 6: risc real.** Una talla desalineada que porti un break degrada la regla a LINEAR
**sense error dur** (només un `warning` que, a més, avui NO s'emet — BLOC 1). Doble silenci.

---

## TAULA FINAL — EXISTEIX / FALTA / DIFERENT

| # | Element | Estat | Evidència |
|---|---|---|---|
| A | `LOGGING` a settings (emissió R4) | **FALTA** (NO EXISTEIX) | `settings.py` sense LOGGING |
| B | Normalitzador `XXL≡2XL` (`canonical_size_label`) | **EXISTEIX** | `size_labels.py:13` |
| C | Ús de `canonical_size_label` al run-client / `detect_grading` | **FALTA** | `grading_utils.py:135` usa `_norm` |
| D | Re-clau `values_by_size`→tenant al run-client | **FALTA** (sí al camí d'import) | `extraction_views.py:1250` vs run-client |
| E | Passar `size_run` a l'extracció (run-client) | **FALTA** | `size_map_views.py:410` sense `wizard_context` |
| F | Prompt sap mapar al run + `size_discrepancy` | **EXISTEIX** (no utilitzat al run-client) | `extraction_prompt.py:52-56` |
| G | Normalitzadors convergits | **DIFERENT** (3: canonical / `_norm` / `_norm_label`) | BLOC 2 |
| H | Break preservat si es descarta una talla | **FALTA** (degrada a LINEAR) | `grading_utils.py:160-188` |

---

## VEREDICTE FINAL — causa, on ha de viure la normalització, risc de break (💡 PROPOSTA, a validar)

### Causa
- **R4 mut:** cap `LOGGING` + `DEBUG=False` → `logger.info` per sota del *lastResort* (WARNING).
- **Desalineació `XXL/2XL`:** el run-client (a) **no diu el run a l'extractor** (retorna etiquetes del
  document) i (b) **no re-clava `values_by_size`** a les etiquetes del tenant abans de `detect_grading`
  (que casa per `_norm`, no per `canonical_size_label`). El pont ja existeix, però no s'aplica aquí.

### On ha de viure la normalització (per capes, sense duplicar)
1. **A la frontera d'extracció (primària):** passar `wizard_context` amb `size_run`+`base_size` a
   `extract_from_file` des del run-client → Opus retorna etiquetes del RUN i ompl `size_discrepancy`.
   És el punt més net: l'alineació la fa qui coneix el run.
2. **Cinturó determinista (secundària):** abans de `detect_grading`, **re-clavar `values_by_size` a
   les etiquetes del tenant amb `canonical_size_label`** (reusant el patró `_canon_to_tenant` del camí
   d'import), NO un quart normalitzador. Cobreix el cas que la IA no faci cas del run.
3. **Convergència:** `detect_grading._norm` i `_apply_rule._norm_label` haurien d'usar
   `canonical_size_label` (o delegar-hi) perquè el break es localitzi encara que el format difereixi.
   ⚠️ **Radi:** tocar el motor (`services.py`) exigeix la seva pròpia diagnosi de paritat (zona
   intocable per defecte) — fer-ho a part.

### Risc de break perdut
**Real i silenciós.** Una talla desalineada que porti un break → regla derivada com LINEAR, amb només
un `warning` (avui ni emès). Mentre no s'alineïn les etiquetes, el break de talles altes (`XXL/2XL`,
justament on solen viure els breaks) és el més exposat. **Mitigació immediata:** arreglar el logging
(veure els `warning`) + alinear a la frontera abans de confiar en cap regla derivada d'un fitxer.

### Decisions a elevar (CTO)
1. `LOGGING`: bloc mínim a `settings.py` (recomanat) o pujar R4 a WARNING (pedaç)?
2. Normalització: fem les dues capes (prompt + re-clau) o només el re-clau determinista?
3. Convergència del motor (`_apply_rule`→`canonical_size_label`): sprint propi amb diagnosi de paritat?

## Obert / dubtós
- No s'ha reproduït en viu la resposta d'Opus amb `wizard_context` (requeriria una crida real a l'API);
  la capacitat del prompt es dedueix del text (`extraction_prompt.py:52-56`) — **PENDENT DE VERIFICAR**
  amb una extracció real un cop s'hi passi el `size_run`.
- No s'ha auditat si algun run ja persistit té regles LINEAR que en realitat tenien un break perdut per
  aquesta desalineació — caldria contrastar `values_by_size` (log R4, un cop emeti) amb les regles.
