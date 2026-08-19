import { useState, useEffect, useMemo, useCallback, Fragment } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { fittingSessions, plan } from '../api/endpoints'
import AddModelToGroupModal from '../components/model/AddModelToGroupModal'
import ModelPicker from '../components/model/ModelPicker'
import StatCard from '../components/ui/StatCard'
import Card from '../components/ui/Card'
import Badge from '../components/ui/Badge'
import Modal from '../components/ui/Modal'
import PageMenu from '../components/ui/PageMenu'
import { useEnumeracio } from '../utils/vocabulariDominiFont'


// Els dos eixos de filtre eren DOS enums del backend copiats aquí («línia divisòria sagrada»,
// deia el comentari — i tenia raó en tot menys en el lloc). Ara venen de `/vocabulari/`:
// `fases_model` (el backend reusa `Model.FASE_CHOICES` a `FittingSession.fase`) i
// `estats_sessio_fitting`. El `''` de davant NO era part de cap enum: és el botó «totes» d'aquest
// filtre, o sigui crom d'aquesta pantalla, i per això es continua posant aquí i no allà.
const TOTES = ''

const estatVariant = {
  Programada: 'gate',   // planificada, encara no oberta (sense variant 'blue' → 'gate' distint)
  Oberta:   'warn',
  Tancada:  'ok',
  Anullada: 'gray',
}

// §8c · el control de filtre de la casa i el rètol d'element del §8e. Substitueixen el
// `filterBtn`, que pintava el filtre triat en NEGRE PLE (`--charcoal`) amb vora `#e4e4e2` —
// una sisena forma de botó que no és a la §5 i un color fora de paleta.
const camp = {
  fontFamily: 'IBM Plex Mono, monospace', fontSize: 'var(--fs-body)', padding: '6px 10px', height: 32,
  border: '1px solid var(--line)', borderRadius: 'var(--r-ctrl)',
  background: 'var(--panel)', color: 'var(--text-main)',
}
const retol = {
  fontFamily: 'IBM Plex Mono, monospace', fontSize: 'var(--fs-caption)', fontWeight: 600,
  letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-soft)',
}

// Cercle de color d'assignació (color_avatar). Fallback --gold si null.
const ColorDot = ({ color, size = 14 }) => (
  <span style={{ display: 'inline-block', width: size, height: size, borderRadius: '50%',
    background: color || 'var(--gold)', border: '1px solid var(--line)', flexShrink: 0 }} />
)

// Assistents → ColorDots (màx 4 + "+N"). Rep [{id, nom, color_avatar}].
const AttendeeDots = ({ attendees }) => {
  if (!attendees || !attendees.length) return <span style={{ color: 'var(--text-soft)' }}>—</span>
  const shown = attendees.slice(0, 4)
  const extra = attendees.length - shown.length
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}>
      {shown.map(a => <ColorDot key={a.id} color={a.color_avatar} />)}
      {extra > 0 && <span style={{ fontSize: 'var(--fs-label)', color: 'var(--text-soft)' }}>+{extra}</span>}
    </span>
  )
}

// §2 · th 10px MAJÚSCULES tracking .08em «a tot arreu», en pes 600 i tinta `--text-soft`.
const thStyle = (align) => ({
  padding: '8px 16px', fontSize: 'var(--fs-label)', letterSpacing: '.08em',
  textTransform: 'uppercase', color: 'var(--text-soft)', fontWeight: 600,
  borderBottom: '1px solid var(--line)', textAlign: align || 'left', whiteSpace: 'nowrap',
})
const tdStyle = (align, extra) => ({
  padding: '12px 16px', fontSize: 'var(--fs-body)', textAlign: align || 'left', ...extra,
})
// §5 · confirmar/cancel·lar en línia: primària blava i terciària. El negre ple (`--charcoal`)
// no és cap de les sis formes de la §5, i el radi 4 no és cap dels tres de la casa.
const miniBtn = (primary) => ({
  fontFamily: 'IBM Plex Mono, monospace', fontSize: 'var(--fs-body)', fontWeight: primary ? 600 : 500,
  padding: '4px 12px', borderRadius: 'var(--r-ctrl)', cursor: 'pointer',
  borderWidth: 1, borderStyle: 'solid',
  borderColor: primary ? 'var(--accio)' : 'transparent',
  background: primary ? 'var(--accio)' : 'none',
  color: primary ? 'var(--panel)' : 'var(--text-soft)',
})

export default function FittingSessionList() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [fase, setFase] = useState('')
  const [estat, setEstat] = useState('')
  const { codis: fases } = useEnumeracio('fases_model')
  const { codis: estats } = useEnumeracio('estats_sessio_fitting')
  const [stats, setStats] = useState({ total: 0, Oberta: 0, Tancada: 0, Anullada: 0 })
  const [openGroups, setOpenGroups] = useState(() => new Set())   // UUIDs desplegats (default: tot plegat)
  // Peça 3 — accions de grup i de sessió.
  const [menuGrup, setMenuGrup] = useState(null)     // uuid amb el menú 3-punts obert
  const [modalGrup, setModalGrup] = useState(null)   // {uuid, tipus, data, start_time, model_id, fase, attendee_ids}
  const [rowAction, setRowAction] = useState(null)   // {id, tipus:'delete'|'discard', motiu, err}
  const [actBusy, setActBusy] = useState(false)
  const [eligibles, setEligibles] = useState([])     // assistents elegibles per attendees
  const [nowOpen, setNowOpen] = useState(false)      // C4 — picker "Fitting aquí i ara"

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
    // P4 — no és un modal: obre la fulla del dia d'aquesta convocatòria.
    if (tipus === 'openSheet') { navigate(`/fittings/convocatoria/${uuid}`); return }
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
          setModalGrup(m => ({ ...m, err: t('fitting.group.remove_conflict', { models }) }))
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
          ? t('fitting.row.use_discard')
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
  const iconBtn = { background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-soft)', fontSize: 'var(--fs-h3)', padding: '2px 4px' }
  const SessionActionsCell = ({ s }) => (
    <span style={{ display: 'inline-flex', gap: 4, justifyContent: 'flex-end' }} onClick={e => e.stopPropagation()}>
      {(s.estat === 'Programada' || s.estat === 'Oberta') && (
        <button style={iconBtn} title={t('fitting.row.discard')}
          onClick={() => setRowAction({ id: s.id, tipus: 'discard', motiu: '', err: null })}>
          <i className="ti ti-circle-x" />
        </button>
      )}
      {s.estat === 'Programada' && (
        <button style={{ ...iconBtn, color: 'var(--err)' }} title={t('fitting.row.delete')}
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
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10, fontSize: 'var(--fs-body)' }}>
              {rowAction.err && <span style={{ color: 'var(--err)' }}>{rowAction.err}</span>}
              <button style={miniBtn(false)} onClick={() => setRowAction(null)}>{t('common.dismiss')}</button>
            </span>
          ) : (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10, fontSize: 'var(--fs-body)', flexWrap: 'wrap' }}>
              {t('fitting.row.discard_label')}
              <input type="text" value={rowAction.motiu || ''} autoFocus
                onChange={e => setRowAction(r => ({ ...r, motiu: e.target.value }))}
                style={{ fontSize: 'var(--fs-body)', padding: '3px 8px', border: '1px solid var(--line)', borderRadius: 'var(--r-ctrl)', minWidth: 220 }} />
              <button style={miniBtn(true)} disabled={actBusy} onClick={() => doDiscard(id, rowAction.motiu)}>{t('common.confirm')}</button>
              <button style={miniBtn(false)} disabled={actBusy} onClick={() => setRowAction(null)}>{t('common.cancel')}</button>
              {rowAction.err && <span style={{ color: 'var(--err)' }}>{rowAction.err}</span>}
            </span>
          )}
        </td>
      </tr>
    )
  }

  return (
    <>
      {/* §8b · MENÚ DE PANTALLA. Aquesta llista no en tenia cap, i l'acció «fitting ara» era un
          botó de fons `--charcoal` (negre ple) a la capçalera — una sisena forma de botó que no
          és a la §5. En pujar al menú, l'acció **deixa de ser botó i deixa de ser de color**
          (§8e: «el blau viu al contingut; el menú té el seu llenguatge»). */}
      <div style={{ margin: '-1.5rem -1.5rem 0' }}>
        <PageMenu
          backTo="/"
          backTitle={t('fitting.sessions.back_title')}
          items={[{ key: 'ara', label: t('fitting.now.button'), onClick: () => setNowOpen(true) }]}
        />
      </div>

      <div style={{ paddingTop: 16 }}>
      {/* §8e · EL COMPTADOR MANA I ELS FILTRES HI VAN AL COSTAT, mateixa línia. El títol de
          l'entitat deixa de ser `h1` («el nom de l'entitat ja no és títol, és element») i el
          recompte, que anava sol dins d'un `<p>` sota el títol sense dir de què era, passa a
          ser el valor gran amb la seva etiqueta.
          ELS DOS EIXOS DE FILTRE DEIXEN DE SER FILES DE PASTILLES. Eren dues files de botons
          amb el triat en NEGRE PLE (`--charcoal`), i amb sis fases i quatre estats ocupaven dues
          línies senceres per a una tria que un select resol en un control. La §8c: «filtres en
          línia (cerca, selects, dates): control de la casa, alçada única, MAI blaus». */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, paddingBottom: 16, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 'var(--fs-h1)', lineHeight: '28px', fontWeight: 600, color: 'var(--text-main)' }}>
          {stats.total}
        </span>
        <span style={retol}>{t('fitting.sessions.entity')}</span>
        <select value={fase} onChange={e => setFase(e.target.value)}
          aria-label={t('fitting.session.fase')} style={camp}>
          <option value={TOTES}>{t('fitting.session.fase')}: {t('fitting.sessions.all')}</option>
          {(fases || []).map(f => <option key={f} value={f}>{f}</option>)}
        </select>
        <select value={estat} onChange={e => setEstat(e.target.value)}
          aria-label={t('fitting.session.estat')} style={camp}>
          <option value={TOTES}>{t('fitting.session.estat')}: {t('fitting.sessions.all')}</option>
          {(estats || []).map(e => <option key={e} value={e}>{t(`fitting.estats.${e}`, e)}</option>)}
        </select>
      </div>

      {nowOpen && (
        <FittingNowPicker t={t} onClose={() => setNowOpen(false)}
          onCreated={(id) => { setNowOpen(false); navigate(`/fittings/${id}`) }} />
      )}

      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '1rem', marginBottom: '1.5rem',
      }}>
        {/* §8c · els KPI van NEUTRES; cap dels quatre és una alerta (un fitting «obert» no és
            un problema, és el seu estat normal). Els `subColor` que hi havia eren, a més, CODI
            MORT: cap dels quatre passa `sub`, i `subColor` només tenyeix el subtítol. */}
        <StatCard icon="ti-clipboard-list" label={t('fitting.sessions.title')} value={stats.total} />
        <StatCard icon="ti-folder-open"    label={t('fitting.estats.Oberta')}   value={stats.Oberta} />
        <StatCard icon="ti-circle-check"   label={t('fitting.estats.Tancada')}  value={stats.Tancada} />
        <StatCard icon="ti-ban"            label={t('fitting.estats.Anullada')} value={stats.Anullada} />
      </div>

      <Card padding={0}>
        {loading ? (
          <div style={{padding: 16, color: 'var(--text-faint)', fontStyle: 'italic', fontSize: 'var(--fs-body)'}}>
            {t('common.loading')}
          </div>
        ) : !hasRows ? (
          <div style={{padding: 16, color: 'var(--text-faint)', fontStyle: 'italic', fontSize: 'var(--fs-body)'}}>
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
                <th style={thStyle()}>{t('fitting.session.attendees')}</th>
                <th style={thStyle('right')}>{t('fitting.session.min')}</th>
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
                      style={{ background: 'var(--sel)', cursor: 'pointer', fontWeight: 500,
                               borderBottom: '1px solid var(--line-soft)' }}>
                      <td style={tdStyle()}>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                          <i className="ti ti-chevron-right" style={{
                            fontSize: 'var(--fs-h3)', transition: 'transform 0.15s',
                            transform: isOpen ? 'rotate(90deg)' : 'rotate(0deg)' }} />
                          <span>{primera.data || '—'}{primera.start_time ? ` · ${primera.start_time.slice(0, 5)}` : ''}</span>
                        </span>
                      </td>
                      <td style={tdStyle()}>
                        <span style={{ fontWeight: 500 }}>
                          {t('fitting.convocatoria')} · {sessions.length} {t('fitting.models')}
                        </span>
                      </td>
                      <td style={tdStyle()}>{primera.fase_display || primera.fase}</td>
                      <td style={tdStyle()}><Badge variant={ea.variant}>{ea.text}</Badge></td>
                      <td style={tdStyle()}><AttendeeDots attendees={attendeesUnio(sessions)} /></td>
                      <td style={tdStyle('right', { fontVariantNumeric: 'tabular-nums' })}>{sum(sessions, 'duracio_minuts')}</td>
                      <td style={tdStyle('right', { fontVariantNumeric: 'tabular-nums' })}>{sum(sessions, 'n_peces')}</td>
                      <td style={tdStyle('right', { position: 'relative', overflow: 'visible' })} onClick={e => e.stopPropagation()}>
                        <button style={iconBtn} title={t('fitting.group.actions')}
                          onClick={() => setMenuGrup(menuGrup === uuid ? null : uuid)}>
                          <i className="ti ti-dots-vertical" />
                        </button>
                        {menuGrup === uuid && (
                          <>
                            <div onClick={() => setMenuGrup(null)} style={{ position: 'fixed', inset: 0, zIndex: 40 }} />
                            <div style={{ position: 'absolute', right: 12, top: '100%', zIndex: 41, background: 'var(--panel)',
                              border: '1px solid var(--line)', borderRadius: 'var(--r-ctrl)', boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
                              minWidth: 170, textAlign: 'left', padding: 4 }}>
                              {[
                                { k: 'openSheet', icon: 'ti-list-details', label: t('fitting.sheet.open_sheet') },
                                { k: 'reschedule', icon: 'ti-calendar-event', label: t('fitting.group.reschedule') },
                                { k: 'addModel', icon: 'ti-plus', label: t('fitting.group.add_model') },
                                { k: 'attendees', icon: 'ti-users', label: t('fitting.group.attendees') },
                                { k: 'removeGroup', icon: 'ti-trash', label: t('fitting.group.remove'), danger: true },
                              ].map(it => (
                                <button key={it.k} onClick={() => openGrupModal(uuid, it.k, sessions)}
                                  style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%', background: 'none',
                                    border: 'none', cursor: 'pointer', padding: '7px 10px', fontSize: 'var(--fs-body)',
                                    color: it.danger ? 'var(--err)' : 'var(--text-main)',
                                    borderRadius: 6 }}>
                                  <i className={`ti ${it.icon}`} style={{ fontSize: 14, color: it.danger ? 'var(--err)' : 'var(--text-soft)' }} /> {it.label}
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
                        style={{ background: 'var(--panel)', cursor: 'pointer', fontSize: 'var(--fs-body)',
                                 borderBottom: j < sessions.length - 1 ? '1px solid var(--line-soft)' : '1px solid var(--line-soft)' }}>
                        <td style={tdStyle(null, { paddingLeft: 24, borderLeft: '2px solid var(--gold-border)', color: 'var(--text-soft)' })}>
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                            <i className="ti ti-corner-down-right" style={{ fontSize: 12, color: 'var(--text-soft)' }} />
                            {s.start_time ? s.start_time.slice(0, 5) : '—'}
                          </span>
                        </td>
                        <td style={tdStyle(null, { fontSize: 'var(--fs-body)', color: 'var(--text-main)', fontWeight: 600 })}>{s.target?.label || '—'}</td>
                        <td style={tdStyle(null, { color: 'var(--text-soft)' })}>—</td>
                        <td style={tdStyle()}><Badge variant={estatVariant[s.estat] || 'gray'}>{s.estat_display || s.estat}</Badge></td>
                        <td style={tdStyle(null, { color: 'var(--text-soft)' })}>—</td>
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
                           borderBottom: i < individuals.length - 1 ? '1px solid var(--line-soft)' : 'none' }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--sel)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'none'}>
                  <td style={tdStyle(null, { color: 'var(--text-soft)', fontWeight: 300 })}>
                    {r.data || '—'}{r.start_time ? ` · ${r.start_time.slice(0, 5)}` : ''}
                  </td>
                  <td style={tdStyle(null, { fontSize: 'var(--fs-body)', color: 'var(--text-main)', fontWeight: 600 })}>{r.target?.label || '—'}</td>
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
        <Modal title={t('fitting.group.reschedule')}
          confirmLabel={actBusy ? t('common.saving') : t('common.confirm')}
          cancelLabel={t('common.cancel')} confirmDisabled={actBusy}
          onConfirm={doReschedule} onCancel={() => !actBusy && setModalGrup(null)}>
          <label style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)' }}>{t('fitting.session.date')}</label>
          <input type="date" value={modalGrup.data} onChange={e => setModalGrup(m => ({ ...m, data: e.target.value }))}
            style={{ width: '100%', marginBottom: 12, padding: '6px 8px', border: '1px solid var(--line)', borderRadius: 'var(--r-ctrl)', fontSize: 'var(--fs-body)' }} />
          <label style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)' }}>{t('fitting.group.start_time_opt')}</label>
          <input type="time" value={modalGrup.start_time} onChange={e => setModalGrup(m => ({ ...m, start_time: e.target.value }))}
            style={{ width: '100%', padding: '6px 8px', border: '1px solid var(--line)', borderRadius: 'var(--r-ctrl)', fontSize: 'var(--fs-body)' }} />
          {modalGrup.err && <div style={{ color: 'var(--err)', fontSize: 'var(--fs-body)', marginTop: 10 }}>{modalGrup.err}</div>}
        </Modal>
      )}

      {/* P4 — mateix component que la fulla de convocatòria; no es reimplementa. */}
      {modalGrup?.tipus === 'addModel' && (
        <AddModelToGroupModal
          uuid={modalGrup.uuid}
          faseInicial={modalGrup.fase}
          onDone={() => { setModalGrup(null); load() }}
          onCancel={() => setModalGrup(null)}
        />
      )}

      {modalGrup?.tipus === 'attendees' && (
        <Modal title={t('fitting.group.attendees')}
          confirmLabel={actBusy ? t('common.saving') : t('common.confirm')}
          cancelLabel={t('common.cancel')} confirmDisabled={actBusy}
          onConfirm={doAttendees} onCancel={() => !actBusy && setModalGrup(null)}>
          {eligibles.length === 0
            ? <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)' }}>{t('model_sheet.fitting_no_attendees')}</div>
            : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 240, overflowY: 'auto' }}>
                {eligibles.map(e => {
                  const sel = (modalGrup.attendee_ids || []).includes(e.profile_id)
                  return (
                    <label key={e.profile_id} style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer',
                      padding: '5px 6px', borderRadius: 'var(--r-ctrl)', fontSize: 'var(--fs-body)', background: sel ? 'var(--ok-bg)' : 'transparent' }}>
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
          {modalGrup.err && <div style={{ color: 'var(--err)', fontSize: 'var(--fs-body)', marginTop: 10 }}>{modalGrup.err}</div>}
        </Modal>
      )}

      {modalGrup?.tipus === 'removeGroup' && (
        <Modal title={t('fitting.group.remove')}
          confirmLabel={actBusy ? t('common.saving') : t('fitting.row.delete')}
          cancelLabel={t('common.cancel')} confirmDisabled={actBusy}
          onConfirm={doRemoveGroup} onCancel={() => !actBusy && setModalGrup(null)}>
          <p style={{ fontSize: 'var(--fs-body)', lineHeight: 1.5 }}>
            {t('fitting.group.remove_warn')}
          </p>
          {modalGrup.err && <div style={{ color: 'var(--err)', fontSize: 'var(--fs-body)', marginTop: 10 }}>{modalGrup.err}</div>}
        </Modal>
      )}
      </div>
    </>
  )
}

// C4 — "Fitting aquí i ara": UN CLIC, cap formulari. Es tria un model i es crea el fitting
// ARA (schedule-now: data=avui, hora=ara, actor com a responsable/assistent, durada default);
// en èxit s'obre directament l'editor de la sessió. 409 (solapament dur) → error; conflicte
// suau → confirmació i reintent amb force.
//
// La TRIA ja no viu aquí: `ModelPicker` (components/model) és la cerca amb debounce extreta
// d'aquesta funció, desacoblada de l'acte. Aquest embolcall és NOMÉS l'acte.
function FittingNowPicker({ t, onClose, onCreated }) {
  const [busyId, setBusyId] = useState(null)
  const [err, setErr] = useState(null)

  const pick = (m, force = false) => {
    setBusyId(m.id); setErr(null)
    fittingSessions.scheduleNow({ model_id: m.id, ...(force ? { force: true } : {}) })
      .then(r => {
        if (r.data?.requires_confirmation) {   // conflicte suau → confirmar i reintentar amb force
          setBusyId(null)
          if (window.confirm(r.data.warning || t('fitting.now.soft_conflict'))) pick(m, true)
          return
        }
        onCreated(r.data.id)
      })
      .catch(e => { setBusyId(null); setErr(e?.response?.data?.error || t('fitting.now.error')) })
  }

  return (
    <ModelPicker
      title={t('fitting.now.title')}
      subtitle={t('fitting.now.subtitle')}
      searchPlaceholder={t('fitting.now.search_ph')}
      emptyLabel={t('fitting.now.empty')}
      loadingLabel={t('common.loading')}
      cancelLabel={t('common.cancel')}
      busyId={busyId}
      error={err}
      onPick={m => pick(m)}
      onClose={onClose}
    />
  )
}
