
import { useState } from "react"
import { useTranslation } from "react-i18next"
import useAuthStore from "../store/auth"

const API = import.meta.env.VITE_API_URL || ""

export function ExportButton({ url, filename, label, type = "csv" }) {
  const { t } = useTranslation()
  const token = useAuthStore(s => s.token) || localStorage.getItem('access_token')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleExport = async () => {
    setLoading(true)
    setError(null)
    try {
      const r = await fetch(`${API}${url}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (!r.ok) {
        const d = await r.json()
        throw new Error(d.error || `HTTP ${r.status}`)
      }
      const blob = await r.blob()
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(link.href)
    } catch (e) {
      setError(e.message)
      setTimeout(() => setError(null), 4000)
    }
    setLoading(false)
  }

  const icon = type === 'pdf' ? '📄' : '📊'
  const ext = type === 'pdf' ? 'PDF' : 'CSV'

  return (
    <div style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'flex-end' }}>
      <button
        onClick={handleExport}
        disabled={loading}
        style={{
          padding: '5px 12px', borderRadius: 4, fontSize: 11,
          background: 'var(--white)', color: 'var(--text-muted)',
          border: '1px solid var(--border)',
          cursor: loading ? 'not-allowed' : 'pointer',
          display: 'flex', alignItems: 'center', gap: 5,
        }}
      >
        <span>{loading ? '...' : icon}</span>
        <span>{loading ? t('export_button.generating') : `${label || t('export_button.export')} ${ext}`}</span>
      </button>
      {error && (
        <div style={{ fontSize: 10, color: '#a32d2d', marginTop: 3 }}>{error}</div>
      )}
    </div>
  )
}

// Pre-configured specific exporters
export function ExportGradingCSV({ ruleSetId }) {
  return (
    <ExportButton
      url={`/api/v1/grading-rule-sets/${ruleSetId}/export/csv/`}
      filename={`grading_${ruleSetId}.csv`}
      label="Grading"
      type="csv"
    />
  )
}

export function ExportSizeSetCSV({ profileId }) {
  return (
    <ExportButton
      url={`/api/v1/sizing-profiles/${profileId}/export/csv/`}
      filename={`sizeset_${profileId}.csv`}
      label="Size Set"
      type="csv"
    />
  )
}

export function ExportFittingCSV({ fittingId }) {
  return (
    <ExportButton
      url={`/api/v1/fittings/${fittingId}/export/csv/`}
      filename={`fitting_${fittingId}.csv`}
      label="Fitting"
      type="csv"
    />
  )
}

export function ExportModelPDF({ modelId, nomModel }) {
  const { t } = useTranslation()
  return (
    <ExportButton
      url={`/api/v1/models/${modelId}/export/pdf/`}
      filename={`spec_${nomModel || modelId}.pdf`}
      label={t('model_sheet.tab_tech_sheet')}
      type="pdf"
    />
  )
}
