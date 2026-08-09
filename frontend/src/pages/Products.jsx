import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams } from 'react-router-dom'
import useAuthStore from '../store/auth'
import { commerce } from '../api/endpoints'
import Feedback from '../components/ui/Feedback'
import Modal from '../components/ui/Modal'
import Badge from '../components/ui/Badge'
import PageMenu from '../components/ui/PageMenu'
import TaulaLlista from '../components/ui/TaulaLlista'
import TranslatableField, { pickTranslation } from '../components/ui/TranslatableField'
import { useCodisEstat } from '../components/commercial/estats'
import {
  BotoMenu, SepMenu, Comptador, FilaIdentitat, EstatBuit, BotoEsborrar, Paginacio,
  camp, forceBarra,
} from '../components/llista/ChromLlista'

// MESTRE D'ARTICLES (`Product`, B1) — LLISTA CANONICA DE LA CASA (NORMA_LAYOUT §8b + §8e).
// Escriptura gated CONFIGURE; el gate de tier del modul arriba a B5.
//
// ── TRES COSES QUE ES DIUEN EN VEU ALTA ──────────────────────────────────────────────────
//
// 1 · **LA LLISTA DEIXA DE SER UNA `LineTable`.** `components/commercial/LineTable` es la taula
//    de LINIES D'UN DOCUMENT —cel·les editables, accions a l'esquerra, columna de cost intern—
//    i aixo es una LLISTA PRINCIPAL, que es una altra cosa: la §8e li dona la seva graella, amb
//    capceleres ordenables, amplades per contingut i ellipsis. Que les dues fossin taules no les
//    feia la mateixa taula.
//
// 2 · **LES QUATRE ACCIONS D'ICONA PER FILA ES REPARTEIXEN.** Hi havia quatre `RowBtn` a cada
//    fila (obrir · editar · activar/desactivar · esborrar), i tres d'elles nomes es distingien
//    per la icona. Ara: OBRIR es el clic de la fila (§8e), ESBORRAR es la paperera de la graella,
//    i EDITAR i ACTIVAR/DESACTIVAR baixen a la FITXA del producte, que es on la pantalla parla
//    d'un article i no de molts — la mateixa decisio que a Clients (commit 200).
//
// 3 · **LES DUES ENUMERACIONS VENEN DE `/vocabulari/`** (`natures_producte`, `modes_preu_producte`).
//    N'hi havia una escrita a `NATURES` i l'altra en DOS `<option>` a pel dins del formulari, que
//    es la forma mes silenciosa de totes: una llista que no sembla una llista.
const MONO = 'IBM Plex Mono, monospace'
const PAGE_SIZE = 25
const ORDRE_DEFECTE = { camp: 'code', dir: 'asc' }

export default function Products() {
  const { t, i18n } = useTranslation()
  const lang = i18n.resolvedLanguage || i18n.language || 'ca'
  const navigate = useNavigate()
  const me = useAuthStore(s => s.user)
  const canEdit = !!me?.capabilities?.includes('configure')

  const [items, setItems] = useState([])
  const [count, setCount] = useState(0)
  const [total, setTotal] = useState(null)
  const [units, setUnits] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [feedback, setFeedback] = useState(null)
  const [saving, setSaving] = useState(false)
  const [modal, setModal] = useState(null)   // { mode:'create'|'edit', prod? }

  const { codis: natures } = useCodisEstat('natures_producte')

  const [sp, setSp] = useSearchParams()
  const natureF = sp.get('nature') || ''
  const page = Math.max(1, parseInt(sp.get('page') || '1', 10))
  const vista = sp.get('vista') === 'inactius' ? 'inactius' : 'actius'
  const ordre = useMemo(() => {
    const raw = sp.get('ordering')
    if (!raw) return ORDRE_DEFECTE
    const desc = raw.startsWith('-')
    return { camp: desc ? raw.slice(1) : raw, dir: desc ? 'desc' : 'asc' }
  }, [sp])

  const setParams = useCallback((patch) => {
    setSp(prev => {
      const next = new URLSearchParams(prev)
      Object.entries(patch).forEach(([k, v]) => {
        if (v === undefined || v === null || v === '') next.delete(k)
        else next.set(k, v)
      })
      return next
    }, { replace: true })
  }, [setSp])

  const ordenar = useCallback((c) => {
    const dir = (ordre.camp === c && ordre.dir === 'asc') ? 'desc' : 'asc'
    setParams({ ordering: dir === 'desc' ? `-${c}` : c, page: undefined })
  }, [ordre, setParams])

  const load = useCallback(() => {
    setLoading(true); setError(false)
    commerce.products.list({
      active: vista === 'actius',
      ...(natureF ? { nature: natureF } : {}),
      ordering: ordre.dir === 'desc' ? `-${ordre.camp}` : ordre.camp,
      page, page_size: PAGE_SIZE,
    })
      .then(res => {
        const d = res.data
        setItems(Array.isArray(d) ? d : (d.results || []))
        setCount(d?.count ?? (Array.isArray(d) ? d.length : 0))
      })
      .catch(() => { setItems([]); setCount(0); setError(true) })
      .finally(() => setLoading(false))
  }, [vista, natureF, ordre, page])

  const carregaTotal = useCallback(() => {
    commerce.products.list({ page_size: 1 })
      .then(r => setTotal(r.data?.count ?? null)).catch(() => setTotal(null))
  }, [])

  useEffect(() => { carregaTotal() }, [carregaTotal])
  useEffect(() => { const id = setTimeout(load, 150); return () => clearTimeout(id) }, [load])
  // Les unitats són files d'una taula (no una enumeració de domini) i les necessita el modal.
  useEffect(() => {
    let alive = true
    commerce.units.list({ active: true, page_size: 500 })
      .then(res => res.data?.results ?? (Array.isArray(res.data) ? res.data : []))
      .then(us => { if (alive) setUnits(us) })
      .catch(() => { if (alive) setUnits([]) })
    return () => { alive = false }
  }, [])

  const pages = Math.max(1, Math.ceil(count / PAGE_SIZE))

  const remove = (prod, e) => {
    e.stopPropagation()
    if (!window.confirm(t('products.confirm_delete', { name: prod.code }))) return
    setSaving(true); setFeedback(null)
    commerce.products.remove(prod.id)
      .then(() => { load(); carregaTotal() })
      .then(() => setFeedback({ type: 'ok', text: t('products.deleted') }))
      .catch(err => setFeedback({ type: 'err', text: err?.response?.data?.detail || t('products.delete_protected') }))
      .finally(() => setSaving(false))
  }

  const resumPreu = (r) => {
    if (r.price_mode === 'TIME_BASED') return r.sale_rate != null ? `${r.sale_rate} €/min` : '—'
    return r.base_price != null ? `${r.base_price} €${r.unit_code ? ` / ${r.unit_code}` : ''}` : '—'
  }

  const cols = useMemo(() => [
    {
      // LA DADA REINA d'un mestre d'articles és el CODI: és el que viatja a la línia d'un
      // document i el que es tecleja. Mateix cas que el catàleg de POMs.
      key: 'code', label: t('products.col_code'), min: 120, max: 160, sort: 'code',
      estil: { fontWeight: 600 }, titol: r => r.code,
      render: r => r.code,
    },
    {
      key: 'name', label: t('products.col_name'), min: 200, max: 320, sort: 'name',
      titol: r => pickTranslation(r, 'name', lang),
      render: r => pickTranslation(r, 'name', lang),
    },
    {
      // La NATURA és una CLASSIFICACIÓ, no un semàfor: text pla, sense badge (§8e — la fase
      // dels models va prendre exactament aquesta decisió pel mateix motiu).
      key: 'nature', label: t('products.col_nature'), min: 130, max: 170, sort: 'nature',
      estil: { fontSize: 11, color: 'var(--text-soft)' },
      render: r => t(`products.nature_${r.nature}`, r.nature),
    },
    {
      key: 'price', label: t('products.col_price'), min: 120, max: 160, align: 'right',
      titol: r => resumPreu(r),
      render: r => resumPreu(r),
    },
    {
      key: 'active', label: t('products.col_active'), min: 86, max: 100, sort: 'active',
      render: r => (
        <Badge variant={r.active ? 'ok' : 'gray'}>
          {r.active ? t('products.active') : t('products.inactive')}
        </Badge>
      ),
    },
    {
      key: 'del', amplada: 36,
      render: r => (canEdit
        ? <BotoEsborrar onClick={(e) => remove(r, e)} title={t('products.delete')} disabled={saving} />
        : null),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [t, lang, canEdit, saving])

  const VISTES = [
    ['actius', t('products.view_active')],
    ['inactius', t('products.view_inactive')],
  ]

  return (
    <>
      <div style={forceBarra}>
        <PageMenu
          backTo="/" backTitle={t('products.back_title')}
          items={VISTES.map(([v, label]) => ({
            key: v, label, active: vista === v,
            onClick: () => setParams({ vista: v === 'actius' ? undefined : v, page: undefined }),
          }))}
        >
          {canEdit && <>
            <SepMenu />
            <BotoMenu onClick={() => setModal({ mode: 'create' })} icona="ti-plus"
              label={t('products.new')} />
          </>}
        </PageMenu>
      </div>

      <div style={{ minWidth: 0, maxWidth: '100%' }}>
        <FilaIdentitat>
          <Comptador valor={count} total={total ?? count} etiqueta={t('products.entity')} />
          <select value={natureF} onChange={e => setParams({ nature: e.target.value, page: undefined })}
            aria-label={t('products.col_nature')} style={camp}>
            <option value="">{t('products.filter_nature_all')}</option>
            {(natures || []).map(n => <option key={n} value={n}>{t(`products.nature_${n}`)}</option>)}
          </select>
        </FilaIdentitat>

        <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

        {loading ? <EstatBuit>{t('products.loading')}</EstatBuit>
          : error ? <EstatBuit>{t('products.error')}</EstatBuit>
            : items.length === 0 ? <EstatBuit>{t('products.empty')}</EstatBuit>
              : (
                <TaulaLlista cols={cols} files={items} clau={(r) => r.id}
                  ordre={ordre} onOrdenar={ordenar}
                  onObrir={(r) => navigate(`/comercial/productes/${r.id}`)} />
              )}

        <Paginacio page={page} pages={pages} onPage={(p) => setParams({ page: p })}
          labelPrev={t('products.prev')} labelNext={t('products.next')}
          info={t('products.page_info', { page, pages })} />
      </div>

      {modal && (
        <ProductModal mode={modal.mode} prod={modal.prod} units={units} t={t} saving={saving} setSaving={setSaving}
          onCancel={() => setModal(null)}
          onSaved={(msg) => {
            setModal(null)
            load(); carregaTotal()
            setFeedback({ type: 'ok', text: msg })
          }}
          onError={(text) => setFeedback({ type: 'err', text })} />
      )}
    </>
  )
}

// S'EXPORTA: la FITXA de l'article el reobre des del seu «Editar» (les accions de govern han
// baixat de la llista a la fitxa). Una sola definició del formulari d'un article — si visqués
// dues vegades, els dos llocs on es crea un producte divergirien sense que fallés res.
export function ProductModal({ mode, prod, units, t, saving, setSaving, onCancel, onSaved, onError }) {
  const isEdit = mode === 'edit'
  // Les DUES enumeracions del formulari, de l'endpoint. Cap llista escrita aquí: ni la de
  // natures ni la de modes de preu, que anava en dos `<option>` a pèl —la forma més silenciosa
  // de totes, perquè una llista que no sembla una llista no la troba cap cens.
  const { codis: natures } = useCodisEstat('natures_producte')
  const { codis: modesPreu } = useCodisEstat('modes_preu_producte')
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
      <Field label={t('products.col_code')}><input value={code} onChange={e => setCode(e.target.value)} style={{ ...camp, width: '100%' }} /></Field>
      <TranslatableField label={t('products.col_name')} field="name" value={name} onChange={setName}
        translations={translations} onTranslationsChange={setTranslations} />
      <TranslatableField label={t('products.description')} field="description" value={description} onChange={setDescription}
        translations={translations} onTranslationsChange={setTranslations} multiline />
      <Field label={t('products.col_nature')}>
        <select value={nature} onChange={e => setNature(e.target.value)} style={{ ...camp, width: '100%' }}>
          {(natures || []).map(n => <option key={n} value={n}>{t(`products.nature_${n}`)}</option>)}
        </select>
      </Field>
      <Field label={t('products.price_mode')}>
        <select value={priceMode} onChange={e => setPriceMode(e.target.value)} style={{ ...camp, width: '100%' }}>
          {(modesPreu || []).map(m => <option key={m} value={m}>{t(`products.mode_${m}`)}</option>)}
        </select>
      </Field>
      {priceMode === 'FIXED' ? (
        <Field label={t('products.base_price')}><input type="text" inputMode="decimal" value={basePrice} onChange={e => setBasePrice(e.target.value)} style={{ ...camp, width: '100%' }} /></Field>
      ) : (
        <Field label={t('products.sale_rate')}><input type="text" inputMode="decimal" value={saleRate} onChange={e => setSaleRate(e.target.value)} style={{ ...camp, width: '100%' }} /></Field>
      )}
      <Field label={t('products.markup_pct')}><input type="text" inputMode="decimal" value={markup} onChange={e => setMarkup(e.target.value)} style={{ ...camp, width: '100%' }} /></Field>
      <Field label={t('products.unit')}>
        <select value={unit} onChange={e => setUnit(e.target.value)} style={{ ...camp, width: '100%' }}>
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
      <label style={etiquetaCamp}>{label}</label>
      {children}
    </div>
  )
}

// §2 · l'etiqueta d'un camp és un LABEL: 10px majúscules, tracking .08em, pes 600.
const etiquetaCamp = {
  display: 'block', marginBottom: 6, fontFamily: MONO,
  fontSize: 'var(--fs-label)', lineHeight: '12px', letterSpacing: '.08em',
  textTransform: 'uppercase', color: 'var(--text-soft)', fontWeight: 600,
}
