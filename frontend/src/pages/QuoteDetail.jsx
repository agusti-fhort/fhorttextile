import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import useAuthStore from '../store/auth'
import { commerce } from '../api/endpoints'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import Modal from '../components/ui/Modal'
import PdfButton from '../components/ui/PdfButton'
import { selS, primaryBtn } from '../components/ui/buttons'
import { DocumentHeader, LineTable, RowBtn, DocumentSummary } from '../components/commercial'
import { StatusBadge } from './Quotes'

// Mòdul Comercial Studio — B2 · fitxa d'oferta: capçalera + línies + totals + PDF.
// Les línies i els detalls només s'editen en DRAFT (segellat en enviar). Plantilla ProductDetail.jsx.
// E6 — vincle preparatori: intencions de model per línia, editables en DRAFT i SENT (l'oferta enviada
// encara negocia models), read-only en ACCEPTED. Picker de models replicat d'OrderDetail.
const MONO = 'IBM Plex Mono, monospace'
const smallBtn = {
  background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6, cursor: 'pointer',
  padding: '4px 9px', fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)',
}
const intentChip = {
  display: 'inline-flex', alignItems: 'center', gap: 5, padding: '2px 8px', borderRadius: 12,
  border: '0.5px solid var(--gray-l)', background: 'var(--gold-pale)', fontFamily: MONO,
  fontSize: 'var(--fs-caption)', color: 'var(--gold)', fontWeight: 600,
}
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
  // E3/E6 — resultat de la conversió amb conflictes d'intenció (models que no han viatjat).
  const [convertResult, setConvertResult] = useState(null)   // { orderId, conflicts, assigned, reattached } | null

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
      .then(res => {
        setConfirmConvert(false)
        const d = res.data
        const conflicts = d.intent_conflicts || []
        // Amb conflictes d'intenció, informem el comercial abans de navegar; sense, anem a la comanda.
        if (conflicts.length) {
          setConvertResult({ orderId: d.id, conflicts, assigned: d.assigned || 0, reattached: d.reattached || 0 })
        } else {
          navigate(`/comercial/comandes/${d.id}`)
        }
      })
      .catch(e => { setConfirmConvert(false); err(e) })
      .finally(() => setBusy(false))
  }

  if (loading) return <Center>{t('quotes.loading')}</Center>
  if (error || !quote) return <Center>{t('quotes.error')}</Center>

  const isDraft = quote.status === 'DRAFT'
  const editable = canEdit && isDraft
  const hasLines = (quote.lines || []).length > 0
  const canConvert = canEdit && quote.status === 'SENT'
  // E6 — les intencions de model es negocien en DRAFT i SENT; read-only en ACCEPTED.
  const canIntents = canEdit && (quote.status === 'DRAFT' || quote.status === 'SENT')

  return (
    <div style={{ minWidth: 0, maxWidth: 900 }}>
      <button onClick={() => navigate('/comercial/ofertes')} style={{ ...smallBtn, marginBottom: 12 }}>
        <i className="ti ti-arrow-left" style={{ fontSize: 14 }} /> {t('quotes.back')}
      </button>

      <DocumentHeader
        reference={quote.document_number}
        statusBadge={<StatusBadge status={quote.status} t={t} />}
        customer={quote.customer_nom}
        actions={<>
          <button onClick={doSend} disabled={busy || !editable || !hasLines} style={{ ...primaryBtn, marginLeft: 0 }}
            title={!isDraft ? t('quotes.send_only_draft') : (!hasLines ? t('quotes.send_needs_lines') : '')}>
            <i className="ti ti-send" style={{ fontSize: 14 }} /> {t('quotes.send')}
          </button>
          <PdfButton onClick={doPdf} disabled={busy} label={t('quotes.download_pdf')} />
          {canConvert && (
            <button onClick={() => setConfirmConvert(true)} disabled={busy} style={{ ...primaryBtn, marginLeft: 0 }}>
              <i className="ti ti-arrow-right-circle" style={{ fontSize: 14 }} /> {t('quotes.convert')}
            </button>
          )}
        </>}
      />

      <div style={{ marginTop: 12 }}>
        <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />
      </div>

      {!isDraft && <p style={{ fontSize: 'var(--fs-label)', color: 'var(--gray)', marginBottom: 12 }}>{t('quotes.locked_note')}</p>}

      <LinesSection quote={quote} editable={editable} canIntents={canIntents} products={products}
        t={t} reload={reload} ok={ok} err={err} />
      <div style={{ marginBottom: 16 }}>
        <DocumentSummary lines={quoteSummaryLines(quote, t)} />
      </div>
      <DetailsSection quote={quote} editable={editable} paymentTerms={paymentTerms} t={t} reload={reload} ok={ok} err={err} />

      {confirmConvert && (
        <Modal title={t('quotes.convert_title')} subtitle={t('quotes.convert_warning')}
          cancelLabel={t('quotes.cancel')} confirmLabel={t('quotes.convert_confirm')}
          onCancel={() => setConfirmConvert(false)} onConfirm={doConvert} confirmDisabled={busy}>
          <p style={{ fontSize: 'var(--fs-body)', lineHeight: 1.5 }}>{t('quotes.convert_body')}</p>
        </Modal>
      )}

      {/* E3/E6 — resultat de la conversió amb conflictes: models d'intenció que no han viatjat. */}
      {convertResult && (
        <Modal title={t('quotes.convert_conflicts_title')} subtitle={t('quotes.convert_conflicts_subtitle')}
          cancelLabel={t('common.close')} confirmLabel={t('quotes.convert_conflicts_open')}
          onCancel={() => setConvertResult(null)}
          onConfirm={() => navigate(`/comercial/comandes/${convertResult.orderId}`)}>
          <p style={{ fontSize: 'var(--fs-body)', marginBottom: 10 }}>
            {t('quotes.convert_conflicts_summary', { assigned: convertResult.assigned, reattached: convertResult.reattached })}
          </p>
          <ul style={{ fontSize: 'var(--fs-body)', margin: 0, paddingLeft: 18, lineHeight: 1.6 }}>
            {convertResult.conflicts.map((c, i) => (
              <li key={i}>
                <span style={{ fontFamily: MONO, fontWeight: 600, color: 'var(--gold)' }}>{c.model_codi}</span>
                {' — '}
                {c.reason === 'busy'
                  ? t('quotes.convert_conflict_busy', { order: c.order || '—' })
                  : (c.detail || t('quotes.convert_conflict_generic'))}
              </li>
            ))}
          </ul>
        </Modal>
      )}
    </div>
  )
}

function Section({ title, hint, children }) {
  return (
    <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', padding: 16, marginBottom: 16 }}>
      <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, fontFamily: MONO, marginBottom: hint ? 2 : 10 }}>{title}</h2>
      {hint && <p style={{ fontSize: 'var(--fs-label)', color: 'var(--gray)', marginBottom: 10 }}>{hint}</p>}
      {children}
    </div>
  )
}

// Línies del resum fiscal del document (subtotal · desglossament IVA per tipus · total).
function quoteSummaryLines(quote, t) {
  const rows = [{ label: t('quotes.subtotal'), value: money(quote.subtotal) }]
  if ((quote.tax_breakdown || []).length) {
    quote.tax_breakdown.forEach(b => rows.push({
      label: `${t('quotes.vat')} ${Number(b.rate)}% · ${t('quotes.base')} ${money(b.base)}`, value: money(b.tax),
    }))
  } else {
    rows.push({ label: t('quotes.tax_amount'), value: money(quote.tax_amount) })
  }
  rows.push({ label: t('quotes.total'), value: money(quote.total), strong: true })
  return rows
}

// --- Línies de l'oferta: afegir/treure (només DRAFT) + intencions de model (DRAFT/SENT) + totals ---
function LinesSection({ quote, editable, canIntents, products, t, reload, ok, err }) {
  const [product, setProduct] = useState('')
  const [description, setDescription] = useState('')
  const [qty, setQty] = useState('1')
  const [price, setPrice] = useState('')
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const lines = quote.lines || []
  const anyIntent = lines.some(l => (l.model_intents || []).length)
  // Pendent (pressupost) = línia SENSE cap intent (decisió a). En tornar del mode selecció, reload()
  // refresca els intents; si en queda alguna pendent, s'ofereix continuar amb la primera.
  const pendingLines = lines.filter(l => (l.model_intents || []).length === 0)

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

  // Sprint C — vincular models va a la superfície universal de selecció (mode intenció): arriba a
  // /models amb propòsit quote_line + prefiltre customer bloquejat, multi-selecciona SENSE sostre
  // (el pressupost no imputa cartera) i torna aquí; el bulk d'intents (H1) ignora els duplicats.
  const goSelect = (lineId) => {
    const params = new URLSearchParams({
      select_for: `quote_line:${lineId}`,
      customer: String(quote.customer),
      return: location.pathname + location.search,
    })
    navigate(`/models?${params.toString()}`)
  }
  const delIntent = (iid) => {
    setBusy(true)
    commerce.quoteLineIntents.remove(iid).then(() => reload()).then(() => ok(t('quotes.intent_removed'))).catch(err).finally(() => setBusy(false))
  }

  const columns = [
    { key: 'desc', label: t('quotes.col_concept'), render: l => l.description || l.product_name },
    { key: 'qty', label: t('quotes.col_qty'), align: 'right', width: 90,
      render: l => <span style={{ fontFamily: MONO, color: 'var(--text-muted)' }}>×{Number(l.quantity).toFixed(2)}</span> },
    { key: 'price', label: t('quotes.col_unit_price'), align: 'right', width: 110,
      render: l => <span style={{ fontFamily: MONO }}>{money(l.unit_price)}</span> },
    { key: 'total', label: t('quotes.col_total'), align: 'right', width: 100,
      render: l => <span style={{ fontFamily: MONO, fontWeight: 600 }}>{money(l.line_total)}</span> },
  ]
  const renderActions = editable ? (l) => (
    <RowBtn icon="ti-trash" danger disabled={busy} title={t('quotes.remove')} onClick={() => del(l.id)} />
  ) : undefined

  return (
    <Section title={t('quotes.lines')} hint={t('quotes.lines_hint')}>
      {lines.length === 0
        ? <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)' }}>{t('quotes.lines_empty')}</p>
        : <LineTable columns={columns} rows={lines} renderActions={renderActions} />}

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

      {/* E6 — vincle preparatori: models previstos per línia. Editable en DRAFT/SENT; read-only en ACCEPTED. */}
      {lines.length > 0 && (canIntents || anyIntent) && (
        <div style={{ marginTop: 16, borderTop: '0.5px solid var(--gray-l)', paddingTop: 12 }}>
          <p style={{ fontSize: 'var(--fs-body)', fontFamily: MONO, fontWeight: 600, marginBottom: 2 }}>{t('quotes.intents_title')}</p>
          <p style={{ fontSize: 'var(--fs-label)', color: 'var(--gray)', marginBottom: 10 }}>{t('quotes.intents_hint')}</p>
          {canIntents && pendingLines.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', margin: '0 0 10px',
              padding: '8px 14px', background: 'var(--gold-pale)', border: '0.5px solid var(--gold)', borderRadius: 8,
              fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-main)' }}>
              <i className="ti ti-arrow-back-up" aria-hidden="true" />
              <span>{t('quotes.pending_lines', { n: pendingLines.length })}</span>
              <button onClick={() => goSelect(pendingLines[0].id)}
                style={{ ...smallBtn, cursor: 'pointer', color: 'var(--gold)', border: '0.5px solid var(--gold)', fontWeight: 600 }}>
                {t('quotes.continue_selecting')}
              </button>
            </div>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {lines.map(l => {
              const intents = l.model_intents || []
              const over = intents.length > Number(l.quantity || 0)
              return (
                <div key={l.id} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 'var(--fs-body)', minWidth: 140, flexShrink: 0 }}>
                    {l.description || l.product_name}
                    <span style={{ fontFamily: MONO, color: 'var(--text-muted)', marginLeft: 6 }}>×{Number(l.quantity).toFixed(0)}</span>
                  </span>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                    {intents.length === 0 && !canIntents &&
                      <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--gray)' }}>{t('quotes.intents_none')}</span>}
                    {intents.map(mi => (
                      <span key={mi.id} style={intentChip} title={mi.model_nom || ''}>
                        {mi.model_codi}
                        {canIntents && <i className="ti ti-x" title={t('quotes.intent_remove')}
                          onClick={() => !busy && delIntent(mi.id)} style={{ cursor: 'pointer', fontSize: 12 }} />}
                      </span>
                    ))}
                    {canIntents && (
                      <button onClick={() => goSelect(l.id)} disabled={busy}
                        style={{ ...smallBtn, color: 'var(--gold)', borderColor: 'var(--gold)' }}>
                        <i className="ti ti-link" style={{ fontSize: 13, marginRight: 4 }} />{t('quotes.intent_add')}
                      </button>
                    )}
                    {over && (
                      <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--gold)' }}>
                        <i className="ti ti-alert-triangle" style={{ fontSize: 12, marginRight: 3 }} />
                        {t('quotes.intents_over', { n: intents.length, q: Number(l.quantity).toFixed(0) })}
                      </span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

    </Section>
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
