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

## Punts d'enganxament per a F2 (del diagnòstic)

- Editor → llegir `.ftt`: `GET ftt-documents/<id>/` retorna `document_json` + URLs d'assets;
  `document_to_v2(document_json, asset_src=…)` reconstrueix el `template_json` v2 que l'editor
  ja sap pintar.
- "Desa" de l'editor: `PATCH ftt-documents/<id>/` (exigeix lock; renova `locked_at`).
- Export: el front ja genera el PDF (pdf-lib); enviar-lo a `POST ftt-documents/<id>/export/`.
- Lock: `POST ftt-documents/<id>/lock/` al muntar + heartbeat opcional; `unlock/` al desmuntar.
  El timer-gap ja està resolt al backend (desar renova el lock).
- Menú lateral grup "Disseny" (F11) i botó "Edita" al Finder: pendents de F2 (frontend).
