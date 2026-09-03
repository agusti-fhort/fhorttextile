# INFORME — CIRCUIT DE PRECEDENTS DE COTES (fitxa tècnica)

**Data:** 24/08/2026 · **Patró A — READ-ONLY.** Cap escriptura, cap fix, cap migració.
**Abast:** flux «Col·loca les cotes que falten» / «3 cotes posades des del precedent» de
l'editor de fitxa tècnica. **Banc:** model **1383** (`TRV-SS27-0001 · 837 VESTIT`), tenant
`fhort` a staging, `.ftt` de la URL **887**.
**Clon llegit:** `/var/www/ftt-staging` (branca `dev`, HEAD `5306df7e`).

---

## 0. VEREDICTE EN UNA LÍNIA

> **Les 3 cotes NO van sortir de cap precedent.** La taula de precedents
> (`models_app.POMPlacement`) té **0 files** als dos tenants: el circuit no ha desat mai res.
> Les 3 cotes són el **repartidor automàtic** (`reparteixCotes`), i van caure a l'esquena perquè
> `superficieDeCotes` tria **la bbox més gran**, i la bbox de l'esquena guanya la del davant per
> **29,8 mm² de 9.250 (0,32 %)** — un marge que **no és de silueta: és de nanses de Bézier**.
> El davant és un `polygon` (0 nanses); l'esquena, un `path` amb corbes (26 de 32 segments amb
> nansa, la més llarga de 20,6 mm). El missatge «posades des del precedent» és **literalment
> fals** i és el que ha dirigit la sospita al lloc equivocat.

---

## 1. D'ON LLEGEIX EL PRECEDENT

### 1.1 La taula

**`models_app.POMPlacement`** — [models.py:1615](../../backend/fhort/models_app/models.py#L1615),
creada per [0062_pomplacement.py](../../backend/fhort/models_app/migrations/0062_pomplacement.py).
Viu al **schema del TENANT**. Penja de **`ItemFitxer`** (el CATÀLEG), no de `Model` ni de
`ModelFitxer`: [models.py:1637](../../backend/fhort/models_app/models.py#L1637) (`CASCADE`).
El vincle al POM és `PROTECT` ([models.py:1639](../../backend/fhort/models_app/models.py#L1639)).

### 1.2 La clau exacta

**Unicitat a BD** — [models.py:1689-1691](../../backend/fhort/models_app/models.py#L1689):

```
UniqueConstraint(item_fitxer, pom, view_slot, capa, instancia)
```

O sigui: **ni `garment_type_item` ni `garment` no hi són**. El `garment_type_item` només
apareix a la **segona passada** de la cascada (el precedent «germana»), i hi entra per
travessia: `item_fitxer__garment_type_item_id`
([pom_placement_views.py:67](../../backend/fhort/models_app/pom_placement_views.py#L67)).
La **peça** (`garment`) està **explícitament fora** de la clau, amb el motiu escrit al codi
([pom_placement_views.py:88-99](../../backend/fhort/models_app/pom_placement_views.py#L88)):
una cota dibuixada sobre un croquis no sap dir de quina prenda és.

**Clau de LECTURA dins la cascada** — [pom_placement_views.py:59-60](../../backend/fhort/models_app/pom_placement_views.py#L59):
`(pom_id, capa, instancia)`, un cop ja filtrat per `view_slot`.

### 1.3 L'endpoint i la cascada

`GET /api/v1/item-fitxers/<item_id>/pom-placements/?view_slot=<slot>&model_id=<id>`
— ruta a [urls.py:216](../../backend/fhort/models_app/urls.py#L216), vista a
[pom_placement_views.py:36](../../backend/fhort/models_app/pom_placement_views.py#L36).

1. **EXACTE** — precedents d'AQUEST `ItemFitxer` ([:63](../../backend/fhort/models_app/pom_placement_views.py#L63)).
2. **GERMANA** — altres `ItemFitxer` del mateix `GarmentTypeItem`, marcats `derivat=True`
   ([:67-69](../../backend/fhort/models_app/pom_placement_views.py#L67)); l'exacte hi guanya
   ([:71-75](../../backend/fhort/models_app/pom_placement_views.py#L71)).
3. Amb `model_id`, es resol el `bm_id` viu contra `BaseMeasurement` filtrant `garment=''`
   (la peça **mare**) ([:100-104](../../backend/fhort/models_app/pom_placement_views.py#L100)).
   Un POM del precedent que el model no té cau a `no_al_model`
   ([:113-116](../../backend/fhort/models_app/pom_placement_views.py#L113)): mai crash.
4. `view_slot` és **obligatori** ([:46-48](../../backend/fhort/models_app/pom_placement_views.py#L46)).

### 1.4 La normalització — **bbox de QUÈ**

Els extrems es desen **0..1 sobre la bounding box de l'OBJECTE SKETCH que la cota anota** —
ni la pàgina ni la silueta ([models.py:1620-1621](../../backend/fhort/models_app/models.py#L1620)).
El model ja avisa que **bbox d'objecte ≠ silueta** i ho traça amb `source_kind`
([models.py:1623-1625](../../backend/fhort/models_app/models.py#L1623)), però l'avís només
parla del cas **ràster** (marges buits dins la imatge).

Qui la calcula, als dos sentits, és **`objectBounds`**
([TechSheetEditor.jsx:616](../../frontend/src/pages/TechSheetEditor.jsx#L616)):

- escriptura: `construirPrecedentCota` ([:6370-6390](../../frontend/src/pages/TechSheetEditor.jsx#L6370))
- lectura: `buildCotaDeProposta` ([:6264-6285](../../frontend/src/pages/TechSheetEditor.jsx#L6264)),
  que desnormalitza sobre la bbox **ACTUAL** del host (si s'ha mogut o redimensionat, la cota hi
  cau bé igualment).

> 🚨 **ANOMALIA A1 — la bbox d'un `path` inclou les NANSES DE BÉZIER, no el traç.**
> [TechSheetEditor.jsx:625-641](../../frontend/src/pages/TechSheetEditor.jsx#L625): per a cada
> segment s'hi afegeixen `p`, `p+in` i `p+out`. Els punts de control d'una corba **cauen fora
> de la corba**. Això vol dir dues coses: (a) la normalització d'un precedent no és sobre la
> figura sinó sobre una capsa inflada de manera **desigual segons com estigui dibuixat** el
> croquis; (b) —i és el que ha passat avui— **decideix qui guanya** a `superficieDeCotes`.
> L'avís del model (1623-1625) diu «ràster»; **el cas vector té el seu propi desviament i no
> està escrit enlloc**.

---

## 2. QUÈ ESCRIU — moure una cota a mà i desar

**Resposta curta: NOMÉS posició de document. El precedent no s'escriu mai sol.**

### 2.1 Cens complet d'escriptors de `POMPlacement`

Un sol camí a tot el backend:

| Camí | file:line |
|---|---|
| `POMPlacement.objects.update_or_create(...)` | [pom_placement_views.py:173-177](../../backend/fhort/models_app/pom_placement_views.py#L173) |

Res més. La IA de visió **no escriu** ([pom_vision_views.py:8-9](../../backend/fhort/models_app/pom_vision_views.py#L8)),
i la sembra `.ai` és **Fase 1, només lectura, cap BD**
([sembra_ai_report.py:1](../../backend/fhort/pom/management/commands/sembra_ai_report.py#L1)).

### 2.2 Qui crida aquell POST, des del front

| Gest de l'usuari | Funció | file:line | Escriu precedent? |
|---|---|---|---|
| Arrossegar/editar la cota + autosave | `PATCH ftt-documents/<id>/` | [ftt_document_views.py:214](../../backend/fhort/models_app/ftt_document_views.py#L214) · [TechSheetEditor.jsx:3838-3844](../../frontend/src/pages/TechSheetEditor.jsx#L3838) | **NO** |
| Botó «Desar com a precedent» (Propietats de la cota) | `desarUnaPrecedent` | [TechSheetEditor.jsx:6399](../../frontend/src/pages/TechSheetEditor.jsx#L6399) · UI [:8340-8348](../../frontend/src/pages/TechSheetEditor.jsx#L8340) | **SÍ** (acte conscient) |
| Acceptar una proposta d'IA | `escriurePrecedentSilent` | [TechSheetEditor.jsx:6411](../../frontend/src/pages/TechSheetEditor.jsx#L6411) | **SÍ** (silenciós) |

**Camí d'escriptura, sencer:**
`construirPrecedentCota` ([:6370](../../frontend/src/pages/TechSheetEditor.jsx#L6370))
→ resol el host sketch **per contenció del punt mig de la cota** ([:6375](../../frontend/src/pages/TechSheetEditor.jsx#L6375))
→ normalitza sobre `objectBounds(host)` ([:6380-6388](../../frontend/src/pages/TechSheetEditor.jsx#L6380))
→ `POST` ([:6402-6404](../../frontend/src/pages/TechSheetEditor.jsx#L6402))
→ gate **CONFIGURE** ([pom_placement_views.py:135-139](../../backend/fhort/models_app/pom_placement_views.py#L135))
→ `update_or_create` ([:173](../../backend/fhort/models_app/pom_placement_views.py#L173)).

El desat porta **batec propi** perquè la fila no té camp `model` i el backend no pot deduir de
quin model és la feina ([TechSheetEditor.jsx:6391-6398](../../frontend/src/pages/TechSheetEditor.jsx#L6391)).

> 🚨 **ANOMALIA A2 — l'escriptura NO pot expressar la clau que la lectura sap llegir.**
> El body que envia el front és `{pom_id, view_slot, x1..y2, label_dx, label_dy, source_kind}`
> ([:6380-6389](../../frontend/src/pages/TechSheetEditor.jsx#L6380)): **no hi viatgen ni `capa`
> ni `instancia`**, i el backend els **clava** a `('exterior', '')`
> ([pom_placement_views.py:173-177](../../backend/fhort/models_app/pom_placement_views.py#L173)).
> Conseqüència: desar com a precedent la cota d'una mesura de **folre** —o de la **sisa
> esquerra**— escriu la fila **sota la clau de l'exterior/instància única**, i **trepitja** el
> precedent que hi hagués. La cascada (que sí que indexa per `(pom, capa, instancia)`,
> [:59-60](../../backend/fhort/models_app/pom_placement_views.py#L59)) el tornarà com si fos el
> de l'exterior. Està **declarat al codi** com a comporta temporal («fins a C4-ins»,
> [models.py:1666-1675](../../backend/fhort/models_app/models.py#L1666)), però les comportes de
> BD ja es van **retirar** a la migració 0078 ([models.py:1699-1705](../../backend/fhort/models_app/models.py#L1699)):
> avui la BD ho **accepta** i qui manté la restricció és **només** aquest literal de la vista.

> 🚨 **ANOMALIA A3 — `label_dx` / `label_dy` s'escriuen i no els llegeix ningú.**
> S'omplen a l'escriptura ([:6386-6387](../../frontend/src/pages/TechSheetEditor.jsx#L6386)) i
> es serveixen a la cascada ([pom_placement_views.py:120](../../backend/fhort/models_app/pom_placement_views.py#L120)),
> però `buildCotaDeProposta` els **descarta a posta** i recalcula l'offset perpendicular
> ([:6281-6283](../../frontend/src/pages/TechSheetEditor.jsx#L6281)). L'arrossegament manual de
> l'etiqueta **no és reutilitzable**: es desa i es perd. Dues columnes de BD sense cap lector.

---

## 3. LA VISTA (`view_slot`)

### 3.1 Com es resol

**No es resol: es DECLARA a mà, i per OBJECTE.**

- És un atribut lliure de l'objecte sketch, escrit pel tècnic a **Propietats de l'objecte**:
  `assignaVista` ([TechSheetEditor.jsx:6218](../../frontend/src/pages/TechSheetEditor.jsx#L6218)),
  UI a [:8313-8325](../../frontend/src/pages/TechSheetEditor.jsx#L8313) (un `<input list>` amb
  datalist `sketch-view-slots` — **suggeriments, no enum**).
- No és enum tancat tampoc a BD: `SlugField(max_length=40)`, canònics `front`/`back`/`detail`
  amb sufix lliure ([models.py:1641-1643](../../backend/fhort/models_app/models.py#L1641)).
- Un objecte entra a F2 **només si té les DUES coses**: `sourceItemFitxer` **i** `viewSlot`
  ([:6225-6228](../../frontend/src/pages/TechSheetEditor.jsx#L6225)). Sense vista, no es demana
  res al backend.

### 3.2 I si l'SVG porta les dues vistes al mateix fitxer?

**El sistema no ho sap i no ho pot saber.** L'importador separa per **ROL D'ESTIL**, mai per
vista: `silueta` / `repunts` / `detall`, decidit per `stroke-dasharray` i `fill`
([TechSheetEditor.jsx:2666-2707](../../frontend/src/pages/TechSheetEditor.jsx#L2666)). Un sol
rol → 1 `path` monolític ([:2696](../../frontend/src/pages/TechSheetEditor.jsx#L2696));
diversos rols → 1 `group kind:'sketch'` ([:2705-2707](../../frontend/src/pages/TechSheetEditor.jsx#L2705)).
**En tots dos casos: UN objecte, UN `viewSlot`, UNA bbox** que abraça davant i esquena alhora.

**Sí: la vista forma part de la clau** del precedent
([models.py:1690](../../backend/fhort/models_app/models.py#L1690)) i és filtre obligatori de la
cascada ([:46-51](../../backend/fhort/models_app/pom_placement_views.py#L46)). Per això un SVG
de dues vistes amb un sol `viewSlot` és **incoherent per construcció**: o bé el tècnic el parteix
a mà (desagrupar / explotar), o bé tots els precedents d'aquell item es normalitzen contra una
capsa que conté les dues figures i cauran **a mig camí entre l'una i l'altra**.

> 🚨 **ANOMALIA A4 — desagrupar o explotar un croquis DESTRUEIX la seva identitat F2, en silenci.**
> `explodeCompoundPath` ([:3294-3308](../../frontend/src/pages/TechSheetEditor.jsx#L3294))
> construeix els objectes nous amb una **llista blanca de claus** (`id, type, layer, x, y,
> rotation, scaleX, scaleY, stroke, fill, strokeWidth, headStart, headEnd, paths`): hi cauen
> `sourceItemFitxer`, `viewSlot`, `garmentId`, `role` i `kind`.
> `ungroupObject` ([:3234-3243](../../frontend/src/pages/TechSheetEditor.jsx#L3234)) puja els
> **fills** amb `globalizeObject`, i la procedència vivia al **grup**, no als fills: també es
> perd. **És justament el gest que cal fer per partir un SVG de dues vistes**, i el gest que hi
> esborra el que faria que la partició servís d'alguna cosa. Verificat al banc: al `.ftt` v23 el
> path `e89faf` porta `role='silueta'`; els 7 fills que en surten a la v24 porten tots
> `role=null` (§4.2).

---

## 4. PER QUÈ LES 3 COTES HAN CAIGUT A L'ESQUENA — rastre concret

### 4.0 Precisió d'identitat: el `.ftt` no és el 887

`ModelFitxer 887` és la **versió 18** del document i **no conté ni croquis ni cap cota** (només
la capçalera i la taula Q8). Cada desat crea una **versió nova**
([ftt_document_views.py:214](../../backend/fhort/models_app/ftt_document_views.py#L214)) i el
front avança el cap a `fttHeadId` ([TechSheetEditor.jsx:3844](../../frontend/src/pages/TechSheetEditor.jsx#L3844))
**sense tocar la URL**, que es queda amb l'id d'obertura. Les 3 cotes viuen a
**`ModelFitxer 895` (versió 25, `is_current=True`)**, `…/2026/08/TRV-SS27-0001_fitxa_eqrat9k.ftt`.

### 4.1 Estat del circuit de precedents al banc

| Fet mesurat | Valor |
|---|---|
| `POMPlacement` a `fhort` | **0 files** |
| `POMPlacement` a `los` | **0 files** |
| `ItemFitxer` a `fhort` | **1** (id 14, `dress_fancy_front.svg`, GTI **30**) |
| `GarmentTypeItem` del model 1383 | **71 · `dress_simple`** |
| `ItemFitxer` del GTI 71 | **cap** |
| Objectes del document amb `sourceItemFitxer` | **cap** |
| Objectes del document amb `viewSlot` | **cap** |

L'SVG del banc va entrar per `ModelFitxer 888` (`837_VESTIT.svg`) amb `derivat_de_item = None`,
i `addModelFitxer` només posa procedència si aquell camp existeix
([TechSheetEditor.jsx:5039](../../frontend/src/pages/TechSheetEditor.jsx#L5039)); l'altra porta,
`importarDelTenant`, la posa quan el fitxer és un `ItemFitxer`
([:6881](../../frontend/src/pages/TechSheetEditor.jsx#L6881)). Cap de les dues s'ha donat.

**→ `propFonts` = ∅ → l'efecte de [:6231-6255](../../frontend/src/pages/TechSheetEditor.jsx#L6231)
ni tan sols arriba a fer el `fetch` → `propostes` = mapa buit.** Era **impossible** que cap de
les 3 cotes vingués d'un precedent.

### 4.2 Cronologia del document (mtimes locals, servidor UTC+2)

| v | id | 24/08 | Objectes sketch |
|---|---|---|---|
| 20-22 | 890-892 | 11:32:58 → 11:33:06 | 1 `group/sketch` (`d2713e`) amb 2 fills |
| 23 | 893 | 11:33:17 | **desagrupat** → `92599a` (`role=detall`) + `e89faf` (`role=silueta`) |
| 24 | 894 | 11:33:22 | **explotat** → `92599a` + **7 paths** solts, tots `role=null` |
| 25 | 895 | 11:33:45 | igual + **3 cotes** (poms 904/906/913 → bm 3359/3360/3361) |

### 4.3 Les 3 cotes, tal com són al disc

```
84dd4d5b  pom=904 bm=3359 "A"  x=193.24026183854443  y= 97.29220450262885  dx=40.984486144681775 dy=0
f2bacb75  pom=906 bm=3360 "B"  x=193.24026183854443  y=125.80453606142771  dx=40.984486144681775 dy=0
c30d2d0c  pom=913 bm=3361 "C"  x=193.24026183854443  y=154.31686762022660  dx=40.984486144681775 dy=0
```

Totes tres: **mateixa x, mateixa longitud, dy=0, y equiespaiades**. Cap porta `viewSlot`, cap
porta `precedentGermana`. **És la signatura de `reparteixCotes`**
([cotesAuto.js:21-37](../../frontend/src/utils/cotesAuto.js#L21)), no la d'un precedent.

### 4.4 Reproducció numèrica exacta

Bboxes reals dels 8 objectes de la pàgina, calculades amb la mateixa fórmula que `objectBounds`
(nanses incloses):

| objecte | bbox (mm) | w × h | **àrea** |
|---|---|---|---|
| `92599a97` (`detall`, els dos colls) | (69,58 · 57,00)–(227,75 · 67,77) | 158,18 × 10,76 | 1.702,3 |
| **`223d9b0a`** (cos **dret** = **ESQUENA**) | (179,58 · 57,92)–(247,89 · 193,69) | 68,31 × 135,77 | **9.274,3** ← guanya |
| `8bdda9d7` (cos **esquerre** = **DAVANT**) | (49,26 · 57,99)–(117,42 · 193,62) | 68,16 × 135,63 | 9.244,5 |
| `f3dc0a77` / `1040b1df` / `6d850eff` / `b75eef8a` (mànigues) | — | 36,94 × ~49,6 | ~1.831 |
| `dead6e4d` (detall) | (78,80 · 67,77)–(87,95 · 88,67) | 9,15 × 20,90 | 191,3 |

`superficieDeCotes` ([cotesAuto.js:42-52](../../frontend/src/utils/cotesAuto.js#L42)) tria la
**més gran** → `223d9b0a`. Aplicant-hi `reparteixCotes(bbox, 3)` amb `AMPLE=0.6`, `MARGE=0.08`
([cotesAuto.js:13-14](../../frontend/src/utils/cotesAuto.js#L13)):

```
(193.24026, 97.29220, 40.98449)
(193.24026, 125.80454, 40.98449)
(193.24026, 154.31687, 40.98449)
```

**Coincidència a l'últim decimal amb el que hi ha al `.ftt`.** El camí és, doncs:
botó «Col·loca les cotes que falten (3)» ([:7624-7633](../../frontend/src/pages/TechSheetEditor.jsx#L7624))
→ `colocarCotes` ([:6328](../../frontend/src/pages/TechSheetEditor.jsx#L6328))
→ `propostes.get(bm.pom_id)` retorna `undefined` per a les tres
→ branca `sensePrecedent` ([:6338-6355](../../frontend/src/pages/TechSheetEditor.jsx#L6338)).

### 4.5 Per què l'esquena i no el davant — **el marge és de nanses, no de dibuix**

Si es mesuren les mateixes dues figures **només pels punts d'ancoratge** (la capsa que un humà
veu):

| objecte | àrea amb nanses | àrea només ancoratges | nº segments | segments amb nansa |
|---|---|---|---|---|
| `223d9b0a` (esquena) | **9.274,3** | 9.229,3 | 32 | **26** (nansa màx. **20,646 mm**) |
| `8bdda9d7` (davant) | 9.244,5 | **9.244,5** | 466 | **0** |

**El davant guanya per silueta (9.244,5 > 9.229,3) i perd per nanses (9.274,3 > 9.244,5).**
El motiu és de **format d'origen**: al `837_VESTIT.svg` el cos de l'esquena és el primer
`<path>` amb corbes de Bézier (32 nodes), i el del davant és un `<polygon>` de 466 punts —
**zero nanses**, per tant zero inflament. `objectBounds` infla l'un i no l'altre, i el
desempat (**0,32 %**) cau del costat equivocat.

> És la **ANOMALIA A1** materialitzada. Amb la mateixa figura exportada d'una altra manera, el
> resultat s'hauria invertit sense que res del document canviés.

### 4.6 I el missatge «3 cotes posades des del precedent»

[TechSheetEditor.jsx:6360](../../frontend/src/pages/TechSheetEditor.jsx#L6360):

```js
setF2Msg(t('tech_sheet.pom_posades', { n: nous.length }))
```

`nous` és **la suma de les dues branques** —precedent i repartidor— i el text és sempre el
mateix: `ca.json:3035` «{{n}} cotes posades des del precedent.» ·
`en.json:3035` «{{n}} callouts placed from the precedent.» (el document declara `lang: "en"`).

> 🚨 **ANOMALIA A5 — el missatge d'èxit ATRIBUEIX AL PRECEDENT una col·locació que no en té cap.**
> El comentari del propi codi diu que són dos camins («PRECEDENT primer […]; la resta,
> repartides sobre la superfície», [:6325-6327](../../frontend/src/pages/TechSheetEditor.jsx#L6325))
> i el comptador els fusiona. Amb `POMPlacement` a **0 files a tot el sistema**, **cap** missatge
> «posades des del precedent» que s'hagi vist mai en aquesta instal·lació ha estat cert. És
> l'anomalia que ha desviat aquesta diagnosi cap al circuit de precedents quan el fet era al
> repartidor.

---

## 5. ANOMALIES — llista amb `file:line`

| # | Anomalia | On |
|---|---|---|
| **A1** | `objectBounds` d'un `path` inclou les **nanses de Bézier**: la bbox de normalització (i el desempat de `superficieDeCotes`) no és la figura. L'avís del model només cobreix el cas ràster. | [TechSheetEditor.jsx:625-641](../../frontend/src/pages/TechSheetEditor.jsx#L625) · [models.py:1623-1625](../../backend/fhort/models_app/models.py#L1623) |
| **A2** | L'escriptura **clava** `capa='exterior'`, `instancia=''` mentre la lectura indexa per la clau completa → el precedent d'una cota de folre o de germana esquerra/dreta **trepitja** el de l'exterior. Les comportes de BD ja es van retirar (mig. 0078): avui només ho reté aquest literal. | [pom_placement_views.py:173-177](../../backend/fhort/models_app/pom_placement_views.py#L173) · [TechSheetEditor.jsx:6380-6389](../../frontend/src/pages/TechSheetEditor.jsx#L6380) · [models.py:1699-1705](../../backend/fhort/models_app/models.py#L1699) |
| **A3** | `label_dx`/`label_dy`: **dues columnes escrites i servides que cap lector consumeix**. L'arrossegament manual de l'etiqueta no es reutilitza mai. | [TechSheetEditor.jsx:6386-6387](../../frontend/src/pages/TechSheetEditor.jsx#L6386) · [:6281-6283](../../frontend/src/pages/TechSheetEditor.jsx#L6281) · [pom_placement_views.py:120](../../backend/fhort/models_app/pom_placement_views.py#L120) |
| **A4** | **Desagrupar / explotar un croquis esborra `sourceItemFitxer`, `viewSlot`, `garmentId`, `role` i `kind`** sense avisar — i és el gest necessari per partir un SVG de dues vistes. | [TechSheetEditor.jsx:3294-3308](../../frontend/src/pages/TechSheetEditor.jsx#L3294) · [:3234-3243](../../frontend/src/pages/TechSheetEditor.jsx#L3234) |
| **A5** | El missatge d'èxit diu «des del precedent» **també** per a les cotes del repartidor automàtic. | [TechSheetEditor.jsx:6360](../../frontend/src/pages/TechSheetEditor.jsx#L6360) · `i18n/ca.json:3035` · `i18n/en.json:3035` |
| **A6** | La procedència de catàleg **només** s'enganxa si el fitxer és un `ItemFitxer` o si un `ModelFitxer` porta `derivat_de_item`. Un SVG pujat al model (el cas normal, i el del banc) **no en té mai** → F2 queda mut sense dir per què: la llista de propostes simplement no apareix. | [TechSheetEditor.jsx:5039](../../frontend/src/pages/TechSheetEditor.jsx#L5039) · [:6881](../../frontend/src/pages/TechSheetEditor.jsx#L6881) · [:6225-6228](../../frontend/src/pages/TechSheetEditor.jsx#L6225) |
| **A7** | L'importador separa per **estil** (`silueta`/`repunts`/`detall`), **mai per vista**: un SVG de dues vistes és sempre **un** objecte amb **un** `viewSlot` i **una** bbox que abraça les dues figures. La vista, però, **és clau del precedent**. | [TechSheetEditor.jsx:2666-2707](../../frontend/src/pages/TechSheetEditor.jsx#L2666) · [models.py:1690](../../backend/fhort/models_app/models.py#L1690) |
| **A8** | La cascada resol `bm_id` **només contra la peça mare** (`garment=''`): un POM que només existeixi en una peça no-mare cau sempre a `no_al_model`. Declarat com a frontera estructural, no com a oblit — i sense data de revisió. | [pom_placement_views.py:88-104](../../backend/fhort/models_app/pom_placement_views.py#L88) |
| **A9** | **Cap test de backend toca `POMPlacement`** (0 fitxers de test el mencionen). L'única cobertura del circuit és `frontend/src/utils/cotesAuto.test.js`, que prova el **repartidor**, no el precedent. | — |

---

## 6. NOTES DE MÈTODE

- Tot llegit del clon `/var/www/ftt-staging` (branca `dev`, HEAD `5306df7e`) i de la BD de
  staging **en lectura** (`schema_context('fhort')` / `('los')`, cap `save`, cap migració).
- Els `.ftt` s'han obert com a ZIP a l'scratchpad de sessió, per `obj.fitxer.path` (mai
  `MEDIA_ROOT + name`); cap fitxer del `media/` s'ha tocat.
- Les àrees i el `reparteixCotes` de §4.4-4.5 s'han **recalculat** amb les mateixes fórmules del
  codi i comparat contra els valors del document: coincidència exacta.
- El davant/esquena s'ha confirmat **rendritzant** l'SVG d'origen: figura esquerra amb escot en
  V i tapeta (davant), figura dreta amb escot rodó net (esquena).
