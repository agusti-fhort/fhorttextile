import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { models as modelsApi } from '../api/endpoints'

// D10 — porta-menú de la fitxa tècnica (S03b · P6).
//
// El gate de `tech_sheet` viu al backend, a open-task (allow-list per usuari). Aquesta pàgina
// NO reimplementa cap comprovació de permisos: crida openTask i navega NOMÉS en èxit, igual
// que WorkPlan.jsx:240-249 i TaskTree.jsx:109-118. Si el backend diu que el tipus no és a
// l'allow-list, s'ofereix "obrir en consulta" (sense task_id → l'editor no imputa temps).
//
// Sidebar-com-a-ruta: les entrades del Sidebar són NavLink declaratius (`to:`); no hi ha cap
// precedent d'entrada amb onClick. Per això el menú apunta a aquesta pàgina en comptes d'obrir
// un modal des del Sidebar: mateix resultat per a l'usuari, sense trencar el patró del menú.

const MONO = 'IBM Plex Mono, monospace'
const PAGE_SIZE = 12

const inputStyle = {
  width: '100%', padding: '10px 12px', borderRadius: 4,
  border: '0.5px solid var(--gray-l)', fontFamily: MONO,
  fontSize: 'var(--fs-body)', background: 'var(--white)', boxSizing: 'border-box',
}

const rowStyle = {
  display: 'flex', alignItems: 'center', gap: 12, width: '100%',
  padding: '10px 12px', textAlign: 'left', cursor: 'pointer',
  background: 'transparent', border: 'none',
  borderBottom: '0.5px solid var(--border)', fontFamily: MONO,
  fontSize: 'var(--fs-body)', color: 'var(--text-main)',
}

export default function TechSheetEntry() {
  const navigate = useNavigate()
  const { t } = useTranslation()

  const [search, setSearch] = useState('')
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState(null)
  const [error, setError] = useState(null)
  // Quan el backend rebutja per allow-list, guardem el model per oferir la consulta.
  const [consultaModel, setConsultaModel] = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    const params = { ordering: '-data_entrada', page_size: PAGE_SIZE }
    if (search) params.search = search
    modelsApi.list(params)
      .then(r => {
        const d = r.data
        setItems(Array.isArray(d) ? d : (d.results || []))
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [search])

  useEffect(() => {
    const id = setTimeout(load, 250)   // debounce de la cerca
    return () => clearTimeout(id)
  }, [load])

  const obrirConsulta = (modelId) => navigate(`/models/${modelId}/fitxa`)

  const obrir = async (model) => {
    setBusyId(model.id)
    setError(null)
    setConsultaModel(null)
    try {
      const res = await modelsApi.openTask(model.id, 'tech_sheet')
      const taskId = res?.data?.task_id
      if (!taskId) {
        // Resposta inesperada: NO degradem silenciosament a consulta. Val més que el sistema
        // sembli trencat que amagar un fallo real fent passar per consulta el que no ho és.
        setError(t('tech_sheet_entry.unexpected_response'))
        return
      }
      navigate(`/models/${model.id}/fitxa?task_id=${taskId}`)
    } catch (e) {
      const status = e?.response?.status
      const code = e?.response?.data?.code
      if (status === 403 && code === 'task_type_not_allowed') {
        // Bloqueig tou: l'usuari no té tech_sheet a l'allow-list, però pot consultar-la.
        setConsultaModel(model)
      } else {
        // Bloqueig dur (sense EXECUTE_TASKS, sense perfil, 409, timeout…): error, sense consulta.
        setError(e?.response?.data?.error || t('tech_sheet_entry.open_error'))
      }
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div style={{ padding: '1.5rem', maxWidth: 720 }}>
      <h1 style={{ fontSize: 'var(--fs-h1)', fontWeight: 500, marginBottom: 4 }}>
        {t('tech_sheet_entry.title')}
      </h1>
      <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginBottom: 20 }}>
        {t('tech_sheet_entry.subtitle')}
      </p>

      <input
        type="search"
        value={search}
        onChange={e => setSearch(e.target.value)}
        placeholder={t('tech_sheet_entry.search_placeholder')}
        aria-label={t('tech_sheet_entry.search_placeholder')}
        style={inputStyle}
      />

      {error && (
        <div role="alert" style={{
          marginTop: 12, padding: '10px 12px', borderRadius: 4,
          border: '0.5px solid var(--err)', color: 'var(--err)',
          fontSize: 'var(--fs-body)',
        }}>
          <i className="ti ti-alert-circle" aria-hidden="true" style={{ marginRight: 6 }} />
          {error}
        </div>
      )}

      {consultaModel && (
        <div role="alert" style={{
          marginTop: 12, padding: '12px', borderRadius: 4,
          border: '0.5px solid var(--gold)', fontSize: 'var(--fs-body)',
        }}>
          <div style={{ marginBottom: 8 }}>
            <i className="ti ti-lock" aria-hidden="true" style={{ marginRight: 6, color: 'var(--gold)' }} />
            {t('tech_sheet_entry.not_allowed', { codi: consultaModel.codi_intern })}
          </div>
          <button
            type="button"
            onClick={() => obrirConsulta(consultaModel.id)}
            style={{
              background: 'var(--white)', color: 'var(--gold)',
              border: '0.5px solid var(--gold)', borderRadius: 6,
              padding: '6px 14px', fontSize: 'var(--fs-body)',
              cursor: 'pointer', fontFamily: MONO,
            }}>
            <i className="ti ti-eye" aria-hidden="true" style={{ marginRight: 6 }} />
            {t('tech_sheet_entry.open_readonly')}
          </button>
        </div>
      )}

      <div style={{ marginTop: 16, border: '0.5px solid var(--border)', borderRadius: 6, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: 16, fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
            {t('app.loading')}
          </div>
        ) : items.length === 0 ? (
          <div style={{ padding: 16, fontSize: 'var(--fs-body)', color: 'var(--text-muted)', fontStyle: 'italic' }}>
            {t('tech_sheet_entry.no_models')}
          </div>
        ) : items.map(m => (
          <button key={m.id} type="button" style={rowStyle}
            disabled={busyId !== null}
            onClick={() => obrir(m)}>
            <i className="ti ti-file-text" aria-hidden="true" style={{ color: 'var(--gold)' }} />
            <span style={{ fontWeight: 500 }}>{m.codi_intern}</span>
            <span style={{ color: 'var(--text-muted)', flex: 1 }}>{m.nom_prenda || '—'}</span>
            {busyId === m.id && (
              <span style={{ color: 'var(--text-muted)' }}>{t('app.loading')}</span>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}
