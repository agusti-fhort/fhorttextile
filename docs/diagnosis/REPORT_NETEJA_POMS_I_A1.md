# REPORT · TRAM NETEJA (Fase 2) + A1 acabat — 🛑 STOP a A2

**Data:** 08/08/2026 · **CAP PUSH** · commits `165` · `166` (+ `164` de la diagnosi)
**Base:** `docs/diagnosis/DIAGNOSI_NETEJA_CATALEG_POMS_2026-08-08.md`, abast **A** autoritzat per Agus.

> **El titular:** la Fase 2 està **feta i verificada sencera**. A1 també. **A2 s'atura, i no per
> mida: la pantalla que descriu `maqueta_size_library_v3.html` NO EXISTEIX** — el que hi ha a
> `/size-library` és justament el selector de presets que la maqueta declara superat. «Conformitat
> contra maqueta» i «construir la pantalla» són dues feines diferents, i la segona no cap dins d'un
> bloc amb el STOP compactat.

---

## A · FASE 2 — el buidat

### A.1 · El dump, i per què la verificació no era un tràmit

`ops/backups/PRE-NETEJA-POMS_20260808.dump` (739 KB, schema `fhort`, format custom).

🚨 **El primer dump NO ERA RESTAURABLE i el meu propi `echo EXIT=$?` deia que sí.** Dues coses
alhora: el servidor és **PostgreSQL 18.4** i `/usr/bin/pg_restore` resol a **16.14**, que no pot
llegir el format 1.16 → `unsupported version (1.16) in file header`. I la comanda acabava en
`| tail -3`, o sigui que el codi de sortida que vaig imprimir era el de `tail`, no el de `pg_dump`
(la mateixa trampa que ja tenim anotada per a la suite). Refet amb
`/usr/lib/postgresql/18/bin/pg_dump`.

**La verificació que compta no és «el fitxer s'obre», és «les files hi són dins»:**

| Taula | Files al dump | Files que hi havia |
|---|---:|---:|
| `pom_pommaster` | 396 | 396 |
| `pom_pomglobal` | 274 | 274 |
| `pom_garmentpommap` | 1.748 | 1.748 |
| `pom_gradingrule` | 1.267 | 1.267 |
| `pom_customerpomalias` | 390 | 390 |
| `pom_itembasemeasurement` | 37 | 37 |
| `pom_clientmesuraperfil` | 20 | 20 |
| `models_app_pomplacement` | 2 | 2 |
| `pom_pomcategory` | 28 | 28 |

### A.2 · L'esborrat — recompte per taula

**Porta prèvia:** les 14 dependents que la diagnosi va donar a 0 es van tornar a comptar **just
abans de la primera escriptura** (entre la diagnosi i l'execució hi havia hagut hores). Totes 0,
incloses les dues **ocultes** (`related_name='+'`): `models_app.SizeCheckLine` i
`fitting.PieceFittingLine`.

| Pas | Taula | Esborrades |
|---|---|---:|
| 0 | `GarmentTypeItem.grading_rule_set` → **NULL** | 3 |
| 1 | `models_app.POMPlacement` | 2 |
| 2 | `pom.ClientMesuraPerfil` | 20 |
| 3 | `pom.ItemBaseMeasurement` | 37 |
| 4 | `pom.GradingRule` | 1.267 |
| 5 | `pom.GarmentPOMMap` | 1.748 |
| 7 | `pom.CustomerPOMAlias` | 390 |
| 9 | `pom.POMMaster` | 396 |
| 10 | `pom.POMGlobal` (tenant) | 274 |
| 11 | `pom.POMCategory` | 28 |
| | **TOTAL** | **4.162 files** |

`CustomerPOMAlias` i `POMEstadisticaTenant` són CASCADE i haurien caigut soles amb `POMMaster`;
s'han esborrat **explícitament i abans** per poder-les comptar. Un CASCADE que no es compta és una
fila que ningú no sap que ha marxat.

### ✅ A.3 · La correcció d'abast: els `GarmentTypeItem` NO s'esborren

**El pas d'11 no s'ha hagut de reescriure:** el document ja els posava a §6.1 «QUÈ NO S'ESBORRA»
(«GarmentType / GarmentTypeItem / GarmentGroup — el catàleg de peces no es toca; només els seus
mapes de POM»). L'única cosa que la correcció hi afegeix és el **pas 0**: les referències de
l'ítem cap al catàleg condemnat (`grading_rule_set`) a NULL, sense tocar la fila. Fet: 3 ítems.

**Comptat abans i després per poder-ho demostrar:**

| Intacte | Abans | Després |
|---|---:|---:|
| `tasks.GarmentTypeItem` | 62 | **62** |
| `pom.GarmentType` | 21 | **21** |
| `pom.GradingRuleSet` (queden buits) | 46 | **46** |
| `pom.ItemBaseSet` (queda buit) | 1 | **1** |
| `pom.SizeSystem` | 26 | **26** |
| `models_app.Model` | 1 | **1** |
| `public.POMGlobal` (catàleg canònic) | 125 | **125** |
| `los.POMMaster` | 0 | **0** |

Model de prova `FTT-SS26-0001` → `garment_type_item_id = 19`, **el mateix lligam que tenia**.

---

## B · LA CONSTRAINT

`pom/0075_pommaster_codi_client_unic_ci` — `UniqueConstraint(Upper('codi_client'))`.

**Auditoria SQL directa** (no el «OK» de `migrate_schemas`, que pot enganyar):

```
uniq_pommaster_codi_client_ci ON <schema>.pom_pommaster USING btree (upper((codi_client)::text))
   ✅ public     ✅ fhort     ✅ los
```

**Provada, i no només a la BD:**

| Prova | Resultat |
|---|---|
| `create(codi_client='ZZ-TEST-CHEST')` duplicat exacte | ✅ `IntegrityError` |
| `create(codi_client='zz-test-chest')` **per majúscules** | ✅ `IntegrityError` |
| `full_clean()` amb `'ZZ-test-Chest'` | ✅ `ValidationError` amb el missatge de domini |
| Codi nou | ✅ entra |
| **`POST /api/v1/poms/` amb `zz-test-chest` contra el SERVEI VIU** | ✅ **HTTP 400** amb `{"codi_client": ["«zz-test-chest» ja és al catàleg (POM 747 · Chest width)…"]}` |

🚨 **El 400 no venia sol.** Una constraint d'**expressió** no la tradueix ningú: DRF genera
validadors automàtics a partir d'`unique_together` i `unique=True`, **no** de `UniqueConstraint`
amb `Upper(...)`. Sense el `validate_codi_client` que hi he afegit, `POMMasterViewSet` —que és un
`ModelViewSet` obert a l'escriptura— hauria contestat **500 amb `IntegrityError`**.

**Sense `Trim`, i és decisió:** retallar a l'índex faria que la BD acceptés desar `'U1 '` i el
rebutgés com a duplicat d'ell mateix al desat següent. L'espai es neteja a l'entrada, on ja es fa.

**Anotat, fora d'abast:** `CustomerPOMAlias.uniq_customer_client_code` és **case-SENSITIVE** i té
el mateix forat. I `POMMaster.tolerancia_default_minus/plus` tenen `default=0.6` **float**: amb
`decimal_places=2`, `full_clean()` sobre una instància nova falla amb «no més de 2 decimals»
(`Decimal(0.6)` = 0.5999…). Avui és latent (DRF no crida `full_clean` del model), però és un 400
fantasma esperant qui l'invoqui.

---

## C · LA SEMBRA ZZ-TEST

| Què | Quant |
|---|---:|
| `POMCategory` netes, sense dobles | **3** (Upper body · Sleeve · Lower body) |
| `POMMaster` `ZZ-TEST-*` | **12** |
| → **dada** (lligats i informats) | 8 |
| → **lligat sense informar** | 2 |
| → **no lligat** | 2 |
| `POMGlobal` de tenant | 10 |
| `GradingRuleSet` `ZZ-TEST` (sobre `ALPHA_EU_W`, 8 talles, base M) | 1, amb **5 regles** (4 LINEAR + 1 STEP) |
| `GarmentPOMMap` **sobre l'ítem REAL 19 «chino»** del model d'Agus | 6 |

⚠️ **La sembra es va haver de completar en un segon pas, i el motiu val la pena.** La primera
passada omplia les **descripcions** (`descripcio_ca/en`), però la secció «com es mesura» de la
fitxa **no llegeix les descripcions**: llegeix els camps estructurats (`start_point`, `end_point`,
`reference_point`, `scope`, `orientation`, `state`, `line`, `body_section`). Amb només les
descripcions, els 8 POMs «plens» s'haurien vist **exactament igual** que els 2 «buits» en aquella
secció — i l'estat «dada», que és el que A1 ha de demostrar, no hauria estat exercitable. Els 8
completats en un `update` posterior.

Cap ítem nou: el `GarmentPOMMap` va sobre l'ítem existent, com manava la correcció d'abast.

---

## D · A1 — el catàleg de POMs, acabat

| Requisit | Estat |
|---|---|
| Cens dada→endpoint | ✅ tot el que pinta la fitxa surt de `/poms/`, `/pom-categories/`, `/poms/<id>/us/` i `/customer-aliases/` |
| **Tres estats amb paraules, mai guions** | ✅ v. sota |
| Paginació al total real | ✅ `page_size: 1000` era un **sostre**; ara segueix `next` fins al final |
| Agrupació per categoria | ✅ **3 blocs** = 3 categories reals, en `display_order` |
| Rètol únic «Catàleg de POMs» | ✅ menú + breadcrumb + pantalla, ×3 idiomes |
| Anglès + ⓘ | ✅ el nom local surt de la fila i va darrere la ⓘ (`title` **i** `aria-label`) |
| Comptador amb la cerca al costat | ✅ i fora el segon comptador que repetia el número |

### D.1 · Els tres estats

* **DADA** — lligat i informat.
* **«No lligat al catàleg global»** — `pom_global` és `null`: no és que falti la dada, és que
  aquest POM **no en té cap font**.
* **«Lligat al catàleg global, sense informar»** — `pom_global` hi és i el camp és `''`: la font
  existeix i **ningú l'ha omplerta**.

Les dues últimes són **accions diferents** per a qui llegeix —lligar el POM, o omplir-lo— i un
«—» no permet saber quina toca. La secció ho diu **un sol cop** a la capçalera quan afecta tota la
secció: repetir-ho cinc vegades seria cert i il·legible.

🔑 **Això només és possible gràcies a F2.1a.** Com que els 21 camps de `pom_global` s'emeten
SEMPRE (amb `null`) en comptes de desaparèixer de la resposta, «no lligat» i «camp inexistent» han
deixat de tenir la mateixa forma —la clau absent— i ara es poden distingir.

### D.2 · L'agrupació no agrupava

Detectava **trams consecutius** sobre una llista ordenada per `codi_client`: les categories
s'entrellaçaven i la mateixa capçalera sortia quatre vegades («MÀNIGA·1 … TORS·1 … MÀNIGA·1 …»).
I el nom venia de `categoria_nom`, un `SerializerMethodField` que **barreja dos vocabularis**:
`POMGlobal.categoria` (text lliure: «TORS») si el POM està lligat, i el `nom_ca` de la
`POMCategory` del tenant («Part inferior del cos») si no — per això la llista mostrava capçaleres
en dues llengües i dues convencions alhora. Ara surt de `POMMaster.categoria` (l'ID) resolt contra
`/pom-categories/`.

**Divergències anotades respecte de `maqueta_cataleg_poms_v3.html`:** la maqueta etiqueta el
comptador «POMs» a seques (aquí hi va el rètol unificat, que és el que l'ordre demana) i no pinta
la descripció sota (es conserva). Els botons «Nou POM» i «Accions» de la maqueta no eren a l'abast.

---

## 🛑 E · A2 S'ATURA — i el motiu és una CONTRADICCIÓ D'ABAST, no la mida

L'ordre diu «A2 · Size Library **contra** `maqueta_size_library_v3.html`», que és una conformitat.
**No ho és.** El que la maqueta descriu i el que hi ha a `/size-library` són dues pantalles
diferents:

| La maqueta v3.1 | `/size-library` avui |
|---|---|
| Llista de **runs** a l'esquerra + **fitxa** a la dreta, «mateix patró que el catàleg de POMs» | `SizingProfileSelector`: chips de target/construcció/fit + **targetes de preset** |
| «Els **presets amb graduació dins han desaparegut**. Un run és una escala; aquí no hi ha ni un delta» | La pantalla **ÉS** el selector de presets |
| Les 4 capes de restricció s'editen a la fitxa (multi-selecció M2M) | No hi ha fitxa de run |
| «On s'usa» comptant **les regles ancorades a les SEVES TALLES** | No existeix |

La maqueta v3.1 és **factualment correcta** contra el model d'avui —ho he verificat—:
`SizeSystem` **no té `is_system`** (camps: `codi, nom, descripcio, actiu, base_unit, norma_ref,
parent, customer_codi, tipus_escala, customer`), i les quatre capes **sí** que són M2M
(`targets, construccions, fits, grups`). O sigui que l'esmena de la maqueta no s'equivoca: el que
passa és que **la pantalla que descriu encara s'ha de construir**.

Construir-la és un tram sencer (llista + fitxa + 4 editors M2M + recompte d'ús incloent-hi
l'ancoratge de talla base + clonar + detecció de tipus d'escala amb avís) — de la mida d'U2. No
cap dins d'un bloc amb el STOP compactat, i començar-la a cegues seria decidir jo un abast que és
teu.

**Tampoc he tocat res per fer bonic:** el badge «CANÒNIC DE LA CASA» que la maqueta mana treure
**no existeix enlloc del codi d'avui** (cens fet: cap consumidor de `size_map_canonical` ni de cap
flag de canonicitat a les pantalles de Size Library).

**A3 i A4 queden darrere d'A2** perquè l'ordre els encadena i el STOP de bloc és al final d'A4.

---

## F · Verificació

| Control | Resultat |
|---|---|
| `manage.py check` | ✅ net |
| `makemigrations --check` | ✅ «No changes detected» (model i migració d'acord) |
| `migrate_schemas` | ✅ `0075` aplicada **3 vegades** = 3 schemes |
| Auditoria SQL de l'índex | ✅ als 3 schemes |
| Duplicat contra el servei viu | ✅ **400** amb missatge de domini |
| `npm run build` | ✅ verd |
| `npx eslint src` | ✅ **0 errors** |
| i18n | ✅ **+18 claus** (6 × 3 idiomes), paritat `ca`/`en`/`es` |
| Captures contra el servei viu | ✅ `f22_06`…`f22_10` |
| Suite `pom` + `models_app` + `fitting` | ⏳ **corrent en segon pla** en tancar el report (v. addenda) |

**Captures noves:** `f22_06` catàleg net · `f22_07` el joc ZZ-TEST amb les 5 regles ·
**`f22_08`/`f22_09`/`f22_10` = un estat del «com es mesura» per captura**, que és la manera de
demostrar que els tres es distingeixen de debò.

## 🛑 STOP

Cal la teva sobre A2: **construir la pantalla de runs** (tram propi, amb el seu abast) o
**una altra cosa**. Amb la resposta, A3 i A4 van seguits.

---

# 🚨 ADDENDA (08/08, vespre) — LA SUITE ÉS VERMELLA I ÉS LA CONSTRAINT

**913 tests · `FAILED (errors=11)`** (`fhort.pom` + `fhort.models_app` + `fhort.fitting`, 61 min).

Abans dels canvis d'aquest tram la referència era **671/671 OK**. La diferència de recompte és que
aquella correguda no incloïa `fhort.pom`.

**Els 11 errors són TOTS el mateix, i és meu:** `duplicate key value violates unique constraint
"uniq_pommaster_codi_client_ci"`, sempre al **FIXTURE**, mai a l'asserció. Els tests creen a posta
dos `POMMaster` amb el mateix `codi_client` i la constraint de `pom/0075` ja no ho permet.

⚠️ **La correguda anterior la vaig matar jo:** `timeout 3000` (50 min) sobre tres apps → `EXIT=124`.
El «failed with exit code 1» que va arribar era el wrapper reportant la mort, no un test vermell.
Vaig informar-ne com a «corrent» quan ja estava tallada.

## Els 11, en TRES famílies que no es decideixen igual

### 1 · Un ACCIDENT del fixture — 1 test, mecànic

`models_app/tests_sembra_grading.py:1385` · `test_el_rastre_conta_les_d_ABANS_no_les_de_despres`

```python
for o in ('MANUAL', 'MANUAL', 'CANONICAL'):
    self._resident(o, pom=self._pom(f'RX{o}{self._seq}'))
```

`_seq` l'incrementa `_model()` (`:73`), **no** `_pom()`: amb `MANUAL` dues vegades surt
`RXMANUAL<n>` repetit. El test comprova que el rastre compta **3 residents**; que dos comparteixin
POM era incidental. **Es fixa en una línia i no perd res.** No ho he tocat: modificar un test
perquè passi el meu canvi s'ha de veure, no fer-se en silenci.

### 2 · El test defensa PRECISAMENT el duplicat — 3 tests

`pom/test_ordre_regla_grading.py` · docstring literal:

> «Dos POMs que **MOSTREN el mateix codi**: el criteri semàntic no desempata i mana el `pk` — la
> regla més antiga. Aquí el que es fixa és que **no sigui aleatori**.»

Aquest test existeix perquè dos POMs podien mostrar el mateix codi. **Ja no poden**, i el guard que
defensa queda sense escenari.

### 3 · El 409 de l'import amb candidats — 7 tests

`models_app/test_import_poms_duplicats.py` (5) i `test_import_poms_resolucions.py` (2). Asserten
que, **si el catàleg ja té un codi duplicat**, l'import torna 409 amb els candidats en comptes de
triar-ne un a l'atzar. Mateixa situació que §2: la premissa ha desaparegut.

## El que he verificat sobre si l'escenari encara és assolible

Perquè la decisió no vagi a cegues: **la col·lisió de codi VISIBLE per a un mateix client sembla
tancada per tots els camins**, no només pel que la constraint bloqueja.

* `POMMaster.pom_code` = `codi_client or pom_global.codi` → amb `codi_client` únic, i el buit també
  rebutjat (dos `''` xoquen entre ells), aquesta porta queda tancada.
* `CustomerPOMAlias` ja té `uniq_customer_client_code`: **el mateix client no pot repetir codi**.
  Dos clients DIFERENTS sí, però l'import és per client.

Si això es confirma, els 10 tests de §2 i §3 defensen un estat inabastable. **Però esborrar 10
guards és una decisió amb dents** —i la lògica del 409 podria caldre encara per a col·lisions d'una
altra font— i per això no l'he presa.

## 🛑 La porta del verd, oberta

Els commits `165`→`170` van entrar amb la suite en estat **desconegut** (la vaig matar). Ara se sap:
**vermella, per la constraint**. Res del que hi ha commitat és incorrecte per si mateix —el `check`,
les migracions, l'auditoria SQL, el 400 del duplicat i el build/eslint segueixen verds— però
**la porta dura de backend NO està passada** fins que es decideixi què es fa amb els 11.

**Tres sortides, i és decisió d'Agus:**

1. **Els tests s'adapten** — §1 mecànic; §2 i §3 es re-fixturen per la porta que encara existeix
   (àlies de client) o es retiren amb acta si l'escenari és inabastable.
2. **La constraint s'acota** — p.ex. només sobre `actiu=True`, deixant conviure duplicats
   desactivats. Canvia la llei que vas demanar.
3. **La constraint es revoca** i el duplicat es continua impedint només als camins d'escriptura
   (que és on era abans, i és el que va deixar els 12 duplicats).

**Recomanació:** la 1. La constraint fa exactament el que vas ordenar i el catàleg net la vol; el
que ha quedat obsolet és l'escenari dels tests, no la regla.
