# Dry-run · aplicació de la sessió Montse al catàleg semàntic

**Data:** 2026-08-27 · **Estat:** ⏸️ **ATURAT esperant OK** · **Res escrit encara.**
**Font:** `docs/ordres/SESSIO_MONTSE_respostes_2026-08-26.txt` (export 26/08 18:24)
**Marca a cada fila tocada:** `source_ref` conté `Montse session 2026-08-26`

---

## 0 · Què s'escriuria

| taula | public | fhort | los |
|---|---:|---:|---:|
| `pom_edgerole` | +1 | +1 | +1 |
| `pom_landmarkrole` | +9 | +9 | +9 |
| `pom_seampairtemplate` | +2 | +2 | +2 |
| `pom_garmenttypeitemedgeprofile` | 0 | **+20** | 0 |
| files actualitzades (noms, notes, graus) | 112 | 112 | 112 |

`public` i `los` no reben perfils GTI i és correcte: els tres pilots són codes del catàleg
de `fhort`, i `public` **ni tan sols té la taula `tasks_garmenttypeitem`** (`tasks` és
tenant-only). Es resolen per `code` i mai per pk — vegeu §5.

---

## 1 · Les respostes, una per una

| id | resposta | què s'ha fet |
|---|---|---|
| B.11 | «si, és bajo manga» | ✅ cap canvi: `sleeve_underarm_seam.nom_es` ja hi era |
| B.15 | «No, és diferent» | nota a `side_seam`: **costadillo ≠ side_seam**, rol de sastreria FUTUR |
| B.22 | «si, bajo = hem» | ✅ cap canvi: `hem.nom_es = Bajo` ja hi era |
| B.24 | «ES = Largo de pinza» | `dart_leg.nom_es`: «Brazo de pinza» → **«Largo de pinza»** |
| B.ORF1/2 | el nom del centre del coll | `EdgeRole collar_centre_seam` NOU + les 2 plantilles òrfenes |
| C.01–C.08 | «OK» ×8 | les 2 mesurades → **confirmades** · les 6 sense mesura → **validades** |
| C.09 | els nou punts | **9 `LandmarkRole` NOUS**, amb els seus noms `ca` literals |
| D.01 | core 75 · common 30 | grau recalculat i escrit a `observed_ref` — §4 |
| D.02 | «LLEI» | la llei del cap de màniga, a `source_ref` — §6.2 |
| D.03 | la seva explicació | **transcrita sencera** a `observed_ref` de les 4 files de pinça |
| E.P1–P3 | GTI + vores | 20 files de perfil pilot — §5 |
| E.P2/P3 `.falten` | el que troba a faltar | **8 slugs proposats i NO creats** |
| F.01–F.04 | metadades de la sessió | 837 VESTIT · XS-XL · DXF-AAMA PolyPattern · 27/08 |

### 1.1 Les 13 vores resolen totes

Tres ho fan per sinònim, i val la pena saber-ho: ella diu **«canto»** on el catàleg diu
**«vora»** (`Canto exterior del coll` → `collar_outer_edge`, `Canto de l'obertura` →
`slit_edge`), i **«Escot sense tirants»** on el catàleg diu «Vora de cos sense tirants»
(`strapless_top`). **No s'ha canviat cap nom**: són sinònims d'ofici, i canviar-los sense
demanar-li-ho seria posar-li paraules a la boca. Candidat a una passada de noms.

---

## 2 · `EdgeRole` — el slug nou i les esmenes

| # | slug | zone | kind | mates | needs_piece_role | nom_en | nom_ca | nom_es | source_ref |
|---|---|---|---|---|---|---|---|---|---|
| 4 | `collar_side_seam` | neck | seam | collar_side_seam | SI | Collar side seam | Costura lateral del coll | Costura lateral del cuello | `GarmentCode@d449629 collars.py:161-163` |
| 15 | `side_seam` | torso | seam | side_seam | SI | Side seam | Costura lateral | Costura lateral | `GarmentCode@d449629 bodice.py:73,217; pants.py:115,232` |
| 19 | `band_side_seam` | waist | seam | band_side_seam | SI | Band side seam | Costura lateral de banda | Costura lateral de banda | `GarmentCode@d449629 bands.py:74-75` |
| 24 | `dart_leg` | any | internal | dart_leg |  | Dart leg | Braç de pinça | Largo de pinza | `GarmentCode@d449629 panel.py:238; edge_factory.py:313` |

Les altres 27 files no canvien de nom. Les tres tocades:

| slug | canvi | font |
|---|---|---|
| `collar_centre_seam` | **NOU** · zone `neck` · mates a si mateix | B.ORF1/2 |
| `dart_leg` | `nom_es` → «Largo de pinza» | B.24 |
| `side_seam` | nota: costadillo ≠ side_seam | B.15 |
| `armhole` | nota: sisa sense màniga porta vora | E.P3 |

---

## 3 · `LandmarkRole` — 8 + 9

## LandmarkRole (17 files)
| # | slug | zone | derivable | op | input | tiebreak | evidencia | nom_en | nom_ca | nom_es |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `hps` | shoulder | SI | shared_endpoint | neckline + shoulder_seam | highest_y | 2371/2371 | High point shoulder | Punt alt d'espatlla | Punto alto de hombro |
| 2 | `shoulder_point` | shoulder | SI | shared_endpoint | shoulder_seam + armhole | -- | 2371/2371 | Shoulder point | Punt d'espatlla | Punto de hombro |
| 3 | `underarm_point` | arm | SI | far_endpoint | armhole | lowest_y | NO MESURADA | Underarm point | Punt de sota-braç | Punto de axila |
| 4 | `neck_centre_point` | neck | SI | far_endpoint | neckline | away_from:hps | NO MESURADA | Neck centre point | Punt central d'escot | Punto central de escote |
| 5 | `waist_side_point` | waist | SI | shared_endpoint | side_seam + waistline | -- | NO MESURADA | Waist side point | Punt de cintura al costat | Punto de cintura en el costado |
| 6 | `hem_side_point` | any | SI | shared_endpoint | side_seam + hem | -- | NO MESURADA | Hem side point | Punt de baix al costat | Punto de bajo en el costado |
| 7 | `crotch_point` | leg | SI | shared_endpoint | inseam + crotch_seam | -- | NO MESURADA | Crotch point | Punt de tir | Punto de tiro |
| 8 | `underarm_seam_point` | arm | SI | shared_endpoint | sleeve_cap + sleeve_underarm_seam | -- | NO MESURADA | Underarm seam point | Punt de sota-màniga | Punto de bajo manga |
| 9 | `dart_point` | any | SI | shared_endpoint | dart_leg + dart_leg | -- | NO MESURADA | Dart point | Punt de pinça | Punto de pinza |
| 10 | `bust_point` | torso | no | manual |  | -- | NO MESURADA | Bust point | Punt de pit | Punto de pecho |
| 11 | `hip_point` | waist | no | manual |  | -- | NO MESURADA | Hip point | Punt de cadera | Punto de cadera |
| 12 | `knee_point` | leg | no | manual |  | -- | NO MESURADA | Knee point | Punt de genoll | Punto de rodilla |
| 13 | `elbow_point` | arm | no | manual |  | -- | NO MESURADA | Elbow point | Punt de colze | Punto de codo |
| 14 | `calf_point` | leg | no | manual |  | -- | NO MESURADA | Calf point | Punt de bessó | Punto de gemelo |
| 15 | `biceps_point` | arm | no | manual |  | -- | NO MESURADA | Biceps point | Punt de bíceps | Punto de bíceps |
| 16 | `ankle_point` | leg | no | manual |  | -- | NO MESURADA | Ankle point | Punt de turmell | Punto de tobillo |
| 17 | `cuff_point` | any | no | manual |  | -- | NO MESURADA | Cuff point | Punt de puny | Punto de puño |

## GCPieceRoleMap (24 files)

## 4 · D.01 · els llindars

## D.01 · el recompte de graus amb els llindars de la Montse

Llindars **core ≥ 75 % · common ≥ 30 %** (abans, la proposta del precedent: 90 / 25).

| grau | amb 90/25 (precedent) | amb 75/30 (Montse) |
|---|---:|---:|
| core | 9 | 10 |
| common | 24 | 23 |
| rare | 22 | 22 |

**1 de 55 plantilles canvien de calaix.**

| plantilla | mena | % | 90/25 | **75/30** |
|---|---|---:|---|---|
| `skirt/front.side_seam ↔ skirt/back.side_seam` | union | 88.2 | common | **core** |
---

## 5 · E · els perfils GTI pilot

## GarmentTypeItemEdgeProfile — els 3 pilots de la Montse (20 files)

_GTI resolts contra l'schema `fhort`._

🚨 **La Montse va respondre per PRENDA i la taula és per PEÇA.** El pont el fa
aquesta llista i cada fila diu d'on surt l'assignació: `catàleg` (les plantilles
nomes la col·loquen alla), `definicio` (la vora ES d'aquella peca) o `ofici`
(el cataleg diu una altra cosa perque GarmentCode parteix les peces d'una
altra manera). **Les marcades `ofici` son la lectura que cal ratificar.**

`presence` surt del seu judici i NO d'una mesura: `observed_*` van a NULL i
els llindars 75/30 de D.01 no s'hi apliquen (son per a graus MESURATS).

### E.P1 · Blusa (Buttoned Tops) · `blouse` → pk 5

| # | peça | cara | vora | presence | assignació de peça |
|---|---|---|---|---|---|
| 1 | `front` | front | `neckline` | core | catàleg |
| 2 | `back` | back | `neckline` | core | catàleg |
| 3 | `collar` | — | `collar_outer_edge` | core | definició |
| 4 | `front` | front | `strapless_top` | rare | 🚩 ofici · alternativa a neckline |
| 5 | `sleeve` | front | `cuff_line` | core | catàleg |
| 6 | `sleeve` | back | `cuff_line` | core | catàleg |
| 7 | `front` | front | `centre_front` | core | catàleg |
| 8 | `front` | front | `hem` | core | 🚩 ofici · el baix d'una brusa és al cos |
| 9 | `back` | back | `hem` | core | 🚩 ofici · el baix d'una brusa és al cos |
| 10 | `front` | front | `slit_edge` | rare | 🚩 ofici · opció de disseny |

### E.P2 · Pantaló estructurat (Tailored & Rigid Pants) · `trousers` → pk 18

| # | peça | cara | vora | presence | assignació de peça |
|---|---|---|---|---|---|
| 1 | `pant` | front | `waistline` | core | catàleg |
| 2 | `pant` | back | `waistline` | core | catàleg |
| 3 | `pant` | front | `hem` | core | 🚩 ofici · el baix d'un pantaló és a la cama |
| 4 | `pant` | back | `hem` | core | 🚩 ofici · el baix d'un pantaló és a la cama |
| 5 | `pant` | front | `slit_edge` | rare | 🚩 ofici · opció de disseny |

### E.P3 · Vestit pla simple (Dresses) · `dress_simple` → pk 28

| # | peça | cara | vora | presence | assignació de peça |
|---|---|---|---|---|---|
| 1 | `front` | front | `neckline` | core | catàleg |
| 2 | `back` | back | `neckline` | core | catàleg |
| 3 | `front` | front | `strapless_top` | rare | 🚩 ofici · alternativa a neckline |
| 4 | `front` | front | `hem` | core | 🚩 ofici · un vestit pla es talla sencer |
| 5 | `back` | back | `hem` | core | 🚩 ofici · un vestit pla es talla sencer |

## Vocabulari que la Montse troba a FALTAR — proposat, NO creat (8)

Decidir un slug es decidir un contracte. Aquests van al report i esperen l'Agus.

| slug proposat | com en diu ella | d'on surt |
|---|---|---|
| `pocket_flap_edge` | Tapeta de butxaca | E.P2.falten |
| `pocket_opening` | Obertura de butxaca | E.P2.falten |
| `zip_placket_edge` | Tapeta cremallera | E.P2.falten |
| `side_opening` | Obertures laterals | E.P3.falten |
| `placket_edge` | Tapeta (vora) | E.P3.falten |
| `cuff_edge` | Punys (vora) | E.P3.falten |
| `skirt_hem` | Baix de faldilla | E.P3.falten · potser ja és `hem` + peça `skirt` |
| `costadillo` | Costadillo (rol de PEÇA, no de vora) | B.15 · sastreria |

  [dry-run] [public]
      edge_roles       creats:   1 · actualitzats:  27 · total ara:  27
      landmark_roles   creats:   9 · actualitzats:   8 · total ara:   8
      seam_pairs       creats:   2 · actualitzats:  53 · total ara:  53
      gc_map           creats:   0 · actualitzats:  24 · total ara:  24
      gti_profiles     creats:   0 · actualitzats:   0 · total ara:   0
  [dry-run] [fhort]
      edge_roles       creats:   1 · actualitzats:  27 · total ara:  27
      landmark_roles   creats:   9 · actualitzats:   8 · total ara:   8
      seam_pairs       creats:   2 · actualitzats:  53 · total ara:  53
      gc_map           creats:   0 · actualitzats:  24 · total ara:  24
      gti_profiles     creats:  20 · actualitzats:   0 · total ara:   0
  [dry-run] [los]
      edge_roles       creats:   1 · actualitzats:  27 · total ara:  27
      landmark_roles   creats:   9 · actualitzats:   8 · total ara:   8
      seam_pairs       creats:   2 · actualitzats:  53 · total ara:  53
      gc_map           creats:   0 · actualitzats:  24 · total ara:  24
      gti_profiles     creats:   0 · actualitzats:   0 · total ara:   0

---

## 6 · Les quatre coses que vull que miris abans de dir que sí

### 6.1 🚩 `name_en` del slug nou: la Montse i el brief no diuen el mateix

Ella escriu **«Center collar seam»**; el brief deia **«Collar centre seam»**. He posat el
del brief, per dues raons: la casa escriu *centre* a la britànica (`centre_front`,
`hood_centre_seam`) i el patró de noms és `<peça> <part> seam` (`Collar side seam`, `Hood
centre seam`, `Band side seam`). **El seu `ca` i `es` s'han posat literals**, que és on ella
és l'autoritat. Si vols el seu anglès, és una línia.

### 6.2 🚩 D.02 parla del cap de màniga, i hi ha DOS zeros mesurats

La llei («el cap bascula endavant; el mirall invers no s'espera») s'ha posat **només** a
`back.armhole ↔ sleeve/front.sleeve_cap`, que és la que descriu. L'altre zero és
`cuff/back.band_attach_upper ↔ pant/front.cuff_line` — **un puny de cama, que no té cap ni
espatlla**. Posar-hi la mateixa frase amb el seu nom a sota seria pitjor que deixar-lo sense
lectura. **Queda sense explicació i és una pregunta oberta per a ella.**

### 6.3 🚩 Les 8 files `ofici` dels perfils GTI

La Montse va respondre per PRENDA («una brusa porta escot») i la taula és per PEÇA. On el
catàleg decideix sol, l'he seguit; on no, la lectura és meva i va marcada 🚩. Les vuit
discutibles són totes de la mateixa mena: **el baix i l'obertura**. GarmentCode posa `hem` i
`slit_edge` a la faldilla perquè sempre parteix el vestit per la cintura; en un patró de
debò el baix d'una brusa és al cos i el d'un pantaló, a la cama. **Si hi discrepes, són
vuit línies.**

### 6.4 🚩 `E.P3.falten` inclou «escot», que ja és a `E.P3.vores`

La llista de vores del vestit porta «Escot» i la de mancances també. No ho he resolt: pot
ser que hi vulgui dir un altre escot (de darrere?) o pot ser un lapsus de la sessió. **Va
tal qual a la llista d'extensions.**

---

## 7 · Coses que NO s'han fet, i per què

| què | per què no |
|---|---|
| els 8 slugs d'extensió | decidir un slug és decidir un contracte: és teu |
| `costadillo` com a rol de peça | idem, i a més és de PEÇA i no de vora (B.15) |
| plantilla `armhole ↔ facing` | `facing` no té cap rol de vora definit; inventar-n'hi un per tancar la frase seria vocabulari sense evidència |
| grau a `SeamPairTemplate` com a COLUMNA | seria una migració, i el brief deia que no se n'esperava cap. El grau es calcula i s'escriu a `observed_ref` |
| enllaç dels 6 corporals a `BodyMeasurementISO` | **la taula és buida** (0 files, comprovat 27/08). Cap codi inventat |

---

## 8 · Quan diguis que sí

```bash
cd /var/www/ftt-montse/backend && set -a && . ./.env && set +a
venv/bin/python manage.py seed_semantic_catalog          # aplica als 3 esquemes
venv/bin/python manage.py seed_semantic_catalog          # 2a passada: 0 creats
```

El `guarda_tancament()` corre sol a cada passada i ha de dir 0 forats als tres esquemes.
Després: recompte amb `psql` directe, merge a `dev` i acta a
`docs/diagnosis/REPORT_APLICACIO_MONTSE_2026-08-27.md`.
