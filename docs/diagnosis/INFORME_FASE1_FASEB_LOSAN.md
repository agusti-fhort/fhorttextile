# FASE 1 · FASE B — Implementació LOSAN SS27 (informe final)

> Staging · BD `ftt_staging` · schema `fhort` · branca `dev`. Data: 2026-07-18.
> Autoritzat per Agus. Via A5: **el gènere viu a la size library** (system per gènere),
> cap migració, cap ús de `fit_type` com a gènere. NO push.

## Resum executiu

- **B1 (catàleg v2) · B2 (size libraries) · B3 (contenidors)** → **APLICATS** a `fhort`.
- **Neteja LOS antic (addendum)** → **ATURADA (STOP)**: el guard ha trobat referències vives.
  Cap esborrat executat. Decisió pendent d'Agus (§ Neteja).
- Cap migració, cap camp nou. `manage.py check` net. Servei reiniciat.

## Ubicació del config i les eines

| artefacte | camí | rol |
|---|---|---|
| **Config versionable** | `fhort/pom/seed_data/losan_ss27.py` | totes les dades per clau natural (B1/B2/B3 + objectius de neteja). Cap lògica. |
| Command creació | `fhort/pom/management/commands/seed_losan_ss27.py` | idempotent · `--dry-run` per defecte · `--no-dry-run` escriu |
| Command neteja | `fhort/pom/management/commands/cleanup_losan_old.py` | `--dry-run` per defecte · guard dur de refs vives · **no executat** |

(Separació motor/config: s'evita l'anti-patró `seed_brownie_fw26` hardcoded.)

## Recomptes abans → després

| mètrica | abans (Fase A) | després | esperat |
|---|---|---|---|
| GarmentGroup (total) | 11 | 12 (+NEWBORN) | — |
| GarmentGroup amb contingut (types actius) | 6 | **8** | 8 ✓ |
| GarmentType total | 19 | 21 (+NEWBORN, +ACCESSORIES) | — |
| GarmentType actius | 17 | **17** (−BABY_SEPARATES −BABY_ONEPIECES +NEWBORN +ACCESSORIES) | 17 ✓ |
| GarmentTypeItem | 57 | **62** (+booties, bag, hat_cap, scarf, socks) | 62 ✓ |
| SizeSystem | 21 | 29 (+8 LOS) | — |
| GradingRuleSet total | 27 | 45 (+18 contenidors) | — |
| GradingRuleSet CLIENT_RUN LOS | 0 | **18** | 18 ✓ |

## B1 — Catàleg v2 (aplicat)

- Grup **NEWBORN** creat · type **NEWBORN** (grup NEWBORN) i type **ACCESSORIES** (grup ACCESSORIES) creats.
- 8 items `baby_*` moguts a NEWBORN amb complexity_order 1/2/3 segons el pla; **POM-maps intactes**
  (baby_top=11, baby_bodysuit=12, baby_leggings=12, baby_dress=10, baby_swimwear=9, baby_bloomers=12,
  baby_sleepbag=12, baby_sleepsuit=19).
- Items nous SENSE POM-map: `booties`→NEWBORN · `bag`/`hat_cap`/`scarf`→ACCESSORIES · `socks`→UNDERWEAR.
- **BABY_SEPARATES** i **BABY_ONEPIECES** desactivats (`actiu=False`) un cop buits.
  (DRESS i T_SHIRT ja estaven inactius des d'abans — no tocats.)
- TaskTimeEstimate: **cap sembra** (lazy `get_or_create` al primer ús, confirmat a Fase A).

## B2 — Size libraries LOSAN (aplicat)

8 systems nous · `customer_codi=LOS` · `actiu=True` · `valor_numeric=None` (designation-only) ·
sense talla base (el camp no existeix). Notació canònica respectada (2XL, 09/10, mesos ERP):

| codi | base_unit | targets | talles |
|---|---|---|---|
| NEWBORN_LOS_01 | MONTHS | BABY_GIRL, BABY_BOY, BABY_UNISEX | 00/01·01/03·03/06·06/09·09/12·12/18·18/24 (7) |
| BABY_LOS_01 | MONTHS | TODDLER_GIRL, TODDLER_BOY | 03/06·06/09·09/12·12/18·18/24·24/36 (6) |
| BOY_LOS_01 | AGE_YEARS | BOY | 2·3·4·5·6·7·8·9/10·11/12 (9) |
| YOUTH_GIRL_LOS_01 | AGE_YEARS | TEEN_GIRL | 8·10·12·14·16 (5) |
| YOUTH_BOY_LOS_01 | AGE_YEARS | TEEN_BOY | 8·10·12·14·16 (5) |
| WOMAN_LOS_01 | ALPHA | WOMAN | XS·S·M·L·XL·2XL·3XL (7) |
| WOMAN_NUM_LOS_01 | NUMERIC_EU | WOMAN | 36·38·40·42·44·46·48·50·52 (9) |
| MAN_NUM_LOS_01 | NUMERIC_EU | MAN | 38·40·42·44·46·48·50·52·54·56·58 (11) |

`GIRL_LOS_01` i `MAN_LOS_01` **ja eren correctes** (Fase A) → no tocats. Swimwear woman = subconjunt
de `WOMAN_LOS_01`, cap system propi.

## B3 — Contenidors de grading (aplicat)

18 `GradingRuleSet` · `origen=CLIENT_RUN` · `customer=LOS` · `fit_type=REGULAR` · **cap GradingRule**
(les regles per-POM entren a la fase de mesures amb la fitxa com a font). Nom `LOS <mon> <item> SS27`.
La `forma` i la `font documental` viuen al **config** (el model no té camp de nota lliure). Cap
col·lisió d'identitat: el gènere el porta el `size_system` (via A5).

Els 18: Newborn{baby_top, baby_leggings, baby_sleepsuit, baby_dress, booties} · Baby{baby_top, baby_dress}
· BOY_LOS_01·jeans · GIRL_LOS_01·dress_simple · YouthBoy{t_shirt, trousers} · YouthGirl{t_shirt,
trousers, bikini} · Woman·t_shirt · Man·polo · WomanNum·trousers · ManNum·trousers.

**Cas que A5 resol** (abans col·lidien): YouthGirl·t_shirt (break 14) vs YouthBoy·t_shirt (linear),
i YouthGirl·trousers vs YouthBoy·trousers → ara `size_system` diferent (YOUTH_GIRL_LOS_01 /
YOUTH_BOY_LOS_01) → identitats distintes, cap xoc de la constraint `uniq_client_container_identity`.

## Neteja LOS antic (addendum) — ⛔ ATURADA, decisió d'Agus

El command `cleanup_losan_old` (dry-run) ha **aturat sense esborrar res**. Escaneig complet de refs vives:

| objectiu | refs externes vives | veredicte |
|---|---|---|
| ruleset **104** '…Kids Knit Regular…' (ss=GIRL_LOS_03) | **4 SizingProfile** (id 519-522) | ⛔ bloqueja |
| ruleset **111** 'EU ALPHA LOS TOP KNIT…' (ss=MAN_LOS_01) | cap | net (esborrable) |
| system **GIRL_LOS_02** | cap | net (esborrable) |
| system **GIRL_LOS_03** | 1 ruleset (=104) + 4 SizingProfile + talla amb 19 regles_base | ⛔ bloqueja (via 104) |

**Causa arrel (sorpresa no prevista):** els 4 `SizingProfile` són
`SWEATSHIRTS_MIDLAYERS × {TODDLER_GIRL, TODDLER_BOY, GIRL, BOY} × REGULAR`, amb
**`is_default=True` i `customer=None`** → són els **perfils de talla PER DEFECTE genèrics del tenant**
per a dessuadores infantils, cablats a ruleset 104 + `GIRL_LOS_03`. El material "antic" **no és mort**:
sosté la resolució de talles per defecte. Esborrar-lo trencaria (o el PROTECT bloquejaria) aquests 4
perfils. Per l'addendum (*"referències vives → NO esborris, STOP"*), no s'ha tocat res.

**Opcions per a Agus (cap executada):**
1. **Repuntar** els 4 SizingProfiles a un grading/system nou (p.ex. un contenidor Youth/Kids
   sweatshirt de Fase 1) i llavors esborrar 104 + GIRL_LOS_03.
2. **Esborrar només el net** (ruleset 111 + system GIRL_LOS_02), que no tenen cap ref → deixar
   104/GIRL_LOS_03 fins resoldre els perfils. (Requeriria un flag `--only-clean` o retocar el config.)
3. **Ajornar tota la neteja** fins decidir el destí dels defaults de dessuadora infantil.

El command i el guard queden commitats (no executats) i llestos per quan es desbloquegi.

## Evidència i verd
- `manage.py check` → net (0 issues).
- Dry-run creació: pla complet imprès abans d'escriure (evidència a la sessió).
- Idempotència confirmada: 2n dry-run post-aplicació → 34× "ja existeix", recomptes estables.
- Dry-run neteja: STOP net al guard, cap esborrat.
- Servei `ftt-staging.service` reiniciat al final.

## Pendents d'OK d'Agus
1. **Neteja LOS antic** — triar opció 1/2/3 de dalt (els 4 default SizingProfiles).
2. (Ja resolt a Fase A: rename GIRL_LOS_01 i consolidació GIRL_LOS_02/03 → ara part de la neteja.)
