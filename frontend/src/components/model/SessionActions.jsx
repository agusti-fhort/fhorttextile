import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { pieceFittings, fittingSessions, modelTasks } from '../../api/endpoints'
import { formatNum, parseNum } from '../../utils/num'
import { boto } from '../ui/buttons'
import Badge from '../ui/Badge'

// Sprint Y — accions del mode sessió a la superfície Mesures (migra el doSave/doDiscard de
// FittingDetail). Gravar i tornar = close de la peça + seal de la sessió (verificant l'estat REAL,
// XC) + tasca a Done + retorn (Y6). Si el close torna 400 code=grading_sealed, modal de reobertura
// explícita → repeteix amb allow_reopen_sealed. Descartar canvis reverteix les preses i deixa la
// tasca Paused (no Done). MOTOR intacte: close/seal/discard/transition_task es criden, no es toquen.
//
// LLEI Agus 24/09 — CONSENTIMENT DE GERMANES (Patró B, COMMIT 5, maqueta
// ops/maquetes/maqueta_consentiment_germanes_v1.html). «Gravar i tornar» ara consulta PRIMER
// `GET …/proposta/` (pur, no escriu res): `buit=true` → close directe, IDÈNTIC a abans; si no,
// obre el modal de consentiment i el close real només es dispara en prémer «Aplicar», amb
// `decisions` al body. Cancel·lar el modal NO truca `close`: la sessió es queda oberta.

const MONO = 'IBM Plex Mono, monospace'
// CODA · retoc 3 (Agus) — «GRAVAR I TORNAR» ÉS EL BLAU D'AQUESTA PANTALLA (§5.1): és el que
// tanca la feina de la sessió. «Descartar canvis» és TERCIÀRIA (desfà, no compromet) i
// «Descartar sessió» és DESTRUCTIVA amb VORA — plena NOMÉS al botó que confirma dins del modal,
// que és on la §5.5 vol el vermell ple. Abans les tres eren plenes: daurada, blanca i vermella,
// i la vermella cridava més que la que de debò havies de prémer.
const btn = (variant, disabled = false) => boto(
  variant === 'gold' ? 'pri' : variant === 'plain' ? 'ter' : variant, disabled)
const overlay = { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }
const modalBox = { background: 'var(--white)', borderRadius: 8, padding: 24, maxWidth: 460, fontFamily: MONO, boxShadow: '0 8px 32px rgba(0,0,0,0.2)' }
// Modal AMPLE (maqueta v1, `.modal{max-width:860px}`): conté una taula, no un paràgraf — cada
// secció (capçalera/taula/peu) porta el seu propi padding, com a la maqueta, en lloc d'un
// padding uniforme del contenidor.
const modalBoxAmpla = { background: 'var(--white)', borderRadius: 'var(--r-card)', maxWidth: 860, width: '100%', fontFamily: MONO, boxShadow: '0 8px 32px rgba(0,0,0,0.2)', overflow: 'hidden' }

// Humanitzat mínim de l'slug d'instància (DIAGNOSI Q2: NO EXISTEIX vocabulari d'instància).
// Bessona de `etiqueta_instancia` (`fitting/services_consentiment.py`) — mateixa regla.
const etiquetaInstancia = (slug) => (slug || '').replace(/[_-]/g, ' ').trim() || '—'
const capitalitza = (s) => s ? s.charAt(0).toUpperCase() + s.slice(1) : s

/** Els defectes de decisió (LLEI Agus 24/09): origen DERIVAT → proposta pre-usada; qualsevol
 * altre origen mesurat → mantenir. Retorna `{bm_id: 'text formatat'}` per als inputs. */
function defectesDe(proposta, lang) {
  const decisions = {}
  for (const bucket of proposta.poms) {
    for (const g of bucket.germanes) {
      const valor = g.decisio_defecte === 'PROPOSTA' ? g.proposat : g.actual
      decisions[g.bm_id] = formatNum(valor, { lang, dec: 1 })
    }
  }
  return decisions
}

function totesLesGermanes(proposta) {
  return proposta.poms.flatMap(b => b.germanes)
}

export default function SessionActions({ session, pieceFittingId, taskId, onSaved, onReload, onFeedback }) {
  const { t, i18n } = useTranslation()
  const lang = (i18n.resolvedLanguage || i18n.language || 'ca').slice(0, 2)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const [sealedModal, setSealedModal] = useState(null)   // {msg, decisions} de la resposta 400
  const [discardMotiu, setDiscardMotiu] = useState(null) // string | null (obert)
  const [proposta, setProposta] = useState(null)         // resposta de GET …/proposta/, o null
  const [decisions, setDecisions] = useState({})         // {bm_id: text cru de l'input}

  // El tancament REAL (close + seal + tasca + retorn), amb o sense `decisions`. `decisionsPayload`
  // és `null` pel camí d'avui (sense consentiment) o un objecte `{bm_id: valor}` (buit inclòs).
  const tancaAmbDecisions = async (allowReopen, decisionsPayload) => {
    setBusy(true); setErr(null); setSealedModal(null)
    try {
      const body = allowReopen ? { allow_reopen_sealed: true } : {}
      if (decisionsPayload !== null) body.decisions = decisionsPayload
      await pieceFittings.close(pieceFittingId, body)
    } catch (e) {
      const data = e?.response?.data || {}
      if (data.code === 'grading_sealed') {
        setSealedModal({ msg: data.error, decisions: decisionsPayload }); setBusy(false); return
      }
      // XC — missatge REAL del servidor, fallback genèric.
      setErr(data.error || data.detail || t('fitting.save.save_error_generic')); setBusy(false); return
    }
    let estat
    try { const r = await fittingSessions.seal(session.id); estat = r.data?.estat }
    catch { setErr(t('fitting.save.seal_error')); setBusy(false); return }
    if (estat !== 'Tancada') { setErr(t('fitting.save.not_sealed')); setBusy(false); return }
    // F1.2 — AQUÍ hi havia `transition(taskId, {to_status:'Done'})` dins d'un `catch {}` buit.
    // Desar no tanca (D-2): «Gravar i tornar» segella la SESSIÓ, i el Stop humà tanca la TASCA.
    // El catch buit, a més, s'empassava el 409 d'albarà i deixava la sessió tancada amb la
    // tasca viva sense dir-ho a ningú (germà de §S-5).
    setBusy(false)
    setProposta(null); setDecisions({})
    onSaved?.()
  }

  // Gravar: consulta PRIMER la proposta (pura). Buida → close directe (camí d'avui, intacte).
  // No buida → obre el modal de consentiment; el close real espera «Aplicar».
  const doSave = async () => {
    setBusy(true); setErr(null); setSealedModal(null)
    let prop
    try {
      const r = await pieceFittings.proposta(pieceFittingId)
      prop = r.data
    } catch {
      // La proposta és una LECTURA; si peta, no bloqueja «Gravar i tornar» — cau al camí
      // sense consentiment (el mateix que hi havia abans que aquest endpoint existís).
      await tancaAmbDecisions(false, null)
      return
    }
    if (prop.buit) {
      await tancaAmbDecisions(false, null)
      return
    }
    setProposta(prop)
    setDecisions(defectesDe(prop, lang))
    setBusy(false)
  }

  const doApply = async () => {
    const payload = {}
    for (const g of totesLesGermanes(proposta)) {
      const v = parseNum(decisions[g.bm_id])
      payload[g.bm_id] = v === null ? g.actual : v
    }
    await tancaAmbDecisions(false, payload)
  }

  const usarProposta = (bmId, valorProposat) =>
    setDecisions(d => ({ ...d, [bmId]: formatNum(valorProposat, { lang, dec: 1 }) }))
  const usarTotesLesPropostes = () => {
    const next = {}
    for (const g of totesLesGermanes(proposta)) next[g.bm_id] = formatNum(g.proposat, { lang, dec: 1 })
    setDecisions(next)
  }
  const restablirValors = () => setDecisions(defectesDe(proposta, lang))
  const cancelarConsentiment = () => { setProposta(null); setDecisions({}) }

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
        <button type="button" style={btn('gold', busy)} disabled={busy}
          onClick={doSave}>{t('fitting.save.save_and_back')}</button>
        <button type="button" style={btn('plain', busy)} disabled={busy}
          onClick={doDiscardChanges}>{t('fitting.save.discard_changes')}</button>
        <button type="button" style={btn('err', busy)} disabled={busy}
          onClick={() => setDiscardMotiu('')}>{t('fitting.save.discard_session')}</button>
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
            {sealedModal.msg && <p style={{ margin: '0 0 16px', fontSize: 'var(--fs-caption)', color: 'var(--text-soft)' }}>{sealedModal.msg}</p>}
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button type="button" style={btn('plain', busy)} disabled={busy}
                onClick={() => setSealedModal(null)}>{t('common.cancel')}</button>
              <button type="button" style={btn('gold', busy)} disabled={busy}
                onClick={() => tancaAmbDecisions(true, sealedModal.decisions ?? null)}>{t('fitting.save.reopen_confirm')}</button>
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
              style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '6px 8px', borderRadius: 4, border: '1px solid var(--line)', marginBottom: 18, width: '100%', boxSizing: 'border-box' }} />
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button type="button" style={btn('plain', busy)} disabled={busy}
                onClick={() => setDiscardMotiu(null)}>{t('common.cancel')}</button>
              {/* §5.5 — AQUÍ sí: el vermell ple, al botó que confirma la destrucció. */}
              <button type="button" style={btn('err-ple', busy)} disabled={busy}
                onClick={doDiscardSession}>{t('fitting.save.discard_session')}</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de CONSENTIMENT DE GERMANES (LLEI Agus 24/09, maqueta v1) */}
      {proposta && (
        <div style={overlay} onClick={() => !busy && cancelarConsentiment()}>
          <div onClick={e => e.stopPropagation()} style={modalBoxAmpla}>
            <div style={{ padding: '16px 16px 12px', borderBottom: '1px solid var(--line)' }}>
              <div style={{ fontSize: 'var(--fs-h2)', lineHeight: '24px', fontWeight: 500 }}>
                {t('fitting.save.consent_title')}
              </div>
              <div style={{ color: 'var(--text-soft)', marginTop: 2, fontSize: 'var(--fs-body)' }}>
                {t('fitting.save.consent_subtitle', {
                  count: totesLesGermanes(proposta).length, poms: proposta.poms.length,
                })}
              </div>
            </div>

            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  {[
                    [t('fitting.save.consent_col_pom'), '28%', false],
                    [t('fitting.save.consent_col_origen'), '12%', false],
                    [t('fitting.save.consent_col_actual'), '14%', true],
                    [t('fitting.save.consent_col_proposta'), '46%', false],
                  ].map(([label, width, right]) => (
                    <th key={label} style={{
                      width, textAlign: right ? 'right' : 'left', padding: '8px 12px',
                      borderBottom: '1px solid var(--line)', fontSize: 'var(--fs-caption)',
                      letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-soft)',
                      fontWeight: 500,
                    }}>{label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {proposta.poms.map(bucket => (
                  <FitBucket key={bucket.pom} bucket={bucket} decisions={decisions} lang={lang} t={t}
                    onUsar={usarProposta}
                    onCanviaActual={(bmId, text) => setDecisions(d => ({ ...d, [bmId]: text }))} />
                ))}
              </tbody>
            </table>

            <div style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '12px 16px', borderTop: '1px solid var(--line)' }}>
              <button type="button" style={btn('sec', busy)} disabled={busy}
                onClick={usarTotesLesPropostes}>{t('fitting.save.consent_use_all')}</button>
              <button type="button" style={btn('sec', busy)} disabled={busy}
                onClick={restablirValors}>{t('fitting.save.consent_reset')}</button>
              <span style={{ flex: 1 }} />
              <button type="button" style={btn('plain', busy)} disabled={busy}
                onClick={cancelarConsentiment}>{t('common.cancel')}</button>
              <button type="button" style={btn('gold', busy)} disabled={busy}
                onClick={doApply}>{t('fitting.save.consent_apply')}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/** Una secció de POM: la fila de capçalera (`--sel`, «mesurat al fitting: …») + les seves
 * germanes. Component local — no surt d'aquest fitxer, com els altres dos modals de sobre. */
function FitBucket({ bucket, decisions, lang, t, onUsar, onCanviaActual }) {
  const mesurat = bucket.mesurades.map(m =>
    `${etiquetaInstancia(m.instancia)} ${formatNum(m.ara, { lang, dec: 1 })} (${t('fitting.save.consent_era', { value: formatNum(m.abans, { lang, dec: 1 }) })})`
  ).join(', ')
  return (
    <>
      <tr>
        <td colSpan={4} style={{ background: 'var(--sel)', padding: '10px 12px', borderBottom: '1px solid var(--line)' }}>
          <span style={{ fontWeight: 600, color: 'var(--gold)' }}>{bucket.pom}</span>
          {bucket.pom_nom && <> · <span style={{ fontWeight: 600 }}>{bucket.pom_nom}</span></>}
          {' '}<span style={{ color: 'var(--text-soft)' }}>
            · {t('fitting.save.consent_measured_at')}: {mesurat}
          </span>
        </td>
      </tr>
      {bucket.germanes.map(g => (
        <GermanaRow key={g.bm_id} g={g} valorActual={decisions[g.bm_id] ?? ''} lang={lang} t={t}
          onUsar={onUsar} onCanviaActual={onCanviaActual} />
      ))}
    </>
  )
}

function GermanaRow({ g, valorActual, lang, t, onUsar, onCanviaActual }) {
  const actualNum = parseNum(valorActual)
  const canviat = actualNum !== null && Math.abs(actualNum - g.actual) > 1e-6
  const usada = actualNum !== null && Math.abs(actualNum - g.proposat) < 1e-6
  return (
    <tr>
      <td style={{ padding: '8px 12px', paddingLeft: 28, borderBottom: '1px solid var(--line)' }}>
        {capitalitza(etiquetaInstancia(g.instancia))}
      </td>
      <td style={{ padding: '8px 12px', borderBottom: '1px solid var(--line)' }}>
        <Badge variant={g.origen === 'DERIVAT' ? 'gold' : 'gray'}>
          {g.origen === 'DERIVAT' ? t('fitting.save.consent_badge_derivat') : t('fitting.save.consent_badge_mesurat')}
        </Badge>
      </td>
      <td style={{ padding: '8px 12px', borderBottom: '1px solid var(--line)', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
        <input value={valorActual} onChange={e => onCanviaActual(g.bm_id, e.target.value)}
          style={{
            width: 76, font: 'inherit', fontSize: 'var(--fs-body)', fontWeight: 600, textAlign: 'right',
            padding: '4px 8px', border: '1px solid var(--line)', borderRadius: 'var(--r-ctrl)',
            color: 'var(--text-main)', background: 'var(--white)',
          }} />
        {canviat && (
          <span style={{ display: 'block', color: 'var(--text-soft)', fontSize: 'var(--fs-caption)', marginTop: 2 }}>
            {t('fitting.save.consent_era', { value: formatNum(g.actual, { lang, dec: 1 }) })}
          </span>
        )}
      </td>
      <td style={{ padding: '8px 12px', borderBottom: '1px solid var(--line)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontVariantNumeric: 'tabular-nums', fontWeight: 600, minWidth: 44, textAlign: 'right' }}>
            {formatNum(g.proposat, { lang, dec: 1 })}
          </span>
          <span style={{ color: 'var(--text-soft)', fontSize: 'var(--fs-caption)', flex: 1 }}>{g.regla_text}</span>
          <button type="button" disabled={usada} onClick={() => onUsar(g.bm_id, g.proposat)}
            style={{
              font: 'inherit', fontSize: 11, lineHeight: '14px', padding: '3px 10px',
              borderRadius: 'var(--r-ctrl)', whiteSpace: 'nowrap', cursor: usada ? 'default' : 'pointer',
              border: `1px solid ${usada ? 'var(--ok)' : 'var(--gold-border)'}`,
              background: usada ? 'var(--ok-bg)' : 'var(--white)',
              color: usada ? 'var(--ok)' : 'var(--text-main)',
            }}>
            {usada ? t('fitting.save.consent_used') : t('fitting.save.consent_use')}
          </button>
        </div>
      </td>
    </tr>
  )
}
