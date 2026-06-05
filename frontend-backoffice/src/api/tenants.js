import client from './client'

// API de tenants del backoffice (Sprint 2). Endpoints servits per l'app
// `backoffice` sobre el schema public.
const BASE = '/api/backoffice/v1'

export const getTenants = (params = {}) =>
  client.get(`${BASE}/tenants/`, { params }).then((r) => r.data)

export const getTenant = (id) =>
  client.get(`${BASE}/tenants/${id}/`).then((r) => r.data)

export const updateEstat = (id, estat, motiu) =>
  client.post(`${BASE}/tenants/${id}/update_estat/`, { estat, motiu }).then((r) => r.data)

export const getPlans = () =>
  client.get(`${BASE}/plans/`).then((r) => r.data)

// ── Dades de mostra ───────────────────────────────────────────────────────
// El backend del Sprint 2 pot no estar migrat encara. Les pàgines fan servir
// aquestes dades com a fallback (amb avís visible) per poder desenvolupar la UI.
export const MOCK_TENANTS = [
  {
    id: 1, codi_tenant: '001', nom: 'Fhort Demo Tèxtil', tipologia: 'Confecció',
    estat: 'actiu', plan: 'Pro', plan_nom: 'Pro', data_alta: '2025-11-12',
    rao_social: 'Fhort Demo Tèxtil SL', nif: 'B12345678',
    adreca: "C/ Indústria 22, Igualada", pais: 'ES',
    email_facturacio: 'facturacio@fhortdemo.cat', stripe_configurat: true,
    data_suspensio: null, data_baixa: null,
  },
  {
    id: 2, codi_tenant: '002', nom: 'Atelier Nord', tipologia: 'Moda',
    estat: 'onboarding', plan: 'Starter', plan_nom: 'Starter', data_alta: '2026-01-03',
    rao_social: 'Atelier Nord SCP', nif: 'J87654321',
    adreca: 'Av. Catalunya 5, Manresa', pais: 'ES',
    email_facturacio: 'admin@ateliernord.cat', stripe_configurat: false,
    data_suspensio: null, data_baixa: null,
  },
  {
    id: 3, codi_tenant: '003', nom: 'TexLusitana', tipologia: 'Confecció',
    estat: 'suspes', plan: 'Pro', plan_nom: 'Pro', data_alta: '2025-08-21',
    rao_social: 'TexLusitana Lda', nif: 'PT501234567',
    adreca: 'Rua do Tecido 10, Porto', pais: 'PT',
    email_facturacio: 'billing@texlusitana.pt', stripe_configurat: true,
    data_suspensio: '2026-04-15', data_baixa: null,
  },
  {
    id: 4, codi_tenant: '004', nom: 'Maglieria Sud', tipologia: 'Gènere de punt',
    estat: 'baixa', plan: 'Starter', plan_nom: 'Starter', data_alta: '2025-05-09',
    rao_social: 'Maglieria Sud Srl', nif: 'IT09876543210',
    adreca: 'Via Tessile 8, Prato', pais: 'IT',
    email_facturacio: 'amministrazione@maglieriasud.it', stripe_configurat: false,
    data_suspensio: '2025-12-01', data_baixa: '2026-02-28',
  },
]

export const MOCK_PLANS = [
  { id: 1, nom: 'Starter' },
  { id: 2, nom: 'Pro' },
  { id: 3, nom: 'Enterprise' },
]
