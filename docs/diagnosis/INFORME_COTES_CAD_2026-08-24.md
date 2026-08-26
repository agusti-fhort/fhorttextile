# INFORME — GRAMÀTICA DE COTES CAD + PANELL ÚNIC DE POMs

**Data:** 24/08/2026 · **Patró B — IMPLEMENTACIÓ.** Staging, `/var/www/ftt-staging`, branca
`dev`. **Cap push.** HEAD de partida `2b8f3bf3`.
**Llei de suites 23/08 respectada: els tests s'han ESCRIT i NO s'han executat.**
Verificació proporcional: `manage.py check` + `npm run build` + `eslint` dels fitxers tocats
+ smoke al Taller del 1383 amb el servei reiniciat.

---

## VEREDICTE EN QUATRE LÍNIES

> **Els tres concerns estan construïts i vius a staging.** El mode `projeccio`, la cota estil
> CAD arrossegable a tots els modes, i el panell únic de POMs amb totes les accions a la fila.
>
> 🚨 **La premissa del brief sobre l'EK NO es compleix, i el problema no és el mètode: és
> l'ancoratge.** La projecció H de l'EK del 1383 dona **24,99 cm**, no «~22». El que hi ha mal
> ancorat és el punt `b`, i el punt bo existeix i es diu **#22704**: amb ell, i amb la RECTA
> de tota la vida, l'EK mesura **22,28 cm** contra un espec de 22,0 — Δ +0,28, dins de
> tolerància. **No s'ha re-ancorat** (el brief ho prohibia i el banc és de l'Agus).
>
> El mode `projeccio` es lliura igualment i és correcte: el que no és, és la resposta a
> aquesta pregunta concreta.
>
> Els tres controls de l'equip van mossegar, i **dues de les seves troballes haurien arribat
> a l'Agus trencant el gest principal del Taller**: la cota s'empassava el clic de l'imant, i
> l'única porta a esborrar i re-ancorar quedava retallada dins del panell (§5bis).
>
> ⚠️ I amb ell arriba un parany que cal saber: **al 837 les peces seuen girades 90°**, o sigui
> que l'horitzontal DEL PLA és el llarg de la prenda. L'AUTO («l'eix de més recorregut») és
> geometria del pla, no semàntica de la prenda.

---

## 1 · EL CAS DE VALIDACIÓ VIU: QUÈ DIU DE DEBÒ L'EK

Mesurat sobre la geometria viva del PF20 v3, **en lectura, sense escriure res**:

L'ancoratge actual de l'EK és `{a: 22808, b: 22755}`:

| | x (mm) | y (mm) |
|---|---|---|
| `a` = #22808 | 2018,6 | 1164,3 |
| `b` = #22755 | 1768,8 | 1066,2 |

| Mètode | Valor | Δ vs espec (22,0) |
|---|---|---|
| recta (el que hi ha desat) | **26,84** | +4,84 |
| **projecció H** (l'AUTO d'aquests punts) | **24,99** | **+2,99** |
| projecció V | **9,81** | −12,19 |

**Cap dels tres és 22,0**, i tots tres queden fora de la tolerància de ±0,6.

### Per què: la peça seu girada 90°

La línia de fil del DELANTERO corre sobre **X** (`grain: y1 == y2`), o sigui que **el llarg
de la prenda és l'eix X del pla i l'amplada és l'eix Y**. Els POMs ja ancorats ho confirmen
sense marge de dubte:

| POM | mena | \|Δx\| | \|Δy\| | eix del pla |
|---|---|---|---|---|
| A · B · C · D · E | amplades | 0,0–0,2 | 44,3–59,3 | **Y** |
| F | llarg total | 110,8 | 0,4 | **X** |
| EK | *amplada de coll* | **25,0** | **9,8** | **cap dels dos** |

Una amplada hauria d'anar sobre Y com totes les altres. L'EK no hi va per cap dels dos eixos:
el seu `b` **no és l'HPS oposat**.

### El punt bo existeix

Cercant girs de la mateixa vora a 20–24 cm de `a` en Y:

| Punt | (x, y) | \|Δx\| | \|Δy\| | corda |
|---|---|---|---|---|
| **#22704** | (2019,3 · 941,5) | **0,07** | **22,28** | **22,28** |

Mateixa abscissa que `a` (0,07 cm de diferència) i mateixa regla de grading (#1). **És l'HPS
oposat.** Amb `{a: 22808, b: 22704}` i `metode='recta'`, l'EK mesura **22,28 cm** → **Δ +0,28,
DINS de tolerància**. No cal cap mètode nou per a aquest POM.

Totes aquestes xifres estan preses pel **camí de producció sencer** (`annotation_views._mesurar`
→ `DjangoGeometryStore` → `engine.measure.resoldre`), amb objectes `PatternPOM` **en memòria
que no s'han desat mai**. No és el motor provat de costat: és el que el servidor respondria.

> **NO s'ha tocat.** El brief ho prohibia expressament i el banc és material viu. Queda dit
> perquè és una correcció de dos clics al Taller, i perquè la lectura contrària —«el mètode
> no arriba»— hauria fet buscar el problema al motor.

### El parany que el mode nou porta de sèrie

L'AUTO tria **l'eix de més recorregut**, que és el que fa qualsevol CAD i el que el brief
demanava. Però en un patró amb les peces girades, això és geometria del PLA i no semàntica de
la PRENDA: per a una amplada del 837, l'AUTO triaria **H** (el llarg) i cal posar **V** a mà.

Per això els rètols de la UI diuen **«Horitzontal / Vertical»** i mai «amplada / llarg», i
l'ajuda de cada valor adverteix del gir als tres idiomes. **Decisió per a l'Agus:** l'AUTO
podria mirar la LÍNIA DE FIL en lloc del recorregut —hi és a `PatternPiece.grain` i el 100%
de les peces del banc en porten— i llavors «vertical» voldria dir sempre el llarg de la
prenda. És un canvi de semàntica del mode, no un ajust: no s'ha fet.

---

## 2 · CONCERN 1 · EL MODE `projeccio`

Recepta: `{"mode": "projeccio", "a": <id>, "b": <id>, "eix": "H"|"V"|""}`. Buit = AUTO.

- **Model** (`3f81313c`): `METODE_PROJECCIO` als `choices`, `ANCORES_PER_METODE`, i
  `OPCIONS_PER_METODE` — les opcions d'un mètode, que van al vocabulari pel mateix motiu que
  les àncores: perquè el Taller pugui oferir la sub-tria **sense saber que cap eix existeix**.
- **La llei metode↔mode passa a una taula.** Amb dos mètodes n'hi havia prou amb dues branques
  d'ifs al serializer; amb quatre, ja no. `MODES_ACCEPTATS` + `mode_admes()`. Un mètode en pot
  admetre **més d'una** forma: `recta` llegeix `points` **i** `landmark`, i rebutjar el segon
  hauria trencat files desades des de S6.
- **Engine** (`5a5f81ef`): producte de projecció, AUTO amb empat a l'horitzontal (arbitrari i
  escrit a posta). El segment tornat **és la cota** —paral·lela al seu eix, a la coordenada
  mitjana dels dos punts—, i manté la invariant de sempre: la seva longitud ÉS el valor.
- **API i adapters** (`94b392f1`): validació de les dues àncores i de l'eix; i `pom_specs`
  l'exclou de la niada **amb motiu propi, que NO és el de la caiguda**. Una cota té dues
  adreces, o sigui que hi cabria: el que no encaixa és la **DIRECCIÓ**. La cota mana que el
  creixement vagi sobre l'eix i la projecció d'escalat mou els punts al llarg de la recta a→b
  (`grading_projection.py:294-298`).

**Migració 0016** — només `choices`, `sqlmigrate` no-op. Aplicada a `fhort` i `los`.

---

## 3 · CONCERN 2 · LA COTA ESTIL CAD

`PatternPOM.cota_offset_mm` (migració **0017**, la primera de la sèrie que toca la taula):
el desplaçament perpendicular de la línia de cota, en mm i amb signe. **Presentació pura.**

> **Camp a part, i no un tercer element de `definicio_mesura`.** Dins de la recepta,
> qualsevol lector del motor l'hauria de saber ignorar, i el dia que un se n'oblidés el
> desplaçament entraria en un càlcul. Fora, no hi ha cap camí perquè hi entri.
>
> ⚠️ **NO és `models_app.POMPlacement`.** Allò acota un CROQUIS de la fitxa tècnica i es desa
> normalitzat 0..1 sobre la bbox de l'objecte que anota (v. `INFORME_PRECEDENTS_COTES_2026-08-24.md`).
> Això acota GEOMETRIA REAL i va en mil·límetres del patró. Comparteixen la paraula i res més.

La gràfica (`4c258335`), per mètode:

| Mètode | Línia de cota | Testimonis |
|---|---|---|
| recta · projecció | paral·lela a l'eix de la mesura | dels dos extrems |
| caiguda | paral·lela a la caiguda | el de baix surt de la **línia de referència** (el peu hi seu) |
| **per vora** | **la VORA desplaçada**, no la corda | dels dos extrems |

> 🔑 **La vora arregla de passada un defecte que ja hi era**, i està MESURAT sobre el banc.
> El POM **S** del 1383 (`metode='vora'`, sisa davantera) val **22,36 cm**; la corda entre els
> seus dos extrems en fa **20,17**. La línia que es dibuixava era la corda: el número deia una
> cosa i el traç n'ensenyava una altra, 2,2 cm més curta. La reconstrucció de l'arc curt al
> client dona **81 punts i 22,36 cm** — quadra amb el servidor al centímetre.

**El drag va constret a la normal.** Una cota de CAD s'allunya i s'apropa, no llisca: per
això es desa un sol número amb sentit geomètric i no una posició absoluta, que caducaria el
dia que algú recol·loqui una àncora. El canvas s'actualitza abans que el servidor respongui, i
si el desat falla la geometria es rellegeix sencera.

A offset **0** la cota seu sobre la mesura: **cap POM ja ancorat no canvia d'aspecte** fins
que algú el mou. Les 14 cotes del banc estan a 0.

> ⚡ **I una porta que el drag obria sense voler** (`6d8d07de`): `perform_update` cridava
> `_mesurar` a cada desat, i `_mesurar` carrega la geometria SENCERA del `PatternFile` —totes
> les peces, tots els punts: 3.840 al banc del 837. Amb el drag desant a cada deixada, això
> volia dir rellegir tot el patró **cada vegada que algú mou una línia**, per tornar a
> escriure exactament el mateix número. Ara només es recalcula quan el PATCH toca un camp que
> canvia què es mesura, i hi ha un test per a cada cara: que moure la cota **no** hi crida, i
> que canviar la recepta **sí**.

---

## 4 · CONCERN 3 · EL PANELL ÚNIC

Hi havia dues llistes dels mateixos POMs. Ara n'hi ha una (`2ad178c1`), amb totes les accions
en un desplegable per fila: **col·locar · assenyalar al patró · re-ancorar · esborrar**. Amb
dos ancoratges del mateix POM (el pit, mesurat al davant i a l'esquena) les accions es
repeteixen **per peça** i el rètol ho diu.

> 🔑 **El grup que la fusió podia haver-se menjat: «Ancorats que no són a la fitxa».** La
> llista de treball recorre les Mesures del model, o sigui que un POM ancorat per la via
> secundària no hi surt per cap banda. Amb dos panells es veia a l'altre; fondre'ls sense
> això l'hauria fet **desaparèixer**, que és el pitjor que pot fer una fusió de llistes.

**Selecció al canvas + Supr**, amb confirmació sempre: és l'única acció destructiva que es
pot disparar amb una tecla, i una tecla no és una decisió.

### 🚨 El bug de la tecla F, tancat — i no era de la F

El listener de teclat del Taller és **global** i no mirava d'on venia la tecla: escriure una
«f» al nom d'un tram girava l'arc que s'estava previsualitzant. **La malaltia era del
listener**, i per això `esCampDeText()` es posa UNA vegada i val per a les tres tecles. Supr hi
hauria entrat de cap — el Taller té camps de text oberts i esborrar caràcters hi hauria
esborrat cotes.

`Escape` en queda **fora a posta**: cancel·lar el gest des d'un camp és el que la pantalla
anuncia («Esc per sortir»).

---

## 5 · ELS CONTROLS

| Control | Resultat |
|---|---|
| `manage.py check` | **net**, abans de cada commit |
| `npm run build` | **verd** |
| `npx eslint` (fitxers tocats) | **0 errors** · `TallerPatro.jsx` 6 avisos i `PatternViewer.jsx` 5, **tots anteriors**; `ModelPomList.jsx`, `RelationsPanel.jsx` i `patternGeometry.js` a **0** |
| Suites | **NO executades** (llei 23/08). 30 tests nous **escrits** |
| Paritat i18n ca/en/es | **4.746 claus a cadascun**, conjunts idèntics per diferència en les sis direccions (i re-verificat pel verificador pel seu compte) |
| Migració 0016 | `sqlmigrate` no-op · `fhort` i `los` a 0016 |
| Migració 0017 | ⚠️ `sqlmigrate` diu **no-op i és FALS** (la renderitza contra `public`). **Auditat a la BD**: `cota_offset_mm double precision NOT NULL` a `fhort` i `los`, absent a `public` (correcte), 15 files a 0.0 |

### Smoke al Taller del 1383 — servei reiniciat (11:20 UTC)

| Prova contra el gunicorn viu | Resultat |
|---|---|
| `GET pattern-poms/metodes/` | **200** amb els 4 mètodes; `projeccio` porta `opcions: {eix: ['', 'H', 'V']}` |
| `GET pattern-files/20/geometry/` | 14 cotes, **totes amb `cota_offset_mm`** |
| `POST` amb `eix: "Z"` | **400** «Eix de projecció desconegut» · cap fila desada |
| `PATCH cota_offset_mm = 25` sobre l'EK | **200** · offset 25,0 · **valor 26,84 intacte** |
| `PATCH cota_offset_mm = 0` (desfet) | **200** · offset 0,0 · valor 26,84 |
| El `dist` desplegat porta el canvi | sí |

**Estat del banc en acabar: idèntic al de començar** — 14 ancoratges, tots els offsets a 0,
cap POM de mètode `projeccio`, i l'EK amb la seva recepta original.

---

---

## 5bis · ELS CONTROLS DE L'EQUIP

Cap dels tres va sortir de buit, i **dues de les seves troballes haurien arribat a l'Agus
trencant el gest principal del Taller**.

| Rol | Veredicte | Què va trobar |
|---|---|---|
| **verificador** | **VERD** | Portes dures netes, abast complet, zona prohibida intacta, tests llegits i coherents amb el que diuen. 3 cues: Escape del menú avortava el gest, docstring de `RelationsPanel` parlant de quatre famílies quan n'han quedat tres, i dues claus i18n orfes. → `15d363c1` |
| **guardia-ui** | **VETO** | **4 vetos**, tots mesurats i tots certs. → `5e6c1bec` |
| **revisor-diff** | **9 banderes** (2 altes) | Les dues altes eren defectes de gest, no d'estil. → `5e6c1bec` |

### Les dues que ho valien tot

> 🔴 **La cota s'empassava el clic de l'imant.** `PomKonva` escoltava el ratolí en TOTS els
> modes i feia `cancelBubble`; el clic de l'imant no és del shape, és del `Stage`. En mode
> «Marcar POM», a menys de 12 px d'una cota, **el marcador d'imant s'encenia i el clic no
> ancorava res**. I com que a offset 0 —on neixen totes— la cota seu damunt de les seves
> pròpies àncores, i amb `metode='vora'` damunt de tot un tros de contorn, la banda morta
> queia justament on es clica. La llei ja era al fitxer dues-centes línies més amunt: el tram
> declarat i `PecaKonva` es desactiven quan s'anota. `PomKonva` era l'únic que no ho feia.

> 🔴 **El desplegable d'accions quedava retallat.** `Contenidor` és una caixa d'scroll, i el
> CSS força l'`overflow-x` a `auto`: retalla pels quatre costats i cap `zIndex` no en salva.
> Mesurat amb Chromium: un menú de tres ítems a una fila baixa cau **84 px fora**. Amb la
> fusió de panells havia deixat de ser una molèstia — el menú és **l'única porta** a esborrar,
> re-ancorar i assenyalar. Un menú retallat és una funció que no existeix.

I una tercera que valia la pena pel motiu contrari —perquè la va trobar el nas i no la
mesura—: **arrossegar una cota reenquadrava el llenç**. `encaixar` depenia de l'OBJECTE
`bbox`, que `bboxDePeces` refà cada cop que `pieces` canvia d'identitat. Fer zoom sobre un
escot per separar tres cotes, moure'n una, i que el patró saltés a «encaixar-ho tot».

### Els altres vetos d'UI, tots mesurats

- **La cota SELECCIONADA baixava a 2,48:1**: `KONVA_COL.tramSel` (#fb8500) sobre blanc no
  arriba ni al llindar de component, i era el `fill` del text. Assenyalar una cota li feia
  perdre la llegibilitat. La tinta es queda a `KONVA_COL.pom` (5,05:1).
- **«Col·locar al patró» no pot viure al menú ⋯** (NORMA §5.6, literal: «NOMÉS ocasionals…
  MAI passos de flux»). I la fila sencera ja era aquest botó: era duplicar-lo i amagar-lo.
- **`pomSelId` arribava a la fila i no pintava res**: el lligam canvas↔llista quedava
  construït a mitges, encenent la fila forana i callant a les de la fitxa, que són la majoria.

### Una que va sortir de corregir-ne una altra

Derivar la selecció (`pomSelViu`) en lloc de netejar-la amb un efecte deixava el `useMemo`
declarat **per sota** de l'efecte de teclat que el porta a les dependències — i les
dependències s'avaluen DURANT el render. Hauria petat el component sencer. És exactament la
zona morta que la capçalera de `llegirRebuigs` ja documenta al mateix fitxer; `eslint` no la
veu i el `build` tampoc.

### Una correcció a un informe

El revisor-diff va avisar que **HEAD s'havia mogut durant la seva revisió** i ho va atribuir a
una sessió concurrent. No ho era: `6d8d07de` i `15d363c1` són d'aquest mateix tram, fets
mentre ell llegia. La conclusió pràctica que en treia —que aquells dos commits ja tancaven
dues de les seves banderes— era correcta.

## 6 · EL QUE QUEDA OBERT (anotat, no tocat)

1. 🚨 **L'ancoratge de l'EK al 1383 és incorrecte** i la correcció és de dos clics: `b` ha de
   ser **#22704**, no #22755. Amb `recta`, 22,28 cm i dins de tolerància (§1).
2. 🚩 **L'AUTO de l'eix mira el recorregut, no la línia de fil.** Al 837, amb les peces
   girades 90°, això vol dir que per a una amplada cal posar **V** a mà. Fer-lo mirar
   `PatternPiece.grain` seria un canvi de semàntica del mode i és decisió de l'Agus (§1).
3. 🚩 **L'esborrat en bloc de POMs no sobreviu a la fusió de panells.** El client i l'endpoint
   segueixen vius (`pattern-poms/bulk-delete/`); el que ha desaparegut és la superfície. La
   fila del panell únic és per MESURA DE LA FITXA i una casella hi marcaria una fila d'espec,
   no un ancoratge. Tornar-hi vol una selecció per ancoratge: peça pròpia.
4. 🚩 **Ni la caiguda ni la cota entren encara a la niada.** Són dos motius diferents i tots
   dos es diuen a la llista de problemes de l'exportació. La decisió de patronatge de la
   caiguda (com es reparteix el delta entre el punt i la línia) segueix a taula des del tram
   anterior; la de la cota és nova i és la seva germana.
5. 🚩 **Un commit porta dues coses.** `4c258335` va entrar amb la gràfica de cota **i** amb la
   selecció + Supr, perquè viuen entrellaçades al mateix fitxer i al mateix gest. El missatge
   ho diu; separar-les després hauria demanat reescriure l'històric d'una branca compartida.

---

## 7 · ELS COMMITS (cap push)

| Hash | Concern | Què |
|---|---|---|
| `3f81313c` | 1 | model: el mètode PROJECCIÓ + migració 0016; la llei metode↔mode passa a taula |
| `5a5f81ef` | 1 | engine: `resoldre()` sap projectar sobre un eix |
| `94b392f1` | 1 | api: validació de la cota, i per què no gradua |
| `ecff3d23` | 2 | model: `cota_offset_mm` + migració 0017; el camp a l'API i a la geometria |
| `a558eab8` | 1+2 | tests **escrits, no executats** (30) |
| `9a4ca33f` | 1 | taller: el 4t mètode al selector, amb la sub-tria de l'eix |
| `4c258335` | 2+3 | taller: les cotes estil CAD, arrossegables · selecció + Supr · **el guard de la tecla F** |
| `2ad178c1` | 3 | taller: el panell únic de POMs |
| `6d8d07de` | 2 | perf: arrossegar una cota ja no rellegeix el patró sencer |
| `15d363c1` | 3 | fix: tres cues de la fusió (Escape, docstring caducat, claus i18n orfes) — **verificador** |
| `5e6c1bec` | 1+2+3 | fix: els 4 vetos del **guardià d'UI** i les banderes altes del **revisor-diff** |

**Què ha de fer el CTO:** revisar amb `git show <hash>`, decidir els punts 1 i 2 de §6, i fer
el push des d'SSH.
