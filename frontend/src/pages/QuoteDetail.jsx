import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams, useNavigate } from 'react-router-dom'
import useAuthStore from '../store/auth'
import { commerce } from '../api/endpoints'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import Modal from '../components/ui/Modal'
import { selS, primaryBtn } from '../components/ui/buttons'
import { StatusBadge } from './Quotes'

// Mòdul Comercial Studio — B2 · fitxa d'oferta: capçalera + línies + totals + PDF.
// Les línies i els detalls només s'editen en DRAFT (segellat en enviar). Plantilla ProductDetail.jsx.
const MONO = 'IBM Plex Mono, monospace'
const smallBtn = {
  background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6, cursor: 'pointer',
  padding: '4px 9px', fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)',
}
const delBtn = { ...smallBtn, color: 'var(--err)', borderColor: 'var(--err)' }
const money = (v) => `${Number(v ?? 0).toFixed(2)} €`

// Baixa un Blob com a fitxer (mateix helper que BulkImportWizard).
function downloadBlob(blob, filename) {
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  document.body.appendChild(link); link.click(); document.body.removeChild(link)
  URL.revokeObjectURL(link.href)
}
function filenameFromHeaders(res, fallback) {
  const cd = res?.headers?.['content-disposition'] || ''
  const m = /filename="?([^"]+)"?/.exec(cd)
  return (m && m[1]) || fallback
}

export default function QuoteDetail() {
  const { t } = useTranslation()
  const { id } = useParams()
  const navigate = useNavigate()
  const me = useAuthStore(s => s.user)
  const canEdit = !!me?.capabilities?.includes('configure')

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [quote, setQuote] = useState(null)
  const [products, setProducts] = useState([])
  const [paymentTerms, setPaymentTerms] = useState([])
  const [feedback, setFeedback] = useState(null)
  const [busy, setBusy] = useState(false)
  const [confirmConvert, setConfirmConvert] = useState(false)

  const reload = useCallback(() => commerce.quotes.get(id)
    .then(res => setQuote(res.data))
    .catch(() => setError(true)), [id])

  useEffect(() => {
    let alive = true
    const rows = (res) => res.data?.results ?? (Array.isArray(res.data) ? res.data : [])
    Promise.all([
      commerce.quotes.get(id).then(res => res.data),
      commerce.products.list({ active: true, page_size: 500 }).then(rows).catch(() => []),
      commerce.paymentTerms.list({ active: true, page_size: 200 }).then(rows).catch(() => []),
    ])
      .then(([q, ps, pt]) => { if (alive) { setQuote(q); setProducts(ps); setPaymentTerms(pt) } })
      .catch(() => { if (alive) setError(true) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [id])

  const ok = (text) => setFeedback({ type: 'ok', text })
  const err = (e) => setFeedback({ type: 'err', text: e?.response?.data?.detail || e?.response?.data?.non_field_errors?.[0] || t('quotes.error') })

  const doSend = () => {
    setBusy(true); setFeedback(null)
    commerce.quotes.send(id)
      .then(() => reload()).then(() => ok(t('quotes.sent')))
      .catch(e => err(e)).finally(() => setBusy(false))
  }

  const doPdf = () => {
    setBusy(true); setFeedback(null)
    commerce.quotes.pdf(id)
      .then(res => downloadBlob(res.data, filenameFromHeaders(res, `${quote?.document_number || 'oferta'}.pdf`)))
      .catch(() => setFeedback({ type: 'err', text: t('quotes.pdf_error') }))
      .finally(() => setBusy(false))
  }

  const doConvert = () => {
    setBusy(true); setFeedback(null)
    commerce.quotes.convert(id)
      .then(res => { setConfirmConvert(false); navigate(`/comercial/comandes/${res.data.id}`) })
      .catch(e => { setConfirmConvert(false); err(e) })
      .finally(() => setBusy(false))
  }

  if (loading) return <Center>{t('quotes.loading')}</Center>
  if (error || !quote) return <Center>{t('quotes.error')}</Center>

  const isDraft = quote.status === 'DRAFT'
  const editable = canEdit && isDraft
  const hasLines = (quote.lines || []).length > 0
  const canConvert = canEdit && quote.status === 'SENT'

  return (
    <div style={{ minWidth: 0, maxWidth: 900 }}>
      <button onClick={() => navigate('/comercial/ofertes')} style={{ ...smallBtn, marginBottom: 12 }}>
        <i className="ti ti-arrow-left" style={{ fontSize: 14 }} /> {t('quotes.back')}
      </button>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6, flexWrap: 'wrap' }}>
        <h1 style={{ fontSize: 'var(--fs-h1)', fontWeight: 500, fontFamily: MONO }}>{quote.document_number}</h1>
        <StatusBadge status={quote.status} t={t} />
      </div>
      <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', marginBottom: 16 }}>{quote.customer_nom}</p>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        <button onClick={doSend} disabled={busy || !editable || !hasLines} style={primaryBtn}
          title={!isDraft ? t('quotes.send_only_draft') : (!hasLines ? t('quotes.send_needs_lines') : '')}>
          <i className="ti ti-send" style={{ fontSize: 14 }} /> {t('quotes.send')}
        </button>
        <button onClick={doPdf} disabled={busy} style={smallBtn}>
          <i className="ti ti-file-download" style={{ fontSize: 14 }} /> {t('quotes.download_pdf')}
        </button>
        {canConvert && (
          <button onClick={() => setConfirmConvert(true)} disabled={busy} style={primaryBtn}>
            <i className="ti ti-arrow-right-circle" style={{ fontSize: 14 }} /> {t('quotes.convert')}
          </button>
        )}
      </div>

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      {!isDraft && <p style={{ fontSize: 'var(--fs-label)', color: 'var(--gray)', marginBottom: 12 }}>{t('quotes.locked_note')}</p>}

      <LinesSection quote={quote} editable={editable} products={products} t={t} reload={reload} ok={ok} err={err} />
      <DetailsSection quote={quote} editable={editable} paymentTerms={paymentTerms} t={t} reload={reload} ok={ok} err={err} />

      {confirmConvert && (
        <Modal title={t('quotes.convert_title')} subtitle={t('quotes.convert_warning')}
          cancelLabel={t('quotes.cancel')} confirmLabel={t('quotes.convert_confirm')}
          onCancel={() => setConfirmConvert(false)} onConfirm={doConvert} confirmDisabled={busy}>
          <p style={{ fontSize: 'var(--fs-body)', lineHeight: 1.5 }}>{t('quotes.convert_body')}</p>
        </Modal>
      )}
    </div>
  )
}

function Section({ title, hint, children }) {
  return (
    <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', padding: 16, marginBottom: 16 }}>
      <h2 style={{ fontSize: 'var(--fs-h2)', fontWeight: 500, fontFamily: MONO, marginBottom: hint ? 2 : 10 }}>{title}</h2>
      {hint && <p style={{ fontSize: 'var(--fs-label)', color: 'var(--gray)', marginBottom: 10 }}>{hint}</p>}
      {children}
    </div>
  )
}

function Row({ children }) {
  return <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0', borderTop: '0.5px solid var(--bg-muted)' }}>{children}</div>
}

// --- Línies de l'oferta: afegir/treure (només DRAFT) + totals ---
function LinesSection({ quote, editable, products, t, reload, ok, err }) {
  const [product, setProduct] = useState('')
  const [description, setDescription] = useState('')
  const [qty, setQty] = useState('1')
  const [price, setPrice] = useState('')
  const [busy, setBusy] = useState(false)
  const lines = quote.lines || []

  // En triar un article, precarrega el preu unitari amb el seu base_price (congelable/editable).
  const onPickProduct = (pid) => {
    setProduct(pid)
    const p = products.find(x => String(x.id) === String(pid))
    if (p && p.base_price != null && price === '') setPrice(String(p.base_price))
  }

  const add = () => {
    if (!product || qty === '') return
    setBusy(true)
    commerce.quoteLines.create({
      quote: quote.id, product, description: description.trim(),
      quantity: qty || 1, unit_price: price === '' ? undefined : price,
    })
      .then(() => reload()).then(() => { setProduct(''); setDescription(''); setQty('1'); setPrice(''); ok(t('quotes.line_added')) })
      .catch(err).finally(() => setBusy(false))
  }
  const del = (lid) => {
    setBusy(true)
    commerce.quoteLines.remove(lid).then(() => reload()).then(() => ok(t('quotes.line_removed'))).catch(err).finally(() => setBusy(false))
  }

  return (
    <Section title={t('quotes.lines')} hint={t('quotes.lines_hint')}>
      {lines.length === 0 && <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)' }}>{t('quotes.lines_empty')}</p>}
      {lines.map(l => (
        <Row key={l.id}>
          <span style={{ flex: 1 }}>{l.description || l.product_name}</span>
          <span style={{ fontFamily: MONO, color: 'var(--text-muted)' }}>×{Number(l.quantity).toFixed(2)}</span>
          <span style={{ fontFamily: MONO, color: 'var(--text-muted)' }}>{money(l.unit_price)}</span>
          <span style={{ fontFamily: MONO, fontWeight: 600, minWidth: 90, textAlign: 'right' }}>{money(l.line_total)}</span>
          {editable && <button onClick={() => del(l.id)} disabled={busy} style={delBtn}>{t('quotes.remove')}</button>}
        </Row>
      ))}

      {/* Totals — subtotal + desglossament fiscal per tipus (tax_breakdown) + total */}
      <div style={{ marginTop: 12, paddingTop: 8, borderTop: '0.5px solid var(--gray-l)', display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-end' }}>
        <Total label={t('quotes.subtotal')} value={money(quote.subtotal)} />
        {(quote.tax_breakdown || []).map((b, i) => (
          <Total key={i} label={`${t('quotes.vat')} ${Number(b.rate)}% · ${t('quotes.base')} ${money(b.base)}`} value={money(b.tax)} />
        ))}
        {(!quote.tax_breakdown || quote.tax_breakdown.length === 0) &&
          <Total label={t('quotes.tax_amount')} value={money(quote.tax_amount)} />}
        <Total label={t('quotes.total')} value={money(quote.total)} strong />
      </div>

      {editable && (
        <div style={{ display: 'flex', gap: 8, marginTop: 14, alignItems: 'center', flexWrap: 'wrap' }}>
          <select value={product} onChange={e => onPickProduct(e.target.value)} style={{ ...selS, flex: 1, minWidth: 160 }}>
            <option value="">{t('quotes.product_ph')}</option>
            {products.map(p => <option key={p.id} value={p.id}>{p.code} · {p.name}</option>)}
          </select>
          <input value={description} onChange={e => setDescription(e.target.value)} placeholder={t('quotes.desc_ph')} style={{ ...selS, flex: 1, minWidth: 140 }} />
          <input type="text" inputMode="decimal" value={qty} onChange={e => setQty(e.target.value)} placeholder={t('quotes.col_qty')} style={{ ...selS, width: 80 }} />
          <input type="text" inputMode="decimal" value={price} onChange={e => setPrice(e.target.value)} placeholder={t('quotes.col_unit_price')} style={{ ...selS, width: 100 }} />
          <button onClick={add} disabled={busy || !product} style={primaryBtn}>{t('quotes.add')}</button>
        </div>
      )}
    </Section>
  )
}

function Total({ label, value, strong }) {
  return (
    <div style={{ display: 'flex', gap: 16, minWidth: 220, justifyContent: 'space-between' }}>
      <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', fontWeight: strong ? 600 : 400 }}>{label}</span>
      <span style={{ fontFamily: MONO, fontWeight: strong ? 700 : 400 }}>{value}</span>
    </div>
  )
}

// --- Detalls editables (validesa, condicions de pagament, notes) — només DRAFT ---
// L'IVA ja NO és editable (B3a): es calcula sobre bases agregades i es mostra al desglossament.
function DetailsSection({ quote, editable, paymentTerms, t, reload, ok, err }) {
  const [terms, setTerms] = useState(quote.payment_terms != null ? String(quote.payment_terms) : '')
  const [validUntil, setValidUntil] = useState(quote.valid_until || '')
  const [notes, setNotes] = useState(quote.notes || '')
  const [busy, setBusy] = useState(false)
  const defaultName = paymentTerms.find(p => String(p.id) === String(quote.customer_payment_terms))?.name

  const save = () => {
    setBusy(true)
    commerce.quotes.update(quote.id, {
      payment_terms: terms === '' ? null : terms, valid_until: validUntil || null, notes,
    })
      .then(() => reload()).then(() => ok(t('quotes.saved'))).catch(err).finally(() => setBusy(false))
  }

  return (
    <Section title={t('quotes.details')}>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 10 }}>
        <Field label={t('quotes.valid_until')}>
          {editable
            ? <input type="date" value={validUntil} onChange={e => setValidUntil(e.target.value)} style={{ ...selS }} />
            : <span style={{ fontFamily: MONO }}>{quote.valid_until || '—'}</span>}
        </Field>
        <Field label={t('quotes.payment_terms')}>
          {editable
            ? <select value={terms} onChange={e => setTerms(e.target.value)} style={{ ...selS, minWidth: 200 }}>
                <option value="">{t('quotes.terms_customer_default')}{defaultName ? ` · ${defaultName}` : ''}</option>
                {paymentTerms.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            : <span style={{ fontFamily: MONO }}>{quote.payment_terms_name || defaultName || '—'}</span>}
        </Field>
      </div>
      <Field label={t('quotes.notes')}>
        {editable
          ? <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={3} style={{ ...selS, width: '100%', resize: 'vertical' }} />
          : <span style={{ whiteSpace: 'pre-wrap' }}>{quote.notes || '—'}</span>}
      </Field>
      {editable && (
        <div style={{ marginTop: 12 }}>
          <button onClick={save} disabled={busy} style={primaryBtn}>{t('quotes.save')}</button>
        </div>
      )}
    </Section>
  )
}

function Field({ label, children }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <label style={{ fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)', textTransform: 'uppercase', display: 'block', marginBottom: 6 }}>{label}</label>
      {children}
    </div>
  )
}
