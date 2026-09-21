import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getLead, updateLead, deleteLead, MOCK_LEADS } from '../api/leads'
import { LEAD_ESTAT_ORDRE, leadEstatConfig } from '../config/leadEstats'

const MONO = "'IBM Plex Mono', monospace"

const labelStyle = { fontSize: 10, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 4 }
const cardStyle = { background: 'var(--bg-main)', border: '1px solid var(--border)', borderRadius: 12, padding: '22px 24px' }
const ghostBtn = { display: 'inline-flex', alignItems: 'center', gap: 6, background: 'transparent', border: '1px solid var(--border)', borderRadius: 8, padding: '7px 13px', fontFamily: MONO, fontSize: 12, color: 'var(--gold)', cursor: 'pointer' }

const fmtDate = (v) => v ? new Date(v).toLocaleString('ca-ES', { dateStyle: 'medium', timeStyle: 'short' }) : '—'

function Field({ label, value }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={labelStyle}>{label}</div>
      <div style={{ fontSize: 13, color: 'var(--text-main)', wordBreak: 'break-word' }}>{value || '—'}</div>
    </div>
  )
}

function SectionTitle({ children }) {
  return (
    <div style={{ fontSize: 11, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--gold)', fontWeight: 600, margin: '4px 0 16px' }}>
      {children}
    </div>
  )
}

function Badge({ estat }) {
  const cfg = leadEstatConfig(estat)
  return <span style={{ display: 'inline-block', padding: '4px 10px', borderRadius: 6, fontSize: 11, fontWeight: 600, letterSpacing: '.04em', color: cfg.color, background: cfg.bg }}>{cfg.label}</span>
}

export default function LeadDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()

  const [lead, setLead] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [mock, setMock] = useState(false)

  const [estatSaving, setEstatSaving] = useState(false)
  const [notes, setNotes] = useState('')
  const [notesSaving, setNotesSaving] = useState(false)
  const [notesSaved, setNotesSaved] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const l = await getLead(id)
      setLead(l)
      setNotes(l.notes || '')
      setMock(false)
    } catch {
      if (import.meta.env.DEV) {
        const m = MOCK_LEADS.find((x) => String(x.id) === String(id)) || MOCK_LEADS[0]
        setLead(m)
        setNotes(m.notes || '')
        setMock(true)
      } else {
        setLead(null)
        setError(`No s’ha pogut carregar el lead #${id}. Potser no existeix o l’API no respon.`)
      }
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { load() }, [load])

  const handleEstatChange = async (e) => {
    const nouEstat = e.target.value
    setEstatSaving(true)
    try {
      const actualitzat = await updateLead(id, { estat: nouEstat })
      setLead(actualitzat)
    } catch {
      setError('No s’ha pogut canviar l’estat.')
    } finally {
      setEstatSaving(false)
    }
  }

  const handleNotesSave = async () => {
    setNotesSaving(true)
    setNotesSaved(false)
    try {
      const actualitzat = await updateLead(id, { notes })
      setLead(actualitzat)
      setNotesSaved(true)
    } catch {
      setError('No s’ha pogut desar la nota.')
    } finally {
      setNotesSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm(`Esborrar el lead de ${lead.nom}? Aquesta acció no es pot desfer.`)) return
    setDeleting(true)
    try {
      await deleteLead(id)
      navigate('/leads')
    } catch {
      setError('No s’ha pogut esborrar el lead.')
      setDeleting(false)
    }
  }

  if (loading) {
    return <div style={{ padding: '28px 32px', fontFamily: MONO, color: 'var(--text-muted)', fontSize: 13 }}>Carregant…</div>
  }

  if (error && !lead) {
    return (
      <div style={{ padding: '28px 32px', fontFamily: MONO }}>
        <button type="button" onClick={() => navigate('/leads')} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontFamily: MONO, fontSize: 12, cursor: 'pointer', padding: 0, marginBottom: 16 }}>
          ← Leads
        </button>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'var(--warn-bg)', color: 'var(--warn)', border: '1px solid var(--warn)', borderRadius: 8, padding: '12px 15px', fontSize: 13 }}>
          <i className="ti ti-alert-triangle" style={{ fontSize: 16 }} /> {error}
        </div>
      </div>
    )
  }

  if (!lead) return null

  const mailtoHref = `mailto:${lead.email}?subject=${encodeURIComponent(`RE: ${lead.nom} — Fhort Textile Tech`)}`

  return (
    <div style={{ padding: '28px 32px', maxWidth: 900, fontFamily: MONO }}>
      <button type="button" onClick={() => navigate('/leads')} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontFamily: MONO, fontSize: 12, cursor: 'pointer', padding: 0, marginBottom: 16 }}>
        ← Leads
      </button>

      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, marginBottom: 18 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600, color: 'var(--text-main)', margin: '0 0 8px' }}>{lead.nom}</h1>
          <Badge estat={lead.estat} />
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <a href={mailtoHref} style={{ ...ghostBtn, textDecoration: 'none' }}>
            <i className="ti ti-mail" style={{ fontSize: 15 }} /> Respon per correu
          </a>
          <button type="button" onClick={handleDelete} disabled={deleting}
            style={{ ...ghostBtn, color: 'var(--err)', cursor: deleting ? 'not-allowed' : 'pointer', opacity: deleting ? 0.6 : 1 }}>
            <i className="ti ti-trash" style={{ fontSize: 15 }} /> {deleting ? 'Esborrant…' : 'Esborrar'}
          </button>
        </div>
      </div>

      {mock && (
        <div style={{ marginBottom: 16, background: 'var(--warn-bg)', color: 'var(--warn)', border: '1px solid var(--warn)', borderRadius: 8, padding: '9px 13px', fontSize: 12 }}>
          Dades de mostra — l'API de leads encara no respon.
        </div>
      )}
      {error && lead && (
        <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8, color: 'var(--err)', fontSize: 12 }}>
          <i className="ti ti-alert-triangle" style={{ fontSize: 15 }} /> {error}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16, marginBottom: 16 }}>
        <div style={cardStyle}>
          <SectionTitle>Dades de contacte</SectionTitle>
          <Field label="Nom" value={lead.nom} />
          <Field label="Empresa" value={lead.empresa} />
          <Field label="Email" value={lead.email} />
          <Field label="Idioma" value={(lead.idioma || '').toUpperCase()} />
        </div>

        <div style={cardStyle}>
          <SectionTitle>Origen i consentiment</SectionTitle>
          <Field label="Pàgina d'origen" value={lead.pagina_origen} />
          <Field label="Data" value={fmtDate(lead.created_at)} />
          <Field label="IP" value={lead.ip} />
          <Field label="Versió de privacitat acceptada" value={lead.privacy_version} />
          <Field label="Avís enviat" value={
            <span style={{ color: lead.notificat ? 'var(--ok)' : 'var(--text-muted)', fontWeight: 600 }}>
              {lead.notificat ? 'Sí' : 'No'}
            </span>
          } />
        </div>
      </div>

      <div style={{ ...cardStyle, marginBottom: 16 }}>
        <SectionTitle>Missatge</SectionTitle>
        <div style={{ fontSize: 13, color: 'var(--text-main)', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
          {lead.missatge}
        </div>
      </div>

      <div style={{ ...cardStyle, marginBottom: 16 }}>
        <SectionTitle>Estat</SectionTitle>
        <select
          value={lead.estat}
          onChange={handleEstatChange}
          disabled={estatSaving}
          style={{
            fontFamily: MONO, fontSize: 13, color: 'var(--text-main)', background: 'var(--bg-card)',
            border: '1px solid var(--border)', borderRadius: 8, padding: '9px 12px',
            cursor: estatSaving ? 'not-allowed' : 'pointer', opacity: estatSaving ? 0.6 : 1,
          }}
        >
          {LEAD_ESTAT_ORDRE.map((k) => (
            <option key={k} value={k}>{leadEstatConfig(k).label}</option>
          ))}
        </select>
        {estatSaving && <span style={{ marginLeft: 10, fontSize: 12, color: 'var(--text-muted)' }}>Desant…</span>}
      </div>

      <div style={cardStyle}>
        <SectionTitle>Notes internes</SectionTitle>
        <textarea
          value={notes}
          onChange={(e) => { setNotes(e.target.value); setNotesSaved(false) }}
          rows={4}
          style={{
            width: '100%', fontFamily: MONO, fontSize: 13, color: 'var(--text-main)',
            background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8,
            padding: '10px 12px', resize: 'vertical', outline: 'none',
          }}
        />
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 10 }}>
          <button type="button" onClick={handleNotesSave} disabled={notesSaving}
            style={{ background: 'var(--accio)', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 18px', fontFamily: MONO, fontSize: 12, fontWeight: 600, cursor: notesSaving ? 'not-allowed' : 'pointer', opacity: notesSaving ? 0.6 : 1 }}>
            {notesSaving ? 'Desant…' : 'Desar notes'}
          </button>
          {notesSaved && <span style={{ fontSize: 12, color: 'var(--ok)' }}>✓ Desat</span>}
        </div>
      </div>
    </div>
  )
}
