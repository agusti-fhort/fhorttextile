
const ESTAT_CONFIG = {
  // Model estats
  'Nou':                { bg: '#1a1a2a', text: '#5a5aaa', border: '#2a2a4a' },
  "Pendent d'inputs":  { bg: '#2a2a1a', text: '#8a7a2a', border: '#3a3a1a' },
  'Preparat':           { bg: '#1a2a1a', text: '#4a9a4a', border: '#2a4a2a' },
  'En curs':            { bg: '#1a1a2a', text: '#4a7aaa', border: '#2a3a5a' },
  'En revisió':         { bg: '#2a1a2a', text: '#8a4a9a', border: '#4a2a5a' },
  'Bloquejat':          { bg: '#2a1a1a', text: '#9a3a3a', border: '#5a2a2a' },
  'Tancat':             { bg: '#1a1a1a', text: '#5a5a5a', border: '#2a2a2a' },
  // Prioritat
  'Baixa':              { bg: '#1a1a1a', text: '#5a5a5a', border: '#2a2a2a' },
  'Normal':             { bg: '#1a2a1a', text: '#4a8a4a', border: '#2a4a2a' },
  'Alta':               { bg: '#2a2a1a', text: '#c27a2a', border: '#3a3a1a' },
  'Urgent':             { bg: '#2a1a1a', text: '#cc4444', border: '#4a2020' },
  // SF estats
  'Pendent':            { bg: '#1a1a1a', text: '#444', border: '#2a2a2a' },
  'Talla base oberta':  { bg: '#1a1a2a', text: '#5a7aaa', border: '#2a2a5a' },
  'Talla base tancada': { bg: '#1a2a2a', text: '#2a8a8a', border: '#1a4a4a' },
  'Talles generades':   { bg: '#1a2a1a', text: '#4a9a6a', border: '#2a5a3a' },
  // Tasca estats
  'Feta':               { bg: '#1a2a1a', text: '#4a9a4a', border: '#2a5a2a' },
  'Bloquejada':         { bg: '#2a1a1a', text: '#7a3a3a', border: '#4a2020' },
}

export function EstatBadge({ estat, size = 'sm' }) {
  if (!estat) return null
  const config = ESTAT_CONFIG[estat] || { bg: '#1a1a2a', text: '#666', border: '#222' }
  const fontSize = size === 'xs' ? 10 : size === 'sm' ? 11 : 12

  return (
    <span style={{
      display: 'inline-block',
      padding: `2px ${size === 'xs' ? 6 : 8}px`,
      borderRadius: 3,
      fontSize,
      fontFamily: 'IBM Plex Mono, monospace',
      fontWeight: 500,
      background: config.bg,
      color: config.text,
      border: `1px solid ${config.border}`,
      whiteSpace: 'nowrap',
      letterSpacing: '0.02em',
    }}>
      {estat}
    </span>
  )
}
