# AUDITORIA DE MODEL — la peça que tanca el cercle FTT

> **Tipus:** disseny conceptual + intenció. NO és un pla executable encara — mereix
> sessió pròpia de disseny amb la Montse abans de cap brief.
> **Data d'origen:** 2026-07-16. **Autor:** sessió d'arquitectura Claude chat + Agus (Patró C).
> **Estat:** ANOTAT. Primera baula ja construïda i a PROD (`SewToleranceAcceptance`, deploy #3).
> **Naixement:** el veredicte de la Montse sobre la pinça 69-71 del Tate (primer defecte
> real trobat pel sistema en un patró de client).

---

## 0. EL TITULAR — PER QUÈ EXISTEIX

Tot el que FTT ha construït (mesures, grading amb segell, motor de patrons, escalat) genera
**senyals de coherència que fins ara viuen escampats** — cada mòdul avisa del seu forat pel
seu compte. L'auditoria de model és la capa que **els recull tots en un sol lloc** i respon
una pregunta que és **la del PM, no la del tècnic**:

> **"Això que enviem a producció, està bé?"**

Aquesta és la frase que **tanca el cercle comercial de FTT**: no és una eina de dibuix, és
la **garantia** que el que surt cap a la fàbrica no porta un defecte que costarà tela i hores.
És el que permet assegurar al PM que el lliurable està bé → evita costos i falles.

**La prova que ho valida ja existeix:** la pinça 69-71 del Tate. La Montse va confirmar que
és **defecte** (costats desiguals 1,3 vs 1,0 cm = 3,1 mm: trenca la geometria de la peça →
farà arruga o el cosidor haurà de retallar a mà). **Primer defecte real trobat pel sistema
en un patró de client** — exactament el cost que l'auditoria evita. Això és el que el Salva
ha de poder ensenyar.

---

## 1. QUÈ AVALUA (l'abast transversal)

Una capa que avalua, en un sol lloc, la coherència de:

- **Mesures** — el mesurat vs la fitxa, dins/fora de tolerància (ja existeix a G1/Size Check).
- **Grading** — segell fresc/estàle/desconegut (ja existeix: detector d'estalitud G6-B2), STEP
  invàlids, matrius amb forats, regles que aplanen a FIXED en silenci (G6-C, R4/R6).
- **Patró** — costures que no casen, pinces que no tanquen planes, cobertura de vora
  incompleta, orígens de mesura inconsistents (QA-TALLER-D).
- **Escalats de patró** — el grading projectat que no preserva longituds de costura (la
  troballa estrella de S7: el frunzit que casa a la base i falla des de la M).

**Recull els senyals que ja detecta cada mòdul** — no els reinventa. La feina nova és la
**vista transversal + el veredicte global**, no la detecció (cada sensor ja està validat pel
seu mòdul). Això la fa **molt més barata del que sembla i molt més sòlida**.

---

## 2. LES LLEIS FUNDACIONALS (no negociables)

### 2.1. TOLERÀNCIA ≠ ERROR
La distinció que ho ordena tot. Són dues coses que el sistema tracta diferent:

- **Variació normal** (ex: 2 mm en una costura de màniga, 51,3 vs 51,5): **s'absorbeix a mà
  sobre el matalàs de tela en producció.** El sistema **DIU "casa", NO proposa res.** Voler
  "corregir" 2 mm seria fabricar feina que la realitat de taller ja resol.
- **Error** (ex: 3,1 mm d'una pinça que no tanca plana): **asimetria que trenca la peça.**
  El sistema **informa amb la xifra.** El tècnic mira i decideix.

Al final, el tall i el cosit es fan **a mà sobre el matalàs** — el mil·límetre de tolerància
queda absorbit en producció. Aquesta realitat de taller és la que fixa que tolerància i error
són coses diferents.

### 2.2. DETECTA + INFORMA, MAI MODIFICA
El sistema **detecta** la incoherència i **n'informa** amb la xifra. **MAI modifica la
geometria** — sobirania del dibuix del tècnic (llei del motor: mai crea ni mou topologia).

⚠️ **La porta que NO s'obre sense sessió pròpia:** "proposar modificar la peça perquè encaixi".
Això és auditoria del patró + ajust de les incorreccions que transporta el dibuix del tècnic —
un mòdul sencer amb tres capes de profunditat:
1. Detectar la incoherència (ja ho fem a mitges).
2. Informar-ne amb la xifra (ja ho fem: l'avís).
3. **Proposar modificar la geometria** perquè encaixi → **xoca de front amb la sobirania del
   dibuix.** No s'obre de passada. Lliga amb **PAT-3 (rectificació post-fitting)** del backlog
   del motor.

### 2.3. EL TÈCNIC ACCEPTA O NO, I DEIXA RASTRE
El sistema gradua l'avís i informa; **el tècnic accepta o no accepta.** Ni bloqueja ni decideix
per ell. **Acceptar deixa rastre auditable** (qui, quan, quin desajust, contra quin llindar) —
i aquest rastre és exactament el que l'auditoria de model llegeix després ("aquí el PM va
acceptar un desajust gros conscientment").

### 2.4. ELS LLINDARS SÓN CRITERI, NO DOGMA
*"És d'intel·ligents tenir criteri, però el dogma és una altra cosa, i normalment on comencen
les guerres."* (Agus, 2026-07-16)

Els llindars viuen com a **constants documentades i afinables**, MAI com a lleis clavades al
motor. Un llindar fix decidit en una reunió és el que faria que d'aquí sis mesos el sistema
marqués en vermell una costura que la Montse cus sense pestanyejar → ella deixa de fer cas dels
vermells → els vermells no valen res. **El sistema proposa un número, l'ofici el corregeix.**
Igual que a tota la casa: geometria mana, criteri acompanya, qui té les mans a la tela decideix.

Aquesta llei és el mateix principi que sosté tot el sistema: **el que sap és auditable i mòbil,
mai clavat.** El segell que confessa quan no sap, els rebuigs que persisteixen però es poden
desfer, l'aprenentatge que suma però no habilita, els llindars que es veuen i es corregeixen.
Cap peça pretén tenir l'última paraula.

---

## 3. LA PRIMERA BAULA — JA CONSTRUÏDA I A PROD

**`SewToleranceAcceptance`** (patterns, migració 0010, deploy #3 a PROD 2026-07-16).
Append-only, patró de `LegalAcceptance`. Cada esdeveniment CONGELA:

| Camp | Rol |
|---|---|
| `model` (FK, CASCADE) | **eix de lectura transversal de l'auditoria** |
| `sew_relation` (FK, SET_NULL) + `sew_relation_snapshot` (int) | pont a la fila viva + id que sobreviu si s'esborra |
| `accio` (accepta/desaccepta) | l'estat viu = últim esdeveniment per data |
| `tipus_relacio` · `mena_tolerancia` · `desajust_cm` · `grau` · `llindar_verd_mm` · `llindar_groc_mm` | snapshot congelat: QUÈ es va acceptar i contra QUIN llindar |
| `decidit_per` (FK) · `data` · `nota` | qui · quan · per què |

Guards a save + delete + queryset (cap update/delete). **Filtrar per `model` = tot l'historial
d'un model** → l'auditoria el llegirà transversalment. Dissenyat per llegir-se transversalment
després, NO com un flag efímer d'UI.

**Els llindars actuals** (tolerance.py, criteri d'ofici afinable per la Montse — deploy #3):

| Mena de relació | 🟢 verd ≤ | 🟡 groc ≤ | 🔴 vermell > |
|---|---|---|---|
| Costura de muntatge | 3 mm | 6 mm | 6 mm |
| Casat | 2 mm | 4 mm | 4 mm |
| Pinça | 1,5 mm | 3 mm | 3 mm |
| Frunzit | — sense gradient (el diferencial és intencional) — | | |

Tipus desconegut → cau a muntatge (el més tolerant). La xifra MAI es tenyeix; el color va a la
vora i la icona. La pinça 69-71 (3,1 mm) surt en **vermell**, com toca.

---

## 4. ELS SENSORS QUE JA EXISTEIXEN (l'auditoria els agrega)

L'auditoria NO reinventa la detecció. Cada mòdul ja sap detectar el seu tipus de desajust:

- **Detector d'estalitud del grading** (G6-B2) — segell fresc/estàle/desconegut, amb els canvis
  datats. "No saber i dir que va bé són coses diferents."
- **Casat que no casa** (W1/S6) — costura amb desviament per longitud.
- **Pinça que no tanca plana** (A1/W4b) — costats desiguals, avís en groc/vermell.
- **Cobertura de vora** (W4) — solapaments/excessos canten.
- **Segell que diu la veritat** (G6-B) — el gate d'exportació confia en un flag que ja no ment.
- **Tolerància gradual + acceptació** (QA-TALLER-H) — el semàfor + el rastre d'acceptació.
- **Grading que no preserva longituds en escalar** (S7) — la validació que cap CAD fa.

**La part nova = la vista transversal + el veredicte global per model.**

---

## 5. UBICACIÓ I ACCÉS

**On viu:** és el mòdul que es va **amagar dels tabs de model** (referència: `ESTAT_BACKOFFICE`
/ la fitxa d'empresa). Opera sobre el schema/context adequat.

**Connexió amb el deploy #3:** el paquet legal/comercial F1-F4 (pricing, tenants Free, docs
legals) JA és a PROD al schema públic, però encara **no té porta d'entrada** —
`fhorttextile.tech` resol com a tenant. El **`backoffice.fhorttextile.tech`** (a l'horitzó) és
el que donarà accés a la capa de control. L'auditoria de model probablement viu en aquest
territori de control (PM/gestió), no al Taller (tècnic).

---

## 6. NATURALESA TÈCNICA

- **Gran part PARAMÈTRICA i DETERMINISTA** — les toleràncies, els desajustos geomètrics, el
  casat que no casa, la pinça que no tanca plana, el grading estàle. Tot això són números i
  regles, no judici.
- **+ recolzament d'IA on toqui** — no per decidir, sinó per interpretar o prioritzar quan el
  determinisme no arriba.

---

## 7. QUÈ CAL DECIDIR ABANS DE CONSTRUIR (sessió pròpia amb Montse)

1. **El veredicte global:** com es combina el conjunt de senyals en una resposta única al PM?
   (semàfor per model? checklist? score?) — sense caure en un número dogmàtic (llei 2.4).
2. **Els llindars per tipus** — la Montse els valida/afina sobre patrons reals (els actuals són
   criteri de partida).
3. **La franja "el motor diu no-casa però cau dins la banda verda"** (QA-TALLER-H) — és el punt
   on la Montse decideix si els llindars són bons.
4. **Fins on arriba l'auditoria de grading** (G6-C: R4 aplana-a-FIXED, R6 close_base).
5. **La porta de la rectificació** (§2.2) — si algun dia s'obre "proposar modificar", com es fa
   respectant la sobirania del dibuix (via PAT-3).

---

## 8. FILS RELACIONATS (al PLA_IMPLEMENTACIO_MOTOR_PATRONS.md)

- **T2-composts** (QA-TALLER-B) EN PAUSA i REORIENTAT: com que 69-71 és defecte (no pinça
  vàlida), "salvar la pinça" amb un compost té menys sentit per aquest cas — no vols salvar un
  defecte, vols reportar-lo. Repensar si T2 segueix sent el que crèiem o va cap a auditoria.
- **QA-TALLER-D** (prioritat alta): família "el motor mesura la vora amb orígens diferents"
  (operations.py:717, _longitud_indexs, segmentar_vora) — soroll que l'auditoria hauria de no
  reportar com a fals positiu.
- **PAT-3** (rectificació post-fitting) del backlog del motor — la porta de §2.2.
- **PREGUNTES MONTSE pendents:** tolerància de costura (0,1 cm correcta?), TATE_SLEEVE 0,2 cm,
  receptes de mesura (15/25 per omplir), rol canònic, G6-C.

---

*Document creat 2026-07-16 en tancar la sessió llarga del Taller (deploys #2 i #3). La primera
baula (`SewToleranceAcceptance`) ja és a PROD. La resta espera sessió pròpia de disseny amb la
Montse abans de qualsevol brief.*
