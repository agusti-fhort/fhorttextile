# ESTAT_PROJECTE — FHORT Textile Tech (Capa de Projecte)

> **Actualitzat:** 2026-06-01 · **Servidor:** 178.105.217.125 (fhorttextile.tech, tenant `fhort`)
> **Stack:** Django 6 + django-tenants + PostgreSQL + DRF + JWT · React 19.2.6 + Vite + Nginx
> **Repo únic:** `agusti-fhort/fhorttextile`, branca `main`, a `/var/www/fhort-textile` (front + backend).
> **Servei:** `fhort.service` (Gunicorn). Intèrpret: `backend/venv/bin/python`.
> **Llengua:** treball en català · codi/UI anglès primari, català subtítol.
> **ZONES INTOCABLES:** `/var/www/assessment`, `/trading`, `/webs` (+ Nginx). NOMÉS `/var/www/fhort-textile`.
>   (NO confondre amb el servidor 178.105.48.204 = ERP Frappe, màquina diferent; ni amb `fhortclinic`, projecte diferent.)

---

## MÈTODE DE TREBALL (rodat, respectar sempre)
- Diagnosi read-only → confirmació Agus → una peça → `manage.py check` / `npm run build` → un commit per peça.
- **Verificar `git log -1` després de CADA commit** (un commit es va perdre un cop i es va detectar tard).
- `git add` SELECTIU (repo únic: front i backend conviuen; no fer `git add .`).
- Migracions: ensenyar el fitxer de `makemigrations` abans de `migrate_schemas --tenant`; **auditar columnes
  reals** a la BD després (no fiar-se del missatge OK — quirk django-tenants).
- Peces que calculen dates/permisos: **provar amb sortida literal** i amb usuari sense permís (Montse
  technician), no només amb admin. Restart `fhort.service` després de canvis de backend.
- Documents de traspàs a `/root/fhort-sessions/` + mantenir aquest fitxer.

---

## ESTAT GENERAL — què està FET i desplegat

### 1. Capa de permisos (Opció A, sense migració)
- `capabilities.py`: `execute_tasks`, `define_tasks`, `schedule_fittings`, `close_gates`, `view_team_tasks`,
  `manage_users`, `configure`. `get_capabilities` = (ROLE_CAPABILITIES[rol] | grant) − revoke, des de
  `UserProfile.permisos` JSON `{grant, revoke, tasks}`. Allow-list de tipus de tasca per usuari (`tasks`),
  deny per defecte, bypass admin.
- Rols: technician {execute_tasks} · product_manager (+define_tasks +schedule_fittings) ·
  manager (+close_gates +view_team_tasks) · admin (ALL +manage_users +configure).
- Row-level scope a `ModelTaskViewSet.get_queryset` (sense `view_team_tasks` → només assignee propi).
- Enforcement per task_type: `define-tasks` (400) + `transition` (403), validat contra l'assignee.

### 2. Usuaris i rols (front, `/configuracio/usuaris`, gated manage_users)
- Matriu (abast/gestió via grant/revoke + tasques via permisos.tasks), filtres, bulk amb confirmació.
- Alta d'usuari (modal; login per USERNAME, password l'escriu l'admin). `UserViewSet`: List/Retrieve +
  PATCH + CREATE (create_user + signal crea profile) + `users/bulk/`.
- Usuari de prova: **Montse** (technician, user_id 13, password `Prova1234`).

### 3. Agregador by-model + Kanban mestre-detall (front, complet)
- `GET model-task-items/by-model/`: scope reusat, paginat, `?search=` (codi+nom), `?all=`,
  `?ordering=` (whitelist: nom_prenda, codi_intern, any, temporada, prioritat, data_entrada, data_objectiu,
  data_tancament, fase_actual, estat), filtres `temporada/estat/fase_actual/responsable(me)/garment_type/any/prioritat`.
  Files: `{model_id, model_codi, model_nom, fase, counts{pending,paused,in_progress,done}, prioritat,
  temporada, estat, data_objectiu, responsable_id}`.
- `KanbanTasks.jsx`: **5 columnes** (Models crema #fdf6ee + Pending/Paused/InProgress/Done blanques).
  Columna 1 cercable/ordenable/filtrable amb **scroll infinit**; selecció model → tasques en 4 estats.
  Filtre Responsable gated `view_team_tasks` (amagat per a tècnic). Reaprofita TaskCard/transicions/timer/
  toast 1-InProgress/403. Cartes de gate (Prioritat A) sintètiques de `gates/ready/` → `models/gate`.

### 4. Motor de planificació — BACKEND COMPLET (sprints A+B)
**Decisió clau:** motor determinista propi + llibreries de calendari (workalendar + python-networkdays) +
SVAR MIT per pintar. NO solver (Timefold descartat: cal JVM, lent en Python; el problema és determinista).
Fusió tram 8 (Planificador) + assignació en UN motor; `plan/compute` antic per-model-en-sèrie JUBILAT.

**Sprint A — calendari laboral (porta migracions):**
- `CompanyCalendar` (singleton/tenant): `horaris` JSON (trams per dia + pauses) + `festius_extra`.
  Horari REAL FHORT: dl-dj 08:00-13:00/14:00-17:00 · dv 08:00-15:00 · festius workalendar Catalunya.
- `UserProfile.jornada_override` (JSON, null = hereta empresa). Model `Absencia` (rangs simples).
- `calendar_service.py`: `next_working_slot` + `add_working_minutes(profile, start, minutes)` — primitiva
  provada (salta pauses/cap de setmana/festius CAT/absències). Endpoints `company-calendar/`,
  `users/<id>/jornada/`, `absencies/` (gated configure).
- Commits: 702cd5d, d8e2693, 09ba161.

**Sprint B — motor (porta migració):**
- `ModelTask.planned_start/planned_end/planned_locked` (migració 0015, columnes auditades).
- `scheduler_service.py`: motor determinista `schedule(qs, now, save)` → `{placements, warnings, models}`.
  Cua per tècnic; ordre prioritat (1=urgent) → data_objectiu → codi_intern; dins model per `default_order`.
  Durada = snapshot `estimated_minutes`. Locked = punt fix (tasques s'empenyen senceres al voltant).
  Warning si `planned_end > data_objectiu` o sense estimació/assignee. PROVAT amb dates reals.
- `plan_service.py` + endpoints `plan/compute` (refactor) + `plan/preview` (save=False, NO muta BD) +
  `plan/apply` (locked=True + desa). Tots gated `configure` (deny 403 provat amb Montse).
- Commits: 88ed31f, c1bffd2, e73efb2.
- **Assignació + recàlcul per cua sencera (commit 6e81cc7):** `assign_model` / `unassign_model` +
  `recompute_for_technicians` (recalcula TOTA la cua no-Done del/s tècnic/s afectat/s, com `apply` →
  **evita solapaments** amb la feina ja assignada; no recalcula "només el model"). Scheduler **Done-safe**:
  `schedule()` exclou `status='Done'` defensiu (no depèn dels cridadors). Endpoints `POST models/<id>/assign/`
  `{assignee_id, task_ids?}` i `POST models/<id>/unassign/` (treu assignee + buida `planned_*` + neteja
  `predicted_*`), gated `define_tasks`. Reassignar una tasca (PATCH `assignee` a `model-task-items`)
  recalcula les cues dels **dos** tècnics (el vell i el nou). Tasques **Done IMMUTABLES** (autor + finished_at
  + dates) en tots els casos — provat amb sortida literal.
- **Nota dates:** es desen UTC (USE_TZ, Europe/Madrid). El front de planificació pinta des del MOTOR (local);
  NO barrejar amb l'UTC del serializer de tasca.

### Catàleg TaskType (9 canòniques, tenant)
pattern_digit, pattern_cad (default_order 20), pattern_hand, scaling, marking, tech_sheet (default_order 60),
bom, pom, grading (name "Taula de talles"). `default_order` reals verificats (NO assumir).

---

## FRONT DE PLANIFICACIÓ (trams 0–2 FETS · tram 3 pendent)
**Decisió de Gantt/Calendar:** SVAR core MIT (`wx-react-gantt` + `wx-react-calendar`), React 19 OK. El core
MIT (timeline/drag/dependències/virtualització milers de tasques) és suficient; les features PRO
(working-calendar/auto-scheduling) NO calen perquè el motor és nostre. Frappe Gantt = pla B (100% lliure,
menys potent amb volum). Resta (DHTMLX/Bryntum/DevExtreme) = de pagament, descartades.

**Trams (0→2 FETS; 3 pendent):**
- ✅ **Tram 0 (backend mini):** `planned_start/end/locked` exposats al `ModelTaskSerializer` (read-only;
  comentari de fus UTC). `endpoints.js` complet: `plan.compute/preview/apply/snapshots`, `companyCalendar`,
  `jornada`, `absencies`. Commits 1ca18a4, 6662a26.
- ✅ **Tram 1A:** SVAR instal·lat (`wx-react-gantt` + `wx-react-calendar`, MIT, React 19 net, sense
  conflictes peerDeps). Pantalla **Calendari d'empresa** (`/configuracio/calendari`, gated `configure`,
  403-safe): editor de **trams horaris per dia** (7 files, inputs hora, +afegir/treure, validació
  inici<fi/solapaments). Commits 1b343f8, 4d60e7a.
- ✅ **Tram 1B:** secció **festius extra** (editor de dates) a la mateixa pantalla; desar envia
  `{horaris, festius_extra}` (anti-regressió verificada: no esborra horaris). Commit 3995dea.
  NOTA: `festius_extra` és **llista de dates ISO** (sense descripció; afegir-la requeriria canvi backend).
  **Jornada-per-tècnic i absències AJORNATS conscientment** (calendari únic per a tothom; el motor ja els
  suportaria). Vacances = es gestionen movent la data del model.
- ✅ **Tram 2:** pantalla **Planificació** (`/planificacio`, gated `define_tasks`/`configure`, 403-safe).
  Carpetes **Pendents** (models amb no-Done sense tècnic) / **Assignades** (totes les no-Done amb tècnic).
  Assignar model (bulk) → **pop-up** (tècnic + tasques opcionals) → `assign` → **compute automàtic**.
  Assignades: tècnic(s), data inici/temps estimat/data fi previstos, **flag "en risc"**
  (`planned_end > data_objectiu`), **mestre-detall** a tasques amb **autor de les Done** (col·laboració
  traçada). Desassignar (Done intactes). Reassignar tasca. Reaprofita el patró cerca/filtres del Kanban.
  Commits f1d02a2 (fix), e82bef1 (pantalla). Verificat visualment (admin + Montse 403).
- ⏳ **Tram 3 (en curs):**
  - ✅ **Peça 1 — code-splitting per ruta (FETA):** `React.lazy` + `<Suspense>` a `App.jsx` (Login i Shell
    eager; les 27 pàgines restants lazy). Bundle inicial **746 kB → 394 kB (-47%)**, gzip 207→125 kB; 27
    chunks de pàgina sota demanda; l'avís Vite >500 kB desaparegut. Abast estricte a `App.jsx` (cap canvi de
    rutes/auth/layout). Commit **4787b51**.
  - ⏳ Resta del Tram 3: Gantt (SVAR) amb drag → `plan/preview` → modal acceptació → `plan/apply` +
    **vista tècnic en DIES** + indicadors de direcció (càrrega per tècnic, models en risc, cost previst =
    Σ temps×cost_hora). NOTA: el `manualChunks` de vendor (`vite.config.js`) queda per a la **Peça 2 (Gantt
    SVAR)** — aïllar React/router/SVAR en un chunk de vendor d'un sol cop (l'index inicial encara porta tot
    el vendor; el code-splitting per ruta només n'ha tret les pàgines).

**LLIÇÓ CLAU — `assignee` és FK a `UserProfile`, NO a `User`:** mai assumir `User.id == UserProfile.id`
(coincideix avui per casualitat amb 2 usuaris; divergiria en escalar). Els serializers d'usuari
(`UserListSerializer`/`UserAdminSerializer`) ara exposen **`profile_id`**; el front mapeja i envia
`profile_id` com a `assignee_id` (selector, mapa de noms, payload) → desacoblat de `User.id`. Fix f1d02a2.

**Menú:** "Planificació" = fill del grup Tasques (gated `define_tasks`/`configure`); "Calendari d'empresa" =
fill de Configuració (gated `configure`).

---

## PENDENTS / DEUTE ANOTAT (no urgents)
- **Col·lecció:** NO existeix camp al Model → requereix camp nou + migració + poblar + filtre. Ajornat
  (es farà quan es refaci el Model).
- **Assignació a ModelSheet:** la cara "per model" de l'assignació, per quan es refaci ModelSheet (ara
  l'assignació la cobreix el motor: assignar = col·locar a la cua = planificar).
- **Auth per email:** ara login per username; tram futur transversal.
- **Endurir `transition`:** que comprovi `request.user == assignee` (avui la UI ho amaga però el backend no
  ho força).
- ~~**Code-splitting (React.lazy):** bundle ~747 kB i pujant. CRÍTIC quan entri el Gantt (Tram 3).~~
  **RESOLT** (Tram 3 peça 1, commit 4787b51): 746→394 kB (-47%), pàgines lazy. Pendent la peça 2:
  `manualChunks` de vendor a `vite.config.js` per aïllar React/router/SVAR (es farà amb el Gantt).
- **product_manager té `define_tasks` però NO `view_team_tasks`** → a Planning veu només les seves tasques
  (scope row-level). Decidir si product_manager ha de tenir `view_team_tasks` per assignar a l'equip.
- **Deep-link a fred a ruta protegida rebota a `/login`** (cursa `initAuth` al useEffect vs `ProtectedRoute`
  que renderitza amb `isAuthenticated:false`). Afegir estat de loading inicial / inicialitzar des de
  localStorage. Detectat fent les captures de verificació.
- **Festius extra amb descripció:** avui `festius_extra` és llista de dates ISO; afegir motiu = canvi backend
  menor (objectes en comptes de cadenes + ajustar el validador).
- **Botons Kanban a columnes estretes:** "Finalitzar" va just; resoldre en enriquir les fitxes del Kanban.
- **Garment Types finder 3 columnes** (POMs, tram futur).
- **Trams 5 (Calendari fittings: schedule→open, per dia), 6 (Producció mostres: request-production + gate
  obligatori)** — diagnosticats, no construïts.

---

## DECISIONS DE PRODUCTE CLAU (registre)
- Hub "Projectes" (Models, Kanban, Calendari, Producció mostres, Planificador). POMs = config tècnica.
  Configuració = General + Tipus de tasca + Proveïdors + Usuaris i rols + Calendari d'empresa.
- Kanban model-cèntric (primer el model, després les seves tasques); pensat per a escala (600 models).
- Usabilitat = filtrar i triar simple (sino entra en desús): cerca + ordre + filtres + scroll infinit.
- Motor: assignar = planificar (un sol motor). Tècnic veu dies; responsable veu Gantt amb dates/hores.
- Reposició = sobreescriu amb advertència + acceptació (drag → preview → apply); locked = punt fix.
- Prioritat: `Model.prioritat` 1-5 tal com està (1=urgent), sense A/B/C, sense migració.

---

## DECISIONS DE PRODUCTE / PRICING (registre nou)
- **Posicionament:** SaaS de **nínxol tècnic** (oficina tècnica digital + planificació de producció), **NO un
  PLM**. Complementa Centric/K3/Garem (que no fan la part tècnica), no competeix.
- **Comprador = direcció** (no el tècnic): valor = visibilitat de capacitat, dates i cost. *"No més dates de
  lliurament falses."* (Justifica els indicadors de direcció del Tram 3.)
- **Cost IA ~0,33 €/model** (trivial). Cost real = temps de suport (baix; es tecnifiquen processos coneguts).
- **Volums reals:** Brownie ~1.200 models/any; LOSAN ~2.400/any. Àncora de preu: ordre dels **30k€** (Garem).
  Model de preu: **tiers per volum anual + overflow per excés** (absorbeix l'estacionalitat).

---

## REGISTRE DE COMMITS (sessió 2026-06-01, branca main)
- Permisos/Usuaris/Kanban: 55ed54a, 50c668f, … , a0ac4b0 (agregador), 19377b9 (ordre+filtres),
  03faa51 (Kanban 5-col), b048904 (5 col iguals), be547ae (sort+filtres), ca6d1f5 (scroll infinit+Responsable gated).
- Sprint A (calendari): 702cd5d, d8e2693, 09ba161.
- Sprint B (motor): 88ed31f, c1bffd2, e73efb2; assign/unassign + recompute + Done-safe: 6e81cc7.
- Front planificació: 1ca18a4 + 6662a26 (Tram 0), 1b343f8 + 4d60e7a (Tram 1A), 3995dea (Tram 1B),
  f1d02a2 (fix profile_id) + e82bef1 (Tram 2 pantalla), 4787b51 (Tram 3 peça 1: code-splitting per ruta).
