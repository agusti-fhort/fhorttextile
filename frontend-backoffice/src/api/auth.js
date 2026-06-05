import client from './client'

// Autenticació del backoffice. Endpoints servits per l'app `backoffice` del backend.
const BASE = '/api/backoffice/v1/auth'

export const login = (email, password) =>
  client.post(`${BASE}/login/`, { email, password }).then((r) => r.data)

export const me = () =>
  client.get(`${BASE}/me/`).then((r) => r.data)
