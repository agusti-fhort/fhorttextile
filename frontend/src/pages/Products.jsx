import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../store/auth'
import { commerce } from '../api/endpoints'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import Modal from '../components/ui/Modal'
import Badge from '../components/ui/Badge'
import { LineTable, RowBtn } from '../components/commercial'
import { selS, primaryBtn } from '../components/ui/buttons'
import TranslatableField, { pickTranslation } from '../components/ui/TranslatableField'

// Mòdul Comercial Studio — B1 · Mestre d'articles (pàgina Productes). Sistema visual unificat
// del mòdul comercial (LineTable + RowBtn + Badge, tipografia continguda).
// Escriptura gated CONFIGURE (backend); el gate de tier del mòdul arriba a B5.
const MONO = 'IBM Plex Mono, monospace'

export default function Products() {
  const { t, i18n } = useTranslation()
  const lang = i18n.resolvedLanguage || i18n.language || 'ca'
  const navigate = useNavigate()
  const me = useAuthStore(s => s.user)
  const canEdit = !!me?.capabilities?.includes('configure')

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [items, setItems] = useState([])
  const [units, setUnits] = useState([])
  const [feedback, setFeedback] = useState(null)
  const [saving, setSaving] = useState(false)
  const [modal, setModal] = useState(null)   // { mode:'create'|'edit', prod? }

  const fetchList = () => commerce.products.list({ ordering: 'code', page_size: 500 })
    .then(res => res.data?.results ?? (Array.isArray(res.data) ? res.data : []))

  const load = useCallback(() => {
    setError(false)
    return fetchList().then(setItems).catch(() => setError(true))
  }, [])

  useEffect(() => {
    let alive = true
    Promise.all([
      fetchList(),
      commerce.units.list({ active: true, page_size: 500 })
        .then(res => res.data?.results ?? (Array.isArray(res.data) ? res.data : [])),
    ])
      .then(([rows, us]) => { if (alive) { setItems(rows); setUnits(us) } })
      .catch(() => { if (alive) setError(true) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [])

  const toggleActive = (prod) => {
    setSaving(true); setFeedback(null)
    commerce.products.update(prod.id, { active: !prod.active })
      .then(() => load())
      .then(() => setFeedback({ type: 'ok', text: t('products.saved') }))
      .catch(() => setFeedback({ type: 'err', text: t('products.error') }))
      .finally(() => setSaving(false))
  }

  const remove = (prod) => {
    if (!window.confirm(t('products.confirm_delete', { name: prod.code }))) return
    setSaving(true); setFeedback(null)
    commerce.products.remove(prod.id)
      .then(() => load())
      .then(() => setFeedback({ type: 'ok', text: t('products.deleted') }))
      .catch(e => setFeedback({ type: 'err', text: e?.response?.data?.detail || t('products.delete_protected') }))
      .finally(() => setSaving(false))
  }

  const natureLabel = (n) => t(`products.nature_${n}`)
  const priceSummary = (r) => {
    if (r.price_mode === 'TIME_BASED') {
      return r.sale_rate != null ? `${r.sale_rate} €/min` : '—'
    }
    return r.base_price != null ? `${r.base_price} €${r.unit_code ? ` / ${r.unit_code}` : ''}` : '—'
  }

  const columns = [
    { key: 'code', label: t('products.col_code'), width: 140, render: r => <span style={{ fontWeight: 600 }}>{r.code}</span> },
    { key: 'name', label: t('products.col_name'), render: r => pickTranslation(r, 'name', lang) },
    { key: 'nature', label: t('products.col_nature'), render: r => natureLabel(r.nature) },
    { key: 'price', label: t('products.col_price'), align: 'right', width: 150, render: r => priceSummary(r) },
    { key: 'active', label: t('products.col_active'), width: 110, render: r => (
      <Badge variant={r.active ? 'ok' : 'gray'}>{r.active ? t('products.active') : t('products.inactive')}</Badge>
    ) },
  ]

  const renderActions = (r) => (
    <>
      <RowBtn icon="ti-arrow-right" title={t('products.open')} disabled={saving}
        onClick={() => navigate(`/comercial/productes/${r.id}`)} />
      {canEdit && <>
        <RowBtn icon="ti-pencil" title={t('products.edit')} disabled={saving}
          onClick={() => setModal({ mode: 'edit', prod: r })} />
        <RowBtn icon={r.active ? 'ti-circle-check' : 'ti-circle'} active={r.active}
          title={r.active ? t('products.deactivate') : t('products.activate')} disabled={saving}
          onClick={() => toggleActive(r)} />
        <RowBtn icon="ti-trash" danger title={t('products.delete')} disabled={saving} onClick={() => remove(r)} />
      </>}
    </>
  )

  return (
    <div style={{ minWidth: 0, maxWidth: 1000 }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, marginBottom: '1rem' }}>
        <div>
          <h1 style={{ fontSize: 'var(--fs-h1)', fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>{t('products.title')}</h1>
          <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontWeight: 300 }}>{t('products.subtitle')}</p>
        </div>
        {canEdit && (
          <button onClick={() => setModal({ mode: 'create' })} style={{ ...primaryBtn, marginLeft: 0 }}>
            <i className="ti ti-plus" style={{ fontSize: 14 }} />{t('products.new')}
          </button>
        )}
      </div>

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      {loading ? <Center>{t('products.loading')}</Center>
        : error ? <Center>{t('products.error')}</Center>
          : items.length === 0 ? (
            <div style={{ border: '0.5px solid var(--border)', borderRadius: 12, background: 'var(--white)', padding: 24, textAlign: 'center', color: 'var(--gray)', fontFamily: MONO, fontSize: 'var(--fs-body)' }}>
              {t('products.empty')}
            </div>
          ) : (
            <div style={{ border: '0.5px solid var(--border)', borderRadius: 12, background: 'var(--white)', overflow: 'hidden' }}>
              <LineTable columns={columns} rows={items} renderActions={renderActions} />
            </div>
          )}

      {modal && (
        <ProductModal mode={modal.mode} prod={modal.prod} units={units} t={t} saving={saving} setSaving={setSaving}
          onCancel={() => setModal(null)}
          onSaved={(msg) => { setModal(null); load().then(() => setFeedback({ type: 'ok', text: msg })) }}
          onError={(text) => setFeedback({ type: 'err', text })} />
      )}
    </div>
  )
}

const NATURES = ['INTERNAL_SERVICE', 'EXTERNAL_SERVICE', 'GOODS', 'PACK']

function ProductModal({ mode, prod, units, t, saving, setSaving, onCancel, onSaved, onError }) {
  const isEdit = mode === 'edit'
  const [code, setCode] = useState(prod?.code || '')
  const [name, setName] = useState(prod?.name || '')
  const [description, setDescription] = useState(prod?.description || '')
  const [translations, setTranslations] = useState(prod?.translations || {})
  const [nature, setNature] = useState(prod?.nature || 'INTERNAL_SERVICE')
  const [priceMode, setPriceMode] = useState(prod?.price_mode || 'FIXED')
  const [basePrice, setBasePrice] = useState(prod?.base_price ?? '')
  const [saleRate, setSaleRate] = useState(prod?.sale_rate ?? '')
  const [markup, setMarkup] = useState(prod?.markup_pct ?? '0')
  const [unit, setUnit] = useState(prod?.unit ?? '')
  const [active, setActive] = useState(prod?.active ?? true)
  const invalid = !code.trim() || !name.trim()

  const submit = () => {
    if (invalid) { onError(t('products.required')); return }
    setSaving(true)
    const payload = {
      code: code.trim(), name: name.trim(), description: description.trim(), translations,
      nature, price_mode: priceMode,
      base_price: basePrice === '' ? null : basePrice,
      sale_rate: saleRate === '' ? null : saleRate,
      markup_pct: markup === '' ? 0 : markup,
      unit: unit === '' ? null : unit,
      active,
    }
    const req = isEdit ? commerce.products.update(prod.id, payload) : commerce.products.create(payload)
    req
      .then(() => onSaved(isEdit ? t('products.saved') : t('products.created')))
      .catch(e => onError(e?.response?.data?.code?.[0] || e?.response?.data?.detail || t('products.error')))
      .finally(() => setSaving(false))
  }

  return (
    <Modal title={isEdit ? t('products.edit_title') : t('products.new_title')}
      cancelLabel={t('products.cancel')} confirmLabel={isEdit ? t('products.save') : t('products.create')}
      onCancel={onCancel} onConfirm={submit} confirmDisabled={saving || invalid}>
      <Field label={t('products.col_code')}><input value={code} onChange={e => setCode(e.target.value)} style={{ ...selS, width: '100%' }} /></Field>
      <TranslatableField label={t('products.col_name')} field="name" value={name} onChange={setName}
        translations={translations} onTranslationsChange={setTranslations} />
      <TranslatableField label={t('products.description')} field="description" value={description} onChange={setDescription}
        translations={translations} onTranslationsChange={setTranslations} multiline />
      <Field label={t('products.col_nature')}>
        <select value={nature} onChange={e => setNature(e.target.value)} style={{ ...selS, width: '100%' }}>
          {NATURES.map(n => <option key={n} value={n}>{t(`products.nature_${n}`)}</option>)}
        </select>
      </Field>
      <Field label={t('products.price_mode')}>
        <select value={priceMode} onChange={e => setPriceMode(e.target.value)} style={{ ...selS, width: '100%' }}>
          <option value="FIXED">{t('products.mode_FIXED')}</option>
          <option value="TIME_BASED">{t('products.mode_TIME_BASED')}</option>
        </select>
      </Field>
      {priceMode === 'FIXED' ? (
        <Field label={t('products.base_price')}><input type="text" inputMode="decimal" value={basePrice} onChange={e => setBasePrice(e.target.value)} style={{ ...selS, width: '100%' }} /></Field>
      ) : (
        <Field label={t('products.sale_rate')}><input type="text" inputMode="decimal" value={saleRate} onChange={e => setSaleRate(e.target.value)} style={{ ...selS, width: '100%' }} /></Field>
      )}
      <Field label={t('products.markup_pct')}><input type="text" inputMode="decimal" value={markup} onChange={e => setMarkup(e.target.value)} style={{ ...selS, width: '100%' }} /></Field>
      <Field label={t('products.unit')}>
        <select value={unit} onChange={e => setUnit(e.target.value)} style={{ ...selS, width: '100%' }}>
          <option value="">{t('products.unit_none')}</option>
          {units.map(u => <option key={u.id} value={u.id}>{u.code}</option>)}
        </select>
      </Field>
      <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 'var(--fs-body)', marginTop: 4 }}>
        <input type="checkbox" checked={active} onChange={e => setActive(e.target.checked)} /><span>{t('products.active')}</span>
      </label>
    </Modal>
  )
}

function Field({ label, children }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={{ fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)', textTransform: 'uppercase', display: 'block', marginBottom: 6 }}>{label}</label>
      {children}
    </div>
  )
}
