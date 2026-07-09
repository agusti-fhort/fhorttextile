# CLAUDE.md — Lleis de mètode FTT (apliquen SEMPRE)

> Litúrgia de mètode versionada al repo. Aquestes lleis manen a totes les sessions
> d'agents sobre staging (`/var/www/ftt-staging`, branca `dev`). Els prompts són
> briefs curts que invoquen les skills; el mètode viu aquí, no als prompts.
> Fonts: `METODE_AGENTS.md` + `DECISIONS.md §1`. En cas de dubte, mana `DECISIONS.md`.

## Governança (Patró C)
- **Claude Chat dissenya · Claude Code executa · l'Agus decideix.** Les decisions
  d'arquitectura i de producte són humanes; l'agent fa la feina pesada (llegir codi,
  escriure peces acotades, verificar), no substitueix el criteri.
- **MAI push, MAI deploy des d'agents.** L'agent fa commits locals; **tots els pushes
  els fa l'Agus des de SSH.** Mai PROD, mai branca `main`. Tot a staging `dev`.

## Investigar abans de construir (visió global)
- **Primer investigar, després construir.** Cap decisió que afecti altres parts sense
  investigar-ne el radi complet: abans de tocar un node, saber què més el toca (qui el
  crida, quins signals dispara, quin estat comparteix).
- **Llegir el projecte sencer, no l'illa.** Comprovar què ja s'ha CONSTRUÏT abans de
  dir "no existeix" o "és estructural".
- **No més pedaços: unificar el ja construït.** Si dues superfícies viuen del mateix
  UI/dades, es convergeixen, no es peguen per separat.

## Disciplina de canvi
- **Codi mínim** per a la funcionalitat. **Un focus per commit.** No optimitzar-ho
  tot; fer exactament el que la peça demana. Scope creep vist fora de scope → s'ANOTA
  al report, no es toca.
- **`git add` de paths explícits, mai `-A`/`-u`.** Un commit per peça. **`git log -1`
  després de cada commit** per confirmar que ha entrat.

## Regla del verd (la porta dura)
- Backend: **`python manage.py check` net** abans de commit (des de `backend/`).
- Frontend: **`npm run build` net** abans de commit (`frontend/` i/o `frontend-backoffice/`).
- Verd = continuar sol a la peça següent. **Aturar-se NOMÉS per:** blocador dur,
  contradicció de paradigma, o verd trencat (qualsevol control vermell/bandera).
  En aturar-se: reportar `fitxer:línia` + quin control + per què, i esperar el CTO.
  No construir mai sobre una peça no-verda.

## Guardians de frontend
- **i18n-gate ca/en/es a tota UI nova.** Tot text de cara a l'usuari amb clau `t()` i
  paritat als tres idiomes (`frontend/src/i18n/{ca,en,es}.json`). Dades de domini
  (LINEAR/STEP, codis POM) NO es tradueixen.
- **Icones Tabler outline** (mai `-filled`). **Colors via tokens CSS, mai hex**
  (única excepció: `KONVA_COL` literal, perquè el canvas Konva no resol `var()`).

## Migracions i BD
- **`migrate_schemas` mai `--schema`.** Auditar les columnes directament a la BD
  després de migrar (django-tenants pot donar un OK enganyós).
- `migrate_schemas --list` NO és read-only en aquesta versió — no usar-lo en diagnosi.

## Fitxers d'estat (fora de git)
- **NO es commiten mai:** `ESTAT_PROJECTE.md`, `ESTAT_BACKOFFICE.md`, `DECISIONS.md`,
  `MAPA_SISTEMA.md`, `*_MODEL_VIU.md`, `MOTOR_*.md`. Viuen al servidor com a memòria
  de treball, no com a codi.

## Diagnosis (`docs/diagnosis/`)
- **Els agents només consulten l'arrel de `docs/diagnosis/` (vigents).**
  `docs/diagnosis/arxiu/` és històric, MAI font de veritat per a decisions.
- Quan un sprint implementa o supera una diagnosi, **el mateix sprint la segella**
  (capçalera `> ⚠️ SUPERADA <data> — <motiu>. Consulta només com a històric.`) **i la
  mou a `arxiu/`**.
- Les diagnosis SÍ es commiten (arrel = vigents · arxiu = històric segellat). Excepció a
  la regla de "fitxers d'estat fora de git": `ESTAT_*.md` i `DECISIONS.md` segueixen
  SENSE commitar; només `docs/diagnosis/` entra a git.

## Zones intocables
- No tocar POMs / grading engine (`generate_graded_specs`) / motor de patrons, tret
  que la peça ho demani explícitament. Problemes vistos en aquestes zones s'anoten.

---
*Mètode viu. Els patrons operatius (diagnosi/implementació) i els rols dels subagents
viuen a `.claude/skills/patro-a/`, `.claude/skills/patro-b/` i `.claude/agents/`.*
