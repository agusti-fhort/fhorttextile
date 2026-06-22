import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import { garmentTypes, garmentTypeItems, taskTimeEstimates, taskTypes } from '../api/endpoints'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import Modal from '../components/ui/Modal'
import { selS, primaryBtn } from '../components/ui/buttons'

// Fase catàlegs — Pas 3 (FUSIONAT) · Garment Types: mestre-detall amb 3 nivells dins el detall:
// (1) capçalera del type · (2) GRAELLA editable items × 9 task_types (matriu de temps integrada,
// desat per fila) · (3) gestió d'items (+ Item / editar / esborrar). Plantilla Peça 0.
// El temps és PREVIST (estimació base; s'ajusta amb dades reals — no es mostren camps Welford).
const MONO = 'IBM Plex Mono, monospace'
const iconBtn = { background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', fontSize: 'var(--fs-h3)', padding: 2 }
const actBtn = {
  background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6, cursor: 'pointer',
  padding: '4px 9px', fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)',
}
const thS = {
  fontFamily: MONO, fontSize: 'var(--fs-label)', fontWeight: 600, color: 'var(--text-muted)', padding: '8px 6px',
  textTransform: 'uppercase', letterSpacing: '.03em', borderBottom: '0.5px solid var(--gray-l)', whiteSpace: 'nowrap',
}
const tdS = { padding: '6px 8px', fontSize: 'var(--fs-body)', borderBottom: '0.5px solid var(--gray-l)', verticalAlign: 'middle' }

export default function GarmentTypes() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const me = useAuthStore(s => s.user)
  const canEdit = !!me?.capabilities?.includes('configure')

  const [types, setTypes] = useState([])
  const [cols, setCols] = useState([])             // 9 TaskTypes (columnes de la matriu)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [feedback, setFeedback] = useState(null)
  const [saving, setSaving] = useState(false)
  const [search, setSearch] = useState('')
  const [grup, setGrup] = useState('')
  const [actiu, setActiu] = useState('true')   // per defecte oculta famílies inactives (catàleg antic)
  const [selectedId, setSelectedId] = useState(null)
  const [items, setItems] = useState([])
  const [detailLoading, setDetailLoading] = useState(false)
  const [cells, setCells] = useState({})           // { itemId: { ttId: { id?, value:'' } } }
  const [dirty, setDirty] = useState({})           // { itemId: true }
  const [savingRow, setSavingRow] = useState(null)
  const [typeModal, setTypeModal] = useState(null)

  const loadTypes = useCallback(() => {
    setError(false)
    return garmentTypes.list({ ordering: 'codi_client', page_size: 500 })
      .then(res => setTypes(res.data?.results ?? (Array.isArray(res.data) ? res.data : [])))
      .catch(() => setError(true))
  }, [])

  useEffect(() => {
    let alive = true
    Promise.all([
      garmentTypes.list({ ordering: 'codi_client', page_size: 500 }),
      taskTypes.list({ ordering: 'default_order', page_size: 100 }),
    ]).then(([gt, tt]) => {
      if (!alive) return
      setTypes(gt.data?.results ?? (Array.isArray(gt.data) ? gt.data : []))
      setCols(tt.data?.results ?? (Array.isArray(tt.data) ? tt.data : []))
    }).catch(() => { if (alive) setError(true) }).finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [])

  // Carrega items + cel·les de temps del type seleccionat (matriu).
  const loadDetail = useCallback((typeId) => {
    if (!typeId) { setItems([]); setCells({}); setDirty({}); return Promise.resolve() }
    setDetailLoading(true)
    return Promise.all([
      garmentTypeItems.list({ garment_type: typeId, ordering: 'complexity_order', page_size: 500 }),
      taskTimeEstimates.list({ page_size: 2000 }),
    ]).then(([itRes, teRes]) => {
      const its = itRes.data?.results ?? (Array.isArray(itRes.data) ? itRes.data : [])
      const tes = teRes.data?.results ?? (Array.isArray(teRes.data) ? teRes.data : [])
      const ids = new Set(its.map(i => i.id))
      const map = {}
      its.forEach(i => { map[i.id] = {} })
      tes.forEach(c => {
        if (ids.has(c.garment_type_item)) {
          map[c.garment_type_item][c.task_type] = { id: c.id, value: c.estimated_minutes == null ? '' : String(c.estimated_minutes) }
        }
      })
      setItems(its); setCells(map); setDirty({})
    }).catch(() => { setItems([]); setCells({}) }).finally(() => setDetailLoading(false))
  }, [])

  useEffect(() => { loadDetail(selectedId) }, [selectedId, loadDetail])

  const selected = types.find(x => x.id === selectedId) || null
  const groups = [...new Set(types.map(x => x.grup).filter(Boolean))].sort()
  const shown = types.filter(x => {
    const s = search.trim().toLowerCase()
    if (s && !(x.codi_client || '').toLowerCase().includes(s) && !(x.nom_client || '').toLowerCase().includes(s)) return false
    if (grup && x.grup !== grup) return false
    if (actiu === 'true' && !x.actiu) return false
    if (actiu === 'false' && x.actiu) return false
    return true
  })

  const deleteType = (tt) => {
    if (!window.confirm(t('garment_types.confirm_delete', { name: tt.nom_client || tt.codi_client }))) return
    setSaving(true); setFeedback(null)
    garmentTypes.remove(tt.id)
      .then(() => { if (selectedId === tt.id) setSelectedId(null); return loadTypes() })
      .then(() => setFeedback({ type: 'ok', text: t('garment_types.deleted') }))
      .catch(e => setFeedback({ type: 'err', text: e?.response?.data?.error || t('garment_types.delete_system') }))
      .finally(() => setSaving(false))
  }

  const deleteItem = (it) => {
    if (!window.confirm(t('garment_types.confirm_delete_item', { code: it.code }))) return
    setSaving(true); setFeedback(null)
    garmentTypeItems.remove(it.id)   // CASCADE → esborra els seus TaskTimeEstimate
      .then(() => loadDetail(selectedId))
      .then(() => setFeedback({ type: 'ok', text: t('garment_types.item_deleted') }))
      .catch(() => setFeedback({ type: 'err', text: t('garment_types.error') }))
      .finally(() => setSaving(false))
  }

  const setCell = (itemId, ttId, value) => {
    setCells(c => ({ ...c, [itemId]: { ...(c[itemId] || {}), [ttId]: { ...(c[itemId]?.[ttId] || {}), value } } }))
    setDirty(d => ({ ...d, [itemId]: true }))
  }

  const saveRow = (item) => {
    setSavingRow(item.id); setFeedback(null)
    const row = cells[item.id] || {}
    const ops = []
    for (const tt of cols) {
      const cell = row[tt.id] || { value: '' }
      const val = String(cell.value ?? '').trim()
      if (val === '') {
        if (cell.id) ops.push(taskTimeEstimates.remove(cell.id))
      } else {
        const num = parseInt(val, 10)
        if (isNaN(num) || num < 0) continue
        if (cell.id) ops.push(taskTimeEstimates.update(cell.id, { estimated_minutes: num }))
        else ops.push(taskTimeEstimates.create({ garment_type_item: item.id, task_type: tt.id, estimated_minutes: num }))
      }
    }
    Promise.all(ops)
      .then(() => taskTimeEstimates.list({ garment_type_item: item.id, page_size: 100 }))   // recarrega NOMÉS la fila
      .then(res => {
        const tes = res.data?.results ?? (Array.isArray(res.data) ? res.data : [])
        const m = {}
        tes.forEach(c => { m[c.task_type] = { id: c.id, value: c.estimated_minutes == null ? '' : String(c.estimated_minutes) } })
        setCells(c => ({ ...c, [item.id]: m }))
        setDirty(d => { const n = { ...d }; delete n[item.id]; return n })
        setFeedback({ type: 'ok', text: t('garment_types.row_saved', { item: item.code }) })
      })
      .catch(() => setFeedback({ type: 'err', text: t('garment_types.error') }))
      .finally(() => setSavingRow(null))
  }

  return (
    <div style={{ minWidth: 0, maxWidth: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, marginBottom: '1rem' }}>
        <div>
          <h1 style={{ fontSize: 'var(--fs-h1)', fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>{t('garment_types.title')}</h1>
          <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontWeight: 300 }}>{t('garment_types.subtitle')}</p>
        </div>
        {canEdit && <button onClick={() => setTypeModal({ mode: 'create' })} style={{ ...primaryBtn, marginLeft: 0 }}>
          <i className="ti ti-plus" style={{ fontSize: 14 }} />{t('garment_types.new')}
        </button>}
      </div>

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      {loading ? <Center>{t('garment_types.loading')}</Center>
        : error ? <Center>{t('garment_types.error')}</Center>
          : (
            <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start', flexWrap: 'wrap' }}>
              {/* MESTRE */}
              <div style={{ flex: '1 1 300px', minWidth: 260, maxWidth: 360 }}>
                <div style={{ display: 'flex', gap: 8, marginBottom: 10, flexWrap: 'wrap' }}>
                  <input value={search} onChange={e => setSearch(e.target.value)} placeholder={t('garment_types.search')} style={{ ...selS, flex: '1 1 120px' }} />
                  <select value={grup} onChange={e => setGrup(e.target.value)} style={selS}>
                    <option value="">{t('garment_types.all_groups')}</option>
                    {groups.map(g => <option key={g} value={g}>{g}</option>)}
                  </select>
                  <select value={actiu} onChange={e => setActiu(e.target.value)} style={selS}>
                    <option value="">{t('garment_types.all')}</option>
                    <option value="true">{t('garment_types.active')}</option>
                    <option value="false">{t('garment_types.inactive')}</option>
                  </select>
                </div>
                <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', maxHeight: 'calc(100vh - 250px)', overflowY: 'auto' }}>
                  {shown.length === 0 ? <Center>{t('garment_types.empty')}</Center>
                    : shown.map(x => (
                      <div key={x.id} onClick={() => setSelectedId(x.id)} style={{
                        padding: '9px 12px', cursor: 'pointer', borderBottom: '0.5px solid var(--gray-l)',
                        background: x.id === selectedId ? 'var(--warn-bg)' : 'transparent',
                      }}>
                        <div style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', fontWeight: 600, color: x.id === selectedId ? 'var(--warn)' : 'var(--text-main)' }}>
                          {x.nom_client || x.nom_ca || x.codi_client}
                          {!x.actiu && <span style={{ marginLeft: 6, fontSize: 'var(--fs-caption)', color: 'var(--gray)' }}>({t('garment_types.inactive')})</span>}
                        </div>
                        <div style={{ fontFamily: MONO, fontSize: 'var(--fs-label)', color: 'var(--gray)' }}>{x.codi_client} · {x.grup}</div>
                      </div>
                    ))}
                </div>
              </div>

              {/* DETALL: capçalera + graella items×task_types */}
              <div style={{ flex: '3 1 540px', minWidth: 340 }}>
                {!selected ? <Center>{t('garment_types.pick')}</Center> : (
                  <div>
                    {/* (1) capçalera del type */}
                    <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', padding: 16, marginBottom: 14 }}>
                      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 10 }}>
                        <div>
                          <div style={{ fontFamily: MONO, fontSize: 'var(--fs-h3)', fontWeight: 600 }}>{selected.nom_client || selected.nom_ca}</div>
                          <div style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--gray)', marginTop: 2 }}>
                            {selected.codi_client} · {selected.grup} · {selected.actiu ? t('garment_types.active') : t('garment_types.inactive')}
                            {selected.is_system && <span style={{ marginLeft: 6, fontSize: 'var(--fs-label)' }}>· {t('garment_types.system')}</span>}
                          </div>
                          {selected.global_codi && <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginTop: 4 }}>{t('garment_types.global')}: {selected.global_codi} · {selected.global_nom}</div>}
                        </div>
                        {canEdit && (
                          <div style={{ display: 'flex', gap: 6 }}>
                            <button onClick={() => setTypeModal({ mode: 'edit', tt: selected })} style={actBtn}>{t('garment_types.edit')}</button>
                            <button onClick={() => deleteType(selected)} disabled={saving} style={{ ...actBtn, color: 'var(--err)', borderColor: 'var(--err)' }}>{t('garment_types.delete')}</button>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* (3) gestió d'items: + Item */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                      <span style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', fontWeight: 600 }}>{t('garment_types.matrix')} · {items.length} {t('garment_types.items').toLowerCase()}</span>
                      {canEdit && <button onClick={() => navigate(`/garment-type-items/nou/${selected.id}`)} style={{ ...primaryBtn, marginLeft: 0 }}>
                        <i className="ti ti-plus" style={{ fontSize: 13 }} />{t('garment_types.new_item')}
                      </button>}
                    </div>

                    {/* (2) GRAELLA editable items × 9 task_types */}
                    {detailLoading ? <Center>{t('garment_types.loading')}</Center>
                      : items.length === 0 ? <Center>{t('garment_types.no_items')}</Center>
                        : (
                          <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', overflowX: 'auto' }}>
                            <table style={{ borderCollapse: 'collapse', width: '100%', fontFamily: MONO }}>
                              <thead>
                                <tr>
                                  <th style={{ ...thS, position: 'sticky', left: 0, background: 'var(--white)', zIndex: 1, minWidth: 150, textAlign: 'left' }}>{t('garment_types.item')}</th>
                                  {cols.map(c => <th key={c.id} style={{ ...thS, textAlign: 'center', minWidth: 60 }} title={c.name}>{c.code}</th>)}
                                  <th style={thS}></th>
                                </tr>
                              </thead>
                              <tbody>
                                {items.map(it => (
                                  <tr key={it.id}>
                                    <td style={{ ...tdS, position: 'sticky', left: 0, background: dirty[it.id] ? 'var(--warn-bg)' : 'var(--white)', zIndex: 1 }}>
                                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                        <div style={{ flex: 1, minWidth: 0 }}>
                                          <div style={{ fontWeight: 600 }}>{it.code}{!it.active && <span style={{ marginLeft: 5, fontSize: 'var(--fs-caption)', color: 'var(--gray)' }}>({t('garment_types.inactive')})</span>}</div>
                                          <div style={{ fontSize: 'var(--fs-label)', color: 'var(--gray)' }}>{it.name}</div>
                                        </div>
                                        {canEdit && (
                                          <>
                                            <button onClick={() => navigate(`/garment-type-items/${it.id}/editar`)} title={t('garment_types.edit')} style={iconBtn}><i className="ti ti-pencil" /></button>
                                            <button onClick={() => deleteItem(it)} title={t('garment_types.delete')} style={{ ...iconBtn, color: 'var(--err)' }}><i className="ti ti-trash" /></button>
                                          </>
                                        )}
                                      </div>
                                    </td>
                                    {cols.map(c => {
                                      const cell = cells[it.id]?.[c.id] || { value: '' }
                                      return (
                                        <td key={c.id} style={{ ...tdS, textAlign: 'center', padding: 4 }}>
                                          <input type="number" min="0" value={cell.value} disabled={!canEdit || savingRow === it.id}
                                            onChange={e => setCell(it.id, c.id, e.target.value)}
                                            style={{ width: 50, textAlign: 'right', fontFamily: MONO, fontSize: 'var(--fs-body)', border: '0.5px solid var(--gray-l)', borderRadius: 4, padding: '3px 4px', background: 'var(--white)' }} />
                                        </td>
                                      )
                                    })}
                                    <td style={{ ...tdS, textAlign: 'right' }}>
                                      {canEdit && (
                                        <button onClick={() => saveRow(it)} disabled={!dirty[it.id] || savingRow === it.id}
                                          style={{ ...primaryBtn, marginLeft: 0, padding: '5px 12px', opacity: (!dirty[it.id] || savingRow === it.id) ? 0.4 : 1, cursor: (!dirty[it.id] || savingRow === it.id) ? 'not-allowed' : 'pointer' }}>
                                          {savingRow === it.id ? t('garment_types.saving') : t('garment_types.save')}
                                        </button>
                                      )}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                  </div>
                )}
              </div>
            </div>
          )}

      {typeModal && (
        <TypeModal mode={typeModal.mode} tt={typeModal.tt} t={t} saving={saving} setSaving={setSaving}
          onCancel={() => setTypeModal(null)}
          onSaved={(msg) => { setTypeModal(null); loadTypes().then(() => setFeedback({ type: 'ok', text: msg })) }}
          onError={(text) => setFeedback({ type: 'err', text })} />
      )}
    </div>
  )
}

function TypeModal({ mode, tt, t, saving, setSaving, onCancel, onSaved, onError }) {
  const isEdit = mode === 'edit'
  const [f, setF] = useState({
    codi_client: tt?.codi_client || '', nom_client: tt?.nom_client || '', nom_ca: tt?.nom_ca || '',
    grup: tt?.grup || '', actiu: tt?.actiu ?? true,
    nom_en: tt?.nom_en || '', nom_es: tt?.nom_es || '', construccio_habitual: tt?.construccio_habitual || '',
  })
  const [more, setMore] = useState(!isEdit)
  const set = (k, v) => setF(s => ({ ...s, [k]: v }))
  const invalid = !f.nom_client.trim() || (!isEdit && !f.codi_client.trim())

  const submit = () => {
    if (invalid) { onError(t('garment_types.required')); return }
    setSaving(true)
    const payload = { ...f, codi_client: f.codi_client.trim(), nom_client: f.nom_client.trim() }   // PATCH parcial: no toca global/targets
    const req = isEdit ? garmentTypes.update(tt.id, payload) : garmentTypes.create(payload)
    req
      .then(() => onSaved(isEdit ? t('garment_types.saved') : t('garment_types.created')))
      .catch(e => onError(e?.response?.data?.codi_client?.[0] || e?.response?.data?.detail || t('garment_types.error')))
      .finally(() => setSaving(false))
  }

  return (
    <Modal title={isEdit ? t('garment_types.edit_title') : t('garment_types.new_title')}
      cancelLabel={t('garment_types.cancel')} confirmLabel={isEdit ? t('garment_types.save') : t('garment_types.create')}
      onCancel={onCancel} onConfirm={submit} confirmDisabled={saving || invalid}>
      <Field label={t('garment_types.f_nom_client')}><input value={f.nom_client} onChange={e => set('nom_client', e.target.value)} style={{ ...selS, width: '100%' }} /></Field>
      <Field label={t('garment_types.f_nom_ca')}><input value={f.nom_ca} onChange={e => set('nom_ca', e.target.value)} style={{ ...selS, width: '100%' }} /></Field>
      <Field label={t('garment_types.f_grup')}><input value={f.grup} onChange={e => set('grup', e.target.value)} placeholder="TOPS / BOTTOMS / …" style={{ ...selS, width: '100%' }} /></Field>
      <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 'var(--fs-body)', marginBottom: 8 }}>
        <input type="checkbox" checked={f.actiu} onChange={e => set('actiu', e.target.checked)} /><span>{t('garment_types.active')}</span>
      </label>
      <button type="button" onClick={() => setMore(m => !m)} style={{ ...actBtn, marginBottom: more ? 12 : 0 }}>
        <i className={`ti ti-chevron-${more ? 'down' : 'right'}`} /> {t('garment_types.more_fields')}
      </button>
      {more && (
        <div>
          <Field label={t('garment_types.f_codi_client')}><input value={f.codi_client} disabled={isEdit && !!tt?.is_system} onChange={e => set('codi_client', e.target.value)} style={{ ...selS, width: '100%' }} /></Field>
          <Field label={t('garment_types.f_nom_en')}><input value={f.nom_en} onChange={e => set('nom_en', e.target.value)} style={{ ...selS, width: '100%' }} /></Field>
          <Field label={t('garment_types.f_nom_es')}><input value={f.nom_es} onChange={e => set('nom_es', e.target.value)} style={{ ...selS, width: '100%' }} /></Field>
          <Field label={t('garment_types.f_construccio')}><input value={f.construccio_habitual} onChange={e => set('construccio_habitual', e.target.value)} placeholder="WOVEN / KNIT / …" style={{ ...selS, width: '100%' }} /></Field>
          {isEdit && (
            <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginTop: 4 }}>
              {tt?.is_system && <div>{t('garment_types.system_note')}</div>}
              <div>{t('garment_types.advanced_note')}</div>
            </div>
          )}
        </div>
      )}
    </Modal>
  )
}

function Field({ label, children }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <label style={{ fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)', textTransform: 'uppercase', display: 'block', marginBottom: 6 }}>{label}</label>
      {children}
    </div>
  )
}
