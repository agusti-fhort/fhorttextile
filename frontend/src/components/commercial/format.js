// Helpers de format del sistema visual comercial (compartits per les 4 pantalles).

// Minuts → "Hh Mm" (mai minuts sols). 526 → "8h 46m", 45 → "0h 45m", 60 → "1h 0m".
export function minutesToHhMm(minutes) {
  const total = Math.max(0, Math.round(Number(minutes) || 0))
  const h = Math.floor(total / 60)
  const m = total % 60
  return `${h}h ${m}m`
}

// Nom del tècnic → inicial + cognom. "Anna Puig" → "A. Puig"; "Anna Maria Puig Roca" → "A. Roca";
// un sol mot es manté tal qual; buit → "—".
export function tecnicShort(name) {
  const parts = String(name || '').trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return '—'
  if (parts.length === 1) return parts[0]
  return `${parts[0][0].toUpperCase()}. ${parts[parts.length - 1]}`
}
