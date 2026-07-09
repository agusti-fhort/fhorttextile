# PROTOCOL — Implementació (cadena de peces, autonomia condicionada al verd)

Objectiu: implementar peces acotades del Model Viu sobre staging (`dev`), amb qualitat
verificada a cada pas i SENSE fer push (el push el fa el CTO des de SSH).

## Equip
- `implementador` — escriu la peça (scope estricte, commit per peça, mai push).
- `verificador` — compila/build + diff fa el que tocava sense scope creep. Dret de veto.
- `guardia-i18n` — text d'usuari amb clau t() + paritat ca/en/es. Veto. (Només si la peça toca frontend.)
- `guardia-ui` — tokens del design system + criteri UI/UX. Veto. (Només si la peça toca frontend.)
- `revisor-diff` — efectes col·laterals (imports, signals, cascades, estat compartit). Bandera.

## Regla d'autonomia: CONTINUAR SI VERD, ATURAR-SE SI VERMELL
Després de cada peça, l'orquestrador passa el diff pels controls aplicables:
- **VERD** = `manage.py check` net + (si toca front) `npm run build` net + verificador VERD +
  guardians sense veto (els que apliquin) + revisor-diff sense bandera.
- Si **TOTS verds** → l'agent CONTINUA SOL a la peça següent de la cadena.
- Si **QUALSEVOL vermell/bandera** → s'ATURA, reporta EXACTAMENT què ha fallat
  (`fitxer:línia`, quin control, per què) i ESPERA el CTO. No intenta seguir endavant
  construint sobre una peça no-verda.

## Regles dures (passi el que passi)
- **Commit per peça, MAI push.** L'agent fa commits locals a `dev`; el push el fa el CTO.
- `git add` de paths explícits, mai `-A`/`-u`. `git log -1` després de cada commit.
- Mai PROD, mai `main`.
- Mai tocar POMs / grading engine / motor de patrons / zones intocables, tret que la peça
  ho demani explícitament.
- Scope estricte: una peça fa el que diu, ni més ni menys. Problemes vistos fora de scope →
  s'ANOTEN, no es toquen.

## CADENA ACTUAL — D-3: la fase la governa l'avanç de gate (l'humà), no fitting/tasques automàticament
> Context: la diagnosi confirma que l'avanç de fase JA és 100% humà (cap signal/automatisme).
> El problema és cosmètic/estructural: dos punts d'escriptura de `fase_actual`, comentari
> mentider, TODO mort, i el segellat del grading acoblat al camí equivocat (fitting).
> Decisió CTO: un sol amo (l'avanç de gate); fitting/tasques són INDICADORS de maduresa;
> producció és terminal (tanca el procés).

**Peça 1 — Neteja del mort (risc ~0).**
- Treure el TODO `recalculate_current_phase` (`fitting/services.py:696`) que apunta a funció
  inexistent.
- Corregir el comentari mentider de `tasks/signals.py:6` ("l'únic amo és fitting.advance_phase"):
  documentar l'estat real (dos punts d'escriptura humans, cap automatisme) o deixar-lo coherent
  amb la decisió final (amo = avanç de gate).
- Sense canvi de comportament. Backend.

**Peça 2 — Desenganxar el segellat de fitting i posar-lo a l'avanç de gate (+ guard D-1).**
- El segellat (`GradingVersion.aprovada=True`, avui a `fitting/services.py:705-710` dins
  `advance_phase`) passa a ser conseqüència de l'AVANÇ DE GATE, no de tancar la sessió de fitting.
- Afegir GUARD (D-1): no superar/desactivar una `GradingVersion` `aprovada` sense reobertura
  EXPLÍCITA registrada (a `close_piece_fitting` i al mirror `resolve_size_check`).
- És la peça de substància. Backend. Probable migració? (revisar.)

**Peça 3 — `fitting.advance_phase` deixa d'escriure `fase_actual`.**
- L'avanç de gate (`tasks/services_d.py`) queda com a ÚNIC amo de `fase_actual`.
- `fitting.advance_phase` es queda gestionant la sessió/peces (indicador de maduresa), sense
  escriure la fase del model. Backend.

**Peça 4 — Producció és terminal.**
- Avançar a producció (TOP) marca `Model.estat → Tancat` (value `'EnCurs'`/`'Tancat'` correctes,
  no labels — vigila l'enum). Segella el patrimoni; el model no torna a desenvolupament.
- Recull que "a producció no es torna a tocar res". Backend.

> Peces 1-4 són TOTES backend → guardians i18n/ui NO apliquen aquí (s'activaran al dashboard).
> Verificador + revisor-diff sí apliquen a totes.

## Final de cadena
Quan les 4 siguin verdes (o aturat a la que falli), report final: estat de cada peça, hashos
de commit, i el que el CTO ha de fer (revisar la cadena de commits i fer push des de SSH).
NO facis push tu.

## Arrencada (prompt del CTO)
> Llegeix `.claude/PROTOCOL_IMPLEMENTACIO.md`, `DISSENY_MODEL_VIU.md` i `DIAGNOSI_FASE_B.md`.
> Executa la CADENA D-3 com a orquestrador: implementador fa la peça 1, els controls la
> verifiquen; si VERD continua a la 2, i així fins a la 4; si alguna surt VERMELL, atura't i
> reporta. Commit per peça, MAI push. Report final amb l'estat de les 4 peces.
