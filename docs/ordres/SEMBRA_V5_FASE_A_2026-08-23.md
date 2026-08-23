# SEMBRA v5 · FASE A — codi i banc a `dev`

**Data:** 2026-08-23 · **Entorn:** `/var/www/ftt-staging`, branca `dev` · **Patró B**
**Brief:** `OPS/SEMBRA_V5` · **Substrat:** `CENS_CATALEG_V5_STAGING.md` (22/08) ·
`TREN_PANYS_2026-08-22.md` · `INSTANCIES_POSICIO_V2_2026-08-23.md` ·
`POMS_TABS_ACTIUS_2026-08-23.md`
**10 commits. Cap push. Cap migració. CAP escriptura a `ftt_staging`.**

> **PORTA D'ARRENCADA — OBERTA.** `origin/dev == dev` (res a fer amb el `git pull`) i les dues
> actes hi són: `25e4f648` (instàncies v2) i `665bfa0e` (tabs). Llegides totes dues abans de
> tocar res. La lliçó que s'ha aplicat d'elles: **el gate és PROPORCIONAL** i **una pk del
> brief és de PROD i no val aquí** (el cas #152→219, que en aquest tram torna a sortir).

---

# 🚨 PREMISSES DEL BRIEF QUE NO ES CONFIRMEN (al davant, com mana el brief)

## ① Quatre columnes del r2 **no tenen camp al model**, i el brief ja ho preveia

El brief diu: *«Si el model de POMGlobal no té camp per a CA/ES o per a alguna columna del r2:
PARAR i reportar el forat. No inventar schema.»* Censat camp a camp:

| Columna del r2 | Camp | Nota |
|---|---|---|
| Codi · Nom EN · Nom CA · **Nom ES** | `codi` · `nom_en` · `nom_ca` · **`nom_es`** | ✅ hi són tots |
| Fam. · UNITAT · ESTAT SEMBRA | `categoria` · `unitat` · `actiu` | ✅ |
| DES D'ON · FINS ON · REFERÈNCIA · SCOPE · ZONA | `start_point` · `end_point` · `reference_point` · `scope` · `body_section` | ✅ |
| TOL. PROD · TOL. MOSTRA | `tol_prod_cm` · `tol_samp_cm` | ✅ |
| Nota | `notes` | ✅ |
| **Pos.** | — | 🚩 `POMGlobal` no té `display_order` (`POMCategory` sí, però és de la FAMÍLIA) |
| **Règim** (Amplada·Llarg·Col·locació·Fix) | — | 🚩 cap camp, ni a `POMGlobal` ni a `POMMaster` |
| **Ancoratge** (Cota·Caiguda·Component·Tirada) | — | 🚩 cap camp |
| **Capa** (exterior·fornitura·folre) | — | 🚩 la capa és de la **PERTINENÇA** (`GarmentPOMMap.capa`, slug de `MeasurementLayer`), no del catàleg |
| **FONT DEF.** · **Origen** | — | 🚩 provenença; `iso_ref` és per a la ISO i `notes` és del patronista |

**No s'ha inventat cap camp i no s'ha abocat res a `notes`** — és exactament el que la sembra
v4 ja va decidir amb les mateixes tres columnes (`REPORT_SEMBRA_V4_2026-08-09.md` §3). El forat
**viu al codi**, a `sembra_v5/corpus.COLUMNES_SENSE_DESTI`, i **S2 el reporta a cada
correguda**: una acta es pot no llegir, un report de sembra no.

**Què cal per tancar-lo:** una migració que afegeixi `display_order`, `regim`, `ancoratge` i
`capa_defecte` a `POMGlobal`. **És un pre-tren propi i el decideix Agus.** La resta del tram
NO en depèn: el catàleg entra sencer menys aquestes quatre columnes.

## ② El «mapa 23→14 de lletres» **no existeix com a funció**, i el full ho diu

El brief diu que a S5 *«els 112 amb lletra van a la seva lletra nova (mapa 23→14 del r2)»*. Al
full `FAMILIES`, la columna «Prefixos de codi que hi viuen» reparteix:

```
prefix I  →  família I (Màniga) · família F (Llargs del cos) · família T (Tirants)
prefix U  →  família G (Acabats) · família U (Botonadura)
```

Un mapa lletra→lletra hauria d'ESCOLLIR, i escollir seria endevinar. **La família d'un POM és
la de la seva FILA al r2** —dada per POM, que el mateix brief cita per als 26+1—, i per això S5
la pren d'allà per a tothom i **depèn de S3**: sense lligam no hi ha fila.

## ③ 🚨 «El codi del tenant ja és un codi v5» és un PARANY — 16 casos mesurats

Cap frase del brief ho demana, però era la drecera evident per lligar els POMs que el mapa
Brownie no cobreix. **Està mesurat i és fals:** dels 16 POMs vius de `fhort` amb un codi que el
v5 també fa servir, **cap dels 16 vol dir el mateix**.

| codi | el tenant hi mesura | el v5 hi mesura |
|---|---|---|
| `E2` | Across front width (11 cm from HPS) | **Shoulder forward** |
| `M` | Leg opening | **Neck width** |
| `I4` | Sleeve length from CB over shoulder point | **1/2 bicep width** |
| `S2` | Back armhole along seam | **Across width** |
| `F1` | Side curve (CB length minus side seam) | **Body length** |
| … | *(11 més, totes divergents)* | |

I es veu per què: el r2 **mapa `EK → M` i `E4 → E2`**. Els dos vocabularis fan servir les
mateixes lletres per a mesures diferents. Lligar-los per coincidència hauria posat **16 POMs
sota el canònic equivocat, en silenci i amb totes les guardes en verd**. S3 no ho fa, ho
reporta amb el text de totes dues bandes, i hi ha un test que ho fixa.

## ④ A **staging**, S7 **no és el no-op** que el brief dona per fet

El brief diu *«NOMÉS PROD (a staging és no-op i ho ha de dir)»*. La meitat (b) sí que ho és —el
cens del 22/08 ja ho deia: 1 sol joc i és el supervivent—, però **la meitat (a) trobaria feina**:
tres models (**1320, 1322, 1383**) tenen FK al joc supervivent i les seves residents la fan
inerta. Per això, **sense cap joc condemnat, tallar FKs exigeix `--talla-fk-sense-condemna`**:
la FASE C corre S1→S6 i S7 no hi entra, i un tall silenciós a staging seria feina que ningú ha
demanat.

## ⑤ L'empremta v2 té **quatre** fitxers de detall, i el brief en demanava tres

Decisió presa i explicada al capdamunt de `ops/sembra_v5/empremta.py`: S2 escriu **165
definicions** («com es mesura» sencer i les dues toleràncies) que el bloc de POMs només veu pel
**codi** (`pom_global_codi`). Amb tres blocs, dos entorns amb el mateix lligam i **definicions
diferents** —una tolerància retocada a mà, un punt A reescrit— passarien el gate com a
**idèntics**. Un gate que no pot veure el que la sembra escriu no és el gate d'aquesta sembra.
**Si Agus prefereix els tres, es treu el bloc `globals` i el hash canvia; és una línia.**

## ⑥ Un ORDRE que el brief no podia saber: **S6 ressuscita el que S3 i S5 ja han passat**

`S` i `S2` arriben a S6 **inactius** —és el que S6 ve a arreglar— i **S3 i S5 només toquen els
VIUS**. Quan S6 els reactiva, els dos passos que els haurien lligat i classificat ja han
passat. Dues conseqüències, totes dues resoltes:

- S6 resol la família **pel mateix mapa del r2** que fa servir S3, i així el POM reactivat no
  es queda sense família;
- el report de S6 **demana la re-passada de S3 i S5**, que són idempotents. A l'assaig es va
  fer i va lligar exactament **1** POM més, sense moure res altre.

---

# QUÈ S'HA CONSTRUÏT

`ops/sembra_v5/` porta el material i l'empremta; les set comandes viuen a
`backend/fhort/pom/management/commands/` perquè és on Django les troba —el mateix repartiment
que `ops/sembra_v4/` + `sembra_cataleg_v4.py`— i el codi compartit, a `fhort/pom/sembra_v5/`.

| Commit | Peça |
|---|---|
| `316d164a` | **corpus + forma comuna** — hash, guardes de recompte, dry-run, abort |
| `c163f6dc` | **S1** `sembra_families_sistema` |
| `4caa6342` | **S2** `sembra_cataleg_sistema` |
| `c7bfbf67` | **S3** `lliga_fhort_al_sistema` |
| `33d076de` | **S4** `sembra_alies_brownie` |
| `ed42ad00` | **S5** `remap_families_fhort` |
| `114c7f57` | **S6** `tancament_142` |
| `c7661f04` | **S7** `finestra_graduacio` |
| `28bb3a03` | **S0** `ops/sembra_v5/empremta.py` |
| `40550072` | **el banc** — 32 tests |

## El corpus, i per què es verifica abans de llegir

`CATALEG_SISTEMA_POM_v5_COMPLET_r2.xlsx` viatja per **dos camins** (repo a staging,
`/root/cens_v5/material/` a PROD) i les dues meitats del gate final només valen si els dos
entorns han llegit **els mateixos bytes**. El sha256 es comprova **abans de llegir cap cel·la**
i, si no coincideix, **cap comanda arrenca**. Els recomptes del full (165 · 14 · 105 i 161+4)
són **guarda**, no documentació: una fila perduda en un desa d'Excel no es veu de cap altra
manera. També aborten els codis repetits, una família que el full `FAMILIES` no declari i un
àlies amb un destí que no és cap POM del catàleg.

## La guarda de recompte, i les dues cares que té

Cada comanda declara les xifres del brief (`ESPERAT`) i les contrasta **dins de l'`atomic()`**:

- en **DRY-RUN** una divergència es **reporta i la correguda segueix** — el dry-run és
  l'instrument de mesura, i aturar-lo a la primera xifra amagaria la resta del cens;
- **ESCRIVINT**, una divergència **ATURA** i la BD queda com era. Llavors o es corregeix la
  causa, o l'operador **declara la xifra mesurada amb `--espera NOM=N`**, que és un acte humà i
  consta al report.

Les xifres del brief són de PROD. A staging divergeixen totes, i és el que el report canta.

## Els panys, aplicats a tot el tram

Literal del brief i literal del tren del 22/08: **es crea el que falta i no es reescriu res del
que ja hi és**. Val a S1, a S2 camp a camp (també per a `notes`), a S3 (`separat_de_global` es
mira PRIMER; un lligam divergent es reporta i no es mou), a S4 (create-only) i a S5 (el text de
les 14 famílies del tenant). `--overwrite-from-xlsx` és l'única manera de reescriure, i quan
ho fa, **consta**.

## ⚖️ La llei de motor @girth, i com es mesura

*«Cap comanda crea NI CREARÀ regles de graduació sobre una instància @girth.»* Els 4 contorns
entren al catàleg com a vocabulari, **INACTIUS**, i sense cap regla. La prova no és una
inspecció: `LleiGirthTest` corre **el tram sencer** i mesura que `GradingRule` **no es mou ni
una fila**. A l'assaig sobre PROD el mateix va sortir sol — el hash del bloc `regles` és
**idèntic abans i després** (`e176e5e343783fc5…`).

## ☠️ L'única supressió, i per què vol guarda

`POMMaster.categoria` és **`SET_NULL`**: esborrar una categoria amb POMs a dins **no peta**,
els deixa orfes en silenci. Per això la candidata a esborrar és **la que té 0 POMs mesurats en
el moment real**, mai la que una llista diu que hauria d'estar buida. A l'assaig: **12 `CAT-*`
esborrades** (la xifra del brief, clavada) i **`CAT-UB` conservada amb els seus 84 POMs
d'arxiu** — mor amb l'arxiu, no aquí.

---

# EL VERD — proporcional, i per què no hi ha `npm run build`

| Control | Resultat |
|---|---|
| `manage.py check` | **net** (0 issues), abans de cada commit |
| `fhort.pom.test_sembra_v5` | **32 tests · OK** · 298 s |
| `npm run build` | **NO s'ha fet, a posta** |

**El build és desplegament, i aquest tren no toca frontend.** És la mateixa lectura que el tren
de panys del 22/08 va deixar escrita («aquest tren no toca frontend, i els gates també són
desplegament»): `npm run build` **publica `frontend/dist`**, que és el que staging serveix, i
publicar-lo sense cap canvi de front seria desplegar feina d'altri sense mirar-se-la. Zero
fitxers de `frontend/` tocats en els 10 commits.

**Com s'ha corregut el banc, i per què així.** BD de test **pròpia** (`test_ftt_sembra_v5`), amb
un shim que només canvia el nom, perquè `test_ftt_staging` és de tothom i hi ha sessions
concurrents:

```python
# <scratchpad>/settings_v5.py
from fhort.settings import *                              # noqa
DATABASES['default'].setdefault('TEST', {})['NAME'] = 'test_ftt_sembra_v5'
```
```
PYTHONPATH=<scratchpad> venv/bin/python manage.py test fhort.pom.test_sembra_v5 \
    --settings=settings_v5 --keepdb --noinput
```

⚠️ **I la trampa del 23/08, viscuda dues vegades:** una correguda interrompuda deixa el schema
`test` a mig migrar i la següent peta amb `column "capa" … already exists` o
`pg_type_typname_nsp_index`, un vermell que sembla teu i no ho és. La neteja és la de l'acta
d'instàncies, i funciona:

```sql
delete from tenants_domain where tenant_id in (select id from tenants_client where schema_name='test');
delete from tenants_client where schema_name='test';
drop schema if exists test cascade;
```

## El banc, cas per cas

| Classe | Què fixa |
|---|---|
| `CorpusTest` | el hash **aborta** amb un byte de més · els recomptes del full · el forat d'esquema declarat |
| `S1FamiliesTest` | les 14 a `public` · 2a passada = 0 canvis · el rebateig humà respectat · el dry-run no escriu |
| `S2CatalegTest` | els 165 · el «com es mesura» sencer · el pany camp a camp · **els 4 girth INACTIUS** |
| `S3LligamTest` | el lligam pel mapa · **un POM SEPARAT no es re-enganxa** · el lligam divergent no es mou · **el codi homònim no es lliga** · l'arxiu no · idempotència |
| `S4AliesTest` | create-only · l'àlies amb un altre destí no es mou · idempotència |
| `S5RemapTest` | el remapatge per fila · **l'arxiu no es reescriu** · `CAT-*` buida fora i `CAT-*` amb POMs es queda · idempotència |
| `S6TancamentTest` | **el cas 462/463 resolt pel CODI** (les pks del banc són unes altres i passa igual) · la família no s'endevina · el duplicat només s'anota |
| `S7FinestraTest` | el tall inert · **l'abort sencer quan deixa de ser inert** · l'arxivat sense cap `DELETE` · **sense supervivent, ATURA** · sense condemnats, no talla sense el flag |
| `LleiGirthTest` | ⚖️ el tram sencer no crea **cap** `GradingRule` |

---

# ANOTAT, FORA D'ABAST

| | Què | On |
|---|---|---|
| 🚩 | Els 4 camps que el r2 vol i `POMGlobal` no té → **pre-tren de migració, decisió d'Agus** | `corpus.COLUMNES_SENSE_DESTI` |
| 🚩 | El full `INSTANCIES` del r2 declara un **eix DATUM sencer** (12 slugs nous: `seam`, `edge`, `incl_band`, `girth`…). **El brief no el demana i no s'ha tocat** | full `INSTANCIES` |
| 🚩 | `docs/ordres/empremta_cataleg_v5.py` (v1) es **conserva**: és qui va produir la línia de base del 22/08. v1 i v2 **no són comparables entre elles** | `docs/ordres/` |
| 🚩 | Els **24 àlies LOS del lot C** queden fora d'abast, com el brief mana | — |

**Cap push. El merge i el desplegament els fa l'Agus.**
