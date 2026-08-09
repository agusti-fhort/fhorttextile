import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import { recursos as recursosApi } from '../api/endpoints'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import Modal from '../components/ui/Modal'
import Table from '../components/ui/Table'
import { botoTer, selS } from '../components/ui/buttons'
import PageMenu from '../components/ui/PageMenu'
import Badge from '../components/ui/Badge'

// P7 (Federació v2) — la superfície del Brand sobre els seus RECURSOS.
//
// UN RECURS ÉS UN ESTUDI, NO UNA CASA DE GENT. Aquesta pàgina ensenya codi, nom i estat del
// pont, i res més: ni qui hi treballa, ni quantes hores, ni quina feina. No hi falta res —
// és el contracte de la federació, i el backend tampoc ho envia.
//
// EL TOKEN ES VEU UN SOL COP. Arriba a la resposta de l'alta i es mostra en un modal propi.
// No es desa a cap estat de llista ni es torna a demanar mai: no hi ha endpoint que el torni.
const MONO = 'IBM Plex Mono, monospace'
// §5.4 · accions de FILA: terciàries. La de revocar hi sobreescriu la tinta i la vora i queda
// DESTRUCTIVA amb vora, mai plena en repòs (§5.5).
const actBtn = {
  ...botoTer, padding: '4px 10px',
}

// L'ESTAT DEL VINCLE, amb el badge de la casa. Això era un mapa de parells fons/tinta SENSE
// VORA (la §1 la vol sempre: «fons suau + tinta del color + VORA FINA DEL MATEIX COLOR, píndola
// sempre»), amb `--warn` de tinta —1.86:1 sobre el seu fons— i `--gray-l`/`--gray` per al
// revocat. `ui/Badge` ja té les tres formes i les té bé; aquí només queda la CORRESPONDÈNCIA
// estat → variant, que és el que aquesta pantalla sap i el component no.
// 🚩 L'enumeració ja NO es declara aquí: els codis surten de `/vocabulari/` →
// `estats_vincle_tenant` (publicada per al lot comercial). Això és un mapa de PELL indexat pel
// codi que arriba, no una llista de valors possibles — el mateix criteri que `FASE_COLORS` del
// Gantt: que les claus coincideixin amb una enumeració no el converteix en vocabulari.
const ESTAT_VARIANT = { ACTIU: 'ok', ATURAT: 'warn', REVOCAT: 'gray' }

export default function Recursos() {
  const { t, i18n } = useTranslation()
  const dateLocale = i18n.language === 'es' ? 'es-ES' : i18n.language === 'en' ? 'en-GB' : 'ca-ES'
  const canEdit = useAuthStore(s => s.user?.capabilities?.includes('configure')) ?? false

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [items, setItems] = useState([])
  const [feedback, setFeedback] = useState(null)
  const [saving, setSaving] = useState(false)
  const [altaOpen, setAltaOpen] = useState(false)
  const [tokenNou, setTokenNou] = useState(null)   // { studio_codi, token } — efímer, mai a la llista

  const load = useCallback(() => {
    setError(false)
    return recursosApi.list()
      .then(r => setItems(r.data?.results ?? (Array.isArray(r.data) ? r.data : [])))
      .catch(() => setError(true))
  }, [])

  useEffect(() => {
    let alive = true
    load().finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [load])

  const fmtDate = (v) => v ? new Date(v).toLocaleDateString(dateLocale, { day: '2-digit', month: '2-digit', year: 'numeric' }) : '—'

  // Els tres actes comparteixen forma. `revocar` demana confirmació a part: és terminal i el
  // botó no ha de poder-ho fer d'un sol clic distret.
  const acte = (r, nom) => {
    if (nom === 'revocar' && !window.confirm(t('recursos.confirm_revocar', { codi: r.studio_codi }))) return
    setSaving(true); setFeedback(null)
    recursosApi[nom](r.id)
      .then(() => load())
      .then(() => setFeedback({ type: 'ok', text: t(`recursos.done_${nom}`) }))
      .catch(e => setFeedback({ type: 'err', text: e?.response?.data?.error || t('recursos.error') }))
      .finally(() => setSaving(false))
  }

  const columns = [
    { key: 'studio_codi', label: t('recursos.col_codi'),
      // §8e · el daurat és marca, no dada; i 700 no és cap dels tres pesos de la casa.
      render: r => <span style={{ fontFamily: MONO, fontWeight: 600, color: 'var(--text-main)' }}>{r.studio_codi}</span> },
    { key: 'studio_nom', label: t('recursos.col_nom'),
      render: r => r.studio_nom || <span style={{ color: 'var(--text-faint)' }}>—</span> },
    { key: 'estat', label: t('recursos.col_estat'), render: r => (
      <Badge variant={ESTAT_VARIANT[r.estat] || 'gray'}>
        {t(`recursos.estat_${r.estat}`, r.estat)}
      </Badge>
    ) },
    { key: 'created_at', label: t('recursos.col_data'),
      render: r => <span style={{ fontFamily: MONO, color: 'var(--text-soft)' }}>{fmtDate(r.created_at)}</span> },
    ...(canEdit ? [{ key: '_a', label: '', align: 'right', render: r => (
      <span style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
        {r.estat === 'ACTIU' && (
          <button onClick={() => acte(r, 'aturar')} disabled={saving} style={actBtn}>{t('recursos.aturar')}</button>
        )}
        {r.estat === 'ATURAT' && (
          <button onClick={() => acte(r, 'reactivar')} disabled={saving} style={actBtn}>{t('recursos.reactivar')}</button>
        )}
        {/* REVOCAT és terminal: un vincle mort no ofereix cap acció, només queda com a rastre. */}
        {r.estat !== 'REVOCAT' && (
          <button onClick={() => acte(r, 'revocar')} disabled={saving}
            style={{ ...actBtn, color: 'var(--err)', borderColor: 'var(--err)' }}>{t('recursos.revocar')}</button>
        )}
      </span>) }] : []),
  ]

  return (
    <>
      {/* §8b · MENÚ DE PANTALLA, i l'acció hi puja: «Nou vincle» era un botó blau a la
          capçalera, i la §8e diu que l'acció primària pujada al menú deixa de ser botó i deixa
          de ser blava («el blau viu al contingut; el menú té el seu llenguatge»). Només hi és
          per a qui té la capacitat: el gate `brand_configure` no es toca. */}
      <div style={{ margin: '-1.5rem -1.5rem 0' }}>
        <PageMenu
          backTo="/"
          backTitle={t('recursos.back_title')}
          items={canEdit ? [{ key: 'nou', label: t('recursos.new'), onClick: () => setAltaOpen(true) }] : []}
        />
      </div>

    <div style={{ minWidth: 0, maxWidth: 900, paddingTop: 16 }}>
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 'var(--fs-h1)', lineHeight: '28px', fontWeight: 500, marginBottom: 4, color: 'var(--text-main)', fontFamily: MONO }}>{t('recursos.title')}</h1>
        <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)', fontFamily: MONO }}>{t('recursos.subtitle')}</p>
      </div>

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      {loading ? <Center>{t('recursos.loading')}</Center>
        : error ? <Center>{t('recursos.error')}</Center>
          : (
            <div style={{ border: '1px solid var(--line)', borderRadius: 'var(--r-card)', background: 'var(--panel)', overflowX: 'auto' }}>
              <Table columns={columns} data={items} loading={false} empty={t('recursos.empty')} />
            </div>
          )}

      {altaOpen && (
        <AltaModal t={t} saving={saving} setSaving={setSaving}
          onCancel={() => setAltaOpen(false)}
          onError={(text) => setFeedback({ type: 'err', text })}
          onCreated={(data) => {
            setAltaOpen(false)
            setTokenNou({ studio_codi: data.studio_codi, token: data.token })
            load()
          }} />
      )}

      {tokenNou && <TokenModal t={t} dades={tokenNou} onClose={() => setTokenNou(null)} />}
    </div>
    </>
  )
}

// Alta: només demana el codi del Studio. El brand no es demana perquè no es pot triar — és
// sempre el tenant de la sessió, i el backend l'ignoraria si viatgés al payload.
function AltaModal({ t, saving, setSaving, onCancel, onCreated, onError }) {
  const [codi, setCodi] = useState('')
  const net = codi.trim().toUpperCase()
  const invalid = net.length !== 3   // els codi_tenant són identitat estable de 3 chars

  const submit = () => {
    if (invalid) return
    setSaving(true)
    recursosApi.create({ studio_codi: net })
      .then(r => onCreated(r.data))
      // El backend discrimina per `code` (link_exists, invalid_studio…); el text ja ve fet i
      // és el que més sap del cas concret. La clau i18n és el fallback, no la font.
      .catch(e => onError(e?.response?.data?.error || t('recursos.error')))
      .finally(() => setSaving(false))
  }

  return (
    <Modal title={t('recursos.new_title')} subtitle={t('recursos.new_help')}
      cancelLabel={t('recursos.cancel')} confirmLabel={t('recursos.create')}
      onCancel={onCancel} onConfirm={submit} confirmDisabled={saving || invalid}>
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 'var(--fs-label)', textTransform: 'uppercase', letterSpacing: '.04em',
          color: 'var(--text-soft)', marginBottom: 4, fontFamily: MONO }}>{t('recursos.col_codi')}</div>
        <input value={codi} maxLength={3} autoFocus
          onChange={e => setCodi(e.target.value.toUpperCase())}
          placeholder={t('recursos.codi_ph')}
          style={{ ...selS, width: '100%', textTransform: 'uppercase', letterSpacing: '.15em' }} />
      </div>
    </Modal>
  )
}

// El token, un sol cop. Sense botó de tancar implícit (l'overlay tanca igual, però el text ho
// diu abans): el que importa és que ningú el tanqui creient que el podrà tornar a mirar.
function TokenModal({ t, dades, onClose }) {
  const [copiat, setCopiat] = useState(false)
  const copia = () => {
    navigator.clipboard?.writeText(dades.token)
      .then(() => setCopiat(true))
      .catch(() => {})
  }

  return (
    <Modal title={t('recursos.token_title', { codi: dades.studio_codi })}
      cancelLabel={t('recursos.token_close')} confirmLabel={copiat ? t('recursos.token_copied') : t('recursos.token_copy')}
      onCancel={onClose} onConfirm={copia}>
      <div style={{
        background: 'var(--warn-state-bg)', border: '1px solid var(--warn-state)', color: 'var(--warn-ink)',
        borderRadius: 'var(--r-ctrl)', padding: '8px 12px', marginBottom: 12,
        fontSize: 'var(--fs-body)', lineHeight: 1.5, fontFamily: MONO,
      }}>
        <i className="ti ti-alert-triangle" style={{ marginRight: 6 }} aria-hidden="true" />
        {t('recursos.token_warn')}
      </div>
      <div style={{
        fontFamily: MONO, fontSize: 'var(--fs-body)', wordBreak: 'break-all', userSelect: 'all',
        background: 'var(--bg-page)', borderRadius: 'var(--r-ctrl)', padding: '10px 12px', color: 'var(--text-main)',
      }}>{dades.token}</div>
    </Modal>
  )
}
