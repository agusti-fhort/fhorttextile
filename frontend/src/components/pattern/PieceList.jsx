import { useTranslation } from 'react-i18next'

import { etiquetaPeca, nomDelRol, nomOriginal } from './pieceText'

/**
 * La llista de peces del patró: nom, rol, recomptes i bbox. Clicar-ne una la selecciona
 * al canvas (i tornar-la a clicar la deselecciona).
 *
 * Viu a part des de W2 perquè la fan servir DUES superfícies: el Taller (columna
 * esquerra, contenidor PECES) i el tab Patró (la porta, per triar quina peça es
 * renderitza al document SVG). Mateixa llista, mateix comportament, un sol lloc.
 */
export default function PieceList({ pieces, pecaSel, onTria }) {
  const { t, i18n } = useTranslation()
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
              background: sel ? 'var(--sel)' : 'var(--panel)',
              border: `1px solid ${sel ? 'var(--gold)' : 'var(--line)'}`,
              borderRadius: 6, padding: '0.5rem 0.7rem',
              display: 'flex', flexDirection: 'column', gap: 3,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <i className="ti ti-vector-triangle" style={{ color: 'var(--gold)' }} />
              {/* L'etiqueta és el nom que una persona ha triat, si n'hi ha; el nom del
                  BLOCK no desapareix mai —va al títol— perquè és l'evidència del fitxer. */}
              <strong style={{ fontSize: 'var(--fs-body)' }} title={nomOriginal(p)}>
                {etiquetaPeca(p)}
              </strong>
              {p.metadata?.material && (
                <span style={{
                  fontSize: 'var(--fs-caption)', color: 'var(--text-soft)',
                  border: '1px solid var(--line)', borderRadius: 8, padding: '0 6px',
                }}>
                  {p.metadata.material}
                </span>
              )}
              {!p.has_sew && (
                <span title={t('pattern.no_sew_layer')}
                      style={{ color: 'var(--text-soft)', fontSize: 'var(--fs-caption)' }}>
                  <i className="ti ti-scissors-off" />
                </span>
              )}
            </div>
            {/* Segona línia (convenció FTP-1): el nom del ROL, en gris i cursiva. Si la
                peça encara no en té, la línia no hi és — un buit no s'omple amb text. */}
            {nomDelRol(p, i18n.language) && (
              <span style={{
                fontSize: 'var(--fs-caption)', color: 'var(--text-soft)',
                fontStyle: 'italic',
              }}>
                {nomDelRol(p, i18n.language)}
              </span>
            )}
            <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)' }}>
              {t('pattern.piece_points', {
                total: p.total_punts, turn: c.turn || 0, curve: c.curve || 0,
                notch: c.notch || 0,
              })}
            </span>
            {bb && (
              <span style={{
                fontSize: 'var(--fs-caption)', color: 'var(--text-soft)',
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
