import { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'

export default function MeasurementsChat({ modelId, onMesuresUpdated }) {
  const { t } = useTranslation()
  const API = import.meta.env.VITE_API_URL || ''
  const token = localStorage.getItem('access_token')

  const [historial, setHistorial] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [historial])

  const handleSend = async () => {
    if (!input.trim() || loading) return
    const message = input.trim()
    setInput('')

    const newHistory = [...historial, { role: 'user', content: message }]
    setHistorial(newHistory)
    setLoading(true)

    try {
      const r = await fetch(`${API}/api/v1/models/${modelId}/xat-mesures/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          missatge: message,
          historial: historial,
        }),
      })
      const d = await r.json()

      if (r.ok) {
        setHistorial(d.historial_nou || [
          ...newHistory,
          { role: 'assistant', content: d.resposta }
        ])
        if (d.accions_executades?.length > 0 && onMesuresUpdated) {
          onMesuresUpdated(d.mesures_actualitzades)
        }
      } else {
        setHistorial(prev => [
          ...prev,
          { role: 'assistant', content: `${t('common.error')}: ${d.error || t('model_sheet.err_unknown')}` }
        ])
      }
    } catch {
      setHistorial(prev => [
        ...prev,
        { role: 'assistant', content: t('model_sheet.err_connection') }
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', minHeight: 400,
      border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
      borderRadius: 8, overflow: 'hidden',
    }}>
      <div style={{
        padding: '10px 14px',
        borderBottom: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
        background: 'var(--color-background-secondary, #f5f0ea)',
        fontSize: 13, fontWeight: 500,
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <i className="ti ti-message-circle" aria-hidden="true" style={{ color: 'var(--gold)' }} />
        {t('measurements_chat.title')}
        <span style={{ fontSize: 11, color: 'var(--color-text-secondary, #868685)', fontWeight: 400 }}>
          · {t('measurements_chat.autosave_note')}
        </span>
      </div>

      <div style={{
        flex: 1, overflowY: 'auto', padding: '12px 14px',
        display: 'flex', flexDirection: 'column', gap: 10,
      }}>
        {historial.length === 0 && (
          <div style={{ fontSize: 12, color: 'var(--color-text-secondary, #868685)',
                        fontStyle: 'italic', textAlign: 'center', marginTop: 20 }}>
            {t('measurements_chat.empty_hint')}
            <br />{t('measurements_chat.examples')}
          </div>
        )}
        {historial.map((msg, i) => (
          <div key={i} style={{
            display: 'flex',
            justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
          }}>
            <div style={{
              maxWidth: '80%', padding: '8px 12px', borderRadius: 8, fontSize: 13,
              background: msg.role === 'user'
                ? 'var(--gold)' : 'var(--color-background-secondary, #f5f0ea)',
              color: msg.role === 'user' ? 'var(--white)' : 'var(--color-text-primary, #1d1d1b)',
              border: msg.role === 'assistant'
                ? '0.5px solid var(--color-border-tertiary, #e0d5c5)' : 'none',
              whiteSpace: 'pre-wrap',
            }}>
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <div style={{
              padding: '8px 14px', borderRadius: 8, fontSize: 13,
              background: 'var(--color-background-secondary, #f5f0ea)',
              border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
              color: 'var(--color-text-secondary, #868685)',
            }}>
              <span style={{ }}>···</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div style={{
        padding: '10px 12px',
        borderTop: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
        display: 'flex', gap: 8,
      }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
          placeholder={t('measurements_chat.input_placeholder')}
          disabled={loading}
          style={{
            flex: 1, padding: '7px 10px', fontSize: 13,
            border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
            borderRadius: 6, background: 'var(--color-background-primary, #fff)',
          }}
        />
        <button type="button" onClick={handleSend} disabled={loading || !input.trim()}
          style={{
            padding: '7px 14px', background: loading ? '#ccc' : 'var(--gold)',
            color: 'var(--white)', border: 'none', borderRadius: 6,
            fontSize: 13, cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
          }}>
          <i className="ti ti-send" aria-hidden="true" />
        </button>
      </div>
    </div>
  )
}
