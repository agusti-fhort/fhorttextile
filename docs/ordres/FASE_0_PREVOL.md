# FASE_0 · PREVOL — TRAM INSTÀNCIA · EXECUCIÓ AUTÒNOMA 02/08

REGLES DE LA TARDA (valen per a TOTES les fases, no es repeteixen):
- Seqüència estricta: FASE_0 → 1 → 2 → 3 → 4. Cap fase comença sense els green
  flags de l'anterior, EXCEPTE via protocol STOP-i-SALTA (sota).
- STOP-i-SALTA: un node concret bloquejat (conflicte inesperat, línia que no és
  on el dossier diu i no es retroba, test que no s'explica) → marca'l PENDENT
  al report de la fase amb el motiu, i CONTINUA amb la resta de nodes. Una fase
  amb PENDENTs pot tancar en verd si els seus green flags globals passen.
  CONTRADICCIÓ DE PARADIGMA (el codi contradiu una decisió ratificada, una
  migració falla, un green flag global vermell sense explicació) → atura la
  fase, escriu el report parcial, i NO comencis la següent si en depèn.
- Cap push · cap fitxer de docs/ dins de cap commit · un concern per commit ·
  git add selectiu · manage.py check abans de cada commit backend · git log -1
  després · res visible per a cap usuari: byte-idèntic o revert.
- ⚠ TRAMPA B5 (dossier §II.14): `base_measurements` és accessor a TRES models
  diferents — cap grep per aquest nom sense qualificar el model.
- Fonts al servidor: docs/diagnosis/DOSSIER_INSTANCIA_POM.md (el registre dels
  487 nodes — LA font de línies) · PLA_EXECUCIO_TRAM_C.md (decisions D1-D3
  ratificades) · MAPA_TOC_INSTANCIA.md.

## FEINA DE FASE_0

0.1 Entorn: git log -1 (anota HEAD) · git status net (DECISIONS.md o similars
    bruts → stash-report, mai a cap commit) · ftt-staging.service actiu ·
    curl -H "Host: staging.fhorttextile.tech" 127.0.0.1:8001/api/schema/ → 200.
0.2 LLEGEIX: PLA_EXECUCIO_TRAM_C.md sencer (les decisions D1-D3 del capdamunt
    manen) · DOSSIER §II.10, §II.13, §II.15, §II.16.
0.3 RE-CENS DELTA: el dossier és de HEAD 72d2e579. Si HEAD ha mogut:
    git diff 72d2e579..HEAD --stat sobre backend/ i frontend/src/ → per a cada
    fitxer tocat que aparegui al dossier, re-localitza els seus nodes (línia
    d'avui). Delta trivial (línies mogudes, forma igual) → continua. Node
    CANVIAT/DESAPAREGUT o lector/escriptor NOU → anota'l; si afecta FASE_1,
    STOP; si afecta 2/3, PENDENT a la fase corresponent.
0.4 CLONA LES EINES (dossier §II.15, "calcar, no inventar"):
    - c1_audit_counts.sql → cins_audit_counts.sql (columna instancia)
    - c1_audit_constraints.sql → cins_audit_constraints.sql
    - amplia onada1_dump_superficies.py amb les superfícies de FASE_2/3 que
      encara no cobreixi (mira quines toca cada fase i afegeix-les)
    Tot a backend/scripts_tmp/, fora de git.
0.5 CAPTURA T0 DE LA TARDA: fumeig base-stages (mètode C1: shell Django, models
    467/548/182, md5 SENSE la 1a línia) + dump de superfícies complet + còpia
    de /api/schema/. Guarda-ho amb sufix _T0_20260802.

REPORT: docs/diagnosis/REPORT_FASE_0.md — HEAD, delta del re-cens, eines
clonades, md5 T0. Veredicte final: «FASE_1 POT ARRENCAR» o motiu del STOP.
