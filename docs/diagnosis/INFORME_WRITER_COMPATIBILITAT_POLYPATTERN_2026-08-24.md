# El writer DXF/RUL i la compatibilitat real amb PolyPattern

**Patró B · staging `dev` · CAP push · CAP escriptura a BD.** `build_export` no escriu res
(l'`ExportAcknowledgement` el crea la view, i aquí no s'hi passa); tota la sondeja va dins
d'un `transaction.atomic()` avortat. Cap reconeixement, cap export real. Els tests
**s'escriuen i no s'executen** (llei 23/08).

Continua [`INFORME_FIX_NIADA_COSIT_2026-08-24.md`](INFORME_FIX_NIADA_COSIT_2026-08-24.md).

---

## 0. PRIMER: L'EVIDÈNCIA DEL BRIEF, CORREGIDA

El fitxer de referència no es diu `837_CORS_VESTIT__op_cost.DXF` i no n'hi ha cap amb aquest
nom a la màquina. El que porta les xifres del brief és
**`837_CORS_194_VESTIT_M3-4_AGUS.DXF`** (pujat el 24/08 a les 08:11) — i el detall que val
la pena saber: **és el fitxer d'origen de PF20**. O sigui que la comparació no és contra un
patró germà, és contra **el nostre propi patró tal com el PolyPattern el va escriure**. Això
la fa molt més forta: qualsevol diferència és nostra.

(L'altre candidat, `837__VESTIT_s_opcio_cost.DXF/.RUL` — l'origen de PF18 —, té **100** TEXT
de regla, tots `# 1`, i un RUL amb **una sola regla de repòs**. No és el fitxer graduat.)

Amb el fitxer correcte al davant, tres xifres del brief no s'aguanten:

| | brief | mesurat | |
|---|---|---|---|
| regles a capa 2 | 202 | **158** | |
| regles a capa 4 | 44 | **22** | ell n'escriu una per PIQUET; els piquets van per PARELLES de POINT |
| regles a capa 8 / 14 | 79 / 79 | **79 / 79** | ✅ |
| total de TEXT de regla | (404) | **338** | |
| numeració RUL | `DELTA 1…238` | el **DXF** numera 1…238; el RUL d'aquest fitxer no és a la màquina | |
| **«FTT: punts amb regla 38»** | 38 | **202** | 38 eren els números DISTINTS (0…38), no els punts |

**La nostra situació de partida era millor del que el brief donava per fet: ja emetíem 158
TEXT a la capa 2, exactament com ell, i amb ZERO punts de gir orfes.** El forat real era un
altre — les capes 8 i 14 buides, la numeració des de 0 i la capçalera del RUL a un quart.

> **La hipòtesi de treball queda a mitges, i s'ha de dir.** «Amb punts orfes i/o numeració
> des de 0 el CAD descarta la taula» no s'ha pogut verificar: la part dels orfes era falsa
> (no en teníem) i la resta només la pot confirmar el PolyPattern obrint el fitxer nou. El
> que sí que està demostrat és que **el fitxer que emetíem es diferenciava del seu en tres
> coses estructurals concretes, i ara no se'n diferencia en cap de les tres.**

---

## 1. LA LLEI DEL CAD, MESURADA

Sobre `837_CORS_194_VESTIT_M3-4_AGUS.DXF`, peça a peça:

```
peça             POINT capa 2   TEXT capa 2   TEXT capa 4   TEXT capa 8   TEXT capa 14
837.CUELLO             20            20            4            10            10
837.DELANTERO          56            56            6            28            28
837.ESPALDA            48            48            4            24            24
837.MANGA              18            18            4             9             9
837.TAPETA             16            16            4             8             8
                      ───           ───          ───           ───           ───
                      158           158           22            79            79
```

Tres lleis, totes tres verificades punt a punt:

1. **Cap gir orfe.** `TEXT capa 2 == POINT capa 2` a les cinc peces, a la mateixa
   coordenada exacta. El que no es mou porta la regla de **repòs**, no cap regla.
2. **El gir del COSIT porta el número tres vegades.** Dels 158 girs, **79 seuen sobre la
   polilínia de cosit (capa 14)** — i són EXACTAMENT aquests 79 els que porten un TEXT
   addicional a la capa 8 i un altre a la capa 14, a la mateixa coordenada i amb el mateix
   número. Ordre dins del bloc: **2 → 8 → 14**.
3. **La numeració comença a 1, i la 1 és el repòs.** El DXF numera 1…238, i les peces que
   no graduen (CUELLO, TAPETA) porten `# 1` a tots els punts. Per a aquest CAD **el zero no
   és cap número de regla**.

I la capçalera del RUL que el seu CAD escriu (del germà `837__VESTIT_s_opcio_cost.RUL`):

```
version ANSI/AAMA-292-B
AUTHOR: PolyPattern 11.0.1
UNITS: METRIC
GRADE RULE TABLE:837  VESTIT s opcio cost
SAMPLE SIZE:S …
```

El nostre n'emetia **una línia de quatre** (`UNITS:`), i no per descuit: les altres tres
eren condicionals a `doc.grade_table`, i **PF20 va entrar sense RUL** (`grade_table` a NULL),
o sigui que no hi havia d'on copiar-les.

---

## 2. ELS CANVIS

### 2.1 · La capçalera del RUL, sencera i sempre

`rul_writer.py` — `version` i `UNITS` deixen de ser condicionals i tenen defecte
(`ANSI/AAMA-292-B`, `METRIC`). No és inventar: **són propietats del fitxer que escrivim**.
Si l'origen en declara de seves, manen les seves (reproduir, no millorar).

`grading_projection._nom_de_taula_del_document` — quan el patró ve sense RUL, el nom de la
taula **es copia del DXF**: el reader ja desa els TEXT del modelspace a
`fingerprint.textos_document`, i allà hi ha
`GRADE RULE TABLE:837 CORS 194 VESTIT M3-4 AGUS`. És el mateix nom que el DXF que emetem ja
posava, o sigui que els dos germans diuen el mateix. **Si el DXF no en declara cap, no
s'inventa**: la línia no surt i `export._problemes_capcalera` ho diu a la llista del modal.

### 2.2 · L'AUTOR — decisió d'Agus (24/08)

```
AUTHOR: FHORT Textile Tech
```

**El nostre nom, i primer.** Aquest RUL no l'ha escrit el PolyPattern: l'hem escrit
nosaltres amb el grading de l'FTT, i signar-lo amb el nom del CAD del client seria dir una
cosa falsa sobre qui respon del fitxer. La versió calcada (`PolyPattern 11.0.1`) queda com a
**segona prova, i només amb evidència**: si el CAD rebutja el fitxer i es demostra que és per
aquest camp, es reporta i es prova. Mai s'assumeix. La constant és
`grading_projection.AUTOR_RUL`, una línia.

> ⚠️ **Una tensió visible que val la pena que sàpigues.** El DXF que emetem continua
> portant, al modelspace, el TEXT `Author: PolyPattern` — perquè és part de l'empremta de
> l'origen i el writer la **reprodueix**; tocar-la trencaria el round-trip byte a byte.
> O sigui que el DXF diu `Author: PolyPattern` i el RUL germà diu `AUTHOR: FHORT Textile
> Tech`. Cap dels dos menteix (un reprodueix l'origen, l'altre signa la taula nova), però
> són dues frases diferents al mateix paquet. Si vols que el DXF també ens signi, és una
> decisió a part i toca l'empremta.

### 2.3 · La numeració des de 1

`REGLA_ZERO = 0` → **`REGLA_ZERO = 1`**, i les regles que mouen comencen a
`PRIMERA_REGLA_MOBIL = 2`. Cap `RULE: DELTA 0` al RUL, cap `# 0` al DXF.

### 2.4 · Les capes 8 i 14

`aama_writer.CAPES_EXTRA_DE_REGLA` — un gir de la línia de **COSIT** emet el seu número a
les capes 2, 8 i 14 (en aquest ordre); un gir d'una línia **INTERNA**, a la 2 i la 8 (el
comportament d'abans, intacte). La condició era `role is INTERNAL` i per això el cosit no
n'emetia cap: **el moviment del cosit hi era —el motor el calcula des del fix d'aquest
vespre— però no viatjava al fitxer**, perquè el CAD el busca a les capes del cosit i no a
la 2.

---

## 3. EL RESULTAT

```
                    MONTSE (origen de PF20)    FTT (abans)     FTT (ara)
punts amb regla            338                     202            360
  · capa 2 (girs)          158                     158            158   ✅ = ell
  · capa 4 (piquets)        22                      44             44   ⚠ divergeix
  · capa 8 (internes)       79                       0             79   ✅ = ell
  · capa 14 (cosit)         79                       0             79   ✅ = ell
girs orfes a capa 2          0                       0              0   ✅
numeració                1…238                   0…38            1…39   ✅ comença a 1
capçalera RUL          4 línies                1 línia        4 línies  ✅
```

I peça a peça, les capes 8/14: 10·28·24·9·8 nostres = 10·28·24·9·8 seus. Clavat.

**La invariant intacta:** 3.840 punts a **0,0000 mm** de l'original, autovalidació del
round-trip **39/39 regles**, cens immòbil (4.274 entitats a les dues voltes).

---

## 4. EL QUE ENCARA NO ÉS IGUAL (i per què no s'ha tocat)

**D1 · La capa 4: 44 nostres vs 22 seves.** No és que en faltin: **en sobren**. Als DOS
fitxers hi ha 44 POINT de piquet, i al DELANTERO els 12 formen **6 parelles a menys de 25
mm** — un piquet és un parell de punts. Ell escriu **un TEXT per piquet** (6); nosaltres
**un per punt** (12), perquè el nostre reader modela cada POINT de la capa 4 com un piquet
independent. Baixar a 22 sense tocar el model deixaria 22 POINT de piquet orfes, que és
justament el que aquest sprint venia a evitar. **És una divergència del MODEL, no del
writer**, i arreglar-la vol tocar el reader — fora d'aquest brief. Queda anotada com la
**primera cosa a mirar si el CAD encara no desplega**.

**D2 · L'ordre d'entitats dins del bloc no està calcat.** Ell escriu
`TEXT/1 → POLYLINE/1 → VERTEX/1 → TEXT/2 → POINT/2 → POINT/3 → TEXT/4 → POINT/4 → LINE/7 →
TEXT/8 → POLYLINE/14 → VERTEX/14 → TEXT/14`; nosaltres agrupem diferent. El que SÍ que s'ha
calcat és el que el brief concreta entre parèntesis —el TEXT de regla associat al punt i a
les mateixes capes— i l'ordre **per punt** (2 → 8 → 14). Reordenar l'emissió sencera del
bloc és un refactor del writer que no canvia cap contingut i que ningú ha demostrat que
calgui; si el CAD el necessita, es fa amb aquella evidència al davant.

**D3 · Blocs `$Model_Space` i `$Paper_Space`.** El nostre fitxer en porta dos de buits que
el seu no té (artefacte d'ezdxf). Preexistent, no tocat, i no afecta cap recompte.

**D4 · El que aquest sprint tenia prohibit tocar, sense tocar:** la geometria base (0,0000
mm), la projecció v1 (A, C, S2, E, S, E1 conserven els seus residus, dits amb la xifra a la
llista de problemes) i els modes `projeccio`/`ortogonal` (els 6 POMs segueixen fora de la
niada en veu alta). GV201 intacta.

---

## 5. LA VERIFICACIÓ

| control | resultat |
|---|---|
| `ops/qa/banc_niada_vs_polypattern.py` | **23 ✓ · 0 ✗** |
| `python manage.py check` | net |
| `npx eslint src` | 0 errors (273 warnings preexistents) |
| `npm run build` | verd |
| smoke de navegador de l'ExportModal | **19 ✓ · 0 ✗** |
| geometria vs original | **0,0000 mm** sobre 3.840 punts |
| autovalidació del round-trip | ✅ 39/39 regles, 0,000 µm |
| `RULWriter(RULReader(AMELIA.RUL))` byte a byte | ✅ idèntic (la guarda que existia segueix verda) |

El banc nou compara **el fitxer que emetem contra el fitxer del CAD**, no contra la nostra
idea del fitxer: llegeix els dos DXF amb un parser cru de parells `(codi, valor)` a posta,
perquè fer-ho amb el nostre `AAMAReader` compararia la nostra lectura amb la nostra lectura.

**Tests escrits, no executats** (llei 23/08): `CompatibilitatPolyPatternTest`, 12 tests —
cap gir orfe · cap piquet orfe · les corbes segueixen sense regla · el gir del cosit a les
capes 2/8/14 amb el mateix número · el gir del tall només a la 2 · la numeració comença a 1
i la 1 és el repòs · cap `DELTA 0` al RUL · la capçalera sencera i en ordre · l'autor és el
nostre · el nom de taula es copia · sense nom no s'inventa i es diu · els TEXT nous no
toquen la geometria.

> Com que no s'han executat, **els seus fixtures no estan verificats**. El que SÍ que està
> mesurat, i sobre el fitxer real i no sobre un fixture sintètic, és tot el que hi ha a la
> taula de dalt.

---

## 6. UNA CORRECCIÓ A L'INFORME D'AQUEST VESPRE

`INFORME_FIX_NIADA_COSIT_2026-08-24.md` deia **«37 regles · autovalidació 37/37»**. La xifra
venia d'una execució anterior a l'últim canvi d'aquell sprint (la propagació que respecta els
ancoratges propis del cosit) i no es va tornar a prendre. Amb el codi entregat en són
**39 · 38 actives · 39/39**: recuperar l'ancoratge de corba mou dos piquets més, i un piquet
que es mou és una regla nova. L'informe i les assercions del smoke ja estan corregits; la
resta d'aquell informe es manté.

---

## 7. FITXERS TOCATS

| fitxer | què |
|---|---|
| `backend/fhort/patterns/engine/rul_writer.py` | capçalera sencera i sempre; `VERSIO_AAMA`, `UNITATS_PER_DEFECTE` |
| `backend/fhort/patterns/engine/grading_projection.py` | `REGLA_ZERO = 1` + `PRIMERA_REGLA_MOBIL`; `_nom_de_taula_del_document`; `AUTOR_RUL` |
| `backend/fhort/patterns/engine/aama_writer.py` | `CAPES_EXTRA_DE_REGLA`: el cosit emet a 2, 8 i 14 |
| `backend/fhort/patterns/export.py` | `_problemes_capcalera` a la llista del modal |
| `backend/fhort/patterns/tests.py` | `CompatibilitatPolyPatternTest`, 12 tests (escrits, no executats) |
| `ops/qa/banc_niada_vs_polypattern.py` | el banc de comparació contra el fitxer del CAD |
| `ops/qa/qa_niada_cosit_1383.py` + `payload_niada_1383.json` | assercions i payload al dia (36→38, 37/37→39/39) |

Cap fitxer de front tocat: l'ExportModal ja pintava `problemes_escalat` des d'aquest vespre.
