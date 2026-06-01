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
- **Nota dates:** es desen UTC (USE_TZ, Europe/Madrid). El front de planificació pinta des del MOTOR (local);
  NO barrejar amb l'UTC del serializer de tasca.

### Catàleg TaskType (9 canòniques, tenant)
pattern_digit, pattern_cad (default_order 20), pattern_hand, scaling, marking, tech_sheet (default_order 60),
bom, pom, grading (name "Taula de talles"). `default_order` reals verificats (NO assumir).

---

## EN CURS — Front de planificació
**Decisió de Gantt/Calendar:** SVAR core MIT (`wx-react-gantt` + `wx-react-calendar`), React 19 OK. El core
MIT (timeline/drag/dependències/virtualització milers de tasques) és suficient; les features PRO
(working-calendar/auto-scheduling) NO calen perquè el motor és nostre. Frappe Gantt = pla B (100% lliure,
menys potent amb volum). Resta (DHTMLX/Bryntum/DevExtreme) = de pagament, descartades.

**4 trams:**
- **Tram 0 (backend mini, EN CURS):** exposar `planned_*` al `ModelTaskSerializer` + completar `endpoints.js`
  (preview/apply/company-calendar/jornada/absencies). Desbloquejant. Additiu, sense migració.
- **Tram 1:** instal·lar SVAR + config "Calendari d'empresa" (SVAR Calendar) a Configuració.
- **Tram 2:** pantalla Planificació — carpetes Pendents (`<ModelPickerList>` extret del Kanban + pop-up
  tècnic/tasques) / Assignades (llista) + `plan/compute`.
- **Tram 3:** Gantt (SVAR) amb drag → `plan/preview` → modal acceptació → `plan/apply` + vista tècnic
  read-only en DIES.

**Menú:** "Planificació" = subgrup de Projectes; "Calendari d'empresa" = fill de Configuració.

---

## PENDENTS / DEUTE ANOTAT (no urgents)
- **Col·lecció:** NO existeix camp al Model → requereix camp nou + migració + poblar + filtre. Ajornat
  (es farà quan es refaci el Model).
- **Assignació a ModelSheet:** la cara "per model" de l'assignació, per quan es refaci ModelSheet (ara
  l'assignació la cobreix el motor: assignar = col·locar a la cua = planificar).
- **Auth per email:** ara login per username; tram futur transversal.
- **Endurir `transition`:** que comprovi `request.user == assignee` (avui la UI ho amaga però el backend no
  ho força).
- **Code-splitting (React.lazy):** bundle ~719 kB i pujant. Deute tècnic.
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

## REGISTRE DE COMMITS (sessió 2026-06-01, branca main)
- Permisos/Usuaris/Kanban: 55ed54a, 50c668f, … , a0ac4b0 (agregador), 19377b9 (ordre+filtres),
  03faa51 (Kanban 5-col), b048904 (5 col iguals), be547ae (sort+filtres), ca6d1f5 (scroll infinit+Responsable gated).
- Sprint A: 702cd5d, d8e2693, 09ba161.
- Sprint B: 88ed31f, c1bffd2, e73efb2.
