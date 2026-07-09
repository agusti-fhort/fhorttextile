// <EntityCard> — contenció visual d'una entitat repetible (un model, un bloc agrupat) del sistema
// comercial. Capçalera CREAM amb identificació, cos (slot) i peu de subtotal. Res de files flotant.
// Principi de jerarquia: la identificació (`name`) és IGUAL de gran que la `reference`; el subtotal
// és gran. Sense text propi (tot per props). `ModelCard` és l'àlies semàntic per a un model.
const MONO = 'IBM Plex Mono, monospace'

export default function EntityCard({ reference, name, meta, subtotalLabel, subtotal, children, style }) {
  return (
    <div style={{
      border: '0.5px solid var(--border)', borderRadius: 12, overflow: 'hidden',
      background: 'var(--white)', ...style,
    }}>
      {/* Capçalera cream — identificació */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px',
        background: 'var(--model-band)', borderBottom: '0.5px solid var(--border)', flexWrap: 'wrap',
      }}>
        {reference && <span style={{ fontFamily: MONO, fontWeight: 700, color: 'var(--gold)', fontSize: 'var(--fs-h3)' }}>{reference}</span>}
        {name && <span style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, color: 'var(--text-main)' }}>{name}</span>}
        {meta != null && <span style={{ marginLeft: 'auto', fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', fontFamily: MONO }}>{meta}</span>}
      </div>

      {/* Cos */}
      <div style={{ padding: '8px 14px' }}>{children}</div>

      {/* Peu de subtotal (gran, a la dreta) */}
      {subtotal != null && (
        <div style={{
          display: 'flex', justifyContent: 'flex-end', alignItems: 'baseline', gap: 12,
          padding: '10px 14px', borderTop: '0.5px solid var(--border)',
        }}>
          {subtotalLabel && <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>{subtotalLabel}</span>}
          <span style={{ fontFamily: MONO, fontWeight: 700, fontSize: 'var(--fs-h3)' }}>{subtotal}</span>
        </div>
      )}
    </div>
  )
}

// Àlies semàntic: una card de model és una EntityCard.
export const ModelCard = EntityCard
