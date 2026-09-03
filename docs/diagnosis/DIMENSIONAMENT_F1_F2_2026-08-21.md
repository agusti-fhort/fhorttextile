# DIMENSIONAMENT DE LES DUES FORCES — F1 motor paramètric · F2 ingesta IA

> **Patró A · read-only.** Cap escriptura de domini, cap migració, cap seed, cap commit.
> **Data:** 2026-08-21. **Fonts:** working tree `/var/www/ftt-staging` (branca `dev`),
> BD de staging (`ftt_staging`, port 5433) i **dump de PROD del 21/08 02:30**
> (`/srv/fhort-prod-backups/incoming/fhort_textile_20260821_023001.dump`).
> **Objectiu:** inventari real (dissenyat / construït / falta / primer valor / esforç) per a
> la sessió de decisió d'Agus.

---

## 0. VEREDICTE EN UNA PÀGINA

**Cap de les dues forces és un projecte per començar. Totes dues estan construïdes i
desplegades a PROD.** El dimensionament que calia no és «quant costa fer-ho», és **«què
separa el que ja hi ha dels diners»** — i en els dos casos la resposta no és codi.

| | F1 · Motor + DXF | F2 · Ingesta IA |
|---|---|---|
| Línies construïdes | ~24.250 (17.269 back + 6.983 front) | ~9.706 |
| Tests | 363 (`patterns/tests.py`) | 75 |
| Commits | ~120 (12/07 → 04/08) | ~124 (26/05 → 16/08, **viva**) |
| Desplegat a PROD | **Sí** — 14 migracions, l'última el 31/07 | **Sí** — en ús diari |
| Ús real a PROD | 4 patrons llegits · **0 exportacions** · aturat des del 28/07 | 61 sessions · 37 confirmades · 26 de 84 models |
| Cost mesurat | — | **3,27 USD de vida del ledger** |
| Què el separa dels diners | Una validació al CAD d'un client + una alta de producte | El **destí** de les dades que ja sap llegir |

**Tres fets que manen sobre la resta:**

1. **El motor no s'ha exportat mai.** `ExportAcknowledgement` = 0 files a PROD. Tota la
   cadena —llegir DXF, declarar trams, ancorar POMs, cosir, projectar el grading, escriure
   DXF+RUL amb autovalidació de doble round-trip— està construïda i verda, i la porta que
   factura no s'ha travessat ni un sol cop.
2. **El cost d'IA no és una variable de decisió.** 3,27 $ mesurats des del 22/07; ~10 $ de
   vida estimada. La projecció és **0,15 $ per model importat**, 27 $ per cada 100 models.
   La variable escassa no són els tokens: és l'ús.
3. **La costura entre les dues forces existeix i està sense construir.** F2 ja extreu
   `fit_comments` de cada document i **els llença**. Són exactament el delta que PAT-3 de F1
   necessita per tancar el cercle fitting→patró. Una sola peça fa guanyar les dues forces.

---

# F1 · MOTOR PARAMÈTRIC + DXF

## 1.1 EL DISSENYAT

| Document | Línies | Data | Estat |
|---|---|---|---|
| `MOTOR_DE_PATRONS.md` | 541 | 2026-06-14 | mestre original |
| `MOTOR_DE_PATRONS_V2.md` | 418 | 2026-07-08 (+ esmenes §4.4 el 12/07) | vigent conceptualment |
| `PLA_IMPLEMENTACIO_MOTOR_PATRONS.md` | 1.528 | 2026-07-12 → 07-16 | **dietari viu**: hi ha les actes de tancament de S0→S8, el paquet Taller, G6, els deploys |

**Els 7 principis (§2 del V2, intactes):** LLM mai dibuixa coordenades · NO crear topologia ·
sobirania del Model · fidelitat d'origen de primera classe · hexagonal només al motor · gate
humà d'exportació · es ven el resultat, mai «la IA».

**Eines decidides i verificades:** ezdxf 1.4.4 (MIT, preserva tags desconeguts) · shapely
2.1.2 (`offset_curve` mitre) · pyclipper 1.4.0 de reserva · libnest2d per a PAT-4 (aparcat) ·
ksons/astm-parser com a documentació executable del format.

**Les fases PAT-\*:** PAT-0a (parser + SVG servidor) · PAT-0b (visor Konva) · PAT-1 (anotació)
· G6 (prerequisit) · PAT-2 (escalador + export + gate) · PAT-3 (rectificació post-fitting) ·
PAT-4 (nesting).

**Esmenes del 12/07 (§4.4):** capa pròpia `FTT-POM` al writer · operació atòmica de moviment
(punt + reflow de curve points + re-derivació + revalidació del graf) · parsing tabular vs
anotació · bases pre-anotades a GTI · **estratègia de traçadora end-to-end**.

## 1.2 EL CONSTRUÏT — evidència

**App instal·lada:** `fhort.patterns` a TENANT_APPS ([settings.py:73](backend/fhort/settings.py#L73)).

**Motor pur — `patterns/engine/`, 6.437 línies, 19 mòduls:**

| Mòdul | Línies | Què fa |
|---|---|---|
| `aama_reader.py` | 870 | parser AAMA/ASTM sobre ezdxf, normalització d'unitats, empremta |
| `operations.py` | 788 | **l'operació atòmica de moviment** (E2): `move_points`, reflow, propagació al cosit, reposicionament de piquets, rellegir POMs, revalidar costures |
| `seam_matching.py` | 755 | proposta i validació de costures |
| `grading_projection.py` | 612 | `GradedSpec` → `GradeRule` (la projecció RUL) |
| `sew.py` | 413 | graf de relacions de cosit |
| `roundtrip.py` | 391 | **el comparador**: write→read→write→read |
| `geometry.py` | 373 | primitives 2D |
| `aama_writer.py` | 358 | writer AAMA |
| `dart_detection.py` | 322 | detecció de pinces |
| `ftt_pom_layer.py` | 316 | la capa pròpia FTT-POM |
| `natural_segments.py` · `segments.py` | 294 · 291 | trams naturals (llindar 22°) i segmentació de vora |
| `rul_reader.py` · `rul_writer.py` | 211 · 67 | taula de regles |
| `measure.py` · `ports.py` · `errors.py` | 167 · 144 · 53 | mesura, frontera hexagonal, errors |

**Adaptadors, API i serveis — `patterns/`, 10.832 línies** (`annotation_views` 1.163 ·
`views` 957 · `models` 921 · `adapters` 689 · `export` 443 · `serializers` 371 · `services`
272 · `seam_proposals` 266 · `svg` 178 · `dart_proposals` 173 · `preferences` 153 ·
`tolerance` 78 · `urls` 32) **+ `tests.py` amb 363 tests**.

**13 models de domini:** `PatternFile`, `PatternPiece`, `PatternPoint`, `PatternSegment`,
`PatternPOM`, `SewRelation`, `SewProposalRejection`, `DartProposalRejection`,
`SegmentPreference`, `PieceIdentityAcknowledgement`, `SewToleranceAcceptance`,
`ExportAcknowledgement` (+ `_AppendOnlyQuerySet`). **14 migracions.**

**Frontend — 6.983 línies:** `pages/TallerPatro.jsx` (1.541) + 17 components a
`components/pattern/` (`PatternViewer` 997 · `RelationsPanel` 975 · `PatternTab` 727 ·
`ExportModal` 453 · `ModelPomList` 392 · `patternGeometry` 334 · `ProposalsPanel` 298 ·
`PieceIdentityList` 246 · `SewEditor` 212 · `DartProposalsPanel` 189 · `seleccio` 177 ·
`sewText` 128 · `POMPicker` 94 · `PieceList` 87 · `SegmentEditor` 86 · `pieceText` 47).

**Desplegament a PROD — verificat al dump:**

```
patterns 0001..0007   2026-07-14 04:58   (deploy #1)
patterns 0008..0010   2026-07-16 10:54   (deploy #2)
patterns 0011..0014   2026-07-31 10:49   (deploy #3)
```

**TaskTypes a PROD:** `pattern_digit` (8) · `pattern_cad` (9) · `pattern_hand` (10) ·
`scaling` (11) · `marking` (12) · `pattern_review` (19). Els cinc de CAD amb `eina='patro'`
(encaminen al Taller) i `facturable=t`.

**Les peces de patró ja entren a la fitxa `.ftt` com a VECTOR editable** — no com a imatge:
`render.svg?piece=…&fons=0` → conversió a `path` amb el color de traç per capa DXF (tall,
costura, piquets, fil), desagrupable i editable per nodes
([TechSheetEditor.jsx:6887](frontend/src/pages/TechSheetEditor.jsx#L6887)). Tram «F1 —
peces de patró a la fitxa», tancat el 14/07.

## 1.3 L'ÚS REAL A PROD (dump 21/08 02:30)

| Taula | Files |
|---|---|
| `patterns_patternfile` | **4** |
| `patterns_patternpiece` | 47 |
| `patterns_patternpoint` | 10.948 |
| `patterns_patternsegment` | 706 |
| `patterns_segmentpreference` | 42 |
| `patterns_sewrelation` | 17 |
| `patterns_sewtoleranceacceptance` | 4 |
| `patterns_patternpom` | **3** |
| `patterns_pieceidentityacknowledgement` | 0 |
| `patterns_exportacknowledgement` | **0** |

**Els 4 fitxers:**

| id | Fitxer | CAD | Model | RUL | Data |
|---|---|---|---|---|---|
| 1 | `TATE.DXF` (v1, superat) | polypattern | 163 | no | 14/07 05:12 |
| 2 | `DEREK BURGUNDY-SAN.dxf` | **tuka** | 173 | no | 14/07 17:39 |
| 3 | `MEREDITH - Retoque.DXF` | polypattern | 166 | no | 22/07 16:37 |
| 4 | `TATE ok prod 27-07-26.DXF` (v2) | polypattern | 163 | **SÍ, 22.500 B** | 28/07 04:59 |

**Lectures d'aquesta taula:**

- **Q6 del V2 queda RESPOSTA**: sí que tenim un RUL real poblat, i el motor l'ha parsejat
  (`grade_table` de 34.646 bytes al fitxer 4). La validació del writer RUL ja té referència.
- Els dos CAD del disseny (Tuka i PolyPattern) han passat pel parser amb material real, amb
  detecció d'unitats per geometria i confiança `high` als quatre.
- **`garment_type_item_id` és NULL als quatre** → la porta d'ITEM (biblioteca GTI, W6) no
  s'ha exercit mai. Tot el que hi ha penja d'un Model.
- **3 `PatternPOM` en total.** L'anotació semàntica —el fossat del disseny— és pràcticament
  verge.
- **0 exportacions.** La porta que factura no s'ha travessat.
- **Última pujada: 28/07. 24 dies d'aturada.**

**Tasques de patró a PROD:** `pattern_cad` 15 (1 Done, 14 Pending) · `scaling` 15 (1 Done,
14 Pending) · `pattern_digit` 3 (1 Done, 2 Paused) · `pattern_review` 2 (1 Done).
**Welford: `n=1`** per a `pattern_digit` (66 min, item 5); la resta a zero. → **la línia base
de temps manual, que el V2 §5 declara la mètrica d'èxit del motor, no existeix.**

## 1.4 EL QUE FALTA

| # | Peça | Estat real |
|---|---|---|
| 1 | **PAT-3 · rectificació post-fitting** | La primitiva hi és i està provada (`move_points`, `deltes_resultants`), però **els seus únics consumidors són `grading_projection.py`** — cap camí `PieceFitting → deltes → operations`. És el que el V2 anomena «val milions». |
| 2 | **Sessió Montse (gate PAT-1)** | Mai feta. En pengen: receptes de mesura, Δ reals, especificació del Taller-GTI i **5 preguntes obertes acumulades** (pinça desigual del Tate 3,1 mm, tram natural de 0,2 cm, receptes recta vs vora, G6-C, POMs per plantilla). |
| 3 | **Biblioteca GTI (W6)** | Dissenyada amb 4 deltes; l'esquema (XOR model/item) hi és des de S3; **cap línia d'UI**. |
| 4 | **Suggeriment IA d'ancoratge** | `CustomerPOMAlias` + `find_pom_master` existeixen; el matcher sobre els TEXT del DXF no s'ha connectat mai. Els 3 POMs ancorats són manuals. |
| 5 | **Validació al CAD real del client (Q5)** | El round-trip propi és verd i és una porta dura. **Ningú ha obert mai un DXF exportat per FTT dins Tuka o PolyPattern.** Únic risc que el codi no pot tancar sol. |
| 6 | **Products al catàleg (Q4)** | `pattern-digitization` i `dxf-grading` no donats d'alta. Sense ells no hi ha línia base de marge. |
| 7 | **QA-TALLER-D** | Deute conegut i documentat: `operations.py:717 _indexs_del_rang` + `_longitud_indexs` + `segmentar_vora` — convenció de recorregut de vora divergent; **cap costura declarada al Taller es revalida en moviment i el detector d'estabilitat menteix en silenci**. S'arreglen junts. |
| 8 | **PAT-4 nesting** | Aparcat per disseny. Cap decisió pendent. |

## 1.5 EL CAMÍ MÍNIM AL PRIMER VALOR

Les tres opcions plantejades, mesurades contra el terreny:

**(a) Ingesta i visualització de DXF a la fitxa → JA VAL DINERS AVUI. Esforç: 0.**
Construït i desplegat des del 14/07: es puja el DXF, el motor el llegeix i normalitza, el
Taller el mostra, i la fitxa n'insereix les peces com a **vector editable**. Cap competidor
del nínxol ho fa. El que falta no és codi: és **ús i preu**.

**(b) El bucle fitting→modificació (PAT-3).** El més valuós i el més gran. Depèn de la
sessió Montse i d'un PAT-1 madur (3 POMs ancorats no ho és). No és el primer valor.

**(c) Escalat geomètric (PAT-2).** **Construït**, amb la porta d'autovalidació de doble
round-trip i el gate acoblat al segell de grading. El que li falta per facturar **no és
motor**: és una validació al CAD del client i un producte al catàleg.

> **La peça més petita que ja val diners no és (a), (b) ni (c): és TANCAR (c).**
> El camí crític són 2 gestos que no són de codi —qui obre el DXF exportat, i l'alta dels
> dos Products— més 1 sessió humana. El motor ja hi és i porta 24 dies aturat.

## 1.6 FASES I ESFORÇ GRUIXUT — F1

| Fase | Què | Esforç | Bloqueig |
|---|---|---|---|
| **F1.0 · Encendre'l** | Validació al CAD real d'un client + alta dels 2 Products + 1 model pilot exportat de punta a punta | ~1 sessió d'agent + 2 decisions humanes | **qui obre el DXF** (Brownie/Tuka o LOSAN) |
| **F1.1 · Montse** | Gate PAT-1: receptes, Δ reals, les 5 preguntes obertes, especificació GTI | 1 dia humà | agenda |
| **F1.2 · Anotació assistida** | Matcher DXF-TEXT → `CustomerPOMAlias`, UX DictionaryWizard (proposta + confiança + confirmació) | 2–3 sessions | F1.1 |
| **F1.3 · Biblioteca GTI (W6)** | 2a porta del mateix Taller; font de POMs de l'item; sense rellotge; permisos CONFIGURE | 3–4 sessions | F1.1 |
| **F1.4 · QA-TALLER-D** | Convenció única de recorregut de vora — els 3 nodes en una passada | 1–2 sessions | — |
| **F1.5 · PAT-3** | El cercle: `PieceFitting` → operacions → DXF nou; avisos DINS la superfície G1 | 5–8 sessions | F1.1 + G1 |
| **F1.6 · PAT-4** | Nesting (libnest2d) | aparcat | tracció de F1.0 |

---

# F2 · INGESTA IA UNIVERSAL

## 2.1 EL VIU — el pipeline

**Tres carrils d'entrada, no un:**

1. **Wizard d'import per document** — el principal. 9 endpoints
   (`cribratge` → `talles` → `extraccio` → `poms` → `grading-preview` → `mesures` →
   `library-prefill` → `teixit` → `confirmar`), **3.821 línies** a
   [extraction_views.py](backend/fhort/models_app/extraction_views.py) + **1.946** a
   [ImportWizard.jsx](frontend/src/components/ImportWizard/ImportWizard.jsx).
2. **Import massiu de models** per plantilla Excel pròpia
   ([bulk_import_service.py](backend/fhort/models_app/bulk_import_service.py), 793 l. + 169
   de views) — **determinista, 0 IA**, esquema fix de 15 columnes amb desplegables.
3. **Size-map / taula de graduació** ([pom/size_map_views.py](backend/fhort/pom/size_map_views.py))
   — xlsx determinista, PDF/imatge → Opus via `extraction_service.extract_from_file`.

**Total de la força: ~9.706 línies + 75 tests · ~124 commits (26/05 → 16/08, encara viva).**

**Formats acceptats:** `.xlsx .xls .pdf .png .jpg .jpeg .webp`
([ImportWizard.jsx:1016](frontend/src/components/ImportWizard/ImportWizard.jsx#L1016); el
backend hi coincideix a `_cribratge_content_block`).

**Encaminament determinista viu** (decisió Agus 22/07, FIX C): un `.xlsx` que el parser
posicional entén **no gasta ni un token** — «IA només quan el determinista no pot». Que el
parser peti compta com abdicar: davant del dubte, IA.

**Models IA en ús:** cribratge i extracció `claude-opus-4-7` · revisió d'Excel
`claude-sonnet-4-6` · proposta de cotes (visió F3) `claude-sonnet-4-6`.

## 2.2 ÚS I COSTOS REALS (dump PROD 21/08)

**61 sessions d'import** (04/06 → 19/08):

| Format | Sessions |
|---|---|
| PDF | 25 |
| XLSX | 25 |
| PNG | 11 |

| Estat | Sessions |
|---|---|
| CONFIRMAT | **37** (61%) |
| POMS | 12 |
| CRIBRATGE | 5 |
| MESURES_OK | 3 |
| TALLES | 2 |
| MESURES | 1 |
| DESCARTAT | 1 |

**26 models de 84 (31%)** han passat pel wizard; 25 amb import confirmat.

**El ledger `AIUsage`** (existeix des del 22/07 — migració `models_app.0059`): **41 crides,
0 errors.**

| Camí | Model | n | input | output | cache w | cache r | USD |
|---|---|---|---|---|---|---|---|
| cribratge | opus-4-7 | 21 | 63.667 | 2.706 | 0 | 0 | 0,386 |
| extracció | opus-4-7 | 17 | 48.115 | 88.024 | 48.628 | 10.491 | **2,750** |
| proposta de cotes | sonnet-4-6 | 3 | 17.534 | 5.540 | 0 | 0 | 0,136 |
| **TOTAL** | | **41** | | | | | **3,272** |

*Tarifa Anthropic vigent: opus $5 / $25 per MTok · sonnet $3 / $15. Escriptura de cache
×1,25, lectura ×0,10.*

**Projecció:**

- Cost per **sessió amb IA**: mediana **0,140 $** · mitjana **0,149 $** · màxim 0,317 $.
- Cost per **model importat**: **0,27 $** de mitjana (12 models tocats des del 27/07,
  reintents inclosos). Un pas net cribratge+extracció ≈ **0,15 $**.
- **100 models/any ≈ 27 $. 1.000 models ≈ 270 $.**
- El gruix és l'**extracció (84% del cost)**; el cribratge en pesa el 12% i és exactament el
  que el determinista ja evita quan pot.

**El determinista funciona, i es mesura.** De les 12 sessions `.xlsx` posteriors al 27/07
(quan el ledger ja era viu): **7 no van fer cap crida a la IA** i 5 van caure a Opus per
abdicació del parser. **Encert ≈ 58% sobre xlsx.** Les 12 sessions PDF i les 4 PNG del
mateix període van totes a Opus, com és el disseny.

## 2.3 FORATS DEL LEDGER (rellevants si el cost ha de manar decisions)

- **3 dels 6 punts del codi que criden Anthropic no registren res:**
  `chat_views.py` (2 crides, sonnet-4-6) · `tech_sheet_views.py` (opus-4-7) ·
  `views.py` → `ai_analysis_view` (opus-4-**5**) i `measurements_chat_view` (sonnet-4-**5**).
  La llei «tot usage es loggeja» (Agus, 22/07) està a mitges.
- **Tres pins de model endarrerits conviuen:** `claude-opus-4-5` a
  [extraction_service.py:83](backend/fhort/models_app/extraction_service.py#L83) i a
  `ai_analysis_view`; `claude-sonnet-4-5` a `measurements_chat_view`; `opus-4-7` /
  `sonnet-4-6` a la resta.
- **El ledger no té cap lector.** Cap endpoint, cap pantalla, cap conversió a euros. La
  pregunta «què ens ha costat aquest import?» encara només es respon per SQL.
- Les 49 sessions anteriors al 22/07 no tenen ledger → la despesa històrica és **estimada**
  (~7 $), no mesurada. Total de vida ≈ **10 $**.
- `ai_analysis_view` (`POST models/<id>/analisi-ia/`) —anàlisi de discrepàncies entre
  fitxers adjunts i mesures— **existeix al backend i no la crida cap pantalla**. Capacitat
  construïda i morta.

## 2.4 EL QUE EL WIZARD FA I NO FA

**Fa:** POMs + valors base · taula de graduació · run i talla base reconciliats contra el
`SizeSystem` de la peça de destí · matching contra `POMMaster`/`CustomerPOMAlias` amb
llindar de confiança i guard many-to-one · resolució de duplicats i identitat de fila
(capa / instància / peça) · preview de graduació · teixit · desa el PDF com a `ModelFitxer`
versionat.

**No fa:**

- **«+ talla».** Una columna del document amb una talla que no és al `SizeSystem` del model
  es **descarta** (hotfix BEACH, 26/07) amb un avís groc; si és la **base**, 422 dur. **No hi
  ha cap gest per afegir aquella talla al sistema des del wizard** — l'única sortida és
  abandonar la sessió, editar el sistema de talles i tornar a començar.
- **`fit_comments`, `construction_notes`, `anomalies_detected`, `design_freeze_blockers`.**
  El prompt els extreu i **ningú els persisteix**: només apareixen com a recompte dins un
  resum de xat ([chat_views.py:321](backend/fhort/models_app/chat_views.py#L321)).
- **BOM / escandall.** Hi ha `TaskType bom` i el prompt té `construction_notes`; cap
  escriptura de domini.

## 2.5 LA DISTÀNCIA A «QUALSEVOL DOCUMENT»

| Tipus | Avui | Què costaria | Esforç |
|---|---|---|---|
| **Fitxa PDF sencera (tech pack)** | S'envia **sencera** a Opus; el prompt només cull mesures, graduació i capçalera | **Prompt nou, res més.** El document ja hi és, ja es paga, i el context d'opus-4-7 és d'1M | 1 sessió per cada camp nou que es vulgui **persistir** (model + escriptura + UI) |
| **Fotos de taller / esbossos manuscrits** | **Ja acceptades i ja usades**: 11 sessions PNG a PROD. El prompt té `document_type: sketch_manual` | **Res al pipeline.** El que falta és el destí: avui una foto ha de contenir una TAULA per servir de res | segons què se'n vulgui treure |
| **Escalats manuscrits** | Cauen al mateix camí d'imatge; el prompt té `grading_table` | **Res nou de lectura**, però mai verificat amb un escalat manuscrit real | 1 sessió de validació amb material real |
| **BOM / escandall** | Ni es llegeix ni es desa | **Pipeline de DESTÍ** (model de dades + UI), no de lectura | 4–6 sessions |
| **Fit comments / comentaris de prova** | S'extreuen i **es llencen** | **Destí, no lectura.** I són exactament el delta que PAT-3 de F1 necessita | **3–5 sessions — la costura entre les dues forces** |
| **DOCX · CSV** | Rebutjats a la porta | Conversió a text i reutilitzar el camí Excel/PDF | 1 sessió cadascun |
| **HEIC** | Rebutjat a la porta | La dependència ja és al lock (fotos de fitting) | 1 sessió |
| **Multi-model en un document** | El cribratge compta `num_models` i el wizard ho confirma, però **un import = un model** | Escrutar l'abast real | mig fet |

## 2.6 PRIMER VALOR — F2

| Ordre | Peça | Per què | Esforç |
|---|---|---|---|
| 1 | **Destí dels fit comments** | Ja els llegim i els llencem. Són l'entrada natural de PAT-3. **Única peça que fa guanyar les dues forces alhora** | 3–5 sessions |
| 2 | **«+ talla» al wizard** | Fricció pura sobre un camí que ja funciona: avui obliga a abandonar la sessió i tornar a començar | 1–2 sessions |
| 3 | **Lector del ledger** | «Què costa un import» encara es respon amb SQL — i amb 3 punts sense registrar, la resposta d'avui és falsa per defecte | 1 sessió |
| 4 | **Tancar els 3 forats de logging + unificar els pins de model** | Un pin a `opus-4-5` i un altre a `sonnet-4-5` conviuen amb `opus-4-7` sense motiu documentat | 1 sessió |

---

## 3. NOTES DE MÈTODE

- **No s'ha executat cap suite de tests.** Hi ha una sessió concurrent escrivint a `dev`
  (últim commit `c07b1d5a`, 21/08 15:49 UTC, TRAM F/F2 de grading) i la llei del projecte és
  **mai dues corregudes alhora** (col·lisió de la BD de test). Els recomptes de tests són de
  cens estàtic (`def test_`), no d'execució.
- **Cap escriptura.** Les consultes a PROD s'han fet contra el dump replicat amb
  `pg_restore -a -n fhort -t <taula> -f -`, sense restaurar res. Les de staging, `SELECT`
  sobre el clúster 18 (port 5433).
- Aquest document **no s'ha commitat** — la llei de l'índex compartit amb sessions
  concurrents ho desaconsella mentre l'altra sessió treballa.

---

*Diagnosi generada el 2026-08-21. Tota xifra d'aquest document surt del codi al disc o del
dump de PROD del mateix dia; cap projecció barreja mesura amb estimació sense dir-ho.*
