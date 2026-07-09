# MASTER PROMPT — enganxar a Claude Code (sessió única, /model opus)

Ets l'orquestrador d'una run nocturna autònoma sobre /var/www/ftt-staging (branca dev).
Autorització: PATRÓ B per a la cua sencera S0→S9, dins dels límits del protocol.

1. Llegeix sencer: ops/sprints-editor/PROTOCOL_RUN_NOCTURNA.md
   i ops/sprints-editor/SPRINT_EDITOR_ESTAT.md
2. Executa el Pas 0 (backup + tag). Si falla → STOP.
3. Executa en SEQÜÈNCIA ESTRICTA els sprints SPRINT_00.md → SPRINT_09.md de
   ops/sprints-editor/, cadascun com a transacció completa segons el protocol
   (llegir → mini-diagnosi → implementar amb subagents Sonnet → porta verda →
   tancar al doc d'estat).
4. Condicions de STOP TOTAL (no continuar mai al següent sprint):
   - porta verda impossible després de 2 intents de correcció
   - contradicció amb el disseny del sprint o amb una llei del protocol
   - qualsevol necessitat de tocar fora de l'abast declarat
   En STOP: deixa SPRINT_EDITOR_ESTAT.md impecable (últim verd, causa exacta,
   fitxers/línia) i atura't.
5. En acabar S9 (o en STOP): escriu el resum final de la run al doc d'estat
   (sprints tancats, tots els commits amb hash, migracions aplicades, decisions
   tècniques preses, pendents per a Agus).

Recorda: subagents SEMPRE Sonnet 4.6; tu (Opus) fas orquestració i revisió de diff.
Autonomia total dins d'aquestes parets; verd = continua; regla del verd.
