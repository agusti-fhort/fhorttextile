import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { fittingSessions, fittingPhotos } from '../../api/endpoints'
import { thStyle, useDebouncedSave, SaveStatus, fmtMeasure, useUnit } from '../../pages/fittingShared'

// Sprint Y — Panell de la SESSIÓ de fitting dins la superfície Mesures (mode sessió). Migra de
// FittingDetail: la franja de context (estat/data/responsable/lloc/persona) + el panell plegable
// Canvis · Observacions · Imatges. Cap pantalla pròpia: és un germà de DependencyPanel/WatchpointsPanel.

const estatColor = { Oberta: 'var(--warn)', Programada: 'var(--gold)', Tancada: 'var(--ok)', Anullada: 'var(--gray)' }

// Ordre de talles segons el size run del model (migrat de FittingDetail): mai alfabètic.
function orderedSizes(sizeRun, present) {
  const run = (sizeRun || '').replace(/;/g, '·').split('·').map(s => s.trim()).filter(Boolean)
  const ordered = run.filter(s => present.has(s))
  const extras = [...present].filter(s => !run.includes(s))
  return [...ordered, ...extras]
}

// Files (POM) amb almenys una talla modificada respecte de Base (evolucio[0]) — migrat de FittingDetail.
function changedRows(grid) {
  const lines = grid?.lines || []
  const present = new Set(lines.map(l => l.size_label))
  const sizeLabels = orderedSizes(grid?.model?.size_run_model, present)
  const baseLabel = (grid?.model?.base_size_label || '').trim()
  const pomMap = new Map()
  for (const l of lines) {
    if (!pomMap.has(l.pom_id)) pomMap.set(l.pom_id, { pom_id: l.pom_id, codi: l.codi, nom: l.nom, is_key: l.is_key, cells: {} })
    pomMap.get(l.pom_id).cells[l.size_label] = l
  }
  const baseOf = (l) => l?.evolucio?.[0]?.valor_cm ?? null
  const isMod = (l) => {
    const b = baseOf(l)
    return l && l.valor_real != null && b != null && Number(l.valor_real) !== Number(b)
  }
  const rows = [...pomMap.values()].filter(row => Object.values(row.cells).some(isMod))
  return { sizeLabels, baseLabel, rows, isMod }
}

// Camp de context editable (autosave PATCH sessió) — migrat de FittingDetail (EditableContextField).
function EditableContextField({ sessionId, field, label, value }) {
  const [v, setV] = useState(value ?? '')
  const persist = useCallback((raw) => fittingSessions.update(sessionId, { [field]: raw }), [sessionId, field])
  const [state, schedule] = useDebouncedSave(persist)
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
      {label}:&nbsp;
      <input value={v} onChange={e => { setV(e.target.value); schedule(e.target.value) }} placeholder="—"
        style={{ width: 120, padding: '1px 2px', fontSize: 'var(--fs-body)', color: 'var(--text-main)',
          border: 'none', borderBottom: '1px solid var(--border)', borderRadius: 0, background: 'transparent', boxSizing: 'border-box' }} />
      <SaveStatus state={state} inline />
    </span>
  )
}

const fmtDate = (iso) => iso ? new Date(iso).toLocaleDateString('ca-ES', { day: '2-digit', month: '2-digit', year: 'numeric' }) : '—'
const muted = { fontSize: 'var(--fs-body)', color: 'var(--text-muted)', fontStyle: 'italic' }

export default function SessionPanel({ session, pieceFittingId, grid }) {
  const { t } = useTranslation()
  const unit = useUnit()                       // unitat del tenant (CM|INCH) → format de presentació
  const [open, setOpen] = useState(false)
  const [notes, setNotes] = useState(session?.notes ?? '')
  const [photos, setPhotos] = useState([])
  const [uploading, setUploading] = useState(false)
  const [err, setErr] = useState(null)

  const reloadPhotos = useCallback(() => {
    if (!session?.id) return
    fittingPhotos.list({ session: session.id })
      .then(r => setPhotos(r.data.results || r.data || [])).catch(() => {})
  }, [session?.id])
  useEffect(() => { if (open) reloadPhotos() }, [open, reloadPhotos])
  useEffect(() => { setNotes(session?.notes ?? '') }, [session?.id, session?.notes])

  if (!session) return null

  const saveNotes = () => { fittingSessions.update(session.id, { notes }).catch(() => {}) }
  const onUpload = (e) => {
    const files = Array.from(e.target.files || [])
    if (!files.length) return
    setUploading(true); setErr(null)
    Promise.all(files.map(f => fittingPhotos.upload(session.id, f, pieceFittingId)))
      .then(reloadPhotos)
      .catch(() => setErr(t('fitting.save.image_error')))
      .finally(() => { setUploading(false); e.target.value = '' })
  }

  const changes = grid ? changedRows(grid) : { rows: [] }

  return (
    <div style={{ border: '0.5px solid var(--border)', borderRadius: 6, background: 'var(--bg-card)', marginBottom: 12 }}>
      {/* Franja de context de la sessió (sempre visible) */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap', padding: '8px 12px' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 'var(--fs-body)', fontWeight: 500, color: 'var(--text-main)' }}>
          <i className="ti ti-ruler-measure" style={{ color: 'var(--gold)' }} />
          {t('fitting.session.panel_title')}
        </span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 'var(--fs-body)', color: estatColor[session.estat] || 'var(--text-muted)' }}>
          <span style={{ width: 7, height: 7, borderRadius: '50%', background: estatColor[session.estat] || 'var(--gray)' }} />
          {t(`fitting.estats.${session.estat}`, session.estat)}
        </span>
        <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
          {fmtDate(session.data)}{session.start_time ? ` · ${session.start_time.slice(0, 5)}` : ''}
        </span>
        <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
          {t('fitting.id.responsible')}: {session.responsable_nom || '—'}
        </span>
        <EditableContextField sessionId={session.id} field="model_persona" label={t('fitting.id.persona')} value={session.model_persona} />
        <EditableContextField sessionId={session.id} field="lloc" label={t('fitting.id.location')} value={session.lloc} />
        <button onClick={() => setOpen(o => !o)} style={{
          marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)',
          fontSize: 'var(--fs-body)', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          <i className={`ti ti-chevron-${open ? 'up' : 'down'}`} style={{ fontSize: 14 }} />
          {t(open ? 'fitting.session.collapse' : 'fitting.session.expand')}
        </button>
      </div>

      {open && (
        <div style={{ padding: '0 12px 12px', borderTop: '0.5px solid var(--border)' }}>
          {/* Canvis (read-only) */}
          <div style={{ marginTop: 12 }}>
            <div style={{ ...muted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8, fontStyle: 'normal', fontWeight: 500 }}>{t('fitting.save.changes')}</div>
            {changes.rows.length === 0 ? (
              <div style={muted}>{t('fitting.save.no_changes')}</div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ borderCollapse: 'collapse', fontSize: 'var(--fs-body)' }}>
                  <thead>
                    <tr>
                      <th style={{ ...thStyle, textAlign: 'left' }}>{t('fitting.grid.pom')}</th>
                      <th style={{ ...thStyle, textAlign: 'left' }}>{t('fitting.grid.name')}</th>
                      {changes.sizeLabels.map(s => (
                        <th key={s} style={{ ...thStyle, textAlign: 'right', background: s === changes.baseLabel ? 'var(--gold-pale)' : undefined }}>{s}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {changes.rows.map((row, i) => (
                      <tr key={row.pom_id} style={{ background: i % 2 === 0 ? 'var(--white)' : 'var(--bg-card)' }}>
                        <td style={{ padding: '5px 10px', borderBottom: '0.5px solid var(--border)', fontWeight: 500, color: 'var(--gold)', whiteSpace: 'nowrap' }}>{row.codi}</td>
                        <td style={{ padding: '5px 10px', borderBottom: '0.5px solid var(--border)', color: 'var(--text-muted)' }}>{row.nom}</td>
                        {changes.sizeLabels.map(s => {
                          const line = row.cells[s]; const mod = changes.isMod(line)
                          return (
                            <td key={s} style={{ padding: '5px 10px', borderBottom: '0.5px solid var(--border)', textAlign: 'right',
                              fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap',
                              background: s === changes.baseLabel ? 'var(--gold-pale)' : undefined,
                              color: mod ? 'var(--err)' : 'var(--text-main)', fontWeight: mod ? 700 : 400 }}>
                              {fmtMeasure(line?.valor_real, unit) ?? '—'}
                            </td>
                          )
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Observacions */}
          <div style={{ marginTop: 16 }}>
            <div style={{ ...muted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8, fontStyle: 'normal', fontWeight: 500 }}>{t('fitting.save.observations')}</div>
            <textarea value={notes} onChange={e => setNotes(e.target.value)} onBlur={saveNotes}
              placeholder={t('fitting.save.no_observations')}
              style={{ width: '100%', minHeight: 70, padding: '8px 10px', fontSize: 'var(--fs-body)',
                border: '1px solid var(--border)', borderRadius: 6, background: 'var(--white)',
                color: 'var(--text-main)', boxSizing: 'border-box', resize: 'vertical', fontFamily: 'inherit' }} />
          </div>

          {/* Imatges */}
          <div style={{ marginTop: 16 }}>
            <div style={{ ...muted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8, fontStyle: 'normal', fontWeight: 500 }}>{t('fitting.save.images')}</div>
            <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, marginBottom: 10,
              cursor: uploading ? 'default' : 'pointer', fontSize: 'var(--fs-body)', color: 'var(--gold)' }}>
              <input type="file" accept="image/*" multiple onChange={onUpload} disabled={uploading} style={{ display: 'none' }} />
              <i className="ti ti-upload" style={{ fontSize: 14 }} />
              {uploading ? t('fitting.save.uploading') : t('fitting.save.add_images')}
            </label>
            {err && <div style={{ color: 'var(--err)', fontSize: 'var(--fs-body)', marginBottom: 8 }}>{err}</div>}
            {photos.length === 0 ? (
              <div style={muted}>{t('fitting.save.no_images')}</div>
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
                {photos.map(f => (
                  <a key={f.id} href={f.fitxer} target="_blank" rel="noopener noreferrer"
                    style={{ display: 'block', width: 140, height: 140, borderRadius: 8, overflow: 'hidden', border: '0.5px solid var(--border)' }}>
                    <img src={f.fitxer} alt={f.caption || ''} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                  </a>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
