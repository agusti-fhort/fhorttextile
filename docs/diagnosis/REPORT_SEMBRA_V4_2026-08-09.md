# REPORT — TRAM SEMBRA v4 (esborrat total + catàleg canònic)

**Data:** 2026-08-09 · staging `/var/www/ftt-staging`, branca `dev` · **cap push, cap deploy**
**Commit:** `451c1f5e` · **Dump previ:** `ops/backups/PRE-SEMBRA-V4_20260809_155013.dump` (1,7 MB)

---

## Recomptes finals

| Taula | Files | Esperat |
|---|---:|---:|
| `pom_pommaster` | **142** | 142 |
| `pom_customerpomalias` (BRW) | **94** | 94 |
| `pom_gradingrule` (`BRW-CATALEG-v3`) | **142** | 142 |
| `pom_pomcategory` | 25 | — (les 25 famílies del corpus) |
| `pom_pomglobal` (fhort) | 0 | 0 |

**Duplicats: 0** a les tres taules. I no és una afirmació: les tres constraints s'han
**provat contra la BD viva** (en savepoint, desfet) i les tres PETEN —
`uniq_pommaster_codi_client_ci`, `uniq_customer_client_code`, `pom_gradingrule_rule_set_id_pom_id`.

---

## 1 · El dump, verificat per FILES DINS

`pg_dump` 18.4 (`/usr/lib/postgresql/18/bin/`, el del PATH és 16.14 i no obre aquests dumps).
`EXIT=0` **no és la prova**: s'ha extret el bloc `COPY` de cada taula i s'han comptat les files.
Totes coincideixen amb la línia base viva — `fhort`: pommaster 12, gradingrule 5, basemeasurement 6,
garmentpommap 6, pomcategory 3, pomglobal 10, gradingruleset 47 · `public`: pomglobal 125,
pomcategory 15 · `los`: tot 0 excepte 51 models. **322 taules amb dades, 8.838 files.**

## 2 · L'esborrat

Ordre d'11 passos de `DIAGNOSI_NETEJA_CATALEG_POMS_2026-08-08.md` §BLOC 6, només a `fhort`.
Dry-run primer, cap cascada inesperada, després `APPLY=1`.

🚨 **PAS 0, FORA DEL FULL D'11 PASSOS.** `models_app_basemeasurement` tenia **6 files** (les del
model 1319 apuntant a POMs ZZ-TEST) i la diagnosi del 08/08 la va censar a **0**. La FK és
**PROTECT** (`models_app/models.py:629`): sense esborrar-les, el pas 9 no passa i el buidat
s'atura a mig camí. **No les va crear la sembra ZZ-TEST** — són posteriors, i el guió d'aquell
script no les toca. S'han esborrat. **El model 1319 i el seu SizeFitting segueixen vius**; el
que ha caigut són les seves 6 mesures, que eren ZZ-TEST i no podien sobreviure a «ZZ-TEST inclòs».

Va caure: 6 BaseMeasurement · 5 GradingRule · 6 GarmentPOMMap · 12 POMMaster · 10 POMGlobal ·
3 POMCategory. La resta de passos ja eren a 0.

**Intacte, com manava el brief:** els 47 `GradingRuleSet` (BUIDATS, mai esborrats) · l'`ItemBaseSet` ·
els 62 `GarmentTypeItem`, 21 `GarmentType`, 12 `GarmentGroup` · el model 1319 · `public.pom_pomglobal`
(125) · tot `los`.

## 3 · La sembra

`python manage.py sembra_cataleg_v4 [--no-dry-run]` — idempotent per construcció: es **nega a
córrer sobre un catàleg poblat**, perquè el brief demana que un duplicat peti, no que es fusioni.

### 🔑 La columna `trenca` no es transcriu: es TRADUEIX

El full anomena l'**última** talla del Δ petit; el motor ancora a la **primera** del Δ gran
(`increment_de_l_aresta`). Transcriure-la desplaçaria **les 98 regles amb break una talla sencera** —
l'error exacte que el full denunciava. La forma surt dels quatre Δ via `forma_de_la_regla`,
**importada** de `seed_brownie_ruleset` i no recopiada.

El contrast full↔derivat sobre les 142 files dona **0 discrepàncies**: cada `trenca` del full és
exactament la talla anterior a la derivada. Els breaks cauen només a **S** i **M** (el full deia
XS i S). Formes: **98 LINEAR+BREAK · 44 FIXED**, cap fila sense forma canònica.

`talla_base` = `XXS` (talles[0] d'`ALPHA_EU_W`), i `talla_base_label` **també** s'omple — la FK és
llegat en retirada (CAT2.1) i l'etiqueta és la forma canònica.

### La prova no és la taula: és el MOTOR

Que la columna estigui ben desada no demostra que el relleu caigui on toca. S'ha propagat amb
`propaga_ancoratges` des de `XXS`=100 i s'han mesurat els Δ que en surten:

| POM | El full declara | Δ que dona el motor | |
|---|---|---|---|
| `A` | 2 · 3 · 3 · 3 («trenca XS») | **2 · 3 · 3 · 3 · 3 · 3 · 3** | ✅ |
| `BL` | 1 · 1 · 1,5 · 1,5 («trenca S») | **1 · 1 · 1,5 · 1,5 · 1,5 · 1,5 · 1,5** | ✅ |
| `BF` | FIXED | **0 a totes les arestes** | ✅ |

El motor reprodueix **exactament** els quatre Δ del full. Amb `trenca` transcrita literalment,
la primera aresta d'`A` hauria valgut 3 en comptes de 2 i totes les talles haurien quedat mogudes.

---

## 🚩 Excepcions i decisions preses (per validar)

1. **Les 6 `BaseMeasurement` del model 1319** — esborrades (v. §2). És l'única lectura possible de
   «ZZ-TEST inclòs», i sense això el buidat no passa. Al dump si es volen recuperar.
2. **25 `POMCategory` creades del corpus** (`familia` → codi, `seccio` → nom). **El brief no les
   demanava**, però el pas 11 les esborra i el CSV en porta la taxonomia: sense elles `/poms`
   queda un bloc pla de 142 files. `L` i `P` comparteixen rètol («CANESÚ (L · P)») i són dues
   categories, com al full.
3. **Tres columnes del corpus no tenen destí a l'esquema i NO s'han desat:** `regim`
   (Amplada/Llarg/Col·locació/Fix), `ancoratge` (Cota/Caiguda/Component/Tirada) i `capa_defecte`
   (134 exterior · 7 fornitura · 1 folre). `POMMaster` no té cap camp per a cap de les tres.
   **No s'han inventat camps ni s'han abocat a `notes`.**
4. **`capa_proposta` i `instancia_proposta` de SEMBRA_2a tampoc es desen.** `CustomerPOMAlias` no
   té camp de capa ni d'instància — i el model diu per escrit que **deliberadament** no desa QUINA
   instància és. El que sí s'ha desat és **`es_instancia=True` a les 31 files** que en porten:
   el matcher hi resoldrà el POM i deixarà la fila a «assignar instància». (3 files diuen
   `folre/exterior`, que no és ni una capa sola.)
5. **`🆕` de `PANELLS I TALLS (Y)`** — anotació del full, no part del nom. No entra a la BD.
6. **El ruleset `ZZ-TEST · Chino BOTTOMS regular` (id 220) segueix viu i buit.** L'ordre validat
   diu que els contenidors es buiden i mai s'esborren; però és un contenidor de prova amb 0 regles
   dins d'un catàleg que ara és el definitiu. **Decisió d'Agus si ha de caure.**
7. **«Els 6 LOSAN inclosos» no és verificable des del corpus**: cap columna de `SEMBRA_1_canonic`
   marca la provinença LOSAN. Els 142 s'han sembrat com un sol conjunt canònic.
8. **`SEMBRA_3_grading` no existeix com a fitxer.** El brief en comptava 4, a `ops/sembra_v4/` n'hi
   ha 3 — però les columnes de grading (`logica`, els 4 Δ, `trenca`) viuen **dins de
   `SEMBRA_1_canonic.csv`**, i són 142 files. Els passos 3a i 3c llegeixen el mateix fitxer.
9. **`BRW-CATALEG-v3` no té `RuleSetScopeNode`** («es proposa a: no declarat» a la pantalla). No
   era a l'abast d'aquest tram.

---

## Verificació a pantalla

`ops/qa/captures/sembra_v4_01_cataleg_poms.png` — `/poms`: **142/142**, agrupats per les 25
famílies, amb l'àlies BRW al panell de detall.
`ops/qa/captures/sembra_v4_02_grading.png` — `/poms/grading`: **`BRW-CATALEG-v3` · BRW · 142
regles**, l'únic joc amb regles; els altres 46 buits.

Captures contra el **servei viu** (`/api/` reenviat al gunicorn del 8001), no contra fixtures:
amb fixtures la foto sortiria bé encara que la sembra no hi fos.

## Suite

`python manage.py test fhort.pom --noinput` → **`Ran 242 tests in 988.376s` · `OK`**, 0 `FAIL`,
0 `ERROR`. `python manage.py check` net.

🔵 **El resum de la suite va a `stderr`.** La primera passada, llançada sense `2>&1`, va deixar
un fitxer de sortida amb només soroll de migracions i un `EXIT=0`. Un exit code no diu quants
tests han corregut: es va tornar a passar amb `stderr` fusionat per tenir el recompte real.

