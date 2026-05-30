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
// el flag `is_key` que la línia JA porta — llavors aquí substituir TOL_FALLBACK per
// line.tolerancia_*. NO toquem el serializer ara (A2 és frontend).
const TOL_FALLBACK = 0.6

const estatVariant = { Oberta: 'warn', Tancada: 'ok', Anullada: 'gray' }
const gateVariant  = { OK: 'ok', NO_OK: 'err', EXCEPCIO: 'warn', Pendent: 'gray' }

function toleranceColor(real, teoric) {
  if (real === '' || real == null) return null
  const r = Number(real)
  if (Number.isNaN(r) || teoric == null) return null
  return Math.abs(r - Number(teoric)) > TOL_FALLBACK ? 'out' : 'in'
}

// Debounce d'autosave PER CEL·LA: cada instància (un (line.id, field)) té el seu
// propi timer, així saltar ràpid entre cel·les no cancel·la desats pendents d'altres.
function useCellAutosave(lineId, field, isNumber) {
  const [state, setState] = useState('idle') // idle | saving | saved | error
  const timerRef = useRef(null)
  const savedRef = useRef(null)

  useEffect(() => () => { clearTimeout(timerRef.current); clearTimeout(savedRef.current) }, [])

  const schedule = useCallback((raw) => {
    setState('saving')
    clearTimeout(timerRef.current)
    clearTimeout(savedRef.current)
    timerRef.current = setTimeout(() => {
      const value = isNumber ? (raw === '' ? null : Number(raw)) : raw
      pieceFittingLines.update(lineId, { [field]: value })
        .then(() => {
          setState('saved')
          savedRef.current = setTimeout(() => setState('idle'), 2000)
        })
        .catch(() => setState('error')) // NO toquem el valor local: es preserva
    }, 800)
  }, [lineId, field, isNumber])

  return [state, schedule]
}

function SaveStatus({ state }) {
  const { t } = useTranslation()
  if (state === 'idle') return null
  const map = {
    saving: { txt: t('fitting.grid.saving'), color: 'var(--gray)' },
    saved:  { txt: t('fitting.grid.saved'),  color: 'var(--ok)' },
    error:  { txt: t('fitting.grid.save_error'), color: 'var(--err)' },
  }
  const s = map[state]
  return <span style={{ fontSize: 9, color: s.color, display: 'block', marginTop: 1 }}>{s.txt}</span>
}

function TheoreticalValue({ line }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const evo = line.evolucio || []
  return (
    <span
      style={{ position: 'relative', fontSize: 10, color: 'var(--gray)', cursor: evo.length ? 'help' : 'default' }}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      {t('fitting.grid.theoretical')}: {line.valor_teoric ?? '—'}
      {evo.length > 0 && <i className="ti ti-history" style={{ fontSize: 10, marginLeft: 3, color: 'var(--gold)' }} />}
      {open && evo.length > 0 && (
        <div style={{
          position: 'absolute', zIndex: 20, top: '100%', left: 0, marginTop: 4,
          background: 'var(--white)', border: '0.5px solid #e4e4e2', borderRadius: 8,
          padding: '6px 8px', boxShadow: '0 4px 16px rgba(0,0,0,0.08)',
          whiteSpace: 'nowrap', textAlign: 'left',
        }}>
          <div style={{ fontSize: 9, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--gray)', marginBottom: 4 }}>
            {t('fitting.grid.evolution')}
          </div>
          {evo.map(e => (
            <div key={e.version_number} style={{ fontSize: 11, color: e.is_active ? 'var(--charcoal)' : 'var(--gray)', fontWeight: e.is_active ? 500 : 300 }}>
              v{e.version_number} · {e.data ? e.data.slice(0, 10) : '—'} · {e.valor_cm}{e.aprovada ? ' ✓' : ''}
            </div>
          ))}
        </div>
      )}
    </span>
  )
}

function GridCell({ line }) {
  const { t } = useTranslation()
  const [real, setReal] = useState(line.valor_real ?? '')
  const [nota, setNota] = useState(line.nota ?? '')
  const [realState, saveReal] = useCellAutosave(line.id, 'valor_real', true)
  const [notaState, saveNota] = useCellAutosave(line.id, 'nota', false)

  const color = toleranceColor(real, line.valor_teoric)
  const colorBg = color === 'out' ? 'var(--err-bg)' : color === 'in' ? 'var(--ok-bg)' : 'var(--white)'
  const colorFg = color === 'out' ? 'var(--err)' : color === 'in' ? 'var(--ok)' : 'var(--charcoal)'

  return (
    <td style={{ padding: '6px 8px', borderBottom: '0.5px solid var(--gray-l)', verticalAlign: 'top' }}>
      <TheoreticalValue line={line} />
      <input
        type="number" step="0.1" value={real}
        onChange={e => { setReal(e.target.value); saveReal(e.target.value) }}
        style={{
          width: 64, padding: '3px 6px', marginTop: 2, fontSize: 12,
          fontVariantNumeric: 'tabular-nums', textAlign: 'right',
          border: `1px solid ${color ? colorFg : '#e4e4e2'}`, borderRadius: 6,
          background: colorBg, color: colorFg, fontFamily: 'var(--font)', boxSizing: 'border-box',
        }}
      />
      <SaveStatus state={realState} />
      <input
        type="text" value={nota} placeholder={t('fitting.grid.notes')}
        onChange={e => { setNota(e.target.value); saveNota(e.target.value) }}
        style={{
          width: 64, padding: '2px 6px', marginTop: 3, fontSize: 10,
          border: '0.5px solid #e4e4e2', borderRadius: 6,
          background: 'var(--white)', color: 'var(--gray)', fontFamily: 'var(--font)', boxSizing: 'border-box',
        }}
      />
      <SaveStatus state={notaState} />
    </td>
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
    if ((value === 'NO_OK' || value === 'EXCEPCIO') && !reason.trim()) {
      return // espera que l'usuari empleni el motiu i confirmi
    }
    submit(value, reason)
  }

  const submit = (value, reason) => {
    setBusy(true)
    onGate(value, reason)
      .catch(() => setError(t('fitting.gate.save_error')))
      .finally(() => setBusy(false))
  }

  const confirmReason = () => {
    if (!motiu.trim()) { setError(t('fitting.gate.reason_required')); return }
    submit(resultat, motiu)
  }

  const closePiece = () => {
    setClosing(true)
    setError('')
    onClose().catch(() => setError(t('fitting.piece.close_error'))).finally(() => setClosing(false))
  }

  const btn = (value, label, variant) => {
    const active = resultat === value
    const v = gateVariant[value]
    return (
      <button key={value} type="button" disabled={busy} onClick={() => apply(value)} style={{
        display: 'inline-flex', alignItems: 'center', gap: 5,
        background: active ? `var(--${v}-bg)` : 'var(--white)',
        color: active ? `var(--${v})` : 'var(--gray)',
        border: `1px solid ${active ? `var(--${v})` : '#e4e4e2'}`,
        borderRadius: 8, padding: '6px 14px', fontSize: 12,
        cursor: busy ? 'default' : 'pointer', fontFamily: 'var(--font)',
      }}>{label}</button>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
        <span style={{ fontSize: 11, color: 'var(--gray)', marginRight: 4 }}>{t('fitting.gate.title')}:</span>
        {btn('OK', t('fitting.gate.ok'))}
        {btn('NO_OK', t('fitting.gate.no_ok'))}
        {btn('EXCEPCIO', t('fitting.gate.exception'))}
        {piece.gate && piece.gate !== 'Pendent' && (
          <Badge variant={gateVariant[piece.gate] || 'gray'} style={{ marginLeft: 4 }}>{piece.gate}</Badge>
        )}
        <button type="button" disabled={closing} onClick={closePiece} style={{
          marginLeft: 'auto', background: 'var(--white)', color: 'var(--gray)',
          border: '0.5px solid #e4e4e2', borderRadius: 8, padding: '6px 14px',
          fontSize: 12, cursor: closing ? 'default' : 'pointer', fontFamily: 'var(--font)',
        }}>{closing ? t('fitting.piece.closing') : t('fitting.piece.close')}</button>
      </div>
      {needsReason && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <input
            type="text" value={motiu} placeholder={t('fitting.gate.reason')}
            onChange={e => setMotiu(e.target.value)}
            style={{
              flex: 1, maxWidth: 360, padding: '6px 10px', fontSize: 12,
              border: '0.5px solid #e4e4e2', borderRadius: 8, fontFamily: 'var(--font)',
            }}
          />
          <button type="button" disabled={busy} onClick={confirmReason} style={{
            background: 'var(--charcoal)', color: 'var(--white)', border: 'none',
            borderRadius: 8, padding: '6px 14px', fontSize: 12, cursor: 'pointer', fontFamily: 'var(--font)',
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
      .then(res => setGrid(res.data))
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
        piece_fittings: (s.piece_fittings || []).map(p =>
          p.id === activePieceId ? { ...p, gate, gate_motiu } : p),
      } : s)
    })
  }

  const handleClose = () => {
    return pieceFittings.close(activePieceId).then(() => loadSession())
  }

  if (loading) {
    return <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13 }}>{t('app.loading')}</div>
  }
  if (!session) return null

  const pieces = session.piece_fittings || []
  const lines = grid?.lines || []
  const sizeLabels = [...new Set(lines.map(l => l.size_label))]
  const pomMap = new Map()
  for (const l of lines) {
    if (!pomMap.has(l.pom_id)) {
      pomMap.set(l.pom_id, { pom_id: l.pom_id, codi: l.codi, nom: l.nom, is_key: l.is_key, cells: {} })
    }
    pomMap.get(l.pom_id).cells[l.size_label] = l
  }
  const pomRows = [...pomMap.values()]
  const activePiece = pieces.find(p => p.id === activePieceId)

  return (
    <div>
      {/* Capçalera mínima — el panell ric ve al DOC B */}
      <div style={{ display: 'flex', alignItems: 'flex-start', marginBottom: '1rem' }}>
        <button onClick={() => navigate('/fittings')} style={{
          background: 'none', border: 'none', color: 'var(--gray)', cursor: 'pointer',
          fontSize: 12, fontFamily: 'var(--font)', padding: 0, marginRight: 12,
        }}>← {t('app.back')}</button>
      </div>
      <Card style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.5rem', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: 18, fontWeight: 500 }}>{session.target?.label || `#${session.id}`}</div>
            <div style={{ fontSize: 11, color: 'var(--gray)' }}>{t('fitting.sessions.title')} #{session.id}</div>
          </div>
          <Badge variant="gate">{session.fase_display || session.fase}</Badge>
          <Badge variant={estatVariant[session.estat] || 'gray'}>{session.estat_display || session.estat}</Badge>
          <div style={{ fontSize: 12, color: 'var(--gray)' }}>
            <span style={{ marginRight: 16 }}>{t('fitting.session.date')}: {session.data || '—'}</span>
            <span style={{ marginRight: 16 }}>{t('fitting.session.responsable')}: {session.responsable_nom || '—'}</span>
            <span>{t('fitting.session.lloc')}: {session.lloc || '—'}</span>
          </div>
        </div>
      </Card>

      {/* Selector de peça */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        <span style={{ fontSize: 11, color: 'var(--gray)', marginRight: 4 }}>{t('fitting.piece.select')}:</span>
        {pieces.map(p => {
          const active = p.id === activePieceId
          return (
            <button key={p.id} onClick={() => setActivePieceId(p.id)} style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              background: active ? 'var(--charcoal)' : 'var(--white)',
              color: active ? 'var(--white)' : 'var(--gray)',
              border: '0.5px solid #e4e4e2', borderRadius: 8, padding: '5px 12px',
              fontSize: 11, cursor: 'pointer', fontFamily: 'var(--font)',
            }}>
              {p.model_codi || `#${p.model}`}
              <Badge variant={gateVariant[p.gate] || 'gray'}>{p.gate}</Badge>
            </button>
          )
        })}
        {session.model && (
          <button onClick={createPiece} disabled={creatingPiece} style={{
            background: 'var(--white)', color: 'var(--gold)', border: '0.5px solid var(--gold)',
            borderRadius: 8, padding: '5px 12px', fontSize: 11,
            cursor: creatingPiece ? 'default' : 'pointer', fontFamily: 'var(--font)',
          }}>+ {creatingPiece ? t('fitting.piece.creating') : t('fitting.piece.create')}</button>
        )}
      </div>

      {pieces.length === 0 && (
        <Card><div style={{ padding: '1rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13 }}>
          {t('fitting.piece.none')}
        </div></Card>
      )}

      {/* Graella de treball */}
      {activePieceId && (
        <Card padding={0} style={{ marginBottom: '1.5rem' }}>
          {gridLoading ? (
            <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13 }}>{t('app.loading')}</div>
          ) : lines.length === 0 ? (
            <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13 }}>{t('fitting.grid.empty')}</div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              {/* key=activePieceId → remunta les cel·les en canviar de peça (reset d'estat local net) */}
              <table key={activePieceId} style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={thStyle}>{t('fitting.grid.pom')}</th>
                    {sizeLabels.map(s => (
                      <th key={s} style={{ ...thStyle, textAlign: 'right' }}>{s}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {pomRows.map(row => (
                    <tr key={row.pom_id}>
                      <td style={{ padding: '6px 10px', borderBottom: '0.5px solid var(--gray-l)', verticalAlign: 'top', whiteSpace: 'nowrap' }}>
                        <div style={{ fontSize: 11, fontWeight: 500, color: 'var(--gold)' }}>
                          {row.codi}{row.is_key && <i className="ti ti-star-filled" style={{ fontSize: 10, marginLeft: 4, color: 'var(--gold)' }} />}
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--gray)' }}>{row.nom}</div>
                      </td>
                      {sizeLabels.map(s => (
                        row.cells[s]
                          ? <GridCell key={s} line={row.cells[s]} />
                          : <td key={s} style={{ borderBottom: '0.5px solid var(--gray-l)' }} />
                      ))}
                    </tr>
                  ))}
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
  padding: '0.6rem 0.8rem', fontSize: 10, letterSpacing: '0.1em',
  textTransform: 'uppercase', color: 'var(--gray)', fontWeight: 400,
  borderBottom: '0.5px solid #e4e4e2', textAlign: 'left', whiteSpace: 'nowrap',
}
