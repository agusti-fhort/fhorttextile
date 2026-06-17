import { useTranslation } from 'react-i18next'

const GARMENT_ICONS = {
  'dress': '👗', 'top': '👚', 'trousers': '👖', 'skirt': '🩱',
  'jacket': '🧥', 'coat': '🧥', 'shirt': '👔', 'default': '🧵'
}

export function DesignFreezeReport({ result, onConfirm, onReject }) {
  const { t } = useTranslation()
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

  const confColor = (c) => c === 'high' ? '#4a9a4a' : c === 'medium' ? 'var(--gold)' : '#cc4444'

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
        background: 'var(--text-main)',
        border: '1px solid var(--text-main)',
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <span style={{ fontSize: 18, color: pass ? 'var(--gold)' : 'var(--white)' }}>{pass ? '✓' : '✗'}</span>
        <div>
          <div style={{ fontWeight: 600, color: 'var(--white)', fontSize: 13 }}>
            Design Freeze — <span style={{ color: pass ? 'var(--gold)' : 'var(--white)' }}>{pass ? 'PASS' : t('design_freeze.returned')}</span>
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>{filename}</div>
        </div>
        <div style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-muted)' }}>
          {extracted?.document_type?.replace('_', ' ')}
        </div>
      </div>

      {/* Blockers */}
      {design_freeze?.blockers?.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ color: '#cc4444', fontSize: 11, marginBottom: 6, letterSpacing: '.05em', textTransform: 'uppercase' }}>
            {t('design_freeze.blockers', { count: design_freeze.blockers.length })}
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
          <div style={{ color: 'var(--gold)', fontSize: 11, marginBottom: 6, letterSpacing: '.05em', textTransform: 'uppercase' }}>
            {t('design_freeze.warnings', { count: design_freeze.warnings.length })}
          </div>
          {design_freeze.warnings.map((w, i) => (
            <div key={i} style={{
              padding: '5px 10px', marginBottom: 4,
              background: 'var(--gold-pale)', border: '1px solid var(--gold-l)', borderRadius: 4,
              color: 'var(--gold)', fontSize: 11,
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
          {t('design_freeze.extracted_data')}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
          {[
            ['brand', 'brand'],
            ['style', 'style_name'],
            ['code', 'style_code'],
            ['season', 'season'],
            ['year', 'year'],
            ['garment', 'garment_type'],
            ['material', 'main_fabric'],
            ['composition', 'fabric_composition'],
            ['base_size', 'base_size'],
            ['size_run', 'size_run'],
            ['designer', 'designer'],
            ['patternmaker', 'patternmaker'],
          ].map(([labelKey, field]) => {
            const v = val(field)
            const c = conf(field)
            return (
              <div key={field} style={{
                padding: '4px 8px',
                background: 'var(--bg-card)',
                borderRadius: 3,
                display: 'flex', justifyContent: 'space-between', gap: 8,
              }}>
                <span style={{ color: 'var(--text-main)' }}>{t(`design_freeze.field.${labelKey}`)}</span>
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
            {t('design_freeze.poms_detected', { count: poms.length })} {hasGrading && t('design_freeze.grading_included')}
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {poms.map((p, i) => (
              <div key={i} style={{
                padding: '3px 8px',
                background: '#f5e6d0',
                border: '1px solid #e0c8a0',
                borderRadius: 4,
                fontSize: 11,
                color: 'var(--text-main)',
              }}>
                <strong style={{ color: 'var(--text-main)', fontWeight: 600 }}>{p.code}</strong>
                {p.base_value_cm && <span style={{ color: 'var(--gold)', marginLeft: 4 }}>{p.base_value_cm}</span>}
              </div>
            ))}
          </div>
          {poms.some(p => !p.base_value_cm) && (
            <div style={{ fontSize: 10, color: 'var(--text-main)', marginTop: 4 }}>
              {t('design_freeze.poms_no_base')}
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
          <span style={{ color: 'var(--text-main)', fontStyle: 'normal' }}>{t('design_freeze.visual_description')}</span>
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
          ← {t('app.back')}
        </button>
        {pass && (
          <button onClick={() => onConfirm(extracted)} style={{
            padding: '7px 16px', background: 'var(--bg-muted)',
            color: '#4a9a4a', border: '1px solid #2a4a2a', borderRadius: 4,
            fontSize: 11, cursor: 'pointer', 
          }}>
            {t('design_freeze.continue')} →
          </button>
        )}
      </div>
    </div>
  )
}
