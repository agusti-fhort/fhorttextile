# SEMBRA v5 · FASE C — STAGING AMB EL CATÀLEG v5 VIU

**Data:** 2026-08-23 · **Entorn:** `/var/www/ftt-staging`, branca `dev`, BD `ftt_staging`,
tenant **`fhort`** · **Patró B**
**Autoritza:** OK d'Agus amb sis decisions (*Diagnosis/SEMBRA_V5_FASES_AB* del vault) + brief
`SEMBRA v5 — TANCAMENT END-TO-END SENSE SUITES`.
**Cap push. PROD no s'ha tocat. `los` no s'ha tocat.**

> **GATE D'AQUEST TRAM, tal com Agus el va tancar:** `manage.py check` + `test_sembra_v5` + les
> verificacions read-only. **Cap altra suite.** El que hi ha aquí sota és això i res més.

---

# EL RESULTAT, EN UNA TAULA

| | abans | després |
|---|---|---|
| `POMGlobal` a `public` | 125 | **290** (125 vells intactes + **165 del v5**) |
| `POMGlobal` a `fhort` | **0** | **165** |
| POMs vius amb canònic | **0** | **89** de 144 |
| POMs vius amb «com es mesura» a la fitxa | **0** | **89** |
| Famílies del v5 al tenant, amb rètol i ordre del r2 | 0 | **14** |
| Àlies de Brownie | 101 | **154** (+53) |
| `S` i `S2` (462/463 a PROD) | actius, família `S` | actius, **família `A` · Pit i sisa** |
| Models amb FK de graduació inerta | 3 | **0** (tallades) |

**Empremta d'staging, post-sembra:**

```
poms       144   38d71f3b8a4a3068060ab0e75d516864…
regles     142   df4e18a8f88548c244b03f090c6fddd4…
families    25   354ea4971cbb89c80d57a5c64fba67d7…
globals    165   f08873ed83dd206cbcbf574310ce6a54…

HASH SEMBRA (EL GATE)  6637686664c678d0e9534532cbc0e301a526c57f8f9dccac8294361dd28d0483
hash global (context)  f4240c1cfe8f414df14f8666002651bfce23e4a3eb18c5c2effe2256b04d860c
```

`hash_sembra` = **famílies + globals**, que és el que la sembra escriu (decisió 6). És el que
PROD haurà de reproduir a la FASE D. El `hash global` hi és com a context i **no és el gate**:
inclou tot el `POMMaster`, i els dos entorns arrenquen de catàlegs diferents (144 files vs 521).

---

# 1 · PRE-TREN — `pom/0081`, mostrat, aplicat i auditat

Additiva, de l'espècie 0078, quatre columnes amb el default buit:

```sql
ALTER TABLE "pom_pomglobal" ADD COLUMN "ancoratge"     varchar(20) DEFAULT '' NOT NULL;
ALTER TABLE "pom_pomglobal" ADD COLUMN "capa_defecte"  varchar(20) DEFAULT '' NOT NULL;
ALTER TABLE "pom_pomglobal" ADD COLUMN "display_order" smallint    DEFAULT 0  NOT NULL CHECK (>= 0);
ALTER TABLE "pom_pomglobal" ADD COLUMN "regim"         varchar(20) DEFAULT '' NOT NULL;
```

Aplicada amb `migrate_schemas` (**mai `--schema`**) i auditada amb `SELECT`:

```
 table_schema | columnes_noves        app |               name               |          applied
--------------+----------------      -----+----------------------------------+--------------------------
 fhort        |      4                pom | 0081_sembra_v5_cataleg_pomglobal | 2026-08-23 10:37:58+00
 los          |      4
 public       |      4
```

Commit `814a8fbf` — **aplicada i commitada alhora**, que és la llei (una migració aplicada i no
commitada és una divergència BD↔repo que cap gate detecta).

🔑 **`capa_defecte` i no `capa`**: la capa és de la PERTINENÇA (`GarmentPOMMap.capa`, slug de
`MeasurementLayer`); el catàleg només la PROPOSA. Un camp dit `capa` en un POM global es
llegiria com «la capa d'aquesta mesura», que és fals.

---

# 2 · FASE C — ESPERAT vs REAL, comanda a comanda

Ordre: **dry-run de les set → llegir → `--no-dry-run` → segona passada → empremta.** Cap guarda
va abortar; cap comanda va tornar RC≠0.

| # | comanda (amb els flags decidits) | esperat | real |
|---|---|---|---|
| **S1** | `sembra_families_sistema --overwrite-from-xlsx` | 14 del corpus ✅ | **14 creades** a `public` · 15 alienes no tocades |
| **S2** | `sembra_cataleg_sistema --schema public --schema fhort` | 165 · 161 ACTIU · 4 INACTIU ✅ | **165 creats a `public`** i **165 a `fhort`** · 0 divergents · 125 de fora del v5 no tocats |
| **S3** | `lliga_fhort_al_sistema --schema fhort` | — | **89 lligats** · 0 sobirans · 0 lligams divergents · **16 nom divergent (full)** · **16 homònims** · **23 sense cap codi v5** |
| **S4** | `sembra_alies_brownie --schema fhort` | 105 al corpus ✅ | **53 creats** · 34 ja correctes · **3 amb un altre destí (no moguts)** · 15 sense POM lligat · 0 ambigus |
| **S5** | `remap_families_fhort --schema fhort --overwrite-from-xlsx --espera "CAT-* buides esborrades=0"` | 0 `CAT-*` ✅ | **24 remapats** · 65 ja hi eren · 55 sense fila · **14 famílies reescrites amb el text del r2** |
| **S6** | `tancament_142 --schema fhort --categoria A` | 2 trobats ✅ | **2 ja actius** · **família `A` posada als dos** · 1 fusió pendent anotada (`SF` pk 1015, 17 mesures) |
| **S7** | `finestra_graduacio --schema fhort --talla-fk-sense-condemna --espera …` | 3 talls · 0 arxivats ✅ | **3 FK tallades** (les 3 inertes) · **0 jocs arxivats** (a staging no n'hi ha cap de condemnat) · **cap `DELETE`** |

## Segona passada — **zero canvis a totes set**

```
S1  creades 0 · iguals 14            S5  remapats 0 · ja hi eren 89
S2  creats 0 · iguals 165 (×2)       S6  reactivats 0 · ja actius 2
S3  lligams NOUS 0 · ja lligats 89   S7  FK tallades 0 · arxivats 0
S4  creats 0 · iguals 87
```

## 🚨 Les xifres del brief que no es confirmen a staging (i per què)

Totes tres són **d'història d'entorn**, no defectes, i ja constaven a l'acta de la FASE B:

| brief | staging | per què |
|---|---|---|
| 12 `CAT-*` buides s'esborren | **0** | a staging no n'hi ha cap `CAT-*`; la neteja del 09/08 ja va deixar 25 famílies de lletra |
| 27 jocs arxivats | **0** | a staging hi ha **un sol** `GradingRuleSet` i és el supervivent |
| 25 models amb FK tallada | **3** | a staging només 3 models tenen FK, i les tres eren inertes |

Les tres es van declarar amb `--espera`, que és un acte humà i consta al report de cada comanda.

---

# 3 · LES CINC EVIDÈNCIES — servei viu, `staging.fhorttextile.tech` → `127.0.0.1:8001`

> El **restart va abans** de les evidències, contra l'ordre del brief i a posta: **un gunicorn
> serveix el codi de quan va arrencar**, i verificar contra el procés ranci no hauria provat res
> del que la Montse rebrà. Tot el que hi ha aquí sota és **posterior** al restart.

## (a) `/poms` — les 14 famílies amb el rètol i l'ordre del r2 · `GET /api/v1/pom-categories/` → **HTTP 200**

```
 1. E   Coll, escot, espatlla i canesú   | Neck, neckline, shoulder and yoke
 2. A   Pit i sisa                       | Chest and armhole
 3. I   Màniga                           | Sleeve
 4. F   Llargs del cos                   | Body lengths
 5. B   Cintura                          | Waist
 6. C   Maluc, cuixa i entrecuix         | Hip, thigh and crotch
 7. D   Baix, camal i peu                | Bottom, leg and foot
 8. Q   Talls, pinces i plecs            | Cuts, darts and pleats
 9. G   Acabats i vores                  | Finishes and edges
10. U   Botonadura i tancaments          | Button stand and closures
11. T   Tirants, tapetes i trabilles     | Straps, tabs and loops
12. R   Butxaca                          | Pocket
13. H   Caputxa i cap                    | Hood and head
14. N   Elements aplicats i fornitures   | Applied elements and trims
(+ 11 famílies velles que el v5 no toca: J K L M P S V W X Y Z)
```

## (b) La fitxa d'un POM lligat · `GET /api/v1/poms/921/` → **HTTP 200**

```
  pom_code           'E'
  pom_global_codi    'E'                       ← el lligam que S3 ha escrit
  categoria_nom      'Coll, escot, espatlla i canesú'
  unitat             'cm'
  scope              'FULL'          body_section  'BACK'
  start_point        'Shoulder seam (left)'
  end_point          'Shoulder seam (right)'
  reference_point    'Across top of back, seam end to seam end'
  tol_prod_cm        '0.75'          tol_samp_cm   '0.50'
```

🚨 **I el POM que el brief posava d'exemple —`A`— és precisament un dels 16 que NO es lliguen.**
`GET /api/v1/poms/904/` torna `pom_global_codi: null` i el «com es mesura» **buit**: el tenant
en diu *«1/2 chest width (armpit to armpit)»* i el v5, *«Chest width (armpit to armpit)»*. La
decisió 2 mana no lligar-los, i és per això que **55 dels 144 POMs vius encara no tenen fitxa
tècnica** (§5). Que el primer POM que un obriria sigui un d'aquests no és casualitat: els 16
són dels més usats.

## (c) El nom CA/ES — **hi és a la BD, i la cascada de la casa el tapa**

```
E:  global nom_ca='Espatlla a espatlla' · nom_es='Hombro a hombro'   ← el v5 SÍ que és a la BD
    noms_de() → {'nom_en': 'Shoulder to shoulder', 'nom_ca': 'Shoulder to shoulder'}
B:  global nom_ca='Ample de cintura'   · nom_es='Ancho de cintura'
    noms_de() → {'nom_en': 'Waist width', 'nom_ca': 'Waist width'}

Amb el mateix POM SENSE `nom_client` propi:
    noms_de() → {'nom_en': 'Shoulder to shoulder', 'nom_ca': 'Espatlla a espatlla'}
```

**No és un defecte de la sembra: és la llei de `nomenclatura.noms_de`** (documentada al seu
propi docstring) — `nom_ca` = descripció LOCAL de l'àlies **>** `nom_client` del tenant **>**
`nom_ca` del global. Com que els 144 POMs de `fhort` tenen `nom_client` propi (en anglès, de
Brownie), **el català del v5 mai guanya**. La tercera línia de la cascada ara existeix, que
abans no: qualsevol POM sense nom propi ja surt en català.

🚩 **DECISIÓ QUE ES DEIXA A AGUS.** Perquè la Montse vegi els noms catalans del v5 a `/poms`,
algú ha de decidir **substituir el `nom_client` dels 89 POMs lligats** — i això és un
**rebateig**, exactament el que el tren de panys del 22/08 va tancar sense flag explícit. No
s'ha fet. *(La traducció de domini viu al TRAM ⓘ — `/api/v1/translate/pom/` + `TranslationCache`
al tenant —, que aquesta sembra no toca.)*

## (d) `S` i `S2` — actius i amb família `A` · `GET /api/v1/poms/1012|1013/` → **HTTP 200**

```
 pk=1012 codi='S'  nom='Front armhole along seam' actiu=True família='Pit i sisa' (id 57)
 pk=1013 codi='S2' nom='Back armhole along seam'  actiu=True família='Pit i sisa' (id 57)
```

*(A PROD són 462 i 463. Aquí són 1012 i 1013, i la comanda no fa servir cap pk: llei R-POM.)*

## (e) El joc de graduació · `GET /api/v1/grading-rule-sets/` → **HTTP 200**

```
 jocs: 1
  pk=219 'GRADING BROWNIE 2026' actiu=True regles=142
```

**Intacte i actiu, amb les seves 142 regles.** No n'hi ha cap altre per arxivar: a staging la
neteja del 09/08 ja va deixar aquest sol. I l'empremta ho confirma pel camí llarg — el hash del
bloc `regles` és `df4e18a8…` **abans i després** de la sembra: ⚖️ el tram no ha tocat **cap**
regla de graduació, que és la llei de motor @girth escrita en un hash.

---

# 4 · SERVEI

```
systemctl restart ftt-staging
● ftt-staging.service — FTT Staging — Gunicorn
   Active: active (running) since Sun 2026-08-23 11:34:26 UTC
   Status: "Gunicorn arbiter booted"   Main PID: 3682401
```

Cap `npm run build`: aquest tram **no toca frontend** i el build publica `frontend/dist`.

---

# 5 · LA CRIBA FINA — el que queda per a la Montse

**89 dels 144 POMs vius tenen canònic. Els altres 55 estan en tres piles**, i cap no s'ha tocat.

## A · El full els aparella, però es diuen coses diferents (16)

Aquests **tenen destí al v5** i només els falta que algú confirmi que parlen de la mateixa
mesura. **És la pila que més val la pena mirar primer**: són 16 POMs molt usats.

| codi | el tenant en diu | → v5 | el v5 en diu |
|---|---|---|---|
| `A` | 1/2 chest width (armpit to armpit) | `A` | Chest width (armpit to armpit) |
| `EK2` | Back neck drop from HPS | `M3` | Neck drop from HPS |
| `EKK` | Back neckline width | `M7` | Neckline width |
| `F` | Centre front length from HPS | `F` | Total length from HPS |
| `FS5` | Lining length difference | `F4` | Llength difference |
| `I2` | Sleeve hem width | `I2` | Sleeve opening |
| `I5` | Elbow position from CB over shoulder point | `I14` | Elbow position over shoulder point |
| `L` | Back yoke width | `P` | Yoke width |
| `N` | **Motive placement** | `N5` | **Reflective band height** |
| `P` | Centre back yoke height | `P1` | Yoke height |
| `R` | Pocket mouth width | `R3` | Pocket opening width |
| `R1` | Pocket mouth length | `R4` | Pocket opening length |
| `RW` | **Welt height** | `R7` | **Pocket topstitch** |
| `S` | Front armhole along seam | `S` | Armhole along seam |
| `VP` | Ruffle end placement | `VP` | Ruffle placement |
| `ZC2` | Cord channel height | `Z6` | Drawstring tunnel height |

> Els dos **en negreta** són els que justifiquen la decisió 2 sencera: `N` i `RW` **no són** la
> mesura que el full els aparella. Lligar-los pel codi sol hauria posat el canònic equivocat.
> La resta són, gairebé tots, el mateix concepte amb una altra redacció —i uns quants ho són
> perquè **el v5 ha mogut «front»/«back» a la INSTÀNCIA** (`S`, `EK2`, `EKK`).

## B · Homònims: el v5 reutilitza el codi per a UNA ALTRA mesura (16)

Aquests **no tenen destí**: el codi coincideix i el significat no.

| codi | el tenant en diu | el v5 hi diu |
|---|---|---|
| `E2` | Across front width (11 cm from HPS) | Shoulder forward |
| `E3` | Across back width (11 cm from HPS) | Shoulder drop (from HPS to shoulder point) |
| `F1` | Side curve (CB length minus side seam) | Body length |
| `F3` | Front centre total length | Inseam length |
| `F4` | Back centre total length | Llength difference |
| `I3` | Cuff slit | Sleeve vent |
| `I4` | Sleeve length from CB over shoulder point (cuff included) | 1/2 bicep width |
| `I6` | Under sleeve length | Cuff opening |
| `I7` | Sleeve cap height | Cuff length |
| `L1` | Yoke seam length | Collar height |
| `M` | Leg opening | Neck width |
| `P1` | Side yoke height | Yoke height |
| `P2` | Centre front yoke height | Yoke placement from HPS |
| `S2` | Back armhole along seam | Across width |
| `S3` | Armhole curve | Across width at half armhole height |
| `T3` | Strap thickness | Placket width |

## C · Cap codi del v5 els correspon (23)

| codi | | codi | |
|---|---|---|---|
| `CR` | Front crotch width | `FF` | Centre back length from HPS |
| `CR1` | Back crotch width | `FJ` | Wingspan length |
| `CR3` | Crotch width placement | `FR` | Knee position |
| `E6` | Front collar panel height | `FS` | Skirt length |
| `E7` | Centre collar panel height | `FS4` | Top layer of the skirt length… |
| `E8` | Collar panel length | `FT` | Pants length (outseam) |
| `EC` | Collar point length | `PC` | Neck pipe width |
| `EK1` | Front neck drop from HPS | `SLT` | Slit / opening length |
| `FB` | Body length | `SLT1` | Vent overlap width |
| `FD` | Front rise length | `TR` | Placket height |
| `FE` | Back rise length | `VR` | Ruffle length |
| | | `ZZS45D` | *(banc de QA, no és domini)* |

🔑 **Uns quants d'aquests el v5 els resol com a DATUM d'un altre POM** —el full `INSTANCIES`
declara `incl_band`/`excl_band` per a `FD`/`FE`, `visible` per a `FB`, `seam` per a `EK1`— i
**l'eix DATUM no és a l'abast de cap brief encara**. Fins que hi sigui, no tenen on anar.

## D · Àlies de Brownie amb un altre destí, reportats i **no moguts** (3)

```
BW   apunta a 'QTD'  · el r2 el vol a 'BW'
U    apunta a 'Y'    · el r2 el vol a 'U'
U1   apunta a 'Y1'   · el r2 el vol a 'U1'
```

> A staging només n'hi ha 3. **A PROD n'hi ha 32**, i quasi tots apunten a un POM `*-ANTIC` —
> l'arxiu—: el codi de Brownie hi resol contra el catàleg mort. Re-apuntar-los és un tram propi
> i està a l'acta de la FASE B.

---

# EL VERD

| Control | Resultat |
|---|---|
| `manage.py check` | **net** (0 issues) |
| `fhort.pom.test_sembra_v5` | **36 tests · OK** |
| Verificacions read-only | **5/5**, totes HTTP 200 contra el servei viu |
| Altres suites | **cap**, per ordre d'Agus |

---

# EL QUE NO S'HA FET, I ES DIU

- **PROD no s'ha tocat.** La FASE D vol tren a `main` + finestra d'Agus. **Aquí es PARA.**
- **`los` no s'ha tocat** en cap comanda.
- **Els 55 POMs sense canònic i els 3 àlies divergents no s'han mogut**: són la criba fina.
- **Cap `nom_client` reescrit**: el català del v5 no arriba a la fitxa mentre el tenant tingui
  nom propi, i canviar-ho és un rebateig que vol decisió (§3c).
- **Cap `DELETE`** a tot el tram.

**Cap push. El merge i el desplegament a PROD els fa l'Agus.**
