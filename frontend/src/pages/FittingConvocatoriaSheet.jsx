// FULLA DE CONVOCATÒRIA (P4) — pantalla intermèdia llista → sessió.
//
// Projecció de LECTURA d'una convocatòria (models del dia + hora + estat + watchpoints oberts),
// amb les accions existents reutilitzades. Cap dada nova al backend:
//   · sessions        → GET fitting-sessions/?convocatoria=<uuid>   (P4a)
//   · watchpoints     → GET watchpoints/?model=<id>&estat=open, UNA crida per model.
//     No hi ha agregat per convocatòria (el Watchpoint s'ancora al MODEL, no a la sessió):
//     és una decisió d'arquitectura pendent, no un problema de volum — una fulla té ~5 models.
//   · afegir model    → AddModelToGroupModal, el MATEIX component que la llista.
//
// Els watchpoints es mostren com a CONTEXT DE LECTURA: la resolució viu al model, no aquí.
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

import { fittingSessions, watchpoints } from '../api/endpoints'
import AddModelToGroupModal from '../components/model/AddModelToGroupModal'
import BackButton from '../components/BackButton'
import Badge from '../components/ui/Badge'
import Card from '../components/ui/Card'
import { thStyle } from './fittingShared'

const estatVariant = { Oberta: 'warn', Tancada: 'ok', Anullada: 'gray', Programada: 'gate' }

const hora = (s) => (s.start_time || '').slice(0, 5) || '—'

export default function FittingConvocatoriaSheet() {
  const { uuid } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()

  const [sessions, setSessions] = useState(null)
  const [wpByModel, setWpByModel] = useState({})
  const [addOpen, setAddOpen] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(() => {
    return fittingSessions.list({ convocatoria: uuid, page_size: 100 })
      .then(r => {
        const rows = r.data.results || r.data || []
        setSessions(rows)
        // Watchpoints oberts, un GET per model (F8b-3: cap agregat). Els models es dedupliquen:
        // una convocatòria pot repetir model si una sessió s'ha descartat i se n'ha creat una altra.
        const modelIds = [...new Set(rows.map(s => s.model).filter(Boolean))]
        return Promise.all(modelIds.map(id =>
          watchpoints.list({ model: id, estat: 'open' })
            .then(res => [id, res.data.results || res.data || []])
            .catch(() => [id, []])
        )).then(parells => setWpByModel(Object.fromEntries(parells)))
      })
      .catch(() => setError(t('fitting.sheet.load_error')))
  }, [uuid, t])

  useEffect(() => { load() }, [load])

  if (error) return <div style={{ padding: '2rem', color: 'var(--err)', fontSize: 'var(--fs-body)' }}>{error}</div>
  if (sessions === null) return <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>{t('app.loading')}</div>

  const primera = sessions[0]
  // Una convocatòria és un acte del dia: data i fase són comunes (schedule_bulk les fixa).
  const subtitol = primera
    ? `${primera.data}${primera.fase ? ` · ${primera.fase}` : ''} · ${t('fitting.sheet.n_models', { n: sessions.length })}`
    : ''

  // Sprint Y — obrir una sessió = obrir la TASCA de presa de mesures a la superfície Mesures amb
  // context de sessió (ModelSheet materialitza la tasca i, en gravar, torna a aquesta fulla via la
  // convocatòria de la pròpia sessió). Sessions segellades (Tancada/Anullada) → split de lectura de
  // FittingDetail (Y7 el conserva).
  const SEALED = ['Tancada', 'Anullada']
  const obrir = (s) => {
    if (SEALED.includes(s.estat)) { navigate(`/fittings/${s.id}`); return }
    navigate(`/models/${s.model}?tab=Mesures&fitting_session=${s.id}`)
  }

  return (
    <div style={{ padding: '1.5rem 2rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: '1.25rem' }}>
        <BackButton to="/fittings" />
        <div>
          <div style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, color: 'var(--text-main)' }}>
            {t('fitting.sheet.title')}
          </div>
          {subtitol && (
            <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>{subtitol}</div>
          )}
        </div>
      </div>

      <Card padding={0} style={{ marginBottom: '1.5rem' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ ...thStyle, width: 70 }}>{t('fitting.sheet.hour')}</th>
              <th style={thStyle}>{t('fitting.session.target')}</th>
              <th style={{ ...thStyle, width: 110 }}>{t('fitting.session.estat')}</th>
              <th style={thStyle}>{t('fitting.sheet.watchpoints')}</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map(s => {
              const wps = wpByModel[s.model] || []
              return (
                <tr key={s.id} onClick={() => obrir(s)} style={{ cursor: 'pointer', borderTop: '1px solid var(--border)' }}>
                  <td style={{ padding: '10px 12px', fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>{hora(s)}</td>
                  <td style={{ padding: '10px 12px', fontSize: 'var(--fs-body)', color: 'var(--text-main)' }}>
                    {s.target?.label || `#${s.model}`}
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    <Badge variant={estatVariant[s.estat] || 'gray'}>{s.estat_display || s.estat}</Badge>
                  </td>
                  <td style={{ padding: '10px 12px', fontSize: 'var(--fs-body)' }}>
                    {wps.length === 0 ? (
                      <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>{t('fitting.sheet.no_watchpoints')}</span>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                        {wps.map(w => (
                          <div key={w.id} style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-main)' }}>
                            <i className="ti ti-flag" style={{ fontSize: 13, color: 'var(--warn)' }} aria-hidden="true" />
                            <span>{w.text || w.task_type_code}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </Card>

      <button type="button" onClick={() => setAddOpen(true)} style={{
        background: 'var(--white)', color: 'var(--gold)', border: '0.5px solid var(--gold)',
        borderRadius: 8, padding: '6px 14px', fontSize: 'var(--fs-body)', cursor: 'pointer',
      }}>+ {t('fitting.group.add_model')}</button>

      {addOpen && (
        <AddModelToGroupModal
          uuid={uuid}
          faseInicial={primera?.fase || ''}
          onDone={() => { setAddOpen(false); load() }}
          onCancel={() => setAddOpen(false)}
        />
      )}
    </div>
  )
}
