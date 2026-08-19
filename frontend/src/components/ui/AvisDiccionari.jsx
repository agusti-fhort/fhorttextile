// EL VOCABULARI QUE NO ARRIBA ES DIU — un sol avís per a totes les superfícies que en viuen.
//
// Va néixer inline a `EditableTable` (P0.2, 06/08) quan el GET del diccionari va fallar amb el
// MILEY: les columnes de POSICIÓ i ESTAT van desaparèixer sense dir res i des de la pantalla
// allò no es distingia d'un catàleg que no en tingués. La segona i la tercera superfície que
// llegeixen el diccionari (`MeasureGrid`, `ComprovacioPanel`) callaven igual, i copiar-hi el
// bloc hauria estat el tercer pedaç: l'avís viu aquí i el consumeix qui el necessiti.
//
// EL «QUÈ ES PERD» ÉS DE CADA PANTALLA (`hint`): a la taula d'autoria no pots crear germanes;
// a les graelles de lectura els noms de les germanes surten crus. El títol i el reintent, no:
// són el mateix fet.
//
// REINTENTA perquè el mode de fallada típic és transitori (la petició surt abans que la sessió
// estigui a punt) i recarregar la pàgina no pot ser l'única sortida.
import { useTranslation } from 'react-i18next'

export default function AvisDiccionari({ hint, onReintenta }) {
  const { t } = useTranslation()
  return (
    <div style={{
      background: 'var(--warn-bg)', border: '1px solid var(--warn)',
      borderRadius: 8, padding: '10px 16px', marginBottom: 12,
      fontSize: 'var(--fs-body)', display: 'flex', alignItems: 'center', gap: 10,
    }}>
      <i className="ti ti-alert-triangle" style={{ color: 'var(--warn)', fontSize: 16 }} aria-hidden="true" />
      <span style={{ flex: 1 }}>
        <strong>{t('dicc.error_title')}</strong>{' '}
        {hint}
      </span>
      <button type="button" onClick={onReintenta}
        style={{
          background: 'var(--white)', color: 'var(--warn)', border: '0.5px solid var(--warn)',
          borderRadius: 6, padding: '5px 12px', fontFamily: 'inherit',
          fontSize: 'var(--fs-body)', cursor: 'pointer', whiteSpace: 'nowrap',
        }}>
        <i className="ti ti-refresh" style={{ fontSize: 13 }} aria-hidden="true" />{' '}
        {t('dicc.error_retry')}
      </button>
    </div>
  )
}
