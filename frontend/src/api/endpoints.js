import client from './client'

export const auth = {
  login: (username, password) => client.post('/api/token/', { username, password }),
}

export const models = {
  list: (params) => client.get('/api/v1/models/', { params }),
  get: (id) => client.get(`/api/v1/models/${id}/`),
  create: (data) => client.post('/api/v1/models/', data),
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

export const tasks = {
  list: (params) => client.get('/api/v1/model-tasques/', { params }),
  listByModel: (modelId) => client.get('/api/v1/model-tasques/', { params: { model: modelId } }),
}

export const sizeFittings = {
  list: (params) => client.get('/api/v1/size-fittings/', { params }),
  get: (id) => client.get(`/api/v1/size-fittings/${id}/`),
  create: (data) => client.post('/api/v1/size-fittings/', data),
}

export const fittings = {
  list: (params) => client.get('/api/v1/fittings/', { params }),
  listByModel: (modelId) => client.get('/api/v1/size-fittings/', { params: { model: modelId } }),
}

export const gradingVersions = {
  list: (params) => client.get('/api/v1/grading-versions/', { params }),
}

export const gradedSpecLines = {
  list: (params) => client.get('/api/v1/graded-spec-lines/', { params }),
}

export const fittingLines = {
  list: (params) => client.get('/api/v1/fitting-lines/', { params }),
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

export const me = {
  get: () => client.get('/api/v1/me/'),
}
