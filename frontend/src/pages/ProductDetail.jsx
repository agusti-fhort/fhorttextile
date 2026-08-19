import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'
import useAuthStore from '../store/auth'
import { commerce, taskTypes, suppliers as suppliersApi, garmentTypeItems } from '../api/endpoints'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import Badge from '../components/ui/Badge'
import PageMenu from '../components/ui/PageMenu'
import { camp, forceBarra } from '../components/llista/ChromLlista'
import { botoPri, botoSec, botoDestructiu, apagat } from '../components/ui/buttons'
import { pickTranslation } from '../components/ui/TranslatableField'
import { ProductModal } from './Products'

// FITXA D'ARTICLE (B1) — nucli + satèl·lits (recepta, proveïdors, components, excepcions GTI).
// Excepcions = LLISTA FILTRABLE + «afegir», mai graella densa.
//
// **AQUÍ BAIXEN LES DUES ACCIONS DE GOVERN QUE LA LLISTA HA DEIXAT DE PORTAR** (editar i
// activar/desactivar). La graella canònica de la §8e no dona columna a les accions de fila, i
// aquestes dues parlen d'UN article: el seu lloc és on la pantalla parla d'una entitat. Mateixa
// decisió, i pel mateix motiu, que el govern del client (commit 200). Entren en el MATEIX tram
// que la llista les perd, perquè la capacitat no desaparegui en cap moment intermedi.
const MONO = 'IBM Plex Mono, monospace'
// §5.5 · el botó «Treure» d'una fila de satèl·lit. Es queda DESTRUCTIU —esborra un vincle de
// debò— però amb la vora i la tinta d'error de la casa i mai ple en repòs. (El `smallBtn` que hi
// havia al costat s'ha quedat sense consumidors: l'únic que el feia servir era el botó-fletxa de
// sobre el títol, que ara és el menú de pantalla. No es deixa un estil orfe al fitxer.)
const delBtn = { ...botoDestructiu, padding: '5px 10px' }

export default function ProductDetail() {
  const { t, i18n } = useTranslation()
  const lang = i18n.resolvedLanguage || i18n.language || 'ca'
  const { id } = useParams()
  const me = useAuthStore(s => s.user)
  const canEdit = !!me?.capabilities?.includes('configure')

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [prod, setProd] = useState(null)
  const [feedback, setFeedback] = useState(null)
  // Catàlegs per als selectors dels satèl·lits.
  const [taskCodes, setTaskCodes] = useState([])
  const [supList, setSupList] = useState([])
  const [gtis, setGtis] = useState([])
  const [allProducts, setAllProducts] = useState([])
  // Les unitats les demana el formulari d'article, que ara també s'obre des d'aquí.
  const [units, setUnits] = useState([])

  const reload = useCallback(() => commerce.products.get(id)
    .then(res => setProd(res.data))
    .catch(() => setError(true)), [id])

  useEffect(() => {
    let alive = true
    const rows = (res) => res.data?.results ?? (Array.isArray(res.data) ? res.data : [])
    Promise.all([
      commerce.products.get(id).then(res => res.data),
      taskTypes.list({ active: true, page_size: 500 }).then(rows).catch(() => []),
      suppliersApi.list({ active: true, page_size: 500 }).then(rows).catch(() => []),
      garmentTypeItems.list({ active: true, page_size: 500 }).then(rows).catch(() => []),
      commerce.products.list({ page_size: 500 }).then(rows).catch(() => []),
      commerce.units.list({ active: true, page_size: 500 }).then(rows).catch(() => []),
    ])
      .then(([p, tc, sl, gl, pl, us]) => {
        if (!alive) return
        setProd(p); setTaskCodes(tc); setSupList(sl); setGtis(gl); setAllProducts(pl); setUnits(us)
      })
      .catch(() => { if (alive) setError(true) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [id])

  // Les dues accions de govern que la llista ha deixat de portar (v. la capçalera del fitxer).
  const [busyGovern, setBusyGovern] = useState(false)
  const [editant, setEditant] = useState(false)

  const commutaActiu = () => {
    setBusyGovern(true); setFeedback(null)
    commerce.products.update(prod.id, { active: !prod.active })
      .then(() => reload())
      .then(() => setFeedback({ type: 'ok', text: t('products.saved') }))
      .catch(() => setFeedback({ type: 'err', text: t('products.error') }))
      .finally(() => setBusyGovern(false))
  }

  const ok = (text) => setFeedback({ type: 'ok', text })
  const err = (e) => setFeedback({ type: 'err', text: e?.response?.data?.detail || e?.response?.data?.non_field_errors?.[0] || t('products.error') })

  if (loading) return <Center>{t('products.loading')}</Center>
  if (error || !prod) return <Center>{t('products.error')}</Center>

  return (
    <>
      {/* §8b.2 · el menú de pantalla, amb el ← de destí explícit. El botó-fletxa solt de sobre el
          títol se'n va: la fletxa té UN lloc a tot el producte i és aquest. */}
      <div style={forceBarra}>
        <PageMenu backTo="/comercial/productes" backTitle={t('products.back')} />
      </div>

      {/* §8b.3 · IDENTITAT sobre el fons, sense contenidor: codi en caption + NOM com a h1. El
          codi feia d'h1 i el nom de subtítol gris; a la llista el codi és la dada reina perquè
          allà se cerca, però el TÍTOL d'una fitxa és el nom de la cosa. */}
      <div style={{ padding: '16px 0 12px', maxWidth: 900 }}>
        <div style={{ fontSize: 'var(--fs-caption)', letterSpacing: '.08em', textTransform: 'uppercase',
          color: 'var(--text-soft)', fontFamily: MONO, fontWeight: 600, marginBottom: 4 }}>
          {prod.code}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <h1 style={{ fontSize: 'var(--fs-h1)', lineHeight: '28px', fontWeight: 500,
            fontFamily: MONO, color: 'var(--text-main)', margin: 0 }}>
            {pickTranslation(prod, 'name', lang)}
          </h1>
          <Badge variant={prod.active ? 'ok' : 'gray'}>
            {prod.active ? t('products.active') : t('products.inactive')}
          </Badge>
          {canEdit && (
            <span style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              <button type="button" onClick={() => setEditant(true)} disabled={busyGovern}
                style={{ ...botoSec, ...(busyGovern ? apagat : null) }}>
                <i className="ti ti-pencil" aria-hidden="true" style={{ fontSize: 14, color: 'currentColor' }} />
                {t('products.edit')}
              </button>
              <button type="button" onClick={commutaActiu} disabled={busyGovern}
                style={{ ...(prod.active ? botoDestructiu : botoSec), ...(busyGovern ? apagat : null) }}>
                {prod.active ? t('products.deactivate') : t('products.activate')}
              </button>
            </span>
          )}
        </div>
      </div>

      <div style={{ minWidth: 0, maxWidth: 900 }}>
      {pickTranslation(prod, 'description', lang) && (
        <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)', marginBottom: 16, whiteSpace: 'pre-wrap' }}>
          {pickTranslation(prod, 'description', lang)}
        </p>
      )}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 20 }}>
        <Tag>{t(`products.nature_${prod.nature}`)}</Tag>
        <Tag>{t(`products.mode_${prod.price_mode}`)}</Tag>
        {prod.price_mode === 'TIME_BASED'
          ? prod.sale_rate != null && <Tag>{prod.sale_rate} €/min</Tag>
          : prod.base_price != null && <Tag>{prod.base_price} €{prod.unit_code ? ` / ${prod.unit_code}` : ''}</Tag>}
        {prod.markup_pct != null && Number(prod.markup_pct) !== 0 && <Tag>+{prod.markup_pct}%</Tag>}
      </div>

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      {prod.nature === 'INTERNAL_SERVICE' && (
        <RecipeSection prod={prod} canEdit={canEdit} taskCodes={taskCodes} t={t} reload={reload} ok={ok} err={err} />
      )}
      {(prod.nature === 'EXTERNAL_SERVICE' || prod.nature === 'GOODS') && (
        <SuppliersSection prod={prod} canEdit={canEdit} supList={supList} t={t} reload={reload} ok={ok} err={err} />
      )}
      {prod.nature === 'PACK' && (
        <ComponentsSection prod={prod} canEdit={canEdit} allProducts={allProducts} t={t} reload={reload} ok={ok} err={err} />
      )}
        <ExceptionsSection prod={prod} canEdit={canEdit} gtis={gtis} t={t} reload={reload} ok={ok} err={err} />
      </div>

      {/* «Editar» reobre el mateix modal d'alta/edició que la llista feia servir: una sola
          definició del formulari d'un article, i el gest arriba des d'on es llegeix la fitxa. */}
      {editant && (
        <ProductModal mode="edit" prod={prod} units={units} t={t}
          saving={busyGovern} setSaving={setBusyGovern}
          onCancel={() => setEditant(false)}
          onSaved={(msg) => { setEditant(false); reload().then(() => setFeedback({ type: 'ok', text: msg })) }}
          onError={(text) => setFeedback({ type: 'err', text })} />
      )}
    </>
  )
}

function Tag({ children }) {
  return <span style={{
    fontSize: 'var(--fs-label)', fontWeight: 600, padding: '3px 10px', borderRadius: 999,
    fontFamily: MONO, background: 'var(--bg-page)', color: 'var(--text-soft)',
  }}>{children}</span>
}

function Section({ title, hint, children }) {
  return (
    <div style={{ borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--line)', borderRadius: 'var(--r-card)', background: 'var(--panel)', padding: 16, marginBottom: 16 }}>
      <h2 style={{ fontSize: 'var(--fs-h2)', fontWeight: 500, fontFamily: MONO, marginBottom: hint ? 2 : 10 }}>{title}</h2>
      {hint && <p style={{ fontSize: 'var(--fs-label)', color: 'var(--text-soft)', marginBottom: 10 }}>{hint}</p>}
      {children}
    </div>
  )
}

function Row({ children }) {
  return <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0', borderTopWidth: 1, borderTopStyle: 'solid', borderTopColor: 'var(--line-soft)' }}>{children}</div>
}

// --- Recepta (INTERNAL_SERVICE): task_code per CODE + qty ---
function RecipeSection({ prod, canEdit, taskCodes, t, reload, ok, err }) {
  const [code, setCode] = useState('')
  const [qty, setQty] = useState('1')
  const [busy, setBusy] = useState(false)
  const lines = prod.recipe_lines || []

  const add = () => {
    if (!code) return
    setBusy(true)
    commerce.recipeLines.create({ product: prod.id, task_code: code, qty: qty || 1 })
      .then(() => reload()).then(() => { setCode(''); setQty('1'); ok(t('products.rec_added')) })
      .catch(err).finally(() => setBusy(false))
  }
  const del = (lid) => { setBusy(true); commerce.recipeLines.remove(lid).then(() => reload()).then(() => ok(t('products.rec_removed'))).catch(err).finally(() => setBusy(false)) }

  return (
    <Section title={t('products.recipe')} hint={t('products.recipe_hint')}>
      {lines.length === 0 && <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)' }}>{t('products.recipe_empty')}</p>}
      {lines.map(l => (
        <Row key={l.id}>
          <span style={{ flex: 1, fontFamily: MONO }}>{l.task_code}</span>
          <span style={{ fontFamily: MONO, color: 'var(--text-soft)' }}>×{l.qty}</span>
          {canEdit && <button onClick={() => del(l.id)} disabled={busy} style={delBtn}>{t('products.remove')}</button>}
        </Row>
      ))}
      {canEdit && (
        <div style={{ display: 'flex', gap: 8, marginTop: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <select value={code} onChange={e => setCode(e.target.value)} style={{ ...camp, flex: 1, minWidth: 160 }}>
            <option value="">{t('products.rec_task_ph')}</option>
            {taskCodes.map(tc => <option key={tc.id} value={tc.code}>{tc.code}</option>)}
          </select>
          <input type="text" inputMode="decimal" value={qty} onChange={e => setQty(e.target.value)} style={{ ...camp, width: 80 }} />
          <button onClick={add} disabled={busy || !code} style={botoPri}>{t('products.add')}</button>
        </div>
      )}
    </Section>
  )
}

// --- Proveïdors (EXTERNAL_SERVICE/GOODS): multi-proveïdor amb cost ---
function SuppliersSection({ prod, canEdit, supList, t, reload, ok, err }) {
  const [sup, setSup] = useState('')
  const [cost, setCost] = useState('')
  const [isDefault, setIsDefault] = useState(false)
  const [busy, setBusy] = useState(false)
  const links = prod.suppliers || []

  const add = () => {
    if (!sup || cost === '') return
    setBusy(true)
    commerce.productSuppliers.create({ product: prod.id, supplier: sup, cost_price: cost, is_default: isDefault })
      .then(() => reload()).then(() => { setSup(''); setCost(''); setIsDefault(false); ok(t('products.sup_added')) })
      .catch(err).finally(() => setBusy(false))
  }
  const del = (lid) => { setBusy(true); commerce.productSuppliers.remove(lid).then(() => reload()).then(() => ok(t('products.sup_removed'))).catch(err).finally(() => setBusy(false)) }

  return (
    <Section title={t('products.suppliers')} hint={t('products.suppliers_hint')}>
      {links.length === 0 && <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)' }}>{t('products.suppliers_empty')}</p>}
      {links.map(l => (
        <Row key={l.id}>
          <span style={{ flex: 1 }}>{l.supplier_name}</span>
          {l.is_default && <Tag>{t('products.default')}</Tag>}
          <span style={{ fontFamily: MONO, color: 'var(--text-soft)' }}>{l.cost_price} €</span>
          {canEdit && <button onClick={() => del(l.id)} disabled={busy} style={delBtn}>{t('products.remove')}</button>}
        </Row>
      ))}
      {canEdit && (
        <div style={{ display: 'flex', gap: 8, marginTop: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <select value={sup} onChange={e => setSup(e.target.value)} style={{ ...camp, flex: 1, minWidth: 160 }}>
            <option value="">{t('products.sup_ph')}</option>
            {supList.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          <input type="text" inputMode="decimal" placeholder={t('products.cost')} value={cost} onChange={e => setCost(e.target.value)} style={{ ...camp, width: 100 }} />
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 'var(--fs-body)' }}>
            <input type="checkbox" checked={isDefault} onChange={e => setIsDefault(e.target.checked)} />{t('products.default')}
          </label>
          <button onClick={add} disabled={busy || !sup || cost === ''} style={botoPri}>{t('products.add')}</button>
        </div>
      )}
    </Section>
  )
}

// --- Components (PACK): un sol nivell (el backend rebutja pack-dins-pack) ---
function ComponentsSection({ prod, canEdit, allProducts, t, reload, ok, err }) {
  const [comp, setComp] = useState('')
  const [qty, setQty] = useState('1')
  const [busy, setBusy] = useState(false)
  const parts = prod.components || []
  const candidates = allProducts.filter(p => p.nature !== 'PACK' && p.id !== prod.id)

  const add = () => {
    if (!comp) return
    setBusy(true)
    commerce.productComponents.create({ pack: prod.id, component: comp, qty: qty || 1 })
      .then(() => reload()).then(() => { setComp(''); setQty('1'); ok(t('products.comp_added')) })
      .catch(err).finally(() => setBusy(false))
  }
  const del = (lid) => { setBusy(true); commerce.productComponents.remove(lid).then(() => reload()).then(() => ok(t('products.comp_removed'))).catch(err).finally(() => setBusy(false)) }

  return (
    <Section title={t('products.components')} hint={t('products.components_hint')}>
      {parts.length === 0 && <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)' }}>{t('products.components_empty')}</p>}
      {parts.map(l => (
        <Row key={l.id}>
          <span style={{ flex: 1, fontFamily: MONO }}>{l.component_code}</span>
          <span style={{ color: 'var(--text-soft)' }}>{l.component_name}</span>
          <span style={{ fontFamily: MONO, color: 'var(--text-soft)' }}>×{l.qty}</span>
          {canEdit && <button onClick={() => del(l.id)} disabled={busy} style={delBtn}>{t('products.remove')}</button>}
        </Row>
      ))}
      {canEdit && (
        <div style={{ display: 'flex', gap: 8, marginTop: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <select value={comp} onChange={e => setComp(e.target.value)} style={{ ...camp, flex: 1, minWidth: 160 }}>
            <option value="">{t('products.comp_ph')}</option>
            {candidates.map(p => <option key={p.id} value={p.id}>{p.code} · {p.name}</option>)}
          </select>
          <input type="text" inputMode="decimal" value={qty} onChange={e => setQty(e.target.value)} style={{ ...camp, width: 80 }} />
          <button onClick={add} disabled={busy || !comp} style={botoPri}>{t('products.add')}</button>
        </div>
      )}
    </Section>
  )
}

// --- Excepcions de preu per GTI: LLISTA FILTRABLE + afegir (mai graella densa) ---
function ExceptionsSection({ prod, canEdit, gtis, t, reload, ok, err }) {
  const [filter, setFilter] = useState('')
  const [gti, setGti] = useState('')
  const [price, setPrice] = useState('')
  const [busy, setBusy] = useState(false)
  const exc = prod.price_exceptions || []
  const shown = filter
    ? exc.filter(e => `${e.gti_code} ${e.gti_name}`.toLowerCase().includes(filter.toLowerCase()))
    : exc

  const add = () => {
    if (!gti || price === '') return
    setBusy(true)
    commerce.priceExceptions.create({ product: prod.id, garment_type_item: gti, price })
      .then(() => reload()).then(() => { setGti(''); setPrice(''); ok(t('products.exc_added')) })
      .catch(err).finally(() => setBusy(false))
  }
  const del = (lid) => { setBusy(true); commerce.priceExceptions.remove(lid).then(() => reload()).then(() => ok(t('products.exc_removed'))).catch(err).finally(() => setBusy(false)) }

  return (
    <Section title={t('products.exceptions')} hint={t('products.exceptions_hint')}>
      {exc.length > 0 && (
        <input value={filter} onChange={e => setFilter(e.target.value)} placeholder={t('products.exc_filter_ph')}
          style={{ ...camp, width: '100%', marginBottom: 10 }} />
      )}
      {shown.length === 0 && <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)' }}>{t('products.exceptions_empty')}</p>}
      {shown.map(e => (
        <Row key={e.id}>
          <span style={{ flex: 1, fontFamily: MONO }}>{e.gti_code}</span>
          <span style={{ color: 'var(--text-soft)' }}>{e.gti_name}</span>
          <span style={{ fontFamily: MONO, color: 'var(--text-soft)' }}>{e.price} €</span>
          {canEdit && <button onClick={() => del(e.id)} disabled={busy} style={delBtn}>{t('products.remove')}</button>}
        </Row>
      ))}
      {canEdit && (
        <div style={{ display: 'flex', gap: 8, marginTop: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <select value={gti} onChange={e => setGti(e.target.value)} style={{ ...camp, flex: 1, minWidth: 160 }}>
            <option value="">{t('products.exc_gti_ph')}</option>
            {gtis.map(g => <option key={g.id} value={g.id}>{g.code} · {g.name}</option>)}
          </select>
          <input type="text" inputMode="decimal" placeholder={t('products.price')} value={price} onChange={e => setPrice(e.target.value)} style={{ ...camp, width: 100 }} />
          <button onClick={add} disabled={busy || !gti || price === ''} style={botoPri}>{t('products.add_exception')}</button>
        </div>
      )}
    </Section>
  )
}
