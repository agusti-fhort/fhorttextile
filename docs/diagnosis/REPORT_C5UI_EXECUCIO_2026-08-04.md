# C5-UI · EXECUCIÓ DE LA LLISTA D'UI PURA — informe

> Nit del **04→05/08/2026**. Base `33451704` → **8 commits locals, CAP PUSH**. Branca `dev`.
> Font de veritat: la llista d'UI PURA de `CENS_UI_PENDENT.md` (blocs A1–A5 i A8) i els dos fixos
> que surten de `DIAGNOSI_CICLE_TASCA_COMPLET.md`.
>
> Un commit per peça · verificació estreta **i pantalla real** · regressió única al final.

---

## 1 · Els vuit commits

| Commit | Peça | Abast |
|---|---|---|
| `fad10351` | **F1a** · el 409 de reobertura diu la paret | 6 fitxers · +50/−6 |
| `55978598` | **F1b** · l'override de QA del guard es consumeix | 1 fitxer · +43/−7 |
| `491993cd` | **F1c** · P11 — el calaix és el pas de Graduació | 4 fitxers · +87/−22 |
| `70405f7b` | **F2** · A1+A2 — les 4 taules de la fitxa | 2 fitxers · +79/−38 |
| `6cdea6a2` | **F2b** · el sufix d'identitat, fixat per test | 1 fitxer · +70 |
| `db3da038` | **F3** · A3 — el panell de cotes per germana | 1 fitxer · +164/−84 |
| `00fbca15` | **F4** · el gest de crear una germana | 1 fitxer · +184/−3 |
| `207ec5d4` | **F5** · les pastilles de convocatòria | 1 fitxer · +18/−3 |

Van **intercalats** amb els de la sessió paral·lela (`9a0e3f43`, `796137c3` D-31.4; `89009858` M6).
HEAD en tancar: `6cdea6a2`. Arbre net a `backend/` i `frontend/src`.

---

## 2 · Peça per peça

### F1a · el 409 de reobertura diu la paret: «tasca albaranada»

El model 188 va acumular **set 409 en dues hores** (16:21→18:28) sobre la mateixa porta, i les set
vegades el tècnic va llegir «No s'ha pogut obrir la tasca». La paret és real i és una regla de
negoci —les tasques 256 i 272 tenen línia a l'albarà 5, EMÈS—, però arribava muda i el gest es
repetia perquè res no deia que fos inútil.

`TransitionError` guanya un `code` opcional; el guard d'albarà l'omple (`tasca_albaranada`) i les
dues portes HTTP el reenvien quan n'hi ha. **Sense codi, la resposta és byte a byte la d'abans**:
cap consumidor existent canvia. Al front, `motiuOpenTask()` tria la frase pel codi i cau al
missatge genèric per a qualsevol codi que encara no conegui — mai a una clau i18n inventada.

- `backend/fhort/tasks/services_c.py:199` · `backend/fhort/tasks/views_b.py:572`
- `frontend/src/pages/ModelSheet.jsx` (`MOTIUS_OPEN_TASK` / `motiuOpenTask`)

> **Pantalla real.** «Editar POM» a ROSALIA → *«Cannot open: this task is already on an issued
> delivery note. To correct it, add a new extra.»*

**No canvia QUI pot reobrir** — això és la decisió D-5 i és de l'Agus. Només fa que la porta
tapiada digui per què ho està.

### F1b · l'override de QA del guard es consumeix en llegir-lo

`ftt_guard_llindar_min` vivia a `localStorage`, i `localStorage` **no és «per sessió»: sobreviu a
tancar el navegador**. Un `1` posat en un QA el 27/07 seguia encès el 04/08, fent saltar el modal
cada minut a qui obrís aquell perfil. El símptoma no assenyala mai la causa.

Dues coses, i **la primera és la que tanca el forat**:

- la clau **es consumeix**: es llegeix i s'esborra → un override val per a UNA càrrega de pàgina.
  Un QA ja no pot deixar res encès en plegar. *(El rang sol no ho hauria aturat: un `1` hi cap.)*
- el valor s'ACOTA a `[0.25, valor de producció]`: escurçar és el QA legítim, allargar no.

Valors de producció amb nom: `LLINDAR_PROD_MIN` 30 · `GRACIA_PROD_MIN` 3.

### F1c · P11 — el calaix de Graduació és el pas de Graduació, no el wizard sencer

Obria `ModelWizard` al pas 4: quatre passos navegables, capçalera de wizard i botons de desar el
MODEL, per a un gest que és **triar un joc de regles**. `GraduacioPanel` ja estava extret
exactament per a això (`6af2f6f2`, i la seva pròpia capçalera ho deia); faltava que aquest costat
el cridés.

Eixos del model, verificats contra el 188: `garment_type_grup='TOPS'` (hi és sempre, a diferència
del FK `garment_group`, buit als importats) · `size_system=29` · fit `REGULAR` (de
`grading_fit_nom`, que és el `nom_en` del fit i els codis de `FITS` en són la majúscula exacta).

**L'escriptura no es toca**: segueix sent `onUsarJoc` → `update-step2`. L'atzucac de «falta la
construcció» tenia com a sortida travessar tres passos; ara el panell diu quin eix falta (ja ho
feia) i la capçalera hi posa la porta: **«Editar el model»**.

### F2 (+F2b) · les quatre taules de la fitxa diuen QUINA mesura és cada fila

**A1 i A2 eren les MATEIXES quatre expressions: un sol canvi, no dos.** Cada taula portava la seva
cadena en línia i totes quatre tenien els mateixos dos forats:

- **el bateig no arribava al paper.** `nomsDePom()` es va escriure el 31/07 com a resolutor únic i
  **no el consumia ningú** — la regla d'or es trencava justament al document que va al fabricant.
- **la germana no es distingia.** Els payloads porten `capa`/`instancia` des de C4, però la cel·la
  només imprimia el nom. En una graella ho salva la columna de capa; en un imprès no hi ha res més.

Punt únic `nomDeTaula()` + `sufixIdentitat()` (a `capaInstancia.js`, on viu el vocabulari):
instància i **després** capa —la instància qualifica la mesura, la capa diu de quina matèria
parla—, i **l'exterior no s'escriu mai**.

> **Pantalla real, taula inserida a la fitxa de ROSALIA:**
> ```
> A      Chest width              37.0
> A-FOL  Chest width · Lining     35.5
> AH-L   Armhole depth · Left     23.2
> AH-R   Armhole depth · R…       23.0
> ```

**R2 de propina**, perquè eren les mateixes línies: les quatre nomenclatures passen per
`nomenclaturaDePom()`. La T1a en surt **sense la crida a `grading-rules/`**: l'única cosa que en
llegia era `rule.pom_nom_en`, i el nom ara el resol `nomsDePom` —que a més sap del bateig—.

**`F2b`** fixa les dues promeses per `node --test`. La segona és la que protegeix les ~600 files
que no són germanes: *la mesura única d'exterior no porta sufix*. Sense aquesta, «arreglar» les
germanes hauria estampat «· Exterior» a tota la fitxa.

### F3 · A3 — el panell de cotes deixa de clavar-se al `pom_id`

Amb la decisió **D-31.25** presa, es desbloqueja. Tot el panell indexava per `pomId`:

- posar la cota d'`A` deixava `A-FOL` amb el ✓ verd i **sense casella** → el folre no s'acotava mai;
- el comptador comptava doble (`.map(bm => bm.pom_id)` sense deduplicar);
- l'automàtic escrivia al croquis una cota que deia **«273»**.

`bmUnicPerPom` era un **guard conscient**, no un descuit: com que `bmId` es desa al `.ftt`,
resoldre `pom_id → mesura` amb germanes hauria lligat la cota a la que sortís l'última de la
consulta i **persistit** l'error. Va preferir no respondre. Amb la decisió presa, la clau és la
identitat sencera i el mapa passa a ser total.

> **Pantalla real.** Col·locar la cota d'`A` la marca ✓ i **`A-FOL` es queda pendent**. Esborrar-la
> torna les dues a pendent.

⚠️ **Cap `.ftt` es migra.** `identitatDeCota` llegeix un `pomId` pelat com a `(pom, exterior, '')`
—que és el que era quan es va escriure— i el format nou desa els eixos **només quan no són el
defecte**. Una cota d'exterior únic es desa byte a byte com abans; els dos formats conviuen.

### F4 · el gest de crear una germana

Tot C4 era a sota des de feia dies —l'escriptura porta els dos eixos, la poda també, la clau única
de la BD ja és `(model, pom, capa, instancia)`— i **no hi havia cap porta d'usuari**: les germanes
de staging es van sembrar per script. **No ha calgut tocar backend.**

Acció **per fila**, no un menú global: una germana no és «una mesura nova», és una cara MÉS
d'aquesta mesura. Neix **al costat de la mare** i **buida** — heretar el valor de l'exterior posaria
a la taula una xifra que ningú no ha mesurat i indistingible d'una de presa.

🔑 **La invariant mana el disseny del diàleg:**
`models_app_basemeasurement_instancia_exigeix_nom` = `CHECK NOT (instancia > '' AND nom_fitxa = '')`.

| Mena | Nom | Per què |
|---|---|---|
| de **capa** | opcional | la capa ja distingeix la fila |
| d'**instància** | **OBLIGATORI** | sense ell, desar peta amb IntegrityError → 500 mut |

Les cares que el POM ja té no s'ofereixen: la clau és única i tornar-ne a triar una existent
escriuria damunt d'una fila viva.

> **Pantalla real (model 162).** Germana de Folre d'`E1 · Hip Position`, nomenclatura `E1-FOL`,
> valor 58,5, desar i **recarregar de zero** → la fila hi és, amb la seva capa i el seu valor
> (`BaseMeasurement 2104`, `capa='folre'`).

### F5 · la pastilla de convocatòria diu de quin model és, i hi porta

Totes deien `Fitting · 5 models · Proto` i totes enllaçaven a `/fittings`. Mesurat al calendari
real: el 13/07 hi ha **quatre pastilles idèntiques** de deu minuts consecutius, cap amb el codi del
model. És el primer que la Montse hi veurà.

Cada marcador **ÉS** una sessió (això ja ho va deixar així el fix de G7), o sigui que pot dir el seu
model i portar-hi: `{codi} · fitting {fase}` amb `· +N` quan ve d'una convocatòria. La convocatòria
passa a ser **context**, no identitat; `meta` segueix portant UUID, `n_models` i `model_ids`.

Verificat sobre `79e06e8a…`: FTT-FW27-0001 · BRW-FW26-0006 · BRW-FW26-0008 · BRW-FW26-0007 ·
BRW-SS26-0001, cadascuna al seu dia i a la seva hora.

---

## 3 · Verificació

**Harness nou** — `scratchpad/qa_server.py`: serveix el `frontend/dist` **REAL** i passa `/api/` per
`django.test.Client` amb `force_login` dins `schema_context('fhort')`. **Mata del tot el problema
dels JWT encunyats des del shell**: sense `page.route`, sense stubs, sense auth bàsica. Playwright
hi apunta i prou. Les escriptures van a la BD de staging de debò → s'ha de netejar després.

| Control | Resultat |
|---|---|
| `fhort.tasks` + `fhort.planning` + `fhort.fitting` | **182 tests · OK** (780 s) |
| `npm run build` | net a cada commit **i a HEAD** |
| `node --test` (8 fitxers) | **62 tests · 0 fails** |
| `manage.py check` | net |

⚠️ **Parany d'infra reconfirmat:** `pgrep -f "manage.py test"` **s'auto-detecta** — els meus propis
bucles d'espera casaven el patró i el comptador no baixava mai a zero. Esperar pel **PID real del
`venv/bin/python`**, no pel patró.

---

## 4 · Higiene de dades — tot restaurat

- **Model 162**: germana `E1-FOL` esborrada · tasca 149 tornada a `Paused` · 16 mesures, capes
  `[(exterior,'')]`. Com abans.
- **Fitxa de ROSALIA**: cota i taula inserides i **tretes**. Head v26 amb **0 objectes**. El churn
  de versions és el conegut (`ftt-ftt-version-churn`).

---

## 5 · Dues coses de procés

**① Les claus i18n de F4 són al commit `796137c3` de l'altra sessió.** El seu `git add` dels tres
`i18n/*.json` va escombrar les meves 14 claus `germana.*` × 3 idiomes mentre esperaven al working
tree. **Funcionalment no passa res** (són a HEAD i el diàleg les resol), però l'atribució queda
creuada: el commit de D-31.4 porta els literals de F4, i F4 no porta els seus. **No s'ha tocat**:
reescriure un commit d'una sessió viva amb dos commits a sobre és pitjor que la molèstia.

**② F1a es va haver de refer.** El primer commit s'havia empassat els canvis de P11 (123 línies en
comptes de 23). Reset i recommit amb l'abast correcte abans de continuar.

---

## 6 · El que queda a mig fer, amb el punt exacte

| Què | On | Per què |
|---|---|---|
| **F4 no verificat a ROSALIA** | tasca `pom` 256 = Done + albaranada | La porta de Definició POM està **tapiada** pel guard que F1a acaba d'explicar. Verificat al 162: mateix codi, mateix endpoint |
| **La IA no proposa dues cotes del mateix POM** | `proposar-cotes/` parla per `pom_id` | Sostre de **backend**. La proposta va a la 1a mesura pendent; la germana queda a mà o per l'automàtic. Anotat al codi |
| **El sufix pot desbordar la cel·la** | taula T1a/base, columna de 46 mm | «Armhole depth · Right» surt com a «· R…». No bloqueja, però es veu |

---

## 7 · F6 · P8 — diagnosi, sense tocar res

**On parteix, exactament:** `CheckMeasureEditor.jsx:285` →
`const lockRegle = ctx.readOnly || ctx.lockRules`, i `lockRules` només és cert amb sessió de
fitting (`ModelSheet.jsx:660`).

**Conseqüència:** entrar a Mesures amb `?task_id=` (tasca `size_check`, «mesurar la peça») dona
**Δ i Break EDITABLES**, i `RegleEditCell` escriu `models.setPomRule` → **patrimoni del MODEL des de
la pantalla de PRESA**.

**El radi és més gran del que sembla:** *quatre* superfícies escriuen la regla per **un sol
endpoint** (`POST models/<id>/pom/<pom>/regim/`):

| Superfície | Client |
|---|---|
| `FittingDetail.jsx:620` | `setPomRegim` |
| `PropagatedEditor.jsx:148` (Escalat) | `setPomRegim` |
| `CheckMeasureEditor.jsx:144` (presa) | `setPomRule` |
| `EditableTable.jsx:160` (definició) | `setPomRegla` |

**Proposta:** que la condició miri el **codi de la tasca**, no només si hi ha sessió — `pom` edita
la regla, `size_check` no. És una línia, però decideix on viu el patrimoni de graduació i per això
**no s'ha tocada**.

---

## 8 · A la taula de l'Agus

- **D-5** — Es pot reobrir una tasca albaranada? Mentre no es decideixi, **ROSALIA no pot definir
  POMs** (i tots els models albaranats, igual).
- **P8** — Δ/Break editables des de la pantalla de presa: sí o no.
- **El contracte de la IA de cotes** — que parli per mesura en comptes de per POM (backend).

---

## 9 · Del cens, què queda per fer

Aquesta nit tanca **A1, A2, A3, A4, A5-parcial i A8** de la llista de `CENS_UI_PENDENT.md`.
Segueixen obertes, per ordre del cens:

- **A5** · el tint de fila no-exterior (token `--lining` + `esGermanaDeCapa()`, que segueix sense
  consumidors) — **XS**
- **A6** · el Taller de Patró pinta capa i instància (el backend ja les serveix) — **S**
- **A7** · reconnectar `FittingTab` com a llista de sessions del model (ja escrita, òrfena) — **XS**
- **A9** · peu de cel·la al règim: «aquesta regla la comparteixen les N germanes» — **XS**
- **A10** · un gest explícit d'«Obrir sessió» (`fittingSessions.open()` no el crida ningú) — **S**
- **A11** · `/tasques/kanban`, ruta inexistent a `ModelFabric.jsx:120` — **XS**
- **A12** · `lloc` i `model_persona` al formulari de programar — **S**
- **A13** · treure `inRange` dels all-day perquè G7 no pugui renéixer — **XS**
- **C1** · 🔴 la pantalla de **Comprovació** (D-31.17): maqueta aprovada, **zero línies** — tram propi
