# INFORME — LECTURA PYGARMENT (GarmentCode, ETH): Edge/Panel/Interface i format de costures

**Data:** 2026-08-25 · **Abast:** Patró A pur — clon `--depth 1` de `github.com/maria-korosteleva/GarmentCode`, llicència MIT verificada (Copyright 2024 Maria Korosteleva). Cap fitxer FTT tocat, cap BD.
**Objecte:** punt 1 del pla del 25/08 (DISSENY_MOTOR_PARAMETRIC_V2 §2-bis) — què adoptem al nostre model de trams.
**Fitxers llegits:** `pygarment/garmentcode/{edge,interface,connector,panel,component,operators,edge_factory}.py` + `pygarment/pattern/core.py` + spec real `assets/Patterns/shirt_mean_specification.json`.

---

## 1. EL MODEL EN QUATRE PECES

| Concepte seu | Què és | Equivalent FTT |
|---|---|---|
| **Edge** | segment de frontera entre dos vèrtexs, en 2D local (start = origen). Subclasses: recta, arc de cercle (`CircleEdge`), Bézier quadràtica/cúbica (`CurveEdge`, màx. 2 control points). Porta `label` semàntic opcional | el nostre **tram** |
| **Panel** | bucle tancat d'Edges + col·locació 3D (translation + rotation) + `label` | **PatternPiece** (sense la part 3D) |
| **Interface** | subconjunt ordenat de vores d'un panell "ofert" per cosir, amb coeficient de **ruffle** per secció | el costat d'una **SewRelation** |
| **StitchingRule / Stitches** | parella d'Interfaces; força l'aparellament 1:1 subdividint | **SewRelation** |
| **Component** | agregat recursiu de panells/components (màniga = 2 panells...) | sense equivalent directe (aprox. GTI com a plantilla) |

---

## 2. TROBALLES QUE IMPORTEN (per ordre de valor per al solver v2)

### T1 — LA GRAN: curvatura relativa al marc de la vora ⇒ les corbes no es graden, es re-deriven
`CurveEdge` guarda els control points **relatius al segment start→end** («Storing control points as relative since it preserves overall curve shape during edge extension/contraction», `edge.py:483-486`). El format serialitzat ho fixa com a propietat global: `curvature_coords: relative` (`core.py:31`). I el mecanisme paramètric ho explota: «Applies equally to straight and curvy edges thanks to relative coordinates of curve controls» (`_extend_edge`, `core.py:714`).

**Conseqüència per a FTT:** és la resposta formal al conflicte obert del cens d'auto-ancoratge («els humans ancoren a punts de corba (29%) — les corbes no es graden»). Si la corba viu relativa als seus extrems, **el camp de desplaçament del solver només mou vèrtexs de tram; la corba es re-genera sola i conserva la forma**. El residu A5 del 24/08 (corba que es mou sense regla) i el ⚠ d'A/C/S2 (àncora sobre corba) són exactament el símptoma d'un model on la corba és polilínia de punts independents. Candidata a **decisió de representació canònica del solver v2**.

### T2 — Costura serialitzada: brutalment simple, i el matching és per FRACCIONS
El JSON d'una costura: `[{"panel": "left_sleeve_b", "edge": 2}, {"panel": "left_ftorso", "edge": 2}]` (+ `'right_wrong'` opcional per a dret-contra-revés). Res més: ni longituds, ni direccions, ni frunzit.

L'aparellament es resol ABANS, a `StitchingRule.match_interfaces` (`connector.py:49-66`): compara **fraccions de longitud projectada** dels dos costats (`Interface.projecting_fractions`) i **subdivideix vores** (`subdivide_len`) fins que els dos costats tenen el mateix nombre de segments amb les mateixes fraccions. El format no suporta costures en T de forma nativa — es parteixen.

**Conseqüència:** la nostra parametrització v1 de SewRelation (correspondència per fracció de longitud d'arc) queda **validada per tercera via independent** (CLO3D + GarmentCode). I el nostre `segmentar_vora` és el mateix gest que el seu `match_interfaces`.

### T3 — El mecanisme paramètric: pivot fix declarat + direcció — el vocabulari dels nostres «orígens fixos»
Un paràmetre (`core.py:657-767`): `{type: length|additive_length|curve, value, influence: [{panel, edge_list: [{id, direction: start|end|both, along?}]}]}`. `_extend_edge` mou els vèrtexs **al llarg d'una línia objectiu** (per defecte la corda del meta-edge, o un vector `along` explícit) amb un **punt fix**: `direction='start'` (extrem final fix), `'end'`, o `'both'` (creix simètric des del centre).

**Conseqüència doble:**
- El seu `direction`+`along` és exactament el vocabulari que ens falta per declarar **orígens fixos de grading per peça** (la sisa de l'esquena de Montse) i eixos de creixement.
- `'both'` = repartiment simètric = **exactament el repartiment v1 nostre que falla a E/S/E1** (la S es passa +3,36 a XL). Ells NO ho resolen: el repartiment és declaratiu per paràmetre, sense acoblaments entre paràmetres. La pregunta 7 de Montse continua sent nostra; PyGarment no la contesta.

### T4 — Restriccions natives: NOMÉS `length_equality`, sense solver
`constraint_types = ['length_equality']` (`core.py:552`). S'aplica DESPRÉS dels paràmetres, iterant: mesura les longituds afectades, en fa la mitjana i re-escala cada vora (`core.py:812-846`). Cap sistema d'equacions, cap negociació.

**Conseqüència:** confirma el matís del DISSENY §2-bis — el nostre graf (correspondències de tram + miralls + orígens + deltes de POM per talla) és **més ric que el que cap peça de l'ecosistema resol declarativament**. El camí scipy propi (~mínims quadrats amb restriccions lineals) segueix sent el nostre; planegcs queda com a validació de conceptes.

### T5 — EL PLEC NO EXISTEIX al seu model — divergència frontal amb la nostra llei
Verificat al spec real del shirt: `right_ftorso ↔ left_ftorso` és **una costura** com qualsevol altra. Les mitges peces són sempre **dos panells** (left_/right_) cosits al centre; no hi ha concepte de plec ni de peça al doblec.

**Conseqüència:** la nostra llei («plec = restricció de mirall, NO costura; els punts del plec només es mouen sobre l'eix») és **més forta per a grading** — al seu model, res impedeix que el "centre davant" es desalineï; al nostre, l'eix és restricció. NO adoptar. Però per al gimnàs N2 (punt 2 del pla) cal saber-ho: **les peces del dataset són meitats explícites**, l'empremta (mirall, signatura de vores) s'ha de calcular després de decidir la normalització meitat/sencera — el mateix problema de resolució de mirall de la lliçó DEREK, en versió inversa.

### T6 — El frunzit viu a la Interface, no a la serialització
`ruffle` és un coeficient per secció de la Interface (`interface.py:14-56`), aplicat com a escala de la **longitud projectada** en el matching. Al JSON final no hi viatja: es manifesta com a longituds desiguals entre costats cosits (el simulador distribueix).

**Conseqüència:** el nostre model (frunzit declarat i persistit a SewRelation) és **més explícit que el seu format d'intercanvi**. Mantenim el nostre; el seu «coeficient per secció» (no per costura sencera) és un refinament a considerar si mai frunzim parcialment un tram.

### T7 — Els labels semàntics viatgen al fitxer: el gimnàs N2 porta l'etiquetatge posat
`Edge.label` i `Panel.label` es serialitzen (`edge.py assembly → properties['label']`, `panel.py:311-313`). GarmentCodeData porta doncs **anatomia per vora i per peça** declarada al JSON — exactament el ground truth que el reconeixedor N2 necessita per mesurar % d'encert sense etiquetar res a mà.

### T8 — Pinces i talls = refinament controlat de frontera, no topologia nova
`cut_into_edge` (`operators.py:145`) insereix la forma d'una pinça dins una vora creant vèrtexs nous sobre la mateixa frontera. El mateix fan les subdivisions del matching de costures.

**Conseqüència de matís per a la nostra llei «el sistema mai crea topologia»:** subdividir una vora per casar costures o allotjar una pinça **no és crear topologia de peça** — és refinar la mateixa frontera. El nostre `segmentar_vora` ja viu en aquest matís; convé deixar-lo escrit perquè cap guardià futur el confongui.

### T9 — Avís de qualitat: bug viu al repo (llegir idees, verificar tot)
`Edge.__eq__` (`edge.py:60-78`): el docstring diu «edges are the same if their length is the same»; el codi fa `if close_enough(...): return False` — **invertit**. És MIT i podríem copiar codi, però la llei de casa aplica: **adoptem idees i formats verificats per nosaltres, mai codi a cegues**.

### T10 — Bonus lateral: `even_armhole_openings`
`operators.py:411` — balanceig de la sisa entre davant i esquena (iguala longituds d'obertura ajustant corbes amb `curve_match_tangents`). Referència directa quan Montse contesti la pregunta 7 (acoblament sisa↔pit) — algú ja ha escrit la versió «construcció» d'aquest acoblament.

---

## 3. PROPOSTA D'ADOPCIÓ (decisió Patró C, res implementat)

**Adoptar com a idea de disseny (solver v2):**
1. **Corbes amb control points relatius al marc del tram** com a representació canònica — el camp de desplaçament mou vèrtexs, les corbes es re-deriven (T1). És el canvi que dissol el conflicte àncora-sobre-corba.
2. **Vocabulari d'orígens/direccions** (`direction: start|end|both` + `along`) per declarar orígens fixos de grading i eixos de creixement al graf de restriccions (T3).

**Adoptar com a eina (MIT, ús directe permès):**
3. `pygarment.pattern.core.BasicPattern` com a **lector del dataset** per al punt 2 del pla (gimnàs N2) — parser fet i mantingut, no el reescrivim. Ús aïllat en scripts d'anàlisi, mai al backend de producte sense revisió.
4. El **JSON panels/stitches** com a format pont per confrontar les nostres peces amb el dataset (i candidat a format de tests del graf de costures).

**NO adoptar:**
5. Plec-com-a-costura (T5) — la nostra llei de mirall és superior per a grading.
6. El seu mecanisme de paràmetres com a solver (T3/T4) — massa curt: sense acoblaments, sense negociació; és el que la v2 ve a superar.
7. Cap còpia de codi sense verificar (T9).

**Per escriure a DECISIONS si es beneeix:** el matís de T8 (subdividir frontera ≠ crear topologia).

---

## 4. PUNT 2 DEL PLA — nota operativa

GarmentCodeData (v2) viu a l'ETH Research Collection (DOI `10.3929/ethz-b-000690432`), fora dels dominis de xarxa d'aquest contenidor. La mostra s'ha de baixar des del Mac d'Agus o del servidor. Amb `pygarment` instal·lat (`pip install`, és paquet), llegir cada `specification.json` i extreure l'empremta N2 (allargament, signatura de vores, mirall) és un script curt — i els labels de T7 fan de jutge automàtic. Recordar T5: panells del dataset = meitats explícites.

---

## 5. FRONTERES RESPECTADES

Cap escriptura a cap BD · cap fitxer del repo FTT llegit ni tocat · clon extern en contenidor efímer · llicència MIT verificada abans de llegir.
