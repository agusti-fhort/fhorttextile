import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams, useNavigate } from 'react-router-dom'
import useAuthStore from '../store/auth'
import { commerce, modelTasks } from '../api/endpoints'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import Badge from '../components/ui/Badge'
import PageMenu from '../components/ui/PageMenu'
import { camp, forceBarra } from '../components/llista/ChromLlista'
import PdfButton, { usePdfLang } from '../components/ui/PdfButton'
import IssueDateField from '../components/commercial/IssueDateField'
import { botoDestructiu, botoPri } from '../components/ui/buttons'
import { DocumentHeader } from '../components/commercial'
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
// M4 · FIT-12 — LA SAFATA S'AGRUPA PER VOLTA. El backend ja envia la volta amb cada ítem
// (`it.ronda`) i l'índex ordenat del bloc (`g.rondes`); aquí només es reparteix. Els ítems que no
// pengen de cap volta —despeses, deduccions de concepte lliure, i tota la feina anterior a la llei
// de rondes— van a un calaix SENSE capçalera, que és el que la safata ja era abans d'M4: no se'ls
// inventa cap volta.
// ── PANTALLA D'ALBARÀ · MAQUETA §2 ─────────────────────────────────────────────────────────

const fmtMin = (m) => `${Math.floor((m || 0) / 60)}h ${String((m || 0) % 60).padStart(2, '0')}m`

// La taula de tasques d'una volta. COST/H és un input (A3) i el cost es recalcula al servidor:
// aquí no s'inventa cap número. L'entrada NOMÉS existeix en esborrany.
function TaulaTasquesRonda({ r, editable, busy, onRate, t }) {
  const th = { textAlign: 'left', fontWeight: 500, color: 'var(--text-soft)',
               fontSize: 'var(--fs-caption)', lineHeight: '12px', letterSpacing: '.08em',
               textTransform: 'uppercase', padding: '4px 8px',
               borderBottom: '1px solid var(--line)' }
  const td = { padding: '4px 8px', borderBottom: '1px solid var(--line)' }
  const tdR = { ...td, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }
  const totalMin = r.tasques.reduce((a, x) => a + (x.feta ? x.minuts : 0), 0)
  const totalCost = r.tasques.reduce((a, x) => a + (x.feta ? Number(x.cost || 0) : 0), 0)
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--fs-body)',
                    lineHeight: '16px' }}>
      <thead>
        <tr>
          <th style={th}>{t('deliverynotes.col_tasca')}</th>
          <th style={th}>{t('deliverynotes.col_tecnic')}</th>
          <th style={{ ...th, textAlign: 'right' }}>{t('deliverynotes.col_temps')}</th>
          <th style={{ ...th, textAlign: 'right' }}>{t('deliverynotes.col_cost_hora')}</th>
          <th style={{ ...th, textAlign: 'right' }}>{t('deliverynotes.col_cost')}</th>
        </tr>
      </thead>
      <tbody>
        {r.tasques.map(x => (
          <tr key={x.id}>
            <td style={td}>
              {x.nom}
              {/* Una tasca de la recepta que no s'ha fet NO desapareix de la volta: el client
                  ha de poder veure què s'havia previst i què no s'ha executat. */}
              {!x.feta && <> <Badge variant="err">{t('deliverynotes.no_realitzada')}</Badge></>}
            </td>
            <td style={{ ...td, color: x.feta ? 'inherit' : 'var(--text-faint)' }}>
              {x.feta ? (x.tecnic || '—') : '—'}
            </td>
            <td style={{ ...tdR, color: x.feta ? 'inherit' : 'var(--text-faint)' }}>
              {x.feta ? fmtMin(x.minuts) : '—'}
            </td>
            <td style={tdR}>
              {!x.feta ? <span style={{ color: 'var(--text-faint)' }}>—</span>
                : editable ? (
                  <input type="number" step="0.01" defaultValue={x.cost_hora ?? ''} disabled={busy}
                    onBlur={e => onRate(x, e.target.value)}
                    aria-label={t('deliverynotes.col_cost_hora')}
                    style={{ ...inp, width: 72, textAlign: 'right', fontSize: 'var(--fs-body)' }} />
                ) : (x.cost_hora != null ? money(x.cost_hora) : '—')}
            </td>
            <td style={{ ...tdR, color: x.feta ? 'inherit' : 'var(--text-faint)' }}>
              {x.feta && x.cost != null ? money(x.cost) : '—'}
            </td>
          </tr>
        ))}
        <tr>
          <td style={{ ...td, borderBottom: 0, fontWeight: 600 }} colSpan={2}>
            {t('deliverynotes.cost_ronda')}
          </td>
          <td style={{ ...tdR, borderBottom: 0, fontWeight: 600 }}>{fmtMin(totalMin)}</td>
          <td style={{ ...tdR, borderBottom: 0 }} />
          <td style={{ ...tdR, borderBottom: 0, fontWeight: 600 }}>{money(totalCost)}</td>
        </tr>
      </tbody>
    </table>
  )
}

// La targeta d'una LÍNIA = un model (A1) o una volta directa (A7). El que canvia entre les dues
// és la línia de pacte i el badge; l'estructura és la mateixa, i per això és UN component.
// Les menes de línia que NO són una targeta de voltes: el seu concepte, quan l'origen no en
// porta cap, és el nom del seu tipus. Mateix conjunt que `_EXTRA_LABEL` del generador de PDF.
const KINDS_EXTRA = new Set(['EXTRA', 'DEDUCTION', 'EXPENSE'])

function TargetaLinia({ l, editable, busy, importEdit, onImport, onImportSave, onEsborrar,
                        onRate, t, locale }) {
  const refs = [l.model_codi_client, l.model_intern].filter(Boolean).join(' · ')
  const camp = [l.model_collection, [l.model_temporada, l.model_any].filter(Boolean).join(' ')]
    .filter(Boolean).join(' · ')
  return (
    // 🚨 LA MIDA ES DECLARA AL CONTENIDOR. Sense `fontSize`, la targeta computa els 16px del
    // document i qualsevol fill sense mida pròpia hi neix — el mateix defecte que la mesura ja
    // va caçar a `TaulaLlista` i al `stateBox` del dashboard. La bidireccional el va tornar a
    // trobar aquí (maqueta 12px · pantalla 16px) i no es veia llegint el codi: el que falla és
    // el que NO hi ha escrit.
    <div style={{ background: 'var(--panel)', border: '1px solid var(--line)',
                  borderRadius: 'var(--r-card)', marginBottom: 16, overflow: 'hidden',
                  fontFamily: MONO, fontSize: 'var(--fs-body)', lineHeight: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, padding: 16 }}>
        <div style={{ lineHeight: '16px', minWidth: 0 }}>
          <span style={{ fontSize: 'var(--fs-h3)', lineHeight: '20px', fontWeight: 600 }}>
            {l.model_nom || l.model_intern || l.description}
          </span>
          {refs && <span style={{ color: 'var(--text-soft)', fontSize: 'var(--fs-caption)' }}> {refs}</span>}
          {/* A7 · el badge --err va a la capçalera de la targeta directa, al costat de la
              identitat: és el primer que s'ha de llegir d'aquesta targeta. */}
          {l.encarrec_directe && <> <Badge variant="err">{t('deliverynotes.tray_fora_pressupost')}</Badge></>}
          {camp && <div style={{ color: 'var(--text-soft)' }}>{camp}</div>}
          <div>
            {l.encarrec_directe
              ? <b style={{ fontWeight: 600 }}>{t('deliverynotes.encarrec_directe')}</b>
              /* 🔑 EL SEPARADOR NO POT ANAR ENGANXAT AL TROS. Amb `{x && <> · {x}</>}` per cada
                 peça, una línia sense pacte —tot un extra n'és una— començava per « · » orfe: el
                 separador el posava el segon tros i no el fet que n'hi hagués un abans. Ara les
                 peces es componen i el separador viu ENTRE elles.
                 Sense cap peça (un extra sense descripció) el concepte és el seu TIPUS, dit
                 aquí i en l'idioma de la pantalla. */
              : <>
                  {l.pacte_oferta && <b style={{ fontWeight: 600 }}>{t('deliverynotes.tray_oferta', { n: l.pacte_oferta })}</b>}
                  {[
                    l.description,
                    l.pacte_rounds != null ? t('deliverynotes.tray_rondes_incloses', { n: l.pacte_rounds }) : null,
                    l.pacte_consum,
                  ].filter(Boolean).map((tros, i) => (
                    <span key={i}>{(i > 0 || l.pacte_oferta) ? ' · ' : ''}{tros}</span>
                  ))}
                  {!l.pacte_oferta && !l.description && KINDS_EXTRA.has(l.line_kind)
                    && t(`deliverynotes.kind_${l.line_kind}`)}
                </>}
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, alignSelf: 'flex-start' }}>
          {editable ? (
            <input type="number" step="0.01" value={importEdit} disabled={busy}
              onChange={e => onImport(l, e.target.value)} onBlur={() => onImportSave(l)}
              aria-label={t('deliverynotes.line_import')}
              style={{ ...inp, width: 96, textAlign: 'right', fontSize: 'var(--fs-h3)',
                       lineHeight: '20px', fontWeight: 600 }} />
          ) : (
            <span style={{ fontSize: 'var(--fs-h3)', lineHeight: '20px', fontWeight: 600,
                           fontVariantNumeric: 'tabular-nums' }}>{Number(l.unit_price ?? 0).toFixed(2)}</span>
          )}
          <span>€</span>
          {editable && (
            <button type="button" onClick={() => onEsborrar(l)} disabled={busy}
              title={t('deliverynotes.remove_line')}
              onMouseEnter={e => { e.currentTarget.style.background = 'var(--err-bg)' }}
              onMouseLeave={e => { e.currentTarget.style.background = 'none' }}
              style={{ border: 0, background: 'none', color: 'var(--err)', padding: 4,
                       marginLeft: 8, borderRadius: 'var(--r-ctrl)', cursor: 'pointer',
                       display: 'inline-flex', alignSelf: 'center' }}>
              <i className="ti ti-trash" aria-hidden="true" style={{ fontSize: 14 }} />
            </button>
          )}
        </div>
      </div>
      {(l.rondes_detall || []).map((r, i) => (
        <details key={r.id} open={i === 0} style={{ borderTop: '1px solid var(--line)' }}>
          <summary style={{ cursor: 'pointer', padding: '8px 16px', color: 'var(--text-soft)' }}>
            {t('deliverynotes.tray_ronda', { n: r.seq })}
            {r.data_lliurament && <> · {t('deliverynotes.tray_lliurada', { data: fmtData(r.data_lliurament, locale) })}</>}
          </summary>
          <div style={{ padding: '4px 16px 12px 36px', background: 'var(--panel)' }}>
            <TaulaTasquesRonda r={r} editable={editable} busy={busy} onRate={onRate} t={t} />
          </div>
        </details>
      ))}
    </div>
  )
}

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
  // 🔑 EL BADGE DEL VIST-I-PLAU NOMÉS TÉ SENTIT SI HI HA VOLTES. Un grup que porta només un
  // extra (o una deducció de concepte lliure, que ni tan sols té model) no té cap entrega de
  // què el client pugui haver dit res: pintar-hi «vist-i-plau pendent» seria inventar una
  // espera que no existeix i empènyer el comercial a perseguir-la.
  const teVoltes = (g.blocs || []).some(b => (b.rondes || []).length > 0)
  return (
    <div style={{ padding: '12px 16px 4px', display: 'flex', justifyContent: 'space-between',
                  alignItems: 'baseline', gap: 8, borderTop: '1px solid var(--line)' }}>
      <div style={{ minWidth: 0 }}>
        <span style={{ fontSize: 'var(--fs-h3)', lineHeight: '20px', fontWeight: 600 }}>
          {m.nom_prenda || m.codi_intern || t('deliverynotes.tray_sense_model')}
        </span>
        {refs && <span style={{ color: 'var(--text-soft)', fontSize: 'var(--fs-caption)' }}> {refs}</span>}
        {context && <div style={{ color: 'var(--text-soft)' }}>{context}</div>}
      </div>
      {teVoltes && (
        <Badge variant={totOk ? 'ok' : 'gray'}>
          {totOk ? t('deliverynotes.tray_vist_i_plau') : t('deliverynotes.tray_vist_i_plau_pendent')}
        </Badge>
      )}
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

// `.mrow` també per a l'extra: casella · concepte · import. MATEIX format que la fila de
// volta —una graella de tres columnes separada pel filet `--line`, casella `--gold`— perquè les
// dues coses es marquen igual i han de llegir-se igual.
//
// 🔑 UN EXTRA ES MARCA SOL. La casella d'una fila de volta marca el BLOC sencer (un bloc és una
// línia d'albarà amb un sol import); un extra JA és una línia, o sigui que la seva casella es
// governa a ella mateixa. Per això la clau que viatja és la de l'ítem i no la d'un bloc.
//
// Sense descripció d'origen, el concepte el diu el TIPUS. La paraula es posa AQUÍ, on hi ha
// l'idioma, i no congelada a la columna en crear la línia.
function FilaExtraSafata({ e, clau, marcat, onToggle, t }) {
  return (
    <label style={{
      display: 'grid', gridTemplateColumns: '16px 1fr auto', gap: 8, alignItems: 'center',
      padding: '8px 16px 8px 32px', borderTop: '1px solid var(--line)', cursor: 'pointer',
    }}>
      <input type="checkbox" checked={marcat} onChange={() => onToggle(clau)}
        aria-label={e.descripcio || t(`deliverynotes.kind_${e.kind}`)}
        style={{ width: 14, height: 14, accentColor: 'var(--gold)', margin: 0 }} />
      <span style={{ minWidth: 0 }}>{e.descripcio || t(`deliverynotes.kind_${e.kind}`)}</span>
      <span style={{ fontVariantNumeric: 'tabular-nums' }}>
        {Number(e.preu_proposat ?? 0).toFixed(2)} €
      </span>
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

  // A3 · el cost/hora d'UNA TASCA. Va a la tasca i no a la línia: el cost intern d'aquella hora
  // és el mateix a tot arreu on la tasca aparegui. Buit = torna a la tarifa del tenant.
  const saveRate = (tasca, valor) => {
    const net = String(valor ?? '').trim()
    const nou = net === '' ? null : Number(net)
    if (nou !== null && !Number.isFinite(nou)) return
    if (String(tasca.cost_hora ?? '') === net) return   // res a desar
    setBusy(true); setFeedback(null)
    modelTasks.costHora(tasca.id, nou)
      .then(reload)
      .catch(err => setFeedback({ type: 'err', text: err?.response?.data?.detail || t('deliverynotes.line_error') }))
      .finally(() => setBusy(false))
  }

  // Els comentaris viuen a `DeliveryNote.notes`, que ja existia: cap camp nou i cap migració.
  const saveNotes = (valor) => {
    if ((dn.notes || '') === valor) return
    setBusy(true); setFeedback(null)
    commerce.deliveryNotes.update(dn.id, { notes: valor })
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
  // Mateixa forma per a un extra: el backend només distingeix per la `clau`, i un ítem sense
  // model (una deducció de concepte lliure sobre un col·lector) hi arriba amb `model_id: null`.
  const extraKey = (g, e) => `${g.model.id}:${e.clau}`
  const togglePick = (k) => setPicked(prev => {
    const n = new Set(prev)
    if (n.has(k)) n.delete(k); else n.add(k)
    return n
  })
  const addPicked = () => {
    const items = []
    for (const g of (tray?.groups || [])) {
      for (const b of (g.blocs || [])) {
        if (picked.has(blocKey(g, b))) items.push({ model_id: g.model.id, clau: b.clau })
      }
      for (const e of (g.extres || [])) {
        if (picked.has(extraKey(g, e))) items.push({ model_id: g.model.id, clau: e.clau })
      }
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

  if (loading) return <Center>{t('deliverynotes.loading')}</Center>
  if (error || !dn) return <Center>{t('deliverynotes.error')}</Center>

  const lines = dn.lines || []
  const visibleCount = lines.filter(l => l.visible).length

  // La graella de línies (`columns`/`renderActions`/`LineTable`/`ModelCard`/`DocumentSummary`)
  // se'n va sencera: aquella pantalla llistava TASQUES amb quantitat, descripció editable i un
  // ull de visibilitat. L'A1 diu que la unitat és el MODEL i que l'import és únic i sense camp
  // de quantitat, i l'A7 que el detall es llegeix DINS de cada volta. `TargetaLinia` ho pinta.

  // MAQUETA §2 · a la dreta de la IDENTITAT NOMÉS el que canvia el document: eliminar-lo
  // (secundari amb vora --err) i emetre'l. «Emetre albarà» és l'ÚNIC BLAU de la pantalla —§5:
  // un primari per pantalla, «el que has vingut a fer»— i per això el PDF i el comentari se'n
  // van al menú i la safata s'obre des del [ + Afegir línia ], que és on es demana.
  const headerActions = (
    <>
      {editable && (
        <button onClick={doDelete} disabled={busy} style={botoDestructiu}>
          {t('deliverynotes.delete')}
        </button>
      )}
      {editable && (
        <button onClick={() => setConfirmIssue(true)} disabled={busy || visibleCount === 0} style={botoPri}>
          {t('deliverynotes.issue_action')}
        </button>
      )}
      {isIssued && canConfigure && (
        <button onClick={doMarkInvoiced} disabled={busy} style={botoPri}>
          {t('deliverynotes.mark_invoiced')}
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
      {/* MAQUETA §2 · el menú de pantalla porta ← · Idioma ▾ · Descarregar PDF · Afegir
          comentari, i TOTS A L'ESQUERRA. Abans el PDF i el comentari vivien a la dreta de la
          identitat, barrejats amb «Emetre» i «Eliminar»: allà hi van les accions que canvien el
          DOCUMENT, i descarregar-lo o anotar-lo no el canvien. */}
      <div style={forceBarra}>
        <PageMenu backTo="/comercial/albarans" backTitle={t('deliverynotes.back')}>
          <PdfButton label={t('deliverynotes.download_pdf')} onClick={doPdf}
            lang={pdfLang} onLangChange={setPdfLang} t={t} />
          {/* 🚨 «AFEGIR COMENTARI» SE'N VA. Creava una `DeliveryNoteLine` MANUAL amb un text de
              plantilla, i des que la graella de línies ha marxat aquell text ja no es pot
              editar (no hi ha input de descripció) ni amagar (l'ull de visibilitat també se'n
              va): quedava una targeta gran amb la plantilla, que sortia al PDF i als totals a
              0,00 €. El comentari de l'albarà ara viu a la caixa `Comentaris` del peu, que
              escriu a `notes` i és el que la maqueta §2 demana. */}
        </PageMenu>
      </div>

      {/* Àncora de mesura: el senyal que diu que aquesta pantalla s'ha muntat de debò. */}
      <div data-ftt-screen="albara-pantalla" style={{ minWidth: 0, maxWidth: 1000 }}>

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

      {/* MAQUETA §2 · UNA TARGETA PER LÍNIA. Cada línia ÉS un model (A1) o una volta directa
          (A7), i el bloc directe surt just després del seu model perquè les línies arriben en
          l'ordre en què es van afegir i la safata sempre posa el pacte abans de la directa. */}
      {lines.length === 0 && (
        <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)', margin: '18px 0' }}>{t('deliverynotes.empty_lines')}</p>
      )}
      <div style={{ marginTop: 16 }}>
        {lines.filter(l => l.visible).map(l => (
          <TargetaLinia key={l.id} l={l} editable={editable} busy={busy}
            importEdit={editVal(l, 'unit_price')}
            onImport={(x, v) => setEdit(x.id, 'unit_price', v)}
            onImportSave={saveLine}
            onEsborrar={removeLine}
            onRate={saveRate}
            t={t} locale={i18n.language} />
        ))}
      </div>

      {/* [ + Afegir línia ] — puntejat `--line`. És la porta de la safata: afegir una línia i
          triar un albaranable són el MATEIX gest, i tenir-ne dos botons en llocs diferents feia
          que el de dalt semblés una altra cosa. Desapareix en emès. */}
      {editable && (
        <div role="button" tabIndex={0} onClick={openTray}
          onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') openTray() }}
          style={{ border: '1px dashed var(--line)', borderRadius: 'var(--r-card)', padding: 12,
                   textAlign: 'center', color: 'var(--text-soft)', marginBottom: 16,
                   cursor: 'pointer' }}>
          {t('deliverynotes.add_line')}
        </div>
      )}

      {/* Comentaris a l'ESQUERRA dels totals i alineats PER DALT (maqueta §2). */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 16,
                    alignItems: 'start' }}>
        <div style={{ background: 'var(--panel)', border: '1px solid var(--line)',
                      borderRadius: 'var(--r-card)',
                      fontFamily: MONO, fontSize: 'var(--fs-body)', lineHeight: '16px' }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--line)',
                        fontSize: 'var(--fs-caption)', lineHeight: '12px', letterSpacing: '.08em',
                        textTransform: 'uppercase', color: 'var(--text-soft)' }}>
            {t('deliverynotes.comments')}
          </div>
          <div style={{ padding: 16 }}>
            {editable ? (
              <textarea defaultValue={dn.notes || ''} disabled={busy} rows={4}
                onBlur={e => saveNotes(e.target.value)}
                aria-label={t('deliverynotes.comments')}
                style={{ ...inp, width: '100%', resize: 'vertical', fontFamily: MONO,
                         fontSize: 'var(--fs-body)', lineHeight: '16px' }} />
            ) : (
              <span style={{ whiteSpace: 'pre-wrap' }}>{dn.notes || '—'}</span>
            )}
          </div>
        </div>
        <div style={{ width: 300, background: 'var(--panel)', border: '1px solid var(--line)',
                      borderRadius: 'var(--r-card)',
                      // Mateixa raó que a la targeta: la mida va al contenidor.
                      fontFamily: MONO, fontSize: 'var(--fs-body)', lineHeight: '16px' }}>
          {[[t('deliverynotes.subtotal'), money(dn.subtotal), false],
            [t('deliverynotes.tax'), money(dn.tax_amount), false],
            [t('deliverynotes.total'), money(dn.total), true]].map(([k, v, fort], i, arr) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between',
                                    padding: '8px 16px', fontWeight: fort ? 600 : 400,
                                    borderBottom: i === arr.length - 1 ? 0 : '1px solid var(--line)' }}>
                <span>{k}</span><span>{v}</span>
              </div>
          ))}
        </div>
      </div>

      {/* Safata d'albaranables */}
      {trayOpen && (
        <div onClick={() => !trayBusy && setTrayOpen(false)} style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 50, padding: 16,
        }}>
          <div onClick={e => e.stopPropagation()} data-ftt-screen="albara-safata" style={{
            background: 'var(--panel)', borderRadius: 'var(--r-card)', padding: '1.2rem 1.4rem',
            maxWidth: 720, width: '100%', maxHeight: '85vh', overflowY: 'auto', borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--line)',
            // La mida es declara al CONTENIDOR, també aquí: la bidireccional va trobar les files
            // de la safata a 16px (les del document) en comptes dels 12 de la maqueta.
            fontFamily: MONO, fontSize: 'var(--fs-body)', lineHeight: '16px',
          }}>
            {/* Maqueta §1 · `.mt`: títol i, sota, EL CLIENT. On hi havia el títol hi havia
                també una frase d'ajuda («Tasques acabades, extres, despeses i deduccions
                pendents d'albarar»): el brief prohibeix el text d'ajuda a pantalla, i a més
                aquella frase havia quedat FALSA —la safata ja no és de tasques. Se'n va, i el
                seu lloc el pren el que la maqueta hi posa, que és una dada. */}
            <h2 style={{ fontSize: 'var(--fs-h2)', lineHeight: '24px', fontWeight: 500,
                         fontFamily: MONO }}>
              {t('deliverynotes.tray_title')}
            </h2>
            <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)', marginBottom: 14 }}>
              {dn.customer_nom}
            </p>
            {!tray ? <Center>{t('deliverynotes.loading')}</Center>
              : (tray.groups || []).length === 0 ? <div style={{ color: 'var(--text-soft)', padding: '10px 0' }}>{t('deliverynotes.tray_empty')}</div>
                : (tray.groups.map(g => (
                  <div key={g.model.id ?? 'sense-model'}>
                    <CapcaleraModelSafata g={g} t={t} locale={i18n.language} />
                    {/* Les files separades NOMÉS pel filet `--line` de cada fila (maqueta §1):
                        cap fons alternat, cap caixa per volta. */}
                    {/* `flatMap` i no un `map` niat: el niat torna ARRAYS al nivell exterior i
                        React en demana clau —n'hi havia a les files, no als arrays. */}
                    {(g.blocs || []).flatMap(b => b.rondes.map(r => (
                      <FilaRondaSafata key={r.id} r={r} bloc={blocKey(g, b)}
                        marcat={picked.has(blocKey(g, b))} onToggle={togglePick}
                        t={t} locale={i18n.language} />
                    )))}
                    {/* El bloc dels albaranables que NO són voltes, SOTA les voltes del model.
                        El rètol és el NOM del bloc (no text d'ajuda: diu què hi ha, no com
                        fer-ho servir) i només es pinta si el bloc existeix. */}
                    {(g.extres || []).length > 0 && (
                      <>
                        <div style={{ padding: '10px 16px 2px 32px', color: 'var(--text-soft)',
                                      fontSize: 'var(--fs-caption)', borderTop: '1px solid var(--line)' }}>
                          {t('deliverynotes.tray_extres')}
                        </div>
                        {g.extres.map(e => (
                          <FilaExtraSafata key={e.clau} e={e} clau={extraKey(g, e)}
                            marcat={picked.has(extraKey(g, e))} onToggle={togglePick} t={t} />
                        ))}
                      </>
                    )}
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
