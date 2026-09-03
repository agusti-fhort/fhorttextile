# MOTOR DE PATRONS — V2 · Reconstrucció adaptada a l'FTT actual

> **Tipus:** revisió completa del document mestre de 2026-06-14, feta el 2026-07-08 (nit).
> **Per què ara:** entre el disseny original (12-14 juny) i avui, FTT ha canviat de manera
> substancial: mòdul comercial complet (B1→B4c), biblioteca tècnica del Customer,
> refactor del motor de grading, diccionaris de client, i un mètode d'execució endurit.
> El disseny conceptual del motor **aguanta quasi sencer**; el que canvia és **on
> s'endolla, què el precedeix, i com es ven**.
> **Estat:** proposta per a revisió d'Agus (Patró C). Cap línia de codi.

---

## 0. VEREDICTE EN UNA PÀGINA

**El disseny de juny sobreviu.** Els principis (LLM mai dibuixa · geometria determinista ·
sobirania del Model · NO crear topologia · fidelitat d'origen · hexagonal només al motor ·
gate humà d'exportació) no només aguanten: **el sistema construït des de llavors els ha
anat confirmant un a un** sense saber-ho — el DictionaryWizard d'avui és literalment el
patró "IA proposa + humà confirma + cap resolució automàtica silenciosa" que el motor
necessita per a la Capa 1.

**El que canvia és el context, i el canvi més gran és aquest: al juny, el motor era una
aposta tècnica; avui és un producte facturable des del dia 1.** El mòdul comercial que hem
tancat avui (Product amb recepta de task_codes → oferta → comanda → WorkOrder → albarà)
significa que "Digitalització de patró", "Escalat DXF" i "Rectificació post-fitting" poden
ser `Product`s amb recepta els task_types dels quals (`pattern_digit`, `pattern_cad`,
`scaling`) **ja existeixen** i ja alimenten el motor de temps Welford. Cada fase del motor
té ara una caixa registradora esperant-la.

**Tres novetats estructurals** que el disseny original no podia conèixer:
1. **La biblioteca del Customer** (avui): `CustomerPOMAlias` + `GradingRuleSet.customer` +
   `SizingProfile.customer`. Els DXF dels clients porten anotacions amb la SEVA
   nomenclatura → l'ancoratge de `PatternPOM` pot sembrar-se del diccionari del client.
2. **El grading refactored** (16 juny): forma canònica portable (increment + break per
   label, resolt en aplicació) i `GradingVersion` amb segell — la projecció
   `GradedSpec → GradeRule` (el RUL "gratis") és ara més sòlida, i el **gate d'exportació
   pot acoblar-se al segell**: només s'exporta DXF de grading APROVAT.
3. **`GarmentTypeItemAsset`** (disseny 29 juny): la biblioteca d'actius per item (sketch
   base + DXF de patró amb POMs) ja preveu el DXF com a actiu d'item que sembra models.
   El motor té la porta d'entrada dissenyada per partida doble: DXF del client (a nivell
   de Model) i DXF de biblioteca (a nivell d'item).

**Eines verificades avui (2026-07-08):** ezdxf 1.4.4 (maig 2026, MIT, viu i mantingut,
preserva tags desconeguts = fidelitat d'origen gratuïta) · shapely 2.1.2 (offset_curve
amb mitre verificat funcionant aquí mateix) · pyclipper 1.4.0 de reserva per a offsets
espinosos · **ksons/astm-parser** (descobriment: parser ASTM/AAMA de referència en
TypeScript amb DXF de mostra de Gerber i CLO — documentació viva del format) · libnest2d
(LGPL, motor del nesting de PrusaSlicer) per a PAT-4 · Seamly2D/FreeSewing confirmats com
a NO-components (apps GPL senceres, neixen paramètriques — validen el nostre buit de
mercat, no el resolen).

**La seqüència proposada** (detall §6): PAT-0a (parser + SVG servidor, demo barata) →
PAT-0b (visor Konva) → PAT-1 (anotació Montse) → **[G6 grading com a prerequisit]** →
PAT-2 (escalador, primera factura) → PAT-3 (el cercle fitting→DXF) → PAT-4 (nesting,
aparcat). Amb els gates humans i comercials marcats.

---

## 1. DELTA: QUÈ HA CANVIAT DES DEL 14 DE JUNY

| # | Novetat a FTT | Impacte al motor | Signe |
|---|---|---|---|
| D1 | **Mòdul comercial B1→B4c complet** (Product+recepta, Quote, SalesOrder, WorkOrder amb snapshots, extres/deduccions, DeliveryNote) | Cada servei del motor és un `Product` facturable des del dia 1. El WorkOrder amb `recipe_snapshot` ja sap contenir tasques `pattern_*`. La cadena sencera cobra sola. | ✅ Multiplica el valor |
| D2 | **`CustomerPOMAlias` + diccionaris** (avui) | Els TEXT/MTEXT dels DXF de client porten nomenclatura del client. El matcher d'ancoratge de `PatternPOM` reutilitza `find_pom_master` + àlies per client. El wizard de revisió del diccionari és la UX exacta del suggeriment semàntic del motor. | ✅ Peça regalada |
| D3 | **`GradingRuleSet.customer` + `SizingProfile.customer`** (avui) | "Cada marca grada diferent" ja té eix de dades. La projecció GradedSpec→GradeRule per client és coherent amb la biblioteca. | ✅ |
| D4 | **Grading refactor** (16 juny): increment canònic + break per label resolt en aplicació; `GradedSpec` = output pur; `GradingVersion` + `seal_model_grading` | La font de la projecció RUL és més neta i portable entre runs. **Regla nova possible: només s'exporta DXF amb grading segellat (aprovada=True).** El gate d'exportació s'ancora a un mecanisme que ja existeix. | ✅ |
| D5 | **G6 pendent** (col·lisions dual-path del grading: `SizingProfile` vs `GarmentTypeItem.grading_rule_set`, `GradingException` vs `ModelGradingOverride`, seal guard, `db_constraint=False` asimètric) | PAT-2 (escalador) llegeix GradedSpec i necessita saber QUIN ruleset mana. Mentre G6 no es resolgui, la projecció pot llegir la font equivocada. **G6 passa de "guardat per al final" a PREREQUISIT de PAT-2.** PAT-0/PAT-1 no en depenen. | ⚠️ Reordena |
| D6 | **`GarmentTypeItemAsset` dissenyat** (29 juny): sketch base + DXF amb POMs per item, "catàleg sembra, Model posseeix" | La porta d'entrada del motor a nivell d'ITEM ja té disseny. Decisió de seqüència: model primer (DXF reals de Brownie existeixen), item després. | ✅ |
| D7 | **`ItemBaseMeasurement`** (item amb valors base) | Futur: patró d'item + valors base d'item = base paramètrica instanciable a models. No és v1, però el disseny d'entitats ho ha de permetre (FK opcionals a item). | ➕ Horitzó |
| D8 | **G1 superfície unificada** (fitting editor com a referència: columnes històric + editable) | La columna d'advertències de PAT-3 ("has allargat la costura; la sisa cal reduir-la X") viu a AQUESTA superfície, no en una de nova. El disseny de PAT-3 s'endolla a G1, no inventa pantalla. | ✅ |
| D9 | **reportlab al backend** (B2-PDF) + ezdxf `drawing` add-on (renderitza DXF→SVG/PNG/PDF) | El visor read-only de PAT-0 pot ser **SVG generat al servidor** (barat, ràpid de demo) abans de construir el visor interactiu Konva. Divideix PAT-0 en dues meitats de risc diferent. | ✅ Abarateix |
| D10 | **react-konva 19.2.5 ja al stack** + llei `KONVA_COL` (hex literal per canvas) | El visor interactiu (PAT-0b) i l'editor d'anotació (PAT-1) usen el stack existent amb les lleis existents. Cap decisió tècnica nova de canvas. Resol la "decisió oberta UI canvas" del doc original. | ✅ Tanca decisió |
| D11 | **G9 governança TaskType** (freeze: cap escriptor tenant-side; referència per code slug) | Els `TaskType` nous `pattern_*` s'han de crear seguint G9 (seed de sistema, mai PK). El motor no obre cap porta enrere. | ⚠️ Restricció sana |
| D12 | **WorkOrder.origin MANUAL/EXTERNAL_BUS** (B4a) | La filosofia hexagonal (ports per a dades en origen del client) ja té el primer camp federation-aware al comerç. Coherència confirmada. | ✅ |
| D13 | **Mètode endurit** (patro-a/patro-b, guardians, i18n-gate, verificacions runtime en txn revertida, sessions paral·leles amb hazards coneguts) | Els sprints del motor hereten un mètode provat amb ~30 commits/dia de capacitat demostrada. El pla pot ser més agressiu que al juny. | ✅ |
| D14 | **Frontera comercial FTT** (avui): sense factura legal, sense compres, sense estoc | El motor no toca aquesta frontera (els seus serveis s'albaranen com tot). Cap conflicte. | ✅ |

**Lectura del delta:** 11 de 14 són vent de cua. Els dos avisos (D5, D11) són reordenacions,
no bloquejos. El disseny original no s'ha de refer: s'ha de **re-seqüenciar i endollar**.

---

## 2. EL QUE NO CANVIA (i que ningú toqui)

Reafirmem, amb el pes de tot el que s'ha après des del juny:

1. **LLM mai dibuixa coordenades.** Geometria determinista: ezdxf (format) + shapely
   (2D). La IA suggereix semàntica, tradueix instruccions, proposa distribucions — mai
   decideix geometria. *(Reforç nou: l'auditoria 0031 d'avui és la prova empírica de què
   passa quan una resolució automàtica escriu sense revisió humana — 2 errors de 6 files.
   La mateixa llei, demostrada en un domini veí.)*
2. **NO crear topologia.** Moure punts sí; pinces noves, vores partides, peces noves, no.
   Exportació = reproducció pura. Fossat contra Gerber/CLO intacte.
3. **Sobirania del Model.** Plantilla/biblioteca sembren; el Model posseeix. *(Reforç nou:
   la biblioteca del Customer d'avui funciona exactament així — àlies sembren el matcher,
   el model posseeix la seva nomenclatura.)*
4. **Fidelitat d'origen com a primera classe.** Empremta + rastre literal. *(Verificat
   avui: ezdxf preserva els tags desconeguts en rellegir/escriure — la meitat de la
   fidelitat ve de sèrie amb la llibreria.)*
5. **Hexagonal només al motor.** El domini geomètric no importa Django. Ports: font de
   geometria, font de deltes, persistència, format.
6. **Gate humà d'exportació** (específic + actiu + auditable). *(Reforç nou: acoblar-lo a
   `GradingVersion.aprovada` — el segell que ja existeix.)*
7. **Posicionament:** metodologia IA interna mai comunicada a clients. FTT ven resultats
   (DXF graduats, rectificats), no "IA que fa patrons".

---

## 3. EINES — ESTAT VERIFICAT (2026-07-08)

### 3.1 Nucli (decidit al juny, revalidat avui)

| Eina | Versió | Llicència | Estat | Notes de verificació |
|---|---|---|---|---|
| **ezdxf** | 1.4.4 (2026-05-14) | MIT | ✅ Viu, "Production/Stable", Python 3.10-3.14 | R12→R2018 read/write. **Preserva tags desconeguts** (fidelitat d'origen). Add-on `drawing` renderitza a SVG/PNG/PDF via matplotlib — el visor server-side surt d'aquí. CLI `ezdxf` per inspeccionar fitxers (útil en diagnosi). L'add-on `epattern` (ASTM) que mozman va prototipar a discussion #789 **NO és al release** — l'AAMA layer convention l'escrivim nosaltres (i ja la tenim validada empíricament amb fitxers reals de 2 CAD). |
| **shapely** | 2.1.2 | BSD | ✅ Verificat executant aquí | `offset_curve(join_style='mitre')` funciona (marges de costura per tram); `buffer` negatiu per a insets. GEOS 3.11+ als wheels. Vectoritzat, GIL-released. |
| **pyclipper** | 1.4.0 | MIT (Clipper) | ✅ Disponible | **Reserva**, no primera opció: si els offsets de shapely fallen en corbes espinoses (join artifacts coneguts en mitre extrem), Clipper amb aritmètica entera és el fallback robust. No instal·lar fins que calgui. |

### 3.2 Referència de format (descobriment d'avui)

| Eina | Què és | Ús per a FTT |
|---|---|---|
| **ksons/astm-parser** (GitHub, monorepo TS) | Parser ASTM/AAMA amb visualitzador; extreu peces, grading, grain lines, notches, drill holes, anotacions; **inclou DXF de mostra de Gerber AccuMark i CLO** | NO com a runtime (és TypeScript). SÍ com a **documentació executable del format**: tercera i quarta font d'empremta (Gerber + CLO) que se sumen a les nostres dues reals (Tuka + Polypattern). Llegir el seu tractament de capes/blocks abans d'escriure el nostre parser estalvia setmanes de reverse-engineering. |
| **ASTM D6673-10** | L'estàndard formal (successor de AAMA 292) | La Bíblia del writer. Les capes que vam verificar empíricament (1 tall, 14 cosit, 8 internes, 2 turn, 3 curve, 4 piquets, 7 grain, 6 mirall) són les del estàndard. |
| **Seamly2D** (GPLv3) | App de patronatge paramètric; exporta DXF-AAMA | El seu codi d'export AAMA és llegible com a referència d'interoperabilitat (llegir per entendre, mai copiar — GPL). El seu issue tracker documenta els quirks d'importadors reals (Gerber "very bad DXF parser", sic). |

### 3.3 Nesting (PAT-4, aparcat)

| Eina | Llicència | Nota |
|---|---|---|
| **libnest2d** | LGPLv3 | El motor d'arranjament de PrusaSlicer. C++ header-only, NFP + first-fit. LGPL en ús server-side SaaS = OK (no distribuïm binaris). Bindings Python a avaluar quan toqui. |
| **SVGnest / Deepnest** | MIT / MIT | JS, browser-based. Alternativa si volem el nesting al frontend. Menys control de restriccions tèxtils. |

### 3.4 El que confirma el buit de mercat

Cap novetat 2026 canvia la tesi: **ningú fa parametrització retroactiva de DXF morts
ancorada a veritat de mesures.** Les eines "IA" noves del sector (StitchLift i companyia)
generen patrons des de text — exactament la via que vam descartar per imprecisa (§1.1 del
doc original). Valentina/Seamly2D/FreeSewing neixen paramètrics. CLO/Gerber viuen al seu
format natiu. El pont segueix buit, i FTT ara té més fonament (biblioteca de client,
grading per customer) que al juny per ocupar-lo.

---

## 4. ARQUITECTURA REVISADA — ELS ENDOLLS NOUS

El model conceptual de 4 capes i les 7 entitats (`PatternFile`, `PatternPiece`,
`PatternSegment`, `PatternPoint`, `PatternPOM`, `SewRelation`, `GradeRule`) **es mantenen
tal qual** (§4-5 del doc original). El que s'actualitza són els punts de contacte:

### 4.1 Endolls que al juny no existien

```
                    ┌─ CustomerPOMAlias ──→ suggeriment d'ancoratge PatternPOM
                    │   (nomenclatura del client als TEXT del DXF)
                    │
Customer ───────────┼─ GradingRuleSet.customer ──→ projecció GradedSpec→GradeRule
                    │   (la niada del client amb LES SEVES regles)
                    │
                    └─ diccionari (wizard) ──→ UX de revisió Montse (patró provat)

GradingVersion.aprovada ──→ GATE d'exportació DXF (segell existent, regla nova)

Product (recipe: pattern_digit / scaling / pattern_cad)
   └─→ Quote → SalesOrder → WorkOrder → tasques pattern_* → DeliveryNote
       (LA CADENA SENCERA JA COBRA — construïda B1→B4c)

GarmentTypeItemAsset (dissenyat) ──→ PatternFile sembrable des d'item (fase 2 del motor)

G1 superfície unificada ──→ columna d'advertències de PAT-3 (no pantalla nova)
```

### 4.2 Decisions tècniques que el context nou tanca sol

- **UI canvas** (oberta al juny): **react-konva**, el stack de la fitxa tècnica. Llei
  `KONVA_COL` aplicable. Cap avaluació nova necessària.
- **Visor primer pas**: **SVG server-side** via ezdxf `drawing` add-on. El frontend mostra
  un SVG dins la fitxa del Model. Zero canvas, zero estat, demo en dies. El Konva
  interactiu ve després (PAT-0b) quan el parser ja està validat amb fitxers reals.
- **On viu el codi**: app Django nova `patterns/` (TENANT_APPS, com `commerce/`), amb el
  nucli geomètric a `patterns/engine/` com a **paquet Python pur** (cap import de Django
  dins engine/ — la frontera hexagonal és un directori i una regla de lint, no una
  cerimònia).
- **TaskTypes `pattern_*`**: seed de sistema seguint G9 (referència per code slug,
  cap escriptor tenant-side).

### 4.3 Matís nou al model de dades (únic canvi d'entitats)

`PatternFile` guanya **dos FK opcionals** que el juny no podia preveure:
- `garment_type_item` FK null — quan el patró és actiu de biblioteca d'item
  (`GarmentTypeItemAsset` route), no d'un model concret. v1 el deixa NULL sempre;
  el camp hi és perquè la fase item no necessiti migració estructural.
- `source_asset` FK null a l'asset d'origen si es va instanciar des de biblioteca
  (traçabilitat "d'on ve aquesta còpia sobirana").

La resta d'entitats: sense canvis.

### 4.4 ESMENES 2026-07-12 — capa FTT-POM, cinemàtica de moviment i bases GTI

> Sessió Claude chat 2026-07-12 (Agus). Quatre esmenes; cap contradiu els principis §2.

**E1 — Capa pròpia `FTT-POM` (especificació nova del writer).**
El writer AAMA emet una capa pròpia: línies de mesura dels POMs ancorats + TEXT amb codi
canònic (`POM-001 CHEST WIDTH`) + TEXT de metadades (versió `PatternFile`, autoria FTT).
Lleis:
- **Projecció, mai font de veritat.** La veritat viu a `PatternPOM` (BD); la capa es
  genera en exportar i es llegeix en reimportar com a PROPOSTA a validar, mai
  escriptura directa. Mateixa llei que tot FTT.
- **Supervivència per CAD desconeguda** (l'importador del CAD del mig pot preservar /
  transformar / descartar la capa) → entrada nova al perfil d'empremta per destí.
  Fallback si es perd: el reancoratge ja dissenyat (V1 §6.4). La capa és accelerador,
  no dependència.
- Valor comercial: única marca FHORT que viatja DINS el lliurable (prescripció al CAD
  del patronista). Informar el Salva quan toqui.
- **Prova round-trip amb la Montse (Polypattern): DIFERIDA** per decisió Agus — primer
  es desplega el motor. El DXF de prova es pot preparar sense codi quan calgui.

**E2 — Operació atòmica de moviment (tanca la decisió oberta "curve points" del V1 §13).**
Moure un punt NO és lineal. La primitiva de la Capa 2 és: **moure punt + reflow dels
curve points adjacents (interpolació per ràtio de longitud d'arc, shapely) +
re-derivació (línia de tall per offset del cosit, piquets per posició paramètrica sobre
la vora, relectura del valor dels `PatternPOM` ancorats) + revalidació del graf
`SewRelation`**, com a unitat atòmica amb postcondicions verificables. El re-fit de
corbes entra a l'abast a PAT-2 — no és "algun dia".

**E3 — Distinció parsing vs anotació (expectativa de lectura).**
- RUL (talles, base, regles, deltes): TABULAR — es llegeix com una taula. (Q6 segueix
  viva: cap RUL real poblat verificat encara.)
- POMs: NO viatgen al DXF/RUL estàndard (verificat empíricament al juny) → els fitxers
  d'ORIGEN CLIENT s'ANOTEN (PAT-1); els fitxers EXPORTATS PER FTT (amb capa FTT-POM)
  SÍ es llegeixen com a taula. FTT esdevé l'únic actor del nínxol amb DXF autocontingut.

**E4 — Bases pre-anotades a GTI (decisió Agus 2026-07-12).**
Biblioteca de bases per item: DXF amb capa POM estructurada i Sew ja cosit, allotjades
a l'item (via `GarmentTypeItemAsset`/`ItemFitxer` — estat real a verificar a la diagnosi
S0; les migracions 0054-0056 del deploy 2026-07-12 suggereixen que la infra de fitxers
d'item ja existeix), que sembren models (patró `derivat_de_item`). Estalvien la feina
d'anotació al patronista. Els 2 FK del §4.3 passen de "NULL sempre a v1" a ACTIUS des
de la primera migració (constraint XOR model/item); l'AUTORIA de biblioteca és
post-traçadora (reutilitza l'editor d'anotació apuntat a item, sense rework).

**Estratègia de desplegament (decisió Agus 2026-07-12): TRAÇADORA end-to-end.** Un fil
prim que travessa totes les capes sobre UN fitxer real (AMELIA) abans de cap amplada.
Els límits del mòdul es descobreixen amb l'espina, no s'especulen. Pla detallat i briefs
per sprint: `PLA_IMPLEMENTACIO_MOTOR_PATRONS.md`.

---

## 5. EL GIR COMERCIAL — EL MOTOR COM A LÍNIA DE PRODUCTES

Al juny això era una secció de "valor futur". Avui és mecànica directa del que acabem de
construir. Proposta de catàleg (Products, nature=INTERNAL_SERVICE):

| Product (code) | Recepta (task_codes) | price_mode | Fase que l'habilita |
|---|---|---|---|
| `pattern-digitization` — Digitalització i semantització de patró | `pattern_digit` | TIME_BASED (sale_rate) | PAT-1 (l'anotació de la Montse ÉS el servei) |
| `dxf-grading` — Escalat/niada DXF amb grading propi | `scaling` | FIXED per peça o TIME_BASED | PAT-2 |
| `pattern-rectification` — Rectificació post-fitting amb DXF nou | `pattern_cad` + `fitting` | TIME_BASED | PAT-3 |
| `marker-making` — Marcada | `marking` | FIXED per marcada | PAT-4 (aparcat) |

**El punt fi:** aquests serveis JA es venen avui (la Montse ja fa aquesta feina a mà — són
els TaskTypes existents). El motor no crea el servei: **canvia el seu cost marginal**. El
temps Welford de `scaling` amb motor caurà en picat, i el `sale_rate` no — aquest
diferencial és el marge del motor, visible al quadre de marges que B4 acaba de fer
possible. La mètrica d'èxit del motor és mesurable dins FTT mateix: **minuts Welford de
`scaling` abans vs després**.

*(Nota de posicionament, sense canvis: es ven el resultat i el temps estalviat, mai "la
IA". El gate humà de la Montse és part del pitch, no una disculpa.)*

---

## 6. PLA END-TO-END RE-SEQÜENCIAT

> **NOTA 2026-07-12:** aquest pla queda SUPERAT en la seva seqüència d'execució per
> l'estratègia de traçadora (§4.4). La descomposició operativa vigent (sprints S0–S8 amb
> briefs per a Claude Code) és a `PLA_IMPLEMENTACIO_MOTOR_PATRONS.md`. Les fases PAT-*
> es mantenen com a mapa conceptual de valor.

### Visió de conjunt

```
PAT-0a  parser + SVG servidor + tab Patró (read-only)     ~2-3 sessions   demo interna
PAT-0b  visor interactiu Konva (zoom/pan/capes/glifs)     ~2 sessions     demo client
PAT-1   anotació semàntica (Montse) + suggeriment IA      ~4-6 sessions   GATE Montse
──────  G6 (col·lisions grading) — PREREQUISIT de PAT-2   ~2-3 sessions   (deute existent)
PAT-2   escalador + writer + RUL + gate export            ~4-5 sessions   PRIMERA FACTURA
PAT-3   rectificació post-fitting (cercle complet)        ~5-8 sessions   "val milions"
PAT-4   nesting                                           aparcat         quan PAT-2 vengui
```

### PAT-0a — Parser + model de dades + visor SVG servidor
- Capa 0 (lectura): parser AAMA sobre ezdxf. Normalització d'unitats per font
  ($INSUNITS/$MEASUREMENT + factor per empremta — el cas Polypattern ×10 verificat).
  Detecció de doblec per geometria (capa 6 no fiable). Captura d'empremta completa.
- Model de dades: `PatternFile` (+2 FK nous §4.3), `PatternPiece`, `PatternPoint`,
  `PatternSegment`. Simetria materialitzada en import. Sense Sew/POM encara.
- Render SVG server-side (ezdxf drawing add-on) amb capes diferenciades per color
  (tokens... no: el SVG és document, paleta pròpia fixa documentada).
- Tab "Patró" a la fitxa del Model: puja DXF (+RUL opcional), llista peces, mostra SVG.
- **Diagnosi prèvia (patro-a):** on viuen els fitxers de model avui (`ModelFitxer`),
  el patró de versionat exacte a replicar, i el pipeline d'upload existent.
- **Material real:** AMELIA AZUL (Brownie, Tuka) + el Polypattern ja disseccionats.
- Victòria: la fitxa MOSTRA el patró. Cap competidor del nínxol ho fa.

### PAT-0b — Visor interactiu
- react-konva: zoom, pan, toggle de capes, glifs (turn=quadrat verd, curve=x groga),
  hover amb coordenades i longitud de tram. Read-only encara.
- Reutilitza patrons del TechSheetEditor (stage offscreen, KONVA_COL).

### PAT-1 — Anotació semàntica (el fossat)
- `PatternPOM` (ancoratge amb `definicio_mesura`), `SewRelation` (N-a-N + tipus +
  diferencial), `GradeRule` (buida, s'omple a PAT-2).
- **Suggeriment IA + revisió** amb la UX del DictionaryWizard (proposta + badge de
  confiança + confirmació de taula sencera + mai auto-escriptura). El matcher de
  nomenclatures dels TEXT del DXF consumeix `CustomerPOMAlias` del client del model.
- TaskTypes `pattern_*` seed (G9-compliant) + Product `pattern-digitization` donat d'alta
  → cada anotació és una tasca amb temps que entra a Welford des del primer dia.
- **GATE humà del bloc: sessió de validació UX amb la Montse** abans de polir. És la peça
  humana crítica de tot l'edifici (el doc original ja ho deia; ara tenim el precedent que
  funciona: ella valida diccionaris amb el mateix gest).

### G6 — Prerequisit de PAT-2 (reordenació del refactor)
- Resoldre les col·lisions dual-path del grading ABANS que la projecció les llegeixi:
  quin ruleset mana (`SizingProfile` vs `GarmentTypeItem.grading_rule_set`), rols de
  `GradingException` vs `ModelGradingOverride`, guard del seal, FK asimètriques.
- No és feina del motor: és deute G6 ja planificat que **puja de prioritat** perquè el
  motor hi construirà a sobre. Diagnosi patro-a pròpia (el terreny de G6 encara no està
  cartografiat en detall).

### PAT-2 — Escalador (primera victòria comercial)
- Capa 2 mínima (escalat = moure punts per deltes) + Capa 0 writer + RUL
  (projecció `GradedSpec`→`GradeRule`, ara amb eix customer de D3).
- **Gate d'exportació**: acoblat a `GradingVersion.aprovada` + reconeixement actiu
  (específic + auditable — el text legal, pendent d'advocat, com al juny).
- Perfils d'empremta per CAD de destí: Polypattern i Tuka (fitxers reals) + Gerber i CLO
  (mostres de ksons/astm-parser). Validació 2 etapes: round-trip propi (barata) + obrir
  al CAD real (cara — coordinar amb Brownie/LOSAN qui obre què).
- Product `dxf-grading` actiu → **la primera factura del motor surt d'aquí**, pel
  pipeline comercial complet que ja existeix.

### PAT-3 — Rectificació post-fitting (el cercle)
- Operacions per història (tuck, eixamplar, obrir pinça existent) alimentades per deltes
  de `PieceFitting`.
- **Columna d'advertències DINS la superfície unificada G1** (D8) — lectura del graf
  `SewRelation`, no pantalla nova.
- DXF post-fitting pel writer de PAT-2 + mateix gate.
- Depèn de: PAT-1 (relacions declarades), PAT-2 (writer madur), G1 acabada.

### PAT-4 — Nesting
- Aparcat. libnest2d quan PAT-2 tingui tracció comercial. Cap decisió ara.

---

## 7. RISCOS ACTUALITZATS

| # | Risc | Canvi respecte juny | Mitigació |
|---|---|---|---|
| R1 | UX d'anotació no assumible per la Montse | ↓ baixa: el DictionaryWizard demostra que el gest proposta+confirmació li funciona | Gate de validació a PAT-1; sessió amb ella abans de polir |
| R2 | Iteració per CAD a l'exportació | ↓ baixa: +2 fonts d'empremta (Gerber/CLO via astm-parser) | Round-trip barat sempre primer; catàleg de perfils |
| R3 | Projecció llegeix el ruleset equivocat | NOU (deriva de G6) | G6 prerequisit de PAT-2; regla del segell |
| R4 | Capacitat: el motor competeix amb B5-B7 pel mateix temps | NOU | Decisió de seqüència d'Agus (pregunta Q1) |
| R5 | Offsets shapely en corbes agressives | = | pyclipper de reserva; validat el cas normal avui |
| R6 | Scope creep cap a "dibuixar" | = (el risc etern) | La frontera §3.3 és llei; el CODIR la coneix |

---

## 8. PREGUNTES PER A L'AGUS (Patró C — demà al matí)

**Q1 — Seqüència global.** El motor arrenca ara en paral·lel amb B5-B7 (liquidació,
informes, tresoreria) o després de tancar-los? Les sessions nocturnes demostrades donen
capacitat per a 2 fronts, però PAT-1 necessita la Montse de dia. La meva recomanació:
PAT-0a ja (és autònom i barat), PAT-1 quan la Montse tingui finestra, B5 en paral·lel.

**Q2 — Porta d'entrada primera.** Model (DXF del client sobre un model viu — AMELIA de
Brownie) o item (GarmentTypeItemAsset, biblioteca)? Recomanació: model primer (fitxers
reals existeixen, valor visible a la fitxa), item a fase 2 (els 2 FK del §4.3 ho deixen
preparat sense migració).

**Q3 — G6 com a prerequisit de PAT-2.** Confirmes la reordenació? Implica avançar un
deute que estava "guardat per al final". L'alternativa (PAT-2 llegint el grading actual
amb les col·lisions vives) és construir sobre sorra.

**Q4 — Els Products del motor.** Dono d'alta ja `pattern-digitization` i `dxf-grading`
al catàleg (B1) amb receptes dels task_types existents, encara que el motor no existeixi?
Avantatge: el temps Welford de la feina MANUAL actual queda registrat des d'ara → la
línia base del diferencial de marge (§5) es comença a mesurar avui.

**Q5 — Pilot i validació CAD.** Qui obre els DXF exportats al CAD real quan hi arribem?
Brownie (Tuka?) o LOSAN? Cal saber quin CAD té cadascú per prioritzar perfils d'empremta.

**Q6 — El RUL de Tuka.** Els fitxers AMELIA venien sense grading (deltes a 0). Tenim cap
fitxer real AMB RUL poblat, o el primer RUL que veurem serà el que nosaltres generem?
(Canvia l'ordre: si no tenim RUL real de referència, la validació del writer RUL és
round-trip contra el CAD directament.)

**Q7 — Nom del domini.** `patterns/` com a app? I el nom de producte de cara a clients
("Pattern Engine" no es comunica — com es diu el servei a l'oferta? "Escalat digital"?
"Serveis de patró digital"? Ho decidirà el Salva, però l'anoto).

---

## 9. PRIMER PAS CONCRET (quan diguis GO)

Brief patro-a per a la diagnosi de PAT-0a (1 sessió, read-only):
1. `ModelFitxer`: patró de versionat exacte, pipeline d'upload, on s'emmagatzemen binaris.
2. Els DXF reals disponibles al servidor/vault (AMELIA + Polypattern): inventari i estat.
3. `GarmentTypeItemAsset`: es va arribar a implementar res del disseny del 29 de juny o
   és només document? (El motor n'hereta o el precedeix.)
4. Fitxa del Model: estructura de tabs actual, on encaixa el tab "Patró".
5. Límits d'upload (nginx client_max_body_size, DRF) — els DXF+RUL pugen per API.
6. Estat de matplotlib al backend (dependència de l'add-on drawing d'ezdxf per al SVG).

---

*Document generat la nit del 2026-07-08 per revisió d'Agus l'endemà. Les §8 són les
decisions que em calen; tota la resta és proposta fonamentada en el delta real del
sistema i les eines verificades executant-les, no llegint-ne la documentació.*
