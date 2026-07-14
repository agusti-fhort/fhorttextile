# DIAGNOSI — G6 · CAMINS DUALS DEL GRADING (+ deute `test_regim_sense_fallback_400`)

> **Data:** 2026-07-13 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev` (HEAD `fdb418c`)
> **Abast:** cens complet dels camins duals de G6 — prerequisit per **generalitzar** la projecció del
> motor de patrons, avui pinçada per un `grading_version_id` explícit. Més el veredicte del deute
> `fitting.PropagarActionTest.test_regim_sense_fallback_400`.
>
> **Convenció:** tota afirmació porta `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi**
> (verificat, no especulat). Les xifres venen de `SELECT` reals sobre staging (schema `fhort`).
> Les propostes van marcades `💡 PROPOSTA (a validar)` i **no** són decisions (Patró C).
>
> **Guardes:** cap escriptura de codi, cap migració, cap restart, cap fixture. BD només `SELECT`.
> Únic fitxer creat: aquest.

---

## RESUM EXECUTIU

1. **La projecció del motor NO es pot despinçar avui — i el bloqueig no és el que semblava.** El
   `grading_version_id` explícit segueix esquivant tots els forks de *selecció* (com deia la S0),
   però hem trobat un forat més profund: **el segell menteix**. El guard de segellat
   (`pom/services.py:561-569`) només protegeix **crear v+1**; **no protegeix escriure dins la versió
   activa**. `_get_or_create_grading_version` (`pom/services.py:496-506`) filtra **`is_active=True`
   i prou — no mira `aprovada`**. Sis endpoints routed reescriuen `GradedSpec` in-place sobre una
   versió `aprovada=True`. **El cas és viu avui: gv 67 (model 182) és activa I aprovada.** El motor
   confia en `gv.aprovada` (`patterns/engine/grading_projection.py:164`) → **el flag pot ser cert
   mentre el contingut ha canviat després del segell.**

2. **BUG VIU, no teòric: el fork 4 serveix una versió desactivada.** `pom/s6_views.py:137-139`
   ordena per `('-data','-id')` **ignorant `is_active`**. Per al SizeFitting 52 (model **162**, el
   golden case) serveix **gv 42 = v5, `is_active=false`**, mentre tota la resta del sistema serveix
   **gv 32 = v3, l'activa**. **Dues superfícies de la UI mostren talles diferents del mateix model,
   avui.** És una línia.

3. **Dos duals són fantasmes: es poden matar gratis.** `GradingException` (`pom/models.py:649`) té
   **0 files** i **CAP escriptor a l'aplicació** (ni API, ni UI, ni serializer — només scripts
   d'import/seed). `ModelGradingOverride` (`models_app/models.py:651`) té **0 files** i és efímer per
   disseny (dos esborradors el buiden a cada propagació). El fork de precedència
   (`pom/services.py:92-108`) té, doncs, **dues de les seves tres branques mortes sobre dades vives**.

4. **El propietari real del grading és `Model.grading_rule_set`, i només ell.** `SizingProfile` és un
   **catàleg de tria** (el wizard en copia l'id i el vincle es perd) i
   `GarmentTypeItem.grading_rule_set` és una **fulla morta aigües avall**: s'escriu, es mostra, es
   valida — i **cap codi el propaga al Model** (`models_app/views.py:428-431` agafa el ruleset del
   payload, no de l'item). 1/57 items poblats.

5. **El gate dur mira el punter, no les regles — i ja hi ha una víctima.** `pom/services.py:42-43`
   llança `ValueError` si `model.grading_rule_set_id` és NULL, **abans** que `_load_grading_rules`
   (`:425`) comprovi si el model té regles residents. **Model 163 té 25 `ModelGradingRule` actives i
   `grading_rule_set = NULL` → no pot graduar mai** (i, coherentment, té 0 `GradedSpec`). El gate
   exigeix un punter que el motor ja no necessita per llegir les regles.

6. **PART 2 — Veredicte (B): el test és ESTAL. El 200 és legítim. NO cal fix abans del deploy.** El
   guard del 400 es va treure **a consciència** al commit `407d8af` (2026-06-23, Sprint *SOBIRANIA DE
   LA REGLA*, P3), que va reescriure la view i **no va tocar el test**. La decisió està escrita a
   `DECISIONS.md:280-294`. El deute és **d'un sol fitxer de test**.

---

## B1 — QUI MANA SOBRE EL RULESET (la propietat)

### B1.1 · Els tres FK cap a `GradingRuleSet`

| Camp | `fitxer:línia` | on_delete | null | Rol real |
|---|---|---|---|---|
| `SizingProfile.grading_rule_set` | `pom/models.py:856-857` | PROTECT | **no** | catàleg de **tria** |
| `GarmentTypeItem.grading_rule_set` | `tasks/models.py:319-324` | PROTECT | sí | **fulla morta** |
| `Model.grading_rule_set` | `models_app/models.py:193-199` | SET_NULL | sí | **el que alimenta el motor** |

**FET — només `Model.grading_rule_set` entra al motor.** `pom/services.py:33-37` fa
`select_related('model__grading_rule_set')` i `:42-43` avorta si és NULL. **`SizingProfile` i
`GarmentTypeItem` NO apareixen enlloc de `pom/services.py`** (verificat).

**FET — `GarmentTypeItem.grading_rule_set` no es propaga.** `_resolve_garment_def`
(`models_app/views.py:396-434`), l'únic resolutor de creació/edició d'esquelet, deriva `garment_type`
i `garment_group` de l'item (`:409-415`) però **agafa el ruleset exclusivament del payload**
(`:428-431`). **NO EXISTEIX** cap codi item→model per al ruleset.

**FET — `SizingProfile` és lookup, no propietat.** El ModelWizard en copia l'id
(`frontend/src/pages/ModelWizard.jsx:75`) i després el perfil no torna a intervenir mai. **NO EXISTEIX
cap FK `Model → SizingProfile`.**

### B1.2 · Dades reals

```sql
SELECT 'models_app_model' t, count(*) total, count(grading_rule_set_id) ple FROM models_app_model
UNION ALL SELECT 'tasks_garmenttypeitem', count(*), count(grading_rule_set_id) FROM tasks_garmenttypeitem
UNION ALL SELECT 'pom_sizingprofile', count(*), count(grading_rule_set_id) FROM pom_sizingprofile;
```
| taula | total | FK ple |
|---|---|---|
| `models_app_model` | 20 | **5** |
| `tasks_garmenttypeitem` | 57 | **1** |
| `pom_sizingprofile` | 26 | 26 |

Creuant els 20 models amb el seu item: **0 discrepàncies, 4 models amb ruleset i item buit, 1 sol cas
on tots dos el tenen** (model 185 · item 4 · rs 84) — i **coincideix per casualitat de dades, no per
codi** (no hi ha propagació). El model 186 apunta a rs=107 (`Importació fitxa`), **que no és a cap
`SizingProfile`** → prova que el camí d'import crea rulesets fora de la capa de perfils.

### B1.3 · `GradingRuleSet.target` — el FK legacy (mig-mort i **divergent**)

`pom/models.py:559-570` — el FK `target` conviu amb una M2M `targets` que el propi codi declara
**autoritativa**; el comentari diu que el FK «will be removed in a later sprint». **NO EXISTEIX cap
`RunPython` que copiï `target` → `targets`.**

- **Únic lector amb efecte de negoci:** el filtre anti-proliferació 1D de `derive_grading_rule_set`
  (`pom/grading_utils.py:311-319`) — encara decideix **si es reutilitza o es crea un ruleset nou**.
- **El deute ja està escrit al codi:** `pom/grading_utils.py:92-95` avisa que `cerca_canonic_equivalent`
  va per la M2M mentre l'anti-proliferació va pel FK legacy, «si un canònic té el target a la M2M però
  no al FK (o viceversa) divergiran».
- **El clon perpetua la divergència:** `pom/s2_views.py:195` copia el FK i **NO copia la M2M**.
- **NO és escrivible per API:** `GradingRuleSetSerializer` (`pom/serializers.py:201-213`) exposa
  `targets` (M2M) però **NO `target`**.

**Dades:** 25 rule sets · FK ple 24 · **1 fila amb FK i CAP M2M** (id 98, el cas que el deute anuncia) ·
1 sense cap dels dos · **4 amb M2M múltiple que el FK no pot representar**.

> **Veredicte B1:** el ruleset té **un sol propietari real** (`Model`). Les altres dues vies són
> catàleg i fulla morta. El FK `target` **no és mort** (1 lector viu) però ja **divergeix** de la M2M.

---

## B2 — ELS FORKS D'ESCRIPTURA DEL MOTOR

### B2.1 · Precedència (`pom/services.py:92-108`) — **2 de 3 branques mortes**

`override` (ModelGradingOverride) > `exc` (GradingException) > `rule is None` → FIXED > `_apply_rule`.
Duplicat literal, sense persistència, al preview (`pom/services.py:175-186`).

| Dual | Model | Escriptors REALS | Files (BD) | Veredicte |
|---|---|---|---|---|
| `GradingException` | `pom/models.py:649` | **CAP a l'aplicació.** NO EXISTEIX viewset, serializer ni URL (verificat a `pom/views.py`, `pom/serializers.py`, `pom/urls.py`); **zero hits als dos frontends**. Només `data/import_master.py:310`, `bootstrap_tenant.py:79` | **0** | **MORT DE FACTO** |
| `ModelGradingOverride` | `models_app/models.py:651` | `escalat_ajustar_talla_view` (`models_app/views.py:1875`, **viu a la UI**) — però només a la branca no-LINEAR; i `set_size_override_view` (`:1730`), **endpoint orfe** (client a `endpoints.js:65-66`, **zero cridadors**) | **0** | **VIU PERÒ EFÍMER** — dos esborradors el buiden a cada propagació (`views.py:1570` "LLENÇ NET" i `:1864`) |

El docstring de `ModelGradingOverride` (`models_app/models.py:653-657`) **declara explícitament** que
existeix per substituir `GradingException` («UNLIKE pom.GradingException, which lives on the shared
GradingRuleSet (a template) and **would leak to every model** using that set»). La substitució està
feta; **el mort no s'ha enterrat**.

### B2.2 · `ModelGradingRule` vs `GradingRule` — el quart fork, **tot-o-res**

`_load_grading_rules` (`pom/services.py:425-446`):

```python
rules = ModelGradingRule.objects.filter(model_id=model.id, actiu=True)
if rules.exists():
    return {r.pom_id: r for r in rules}          # ← NIVELL 1: resident. El ruleset queda IGNORAT SENCER
if model.grading_rule_set_id:
    return {... GradingRule.objects.filter(rule_set_id=..., actiu=True) ...}   # ← NIVELL 2: camí vell
return {}                                        # ← cap regla → tot FIXED
```

**FET — la semàntica és tot-o-res per model, no merge per POM.** N'hi ha prou amb **UNA**
`ModelGradingRule` activa perquè el catàleg extern quedi completament ignorat.

**Quina branca està viva (LA XIFRA CLAU):**

| model | ruleset | MGR actives | GradingRule al ruleset | branca del motor |
|---|---|---|---|---|
| 162 | 75 | 0 | 61 | **GradingRule (ruleset)** — l'únic |
| 163 | **NULL** | **25** | 0 | *(no pot graduar — v. B2.3)* |
| 182 | 75 | 62 | 61 | MGR (resident) |
| 185 | 84 | 35 | 35 | MGR (resident) |
| 186 | 107 | 20 | 20 | MGR (resident) |
| 188 | 79 | 49 | 40 | MGR (resident) |
| 14 models | — | 0 | 0 | cap regla → tot FIXED |

**Els 707 `GradingRule` repartits en 24 rule sets alimenten el motor per a EXACTAMENT 1 model** (162).
La seva funció real avui és ser **la llavor** de `materialize_model_grading_rules`
(`models_app/services.py:114-135`), no l'entrada de càlcul.

Les 191 MGR per origen: `CANONICAL/LINEAR` 110 · `MANUAL/LINEAR` 47 · `CANONICAL/FIXED` 24 ·
`MANUAL/FIXED` 9 · `MANUAL/STEP` 1. *(Nota: `origen` **està poblat**; una hipòtesi contrària va ser
descartada en verificació.)*

**Asimetria a retenir:** les **excepcions es llegeixen SEMPRE del ruleset extern**
(`pom/services.py:64`, `_load_grading_exceptions(model.grading_rule_set_id)`) **encara que les regles
vinguin de `ModelGradingRule`**. Els dos rellotges conviuen dins la mateixa passada.

### B2.3 · La víctima del gate dur (model 163)

`pom/services.py:42-43` llança `ValueError` si `not model.grading_rule_set_id` — **abans** que `:63`
cridi `_load_grading_rules`. **Model 163 (`BRW-FW26-0001`): 25 MGR actives (origen MANUAL),
`grading_rule_set_id = NULL` → `ValueError` garantit.** Verificat: el model **no té cap `GradedSpec`**.
Un model completament equipat amb la branca guanyadora **no pot graduar** perquè li falta un punter que
el fork ja no fa servir per llegir les regles.

### B2.4 · La petja congelada (`grading_type_applied`)

Valors: `LINEAR|STEP|FIXED|ZERO|EXCEPTION` (`fitting/models.py:165-171`). **`EXCEPTION` és ambigu per
disseny:** override i exception hi deixen **la mateixa petja** (`pom/services.py:97` i `:100`) → la fila
**no distingeix quin fork va guanyar**.

| `grading_type_applied` | totes les versions | **només versions `is_active`** |
|---|---|---|
| LINEAR | 445 | **128** |
| FIXED | 338 | **70** |
| EXCEPTION | 17 | **0** |
| STEP | 1 | **0** |
| ZERO | **0** | 0 |

**Sobre dades vives no hi ha ni una sola fila `EXCEPTION`.** Les 17 viuen totes en versions superades —
arqueologia d'overrides que el "LLENÇ NET" va esborrar després.

> **Veredicte B2:** el fork de precedència té **dues branques mortes sobre dades vives**. El quart fork
> (MGR vs GR) és **el viu i el guanyador**, però és **tot-o-res** i el gate dur el contradiu.

---

## B3 — ELS 7 FORKS DE LECTURA (verificació de la S0 §B7.5)

**Cap ha mort. 6/7 vius (5 moguts de línia), 1 mal classificat. I n'hi ha 3 de nous.**

| # | Fork | Línia AVUI | Estat |
|---|---|---|---|
| 1 | `vigent_grading_version(sf)` — `is_active` + desempat `-version_number` | `fitting/services.py:557-580` | **VIU** (mogut). El fallback no s'exerceix avui |
| 2 | `_active_grading_version(sf)` — estrictament `is_active=True` | `fitting/services.py:546-555` | **VIU** (mogut) |
| 3 | `.last()` sobre `is_active` | `pom/services.py:496-506` · `pom/grading_views.py:68-73` | **VIU**. `Meta.ordering=['size_fitting','-data']` (`fitting/models.py:92`) → **`.last()` retorna la MÉS ANTIGA** entre les actives. Latent (0 SF amb 2+ actives) |
| 4 | `order_by('-data','-id').first()` **ignorant `is_active`** | `pom/s6_views.py:137-139` | **🔴 VIU I DISPARANT — v. B3.1** |
| 5 | Serializer sense filtre de versió | `fitting/serializers.py:216-224` | **VIU però la S0 el va classificar malament** — v. B3.2 |
| 6 | `_resolve_working_size_fitting(model)` | `fitting/services.py:534-543` | **VIU i ARMAT** (era 0 models amb 2+ SF; **ara n'hi ha 1**: el 163) |
| 7 | Cap lector filtra per `aprovada` | — | **PARCIALMENT MORT**: tancat dins `patterns/`; **viu** a `fitting/`, `pom/`, `models_app/` |

### B3.1 · 🔴 El fork 4 és un bug en curs, no un risc

`pom/s6_views.py:137-139` (`graded_specs_with_units_view`, ruta `size-fittings/<sf_id>/graded-specs-units/`,
`tasks/urls.py:213`). SizeFitting **52** (model **162**, el golden case):

| gv.id | v# | `is_active` | `aprovada` | data |
|---|---|---|---|---|
| 30 | 1 | f | **t** | 2026-06-08 08:05 |
| 31 | 2 | f | f | 2026-06-08 08:12 |
| **32** | **3** | **t** | f | 2026-06-08 08:48 |
| 40 | 4 | f | f | 2026-06-16 16:36 |
| **42** | **5** | **f** | f | 2026-06-16 17:00 |

`graded-specs-units/52/` serveix **gv 42 (v5, DESACTIVADA)**; tots els altres lectors serveixen **gv 32
(v3, l'activa)**. *(Verificat per l'orquestrador amb `SELECT` directe.)*

### B3.2 · El fork 5 estava mal diagnosticat

`fitting/serializers.py:216-224` **NO barreja versions**: la clau del map és `(version_id, pom, size)` i
cada valor surt **etiquetat** amb `version_number`/`data`/`aprovada` dins l'array `evolucio` — és la
**columna d'evolució històrica deliberada** (la pinta `frontend/src/components/model/fittingGridAdapter.jsx:12,37`).
**El seu defecte real és un altre:** és **l'únic lector de `GradedSpec` que no filtra `is_active=True`**
(inofensiu avui: 801/801 specs actius).

### B3.3 · Forks NOUS que la S0 no tenia

- **N1 · `patterns/views.py:448-453`** — 8è criteri: `aprovada=True` + `order_by('-data','-id')`. És
  **l'únic lloc del sistema que tria per `aprovada`**; el frontend autoselecciona `data[0]`
  (`frontend/src/components/pattern/ExportModal.jsx:35-40`).
- **N2 · 🔴 `pom/services.py:279`** (dins `close_base`) — `if not GradedSpec.objects.filter(grading_version__size_fitting=sf).exists(): generate_graded_specs(...)`. **Si QUALSEVOL versió antiga té specs, `exists()` és True → no regenera mai.** Amb 4 SF que tenen specs de 2-7 versions, és un **no-op silenciós garantit**.
- **N3 · `fitting/views.py:70-76`** — `GradingVersionViewSet` és un **ModelViewSet complet** (v. B4.2).
- **Frontends:** grep exhaustiu → **NO EXISTEIX** cap lògica client de selecció de versió (només pinten
  el `version_number` que ve del backend).

### B3.4 · `aprovada` i `is_active` són **ortogonals a les dades**

```sql
SELECT is_active, aprovada, count(*) FROM fitting_gradingversion GROUP BY 1,2;
```
| `is_active` | `aprovada` | files |
|---|---|---|
| f | f | 14 |
| f | **t** | **3** ← 3 de les 4 aprovades **no** són l'activa |
| **t** | f | **3** |
| t | t | **1** |

**Només 1 de 21 files té les dues.** Qualsevol codi que assumeixi «activa ⇒ aprovada» (o l'invers) és
**fals a staging**. Multi-activa i multi-aprovada per SizeFitting: **0 casos avui** (però v. B4.3: **cap
constraint** ho impedeix).

> **Veredicte B3:** el pinçament per `grading_version_id` **segueix sent correcte i necessari**. Els
> forks de selecció no s'han reduït: n'hi ha **10**, i **un d'ells (el 4) serveix dades errònies avui**.

---

## B4 — EL SEAL GUARD: **existeix, però protegeix la porta equivocada**

### B4.1 · On és (i on NO és)

`docs/diagnosis/DIAGNOSI_MOTOR_FRONTERES.md:10` deia que el guard viu a `close_piece_fitting:430-445` i
`resolve_size_check:199-208`. **Aquelles línies ja no el contenen**: el sprint de paritat el va extreure
a un **helper únic**.

**Guard REAL, únic exemplar:** `pom/services.py:561-569`, dins `bump_grading_version_and_generate`
(`:530`):
```python
sealed_active = (GradingVersion.objects
                 .filter(size_fitting_id=sf_id, is_active=True, aprovada=True)
                 .order_by('-version_number').first())
if sealed_active is not None and not allow_reopen_sealed:
    raise ValueError(f"GradingVersion v{...} està aprovada (segellada a producció); ...")
```
Còpia PRE-guard (mateix predicat, 409 en lloc de ValueError): `models_app/views.py:1555-1563`.
Únic **escriptor** del segell: `seal_model_grading` (`fitting/services.py:581-600`), cridat només des de
`advance_phase_gate` (`tasks/services_d.py:45-48`). **Escriptor de `aprovada=False` (dessegellar): NO
EXISTEIX** al codi.

### B4.2 · 🔴 Què NO protegeix

**El guard cobreix *crear v+1*. No cobreix *escriure dins la versió activa*.**
`_get_or_create_grading_version` (`pom/services.py:496-506`) filtra **`is_active=True` i prou — no mira
`aprovada`**; `generate_graded_specs` hi fa `update_or_create` (`pom/services.py:722`).

**Sis endpoints routed criden `generate_graded_specs` directament, sense guard de segellat:**

| Endpoint | Codi |
|---|---|
| `POST /models/<id>/generar-grading/` amb `new_version` falsy | `models_app/views.py:1613` |
| `POST /models/<id>/set-size-override/` | `models_app/views.py:1760` |
| `POST /models/<id>/escalat/ajustar-talla/` | `models_app/views.py:1888` |
| `POST /size-fittings/<sf_id>/regenerar-talles/` | `pom/grading_views.py:37` |
| `POST /size-fittings/<sf_id>/tancar-base/` | `pom/services.py:280` |
| `POST /models/<id>/confirmar-talla-base/` | `pom/wizard_views.py:269` |

**El cas és VIU: gv 67 (SizeFitting 75, model 182) és `is_active=t` I `aprovada=t`.** Qualsevol d'aquests
sis camins li reescriu els specs **conservant `aprovada=True`**.

**Segon forat, més gros:** `GradingVersionViewSet` (`fitting/views.py:70-76`) és un **ModelViewSet
complet** amb `permission_classes=[IsAuthenticated]` i serializer `fields='__all__'`,
`read_only_fields=('data',)` (`fitting/serializers.py:29-35`). **Qualsevol usuari autenticat pot fer
`PATCH {"aprovada": false}` / `{"is_active": ...}` o `DELETE` sobre una versió segellada.** Sense
capability, sense guard.

**Tercer:** `resolve_size_check` només crida el helper si `base_changed AND te_deltes`
(`models_app/services_size_check.py:191`). Sense deltes, s'escriuen `BaseMeasurement` noves
(`origen='CHECKED'`, `:178-185`) **sense guard i sense bump** → la base sota la versió segellada canvia.

**Cobertura de tests del guard D-1: ZERO** (grep de `allow_reopen_sealed` / `segellada a producció` a
fitxers de test → cap resultat).

**Conseqüència directa per a G6:** el motor de patrons pinça per PK i **confia en `gv.aprovada`**
(`patterns/adapters.py:475`, guard dur a `patterns/engine/grading_projection.py:164`). **El flag pot ser
cert mentre el contingut ha canviat després del segell.** Això és el que fa perillós despinçar avui.

### B4.3 · Constraints a BD: **cap**

`fhort.fitting_gradingversion` té només `pkey`, 3 FK i un `CHECK (version_number >= 0)`. **CAP UNIQUE:**
no hi ha unicitat de `(size_fitting, version_number)`, ni de `(size_fitting, is_active)`, ni res sobre
`aprovada`. ⇒ **2+ versions aprovades (o actives) per SizeFitting són estructuralment possibles.** El
codi tampoc ho impedeix (`seal_model_grading` marca sense desmarcar cap anterior). *(Per això
`patterns/adapters.py:425-433` exigeix `filter(pk=…)` i mai `get(aprovada=True)` — la condició C2 de la
S0 es confirma necessària.)*

**Anomalia a les dades:** gv **30** i gv **53** tenen `aprovada=True` amb `aprovada_per=NULL` i
`data_aprovacio=NULL` → **no les pot haver segellades `seal_model_grading`** (que escriu sempre els 3
camps, `fitting/services.py:596-599`). Les `notes` apunten a l'importador guiat — un **camí de codi que
ja NO EXISTEIX** (`extraction_views.py:1583-1584`: «SizeFitting contenidor (sense GradingVersion/GradedSpec)»).

> **Veredicte B4: el segell NO és de confiança.** Protegeix la creació de v+1 i deixa oberta
> l'escriptura in-place i el CRUD REST. **És el bloqueig #1 per a generalitzar.**

---

## B5 — `GateEvent`: sense màquina d'estats (però dades netes)

`tasks/models.py:140-159`. `from_phase`/`to_phase` són **text lliure sense `choices`**. Fases vàlides:
`models_app/models.py:94-101` (`Pending, Dev, Proto, SizeSet, PP, TOP`). Constraints de
`fhort.tasks_gateevent`: només `pkey` + 2 FK. **Cap UNIQUE, cap CHECK.**

Únic escriptor: `tasks/services_d.py`.
- **`advance_phase_gate` (`:25-52`)** valida només **(a)** `to_phase ∈ FASE_CHOICES` i **(b)** `frm != 'TOP'`. **I res més:**
  - **NO comprova adjacència** → `Pending → TOP` en un salt és acceptat.
  - **NO comprova direcció** → un `advance` cap enrere (`PP → Dev`) és acceptat **i segella el grading**
    (`:45-48` → `seal_model_grading`).
  - **NO comprova self-loop** → `Dev → Dev` acceptat (i torna a segellar).
  - **NO exigeix `model_ready_for_gate`** (definit a `:11-17`, consumit només per lectura).
- **`regress_phase` (`:55-69`)** valida només que la fase destí sigui anterior. **NO toca `GradingVersion`:
  no dessegella, no crea versió, no reobre res.** ⇒ **Retrocedir la fase NO reobre el grading**: el guard
  D-1 segueix bloquejant, i els 6 camins de B4.2 segueixen escrivint dins la versió segellada.

**Dades reals: 16 events / 7 models, 100% lineals.** Salts no adjacents: **0**. Cadena trencada
(`from_phase` ≠ `to_phase` de l'event anterior): **0**. `model.fase_actual` ≠ últim `to_phase`: **0**.
El model 162 és l'única cadena amb retrocés real (`TOP→PP→SizeSet→Proto`) — i la seva versió segellada
(gv 30) **segueix `aprovada=True`** després dels 3 retrocessos.

> **Veredicte B5: les dades d'avui són lineals; el codi no ho garanteix.** No és bloquejant per a G6,
> però un `advance` cap enrere **segella** — i això sí que toca el motor.

---

## B6 — `db_constraint=False` cross-schema: 7 FK, **0 orfes avui**

Motiu estructural (django-tenants): `fhort.pom` és SHARED **i** TENANT (`settings.py:55,68`), `fhort.tasks`
és **només** TENANT (`:70`) → un FK real petaria a `public`.

| # | `fitxer:línia` | FK | on_delete | Risc |
|---|---|---|---|---|
| 1 | `pom/models.py:249-251` | `CustomerPOMAlias.customer → tasks.Customer` | PROTECT | **alt** (PROTECT només ORM) |
| 2 | `pom/models.py:440-443` | `GarmentPOMMap.garment_type_item` | CASCADE | **alt** (1529 files; CASCADE només l'emula el collector) |
| 3 | `pom/models.py:480-481` | `ItemBaseMeasurement.garment_type_item` | CASCADE | alt (37 files) |
| 4 | `pom/models.py:545-547` | `GradingRuleSet.customer` | SET_NULL | baix |
| 5 | `pom/models.py:861-864` | `SizingProfile.customer` | SET_NULL | baix |
| 6 | `models_app/models.py:709-713` | `ModelGradingRule.pom → pom.POMMaster` | PROTECT | **alt** |
| 7 | `models_app/models.py:893-897` | `SizeCheckLine.pom → pom.POMMaster` | PROTECT | **alt** |

**Orfes reals avui: 0 als 7 FK** (LEFT JOIN cap a la taula destí, tant a `fhort` com a `public`).
Única validació compensatòria trobada: `pom/views.py:319-321`. **Els altres 6 FK no en tenen.**

**Risc de futur a retenir:** `POMMaster` viu a **dos schemas amb espais d'id independents**
(`public.pom_pommaster` = **0 files**, `fhort.pom_pommaster` = 217). Avui `public` és buit → cap col·lisió
possible. **El dia que s'hi sembrin POMs globals**, un `pom_id` escrit sota un `search_path` diferent
apuntaria a una fila diferent **sense que cap constraint ho detecti**.

> **Veredicte B6: no bloquejant per a G6.** 0 orfes. El risc és latent, no actiu.

---

## B7 — PART 2 · EL DEUTE `test_regim_sense_fallback_400`

### **VEREDICTE: (B) — el test és ESTAL. El 200 és el contracte volgut, decidit i documentat. NO cal fix de codi abans del deploy a PROD.**

### B7.1 · El test i el seu fracàs

`fitting/tests.py:196-201`. El fixture (`:145-152`) crea un POM (`P3`) **sense cap `GradingRule`** al
rule set del model; el test fa POST a `set_pom_regim_view` amb `logica='STEP'` i espera **400**.
Sortida real a HEAD `fdb418c`: `AssertionError: 200 != 400`.

### B7.2 · Per què avui és 200

`models_app/views.py:2531-2547` (`set_pom_regim_view`, def a `:2491`): `src is None` **ja no és una
condició d'error**, és un `if src else <default>` a cada camp — es crea la `ModelGradingRule` de zero
(`origen='MANUAL'`) i es retorna 200. El docstring ho diu textualment (`:2504-2506`): *«si tampoc n'hi ha,
es crea de nou (autoria manual de la regla des de zero)»*.

### B7.3 · Arqueologia (verificada per l'orquestrador)

| Fet | Hash | Data | Commit |
|---|---|---|---|
| **Introdueix** view + guard 400 + el test | `808ef1f` | 2026-06-17 | *«endpoint de règim per-POM…»* — el cos diu literalment «Sense fallback → 400, mai resident buida» |
| **Mata el guard** i **no toca el test** | `407d8af` | **2026-06-23** | *«P3: delta + break editables a la talla base (regla viva del model)»* |

`git log -S "No hi ha regla de fallback" --all` → **només aquests dos commits**. El `--stat` de `407d8af`
confirma que toca `models_app/views.py` + frontend, i **no `fitting/tests.py`**.
`git diff b93db34 HEAD -- backend/fhort/fitting/tests.py backend/fhort/models_app/views.py` → **buit** ⇒
el vermell és **preexistent** i **cap sessió recent** (ni la d'`extraction_views`) l'ha causat.

### B7.4 · La decisió està escrita

- **`DECISIONS.md:280-294`** — Sprint *SOBIRANIA DE LA REGLA* (2026-06-23). **Llei (Agus):** «tot sembra
  el model però **tot viu i és modificable AL MODEL, inclosa la REGLA** (deltes+breaks)».
- **`DECISIONS.md:686-688`** — el vermell **ja estava censat** com a preexistent i com a «peça pròpia».

**Per què el 200 és el contracte correcte:** el consumidor real ja no és un desplegable de règim —
`frontend/src/components/model/CheckMeasureEditor.jsx:138` hi envia `increment_base`/`increment_break`/
`talla_break_label` per **autorar la regla des de zero a Mesures**. Amb el guard antic, **un POM sense
regla de catàleg seria ineditable per sempre** — exactament el que P3 volia desbloquejar.

### B7.5 · Què cal fer (deute, 1 fitxer, només test)

`💡 PROPOSTA (a validar)` — reescriure `fitting/tests.py:196-201` al contracte viu: renombrar-lo
(p.ex. `test_regim_sense_fallback_crea_regla_de_zero`) i afirmar `status_code == 200` +
`ModelGradingRule` creada per a `pom3` amb `origen='MANUAL'`, `logica='STEP'`, `increment == 0`.
**No s'ha tocat** (Patró A read-only).

### B7.6 · 🔴 Troballa col·lateral (fora d'encàrrec, risc REAL)

El fork tot-o-res de B2.2 té una conseqüència que **cap test cobreix**: **crear la PRIMERA
`ModelGradingRule` d'un model (per a un sol POM, des del desplegable de règim) fa que TOTS els altres
POMs del model perdin la regla de catàleg** — i a `pom/services.py:101-102` un POM sense regla es gradua
`graded_val = base_val` / `'FIXED'` → **totes les talles planes, en silenci, sense warning**. No ho ha
introduït l'eliminació del guard (era igual d'assolible via un POM amb fallback), però **és una mina
viva**.

---

## 💡 PROPOSTA D'UNIFICACIÓ SEQÜENCIADA (a validar — Patró C)

> Cap d'aquestes peces s'ha implementat. L'ordre és per **cost creixent** i **desbloqueig decreixent**.

### FASE 0 — Els 3 sagnats que no poden esperar *(no és unificació; és aturar l'hemorràgia)*

| # | Peça | Cost | Risc |
|---|---|---|---|
| **0a** | **Fork 4**: `pom/s6_views.py:137-139` → usar `vigent_grading_version(sf)`. **Avui serveix la v5 desactivada del model 162.** | **1 línia** | Nul. Alinea amb la resta del sistema |
| **0b** | **Gate dur**: `pom/services.py:42-43` — condicionar el `ValueError` a que el model **tampoc tingui `ModelGradingRule` actives**. Desbloqueja el model 163 (25 regles, 0 specs). | ~3 línies | Baix. Cal decidir si 163 ha de graduar |
| **0c** | **`close_base` no-op**: `pom/services.py:279` — l'`exists()` cross-version fa que **no regeneri mai** si hi ha specs d'una versió antiga. Filtrar per la versió vigent. | ~2 línies | Baix |

### FASE 1 — Matar el que ja és mort *(barat, sense migració de dades)*

| # | Peça | Per què és barat |
|---|---|---|
| **1a** | **Jubilar `GradingException`** + la branca `elif exc:` (`pom/services.py:98-100`, `:176-177`) i `_load_grading_exceptions` (`:452-463`). | **0 files**, **cap escriptor a l'aplicació**, substitut declarat al docstring de `ModelGradingOverride`. Migració de dades: **cap**. *(Deixar el model i la taula si es vol; el que es mata és el **fork**.)* |
| **1b** | **Jubilar l'endpoint orfe** `set_size_override_view` (`models_app/views.py:1730`) + el client mort (`endpoints.js:65-66`). | **Zero cridadors** a tot `frontend/src`. |

⚠️ **1a NO implica jubilar `ModelGradingOverride`**: és el substitut viu (escrit per
`escalat_ajustar_talla_view`). El que mor és **el dual**, no el mecanisme.

### FASE 2 — Segellar el segell *(el bloqueig #1; toca el motor indirectament)*

| # | Peça | Notes |
|---|---|---|
| **2a** | **Guard d'escriptura in-place**: `_get_or_create_grading_version` (`pom/services.py:496-506`) ha de **refusar** servir una versió `aprovada=True` (o forçar bump). Tanca els **6 endpoints** de B4.2. | **És el que permet que el motor confiï en `gv.aprovada`.** Cal decidir el comportament: 409, o bump automàtic. |
| **2b** | **Tancar el CRUD REST**: `GradingVersionViewSet` (`fitting/views.py:70-76`) → `ReadOnlyModelViewSet`, o `read_only_fields` sobre `aprovada`/`is_active`, o capability. | Avui qualsevol autenticat pot flipar el segell. |
| **2c** | **Constraint a BD**: UNIQUE parcial `(size_fitting) WHERE is_active` i `(size_fitting, version_number)`. | **Migració de dades: cap** (0 duplicats avui). Converteix les condicions C1/C2 de la S0 en garantia estructural. |
| **2d** | **Tests del guard D-1** (avui: **zero**). | Prerequisit per tocar res d'això amb confiança. |

### FASE 3 — Unificar la propietat del ruleset *(necessita decisió de producte)*

| # | Peça | Necessita |
|---|---|---|
| **3a** | **`GarmentTypeItem.grading_rule_set`**: decidir si **es propaga** a `Model` (i llavors implementar-ho a `_resolve_garment_def`, `models_app/views.py:428-431`) o **es jubila**. Avui és una fulla morta que la UI deixa editar. | **Decisió del CTO.** 1/57 files. |
| **3b** | **FK legacy `GradingRuleSet.target`** → migrar l'anti-proliferació 1D (`pom/grading_utils.py:311-319`) a la M2M `targets`, i arreglar el clon (`pom/s2_views.py:195`) perquè copiï la M2M. Llavors **DROP del FK**. | **Migració de dades: SÍ** (backfill `target` → `targets` per a la fila id 98; els 4 multi-target ja hi són). El deute ja és al codi (`grading_utils.py:92-95`). |

### FASE 4 — El fork tot-o-res *(el més profund; NO tocar sense decisió)*

| # | Peça | Notes |
|---|---|---|
| **4a** | `_load_grading_rules` (`pom/services.py:425-446`): decidir si el fallback ha de ser **tot-o-res** (avui) o **merge per POM** (resident guanya POM a POM, la resta cau al catàleg). | **Canvia el resultat del grading de models reals.** Avui, crear 1 sola MGR aplana en silenci tots els altres POMs (B7.6). Requereix decisió + backfill + regeneració controlada. **Zona intocable sense encàrrec explícit.** |
| **4b** | **Asimetria**: les excepcions es llegeixen sempre del ruleset extern (`pom/services.py:64`) encara que les regles siguin residents. Coherent amb 4a. | Irrellevant mentre `GradingException` sigui 0 files (Fase 1a la resol de retruc). |

### Què desbloqueja **generalitzar la projecció del motor**

**Mínim imprescindible: FASE 2 (2a + 2b).** Mentre el contingut d'una versió `aprovada=True` es pugui
reescriure in-place per 6 endpoints i el flag es pugui flipar per REST, **el `grading_version_id`
explícit és l'única cosa que fa la projecció determinista** — i el pinçament s'ha de mantenir. Les fases
0 i 1 són barates i **no** desbloquegen G6 per si soles; la 3 i la 4 són ortogonals a la projecció.

---

## TAULA FINAL DE RISCOS (per al CTO)

| # | Risc | Evidència | Gravetat | Actiu avui? |
|---|---|---|---|---|
| R1 | **El segell menteix**: 6 endpoints reescriuen `GradedSpec` dins una versió `aprovada=True`; el motor confia en el flag | `pom/services.py:496-506` · `patterns/engine/grading_projection.py:164` · gv 67 activa+aprovada | 🔴 **Alta** | **SÍ** (gv 67, model 182) |
| R2 | **Fork 4 serveix una versió desactivada** — dues superfícies de la UI mostren talles diferents | `pom/s6_views.py:137-139` · SF 52 → gv 42 (v5, inactiva) vs gv 32 (v3, activa) | 🔴 **Alta** | **SÍ** (model 162) |
| R3 | **CRUD REST obert sobre el segell**: qualsevol autenticat pot `PATCH aprovada` o `DELETE` | `fitting/views.py:70-76` · `fitting/serializers.py:29-35` | 🔴 **Alta** | SÍ (superfície) |
| R4 | **Fork tot-o-res**: crear 1 MGR aplana en silenci tots els altres POMs (`FIXED`, sense warning) | `pom/services.py:438-446` · `:101-102` | 🔴 **Alta** | Latent (assolible) |
| R5 | **Model 163 no pot graduar mai**: 25 MGR actives, `grading_rule_set = NULL` → `ValueError` | `pom/services.py:42-43` · 0 `GradedSpec` a la BD | 🟠 Mitjana | **SÍ** |
| R6 | **`close_base` no regenera mai** si hi ha specs d'una versió antiga | `pom/services.py:279` · 4 SF amb specs de 2-7 versions | 🟠 Mitjana | **SÍ** |
| R7 | **Cap constraint** impedeix 2+ versions actives/aprovades per SizeFitting | `pg_constraint` de `fitting_gradingversion`: cap UNIQUE | 🟠 Mitjana | Latent (0 casos) |
| R8 | **Fork 6 armat**: `_resolve_working_size_fitting` tria per `numero`, no per estat | `fitting/services.py:534-543` · model 163 té SF 53 (Pendent) i 79 (Tancat) → tria el Pendent | 🟠 Mitjana | Latent (0 grading) |
| R9 | **`advance_phase_gate` sense màquina d'estats**: accepta salts, retrocessos i self-loops — **i segella** | `tasks/services_d.py:25-52` | 🟡 Baixa | Latent (dades 100% lineals) |
| R10 | **FK legacy `target` divergeix** de la M2M autoritativa; el clon perpetua la divergència | `pom/models.py:559-570` · `pom/s2_views.py:195` · 1/25 files ja divergent | 🟡 Baixa | SÍ (1 fila) |
| R11 | **2 versions aprovades sense `aprovada_per`** — d'un camí de codi que ja NO EXISTEIX | gv 30, gv 53 · `fitting/services.py:596-599` | 🟡 Baixa | SÍ (dades) |
| R12 | **`db_constraint=False`**: CASCADE/PROTECT només-ORM sobre 1566+ files | 7 FK (B6) | 🟡 Baixa | **NO** (0 orfes) |
| R13 | **`test_regim_sense_fallback_400` vermell** | `fitting/tests.py:196-201` | 🟢 **Nul** | Test estal — **no cal fix de codi** |

### Estat de les 2 preguntes del brief

- **PART 1 (G6):** el cens està tancat. **La projecció NO es pot generalitzar avui** — no pels forks de
  selecció (que el pinçament esquiva), sinó perquè **el segell no garanteix immutabilitat del contingut**
  (R1). **Fase 2 és el desbloqueig.**
- **PART 2 (deute):** **(B) test estal.** El 200 és legítim i decidit (`407d8af`, `DECISIONS.md:280-294`).
  **No bloqueja el deploy a PROD.** Queda un deute de test d'un sol fitxer.
