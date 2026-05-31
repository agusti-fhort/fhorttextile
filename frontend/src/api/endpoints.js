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
}

// Fitxers del model (read-only) — panell info de fitting (5B.6-B1).
export const modelFitxers = {
  list: (params) => client.get('/api/v1/model-fitxers/', { params }),
}

export const poms = {
  list: (params) => client.get('/api/v1/poms/', { params }),
}

export const garmentTypes = {
  list: (params) => client.get('/api/v1/garment-types/', { params }),
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

export const modelTasks = {
  list: (params) => client.get('/api/v1/model-tasques/', { params }),
  listByModel: (modelId) => client.get('/api/v1/model-tasques/', { params: { model: modelId } }),
}
// Alias retrocompatible
export const tasks = modelTasks

export const sizeFittings = {
  list: (params) => client.get('/api/v1/size-fittings/', { params }),
  get: (id) => client.get(`/api/v1/size-fittings/${id}/`),
  create: (data) => client.post('/api/v1/size-fittings/', data),
}

// Sprint 5B.6 — Fitting sessions (capa nova).
export const fittingSessions = {
  list: (params) => client.get('/api/v1/fitting-sessions/', { params }),
  get: (id) => client.get(`/api/v1/fitting-sessions/${id}/`),
  create: (data) => client.post('/api/v1/fitting-sessions/', data),
  // PATCH del context (notes/model_persona/assistents/lloc/responsable) — autosave capçalera.
  update: (id, data) => client.patch(`/api/v1/fitting-sessions/${id}/`, data),
  canAdvance: (id) => client.get(`/api/v1/fitting-sessions/${id}/can-advance/`),
  createPiece: (id, modelId) => client.post(`/api/v1/fitting-sessions/${id}/create-piece/`, { model_id: modelId }),
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

// NOTE: the Django backend does not expose /api/v1/me/ yet.
// The callers (Settings, KanbanTasks, UserProfilePage) wrap the call
// with .catch(()=>{}) to fail gracefully while the endpoint does not exist.
export const me = {
  get: () => client.get('/api/v1/me/'),
}
