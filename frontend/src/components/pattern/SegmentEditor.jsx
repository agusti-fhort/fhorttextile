import { useTranslation } from 'react-i18next'
import { formatLen } from '../../utils/format'

/**
 * La barra de CONFIRMAR un gest de vora: un tram declarat, o una pinça.
 *
 * **Ja no es tria l'arc aquí** (W4b/T3c). Abans, amb els dos punts posats, es dibuixaven els
 * dos arcs possibles i es preguntava quin dels dos es volia dir; i preguntar-ho aleshores és
 * preguntar-ho quan la mà ja ha marxat. Qui declara un tram ja sap, mentre mou el cursor, per
 * quin costat el vol —i ara l'arc el segueix en temps real i el clic el fixa. Aquí només
 * queda el que encara no s'ha dit: com se'n diu, i el vistiplau.
 *
 * El nom no és decoració: un tram és el vocabulari amb què després es cus, i «Tram 3» és
 * pitjor que «costura lateral» el dia que algú l'hagi de triar d'una llista.
 */
export default function SegmentEditor({
  llargMm, nom, onNom, onCrea, onCancela, creant, pinca = false, unit = 'CM',
}) {
  const { t } = useTranslation()

  const chip = (actiu) => ({
    background: actiu ? 'var(--gold)' : 'var(--white)',
    color: actiu ? 'var(--white)' : 'var(--text-main)',
    border: `1px solid ${actiu ? 'var(--gold)' : 'var(--border)'}`,
    borderRadius: 4, padding: '0.25rem 0.6rem', cursor: 'pointer',
    fontSize: 'var(--fs-caption)',
  })

  return (
    <div style={{
      display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap',
      background: 'var(--bg-muted)', borderRadius: 4, padding: '0.4rem 0.6rem',
      fontSize: 'var(--fs-caption)', flexShrink: 0,
    }}>
      <span style={{
        display: 'flex', alignItems: 'center', gap: '0.3rem',
        fontWeight: 600, color: 'var(--text-main)',
      }}>
        <i className={`ti ${pinca ? 'ti-triangle' : 'ti-line'}`} />
        {t(pinca ? 'pattern.taller.pinca_confirm' : 'pattern.taller.segment_confirm')}
      </span>

      {/* La longitud del que s'està a punt de declarar. En una PINÇA, la suma dels dos costats
          — que és, exactament, la tela que la costura deixarà de cosir. Dir-la aquí és dir el
          descompte abans de fer-lo. */}
      {llargMm != null && (
        <span style={{
          fontFamily: 'var(--mono)', color: 'var(--gold)', fontWeight: 600,
        }}>
          {formatLen(llargMm / 10, unit)}
        </span>
      )}

      <label style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', flex: 1 }}>
        {t('pattern.taller.segment_name')}
        <input
          autoFocus
          value={nom}
          onChange={e => onNom(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && nom.trim()) onCrea() }}
          style={{
            flex: 1, minWidth: 120, maxWidth: 240,
            fontSize: 'var(--fs-caption)', padding: '0.2rem 0.4rem',
            border: '1px solid var(--border)', borderRadius: 4,
          }}
        />
      </label>

      <button onClick={onCancela} style={chip(false)}>
        {t('app.cancel')}
      </button>
      <button
        onClick={onCrea}
        disabled={creant || !nom.trim()}
        style={{
          ...chip(!creant && !!nom.trim()),
          opacity: creant || !nom.trim() ? 0.5 : 1,
          cursor: creant || !nom.trim() ? 'not-allowed' : 'pointer',
        }}
      >
        <i className="ti ti-check" />{' '}
        {t(pinca ? 'pattern.taller.pinca_create' : 'pattern.taller.segment_create')}
      </button>
    </div>
  )
}
