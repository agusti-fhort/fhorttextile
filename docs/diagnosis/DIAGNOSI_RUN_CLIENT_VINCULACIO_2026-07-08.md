# DIAGNOSI — "Nou run de client": vinculació manual, derivació, toleràncies i valor base

**Data:** 2026-07-08 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
**Equip:** director-investigació + 3 investigadors-codi paral·lels (payload manual · derivació grading · creació-POM) + verificació a BD (fhort) + síntesi. Cap escriptura de codi, cap migració, cap restart.
**Substrat:** `DIAGNOSI_IMPORT_RUN_CLIENT_2026-07-07.md` (vigent; el fix `0ad3ecf` ja alinea l'esquema `poms`+`grading_table`).
**Cas real:** BERG.pdf → run `EU ALPHA LOS TOP KNIT REGULAR V01` (GradingRuleSet **id=111**, fhort).

> Convenció: `fitxer:línia` relatiu a l'arrel del repo. "NO EXISTEIX" = confirmat absent al codi.
> **Principi de domini (llei, donat pel CTO):** les REGLES són l'actiu portable de la graduació
> (reaplicables a un altre model); el **valor base és dada de model**. L'absència de base al run
> NO és bug per defecte.

---

## 0. Resum executiu (director)

- **La vinculació manual NO falla en bloc** — la BD ho confirma: 16 regles, moltes ben derivades
  (S.37→FIXED ✓, G.3→LINEAR ✓, BJ→LINEAR +0.40 ✓). Els símptomes són **quatre causes independents**:
- **(K.1 → FIXED sense delta):** `detect_grading` només retorna FIXED quan **tots els deltes són
  exactament 0** (determinista, sense llindar ni arrodoniment). Per tant els valors per talla de
  K.1 van arribar **constants** al detector — la fallada és **aigües amunt** (fidelitat de
  l'extracció d'aquella fila, o desalineació run↔`values_by_size`), NO un llindar del detector.
- **(J.2 vinculat però absent):** **col·lisió de mapping** — `create` fa
  `GradingRule.update_or_create(rule_set, pom)`; dues files que apunten al **mateix POMMaster**
  col·lapsen a una sola regla (l'última guanya). J.2 desapareix perquè el seu POM el reclama una altra fila.
- **(E, H.6 no vinculats i absents):** el frontend filtra `grading.filter(g => g.pom_id)` abans
  d'enviar → els no vinculats **es descarten** (amb un `window.confirm`, però sense rastre persistent).
- **(Toleràncies absents):** extretes (l'`EXTRACTION_PROMPT` les demana i `extract_from_file` les
  retorna) però **descartades** pel consumidor `_pdf_extracted_to_poms`; a més, el GradingRule **no
  té camp de tolerància** — les toleràncies són dada de **POM/model**, no de regla.
- **("Valor base —"):** **per DISSENY**, no pèrdua. `GradingRule.valor_base` es va **eliminar**; el
  valor base viu a `BaseMeasurement` (model) / `ItemBaseMeasurement` (item). El run és actiu de
  regles, no de valors. `increment_base` (el delta base) SÍ està poblat a les 16 regles.

---

## BLOC 1 — Vinculació manual: component + payload [Q1]

- **Selector de catàleg:** `catalegPoms` es carrega un cop via `poms.list({page_size:200, actiu:true})`
  ([SizeMapSetup.jsx:271-276](../../frontend/src/pages/SizeMapSetup.jsx#L271)). Per fila sense match,
  render d'un `<select>` d'existents (`:633-641`); en triar, `onChange` escriu `pom_id` (+ `pom_nom`
  cosmètic) a la fila de `gradingResults` (`:634-638`). **Només vincula a POMs existents.**
- **La fila JA porta la graduació derivada abans i amb independència del matching:** al backend,
  `detect_grading(values, run, base_size)` es crida per a TOTA fila (`size_map_views.py:417` fitxer /
  `:251` paste); `find_pom_master` només decideix `pom_id` (`:412`/`:246`). Per tant una fila
  "sense match" arriba amb `logica_detectada`/`increment`/`valors_step` **ja derivats dels seus
  propis valors**; en vincular-la, només s'hi afegeix `pom_id`.
- **Payload a `POST size-map/create/`** (`buildPayload`, `SizeMapSetup.jsx:352-386`): cada fila de
  `grading` porta **NOMÉS** `{pom_id, logica, valors_step?, increment?}` (`:353-364`). **NO viatgen**
  `values_by_size`, `base_value_cm` ni `tolerance_*`. La forma és **idèntica** per a files auto i
  manuals; l'única diferència és l'origen de `pom_id` (backend `find_pom_master` vs selecció d'usuari).

**Veredicte BLOC 1: llest (amb matís).** Viatja el mapping + la regla ja derivada; **NO** els valors
crus, ni la base, ni les toleràncies. La vinculació manual conserva la derivació que el preview va fer.

---

## BLOC 2 — Derivació de regla (LINEAR/FIXED + delta) [Q2]

- **`detect_grading(valors_per_talla, run_ordenat, base_label)`** ([grading_utils.py:116-195](../../backend/fhort/pom/grading_utils.py#L116)):
  - Calcula deltes per talla cap al veí en direcció a la base (`:147-165`). Talla amb valor absent →
    warning + `continue` (delta omès, `:160-163`).
  - Decisió NOMÉS dins `if deltas:` (`:167`): **FIXED = `all(d == 0)`** (`:179-180`); LINEAR uniforme
    (`nb==0`, `:181-182`); LINEAR+1 break (`:183-186`); STEP (`:187-188`).
  - **`valors` buit `{}` o 1 sola entrada** → deltes buits → `if deltas` fals → retorna
    **`logica=None`** (+ warning), **NO FIXED** (`:145-146,167`).
- **`derive_break_fields`** (`:198-223`): `increment_base` = primer delta del run; None només si
  `seq` buit **i** `increment is None` (camí net: STEP amb `valors_step` fora del run). Per LINEAR
  (increment present) i FIXED (increment 0.0) → `increment_base` **sempre poblat**.
- **`_norm(codi)`** (`:9-11`): `strip().upper()`; dos codis que difereixin només en majús./espais
  **col·lisionen** (última clau guanya, sense avís).
- **El `create` NO re-deriva dels valors:** usa `logica_eff = g.get('logica') or 'LINEAR'` i
  `derive_break_fields(logica_eff, g.get('increment'), g.get('valors_step'), run)`
  ([size_map_views.py:624-626](../../backend/fhort/pom/size_map_views.py#L624)). La derivació real
  passa al PREVIEW; el create només persisteix.

**Conseqüència per a K.1 (5.6→8.0, +0.3):** que surti **FIXED** exigeix deltes **tots exactament 0**
→ els valors per talla van arribar **constants**. El detector **no té llindar ni arrodoniment** que
converteixi +0.3 en 0 (compara amb BJ +0.40 i G.3 +0.50, que deriven LINEAR correctament). Per tant
la causa és **aigües amunt del detector**: (a) l'extracció va retornar `values_by_size` constant per
a K.1 (OCR d'aquella fila), o (b) desalineació entre `run` i les claus de `values_by_size` que deixa
només veïns de valor igual. **No es pot discriminar (a) vs (b) en read-only** perquè els valors
extrets **no es persisteixen** enlloc (vegeu obert/dubtós).

**Veredicte BLOC 2: cal X (instrumentar).** El detector és correcte i determinista; el problema de
K.1 és de dades d'entrada, no de llindar. Cal registrar els `values_by_size` extrets per POM per
tancar (a)/(b).

---

## BLOC 3 — Per què desapareixen files (E/J.2/H.6) [Q3]

- **E (+3.0) i H.6 (+1.0) — NO vinculats:** el frontend filtra abans d'enviar:
  **`buildPayload` `SizeMapSetup.jsx:354` `.filter(g => g.pom_id)`** → tota fila sense `pom_id` es
  descarta. Guard: `submitCreate` (`:391-397`) fa `window.confirm` llistant els no-resolts ("no es
  desaran"), però si es confirma, el filtre les elimina **sense rastre persistent**.
- **J.2 (fix 2.0) — VINCULAT però absent:** **col·lisió de mapping al backend.**
  `create` recorre `for g in grading` i fa
  **`GradingRule.update_or_create(rule_set=rule_set, pom=pom, defaults=...)`**
  ([size_map_views.py:625](../../backend/fhort/pom/size_map_views.py#L625)). La unicitat és
  `(rule_set, pom)`; si J.2 i una altra fila (auto o manual) apunten al **mateix POMMaster**, la
  segona **sobreescriu** la primera → una sola regla per aquell POM. J.2 "desapareix" perquè el seu
  POM l'ha reclamat una altra fila. (Reforçat pel `_norm` col·lisionant a l'origen, `grading_utils.py:11`.)
- El camí de FITXER té una segona via de desaparició: si `detect_grading` llança, `continue` elimina
  la fila amb avís (`size_map_views.py:416-420`).

**Veredicte BLOC 3: cal X.** Dos mecanismes: (1) descart silenciós de no-vinculats (frontend filter);
(2) **col·lisió `update_or_create(rule_set, pom)`** que perd la fila perdedora sense cap avís.

---

## BLOC 4 — Valor base: disseny o pèrdua? [Q4]

- **`GradingRule.valor_base` es va ELIMINAR** (Sprint Mesures Base per Item, P0):
  [pom/models.py:158-162](../../backend/fhort/pom/models.py#L158) — "el VALOR base de cada POM viu a
  `BaseMeasurement` (del Model) i, com a plantilla, a `ItemBaseMeasurement` (de l'Item). El grading
  no en depèn (mai es llegia per a càlcul)."
- **BD (ruleset 111):** `increment_base` està **poblat a les 16 regles** (2.00, 0.40, 3.00…; 0.00 als
  FIXED). Per tant **"Valor base —" NO és `increment_base`** (que la UI del wizard lliga a
  `SizeMapSetup.jsx:650-656`). El "—" correspon al **valor base de mesura**, que el run **no
  emmagatzema per disseny**.
- Coherent amb el **principi de domini:** el run és actiu de **regles** (portable a un altre model);
  el valor base és dada del **model**. Com que el wizard crea un **size system + ruleset** (no un
  Model), no hi ha `BaseMeasurement` receptora → el `base_value_cm` extret **no té casa en aquest
  flux, per disseny**.

**Veredicte BLOC 4: llest (DISSENY, no pèrdua).** L'absència de valor base al run és intencionada i
consistent amb la llei. (Matís: el `base_value_cm` extret es descarta a `_pdf_extracted_to_poms`;
això és correcte per al run, però vol dir que **si mai calgués** sembrar-lo a un model, aquest flux no
ho fa — decisió de producte, no bug.)

---

## BLOC 5 — Toleràncies [Q5]

- **L'`EXTRACTION_PROMPT` SÍ les demana:** `tolerance_minus`/`tolerance_plus` per POM i per fila de
  graduació ([extraction_service.py:50,53](../../backend/fhort/models_app/extraction_service.py#L50)).
  `extract_from_file` les retorna al JSON cru.
- **El consumidor les DESCARTA:** `_pdf_extracted_to_poms`
  ([size_map_views.py:315-341](../../backend/fhort/pom/size_map_views.py#L315)) només mapeja
  `code`/`description`/`values` → **`tolerance_*` es perden aquí**. Cap altre punt del flux del run
  les llegeix (`grep tolerance` a `size_map_views.py` = **NO EXISTEIX**).
- **El GradingRule no té camp de tolerància** (verificat al model). On viuen les toleràncies:
  `POMMaster.tolerancia_default_minus/plus` (catàleg, asimètric, default 0.6,
  [pom/models.py:167-168](../../backend/fhort/pom/models.py#L167)) i `BaseMeasurement.tol_minus/plus`
  (per-model, `:431-432`). Són dada de **POM/model**, no de **regla** → el run, correctament, no les
  desa; però el consumidor **no les ofereix a cap POM/model** → **es perden del tot**.
- **Deute obert (DECISIONS §5, `:286`):** "Tolerància: avui 2 valors; sempre simètrica ± → fusionar a
  1 sola columna (p.ex. ±0.6). Sprint POMs." → on HAURIEN de viure: **una sola ± al POM/model**, no al run.

**Veredicte BLOC 5: cal X (decisió + fix).** Les toleràncies s'extreuen i es llencen. Per disseny no
van al run; però haurien d'aterrar al POM (`tolerancia_default_*`) o al model (`tol_*`) — avui no ho
fan. Lligar-ho amb el col·lapse 2→1 ± del deute obert.

---

## BLOC 6 — Verificació a BD (Q6): ruleset 111

**16 GradingRules** (11 LINEAR · 5 FIXED), tots amb `increment_base` poblat, `valors_step=None`,
`increment_break=None` (cap break):

| POM (codi canònic) | lògica | incr | inc_base |
|---|---|---|---|
| A.1 · A.2 | LINEAR | 2.00 | 2.00 |
| BJ | LINEAR | 0.40 | 0.40 |
| CH · SK SW | LINEAR | 3.00 | 3.00 |
| H · SH | LINEAR | 0.80 | 0.80 |
| L.4 · NK W · SL UA | LINEAR | 0.50 | 0.50 |
| M-M79 | LINEAR | 1.50 | 1.50 |
| COL H CF · CUF H · L.5 · S1-M76 · SH DR | FIXED | 0.00 | 0.00 |

- **Els codis emmagatzemats són CANÒNICS** (`POMMaster.codi_client` del POM casat), **no els del
  document** (K.1/S.37/J.2/E/H.6). Confirma que múltiples codis de document → pocs POMs canònics
  (evidència de col·lisió/mapping).
- **"15/16 regles" (UI) vs 16 (BD):** discrepància de comptador. La BD té 16 regles reals; el "16è
  sense regla" **no es correspon amb la persistència** (totes 16 tenen regla). El comptador de la UI
  barreja probablement files-de-document vs regles-persistides (per la col·lisió i el descart de
  no-vinculats). **Cal reconciliar el comptador** amb la font única (regles del ruleset).
- **SizeSystem del run:** `Home ALPHA — LOSAN IBERIA SA Run 01`.

**Veredicte BLOC 6: cal X.** La persistència és coherent (16 regles ben formades); els símptomes
(FIXED erroni, absències) es materialitzen ABANS de la BD (extracció/preview/filtre/col·lisió), i el
comptador "15/16" és un artefacte de UI.

---

## BLOC 7 — Creació de POM de client des del wizard [context, ex-Q5]

- **NO EXISTEIX.** Cap vista de `size_map_views.py` fa `POMMaster.objects.create`; només
  `find_pom_master` (match a existents, `extraction_views.py:525-604`, **mai crea**). Codi no resolt i
  no vinculat → regla **omesa** (`size_map_views.py:619-622`). El frontend només té selector
  d'existents (cap botó "crear POM"). Gating: `_Configure` (CONFIGURE) a tots els endpoints.
- **Sense governança de catàleg:** `POMMaster` no té `is_system`/`read_only`. La creació de POM de
  tenant viu en un endpoint SEPARAT (`create_tenant_pom_view`, `pom/wizard_views.py:332`, gated només
  `IsAuthenticated`), **no accessible des de la Size Library**.

**Veredicte BLOC 7: decisió de producte.** Un codi de client desconegut al wizard només es pot
vincular a un POM existent o es perd. No hi ha camí per crear/registrar POMs de client des d'aquí.

---

## BLOC 8 — Pas de confirmació del wizard i paritat regla↔document [Q8]

- **Pas 3 (taula de regles, editable):** per fila mostra `pom_codi_client` + descripció del document
  (referència), badge de confiança, vincle/selector de POM, **selector de lògica editable**, la
  **regla DERIVADA** (`increment_base` / `valors_step_text`, o "—" si el detector va retornar None),
  i el warning ([SizeMapSetup.jsx:613-660](../../frontend/src/pages/SizeMapSetup.jsx#L613)).
- **Pas 4 (destí + resum):** panell "Resum" (`:709-714`): **`Acció: <CREAR|REUTILITZAR>`** · Target ·
  Unit · Client · Talles: N · **Regles: N** (`gradingResults.filter(g => g.pom_id).length`, `:712`) ·
  Perfils: N. + panell de conflicte 409 (`:716+`).
- **CLAU — NO EXISTEIX cap vista de paritat regla-derivada ↔ document.** La taula mostra la regla
  DERIVADA (lògica + delta), però **NO els valors originals per talla** del document
  (`valors_calculats` / `values_by_size`). El backend SÍ els retorna
  ([size_map_views.py:441](../../backend/fhort/pom/size_map_views.py#L441) `'valors_calculats'`) i el
  frontend els té a l'estat (spread `...x` a `SizeMapSetup.jsx:317`), però **no es renderitzen**. L'humà
  NO pot comparar "el document deia 5.6→8.0 per talla" amb "derivat: LINEAR +0.3" abans de persistir;
  només veu (i pot editar a cegues) el selector de lògica.

**Veredicte BLOC 8: cal X (candidat de fix prioritari).** La validació humana d'un **actiu de secret
industrial** (les regles de graduació) **NO és possible avui abans de persistir**: falta la columna de
valors originals al costat de la regla derivada. Fix mínim: renderitzar `valors_calculats` (ja a
l'estat del frontend) com a columna de paritat al pas 3. Precisament aquesta paritat hauria fet
visible el símptoma K.1 (valors 5.6→8.0 vs regla FIXED) abans de desar.

---

## VEREDICTE FINAL — causa arrel per símptoma + fix mínim (sense implementar)

| Símptoma | Causa arrel | Fix mínim proposat |
|---|---|---|
| **K.1 +0.3 → FIXED** | Els valors per talla arriben **constants** al detector (fidelitat extracció o desalineació run↔`values_by_size`); el detector és determinista, no és llindar. | **Instrumentar:** registrar/retornar els `values_by_size` extrets per POM (avui no es persisteixen) per discriminar extracció vs alineació. Després, si és alineació, casar claus de `values_by_size` al `run` amb `_norm` abans de `detect_grading`. |
| **J.2 vinculat però absent** | Col·lisió `GradingRule.update_or_create(rule_set, pom)` (`size_map_views.py:625`): dues files → mateix POM, l'última guanya. | Detectar `pom_id` duplicats al payload i **avisar/bloquejar** abans de crear (o acumular en comptes de sobreescriure). Retornar un avís explícit de col·lisió, no silenci. |
| **E/H.6 no vinculats absents** | Filtre `grading.filter(g => g.pom_id)` (`SizeMapSetup.jsx:354`) descarta no-vinculats. | Convertir el `window.confirm` en **avís persistent** al resultat del run (llista de codis descartats), i/o materialitzar-los com a "pendents de vincular" en comptes de perdre'ls. |
| **Toleràncies absents** | `_pdf_extracted_to_poms` descarta `tolerance_*`; el run no té camp (correcte) però no les deriva a cap POM/model. | Portar `tolerance_minus/plus` al consumidor i **aterrar-les al POM** (`tolerancia_default_*`) o al model — **col·lapsades a una sola ±** (deute DECISIONS §5). Decisió de producte on aterren. |
| **"Valor base —"** | **DISSENY:** el run no desa valors base (viuen al model). `increment_base` sí és poblat. | **Cap** (comportament correcte). Opcional: aclarir l'etiqueta de la UI perquè "—" no s'interpreti com a error. |
| **"15/16 regles"** | Comptador de UI que barreja files-document vs regles-persistides. | Reconciliar el comptador amb les regles reals del ruleset. |
| **Sense paritat regla↔document** | El pas de confirmació no mostra els valors originals per talla al costat de la regla derivada (`valors_calculats` no es renderitza). | Afegir columna de **paritat** (valors originals per talla) al pas 3, abans de crear — permet la validació humana de l'actiu. |

### Decisions de producte a elevar (CTO)
1. **POMs de client:** no hi ha camí per registrar un codi de client desconegut des del wizard (només
   vincular a existents; els no-vinculats es perden). Cal decidir si el wizard ha de poder **crear POM
   de client** (amb governança) o mantenir una **cua de no-resolts**.
2. **Toleràncies:** on aterren (POM catàleg vs model) i **col·lapse 2→1 ±** (deute §5) — decisió abans
   d'implementar el pas de captura.
3. **Col·lisió de mapping:** política quan dos codis de document es vinculen al mateix POM (avís,
   bloqueig, o fusió).

---

## TAULA FINAL DE RISCOS

| # | Risc | Evidència | Severitat |
|---|---|---|---|
| R1 | Pèrdua **silenciosa** de regles per col·lisió `update_or_create(rule_set,pom)` | `size_map_views.py:625` · J.2 absent | **Alt** (dades perdudes sense avís) |
| R2 | Descart **silenciós** de codis no vinculats (només `confirm`, sap rastre) | `SizeMapSetup.jsx:354,391-397` | Mitjà-alt |
| R3 | Toleràncies extretes i **llençades** (mai aterren a POM/model) | `_pdf_extracted_to_poms` · GradingRule sense tol | Mitjà |
| R4 | K.1 FIXED: **no diagnosticable** sense instrumentació (valors extrets no persistits) | BLOC 2 obert | Mitjà (cal log) |
| R5 | Comptador "15/16" enganyós vs BD (16) | BLOC 6 | Baix |
| R6 | Sense camí per a POMs de client ni cua de no-resolts | BLOC 7 | Mitjà (decisió de producte) |
| R7 | **No es pot validar humanament** la fidelitat regla↔document abans de persistir (actiu de secret industrial) | BLOC 8 · `valors_calculats` no renderitzat | **Alt** (es desa un actiu crític sense revisió possible) |

## Obert / dubtós
- **Valors extrets NO persistits:** ni `values_by_size` ni `tolerance_*` es desen abans de derivar →
  impossible confirmar en read-only si K.1 va arribar constant per extracció o per alineació. Únic
  desllorigador: instrumentar (log/retorn de debug) — fora de l'abast read-only.
- **Quin POM canònic = K.1/J.2:** els rules es desen per codi canònic; el mapping document→canònic no
  es persisteix, així que no es pot lligar amb certesa K.1↔regla concreta sense el payload de creació.
- No s'ha obert la vista de detall del run de la Size Library (si n'hi ha una amb columna "Valor base"
  diferent de la del wizard); la conclusió de disseny es basa en l'eliminació de `GradingRule.valor_base`.
