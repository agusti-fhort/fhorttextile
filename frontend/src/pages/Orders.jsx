import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { commerce, customers as customersApi } from '../api/endpoints'
import Feedback from '../components/ui/Feedback'
import PageMenu from '../components/ui/PageMenu'
import TaulaLlista from '../components/ui/TaulaLlista'
import { EstatBadge, useCodisEstat } from '../components/commercial/estats'
import {
  Comptador, FilaIdentitat, EstatBuit, Paginacio, camp, forceBarra,
} from '../components/llista/ChromLlista'

// COMANDES DE VENDA (`SalesOrder`) — LLISTA CANÒNICA DE LA CASA (NORMA_LAYOUT §8b + §8e).
//
// Les comandes NEIXEN de la conversió d'una oferta i el disseny és irreversible (decisió d'Agus,
// B3b): aquí només es consulten. Per això aquesta pantalla **no té acció primària** i el seu menú
// de pantalla porta NOMÉS la fletxa — que és exactament el que la §8b.2 preveu («sense seccions:
// només queda la fletxa; la barra no desapareix mai») i el que la §8c ratifica («les pantalles de
// CONSULTA poden tenir ZERO accions primàries: si no hi ha cosa que has vingut a fer, no hi ha
// blau»).
//
// Com a `/comercial/ofertes`: els filtres deixen de fer-se en memòria sobre `page_size: 500` —que
// partia la llista en silenci a partir de la 501— i passen al backend, i la llista d'estats ve de
// `/vocabulari/` (`estats_comanda`) i no d'una constant local.
const PAGE_SIZE = 25
const ORDRE_DEFECTE = { camp: 'created_at', dir: 'desc' }
const aOrdering = (o) => (o.dir === 'desc' ? `-${o.camp}` : o.camp)
const money = (v) => `${Number(v ?? 0).toFixed(2)} €`

// El badge d'una comanda. S'exporta perquè `CustomerDetail` en pinta la columna d'estat a la seva
// pestanya Comercial; el que se'n va és la LLISTA de codis, no el component.
export function OrderStatusBadge({ status, t }) {
  return <EstatBadge clau="estats_comanda" codi={status}>{t(`orders.status_${status}`)}</EstatBadge>
}

// % imputat = Σ qty_allocated / Σ quantity (control de cartera). Sense línies → 0%.
export function allocatedPct(order) {
  const lines = order?.lines || []
  const ordered = lines.reduce((s, l) => s + Number(l.quantity || 0), 0)
  if (ordered <= 0) return 0
  const allocated = lines.reduce((s, l) => s + Number(l.qty_allocated || 0), 0)
  return Math.round((allocated / ordered) * 100)
}

export default function Orders() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const [items, setItems] = useState([])
  const [count, setCount] = useState(0)
  const [total, setTotal] = useState(null)
  const [customers, setCustomers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [feedback, setFeedback] = useState(null)

  const { codis: estats } = useCodisEstat('estats_comanda')

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
    commerce.orders.list({
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
    commerce.orders.list({ page_size: 1 }).then(r => setTotal(r.data?.count ?? null)).catch(() => setTotal(null))
  }, [])

  useEffect(() => { carregaTotal() }, [carregaTotal])
  useEffect(() => { const id = setTimeout(load, 150); return () => clearTimeout(id) }, [load])
  useEffect(() => {
    let alive = true
    customersApi.list({ active: true, page_size: 500 }).then(rows)
      .then(cs => { if (alive) setCustomers(cs) })
      .catch(() => { if (alive) setCustomers([]) })
    return () => { alive = false }
  }, [])

  const pages = Math.max(1, Math.ceil(count / PAGE_SIZE))

  const cols = useMemo(() => [
    {
      key: 'document_number', label: t('orders.col_number'), min: 130, max: 170, sort: 'document_number',
      estil: { fontWeight: 600 }, titol: r => r.document_number,
      render: r => r.document_number || '—',
    },
    {
      key: 'customer', label: t('orders.col_customer'), min: 180, max: 300, sort: 'customer',
      titol: r => r.customer_nom || undefined,
      render: r => r.customer_nom || '—',
    },
    {
      key: 'status', label: t('orders.col_status'), min: 100, max: 130, sort: 'status',
      render: r => <OrderStatusBadge status={r.status} t={t} />,
    },
    {
      // §8c · «KPI/recomptes NEUTRES: --text-main. El daurat NO pinta números.» El % imputat és
      // un recompte de cartera, no un semàfor: no porta color.
      key: 'allocated', label: t('orders.col_allocated'), min: 90, max: 110, align: 'right',
      render: r => `${allocatedPct(r)}%`,
    },
    {
      key: 'total', label: t('orders.col_total'), min: 100, max: 130, align: 'right', sort: 'total',
      render: r => money(r.total),
    },
    {
      key: 'created_at', label: t('orders.col_created'), min: 90, max: 110, sort: 'created_at',
      estil: { fontSize: 11, color: 'var(--text-soft)' },
      render: r => (r.created_at || '').slice(0, 10) || '—',
    },
  ], [t])

  return (
    <>
      {/* §8b.2 · la barra no desapareix mai; sense seccions ni accions, queda només la fletxa. */}
      <div style={forceBarra}>
        <PageMenu backTo="/" backTitle={t('orders.back_title')} />
      </div>

      <div style={{ minWidth: 0, maxWidth: '100%' }}>
        <FilaIdentitat>
          <Comptador valor={count} total={total ?? count} etiqueta={t('orders.entity')} />
          <select value={statusF} onChange={e => setParams({ status: e.target.value, page: undefined })}
            aria-label={t('orders.col_status')} style={camp}>
            <option value="">{t('orders.filter_status_all')}</option>
            {(estats || []).map(s => <option key={s} value={s}>{t(`orders.status_${s}`)}</option>)}
          </select>
          <select value={customerF} onChange={e => setParams({ customer: e.target.value, page: undefined })}
            aria-label={t('orders.col_customer')} style={{ ...camp, flex: 1, minWidth: 200 }}>
            <option value="">{t('orders.filter_customer_all')}</option>
            {customers.map(c => <option key={c.id} value={c.id}>{c.nom}</option>)}
          </select>
        </FilaIdentitat>

        <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

        {loading ? <EstatBuit>{t('orders.loading')}</EstatBuit>
          : error ? <EstatBuit>{t('orders.error')}</EstatBuit>
            : items.length === 0 ? <EstatBuit>{t('orders.empty')}</EstatBuit>
              : (
                <TaulaLlista cols={cols} files={items} clau={(r) => r.id}
                  ordre={ordre} onOrdenar={ordenar}
                  onObrir={(r) => navigate(`/comercial/comandes/${r.id}`)} />
              )}

        <Paginacio page={page} pages={pages} onPage={(p) => setParams({ page: p })}
          labelPrev={t('orders.prev')} labelNext={t('orders.next')}
          info={t('orders.page_info', { page, pages })} />
      </div>
    </>
  )
}
