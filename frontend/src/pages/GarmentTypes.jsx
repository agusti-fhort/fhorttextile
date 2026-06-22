import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import { garmentTypes, garmentTypeItems } from '../api/endpoints'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import Modal from '../components/ui/Modal'
import { selS, primaryBtn } from '../components/ui/buttons'

// Fase catàlegs · Garment Types: mestre-detall. Esquerra = llista de garment types; dreta =
// capçalera del type + GRAELLA DE CARDS d'item (porta d'entrada a la pàgina d'autoria + termòmetre
// de completesa). B3b: la matriu de temps (TaskTimeEstimate) s'ha tret d'aquí (anirà a Planning);
// model i endpoints intactes al backend.
const MONO = 'IBM Plex Mono, monospace'
const iconBtn = { background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', fontSize: 'var(--fs-h3)', padding: 2 }
const actBtn = {
  background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6, cursor: 'pointer',
  padding: '4px 9px', fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)',
}

export default function GarmentTypes() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const me = useAuthStore(s => s.user)
  const canEdit = !!me?.capabilities?.includes('configure')

  const [types, setTypes] = useState([])
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
  const [typeModal, setTypeModal] = useState(null)

  const loadTypes = useCallback(() => {
    setError(false)
    return garmentTypes.list({ ordering: 'codi_client', page_size: 500 })
      .then(res => setTypes(res.data?.results ?? (Array.isArray(res.data) ? res.data : [])))
      .catch(() => setError(true))
  }, [])

  useEffect(() => {
    let alive = true
    garmentTypes.list({ ordering: 'codi_client', page_size: 500 })
      .then(gt => { if (alive) setTypes(gt.data?.results ?? (Array.isArray(gt.data) ? gt.data : [])) })
      .catch(() => { if (alive) setError(true) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [])

  // Carrega els items del type seleccionat (amb l'estat de completesa: grading_rule_set_nom,
  // base_size_label, poms_count — camps read-only del serializer, B3b).
  const loadDetail = useCallback((typeId) => {
    if (!typeId) { setItems([]); return Promise.resolve() }
    setDetailLoading(true)
    return garmentTypeItems.list({ garment_type: typeId, ordering: 'complexity_order', page_size: 500 })
      .then(itRes => setItems(itRes.data?.results ?? (Array.isArray(itRes.data) ? itRes.data : [])))
      .catch(() => setItems([]))
      .finally(() => setDetailLoading(false))
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

                    {/* gestió d'items: títol + Nou item */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                      <span style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', fontWeight: 600 }}>{t('garment_types.items_title')} · {items.length}</span>
                      {canEdit && <button onClick={() => navigate(`/garment-type-items/nou/${selected.id}`)} style={{ ...primaryBtn, marginLeft: 0 }}>
                        <i className="ti ti-plus" style={{ fontSize: 13 }} />{t('garment_types.new_item')}
                      </button>}
                    </div>

                    {/* GRAELLA DE CARDS d'item: porta d'entrada a l'autoria + termòmetre de completesa */}
                    {detailLoading ? <Center>{t('garment_types.loading')}</Center>
                      : items.length === 0 ? (
                        <div style={{ border: '0.5px dashed var(--gray-l)', borderRadius: 12, padding: '2rem', textAlign: 'center', color: 'var(--gray)' }}>
                          <div style={{ marginBottom: 12, fontSize: 'var(--fs-body)' }}>{t('garment_types.no_items')}</div>
                          {canEdit && <button onClick={() => navigate(`/garment-type-items/nou/${selected.id}`)} style={{ ...primaryBtn, marginLeft: 0 }}>
                            <i className="ti ti-plus" style={{ fontSize: 13 }} />{t('garment_types.new_item')}
                          </button>}
                        </div>
                      ) : (
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 12 }}>
                          {items.map(it => (
                            <ItemCard key={it.id} it={it} t={t} canEdit={canEdit}
                              onEdit={() => navigate(`/garment-type-items/${it.id}/editar`)}
                              onDelete={() => deleteItem(it)} />
                          ))}
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

// Card curta d'item: porta d'entrada a la pàgina d'autoria + termòmetre de completesa
// (POMs · grading · talla base). NO repeteix el detall que s'edita dins (B3).
function ItemCard({ it, t, canEdit, onEdit, onDelete }) {
  const hasGrading = !!it.grading_rule_set_nom
  const hasBase = it.base_size_label != null
  const hasPoms = (it.poms_count || 0) > 0
  const facets = [hasPoms, hasGrading, hasBase]
  const done = facets.filter(Boolean).length
  return (
    <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontFamily: MONO, fontWeight: 600, fontSize: 'var(--fs-body)' }}>
            {it.name}{!it.active && <span style={{ marginLeft: 5, fontSize: 'var(--fs-caption)', color: 'var(--gray)' }}>({t('garment_types.inactive')})</span>}
          </div>
          <div style={{ fontFamily: MONO, fontSize: 'var(--fs-label)', color: 'var(--gray)' }}>{it.code}</div>
        </div>
        {/* termòmetre: 3 punts (POMs · grading · talla base) */}
        <div style={{ display: 'flex', gap: 3, flexShrink: 0, marginTop: 3 }} title={`${done}/3`}>
          {facets.map((on, i) => (
            <span key={i} style={{ width: 8, height: 8, borderRadius: '50%', background: on ? 'var(--gold)' : 'transparent', border: `1px solid ${on ? 'var(--gold)' : 'var(--gray-l)'}` }} />
          ))}
        </div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 3, fontFamily: MONO }}>
        <StatusLine label={t('garment_types.card_poms')} value={String(it.poms_count ?? 0)} on={hasPoms} />
        <StatusLine label={t('garment_types.card_grading')} value={it.grading_rule_set_nom || '—'} on={hasGrading} />
        <StatusLine label={t('garment_types.card_basesize')} value={it.base_size_label || '—'} on={hasBase} />
      </div>
      {canEdit && (
        <div style={{ display: 'flex', gap: 6, marginTop: 'auto', paddingTop: 4 }}>
          <button onClick={onEdit} style={{ ...actBtn, flex: 1, color: 'var(--gold)', borderColor: 'var(--gold)' }}>
            <i className="ti ti-pencil" /> {t('garment_types.edit')}
          </button>
          <button onClick={onDelete} title={t('garment_types.delete')} style={{ ...iconBtn, color: 'var(--err)' }}>
            <i className="ti ti-trash" />
          </button>
        </div>
      )}
    </div>
  )
}

function StatusLine({ label, value, on }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, fontSize: 'var(--fs-label)' }}>
      <span style={{ color: 'var(--text-muted)' }}>{label}</span>
      <span style={{
        color: on ? 'var(--text-main)' : 'var(--gray)', fontWeight: on ? 600 : 400,
        textAlign: 'right', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 150,
      }}>{value}</span>
    </div>
  )
}
