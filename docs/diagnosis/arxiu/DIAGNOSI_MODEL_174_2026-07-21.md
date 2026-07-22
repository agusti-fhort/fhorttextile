> ⚠️ SUPERADA 2026-07-21 — implementada de punta a punta pel sprint FIX WIZARD EDICIÓ
> (commits 743b7cc · d28590d · 0251d9f · 2fa51b9 · a7366b1): els nou riscos de la taula final
> i les cinc propostes estan tancats. Consulta només com a històric.

# DIAGNOSI — MODEL 174: el pas 4 del wizard («Graduació») neix cec en edició

> **Data:** 2026-07-21 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
> **Símptoma:** editant el model 174 (Editar model → pas 3 «Talles» → pas 4 «Graduació»), el pas 4
> mostra **«Sistema de talles: —»**, el selector de graduació no respon, i no es pot guardar.
> Reproduït al 174; el model de control 523 (mateix target/construcció/grup) completa el flux.
>
> **Convenció:** tota afirmació porta `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi**
> (verificat per grep, no especulat). Les propostes van marcades `💡 PROPOSTA (a validar)`; les
> decisions són humanes (Patró C).
>
> **Guardes complertes:** cap escriptura de codi, cap commit, cap migració, cap restart · BD només
> `SELECT` · `migrate_schemas --list` no usat · únic fitxer creat: aquest.
>
> **Fora d'abast (aparcat amb nom):** el `.rul` de CALLIE que no va detectar graduacions. Aquesta
> diagnosi **no** investiga el RUL; només confirma que el `PatternFile` no toca el wizard (§B0.5).

---

## RESUM EXECUTIU

1. **NO és un problema de dades del 174.** Els dotze camps que alimenten el wizard són **idèntics**
   als del model de control 523: `garment_type_item=5`, `garment_type=63`, `target=WOMAN`,
   `construction=WOVEN`, `garment_group=7`, `size_system=29`, `size_run_model=XXS·XS·S·M·L`,
   `base_size_label=S`, `grading_rule_set=115`. L'única divergència de configuració és el **client**
   (174 = BRW 7 · 523 = LOS 6). **El model 174 és sa i no s'ha de reparar.**

2. **És un bug d'UI, i té data de naixement: 2026-07-17.** En mode edició el wizard **no rehidrata
   mai** els tres estats del pas 3 (`selSystem`, `selectedSizes`, `baseSize`) — només en desa una
   *còpia de memòria* per detectar canvis (`ModelWizard.jsx:145-146`). Això era latent i inofensiu
   fins que el commit `6f4107f` (17/07, *"pas 4 «Graduació» al ModelWizard (creació + edició)"*) va
   fer que **tot el pas 4 depengués d'aquest estat transitori**.

3. **«Sistema de talles: —» és literal i té una sola font:** `ModelWizard.jsx:549` pinta
   `sizingResult?.size_system_nom || '—'` (em-dash **hardcoded al JSX**, cap clau i18n el conté), i
   `sizingResult` és `null` tret que es compleixin **les tres** condicions alhora (`:86-92`).
   `size_system_nom` surt de `selSystem.nom` (`:91`) — **mai del model**.

4. **El botó no «no respon»: no existeix.** Amb `sizingResult` null, el `RuleSetPicker` **no es
   renderitza** (`:562`, `:582`). I si arribés a muntar-se sense eixos, el propi picker retorna `null`
   **en silenci absolut** (`RuleSetPicker.jsx:34-36`). El botó **Guardar**, a més, queda `disabled`
   per `baseSizeInvalid` (`:615`) — això és el *"no s'ha pogut guardar"*.

5. **Ampliar el run no ho pot arreglar, per disseny de les dependències.** L'efecte que assigna
   `baseSize` té deps **`[selSystem]`** (`:196`): tocar les talles canvia `selectedSizes` però **mai**
   recalcula `baseSize`. Si va quedar `null`, hi continua per sempre. Només un clic manual a un xip de
   talla base (`:528`) ho desbloqueja.

6. **El backend és innocent i D1 no hi té culpa.** Amb els valors reals del 174, **cap** dels tres
   guards nous de `_validar_ruleset_assignable` (`views.py:485-539`) es dispararia: el ruleset 115 té
   **34 regles actives**, `size_system` **29 = 29**, `customer` **7 = 7**. El bloqueig és anterior a
   qualsevol petició HTTP. *(Els commits d'avui sí milloren el missatge d'error del Guardar; no són
   la causa.)*

---

## BLOC B0 — Foto del 174 contra el 523

### B0.1 · `models_app_model`, columnes paral·leles

| Camp | **174** (BRW-FW26-0012) | **523** (LOS-SS27-0249) | |
|---|---|---|---|
| `garment_type_item_id` | **5** | **5** | = |
| `garment_type_id` | **63** | **63** | = |
| `garment_group_id` | **7** | **7** | = |
| `target` | **WOMAN** | **WOMAN** | = |
| `construction` | **WOVEN** | **WOVEN** | = |
| `size_system_id` | **29** | **29** | = |
| `size_run_model` | **XXS·XS·S·M·L** | **XXS·XS·S·M·L** | = |
| `base_size_label` | **S** | **S** | = |
| `grading_rule_set_id` | **115** | **115** | = |
| `fit_type` / `estat` | Regular / Nou | Regular / Nou | = |
| **`customer_id`** | **7 (BRW)** | **6 (LOS)** | ⚠️ **l'única divergència que compta** |
| `nom_prenda` / `collection` | Blusa CALLIE / Feels Christmas | POP / CHERRY POP | ⚠️ |
| `created_at` | 2026-06-10 | 2026-07-19 | ⚠️ |
| `fase_actual` | Dev | Pending | ⚠️ |
| `consumption_started_at` / `reanchored_by_start` | poblat / `t` | NULL / `f` | ⚠️ (no intervé al wizard) |

```sql
set search_path to fhort;
SELECT id, codi_intern, target, construction, size_system_id, grading_rule_set_id,
       size_run_model, base_size_label, customer_id, garment_type_id, garment_type_item_id
FROM models_app_model WHERE id IN (174,523);
```

> **Veredicte B0.1: la primera divergència NO és a `models_app_model`.** Tots els camps que el
> wizard llegeix són idèntics.

### B0.2 · `GarmentTypeItem` — sa i compartit

GTI **5** és el mateix per als dos models: `code='blouse'`, `name='Blusa'`, **`active=t`**,
`garment_type_id=63`, `grading_rule_set_id=115`. `GarmentType 63` = `Buttoned Tops`, **`grup='TOPS'`**,
actiu — coherent amb el "Tops" que mostra la UI. `base_size_definition_id` és **NULL als dos** (no
intervé en aquest camí).

### B0.3 · `SizeFitting`

| | 174 | 523 |
|---|---|---|
| Files | **1** (id 64, `BRW-FW26-0012-SF1`, Proto/Pendent, `base_tancada=f`) | **0** |

El 523 no en té perquè va néixer per import massiu (els models 515-530 en tenen 0). **No correlaciona
amb el símptoma**: el que falla és precisament el que SÍ en té, i el wizard no llegeix `SizeFitting`
en cap punt.

### B0.4 · Els sistemes de talles en joc (el parany)

El pas 3 ofereix **5 sistemes** per a `target=WOMAN` (actius i amb talles), **sense filtrar pel client
del model** i **sense marcar quin és el del model**:

| id | codi | client | talles |
|---|---|---|---|
| **29** | `ALPHA_EU_W` | *(canònic)* | **XXS·XS·S·M·L·XL·XXL·3XL** (8) ← **el del model** |
| 32 | `NUMERIC_EU_W` | *(canònic)* | 34…48 (8) |
| **53** | `WOMAN_BRW_01` | **BRW** | **XXS·XS·S·M·L** (5) ← **el parany del 174** |
| 67 | `WOMAN_LOS_01` | LOS | XS…3XL (7) |
| 68 | `WOMAN_NUM_LOS_01` | LOS | 36…52 (9) |

```sql
SELECT s.id, s.codi, s.customer_codi FROM pom_sizesystem s
JOIN pom_sizesystem_targets st ON st.sizesystem_id = s.id
JOIN pom_target t ON t.id = st.target_id
WHERE t.codi='WOMAN' AND s.actiu
  AND (SELECT count(*) FROM pom_sizedefinition d WHERE d.size_system_id=s.id) > 0;
```

**El run del model és un subconjunt legítim del sistema 29** (`XXS·XS·S·M·L` ⊂ les 8 talles) — triar
un subconjunt és el disseny, **no** una corrupció. De fet **218 models del tenant** tenen un run que
no és el sistema sencer: la forma és normal i massiva. El que és específic del 174 és que aquest
subconjunt **coincideix caràcter a caràcter amb el run sencer del sistema BRW 53**, que el pas 3
mostra amb un distintiu daurat **«Run de client: BRW»** (`ModelWizard.jsx:496-499`).

### B0.5 · `PatternFile` 12 — descartat com a causa

| Camp | Valor |
|---|---|
| id / model_id | 12 / **174** |
| nom_fitxer | `CALLIE-DEC 26 PUR-STYLE-06- 3rd FIT -08-07-2026.dxf` |
| data_pujada | **2026-07-21 17:20:48** |
| `garment_type_item_id` | **NULL** ✔ reconfirmat |

**Refutada la interferència, no assumida:** grep d'escriptures a `backend/fhort/patterns/` sobre
`models_app.Model` i `tasks.GarmentTypeItem` → **cap `.save()/.create()/.update()` a codi de
producció** (només aparicions a `patterns/tests.py`). Pujar el DXF **no ha pogut** tocar cap camp del
wizard. El 523 no té cap `PatternFile`.

---

## BLOC B1 — El camí del wizard, pas 3 → pas 4

### B1.0 · Estructura

Un sol component, 4 blocs inline, **~25 `useState` plans, cap `useReducer`**:

| Element | `ruta:línia` |
|---|---|
| `block` (1..4); entra a 4 si `?block=4` | `ModelWizard.jsx:37` |
| Stepper (permet **saltar** a qualsevol pas un cop resolt el pas 1) | `:356-373` (gate a `:359`) |
| Bloc 3 «Talles» (inline) | `:470-540` |
| Bloc 4 «Graduació» (inline + `RuleSetPicker`) | `:542-596` |
| Footer / Guardar | `:607-620` |

### B1.1 · L'estat del pas 3 i la seva conjunció de tres

```js
const sizingResult = useMemo(() => (
  (selSystem && selectedSizes.length > 0 && baseSize) ? { … } : null
), [selSystem, selectedSizes, baseSize])
```
— `ModelWizard.jsx:86-92`

**Els tres han de ser certs alhora.** `sizingResult` és l'únic pont entre el pas 3 i el pas 4.
**Cap petició HTTP surt en avançar de pas**: tot és estat local fins al Guardar final
(`models.update` + `models.updateStep2`, `:325-332`); «Següent» només fa `setBlock` (`:612`).

### B1.2 · En EDICIÓ, els tres neixen buits — i mai es rehidraten

| Estat | Es prefill en edició? | `ruta:línia` |
|---|---|---|
| `selSystem` | **NO** — autoselecció explícitament exclosa: `if (rows.length && !selSystem && !isEditMode)` | `:180` |
| `selectedSizes` | **NO** — només es pobla dins l'efecte `[selSystem]` | `:191-192` |
| `baseSize` | **NO** — idem | `:195` |
| `modelSizeSystemId` | sí, però **només com a memòria** per comparar | `:145` |
| `modelSizeRun` | sí, però **només com a memòria** (mai reconstrueix `selectedSizes`) | `:146` |

Grep de tots dos flags: apareixen **només** a la declaració, al prefill i dins `systemChanged`
(`:116-117`, `:194`). **NO EXISTEIX** cap línia que reconstrueixi la selecció del pas 3 des del model.
Tampoc hi ha cap validació de "el valor del backend no casa amb cap opció": **simplement no s'intenta
casar**.

> No és una regressió recent: el codi anterior al refactor 5 CAPES ja ho feia, amb el comentari
> explícit *"Pre-selecció només en CREACIÓ (en edició no toquem la selecció ni el guard de talla
> base)"* (`git show 156bca6`, 16/07). Era una decisió raonable **mentre el wizard acabava al pas 3**.

### B1.3 · El pas 4 llegeix un estat que en edició no existeix

| Consumidor del pas 4 | Què fa si `sizingResult` és `null` | `ruta:línia` |
|---|---|---|
| Xip «Sistema de talles» | pinta **`'—'`** (el guió literal del símptoma) | `:549` |
| Missatge d'ajuda | *"Defineix primer les talles (pas 3)…"* | `:558-560` + `i18n/ca.json:936` |
| **Tot el bloc de graduació** | **no es renderitza** (fit, bàner i **`RuleSetPicker`** inclosos) | `:562`, `:582-593` |
| `fitOptions` | `availableFitsStrict(..., sizeSystemId=null)` → **`[]` en silenci** | `:232-236` → `gradingAxes.js:166-168` |
| `strictMatches` | `matchingRuleSetsStrict(..., null)` → **`[]` en silenci** | `:243-247` → `gradingAxes.js:151-153` |
| Autoselecció de ruleset | `if (noGrading || !fit || !sizingResult) return` | `:253-260` |
| `skeletonPayload` | `size_system_id`/`size_run`/`base_size` → **`undefined`** → el backend no toca res | `:272-274` |

**L'eix letal és `sizeSystemId`**: qualsevol dels 5 eixos a null buida la llista sencera, sense llançar
i sense avisar (`gradingAxes.js:153`, `:168`). El segon candidat seria `garmentGroup` (`:200`, de
`garment_type_grup`, `serializers.py:176`) — al 174 està poblat (`TOPS`), per tant descartat.

### B1.4 · Per què «el botó no respon»

| Causa | `ruta:línia` | Feedback visible? |
|---|---|---|
| El wizard no munta el picker (`!sizingResult`) | `:562` | Sí, però **text enganyós**: diu "defineix les talles" quan el que falta és **la talla base** |
| El wizard no munta el picker (`!fit`) | `:581` | **Cap literal**, només l'absència del bloc |
| El picker es desmunta sol si li falta un eix | `RuleSetPicker.jsx:34-36` | **CAP. Silenci absolut**, ni tan sols caixa buida |
| 0 coincidències | `RuleSetPicker.jsx:38-59` | Sí, `grading.no_match` |
| Guardar `disabled` | `:615` + `:119` | Botó gris; l'avís `wizard_base_size_required` (`ca.json:2143`) **només es pinta al pas 3** (`:530-534`) — invisible des del pas 4 |

El handler d'assignar (`RuleSetPicker.jsx:124-135` → `:70` → `ModelWizard.jsx:590`) **no fa cap crida
HTTP, no té `disabled`, no té guard ni try/catch**: només `setGradingRuleSetId(rs.id)`. Per tant, si es
veiés, respondria. **El que la tècnica interpreta com "no respon" és, literalment, "no hi és".**

### B1.5 · L'efecte lateral que ningú ha demanat

```js
setSelectedSizes(labels)                       // les 8 del sistema, no les 5 del model
setBaseSize(changed ? null : (labels[Math.floor(labels.length / 2)] || labels[0] || null))
```
— `ModelWizard.jsx:192-195`

Triar un sistema **substitueix el run del model per TOTES les talles del sistema** i mou la base al
mig. Per al 174 amb el sistema 29: el run passaria de **XXS·XS·S·M·L** a les **8** talles, i la base
de **S** a **L** (`labels[4]`). Avui el guard `baseSizeInvalid` ho impedeix **per accident** quan el
sistema canvia — però **no** quan es retria el mateix sistema 29 (`changed=false`), cas en què el
desat sí passaria i el run triat es perdria en silenci.

### B1.6 · Curses i dependències incompletes (anotades)

- `:170-184` deps `[target, block]`, amb `selSystem`/`isEditMode` llegits dins i fora de deps
  (`eslint-disable` a `:184`) → closure vella possible.
- `:204-221` deps `[block]`, llegeix `gradingRuleSetId` i `fit` fora de deps (`:214`). **Cursa real al
  camí `?block=4`**: `models.get` (`:135`) i el `Promise.all` de rulesets (`:207`) competeixen; si
  l'efecte del bloc 4 corre amb `gradingRuleSetId` encara `null`, el `fit` vigent no es deriva mai i el
  picker no arriba a muntar-se (`:581`).
- `:253-260` l'autoselecció surt si `gradingRuleSetId != null` (`:256`): en edició el ruleset hidratat
  (`:150`) **no es neteja mai** encara que deixi de casar amb els eixos, i `skeletonPayload` (`:266`)
  seguiria enviant l'id antic.
- `:239` `gradingAxes` és un objecte nou cada render → el `useMemo` de `RuleSetPicker.jsx:27-32` mai
  memoïtza (soroll, no bug).
- `:44` `customerCodi` es carrega i **no s'usa enlloc** — estat mort (l'ordenació per client que
  documenta ja no existeix).

---

## BLOC B2 — La diferència amb el cas sa (523)

**Cap camp del model diverteix.** La variable discriminant és **quin `SizeSystem` acaba seleccionat al
pas 3**, perquè d'això depèn `systemChanged` (`:116-117`) i, per tant, si `baseSize` es nul·la:

| | 174 (BRW) | 523 (LOS) |
|---|---|---|
| Existeix un sistema **del seu client** amb el run exacte del model? | **SÍ** — id 53 `WOMAN_BRW_01`, run `XXS·XS·S·M·L`, distintiu daurat «Run de client: BRW» | **NO** — cap sistema LOS amb aquest run |
| Tria natural al pas 3 | el **53** → `53 ≠ 29` → **`changed=true`** → `baseSize=null` | el **29** → `29 = 29` → `changed=false` → base autoassignada |
| Pas 4 | **«—» + cap picker + Guardar disabled** | picker viu → 409 client-creuat → confirma → desa |

**Segon efecte, per si es forcés:** encara que es posés la talla base a mà amb el sistema 53
seleccionat, el matching estricte exigeix `rs.size_system === sizeSystemId` (`gradingAxes.js:160`) i
**el ruleset 115 és del sistema 29**. L'únic ruleset sobre el sistema 53 és el **124 «Prova BRW ALPHA
UE»** (21 regles, sense `garment_type_item` ni `garment_group`). És a dir: **pel camí del sistema 53
no hi ha graduació possible per a aquesta blusa**, i la UI no ho diu — mostra una llista buida.

**El 409 que l'Agus va veure al 523 encaixa i confirma D1:** el ruleset 115 és de BRW (7) i el model
523 és de LOS (6) → tercer guard → 409 `GRADING_CUSTOMER_MISMATCH` (`views.py:527-539`) →
`window.confirm` → reintent amb `confirmar_altre_client` (`ModelWizard.jsx:286-291`, `:326-331`).

> ⚠️ **Punt no observable *a posteriori* (honestedat de mètode):** no es pot reconstruir amb certesa
> **quin sistema es va clicar** a cada sessió, ni l'estat exacte del 523 en el moment d'editar-lo.
> Avui tots dos models mostren el mateix run i la mateixa base. La cadena causal del codi (§B1) és
> certa i verificada; l'atribució de *quina* tria va fer la tècnica a cada cas és inferència a partir
> del context (el distintiu de client del sistema 53). **Una hipòtesi alternativa examinada i
> descartada:** que el 523 se salvés per tenir `size_run_model` buit — la BD mostra que el té poblat
> igual que el 174.

> **Resposta a la pregunta 9 del brief: és ESTAT DEL WIZARD, no dades.**

---

## BLOC B3 — Història recent del 174

| Timestamp (UTC) | Objecte | Fet |
|---|---|---|
| 2026-06-10 08:55:01.015 | Model 174 | creat |
| 2026-06-10 08:55:01.025 | `SizeFitting` 64 | creat pel signal |
| 2026-06-28 07:36:39 | Model 174 | `consumption_started_at` |
| **2026-07-21 17:20:48** | `PatternFile` 12 + 16 `PatternPiece` | pujada del DXF de CALLIE |
| **2026-07-21 18:10:49** | **34 × `ModelGradingRule`** | wipe-and-recreate (`origen=CLIENT_RUN`, `logica=LINEAR`, actius) |
| *2026-07-21 18:13:30* | *(523: 34 MGR)* | *el control, 3 minuts després* |

- **`MeasurementChangeLog`: 0 files** als dos → cap escriptura de mesures a mig fer.
- **`BaseMeasurement`: 0 files** als dos.
- **`GradingVersion` / `GradedSpec`: 0** per al `SizeFitting` 64 → **cap intent de graduació
  materialitzat**, cap estat intermedi. (`fitting_gradingversion` penja de `size_fitting_id`, no de
  `model_id` — `fitting/models.py:62`.)
- **`ModelGradingRule`: 34 als dos**, mateix origen i lògica. **Cap asimetria.**

> **Resposta a la pregunta 10 del brief: NO hi ha cap escriptura parcial.** El 174 va rebre les seves
> 34 regles residents correctament. L'estat a BD és sa.

### B3.1 · La migració `0058` — hipòtesi refutada

`models_app/migrations/0058_alter_modelgradingrule_origen.py` conté **una sola operació**: un
`AlterField` que afegeix el *choice* `CLIENT_RUN` a `ModelGradingRule.origen`. **No afegeix ni altera
cap columna de `models_app_model`**, i `choices` a Django **no toca l'esquema de BD**. Els 68 valors
(34+34) són `CLIENT_RUN` als dos models. **NO EXISTEIX** cap `0058` a `pom/migrations/`.

---

## VEREDICTE

### 1 · Causa arrel de «Sistema de talles: —»

**En mode edició, el wizard no reconstrueix mai la selecció del pas 3 a partir del que el model ja té
desat** (`ModelWizard.jsx:180`, `:191-195`, i l'absència confirmada de qualsevol rehidratació de
`selSystem`/`selectedSizes`/`baseSize`). El pas 4 depèn al 100% de `sizingResult` (`:86-92`), que és
`null` mentre la tècnica no torni a triar sistema **i** talla base a mà. El xip pinta llavors el guió
literal de `:549`.

Al 174 la trampa es tanca perquè, en tornar a triar, l'opció **visualment correcta** (el sistema del
seu client, marcat en daurat) **no és la que el model té desada** → `systemChanged=true` →
`setBaseSize(null)` (`:194-195`) → el pas 4 es queda cec **fins i tot després de passar pel pas 3**.

### 2 · Per què el botó no respon

- **El botó d'assignació no existeix** mentre `sizingResult` sigui `null` (`:562`, `:582`); i el propi
  `RuleSetPicker` es desmunta en silenci si li falta un eix (`RuleSetPicker.jsx:34-36`).
- **El botó Guardar està deshabilitat** per `baseSizeInvalid` (`:615`, `:119`) — guard deliberat.
- **Ampliar el run no ho arregla**: `baseSize` només es reassigna a l'efecte `[selSystem]` (`:196`).
- **L'únic avís que diu la veritat viu al pas 3** (`wizard_base_size_required`, `:530-534`); al pas 4
  només s'hi llegeix "Defineix primer les talles", que **no** explica que el que falta és la base.

### 3 · Dades del 174 o bug de la UI?

> **BUG DE LA UI. Reproduïble en qualsevol model ja poblat que s'editi** — no és un cas aïllat del 174,
> i és **calent per a models futurs**.

- **Combinació mínima:** model amb `size_run_model` no buit i `size_system` no null (qualsevol model
  ja treballat) + edició + entrar al pas 4 sense re-triar sistema **i** talla base. Es dona també
  **saltant pel stepper** (`:359`) o entrant per «Canviar graduació» → `?block=4`
  (`RuleSetCard.jsx:26` + `:37`), camí en què **els sistemes ni tan sols es carreguen** (`:169`).
- **Radi immediat mesurat:** **3 models BRW** amb la forma exacta que fa el parany irresistible
  (`size_system=29` + run `XXS·XS·S·M·L`): **174, 268 i 269**.
- **Radi ampli:** qualsevol model d'un client amb `SizeSystem` propi (avui BRW 1, LOS 2).

**Cap dada del 174 s'ha de reparar.**

---

## TAULA FINAL DE RISCOS

| # | Risc | `ruta:línia` | Gravetat |
|---|---|---|---|
| 1 | **El pas 4 en edició neix cec**: cap rehidratació de `selSystem`/`selectedSizes`/`baseSize` | `ModelWizard.jsx:180,191-195` | **ALTA** — bloqueja editar la graduació de qualsevol model |
| 2 | **El motiu real no arriba al pas 4**: es diu "defineix les talles" quan falta la talla base | `:558-560` vs `:530-534` | **ALTA** — la tècnica no pot deduir què li demanen |
| 3 | **Triar sistema amplia el run a TOTES les talles i mou la base al mig**, en silenci | `:192-195` | **ALTA** — pèrdua del run triat si es desa amb `changed=false` |
| 4 | **Els dos matchers tornen `[]` en silenci** si un eix és null → "cap graduació disponible" amb motiu fals | `gradingAxes.js:153,168` | **MITJANA** |
| 5 | **`RuleSetPicker` es desmunta sense dir res** si li falta un eix | `RuleSetPicker.jsx:34-36` | **MITJANA** |
| 6 | El pas 3 ofereix sistemes **d'altres clients** i **no marca quin és el del model** | `:480-512` | **MITJANA** — indueix l'error exacte del 174 |
| 7 | Entrar per `?block=4` no carrega mai els sistemes; cursa entre `models.get` i la càrrega de rulesets | `:37`, `:169`, `:204-221` | **MITJANA** |
| 8 | El ruleset hidratat en edició no es neteja mai encara que deixi de casar amb els eixos | `:150`, `:253-260`, `:266` | **BAIXA** |
| 9 | `customerCodi` carregat i **no usat enlloc** | `:44` | **BAIXA** — estat mort |

---

## 💡 PROPOSTES (a validar) — no són decisions

1. **Rehidratar el pas 3 en edició** des de `model.size_system` + `size_run_model` + `base_size_label`
   (el serializer ja exposa `size_system_nom`, `serializers.py:183`). Tanca #1, #2 i #7 alhora i
   retorna a `systemChanged` el seu sentit original: avisar d'un canvi **volgut**, no d'un estat mai
   inicialitzat.
2. **Que el pas 4 llegeixi el sistema del model com a fallback** en lloc de pintar `'—'`. La fitxa ja
   ho fa (`ModelSheet.jsx:943`).
3. **No tocar el run en triar sistema** si el model ja en tenia un de vàlid dins aquell sistema (#3).
4. **Marcar visualment quin sistema és el del model** al pas 3, i/o filtrar per client (#6).
5. **Que el picker digui per què no es mostra** en lloc de retornar `null` (#5).

*Cap d'aquestes és una decisió presa. Les decisions són humanes (Patró C).*

---

*Diagnosi Patró A. Cap línia de codi tocada. El `.rul` de CALLIE queda aparcat amb nom, fora d'abast.*
