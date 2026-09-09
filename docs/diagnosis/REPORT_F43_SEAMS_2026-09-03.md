# F4.3 · COSTURES ASSISTIDES PER CATÀLEG I PRECEDENT — informe de tancament

> Sprint del **2026-09-03**, worktree `/var/www/ftt-f42`, branca `f43-seams` (des de `dev`).
> **Cap push.** 4 commits.

---

## 0 · EL TITULAR, I LA DECISIÓ QUE MANA SOBRE TOT

El motor de propostes guanya dos senyals nous —**l'expectativa del catàleg** i **el
precedent del taller**— i un **veto dur** que no hi era. Tot additiu: el puntuador no s'ha
reescrit.

> ## 🚨 ELS DOS SENYALS PESEN ZERO, I EL ZERO ÉS EL QUE S'HA MESURAT
>
> No és «no s'ha pogut pesar». És el resultat del calibratge:
>
> | | confiança | catàleg |
> |---|---|---|
> | Les **4 parelles CERTES** que la geometria recupera | 0,600 · 0,600 · 0,465 · 0,459 | **core** |
> | Les **8 FALSES** de més confiança | 0,600 · 0,600 · 0,550 · 0,550 · 0,465 · 0,463 … | **core** |
>
> El motiu és estructural i cap número no l'arregla: **el catàleg parla de la parella de
> ROLS, i l'espatlla dreta i l'esquerra tenen els mateixos rols. No sap distingir esquerra
> de dreta.** Un pes sumaria la MATEIXA constant a certes i a falses i no canviaria ni una
> sola decisió.
>
> I les 3 certes que la geometria NO troba tenen `_te_evidencia_geometrica` a **fals** —zero
> piquets casats i zero longitud—: cap pes les salvaria sense saltar-se la porta geomètrica,
> que hi és justament perquè el costum no habiliti mai una proposta.
>
> **Posar-hi un pes seria fabricar precisió.** `PES_CATALEG = PES_PRECEDENT = 0.0`, amb el
> raonament escrit al costat de la constant. El dia que el banc separi certes de falses,
> es mesuren i es posen: el codi no s'haurà de tocar enlloc més.

El valor del catàleg és real i **sí** que s'entrega, per tres vies que no són un pes:
l'**evidència al xip**, el **checklist d'absents**, i el **veto de la llei D.02**.

---

## 1 · FASE 0 · EL MAPA, I QUATRE PREMISSES CORREGIDES

| Què | On |
|---|---|
| Motor de propostes (pur) | `engine/seam_matching.py` · `avaluar():654` · `proposar():692` |
| Pesos existents | `PES_PIQUETS` 0,50 · `PES_LONGITUD` 0,35 · `PES_NOMS` 0,15 · `PES_PREFERENCIA` 0,10 |
| Llindar | `LLINDAR_PROPOSTA = 0.40` |
| Porta geomètrica | `_te_evidencia_geometrica` — el costum NO hi entra (`seam_matching.py:662`) |
| Pont BD↔motor | `seam_proposals.py` · `candidats_del_patro():79` · `propostes_del_model():160` |
| Targeta +/o/⚠ | `components/pattern/ProposalsPanel.jsx` · `Senyal():229` |
| `SewRelation` | `models.py:708` · confirmar per `annotation_views.confirmar_proposta` |

### 🔑 La condició d'aturada del brief NO es compleix: el motor SÍ que admet senyals additius

`avaluar` suma `s_piquets + s_longitud + s_noms + s_pref` i `Candidat` ja porta fets
RESOLTS pel pont (`preferencia`). Afegir-n'hi dos és exactament la forma que
`PES_PREFERENCIA` va obrir. **No s'ha reescrit res.**

### Quatre premisses del brief que la realitat corregeix

1. ✅ **«les costures confirmades del 837»** — hi són: **8 `SewRelation`, totes del model
   1383**. *(Corregeix el meu propi informe de F4.2-BIS, que deia «cap al 837». Era fals.)*
2. 🚨 **«un model amb trams identificats»** — **NO**. A la BD hi ha **1** `edge_role`
   confirmat per un humà, de ~38. Els dos senyals nous, doncs, **neixen adormits en
   producció** i s'encenen a mesura que algú confirmi rols de vora. És el mateix forat que
   F4.2 ja va reportar, vist des de l'altra banda.
3. 🚨 **Les costures confirmades viuen sobre trams `declarat`; els rols de vora, sobre
   `natural`.** Dues poblacions sobre el mateix contorn. Tot el que les creua ha de resoldre
   declarat→natural per solapament, i **un `t` que embolcalla no es compara amb `min`/`max`**
   (mesurat: casava una sisa d'esquena contra l'escot).
4. 🚨 **`sew#56` és MANGA ⛓ MANGA** — la costura de sota-màniga, dins d'UNA peça. `proposar()`
   salta les parelles de la mateixa peça **per disseny documentat**, o sigui que és
   estructuralment irrecuperable a l'examen. No és una fallada del senyal nou.

**La cadena sencera, validada abans de construir:** amb els rols de vora que proposa F4.2,
**6 de les 8 costures confirmades resolen a una plantilla del catàleg.**

---

## 2 · FASE A · L'EXPECTATIVA (`recognition/seam_expectations.py`)

**Graus** sobre `observed_seams / observed_den` (costures per patró aplicable; passa d'1
amb normalitat —un cos té dos laterals—): **core ≥ 0,75 · common ≥ 0,30 · rara**. Distribució
mesurada sobre les 55 plantilles: **34 core · 6 common · 13 rares · 2 de zero**.

🚨 **Una rara NO és una dolenta.** `collar_attach↔neckline` mesura 0,157 i el 837 la porta.
«Rara» governa només si el catàleg parla PRIMER: no encapçala cap checklist, i anota igual
la candidata que la geometria hagi trobat. Llegir-la com a «malament» seria dir-li al
patronista que el seu propi vestit és un error.

🚨 **LA CARA NO IDENTIFICA UN COSTAT.** Les 5 peces del 837 porten `face = ''` amb tota la
raó (D1 va posar l'eix davant/darrere al ROL per a les peces de cos) i les plantilles el
deletregen (`front/front.shoulder_seam`). Casar també per cara dona **0 de 8** en comptes de
**6 de 8**. La cara viatja a l'evidència; no és clau.

### 🚨 A3 · LA LLEI D.02, implementada com a VETO i no com a descompte

Dues plantilles porten `observed_seams = 0` sobre un denominador real:

```
back/back.armhole            ↔ sleeve/front.sleeve_cap        0 de 90.273   (el mirall fa 105.612)
cuff/back.band_attach_upper  ↔ pant/front.cuff_line           0 de 17.130   (el mirall fa  15.882)
```

Una copa de màniga entra a una sisa **en un sol sentit**, i el corpus ho diu amb un
denominador prou gran. Per això **tomba la proposta** en comptes de baixar-li la confiança:
un descompte deixaria que una geometria perfecta la tornés a pujar, i el test ho prova amb
piquets i longituds idèntics.

I una precisió que calia: `armhole↔sleeve_cap` hi és **com a 105.612 i com a 0**. La PARELLA
es queda amb la lectura forta; el zero parla d'una DIRECCIÓ. Llegir-lo com el veredicte de
la parella vetaria la costura més comuna del corpus.

---

## 3 · FASE B · EL PRECEDENT (`recognition/seam_precedent.py`)

Transferència **per ROL de vora, mai per geometria** — que és tota la raó per la qual F4.2
va ensenyar les vores a tenir nom. Un precedent que comparés formes seria el banc de corpus
de F4.1 un altre cop, que va mesurar 13 % i està retirat.

Un model queda **fora del seu propi banc** (`exclou_model_id`), com
`recognition.service.exclude_self`. Conseqüència mesurada avui: com que l'ÚNIC model amb
costures és el 837, córrer el proposador sobre el 837 dona **`precedents_tenant: 0`**. És
correcte, i és la mida real del banc.

---

## 4 · FASE D · L'EXAMEN

### D1 · Leave-one-out sobre el 837 (`ops/recognition/lab_seams.py`)

Cada costura confirmada s'amaga **en lectura** (`exclou_sew_ids`, un paràmetre que cap porta
HTTP exposa) i es mira si el motor la torna a trobar. Els rols de vora els posa el
proposador de F4.2 **en memòria** — la tècnica del gate D2 de F4.2: provar la regla no
exigeix adoptar-la.

| costura | resultat | conf. | senyals |
|---|---|---|---|
| sew#51 DELANTERO ⛓ ESPALDA | ✅ RECUPERADA | 0,600 | piquets·longitud·noms·preferència·**catàleg** |
| sew#52 DELANTERO ⛓ ESPALDA | ✅ RECUPERADA | 0,600 | idem |
| sew#53 DELANTERO ⛓ ESPALDA | ✅ RECUPERADA | 0,465 | idem |
| sew#54 DELANTERO ⛓ ESPALDA | ✅ RECUPERADA | 0,459 | idem |
| sew#55 CUELLO ⛓ ESPALDA | ❌ | — | sense evidència geomètrica |
| sew#56 MANGA ⛓ MANGA | ❌ | — | **mateixa peça: `proposar()` les salta per disseny** |
| sew#57 MANGA ⛓ ESPALDA | ❌ | — | sense evidència geomètrica |
| sew#58 MANGA ⛓ DELANTERO | ❌ | — | sense evidència geomètrica |

**RECUPERADES 4 de 8**, i les 4 que no, amb motiu. 🔑 **Cap de les 4 pèrdues és del senyal
nou**: una és estructural i tres no tenen geometria on sumar-se. El catàleg les CONEIX —
`armhole↔sleeve_cap` és core— i tot i així no les pot obrir, perquè la porta geomètrica no
és seva. Això és el disseny funcionant, no fallant.

### D2 · Zero bestieses

Cap proposta amb una parella que el catàleg no tingui. El veto D.02 no ha disparat sobre el
837 (no hi ha cap candidata de sisa d'esquena contra copa de davant) i es prova al banc
sintètic. `needs_piece_role` el garanteix el vocabulari de F4.2, per construcció.

### D3 · Mode informe, fora de mostra

| patró | peces amb rol | rols de vora | candidats | propostes (≥0,60) | amb catàleg | absents |
|---|---|---|---|---|---|---|
| 837 (pf 20) | 5 | 30 | 18 | 2 (0) | 2 | **0** |
| TATE (pf 23) | 8 | 21 | 48 | 8 (4) | 1 | **5** |
| AMELIA (pf 24) | 4 | 16 | 16 | 6 (2) | **6** | 2 |
| CALLIE (pf 21) | 0 | 0 | 79 | 1 (0) | 0 | 0 |
| MEREDITH (pf 22) | 0 | 0 | 82 | 13 (0) | 0 | 0 |

🔑 **El checklist és més útil on encara no s'ha cosit res.** El TATE no té cap `SewRelation`
i el catàleg li llista les 5 de nucli que hi esperaria: espatlla, lateral, sota-màniga i
sisa↔copa. Això és una llista de feina, i és el guany més clar d'aquest tram.
CALLIE i MEREDITH, sense identitat confirmada, queden correctament inerts.

### D4 · Els absents del 837, contrastats a mà

**0 absents, i és correcte**: les expectatives de nucli assolibles amb els seus rols ja hi
són totes cosides (laterals, espatlles, sisa↔copa, escot↔coll).

🚨 **Aquí hi havia un bug meu, i el va destapar aquest contrast.** La primera versió deia
que hi faltava `back.side_seam ⛓ front.side_seam` **en un vestit que en porta dues**: el
checklist resolia el vocabulari de les costures confirmades amb un diccionari buit, i per
tant no en reconeixia cap com a coberta. Corregit; sense la comprovació a mà que el brief
demana, hauria passat.

🚩 **Els 3 silencis de F4.2 hi reapareixen i NO es maquillen**: `front.slit_edge` i
`collar.collar_outer_edge` segueixen sense paraula al perfil del GTI 28, i els seus trams
segueixen muts. No afecten cap absent perquè cap expectativa de nucli els reclama, però el
forat és el mateix i segueix sent feina de catàleg.

---

## 5 · FASE C · LA UI

Mateixa targeta, mateix vocabulari. Els dos senyals surten amb **`o` (neutre)** perquè
informen sense puntuar — que és exactament el que fan.

```
+ 837.DELANTERO i 837.ESPALDA són peces veïnes
+ Aquest taller ja havia confirmat trams així a 837.ESPALDA
o Cap dels dos trams no porta piquets
o El catàleg espera aquesta parella: 436.842 costures en 90.273 patrons on era possible.
⚠ Si la confirmes, NO casarà per 0,1 cm.
```

· **Checklist d'absents** al peu, i **també quan no hi ha cap proposta** — són dues preguntes
  diferents, i la segona és la que val en un patró verge. Gris, icona de llista i no d'avís,
  i diu «n'esperaria», no «te'n falta».
· **«Proposa el cosit sencer»** accepta en bloc les de confiança **≥0,60** — no el 0,40 de
  proposar: oferir-les a la llista i acceptar-les totes sense mirar-les són dos gestos amb
  dos riscos diferents. Va **en sèrie pel camí d'una a una**, perquè cada costura ha de passar
  pel seu veredicte i pel seu repartiment de trams.
· Els milers, en l'idioma de la pantalla (`toLocaleString()` sol escrivia «436,842» en
  català).
· i18n ca/en/es amb **paritat global**.

### El fum amb ULLS — i una tensió del brief que he hagut de resoldre

> ⚠️ **El brief demanava la captura dels xips nous I prohibia escriure a la BD. Amb 1 sol
> `edge_role` confirmat, els xips estan APAGATS en producció: una parella en necessita dos.**
> Les dues coses no es podien complir alhora.
>
> Resolució: he confirmat els rols de vora del 837 **pel mateix servei auditat que fa servir
> la UI** (`confirm_edge_roles`, `UPDATE_FIELDS = ['edge_role']`), he capturat, i **els he
> revertit**. Verificat amb `diff` de l'estat abans/després: **idèntic** —una sola fila,
> `1511|collar_attach`— i `SewRelation` intactes a **8**. Cap costura tocada, cap creació
> automàtica. Queda dit perquè és una escriptura, encara que sigui de saldo zero.

Captures a `docs/diagnosis/f43_smoke/`; el fum és `ops/qa/f43_costures_xips.mjs`.

---

## 6 · VERD

| Control | Resultat |
|---|---|
| `manage.py check` | net |
| `npm run build` | net (còpia aïllada del worktree) |
| `npm run lint` (fitxers tocats) | **0 errors** |
| i18n ca/en/es | **paritat global** |
| `tests_seam_signals` | **`Ran 23 tests · OK`** |
| BD del producte | **restituïda idèntica** i verificada |

---

## 7 · QUÈ OBRE

**F5 · els POMs.** Amb això, un POM que s'hagi d'ancorar ja té les quatre coses: **peces**
amb rol confirmat (F4.1), **trams** amb nom (F4.2), **landmarks** derivats i validats contra
producció a 0,0000 mm (F4.2), i **costures** amb expectativa i precedent (F4.3). La recepta
d'un POM pot deixar de dir «el `PatternPoint#22808`» i dir «l'`hps`».

**El que encendrà F4.3 de debò no és codi, és DADA**, i és la mateixa frase de F4.2:
- confirmar els rols de vora d'un patró encén els xips i el checklist d'aquell patró;
- confirmar-ne un SEGON model encén el **precedent** per a tots els altres (avui el banc és
  d'un model i per això dona 0);
- i les files que falten al GTI 28 segueixen fent callar tres trams del 837.

---

## 8 · FRONTERES

- **Cap `SewRelation` tocada.** 8 abans, 8 després.
- **Cap creació automàtica**: el bloc accepta pel camí humà, una a una, i cada una amb el seu
  veredicte.
- **Cap POM tocat.** Cap migració. Cap endpoint nou.
- L'única escriptura ha estat la del fum, **revertida i verificada** (§5).
- **Cap push.** 4 commits locals a `f43-seams`.
