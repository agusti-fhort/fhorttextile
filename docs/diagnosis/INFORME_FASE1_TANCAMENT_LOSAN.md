# FASE 1 · Tancament — neteja acotada + sembra de GradingRules (informe)

> Staging · BD `ftt_staging` · schema `fhort` · branca `dev`. Data: 2026-07-18.
> Autoritzat per Agus. Dades només, dry-run primer, commits d'un concern. NO push.

## Part 1 — Neteja acotada (OPCIÓ 2: "esborrar només el net")

Flag `--only-clean` afegit a `cleanup_losan_old` (config `ONLY_CLEAN_*` a `losan_ss27.py`).
Refs vives re-verificades a l'execució (no es va confiar en l'escaneig previ): cap nova.

**Eliminats:**

| model | id | clau natural | arrossegat |
|---|---|---|---|
| GradingRuleSet | 111 | 'EU ALPHA LOS TOP KNIT REGULAR V01' (customer LOS, origen None) | +16 GradingRule |
| SizeSystem | 49 | GIRL_LOS_02 | +9 SizeDefinition |

**NO tocats (deute anotat):** ruleset **104** ('LOS Kids Knit Regular 2Y - 12Y') + system
**GIRL_LOS_03** + els **4 SizingProfile default** (SWEATSHIRTS_MIDLAYERS × TODDLER_GIRL/BOY +
GIRL/BOY, `is_default=True`). Es resoldran al domini SizingProfile en el futur.

## Part 2 — Sembra de GradingRules (addendum B3-estès)

Config JSON versionable: `fhort/pom/seed_data/grading_rules_losan_ss27_v1.json`.
Command idempotent `seed_losan_rules` (--dry-run per defecte). Les regles se sembren sobre els
contenidors B3 resolts per **identitat natural** (LOS + size_system + garment_type_item + fit
REGULAR), no per nom.

**Convencions (calcades del precedent LOS ruleset 104; motor NO tocat):**
- `logica = LINEAR` sempre · `increment` (legacy) = `increment_base`.
- `talla_base` = la talla **més petita** (ordre 1) del size_system del contenidor. ⚠️ La talla
  base/sample formal està pendent de Montse; s'usa la convenció LOS existent (104 usa la petita).
- Break ancorat **per etiqueta** (`talla_break_label`); `talla_break_pos=NULL` (cache opcional que
  el motor canònic no llegeix — `pom/services.py:747`).

**Regles creades (36 total; tots els 27 codis POMMaster validats contra BD, cap no resolt):**

| contenidor (identitat) | size_system | base | break | regles |
|---|---|---|---|---|
| kids girl dress_simple | GIRL_LOS_01 | 2 | 9/10 | **18** |
| youth girl bikini | YOUTH_GIRL_LOS_01 | 8 | — | **11** |
| newborn baby_top | NEWBORN_LOS_01 | 00/01 | — | 1 |
| youth girl trousers | YOUTH_GIRL_LOS_01 | 8 | 14 | 1 |
| man polo | MAN_LOS_01 | S | — | 3 |
| woman num trousers | WOMAN_NUM_LOS_01 | 36 | — | 1 |
| man num trousers | MAN_NUM_LOS_01 | 38 | — | 1 |

Spot-check: CH(dress) ib=1.10 ibreak=2.20 break='9/10' · L.5(dress 0/0) ib=0 ibreak=0 break='9/10'
· B3(bikini) ib=1.60 ibreak=None break=None · WA(youth trousers) ib=1.50 ibreak=2.00 break='14'. ✓

**POMs no resolts:** cap (27/27 codis existeixen a POMMaster).

**Pendents (13, NO sembrats — a l'informe per a la fase de mesures / Montse):**
- Kids dress: `E (obs 2)` BODY&SKIRT JOIN (candidat 'CL') · `M.4 (obs 1)` SKIRT LENGTH (candidat
  'SK L') · `Z` FRILL (GAP) · `SR9`/`SR10` BOW (GAP detall).
- Bikini: `B.4` BACK CHEST (GAP) · `E.1` FRONT BOTTOM (candidat E5) · `E.2` BACK BOTTOM (GAP) ·
  `M.1` FRONT LENGTH CENTER (GAP) · `R.1`/`R.2`/`R.3` STRAPS (GAP família strap swimwear) ·
  `M.8 (PANTIE)` POM DUPLICAT TOP/PANTIE (mecanisme de sufix de secció → decisió a fase mesures).

**Watchpoints anotats (dins les regles sembrades, del JSON):** dress `K.1` SHOULDER DROP (fitxa
declara 0/0 però els valors salten al 9/10 — revisar Montse) · dress `K.2` SHOULDER TO SHOULDER
(la fitxa l'expressa en diferencial → tractat com a increment).

**Contenidors esquelet (11):** sense regles encara (reben regles quan el parser processi les
seves fitxes). Intactes.

## Notes transversals (del JSON, per a consolidació futura — NO resoltes ara)
- Col·lisions POMMaster semàntiques duplicades: T.1/RI FR, L.4/NK DR FR, L.5/NK DR BK, K.2/AC SH,
  H/BIC, M-M79/DR L HPS. La config usa sempre el POMMaster del diccionari LOS.
- GAPS de diccionari LOS: Z, SR9, SR10, B4, E.2-back, M1, R1/R2/R3 (reforça petició C.12 bany).

## Verd, restart, git
- `manage.py check` → net (0 issues) després de cada commit.
- Idempotència confirmada (2n dry-run seed_losan_rules → 0 creades, 36 actualitzades).
- Servei `ftt-staging.service` reiniciat.

## Pendents d'OK d'Agus / Montse
1. **Talla base/sample formal** dels size systems LOS (ara s'usa la petita per convenció).
2. **13 pendents** de nomenclatura (GAPS diccionari + candidats a confirmar).
3. **Deute SizingProfile**: destí dels 4 defaults sobre 104/GIRL_LOS_03 (per desbloquejar la
   resta de la neteja).
