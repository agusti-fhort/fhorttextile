import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

import { OBERT, useTramObert } from '../api/tramObert'
import { durada, estatSessio, segonsDeSessio } from '../utils/sessioActiva'

/**
 * F2.3 · INDICADOR PERSISTENT DE SESSIÓ · T4 (maqueta v1, §2): «diu què corre i des de quan».
 *
 * UN component per a tota l'app, muntat al costat de `GuardTascaOblidada` a `App.jsx`, i no un
 * botó per pantalla: el tècnic salta de Mesures a Fitxa a Escalat i la sessió és la mateixa cosa
 * a totes.
 *
 * **JA NO TANCA RES.** F2.3 hi va posar el gest d'acabar perquè, des de F1, desar no tanca i
 * calia que Done tingués una porta visible. La porta era aquesta píndola flotant, i el lloc
 * estava equivocat: acabar arribava per sorpresa, lluny de la feina i sense dir quant temps
 * s'estava tancant. T4 el mou a on la decisió ja s'està prenent —en SORTIR de la superfície de
 * treball— i aquí només queda la informació, que és el que sempre va ser útil.
 *
 * ✅ F3.2 · DEUTE SALDAT: la lectura ja no és pròpia. Sondejava `timers.list` pel seu compte, com
 * fa `GuardTascaOblidada`, i eren quatre peticions per minut i dos rellotges desfasats per saber
 * una sola cosa. Ara tots dos escolten `api/tramObert`. Les PREGUNTES segueixen sent diferents
 * —ell vigila la INACTIVITAT, això mostra la PRESÈNCIA— i per això la política es queda a cada
 * banda: davant d'un error de xarxa el guard es manté armat i aquesta píndola s'amaga, que és el
 * que cadascun ha de fer. De regal, en pausar-se una tasca la píndola marxa a l'instant en comptes
 * d'anar-se'n quan li toqués el minut.
 */

const TICK_MS = 30_000      // només per repintar la durada; l'instant absolut mana

export default function SessioActiva() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [ara, setAra] = useState(() => Date.now())

  // Sense dada confirmada no s'ensenya res: `estatSessio` ja diu que `null` (una píndola que
  // menteix és pitjor que cap píndola) i qualsevol estat que no sigui OBERT hi cau igual.
  const resultat = useTramObert()
  const sessio = resultat?.estat === OBERT
    ? estatSessio(resultat.tram, resultat.tasca)
    : null

  useEffect(() => {
    const id = setInterval(() => setAra(Date.now()), TICK_MS)
    return () => clearInterval(id)
  }, [])

  if (!sessio) return null
  const mins = durada(segonsDeSessio({ inici: sessio.inici }, ara))

  return (
    <div style={{
      position: 'fixed', bottom: 16, right: 16, zIndex: 900,
      display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'flex-end',
      fontFamily: 'IBM Plex Mono, monospace',
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        background: 'var(--white)', border: '0.5px solid var(--gray-l)', borderRadius: 999,
        padding: '6px 8px 6px 14px', boxShadow: '0 2px 12px rgba(0,0,0,0.10)',
      }}>
        <span style={{
          width: 7, height: 7, borderRadius: '50%', background: 'var(--gold)', flexShrink: 0,
        }} />
        <button
          onClick={() => sessio.modelId && navigate(`/models/${sessio.modelId}`)}
          title={t('sessio.anar_al_model')}
          style={{
            border: 'none', background: 'transparent', padding: 0, cursor: 'pointer',
            fontFamily: 'inherit', fontSize: 'var(--fs-body)', color: 'var(--text-main)',
            display: 'flex', alignItems: 'baseline', gap: 8,
          }}
        >
          <span style={{ fontWeight: 500 }}>{sessio.nom}</span>
          <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>
            {sessio.model}
          </span>
          <span style={{ fontVariantNumeric: 'tabular-nums', color: 'var(--text-muted)' }}>
            {mins}
          </span>
        </button>
      </div>
    </div>
  )
}
