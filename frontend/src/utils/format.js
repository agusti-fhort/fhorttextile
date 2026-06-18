// Helpers de presentació compartits.

// Minuts (enters) → "Hh MMm". Coherent amb el format de TimeTracking.jsx (que
// treballa en SEGONS); aquí l'entrada ja són minuts consolidats del backend.
export function formatMinutes(m) {
  if (m == null) return '—';
  const total = Math.round(m);   // mitjanes del backend poden venir fraccionàries
  const h = Math.floor(total / 60), mm = total % 60;
  return `${h}h ${String(mm).padStart(2, '0')}m`;
}
