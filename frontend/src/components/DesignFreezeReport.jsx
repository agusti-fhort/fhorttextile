
const GARMENT_ICONS = {
  'dress': '👗', 'top': '👚', 'trousers': '👖', 'skirt': '🩱',
  'jacket': '🧥', 'coat': '🧥', 'shirt': '👔', 'default': '🧵'
}

export function DesignFreezeReport({ result, onConfirm, onReject }) {
  if (!result) return null
  const { extracted, design_freeze, filename } = result
  const pass = design_freeze?.pass

  const val = (field) => {
    const v = extracted?.[field]
    if (typeof v === 'object' && v !== null) return v.value
    return v
  }
  const conf = (field) => {
    const v = extracted?.[field]
    if (typeof v === 'object' && v !== null) return v.confidence
    return 'low'
  }

  const confColor = (c) => c === 'high' ? '#4a9a4a' : c === 'medium' ? '#c27a2a' : '#cc4444'

  const poms = extracted?.poms || []
  const hasGrading = extracted?.has_grading_table
  const thumbnail = extracted?.thumbnail_description

  return (
    <div style={{ fontSize: 12 }}>

      {/* Resultat gate — fons negre, label "PASS" en gold, "RETORNAT" en blanc */}
      <div style={{
        padding: '10px 16px',
        borderRadius: 6,
        marginBottom: 16,
        background: '#1d1d1b',
        border: '1px solid #1d1d1b',
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <span style={{ fontSize: 18, color: pass ? '#c27a2a' : '#ffffff' }}>{pass ? '✓' : '✗'}</span>
        <div>
          <div style={{ fontWeight: 600, color: '#ffffff', fontSize: 13 }}>
            Design Freeze — <span style={{ color: pass ? '#c27a2a' : '#ffffff' }}>{pass ? 'PASS' : 'RETORNAT'}</span>
          </div>
          <div style={{ color: '#868685', fontSize: 11 }}>{filename}</div>
        </div>
        <div style={{ marginLeft: 'auto', fontSize: 11, color: '#868685' }}>
          {extracted?.document_type?.replace('_', ' ')}
        </div>
      </div>

      {/* Blockers */}
      {design_freeze?.blockers?.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ color: '#cc4444', fontSize: 11, marginBottom: 6, letterSpacing: '.05em', textTransform: 'uppercase' }}>
            Camps bloquejants ({design_freeze.blockers.length})
          </div>
          {design_freeze.blockers.map((b, i) => (
            <div key={i} style={{
              padding: '5px 10px', marginBottom: 4,
              background: 'var(--bg-muted)', border: '1px solid #4a2020', borderRadius: 4,
              color: '#cc6666', fontSize: 11,
              display: 'flex', alignItems: 'center', gap: 8,
            }}>
              <span>✗</span> {b}
            </div>
          ))}
        </div>
      )}

      {/* Warnings */}
      {design_freeze?.warnings?.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ color: '#c27a2a', fontSize: 11, marginBottom: 6, letterSpacing: '.05em', textTransform: 'uppercase' }}>
            Avisos ({design_freeze.warnings.length})
          </div>
          {design_freeze.warnings.map((w, i) => (
            <div key={i} style={{
              padding: '5px 10px', marginBottom: 4,
              background: 'var(--gold-pale)', border: '1px solid var(--gold-l)', borderRadius: 4,
              color: '#c27a2a', fontSize: 11,
              display: 'flex', alignItems: 'center', gap: 8,
            }}>
              <span>⚠</span> {typeof w === 'string' ? w : JSON.stringify(w)}
            </div>
          ))}
        </div>
      )}

      {/* Camps extrets */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 8, letterSpacing: '.05em', textTransform: 'uppercase' }}>
          Dades extretes
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
          {[
            ['Marca', 'brand'],
            ['Estil', 'style_name'],
            ['Codi', 'style_code'],
            ['Temporada', 'season'],
            ['Any', 'year'],
            ['Prenda', 'garment_type'],
            ['Material', 'main_fabric'],
            ['Composició', 'fabric_composition'],
            ['Talla base', 'base_size'],
            ['Run talles', 'size_run'],
            ['Dissenyador', 'designer'],
            ['Patronista', 'patternmaker'],
          ].map(([label, field]) => {
            const v = val(field)
            const c = conf(field)
            return (
              <div key={field} style={{
                padding: '4px 8px',
                background: 'var(--bg-card)',
                borderRadius: 3,
                display: 'flex', justifyContent: 'space-between', gap: 8,
              }}>
                <span style={{ color: 'var(--text-main)' }}>{label}</span>
                <span style={{ color: v ? '#aaa' : 'var(--border)', textAlign: 'right', maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {v || '—'}
                  {v && <span style={{ marginLeft: 4, fontSize: 9, color: confColor(c) }}>●</span>}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* POMs detectats */}
      {poms.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 8, letterSpacing: '.05em', textTransform: 'uppercase' }}>
            POMs detectats ({poms.length}) {hasGrading && '· taula de grading inclosa'}
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {poms.map((p, i) => (
              <div key={i} style={{
                padding: '3px 8px',
                background: '#f5e6d0',
                border: '1px solid #e0c8a0',
                borderRadius: 4,
                fontSize: 11,
                color: '#1d1d1b',
              }}>
                <strong style={{ color: '#1d1d1b', fontWeight: 600 }}>{p.code}</strong>
                {p.base_value_cm && <span style={{ color: '#c27a2a', marginLeft: 4 }}>{p.base_value_cm}</span>}
              </div>
            ))}
          </div>
          {poms.some(p => !p.base_value_cm) && (
            <div style={{ fontSize: 10, color: 'var(--text-main)', marginTop: 4 }}>
              POMs sense valor de talla base — es generaran des de les Grading Rules del client
            </div>
          )}
        </div>
      )}

      {/* Thumbnail description */}
      {thumbnail && (
        <div style={{
          padding: '8px 12px', marginBottom: 16,
          background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 4,
          fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic', lineHeight: 1.5,
        }}>
          <span style={{ color: 'var(--text-main)', fontStyle: 'normal' }}>Descripció visual: </span>
          {thumbnail}
        </div>
      )}

      {/* Botons */}
      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
        <button onClick={onReject} style={{
          padding: '7px 16px', background: 'transparent',
          color: 'var(--text-muted)', border: '1px solid var(--border)', borderRadius: 4,
          fontSize: 11, cursor: 'pointer',
        }}>
          ← Tornar
        </button>
        {pass && (
          <button onClick={() => onConfirm(extracted)} style={{
            padding: '7px 16px', background: 'var(--bg-muted)',
            color: '#4a9a4a', border: '1px solid #2a4a2a', borderRadius: 4,
            fontSize: 11, cursor: 'pointer', 
          }}>
            Continuar →
          </button>
        )}
      </div>
    </div>
  )
}
