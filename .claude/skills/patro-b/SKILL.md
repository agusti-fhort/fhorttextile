---
name: patro-b
description: Protocol d'IMPLEMENTACIÓ (Patró B) de FTT — construir una peça de codi ja dissenyada i acotada, amb qualitat verificada a cada pas i autonomia condicionada al verd. Invoca-la quan un brief demana implementar/construir una cadena de peces sobre staging dev. Commit per peça, MAI push (el push el fa l'Agus).
---

# Patró B — IMPLEMENTACIÓ (escriure codi)

Quan una peça ja dissenyada i acotada s'ha de construir. Autonomia **condicionada al verd**.
Aquesta skill és la casa versionada del protocol d'implementació (origen: l'antic
`PROTOCOL_IMPLEMENTACIO`, ara succeït per aquest fitxer). Les lleis dures són les del
`CLAUDE.md` de l'arrel.

## Ordre de treball per peça
**implementador → verificador → guardians (i18n, ui) → revisor-diff.**
- **`implementador`** — l'ÚNIC que escriu codi de producte. Scope estricte (una peça, ni
  més ni menys). Abans d'editar, llegeix el codi real (grep -n + rangs). Fa el canvi,
  itera fins a verd, commiteja amb paths explícits, `git log -1`. MAI push.
- **`verificador`** (VETO) — `manage.py check` + (si toca front) `npm run build` nets + el
  diff fa el que tocava sense scope creep.
- **`guardia-i18n`** (VETO, només si toca frontend) — text d'usuari amb `t()` + paritat
  ca/en/es. Revisa el DELTA, no tot el codebase.
- **`guardia-ui`** (VETO, només si toca frontend) — tokens del design system, icones
  Tabler outline, criteri UI/UX, excepcions conegudes (Konva). Revisa el DELTA.
- **`revisor-diff`** (BANDERA, no veto dur) — efectes col·laterals: imports, signals,
  cascades, estat compartit, atomicitat, migracions.

## Disciplina de commits (lleis del CLAUDE.md)
- **Un focus per commit**, `git add` de paths explícits (mai `-A`/`-u`), `git log -1`
  després. **MAI push** (el fa l'Agus des de SSH). Mai PROD, mai `main`.
- Problemes vistos fora de scope → s'ANOTEN al report, no es toquen.

## Loops de regeneració (qualitat abans del commit)
- **Si el verd falla, itera fins a verd abans de continuar.** No es passa a la peça
  següent amb res vermell.
- **Optimitza el codi generat abans del commit** — no el primer esborrany. El commit ha
  de ser la versió neta, no el rascada inicial.

## Regla d'autonomia — VERD = continuar, VERMELL = aturar
Després de cada peça, l'orquestrador passa el diff pels controls aplicables. Una peça és
**VERDA** si: `manage.py check` net + (si toca front) `npm run build` net + verificador
VERD + guardians sense veto (els que apliquin) + revisor-diff sense bandera.
- **Tots verds** → l'agent continua sol a la peça següent de la cadena.
- **Qualsevol vermell/bandera** → s'atura, reporta EXACTAMENT què ha fallat
  (`fitxer:línia`, quin control, per què) i espera el CTO.

## Sessions autònomes
Corre ample sense demanar confirmació **mentre el verd aguanti**. Consum mínim de tokens:
lectures quirúrgiques amb rangs (`view_range`/grep -n), mai fitxers sencers. L'objectiu és
una cadena de peces verdes; el report final llista l'estat de cada peça, els hashos de
commit, i què ha de fer el CTO (revisar la cadena amb `git show <hash>` i fer push des de SSH).
