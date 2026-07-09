# SPRINT 04 — FTTPT fase 1: tipus plantilla, desar-com, flux nou document, poda
FRONTEND + BACKEND (migració autoritzada amb auditoria).

## Decisions (Agus)
Plantilles del TENANT (tantes com vulgui) · qualsevol usuari en pot crear · en obrir
document nou: pàgina en blanc | des de plantilla.

## Abast
1. MANIFEST: camp `kind: 'document'|'template'` al manifest del .ftt (services_ftt.py;
   absent = 'document', retrocompatible). Extensió .fttpt per a plantilles (cosmètic;
   el kind mana).
2. EMMAGATZEMATGE: reviure DocumentTemplate (ftt_models.py:36-64, model mort) com a
   contenidor tenant-level: FileField del .fttpt + nom + descripció + created_by.
   Migració dels camps que faltin. Serializer + ViewSet CRUD mínim (IsAuthenticated)
   + rutes. NO usar TechSheetTemplate (deprecat).
3. DESAR COM A PLANTILLA: acció al menú de l'editor → empaqueta el document actual com
   a .fttpt (kind=template, snapshot del contingut, SENSE lligams al model d'origen:
   netejar snapshot{} de taules? NO — les taules queden com a mostra estàtica; els
   camps vius vindran a S5) → crea DocumentTemplate.
4. FLUX NOU DOCUMENT: FttResolver/creació (services_ftt_document.create_document, on
   template_id era "reservat B5") → si l'usuari tria plantilla, el document neix del
   contingut del .fttpt (kind=document). UI: diàleg blanc|plantilles del tenant (llista
   amb nom/descripció).
5. PODA de confusió: retirar el botó "plantilla" de la llista de Clients i la ruta
   /clients/:id/plantilla + TechSheetTemplateEditor.jsx (jubilar amb comentari; NO
   esborrar encara tech_sheet_models/serializers/views backend — anotar com a candidat
   G-poda al doc d'estat).

## Porta verda
Cicle sencer: crear doc → decorar-lo → desar com a plantilla → nou document des de la
plantilla = neix amb el contingut. Migració aplicada amb migrate_schemas + auditoria
\d directa a BD (fitxer de migració al doc d'estat). Doc .ftt antic obre igual.
Restart servei al final del sprint. Build+check nets.

## Commits: 1. kind al manifest · 2. backend DocumentTemplate (migració+API) ·
3. desar-com + flux nou document · 4. poda UI vella.
