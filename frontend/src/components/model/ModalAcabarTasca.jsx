import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { modelTasks } from '../../api/endpoints'
import { selS } from '../ui/buttons'
import { overlayBase } from '../ui/overlay'
import { formatMinutes } from '../../utils/format'

/**
 * T4 · EL GEST D'ACABAR, AL SEU LLOC (maqueta `maqueta_temps_declarat_i_modal_v1.html`, §3).
 *
 * Apareix EN SORTIR d'una superfície de treball, no mentre s'hi treballa. És la diferència
 * entre preguntar quan la persona ja està pensant en aquella tasca i interrompre-la enmig.
 *
 * Central i intrusiu a posta: des de F1 **desar no tanca res**, i `Done` és el que entra a
 * albarà. Una conseqüència d'aquesta mida no pot dependre de recordar-se'n ni amagar-se en una
 * píndola en un racó — que és el que T4 retira de `SessioActiva`.
 *
 * DUES SORTIDES REALS, cap d'elles un defecte silenciós, i cadascuna amb la seva conseqüència
 * escrita a sota. La maqueta premarca «L'he acabat» perquè és el cas majoritari en sortir; és
 * una de les quatre decisions que hi ha declarades com a pendents de confirmar.
 */
export const ACABAR = 'acabar'
export const PAUSAR = 'pausar'

export default function ModalAcabarTasca({
  taskId, nomTasca, minutsSessio, minutsTotal, onFet, onCancel,
}) {
  const { t } = useTranslation()
  const [tria, setTria] = useState(ACABAR)
  const [enviant, setEnviant] = useState(false)
  const [error, setError] = useState(null)

  const confirma = () => {
    setEnviant(true); setError(null)
    modelTasks.transition(taskId, { to_status: tria === ACABAR ? 'Done' : 'Paused' })
      .then(() => onFet?.(tria))
      .catch(e => {
        setError(e?.response?.data?.error || t('acabar_tasca.err_servidor'))
        setEnviant(false)
      })
  }

  const opcio = (clau, icona, etiqueta, nota) => (
    <button type="button" onClick={() => setTria(clau)} disabled={enviant}
      style={{
        ...selS, width: '100%', textAlign: 'left', padding: '11px 13px', cursor: 'pointer',
        borderColor: tria === clau ? 'var(--gold)' : 'var(--border)',
        borderWidth: tria === clau ? 1 : 0.5,
        background: tria === clau ? '#fdf6ee' : 'var(--white)',
      }}>
      <span style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600 }}>
        <i className={`ti ${icona}`} style={{ color: 'var(--gold)', fontSize: 15 }} />
        {etiqueta}
      </span>
      <span style={{
        display: 'block', marginTop: 5, fontSize: 'var(--fs-caption)',
        color: 'var(--text-muted)', fontWeight: 400, whiteSpace: 'normal', lineHeight: 1.45,
      }}>{nota}</span>
    </button>
  )

  return (
    <div style={overlayBase({ alignItems: 'center' })}>
      <div onClick={e => e.stopPropagation()} style={{
        background: 'var(--white)', borderRadius: 12, padding: 22, width: 460, maxWidth: '92vw',
        fontFamily: 'IBM Plex Mono, monospace',
      }}>
        <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, margin: 0 }}>
          {t('acabar_tasca.titol', { tasca: nomTasca })}
        </h2>
        <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', margin: '6px 0 16px', lineHeight: 1.5 }}>
          {t('acabar_tasca.cos')}
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {opcio(ACABAR, 'ti-check', t('acabar_tasca.fet'), t('acabar_tasca.fet_nota'))}
          {opcio(PAUSAR, 'ti-player-pause', t('acabar_tasca.pausa'), t('acabar_tasca.pausa_nota'))}
        </div>

        {/* El temps que es tanca, dit en veu alta: la decisió no es pren a cegues. */}
        <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', marginTop: 14 }}>
          {t('acabar_tasca.temps', {
            sessio: formatMinutes(minutsSessio ?? 0),
            total: formatMinutes(minutsTotal ?? 0),
          })}
        </p>
        {error && (
          <p style={{ fontSize: 'var(--fs-body)', color: 'var(--err)', marginTop: 10 }}>{error}</p>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 18 }}>
          <button type="button" onClick={onCancel} disabled={enviant}
            style={{ ...selS, border: 'none', background: 'transparent', color: 'var(--text-muted)', cursor: 'pointer' }}>
            {t('acabar_tasca.enrere')}
          </button>
          <button type="button" onClick={confirma} disabled={enviant} style={{
            fontFamily: 'inherit', fontSize: 'var(--fs-body)', fontWeight: 600,
            padding: '8px 16px', border: 'none', borderRadius: 6,
            background: 'var(--gold)', color: 'var(--white)',
            cursor: enviant ? 'not-allowed' : 'pointer', opacity: enviant ? 0.5 : 1,
          }}>
            {t('acabar_tasca.confirmar')}
          </button>
        </div>
      </div>
    </div>
  )
}
