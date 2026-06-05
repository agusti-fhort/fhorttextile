// Configuració única dels estats de tenant. Compartida per la llista i el detall
// perquè el badge sigui idèntic a tot arreu.
//
// Colors via tokens d'estat de index.css:
//   ACTIU=--ok, ONBOARDING=--warn, SUSPÈS=--err, BAIXA=--gray (text-muted).
export const ESTATS = {
  onboarding: { key: 'onboarding', label: 'ONBOARDING', color: 'var(--warn)', bg: 'var(--warn-bg)' },
  actiu:      { key: 'actiu',      label: 'ACTIU',      color: 'var(--ok)',   bg: 'var(--ok-bg)' },
  suspes:     { key: 'suspes',     label: 'SUSPÈS',     color: 'var(--err)',  bg: 'var(--err-bg)' },
  baixa:      { key: 'baixa',      label: 'BAIXA',      color: 'var(--text-muted)', bg: 'var(--bg-muted)' },
}

// Ordre de presentació (tabs + selector de canvi d'estat).
export const ESTAT_ORDRE = ['onboarding', 'actiu', 'suspes', 'baixa']

// Normalitza qualsevol forma rebuda del backend ('SUSPÈS', 'suspes', 'Suspès'…)
// a la clau canònica sense accents.
export function normalitzaEstat(raw) {
  const s = (raw ?? '').toString().toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
  return ESTATS[s] ? s : (s || 'onboarding')
}

// Retorna la config d'estat (amb fallback segur).
export function estatConfig(raw) {
  return ESTATS[normalitzaEstat(raw)] || ESTATS.onboarding
}
