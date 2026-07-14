import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import CustomerSelector from '../components/CustomerSelector'
import BulkImportReconciliation from '../components/BulkImportReconciliation'
import { bulkImport } from '../api/endpoints'

// Import massiu de models per Excel — modal stepper de 4 passos.
// 1 Client+fitxer · 2 Preview · 3 Confirmació · 4 Resultat. Reutilitza CustomerSelector (Commit 0).
const MONO = 'IBM Plex Mono, monospace'
const GOLD = 'var(--gold, #c27a2a)'
const BORDER = 'var(--gray-l)'

// Baixa un Blob com a fitxer. Filename de Content-Disposition si hi és, si no el fallback.
function downloadBlob(blob, filename) {
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(link.href)
}

function filenameFromHeaders(res, fallback) {
  const cd = res?.headers?.['content-disposition'] || ''
  const m = /filename="?([^"]+)"?/.exec(cd)
  return (m && m[1]) || fallback
}

// Quan una resposta blob és en realitat un error JSON, el llegim com a text i el parsegem.
async function blobErrorMessage(err, fallback) {
  try {
    const data = err?.response?.data
    if (data && typeof data.text === 'function') {
      const txt = await data.text()
      const j = JSON.parse(txt)
      return j.error || j.detail || fallback
    }
  } catch { /* no-op */ }
  return err?.response?.data?.error || err?.message || fallback
}

const STEP_KEYS = ['step1', 'step2', 'step3', 'step4']

export default function BulkImportWizard() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const me = useAuthStore(s => s.user)
  const canConfigure = !!me?.capabilities?.includes('configure')

  const [step, setStep] = useState(1)
  const [error, setError] = useState('')
  // Pas 1
  const [customerId, setCustomerId] = useState(null)
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  // Resultat d'upload
  const [importId, setImportId] = useState(null)
  const [resum, setResum] = useState(null)
  // Pas 2 — conciliació (què ha entès el sistema de cada cel·la + quins codis ocuparà)
  const [rec, setRec] = useState(null)
  // Pas 3/4
  const [committing, setCommitting] = useState(false)
  const [commitStats, setCommitStats] = useState(null)

  // Gate: el Pas 2 només es desbloqueja quan l'upload ha retornat resum (handleUpload fa
  // setStep(2) NOMÉS si el POST upload ha respost OK amb import_id). El stepper no és clicable.
  const downloadTemplate = async () => {
    if (!customerId) { setError(t('bulk_import.err_no_customer')); return }
    setError('')
    try {
      const res = await bulkImport.template(customerId)
      downloadBlob(res.data, filenameFromHeaders(res, 'plantilla_colleccio.xlsx'))
    } catch (err) {
      setError(await blobErrorMessage(err, t('bulk_import.err_template')))
    }
  }

  // Pujar → CONCILIAR. El pas 2 no s'obre fins que el sistema pot dir què ha entès de cada
  // cel·la: mai s'ensenya un "20 files OK" que només ha mirat el format.
  const handleUpload = async () => {
    if (!customerId) { setError(t('bulk_import.err_no_customer')); return }
    if (!file) { setError(t('bulk_import.err_select_file')); return }
    setUploading(true); setError('')
    try {
      const fd = new FormData()
      fd.append('customer_id', customerId)
      fd.append('file', file)
      const res = await bulkImport.upload(fd)
      setImportId(res.data.import_id)
      setResum(res.data.resum)

      const rec = await bulkImport.reconciliation(res.data.import_id)
      setRec(rec.data)
      setStep(2)
    } catch (err) {
      setError(err?.response?.data?.error || t('bulk_import.err_upload'))
    } finally {
      setUploading(false)
    }
  }

  const downloadErrors = async () => {
    setError('')
    try {
      const res = await bulkImport.errorsReport(importId)
      downloadBlob(res.data, filenameFromHeaders(res, 'errors_import.xlsx'))
    } catch (err) {
      setError(await blobErrorMessage(err, t('bulk_import.err_report')))
    }
  }

  const handleCommit = async () => {
    setCommitting(true); setError('')
    try {
      const res = await bulkImport.commit(importId)
      setCommitStats(res.data)
      setStep(4)
    } catch (err) {
      setError(err?.response?.data?.error || t('bulk_import.err_commit'))
    } finally {
      setCommitting(false)
    }
  }

  const errCount = resum?.errors ?? 0
  // El número que entrarà de debò surt de la CONCILIACIÓ, no del recompte de format.
  const importables = rec?.resum?.importables ?? 0

  return (
    <div style={{ maxWidth: 920, margin: '0 auto', padding: '2rem 1rem' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 16, marginBottom: 18 }}>
        <div>
          <h1 style={{ fontFamily: MONO, fontSize: 'var(--fs-h1)', fontWeight: 500, margin: 0 }}>{t('bulk_import.title')}</h1>
          <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontWeight: 300, margin: '4px 0 0' }}>{t('bulk_import.subtitle')}</p>
        </div>
        <button type="button" onClick={() => navigate('/models')} style={linkBtn}>✕ {t('bulk_import.cancel')}</button>
      </div>

      <Stepper step={step} t={t} />

      {error && <div style={errBox}>{error}</div>}

      <div style={card}>
        {/* ───── PAS 1 — Client + fitxer ───── */}
        {step === 1 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            <Field label={t('bulk_import.customer_label')}>
              <CustomerSelector value={customerId} onChange={setCustomerId} allowCreate={canConfigure} onError={setError} />
            </Field>

            <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <button type="button" onClick={downloadTemplate} disabled={!customerId} style={ghostBtn(!customerId)}>
                <i className="ti ti-download" /> {t('bulk_import.download_template')}
              </button>
              <span style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)' }}>{t('bulk_import.download_template_hint')}</span>
            </div>

            <div
              onDragOver={e => e.preventDefault()}
              onDrop={e => { e.preventDefault(); setFile(e.dataTransfer.files[0]) }}
              onClick={() => document.getElementById('bulk-file').click()}
              style={{
                border: `2px dashed ${BORDER}`, borderRadius: 12, padding: '2.5rem 2rem',
                textAlign: 'center', cursor: 'pointer', background: file ? '#f0f9f0' : 'var(--white)',
              }}>
              <input id="bulk-file" type="file" accept=".xlsx,.xls" style={{ display: 'none' }}
                onChange={e => setFile(e.target.files[0])} />
              <i className="ti ti-file-spreadsheet" style={{ fontSize: 30, color: GOLD }} />
              <div style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, marginTop: 8 }}>
                {file ? file.name : t('bulk_import.drop_zone')}
              </div>
              <div style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', marginTop: 4 }}>{t('bulk_import.drop_hint')}</div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button type="button" onClick={handleUpload} disabled={!customerId || !file || uploading} style={primaryBtn(!customerId || !file || uploading)}>
                {uploading ? t('bulk_import.uploading') : t('bulk_import.upload_btn')}
              </button>
            </div>
          </div>
        )}

        {/* ───── PAS 2 — Conciliació (què ha entès el sistema, abans que res s'escrigui) ───── */}
        {step === 2 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <BulkImportReconciliation rec={rec} />

            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10 }}>
              {errCount > 0 ? (
                <button type="button" onClick={downloadErrors} style={ghostBtn(false)}>
                  <i className="ti ti-download" /> {t('bulk_import.download_errors')}
                </button>
              ) : <span />}
              <button type="button" onClick={() => setStep(3)} style={primaryBtn(false)}>{t('bulk_import.next')} →</button>
            </div>
          </div>
        )}

        {/* ───── PAS 3 — Confirmació ───── */}
        {step === 3 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            <p style={{ fontFamily: MONO, fontSize: 'var(--fs-h3)' }}>
              {t('bulk_import.confirm_text', { ok: importables, conjunts: resum?.conjunts ?? 0, errors: errCount })}
            </p>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <button type="button" onClick={() => setStep(2)} style={ghostBtn(false)}>← {t('bulk_import.back')}</button>
              {/* El botó diu el número REAL que entrarà: el de la conciliació que el tècnic ha vist. */}
              <button type="button" onClick={handleCommit} disabled={importables === 0 || committing} style={primaryBtn(importables === 0 || committing)}>
                {committing ? t('bulk_import.importing') : t('bulk_import.import_n_btn', { n: importables })}
              </button>
            </div>
          </div>
        )}

        {/* ───── PAS 4 — Resultat ───── */}
        {step === 4 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ fontFamily: MONO, fontSize: 'var(--fs-h3)', fontWeight: 600, color: 'var(--ok)' }}>
              ✓ {t('bulk_import.result_created', { n: commitStats?.models ?? 0 })}
            </div>
            {errCount > 0 && (
              <div style={{ fontSize: 'var(--fs-body)', color: GOLD }}>
                {t('bulk_import.result_errors_pending', { errors: errCount })}
                <button type="button" onClick={downloadErrors} style={{ ...ghostBtn(false), marginLeft: 10 }}>
                  <i className="ti ti-download" /> {t('bulk_import.download_errors')}
                </button>
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button type="button" onClick={() => navigate(`/models?customer=${customerId}`)} style={ghostBtn(false)}>
                {t('bulk_import.view_models')}
              </button>
              <button type="button" onClick={() => navigate('/models')} style={primaryBtn(false)}>{t('bulk_import.close')}</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ───────────────────────────── UI atoms ─────────────────────────────

function Stepper({ step, t }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 0, marginBottom: 20 }}>
      {STEP_KEYS.map((key, i) => {
        const n = i + 1
        const done = n < step
        const active = n === step
        return (
          <div key={key} style={{ display: 'flex', alignItems: 'center', flex: i < STEP_KEYS.length - 1 ? 1 : '0 0 auto' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{
                width: 26, height: 26, borderRadius: '50%', flexShrink: 0, display: 'flex',
                alignItems: 'center', justifyContent: 'center', fontSize: 'var(--fs-body)', fontWeight: 600,
                background: active ? GOLD : done ? 'var(--ok)' : 'transparent',
                color: active || done ? 'var(--white)' : 'var(--gray)',
                border: active || done ? 'none' : `1px solid ${BORDER}`,
              }}>{done ? '✓' : n}</div>
              <span style={{ fontSize: 'var(--fs-body)', fontWeight: active ? 600 : 400, color: active ? 'var(--text-main)' : 'var(--gray)', whiteSpace: 'nowrap' }}>
                {t(`bulk_import.${key}`)}
              </span>
            </div>
            {i < STEP_KEYS.length - 1 && (
              <div style={{ flex: 1, height: 1, background: done ? 'var(--ok)' : BORDER, margin: '0 10px' }} />
            )}
          </div>
        )
      })}
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div>
      <div style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', textTransform: 'uppercase', letterSpacing: '.04em', fontFamily: MONO, marginBottom: 6 }}>{label}</div>
      {children}
    </div>
  )
}

const card = { border: `0.5px solid ${BORDER}`, borderRadius: 12, background: 'var(--white)', padding: 22 }
const errBox = { background: '#fee', border: '1px solid #fcc', borderRadius: 8, padding: '0.6rem 1rem', margin: '0 0 12px', fontSize: 'var(--fs-body)', color: '#c00', fontFamily: MONO }
const linkBtn = { background: 'none', border: 'none', padding: 0, color: 'var(--gray)', fontSize: 'var(--fs-body)', cursor: 'pointer', fontFamily: MONO }
const primaryBtn = (disabled) => ({ background: disabled ? 'var(--gray-l)' : GOLD, color: 'var(--white)', border: 'none', borderRadius: 6, padding: '8px 20px', fontSize: 'var(--fs-h3)', fontWeight: 500, cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.6 : 1, fontFamily: MONO })
const ghostBtn = (disabled) => ({ background: 'var(--white)', color: GOLD, border: `0.5px solid ${GOLD}`, borderRadius: 6, padding: '7px 14px', fontSize: 'var(--fs-body)', cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.5 : 1, fontFamily: MONO })
