// Àtoms de UI del wizard de model, EXTRETS perquè el pas de Graduació pugui viure fora d'ell.
//
// Fins al 31/07 vivien dins `ModelWizard.jsx` i eren privats. El pas de Graduació ara s'obre
// també com a OVERLAY sobre Mesures (el gest que l'Agus vol), i el component ha de ser UN de
// sol per als dos llocs — MAI una còpia. Aquests àtoms se n'han vingut amb ell; el wizard els
// torna a importar d'aquí i els fa servir exactament igual.
//
// Res de nou: el codi és el mateix que hi havia, moguts de fitxer i prou.
export const MONO = 'IBM Plex Mono, monospace'

export const labelStyle = {
  fontSize: 'var(--fs-body)', color: 'var(--gray)', textTransform: 'uppercase',
  letterSpacing: '.04em', fontFamily: MONO,
}

export function Field({ label, children }) {
  return (
    <div style={{ flex: '1 1 auto' }}>
      <div style={{ ...labelStyle, marginBottom: 6 }}>{label}</div>
      {children}
    </div>
  )
}

export function Chip({ active, onClick, disabled, motiu, children }) {
  return (
    <button type="button" onClick={onClick} disabled={disabled} title={motiu || undefined} style={{
      padding: '6px 14px', borderRadius: 6, fontFamily: MONO, fontSize: 'var(--fs-body)',
      border: active ? '1.5px solid var(--warn)' : '0.5px solid var(--gray-l)',
      background: active ? 'var(--warn)' : 'transparent', color: active ? 'var(--white)' : 'var(--text-main)',
      cursor: disabled ? 'not-allowed' : 'pointer', fontWeight: active ? 500 : 400,
      opacity: (disabled || motiu) && !active ? 0.5 : 1,
    }}>{children}</button>
  )
}

// Xip de NOMÉS LECTURA: el context fix de la peça i les talles al capdamunt del pas de
// Graduació (target · construcció · grup · sistema). No es tria aquí; es recorda.
export function ReadChip({ label, value }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2, padding: '6px 12px', borderRadius: 6, border: '0.5px solid var(--gray-l)', background: 'var(--bg-card)', minWidth: 90 }}>
      <span style={{ fontFamily: MONO, fontSize: 'var(--fs-caption)', color: 'var(--gray)', textTransform: 'uppercase', letterSpacing: '.04em' }}>{label}</span>
      <span style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-main)', fontWeight: 500 }}>{value}</span>
    </div>
  )
}
