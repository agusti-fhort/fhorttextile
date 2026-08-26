# INFORME — MODE DE MESURA ORTOGONAL (`PatternPOM`)

**Data:** 24/08/2026 · **Patró B — IMPLEMENTACIÓ.** Staging, clon `/var/www/ftt-staging`,
branca `dev`. **Cap push** (el fa l'Agus des de SSH). HEAD de partida `5306df7e`.
**10 commits**, un concern cadascun, `git add` de paths explícits.

---

## VEREDICTE EN TRES LÍNIES

> El mode **ortogonal està CONSTRUÏT i viu a staging**: es tria al Taller, es guia en tres
> clics, es valida a l'API i es mesura al motor. La caiguda sobreviu al gir de la peça i a
> l'escot asimètric, que és tot el motiu pel qual no és una resta de coordenades.
>
> **La caiguda MESURA i no GRADUA, i és deliberat.** `POMSpec` porta dues adreces i una
> caiguda en té tres; com es reparteix el seu delta entre el punt que cau i la línia que el
> referencia és patronatge i no està decidit. La projecció queda **intacta**, i qui exporti
> ho llegeix a la llista de problemes en lloc de rebre una niada moguda per una regla que
> ningú no ha triat. **Aquesta és la decisió que espera l'Agus.**
>
> Els 4 POMs que van motivar el sprint (**EK1 · EK2 · E5 · SF**) ja es poden ancorar. **No
> s'han ancorat**: el banc del 1383 és material viu i ancorar-hi és feina de patronatge.
>
> Els quatre controls de l'equip van mossegar: **4 dels 10 commits són troballes seves**, i la
> més greu era que un POM ortogonal ancorat **no es dibuixava gens** al canvas (§3bis).

---

## 1 · LA FRONTERA, VERIFICADA ABANS D'IMPLEMENTAR (Patró A intern)

El brief demanava llegir com la projecció `GradedSpec → GradeRule` consumeix `PatternPOM` i
el seu `metode`, i **no implementar** cap decisió que en sortís. Això és el que hi ha:

| On | Què fa | Per què bloqueja la caiguda |
|---|---|---|
| `engine/operations.py:98-107` | `POMSpec` declara **exactament dues** adreces: `ref_a`, `ref_b` | Una caiguda en té **tres**. No hi cap sense canviar el contracte que travessa projecció, export i capa FTT-POM |
| `engine/grading_projection.py:312-331` | `_direccio()` = vector **a→b normalitzat sobre la geometria BASE** | Per a una caiguda, la direcció del creixement **no** és ref_a→ref_b: és la perpendicular. El vector que hi ha calculat apunta al llarg de la línia de referència |
| `engine/grading_projection.py:294-298` | `_deltes_dels_poms()` reparteix `delta/2` a cada extrem, **en sentits oposats** | Aplicat a una caiguda voldria dir **separar els dos HPS l'un de l'altre per fer baixar un escot**. No és el que ningú ha demanat |
| `engine/operations.py:643-649` | `_rellegir_poms()` rellegeix amb `{'mode': 'points', 'a': ref_a, 'b': ref_b}` **literal** | La postcondició tornaria a mesurar una recta encara que el POM fos una caiguda: la invariant `mesura(talla) − mesura(base) == delta` es validaria contra la magnitud equivocada |
| `export.py:169` → `project()` · `export.py:384` `_amb_capa_pom()` | `pom_specs` alimenta la projecció **i** la capa FTT-POM escrita dins del DXF | Un `POMSpec` de dues adreces fabricat des d'una caiguda hauria viatjat fins al fitxer que una màquina de tallar llegeix |

**LA DECISIÓ QUE FALTA** (i que aquest sprint NO pren): quan el grading diu que `EK2` («neck
drop from HPS») creix 0,5 cm, **què es mou**? El punt que cau, tot sol? La línia de
referència, tota sola? Es reparteix? I si es reparteix, en quina proporció, i igual per a un
escot que per a una profunditat de sisa? La v1 de la projecció reparteix **simètricament**
entre dos punts i ho declara com a decisió, no com a simplificació
(`grading_projection.py:41-53`); per a tres àncores amb papers diferents no hi ha cap
equivalent «raonable per defecte». **És patronatge, i s'escriu amb la Montse davant.**

Mentrestant la caiguda queda **exclosa de la projecció amb motiu propi**, i el motiu es diu:
no cau al calaix genèric de «mode que la v1 no sap graduar», sinó que declara que **es mesura
i no es gradua**. És la mateixa llei que ja regeix el `landmark` i els ancoratges orfes —
*omissions, mai en silenci* (`adapters.py:569-585`).

---

## 2 · QUÈ S'HA CONSTRUÏT

### 2.1 · Model — `a92be1a9`

`PatternPOM.METODE_ORTOGONAL = 'ortogonal'` als `METODE_CHOICES`. La recepta creix a tres
àncores; **els dos modes existents no canvien ni de forma ni de contingut**:

```
{"mode": "points",    "a": <id>, "b": <id>}                       ← igual
{"mode": "landmark",  "landmark": <id>, "offset_cm": …, "b": <id>} ← igual
{"mode": "ortogonal", "ref_a": <id>, "ref_b": <id>, "p": <id>}     ← nou
```

`metode` i `definicio_mesura['mode']` són **una decisió escrita dues vegades** — la primera
la veuen l'API i la UI, la segona és la forma que el motor ha de saber llegir. En lloc de
deixar-les com a dos camps que es poden contradir, la classe en declara el lligam
(`PatternPOM.mode_esperat`) i el serializer el fa complir.

**Migració `0015_patternpom_metode_ortogonal`.** Només `choices`: `sqlmigrate` surt **no-op**
(Postgres no en desa cap constraint). Existeix igualment perquè l'estat de les migracions i
el dels models han de dir el mateix — si no, el `makemigrations` següent de qualsevol altra
sessió se l'inventaria.

> **Aplicada i commitada alhora** (llei `ftt-migracions-es-commiten-en-aplicar-se`).
> `migrate_schemas --tenant`. Auditat a la BD, esquema per esquema:
> `fhort` → 0015 · `los` → 0015 · `public` → 0014, **que és el que toca**: `fhort.patterns`
> és app de TENANT i no de SHARED (`settings.py:62-75`).

### 2.2 · Engine — `199f4b25`

`engine/measure.resoldre()` guanya la branca `mode == 'ortogonal'`:

```
distància = |(ref_b − ref_a) × (p − ref_a)| / |ref_b − ref_a|
```

Producte vectorial 2D, **no** projecció sobre eixos. És l'àrea del paral·lelogram partida per
la base, i tant l'àrea com la base **giren juntes**: per això el valor no es mou quan la peça
seu girada al plànol.

- **El signe es descarta dins de `_ortogonal`**, no més amunt: una caiguda no té costat, i qui
  llegeixi el valor no ha de saber que mai va existir.
- **El peu de la perpendicular és DERIVAT** (`derivat=True`), com el punt del mode `landmark`:
  es calcula cada vegada, no es materialitza com a vèrtex. Pot caure **fora** del segment
  ref_a–ref_b, i és correcte que hi caigui: la referència és el **nivell** (una recta), no un
  tram.
- **`punts` torna només `(peu → p)`**: la polilínia la longitud de la qual **és** el valor. És
  la invariant que ja complien `recta` i `vora`, i mantenir-la vol dir que ningú no ha
  d'aprendre un cas especial per dibuixar-ho. La línia de referència no hi entra perquè no
  forma part de la mesura; qui la vulgui pintar ja en té les dues àncores a la recepta.
- **El `metode` no hi juga cap paper**: una perpendicular no té variant recta ni variant per
  vora.

**Degenerats — error explícit, cap NaN que viatgi:**

| Cas | Resposta |
|---|---|
| `ref_a ≈ ref_b` (per sota de `TOL_REFERENCIA_MM = 1e-6`, el mateix llindar que `grading_projection.TOL_DIRECCIO_MM` fa servir per a la mateixa pregunta) | `MeasureError`: «no defineixen cap línia» |
| Una àncora que falta | `MeasureError` que **diu QUINA** de les tres. Amb tres papers diferents, «falta un punt» no deixaria saber quina s'ha de tornar a clicar |
| `p` sobre la línia | **No és cap degenerat**: és una caiguda de zero, i es torna com a tal. Qui ho ha de rebutjar és l'API (una recepta que ho demana és un error de qui la fa), no el motor |

### 2.3 · Adapters — `2a02a20f`

`pom_specs()` reconeix el mode nou i l'exclou **amb motiu propi** (v. §1). Cap canvi per a les
receptes existents.

### 2.4 · API — `487b8469`

**Validació de la recepta** (`PatternPOMSerializer._valida_ortogonal`): les tres àncores hi han
de ser, `ref_a ≠ ref_b`, i `p` no pot ser cap de les dues (mesuraria zero — el mateix error que
el `a == b` del mode de punts, i es rebota igual). L'engine ja rebutja el primer cas, però
rebutjar-lo **només allà** voldria dir desar un ancoratge sabent que no es podrà mesurar.

**El lligam `metode` ↔ `mode`** (`PatternPOMSerializer.validate`) es comprova contra l'estat
**EFECTIU**, no contra el payload: un PATCH pot portar només la recepta (és el que fa el Taller
en reobrir un POM) o només el mètode, i llavors la meitat que falta és la que ja hi ha al disc.
Validar només el que arriba deixaria passar exactament el cas que això vol impedir.

**`GET /api/v1/patterns/pattern-poms/metodes/` — cap enum al front.** Serveix els codis i la
gramàtica de cadascun, tot de `PatternPOM.ANCORES_PER_METODE`, que viu al costat dels `choices`:

```json
[{"codi":"recta","mode":"points","ancores":["a","b"]},
 {"codi":"vora","mode":"points","ancores":["a","b"]},
 {"codi":"ortogonal","mode":"ortogonal","ancores":["ref_a","ref_b","p"]}]
```

Sense rètols, a posta: els tres idiomes són del client (llei i18n-gate), i una etiqueta servida
des d'aquí seria un quart lloc on mantenir-los.

### 2.5 · Taller — `e5eebfc9`

La forma del gest la dicta el **mètode**, i el mètode ve del servidor. De l'endpoint en surten
les **tres** coses que abans haurien estat tres llistes escrites a mà al `.jsx`: quants clics
guia el canvas (`ancores.length`), com es construeix la recepta (les claus, en ordre) i què es
demana a cada pas. **Un mètode nou al backend l'ofereix aquesta pantalla sola.**

- **El gest de dos punts no s'ha tocat.** `place_a` / `place_b` / `pom_hint_*` són literalment
  els que hi havia: és gest conformat. La branca nova és per als mètodes de tres àncores o més.
- **Guia de tres passos**: xips amb l'àncora que toca marcada (`ti-point` → `ti-check`) i una
  frase que diu sempre quina és i en quin pas va. Mateixa llei que el gest de la pinça, que
  també és de tres clics.
- **Canviar de mètode reinicia els punts clicats**: dos punts posats per a una recta no són les
  dues primeres àncores d'una caiguda, i conservar-los hauria fet que el tercer clic ancorés
  una cosa que ningú no ha marcat.
- **Reobrir** posa el selector al mètode d'aquell POM i dibuixa l'ombra amb les seves àncores.
  Llegir-hi sempre `a` i `b` hauria deixat l'ombra buida en tot el que no fos una recta.
- **Sense vocabulari** (xarxa, permís): no hi ha selector i el gest és el de dos punts de
  sempre. Un mínim, no un enum de recanvi.

El **visor** hi va haver d'entrar després (v. §3bis): dibuixa la caiguda com el segment
(peu → p) —la polilínia la longitud de la qual és el valor—, i mentre es marca pinta la
línia de REFERÈNCIA fina i la perpendicular que en penja, en lloc de la polilínia
`ref_a → ref_b → p`, que no és cap caiguda. El peu el calcula `patternGeometry.peuPerpendicular`
amb la mateixa fórmula que el motor, i **només per dibuixar**: la xifra que val segueix sent
la del servidor.

> **BUG DE LA TECLA `F`: no s'ha empitjorat.** El listener global de
> `TallerPatro.jsx:293-305` segueix exactament com estava — **no s'hi ha afegit cap listener
> de teclat nou**, ni global ni local. El deute (`e.target` sense comprovar, o sigui que
> teclejar una `f` en un camp de text gira l'arc) queda **obert i intacte**.

### 2.6 · Tests — `51339ef9`

**25 tests nous**, en dues classes:

`CaigudaOrtogonalTest` (geometria pura, sense BD — el motor és un paquet Python pur i aquesta
absència és la prova que la frontera hexagonal aguanta):

- **El test que mana**: mateix valor a 0°, 30°, 90°, 137,5°, −63°, 180° i 359,9°, i el mateix
  amb la referència inclinada.
- **La prova per l'absurd**: ΔY passa el cas recte i **es trenca als 30°**. És el bug que
  aquest mode existeix per evitar, escrit com a test perquè ningú no el reintrodueixi «per
  simplificar».
- Peu derivat i no materialitzat · `punts` = la polilínia que val · valor sense signe · ordre
  de les referències indiferent · peu fora del tram · els tres degenerats · i que **els modes
  de sempre no han canviat de resposta**.

`CaigudaOrtogonalAPITest` (BD, sobre l'AMELIA de `fixtures/`): el camí bo, els quatre rebots,
el PATCH que intenta separar les dues meitats, l'endpoint de vocabulari, i un test que lliga
els `choices` amb la seva gramàtica (qui afegeixi un mètode i s'oblidi de les àncores peta
allà i no al navegador).

**I la frontera, escrita com a test perquè es vegi que és deliberada**: la caiguda es mesura i
NO entra a la niada; les receptes de sempre hi segueixen entrant. Si algú fa graduable el mode
ortogonal sense decidir com es reparteix el delta, aquests dos es posen vermells.

> ⚠️ **Cap test toca el banc del 837.** Es munten sobre l'AMELIA de `fixtures/`, tal com
> demanava el brief: el 1383 és material viu de l'Agus i un test que hi escrivís deixaria
> feina que ningú no ha demanat dins de la seva pantalla.

---

## 3 · ELS CONTROLS

| Control | Resultat |
|---|---|
| `manage.py check` | **net** (0 issues), abans de cada commit |
| `npm run build` | **verd** (904 ms) |
| `npx eslint` sobre els 4 fitxers de front tocats | **0 errors** · `TallerPatro.jsx` es queda amb els seus 6 avisos anteriors i `PatternViewer.jsx` amb els seus 5; `patternGeometry.js` net |
| `manage.py test fhort.patterns` | **405 tests · OK** (1.249 s). Re-corregudes les 25 noves després dels fixos: **OK** |
| Paritat i18n ca/en/es | **4.728 claus a cadascun**, conjunts idèntics (verificat per diferència de conjunts, no per recompte — i re-verificat pel guardià pel seu compte) |
| `sqlmigrate patterns 0015` | **no-op** |
| Migracions aplicades i auditades a la BD | `fhort` 0015 · `los` 0015 · `public` 0014 (correcte: app de tenant) |
| `/api/schema/` | **200** — cap avís nou de `drf-spectacular` sobre el mètode nou |
| Esquema `test` residual després de la suite | **cap** (`fhort`, `los`, `public` i prou) |

### Smoke al Taller del 1383 — **servei reiniciat**

`systemctl restart ftt-staging` — dues vegades: 09:57 UTC per a l'smoke, i **10:42 UTC** en
tancar, perquè el que corre sigui exactament HEAD. Abans del primer reinici servia el codi del
**23/08 14:52**: sense reiniciar, el build verd no hauria provat res.

| Prova contra el gunicorn viu | Resultat |
|---|---|
| `GET pattern-poms/metodes/` sense token | **401** (la ruta hi és i demana auth) |
| `GET pattern-poms/metodes/` amb token | **200** amb els tres mètodes i la seva gramàtica |
| `GET pattern-poms/?pattern_piece__pattern_file=20` | **14 POMs**, tots `recta`, valors intactes |
| `POST` amb `ref_a == ref_b` | **400** — i **cap fila desada** |
| `POST` amb `metode='ortogonal'` i recepta de punts | **400**: «El mètode «ortogonal» vol una recepta de mode «ortogonal», i la que ha arribat és de mode «points».» |
| `PatternPOM` al PF20 després de l'smoke | **14** (igual que abans) · amb `metode='ortogonal'`: **0** |
| El `dist` desplegat porta el canvi | sí: `pattern-poms/metodes`, `ancora_pas` i el text d'ajuda català són al bundle servit |

> **Cap escriptura a la BD de staging en tot el sprint**, tret de la migració (no-op) i la
> seva fila a `django_migrations`.

---

---

## 3bis · ELS CONTROLS DE L'EQUIP (i el que van trobar)

Els quatre rols del `patro-b` s'han passat sobre el tram sencer. **Cap va sortir de buit**, i
les seves troballes són quatre dels deu commits.

| Rol | Veredicte | Què va trobar |
|---|---|---|
| **verificador** | **VERD** | Portes dures netes i abast complert punt per punt. **1 troballa real**: amb el vocabulari caigut, el PATCH de reobrir enviava `metode:'recta'` i **convertia en silenci** un POM de `vora` (o una caiguda) en recta, amb 200 OK i sense que el servidor ho pogués veure —recepta i mètode arribaven coherents entre ells, només que no eren els del POM. → `71941896` |
| **guardia-i18n** | **VERD** | Paritat mesurada per diferència de conjunts en les sis direccions, no per recompte. Interpolacions comparades clau a clau. Va verificar el punt crític —que **tots** els codis i noms d'àncora que el backend pot servir tinguin clau— contra `ANCORES_PER_METODE`. Cap forat. |
| **guardia-ui** | **VETO** → **VERD** | **3 vetos**: (1) el xip «fet» a **2,43:1** per un `opacity: 0.6` sobre text de 10 px; (2) el xip contradeia la NORMA §1 i §3 —fons ple de daurat i radi 4 on toca píndola i filet fi—; (3) `role="radiogroup"` a mitges (sense roving tabindex ni fletxes) i **dues gramàtiques d'ARIA per a la mateixa pell** a la mateixa pantalla. → `f1f0077b`. A la re-revisió, **2 residuals més**: l'`aria-label` sobre un `<span>` pelat que cap lector de pantalla llegeix, i «on soc» quedant-se amb un sol canal. → `05fb6c89` |
| **revisor-diff** | **7 banderes** (2 altes) | La més greu: **un POM ortogonal ancorat no es dibuixava GENS** al canvas. I la segona còpia de la regla de clics que vivia al visor. → `f67ff06b` |

### La bandera que ho valia tot

> El patronista col·loca la caiguda amb tres clics, el valor torna i surt a la llista de
> treball, i **sobre la peça no hi ha res** mentre tots els altres POMs sí que hi són. La
> lectura natural és «no s'ha desat»; el gest natural, tornar-lo a col·locar.

`puntsDeLaMesura` llegia `def.a`/`def.b`, i una recepta ortogonal porta `ref_a`/`ref_b`/`p`.
El sprint hauria arribat a l'Agus amb un mètode que es podia triar, guiar, validar i mesurar
— i que semblava no funcionar.

Pel camí també va sortir que **la regla dels clics tenia dues còpies**: `TallerPatro` ja la
prenia del servidor, però `PatternViewer.jsx` es guardava el seu `mode === 'pinca' ? 3 : 2`,
que és exactament la còpia que aquest tram volia treure del client. Amb tres àncores el
canvas etiquetava els clics **«A, B, B»** i dibuixava una ela `ref_a → ref_b → p` que no és
cap caiguda.

### Dues correccions als informes dels controls

- 🔴 **«La migració 0015 no està aplicada» és FALS**, i el van dir dos rols independentment.
  Tots dos van córrer `showmigrations` **sense context de tenant**, que reporta l'esquema
  `public` — on 0015 legítimament no hi és, perquè `fhort.patterns` és app de TENANT.
  `tenant_command showmigrations --schema=fhort` la dona `[X]`, i `los` també. És exactament
  el parany que el `CLAUDE.md` del repo adverteix («django-tenants pot donar un OK
  enganyós») — aquí el va donar del revés.
- 🟡 El revisor-diff va descriure el forat del reobrir sense vocabulari com a conversió
  silenciosa; el va revisar **abans** de `71941896`, que ja el tancava. `f67ff06b` va més
  enllà i **ni tan sols obre** el POM, amb el motiu.

### La mesura que queda deguda

`ops/qa/qa_auditoria_computats.py` (la passada de `getComputedStyle` sobre la pantalla viva)
**no s'ha corregut**, i el guardià d'UI té raó que sense ella el seu verd es basa en xifres
dels tokens i del codi, no del navegador. Dues raons, i la segona mana:

1. El script **carrega la ruta i prou**, i el `SelectorMetode` només es pinta en mode `'pom'`
   amb més d'un mètode: una correguda d'avui donaria **verd sense haver mesurat el component**.
2. **Entrar al Taller OBRE TASCA.** La correguda no és neutra: escriuria al domini d'un model
   viu. Amb l'sprint acabat i sense que el brief ho demanés, no és una escriptura que em
   toqui fer.

Quan es corri, li calen `FTT_QA_TOKEN` (JWT d'accés cru, 1 h de vida), playwright, i **un pas
nou que entri en mode POM** i triï una caiguda.

## 4 · ELS 4 POMS QUE VAN MOTIVAR EL SPRINT

Ja es poden ancorar. **No s'han ancorat** — ancorar és feina de patronatge sobre material viu:

| POM | Nom | Espec S | Línia de referència proposada | Punt que cau |
|---|---|---|---|---|
| **EK1** | Front neck drop from HPS | 7,7 | els dos HPS del DELANTERO | el punt més baix de l'escot davant |
| **EK2** | Neck drop from HPS | 4,0 | els dos HPS de la peça | el punt més baix de l'escot |
| **E5** | Shoulder drop (HPS → shoulder point) | 2,5 | els dos HPS de l'ESPALDA | el punt d'espatlla a la sisa |
| **SF** | Armhole depth from HPS | 22,0 | els dos HPS | el fons de la sisa |

Els altres **5 forats** de la valoració del 24/08 **no** els tanca aquest sprint, i cap
d'ells necessita el mode nou:

- **S** i **S2** (armhole along seam) volen `metode='vora'`, que el motor **ja** suporta.
  🚩 **Algú els va ancorar avui a les 09:30 amb `metode='recta'`** (PPOM44 i PPOM45): mesuren
  **20,17** i **20,29** cm contra un espec de **22,0** — Δ −1,83 i −1,71, tots dos ben fora de
  tolerància. Les costures ja diuen quant fan de debò **resseguint la vora**: 22,36 (SEW58-B,
  davant) i 22,03 (SEW57-B, esquena). **Amb `vora` en lloc de `recta` quadrarien.** No ho he
  tocat: és el banc de l'Agus.
- **EK**, **E1** i **J** no estan ancorats i prou; `points` + `recta` els serveix.

---

## 5 · EL QUE QUEDA OBERT (anotat, no tocat)

1. 🚨 **LA DECISIÓ DE PATRONATGE** — com es reparteix el delta d'un POM ortogonal entre el punt
   que cau i la línia de referència. Fins que no estigui presa, la caiguda **mesura i no
   gradua**. És el que aquest sprint deixa expressament a taula (§1).
2. 🚩 **Lectura conservadora del punt 3 del brief.** El brief deia «`pom_specs` ha d'acceptar i
   reportar el mode nou **sense problemes**». Ho he llegit com «sense petar / sense caure al
   calaix genèric», **no** com «sense afegir-lo a la llista de `problemes`». El motiu és dur:
   emetre un `POMSpec` de dues adreces fabricat des d'una caiguda hauria fet que la projecció
   separés els dos HPS en silenci, i el brief prohibia expressament prendre aquesta decisió.
   Si l'Agus volia l'altra lectura, **el canvi és una sola branca a
   `adapters.py:604-611`** — però llavors cal decidir abans el punt 1.
3. 🚩 **`drf-spectacular` documenta `metodes/` amb `PatternPOMSerializer`**, que no és la forma
   que torna. Es resoldria amb `@extend_schema`, **que el repo no fa servir enlloc** (0
   ocurrències): introduir-lo per a una sola acció seria estrenar un patró, i hi ha una
   dotzena d'accions al mòdul amb el mateix cas. Anotat, no tocat.
4. 🚩 **Dos vocabularis de `choices` cap al front.** Existeix `/api/v1/vocabulari/`
   (`models_app/vocabulari_views.py:151`), que és la casa canònica del «cap enum al front» i
   serveix `{codi, etiqueta}`. El de mètodes ha anat a `patterns/` perquè (a) el brief deia
   *res fora del motor* i (b) la seva forma és més rica que `{codi, etiqueta}` — hi viatja la
   **gramàtica** (`mode`, `ancores`), que és el que fa que el Taller no hagi de saber res.
   Unificar-los voldria dir eixamplar la forma del genèric: decisió d'arquitectura, no
   d'aquest sprint.
5. 🚩 **`metode='vora'` no s'ha fet servir mai** en tot el 1383, tot i que el motor el suporta i
   el catàleg marca **S** com a `Tirada` (along seam). Ara el selector el fa **visible i
   triable** per primera vegada al Taller — abans no hi havia manera d'escollir-lo des de la
   pantalla, que és probablement per què ningú no l'havia usat.
6. 🚩 **Els motius del rebot no arriben a l'usuari.** El servidor ara dona missatges precisos
   («el punt que cau és una de les àncores de referència: això mesuraria zero»), però el
   `catch` d'`ancorar` (`TallerPatro.jsx:408-411`) els descarta tots i pinta el genèric
   `t('pattern.err_pom')`. Amb un gest nou de tres clics, perdre el motiu és pitjor que amb
   un de dos. **No s'ha tocat** perquè arreglar-ho de debò vol que el backend emeti un CODI
   de rebot (els seus missatges són català monolingüe i ensenyar-los trencaria l'i18n-gate),
   i això és una porta nova, no aquest sprint. L'única excepció que ja existeix
   (`err_pom_duplicate`) ho fa ensumant `non_field_errors`, que no escala.

7. 🚩 **Dos camps `metode` diferents a la mateixa pantalla.** `PatternPOM.metode` (recta ·
   vora · ortogonal — **com s'ancora**) i `fitxa_pom.metode`, que el Taller pinta a la
   targeta ⓘ de cada POM (`ModelPomList.jsx:312`) i que ve de `POMGlobal.line`
   (`patterns/views.py:138`: STRAIGHT · CURVED · ALONG CURVE · ANGLED — **què diu el
   catàleg que és la mesura**). **No xoquen** —són dos camins independents i el sprint no
   n'ha tocat cap— però comparteixen nom a dos pams l'un de l'altre, que és exactament el
   parany que `ftt-nomenclatura-pom-camps` documenta per a `codi_client`/`client_alias`.
   Verificat, no tocat.

8. 🚩 **La BD s'ha mogut sota el sprint.** Entre la valoració del matí (12 POMs ancorats) i
   aquest tram (14) hi ha hagut una altra mà treballant a `dev` i al banc del 1383. Cap
   conflicte de fitxers, però convé saber-ho abans de fer push.

---

## 6 · ELS COMMITS (cap push)

| Hash | Concern |
|---|---|
| `a92be1a9` | model: el mètode ORTOGONAL entra al vocabulari de `PatternPOM` + migració 0015 |
| `199f4b25` | engine: `resoldre()` sap mesurar una caiguda ortogonal |
| `2a02a20f` | adapters: `pom_specs` reconeix la caiguda i diu per què no gradua |
| `487b8469` | api: validació al serializer + `GET pattern-poms/metodes/` |
| `51339ef9` | tests: la caiguda, de la geometria fins a la frontera (25 tests) |
| `e5eebfc9` | taller: selector de mètode + flux de 3 clics guiat + i18n ca/en/es |
| `71941896` | fix: reobrir amb el vocabulari caigut ja no canvia el mètode del POM (**verificador**) |
| `f1f0077b` | fix: els tres vetos del **guardià d'UI** sobre el selector (contrast, forma de xip, ARIA) |
| `f67ff06b` | fix: el visor sap dibuixar una caiguda + les banderes del **revisor-diff** |
| `05fb6c89` | fix: els residuals del **guardià d'UI** i una promesa del validador massa ampla |

**Què ha de fer el CTO:** revisar la cadena amb `git show <hash>`, decidir el punt 1 de §5, i
fer el push des d'SSH.

---

*Informe generat pel tram d'implementació del 24/08/2026. Res d'aquest sprint no ha tocat la
projecció d'escalat, `GradingVersion`, les costures, `segmentar_vora`, G1/G6 ni PROD.*
