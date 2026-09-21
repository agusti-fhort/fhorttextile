import client from './client'

// API de leads del backoffice (P-LEADS L3). Endpoints servits per l'app
// `backoffice` sobre el schema public. L'alta és la porta pública
// (leads/public/, consumida per ftt-web, no per aquesta SPA).
const BASE = '/api/backoffice/v1'

export const getLeads = (params = {}) =>
  client.get(`${BASE}/leads/`, { params }).then((r) => r.data)

export const getLead = (id) =>
  client.get(`${BASE}/leads/${id}/`).then((r) => r.data)

// NOMÉS estat i notes són escrivibles (la resta és read-only al backend).
export const updateLead = (id, data) =>
  client.patch(`${BASE}/leads/${id}/`, data).then((r) => r.data)

export const deleteLead = (id) =>
  client.delete(`${BASE}/leads/${id}/`).then((r) => r.data)

// {nou, contactat, tancat, tots} — font única del número a cada pestanya de LeadsPage.
export const getLeadCounts = () =>
  client.get(`${BASE}/leads/counts/`).then((r) => r.data)

// ── Dades de mostra ───────────────────────────────────────────────────────
// NOMÉS per a desenvolupament local (mateixa regla que api/tenants.js): a
// staging/PROD un error d'API mostra un ERROR, mai dades inventades.
export const MOCK_LEADS = [
  {
    id: 1, nom: 'Maria Puig', empresa: 'Puig Confecció SL', email: 'maria@puigconfeccio.example',
    missatge: 'Voldria una demo del motor de patrons per al nostre equip de patronatge.',
    idioma: 'ca', pagina_origen: '/ca/plataforma/motor-de-patrons/',
    consentiment: true, privacy_version: 'v1', ip: '198.51.100.7',
    estat: 'nou', notes: '', notificat: true, created_at: '2026-09-18T09:12:00Z',
  },
  {
    id: 2, nom: 'Jean Dubois', empresa: 'Atelier Nord', email: 'jean@ateliernord.example',
    missatge: 'Interested in the planning module for our production team.',
    idioma: 'en', pagina_origen: '/platform/planning/',
    consentiment: true, privacy_version: 'v1', ip: '203.0.113.44',
    estat: 'contactat', notes: 'Trucat el 19/09, esperant resposta.', notificat: true,
    created_at: '2026-09-17T15:40:00Z',
  },
  {
    id: 3, nom: 'Laura Gómez', empresa: '', email: 'laura.gomez@example.com',
    missatge: 'Necesitamos digitalizar nuestro proceso de graduación de tallas.',
    idioma: 'es', pagina_origen: '/es/',
    consentiment: true, privacy_version: 'v1', ip: '192.0.2.10',
    estat: 'tancat', notes: 'No segueix — pressupost fora d’abast.', notificat: false,
    created_at: '2026-09-10T11:05:00Z',
  },
]
