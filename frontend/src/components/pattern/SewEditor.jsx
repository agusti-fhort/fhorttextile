import { useTranslation } from 'react-i18next'
import { KONVA_COL } from './PatternViewer'

/**
 * Editor de costura: tria els trams del costat A i del B, el tipus, i declara.
 *
 * Ve del tab Patró (S6) i viu al Taller des de W2 — mateix comportament, mateix
 * mecanisme: es TRASLLADA, no es reescriu.
 */
export default function SewEditor({
  segmentsA, segmentsB, costatActiu, onCostat, tipus, onTipus,
  diferencial, onDiferencial, onDeclara, onNeteja,
}) {
  const { t } = useTranslation()
  const llest = segmentsA.length > 0 && segmentsB.length > 0

  const chip = (actiu, color) => ({
    background: actiu ? color : 'var(--white)',
    color: actiu ? 'var(--white)' : 'var(--text-main)',
    border: `1px solid ${actiu ? color : 'var(--border)'}`,
    borderRadius: 4, padding: '0.25rem 0.6rem', cursor: 'pointer',
    fontSize: 'var(--fs-caption)',
  })

  return (
    <div style={{
      display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap',
      background: 'var(--bg-muted)', borderRadius: 4, padding: '0.4rem 0.6rem',
      fontSize: 'var(--fs-caption)', flexShrink: 0,
    }}>
      {/* Els chips duen EL MATEIX color que els segments al canvas. No són tokens perquè
          no n'hi ha cap per a aquests dos colors, i inventar-ne dos al design system per a
          un editor de costures seria pitjor que compartir la paleta del canvas: el que
          importa és que el que es clica i el que s'il·lumina siguin del mateix color. */}
      <button onClick={() => onCostat('a')} style={chip(costatActiu === 'a', KONVA_COL.sewA)}>
        {t('pattern.sew_side_a', { n: segmentsA.length })}
      </button>
      <button onClick={() => onCostat('b')} style={chip(costatActiu === 'b', KONVA_COL.sewB)}>
        {t('pattern.sew_side_b', { n: segmentsB.length })}
      </button>

      <select
        value={tipus} onChange={e => onTipus(e.target.value)}
        style={{ fontSize: 'var(--fs-caption)', padding: '0.2rem',
                 border: '1px solid var(--border)', borderRadius: 4 }}
      >
        <option value="casat">{t('pattern.sew_type.casat')}</option>
        <option value="frunzit">{t('pattern.sew_type.frunzit')}</option>
        <option value="pinca">{t('pattern.sew_type.pinca')}</option>
      </select>

      {/* El diferencial només té sentit si un costat ha de sobrar: en un CASAT, la seva
          existència ja és l'error. Per això el camp desapareix. */}
      {tipus !== 'casat' && (
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
          {t('pattern.sew_differential')}
          <input
            type="number" step="0.1" value={diferencial}
            onChange={e => onDiferencial(e.target.value)}
            style={{ width: 62, fontSize: 'var(--fs-caption)', padding: '0.15rem 0.3rem',
                     border: '1px solid var(--border)', borderRadius: 4 }}
          />
          cm
        </label>
      )}

      <span style={{ flex: 1 }} />
      <button onClick={onNeteja} style={chip(false)}>
        {t('app.cancel')}
      </button>
      <button
        onClick={onDeclara} disabled={!llest}
        style={{ ...chip(llest, 'var(--gold)'), opacity: llest ? 1 : 0.5,
                 cursor: llest ? 'pointer' : 'not-allowed' }}
      >
        <i className="ti ti-check" /> {t('pattern.sew_declare')}
      </button>
    </div>
  )
}
