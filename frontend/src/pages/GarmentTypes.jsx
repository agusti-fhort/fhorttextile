import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import { garmentTypes, garmentTypeItems, itemFitxers } from '../api/endpoints'
import FileList from '../components/assets/FileList'
import { UPLOAD_ACCEPT } from '../utils/uploads'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import Modal from '../components/ui/Modal'
import { selS, primaryBtn } from '../components/ui/buttons'
import GroupPills from '../components/GarmentTypeSelector/GroupPills'

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
  // D21 · secció Fitxers del DETALL: un GTI triat, els seus ItemFitxer.
  const [filesItemId, setFilesItemId] = useState(null)
  const [filesRes, setFilesRes] = useState({ clau: null, rows: null })
  const [filesNonce, setFilesNonce] = useState(0)
  const [allVersions, setAllVersions] = useState(false)
  const [uploading, setUploading] = useState(false)

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

  // Els fitxers del GTI triat. Per defecte NOMÉS els caps de cadena (`is_current`): la vista és
  // de consulta del catàleg, i FileList ja mostra la columna `v`. L'historial complet és una
  // pregunta diferent i s'ha de demanar — per això va darrere d'un interruptor, no d'un desplegable
  // per fila: les cadenes són curtes i barrejar-les per nom seria més confús que una llista plana.
  //
  // El resultat va LLIGAT a la clau que el va demanar (mateix patró que `useLlista` de
  // l'AssetNavigator): mentre no casen, encara carreguem → `null`. Així no s'ensenyen mai els
  // fitxers de l'item anterior, i cap effect no crida `setState` de manera síncrona.
  const clauFitxers = filesItemId ? `${filesItemId}:${allVersions}:${filesNonce}` : null
  useEffect(() => {
    if (!clauFitxers) return undefined
    let viu = true
    const params = { garment_type_item: filesItemId, ordering: '-data_pujada' }
    if (!allVersions) params.is_current = true
    itemFitxers.list(params)
      .then(r => { if (viu) setFilesRes({ clau: clauFitxers, rows: r.data?.results ?? (Array.isArray(r.data) ? r.data : []) }) })
      .catch(() => { if (viu) setFilesRes({ clau: clauFitxers, rows: [] }) })
    return () => { viu = false }
  }, [clauFitxers, filesItemId, allVersions])
  const files = filesRes.clau === clauFitxers ? filesRes.rows : null

  const pujarFitxer = async (file) => {
    if (!file || !filesItemId) return
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('garment_type_item', filesItemId)
      fd.append('fitxer', file)
      fd.append('nom', file.name)
      await itemFitxers.create(fd)
      setFilesNonce(n => n + 1)          // rellegeix la llista
      await loadDetail(selectedId)       // i el `fitxers_count` de les cards
      setFeedback({ type: 'ok', text: t('garment_types.files_upload_ok', { nom: file.name }) })
    } catch (e) {
      setFeedback({ type: 'err', text: e?.response?.data?.error || t('garment_types.files_upload_error') })
    } finally {
      setUploading(false)
    }
  }

  // En canviar de type, la selecció d'un item d'un ALTRE type deixa de tenir sentit. Es fa al
  // gest que canvia el type, no a un effect: l'effect només reaccionaria després de renderitzar.
  const triarType = (typeId) => { setSelectedId(typeId); setFilesItemId(null) }

  const selected = types.find(x => x.id === selectedId) || null
  const filesItem = items.find(x => x.id === filesItemId) || null
  const shown = types.filter(x => {
    const s = search.trim().toLowerCase()
    // WIZARD-COMPLET C.1 — la CERCA salta nivells: quan hi ha text, ignora el filtre de grup (busca a
    // totes les famílies pel codi/nom, per resoldre directament sense navegar l'arbre).
    if (s && !(x.codi_client || '').toLowerCase().includes(s) && !(x.nom_client || '').toLowerCase().includes(s)) return false
    if (!s && grup && x.grup !== grup) return false
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
                  <select value={actiu} onChange={e => setActiu(e.target.value)} style={selS}>
                    <option value="">{t('garment_types.all')}</option>
                    <option value="true">{t('garment_types.active')}</option>
                    <option value="false">{t('garment_types.inactive')}</option>
                  </select>
                </div>
                {/* WIZARD-COMPLET C.1 + rectificació pills — selector de GRUP amb el patró ÚNIC compartit
                    (GroupPills), idèntic al selector de peça del wizard i al Navegador de POM Systems.
                    «Tots els grups» és la primera pill del mateix estil. Es desactiva mentre hi ha cerca. */}
                <div style={{ marginBottom: 10, opacity: search.trim() ? 0.45 : 1, pointerEvents: search.trim() ? 'none' : 'auto' }}>
                  <GroupPills value={grup} onChange={setGrup} allLabel={t('garment_types.all_groups')} />
                </div>
                <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', maxHeight: 'calc(100vh - 250px)', overflowY: 'auto' }}>
                  {shown.length === 0 ? <Center>{t('garment_types.empty')}</Center>
                    : shown.map(x => (
                      <div key={x.id} onClick={() => triarType(x.id)} style={{
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
                              onDelete={() => deleteItem(it)}
                              actiu={it.id === filesItemId}
                              onFiles={() => setFilesItemId(id => (id === it.id ? null : it.id))} />
                          ))}
                        </div>
                      )}

                    {/* (4) D21 — FITXERS del GTI triat, amb el FileList compartit del navegador */}
                    {items.length > 0 && (
                      <section style={{ marginTop: 18, border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', overflow: 'hidden' }}>
                        <header style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', borderBottom: '0.5px solid var(--gray-l)' }}>
                          <i className="ti ti-folder" aria-hidden="true" style={{ color: 'var(--gold)' }} />
                          <span style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', fontWeight: 600, flex: 1 }}>
                            {t('garment_types.files_title')}
                            {filesItem && <span style={{ color: 'var(--gray)', fontWeight: 400 }}> · {filesItem.code}</span>}
                          </span>
                          {filesItemId && (
                            <label style={{ display: 'flex', alignItems: 'center', gap: 5, fontFamily: MONO, fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', cursor: 'pointer' }}>
                              <input type="checkbox" checked={allVersions} onChange={e => setAllVersions(e.target.checked)} />
                              {t('garment_types.files_all_versions')}
                            </label>
                          )}
                          {/* Gate CONFIGURE: el mateix que ja regeix a crear/editar/esborrar type i item,
                              i el mateix que el backend imposa a `ItemFitxerViewSet.create` (P4). */}
                          {filesItemId && canEdit && (
                            <label style={{ ...actBtn, color: 'var(--gold)', borderColor: 'var(--gold)', opacity: uploading ? 0.5 : 1, cursor: uploading ? 'default' : 'pointer' }}>
                              <i className="ti ti-file-upload" aria-hidden="true" /> {uploading ? t('garment_types.loading') : t('garment_types.files_upload')}
                              <input type="file" hidden disabled={uploading} accept={UPLOAD_ACCEPT}
                                onChange={e => { const f = e.target.files?.[0]; e.target.value = ''; pujarFitxer(f) }} />
                            </label>
                          )}
                        </header>
                        {!filesItemId
                          ? <div style={{ padding: 20, textAlign: 'center', color: 'var(--gray)', fontFamily: MONO, fontSize: 'var(--fs-body)', fontStyle: 'italic' }}>
                              {t('garment_types.files_pick_item')}
                            </div>
                          : <FileList files={files} emptyLabel={t('garment_types.files_empty')} />}
                      </section>
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
function ItemCard({ it, t, canEdit, onEdit, onDelete, onFiles, actiu = false }) {
  const hasGrading = !!it.grading_rule_set_nom
  const hasBase = it.base_size_label != null
  const hasPoms = (it.poms_count || 0) > 0
  const facets = [hasPoms, hasGrading, hasBase]
  const done = facets.filter(Boolean).length
  return (
    <div style={{ border: `0.5px solid ${actiu ? 'var(--gold)' : 'var(--gray-l)'}`, borderRadius: 12, background: actiu ? 'var(--gold-pale)' : 'var(--white)', padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
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
      {/* D21 — consulta de fitxers: gate de LECTURA (IsAuthenticated), no CONFIGURE. Qui pot veure
          el catàleg pot veure'n els fitxers; només pujar-ne demana CONFIGURE. */}
      <button onClick={onFiles} aria-pressed={actiu}
        style={{ ...actBtn, textAlign: 'left', color: actiu ? 'var(--gold)' : 'var(--text-muted)', borderColor: actiu ? 'var(--gold)' : 'var(--gray-l)' }}>
        <i className="ti ti-folder" aria-hidden="true" /> {t('garment_types.files_title')} · {it.fitxers_count ?? 0}
      </button>
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
