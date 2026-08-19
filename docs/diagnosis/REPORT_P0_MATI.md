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

---

# TRAM · la identitat de la fila (06/08, tarda) — els 5 punts, fets

> Commits petits i build per commit, amb l'Agus entrant mesures a la mateixa pantalla.
> **Cap canvi al desat de valors ni al carril.** Verificat sobre el model de prova, mai el MILEY.

| # | Punt | Estat |
|---|---|---|
| 1 | POSICIÓ: només Left/Right + el ＋ | ✅ `666ba2ec` |
| 2 | ESTAT: «Extended» sense el sinònim | ✅ `666ba2ec` |
| 3 | El llapis d'identitat (i fora l'edició per clic) | ✅ `662d4ec9` |
| 4 | La nomenclatura, en daurat ple | ✅ `2d876e5e` |
| 5 | La ⓘ de traducció | ✅ `555e0cdd` |

## 1 · Quin criteri s'ha fet servir per a les píndoles

**Les dues primeres de cada eix per `display_order` del diccionari.** Cap slug escrit al codi.

El catàleg dona avui `POSICIO`: left(1) · right(2) · top(3) · bottom(4) · cf(5) · cb(6) ·
side(7) · waistband_seam(8). Les dues primeres per ordre són, exactament, **Left i Right** — que
és el que la decisió demana, però arribat pel camí del diccionari i no per una llista. Si el
catàleg reordena, la fila el segueix sense tocar codi.

La regla s'aplica **per eix**, no només a la posició: `ESTAT` només en té dues i queda igual.
Cap opció es perd — el modal del `＋` recorre TOTS els eixos amb TOTES les opcions, i a més és
l'únic lloc que pot creuar-los (`left` i `relaxed` alhora). Verificat: les 6 posicions restants
hi són.

⚠️ **Un cas que val la pena saber:** si una fila ja té una posició que ara no es pinta (p. ex.
`top`), les píndoles surten totes apagades. La posició **no es perd ni s'amaga** — es llegeix al
nom de la fila (`… · Top`) i s'edita pel `＋`. Ho deixo així perquè el brief demana explícitament
només dues píndoles; si vols que la fila ensenyi també la seva, és una línia.

## 2 · «Extended» — i el que queda per decidir amb la Montse

El catàleg porta **`nom_en = 'Extended / stretched'`** a `MeasurementInstance`. S'ha escurçat
**només la PRESENTACIÓ** (es pren el primer terme abans de la barra); **la BD no s'ha tocat**.

La regla és el separador i no una llista de casos: qualsevol fila que porti sinònims darrere
d'una barra es presentarà pel primer terme.

🚩 **PENDENT amb la Montse:** decidir si el nom del catàleg ha de ser «Extended» a seques. Mentre
digui `Extended / stretched`, el nom llarg segueix sent el canònic a la BD i és el que veurà
qualsevol superfície que no passi per aquesta funció de presentació.

## 3 · El llapis · què s'ha retirat

El text del nom **ja no s'edita clicant-hi**: en repòs és estàtic, sense cursor de text ni
subratllat en passar-hi per sobre. L'única porta és el llapis, i obre **NOM + NOMENCLATURA
alhora**. L'estat viu a la FILA, no dins de cada camp: són la mateixa resposta a «quina mesura és
aquesta», i editar-los per separat era el que feia que se'n canviés un i l'altre es quedés dient
una altra cosa.

**No s'ha tocat cap porta de desat**: el nom segueix anant per `baseMeasurements.setNoms` i la
nomenclatura pel buffer de la taula. Només canvia **quan** es veuen els camps.

## 4 · Per què es veia apagada la nomenclatura

No era una decisió de disseny. El codi (A · B · E1 · AC FR…) es pinta com a **placeholder** de
l'input mentre el model no té nomenclatura pròpia —que és el cas normal: a staging `nom_fitxa`
és buit a **totes** les files— i **el navegador esvaeix els placeholders per defecte**. Una regla
`input[data-nomen]::placeholder { color: var(--gold); opacity: 1 }` sobre el hook que ja hi era.

## 5 · La ⓘ · la dada hi era; fallava el mecanisme

**No falta cap traducció al catàleg.** Les files porten `nom_ca` ple («Chest width» → «Ample de
pit») i la ⓘ ja es pintava amb el `title` correcte a dins. El que fallava:

- el **`title` natiu** només surt passant-hi per sobre i esperant-se un segon llarg;
- **no respon al clic**;
- damunt d'una icona de 12px, la meitat de les vegades no arriba a sortir.

Ara respon a **hover**, **clic** (que la fixa, per llegir-la amb calma) i **focus de teclat**;
`Esc` i un clic a fora la tanquen. Va per **portal**: la cel·la del nom viu dins del contenidor
`overflow-x:auto` i qualsevol cosa posicionada que en surti queda retallada — la mateixa trampa
del desplegable del cercador (P0.2b).

També s'hi ha declarat la **caixa del botó (16×16)** en comptes d'heretar la del glif: ho vaig
veure al fum, on la font d'icones no carrega i el botó era un objectiu de 0×0. Amb la font
caiguda, la ⓘ seria impossible de clicar i sense manera de saber per què.

## Verificació

```
✓ 0 · la ruta és VIVA al backend desplegat (HTTP 401 sense credencial)
✓ A · columnes d'instància: ['Posició', 'Estat']
✓ A · F5 × 3 · hi segueixen a cada recàrrega
✓ A · píndoles: ['Extended', 'Left', 'Relaxed', 'Right'] (la resta, al ＋)
✓ A · llapis ×6 · obre nom i nomenclatura alhora · el text no s'edita per clic
✓ A · el ＋ porta les 6 posicions restants
✓ A · ⓘ · hover i clic ensenyen la traducció ('Ample de pit')
✓ A · consola sense cap 404
· B · amb diccionari CAIGUT · cap columna, PERÒ avís + Reintenta
✓ C · ca / es / en · píndoles correctes · consola neta
```

Les píndoles van en **anglès canònic als tres idiomes**: és la decisió del 05/08 (d'aquesta
paraula surt el sufix del codi). No és un defecte de traducció.

## Anotat pel camí (fora d'abast, no tocat)

- **El modal de posicions no es tanca amb `Esc`** i el seu vel es queda interceptant els clics.
  El fum ho esquiva recarregant. Val la pena arreglar-ho: `Esc` és el gest que tothom prova.
- L'**`aria-label` d'un botó sobreescriu el nom accessible** — el `＋` no es troba amb
  `get_by_role(name='＋')`. No és un defecte, però convé saber-ho per als fums.
- `MeasureGrid.jsx` i `ComprovacioPanel.jsx` segueixen amb el hook antic del diccionari: si els
  falla, callen. La regla de l'avís només s'ha aplicat a `EditableTable`.

## Commits

| Hash | Què |
|---|---|
| `666ba2ec` | 24 · les píndoles, a dues per eix · i «Extended» sense el sinònim |
| `2d876e5e` | 25 · la nomenclatura del POM, en daurat ple |
| `662d4ec9` | 26 · el llapis d'identitat · nom i nomenclatura s'obren junts |
| `555e0cdd` | 27 · la ⓘ de traducció ja respon · hover, clic i teclat |
| `45f7fec2` | 28 · el fum cobreix la identitat de la fila |

---

# TRAM P0.5 · el contenidor de graduació i les columnes de la regla

| Punt | Estat |
|---|---|
| **P0.5a** · contenidor central, pertinença ordena | ✅ `ff7585d0` |
| **P0.5b** · columnes de la regla a Definició POM | ✅ `4dcf18a1` (en LECTURA) |
| **P0.5c** · guard D-31.4 amb consentiment | ✅ **ja existia** — i **no arribava a la pantalla**; arreglat a `ff7585d0` |

## P0.5a · per què el panell antic no deixava triar

`GraduacioPanel` és el **pas 4 del wizard**, i hi porta les portes del wizard:

- sense `size_system` no ensenya res (`grading_needs_system`);
- demana un **FIT** abans d'obrir el picker;
- el picker corre en mode **estricte** (`matchingRuleSetsStrict`), que exigeix els cinc eixos i
  **exclou** tot el que no casi.

Amb un model real al davant això acaba en «falta la construcció» i una llista buida: es veu què
falta i no es pot triar **res** — quan el que es venia a fer era assignar un joc que ja existeix.

Ara és un contenidor **central** i la pertinença **ordena** en comptes d'excloure — la mateixa
llei del pas 3 del wizard (sistemes de talles) i de C5 al catàleg de peces (D-31.3): primer els
jocs del **client del model**, després la resta; els que no encaixen surten **atenuats amb el
motiu** i es poden triar igualment.

**No s'ha fet cap picker nou.** `RuleSetPicker` ja tenia el mode `eliminatiu` (C5) que fa
exactament això i ja pinta nom, recompte de regles i el joc seleccionat. El que faltava era que
algú el cridés sense el mode estricte. **`GraduacioPanel` no s'ha tocat**: segueix sent el pas 4.

## 🔴 P0.5c ja existia — i el seu diàleg no es pintava mai

El brief demanava construir l'avís de D-31.4. **Ja hi era**: `useConfirmacioRuleset` porta els dos
avisos conscients (D1 · client aliè · D-31.4 · esborrat de residents), amb el recompte i el
desglossament per origen (IMPORTED separat), i el backend ja els retorna com a 409 amb un flag per
cas. No s'ha duplicat res.

**El que fallava era que el diàleg no arribava a la pantalla.** `{dialegRuleset}` estava escrit al
final de **`TabAIAnalysis`** — un altre component, 1.400 línies més avall — on la variable ni tan
sols és a l'abast. O sigui: el guard existia, el backend tornava el seu 409, i la confirmació no
es pintava **mai**. Assignar un joc que havia d'esborrar regles pròpies es quedava en un botó que
no responia.

Ho vaig trobar perquè `eslint` deia alhora dues coses contradictòries sobre la mateixa variable:
«assignada i no feta servir» (:518) i «no definida» (:2418). **Totes dues d'abans d'aquest tram.**
Ara es pinta on viu el hook que el crea.

## P0.5b · les columnes, i on m'he aturat

Els quatre camps **ja viatjaven** a cada fila de `taula-mesures` (`logica`, `increment_base`,
`increment_break`, `talla_break_label`): no calia cap petició nova, només pintar-los quan hi ha
graduació de què parlar.

- **joc assignat** → columnes plenes;
- **sense cap tria** → no hi són (l'estat que vas fixar el 05/08);
- `null` es pinta `—`, mai zero: un règim sense delta no és un delta de zero.

⚠️ **EN LECTURA, i és una frontera deliberada.** Fer-les editables vol dir tornar a enviar `rules`
des d'aquesta taula, i això **es va retirar el 31/07 precisament perquè feia mal**: enviava una
entrada per **cada** fila amb `logica: 'LINEAR'` i acabava creant regles residents a models que
ningú havia graduat (i, amb la proposta del catàleg pintada a sobre, materialitzava la regla d'un
altre). Reobrir aquell camí demana decidir abans **quines files hi entren i quan**. No ho he fet a
corre-cuita.

## 🚩 «Entrada manual» — el que el domini no té

L'opció hi és al contenidor, però **no escriu res**, i cal saber-ho:

Al domini **no hi ha cap camp «aquest model es gradua a mà»**. `update-step2` només sap assignar
un joc o desacoblar-lo. El que sí que existeix és que un model **amb regles residents i sense
joc** ja **és** un model graduat a mà — és l'estat que deixa la importació.

Conseqüència honesta: mentre no s'hi hagi escrit **cap** regla, la intenció «vull graduar a mà»
viu només a la pantalla i **un F5 la perd**. En escriure la primera regla, l'estat es manté sol.
Tancar-ho de debò vol dir **un camp nou i una migració** (i, per tant, restart) — o acceptar que
l'entrada manual comença en el moment que s'escriu la primera regla. **És decisió teva.**

## Verificació

```
model 1302 · joc 115 · fila0: LINEAR · Δ2.0 · Δbreak 3.0 · break XS
✓ les quatre columnes surten a la capçalera i amb valors
✓ després d'F5 hi segueixen
✓ el mateix model SENSE joc assignat no n'ensenya cap
✓ cap error de pàgina
```

Build net i `eslint` **0 errors** a `ModelSheet.jsx` — HEAD en tenia **2**, que eren justament els
del diàleg que no es pintava.

## Anotat, no tocat

- Les columnes de la regla **no són editables** (v. la frontera de dalt).
- El **modal de posicions segueix sense tancar-se amb `Esc`** (ve del tram anterior).
- `GraduacioPanel` queda viu per al wizard. Quan el contenidor central hagi rodat, val la pena
  decidir si el pas 4 del wizard ha de fer servir el mateix, i llavors el panell es jubila.
