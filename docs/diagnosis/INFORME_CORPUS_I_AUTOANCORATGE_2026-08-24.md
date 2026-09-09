# INFORME — (1) CENS DEL CORPUS DE PRECEDENTS · (2) VIABILITAT DE L'AUTO-ANCORATGE

**Data:** 24/08/2026 · **Patró A — READ-ONLY.** Cap escriptura a cap BD, cap fitxer del repo
modificat, cap `.ai` tocat, **cap suite executada** (llei operativa 23/08). Els experiments són
scripts standalone de lectura, fora del repo (scratchpad de sessió).
**Entorn:** staging · clon `/var/www/ftt-staging` (branca `dev`, HEAD `5306df7e`) · schemes
`public` / `fhort` / `los`.

---

## VEREDICTE EN DUES LÍNIES

> **BLOC 1** — El corpus **existeix i és bo** (2.782 regles a `/root/sembra_ai/INFORME_SEMBRA_AI.md`),
> però **`PlacementProposal` no existeix**: ni model, ni migració, ni taula, ni un sol commit a
> tot l'historial. I el **catàleg que el resolia ja no hi és**: `CustomerPOMAlias` de LOS = **0**
> files i **0 de 144** codis del tenant porten punt, quan tot el vocabulari del lot és puntejat.
> El corpus és viu; **el pont cap al catàleg és mort**.
>
> **BLOC 2** — L'auto-ancoratge per casament de mesura **no és viable avui**: dels 14 POMs
> ancorats a mà a PF20 v3, **0 donen una candidata única** i 12 en donen més de 5 (mitjana
> **20,7**). La restricció que més ajuda —la direcció— és exactament la columna `orientation`,
> **buida a 165/165 POMGlobal i 144/144 POMMaster**. I **3 de 14** ancoratges humans ni tan sols
> cauen dins de ±0,6 cm de l'espec: el criteri rebutjaria la resposta correcta.

---
---

# BLOC 1 · CENS DEL CORPUS DE COL·LOCACIÓ (Nivell 2)

## 1.1 · ON VIU EL CORPUS AVUI

### `PlacementProposal` — **NO EXISTEIX**

| Comprovació | Resultat |
|---|---|
| Classe al codi (tots els clons de `/var/www`) | **cap** |
| Migració que la creï | **cap** (`models_app/0064` és `basemeasurement_origen_copied`) |
| Taula a Postgres (`information_schema`, els 3 schemes) | **cap** |
| Commits a tot l'historial (`git log --all -S`) | **cap** |
| Menció | **només** com a DECISIÓ: [DECISIONS_snapshot_2026-08-22.md:426-445](../ordres/DECISIONS_snapshot_2026-08-22.md) |

Les úniques taules amb «placement/proposal» al sistema són `models_app_pomplacement`,
`patterns_dartproposalrejection` i `patterns_sewproposalrejection` (a `fhort` i a `los`).

> Les «41 PlacementProposal de la primera sembra real» **no són en aquest entorn**. La decisió
> del 27/07 preveia l'entrega en dues seccions —«A staging … + migració 0064 + command → B PROD»—
> i el que hi ha a staging al lloc del 0064 és una altra migració. La Fase 2 **no s'ha construït
> mai aquí**.

### `POMPlacement` — **confirmat 0 / 0**

| Schema | `POMPlacement` | `ItemFitxer` |
|---|---|---|
| `fhort` | **0** | 1 (id 14, `dress_fancy_front.svg`, GTI 30) |
| `los` | **0** | 0 |

(Coincideix amb el cens de l'informe germà [INFORME_PRECEDENTS_COTES_2026-08-24.md](INFORME_PRECEDENTS_COTES_2026-08-24.md).)

### Els fitxers d'extracció a disc — **AQUÍ SÍ QUE HI ÉS EL CORPUS**

**Ruta:** `/root/sembra_ai/` (fora del repo, fora de `media/`, sense cap backup declarat)

| Contingut | Quantitat |
|---|---|
| Lot `.ai` LOSAN | **27 fitxers**, 550 MB (de 2,0 MB `CAMI MATEO` a 113,8 MB `BOTTOMS WOMAN`) |
| Informe d'extracció | `INFORME_SEMBRA_AI.md` · 31.121 B · **26/07/2026 21:10** |
| Docs de la PoC | `FTT_POC_B_MODIFICAT_LOSAN.md` (14,7 kB) · `FTT_DISSECCIO_LOT_AI_LOSAN.md` (10,2 kB) |

**Format del corpus:** Markdown, una línia per artboard, camps fixos —
`codis=N (🟩V 🟨G 🟥O) · lligam segur=S ampli=A · vistes=V (sense_cotes=X) · bbox_vista_max=Mmm · gti_hint=H`
— més tres seccions globals (col·lisions, codis que xoquen, òrfes).

> 🚨 **A1 — el corpus és un INFORME, no un artefacte de dades.** No hi ha ni JSON ni CSV ni cap
> taula: les 2.782 regles viuen com a **agregats per artboard**. Les coordenades de cada cota,
> que és el que una sembra necessitaria, **no s'han persistit enlloc**: es recalculen cada
> vegada que es torna a passar el command. El corpus reutilitzable, avui, són els 27 `.ai` i el
> command; l'informe només en diu la mida.

**Recompte de regles (mesurat re-analitzant l'informe):**

| Mètrica | Valor |
|---|---|
| Artboards analitzats | **173** |
| Codis extrets (etiquetes vermelles) | **2.782** |
| 🟩 VERD (match exacte) | 2.410 (86,6 %) |
| 🟨 GROC (només normalitzant) | 329 (11,8 %) |
| 🟥 ÒRFES | 43 (1,5 %) |
| Vistes detectades | 494 |
| Etiquetes sense cota (`sense_cotes`) | 1.351 |

> 🚩 **A2 — el brief diu «~60 sketches útils, ~2.000 regles»; el corpus real en té 173 artboards
> i 2.782 codis.** I la decisió del 27/07 parla de «PLE de **172** artboards TOTS amb GTI»: el
> command n'analitza **173**. La discrepància d'un artboard no està explicada enlloc, i el full
> del PLE artboard→GTI **no és a `/root/sembra_ai/` ni al repo**.

## 1.2 · QUALITAT — la franja groga i la resta

### Lligam segur vs ampli (la «franja groga» de la PoC)

Llindars: `STRICT_PT = 14.0` / `WIDE_PT = 34.0` pt —
[sembra_ai_report.py:59-60](../../backend/fhort/pom/management/commands/sembra_ai_report.py#L59).

| Franja | Codis | % del total |
|---|---|---|
| 🟢 **Lligam SEGUR** (≤14 pt) | **1.497** | 53,8 % |
| 🟡 **FRANJA GROGA** (>14 i ≤34 pt) — revisió humana | **789** | 28,4 % |
| ⚪ **SENSE CAP LLIGAM** (>34 pt o cap cota) | **496** | 17,8 % |

Aquesta és la xifra que dimensiona la pantalla de validació: **789 decisions humanes** només
per a la franja groga, i 496 codis que no tenen cota a proposar.

### Per `view_slot`

> 🚨 **A3 — el corpus NO TÉ `view_slot`, i no és un oblit del cens: és una frontera del disseny.**
> L'extractor compta **quantes** vistes hi ha a l'artboard (`vistes=N`, per clustering de tinta
> no-vermella) i la **més alta** (`bbox_vista_max`), però **no assigna cap cota a cap vista**.
> La decisió del 27/07 ho diu explícitament: la normalització per vista es fa **a la validació
> humana**, no a la sembra ([DECISIONS_snapshot:428-433](../ordres/DECISIONS_snapshot_2026-08-22.md)).
> Com que `view_slot` **és clau de `POMPlacement`** ([models_app/models.py:1690](../../backend/fhort/models_app/models.py#L1690)),
> **cap de les 2.782 regles es pot escriure sense que abans una persona digui de quina vista és.**
>
> Distribució disponible, doncs: **vistes per artboard** — 494 en total, mitjana 2,9;
> **13 artboards amb 0 vistes** i 8 amb 0 codis.

### Per GTI / peça — `item_hint`

| Mètrica | Valor |
|---|---|
| Artboards **amb** `gti_hint` (referència `L\d{2}[A-Z]{2,3}\d{3,4}` al text negre) | **16 / 173** (9,2 %) |
| Artboards **amb `gti_hint` BUIT** | **157 / 173** (**90,8 %**) |
| `gti_hint` distints | 14 |

> 🚨 **A4 — el 90,8 % del corpus no sap dir a quin ítem pertany.** El pla ho resolia amb el PLE
> validat amb la Montse (172 files artboard→GTI), que **no és a cap dels dos llocs on hauria de
> ser** (ni `/root/sembra_ai/`, ni el repo). Sense aquell full, el `gti_hint` automàtic cobreix
> 16 artboards de 173.

### Concentració i pèrdues

- **6 fitxers concentren el 70 %** dels codis: CARRYOVERS WOMAN (479), CARRY OVERS AW27 (391),
  KID GIRL FLETXES (334), prendas baby2 (280), FLETXES TEEN GIRL (250), CARRY OVERS BOY (245).
- **2 fitxers donen 0 codis**: CAMISA BRAIS CLASICA, PANADERO.
- **2 artboards amb el lligam OMÈS** per SVG ràster >25 MB (`MAX_SVG_MB`,
  [sembra_ai_report.py:64](../../backend/fhort/pom/management/commands/sembra_ai_report.py#L64)) →
  **35 codis extrets sense cap possibilitat de cota**.

## 1.3 · VOCABULARI — què sobreviuria una anonimització

El corpus és **íntegrament vocabulari de client LOSAN**. La resolució té dos camins, i tots dos
són de client ([sembra_ai_report.py:85-131](../../backend/fhort/pom/management/commands/sembra_ai_report.py#L85)):
`CustomerPOMAlias(customer=LOS).client_code` (prioritari, `:98`) → `POMMaster.codi_client` (`:103`).
**Cap dels dos passa pel catàleg global.**

**Estat del catàleg AVUI (mesurat):**

| | 26/07 (l'informe) | 24/08 (mesurat ara) |
|---|---|---|
| `CustomerPOMAlias` de LOS (pk 6) | índex primari de resolució | **0** |
| `POMMaster` a `fhort` | catàleg LOSAN puntejat | **144**, **0 amb punt** |
| `codi_client` DUPLICAT | **12 famílies** (`BJ`, `D`, `U`, `H`…) | **0** |
| Col·lisió de normalització dotted↔undotted | **39 famílies** | **0** |
| `POMMaster` amb `pom_global` | — | 103 (71,5 %) · 41 tenant-only |
| `POMMaster` separats del global | — | **0** |

Els 154 `CustomerPOMAlias` que queden al tenant són **tots de BRW (Brownie)**; LOS, FTT i TRV en
tenen **0**. El catàleg d'avui és el canònic de SEMBRA v4/v5
(`451c1f5e`, `33d076de`, [sembra_cataleg_v4.py:1-10](../../backend/fhort/pom/management/commands/sembra_cataleg_v4.py#L1)).

**Projecció mesurada de la resolució, avui:**

- **Camí àlies: mort** (0 files) → tot el que resolia per àlies passa a òrfe.
- **Camí `codi_client`, normalitzat (GROC):** dels 39 codis puntejats que el 26/07 col·lisionaven,
  **només 9 tornarien a resoldre** avui (`U.1 T.1 T.2 E.4 R.1 A.1 E.8 E.2 E.1`); **30 no** —
  entre ells tota la família `O.*` (`O.23 O.36 O.38 O.39 O.41`), `K.*`, `V.12`, `M.1`.
- Dels 12 `codi_client` duplicats del 26/07, **9 sobreviuen com a codi únic**; `BJ`, `C1` i `H`
  **han desaparegut** del catàleg.
- Dels 30 codis ÒRFES del 26/07, **cap** ha estat adoptat pel catàleg d'avui (0/30).

**Què sobreviuria una capa d'anonimització cap a precedent transversal:**
la col·locació és **geometria normalitzada** i no porta cap dada de client
([models_app/models.py:1616-1630](../../backend/fhort/models_app/models.py#L1616)); l'única
peça que impedeix la transversalitat és **la identitat del POM**. El sostre és, doncs, **el
103/144 (71,5 %)** de POMs del tenant que encara pengen d'un `POMGlobal` i, per tant, tenen codi
canònic; els **41 tenant-only** no tenen a què anonimitzar-se. Però això és el sostre del catàleg
d'avui, **no del corpus**: el pont entre els codis LOSAN del lot i aquests 144 POMs **ja no
existeix** (v. §1.4).

## 1.4 · PIPELINE — existeix i corre, però contra un catàleg que ja no el reconeix

**L'ordre existeix:** `python manage.py sembra_ai_report`
([sembra_ai_report.py:463-475](../../backend/fhort/pom/management/commands/sembra_ai_report.py#L463)),
`--dir` per defecte `/root/sembra_ai` (`:466`), Fase 1, **només lectura, cap BD** (`:1`, `:30-31`).

**Prerequisits — tots presents (comprovat sense executar el command):**

| | Estat |
|---|---|
| `pdftotext` · `pdftocairo` · `pdfinfo` | `/usr/bin/*` — **presents** |
| `numpy 2.5.1` · `lxml 6.1.1` · `Pillow 12.2.0` · `pikepdf 10.10.0` | **presents al venv** |
| Lot `.ai` | 27 fitxers a `/root/sembra_ai` |
| `Customer` LOS | existeix (`fhort` pk=6, `los` pk=1) |

**Compatibilitat amb l'esquema actual (post-neteja, post-0078):**

- ✅ **Estructuralment compatible.** El command només llegeix `Customer`, `POMMaster.codi_client`
  i `CustomerPOMAlias.client_code` — cap camp que 0078 hagi tocat, cap camp retirat.
- 🚨 **Funcionalment inútil.** El seu propi guard d'avortament és `if not cat.los_pk`
  ([:485-487](../../backend/fhort/pom/management/commands/sembra_ai_report.py#L485)): mira que el
  **Customer** existeixi, **no que tingui àlies**. Avui LOS existeix amb **0 àlies**, de manera
  que el command **no avorta: corre i produeix un informe amb la resolució esfondrada** — el
  pitjor mode de fallada possible, perquè s'assembla a un èxit.

> 🚨 **A5 — el guard de la Fase 1 mira el Customer i no l'índex.** [`sembra_ai_report.py:485-487`](../../backend/fhort/pom/management/commands/sembra_ai_report.py#L485).
> Amb `exact_alias` buit i `exact_master` sense cap codi puntejat, els 2.410 VERD del 26/07 no es
> poden reproduir, i el que en sortiria és un informe ple d'ÒRFES **sense cap avís que el
> catàleg ha canviat sota els peus**. La línia que ho diria (`Catàleg viu: … àlies=N`, `:489-492`)
> **s'escriu a stdout i no entra a l'informe `.md`**: un informe re-generat avui no duria cap
> traça del col·lapse.

**Conclusió del Bloc 1:** el corpus és recuperable —els 27 `.ai` i el command hi són, i corren—
però la Fase 2 s'ha de re-briefar sencera: falta el model, falta el PLE artboard→GTI, i
**falta decidir contra quin vocabulari es resol**, perquè el del 26/07 ja no existeix.

---
---

# BLOC 2 · VIABILITAT DE L'AUTO-ANCORATGE AL TALLER (model 1383 · PF20 v3)

## 2.1 · CATÀLEG — les columnes de la 0078

**Precisió sobre el brief:** la migració
[`pom/0078_sobirania_pom_copy_on_write.py`](../../backend/fhort/pom/migrations/0078_sobirania_pom_copy_on_write.py)
afegeix **onze** columnes a `pom_pommaster`, però **només nou** són el «com es mesura»; les altres
dues són la marca de sobirania (`separat_de_global`, `separat_at`). El vocabulari canònic viu a
[`nomenclatura.py:244-254`](../../backend/fhort/pom/nomenclatura.py#L244).

**Grau d'ompliment — MESURAT als dos catàlegs:**

| Columna | Domini | `POMGlobal` (165) | `POMMaster` `fhort` (144) |
|---|---|---|---|
| `unitat` | text | **165** | 0 |
| `start_point` | text | **165** | 0 |
| `end_point` | text | **165** | 0 |
| `reference_point` | text | **165** | 0 |
| `scope` | HALF · FULL · CALCULATED | **165** | 0 |
| `body_section` | FRONT·BACK·SIDE·SLEEVE·BOTH·HEAD | **165** | 0 |
| **`orientation`** | HORIZONTAL·VERTICAL·CIRCUMFERENCE·CURVED·DIAGONAL | **0** | **0** |
| **`state`** | FLAT·RELAXED·STRETCHED·ON_BODY | **0** | **0** |
| **`line`** | STRAIGHT·CURVED·ALONG CURVE·ANGLED | **0** | **0** |
| `separat_de_global` / `separat_at` | marca de sobirania | — | **0** |

> 🚨 **A6 — les TRES columnes que l'auto-ancoratge necessitaria són les tres que no ha omplert
> ningú, enlloc.** `orientation` és exactament la restricció de direcció que a §2.3 divideix
> l'ambigüitat; `line` és exactament la que triaria entre `metode='recta'` i `metode='vora'`.
> Estan declarades amb domini tancat des del 22/08 i tenen **0 files informades** de 309.

### Els 21 POMs de l'espec del 837

`Model 1383` · 21 `BaseMeasurement` actives · **tolerància ±0,60 cm a totes 21**.

| Grup | POMs | Camps plens |
|---|---|---|
| **17 lligats al global** | A B C D G1 F EK EK2 E1 E E5 SF S I J J1 U | **6 de 9** (els mateixos sis a tots) |
| **4 tenant-only** (`pom_global IS NULL`) | **SLT · EK1 · S2 · E7** | **0 de 9** |

Exemples (valor servit per la cascada `com_es_mesura_de`, tots des del global):

```
A  (44,0 cm) unitat=cm scope=HALF body_section=BOTH
             start=Side seam  end=Side seam  ref='1 inch below armhole'
E5 (2,5 cm)  unitat=cm scope=FULL body_section=BACK
             start=HPS  end='Shoulder seam at armhole'  ref='Straight vertical drop'
SLT (31,5 cm) — cap camp: POM del tenant sense global
```

> 🚨 **A7 — el règim «Caiguda» només es pot llegir de TEXT LLIURE.** Els 3 POMs de caiguda de
> l'espec (EK2, E5, SF) s'identifiquen únicament perquè el seu `reference_point` diu
> *«Straight vertical drop»* / *«Vertical at CF or CB»*. El camp que ho hauria de dir amb domini
> tancat (`orientation=VERTICAL`, `line=STRAIGHT`) és buit. Un matcher que hi confiï estarà fent
> **NLP sobre una columna de text lliure en anglès**.

> 🚨 **A8 — comentari caducat al motor.** [`engine/measure.py:22-23`](../../backend/fhort/patterns/engine/measure.py#L22):
> *«`POMMaster` no diu quin toca —no té camp per dir-ho—»*. Des de la 0078 **sí que en té**
> (`line`). El comentari justifica el `metode` per defecte RECTA amb una premissa que ja no és
> certa; el que és cert és que el camp existeix i **ningú l'ha omplert**.

## 2.2 · CODI EXISTENT — no hi ha cap matcher d'ancoratge

**Cens complet de motors de proposta a `patterns/`:**

| Motor | Proposa | file:line |
|---|---|---|
| Costures | parelles de trams gir→gir, 3 senyals ponderats | [`engine/seam_matching.py:692`](../../backend/fhort/patterns/engine/seam_matching.py#L692) · `avaluar` [`:654`](../../backend/fhort/patterns/engine/seam_matching.py#L654) · pesos [`:82-84`](../../backend/fhort/patterns/engine/seam_matching.py#L82) · llindar [`:114`](../../backend/fhort/patterns/engine/seam_matching.py#L114) |
| Costures (pont BD) | `candidats_del_patro` / `propostes_del_model` | [`seam_proposals.py:79`](../../backend/fhort/patterns/seam_proposals.py#L79) · [`:160`](../../backend/fhort/patterns/seam_proposals.py#L160) |
| Pinces | tripletes de la vora | [`dart_proposals.py:72`](../../backend/fhort/patterns/dart_proposals.py#L72) |
| POMs des d'un DXF ja exportat | **relectura** de la capa `FTT-POM` com a PROPOSTA | [`engine/ftt_pom_layer.py:221`](../../backend/fhort/patterns/engine/ftt_pom_layer.py#L221) |

> **No existeix cap suggeridor d'ancoratge de POM per casament de mesura.** El que el brief
> anomena F1.2 és una altra cosa: al dimensionament és *«Matcher DXF-TEXT → `CustomerPOMAlias`»*
> ([DIMENSIONAMENT_F1_F2_2026-08-21.md:206](DIMENSIONAMENT_F1_F2_2026-08-21.md)) — matching de
> **noms**, no de geometria. L'únic camí que avui produeix ancoratges automàtics és
> `FTTPOMLayerReader`, i **no descobreix res**: rellegeix el que FTT mateix va escriure.
>
> **L'arquitectura a imitar ja hi és**, però: `seam_matching` és un matcher de senyals ponderats
> amb desglòs explicable (`PES_PIQUETS 0,50 · PES_LONGITUD 0,35 · PES_NOMS 0,15`, llindar 0,40) i
> amb taula de rebuigs (`SewProposalRejection`, 7 files vives). És el motlle exacte del que
> caldria per als POMs — i el §2.3 diu quins senyals hi hauria de posar.

## 2.3 · EXPERIMENT DE LECTURA — PF20 v3

**Objecte:** `PatternFile 20`, `versio=3`, `is_current=True`,
`837 CORS 194 VESTIT M3-4 AGUS.DXF`, pujat **24/08 08:11 UTC**. Sample Size **S**, mètric,
`factor_to_mm = 1.0` amb **`unitats_confianca = 'low'`**.

**Peces i conjunt candidat** (`tipus='turn'` ∪ `mena='notch'`,
[`patterns/models.py:278-287`](../../backend/fhort/patterns/models.py#L278)):

| Peça | punts | gir | piquet | corba | **candidats** |
|---|---|---|---|---|---|
| 91 · 837.CUELLO | 1.224 | 20 | 8 | 1.196 | **28** |
| 92 · 837.DELANTERO | 984 | 56 | 12 | 916 | **68** |
| 93 · 837.ESPALDA | 928 | 48 | 8 | 872 | **56** |
| 94 · 837.MANGA | 612 | 18 | 8 | 586 | **26** |
| 95 · 837.TAPETA | 92 | 16 | 8 | 68 | **24** |

**Ancoratges reals: 14 a PF20 v3** (el brief en deia 12; n'hi ha 14 — més 1 residual a PF18).
Tots `metode='recta'`; **cap `ortogonal`, cap `vora`**.

### (a) Verificació prèvia — els extrems reals, són candidats?

| | |
|---|---|
| Ancoratges amb **els dos** extrems a (gir ∪ piquet) | **10 / 14** |
| Ancoratges que usen un punt de **CORBA** com a extrem | **4 / 14 (29 %)** — `A`, `C`, `S2`, `I` |

> 🚨 **A9 — el conjunt candidat del mètode deixa fora el 29 % de les respostes correctes,
> per construcció.** Ampliar-lo a tots els punts porta DELANTERO de 68 a 984 candidats
> (**483.336 parelles** en comptes de 2.278): ×212 de combinatòria per recuperar 4 casos.

### (b) La premissa: la parella humana casa amb l'espec?

| | |
|---|---|
| Ancoratges amb `|mesurat − espec| > 0,6 cm` | **3 / 14** |

```
S    espec 22,0  patró 20,17  Δ 1,83 cm
S2   espec 22,0  patró 20,29  Δ 1,71 cm
I    espec 43,5  patró 44,49  Δ 0,99 cm
```

> 🚨 **A10 — per a 3 de 14 POMs, el criteri «casa amb l'espec ±0,6» REBUTJARIA l'ancoratge que
> el patronista ha posat a mà.** El patró i la fitxa no coincideixen —i és normal que no
> coincideixin— però això vol dir que l'espec **no és una veritat amb què filtrar**: és una pista.

### (c) HISTOGRAMA D'AMBIGÜITAT — línia base (peça real, candidats, ±0,6 cm)

| POM | peça | espec | parelles dins ±0,6 | la real hi és? |
|---|---|---|---|---|
| E7 | CUELLO | 2,5 | 12 | sí |
| A | DELANTERO | 44,0 | **39** | no (corba) |
| B | DELANTERO | 46,0 | 28 | sí |
| C | DELANTERO | 54,0 | 19 | no (corba) |
| D | DELANTERO | 59,0 | **41** | sí |
| E | DELANTERO | 37,0 | 17 | sí |
| F | DELANTERO | 110,5 | 28 | sí |
| S | DELANTERO | 22,0 | 16 | **no (fora de tolerància)** |
| SLT | DELANTERO | 31,5 | 18 | sí |
| G1 | ESPALDA | 2,0 | 25 | sí |
| S2 | ESPALDA | 22,0 | **4** | no (corba) |
| I | MANGA | 43,5 | **4** | no (corba) |
| J1 | MANGA | 12,0 | 17 | sí |
| U | TAPETA | 16,5 | 22 | sí |

```
0 candidates (no la troba) :  0
1 candidata  (DETERMINISTA):  0      ← cap
2-5          (wizard curt) :  2      S2, I
>5           (cal restringir): 12    mitjana 20,7 · màxim 41
```

### (d) Com cau l'ambigüitat amb restriccions (precisió **i** recall)

`RECALL` = de les 10 parelles reals que **són** al conjunt candidat, quantes sobreviuen al filtre.

| Restricció | Σ candidates | mitjana | 0 | **1** | 2-5 | >5 | RECALL |
|---|---|---|---|---|---|---|---|
| cap (base) | 290 | 20,7 | 0 | **0** | 2 | 12 | 9/10 (90 %) |
| només punts de GIR (sense piquets) | 193 | 13,8 | 0 | **0** | 2 | 12 | 9/10 (90 %) |
| **direcció** (H/V, = `orientation`) | 187 | 13,4 | 2 | **0** | 2 | 10 | 9/10 (90 %) |
| **nivell** \|Δy\|≤5 mm (= `reference_point`) | 81 | 5,8 | 1 | **1** | 7 | 5 | 8/10 (80 %) |
| nivell \|Δy\|≤2 mm | 71 | 5,1 | 2 | **1** | 7 | 4 | 7/10 (70 %) |
| **direcció + nivell 5 mm** | **63** | **4,5** | 3 | **1** | 6 | 4 | 8/10 (80 %) |
| direcció + tolerància ±0,3 | 105 | 7,5 | 2 | **0** | 5 | 7 | 8/10 (80 %) |
| (tolerància ±0,1 sola) | 72 | 5,1 | 7 | **0** | 2 | 5 | — |

> 🔑 **Estrènyer la tolerància no desambigua: només destrueix recall.** A ±0,1 cm set POMs es
> queden **sense cap** candidata i **cap** no arriba a una de sola. La tolerància no és la
> palanca; **la geometria semàntica (direcció + nivell) sí que ho és**: −70 % de candidates per
> −10 punts de recall.

### (e) Mode «CAIGUDA» (ortogonal) — combinatòria mesurada

Tripletes `(ref_a, ref_b, p)` dins ±0,6 cm, per als 3 POMs de règim caiguda de l'espec:

| POM | espec | peça | tripletes possibles | **dins ±0,6** | ràtio |
|---|---|---|---|---|---|
| EK2 | 4,0 | DELANTERO | 149.556 | **3.141** | 2,10 % |
| EK2 | 4,0 | CUELLO | 9.620 | 608 | 6,32 % |
| E5 | 2,5 | DELANTERO | 149.556 | **5.080** | 3,40 % |
| E5 | 2,5 | TAPETA | 5.896 | 1.376 | **23,34 %** |
| SF | 22,0 | DELANTERO | 149.556 | **2.647** | 1,77 % |
| SF | 22,0 | TAPETA | 5.896 | 0 | 0,00 % |

> 🚨 **A11 — el mode ortogonal no és desambiguable per mesura.** Milers de tripletes per POM.
> El mode existeix i està ben pensat ([`patterns/models.py:396-401`](../../backend/fhort/patterns/models.py#L396),
> [`engine/measure.py:14-18`](../../backend/fhort/patterns/engine/measure.py#L14)), però exigeix
> que **la línia de referència vingui donada** (els dos HPS de la peça). Avui **cap dada del
> sistema identifica els HPS**: no hi ha ni rol de punt ni landmark batejat. Sense això, la
> caiguda no es proposa: es tria a mà.

### (f) Els 7 POMs de l'espec sense ancoratge — peça desconeguda

Candidates dins ±0,6 cm per peça (conjunt gir ∪ piquet):

| POM | `body_section` | espec | CUELLO | DELANT. | ESPALDA | MANGA | TAPETA | **TOTAL** |
|---|---|---|---|---|---|---|---|---|
| EK | BOTH | 22,0 | 16 | 16 | 4 | 12 | 0 | 48 |
| EK1 | *(buit)* | 7,7 | 19 | 5 | 4 | 0 | 2 | 30 |
| EK2 | BOTH | 4,0 | 24 | 0 | 0 | 0 | 24 | 48 |
| E1 | BOTH | 7,6 | 19 | 3 | 2 | 0 | 2 | 26 |
| E5 | BACK | 2,5 | 12 | 26 | 23 | 8 | **66** | 135 |
| SF | SIDE | 22,0 | 16 | 16 | 4 | 12 | 0 | 48 |
| J | SIDE | 16,6 | 15 | 44 | 8 | 16 | 30 | 113 |

> 🚨 **A12 — `body_section` NO restringeix la peça.** `E5` és `BACK` i el seu màxim de
> candidates és a **TAPETA** (66); `SF` és `SIDE` i n'empata a CUELLO i DELANTERO. El vocabulari
> de `body_section` (FRONT/BACK/SIDE/SLEEVE/BOTH/HEAD) parla de **zones del cos**, i els rols de
> peça del DXF (`837.CUELLO`, `837.TAPETA`…) parlen de **trossos de patró**: no hi ha cap taula
> que els relacioni, i les que semblen relacionar-se ho fan per casualitat de nom.

## 2.4 · CONCLUSIÓ DE VIABILITAT

**Com a proposador automàtic (una resposta, sense preguntar): NO és viable.**
0 de 14 casos donen candidata única, ni amb la millor combinació de restriccions mesurada.

**Com a REDUCTOR per a un wizard curt: viable amb condicions, i cap és de codi.**
La millor configuració mesurada —**direcció + nivell ≤5 mm**— porta la mitjana de **20,7 → 4,5**
candidates i deixa **7 de 14 POMs a la franja 1-5**, amb 80 % de recall. Sostre realista
end-to-end: **8 de 14 POMs** (57 %), perquè 4 tenen l'extrem a una corba i 3 no casen amb l'espec.

**Les quatre restriccions, per ordre de rendiment mesurat:**

| # | Restricció | On viuria | Estat avui |
|---|---|---|---|
| 1 | **Nivell** (els dos extrems a la mateixa alçada, ≤5 mm) | `reference_point` — *«1 inch below armhole»*, *«At bottom hem»* | ✅ ple (165/165) però **text lliure en anglès** |
| 2 | **Direcció** (H/V) | **`orientation`** | ❌ **0/165 i 0/144** |
| 3 | **Mètode** (recta vs vora) | **`line`** | ❌ **0/165 i 0/144** |
| 4 | **Zona / peça** | cap camp: caldria un mapa `body_section` → rol de peça | ❌ **no existeix** (A12) |

**Les tres frontereres que cap restricció no arregla:**

1. **El conjunt candidat.** 29 % dels ancoratges reals usen punts de corba (A9). O s'amplia el
   conjunt (×212 de combinatòria) o s'accepta que un de cada tres POMs no es proposarà mai.
2. **L'espec no és veritat.** 3 de 14 ancoratges humans queden fora de ±0,6 (A10). La mesura de
   l'espec ha de ser **un senyal ponderat**, mai un filtre dur — exactament com
   `PES_LONGITUD = 0,35` a `seam_matching` ([:83](../../backend/fhort/patterns/engine/seam_matching.py#L83)).
3. **La caiguda.** Sense HPS identificats, el mode ortogonal no es pot proposar (A11).

**El senyal que aquest experiment NO ha pogut mesurar i que probablement mana:** els **piquets**
i el **`grade_rule_num`**. A `seam_matching` el piquet pesa 0,50 —el senyal dominant— i el
`PatternPoint` ja porta la regla de grading que el CAD li va assignar
([`patterns/models.py:296-299`](../../backend/fhort/patterns/models.py#L296)). Un POM que creix
2 cm per talla ha de tenir els seus dos extrems en punts que **es mouen**: creuar l'espec amb la
`grade_table` del `PatternFile` és una restricció **ortogonal** a totes les de §2.3 i, a
diferència d'`orientation` i `line`, **la dada ja hi és**. Queda fora d'aquest cens.

---
---

## ANOMALIES — llista amb `file:line`

| # | Anomalia | On |
|---|---|---|
| **A1** | El corpus és un **informe agregat**, no dades: les coordenades de les 2.782 cotes no s'han persistit enlloc; es recalculen a cada passada. | `/root/sembra_ai/INFORME_SEMBRA_AI.md` · [sembra_ai_report.py:1-36](../../backend/fhort/pom/management/commands/sembra_ai_report.py#L1) |
| **A2** | Discrepància de mida no explicada: brief «~60 sketches / ~2.000 regles» · decisió «172 artboards» · command **173 artboards / 2.782 codis**. El full del PLE artboard→GTI **no és ni al lot ni al repo**. | [DECISIONS_snapshot:436-438](../ordres/DECISIONS_snapshot_2026-08-22.md) |
| **A3** | El corpus **no té `view_slot`** (compta vistes, no les assigna) i `view_slot` **és clau de `POMPlacement`** → cap regla es pot escriure sense decisió humana prèvia. | [models_app/models.py:1690](../../backend/fhort/models_app/models.py#L1690) · [DECISIONS_snapshot:428-433](../ordres/DECISIONS_snapshot_2026-08-22.md) |
| **A4** | **90,8 %** dels artboards (157/173) tenen `item_hint` buit; el `gti_hint` automàtic només cobreix 16. | [sembra_ai_report.py:74](../../backend/fhort/pom/management/commands/sembra_ai_report.py#L74) (`MODEL_REF`) |
| **A5** | **El guard de la Fase 1 mira el `Customer`, no l'índex d'àlies**: amb 0 àlies el command no avorta, corre i produeix un informe esfondrat que sembla un èxit; i la línia que ho denunciaria va a stdout, no a l'informe. | [sembra_ai_report.py:485-492](../../backend/fhort/pom/management/commands/sembra_ai_report.py#L485) |
| **A6** | `orientation`, `state` i `line` — les tres columnes de domini tancat de la 0078 — són buides a **165/165 `POMGlobal` i 144/144 `POMMaster`**. Són precisament les que l'auto-ancoratge necessita. | [0078:30-90](../../backend/fhort/pom/migrations/0078_sobirania_pom_copy_on_write.py#L30) · [nomenclatura.py:244](../../backend/fhort/pom/nomenclatura.py#L244) |
| **A7** | El règim «Caiguda» només es pot deduir de **text lliure en anglès** (`reference_point`), perquè `orientation`/`line` són buides. | [nomenclatura.py:248-254](../../backend/fhort/pom/nomenclatura.py#L248) |
| **A8** | Comentari **caducat** al motor: «`POMMaster` no diu quin toca —no té camp per dir-ho—». Des de la 0078 el camp és `line`; el que passa és que ningú l'omple. | [engine/measure.py:22-23](../../backend/fhort/patterns/engine/measure.py#L22) |
| **A9** | El conjunt candidat (gir ∪ piquet) **exclou el 29 %** de les respostes correctes: 4 de 14 ancoratges usen un punt de **corba**. | [patterns/models.py:278-287](../../backend/fhort/patterns/models.py#L278) |
| **A10** | **3 de 14** ancoratges humans queden **fora de ±0,6 cm** de l'espec (`S` Δ1,83 · `S2` Δ1,71 · `I` Δ0,99): el criteri rebutjaria la veritat. | mesurat sobre `PatternPOM.valor_mesurat_cm` [:424](../../backend/fhort/patterns/models.py#L424) vs `BaseMeasurement.base_value_cm` |
| **A11** | El mode **ortogonal** dona milers de tripletes dins tolerància (EK2 3.141 · E5 5.080 · SF 2.647 a DELANTERO): no és desambiguable sense una línia de referència, i **cap dada identifica els HPS**. | [patterns/models.py:396-401](../../backend/fhort/patterns/models.py#L396) · [engine/measure.py:14-18](../../backend/fhort/patterns/engine/measure.py#L14) |
| **A12** | **`body_section` no restringeix la peça**: `E5` (BACK) té el màxim de candidates a TAPETA. Falta un mapa zona-del-cos → rol de peça; avui la coincidència és de nom. | [0078:32-34](../../backend/fhort/pom/migrations/0078_sobirania_pom_copy_on_write.py#L32) |
| **A13** | El lot `.ai` (550 MB) i el seu informe viuen a **`/root/sembra_ai/`** — fora del repo, fora de `media/`, sense backup declarat ni cap referència al repo tret del `default` d'un argument. | [sembra_ai_report.py:466](../../backend/fhort/pom/management/commands/sembra_ai_report.py#L466) |
| **A14** | `PatternFile 20` declara `unitats_confianca = 'low'` («factors plausibles alhora (mm, 1/10mm); s'assumeix mm»). **Tot el §2.3 depèn d'aquesta assumpció**: si el factor fos 1/10 mm, cap distància casaria. | `empremta.unitats` de `PatternFile` 20 |

---

## NOTES DE MÈTODE

- **Cap suite executada** (llei operativa 23/08). Els quatre experiments són scripts standalone
  al scratchpad de sessió: només `SELECT` via ORM dins `schema_context`, cap `save()`, cap
  `delete()`, cap migració.
- **`sembra_ai_report` NO s'ha executat** (Bloc 1.4 demanava llegir-lo, no córrer-lo). Els
  prerequisits s'han comprovat sense invocar-lo: `which` dels tres binaris i `importlib` de les
  quatre dependències.
- Les xifres del corpus (§1.1-1.2) surten de **re-analitzar** `INFORME_SEMBRA_AI.md` amb un
  parser de la seva pròpia línia de format; les del catàleg (§1.3) i les del patró (§2) surten
  de la BD de staging **en lectura**.
- El conjunt candidat de §2.3 és `tipus='turn'` ∪ `mena='notch'`, tal com demanava el brief.
  Les distàncies són en mm a la BD i s'han passat a cm dividint per 10 (`escala_mm = 1.0`).
- El `RECALL` de §2.3(d) té denominador **10** —els ancoratges que tenen els dos extrems dins el
  conjunt candidat—, no 14: els altres 4 són irrecuperables per construcció (A9), i comptar-los
  al denominador barrejaria dues fallades diferents.
