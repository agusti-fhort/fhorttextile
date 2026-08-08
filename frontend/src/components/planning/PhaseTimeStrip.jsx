import { useState, useEffect } from 'react'
import { timeAnalysis } from '../../api/endpoints'
import Center from '../ui/Center'

// Tira horitzontal de fases amb TEMPS estadístic (rollup task_type→fase, GET time-analysis/by-phase/).
//
// L'EIX ÉS LA FASE DE TASCA (`TaskType.fase`: Disseny…Producció), que és la que porta temps, i
// NO el cicle de vida del model (`Model.fase_actual`: Pending…TOP). Són dos vocabularis
// independents i l'endpoint `/api/v1/vocabulari/` els publica per separat (`fases_tasca` i
// `fases_model`) justament perquè no es tornin a barrejar.
//
// Aquests comentaris citaven un `PhaseStepper` com a germà visual: era CODI MORT —no el muntava
// ningú— i barrejava tres vocabularis (dos estats del model, cinc fases de tasca i un 'Tècnic'
// que no existeix enlloc; la fase real és 'Dev. tècnic'). Esborrat a F2.2.
const MONO = 'IBM Plex Mono, monospace'

// TaskType.fase → slug per a la clau i18n (els valors reals duen punts/espais: 'Dev. tècnic').
const FASE_KEY = {
  'Disseny': 'disseny', 'Dev. tècnic': 'dev_tecnic', 'Prototip': 'prototip',
  'Mostres': 'mostres', 'Preproducció': 'preproduccio', 'Producció': 'produccio',
}
const MAT_DOT = { empiric: 'var(--ok)', seed: 'var(--gold)', empty: 'var(--gray-l)' }

function fmtMins(m) {
  if (m == null) return null
  const h = Math.floor(m / 60), mm = m % 60
  return h ? (mm ? `${h}h ${mm}m` : `${h}h`) : `${mm}m`
}

export default function PhaseTimeStrip({ t }) {
  const [phases, setPhases] = useState([])
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    timeAnalysis.byPhase()
      .then(res => setPhases(res.data?.phases || []))
      .catch(() => setPhases([]))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Center>{t('planning.loading')}</Center>

  return (
    <div style={{ display: 'flex', alignItems: 'stretch', gap: 0, overflowX: 'auto', padding: '4px 0' }}>
      {phases.map((p, i) => {
        const label = t(`planning.time.phase.${FASE_KEY[p.fase] || 'other'}`, { defaultValue: p.fase })
        const mins = fmtMins(p.minutes)
        const matLabel = t(`planning.time.maturity.${p.maturity}`, { defaultValue: p.maturity })
        const tip = t('planning.time.coverage_tip', {
          empiric: p.cells_empiric, seed: p.cells_seed, none: p.cells_none, n: p.n_total,
        })
        return (
          <div key={p.fase} style={{ display: 'flex', alignItems: 'center' }}>
            <div title={tip} style={{
              minWidth: 116, padding: '8px 12px', borderRadius: 6,
              border: '0.5px solid var(--gray-l)',
              background: p.maturity === 'empty' ? '#f0f0f0' : 'var(--white)',
              opacity: p.maturity === 'empty' ? 0.6 : 1,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 4 }}>
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: MAT_DOT[p.maturity] || 'var(--gray-l)', flexShrink: 0 }} />
                <span style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontFamily: MONO, whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>{label}</span>
              </div>
              <div style={{ fontSize: 'var(--fs-body)', fontWeight: 600, fontFamily: MONO, color: mins ? 'var(--text-main)' : 'var(--text-muted)' }}>
                {mins || '—'}
              </div>
              <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontFamily: MONO }}>{matLabel}</div>
            </div>
            {i < phases.length - 1 && (
              <div style={{ width: 12, height: 1, background: 'var(--border)', flexShrink: 0 }} />
            )}
          </div>
        )
      })}
    </div>
  )
}
