> ⚠️ SUPERADA 2026-07-07 — cutover F2 fet (editor 100% .ftt, TechSheet eliminat mig 0050); substituïda per DIAGNOSI_EDITOR_ESTAT. Consulta només com a històric.

# Fase 1 .ftt — anotacions per a la Fase 2 (cutover frontend)

Backend de la Fase 1 complet (peces B1–B8, branca `dev`, sense push). Aquest document recull
el que la Fase 1 ha deixat **deliberadament intacte** perquè el frontend encara hi depèn, i el
que F2 haurà de fer en el cutover de l'editor.

## Estat al final de Fase 1

- El document editable ja viu com a `ModelFitxer` tipus `TECHSHEET` (.ftt), versionat amb la
  invariant `is_current`/`save_model_file`. Endpoints crear/carregar/desar/lock/unlock/export
  operatius. La fitxa real (model 162) ja s'ha migrat a `.ftt` v1 (id=28) amb el command
  `migrate_techsheets_to_ftt` (idempotent, re-executable al cutover).
- El model `TechSheet` (O2O) i `TechSheetTemplate` segueixen **vius**: el frontend
  (`TechSheetEditor.jsx`) i `_resolve_template_json` encara hi llegeixen/escriuen.

## 🔴 Deixat per F2 (NO tocar a Fase 1)

| Element | Per què s'ha deixat | Acció a F2 |
|---|---|---|
| `TechSheet.versio` | El front el pinta a 8 llocs ([TechSheetEditor.jsx:212,324,635,877,903,916,1025,1067](../../frontend/src/pages/TechSheetEditor.jsx#L212)): capçalera, nom del PDF, badge. Retirar-lo ara trencaria el render. | Substituir per `ModelFitxer.versio` (versionat real del .ftt) quan l'editor llegeixi el .ftt; després `RemoveField`. |
| Model `TechSheet` (O2O) | Editor viu encara hi fa GET/PATCH `tech-sheet/`. | Migrar l'editor a llegir/desar el `.ftt` (endpoints `ftt-documents/…`), re-executar `migrate_techsheets_to_ftt --apply`, i fer drop del model. |
| Model `TechSheetTemplate` | `_resolve_template_json` ([tech_sheet_editor_views.py:53,63](../../backend/fhort/models_app/tech_sheet_editor_views.py#L53)) l'usa en crear una TechSheet. | Migrar les plantilles a `DocumentTemplate` (B5) i fer drop. |
| Comentari stale [TechSheetEditor.jsx:536-539](../../frontend/src/pages/TechSheetEditor.jsx#L536-L539) | És frontend; la Fase 1 és backend-only. El comentari ja és **fals** (el serializer SÍ exposa `template_json`). | Esborrar el comentari en tocar l'editor. |

## ✅ Ja jubilat a Fase 1 (backend-only, sense dependència del front)

- `TechSheet.estat` — mort (0 escriptors, 0 lectors al front). Retirat (migració 0049).
- Fallback legacy `schemas` als serializers — 0 files l'usen. Retirat.

## ✅ Estat post-Fase 2 (cutover de l'editor fet)

L'editor de fitxa per-model treballa **100% sobre `.ftt`**:
- `/models/:id/fitxa` → `FttResolver` (resol/crea el `.ftt`) → `/models/:id/ftt/:fitxerId`.
- Load/save/lock/export via `ftt-documents/`. `versio` = `ModelFitxer.versio`. Botó "Edita" al
  Finder + grup "Disseny" al menú.
- Backend: model `TechSheet` **eliminat** (migració 0050 amb data-migration idempotent
  prependida per a seguretat a PROD) i endpoints `tech-sheet/` retirats.

### 🔴 Encara pendent (cutover propi, decisió de disseny)
- **`TechSheetTemplate` → `DocumentTemplate`**: l'editor de plantilla per Customer
  (`/clients/:id/plantilla`, `TechSheetTemplateEditor`) i els 2 endpoints `tech-sheet-template/`
  segueixen **vius**. Migrar-hi implica decidir com mapeja el concepte "una plantilla per client
  (template_json)" al magatzem genèric `DocumentTemplate` (FileField `.ftt` + `metadata_schema`).
  No fet a Fase 2 (decisió ⚖️ oberta).
- **Eines de girar/simetria i importació de mesures/grading** a l'editor: anotades, no entren a F2.
- **Poda d'assets no referenciats** en desar: `save_document` fusiona assets sense podar; imatges
  noves es desen inline (no extretes a `assets/`). Refinament futur.
- **Proliferació de versions per autosave**: cada desat crea una versió `.ftt`. El Finder només
  mostra `is_current`; consolidació draft-vs-versió a decidir.

## Punts d'enganxament per a F2 (del diagnòstic)

- Editor → llegir `.ftt`: `GET ftt-documents/<id>/` retorna `document_json` + URLs d'assets;
  `document_to_v2(document_json, asset_src=…)` reconstrueix el `template_json` v2 que l'editor
  ja sap pintar.
- "Desa" de l'editor: `PATCH ftt-documents/<id>/` (exigeix lock; renova `locked_at`).
- Export: el front ja genera el PDF (pdf-lib); enviar-lo a `POST ftt-documents/<id>/export/`.
- Lock: `POST ftt-documents/<id>/lock/` al muntar + heartbeat opcional; `unlock/` al desmuntar.
  El timer-gap ja està resolt al backend (desar renova el lock).
- Menú lateral grup "Disseny" (F11) i botó "Edita" al Finder: pendents de F2 (frontend).
