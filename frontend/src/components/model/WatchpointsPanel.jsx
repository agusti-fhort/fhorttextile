import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { watchpoints } from '../../api/endpoints'

const fmtDate = (iso) => iso ? new Date(iso).toLocaleString('ca-ES', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' }) : ''
const linkBtn = { background: 'none', border: 'none', cursor: 'pointer', fontSize: 'var(--fs-caption)', color: 'var(--gold)' }

// D-12 — Watchpoints: advertències de TEXT LLIURE que viatgen amb el model a través dels gates.
// Crear (mode treball) + veure/resoldre. Origen = la tasca on es crea (`taskId`). NO van a la fitxa
// tècnica; viuen amb el model perquè un altre tècnic entengui l'advertència.
export default function WatchpointsPanel({ modelId, taskId = null, editable = false, showAllByDefault = false }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [items, setItems] = useState([])
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [showResolved, setShowResolved] = useState(false)
  const [err, setErr] = useState(false)

  const load = useCallback(() => {
    if (!modelId) return
    watchpoints.list({ model: modelId, ordering: '-created_at', page_size: 100 })
      .then(r => setItems(r.data?.results ?? r.data ?? [])).catch(() => {})
  }, [modelId])
  useEffect(() => { load() }, [load])

  const add = () => {
    const v = text.trim()
    if (!v || busy) return
    setBusy(true); setErr(false)
    watchpoints.create({ model: modelId, task: taskId || null, text: v })
      .then(() => { setText(''); load() })
      .catch(() => setErr(true))   // visible: ja no s'empassa el fallo (p.ex. 500)
      .finally(() => setBusy(false))
  }
  const resolve = (id) => { setBusy(true); watchpoints.resolve(id).then(load).finally(() => setBusy(false)) }
  const reopen = (id) => { setBusy(true); watchpoints.reopen(id).then(load).finally(() => setBusy(false)) }

  const open = items.filter(w => w.estat === 'open')
  const resolved = items.filter(w => w.estat === 'resolved')
  // Al dashboard (consulta) volem el fil COMPLET sense dependre del toggle.
  const visible = (showAllByDefault || showResolved) ? items : open

  return (
    // Sense CAIXA pròpia (el marc i el scroll els posa el contenidor de FORA), però SÍ amb capçalera
    // interna "Watchpoints (N obertes)" + "Veure resoltes" (decisió UX: relaciona l'avís amb el component).
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <i className="ti ti-flag" style={{ color: 'var(--warn)' }} />
        <span style={{ fontSize: 'var(--fs-body)', fontWeight: 500, color: 'var(--text-main)' }}>{t('watchpoints.title')}</span>
        <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>({open.length} {t('watchpoints.open')})</span>
        {resolved.length > 0 && (
          <button type="button" onClick={() => setShowResolved(s => !s)}
            style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>
            {showResolved ? t('watchpoints.hide_resolved') : t('watchpoints.show_resolved', { n: resolved.length })}
          </button>
        )}
      </div>
      {editable && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
          <input value={text} onChange={e => setText(e.target.value)} placeholder={t('watchpoints.placeholder')}
            onKeyDown={e => { if (e.key === 'Enter') add() }}
            style={{ flex: 1, font: 'inherit', fontSize: 'var(--fs-body)', padding: '4px 8px', border: '1px solid var(--border)', borderRadius: 4, background: 'var(--white)' }} />
          <button type="button" onClick={add} disabled={busy || !text.trim()}
            style={{ padding: '4px 12px', border: '0.5px solid var(--gold)', borderRadius: 4, background: 'var(--white)', color: 'var(--gold)', cursor: busy ? 'default' : 'pointer', fontSize: 'var(--fs-body)' }}>
            + {t('watchpoints.add')}
          </button>
        </div>
      )}
      {editable && err && (
        <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--err)', marginBottom: 10 }}>
          {t('watchpoints.err_save')}
        </div>
      )}
      {visible.length === 0 ? (
        <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>{t('watchpoints.empty')}</div>
      ) : visible.map(w => (
        <div key={w.id} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', padding: '6px 0', borderTop: '0.5px solid var(--border)' }}>
          <i className={`ti ${w.estat === 'resolved' ? 'ti-check' : 'ti-flag'}`}
            style={{ fontSize: 14, marginTop: 2, color: w.estat === 'resolved' ? 'var(--ok)' : 'var(--warn)' }} />
          <div style={{ flex: 1, minWidth: 0 }}>
            {Array.isArray(w.dades) && w.dades.length > 0 ? (
              // F2 — Watchpoint de SISTEMA (import viu): render PER CLAU en l'idioma del lector.
              <div style={{ fontSize: 'var(--fs-body)',
                            color: w.estat === 'resolved' ? 'var(--text-muted)' : 'var(--text-main)',
                            textDecoration: w.estat === 'resolved' ? 'line-through' : 'none' }}>
                <div style={{ fontWeight: 500 }}>{t('import_missing.title')}</div>
                <ul style={{ margin: '4px 0 0', paddingLeft: 18 }}>
                  {w.dades.map(camp => <li key={camp}>{t(`import_missing.${camp}`, camp)}</li>)}
                </ul>
                {w.estat === 'open' && modelId && (
                  // F4 — gate SUPER SUAU: acció genèrica disponible, però el tècnic decideix (no redirecció).
                  <button type="button" onClick={() => navigate(`/models/${modelId}/editar`)}
                    style={{ ...linkBtn, padding: 0, marginTop: 4, display: 'inline-block' }}>
                    {t('import_missing.action')}
                  </button>
                )}
              </div>
            ) : (
              <div style={{ fontSize: 'var(--fs-body)', whiteSpace: 'pre-wrap',
                            color: w.estat === 'resolved' ? 'var(--text-muted)' : 'var(--text-main)',
                            textDecoration: w.estat === 'resolved' ? 'line-through' : 'none' }}>{w.text}</div>
            )}
            <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>
              {w.created_by_nom || '—'} · {fmtDate(w.created_at)}{w.task_type_code ? ` · ${w.task_type_code}` : ''}
              {w.estat === 'resolved' && w.resolved_by_nom ? ` · ${t('watchpoints.resolved_by', { who: w.resolved_by_nom })}` : ''}
            </div>
          </div>
          {editable && (w.estat === 'open'
            ? <button type="button" onClick={() => resolve(w.id)} disabled={busy} style={linkBtn}>{t('watchpoints.resolve')}</button>
            : <button type="button" onClick={() => reopen(w.id)} disabled={busy} style={linkBtn}>{t('watchpoints.reopen')}</button>)}
        </div>
      ))}
    </div>
  )
}
