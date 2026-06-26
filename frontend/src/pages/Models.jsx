import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { models as modelsApi } from '../api/endpoints'
import ActionsMenu, { PHASES } from '../components/model/ActionsMenu'
import Feedback from '../components/ui/Feedback'

const MONO = 'IBM Plex Mono, monospace'
const SEASONS = ['SS', 'FW', 'CO', 'SP']
const PAGE_SIZE = 25
const fmtDate = (v, locale) => v ? new Date(v).toLocaleDateString(locale, { day: '2-digit', month: '2-digit', year: '2-digit' }) : '—'

export default function Models() {
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const dateLocale = i18n.language === 'es' ? 'es-ES' : i18n.language === 'en' ? 'en-GB' : 'ca-ES'

  const [items, setItems] = useState([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [feedback, setFeedback] = useState(null)
  const [search, setSearch] = useState('')
  const [fase, setFase] = useState('')
  const [temporada, setTemporada] = useState('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState(() => new Set())
  const [newOpen, setNewOpen] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    const params = { ordering: '-data_entrada', page, page_size: PAGE_SIZE }
    if (search) params.search = search
    if (fase) params.fase_actual = fase
    if (temporada) params.temporada = temporada
    modelsApi.list(params)
      .then(r => {
        const d = r.data
        setItems(Array.isArray(d) ? d : (d.results || []))
        setCount(d.count ?? (Array.isArray(d) ? d.length : 0))
      })
      .catch(() => { setItems([]); setCount(0) })
      .finally(() => setLoading(false))
  }, [search, fase, temporada, page])

  // Debounce de la cerca + reset de pàgina quan canvien filtres.
  useEffect(() => { setPage(1) }, [search, fase, temporada])
  useEffect(() => { const id = setTimeout(load, 200); return () => clearTimeout(id) }, [load])

  const pages = Math.max(1, Math.ceil(count / PAGE_SIZE))
  const selectedModels = useMemo(() => items.filter(m => selected.has(m.id)), [items, selected])
  const allOnPage = items.length > 0 && items.every(m => selected.has(m.id))

  const toggle = (id) => setSelected(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })
  const toggleAll = () => setSelected(s => {
    const n = new Set(s)
    if (allOnPage) items.forEach(m => n.delete(m.id)); else items.forEach(m => n.add(m.id))
    return n
  })
  const afterAction = () => { setSelected(new Set()); load() }

  const remove = async (m, e) => {
    e.stopPropagation()
    if (!window.confirm(t('models_list.confirm_delete', { codi: m.codi_intern }))) return
    try { await modelsApi.destroy(m.id); setFeedback({ type: 'ok', text: '✓' }); load() }
    catch { setFeedback({ type: 'err', text: t('models_list.delete_error') }) }
  }

  return (
    <div style={{ padding: '24px', maxWidth: 1240, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 16 }}>
        <div>
          <h1 style={{ fontSize: 'var(--fs-h2)', fontFamily: MONO, color: 'var(--text-main)', fontWeight: 500, margin: 0 }}>{t('models_list.title')}</h1>
          <div style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontFamily: MONO, marginTop: 2 }}>
            {selected.size > 0 ? t('models_list.selected', { n: selected.size }) : t('models_list.count', { n: count })}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <NewModelMenu open={newOpen} setOpen={setNewOpen} navigate={navigate} t={t} />
          <ActionsMenu targets={selectedModels} onChanged={afterAction} onFeedback={setFeedback} />
        </div>
      </div>

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      {/* Toolbar de filtres */}
      <div style={{ display: 'flex', gap: 8, margin: '12px 0', flexWrap: 'wrap', alignItems: 'center' }}>
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder={t('models_list.search_ph')}
          style={{ ...inp, flex: 1, minWidth: 220 }} />
        <select value={fase} onChange={e => setFase(e.target.value)} style={inp}>
          <option value="">{t('models_list.all_phases')}</option>
          {PHASES.map(p => <option key={p} value={p}>{p}</option>)}
        </select>
        <select value={temporada} onChange={e => setTemporada(e.target.value)} style={inp}>
          <option value="">{t('models_list.all_seasons')}</option>
          {SEASONS.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        {(search || fase || temporada) && (
          <button onClick={() => { setSearch(''); setFase(''); setTemporada('') }} style={{ ...inp, cursor: 'pointer', color: 'var(--gray)' }}>× {t('models_list.clear')}</button>
        )}
      </div>

      {/* Select all */}
      {items.length > 0 && (
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 'var(--fs-body)', color: 'var(--gray)', fontFamily: MONO, margin: '0 0 8px 2px', cursor: 'pointer' }}>
          <input type="checkbox" checked={allOnPage} onChange={toggleAll} />
          {allOnPage ? '✓' : ''}
        </label>
      )}

      {/* Llistat */}
      {loading ? (
        <div style={{ color: 'var(--gray)', fontSize: 'var(--fs-body)', fontFamily: MONO, padding: '20px 0' }}>{t('models_list.loading')}</div>
      ) : items.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--gray)', fontSize: 'var(--fs-body)', fontFamily: MONO }}>
          {(search || fase || temporada) ? t('models_list.empty_filtered') : t('models_list.empty')}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {items.map(m => (
            <ModelRow key={m.id} m={m} selected={selected.has(m.id)} onToggle={() => toggle(m.id)}
              onOpen={() => navigate(`/models/${m.id}`)} onDelete={(e) => remove(m, e)} t={t} locale={dateLocale} />
          ))}
        </div>
      )}

      {/* Paginació */}
      {pages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, marginTop: 18, fontFamily: MONO, fontSize: 'var(--fs-body)' }}>
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1} style={{ ...inp, cursor: page <= 1 ? 'not-allowed' : 'pointer', opacity: page <= 1 ? 0.4 : 1 }}>← {t('models_list.prev')}</button>
          <span style={{ color: 'var(--gray)' }}>{t('models_list.page_info', { page, pages })}</span>
          <button onClick={() => setPage(p => Math.min(pages, p + 1))} disabled={page >= pages} style={{ ...inp, cursor: page >= pages ? 'not-allowed' : 'pointer', opacity: page >= pages ? 0.4 : 1 }}>{t('models_list.next')} →</button>
        </div>
      )}
    </div>
  )
}

function ModelRow({ m, selected, onToggle, onOpen, onDelete, t, locale }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'stretch', gap: 12, borderRadius: 8, background: 'var(--white)',
      border: `1px solid ${selected ? 'var(--gold)' : 'var(--gray-l)'}`,
      boxShadow: selected ? 'inset 0 0 0 1px var(--gold)' : 'none',
    }}>
      {/* Checkbox amb "rowspan" sobre les 2 files */}
      <label onClick={e => e.stopPropagation()} style={{ display: 'flex', alignItems: 'center', padding: '0 4px 0 14px', cursor: 'pointer' }}>
        <input type="checkbox" checked={selected} onChange={onToggle} style={{ width: 15, height: 15 }} />
      </label>

      <div onClick={onOpen} style={{ flex: 1, minWidth: 0, padding: '12px 16px 12px 0', cursor: 'pointer' }}>
        {/* Fila 1 — descriptiva */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8, flexWrap: 'wrap' }}>
          <span style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', fontWeight: 700, color: 'var(--gold)' }}>{m.codi_intern}</span>
          {m.nom_prenda && <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)', fontWeight: 500 }}>{m.nom_prenda}</span>}
          {m.codi_client && <span style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontFamily: MONO }}>· {m.codi_client}</span>}
          {m.collection && <span style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)' }}>· {m.collection}</span>}
          <span style={{ marginLeft: 'auto', fontSize: 'var(--fs-body)', color: 'var(--gray)', fontFamily: MONO }}>{m.temporada}{m.any ? ` ${m.any}` : ''}</span>
          <button onClick={onDelete} title={t('models_list.delete')} style={delBtn}><i className="ti ti-trash" /></button>
        </div>
        {/* Fila 2 — operativa */}
        <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr 1fr 1fr 1.4fr', gap: 12, alignItems: 'center', fontFamily: MONO, fontSize: 'var(--fs-body)' }}>
          <span style={faseBadge}>{m.fase_actual ? t(`model_sheet.dashboard.phase.${m.fase_actual}`, m.fase_actual) : '—'}</span>
          <Cell label={t('models_list.col_entrada')} value={fmtDate(m.entrada_prod, locale)} />
          <Cell label={t('models_list.col_proto')} value={fmtDate(m.arribada_proto, locale)} />
          <Cell label={t('models_list.col_fitting')} value={fmtDate(m.fitting_prev, locale)} />
          <Tecnic label={t('models_list.col_tecnic')} tecnics={m.tecnics} />
        </div>
      </div>
    </div>
  )
}

function Cell({ label, value }) {
  return (
    <div style={{ minWidth: 0 }}>
      <div style={{ fontSize: 'var(--fs-caption)', textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--gray)' }}>{label}</div>
      <div style={{ color: value === '—' ? 'var(--gray-l)' : 'var(--text-main)' }}>{value}</div>
    </div>
  )
}

function Tecnic({ label, tecnics }) {
  const list = tecnics || []
  const principal = list[0]
  return (
    <div style={{ minWidth: 0 }}>
      <div style={{ fontSize: 'var(--fs-caption)', textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--gray)' }}>{label}</div>
      {principal ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 9, height: 9, borderRadius: '50%', background: principal.color || 'var(--gray)', flex: 'none' }} />
          <span style={{ color: 'var(--text-main)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{principal.nom}</span>
          {list.length > 1 && <span style={{ color: 'var(--gray)' }}>+{list.length - 1}</span>}
        </div>
      ) : <div style={{ color: 'var(--gray-l)' }}>—</div>}
    </div>
  )
}

function NewModelMenu({ open, setOpen, navigate, t }) {
  return (
    <div style={{ position: 'relative' }}>
      <button onClick={() => setOpen(o => !o)} style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'var(--white)', color: 'var(--gold)', border: '0.5px solid var(--gold)', borderRadius: 6, padding: '7px 14px', fontSize: 'var(--fs-body)', fontWeight: 600, cursor: 'pointer', fontFamily: MONO }}>
        <i className="ti ti-plus" /> {t('models_list.new_model')} <i className="ti ti-chevron-down" />
      </button>
      {open && (
        <>
          <div onClick={() => setOpen(false)} style={{ position: 'fixed', inset: 0, zIndex: 40 }} />
          <div style={{ position: 'absolute', right: 0, top: 'calc(100% + 4px)', zIndex: 41, background: 'var(--white)', border: '0.5px solid var(--gray-l)', borderRadius: 8, boxShadow: '0 8px 24px rgba(0,0,0,0.12)', padding: 4, minWidth: 200 }}>
            <button onClick={() => { setOpen(false); navigate('/models/nou') }} style={menuItem}><i className="ti ti-edit" /> {t('models_list.manual')}</button>
            <button onClick={() => { setOpen(false); navigate('/models/importar-colleccio') }} style={menuItem}>
              <i className="ti ti-file-spreadsheet" /> {t('nav.import_collection')}
            </button>
          </div>
        </>
      )}
    </div>
  )
}

const inp = { padding: '6px 10px', border: '0.5px solid var(--gray-l)', borderRadius: 6, fontSize: 'var(--fs-body)', fontFamily: MONO, background: 'var(--white)', color: 'var(--text-main)' }
const faseBadge = { fontFamily: MONO, fontSize: 'var(--fs-body)', fontWeight: 600, padding: '2px 8px', borderRadius: 12, background: 'var(--gold)', color: 'var(--white)', justifySelf: 'start' }
const delBtn = { fontSize: 'var(--fs-body)', color: '#C0392B', background: 'none', border: '0.5px solid #FADBD8', borderRadius: 4, padding: '2px 7px', cursor: 'pointer', fontFamily: MONO }
const menuItem = { display: 'flex', alignItems: 'center', gap: 8, width: '100%', textAlign: 'left', background: 'none', border: 'none', padding: '8px 10px', borderRadius: 6, fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-main)', cursor: 'pointer' }
