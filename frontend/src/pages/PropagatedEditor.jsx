import { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import client from '../api/client'
import { models } from '../api/endpoints'
import MeasureTable from './MeasureTable'

// Editor de la TAULA PROPAGADA del model (totes les talles, règim, breaks) en mode EDICIÓ.
// Reusa MeasureTable (el mateix de la sessió de fitting) en "mode model": cada cel·la NO-base
// escriu un ModelGradingOverride i re-propaga al servidor (PEÇA 1); la talla base és de lectura
// (s'edita com a mesura base). El règim per POM es canvia amb models.setPomRegim (ja independent
// de la sessió). S'alimenta de taula-mesures (GradingVersion vigent, criteri PEÇA 0).
export default function PropagatedEditor({ modelId, onClose, inline = false, readOnly = false }) {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState('')
  const [reals, setReals] = useState({})
  const [editedIds, setEditedIds] = useState(new Set())
  const focusedIdRef = useRef(null)

  const cellId = (pomId, size) => `${pomId}:${size}`

  const load = useCallback(() => {
    setLoading(true)
    return client.get(`/api/v1/models/${modelId}/taula-mesures/`)
      .then(res => {
        const d = res.data
        setData(d)
        const base = (d.base_size || '').trim()
        const sizes = d.size_run || []
        const r = {}
        for (const row of d.rows || []) {
          for (const s of sizes) {
            const val = s === base ? row.base_value_cm : (row.graded?.[s] ?? null)
            r[cellId(row.pom_id, s)] = val == null ? '' : val
          }
        }
        // Després d'una re-propagació no trepitgem la cel·la amb focus (l'usuari pot teclejar-hi).
        setReals(prev => {
          const keep = focusedIdRef.current
          if (keep && prev[keep] !== undefined) return { ...r, [keep]: prev[keep] }
          return r
        })
      })
      .catch(() => setErr(t('model_measurements.propagated_load_err')))
      .finally(() => setLoading(false))
  }, [modelId, t])

  useEffect(() => { load() }, [load])

  const onValue = (id, v) => setReals(r => ({ ...r, [id]: v }))
  const onAnchor = (id) => setEditedIds(new Set([id]))

  // Escriptura per talla (mode model): override + re-propaga; després recarrega per repintar germanes.
  const persistCell = useCallback(({ row, sizeLabel, raw }) => {
    const v = raw === '' ? null : Number(raw)
    if (v == null || Number.isNaN(v)) return Promise.resolve()
    return models.setSizeOverride(modelId, row.pom_id, sizeLabel, v).then(res => {
      load()
      return res
    })
  }, [modelId, load])

  // Canvi de règim del POM (reusa l'endpoint ja independent de la sessió) → recarrega.
  const onRegimChange = (row, nova) => {
    if (!nova || nova === (row.logica ?? '')) return
    models.setPomRegim(modelId, row.pom_id, nova).then(() => load())
      .catch(() => setErr(t('model_measurements.regim_err')))
  }

  // Construeix les files en la forma que espera MeasureTable. Una sola "versió" (la vigent):
  // columna read-only "Base" (valor propagat actual) + columna editable "Fit actual".
  const base = (data?.base_size || '').trim()
  const sizes = data?.size_run || []
  const versionNumbers = [1]
  const pomRows = (data?.rows || []).map(row => {
    const cells = {}
    for (const s of sizes) {
      const v = s === base ? row.base_value_cm : (row.graded?.[s] ?? null)
      cells[s] = {
        id: cellId(row.pom_id, s), pom_id: row.pom_id, size_label: s,
        logica: row.logica,
        evolucio: [{ version_number: 1, valor_cm: v }],
      }
    }
    return {
      pom_id: row.pom_id, codi: row.pom_code, nom: row.nom_ca || row.nom_en, is_key: row.is_key,
      logica: row.logica, increment_base: row.increment_base,
      increment_break: row.increment_break, talla_break_label: row.talla_break_label,
      cells,
    }
  })

  // inline=true: incrustat com a contingut de pestanya (sense overlay fix ni botó tancar).
  const outerStyle = inline
    ? {}
    : { position: 'fixed', inset: 0, zIndex: 50, background: 'rgba(0,0,0,0.45)', display: 'flex', flexDirection: 'column' }
  const bodyStyle = inline
    ? { background: 'var(--white)' }
    : { flex: 1, overflow: 'auto', background: 'var(--white)', padding: '1rem' }

  return (
    <div style={outerStyle}>
      <div style={{
        background: inline ? 'transparent' : 'var(--bg-muted)', padding: inline ? '0 0 12px' : '12px 18px',
        borderBottom: inline ? 'none' : '0.5px solid var(--border)', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div>
          <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, margin: 0 }}>
            {t('model_measurements.propagated_title')}
          </h2>
          <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', margin: '2px 0 0' }}>
            {readOnly ? t('model_measurements.propagated_hint_ro') : t('model_measurements.propagated_hint')}
          </p>
        </div>
        {!inline && (
          <button type="button" onClick={onClose}
            style={{ padding: '6px 16px', border: '0.5px solid var(--border)', borderRadius: 6,
                     background: 'var(--white)', cursor: 'pointer', fontSize: 'var(--fs-body)' }}>
            {t('model_measurements.propagated_close')}
          </button>
        )}
      </div>
      <div style={bodyStyle}>
        {err && <div style={{ color: 'var(--err)', fontSize: 'var(--fs-body)', marginBottom: 8 }}>{err}</div>}
        {loading && !data ? (
          <div style={{ padding: '2rem', color: 'var(--text-muted)' }}>{t('app.loading')}</div>
        ) : pomRows.length === 0 ? (
          <div style={{ padding: '2rem', color: 'var(--text-muted)' }}>{t('model_measurements.propagated_empty')}</div>
        ) : (
          <MeasureTable
            pomRows={pomRows}
            sizeLabels={sizes}
            baseLabel={base}
            versionNumbers={versionNumbers}
            reals={reals}
            editedIds={editedIds}
            focusedIdRef={focusedIdRef}
            readOnly={readOnly}
            onValue={onValue}
            onAnchor={onAnchor}
            onPropagated={() => {}}
            onRegimChange={readOnly ? () => {} : onRegimChange}
            persistCell={readOnly ? null : persistCell}
            cellReadOnly={(row, s) => s === base}
          />
        )}
      </div>
    </div>
  )
}
