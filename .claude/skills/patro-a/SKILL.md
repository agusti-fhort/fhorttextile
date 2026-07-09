---
name: patro-a
description: Protocol de DIAGNOSI (Patró A) de FTT — entendre el sistema real abans de decidir o construir, sense tocar cap línia. Read-only absolut. Invoca-la quan un brief demana diagnosticar, mapejar, auditar o investigar el radi d'un canvi abans d'implementar. Produeix UN doc a docs/diagnosis/ amb cada afirmació ancorada a fitxer:línia.
---

# Patró A — DIAGNOSI (entendre sense tocar)

Quan cal entendre el sistema real abans de decidir o construir. **Read-only absolut.**
Aquesta skill és la casa versionada del protocol de diagnosi (origen: l'antic
`PROTOCOL_FASE_B`, ara succeït per aquest fitxer). En cas de dubte sobre una llei de
mètode, mana el `CLAUDE.md` de l'arrel.

## Read-only estricte (línia dura)
- **Cap escriptura de codi, cap commit, cap migració, cap restart, cap comanda que
  modifiqui estat.** Si una comanda no és lectura pura, NO es fa.
- `grep -n` + lectura de RANGS, mai fitxers sencers (consum mínim de tokens).
- `migrate_schemas --list` PROHIBIT (no és read-only en aquesta versió de django-tenants).
- Staging `/var/www/ftt-staging`, branca `dev`. Mai PROD, mai `main`.
- L'única escriptura permesa és la del documentador, i només al doc de diagnosi.

## Equip
- **`director-investigacio`** — descompon l'objectiu del brief en tasques d'investigació
  acotades, les ordena per prioritat de desbloqueig i defineix el criteri d'èxit de
  cadascuna. No investiga ell; si una troballa canvia les preguntes posteriors, reordena.
- **`investigador-codi` ×N (en paral·lel, un per bloc)** — read-only; torna FETS amb
  referència `fitxer:línia`, mai opinions. Marca "TROBALLA TRANSVERSAL" si topa amb una
  relació que afecta altres blocs.
- **`documentador`** — l'ÚNIC que escriu, i només al doc. Acumula els fets separant FET
  (amb referència) de `💡 PROPOSTA (a validar)`.

Una sola sessió de Claude Code orquestra tot l'equip (no cal una sessió per agent).

## Output — UN document
Un únic fitxer: **`docs/diagnosis/DIAGNOSI_<TEMA>_<DATA>.md`** (data ISO, p.ex.
`DIAGNOSI_CATALEG_COMERCIAL_2026-07-07.md`). Estructura calcada de les diagnosis reals:

1. **Capçalera:** títol `# DIAGNOSI — <tema>`; línia amb Data · `Patró A (READ-ONLY)` ·
   staging/branca; abast en 1-2 línies; nota de convenció:
   `fitxer:línia` + `"NO EXISTEIX" = confirmat absent al codi (no especulat)`.
2. **Resum executiu (director)** — les 4-6 conclusions que desbloquegen la decisió.
3. **BLOCs temàtics** — un per àrea investigada. Dins cada bloc, fets ancorats a
   `fitxer:línia`, i al final un **`Veredicte <bloc>: llest / cal X`** curt.
4. **TAULA FINAL de riscos** (o EXISTEIX/FALTA/DIFERENT) per al CTO.

## Regles de contingut
- **Cada afirmació sobre el codi porta `fitxer:línia`.** Sense font verificada →
  "PENDENT DE VERIFICAR", mai una afirmació nua.
- **Si no existeix al codi: escriu "NO EXISTEIX".** Mai especular, mai inventar el
  sistema de memòria. Consulta només l'arrel de `docs/diagnosis/` (vigents), mai
  `docs/diagnosis/arxiu/` com a font de veritat.
- Les propostes de disseny s'admeten però SEMPRE marcades `💡 PROPOSTA (a validar)`,
  clarament separades dels fets. Les decisions són humanes (Patró C).

## Autonomia
AMPLA — res és irreversible. Pot córrer fins al final i revisar-se al final. En sessió
supervisada: atura't i resumeix en acabar cada àrea perquè el CTO pugui corregir el rumb;
en mode autònom, cobreix totes les àrees seguit. El doc està bé quan el CTO pot decidir
sense haver de reobrir el codi per a les preguntes bàsiques.
