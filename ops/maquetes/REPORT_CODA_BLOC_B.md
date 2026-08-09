# CODA DEL BLOC B — quatre retocs vistos a pantalla real

> 09/08/2026 · commits **192 → 196** (cap push) · build **desplegat** · `npx eslint src` **0
> errors** · `node --test` **218 · 0 fallides** · bidireccional **0 desviacions** · auditoria de
> computats **0 incompliments**.

---

## Els quatre retocs

### 4 · El fons de pàgina passa a `--bg-page` — commit **192**, aïllat
El `<main>` de la Shell pintava `--gray-l` (#f0f0f0): un **gris fred**, i a més un àlies legacy
que la casa fa servir per a **vores i farciments de control**, no per a la superfície on viuen
totes les pantalles. `--bg-page` (#fbfaf8, blanc càlid) existia des de T0.1 i aquest era l'últim
lloc que no el consumia — mentre el `<main>` pintés gris, **cap pantalla conforme podia acabar de
casar amb la seva maqueta**, que va tota sobre `--bg`.

Va en commit aïllat perquè **toca totes les pantalles alhora**, també les que encara no han
passat conformitat: si alguna se'n ressent, es reverteix una línia.

### 1 · La lletra de la talla base, centrada — commit **193**
El carril és una columna d'amplada fixa amb un camp més estret a dins. Amb `text-align: right` a
la capçalera i a la cel·la, l'etiqueta, la lletra i el camp quedaven **tots enganxats al filet
dret** i el buit se n'anava sencer a l'esquerra. Ara la columna centra el que porta —**la lletra
a la capçalera i el camp a la cel·la**— i el **número de dins del camp segueix a la dreta i
tabular**, que és el que s'ha de poder escombrar amunt i avall.

De passada, el carril pren els tokens que la seva pròpia maqueta li dona (`th.baseh`): `--sel`
amb marc `--gold-border`. Anava amb **`--gold-pale`, que la §1 ha ELIMINAT del sistema**.

🚩 **La maqueta v9 alineava el carril a la DRETA.** L'ordre és posterior i mana (jerarquia §8b);
**la maqueta queda esmenada a la font** amb acta al costat, perquè el pròxim tram no la torni a
dibuixar arrambada.

### 2 · «Gravar POM» és l'acció primària — commit **194**
És el que has vingut a fer a Definició de POMs, i per tant va en **blau** (§5.1). Anava en
**daurat ple**, que és la llei *anterior* a la §5: el daurat feia dues feines alhora —marcar la
casa i cridar l'acció— i **quan un color diu dues coses no en diu cap**.

### 3 · La jerarquia de la pantalla d'edició — commit **194**
Tenia **tres botons plens i cap blau**: daurat («Gravar i tornar»), blanc («Descartar canvis») i
**vermell PLE** («Descartar sessió»), que la §5.5 prohibeix fora d'una confirmació — **cridava
més que el que de debò havies de prémer**. Ara:

| Botó | Forma |
|---|---|
| «Gravar i tornar» · «Gravar size check» | **PRIMÀRIA blava** — una per pantalla i estat |
| «Mesurar prenda» · «Graduació» · «Propagar» · «Importar taula» · «Tornar a consulta» | **PORTES** (blanc + vora de la casa) |
| «Descartar canvis» · «Cancel·lar» | **TERCIÀRIA** |
| «Descartar sessió» | **DESTRUCTIVA amb VORA**; el vermell ple **només** al botó que confirma dins del modal |

**Per què s'ha tocat `ui/buttons`:** cada superfície s'havia inventat la seva família —`btn('gold')`
a `CheckMeasureEditor`, un altre `btn('gold')` a `SessionActions`, `btnPrimary`/`btnSecondary` a
`EditableTable`— i **les tres deien que la primària era daurada**. Tres còpies de la mateixa
decisió és com aquesta pantalla va acabar sense cap blau. La família sencera de la §5 (primària ·
secundària · porta · terciària · destructiva · destructiva plena · deshabilitat) viu ara al mòdul
compartit, amb el motiu de cada forma escrit al costat. **`primaryBtn` (28 consumidors) no es toca.**

---

## Captures (`ops/qa/captures/`)

| Fitxer | Què s'hi veu |
|---|---|
| `coda_01_fons_pagina` | retoc **4** — el blanc càlid sota la llista de models |
| `coda_02_definicio_pom` | retocs **1 + 2 + 3** — «TALLA BASE / L» centrada sobre el carril, els camps centrats a la columna, **«Gravar POM» blau**, i «Graduació» i «Importar taula» com a portes |

🛑 **El que NO s'ha pogut fotografiar**: la barra de **sessió de fitting** («Gravar i tornar» ·
«Descartar canvis» · «Descartar sessió») i els seus dos modals. Segueix sense haver-hi **cap
sessió de fitting a cap dels dos tenants** — el mateix límit que el report del bloc. El canvi hi
és al codi i el lint i el build el cobreixen; **la foto no.**

---

## ⚠️ EFECTE SECUNDARI DE LA MEVA PRÒPIA QA SOBRE EL BANC — i què he fet

Per fotografiar la pantalla de Definició de POMs vaig obrir-la per la seva adreça
(`?tab=Mesures&mode=entry`). **Aquella adreça no és una vista: és una porta de treball**, i el
circuit de tasca va fer la seva feina. Conseqüència al model **1319 (`FTT-SS26-0001`)**:

| Què | Estat |
|---|---|
| Tasca **358 · Definició POM** | creada · **1 minut consumit** · ara **Paused** (el rellotge, aturat per mi) |
| Tasca **359 · Mesurar prenda** | creada · 0 minuts · Paused |
| `fase_actual` | **`Pending` → `Dev`** (conseqüència d'obrir la tasca) |
| Talla base · peça · joc | **intactes** (`L` · ítem 19 · sense joc) — la prova funcional d'A7 va restaurar la seva |

**El que he fet:** aturar el rellotge de seguida que l'he vist córrer. **El que NO he fet:**
tornar la fase a `Pending` ni esborrar les dues tasques. Escriure-ho a mà deixaria un estat
**incoherent** —una fase de model que diu una cosa i dues tasques que en diuen una altra— i, pitjor,
taparia el que ha passat. **Ho decideixes tu**: si vols el banc com estava, són dos gestos, i te'ls
faig; si el vols així, ja hi és. El minut consumit és meu i és a la comptabilitat.

**La lliçó, per al pròxim que capturi**: a la fitxa del model, `?mode=entry`, `?task_id=` i
`?fitting_session=` **són gestos, no vistes** (el codi ja ho diu: `PARAMS_DE_TREBALL`). Un arnès
de captures que hi entri **escriu al domini**.

---

## Verificació

| Control | Resultat |
|---|---|
| `npx eslint src` | ✅ **0 errors** |
| `npm run build` + desplegat a `frontend/dist` | ✅ |
| `node --test "src/**/*.test.js"` | ✅ **218 · 0 fallides** |
| `ops/qa/qa_bidireccional.py` (re-executada sencera) | ✅ **49 casos mesurats · 0 desviacions** — v. la nota |
| `ops/qa/qa_auditoria_computats.py` (6 pantalles) | ✅ **0 incompliments** |

**Backend no tocat** → cap suite nova: l'última correguda de tancament segueix valent
(913 tests · OK).

> ⚠️ **I la re-execució va ensenyar una cosa que val la pena**: dos casos van passar de mesurats
> a **NO MESURATS**, i no per cap canvi de pell — anaven ancorats al literal **«Pendent»**, i la
> fase del banc s'havia mogut (v. l'efecte secundari de sobre). **Un selector que depèn d'un
> ESTAT DE DOMINI deixa de mesurar sense avisar, i el silenci s'assembla massa a un verd.** Els
> dos casos s'ancoren ara a **qualsevol** de les sis fases del vocabulari (A5) i al `title` del
> badge (A6), que no es mouen amb la dada. **Verificat**: els dos tornen a mesurar-se i casen —
> 49 casos mesurats, 0 desviacions. L'únic `⚠️` que queda és el de sempre (la capa de restricció
> d'A2, estat no assolible amb les dades vives; el bloc A ja el va anotar).


---

# APÈNDIX · TANCAMENT DEL TRAM 0

## Restauració del banc (model 1319 · `FTT-SS26-0001`) — **feta a mitges, i pel circuit**

| Gest | Circuit | Resultat |
|---|---|---|
| **Fase → `Pending`** | `POST /models/1319/regress/` (l'endpoint de retrocés: només toca `fase_actual` i deixa un `GateEvent kind=regress` amb la nota del motiu) | ✅ **`Dev` → `Pending`** |
| **Retirar les tasques 358 i 359** | `DELETE /model-task-items/{id}/` | 🛑 **EL SISTEMA HI DIU QUE NO**, i ho diu bé |

El `DELETE` respon **409** amb aquest text, que és una regla de domini i no una avaria:

> «Només es poden esborrar tasques pendents (`Pending`). Una tasca iniciada, pausada o feta
> **conserva la seva història** i no s'esborra.»

I la màquina d'estats tampoc no ofereix cap sortida neta: des de `Paused` l'única transició legal
és `InProgress`, i d'allà `Done`. **Marcar-les `Done` diria que «Definició POM» i «Mesurar prenda»
estan FETES al banc** — una mentida al llibre, i pitjor que deixar-les pausades. Amb «no SQL a mà»
com a condició, **el circuit s'ha acabat aquí**.

**Estat final verificat:**

```
fase: Pending  ·  estat: Nou
base: L  ·  run: XS·S·M·L·XL·XXL·3XL  ·  sistema: 30
peça: 19  ·  joc: cap
tasques: 358 pom Paused (1 min) · 359 size_check Paused (0 min)  →  CAP RELLOTGE CORRENT
```

**La causa, per a tota QA futura:** l'adreça `?tab=Mesures&mode=entry` **no és una vista, és un
gest**. El codi ja ho declara (`PARAMS_DE_TREBALL = ['mode', 'task_id', 'fitting_session']`): els
tres «diuen *entra a treballar*, no *mira aquesta pantalla*». **Un arnès de captures que hi entri
escriu al domini.** Si cal fotografiar aquelles superfícies, s'ha de sembrar un model de sacrifici,
no fer-ho sobre el banc.

## «＋ Afegir POM» — 🛑 **ATURADA, per la porta que el mateix brief deixa oberta**

El brief demanava «la via mínima que el motor admeti… si triar-ne una és decisió d'abast, ATURA i
descriu-les». **N'hi ha tres, i triar canvia l'abast.** La diagnosi sencera —amb els cinc fets que
manen i el preu de cada via— és a **`docs/diagnosis/DIAGNOSI_AFEGIR_POM.md`**. El resum:

El motiu que el bloc A va escriure al botó **era mitja veritat**. Hi ha **dues** parets, no una:
`rule_set` és `read_only` (una línia) **i `talla_base` és una FK NOT NULL** — que és la de debò,
perquè demana **una dada que ningú té i que el motor no llegeix mai** (`grading_utils.py:72`:
«mer metadata del seed»). I **46 dels 47 jocs de `fhort` no tenen cap regla**, o sigui que no hi ha
ni una regla germana d'on copiar-la.

| Via | Backend | Obre el botó a | Preu |
|---|---|---|---|
| **A** · exigir `talla_base` al client | 1 línia, cap migració | 40 de 47 jocs | pregunta a la pantalla **una talla base que la maqueta v4 no té i el motor ignora** |
| **B** · derivar-la al backend | 1 línia, cap migració | 40 de 47 | **no hi ha res d'on derivar-la** en un joc buit |
| **C** · FK **nullable** (CAT2.1 pas (b), versió mínima) | **migració d'una columna** + guard de `None` | **47 de 47** | hi ha migració, i el brief deia que no n'hauria de caldre |

I una quarta, que no és tècnica: **amb 46 jocs buits, potser el botó no ha d'obrir-se ara** sinó
amb la sembra del corpus.

**El que sí que es pot fer avui sense decidir res**: corregir el motiu escrit al botó, que avui
amaga la paret que de debò mana. Un gest, si el vols.
