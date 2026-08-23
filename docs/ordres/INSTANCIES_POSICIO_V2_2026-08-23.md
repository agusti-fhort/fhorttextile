# INSTÀNCIES DE POSICIÓ v2 — front/back, B→BM i els dos eixos

**Data:** 2026-08-23 · **Entorn:** `/var/www/ftt-staging`, branca `dev` · **Patró B**
**Decisió:** Agus, 22-23/08 · **Cap push.**

> **LA LLEI, EN UNA FRASE.** La posició d'una mesura té **DOS EIXOS**: LATERAL (left · right) i
> CARA (front · back). Dins d'un eix, excloents; entre eixos, combinables — `left`+`back`
> existeix, `left`+`right` i `front`+`back` no.

| Commit | Què |
|---|---|
| `4e1ebc60` | **D1a** · el sufix de `bottom` passa de `B` a `BM` |
| `dd81e6ef` | **D1b** · les dues cares: `front` (F) i `back` (B) |
| `c277ab55` | **D2** · una etiqueta per eix, i el backend ho fa complir |
| `952c9654` | **D3a** · la regla al front: exclusió per sub-eix i sufix canònic |
| `448c3a3b` | **D3b** · quatre xips a la columna POSICIÓ |
| *(aquesta acta)* | |

---

## D1 · DADES — dues migracions, cap canvi d'esquema

### El rebateig va PRIMER, i sol

`back` vol el sufix natural `B`, que era de `bottom`. **Dos sufixos iguals dins de l'eix farien
que el codi proposat no digués de quina cara parla**: `BB` seria «Waist width · bottom» i
«Waist width · back» alhora. Per això `bottom` → `BM` és una migració a part i va abans.

| | |
|---|---|
| `backend/fhort/pom/migrations/0079_bottom_sufix_bm.py` | guarda de recompte exacte (`slug` és únic → UNA fila per schema com a molt) dins de l'atomic; `reverse` que **no desfà si `back` ja existeix** |
| `backend/fhort/pom/migrations/0080_posicions_front_back.py` | `get_or_create` per slug; guarda que **mesura el dany abans de fer-lo**: si `F` o `B` ja són d'una altra posició, ATURA i diu que passi `0079` |
| `seed_measurement_instances.py:47,55-56` | **la font, alineada al mateix commit** — sense això la propera sembra tornaria a posar `B` (lliçó de `0060_extended_net`) |

**Les cares van al FINAL de `POSICIONS`** (display 9 i 10) i no darrere de `right`: moure el
`display_order` dels sis de sobre reescriuria files que aquest tram no ha de tocar, i l'ordre de
presentació no decideix quins xips surten a la fila.

### Aplicat a staging i auditat

```
manage.py migrate_schemas --plan      → pom.0079 · pom.0080 (Raw Python), per schema
manage.py migrate_schemas             → OK a public, fhort i los
```
```
[public] 10 posicions · sufixos únics: True
[fhort]  10 posicions · sufixos únics: True
[los]    10 posicions · sufixos únics: True
   left L · right R · top T · bottom BM · cf CF · cb CB · side S · waistband_seam '' ·
   front F · back B
```
Mai `--schema` (llei del CLAUDE.md). `sqlmigrate` diu *«THIS OPERATION CANNOT BE WRITTEN AS
SQL»*: són migracions de **dades**, cap DDL.

### 🚩 DUES PREMISSES DEL BRIEF QUE NO ES CONFIRMEN

**① «ZERO files de dades amb `instancia='bottom'`» és FALS a staging.** N'hi ha **61**:

| taula | files amb `bottom` |
|---|---|
| `GradedSpec` | 25 |
| `PieceFittingLine` | 25 |
| `MeasurementChangeLog` | 7 |
| `BaseMeasurement` | **3** |
| `SizeCheckLine` | 1 |

**No canvia el que la migració fa** —el `slug` no es toca i el sufix només PROPOSA—, però sí el
que se n'ha de dir: **els codis ja escrits es queden com són.** Les tres `BaseMeasurement` porten
`nom_fitxa` = `YB`, `YB` i **`BB`** — i aquell `BB` és, literalment, el POM de codi `B` amb el
sufix `B` de bottom. A partir d'ara una germana NOVA de `bottom` es proposarà `BBM`.
**Si l'Agus vol que els codis vells també es rebategin, és una decisió seva i una altra
migració**: el `nom_fitxa` és del patronista, i aquest tram no l'hi toca.

**② El POM del parany no és el #992: a staging és la pk 906** (`B` · «Waist width»). El nom
coincideix i la pk no — la divergència de pk entre entorns, un altre cop (cas #152→219 del cens
del 22/08). **Per això el test en fabrica un i no en cita cap**, i mesura que el rebateig no hi
arriba: són dues taules i dos conceptes.

---

## D2 · MODEL DE VALIDACIÓ — i quatre portes

`backend/fhort/pom/models.py` · `MeasurementInstance`:

```python
SUBEIXOS = (('CARA', ('front', 'back')), ('LATERAL', ('left', 'right')))
subeix_de(slug)              # '' si no en declara cap
error_de_combinacio(valor)   # el MOTIU, o '' si és legal
```

**La regla, sencera:** fins a una etiqueta per eix i, a la posició, fins a una per sub-eix —
**amb una excepció que conserva el comportament d'abans**: una posició *sense* sub-eix declarat
(`top`, `bottom`, `cf`, `cb`, `side`, `waistband_seam`) segueix sent **excloent amb tota la resta
del seu eix**. `top`+`left` no és legal.

> 🚩 **DECISIÓ QUE ES DEIXA A L'AGUS.** El brief obre exactament una família de combinacions
> (cara × lateral). Si algun dia «top-left» o «cf-left» han de conviure, **és declarar-los un
> sub-eix a `SUBEIXOS`** i tot el sistema —validació, xips, sufix— hi va darrere sense tocar res
> més. Ara mateix no s'ha fet perquè ningú ho ha demanat.

**Per què una constant i no una columna:** el sub-eix és la GEOMETRIA de la peça (que left i
right són la mateixa pregunta), no una dada que un tenant informi. Una columna la faria editable
per schema i, el dia que dos schemes discrepessin, la mateixa germana tindria dos codis.

**El que SÍ que viatja:** `GET /api/v1/mesures/diccionari/` publica `subeix` a cada fila i
`subeixos: ['CARA','LATERAL']` en **ordre de composició**. El front no se l'escriu.

### Les quatre portes

Una pantalla no és una barana: el slug entra per HTTP i qualsevol client el pot compondre.

| Porta | On |
|---|---|
| `gravar_pom_view` | `models_app/views.py` — **la de la pantalla de D3** |
| `set_measurements_view` | `models_app/views.py` — el germà bulk |
| `BaseMeasurementSerializer.validate` | `models_app/serializers.py` |
| `GarmentPOMMapSerializer.validate_instancia` | `pom/serializers.py` — la pertinença del catàleg |

### El sufix: **CARA primer, LATERAL després**

`F · B · L · R` quan hi ha un eix; `FL · FR · BL · BR` quan n'hi ha dos.

> ⚠️ **DUES ORDENACIONS, I NO ES CONTRADIUEN.** L'ordre de **composició** el mana `SUBEIXOS`
> (cara → lateral: el codi que va al fabricant es llegeix cara-i-banda). L'ordre de
> **presentació** dels xips el mana el `display_order` (Left · Right · Front · Back: el que es fa
> servir cada dia, primer). El brief demana totes dues, i per això no s'han fet coincidir.

---

## D3 · UI

**La pantalla:** `model_measurements.pom_title` → `MeasuresEntryPanel` → **`EditableTable`**,
columna INSTÀNCIA > POSICIÓ.

- Els xips de la fila són **els que declaren SUB-EIX** (avui Left · Right · Front · Back), no
  `d.opcions.slice(0, 2)`. **Cap slug escrit al codi**: un eix sense sub-eixos (l'ESTAT) cau al
  criteri d'abans i es comporta exactament com sempre (Relaxed · Extended).
- Tota la maquinària de la fila (`dimState`, `germanesDeLEix`, `identitatSenseEix`, el `＋`)
  s'indexa pel **BLOC D'EXCLUSIÓ** i no per l'eix: amb la clau per eix, encendre «l'esquena»
  hauria deixat «l'esquerra» com a *repartida* i el gest s'hauria deshabilitat sol.
- `aplicaInstancia` conserva del que la fila ja portava **tot el que pot conviure** (`xoquen`):
  partir per la cara ja no perd la banda.
- **Cap color nou, cap icona nova**: els xips són els de sempre (`PindolaInstancia`).
  L'estat Relaxed/Extended no s'ha tocat.

**Dues superfícies germanes, tocades perquè comparteixen la regla i no per ampliar l'abast:**
`ColumnatIdentitat` (pas 2 de l'import) comparteix `tramsPerEix` i hauria quedat amb els xips
apagats; `TaulaPOMsCataleg` tenia una **tercera còpia** de la regla escrita a dins
(«dins d'un eix, excloents») i ara passa per `triaTram`. La seva forma no canvia: segueix
ensenyant dues píndoles per columna, que és la seva maqueta.

🚩 **Anotat, fora d'abast:** el `＋` de `TaulaPOMsCataleg` (`:377`) és un botó **sense
`onClick`** — no obre res. Ve d'abans d'aquest tram i no s'ha tocat.

---

## EL VERD

| Control | Resultat |
|---|---|
| `manage.py check` abans de cada commit | **net**, 5/5 |
| `fhort.pom.test_instancies_posicio_v2` | **22 tests · OK** |
| `node --test` diccionariMesures · instanciaTria · capaInstancia | **24 + 17 + n · OK** |
| `npx eslint src` | **0 errors** (272 warnings preexistents) |
| `npm run build` | **OK** |
| **`fhort.pom`** (l'app del tram) | **488 tests · OK** · 2 156 s |

### 🚨 EL GATE ÉS PROPORCIONAL — llei nova d'Agus, 23/08

Aquest tram anava a tancar-se amb `fhort.pom + fhort.models_app` (1 h 50 de correguda). **L'Agus
la va MATAR a mitges** i va posar llei a `DECISIONS.md`: **«verd proporcional»** — el gate de
tancament d'un tram és `manage.py check` + `npm run build` + **NOMÉS l'app tocada**, amb els
tests nous del tram inclosos. És el que s'ha fet.

⚠️ **I EL QUE VA DEIXAR LA SUITE MORTA A MITGES.** El primer intent del gate va donar **68
errors que no eren del tram**: un `TenantTestCase` interromput deixa la fila
`tenants_client(schema_name='test')` COMMITADA a la BD de test, i amb `--keepdb` cada
`setUpClass` peta amb `UniqueViolation: tenants_client_schema_name_key`. Vermell que sembla teu
i no ho és. Neteja i re-correguda:

```sql
delete from tenants_domain where tenant_id in (select id from tenants_client where schema_name='test');
delete from tenants_client where schema_name='test';
drop schema if exists test cascade;
```

⚠️ **`npm run build` PUBLICA `frontend/dist`**, que és el que staging serveix. S'ha fet perquè
el gate el demana i perquè l'arbre no tenia feina aliena sense commitar: el que s'ha publicat és
exactament el que hi ha a `dev`.

**Els tests que el brief demanava, i on són:**

| Demanat | On |
|---|---|
| exclusió per eix (backend) | `ExclusioPerEixTest` · `PortesDeLaCombinacioTest` |
| combinada legítima (back+left) | `ExclusioPerEixTest.test_la_combinada_legitima_back_left` + els xips |
| sufixos F/B/L/R/FL/FR/BL/BR | `SufixCompostTest` (backend) + `diccionariMesures.test.js` (composició) |
| bottom respon BM i cap resta de B | `SufixBottomTest` · `CaresFrontBackTest.test_el_sufix_B_ja_no_es_de_bottom` |
| el POM `B` intacte (el parany) | `SufixBottomTest.test_el_POM_de_codi_B_no_el_toca_ningu` |

**Cap push. El merge i el desplegament els fa l'Agus.**
