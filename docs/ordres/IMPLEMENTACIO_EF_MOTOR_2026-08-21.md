# IMPLEMENTACIÓ E+F · MOTOR — STEP SENSE VALORS + MULTI-BREAK PER INTERVALS

**Data:** 2026-08-21 · staging, branca `dev` · **cap push**
**Substrat:** `DIAGNOSI_PRE_SPRINTS_STAGING_2026-08-21.md` §0 i §4 · `DIAGNOSI_BUGS_PROD_837_2026-08-21.md` §E/§F · `VERMELLS_SUITE3_2026-08-21.md`
**Gate:** `ops/qa/banc_paritat_1383.py` (blocs A/B/C) abans de tocar res i després de cada tram.

---

## 0 · EL GATE, ABANS I DESPRÉS

**Baseline v2 (post fix-A / post QA), re-anotada al començar aquesta sessió:**

```
▸ BLOC A · GradedSpec ....... OK=105  DISCREPA=0  ABSENT=0  SOBRER=0
▸ BLOC B · presa/ancoratges . OK=525  DIVERGEIX=0
▸ BLOC C · coherència ....... COHERENTS=4  INCOHERENTS=0
  HASH JOC        096990db404b778a2140fffd8327c54294849b73d42ec67b3265247f9840989f
  HASH RESIDENTS  6e55bc1360630b9e3019c7c2d2265df445adffddef16a4780ae8c9a1f1f8b6b4   ← NOVA referència
  SizeFitting #371 · GradingVersion #131 (v7) vigent
```

> ⚠️ **El hash de residents ha canviat respecte del segell del 21/08 anotat al capçal del banc**
> (`5715f4a2…` → `59b84241…` → **`6e55bc13…`**). No l'ha mogut aquesta sessió: ja hi era abans de
> tocar cap fitxer, i el banc mateix diu que aquest hash canvia legítimament quan algú edita una
> regla del banc (per això és segell, no asserció). El que **no** s'ha mogut ni una vegada és el
> **HASH JOC** ni cap de les 630 cel·les d'A i B.

**Després de CADA tram (F1, F2, F3, F5, E) — idèntic:**

```
A=✔(105) · B=✔(525) · C=✔(4) · HASH JOC 096990db…989f IDÈNTIC · HASH RESIDENTS 6e55bc13…b6b4
VEREDICTE: ✅ PARITAT · joc intacte
```

**Cap cel·la moguda. Cap STOP.**

---

## 1 · TRAM F — MULTI-BREAK PER INTERVALS

### F1 · El model de dades — `breaks`, i per què JSON

Camp nou a **les dues** taules de regla, additiu i NULL:

| Taula | App | Camp |
|---|---|---|
| `pom.GradingRule` | SHARED (`public` **i** tenant) | `breaks = JSONField(null=True)` |
| `models_app.ModelGradingRule` | TENANT | `breaks = JSONField(null=True)` |

Forma: `[{"inici": "M", "final": "3XL", "delta": 3.0}, …]` — llista **ordenada**, etiquetes en
**convenció de MOTOR** (`inici` = primera talla que creix amb el Δ nou), extrems **inclusius**,
delta **entre talles consecutives** (confirmat Montse: `S→L = 3` vol dir S→M 3 **i** M→L 3).

**Per què JSON i no taula filla:** `valors_step` ja és un `JSONField` que travessa el motor, els
dos serializers, l'import, la federació, la fitxa i les sis comandes de sembra sense que mai
hagi calgut res més. Una taula filla hauria volgut **doble migració (SHARED + TENANT)**, nested
writable ×2 i «una llista dins d'una fila» al manifest de federació. La unicitat i l'ordre que la
BD hi posaria els posa `grading_regime.valida_breaks`, que és el punt únic de les quatre portes.

**`MAX_BREAKS = 3`** viu a `backend/fhort/pom/grading_regime.py` i és **constant única**; el
front en té el mirall declarat a `frontend/src/utils/gradingRegime.js` (com ja passa amb
`es_linear_degenerada` ↔ `effectiveRegime`).

**Migracions:** `pom/0077_tram_f_breaks_intervals` · `models_app/0086_tram_f_breaks_intervals`.
**Additives i buides: cap backfill, cap fila tocada** — i **aplicades a staging amb
`migrate_schemas`** (public + tenants) **al mateix tram que el commit** (llei: una migració
aplicada i no commitada és una divergència BD↔repo que cap gate detecta).

> 🚨 **L'off-by-one que aquesta migració NO fa, i és a posta.** L'ordre demanava desplaçar
> l'etiqueta en migrar («la vella marca l'última talla del delta petit»). Això és cert de la
> convenció de DOCUMENT i **fals de la BD**, que ja desa la de MOTOR. Aplicar-hi el desplaçament
> mouria **33 de les 105 cel·les** del banc (contra-experiment de `equiv_intervals_1383.py`).
> Com que aquí no es migra cap fila, el parany queda tancat per construcció — i el test
> `test_L_OFF_BY_ONE_QUE_NO_S_HA_FET` el fixa perquè el dia que algú ho torni a proposar ho vegi.

### F2 · El motor — un sol node, i els dos camins a la mateixa passada

`grading_utils.increment_de_l_aresta` deixa de tenir dos trams i un llindar:

```python
# ABANS
return brk if exterior >= break_idx else ib
# ARA
intervals = intervals_de(rule, run)          # ← el punt únic que decideix quina forma es llegeix
return delta_de_posicio(exterior, intervals, ib)
```

`intervals_de` llegeix **`rule.breaks`** si n'hi ha; si no, el break d'1 tram com **l'interval
`[talla_break_label .. última talla del run]`**. Amb les dues formes informades mana `breaks`.

**El que NO ha canviat:** quin extrem de l'aresta es pregunta. Segueix sent l'**EXTERIOR** (el
més allunyat de la base), que és el que fa que propagar des de qualsevol talla reprodueixi la
mateixa corba.

**Els dos nodes, a la mateixa passada.** `_apply_rule` (Escalat/`GradedSpec`) i
`propaga_ancoratges` (la presa i la derivació de base) **comparteixen aquest node**: tocar-lo un
sol cop és, literalment, tocar-los tots dos. És la lliçó del fix A —allà el fallback al llegat
vivia a dos nodes i el cens només en va veure un— i per això cada cas de test es mesura pels dos
camins, i el bloc B del banc n'és el testimoni sobre dades vives.

**Equivalència, provada i no argumentada:** banc A=105/105 i B=525/525 amb els dos hashos
intactes, més `test_tram_f_intervals.EquivalenciaUnBreakIntervalTest`, que la fixa sobre la
geometria que un banc de dades no pot tenir: run amb forat, break per sota de la base, break
amb `brk=0` (el sostre), etiqueta forana.

### F3 · La validació — punt únic, quatre portes, i el deute LINEAR+0

`grading_regime.valida_breaks(breaks, logica, run, increment_base) → (normalitzats, error)`.
Estricta (autoria) i separada de la lectura del motor, que és **tolerant** (un interval que no es
pot resoldre s'ignora, com avui el break amb etiqueta forana: el motor és una funció pura i no té
canal per dir «aquesta dada és dolenta»).

| Codi | Què tanca |
|---|---|
| `BREAKS_NOMES_LINEAR` | sota STEP el relleu és `valors_step`; sota FIXED/ZERO no n'hi ha |
| `BREAKS_MAX` | més de `MAX_BREAKS` intervals |
| `BREAKS_SENSE_GENERAL` | intervals sense Δ base: no hi ha corba de fons a trencar |
| `BREAKS_TALLA_FORANA` | etiqueta que no és al SizeSystem de la regla |
| `BREAKS_ORDRE` | `inici` després de `final` en ordre de sistema |
| `BREAKS_SOLAPAMENT` | dos intervals que es trepitgen |
| `BREAKS_DELTA_REDUNDANT` | Δ igual al del tram **adjacent** (el general o l'interval enganxat): no trenca res |
| `BREAKS_FORMA` | forma no llegible (no és llista, falta un extrem, Δ no numèric) |

**Les quatre portes** que la criden o que ara jutgen la regla sencera:

| # | Porta | Àncora |
|---|---|---|
| ① | `set_pom_regim_view` (regla resident, pantalla de Graduació) | `models_app/views.py` |
| ② | `gravar_pom_view` (la taula de gènesi) | `models_app/views.py` |
| ③ | `GradingRuleSerializer.validate` (el joc del catàleg, `GradingRuleViewSet`) | `pom/serializers.py` |
| ④ | `update_grading_rule_view` ×2 (`s2_views` i `s4_views`) | poden canviar `logica` i deixar intervals penjats → el guard hi jutja `rule.breaks` |

**+ DEUTE LINEAR+0 (defecte 4 de la diagnosi de PROD, §A.5).** `es_linear_degenerada` ja no fa
curtcircuit amb `te_break`: ara una LINEAR és degenerada quan **cap** delta en joc és diferent de
0 (`increment_base`, `increment_break` i els Δ dels intervals). Amb `ib=0 · brk=0 · break M` —les
cinc regles del 1215 a PROD— la porta ja no la deixa entrar. **El que no canvia:** `ib=0 ·
brk=1.5` (el sostre a l'inrevés) segueix sent LINEAR de ple dret.

> ⚠️ **Cap fila existent s'ha tocat.** És una porta d'autoria. Les 9 regles d'aquesta forma que
> viuen al banc segueixen com són i graduant igual (dades vives, precedent del ruleset 115); el
> que canvia és que no se'n pot escriure cap de nova. L'única conseqüència de segon ordre és que
> `normalitza_logica` —el camí de SEMBRA/IMPORT— les etiquetarà `FIXED` si algun dia es
> re-materialitzen: cap valor graduat canvia (una i altra donen la mateixa taula plana), només
> deixa de dir-se graduada.

### F4 · La UI — el signe `+` i la sub-línia

**Component compartit nou:** `frontend/src/components/grading/EditorIntervals.jsx`
(`BotoAfegirInterval` + `FilesIntervals`), muntat a les **dues** superfícies d'autoria amb la
**mateixa gramàtica**:

| Superfície | On | Gest |
|---|---|---|
| **Generar regles** (joc del catàleg) | `JocsDeRegles.jsx` | `+` a la fila del POM · una `<tr>` filla per interval |
| **Graduació del model** | `GraduacioSuperficie.jsx` | idèntic, i el payload envia la llista SENCERA |

**Per què sub-línia i no columnes:** les dues taules tenen amplades **declarades**
(`EditableTable.AMPLADES`, el `colgroup` de `JocsDeRegles`) i l'escalat les té a 54px. N intervals
no hi caben, i eixamplar-les es menja carril de talles. La fila creix **cap avall**, que és on hi
ha lloc, i les columnes es queden exactament on eren.

**Convenció:** els intervals es pinten i es trien **en convenció de MOTOR, sense volta**
(`inici` = la primera talla que creix amb el Δ nou), amb el rètol i els `title` que ho diuen. La
columna «Talla break» del costat segueix en convenció de **DOCUMENT**: són dues coses diferents a
la mateixa taula i per això la nova porta el seu propi encapçalament. Fer la volta N vegades era
multiplicar per tres el risc que `breakConvention.js:18` ja avisa.

**El run que s'ofereix als pickers és el del SISTEMA** — `taula-mesures` ara serveix
`run_sistema`. Tanca la frontera de §4.4: el motor resol contra el sistema i la pantalla només
sabia oferir el run del model, de manera que un interval acabat a `3XL` (la forma canònica de
tota regla d'1 break llegida com a interval) no era ni triable ni re-desable.

**Compacte** (propagació, escalat, consulta de Mesures): `+2 · S→L +3`, i amb més d'un interval
`S→L +3 +2` amb el relleu sencer al `title` (`etiquetaRegla`, `escalatRuleLeadCols`,
`COLS_GRADING`). Amb intervals, la columna «Δ break» diu `—`: no n'hi ha **un**, i inventar-ne un
de tres seria mentir.

**G5 vigent:** en mode fitting el règim segueix OCULT i l'interval **no hi apareix**.
**Tokens CSS i i18n ca/en/es** (`grading.intervals.*`, `escalat.step_base_copiada*`).

### F5 · La serialització — un camp de forma que ha de viatjar sencer

| Node | Què s'hi ha fet |
|---|---|
| `GradingRuleSerializer` | `breaks` **escrivible** + validació al `validate` |
| Payload `taula-mesures` | `breaks` per fila + `run_sistema` al conjunt |
| `set_pom_regim_view` | entrada i **resposta** (`breaks`) |
| `gravar_pom_view` | entrada per fila |
| `materialize_model_grading_rules` **i** `…_from_specs` | copien `breaks` |
| `rule_to_spec` · `spec_forms_match` · `grading_rules_match` | els intervals entren a la comparació **per FORMA** (`_breaks_equal`) |
| `clone_sizing_profile_view` | **clona els intervals** — el camp s'enumera a mà a posta, perquè un camp nou s'hi hagi de fer veure (és el forat exacte que el fix A hi va trobar) |
| `federation_service` | viatgen al manifest; a l'arribada `row.get('breaks')`, que un paquet emès abans d'aquest tram no en porta |
| `wizard_views` (preview) | `breaks` a la regla resident |

Verificat amb dos testimonis vius: **el clon de perfil conserva els intervals** i
**`grading_rules_match` veu com a diferents dues regles que només difereixen en el relleu**.

---

## 2 · TRAM E — STEP SENSE VALORS

### El comportament (decisió d'Agus)

Una regla STEP que **no té valor per a una talla** ja no fa desaparèixer la fila: la cel·la surt
amb **el valor de la talla base**, **en vermell**, amb l'avís «valors a posar a mà a l'escalat».

```python
# pom/services.py · _apply_rule, branca STEP
total, falta = step_delta_acumulat(rule, size_run, base_idx, size_idx)
if falta is not None:
    _add_warning(...); marques.append({...})
    return base_val, 'STEP'
```

**Per què això no contradiu la llei D2** (i queda escrit al codi): D2 existeix perquè el motor no
**fabriqui** una corba que sembli graduació —el FIXED inventat del model 163, 225 specs a delta 0
tornant 200 OK—. Aquí la corba **no se sap dir i es diu que no se sap**: la fila apareix, el valor
és reconeixible com a prestat, la cel·la va marcada i el POM entra a una llista de treball. El
silenci d'abans era pitjor: la fila desapareixia sencera i el senyal vivia només al log.

### La marca es DERIVA, no s'emmagatzema

`GradedSpec` és sortida pura i **no té camp d'origen** — la llei no es toca i **no hi ha cap camp
nou**. La marca és una propietat de la **regla** (`logica='STEP'` i `valors_step` que no cobreix
el camí fins a aquella talla) i es deriva **al lector**: l'alternativa de menys radi de les quatre
censades (§4.6 (c)).

🔑 **I es deriva al BACKEND, no al front.** El predicat ha de ser EXACTAMENT el del motor, i el
del motor és `grading_utils.step_delta_acumulat` — la mateixa funció que decideix què s'emet és la
que diu què es pinta. Amb un mirall a JavaScript, la cel·la vermella i la cel·la copiada podrien
deixar de ser la mateixa el dia que una de les dues canviés, i el cas on això passaria és
justament el freqüent: quan la talla que falta al camí és una que el model no fabrica.

| Superfície | Com hi arriba |
|---|---|
| **Escalat** (`PropagatedEditor` → `MeasureGrid`) | `taula-mesures.rows[].step_base_copiada` → `buildEscalatRows` → `cellaEscalat({baseCopiada})` → cel·la amb `--err`/`--err-bg` i el `title` de l'avís |
| **Size set / presa** | la mateixa graella i la mateixa fila: la presa neix de l'spec i **hereta l'estat** |
| **Propagació** | `generate_grading_view` retorna `step_base_copiada: [{pom_id, pom_codi, talles}]` i `ModelSheet` el pinta com a **llista de treball manual** (POM × talles), no com un avís genèric |

**Efecte col·lateral volgut i censat:** `preview_graded_specs` (el preview del wizard d'import)
comparteix `_apply_rule`, o sigui que **la previsualització ensenya el mateix** que després
propagarà — que és exactament el que ha de fer un preview. Cap altre camí en depèn.

Canal nou i opcional al motor: `generate_graded_specs(sf_id, informe=None)` — mateix patró que
`warnings` (un canal que el cridador obre si el vol). El valor de retorn no canvia.

### ✅ LA PORTA D'EDICIÓ DEL VALOR VERMELL — CENS, PROPOSTA I **CONSTRUÏDA** (OK d'Agus, 21/08)

L'ordre demana censar les dues formes i **proposar amb el cens al davant**. Aquí són, i el cens
canta un fet que decideix mig assumpte.

| | **(a) escriure `valors_step` de la regla resident** | **(b) `ModelGradingOverride` per cel·la** |
|---|---|---|
| Mecanisme | la cel·la editada calcula el Δ respecte del veí cap a la base i el desa a `ModelGradingRule.valors_step` | ja existeix: `set_size_override_view` (`POST /models/<id>/set-size-override/`), escriu l'override i re-propaga |
| Qui guanya al motor | la regla (branca STEP) | l'override, que té **precedència màxima** (override → regla) |
| La marca | **desapareix sola**: la regla ja té valor per a aquella talla, i la marca és derivada d'això | **es queda vermella per sempre**, perquè la regla segueix sense valor — caldria fer que la derivació també mirés els overrides |
| Traçabilitat | `origen='MANUAL'` a la regla | `motiu` + `created_by` per cel·la (`MeasurementChangeLog`) |
| Viatja? | sí: materialització, clon, federació, fitxa | no: és patrimoni de cel·la del model |
| 🚨 **Supervivència a la propagació següent** | **sobreviu** (és la regla) | **ES DESTRUEIX**: propagar amb `new_version=True` fa `ModelGradingOverride.objects.filter(model=model).delete()` — el «llenç net» és llei, i s'enduria tots els valors posats a mà |
| Preu | el Δ d'una talla es defineix **respecte del veí**: editar una cel·la vol dir escriure una CADENA de deltes (o completar les talles del camí), no un número solt | cap: és una xifra absoluta per cel·la |

**PROPOSTA I DECISIÓ:** **(a)**. L'Agus la va confirmar el 21/08 i està **construïda**:
`POST /models/<id>/pom/<pom_id>/step-valor/` `{talla, valor, capa?, instancia?, garment?}`.
La (b) és més barata i ja existia, però amb la llei del llenç net és una trampa: el tècnic
escriuria 20 xifres i el primer «Propagar» conscient se les enduria totes sense dir res.

**Com ha quedat, i el detall que la fa delicada.** `valors_step` no desa valors: desa **passos
entre veïns** acumulats cap enfora. Per tant «la M mesura 103» és `delta[M] = 103 − valor del veí
cap a la base`, i el veí ha de ser CALCULABLE. Quan el camí té forats, la porta **rebutja
nomenant la talla que s'ha d'omplir primer** (`STEP_CAMI_INCOMPLET`, amb `talla_que_falta`):
omplir-los amb un zero seria fabricar la corba plana que la llei D2 prohibeix, i fer-ho en
silenci seria pitjor. La conseqüència pràctica és que la feina es fa **de la base cap enfora**,
que és l'ordre en què els deltes volen dir alguna cosa.

| Node | On |
|---|---|
| Validació (punt únic) | `grading_regime.valida_valor_step` — només STEP · la base no · talla del run · valor numèric (el 0 hi és legítim) |
| Camí | `grading_utils.step_delta_acumulat`, el MATEIX predicat del motor i de la marca |
| Escriptura | `valors_step` de la `ModelGradingRule` + `origen='MANUAL'`, i **re-propaga in place** (com feia la porta d'override): sense això la marca cauria i la xifra seguiria sent la prestada |
| UI | la columna **«Mesura»** de l'Escalat, que és on la xifra prestada viu: un llapis obre la cel·la (Enter desa, Escape plega) i l'error del servidor arriba al mateix control. **Opt-in** a `buildEscalatRows({onDesaValorRegla})`: qui no la passa té la cel·la en lectura |
| Proves | 7 al mòdul de regressió (cicle sencer · camí incomplet que no escriu res · cadena amunt i avall · quatre portes tancades) + el bloc propi de `qa_tram_ef_staging.py` |

**L'override no es jubila**: es queda per al seu ús propi —la decisió puntual per talla que el
llenç net ha d'esborrar per disseny—. Dues intencions, dues portes.

---

## 3 · QA

| Prova | Com | Resultat |
|---|---|---|
| **Banc de paritat** (3 blocs) | `ops/qa/banc_paritat_1383.py`, abans i després de cada tram | ✅ A=105 · B=525 · C=4 · hashos intactes |
| **QA sobre STAGING**, model de prova **NO-banc** | `ops/qa/qa_tram_ef_staging.py` — `QA-TRAMF-0001` (pk **1384**) amb **dos POMs**: `A` amb interval (tram F) i `B` amb STEP sense valors (tram E). Tot per les portes reals i el motor real | ✅ **22/22** · cas Montse `XS 98 · S 100 · M 103 · L 106 · XL 108` · porta del valor vermell · payload Q8b de 1384 i 1383 |
| **Les cinc portes** (solapament · ordre · talla forana · Δ redundant · LINEAR+0 amb break) | el mateix script, per la porta `set_pom_regim_view` | ✅ 400 amb el `codi` exacte, les cinc |
| **STEP sense valors** | el mateix script | ✅ totes les talles amb el valor base · llista `[{pom_codi: 'A', talles: [XS, M, L, XL]}]` a la propagació · marca derivada per fila a `taula-mesures` |
| **Regressió pròpia** | `fhort.pom.test_tram_f_intervals` (nou) — equivalència pels dos camins, semàntica dels intervals, les 8 validacions, el deute LINEAR+0, la porta HTTP i el viatge del camp | ✅ |
| **Mòduls tocats** | 49 mòduls de grading/motor/federació/`models_app` · **502 proves** | ✅ després de §3.1 |
| **Front** | `npx eslint src` sobre els fitxers tocats · `node --test` (breakConvention, gradingRegime, cellaEscalat) · `npm run build` | ✅ 0 errors · 27 proves verdes · build net |

### 3.1 · ELS 5 VERMELLS DE LA PRIMERA CORREGUDA — qui mentia

`Ran 502 tests · FAILED (failures=2, errors=3)`. **Regla d'or: primer decidir qui ment.** Cap
test s'ha afluixat per passar.

**① ×3 ERRORS · `test_set2_t3_sembra_per_garment` — MENTIA EL CODI, i era un defecte de veritat.**

```
AttributeError: 'types.SimpleNamespace' object has no attribute 'breaks'
  → models_app/services.py  ·  materialize_model_grading_rules
```

`materialize_model_grading_rules` rep regles **NO DESADES** (specs convertits a objecte) —ho diu
el seu propi codi tres línies més avall, on `rule_set_id` es llegeix amb `getattr` **per aquest
mateix motiu**— i jo hi havia posat `r.breaks` amb accés directe. És exactament el mode de
fallada que el comentari del costat avisava, i el camí que trencava no és cap cas de laboratori:
és la sembra des d'specs (import i conflictes resolts). **Fix al CODI**, no al test:
`getattr(r, 'breaks', None)` a les dues crides, amb la nota al costat.

**② ×2 FAILURES · el contracte STEP que el TRAM E RETIRA — mentien els tests, i es diu.**

`test_propaga.test_r3_step_sense_valors_step` i
`test_espai_de_sistema.test_step_necessita_el_delta_de_la_talla_TRAVESSADA` asserien
`val is None` (cel·la absent). **És el contracte que la decisió d'Agus retira**: ara la cel·la
porta el valor de la talla base, marcat. Els dos tests s'actualitzen **dient-ho a la capçalera**
i, sobretot, **conservant el que protegien de debò**: que el motor **no inventa cap delta** (52 i
106.0 segueixen sent els números prohibits) i que el warning segueix nomenant la talla que falta.
El segon hi guanya una asserció nova: la cel·la queda **apuntada** a `marques`, que és el que la
converteix en feina i no en silenci.

> 🔑 Per què la STEP sí i la LINEAR-sense-Δ no (la pregunta que això obre): una columna plana
> LINEAR es presentava **com a graduació** i ningú no ho podia veure; una cel·la STEP prestada és
> **reconeixible** (és el valor de la base), va **marcada** i entra en una **llista**. La llei D2
> prohibeix fabricar, no prohibeix dir «això encara no ho sé».

**Segona correguda** (14 mòduls: els 3 tocats pels vermells + 10 de control + el nou):
`Ran 165 tests` amb els **13 mòduls existents en VERD** —el fix del `getattr` i els dos
contractes actualitzats confirmats— i els únics vermells dins del mòdul NOU: tres de fixture
(`GradingRule.talla_base` és FK NOT NULL i `SizingProfile` vol els quatre eixos: **mentia la
fixture**, i el que ho canta és una restricció de domini real) i **una asserció meva
equivocada** —`XL` és a TRES arestes de la base i esperava 104 on el motor deia 106—. Corregits
els quatre i re-llançat el mòdul.

🚩 **QA de navegador PENDENT**: l'agent no pot emetre el JWT de staging (bloqueig conegut,
`ftt-qa-token-jwt-bloquejat`). Tot el que es podia mesurar sense navegador s'ha mesurat pel camí
de la vista real (`APIRequestFactory` + `force_authenticate` sobre la BD viva d'staging), que
travessa la porta sencera menys nginx. **El model `QA-TRAMF-0001` (pk 1384) es deixa VIU a
staging expressament**, perquè la QA de pantalla es pugui fer sobre ell sense tocar el banc
(`--neteja` l'esborra quan sobri).

---

## 4 · EL QUE NO S'HA TOCAT (i per què)

- ✅ **`TechSheetEditor.jsx` · Q8b — FET** (seguiment tancat el 21/08, ordre d'Agus). La taula
  d'Escalat de la fitxa diu els intervals amb les **tres columnes que ja hi havia**: `Δ` porta el
  general, `Break` el Δ del tram i `B.Size` el tram (`S→L`), que llegides juntes són la frase
  «+2,0 · S→L +3,0». Cap columna nova i cap mil·límetre de més — l'ample es reparteix en bandes
  per no passar l'A4 (**mai A3**) i cada mil·límetre és una talla que deixa de cabre. Amb més
  d'un interval hi cap el primer i un `+N`; la corba sencera hi és igualment a les columnes de
  talla. Qui decideix quina de les dues formes parla és **`resumBreakQ8`** (una funció, amb banc
  propi): break d'1 tram → convenció de DOCUMENT; intervals → convenció de MOTOR i **sense
  volta**. QA sobre **1384** (interval) i **1383** (21 files de break d'1 tram, intactes).
- **`CheckMeasureEditor.jsx`** — mostra el relleu compacte (ja hi arriba per `etiquetaRegla`) però
  **no edita intervals**. No perd res: el seu desat va per presència de clau i no toca `breaks`.
  🚩 seguiment si es vol paritat d'autoria a la tercera superfície.
- **`SizeSetDetail.jsx`** i **l'export CSV de `s8_views`** — segueixen sense dir el relleu (ja no
  el deien abans: §1.6·#5 i §1.5·#13 de la diagnosi). Fora d'abast, anotat.
- **`talla_break_pos`** — segueix sent columna morta i divergent (defecte 5). Els intervals **no
  en tenen cap equivalent i no se n'ha fabricat cap**: la posició es resol per etiqueta contra el
  run del sistema, que és el que fa el motor.
- **L'import / `size_map_views`** — escriu regles d'1 break i segueix fent-ho. No cal tocar-lo:
  el motor llegeix aquella forma exactament igual que abans.
- **Cap fila migrada, a cap tenant.** Les dues formes conviuen i el punt únic que decideix quina
  es llegeix és `intervals_de`.
- **`increment` (llegat)** — mort des del fix A; aquest tram no el ressuscita enlloc.
- **`DECISIONS.md`** — no s'hi ha escrit res. La diagnosi ja avisava que **la decisió MULTI-BREAK
  v2 no hi és** (§12 de les contradiccions) i segueix sense ser-hi: `DECISIONS.md` no es commita
  (llei §1) i en aquest moment el toca una altra sessió. 🚩 **La llei d'aquest tram viu, escrita,
  a tres llocs versionats**: el docstring del camp `breaks` (`pom/models.py`), el de
  `grading_utils.intervals_de` i aquest document. Si l'Agus vol el resum a `DECISIONS.md`, és
  una baixada de text, no una decisió nova.

---

## 5 · COMMITS (locals, `dev`, **cap push**)

| Commit | Concern |
|---|---|
| `c07e0b6a` | **F1** · el camp `breaks` a les dues taules + les dues migracions additives |
| `c07b1d5a` | **F2** · el motor llegeix intervals (un node, els dos camins) |
| `a4d179eb` | **F3+F5** · la porta (`valida_breaks` × 4 + el deute LINEAR+0) i el viatge del camp · `test_tram_f_intervals` (39 proves) |
| `196887d1` | **F4** · UI: `EditorIntervals` a les dues superfícies, compacte, mirall del règim, i18n ca/en/es + els dos bancs de `node --test` |
| `8eb701e7` | **E** · motor: valor de la base copiat + `informe` + marca derivada al payload; dos contractes de test retirats amb acta |
| `6bd405d7` | **E/UI** · el vermell de la cel·la prestada i la llista de treball manual a «Propagar» |
| `eac1a92b` | l'acta (aquest document) + `ops/qa/qa_tram_ef_staging.py` |

**Segona tanda (OK d'Agus sobre el cens · 21/08):**

| Commit | Concern |
|---|---|
| `bbbc05e6` | **E/porta** · `step-valor/` escriu `valors_step` de la regla resident (mai un override) + validació al punt únic + 7 proves |
| `03cd6a59` | **E/porta UI** · la cel·la prestada s'edita a la columna «Mesura», opt-in a l'adaptador; i el vermell de la cel·la activa s'acota al fantasma |
| `7268138d` | **Q8b** · la fitxa diu els intervals amb les tres columnes que ja hi havia (`resumBreakQ8`, amb banc) |
| `361a1ffd` + `8aa25afa` | **CENS_PODA_PLATAFORMA** surt del commit de codi i entra sol (v. sota) |
| *(aquest)* | l'acta al dia + la QA d'staging ampliada |

**Per què el cens de poda es parteix amb DOS commits i no amb un rebase:** `b0066c3c` té 42
commits a sobre i `dev` la comparteixen diverses sessions alhora — reescriure-hi la història els
trencaria la feina a totes. El resultat a l'arbre és idèntic (md5 comprovat) i el fitxer ja té
commit propi i missatge propi.

**F3 i F5 van al mateix commit a posta:** són el mateix concern dit dues vegades —«la forma nova
entra» i «la forma nova viatja»— i comparteixen fitxer (`views.py`, `serializers.py`,
`s2_views.py`). El tall que sí que s'ha respectat, i que és el que importa per llegir-ho demà, és
**TRAM F ↔ TRAM E**: cap commit els barreja, ni al backend ni al front.

**Migracions aplicades a staging** (`migrate_schemas`, public + tenants) **al mateix tram del seu
commit**.

🚩 **La suite SENCERA és el gate pre-push i no s'ha re-llançat aquí** (llei de l'ordre). El que
s'ha corregut són els 49 mòduls que toquen grading, motor, federació i `models_app`.
