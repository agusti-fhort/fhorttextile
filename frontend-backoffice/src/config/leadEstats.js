// Configuració única dels estats de lead. Compartida per la llista i el detall
// (mateix patró que config/estats.js per als tenants).
export const LEAD_ESTATS = {
  nou:       { key: 'nou',       label: 'NOU',       color: 'var(--warn)',       bg: 'var(--warn-bg)' },
  contactat: { key: 'contactat', label: 'CONTACTAT',  color: 'var(--gold)',       bg: 'var(--gold-pale)' },
  tancat:    { key: 'tancat',    label: 'TANCAT',     color: 'var(--text-muted)', bg: 'var(--bg-muted)' },
}

// Ordre de presentació (selector de canvi d'estat al detall).
export const LEAD_ESTAT_ORDRE = ['nou', 'contactat', 'tancat']

export function leadEstatConfig(raw) {
  const key = (raw ?? '').toString().toLowerCase()
  return LEAD_ESTATS[key] || LEAD_ESTATS.nou
}
