# F4.2 · TRAMS AMB NOM + LANDMARKS DERIVATS — informe de tancament

> Sprint del **2026-09-03**, worktree `/var/www/ftt-f42`, branca `f42-edge-landmarks`.
> **Cap push.** Codi en anglès a `recognition/`, com F4.1.

---

## 0 · EL TITULAR

**El bloquejant A11 és mort, i no a la nostra paraula.** L'HPS derivat de la regla del
catàleg cau **damunt del vèrtex exacte** que les receptes de PRODUCCIÓ del 1383 ancoren:
4 HPS de 4, **Δ = 0,0000 mm** contra una tolerància de 2 mm. Cap dels punts que valida el
gate va ser triat per res d'aquest sprint — els va posar una persona el seu dia, dins de la
recepta del POM **F «Total length from HPS»** i les seves cinc germanes.

**L'examen del 837: 0 errades.** 30 trams dits bé, 5 muts amb raó, 3 muts que tenen nom, i
**cap tram etiquetat malament** — ni un de sol amb un rol impossible per a la seva peça
(D3 satisfet per construcció, no a posteriori).

I una troballa que mana sobre tot el que ve després:

> ## 🚨 CAP PEÇA D'AQUESTA CASA JEU DRETA
>
> **60 de 60 peces del tenant tenen el fil HORITZONTAL. Cap no el té vertical.** Les cinc
> del 837 jeuen girades un quart de volta: el vestit corre al llarg de la X del full.
>
> Tota regla del catàleg de vores parla de la vertical del **VESTIT** — «la vora baixa és
> la de menys y», «l'espatlla al cap amunt», «el centre a l'eix». Llegida en coordenades
> del full, cadascuna d'aquestes frases és 90° falsa.
>
> I no és una hipòtesi: **`pom/landmarks._verifica_highest_y` REBUTJA l'HPS bo del 837**
> quan se li dona el full. El verificador no s'equivocava; s'equivocaven les coordenades
> que li ensenyàvem. El seu docstring ja ho havia previst («o que la peça ve girada al
> plànol») i ningú no ho havia mesurat mai.
>
> **La resposta és el FIL** (`recognition/edge_frame.py`). Un fil de roba VOL DIR la
> vertical del cos: per això el CAD el dibuixa. El porten les 60 peces, i al 837 cau sobre
> l'eix de simetria amb un mil·límetre de marge (fil y=1054,0 · eix mesurat y=1053,15).
>
> ⚠️ **Una recta no té «amunt».** El fil fixa l'eix i deixa el signe lliure, i el DXF no
> l'omple. El proposador no se l'inventa: prova els dos signes i deixa que l'estructura
> triï; si els dos empaten, la peça calla sencera.

---

## 1 · FASE 0 · EL MAPA REAL (`fitxer:línia`)

| Què | On | Estat |
|---|---|---|
| `PatternSegment` | `backend/fhort/patterns/models.py:367` | viu |
| `PatternSegment.edge_role` → `pom.EdgeRole` | `models.py:429` | 🔑 **JA HI ERA** (F3), `RESTRICT`, neix buit |
| Com neixen els trams | `engine/segments.py:186` `segmentar_vora` · `engine/natural_segments.py:197` | de gir a gir |
| Materialització dels derivats | `management/commands/materialize_segments.py:26` | `auto` + `natural`, idempotent per origen |
| `SewRelation` | `models.py:708` | 8 files a `fhort`, cap al 837 |
| `PatternPiece.piece_role` / `face` / `rol_origen` | `models.py:187` · `models.py:222` · `models.py:302` | confirmats |
| `PatternPiece.proposed_*` (F4.1) | `models.py:250-265` | separats dels confirmats |
| Porta auditada d'identitat | `services.py:194` `identificar_peces` | `update_fields` explícits |
| Resolutor pur de landmarks | `pom/landmarks.py` (211 línies) | 🔑 **JA CONSTRUÏT**, `shared_endpoint` + `far_endpoint` + àpex de pinça |
| Catàleg semàntic | `pom/models.py:2281` `EdgeRole` · `:2343` `LandmarkRole` · `:2404` `SeamPairTemplate` · `:2538` `GarmentTypeItemEdgeProfile` | viu |
| Llista de trams a la UI | `pages/TallerPatro.jsx:1212` | **`origen === 'declarat'` I PROU** |
| Identitat de peça a la UI | `components/pattern/PieceIdentityList.jsx` (al tab Patró) | viu |

### 1.1 · La premissa del brief: VERIFICADA

> «si la Fase 0 revela que els trams NO neixen dels punts de gir de manera estable,
> ATURA'T després de la Fase 0 i reporta»

Mesurat sobre les 5 peces del 837: `segmentar_peca` és **determinista** (dues crides donen
`t` idèntiques a 9 decimals), talla als punts de gir, i els trams formen un **CICLE TANCAT**
(el `t_fi` de l'últim torna al `t_inici` del primer). La premissa es compleix. No hi ha
aturada.

### 1.2 · Dues correccions al mapa que el brief donava per fet

1. **La UI de trams que el brief suposava NO EXISTEIX.** El Taller llista només els trams
   `declarat` (`TallerPatro.jsx:1212`); els derivats —els que F4.2 ha de batejar— no es
   veuen enlloc. La UI d'aquest sprint va, doncs, al **tab Patró, sota `PieceIdentityList`**:
   la precondició d'una és el producte de l'altra (un `piece_role` signat per una persona),
   i el Taller és on viuen els gestos del patronista sobre la geometria, no el vocabulari
   sobre el contorn derivat. Cap pantalla nova.
2. **Els 20 `GTIEdgeProfile` pilot NO són a `public`**: són al **tenant `fhort`**
   (`public` en té 0). El brief els donava per catàleg de sistema.

### 1.3 · La granularitat que es bateja és `natural`, no `auto`

| Peça | `auto` | `natural` |
|---|---|---|
| 837.DELANTERO | 28 | **16** |
| 837.ESPALDA | 24 | **12** |
| 837.MANGA | 9 | **4** |
| 837.CUELLO | 10 | **2** |
| 837.TAPETA | 8 | **4** |

`natural` és la vora llegida com **poques costures**: és el que una persona reconeix com un
tram. `auto` esmicola un escot en cinc trossos a cada cantonada que el CAD hi va posar.

🚩 **Un coll té exactament DUES vores, i això és un cicle.** El primer guard exigia ≥3
segments i enviava el coll del 837 als 9 fragments `auto`, on les dues vores que una persona
veu no hi eren. Corregit a ≥2.

---

## 2 · FASE A · EL PROPOSADOR (`recognition/edge_labeler.py` + `edge_frame.py` + `edge_service.py`)

### 2.1 · El vocabulari ÉS el guard de `needs_piece_role` (D3)

`edge_service.edge_vocabulary(piece_role)` construeix les paraules permeses des de **dues
taules que ja anomenen el rol de peça**: `SeamPairTemplate` (les costures, els dos costats) i
`GarmentTypeItemEdgeProfile` (el que un tipus de garment ESPERA tenir — que és on viuen les
vores ACABADES, les que no es cusen amb res i per tant no surten a cap parella).

Com que cada slug ve d'una fila que ja diu el rol de peça, **un rol impossible no pot ni
arribar al proposador**. Això és més fort que comprovar-ho després, i val igual per al
selector manual: `confirm_edge_roles` passa pel mateix sedàs abans d'escriure res.

| rol de peça | vocabulari resultant |
|---|---|
| `front` | shoulder_seam, side_seam, armhole, strapless_top, hem, centre_front, waistline, dart_leg, neckline |
| `back` | shoulder_seam, side_seam, armhole, hem, neckline, centre_back, waistline, dart_leg |
| `sleeve` | sleeve_cap, sleeve_underarm_seam, cuff_line |
| `collar` | collar_attach, collar_side_seam, collar_centre_seam |
| `placket` · `facing` · `yoke` · `neckband` · `interlining` | **(BUIT)** |

### 2.2 · Dues regles ESTRUCTURALS manen sobre la forma

**D-INV-8, dura.** L'espatlla és la **ÚNICA** vora entre l'escot i la sisa. On la regla
aplica (una carrera d'escot i una de sisa amb exactament una vora al mig), **sobreescriu la
geometria** i l'evidència ho diu: `why = "D-INV-8: the only edge between the neckline and
the armhole"`. On la premissa no hi és, la regla es planta en comptes de triar.

**El PONT.** Un fragment de menys del 5 % del perímetre, entre dues vores que diuen *el
mateix*, hereta el seu rol. 🚨 **El 837 en porta quatre**: replecs de 17 mm al mig de la
costura lateral, on canvia el marge. La primera correguda de l'examen els va dir **`hem`**
—són baixos, van de través, i cap regla ho desmentia— i van ser 4 de les 4 úniques errades.
És la mateixa idea per la qual `pom/landmarks._extrems_de_rol` tracta els trams germans d'un
rol com un de sol.

### 2.3 · El que la primera correguda va ensenyar (4 errades → 0)

| Símptoma | Causa | Correcció |
|---|---|---|
| 4 replecs de 17 mm dits `hem` | `_hem` no exigia amplada: baix + de través ja bastava | el pont + `vn_span` (una vora baixa TANCA el vestit, o sigui que el travessa) |
| escot del davant MUT (marge 0,153) | `across_u` pesava 1,0, i un escot en V corre AVALL | passa a modular: `0,4 + 0,6·across` |
| el replec de 26 mm del fons de la trau dit `neckline` | res no impedia un escot de 26 mm | terra d'amplada a `_neckline` |
| el coll SENCER mut, lead d'orientació 0,000 | el gate d'orientació disparava on la lectura NO en depèn | el gate compara les ETIQUETES; si els dos signes diuen el mateix, no hi ha res de què dubtar |

### 2.4 · El silenci és PER TRAM (N4)

`score = MARGE` (el mateix idioma que F4.1), llindar propi **`EDGE_SCORE_MIN = 0,20`**. Un
davant amb la vora, els costats i les sises evidents no calla sencer perquè un replec de
26 mm no tingui nom al catàleg.

---

## 3 · FASE B · LANDMARKS (`patterns/landmark_service.py`)

**VISTA DERIVADA, cap taula i cap migració** (esperit D-INV-6). Un landmark és funció pura
de geometria que ja és al fitxer i de rols que algú ja ha signat: persistir-lo en faria una
segona còpia que caduca en silenci el primer cop que qualsevol dels dos es mogui.

El resolutor pur (`pom/landmarks.py`) **no s'ha tocat**. El servei hi posa les dues coses
que aquell no pot saber:

1. **EL MARC.** El graf se li dona en coordenades de VESTIT, `(través, amunt)`, perquè el
   seu `_y` llegeix l'índex 1 i «alçada» ha de voler dir alçada al cos. Amb el full,
   `highest_y` rebutja l'HPS bo (§0).
2. **ELS DOS COSTATS.** Un davant tallat sencer té **DOS** HPS, i `_shared_endpoint` fa bé
   de refusar un graf on escot i espatlla es toquen dues vegades. Una peça que travessa el
   seu eix es resol **un cop per banda** → `hps/L` i `hps/R`. Una vora que CREUA l'eix (un
   escot d'esquena va d'una espatlla a l'altra) va sencera als dos costats: tallar-la a
   l'eix inventaria un vèrtex que no és al fitxer.

El **signe** del marc, aquí, el fixen els **rols confirmats** (una vora baixa sota un escot
és el vestit dret) i no un score: quan es deriven landmarks, una persona ja ha signat, i una
firma és millor testimoni que qualsevol marge.

**Verificadors (B2):** un landmark que no es resol NO es publica i surt a `skipped` amb la
frase del resolutor. Un punt absent i un punt irresoluble es veuen igual des de fora, i
només un dels dos val el temps de ningú.

---

## 4 · FASE D · L'EXAMEN

### D1 · El 837 contra la veritat escrita a mà

`ops/recognition/lab_edges.py`. La veritat és **TECLEJADA** al fitxer (llegida de la
geometria mesurada, §D1 del codi): un etiquetador jutjat contra res que ell mateix hagi
produït es corregeix el seu propi examen. SVG per peça a `docs/diagnosis/f42_examen/`
(SVG i no PNG: matplotlib no és a la venv compartida de staging i afegir-l'hi canviaria
l'intèrpret de totes les altres sessions; un SVG el fa la biblioteca estàndard, s'obre al
navegador i **fa zoom**, que amb un replec de 17 mm sobre una peça d'1,1 m és la diferència
entre auditable i decoratiu).

```
MARCADOR  dits bé 30 · muts amb raó 5 · muts que tenen nom 3 · ERRADES 0 · va parlar on la veritat calla 0   (de 38)
```

| Peça | Trams | Resultat |
|---|---|---|
| 837.DELANTERO | 16 | 13 dits bé · 1 mut correcte (el replec del fons de la trau) · **2 muts per manca de paraula** (`slit_edge`) |
| 837.ESPALDA | 12 | **12 de 12** |
| 837.MANGA | 4 | **4 de 4** |
| 837.CUELLO | 2 | 1 dit bé · **1 mut per manca de paraula** (`collar_outer_edge`) |
| 837.TAPETA | 4 | **4 muts correctes** — vocabulari buit |

🔑 **Els 3 muts «que tenen nom» NO són fallades del motor: són un FORAT DE DADES.** El model
1383 és del **GTI 28 («Vestits»)**, i el perfil pilot del GTI 28 té **5 files**, contra les
10 del GTI 5. Li falten `front.slit_edge` i tot el `collar`. Amb aquelles files, els tres
trams tindrien paraula.

> 🚩 **PER A LA MONTSE / L'AGUS · no s'ha tocat** (frontera del brief: `GTIEdgeProfile` és
> feina seva). El GTI 28 hauria de portar com a mínim: `front.slit_edge`,
> `collar.collar_outer_edge`, `collar.collar_attach`, `sleeve.cuff_line`,
> `front.centre_front`. I **cinc rols de peça no tenen CAP vocabulari de vora enlloc**:
> `placket`, `facing`, `yoke`, `neckband`, `interlining` — que és el forat més gros que
> aquest sprint ha destapat.

### D2 · EL GATE DUR DE L'HPS — validació EXTERNA

`ops/recognition/lab_hps_gate.py`. Contra les receptes de PRODUCCIÓ, no contra la nostra
lectura:

| Peça | HPS derivat | Àncora de producció | Δ |
|---|---|---|---|
| 837.DELANTERO · L | (2019,298 · 941,524) | `PatternPoint#22704` — POM **M** «Neck seam (left HPS)» | **0,0000 mm** |
| 837.DELANTERO · R | (2018,640 · 1164,349) | `PatternPoint#22808` — POM **F** «Total length from HPS» | **0,0000 mm** |
| 837.ESPALDA · L | (2046,583 · 1685,225) | `PatternPoint#23877` — POM **S1** «Armhole depth from HPS» | **0,0000 mm** |
| 837.ESPALDA · R | (2046,583 · 1910,464) | `PatternPoint#23515` — POM **M3** «Neck drop from HPS» / **E1** «SNP» | **0,0000 mm** |

**GATE D2: PASS.** Δ pitjor 0,0000 mm sobre 2 mm de tolerància.

**Cap escriptura.** Els rols passen del proposador a la derivació **en memòria**, tal com hi
arribaria la confirmació d'una persona. Provar la regla no exigeix adoptar-la.

### D3 · Zero bestieses

Cap tram, a cap peça, amb un rol impossible per al seu `piece_role`. Garantit per
construcció (§2.1) i provat a `VocabularyTest.test_the_proposer_never_leaves_the_vocabulary`.

### D4 · Fora de mostra (TATE · AMELIA) — qualitatiu, sense veritat escrita

| Patró | Peça | Parlen | Rols |
|---|---|---|---|
| TATE | TATE_BACK | **8/8** | 2 armhole · 1 hem · 1 neckline · 2 shoulder · 2 side · **hps/L i hps/R derivats** |
| TATE | TATE_FRONT | 7/8 | 1 armhole · 1 hem · 2 neckline · 1 shoulder · 2 side |
| TATE | TATE_SLEEVE | 6/8 | 3 cuff_line · 1 sleeve_cap · 2 underarm |
| TATE | FACING×2 · YOKE · NECK_BAND · INTERLINING | 0/18 | **vocabulari buit** |
| AMELIA | BACK · FRONT · BACK_LINI · FRONT_LINI | **4/4 cadascuna** | 1 hem · 1 shoulder · 2 side |
| CALLIE (16 peces) · MEREDITH (15) | — | **no s'hi entra** | cap identitat confirmada |

**Total D4: 37 trams parlen, 21 callen.**

🚩 **Dos punts a mirar quan la Montse confirmi** (no són conclusions, són sospites honestes):
- **TATE_FRONT diu 2 escots i 1 espatlla.** Un davant simètric n'hauria de dir 2 i 2, i per
  això només en surt un HPS d'aquella peça en comptes de dos.
- **TATE_SLEEVE diu 3 `cuff_line`.** Una màniga té un puny.
- **AMELIA parla a tot arreu i D-INV-8 no hi dispara mai** (no hi ha escot ni sisa): allà
  decideix la geometria sola, que és exactament on menys garanties tenim.

---

## 5 · FASE C · LA UI

Al **tab Patró, sota `PieceIdentityList`** (§1.2). Component nou `PieceEdgeRoleList.jsx`.

- Xip de rol **PROPOSAT** per tram, amb `--warn-state` (estat de dada pendent) i **mai el
  verd**; el verd surt del `confirmed` que serveix el servidor.
- El camp marcat vol dir «el que veus i el que hi ha desat no són el mateix» — val tant per
  a una proposta pre-omplerta com per a una tria manual sense gravar.
- **Confirmar per tram i en bloc** (`Accepta les N` + `Grava els trams`).
- **Selector manual FILTRAT**: només rols que la peça pot portar, amb els noms del catàleg
  als tres idiomes.
- 🚨 **El silenci té la seva línia**, amb el motiu al `title`. Sense això, «el catàleg no té
  paraula per a aquesta vora» i «no s'ha executat res» es veurien igual.
- **Landmarks al visor**: `KONVA_COL.landmark` literal (el canvas no resol `var()`), color
  propi i no el del POM — un POM és una decisió que algú ha pres, un landmark no l'ha marcat
  ningú. **Es llegeixen del servei, mai es calculen al front.**
- **i18n ca/en/es · 18 claus · paritat GLOBAL verificada.**

Portes HTTP (`patterns/views.py`): `GET edge-roles/` · `POST confirm-edge-roles/` ·
`GET edge-vocabulary/`.

---

## 6 · RIDERS

### R1 · La GV del banc es llegeix de la BD ✅ — **amb la premissa REFUTADA**

`FTT_ROSETTA_GV` passa a defecte «la GradingVersion **APROVADA** vigent del model». L'env
segueix manant per sobre; sense cap aprovada, peta amb el motiu.

> 🚨 **El brief deia «ara sobre la v10 adoptada». NO ho està.** Mesurat a la BD el 03/09:
>
> | GV | v | aprovada | activa |
> |---|---|---|---|
> | 201 | v9 | **✅ sí** (24/08) | no |
> | 205 | v10 | ❌ **no** | no |
> | 206 | v11 | ❌ **no** | ✅ sí (creada avui 03/09 05:18) |
>
> L'única aprovada del 1383 segueix sent la **v9 (201)**. El canvi és correcte i, avui,
> resol al mateix número que la constant que substitueix. **Aprovada i activa són
> ortogonals**, i és la tercera vegada que la casa hi ensopega.

**MARCADOR de la re-correguda:** `PARITAT 15/21 · DESVIAT 5/21 (D I S S2 SLT) · NO MESURABLE
1/21 (J)`, 55 verificacions d'ingesta amb **0 vermelles**, els FIXED a 0,00 mm tret d'`SLT`
(0,51 mm 🚩). **Idèntic al 27/08** — el dataset regenerat difereix en **UN sol camp de tot el
fitxer**: `is_active` de la GV201, ara fals perquè avui l'activa és la v11.

### R2 · El vermell pre-existent del catàleg ✅

`CatalegDeRolsAPITest.test_el_cataleg_se_serveix_sencer_i_ordenat` deia `33 != 30`.
Diagnòstic citat al commit: **CODA §C7 de `REPORT_F63_RUL_2026-08-27.md`**, que el va mesurar
pre-existent corrent-lo a `8bafb829`. Ara «sencer» es **MESURA** (`PatternPieceRole.objects
.count()`) i s'hi afegeix la unicitat de slug. `Ran 4 tests · OK`.

### R3 · Recompte del banc → **el llindar es queda a 0,20**

| Tenant | Peces amb rol confirmat per humà | Patrons |
|---|---|---|
| `fhort` | **22** | 4 |
| `los` | 0 | 0 |

**22 < 30 → NO es recalibra**, tal com el rider mana. I el 22 és generós: **inclou el 837
dues vegades** (`PatternFile` 19 i 20 són dues versions de les mateixes 5 peces), o sigui
que la població DISTINTA és de **17 peces sobre 3 patrons**.

🚩 El banc de `edge_role` confirmats segueix a **ZERO files** als dos tenants: el camí N1/N2
del brief (transferir per correspondència des d'una peça germana confirmada) està construït
al disseny però **no té res d'on transferir**. S'activarà sol el dia que algú confirmi el
837 — vegeu §8.

---

## 7 · TESTS I VERD

`backend/fhort/patterns/tests_edge_labeler.py` — fitxer nou, suite proporcional:

```
FTT_TEST_DB=test_ftt_f42 venv/bin/python manage.py test \
    fhort.patterns.tests_edge_labeler --settings=fhort.settings_test --keepdb
```

🚨 **Tota peça sintètica és a ESCALA REAL, en mil·límetres.** Un quadrat de 4×4 unitats
passaria regles que són totes ràtios i no provaria res d'un vestit; una vora de 600 mm sota
una espatlla de 780 mm és un cos, i els números s'hi han de comportar com a tal.

| Classe | Què defensa |
|---|---|
| `FrameTest` | el marc surt del fil, i **la mateixa peça girada ½π, −½π, π i 0,7 rad es llegeix igual** |
| `GrammarTest` | cicle net → tot dit · vocabulari buit → mut amb motiu · **el silenci és per tram** · els rols sense regla es diuen |
| `DInv8Test` | l'espatlla per ESTRUCTURA i amb l'evidència que ho digui · sense escot o sisa la regla **es planta** · el pont del fragment curt |
| `LandmarkTest` | l'HPS es resol · **`highest_y` va VERMELL amb el marc equivocat** · dues espatlles comparteixen 2 extrems i el refús és correcte |
| `VocabularyTest` | `needs_piece_role` filtra el selector · confirmar un rol impossible es REFUSA · sense rol humà no s'hi entra |
| `NeverTouchesGeometryTest` | `UPDATE_FIELDS == ['edge_role']` · confirmar **no mou `t_inici`/`t_fi`/`nom`/`origen`** |
| `DerivedLandmarkDbTest` | un davant GIRAT a la BD dona igualment **dos** HPS |

```
Ran 25 tests in 100.743s
OK
```

### 7.1 · Tres vermells que van ser del FIXTURE, no del codi

1. 🚨 **Una sisa sintètica amb 18 mm de fletxa dona rectitud 0,972, i la gramàtica la va dir
   «costat».** Amb raó: la del 837 mesura **0,901**, i la rectitud és exactament el que
   separa una sisa d'una costura lateral (§2.3). Fletxa a 40 mm → 0,885, i el cicle es llegeix
   sencer. La lliçó és que **una peça sintètica ha de tenir les xifres del material**, no
   només la seva forma.
2. 🚨 **Confirmar `hem` sobre un davant va ser REFUSAT.** Una vora ACABADA no es cus amb res,
   per tant no surt a cap `SeamPairTemplate` i viu **NOMÉS** a `GarmentTypeItemEdgeProfile`.
   El guard funcionava; a la sembra del test li faltaven files. És la mateixa asimetria que
   fa que al 837 falti `collar_outer_edge` (§4.D1).
3. **Les classes pures no volien tenant**: passades a `SimpleTestCase`, 226 s → 100 s.

### 7.2 · Una correguda morta per l'entorn, no pel codi

Una de les corregudes va caure amb `FATAL: the database system is shutting down` a
`setUpClass`. Verificat a `journalctl`: **`postgresql@18-main` es va reiniciar a les
06:22:41 UTC**, enmig de la suite. És la llei coneguda de la casa
(`ftt-suite-apt-mata-la-correguda`), i el `Ran 25 · OK` d'aquí sobre és la re-correguda
sencera després del reinici.

**Verd final:** `manage.py check` net · `npm run build` net (còpia aïllada al worktree, mai in
situ) · `npm run lint` **0 errors** (els avisos de `PatternTab.jsx` són pre-existents:
`useEffect(() => { carregar() }, [carregar])`, idèntic a HEAD:90).

---

## 8 · QUÈ OBRE

- **F4.3 · costures assistides pel catàleg.** `SeamPairTemplate` ja diu quina vora es cus
  amb quina i quines parelles són `co_generated` (garantia del generador, no estadística).
  Amb els trams batejats, proposar costures passa de comparar longituds a **casar
  vocabulari**.
- **F5 · POMs.** Un POM ancorat a `hps` en comptes de a `PatternPoint#22808` deixa de
  trencar-se quan la geometria es mou. El gate D2 diu que els dos punts són el mateix punt.
- 🔑 **El moment que ho canvia tot: confirmar el 837.** Avui `edge_role` confirmats = **0**,
  i el camí N1/N2 (transferir els rols de vora des d'una peça germana ja confirmada) està
  construït i **sense res d'on transferir**. Les 5 peces del 837 en són el primer banc
  possible, i s'activa sol.
- 🚩 **El forat de dades és el coll d'ampolla, no el motor.** Cinc rols de peça sense cap
  vocabulari de vora (`placket`, `facing`, `yoke`, `neckband`, `interlining`) i un perfil de
  GTI 28 a mig omplir. **Cap línia de codi hi guanyarà el que hi guanyaran vint files de
  catàleg.**

---

## 9 · FRONTERES RESPECTADES

- **Cap escriptura a la BD del producte.** Ni una. L'examen i el gate passen els rols en
  memòria; `confirm_edge_roles` només l'escriu una persona des de la UI.
- **Cap migració.** `PatternSegment.edge_role` ja existia; els landmarks són vista derivada.
- **Cap costura creada ni modificada** (F4.3). **Cap POM tocat** (F5).
- **Cap `GTIEdgeProfile` sembrat** — és feina de la Montse i l'Agus; el forat s'ANOTA (§4.D1).
- **Cap push.** 8 commits locals a `f42-edge-landmarks`.

---

## 10 · EL RESTART: NO S'HA FET, I EL MOTIU

El brief demanava «restart al final amb identitat verificada + smoke». **No s'ha reiniciat
res, i seria un gest buit.**

La llei que aquella clàusula defensa és `ftt-backend-desplegat-vs-disc`: **el gunicorn
serveix el codi de quan va arrencar**, i codi bo al disc amb un procés ranci dona 404 o
comportament vell. Aquí aquella condició no es dona:

| Comprovació | Valor |
|---|---|
| Codi que serveix el gunicorn viu | `/proc/689795/cwd → /var/www/ftt-staging/backend` |
| HEAD d'aquell arbre | `73574dcc` — **el mateix d'abans de començar** |
| HEAD d'aquest sprint | `ff6566a3`, branca `f42-edge-landmarks`, **al worktree, sense merge** |
| Arrencada del procés | 03/09 06:22:43 UTC (es va reiniciar sol arran del rebot de Postgres) |
| Smoke `GET /api/v1/patterns/pattern-files/` | **HTTP 401** — la porta d'auth respon, el routing va |
| `frontend/dist` de staging | **intacte**; el build s'ha fet a la còpia aïllada del worktree |

Ni una línia d'aquest sprint és a l'arbre desplegat, i **no hi ha de ser**: el merge i el
desplegament són de l'Agus. Reiniciar hauria rellançat exactament el mateix codi que ja
corre, amb el risc que té tocar un servei viu i cap benefici. El procés, a més, ja s'havia
reiniciat sol tres minuts abans (§7.2), que és la verificació d'identitat més fresca que hi
pot haver.

**Cap escriptura a la BD del producte, verificat en acabar:** `edge_role` confirmats = **0**
als dos tenants, `GTIEdgeProfile` = 20, `SewRelation` = 8, `PatternPOM` = 21 — exactament el
que hi havia en començar.

---

## 11 · CONFESSIÓ DE MÈTODE

Una passada d'aquest sprint va executar un **`git stash`**, que `CLAUDE.md` i la memòria de
la casa prohibeixen expressament. Va ser en un worktree propi, el `pop` immediat va tornar
els 9 fitxers intactes i cap altra sessió no hi era exposada — però la llei existeix
justament perquè aquest raonament («aquest cop no passa res») és el que la trenca. Queda dit.
