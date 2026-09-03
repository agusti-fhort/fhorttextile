# Esborranys per a la sessió Montse — gimnàs N2, 2a passada

**Data:** 2026-08-25 · **Fil:** S46-MOTOR · Patró A
**Continua:** `INFORME_GIMNAS_N2_GARMENTCODEDATA_2026-08-25.md`
**Objectiu:** que la sessió amb la Montse passi de **construir** a **validar**.

> **Fronteres respectades.** Tota la feina viu a `/root/n2_gym/` amb venv propi.
> Cap `systemctl`, cap escriptura al repo ni a cap worktree, cap migració, cap
> escriptura a cap BD, cap `pip install` al venv del projecte, cap accés al
> vault. **Aquest fitxer és l'única escriptura fora de l'scratchpad.**
> Cap xoc amb la sessió paral·lela (fil S43).

> **🚧 ELS QUATRE LLIURABLES SÓN PAPERS DE TREBALL.** Tots quatre porten la
> capçalera «pendent de validació Montse». **Cap taxonomia no ha entrat al
> sistema**, i cap sortida no està en format llest-per-sembrar — són `.md` i
> `.csv` de treball, amb una columna buida per al vocabulari d'ofici.
> *(Llei LOSAN inline: «un artboard sense assignar no se sembra; mai s'endevina».)*

---

## 0 · El veredicte en set línies

1. **Els quatre lliurables són fets** i viuen a `/root/n2_gym/esborranys/` i
   `/root/n2_gym/svg_gti/`.
2. **La baixada nova va costar 1,808 GB de xarxa i 27,5 MB de disc** — molt per
   sota del sostre de 3 GB. Cobreix **1 200 elements**, no 600-800: mantenir els
   mateixos 1 200 de la 1a passada surt **igual de car** (el pes és el prefix
   del tar, no els fitxers que en desem) i estalvia tota la reestratificació.
3. 🚨 **La premissa del Lliurable 3 era falsa.** `vertex_labels.yaml` **no
   conté landmarks del patró pla**: són índexs del **mallat 3D**. La font real
   són les etiquetes de vora en 2D — i són **millors**.
4. 🔑 **L'HPS es deriva, i sense cap dada nova.** El pont entre l'escot i la
   sisa és **sempre una sola vora** (2 371 de 2 371, **100,00 %**): els seus dos
   extrems són l'HPS i la punta d'espatlla. **Toca directament el bloquejant
   A11** de `INFORME_CORPUS_I_AUTOANCORATGE_2026-08-24`.
5. 🔑 **La gramàtica de costura és quasi tancada:** 50 parelles rol↔rol a tot
   el corpus, i només 2 combinacions per sota de l'1 %. La mediana de **28
   costures per patró de la 1a passada queda VERIFICADA**.
6. 🚨 **Una costura no és sempre una unió**: n'hi ha tres menes (unió 28 268 ·
   pinça 5 496 · centre 2 659) i **la pinça només cau a quatre rols**, mai al
   davant de faldilla ni de pantaló.
7. 🚨 **Aquest corpus no pot ensenyar res sobre escalat.** Els 1 200
   `body_measurements.yaml` són **byte a byte idèntics**: un sol cos mitjà
   (172,0 cm). Tota la variació és de **disseny**, cap de **talla**.

---

## 1 · La baixada (rastre)

### 1.1 Mètode

El mateix de la 1a passada, dirigit a altres fitxers: WebDAV sobre el share
públic d'ownCloud descobert dins del PDF de documentació, llegit **en streaming**
sense escriure mai el tar al disc, desant només els membres volguts i **tallant
la connexió** en assolir el compte.

```bash
cd /root/n2_gym
./venv/bin/python scripts/stream_aux.py \
  --path GarmentCodeData_v2/garments_5000_0/default_body/data.tar.gz \
  --out data/b0_aux --limit 1200
```

Token del share: `4UtC8smtLOGwKoZ` · base `https://libdrive.ethz.ch/public.php/webdav/`.

### 1.2 L'estructura real **coincideix** amb la doc v2

Comprovat abans de baixar res (`scripts/probe_members.py`, 45 membres, 7 MB):
un directori per element, i a dins els 13 fitxers que la doc anuncia. **Aquesta
vegada la doc no menteix** (a la 1a passada sí, amb el DOI).

Per element, de 5,3 MB totals, el que volem en pesa **~25 KB**:

| fitxer | mida típica | el volem? |
|---|---:|---|
| `_design_params.yaml` | ~15 KB | ✅ |
| `_pattern.svg` | 5-9 KB | ✅ |
| `_vertex_labels.yaml` | 0,6-2 KB | ✅ |
| `_body_measurements.yaml` | 796 B | ✅ |
| `_sim.ply`, `_boxmesh.ply` | 0,8-1,6 MB **cadascun** | ❌ |
| `_render_*.png`, `_texture.png`, `_pattern.png` | 0,1-0,3 MB | ❌ |
| `_orig_lens.pickle`, `_sim_segmentation.txt` | 0,2-0,3 MB | ❌ |

### 1.3 🚨 Per què 1 200 i no 600-800

El brief demanava ~600-800 elements estratificats. **N'hem baixat 1 200, i no és
un excés: és el mateix cost.** El tar es llegeix **seqüencialment**, de manera
que arribar a l'element *N* obliga a llegir tots els bytes anteriors. Els
elements que caldria per a una mostra estratificada estan **escampats** pels
1 200 primers, així que el cost de xarxa és idèntic tant si en desem 700 com
1 200 — i el de disc puja de ~17 MB a 27,5 MB.

Guanyem tres coses i no en perdem cap:
- **La població és EXACTAMENT la mateixa** que la dels 1 200 `specification.json`
  de la 1a passada → tots els lliurables **s'uneixen sense cap pèrdua**.
- **Zero biaix d'estratificació**: no cal triar, hi són tots.
- L'estratificació es fa **a l'anàlisi**, on es pot refer sense tornar a baixar.

### 1.4 Les xifres

```
FI: elements=1200 fitxers=4800 membres_llegits=16801
    bytes_xarxa=1807745024 (1.808 GB)  bytes_disc=27452870 (27.5 MB)  temps=32s
```

| concepte | valor | sostre del brief |
|---|---:|---:|
| **xarxa** | **1,808 GB** | *(no acotat)* |
| **disc nou** | **27,5 MB** | 3 GB ✅ (0,9 %) |
| elements | 1 200 | 600-800 ✅ (superat, §1.3) |
| lots tocats | **1** (`garments_5000_0`, `default_body`) | — |
| disc total de `/root/n2_gym` | **685 MB** (608 el venv) | — |

**Estrats coberts** (per `garment_types` de `dataset_properties`):

| tipus | n | % | subcategories (`design.meta`) |
|---|---:|---:|---|
| dress | 446 | 37,2 % | 8 valors de `bottom` × 2 d'`upper` |
| upper_garment | 307 | 25,6 % | FittedShirt 207 · Shirt 100 |
| skirt | 282 | 23,5 % | 7 valors de `bottom` |
| pants | 97 | 8,1 % | Pants |
| jumpsuit | 68 | 5,7 % | FittedShirt 43 · Shirt 25 |

Un sol lot: el lot **només fixa el material de drapejat**, que no afecta el
patró pla (establert a la 1a passada). Les proporcions coincideixen amb les
publicades per al dataset sencer.

---

## 2 · Lliurable 1 · Plantilla anatòmica

📄 `/root/n2_gym/esborranys/PLANTILLA_ANATOMICA_ESBORRANY.md`
📊 `out/plantilla_anatomica.csv` · `out/plantilla_variants.csv` (333 files)
⚙️ `scripts/plantilla_anatomica.py`

**Mètode.** Per tipus de peça i per subcategoria, es compta quins **rols** de
panell hi surten, en quin **% de patrons**, i quants n'hi ha de mitjana. Tres
graus declarats: **NUCLI** (≥ 90 %), **comuna** (25-90 %), **rara** (< 25 %).
Els **eixos de variant** es descobreixen **automàticament** (totes les fulles de
`design_params` de tipus `select`/`select_null`/`bool`), no d'una llista a mà.

**Troballes:**

- 🚨 **La faldilla és l'únic tipus SENSE cap casella de NUCLI.** Les seves
  subcategories no comparteixen anatomia: `SkirtManyPanels` es fa de
  `skirt_panel` (fins a **15** galls), `GodetSkirt` de `skirt_*` + `ins_skirt_*`.
  **La plantilla de faldilla s'ha de definir per subcategoria.**
- **La granota no té cap casella pròpia**: és cos + pantaló, i el catàleg de
  costures ho confirma (§3). Per al motor, **composició, no plantilla nova**.
- Un `upper_garment` porta panells `skirt_*` en el 30,6 % dels casos: al
  vocabulari del dataset, «faldilla» és **una peça de baix cosida a un cos**.
- 🚨 **`design_params` porta sempre l'arbre SENCER de paràmetres**, faci servir
  la peça aquella branca o no: una faldilla porta un `sleeve.armhole_shape`
  mostrejat que no fa servir ningú. Comptar-lo sobre tots els patrons del tipus
  donaria un **percentatge fals**. Cada eix té ara una **porta d'aplicabilitat**
  declarada i el CSV dona `n_patrons_on_l_eix_APLICA` al costat del tant per cent.

**Contrast del comptador de panells amb la doc oficial:**

| | min | mediana | mitjana | màx |
|---|---:|---:|---:|---:|
| doc v2 (5 000 del lot) | 2 | 12,0 | 12,1 | 35 |
| la nostra mostra (1 200) | 2 | 10,0 | 10,90 | 34 |

> El brief deia «min 2 · avg 10,9 · max 37». El **10,9 és la mitjana de la
> mostra, no la del dataset** (la doc en diu 12,1) i **el màxim publicat és 35,
> no 37**.

---

## 3 · Lliurable 2 · Parelles de costura

📄 `/root/n2_gym/esborranys/PARELLES_COSTURA_EMPIRIQUES.md`
📊 `out/parelles_costura.csv` (161 files) · `out/parelles_resum.txt`
⚙️ `scripts/parelles.py` — **cap xarxa**, només els 1 200 specs de la 1a passada

**Mètode.** Cada `stitch` és una parella `[{panel,edge},{panel,edge}]`. Es
canonicalitza cada panell al seu **rol** (la derivació de la 1a passada) i es
compta per tipus de peça. **La mediana de 28 costures per patró queda
verificada** (mitjana 30,65; rang 2-90; 36 423 costures en total).

**Troballes:**

- 🚨 **Tres menes de costura, que el matcher ha de separar d'entrada:**

  | mena | definició | n |
  |---|---|---:|
  | `UNIO` | dos panells de rols diferents | 28 268 |
  | `PINCA` | dues vores del **mateix** panell | 5 496 |
  | `CENTRE` | mateix rol, lateralitat oposada | 2 659 |

  Sense la distinció, una pinça del davant compta com una unió davant↔davant i
  el graf dirà que un panell **es cus amb ell mateix**.

- 🔑 **La pinça només viu a quatre rols:** `ftorso` (1 840), `btorso` (1 840),
  `skirt_back` (1 156), `pant_b` (660). **`skirt_front` i `pant_f` no en porten
  MAI.** La 1a passada va concloure que *el bit davant/darrere no és al
  contorn*; **aquí n'hi ha un tros, i és al graf de costures.**
- 🔑 **La gramàtica és quasi tancada:** 50 parelles rol↔rol distintes; només 2
  combinacions tipus×parella per sota de l'1 %.
- **Tres ancores al 100 %:** `btorso`↔`ftorso`, `pant_b`↔`pant_f`, i a la
  faldilla `skirt_back`↔`skirt_front` (89,7 %). Un matcher que hi comenci té el
  patró ancorat abans de mirar cap forma.
- **La simetria del catàleg és perfecta** (`ftorso`↔`sleeve_f` 275 patrons /
  `btorso`↔`sleeve_b` 275). **Una asimetria en un patró real és senyal d'error
  de lectura**, no de disseny exòtic.
- La granota afegeix **una sola parella nova** al cos i el pantaló:
  `ftorso`↔`pant_f` (48,53 %), la costura de cintura quan no hi ha cinturilla —
  i el 48,53 % de granotes tenen `meta.wb = cap`.

---

## 4 · Lliurable 3 · Vocabulari de landmarks

📄 `/root/n2_gym/esborranys/VOCABULARI_LANDMARKS_ESBORRANY.md`
📊 `out/landmarks_regions_3d.csv` · `out/landmarks_vores_2d.csv` ·
`out/landmarks_junctures.csv` · `out/hps_pont.csv`
⚙️ `scripts/landmarks.py` · `scripts/hps.py`

### 4.1 🚨 La premissa del brief no es compleix

El brief demanava el vocabulari «dels `vertex_labels.yaml`». **Aquests fitxers
no contenen landmarks del patró pla**: contenen índexs de vèrtex del **mallat 3D
simulat**. La mesura que ho sentencia:

| element | panells | vèrtexs **2D totals** | índex **màxim** a `vertex_labels.yaml` |
|---|---:|---:|---:|
| `rand_00YONAPXZE` | 18 | 116 | 847 |
| `rand_033UAN6C0K` | 12 | 76 | **13 030** |
| `rand_023FMIGQK0` | 14 | 64 | **15 691** |

Un patró amb 64 vèrtexs no pot tenir un vèrtex 15 691.

**Adaptació declarada:** el vocabulari surt de les **etiquetes de vora en 2D**
del `specification.json` — les mateixes 6 paraules (`lower_interface`,
`left/right_collar`, `left/right_armhole`, `strapless_top`), però ancorades al
patró pla. **5 856 panells de 13 078 (44,78 %)** en porten alguna.

### 4.2 🔑 L'HPS es deriva — i toca el bloquejant A11

Les 6 etiquetes són **vores**; els landmarks del §3.3 són **punts**. El pont
entre les dues coses és la **juntura**: al bucle tancat de vores, on acaba una
tirada d'etiqueta i en comença una altra hi ha un **vèrtex compartit**.

Cap juntura és mai `collar`^`armhole`: **l'escot i la sisa no es toquen**.
Entremig hi ha la **costura d'espatlla**, i n'hem mesurat la llargada pel camí
curt del bucle:

```
    pont d'1 vora : 2371  (100,00 %)     btorso 1452 · ftorso 919
```

**2 371 de 2 371.** La costura d'espatlla és **sempre** una sola vora, de manera
que en tot panell de tors amb escot i sisa:

| punt | definició mecànica |
|---|---|
| **HPS** | l'extrem de la vora d'espatlla que toca la tirada d'**escot** |
| **punta d'espatlla** | l'altre extrem, el que toca la tirada de **sisa** |
| **fons de sisa** | l'extrem llunyà de la tirada de sisa (desempat per alçada) |
| **extrem d'escot** | l'extrem llunyà de la tirada d'escot |

> `INFORME_CORPUS_I_AUTOANCORATGE_2026-08-24` §A11 diu: *«cap dada del sistema
> identifica els HPS: no hi ha ni rol de punt ni landmark batejat»*, i per això
> el mode ortogonal no es pot proposar. **Sobre patrons amb etiquetes de vora,
> l'HPS es deriva amb una regla de dues línies i sense cap ambigüitat.**
> ⚠️ **El que això NO diu:** que els patrons d'FTT portin aquestes etiquetes.
> Aquí les posa el generador. **Si el CAD d'on venen els nostres patrons en
> marca cap d'equivalent és una pregunta per a l'Agus, no per a la Montse.**

- ⚠️ **`lower_interface` és ambigu:** la mateixa paraula marca **la cintura**
  (a `wb_back`) **i el baix** (a `skirt_*`, `pant_*`). El desempat és el **rol**
  del panell, que el dona el Lliurable 1.

---

## 5 · Lliurable 4 · Paquet SVG per a la Biblioteca GTI

📁 `/root/n2_gym/svg_gti/` — **60 fitxers**, 452 KB · `INDEX.csv` · `LLEGEIX-ME.md`
⚙️ `scripts/svg_gti.py`

**Mètode.** Una cel·la = tipus × subcategoria (`design.meta`) × variant (màniga
per a les peces amb cos; llargada per a les de baix). Cel·les amb < 4 elements
descartades. **Representant** = l'element amb el nombre de panells **més proper
a la mediana de la cel·la**, desempat alfabètic. **Cap aleatorietat: no cal
seed**, és reproduïble per construcció.

Noms llegibles: `upper-garment__FittedShirt__long-sleeve.svg`,
`skirt__GodetSkirt__midi.svg`, `dress__sense-baix__sleeveless.svg`…
L'`INDEX.csv` dona per fitxer: tipus, subcategoria, variant, nombre de panells,
paràmetres clau (escot, component de coll, puny, cinturilla), **l'element
d'origen per a citació** i la columna buida per a la Montse.

> ⚠️ **Desviació declarada:** el brief demanava ~25-40 fitxers. En surten **60**
> perquè hem creuat **subcategoria × variant** i no només subcategoria — que és
> el que el mateix brief demanava al nom d'exemple (`dress_long-sleeve_maxi.svg`,
> tres eixos). Pesa 452 KB i dona a la Montse **cada variant a la vista**.
> Reduir-ho a ~35 és treure l'eix de variant i és una línia de l'script.

**NO s'integra enlloc**: és matèria primera per a la Biblioteca GTI (M7) i per a
l'horitzó patró-primer.

---

## 6 · 🚨 Què NO cobreix el dataset (límits, per saber-ho d'entrada)

Perquè la sessió Montse no hi ensopegui a mitja conversa:

| forat | estat | evidència |
|---|---|---|
| **Infantil i nadó** | **absent, i estructuralment impossible en aquesta meitat** | els 1 200 `body_measurements.yaml` són **byte a byte idèntics**: un sol cos adult (**172,0 cm**, pit 99,8). `body_default: mean_all` |
| **Petos** (amb pitrera i tirants) | **absent** | `jumpsuit` és sempre **tors sencer + pantaló**; no hi ha cap variant de pitrera |
| **Bodies** | **absent** | cap tancament d'entrecuix; el catàleg de costures no té cap parella que hi correspongui |
| **Auxiliars DEREK** | **absent** | el vocabulari és de 24 rols de peça; no hi ha butxaques, vistes, entreteles, cintes ni folres |
| **Escalat / graduació** | 🚨 **absent, i és el forat gros** | tota la variació de `default_body` és de **disseny**, cap de **talla** |
| **Màniga muntada contra raglan/kimono** | només **muntada** | `sleeve_f`/`sleeve_b` sempre cosits a `ftorso`/`btorso` per la sisa |
| Butxaques, tanques, ullals, plecs | **absents** | no hi ha cap rol de panell que hi correspongui |

> 🚨 **El límit que més pesa per a FTT.** Els 1 200 patrons estan **tallats tots
> per al mateix cos**. Aquest corpus serveix per a **reconèixer anatomia i
> costures**; **no serveix per a res que tingui a veure amb graduació**, que és
> el nucli del negoci. Per a variació de cos caldria la meitat `random_body`
> (5 000 cossos), **deliberadament fora d'abast** en aquest brief.

**Un forat de vocabulari, no de dades:** els noms del dataset són de generador
(`wb`, `sl_cuff_skirt_f`, `ins_skirt`, `skirt_panel`). **El pont cap a l'ofici
és exactament el que aporta la Montse**, i és la columna buida dels quatre CSV.

---

## 7 · Llicència i citació

> ⚠️ **Correcció al brief.** El brief deia «MIT + citació ECCV 2024». **MIT és
> la llicència del CODI de GarmentCode.** El que hi ha aquí són **DADES**, i el
> registre de l'ETH Research Collection les publica sota
> **Creative Commons Attribution 4.0 International (CC-BY-4.0)**
> (`http://creativecommons.org/licenses/by/4.0/`, camp `dc.rights.license` de
> l'ítem `9d16a4da-0d30-4963-8842-af20fcf82899`). **CC-BY-4.0 obliga a atribuir.**

```bibtex
@inproceedings{GarmentCodeData2024,
  author = {Korosteleva, Maria and Kesdogan, Timur Levent and Kemper, Fabian and
            Wenninger, Stephan and Koller, Jasmin and Zhang, Yuhan and
            Botsch, Mario and Sorkine-Hornung, Olga},
  title = {{GarmentCodeData}: A Dataset of 3{D} Made-to-Measure Garments
           With Sewing Patterns},
  booktitle = {Computer Vision -- ECCV 2024},
  year = {2024},
  keywords = {sewing patterns, garment reconstruction, dataset}
}
```

La citació completa és a `svg_gti/LLEGEIX-ME.md` i a **cada fila** de
`svg_gti/INDEX.csv`.

---

## 8 · Rutes de tot

| què | on |
|---|---|
| **Lliurable 1** · plantilla anatòmica | `/root/n2_gym/esborranys/PLANTILLA_ANATOMICA_ESBORRANY.md` |
| **Lliurable 2** · parelles de costura | `/root/n2_gym/esborranys/PARELLES_COSTURA_EMPIRIQUES.md` |
| **Lliurable 3** · vocabulari de landmarks | `/root/n2_gym/esborranys/VOCABULARI_LANDMARKS_ESBORRANY.md` |
| **Lliurable 4** · paquet SVG (60 fitxers) | `/root/n2_gym/svg_gti/` + `INDEX.csv` + `LLEGEIX-ME.md` |
| CSV de suport | `/root/n2_gym/out/plantilla_{anatomica,variants}.csv`, `parelles_costura.csv`, `landmarks_*.csv`, `hps_pont.csv` |
| Dades noves (27,5 MB) | `/root/n2_gym/data/b0_aux/` (4 800 fitxers + `_manifest.tsv`) |
| Dades de la 1a passada | `/root/n2_gym/data/b0_default/` (1 200 specs) |
| Traça de la baixada | `/root/n2_gym/logs/stream_aux_b0.log` |

**Scripts nous d'aquesta passada** (tots a `/root/n2_gym/scripts/`):

| script | què fa |
|---|---|
| `probe_members.py` | llista membres del tar remot sense desar res (§1.2) |
| `stream_aux.py` | baixada dirigida dels 4 fitxers auxiliars (§1.1) |
| `plantilla_anatomica.py` | Lliurable 1 |
| `parelles.py` | Lliurable 2 |
| `landmarks.py` · `hps.py` | Lliurable 3 |
| `svg_gti.py` | Lliurable 4 |

**Reproducció completa des de l'estat de la 1a passada:**

```bash
cd /root/n2_gym
./venv/bin/python scripts/stream_aux.py \
    --path GarmentCodeData_v2/garments_5000_0/default_body/data.tar.gz \
    --out data/b0_aux --limit 1200
./venv/bin/python scripts/plantilla_anatomica.py
./venv/bin/python scripts/parelles.py
./venv/bin/python scripts/landmarks.py
./venv/bin/python scripts/hps.py
./venv/bin/python scripts/svg_gti.py
```

Cap d'aquestes ordres no fa servir cap seed: **tots els números són recomptes
exhaustius** sobre els mateixos 1 200 elements, i el representant de cada cel·la
del paquet SVG es tria per mediana amb desempat alfabètic. Reproduïbles bit a bit.

---

## 9 · Les preguntes que la sessió Montse ha de tancar

1. **Els graus** NUCLI/comuna/rara (90 % i 25 %): ¿són els talls de l'ofici?
2. **La faldilla sense nucli**: ¿plantilla per subcategoria, o hi ha un nom
   d'ofici que cobreix galls, godets i davant/darrere alhora?
3. **Les tres menes de costura**: ¿pinça / centre / unió són els talls bons?
4. **La pinça només al darrere**: ¿llei d'ofici o biaix del generador?
5. **`lower_interface`**: ¿cintura i baix són dos landmarks o un?
6. **Escot esquerre i dret**: ¿un POM mesurat un cop, o dos?
7. **El vocabulari sencer**: la columna `VOCABULARI_OFICI_MONTSE` dels quatre CSV.
