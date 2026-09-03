# ORDRE FIX NOMENCLATURA M1194 — report d'implementació

> 🛑 **SI ARRIBES AQUÍ AMB UN BRIEF QUE DIU «res d'això s'ha implementat encara: dev acaba a
> `bc130305`», AQUELLA PREMISSA ÉS FALSA.** Mesurat l'01/09: `dev` té **7 commits per damunt** de
> `bc130305` que implementen la Decisió 8 sencera. La re-verificació d'acceptació (12 curls
> contra staging viu, model verge BRW 1361) és a la **§6** d'aquest fitxer. No re-implementis res
> sense llegir-la primer.

> **Patró B · staging (`/var/www/ftt-staging`, branca `dev`) · 2026-09-01**
> 3 commits locals, **cap push**. Cap migració (com el brief preveia).
> Backend desplegat (`systemctl restart ftt-staging`) · frontend desplegat
> (`npm run build` sobre `frontend/dist`, que és el que nginx serveix).

---

## 0 · Abans de res: dues coses que el brief donava per certes i no ho eren

**Els precedents no existeixen al servidor.** `/root/diagnosi_losan/` no hi és, ni
`DIAGNOSI_BUG_NOMENCLATURA_M1194.md` ni `DIAGNOSI_RETIRADA_GUARDA_M1194.md` enlloc del disc
(`find /`). S'ha treballat contra el **codi**, que és la font que mana. Els `fitxer:línia` del
brief s'han verificat un per un abans de tocar res; els desviaments es diuen a §5.

**Dues de les tres peces del COMMIT 3 ja eren construïdes** (v. §4). Es diu, no es
reimplementa.

---

## 1 · Identitat de staging, verificada en fred

| | |
|---|---|
| BD viva | `ftt_staging` a **`127.0.0.1:5433`** (`postgresql@18-main`), usuari `ftt_staging` |
| Tenants | `public` (id 1) · **`fhort` (id 2)** · `los` (id 13) — **no hi ha id 6** |
| Host → schema | `staging.fhorttextile.tech` → **`fhort`** |
| Customer BRW | **`fhort.tasks_customer` id = 7**, «Textiles y Confecciones Brownie SL» |
| Model verge | **1362 `BANC-11`** (customer 7, 0 `BaseMeasurement`) — l'equivalent al 1194 |
| Àlies del cas | `B` → POM **906** · `SF` → POM **1015** (tots dos `DICCIONARI`, customer 7) |

Els altres dos verges de BRW (**1358 `BANC-07`**, **1361 `BANC-10`**) es queden **intactes**
per a la QA d'Agus.

> 🚨 **`/api/` de staging demana el claim `tenant_schema` al JWT.** Un token emès amb
> `RefreshToken.for_user()` pelat torna `401 {"code":"token_not_valid"}` — **indistingible d'un
> token caducat, a posta** (`fhort/auth_jwt.py:79`, per no fer de l'endpoint un oracle
> d'enumeració d'schemas). S'ha d'emetre amb `TenantTokenObtainPairSerializer.get_token(u)` dins
> del `schema_context` que toca. (L'`auth_basic` d'nginx **no** afecta `/api/`: hi té `auth_basic off`.)

---

## 2 · COMMIT 1 · backend — `083b18f5`

`fix(pom): M1194 — la nomenclatura de gravar-pom avisa, ja no barra`

### El defecte

`gravar_pom_view` cridava `colisio_de_codi(model.customer_id, nomen)` **per fila** i, si el
`nom_fitxa` ja era `CustomerPOMAlias` d'un altre POM del client, refusava **la petició sencera**
amb `400 NOMENCLATURA_OCUPADA` — abans d'escriure res.

La pregunta era d'abast **CUSTOMER** a una porta que **no escriu cap àlies**: la
`UNIQUE (customer, client_code)` que aquell guarda protegeix no la pot trencar desar una taula
de mesures. Qui la pot trencar és `create_model_pom_view`, i **allà el guarda es queda**.

### Els canvis

| Fitxer | Què |
|---|---|
| `backend/fhort/pom/nomenclatura.py` | **+`avisos_de_nomenclatura(files)`** — pura, sense BD. Agrupa pels **quatre** camps de l'àmbit (`garment, capa, instancia, nom_fitxa`), compara el nom en `casefold` (mateix criteri que l'`iexact` d'`alies_del_codi`) i només avisa amb **≥2 `pom_id` diferents**. |
| `backend/fhort/models_app/views.py` | Fora la crida a `colisio_de_codi` i fora el `return 400`. La recollida per fila fa servir els eixos **ja normalitzats per `_identitat_de_mesura`** — els mateixos amb què s'escriurà. El 200 porta `avisos_nomenclatura`, **sempre present**. |
| `backend/fhort/models_app/test_avisos_nomenclatura_m1194.py` | **Nou.** 7 casos purs + 8 contra la BD. |
| `backend/fhort/models_app/test_f_formacio_1.py` | Retirats els **5** tests de F3 que provaven el 400 d'aquesta porta, amb nota segellada. La **PART 1** (la frase del refús) es queda: la serveix `create_model_pom_view`. |

**No s'han tocat**: `wizard_views.py:862` (pom-propi) ni `set_measurements_view`.
El cens de cridadors de `colisio_de_codi` en donava exactament **dos**, i només se n'ha retirat un.

### Dues decisions que val la pena que constin

1. **La referència de fila és l'índex del payload, no `ordre`.** El brief deia «`ordre` és mort:
   ignora'l» — i té raó que el client no l'envia, però des del 09/08 **el servidor sí que
   l'escriu** (`enumerate` sobre `prepared`: la posició a la llista ÉS l'ordre). Fer servir
   `m.get('ordre')` hauria donat `None` a cada avís.
2. **L'agrupació fa servir la capa JA normalitzada (`'exterior'`), no la crua.** El brief avisava
   contra `clau_mesura` perquè hi posa `'exterior'`; el perill real és **barrejar** files crues i
   normalitzades. Normalitzar-les **totes** pel punt únic que després escriu és el que garanteix
   que cada avís es correspongui amb una fila que existeix a la BD.

### Verificació — curls dirigits, servei reiniciat abans

Model **1362** (`BANC-11`, BRW). *(Ha calgut crear-li la `ModelTask` `pom` — `id 701`, `Pending` —:
no en tenia cap i `gravar-pom` l'exigeix. És muntatge de banc sobre un model `BANC-*`.)*

| | Cas | Resultat |
|---|---|---|
| **A** | `«B»` (àlies BRW del POM 906) sobre el POM **904** | `200` · `created:1` · `avisos:[]` — **abans: 400** |
| **B** | `«SF»` (àlies del POM 1015) sobre el POM **907** | `200` · desada · `avisos:[]` — **abans: 400** |
| **C** | `«X1»` + `«x1»`, POMs 904/907, mateix àmbit | `200` · **`updated:2`** · **1 avís** `{poms:[904,907], files:[0,1]}` |
| **D** | mateix nom amb `garment:"02"` | `200` · `avisos:[]` — **l'àmbit separa** |
| **E** | `«J1»`, ja usat al model BRW **1320** | `200` · `avisos:[]` — **entre models, lliure** |

Les tres files de C i D **comprovades a la BD**: `3394 (904,'X1')`, `3395 (907,'x1')`,
`3396 (907,'X1',garment='02')`, totes `is_active`. Cap error de `manage.py check`.

---

## 3 · COMMIT 2 · frontend — `60abe62a`

`feat(mesures): l'homonímia de nomenclatura es pinta, ja no barra`

- **`MeasuresEntryPanel`** — mort el camí bloquejant: fora l'estat `colisions`, fora la branca
  `codi === 'NOMENCLATURA_OCUPADA'` de `confirmGravarPom` i fora el bloc vermell del modal. El
  confirm de Gravar torna a ser un **confirm simple** (o l'advertència de resembra). Al seu lloc,
  una **banda de resum** amb quants àmbits i quins noms, tancable amb la ✕, que **mor sola al
  desat següent**. Banda i no modal: no hi ha cap gest a demanar, el desat ja ha passat.
- **`utils/avisosNomenclatura.js`** — mòdul **pur**, sense dependències (ni i18n), que retroba
  cada avís amb la seva fila.
- **`EditableTable`** — **segona** ranura sota la cel·la de nomenclatura.

### 🚨 Les dues coses que aquest commit existeix per no fer malament

**1 · La capa s'ha de normalitzar als DOS costats.** El backend serveix l'àmbit amb `'exterior'`
resolt i una fila de pantalla la pot dur buida. Comparar-les crues faria que l'avís **no trobés
mai la seva fila**: es desaria l'ambigüitat i no la cantaria ningú — pitjor que cap avís, perquè
fa creure que s'ha mirat. El banc `node --test` (8 casos) **s'ha vist VERMELL** amb la
normalització sabotejada (`not ok 3 - 🚨 LA CAPA BUIDA DE LA FILA ÉS LA «exterior» DE L'AVÍS`)
abans de donar-lo per bo.

**2 · Un avís no es pinta com un refús.** La cel·la ja té una ranura **vermella** (`refus`,
Decisió 7) per al 409, que **barra**. L'avís **descriu** una fila que ja és a la BD. Dues ranures,
dos colors, dos rols ARIA: taronja de marca de dada (`--warn-state`/`--warn-ink`, mesurat AA al
propi `index.css`) i `role="status"`, no `alert`. *Pintar dues lleis diferents amb la mateixa
gramàtica és el mode de fallada que aquest projecte ja ha pagat una vegada.*

**i18n**: 4 claus a ca/en/es, paritat verificada per script. Retirades `colisio_title` i
`colisio_pendent`, **òrfenes** des que el bloc vermell ha marxat (censat sobre `src/`).

---

## 4 · COMMIT 3 · frontend — `e03f0b25`

`feat(mesures): la pantalla d'entrada explica les DUES lleis de nomenclatura`

### ⚠️ Dues de les tres peces del brief JA ERAN CONSTRUÏDES

| Peça del brief | Estat real | On |
|---|---|---|
| «fes la nomenclatura de cada fila EDITABLE (és el que avui no deixava)» | **JA HO ERA** — `NomenInput`, camp sempre obert | `EditableTable.jsx:1303` |
| «fes VIATJAR (garment, capa, instancia) al payload» | **JA HI VIATJAVEN**, amb la identitat crua i no `clau_mesura` | `utils/payloadMesures.js:57-63` (SET-2/T7-B6, 12/08) |
| «explica les DUES lleis» | **construït avui** | `MeasuresEntryPanel.jsx` |

Mesurat, no deduït: `construeixPayload` emet els tres camps (executat), `payloadMesures.test.js`
13/13 verd, i **el curl D del commit 1** prova que el backend els honora de punta a punta.

El que **avui no deixava** era el `400` del commit 1 — ja retirat.

### El que s'ha construït

Nota **neutra i permanent** a dalt de la taula (no és un avís: no hi ha res que vagi malament, és
el mapa) que contrasta els dos actes: **anomenar una fila** (lliure per model, avís dins la peça)
vs **crear un POM nou de client** (pel cercador del peu, i allà el codi sí que ha de ser únic).
Va al capdamunt i no a un tooltip de la cel·la **perquè la segona llei no viu a la cel·la**: viu
al cercador del peu de taula, i la frase s'ha de poder llegir veient totes dues portes alhora.
`guardia-ui`: tokens (cap hex), icona Tabler outline en l'idioma del fitxer, IBM Plex Mono global.

---

## 5 · Verificació — què s'ha mesurat i què NO

| Control | Resultat |
|---|---|
| `manage.py check` | **net** (0 issues) |
| `npm run build` | **net** |
| `npx eslint` (3 fitxers tocats) | **0 errors** · 12 avisos = **els mateixos 12 que a HEAD** (mesurat amb `stash`) |
| `node --test avisosNomenclatura.test.js` | **8/8**, i **vist vermell** amb sabotatge |
| `node --test payloadMesures.test.js` | 13/13 (no tocat; confirma la peça «ja construïda») |
| `avisos_de_nomenclatura` pura | 6 casos executats en fred abans de cablejar-la |
| Curls dirigits `gravar-pom` | **5/5** (§2) |
| `dist` desplegat | `avisos_nomenclatura`, `avis_homonimia`, `llei_bateig_titol` **PRESENTS** · `NOMENCLATURA_OCUPADA` **absent** |

**No verificat**: els tests de Django **s'han escrit i no executat** (prohibit llançar suites
sense OK d'Agus) i **no hi ha hagut smoke de navegador** — la verificació de pantalla és
build + eslint + la mesura del `dist`. La correspondència avís↔fila està provada al banc pur,
no amb el DOM real.

---

## 6 · 🚩 UNA CONTRADICCIÓ QUE NO ENTRA EN AQUESTS TRES COMMITS

**La llei nova i la porta veïna diuen coses diferents, i la porta veïna és a la MATEIXA pantalla.**

La Decisió 8 diu: *dins model, `(garment,capa,instancia,nom_fitxa)` amb POMs diferents → DESAR +
avisar, **MAI bloquejar***.

`PATCH base-measurements/<id>/noms/` (`views.py:4185-4195`, la «porta única» de la **Decisió 7**)
fa exactament el contrari: `colisio_de_nomenclatura` → **`409`, i no desa**. I divergeix en tres
punts alhora:

1. **Barra** on la Decisió 8 diu avisar.
2. L'àmbit són **TRES** camps (`model, garment, capa`) — **no mira `instancia`**.
3. **No comprova que el POM sigui diferent**: dues files del mateix POM també es refusen.

**És reachable des d'aquesta mateixa pantalla.** `EditableTable.handleCellChange:283` desvia
`nom_fitxa` cap a aquell PATCH **sempre que la fila ja estigui desada** (`id` no `tmp-`). O sigui:
el tècnic grava dues files homònimes (200 + avís, com toca), intenta reanomenar-ne una des de la
taula → **409, no desa**. El carreró de M1194, mogut a la porta del costat.

**No s'ha tocat**, i per què: el brief acota els «no tocar» a `pom-propi` i `set-measurements` i
no menciona aquesta porta; retirar-hi el bloqueig seria desfer feina de la Decisió 7 acabada de
construir (`bc130305`), i **quina de les dues decisions mana sobre aquell endpoint és una
decisió d'Agus, no meva**. La recomanació, si es vol tancar: alinear-la amb la Decisió 8
(avís + `200`, àmbit de **quatre** camps, i només quan el POM difereix), un commit propi.

---

## 7 · Rastre

```
e03f0b25  feat(mesures): la pantalla d'entrada explica les DUES lleis de nomenclatura
60abe62a  feat(mesures): l'homonímia de nomenclatura es pinta, ja no barra
083b18f5  fix(pom): M1194 — la nomenclatura de gravar-pom avisa, ja no barra
```

11 fitxers · +657 / −139. **Cap push** · `git add` amb pathspec explícit als tres (l'índex era
compartit: hi havia feina bruta d'altres sessions al working tree, cap de la qual ha entrat).

**Escriptures al domini fetes per la QA** (totes al banc `BANC-11`, model **1362**): `ModelTask`
`pom` **id 701** creada · `BaseMeasurement` **3394 · 3395 · 3396** · la tasca ha quedat
`InProgress` (`gravar-pom` obre, mai tanca). Models **1358** i **1361** intactes.

---
---

# COMMIT 4 — la porta 4185, alineada amb la Decisió 8

> **2026-09-01, mateixa sessió.** 2 commits més (`05e429e8` backend · `a4b52cb8` frontend),
> **cap push**. Cap migració. Backend reiniciat · frontend rebuildat sobre `frontend/dist`.
> Tanca la 🚩 de la §6 d'aquest mateix report.

---

## 4.0 · PAS 0 · transcripció del codi fresc (abans de tocar res)

`git rev-parse --abbrev-ref HEAD` → **`dev`** · els 3 commits del sprint hi són
(`e03f0b25`, `60abe62a`, `083b18f5`) sobre `bc130305` (merge de la D7).

### El veredicte actual — `views.py:4185-4195`

```python
if 'nom_fitxa' in canvis and canvis['nom_fitxa'] != bm.nom_fitxa:
    germana, _etiqueta, context = colisio_de_nomenclatura(bm, canvis['nom_fitxa'])
    if germana is not None:
        return Response({
            'error': frase_de_colisio_nomenclatura(canvis['nom_fitxa'], context),
            'codi': 'NOMENCLATURA_DUPLICADA',
            'conflicte': context,          # {nom_fitxa, fila_id, pom_nom, pom_codi,
        }, status=409)                     #  instancia, garment}
```

**`409` i `return` abans de l'escriptura**: no es desava res, ni el `nom_fitxa` ni els dos
noms llargs que viatgessin al mateix body.

### L'àmbit literal — `nomenclatura.py:477`

```python
BaseMeasurement.objects
    .filter(model_id=bm.model_id, garment=bm.garment or '', capa=bm.capa or '',
            nom_fitxa__iexact=codi)
    .exclude(pk=bm.pk)
```

**Confirmat: TRES camps** (`model` + `garment` + `capa`), **sense `instancia`**.
**Confirmat: NO comprova que el POM sigui diferent** — qualsevol germana amb el codi xoca.

🚨 **I no era un oblit.** El comentari de la D7 que hi havia al damunt ho argumentava:

> «`instancia` — **a posta**: dues instàncies del mateix POM a la mateixa peça i capa (la sisa
> dreta i l'esquerra) SÓN el cas que ha de tenir nomenclatures diferents. Deixar-la fora de
> l'àmbit és el que fa que 'AH' i 'AH' a dues instàncies germanes **es refusi**.»

### Cridadors

`grep` sobre tot `backend/` (fora `venv/`): `colisio_de_nomenclatura` i
`frase_de_colisio_nomenclatura` **només** les crida `views.py:4188-4193`.
**Cap tercer cridador → no s'atura.**

### El desviament del front

`EditableTable.handleCellChange:283` confirmat: tota edició de `nom_fitxa` d'una fila **ja
desada** (`id` que no comença per `tmp-`) va a `handleBateig` → `baseMeasurements.setNoms` →
porta 4185. Les files `tmp-` es queden al buffer i van pel desat en bloc.
El 409 el consumia `handleBateig:404-409` → `setRefusNomen` → ranura **vermella** sota la
cel·la, amb l'edició **no desada**.

---

## 4.1 · 🚨 EL CENS QUE CANVIA LA LECTURA DEL TRAM

Abans de tocar res, mesurat sobre `fhort` viu — totes les parelles de files actives que
comparteixen àmbit-de-3-camps i `nom_fitxa`:

| eix | POM | veredicte | parelles |
|---|---|---|---|
| instància DIFERENT | **MATEIX** pom | D7: xoca (409) → **D8: MUT** | **4** |
| *(qualsevol altra combinació)* | | | **0** |

**Les úniques 4 parelles vives de `fhort` són exactament el cas que la D7 volia vigilar**
(bm 3389/3390 `SR`, 2288/2289 i 2230/2231 `J1`, 3386/3387 `B` — el mateix POM en dues
instàncies). I **no n'hi ha cap** de «dos POMs diferents amb el mateix nom», que és l'únic cas
que la D8 avisa.

Dit d'una altra manera: **sobre la població d'avui, aquest commit no encén cap avís nou; només
desbloqueja les 4 parelles llegades.** El que canvia no és el present, és el que el sistema
deixarà de notar a partir d'ara.

⚠️ **I `instancia_exigeix_nom` no ho cobreix.** Verificat viu a la BD:
`CHECK (NOT (instancia > '' AND nom_fitxa = ''))` — demana que una fila amb instància tingui
**UN** nom, no que en tingui un de **DIFERENT**. Amb el commit 4, la sisa dreta i l'esquerra
poden tornar a dir-se totes dues `AH` i **cap capa del sistema ho dirà**.

Consta a tres llocs perquè no es perdi: la nota d'`avisos_de_rebateig`, el cos del commit, i
`test_f2_D8_el_mateix_POM_en_una_ALTRA_instancia_no_avisa`.

---

## 4.2 · COMMIT 4a · backend — `05e429e8`

`fix(pom): la porta del rebateig avisa, ja no barra (409 → 200 + avís)`

| Fitxer | Què |
|---|---|
| `pom/nomenclatura.py` | **−`colisio_de_nomenclatura`** i **−`frase_de_colisio_nomenclatura`** (sense cap altre cridador → se'n van senceres, amb nota segellada). **+`avisos_de_rebateig(bm, codi)`**: NOMÉS la consulta que converteix la fila desada i el codi nou en la llista que **`avisos_de_nomenclatura` (commit 1)** sap llegir. |
| `models_app/views.py` | El `409` passa a ser `avisos = avisos_de_rebateig(...)`; l'escriptura procedeix sempre; el 200 porta **`avisos_nomenclatura`**, sempre present. |
| `test_d7_nomenclatura.py` | `UnicitatTest` re-acotada: **5 → 10** casos. Els 2 del 409 canvien de veredicte, no s'esborren. Nota a la capçalera del fitxer. |

**El criteri no es duplica**: àmbit de 4 camps, `casefold` i «≥2 POMs» viuen **en un sol lloc**
(`avisos_de_nomenclatura`), i les dues portes hi passen. Era el punt del tram.

### 🔑 La 3a exigència del brief és ESTRUCTURAL aquí, no una branca

`UNIQUE (model_id, pom_id, capa, instancia, garment)` (verificat a `pg_indexes`) garanteix com a
molt **una fila per POM dins de cada àmbit de quatre camps**. Per tant **tota germana que
`avisos_de_rebateig` pugui trobar té per força un POM diferent**, i la condició «només si el POM
difereix» no es pot arribar a exercir en aquesta porta. A `gravar-pom` **sí** que fa feina: allà
el payload pot dur dues entrades del mateix POM abans que cap índex hi digui res (i té test
propi des del commit 1).

Per això el test que hi correspon prova **la invariant** i no la branca
(`test_f2_D8_el_mateix_POM_al_mateix_ambit_NO_POT_EXISTIR`, amb `assertRaises(IntegrityError)`):
el dia que algú relaxi l'índex, cau aquell test i la condició passarà a fer feina també aquí.

> ℹ️ El brief demanava el camp de resposta amb el nom `avisos_de_nomenclatura`. S'ha fet servir
> **`avisos_nomenclatura`**, que és el que el commit 1 ja serveix a `gravar-pom`
> (`avisos_de_nomenclatura` n'és la **funció**). Mana la intenció explícita del brief —«perquè
> el front el consumeixi igual»—, que amb l'altre nom no es compliria.

### Els 4 curls (banc 1362 `BANC-11`, BRW · servei reiniciat abans)

Banc: `3394` (POM 904, `J1`) i `3395` (POM 907, `WA`), mare · exterior · sense instància.

| | Cas | Resposta | BD |
|---|---|---|---|
| **F1** | `3395` → `«J1»`, mateix àmbit, **POM diferent** | `200` · 1 avís `{poms:[907,904], files:[3395,3394]}` | `nom_fitxa=J1` **DESAT** |
| **F2** | el mateix amb `3394 left` / `3395 right` | `200` · **cap avís** | `nom_fitxa=J1` desat |
| **F3** | re-desar `3395` amb el `«J1»` que **ja té** | `200` · cap avís | el nom llarg s'hi desa |
| **F4** | `3395` → un nom **lliure** | `200` · cap avís | `nom_fitxa=LLIURE9` desat |

**F1 i F2 eren tots dos `409` + cap escriptura sota la D7.** F1 pel motiu que la D8 manté
(dos POMs), F2 pel motiu que la D8 retira (l'àmbit de 3 camps ignorava la instància).

---

## 4.3 · COMMIT 4b · frontend — `a4b52cb8`

`feat(mesures): el rebateig fila a fila pinta l'avís, i el refús vermell se'n va`

**Calia tocar-lo**: `handleBateig` catch-ejava el 409 i encenia la ranura **vermella**
(`refusNomen`). Aquell 409 ja no arriba mai, o sigui que sense canvi el rebateig hauria quedat
**mut** — desant una homonímia sense dir-ho.

- `handleBateig` llegeix el `200` i en treu `avisos_nomenclatura`; el pinta **la MATEIXA
  ranura** del commit 2. L'edició es confirma sempre.
- ⚠️ **Es guarda per `bmId`, no com una llista plana.** Un rebateig posterior de la mateixa fila
  ha de SUBSTITUIR el que aquella fila deia abans; amb una llista que només creixés, un avís
  resolt no marxaria mai. `null` esborra la marca.
- Les **dues fonts** —desat en bloc (per prop) i rebateig fila a fila (estat local)— s'uneixen
  abans de pintar: qui decideix si un avís parla d'una fila és sempre `avisDeLaFila`.
- **Retirats amb el 409**: `refusNomen`, la prop `refus` de `SortableRow`, la ranura vermella i
  la clau i18n `editable_table.nomenclatura_duplicada` (òrfena, censada sobre `src/`).
  **Cap string nou** — és el que fa que les dues portes es llegeixin igual.

🚨 **Actualitzada la capçalera d'`utils/avisosNomenclatura.js`**, que argumentava «són dues
ranures i dos colors a posta» contra una ranura que aquest commit esborra. La distinció hi
queda escrita però **datada**: un comentari que descriu un mecanisme retirat és la trampa que
aquest projecte segueix pagant.

---

## 4.4 · Verificació

| Control | Resultat |
|---|---|
| `manage.py check` | **net** |
| `npm run build` | **net** |
| `npx eslint` (3 fitxers) | **0 errors** · 12 avisos = **els mateixos 12 que a HEAD** (mesurat amb `stash`) |
| `node --test avisosNomenclatura.test.js` | **8/8** |
| Curls F1-F4 | **4/4**, amb la BD comprovada després de cadascun |
| `dist` desplegat | `avisos_nomenclatura` i `avis_homonimia` **presents** · `NOMENCLATURA_DUPLICADA` i `nomenclatura_duplicada` **absents** |
| Backend desplegat | `PATCH …/noms/` retorna `avisos_nomenclatura` |

**No verificat**: tests de Django **escrits i no executats** (10 casos a `UnicitatTest`), i
**cap smoke de navegador**.

---

## 4.5 · 🚩 El que queda obert (anotat, no tocat)

1. **La vigilància que la D7 feia i la D8 no fa.** Dues instàncies del mateix POM amb el mateix
   `nom_fitxa` (la sisa dreta i l'esquerra totes dues `AH`) ara són **mudes a tot arreu**, i
   `instancia_exigeix_nom` no ho cobreix. El `TechSheetEditor` resol el lligam fletxa↔fila **pel
   TEXT** de la nomenclatura i el seu comentari declara el supòsit «curts i únics dins un
   model»: aquell supòsit torna a ser «cert per costum». Si es vol recuperar, la forma que la D8
   permet és **un avís PROPI d'una altra família** (mateix POM · àmbit de 3 camps · instàncies
   diferents), mai tornant a tancar la porta. **Decisió d'Agus.**

2. **Les 4 parelles llegades segueixen vives** (bm 3389/3390, 2288/2289, 2230/2231, 3386/3387).
   Ja no molesten ningú, però tampoc no s'han netejat, i la constraint de BD que la D7 esperava
   poder posar algun dia ara no tindria cap llei que la justifiqués.

3. **Un avís pot nomenar una fila INACTIVA.** `avisos_de_rebateig` no filtra `is_active`
   (fidel al codi que substitueix). Una germana podada que porti el codi encendria un avís
   sobre una fila que la pantalla no pinta: el resum diria un nom sense cap fila marcada.
   Cap cas viu avui; un `is_active=True` al filtre ho tancaria. **Fora d'abast, s'anota.**

---

## 4.6 · Rastre

```
a4b52cb8  feat(mesures): el rebateig fila a fila pinta l'avís, i el refús vermell se'n va
05e429e8  fix(pom): la porta del rebateig avisa, ja no barra (409 → 200 + avís)
```

Sprint sencer: **5 commits**, cap push, `git add` amb pathspec explícit a tots.

**Escriptures al domini fetes pels curls F1-F4** (banc `BANC-11`, model 1362): `nom_fitxa` de
`3395` mogut a `LLIURE9` amb `nom_canonic_model='Prova F3'` · `3394` amb `instancia='left'` ·
`3395` amb `instancia='right'` · fila **3398** creada (POM 907, `left`, `ZZZ9`) i **no
esborrable** (el `MeasurementChangeLog` és append-only i la reté). El banc queda així; **1358**
i **1361** segueixen verges.

---
---

# COMMIT 5 — les germanes homònimes: la vigilància de la D7, recuperada com a avís

> **2026-09-01, mateixa sessió.** 2 commits més (`441a4d31` backend · `2cdb0705` frontend),
> **cap push**. Cap migració. Backend reiniciat · frontend rebuildat.
> Tanca el punt **1** de la §4.5 d'aquest report.

---

## 5.0 · PAS 0 · les dues funcions existents, transcrites (i NO tocades)

### `avisos_de_nomenclatura(files)` — el jutge de l'homonímia real

```python
grups = {}
for f in files or []:
    nom = _net(f.get('nom_fitxa'))
    if not nom:
        continue
    clau = (f.get('garment') or '', f.get('capa') or '', f.get('instancia') or '',
            nom.casefold())
    ...
    pom_id = f.get('pom_id')
    if pom_id is not None and pom_id not in g['poms']:
        g['poms'].append(pom_id)
    g['files'].append(f.get('ref'))
return [g for g in grups.values() if len(g['poms']) > 1]
```

**Criteri literal**: clau de **QUATRE** camps `(garment, capa, instancia, nom_fitxa.casefold())`
· emet **si i només si `len(poms) > 1`** · les files sense nom no entren mai.
Forma: `{garment, capa, instancia, nom_fitxa, poms[], files[]}`.

### `avisos_de_rebateig(bm, codi)` — l'adaptador de consulta

```python
ambit = {'garment': bm.garment or '', 'capa': bm.capa or '',
         'instancia': bm.instancia or ''}
germanes = (BaseMeasurement.objects
            .filter(model_id=bm.model_id, nom_fitxa__iexact=codi, **ambit)
            .exclude(pk=bm.pk).order_by('ordre', 'pk'))
files = [{'ref': bm.pk, 'pom_id': bm.pom_id, 'nom_fitxa': codi, **ambit}]
files += [{'ref': g.pk, 'pom_id': g.pom_id, 'nom_fitxa': g.nom_fitxa, **ambit} for g in germanes]
return avisos_de_nomenclatura(files)
```

**Àmbit de consulta de QUATRE camps** · jutja el codi **nou** · `ref` = PK · delega el veredicte.

✅ **Cap de les dues s'ha modificat en aquest commit** (`git diff` ho confirma: només línies
afegides al final del fitxer). No ha calgut cap aturada.

---

## 5.1 · COMMIT 5a · backend — `441a4d31`

### Les dues famílies, i per què no comparteixen cos

| | homonímia real | germanes homònimes |
|---|---|---|
| clau | `(garment, capa, **instancia**, nom)` | `(garment, capa, nom)` |
| condició | **≥2 POMs** | **≥2 instàncies** |
| POM | decisiu | **indiferent** |
| pregunta | dues mesures DIFERENTS es diuen igual | la MATEIXA mesura es diu igual a dues instàncies |
| sortida | quin dels dos noms canvia | val la pena aquesta instància |
| camp | `avisos_nomenclatura` | `avisos_germanes` |

**Dues funcions llegibles i no una amb un flag**: el flag que decidís família seria exactament
el lloc on tornarien a confondre's. `germanes_homonimes(files)` menja **la mateixa llista** que
l'altre jutge —a posta: els dos han de poder mirar la mateixa taula i respondre coses diferents.

**La forma és germana però no idèntica, i la diferència és honesta**: `instancies` en **plural**
i sense `instancia` en singular, perquè el grup **travessa** l'eix en comptes de viure-hi dins.

⚠️ **La instància buida compta com una més.** Una fila sense instància i una de `left` que es
diguin totes dues «AH» són dues línies indistingibles al paper igual que `left`/`right` — i és el
cas més fàcil de fabricar (afegir una germana a una fila que no en tenia).

`germanes_de_rebateig(bm, codi)` és la bessona de l'adaptador, amb **l'àmbit de consulta de TRES
camps**: és el mateix àmbit que la D7 feia servir per refusar; el que ha canviat és **què se'n fa**.

### Els curls (banc 1362 `BANC-11`, BRW · servei reiniciat abans)

| | Cas | `avisos_germanes` | `avisos_nomenclatura` |
|---|---|---|---|
| **G1** | `gravar` · **mateix POM** (904) · `left`/`right` · «AH» | **1** | 0 |
| **G2** | `gravar` · **POM diferent** (904/907) · `left`/`right` · «AH» | **1** | **0** |
| **G3** | `gravar` · mateixa instància · POM diferent · «AH» | 0 | **1** |
| **G4** | `gravar` · germanes amb noms **diferents** | 0 | 0 |
| **G5** | `rebateig` · 3395 (`right`) → «AH» que 3394 (`left`) ja té | **1** | 0 |
| **G6** | `rebateig` · mateixa instància, dos POMs | **1** | **1** |

**G2 és la que separa les famílies**, i respon la pregunta que el brief demanava documentar:
surt **només germanes**. Dos POMs, sí — però la instància **difereix**, i l'homonímia real
agrupa per un àmbit que inclou la instància: les dues files cauen en **grups diferents** i
`len(poms) > 1` no s'arriba a complir a cap dels dos. Les famílies són independents **per
construcció de la clau**, no per una condició afegida.

**G6 ensenya que poden encendre's alhora** sobre subconjunts diferents del mateix desat:
germanes sobre `''`/`left`/`right` i homonímia sobre les dues files de `''` amb POMs distints.
Per això van en camps separats i no es fonen mai.

> ℹ️ **G5 va donar `[]` al primer intent i no era un defecte.** G2 ja havia deixat la fila 3395
> en «AH», i el guard «només si el valor CANVIA» va saltar la pregunta sencera — correcte. Es va
> repetir posant-hi un valor diferent abans. Consta perquè el mateix parany és fàcil de repetir.

---

## 5.2 · 🔑 EL CENS: la família nova recupera EXACTAMENT les 4 parelles que la D7 vigilava

Mesurat sobre `fhort` viu, fora del banc:

| model | àmbit | nom | instàncies | POMs |
|---|---|---|---|---|
| **1320** | mare · exterior | `J1` | `extended` · `relaxed` | 1 |
| **1322** | mare · exterior | `J1` | `extended` · `relaxed` | 1 |
| **1380** | mare · exterior | `SR` | `right-extended` · `right-relaxed` | 1 |
| **1494** | mare · exterior | `B` | `extended` · `relaxed` | 1 |

**Quatre, i són les quatre de sempre** (bm 2288/2289, 2230/2231, 3389/3390, 3386/3387). Res més
s'encén. El cercle es tanca amb el cens de la §4.1: aquelles 4 parelles eren l'únic que la D7
barrava i l'únic que la D8 va deixar mut; **ara es desbloquegen I es diuen**, que és exactament
el que la llei d'Agus demanava.

📌 **I no són `left`/`right` sinó `extended`/`relaxed`** — instàncies de l'eix ESTAT (la peça
mesurada estirada i relaxada). L'ambigüitat és igual de real: dues línies «J1» a la mateixa
fitxa, i el paper no diu quina és quina.

---

## 5.3 · COMMIT 5b · frontend — `2cdb0705`

- **`germanaDeLaFila`** a `utils/avisosNomenclatura.js` — funció **pròpia**, no un flag a
  `avisDeLaFila`, pel mateix argument que al backend.
  🚨 **No mira el `pom_id`**: al backend és indiferent per a aquesta família, i mirar-lo deixaria
  sense marca el cas **CENTRAL** (dues instàncies del mateix POM) — l'avís existiria a la
  resposta i **cap fila s'encendria**. Banc `node --test` **15/15**, i aquest cas **vist vermell**
  amb la comprovació de POM sabotejada (**5 de 15 cauen**).
- **`EditableTable`** — prop `avisosGermanes` + registre per `bmId`, **bessons** dels de l'altra
  família. Dos estats i no un de genèric amb clau de família, pel mateix argument del flag.
- **Ranura pròpia**, i la diferència visual és l'argument:

  | | homonímia | germanes |
  |---|---|---|
  | fons | `--warn-state-bg` (marca de dada) | **cap** (és una observació) |
  | vora | `--warn-state` | `--border` |
  | tinta | `--warn-ink` | `--text-soft` |
  | icona | `ti-alert-triangle` | `ti-arrows-left-right` |

  El `title` diu el cas sencer i **anomena les instàncies** amb l'etiqueta del diccionari
  (`etiquetaInstancia`), no amb el slug cru.
- **`MeasuresEntryPanel`** només **transporta**. La banda de resum es queda sent de l'homonímia:
  les germanes es diuen **a la fila**, que és on es veuen les dues alhora i on la pregunta («val
  la pena aquesta instància?») té sentit.
- **i18n**: 3 claus × ca/en/es, amb paritat de **claus i de PLACEHOLDERS** verificada per script
  — l'esborrany castellà deia `{{instancias}}` i mai s'hauria substituït. Icona Tabler **outline**
  (confirmada al paquet), tokens, cap hex.

---

## 5.4 · Verificació

| Control | Resultat |
|---|---|
| `manage.py check` | **net** |
| `npm run build` | **net** |
| `npx eslint` (3 fitxers) | **0 errors** · 12 avisos = **els mateixos 12 que a HEAD** (stash) |
| `node --test avisosNomenclatura.test.js` | **15/15**, i el cas del POM **vist vermell** |
| Els dos jutges en fred | taula de 8 casos creuats, executada abans de cablar res |
| Curls G1-G6 | **6/6** |
| `dist` desplegat | `avisos_germanes`, `avis_germanes`, `ti-arrows-left-right` **presents** |
| `git diff` sobre l'homonímia | **cap línia modificada** a `avisos_de_nomenclatura` ni `avisos_de_rebateig` |

**No verificat**: 10 casos purs nous (PART 3) **escrits i no executats**; cap smoke de navegador.

---

## 5.5 · 🚩 El que segueix obert

1. **El deute d'`is_active`, ara a DUES famílies.** Cap de les dues funcions el filtra —deixat
   idèntic **a posta**, com el brief demana, perquè s'arreglin d'una sola vegada—. Una fila
   podada que porti el codi encendria un avís sobre una fila que la pantalla no pinta.
   Un `is_active=True` a les dues consultes ho tancaria.
2. **Les 4 parelles llegades segueixen vives.** Ara es veuen i es diuen, però ningú les ha
   netejat; la constraint de BD que la D7 esperava poder posar continua sense llei que la
   justifiqui (i amb la D8 ja no n'hi haurà cap: la llei és avisar, no impedir).
3. **La banda de resum del panell no parla de germanes.** Decisió d'aquest commit i no un oblit
   (v. §5.3). Si es vol un resum de peça, és una línia més al panell.

---

## 5.6 · Rastre

```
2cdb0705  feat(mesures): ranura pròpia per a l'avís de germanes homònimes
441a4d31  feat(pom): avís de GERMANES HOMÒNIMES — la vigilància de la D7, sota la D8
```

Sprint sencer: **7 commits**, cap push, `git add` amb pathspec explícit a tots.

**Escriptures al domini fetes pels curls G1-G6** (banc `BANC-11`, model 1362): files **3399**,
**3400** i **3401** creades (POMs 904/907 amb instàncies `right` i cap) · `nom_fitxa` de 3394,
3395, 3400 i 3401 mogut a «AH»/«AH-R». El banc queda amb 7 files i és, ara mateix, el joc de
proves de les dues famílies. **1358** i **1361** segueixen verges.

---
---

# §6 · RE-VERIFICACIÓ D'ACCEPTACIÓ (01/09) — un brief amb la premissa caducada

> Un brief posterior demanava implementar la Decisió 8 **sencera** en 4 commits, declarant que
> «RES d'això s'ha implementat encara: dev acaba a `bc130305` (D7)». **Aquella premissa és
> falsa**, i el PAS 0 que el mateix brief exigia és el que ho ha demostrat. No s'ha escrit ni una
> línia de codi nova: s'ha auditat i s'ha re-verificat en viu.

## 6.1 · PAS 0a · l'estat real de `dev`

```
2cdb0705  feat(mesures): ranura pròpia per a l'avís de germanes homònimes
441a4d31  feat(pom): avís de GERMANES HOMÒNIMES — la vigilància de la D7, sota la D8
a4b52cb8  feat(mesures): el rebateig fila a fila pinta l'avís, i el refús vermell se'n va
05e429e8  fix(pom): la porta del rebateig avisa, ja no barra (409 → 200 + avís)
e03f0b25  feat(mesures): la pantalla d'entrada explica les DUES lleis de nomenclatura
60abe62a  feat(mesures): l'homonímia de nomenclatura es pinta, ja no barra
083b18f5  fix(pom): M1194 — la nomenclatura de gravar-pom avisa, ja no barra
bc130305  merge: decisió 7 …          ← on el brief creia que acabava `dev`
```

`git rev-list --count bc130305..HEAD` → **7**.

## 6.2 · PAS 0b · identitat de staging, en fred

`\l` → bases `ftt_staging` · `ftt_assaig_v5` · `ftt_corpus` (port **5433**, `postgresql@18-main`).
`\dn` → **`fhort`** · `los` · `public`. `public.tenants_client` → 1 `public` · 2 `fhort` · 13 `los`.
Customer BRW **buscat, no assumit** (`codi ilike '%BRW%' or nom ilike '%brownie%'` als DOS
schemes de tenant) → **una sola fila: `fhort`, id 7**, «Textiles y Confecciones Brownie SL».

## 6.3 · PAS 0c · els `fitxer:línia` del brief, contra el codi d'avui

| El brief diu | Estat real a `dev` |
|---|---|
| `views.py:2497-2499` crida `colisio_de_codi` | **Retirada** (083b18f5). Al seu lloc, la nota segellada del perquè. |
| `colisio_de_nomenclatura` (`nomenclatura.py:477`), únic cridador el llapis | **Retirada sencera** (05e429e8), sense cap cridador. |
| Porta `4185`: 409 bloquejant, àmbit 3 camps | **`200` + avisos**, àmbit 4 camps (`views.py:4199-4206`). |
| `EditableTable.jsx:283` desvia el nom al 409 | El desviament hi és; el **409 ja no arriba** i el `catch` s'ha retirat. |
| `pom-propi` (`wizard_views.py:862`) ES QUEDA | ✅ **Intacte** — és l'únic cridador viu de `colisio_de_codi`. |
| `set-measurements` (`views.py:2280`) fora d'abast | ✅ **No s'ha tocat.** |

Funcions vives a `nomenclatura.py`: `avisos_de_nomenclatura` (482) · `avisos_de_rebateig` (564) ·
`germanes_homonimes` (650) · `germanes_de_rebateig` (687).
Camps de resposta: `avisos_nomenclatura` i `avisos_germanes` als **dos** camins (2750/2754 i
4222/4225).

**El que el brief demanava com a COMMIT 4 (frontend) també hi és**, i dues de les seves peces
ja eren construïdes abans del sprint (v. §4 del report): `NomenInput` a
`EditableTable.jsx:1339` fa la nomenclatura editable per fila, i `payloadMesures.js:58-60`
fa viatjar `(capa, instancia, garment)` amb identitat crua. Mesurat, no deduït.

## 6.4 · PAS 0d + acceptació · 12 curls contra staging viu

Servei **reiniciat** abans (el gunicorn havia arrencat 11:20:47 i el darrer commit era d'11:25 —
v. la llei del backend ranci). Banc: model **1361 `BANC-10`**, BRW, **verge** (0 BaseMeasurement),
amb `ModelTask` pom 702 i dues files netes. **1358 `BANC-07` queda verge i sense tocar.**

**COMMIT 1 · `gravar-pom`**

| | Cas | Resultat |
|---|---|---|
| C1a | «B» (àlies BRW del POM 906) sobre el 904 | `200` desat · 0 avisos — **abans 400** |
| C1b | «SF» (àlies del 1015) sobre el 907 | `200` desat · 0 avisos — **abans 400** |
| C1c | 2 files mateix àmbit, POM diferent | `200` · `updated=2` · **1 homonímia** |
| C1d | «J1», ja usat al model BRW 1320 | `200` · 0 avisos |

**COMMIT 2 · la porta del llapis**

| | Cas | Resultat |
|---|---|---|
| C2a | 3403 → «ZA» de 3402 · mateix àmbit, POM diferent | `200` **desat** · **1 homonímia** — abans `409` sense desar |
| C2b | el mateix amb instància `left`/`right` | `200` desat · 0 homonímia · **1 germanes** |
| C2c | re-desar el mateix codi | `200` · 0 · 0 |
| C2d | a un nom lliure | `200` desat · 0 · 0 |

**COMMIT 3 · les dues famílies**

| | Cas | homonímia | germanes |
|---|---|---|---|
| G1 | mateix POM · `left`/`right` · «AH» | 0 | **1** |
| G2 | **POM diferent** · `left`/`right` · «AH» | **0** | **1** |
| G3 | mateixa instància · POM diferent · «AH» | **1** | 0 |
| G4 | germanes amb noms diferents | 0 | 0 |

⚑ **G2 és la condició d'aturada del brief** («si surten els dos, mal separades → ATURA»):
surten **només germanes**. Les famílies estan separades per **construcció de la clau** —
l'homonímia agrupa per un àmbit que inclou `instancia`, o sigui que les dues files cauen en grups
diferents i `len(poms) > 1` no s'hi compleix mai. **No s'atura.**

## 6.5 · Regla del verd, sobre l'arbre tal com queda

| Control | Resultat |
|---|---|
| `manage.py check` | **net** (0 issues) |
| `npm run build` | **net** |
| `node --test avisosNomenclatura.test.js` | **15/15** |
| `npx eslint` (3 fitxers) | **0 errors** · 12 avisos, els de sempre |
| `git status` | `dev` ahead 7, **cap push** |

## 6.6 · Cap aturada, i cap línia nova

Les sis condicions d'aturada del brief, comprovades: cap fet del PAS 0 divergeix **cap a on el
brief temia** (divergeixen perquè ja estan arreglats) · `colisio_de_nomenclatura` no té cap
cridador (està retirada) · cap migració · G2 no encén les dues famílies · el camp d'avisos no
xoca amb cap contracte (els dos camins ja el serveixen) · verd.

**Escriptures al domini d'aquesta re-verificació**: banc **1361 `BANC-10`** materialitzat
(`ModelTask` pom **702**, files **3402** i **3403** i les que els curls G1-G3 hi han afegit).
El model **1358** segueix verge.
