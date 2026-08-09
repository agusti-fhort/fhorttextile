import { useState, useEffect, useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import { suppliers } from '../api/endpoints'
import Feedback from '../components/ui/Feedback'
import Modal from '../components/ui/Modal'
import Badge from '../components/ui/Badge'
import PageMenu from '../components/ui/PageMenu'
import TaulaLlista from '../components/ui/TaulaLlista'
import {
  BotoMenu, SepMenu, Comptador, FilaIdentitat, EstatBuit, BotoEsborrar, Paginacio,
  camp, buit, forceBarra,
} from '../components/llista/ChromLlista'

// CATALEG DE PROVEIDORS (tallers/fabrica) — LLISTA CANONICA DE LA CASA (NORMA_LAYOUT §8b + §8e).
//
// Germana de `/clients` i de `/models`: mateix menu de pantalla, mateixa graella
// (`ui/TaulaLlista`), mateix crom (`components/llista/ChromLlista`). El que canvia son les
// columnes. Backend: `SupplierViewSet`; escriptura gated SCHEDULE_FITTINGS (no CONFIGURE, com a
// Clients: qui contracta una confeccio es qui planifica); destroy → 409 si te confeccions.
//
// ── TRES COSES QUE ES DIUEN EN VEU ALTA ──────────────────────────────────────────────────
//
// 1 · 🛑 **NO HI HA CERCADOR, i no es un oblit: es que no funcionaria.** `SupplierViewSet` no
//    declara `search_fields`, i el `SearchFilter` de DRF sense `search_fields` deixa passar el
//    queryset SENCER. Mesurat contra l'API viva: `?search=zzzz` torna `count: 1`, exactament el
//    mateix que sense cap filtre. Un camp de cerca aqui seria un control que sembla que fa una
//    cosa i no en fa cap — el germa exacte de l'`ordering` que /clients demanava i que DRF es
//    menjava. BLOQUEJAT-PER-S1: cal `search_fields = ['name', 'nif', 'ciutat']` al ViewSet.
//
// 2 · **LES CAPCALERES ORDENEN, pero no s'ha pogut VEURE.** El ViewSet no sobreescriu
//    `filter_backends`, o sigui que hereta l'`OrderingFilter` del `DEFAULT_FILTER_BACKENDS`, i
//    `name`/`type`/`active` son camps del serializer (comprovat) → DRF els accepta com a
//    `ordering_fields` implicits. Pero `ordering_fields` NO esta declarat, i el implicit es
//    justament la mena de contracte que es trenca en silenci el dia que algu toca el serializer.
//    Demanat a S1 que el faci explicit.
//    🛑 **LIMIT DECLARAT**: el banc te **UN sol proveidor** (`Syttex`, tenant `fhort`) i **CAP**
//    al tenant `los`. Amb una fila no es pot observar cap ordenacio. Les icones hi son perque el
//    contracte les sosté; el que NO s'ha pogut fer es la comprovacio empirica que si que s'ha fet
//    a /clients. No esta amagat: esta dit.
//
// 3 · 🛑 **`Supplier.type` (workshop · factory) segueix declarat al client, marcat.** Els
//    `choices` son INLINE al model (`tasks/models.py:273`, sense ni tan sols una constant amb
//    nom) i cap endpoint els publica. La llei diu que no se n'inventin de NOVES; aquesta ja hi
//    era i es queda VIVA i censada fins que S1 la publiqui — igual que va fer el bloc A amb les
//    ~25 enumeracions que encara no tenien endpoint. Es un select que ESCRIU, o sigui que el dia
//    que arribi, arriba amb marca d'oferible o sense.
const MONO = 'IBM Plex Mono, monospace'
const PAGE_SIZE = 25
// Ordre per defecte: alfabètic pel nom, que és el `Meta.ordering` del model. Explícit aquí
// perquè la icona de la capçalera pugui dir-ho en obrir la pàgina.
const ORDRE_DEFECTE = { camp: 'name', dir: 'asc' }

export default function Suppliers() {
  const { t } = useTranslation()
  const me = useAuthStore(s => s.user)
  const canEdit = !!me?.capabilities?.includes('schedule_fittings')

  const [items, setItems] = useState([])
  const [count, setCount] = useState(0)
  const [total, setTotal] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [feedback, setFeedback] = useState(null)
  const [saving, setSaving] = useState(false)
  const [modal, setModal] = useState(null)   // { mode:'create'|'edit', sup? }

  const [sp, setSp] = useSearchParams()
  const page = Math.max(1, parseInt(sp.get('page') || '1', 10))
  // §8e · filtres ràpids de VISTA al menú. Com a Clients, el criteri no s'endevina: `active` és
  // un camp de debò i el backend ja el filtra (`filterset_fields = ['active', 'type']`).
  // ⚠️ CONDUCTA AFEGIDA: fins avui la llista barrejava actius i inactius; ara els inactius són a
  // la píndola del costat. Va al report perquè Agus ho pugui vetar.
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
    suppliers.list({
      active: vista === 'actius',
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
  }, [vista, ordre, page])

  // El DENOMINADOR del comptador: el cens sencer, sense el filtre de vista. Una sola fila
  // demanada — l'únic que se'n vol és el `count` (§8e: «no es dedueix d'una pàgina»).
  const carregaTotal = useCallback(() => {
    suppliers.list({ page_size: 1 }).then(r => setTotal(r.data?.count ?? null)).catch(() => setTotal(null))
  }, [])
  useEffect(() => { carregaTotal() }, [carregaTotal])
  useEffect(() => { const id = setTimeout(load, 150); return () => clearTimeout(id) }, [load])

  const pages = Math.max(1, Math.ceil(count / PAGE_SIZE))

  const remove = (sup, e) => {
    e.stopPropagation()
    if (!window.confirm(t('suppliers.confirm_delete', { name: sup.name }))) return
    setSaving(true); setFeedback(null)
    suppliers.remove(sup.id)
      .then(() => { load(); carregaTotal() })
      .then(() => setFeedback({ type: 'ok', text: t('suppliers.deleted') }))
      // PROTECT → 409 amb {detail} del backend; fallback i18n.
      .catch(err => setFeedback({ type: 'err', text: err?.response?.data?.detail || t('suppliers.delete_protected') }))
      .finally(() => setSaving(false))
  }

  // 🛑 BLOQUEJAT-PER-S1 · l'etiqueta d'un `Supplier.type`. Els choices són inline al model i cap
  // endpoint els publica: la traducció es queda aquí, marcada, fins que arribi l'enumeració.
  const typeLabel = (type) => type === 'factory' ? t('suppliers.factory') : t('suppliers.workshop')

  const cols = useMemo(() => [
    {
      // LA DADA REINA d'un catàleg de proveïdors és el NOM: és l'única cosa amb què es demanen.
      key: 'name', label: t('suppliers.col_name'), min: 200, max: 340, sort: 'name',
      estil: { fontWeight: 600 }, titol: r => r.name,
      render: r => r.name || '—',
    },
    {
      key: 'type', label: t('suppliers.col_type'), min: 100, max: 130, sort: 'type',
      estil: { fontSize: 11, color: 'var(--text-soft)' },
      render: r => typeLabel(r.type),
    },
    {
      // §8e · l'ESTAT amb badge de codi de colors. Actiu = verd; inactiu = NEUTRE, no vermell:
      // un proveïdor retirat no és cap error.
      key: 'active', label: t('suppliers.col_active'), min: 86, max: 100, sort: 'active',
      render: r => (
        <Badge variant={r.active ? 'ok' : 'gray'}>
          {r.active ? t('suppliers.active') : t('suppliers.inactive')}
        </Badge>
      ),
    },
    {
      key: 'del', amplada: 36,
      render: r => (canEdit
        ? <BotoEsborrar onClick={(e) => remove(r, e)} title={t('suppliers.delete')} disabled={saving} />
        : null),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [t, canEdit, saving])

  const VISTES = [
    ['actius', t('suppliers.view_active')],
    ['inactius', t('suppliers.view_inactive')],
  ]

  return (
    <>
      <div style={forceBarra}>
        <PageMenu
          backTo="/"
          backTitle={t('suppliers.back_title')}
          items={VISTES.map(([v, label]) => ({
            key: v, label, active: vista === v,
            onClick: () => setParams({ vista: v === 'actius' ? undefined : v, page: undefined }),
          }))}
        >
          {canEdit && <>
            <SepMenu />
            <BotoMenu onClick={() => setModal({ mode: 'create' })} icona="ti-plus"
              label={t('suppliers.new')} />
          </>}
        </PageMenu>
      </div>

      <div style={{ minWidth: 0, maxWidth: '100%' }}>
        {/* §8e · comptador + (aquí no hi va cerca: v. el punt 1 de la capçalera del fitxer). */}
        <FilaIdentitat>
          <Comptador valor={count} total={total ?? count} etiqueta={t('suppliers.entity')} />
        </FilaIdentitat>

        <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

        {loading ? <EstatBuit>{t('suppliers.loading')}</EstatBuit>
          : error ? <EstatBuit>{t('suppliers.error')}</EstatBuit>
            : items.length === 0 ? <EstatBuit>{t('suppliers.empty')}</EstatBuit>
              : (
                <TaulaLlista cols={cols} files={items} clau={(r) => r.id}
                  ordre={ordre} onOrdenar={ordenar}
                  // No hi ha fitxa de proveïdor: obrir la fila obre el seu formulari, que és on
                  // viu tot el que se'n sap. Sense permís d'escriptura la fila no s'obre —
                  // oferir-ho seria prometre una edició que el backend rebutjaria.
                  onObrir={canEdit ? (r) => setModal({ mode: 'edit', sup: r }) : null} />
              )}

        {/* §8c · una capacitat que falta també s'explica: aquesta llista no es pot cercar, i el
            motiu no es llegeix mirant-la. */}
        <div style={{ ...buit, margin: '4px 0 16px 2px' }}>{t('suppliers.search_pending')}</div>

        <Paginacio page={page} pages={pages} onPage={(p) => setParams({ page: p })}
          labelPrev={t('suppliers.prev')} labelNext={t('suppliers.next')}
          info={t('suppliers.page_info', { page, pages })} />
      </div>

      {modal && (
        <SupplierModal mode={modal.mode} sup={modal.sup} t={t} saving={saving} setSaving={setSaving}
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

// B3-M (M3): pestanya "Comercial" amb els camps fiscals/de compra/contacte del proveïdor
// (B1-P4). Tab "Dades" = identitat; tab "Comercial" = fiscalitat, condicions de compra i contacte.
function SupplierModal({ mode, sup, t, saving, setSaving, onCancel, onSaved, onError }) {
  const isEdit = mode === 'edit'
  const [tab, setTab] = useState('dades')
  const [name, setName] = useState(sup?.name || '')
  const [type, setType] = useState(sup?.type || 'workshop')
  const [active, setActive] = useState(sup?.active ?? true)
  const [f, setF] = useState({
    rao_social: sup?.rao_social || '', nif: sup?.nif || '',
    adreca_linia1: sup?.adreca_linia1 || '', adreca_linia2: sup?.adreca_linia2 || '',
    codi_postal: sup?.codi_postal || '', ciutat: sup?.ciutat || '', pais: sup?.pais || 'ES',
    condicions_compra: sup?.condicions_compra || '', email_contacte: sup?.email_contacte || '',
    persona_contacte: sup?.persona_contacte || '', telefon_contacte: sup?.telefon_contacte || '',
  })
  const set = (k, v) => setF(prev => ({ ...prev, [k]: v }))
  const invalid = !name.trim()

  const submit = () => {
    if (invalid) { onError(t('suppliers.required')); return }
    setSaving(true)
    const payload = {
      name: name.trim(), type, active,
      rao_social: f.rao_social, nif: f.nif.trim(), adreca_linia1: f.adreca_linia1,
      adreca_linia2: f.adreca_linia2, codi_postal: f.codi_postal, ciutat: f.ciutat,
      pais: f.pais.trim().toUpperCase(), condicions_compra: f.condicions_compra,
      email_contacte: f.email_contacte, persona_contacte: f.persona_contacte,
      telefon_contacte: f.telefon_contacte,
    }
    const req = isEdit ? suppliers.update(sup.id, payload) : suppliers.create(payload)
    req
      .then(() => onSaved(isEdit ? t('suppliers.saved') : t('suppliers.created')))
      .catch(e => onError(e?.response?.data?.name?.[0] || e?.response?.data?.detail || t('suppliers.error')))
      .finally(() => setSaving(false))
  }

  return (
    <Modal title={isEdit ? t('suppliers.edit_title') : t('suppliers.new_title')}
      cancelLabel={t('suppliers.cancel')} confirmLabel={isEdit ? t('suppliers.save') : t('suppliers.create')}
      onCancel={onCancel} onConfirm={submit} confirmDisabled={saving || invalid}>
      <TabBar tab={tab} setTab={setTab}
        tabs={[['dades', t('suppliers.tab_dades')], ['comercial', t('suppliers.tab_comercial')]]} />

      {tab === 'dades' && <>
        <Field label={t('suppliers.col_name')}><input value={name} onChange={e => setName(e.target.value)} style={{ ...camp, width: '100%' }} /></Field>
        <Field label={t('suppliers.col_type')}>
          <select value={type} onChange={e => setType(e.target.value)} style={{ ...camp, width: '100%' }}>
            <option value="workshop">{t('suppliers.workshop')}</option>
            <option value="factory">{t('suppliers.factory')}</option>
          </select>
        </Field>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 'var(--fs-body)', marginTop: 4 }}>
          <input type="checkbox" checked={active} onChange={e => setActive(e.target.checked)} /><span>{t('suppliers.active')}</span>
        </label>
      </>}

      {tab === 'comercial' && <>
        <Field label={t('suppliers.rao_social')}>
          <input value={f.rao_social} onChange={e => set('rao_social', e.target.value)} style={{ ...camp, width: '100%' }} />
        </Field>
        <Field label={t('suppliers.nif')}>
          <input value={f.nif} onChange={e => set('nif', e.target.value)} style={{ ...camp, width: '100%' }} />
        </Field>
        <Field label={t('suppliers.adreca')}>
          <input value={f.adreca_linia1} onChange={e => set('adreca_linia1', e.target.value)}
            placeholder={t('suppliers.adreca1')} style={{ ...camp, width: '100%', marginBottom: 6 }} />
          <input value={f.adreca_linia2} onChange={e => set('adreca_linia2', e.target.value)}
            placeholder={t('suppliers.adreca2')} style={{ ...camp, width: '100%' }} />
        </Field>
        <Row>
          <Field label={t('suppliers.codi_postal')}>
            <input value={f.codi_postal} onChange={e => set('codi_postal', e.target.value)} style={{ ...camp, width: '100%' }} />
          </Field>
          <Field label={t('suppliers.ciutat')}>
            <input value={f.ciutat} onChange={e => set('ciutat', e.target.value)} style={{ ...camp, width: '100%' }} />
          </Field>
          <Field label={t('suppliers.pais')}>
            <input value={f.pais} maxLength={2} onChange={e => set('pais', e.target.value.toUpperCase())}
              style={{ ...camp, width: '100%', textTransform: 'uppercase' }} />
          </Field>
        </Row>
        <Field label={t('suppliers.condicions_compra')}>
          <input value={f.condicions_compra} onChange={e => set('condicions_compra', e.target.value)} style={{ ...camp, width: '100%' }} />
        </Field>
        <Row>
          <Field label={t('suppliers.persona_contacte')}>
            <input value={f.persona_contacte} onChange={e => set('persona_contacte', e.target.value)} style={{ ...camp, width: '100%' }} />
          </Field>
          <Field label={t('suppliers.telefon_contacte')}>
            <input value={f.telefon_contacte} onChange={e => set('telefon_contacte', e.target.value)} style={{ ...camp, width: '100%' }} />
          </Field>
        </Row>
        <Field label={t('suppliers.email_contacte')}>
          <input value={f.email_contacte} onChange={e => set('email_contacte', e.target.value)} type="email" style={{ ...camp, width: '100%' }} />
        </Field>
      </>}
    </Modal>
  )
}

// §8b-bis · TABS DE SECCIO (dues germanes dins d'un panell): subratllat d'or. No es barregen
// amb les pindoles del menu de pantalla, que son l'altre patro i viuen a un altre nivell.
// El subratllat va per `box-shadow` i no per `border-bottom` pel mateix motiu que a la graella
// del fitting: una vora que apareix i desapareix mou el contingut dos pixels cada cop que algu
// tria.
function TabBar({ tab, setTab, tabs }) {
  return (
    <div style={{
      display: 'flex', gap: 4, marginBottom: 16,
      borderBottomWidth: 1, borderBottomStyle: 'solid', borderBottomColor: 'var(--line)',
    }}>
      {tabs.map(([k, label]) => (
        <button key={k} type="button" onClick={() => setTab(k)} style={{
          fontFamily: MONO, fontSize: 'var(--fs-body)', lineHeight: '16px',
          padding: '8px 12px', cursor: 'pointer', background: 'none', border: 'none',
          color: tab === k ? 'var(--text-main)' : 'var(--text-soft)',
          fontWeight: tab === k ? 600 : 400,
          boxShadow: tab === k ? 'inset 0 -2px 0 var(--gold)' : 'none',
        }}>{label}</button>
      ))}
    </div>
  )
}

function Row({ children }) {
  return <div style={{ display: 'flex', gap: 10 }}>{children}</div>
}

// §2 · l'etiqueta d'un camp es un LABEL: 10px, majuscules, tracking .08em, pes 600. Anava a
// 12px (mida de COS) amb pes normal, o sigui que cridava tant com el valor que etiqueta.
function Field({ label, children }) {
  return (
    <div style={{ marginBottom: 14, flex: 1 }}>
      <label style={{
        display: 'block', marginBottom: 6, fontFamily: MONO,
        fontSize: 'var(--fs-label)', lineHeight: '12px', letterSpacing: '.08em',
        textTransform: 'uppercase', color: 'var(--text-soft)', fontWeight: 600,
      }}>{label}</label>
      {children}
    </div>
  )
}
