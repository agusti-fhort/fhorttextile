# REPORT P0 · matí del 06/08 — desbloquejar l'entrada del MILEY

> Staging `dev` · cap push, cap suite · **cada punt acabat ja és a staging** (`npm run build`
> desplega). FRONTERA respectada: `ModelWizard.jsx` i `CascadeFinder.jsx` NO s'han tocat.
> Model de proves: se'n crea un i s'esborra. **El MILEY (1308) no s'ha tocat mai.**

## Estat

| Punt | Què | Estat |
|---|---|---|
| **P0.2** | Les columnes d'instància no hi eren a Definició POM | ✅ **RESOLT** · `0d9e53de` |
| **P0.2b** | El desplegable del cercador sortia tallat | ✅ **RESOLT** · `c5868eb1` |
| **P0.1** | Valors: escriure → Gravar → llegir → F5 | ✅ **VERD al backend** · `e68bc9b9` · símptoma explicat |
| **P0.5-parcial** | Columnes de graduació sense ruleset triat | 🛑 **NO FET** — em falta saber quina pantalla és |
| P0.3 · P0.4 · P0.5 complet · P0.6 | — | ⏳ pendents |

---

## P0.2 · les columnes d'instància — RESOLT

> ⚠️ **RECTIFICAT per l'ADDENDA del final.** Aquesta secció deia que el backend estava bé. El
> CODI ho estava; el **procés desplegat, no** —servia una versió anterior a la ruta i responia
> 404. Ho vaig donar per bo perquè l'`APIClient` de DRF carrega el codi del disc, no el del
> gunicorn viu. La millora que hi ha aquí sota (avís + Reintenta) segueix sent bona i necessària,
> però **no era això el que bloquejava l'Agus**. Vegeu l'addenda.

El que vaig comprovar abans de tocar res: `GET /api/v1/mesures/diccionari/` tornava 200 **contra
el codi del disc** amb els dos eixos (POSICIÓ 8 · ESTAT 2), la ruta hi és, i el bundle desplegat
conté la crida.

Prova A/B al navegador sobre el bundle real (`ops/qa/qa_p02_definicio_pom.py`):

- **A · diccionari sa → les columnes SURTEN.** El codi era correcte.
- **B · diccionari caigut → desapareixen i la pantalla CALLA.** El símptoma de l'Agus.

La cadena era:

```
useDiccionariMesures  →  .catch(() => {})  →  dicc = null
dimensionsDe(null)    →  []
les columnes van darrere de  dims.length > 0
```

O sigui que **«encara no ha arribat» i «no arribarà mai» es deien igual** (`null` totes dues), i
des de la pantalla allò no es distingia d'un catàleg sense instàncies.

**Fet:** `useEstatDiccionari` separa les dues coses i torna `{dicc, error, reintenta}`. Quan hi
ha error, la taula pinta un avís que diu **què falta**, **què no es pot fer** (crear germanes) i
que la resta de la taula segueix funcionant — amb **REINTENTA**, perquè la fallada típica és
transitòria (la petició surt abans que la sessió estigui a punt) i recarregar la pàgina no pot
ser l'única sortida. La llei de sempre es manté: cap pantalla no espera el diccionari per pintar-se.

> ⚠️ **Per a l'Agus:** si torna a passar, ara ho veuràs escrit i podràs prémer Reintenta.
> Si l'avís surt sovint, el que hem de mirar és **per què la petició falla al teu navegador**
> (la sospita és la cursa amb el refresc de sessió) — això encara no està tancat.

## P0.2b · el cercador tallat — RESOLT

La llista anava `position:absolute` dins del cercador, i el cercador viu dins del
`<div style={{overflowX:'auto'}}>` que fa scrollar la taula. **Un avantpassat amb overflow ≠
`visible` retalla els fills posicionats encara que portin z-index alt**: és clipping, no
apilament, i per això pujar el z-index no ho hauria arreglat mai.

Ara la llista va al `body` amb un **portal** i es posiciona en coordenades de finestra. Decideix
cada cop cap on obrir-se: amunt si hi cap (el gest natural d'un cercador al peu de la taula) i
avall si no — arran del final de la finestra, obrir-se amunt la deixava mig fora. L'alçada es
retalla a l'espai real i la llista **scrolla dins seu**, així hi són tots els resultats.

Verificat (`ops/qa/qa_p02b_cercador.py`) a les tres situacions que el brief demana:

```
✓ taula CURTA                                   sencera dins del viewport
✓ taula LLARGA (el contenidor scrolla de debò)  sencera dins del viewport
✓ finestra BAIXA (cercador arran del final)     sencera dins del viewport
```

En les tres: penjada del `body` (cap avantpassat la pot retallar) i amb tots els resultats
abastables.

## P0.1 · els valors — el camí és NET; el símptoma té una altra explicació

`ops/qa/qa_p01_valors.py` segueix un valor per les vistes reals, sobre un model propi que es
crea i s'esborra:

```
· poms-suggerits=46 · taula-mesures=0 (verge)
· open-task pom → HTTP 200
✓ gravat · POM CH = 42.5
✓ BD · BaseMeasurement 2176 = 42.5 (capa='exterior' instancia='')
✓ lectura · taula-mesures torna 42.5 per al mateix POM
✓ F5 · el valor segueix: 42.5
✓ model de prova esborrat
```

**La sospita de «dues poblacions» al camí de LECTURA no es sosté:** Definició POM i la Consulta
llegeixen **el mateix endpoint** (`taula-mesures`; `MeasuresEntryPanel` i `ModelSheet:158/175`).

**El que sí que ha sortit, i explica el que vas veure.** A la primera passada el fum va petar amb:

```
gravar-pom → HTTP 400: "Cal obrir la tasca POM abans de gravar-la"
```

Si la tasca POM no està oberta, **Gravar no desa res**. I com que amb la taula verge Definició
pinta els 46 `poms-suggerits` (files `tmp-`, sense valor), **el que escrius viu només a l'estat
local del navegador**: la pantalla segueix ensenyant el teu número mentre la Consulta no té res.
Això és, exactament, «unes files i unes altres, tot —».

El missatge d'error **sí que es pinta** (`MeasuresEntryPanel:260`), o sigui que el cas és
reconeixible: si en prémer Gravar surt una línia vermella, el valor NO s'ha desat.

🚩 **El que queda per tancar de P0.1** (i que no he pogut fer): reproduir-ho **pel navegador amb
la teva sessió**. El gunicorn viu rebutja els tokens encunyats des del shell (401) i a staging no
s'hi creen usuaris de QA, així que el clic de Gravar per HTTP segueix sense verificar. Si et torna
a passar, **mira si surt la línia vermella**: si surt, és el gate de la tasca; si no surt, és una
altra cosa i llavors tenim un cas nou.

## 🛑 P0.5-parcial · NO l'he fet, i el motiu

La regla és clara («sense tria, les columnes NO hi són») però **no he pogut identificar quina
pantalla surt a la captura de les 08:54**. El que he mirat:

- la superfície de **consulta** (`checkSource.buildGroups`, `CheckMeasureEditor:213`) construeix
  **un sol grup**, el de la talla base — no hi ha columnes de graduació per talla;
- el bloc **«Regla de graduació»** de la taula de mesures ja es va retirar el 05/08 (ordre teva:
  «la columna de REGLA DE GRADUACIÓ sobra», v8.1).

O sigui que les columnes que vas veure surten d'una altra superfície — probablement **Escalat /
PropagatedEditor**. Tocar a cegues la visibilitat de columnes quinze minuts abans que arribi la
Montse era el risc que no calia córrer, i m'he aturat.

**Una línia teva i ho tanco:** de quina pantalla és la captura de les 08:54 (Mesures · Escalat ·
Comprovació · una altra)?

## Verificació · com tornar-ho a córrer

```
backend/venv/bin/python ../ops/qa/qa_p02_fixture.py      # dades reals (el JSON no va a git)
/tmp/qa-venv/bin/python  ops/qa/qa_p02_definicio_pom.py  # A/B del diccionari
/tmp/qa-venv/bin/python  ops/qa/qa_p02b_cercador.py      # el desplegable, 3 situacions
backend/venv/bin/python ../ops/qa/qa_p01_valors.py       # el camí d'un valor
```

Tots verds. `npm run build` net i `eslint` sense errors a cada commit.

## Commits (cap push — el fas tu des de SSH)

| Hash | Què |
|---|---|
| `0d9e53de` | 17 · P0.2 · el vocabulari que no arriba es DIU, i es pot reintentar |
| `c5868eb1` | 18 · P0.2b · el desplegable del cercador ja no surt tallat |
| `e68bc9b9` | 19 · P0.1 · el camí d'un valor, recorregut de punta a punta |

## Anotat pel camí (fora d'abast, no tocat)

- `MeasureGrid.jsx` i `ComprovacioPanel.jsx` també consumeixen el diccionari amb el hook antic:
  si els falla, callen igual que callava Definició POM. La regla nova només s'ha aplicat a la
  taula (`EditableTable`), que és on el brief l'ha demanada.
- La causa de fons de P0.2 —**per què** la petició del diccionari falla al navegador de l'Agus—
  segueix oberta. L'avís i el reintenta tapen el forat; no el tanquen.

---

# ADDENDA · el 404 del diccionari (09:28) — RESOLT

## No eren dues rutes. N'hi ha UNA.

El brief demanava trobar «les dues rutes» i unificar-les. **No existeixen.** El cens complet:

| On | Ruta |
|---|---|
| Backend | `backend/fhort/pom/urls.py:95` → `mesures/diccionari/` |
| Frontend | `frontend/src/api/endpoints.js:231` → `/api/v1/mesures/diccionari/` |

**Coincideixen exactament**, i és l'ÚNICA crida del frontend (els altres tres encerts del `grep`
són comentaris i un test). No hi havia res a unificar, i canviar la ruta del frontend hauria
trencat l'única crida correcta que hi havia. Per això no ho vaig fer i ho vaig preguntar abans.

## El que passava de debò: el codi del disc ≠ el codi que corria

```
gunicorn viu, arrencat        2026-08-05 10:17:53
la ruta es va crear a         2026-08-05 19:02:49   (ec0e9730)
```

El procés que serveix **portava nou hores de retard sobre la ruta**: no l'havia carregada mai.
D'aquí que tot semblés correcte des de dins —codi al disc amb la ruta, `manage.py check` net,
`resolve()` la troba— i que l'Agus rebés 404 a cada intent des de fora.

Prova que ho separa sense ambigüitat (sense credencial, contra el procés viu):

```
ABANS          404  /api/v1/mesures/diccionari/     ← el procés no la té
               401  /api/v1/models/                 ← ruta viva, només li falta auth
DESPRÉS        401  /api/v1/mesures/diccionari/     ← viva
```

També explica per què la meva verificació anterior deia 200: l'`APIClient` de DRF carrega el codi
del **disc**, no el del procés desplegat. Les dues coses eren certes alhora, i és exactament la
distinció que el fum no feia.

## Fet

**Reinici del servei** (autoritzat per l'Agus, opció «reinicia i queda't mirant»). Carregava 19
commits de backend que aquell procés no havia corregut mai; **0 migracions pendents** i
`manage.py check` net abans de tocar-lo.

Comprovacions després del reinici:

```
✓ /api/v1/mesures/diccionari/  404 → 401 (directe i via nginx)
✓ cap 404 als endpoints que fa servir la pantalla (models · taula-mesures · poms/cerca · items)
✓ cicle de model (crear · llistar · esborrar)      verd
✓ P0.1 · el camí d'un valor + F5                   verd
✓ cap error al journal del servei
```

⚠️ Una línia al log en arrencar, **benigna i no nova**: `Control server error: [Errno 13]
Permission denied: '/var/www/.gunicorn'`. És el socket de control de gunicorn, no el servei
d'HTTP — l'aplicació respon amb normalitat. Anotat, no tocat.

## Per què el fum no ho va caçar (i què s'ha fet)

El fum de P0.2 **estubejava la crida del diccionari**: provava la pantalla contra una API
imaginària i donava verd mentre l'usuari rebia 404. Ara, **abans d'obrir cap navegador**,
pregunta al backend DESPLEGAT si la ruta hi és: sense credencial, **401 = viva · 404 = el procés
no la té**. Verificat que el guard discrimina (ruta real 401 · ruta inventada 404).

S'hi han afegit les altres dues coses que la consola ensenyava i el fum no mirava: **F5 × 3** (la
cache del diccionari és de mòdul i una recàrrega la buida) i **cap 404 a la consola**.

```
✓ 0 · la ruta és VIVA al backend desplegat (HTTP 401 sense credencial)
✓ A · amb diccionari SA hi són les columnes d'instància: ['Posició', 'Estat']
✓ A · F5 × 3 · les columnes hi segueixen a cada recàrrega
✓ A · consola sense cap 404
· B · amb diccionari CAIGUT · cap columna, PERÒ avís + Reintenta
```

## La millora de P0.2 es queda, i ara sí que serveix

L'avís + Reintenta + cache es mantenen. Abans picaven una porta tapiada; **ara protegeixen del
cas transitori de debò** (una petició que surt abans que la sessió estigui a punt), que era el
que estaven pensats per cobrir.

## 🚩 El que segueix obert

- **La verificació amb la teva sessió al navegador la fas tu.** Els tokens encunyats des del
  shell segueixen donant 401 fins i tot després del reinici, o sigui que la teoria del
  SECRET_KEY desfasat no era la bona i el clic real segueix sense poder-se automatitzar.
  **Obre Definició POM al MILEY i mira que surtin POSICIÓ i ESTAT.**
- **La lliçó operativa:** un `npm run build` desplega el frontend a l'instant, però **el backend
  no es desplega sol**. Cap dels controls del mètode (build, check, tests) mira si el procés que
  serveix porta el codi que hem escrit. Val la pena decidir si el reinici entra al ritual de
  desplegament — avui aquesta divergència va costar un matí.

## Commit

| Hash | Què |
|---|---|
| `133b846b` | 21 · el fum del diccionari pica la RUTA REAL, no la que ell mateix estubejava |

(El reinici del servei no és un commit: és una acció d'infra sobre staging.)
