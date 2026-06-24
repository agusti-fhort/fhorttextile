import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import client from '../api/client'
import { models } from '../api/endpoints'
import MeasureGrid from '../components/model/MeasureGrid'
import EditorHeader from '../components/model/EditorHeader'
import Modal from '../components/ui/Modal'
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
  // Peça 2 — propagació conscient: estat del botó, conflicte de segellat (409) i pas de la doble
  // confirmació (1 = avís, 2 = confirmació de producció), i feedback breu d'èxit.
  const [propagating, setPropagating] = useState(false)
  const [sealed, setSealed] = useState(null)      // payload 409 {version_number, message}
  const [sealedStep, setSealedStep] = useState(0)
  const [notice, setNotice] = useState('')

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

  // Propagar conscient → crea v+1 sobre la versió vigent. Normal = un clic. Sobre una versió
  // segellada el backend torna 409 'sealed' → doble confirmació; només amb les dues capes es
  // reintenta amb allow_reopen_sealed (que deixa un watchpoint de traça al servidor).
  const onPropagar = useCallback((allowReopen = false) => {
    setPropagating(true); setErr(''); setNotice('')
    const body = { new_version: true }
    if (allowReopen) body.allow_reopen_sealed = true
    return models.generarGrading(modelId, body)
      .then(() => {
        setSealed(null); setSealedStep(0)
        return load().then(() => { setReloadKey(k => k + 1); setNotice(t('grading_propagate.done')) })
      })
      .catch(e => {
        const d = e?.response?.data
        if (e?.response?.status === 409 && d?.error === 'sealed') { setSealed(d); setSealedStep(1) }
        else { setErr(t('grading_propagate.err')) }
      })
      .finally(() => setPropagating(false))
  }, [modelId, load, t])

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
        {/* Barra d'accions: Propagar (acte conscient, quan editable) a l'esquerra; tancar (overlay)
            a la dreta. El botó tancar segueix disponible encara que no hagi carregat la identitat. */}
        {(!readOnly || !inline) && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                        gap: 12, marginBottom: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              {!readOnly && (
                <button type="button" onClick={() => onPropagar(false)} disabled={propagating}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 16px',
                           border: '0.5px solid var(--border)', borderRadius: 6, background: 'var(--white)',
                           cursor: propagating ? 'not-allowed' : 'pointer', opacity: propagating ? 0.5 : 1,
                           fontSize: 'var(--fs-body)' }}>
                  <i className="ti ti-git-branch" style={{ fontSize: 14 }} />
                  {propagating ? t('grading_propagate.running') : t('grading_propagate.button')}
                </button>
              )}
              {notice && <span style={{ color: 'var(--ok)', fontSize: 'var(--fs-body)' }}>{notice}</span>}
            </div>
            {!inline && (
              <button type="button" onClick={onClose}
                style={{ padding: '6px 16px', border: '0.5px solid var(--border)', borderRadius: 6,
                         background: 'var(--white)', cursor: 'pointer', fontSize: 'var(--fs-body)' }}>
                {t('model_measurements.propagated_close')}
              </button>
            )}
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

      {/* Doble confirmació conscient en propagar sobre una versió SEGELLADA (409 'sealed'). */}
      {sealed && sealedStep === 1 && (
        <Modal
          title={t('grading_propagate.sealed_title')}
          subtitle={t('grading_propagate.sealed_l1', { version: sealed.version_number })}
          confirmLabel={t('grading_propagate.continue')}
          cancelLabel={t('app.cancel')}
          onCancel={() => { setSealed(null); setSealedStep(0) }}
          onConfirm={() => setSealedStep(2)}
        />
      )}
      {sealed && sealedStep === 2 && (
        <Modal
          title={t('grading_propagate.sealed_title')}
          subtitle={t('grading_propagate.sealed_l2')}
          confirmLabel={t('grading_propagate.confirm_supersede')}
          cancelLabel={t('app.cancel')}
          onCancel={() => { setSealed(null); setSealedStep(0) }}
          onConfirm={() => onPropagar(true)}
        />
      )}
    </div>
  )
}
