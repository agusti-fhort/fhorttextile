import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { commerce } from '../api/endpoints'
import Feedback from '../components/ui/Feedback'
import Modal from '../components/ui/Modal'
import PageMenu from '../components/ui/PageMenu'
import TaulaLlista from '../components/ui/TaulaLlista'
import useToc, { anellFocus } from '../components/ui/toc'
import { WOStatusBadge } from './WorkOrders'
import {
  Comptador, FilaIdentitat, EstatBuit, buit, forceBarra,
} from '../components/llista/ChromLlista'
import { botoSec, apagat } from '../components/ui/buttons'

// ENCÀRRECS ORFES (D6/E5) — WorkOrders desassignats d'una línia de comanda, pendents de
// reassignar. Font: `work-orders/orphaned/` (un informe, no un llistat paginat: torna
// `{orphaned: [...]}` sencer).
//
// ── QUATRE COSES QUE ES DIUEN EN VEU ALTA ────────────────────────────────────────────────
//
// 1 · **AQUESTA PANTALLA SÍ QUE TÉ ACCIÓ PRIMÀRIA, i és per fila.** «Reassignar» és exactament
//    «el que has vingut a fer aquí»: un orfe és una anomalia i la pantalla existeix per resoldre
//    -la. Però n'hi ha UNA PER FILA, i la §5.1 diu «UNA per pantalla». Es resol com la §5.3
//    resol les portes: el botó de la fila **no és blau** —obre un modal, no completa res—, i el
//    blau viu al botó que CONFIRMA dins del modal, que és on la feina s'acaba de debò. Anava a
//    l'inrevés: el de la fila era daurat ple (llei anterior a la §5) i el de confirmar, el mateix
//    daurat, o sigui que la pantalla no tenia cap blau i el gest que compromet no es distingia
//    del que només obre.
//
// 2 · **EL MODAL ERA FET A MÀ** (`position: fixed` + `rgba(0,0,0,0.35)` + `zIndex: 50` propis),
//    com el de composició d'albarans. Passa a `ui/Modal`: el §8b-quater fixa l'escala de capes
//    del sistema i una pantalla no se la pot inventar.
//
// 3 · **EL FEEDBACK ERA UN `<p>` VERD-DAURAT.** L'èxit es pintava en `--gold` i l'error en
//    `--grana` — dos colors de MARCA fent de semàfor, que és el que la §1 no admet. Passa a
//    `ui/Feedback`, que és el component de la casa.
//
// 4 · **NO HI HA PAGINACIÓ, i no és un oblit.** L'endpoint és un informe: torna tots els orfes
//    d'un cop, sense `count` ni `next`. Inventar-hi paginació al client seria paginar sobre una
//    llista que ja hi és sencera. El comptador diu «N/N» perquè el filtre és tot el cens.
const MONO = 'IBM Plex Mono, monospace'

export default function OrphanedWorkOrders() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [items, setItems] = useState([])
  const [feedback, setFeedback] = useState(null)

  // E5 — reassignació: fila orfe triada + candidates + línia seleccionada.
  const [reattach, setReattach] = useState(null)   // { woId, number, codi } | null
  const [candidates, setCandidates] = useState([])
  const [candLoading, setCandLoading] = useState(false)
  const [selectedLine, setSelectedLine] = useState(null)
  const [busy, setBusy] = useState(false)

  const reload = useCallback(() => {
    setLoading(true); setError(false)
    return commerce.workOrders.orphaned()
      .then(res => setItems(res.data?.orphaned || []))
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { reload() }, [reload])

  const fmtDate = (iso) => iso ? new Date(iso).toLocaleDateString(i18n.language || 'ca',
    { day: '2-digit', month: '2-digit', year: 'numeric' }) : '—'

  const obreReassignacio = (r) => {
    setReattach({ woId: r.id, number: r.number, codi: r.model?.codi_intern || r.number })
    setSelectedLine(null)
    setCandidates([])
    setCandLoading(true)
    commerce.workOrders.reattachCandidates(r.id)
      .then(res => setCandidates(res.data?.candidates || []))
      .catch(() => setCandidates([]))
      .finally(() => setCandLoading(false))
  }

  const reassigna = () => {
    if (!reattach || !selectedLine) return
    setBusy(true)
    commerce.workOrders.reattach(reattach.woId, { order_line_id: selectedLine })
      .then(() => { setReattach(null); return reload() })
      .then(() => setFeedback({ type: 'ok', text: t('orphans.reattach_done') }))
      .catch(err => setFeedback({ type: 'err', text: err?.response?.data?.detail || t('orphans.reattach_error') }))
      .finally(() => setBusy(false))
  }

  const cols = useMemo(() => [
    {
      key: 'date', label: t('orphans.col_date'), min: 90, max: 110,
      estil: { fontSize: 11, color: 'var(--text-soft)' },
      render: r => fmtDate(r.created_at),
    },
    {
      // LA DADA REINA: el número de l'encàrrec orfe. És el que s'ha de reassignar.
      key: 'wo', label: t('orphans.col_wo'), min: 130, max: 170,
      estil: { fontWeight: 600 }, titol: r => r.number,
      render: r => r.number || '—',
    },
    {
      // El codi del model anava en `--gold`: el daurat és marca i selecció, no una dada
      // (§8c: «el daurat NO pinta números», i la mateixa raó val per a un codi).
      key: 'model', label: t('orphans.col_model'), min: 120, max: 150,
      estil: { fontSize: 11, color: 'var(--text-soft)' },
      titol: r => r.model?.codi_intern || undefined,
      render: r => r.model?.codi_intern || '—',
    },
    {
      key: 'customer', label: t('orphans.col_customer'), min: 150, max: 250,
      titol: r => r.customer || undefined,
      render: r => r.customer || '—',
    },
    {
      key: 'order', label: t('orphans.col_order'), min: 120, max: 160,
      estil: { fontSize: 11, color: 'var(--text-soft)' },
      render: r => r.order?.document_number || '—',
    },
    {
      key: 'total', label: t('orphans.col_total'), min: 90, max: 120, align: 'right',
      render: r => r.order?.total ?? '—',
    },
    {
      key: 'status', label: t('orphans.col_status'), min: 90, max: 120,
      render: r => <WOStatusBadge status={r.status} t={t} />,
    },
    {
      key: '_a', amplada: 130,
      // Reassignar només si el WO és OPEN — és el guard del `reattach` al backend: un CLOSED no
      // es re-adopta. No oferir-ho és cortesia; qui blinda de debò és l'API.
      render: r => (r.status === 'OPEN'
        ? <BotoFila onClick={(e) => { e.stopPropagation(); obreReassignacio(r) }}
          icona="ti-link" label={t('orphans.reattach')} />
        : null),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [t, i18n.language])

  return (
    <>
      <div style={forceBarra}>
        <PageMenu backTo="/comercial/encarrecs" backTitle={t('orphans.back_title')} />
      </div>

      <div style={{ minWidth: 0, maxWidth: '100%' }}>
        <FilaIdentitat>
          {/* L'informe torna el cens sencer: el filtre ÉS tot, i el comptador ho diu sense
              fingir un denominador que aquí no existeix. */}
          <Comptador valor={items.length} total={items.length} etiqueta={t('orphans.entity')} />
        </FilaIdentitat>

        <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

        {loading ? <EstatBuit>{t('orphans.loading')}</EstatBuit>
          : error ? <EstatBuit>{t('orphans.error')}</EstatBuit>
            : items.length === 0 ? <EstatBuit>{t('orphans.empty')}</EstatBuit>
              : (
                <TaulaLlista cols={cols} files={items} clau={(r) => r.id}
                  onObrir={(r) => r.order && navigate(`/comercial/comandes/${r.order.id}`)} />
              )}
      </div>

      {reattach && (
        <Modal title={t('orphans.reattach_title')}
          subtitle={t('orphans.reattach_help', { codi: reattach.codi })}
          cancelLabel={t('common.cancel')} confirmLabel={t('orphans.reattach_confirm')}
          confirmDisabled={busy || !selectedLine}
          onCancel={() => !busy && setReattach(null)} onConfirm={reassigna}>
          {candLoading ? <p style={buit}>{t('orphans.reattach_loading')}</p>
            : candidates.length === 0 ? <p style={buit}>{t('orphans.reattach_empty')}</p>
              : (
                <div role="radiogroup" aria-label={t('orphans.reattach_title')}
                  style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {candidates.map(c => (
                    <Candidata key={c.id} c={c} triada={selectedLine === c.id}
                      onTria={() => setSelectedLine(c.id)} />
                  ))}
                </div>
              )}
        </Modal>
      )}
    </>
  )
}

// La línia de comanda candidata. §1 · «on soc» (l'element triat d'una llista de navegació/tria)
// = `--sel` + FILET D'OR, no una vora daurada tot al voltant: la vora completa és el llenguatge
// del botó secundari, i això no és un botó, és una fila triada.
function Candidata({ c, triada, onTria }) {
  const [toc, gestos] = useToc()
  return (
    <button type="button" role="radio" aria-checked={triada} onClick={onTria} {...gestos}
      style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10,
        width: '100%', textAlign: 'left', padding: '8px 12px',
        borderWidth: 1, borderStyle: 'solid',
        borderColor: triada ? 'var(--gold-border)' : 'var(--line)',
        borderRadius: 'var(--r-ctrl)',
        background: triada ? 'var(--sel)' : (toc.hover ? 'var(--bg-page)' : 'var(--panel)'),
        boxShadow: triada ? 'inset 3px 0 0 var(--gold)' : 'none',
        fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-main)',
        cursor: 'pointer', outline: 'none',
        ...(toc.focus ? anellFocus : null),
      }}>
      <span style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        <b style={{ fontWeight: 600 }}>{c.order_number}</b>
        <span style={{ color: 'var(--text-soft)', marginLeft: 8 }}>{c.description}</span>
      </span>
      <span style={{ display: 'flex', alignItems: 'center', gap: 8, whiteSpace: 'nowrap',
        color: 'var(--text-soft)' }}>
        {c.qty_allocated}/{c.quantity}
        {triada && <i className="ti ti-check" aria-hidden="true"
          style={{ fontSize: 14, color: 'var(--gold)' }} />}
      </span>
    </button>
  )
}

// El botó d'acció d'una fila: SECUNDARI de la casa, compacte. No és blau —obre un modal, no
// completa la feina— i no és daurat ple, que és la llei anterior a la §5.
function BotoFila({ onClick, icona, label, disabled = false }) {
  const [toc, gestos] = useToc()
  return (
    <button type="button" onClick={onClick} disabled={disabled} {...gestos}
      style={{
        ...botoSec, padding: '5px 10px', fontSize: 'var(--fs-body)',
        background: (toc.hover && !disabled) ? 'var(--sel)' : 'var(--panel)',
        outline: 'none',
        ...(disabled ? apagat : null),
        ...(toc.focus ? anellFocus : null),
      }}>
      <i className={`ti ${icona}`} aria-hidden="true" style={{ fontSize: 14, color: 'currentColor' }} />
      {label}
    </button>
  )
}
