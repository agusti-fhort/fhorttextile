# MÈTODE_AGENTS — Com treballem amb agents a FHORT Textile Tech

> Document de mètode (treball intern). Viu al servidor, fora de git, com `ESTAT_PROJECTE.md`.
> Captura els patrons d'agents validats a la pràctica. S'amplia amb l'experiència de cada fase.
> Origen: validat amb la Fase B (diagnosi) i la cadena D-3 (primera implementació), juny 2026.

---

## 0. Principi rector

Els agents fan la **feina pesada** (llegir molt codi, escriure peces acotades, verificar);
les **decisions d'arquitectura i de producte les prenem els humans** (Agus com a CTO/decisor,
Claude com a CTO tècnic). L'agent és el tercer actor de la metodologia de sempre (Claude Code a
VS Code), no un substitut del criteri.

Regla d'or heretada de la metodologia de tres actors: **l'agent MAI fa push ni deploy.** El push
el fa l'Agus des de SSH, sempre. L'agent escriu a staging i s'atura.

---

## 1. Els tres patrons (quin equip per a quina feina)

La pregunta operativa abans de qualsevol tasca: **quin tipus de feina és?** D'aquí surt l'equip.

### Patró A — DIAGNOSI (entendre sense tocar)
**Quan:** cal entendre el sistema real abans de decidir o construir. Read-only absolut.
**Equip:**
- `director-investigacio` — descompon l'objectiu en tasques d'investigació acotades, ordena per
  prioritat de desbloqueig, defineix criteri d'èxit. No investiga ell.
- `investigador-codi` (×N en paral·lel) — read-only; torna FETS amb referència `fitxer:línia`,
  mai opinions. grep -n + rangs, mai fitxers sencers.
- `documentador` — acumula a un únic `docs/*.md`, separant FET (amb referència) de
  `💡 PROPOSTA (a validar)`. És l'únic que escriu, i només al document.
**Eines:** Read/Grep/Glob (tots); el documentador també Write/Edit (només el doc).
**Autonomia:** AMPLA. Pot córrer fins al final i revisar-se al final, perquè res és irreversible.
Atura's i resumeix per àrea si la sessió és supervisada; mode autònom complet si no.
**Validat a:** Fase B → `docs/DIAGNOSI_FASE_B.md` (8 àrees, 15 decisions, 0 codi tocat).

### Patró B — IMPLEMENTACIÓ (escriure codi)
**Quan:** una peça de codi ja dissenyada i acotada s'ha de construir.
**Equip:**
- `implementador` — l'ÚNIC que escriu codi de producte. Scope estricte (una peça, ni més ni
  menys). Commit per peça, paths explícits, `git log -1` després. MAI push.
- `verificador` (QA) — `manage.py check` + `npm run build` net + el diff fa el que tocava sense
  scope creep. Dret de VETO.
- `guardia-i18n` — només si la peça toca frontend. Text d'usuari amb clau `t()` + paritat
  ca/en/es. Veto. Revisa el DELTA, no tot el codebase.
- `guardia-ui` — només si la peça toca frontend. Tokens del design system (gold/cream, IBM Plex
  Mono, Tabler), criteri UI/UX (skill `frontend-design`), excepcions conegudes (Konva). Veto.
- `revisor-diff` — efectes col·laterals (imports, signals, cascades, estat compartit). Bandera
  (no veto dur, però atura per revisió del CTO).
**Eines:** l'implementador Read/Grep/Glob/Edit/Write/Bash; la resta read-only + Bash de verificació.
**Autonomia:** CONDICIONADA AL VERD. Continua sol a la peça següent NOMÉS si tots els controls
aplicables són verds; s'atura i reporta a la primera cosa vermella/bandera.
**Validat a:** cadena D-3 (4 peces, 4 commits verds, 0 push).

### Patró C — DISSENY (decisió humana)
**Quan:** una decisió d'arquitectura o de producte. NO és feina d'agents autònoms.
**Equip:** Agus + Claude, amb el codi real al davant (un agent de diagnosi pot fer la lectura
quirúrgica prèvia, read-only, per portar els fragments exactes).
**Autonomia:** CAP. La decisió la prenen els humans. L'agent només llegeix per informar.
**Validat a:** la conversa de D-3 (qui governa la fase) i totes les converses de disseny del
model viu.

---

## 2. Definició de VERD (la porta dura del patró B)

Una peça és **verda** i l'agent pot continuar SOLAMENT si TOTS els controls aplicables passen:
- `python manage.py check` net.
- `npm run build` net (si la peça toca frontend).
- `verificador` VERD (compila + fa el que tocava + sense scope creep).
- `guardia-i18n` sense veto (si toca frontend).
- `guardia-ui` sense veto (si toca frontend).
- `revisor-diff` sense bandera.

Si **tot** verd → continua sol. Si **qualsevol** vermell/bandera → s'atura, reporta
`fitxer:línia` + quin control + per què, i ESPERA el CTO. No construeix sobre una peça no-verda.

---

## 3. Regles dures (passi el que passi, a tots els patrons)

- **MAI push, MAI deploy.** L'agent fa commits locals; el push el fa l'Agus des de SSH.
- **MAI PROD, MAI branca `main`.** Tot a staging `dev`.
- **Scope estricte.** Una peça fa el que diu. Problemes vistos fora de scope → s'ANOTEN al
  report, NO es toquen.
- **`git add` de paths explícits.** Mai `-A`/`-u`. Un commit per peça. `git log -1` després.
- **Zones intocables.** No tocar POMs / grading engine / motor de patrons / (al servidor
  PROJECTES) assessment, trading, webs, post-me — tret que la peça ho demani explícitament.
- **Migracions:** `migrate_schemas` mai `--schema`; auditar columnes directament a BD (django-
  tenants pot donar OK enganyós). `migrate_schemas --list` NO és read-only en aquesta versió.
- **Documents de treball fora de git:** `.claude/`, `*_MODEL_VIU.md`, `DIAGNOSI_*.md`,
  `ESTAT_*.md`, `MAPA_*.md`, `MOTOR_*.md` viuen al servidor, no entren a commits.

---

## 4. Aprenentatges concrets (de la pràctica, s'amplien)

- **Els controls funcionen:** a D-3 el verificador va VETAR la peça 1 (un comentari deia "cap
  automatisme" però `services_c.py:91` fa Pending→Dev). Es va corregir dins scope → VERD. Si
  aturen un comentari imprecís, aturen un error real.
- **Les anotacions fora d'scope són valuoses:** l'implementador va trobar el 3r escriptor de fase
  (Pending→Dev), els residus a `advance_phase` i el tema de la reobertura — i NO els va tocar,
  els va anotar. Disciplina anti-scope-creep que cal mantenir.
- **El context de negoci no és al codi:** el Pending→Dev semblava un automatisme de fase a
  netejar, però és el **trigger de facturació** (el model comença a consumir → comença a meritar).
  Lliçó: un automatisme sense el seu "per què" sembla un error. Documentar SEMPRE el per què.
- **Construir el mecanisme, no obrir la porta:** el guard D-1 té el paràmetre `allow_reopen_sealed`
  però cap endpoint l'exposa → bloqueja per defecte fins que es dissenyi el flux de reobertura.
  Patró: construeix el mecanisme complet, però no l'habilites fins que el flux que el justifica
  està dissenyat.
- **Lectura quirúrgica abans de decidir:** abans de cada decisió de disseny, un prompt read-only
  que porti els fragments exactes (`fitxer:línia`) val molt més que decidir sobre el resum d'una
  diagnosi. Es decideix amb el codi real al davant.

---

## 5. Flux operatiu d'una sessió tipus

1. **Decidir el patró** (A diagnosi / B implementació / C disseny) segons la feina.
2. Si cal entendre primer → **lectura quirúrgica** (agent de diagnosi, read-only) que porti els
   fragments.
3. **Disseny humà** (Agus + Claude): decidir i trossejar en peces acotades (1 commit cadascuna).
4. **Implementació** (patró B): cadena de peces amb la regla del verd; commit per peça; mai push.
5. **Revisió humana** del/s canvi/s de substància amb el diff real (`git show <hash>`).
6. **Push** per l'Agus des de SSH; `git log` per verificar que han entrat a `origin/dev`.
7. **Documentar** decisions diferides i el "per què" de tot el que no és obvi.

---

## 6. Infraestructura d'agents

- Definicions a `.claude/agents/*.md` dins el repo de staging (`/var/www/ftt-staging`).
- Protocols mestres a `.claude/PROTOCOL_*.md`.
- Una SOLA sessió de Claude Code els orquestra (no cal obrir-ne una per agent; els subagents els
  invoca l'orquestrador internament).
- Equips actuals:
  - Diagnosi: `director-investigacio`, `investigador-codi`, `documentador` + `PROTOCOL_FASE_B.md`.
  - Implementació: `implementador`, `verificador`, `guardia-i18n`, `guardia-ui`, `revisor-diff`
    + `PROTOCOL_IMPLEMENTACIO.md`.

---

*Mètode viu. S'amplia amb cada fase. Propera ampliació prevista: aprenentatges dels guardians
i18n/UI quan s'estrenin amb el dashboard del model (primera peça frontend del model viu).*
