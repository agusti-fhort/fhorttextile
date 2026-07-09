# MOTOR DE PATRONS — Document mestre de disseny i pla d'execució

> **Tipus:** document de disseny viu i full de ruta. Separat dels fitxers d'estat
> (`ESTAT_PROJECTE.md` / `ESTAT_BACKOFFICE.md`), que registren el QUÈ ja està fet.
> Aquest document registra el QUÈ volem fer, PER QUÈ, i COM, perquè es pugui programar
> i desplegar pas a pas sense perdre el fil i absorbint els canvis que apareixeran.
>
> **Estat:** disseny conceptual TANCAT. Cap línia de codi escrita. Res executat.
> **Origen:** sessions de disseny 2026-06-12 → 2026-06-14 (Claude chat).
> **Llengua:** treball en català · codi/UI anglès primari.
> **Àmbit:** FHORT Textile Tech, tenant `fhort`, repo `agusti-fhort/fhorttextile`.

---

## 0. RESUM EXECUTIU (una pàgina)

El **Motor de Patrons** és un domini nou dins FTT que entén els fitxers de patronatge
(DXF-AAMA + RUL) que avui els clients ens envien com a blobs morts, els converteix en un
**model paramètric** ancorat a l'espinada semàntica que FTT ja té (POMs → item → sizing →
grading), i permet operar-hi: **escalar** amb els deltes que ja tenim, **rectificar** un
patró després d'un fitting propagant els canvis a totes les peces afectades, i **reexportar**
DXF+RUL que el CAD del client torni a obrir.

Tanca el cercle que avui mor als fitxers:

```
fitting → deltes → rectificació propagada → DXF nou → CAD del client
```

**Per què val molt:** avui, després d'un fitting, una persona ha de tornar al CAD, aplicar
les correccions a mà, recordar totes les peces afectades, recalcular costures que han de
seguir casant i regenerar el grading — hores de feina i la classe d'error més cara (material
tallat malament). El Motor de Patrons converteix la cadena "què he tocat → què afecta → què
més haig de canviar → com queda el patró" d'un acte d'ofici i memòria en una **propagació que
el sistema calcula i proposa**, amb la persona validant en comptes de reconstruint.

**Principi rector (igual que la resta de FTT):** *tot passa al Model; el canònic/plantilla
només suggereix*. La capa paramètrica no és arquitectura nova: és la mateixa llei de sobirania
del `GarmentPOMMap` aplicada a una quarta representació (la geometria).

**Frontera dura amb el mercat:** el sistema **NO dibuixa geometria nova**. Pot moure punts,
obrir més una pinça existent, escalar, escurçar — mai crear topologia (una pinça nova, partir
una vora, una peça nova). Si cal geometria nova, la fa el patronista al seu CAD i reimporta.
Aquesta restricció ens dóna **exportació de risc ~zero** (reproducció pura) i ens manté fora
de competir amb Polypattern/Gerber/Tuka/CLO.

---

## 1. ORIGEN I MOTIVACIÓ (per què existeix)

### 1.1 El problema que vam descartar
La temptació inicial és "IA que dibuixa DXF". Falla a tothom i la recerca ho confirma: els
patrons requereixen precisió de centímetre i les xarxes neuronals donen aproximacions
estadístiques. **Un LLM dibuixant coordenades sempre serà aproximat.** Descartat.

### 1.2 El problema real, reorientat
No volem *generar* patrons (frontera de recerca, fràgil). Volem *operar sobre patrons
existents*: llegir, entendre, rectificar, escalar, marcar. Molt més tractable i alineat amb
la realitat del negoci: **els clients ens envien DXF morts** i no els podem obligar a redibuixar
en cap sistema nou.

### 1.3 Què té el mercat (i per què no hi competim)
- **Valentina / Seamly2D** (open source, 13 anys): patronatge paramètric MADUR, però *neix*
  paramètric — dibuixes des de fórmules. No pren un DXF mort i el parametritza retroactivament.
- **CLO / Browzwear**: tenen la topologia de costura (saben com es munta) per al 3D, però viu
  al seu format natiu; en exportar AAMA es perd.
- **Gerber / Lectra / Optitex / Tuka / Polypattern**: dibuix, grading i marcada professionals.

**La posició FHORT és el PONT:** ningú d'ells té la *veritat de les mesures* que FTT sí té
(POMs canònics, fittings amb deltes reals, estadística per client). FTT decideix amb les dades
que només FTT té, i el CAD del client rep el resultat per re-importar. **Parametrització
retroactiva ancorada a la veritat de mesures = el buit real i el fossat.**

---

## 2. VALIDACIÓ EMPÍRICA DEL FORMAT (què sabem del cert)

Disseccionats fitxers reals (AMELIA AZUL, model Brownie) de **dos CAD diferents**. No és teoria.

### 2.1 Estructura AAMA confirmada
Format obert, ASCII, parells codi/valor, estructura `BLOCKS` (un block per peça). Capes
verificades empíricament:

| Capa | Contingut |
|------|-----------|
| 1 | Línia de **tall** |
| 14 | Línia de **cosit** |
| 8 | Línies **internes** (guies d'elàstic, etc.) |
| 2 | **Turn points** (cantonades) — Polypattern hi enganxa el nº de regla de grading |
| 3 | **Curve points** (forma interna de la vora) |
| 4 | **Piquets** |
| 7 | **Grain line** |
| 6 | **Línia de mirall** (doblec) — INCONSISTENT entre exports → detectar per geometria |

### 2.2 Troballes clau per al disseny
1. **Hi ha tall I cosit** → el marge de costura és derivable per tram (mesurats 12–21 mm).
   Es pot operar sobre el cosit i re-derivar el tall per offset.
2. **Peces a MITGES** (doblec implícit): la vora recta llarga = línia de centre. La capa 6
   (mirall) no sempre hi és → el parser ha de detectar el doblec per geometria, no per capa.
3. **El grading és model REGLA-I-DELTES, no geometria multi-talla.** El DXF guarda NOMÉS la
   talla mostra + un nº de regla per punt. Els deltes (Δx,Δy per talla) viuen al RUL en línies
   `RULE: DELTA n`. El CAD reconstrueix cada talla: `punt_base + delta(regla, talla)`.
   **→ Casa perfectament amb `GradedSpec`** (que ja pensa en deltes per POM×talla).
4. **Variabilitat entre CAD:** Tuka (AAMA 2.1.1, 92 punts, sense nº de regla explícit) vs
   Polypattern (292-B, 266 punts, nº de regla per punt, separador decimal amb COMA "1,0").
   Llegir Polypattern (AAMA canònic ric) cobreix el cas general; Tuka n'és versió reduïda.
5. **Factor d'escala per font de CAD:** unitats DXF no sempre mm directes (Polypattern donava
   ~10× ). El header (`$INSUNITS`/`$MEASUREMENT`) ho indica → normalitzar per font.

### 2.3 Insight unificador
El patró és la **4a representació** de l'espinada semàntica que FTT ja modela:
```
fitxa tècnica  →  POM (G1=51,5cm)  →  GradedSpec (creixement/talla)  →  PATRÓ (el dibuix)
```
Avui viuen desconnectades. El Motor de Patrons **ancora** la 4a representació a les altres
tres; no en duplica cap. I els `TaskType` `pattern_digit`/`pattern_cad`/`scaling`/`marking`
JA modelen aquestes feines com a treball humà → el motor **tecnifica tasques existents**, no
n'inventa de noves.

---

## 3. PRINCIPIS D'ARQUITECTURA (no negociables)

### 3.1 LLM mai dibuixa
La IA toca exactament tres llocs, sempre com a **suggeridor**, mai com a decididor de geometria:
- Suggerir l'esquema semàntic en importar (visió: "aquest block sembla el FRONT").
- Traduir instruccions de la Montse a operacions ("escurça 3 cm" → `tuck(−3, alçada)`).
- Proposar distribucions quan un delta és ambigu (+2 cm pit: quant davant/darrere — regles
  per item).

La **geometria és sempre determinista** (Python pur: `ezdxf` per format, `shapely` per 2D —
offsets, interseccions, longitud d'arc, perímetres). Cap kernel CAD; el problema és 2D pur.

### 3.2 Llei de sobirania: tot passa al Model
Idèntica al `GarmentPOMMap` ja provat: la plantilla de l'item **suggereix** (vocabulari de
rols, POMs candidats, costures típiques); un cop instanciat, **tot és del Model** i és
editable (treure/posar POMs, modificar segments, dimensions, deltes, relacions). El `Model` és
sobirà i autònom; si demà canvia la plantilla de l'item, els models ja fets no es toquen.
Mateixa norma "*mana el document*" del wizard d'import, aplicada a la geometria.

### 3.3 NO crear topologia (la frontera com a característica)
El programa **no té primitives de creació de geometria**. Operacions permeses: moure punts,
obrir més una pinça existent, escalar, escurçar per tuck/desplaçament. Operacions prohibides:
dibuixar una pinça nova, partir una vora sencera, afegir una peça. Si cal → el patronista
redibuixa al seu CAD i reimporta (vegeu §6.4, reancoratge).

**Conseqüència 1:** exportació = **reproducció pura** (mai cal emetre un punt "per regla"
perquè mai hi ha punts sense testimoni). Risc ~zero.
**Conseqüència 2:** no competim amb el CAD de dibuix en cap moment.

### 3.4 Hexagonal (ports i adaptadors) — NOMÉS al Motor de Patrons
El motor (lògica de domini) NO sap d'on vénen les dades ni on van. Defineix **ports**;
els implementen **adaptadors** intercanviables. Permet que el mateix motor visqui de dades
del tenant (avui) o de dades en origen del client (ex. Inditex) sense reescriure (vegeu §8).

Ports mínims:
- **font de geometria** (d'on llegeixo el patró)
- **font de deltes/grading** (`GradedSpec`)
- **persistència de resultat**
- **import/export de format** (adaptador AAMA per CAD de destí)

**Regla dura:** el domini del motor NO depèn mai de Django/ORM directament (res de
`Model.objects.get()` dins el motor). El cost de la hexagonal NO és l'estructura inicial sinó
la **vigilància** que ningú creui la frontera per comoditat. S'aplica **quirúrgicament al motor
de patrons**, no a la resta de FTT (allà seria sobreenginyeria).

> Nota: el motor determinista ja "volia" ser hexagonal — un motor pur és lògica de domini sense
> dependències d'infra. Formalitzar-ho és fer explícites les fronteres que el determinisme ja
> imposava.

### 3.5 Fidelitat d'origen (primera classe)
Cada element importat guarda la seva **representació original literal** com a metadada (no només
la geometria interpretada): l'**empremta** del fitxer (versió AAMA, ordre de seccions, codis de
capa, separador decimal, codi d'unitats, convencions d'anotació) + el rastre literal de cada
entitat. Exportar = "preserva el que pots, genera el mínim". Com que NO creem topologia (§3.3),
el "genera" és buit → exportació = preservar al 100%. L'empremta cobreix tot el fitxer.

---

## 4. MODEL CONCEPTUAL — LES 4 CAPES

```
Capa 0  Parser/Writer AAMA bidireccional        (ezdxf + shapely)   — determinista
Capa 1  Semàntica per Model                     (vores, POMs, costures, restriccions)
Capa 2  Operacions paramètriques per història   (tuck, eixamplar, escalar) — alimentades per deltes
Capa 3  Nesting (marcada)                        (NFP / libnest2d) — determinista, sense IA
```

- La IA només toca la **Capa 1** (suggeriment d'anotació) i la traducció instrucció→operació
  de la **Capa 2**. Capes 0 i 3 són matemàtica pura.
- Les operacions de la Capa 2 són **per història** (com el feature-tree de SolidWorks, NO
  l'sketcher/solver de restriccions): patró base + llista ordenada d'operacions deterministes,
  re-executable, auditable, versionable. Cada operació té postcondicions verificables (costures
  casades, restriccions respectades, marges re-derivats).

---

## 5. MODEL DE DADES

### 5.1 Llei: el domini paramètric penja del `Model`
- `PatternFile` = font de geometria reimportable, **versionada** (`versio`/`versio_anterior`,
  patró idèntic als `ModelFitxer`). Pertany al `Model`. El DXF passa a ser adjunt històric un
  cop importat i autorat.
- Tot el que segueix penja del `Model` (línia plena = sobirà/editable). La plantilla de l'item
  connecta amb línia **discontínua** (suggereix, no posseeix).

### 5.2 Entitats (noms provisionals, anglès)

| Entitat | Pertany a | Funció | Camps clau |
|---------|-----------|--------|------------|
| `PatternFile` | Model | Geometria importada, versionada | `model FK`, `versio`, `versio_anterior`, `font_cad`, `escala_mm`, **`empremta` (fidelitat d'origen)** |
| `PatternPiece` | PatternFile | Una peça (block / carpeta de l'arbre) | `rol`, `nom_block`, `contorns` (geometria desplegada), `doblec_original` (anotat per reexport) |
| `PatternSegment` | PatternPiece | Tram de vora seleccionable per Sew | **rang sobre vora:** `vora`, `t_inici`, `t_fi` (per defecte turn points; curve point si cal partir), `tipus_vora` |
| `PatternPoint` | PatternPiece | Punt SINGULAR amb semàntica (NO tots els vèrtexs) | `x`, `y`, `tipus` (turn/curve), `grade_rule FK` (opc.), rastre literal |
| `PatternPOM` | PatternPiece | El POM dins la carpeta de la peça (pont mètric↔geomètric) | `pom_master FK`, **`definicio_mesura`** (landmark+offset+direcció+landmark), `punts_ancora`, `valor_mesurat` |
| `SewRelation` | **Model** | Costura entre peces (relació, no unió) | `segments_a` (N), `segments_b` (N), `tipus` (casat/frunzit/pinça), `diferencial` |
| `GradeRule` | (geometria) | Taula regla-i-deltes projectable | `numero`, `deltes_per_talla` (Δx,Δy per talla) |

Referenciats (existents): `POMMaster`/`POMGlobal`, `GradedSpec`, `GarmentTypeItem`, `Model`,
`GarmentSet`, `ModelFitxer`.

### 5.3 Les quatre intel·ligències del model (la resta és bastida)

1. **`PatternPOM` = el cor (pont mètric↔geomètric).** Un costat mira a `POMMaster` (quin POM);
   l'altre als `PatternPoint` (on viu sobre la geometria). Materialitza "marcar el POM des d'on
   a on". Un cop ancorat, el valor **es llegeix** de la geometria → la fitxa tècnica es pot
   generar des del patró.
   - **`definicio_mesura`:** l'ancoratge sovint NO és dos punts absoluts sinó una **regla
     relativa a un landmark** ("amplada de pit = 1 cm per sota del punt de sisa"). El punt de
     mesura pot ser DERIVAT (no cap vèrtex). La recepta "des d'on fins on" JA viu al `POMMaster`
     canònic; el `PatternPOM` la **resol** sobre el patró concret.

2. **`PatternPoint` = rol DUAL.** El mateix punt és candidat a ancoratge de POM i portador de
   regla de grading (`grade_rule`). El punt que la Montse marca per al POM sovint JA porta nº de
   regla al DXF. Una entitat, dos usos, un sol gest d'autoria.
   - **Identitat només on hi ha semàntica:** `PatternPoint` són els punts singulars (turn
     points, ancoratges de POM, punts de regla), NO tots els vèrtexs. Els curve points que només
     descriuen corba són dada dins la vora, no entitats. Evita l'explosió de files.

3. **`SewRelation` penja del Model** (relaciona DUES peces = muntatge). Enllaça `PatternSegment`
   en **N-a-N** a banda i banda (la sisa = 2 segments contra una corona = 1). El `tipus` +
   `diferencial` capturen l'excepció:
   - `casat` + diferencial ≠ 0 → **error** (mesures desplaçades).
   - `frunzit`/`pinça` + diferencial → **decisió de disseny**; el diferencial ÉS la instrucció
     de muntatge (ex. baloon: "frunzir corona X cm"). El mateix mecanisme detecta l'error i
     genera la instrucció.

4. **Grading per projecció.** `GradedSpec` (delta escalar per POM×talla, ja vostre) entra per
   `POMMaster`; com que `PatternPOM` sap quins punts ancora i en quina direcció es mesura, aquell
   delta escalar es **distribueix** sobre els `PatternPoint` i es materialitza com a Δx,Δy dins
   `GradeRule`. La taula de regles del RUL no és dada importada: és una **projecció dels vostres
   `GradedSpec`** sobre la geometria. **→ L'exportació RUL surt gratis del que ja teniu.**

### 5.4 Tres forats de disseny — RESOLTS

- **Forat 1 (què és un segment):** turn point → turn point (cas normal). Però patrons mal
  definits/sense definir existeixen → cal poder definir sobre **curve points** com a excepció.
  Solució: `PatternSegment` = **rang sobre vora** (`vora` + `t_inici` + `t_fi`), límits a turn
  point per defecte, curve point si cal partir. UI: turn point = **quadrat verd**, curve point =
  **x groga** (pista visual de "net" vs "forçat").
- **Forat 2 (contorns JSON vs taula):** **identitat només on hi ha semàntica.** El contorn de
  **cosit** és actiu (s'hi mesuren POMs, s'hi ancoren punts, s'hi relaciona Sew) → els seus punts
  singulars són `PatternPoint` reals. Tall/internes/grain/mirall són passius → geometria adjunta
  (a `contorns`, es dibuixen i exporten sense identitat per punt). + el POM porta
  `definicio_mesura` (landmark relatiu).
- **Forat 3 (simetria):** **materialitzar en importar.** Tot i que hi ha patronistes que
  treballen a mitges, a producció acaba passant la peça sencera → per coherència amb els POMs,
  desplegem la peça completa i posem el **POM enter**. El doblec queda anotat (`doblec_original`)
  per reexportar a mitges si el CAD ho espera. Nucli homogeni: una peça és una peça, sense
  asteriscs.

> Criteri de fons compartit pels tres: **identitat només on hi ha semàntica, complexitat
> resolta a l'entrada, nucli homogeni.** El mateix que ja governa FTT.

---

## 6. PUNTS DE CONTACTE AMB FTT EXISTENT (no inventem, projectem)

El segell que el disseny és correcte: cada peça "nova" resulta ser projecció d'una existent.

- **`GarmentSet` → arbre de peces de la UI.** `GarmentSet (codi_base, num_pieces)` → `Model`
  (peça, FK + `piece_number`) → `PatternFile` → `PatternPiece`. L'arbre amb carpetes i
  dependències (twinset, combos) NO inventa jerarquia; projecta el `GarmentSet` existent.
  Subcarpeta per patró = `PatternFile` versionat.
- **`GradedSpec` → `GradeRule`.** Vegeu §5.3.4. L'escalat no "dibuixa talles": projecta deltes
  a punts.
- **`ModelFitxer` (versionat `versio`/`versio_anterior`) → `PatternFile`.** Mateix patró de
  versionat; el reimport intel·ligent de fitxa = el mateix mecanisme per al patró.
- **`TaskType` `pattern_*`/`scaling`/`marking` → tasques de Kanban.** Ancorar POMs geomètrics
  consumeix temps de la Montse → és una tasca amb estimació (`TaskTimeEstimate` per
  `garment_type_item`), assignació i cua. El motor de temps, Kanban i planificació ja ho saben
  tractar. Afegim un `TaskType` de la família `pattern_*`, no un concepte de planificació nou.
- **Gates (`GateEvent`) → gate d'exportació a producció.** Vegeu §7. Mateix patró de gate dur
  que ja teniu (precondició fitting = Production Delivered).
- **Fitxa tècnica pdfme (canvas x/y PPT-style) → peça-amb-POMs com a element col·locable.**
  La peça parsejada amb POMs ancorats és geometria vectorial neta + mesures → element de fitxa
  com una foto/sketch, però amb info tècnica que avui NO hi arriba (ningú sap portar DXF→
  Illustrator). **L'arbre de patrons ha d'existir dins el creador de fitxa** per arrossegar-hi
  peces. Resol un dolor real del fabricant.
- **`PieceFitting` (deltes de fitting) → entrada de la rectificació.** Vegeu §6.4.

### 6.4 El cercle complet: fitting → DXF (l'objectiu final, "el que val milions")

Quan, en un fitting, es modifica una mesura, el sistema sap **què toca què** perquè les
relacions estan declarades (Sew, davant↔esquena, tela↔folro). Apareix una **columna lateral
d'advertències**: *"has allargat la costura; la sisa cal reduir-la X igual que la copa de la
màniga; vols modificar?"*. Un cop acabat, **s'ha generat un DXF amb les noves mesures**.

Cada baula JA està dissenyada:
```
fitting (PieceFitting, ja produeix deltes)
  → relacions diuen què propaga cada delta (SewRelation)
  → operació mou punts existents (Capa 2, abast limitat, risc zero)
  → exportació reprodueix el fitxer amb punts moguts (fidelitat d'origen)
  → gate humà revisa abans de producció
  → DXF nou
```
La columna d'advertències NO és una feature afegida: és la **lectura del graf de relacions**
que hem dissenyat. Tot l'edifici (POMs ancorats, Sew amb excepcions, propagació) existeix
PERQUÈ això sigui possible.

**Cas redibuix:** si cal geometria nova (§3.3), el patronista redibuixa i reimporta. La feina
semàntica NO es perd: com que la sobirania és del Model i el `PatternFile` és versionat, la 2a
importació és una versió nova de geometria sota el mateix Model, i POMs/segments/Sew existents
es **reancoren** sobre la geometria nova (suggeriment + validació) — el mateix mecanisme del
reimport de fitxa. La Montse confirma/ajusta, no torna a marcar des de zero.

---

## 7. GATE HUMÀ D'EXPORTACIÓ (seguretat + producte + legal)

Tota exportació passa per un **gate de revisió** abans de producció. Tres justificacions:

1. **Seguretat:** cap sistema que genera geometria per a producció hauria de passar sense gate
   humà, menys amb IA al reconeixement. El patró alimenta tall de teixit real.
2. **Producte/posicionament:** el gate **reforça** la proposta de valor. FTT no es ven com "la
   màquina que substitueix la patronista" sinó com "l'eina que li estalvia la feina mecànica i
   li deixa el judici". Demanar la revisió de la Montse diu que el seu criteri és insubstituïble
   → desactiva la por a l'automatització, la fa aliada.
3. **Legal:** reconeixement amb clic + desplaçament de responsabilitat.

**Disseny perquè sigui defensable (no decoratiu):**
- **Específic:** "aquest fitxer ha estat generat/modificat automàticament; cal obrir-lo al teu
  CAD i verificar geometria, costures i grading abans de tallar" (no un "úsa sota la teva
  responsabilitat" genèric).
- **Contextual i actiu:** apareix en el moment de l'exportació, no enterrat en uns termes.
- **Auditable:** rastre de qui va acceptar, quan, sobre quina versió del `PatternFile` →
  `GateEvent` o registre d'acceptació (usuari + timestamp + versió). Connecta amb el vostre
  sistema de gates i versionat.

> ⚠️ **El text legal concret s'ha de validar amb assessoria jurídica abans de producció real.**
> L'eficàcia d'una clàusula d'exempció varia per jurisdicció; Claude no és advocat. El disseny
> aquí garanteix la part tècnica (específic + actiu + auditable), no la suficiència legal.

---

## 8. DESPLEGAMENT: SaaS ara, opcionalitat oberta

### 8.1 Decisió
- **SaaS multi-tenant (com ara) = el camí.** On teniu tracció, cost marginal ~0, control del
  producte, metodologia IA interna no exposada. Cobreix LOSAN, Brownie, ANVITO i el gruix del
  mercat.
- **Instal·lable de debò = NO ara, ni objectiu documentat.** Mantenir dos productes (SaaS +
  instal·lable) és quasi dues empreses: versions divergents, suport sobre entorns no
  reproduïbles, i — crític — la metodologia IA interna inspeccionable a casa del client.
- **Terme mitjà per a clients grans (Mango/Inditex): single-tenant dedicat.** Mateix codi, una
  instància aïllada (servidor/BD/regió del client). Satisfà sobirania de dades sense divergir
  el producte. És el que fa la majoria de SaaS B2B en pujar a enterprise.

### 8.2 Com mantenim l'opcionalitat sense cost (hexagonal, §3.4)
La sobirania de dades passa de "decisió d'infra traumàtica" a "**quin adaptador endolles**":
- Tenant normal: adaptador → schema propi (django-tenants).
- Tenant sobirà (Inditex): adaptador → font externa dins la seva xarxa; **les dades viuen en
  origen**, el motor les consumeix pel port sense copiar-les.

La hexagonal **complementa** el multi-tenant: django-tenants = aïllament horitzontal (schema
per client); hexagonal = aïllament vertical (el mòdul no sap qui li serveix les dades). Un
domini + un catàleg d'adaptadors, no dos productes. El cas DXF reimportat ja és això:
import = port d'entrada, export amb empremta = port de sortida; on visquin les dades és invisible
al motor.

**Recomanació CTO:** construir la capa paramètrica amb el **nucli geomètric desacoblat darrere
ports nets** des del dia 1. No construïm l'instal·lable; **no l'impedim**. Barat ara, caríssim
de retrofitar.

---

## 9. FASES I SPRINTS

Ordre per valor i per risc d'exportació creixent. Cada fase ven sola.

### PAT-0 — Parser + model intern + visor read-only
**Objectiu:** FTT *entén* i *mostra* el patró (avui és un blob opac).
- Capa 0: parser AAMA bidireccional (`ezdxf`), normalització d'unitats per font de CAD,
  detecció de doblec per geometria, captura d'**empremta** (fidelitat d'origen).
- Model de dades: `PatternFile`/`PatternPiece`/`PatternPoint`/`PatternSegment` (sense Sew/POM
  encara). Simetria materialitzada en import.
- Visor de patró dins la fitxa del Model (read-only).
- **Victòria:** la fitxa *mostra* el patró. Cap competidor del nínxol ho fa.
- **Risc:** baix (només llegir + dibuixar).

### PAT-1 — Anotació semàntica (autoria Montse)
**Objectiu:** la capa que val (el fossat).
- `PatternPOM` (marcar POM amb punts/landmarks, `definicio_mesura`), `SewRelation` (seleccionar
  segments + botó Sew, tipus + diferencial + excepcions).
- Suggeriment IA (visió) + validació Montse. Plantilla de l'item suggereix; Model posseeix.
- Nova `TaskType` família `pattern_*` per al temps d'autoria (entra a Kanban/planificació).
- **Risc:** mitjà (UX d'autoria; vegeu §10 UI). És la peça humana de tot l'edifici → validar
  amb Montse que el flux és assumible.

### PAT-2 — Escalador (primera victòria comercial)
**Objectiu:** client envia patró d'1 talla (AMELIA arriba literalment sense grading, deltes a 0);
FTT retorna la niada graduada amb els vostres `GradedSpec`.
- Capa 2 (escalat = moure punts pels deltes, topologia intacta).
- Capa 0 writer + RUL (projecció de `GradedSpec` → `GradeRule`).
- Exportació amb destí seleccionable (AAMA Polypattern / Gerber / Tuka) via empremta.
- **Risc d'exportació:** el MÉS BAIX (només mou punts → reproducció pura). Per això va primer.
- **Validació round-trip:** (a) barata: reexportar + rellegir amb el nostre parser + comparar;
  (b) cara: obrir al CAD real i comparar amb l'original.

### PAT-3 — Rectificació post-fitting (el cercle complet)
**Objectiu:** "el que val milions" (§6.4).
- Operacions per història (tuck, eixamplar, obrir pinça) alimentades per deltes de `PieceFitting`.
- Columna d'advertències al fitting (lectura del graf `SewRelation`).
- Gate humà d'exportació (§7).
- DXF post-fitting.
- **Risc:** acotat (operacions que mouen punts; res de topologia nova per §3.3).

### PAT-4 — Nesting (marcada)
**Objectiu:** marcada = nesting de polígons irregulars (NFP). Mòdul independent, pot esperar.
- Solver determinista (libnest2d / SVGnest), restriccions tèxtils com a paràmetres (grain
  obligatori, rotacions 0°/180°, sentit teixit, ratlles/quadres).
- Sense IA (la IA com a molt tradueix instruccions a config).
- **Risc:** independent de la resta; investigació operativa clàssica resolta.

---

## 10. CAPA UI (paradigma FeatureManager de SolidWorks)

> Importància: SEGONA (després de l'exportació). Una UI imperfecta sobre un model correcte és
> iterable; una UI bonica sobre un model equivocat és una trampa. Per això la UI ve després del
> model. És feina REAL de frontend (canvas, hit-testing, snapping) però CONEGUDA.

Paradigma SolidWorks (FeatureManager + PropertyManager + CommandManager):
- **Menú lateral, part superior:** arbre de peces tipus carpetes amb **dependències** (combos/
  twinset = projecció del `GarmentSet`). Dins cada carpeta, **subcarpeta per patró**
  (`PatternFile` versionat).
- **Menú lateral, part inferior:** en seleccionar un patró/peça, es desplega **característiques +
  camps d'edició** (PropertyManager).
- **Barra d'accions superior:** ordenada per tipus i/o desplegables (CommandManager).
- Glifs: turn point = quadrat verd, curve point = x groga (§5.4 forat 1).
- Dues etapes: (1) definir cada peça individualment (segments, POMs dins la seva carpeta);
  (2) a la pantalla principal, **Sew** entre peces (els segments ja existeixen a banda i banda).
- **Eines mínimes d'edició** (no drafting): la creació és quasi-zero (no dibuixem des de zero);
  les eines RELACIONALS (marcar POM, Sew, simetria, selecció) són la substància.

---

## 11. CAPA EXPORTACIÓ (la crítica — garanties honestes)

> Importància: PRIMERA. Sense aquesta capa, tot l'anterior val la meitat.

### 11.1 Garantia: SÍ, es podrà exportar
Basada en fets durs, no optimisme:
1. Format **obert i text pla** (codi/valor ASCII + RUL de text). Emetre'l = escriure bytes en
   estructura coneguda.
2. Tenim **fitxers de referència reals en totes dues direccions, de 2 CAD** (Tuka + Polypattern).
   Escriure = seguir la convenció a la inversa, amb plantilla davant.
3. La part difícil (grading) **ja és vostra** (`GradedSpec` → `RULE: DELTA`).
4. **Determinista**, sense ambigüitat.
5. **Simplificació clau (decisió Agus):** com que NO creem topologia (§3.3), exportar =
   **reproducció pura** del fitxer importat amb punts moguts. El fitxer importat és la seva
   pròpia especificació d'exportació (empremta, §3.5). Risc ~zero.

### 11.2 El que NO es promet (honestedat)
Que "simplement funcioni" a tot CAD al primer intent NO està garantit. Conformar-se a AAMA i
que *el CAD concret obri el fitxer* no són el mateix (ordre de blocks, codi d'unitats, versió
2.1.1 vs 292-B, separador decimal "1,0"). Per això: **exportació amb destí seleccionable = un
perfil d'empremta per CAD de destí**, validat contra el programa real. L'èxit el defineix el
CAD del client en obrir el fitxer → cal la prova real (Polypattern/Gerber a la màquina).

La incògnita NO és *si* es pot fer, sinó *quanta iteració* costa cada CAD. Acotada i mesurable.

### 11.3 Desrisc
- Validació 2 etapes: barata (round-trip amb el nostre parser) + cara (CAD real).
- Inversió en model de dades ric es cobra aquí: com més net `PatternPoint`/`GradeRule`/empremta,
  més mecànica i fiable l'exportació (projectar model ric ≠ reconstruir info perduda).

---

## 12. REGISTRE DE DECISIONS (tancades)

- LLM mai dibuixa coordenades; geometria determinista (ezdxf + shapely).
- Capes 0–3; IA només a Capa 1 (suggeriment) i traducció instrucció→operació a Capa 2.
- Llei de sobirania: tot al Model; plantilla de l'item suggereix, no posseeix.
- Item = categoria que exposa coincidències per similitud; NO motlle, NO isomorfisme. Variants
  = del Model, no de la plantilla. Plantilla s'enriqueix (addició neta), mai es deforma.
- NO crear topologia → exportació reproducció pura + no competir amb CAD de dibuix.
- Segment = rang sobre vora (turn point defecte, curve point excepció). Glifs verd/groc.
- Identitat (`PatternPoint`) només als punts amb semàntica; geometria decorativa = dada.
- Simetria materialitzada en import; POM enter; doblec anotat per reexport.
- POM amb `definicio_mesura` (landmark + offset + direcció); recepta ve del `POMMaster`.
- Grading = projecció de `GradedSpec` sobre punts (`GradeRule`); RUL surt gratis.
- Reancoratge en reimport (mateix mecanisme que reimport de fitxa).
- Gate humà d'exportació (específic + actiu + auditable); text legal a validar amb advocat.
- Hexagonal NOMÉS al motor de patrons (ports/adaptadors); domini no toca ORM.
- Desplegament: SaaS ara; single-tenant dedicat per a grans; instal·lable descartat de moment.
- Fitxa tècnica: arbre de patrons dins el creador; peça-amb-POMs com a element col·locable.
- Cercle fitting→DXF (PAT-3) = objectiu final; columna d'advertències = lectura del graf Sew.

---

## 13. DECISIONS OBERTES / RISCOS / PENDENTS

- **UI canvas:** elecció tècnica (SVG vs Canvas), llibreria de manipulació 2D, snapping a turn/
  curve points. Decisió a PAT-1.
- **`contorns`:** confirmar si geometria adjunta com a JSON n'hi ha prou o cal `PatternContour`
  (taula) per a consulta separada. Probablement JSON a la fase dirigida.
- **Curve points i corbes:** representació polilínia n'hi ha prou per relacionar i validar
  (longitud d'arc). Re-fit d'splines NOMÉS si algun dia el sistema mou geometria al canviar un
  POM (capa dirigent, posterior) — fora d'abast inicial.
- **Direcció dirigent (POM→geometria):** "allarga camal → creix tir" = capa d'equacions
  posterior, més difícil. NO barrejar amb la dirigida (geometria→POM) que fem primer.
- **Validació round-trip per CAD:** quanta iteració per perfil (Polypattern/Gerber/Tuka). Provar
  amb fitxers reals + obrir al programa.
- **Flux d'anotació Montse:** validar que marcar punts + Sew li és natural (peça humana crítica).
- **Plantilla item — variants:** decidit que viuen al Model; confirmar a la pràctica amb LOSAN/
  Brownie que la variació és additiva (rols opcionals) i no estructural.
- **Material pendent:** ja tenim DXF+RUL Tuka (pelat) i Polypattern (amb estructura de grading).
  Cobreix els dos extrems del format.

---

## 14. METODOLOGIA (igual que la resta de FTT)

Diagnosi read-only (grep -n) → confirmació Agus → una peça → `manage.py check` +
`makemigrations --check` / `npm run build` → un commit per peça (git add selectiu, mai `-A`) →
verificar `git log -1`. Migracions: mostrar fitxer abans de migrate, auditar BD després (quirk
django-tenants). Provar amb usuari sense permís (Montse). Restart `fhort.service` després de
backend. Agus fa tots els push. Arquitectura i decisions a Claude chat; Claude Code executa.
Aquest document s'actualitza a mesura que el disseny evolucioni amb la implementació.
