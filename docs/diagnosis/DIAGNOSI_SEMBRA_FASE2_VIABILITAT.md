# DIAGNOSI — VIABILITAT SEMBRA FASE 2: los→FONT, fhort←HERÈNCIA, segon consumidor

Data: 2026-07-27 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging` branca `dev` · cap escriptura, cap migració, cap commit.
Base: [DIAGNOSI_CATALEG_POM_STAGING_PROD](DIAGNOSI_CATALEG_POM_STAGING_PROD.md) (bandera resolta: LOSAN opera a `los`-PROD, self pk=1; catàleg `los` 262/212 vs `fhort`-LOS 413).
Decisió Agus (base d'aquesta diagnosi): **LOS és la FONT, `fhort` (estudi) HERETA, després l'aprenentatge diagnostica el catàleg propi de FTT + Brownie.**
Convenció: cada fet porta font (`fitxer:línia` per codi · schema.taula + entorn per dades). Font PROD = dump diari
`/srv/fhort-prod-backups/incoming/fhort_textile_20260726_023001.dump` (pg_restore v18, read-only, sense restaurar). `0` = comptat, no especulat.

---

## Resum executiu

1. **Q1 — El número que MANA (resolució contra el destí real `los`): 94,8% net, 146 òrfes.** Re-cens del MATEIX joc
   d'etiquetes (2782) contra el catàleg de la MARCA (`los`, 323 codis): **VERD 1852 · GROC 784 · ÒRFE 146**. El
   98,5%/43 d'abans era de `fhort`-estudi i **no valia**. La caiguda és sobretot **GROC** (329→784: molts codis que
   a l'estudi casaven EXACTE, a la marca només casen NORMALITZANT) + **òrfes ×3,4** (43→146).
2. **Q1 — El «heritage gap» és petit i concentrat: 7 famílies de codi, 103 ocurrències**, que existeixen a `fhort`
   però FALTEN al catàleg `los`: **`G`×62, `H.11`×16, `H11`×15, `O23.2`×5, `GM`×2, `GN`×2, `O.23-2`×1**. Afegir-les al
   catàleg `los` (o acceptar-les com a revisió) recupera gairebé tot el marge estudi→marca.
3. **Q2 — NO existeix cap pont que materialitzi POMPlacement (ni ItemFitxer) d'un tenant a un altre.** L'únic
   transport cross-tenant és `federation_service.traspassa` (Brand→Studio), i **copia NOMÉS Models (identitat+config,
   "nascuts a zero"), EXPLÍCITAMENT no fitxes ni feina** (`federation_service.py:112`). «recursos» (P7) és el CICLE DE
   VINCLE (alta/aturar/revocar), no un copiador d'actius (`views_recursos.py:1-7`). ⇒ **"fhort hereta els
   POMPlacement" NO és viable amb la infra existent; caldria construir un pont nou.**
4. **Q2 (estructural) — POMPlacement penja d'ItemFitxer → `tasks.GarmentTypeItem`; a PROD hi ha 0 ItemFitxer i 0
   POMPlacement als DOS schemas.** Abans d'escriure cap POMPlacement, la Fase 2 ha de **materialitzar primer els
   ItemFitxer** (els sketches del `.ai`, lligats al GTI — exactament la cua "artboard→GTI").
5. **Q3 — El diagnòstic de catàleg és trivial per SQL però ara mateix sense dades: 2/368 POMMaster tenen
   placement.** La clau és `POMMaster LEFT JOIN POMPlacement` (POM sense col·locació = forat). **Dins `fhort` els 368
   POMMaster són COMPARTITS entre clients** (LOS 229 àlies · BRW/Brownie 94 · FTT 2) → un cop hi ha placements sobre
   el catàleg compartit, FTT i Brownie n'hereten **sense pont**. Aquesta és la via real de "l'aprenentatge diagnostica FTT+Brownie".
6. **DECISIÓ (secció final):** l'única via de "herència" viable AVUI **no és copiar placements** sinó **re-sembrar
   des de la MATEIXA FONT** (`.ai`), perquè `sembra_ai_report`/el command de Fase 2 ja són `--schema`-param i el `.ai`
   és la font única. Independent-vs-heretat es col·lapsa: **sembra independent per schema, font compartida.**

---

## BLOC Q1 — Re-cens contra el destí real (`los`)

Mètode (read-only): mateixes funcions d'extracció del command (`parse_words`/`merge_fragments`/`render_rgb`/`red_mask`/
red-gate), MATEIX joc d'etiquetes que el cens de F1 (2782, definit per "resol a `fhort` O té forma de codi"), re-graduat
contra el catàleg `los` extret del dump PROD (client_code + codi_client → exact casefold + normalitzat). Script scratch
fora de git; cap BD tocada.

| | contra `fhort` (estudi) | contra `los` (marca) |
|---|---|---|
| VERD (exacte) | 2410 | **1852** |
| GROC (normalitzant/variant) | 329 | **784** |
| ÒRFE (cap match) | 43 | **146** |
| **net (VERD+GROC)** | **2739 (98,5%)** | **2636 (94,8%)** |
| codis de catàleg | 413 (àlies LOS-6 + master estudi) | 323 (àlies self + master `los`) |

- **El número que mana per a Fase 2 és 94,8% net / 146 òrfes** (contra `los`), no el 98,5%/43.
- **Heritage gap** (net a `fhort` però ÒRFE a `los`): **7 famílies, 103 ocurrències** — `G`×62, `H.11`×16, `H11`×15,
  `O23.2`×5, `GM`×2, `GN`×2, `O.23-2`×1. Són codis reals de LOSAN al `.ai` que el catàleg de la marca encara no coneix.
- El salt de GROC (329→784) diu que **el catàleg `los` usa una PUNTUACIÓ diferent** de la de les etiquetes del `.ai`
  (moltes cases només passen després de normalitzar) → la normalització v1 del command és el que salva el 94,8%.

⚠️ **Aquest cens és contra el catàleg `los` de PROD (dump).** A STAGING `los` és buit (0/0) → `sembra_ai_report --schema los`
a staging dona **57/57 ÒRFE** (verificat). Els `.ai` de `/root/sembra_ai/` SERVEIXEN (l'extracció és independent del
catàleg), però **per validar la resolució `los` a staging cal poblar-hi el catàleg primer** (via traspàs, com PROD).

**Veredicte Q1:** contra el destí real, 94,8% net / 146 òrfes. El gap estudi→marca és 7 codis concentrats; tapar-los
(afegir-los al catàleg `los`) és la feina de preparació de Fase 2.

---

## BLOC Q2 — El pont d'herència los→fhort per a POMPlacement

**POMPlacement** (`models_app/models.py:1054`): FK a **ItemFitxer** (CASCADE) + FK a **POMMaster** (PROTECT); geometria
normalitzada 0..1 sobre la bbox de l'objecte sketch; viu al CATÀLEG (ItemFitxer), i els models n'HERETEN dins el mateix
tenant via `ModelFitxer.derivat_de_item` (D1) — herència INTRA-tenant, no cross-tenant.

**ItemFitxer** (`models_app/models.py:485`): FK a **`tasks.GarmentTypeItem`** (CASCADE) — és el fitxer/sketch d'un GTI
del catàleg. ⇒ el `.ai` esdevé ItemFitxer sobre un GTI (la cua "artboard→GTI"), i el POMPlacement s'hi enganxa.

**L'únic transport cross-tenant existent** — `federation_service.traspassa(brand, studio)` (`federation_service.py:190`):
- Direcció **Brand→Studio** (los→fhort) = la direcció de "fhort hereta". ✔ direcció correcta.
- Copia **NOMÉS Models**, com a `ORIGEN_EXTERN`, resolts per CLAU NATURAL (`instancia_al_studio:163`).
- **EXPLÍCITAMENT no viatgen "mesures, regles, FITXES, fittings ni tasques — la feina es fa al Studio i neix a zero"**
  (`federation_service.py:112-113`). ⇒ **POMPlacement, ItemFitxer i catàleg POM queden FORA del pont.**
- «recursos» (`views_recursos.py`) = gestió del VINCLE (alta/aturar/reactivar/revocar + token), **no** copiador d'actius.

**Estat de dades (dump PROD 2026-07-26):**

| taula | PROD `fhort` | PROD `los` | STA `fhort` | STA `los` |
|---|---|---|---|---|
| models_app_itemfitxer | **0** | **0** | 1 | 0 |
| models_app_pomplacement | **0** | **0** | 2 | 0 |
| models_app_modelfitxer | 177 | 7 | 177 | 0 |

- **A PROD no hi ha CAP ItemFitxer ni POMPlacement a cap dels dos schemas.** Els 1/2 de staging `fhort` són les dades de
  prova dels sprints F1/F2 de cotes.

**Veredicte Q2:** el pont d'herència per a POMPlacement **NO EXISTEIX** (la federació copia Models, no placements/fitxes).
"fhort hereta els POMPlacement de los" exigiria **construir un copiador nou** (re-apuntar `item_fitxer`→GTI i `pom`→codi
per clau natural, cross-schema). A més, **abans de qualsevol POMPlacement cal materialitzar ItemFitxer** (0 a PROD).

---

## BLOC Q3 — Segon consumidor: diagnòstic de catàleg (FTT + Brownie)

Font: staging `fhort` (live, read-only).

- Clients de l'estudi amb nomenclatura pròpia: **LOS 229 àlies · BRW (Brownie) 94 · FTT (self) 2**. Els **368 POMMaster
  són COMPARTITS** (no per-client; el per-client és el CustomerPOMAlias). GarmentTypeItem=62.
- **Cobertura actual: 2/368 POMMaster tenen ≥1 POMPlacement** (les dades de prova). La resta (366) no en tenen.

**La clau del diagnòstic** (SQL trivial, sense codi nou): `POMMaster LEFT JOIN POMPlacement` →
- **Forat de catàleg** = POMMaster (usat per un client via àlies) SENSE cap POMPlacement → mesura definida però que
  l'estudi no sap ON va dibuixada. Per Brownie: dels ~94 POMs que anomena, quants tenen precedent de col·locació.
- **Divergència** = el mateix POMMaster col·locat amb geometria/`view_slot` incoherent entre ItemFitxer diferents →
  coneixement de col·locació en conflicte, a revisar.

**Per què l'aprenentatge de LOSAN pot diagnosticar FTT+Brownie:** perquè **dins `fhort` el POMMaster és compartit**. Si
els placements se sembren sobre el catàleg COMPARTIT de l'estudi, tot POM que Brownie/FTT també anomenin (via àlies)
queda cobert automàticament, SENSE pont. ⚠️ Tensió amb Q2/la bandera: LOSAN OPERA a `los`, i el POMMaster de `los` (262)
és **tenant-local, diferent** del de `fhort` (368). Placements escrits a `los` cobreixen POMMaster de `los`, **no** els de
`fhort` que comparteixen Brownie/FTT. ⇒ el diagnòstic de FTT+Brownie només s'alimenta si els placements arriben al
POMMaster COMPARTIT de `fhort` — cosa que torna a demanar el pont de Q2, O bé una sembra independent a `fhort`.

**Veredicte Q3:** la maquinària de diagnòstic (cobertura POMMaster↔POMPlacement) és trivial i ja possible; el que falta
és la DADA (placements) i que arribin al catàleg COMPARTIT de l'estudi. Viable, condicionat a on s'escriuen els placements.

---

## TAULA FINAL — EXISTEIX / FALTA / A CONSTRUIR

| Peça | Estat | Font |
|---|---|---|
| Resolució contra `los` (destí real) | **94,8% net / 146 òrfes** (número que mana) | re-cens dump PROD |
| Catàleg `los` complet per als codis del `.ai` | **FALTA** 7 famílies (`G`,`H.11`/`H11`,`O23.2`,`GM`,`GN`,`O.23-2`) | Q1 heritage gap |
| Staging `los` per provar Fase 2 | **BUIT** (0 catàleg) → cal poblar-lo primer | STA `los` |
| ItemFitxer per penjar POMPlacement | **0 a PROD** (tots dos schemas) → materialitzar primer | dump PROD |
| Pont cross-tenant per a POMPlacement | **NO EXISTEIX** (federació copia Models, no fitxes) | `federation_service.py:112` |
| POMMaster compartit dins `fhort` (base del 2n consumidor) | **EXISTEIX** (368 compartits: LOS/BRW/FTT) | STA `fhort` |
| Diagnòstic de cobertura (POM sense placement) | **TRIVIAL** (SQL), sense dades encara (2/368) | STA `fhort` |

---

## DECISIÓ FASE 2 (independent vs heretat)

**FET (no proposta):**
- **"Heretar" POMPlacement per CÒPIA cross-tenant NO és viable avui** (no hi ha pont; la federació copia Models nascuts a
  zero, `federation_service.py:112`). Fer-ho exigiria construir un copiador nou.
- El command d'informe/sembra **ja és `--schema`-param**, i el `.ai` és la **font única** compartida per tots els schemas.
- Escriure POMPlacement exigeix **ItemFitxer previ** (0 a PROD) i **POMMaster al mateix schema** (los 262 ≠ fhort 368).

**💡 PROPOSTA (a validar — Patró C):**
1. **Herència = re-sembra des de la MATEIXA FONT, no còpia.** Com que sembra és `--schema`-param i el `.ai` és únic, la via
   neta és **córrer la Fase 2 per schema**: `--schema los` (la MARCA, on LOSAN opera → 94,8% net) i, quan es vulgui que
   l'estudi "hereti", `--schema fhort` (catàleg COMPARTIT → cobreix LOS+BRW+FTT). No cal construir cap pont: la "herència"
   és la font compartida, no un transport d'actius. **Independent-vs-heretat es col·lapsa en "independent per schema".**
2. **Preparació obligatòria abans d'escriure a `los`:** (a) poblar el catàleg `los` amb les 7 famílies que falten
   (`G`,`H.11`/`H11`,`O23.2`,`GM`,`GN`,`O.23-2`) o acceptar-les a la cua de revisió; (b) **materialitzar els ItemFitxer**
   (artboard→GTI) abans dels POMPlacement — sense ItemFitxer no hi ha on penjar la col·locació.
3. **El destí operatiu és `los`** (on viuen els 961 models i on opera la marca). Escriure a `fhort` només té sentit per
   alimentar el 2n consumidor (diagnòstic FTT/Brownie sobre el POMMaster compartit) — decisió separada de la sembra operativa.
4. **Si es vol el pont real los→fhort** (perquè Brownie/FTT aprofitin EXACTAMENT els placements de LOSAN, no re-sembrats):
   caldria un copiador nou anàleg a `traspassa` però per a POMPlacement, re-apuntant `item_fitxer`→GTI i `pom`→codi per
   clau natural. És un BUILD, no infra existent — fora de l'abast de sembra F2, decisió d'arquitectura.
5. **Staging:** per provar Fase 2 fidelment cal **poblar staging `los`** (catàleg + GTI) com a PROD; mentrestant
   `--schema fhort` és PROXY (números diferents: 98,5% vs 94,8%). Els `.ai` de `/root/sembra_ai/` serveixen tal com són.

---
*Patró A · READ-ONLY · cap codi tocat, cap BD escrita, cap dump restaurat, cap commit. Fonts: staging live (read-only) +
dump PROD 2026-07-26 via pg_restore v18 + re-cens scratch (extracció del command, catàleg `los` del dump).*
