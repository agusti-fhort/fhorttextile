# El fix de la niada morta — ordres de grading sobre la línia de cosit

**Patró B · staging `dev` · CAP push · CAP escriptura a BD.** Tota la mesura es fa dins
d'un `transaction.atomic()` amb `set_rollback(True)`; cap `ExportAcknowledgement`, cap
reconeixement, cap export real. Els tests **s'escriuen i no s'executen** (llei 23/08).

Causa diagnosticada a [`INFORME_NIADA_SENSE_MOVIMENT_2026-08-24.md`](INFORME_NIADA_SENSE_MOVIMENT_2026-08-24.md).

---

## RESULTAT EN UNA LÍNIA

La niada del 1383 passa de **1 regla i 0 punts moguts** a **37 regles i 984 punts moguts**,
i **8 dels 14 POMs claven el delta a totes les talles**. Els altres 6 no hi aterren per
dues limitacions que aquest sprint tenia prohibit tocar, i ara es diuen a la pantalla amb
la xifra al davant en comptes de sortir com una columna de ⚠ sense explicació.

| | abans | després |
|---|---|---|
| Regles a la taula (RUL) | 1 (només `REGLA_ZERO`) | **39** (38 actives) |
| Punts moguts · M/L/XL | 0 | **984** |
| Punts moguts · XS | 0 | 467 |
| POMs que claven el delta | 0 de 14 | **8 de 14** |
| Autovalidació | «1/1 regles idèntiques» (verd sobre el no-res) | **39/39**, 3.840 punts, 0,000 µm |
| Problemes d'escalat dits | cap | **6, amb xifra i causa** |

---

## EL FIX

### 1. La normalització (el canvi de fons)

`engine/operations.py` · `_normalitzar_ordres_al_tall`, cridada la PRIMERA de tot a
`_move_piece` — abans que res, perquè si anés després `_propagar_al_cosit` ja hauria
esborrat les ordres i estaríem normalitzant un zero.

Tota ordre que aterra sobre un punt de **gir** de la línia de cosit es trasllada al seu
company del **tall** amb el mateix desplaçament. Després la propagació de sempre re-deriva
el cosit, i les dues línies es mouen juntes amb el marge de costura constant.

L'aparellament és **gir de cosit ↔ gir de tall més proper**, deliberadament la mateixa
regla que fa servir `_propagar_al_cosit`: si aquí normalitzéssim contra un altre punt, la
propagació aniria a buscar-ne un que no duria cap ordre i el desplaçament es tornaria a
perdre. Amb la mateixa regla, el que injectem és exactament el que ens torna.

Les tres sortides, cap en silenci:

| cas | què passa |
|---|---|
| el company del tall ja té una ordre **idèntica** | fusió; callar aquí és legítim |
| el company del tall té una ordre **diferent** | `ordre_cosit_en_conflicte` · l'ordre del cosit **no s'aplica** i mana el tall |
| **no hi ha company** a menys de 30 mm | `ordre_cosit_sense_company` · es deixa on era |

En els dos casos d'error el comportament és el d'abans —dolent però conegut— i el problema
puja a la llista del modal. Inventar un company, o decidir quin dels dos POMs mana, no és
feina d'aquesta capa.

### 2. La correcció que les xifres van obligar a fer

**La primera versió normalitzava TOTES les ordres del cosit, també les de corba. Estava
malament, i es va veure mesurant.** Una corba no té parella a la propagació —el cosit es
re-deriva dels girs i la corba hi torna a fluir—, o sigui que traslladar-li l'ordre al tall
no és neutre: és perdre-la.

Mesurat al 837, talla M:

| | POM A | POM C | POM S2 |
|---|---|---|---|
| normalitzant també les corbes | +1,577 | **+1,500** | +0,353 |
| deixant-les on són (el que s'ha entregat) | **+3,075** | **+3,000** | +0,727 |
| el que el grading mana | +3,000 | +3,000 | +0,800 |

Per això `_propagar_al_cosit` rep ara les ordres originals i **respecta els ancoratges
propis del cosit que no són girs** en re-derivar la vora. És el mínim per no fer una
regressió: sense això, el fix hauria arreglat B, D, F i J1 i hauria trencat A, C i S2.

### 3. Els problemes d'escalat, dits amb la xifra

`export.py` · `_problemes_escalat` → nou camp `ExportResult.problemes_escalat`, servit a
`views.py::_preview_payload` i pintat a la mateixa llista del modal
(`ExportModal.jsx`, 3 línies; cap text nou, o sigui **cap clau i18n nova**).

Hi entren dues coses: els conflictes/orfes del motor (deduplicats — el mateix punt es
queixa a cada talla, i cinc vegades la mateixa frase ofega la resta de la llista) i **cada
POM la re-mesura del qual no aterra al delta**, amb la talla on més es nota, les dues
xifres i la causa. Llindar 0,05 cm: mig mil·límetre és més fi que el que una taula de tall
distingeix.

---

## LA VERIFICACIÓ

### La contraprova del diagnòstic, repetida SENSE neutralitzar res

El diagnòstic va provar la causa neutralitzant `has_sew` en una còpia en memòria. Ara es
repeteix pel **camí de producció**, i es compara amb aquella referència. Talla M:

```
POM   extrems  manat    producció  residu  |  contraprova v1 pura  residu
E7    gir-gir   0.000     0.000     0.000  |         0.000         0.000
A     gir-CORBA 3.000     3.075     0.075  |         3.075         0.075
B     gir-gir   3.000     3.000    -0.000  |         3.000        -0.000
C     CORBA-gir 3.000     3.000     0.000  |         3.000         0.000
D     gir-gir   3.000     3.000     0.000  |         3.000         0.000
E     gir-gir   0.600     0.529    -0.071  |         0.529        -0.071
F     gir-gir   2.000     2.000     0.000  |         2.000         0.000
S     gir-gir   0.800     1.874     1.074  |         1.874         1.074
SLT   gir-gir   0.000     0.000     0.000  |         0.000         0.000
E1    gir-gir   0.300     0.120    -0.180  |         0.120        -0.180
G1    gir-gir   0.000     0.000     0.000  |         0.000         0.000
S2    CORBA-gir 0.800     0.727    -0.073  |         0.727        -0.073
J1    gir-gir   0.250     0.250     0.000  |         0.250         0.000
U     gir-gir   0.000     0.000     0.000  |         0.000         0.000
```

**Les dues columnes són idèntiques als 14 POMs.** El camí de producció fa exactament el que
la contraprova prometia: el fix no hi afegeix res de seu i no en perd res. Els residus que
queden ja hi eren i són els de la projecció v1, no els de la propagació al cosit.

### Els controls

| control | resultat |
|---|---|
| `python manage.py check` | **net** (0 issues) |
| `npm run build` | **verd** (987 ms) — i staging serveix `frontend/dist`, o sigui que ja hi és |
| `npx eslint src` | **0 errors** (273 warnings preexistents; l'única d'`ExportModal.jsx` és a la línia 70, que no s'ha tocat) |
| `build_export(PF20, GV201)` sencer | 502.748 B de DXF + 2.877 B de RUL, autovalidació ✅ |

> **Correcció (24/08, sprint del writer).** Aquesta taula deia «37 regles · 37/37» perquè la
> xifra es va prendre d'una execució ANTERIOR a l'últim canvi del sprint (la propagació que
> respecta els ancoratges propis del cosit). Amb el codi entregat en són **39 · 38 actives ·
> 39/39**: recuperar l'ancoratge de corba mou dos piquets més, i un piquet que es mou és una
> regla nova. La resta de la taula es manté.
| smoke de navegador | **19 ✓ · 0 ✗** |

### El smoke de navegador (llei «build verd ≠ front viu»)

`ops/qa/qa_niada_cosit_1383.py` — obre `/models/1383?tab=Patró`, clica **Exporta** i llegeix
la taula de pre-reconeixement de debò. Sense JWT (l'agent no en pot emetre): serveix el
bundle real de `frontend/dist` i stubeja `/api/`.

**El stub NO és inventat.** `ops/qa/payload_niada_1383.json` és la resposta literal del
backend, generada amb `_preview_payload(build_export(fp, 201, 'polypattern'))` contra el banc
viu en lectura avortada. La meitat de backend està mesurada al banc; aquest fitxer mesura que
la pantalla la pinta.

El que passa: ① el modal ofereix la GV201 (v9, 105 specs) · ② la taula pinta 5 talles × 14
POMs · ③ B, D, F i J1 sense cap ⚠ a cap talla · ④ la base (S) neta · ⑤ els 6 residus a la
llista amb la xifra i la causa · ⑥ 38 regles actives i autovalidació 39/39 · ⑦ cap error de
consola. Captura: `ops/qa/captures/niada_cosit_modal.png`.

### Els tests (ESCRITS, no executats)

`backend/fhort/patterns/tests.py` — 12 tests en dues classes noves:

`OrdresSobreLaLiniaDeCositTest` (8) — el POM ancorat sobre el cosit mou les dues línies i la
re-mesura clava el delta · el mateix a quatre deltes diferents amb el marge conservat · el
conflicte tall/cosit es diu en veu alta amb les dues xifres i el nom del POM · l'ordre
idèntica es fusiona sense cridar · l'ordre sense company es diu i no s'inventa res ·
`has_sew=False` es comporta exactament com abans · una ordre sobre el TALL no canvia gens ·
l'ancoratge sobre corba conserva el seu moviment.

`ProblemesDEscalatTest` (4) — el residu es diu amb la xifra i a la talla on més es nota · un
POM de girs no s'acusa a la corba · un residu per sota de la tolerància no diu res · el
mateix conflicte a cinc talles es diu una vegada.

> El banc vell no podia veure el defecte: `SewCosidorAMBTallTest` mou `PointRef('P', 0, 2)`
> —la vora **0**, el TALL— i tot `EscalatTestBase` ancora a `boundary_index=0`. Cap test
> ancorava mai sobre la vora `SEW`, que és el 100 % del cas real. Aquestes dues classes
> tanquen aquell forat.

---

## EL QUE NO S'HA ARREGLAT (i s'ha deixat dit)

**Els ⚠ no desapareixen de totes les files recta/vora.** El brief ho esperava; les xifres
diuen una altra cosa i val més dir-la. 6 dels 14 POMs conserven ⚠, per dues causes que
aquest sprint tenia prohibit tocar:

**R1 · Ancoratge sobre punt de CORBA (A, C, S2).** El lliurable només porta regla als punts
de gir i als piquets (`_regles_des_dels_deltes`): el moviment d'un extrem de corba **no
arriba mai al fitxer** i el CAD del client el fa fluir. La geometria de treball el clava
(taula de dalt: C a +3,000); la geometria reconstruïda des de les regles —que és el que
l'ExportModal mesura i el que el client rebrà— no. **A la XL, C creix 4,50 cm dels 9,00 que
mana el grading.** Això és el residu «A5» del diagnòstic, i **no són els 0,074 cm que el
brief donava per fets**: aquell número sortia de la contraprova que movia punts directament,
no del camí de les regles. És la xifra que decideix si això és de segon ordre o no.

**R2 · Repartiment simètric de la projecció v1 (E, S, E1).** Els dos extrems són girs i el
moviment hi arriba sencer; el que no aterra és **com** es reparteix. La v1 mou els dos punts
en sentits oposats al llarg de la recta a→b, i amb un POM de mètode `vora` (S: arc, no
recta) o amb dos POMs que comparteixen ancoratge (E1 i S2 comparteixen el punt 49 de
l'ESPALDA) el creixement resultant no és el manat. **S creix 5,76 cm a la XL quan n'havia de
créixer 2,40.** Ja documentat com a decisió pendent («backlog §3.5, amb la Montse davant»).

**R3 · Dues costures deixen de casar a les talles grans — i això és NOU de veure.** Amb la
niada aturada totes les costures casaven, perquè no es movia res. Ara que es mou, la
validació diu:

```
                        geometria base        niada a la XL
   sew 51                Casa (7.6 = 7.6)     NO casa (8.5 vs 8.1 · 0.4 cm)
   sew 52                Casa (7.7 = 7.7)     NO casa (8.8 vs 7.7 · 1.1 cm)
   sew 53,54,55,57,58    no mesurables        no mesurables      (idèntic)
   sew 56                NO casa (0.2 cm)     NO casa (0.2 cm)   (idèntic)
```

**No és una regressió: és exactament el que el motor existeix per dir** («dues vores que
casaven a la talla mostra poden deixar de casar tres talles amunt; això és el que un CAD no
et diu»). Sis dels vuit veredictes són idèntics. Els dos que canvien són patronatge real que
apareix per primera vegada perquè per primera vegada hi ha niada. **Fora de l'scope
d'aquest sprint** (`NO TOCAR: costures/QA-TALLER-D`) i sense tocar.

**R4 · Els 6 POMs de mètode `projeccio` segueixen fora de la niada en veu alta**, com manava
el brief. No s'ha tocat res del filtre d'`adapters.py`.

---

## FITXERS TOCATS

| fitxer | què |
|---|---|
| `backend/fhort/patterns/engine/operations.py` | `_normalitzar_ordres_al_tall` + `_company_al_tall` + `_de_qui_tall` + `_poms_del_punt`; `_propagar_al_cosit` respecta els ancoratges propis; `MoveReport.punts_cosit_normalitzats`; docstring del mòdul amb la llei nova |
| `backend/fhort/patterns/export.py` | `_problemes_escalat`, `_extrems_de_corba`, `TOL_RESIDU_CM`, `ExportResult.problemes_escalat` |
| `backend/fhort/patterns/views.py` | `problemes_escalat` al payload del modal |
| `frontend/src/components/pattern/ExportModal.jsx` | 3 línies: la llista i el recompte |
| `backend/fhort/patterns/tests.py` | 2 classes, 12 tests (escrits, no executats) |
| `ops/qa/qa_niada_cosit_1383.py` + `ops/qa/payload_niada_1383.json` | el smoke de navegador i el payload real |

**Intocats, com manava el brief:** la projecció `GradedSpec→GradeRule`, el writer, el filtre
de `projeccio`/`ortogonal`, la GV201 (segellada) i les costures.

**Backend reiniciat** (`systemctl restart ftt-staging`, 15:38) perquè el gunicorn servís el
codi del disc; `npm run build` ja havia desplegat el front (staging serveix `frontend/dist`).
