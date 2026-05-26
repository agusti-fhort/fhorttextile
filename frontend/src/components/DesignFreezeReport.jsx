
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
    <div style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 12 }}>

      {/* Resultat gate */}
      <div style={{
        padding: '10px 16px',
        borderRadius: 6,
        marginBottom: 16,
        background: pass ? '#1a2a1a' : '#2a1a1a',
        border: `1px solid ${pass ? '#2a4a2a' : '#4a2020'}`,
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <span style={{ fontSize: 18 }}>{pass ? '✓' : '✗'}</span>
        <div>
          <div style={{ fontWeight: 600, color: pass ? '#4a9a4a' : '#cc4444', fontSize: 13 }}>
            Design Freeze — {pass ? 'PASS' : 'RETORNAT'}
          </div>
          <div style={{ color: '#666', fontSize: 11 }}>{filename}</div>
        </div>
        <div style={{ marginLeft: 'auto', fontSize: 11, color: '#555' }}>
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
              background: '#2a1a1a', border: '1px solid #4a2020', borderRadius: 4,
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
              background: '#2a1a0a', border: '1px solid #4a3010', borderRadius: 4,
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
        <div style={{ color: '#555', fontSize: 11, marginBottom: 8, letterSpacing: '.05em', textTransform: 'uppercase' }}>
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
                background: '#111',
                borderRadius: 3,
                display: 'flex', justifyContent: 'space-between', gap: 8,
              }}>
                <span style={{ color: '#444' }}>{label}</span>
                <span style={{ color: v ? '#aaa' : '#2a2a2a', textAlign: 'right', maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
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
          <div style={{ color: '#555', fontSize: 11, marginBottom: 8, letterSpacing: '.05em', textTransform: 'uppercase' }}>
            POMs detectats ({poms.length}) {hasGrading && '· taula de grading inclosa'}
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {poms.map((p, i) => (
              <div key={i} style={{
                padding: '3px 8px',
                background: p.base_value_cm ? '#1a2a1a' : '#1a1a1a',
                border: `1px solid ${p.base_value_cm ? '#2a4a2a' : '#2a2a2a'}`,
                borderRadius: 3,
                fontSize: 11,
                color: p.base_value_cm ? '#5a9a5a' : '#555',
              }}>
                <strong>{p.code}</strong>
                {p.base_value_cm && <span style={{ color: '#888', marginLeft: 4 }}>{p.base_value_cm}</span>}
              </div>
            ))}
          </div>
          {poms.some(p => !p.base_value_cm) && (
            <div style={{ fontSize: 10, color: '#444', marginTop: 4 }}>
              POMs sense valor de talla base — es generaran des de les Grading Rules del client
            </div>
          )}
        </div>
      )}

      {/* Thumbnail description */}
      {thumbnail && (
        <div style={{
          padding: '8px 12px', marginBottom: 16,
          background: '#111', border: '1px solid #2a2a2a', borderRadius: 4,
          fontSize: 11, color: '#666', fontStyle: 'italic', lineHeight: 1.5,
        }}>
          <span style={{ color: '#444', fontStyle: 'normal' }}>Descripció visual: </span>
          {thumbnail}
        </div>
      )}

      {/* Botons */}
      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
        <button onClick={onReject} style={{
          padding: '7px 16px', background: 'transparent',
          color: '#555', border: '1px solid #2a2a2a', borderRadius: 4,
          fontSize: 11, cursor: 'pointer',
        }}>
          ← Tornar
        </button>
        {pass && (
          <button onClick={() => onConfirm(extracted)} style={{
            padding: '7px 16px', background: '#1a2a1a',
            color: '#4a9a4a', border: '1px solid #2a4a2a', borderRadius: 4,
            fontSize: 11, cursor: 'pointer', fontFamily: 'IBM Plex Mono, monospace',
          }}>
            ✓ Crear model
          </button>
        )}
      </div>
    </div>
  )
}
