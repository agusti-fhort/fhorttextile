// <EntityCard> — la contenció visual d'una entitat repetible dins d'un document (un model, un
// bloc agrupat). Capçalera d'identificació, cos (slot) i peu de subtotal. Res de files flotant.
//
// **LA FRANJA CREMA SE'N VA.** La capçalera anava sobre `--model-band` (#f7efe1), un crema de la
// mateixa família que `--gold-pale`, que la §1 ha **ELIMINAT del sistema**: «cap superfície ni
// estat». La §1 diu que TOT panell, targeta i capçalera és `--white`, i el que separa la
// capçalera del cos és un FILET, no un fons. El que la franja feia —dir «aquí comença una
// entitat»— ho fa ara la jerarquia: el codi en caption, el nom en pes de secció, i el filet.
//
// El codi tampoc va en `--gold` pes 700: el daurat és marca i selecció, no una dada (§8c). El
// SUBTOTAL sí que porta pes, perquè és la xifra que la targeta existeix per dir.
//
// `ModelCard` és l'àlies semàntic per a un model. Sense text propi: tot per props.
const MONO = 'IBM Plex Mono, monospace'

export default function EntityCard({ reference, name, meta, subtotalLabel, subtotal, children, style }) {
  return (
    <div style={{
      borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--line)',
      borderRadius: 'var(--r-card)', overflow: 'hidden', background: 'var(--panel)', ...style,
    }}>
      {/* Identificació */}
      <div style={{
        display: 'flex', alignItems: 'baseline', gap: 10, padding: '10px 14px', flexWrap: 'wrap',
        background: 'var(--panel)',
        borderBottomWidth: 1, borderBottomStyle: 'solid', borderBottomColor: 'var(--line)',
      }}>
        {reference && (
          <span style={{
            fontFamily: MONO, fontSize: 'var(--fs-caption)', lineHeight: '12px',
            letterSpacing: '.08em', textTransform: 'uppercase',
            color: 'var(--text-soft)', fontWeight: 600,
          }}>{reference}</span>
        )}
        {name && (
          <span style={{
            fontSize: 'var(--fs-h3)', lineHeight: '20px', fontWeight: 600, color: 'var(--text-main)',
          }}>{name}</span>
        )}
        {meta != null && (
          <span style={{
            marginLeft: 'auto', fontSize: 'var(--fs-caption)', color: 'var(--text-soft)', fontFamily: MONO,
          }}>{meta}</span>
        )}
      </div>

      {/* Cos */}
      <div style={{ padding: '8px 14px' }}>{children}</div>

      {/* Peu de subtotal (a la dreta, i amb pes: és la xifra que la targeta existeix per dir) */}
      {subtotal != null && (
        <div style={{
          display: 'flex', justifyContent: 'flex-end', alignItems: 'baseline', gap: 12,
          padding: '10px 14px',
          borderTopWidth: 1, borderTopStyle: 'solid', borderTopColor: 'var(--line)',
        }}>
          {subtotalLabel && (
            <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)', fontFamily: MONO }}>
              {subtotalLabel}
            </span>
          )}
          <span style={{ fontFamily: MONO, fontWeight: 600, fontSize: 'var(--fs-h3)', color: 'var(--text-main)' }}>
            {subtotal}
          </span>
        </div>
      )}
    </div>
  )
}

// Àlies semàntic: una card de model és una EntityCard.
export const ModelCard = EntityCard
