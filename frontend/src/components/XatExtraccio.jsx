
import { useState, useEffect, useRef } from "react"
import useAuthStore from "../store/auth"

const API = import.meta.env.VITE_API_URL || ""

export function XatExtraccio({ extraccio, fileBase64, fileType, onUpdate, onClose }) {
  const token = useAuthStore(s => s.token) || localStorage.getItem('access_token')
  const [historial, setHistorial] = useState([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [iniciant, setIniciant] = useState(true)
  const messagesEndRef = useRef(null)

  // Start the chat automatically
  useEffect(() => {
    const iniciar = async () => {
      setIniciant(true)
      try {
        const r = await fetch(`${API}/api/v1/models/iniciar-chat-extraccio/`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({ extraccio }),
        })
        const d = await r.json()
        if (r.ok) {
          setHistorial(d.historial || [{ role: 'assistant', content: d.resposta }])
        } else {
          setHistorial([{ role: 'assistant', content: `Error iniciant el xat: ${d.error}` }])
        }
      } catch (e) {
        setHistorial([{ role: 'assistant', content: `Error de connexió: ${e.message}` }])
      }
      setIniciant(false)
    }
    iniciar()
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [historial, loading])

  const send = async () => {
    const msg = input.trim()
    if (!msg || loading) return
    setInput("")
    setLoading(true)

    // Add the user's message immediately
    const newHistory = [...historial, { role: 'user', content: msg }]
    setHistorial(newHistory)

    try {
      // Include the file only in the first real message
      const isFirstReal = historial.filter(h => h.role === 'user').length === 0

      const body = {
        missatge: msg,
        historial: historial,
        extraccio,
        ...(isFirstReal && fileBase64 ? { file_base64: fileBase64, file_type: fileType } : {}),
      }

      const r = await fetch(`${API}/api/v1/models/chat-extraccio/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const d = await r.json()

      if (r.ok) {
        setHistorial(d.historial || [...newHistory, { role: 'assistant', content: d.resposta }])
        // Aplicar updates si n'hi ha
        if (d.updates && Object.keys(d.updates).length > 0) {
          onUpdate && onUpdate(d.updates)
        }
      } else {
        setHistorial([...newHistory, { role: 'assistant', content: `Error: ${d.error}` }])
      }
    } catch (e) {
      setHistorial([...newHistory, { role: 'assistant', content: `Error de connexió: ${e.message}` }])
    }
    setLoading(false)
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  // Mostrar missatges visibles (excloure els de sistema)
  const missatgesVisibles = historial.filter(h =>
    h.role === 'assistant' ||
    (h.role === 'user' && !h.content?.includes('Acabo d\'analitzar el document'))
  )

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      fontFamily: 'IBM Plex Mono, monospace',
    }}>
      {/* Header */}
      <div style={{
        padding: '10px 14px', borderBottom: '1px solid #e0d5c5',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        background: '#fdf9f5',
      }}>
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#c27a2a' }}>
            ⚡ Assistent tècnic IA
          </div>
          <div style={{ fontSize: 10, color: '#868685' }}>
            Pregunta o confirma les dades del document
          </div>
        </div>
        {onClose && (
          <button onClick={onClose} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: '#868685', fontSize: 18, lineHeight: 1,
          }}>×</button>
        )}
      </div>

      {/* Missatges */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {iniciant ? (
          <div style={{ color: '#868685', fontSize: 11, textAlign: 'center', padding: '20px 0' }}>
            Analitzant el document...
          </div>
        ) : (
          missatgesVisibles.map((msg, i) => (
            <div key={i} style={{
              display: 'flex',
              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
            }}>
              <div style={{
                maxWidth: '85%',
                padding: '8px 12px',
                borderRadius: msg.role === 'user' ? '12px 12px 4px 12px' : '12px 12px 12px 4px',
                background: msg.role === 'user' ? '#f5e6d0' : '#fff',
                border: `1px solid ${msg.role === 'user' ? '#e0c8a0' : '#e0d5c5'}`,
                fontSize: 12,
                color: '#1d1d1b',
                lineHeight: 1.5,
                whiteSpace: 'pre-wrap',
              }}>
                {msg.content}
              </div>
            </div>
          ))
        )}
        {loading && (
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <div style={{
              padding: '8px 14px', borderRadius: '12px 12px 12px 4px',
              background: '#fff', border: '1px solid #e0d5c5',
              fontSize: 12, color: '#868685',
            }}>
              Escrivint...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div style={{
        padding: '10px 14px', borderTop: '1px solid #e0d5c5',
        display: 'flex', gap: 8, background: '#fff',
      }}>
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Escriu aquí... (Enter per enviar)"
          rows={2}
          disabled={loading || iniciant}
          style={{
            flex: 1, padding: '6px 10px',
            border: '1px solid #e0d5c5', borderRadius: 6,
            fontSize: 12, fontFamily: 'IBM Plex Mono, monospace',
            resize: 'none', color: '#1d1d1b', background: '#fff',
          }}
        />
        <button
          onClick={send}
          disabled={!input.trim() || loading || iniciant}
          style={{
            padding: '6px 14px', borderRadius: 6,
            background: input.trim() ? '#f5e6d0' : '#f5f0e8',
            color: input.trim() ? '#c27a2a' : '#c8b89a',
            border: '1px solid #e0c8a0',
            fontSize: 12, cursor: input.trim() ? 'pointer' : 'not-allowed',
            fontFamily: 'IBM Plex Mono, monospace', alignSelf: 'flex-end',
          }}
        >
          ↑
        </button>
      </div>
    </div>
  )
}
