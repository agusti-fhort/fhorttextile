import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import client from '../api/client'
import { models } from '../api/endpoints'
import MeasureGrid from '../components/model/MeasureGrid'
import EditorHeader from '../components/model/EditorHeader'
import { buildEscalatGroups, buildEscalatRows, regimeLeadCol } from '../components/model/fittingGridAdapter'

// ESCALAT — editor de la taula propagada del model (totes les talles) sobre l'editor únic MeasureGrid,
// CONVERGIT amb el fitting: totes les talles editables (base inclosa) i editar una cel·la PROPAGA per
// regla a les germanes (endpoint escalat/ajustar-talla → propaga_ancoratges, com piece-fitting-lines/
// propagar). El règim per POM es canvia amb setPomRegim. S'alimenta de taula-mesures (UNA taula vigent
// neta; LLEI: propagar = llenç net, no eix de versions). Versionar és l'acte conscient "Propagar a
// grading" a MESURES, no aquí.
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

  // Escriptura per talla (convergit amb el fitting): ancora la talla i PROPAGA per regla a les germanes.
  // Retorna l'axios promise; MeasureGrid llegeix res.data.linies i refresca la fila (germanes + base).
  const onGridSave = useCallback((lineId, value) => {
    if (value == null) return Promise.resolve()
    const i = lineId.lastIndexOf(':')
    const pomId = Number(lineId.slice(0, i))
    const talla = lineId.slice(i + 1)
    return models.escalatAjustarTalla(modelId, pomId, talla, value)
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
        {/* Overlay (ruta /escalat o modal "Veure escalat"): botó tancar sempre disponible. */}
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
