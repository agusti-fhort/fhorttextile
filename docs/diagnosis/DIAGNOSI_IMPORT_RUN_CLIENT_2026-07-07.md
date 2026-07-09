# DIAGNOSI — Import "Nou run de client" (Size Library, pas 2) falla amb "cap mesura llegible"

**Data:** 2026-07-07 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
**Equip:** director-investigació + 3 investigadors-codi paral·lels (camí run-client · camí wizard-model · fallback+G3) + síntesi. Cap escriptura de codi, cap migració, cap restart.
**Abast:** per què el mateix PDF (BERG, escanejat amb OCR brut) s'extreu bé al wizard d'import a model/POMs i retorna "La IA no ha retornat cap mesura llegible del document." al wizard "Nou run de client".

> Convenció: `fitxer:línia` relatiu a l'arrel del repo. "NO EXISTEIX" = confirmat absent al codi (no especulat).

---

## 0. Resum executiu (director)

- **Causa arrel = desajust de contracte d'esquema (bug determinista), NO qualitat d'OCR ni model.** El camí run-client crida `extract_from_file` (servei G3), que retorna un JSON amb claus **`poms`** + **`grading_table`**; però el consumidor `size_map_views.py:354` llegeix **`extracted.get('measurements')`** — clau que aquest servei **mai** retorna. Resultat: `measurements` és sempre `None` → `poms_in` sempre buit → l'avís de `size_map_views.py:361` salta **amb QUALSEVOL fitxer PDF/imatge**, encara que l'extracció hagi anat perfecta.
- **L'OCR brut és un fals culpable.** Els DOS camins envien el PDF **igual**: document natiu (base64) a un model de visió; **cap** capa de text OCR. La diferència no és text-vs-visió (Q6).
- **La divergència de model/prompt és secundària (deute), no la causa.** Run-client usa `claude-opus-4-5` + `EXTRACTION_PROMPT` (esquema `poms`); el wizard que funciona usa `claude-opus-4-7` + `TECH_SHEET_EXTRACTION_PROMPT` (esquema `measurements`). El consumidor run-client està escrit contra l'esquema del **wizard** (`measurements`/`client_code`/`values`) però crida el servei **G3** (`poms`/`base_value_cm`/`grading_table`).
- **El fallback Opus del 06/07-07 (`b4aa3c1`, `6517440`) NO cobreix aquest camí:** només toca `models_app/extraction_views.py` (via Excel del wizard). No té cap efecte sobre `pom/size_map_views.py`.
- **Fix mínim:** alinear el consumidor a l'esquema real de `extract_from_file` (llegir `poms` + `grading_table`), no substituir el model.

---

## BLOC 1 — Camí COMPLET del "Nou run de client" (pas 2) [Q1]

- **Frontend (pas 2):** `SizeAuthoringDrawer.jsx` és un embolcall de modal ([SizeAuthoringDrawer.jsx:2,57](../../frontend/src/components/SizeAuthoringDrawer.jsx#L57)) que renderitza el `Wizard` de `frontend/src/pages/SizeMapSetup.jsx`. El pas 2 real (pujada de fitxer) és `SizeMapSetup.jsx:482` (UI a `:576-592`; `<input>` accepta `.xlsx,.xls,.pdf,.png,.jpg,.jpeg,.webp` a `:588`).
- **Handler:** `calcGradingFromFile` ([SizeMapSetup.jsx:337-348](../../frontend/src/pages/SizeMapSetup.jsx#L337)) → `FormData` amb camp **`file`** + `size_system_id` + `base_size` (`:340-343`).
- **Endpoint:** `sizeMap.gradingPreviewFile(fd)` → `POST /api/v1/size-map/grading-preview-file/` ([endpoints.js:142-144](../../frontend/src/api/endpoints.js#L142), multipart amb `Content-Type: undefined`).
- **Vista:** `size_map_grading_preview_file_view` ([size_map_views.py:315-425](../../backend/fhort/pom/size_map_views.py#L315)), permís `_Configure` (`:315-316`). Classifica per extensió: Excel → parser local `_parse_grading_excel` (`:282-312`, cridat `:345`); **PDF/imatge → `extract_from_file`** (`:353`).
- **Extracció (servei):** `from fhort.models_app.extraction_service import extract_from_file` ([size_map_views.py:330](../../backend/fhort/pom/size_map_views.py#L330)). Dins `extract_from_file` ([extraction_service.py:129-186](../../backend/fhort/models_app/extraction_service.py#L129)): **NO** usa l'SDK d'Anthropic; fa `POST` HTTP directe amb `httpx` a `api.anthropic.com/v1/messages` (`:80,166`), header beta `pdfs-2024-09-25` (`:162`).
- **Model:** `MODEL = "claude-opus-4-5"` ([extraction_service.py:81](../../backend/fhort/models_app/extraction_service.py#L81), usat al payload `:145`). `max_tokens: 8192` (`:146`); sense `thinking`/`effort`.
- **Prompt:** `build_extraction_prompt(None) + EXTRACTION_PROMPT` (`:142`); `EXTRACTION_PROMPT` és constant local (`:15-77`) amb esquema de sortida de claus **`poms`** (`:49`) i **`grading_table`** (`:52`).

**Veredicte BLOC 1: cal X (bug determinista).** El camí és coherent fins a la crida IA; el trencament és al consumidor (BLOC 2/veredicte final).

---

## BLOC 2 — Camí que SÍ funciona + taula comparativa [Q2]

- **Frontend:** `frontend/src/components/ImportWizard/ImportWizard.jsx` (5 passos). Pas 1 puja `document` a `POST /api/v1/import-sessions/cribratge/` ([ImportWizard.jsx:143](../../frontend/src/components/ImportWizard/ImportWizard.jsx#L143)); pas 2 crida `runExtraccio` → `POST /api/v1/import-sessions/<token>/extraccio/` (`:212`, sense reenviar el fitxer: el backend rellegeix el document de la sessió).
- **Vista:** `import_session_extraccio_view` ([extraction_views.py:740-903](../../backend/fhort/models_app/extraction_views.py#L740)). Crida IA **inline** (no via `extraction_service`) a `:800-809` amb SDK `anthropic.Anthropic`.
- **Model:** `EXTRACCIO_MODEL = 'claude-opus-4-7'` ([extraction_views.py:608](../../backend/fhort/models_app/extraction_views.py#L608), usat `:802`); `max_tokens=16000`, `thinking=adaptive` (`:804`), `output_config effort=high` (`:805`), prompt-cache.
- **Prompt:** `TECH_SHEET_EXTRACTION_PROMPT` ([extraction_prompt.py:86-234](../../backend/fhort/models_app/extraction_prompt.py#L86)), esquema de sortida amb clau **`measurements`** (`extraction_prompt.py:199`), ítems amb `client_code`/`code`/`description`/`values`.
- Parse tolerant + `salvage_measurements` per fila (`:828-838`).

### Taula comparativa dels dos camins
| | **Run de client (FALLA)** | **Wizard model/POMs (FUNCIONA)** |
|---|---|---|
| Vista | `size_map_views.py:315` → `extract_from_file` | `extraction_views.py:740` (inline) |
| Servei | `extraction_service.extract_from_file` (`:129`) | crida IA inline a la vista |
| Transport | `httpx` cru (`extraction_service.py:166`) | SDK `anthropic.Anthropic` (`:800`) |
| **Model** | **`claude-opus-4-5`** (`extraction_service.py:81`) | **`claude-opus-4-7`** (`extraction_views.py:608`) |
| **Prompt** | `EXTRACTION_PROMPT` (`extraction_service.py:15`) | `TECH_SHEET_EXTRACTION_PROMPT` (`extraction_prompt.py:86`) |
| **Clau de sortida** | **`poms` + `grading_table`** (`:49,52`) | **`measurements`** (`extraction_prompt.py:199`) |
| Camps ítem | `code`/`description`/`base_value_cm` · grading a `grading_table.values_by_size` | `client_code`/`code`/`description`/`values` |
| Extres | cap | `thinking adaptive`, `effort high`, salvage, prompt-cache |
| max_tokens | 8192 | 16000 |
| Enviament PDF | document natiu base64 (`extraction_service.py:99-107`) | document natiu base64 (`extraction_views.py:236-244`) |

**Veredicte BLOC 2: llest (referència).** Els camins **NO comparteixen** servei, prompt ni model. El consumidor run-client (`size_map_views.py:354-358`) està escrit contra l'esquema d'AQUEST camí (`measurements`/`client_code`/`values`) però crida el servei de l'altre.

---

## BLOC 3 — Fallback Opus (`b4aa3c1`, `6517440`) [Q3]

- Els DOS commits toquen **NOMÉS** `backend/fhort/models_app/extraction_views.py`, funcions `_extraccio_via_excel` i `import_session_extraccio_view`.
- **On:** `import_session_extraccio_view` detecta Excel (`:768-775`); si el parser determinista `_parse_excel_poms` no troba POMs, `_extraccio_via_excel` retorna `None` (`:665-666`, abans `Response 400`) i la vista cau al camí comú Opus amb el full convertit a text (`:762-767`).
- **Format cobert:** NOMÉS `.xlsx/.xls`. **PDF/imatge NO canvien** (ja anaven sempre pel camí Opus del wizard).
- **Model:** `claude-opus-4-7` (`:608`, usat `:802`). Guarda de truncament `6517440`: `if response.stop_reason == 'max_tokens'` → avís (`:817-820`).
- **Cobreix el run de client (`pom/size_map_views.py`)? → NO.** `size_map_views.py` importa d'`extraction_views` **només** `find_pom_master` (`size_map_views.py:217,329`), que **cap** dels dos commits toca. No hi ha cap referència a `_extraccio_via_excel`/`import_session_extraccio_view` des del run de client.

**Veredicte BLOC 3: cal X.** El fallback és específic del wizard-Excel; **no té cap efecte** sobre el camí que falla.

---

## BLOC 4 — Pertinença al pipeline antic G3 [Q4]

- **SÍ, per a PDF/imatge el run de client penja de G3.** Crida `extract_from_file` d'`extraction_service.py`, que ÉS el servei G3: `EXTRACTION_PROMPT` (`:15`), `MODEL="claude-opus-4-5"` (`:81`), HTTP directe (`:80`), `max_tokens:8192` (`:146`), **sense** guarda `stop_reason` (grep: NO EXISTEIX a `extraction_service.py`).
- **No és orfe: penja d'un tros G3 no-podat i intencionadament preservat.** `models_app/urls.py:65-66` documenta que el camí d'import VELL es va retirar (P6, 0 consumidors) **però** "`extraction_service`/`EXTRACTION_PROMPT` es MANTENEN: són VIUS (els usa el wizard nou + size-map)". Confirmat a `settings.py:129` ("usat per extraction_service.py").
- **Per Excel**, en canvi, el run de client té motor propi separat (`_parse_grading_excel`, `size_map_views.py:282`), aliè a G3 i al wizard.
- **Model ids per camí:** wizard `claude-opus-4-7` (`extraction_views.py:91,608`); run-client PDF `claude-opus-4-5` (`extraction_service.py:81`). Cap model id a `settings.py` (NO EXISTEIX; només `ANTHROPIC_API_KEY`, `settings.py:130`).

**Veredicte BLOC 4: cal X.** El camí run-client PDF/imatge és G3-antic (servei preservat), amb model més vell i sense les millores del wizard — però això és **deute secundari**, no la causa del "cap mesura llegible".

---

## BLOC 5 — Logs [Q5]

- **Servei:** `ftt-staging.service` (Gunicorn), host `fhort-assessment`.
- `journalctl -u ftt-staging`: només **warnings d'arrencada de DRF** ("unable to guess serializer" per a múltiples vies, incloent `size_map_grading_preview_file_view`) — **inofensius** (fallback de schema d'OpenAPI, no runtime).
- **Cap traça runtime** de `grading-preview-file` / `extract_from_file` / `measurements` a la finestra inspeccionada. Coherent amb la causa arrel: el camí 361 retorna **200 amb `avisos`** (no és excepció) i **no escriu cap log**; `extract_from_file` només registra en error de parse JSON (`extraction_service.py:182`). Una crida IA reeixida que retorna `poms` llegida com a `measurements` produeix **zero logs**.
- **Logs de prod: NO accessibles** des de staging (només `journalctl` de staging + `/var/log/ftt_staging_refresh.log`, no relacionat).

**Veredicte BLOC 5: llest (consistent).** L'absència de traça d'error confirma que **no és una fallada d'API**, sinó el desajust silenciós de clau. Verificació runtime directa: pendent (read-only) — no cal per al veredicte, que és determinista pel codi.

---

## BLOC 6 — Com s'envia el PDF en cada camí [Q6]

- **Run de client:** `_file_to_content_block` ([extraction_service.py:95-126](../../backend/fhort/models_app/extraction_service.py#L95)) → PDF = bloc `{"type":"document","source":{"type":"base64","media_type":"application/pdf",...}}` (`:99-107`); imatge = bloc `image` (`:108-119`). **Document natiu a visió; cap OCR/pdfplumber.**
- **Wizard model/POMs:** `_cribratge_content_block` ([extraction_views.py:231-265](../../backend/fhort/models_app/extraction_views.py#L231)) → PDF = mateix bloc `document/base64` (`:236-244`); imatge = `image` (`:258-265`); Excel = text tabulat via `_excel_to_text` (`:122-134`).
- **Diferència rellevant:** **CAP** pel que fa al transport del PDF — tots dos passen el PDF cru (amb el seu OCR incrustat) a un model de visió. Per tant **l'OCR brut afecta els dos camins per igual**; no explica la diferència de comportament.

**Veredicte BLOC 6: llest.** El "OCR brut" és irrellevant per a la diferència: no és text-vs-visió. Ambdós són visió-document.

---

## VEREDICTE FINAL — causa arrel + fix mínim (sense implementar)

**CAUSA ARREL (verificada, determinista):** desajust de contracte d'esquema al consumidor PDF/imatge del run de client.
- `size_map_views.py:353-361` fa `extracted = extract_from_file(...)` i itera `extracted.get('measurements')`, llegint camps `client_code`/`description`/`values`.
- Però `extract_from_file` retorna el JSON cru d'`EXTRACTION_PROMPT` (`extraction_service.py:186`), l'esquema del qual té **`poms`** (`code`/`description`/`base_value_cm`) i **`grading_table`** (`code`/`values_by_size`) — **mai `measurements`, mai `values`**.
- → `measurements` sempre `None` → cap fila → `poms_in` buit → avís `size_map_views.py:361` **amb qualsevol PDF/imatge**, independentment de l'OCR, el contingut o el model.

El consumidor va ser escrit contra l'esquema del **wizard** (`TECH_SHEET_EXTRACTION_PROMPT` → `measurements`) però connectat al servei **G3** (`EXTRACTION_PROMPT` → `poms`). El camí Excel del run de client (`_parse_grading_excel`) no passa per aquí i per això funciona.

**FIX MÍNIM proposat (no implementat):** a `size_map_views.py:353-361`, alinear el consumidor a l'esquema real d'`extract_from_file`:
- Iterar `extracted.get('poms')` → `codi_fitxa = p['code']`, `descripcio = p['description']`.
- `values`: prendre de `extracted.get('grading_table')` casant per `code` → `values_by_size`; si `has_base_only`/sense grading, muntar `{base_size: base_value_cm}`.
- Mantenir l'avís 361 només com a cas real de zero POMs.

**Alternativa (més canvi, NO recomanada com a mínim):** fer que el run de client cridi la mateixa extracció del wizard (`TECH_SHEET_EXTRACTION_PROMPT` → `measurements`, `opus-4-7`), unificant els dos pipelines. Ressol també el deute de model/prompt divergent, però és una convergència de pipeline (peça pròpia), no un fix mínim.

> 💡 PROPOSTA (a validar): unificar a mitjà termini els dos serveis d'extracció (G3 `extraction_service` vs inline del wizard) en un de sol amb un únic esquema de sortida — avui hi ha dos prompts, dos models Opus i dos transports per a la mateixa tasca (llei "no més pedaços").

---

## TAULA FINAL DE RISCOS

| # | Risc | Evidència | Severitat |
|---|---|---|---|
| R1 | **Camí run-client PDF/imatge trencat al 100%** (desajust de clau `measurements` vs `poms`) | `size_map_views.py:354` vs `extraction_service.py:49,186` | **Alt** (funcionalitat morta; el fix és quirúrgic) |
| R2 | Fals diagnòstic "problema d'OCR/model": pot portar a canviar model o pre-processar OCR sense arreglar res | BLOC 6; ambdós camins = visió-document | Mitjà (perdre temps al lloc equivocat) |
| R3 | Deute: dos pipelines d'extracció divergents (opus-4-5+`EXTRACTION_PROMPT`+httpx vs opus-4-7+`TECH_SHEET`+SDK) | Taula BLOC 2 | Mitjà (manteniment; qualitat inferior al camí G3) |
| R4 | Camí G3 (`extract_from_file`) sense guarda `stop_reason` ni salvage per fila → pèrdua silenciosa en documents grans | `extraction_service.py` (NO EXISTEIX stop_reason); vs `extraction_views.py:817` | Baix-mitjà |
| R5 | Verificació runtime no feta (read-only); si per algun motiu la crida retornés 500 en comptes de 200, la ruta a l'avís seria una altra | BLOC 5 (obert) | Baix (el codi és determinista; el fix cobreix ambdós) |
