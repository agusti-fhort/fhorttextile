# REPORT · U1 · U2 — Catàleg de POMs i Catàleg de peces

> **Data:** 2026-08-07 · **Branca:** `dev` (staging) · **Cap push.**
> **Maquetes (l'especificació):** `ops/maquetes/maqueta_cataleg_poms_v1.html` ·
> `maqueta_cataleg_peces_v4.html`
> **Commits:** `1adc4380` (U2 · models) · `ef10ce46` (U1/U2 · API) · `457c627c` (U1 · pantalla)

---

## 0 · ESTAT, SENSE MAQUILLAR

| Peça | Estat |
|---|---|
| **U2 · el model de dades de l'acumulació** | ✅ **fet** — 2 taules + migració + servei d'unió + 19 tests escrits |
| **U1/U2 · l'API** | ✅ **fet** — 2 ViewSets, `poms/<id>/us/`, `.../acumulacio/`, porta d'escriptura de grups |
| **U1 · Catàleg de POMs (pantalla)** | ✅ **fet** — llista + fitxa + accions + 45 claus i18n ×3 |
| **U2 · Catàleg de peces (pantalla)** | 🛑 **NO fet** — v. §5 |
| Suite de tests | 🛑 **NO corregut** — v. §4 |
| `migrate_schemas` + auditoria | 🛑 **NO fet** — depèn dels tests |

**Les dues aturades que el brief preveia s'han disparat totes dues**, i les dues decisions
són d'Agus (preses el 07/08, §1). El que hi havia darrere no era feina de pantalla: era el
model de dades.

---

## 1 · LES DUES ATURADES, I QUÈ HI HA DECIDIT

### 🛑 U2 · La LLEI DE L'ACUMULACIÓ no cabia al model

`GarmentPOMMap` penja **només** de `garment_type_item` (`pom/models.py:816`). Cap taula
mapejava POMs a una **família** ni a un **grup**; ho vaig confirmar censant les 11 FK cap a
`POMMaster`. Dimensionat: **1.748 files vives**, `unique_together('garment_type_item','pom',
'capa','instancia')` i **103 referències** en 8 fitxers.

**Decisió (Agus): dues taules germanes**, no una amb FKs nullables. Els seus motius, que són
els que el codi documenta:

1. A Postgres **els NULL no comparen iguals** → un `unique_together` sobre FK nullable deixaria
   de protegir exactament els dos nivells nous. *«Un constraint que existeix i no protegeix és
   pitjor que cap — avui mateix n'hem enterrat un»* (el `clean()` de `SizingProfile`).
2. El **«Ve de»** ha de dir de quin nivell arriba cada POM. Amb tres taules la resposta és la
   taula; amb FKs nullables es respondria **per absència**, que és fràgil.
3. Risc zero per a les 1.748 files i els 103 lectors.

### 🛑 U1 · «Instàncies admeses» i «Capes on té sentit» no tenen dada

**Cap FK ni M2M de tot el codi apunta a `MeasurementLayer` ni a `MeasurementInstance`**: són
catàlegs de vocabulari (6 capes · 10 instàncies en 2 eixos) que les taules de mesura
referencien per slug. No existeix enlloc «quines capes admet aquest POM».

**Decisió (Agus): pintar l'ÚS OBSERVAT, ben etiquetat.** *«Declarar-ho ara obligaria a omplir
274 POMGlobal a mà o a deixar-los buits dient "cap" — i "cap" seria FALS, que és pitjor que no
dir-ho.»* La secció diu literalment que és ús observat, i amb llista buida diu **«encara no
s'ha fet servir enlloc»**, no «no admet cap capa».

> 📌 **Dimensionat de la declaració, per al tram futur** (Agus el va demanar anotat): dues M2M
> a `POMGlobal` (`capes_admeses` → `MeasurementLayer`, `instancies_admeses` →
> `MeasurementInstance`), migració additiva, UI d'edició a la fitxa, i **la sembra dels 274
> `POMGlobal`**, que és el gruix real i és feina de la Montse amb el catàleg v4 a la mà. Quan
> hi sigui, aquesta vista d'ús observat es queda com a **contrast declarat vs observat**.

---

## 2 · U2 · EL QUE S'HA CONSTRUÏT AL MODEL

`GarmentTypePOMMap` (família) i `GarmentGroupPOMMap` (grup), germanes de `GarmentPOMMap` i amb
**la mateixa clau** `(àncora, pom, capa, instancia)` — perquè la capa i la instància són
**identitat**: el mateix POM a l'exterior i al folre són dues pertinences.

Comparteixen `_POMMapBase`, **abstracta a posta**: no crea taula i no toca la germana viva. Les
seves FK van cap a `GarmentType`/`GarmentGroup`, que són de **la mateixa app**, o sigui que
porten constraint de BD real — a diferència de la de l'item, que creua cap a `tasks`
(tenant-only) amb `db_constraint=False`.

**La jerarquia NO viu a la BD**: viu a `pom/acumulacio.py` com una **unió a la lectura**. Guanya
el nivell **més específic** (item > família > grup) i els altres queden a `tambe_a`, perquè la
pantalla pugui dir «això ve de l'item, però el grup ja ho demanava». **Cap fila existent es
migra.**

---

## 3 · U1 · LA PANTALLA, I LA REGLA D'ESBORRAT

Mitja i mitja: llista agrupada per categoria + fitxa. Substitueix les dues pestanyes de POM
Systems; **`POMBrowser` no s'esborra ni es toca** (el consumeixen 5 pantalles més).

Les seccions amb dada sencera surten de `POMGlobal` amb el fallback a `POMMaster`: Identitat i
«Com es mesura» (des d'on · fins on · referència · scope · orientació · estat · línia · zona del
cos). Àlies de client en lectura.

### 🔴 `GET poms/<id>/us/` — la lliçó de TGIRL, en codi

El recompte recorre **`POMMaster._meta.related_objects` (16 relacions)** i **mai**
`information_schema`: les FK amb `db_constraint=False` —que aquesta casa fa servir a tot arreu
per creuar shared↔tenant— **no existeixen per a Postgres**. Un cens contra la BD va donar
`TGIRL-EU-HEIGHT` per «risc zero» i era l'àncora de 350 regles.

**I una segona lliçó, d'avui: no totes les relacions bloquegen igual.**

| | Efecte | Avui |
|---|---|---|
| **PROTECT** amb files | esborrar és impossible → **això és ús** | 14 relacions |
| **CASCADE** amb files | esborrar és possible, **però se les endú** | `CustomerPOMAlias` · `POMEstadisticaTenant` |

Un botó que esborra 3 àlies de client sense avisar és el mateix silenci de sempre. El peu de la
fitxa **diu sempre el motiu**, i el motiu el redacta el backend, que és qui sap el recompte.

> ⚠️ **`POMMaster` NO té cap camp `is_system`.** «DE SISTEMA» es deriva de `pom_global is not
> None` (ve del catàleg global de la casa); els que no en tenen han nascut al tenant i són els
> únics esborrables. **És una derivació, no una dada declarada** — si el criteri ha de ser un
> altre, és una línia.

---

## 4 · 🛑 EL QUE NO S'HA VERIFICAT, I PER QUÈ

**La suite no s'ha corregut.** El brief mana «UNA correguda de tests alhora: coordina't amb la
sessió de CAT», i aquella sessió porta **43+ minuts** amb `manage.py test fhort.pom
fhort.models_app`. Els 19 tests estan **escrits** (`test_u2_acumulacio.py`) i no s'han executat
ni una vegada.

Per tant **tampoc s'ha aplicat `migrate_schemas`** (la migració `0073` només existeix al disc) ni
s'ha auditat a `information_schema` als tres schemes, ni s'ha reiniciat el backend. Els commits
van entrar amb el verd que el `CLAUDE.md` demana per commitar —`manage.py check` net i
`npm run build` net—, però **la porta dels tests queda oberta**.

👉 **El que falta, en ordre:** `test fhort.pom.test_u2_acumulacio` → suite de `pom` →
`migrate_schemas` (sense `--schema`) → auditoria a `information_schema` als 3 schemes →
`restart` → rutes vives.

> 🔵 **Un parany de mètode, i és meu.** El vigilant que vaig posar per esperar el torn
> (`until ! pgrep -f "manage.py test"`) **es bloqueja a si mateix**: el seu propi `bash -c` conté
> la cadena que busca. És exactament el bug que aquest matí vaig diagnosticar a l'altra sessió, i
> hi he caigut igual. El predicat bo ancora al procés de Python: `^[^ ]*python.* manage\.py test`.

---

## 5 · 🛑 U2 · LA PANTALLA NO S'HA CONSTRUÏT

**Per què m'aturo aquí i no la faig a mitges.** U2 no és una pantalla nova: és el **redisseny de
dues pantalles vives**, i totes dues són grans:

| Existeix avui | Què és | U2 hi vol |
|---|---|---|
| `pages/GarmentTypes.jsx` · **448 línies** · ruta `garment-types` | El catàleg de peces actual: mestre-detall amb graella de *cards* d'item + secció Fitxers | Cascada de **3 columnes** (grup › família › item) + items en **línies** amb 6 columnes |
| `pages/ItemAuthoring.jsx` · **429 línies** · ruta `garment-type-items/:itemId/editar` | L'autoria d'item: talla base + `MeasurementBaseGrid` | **Dos tabs** (Talles i POMs · Fitxers) amb el run i la talla base fixats a dalt |

Fer-ho bé vol dir tocar 877 línies de pantalles que la casa fa servir cada dia. Començar-ho ara,
amb el torn de tests bloquejat i sense poder verificar res, seria el contrari del que aquest
sprint ha après.

### El mapa de reutilització, ja establert (perquè el tram següent no el torni a fer)

- **`CascadeFinder`** (`components/CascadeSelector/CascadeFinder.jsx:43`) — contracte
  `{value, onChange, onPickItem, target, compat, query, renderHeader, renderItemMeta, height}`.
  Avui només el consumeix `ModelWizard`: **U2 seria el 2n consumidor, que és el que tanca el
  veto dels dos sistemes.**
- **`MeasurementBaseGrid`** (`{garmentTypeItemId, baseSetId, readOnly, onSaved}`) — la taula de
  Definició de POMs. Ja la consumeixen `ItemAuthoring` i `BaseSetPanel`: el tab «Talles i POMs»
  l'ha de **reutilitzar**, no copiar.
- **`FileList`** (`components/assets/FileList.jsx:19`, `{files, selectedId, onSelect, onOpen,
  emptyLabel}`) + `itemFitxers` (endpoints.js:210) — el tab «Fitxers» ja té les dues meitats.
- **`Chip`** (`components/grading/wizardUI.jsx:25`) per a tota píndola seleccionable.
- L'endpoint d'acumulació (`garmentTypeItems.acumulacio`) ja retorna el recompte per nivell que
  pinta la barra i el «Ve de» de cada fila: **la columna més caraacterística de la maqueta ja té
  el seu backend fet.**

---

## 6 · SORPRESES

1. 🔴 **La maqueta demanava una cosa que el model no podia sostenir, i no era un detall.** Les
   dues aturades del brief no eren defensives: totes dues eren reals, i la de U2 era un canvi de
   model amb 1.748 files i 103 lectors al davant.

2. 🟡 **`GarmentGroupViewSet` era `ReadOnlyModelViewSet`**: el «＋ Nou grup» de la maqueta no
   tenia porta. S'ha obert CREATE+UPDATE gated CONFIGURE, i **NO DELETE a posta** —
   `GarmentType.grup_ref` hi apunta amb `PROTECT` (C6 pas 1) i el string `grup` encara hi conviu,
   o sigui que esborrar deixaria el string orfe i petaria amb un 500 en comptes d'un missatge.
   Quan C6 faci el pas 2, obrir-lo serà una línia.

3. 🟡 **Me n'havia inventat tres tokens CSS** (`--bg-subtle`, `--border-soft`, `--text-faint`) i
   **dos noms d'endpoint** (`customerPomAliases`, `pomCategories`). Els vaig comprovar un a un
   contra `index.css` i `endpoints.js` abans de construir: cap va arribar al commit. És el mateix
   pecat que el vet d'aquest matí, en direcció contrària — inventar-se el vocabulari en comptes
   de buscar-lo.

4. 🟡 **La casa té tres formes de «tag» i cap contracte compartit**: `Chip` (botó seleccionable),
   `ReadChip` (caixa etiqueta/valor) i el `tagBase` **privat** de `RunRestrictionTags`. Per a una
   llista de tags de només lectura no n'hi ha cap, i el `tagBase` cau dins la frontera dura
   d'aquest sprint. He fet **marcatge local de pàgina**, no un component compartit nou (que
   hauria demanat aturar-se). 🚩 **Un `Tag` compartit és la convergència òbvia de les tres.**

5. 🔵 **`GarmentPOMMapSerializer` no s'ha convergit** amb el `_POMDisplayMixin` nou. Seria obvi i
   és una millora clara, però toca un serializer viu amb 103 lectors i aquest sprint no ho
   demanava. **ANOTAT com a deute**, no fet.

---

## 7 · EL QUE QUEDA

| # | Què | On |
|---|---|---|
| 🛑 1 | **Córrer la suite** (19 tests nous inclosos), després `migrate_schemas` + auditoria als 3 schemes + restart | §4 |
| 🛑 2 | **U2 · la pantalla**, amb el mapa de reutilització ja fet | §5 |
| 🚩 3 | Sembrar POMs a nivell de grup i família: les taules existeixen i **estan buides**. Sense dades, la barra d'acumulació dirà «grup 0 · fam 0» — correcte, però la llei no es veurà fins que algú hi declari alguna cosa | §2 |
| 🚩 4 | El criteri de **«POM de sistema»** és una derivació (`pom_global is not None`), no una dada | §3 |
| 🚩 5 | Un `Tag` compartit · convergir `GarmentPOMMapSerializer` | §6.4 · §6.5 |
| 📌 6 | El tram de la **declaració** de capes/instàncies, quan la Montse tingui el catàleg v4 | §1 |
