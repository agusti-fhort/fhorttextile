import client from './client'

export const auth = {
  login: (username, password) => client.post('/api/token/', { username, password }),
}

export const models = {
  list: (params) => client.get('/api/v1/models/', { params }),
  get: (id) => client.get(`/api/v1/models/${id}/`),
}

export const poms = {
  list: (params) => client.get('/api/v1/poms/', { params }),
}

export const garmentTypes = {
  list: () => client.get('/api/v1/garment-types/'),
}

export const garmentGroups = {
  list: () => client.get('/api/v1/garment-groups/'),
}

export const sizeSystems = {
  list: () => client.get('/api/v1/size-systems/'),
}

export const gradingRuleSets = {
  list: () => client.get('/api/v1/grading-rule-sets/'),
}

export const tasks = {
  listByModel: (modelId) => client.get('/api/v1/model-tasques/', { params: { model: modelId } }),
}

export const fittings = {
  listByModel: (modelId) => client.get('/api/v1/size-fittings/', { params: { model: modelId } }),
}

export const alerts = {
  list: (params) => client.get('/api/v1/pom-alerts/', { params }),
}
