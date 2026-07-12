import { useTranslation } from 'react-i18next'

/**
 * Panell del treball d'anotació: què s'ha marcat i què s'ha declarat.
 *
 * NOMENCLATURA (convenció de la casa): el codi canònic mana i el nom en la llengua de
 * l'usuari va a sota, en gris petit. El codi és el que viatja al DXF exportat i el que el
 * grading reconeix; el nom és per a qui mira.
 */
export default function AnnotationPanel({
  poms, sews, pieces, mode,
  onEsborraPom, onEsborraSew,
}) {
  const { t } = useTranslation()

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {/* ── POMs ancorats ─────────────────────────────────────────────────── */}
      <div>
        <h4 style={{
          fontSize: 'var(--fs-label)', textTransform: 'uppercase', letterSpacing: '0.03em',
          color: 'var(--text-muted)', margin: '0 0 0.35rem',
        }}>
          {t('pattern.poms_anchored', { n: poms.length })}
        </h4>
        {poms.length === 0 ? (
          <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', margin: 0 }}>
            {t('pattern.poms_empty')}
          </p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {poms.map(p => (
              <div
                key={p.id}
                style={{
                  display: 'flex', alignItems: 'center', gap: '0.5rem',
                  border: '1px solid var(--border)', borderRadius: 4,
                  padding: '0.3rem 0.5rem', background: 'var(--bg-card)',
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 'var(--fs-body)', fontWeight: 600 }}>
                    {p.pom_code}
                  </div>
                  <div style={{
                    fontSize: 'var(--fs-caption)', color: 'var(--text-muted)',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {p.pom_nom} · {p.peca}
                  </div>
                </div>
                <span style={{
                  fontFamily: 'var(--mono)', fontSize: 'var(--fs-body)',
                  color: p.valor_mesurat_cm == null ? 'var(--err)' : 'var(--text-main)',
                }}>
                  {p.valor_mesurat_cm != null
                    ? `${p.valor_mesurat_cm} cm`
                    : t('pattern.pom_unmeasured')}
                </span>
                {mode !== 'view' && (
                  <button
                    onClick={() => onEsborraPom(p.id)}
                    aria-label={t('app.delete')}
                    style={{
                      background: 'none', border: 'none', cursor: 'pointer',
                      color: 'var(--text-muted)',
                    }}
                  >
                    <i className="ti ti-trash" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Costures ──────────────────────────────────────────────────────── */}
      <div>
        <h4 style={{
          fontSize: 'var(--fs-label)', textTransform: 'uppercase', letterSpacing: '0.03em',
          color: 'var(--text-muted)', margin: '0 0 0.35rem',
        }}>
          {t('pattern.sews', { n: sews.length })}
        </h4>
        {sews.length === 0 ? (
          <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', margin: 0 }}>
            {t('pattern.sews_empty')}
          </p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {sews.map(s => {
              const e = s.estat || {}
              return (
                <div
                  key={s.id}
                  style={{
                    border: `1px solid ${e.casa ? 'var(--ok)' : 'var(--err)'}`,
                    background: e.casa ? 'var(--ok-bg)' : 'var(--err-bg)',
                    borderRadius: 4, padding: '0.35rem 0.5rem',
                    display: 'flex', alignItems: 'flex-start', gap: '0.4rem',
                  }}
                >
                  <i className={`ti ${e.casa ? 'ti-check' : 'ti-alert-triangle'}`}
                     style={{ color: e.casa ? 'var(--ok)' : 'var(--err)', marginTop: 2 }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 'var(--fs-body)', fontWeight: 600 }}>
                      {t(`pattern.sew_type.${s.tipus}`)}
                      {s.diferencial_cm ? ` · ${s.diferencial_cm} cm` : ''}
                    </div>
                    <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-main)' }}>
                      {e.missatge}
                    </div>
                  </div>
                  {mode !== 'view' && (
                    <button
                      onClick={() => onEsborraSew(s.id)}
                      aria-label={t('app.delete')}
                      style={{ background: 'none', border: 'none', cursor: 'pointer',
                               color: 'var(--text-muted)' }}
                    >
                      <i className="ti ti-trash" />
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
