> ⚠️ SUPERADA 2026-07-07 — implementada (superficiar fase / retirar estat: b9e2602/e2fddb9). Consulta només com a històric.

# DIAGNOSI G2 — `Model.estat`: derivar o mantenir?

**Data:** 2026-06-26 · **Branca:** `dev` · **Patró:** A (READ-ONLY, 0 codi, 0 push) · Dades: schema `fhort`
**Objectiu de disseny:** determinar si `fase_actual` SOL cobreix l'usabilitat que `Model.estat` dóna
avui, per decidir entre **(1)** matar el camp i superficiar la fase, o **(2/3)** derivar un estat
d'activitat. La diagnosi porta els FETS; **la decisió NO es pren aquí** (Patró C).

> **TL;DR dels fets:** `Model.estat` només té **2 valors assolibles per codi** — `'Nou'` (creació) i
> `'Tancat'` (gate TOP) — i el `'Tancat'` el dispara **el propi gate de fase** (`fase==TOP`). Els
> altres 2 choices (`EnCurs`/`EnRevisio`) **no els escriu ningú**. A BD, **els 19 models = `'Nou'`**.
> `fase_actual` SÍ té motor i distribució real. → §A4 conclou que estat és **derivable** de la fase
> per al que mostra avui; el senyal "actiu/en curs" **no viu a estat** (mai s'hi va implementar).

---

## A1 — Qui ESCRIU `Model.estat`

**Definició del camp ([models.py:201](backend/fhort/models_app/models.py#L201)):**
`estat = CharField(max_length=20, choices=ESTAT_CHOICES, default=ESTAT_NOU)`
**Choices ([models.py:83-92](backend/fhort/models_app/models.py#L83-L92)):** `Nou` · `EnCurs` · `EnRevisio` · `Tancat` (4).

**Escriptors reals de `Model.estat` (backend):**
| Què escriu | On | Valor |
|---|---|---|
| Creació (create-wizard / create) | [views.py:385](backend/fhort/models_app/views.py#L385), [views.py:422](backend/fhort/models_app/views.py#L422) | `'Nou'` |
| Creació via tech-sheet | [tech_sheet_views.py:305](backend/fhort/models_app/tech_sheet_views.py#L305) | `'Nou'` |
| Creació via bulk import | [bulk_import_service.py:502](backend/fhort/models_app/bulk_import_service.py#L502) | `'Nou'` |
| Clon QA | [clone_model_for_qa.py:82](backend/fhort/models_app/management/commands/clone_model_for_qa.py#L82) | `'Nou'` |
| **Gate TOP (única TRANSICIÓ)** | [services_d.py:46-48](backend/fhort/tasks/services_d.py#L46-L48) | `ESTAT_TANCAT` |

- L'**única transició** d'estat de tota la base de codi és a `advance_phase_gate`: en arribar a
  `to_phase=='TOP'` fa `model.estat = Model.ESTAT_TANCAT` ([services_d.py:46-48](backend/fhort/tasks/services_d.py#L46-L48)). És a dir,
  **`Tancat` ⟺ `fase==TOP`** (conseqüència del gate, no un estat independent).
- **`EnCurs` i `EnRevisio` NO els escriu cap línia de codi** (grep exhaustiu): són choices morts.
- **Asimetria (FET):** `regress_phase` ([services_d.py:60-72](backend/fhort/tasks/services_d.py#L60-L72)) NO toca `estat` → si un model TOP es
  retrocedeix, `estat` es queda `Tancat` (no reobre). Reforça que estat no és una màquina pròpia.

**Distribució REAL a BD (schema `fhort`, 19 models) — confirma "tots = Nou":**
```
estat:        {'Nou': 19}                                  ← 100% Nou
fase_actual:  {'Pending': 5, 'Dev': 12, 'Proto': 1, 'PP': 1}
estat×fase:   Nou/Pending 5 · Nou/Dev 12 · Nou/Proto 1 · Nou/PP 1
```
→ `estat` aporta **0 bits d'informació avui** (constant 'Nou'); cap model ha arribat a TOP, així que
ni `Tancat` apareix. `EnCurs`/`EnRevisio` = 0 i, a més, **inassolibles**. *(No cal mostrar QA a part:
el clon QA neix amb `estat='Nou'` per [clone_model_for_qa.py:82](backend/fhort/models_app/management/commands/clone_model_for_qa.py#L82); el golden 162 NO s'ha tocat.)*

**Choices declarats vs presents:** 4 declarats · **1 present a BD** (`Nou`) · **2 assolibles per codi**
(`Nou`, `Tancat`) · **2 morts** (`EnCurs`, `EnRevisio`).

---

## A2 — Qui LLEGEIX `Model.estat` (consumidors a reapuntar)

### Backend
- **Serialitza:** `ModelSerializer` emet `estat` ([serializers.py:37](backend/fhort/models_app/serializers.py#L37)) i `fase_actual` ([:38](backend/fhort/models_app/serializers.py#L38)).
  ⚠️ Aquest serializer **no declara `read_only_fields`** per a estat → DRF el deixa **writable** per
  defecte; cap pantalla l'escriu, però un PATCH a `/models/<id>/` l'acceptaria (punt menor de neteja).
- **Filtre:** `filterset_fields` inclou `'estat'` i `'fase_actual'` ([views.py:38](backend/fhort/models_app/views.py#L38)) → `?estat=` funciona a
  l'API de llista.
- **Ordre:** `ordering_fields = ['prioritat','data_objectiu','data_entrada']` ([views.py:47](backend/fhort/models_app/views.py#L47)) → **estat NO
  és ordenable** (ni fase_actual).
- **Índex compost:** `models.Index(fields=['estat','fase_actual'])` ([models.py:321](backend/fhort/models_app/models.py#L321)) — l'única
  estructura de BD que referencia estat (cap FK l'apunta).
- **Lògica de negoci que ramifiqui per estat:** NO se n'ha trobat cap (cap `if model.estat ==`); l'únic
  ús de negoci és l'escriptura a Tancat del gate (A1).

### Frontend (consumidors de `model.estat` — el del Model, no d'altres entitats)
| On | Què fa | línia |
|---|---|---|
| Llista de Models | `<EstatBadge estat={m.estat} />` (badge) | [Models.jsx:160](frontend/src/pages/Models.jsx#L160) |
| ModelSheet (detall) | mostra `model.estat` (capçalera/camps) | [ModelSheet.jsx:604](frontend/src/pages/ModelSheet.jsx#L604), [:691](frontend/src/pages/ModelSheet.jsx#L691), [:895](frontend/src/pages/ModelSheet.jsx#L895) |
| Dashboard (board govern) | **FILTRE** `?estat=` amb dropdown | [Dashboard.jsx:120](frontend/src/pages/Dashboard.jsx#L120),[:142](frontend/src/pages/Dashboard.jsx#L142),[:248-250](frontend/src/pages/Dashboard.jsx#L248-L250) |

- El **filtre d'estat** del Dashboard ofereix `ESTATS = ["Nou","EnCurs","EnRevisio","Tancat"]`
  ([Dashboard.jsx:24](frontend/src/pages/Dashboard.jsx#L24)) i envia `p.estat` ([:142](frontend/src/pages/Dashboard.jsx#L142)). **Funcionalment mort avui**: triar res ≠ "Nou"
  retorna 0 models (tots Nou). És l'**únic filtre/ordre per estat de tota la UI** (Models.jsx NO filtra
  per estat — només `fase`, `temporada`, `search`, [Models.jsx:33-35](frontend/src/pages/Models.jsx#L33-L35)).
- **`EstatBadge`** ([components/EstatBadge.jsx:51](frontend/src/components/EstatBadge.jsx#L51)) mapeja l'string → color + clau i18n
  (`Nou→model.estats.Nou`, `Tancat→model.estats.Tancat`, etc.). És **compartit** (també pinta
  prioritats i estats de SF/tasques) → NO es pot esborrar; només es deixaria de cridar amb `model.estat`.

---

## A3 — `fase_actual`: l'alternativa real

- **Definició ([models.py:202](backend/fhort/models_app/models.py#L202)):** `CharField(choices=FASE_CHOICES, default='Pending')`.
  **FASE_CHOICES ([models.py:94-101](backend/fhort/models_app/models.py#L94-L101)):** `Pending · Dev · Proto · SizeSet · PP · TOP` (6, ordenades).
- **Qui l'escriu (motor real):**
  | Què | On |
  |---|---|
  | 1a tasca arrencada: `Pending→Dev` | [services_c.py:95](backend/fhort/tasks/services_c.py#L95) |
  | Gate del responsable (avança) | `advance_phase_gate` [services_d.py:37](backend/fhort/tasks/services_d.py#L37) |
  | Retrocés de fase | `regress_phase` [services_d.py:69](backend/fhort/tasks/services_d.py#L69) |
  | Aprovació de fitting avança fase | [fitting/services.py:730](backend/fhort/fitting/services.py#L730) |
  - Endpoints: `modelsApi.gate`/`regress` → cridats des de [ActionsMenu.jsx:170-171](frontend/src/components/model/ActionsMenu.jsx#L170-L171) i
    [DashboardGovPanel.jsx:217](frontend/src/components/planning/DashboardGovPanel.jsx#L217). Cada transició desa un **`GateEvent`** (traça).
- **Valors reals a BD:** `Pending 5 · Dev 12 · Proto 1 · PP 1` (distribució viva).
- **Es mostra JA al frontend? SÍ, àmpliament:**
  | On | Com |
  |---|---|
  | Llista de Models | `<span style={faseBadge}>{m.fase_actual}</span>` (**valor cru, sense i18n**) [Models.jsx:165](frontend/src/pages/Models.jsx#L165) |
  | Filtre de llista | `params.fase_actual` (dropdown) [Models.jsx:34](frontend/src/pages/Models.jsx#L34),[:91](frontend/src/pages/Models.jsx#L91) |
  | ModelSheet | `model.fase_actual` [ModelSheet.jsx:697](frontend/src/pages/ModelSheet.jsx#L697) |
  | Dashboard board | `FaseChip` + `faseCounts` per fase, i18n `model_sheet.dashboard.phase.*` [Dashboard.jsx:222](frontend/src/pages/Dashboard.jsx#L222) |
  | ProjectGantt / DashboardTab del model | pinta i ordena per fase |
  - i18n de fase **ja existeix i és ric**: `model_sheet.dashboard.phase` = `{Pending:Pendent, Dev:
    Desenvolupament, Proto:Prototip, SizeSet:Joc de talles, PP:Preproducció, TOP:Producció}`.
  - → **L'opció 1 reusa representació de fase ja existent**; l'únic forat cosmètic és que
    [Models.jsx:165](frontend/src/pages/Models.jsx#L165) pinta el valor cru (caldria passar-lo per `model_sheet.dashboard.phase.*`).

---

## A4 — LA PREGUNTA DE DISSENY (lliurable clau)

**Mapeig conceptual — què comunica `estat` que `fase_actual` no?**
| `estat` (intenció dels 4 choices) | Realitat al codi | On viu de debò |
|---|---|---|
| `Nou` (no començat) | default de creació; mai canvia sol | ≈ `fase_actual == 'Pending'` |
| `EnCurs` (s'està movent) | **MAI escrit** (choice mort) | **NO a estat** → fase!=Pending + tasques InProgress/Paused + `consumption_started_at` |
| `EnRevisio` (en revisió) | **MAI escrit** (choice mort) | no modelat enlloc com a estat de Model |
| `Tancat` (producció/terminal) | escrit NOMÉS pel gate TOP | ⟺ `fase_actual == 'TOP'` |

**Resposta a "captura `fase_actual` la noció «aquest model està actiu»?":**
- La **posició al cicle** (nou→…→tancat) SÍ la captura `fase_actual` completament; `Nou`≈`Pending` i
  `Tancat`≈`TOP` (de fet el `Tancat` el **deriva el gate de fase**, [services_d.py:46-48](backend/fhort/tasks/services_d.py#L46-L48)).
- El **senyal d'activitat "s'està movent"** (l'equivalent a `EnCurs`) **NO el dóna `estat`** —
  perquè `EnCurs` no s'escriu mai. Avui aquest senyal només existeix, implícitament, en:
  `fase_actual != 'Pending'` (la 1a tasca el treu de Pending, [services_c.py:95](backend/fhort/tasks/services_c.py#L95)) **+** agregació de
  ModelTask (`InProgress`/`Paused`) **+** `consumption_started_at` (camp de Model, àncora d'inici real,
  usat pel Gantt). Cap d'aquests és `Model.estat`.

**💡 CONCLUSIÓ A VALIDAR (no decisió):**
> Per a **tot el que `estat` mostra/filtra avui**, `fase_actual` és suficient: estat és constant
> (`Nou`) o redundant amb la fase (`Tancat`=TOP). → **Opció 1 (matar camp + superficiar fase) és
> viable sense pèrdua d'informació EXISTENT.** El matís d'activitat (`EnCurs`) que el camp prometia
> **mai es va implementar**, així que l'opció 1 no perd res que avui funcioni. **Si** el producte vol
> un badge explícit "actiu/en curs", aquell senyal **s'ha de DERIVAR** (opció 2/3) de
> `fase + tasques + consumption_started_at` — però seria funcionalitat **nova**, no recuperació d'estat.

---

## A5 — Cost de cada camí

### Opció 1 — matar `estat`, superficiar fase
**Consumidors a reapuntar (tots localitzats):**
- Frontend (3): badge de llista [Models.jsx:160](frontend/src/pages/Models.jsx#L160) (→ usar fase, ja hi és a [:165](frontend/src/pages/Models.jsx#L165)); display de detall
  [ModelSheet.jsx:604](frontend/src/pages/ModelSheet.jsx#L604)/[:691](frontend/src/pages/ModelSheet.jsx#L691)/[:895](frontend/src/pages/ModelSheet.jsx#L895); **filtre Dashboard** [Dashboard.jsx:120](frontend/src/pages/Dashboard.jsx#L120)/[:142](frontend/src/pages/Dashboard.jsx#L142)/[:248-250](frontend/src/pages/Dashboard.jsx#L248-L250)
  + constant `ESTATS` [:24](frontend/src/pages/Dashboard.jsx#L24).
- Backend (4): treure de `fields` [serializers.py:37](backend/fhort/models_app/serializers.py#L37); treure de `filterset_fields` [views.py:38](backend/fhort/models_app/views.py#L38); treure
  la línia `model.estat = ESTAT_TANCAT` del gate [services_d.py:46-48](backend/fhort/tasks/services_d.py#L46-L48); camp + `ESTAT_CHOICES`
  [models.py:83-92](backend/fhort/models_app/models.py#L83-L92),[:201](backend/fhort/models_app/models.py#L201).
- **Filtre/ordre que es perdria:** el filtre `?estat=` del Dashboard (avui **mort** — tots Nou). **Cap
  ordre** per estat (no és a `ordering_fields`). **Cap pèrdua funcional real.**
- **Migració DROP:** toca **l'índex compost** `Index(fields=['estat','fase_actual'])` [models.py:321](backend/fhort/models_app/models.py#L321) →
  cal substituir-lo per `Index(fields=['fase_actual'])` (o eliminar). **Cap FK** apunta estat → DROP net.
  És **diferible**: es pot treure de serializer/filtre/UI primer (deixant la columna), i fer el
  `DROP COLUMN` + reindex en una migració posterior, sense bloquejar.

### Opció 2/3 — derivar un estat d'activitat
- **Propietat-serializer (només MOSTRAR):** `SerializerMethodField` que retorni p.ex. `Tancat` si
  `fase=='TOP'`, `EnCurs` si (`consumption_started_at` o alguna ModelTask `InProgress/Paused` o
  `fase!='Pending'`), si no `Nou`. **Cap canvi de BD.** Cobreix Models.jsx/ModelSheet (display).
- **Annotation-queryset (cal FILTRAR/ORDENAR):** si es vol mantenir el filtre del Dashboard sobre
  l'estat derivat, cal `annotate` amb `Case/When` sobre `fase_actual` + `Exists(ModelTask InProgress)`
  + `consumption_started_at`. Més cost; només si es recupera el filtre (que avui és mort).
- **Inputs i d'on surten:** `fase_actual` (Model), `consumption_started_at` (Model, ja usat al
  `gantt_view`), `model_tasks.status` (relació ModelTask). Tots disponibles sense camps nous.

---

## Punts OBERTS
- **Writable del serializer:** `estat` no té `read_only_fields` al `ModelSerializer` → tècnicament
  un PATCH l'acceptaria; no s'ha trobat cap client que ho faci, però no es pot **provar negatiu** al
  100% en read-only (formularis externs/scripts). Marcat OBERT (impacte baix).
- Cap altre punt obert: A1–A5 resolts amb codi + BD.

### Resum per decidir (Agus + Claude, Patró C)
1. `estat` avui = constant `Nou` (19/19) + un `Tancat` derivat del gate TOP; `EnCurs`/`EnRevisio` morts.
2. `fase_actual` té motor, distribució i representació frontend ja existents.
3. Opció 1 reapunta **3 punts frontend + 4 backend**, perd només un filtre **ja mort**, i la migració
   DROP és **diferible** (només toca 1 índex compost, cap FK).
4. Opció 2/3 només cal si es vol un badge "actiu" NOU (que estat no dóna avui): property-serializer si
   és només mostrar, annotation si cal filtrar.

---

# SECCIÓ B — `TipologiaModel` (complement 3b)

**Mateix criteri codi-mort:** s'esborra NOMÉS amb grep que confirmi 0 consumidor/FK **entrant** viu;
una FK viva entrant = es manté encara que sembli mort. Read-only, dades schema `fhort` (clon QA neix
de [clone_model_for_qa.py](backend/fhort/models_app/management/commands/clone_model_for_qa.py); golden 162 intacte).

> **TL;DR:** `TipologiaModel` és un model Django amb taula i **57 files sembrades**, però **0
> escriptors de codi · 0 FK entrants · 0 lectors** (cap serializer, view, admin, frontend; el
> related_name `.tipologies` mai es navega). Té només una FK **sortint** a `GarmentType` (no bloqueja
> el seu propi DROP). → **veredicte (a) MORT SEGUR** (§B4). Migració aïllable i diferible (§B5).

## B1 — Què és
- **Model Django** (taula pròpia): `class TipologiaModel(models.Model)` ([tasks/models.py:4](backend/fhort/tasks/models.py#L4)).
  Camps: `codi (unique)`, `nom`, `familia`, `familia_codi`, FK **sortint** `garment_type →
  pom.GarmentType` (`on_delete=SET_NULL`, `related_name='tipologies'`, [:16-22](backend/fhort/tasks/models.py#L16-L22)), `complexitat`,
  `patrons_aprox`, i 4+ `slots_*` (DecimalField). `verbose_name='Tipologia de model'` ([:38](backend/fhort/tasks/models.py#L38)).
- **Taula creada per migració** `0002_tipologiamodel.py` (CreateModel; `operations` sense `RunPython`
  → **la migració NO sembra dades**).
- **Files reals:** **57 a `fhort`** (tenant). A `public` → `ProgrammingError` (taula inexistent) → és
  un model de **TENANT_APPS** (per-schema). → Taula **sembrada** (57 files de master-data), però la
  sembra **no és al codi** (cap migració de dades, cap fixture, cap command — §B2): càrrega externa
  (SQL/loaddata manual) feta una vegada.

## B2 — Qui ESCRIU
- **0 escriptors de codi.** `grep "TipologiaModel.objects" / "TipologiaModel("` a tot `fhort` →
  **només la definició de classe** ([tasks/models.py:4](backend/fhort/tasks/models.py#L4)); cap `create`/`update`/instància a views,
  serializers, signals, seeds, management commands ni migracions de dades.
- Les 57 files existeixen però **cap línia de codi les escriu** → master-data carregada fora de banda.

## B3 — Qui LLEGEIX / FK (el grep decisiu)
- **FK ENTRANTS (qui depèn d'ell): CAP.** `grep "ForeignKey(...TipologiaModel" / "'TipologiaModel'" /
  "\"TipologiaModel\""` a tot el backend → **0 hits** fora del `CreateModel` de la seva pròpia migració.
  Cap model fa FK/OneToOne/M2M cap a `TipologiaModel`. **Aquest és el punt que decideix: no hi ha FK
  viva entrant.**
- **FK SORTINT (ell → un altre):** `garment_type → pom.GarmentType` (SET_NULL, [:16-22](backend/fhort/tasks/models.py#L16-L22)). És
  sortint → **no bloqueja el seu propi DROP**; en eliminar-lo, `GarmentType` només perd el
  `related_name='tipologies'`, **que ningú navega** (grep `.tipologies` → buit).
- **Backend lectors:** cap serializer l'emet, cap queryset/filter/ordering el referencia, **no està
  registrat a cap `admin.py`**.
- **Frontend:** **0 referències** a `frontend/src` (grep `TipologiaModel` → buit).
- **Desambiguació (FET):** els hits de `tipologia` en minúscula del repo són **`Tenant.tipologia`**
  (CharField estudi/marca/enterprise, [tenants/models.py:34](backend/fhort/tenants/models.py#L34)) i `extraction.tipologia_confirmada` —
  **entitats diferents**, sense relació amb `TipologiaModel`.
- **Coincidència conceptual NO cablejada:** `Model` té camps `slots_prev_tecnics/_confeccio` (serializer
  [serializers.py:51-54](backend/fhort/models_app/serializers.py#L51-L54)) que semànticament s'assemblen als `slots_*` de `TipologiaModel`, però **no hi ha
  cap codi que els derivi de `TipologiaModel`** (cap lookup per `codi`); són camps independents del Model.

## B4 — Veredicte d'estat (FET, sense decidir l'acció)
**💡 (a) MORT SEGUR — esborrable.** Compleix els tres: **0 escriptors de codi** + **0 FK viva
entrant** + **0 lectors** (backend/frontend/admin). Les 57 files i la FK sortint a `GarmentType` **no
el mantenen viu** segons la llei codi-mort (la llei guarda per FK **entrant**, i no n'hi ha). No és
(b) MORT-ALIVE (no hi ha FK declarada entrant que obligui a mantenir-lo) ni (c) VIU (cap consumidor
real). *Únic matís a validar abans d'esborrar: les 57 files són master-data que algú podria voler
preservar/migrar a un altre lloc; és decisió de producte, no de codi.*

## B5 — Agrupació 3b (migració)
- **Comparteix natura amb G2:** SÍ — esborrar `TipologiaModel` és **canvi d'esquema** (`DROP TABLE`
  `tasks_tipologiamodel` per-tenant) → va al **mateix sub-bloc de migració pre-deploy** que el DROP
  diferit de `Model.estat`.
- **Aïllable:** SÍ — **cap FK entrant** → el DROP és **aïllat, sense cascada**. No toca cap altra taula
  (la FK sortint a `GarmentType` desapareix amb la pròpia taula; `GarmentType` no s'altera). És en una
  **app diferent** (`tasks`) que el `Model.estat` (`models_app`) → **independent** d'aquell DROP; es
  poden fer per separat o junts al mateix pas.
- **Diferible:** SÍ — com que ningú el llegeix ni en depèn, el DROP no té cap precondició de codi; es
  pot programar al pas pre-deploy sense reapuntar consumidors (no n'hi ha).

---

## Tancament 3b (G2 + TipologiaModel)
| | escriptors | lectors / FK entrant viva | veredicte | migració |
|---|---|---|---|---|
| **`Model.estat`** | només creació (`Nou`) + gate TOP (`Tancat`); `EnCurs`/`EnRevisio` morts | display (Models/ModelSheet) + filtre Dashboard (mort) + 1 índex compost; **cap FK entrant** | derivable de `fase_actual` (§A4) | DROP diferible; toca 1 índex compost; cap FK |
| **`TipologiaModel`** | **0 de codi** (57 files sembrades fora de banda) | **0 lectors, 0 FK entrant**; 1 FK sortint a GarmentType | **MORT SEGUR** | DROP aïllat, sense cascada; app `tasks`; diferible |

Cap acció d'esborrat es pren aquí (Patró C); el doc tanca el 3b amb els fets per decidir-la.

---

# SECCIÓ C — ¿La "imatge" de TipologiaModel ja viu a GarmentType/Item? (DROP net vs export previ)

Read-only, dades schema `fhort` (clon QA per a comptes; golden 162 intacte). Objectiu: decidir si el
DROP de `TipologiaModel` és **NET** (la dada ja és a GarmentType/Item → cap export) o exigeix **EXPORT**
(les 57 files són l'única còpia). No s'esborra res.

> **TL;DR:** **NO**, la imatge **no** viu a GarmentType/Item. Cap dels dos té els camps quantitatius de
> `TipologiaModel` (`slots_*`, `complexitat`, `patrons_aprox`). La matriu de temps **viva** és una taula
> **distinta** (`TaskTimeEstimate`, item×task_type→minuts) amb **una altra forma** i sembrada
> **independentment**. A més, **les 57 files tenen `garment_type=None`** (0/57) → ni tan sols hi ha
> enllaç. → **veredicte (b) EXPORT PREVI** (§C4): la dada família-nivell només viu a TipologiaModel.

## C1 — Camps de GarmentType i GarmentTypeItem
- **`GarmentType`** ([pom/models.py:372-404](backend/fhort/pom/models.py#L372-L404)): `garment_type_global` (FK), `codi_client`, `nom_client`,
  **`grup`** (CharField 40 — etiqueta de família-ish), `actiu`, `nom_en/ca/es`, `is_system`,
  `targets_recomanats` (M2M), `construccio_habitual`, `descripcio`.
  → **NO** té `familia_codi`, `complexitat`, `patrons_aprox`, **ni cap `slots_*`/temps**. L'únic anàleg
  parcial és `grup` (nom de família), sense la càrrega quantitativa.
- **`GarmentTypeItem`** ([tasks/models.py:255-292](backend/fhort/tasks/models.py#L255-L292)): `garment_type` (FK), `code`, `name`,
  **`complexity_order`** (PositiveInteger — només ORDRE de complexitat), `active`,
  `base_size_definition`, `grading_rule_set`.
  → **NO** té `slots_*` ni minuts; `complexity_order` és un enter d'ordre, no el `complexitat`
  ('Alta'…) ni `patrons_aprox` ('12–14') de TipologiaModel.
- **On viu el temps de debò (NO a GarmentType/Item):** `TaskTimeEstimate` ([tasks/models.py:319-336](backend/fhort/tasks/models.py#L319-L336)) —
  *"Cel·la de la matriu d'estimació de temps: (garment_type_item × task_type) → minuts"*. La llegeix
  `lookup_estimated_minutes` ([services_g.py:11](backend/fhort/tasks/services_g.py#L11)) i la sembra `restructure_garment_types_v2`
  (*"TaskTimeEstimate: 9 estimacions de temps per item"*, [restructure_garment_types_v2.py:13](backend/fhort/pom/management/commands/restructure_garment_types_v2.py#L13),[:247](backend/fhort/pom/management/commands/restructure_garment_types_v2.py#L247)).
  → És la **matriu de temps VIVA**, però de forma **diferent** (item×task_type→minuts) i sembrada amb
  valors **hardcoded** al command, **NO derivats de TipologiaModel**. *(Els `slots_*` de [Model](backend/fhort/models_app/models.py#L257-L260)
  són per-instància, tampoc venen de TipologiaModel.)*

## C2 — Correspondència de dades (la prova real)
- **Mapeig FK:** de les **57** files, **0 tenen `garment_type`** (totes `None`); **0 GarmentType
  distints** enllaçats. → La FK sortint `garment_type→GarmentType` **mai es va poblar**; les files són
  master-data **autònoma**, indexada només per `codi`/`familia_codi` (no per GarmentType).
- **Contingut real (5 exemples, família ABR "Abrics"):**
  | codi | familia / codi | complexitat | patrons_aprox | slots (cad·dig·zero·proto) | garment_type |
  |---|---|---|---|---|---|
  | TM-ABR-0001 | Abrics i Roba d'Abric / ABR | Alta | 12–14 | 3.0 · 4.0 · 5.5 · 1.5 | **None** |
  | TM-ABR-0002 | " / ABR | Alta | 12–16 | 3.5 · 5.0 · 6.5 · 1.5 | None |
  | TM-ABR-0003 | " / ABR | Alta | 10–13 | 3.0 · 4.0 · 5.5 · 1.5 | None |
  | TM-ABR-0004 | " / ABR | Alta | 12–14 | 3.0 · 4.0 · 5.5 · 1.5 | None |
  | TM-ABR-0005 | " / ABR | Alta | 12–16 | 3.5 · 5.0 · 6.5 · 1.5 | None |
- **Comparació imatge ja migrada vs única còpia:** **no es pot comparar per FK** (cap enllaç). I com que
  GarmentType/Item **no tenen aquests camps** (§C1), no hi ha on comparar-los → la dada
  (slots-per-família/ruta + complexitat + patrons) **divergeix/és absent** a GarmentType/Item: **viu
  NOMÉS a TipologiaModel**.

## C3 — Rastre Frappe / origen
- **Cap rastre de codi** que lligui TipologiaModel a una font Frappe o a un altre canònic. Els hits
  "Frappe" del repo són **comentaris genèrics** d'altres mòduls (*"Equivalent to Frappe's Server
  Scripts"* [models_app/signals.py:3](backend/fhort/models_app/signals.py#L3); *"Equivalent to … Frappe's api.py"* [pom/services.py:3](backend/fhort/pom/services.py#L3)) —
  **no toquen tipologia**.
- `tipologia_confirmada` ([models_app/migrations/0030](backend/fhort/models_app/migrations/0030_importsession.py#L34)) és FK a `tasks.GarmentTypeItem`, **no** a TipologiaModel.
- Cap command/servei d'import sembra TipologiaModel (coherent amb §B2: les 57 files es van carregar
  **fora de banda** — els codis `TM-ABR-####` + famílies suggereixen una importació de master-data
  externa, però **sense rastre al codi**). → S'anota com a **origen extern no traçable al repo**.

## C4 — Veredicte d'export (FET, no decisió)
**💡 (b) EXPORT PREVI.** La imatge **NO** és a GarmentType/Item: els camps quantitatius de
TipologiaModel (`slots_cad_client/digitalitzacio/des_de_zero/conf_proto…`, `complexitat`,
`patrons_aprox`) **no existeixen** en cap dels dos, i la matriu de temps viva (`TaskTimeEstimate`) té
**una altra forma** (item×task_type→minuts) sembrada amb valors propis. Les **57 files són l'única
còpia** d'aquest dataset família-nivell (slots de temps per ruta de producció + rang de patrons +
complexitat), i ni tan sols estan enllaçades a un GarmentType (gt=None). Encara que siguin **codi-mort**
(§B: 0 consumidors) i el DROP sigui net a nivell d'esquema (cap FK entrant, §B5), **la DADA no és
recuperable d'enlloc** → si pot informar la **futura matriu de temps** (p.ex. seed família→ruta o
calibratge de `TaskTimeEstimate`), cal **exportar les 57 files a fixture/CSV abans del DROP**.
*No és (a) DROP NET* perquè la dada no viu duplicada a GarmentType/Item. Decisió d'exportar o descartar:
de producte (Patró C); el fet és que **és l'única còpia**.

### Actualització del tancament 3b (matís d'export)
- `Model.estat`: DROP **net** (cap dada única que perdre — és estat derivable).
- `TipologiaModel`: DROP **net d'esquema** (cap FK entrant) **PERÒ amb dada única** → **export previ
  recomanat** de les 57 files (l'única còpia dels slots família×ruta), no perquè el constraint ho
  exigeixi sinó perquè la informació no viu enlloc més.
