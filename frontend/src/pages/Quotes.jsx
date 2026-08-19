import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams } from 'react-router-dom'
import useAuthStore from '../store/auth'
import { commerce, customers as customersApi } from '../api/endpoints'
import Feedback from '../components/ui/Feedback'
import Modal from '../components/ui/Modal'
import PageMenu from '../components/ui/PageMenu'
import TaulaLlista from '../components/ui/TaulaLlista'
import { EstatBadge, useCodisEstat } from '../components/commercial/estats'
import {
  BotoMenu, Comptador, FilaIdentitat, EstatBuit, BotoEsborrar, Paginacio,
  camp, forceBarra,
} from '../components/llista/ChromLlista'

// OFERTES (`Quote`) — LLISTA CANONICA DE LA CASA (NORMA_LAYOUT §8b + §8e).
//
// Germana de /models, /clients i /proveidors. Backend: `QuoteViewSet`; escriptura gated
// CONFIGURE; el gate de tier del modul arriba a B5.
//
// ── QUATRE COSES QUE ES DIUEN EN VEU ALTA ────────────────────────────────────────────────
//
// 1 · **ELS FILTRES DEIXEN DE SER DEL CLIENT.** La pantalla demanava `page_size: 500` i despres
//    filtrava en memoria (`items.filter(...)`). Amb 500 ofertes la llista es partia en silenci —
//    la 501 no existia per a ningu— i el comptador no podia dir mai la veritat. Ara filtra i
//    pagina el BACKEND (`status`, `customer`, `page`), i el comptador es «X/N» de debo: X del
//    filtre i N el cens sencer, demanat a part amb `page_size=1`.
//
// 2 · **LA LLISTA D'ESTATS VE DE `/vocabulari/`** (`estats_oferta`), no d'una constant local.
//    N'hi havia una copia aqui (`STATUSES`) i una altra a `OrderDetail`, i el badge el
//    importaven `CustomerDetail` d'aquesta pagina —una fitxa depenent d'una llista—. Tot aixo
//    viu ara a `components/commercial/estats`.
//
// 3 · **LA DADA REINA ES EL NUMERO DE DOCUMENT.** A un document, el numero ES l'entitat (com el
//    codi al cataleg de POMs, i a l'inversa d'un client, on mana el nom).
//
// 4 · 🚩 **EXPIRED es pinta com REJECTED**, i es una decisio de domini que va al report: les dues
//    volen dir que l'oferta s'ha acabat sense convertir-se en comanda. v. `commercial/estats`.
const MONO = 'IBM Plex Mono, monospace'
const PAGE_SIZE = 25
const ORDRE_DEFECTE = { camp: 'created_at', dir: 'desc' }
const aOrdering = (o) => (o.dir === 'desc' ? `-${o.camp}` : o.camp)

const money = (v) => `${Number(v ?? 0).toFixed(2)} €`

// El badge d'una oferta. Viu aqui —i s'exporta— perque `CustomerDetail` en pinta la columna
// d'estat a la seva pestanya Comercial; el que se'n va es la LLISTA de codis, no el component.
export function StatusBadge({ status, t }) {
  return <EstatBadge clau="estats_oferta" codi={status}>{t(`quotes.status_${status}`)}</EstatBadge>
}

export default function Quotes() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const me = useAuthStore(s => s.user)
  const canEdit = !!me?.capabilities?.includes('configure')

  const [items, setItems] = useState([])
  const [count, setCount] = useState(0)
  const [total, setTotal] = useState(null)
  const [customers, setCustomers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [feedback, setFeedback] = useState(null)
  const [saving, setSaving] = useState(false)
  const [creating, setCreating] = useState(false)

  // ⚠️ CAP LLISTA D'ESTATS AQUI. `codis` és `null` mentre no se sap i el select NO ofereix res:
  // «Totes» segueix funcionant, perquè no filtrar no demana saber-se l'enumeració.
  const { codis: estats } = useCodisEstat('estats_oferta')

  // URL = font de veritat de l'estat de la llista.
  const [sp, setSp] = useSearchParams()
  const statusF = sp.get('status') || ''
  const customerF = sp.get('customer') || ''
  const page = Math.max(1, parseInt(sp.get('page') || '1', 10))
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
    const dir = (ordre.camp === c && ordre.dir === 'desc') ? 'asc' : 'desc'
    setParams({ ordering: aOrdering({ camp: c, dir }), page: undefined })
  }, [ordre, setParams])

  const rows = (res) => res.data?.results ?? (Array.isArray(res.data) ? res.data : [])

  const load = useCallback(() => {
    setLoading(true); setError(false)
    commerce.quotes.list({
      ...(statusF ? { status: statusF } : {}),
      ...(customerF ? { customer: customerF } : {}),
      ordering: aOrdering(ordre), page, page_size: PAGE_SIZE,
    })
      .then(res => {
        const d = res.data
        setItems(Array.isArray(d) ? d : (d.results || []))
        setCount(d?.count ?? (Array.isArray(d) ? d.length : 0))
      })
      .catch(() => { setItems([]); setCount(0); setError(true) })
      .finally(() => setLoading(false))
  }, [statusF, customerF, ordre, page])

  const carregaTotal = useCallback(() => {
    commerce.quotes.list({ page_size: 1 }).then(r => setTotal(r.data?.count ?? null)).catch(() => setTotal(null))
  }, [])

  useEffect(() => { carregaTotal() }, [carregaTotal])
  useEffect(() => { const id = setTimeout(load, 150); return () => clearTimeout(id) }, [load])

  // Els clients del select de filtre: una sola lectura. No és una llista de domini —són files
  // d'una taula— i per tant no passa pel vocabulari.
  useEffect(() => {
    let alive = true
    customersApi.list({ active: true, page_size: 500 }).then(rows)
      .then(cs => { if (alive) setCustomers(cs) })
      .catch(() => { if (alive) setCustomers([]) })
    return () => { alive = false }
  }, [])

  const pages = Math.max(1, Math.ceil(count / PAGE_SIZE))

  const remove = (q, e) => {
    e.stopPropagation()
    if (!window.confirm(t('quotes.confirm_delete', { number: q.document_number }))) return
    setSaving(true); setFeedback(null)
    commerce.quotes.remove(q.id)
      .then(() => { load(); carregaTotal() })
      .then(() => setFeedback({ type: 'ok', text: t('quotes.deleted') }))
      .catch(err => setFeedback({ type: 'err', text: err?.response?.data?.detail || t('quotes.error') }))
      .finally(() => setSaving(false))
  }

  const cols = useMemo(() => [
    {
      // LA DADA REINA: a un document, el número ÉS l'entitat.
      key: 'document_number', label: t('quotes.col_number'), min: 130, max: 170, sort: 'document_number',
      estil: { fontWeight: 600 }, titol: r => r.document_number,
      render: r => r.document_number || '—',
    },
    {
      key: 'customer', label: t('quotes.col_customer'), min: 180, max: 300, sort: 'customer',
      titol: r => r.customer_nom || undefined,
      render: r => r.customer_nom || '—',
    },
    {
      key: 'status', label: t('quotes.col_status'), min: 100, max: 130, sort: 'status',
      render: r => <StatusBadge status={r.status} t={t} />,
    },
    {
      key: 'total', label: t('quotes.col_total'), min: 100, max: 130, align: 'right', sort: 'total',
      render: r => money(r.total),
    },
    {
      key: 'created_at', label: t('quotes.col_created'), min: 90, max: 110, sort: 'created_at',
      estil: { fontSize: 11, color: 'var(--text-soft)' },
      render: r => (r.created_at || '').slice(0, 10) || '—',
    },
    {
      key: 'del', amplada: 36,
      render: r => (canEdit
        ? <BotoEsborrar onClick={(e) => remove(r, e)} title={t('quotes.delete')} disabled={saving} />
        : null),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [t, canEdit, saving])

  return (
    <>
      <div style={forceBarra}>
        {/* §8e · l'acció primària PUJADA AL MENÚ deixa de ser blava. Aquí no hi ha filtres de
            VISTA: l'eix «en curs / acabat» d'una oferta és el seu ESTAT, i l'estat ja té el seu
            select a la fila d'identitat. Partir-lo en píndoles hauria estat dir dues vegades el
            mateix filtre amb dos controls diferents. */}
        <PageMenu backTo="/" backTitle={t('quotes.back_title')}>
          {canEdit && (
            <BotoMenu onClick={() => setCreating(true)} icona="ti-plus" label={t('quotes.new')} />
          )}
        </PageMenu>
      </div>

      <div style={{ minWidth: 0, maxWidth: '100%' }}>
        <FilaIdentitat>
          <Comptador valor={count} total={total ?? count} etiqueta={t('quotes.entity')} />
          <select value={statusF} onChange={e => setParams({ status: e.target.value, page: undefined })}
            aria-label={t('quotes.col_status')} style={camp}>
            <option value="">{t('quotes.filter_status_all')}</option>
            {(estats || []).map(s => <option key={s} value={s}>{t(`quotes.status_${s}`)}</option>)}
          </select>
          <select value={customerF} onChange={e => setParams({ customer: e.target.value, page: undefined })}
            aria-label={t('quotes.col_customer')} style={{ ...camp, flex: 1, minWidth: 200 }}>
            <option value="">{t('quotes.filter_customer_all')}</option>
            {customers.map(c => <option key={c.id} value={c.id}>{c.nom}</option>)}
          </select>
        </FilaIdentitat>

        <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

        {loading ? <EstatBuit>{t('quotes.loading')}</EstatBuit>
          : error ? <EstatBuit>{t('quotes.error')}</EstatBuit>
            : items.length === 0 ? <EstatBuit>{t('quotes.empty')}</EstatBuit>
              : (
                <TaulaLlista cols={cols} files={items} clau={(r) => r.id}
                  ordre={ordre} onOrdenar={ordenar}
                  onObrir={(r) => navigate(`/comercial/ofertes/${r.id}`)} />
              )}

        <Paginacio page={page} pages={pages} onPage={(p) => setParams({ page: p })}
          labelPrev={t('quotes.prev')} labelNext={t('quotes.next')}
          info={t('quotes.page_info', { page, pages })} />
      </div>

      {creating && (
        <NewQuoteModal customers={customers} t={t}
          onCancel={() => setCreating(false)}
          onCreated={(id) => navigate(`/comercial/ofertes/${id}`)}
          onError={(text) => setFeedback({ type: 'err', text })} />
      )}
    </>
  )
}

function NewQuoteModal({ customers, t, onCancel, onCreated, onError }) {
  const [customer, setCustomer] = useState('')
  const [validUntil, setValidUntil] = useState('')
  const [busy, setBusy] = useState(false)
  const invalid = !customer

  const submit = () => {
    if (invalid) { onError(t('quotes.required')); return }
    setBusy(true)
    commerce.quotes.create({ customer, valid_until: validUntil || null })
      .then(res => onCreated(res.data.id))
      .catch(e => onError(e?.response?.data?.detail || t('quotes.error')))
      .finally(() => setBusy(false))
  }

  return (
    <Modal title={t('quotes.new_title')} cancelLabel={t('quotes.cancel')} confirmLabel={t('quotes.create')}
      onCancel={onCancel} onConfirm={submit} confirmDisabled={busy || invalid}>
      <div style={{ marginBottom: 14 }}>
        <label style={etiquetaCamp}>{t('quotes.customer')}</label>
        <select value={customer} onChange={e => setCustomer(e.target.value)} style={{ ...camp, width: '100%' }}>
          <option value="">{t('quotes.select_customer')}</option>
          {customers.map(c => <option key={c.id} value={c.id}>{c.nom}</option>)}
        </select>
      </div>
      <div style={{ marginBottom: 4 }}>
        <label style={etiquetaCamp}>{t('quotes.valid_until')}</label>
        <input type="date" value={validUntil} onChange={e => setValidUntil(e.target.value)} style={{ ...camp, width: '100%' }} />
      </div>
    </Modal>
  )
}

// §2 · l'etiqueta d'un camp és un LABEL: 10px majúscules, tracking .08em, pes 600. Anava a mida
// de COS (12) i pes normal, o sigui que cridava tant com el valor que etiqueta.
const etiquetaCamp = {
  display: 'block', marginBottom: 6, fontFamily: MONO,
  fontSize: 'var(--fs-label)', lineHeight: '12px', letterSpacing: '.08em',
  textTransform: 'uppercase', color: 'var(--text-soft)', fontWeight: 600,
}
