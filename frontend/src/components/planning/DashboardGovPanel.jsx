import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { gates, models as modelsApi } from '../../api/endpoints'
import Center from '../ui/Center'
import Feedback from '../ui/Feedback'
import { primaryBtn } from '../ui/buttons'

// Panell de govern (tab "Tauler" de Planificació). Recupera la cua de gates òrfena de la
// jubilació del Kanban (DIAGNOSI §16.A.b: gates/ready sense surface). Es construeix per blocs;
// el primer és la cua "Llestos per validar". Comptadors + models en risc s'afegeixen després.
const MONO = 'IBM Plex Mono, monospace'
const PHASES = ['Pending', 'Dev', 'Proto', 'SizeSet', 'PP', 'TOP']
const nextPhase = (f) => { const i = PHASES.indexOf(f); return i >= 0 && i < PHASES.length - 1 ? PHASES[i + 1] : null }

const thS = {
  fontFamily: MONO, fontSize: 'var(--fs-label)', fontWeight: 600, color: 'var(--text-muted)', textAlign: 'left',
  padding: '8px 10px', textTransform: 'uppercase', letterSpacing: '.04em',
  borderBottom: '0.5px solid var(--gray-l)', whiteSpace: 'nowrap',
}
const tdS = { padding: '8px 10px', fontSize: 'var(--fs-body)', borderBottom: '0.5px solid var(--gray-l)', verticalAlign: 'middle' }
const ghostBtn = {
  background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6, cursor: 'pointer',
  padding: '4px 12px', fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-main)',
}

export default function DashboardGovPanel({ me }) {
  const { t } = useTranslation()
  // GATING ii: la cua de gates només es renderitza si l'usuari pot tancar gates (close_gates).
  // La resta del panell (comptadors, risc) NO depèn d'aquesta capacitat.
  const canCloseGates = !!me?.capabilities?.includes('close_gates')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
      {canCloseGates
        ? <GatesReadyBlock t={t} />
        : <p style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-body)', padding: '1rem 0' }}>{t('planning.coming_soon')}</p>}
    </div>
  )
}

// Bloc "Llestos per validar": models amb totes les ModelTask Done (GET gates/ready/, gated
// close_gates al backend). Validació individual (POST models/<id>/gate/) i en lot (POST gates/bulk/).
function GatesReadyBlock({ t }) {
  const navigate = useNavigate()
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [selected, setSelected] = useState(() => new Set())
  const [feedback, setFeedback] = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    return gates.ready()
      .then(res => { setRows(res.data?.ready || []); setSelected(new Set()) })
      .catch(() => setFeedback({ type: 'err', text: t('planning.gates.error') }))
      .finally(() => setLoading(false))
  }, [t])

  useEffect(() => { load() }, [load])

  const toggle = (id) => setSelected(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })

  const validateOne = (row) => {
    const nx = nextPhase(row.fase_actual)
    if (!nx) return
    setBusy(true); setFeedback(null)
    modelsApi.gate(row.model_id, { to_phase: nx })
      .then(() => { setFeedback({ type: 'ok', text: t('planning.gates.validated_ok') }); return load() })
      .catch(e => setFeedback({ type: 'err', text: e?.response?.data?.error || t('planning.gates.error') }))
      .finally(() => setBusy(false))
  }

  const validateSelected = () => {
    const items = rows
      .filter(r => selected.has(r.model_id) && nextPhase(r.fase_actual))
      .map(r => ({ model_id: r.model_id, to_phase: nextPhase(r.fase_actual) }))
    if (!items.length) return
    setBusy(true); setFeedback(null)
    gates.bulk({ items })
      .then(res => {
        const okN = (res.data?.done || []).length
        const errN = (res.data?.errors || []).length
        setFeedback(errN
          ? { type: 'err', text: t('planning.gates.validated_bulk_partial', { ok: okN, err: errN }) }
          : { type: 'ok', text: t('planning.gates.validated_bulk_ok', { n: okN }) })
        return load()
      })
      .catch(e => setFeedback({ type: 'err', text: e?.response?.data?.error || t('planning.gates.error') }))
      .finally(() => setBusy(false))
  }

  const selectableCount = rows.filter(r => selected.has(r.model_id) && nextPhase(r.fase_actual)).length

  return (
    <section>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap', marginBottom: 4 }}>
        <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, fontFamily: MONO, margin: 0 }}>
          <i className="ti ti-checkup-list" style={{ fontSize: 16, marginRight: 6, color: 'var(--gold)' }} />
          {t('planning.gates.title')}
        </h2>
        <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', fontFamily: MONO }}>{rows.length}</span>
        {selectableCount > 0 && (
          <button onClick={validateSelected} disabled={busy} style={{ ...primaryBtn, marginLeft: 'auto' }}>
            <i className="ti ti-circle-check" style={{ fontSize: 14 }} />
            {t('planning.gates.validate_selected', { n: selectableCount })}
          </button>
        )}
      </div>
      <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontWeight: 300, marginTop: 0, marginBottom: 12 }}>
        {t('planning.gates.subtitle')}
      </p>

      <Feedback feedback={feedback} />

      {loading ? <Center>{t('planning.loading')}</Center>
        : rows.length === 0 ? (
          <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--fs-body)', border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)' }}>
            {t('planning.gates.empty')}
          </div>
        ) : (
          <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', overflowX: 'auto' }}>
            <table style={{ borderCollapse: 'collapse', width: '100%' }}>
              <thead><tr>
                <th style={{ ...thS, width: 34 }}></th>
                <th style={thS}>{t('planning.col_model')}</th>
                <th style={thS}>{t('planning.gates.col_phase')}</th>
                <th style={thS}>{t('planning.gates.col_next')}</th>
                <th style={thS}>{t('planning.col_pending_count')}</th>
                <th style={thS}></th>
              </tr></thead>
              <tbody>
                {rows.map(r => {
                  const nx = nextPhase(r.fase_actual)
                  return (
                    <tr key={r.model_id}>
                      <td style={tdS}>
                        <input type="checkbox" checked={selected.has(r.model_id)} disabled={!nx}
                               onChange={() => toggle(r.model_id)} />
                      </td>
                      <td style={{ ...tdS, fontFamily: MONO, fontWeight: 600, cursor: 'pointer' }}
                          onClick={() => navigate(`/models/${r.model_id}`)}>{r.codi_intern}</td>
                      <td style={tdS}>{t(`model_sheet.dashboard.phase.${r.fase_actual}`, { defaultValue: r.fase_actual })}</td>
                      <td style={tdS}>
                        {nx
                          ? <span style={{ fontWeight: 500 }}>{t(`model_sheet.dashboard.phase.${nx}`, { defaultValue: nx })}</span>
                          : <span style={{ color: 'var(--text-muted)' }}>{t('planning.gates.at_top')}</span>}
                      </td>
                      <td style={tdS}>{r.task_count}</td>
                      <td style={tdS}>
                        <button onClick={() => validateOne(r)} disabled={busy || !nx} title={t('planning.gates.validate')}
                                style={{ ...ghostBtn, opacity: nx ? 1 : 0.4, cursor: nx ? 'pointer' : 'not-allowed' }}>
                          <i className="ti ti-arrow-right" style={{ fontSize: 14, marginRight: 4 }} />
                          {t('planning.gates.validate')}
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
    </section>
  )
}
