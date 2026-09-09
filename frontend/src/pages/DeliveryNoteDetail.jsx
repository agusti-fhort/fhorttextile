import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams, useNavigate } from 'react-router-dom'
import useAuthStore from '../store/auth'
import { commerce } from '../api/endpoints'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import { ClassificacioBadge } from '../components/commercial/estats'
import Badge from '../components/ui/Badge'
import PageMenu from '../components/ui/PageMenu'
import { camp, forceBarra } from '../components/llista/ChromLlista'
import PdfButton, { usePdfLang } from '../components/ui/PdfButton'
import IssueDateField from '../components/commercial/IssueDateField'
import { botoPri } from '../components/ui/buttons'
import { DocumentHeader, ModelCard, LineTable, RowBtn, DocumentSummary } from '../components/commercial'
import { DNStatusBadge } from './DeliveryNotes'

// Mòdul Comercial — v2 · fitxa/composició d'albarà (reskin: sistema visual comercial unificat).
// Es compon per MODEL des de la safata d'albaranables del client (tasques Done + extres + despeses +
// deduccions, seleccionats per check). Blocs per model amb capçalera i subtotal; l'ull commuta la
// visibilitat (les línies amagades no compten al total ni surten al PDF). Cicle DRAFT→ISSUED
// (congela)→INVOICED. Comportament INTACTE respecte v2; només canvia el markup (components compartits).
const MONO = 'IBM Plex Mono, monospace'
const smallBtn = {
  background: 'none', borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--line)', borderRadius: 6, cursor: 'pointer',
  padding: '4px 9px', fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-soft)',
  display: 'inline-flex', alignItems: 'center', gap: 4,
}
const inp = { ...camp, minWidth: 0 }
const money = (v) => `${Number(v ?? 0).toFixed(2)} €`
// ⚠️ `line_kind` I `kind` SÓN EL MATEIX VOCABULARI AMB DOS NOMS SEGONS D'ON VE LA FILA: la
// línia DESADA el porta a `line_kind` (`commerce/models.py:752`) i l'ítem PROPOSAT per la
// safata, a `kind`. No és un error: són dues formes, la del model i la del càlcul. Es diu aquí
// perquè un mapa keyed pel nom equivocat no falla — simplement pinta tothom neutre, i això
// s'assembla massa a estar bé.

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

// Agrupa les línies per model (les MANUAL/sense model van a un bloc "general" final).
function groupByModel(lines) {
  const blocks = new Map()
  for (const l of lines) {
    const key = l.model ?? '__general__'
    if (!blocks.has(key)) blocks.set(key, { model: l.model, header: l, lines: [] })
    blocks.get(key).lines.push(l)
  }
  return [...blocks.values()]
}

// M4 · FIT-12 — LA SAFATA S'AGRUPA PER VOLTA. El backend ja envia la volta amb cada ítem
// (`it.ronda`) i l'índex ordenat del bloc (`g.rondes`); aquí només es reparteix. Els ítems que no
// pengen de cap volta —despeses, deduccions de concepte lliure, i tota la feina anterior a la llei
// de rondes— van a un calaix SENSE capçalera, que és el que la safata ja era abans d'M4: no se'ls
// inventa cap volta.
// ── SAFATA · MAQUETA §1 ────────────────────────────────────────────────────────────────────
//
// La unitat és el MODEL (A1) i el que es marca és un BLOC de voltes (A7): el bloc del PACTE amb
// les voltes que hi caben, i un bloc PROPI per cada volta que en surt. Les targetes de tasca
// se'n van senceres — el preu d'un model no és la suma dels preus de les seves tasques.

const fmtData = (iso, locale) => (iso
  // La data va amb el LOCALE de l'app, no amb el del navegador: `toLocaleDateString()` pelat
  // pinta 8/25/2026 al Chromium headless (mesurat) i pintaria el que el navegador de cadascú
  // digués a producció, dins d'una pantalla que ja està en català.
  ? new Date(iso).toLocaleDateString(locale || 'ca', { day: '2-digit', month: '2-digit', year: 'numeric' })
  : null)

// `.mhead` de la maqueta: nom 14/600 · refs en caption soft · línia de context · badge a la dreta.
function CapcaleraModelSafata({ g, t, locale }) {
  const m = g.model
  const p = g.pacte
  const refs = [m.codi_client, m.codi_intern].filter(Boolean).join(' · ')
  const context = [
    m.collection, [m.temporada, m.any].filter(Boolean).join(' '),
    p?.oferta && t('deliverynotes.tray_oferta', { n: p.oferta }),
    p?.concepte,
    p?.rounds_included != null && t('deliverynotes.tray_rondes_incloses', { n: p.rounds_included }),
  ].filter(Boolean).join(' · ')
  // A2 · EL VERD DEL VIST-I-PLAU INFORMA, NO BLOQUEJA. Verd només quan TOTES les voltes
  // entregades d'aquest model porten l'OK del client: així el verd vol dir «pots facturar això
  // sabent que el client ho ha donat per bo», que és per al que serveix. Amb un «alguna» n'hi
  // hauria prou per pintar-lo i no diria res.
  const entregades = (g.blocs || []).flatMap(b => b.rondes).filter(r => r.entregada)
  const totOk = entregades.length > 0 && entregades.every(r => r.data_ok)
  return (
    <div style={{ padding: '12px 16px 4px', display: 'flex', justifyContent: 'space-between',
                  alignItems: 'baseline', gap: 8, borderTop: '1px solid var(--line)' }}>
      <div style={{ minWidth: 0 }}>
        <span style={{ fontSize: 'var(--fs-h3)', lineHeight: '20px', fontWeight: 600 }}>
          {m.nom_prenda || m.codi_intern}
        </span>
        {refs && <span style={{ color: 'var(--text-soft)', fontSize: 'var(--fs-caption)' }}> {refs}</span>}
        {context && <div style={{ color: 'var(--text-soft)' }}>{context}</div>}
      </div>
      <Badge variant={totOk ? 'ok' : 'gray'}>
        {totOk ? t('deliverynotes.tray_vist_i_plau') : t('deliverynotes.tray_vist_i_plau_pendent')}
      </Badge>
    </div>
  )
}

// `.mrow`: casella · «Ronda N · lliurada dd/mm/aaaa» (+ badge --err si va fora) · estat.
//
// 🔑 LA CASELLA ÉS DEL BLOC, NO DE LA VOLTA, encara que es pinti a cada fila. Un bloc del pacte
// és UNA línia d'albarà amb un sol import: no es pot facturar mig bloc, i per això les seves
// voltes es marquen i es desmarquen juntes. La maqueta dibuixa una casella per fila i això no
// canvia; el que canvia és què passa en prémer-la.
function FilaRondaSafata({ r, bloc, marcat, onToggle, t, locale }) {
  const data = fmtData(r.data_lliurament, locale)
  return (
    <label style={{
      display: 'grid', gridTemplateColumns: '16px 1fr auto', gap: 8, alignItems: 'center',
      padding: '8px 16px 8px 32px', borderTop: '1px solid var(--line)',
      cursor: r.entregada ? 'pointer' : 'not-allowed',
    }}>
      <input type="checkbox" checked={marcat} disabled={!r.entregada}
        onChange={() => onToggle(bloc)}
        aria-label={t('deliverynotes.tray_ronda', { n: r.seq })}
        style={{ width: 14, height: 14, accentColor: 'var(--gold)', margin: 0,
                 opacity: r.entregada ? 1 : 0.4 }} />
      <span style={{ minWidth: 0, color: r.entregada ? 'var(--text-main)' : 'var(--text-faint)' }}>
        {t('deliverynotes.tray_ronda', { n: r.seq })}
        {data && <span style={{ color: 'var(--text-soft)' }}> · {t('deliverynotes.tray_lliurada', { data })}</span>}
        {/* A7 — el badge --err de la volta fora de pacte. No és una classificació neutra: diu
            que això es factura a part i sense pressupost, que és el que el comercial ha de
            veure abans de posar-hi un preu. */}
        {r.fora_de_comanda && (
          <> <Badge variant="err">{t('deliverynotes.tray_fora_pressupost')}</Badge></>
        )}
      </span>
      <Badge variant={r.entregada ? 'ok' : 'gray'}>
        {r.entregada ? t('deliverynotes.tray_entregada') : t('deliverynotes.tray_en_curs')}
      </Badge>
    </label>
  )
}

export default function DeliveryNoteDetail() {
  const { t, i18n } = useTranslation()
  const { id } = useParams()
  const navigate = useNavigate()
  const me = useAuthStore(s => s.user)
  const canConfigure = !!me?.capabilities?.includes('configure')

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [dn, setDn] = useState(null)
  // Idioma del PDF: default = el del client destinatari, canviable per document.
  const [pdfLang, setPdfLang] = usePdfLang(dn?.customer_language)
  const [feedback, setFeedback] = useState(null)
  const [busy, setBusy] = useState(false)
  const [edits, setEdits] = useState({})          // lineId → {unit_price, description, quantity}
  const [confirmIssue, setConfirmIssue] = useState(false)
  // Safata d'albaranables (afegir ítems al DRAFT)
  const [trayOpen, setTrayOpen] = useState(false)
  const [tray, setTray] = useState(null)          // {groups:[…]}
  const [trayBusy, setTrayBusy] = useState(false)
  const [picked, setPicked] = useState(() => new Set())   // "kind:id"

  const reload = useCallback(() => commerce.deliveryNotes.get(id)
    .then(res => { setDn(res.data); setEdits({}) }).catch(() => setError(true)), [id])

  useEffect(() => {
    let alive = true
    commerce.deliveryNotes.get(id)
      .then(res => { if (alive) setDn(res.data) })
      .catch(() => { if (alive) setError(true) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [id])

  const isDraft = dn?.status === 'DRAFT'
  const isIssued = dn?.status === 'ISSUED'
  const editable = isDraft && canConfigure
  // La data d'emissió es corregeix en DRAFT i ISSUED (l'emissió és seva); INVOICED ja s'ha
  // presentat al client. El guard dur el posa el backend (serializers.guard_issued_at_editable).
  const canEditDate = canConfigure && (isDraft || isIssued)

  const saveIssuedAt = (value) => {
    setFeedback(null)
    return commerce.deliveryNotes.update(id, { issued_at: value })
      .then(reload).then(() => setFeedback({ type: 'ok', text: t('deliverynotes.saved') }))
      .catch(err => setFeedback({ type: 'err', text: err?.response?.data?.detail || t('deliverynotes.error') }))
  }

  const editVal = (line, field) => {
    const e = edits[line.id]
    if (e && e[field] !== undefined) return e[field]
    if (field === 'unit_price') return String(line.unit_price ?? '')
    if (field === 'quantity') return String(line.quantity ?? '')
    return line.description ?? ''
  }
  const setEdit = (lineId, field, value) =>
    setEdits(prev => ({ ...prev, [lineId]: { ...prev[lineId], [field]: value } }))

  const saveLine = (line) => {
    const e = edits[line.id]
    if (!e) return
    const payload = {}
    if (e.unit_price !== undefined && e.unit_price !== String(line.unit_price ?? '')) payload.unit_price = e.unit_price === '' ? '0' : e.unit_price
    if (e.quantity !== undefined && e.quantity !== String(line.quantity ?? '')) payload.quantity = e.quantity === '' ? '0' : e.quantity
    if (e.description !== undefined && e.description !== (line.description ?? '')) payload.description = e.description
    if (Object.keys(payload).length === 0) return
    setBusy(true); setFeedback(null)
    commerce.deliveryNoteLines.update(line.id, payload)
      .then(reload).then(() => setFeedback({ type: 'ok', text: t('deliverynotes.line_saved') }))
      .catch(err => setFeedback({ type: 'err', text: err?.response?.data?.detail || t('deliverynotes.line_error') }))
      .finally(() => setBusy(false))
  }

  const toggleVisible = (line) => {
    setBusy(true); setFeedback(null)
    commerce.deliveryNoteLines.update(line.id, { visible: !line.visible })
      .then(reload)
      .catch(err => setFeedback({ type: 'err', text: err?.response?.data?.detail || t('deliverynotes.line_error') }))
      .finally(() => setBusy(false))
  }

  const removeLine = (line) => {
    setBusy(true); setFeedback(null)
    commerce.deliveryNoteLines.remove(line.id)
      .then(reload)
      .catch(err => setFeedback({ type: 'err', text: err?.response?.data?.detail || t('deliverynotes.line_error') }))
      .finally(() => setBusy(false))
  }

  const addComment = () => {
    setBusy(true); setFeedback(null)
    commerce.deliveryNoteLines.create({ delivery_note: dn.id, description: t('deliverynotes.comment_placeholder'), quantity: 0, unit_price: 0 })
      .then(reload)
      .catch(err => setFeedback({ type: 'err', text: err?.response?.data?.detail || t('deliverynotes.line_error') }))
      .finally(() => setBusy(false))
  }

  // ── Safata ──
  const openTray = () => {
    setTrayOpen(true); setPicked(new Set()); setTray(null)
    commerce.deliveryNotes.billable({ customer: dn.customer })
      .then(res => setTray(res.data))
      .catch(() => setTray({ groups: [] }))
  }
  // La clau de tria és `<model>:<clau del bloc>` — exactament el que el backend espera. No es
  // deriva de cap ronda: el bloc és la unitat i marcar-ne una volta marca el bloc sencer.
  const blocKey = (g, b) => `${g.model.id}:${b.clau}`
  const togglePick = (k) => setPicked(prev => {
    const n = new Set(prev)
    if (n.has(k)) n.delete(k); else n.add(k)
    return n
  })
  const addPicked = () => {
    const items = []
    for (const g of (tray?.groups || [])) for (const b of (g.blocs || [])) {
      if (picked.has(blocKey(g, b))) items.push({ model_id: g.model.id, clau: b.clau })
    }
    if (items.length === 0) { setTrayOpen(false); return }
    setTrayBusy(true); setFeedback(null)
    commerce.deliveryNotes.addLines(dn.id, { items })
      .then(reload)
      .then(() => { setTrayOpen(false); setFeedback({ type: 'ok', text: t('deliverynotes.tray_added', { n: items.length }) }) })
      .catch(err => setFeedback({ type: 'err', text: err?.response?.data?.detail || t('deliverynotes.tray_error') }))
      .finally(() => setTrayBusy(false))
  }

  const doIssue = () => {
    setBusy(true); setFeedback(null)
    commerce.deliveryNotes.issue(id)
      .then(() => { setConfirmIssue(false); return reload() })
      .then(() => setFeedback({ type: 'ok', text: t('deliverynotes.issued_ok') }))
      .catch(err => setFeedback({ type: 'err', text: err?.response?.data?.detail || t('deliverynotes.issue_error') }))
      .finally(() => setBusy(false))
  }

  const doMarkInvoiced = () => {
    setBusy(true); setFeedback(null)
    commerce.deliveryNotes.markInvoiced(id)
      .then(reload).then(() => setFeedback({ type: 'ok', text: t('deliverynotes.invoiced_ok') }))
      .catch(err => setFeedback({ type: 'err', text: err?.response?.data?.detail || t('deliverynotes.invoice_error') }))
      .finally(() => setBusy(false))
  }

  const doPdf = () => {
    commerce.deliveryNotes.pdf(id, pdfLang)
      .then(res => downloadBlob(res.data, filenameFromHeaders(res, `${dn?.document_number || 'albara'}.pdf`)))
      .catch(() => setFeedback({ type: 'err', text: t('deliverynotes.pdf_error') }))
  }

  const doDelete = () => {
    if (!window.confirm(t('deliverynotes.delete_confirm'))) return
    setBusy(true)
    commerce.deliveryNotes.remove(id)
      .then(() => navigate('/comercial/albarans'))
      .catch(err => { setFeedback({ type: 'err', text: err?.response?.data?.detail || t('deliverynotes.delete_error') }); setBusy(false) })
  }

  const blocks = useMemo(() => groupByModel(dn?.lines || []), [dn])

  if (loading) return <Center>{t('deliverynotes.loading')}</Center>
  if (error || !dn) return <Center>{t('deliverynotes.error')}</Center>

  const lines = dn.lines || []
  const visibleCount = lines.filter(l => l.visible).length
  const internalTotal = lines.reduce((s, l) => s + (l.internal_cost != null ? Number(l.internal_cost) : 0), 0)
  const hasInternal = lines.some(l => l.internal_cost != null || l.internal_minutes != null)
  const internalLabels = { time: t('deliverynotes.line_time'), tecnic: t('deliverynotes.line_tecnic'), cost: t('deliverynotes.line_cost') }

  // Columnes de línia (sistema unificat). Cel·les editables amb el patró save-on-blur (INTACTE).
  const columns = [
    { key: 'kind', label: t('deliverynotes.line_kind'),
      render: l => <ClassificacioBadge>{t(`deliverynotes.kind_${l.line_kind}`)}</ClassificacioBadge> },
    { key: 'desc', label: t('deliverynotes.line_desc'),
      render: l => editable
        ? <input value={editVal(l, 'description')} disabled={busy}
            onChange={e => setEdit(l.id, 'description', e.target.value)} onBlur={() => saveLine(l)}
            style={{ ...inp, width: '100%' }} />
        : (l.description || l.product_name || '—') },
    { key: 'qty', label: t('deliverynotes.line_qty'), align: 'right', width: 90,
      render: l => editable
        ? <input type="number" step="0.01" value={editVal(l, 'quantity')} disabled={busy}
            onChange={e => setEdit(l.id, 'quantity', e.target.value)} onBlur={() => saveLine(l)}
            style={{ ...inp, width: 70, textAlign: 'right' }} />
        : <span style={{ fontFamily: MONO, color: 'var(--text-soft)' }}>{Number(l.quantity ?? 0)}</span> },
    { key: 'price', label: t('deliverynotes.line_price'), align: 'right', width: 110,
      render: l => editable
        ? <input type="number" step="0.01" value={editVal(l, 'unit_price')} disabled={busy}
            onChange={e => setEdit(l.id, 'unit_price', e.target.value)} onBlur={() => saveLine(l)}
            style={{ ...inp, width: 100, textAlign: 'right' }} />
        : <span style={{ fontFamily: MONO }}>{money(l.unit_price)}</span> },
    { key: 'total', label: t('deliverynotes.line_total'), align: 'right', width: 100,
      render: l => <span style={{ fontFamily: MONO, color: Number(l.line_total ?? 0) < 0 ? 'var(--err)' : 'inherit' }}>{money(l.line_total)}</span> },
  ]

  const renderActions = editable ? (l) => (
    <>
      <RowBtn icon={l.visible ? 'ti-eye' : 'ti-eye-off'} active={l.visible} disabled={busy}
        title={l.visible ? t('deliverynotes.hide') : t('deliverynotes.show')} onClick={() => toggleVisible(l)} />
      <RowBtn icon="ti-x" danger disabled={busy}
        title={t('deliverynotes.remove_line')} onClick={() => removeLine(l)} />
    </>
  ) : undefined

  // Barra d'accions de la capçalera (segons el sistema de la casa; mai text pla).
  const headerActions = (
    <>
      <PdfButton label={t('deliverynotes.download_pdf')} onClick={doPdf}
        lang={pdfLang} onLangChange={setPdfLang} t={t} />
      {editable && (
        <button onClick={openTray} disabled={busy} style={smallBtn}>
          <i className="ti ti-inbox" style={{ fontSize: 14 }} />{t('deliverynotes.tray_action')}
        </button>
      )}
      {editable && (
        <button onClick={addComment} disabled={busy} style={smallBtn}>
          <i className="ti ti-message-plus" style={{ fontSize: 14 }} />{t('deliverynotes.add_comment')}
        </button>
      )}
      {editable && (
        <button onClick={() => setConfirmIssue(true)} disabled={busy || visibleCount === 0} style={botoPri}>
          <i className="ti ti-send" style={{ fontSize: 14 }} />{t('deliverynotes.issue_action')}
        </button>
      )}
      {isIssued && canConfigure && (
        <button onClick={doMarkInvoiced} disabled={busy} style={botoPri}>
          <i className="ti ti-checkbox" style={{ fontSize: 14 }} />{t('deliverynotes.mark_invoiced')}
        </button>
      )}
      {editable && (
        <button onClick={doDelete} disabled={busy} style={smallBtn} title={t('deliverynotes.delete')}>
          <i className="ti ti-trash" style={{ fontSize: 13 }} />
        </button>
      )}
    </>
  )

  return (
    <>
      {/* §8b.2 · MENÚ DE PANTALLA. El botó-fletxa solt de sobre el títol se'n va: la fletxa té
          UN lloc a tot el producte, i és aquest. El destí és EXPLÍCIT — mai `history.back()`,
          que no pot garantir on porta si s'hi ha arribat per enllaç, per recàrrega o per una
          pestanya nova. */}
      <div style={forceBarra}>
        <PageMenu backTo="/comercial/albarans" backTitle={t('deliverynotes.back')} />
      </div>

      <div style={{ minWidth: 0, maxWidth: 1000 }}>

      <DocumentHeader
        reference={dn.document_number}
        statusBadge={<DNStatusBadge status={dn.status} t={t} />}
        customer={<>{dn.customer_nom}{dn.invoiced_at && <> · {t('deliverynotes.invoiced_on')} {String(dn.invoiced_at).slice(0, 10)}</>}</>}
        actions={headerActions}
      />

      <div style={{ marginTop: 12 }}>
        <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />
      </div>

      {/* Data d'emissió: l'albarà no en tenia superfície. Corregible en DRAFT i ISSUED. */}
      <div style={{ marginTop: 12 }}>
        <IssueDateField value={dn.issued_at} editable={canEditDate} onSave={saveIssuedAt} t={t} />
      </div>

      {/* Blocs per model */}
      {lines.length === 0 && (
        <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)', margin: '18px 0' }}>{t('deliverynotes.empty_lines')}</p>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14, margin: '16px 0' }}>
        {blocks.map(block => {
          const subtotal = block.lines.filter(l => l.visible).reduce((s, l) => s + Number(l.line_total ?? 0), 0)
          const dates = block.lines.map(l => l.task_finished_at).filter(Boolean).sort()
          const deliveredAt = dates.length ? dates[dates.length - 1].slice(0, 10) : null
          const h = block.header
          const showClient = h.model_codi_client && h.model_codi_client !== h.model_intern
          const metaParts = []
          if (showClient) metaParts.push(h.model_codi_client)
          const camp = [h.model_collection, h.model_temporada, h.model_any].filter(Boolean).join(' · ')
          if (camp) metaParts.push(camp)
          if (deliveredAt) metaParts.push(`${t('deliverynotes.delivered_at')} ${deliveredAt}`)
          const rows = block.lines.map(l => ({
            ...l,
            internal: {
              minutes: l.internal_minutes,
              tecnic: l.internal_tecnic,
              cost: l.internal_cost != null ? money(l.internal_cost) : '—',
            },
          }))
          return (
            <ModelCard key={block.model ?? 'general'}
              reference={block.model ? h.model_intern : undefined}
              name={block.model ? (h.model_nom || h.model_intern) : t('deliverynotes.general_block')}
              meta={metaParts.join(' · ') || undefined}
              subtotalLabel={t('deliverynotes.model_subtotal')} subtotal={money(subtotal)}>
              <LineTable columns={columns} rows={rows} renderActions={renderActions}
                showInternal={hasInternal} internalLabels={internalLabels}
                rowStyle={l => ({ opacity: l.visible === false ? 0.4 : 1 })} />
            </ModelCard>
          )
        })}
      </div>

      {/* Resum del document (contenidor propi separat + cost intern al peu) */}
      <DocumentSummary
        lines={[
          { label: t('deliverynotes.subtotal'), value: money(dn.subtotal) },
          { label: t('deliverynotes.tax'), value: money(dn.tax_amount) },
          { label: t('deliverynotes.total'), value: money(dn.total), strong: true },
        ]}
        showInternal={hasInternal}
        internalLabel={t('deliverynotes.internal_cost_foot')}
        internalValue={money(internalTotal)}
      />

      {/* Safata d'albaranables */}
      {trayOpen && (
        <div onClick={() => !trayBusy && setTrayOpen(false)} style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 50, padding: 16,
        }}>
          <div onClick={e => e.stopPropagation()} style={{
            background: 'var(--panel)', borderRadius: 'var(--r-card)', padding: '1.2rem 1.4rem',
            maxWidth: 720, width: '100%', maxHeight: '85vh', overflowY: 'auto', borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--line)',
          }}>
            <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>
              {t('deliverynotes.tray_title')}
            </h2>
            <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)', marginBottom: 14 }}>
              {t('deliverynotes.tray_hint')}
            </p>
            {!tray ? <Center>{t('deliverynotes.loading')}</Center>
              : (tray.groups || []).length === 0 ? <div style={{ color: 'var(--text-soft)', padding: '10px 0' }}>{t('deliverynotes.tray_empty')}</div>
                : (tray.groups.map(g => (
                  <div key={g.model.id}>
                    <CapcaleraModelSafata g={g} t={t} locale={i18n.language} />
                    {/* Les files separades NOMÉS pel filet `--line` de cada fila (maqueta §1):
                        cap fons alternat, cap caixa per volta. */}
                    {(g.blocs || []).map(b => b.rondes.map(r => (
                      <FilaRondaSafata key={r.id} r={r} bloc={blocKey(g, b)}
                        marcat={picked.has(blocKey(g, b))} onToggle={togglePick}
                        t={t} locale={i18n.language} />
                    )))}
                  </div>
                )))}
            <div style={{ display: 'flex', gap: 8, marginTop: 12, position: 'sticky', bottom: 0, background: 'var(--panel)', paddingTop: 8 }}>
              <button onClick={addPicked} disabled={trayBusy || picked.size === 0} style={botoPri}>
                {t('deliverynotes.tray_add', { n: picked.size })}
              </button>
              <button onClick={() => setTrayOpen(false)} disabled={trayBusy} style={smallBtn}>{t('deliverynotes.issue_cancel')}</button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmació d'emissió */}
      {confirmIssue && (
        <div onClick={() => setConfirmIssue(false)} style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 50, padding: 16,
        }}>
          <div onClick={e => e.stopPropagation()} style={{
            background: 'var(--panel)', borderRadius: 'var(--r-card)', padding: '1.2rem 1.4rem',
            maxWidth: 460, width: '100%', borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--line)',
          }}>
            <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, marginBottom: 10, fontFamily: MONO }}>
              {t('deliverynotes.issue_title')}
            </h2>
            <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)', marginBottom: 16 }}>
              {t('deliverynotes.issue_warning')}
            </p>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={doIssue} disabled={busy} style={botoPri}>{t('deliverynotes.issue_confirm')}</button>
              <button onClick={() => setConfirmIssue(false)} disabled={busy} style={smallBtn}>{t('deliverynotes.issue_cancel')}</button>
            </div>
          </div>
        </div>
      )}
      </div>
    </>
  )
}
