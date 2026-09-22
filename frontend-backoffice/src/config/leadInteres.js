// Configuració única de l'interès (origen comercial) d'un lead. Mateix patró
// que config/leadEstats.js — font única per a la llista, el filtre i el detall.
export const LEAD_INTERES = {
  saas:    { key: 'saas',    label: 'SaaS' },
  studio:  { key: 'studio',  label: 'Studio' },
  early:   { key: 'early',   label: 'Accés anticipat' },
  other:   { key: 'other',   label: 'Altres' },
}

export const LEAD_INTERES_ORDRE = ['saas', 'studio', 'early', 'other']

export function leadInteresLabel(raw) {
  const key = (raw ?? '').toString().toLowerCase()
  return LEAD_INTERES[key]?.label || '—'
}
