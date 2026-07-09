# PROTOCOL RUN NOCTURNA — Editor FTT (S0–S9)
Data: 2026-07-06/07 · Autor disseny: Claude Chat (Fable 5) · Executor: Claude Code

## Models
- Fil principal (orquestrador i revisor-diff): **Opus 4.8** (`/model opus`).
- Subagents implementador/verificador/guàrdies: **Sonnet 4.6** (declarar-ho al spawn).

## Regla d'or
Cada sprint és una TRANSACCIÓ. Mai començar el següent sense la porta verda del previ.
Verd trencat o contradicció de paradigma → **STOP TOTAL** (no saltar, no improvisar):
escriure a SPRINT_EDITOR_ESTAT.md on i per què, i aturar la run.

## Pas 0 obligatori (abans de S0)
1. Backup BD: `pg_dump` d'ftt_staging (PG18:5433) a /root/backup_pre_sprints_editor.dump
   amb `/usr/lib/postgresql/18/bin/pg_dump`; verificar mida > 0.
2. Tag git: `git tag pre-sprints-editor` a dev (staging, /var/www/ftt-staging).
3. `git status` net; si hi ha res sense committejar → STOP.

## Transacció de sprint (idèntica per a tots)
1. LLEGIR: SPRINT_EDITOR_ESTAT.md + SPRINT_NN.md + les seccions de
   docs/diagnosis/DIAGNOSI_EDITOR_ESTAT.md que el sprint citi.
2. MINI-DIAGNOSI (read-only, barata): verificar que el codi objectiu és on la diagnosi
   diu; si divergeix (algú ha tocat), anotar-ho i adaptar SENSE canviar l'abast.
3. IMPLEMENTAR (subagents Sonnet): codi mínim, un concern per commit,
   `git add` selectiu (MAI -A), `manage.py check` abans de commit backend,
   `npm run build` abans de commit frontend, `git log -1` després de cada commit.
4. PORTA VERDA: build net · smoke del verificador (criteris del sprint) ·
   revisor-diff (Opus) aprova · guàrdia i18n (cap string UI sense clau; excepcions
   declarades) · guàrdia UI (tokens CSS no hex fora KONVA_COL; Tabler outline).
5. TANCAR: actualitzar SPRINT_EDITOR_ESTAT.md (fet/commits/decisions/pendents) → següent.

## Prohibicions de tota la run
- NO push (commits queden a dev local; Agus pusha al matí).
- NO tocar PROD ni res fora de /var/www/ftt-staging (zones intocables del servidor).
- NO tocar el domini d'import/extracció (track 1) ni grading motor (G6).
- NO esborrar codi fora de l'abast explícit del sprint.
- Restart d'ftt-staging.service NOMÉS si un sprint toca backend, i al final del sprint.

## Migracions (autorització d'Agus 2026-07-06)
Permès generar i APLICAR a staging (`migrate_schemas`, mai --schema), amb:
fitxer de migració enganxat al doc d'estat + auditoria directa de BD pel verificador
(\d de la taula) — no fiar-se del OK de Django (quirk django-tenants).

## Render a dues bandes (llei tècnica)
Tot element/propietat visual nou s'implementa a ObjectNode (live) I addObjectToLayer
(export), preferentment via helper compartit. El verificador comprova sempre:
live == export (miniatura/PDF) per al que s'ha tocat.

## Historial (a partir de S0)
Tota mutació del document passa pel mòdul d'història de S0. Sprints posteriors que
afegeixin mutacions NOVES han de registrar-les-hi (criteri de porta verda).
