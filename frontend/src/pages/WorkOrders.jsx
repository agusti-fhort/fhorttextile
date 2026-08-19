import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { commerce, customers as customersApi } from '../api/endpoints'
import Feedback from '../components/ui/Feedback'
import PageMenu from '../components/ui/PageMenu'
import TaulaLlista from '../components/ui/TaulaLlista'
import { EstatBadge, ClassificacioBadge, useCodisEstat } from '../components/commercial/estats'
import {
  Comptador, FilaIdentitat, EstatBuit, Paginacio, camp, forceBarra,
} from '../components/llista/ChromLlista'

// ENCÀRRECS / ORDRES DE TREBALL (`WorkOrder`) — LLISTA CANÒNICA (NORMA_LAYOUT §8b + §8e).
//
// Contenidors d'execució: ORDER (encàrrec d'un model × línia de comanda) i COLLECTOR (col·lector
// mensual per client). **No es creen aquí** —ORDER neix del wizard B4b, COLLECTOR d'un hook
// lazy—, o sigui que aquesta pantalla és de CONSULTA i no té acció primària (§8c): el seu menú
// porta només la fletxa.
//
// **EL TIPUS DEIXA DE SER UN SEMÀFOR.** `kind` anava amb `ORDER` en VERD i `COLLECTOR` en TARONJA:
// un encàrrec d'un model no és «correcte» ni un col·lector mensual és un «avís». És una
// CLASSIFICACIÓ, i les classificacions van neutres (v. `components/commercial/estats`, decisió 3).
//
// Les tres llistes de codis (`KINDS`, `STATUSES`, i el mapa de tipus) se'n van a `/vocabulari/`
// (`tipus_encarrec`, `estats_encarrec`).
const PAGE_SIZE = 25
const ORDRE_DEFECTE = { camp: 'number', dir: 'desc' }
const aOrdering = (o) => (o.dir === 'desc' ? `-${o.camp}` : o.camp)

// S'exporten: la fitxa d'encàrrec i la pantalla d'orfes en pinten els mateixos badges.
export function WOStatusBadge({ status, t }) {
  return <EstatBadge clau="estats_encarrec" codi={status}>{t(`workorders.status_${status}`)}</EstatBadge>
}
export function WOKindBadge({ kind, t }) {
  return <ClassificacioBadge>{t(`workorders.kind_${kind}`)}</ClassificacioBadge>
}

export default function WorkOrders() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const [items, setItems] = useState([])
  const [count, setCount] = useState(0)
  const [total, setTotal] = useState(null)
  const [customers, setCustomers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [feedback, setFeedback] = useState(null)

  const { codis: estats } = useCodisEstat('estats_encarrec')
  const { codis: tipus } = useCodisEstat('tipus_encarrec')

  const [sp, setSp] = useSearchParams()
  const kindF = sp.get('kind') || ''
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
    commerce.workOrders.list({
      ...(kindF ? { kind: kindF } : {}),
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
  }, [kindF, statusF, customerF, ordre, page])

  const carregaTotal = useCallback(() => {
    commerce.workOrders.list({ page_size: 1 }).then(r => setTotal(r.data?.count ?? null)).catch(() => setTotal(null))
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
      key: 'number', label: t('workorders.col_number'), min: 130, max: 170, sort: 'number',
      estil: { fontWeight: 600 }, titol: r => r.number,
      render: r => r.number || '—',
    },
    {
      key: 'kind', label: t('workorders.col_kind'), min: 110, max: 140, sort: 'kind',
      render: r => <WOKindBadge kind={r.kind} t={t} />,
    },
    {
      key: 'customer', label: t('workorders.col_customer'), min: 170, max: 280, sort: 'customer',
      titol: r => r.customer_nom || undefined,
      render: r => r.customer_nom || '—',
    },
    {
      // UNA columna, DUES dades segons la mena d'encàrrec — i és a posta: un ORDER apunta a un
      // MODEL i un COLLECTOR a un PERÍODE, i mai tots dos. Dues columnes serien dues columnes
      // mig buides, que és el que la §8e evita amb les amplades per contingut.
      key: 'target', label: t('workorders.col_target'), min: 110, max: 150,
      estil: { fontSize: 11, color: 'var(--text-soft)' },
      titol: r => (r.kind === 'COLLECTOR' ? r.period : r.model_codi) || undefined,
      render: r => (r.kind === 'COLLECTOR' ? r.period : (r.model_codi || '—')),
    },
    {
      key: 'status', label: t('workorders.col_status'), min: 90, max: 120, sort: 'status',
      render: r => <WOStatusBadge status={r.status} t={t} />,
    },
    {
      key: 'n_tasks', label: t('workorders.col_tasks'), min: 80, max: 100, align: 'right',
      render: r => r.n_tasks ?? 0,
    },
  ], [t])

  return (
    <>
      <div style={forceBarra}>
        <PageMenu backTo="/" backTitle={t('workorders.back_title')} />
      </div>

      <div style={{ minWidth: 0, maxWidth: '100%' }}>
        <FilaIdentitat>
          <Comptador valor={count} total={total ?? count} etiqueta={t('workorders.entity')} />
          <select value={kindF} onChange={e => setParams({ kind: e.target.value, page: undefined })}
            aria-label={t('workorders.col_kind')} style={camp}>
            <option value="">{t('workorders.filter_kind_all')}</option>
            {(tipus || []).map(k => <option key={k} value={k}>{t(`workorders.kind_${k}`)}</option>)}
          </select>
          <select value={statusF} onChange={e => setParams({ status: e.target.value, page: undefined })}
            aria-label={t('workorders.col_status')} style={camp}>
            <option value="">{t('workorders.filter_status_all')}</option>
            {(estats || []).map(s => <option key={s} value={s}>{t(`workorders.status_${s}`)}</option>)}
          </select>
          <select value={customerF} onChange={e => setParams({ customer: e.target.value, page: undefined })}
            aria-label={t('workorders.col_customer')} style={{ ...camp, flex: 1, minWidth: 180 }}>
            <option value="">{t('workorders.filter_customer_all')}</option>
            {customers.map(c => <option key={c.id} value={c.id}>{c.nom}</option>)}
          </select>
        </FilaIdentitat>

        <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

        {loading ? <EstatBuit>{t('workorders.loading')}</EstatBuit>
          : error ? <EstatBuit>{t('workorders.error')}</EstatBuit>
            : items.length === 0 ? <EstatBuit>{t('workorders.empty')}</EstatBuit>
              : (
                <TaulaLlista cols={cols} files={items} clau={(r) => r.id}
                  ordre={ordre} onOrdenar={ordenar}
                  onObrir={(r) => navigate(`/comercial/encarrecs/${r.id}`)} />
              )}

        <Paginacio page={page} pages={pages} onPage={(p) => setParams({ page: p })}
          labelPrev={t('workorders.prev')} labelNext={t('workorders.next')}
          info={t('workorders.page_info', { page, pages })} />
      </div>
    </>
  )
}
