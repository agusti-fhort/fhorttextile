import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import { customers, tenantConfig } from '../api/endpoints'
import CustomerModal from '../components/CustomerModal'
import Feedback from '../components/ui/Feedback'
import Badge from '../components/ui/Badge'
import PageMenu from '../components/ui/PageMenu'
import TaulaLlista from '../components/ui/TaulaLlista'
import {
  BotoMenu, SepMenu, Comptador, FilaIdentitat, EstatBuit, BotoEsborrar, Paginacio,
  camp, forceBarra,
} from '../components/llista/ChromLlista'

// ARXIU DE CLIENTS (`Customer`) — LLISTA CANÒNICA DE LA CASA (NORMA_LAYOUT §8b + §8e).
//
// La §8e no descriu «la pantalla Models»: descriu TOTA llista del producte, i Clients hi surt
// nomenada. Aquesta pantalla és, doncs, GERMANA de `/models`: mateix menú de pantalla, mateix
// comptador «X/N» amb la cerca al costat, mateixa graella (`ui/TaulaLlista`) i mateix crom
// (`components/llista/ChromLlista`). El que canvia són les columnes, que són d'aquí.
//
// Backend: `CustomerViewSet` (CRUD); escriptura gated CONFIGURE; destroy → 409 si té models.
//
// ── TRES DECISIONS QUE ES DIUEN EN VEU ALTA ──────────────────────────────────────────────
//
// 1 · **LA DADA REINA ÉS EL NOM, NO EL CODI.** Abans el `codi` anava en pes 600 i el `nom` en
//    text pla. La §8e diu que la reina «porta el pes», i a un arxiu de clients el que es busca
//    és el nom (l'invers del catàleg de POMs, on la reina és el codi perquè allà el codi ÉS
//    l'entitat). El codi baixa a referència secundària, com la ref interna a Models. Per això
//    el `SelfBadge` també es muda: qualifica l'entitat, i l'entitat és el nom.
//
// 2 · **NO HI HA COLUMNA DE CHECKBOX, i és una absència deliberada.** La graella canònica en
//    porta perquè Models té accions de conjunt (`ActionsMenu`). Aquí no n'hi ha cap: activar,
//    desactivar i pujar el logo parlen d'UN client i han baixat a la seva fitxa (§5.6: el menú
//    d'accions és per als gestos ocasionals; i la fitxa és on la pantalla parla d'una entitat).
//    Posar-hi caselles que no habiliten res seria prometre una acció que no existeix, i
//    fabricar-la aquí com un bucle de PATCH al client seria pitjor: una fallada a mig bucle deixa
//    la meitat dels clients commutats i l'altra meitat no, sense que ningú pugui saber quins.
//
// 3 · **LES SET CAPÇALERES ORDENEN, I ES VA HAVER D'ARREGLAR EL BACKEND PERQUÈ HO FESSIN.**
//    `CustomerViewSet` declarava `filter_backends = [DjangoFilterBackend, SearchFilter]`, i
//    declarar-ne dos no n'AFEGEIX: els SUBSTITUEIX tots tres del `DEFAULT_FILTER_BACKENDS`, o
//    sigui que es carregava l'`OrderingFilter`. La versió anterior d'aquesta pantalla enviava
//    `ordering: 'codi'` a cada crida i **DRF el descartava sense error ni avís**: la llista
//    sortia en l'ordre del `Meta.ordering` del model i semblava que funcionés. Corregit per S1
//    (propietària del backend) amb els set camps —els tres de dada i els QUATRE COMPTADORS, que
//    són `annotate` i per tant ordenables sense cost—, i **mesurat contra l'API viva** abans de
//    posar-hi cap icona: `?ordering=-codi` inverteix, `?ordering=-orders_open` i
//    `?ordering=-delivery_notes_count` porten a dalt el client amb més comandes i més albarans.
const MONO = 'IBM Plex Mono, monospace'
const PAGE_SIZE = 25
// L'ordre per defecte de la casa per a un ARXIU: alfabètic pel codi. És el que el ViewSet
// declara com a `ordering`, i el que la icona de la capçalera ha de dir en obrir la pàgina.
const ORDRE_DEFECTE = { camp: 'codi', dir: 'asc' }
const aOrdering = (o) => (o.dir === 'desc' ? `-${o.camp}` : o.camp)

export default function Customers() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const me = useAuthStore(s => s.user)
  const canEdit = !!me?.capabilities?.includes('configure')

  const [items, setItems] = useState([])
  const [count, setCount] = useState(0)
  // §8e — «el comptador ÉS selecció, no KPI»: «12/84». El primer número és el resultat del
  // filtre; el segon, el CENS SENCER, que no es pot deduir d'una pàgina de 25 i per això es
  // demana un cop, a part, amb `page_size=1`.
  const [total, setTotal] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [feedback, setFeedback] = useState(null)
  const [saving, setSaving] = useState(false)
  const [modal, setModal] = useState(null)   // { mode:'create'|'edit', customer? }
  // Tipologia del tenant ('estudi'|'marca'|'enterprise'), de /api/v1/tenant-config/. `null` =
  // encara no carregada: mentre ho estigui NO es demana el llistat, perquè fer-ho amb un valor
  // endevinat pintaria la llista amb el filtre equivocat i després la corregiria (flash).
  const [tipologia, setTipologia] = useState(null)

  // URL = FONT DE VERITAT de l'estat de la llista (vista, cerca, pàgina): recarregar la conserva
  // i es pot enllaçar. Mateix contracte que `/models`.
  const [sp, setSp] = useSearchParams()
  const search = sp.get('search') || ''
  const page = Math.max(1, parseInt(sp.get('page') || '1', 10))
  const [searchInput, setSearchInput] = useState(search)

  // §8e · FILTRES RÀPIDS DE VISTA AL MENÚ: «els elements acabats NO es llisten per defecte
  // (embruten la cerca)». A Models el criteri d'«acabat» no existia i la vista no va endevinar
  // res; aquí SÍ que existeix i no s'ha d'endevinar: `Customer.active` és un camp de debò, el
  // backend ja el filtra (`filterset_fields = ['active']`) i la pantalla ja en deia «Actiu /
  // Inactiu». Un client inactiu és un client retirat — exactament l'eix que la §8e nomena.
  // ⚠️ CONDUCTA AFEGIDA: fins avui la llista els barrejava tots. Ara, per defecte, els inactius
  // no hi surten; hi són a un clic, a la píndola del costat. Va al report perquè Agus ho pugui vetar.
  const vista = sp.get('vista') === 'inactius' ? 'inactius' : 'actius'

  // L'ORDENACIÓ viu a la URL com la resta de l'estat de la llista: recarregar la conserva i es
  // pot enllaçar. Es guarda tal com el backend l'espera (`-camp`).
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

  // Tipologia del tenant: una sola lectura, en muntar. Si la crida falla es cau a 'estudi', que
  // és el comportament històric de la pàgina (amagar el self) — mai deixar la llista penjada.
  useEffect(() => {
    let alive = true
    tenantConfig.get()
      .then(r => { if (alive) setTipologia(r.data?.tipologia || 'estudi') })
      .catch(() => { if (alive) setTipologia('estudi') })
    return () => { alive = false }
  }, [])

  // exclude_self: en un ESTUDI el customer propi és fontaneria del sistema i la pàgina l'amaga;
  // en una MARCA el self és el seu propi patrimoni i s'ha de veure (amb el badge `(propi)`), que
  // si no la pàgina Clients d'una Marca pot sortir buida. Els altres consumidors del llistat
  // (selectors de client, filtre del Dashboard) no envien mai el filtre.
  const filtreBase = useMemo(() => ({
    active: vista === 'actius',
    ...(tipologia === 'marca' ? {} : { exclude_self: true }),
    ...(search ? { search } : {}),
  }), [vista, tipologia, search])

  // Clicar una capçalera: si ja mana, inverteix; si no, entra ASCENDENT — a un arxiu, el que
  // s'espera d'una columna nova és el començament de l'alfabet, no el final (l'invers de
  // `/models`, on la columna nova entra descendent perquè allà el que es busca és el més recent).
  const ordenar = useCallback((c) => {
    const dir = (ordre.camp === c && ordre.dir === 'asc') ? 'desc' : 'asc'
    setParams({ ordering: aOrdering({ camp: c, dir }), page: undefined })
  }, [ordre, setParams])

  const load = useCallback(() => {
    if (!tipologia) return
    setLoading(true); setError(false)
    customers.list({ ...filtreBase, ordering: aOrdering(ordre), page, page_size: PAGE_SIZE })
      .then(res => {
        const d = res.data
        setItems(Array.isArray(d) ? d : (d.results || []))
        setCount(d?.count ?? (Array.isArray(d) ? d.length : 0))
      })
      .catch(() => { setItems([]); setCount(0); setError(true) })
      .finally(() => setLoading(false))
  }, [filtreBase, ordre, page, tipologia])

  // El DENOMINADOR: el cens sencer del tenant, sense cap filtre de vista ni de cerca. Una sola
  // fila demanada — l'únic que se'n vol és el `count`.
  const carregaTotal = useCallback(() => {
    if (!tipologia) return
    customers.list({
      page_size: 1, ...(tipologia === 'marca' ? {} : { exclude_self: true }),
    }).then(r => setTotal(r.data?.count ?? null)).catch(() => setTotal(null))
  }, [tipologia])
  useEffect(() => { carregaTotal() }, [carregaTotal])

  // Cerca: mirall local per a la resposta de teclat, a la URL amb debounce.
  useEffect(() => { setSearchInput(search) }, [search])
  useEffect(() => {
    const id = setTimeout(() => { if (searchInput !== search) setParams({ search: searchInput, page: undefined }) }, 250)
    return () => clearTimeout(id)
  }, [searchInput])   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { const id = setTimeout(load, 200); return () => clearTimeout(id) }, [load])

  const pages = Math.max(1, Math.ceil(count / PAGE_SIZE))

  const remove = (c, e) => {
    e.stopPropagation()
    if (!window.confirm(t('clients.confirm_delete', { name: c.nom }))) return
    setSaving(true); setFeedback(null)
    customers.remove(c.id)
      .then(() => { load(); carregaTotal() })
      .then(() => setFeedback({ type: 'ok', text: t('clients.deleted') }))
      // PROTECT → 409 amb {detail} del backend; fallback i18n.
      .catch(err => setFeedback({ type: 'err', text: err?.response?.data?.detail || t('clients.delete_protected') }))
      .finally(() => setSaving(false))
  }

  // ── LES COLUMNES (§8e: amplades PER CONTINGUT, no iguals) ─────────────────────────────
  const cols = useMemo(() => [
    {
      key: 'codi', label: t('clients.col_codi'), min: 78, max: 100, sort: 'codi',
      estil: { fontSize: 11, color: 'var(--text-soft)' }, titol: (c) => c.codi,
      render: (c) => c.codi,
    },
    {
      // LA DADA REINA: porta el pes, i les marques de la fila hi van enganxades perquè és el
      // que qualifiquen (mateix patró que el `SetBadge` d'A5 dins de la cel·la del nom).
      key: 'nom', label: t('clients.col_nom'), min: 200, max: 340, sort: 'nom',
      estil: { fontWeight: 600 }, titol: (c) => c.nom,
      render: (c) => (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, maxWidth: '100%' }}>
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.nom || '—'}</span>
          {c.is_self && <SelfBadge t={t} />}
        </span>
      ),
    },
    {
      // §8e: l'ESTAT va amb badge de codi de colors. Actiu = verd; inactiu = neutre (no és cap
      // error, és un client retirat: pintar-lo en vermell diria que alguna cosa ha fallat).
      key: 'active', label: t('clients.col_active'), min: 86, max: 100, sort: 'active',
      render: (c) => (
        <Badge variant={c.active ? 'ok' : 'gray'}>
          {c.active ? t('clients.active') : t('clients.inactive')}
        </Badge>
      ),
    },
    {
      key: 'offers', label: t('clients.col_offers'), min: 90, max: 110, align: 'right', sort: 'quotes_sent',
      titolCap: t('clients.offers_hint'),
      render: (c) => (
        <span style={{ fontFamily: MONO }} title={t('clients.offers_hint')}>
          <Recompte v={c.quotes_sent} />
          <span style={{ color: 'var(--text-soft)' }}> / </span>
          <Recompte v={c.quotes_accepted} />
        </span>
      ),
    },
    {
      key: 'orders_open', label: t('clients.col_orders_open'), min: 100, max: 120, align: 'right', sort: 'orders_open',
      render: (c) => <Recompte v={c.orders_open} />,
    },
    {
      key: 'delivery_notes', label: t('clients.col_delivery_notes'), min: 80, max: 100, align: 'right', sort: 'delivery_notes_count',
      render: (c) => <Recompte v={c.delivery_notes_count} />,
    },
    {
      key: 'del', amplada: 36,
      // El client propi no s'esborra: el tenant es quedaria sense casa (el backend hi respon
      // 409 `self_customer_protected`). No oferir-ho és cortesia; el blindatge és allà.
      render: (c) => (canEdit && !c.is_self
        ? <BotoEsborrar onClick={(e) => remove(c, e)} title={t('clients.delete')} disabled={saving} />
        : null),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [t, canEdit, saving])

  const VISTES = [
    ['actius', t('clients.view_active')],
    ['inactius', t('clients.view_inactive')],
  ]

  return (
    <>
      {/* §8b · MENÚ DE PANTALLA — barra blanca de costat a costat amb filet a dalt i a baix.
          Ordre de la §8e: ← · filtres de VISTA · separador · accions. Les accions van a
          l'ESQUERRA (comportament de menú) i, en pujar-hi, PERDEN el blau: «el blau viu al
          contingut; el menú té el seu llenguatge». */}
      <div style={forceBarra}>
        <PageMenu
          backTo="/"
          backTitle={t('clients.back_title')}
          items={VISTES.map(([v, label]) => ({
            key: v, label, active: vista === v,
            onClick: () => setParams({ vista: v === 'actius' ? undefined : v, page: undefined }),
          }))}
        >
          {canEdit && <>
            <SepMenu />
            {/* Una sola via d'alta → botó simple, no desplegable: la §1 demana el desplegable
                quan una acció TÉ variants, i aquí no en té. */}
            <BotoMenu onClick={() => setModal({ mode: 'create' })} icona="ti-plus"
              label={t('clients.new')} />
          </>}
        </PageMenu>
      </div>

      <div style={{ minWidth: 0, maxWidth: '100%' }}>
        {/* §8e · EL COMPTADOR MANA I LA CERCA HI VA AL COSTAT, mateixa línia. El nom de l'entitat
            ja no és títol: és element en caption. I no hi va cap descripció a sota (esmena
            d'Agus del 08/08: la fila d'identitat és comptador + cerca i prou). */}
        <FilaIdentitat>
          <Comptador valor={count} total={total ?? count} etiqueta={t('clients.entity')} />
          <input value={searchInput} onChange={e => setSearchInput(e.target.value)}
            placeholder={t('clients.search_ph')} aria-label={t('clients.search_ph')}
            style={{ ...camp, flex: 1, minWidth: 220 }} />
        </FilaIdentitat>

        <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

        {loading ? <EstatBuit>{t('clients.loading')}</EstatBuit>
          : error ? <EstatBuit>{t('clients.error')}</EstatBuit>
            : items.length === 0 ? (
              <EstatBuit>{search ? t('clients.empty_filtered') : t('clients.empty')}</EstatBuit>
            ) : (
              <TaulaLlista
                cols={cols}
                files={items}
                clau={(c) => c.id}
                ordre={ordre}
                onOrdenar={ordenar}
                onObrir={(c) => navigate(`/clients/${c.id}`)}
              />
            )}

        <Paginacio page={page} pages={pages} onPage={(p) => setParams({ page: p })}
          labelPrev={t('clients.prev')} labelNext={t('clients.next')}
          info={t('clients.page_info', { page, pages })} />
      </div>

      {modal && (
        <CustomerModal mode={modal.mode} customer={modal.customer} t={t}
          onCancel={() => setModal(null)}
          onSaved={(_cust, msg) => {
            setModal(null)
            load(); carregaTotal()
            setFeedback({ type: 'ok', text: msg })
          }}
          onError={(text) => setFeedback({ type: 'err', text })} />
      )}
    </>
  )
}

// §8c · «KPI/recomptes NEUTRES: --text-main. El daurat NO pinta números.» El zero baixa a tinta
// secundària —segueix sent un valor, no un estat buit— i per això no va a `--text-faint`, que la
// §1 reserva al deshabilitat.
function Recompte({ v }) {
  const n = v ?? 0
  return <span style={{ color: n ? 'var(--text-main)' : 'var(--text-soft)' }}>{n}</span>
}

// Marca visual del client propi. Viu aquí i s'importa a la fitxa: una sola definició, perquè
// la llista i el detall no puguin divergir en el que és la identitat del tenant.
// §1 · el badge de la casa: fons suau + tinta + VORA FINA. `--gold-pale` està ELIMINAT del
// sistema i el daurat és marca, no dada: aquesta marca passa a la forma neutra de la casa
// (`--sel` + `--gold-border`), que és la que `ui/Badge` dona a la variant `gold`.
export function SelfBadge({ t }) {
  return (
    <Badge variant="gold" icon="ti-home" style={{ flex: 'none' }}>
      <span title={t('clients.self_badge_hint')}>{t('clients.self_badge')}</span>
    </Badge>
  )
}
