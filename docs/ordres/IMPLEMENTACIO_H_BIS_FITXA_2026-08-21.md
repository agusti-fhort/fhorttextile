# H-bis · LES CINC TAULES DE LA FITXA: LAYER · POM · NOM, I EL CODI QUE ES VEU A MESURES

> **21/08/2026 · ✅ TRAM TANCAT AL CODI · 3 commits a `dev`, CAP PUSH.**
> 🚩 **QA de navegador PENDENT del JWT** (§6). Tot el que no demana navegador és verd.
> Substrat: ordre d'Agus sobre les captures reals del 1383 · acta d'H
> (`IMPLEMENTACIO_H_FITXA_2026-08-21.md`) · espec `docs/diagnosis/DIAGNOSI_Q8_TAULES_FITXA.md`.

---

## 0 · EL RESULTAT EN UNA LÍNIA

Les **cinc** taules de la fitxa (base · fitting · escalat · size set · notes) porten ara les
mateixes tres columnes d'identitat i en el mateix ordre —**LAYER · POM · NOM**—, i el codi i el
nom que s'hi imprimeixen són **els que el tècnic veu a Mesures**, no els que cada payload
arrossega pel seu compte. La columna de tolerància de la taula base, revocada.

---

## 1 · QUÈ MOSTRAVA CADA TAULA I QUÈ MOSTRA ARA

`‹talla›` = l'etiqueta real de la talla base (`S`), mai la paraula «Base». Les capçaleres van
sempre en anglès (`tEn`, `getFixedT('en')`) — llei Q8, sense excepcions noves.

| Taula | ABANS (fins al 21/08 al matí) | ARA |
|---|---|---|
| **Q8e · Mesures talla base** | LAYER · **POM = el NOM** · *(columna MUDA, sense capçalera, amb el codi)* · ‹talla› · **Tol ±** | LAYER · **POM = el CODI** · **NAME = el nom** · ‹talla› |
| **Q8a · Fitting** | LAYER · **POM = el NOM** · ‹talla› · REAL · DIFF · VERDICT · NOTES | LAYER · **POM** · **NAME** · ‹talla› · REAL · DIFF · VERDICT · NOTES |
| **Q8b · Escalat** | LAYER · **POM = el NOM** · RULE · Δ · BREAK · B. SIZE · ‹talles› | LAYER · **POM** · **NAME** · RULE · Δ · BREAK · B. SIZE · ‹talles› |
| **Q8c · Size set** | LAYER · **POM = el NOM** · ‹talla›×(teòrica · REAL) | LAYER · **POM** · **NAME** · ‹talla›×(teòrica · REAL) |
| **Q8c-bis · Notes** | LAYER · **POM = el NOM** · ‹talla› · NOTES | LAYER · **POM** · **NAME** · ‹talla› · NOTES |

**Quatre de les cinc no deien la nomenclatura enlloc.** Només la de base la portava, i la
portava malament col·locada: muda i al final. La instància (`left`/`right`/`relaxed`/`extended`)
segueix vivint **dins del nom**, que és la llei de Mesures des del 05/08 i no un detall
d'aquesta taula — v. §4, on és el que salva dues files del 1320.

### La capçalera que estrena la columna del nom

La decisió del 31/07 —*«la nomenclatura no s'etiqueta: el que hi ha sota s'explica sol»*— valia
per a una columna **muda i al FINAL** de la taula. Amb tres columnes d'identitat seguides, la
del mig sense capçalera no és sobrietat: és no dir quina és quina. Clau nova `q8_col_name`
(`Name`) als tres idiomes; `q8_col_tol` cau amb la columna.

---

## 2 · 🚨 LA TOLERÀNCIA, REVOCADA — I LA DADA SE'N VA AMB LA COLUMNA

El brief d'H l'autoritzava, H la va construir (`cellaTol`) i la QA visual d'Agus la treu. Amb
ella cauen `cellaTol`, la clau `q8_col_tol` i **els camps `tol_minus`/`tol_plus` de `filesBase`**.

Deixar-hi la dada hauria estat barat, i per això mateix és la temptació: un camp que ningú no
pinta és una **promesa que la taula el porta**, i la sessió que el trobi hi construirà a sobre.
La font segueix servint-la resolta (`_tol_vigent`, `pom/wizard_views.py:697-698`) i qui la
necessiti la té a un camp de distància — el que no ha de quedar és el rastre.

---

## 3 · 🚨 EL FORAT GRAN: TRES PAYLOADS, TRES BATEIGS PER A LA MATEIXA FILA

Les cinc taules beuen de **tres fonts** i cadascuna resolia el nom i el codi amb els camps que
la SEVA tenia a mà:

| Font | Qui hi beu | Porta el bateig del model? | Porta l'àlies del client? |
|---|---|---|---|
| `base-measurements/` (`pomRows`) | Q8e base | ✅ `nom_canonic_model`/`nom_traduit_model`/`nom_fitxa` | ✅ `client_alias` |
| `taula-mesures` | Q8b escalat | ✅ | ✅ (l'anomena `client_code`) |
| grid del `PieceFitting` | Q8a fitting · Q8c size set · Q8c-bis notes | ❌ **no els serveix** | ❌ **no el serveix** |

O sigui que **el bateig del model i la nomenclatura del client no arribaven mai a les tres
taules que surten d'un fitting**: hi sortia el nom i el codi del CATÀLEG DE LA CASA. La regla
d'or del 31/07 —*un canvi de nom al model es veu igual a Mesures, al croquis i a cada taula de
paper*— es trencava justament a la superfície que s'imprimeix.

### La reparació: mana el RESIDENT

`residentQ8` (`TechSheetEditor.jsx`) indexa `pomRows` per **identitat sencera**
(`pom · capa · instància · prenda`, `identitatMesura`) i les cinc taules hi resolen el codi
(`codiPomQ8` → `nomenclaturaDePom`) i el nom (`nomPomQ8` → `nomsDePom`). És la MATEIXA fila que
la pantalla de Mesures pinta, i per tant «cap segona font» és literal.

- Per `pom_id` pelat, no: dues germanes hi caurien a sobre i una s'imprimiria amb el nom de
  l'altra (el mode de fallada que C4 va matar a tot arreu).
- Sense resident —una fila d'un fitting antic que el model ja no té— es cau als camps de la
  fila. El pitjor cas és el bateig d'abans; **mai una columna muda**.
- `filesGrading` passa a més els camps CRUS (`client_alias` ← `client_code`, `codi_client` ←
  `pom_code`, `pom_abbreviation` ← `abbreviation`) perquè aquell fallback també encadeni bé.
  Comprovats **al payload d'aquell endpoint**, no copiats del constructor germà: és la lliçó
  d'H (`nom_client`), i aquí s'ha aplicat abans de trencar-hi res.

---

## 4 · LA PROVA, SOBRE DADES VIVES — I NO ÉS TEÒRICA

`ops/qa/hbis_columnes_fitxa.mjs` corre els **mòduls reals** sobre payloads reals de staging.

### 4.1 · 1320 · sis files de vint-i-vuit imprimien el codi de la CASA

El 1320 és **l'únic model del corpus amb àlies de client** (`CustomerPOMAlias`), i les seves
taules de fitting i de size set haurien imprès això:

| El tècnic veu a Mesures | La fitxa hauria imprès | Mesura |
|---|---|---|
| `FB2` | `F` | Centre front length from HPS |
| `FB1` | `FF` | Centre back length from HPS |
| `VL` | `VP` | Ruffle end placement |
| **`L`** | **`P`** | Centre back yoke height |
| **`L2`** | **`L`** | Back yoke width |
| `0` | `SLT` | Slit / opening length |

Les dues files en negreta són el cas dolent de debò: el full hauria dit **`P`** on el client diu
`L`, **i `L`** on el client diu `L2` — o sigui que hauria imprès un codi que al vocabulari del
client **vol dir una altra mesura**. No és un nom lleig: és una instrucció equivocada cap al
taller. Amb el resident, les sis surten com a Mesures.

### 4.2 · 1379 · tres files que es deien totes «Waist width»

`B` · `BB` · `B1`, el mateix nom de catàleg i tres xifres diferents. **Sense columna de
nomenclatura, la taula impresa deia tres vegades el mateix.** És l'argument de l'ordre 3
d'Agus, en dades.

### 4.3 · 1320 · dues files amb el MATEIX codi que només la instància separa

POM 981, capa `exterior`, codi de client `J1` a totes dues, `Sleeve opening` a totes dues —i
**7,0 cm** l'una i **18,0 cm** l'altra—: el que les distingeix és `relaxed` vs `extended`. La
porta d'unicitat del banc va sortir **VERMELLA** fins que el banc va pintar la instància com la
pinta l'editor. La prova tenia raó i el banc no mirava el mateix: és exactament el cas que
l'ordre 4 anomena *«amb les seves INSTÀNCIES, tal com viuen sembrades al model»*.

### 4.4 · Les portes que queden posades

Per taula i per model: **cap cel·la de POM muda, cap de NOM muda, cap parell (POM, NOM) repetit
dins d'una peça**, i el codi de l'escalat surt del resident. Verd a **1383 · 1379 · 1320 · 1354**.

---

## 5 · LA CONSEQÜÈNCIA DECLARADA: DOS FULLS QUE PASSEN A APAÏSAT

Una columna més són mil·límetres més, i dues taules creuen el llindar de l'A4 vertical (190 mm
útils). Amb el corpus del banc:

| Taula (run de 5 talles) | Abans | Ara | Full |
|---|---|---|---|
| Q8a fitting | 176 mm | **190 mm** | A4 vertical (just) |
| Q8b escalat | 184 mm | **198 mm** | A4 **apaïsat** |
| Q8c size set | 180 mm | **194 mm** | A4 **apaïsat** |

**No és una regressió silenciosa: és el fallback SANCIONAT de T3** —apaïsat abans que encongir,
i mai A3, que la fitxa s'imprimeix en A4—. El sòl de 8pt no es toca (les tres es queden a 9,0pt)
i el que no cabria ni en apaïsat segueix partint-se per TALLES.

Però T3 (18/08) havia guanyat el vertical per al run de cinc traient la Dif i el Verdict del
size set, i aquesta ordre se'l torna a menjar. **La prova que ho assegurava s'ha reescrit per
dir el que és cert des d'avui**, amb les dues xifres al costat: una prova verda que descriu unes
columnes que ja no existeixen és pitjor que no tenir-la.
🚩 **Si Agus vol recuperar el vertical, el mil·límetre és de la columna del NOM** (`maxMm` de
`ampladaPomQ8`), no de la del codi: escurçar el codi el fa inservible per al que serveix.

---

## 6 · 🚩 QA DE NAVEGADOR — PENDENT DEL TOKEN, I PER QUÈ

L'ordre demana captures de les taules i l'export PDF del 1383. **No s'han pogut fer**: el JWT de
QA el bloqueja el classificador de permisos (v. `ftt-qa-token-jwt-bloquejat`), i sense ell el
`goto` a staging captura el 401 d'nginx. L'script queda escrit i és **una sola ordre**:

```bash
FTT_QA_TOKEN=… /tmp/qa-venv/bin/python ops/qa/qa_hbis_taules.py
```

### El repartiment de casos el manen les DADES

🚨 **El 1383 no té cap sessió TANCADA** (159 Oberta · 158 Anul·lada), o sigui que allà **Fitting
i Notes no tenen font i el panell les ha de mostrar tancades amb el motiu** — que és el
comportament correcte i no una taula buida. Les «quatre taules» de l'ordre, al 1383, són tres.
Les altres dues es capturen on hi ha fitting tancat:

| Cas | `.ftt` | Taules | Per què aquest model |
|---|---|---|---|
| **1383** | 873 | Base · Escalat · Size set | el model de l'ordre |
| **1379** | 865 | les cinc | sessió 155 tancada · les tres «Waist width» |
| **1320** | 770 | les cinc | sessió 152 tancada · **l'únic amb àlies de client** (§4.1) |

El 1320 obre el **770** i no el 771: aquell és el fixture de regressió dels `kind` retirats que
H va deixar, i inserir-hi res el deixaria de ser.

### Què SÍ que s'ha verificat sense navegador

`npm run build` net (i **build = desplegar**: staging serveix `frontend/dist`) · `npx eslint`
**0 errors** · `node --test taulesQ8.test.js` **22/22** · `q8_taules_fitxa.mjs` **26/26** ·
`hbis_columnes_fitxa.mjs` verd als **quatre** models. L'export PDF, a més, **és el mateix
`renderPageToDataURL` que pinta el llenç**: «PDF == live» hi és per construcció, i el que la
captura ha de verificar és que no peti ni sobresurti.

---

## 7 · CENS — VIST I NO TOCAT

- 🚨 **CAP dels vuit `.ftt` del model 1383 (866-873) és al disc.** H ho va anotar del 873; és de
  **tots**: a `media/fhort/model_fitxers/2026/08/` només hi ha `TRV-SS27-0001_fitxa_v1.pdf`.
  L'editor els obre BUITS i l'autosave no hi persisteix. **Dany viu al model de banc.**
- 🚩 El `CustomerPOMAlias` del POM 1016 al client del 1320 és el codi **`'0'`** (zero). El
  resolutor l'imprimirà, i és correcte que ho faci —és el que el client diu—, però **té pinta
  d'error de dades d'import**, no de nomenclatura.
- 🚩 `POMMaster.pom_code` posa `codi_client` PER DAVANT del codi canònic i `nomenclaturaDePom`
  ho fa al revés. Amb el resident manant ja no afecta cap taula de la fitxa, però la divergència
  segueix viva per a qui llegeixi el payload cru (v. l'avís del capçal de `nomenclaturaPom.js`).
- 🚩 Segueix obert d'H: tota la família Q8 insereix a `Y_INICI = 14` (dues peces seguides
  s'apilen al mateix punt) i el banc `test_q8_banc_taules_fitxa.py` encara no s'ha pogut córrer.

---

## 8 · ELS COMMITS

| # | Commit | Què |
|---|---|---|
| 1 | `1bfd7850` | les cinc taules: ordre, columna de codi, resident, tolerància fora, i18n |
| 2 | `deb200fb` | `hbis_columnes_fitxa.mjs` (nou) + la geometria de Q8 reescrita |
| 3 | `d8f95de2` | `qa_hbis_taules.py` — les captures, a punt per al token |

**Cap push.** Els fa l'Agus des d'SSH.
