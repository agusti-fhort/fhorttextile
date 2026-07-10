import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { pieceFittings, fittingSessions, modelTasks } from '../../api/endpoints'

// Sprint Y — accions del mode sessió a la superfície Mesures (migra el doSave/doDiscard de
// FittingDetail). Gravar i tornar = close de la peça + seal de la sessió (verificant l'estat REAL,
// XC) + tasca a Done + retorn (Y6). Si el close torna 400 code=grading_sealed, modal de reobertura
// explícita → repeteix amb allow_reopen_sealed. Descartar canvis reverteix les preses i deixa la
// tasca Paused (no Done). MOTOR intacte: close/seal/discard/transition_task es criden, no es toquen.

const MONO = 'IBM Plex Mono, monospace'
const btn = (variant) => ({
  fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '6px 14px', borderRadius: 4, cursor: 'pointer',
  border: '0.5px solid var(--gray-l)',
  background: variant === 'err' ? 'var(--err)' : variant === 'plain' ? 'var(--white)' : 'var(--gold)',
  color: variant === 'plain' ? 'var(--text-main)' : 'var(--white)', fontWeight: 500,
})
const overlay = { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }
const modalBox = { background: 'var(--white)', borderRadius: 8, padding: 24, maxWidth: 460, fontFamily: MONO, boxShadow: '0 8px 32px rgba(0,0,0,0.2)' }

export default function SessionActions({ session, pieceFittingId, taskId, onSaved, onReload, onFeedback }) {
  const { t } = useTranslation()
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const [sealedModal, setSealedModal] = useState(null)   // {version, gate} de la resposta 400
  const [discardMotiu, setDiscardMotiu] = useState(null) // string | null (obert)

  // Gravar: close (amb reobertura opcional) → seal → tasca Done → retorn. Migra la seqüència de doSave.
  const doSave = async (allowReopen = false) => {
    setBusy(true); setErr(null); setSealedModal(null)
    try {
      await pieceFittings.close(pieceFittingId, allowReopen ? { allow_reopen_sealed: true } : {})
    } catch (e) {
      const data = e?.response?.data || {}
      if (data.code === 'grading_sealed') { setSealedModal({ msg: data.error }); setBusy(false); return }
      // XC — missatge REAL del servidor, fallback genèric.
      setErr(data.error || data.detail || t('fitting.save.save_error_generic')); setBusy(false); return
    }
    let estat = null
    try { const r = await fittingSessions.seal(session.id); estat = r.data?.estat }
    catch { setErr(t('fitting.save.seal_error')); setBusy(false); return }
    if (estat !== 'Tancada') { setErr(t('fitting.save.not_sealed')); setBusy(false); return }
    // Tasca a Done (no fatal: la sessió ja és Tancada encara que la transició falli).
    if (taskId) { try { await modelTasks.transition(taskId, { to_status: 'Done' }) } catch { /* no-op */ } }
    setBusy(false)
    onSaved?.()
  }

  // Descartar canvis: revert de les preses a l'obertura; la tasca torna a Paused (segueix viva).
  const doDiscardChanges = async () => {
    setBusy(true); setErr(null)
    try {
      await pieceFittings.discard(pieceFittingId)
      if (taskId) { try { await modelTasks.transition(taskId, { to_status: 'Paused' }) } catch { /* no-op */ } }
      await onReload?.()
      onFeedback?.({ type: 'ok', text: t('fitting.save.discard_ok') })
    } catch { setErr(t('fitting.save.discard_error', { piece: pieceFittingId })) }
    finally { setBusy(false) }
  }

  const doDiscardSession = async () => {
    setBusy(true); setErr(null)
    try {
      await fittingSessions.discardSession(session.id, discardMotiu || '')
      setDiscardMotiu(null); setBusy(false)
      onSaved?.()
    } catch { setErr(t('fitting.save.discard_session_error')); setBusy(false) }
  }

  return (
    <div style={{ marginTop: 16 }}>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        <button style={btn('gold')} disabled={busy} onClick={() => doSave(false)}>{t('fitting.save.save_and_back')}</button>
        <button style={btn('plain')} disabled={busy} onClick={doDiscardChanges}>{t('fitting.save.discard_changes')}</button>
        <button style={btn('err')} disabled={busy} onClick={() => setDiscardMotiu('')}>{t('fitting.save.discard_session')}</button>
      </div>
      {err && <div style={{ color: 'var(--err)', fontSize: 'var(--fs-body)', marginTop: 10 }}>{err}</div>}

      {/* Modal de reobertura explícita (grading segellat, guard D-1) */}
      {sealedModal && (
        <div style={overlay} onClick={() => !busy && setSealedModal(null)}>
          <div onClick={e => e.stopPropagation()} style={{ ...modalBox, borderTop: '3px solid var(--gold)' }}>
            <h3 style={{ margin: '0 0 12px', fontSize: 'var(--fs-h3)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 }}>
              <i className="ti ti-lock-open" style={{ color: 'var(--gold)' }} />{t('fitting.save.reopen_title')}
            </h3>
            <p style={{ margin: '0 0 10px', fontSize: 'var(--fs-body)', lineHeight: 1.5, color: 'var(--text-main)' }}>{t('fitting.save.reopen_body')}</p>
            {sealedModal.msg && <p style={{ margin: '0 0 16px', fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>{sealedModal.msg}</p>}
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button style={btn('plain')} disabled={busy} onClick={() => setSealedModal(null)}>{t('common.cancel')}</button>
              <button style={btn('gold')} disabled={busy} onClick={() => doSave(true)}>{t('fitting.save.reopen_confirm')}</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de descartar sessió (motiu opcional) */}
      {discardMotiu !== null && (
        <div style={overlay} onClick={() => !busy && setDiscardMotiu(null)}>
          <div onClick={e => e.stopPropagation()} style={modalBox}>
            <h3 style={{ margin: '0 0 12px', fontSize: 'var(--fs-h3)', fontWeight: 600 }}>{t('fitting.save.discard_session')}</h3>
            <input type="text" value={discardMotiu} onChange={e => setDiscardMotiu(e.target.value)}
              placeholder={t('fitting.save.discard_motiu_ph')}
              style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '6px 8px', borderRadius: 4, border: '1px solid var(--border)', marginBottom: 18, width: '100%', boxSizing: 'border-box' }} />
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button style={btn('plain')} disabled={busy} onClick={() => setDiscardMotiu(null)}>{t('common.cancel')}</button>
              <button style={btn('err')} disabled={busy} onClick={doDiscardSession}>{t('fitting.save.discard_session')}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
