import client from './client'

export const auth = {
  login: (username, password) => client.post('/api/token/', { username, password }),
}

export const models = {
  list: (params) => client.get('/api/v1/models/', { params }),
  get: (id) => client.get(`/api/v1/models/${id}/`),
  create: (data) => client.post('/api/v1/models/', data),
  update: (id, data) => client.patch(`/api/v1/models/${id}/`, data),
  remove: (id) => client.delete(`/api/v1/models/${id}/`),
  // Capa de Projecte: definir tasques d'un model i avançar fase (gate del responsable).
  defineTasks: (id, data) => client.post(`/api/v1/models/${id}/define-tasks/`, data),   // {task_type_ids:[...]}
  gate: (id, data) => client.post(`/api/v1/models/${id}/gate/`, data),                   // {to_phase} o {to_phases:[...]}
  // Tram 2 planificació (gated define_tasks): assigna les no-Done a un tècnic + compute de cua
  // sencera; unassign treu tècnic + buida planned_*. Done sempre intactes.
  assign: (id, body) => client.post(`/api/v1/models/${id}/assign/`, body),   // {assignee_id, task_ids?}
  unassign: (id) => client.post(`/api/v1/models/${id}/unassign/`),
}

// Fitxers del model (read-only) — panell info de fitting (5B.6-B1).
export const modelFitxers = {
  list: (params) => client.get('/api/v1/model-fitxers/', { params }),
}

export const poms = {
  list: (params) => client.get('/api/v1/poms/', { params }),
}

// CRUD complet (GarmentTypeViewSet és ModelViewSet). S'usa al tram 7 (finder 3 columnes).
export const garmentTypes = {
  list: (params) => client.get('/api/v1/garment-types/', { params }),
  get: (id) => client.get(`/api/v1/garment-types/${id}/`),
  create: (data) => client.post('/api/v1/garment-types/', data),
  update: (id, data) => client.patch(`/api/v1/garment-types/${id}/`, data),
  remove: (id) => client.delete(`/api/v1/garment-types/${id}/`),
}

export const garmentGroups = {
  list: (params) => client.get('/api/v1/garment-groups/', { params }),
}

export const sizeSystems = {
  list: (params) => client.get('/api/v1/size-systems/', { params }),
}

export const sizeDefinitions = {
  list: (params) => client.get('/api/v1/size-definitions/', { params }),
}

export const gradingRuleSets = {
  list: (params) => client.get('/api/v1/grading-rule-sets/', { params }),
}

export const gradingRules = {
  list: (params) => client.get('/api/v1/grading-rules/', { params }),
}

// Capa de Projecte — instàncies ModelTask (model-task-items/, ModelViewSet + row-level scope).
// Filtres reals del backend: ?model & status & task_type & assignee.
export const modelTasks = {
  list: (params) => client.get('/api/v1/model-task-items/', { params }),
  listByModel: (modelId) => client.get('/api/v1/model-task-items/', { params: { model: modelId } }),
  // Agregador columna 1 del Kanban: ?search & ?all (per defecte només models amb tasca no-Done).
  // Resposta paginada: [{model_id, model_codi, model_nom, fase, counts:{pending,paused,in_progress,done}}].
  byModel: (params) => client.get('/api/v1/model-task-items/by-model/', { params }),
  get: (id) => client.get(`/api/v1/model-task-items/${id}/`),
  create: (data) => client.post('/api/v1/model-task-items/', data),
  // Assignació: PATCH {assignee} (gated define_tasks; 400 si fora de l'allow-list de l'assignee).
  patch: (id, data) => client.patch(`/api/v1/model-task-items/${id}/`, data),
  remove: (id) => client.delete(`/api/v1/model-task-items/${id}/`),
  // Màquina d'estats (gated execute_tasks). La resposta pot dur paused_task_id (→ toast 3s).
  transition: (id, data) => client.post(`/api/v1/model-task-items/${id}/transition/`, data),  // {to_status}
}
// Alias retrocompatible (KanbanTasks vell encara importa `tasks`; es reconstrueix al tram 4).
export const tasks = modelTasks

// Capa de Projecte — catàleg de tipus de tasca (task-types/, ModelViewSet).
export const taskTypes = {
  list: (params) => client.get('/api/v1/task-types/', { params }),
  get: (id) => client.get(`/api/v1/task-types/${id}/`),
  create: (data) => client.post('/api/v1/task-types/', data),
  update: (id, data) => client.patch(`/api/v1/task-types/${id}/`, data),
  remove: (id) => client.delete(`/api/v1/task-types/${id}/`),
}

// Capa de Projecte — gate del responsable (cartes sintètiques al kanban).
export const gates = {
  ready: () => client.get('/api/v1/gates/ready/'),
  bulk: (data) => client.post('/api/v1/gates/bulk/', data),   // {items:[{model_id,to_phase}], notes}
}

// Capa de Projecte — proveïdors de mostres (suppliers/, ModelViewSet).
export const suppliers = {
  list: (params) => client.get('/api/v1/suppliers/', { params }),
  get: (id) => client.get(`/api/v1/suppliers/${id}/`),
  create: (data) => client.post('/api/v1/suppliers/', data),
  update: (id, data) => client.patch(`/api/v1/suppliers/${id}/`, data),
  remove: (id) => client.delete(`/api/v1/suppliers/${id}/`),
}

// Capa de Projecte — producció de mostres (productions/ és ReadOnlyModelViewSet).
// Alta = models/<id>/request-production/; canvi d'estat = productions/<id>/status/.
export const productions = {
  list: (params) => client.get('/api/v1/productions/', { params }),   // ?model & phase & status & supplier
  get: (id) => client.get(`/api/v1/productions/${id}/`),
  requestProduction: (modelId, data) => client.post(`/api/v1/models/${modelId}/request-production/`, data),
  setStatus: (id, data) => client.post(`/api/v1/productions/${id}/status/`, data),   // {status}
}

// Capa de Projecte — motor de planificació (sprints A+B). Tots gated `configure`.
// Les respostes del motor (compute/preview/apply) porten planned_start/end en ISO LOCAL
// (Europe/Madrid, sense offset) → pintar directe; NO barrejar amb el serializer de tasca (UTC).
export const plan = {
  // body: {model_ids?:[...], campaign_filter?:{temporada,any}}  (sense res = tot el pendent)
  // → {snapshot_id, result:{placements:[{task_id,model,task_type,assignee,planned_start,planned_end,locked}], warnings, models}}
  compute: (body) => client.post('/api/v1/plan/compute/', body),
  // body: {task_id, new_start:"YYYY-MM-DDTHH:MM:SS"} → {moved_task_id, placements, warnings, impact:[{task_id,model,task_type,old_start,new_start}]} (NO desa)
  preview: (body) => client.post('/api/v1/plan/preview/', body),
  // body: {task_id, new_start} → {snapshot_id, result, locked_task_id} (desa + locked)
  apply: (body) => client.post('/api/v1/plan/apply/', body),
  snapshots: () => client.get('/api/v1/plan/snapshots/'),
}

// Calendari propi (agenda) — esdeveniments unificats per pintar. Accés IsAuthenticated; scope per
// view_team_tasks al servidor. Dates en ISO amb offset Europe/Madrid (+02:00), NO UTC cru.
// params opcionals {start:'YYYY-MM-DD', end:'YYYY-MM-DD'} per acotar el rang.
// → {events:[{id,tipus,start,end,titol,tecnic_id,tecnic_nom,color,link,en_risc,meta}]}
export const calendar = {
  events: (params) => client.get('/api/v1/calendar/events/', { params }),
}

// Configuració del calendari d'empresa (singleton del tenant). GET/PUT gated `configure`.
export const companyCalendar = {
  get: () => client.get('/api/v1/company-calendar/'),
  // body: {horaris:{mon:[["08:00","13:00"],...],...}, festius_extra:["YYYY-MM-DD",...]} (parcial)
  update: (body) => client.put('/api/v1/company-calendar/', body),
}

// Override de jornada per tècnic. <userId> = User id. gated `configure` o `manage_users`.
export const jornada = {
  get: (userId) => client.get(`/api/v1/users/${userId}/jornada/`),
  // body: {jornada_override: {...mateix format que horaris...} | null}  (null → hereta empresa)
  update: (userId, body) => client.put(`/api/v1/users/${userId}/jornada/`, body),
}

// Absències per tècnic (rangs de dates). Filtrable ?user_profile=. gated `configure` o `manage_users`.
export const absencies = {
  list: (params) => client.get('/api/v1/absencies/', { params }),   // {user_profile}
  // body: {user_profile, data_inici, data_fi, motiu?}
  create: (body) => client.post('/api/v1/absencies/', body),
  remove: (id) => client.delete(`/api/v1/absencies/${id}/`),
}

// Capa de Projecte — variants de complexitat (garment-type-items/, ModelViewSet).
export const garmentTypeItems = {
  list: (params) => client.get('/api/v1/garment-type-items/', { params }),   // ?garment_type & active
  get: (id) => client.get(`/api/v1/garment-type-items/${id}/`),
  create: (data) => client.post('/api/v1/garment-type-items/', data),
  update: (id, data) => client.patch(`/api/v1/garment-type-items/${id}/`, data),
  remove: (id) => client.delete(`/api/v1/garment-type-items/${id}/`),
}

// Capa de Projecte — matriu de temps (task-time-estimates/, ModelViewSet).
export const taskTimeEstimates = {
  list: (params) => client.get('/api/v1/task-time-estimates/', { params }),   // ?garment_type_item & task_type
  get: (id) => client.get(`/api/v1/task-time-estimates/${id}/`),
  create: (data) => client.post('/api/v1/task-time-estimates/', data),
  update: (id, data) => client.patch(`/api/v1/task-time-estimates/${id}/`, data),
  remove: (id) => client.delete(`/api/v1/task-time-estimates/${id}/`),
}

export const sizeFittings = {
  list: (params) => client.get('/api/v1/size-fittings/', { params }),
  get: (id) => client.get(`/api/v1/size-fittings/${id}/`),
  create: (data) => client.post('/api/v1/size-fittings/', data),
}

// Sprint 5B.6 — Fitting sessions (capa nova). Capa de Projecte: schedule/open al calendari.
export const fittingSessions = {
  list: (params) => client.get('/api/v1/fitting-sessions/', { params }),   // ?estat & data & responsable & fase & model
  get: (id) => client.get(`/api/v1/fitting-sessions/${id}/`),
  create: (data) => client.post('/api/v1/fitting-sessions/', data),
  // PATCH del context (notes/model_persona/assistents/lloc/responsable) — autosave capçalera.
  update: (id, data) => client.patch(`/api/v1/fitting-sessions/${id}/`, data),
  canAdvance: (id) => client.get(`/api/v1/fitting-sessions/${id}/can-advance/`),
  createPiece: (id, modelId) => client.post(`/api/v1/fitting-sessions/${id}/create-piece/`, { model_id: modelId }),
  // Calendari: programar (neix Programada) i obrir (Programada → Oberta).
  schedule: (data) => client.post('/api/v1/fitting-sessions/schedule/', data),
  open: (id) => client.post(`/api/v1/fitting-sessions/${id}/open/`),
}

// Sprint 5B.6-A2 — Piece fittings: graella de treball + gate.
export const pieceFittings = {
  get: (id) => client.get(`/api/v1/piece-fittings/${id}/`),
  setGate: (id, resultat, motiu = '') => client.post(`/api/v1/piece-fittings/${id}/set-gate/`, { resultat, motiu }),
  close: (id) => client.post(`/api/v1/piece-fittings/${id}/close/`),
  // 5B.6-B3 — revert atòmic de reals a l'estat d'obertura (valor_real := valor_teoric).
  discard: (id) => client.post(`/api/v1/piece-fittings/${id}/discard/`),
}

// Autosave de cel·la: només PATCH de valor_real / nota.
export const pieceFittingLines = {
  update: (id, data) => client.patch(`/api/v1/piece-fitting-lines/${id}/`, data),
}

// 5B.6-B3 — Fotos de la sessió (llistar; pujada ajornada a B2).
export const fittingPhotos = {
  list: (params) => client.get('/api/v1/fitting-photos/', { params }),
}

export const gradingVersions = {
  list: (params) => client.get('/api/v1/grading-versions/', { params }),
}

export const pomAlerts = {
  list: (params) => client.get('/api/v1/pom-alerts/', { params }),
  update: (id, data) => client.patch(`/api/v1/pom-alerts/${id}/`, data),
}

export const alerts = pomAlerts

export const timers = {
  list: (params) => client.get('/api/v1/timers/', { params }),
  create: (data) => client.post('/api/v1/timers/', data),
  tancar: (id) => client.post(`/api/v1/timers/${id}/tancar/`),
}

// Usuari autenticat (capabilities + rol_nom). El backend SÍ exposa /api/v1/me/.
export const me = {
  get: () => client.get('/api/v1/me/'),
}

// Gestió d'usuaris (gated manage_users a l'escriptura). Tram 3: pantalla "Usuaris i rols".
export const users = {
  list: (params) => client.get('/api/v1/users/', { params }),   // ?role & can_task & search
  retrieve: (id) => client.get(`/api/v1/users/${id}/`),
  create: (data) => client.post('/api/v1/users/', data),   // {username, email, nom_complet, rol_nom, password, permisos?}
  patch: (id, data) => client.patch(`/api/v1/users/${id}/`, data),   // {rol_nom, actiu, permisos}
  bulk: (data) => client.post('/api/v1/users/bulk/', data),   // {user_ids, action, value} -> {updated}
}
