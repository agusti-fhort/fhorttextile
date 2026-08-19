import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"
import useAuthStore from "../store/auth"
import PageMenu from "../components/ui/PageMenu"
import Feedback from "../components/ui/Feedback"
import { apagat, botoPri, botoSec } from "../components/ui/buttons"
import useToc, { anellFocus } from "../components/ui/toc"
import { useEnumeracio } from "../utils/vocabulariDominiFont"

const API = import.meta.env.VITE_API_URL || ""
const MONO = "IBM Plex Mono, monospace"

// ── CONFORMITAT (part B · pantalla 9 · «Configuració inicial») ───────────────────────────────
//
// 🚨 AQUESTA PANTALLA NO TENIA i18n. **Cap** cadena de cara a l'usuari passava per `t()`: vint
// literals catalans escrits a dins («Benvingut a FHORT Textile Tech», «Guardar i continuar →»,
// «Nom de l'empresa *»…). És la porta que el `CLAUDE.md` posa com a guardià de frontend —«tot
// text de cara a l'usuari amb clau `t()` i paritat als tres idiomes»— i era la pantalla on més
// mal fa: **és la PRIMERA que veu un tenant nou**, i un estudi anglès o castellà l'obria en
// català sense cap manera de canviar-ho. Vint-i-dues claus noves, amb paritat ca/en/es.
//
// 🚨 I LA PALETA ERA UNA ALTRA. Nou hex literals que no són de la casa (`#f0f9f0`, `#fff0f0`,
// `#c0dd97`, `#f09595`, `#3b6d11`, `#a32d2d`, `#f5e6d0`, `#f5f0ea`, `#c8b89a`) — entre ells el
// verd i el vermell ANTERIORS a l'alineació del semàfor de la §1b(a), que el bloc A ja va
// migrar a tot el producte. Aquesta pantalla se n'havia quedat fora perquè no els llegia dels
// tokens: se'ls havia escrit.
//
// §6 · LES ACCIONS DE MOTOR SÓN PASSOS DE FLUX. El wizard tenia quatre passos i **cap manera
// de saber on eres**: ni stepper, ni numeral, ni tornar enrere. La seqüència no se l'inventa
// aquest tram —ja era al codi, `step` 0→1→2→3, i és la que el backend serveix—; el que hi entra
// és la FORMA que la norma li dona: FET (verd amb ✓) · ACTUAL (`--sel` + filet d'or) ·
// DISPONIBLE (blanc + `--line`) · BLOQUEJAT (tènue). El pas actual és l'únic que porta blau.
const PASSOS = ['step_intro', 'step_config', 'step_dades', 'step_fi']

function Stepper({ t, actual }) {
  return (
    <div style={{ display: 'flex', gap: 8, marginBottom: 24, flexWrap: 'wrap' }}>
      {PASSOS.map((clau, i) => {
        const fet = i < actual
        const ara = i === actual
        return (
          <div key={clau} style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            padding: '6px 12px', borderRadius: 'var(--r-ctrl)',
            borderWidth: 1, borderStyle: 'solid',
            // El filet d'or de 3px a l'esquerra és el «on soc» de la casa (§1 · §6).
            borderLeftWidth: ara ? 3 : 1,
            borderColor: fet ? 'var(--ok)' : ara ? 'var(--line)' : 'var(--line)',
            borderLeftColor: ara ? 'var(--gold)' : fet ? 'var(--ok)' : 'var(--line)',
            background: fet ? 'var(--ok-bg)' : ara ? 'var(--sel)' : 'var(--panel)',
            color: fet ? 'var(--ok)' : ara ? 'var(--text-main)' : 'var(--text-faint)',
            fontFamily: MONO, fontSize: 'var(--fs-body)', fontWeight: ara ? 600 : 400,
          }}>
            {fet && <i className="ti ti-check" aria-hidden="true" style={{ fontSize: 14, color: 'currentColor' }} />}
            {t(`onboarding.${clau}`)}
          </div>
        )
      })}
    </div>
  )
}

// Una fila de la llista d'estat: ✓/○ + etiqueta + descripció. El check verd i el cercle buit
// són DADA (§1: «la dada porta el color»), i per això conserven el semàfor — amb els tokens.
function FilaEstat({ ok, label, descripcio }) {
  return (
    <div style={{ display: 'flex', gap: 8, padding: '3px 0', fontSize: 'var(--fs-body)' }}>
      <i className={`ti ti-${ok ? 'circle-check' : 'circle'}`} aria-hidden="true"
        style={{ fontSize: 14, color: ok ? 'var(--ok)' : 'var(--text-faint)', flex: 'none' }} />
      <span style={{ color: ok ? 'var(--text-main)' : 'var(--text-soft)' }}>{label}</span>
      <span style={{ marginLeft: 'auto', color: 'var(--text-soft)', fontSize: 'var(--fs-caption)' }}>{descripcio}</span>
    </div>
  )
}

// El tria-unitat: multi-selecció d'un sol valor → la forma d'inclusió de la casa (§1: verd),
// amb els tres estats de `ui/toc` (repòs · triat · hover) i l'anell només amb focus de teclat.
function TriaUnitat({ codi, triat, onTria }) {
  const [toc, gestos] = useToc()
  return (
    <button type="button" onClick={onTria} aria-pressed={triat} {...gestos}
      style={{
        padding: '6px 16px', borderRadius: 'var(--r-pill)', cursor: 'pointer',
        fontFamily: MONO, fontSize: 'var(--fs-body)', fontWeight: triat ? 600 : 400,
        borderWidth: 1, borderStyle: 'solid',
        borderColor: triat ? 'var(--ok)' : 'var(--line)',
        background: triat ? 'var(--ok-bg)' : toc.hover ? 'var(--sel)' : 'var(--panel)',
        color: triat ? 'var(--ok)' : 'var(--text-main)',
        outline: 'none', ...(toc.focus ? anellFocus : null),
      }}>
      {codi}
    </button>
  )
}

export default function OnboardingWizard() {
  const token = useAuthStore(s => s.token) || localStorage.getItem('access_token')
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [step, setStep] = useState(0)
  const [status, setStatus] = useState(null)
  const [config, setConfig] = useState({ nom_empresa: '', unitat_mesura: 'CM', norma_referencia: 'ISO_8559' })
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState(null)
  const [msg, setMsg] = useState(null)
  // LLEI 1 · les unitats venien d'una constant del client (`['CM','INCH']`). Ara de
  // `/vocabulari/` → `unitats_mesura`, com a Configuració general. Sense vocabulari no s'ofereix
  // cap unitat i es diu; la que ja hi ha al formulari es conserva (és el default del backend).
  const { codis: unitats } = useEnumeracio('unitats_mesura')

  useEffect(() => {
    fetch(`${API}/api/v1/onboarding/status/`, {
      headers: { Authorization: `Bearer ${token}` }
    }).then(r => r.json()).then(setStatus).catch(() => {})
  }, [token])

  const saveConfig = async () => {
    const r = await fetch(`${API}/api/v1/onboarding/config/`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    })
    const d = await r.json()
    if (r.ok) { setMsg({ type: 'ok', text: d.missatge }); setStep(2) }
    else setMsg({ type: 'err', text: d.error })
  }

  const uploadExcel = async () => {
    if (!file) return
    setUploading(true)
    const fd = new FormData()
    fd.append('file', file)
    const r = await fetch(`${API}/api/v1/onboarding/setup-from-excel/`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: fd,
    })
    const d = await r.json()
    if (r.ok) { setUploadResult(d); setStep(3) }
    else setMsg({ type: 'err', text: d.error })
    setUploading(false)
  }

  return (
    <>
      {/* §8b · menú de pantalla; sense seccions, queda la fletxa (§8b.2). La fletxa és, a més,
          l'ÚNICA sortida que aquesta pantalla tenia: el wizard no en donava cap fins al final. */}
      <div style={{ margin: '-1.5rem -1.5rem 0' }}>
        <PageMenu backTo="/" backTitle={t('onboarding.back_title')} />
      </div>

      {/* `width: '100%'` no és redundant: en una columna FLEX (el `<main>` ho és des del
          §8b-quater(3)) un `margin: 0 auto` anul·la l'`align-items: stretch` i la caixa passa
          a mida de CONTINGUT. Mesurat: 600 → 505.7. En bloc no canvia res. */}
      <div style={{ width: '100%', maxWidth: 600, margin: '0 auto', paddingTop: 16 }}>
        {/* §8b.3 · identitat sobre el fons. El títol anava en DAURAT: el daurat és marca, i el
            títol d'una pàgina és tinta principal (§8c: el daurat no pinta ni números ni rètols).
            L'ull de cella («FHORT Textile Tech · Onboarding») deia el nom del producte, que ja
            és a la top bar i al molla de pa; queda la secció. */}
        <div style={{ marginBottom: 8, fontSize: 'var(--fs-label)', fontWeight: 600, color: 'var(--text-soft)', letterSpacing: '.08em', textTransform: 'uppercase', fontFamily: MONO }}>
          {t('onboarding.eyebrow')}
        </div>
        <h1 style={{ fontSize: 'var(--fs-h1)', lineHeight: '28px', fontWeight: 500, color: 'var(--text-main)', margin: '0 0 24px' }}>
          {t('onboarding.title')}
        </h1>

        <Stepper t={t} actual={step} />

        {/* Els missatges d'estat passen pel bastiment de la casa (§9: «els estats asíncrons van
            amb el bastiment de la casa, zero vocabulari nou»). Hi havia una caixa pròpia amb
            quatre hex literals, dos dels quals eren el verd i el vermell ANTERIORS a la §1b(a). */}
        <Feedback feedback={msg} onDismiss={() => setMsg(null)} />

        {step === 0 && (
          <div>
            <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)', lineHeight: 1.7, marginBottom: 20 }}>
              {t('onboarding.intro')}
            </p>
            {status && (
              <div style={{ padding: 16, border: '1px solid var(--line)', borderRadius: 'var(--r-card)', background: 'var(--panel)', fontSize: 'var(--fs-body)', marginBottom: 20 }}>
                {/* §8c · el percentatge és un KPI i va NEUTRE: anava en daurat. */}
                <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)', marginBottom: 8 }}>
                  {t('onboarding.estat_actual')}: <strong style={{ color: 'var(--text-main)' }}>
                    {t('onboarding.percent_done', { n: status.percentatge })}</strong>
                </div>
                {Object.entries(status.steps || {}).map(([k, s]) => (
                  <FilaEstat key={k} ok={s.ok} label={s.label} descripcio={s.descripcio} />
                ))}
              </div>
            )}
            {/* §5.1 · l'acció que completa la feina d'aquest pas, i l'única: blava. Anava amb
                fons `--gold-pale` (token ELIMINAT) i tinta daurada. */}
            <button onClick={() => setStep(1)} style={botoPri}>
              {t('onboarding.begin')}
              <i className="ti ti-arrow-right" aria-hidden="true" style={{ fontSize: 14, color: 'currentColor' }} />
            </button>
          </div>
        )}

        {step === 1 && (
          <div>
            <div style={{ marginBottom: 16 }}>
              <label htmlFor="ob-nom" style={etiqueta}>{t('onboarding.nom_empresa')}</label>
              <input id="ob-nom" value={config.nom_empresa} onChange={e => setConfig(c => ({ ...c, nom_empresa: e.target.value }))}
                placeholder={t('onboarding.nom_empresa_ph')} style={camp} />
            </div>
            <div style={{ marginBottom: 16 }}>
              <span style={etiqueta}>{t('onboarding.unitat')}</span>
              <div style={{ display: 'flex', gap: 8 }}>
                {unitats === null
                  ? <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-faint)', fontStyle: 'italic' }}>{t('onboarding.no_vocab')}</span>
                  : unitats.map(u => (
                    <TriaUnitat key={u} codi={u} triat={config.unitat_mesura === u}
                      onTria={() => setConfig(c => ({ ...c, unitat_mesura: u }))} />
                  ))}
              </div>
            </div>
            <button onClick={saveConfig} disabled={!config.nom_empresa}
              style={{ ...botoPri, ...(!config.nom_empresa ? apagat : null) }}>
              {t('onboarding.save_next')}
              <i className="ti ti-arrow-right" aria-hidden="true" style={{ fontSize: 14, color: 'currentColor' }} />
            </button>
          </div>
        )}

        {step === 2 && (
          <div>
            <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)', marginBottom: 16, lineHeight: 1.6 }}>
              {t('onboarding.file_intro')}
            </p>
            <input type="file" accept=".xlsx" aria-label={t('onboarding.upload')}
              onChange={e => setFile(e.target.files[0])}
              style={{ marginBottom: 12, fontSize: 'var(--fs-body)', fontFamily: MONO }} />
            {file && (
              <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)', marginBottom: 12, fontFamily: MONO }}>
                {file.name} · {(file.size / 1024).toFixed(0)} KB
              </div>
            )}
            <button onClick={uploadExcel} disabled={!file || uploading}
              style={{ ...botoPri, ...((!file || uploading) ? apagat : null) }}>
              <i className="ti ti-upload" aria-hidden="true" style={{ fontSize: 14, color: 'currentColor' }} />
              {uploading ? t('onboarding.uploading') : t('onboarding.upload')}
            </button>
          </div>
        )}

        {step === 3 && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 'var(--fs-body)', fontWeight: 600, color: 'var(--ok)', marginBottom: 16 }}>
              <i className="ti ti-circle-check" aria-hidden="true" style={{ fontSize: 16, color: 'currentColor' }} />
              {t('onboarding.done_title')}
            </div>
            {uploadResult && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)', marginBottom: 8 }}>{t('onboarding.loaded')}</div>
                {Object.entries(uploadResult.resultats || {}).map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', gap: 8, fontSize: 'var(--fs-body)', padding: '3px 0' }}>
                    <i className={`ti ti-${v.ok ? 'circle-check' : 'circle-x'}`} aria-hidden="true"
                      style={{ fontSize: 14, color: v.ok ? 'var(--ok)' : 'var(--err)', flex: 'none' }} />
                    {/* La clau del resultat és DADA del backend i s'ensenya crua, com un codi de
                        POM: no es tradueix i no s'inventa cap etiqueta per a ella. */}
                    <span style={{ color: 'var(--text-main)', fontFamily: MONO }}>{k}</span>
                    {v.count !== undefined && <span style={{ marginLeft: 'auto', color: 'var(--text-soft)', fontFamily: MONO }}>{v.count}</span>}
                  </div>
                ))}
              </div>
            )}
            {/* Ja no hi ha res per completar aquí: anar al tauler és una PORTA (§5.3). */}
            <button onClick={() => navigate('/')} style={botoSec}>
              {t('onboarding.go_dashboard')}
              <i className="ti ti-chevron-right" aria-hidden="true" style={{ fontSize: 14, color: 'currentColor' }} />
            </button>
          </div>
        )}
      </div>
    </>
  )
}

// §2 · rètol de camp: 10px MAJÚSCULES amb tracking. §8c · control de la casa: vora `--line`,
// radi 6, alçada única.
const etiqueta = {
  fontSize: 'var(--fs-label)', fontWeight: 600, letterSpacing: '.08em', textTransform: 'uppercase',
  color: 'var(--text-soft)', fontFamily: MONO, display: 'block', marginBottom: 6,
}
const camp = {
  width: '100%', boxSizing: 'border-box', fontFamily: MONO, fontSize: 'var(--fs-body)',
  padding: '6px 10px', height: 32, border: '1px solid var(--line)',
  borderRadius: 'var(--r-ctrl)', background: 'var(--panel)', color: 'var(--text-main)',
}
