# DIAGNOSI QUIRURGICA - Sembra POM + event de tancament de la tasca

Data: 2026-06-26  
Entorn: dev `/var/www/ftt-staging`  
Mode: READ-ONLY absolut. Unica escriptura: aquest document.

## 0. Marc carregat

FET: `METODE_AGENTS.md` defineix el patro de diagnosi com a "Read-only absolut" i demana fets amb `fitxer:linia`, sense opinions (`METODE_AGENTS.md:25-34`). Tambe fixa "MAI push, MAI deploy" i scope estricte (`METODE_AGENTS.md:82-90`).

FET: `DECISIONS.md` fixa la sobirania de dades: la plantilla sembra i el model posseeix valors/nomenclatura (`DECISIONS.md:54-55`). Tambe fixa que propagar es acte conscient i mai automatic (`DECISIONS.md:57-63`), i que a HEAD conviuen `MeasureGrid` per check/fitting/escalat i `EditableTable` per entrada/estructura POM (`DECISIONS.md:156-157`).

FET: en el `DECISIONS.md` carregat, la linia 57 no diu literalment "size_check/pom: auto-Done lligat a un esdeveniment de domini discret"; la linia 57 diu "Propagar = ACTE CONSCIENT" (`DECISIONS.md:57-63`). Per tant, aquesta diagnosi contrasta el codi viu, no una frase literal present en aquesta versio del document.

## 1. On viu fisicament la sembra avui

FET: la ruta de la tasca `pom` al WorkPlan envia a `/models/<id>?tab=Mesures&mode=entry`; el comentari diu explicitament que "Definicio POM" obre el TAB Mesures en mode ENTRADA/genesi i que ja no usa pagina standalone (`frontend/src/components/model/WorkPlan.jsx:24-30`).

FET: `ModelSheet` llegeix `tab`, `task_id` i `mode=entry`; `entryMode` es `sp.get('mode') === 'entry'` (`frontend/src/pages/ModelSheet.jsx:87-95`).

FET: el mateix `ModelSheet` decideix, en entrar al tab Mesures, si mostra entrada o treball: `verge = !taulaRows.some(r => r.base_value_cm != null)` i `setMesuresEntry((verge || entryMode) && !taskParam)`; `task_id` forca treball, no entrada (`frontend/src/pages/ModelSheet.jsx:136-155`).

FET: quan `activeTab === 'Mesures'`, `ModelSheet` renderitza `MeasuresEntryPanel` si `mesuresEntry && editing !== 'Mesures'`; en cas contrari renderitza `CheckMeasureEditor` (`frontend/src/pages/ModelSheet.jsx:378-423`).

FET: `MeasuresEntryPanel` declara que es "flux d'ENTRADA/genesi de mesures" portat dins el TAB Mesures, cobreix buit/seed/import/manual, i exclou `size_check` perque aquest es flux de treball (`frontend/src/components/model/MeasuresEntryPanel.jsx:9-18`).

FET: `MeasuresEntryPanel` crida `materialitzar-poms` en dues situacions: confirmacio de l'oferta de sembra (`frontend/src/components/model/MeasuresEntryPanel.jsx:54-67`) i auto-materialitzacio quan no hi ha files i l'item no porta valors base (`frontend/src/components/model/MeasuresEntryPanel.jsx:115-121`).

FET: `MeasuresEntryPanel` no es una superficie propia independent: la seva entrada actual depen del tab Mesures i del flag `mesuresEntry` gestionat per `ModelSheet` (`frontend/src/pages/ModelSheet.jsx:136-155`, `frontend/src/pages/ModelSheet.jsx:378-382`).

FET: la sembra no esta acoblada estrictament a "obrir qualsevol tab Mesures"; esta acoblada a "tab Mesures en mode entrada" o "tab Mesures verge sense `task_id`". Aixo passa per `verge || entryMode` i `!taskParam` (`frontend/src/pages/ModelSheet.jsx:149-153`).

FET: si se separa POM en pantalla propia, cal moure o reutilitzar aquests punts: la ruta `pom -> ?tab=Mesures&mode=entry` (`frontend/src/components/model/WorkPlan.jsx:24-30`), la decisio `mesuresEntry` (`frontend/src/pages/ModelSheet.jsx:136-155`), el lifecycle `enterEdit('Mesures','pom')` (`frontend/src/pages/ModelSheet.jsx:186-200`), i les crides de sembra/save dins `MeasuresEntryPanel` + `EditableTable` (`frontend/src/components/model/MeasuresEntryPanel.jsx:54-67`, `frontend/src/components/EditableTable/EditableTable.jsx:112-143`).

## 2. Com s'obre la tasca `pom` i que dispara

FET: WorkPlan mapeja `pom` a `?tab=Mesures&mode=entry` sense `task_id` (`frontend/src/components/model/WorkPlan.jsx:24-30`).

FET: en fer Play sobre una tasca propia, `playMine` calcula la ruta, fa `modelTasks.transition(task.id, { to_status: 'InProgress' })` si cal, i navega igualment a la ruta (`frontend/src/components/model/WorkPlan.jsx:216-230`).

FET: `modelTasks.transition` es el client HTTP de `POST /api/v1/model-task-items/<id>/transition/` amb `{to_status}` (`frontend/src/api/endpoints.js:157-173`), i la view backend aplica `transition_task` (`backend/fhort/tasks/views_b.py:382-410`).

FET: el servei `transition_task` permet `Pending -> InProgress`, `Paused -> InProgress`, `InProgress -> Paused/Done`, i `Done -> InProgress` (`backend/fhort/tasks/services_c.py:10-16`).

FET: en entrar a `InProgress`, `transition_task` obre timer, fixa `started_at` si era null i autoassigna si cal (`backend/fhort/tasks/services_c.py:58-83`).

FET: en entrar a `InProgress`, `transition_task` mou el model de `Pending` a `Dev` (`backend/fhort/tasks/services_c.py:89-95`) i, si `consumption_started_at` era null, el fixa i crea `ConsumptionRecord` de meritacio (`backend/fhort/tasks/services_c.py:97-118`). Per tant, obrir POM com a primera tasca pot meritar.

FET: a mes del Play del WorkPlan, `ModelSheet` tambe te una "porta-menu" `models.openTask(id, code)` que crea-si-falta i posa la tasca En curs (`frontend/src/pages/ModelSheet.jsx:157-166`). El client HTTP es `POST /api/v1/models/<id>/open-task/ {code}` (`frontend/src/api/endpoints.js:31-34`).

FET: `open_model_task_view` crea la `ModelTask` si falta, status inicial `Pending`, i despres la passa a `InProgress` reutilitzant `transition_task`; retorna `{task_id, code, created, status}` (`backend/fhort/tasks/views_b.py:466-522`).

FET: quan `ModelSheet` detecta `?mode=entry` sense `task_id`, crida `enterEdit('Mesures','pom')`; el comentari diu que aixo resol el gap de POM sense `task_id` i registra la tasca a `activeTaskRef` (`frontend/src/pages/ModelSheet.jsx:242-253`).

FET: `enterEdit` crida `models.openTask`, guarda `editTaskId`, registra `activeTaskRef.current = task_id`, i si `tab === 'Mesures' && code === 'pom'` activa `setMesuresEntry(true)` en comptes de `editing='Mesures'` (`frontend/src/pages/ModelSheet.jsx:186-200`).

FET: en sortir d'entrada/edicio, `exitEdit` crida `pauseActiveTask`, que fa `modelTasks.transition(tid, { to_status: 'Paused' })`, neteja refs i apaga `mesuresEntry` (`frontend/src/pages/ModelSheet.jsx:180-206`). Tambe es pausa en canvi de tab o desmuntatge (`frontend/src/pages/ModelSheet.jsx:207-213`).

## 3. Com es tanca la tasca `pom`

FET: el WorkPlan ofereix Stop com a gest huma explicit: el comentari diu "Stop = gest huma explicit 'feta, 100%' (MAI automatic)" i el codi fa `doTransition(task, 'Done')` (`frontend/src/components/model/WorkPlan.jsx:267-269`).

FET: a nivell backend, `Done` nomes es pot assolir des de `InProgress` (`backend/fhort/tasks/services_c.py:10-16`). En transicio `InProgress -> Done`, el servei tanca timer i fixa `finished_at` (`backend/fhort/tasks/services_c.py:76-80`), i despres alimenta estadistica de temps real (`backend/fhort/tasks/services_c.py:125-129`).

FET: existeix una porta backend que auto-tanca la tasca POM, pero no es `materialitzar-poms` ni `set-measurements`; es `POST /api/v1/models/<id>/tancar-taula/`, registrat a urls (`backend/fhort/models_app/urls.py:171-176`) i implementat a `close_table_view` (`backend/fhort/models_app/views.py:595-633`).

FET: `close_table_view` primer exigeix que existeixi almenys una `BaseMeasurement` activa amb `base_value_cm` no-null; si no, retorna error "Cal introduir mides abans de tancar la taula" (`backend/fhort/models_app/views.py:608-616`).

FET: si la taula es pot tancar, `close_table_view` crea/resol `SizeFitting`, crida `close_base`, i despres `_close_pom_task_for_model` dins una transaccio (`backend/fhort/models_app/views.py:618-626`).

FET: `_close_pom_task_for_model` diu explicitament que "en tancar la taula, la tasca POM del model passa a Done via transition_task"; si no hi ha tasca `pom` no fa res, si ja es `Done` es idempotent, i si esta `Pending/Paused` la passa primer a `InProgress` i despres a `Done` (`backend/fhort/models_app/views.py:636-658`).

FET: l'event discret existent per auto-Done de POM, doncs, es "tancar taula" (`/tancar-taula/`), no "desar base" ni "materialitzar". Aquest event tambe tanca la base de `SizeFitting`.

FET: `close_base` no es una simple marca de POM feta: si encara no hi ha `GradedSpec`, genera talles amb `generate_graded_specs`, i despres segella `base_tancada=True` / estat tancat (`backend/fhort/pom/services.py:238-252`, `backend/fhort/pom/services.py:277-285`). Aixo el fa mes madur que una simple sembra.

FET: el flux actual de `MeasuresEntryPanel` no crida `/tancar-taula/`: confirma la sembra amb `/materialitzar-poms/` (`frontend/src/components/model/MeasuresEntryPanel.jsx:54-67`) i la graella d'entrada desa amb `/set-measurements/` i `/reorder-measurements/` (`frontend/src/components/EditableTable/EditableTable.jsx:112-143`).

FET: `set_measurements_view` fa upsert de `BaseMeasurement`, aplica soft-delete via `keep_pom_ids`, i el comentari diu que la generacio de `GradedSpec` viu exclusivament a `generar-grading`; no tanca cap tasca (`backend/fhort/models_app/views.py:787-849`).

FET: `materialize_poms_view` crea o sembra `BaseMeasurement` des de l'item i retorna comptadors, pero no crida `_close_pom_task_for_model` ni `transition_task` (`backend/fhort/models_app/views.py:516-592`).

FET: l'unica crida frontend trobada a `/tancar-taula/` es a `ModelFabric`, despres de persistir teixit, i no en el flux POM del `ModelSheet` (`frontend/src/pages/ModelFabric.jsx:101-120`).

Conclusio factual: avui hi ha dues vies de tancament possibles:

- FET: Stop manual del WorkPlan: `InProgress -> Done` per decisio humana (`frontend/src/components/model/WorkPlan.jsx:267-269`).
- FET: auto-Done backend lligat a `/tancar-taula/`, que tanca SizeFitting/base i POM task en transaccio (`backend/fhort/models_app/views.py:595-658`).
- FET: el POM entry actual del ModelSheet no dispara cap d'aquestes en desar/materialitzar; en sortir, pausa (`frontend/src/pages/ModelSheet.jsx:180-206`, `frontend/src/pages/ModelSheet.jsx:378-382`).

## 4. Senyal "POM feta" vs "verge"

FET: avui el senyal frontend de "verge" al `ModelSheet` es purament de dades: cap `taulaRows` amb `base_value_cm != null` (`frontend/src/pages/ModelSheet.jsx:149-153`).

FET: `MeasuresEntryPanel` repeteix el mateix criteri: `verge = !rows.some(r => r.base_value_cm != null)`; si no es verge i `entryMode` esta actiu, no surt a consulta sino que obre selector per afegir/importar POMs (`frontend/src/components/model/MeasuresEntryPanel.jsx:90-103`).

FET: la taula backend retorna files de `BaseMeasurement` actives, amb `base_value_cm`, `nom_fitxa`, `ordre`, `origen`, regim i graded specs (`backend/fhort/models_app/views.py:675-738`). Per tant, "verge" actual vol dir "sense cap valor base", no "tasca POM no feta".

FET: durant POM en curs, abans de desar, el backend encara pot ser verge perque `EditableTable` nomes persisteix valors quan fa `POST /set-measurements/` (`frontend/src/components/EditableTable/EditableTable.jsx:112-135`). L'estat local de tecles no es un senyal global.

FET: existeix `ModelTask` amb `status` `Pending/Paused/InProgress/Done`, `started_at` i `finished_at`; una per tipus i model (`backend/fhort/tasks/models.py:103-140`).

FET: les tasques son consultables per API amb filtres `model`, `status`, `task_type`, `assignee` (`backend/fhort/tasks/views_b.py:41-47`), i el serializer exposa `task_type_code`, `status`, `started_at`, `finished_at`, etc. (`backend/fhort/tasks/serializers_b.py:13-35`). El client ja te `modelTasks.listByModel(modelId)` (`frontend/src/api/endpoints.js:157-164`).

FET: el `ModelSheet` actual no consulta `ModelTask` per decidir si Mesures es buit/entrada/treball; carrega nomes model i `/taula-mesures/` en el `Promise.all` inicial (`frontend/src/pages/ModelSheet.jsx:121-134`) i decideix amb `verge/entryMode/taskParam` (`frontend/src/pages/ModelSheet.jsx:136-155`).

FET: `activeTaskRef` distingeix "POM en curs ara" nomes dins la sessio de `ModelSheet`; no es un senyal persistent per a altres pantalles o recarregues (`frontend/src/pages/ModelSheet.jsx:173-185`, `frontend/src/pages/ModelSheet.jsx:242-253`).

💡 PROPOSTA (a validar): per separar sense contradiccio els tres estats demanats, el senyal no hauria de ser nomes `verge`; hauria de combinar estat de tasca i dades:

- `pom` inexistent/Pending + cap base amb valor => "POM mai feta / iniciar Definicio POM".
- `pom` InProgress/Paused => "POM en curs o interrompuda"; obrir pantalla de genesi, no tab Mesures de treball.
- `pom` Done + almenys una `BaseMeasurement.base_value_cm` no-null => "POM feta + base present"; tab Mesures treballable.

💡 PROPOSTA (a validar): si s'usa `pom Done` com a porta del tab Mesures, cal decidir que fer amb el cas avui possible "base amb valors pero POM Paused" provocat per desar `set-measurements` i sortir sense Stop ni `/tancar-taula/` (`frontend/src/components/EditableTable/EditableTable.jsx:112-143`, `frontend/src/pages/ModelSheet.jsx:201-206`).

## 5. Contradiccions potencials si es mou la sembra o es buida Mesures fins POM Done

FET: moure la sembra fora del tab Mesures trenca el routing actual si no es canvia `toolRoute`: `pom` avui navega a `?tab=Mesures&mode=entry` (`frontend/src/components/model/WorkPlan.jsx:24-30`).

FET: moure la sembra tambe ha de preservar la meritacio i el timer: `openTask`/`transition_task` son qui posen `InProgress`, fase `Pending -> Dev`, `consumption_started_at` i timer (`backend/fhort/tasks/views_b.py:466-522`, `backend/fhort/tasks/services_c.py:58-118`).

FET: si el tab Mesures passa a quedar buit fins que `pom` sigui `Done`, el flux actual pot deixar el model amb base desada pero POM `Paused`: `EditableTable` desa base (`frontend/src/components/EditableTable/EditableTable.jsx:112-143`) i `onMaterialized` del `ModelSheet` fa `exitEdit()`; `exitEdit` pausa, no tanca (`frontend/src/pages/ModelSheet.jsx:378-382`, `frontend/src/pages/ModelSheet.jsx:201-206`).

FET: fer auto-Done en "desar base" seria un canvi respecte al codi viu: `set_measurements_view` avui no tanca tasca i el seu comentari limita la funcio a upsert/soft-delete de `BaseMeasurement` (`backend/fhort/models_app/views.py:787-849`).

FET: fer servir l'auto-Done existent de `/tancar-taula/` tampoc es neutre: aquesta porta exigeix valors, tanca `SizeFitting` i pot generar `GradedSpec` si no existeixen (`backend/fhort/models_app/views.py:608-626`, `backend/fhort/pom/services.py:238-285`). Aixo barreja "POM feta" amb un event de maduresa/tancament de base mes fort.

FET: l'entrada `mode=entry` no ve nomes del WorkPlan; `ModelSheet` tambe pot obrir POM amb el boto intern "Editar mides", que crida `enterEdit('Mesures','pom')` (`frontend/src/pages/ModelSheet.jsx:391-404`). Aquesta etiqueta fa que el boto d'editar mesures obri POM/entrada, no `size_check`.

FET: `size_check` te un cami diferent: WorkPlan navega amb `?tab=Mesures&task_id=<id>` (`frontend/src/components/model/WorkPlan.jsx:31-33`), i `ModelSheet` consumeix aquest `task_id` posant `editing='Mesures'` i registrant `activeTaskRef` sense crear tasca nova (`frontend/src/pages/ModelSheet.jsx:225-240`).

FET: per tant, la frontera real actual es:

- `pom` sense `task_id` / `mode=entry` => genesi amb `MeasuresEntryPanel` + `EditableTable` (`frontend/src/pages/ModelSheet.jsx:242-253`, `frontend/src/pages/ModelSheet.jsx:378-382`).
- `size_check` amb `task_id` => treball amb `CheckMeasureEditor` (`frontend/src/pages/ModelSheet.jsx:225-240`, `frontend/src/pages/ModelSheet.jsx:418-423`).
- `verge` sense `task_id` => tambe genesi dins Mesures per criteri de dades (`frontend/src/pages/ModelSheet.jsx:136-155`).

💡 PROPOSTA (a validar): si la decisio de producte es "POM es pantalla propia i Mesures buit fins POM feta", cal introduir un event de domini discret mes ajustat que `/tancar-taula/`, o reutilitzar-lo nomes si s'accepta que "POM feta" equival a tancar base/SizeFitting. El codi viu no te encara un event "base sembrada i confirmada" separat de `set-measurements` ni de `tancar-taula`.

💡 PROPOSTA (a validar): el senyal robust de maduresa hauria de ser doble: `ModelTask(pom).status === Done` per meritacio/proces, i existencia de `BaseMeasurement` amb valor per integritat de dades. Cap dels dos sol resol tots els casos actuals.

## 6. Resposta curta a les preguntes

FET: la sembra viu avui fisicament sota el tab Mesures, en `MeasuresEntryPanel`, activada per `?mode=entry` o per model verge (`frontend/src/components/model/WorkPlan.jsx:24-30`, `frontend/src/pages/ModelSheet.jsx:136-155`, `frontend/src/pages/ModelSheet.jsx:378-382`).

FET: obrir `pom` dispara `InProgress`, timer, fase `Pending -> Dev` i meritacio si es la primera tasca, via `transition_task` o `open-task` (`backend/fhort/tasks/services_c.py:58-118`, `backend/fhort/tasks/views_b.py:466-522`).

FET: `activeTaskRef` es registra per `pom` via `?mode=entry` gracies a `enterEdit('Mesures','pom')`, i es pausa en sortir/desmuntar (`frontend/src/pages/ModelSheet.jsx:180-206`, `frontend/src/pages/ModelSheet.jsx:242-253`).

FET: no hi ha auto-Done de POM en `materialitzar-poms` ni en `set-measurements`; el flux actual de POM entry pausa en sortir si no hi ha Stop manual (`backend/fhort/models_app/views.py:516-592`, `backend/fhort/models_app/views.py:787-849`, `frontend/src/pages/ModelSheet.jsx:201-206`).

FET: si existeix auto-Done per POM, es a `/tancar-taula/`, event "tancar taula/base", no "desar base"; i aquesta porta actualment es cridada des de `ModelFabric`, no des de `MeasuresEntryPanel` (`backend/fhort/models_app/views.py:595-658`, `frontend/src/pages/ModelFabric.jsx:101-120`).

FET: el senyal actual "verge" es nomes `base_value_cm` absent; no distingeix POM mai iniciada, POM en curs, POM pausada o POM feta (`frontend/src/pages/ModelSheet.jsx:149-153`, `frontend/src/components/model/MeasuresEntryPanel.jsx:90-103`).

💡 PROPOSTA (a validar): per fer el tab Mesures buit sense contradiccio, usar `ModelTask(pom)` com a senyal de proces i `BaseMeasurement` com a senyal d'integritat. Abans cal definir quin event exacte passa POM a `Done`: Stop manual, `/tancar-taula/`, o un nou "confirmar POM" separat de tancar base/escalat.
