import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import client from '../api/client'
import { models } from '../api/endpoints'
import MeasureGrid from '../components/model/MeasureGrid'
import EditorHeader from '../components/model/EditorHeader'
import { buildEscalatGroups, buildEscalatRows, regimeLeadCol } from '../components/model/fittingGridAdapter'

// ESCALAT — editor de la taula propagada del model (totes les talles) sobre l'editor únic MeasureGrid
// (mode model). Cada cel·la NO-base escriu un ModelGradingOverride i re-propaga al servidor via
// `models.setSizeOverride` (motor INTACTE: el QUI/QUAN no canvia); la talla base és read-only. El
// règim per POM es canvia amb `models.setPomRegim`. S'alimenta de taula-mesures (GradingVersion vigent).
export default function PropagatedEditor({ modelId, onClose, inline = false, readOnly = false }) {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [modelInfo, setModelInfo] = useState(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState('')
  const [reloadKey, setReloadKey] = useState(0)   // remunta MeasureGrid en canvi de règim (re-sembra)

  const load = useCallback(() => {
    setLoading(true)
    return client.get(`/api/v1/models/${modelId}/taula-mesures/`)
      .then(res => setData(res.data))
      .catch(() => setErr(t('model_measurements.propagated_load_err')))
      .finally(() => setLoading(false))
  }, [modelId, t])

  useEffect(() => { load() }, [load])
  // Identitat de model per a la capçalera unificada (EditorHeader).
  useEffect(() => { models.get(modelId).then(r => setModelInfo(r.data)).catch(() => {}) }, [modelId])

  const base = (data?.base_size || '').trim()
  const sizes = data?.size_run || []
  const gridGroups = buildEscalatGroups(sizes, base, t)
  const gridRows = buildEscalatRows(data?.rows || [], sizes, base)

  // Escriptura per talla (mode model): override + re-propaga (motor intacte). Després rellegeix la
  // taula i retorna les cel·les del POM perquè MeasureGrid refresqui les germanes (excepte la del focus).
  const onGridSave = useCallback((lineId, value) => {
    if (value == null) return Promise.resolve()
    const i = lineId.lastIndexOf(':')
    const pomId = Number(lineId.slice(0, i))
    const size = lineId.slice(i + 1)
    return models.setSizeOverride(modelId, pomId, size, value)
      .then(() => client.get(`/api/v1/models/${modelId}/taula-mesures/`))
      .then(res => {
        const d = res.data; setData(d)
        const b = (d.base_size || '').trim()
        const row = (d.rows || []).find(r => r.pom_id === pomId)
        const lines = row ? (d.size_run || []).map(s => {
          const v = s === b ? row.base_value_cm : (row.graded?.[s] ?? null)
          return { id: `${pomId}:${s}`, valor_real: v == null ? '' : v }
        }) : []
        return { lines }
      })
  }, [modelId])

  // Canvi de règim del POM (endpoint independent de la sessió) → rellegeix i remunta la graella.
  const onRegimChange = (row, nova) => {
    if (!nova || nova === (row.logica ?? '')) return
    models.setPomRegim(modelId, row.pom_id, nova)
      .then(() => load().then(() => setReloadKey(k => k + 1)))
      .catch(() => setErr(t('model_measurements.regim_err')))
  }

  const leadCols = [regimeLeadCol(t, onRegimChange, readOnly)]

  // inline=true: incrustat com a contingut de pestanya (sense overlay fix ni botó tancar).
  const outerStyle = inline
    ? {}
    : { position: 'fixed', inset: 0, zIndex: 50, background: 'rgba(0,0,0,0.45)', display: 'flex', flexDirection: 'column' }
  const bodyStyle = inline
    ? { background: 'var(--white)' }
    : { flex: 1, overflow: 'auto', background: 'var(--white)', padding: '1rem' }

  return (
    <div style={outerStyle}>
      <div style={bodyStyle}>
        {/* Overlay (ruta /escalat o modal "Veure escalat"): botó tancar sempre disponible (no depèn
            que hagi carregat la identitat de model). */}
        {!inline && (
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 8 }}>
            <button type="button" onClick={onClose}
              style={{ padding: '6px 16px', border: '0.5px solid var(--border)', borderRadius: 6,
                       background: 'var(--white)', cursor: 'pointer', fontSize: 'var(--fs-body)' }}>
              {t('model_measurements.propagated_close')}
            </button>
          </div>
        )}
        {/* Capçalera UNIFICADA: identitat de model + franja contextual (Escalat · pista). */}
        <EditorHeader
          model={modelInfo}
          context={
            <span>
              <strong>{t('model_sheet.tab_grading')}</strong>
              {' — '}
              {readOnly ? t('model_measurements.propagated_hint_ro') : t('model_measurements.propagated_hint')}
            </span>
          }
        />
        {err && <div style={{ color: 'var(--err)', fontSize: 'var(--fs-body)', marginBottom: 8 }}>{err}</div>}
        {loading && !data ? (
          <div style={{ padding: '2rem', color: 'var(--text-muted)' }}>{t('app.loading')}</div>
        ) : gridRows.length === 0 ? (
          <div style={{ padding: '2rem', color: 'var(--text-muted)' }}>{t('model_measurements.propagated_empty')}</div>
        ) : (
          <MeasureGrid
            key={`${modelId}:${reloadKey}`}
            editable={!readOnly}
            rows={gridRows} groups={gridGroups}
            leadCols={leadCols}
            onSave={onGridSave}
          />
        )}
      </div>
    </div>
  )
}
