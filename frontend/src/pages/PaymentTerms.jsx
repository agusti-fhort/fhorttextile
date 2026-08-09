import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router-dom'
import useAuthStore from '../store/auth'
import { commerce } from '../api/endpoints'
import Feedback from '../components/ui/Feedback'
import Modal from '../components/ui/Modal'
import Badge from '../components/ui/Badge'
import PageMenu from '../components/ui/PageMenu'
import TaulaLlista from '../components/ui/TaulaLlista'
import TranslatableField, { pickTranslation } from '../components/ui/TranslatableField'
import {
  BotoMenu, SepMenu, Comptador, FilaIdentitat, EstatBuit, BotoEsborrar, Paginacio,
  camp, buit, forceBarra,
} from '../components/llista/ChromLlista'
import { botoSec } from '../components/ui/buttons'

// CONDICIONS DE PAGAMENT (`PaymentTerms`, M4) — LLISTA CANONICA (NORMA_LAYOUT §8b + §8e).
//
// Llista + fitxa amb FRACCIONS (percentage, days_offset, position). Les fraccions s'editen com a
// conjunt i es desen amb la condicio en UNA sola crida (nested writable); el guard Σ%=100 viu al
// backend i aqui nomes s'hi ensenya.
//
// ── DUES COSES QUE ES DIUEN EN VEU ALTA ──────────────────────────────────────────────────
//
// 1 · **EL TOTAL DE FRACCIONS ES L'UNIC SEMAFOR LEGITIM D'AQUESTA PANTALLA**, i es queda —pero
//    ara amb la forma de la casa. «Σ = 100%» verd / «no suma 100» vermell es LA DADA portant el
//    color (D-31.21), que es exactament el cas que la §1 admet. El que canvia es que ho fa amb
//    els tokens del semafor i no amb tinta solta sobre el fons del modal.
//
// 2 · **ES L'UNICA PANTALLA DEL LOT AMB UNA COLUMNA QUE POT SER LLARGA DE DEBO**: el resum de
//    fraccions («50% · +0d | 50% · +30d»). La §8e mana ellipsis + `title`, i aixi es queda: el
//    detall sencer es al modal, que es on s'editen. Una fila d'una linia es el que fa que la
//    llista es pugui escombrar amb la vista.
const MONO = 'IBM Plex Mono, monospace'
const PAGE_SIZE = 25
const ORDRE_DEFECTE = { camp: 'code', dir: 'asc' }

export default function PaymentTerms() {
  const { t, i18n } = useTranslation()
  const lang = i18n.resolvedLanguage || i18n.language || 'ca'
  const me = useAuthStore(s => s.user)
  const canEdit = !!me?.capabilities?.includes('configure')

  const [items, setItems] = useState([])
  const [count, setCount] = useState(0)
  const [total, setTotal] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [feedback, setFeedback] = useState(null)
  const [saving, setSaving] = useState(false)
  const [modal, setModal] = useState(null)   // { mode:'create'|'edit', term? }

  const [sp, setSp] = useSearchParams()
  const page = Math.max(1, parseInt(sp.get('page') || '1', 10))
  // §8e · filtres ràpids de VISTA. Com a Clients i Proveïdors: el criteri no s'endevina,
  // `active` és un camp de debò i el backend ja el filtra.
  const vista = sp.get('vista') === 'inactives' ? 'inactives' : 'actives'
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
    commerce.paymentTerms.list({
      active: vista === 'actives',
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

  const carregaTotal = useCallback(() => {
    commerce.paymentTerms.list({ page_size: 1 })
      .then(r => setTotal(r.data?.count ?? null)).catch(() => setTotal(null))
  }, [])

  useEffect(() => { carregaTotal() }, [carregaTotal])
  useEffect(() => { const id = setTimeout(load, 150); return () => clearTimeout(id) }, [load])

  const pages = Math.max(1, Math.ceil(count / PAGE_SIZE))

  const remove = (term, e) => {
    e.stopPropagation()
    if (!window.confirm(t('payment_terms.confirm_delete', { name: term.name }))) return
    setSaving(true); setFeedback(null)
    commerce.paymentTerms.remove(term.id)
      .then(() => { load(); carregaTotal() })
      .then(() => setFeedback({ type: 'ok', text: t('payment_terms.deleted') }))
      .catch(err => setFeedback({ type: 'err', text: err?.response?.data?.detail || t('payment_terms.error') }))
      .finally(() => setSaving(false))
  }

  const resumFraccions = (r) => (r.lines || [])
    .map(l => `${Number(l.percentage)}% · +${l.days_offset}d`).join('  |  ') || '—'

  const cols = useMemo(() => [
    {
      // LA DADA REINA d'un catàleg de condicions és el CODI («50-50», «30D»): és amb el que es
      // demanen i el que surt al document. Mateix cas que el catàleg de POMs, no el de clients.
      key: 'code', label: t('payment_terms.col_code'), min: 90, max: 120, sort: 'code',
      estil: { fontWeight: 600 }, titol: r => r.code,
      render: r => r.code,
    },
    {
      key: 'name', label: t('payment_terms.col_name'), min: 160, max: 240, sort: 'name',
      titol: r => pickTranslation(r, 'name', lang),
      render: r => pickTranslation(r, 'name', lang),
    },
    {
      key: 'fractions', label: t('payment_terms.col_fractions'), min: 200, max: 340,
      estil: { fontSize: 11, color: 'var(--text-soft)' },
      titol: r => resumFraccions(r),
      render: r => resumFraccions(r),
    },
    {
      key: 'active', label: t('payment_terms.col_active'), min: 86, max: 100, sort: 'active',
      render: r => (
        <Badge variant={r.active ? 'ok' : 'gray'}>
          {r.active ? t('payment_terms.active') : t('payment_terms.inactive')}
        </Badge>
      ),
    },
    {
      key: 'del', amplada: 36,
      render: r => (canEdit
        ? <BotoEsborrar onClick={(e) => remove(r, e)} title={t('payment_terms.delete')} disabled={saving} />
        : null),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [t, lang, canEdit, saving])

  const VISTES = [
    ['actives', t('payment_terms.view_active')],
    ['inactives', t('payment_terms.view_inactive')],
  ]

  return (
    <>
      <div style={forceBarra}>
        <PageMenu
          backTo="/" backTitle={t('payment_terms.back_title')}
          items={VISTES.map(([v, label]) => ({
            key: v, label, active: vista === v,
            onClick: () => setParams({ vista: v === 'actives' ? undefined : v, page: undefined }),
          }))}
        >
          {canEdit && <>
            <SepMenu />
            <BotoMenu onClick={() => setModal({ mode: 'create' })} icona="ti-plus"
              label={t('payment_terms.new')} />
          </>}
        </PageMenu>
      </div>

      <div style={{ minWidth: 0, maxWidth: '100%' }}>
        <FilaIdentitat>
          <Comptador valor={count} total={total ?? count} etiqueta={t('payment_terms.entity')} />
        </FilaIdentitat>

        <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

        {loading ? <EstatBuit>{t('payment_terms.loading')}</EstatBuit>
          : error ? <EstatBuit>{t('payment_terms.error')}</EstatBuit>
            : items.length === 0 ? <EstatBuit>{t('payment_terms.empty')}</EstatBuit>
              : (
                <TaulaLlista cols={cols} files={items} clau={(r) => r.id}
                  ordre={ordre} onOrdenar={ordenar}
                  // No hi ha fitxa pròpia: el modal ÉS la fitxa d'una condició de pagament.
                  onObrir={canEdit ? (r) => setModal({ mode: 'edit', term: r }) : null} />
              )}

        <Paginacio page={page} pages={pages} onPage={(p) => setParams({ page: p })}
          labelPrev={t('payment_terms.prev')} labelNext={t('payment_terms.next')}
          info={t('payment_terms.page_info', { page, pages })} />
      </div>

      {modal && (
        <PaymentTermModal mode={modal.mode} term={modal.term} t={t} saving={saving} setSaving={setSaving}
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

function PaymentTermModal({ mode, term, t, saving, setSaving, onCancel, onSaved, onError }) {
  const isEdit = mode === 'edit'
  const [code, setCode] = useState(term?.code || '')
  const [name, setName] = useState(term?.name || '')
  const [translations, setTranslations] = useState(term?.translations || {})
  const [active, setActive] = useState(term?.active ?? true)
  const [lines, setLines] = useState(
    (term?.lines || []).map(l => ({ percentage: String(l.percentage), days_offset: String(l.days_offset), position: l.position }))
  )
  const invalid = !code.trim() || !name.trim()
  const total = lines.reduce((s, l) => s + (parseFloat(l.percentage) || 0), 0)
  const totalOk = lines.length === 0 || Math.abs(total - 100) < 0.005

  const setLine = (i, k, v) => setLines(prev => prev.map((l, idx) => idx === i ? { ...l, [k]: v } : l))
  const addLine = () => setLines(prev => [...prev, { percentage: '', days_offset: '0', position: prev.length }])
  const removeLine = (i) => setLines(prev => prev.filter((_, idx) => idx !== i).map((l, idx) => ({ ...l, position: idx })))

  const submit = () => {
    if (invalid) { onError(t('payment_terms.required')); return }
    setSaving(true)
    const payload = {
      code: code.trim(), name: name.trim(), translations, active,
      lines: lines.map((l, idx) => ({
        percentage: l.percentage === '' ? '0' : l.percentage,
        days_offset: l.days_offset === '' ? 0 : parseInt(l.days_offset, 10),
        position: idx,
      })),
    }
    const req = isEdit ? commerce.paymentTerms.update(term.id, payload) : commerce.paymentTerms.create(payload)
    req
      .then(() => onSaved(isEdit ? t('payment_terms.saved') : t('payment_terms.created')))
      .catch(e => onError(
        e?.response?.data?.lines?.[0] || e?.response?.data?.lines
        || e?.response?.data?.code?.[0] || e?.response?.data?.detail || t('payment_terms.error')))
      .finally(() => setSaving(false))
  }

  return (
    <Modal title={isEdit ? t('payment_terms.edit_title') : t('payment_terms.new_title')}
      cancelLabel={t('payment_terms.cancel')} confirmLabel={isEdit ? t('payment_terms.save') : t('payment_terms.create')}
      onCancel={onCancel} onConfirm={submit} confirmDisabled={saving || invalid}>
      <Field label={t('payment_terms.col_code')}>
        <input value={code} onChange={e => setCode(e.target.value)} placeholder="ex: 50-50" style={{ ...camp, width: '100%' }} />
      </Field>
      <TranslatableField label={t('payment_terms.col_name')} field="name" value={name} onChange={setName}
        translations={translations} onTranslationsChange={setTranslations} />

      <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <label style={etiquetaCamp}>{t('payment_terms.fractions')}</label>
        {/* SECUNDARI (§5.2): afegir una fracció no acaba la feina —desar la condició, sí— i per
            això no competeix amb el botó de confirmar del modal. */}
        <button type="button" onClick={addLine} style={{ ...botoSec, padding: '5px 10px' }}>
          <i className="ti ti-plus" aria-hidden="true" style={{ fontSize: 14, color: 'currentColor' }} />
          {t('payment_terms.add_fraction')}
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: 6, marginBottom: 4 }}>
        <span style={etiquetaCamp}>{t('payment_terms.percentage')}</span>
        <span style={etiquetaCamp}>{t('payment_terms.days_offset')}</span>
        <span />
      </div>
      {lines.map((l, i) => (
        <div key={i} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: 6, marginBottom: 6, alignItems: 'center' }}>
          <input type="text" inputMode="decimal" value={l.percentage} onChange={e => setLine(i, 'percentage', e.target.value)} style={{ ...camp, width: '100%' }} />
          <input type="text" inputMode="numeric" value={l.days_offset} onChange={e => setLine(i, 'days_offset', e.target.value)} style={{ ...camp, width: '100%' }} />
          <BotoEsborrar onClick={() => removeLine(i)} title={t('payment_terms.remove_fraction')} />
        </div>
      ))}
      {/* §8c · estat buit = frase en --text-faint CURSIVA, mai una caixa muda ni text gris pla. */}
      {lines.length === 0 && <p style={{ ...buit, margin: '4px 0 10px' }}>{t('payment_terms.no_fractions')}</p>}

      {/* D-31.21 · LA DADA PORTA EL COLOR, i aquest és el cas que la §1 admet: la suma de
          fraccions és una condició de validesa (el guard Σ=100 viu al backend) i el seu
          resultat es llegeix d'un cop d'ull. Amb la forma de badge de la casa —fons suau +
          tinta + filet fi— i no amb tinta solta sobre el fons del modal. */}
      <div style={{ marginTop: 8, marginBottom: 4 }}>
        <Badge variant={totalOk ? 'ok' : 'err'}>
          {t('payment_terms.total_pct')}: {total.toFixed(2)}%
          {!totalOk && ` · ${t('payment_terms.total_must_be_100')}`}
        </Badge>
      </div>

      <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 'var(--fs-body)', marginTop: 8 }}>
        <input type="checkbox" checked={active} onChange={e => setActive(e.target.checked)} /><span>{t('payment_terms.active')}</span>
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

// §2 · l'etiqueta d'un camp és un LABEL: 10px majúscules, tracking .08em, pes 600. Anava a mida
// de COS (12) i pes normal, o sigui que cridava tant com el valor que etiqueta.
const etiquetaCamp = {
  display: 'block', marginBottom: 6, fontFamily: MONO,
  fontSize: 'var(--fs-label)', lineHeight: '12px', letterSpacing: '.08em',
  textTransform: 'uppercase', color: 'var(--text-soft)', fontWeight: 600,
}
