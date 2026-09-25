# DIAGNOSI — Consentiment de les germanes en consolidar fitting → base

Data 2026-09-24 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`.
Abast: entendre, abans de construir el modal de consentiment (LLEI Agus 24/09), on i com es
consolida avui un fitting a la base, com es calculen i s'escriuen les germanes, i què fa
falta (dades, model, pantalla) per interposar-hi una decisió humana per germana.

Convenció: `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi** (grepat, no
especulat). Les propostes de disseny porten sempre `💡 PROPOSTA (a validar)`.

**Precedent citat al brief, verificat absent:** `docs/ordres/ORDRE_FIX_CONSOLIDACIO_FITTING.md`
**NO EXISTEIX** al disc — la sessió de Patró B del 23/09 (commits `a8575ec4` + `0bbfd08a`) no
va arribar a escriure'l. Aquesta diagnosi treballa contra el codi real dels dos commits, no
contra cap acta.

---

## Resum executiu

1. **El gest no és explícit.** No hi ha cap botó «Aplicar a la base»: la consolidació és un
   EFECTE COL·LATERAL de «Gravar i tornar» (tanca la peça de fitting) i, per una porta
   diferent, de «Propagar a grading» amb `new_version=true`. Cap dels dos avisa que mourà
   germanes. → BLOC Q1.
2. **El càlcul ja és pur i reutilitzable sense escriure res.** `deriva()` (`services_derivacio.py:125`)
   no escriu; és `aplica()` qui ho fa. El modal es pot alimentar de `deriva()` tal qual. La
   FRASE humana («extended = relaxed + 18») **NO EXISTEIX**: cap format actual la genera. →
   BLOC Q2.
3. **`origen` ja distingeix mesurat de derivat** (11 valors, 4 en ús a `fhort`: `IMPORTED`
   465 · `MANUAL` 88 · `FITTED` 14 · `DERIVAT` 6) i **ja hi ha un badge de producció** que el
   llegeix (`fittingGridAdapter.jsx:159`). Bona base pel defecte del modal i pels badges. →
   BLOC Q3.
4. **No hi ha enlloc on desar «què es va proposar i què es va triar» per germana.**
   `MeasurementChangeLog` és append-only i només escriu quan el VALOR canvia — «vaig triar
   mantenir» no produeix cap fila avui. Cal un model nou (migració). → BLOC Q4.
5. **El «cas 2578» no s'ha pogut localitzar a la BD de staging** (ni per id ni per
   pom=B+instancia=`waistband_seam`, censat als dos schemas amb dades, `fhort`/`los`) — es
   respon per LECTURA DE CODI, i la resposta desemmascara un **forat real i actual** al fix
   `a8575ec4` i a la comanda `0bbfd08a`: una instància mesurada **sense desviació**
   (`valor_real == valor_teoric`) no entra mai al conjunt `mesurades`, i per tant SÍ que pot
   ser trepitjada per la propagació d'una germana — el mateix bug que es va tancar el 23/09,
   per una escletxa que el fix no tapava. → BLOC Q6.
6. **Hi ha un SEGON lloc amb la trepitjada sense el fix del 23/09**: `resolve_size_check`
   (`services_size_check.py:230-264`) fa el mateix escriu-i-deriva línia-a-línia que
   `consolidate_base_from_fitting` feia abans d'`a8575ec4`. La LLEI hi aplica igual, però el
   Patró B d'aquest sprint (segons el brief) només toca el fitting. → BLOC Q7.

---

## BLOC Q1 — El gest

**No hi ha cap acció «Aplicar a la base».** La consolidació neix com a EFECTE de dos gestos
diferents que no la mencionen:

### Camí 1 — «Gravar i tornar» (tanca la peça de fitting)
- Botó: `frontend/src/components/model/SessionActions.jsx:78` —
  `onClick={() => doSave(false)}>{t('fitting.save.save_and_back')}`.
- `doSave` (`SessionActions.jsx:27-41`) crida `pieceFittings.close(pieceFittingId, …)`
  (`frontend/src/api/endpoints.js:868`) → `POST /api/v1/piece-fittings/{id}/close/`.
- Backend: `PieceFittingViewSet.close` (`fitting/views.py:551-570`) → `services.close_piece_fitting`
  (`fitting/services.py:782`) → dins de LA MATEIXA transacció atòmica (`fitting/services.py:823`):
  `reconcilia_linies` → **`consolidate_base_from_fitting`** (`:834`) → Welford → versionat →
  `_seal_session`.
- Un segon caller amb el mateix `close`, per a `GarmentSet` (multi-peça): `FittingDetail.jsx`
  `doSave` (`:217-230`) el crida **en bucle, una vegada per peça** (`for (const g of toClose)`,
  `:224-230`) — si el modal es lligués a `close`, una sessió de N peces obriria N modals en
  sèrie tret que es dissenyi un pas de recollida previ a tot el lot.

### Camí 2 — «Propagar a grading» amb `new_version=true`
- Endpoint: `POST /models/{id}/generar-grading/` → `generate_grading_view`
  (`models_app/views.py:3130`, ruta a `models_app/urls.py:237`).
- Dins del `with transaction.atomic()` (`models_app/views.py:3208`), ABANS de cridar el motor,
  itera els `PieceFitting` OBERTS del model i consolida cadascun (`:3223-3228`):
  `for _pf in _open_pfs: n_consolidat += len(consolidate_base_from_fitting(_pf, …))`.
- `n_consolidat` es COMPTA però mai es RETORNA a la resposta ni es mostra — la propagació pot
  moure germanes en silenci total, sense ni un toast.

### ¿Es pot interposar un pas de confirmació sense trencar el flux?

**FET**: `consolidate_base_from_fitting` avui NO té mode "només calcular" — barreja en un sol
pas «quines línies calen consolidar» amb «escriure-les» (`fitting/services.py:758-798`, v.
BLOC Q2 per `deriva()`, que sí que ho separa a nivell de germana).

💡 **PROPOSTA (a validar)**: dividir en dues crides, sense tocar `close`:
1. `POST /piece-fittings/{id}/close/` (primera trucada, SENSE `decisions`): calcula els
   candidats mesurats + les seves germanes afectades (via `deriva()`, pur) i **respon 200
   amb la proposta, sense escriure res** si `deriva()` retorna alguna fila per a alguna
   germana fora del conjunt `mesurades`. Si no n'hi ha cap, escriu de seguida (comportament
   actual, cap modal).
2. El mateix `close`, ARA amb `decisions` al body (format BLOC final), aplica exactament
   el que el tècnic ha triat i segella.

Aquest disseny no trenca el contracte actual (`close` sense `decisions` continua funcionant
igual quan no hi ha cap germana implicada) i evita un endpoint nou. Pel camí 2 (propagació),
la mateixa idea val però cal decidir si el modal hi apareix igual (avui `n_consolidat` ja es
perd en silenci — BLOC Q7 ho assenyala com a abast, no com a peça d'aquest sprint).

**Veredicte Q1: el gest és implícit als dos camins; interposar-hi un pas és viable sense
trencar el contracte, però `FittingDetail.jsx` (multi-peça) demana decidir si el modal és
per PEÇA o per SESSIÓ abans de tocar res.**

---

## BLOC Q2 — Les germanes (`services_derivacio.py`)

### Com es calculen
- `germanes_de(bm, *, nomes_actives=True)` (`:81-117`): mateix `(model, pom, garment)`,
  `is_active` opcional, i `Q(instancia=bm.instancia) | Q(capa=bm.capa)` (`:115-117`) —
  «comparteixen un dels dos eixos i no l'altre», garantit per la unicitat
  `(model, pom, capa, instancia, garment)`.
- `deriva(bm, valor_anterior, valor_nou, *, nomes_actives=True, exclou=None)` (`:125-160`):
  **PUR — no escriu res, no toca `bm`, no dispara cap senyal** (docstring `:127`, verificat:
  cap `.save()` ni `.update()` al cos). Calcula `increment = round(valor_nou - valor_anterior, 2)`
  (`:140`) i per cada germana activa amb valor: `valor_proposat = round(actual + increment, 2)`
  (`:158`). Retorna `[]` si `valor_anterior is None`, si l'increment és 0, o si la germana no
  té `base_value_cm` (`:130-136`, `:146-148` — mai s'inventa un valor de partida).
- Retorna una llista de `Derivacio` (dataclass congelada, `:64-78`):
  `base_measurement_id, pom_id, capa, instancia, eix (CAPA|INSTANCIA), valor_actual,
  increment, valor_proposat`.
- `exclou` (paràmetre afegit a `a8575ec4`, `:125`, `:145-146`): un conjunt de
  `(pom_id, capa, instancia)` que `deriva()` salta encara que siguin germanes vives amb
  valor — és el mecanisme que ja usa `consolidate_base_from_fitting` per no trepitjar les
  instàncies mesurades EN AQUESTA sessió (v. BLOC Q6 pel forat que hi queda).
- `aplica(bm, valor_anterior, valor_nou, …, exclou=None)` (`:170-201`) és qui ESCRIU: itera
  `deriva(...)` i per cada `Derivacio` fa `germana.save(update_fields=['base_value_cm',
  'origen', 'updated_at'])` (`:198`) amb `origen=ORIGEN_DERIVAT` (`:191`, `= 'DERIVAT'`,
  `:38`).

### Mode «només calcular» per alimentar el modal
**FET: ja existeix.** `deriva()` és exactament aquesta funció — no cal escriure'n cap de
nova per a la PART de germanes. El que falta és que `consolidate_base_from_fitting`
exposi «quines línies consolidaria» sense trucar `aplica()` (v. BLOC Q1).

### La frase humana («extended = relaxed + 18»)
**NO EXISTEIX cap generador d'aquesta frase.** El més a prop és el `motiu` que `aplica()`
escriu a `MeasurementChangeLog._motiu` (`:196-199`):
```
f'Derivat de {bm.capa}/{bm.instancia or "—"} ({d.increment:+.2f} cm)'
```
— parla en termes de capa/instància D'ORIGEN i increment amb signe i 2 decimals
(`+18.00 cm`), no en termes de LA GERMANA (`extended`) i el seu valor RESULTANT. Fabricar
«extended = relaxed + 18» necessita, per cada `Derivacio`: la instància DESTÍ (`d.instancia`,
ja hi és), la instància ORIGEN (`bm.instancia`, ja hi és) i l'increment (`d.increment`, ja
hi és) — les dades hi són TOTES a `Derivacio` + `bm`; **el que falta és el FORMAT i, sobretot,
l'ETIQUETA HUMANA de la instància**: `pom.MeasurementLayer` dona etiqueta humana per a
`capa` (consumida per `LAYEN` a la maqueta, `ops/maquetes/maqueta_fitting_v4.html:344`, i per
`GET /api/v1/mesures/diccionari/` → `capes`), però **NO EXISTEIX cap vocabulari equivalent
per a `instancia`**: grepat `pom/models.py`, `models_app/vocabulari_views.py` i el front
(`frontend/src/utils/*.js`) — cap taula, cap camp `label`, cap `.replace()`/`.capitalize()`
de slug a frase. Avui `instancia='waistband_seam'` es mostraria literal.

💡 **PROPOSTA (a validar)**: (a) reaprofitar `deriva()` sense canviar-la; (b) al serialitzador
de la proposta, generar la frase amb un format fix (`f"{etiqueta(d.instancia)} = {etiqueta(bm.instancia)} {d.increment:+.1f}"`)
i, mentre no hi hagi vocabulari d'instància, `etiqueta()` fa un humanitzat mínim
(`slug.replace('_',' ').replace('-',' ').capitalize()`) — NO bloqueja el Patró B, però la
frase serà lletja fins que hi hagi vocabulari real (fora d'abast, com `capa`).

**Veredicte Q2: el motor de càlcul ja serveix el modal sense tocar-lo; la frase humana i
l'etiqueta d'instància són l'única peça nova de "domini" que cal construir o pedaçar.**

---

## BLOC Q3 — L'origen

`BaseMeasurement.ORIGEN_CHOICES` (`models_app/models.py:687-722`), 11 valors declarats:
`STANDARD, IMPORTED, MANUAL, FITTED, CALCULATED, TEMPLATE, CHECKED, ITEM_STANDARD, COPIED,
FEDERAT, DERIVAT`.

### Cens a staging (avui, 24/09, `SELECT origen, count(*) … GROUP BY origen`)

**Schema `fhort`** (573 files a `models_app_basemeasurement`):

| origen | files |
|---|---|
| IMPORTED | 465 |
| MANUAL | 88 |
| FITTED | 14 |
| DERIVAT | 6 |

Els altres 7 valors declarats (`STANDARD, CALCULATED, TEMPLATE, CHECKED, ITEM_STANDARD,
COPIED, FEDERAT`) tenen **0 files** avui a `fhort`.

**Schema `los`**: taula `models_app_basemeasurement` **buida (0 files)** — confirmat amb la
unitat i el port bons (`postgresql@18-main`, port 5433, v. `ftt-bd-staging-com-sinterroga`),
no és cap fals negatiu: `los` és un tenant real sense dades en aquesta taula encara.

### Per al defecte del modal i els badges
- **Defecte proposat pel brief** («germana amb DERIVAT → proposat; amb MESURAT → mantenir»)
  necessita una funció `és_mesurat(origen)`. **NO EXISTEIX** com a tal, però el mapa
  `_ORIGEN_TO_CONTEXT` (`models_app/signals.py:200-226`) ja classifica TOTS els origens en un
  `context` de log (`fitting`, `manual`, `import`, `derivat`, `calculated`…) — és la font
  natural per derivar-ne un booleà (`context != 'derivat'` ⇒ mesurat) sense duplicar la
  llista.
- **Badge**: `fittingGridAdapter.jsx:156-159` YA pinta `marca: row.origen === 'DERIVAT' ?
  'derivada' : null` a la graella de fitting — el mecanisme de badge EXISTEIX en producció i
  es pot reutilitzar/estendre per al modal (mateix predicat, superfície nova).

**Veredicte Q3: `origen` ja porta tota la informació que el defecte necessita; falta NOMÉS
la funció `és_mesurat()` (trivial, reaprofitant `_ORIGEN_TO_CONTEXT`), no cap dada nova.**

---

## BLOC Q4 — La decisió (rastre i «no tornar a preguntar»)

### El que ja existeix i per què NO serveix tal qual
`MeasurementChangeLog` (`models_app/models.py:1002-1034` i camps addicionals `capa`/
`instancia`/`garment` fins `:1070`ish) és **append-only a nivell d'aplicació**
(docstring `:1010-1011`) i el seu ÚNIC escriptor és el senyal `log_measurement_change`
(`models_app/signals.py:253-...`). Aquest senyal:
- Només crea fila si `base_value_cm` **canvia de debò** (`models_app/signals.py:312-317`:
  `if not created and old_value == instance.base_value_cm: return`).
- No té CAP concepte de «es va proposar X i es va triar mantenir» — «mantenir» és
  literalment NO ESCRIURE, i no escriure no dispara `post_save`, o sigui que **avui és
  estructuralment impossible que aquesta taula recordi un «mantenir»**.
- No té cap columna per a «valor proposat» (només `valor_anterior`/`valor_nou`, que parlen
  del que SÍ es va escriure).

### Cap altra taula ho cobreix
Grepat `PieceFitting`, `PieceFittingLine`, `FittingSession`, `GradingVersion` (`fitting/models.py`
sencer per noms de camp) i `SizeFitting`: **NO EXISTEIX** cap camp ni taula que guardi una
decisió «per germana, per sessió». `PieceFittingLine.decisio` (`fitting/models.py:469-479`)
és el veredicte de la CEL·LA PRÒPIA del tècnic (D-31.21), no una decisió sobre la proposta
d'una ALTRA fila.

💡 **PROPOSTA (a validar, migració nova)**: un model petit, p. ex.
`FittingDerivationDecision` a `models_app` (o `fitting`, a decidir per veïnatge amb
`PieceFitting`):
```
piece_fitting        FK → fitting.PieceFitting
base_measurement     FK → models_app.BaseMeasurement   (la germana)
valor_proposat        float
decisio               choices: MANTENIR | PROPOSAT | NOU_VALOR
valor_final            float (= valor actual si MANTENIR, = proposat si PROPOSAT, = editat si NOU_VALOR)
created_by / created_at
```
Unique `(piece_fitting, base_measurement)` — una decisió per germana i per sessió (el
«no tornar a preguntar» es llegeix comprovant si ja hi ha fila per aquest parell abans de
tornar a mostrar el modal). `MeasurementChangeLog` seguiria escrivint-se IGUAL que avui, però
NOMÉS quan la decisió sigui `PROPOSAT`/`NOU_VALOR` (és a dir, quan de debò hi hagi un canvi de
valor) — aquesta taula nova és la que recorda el «mantenir», que és l'ÚNIC cas que
`MeasurementChangeLog` no pot ni podrà recordar sense trencar el seu contracte d'append-only.

**Veredicte Q4: NO EXISTEIX cap lloc reutilitzable; cal un model nou i una migració petita
(un FK doble + un `choices` + un float). No hi ha alternativa sense migració que no sigui
un camp JSON ad hoc a `PieceFitting`, que perdria la unicitat per germana.**

---

## BLOC Q5 — La pantalla

### Component que dispara la consolidació
- `SessionActions.jsx` (frontend, `frontend/src/components/model/SessionActions.jsx`) és
  el component que crida `close` des del botó «Gravar i tornar» (v. BLOC Q1). Ja té DOS
  modals amb el patró exacte que demana el brief: `overlay`/`modalBox` (`:17-18`), capçalera
  amb icona, cos, i **dos botons alineats a la dreta** (`display:flex; justifyContent:
  flex-end`, `:95`, `:113`) — un `plain` (cancel·lar) i un `gold`/`err-ple` (acció). El modal
  de consentiment hi encaixa com un TERCER `useState` (`derivationProposal`) al costat de
  `sealedModal`/`discardMotiu`.
- **Restricció d'amplada**: `modalBox` fixa `maxWidth: 460` (`:18`) — pensat per a text, no
  per a una TAULA amb N germanes. El brief demana una taula: caldrà una variant més ampla
  (o reutilitzar `modalBox` amb `maxWidth` més gran només per aquest cas), NORMA_LAYOUT no
  ho prohibeix (no hi ha cap regla d'amplada de modal a `ops/maquetes/NORMA_LAYOUT.md`).

### Norma de botons (`ops/maquetes/NORMA_LAYOUT.md`)
- Primari únic blau (`--accio`, `:25`) — coincideix amb el brief («Aplicar» primari únic).
- **ACCIONS COMPOSTES (esmena Agus 08/08, `:41`)**: «si una acció primària té variants…, UN
  sol botó blau amb desplegable — mai dos botons d'acció directa a la mateixa capçalera.» —
  Aquesta norma xoca de cara amb el brief, que demana TRES botons visibles («Aplicar» +
  «Acceptar totes les proposades» + «Mantenir totes»): els dos secundaris no són «variants
  de la mateixa acció primària» sinó ATALLS que OMPLEN la taula abans de prémer «Aplicar»
  (no envien res per si sols) — **cal que Agus confirmi si això els treu de la comporta
  d'«accions compostes»** o si ha de ser un desplegable sota «Aplicar» en comptes de dos
  botons secundaris visibles.

### Maquetes existents a respectar/revisar
- **`ops/maquetes/maqueta_fitting_v4.html:371-420`**: MOSTRA IL·LUSTRATIVA d'una germana que
  es mou **EN VIU, DINS DE LA TAULA**, mentre el tècnic tecleja el valor de l'exterior —sense
  cap modal, sense cap consentiment— amb una etiqueta `DERIVADA`/`NO ACTUALITZADA` per fila
  (`:408-420`). **Aquest patró CONTRADIU la LLEI NOVA** (avui no hi ha proposta ni decisió,
  la fila simplement es mou tota sola a la maqueta). Cal que la maqueta es revisi o que
  quedi explícitament marcada com a SUPERADA quan es construeixi el modal.
- `ops/maquetes/maqueta_temps_declarat_i_modal_v2.html` — modal amb formulari, no amb taula;
  no aporta patró de taula-dins-de-modal directament reaprofitable, però confirma l'estil
  general (`overlay`/`modalBox`) ja vist a `SessionActions.jsx`.

**Veredicte Q5: el component i el patró de modal ja existeixen i encaixen; calen (a)
`maxWidth` més ampla per a la taula, (b) una decisió d'Agus sobre els dos botons secundaris
vs. la norma d'accions compostes, i (c) revisar/segellar `maqueta_fitting_v4.html` que
mostra el comportament contrari al que mana la llei nova.**

---

## BLOC Q6 — El cas 2578

**No localitzat a la BD de staging.** Cercat per `id=2578` a `fhort.models_app_basemeasurement`
(0 files; l'id cau dins el rang existent `2207-3406` però no hi és) i per
`pom.codi_client='B' AND instancia ILIKE '%seam%'` (0 files) i per la mateixa combinació a
`fitting_piecefittingline` (0 files). `los` no té dades a cap de les dues taules. Grepat
també `docs/` i `backend/scripts_tmp/` per "2578": cap referència. **No es pot confirmar la
fila; la pregunta es respon per lectura de codi**, i la resposta és sòlida perquè no depèn
de la fila concreta sinó del PREDICAT que decideix «mesurada».

### El predicat real, avui (post `a8575ec4`)
`consolidate_base_from_fitting` (`fitting/services.py:758-770`):
```python
a_consolidar = []
for line in linies:
    if line.valor_real is None:
        continue
    if abs(line.valor_real - line.valor_teoric) < 1e-6:
        continue  # no change on this line          ← :762-763
    if line.size_label.strip() != base_size:
        continue
    a_consolidar.append(line)

mesurades = {(line.pom_id, line.capa, line.instancia) for line in a_consolidar}   # :770
```
Una línia amb `valor_real == valor_teoric` (mesurat 41, teòric 41, «sense desviació») **MAI
entra a `a_consolidar`**, i per tant **MAI entra a `mesurades`** — independentment del seu
`decisio`. Aquesta és la causa suficient per si sola; `decisio` buida NO cal per explicar-ho
(encara que també hi contribuiria: cap dels dos punts de `fitting/services.py:752-766`
exigeix `decisio` informat per a la CONSOLIDACIÓ — només ho exigeix la COMANDA DE REPARACIÓ).

**Conseqüència, verificada per lectura (no per repetir el test del 23/09, que ja demostra
el mecanisme general amb altres números):** si UNA ALTRA instància germana d'aquest mateix
POM/capa ES RECTIFICA a la mateixa sessió, `deriva()` (`services_derivacio.py:144-159`)
recorre TOTES les germanes actives amb valor —inclosa aquesta, que NO és a `exclou`
(`exclou=mesurades`, `fitting/services.py:797`)— i li proposa (i `aplica()` li ESCRIU) un
`valor_proposat` que trepitja el 41 mesurat, deixant `origen='DERIVAT'`. **El fix d'`a8575ec4`
tanca el forat de tres instàncies TOTES rectificades; no tanca el d'una instància CONFIRMADA
(mesurada, sense canvi) al costat d'una altra rectificada.**

### I la comanda de reparació tampoc ho recupera
`repara_base_des_de_fitting._proposta` (`models_app/management/commands/repara_base_des_de_fitting.py:69-76`):
```python
if abs(linia.valor_real - linia.valor_teoric) < 1e-6:
    return None, None  # confirmació, no rectificació: no hi ha res a reparar   ← :73-74
```
Amb la línia candidata a `valor_real == valor_teoric == 41`, la comanda descarta la reparació
—pensada per a «recuperar el valor mesurat que es va trepitjar», però la seva pròpia guarda
li impedeix veure que 41 ERA el valor mesurat. La fila queda `origen='DERIVAT'` per sempre,
la comanda diu «cap fila a reparar» i el dry-run no aixeca cap senyal.

### El criteri únic proposat (Q6 ho demana explícitament)
> Una instància mesurada al fitting (`valor_real` present, tingui o no `decisio`) és
> MESURADA — sense exigir que difereixi de `valor_teoric`.

💡 **PROPOSTA (a validar)**: separar DOS conjunts que avui són un de sol:
- **`mesurades`** (per NO trepitjar-les mai): `valor_real is not None` i `size_label ==
  base_size` — PROU. Sense el filtre de desviació, sense exigir `decisio`.
- **`a_escriure`** (les que de debò canvien la base): el filtre actual sencer
  (desviació + no REJECTED + talla base) — aquest sí que ha de seguir exigint desviació,
  perquè escriure `base_value_cm := 41` quan ja val 41 no aporta res.

Avui `fitting/services.py:758-770` calcula `mesurades` COM SI fos `a_escriure` (és el mateix
bucle, `:770` reaprofita `a_consolidar`). Separar-los és el canvi mínim que tanca el forat de
Q6, i és EXACTAMENT la mateixa peça de codi que caldrà tocar per fer lloc al modal de
consentiment (el conjunt «germanes afectades» del modal ha de sortir de `deriva()` aplicat
a `a_escriure`, EXCLOENT `mesurades` sencer, no només `a_escriure`).

**Veredicte Q6: la fila no es pot confirmar, però el mecanisme SÍ, amb una precisió important
—no és un bug nou, és el mateix bug de `a8575ec4` amb un cas que el fix no cobria (mesura
confirmada, no rectificada). Ambdós artefactes del 23/09 (el fix i la comanda) hereten el
mateix forat.**

---

## BLOC Q7 — Abast: altres llocs que deriven germanes en silenci

Cercat `services_derivacio import` i `services_derivacio\.(aplica|deriva)` a tot
`backend/fhort` (fora de tests): **exactament DOS crides** a tot el backend.

| # | Lloc | Gest que ho dispara | Mateixa trepitjada que `a8575ec4`? |
|---|---|---|---|
| 1 | `fitting/services.py:735,797` (`consolidate_base_from_fitting`) | «Gravar i tornar» / «Propagar a grading» (BLOC Q1) | **NO** — arreglat a `a8575ec4` (amb el forat de Q6 pendent) |
| 2 | `models_app/services_size_check.py:184,261` (`resolve_size_check`) | Resoldre un Size Check («Acceptat») | **SÍ, SENSE ARREGLAR** — v. sota |

**Confirmat NO EXISTEIX** derivació silenciosa a: importació (cap crida a
`services_derivacio` a `pom/` ni als views d'extracció/confirm) i edició manual de la taula
(`BaseMeasurementViewSet.perform_update`, `models_app/views.py:539-544`, és un
`ModelViewSet.save()` net, sense cap crida a `aplica`/`deriva` — editar «exterior» a mà NO
mou «folre» avui).

### El forat bessó a `resolve_size_check`
`models_app/services_size_check.py:230-264` fa LITERALMENT el mateix bucle
escriu-i-deriva-línia-a-línia que `consolidate_base_from_fitting` feia ABANS d'`a8575ec4`:
per cada `SizeCheckLine` acceptada, `bm.save()` (`:256`) seguit IMMEDIATAMENT de
`aplica_derivacio(...)` (`:261-263`) SENSE cap `exclou` ni cap fase de «primer totes les
mesurades». Amb un Size Check que resol diverses instàncies germanes del mateix POM a la
vegada, la mateixa trepitjada de Q6/`a8575ec4` hi és intacta, avui.

Un TERCER mecanisme, d'una NATURALESA diferent i que **probablement queda fora d'abast**:
`PieceFittingLineViewSet.propagar` (`fitting/views.py:641-699`, «ancoratge en temps
d'edició») propaga el delta d'una cel·la a les seves germanes de **TALLA** (S/M/L, via
`pom.grading_utils.propaga_ancoratges`), no a germanes de capa/instància, i no toca
`BaseMeasurement` ni `services_derivacio` — escriu `PieceFittingLine.valor_real` en temps
real mentre es tecleja. **No és el mateix sistema de germanor** (eix `talla`, no
`capa`/`instancia`) i el brief ja avisa que «el Patró B d'aquest sprint només toca el
fitting» — cal que Agus confirmi si «el fitting» inclou aquest ancoratge o només el camí de
consolidació (Q1).

**Veredicte Q7: la LLEI del consentiment, en rigor, hauria d'aplicar-se també a
`resolve_size_check` (mateix mecanisme, mateix forat), però el Patró B d'aquest sprint —
segons el brief— només construeix el modal per al fitting. Es recomana ANOTAR
`services_size_check.py:230-264` com a deute obert amb el mateix nom (Patró C) per a un
sprint posterior, en comptes de tocar-lo ara.**

---

## TAULA FINAL — Existeix / Falta / Diferent

| Peça | Estat | Referència |
|---|---|---|
| Càlcul pur de la derivació (sense escriure) | **EXISTEIX** | `services_derivacio.py:125` (`deriva`) |
| Escriptura de la derivació | **EXISTEIX** | `services_derivacio.py:170` (`aplica`) |
| Exclusió de germanes ja mesurades EN AQUESTA sessió | **EXISTEIX, INCOMPLETA** (Q6) | `fitting/services.py:758-770` |
| Mateixa exclusió a `resolve_size_check` | **NO EXISTEIX** (Q7) | `services_size_check.py:230-264` |
| Frase humana de la proposta («X = Y + Z») | **NO EXISTEIX** | — |
| Vocabulari d'etiqueta per a `instancia` | **NO EXISTEIX** (sí per `capa`, `MeasurementLayer`) | `pom/models.py`, `/api/v1/mesures/diccionari/` |
| Origen mesurat/derivat a `BaseMeasurement` | **EXISTEIX**, 4 valors en ús a `fhort` | `models_app/models.py:687-722` (BLOC Q3) |
| Predicat `és_mesurat(origen)` | **NO EXISTEIX** com a funció, trivial de derivar | `models_app/signals.py:200-226` (`_ORIGEN_TO_CONTEXT`) |
| Badge visual d'origen DERIVAT | **EXISTEIX** en producció | `fittingGridAdapter.jsx:159` |
| Model/taula de decisió per germana | **NO EXISTEIX** — cal migració | BLOC Q4 |
| `MeasurementChangeLog` com a substitut | **DIFERENT** — no pot registrar «mantenir» (no hi ha canvi de valor) | `models_app/signals.py:312-317` |
| Endpoint de «previsualitzar sense escriure» | **NO EXISTEIX** — factible sense trencar `close` | BLOC Q1 |
| Component i patró visual del modal | **EXISTEIX**, cal ampliar-lo | `SessionActions.jsx:17-18,95,113` |
| Maqueta consistent amb la llei nova | **DIFERENT** (contradiu la llei) | `maqueta_fitting_v4.html:371-420` |
| Norma d'accions compostes vs. 3 botons del brief | **A ACLARIR AMB AGUS** | `NORMA_LAYOUT.md:41` |

---

## Proposta de contracte (payload) — 💡 PROPOSTA (a validar), per a la maqueta i el Patró B

### 1. Payload de PROPOSTA (resposta del `close`/preview, abans d'escriure)

```json
{
  "consolidacio": "proposta",
  "piece_fitting_id": 4821,
  "mesurades": [
    {"base_measurement_id": 1190, "pom": "B", "capa": "exterior", "instancia": "relaxed",
     "valor_anterior": 40.0, "valor_nou": 44.0}
  ],
  "germanes_afectades": [
    {
      "base_measurement_id": 1191,
      "pom": "B",
      "capa": "exterior",
      "instancia": "extended",
      "eix": "INSTANCIA",
      "origen_actual": "DERIVAT",
      "valor_actual": 42.0,
      "increment": 4.0,
      "valor_proposat": 46.0,
      "frase": "extended = relaxed + 4,0",
      "font": {"instancia": "relaxed", "base_measurement_id": 1190},
      "decisio_defecte": "proposat"
    },
    {
      "base_measurement_id": 1192,
      "pom": "B",
      "capa": "exterior",
      "instancia": "waistband_seam",
      "eix": "INSTANCIA",
      "origen_actual": "FITTED",
      "valor_actual": 41.0,
      "increment": 4.0,
      "valor_proposat": 45.0,
      "frase": "waistband_seam = relaxed + 4,0",
      "font": {"instancia": "relaxed", "base_measurement_id": 1190},
      "decisio_defecte": "mantenir"
    }
  ]
}
```
`decisio_defecte` surt de `és_mesurat(origen_actual)` (BLOC Q3): `DERIVAT` → `proposat`,
qualsevol altre → `mantenir`. Si `germanes_afectades` és `[]`, el frontend NO obre cap modal
i el `close` real (pas 2) es dispara tot seguit sense esperar cap decisió (compleix «si no
n'hi ha cap, cap modal»).

### 2. Payload de DECISIÓ (segona crida al `close`, amb les tries)

```json
{
  "decisions": [
    {"base_measurement_id": 1191, "decisio": "proposat"},
    {"base_measurement_id": 1192, "decisio": "mantenir"},
    {"base_measurement_id": 1193, "decisio": "nou_valor", "valor": 47.5}
  ]
}
```
- `"proposat"` → escriu `valor_proposat` (el que el modal ja mostrava), `origen='DERIVAT'`.
- `"mantenir"` → NO escriu `base_value_cm`/`origen`; crea NOMÉS la fila de
  `FittingDerivationDecision` (BLOC Q4) amb `decisio='MANTENIR'`.
- `"nou_valor"` → escriu el `valor` que envia el tècnic, `origen='DERIVAT'` (segueix sent
  un valor que el sistema ha proposat com a conseqüència d'una altra mesura, editat a mà —
  no esdevé `FITTED`: ningú no l'ha pres amb el metre).
- Botons ràpids del brief: «Acceptar totes les proposades» envia `decisio:"proposat"` per a
  totes les files de `germanes_afectades`; «Mantenir totes» envia `decisio:"mantenir"` per a
  totes. Cap dels dos calcula res de nou: només omplen el mateix payload.

---

## Notes de mètode d'aquesta diagnosi

- Consultada la BD viva de staging (`postgresql@18-main`, port 5433, schemas `fhort`/`los`)
  amb `SELECT` de només lectura — cap escriptura, cap `migrate_schemas`.
- `git status`/`git log -1` comprovats abans de llegir (branca `dev`, cap commit propi
  d'aquesta sessió — Patró A és read-only absolut, aquest document NO es committa).
- Cap fitxer de codi tocat. Cap comanda que no fos lectura pura.
