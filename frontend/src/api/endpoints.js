import axios from 'axios'
import client from './client'

// C4 — invalidació de les superfícies LECTORES del pla (Board + Gantt): quan una acció canvia
// l'ordre materialitzat (reorder manual, o inici real que reancora), emetem un únic esdeveniment
// perquè els lectors muntats es refresquin sense ordenació pròpia. Pass-through de la resposta.
export const planChanged = (res) => {
  try { window.dispatchEvent(new CustomEvent('plan:changed')) } catch { /* SSR/test */ }
  return res
}

export const auth = {
  login: (username, password) => client.post('/api/token/', { username, password }),
}

// Configuració del tenant (TenantConfig) — pantalla General (M5). GET/PATCH d'un únic objecte
// de config; hourly_rate = tarifa interna de cost (≠ tarifes de venda de Product).
export const tenantConfig = {
  get: () => client.get('/api/v1/tenant-config/'),
  update: (data) => client.patch('/api/v1/tenant-config/', data),
  // P6 — puja el logo del tenant (multipart) al mateix endpoint; retorna la config actualitzada.
  // Content-Type: undefined perquè axios/el navegador posin el boundary multipart (el client per
  // defecte és application/json — sense això, el fitxer no arriba a request.FILES). Patró de la casa.
  uploadLogo: (file) => {
    const fd = new FormData(); fd.append('logo_file', file)
    return client.patch('/api/v1/tenant-config/', fd, { headers: { 'Content-Type': undefined } })
  },
}

// Client NET (sense interceptor Bearer) per a la recuperació de contrasenya pública:
// la persona que recupera no està autenticada i no ha d'enviar cap token.
const publicClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  headers: { 'Content-Type': 'application/json' },
})
export const passwordReset = {
  validate: (uid, token) => publicClient.get('/api/v1/password-reset/validate/', { params: { uid, token } }),
  confirm: (data) => publicClient.post('/api/v1/password-reset/confirm/', data),   // {uid, token, new_password}
}

// Tenant-discovery (porta única). SAME-ORIGIN a posta: l'endpoint /api/discovery/ viu al schema
// PUBLIC del host que serveix la pantalla neutra (login.*), no al tenant fhort al qual apunta
// VITE_API_URL. Ruta relativa → cau sobre l'origen actual. Resposta SEMPRE uniforme.
export const tenantDiscovery = {
  submit: (email) => axios.post('/api/discovery/', { email }),
}

export const models = {
  list: (params) => client.get('/api/v1/models/', { params }),
  get: (id) => client.get(`/api/v1/models/${id}/`),
  create: (data) => client.post('/api/v1/models/', data),
  update: (id, data) => client.patch(`/api/v1/models/${id}/`, data),
  remove: (id) => client.delete(`/api/v1/models/${id}/`),
  // Pas 5A — wizard d'esquelet unificat.
  nextRef: (params) => client.get('/api/v1/models/next-ref/', { params }),       // ?year&season
  createWizard: (data) => client.post('/api/v1/models/create-wizard/', data),    // esquelet COMPLET
  updateStep2: (id, data) => client.patch(`/api/v1/models/${id}/update-step2/`, data),
  destroy: (id) => client.delete(`/api/v1/models/${id}/delete/`),
  taskLog: (id) => client.get(`/api/v1/models/${id}/task-log/`),   // 5B-fix: log de transicions
  // Capa de Projecte: definir tasques d'un model i avançar fase (gate del responsable).
  defineTasks: (id, data) => client.post(`/api/v1/models/${id}/define-tasks/`, data),   // {task_type_ids:[...]}
  // Porta-menú: obre una tasca concreta del model (crea-si-falta + auto-assign + En curs). {code}
  // Sprint Y — fittingSessionId opcional: lliga la tasca a la sessió (FK) i obre la sessió Programada.
  openTask: (id, code, fittingSessionId = null) =>
    client.post(`/api/v1/models/${id}/open-task/`, { code, ...(fittingSessionId ? { fitting_session_id: fittingSessionId } : {}) })
      .then(planChanged),   // C4 — l'auto-start pot reancorar el pla → invalida Board+Gantt
  // Acte lleuger de gènesi POM: base+nomenclatura+regles i tanca la tasca pom. No propaga.
  gravarPom: (id, data) => client.post(`/api/v1/models/${id}/gravar-pom/`, data),
  gate: (id, data) => client.post(`/api/v1/models/${id}/gate/`, data),                   // {to_phase} o {to_phases:[...]}
  regress: (id, data) => client.post(`/api/v1/models/${id}/regress/`, data),             // {to_phase} — retrocés net
  // Tram 2 planificació (gated define_tasks): assigna les no-Done a un tècnic + compute de cua
  // sencera; unassign treu tècnic + buida planned_*. Done sempre intactes.
  assign: (id, body) => client.post(`/api/v1/models/${id}/assign/`, body),   // {assignee_id, task_ids?}
  unassign: (id) => client.post(`/api/v1/models/${id}/unassign/`),
  // PG-4b-3b — fixa el règim de grading d'un POM del model (l'usarà 3c). {logica}
  setPomRegim: (modelId, pomId, logica) => client.post(`/api/v1/models/${modelId}/pom/${pomId}/regim/`, { logica }),
  // P3 — autoria de la REGLA viva del model per POM: delta + break (+ règim). Patrimoni del model
  // (origen MANUAL). payload: {logica?, increment_base?, increment_break?, talla_break_label?}.
  setPomRule: (modelId, pomId, payload) => client.post(`/api/v1/models/${modelId}/pom/${pomId}/regim/`, payload),
  // Edita una talla NO-base com a ModelGradingOverride i re-propaga (editor propagat del model).
  setSizeOverride: (modelId, pomId, sizeLabel, valor) =>
    client.post(`/api/v1/models/${modelId}/set-size-override/`, { pom_id: pomId, size_label: sizeLabel, valor }),
  // Taula base amb estadis (històric per presa + tolerància + base vigent). Read-only.
  baseStages: (modelId) => client.get(`/api/v1/models/${modelId}/base-stages/`),
  // Peça 2 — propagació conscient (origen Mesures): {new_version:true} crea v+1 sobre la vigent. Sobre
  // una versió segellada retorna 409 {error:'sealed', version_number} → cal doble confirmació
  // ({allow_reopen_sealed:true}).
  generarGrading: (modelId, body) => client.post(`/api/v1/models/${modelId}/generar-grading/`, body || {}),
  // Fase 2 — ajust de talla a Escalat: ancora la talla i PROPAGA per regla a les germanes (com el
  // fitting). Retorna {linies:[{id,valor_real}]} per refrescar la fila. Base inclosa.
  escalatAjustarTalla: (modelId, pomId, talla, valor) =>
    client.post(`/api/v1/models/${modelId}/escalat/ajustar-talla/`, { pom_id: pomId, talla, valor }),
  // Fase B — estat de propagació perquè el botó Propagar MIRI ABANS (read-only):
  // {te_dades_propagades, segellada, version_number}.
  gradingStatus: (modelId) => client.get(`/api/v1/models/${modelId}/grading-status/`),
  // Sprint 5 — comptadors de models per fase (board del Dashboard). Respecta els mateixos
  // filtres que el Model list (customer/collection/data_objectiu_after|before/temporada/...).
  // → {counts:{<fase>:n}, total}.
  faseCounts: (params) => client.get('/api/v1/models/fase-counts/', { params }),
  // Comptadors de models per garment_type i per garment_type_item del conjunt FILTRAT (mateix
  // ModelFilter C1). Alimenta el CascadeSelector mode=multi (showCounts) del panell de filtres.
  // → {by_type:{<id>:n}, by_item:{<id>:n}, total}.
  garmentCounts: (params) => client.get('/api/v1/models/garment-counts/', { params }),
}

// Mesura base d'un POM (talla base). PATCH per editar nom_fitxa per-POM (escriu NOMÉS BaseMeasurement).
export const baseMeasurements = {
  update: (id, body) => client.patch(`/api/v1/base-measurements/${id}/`, body),
  // Reordena els POM del model en bloc (ordre ÚNIC i global; es materialitza a Grading en propagar).
  reorder: (modelId, ids) => client.post(`/api/v1/models/${modelId}/base-measurements/reorder/`, { ids }),
}

// D-12 — Watchpoints: advertències de text lliure ancorades al model (+ tasca d'origen), open→resolved.
export const watchpoints = {
  list: (params) => client.get('/api/v1/watchpoints/', { params }),     // ?model&estat&task
  create: (data) => client.post('/api/v1/watchpoints/', data),          // {model, task?, text}
  resolve: (id, data) => client.post(`/api/v1/watchpoints/${id}/resolve/`, data || {}),
  reopen: (id) => client.post(`/api/v1/watchpoints/${id}/reopen/`),
}

// Fitxers del model — panell info de fitting (5B.6-B1) i FilePicker de l'editor (S03b · P7).
// L'escriptura NO passa per aquí: puja per models/<id>/upload-fitxer/ (multipart, fetch cru).
export const modelFitxers = {
  list: (params) => client.get('/api/v1/model-fitxers/', { params }),
  // Cicle model→model (S03c · C3.2): crea una CÒPIA sobirana al model destí (derivat_de_model);
  // l'origen no es toca mai. Un `.ftt` s'hi descongela i es re-resol contra el destí (D16).
  usarAlModel: (id, modelId) =>
    client.post(`/api/v1/model-fitxers/${id}/usar-al-model/`, { model_id: modelId }),
}

// Fitxers del CATÀLEG, ancorats a un GarmentTypeItem (S03b · P4/P5).
export const itemFitxers = {
  list: (params) => client.get('/api/v1/item-fitxers/', { params }),
  // P4 · gated CONFIGURE al backend. `Content-Type: undefined` perquè el navegador hi posi el
  // boundary multipart: si s'hi força un valor, `request.FILES` arriba buit.
  create: (formData) => client.post('/api/v1/item-fitxers/', formData,
    { headers: { 'Content-Type': undefined } }),
  // Cicle ①: crea una CÒPIA al model (derivat_de_item), no toca l'ItemFitxer.
  usarAlModel: (id, modelId) =>
    client.post(`/api/v1/item-fitxers/${id}/usar-al-model/`, { model_id: modelId }),
}

export const poms = {
  list: (params) => client.get('/api/v1/poms/', { params }),
  cerca: (params) => client.get('/api/v1/poms/cerca/', { params }),          // ?q & page_size
  crearTenant: (data) => client.post('/api/v1/poms/crear-tenant/', data),    // POM tenant-only nou
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

export const sizingProfiles = {
  list: (params) => client.get('/api/v1/sizing-profiles/', { params }),   // ?target&construction
  get: (id) => client.get(`/api/v1/sizing-profiles/${id}/`),
  restore: (id) => client.post(`/api/v1/sizing-profiles/${id}/restaurar/`),
  clone: (id, payload) => client.post(`/api/v1/sizing-profiles/${id}/clonar/`, payload),
}

export const targets = {
  list: (params) => client.get('/api/v1/targets/', { params }),
}

export const fitTypes = {
  list: (params) => client.get('/api/v1/fit-types/', { params }),
}

export const constructionTypes = {
  list: (params) => client.get('/api/v1/construction-types/', { params }),
}

// Size Map Setup wizard (Sprint Size Map). Escriptura gated CONFIGURE al backend.
export const sizeMap = {
  lookups:        () => client.get('/api/v1/size-map/lookups/'),
  match:          (data) => client.post('/api/v1/size-map/match/', data),
  preview:        (data) => client.post('/api/v1/size-map/preview/', data),
  gradingPreview: (data) => client.post('/api/v1/size-map/grading-preview/', data),
  gradingPreviewFile: (formData) => client.post('/api/v1/size-map/grading-preview-file/', formData, {
    headers: { 'Content-Type': undefined },
  }),
  create:         (data) => client.post('/api/v1/size-map/create/', data),
  systems:        (params) => client.get('/api/v1/size-map/systems/', { params }),
}

export const gradingRuleSets = {
  list: (params) => client.get('/api/v1/grading-rule-sets/', { params }),
  get: (id) => client.get(`/api/v1/grading-rule-sets/${id}/`),
  editRule: (setId, pom, payload) =>
    client.patch(`/api/v1/grading-rule-sets/${setId}/regles/${pom}/editar/`, payload),
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
  // Self-claim entre tècnics (P4a-back, gated execute_tasks, self-only). Sense body: assignee = jo.
  claim: (id) => client.post(`/api/v1/model-task-items/${id}/claim/`),
}
// Alias retrocompatible (KanbanTasks vell encara importa `tasks`; es reconstrueix al tram 4).
export const tasks = modelTasks

// Capa de Projecte — catàleg de tipus de tasca (task-types/, ModelViewSet).
export const taskTypes = {
  list: (params) => client.get('/api/v1/task-types/', { params }),
  get: (id) => client.get(`/api/v1/task-types/${id}/`),
  // create/update/remove retirats (G8-2): el backend és ReadOnlyModelViewSet (405) i cap pantalla els cridava.
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

// Estudi tècnic — arxiu de clients (customers/, ModelViewSet). Escriptura gated CONFIGURE;
// remove → 409 si el client té models associats (Model.customer = PROTECT).
export const customers = {
  list: (params) => client.get('/api/v1/customers/', { params }),
  get: (id) => client.get(`/api/v1/customers/${id}/`),
  create: (data) => client.post('/api/v1/customers/', data),
  update: (id, data) => client.patch(`/api/v1/customers/${id}/`, data),
  remove: (id) => client.delete(`/api/v1/customers/${id}/`),
}

// Biblioteca de nomenclatura del client (CustomerPOMAlias). Escriptura gated CONFIGURE.
export const customerAliases = {
  list: (params) => client.get('/api/v1/customer-pom-aliases/', { params }),   // ?customer=<id>
  create: (data) => client.post('/api/v1/customer-pom-aliases/', data),
  update: (id, data) => client.patch(`/api/v1/customer-pom-aliases/${id}/`, data),
  remove: (id) => client.delete(`/api/v1/customer-pom-aliases/${id}/`),
}

// Diccionari de nomenclatura del client (setup). Escriptura gated CONFIGURE. Stateless.
export const customerDictionary = {
  template: (id) => client.get(`/api/v1/pom/customers/${id}/dictionary/template/`, { responseType: 'blob' }),
  preview: (id, formData) => client.post(`/api/v1/pom/customers/${id}/dictionary/preview/`, formData, {
    headers: { 'Content-Type': undefined },
  }),
  commit: (id, payload) => client.post(`/api/v1/pom/customers/${id}/dictionary/commit/`, payload),
}

// Plantilla de fitxa tècnica per client (TS-3). get_or_create + PATCH; escriptura gated CONFIGURE.
export const techSheetTemplate = {
  detail: (customerId) => client.get(`/api/v1/customers/${customerId}/tech-sheet-template/`),
  update: (customerId, data) => client.patch(`/api/v1/customers/${customerId}/tech-sheet-template/update/`, data),
}

// Import massiu de models per Excel. template/errorsReport són descàrregues binàries
// (responseType blob); upload és multipart (Content-Type undefined → axios posa el boundary).
export const bulkImport = {
  template: (customerId) => client.get('/api/v1/bulk-import/template/', {
    params: { customer_id: customerId }, responseType: 'blob',
  }),
  upload: (formData) => client.post('/api/v1/bulk-import/upload/', formData, {
    headers: { 'Content-Type': undefined },
  }),
  reconciliation: (id) => client.get(`/api/v1/bulk-import/${id}/reconciliation/`),
  commit: (id) => client.post(`/api/v1/bulk-import/${id}/commit/`),
  errorsReport: (id) => client.get(`/api/v1/bulk-import/${id}/errors-report/`, {
    responseType: 'blob',
  }),
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
  // M3 — Calendari-Gantt de projecte (gated view_team_tasks). ?model_id&responsable&collection&temporada
  gantt: (params) => client.get('/api/v1/plan/gantt/', { params }),   // → {models:[...], today}
  // body: {model_ids?:[...], campaign_filter?:{temporada,any}}  (sense res = tot el pendent)
  // → {snapshot_id, result:{placements:[{task_id,model,task_type,assignee,planned_start,planned_end,locked}], warnings, models}}
  compute: (body) => client.post('/api/v1/plan/compute/', body),
  // body: {task_id, new_start:"YYYY-MM-DDTHH:MM:SS"} → {moved_task_id, placements, warnings, impact:[{task_id,model,task_type,old_start,new_start}]} (NO desa)
  preview: (body) => client.post('/api/v1/plan/preview/', body),
  // body: {task_id, new_start} → {snapshot_id, result, locked_task_id} (desa + locked)
  apply: (body) => client.post('/api/v1/plan/apply/', body),
  snapshots: () => client.get('/api/v1/plan/snapshots/'),
  // body: {assignee_id, model_ids:[...ordenats]} → desa l'ordre manual de la cua + recompute.
  // → {ok, assignee_id, result:{placements,warnings,models}}. Gated define_tasks.
  reorder: (body) => client.post('/api/v1/plan/reorder/', body).then(planChanged),
  // Wizard multi-assign (Peça 2/3, gated define_tasks).
  // → [{profile_id, full_name, color_avatar, disponible_des_de, models_en_cua}] (ordenat per disponibilitat).
  eligibleTechnicians: (code) =>
    client.get(`/api/v1/plan/eligible-technicians/?task_type=${code}`),
  // body: {model_ids:[int], assignacions:[{task_type_code, assignee_profile_id, planned_start?, planned_end?}]}
  // → {fets, creats, reassignats, omesos, warnings, resultats}.
  assignBatch: (body) =>
    client.post('/api/v1/plan/assign-batch/', body),
  // Assistents elegibles per a un fitting (gated schedule_fittings).
  // → [{profile_id, full_name, color_avatar}].
  eligibleAttendees: () =>
    client.get('/api/v1/plan/eligible-attendees/'),
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

// Mòdul Comercial Studio (B1) — mestre d'articles. Escriptura gated CONFIGURE.
// Satèl·lits filtrables per ?product=. price-exceptions = taula d'EXCEPCIONS (no graella densa).
export const commerce = {
  units: {
    list: (params) => client.get('/api/v1/commerce/units/', { params }),
  },
  products: {
    list: (params) => client.get('/api/v1/commerce/products/', { params }),
    get: (id) => client.get(`/api/v1/commerce/products/${id}/`),
    create: (data) => client.post('/api/v1/commerce/products/', data),
    update: (id, data) => client.patch(`/api/v1/commerce/products/${id}/`, data),
    remove: (id) => client.delete(`/api/v1/commerce/products/${id}/`),
  },
  recipeLines: {
    list: (params) => client.get('/api/v1/commerce/recipe-lines/', { params }),
    create: (data) => client.post('/api/v1/commerce/recipe-lines/', data),
    update: (id, data) => client.patch(`/api/v1/commerce/recipe-lines/${id}/`, data),
    remove: (id) => client.delete(`/api/v1/commerce/recipe-lines/${id}/`),
  },
  productSuppliers: {
    list: (params) => client.get('/api/v1/commerce/product-suppliers/', { params }),
    create: (data) => client.post('/api/v1/commerce/product-suppliers/', data),
    update: (id, data) => client.patch(`/api/v1/commerce/product-suppliers/${id}/`, data),
    remove: (id) => client.delete(`/api/v1/commerce/product-suppliers/${id}/`),
  },
  productComponents: {
    list: (params) => client.get('/api/v1/commerce/product-components/', { params }),
    create: (data) => client.post('/api/v1/commerce/product-components/', data),
    remove: (id) => client.delete(`/api/v1/commerce/product-components/${id}/`),
  },
  priceExceptions: {
    list: (params) => client.get('/api/v1/commerce/price-exceptions/', { params }),
    create: (data) => client.post('/api/v1/commerce/price-exceptions/', data),
    update: (id, data) => client.patch(`/api/v1/commerce/price-exceptions/${id}/`, data),
    remove: (id) => client.delete(`/api/v1/commerce/price-exceptions/${id}/`),
  },
  // Condicions de pagament (B3a/M4) — CRUD amb fraccions nested writable (guard Σ%=100 al backend).
  paymentTerms: {
    list: (params) => client.get('/api/v1/commerce/payment-terms/', { params }),
    get: (id) => client.get(`/api/v1/commerce/payment-terms/${id}/`),
    create: (data) => client.post('/api/v1/commerce/payment-terms/', data),
    update: (id, data) => client.patch(`/api/v1/commerce/payment-terms/${id}/`, data),
    remove: (id) => client.delete(`/api/v1/commerce/payment-terms/${id}/`),
  },
  // Documents comercials — Quote (B2). send/pdf són accions; pdf retorna blob.
  quotes: {
    list: (params) => client.get('/api/v1/commerce/quotes/', { params }),
    get: (id) => client.get(`/api/v1/commerce/quotes/${id}/`),
    create: (data) => client.post('/api/v1/commerce/quotes/', data),
    update: (id, data) => client.patch(`/api/v1/commerce/quotes/${id}/`, data),
    remove: (id) => client.delete(`/api/v1/commerce/quotes/${id}/`),
    send: (id) => client.post(`/api/v1/commerce/quotes/${id}/send/`),
    pdf: (id) => client.get(`/api/v1/commerce/quotes/${id}/pdf/`, { responseType: 'blob' }),
    convert: (id) => client.post(`/api/v1/commerce/quotes/${id}/convert/`),   // → SalesOrder (201)
  },
  quoteLines: {
    list: (params) => client.get('/api/v1/commerce/quote-lines/', { params }),   // ?quote=
    create: (data) => client.post('/api/v1/commerce/quote-lines/', data),
    update: (id, data) => client.patch(`/api/v1/commerce/quote-lines/${id}/`, data),
    remove: (id) => client.delete(`/api/v1/commerce/quote-lines/${id}/`),
  },
  // E6 — vincle preparatori model↔línia d'oferta (intenció informativa, editable en DRAFT/SENT).
  quoteLineIntents: {
    list: (params) => client.get('/api/v1/commerce/quote-line-intents/', { params }),   // ?quote_line=
    create: (data) => client.post('/api/v1/commerce/quote-line-intents/', data),
    remove: (id) => client.delete(`/api/v1/commerce/quote-line-intents/${id}/`),
  },
  // Documents comercials — SalesOrder (comanda, B3b). Neixen de la conversió d'una oferta;
  // lectura + pdf. Línies read-only (mutació només qty_allocated, control de cartera B4).
  orders: {
    list: (params) => client.get('/api/v1/commerce/orders/', { params }),
    get: (id) => client.get(`/api/v1/commerce/orders/${id}/`),
    update: (id, data) => client.patch(`/api/v1/commerce/orders/${id}/`, data),   // només status
    pdf: (id) => client.get(`/api/v1/commerce/orders/${id}/pdf/`, { responseType: 'blob' }),
  },
  orderLines: {
    list: (params) => client.get('/api/v1/commerce/order-lines/', { params }),   // ?order=
    update: (id, data) => client.patch(`/api/v1/commerce/order-lines/${id}/`, data),   // qty_allocated
    // B4b — assigna un model a la línia i crea el WO ORDER (migra el col·lector). {model_id}
    assignModel: (id, data) => client.post(`/api/v1/commerce/order-lines/${id}/assign-model/`, data),
    // P4 — expansió read-only: models assignats (via WO), tasques amb estat, % imputat.
    allocation: (id) => client.get(`/api/v1/commerce/order-lines/${id}/allocation/`),
  },
  // Encàrrecs / ordres de treball (B4a). No es creen per POST (ORDER=wizard, COLLECTOR=hook).
  workOrders: {
    list: (params) => client.get('/api/v1/commerce/work-orders/', { params }),   // ?kind=&status=&customer=&period=
    get: (id) => client.get(`/api/v1/commerce/work-orders/${id}/`),
    close: (id, data) => client.post(`/api/v1/commerce/work-orders/${id}/close/`, data || {}),
    // B4b — revisió comercial (preu de venda) d'un WO tancat. {items:[{model_task_id,kind,amount}]}
    review: (id, data) => client.post(`/api/v1/commerce/work-orders/${id}/review/`, data || {}),
    // Desassigna el model de la línia: orfanda el WO (gate CONFIGURE). 400 si ORDER tancat/albaranat.
    unassign: (id) => client.post(`/api/v1/commerce/work-orders/${id}/unassign/`),
    // Informe read-only dels WO desassignats (orphaned_from_line no null) — pendents de reassignar.
    orphaned: () => client.get('/api/v1/commerce/work-orders/orphaned/'),
    // E5 — línies candidates per re-adoptar un WO orfe (comandes OPEN del mateix client, qty lliure).
    reattachCandidates: (id) => client.get(`/api/v1/commerce/work-orders/${id}/reattach-candidates/`),
    // E5 — re-adopta el WO orfe a una línia nova (re-congela snapshots). {order_line_id}. Gate CONFIGURE.
    // Nom CLAR per no col·lidir amb la homonímia unassign (tècnic vs comercial).
    reattach: (id, data) => client.post(`/api/v1/commerce/work-orders/${id}/reattach/`, data),
  },
  // Despeses d'un encàrrec (B4b) — línia externa amb proveïdor i marge. Satèl·lit ?work_order=.
  expenses: {
    list: (params) => client.get('/api/v1/commerce/expenses/', { params }),   // ?work_order=
    create: (data) => client.post('/api/v1/commerce/expenses/', data),
    update: (id, data) => client.patch(`/api/v1/commerce/expenses/${id}/`, data),
    remove: (id) => client.delete(`/api/v1/commerce/expenses/${id}/`),
  },
  // Albarans (B4c) — document derivat que agrega 1..N WorkOrder CLOSED del mateix client.
  // No es creen per POST directe: neixen de generate/ (línies proposades pel sistema).
  deliveryNotes: {
    list: (params) => client.get('/api/v1/commerce/delivery-notes/', { params }),   // ?status=&customer=
    get: (id) => client.get(`/api/v1/commerce/delivery-notes/${id}/`),
    update: (id, data) => client.patch(`/api/v1/commerce/delivery-notes/${id}/`, data),   // notes en DRAFT
    remove: (id) => client.delete(`/api/v1/commerce/delivery-notes/${id}/`),   // només DRAFT (allibera WO)
    // Genera un DRAFT amb línies proposades. {work_order_ids:[…]} → 201 o 400 {detail, errors}.
    generate: (data) => client.post('/api/v1/commerce/delivery-notes/generate/', data),
    issue: (id) => client.post(`/api/v1/commerce/delivery-notes/${id}/issue/`),   // DRAFT→ISSUED (congela)
    pdf: (id) => client.get(`/api/v1/commerce/delivery-notes/${id}/pdf/`, { responseType: 'blob' }),
    // v2 — safata d'albaranables per model. ?customer=<id> → {customer, groups:[{model, items}]}.
    billable: (params) => client.get('/api/v1/commerce/delivery-notes/billable/', { params }),
    // v2 — retorna el DRAFT obert del client o en crea un. {customer} → 200/201.
    draft: (data) => client.post('/api/v1/commerce/delivery-notes/draft/', data),
    // v2 — afegeix línies seleccionades de la safata al DRAFT. {items:[{kind, *_id}]}.
    addLines: (id, data) => client.post(`/api/v1/commerce/delivery-notes/${id}/add-lines/`, data),
    // v2 — marcatge ISSUED→INVOICED (individual i massiu {ids:[…]}).
    markInvoiced: (id) => client.post(`/api/v1/commerce/delivery-notes/${id}/mark-invoiced/`),
    markInvoicedBulk: (data) => client.post('/api/v1/commerce/delivery-notes/mark-invoiced-bulk/', data),
  },
  deliveryNoteLines: {
    list: (params) => client.get('/api/v1/commerce/delivery-note-lines/', { params }),   // ?delivery_note=
    update: (id, data) => client.patch(`/api/v1/commerce/delivery-note-lines/${id}/`, data),   // preu/descr/visible en DRAFT
    create: (data) => client.post('/api/v1/commerce/delivery-note-lines/', data),   // v2 — línia MANUAL
    remove: (id) => client.delete(`/api/v1/commerce/delivery-note-lines/${id}/`),   // v2 — treu línia del DRAFT
  },
}

// Sprint Llibreria d'Items — pertinença POM de l'Item (garment-pom-maps/, ModelViewSet).
// Escriptura gated CONFIGURE. Reorder = PATCH {ordre} per fila (mateix patró que POMBrowser).
export const garmentPomMaps = {
  list: (params) => client.get('/api/v1/garment-pom-maps/', { params }),   // ?garment_type_item & pom
  create: (data) => client.post('/api/v1/garment-pom-maps/', data),
  update: (id, data) => client.patch(`/api/v1/garment-pom-maps/${id}/`, data),
  remove: (id) => client.delete(`/api/v1/garment-pom-maps/${id}/`),
}

// Sprint Llibreria d'Items — valors base de l'Item (item-base-measurements/, ModelViewSet + upsert).
// upsert keyed (garment_type_item, pom): base_value_cm, tol_minus, tol_plus, nom_fitxa. Gated CONFIGURE.
export const itemBaseMeasurements = {
  list: (params) => client.get('/api/v1/item-base-measurements/', { params }),   // ?garment_type_item & pom
  upsert: (data) => client.post('/api/v1/item-base-measurements/upsert/', data),
  remove: (id) => client.delete(`/api/v1/item-base-measurements/${id}/`),
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
  // PATCH del context (notes/model_persona/assistents/lloc/responsable) — autosave capçalera.
  update: (id, data) => client.patch(`/api/v1/fitting-sessions/${id}/`, data),
  canAdvance: (id) => client.get(`/api/v1/fitting-sessions/${id}/can-advance/`),
  createPiece: (id, modelId) => client.post(`/api/v1/fitting-sessions/${id}/create-piece/`, { model_id: modelId }),
  // Calendari: programar (neix Programada) i obrir (Programada → Oberta).
  schedule: (data) => client.post('/api/v1/fitting-sessions/schedule/', data),
  // C4 — "Fitting aquí i ara": un clic, cap formulari. body {model_id, fase?, force?}.
  scheduleNow: (data) => client.post('/api/v1/fitting-sessions/schedule-now/', data),
  // Bulk: N sessions encadenades amb convocatoria UUID compartit (sessió i+1 on acaba la i).
  scheduleBulk: (data) => client.post('/api/v1/fitting-sessions/schedule-bulk/', data),
  open: (id) => client.post(`/api/v1/fitting-sessions/${id}/open/`),
  // Peça 2/3 — cicle de vida de sessió i gestió de convocatòria (grup).
  remove: (id) => client.delete(`/api/v1/fitting-sessions/${id}/`),
  discardSession: (id, motiu = '') => client.post(`/api/v1/fitting-sessions/${id}/discard/`, { motiu }),
  seal: (id) => client.post(`/api/v1/fitting-sessions/${id}/seal/`),
  groupReschedule: (uuid, payload) => client.patch(`/api/v1/fitting-sessions/group/${uuid}/reschedule/`, payload),
  groupAddModel: (uuid, payload) => client.post(`/api/v1/fitting-sessions/group/${uuid}/add-model/`, payload),
  groupRemoveModel: (uuid, modelId) => client.delete(`/api/v1/fitting-sessions/group/${uuid}/remove-model/${modelId}/`),
  groupAttendees: (uuid, payload) => client.patch(`/api/v1/fitting-sessions/group/${uuid}/attendees/`, payload),
  groupRemove: (uuid) => client.delete(`/api/v1/fitting-sessions/group/${uuid}/`),
}

// Sprint 5B.6-A2 — Piece fittings: graella de treball + gate.
export const pieceFittings = {
  get: (id) => client.get(`/api/v1/piece-fittings/${id}/`),
  setGate: (id, resultat, motiu = '') => client.post(`/api/v1/piece-fittings/${id}/set-gate/`, { resultat, motiu }),
  close: (id, data) => client.post(`/api/v1/piece-fittings/${id}/close/`, data || {}),
  // 5B.6-B3 — revert atòmic de reals a l'estat d'obertura (valor_real := valor_teoric).
  discard: (id) => client.post(`/api/v1/piece-fittings/${id}/discard/`),
}

// Autosave de cel·la: només PATCH de valor_real / nota.
export const pieceFittingLines = {
  update: (id, data) => client.patch(`/api/v1/piece-fitting-lines/${id}/`, data),
  // PG-4b-3b — ancoratge en règim LINEAR/canònic: desa la cel·la i propaga el delta a les
  // germanes del POM (retorna {propagat, motiu, warnings, linies:[...]}). STEP → només desa.
  propagar: (id, valorReal) => client.post(`/api/v1/piece-fitting-lines/${id}/propagar/`, { valor_real: valorReal }),
}

// 5B.6-B3 — Fotos de la sessió (llistar) · Sprint Y — pujada multipart.
export const fittingPhotos = {
  list: (params) => client.get('/api/v1/fitting-photos/', { params }),
  // Sprint Y — substitueix el client.post cru de FittingDetail i OMPLE piece_fitting (abans null):
  // la foto queda ancorada a la peça concreta, no només a la sessió.
  upload: (sessionId, file, pieceFittingId = null) => {
    const fd = new FormData()
    fd.append('session', sessionId)
    fd.append('fitxer', file)
    if (pieceFittingId) fd.append('piece_fitting', pieceFittingId)
    return client.post('/api/v1/fitting-photos/', fd)
  },
}

// SC-1 — Size Check: validació del proto a talla base, ABANS del fitting.
export const sizeChecks = {
  list: (params) => client.get('/api/v1/size-checks/', { params }),         // ?model & estat
  get: (id) => client.get(`/api/v1/size-checks/${id}/`),
  // Obre o reutilitza el check Pendent del model (idempotent: reusa si n'hi ha un de viu).
  open: (modelId) => client.post('/api/v1/size-checks/open/', { model_id: modelId }),
  // SC-5: data_represa (YYYY-MM-DD) reagenda la tasca size_check quan queda viva (Rebutjat/Descartat).
  resolve: (id, estat, { missatge = '', data_represa = null } = {}) =>
    client.post(`/api/v1/size-checks/${id}/resolve/`, {
      estat, missatge_fabricant: missatge, data_represa,
    }),
}

// Autosave de cel·la del size check: PATCH de valor_real / acceptat / nota.
export const sizeCheckLines = {
  update: (id, data) => client.patch(`/api/v1/size-check-lines/${id}/`, data),
}

export const gradingVersions = {
  list: (params) => client.get('/api/v1/grading-versions/', { params }),
}

export const pomAlerts = {
  list: (params) => client.get('/api/v1/pom-alerts/', { params }),
  update: (id, data) => client.patch(`/api/v1/pom-alerts/${id}/`, data),
}

export const timers = {
  list: (params) => client.get('/api/v1/timers/', { params }),
  create: (data) => client.post('/api/v1/timers/', data),
  tancar: (id) => client.post(`/api/v1/timers/${id}/tancar/`),
}

// Usuari autenticat (capabilities + rol_nom). El backend SÍ exposa /api/v1/me/.
export const me = {
  get: () => client.get('/api/v1/me/'),
  changePassword: (data) => client.post('/api/v1/me/change-password/', data),   // {new_password, new_password_confirm}
}

// Gestió d'usuaris (gated manage_users a l'escriptura). Tram 3: pantalla "Usuaris i rols".
export const users = {
  list: (params) => client.get('/api/v1/users/', { params }),   // ?role & can_task & search
  retrieve: (id) => client.get(`/api/v1/users/${id}/`),
  create: (data) => client.post('/api/v1/users/', data),   // {username, email, nom_complet, rol_nom, password, permisos?}
  patch: (id, data) => client.patch(`/api/v1/users/${id}/`, data),   // {rol_nom, actiu, permisos}
  bulk: (data) => client.post('/api/v1/users/bulk/', data),   // {user_ids, action, value} -> {updated}
  resetLink: (id) => client.post(`/api/v1/users/${id}/reset-link/`),   // -> {url}
}

// Motor de patrons (S3) — DXF-AAMA + RUL: pujar, llegir, renderitzar, descarregar.
export const patterns = {
  list: (modelId) => client.get('/api/v1/patterns/pattern-files/', { params: { model: modelId } }),
  get: (id) => client.get(`/api/v1/patterns/pattern-files/${id}/`),
  // Content-Type: undefined perquè el navegador hi posi el boundary multipart; si s'hi
  // força un valor, request.FILES arriba buit. Patró de la casa (v. itemFitxers.create).
  upload: (formData) => client.post('/api/v1/patterns/pattern-files/', formData,
    { headers: { 'Content-Type': undefined } }),
  remove: (id) => client.delete(`/api/v1/patterns/pattern-files/${id}/`),

  // URLs signades FRESQUES, al moment del clic (W5 · D9). Les del detall es couven amb la
  // pàgina i caduquen als 15 min: al Taller, on el tab es queda obert mentre es treballa,
  // això vol dir botons de descàrrega morts sense que res hagi canviat a la pantalla.
  downloadLinks: (id) => client.get(`/api/v1/patterns/pattern-files/${id}/download-links/`),

  // La geometria SENCERA amb coordenades: el que dibuixa el visor Konva. El detall
  // (get) només porta recomptes — un llistat no ha d'arrossegar milers de punts.
  // Porta també els segments (el que una costura pot triar) i els POMs ja ancorats.
  geometry: (id) => client.get(`/api/v1/patterns/pattern-files/${id}/geometry/`),

  // La LLISTA DE TREBALL del taller (W3): les Mesures del model creuades amb el que
  // AQUEST patró mesura — valor de fitxa, valor mesurat i la Δ. El creuament és de domini
  // (la frontissa és el POMMaster) i el fa el servidor: baixar-se dues llistes i creuar-les
  // al client seria refer-lo a mà, i a mà cada pantalla el refaria una mica diferent.
  modelPoms: (id) => client.get(`/api/v1/patterns/pattern-files/${id}/model-poms/`),

  // POMs ancorats (S6). El VALOR no s'envia mai: s'envia la recepta (quins punts) i el
  // servidor la resol sobre la geometria. Un valor teclejat no seria una mesura del
  // patró, seria una opinió sobre el patró.
  poms: {
    list: (patternFileId) => client.get('/api/v1/patterns/pattern-poms/',
      { params: { pattern_piece__pattern_file: patternFileId } }),
    create: (data) => client.post('/api/v1/patterns/pattern-poms/', data),
    // REOBRIR (W4b/T5a): la recepta nova sobre el MATEIX PatternPOM, i el servidor RECALCULA
    // el valor. Mai esborrar-i-crear: corregir on és una mesura no és tornar-la a ancorar.
    update: (id, data) => client.patch(`/api/v1/patterns/pattern-poms/${id}/`, data),
    remove: (id) => client.delete(`/api/v1/patterns/pattern-poms/${id}/`),

    // ESBORRAT EN BLOC (E/T3). Torna `{esborrats, retinguts}`: mai un 500 per dependència,
    // i mai «tot o res» —qui n'ha marcat divuit no ha demanat que un de retingut en salvés
    // disset. L'atomicitat és per ítem, al servidor.
    bulkRemove: (ids) => client.post('/api/v1/patterns/pattern-poms/bulk-delete/', { ids }),
  },

  // Costures. L'estat (casa / no casa) el calcula el servidor cada cop sobre la
  // geometria viva: no es desa, perquè una costura que casava i ja no casa ho ha de dir.
  // Des de W1, `estat.cobertura` hi porta els avisos de solapament i excés de la vora.
  sew: {
    list: (modelId) => client.get('/api/v1/patterns/sew-relations/',
      { params: { model: modelId } }),
    create: (data) => client.post('/api/v1/patterns/sew-relations/', data),
    // REOBRIR (W4b/T5c): tipus, diferencial, composició de costats i bateig, sobre la MATEIXA
    // costura. Encunyar-ne una altra li perdria la data i l'autor per un canvi de tipus.
    update: (id, data) => client.patch(`/api/v1/patterns/sew-relations/${id}/`, data),

    // MARCAR PINÇA (W4b/T1): tres punts, i el servidor en fa els dos costats (trams
    // declarats) i la costura de pinça que els uneix — en UNA transacció. Fer-ho amb tres
    // crides des d'aquí podia fallar a la tercera i deixar dos trams orfes al patró, amb nom
    // de pinça i sense pinça.
    pinca: (data) => client.post('/api/v1/patterns/sew-relations/pinca/', data),

    // Esborrar una pinça se n'emporta els seus dos costats: no existeixen sense ella.
    remove: (id) => client.delete(`/api/v1/patterns/sew-relations/${id}/`),

    // En BLOC (E/T3), costures i pinces: cada pinça s'emporta els seus costats dins de la
    // seva pròpia transacció. Torna `{esborrats, retinguts}`.
    bulkRemove: (ids) => client.post('/api/v1/patterns/sew-relations/bulk-delete/', { ids }),

    // ── ASSISTIT (A2): el motor PROPOSA, la persona decideix ────────────────
    //
    // Les propostes NO es desen enlloc: es recalculen senceres a cada crida sobre la geometria
    // viva. Per això no hi ha cap `id` de proposta —una proposta no és una fila— i el que la
    // identifica és la `clau`: els dos trams que uneix. Confirmar-ne una o esborrar una costura
    // canvia la cobertura, i per tant canvia la llista: es torna a demanar, no es pedaça.
    propostes: (modelId, fileId = null) =>
      client.get('/api/v1/patterns/sew-relations/propostes/',
        { params: fileId ? { model: modelId, file: fileId } : { model: modelId } }),

    // Confirmar = el gest manual, fet en un clic. En surt exactament el mateix que si el
    // patronista hagués declarat els dos trams i els hagués cosit: dos trams DECLARATS i una
    // costura. Una costura confirmada no és una entitat de segona categoria.
    confirmarProposta: (data) =>
      client.post('/api/v1/patterns/sew-relations/confirmar-proposta/', data),

    // El rebuig és PERSISTENT: el que es diu que no, no torna a sortir. Una eina que reproposa
    // el que ja li han dit que no ensenya a no mirar-la. El que es rebutja és la PARELLA —els
    // seus trams queden lliures per a la proposta bona.
    rebutjarProposta: (data) =>
      client.post('/api/v1/patterns/sew-relations/rebutjar-proposta/', data),

    // ── ASSISTIT (A1): les PINCES que el motor veu a la vora ────────────────
    //
    // Mateix patró que les costures proposades. **No hi ha cap endpoint de confirmació**: una
    // pinça proposada es confirma cridant `pinca()` (aquí sobre) amb els tres punts que el
    // candidat ja porta — el MATEIX camí de codi que els tres clics del taller. Un segon camí per
    // a la mateixa cosa hauria estat un lloc més on la llei de la pinça podria divergir.
    pincesProposades: (modelId, fileId = null) =>
      client.get('/api/v1/patterns/sew-relations/pinces-proposades/',
        { params: fileId ? { model: modelId, file: fileId } : { model: modelId } }),

    rebutjarPinca: (data) =>
      client.post('/api/v1/patterns/sew-relations/rebutjar-pinca/', data),
  },

  // ACCEPTACIÓ DE TOLERÀNCIA (H/T2): el tècnic accepta/desaccepta un desajust, amb rastre
  // append-only. Desacceptar NO esborra: és un esdeveniment nou. `history` llegeix l'auditoria
  // (per model = transversal; l'estat viu de cada costura ja ve inline a `estat`/`acceptacio`).
  tolerance: {
    accept: (sewId, nota = '') => client.post('/api/v1/patterns/sew-tolerance-acceptances/',
      { sew_relation: sewId, accio: 'accepta', nota }),
    unaccept: (sewId, nota = '') => client.post('/api/v1/patterns/sew-tolerance-acceptances/',
      { sew_relation: sewId, accio: 'desaccepta', nota }),
    history: (modelId) => client.get('/api/v1/patterns/sew-tolerance-acceptances/',
      { params: { model: modelId } }),
  },

  // Els REBUIGS de proposta: llegir-los i DESFER-LOS (F/T3). Crear-ne un NO és aquí, és
  // `sew.rebutjarProposta` — la llei del rebuig (clau canònica, idempotència) té una sola
  // porta d'entrada. Desfer-lo no torna a proposar res per ell mateix: només treu la
  // mordassa, i el motor dirà el que vegi la propera vegada que se li demani.
  sewRejections: {
    list: (modelId) => client.get('/api/v1/patterns/sew-proposal-rejections/',
      { params: { model: modelId } }),
    remove: (id) => client.delete(`/api/v1/patterns/sew-proposal-rejections/${id}/`),
  },

  // Trams DECLARATS (W1/T4). La segmentació gir→gir és una proposta del motor (origen
  // 'auto'); un tram DECLARAT és una afirmació humana: "aquest tros de vora existeix i es
  // diu així". Per això té nom i es pot reanomenar. Esborrar-ne un que una costura fa
  // servir rebota amb 409 + les costures que el retenen: deixar-la coixa en silenci seria
  // pitjor que el rebuig.
  // No hi ha `list`: els trams viuen a la geometria (amb origen i nom des de W4), i
  // demanar-los a part era fer dues peticions per a una sola pregunta.
  //
  // Al crear NO s'envien t ni longituds: s'envien dos PUNTS i el servidor resol el tram
  // sobre la geometria — el mateix principi que amb el valor d'un POM. `arc_llarg` tria
  // quin dels dos arcs (dos punts d'una vora tancada en defineixen DOS, no un).
  segments: {
    create: (data) => client.post('/api/v1/patterns/pattern-segments/', data),
    rename: (id, nom) => client.patch(`/api/v1/patterns/pattern-segments/${id}/`, { nom }),
    // RECOL·LOCAR (W4b/T5b): els extrems nous, sobre la MATEIXA fila. Les costures la
    // referencien: esborrar-la i crear-ne una altra els buidaria el costat en silenci. El
    // PROTECT queda només per a ESBORRAR — corregir un tram mal posat no ha d'obligar a
    // desmuntar la costura que el fa servir.
    update: (id, data) => client.patch(`/api/v1/patterns/pattern-segments/${id}/`, data),
    remove: (id) => client.delete(`/api/v1/patterns/pattern-segments/${id}/`),

    // En BLOC (E/T3). El PROTECT que aquí rebota amb 409 hi arriba com a INFORME: en bloc,
    // que un tram es quedi no és l'excepció que atura la feina, és una de les respostes.
    // `retinguts: [{id, motiu: 'en_us', sew_relations: [...]}]`.
    bulkRemove: (ids) =>
      client.post('/api/v1/patterns/pattern-segments/bulk-delete/', { ids }),
  },

  // El render està gated per Authorization, i un <img src> no pot portar capçaleres: es
  // baixa com a blob i es mostra per objectURL. (Les DESCÀRREGUES sí que tenen URL
  // signada al serializer — download_url / download_rul_url —, i per això no es
  // construeixen aquí a mà.)
  renderSvg: (id, piece = '') =>
    client.get(`/api/v1/patterns/pattern-files/${id}/render.svg/`, {
      params: piece ? { piece } : undefined,
      responseType: 'blob',
    }),

  // Escalat i exportació de la niada (S7).
  export: {
    // NOMÉS les versions aprovades. `aprovada` i `is_active` són ortogonals: la versió
    // aprovada d'un model sovint NO és la que la UI serveix per defecte, i qui exporta
    // una niada tria una versió SIGNADA, no la que passava per allà.
    gradingVersions: (id) =>
      client.get(`/api/v1/patterns/pattern-files/${id}/grading-versions/`),

    // El pipeline sencer SENSE bytes: projecció + preview per talla + autovalidació. Si
    // l'exportació ha de fallar, falla aquí — amb el modal obert i el motiu a la vista.
    preview: (id, data) =>
      client.post(`/api/v1/patterns/pattern-files/${id}/export-preview/`, data),

    // Els bytes. Sense `acknowledged: true` el servidor no genera res (403): el gate és
    // una precondició dura, no un registre a posteriori.
    dxf: (id, data) =>
      client.post(`/api/v1/patterns/pattern-files/${id}/export/`, data,
        { responseType: 'blob' }),
    rul: (id, data) =>
      client.post(`/api/v1/patterns/pattern-files/${id}/export-rul/`, data,
        { responseType: 'blob' }),
  },
}

// Sprint M2 — Anàlisi de temps (gated view_team_tasks; set-estimate gated define_tasks).
export const timeAnalysis = {
  byPhase: () => client.get('/api/v1/time-analysis/by-phase/'),               // -> {phases, welford_min_samples}
  tree: (params) => client.get('/api/v1/time-analysis/tree/', { params }),    // ?fase&task_type&garment_type&garment_type_item
  setEstimate: (data) => client.post('/api/v1/time-analysis/set-estimate/', data),   // {garment_type_item, task_type, minutes}
  byModel: (params) => client.get('/api/v1/time-analysis/by-model/', { params }),    // ?model&fase → {models:[{label,nom,est,real,n,fases:[{fase,...,tasks:[...]}]}]}
  captureSeed: (data) => client.post('/api/v1/time-analysis/capture-seed/', data),   // {task_code, minuts} → llavor CAPTURA
}
