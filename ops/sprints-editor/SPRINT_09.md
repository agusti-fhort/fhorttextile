# SPRINT 09 — Deutes tècnics de l'editor
FRONTEND + backend lleu. Últim de la cua: només si S0–S8 verds.

## Abast
1. CHUNK: vite.config.js → manualChunks separant konva/react-konva, paper, pdf-lib
   del chunk TechSheetEditor (avui 596kB > llindar 500kB, i haurà crescut amb la run).
   Objectiu: cap chunk d'app > 500kB; vendors cacheables a part. Verificar que el
   lazy import del PaperFlatEditor es manté.
2. LOCK HEARTBEAT: setInterval de renew_lock cada 10min mentre el document és obert
   (independent de l'autosave — tanca el gap "obert sense editar >30min" §2.4);
   netejat a l'unmount. + beforeunload amb release keepalive (best effort).
3. PODA PDF ANTIC: retirar export_model_spec_pdf_view (pom/s8_views.py:229-347) +
   rutes (tasks/urls.py:220-238) + ExportModelPDF (ExportButton.jsx:100-108, sense
   consumidor muntat — verificar-ho a la mini-diagnosi amb grep abans d'esborrar).
   Un commit aïllat i reversible.

## Porta verda
Build amb chunks < 500kB i editor funcional (smoke: obrir doc, dibuixar, exportar PDF).
Lock: obrir doc, no tocar res 12min (simulable ajustant l'interval en test manual o
inspeccionant la crida) → renew registrat. Poda: check net, grep sense referències
mortes, editor i exports intactes. Restart servei al final.

## Commits: 1. manualChunks · 2. heartbeat+beforeunload · 3. poda PDF antic.

## En tancar aquest sprint (final de la run)
Escriure el RESUM FINAL a SPRINT_EDITOR_ESTAT.md: tots els commits, migracions,
decisions, deutes nous, i la llista de coses que Agus ha de revisar al matí abans
de fer push.
