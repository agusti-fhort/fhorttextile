# DIAGNOSI — F3-FINE-A: viabilitat de la selecció FINA de sembra

Data: 2026-07-15 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`

**Abast.** Dimensionar el salt de "selecció per BLOCS" (F3, ja a `dev`) a "selecció FINA per
registre/subconjunt". **No es dissenya el wizard**: es censa el cost del motor de clausura.

**Convenció.** Cada afirmació porta `fitxer:línia`. `"NO EXISTEIX"` = confirmat absent al codi, no
especulat. Les xifres són del tenant `fhort` real de staging (SELECTs de lectura). Propostes
marcades `💡 PROPOSTA (a validar)`.

---

## Resum executiu

1. **La clausura NO explota.** Triar 1 GarmentType arrossega **165 files de mitjana** (mín 1, màx
   298 — HEAVY_OUTERWEAR), no el catàleg sencer. El motiu és que el graf és **pla**: `GarmentType →
   GTI → GarmentPOMMap → POMMaster`, i **POMMaster és una fulla** (totes les seves FKs són
   nullable). La por del brief ("triar poca cosa acaba sembrant molt igualment") **no es confirma**.
2. **El motor de clausura per registre JA EXISTEIX en embrió.** `_read_source` accepta
   `filter_kwargs` per model (`bootstrap_tenant.py:193-202`), `_copy_piece` els aplica (`:228`), i
   el **gate de grading ja és un filtre per registre amb una clausura d'un salt escrita a mà**
   (`:404-405`: `rule_set__origen=CANONICAL`). El motor de còpia **no s'ha de tocar**.
3. **Per tant: peça PETITA-MITJANA.** El que falta no és un motor nou, és un **resolutor de
   clausura** que tradueixi la selecció a `source_filters` — i per l'eix GarmentType són **7
   lookups d'ORM** que segueixen FKs que ja existeixen. El gruix del cost real és **UI + frontera**,
   no motor.
4. **L'eix útil és UN: GarmentType** (amb la família com a drecera d'agrupació). L'eix "categoria de
   POM" **va a contrapèl del graf** i és una trampa: `GarmentPOMMap.pom` és PROTECT **NOT NULL**
   (`pom/models.py:444`), així que excloure un POMMaster fa **saltar** els seus mapes en silenci.
5. **⚠️ La frontera SHARED és la decisió real, i és arquitectura, no cost.** `SeedProfile` declara
   explícitament que guarda BLOCS i **no** registres, perquè el backoffice és SHARED i no ha de
   conèixer el catàleg d'un tenant (`backoffice/models.py:206-214`). La selecció fina **contradiu
   aquesta frontera**. Tècnicament `seleccio` és un `JSONField` lliure i aguantaria ids/codis sense
   cap model nou (`:233`) — però "aguanta" no vol dir "toca".
6. **⚠️ La premissa d'Agus ("el canònic creixerà") NO ES POT MESURAR.** **8 de 10 entitats
   sembrables no tenen cap timestamp** (v. BLOC A4). No es refuta; és que **no hi ha dades per
   verificar-la**. L'únic indici indirecte: el catàleg `GarmentGroup` té **11 famílies i només 6
   s'usen**.

---

## BLOC A1 — Graf de dependències a nivell de REGISTRE

### Les FKs que manen (només les DURES: NOT NULL → sembrar el registre exigeix el destí)

| entitat | FKs DURES (NOT NULL) | fitxer:línia |
|---|---|---|
| POMGlobal | **cap** — `body_measure_iso` és SET_NULL nullable | `pom/models.py:62-68` |
| GarmentType | **cap** — `garment_type_global` SET_NULL nullable; `targets_recomanats` M2M blank | `pom/models.py:393-399`, `:413-417` |
| **GarmentTypeItem** | `garment_type` (CASCADE) | `tasks/models.py:290-291` |
| POMMaster | **cap** — `pom_global` i `categoria` SET_NULL nullable | `pom/models.py:145-158` |
| **GarmentPOMMap** | `pom` → POMMaster (**PROTECT**) | `pom/models.py:444` |
| GradingRuleSet | **cap** — les 7 FKs són nullable | `pom/models.py:533-588` |
| **GradingRule** | `rule_set` · `pom` · `talla_base` (**3 dures**) | `pom/models.py:616-618` |
| **SizingProfile** | `target` · `garment_type` · `construction` · `fit_type` · `size_system` · `grading_rule_set` (**6 dures**) | `pom/models.py:842-853` |
| **TaskTimeEstimate** | `garment_type_item` · `task_type` | `tasks/models.py:353-355` |
| TimeSeed | **cap** | `tasks/models.py:413-414` |

### El graf (X → Y = "sembrar X exigeix sembrar Y"; només arestes dures)

```
POMGlobal ........... FULLA          TimeSeed ............ FULLA
GarmentType ......... FULLA          POMMaster ........... FULLA
GradingRuleSet ...... FULLA (les 7 FKs nullable)

GarmentTypeItem  → GarmentType
GarmentPOMMap    → POMMaster
                 ⇢ GarmentTypeItem → GarmentType   [nullable + db_constraint=False]
GradingRule      → GradingRuleSet · POMMaster · SizeDefinition → SizeSystem
TaskTimeEstimate → GarmentTypeItem → GarmentType
                 → TaskType                          [NO es copia: ha de preexistir]
SizingProfile    → Target · ConstructionType · FitType · SizeSystem · GarmentType · GradingRuleSet
```

**El graf és PLA: profunditat màxima 3.** Això és el que fa barata la clausura.

### Correccions a supòsits (el brief demanava no anar de memòria)

- **`GarmentPOMMap` NO penja de `GarmentType`.** Aquell FK i el seu `unique_together` **NO
  EXISTEIXEN**: eliminats a la migració 0016 un cop migrats els 95 mapes legacy
  (`pom/models.py:435-437`). La clau real és `('garment_type_item','pom')` (`:461`).
- **`POMMaster → POMGlobal` és TOVA**, no dura (SET_NULL nullable, `:145-151`). I **no és 1:1**: 126
  distints per 170 files, ja corregit al cens de F3 (`bootstrap_tenant.py:151-152`).
- **`SizingProfile` té SIS FKs dures**, no una. El que F3 va descobrir (`grading_rule_set`
  PROTECT+NOT NULL, `:852`) és cert però incomplet.
- **`TimeSeed` no té cap FK a `TaskType`**: el lligam és un `CharField` (`tasks/models.py:405-408`)
  sense constraint. El bloc `time_seeds` depèn de `garments` **només per TaskTimeEstimate**.
- **`GarmentTypeItem.grading_rule_set` és nullable AVUI però el codi declara que serà NOT NULL**
  (`tasks/models.py:313-316`): la dependència tova és **transitòria**. `💡` Quan passi, `garments`
  arrossegarà `grading`, i un Free sense grading deixarà de ser possible per aquesta via.
- **Cap `unique_together` bloqueja el gra fi**: els que existeixen són tots compostos amb el pare, i
  GarmentType/POMMaster/GradingRuleSet/SizingProfile **no tenen cap constraint d'unicitat** — les
  "claus naturals" del bootstrap són **conveni, no BD** (`pom/models.py:426-428`, `:182-184`).

### ⚠️ Quan la clausura es trenca, les files desapareixen amb un WARNING

`_copy_piece` (`bootstrap_tenant.py:287-297`): si una FK apunta a una fila no copiada → **NULL si és
nullable**, **skip de la fila sencera si és dura**. El skip només escriu un `[skip]` a stdout i posa
`ok=False` (`:428-429`). O sigui: **una clausura mal calculada no peta, sembra menys en silenci.**
És el risc central de baixar a registre.

**Veredicte A1: el graf és pla i barat de tancar; el perill no és el volum, és el skip silenciós.**

---

## BLOC A1-bis — Quant arrossega de veritat (mesurat a `fhort`)

### Per GarmentType (els 19 reals)

| GarmentType | grup | GTI | maps | POMMaster | TTE | **clausura** |
|---|---|---:|---:|---:|---:|---:|
| HEAVY_OUTERWEAR | OUTERWEAR | 4 | 169 | 46 | 32 | **298** |
| BUTTONED_TOPS | TOPS | 4 | 148 | 37 | 34 | **261** |
| ADULT_JUMPSUITS | DRESSES | 3 | 138 | 46 | 24 | **258** |
| TAILORED_PANTS | BOTTOMS | 6 | 140 | 29 | 49 | **252** |
| DRESSES | DRESSES | 4 | 136 | 35 | 33 | **244** |
| UNDERWEAR | UNDERWEAR | 5 | 104 | 46 | 40 | **242** |
| STRUCTURED_JACKETS | OUTERWEAR | 3 | 123 | 44 | 24 | **239** |
| JERSEY_TOPS | TOPS | 4 | 116 | 29 | 32 | **211** |
| … | | | | | | |
| BRA_SHAPEWEAR | UNDERWEAR | 3 | 18 | 6 | 24 | **58** |
| DRESS · T_SHIRT | | 0 | 0 | 0 | 0 | **1** (buits) |

**mín 1 · mitjana 165 · màx 298.**

### Per família (l'eix candidat), amb deduplicació

| família | GT | GTI | maps | POMMaster | TTE | **clausura** |
|---|---:|---:|---:|---:|---:|---:|
| TOPS | 7 | 19 | 514 | 65 | 154 | **759** |
| DRESSES | 4 | 10 | 317 | 62 | 81 | **474** |
| OUTERWEAR | 2 | 7 | 292 | 49 | 56 | **406** |
| BOTTOMS | 3 | 10 | 224 | 33 | 81 | **351** |
| UNDERWEAR | 2 | 8 | 122 | 51 | 64 | **247** |
| SWIMWEAR | 1 | 3 | 60 | 20 | 24 | **108** |

### La troballa que fa viable l'eix: el solapament

- **Un GarmentType arrossega com a màxim 46 POMMaster dels 217** del catàleg. Triar-ne un **no**
  arrossega el POMMaster sencer.
- **78 dels 93 POMMaster usats es comparteixen entre 2+ GarmentTypes.** El cost marginal d'afegir
  una família és **subllineal**: les famílies convergeixen, no s'acumulen.
- **124 dels 217 POMMaster no tenen cap mapa**: avui la sembra "tot" els aboca igualment, i **cap
  selecció fina per GarmentType els portarà mai**. Són pes mort per a qualsevol tenant nou.

**Veredicte A1-bis: triar poca cosa sembra poca cosa. La premissa del brief queda REFUTADA amb dades.**

---

## BLOC A2 — Granularitat útil vs possible

`GarmentType.grup` és un **CharField**, no una FK a `GarmentGroup` (`pom/models.py:402`) — però els
**6 valors usats casen tots amb un `GarmentGroup.codi`** (0 orfes, verificat). L'eix família és
coherent tot i no tenir constraint.

| eix | granularitat | cost de clausura | utilitat de NEGOCI | veredicte |
|---|---|---|---|---|
| **família (`grup`)** | 6 famílies | **108–759 files** · 1 lookup (`grup__in`) · l'usuari no resol res | **Alta**: "què fabriques?" és la pregunta que un client entén | ✅ **L'eix real** |
| **GarmentType concret** | 19 tipus | **1–298 files** · mateixos lookups (`pk__in`) · **cost idèntic** | **Alta**: el mateix eix, un grau més fi. Gratis si es fa la família | ✅ **Recomanat (mateix motor)** |
| GTI dins família | 57 items | ~30–50 c/u · mateix motor | **Baixa**: "item" és vocabulari intern (variant d'un tipus). Obliga el client a saber què és | ⚠️ possible, poc útil |
| **categoria de POM** | 16 cat. (+**57 POMMaster amb categoria NULL**) | **Va a contrapèl**: excloure POMMaster fa **saltar** els seus `GarmentPOMMap` (FK dura PROTECT, `:444`) → sembra silenciosament incompleta | **Nul·la**: un catàleg de POMs sense mapes és **inert** | ❌ **Trampa** |
| subconjunts de grading | 25 rulesets | ja filtrat per `origen=CANONICAL` | **Moot avui**: v. sota | ⛔ **bloquejat** |

### ⛔ El grading està 100% tancat avui

**Els 25 GradingRuleSet de `fhort` tenen `origen = NULL`** (0 CANONICAL, 0 CLIENT_RUN, 0 IMPORT).
El gate del bootstrap **falla fort** si el perfil demana grading i no hi ha cap CANONICAL
(`bootstrap_tenant.py:397-403`). Per tant **avui cap tenant nou pot rebre grading**, ni per blocs ni
fi, fins que es passi `set_grading_origen` (ja anotat com a pendent #3 de F3). **Dissenyar selecció
fina de grading abans d'això és dissenyar sobre una porta tancada.**

**Veredicte A2: UN sol eix — GarmentType, amb la família com a drecera d'agrupació a la UI.** Dona
control real (1017 files vs 2440) sense que l'usuari resolgui cap dependència a mà, perquè tot el
que penja avall és derivable seguint FKs. **STOP-AGUS: la taula de dalt és la decisió.**

---

## BLOC A3 — Reutilització

### El que JA hi és (i no s'ha de tocar)

| peça | fitxer:línia | serveix per a registre? |
|---|---|---|
| `_read_source(model, source, filter_kwargs)` | `bootstrap_tenant.py:193-202` | ✅ **filtre per registre, ja existeix** |
| `source_filters` per model, passat a cada peça | `:228`, `:420-422` | ✅ el diccionari ja viatja |
| Gate de grading = filtre + **clausura d'1 salt a mà** | `:404-405` | ✅ **la prova que el patró funciona** |
| Skip/NULL segons FK dura o tova | `:287-297` | ✅ ja resol el "destí no copiat" |
| `_spec()` ordre topològic | `:128-165` | ✅ intacte |
| `seleccio` = `JSONField(default=dict)` lliure | `backoffice/models.py:233` | ✅ **aguanta ids/codis sense model nou** |
| El backoffice ja llegeix el catàleg del tenant delegant a `tasks` | `views_seeding.py:45-62` → `seed_block_counts` (`bootstrap_tenant.py:103-125`) | ✅ **el camí de la frontera ja està obert** |
| La pantalla ja calcula clausura i ensenya el cost en files | `SeedProfilesPage.jsx:141-144`, `:198-206` | ✅ s'amplia, no cal wizard nou |

### El que s'ha de construir

1. **El resolutor de clausura** (la peça nova de veritat). Per a l'eix GarmentType són **7 lookups**
   que segueixen FKs existents — `💡 PROPOSTA (a validar)`:
   ```
   GarmentType      → pk__in / grup__in = <selecció>
   GarmentTypeItem  → garment_type__in = <selecció>
   GarmentPOMMap    → garment_type_item__garment_type__in = <selecció>
   POMMaster        → pk__in = <poms dels mapes d'aquests items>   ← l'únic calculat
   TaskTimeEstimate → garment_type_item__garment_type__in = <selecció>
   SizingProfile    → garment_type__in = <selecció>
   GradingRule      → pom__in = <els mateixos poms> + rule_set__origen=CANONICAL
   ```
   Tot expressable com a `filter_kwargs` d'ORM: **no cal recórrer cap graf a mà**, la profunditat
   màxima és 3 i les FKs ja hi són.
2. **Un endpoint d'enumeració** (llista de GarmentType amb `codi_client`+`grup`+cost), calcat del
   patró de `blocs-meta`: el backoffice delega a `tasks`, que és qui coneix el catàleg.
3. **Drill-down a la pantalla**: obrir el bloc `garments` a una llista de famílies/tipus. La
   maquinària de clausura+comptadors del client ja hi és.

### ⚠️ Les dues fragilitats del magatzem de la selecció

- **`GarmentType.codi_client` NO és unique** (`pom/models.py:426-428`). Els 19/19 distints a `fhort`
  són **un fet observat, no una garantia**. Guardar codis com a clau de selecció n'hereta la
  fragilitat.
- **Guardar `pk`s és pitjor**: són ids del tenant origen. `--from` és un paràmetre
  (`bootstrap_tenant.py:179-180`); el dia que l'origen no sigui `fhort`, una selecció per pk
  apunta a files diferents **en silenci**.

**Veredicte A3: el motor es reutilitza sencer. La feina nova és el resolutor (petit), un endpoint
d'enumeració (calcat) i el drill-down de la UI (mitjà).**

---

## BLOC A4 — "El canònic creixerà": NO ES POT VERIFICAR

### Volums reals a `fhort` (3.173 files en total)

| entitat | files | | entitat | files |
|---|---:|---|---|---:|
| **GarmentPOMMap** | **1.529** | | GradingRuleSet | 25 |
| **GradingRule** | **707** | | GarmentType | 19 |
| TaskTimeEstimate | 460 | | TimeSeed | 8 |
| POMMaster | 217 | | SizingProfile | 26 |
| POMGlobal | 125 | | GarmentTypeItem | 57 |

**Dues entitats són el 70%**: GarmentPOMMap + GradingRule = 2.236 files.

### El ritme de creixement: NO EXISTEIX la dada

| model | timestamp |
|---|---|
| POMGlobal · GarmentType · GarmentTypeItem · POMMaster · GarmentPOMMap · GradingRuleSet · GradingRule · TaskTimeEstimate | **NO EXISTEIX cap timestamp** |
| SizingProfile | `modified_at` (`pom/models.py:868`) — **no és `auto_now`**, nullable, 1/26 informat → no data altes |
| TimeSeed | `created_at`/`updated_at` (`tasks/models.py:415-416`) — 8 files, totes de 2026-07 |

`GradingRuleHistory` (`pom/models.py:880`) podria haver fet de testimoni: **0 files**.

> **La premissa d'Agus no es refuta ni es confirma: no hi ha dades per fer-ho.** L'únic indici
> *indirecte* a favor: el catàleg `GarmentGroup` té **11 famílies i només 6 tenen cap GarmentType**
> (`ACCESSORIES`, `DRESSES-FULL`, `KNITWEAR`, `TOPS-KNIT`, `TOPS-WOVEN` són buides) — l'estructura
> ja preveu créixer. `💡 PROPOSTA (a validar)`: si el creixement ha de guiar decisions de producte,
> **cal instrumentar-lo primer** (un `created_at` `auto_now_add` a les entitats de catàleg és una
> migració petita i additiva).

### ¿La selecció per blocs ja aboca "massa" avui?

| escenari | files |
|---|---:|
| Free amb **TOT** (blocs sencers, sense grading) | **~2.440** |
| Free amb **tot inclòs grading** | **3.173** |
| Free amb **només la família TOPS** (base+garments+pom_masters+time_seeds) | **~1.017** |
| Free amb **només SWIMWEAR** | **~366** |
| **Terra irreductible: el bloc `base`** | **250** |

**Sí, aboca de més, però no de forma escandalosa**: 2.440 files no ofega ningú tècnicament. El
guany de la selecció fina és **2,4× (TOPS) a 6,7× (SWIMWEAR)** — i el valor és de **producte**
(un Free que no veu 19 tipus de peça que no fabricarà), no de rendiment.

> **Troballa lateral:** el bloc `base` són **250 files sempre**, i el 74% són `POMGlobal` (125) +
> `GarmentTypeGlobal` (59). Com que `POMMaster → POMGlobal` és **TOVA**, aquests 125 s'aboquen
> sencers encara que la selecció només en necessiti 46. `💡` El mateix resolutor podria escurçar
> `base`, però és scope a part.

**Veredicte A4: el volum d'avui no és un problema tècnic; la selecció fina és una decisió de
producte. I el creixement, avui, és una creença sense instrumentació.**

---

## TAULA FINAL per al CTO

| # | fet | estat | implicació |
|---|---|---|---|
| 1 | La clausura no explota: 1 GarmentType = 165 files de mitjana (màx 298) | ✅ mesurat | l'eix fi és viable |
| 2 | 78/93 POMMaster es comparteixen entre GarmentTypes | ✅ mesurat | cost marginal subllineal |
| 3 | El motor ja filtra per registre (`filter_kwargs` + gate de grading) | ✅ existeix | **el motor no es toca** |
| 4 | El graf és pla (profunditat 3) i sense unique_together que bloquegi | ✅ verificat | resolutor = 7 lookups d'ORM |
| 5 | `seleccio` és JSONField lliure; la pantalla ja fa clausura i costos | ✅ existeix | ni model nou ni wizard nou |
| 6 | **Clausura mal calculada → skip silenciós, no error** | ⚠️ **risc** | cal `--dry-run` i un test de clausura |
| 7 | **La frontera SHARED prohibeix conceptualment guardar registres al backoffice** | ⚠️ **decisió d'Agus** | és arquitectura, no cost |
| 8 | `codi_client` no és unique; els `pk` són del tenant origen | ⚠️ risc | triar clau de selecció amb cura |
| 9 | **Els 25 rulesets tenen `origen=NULL` → grading 100% tancat** | ⛔ **bloquejador** | l'eix grading no es pot ni provar |
| 10 | `GarmentTypeItem.grading_rule_set` serà NOT NULL | ⚠️ latent | `garments` arrossegarà `grading` |
| 11 | 8/10 entitats sense timestamp → creixement no mesurable | ⚠️ buit | instrumentar abans de decidir per creixement |
| 12 | 124/217 POMMaster no tenen cap mapa | ⚠️ pes mort | cap selecció per GarmentType els portarà |

## VEREDICTE DE COST

**Peça PETITA-MITJANA, i el pes NO és on semblava.**

- **Motor de clausura: PETIT.** No cal motor nou. `source_filters` ja és el forat, el gate de
  grading ja n'és la prova, i el graf és prou pla perquè l'eix GarmentType siguin **7 lookups
  d'ORM**. Estimació: **1 peça** (resolutor + `--dry-run` + test de clausura contra els 19 GT).
- **Endpoint d'enumeració: PETIT.** Calcat de `blocs-meta`.
- **UI drill-down: MITJÀ.** És la part més grossa, i és UI.
- **La frontera SHARED: no és cost, és una DECISIÓ** (Patró C). Si Agus decideix que el backoffice
  pot conèixer `GarmentType` per codi natural, la resta és mecànica.

**STOP-AGUS.** Cal decisió sobre: (a) l'**eix** (taula A2 — recomanat: GarmentType amb família com a
drecera); (b) la **frontera** (¿el backoffice pot guardar codis de catàleg?); (c) què es fa amb el
**bloqueig del grading** (#9), que avui tanca l'eix més car abans de començar.
