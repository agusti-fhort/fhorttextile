# Fix del desplegat (`unfold_piece`) + tests T6-T9

**Data:** 2026-08-25 · **Fil:** S46-MOTOR · Patró B
**Defecte:** viu, detectat a `QA_TALLER_D_CONVENCIO_RECORREGUT_2026-08-25.md`
**Branca:** `s46-fix-desplegat` (worktree `/root/s46-unfold`) · **CAP push** — el push és d'Agus

> **Fronteres respectades.** Worktree propi des del minut zero. Commits amb `git add`
> de paths explícits. Cap `systemctl`, cap migració (`makemigrations --check`: *no
> changes detected*), cap escriptura a cap BD, cap secret llegit (el `.env` real no s'ha
> obert: `manage.py check` s'ha corregut amb valors de rebuig).
> **Tests executats: NOMÉS el fitxer nou d'aquest fix.** Cap suite d'app, cap suite sencera.

---

## 0 · El resum en cinc línies

1. **13 de 13 peces amb doblec del material real donen ara àrea desplegada = 2× la
   meitat.** Abans, **8** no ho feien.
2. 🚨 **El defecte era MÉS ample del que el cens deia.** El cens en va comptar 6 de
   trencades; en són **8**. `BACK_RUFFL` i `FRONT_RUFFL` del MEREDITH donaven 1,96× i el
   cens ho va atribuir a la curvatura. **Era un tercer punt d'eix al mig de la tirada**
   que hi feia un triangle espuri: un error del 4 % que no cantava. §3.
3. El criteri separador correcte no és «l'eix als índexs 0 i n−1» sinó **«exactament dos
   punts d'eix, als índexs 0 i n−1»**. Les 5 peces que anaven bé el compleixen totes;
   les 8 trencades, cap.
4. **Les 5 que ja anaven bé surten idèntiques punt a punt** — verificat contra el llegat
   executant-se, no contra una llista escrita a mà.
5. **16 tests nous, en verd.** Verificat que caçen el defecte: amb el fix neutralitzat,
   **18 subtests fallen** i anomenen exactament les 8 peces trencades.

---

## 1 · La causa, amb rastre

[`engine/aama_reader.py:650-666`](../../backend/fhort/patterns/engine/aama_reader.py#L650)
(numeració d'abans del fix) — `_mirror_points`:

```python
return points + tuple(reflectits)   # reflectits = mirall dels no-eix, en ordre invers
```

La còpia reflectida s'empelta **al final de la llista**, o sigui que **substitueix
l'aresta de TANCAMENT** del bucle (l'última cap a la primera). Això és correcte només si
aquella aresta de tancament **és la vora del doblec**.

I això no és una propietat de la peça: **és on el CAD va obrir la polilínia**, que és
arbitrari. El reader pren els punts en ordre natiu i no els normalitza mai
([`:334`](../../backend/fhort/patterns/engine/aama_reader.py#L334)).

Els punts de l'eix s'identifiquen amb el criteri **que el codi ja feia servir i que s'ha
mantingut**: `_on_axis(x, y, fold)`
([`:682-684`](../../backend/fhort/patterns/engine/aama_reader.py#L682) d'abans del fix),
que és per **coordenada** contra la recta de l'eix — no per índex ni per capa.

### El cas canònic: CALLIE peça `14`

Rectangle a la dreta d'un eix vertical a `x = 5210,14`, amb els punts d'eix als índexs
**1 i 2** (al mig del bucle):

```
ABANS (4 punts)                    LLEGAT DESPLEGAT (6 punts)
  0: (5335.21, -147.46)              0: (5335.21, -147.46)
  1: (5210.14, -147.46) ← EIX        1: (5210.14, -147.46)
  2: (5210.14,  272.54) ← EIX        2: (5210.14,  272.54)
  3: (5335.12,  272.54)              3: (5335.12,  272.54)
                                     4: (5085.16,  272.54)  ← salta l'eix sencer
                                     5: (5085.07, -147.46)
```

El recorregut arriba a `x = 5335` (dreta) i **salta a `x = 5085`** (esquerra), creuant
tota la peça: **un llaç en forma de vuit**. El rectangle real fa 250 × 420 =
**105 000 mm²**; el contorn en donava **|−52 511|**, exactament la meitat, perquè els dos
lòbuls es cancel·len.

---

## 2 · El fix

Un helper privat nou, `_bucle_des_del_doblec`
([`aama_reader.py:650-712`](../../backend/fhort/patterns/engine/aama_reader.py#L650)),
i una crida que li passa `closed`
([`:593`](../../backend/fhort/patterns/engine/aama_reader.py#L593)).

**Què fa**, en tres passes:

1. **Marca** els punts d'eix amb `_on_axis` (el criteri que ja hi havia).
2. **Localitza la tirada contigua** d'eix, cíclicament: l'inici és el punt marcat el
   predecessor cíclic del qual no ho és. Si n'hi ha més d'una tirada, o cap, o la tirada
   té un sol punt, **es torna el bucle tal com és** — sense una frontissa de dos extrems
   no hi ha res a normalitzar, i endevinar seria pitjor que no fer res.
3. **Reconstrueix** el bucle com `[extrem_final] + no-eix + [extrem_inicial]`, de manera
   que la vora del doblec passa a ser l'aresta de tancament.

**Els punts d'eix INTERIORS a la tirada cauen, i han de caure.** La vora del doblec
desapareix en desplegar —queda a dins de la peça sencera— i només en sobreviuen els dos
extrems, que són la frontissa. Mantenir-los feia que el contorn baixés per l'eix i
tornés a pujar: una punta que es toca a ella mateixa, i és el que menjava el 4 % de les
dues faldilles del MEREDITH.

**Què NO fa:** cap punt no es mou, cap coordenada no canvia, cap reordenació no es
persisteix com a decisió i el signe global no es toca. **Es normalitza la VISTA del
bucle** —per quin vèrtex es llegeix, que en un bucle tancat és una llibertat que no vol
dir res— i prou.

**Les vores OBERTES entren com sempre**: no tenen aresta de tancament i no es poden
girar. Per això la normalització va darrere de `closed=b.closed` i no s'aplica a totes.

**Amb l'eix ja als extrems la funció és la identitat** — retorna l'objecte d'entrada. Per
això el fixture sintètic existent (`CONTORN_MITJA_PECA`, eix als índexs 0 i n−1) i els
tests de doblec que ja hi havia (`DoblecTest`, `ReplegatDoblecTest`) **no els toca res**.

---

## 3 · La taula 13/13, abans i després

Àrea signada (shoelace) en mm². «A esperada» = 2 × la meitat. 🚨 = el llegat fallava.

| peça | n | eix idx | A meitat | A esperada | ABANS | ràtio | DESPRÉS | ràtio |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| MER `FRONT_&_BACK_SHOULDER_LACE` | 4 | `[0, 1]` | 15 800 | 31 600 | 23 700 🚨 | 1,500 | **31 600** | **2,000** |
| MER `NECK_LACE` | 4 | `[0, 1]` | 7 800 | 15 600 | 11 700 🚨 | 1,500 | **15 600** | **2,000** |
| MER `BACK_RUFFL` | 41 | `[0, 39, 40]` | 99 765 | 199 529 | 195 317 🚨 | 1,958 | **199 529** | **2,000** |
| MER `FRONT_RUFFL` | 41 | `[0, 39, 40]` | 87 766 | 175 533 | 171 584 🚨 | 1,955 | **175 533** | **2,000** |
| MER `base_esqu` | 93 | `[0, 92]` | 131 023 | 262 047 | 262 047 | 2,000 | 262 047 | 2,000 |
| CAL `1` | 22 | `[0, 21]` | −138 025 | −276 049 | −276 049 | 2,000 | −276 049 | 2,000 |
| CAL `3` | 6 | `[0, 1, 2]` | −13 518 | −27 036 | −18 380 🚨 | 1,360 | **−27 036** | **2,000** |
| CAL `7` | 8 | `[0, 7]` | −10 957 | −21 913 | −21 913 | 2,000 | −21 913 | 2,000 |
| CAL `8` | 7 | `[0, 6]` | −6 624 | −13 247 | −13 247 | 2,000 | −13 247 | 2,000 |
| CAL `11` | 10 | `[1, 2, 3, 4, 5]` | −9 604 | −19 208 | −8 976 🚨 | 0,935 | **−19 208** | **2,000** |
| CAL `13` | 6 | `[1, 2, 3]` | −18 455 | −36 911 | **6** 🚨 | −0,000 | **−36 911** | **2,000** |
| CAL `14` | 4 | `[1, 2]` | −52 511 | −105 023 | **+52 511** 🚨 | −1,000 | **−105 023** | **2,000** |
| CAL `16` | 28 | `[0, 27]` | −63 968 | −127 937 | −127 937 | 2,000 | −127 937 | 2,000 |

### 3.1 🚨 Correcció al cens: eren 8, no 6

El cens (§5.2 de `QA_TALLER_D`) va comptar **6 trencades i 7 correctes**, i va marcar
`BACK_RUFFL` i `FRONT_RUFFL` com a ✅ atribuint el 1,96 a la curvatura. **Era fals.** La
causa és el tercer punt d'eix (`idx 40`, a `y = 717,98`, entre els extrems `y = 1420,07`
i `y = 705,98`): el contorn desplegat baixava de dalt de l'eix fins a `y = 718` i tornava
a saltar amunt al mirall, i el triangle espuri es menjava 4 212 mm².

**El recompte bo és 8 trencades i 5 correctes**, i el criteri separador exacte és
**«exactament dos punts d'eix, als índexs 0 i n−1»**. Les 5 correctes el compleixen totes;
cap de les 8 no el compleix. Cap altra variable (CAD, orientació, nombre de punts) les
separa: el MEREDITH és PolyPattern i antihorari i també en té dues de trencades.

---

## 4 · Els tests

`backend/fhort/patterns/tests_desplegat.py` — **fitxer propi**, perquè la verificació
sigui proporcional al fix i es puguin córrer sols.

| test | què afirma |
|---|---|
| **T6** | àrea del desplegat = 2× la de la meitat (±1 %) **i el signe no es cancel·la** (`mitja · sencera > 0`, i la magnitud creix) |
| **T7** | cap contorn desplegat no es creua a ell mateix (creuament PROPI, no tangència) · **+ control**: la meitat d'origen tampoc, perquè el test mesuri el fix i no el material |
| **T8** | on el llegat ja anava bé, el resultat és **idèntic punt a punt** · **+** cap punt del desplegat no és inventat: o és de la meitat o és el mirall exacte d'un punt de la meitat |
| **T9** | el cas mínim sintètic: el mateix quadrat obert pels seus **quatre** vèrtexs; les quatre rotacions són la MATEIXA peça i han de donar el mateix desplegat · + la tirada d'eix subdividida · + el braç prudent (sense frontissa, el bucle no es toca) |

**T8 no té cap llista de peces escrita a mà.** Qui decideix quines hi entren és **el
llegat, executant-se**: `_mirall_llegat` és una còpia literal del `_mirror_points`
d'abans del fix, i una peça hi entra si el llegat ja li donava el doble d'àrea. Així el
test no depèn de cap recompte — ni del meu, que ja s'ha vist que era d'un.

**T9 bateja les rotacions per on cau l'eix**, que és el que decideix:
`eix_al_tancament` (0 i n−1, l'única que el llegat resolia), `eix_al_principi` (0,1),
`eix_al_mig` (1,2), `eix_al_final` (2,3).

### 4.1 Sortida

```
$ python -m unittest fhort.patterns.tests_desplegat
................
----------------------------------------------------------------------
Ran 16 tests in 4.483s

OK
```

### 4.2 🔑 Que caçen el defecte, provat

Un test que no pot fallar no prova res. Amb `_bucle_des_del_doblec` **neutralitzat a
identitat en memòria** (cap fitxer tocat, cap `git stash`):

```
>>> fix NEUTRALITZAT: _bucle_des_del_doblec = identitat
Ran 16 tests — FAILED (failures=18)
```

I les fallades anomenen **exactament les 8 peces trencades**:

```
T6 àrea:  MEREDITH:FRONT_&_BACK_SHOULDER_LACE · MEREDITH:NECK_LACE ·
          MEREDITH:BACK_RUFFL · MEREDITH:FRONT_RUFFL ·
          CALLIE:3 · CALLIE:11 · CALLIE:13 · CALLIE:14
T6 signe: CALLIE:11 · CALLIE:13 · CALLIE:14
T7 creu:  CALLIE:3 · CALLIE:11 · CALLIE:13
T9:       eix_al_principi · eix_al_mig · eix_al_final · tirada subdividida
```

8 trencades + 5 que ja anaven bé = les 13. **T8 no falla mai** en aquesta correguda, que
és el que ha de passar: les 5 que anaven bé anaven bé abans i després.

### 4.3 Fixtures nous

Dos, seguint la política **ja escrita** al `README.md` del directori (*«material CAD real
versionat a git deliberadament… és l'única manera que els tests del motor s'executin
contra el format de veritat»*), amb la fitxa de procedència de rigor.

| fixture | mida | per què cal |
|---|---:|---|
| `CALLIE_prova.dxf` | 101 860 B | l'**ÚNIC** material en sentit horari (30/30) i **sense `Author:`**; 6 peces amb doblec amb **totes** les topologies d'eix que trencaven (tirades de 2, 3 i 5 punts; als extrems i al mig) |
| `MEREDITH_prova.dxf` | 464 287 B | PolyPattern i **antihorari** —del costat «bo»— i tanmateix **2 de 5 trencades**: és la prova que el defecte és de l'**ORIGEN del bucle**, no del sentit del CAD. Porta l'únic cas «trencat de poc» (1,96×), el que el cens va donar per bo |

> ⚠️ **Decisió que val la pena que Agus revisi abans del push:** el MEREDITH són 464 KB,
> el fixture més gros del directori (el TATE en fa 332). Es paga perquè **cap material
> sintètic no reprodueix aquest cas** —depèn d'una llibertat del format que només el CAD
> real exercita— i perquè sense ell el defecte semblaria una peculiaritat del CALLIE.
> Si es vol estalviar, es pot deixar només el CALLIE: T6/T7/T8 continuen passant amb 6
> peces en comptes de 13, i es perd el cas del 1,96 %.

---

## 5 · Conseqüències, dites clares

1. 🚩 **El fix és del camí d'IMPORTACIÓ, i actua sobre imports NOUS.**
   `unfold_piece` es crida a
   [`views.py:430-431`](../../backend/fhort/patterns/views.py#L430), i el que en surt és
   el que es persisteix com a `PatternPoint`. **Els patrons ja importats conserven la
   geometria trencada**: per beneficiar-se'n han de tornar a passar per l'import. Com que
   `PatternFile` és immutable de facto (versió nova = fila nova), reimportar és el camí
   normal — però **no passa sol, i ningú no ho notificarà**.
2. **El nombre de punts baixa a 5 de les 13 peces** (els punts d'eix interiors podats):
   MER `BACK_RUFFL` 41→40 · MER `FRONT_RUFFL` 41→40 · CAL `3` 6→5 · CAL `11` 10→7 ·
   CAL `13` 6→5. Geomètricament no canvia res (eren col·lineals sobre l'eix).
3. **Cap informació de grading no es perd al material actual.** Comprovat: els punts
   podats del MEREDITH porten `grade_rule = 1`, i **tota** la vora porta la mateixa regla,
   o sigui que no era informació única; els del CALLIE no en porten cap (`None`).
   🚩 **Límit conegut:** un CAD que graduï la vora del doblec de manera NO uniforme
   perdria una regla per punt podat. No passa a cap dels 8 fitxers del material.
4. 🚩 **`fold_piece` ja no reconstrueix els punts d'eix interiors.** El replegat de
   sortida ([`export.py:215`](../../backend/fhort/patterns/export.py#L215)) donarà la vora
   del doblec amb 2 punts en comptes de 3 on n'hi havia. Geomètricament idèntica
   (col·lineals), però el DXF exportat difereix del d'origen en aquelles 5 peces.
   **El comparador de round-trip no s'hi veu afectat**: treballa des de `read()` directe i
   no passa per `unfold_piece` (v. el comentari de `views.py:422-424`).
5. **No cal reiniciar res per als tests.** Si es vol veure el fix en viu a staging, cal
   que Agus reiniciï `ftt-staging` quan toqui — el gunicorn serveix el codi de quan va
   arrencar. **No s'ha tocat cap servei.**

---

## 6 · El que queda PROHIBIT i pendent de ratificació (Patró C)

> Perquè la sessió següent no ho confongui amb feina feta. **Res d'això no s'ha tocat.**

| pendent | estat |
|---|---|
| **La convenció CCW + origen mín(y,x)** | ❌ **NO implementada.** El fix normalitza *localment i a l'ús* el bucle dins de `unfold_piece`, i **no imposa cap convenció global**. És deliberadament compatible amb qualsevol que es ratifiqui després. |
| `PatternSegment` / `SegmentPreference` / qualsevol fracció desada | ❌ **NO tocats.** Cap `t_inici`/`t_fi` no s'ha recalculat ni invalidat. |
| Camp de sentit (`invertit`) a `SewRelation` | ❌ **NO afegit.** El matcher continua calculant el sentit relatiu i llençant-lo ([`seam_proposals.py:246`](../../backend/fhort/patterns/seam_proposals.py#L246)). |
| `seam_matching` · writer DXF/RUL · motor de cotes · verificador de round-trip | ❌ **NO tocats.** Zero línies. |
| Migracions | ❌ **Cap.** `makemigrations --check` → *No changes detected*. |
| Frontend | ❌ **No tocat.** El diff no toca cara: cap `npm run build`, cap eslint (no s'hi esperava i no ha calgut). |

**La pregunta oberta segueix sent la del cens §6.4:** què es fa amb les fraccions **ja
desades** el dia que es ratifiqui la convenció. `PatternSegment` es pot recalcular (la
geometria hi és); `SegmentPreference` potser no, i és justament el model dissenyat per
sobreviure el patró on va néixer.

---

## 7 · Verificació proporcional i commits

```
manage.py check                    → System check identified no issues (0 silenced).
makemigrations --check --dry-run   → No changes detected
python -m unittest fhort.patterns.tests_desplegat → Ran 16 tests … OK
```

*(`check` i `makemigrations` s'han corregut amb `SECRET_KEY`/`DB_*` de rebuig: el `.env`
real no s'ha obert i cap dels dos no contacta la BD per fer la seva feina.)*

| commit | concern |
|---|---|
| `3b7e4841` | **fix** — `_bucle_des_del_doblec` + la crida amb `closed` (1 fitxer, +67/−2) |
| `f8a6ea47` | **tests** — `tests_desplegat.py` (16 tests) + 2 fixtures + fitxa al README |
| *(el tercer)* | **informe** — aquest fitxer |

> Aquest informe es commita **a la branca** (`docs/diagnosis/`), que és on ha de viure
> per viatjar amb el fix. Se n'ha deixat una còpia idèntica al checkout principal
> (`/var/www/ftt-staging/docs/diagnosis/`) perquè es pugui llegir abans del merge, com
> els dos informes anteriors d'aquest fil.

Branca `s46-fix-desplegat`, worktree `/root/s46-unfold`. **Cap push.**
