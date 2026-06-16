
import { useState } from "react"

const API = import.meta.env.VITE_API_URL || ""

export function DesignFreezePanel({ model, token, onApproved }) {
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState(null)

  const isApproved = !!model?.design_freeze_at
  const approvedBy = model?.design_freeze_by_nom || model?.design_freeze_by || ''
  const approvedAt = model?.design_freeze_at
    ? new Date(model.design_freeze_at).toLocaleDateString('ca-ES', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
      })
    : null

  const handleAprovar = async () => {
    setLoading(true)
    setMsg(null)
    try {
      const r = await fetch(`${API}/api/v1/models/${model.id}/aprovar-design-freeze/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      const d = await r.json()
      if (r.ok) {
        setMsg({ type: 'ok', text: d.missatge })
        onApproved && onApproved()
      } else {
        setMsg({ type: 'error', text: d.error })
      }
    } catch (e) {
      setMsg({ type: 'error', text: String(e) })
    }
    setLoading(false)
  }

  return (
    <div style={{
      border: `1px solid ${isApproved ? '#c0dd97' : 'var(--border)'}`,
      borderRadius: 6, padding: '12px 16px', marginBottom: 20,
      background: isApproved ? 'var(--ok-bg)' : '#fdf6ee',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: isApproved ? 'var(--ok)' : 'var(--gold)', marginBottom: 2 }}>
            {isApproved ? '✓ Design Freeze aprovat' : '○ Design Freeze pendent'}
          </div>
          {isApproved ? (
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              {approvedAt} · {approvedBy}
            </div>
          ) : (
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              El tècnic revisa el disseny i confirma que és correcte per iniciar el desenvolupament tècnic.
              No calen mesures en aquest punt.
            </div>
          )}
        </div>
        {!isApproved && (
          <button
            onClick={handleAprovar}
            disabled={loading}
            style={{
              padding: '7px 16px', borderRadius: 4, fontSize: 11, cursor: 'pointer',
              background: 'var(--gold-pale)', color: 'var(--gold)', border: '1px solid var(--gold)',
            }}
          >
            {loading ? 'Aprovant...' : '✓ Aprovar Design Freeze'}
          </button>
        )}
      </div>
      {msg && (
        <div style={{
          marginTop: 8, fontSize: 11, padding: '4px 8px', borderRadius: 3,
          background: msg.type === 'ok' ? '#e8f5e8' : 'var(--err-bg)',
          color: msg.type === 'ok' ? 'var(--ok)' : 'var(--err)',
        }}>
          {msg.text}
        </div>
      )}
    </div>
  )
}
