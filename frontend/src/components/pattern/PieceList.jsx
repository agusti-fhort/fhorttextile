import { useTranslation } from 'react-i18next'

/**
 * La llista de peces del patró: nom, rol, recomptes i bbox. Clicar-ne una la selecciona
 * al canvas (i tornar-la a clicar la deselecciona).
 *
 * Viu a part des de W2 perquè la fan servir DUES superfícies: el Taller (columna
 * esquerra, contenidor PECES) i el tab Patró (la porta, per triar quina peça es
 * renderitza al document SVG). Mateixa llista, mateix comportament, un sol lloc.
 */
export default function PieceList({ pieces, pecaSel, onTria }) {
  const { t } = useTranslation()
  const cm = mm => (mm / 10).toFixed(1)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
      {pieces.map(p => {
        const sel = p.nom_block === pecaSel
        const bb = p.bounding_box_mm
        const c = p.punts_per_capa || {}
        return (
          <button
            key={p.id}
            onClick={() => onTria(sel ? '' : p.nom_block)}
            aria-pressed={sel}
            style={{
              textAlign: 'left', cursor: 'pointer',
              background: sel ? 'var(--gold-pale)' : 'var(--bg-card)',
              border: `1px solid ${sel ? 'var(--gold)' : 'var(--border)'}`,
              borderRadius: 6, padding: '0.5rem 0.7rem',
              display: 'flex', flexDirection: 'column', gap: 3,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <i className="ti ti-vector-triangle" style={{ color: 'var(--gold)' }} />
              <strong style={{ fontSize: 'var(--fs-body)' }}>{p.nom_block}</strong>
              {p.metadata?.material && (
                <span style={{
                  fontSize: 'var(--fs-caption)', color: 'var(--text-muted)',
                  border: '1px solid var(--border)', borderRadius: 8, padding: '0 6px',
                }}>
                  {p.metadata.material}
                </span>
              )}
              {!p.has_sew && (
                <span title={t('pattern.no_sew_layer')}
                      style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-caption)' }}>
                  <i className="ti ti-scissors-off" />
                </span>
              )}
            </div>
            <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>
              {t('pattern.piece_points', {
                total: p.total_punts, turn: c.turn || 0, curve: c.curve || 0,
                notch: c.notch || 0,
              })}
            </span>
            {bb && (
              <span style={{
                fontSize: 'var(--fs-caption)', color: 'var(--text-muted)',
                fontFamily: 'var(--mono)',
              }}>
                {cm(bb.ample)} × {cm(bb.alt)} cm
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
