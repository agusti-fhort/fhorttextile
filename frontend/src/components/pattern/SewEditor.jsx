import { useTranslation } from 'react-i18next'
import { KONVA_COL } from './PatternViewer'
import { formatLen, unitLabel } from '../../utils/format'

/**
 * Cosir: quins trams van a cada costat, de quin tipus és la costura, i declarar-la.
 *
 * **Es tria NOMÉS entre trams DECLARATS.** Un tram 'auto' és la proposta de lectura que el
 * motor fa del CAD (gir→gir); una costura és una afirmació sobre la peça, i no es fa una
 * afirmació amb una hipòtesi. Si la peça no té cap tram declarat, el buit-estat no és un
 * mur: porta a l'eina de declarar-ne un. El pas previ és el flux, no un obstacle.
 *
 * Els costats de PINÇA no s'ofereixen (W4b): un costat de pinça es cus contra el seu germà,
 * mai contra una altra peça, i oferir-lo aquí seria oferir un disbarat. La llista ja arriba
 * filtrada del taller.
 *
 * **La mateixa superfície serveix per REOBRIR** (T5c): amb `editant`, això no declara una
 * costura nova, desa la que hi ha —tipus, diferencial, composició de costats i bateig— sobre
 * la mateixa fila. Un segon editor per a la mateixa cosa acabaria divergint del primer.
 *
 * Les costures que ja existien sobre trams 'auto' (les d'abans d'aquesta llei) es veuen i
 * s'esborren igual que sempre, a RELACIONS: compatibilitat, no migració.
 */
export default function SewEditor({
  segmentsA, segmentsB, costatActiu, onCostat, tipus, onTipus,
  diferencial, onDiferencial, nom, onNom, editant = false,
  onDeclara, onNeteja,
  trams, onTriaTram, onRessalta, onDefinirTram, unit = 'CM',
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

  // Per peça: un tram és un tros d'una peça, i triar-lo sense saber de quina peça és seria
  // triar a cegues (dues peces poden tenir un «lateral» cadascuna).
  const perPeca = trams.reduce((acc, tr) => {
    (acc[tr.peca] = acc[tr.peca] || []).push(tr)
    return acc
  }, {})

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', gap: '0.4rem',
      background: 'var(--bg-muted)', borderRadius: 4, padding: '0.4rem 0.6rem',
      fontSize: 'var(--fs-caption)', flexShrink: 0,
    }}>
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
        {/* Els chips duen EL MATEIX color que els trams al canvas. No són tokens perquè no
            n'hi ha cap per a aquests dos colors, i inventar-ne dos al design system per a un
            editor de costures seria pitjor que compartir la paleta del canvas: el que importa
            és que el que es clica i el que s'il·lumina siguin del mateix color. */}
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
            {unitLabel(unit)}
          </label>
        )}

        {/* EL BATEIG (T6). Buit = el nom se'l genera dels dos trams («Lateral ⛓ Esquena»), i
            es refà sol si algú els reanomena. Escrit, mana: un nom que una persona ha triat no
            el pot trepitjar un generador. El placeholder ho diu sense haver-ho d'explicar. */}
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', minWidth: 0 }}>
          {t('pattern.taller.sew_name')}
          <input
            value={nom || ''}
            onChange={e => onNom(e.target.value)}
            placeholder={t('pattern.taller.sew_name_auto')}
            style={{ width: 150, fontSize: 'var(--fs-caption)', padding: '0.15rem 0.3rem',
                     border: '1px solid var(--border)', borderRadius: 4 }}
          />
        </label>

        <span style={{ flex: 1 }} />
        <button onClick={onNeteja} style={chip(false)}>{t('app.cancel')}</button>
        <button
          onClick={onDeclara} disabled={!llest}
          style={{ ...chip(llest, 'var(--gold)'), opacity: llest ? 1 : 0.5,
                   cursor: llest ? 'pointer' : 'not-allowed' }}
        >
          <i className="ti ti-check" />{' '}
          {t(editant ? 'pattern.taller.sew_save' : 'pattern.sew_declare')}
        </button>
      </div>

      {trams.length === 0 ? (
        // El buit-estat no és un mur: és la porta al pas que falta.
        <div style={{
          display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap',
          color: 'var(--text-muted)', padding: '0.2rem 0',
        }}>
          <i className="ti ti-info-circle" />
          <span style={{ flex: 1 }}>{t('pattern.taller.sew_no_segments')}</span>
          <button
            onClick={onDefinirTram}
            style={{ ...chip(true, 'var(--gold)'), display: 'flex',
                     alignItems: 'center', gap: '0.3rem' }}
          >
            <i className="ti ti-line" />
            {t('pattern.taller.mode_seg')}
          </button>
        </div>
      ) : (
        <div style={{
          display: 'flex', gap: '0.6rem', flexWrap: 'wrap', alignItems: 'flex-start',
          maxHeight: 92, overflowY: 'auto',
        }}>
          {Object.entries(perPeca).map(([peca, llista]) => (
            <div key={peca} style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
              <span style={{
                color: 'var(--text-muted)', fontFamily: 'var(--mono)',
                textTransform: 'uppercase', letterSpacing: '0.03em',
              }}>
                {peca}
              </span>
              {llista.map(tr => {
                const enA = segmentsA.includes(tr.id)
                const enB = segmentsB.includes(tr.id)
                const color = enA ? KONVA_COL.sewA : enB ? KONVA_COL.sewB : null
                return (
                  <button
                    key={tr.id}
                    onClick={() => onTriaTram(tr)}
                    onMouseEnter={() => onRessalta(tr.id)}
                    onMouseLeave={() => onRessalta(null)}
                    aria-pressed={enA || enB}
                    style={{
                      ...chip(!!color, color || 'var(--gold)'),
                      display: 'flex', alignItems: 'center', gap: '0.3rem',
                    }}
                  >
                    <span>{tr.nom || t('pattern.taller.segment_unnamed')}</span>
                    <span style={{ fontFamily: 'var(--mono)', opacity: 0.85 }}>
                      {formatLen(tr.longitud_cm, unit)}
                    </span>
                  </button>
                )
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
