import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import StatCard from '../ui/StatCard'
import Table from '../ui/Table'
import RegistreRondes from './RegistreRondes'
import { models } from '../../api/endpoints'
import { formatMinutes } from '../../utils/format'

const API = import.meta.env.VITE_API_URL || ''
const MONO = 'IBM Plex Mono, monospace'
const authHeaders = () => ({ Authorization: `Bearer ${localStorage.getItem('access_token')}` })

const fmtDateTime = (v) => v ? new Date(v).toLocaleString('ca-ES', { dateStyle: 'medium', timeStyle: 'short' }) : '—'

// 4.4 — Tab "Registre d'activitat" = albarà read-only del model (capçalera immutable,
// resum, passos, repartiment per tècnic, historial col·lapsable). Sense escriptura.
//
// M2 · MOCKUP B v3 — LA GRAELLA DE PASSOS PASSA A SER **UNA SOLA GRAELLA PER RONDES**
// (`RegistreRondes`), i la SUBSTITUEIX: micro-decisió d'Agus, sense convivència i sense flag.
// Els quatre KPI de capçalera prenen el lloc de les tres StatCard —temps total i inici
// d'activitat ja hi eren; rondes i entregues surten de la porta de voltes, que és la mateixa
// que fa servir el Pla de treball—. La resta del tab (capçalera immutable, repartiment per
// tècnic, historial complet de transicions) NO es toca: el mockup no la substitueix i treure-la
// hauria estat un redisseny, no una adaptació.
//
// 🔑 La font segueix sent `/albara/` i **cap dada del registre canvia de mà**. El brief donava
// `model_task_log_view` com a font d'aquesta graella; a la pantalla viva no ho és (aquell
// endpoint alimenta `TaskLog.jsx`, que no el munta ningú) i, a més, un log de TRANSICIONS no
// pot dir ni el temps ni l'inici ni el fi d'una tasca. V. l'acta.
export default function RegistreActivitatTab({ modelId }) {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [rondes, setRondes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showHistory, setShowHistory] = useState(false)

  useEffect(() => {
    let alive = true
    setLoading(true); setError(null)
    fetch(`${API}/api/v1/models/${modelId}/albara/`, { headers: authHeaders() })
      .then(r => { if (!r.ok) throw new Error(r.status); return r.json() })
      .then(d => { if (alive) { setData(d); setLoading(false) } })
      .catch(e => { if (alive) { setError(e.message); setLoading(false) } })
    // Les VOLTES, per la porta d'M1: l'albarà no en sap res (una ronda entregada és tancada) i
    // és d'aquí que surten l'entrega niuada i els dos KPI nous. Si falla, la graella es queda
    // amb els passos i sense agrupar: el registre no desapareix per una lectura auxiliar.
    models.rondes(modelId)
      .then(r => { if (alive) setRondes(Array.isArray(r?.data) ? r.data : []) })
      .catch(() => { if (alive) setRondes([]) })
    return () => { alive = false }
  }, [modelId])

  if (loading) {
    return <div style={{ padding: 24, color: 'var(--text-muted)', fontFamily: MONO }}>{t('common.loading')}</div>
  }
  if (error) {
    return <div style={{ padding: 24, color: 'var(--err, #c0392b)', fontFamily: MONO }}>{t('common.error')}: {error}</div>
  }

  // Estat NO meritat — encara no ha iniciat activitat.
  if (data && data.merited === false) {
    return (
      <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', fontFamily: MONO }}>
        <i className="ti ti-clock-off" style={{ fontSize: 32, display: 'block', marginBottom: 8 }} />
        {t('albara.notMerited')}
      </div>
    )
  }

  const { header, steps = [], totals = {}, per_technician = [], history = [] } = data || {}

  const techCols = [
    { key: 'label', label: t('albara.technician'), render: r => r.label || '—' },
    { key: 'minutes', label: t('albara.time'), align: 'right', render: r => formatMinutes(r.minutes) },
  ]

  const historyCols = [
    { key: 'task_type', label: t('albara.taskType'), render: r => r.task_type || '—' },
    { key: 'transition', label: t('albara.status'), render: r => `${r.from ?? '—'} → ${r.to ?? '—'}` },
    { key: 'by', label: t('albara.technician'), render: r => r.by || '—' },
    { key: 'at', label: t('albara.end'), render: r => fmtDateTime(r.at) },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, fontFamily: MONO }}>
      {/* 1. Capçalera immutable */}
      <div style={{
        background: 'var(--bg-card, #fafafa)',
        border: '0.5px solid var(--border)',
        borderRadius: 8, padding: 16,
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16,
      }}>
        <div>
          <span style={{ color: 'var(--gold)', fontWeight: 600 }}>{header?.code}</span>
          {header?.name && <span style={{ marginLeft: 8 }}>{header.name}</span>}
        </div>
        <div style={{ textAlign: 'right', color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>
          <div>{t('albara.period')}: {header?.period || '—'}</div>
          <div>{t('albara.meritedAt')}: {fmtDateTime(header?.merited_at)}</div>
        </div>
      </div>

      {/* 2. Resum — els QUATRE KPI del mockup B v3. «Passos» se'n va: la graella ja diu quantes
          tasques té cada volta, i el que el registre per rondes ha de dir al capdamunt és
          quantes voltes hi ha hagut i quantes n'han sortit entregades. «Rectificacions» es
          queda (és la xifra d'FIT-8 a escala de model) i «Inici activitat» pren el
          `merited_at`, que ja portava aquest nom a l'i18n des d'abans d'M2. */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
        <StatCard icon="ti-clock" label={t('albara.totalTime')} value={formatMinutes(totals.total_minutes)} />
        <StatCard icon="ti-rotate-clockwise" label={t('rondes.reg_kpi_rondes')} value={rondes.length} />
        <StatCard icon="ti-package-export" label={t('rondes.reg_kpi_entregues')}
                  value={rondes.filter(r => r.entregada).length} />
        <StatCard icon="ti-rotate" label={t('albara.rectifications')} value={totals.rectifications ?? 0} />
        <StatCard icon="ti-clock-play" label={t('albara.meritedAt')}
                  value={fmtDateTime(header?.merited_at)} />
      </div>

      {/* 3. UNA SOLA GRAELLA, per rondes (mockup B v3) — substitueix la taula de passos. */}
      <div>
        <div style={{ fontSize: 'var(--fs-label)', letterSpacing: '.08em',
                      textTransform: 'uppercase', color: 'var(--text-soft)', fontWeight: 600,
                      marginBottom: 10 }}>
          {t('rondes.reg_titol')}
        </div>
        <RegistreRondes passos={steps} rondes={rondes} />
      </div>

      {/* 4. Repartiment per tècnic */}
      <Table columns={techCols} data={per_technician} empty="—" />

      {/* 5. Historial col·lapsable */}
      <div>
        <button
          onClick={() => setShowHistory(v => !v)}
          style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--gold)', fontFamily: MONO, fontSize: 'var(--fs-body)',
            display: 'inline-flex', alignItems: 'center', gap: 6, padding: '4px 0',
          }}>
          <i className={`ti ti-chevron-${showHistory ? 'up' : 'down'}`} />
          {t('albara.history')}
        </button>
        {showHistory && (
          <Table columns={historyCols} data={history} empty="—" />
        )}
      </div>
    </div>
  )
}
