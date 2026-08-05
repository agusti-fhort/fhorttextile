# REPORT · Les cinc maquetes com a especificació

> **Data:** 2026-08-05 · staging `dev` · **cap push** · **cap suite** · `git add` selectiu.
> Base: [`DIAGNOSI_UI_MAQUETES.md`](DIAGNOSI_UI_MAQUETES.md) (cens del matí) i
> [`REPORT_UI_MAQUETES.md`](REPORT_UI_MAQUETES.md) (primera tongada).

## 1 · Els commits

| # | Commit | Què tanca |
|---|---|---|
| A | `f0c852fa` | Els TRES comentaris rancis, esmenats |
| B0 | `ec0e9730` | `GET /api/v1/mesures/diccionari/` — el vocabulari d'identitat, publicat |
| B1 | `91841246` | Píndoles d'instància per dimensió (M1) |
| B2 | `3af98656` | Modal `＋` de posició i combinacions (M2) |
| B3 | `4e621f06` | Cercador: sufixos · nivells · ↓ des de l'última fila (M5·M5b·M5c) |
| B4 | `3096dfcf` | Tecla `L` i fons de les files de capa (M3b·M3c) |
| B5 | `af3e7400` | Barra d'estat fixa al peu (M7) |
| C1 | `617db73f` | **El veredicte del fitting deixa de perdre's** (D6) |
| C2 | `1a5e2c10` | Barra de recomptes + marca de germana derivada (F9 · F7 parcial) |

## 2 · A · El diccionari, llegit a BD

**El cens del matí es va equivocar, i el brief tenia raó.** El diccionari existeix des de
`b631b12d` (F2 · D-31.26) i està sembrat als **tres schemes** (`public`, `fhort`, `los`), 10
files, `is_system=True`:

| Eix | Slugs | Sufix |
|---|---|---|
| **POSICIÓ** | left · right · top · bottom · cf · cb · side | `L` · `R` · `T` · `B` · `CF` · `CB` · `S` |
| **POSICIÓ** | waistband_seam | *(cap — és un DATUM, es diu a la descripció)* |
| **ESTAT** | relaxed · extended | *(cap — usen el codi oficial del client)* |

### La diferència de format, que és el que calia escriure

**D-31.26 diu CONCATENAT sense guió** (`B`+`T` → `BT`, `FS`+`CF` → `FSCF`).
**Les dades vives de staging no ho compleixen.** L'única família d'instància que hi ha
—model 188, `fhort`— està desada així:

```
model=188  instancia='left'   capa='exterior'  nom_fitxa='AH-L'    ← amb GUIÓ
model=188  instancia='right'  capa='exterior'  nom_fitxa='AH-R'    ← amb GUIÓ
```

Segons el contracte haurien de ser `AHL` i `AHR`. **No s'ha migrat res**: `nom_fitxa` és text
lliure del patronista i reescriure-li la nomenclatura sense que ho demani seria pitjor que la
inconsistència. **Tot el que es crea a partir d'avui surt bé** (B1/B2/B3 componen amb la regla
del backend, i hi ha test que ho fixa: `assert.notEqual(codiProposat(D,'AH',['left']), 'AH-L')`).
**Decisió pendent:** migrar les dues files del 188, o deixar-les.

Altres troballes d'A:

- **`instancia` és un slug compost amb guió** (`left-relaxed`) i els dos eixos són ORTOGONALS.
  Coincideix amb el que el front ja desmuntava.
- **`capa` no entra mai al codi** (`regles.capa_al_codi: false`).
- **La constant local només tenia 4 dels 10 slugs** → `cf` es llegia «Cf». Corregit a B1.

## 3 · B · Mesures, v8.1 sencera

Els cinc blocs, fets. El que val la pena destacar:

- **B0 era invisible i bloquejava tot B.** Les dues taules estaven sembrades i **cap endpoint
  les publicava**. Sense el GET, B1/B2/B3 només es podien fer duplicant el vocabulari al front.
  L'endpoint emet també **la regla de composició com a DADA** (`sufix_separador`,
  `capa_al_codi`, `instancia_separador`), de manera que el dia que canviï no hi haurà dues
  respostes.
- **`dimState` es calcula per EIX, no per parella.** Una fila que ja sigui `top` té la POSICIÓ
  ocupada encara que ni «Esquerra» ni «Dreta» hi surtin enceses; la maqueta, amb només dues
  opcions per dimensió, no podia veure aquest cas.
- **La família és (POM + CAPA).** L'exterior i el folre del pit es parteixen per separat.
- **Partir hereta els valors; afegir una germana de capa no.** Són dos actes diferents i tenen
  dues respostes diferents (v. §6, on es diu que això contradiu un comentari viu).
- **`aplicaInstancia` és el motor comú** de les píndoles i del modal: dos camins voldrien dir
  dues identitats per a la mateixa germana, i la clau única de la BD no perdona això.

## 4 · C · Fitting

### C1 · El veredicte que es perdia — TANCAT

El defecte més seriós del cens. Verificat sobre la superfície VIVA
(`/models/<id>?tab=Mesures&fitting_session=<id>`) amb els PATCH capturats:

| | |
|---|---|
| En obrir | els veredictes desats **surten encesos** (abans: graella en blanc) |
| En decidir | **un** PATCH `{decisio: 'ADJUSTED'}`, la mateixa porta que la nota |
| Després de F5 | **els tres hi tornen a ser** |

Dos detalls que no eren obvis:

- **Se sembra també en CONSULTA.** Una sessió segellada s'ha de poder rellegir amb els colors
  amb què es va decidir; el `decisio` opt-in només afegeix les portes que escriuen.
- **El buffer es consulta amb `in`, no per veritat.** `null` hi és un valor legítim —«s'acaba de
  treure el veredicte»— i amb `||` la cel·la hauria tornat a pintar el valor desat: desmarcar no
  s'hauria pogut veure mai.
- **En fallar, el buffer es desfà i s'avisa.** Un veredicte que es pinta i no arriba és pitjor
  que un que no es pinta: la modista continua avall creient que ha decidit.

### C2 · Recomptes i germana derivada

Barra de recomptes feta (sobre les línies de la talla BASE, que són les úniques que es
decideixen). Marca `DERIVADA` feta, llegint l'`origen` que el backend ja emetia des de C4/F2 i
que el front ignorava.

## 5 · 🛑 D i E · PUNT DE PARADA

### D · Comprovació v2 — **no construïda**

La maqueta demana cinc seccions. Tres necessiten dades que **no existeixen**, i el brief mana
aturar-se i llistar-ho exactament en comptes d'inventar-ho o simular-ho.

| Secció de la v2 | Es pot fer avui? | Què falta |
|---|---|---|
| 1 · Bloquegen (fila sense valor a la base) | **SÍ** | `taula-mesures` ja serveix `base_value_cm` per fila |
| 1 · Bloquegen (POM sense regla de graduació) | **SÍ** | `taula-mesures` ja serveix `logica` per fila |
| 2 · Van quedar enrere quan la base es va moure | **PARCIAL** | `base_stages_view` emet `context` + `at`; **falta l'endpoint que compari la data de la darrera presa amb la del moviment de base i en tregui els dies** |
| 3 · Preses descartades pendents de reclamar | **NO** | `SizeCheckLine.decisio='valor_descartat'` existeix, però **no hi ha cap lectura agregada per MODEL** que en digui el valor que va arribar, el vigent i la SESSIÓ |
| 4 · Fora de tolerància al darrer fitting | **NO** | **`PieceFittingLine` no té `tol_minus`/`tol_plus`** (verificat: els camps són a `SizeCheckLine`, que és un altre flux). Sense tolerància al costat del fitting no es pot dir «fora de tolerància» |
| 5 · Famílies de mesura | **NO** | Falten DUES coses: (a) l'agregat per família (POM × capa × instància amb valor i **origen llegible**); (b) **el concepte de BUIT DECLARAT amb MOTIU** — les files `gap` de la maqueta («la germana es va proposar i es va treure: el coll passa sota l'aixella esquerra»). `desactivar_pom_view` no desa cap motiu i no hi ha cap model que el pugui guardar |

**El que falta, en una llista:**

1. `GET /api/v1/models/<id>/comprovacio/` — no existeix cap endpoint de preflight/checklist.
2. `PieceFittingLine.tol_minus` / `tol_plus` (o la font de tolerància del fitting) — camp nou.
3. Lectura agregada de preses descartades per model, amb la sessió d'origen.
4. Model per al **buit declarat amb motiu** d'una germana (avui la poda és `is_active=False` i
   prou) + la porta que l'escrigui.
5. L'agregat de famílies amb l'origen de cada cara en text llegible («Derivat de l'exterior ·
   18/07»), que avui només existeix com a slug (`origen`).

**Per què no s'ha fet a mitges:** el bloc de veredicte de dalt («La fitxa encara no pot sortir ·
2 bloquegen · 5 a revisar») és un RECOMPTE de totes les seccions. Amb tres seccions sense dades,
diria «la fitxa pot sortir» sense haver mirat la tolerància ni les preses descartades. Una
pantalla de comprovació que dona el vistiplau sense comprovar és pitjor que no tenir-la.

### E · Vista de família v1 — **no construïda, i cal decidir si existeix**

⚠️ **El propi `ops/maquetes/README.txt` la declara DESCARTADA:**

```
Descartada — NO la facis servir:
  maqueta_vista_familia_v1.html    · absorbida com a secció 5 de Comprovació
```

El brief la llista com a especificació. **Contradicció directa** entre el brief i el README de
la carpeta canònica. A més, el seu contingut **és** la secció 5 de Comprovació, que està
bloquejada pels punts 4 i 5 de la llista de dalt.

**No s'ha construït** per les dues raons alhora. Cal que l'Agus digui si la v1 de família
ressuscita com a pantalla pròpia o es queda absorbida.

## 6 · F · Wizard de model — censat, **no alineat**

⚠️ **El README diu que aquesta maqueta és «pendent de validació»**, no aprovada. El brief la
tracta com a criteri d'acceptació. Reestructurar un flux de creació que funciona contra una
maqueta que ningú ha validat és exactament el que la governança de la casa no permet, així que
s'ha fet el CENS i prou.

| Bloc de la maqueta | Estat a `ModelWizard.jsx` |
|---|---|
| 3 passos (Identificació · Peça · Talles) | **HI ÉS PARCIAL** — la viva en té **4 blocs**: el 4t hostatja `GraduacioPanel` (`491993cd`), que el brief prohibeix tocar |
| Filtres TARGET per descarte | **HI ÉS** (chips, desmarcables — el target és filtre opcional des de P6) |
| Filtres FIT | **HI ÉS** (chips `FITS`), però a la viva el FIT alimenta la GRADUACIÓ, no el filtre del catàleg |
| Filtre CONSTRUCTION | **A LA VIVA I NO A LA MAQUETA** |
| Cercador de peça per nom o codi | **HI ÉS** |
| Finder de 3 columnes (Grup · Família · Item) | **HI ÉS** — `CascadeSelector` |
| Pas 3 · sistemes de talles «per proximitat, cap amagat» | **HI ÉS PARCIAL** — es filtren per target i es descarten els que no tenen talles; **no hi ha ordenació per proximitat ni el filtre de text «escriu per filtrar»** |
| Pas 3 · talles del run | **HI ÉS** |
| Pas 3 · talla base amb ★ | **HI ÉS** |

**Divergència que val la pena decidir:** la maqueta fa del FIT un filtre del catàleg de peces; a
la viva el FIT és un eix de graduació. Són dues coses diferents amb el mateix nom.

## 7 · La maqueta de Mesures passa a v8.2

Fet, com demanava el brief: `ops/maquetes/maqueta_mesures_carril_v8_2.html`, amb el bloc
**REGLA DE GRADUACIÓ** (Règim · Δ · Δ break · Talla break) incorporat, les columnes buides (mai
pre-omplertes — lliçó del model 1302) i la nota que explica que la v8.1 no el portava perquè és
**anterior** a la decisió (`ff23c7f4`, W2/W3, 31/07, confirmada per l'Agus el 05/08).
`README.txt` actualitzat: la v8.2 és la vigent i la v8.1 queda com a històric.

**No entra en cap commit**: `ops/` és untracked per decisió pròpia del README.

## 8 · SORPRESES

1. **El cens del matí va declarar quatre divergències «estructurals» creient-se un comentari.**
   `capaInstancia.js` deia que el diccionari «encara no existeix (arriba amb C4-ins i la
   Montse)» quan feia hores que existia. Les quatre s'han fet avui en un dia. **La lliçó no és
   sobre el diccionari: és que un comentari ranci en zona sensible costa un tram sencer de
   feina mal planificada.** Tres n'hi havia; els tres ja estan esmenats (bloc A).
2. **Cap endpoint publicava les dues taules de vocabulari** tot i estar sembrades des de fa
   dies i tot i que `capaInstancia.js` ho tenia anotat com a TODO. Sense B0, B1/B2/B3 haurien
   acabat duplicant el vocabulari al front.
3. **`PieceFittingLine` no té tolerància.** El fitting mesura i decideix, però la banda de
   tolerància viu a `SizeCheckLine`. La secció 4 de Comprovació la dona per feta.
4. **Les úniques dades d'instància vives de staging incompleixen D-31.26** (`AH-L` en comptes
   de `AHL`). Dues files, model 188.
5. **`dictionary_views.py` ja existia** i és una altra cosa (la nomenclatura d'un CLIENT). El
   nom que hi anava a posar hauria trepitjat feina d'una sessió concurrent; l'endpoint nou viu
   a `identity_views.py`.
6. **Contradicció maqueta ↔ codi viu sobre l'herència de valors.** `EditableTable` té escrit
   que una germana que neixi amb el valor de la mare és «el pitjor defecte possible en una
   taula de mesures»; la v8.1 mana que **partir** hereti els valors. S'ha implementat la
   maqueta i el comentari s'ha mantingut per a l'altre gest (afegir germana de capa), que sí
   que neix buida. **Són dos actes diferents**, però convé que l'Agus ho confirmi.
7. **Dues de les cinc maquetes no són font vàlida**: la de família està DESCARTADA al README i
   la del wizard és «pendent de validació». El brief les tracta com a criteri d'acceptació.

## 9 · Què queda diferent de cada maqueta

| Maqueta | Què queda fora | Per què |
|---|---|---|
| **Mesures v8.2** | Res dels blocs demanats | — |
| **Fitting v3** | **La FOLGANÇA de la germana derivada** (`sis.folg`) | La maqueta la cabla a `2,0`; el domini **no té camp** on desar-la. Calcular-la com el diferencial viu seria decidir la D4 de l'Agus. La MARCA sí que hi és perquè no demana cap número |
| **Fitting v3** | El vocabulari de capes (Interlining/Binding/Knit/Reinforcement) | **Excepció declarada al brief**: mana D-31.22 |
| **Comprovació v2** | Tota la pantalla | §5 — 3 de 5 seccions sense dades |
| **Vista de família v1** | Tota la pantalla | §5 — descartada al README + bloquejada com la secció 5 |
| **Wizard v1** | L'alineació | §6 — maqueta no validada; cens fet |

## 10 · Verificació

- **`manage.py check`** net a cada commit de backend.
- **`npm run build`** net a cada commit de frontend.
- **`node --test`**: **140/140** (11 de nous, sobre la composició de codi i slug de D-31.26).
- **Checklist de pantalla als TRES idiomes** (`ca` · `en` · `es`), amb **consola a zero** a cada
  moment: càrrega · partir un POM · modal `＋` · cercador · tecla `L` · F5 · navegació entre
  superfícies · `prefers-reduced-motion`.
- **QA de la superfície viva del FITTING** als tres idiomes, amb els PATCH capturats.
- Passis a `scratchpad/qa_fase_b.py` i `scratchpad/qa_fitting.py`.
- Endpoint nou provat contra el tenant `fhort` amb `django.test.Client`.

## 11 · Què decideix l'Agus

1. **D · Comprovació**: aprovar els 5 punts de backend de §5, o retallar la pantalla a les dues
   seccions que sí que es poden fer avui (i llavors el bloc de veredicte no pot dir «pot sortir»).
2. **E · Vista de família**: ressuscita com a pantalla pròpia o es queda absorbida? El README diu
   descartada; el brief la demana.
3. **F · Wizard**: es valida la maqueta v1? I el FIT és filtre de catàleg (maqueta) o eix de
   graduació (viva)?
4. **D4 · La folgança** de la germana derivada: diferencial viu o valor declarat?
5. **Les dues files del model 188** amb `AH-L`/`AH-R`: es migren a `AHL`/`AHR` o es deixen?
6. **L'herència de valors en PARTIR** (§8.6): es confirma que partir hereta i afegir no?

---

**Cap push. Cap suite. `git add` selectiu a tots els commits.**
