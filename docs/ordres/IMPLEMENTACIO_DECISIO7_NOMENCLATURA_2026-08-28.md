# ACTA — DECISIÓ 7 · LA NOMENCLATURA ÉS SOBIRANIA DEL MODEL

**Data:** 2026-08-28 · **Patró:** B · **Branca:** `decisio7-nomenclatura` (worktree `/var/www/ftt-d7`)
**Base:** dev @ `cc933a06` · **Commits:** 3 + aquesta acta · **Cap push.**
**Substrat:** [`DIAGNOSI_NOMENCLATURA_MODEL_2026-08-28.md`](DIAGNOSI_NOMENCLATURA_MODEL_2026-08-28.md)

## PAS -1 · Entorn

| | |
|---|---|
| `hostname` | **fhort-assessment** ✅ |
| `WorkingDirectory` | **/var/www/ftt-staging/backend** ✅ |
| HEAD de `dev` | **cc933a06** (28/08 06:52) |
| Worktree | **`/var/www/ftt-d7`**, branca `decisio7-nomenclatura`, des d'aquell HEAD |
| `ps` | un `manage.py runserver :8099 --noreload` de 23 dies. No és fil de motor i, amb `--noreload`, no llegeix res del que aquí es toca |
| Intersecció amb l'arbre brut | **cap**. Els 4 modificats de `dev` (`DECISIONS.md`, `IMPLEMENTACIO_SOBIRANIA_POM_2026-08-22.md`, `ops/maquetes/REPORT_CODA_BLOC_B.md`, `ops/qa/qa_f22_vocabulari_captures.py`) no són cap dels 11 fitxers d'aquest sprint |

🚩 **Una correcció al substrat.** La diagnosi citava `models.py:220` per a l'`unique_together`;
és **`models_app/models.py:903`**. El 220 era un desplaçament RELATIU dins del bloc `Meta` que
vaig extreure amb `awk`, escrit com si fos absolut. **El contingut és exactament el que deia** —
`('model','pom','capa','instancia','garment')`— o sigui que el substrat es manté i no hi ha
motiu d'aturada; però la citació era dolenta i queda corregida aquí. La resta de línies del
report s'han verificat una a una contra el HEAD i totes casen.

---

## EL TITULAR

La diagnosi ja deia que el camp existia. El que aquest sprint ha trobat en construir és que
**el llapis també obria ja les dues cel·les**: el comentari d'`EditableTable.jsx:1362` ho
declarava («l'ÚNICA porta a l'edició de la identitat. Obre el nom I la nomenclatura alhora») i
`editantIdentitat` ja governava els dos camps. **El que no era una era la porta d'ESCRIPTURA.**
Això és el que s'ha unificat, i el que faltava de debò —la unicitat i el rebateig de l'import—
s'ha construït.

---

## F1 · LA PORTA ÚNICA

| | |
|---|---|
| `nom_fitxa` entra al llapis | `models_app/views.py:4090` → `NOMS_POM_LIMITS` / `NOMS_POM_CAMPS` |
| …i surt del PATCH genèric | `models_app/serializers.py` → `update()` el descarta |
| Resposta | ara torna també `nom_fitxa` (`views.py:4151`) |

⚠️ **El límit va haver de passar a ser un diccionari.** `nom_fitxa` és `CharField(20)` i els dos
noms `CharField(160)`: amb el `NOMS_POM_MAX` únic, un codi de 30 caràcters hauria **passat la
validació** i hauria petat a la BD amb un 500 mut — que és exactament el que aquella constant
existeix per evitar.

🚨 **I la porta ampla és d'un sol sentit, no una paret.** El primer intent (`read_only_fields`
sencer) trencava el camí de **partir un POM**: la germana neix amb `instancia`, i la comporta
`instancia_exigeix_nom` (migració `0074:75`) exigeix que porti nomenclatura. Si el CREATE no la
pot escriure, la partició peta amb un `IntegrityError`. La llei bona és la mateixa que F3 aplica
a l'import — **al néixer s'escriu, un cop existeix no es toca** — i els dos costats tenen test.

## F2 · LA UNICITAT

`colisio_de_nomenclatura` i `frase_de_colisio_nomenclatura` viuen a **`pom/nomenclatura.py`**, al
costat de `colisio_de_codi`, i pel mateix argument que ja hi era escrit: *el refús ha de sonar
igual vingui d'on vingui*. La vista només crida i respon **409 · `NOMENCLATURA_DUPLICADA`** amb
el context (quina fila, quin POM).

**Per què al servei i no al serializer:** la porta d'F1 és una vista de funció, no un
`ModelSerializer` — no hi ha `validate()` on penjar-ho. I posar-ho al serializer genèric hauria
significat validar precisament a la porta que aquest sprint tanca.

**L'àmbit és `model + garment + capa`** i en deixa fora dos eixos de la clau de fila, cadascun per
un motiu diferent: `pom` perquè si hi entrés no es compararia res, i **`instancia` a posta** —
dues instàncies del mateix POM a la mateixa peça (la sisa dreta i l'esquerra) SÓN el cas que ha
de tenir codis diferents.

### 🚨 El cens decideix: CAP constraint de BD, encara

| schema | files | amb `nom_fitxa` | grups duplicats |
|---|---:|---:|---:|
| `fhort` | 561 | 493 | **4** |
| `los` | 0 | 0 | 0 |

| model | capa | codi | files |
|---|---|---|---|
| 1380 | exterior | **SR** | 3389 (`right-extended`) · 3390 (`right-relaxed`) |
| 1322 | exterior | **J1** | 2288 (`relaxed`) · 2289 (`extended`) |
| 1494 | exterior | **B** | 3386 (`relaxed`) · 3387 (`extended`) |
| 1320 | exterior | **J1** | 2230 (`relaxed`) · 2231 (`extended`) |

Les quatre són **el mateix POM en dues instàncies** compartint codi: anteriors a la llei i
exactament el que ve a evitar. Per instrucció del brief, **la constraint espera la neteja** i
queda escrit aquí.

⚠️ **I el cens ha canviat el disseny, no només l'ha informat.** La validació només mira si el
valor **CANVIA**: re-desar el codi que una fila ja tenia no és col·lisió amb ningú (mateix
argument que `excloent_pom_id` a `colisio_de_codi`). Sense això, obrir el llapis en una
d'aquestes quatre files per canviar-ne el **nom** hauria donat un 409 contra la seva pròpia
germana. Té test propi.

### El que la unicitat NO cobreix, i queda dit

`set_measurements_view` (`views.py:2354`) escriu `nom_fitxa` directament sobre el model, i el
payload de la graella el porta (`payloadMesures.js:32,63`). **Amb F4 aquest camí ja no pot
introduir codis nous** —la cel·la ja no toca el buffer local, i el desat massiu només reenvia el
que ja hi ha—, però segueix sent un escriptor sense comprovació. Els altres (federació,
abocament de plantilla) són sincronitzacions de sistema o només de creació. **La constraint,
quan les 4 parelles estiguin netes, és el que tanca això de debò.**

## F3 · L'IMPORT DEIXA DE REBATEJAR

`extraction_views.py:3385` → `nom_fitxa` surt dels `defaults` i passa a **`create_defaults`**
(Django 6.0.5). Sense cap flag: la clau ja distingia els dos casos.

⚠️ Ha de quedar **als dos diccionaris**: quan es dona `create_defaults`, la creació deixa de
mirar `defaults`, i una fila nova amb instància naixeria sense nomenclatura contra la comporta.

## F4 · EL LLAPIS

El desviament es fa a **`handleCellChange`**, en un sol lloc i no un per mode. El refús es desa
per `bmId` i es pinta **sota la cel·la** (`role="alert"`), amb el valor escrit encara al camp.
Repuntats també els tres escriptors que quedaven a la porta ampla (`onNomSave` × 2 i
`onIdentitat`, que ara reparteix). i18n `editable_table.nomenclatura_duplicada` amb paritat
ca/en/es.

---

## 🚨 F5 · LA FITXA — S'ATURA, I AQUÍ HI HA EL PERQUÈ

El brief autoritzava el fix només si era petit i local, i manava **aturar-se si el text viu dins
del document serialitzat**. Viu. Cens exacte:

### (b) Les etiquetes: DUES respostes diferents dins de la mateixa fitxa

| on | d'on surt el codi | es resol… | després d'un rebateig |
|---|---|---|---|
| **Taules de mesures** de la fitxa | `codiPomQ8` → `nomenclaturaDePom(residentQ8(fila))` (`TechSheetEditor.jsx:5292-5293`) | **EN VIU**, contra el `BaseMeasurement` resident, per identitat sencera | ✅ **codi NOU** |
| **Cotes/fletxes al canvas i al PDF** | un objecte de TEXT del document | **NO es resol**: el text és dada desada | ❌ **codi VELL** |

La serialització és `serializePages` (`TechSheetEditor.jsx:2189`): desa `pages[].objects[]` tal
qual al `.ftt`. Una cota és un objecte de text i **el seu `text` porta la cadena**.

### (a) El lligam fletxa↔fila

`TechSheetEditor.jsx:6045-6047` ho declara sense embuts: *«Sense cap referència desada (G1),
l'única prova possible és la que veu l'ull: hi ha un text amb aquell `nom_fitxa`»*. **No hi ha
`bm_id` ni identitat desada.** Rebatejar trenca la coincidència: el POM passa a llegir-se com a
**no col·locat** i la fletxa vella queda **òrfena** al document.

### Conseqüència, dita en clar

Un model rebatejat i amb fitxa ja desada ensenyaria **dos codis diferents per a la mateixa
mesura dins del mateix full**: el nou a la taula, el vell a la fletxa. I les fitxes **ja desades**
porten el text vell a dins.

**No s'ha tocat res.** El fix no és local —vol una referència desada a l'objecte i una resolució
al render, o sigui tocar la serialització de la fitxa i el que ja hi ha desat— i la regla vigent
diu que al `TechSheetEditor` no es toca la serialització sense mesurar. **Decisió d'Agus.**

⚠️ **I per això no hi ha les captures de canvas i PDF que el gate demanava.** Demanava els tres
—taula · canvas · PDF— «mostrant el bateig nou», i el cens diu que **dos dels tres no el poden
mostrar** amb el codi d'avui. Fabricar-les hauria estat documentar una cosa que no passa.

---

## GATE

| control | resultat |
|---|---|
| `manage.py check` | ✅ net |
| `npm run build` | ✅ `✓ built in 1.11s` |
| `npx eslint` (3 fitxers) | ✅ **0 errors**; avisos **iguals que a dev** (10/10 a `EditableTable`, mesurat contra `/var/www/ftt-staging/frontend`) |
| Tests dirigits nous | ✅ **13/13** (`test_d7_nomenclatura.py`) |
| **Vermells contra el codi vell** | ✅ **10 de 13**, en worktree separat a `cc933a06` amb el fitxer de tests copiat a sobre. Els 3 que hi passen són **controls**: l'import verge, el `create` de la partició i re-desar el mateix codi — descriuen el que NO ha de canviar |
| Fum de pantalla | ⚠️ **parcial, i mesurat** — v. sota |
| Suite sencera | ❌ **no s'ha corregut**, per instrucció |
| `dist` d'staging | ✅ intacte (26/08): el build s'ha fet al worktree, no s'ha desplegat res |

### El fum: què prova i què no

**Prova** (4 ✓, captures a `ops/qa/captures/d7_*.png`): la graella pinta un llapis per fila i
**obre les DUES cel·les alhora** — nomenclatura i nom—, cap error de JS.

**No prova:** que el missatge de refús es PINTI. El gest de commit no es pot conduir des del
headless: al primer clic dins de l'input, l'editor d'identitat es tanca i cap crida arriba a la
porta. 🔑 **No és regressió d'aquest sprint**: el mateix guió contra el bundle del **26/08**
—anterior a qualsevol canvi— es comporta exactament igual (`QA_DIST=…/ftt-staging/frontend/dist`,
que per això és un paràmetre del guió). El 409 i el seu text els cobreixen els tests de backend;
**que es pinti queda sense verificar i no es dona per bo.**

🔑 El fum va néixer mentint i es va veure: amb només `taula-mesures` stubejat donava capçalera i
cap fila. És la llei d'F4-quater —**la consulta es dibuixa amb `base-stages`**— i ara les dues
porten les mateixes files.

---

## QUEDA OBERT

| | |
|---|---|
| 🚩 **Netejar les 4 parelles** i llavors posar la constraint de BD | Dades + una migració. |
| 🚩 **F5: la fitxa** | Decisió d'Agus: referència desada + resolució al render, o conviure-hi. |
| 🚩 **`set_measurements_view`** | Escriptor sense comprovació; la constraint el tanca. |
| 🚩 **Que el refús es pinti** | Sense fum. Verificació manual d'un minut a la pantalla. |
| 🔵 **Fora d'abast, com deia el brief** | corroboració del matching · catàleg del tenant · promocions. |
