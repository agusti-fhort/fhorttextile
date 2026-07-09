# PROTOCOL — Diagnosi Fase B (autònom, read-only)

Objectiu: produir `docs/DIAGNOSI_FASE_B.md`, el mapa global de com reencaixar TOT el
sistema FHORT al model viu definit a `DISSENY_MODEL_VIU.md`, abans de tocar cap línia de codi.

## Mode de treball
- Nivell CONSERVADOR + suggeriments. Els agents diagnostiquen i documenten FETS; els
  suggeriments de disseny/sprints/pantalles s'admeten però SEMPRE marcats `💡 PROPOSTA (a validar)`.
- READ-ONLY de codi absolut. Escriptura permesa NOMÉS a `docs/DIAGNOSI_FASE_B.md`.
- Staging (`/var/www/ftt-staging`, branca `dev`). Mai PROD, mai main.
- grep -n + rangs, mai fitxers sencers. `migrate_schemas --list` PROHIBIT (no és read-only aquí).

## Seqüència
1. `director-investigacio` llegeix DISSENY_MODEL_VIU.md i MAPA_SISTEMA.md i produeix el pla
   de tasques d'investigació ordenat, començant OBLIGATÒRIAMENT per la col·lisió SizeFitting.
2. Per cada tasca, `investigador-codi` retorna fets amb referències fitxer:línia.
3. `documentador` acumula a `docs/DIAGNOSI_FASE_B.md` separant fets de propostes.
4. Si una troballa és transversal, el director reordena abans de continuar.
5. Es cobreixen les 7 àrees + capa de disseny. Al final, el documentador omple el resum
   executiu i la llista de riscos/decisions obertes per al CTO.

## Atura't i resumeix
Quan s'acaba una àrea, ATURA'T i fes un resum del que has trobat abans de passar a la
següent. No facis les 12 seccions de cop. Així el CTO pot corregir el rumb entremig.

## Criteri de qualitat
El document està bé quan, llegint-lo, el CTO pot decidir els sprints SENSE haver de tornar
a obrir el codi per a les preguntes bàsiques. Cada afirmació sobre el codi té referència;
cada proposta està marcada; res s'ha modificat.

## El que NO s'ha de fer
- No escriure ni modificar codi, migracions, configs.
- No decidir disseny final de pantalles (només propostes marcades).
- No tocar les zones intocables del servidor PROJECTES (assessment, trading, webs, post-me).

## Arrencada (prompt que dona el CTO a la sessió de Claude Code)
> Llegeix `.claude/PROTOCOL_FASE_B.md` i executa'l. Actua com a orquestrador: fes que
> `director-investigacio` produeixi el pla començant per la col·lisió SizeFitting, deriva
> les tasques a `investigador-codi`, i fes que `documentador` acumuli a
> `docs/DIAGNOSI_FASE_B.md`. Treballa read-only sobre staging. Quan acabis una àrea,
> atura't i resumeix abans de passar a la següent.
