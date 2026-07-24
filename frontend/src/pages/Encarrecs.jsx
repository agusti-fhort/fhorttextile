import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import { encarrecs as encarrecsApi } from '../api/endpoints'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import Modal from '../components/ui/Modal'
import { primaryBtn } from '../components/ui/buttons'

// P8 (Federació v2) — la SAFATA del Studio: què m'han encomanat i què me n'he portat a casa.
//
// MIRALL DE «RECURSOS» (la pàgina del Brand), i a posta: allà es governa amb qui es pot
// comptar; aquí es treballa el que t'han encomanat. Cap de les dues ensenya l'altra meitat.
//
// L'ESTAT NO ÉS UN CAMP QUE ES PUGUI DESINCRONITZAR: PENDENT/TRASPASSAT el calcula el backend
// comparant el codi del Brand amb el que ja tinc al meu schema. Si algú esborra el model
// local, la fila torna a PENDENT tot sola i el traspàs el tornarà a crear.
const MONO = 'IBM Plex Mono, monospace'

const ESTAT_STYLE = {
  PENDENT:    { background: 'var(--warn-bg)', color: 'var(--warn)' },
  TRASPASSAT: { background: 'var(--ok-bg)', color: 'var(--ok)' },
}

export default function Encarrecs() {
  const { t } = useTranslation()
  const canEdit = useAuthStore(s => s.user?.capabilities?.includes('configure')) ?? false

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [grups, setGrups] = useState([])
  const [feedback, setFeedback] = useState(null)
  const [busy, setBusy] = useState(false)
  // Selecció per codi_intern. El codi és únic dins d'un Brand i els grups no es barregen mai
  // en una sola acció (el traspàs és per Brand), així que no cal clau composta.
  const [sel, setSel] = useState(() => new Set())
  const [confirm, setConfirm] = useState(null)   // { brand, codis } — codis=null → tots els pendents
  const [informe, setInforme] = useState(null)   // resultat del traspàs, per llegir amb calma

  const load = useCallback(() => {
    setError(false)
    return encarrecsApi.list()
      .then(r => setGrups(r.data?.grups ?? []))
      .catch(() => setError(true))
  }, [])

  useEffect(() => {
    let alive = true
    load().finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [load])

  const totalPendents = useMemo(
    () => grups.reduce((a, g) => a + (g.n_pendents || 0), 0), [grups])

  const toggle = (codi) => setSel(s => {
    const n = new Set(s)
    n.has(codi) ? n.delete(codi) : n.add(codi)
    return n
  })

  // Només es poden triar els PENDENTS: seleccionar un traspassat suggeriria que l'acció faria
  // alguna cosa, i el backend el saltaria en silenci. Millor no oferir-ho.
  const pendentsDe = (g) => g.models.filter(m => m.estat_local === 'PENDENT')
  const selDe = (g) => pendentsDe(g).filter(m => sel.has(m.codi_intern))

  const executa = () => {
    const { brand, codis } = confirm
    setBusy(true)
    encarrecsApi.traspassar({ brand_codi: brand, codis: codis ?? 'tots_pendents' })
      .then(r => {
        setConfirm(null)
        setSel(new Set())
        setInforme(r.data)
        return load()
      })
      .catch(e => {
        setConfirm(null)
        setFeedback({ type: 'err', text: e?.response?.data?.error || t('encarrecs.error') })
      })
      .finally(() => setBusy(false))
  }

  return (
    <div style={{ minWidth: 0, maxWidth: 1000 }}>
      <div style={{ marginBottom: '1rem' }}>
        <h1 style={{ fontSize: 'var(--fs-h1)', fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>
          {t('encarrecs.title')}
        </h1>
        <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontWeight: 300 }}>
          {totalPendents > 0
            ? t('encarrecs.subtitle_pendents', { n: totalPendents })
            : t('encarrecs.subtitle')}
        </p>
      </div>

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      {loading ? <Center>{t('encarrecs.loading')}</Center>
        : error ? <Center>{t('encarrecs.error')}</Center>
          : grups.length === 0 ? <Center>{t('encarrecs.empty')}</Center>
            : grups.map(g => (
              <GrupBrand key={g.brand_codi} g={g} t={t} canEdit={canEdit} busy={busy}
                sel={sel} toggle={toggle} pendents={pendentsDe(g)} triats={selDe(g)}
                onTraspassar={(codis) => setConfirm({ brand: g.brand_codi, codis })} />
            ))}

      {confirm && (
        <Modal title={t('encarrecs.confirm_title')}
          subtitle={confirm.codis
            ? t('encarrecs.confirm_n', { n: confirm.codis.length, brand: confirm.brand })
            : t('encarrecs.confirm_tots', { brand: confirm.brand })}
          cancelLabel={t('encarrecs.cancel')}
          confirmLabel={busy ? t('encarrecs.working') : t('encarrecs.traspassar')}
          confirmDisabled={busy} onConfirm={executa} onCancel={() => !busy && setConfirm(null)}>
          <p style={{ fontSize: 'var(--fs-body)', lineHeight: 1.5, color: 'var(--text-muted)' }}>
            {t('encarrecs.confirm_help')}
          </p>
        </Modal>
      )}

      {informe && <InformeModal informe={informe} t={t} onClose={() => setInforme(null)} />}
    </div>
  )
}

function GrupBrand({ g, t, canEdit, busy, sel, toggle, pendents, triats, onTraspassar }) {
  if (g.error) {
    return (
      <div style={{ ...card, padding: '14px 16px', color: 'var(--err)', fontFamily: MONO }}>
        {t('encarrecs.brand_missing', { codi: g.brand_codi })}
      </div>
    )
  }
  return (
    <div style={card}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
        padding: '12px 16px', borderBottom: '0.5px solid var(--gray-l)' }}>
        <span style={{ fontFamily: MONO, fontWeight: 700, color: 'var(--gold)' }}>{g.brand_codi}</span>
        <span style={{ fontSize: 'var(--fs-body)', fontWeight: 500 }}>{g.brand_nom}</span>
        <span style={{ fontFamily: MONO, fontSize: 'var(--fs-caption)', color: 'var(--gray)' }}>
          {t('encarrecs.comptador', { p: g.n_pendents, tot: g.models.length })}
        </span>
        {canEdit && pendents.length > 0 && (
          <span style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
            <button onClick={() => onTraspassar(triats.map(m => m.codi_intern))}
              disabled={busy || triats.length === 0}
              style={{ ...primaryBtn, marginLeft: 0,
                opacity: (busy || triats.length === 0) ? 0.5 : 1,
                cursor: (busy || triats.length === 0) ? 'not-allowed' : 'pointer' }}>
              <i className="ti ti-download" style={{ fontSize: 14 }} aria-hidden="true" />
              {t('encarrecs.traspassar_n', { n: triats.length })}
            </button>
            <button onClick={() => onTraspassar(null)} disabled={busy}
              style={{ ...ghostBtn, cursor: busy ? 'not-allowed' : 'pointer' }}>
              {t('encarrecs.traspassar_tots')}
            </button>
          </span>
        )}
      </div>

      {g.models.length === 0
        ? <div style={{ padding: '16px', color: 'var(--gray)', fontFamily: MONO,
            fontSize: 'var(--fs-body)' }}>{t('encarrecs.grup_buit')}</div>
        : g.models.map(m => {
          const pendent = m.estat_local === 'PENDENT'
          return (
            <label key={m.codi_intern} style={{
              display: 'flex', alignItems: 'center', gap: 12, padding: '9px 16px',
              borderBottom: '0.5px solid var(--gray-l)',
              cursor: (canEdit && pendent) ? 'pointer' : 'default',
            }}>
              <input type="checkbox" disabled={!canEdit || !pendent}
                checked={sel.has(m.codi_intern)} onChange={() => toggle(m.codi_intern)}
                style={{ width: 15, height: 15, opacity: pendent ? 1 : 0.25 }} />
              <span style={{ fontFamily: MONO, fontWeight: 600, minWidth: 150 }}>{m.codi_intern}</span>
              <span style={{ flex: 1, fontSize: 'var(--fs-body)', minWidth: 0, overflow: 'hidden',
                textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.nom_prenda || '—'}</span>
              <span style={{ fontFamily: MONO, fontSize: 'var(--fs-caption)', color: 'var(--gray)' }}>
                {m.temporada}{m.any ? ` ${m.any}` : ''}
              </span>
              <span style={{ fontSize: 'var(--fs-label)', fontWeight: 600, padding: '2px 8px',
                borderRadius: 999, fontFamily: MONO, ...ESTAT_STYLE[m.estat_local] }}>
                {t(`encarrecs.estat_${m.estat_local}`, m.estat_local)}
              </span>
            </label>
          )
        })}
    </div>
  )
}

// L'informe del traspàs es llegeix amb calma en un modal i no com un toast que s'esvaeix: hi
// ha coses que l'usuari ha de poder mirar dues vegades (què s'ha saltat, quina config no ha
// aparellat i per tant ha quedat buida al model nou).
function InformeModal({ informe, t, onClose }) {
  const um = informe.unmatched || {}
  const noAparellats = Object.entries(um).filter(([, v]) => v && v.length)
  return (
    <Modal title={t('encarrecs.informe_title')} cancelLabel={t('encarrecs.tancar')}
      confirmLabel={t('encarrecs.tancar')} onCancel={onClose} onConfirm={onClose}>
      <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontFamily: MONO,
        fontSize: 'var(--fs-body)', lineHeight: 1.8 }}>
        <li><b style={{ color: 'var(--ok)' }}>{informe.n_creats}</b> {t('encarrecs.informe_creats')}</li>
        <li><b>{informe.n_saltats}</b> {t('encarrecs.informe_saltats')}</li>
      </ul>
      {noAparellats.length > 0 && (
        <div style={{ marginTop: 12, background: 'var(--warn-bg)', border: '0.5px solid var(--warn)',
          color: 'var(--warn)', borderRadius: 8, padding: '8px 12px',
          fontSize: 'var(--fs-body)', lineHeight: 1.5, fontFamily: MONO }}>
          <div style={{ marginBottom: 4 }}>{t('encarrecs.informe_unmatched')}</div>
          {noAparellats.map(([tipus, codis]) => (
            <div key={tipus}>· {tipus}: {[...new Set(codis)].join(', ')}</div>
          ))}
        </div>
      )}
    </Modal>
  )
}

const card = { border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)',
  marginBottom: 16, overflow: 'hidden' }
const ghostBtn = { background: 'var(--white)', color: 'var(--gold)', border: '0.5px solid var(--gold)',
  borderRadius: 6, padding: '7px 14px', fontSize: 'var(--fs-body)', fontWeight: 600, fontFamily: MONO }
