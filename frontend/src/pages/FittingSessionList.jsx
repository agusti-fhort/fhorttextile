import { useState, useEffect, useMemo, useCallback, Fragment } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { fittingSessions, models as modelsApi, plan } from '../api/endpoints'
import StatCard from '../components/ui/StatCard'
import Card from '../components/ui/Card'
import Badge from '../components/ui/Badge'
import Modal from '../components/ui/Modal'

// Backend enums (línia divisòria sagrada — valors en català, no es toquen).
const FASES = ['', 'Pending', 'Dev', 'Proto', 'SizeSet', 'PP', 'TOP']
const ESTATS = ['', 'Oberta', 'Programada', 'Tancada', 'Anullada']

const estatVariant = {
  Programada: 'gate',   // planificada, encara no oberta (sense variant 'blue' → 'gate' distint)
  Oberta:   'warn',
  Tancada:  'ok',
  Anullada: 'gray',
}

const filterBtn = (active) => ({
  background: active ? 'var(--charcoal)' : 'var(--white)',
  color:      active ? 'var(--white)' : 'var(--gray)',
  border: '0.5px solid #e4e4e2', borderRadius: 8,
  padding: '5px 12px', fontSize: 11, cursor: 'pointer',
})

// Cercle de color d'assignació (color_avatar). Fallback --gold si null.
const ColorDot = ({ color, size = 14 }) => (
  <span style={{ display: 'inline-block', width: size, height: size, borderRadius: '50%',
    background: color || 'var(--gold)', border: '0.5px solid var(--gray-l)', flexShrink: 0 }} />
)

// Assistents → ColorDots (màx 4 + "+N"). Rep [{id, nom, color_avatar}].
const AttendeeDots = ({ attendees }) => {
  if (!attendees || !attendees.length) return <span style={{ color: 'var(--gray)' }}>—</span>
  const shown = attendees.slice(0, 4)
  const extra = attendees.length - shown.length
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}>
      {shown.map(a => <ColorDot key={a.id} color={a.color_avatar} />)}
      {extra > 0 && <span style={{ fontSize: 10, color: 'var(--gray)' }}>+{extra}</span>}
    </span>
  )
}

const thStyle = (align) => ({
  padding: '0.7rem 1rem', fontSize: 10, letterSpacing: '0.1em',
  textTransform: 'uppercase', color: 'var(--gray)', fontWeight: 400,
  borderBottom: '0.5px solid var(--gray-l)', textAlign: align || 'left', whiteSpace: 'nowrap',
})
const tdStyle = (align, extra) => ({
  padding: '0.75rem 1rem', fontSize: 12, textAlign: align || 'left', ...extra,
})
const miniBtn = (primary) => ({
  fontSize: 11, padding: '3px 10px', borderRadius: 4, cursor: 'pointer',
  border: primary ? 'none' : '0.5px solid var(--gray-l)',
  background: primary ? 'var(--charcoal)' : 'var(--white)',
  color: primary ? 'var(--white)' : 'var(--gray)',
})

export default function FittingSessionList() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [fase, setFase] = useState('')
  const [estat, setEstat] = useState('')
  const [stats, setStats] = useState({ total: 0, Oberta: 0, Tancada: 0, Anullada: 0 })
  const [openGroups, setOpenGroups] = useState(() => new Set())   // UUIDs desplegats (default: tot plegat)
  // Peça 3 — accions de grup i de sessió.
  const [menuGrup, setMenuGrup] = useState(null)     // uuid amb el menú 3-punts obert
  const [modalGrup, setModalGrup] = useState(null)   // {uuid, tipus, data, start_time, model_id, fase, attendee_ids}
  const [rowAction, setRowAction] = useState(null)   // {id, tipus:'delete'|'discard', motiu, err}
  const [actBusy, setActBusy] = useState(false)
  const [modelOpts, setModelOpts] = useState([])     // models per al selector add-model
  const [eligibles, setEligibles] = useState([])     // assistents elegibles per attendees

  const load = useCallback(() => {
    setLoading(true)
    const params = { page_size: 100 }
    if (fase) params.fase = fase
    if (estat) params.estat = estat
    return fittingSessions.list(params)
      .then(res => setData(res.data.results || []))
      .finally(() => setLoading(false))
  }, [fase, estat])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    Promise.all([
      fittingSessions.list({ page_size: 1 }),
      fittingSessions.list({ estat: 'Oberta', page_size: 1 }),
      fittingSessions.list({ estat: 'Tancada', page_size: 1 }),
      fittingSessions.list({ estat: 'Anullada', page_size: 1 }),
    ]).then(([a, b, c, d]) => {
      setStats({
        total: a.data.count,
        Oberta: b.data.count,
        Tancada: c.data.count,
        Anullada: d.data.count,
      })
    })
  }, [])

  // Partició: sessions amb convocatoria → grups (ordenats per data+start_time); resta → individuals.
  const { grups, individuals } = useMemo(() => {
    const conv = {}
    const ind = []
    const key = s => `${s.data || ''}${s.start_time || ''}`
    data.forEach(s => {
      if (s.convocatoria) {
        (conv[s.convocatoria] = conv[s.convocatoria] || []).push(s)
      } else {
        ind.push(s)
      }
    })
    Object.values(conv).forEach(g => g.sort((a, b) => (key(a) > key(b) ? 1 : -1)))
    const grups = Object.entries(conv)
      .map(([uuid, sessions]) => ({ uuid, sessions }))
      .sort((a, b) => (key(a.sessions[0]) > key(b.sessions[0]) ? 1 : -1))
    return { grups, individuals: ind }
  }, [data])

  const toggleGrup = (uuid) => setOpenGroups(prev => {
    const next = new Set(prev)
    next.has(uuid) ? next.delete(uuid) : next.add(uuid)
    return next
  })

  // Estat agregat d'un grup: si tots igual → aquell estat; si mixt → "En curs (X/N tancades)".
  const estatAgregat = (sessions) => {
    const estats = new Set(sessions.map(s => s.estat))
    if (estats.size === 1) {
      const e = [...estats][0]
      return { text: sessions[0].estat_display || e, variant: estatVariant[e] || 'gray' }
    }
    const tancades = sessions.filter(s => s.estat === 'Tancada').length
    return { text: `En curs (${tancades}/${sessions.length} tancades)`, variant: 'gate' }
  }

  // Unió d'assistents d'un grup (dedup per id).
  const attendeesUnio = (sessions) => {
    const m = new Map()
    sessions.forEach(s => (s.attendees_info || []).forEach(a => m.set(a.id, a)))
    return [...m.values()]
  }

  const sum = (sessions, f) => sessions.reduce((acc, s) => acc + (s[f] || 0), 0)
  const hasRows = grups.length > 0 || individuals.length > 0

  // ── Accions de grup (C2) ──────────────────────────────────────────────────
  const openGrupModal = (uuid, tipus, sessions) => {
    setMenuGrup(null)
    if (tipus === 'addModel' && !modelOpts.length) {
      modelsApi.list({ page_size: 500, ordering: 'codi_intern' })
        .then(r => setModelOpts(r.data.results || r.data || [])).catch(() => {})
    }
    if (tipus === 'attendees' && !eligibles.length) {
      plan.eligibleAttendees().then(r => setEligibles(r.data?.results ?? r.data ?? [])).catch(() => {})
    }
    const primera = sessions[0]
    setModalGrup({
      uuid, tipus, err: null,
      data: primera?.data || '', start_time: '',
      model_id: '', fase: primera?.fase || '',
      attendee_ids: tipus === 'attendees' ? attendeesUnio(sessions).map(a => a.id) : [],
    })
  }

  const doReschedule = () => {
    setActBusy(true)
    const payload = { data: modalGrup.data }
    if (modalGrup.start_time) payload.start_time = modalGrup.start_time
    fittingSessions.groupReschedule(modalGrup.uuid, payload)
      .then(() => { setModalGrup(null); load() })
      .catch(e => setModalGrup(m => ({ ...m, err: e.response?.data?.error || 'error' })))
      .finally(() => setActBusy(false))
  }

  const doAddModel = () => {
    if (!modalGrup.model_id) { setModalGrup(m => ({ ...m, err: t('fitting.group.select_model', 'Selecciona un model') })); return }
    setActBusy(true)
    const payload = { model_id: Number(modalGrup.model_id) }
    if (modalGrup.fase) payload.fase = modalGrup.fase
    fittingSessions.groupAddModel(modalGrup.uuid, payload)
      .then(() => { setModalGrup(null); load() })
      .catch(e => setModalGrup(m => ({ ...m,
        err: e.response?.status === 409
          ? (e.response?.data?.error || t('fitting.group.model_in_group', 'Model ja és al grup'))
          : (e.response?.data?.error || 'error') })))
      .finally(() => setActBusy(false))
  }

  const doAttendees = () => {
    setActBusy(true)
    fittingSessions.groupAttendees(modalGrup.uuid, { attendee_ids: modalGrup.attendee_ids })
      .then(() => { setModalGrup(null); load() })
      .catch(e => setModalGrup(m => ({ ...m, err: e.response?.data?.error || 'error' })))
      .finally(() => setActBusy(false))
  }

  // Ajust 1 — eliminar la convocatòria en bloc (atòmic; 409 amb models conflictius).
  const doRemoveGroup = () => {
    setActBusy(true)
    fittingSessions.groupRemove(modalGrup.uuid)
      .then(() => { setModalGrup(null); load() })
      .catch(e => {
        if (e.response?.status === 409) {
          const models = (e.response.data?.conflicts || [])
            .map(c => c.model_codi || `#${c.id}`).join(', ')
          setModalGrup(m => ({ ...m, err: t('fitting.group.remove_conflict',
            { models, defaultValue: `No es pot eliminar: hi ha sessions ja obertes ({{models}}). Descarta-les primer.` }) }))
        } else {
          setModalGrup(m => ({ ...m, err: e.response?.data?.error || 'error' }))
        }
      })
      .finally(() => setActBusy(false))
  }

  // ── Accions de sessió (C3/C4) ─────────────────────────────────────────────
  const doRemove = (id) => {
    setActBusy(true)
    fittingSessions.remove(id)
      .then(() => { setRowAction(null); load() })
      .catch(e => setRowAction({ id, tipus: 'delete',
        err: e.response?.status === 409
          ? t('fitting.row.use_discard', 'Usa Descartar per a sessions ja obertes.')
          : (e.response?.data?.error || 'error') }))
      .finally(() => setActBusy(false))
  }

  const doDiscard = (id, motiu) => {
    setActBusy(true)
    fittingSessions.discardSession(id, motiu || '')
      .then(() => { setRowAction(null); load() })
      .catch(e => setRowAction(r => ({ ...r, err: e.response?.data?.error || 'error' })))
      .finally(() => setActBusy(false))
  }

  // Cel·la d'accions d'una sessió (eliminar si Programada; descartar si Programada/Oberta).
  const iconBtn = { background: 'none', border: 'none', cursor: 'pointer', color: 'var(--gray)', fontSize: 14, padding: '2px 4px' }
  const SessionActionsCell = ({ s }) => (
    <span style={{ display: 'inline-flex', gap: 4, justifyContent: 'flex-end' }} onClick={e => e.stopPropagation()}>
      {(s.estat === 'Programada' || s.estat === 'Oberta') && (
        <button style={iconBtn} title={t('fitting.row.discard', 'Descartar sessió')}
          onClick={() => setRowAction({ id: s.id, tipus: 'discard', motiu: '', err: null })}>
          <i className="ti ti-circle-x" />
        </button>
      )}
      {s.estat === 'Programada' && (
        <button style={{ ...iconBtn, color: 'var(--err)' }} title={t('fitting.row.delete', 'Eliminar')}
          disabled={actBusy} onClick={() => doRemove(s.id)}>
          <i className="ti ti-trash" />
        </button>
      )}
    </span>
  )

  // Sub-fila inline de confirmació/motiu (delete o discard) per a una sessió.
  const RowActionPanel = ({ id, colSpan }) => {
    if (!rowAction || rowAction.id !== id) return null
    return (
      <tr style={{ background: 'var(--warn-bg)' }}>
        <td colSpan={colSpan} style={{ padding: '10px 16px' }}>
          {rowAction.tipus === 'delete' ? (
            // Ajust 2 — sense confirmació: el borrat és directe; aquí només es mostra l'error (p.ex. 409).
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10, fontSize: 12 }}>
              {rowAction.err && <span style={{ color: 'var(--err)' }}>{rowAction.err}</span>}
              <button style={miniBtn(false)} onClick={() => setRowAction(null)}>{t('common.dismiss', 'D\'acord')}</button>
            </span>
          ) : (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10, fontSize: 12, flexWrap: 'wrap' }}>
              {t('fitting.row.discard_label', 'Motiu (opcional):')}
              <input type="text" value={rowAction.motiu || ''} autoFocus
                onChange={e => setRowAction(r => ({ ...r, motiu: e.target.value }))}
                style={{ fontSize: 12, padding: '3px 8px', border: '1px solid var(--gray-l)', borderRadius: 4, minWidth: 220 }} />
              <button style={miniBtn(true)} disabled={actBusy} onClick={() => doDiscard(id, rowAction.motiu)}>{t('common.confirm', 'Confirmar')}</button>
              <button style={miniBtn(false)} disabled={actBusy} onClick={() => setRowAction(null)}>{t('common.cancel', 'Cancel·lar')}</button>
              {rowAction.err && <span style={{ color: 'var(--err)' }}>{rowAction.err}</span>}
            </span>
          )}
        </td>
      </tr>
    )
  }

  return (
    <div>
      <div style={{display: 'flex', alignItems: 'flex-start', marginBottom: '1.5rem'}}>
        <div>
          <h1 style={{fontSize: 20, fontWeight: 500, marginBottom: 4}}>{t('fitting.sessions.title')}</h1>
          <p style={{fontSize: 12, color: 'var(--gray)', fontWeight: 300}}>
            {stats.total}
          </p>
        </div>
        <button onClick={() => navigate('/fittings/new')} style={{
          marginLeft: 'auto',
          background: 'var(--charcoal)', color: 'var(--white)',
          border: 'none', borderRadius: 8, padding: '8px 16px',
          fontSize: 12, cursor: 'pointer', 
        }}>
          + {t('fitting.sessions.new')}
        </button>
      </div>

      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '1rem', marginBottom: '1.5rem',
      }}>
        <StatCard icon="ti-clipboard-list" label={t('fitting.sessions.title')} value={stats.total} />
        <StatCard icon="ti-folder-open"    label={t('fitting.estats.Oberta')}   value={stats.Oberta}   subColor="var(--warn)" />
        <StatCard icon="ti-circle-check"   label={t('fitting.estats.Tancada')}  value={stats.Tancada}  subColor="var(--ok)" />
        <StatCard icon="ti-ban"            label={t('fitting.estats.Anullada')} value={stats.Anullada} subColor="var(--gray)" />
      </div>

      <div style={{display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap'}}>
        <span style={{fontSize: 11, color: 'var(--gray)', alignSelf: 'center', marginRight: 4}}>
          {t('fitting.session.fase')}:
        </span>
        {FASES.map(f => (
          <button key={`f-${f}`} onClick={() => setFase(f)} style={filterBtn(fase === f)}>
            {f || t('fitting.sessions.all')}
          </button>
        ))}
        <span style={{fontSize: 11, color: 'var(--gray)', alignSelf: 'center', marginLeft: 12, marginRight: 4}}>
          {t('fitting.session.estat')}:
        </span>
        {ESTATS.map(e => (
          <button key={`e-${e}`} onClick={() => setEstat(e)} style={filterBtn(estat === e)}>
            {e ? t(`fitting.estats.${e}`, e) : t('fitting.sessions.all')}
          </button>
        ))}
      </div>

      <Card padding={0}>
        {loading ? (
          <div style={{padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
            {t('common.loading', 'Carregant…')}
          </div>
        ) : !hasRows ? (
          <div style={{padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
            {t('fitting.sessions.empty')}
          </div>
        ) : (
          <table style={{width: '100%', borderCollapse: 'collapse'}}>
            <thead>
              <tr>
                <th style={thStyle()}>{t('fitting.session.date')}</th>
                <th style={thStyle()}>{t('fitting.session.target')}</th>
                <th style={thStyle()}>{t('fitting.session.fase')}</th>
                <th style={thStyle()}>{t('fitting.session.estat')}</th>
                <th style={thStyle()}>{t('fitting.session.attendees', 'Assistents')}</th>
                <th style={thStyle('right')}>{t('fitting.session.min', 'Min')}</th>
                <th style={thStyle('right')}>{t('fitting.session.n_peces')}</th>
                <th style={thStyle('right')}></th>
              </tr>
            </thead>
            <tbody>
              {/* ── GRUPS (convocatòries) ── */}
              {grups.map(({ uuid, sessions }) => {
                const isOpen = openGroups.has(uuid)
                const primera = sessions[0]
                const ea = estatAgregat(sessions)
                return (
                  <Fragment key={uuid}>
                    <tr onClick={() => toggleGrup(uuid)}
                      style={{ background: 'var(--bg-muted)', cursor: 'pointer', fontWeight: 500,
                               borderBottom: '0.5px solid var(--gray-l)' }}>
                      <td style={tdStyle()}>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                          <i className="ti ti-chevron-right" style={{
                            fontSize: 14, transition: 'transform 0.15s',
                            transform: isOpen ? 'rotate(90deg)' : 'rotate(0deg)' }} />
                          <span>{primera.data || '—'}{primera.start_time ? ` · ${primera.start_time.slice(0, 5)}` : ''}</span>
                        </span>
                      </td>
                      <td style={tdStyle()}>
                        <span style={{ fontWeight: 500 }}>
                          {t('fitting.convocatoria', 'Convocatòria')} · {sessions.length} {t('fitting.models', 'models')}
                        </span>
                      </td>
                      <td style={tdStyle()}><Badge variant="gate">{primera.fase_display || primera.fase}</Badge></td>
                      <td style={tdStyle()}><Badge variant={ea.variant}>{ea.text}</Badge></td>
                      <td style={tdStyle()}><AttendeeDots attendees={attendeesUnio(sessions)} /></td>
                      <td style={tdStyle('right', { fontVariantNumeric: 'tabular-nums' })}>{sum(sessions, 'duracio_minuts')}</td>
                      <td style={tdStyle('right', { fontVariantNumeric: 'tabular-nums' })}>{sum(sessions, 'n_peces')}</td>
                      <td style={tdStyle('right', { position: 'relative', overflow: 'visible' })} onClick={e => e.stopPropagation()}>
                        <button style={iconBtn} title={t('fitting.group.actions', 'Accions de grup')}
                          onClick={() => setMenuGrup(menuGrup === uuid ? null : uuid)}>
                          <i className="ti ti-dots-vertical" />
                        </button>
                        {menuGrup === uuid && (
                          <>
                            <div onClick={() => setMenuGrup(null)} style={{ position: 'fixed', inset: 0, zIndex: 40 }} />
                            <div style={{ position: 'absolute', right: 12, top: '100%', zIndex: 41, background: 'var(--white)',
                              border: '0.5px solid var(--gray-l)', borderRadius: 8, boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
                              minWidth: 170, textAlign: 'left', padding: 4 }}>
                              {[
                                { k: 'reschedule', icon: 'ti-calendar-event', label: t('fitting.group.reschedule', 'Reagendar') },
                                { k: 'addModel', icon: 'ti-plus', label: t('fitting.group.add_model', 'Afegir model') },
                                { k: 'attendees', icon: 'ti-users', label: t('fitting.group.attendees', 'Canviar assistents') },
                                { k: 'removeGroup', icon: 'ti-trash', label: t('fitting.group.remove', 'Eliminar convocatòria'), danger: true },
                              ].map(it => (
                                <button key={it.k} onClick={() => openGrupModal(uuid, it.k, sessions)}
                                  style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%', background: 'none',
                                    border: 'none', cursor: 'pointer', padding: '7px 10px', fontSize: 12,
                                    color: it.danger ? 'var(--err)' : 'var(--text-main)',
                                    borderRadius: 6 }}>
                                  <i className={`ti ${it.icon}`} style={{ fontSize: 14, color: it.danger ? 'var(--err)' : 'var(--gray)' }} /> {it.label}
                                </button>
                              ))}
                            </div>
                          </>
                        )}
                      </td>
                    </tr>
                    {isOpen && sessions.map((s, j) => (
                      <Fragment key={`${uuid}-${s.id}`}>
                      <tr onClick={() => navigate(`/fittings/${s.id}`)}
                        style={{ background: 'var(--bg-card)', cursor: 'pointer', fontSize: 13,
                                 borderBottom: j < sessions.length - 1 ? '0.5px solid var(--gray-l)' : '0.5px solid var(--gray-l)' }}>
                        <td style={tdStyle(null, { paddingLeft: 24, borderLeft: '2px solid var(--gold-pale)', color: 'var(--gray)' })}>
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                            <i className="ti ti-corner-down-right" style={{ fontSize: 12, color: 'var(--gray)' }} />
                            {s.start_time ? s.start_time.slice(0, 5) : '—'}
                          </span>
                        </td>
                        <td style={tdStyle(null, { fontSize: 11, color: 'var(--gold)', fontWeight: 500 })}>{s.target?.label || '—'}</td>
                        <td style={tdStyle(null, { color: 'var(--gray)' })}>—</td>
                        <td style={tdStyle()}><Badge variant={estatVariant[s.estat] || 'gray'}>{s.estat_display || s.estat}</Badge></td>
                        <td style={tdStyle(null, { color: 'var(--gray)' })}>—</td>
                        <td style={tdStyle('right', { fontVariantNumeric: 'tabular-nums' })}>{s.duracio_minuts || '—'}</td>
                        <td style={tdStyle('right', { fontVariantNumeric: 'tabular-nums' })}>{s.n_peces ?? 0}</td>
                        <td style={tdStyle('right')}><SessionActionsCell s={s} /></td>
                      </tr>
                      <RowActionPanel id={s.id} colSpan={8} />
                      </Fragment>
                    ))}
                  </Fragment>
                )
              })}

              {/* ── INDIVIDUALS (convocatoria=None) — format pla ── */}
              {individuals.map((r, i) => (
                <Fragment key={r.id}>
                <tr onClick={() => navigate(`/fittings/${r.id}`)}
                  style={{ cursor: 'pointer',
                           borderBottom: i < individuals.length - 1 ? '0.5px solid var(--gray-l)' : 'none' }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--gray-l)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'none'}>
                  <td style={tdStyle(null, { color: 'var(--gray)', fontWeight: 300 })}>
                    {r.data || '—'}{r.start_time ? ` · ${r.start_time.slice(0, 5)}` : ''}
                  </td>
                  <td style={tdStyle(null, { fontSize: 11, color: 'var(--gold)', fontWeight: 500 })}>{r.target?.label || '—'}</td>
                  <td style={tdStyle()}><Badge variant="gate">{r.fase_display || r.fase}</Badge></td>
                  <td style={tdStyle()}><Badge variant={estatVariant[r.estat] || 'gray'}>{r.estat_display || r.estat}</Badge></td>
                  <td style={tdStyle()}><AttendeeDots attendees={r.attendees_info} /></td>
                  <td style={tdStyle('right', { fontVariantNumeric: 'tabular-nums' })}>{r.duracio_minuts || '—'}</td>
                  <td style={tdStyle('right', { fontVariantNumeric: 'tabular-nums' })}>{r.n_peces ?? 0}</td>
                  <td style={tdStyle('right')}><SessionActionsCell s={r} /></td>
                </tr>
                <RowActionPanel id={r.id} colSpan={8} />
                </Fragment>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {/* ── Modals de grup (C2) ── */}
      {modalGrup?.tipus === 'reschedule' && (
        <Modal title={t('fitting.group.reschedule', 'Reagendar')}
          confirmLabel={actBusy ? t('common.saving', 'Desant…') : t('common.confirm', 'Confirmar')}
          cancelLabel={t('common.cancel', 'Cancel·lar')} confirmDisabled={actBusy}
          onConfirm={doReschedule} onCancel={() => !actBusy && setModalGrup(null)}>
          <label style={{ fontSize: 11, color: 'var(--gray)' }}>{t('fitting.session.date', 'Data')}</label>
          <input type="date" value={modalGrup.data} onChange={e => setModalGrup(m => ({ ...m, data: e.target.value }))}
            style={{ width: '100%', marginBottom: 12, padding: '6px 8px', border: '1px solid var(--gray-l)', borderRadius: 4, fontSize: 13 }} />
          <label style={{ fontSize: 11, color: 'var(--gray)' }}>{t('fitting.group.start_time_opt', "Hora d'inici (opcional)")}</label>
          <input type="time" value={modalGrup.start_time} onChange={e => setModalGrup(m => ({ ...m, start_time: e.target.value }))}
            style={{ width: '100%', padding: '6px 8px', border: '1px solid var(--gray-l)', borderRadius: 4, fontSize: 13 }} />
          {modalGrup.err && <div style={{ color: 'var(--err)', fontSize: 12, marginTop: 10 }}>{modalGrup.err}</div>}
        </Modal>
      )}

      {modalGrup?.tipus === 'addModel' && (
        <Modal title={t('fitting.group.add_model', 'Afegir model')}
          confirmLabel={actBusy ? t('common.saving', 'Desant…') : t('common.confirm', 'Confirmar')}
          cancelLabel={t('common.cancel', 'Cancel·lar')} confirmDisabled={actBusy}
          onConfirm={doAddModel} onCancel={() => !actBusy && setModalGrup(null)}>
          <label style={{ fontSize: 11, color: 'var(--gray)' }}>{t('fitting.session.target', 'Model')}</label>
          <select value={modalGrup.model_id} onChange={e => setModalGrup(m => ({ ...m, model_id: e.target.value }))}
            style={{ width: '100%', marginBottom: 12, padding: '6px 8px', border: '1px solid var(--gray-l)', borderRadius: 4, fontSize: 13 }}>
            <option value="">— {t('fitting.group.select_model', 'Selecciona un model')} —</option>
            {modelOpts.map(m => (
              <option key={m.id} value={m.id}>{m.codi_intern}{m.nom_prenda ? ` · ${m.nom_prenda}` : ''}</option>
            ))}
          </select>
          <label style={{ fontSize: 11, color: 'var(--gray)' }}>{t('fitting.session.fase', 'Fase')}</label>
          <select value={modalGrup.fase} onChange={e => setModalGrup(m => ({ ...m, fase: e.target.value }))}
            style={{ width: '100%', padding: '6px 8px', border: '1px solid var(--gray-l)', borderRadius: 4, fontSize: 13 }}>
            {FASES.filter(Boolean).map(f => <option key={f} value={f}>{f}</option>)}
          </select>
          {modalGrup.err && <div style={{ color: 'var(--err)', fontSize: 12, marginTop: 10 }}>{modalGrup.err}</div>}
        </Modal>
      )}

      {modalGrup?.tipus === 'attendees' && (
        <Modal title={t('fitting.group.attendees', 'Canviar assistents')}
          confirmLabel={actBusy ? t('common.saving', 'Desant…') : t('common.confirm', 'Confirmar')}
          cancelLabel={t('common.cancel', 'Cancel·lar')} confirmDisabled={actBusy}
          onConfirm={doAttendees} onCancel={() => !actBusy && setModalGrup(null)}>
          {eligibles.length === 0
            ? <div style={{ fontSize: 12, color: 'var(--gray)' }}>{t('model_sheet.fitting_no_attendees', 'Cap assistent elegible.')}</div>
            : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 240, overflowY: 'auto' }}>
                {eligibles.map(e => {
                  const sel = (modalGrup.attendee_ids || []).includes(e.profile_id)
                  return (
                    <label key={e.profile_id} style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer',
                      padding: '5px 6px', borderRadius: 6, fontSize: 12, background: sel ? 'var(--gold-pale)' : 'transparent' }}>
                      <input type="checkbox" checked={sel} style={{ accentColor: 'var(--gold)' }}
                        onChange={() => setModalGrup(m => ({ ...m,
                          attendee_ids: sel
                            ? m.attendee_ids.filter(id => id !== e.profile_id)
                            : [...(m.attendee_ids || []), e.profile_id] }))} />
                      <ColorDot color={e.color_avatar} />
                      {e.full_name}
                    </label>
                  )
                })}
              </div>
            )}
          {modalGrup.err && <div style={{ color: 'var(--err)', fontSize: 12, marginTop: 10 }}>{modalGrup.err}</div>}
        </Modal>
      )}

      {modalGrup?.tipus === 'removeGroup' && (
        <Modal title={t('fitting.group.remove', 'Eliminar convocatòria')}
          confirmLabel={actBusy ? t('common.saving', 'Desant…') : t('fitting.row.delete', 'Eliminar')}
          cancelLabel={t('common.cancel', 'Cancel·lar')} confirmDisabled={actBusy}
          onConfirm={doRemoveGroup} onCancel={() => !actBusy && setModalGrup(null)}>
          <p style={{ fontSize: 13, lineHeight: 1.5 }}>
            {t('fitting.group.remove_warn', "S'eliminaran totes les sessions de la convocatòria. Aquesta acció no es pot desfer.")}
          </p>
          {modalGrup.err && <div style={{ color: 'var(--err)', fontSize: 12, marginTop: 10 }}>{modalGrup.err}</div>}
        </Modal>
      )}
    </div>
  )
}
