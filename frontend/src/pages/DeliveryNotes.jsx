import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { commerce, customers as customersApi } from '../api/endpoints'
import Feedback from '../components/ui/Feedback'
import Modal from '../components/ui/Modal'
import PageMenu from '../components/ui/PageMenu'
import TaulaLlista from '../components/ui/TaulaLlista'
import { EstatBadge, useCodisEstat } from '../components/commercial/estats'
import {
  BotoMenu, Comptador, FilaIdentitat, EstatBuit, Paginacio, camp, forceBarra,
} from '../components/llista/ChromLlista'

// ALBARANS (`DeliveryNote`) — LLISTA CANÒNICA DE LA CASA (NORMA_LAYOUT §8b + §8e).
//
// L'albarà v2 es COMPON per model des de la safata d'albaranables d'un client («Compondre albarà»
// → obre o crea el DRAFT del client). Cicle DRAFT → ISSUED → INVOICED.
//
// ── DUES COSES QUE ES DIUEN EN VEU ALTA ──────────────────────────────────────────────────
//
// 1 · **EL MODAL DE COMPOSICIÓ ERA UN MODAL FET A MÀ**: `position: fixed` amb el seu propi
//    `rgba(0,0,0,0.35)` i el seu propi `zIndex: 50`, al costat de `ui/Modal`, que és el modal de
//    la casa. Dos modals amb dues capes diferents al mateix producte és com es guanya una
//    superposició que ningú ha decidit —i ara, a més, el §8b-quater fixa l'escala de capes del
//    sistema i una pantalla no se la pot inventar—. Passa a `ui/Modal`.
//
// 2 · **EL CICLE ES PINTA AMB L'ESCALA DE LA §8e** i no amb dos verds. Anava `DRAFT` daurat,
//    `ISSUED` verd i `INVOICED` verd-àlies: dos estats diferents del mateix color, i el daurat
//    fent de dada. Ara: DRAFT neutre (començat) · ISSUED taronja (en curs: emès i esperant) ·
//    INVOICED verd (acabat). v. `components/commercial/estats`.
const PAGE_SIZE = 25
const ORDRE_DEFECTE = { camp: 'created_at', dir: 'desc' }
const aOrdering = (o) => (o.dir === 'desc' ? `-${o.camp}` : o.camp)
const money = (v) => `${Number(v ?? 0).toFixed(2)} €`

// S'exporta: `CustomerDetail` en pinta la columna d'estat a la seva pestanya Comercial.
export function DNStatusBadge({ status, t }) {
  return <EstatBadge clau="estats_albara" codi={status}>{t(`deliverynotes.status_${status}`)}</EstatBadge>
}

export default function DeliveryNotes() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const [items, setItems] = useState([])
  const [count, setCount] = useState(0)
  const [total, setTotal] = useState(null)
  const [customers, setCustomers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [feedback, setFeedback] = useState(null)
  const [composeFor, setComposeFor] = useState('')   // customer id triat al modal de composició
  const [composing, setComposing] = useState(false)
  const [showCompose, setShowCompose] = useState(false)

  const { codis: estats } = useCodisEstat('estats_albara')

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
    commerce.deliveryNotes.list({
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
    commerce.deliveryNotes.list({ page_size: 1 }).then(r => setTotal(r.data?.count ?? null)).catch(() => setTotal(null))
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

  const compon = () => {
    if (!composeFor) return
    setComposing(true)
    commerce.deliveryNotes.draft({ customer: composeFor })
      .then(res => navigate(`/comercial/albarans/${res.data.id}`))
      .catch(e => {
        setComposing(false)
        setShowCompose(false)
        // El que fallava abans es confonia amb un error de CÀRREGA de la llista (`setError(true)`)
        // i la pantalla es quedava dient «no s'han pogut carregar els albarans» quan els havia
        // carregat perfectament: el que havia fallat era compondre'n un de nou.
        setFeedback({ type: 'err', text: e?.response?.data?.detail || t('deliverynotes.error') })
      })
  }

  const cols = useMemo(() => [
    {
      key: 'document_number', label: t('deliverynotes.col_number'), min: 130, max: 170, sort: 'document_number',
      estil: { fontWeight: 600 }, titol: r => r.document_number,
      render: r => r.document_number || '—',
    },
    {
      key: 'customer', label: t('deliverynotes.col_customer'), min: 180, max: 300, sort: 'customer',
      titol: r => r.customer_nom || undefined,
      render: r => r.customer_nom || '—',
    },
    {
      key: 'status', label: t('deliverynotes.col_status'), min: 100, max: 130, sort: 'status',
      render: r => <DNStatusBadge status={r.status} t={t} />,
    },
    {
      key: 'total', label: t('deliverynotes.col_total'), min: 100, max: 130, align: 'right', sort: 'total',
      render: r => money(r.total),
    },
    {
      key: 'date', label: t('deliverynotes.col_date'), min: 90, max: 110, sort: 'issued_at',
      estil: { fontSize: 11, color: 'var(--text-soft)' },
      render: r => (r.issued_at || r.created_at || '').slice(0, 10) || '—',
    },
  ], [t])

  return (
    <>
      <div style={forceBarra}>
        <PageMenu backTo="/" backTitle={t('deliverynotes.back_title')}>
          {/* §8e · l'acció primària PUJADA AL MENÚ deixa de ser botó i deixa de ser blava. */}
          <BotoMenu onClick={() => { setComposeFor(''); setShowCompose(true) }}
            icona="ti-layout-grid-add" label={t('deliverynotes.compose_action')} />
        </PageMenu>
      </div>

      <div style={{ minWidth: 0, maxWidth: '100%' }}>
        <FilaIdentitat>
          <Comptador valor={count} total={total ?? count} etiqueta={t('deliverynotes.entity')} />
          <select value={statusF} onChange={e => setParams({ status: e.target.value, page: undefined })}
            aria-label={t('deliverynotes.col_status')} style={camp}>
            <option value="">{t('deliverynotes.filter_status_all')}</option>
            {(estats || []).map(s => <option key={s} value={s}>{t(`deliverynotes.status_${s}`)}</option>)}
          </select>
          <select value={customerF} onChange={e => setParams({ customer: e.target.value, page: undefined })}
            aria-label={t('deliverynotes.col_customer')} style={{ ...camp, flex: 1, minWidth: 200 }}>
            <option value="">{t('deliverynotes.filter_customer_all')}</option>
            {customers.map(c => <option key={c.id} value={c.id}>{c.nom}</option>)}
          </select>
        </FilaIdentitat>

        <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

        {loading ? <EstatBuit>{t('deliverynotes.loading')}</EstatBuit>
          : error ? <EstatBuit>{t('deliverynotes.error')}</EstatBuit>
            : items.length === 0 ? <EstatBuit>{t('deliverynotes.empty')}</EstatBuit>
              : (
                <TaulaLlista cols={cols} files={items} clau={(r) => r.id}
                  ordre={ordre} onOrdenar={ordenar}
                  onObrir={(r) => navigate(`/comercial/albarans/${r.id}`)} />
              )}

        <Paginacio page={page} pages={pages} onPage={(p) => setParams({ page: p })}
          labelPrev={t('deliverynotes.prev')} labelNext={t('deliverynotes.next')}
          info={t('deliverynotes.page_info', { page, pages })} />
      </div>

      {/* El modal de la casa, no un `position: fixed` propi amb la seva pròpia capa. */}
      {showCompose && (
        <Modal title={t('deliverynotes.compose_title')} subtitle={t('deliverynotes.compose_hint')}
          cancelLabel={t('deliverynotes.issue_cancel')} confirmLabel={t('deliverynotes.compose_confirm')}
          confirmDisabled={composing || !composeFor}
          onCancel={() => !composing && setShowCompose(false)} onConfirm={compon}>
          <select value={composeFor} onChange={e => setComposeFor(e.target.value)}
            aria-label={t('deliverynotes.compose_pick_customer')}
            style={{ ...camp, width: '100%' }} disabled={composing}>
            <option value="">{t('deliverynotes.compose_pick_customer')}</option>
            {customers.map(c => <option key={c.id} value={c.id}>{c.nom}</option>)}
          </select>
        </Modal>
      )}
    </>
  )
}
