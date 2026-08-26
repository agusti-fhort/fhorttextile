# CODA T3 · FAMÍLIES D'INSTÀNCIA I ORDRE CANÒNIC · 2026-08-26

> Fitxer propi i no annex a `IMPLEMENTACIO_FIXOS_FORMACIO_1`: aquella acta ja és a `dev`
> (merge `c8924f32`) i això porta una LLEI, una MIGRACIÓ i una decisió d'Agus enmig. Pesa menys
> obrir-ne un que reobrir aquella.
>
> Substrat: `DIAGNOSI_FORMACIO_2026-08-26.md` §T3 + annex.

## PAS -1 · IDENTITAT, BASE I COORDINACIÓ

| Fet | Valor |
|---|---|
| `hostname` | `fhort-assessment` ✅ |
| `WorkingDirectory` d'`ftt-staging.service` | `/var/www/ftt-staging/backend` ✅ |
| **HEAD de `dev`** | **`c8924f32`** — *«merge: fixos formació 1a tanda»* (el brief deia `c8924f32`; hi coincideix) |
| Worktree | `/var/www/ftt-coda3`, branca **`coda-t3-families`** |
| Fil motor (`ftt-f41`) | worktree a `37339906`, **cap procés viu** (`ps` net) |
| Arbre brut de staging | els 4 aliens de sempre — **intersecció ZERO** amb els fitxers d'aquesta coda |

---

# 🚨 EL CENS BLOQUEJANT DE C2, I LA DECISIÓ D'AGUS

El brief demanava aturar-se **abans d'escriure** si l'ordre nou no reproduïa algun slug viu.
Es va censar primer.

### La consulta (les 12 columnes `instancia` × `public`/`fhort`/`los`)

```sql
SELECT '<sch>' , '<taula>', instancia, count(*) FROM <sch>.<taula>
WHERE instancia LIKE '%-%' GROUP BY instancia            -- × 28 taules, UNION ALL
```

### El resultat: 3 slugs compostos vius, 6 files, i **2 dels 3 canvien**

| slug viu | ordre vell | ordre nou | |
|---|---|---|---|
| `front-left` | `front-left` | `front-left` | IGUAL |
| `extended-right` | `extended-right` | `right-extended` | **CANVIA** |
| `relaxed-right` | `relaxed-right` | `right-relaxed` | **CANVIA** |

**Files** (totes al model **1380 `QA-F1-GARMENT`**, un banc de QA del 17/08, POM 1012 «S»):

| taula | pks | unique |
|---|---|---|
| `models_app_basemeasurement` | 3388 · **3389** · **3390** | `UNIQUE (model_id, pom_id, capa, instancia, garment)` |
| `models_app_measurementchangelog` | 1841 · **1842** · **1843** | cap (és un log) |

⚠️ 3389 i 3390 comparteixen `nom_fitxa` «SR»: són DUES germanes que només distingeix la
instància.

**Radi del dany si s'activés l'ordre nou sense migrar:** la LECTURA no es trenca —
`tramsInstancia` parteix per `-` i cada tram es resol sol, o sigui que l'ordre no hi compta.
Es trenca en **RE-DESAR**: `EditableTable` recompon el slug d'una fila existent → clau nova →
l'upsert no troba la fila → **INSERT en comptes d'UPDATE, amb 200 OK i en silenci**.

### 🔑 LA DECISIÓ (Agus, 26/08): **opció 2 — tot ara + migració de dades**, amb quatre lleis

> 1. La migració ha de cobrir **TOTES** les taules que porten `instancia` (12 per tenant), no
>    només la del diccionari — un slug recompost en una taula i vell en una altra trenca les
>    claus creuades (`GradedSpec`, `PieceFittingLine`…).
> 2. **Guarda de col·lisió**: si el slug recompost ja existeix a la mateixa clau, la migració
>    **avorta i llista, no tria**.
> 3. **Idempotent i amb recompte declarat** (dry-run intern: 4 esperades; si en troba unes
>    altres, para) — perquè la mateixa migració viatjarà al mini-tren i s'aplicarà a PROD via
>    `migrate_schemas` sobre una població que encara no s'ha comptat.

Les quatre estan implementades i provades una a una (v. GATE).

---

# C1 · LA CONSTANT DE FAMÍLIES

**Commit `278c717c`.** `backend/fhort/pom/families.py` (nou).

| # | família | slugs | mirall |
|---:|---|---|---|
| 1 | `PECA` | `front` · `back` | ✅ |
| 2 | `BANDA` | `left` · `right` | ✅ |
| 3 | `VERTICALITAT` | `top` · `bottom` | ✅ |
| 4 | `COSTURA` | `side` · `waistband_seam` | ❌ **no binomial** |
| 5 | `LINIA` | `cf` · `cb` | ✅ |
| Ú | `ESTAT` | `relaxed` · `extended` | ✅ |

**Cap slug orfe:** 12 de 12 amb casa. Abans n'hi havia **6 sense família** (`top`, `bottom`,
`cf`, `cb`, `side`, `waistband_seam`) i un slug sense família era **excloent amb tot** — d'aquí
el símptoma de la formació.

`cf`/`cb` són **família pròpia i NO són peça**: el centre davant és una LÍNIA de la peça, no la
seva cara. Per això `front`+`cf` és legal — és redundant, i **el sistema no fa de policia
semàntic**.

**Els miralls es declaren com a DADA** (`mirall_de`), per al dia que el motor demani girar una
peça o copiar left→right. **Cap operació de gir s'implementa** (fora d'abast, i dit al codi).

### ⚠️ Per què la llei viu a `families.py` i no al model

Les migracions de dades treballen amb models **HISTÒRICS**, que no porten els mètodes de la
classe viva. Si la llei visqués al model, la migració se n'hauria d'escriure una còpia — i **una
còpia de l'ordre canònic és exactament el defecte que aquesta coda tanca**. `MeasurementInstance`
n'és consumidor: `SUBEIXOS`, `familia_de`, `mirall_de`, `composa` hi deleguen.

El nom `SUBEIXOS`/`subeix` es conserva: és el **contracte publicat** a
`GET /api/v1/mesures/diccionari/` i renombrar-lo seria un tram propi.

---

# C2 · L'ORDRE CANÒNIC DETERMINISTA

**Font triada: `dicc.subeixos` (les FAMÍLIES), NO `dicc.eixos`.** El perquè:

* `subeixos` és la llista de famílies **en ordre canònic**, emesa des de `FAMILIES` — que és on
  la llei viu escrita (peça → banda → verticalitat → costura → línia → estat).
* `eixos` és una altra cosa: POSICIÓ i ESTAT, el que agrupa les **columnes** de la taula de
  mesures. Des d'aquesta llei **l'eix ja no decideix res de l'ordre**: cada slug té família i la
  família sola en diu el lloc. Fer-lo servir mantindria **dos nivells d'ordenació on la llei
  només en té un**, i el dia que família i eix no casessin tornaríem a tenir dues respostes.

Abans (`pesCanonic`): `Object.keys(dicc.instancies).indexOf(eix) * 100 + subeixIndex`. Les claus
d'aquell objecte les posa el backend amb `order_by('eix')` — **alfabètic**, `'ESTAT' < 'POSICIO'`.

També s'ha fet **determinista l'emissió** (`identity_views`): les claus de `instancies` surten
per `EIX_CHOICES` i no per l'alfabet. Ja no decideixen res, però un diccionari amb un ordre
accidental és una mina esperant el proper lector que se'l cregui.

### ⚠️ EL FALLBACK A L'EIX, i per què no és decoració

Amb la clau d'exclusió i el pes canònic reduïts a la família sola, **un payload sense `subeix`
—un backend anterior a aquest tram, que és exactament el cas d'un PROD amb el gunicorn ranci—
deixaria totes les píndoles sense clau i els xips es tornarien INERTS**: pitjor que excloents.
`clauExclusio` i `pesCanonic` cauen a l'eix quan no hi ha família. Amb el vocabulari de la casa
això no passa mai (cap slug és orfe des d'avui); passa amb un backend endarrerit o amb una
instància que s'hagi creat un tenant.

*Ho van cantar els nou tests de `instanciaTria.test.js` que corren contra un diccionari SENSE
`subeix` a posta. Sense ells, la regressió hauria passat.*

---

# LA MIGRACIÓ · `pom/0086_ordre_canonic_instancia`

**Va al MATEIX commit que la llei**, i no es poden separar: amb l'ordre nou viu i les files
velles sense tocar hi hauria una finestra en què el sistema escriu claus que no troba.

| Llei d'Agus | Com |
|---|---|
| 1 · totes les taules | La llista surt del **registre de models** (`apps.get_models()` amb camp `instancia`), no escrita a mà: una llista a mà es queda enrere el dia que algú afegeixi la columna a una taula nova |
| 2 · guarda de col·lisió | Si el slug canònic ja el té una altra fila de la **mateixa clau única**, `ColisioDeNormalitzacio` amb la llista. **No tria** |
| 3 · idempotent + recompte | Segona correguda = 0 canvis. El pla es diu **sempre** al log, per schema i per taula |
| 4 · vocabulari forà | Un slug amb algun tram sense família es **SALTA i es diu**: no té ordre canònic i inventar-l'hi seria canviar-li la clau a algú |

**El canari `--esperades`** és de la correguda controlada (`--dry-run --esperades 4`), **no de la
migració**: a PROD la població no s'ha comptat i assertar-hi un número que no sabem seria aturar
el tren per força. El que sí que hi ha sempre és el recompte al log.

### Dos vermells que van costar una volta cadascun

* **`.iterator()` fora** — obre un cursor de servidor amb NOM i el canvi de schema de
  `django_tenants` l'invalida enmig del recorregut (`InvalidCursorName`, mesurat a `public`).
* **`.order_by()` buit** — el `Meta.ordering` d'alguns models afegeix un JOIN a una taula que a
  `public` no existeix (`pom_garmentpommap` → `tasks_garmenttypeitem`). Ordenar aquí no serveix
  de res i costava el tren sencer.
* I un filtre de **taules presents al schema**: `public` en té 4 de 12 (`fhort.pom` viu a SHARED
  **i** TENANT), i sense filtre la migració petava allà per una taula que en aquell schema no ha
  d'existir mai.

### 🚨 LA MIGRACIÓ **NO** S'HA APLICAT A LA BD VIVA DE STAGING

Aplicar-la sense desplegar aquest codi crearia **exactament el desajust que existeix per
evitar** (la BD en canònic, el gunicorn desplegat component en alfabètic). Viatja amb el codi al
mini-tren. El que sí que s'ha corregut és el **dry-run** a les tres schemes:

```
public  canvis=0 colisions=0 saltades=0
fhort   canvis=4 colisions=0 saltades=0      ← el canari d'Agus
   models_app.BaseMeasurement      pk=3389  «extended-right» → «right-extended»
   models_app.BaseMeasurement      pk=3390  «relaxed-right»  → «right-relaxed»
   models_app.MeasurementChangeLog pk=1842  «extended-right» → «right-extended»
   models_app.MeasurementChangeLog pk=1843  «relaxed-right»  → «right-relaxed»
los     canvis=0 colisions=0 saltades=0
```

---

# C3 · EL TEST QUE MENTIA

El fixture de `diccionariMesures.test.js` escrivia `instancies` amb **`POSICIO` primer**, i el
servidor no les emetia així (`order_by('eix')` → ESTAT primer). El test passava en **verd contra
un payload que la porta real no envia mai**, mentre la BD acumulava `extended-right`.

**Ara el fixture porta les claus en l'ordre «dolent» a posta** (ESTAT primer, el pitjor cas) i
l'ordre canònic n'ha de sortir igualment bé: si algú torna a fer dependre la composició de les
claus d'aquell objecte, les assercions cauen. El fixture que mentia passa a ser el guard.

### ✅ VIST VERMELL contra el codi vell

```
not ok 4  - el slug compost va SEMPRE en l'ordre CANÒNIC, no en el del clic
not ok 19 - la clau d'exclusió és LA FAMÍLIA, i prou
not ok 21 - l'ORDRE CANÒNIC SENCER: peça → banda → verticalitat → costura → línia → estat
# tests 24 · pass 21 · fail 3
```

…i 24/24 amb el codi nou. **El mateix es va fer amb el fitxer germà**
(`instanciaTria.test.js`), que portava la mateixa mentida en una segona còpia.

---

# C4 · LA UI DELS XIPS

**No s'ha construït cap UI.** El mecanisme ja hi era i llegeix `subeix` del diccionari; el que
canvia és la DADA que el diccionari publica. El fum ho mesura contra el bundle real.

🚨 **El diccionari del fum NO està escrit a mà**: és el payload REAL que
`GET /api/v1/mesures/diccionari/` emet des del backend nou
(`ops/qa/_diccionari_families.json`, generat contra `fhort`). Amb un stub escrit a ull, el fum
provaria la meva idea del contracte i no el contracte.

| Què | Resultat |
|---|---|
| Front + Left conviuen (peça + banda) | ✅ |
| **Top no apaga Left ni Front** (el símptoma de la formació) | ✅ |
| Side seam s'afegeix sense apagar res | ✅ |
| CF conviu amb Front (la línia no és la peça; redundància legal) | ✅ |
| L'estat es creua amb les cinc famílies de posició | ✅ |
| Les SIS exclusions dins de família (Back↔Front, Right↔Left, Bottom↔Top, Waistband↔Side, CB↔CF, Extended↔Relaxed) | ✅ |
| Les sis famílies conviuen després de substituir-les totes | ✅ |
| El rètol compon en ordre canònic | ✅ |

### ✅ VIST VERMELL contra el diccionari vell (dos sub-eixos, sis orfes): **9 de 21 assercions**

---

# GATE

| Bloc | Resultat |
|---|---|
| `manage.py check` | **no issues** |
| `makemigrations --check` | **No changes detected** (la llei és constant, no columna) |
| `test_families_instancia` + `test_instancies_posicio_v2` (re-acotat) | **Ran 48 · OK** |
| `test_normalitza_instancies` (les 4 lleis d'Agus) | **Ran 11 · OK** |
| Veïns — `test_f_formacio_1` + `test_u2_r2_capa_instancia_api` + normalitza | **Ran 35 · OK** |
| `node --test` · **tot el projecte** (no només els fitxers tocats) | **559 tests · 559 pass · 0 fail** |
| `npx eslint src` (tot) | **0 errors** (274 warnings preexistents) |
| `npx vite build` | ✓ built |
| Fum C4 · xips de famílies | **21 ✓ · 0 ✗** · vist vermell 9/21 amb el diccionari vell |
| Fum F1/F2 de la tanda anterior | intactes (no s'han tocat) |

**Cap suite sencera. Cap correguda simultània.** `FTT_TEST_DB=test_ftt_coda3`.

## RETIRADA · `test_instancies_posicio_v2` — **8 de 27 en vermell**

La llei de dos sub-eixos que aquell fitxer fixava (22-23/08) queda superseded. **Es re-acota,
no s'esborra**: `LATERAL`→`BANDA`, `CARA`→`PECA`, i el test que deia *«una posició sense
sub-eix no es combina amb cap altra»* passa a dir el contrari **amb el motiu escrit** — era
exactament el símptoma de la formació. S'hi afegeixen els miralls i que cap fila surt publicada
sense família.

*El recompte és el mesurat, no l'estimat: una acta pot subcomptar els vermells d'una retirada.*

## 🚨 TRES VERMELLS DEL BANC, no del producte

* **`instancia_exigeix_nom`** — la invariant de BD no admet una germana sense `nom_fitxa`, i el
  banc de la migració no n'hi posava: 10 errors que no tenien res a veure amb el que es volia
  provar.
* **La taula de vocabulari del tenant de test és BUIDA** — i `error_de_combinacio` només jutja
  el que el diccionari declara, o sigui que `left`+`right` sortia **legal** i el test passava en
  verd sense mirar res. **És el mateix mode de fallada que un fixture que menteix** — el que
  aquesta coda existeix per tancar. La sembra és ara part del banc, amb el recompte assertat.
* **Una expectativa meva equivocada**: crear una `BaseMeasurement` amb instància n'escriu TAMBÉ
  una a `MeasurementChangeLog` (el senyal que registra l'escriptura), o sigui que el recompte
  TOTAL de canvis no és un per fila creada. El banc deia «2 != 1» amb el producte funcionant.
  Es compta per model — i de passada això PROVA la llei 1 d'Agus: el registre d'escriptura
  també es normalitza.

## 🚨 I LA SONDA DEL FUM VA NÉIXER MENTINT (com les dues de la tanda anterior)

Buscava els xips per `get_by_role(name=...)`, i l'`aria-label` d'aquestes píndoles és una FRASE
(«Marca aquesta mesura com a Left», `instancia.tip_aquesta`), no l'etiqueta — i l'aria-label
mana sobre el nom accessible. **El fum deia que faltaven els dotze xips quan hi eren tots.**
Ara es localitzen pel TEXT exacte.

## Captures

`ops/qa/captures/` és a `.git/info/exclude` (evidència, no font):
`c4_00_columnat.png` · `c4_01_front_left.png` · `c4_02_sis_families.png` ·
`c4_03_substituides.png`.

---

# FORA D'ABAST (declarat)

* **Operacions de mirall** (gir de peces, còpia left→right) — els miralls es declaren com a
  dada i prou.
* **Res de PROD** — viatja al mini-tren.
* **Cap push.**

## 🚩 QUEDA OBERT

* **La migració s'ha d'aplicar a staging quan es desplegui aquest codi**, no abans. L'ordre
  correcte és: desplegar → migrar. A l'inrevés trenca les escriptures durant la finestra.
* A **PROD** el cens no s'ha fet. La migració el farà i el dirà al log; si hi troba col·lisions,
  **avortarà** i caldrà la decisió d'Agus sobre com fusionar aquelles germanes.
* El nom publicat segueix sent `subeix`/`subeixos` quan el concepte ja es diu **família**.
  Renombrar el contracte és un tram propi.
