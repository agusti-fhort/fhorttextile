# ORDRE · Sembra graduació BRW · Denim + Exterior (Patró B)

Data: 2026-09-21 · Branca: `dev` (staging, cap push) · Font: `/root/GUIA_ENTRADA_BRW_DENIM_EXTERIOR.xlsx`

## Commits (locals a `dev`, per revisar i fer push des de SSH)

| # | SHA | Missatge |
|---|---|---|
| 1 | `41d0e7ed` | `data(sembra-brw): joc canònic de graduació BRW denim+exterior (COMMIT 1)` — `ops/sembra_brw/graduacio_denim_exterior.json` |
| 2 | `220971f8` | `feat(pom): sembra_graduacio_brw — POMs/àlies/graduació denim+exterior (COMMIT 2)` — `backend/fhort/pom/management/commands/sembra_graduacio_brw.py` |
| 3 | `bbe435a6` | `test(pom): sembra_graduacio_brw — idempotència, diff de POM, repunt, FIX (COMMIT 3)` — tests + fix petit (`editat_at` al repunt) |
| 4 | `224edd95` | `fix(sembra-brw): àlies del JSON canònic porten pom_desti_codi/es_instancia explícits` — completa COMMIT 1: sense això, BB i R5 haurien resolt al POM equivocat |

`git show <sha>` per revisar cada peça individualment.

## PAS 0 — Troballes que van fer ATURAR abans de construir (resoltes amb el CTO)

1. **Tolerància (TOL−/TOL+ del full 4).** `GradingRule` no té cap camp de tolerància.
   Decisió: **s'omet d'aquest sembra.** Es conserva com a `tolerancia_referencia` al JSON
   (COMMIT 1) per si mai cal decidir on viu (deute anotat, NO és a `POMMaster.tolerancia_default_*`
   perquè contaminaria el catàleg global del tenant).
2. **RT, PR4, PR5 (full 4).** Cap POM de catàleg ni àlies BRW. Exclosos, reportats com a
   PENDENT al dry-run/apply. **Escalar a la Montse.**
3. **R4 vs R2 (full 4).** L'àlies BRW `R4` apunta al mateix POM (`R2`) que la fila pròpia
   `R2` del full, amb valors diferents. `GradingRule` no té eix d'instància
   (`unique_together=(rule_set,pom)`): exclòs, es manté només la regla de `R2`.
   **Escalar (decisió d'arquitectura: si `R4`/`PR4`/`PR5` han de tenir POM propi).**
4. **Joc DENIM absent a staging** (a diferència de la diagnosi de PROD, que el donava per
   existent i buit). Resolt amb `--create-run`: crea `SYS_BRW_01` i el contenidor
   `BRW Denim` NOMÉS si no existeixen pel nom — a PROD els hauria de trobar sempre.
5. **Full 0 (ORDRE) vs full 4 (DENIM), contradicció.** El full 0 diu «FT queda sense
   regla»; el full 4 (font de dades, autoritativa) diu que és **FE** qui queda sense
   regla (nota explícita a la fila). FT té regla completa i resol net contra el catàleg.
   Es tracta com un error de transcripció del resum.
6. **Estat "avui" del full 2 (àlies) obsolet a staging.** Els commits `035d51fb`/`cae39c4c`
   (16-21/09, una altra sessió) ja havien tocat el repunt d'àlies retirats: a staging,
   `T14` no existeix, `BF`/`BB` ja apuntaven correctament. El command no assumeix cap
   estat de partida — només imposa l'estat final ("HA D'APUNTAR A"), que sí és inequívoc.
   Verificat idempotent igualment.

## COMMIT 1 — JSON canònic

`ops/sembra_brw/graduacio_denim_exterior.json` (1138 línies, NO committar-lo a `main`
sense revisió — ja és a `dev`). Conté 2 POMs nous, 4 àlies, 14 regles exterior i 29 files
denim (valors literals, sense arrodonir), més `avisos_pas0` i `pendents` explicats a dalt.

## COMMIT 2 — Comanda `sembra_graduacio_brw`

```
venv/bin/python manage.py sembra_graduacio_brw --customer BRW --create-run            # dry-run
venv/bin/python manage.py sembra_graduacio_brw --customer BRW --create-run --apply    # escriu
```

Dry-run **escriu de debò dins la transacció i fa rollback** (així els blocs 2-4 veuen
els POMs/àlies que el bloc anterior acaba de crear, sense falsos PENDENT).

### Sortida del dry-run (idèntica a l'apply, excepte que aquest fa rollback)

```
=== sembra_graduacio_brw · DRY-RUN (escriu dins la transacció i fa rollback) ===

--- 1 · POMs nous ---
  B2     Width 10 cm below waist                       CREAT
  I8     Underarm sleeve seam length                   CREAT

--- 2 · Àlies BRW ---
  B2     → B2     accio=CREAT
  BF     → BF     accio=IGUAL
  BB     → B      accio=IGUAL
  R5     → R3     accio=CREAT

--- 3 · Joc «BRW Exterior» ---
  ruleset: CREAT «BRW Exterior»
  [14 regles LINEAR, delta uniforme, sense breaks]

--- 4 · Joc «BRW Denim» ---
  sistema: CREAT «SYS_BRW_01» (7 talles)
  ruleset: CREAT «BRW Denim»
  [23 regles: LINEAR+breaks o STEP segons el patró; BB = DEDUP amb B]

--- PENDENTS (no escrits) ---
  FE, RT, PR4, PR5, R4 (motius al full 0), BB (nota informativa, no és un pendent real)
```

### Apply al banc d'staging — verificat (ORM)

| Bloc | Resultat |
|---|---|
| POMs nous | `B2` (id=1124), `I8` (id=1125) |
| Àlies BRW | `B2→B2`, `BF→BF`, `BB→B` (es_instancia), `R5→R3` (es_instancia) |
| `SYS_BRW_01` | id=77, talles `P·32·34·36·38·40·42` |
| `BRW Exterior` | id=248, `size_system=ALPHA_EU_W`, àmbit `OUTERWEAR`, **14 regles** |
| `BRW Denim` | id=249, `size_system=SYS_BRW_01`, àmbit `BOTTOMS`, **23 regles** (29 files del full − FE sense regla − BB dedup amb B − RT/PR4/PR5/R4 pendents) |

**Segona passada `--apply` → 0 canvis** (tot `IGUAL`/`DEDUP`, cap `CREAT`/`ACTUALITZAT`) — idempotència verificada al banc.

## COMMIT 3 — Tests (escrits, no executats)

`backend/fhort/pom/test_sembra_graduacio_brw.py`: idempotència (2 passades), POM existent
amb nom diferent → `DIVERGEIX` sense sobreescriure, àlies repuntat amb rastre
(`origen='SEMBRA0921'` + `editat_at`), àlies ja correcte intacte, denim reutilitza el joc
existent (mai en duplica un altre), 4 deltes iguals → `LINEAR` sense breaks, delta no
uniforme → `PENDENT`, 6 deltes a 0 → `FIXED`. `py_compile` net.

## Camps del model usats

- `POMMaster`: `codi_client`, `nom_client` (només aquests dos — família/lògica NO són
  camps del model, NOM(ES) no s'escriu enlloc, viu a `TranslationCache` auto-DeepL).
- `CustomerPOMAlias`: `customer`, `client_code`, `pom`, `es_instancia`, `origen`,
  `editat_at` (clau natural real: `(customer, client_code, pom)`).
- `GradingRuleSet`: `nom`, `size_system`, `customer`, `origen=CLIENT_RUN`, `actiu`.
- `RuleSetScopeNode`: `rule_set`, `node_type=GROUP`, `garment_group`.
- `GradingRule`: `rule_set`, `pom`, `talla_base`, `logica`, `increment_base`, `breaks`
  (JSON, ≤3 intervals), `valors_step` (JSON, patrons irregulars), `actiu`. **Cap camp de
  tolerància** (deute anotat, punt 1 de dalt).
- `SizeSystem`/`SizeDefinition`: creats per `SYS_BRW_01` amb `--create-run`.

## Pendents per al CTO abans de PROD

1. **I8 pendent de benedicció de la Montse** (explícit a la guia) — no desplegar a PROD
   sense confirmar-ho.
2. **Model amb base 36 vs proto a 34** (nota del full 0) — demanar a la Marta abans
   d'assignar el joc denim a aquell model concret.
3. **RT / PR4 / PR5 / R4** — escalar (v. punts 2-3 de dalt).
4. **Tolerància** — decidir on ha de viure una tolerància per (ruleset, pom) abans que
   torni a aparèixer en un altre sembra (deute d'arquitectura, no d'aquesta peça).
5. Revisar la cadena de commits (`git show 41d0e7ed 220971f8 bbe435a6`) i fer push des
   de SSH quan es doni per bo.
