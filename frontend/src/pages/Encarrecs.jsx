import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import { encarrecs as encarrecsApi } from '../api/endpoints'
import Feedback from '../components/ui/Feedback'
import Modal from '../components/ui/Modal'
import PageMenu from '../components/ui/PageMenu'
import { EstatBadge } from '../components/commercial/estats'
import { Comptador, FilaIdentitat, EstatBuit, buit, forceBarra } from '../components/llista/ChromLlista'
import { botoPri, botoSec, apagat } from '../components/ui/buttons'

// P8 (Federació v2) — la SAFATA del Studio: què m'han encomanat i què me n'he portat a casa.
//
// MIRALL DE «RECURSOS» (la pàgina del Brand), i a posta: allà es governa amb qui es pot
// comptar; aquí es treballa el que t'han encomanat. Cap de les dues ensenya l'altra meitat.
//
// L'ESTAT NO ÉS UN CAMP QUE ES PUGUI DESINCRONITZAR: PENDENT/TRASPASSAT el calcula el backend
// comparant el codi del Brand amb el que ja tinc al meu schema. Si algú esborra el model
// local, la fila torna a PENDENT tot sola i el traspàs el tornarà a crear.
//
// ── TRES COSES QUE ES DIUEN EN VEU ALTA ──────────────────────────────────────────────────
//
// 1 · **NO ES UNA LLISTA CANONICA, i es a posta.** La §8e descriu la graella d'una llista d'UNA
//    entitat; aixo son GRUPS PER BRAND, cadascun amb la seva accio de traspas i el seu propi
//    comptador. Aplanar-ho a una taula plana perdria justament el que la pantalla diu: de quin
//    Brand ve cada model i quants en queden per cada un. El que si que agafa de la §8b es
//    l'estructura de pagina (menu + identitat) i tota la pell.
//
// 2 · **L'ESTAT VE DE `/vocabulari/`** (`estats_locals_encarrec`). Aqui hi havia un `ESTAT_STYLE`
//    amb els dos codis escrits, i el cas es especial i val la pena dir-lo: `estat_local` NO es
//    un camp ni uns `choices` — el backend el CALCULA comparant el codi del Brand amb el que ja
//    tinc al meu schema. Que la dada sigui derivada no la fa menys enumeracio: el mapa del
//    client declarava el conjunt tancat de valors possibles, que es el que la llei prohibeix. El
//    dia que la federacio en retorni un tercer («traspassat pero divergent»), una pantalla que
//    en declara dos no en pinta tres: en pinta dos i menteix.
//
// 3 · **«Traspassar tots» DEIXA DE SER UN GHOST DAURAT.** La §5.4 jubila el ghost daurat com a
//    boto. Les dues accions del grup son germanes —traspassar els TRIATS i traspassar-los TOTS—
//    i per tant: la dels triats es la PRIMARIA (es el gest que has vingut a fer) i la de tots,
//    SECUNDARIA de la casa.
const MONO = 'IBM Plex Mono, monospace'

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

  const totalModels = useMemo(
    () => grups.reduce((a, g) => a + (g.models?.length || 0), 0), [grups])

  return (
    <>
      <div style={forceBarra}>
        <PageMenu backTo="/" backTitle={t('encarrecs.back_title')} />
      </div>

      <div style={{ minWidth: 0, maxWidth: 1000 }}>
        {/* §8e · el comptador ES selecció i ELS VALORS MANEN: aquí el que importa és quants
            encàrrecs queden PENDENTS sobre el total encomanat, que és la pregunta que la safata
            respon. El subtítol se'n va (esmena d'Agus del 08/08) i el que deia —«en queden N»—
            passa a ser el número, que és on es llegeix d'un cop d'ull. */}
        <FilaIdentitat>
          <Comptador valor={totalPendents} total={totalModels} etiqueta={t('encarrecs.entity')} />
        </FilaIdentitat>

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      {loading ? <EstatBuit>{t('encarrecs.loading')}</EstatBuit>
        : error ? <EstatBuit>{t('encarrecs.error')}</EstatBuit>
          : grups.length === 0 ? <EstatBuit>{t('encarrecs.empty')}</EstatBuit>
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
          <p style={{ fontSize: 'var(--fs-body)', lineHeight: 1.5, color: 'var(--text-soft)',
            fontFamily: MONO, margin: 0 }}>
            {t('encarrecs.confirm_help')}
          </p>
        </Modal>
      )}

      {informe && <InformeModal informe={informe} t={t} onClose={() => setInforme(null)} />}
      </div>
    </>
  )
}

function GrupBrand({ g, t, canEdit, busy, sel, toggle, pendents, triats, onTraspassar }) {
  if (g.error) {
    return (
      <div style={{ ...card, padding: '14px 16px', color: 'var(--err)', fontFamily: MONO,
        fontSize: 'var(--fs-body)' }}>
        {t('encarrecs.brand_missing', { codi: g.brand_codi })}
      </div>
    )
  }
  return (
    <div style={card}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
        padding: '12px 16px',
        borderBottomWidth: 1, borderBottomStyle: 'solid', borderBottomColor: 'var(--line)' }}>
        {/* El codi del Brand anava en --gold pes 700: el daurat és marca i selecció, no una
            dada. Aquí la reina és el NOM del Brand; el codi és la seva referència. */}
        <span style={{ fontFamily: MONO, fontSize: 'var(--fs-caption)', letterSpacing: '.08em',
          color: 'var(--text-soft)', fontWeight: 600 }}>{g.brand_codi}</span>
        <span style={{ fontSize: 'var(--fs-h3)', fontWeight: 600, color: 'var(--text-main)' }}>{g.brand_nom}</span>
        <span style={{ fontFamily: MONO, fontSize: 'var(--fs-caption)', color: 'var(--text-soft)' }}>
          {t('encarrecs.comptador', { p: g.n_pendents, tot: g.models.length })}
        </span>
        {canEdit && pendents.length > 0 && (
          <span style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
            {/* §5.1 · LA PRIMÀRIA és traspassar els TRIATS: és el gest que has vingut a fer.
                §5.7 · deshabilitat = BAIXA EL FONS, no la tinta (l'`opacity: 0.5` apagava també
                el text i el deixava per sota d'AA, i el que diu un botó apagat és justament el
                que ara no es pot fer). */}
            <button type="button" onClick={() => onTraspassar(triats.map(m => m.codi_intern))}
              disabled={busy || triats.length === 0}
              style={{ ...botoPri, ...((busy || triats.length === 0) ? apagat : null) }}>
              <i className="ti ti-download" style={{ fontSize: 14, color: 'currentColor' }} aria-hidden="true" />
              {t('encarrecs.traspassar_n', { n: triats.length })}
            </button>
            <button type="button" onClick={() => onTraspassar(null)} disabled={busy}
              style={{ ...botoSec, ...(busy ? apagat : null) }}>
              {t('encarrecs.traspassar_tots')}
            </button>
          </span>
        )}
      </div>

      {g.models.length === 0
        ? <div style={{ padding: 16, textAlign: 'center' }}>
            <span style={buit}>{t('encarrecs.grup_buit')}</span>
          </div>
        : g.models.map(m => {
          const pendent = m.estat_local === 'PENDENT'
          return (
            <label key={m.codi_intern} style={{
              display: 'flex', alignItems: 'center', gap: 12, padding: '9px 16px',
              borderBottomWidth: 1, borderBottomStyle: 'solid', borderBottomColor: 'var(--line-soft)',
              cursor: (canEdit && pendent) ? 'pointer' : 'default',
            }}>
              <input type="checkbox" disabled={!canEdit || !pendent}
                checked={sel.has(m.codi_intern)} onChange={() => toggle(m.codi_intern)}
                style={{ width: 14, height: 14, accentColor: 'var(--gold)', opacity: pendent ? 1 : 0.25 }} />
              <span style={{ fontFamily: MONO, fontWeight: 600, minWidth: 150 }}>{m.codi_intern}</span>
              <span style={{ flex: 1, fontSize: 'var(--fs-body)', minWidth: 0, overflow: 'hidden',
                textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.nom_prenda || '—'}</span>
              <span style={{ fontFamily: MONO, fontSize: 'var(--fs-caption)', color: 'var(--text-soft)' }}>
                {m.temporada}{m.any ? ` ${m.any}` : ''}
              </span>
              <EstatBadge clau="estats_locals_encarrec" codi={m.estat_local}>
                {t(`encarrecs.estat_${m.estat_local}`, m.estat_local)}
              </EstatBadge>
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
      {/* §1b(d) · el taronja de TEXT s'enfosqueix (`--warn-ink`, AA); la MARCA —la vora— es
          queda al to viu. I el radi passa a `--r-ctrl`: el 8 no és cap dels tres del sistema. */}
      {noAparellats.length > 0 && (
        <div style={{ marginTop: 12, background: 'var(--warn-state-bg)',
          borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--warn-state)',
          color: 'var(--warn-ink)', borderRadius: 'var(--r-ctrl)', padding: '8px 12px',
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

const card = {
  borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--line)',
  borderRadius: 'var(--r-card)', background: 'var(--panel)',
  marginBottom: 16, overflow: 'hidden',
}
