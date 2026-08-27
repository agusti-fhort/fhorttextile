# Aplicació de la sessió Montse al catàleg semàntic — acta

**Data:** 2026-08-27 · **Patró B** · **Branca:** `montse-cataleg-v2` · **Cap push**
**Font d'autoritat:** `docs/ordres/SESSIO_MONTSE_respostes_2026-08-26.txt` (export 26/08 18:24)
**Marca:** `source_ref` conté `Montse session 2026-08-26` a cada fila tocada
**Dry-run validat per l'Agus:** 27/08 · `docs/ordres/APLICACIO_MONTSE_DRYRUN_2026-08-27.md`

> ## ✅ APLICAT
>
> | | public | fhort | los |
> |---|---:|---:|---:|
> | `pom_edgerole` | 28 | 28 | 28 |
> | `pom_landmarkrole` | 17 | 17 | 17 |
> | `pom_seampairtemplate` | 55 | 55 | 55 |
> | `pom_gcpiecerolemap` | 24 | 24 | 24 |
> | `pom_garmenttypeitemedgeprofile` | 0 | **20** | 0 |
> | **total** | **124** | **144** | **124** |
>
> **2a passada: 0 creats a les tres.** `guarda_tancament()`: **0 forats als tres esquemes.**
> Cap migració: tot és dada.

---

## 0 · El resum en cinc línies

1. **El catàleg deixa de tenir òrfenes.** Amb `collar_centre_seam` (B.ORF1/2), les 51
   parelles que el corpus mesura tenen totes plantilla: **0 de 51 sense recollir**.
2. **Els punts notables passen de 8 a 17**, i els nou nous porten els noms d'ofici de la
   Montse. **Només un és derivable**, i és el que ho és de debò.
3. 🚩 **Els llindars de la Montse mouen menys del que semblava: 1 plantilla de 55.** La
   distribució és bimodal, i canviar 90/25 per 75/30 amb prou feines la toca.
4. 🚩 **`BodyMeasurementISO` és buida**: cap dels sis punts corporals té on enllaçar-se.
5. 🚩 **El guard de tancament tenia un forat propi** i el va destapar aquesta mateixa
   sembra: no mirava `GTIEdgeProfile` perquè fins avui era buida.

---

## 1 · Les respostes, i què n'ha sortit

| id | resposta | resultat |
|---|---|---|
| B.11 · B.22 | «bajo manga» · «bajo = hem» | ✅ confirmats, **cap canvi** |
| B.15 | «No, és diferent» | nota a `side_seam`: costadillo ≠ side_seam |
| B.24 | «ES = Largo de pinza» | `dart_leg.nom_es` corregit |
| B.ORF1/2 | el nom del centre del coll | `collar_centre_seam` + 2 plantilles |
| C.01–C.08 | «OK» ×8 | 2 **confirmades** · 6 **validades** |
| C.09 | els nou punts | 9 `LandmarkRole` nous |
| D.01 | 75 / 30 | grau recalculat a les 55 plantilles |
| D.02 | «LLEI» | la llei del cap de màniga |
| D.03 | la seva explicació | **transcrita sencera** a les 4 files de pinça |
| E.P1–P3 | GTI + vores | 20 files de perfil pilot a `fhort` |
| E.*.falten | el que troba a faltar | 8 slugs **proposats i NO creats** — §6 |
| F.01–F.04 | metadades | 837 VESTIT · XS-S-M-L-XL · DXF-AAMA PolyPattern · 27/08 |

### 1.1 Les 13 vores van resoldre totes, tres per sinònim

Ella diu **«canto»** on el catàleg diu **«vora»**, i **«Escot sense tirants»** on el catàleg
diu «Vora de cos sense tirants». **No s'ha canviat cap nom**: són sinònims d'ofici i
canviar-los sense demanar-li-ho seria posar-li paraules a la boca. Candidat a una passada
de noms amb ella.

---

## 2 · Els nou punts nous, i per què només un és derivable

| slug | `ca` (seu) | zona | derivable |
|---|---|---|---|
| `dart_point` | Punt de pinça | any | **✅ àpex = juntura dels dos braços** |
| `bust_point` | Punt de pit | torso | ❌ |
| `hip_point` | Punt de cadera | waist | ❌ corporal |
| `knee_point` | Punt de genoll | leg | ❌ corporal |
| `elbow_point` | Punt de colze | arm | ❌ corporal |
| `calf_point` | Punt de bessó | leg | ❌ corporal |
| `biceps_point` | Punt de bíceps | arm | ❌ corporal |
| `ankle_point` | Punt de turmell | leg | ❌ corporal |
| `cuff_point` | Punt de puny | any | ❌ construcció (F4.2) |

> 🚨 **La temptació era encadenar-los** —«el punt de pit surt del de pinça»— i el brief ho
> prohibia expressament. És la decisió correcta i val la pena dir per què: **un davant sense
> pinça té punt de pit igualment**, i un patró amb dues pinces en té un de sol. Un punt
> marcat com a derivable que després no es pot calcular és **pitjor** que un de manual,
> perquè F4 el buscarà i no el trobarà mai.

### 2.1 L'àpex va exigir una operació nova

`_extrems_de_rol` torna els punts que apareixen **un** cop i **cancel·la els que apareixen
dos**, que són les juntures interiors. L'àpex d'una pinça és exactament una d'aquelles: els
dos braços hi arriben. O sigui que la funció que semblava servir era la que el llençava.

`_junctura_del_mateix_rol` és el cas invers. Provada en verd (una pinça → l'àpex) i en
vermell (dues pinces → **es queixa en comptes de triar-ne una**).

---

## 3 · D.01 · els llindars, i la sorpresa

| grau | amb 90/25 (el precedent) | amb **75/30** (Montse) |
|---|---:|---:|
| core | 9 | **10** |
| common | 24 | **23** |
| rare | 22 | 22 |

**Canvia 1 plantilla de 55:** `skirt/front.side_seam ↔ skirt/back.side_seam`, 88,2 % —
de `common` a `core`.

> 🔑 **Els llindars mouen menys del que tothom esperava, i el motiu és la forma de la
> distribució, no els números.** Les freqüències del corpus són bimodals: o la parella surt
> a prop del 100 % (és estructural) o cau molt per sota del 30 % (és una opció de disseny).
> **Entre el 30 % i el 75 % gairebé no hi ha ningú**, o sigui que moure la frontera per allà
> no toca res. Val la pena saber-ho abans de discutir un llindar una altra vegada.

🚩 **`SeamPairTemplate` no té columna de grau.** L'únic `presence` del catàleg és a
`GTIEdgeProfile`. Afegir-n'hi una hauria estat la migració que el brief deia que no
s'esperava; deixar-ho córrer hauria perdut la decisió. **El grau es calcula i s'escriu dins
d'`observed_ref`** — visible, auditable, i migrable el dia que faci falta com a columna.

---

## 4 · D.02 i D.03 · les dues lectures d'ofici

**D.02** («LLEI») ha anat a `source_ref` de la plantilla que descriu:
`back.armhole ↔ sleeve/front.sleeve_cap`, el zero mesurat. El cap de màniga bascula
endavant i **el mirall invers no s'espera mai** — el zero era la resposta correcta i ara diu
per què.

> 🚩 **L'ALTRE zero mesurat s'ha quedat sense lectura, a posta.**
> `cuff/back.band_attach_upper ↔ pant/front.cuff_line` també surt a zero, però és **un puny
> de cama, que no té cap ni espatlla**. Posar-hi la frase de la màniga amb el nom de la
> Montse a sota seria pitjor que deixar-lo mut. **Pregunta oberta per a ella.**

**D.03** va a `observed_ref` de les quatre files de pinça i es transcriu **sencera**. El que
diu és que la xifra no és una llei —*«No hi ha un perquè»*— i sense la nota algú llegiria el
52 % del corpus com una regla d'ofici.

---

## 5 · E · els vint perfils pilot

| GTI | code | pk a `fhort` | files |
|---|---|---:|---:|
| Blusa | `blouse` | 5 | 10 |
| Pantaló estructurat | `trousers` | 18 | 5 |
| Vestit pla simple | `dress_simple` | 28 | 5 |

🚨 **Resolts per `code`, mai per pk** (llei G9). Aquest seed corre als tres esquemes i les
pks de `tasks_garmenttypeitem` són **locals de cada tenant**: sembrar per id hauria volgut
dir que el dia que `los` creï el seu GTI número 5, li enganxaríem un perfil de «Blusa» en
silenci. Avui no xocaria —`los` en té un de sol i no és cap dels tres— però la bomba hauria
quedat armada.

🚩 **La Montse va respondre per PRENDA i la taula és per PEÇA.** El pont el va fer aquesta
sessió i **vuit files van marcades com a lectura d'ofici** (ratificades per l'Agus al
dry-run). Totes vuit són de la mateixa mena: **el baix i l'obertura**. GarmentCode posa
`hem` i `slit_edge` a la faldilla perquè sempre parteix el vestit per la cintura; en un
patró de debò el baix d'una brusa és al cos i el d'un pantaló, a la cama.

🚩 **`presence` no és una mesura.** Surt del judici de la Montse: `observed_n` i
`observed_den` van a **NULL** —no s'ha mesurat res per GTI— i `observed_ref` ho diu. **Els
75/30 de D.01 no s'hi apliquen**: són per a graus mesurats.

---

## 6 · Vocabulari proposat i NO creat

Decidir un slug és decidir un contracte, i això no és d'aquesta sessió.

| slug proposat | com en diu ella | d'on surt |
|---|---|---|
| `pocket_flap_edge` | Tapeta de butxaca | E.P2.falten |
| `pocket_opening` | Obertura de butxaca | E.P2.falten |
| `zip_placket_edge` | Tapeta cremallera | E.P2.falten |
| `side_opening` | Obertures laterals | E.P3.falten |
| `placket_edge` | Tapeta (vora) | E.P3.falten |
| `cuff_edge` | Punys (vora) | E.P3.falten |
| `skirt_hem` | Baix de faldilla | E.P3.falten · potser ja és `hem` + peça `skirt` |
| `costadillo` | Costadillo | B.15 · és rol de **PEÇA**, no de vora |

També pendent: **la plantilla `armhole ↔ facing`** que la llei E.P3 implica («si va sense
mànigues, la sisa portarà vora»). No es crea perquè **`facing` no té cap rol de vora
definit**, i inventar-n'hi un per tancar la frase seria vocabulari sense evidència. La llei
sí que és escrita, al `source_ref` d'`armhole`.

🚩 **`E.P3.falten` inclou «escot», que ja és a `E.P3.vores`.** No s'ha resolt: pot voler dir
un altre escot (de darrere?) o pot ser un lapsus de la sessió.

---

## 7 · 🚩 El guard de tancament tenia un forat, i el va destapar aquesta sembra

`guarda_tancament()` (F3) comprovava el mapa GC, les plantilles, els `mates_slug` i els
operands dels punts. **No mirava `GTIEdgeProfile`** — i no es notava, perquè la taula era
buida. Les primeres vint files l'han estrenat sense vigilància.

Ampliat i **provat en vermell**: esborrant `strapless_top` dins d'un `ROLLBACK`, canta
`perfil GTI 5 -> rol de vora «strapless_top» NO EXISTEIX` i el seu bessó del 28.

> 🔑 **Un guard que només cobreix les taules que ja tenien files caduca sol.** La primera
> fila d'una taula nova és, per construcció, la que no vigila ningú.

I un segon ensurt de la mateixa consulta: `GTIEdgeProfile.Meta.ordering` comença per
`garment_type_item` —una FK—, i **ordenar per una FK fa que Django hi faci JOIN**. A
`public` aquella taula no existeix i el guard petava. `.order_by()` buit. És la mateixa
trampa que el tren de coda T3 va documentar per a les migracions multi-schema.

---

## 7-bis · 🚩 I un test d'F3 que la sembra va caducar

`test_els_vuit_son_derivables_i_cap_no_es_manual` assertava exactament això: **vuit**
derivables i **cap** manual. Amb els nou punts nous va donar `9 != 8`, i tenia raó de
petar: sis dels nous són CORPORALS i `derivation_op='manual'` és el registre honest que
del patró no surten mai.

Reescrit com a **invariant** i no com a recompte: un punt `derivable=True` no pot tenir
operació `manual` (seria una promesa que ningú no pot complir — F4 el buscaria i no el
trobaria) i un `derivable=False` no pot portar una regla escrita que ningú no crida.

> 🔑 **Un test que compta files caduca cada vegada que el catàleg creix; un que asserta
> una contradicció impossible, no.** Val la pena mirar-s'ho quan un vermell surt d'una
> sembra que ha fet exactament el que havia de fer.

`Ran 23 tests · OK`.

---

## 8 · Fronteres

| frontera | com s'ha comprovat |
|---|---|
| cap migració | `makemigrations --check` net; tot és dada |
| idempotència | 2a passada: **0 creats** als tres esquemes |
| tancament del catàleg | `guarda_tancament()`: **0 forats** × 3 |
| `public`/`los` sense perfils GTI | correcte: els codes són de `fhort` i `public` ni té la taula |
| cap dada de model tocada | només catàleg |
| push | cap |
