import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { fittingSessions, pieceFittings, pieceFittingLines } from '../api/endpoints'
import Card from '../components/ui/Card'
import Badge from '../components/ui/Badge'

// DEUTE (tolerància): el grid serializer NO exposa tolerància per línia, així que
// fem servir el fallback 0.6 (= default de POMMaster al backend, visualment correcte
// en el cas habitual). Quan es resolgui al backend, el serializer haurà d'exposar la
// tolerància per línia escollint entre tolerancia_critica/tolerancia_secundaria segons
// el flag `is_key` que la línia JA porta — llavors aquí substituir TOL_FALLBACK.
const TOL_FALLBACK = 0.6

const estatVariant = { Oberta: 'warn', Tancada: 'ok', Anullada: 'gray' }
const gateVariant  = { OK: 'ok', NO_OK: 'err', EXCEPCIO: 'warn', Pendent: 'gray' }

const COL_POM_W = 78
const COL_NOM_W = 150

function toleranceClass(real, teoric) {
  if (real === '' || real == null) return null
  const r = Number(real)
  if (Number.isNaN(r) || teoric == null) return null
  return Math.abs(r - Number(teoric)) > TOL_FALLBACK ? 'out' : 'in'
}

function realColors(real, teoric) {
  const c = toleranceClass(real, teoric)
  if (c === 'out') return { bg: 'var(--err-bg)', fg: 'var(--err)', br: 'var(--err)' }
  if (c === 'in')  return { bg: 'var(--ok-bg)',  fg: 'var(--ok)',  br: 'var(--ok)' }
  return { bg: 'var(--white)', fg: 'var(--text-main)', br: 'var(--border)' }
}

// Ordre de talles segons el size run del model: split per '·' (U+00B7) + trim.
// Mai alfabètic. Talles presents a les línies que no surtin al run s'afegeixen al final.
function orderedSizes(sizeRun, present) {
  const run = (sizeRun || '').split('·').map(s => s.trim()).filter(Boolean)
  const ordered = run.filter(s => present.has(s))
  const extras = [...present].filter(s => !run.includes(s))
  return [...ordered, ...extras]
}

// Debounce genèric d'autosave (800ms). Cada instància té el seu propi timer.
function useDebouncedSave(persist) {
  const [state, setState] = useState('idle') // idle | saving | saved | error
  const timerRef = useRef(null)
  const savedRef = useRef(null)
  useEffect(() => () => { clearTimeout(timerRef.current); clearTimeout(savedRef.current) }, [])
  const schedule = useCallback((value) => {
    setState('saving')
    clearTimeout(timerRef.current)
    clearTimeout(savedRef.current)
    timerRef.current = setTimeout(() => {
      persist(value)
        .then(() => { setState('saved'); savedRef.current = setTimeout(() => setState('idle'), 2000) })
        .catch(() => setState('error')) // NO toquem el valor local: es preserva
    }, 800)
  }, [persist])
  return [state, schedule]
}

// Autosave d'una cel·la de línia (valor_real / nota). Debounce PER (line.id, field).
function useCellAutosave(lineId, field, isNumber) {
  const persist = useCallback((raw) => {
    const value = isNumber ? (raw === '' ? null : Number(raw)) : raw
    return pieceFittingLines.update(lineId, { [field]: value })
  }, [lineId, field, isNumber])
  return useDebouncedSave(persist)
}

// Autosave d'un camp de context de la sessió (model_persona / lloc...). PATCH sessió.
function useSessionField(sessionId, field) {
  const persist = useCallback((raw) => fittingSessions.update(sessionId, { [field]: raw }), [sessionId, field])
  return useDebouncedSave(persist)
}

function SaveStatus({ state, inline }) {
  const { t } = useTranslation()
  if (state === 'idle') return null
  const map = {
    saving: { txt: t('fitting.grid.saving'), color: 'var(--text-muted)' },
    saved:  { txt: t('fitting.grid.saved'),  color: 'var(--ok)' },
    error:  { txt: t('fitting.grid.save_error'), color: 'var(--err)' },
  }
  const s = map[state]
  return (
    <span style={{ fontSize: 9, color: s.color, display: inline ? 'inline-block' : 'block', marginLeft: inline ? 6 : 0, marginTop: inline ? 0 : 1 }}>
      {s.txt}
    </span>
  )
}

// Valor teòric (read-only, atenuat) + popover d'evolució en hover. Reutilitzat d'A2.
function TheoreticalValue({ line }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const evo = line.evolucio || []
  return (
    <span
      style={{ position: 'relative', fontSize: 11, color: 'var(--text-muted)', fontVariantNumeric: 'tabular-nums', cursor: evo.length ? 'help' : 'default' }}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      {line.valor_teoric ?? t('fitting.grid.no_value')}
      {evo.length > 0 && <i className="ti ti-history" style={{ fontSize: 10, marginLeft: 3, color: 'var(--gold)' }} />}
      {open && evo.length > 0 && (
        <div style={{
          position: 'absolute', zIndex: 30, top: '100%', left: 0, marginTop: 4,
          background: 'var(--white)', border: '0.5px solid var(--border)', borderRadius: 8,
          padding: '6px 8px', boxShadow: '0 4px 16px rgba(0,0,0,0.08)',
          whiteSpace: 'nowrap', textAlign: 'left',
        }}>
          <div style={{ fontSize: 9, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 4 }}>
            {t('fitting.grid.evolution')}
          </div>
          {evo.map(e => (
            <div key={e.version_number} style={{ fontSize: 11, color: e.is_active ? 'var(--text-main)' : 'var(--text-muted)', fontWeight: e.is_active ? 500 : 300 }}>
              v{e.version_number} · {e.data ? e.data.slice(0, 10) : '—'} · {e.valor_cm}{e.aprovada ? ' ✓' : ''}
            </div>
          ))}
        </div>
      )}
    </span>
  )
}

const cellTd = (base) => ({
  padding: '5px 8px', borderBottom: '0.5px solid var(--border)', verticalAlign: 'middle',
  textAlign: 'right',
  background: base ? 'var(--gold-pale)' : undefined,
  borderLeft: base ? '1px solid var(--base-hairline)' : undefined,
})

function TheoreticalCell({ line, base }) {
  return <td style={cellTd(base)}>{line ? <TheoreticalValue line={line} /> : <span style={{ color: 'var(--text-muted)' }}>—</span>}</td>
}

// Cel·la real editable + nota (icona + popover). base = columna de talla base.
function RealCell({ line, base, value, note, onValue, onNote }) {
  const { t } = useTranslation()
  const [realState, saveReal] = useCellAutosave(line?.id, 'valor_real', true)
  const [notaState, saveNota] = useCellAutosave(line?.id, 'nota', false)
  const [noteOpen, setNoteOpen] = useState(false)

  if (!line) return <td style={cellTd(base)} />

  const c = realColors(value, line.valor_teoric)
  const hasNote = (note ?? '').trim() !== ''

  return (
    <td style={{ ...cellTd(base), borderLeft: undefined, position: 'relative' }}>
      <div style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
        <input
          type="number" step="0.1" value={value}
          onChange={e => { onValue(line.id, e.target.value); saveReal(e.target.value) }}
          style={{
            width: 58, padding: '3px 6px', fontSize: 12, fontVariantNumeric: 'tabular-nums',
            textAlign: 'right', border: `1px solid ${c.br}`, borderRadius: 6,
            background: c.bg, color: c.fg, boxSizing: 'border-box',
          }}
        />
        <button
          type="button" onClick={() => setNoteOpen(o => !o)} title={t('fitting.grid.note')}
          style={{
            background: 'none', border: 'none', cursor: 'pointer', padding: 2, lineHeight: 1,
            color: hasNote ? 'var(--gold)' : 'var(--text-muted)',
          }}
        >
          <i className={`ti ${hasNote ? 'ti-message-2-filled' : 'ti-message-2'}`} style={{ fontSize: 13 }} />
        </button>
      </div>
      <SaveStatus state={realState} />
      {noteOpen && (
        <div style={{
          position: 'absolute', zIndex: 25, top: '100%', right: 4, marginTop: 4,
          background: 'var(--white)', border: '0.5px solid var(--border)', borderRadius: 8,
          padding: 8, boxShadow: '0 4px 16px rgba(0,0,0,0.08)', width: 200, textAlign: 'left',
        }}>
          <div style={{ fontSize: 9, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 4 }}>
            {t('fitting.grid.note')}
          </div>
          <textarea
            value={note} autoFocus
            onChange={e => { onNote(line.id, e.target.value); saveNota(e.target.value) }}
            style={{
              width: '100%', minHeight: 56, resize: 'vertical', padding: '4px 6px', fontSize: 11,
              border: '0.5px solid var(--border)', borderRadius: 6, boxSizing: 'border-box', color: 'var(--text-main)',
            }}
          />
          <SaveStatus state={notaState} />
        </div>
      )}
    </td>
  )
}

function DeltaCell({ baseLine, baseReal }) {
  const { t } = useTranslation()
  if (!baseLine || baseReal === '' || baseReal == null) {
    return <td style={{ ...cellTd(false), color: 'var(--text-muted)', fontVariantNumeric: 'tabular-nums' }}>{t('fitting.grid.no_value')}</td>
  }
  const d = Number(baseReal) - Number(baseLine.valor_teoric)
  const cls = Math.abs(d) > TOL_FALLBACK ? 'out' : 'in'
  const color = d === 0 ? 'var(--text-muted)' : cls === 'out' ? 'var(--err)' : 'var(--ok)'
  const txt = `${d > 0 ? '+' : ''}${d.toFixed(1)}`
  return <td style={{ ...cellTd(false), color, fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}>{txt}</td>
}

function EditableContextField({ sessionId, field, label, value }) {
  const [v, setV] = useState(value ?? '')
  const [state, schedule] = useSessionField(sessionId, field)
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', fontSize: 11, color: 'var(--text-muted)' }}>
      {label}:&nbsp;
      <input
        value={v} onChange={e => { setV(e.target.value); schedule(e.target.value) }}
        placeholder="—"
        style={{
          width: 120, padding: '2px 6px', fontSize: 11, color: 'var(--text-main)',
          border: '0.5px solid var(--border)', borderRadius: 6, background: 'var(--white)', boxSizing: 'border-box',
        }}
      />
      <SaveStatus state={state} inline />
    </span>
  )
}

function GateBar({ piece, onGate, onClose }) {
  const { t } = useTranslation()
  const [resultat, setResultat] = useState(piece.gate && piece.gate !== 'Pendent' ? piece.gate : '')
  const [motiu, setMotiu] = useState(piece.gate_motiu || '')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [closing, setClosing] = useState(false)

  const needsReason = resultat === 'NO_OK' || resultat === 'EXCEPCIO'

  const apply = (value) => {
    setResultat(value)
    setError('')
    const reason = (value === 'NO_OK' || value === 'EXCEPCIO') ? motiu : ''
    if ((value === 'NO_OK' || value === 'EXCEPCIO') && !reason.trim()) return
    submit(value, reason)
  }
  const submit = (value, reason) => {
    setBusy(true)
    onGate(value, reason).catch(() => setError(t('fitting.gate.save_error'))).finally(() => setBusy(false))
  }
  const confirmReason = () => {
    if (!motiu.trim()) { setError(t('fitting.gate.reason_required')); return }
    submit(resultat, motiu)
  }
  const closePiece = () => {
    setClosing(true); setError('')
    onClose().catch(() => setError(t('fitting.piece.close_error'))).finally(() => setClosing(false))
  }

  const btn = (value, label) => {
    const active = resultat === value
    const v = gateVariant[value]
    return (
      <button key={value} type="button" disabled={busy} onClick={() => apply(value)} style={{
        background: active ? `var(--${v}-bg)` : 'var(--white)',
        color: active ? `var(--${v})` : 'var(--text-muted)',
        border: `1px solid ${active ? `var(--${v})` : 'var(--border)'}`,
        borderRadius: 8, padding: '6px 14px', fontSize: 12,
        cursor: busy ? 'default' : 'pointer',
      }}>{label}</button>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginRight: 4 }}>{t('fitting.gate.title')}:</span>
        {btn('OK', t('fitting.gate.ok'))}
        {btn('NO_OK', t('fitting.gate.no_ok'))}
        {btn('EXCEPCIO', t('fitting.gate.exception'))}
        {piece.gate && piece.gate !== 'Pendent' && (
          <Badge variant={gateVariant[piece.gate] || 'gray'} style={{ marginLeft: 4 }}>{piece.gate}</Badge>
        )}
        <button type="button" disabled={closing} onClick={closePiece} style={{
          marginLeft: 'auto', background: 'var(--white)', color: 'var(--text-muted)',
          border: '0.5px solid var(--border)', borderRadius: 8, padding: '6px 14px',
          fontSize: 12, cursor: closing ? 'default' : 'pointer',
        }}>{closing ? t('fitting.piece.closing') : t('fitting.piece.close')}</button>
      </div>
      {needsReason && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <input
            type="text" value={motiu} placeholder={t('fitting.gate.reason')}
            onChange={e => setMotiu(e.target.value)}
            style={{ flex: 1, maxWidth: 360, padding: '6px 10px', fontSize: 12, border: '0.5px solid var(--border)', borderRadius: 8 }}
          />
          <button type="button" disabled={busy} onClick={confirmReason} style={{
            background: 'var(--gold)', color: 'var(--white)', border: 'none',
            borderRadius: 8, padding: '6px 14px', fontSize: 12, cursor: 'pointer',
          }}>{t('app.confirm')}</button>
        </div>
      )}
      {error && <div style={{ fontSize: 12, color: 'var(--err)' }}>{error}</div>}
    </div>
  )
}

export default function FittingDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activePieceId, setActivePieceId] = useState(null)
  const [grid, setGrid] = useState(null)
  const [gridLoading, setGridLoading] = useState(false)
  const [creatingPiece, setCreatingPiece] = useState(false)
  // Valors editables lligats al parent → Δ reactiu i remuntatge net per peça.
  const [reals, setReals] = useState({})
  const [notes, setNotes] = useState({})

  const loadSession = useCallback((selectFirst = false) => {
    return fittingSessions.get(id).then(res => {
      setSession(res.data)
      const pieces = res.data.piece_fittings || []
      if (selectFirst && pieces.length) setActivePieceId(pieces[0].id)
      return res.data
    })
  }, [id])

  useEffect(() => {
    setLoading(true)
    loadSession(true).finally(() => setLoading(false))
  }, [loadSession])

  useEffect(() => {
    if (!activePieceId) { setGrid(null); return }
    setGridLoading(true)
    pieceFittings.get(activePieceId)
      .then(res => {
        setGrid(res.data)
        const r = {}, n = {}
        for (const l of res.data.lines || []) { r[l.id] = l.valor_real ?? ''; n[l.id] = l.nota ?? '' }
        setReals(r); setNotes(n)
      })
      .finally(() => setGridLoading(false))
  }, [activePieceId])

  const createPiece = () => {
    if (!session?.model) return
    setCreatingPiece(true)
    fittingSessions.createPiece(session.id, session.model)
      .then(res => loadSession().then(() => setActivePieceId(res.data.id)))
      .finally(() => setCreatingPiece(false))
  }

  const handleGate = (resultat, motiu) => {
    return pieceFittings.setGate(activePieceId, resultat, motiu).then(res => {
      const { gate, gate_motiu, gate_at } = res.data
      setGrid(g => g ? { ...g, gate, gate_motiu, gate_at } : g)
      setSession(s => s ? {
        ...s,
        piece_fittings: (s.piece_fittings || []).map(p => p.id === activePieceId ? { ...p, gate, gate_motiu } : p),
      } : s)
    })
  }

  const handleClose = () => pieceFittings.close(activePieceId).then(() => loadSession())

  if (loading) {
    return <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>{t('app.loading')}</div>
  }
  if (!session) return null

  const pieces = session.piece_fittings || []
  const activePiece = pieces.find(p => p.id === activePieceId)
  const lines = grid?.lines || []
  const model = grid?.model || {}
  const baseLabel = model.base_size_label

  // Identificació (codi/nom): del grid si hi ha peça; si no, de la primera peça.
  const idCodi = model.codi || pieces[0]?.model_codi || null
  const idNom = model.nom || pieces[0]?.model_nom || null
  const collection = session.model_temporada ? `${session.model_temporada}${session.model_any ? ` ${session.model_any}` : ''}` : null
  const clientRef = session.model_codi_client || null

  // Matriu: files = POM, columnes ordenades = talles del size run.
  const present = new Set(lines.map(l => l.size_label))
  const sizeLabels = orderedSizes(model.size_run_model, present)
  const pomMap = new Map()
  for (const l of lines) {
    if (!pomMap.has(l.pom_id)) pomMap.set(l.pom_id, { pom_id: l.pom_id, codi: l.codi, nom: l.nom, is_key: l.is_key, cells: {} })
    pomMap.get(l.pom_id).cells[l.size_label] = l
  }
  const pomRows = [...pomMap.values()]

  const onValue = (lineId, v) => setReals(r => ({ ...r, [lineId]: v }))
  const onNote = (lineId, v) => setNotes(n => ({ ...n, [lineId]: v }))

  const stickyHd = (left, w) => ({
    ...thStyle, position: 'sticky', left, zIndex: 3, minWidth: w, width: w,
    background: 'var(--bg-muted)', textAlign: 'left',
  })
  const stickyTd = (left, w, bg) => ({
    position: 'sticky', left, zIndex: 1, minWidth: w, width: w, background: bg,
    padding: '5px 10px', borderBottom: '0.5px solid var(--border)', verticalAlign: 'middle', whiteSpace: 'nowrap',
  })

  return (
    <div>
      {/* Capçalera d'identificació rica (sticky a dalt) — B0.3 */}
      <div style={{ position: 'sticky', top: 0, zIndex: 10, background: 'var(--bg-main)', paddingBottom: 8, marginBottom: '1rem', borderBottom: '0.5px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
          <button onClick={() => navigate('/fittings')} style={{
            background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 12, padding: 0, marginRight: 12,
          }}>← {t('app.back')}</button>
          <Badge variant="gate" style={{ marginRight: 6 }}>{session.fase_display || session.fase}</Badge>
          <Badge variant={estatVariant[session.estat] || 'gray'}>{session.estat_display || session.estat}</Badge>
        </div>
        {/* Línia 1 — identitat */}
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.9rem', flexWrap: 'wrap', marginBottom: 6 }}>
          {idCodi && <Badge variant="gold" style={{ fontSize: 12 }}>{idCodi}</Badge>}
          {idNom && <span style={{ fontSize: 15, fontWeight: 500, color: 'var(--text-main)' }}>{idNom}</span>}
          {collection && <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{t('fitting.id.collection')}: {collection}</span>}
          {clientRef && <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{t('fitting.id.client_ref')}: {clientRef}</span>}
        </div>
        {/* Línia 2 — context de sessió (persona/lloc editables inline; responsable read-only) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.9rem', flexWrap: 'wrap' }}>
          <EditableContextField sessionId={session.id} field="model_persona" label={t('fitting.id.persona')} value={session.model_persona} />
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{t('fitting.id.responsible')}: {session.responsable_nom || '—'}</span>
          <EditableContextField sessionId={session.id} field="lloc" label={t('fitting.id.location')} value={session.lloc} />
          {/* STUB B1/B2: el cablejat dels pop-ups (info fitxers / fotos / observacions) és als DOCs B1 i B2 */}
          <span style={{ marginLeft: 'auto', display: 'inline-flex', gap: 6 }}>
            {[['ti-info-circle', t('fitting.id.info')], ['ti-photo', t('fitting.id.photos')], ['ti-note', t('fitting.id.observations')]].map(([icon, label]) => (
              <button key={icon} type="button" title={`${label} · (B1/B2)`} onClick={() => {}} style={{
                background: 'var(--white)', border: '0.5px solid var(--border)', borderRadius: 8,
                padding: '5px 9px', cursor: 'pointer', color: 'var(--text-muted)',
              }}><i className={`ti ${icon}`} style={{ fontSize: 14 }} /></button>
            ))}
          </span>
        </div>
      </div>

      {/* Selector de peça */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginRight: 4 }}>{t('fitting.piece.select')}:</span>
        {pieces.map(p => {
          const active = p.id === activePieceId
          return (
            <button key={p.id} onClick={() => setActivePieceId(p.id)} style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              background: active ? 'var(--gold-pale)' : 'var(--white)',
              color: active ? 'var(--text-main)' : 'var(--text-muted)',
              border: `1px solid ${active ? 'var(--gold)' : 'var(--border)'}`, borderRadius: 8, padding: '5px 12px',
              fontSize: 11, cursor: 'pointer',
            }}>
              {p.model_codi || `#${p.model}`}
              <Badge variant={gateVariant[p.gate] || 'gray'}>{p.gate}</Badge>
            </button>
          )
        })}
        {session.model && (
          <button onClick={createPiece} disabled={creatingPiece} style={{
            background: 'var(--white)', color: 'var(--gold)', border: '0.5px solid var(--gold)',
            borderRadius: 8, padding: '5px 12px', fontSize: 11, cursor: creatingPiece ? 'default' : 'pointer',
          }}>+ {creatingPiece ? t('fitting.piece.creating') : t('fitting.piece.create')}</button>
        )}
      </div>

      {pieces.length === 0 && (
        <Card><div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>{t('fitting.piece.none')}</div></Card>
      )}

      {/* Graella matricial */}
      {activePieceId && (
        <Card padding={0} style={{ marginBottom: '1.5rem' }}>
          {gridLoading ? (
            <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>{t('app.loading')}</div>
          ) : lines.length === 0 ? (
            <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>{t('fitting.grid.empty')}</div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table key={activePieceId} style={{ borderCollapse: 'collapse', fontSize: 11 }}>
                <thead>
                  {/* Pis 1: talla (colspan 2) */}
                  <tr>
                    <th rowSpan={2} style={stickyHd(0, COL_POM_W)}>{t('fitting.grid.pom')}</th>
                    <th rowSpan={2} style={stickyHd(COL_POM_W, COL_NOM_W)}>{t('fitting.grid.name')}</th>
                    {sizeLabels.map(s => {
                      const base = s === baseLabel
                      return (
                        <th key={s} colSpan={2} style={{
                          ...thStyle, textAlign: 'center',
                          background: base ? 'var(--gold-pale)' : 'var(--bg-muted)',
                          borderLeft: base ? '1px solid var(--base-hairline)' : '0.5px solid var(--border)',
                        }}>
                          {s}{base && <i className="ti ti-star-filled" style={{ fontSize: 10, marginLeft: 4, color: 'var(--gold)' }} />}
                        </th>
                      )
                    })}
                    <th rowSpan={2} style={{ ...thStyle, textAlign: 'right', borderLeft: '0.5px solid var(--border)' }}>{t('fitting.grid.delta')}</th>
                  </tr>
                  {/* Pis 2: teòric | real */}
                  <tr>
                    {sizeLabels.map(s => {
                      const base = s === baseLabel
                      const sub = {
                        ...thStyle, textAlign: 'right', fontSize: 9, padding: '3px 8px',
                        background: base ? 'var(--gold-pale)' : 'var(--bg-muted)',
                      }
                      return [
                        <th key={`${s}-t`} style={{ ...sub, borderLeft: base ? '1px solid var(--base-hairline)' : '0.5px solid var(--border)' }}>{t('fitting.grid.theoretical')}</th>,
                        <th key={`${s}-r`} style={sub}>{t('fitting.grid.actual')}</th>,
                      ]
                    })}
                  </tr>
                </thead>
                <tbody>
                  {pomRows.map((row, i) => {
                    const rowBg = i % 2 === 0 ? 'var(--white)' : 'var(--bg-card)'
                    const baseLine = baseLabel ? row.cells[baseLabel] : null
                    return (
                      <tr key={row.pom_id} style={{ background: rowBg }}>
                        <td style={stickyTd(0, COL_POM_W, rowBg)}>
                          <span style={{ fontSize: 11, fontWeight: 500, color: 'var(--gold)' }}>
                            {row.codi}{row.is_key && <i className="ti ti-star-filled" style={{ fontSize: 9, marginLeft: 3, color: 'var(--gold)' }} title="key measure" />}
                          </span>
                        </td>
                        <td style={{ ...stickyTd(COL_POM_W, COL_NOM_W, rowBg), fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'normal' }}>{row.nom}</td>
                        {sizeLabels.map(s => {
                          const base = s === baseLabel
                          const line = row.cells[s]
                          return [
                            <TheoreticalCell key={`${s}-t`} line={line} base={base} />,
                            <RealCell key={`${s}-r`} line={line} base={base}
                              value={line ? reals[line.id] ?? '' : ''} note={line ? notes[line.id] ?? '' : ''}
                              onValue={onValue} onNote={onNote} />,
                          ]
                        })}
                        <DeltaCell baseLine={baseLine} baseReal={baseLine ? reals[baseLine.id] : null} />
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* Gate de la peça activa */}
      {activePiece && lines.length > 0 && (
        <Card>
          <GateBar
            key={activePieceId}
            piece={{ ...activePiece, gate: grid?.gate ?? activePiece.gate, gate_motiu: grid?.gate_motiu ?? activePiece.gate_motiu }}
            onGate={handleGate}
            onClose={handleClose}
          />
        </Card>
      )}
    </div>
  )
}

const thStyle = {
  padding: '0.5rem 0.8rem', fontSize: 10, letterSpacing: '0.08em',
  textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 500,
  borderBottom: '0.5px solid var(--border)', whiteSpace: 'nowrap',
}
