import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { fittingSessions, pieceFittings, pieceFittingLines, modelFitxers } from '../api/endpoints'
import Card from '../components/ui/Card'
import Badge from '../components/ui/Badge'

const estatVariant = { Oberta: 'warn', Tancada: 'ok', Anullada: 'gray' }
const gateVariant  = { OK: 'ok', NO_OK: 'err', EXCEPCIO: 'warn', Pendent: 'gray' }

const COL_POM_W = 78
const COL_NOM_W = 150

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

function SaveStatus({ state, inline, absolute }) {
  const { t } = useTranslation()
  if (state === 'idle') return null
  const map = {
    saving: { txt: t('fitting.grid.saving'), color: 'var(--text-muted)' },
    saved:  { txt: t('fitting.grid.saved'),  color: 'var(--ok)' },
    error:  { txt: t('fitting.grid.save_error'), color: 'var(--err)' },
  }
  const s = map[state]
  // absolute = no ocupa espai (no altera l'alçada de la fila de la graella).
  const pos = absolute
    ? { position: 'absolute', bottom: 1, left: 4, fontSize: 8, pointerEvents: 'none' }
    : { display: inline ? 'inline-block' : 'block', marginLeft: inline ? 6 : 0, marginTop: inline ? 0 : 1, fontSize: 9 }
  return <span style={{ color: s.color, ...pos }}>{s.txt}</span>
}

// Estil base d'una cel·la de valor. baseSize = columna d'una talla base (fons daurat).
// groupStart = primera columna del grup d'una talla (filet esquerre). groupEnd = última.
const cellTd = (baseSize, groupStart, groupEnd) => ({
  padding: '5px 8px', borderBottom: '0.5px solid var(--border)', verticalAlign: 'middle',
  textAlign: 'right', whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums',
  background: baseSize ? 'var(--gold-pale)' : undefined,
  borderLeft: groupStart && baseSize ? '1px solid var(--gold)' : '0.5px solid var(--border)',
  borderRight: groupEnd && baseSize ? '1px solid var(--gold)' : undefined,
})

// Valor d'una versió (read-only). isBase = columna Base (v1) → text atenuat.
function VersionCell({ value, isBase, baseSize, groupStart }) {
  return (
    <td style={{ ...cellTd(baseSize, groupStart, false), color: isBase ? 'var(--text-muted)' : 'var(--text-main)' }}>
      {value == null ? '—' : value}
    </td>
  )
}

// Fit actual (valor_real): única cel·la editable. Vermell+negreta si difereix de Base.
// Triangle discret de nota a la cantonada; clic obre el popover existent.
function CurrentFitCell({ line, baseSize, baseValue, value, note, onValue, onNote }) {
  const { t } = useTranslation()
  const [realState, saveReal] = useCellAutosave(line?.id, 'valor_real', true)
  const [notaState, saveNota] = useCellAutosave(line?.id, 'nota', false)
  const [noteOpen, setNoteOpen] = useState(false)

  if (!line) return <td style={cellTd(baseSize, false, baseSize)} />

  const hasNote = (note ?? '').trim() !== ''
  const modified = value !== '' && value != null && baseValue != null
    && Number(value) !== Number(baseValue)

  return (
    <td style={{ ...cellTd(baseSize, false, baseSize), position: 'relative' }}>
      <input
        className="fit-input" type="number" step="0.1" inputMode="decimal" value={value}
        onChange={e => { onValue(line.id, e.target.value); saveReal(e.target.value) }}
        style={{
          font: 'inherit', width: 66, padding: '2px 4px', textAlign: 'right',
          border: '1px solid var(--border)', borderRadius: 4, background: 'var(--white)',
          color: modified ? 'var(--err)' : 'var(--text-main)',
          fontWeight: modified ? 700 : 400,
          fontVariantNumeric: 'tabular-nums', boxSizing: 'border-box',
        }}
      />
      {/* Triangle de nota a la cantonada (daurat si hi ha nota, tènue si no). */}
      <button
        type="button" onClick={() => setNoteOpen(o => !o)}
        title={hasNote ? note : t('fitting.grid.note')}
        style={{
          position: 'absolute', top: 0, right: 0, width: 0, height: 0, padding: 0,
          border: '5px solid transparent',
          borderTopColor: hasNote ? 'var(--gold)' : 'var(--border)',
          borderRightColor: hasNote ? 'var(--gold)' : 'var(--border)',
          background: 'none', cursor: 'pointer',
        }}
      />
      <SaveStatus state={realState} absolute />
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

// Panell info de fitxers del model (read-only). 3 grups via filtres del backend.
function ModelFilesPanel({ modelId }) {
  const { t } = useTranslation()
  const [groups, setGroups] = useState(null)

  useEffect(() => {
    let cancelled = false
    Promise.all([
      modelFitxers.list({ model: modelId, categoria: 'Patro' }),
      modelFitxers.list({ model: modelId, tipus: 'MARCADA' }),
      modelFitxers.list({ model: modelId, categoria: 'Document' }),
    ])
      .then(([p, m, d]) => {
        if (cancelled) return
        setGroups({
          patterns: p.data.results || [],
          markers: m.data.results || [],
          documents: d.data.results || [],
        })
      })
      .catch(() => { if (!cancelled) setGroups({ patterns: [], markers: [], documents: [] }) })
    return () => { cancelled = true }
  }, [modelId])

  const renderGroup = (label, files) => (
    <div style={{ marginBottom: 14 }}>
      <div style={{ fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 500, marginBottom: 6 }}>
        {label}
      </div>
      {(!files || files.length === 0) ? (
        <div style={{ fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic' }}>{t('fitting.info.no_files')}</div>
      ) : (
        files.map(f => {
          const url = f.fitxer || f.url_extern || null
          return (
            <div key={f.id} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, padding: '3px 0' }}>
              <i className="ti ti-file" style={{ fontSize: 13, color: 'var(--gold)' }} />
              <span style={{ color: 'var(--text-main)' }}>{f.nom_fitxer}</span>
              {url && (
                <a href={url} target="_blank" rel="noopener noreferrer"
                  style={{ marginLeft: 4, fontSize: 11, color: 'var(--gold)', textDecoration: 'none' }}>
                  ↓ {t('fitting.info.download')}
                </a>
              )}
            </div>
          )
        })
      )}
    </div>
  )

  return (
    <Card title={t('fitting.info.title')} icon="ti-info-circle" style={{ marginBottom: '1.5rem' }}>
      {groups === null ? (
        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{t('app.loading')}</div>
      ) : (
        <>
          {renderGroup(t('fitting.info.patterns'), groups.patterns)}
          {renderGroup(t('fitting.info.markers'), groups.markers)}
          {renderGroup(t('fitting.info.documents'), groups.documents)}
        </>
      )}
    </Card>
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
  const [infoOpen, setInfoOpen] = useState(false)
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

  // Columnes d'evolució: unió de version_number entre totes les línies (ascendent).
  // El primer (v1) és Base; els següents (v2..vM) són Fit 1..Fit (M-1); després el fit
  // actual editable (valor_real). Etiqueta Fit N amb N = version_number - 1.
  const versionNumbers = [...new Set(
    lines.flatMap(l => (l.evolucio || []).map(e => e.version_number))
  )].sort((a, b) => a - b)
  const versionLabel = (vn, idx) =>
    idx === 0 ? t('fitting.grid.base') : t('fitting.grid.fit', { n: vn - 1 })
  const groupSpan = versionNumbers.length + 1  // versions read-only + fit actual

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
          {/* Icona Info cablada al panell de fitxers (B1); ti-photo/ti-note stub fins a B2 */}
          <span style={{ marginLeft: 'auto', display: 'inline-flex', gap: 6 }}>
            {[
              { icon: 'ti-info-circle', label: t('fitting.id.info'), wired: !!session.model, active: infoOpen, onClick: () => setInfoOpen(o => !o) },
              { icon: 'ti-photo', label: t('fitting.id.photos'), wired: false },
              { icon: 'ti-note', label: t('fitting.id.observations'), wired: false },
            ].map(({ icon, label, wired, active, onClick }) => (
              <button key={icon} type="button"
                title={wired ? label : `${label} · (B2)`}
                onClick={wired ? onClick : () => {}}
                style={{
                  background: active ? 'var(--gold-pale)' : 'var(--white)',
                  border: `0.5px solid ${active ? 'var(--gold)' : 'var(--border)'}`, borderRadius: 8,
                  padding: '5px 9px', cursor: 'pointer',
                  color: active ? 'var(--gold)' : 'var(--text-muted)',
                }}><i className={`ti ${icon}`} style={{ fontSize: 14 }} /></button>
            ))}
          </span>
        </div>
      </div>

      {/* Panell info de fitxers del model (toggle des de la icona Info) */}
      {infoOpen && session.model && <ModelFilesPanel modelId={session.model} />}

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
                  {/* Pis 1: talla (colspan = versions + fit actual) */}
                  <tr>
                    <th rowSpan={2} style={stickyHd(0, COL_POM_W)}>{t('fitting.grid.pom')}</th>
                    <th rowSpan={2} style={stickyHd(COL_POM_W, COL_NOM_W)}>{t('fitting.grid.name')}</th>
                    {sizeLabels.map(s => {
                      const base = s === baseLabel
                      return (
                        <th key={s} colSpan={groupSpan} style={{
                          ...thStyle, textAlign: 'center',
                          background: base ? 'var(--gold-pale)' : 'var(--bg-muted)',
                          borderLeft: base ? '1px solid var(--gold)' : '0.5px solid var(--border)',
                          borderRight: base ? '1px solid var(--gold)' : undefined,
                        }}>
                          {s}{base && <i className="ti ti-star-filled" style={{ fontSize: 10, marginLeft: 4, color: 'var(--gold)' }} />}
                        </th>
                      )
                    })}
                  </tr>
                  {/* Pis 2: Base · Fit1..Fit(M-1) · Fit actual */}
                  <tr>
                    {sizeLabels.flatMap(s => {
                      const base = s === baseLabel
                      const sub = (groupStart, groupEnd) => ({
                        ...thStyle, textAlign: 'right', fontSize: 9, padding: '3px 8px',
                        background: base ? 'var(--gold-pale)' : 'var(--bg-muted)',
                        borderLeft: groupStart && base ? '1px solid var(--gold)' : '0.5px solid var(--border)',
                        borderRight: groupEnd && base ? '1px solid var(--gold)' : undefined,
                      })
                      const cols = versionNumbers.map((vn, idx) => (
                        <th key={`${s}-v${vn}`} style={sub(idx === 0, false)}>{versionLabel(vn, idx)}</th>
                      ))
                      cols.push(
                        <th key={`${s}-cur`} style={sub(false, true)}>{t('fitting.grid.fit_current')}</th>
                      )
                      return cols
                    })}
                  </tr>
                </thead>
                <tbody>
                  {pomRows.map((row, i) => {
                    const rowBg = i % 2 === 0 ? 'var(--white)' : 'var(--bg-card)'
                    return (
                      <tr key={row.pom_id} style={{ background: rowBg }}>
                        <td style={stickyTd(0, COL_POM_W, rowBg)}>
                          <span style={{ fontSize: 11, fontWeight: 500, color: 'var(--gold)' }}>
                            {row.codi}{row.is_key && <i className="ti ti-star-filled" style={{ fontSize: 9, marginLeft: 3, color: 'var(--gold)' }} title="key measure" />}
                          </span>
                        </td>
                        <td style={{ ...stickyTd(COL_POM_W, COL_NOM_W, rowBg), fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'normal' }}>{row.nom}</td>
                        {sizeLabels.flatMap(s => {
                          const base = s === baseLabel
                          const line = row.cells[s]
                          const evoMap = new Map((line?.evolucio || []).map(e => [e.version_number, e.valor_cm]))
                          const baseValue = line?.evolucio?.[0]?.valor_cm ?? null
                          const cells = versionNumbers.map((vn, idx) => (
                            <VersionCell key={`${s}-v${vn}`}
                              value={evoMap.has(vn) ? evoMap.get(vn) : null}
                              isBase={idx === 0} baseSize={base} groupStart={idx === 0} />
                          ))
                          cells.push(
                            <CurrentFitCell key={`${s}-cur`} line={line} baseSize={base} baseValue={baseValue}
                              value={line ? reals[line.id] ?? '' : ''} note={line ? notes[line.id] ?? '' : ''}
                              onValue={onValue} onNote={onNote} />
                          )
                          return cells
                        })}
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
