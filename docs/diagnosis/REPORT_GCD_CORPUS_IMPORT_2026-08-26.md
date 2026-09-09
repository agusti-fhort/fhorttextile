# GarmentCodeData v2 · import tancat — FASES 3 i 4

> Abast d'aquesta correguda: **només sanity (F3) i report (F4)** sobre el que ja era a BD.
> Cap baixada, cap re-ingesta, cap escriptura fora d'aquest fitxer. Les fases 1 i 2 van
> acabar soles el **25/08 a les 18:31 UTC** (`ALL BATCHES DONE`).
>
> ⏱️ Tot en **UTC** (el servidor hi va; l'Agus és UTC+2).

## VEREDICTE EN UNA LÍNIA

> **Corpus SANT i utilitzable** — `sanity.py` dona **PASS** amb les 10 comprovacions
> d'integritat a zero i 20/20 SVGs oberts — **amb dues coses que s'han de saber**: el
> **share serveix els lots 12 i 13 solapats** (3.696 designs duplicats, verificat byte a byte),
> i el **delta contra el doc oficial no és `+8` sinó `+6.797`** (`+3.101` un cop deduplicat),
> concentrat gairebé tot a `dresses`.

---

# FASE 3 · SANITY

Eina: `/root/gcd_corpus/scripts/sanity.py` (només SELECTs i lectura de fitxers).
Correguda: **26/08 04:51:39 → 04:51:53 UTC**, exit 0, **`RESULT: PASS`**.

## 3.1 · Recomptes per taula, i quadratura contra els logs

| taula | files a BD | suma de les línies `FI ingest` | quadra? |
|---|---:|---:|:--:|
| `design` | **132.670** | 132.670 | ✅ |
| `panel` | **1.470.237** | 1.470.237 | ✅ |
| `edge` | **9.817.862** | 9.817.862 | ✅ |
| `stitch` | **4.028.305** | 4.028.305 | ✅ |

**Quadratura exacta, fila a fila, a les quatre taules.** Els 36 lots hi són
(`ingest_batch`: 36 × `complete`) i els 36 directoris del disc porten `_COMPLETE`.

Ràtios: **11,08 panels/design · 74,00 edges/design · 30,36 stitches/design**.

### El «~43k panels i ~285k edges per lot» del brief

Són el **sostre**, no la mitjana. Mesurat sobre les 36 línies `FI ingest`:

| | mín | màx | **mitjana** |
|---|---:|---:|---:|
| panels/lot | 36.225 | 44.181 | **40.840** |
| edges/lot | 244.999 | 294.176 | **272.718** |

Els lots baixos (0-6, 21-25) porten ~3.4xx elements i els alts ~3.8xx, i d'aquí ve la
forquilla. **Els ~43k/~285k del brief són el que fan els lots grans**; la mitjana real és un
5-6% per sota, i multiplicada per 36 dona exactament el que hi ha a BD.

## 3.2 · Totals per categoria vs documentació oficial

### Tal com surt de BD (amb els duplicats a dins)

| categoria | nostre | oficial | delta | nostre % | oficial % |
|---|---:|---:|---:|---:|---:|
| dresses | 49.725 | 44.333 | **+5.392** | 37,5% | 35,2% |
| jumpsuits | 7.988 | 7.575 | +413 | 6,0% | 6,0% |
| pants | 9.588 | 10.177 | −589 | 7,2% | 8,1% |
| skirts | 30.219 | 29.648 | +571 | 22,8% | 23,6% |
| upper_garments | 35.150 | 34.140 | +1.010 | 26,5% | 27,1% |
| **TOTAL** | **132.670** | **125.873** | **+6.797** | | |

### 🚨 El delta NO és `+8`. És `+6.797`, i una meitat té causa trobada

El brief demanava reportar les deltes «amb el +8 global ja observat». **Aquest +8 no es
reprodueix per enlloc**: el desajust real és de **+6.797 designs (+5,4%)**. No s'ha forçat res;
això és el que hi ha. D'aquests, **3.696 tenen causa identificada i és amunt** (§3.3).

### Deduplicat — 1 fila per `element_name`

| categoria | nostre (dedup) | oficial | delta |
|---|---:|---:|---:|
| dresses | 48.336 | 44.333 | **+4.003** |
| jumpsuits | 7.783 | 7.575 | +208 |
| pants | 9.347 | 10.177 | −830 |
| skirts | 29.354 | 29.648 | −294 |
| **upper_garments** | **34.154** | **34.140** | **+14** |
| **TOTAL** | **128.974** | **125.873** | **+3.101** |

Un cop deduplicat, **quatre de les cinc categories cauen a distància petita** i
`upper_garments` queda a **+14** sobre 34.140 (**+0,04%**) — que és, versemblantment, l'ordre de
magnitud del «+8» que el brief recordava. **Tot el desajust que queda viu a `dresses`: +4.003.**

### Per què `dresses` i per què no s'ha «arreglat»

La categoria **no ve donada pel dataset: la derivem nosaltres**, a `ingest_batch.py:51`:

```python
def categorise(meta):
    up, bo = meta.get("upper"), meta.get("bottom")
    is_pants = bo == "Pants"
    if up and bo:  return "jumpsuits" if is_pants else "dresses"
    if bo:         return "pants" if is_pants else "skirts"
    if up:         return "upper_garments"
    return "other"
```

`dresses` és el **calaix ample** (`upper` **i** `bottom`, i el `bottom` no és `Pants`), i és
justament el que sobra, mentre `pants` (−830) i `skirts` (−294) falten. Això apunta a una
**frontera de classificació** que no cau on la va posar el generador, no necessàriament a
designs de més al corpus. Però `−830 −294 = −1.124` **no cobreix `+4.003`**, o sigui que la
frontera tota sola no ho explica. **Es reporta i no es toca**, que és el que demanava el brief.

## 3.3 · 🚨 EL SHARE SERVEIX ELS LOTS 12 I 13 SOLAPATS

`sanity.py` comprova duplicats per **`(batch, element_name)`** — que és la `UNIQUE` de la taula.
**Un mateix element servit en DOS lots hi passa per sota.** Comprovat a part:

```
designs:                    132.670
element_name distints:      128.974
                            --------
duplicats:                    3.696
```

Un sol parell de lots hi és implicat, i no és cap altre:

| | |
|---|---|
| parells de lots amb elements compartits | **només `garments_5000_12` ∩ `garments_5000_13`** |
| elements compartits | **3.696** |
| lot 12 | 3.819 designs (123 exclusius seus) |
| lot 13 | 3.805 designs (109 exclusius seus) |
| solapament | **~97%** de cada lot |

**No és una doble baixada nostra.** Els dos lots es van baixar per separat, amb xifres
diferents (`net_bytes` 5.762.925.074 vs 5.746.482.963; `files` 11.457 vs 11.415), i el driver
no va reintentar res entremig (§4.2). **És el share d'origen qui serveix els dos lots amb el
mateix contingut a dins.**

**Verificat pel contingut, no pel nom.** Sobre 4 parells presos a l'atzar, el `.gz` **difereix**
i el contingut **descomprimit és idèntic**:

| element | md5 del `.gz` (12/13) | md5 del contingut | |
|---|---|---|---|
| `rand_008CF7SXIX` | `1520524e…` / `ed5fe24b…` | `ba4f393e…` / `ba4f393e…` | **IDÈNTIC** |
| `rand_00C6RWWA0F` | `942beb85…` / `4b984f0f…` | `87438608…` / `87438608…` | **IDÈNTIC** |
| `rand_00EPC44KSJ` | `7cd23bda…` / `3b312f69…` | `f2d666c2…` / `f2d666c2…` | **IDÈNTIC** |
| `rand_01CGLSRYKE` | `2d17fb6e…` / `a1fbb8a9…` | `f0aca94a…` / `f0aca94a…` | **IDÈNTIC** |

> 🔑 El `.gz` no serveix per comparar: **gzip estampa l'hora a la capçalera**, o sigui que dos
> fitxers idèntics donen sha diferents. És la mateixa trampa que `ModelFitxer.checksum` als
> `.ftt`. **Es compara el contingut descomprimit.**

**Pes mort**: els 3.696 designs duplicats arrosseguen **41.069 panels** i **273.080 edges**
(≈2,8% dels panels del corpus). Repartits per categoria: dresses 1.389 · upper_garments 996 ·
skirts 865 · pants 241 · jumpsuits 205.

**No s'ha esborrat res** (l'ordre diu cap escriptura). Per a qualsevol consum estadístic o
d'entrenament, **desduplicar a la lectura**:

```sql
SELECT DISTINCT ON (element_name) * FROM design ORDER BY element_name, batch;
```

## 3.4 · Integritat — 10 de 10 a zero

| comprovació | resultat |
|---|---|
| panels sense design | **0** ✅ |
| edges sense panel | **0** ✅ |
| stitches sense design | **0** ✅ |
| designs amb 0 panels | **0** ✅ |
| `contour_rs` de llargada incorrecta | **0** ✅ |
| `descriptor` de llargada incorrecta | **0** ✅ |
| mètriques de panel no finites | **0** ✅ |
| `panel.n_edges` ≠ files a `edge` | **0** ✅ |
| família sense classificar (`other`) | **0** ✅ |
| duplicats `(batch, element)` | **0** ✅ |

> Nota de lectura: `contour_rs` es comprova contra **256**, i tant `schema.sql` com
> `ATTRIBUTION.md` parlen de **128 punts**. No es contradiuen: són 128 punts × (x,y) = 256
> reals. Val la pena saber-ho abans d'«arreglar» cap de les dues xifres.

## 3.5 · Mostra de 20 SVGs — 20/20

Oberts, descomprimits, validats com a XML/SVG i **comptats els `<path>` contra `design.n_panels`**:
**20 OK, 0 bad**, amb panells de 4 a 26. Cap fitxer corrupte, cap desajust paths↔panels.

## 3.6 · Índexs — els 8 creats

`panel_family_idx` · `panel_role_raw_idx` · `panel_design_id_idx` · `stitch_design_id_idx` ·
`edge_panel_id_idx` · `design_category_idx` · `design_batch_idx` · `panel_edge_signature_idx`

Els **8 d'`indexes.sql`** hi són, més les PK de les 4 taules, la d'`ingest_batch` i la unique
`design_batch_element_name_key`. **14 índexs en total.**

## 3.7 · Rol `corpus_ro` — operatiu i ben tancat

Provat **connectant-s'hi de debò**, no mirant `pg_roles`:

| prova | resultat |
|---|---|
| `SELECT` sobre `design` / `panel` a `ftt_corpus` | ✅ funciona (132.670 / 1.470.237) |
| `CREATE TABLE` | ✅ **denegat** (`permission denied for schema public`) |
| `DELETE FROM design` | ✅ **denegat** (`permission denied for table design`) |
| llegir taules d'`ftt_staging` | ✅ **denegat** (`permission denied for table tenants_client`) |
| llegir l'esquema de tenant `fhort` | ✅ **denegat** (`permission denied for schema fhort`) |

Privilegis: `SELECT` sobre `design`, `edge`, `panel`, `stitch`, `ingest_batch`. Res més.

🚩 **Dues coses menors per a l'Agus, cap d'elles bloquejant:**

1. **El fitxer `corpus_ro.pgpass` no és un `.pgpass`.** És un conninfo de libpq per paraules
   clau (`host=` / `port=` / `dbname=` / `user=` / `password=`, una per línia). Amb
   `PGPASSFILE` **no funciona**; s'ha de consumir com a cadena de connexió. El nom enganya.
2. **`corpus_ro` encara pot CONNECTAR a `ftt_staging`** (el `CONNECT` que `PUBLIC` té per
   defecte) i llegir-ne el catàleg, tot i que **cap taula de producte no li és accessible**.
   Si es vol tancar del tot: `REVOKE CONNECT ON DATABASE ftt_staging FROM PUBLIC;`.

> 🔒 **Higiene de secrets**: `corpus_ro.pgpass` porta la contrasenya en clar (té `0600`, bé) i
> `run_fetch.sh` porta el token del WebDAV **hardcodat** al cos de l'script. **Cap dels dos
> valors no es reprodueix en aquest report**; si el repo s'ha de compartir, el token vol sortir
> de l'script.

## 3.8 · `ATTRIBUTION.md` — al lloc i complet

A `/var/www/ftt-corpus/ATTRIBUTION.md`. Porta font, autors (els 8), editor (ETH Zurich Research
Collection), landing page, distribució feta servir, **llicència CC BY 4.0 amb enllaç**, la cita
formal, i —el que compta— una secció **«Changes made in this copy»** que diu que **no és un
mirall verbatim**: només es retenen `specification.json`, `pattern.svg` i `design_params.yaml`
gzipats, sense malles 3D ni renders ni models de cos. A més, **cada fila de `design` porta
`source_attribution`** (`NOT NULL`), o sigui que l'atribució viatja amb la dada i no només amb
el directori.

---

# FASE 4 · REPORT

## 4.1 · Pressupost real vs estimat

| concepte | estimat | **real** | desviació |
|---|---:|---:|---|
| **xarxa** | ~200 GB | **186,35 GB** | **−13,65 GB (−6,8%)** ✅ |
| **disc (raw)** | 1,6 GB | **1,6 GB** (`du`) | **clavat** ✅ |
| temps de baixada | — | **2 h 06 min 32 s** (7.592 s) | 36 lots |
| temps d'ingesta | — | **20 min 27 s** (1.227 s) | en paral·lel |
| finestra sencera | — | **16:24:59 → 18:31:52** (2 h 07 min) | |

- **Xarxa**: 186,35 GB en 398.010 fitxers de 36 lots, a `--limit-rate 25M`. L'estimació de
  ~200 GB era bona i **conservadora pel costat correcte**.
- **Disc**: la suma de `disk_bytes` dels logs dona **0,81 GB** de càrrega útil, i `du` en diu
  **1,6 GB**. **No es contradiuen**: són 398.010 fitxers petits i el sobrant és arrodoniment a
  bloc de 4K (≈2 KB × 398k ≈ 0,8 GB). **L'estimació d'1,6 GB era la del disc ocupat, i clava.**
- ⚠️ **El que el pressupost no deia**: la BD `ftt_corpus` ocupa **3.706 MB (3,62 GB)** a més
  del raw. **Petjada total ≈ 5,2 GB.** No és un problema (queden ~12 GB lliures a `/var/www`),
  però si algú va comptar 1,6 GB, el número de debò és tres vegades més.
- El driver mai va tocar el terra de seguretat: `free` va anar de 18 GB a 12,2 GB, sempre per
  sobre del `MINFREE=8` que hauria aturat la baixada.

## 4.2 · 🔑 LA CAIGUDA DEL SHARE — 16:06 → 16:23, i què la va absorbir de debò

**Això és el que el brief volia que quedés escrit.** Registre sencer, a
`/root/gcd_corpus/logs/libdrive_watch.log`:

```
2026-08-25T16:06:43Z rc=124 http=none
2026-08-25T16:09:08Z rc=124 http=none
2026-08-25T16:11:33Z rc=124 http=none
2026-08-25T16:13:58Z rc=124 http=none
2026-08-25T16:16:23Z rc=124 http=none
2026-08-25T16:18:48Z rc=124 http=none
2026-08-25T16:21:13Z rc=124 http=none
2026-08-25T16:23:14Z rc=0 http=200
2026-08-25T16:23:14Z LIBDRIVE UP http=200
```

**16 min 31 s de caiguda · 7 sondes mortes · recuperació neta.** El `rc=124` és el codi de
`timeout(1)`: `timeout 25 curl` matava cada intent als 25 s sense que `libdrive.ethz.ch`
digués res (`http=none`, ni tan sols un `000`). No era lentitud: **era silenci**.

### Qui la va absorbir — i aquí el brief s'ha de corregir

El brief l'atribueix al **resume**. **No va ser el resume: va ser el guaita.**

- `watch_libdrive.sh` sondeja cada 120 s i **només surt amb 0 quan el share respon**. El
  `run_fetch.sh` estava darrere seu, o sigui que **la baixada no va començar fins que hi va
  haver servidor**: `LIBDRIVE UP` a les **16:23:14**, primer `FETCH garments_5000_0` a les
  **16:24:59** — **1 min 45 s després**.
- El **resume per `_COMPLETE` no va disparar ni un cop**: `grep SKIP fetch.log` → **cap línia**,
  perquè cap lot estava baixat quan la correguda va arrencar. La màquina de resume **existeix i
  és sana** (36/36 marcadors escrits, `ingest_batch` amb 36 `complete`, i el `run_ingest.sh`
  només mira directoris amb `_COMPLETE`), però **en aquesta correguda no li va tocar treballar**.

> **La prova del disseny que en queda és una altra, i és més bona**: la caiguda no va costar ni
> un byte perquè **la porta estava tancada abans d'obrir l'aixeta**. Un pipeline que hagués
> començat a baixar a les 16:06 hauria escrit 7 lots corruptes o buits. El guaita va convertir
> 16 minuts de share mort en **1 min 45 s de retard i zero feina llençada**.

I un cop oberta l'aixeta, **cap incident més**: `grep -E "STOP|rc=" fetch.log` no torna res
llevat del `ALL BATCHES DONE` final, i els 36 lots tanquen amb `status=complete`.

## 4.3 · Distribucions

**Famílies de panel** (10 famílies, cap `other`) — recompte i àrea mitjana en cm²:

| família | panels | àrea mitjana |
|---|---:|---:|
| skirt | 273.721 | 2.496,0 |
| cuff | 247.800 | 169,7 |
| sleeve | 217.380 | 764,8 |
| torso_front | 185.726 | 886,0 |
| torso_back | 185.726 | 843,5 |
| waistband | 127.630 | 431,2 |
| skirt_insert | 79.998 | 377,1 |
| pant | 70.304 | 1.658,3 |
| collar | 67.176 | 115,7 |
| hood | 14.776 | 1.099,4 |

> `torso_front` i `torso_back` empaten a **185.726 exactes** — és la simetria del generador, no
> una casualitat: tot cos que porta davant porta darrere.

**Curvatura d'aresta** (9,82 M arestes):

| tipus | arestes | % |
|---|---:|---:|
| straight | 7.459.989 | 76% |
| quadratic | 840.971 | 9% |
| circle | 816.282 | 8% |
| cubic | 700.620 | 7% |

> **Tres de cada quatre arestes són rectes**, i només el 24% porta corba. Per a qualsevol
> classificador o mètrica de forma, és el desequilibri de classes que s'haurà de tenir present.

**`role_raw`** (3 valors, cap nul): body 581.034 · leg 466.547 · arm 422.656.

**Lots**: 36, de `garments_5000_0` a `garments_5000_35`, entre **3.367** i **3.885** designs
cadascun (mitjana 3.685).

## 4.4 · Rutes i checkpoints

| què | on |
|---|---|
| fitxers baixats | `/var/www/ftt-corpus/raw/garments_5000_<0..35>/` |
| per element | `*_specification.json.gz`, `*_pattern.svg.gz`, `*_design_params.yaml.gz` |
| manifest per lot | `_manifest.tsv.gz` |
| **marcador de lot baixat** | `_COMPLETE` — **36/36 escrits** |
| atribució | `/var/www/ftt-corpus/ATTRIBUTION.md` |
| BD | `ftt_corpus` al port **5433** (`postgresql@18-main`), **3.706 MB** |
| **checkpoint d'ingesta** | taula `ingest_batch` — **36 files, totes `complete`** |
| scripts | `/root/gcd_corpus/scripts/` |
| logs | `/root/gcd_corpus/logs/` (`fetch`, `ingest`, `libdrive_watch` + els `_driver`) |
| `ckpt/` | **buit** — mai fet servir; el checkpoint real són `_COMPLETE` + `ingest_batch` |

**Els dos checkpoints són independents i complementaris**: `_COMPLETE` diu «baixat» (el mira
`run_fetch.sh` per saltar-se lots i `run_ingest.sh` per no llegir directoris a mig escriure), i
`ingest_batch.status` diu «ingerit». Per això les dues fases van poder córrer **alhora** sense
trepitjar-se: l'ingest només entra on el fetch ja ha plantat bandera.

## 4.5 · Què queda habilitat

### ✅ Banc kNN per a F4/F5 — **verificat, no només declarat**

`scripts/knn.py` fa cerca de semblança en dues passades: **shortlist** per força bruta exacta
sobre els descriptors de 40 dimensions (1,4 M panels ≈ 230 MB float32, hi caben a RAM) i
**re-rank** pel contorn de 128 punts en marc canònic. Els canals 0 i 1 són escala absoluta
(log-àrea, log-perímetre) i `use_scale=False` els anul·la per a **cerca de forma pura**.

Provat de debò en aquesta sessió, amb un subconjunt:

```
Bank(where="family='collar'") → 67.176 panels · descriptor (67176, 40)
cap NaN al descriptor: True · API: query, rerank, contours, family, side, …
```

**Funciona.** I `sanity.py` ja garanteix que **cap dels 1.470.237 descriptors** té llargada
diferent de 40 ni mètriques no finites, o sigui que el banc sencer es pot construir sense sorpreses.

### ✅ Freqüències per a F3

`edge.curvature_type` + `edge.length_rel` + `panel.edge_signature` (indexat) donen les
distribucions de gramàtica d'aresta sobre 9,8 M d'arestes reals. La taula de §4.3 n'és la
primera lectura.

### ✅ Gimnàs v2

`/root/n2_gym/` amb el seu venv, i `sanity.py` ja importa `svgref` des de
`/root/n2_gym/scripts` — els dos arbres es parlen. El corpus li dona **1,47 M de panels reals
etiquetats per família i rol**.

### ✅ Biblioteca SVG

**398.010 fitxers**, dels quals **132.670 SVG de patró** gzipats, adreçables per
`design.svg_path` (comprovat: 20/20 obren i els `<path>` quadren amb `n_panels`).

---

## Advertiments per a qui hi construeixi a sobre

1. 🚨 **Desduplica a la lectura.** 3.696 designs són a BD dos cops (lots 12 i 13). Qualsevol
   estadística, entrenament o mostreig que no ho faci **sobrepondera aquests designs al doble**.
2. 🚨 **La `UNIQUE (batch, element_name)` no protegeix de duplicats entre lots.** És per disseny
   —permet re-ingerir un lot sense xocar— però vol dir que **`sanity.py` no els veu**. Si
   s'afegeixen lots nous, la comprovació de duplicats s'ha de fer per `element_name` sol.
3. ⚠️ **`garment_category` és nostra, no del dataset** (`ingest_batch.py:51`). Contra el doc
   oficial no compares corpus amb corpus: compares **la nostra frontera** amb la seva.
4. ⚠️ **76% de les arestes són rectes.** Desequilibri de classes a tenir present.
5. 🔒 El token del WebDAV és **hardcodat** a `run_fetch.sh` i la contrasenya de `corpus_ro` és
   en clar al seu fitxer. Cap dels dos no surt en aquest report.

---

## El que NO s'ha fet, expressament

- ❌ Cap baixada, cap re-ingesta, cap `CREATE INDEX` (ja hi eren tots vuit).
- ❌ **Cap esborrat dels 3.696 duplicats** — és una escriptura, i l'ordre no en porta cap.
  Queda com a decisió d'Agus (esborrar-los o deduplicar a la lectura).
- ❌ Cap canvi als scripts, ni al rol, ni al `pg_hba`.
- ✅ L'única escriptura d'aquesta correguda **és aquest fitxer**.
