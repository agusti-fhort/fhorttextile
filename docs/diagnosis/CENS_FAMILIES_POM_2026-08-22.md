# CENS · GOVERN DEL VOCABULARI DE FAMÍLIES DE POM

**Data:** 2026-08-22 · **Entorn:** staging (`ftt_staging`) · **Patró A exprés — READ-ONLY**
**Origen:** l'Agus veu al desplegable «Família de lletra» del POMCataleg dues entrades
`CANESÚ (L · P)`.

> **BARANA.** Tota consulta d'aquest cens s'ha fet amb `PGOPTIONS='-c
> default_transaction_read_only=on'`, i la barana s'ha **provat amb una escriptura que havia de
> petar** abans de començar (llei del 22/08):
> ```
> llegir SÍ: pk=57 codi='A'
> ✅ BARANA VIVA — l'escriptura ha petat: InternalError: cannot execute UPDATE in a read-only transaction
> ```
> **Cap escriptura en tot el cens.** Cap fitxer de codi tocat.

> ⚠️ **PROD NO ÉS ACCESSIBLE DES D'AQUESTA MÀQUINA.** El clúster només serveix `ftt_staging`
> (+ bases de test i diagnosi): `['ftt_staging', 'ftt_tmp_diag_v4', 'postgres', 'tea205_probe',
> 'test_*']`. El cens equivalent a PROD **no s'ha pogut fer** i queda pendent d'una sessió amb
> accés. Res del que segueix afirma res sobre PROD.

---

## 🚨 EL VEREDICTE, PRIMER: NO HI HA CAP DUPLICAT

**`L` i `P` són DUES FAMÍLIES DIFERENTS, totes dues en ús, que comparteixen ETIQUETA.**

| pk | codi | nom_ca | ordre | POMs que hi apunten |
|---|---|---|---|---|
| 68 | `L` | `CANESÚ (L · P)` | 12 | 2 — `L` Back yoke width · `L1` Yoke seam length |
| 69 | `P` | `CANESÚ (L · P)` | 13 | 3 — `P` Centre back yoke height · `P1` Side yoke height · `P2` Centre front yoke height |

`L` són **amples i llargs de costura** del canesú; `P` són **alçades** de canesú. Són conceptes
diferents del document del client, i els seus 5 POMs també ho són.

**El que està trencat no és la dada: és el que la pantalla ENSENYA.** El desplegable pinta
l'**etiqueta** i no el **codi** — i l'etiqueta, que ve del full de sembra, ja duu les dues
lletres a dins (`CANESÚ (L · P)`), perquè al document del client aquestes dues famílies formen
**una sola secció**.

> 🔴 **PER TANT: NO S'HA D'ESBORRAR RES.** Una «neteja de duplicats» aquí fusionaria dues
> famílies vives i mouria 5 POMs. La reparació és de **PRESENTACIÓ**, no de dades.

---

## 1 · D'ON SURT LA LLISTA

| | |
|---|---|
| **Model** | `fhort.pom.models.POMCategory` (`backend/fhort/pom/models.py:360`) |
| **Taula** | `pom_pomcategory` — **taula pròpia**, no `choices` |
| **Endpoint** | `GET /api/v1/pom-categories/` |
| **ViewSet** | `POMCategoryViewSet` (`pom/views.py:238`) — **`ReadOnlyModelViewSet`** |
| **Serializer** | `POMCategorySerializer`, `fields = '__all__'` |
| **Qui el crida** | `POMCataleg.jsx:323` → `pomCategories.list` (`endpoints.js:313`), paginat sencer |
| **Com es pinta** | `nomCat()` = **`c.nom_en \|\| c.nom_ca \|\| c.codi`** (`POMCataleg.jsx:382`) |

Camps: `codi` (**`unique=True`**, ≤20), `nom_en`, `nom_ca`, `descripcio`, `body_area`,
`display_order`, `actiu`.

🔑 **`pom` viu a SHARED *i* TENANT** (`settings.py:55,68`), o sigui que `pom_pomcategory`
**existeix a cada schema**. És **catàleg de TENANT** a efectes pràctics: cada schema té el seu
contingut i **no hi ha cap lligam entre ells**.

---

## 2 · CONTINGUT PER SCHEMA — són DOS VOCABULARIS SENSE RELACIÓ

### `public` — 15 files · vocabulari de SECTOR, bilingüe

`Upper body` · `Sleeve` · `Collar / Neckline` · `Lower body` · `Waistband` · `Rise` ·
`Skirt / Dress` · `Hem / Finish` · `Knitwear-specific` · `Swimwear-specific` ·
`Closure / Detail` · `Jacket / Coat` · `Placement` · `Accessories` · `Technical / Workwear`

pk 1–15 · `codi` = el nom anglès · `nom_en` **i** `nom_ca` informats (15/15) · `descripcio` 15/15
· `body_area` **0/15** · tots actius · **cap duplicat** · **0 POMMaster a `public`**.

### `fhort` — 25 files · vocabulari de LLETRA (A–Z), només català

| pk | codi | nom_ca | POMs | | pk | codi | nom_ca | POMs |
|---|---|---|---|---|---|---|---|---|
| 57 | A | PIT I SOTA-PIT (A) | 3 | | 70 | M | BOCA DE CAMAL (M) | 1 |
| 58 | B | CINTURA I ENTORN (B) | 7 | | 71 | N | MOTIUS I APLICATS (N) | 3 |
| 59 | C | CADERA, CUIXA I ENTRECUIX (C) | 7 | | 72 | Q | PINCES I PLECS (Q) | 7 |
| 60 | D | BAIX DEL COS (D) | 1 | | 73 | R | BUTXACA (R) | 8 |
| 61 | E | COLL · ESPATLLA · ESCOT · SOLAPA (E) | 25 | | 74 | S | SISA I OBERTURES (S) | 6 |
| 62 | F | LLARGS DEL COS (F) | 16 | | 75 | T | TIRANT I TAPETA (T) | 6 |
| 63 | G | CANALÉ, BAIXOS I GODET (G) | 3 | | 76 | U | BOTONADURA I CREUAMENT (U) | 7 |
| 64 | H | CAPUTXA (H) | 5 | | 77 | V | VOLANT (V) | 3 |
| 65 | I | LLARGS DE MÀNIGA (I) | 10 | | 78 | W | GOMA I ELÀSTICS (W) | 2 |
| 66 | J | AMPLES DE MÀNIGA (J) | 5 | | 79 | X | PESPUNT I VIUS (X) | 3 |
| 67 | K | TRAUS, BOTONS I ULLETS (K) | 3 | | 80 | Y | PANELLS I TALLS (Y) | 4 |
| **68** | **L** | **CANESÚ (L · P)** | **2** | | 81 | Z | COMPLEMENTS (Z) | 3 |
| **69** | **P** | **CANESÚ (L · P)** | **3** | | | | | |

`nom_en` **0/25** · `descripcio` **0/25** · `body_area` **0/25** · tots actius · ordre 1–25 sense
salts. **Cap duplicat de codi** (la constraint no ho permetria) · **1 duplicat d'etiqueta**.

### `los` — **0 files**

El tenant LOSAN **no té cap família** (coherent amb els seus 0 POMMaster).

### 🚨 Els dos vocabularis són INCOMPATIBLES i un tenant nou rep el DE `public`

`bootstrap_tenant` sembra `POMCategory` al bloc `base` copiant de `public` per clau natural
`('codi',)` (`tasks/management/commands/bootstrap_tenant.py:57,142`). O sigui que **un tenant
nou neix amb les 15 categories de sector en anglès**, i `fhort` funciona amb 25 lletres en
català que **no existeixen enlloc més**. No hi ha cap mecanisme que els reconciliï.

---

## 3 · ÚS REAL — el vocabulari SÍ que s'omple

| | `public` | `fhort` | `los` |
|---|---|---|---|
| POMMaster totals | 0 | **144** | 0 |
| …amb família | 0 | **143 (99,3 %)** | 0 |
| …**sense** família | 0 | **1** | 0 |
| famílies que no fa servir ningú | **15/15** | **0/25** | — |

**La hipòtesi «el desplegable ofereix un vocabulari que ningú omple» és FALSA a `fhort`**: 143
de 144 POMs tenen família i **cap de les 25 famílies està òrfena**. La distribució és desigual
però tota viva (de 1 POM a `D`/`M` fins a 25 a `E`).

L'únic POM sense família és **pk=1051 `ZZS45D` «Mesura de prova S45/D»**, `origen_import='cataleg'`
— **residu d'una QA del tram S45/D**, no una fila de domini. 🚩 Candidat a neteja, a part.

**A `public` passa el contrari i és el senyal fort:** 15 famílies, **cap POMMaster**, **ningú les
fa servir**. Són vocabulari mort que només reviu quan `bootstrap_tenant` el copia a un tenant nou.

---

## 4 · QUI ESCRIU — tres escriptors, i **un és per API sense gating**

| # | Node | Tipus | Clau | Gating |
|---|---|---|---|---|
| ① | `sembra_cataleg_v4.py:105` `POMCategory.objects.create(codi=fam, nom_ca=sec…)` | command | `codi` | CLI |
| ② | `replace_pom_catalog.py:758` `update_or_create(codi=…)` (les 15 de sector) | command | `codi` | CLI |
| ③ | **`s9_views.py:162` `update_or_create(codi=…)`** | **API** | `codi` | 🔴 **`IsAuthenticated`** |
| ④ | `bootstrap_tenant.py:142` (còpia public→tenant) | command | `codi` | CLI |

### 🔴 ③ ÉS EL FORAT: `POST /api/v1/onboarding/setup-from-excel/`

Rutat i viu (`tasks/urls.py:265`), decorat **només** `@permission_classes([IsAuthenticated])`
(`s9_views.py:79-81`). Puja un Excel i, del full `pom_categories`, fa `update_or_create` per
`codi` sobre **`nom_en`, `nom_ca` i `display_order`**.

Conseqüència: **qualsevol usuari autenticat —un tècnic— pot reescriure les etiquetes i l'ordre
de les 25 famílies de la casa amb un fitxer**, sense CONFIGURE i sense traça. És exactament el
forat que el tram 4 de la sobirania del POM acaba de tancar a `POMMasterViewSet`, per una altra
porta i al vocabulari del qual pengen 143 POMs.

🚩 **I al costat, codi que no pot funcionar:** `s9_views.py:180` fa
`POMGlobal.objects.update_or_create(codi_intern=pom_code, …)` i **`POMGlobal` no té cap camp
`codi_intern`** (`models.py:33`, es diu `codi`). Aquesta branca llança `FieldError` sempre que
s'hi arriba. Anotat, no tocat.

### La resta són LECTORS, i tots per `codi` ✅

`load_losan_package:251` · `extend_pom_catalog:191` · `seed_baby_poms:222,257` ·
`reseed_tenant_fhort:249` · `export_losan_package:185` (emet `categoria.codi`, mai la pk).
`extraction_views:2435` no escriu famílies però **n'assigna una per defecte** —la primera per
`display_order, codi`— als POMs que l'import crea (avui seria sempre `A`, la del pit).

### ¿És el patró G9 un altre cop? **Sí, punt per punt.**

G9 (`DECISIONS §G9`, activa des de la seva data) diu de `TaskType`: *«cap escriptor/editabilitat
nou al tenant; referències noves sempre per `code`, mai per PK; tall futur: la definició va a
sistema/public (patró POMGlobal)»*.

`POMCategory` compleix **les tres condicions** de la mateixa manera: escriptor viu al tenant per
API sense gating (③), referències per **PK** a tot el contracte (§6), i definició duplicada
entre `public` i el tenant sense cap tall declarat.

---

## 5 · i18n — 🚨 XOC FRONTAL AMB LA LLEI DEL 09/08

**Les 25 etiquetes de `fhort` són literals EN CATALÀ a la BD** (`nom_ca` 25/25, `nom_en` 0/25).

Això contradiu la decisió d'Agus del 09/08, **vigent**: *la traducció de vocabulari de domini NO
viu a la base de dades*; va per `TranslationCache` amb l'idioma de l'usuari i fallback a
l'anglès (mecanisme ja CONSTRUÏT el 13/08, `/api/v1/translate/pom/`).

I hi ha un **segon efecte, visible**: `nomCat()` fa `nom_en || nom_ca || codi` perquè *«el
catàleg va en anglès»* (maqueta v3). Amb `nom_en` buit a les 25, **la pantalla cau sempre al
català** — capçaleres de grup i desplegable en català enmig d'una pantalla que la maqueta va
decidir en anglès. La cascada està bé; el que falta és la dada.

**Què caldria per fer-ho bé** (proposta, §7-C).

---

## 6 · INTEGRITAT

| Pregunta | Resposta |
|---|---|
| Unicitat declarada? | **Sí, `codi = CharField(unique=True)`** (`models.py:363`). Sensible a majúscules, sense `Trim`. |
| Unicitat d'etiqueta? | **No.** Cap constraint sobre `nom_ca` ni `nom_en`. |
| Quants duplicats de codi? | **0** — i la constraint els fa impossibles. |
| Quants duplicats d'etiqueta? | **1**, i només un: `CANESÚ (L · P)` (`L` i `P`). |

### Com ha nascut, exactament

`sembra_cataleg_v4.py:98-106` recorre `ops/sembra_v4/SEMBRA_1_canonic.csv` i, **per cada
`familia` nova**, crea la fila amb `codi=familia` i **`nom_ca=seccio`**. La `familia` i la
`seccio` són **dues columnes diferents del full**, i el full té exactament **una secció que en
cobreix dues famílies**:

```
codi | fam | seccio
L    | L   | CANESÚ (L · P)
L1   | L   | CANESÚ (L · P)
P    | P   | CANESÚ (L · P)
P1   | P   | CANESÚ (L · P)
P2   | P   | CANESÚ (L · P)
```

Comprovat sobre les 25 seccions del full: **`CANESÚ (L · P)` és l'ÚNICA que en cobreix dues.**
La resta són 1:1. O sigui que el duplicat és **determinista, únic i acotat** — i el document
del client ja el declarava, escrivint les dues lletres dins del rètol.

> 🔑 **La lliçó:** la clau (`familia`) i l'etiqueta (`seccio`) del full **no tenen la mateixa
> cardinalitat**, i la sembra les va tractar com si sí. La constraint de `codi` va fer la seva
> feina; el que no hi havia era ningú vigilant que dues claus no es quedessin **indistingibles
> a pantalla**.

---

## 7 · PROPOSTA (no executada — cap escriptura)

### A · LA REPARACIÓ IMMEDIATA: el desplegable diu el CODI

**Un canvi de PRESENTACIÓ, zero migració, zero risc de dades.** La pantalla ha de pintar la
lletra al costat de l'etiqueta a les tres superfícies que avui només diuen l'etiqueta
(`nomCat`, la capçalera de grup de la llista, i els dos `<select>`):

```
L · CANESÚ (L · P)
P · CANESÚ (L · P)
```

El codi ÉS la família —és el que la patronista diu— i és **únic per constraint**, o sigui que
dues entrades no es podran tornar a veure iguals mai més, vingui d'on vingui l'etiqueta.

**Rebutjat explícitament: fusionar `L` i `P`.** Són dues famílies vives amb 5 POMs i conceptes
diferents (amples/llargs vs alçades). Fusionar-les perdria una distinció del document del
client per un defecte de rètol.

**Rebutjat també: reescriure les etiquetes a `CANESÚ (L)` / `CANESÚ (P)`.** És escriure a la BD
per arreglar el que la pantalla no diu, i **trairia el document**, que declara una sola secció.

### B · GOVERN (patró G9, aplicat a `POMCategory`)

1. **Congelació viva dels escriptors de tenant.** `POST /api/v1/onboarding/setup-from-excel/`
   passa a **CONFIGURE** com a mínim, i idealment la branca `pom_categories` es retira: la
   definició del vocabulari no és una càrrega d'Excel de qualsevol usuari. *(La branca
   `pom_globals` del mateix endpoint està trencada — `codi_intern` no existeix — i la seva
   retirada no perd res.)*
2. **Referència per `codi`, mai per PK.** Avui **tot el contracte viatja per pk**:
   `POMMasterSerializer.categoria` (PrimaryKeyRelatedField), `poms/crear-tenant/` i `pom-propi/`
   (`categoria_id`), i el `<select>` del front (`Number(e.target.value)`). L'únic node que ja ho
   fa bé és `export_losan_package` (`categoria.codi`, regla R2). Proposta: **afegir
   `categoria_codi` (SlugRelatedField) al contracte, escrivible, i deixar `categoria` com a
   llegat de lectura** — mateix patró que `target_codis` a `SizeSystemSerializer`, que ja existeix
   i funciona. Sense això, cap paquet de federació ni cap import pot referir-se a una família
   sense endevinar-ne la pk del schema de destí.
3. **Unicitat d'etiqueta: NO afegir-la.** Seria contradictòria amb el document del client, que
   comparteix rètol a posta. El que ha de ser únic ja ho és: el `codi`. *(Sí que valdria la pena
   fer la de `codi` insensible a majúscules —`Upper('codi')`, com
   `uniq_pommaster_codi_client_ci`— per la mateixa raó que allà: `l` i `L` són la mateixa
   família per a qui la llegeix. Cap col·lisió actual.)*
4. **Decidir on viu la definició** (el «tall futur» de G9). Avui `public` té 15 famílies que **no
   fa servir ningú** i que un tenant nou hereta, mentre `fhort` en té 25 que no existeixen enlloc
   més. Les dues opcions són netes; la que hi ha ara no ho és:
   · **(a) família = del TENANT** → buidar/retirar les 15 de `public` i treure `POMCategory` del
     bloc `base` de `bootstrap_tenant`; un tenant nou neix sense famílies i les declara.
   · **(b) família = de SISTEMA** (patró `POMGlobal`) → `public` mana i el tenant hi apunta;
     obliga a decidir què es fa amb les 25 lletres de `fhort`, que són **vocabulari de client**.
   🔑 Les lletres A–Z de `fhort` vénen del full d'un client concret (Brownie): això empeny cap a
   **(a)**, o cap a un tercer nivell «família de client» anàleg a `CustomerPOMAlias`. **És decisió
   d'Agus.**

### C · CAMÍ D'i18n

L'estat d'avui (català literal a `nom_ca`) **és el que la llei del 09/08 prohibeix**, i alhora
és l'única cosa que fa la pantalla llegible. El camí coherent amb la llei ja construïda:

1. **`nom_en` passa a ser el camp canònic** i s'omple amb el rètol en anglès (25 files). És dada
   de catàleg, no traducció: el mateix estatus que `POMMaster.nom_client`.
2. **`nom_ca` es congela i deixa de llegir-se** —o es buida— i la traducció visible surt de
   `TranslationCache` per la ⓘ, com als POMs (`/api/v1/translate/pom/`, tram ⓘ del 13/08).
   `nomCat()` no s'ha de tocar: ja prefereix `nom_en`.
3. **Requisit bloquejant:** el mecanisme de traducció **necessita la clau de l'API al `.env`**,
   que segons l'acta del 13/08 encara falta. Sense això, buidar `nom_ca` deixaria la pantalla
   muda — o sigui que el pas 2 **no es pot fer abans**.
4. Els codis de família (`A`…`Z`) **no es tradueixen mai**: són dades de domini, com LINEAR/STEP.

### D · NETEJA A PART

🚩 `POMMaster pk=1051 ZZS45D «Mesura de prova S45/D»` (`origen_import='cataleg'`) — residu de la
QA del tram S45/D, l'únic POM sense família de tot `fhort`. No és d'aquest tram; s'anota.

---

## 8 · RESUM EXECUTIU

| Pregunta de l'ordre | Resposta |
|---|---|
| D'on surt la llista | `POMCategory`, taula pròpia, `GET /api/v1/pom-categories/` (**ReadOnly**) |
| Catàleg global o de tenant | **De tenant**, i amb `public` servint de motlle per a tenants nous — **dos vocabularis incompatibles** |
| Hi ha duplicats | **Cap de codi** (constraint). **Un d'etiqueta**, i **no és un error de dades** |
| S'usa el vocabulari | **Sí**: 143/144 POMs amb família, **0 famílies òrfenes** a `fhort`; a `public`, 15 famílies i **cap ús** |
| Qui escriu | 3 escriptors; **un és API amb només `IsAuthenticated`** (`onboarding/setup-from-excel/`) |
| És el patró G9 | **Sí, punt per punt** |
| i18n | **Català literal a la BD** → xoca amb la llei del 09/08; a més deixa la pantalla en català on la maqueta la vol en anglès |
| Unicitat | `codi unique=True` ✅ · etiqueta sense unicitat, **i és correcte que no en tingui** |

**Cap escriptura. Cap fitxer de codi tocat. Res executat.**
