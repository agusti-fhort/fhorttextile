import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { commerce, customers as customersApi } from '../api/endpoints'
import Feedback from '../components/ui/Feedback'
import PageMenu from '../components/ui/PageMenu'
import TaulaLlista from '../components/ui/TaulaLlista'
import SubTabs from '../components/ui/SubTabs'
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
//
// LOT 09/09 · LA LLEI DEL NOM ARRIBA AQUÍ. La llista identificava l'encàrrec pel CODI del model
// dins d'una columna «Model/Període» que barrejava dues dades («una columna, dues dades»). Ara el
// NOM del model és la segona columna i la COL·LECCIÓ la tercera, i el codi baixa a secundari sota
// el nom. La columna barrejada se'n va: el període d'un col·lector ocupa la mateixa cel·la del
// nom perquè és el que ANOMENA aquell encàrrec —un col·lector no té model i mai en tindrà—, i
// això no és barrejar dues dades sinó dir el nom de cada mena amb la seva paraula.
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
  // Selecció múltiple. Viu en memòria i NO a la URL: és una intenció de treball d'aquesta
  // estona, no un estat compartible per enllaç. Es buida en canviar de safata o de cerca,
  // perquè arrossegar una tria a través d'un conjunt que ja no es veu és com es tanca el que
  // no es volia tancar.
  const [triats, setTriats] = useState(() => new Set())

  const { codis: estats } = useCodisEstat('estats_encarrec')
  const { codis: tipus } = useCodisEstat('tipus_encarrec')

  const [sp, setSp] = useSearchParams()
  const kindF = sp.get('kind') || ''
  const statusF = sp.get('status') || ''
  const customerF = sp.get('customer') || ''
  // La cerca SÍ que va a la URL: un resultat de cerca es comparteix i es torna a obrir.
  const searchF = sp.get('search') || ''
  const page = Math.max(1, parseInt(sp.get('page') || '1', 10))
  const ordre = useMemo(() => {
    const raw = sp.get('ordering')
    if (!raw) return ORDRE_DEFECTE
    const desc = raw.startsWith('-')
    return { camp: desc ? raw.slice(1) : raw, dir: desc ? 'desc' : 'asc' }
  }, [sp])

  const setParams = useCallback((patch) => {
    // 🔑 QUALSEVOL canvi de consulta BUIDA LA TRIA —safata, cerca, filtre i també pàgina—, i es
    // fa AQUÍ i no en un efecte: la tria d'abans ja no és a la pantalla, i arrossegar-la a
    // través d'un conjunt que l'usuari no té davant és com es tanca el que no es volia tancar.
    // El gest ho ha de dir, no un efecte que ho endreci després.
    setTriats(new Set())
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
      ...(searchF ? { search: searchF } : {}),
      ordering: aOrdering(ordre), page, page_size: PAGE_SIZE,
    })
      .then(res => {
        const d = res.data
        setItems(Array.isArray(d) ? d : (d.results || []))
        setCount(d?.count ?? (Array.isArray(d) ? d.length : 0))
      })
      .catch(() => { setItems([]); setCount(0); setError(true) })
      .finally(() => setLoading(false))
  }, [kindF, statusF, customerF, searchF, ordre, page])

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

  const commuta = useCallback((id) => setTriats(prev => {
    const next = new Set(prev)
    if (next.has(id)) next.delete(id); else next.add(id)
    return next
  }), [])
  // La casella de la capçalera opera NOMÉS sobre la pàgina visible, que és el que l'usuari té
  // davant: «totes» no pot voler dir files que no ha vist mai.
  const totsVisibles = items.length > 0 && items.every(r => triats.has(r.id))
  const commutaTots = useCallback(() => setTriats(prev => {
    const next = new Set(prev)
    if (items.every(r => next.has(r.id))) items.forEach(r => next.delete(r.id))
    else items.forEach(r => next.add(r.id))
    return next
  }), [items])

  // ELS TABS SURTEN DEL VOCABULARI, no d'una llista escrita aquí: `estats_encarrec` és la
  // mateixa font que alimentava el desplegable que substitueixen, i els seus rètols són els
  // `workorders.status_*` que la casa ja té traduïts. L'única cosa que s'hi afegeix és la
  // safata «totes», que no és cap estat del domini sinó l'absència de filtre.
  const tabs = useMemo(() => [
    ...(estats || []).map(codi => ({ key: codi, label: `workorders.status_${codi}` })),
    { key: '', label: 'workorders.tab_all' },
  ], [estats])

  const pages = Math.max(1, Math.ceil(count / PAGE_SIZE))

  const cols = useMemo(() => [
    {
      // CONTROL, no dada: va abans del número i no ordena. El `stopPropagation` és obligatori
      // —`TaulaLlista` posa l'`onClick` d'obrir a tot el `<tr>`— o triar una fila navegaria.
      key: 'tria', label: '', min: 38, max: 38, align: 'center',
      // `renderCap` ja el preveu la graella canònica per a aquesta columna exacta (v. el
      // comentari de `Capcalera`): la pantalla hi posa el control de conjunt i el `th` conserva
      // la caixa de la norma.
      renderCap: () => (
        <input type="checkbox" checked={totsVisibles} onChange={commutaTots}
          aria-label={t('workorders.select_all')} style={{ cursor: 'pointer' }} />
      ),
      render: r => (
        <input type="checkbox" checked={triats.has(r.id)}
          onClick={e => e.stopPropagation()}
          onChange={() => commuta(r.id)}
          aria-label={t('workorders.select_one', { n: r.number })}
          style={{ cursor: 'pointer' }} />
      ),
    },
    {
      key: 'number', label: t('workorders.col_number'), min: 130, max: 170, sort: 'number',
      estil: { fontWeight: 600 }, titol: r => r.number,
      render: r => r.number || '—',
    },
    {
      // COLUMNA 2 · EL NOM. La llei del nom: l'identificador més visible és el nom del model i
      // el codi va a sota, en secundari. Un COLLECTOR no té model i mai en tindrà (ho blinda la
      // constraint `collector_no_model_no_orderline`): el seu període ocupa aquesta cel·la
      // perquè és el que l'anomena. `nowrap` de la cel·la fora, que aquí hi ha dues línies.
      key: 'nom', label: t('workorders.col_nom'), min: 220, max: 380, sort: 'model__nom_prenda',
      estil: { whiteSpace: 'normal' },
      titol: r => (r.kind === 'COLLECTOR' ? r.period : r.model_nom) || undefined,
      render: r => (r.kind === 'COLLECTOR' ? (
        <span style={{ color: 'var(--text-main)' }}>
          {t('workorders.collector_period', { period: r.period || '—' })}
        </span>
      ) : (
        <span style={{ display: 'block', minWidth: 0 }}>
          <span style={{ display: 'block', color: 'var(--text-main)', overflow: 'hidden',
                         textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {r.model_nom || t('workorders.no_name')}
          </span>
          {r.model_codi && (
            <span style={{ display: 'block', fontSize: 'var(--fs-caption)',
                           color: 'var(--text-soft)' }}>{r.model_codi}</span>
          )}
        </span>
      )),
    },
    {
      // COLUMNA 3 · LA COL·LECCIÓ. Buida en un col·lector i en un model que no en declara: es
      // pinta el guió de la casa i no una cadena inventada.
      key: 'collection', label: t('workorders.col_collection'), min: 130, max: 200,
      estil: { color: 'var(--text-soft)' },
      titol: r => r.model_collection || undefined,
      render: r => r.model_collection || '—',
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
      key: 'status', label: t('workorders.col_status'), min: 90, max: 120, sort: 'status',
      render: r => <WOStatusBadge status={r.status} t={t} />,
    },
    {
      key: 'n_tasks', label: t('workorders.col_tasks'), min: 80, max: 100, align: 'right',
      render: r => r.n_tasks ?? 0,
    },
  ], [t, triats, totsVisibles, commuta, commutaTots])

  return (
    <>
      <div style={forceBarra}>
        <PageMenu backTo="/" backTitle={t('workorders.back_title')} />
      </div>

      <div style={{ minWidth: 0, maxWidth: '100%' }}>
        {/* OBERTS · TANCATS · TOTS. El desplegable d'estat se'n va: obert i tancat no són un
            filtre entre molts, són les dues safates on viu la feina, i amagar-les dins d'un
            `select` les feia costar dos clics i una lectura. La resta de filtres (mena, client)
            es queden com estaven —aquells sí que són filtres. Els codis segueixen sortint de
            `/vocabulari/`; aquí només es fixa quin ordre tenen a la barra. */}
        <SubTabs items={tabs} actiu={statusF}
                 onTria={(k) => setParams({ status: k, page: undefined })} />

        <FilaIdentitat>
          <Comptador valor={count} total={total ?? count} etiqueta={t('workorders.entity')} />
          {/* Cerca per NOM del model, codi i client (search_fields del ViewSet). Va a la URL
              perquè un resultat de cerca es comparteix; el `load` ja porta 150 ms de coixí, o
              sigui que escriure no dispara una crida per lletra. */}
          <span style={{ position: 'relative', flex: 1, minWidth: 200 }}>
            <i className="ti ti-search" aria-hidden="true"
               style={{ position: 'absolute', left: 8, top: '50%', transform: 'translateY(-50%)',
                        fontSize: 14, color: 'var(--text-soft)', pointerEvents: 'none' }} />
            <input type="search" value={searchF}
              onChange={e => setParams({ search: e.target.value, page: undefined })}
              placeholder={t('workorders.search_placeholder')}
              aria-label={t('workorders.search_placeholder')}
              style={{ ...camp, width: '100%', paddingLeft: 28 }} />
          </span>
          <select value={kindF} onChange={e => setParams({ kind: e.target.value, page: undefined })}
            aria-label={t('workorders.col_kind')} style={camp}>
            <option value="">{t('workorders.filter_kind_all')}</option>
            {(tipus || []).map(k => <option key={k} value={k}>{t(`workorders.kind_${k}`)}</option>)}
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
                  triada={(r) => triats.has(r.id)}
                  onObrir={(r) => navigate(`/comercial/encarrecs/${r.id}`)} />
              )}

        <Paginacio page={page} pages={pages} onPage={(p) => setParams({ page: p })}
          labelPrev={t('workorders.prev')} labelNext={t('workorders.next')}
          info={t('workorders.page_info', { page, pages })} />
      </div>
    </>
  )
}
