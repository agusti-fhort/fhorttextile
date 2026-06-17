import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { fittingSessions, pieceFittings, pieceFittingLines, fittingPhotos, modelFitxers, models } from '../api/endpoints'
import client from '../api/client'
import Card from '../components/ui/Card'
import Badge from '../components/ui/Badge'

const estatVariant = { Oberta: 'warn', Tancada: 'ok', Anullada: 'gray' }

const COL_POM_W = 78
const COL_NOM_W = 150
const COL_REG_W = 118   // PG-4b-3c — columna de règim (select LINEAR/STEP + etiqueta de regla)

// Ordre de talles segons el size run del model: split per '·' (U+00B7) o ';' + trim
// (mateixa normalització que el backend, que desa amb '·' però admet ';').
// Mai alfabètic. Talles presents a les línies que no surtin al run s'afegeixen al final.
function orderedSizes(sizeRun, present) {
  const run = (sizeRun || '').replace(/;/g, '·').split('·').map(s => s.trim()).filter(Boolean)
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
    ? { position: 'absolute', bottom: 1, left: 4, fontSize: 'var(--fs-caption)', pointerEvents: 'none' }
    : { display: inline ? 'inline-block' : 'block', marginLeft: inline ? 6 : 0, marginTop: inline ? 0 : 1, fontSize: 'var(--fs-caption)' }
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
// Stepper natiu (fletxes); amplada suficient per "104,75" + fletxes. Sense nota per cel·la
// (el comentari és global del fitting, viu a Observacions).
function CurrentFitCell({ line, baseSize, baseValue, value, edited, onValue, onAnchor, onPropagated, focusRef }) {
  // Persist segons règim del POM (ve a la línia): STEP → PATCH pur, només aquesta cel·la.
  // LINEAR/canònic → propaga el delta i repinta les germanes amb el valor_real propagat.
  const lineId = line?.id
  const isStep = line?.logica === 'STEP'
  const persist = useCallback((raw) => {
    const v = raw === '' ? null : Number(raw)
    if (isStep) return pieceFittingLines.update(lineId, { valor_real: v })
    return pieceFittingLines.propagar(lineId, v).then(res => {
      onPropagated(res.data?.linies || [])
      return res
    })
  }, [lineId, isStep, onPropagated])
  const [realState, saveReal] = useDebouncedSave(persist)

  if (!line) return <td style={cellTd(baseSize, false, baseSize)} />

  const modified = value !== '' && value != null && baseValue != null
    && Number(value) !== Number(baseValue)

  return (
    <td style={{ ...cellTd(baseSize, false, baseSize), position: 'relative' }}>
      <input
        type="number" step="0.1" value={value}
        onFocus={() => { focusRef.current = line.id }}
        onBlur={() => { if (focusRef.current === line.id) focusRef.current = null }}
        onChange={e => { onValue(line.id, e.target.value); onAnchor(line.id); saveReal(e.target.value) }}
        style={{
          font: 'inherit', width: 88, padding: '2px 4px', textAlign: 'right',
          border: '1px solid var(--border)', borderRadius: 4, background: 'var(--white)',
          color: modified ? 'var(--err)' : 'var(--text-main)',
          // Ancoratge editat a mà → negreta; germana modificada però propagada → vermell normal.
          fontWeight: modified && edited ? 700 : 400,
          fontVariantNumeric: 'tabular-nums', boxSizing: 'border-box',
        }}
      />
      <SaveStatus state={realState} absolute />
    </td>
  )
}

function EditableContextField({ sessionId, field, label, value }) {
  const [v, setV] = useState(value ?? '')
  const [state, schedule] = useSessionField(sessionId, field)
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
      {label}:&nbsp;
      <input
        value={v} onChange={e => { setV(e.target.value); schedule(e.target.value) }}
        placeholder="—"
        style={{
          width: 120, padding: '1px 2px', fontSize: 'var(--fs-body)', color: 'var(--text-main)',
          border: 'none', borderBottom: '1px solid var(--border)', borderRadius: 0,
          background: 'transparent', boxSizing: 'border-box',
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
      <div style={{ fontSize: 'var(--fs-label)', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 500, marginBottom: 6 }}>
        {label}
      </div>
      {(!files || files.length === 0) ? (
        <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', fontStyle: 'italic' }}>{t('fitting.info.no_files')}</div>
      ) : (
        files.map(f => {
          const url = f.fitxer || f.url_extern || null
          return (
            <div key={f.id} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 'var(--fs-body)', padding: '3px 0' }}>
              <i className="ti ti-file" style={{ fontSize: 13, color: 'var(--gold)' }} />
              <span style={{ color: 'var(--text-main)' }}>{f.nom_fitxer}</span>
              {url && (
                <a href={url} target="_blank" rel="noopener noreferrer"
                  style={{ marginLeft: 4, fontSize: 'var(--fs-body)', color: 'var(--gold)', textDecoration: 'none' }}>
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
        <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>{t('app.loading')}</div>
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

// ── 5B.6-B3 — Pantalla "Gravar el fitting" ───────────────────────────────────
// Revisió abans de consolidar. Gravar = close per cada peça amb canvis (valor_real ≠
// valor_teoric). Descartar = revert atòmic de reals a l'obertura (NO toca sessió/fotos/
// notes). PDF/mail ajornat: "Enviar a" és stub visual, no dispara res.

// Files (POM) d'una peça amb almenys una talla modificada respecte de Base (evolucio[0]).
function changedRows(grid) {
  const lines = grid.lines || []
  const present = new Set(lines.map(l => l.size_label))
  const sizeLabels = orderedSizes(grid.model?.size_run_model, present)
  const baseLabel = (grid.model?.base_size_label || '').trim()
  const pomMap = new Map()
  for (const l of lines) {
    if (!pomMap.has(l.pom_id)) pomMap.set(l.pom_id, { pom_id: l.pom_id, codi: l.codi, nom: l.nom, is_key: l.is_key, cells: {} })
    pomMap.get(l.pom_id).cells[l.size_label] = l
  }
  const baseOf = (l) => l?.evolucio?.[0]?.valor_cm ?? null
  const isMod = (l) => {
    const b = baseOf(l)
    return l && l.valor_real != null && b != null && Number(l.valor_real) !== Number(b)
  }
  const rows = [...pomMap.values()].filter(row => Object.values(row.cells).some(isMod))
  return { sizeLabels, baseLabel, rows, isMod }
}

// Una peça té canvis a gravar si alguna línia té valor_real ≠ valor_teoric (el que close aplica).
function hasSaveChanges(grid) {
  return (grid.lines || []).some(
    l => l.valor_real != null && Math.abs(Number(l.valor_real) - Number(l.valor_teoric)) > 1e-6
  )
}

function ReviewScreen({ session, pieces, onBack, onSaved, onDone, onShowGrid, onCreatePiece, creatingPiece, readOnly }) {
  const { t } = useTranslation()
  const [grids, setGrids] = useState(null)
  const [photos, setPhotos] = useState([])
  const [busy, setBusy] = useState(false)
  const [progress, setProgress] = useState(null)
  const [error, setError] = useState(null)
  // FIX 5/6 — observacions editables + pujada d'imatges.
  const [notes, setNotes] = useState(session.notes || '')
  const [uploading, setUploading] = useState(false)
  // Peça 3 — D5 descartar sessió (motiu inline) + D3 registrar mesures.
  const [discardOpen, setDiscardOpen] = useState(false)
  const [discardMotiu, setDiscardMotiu] = useState('')
  const [pieceErr, setPieceErr] = useState(null)
  const hasPieces = pieces.length > 0

  useEffect(() => {
    let cancelled = false
    Promise.all([
      Promise.all(pieces.map(p => pieceFittings.get(p.id).then(r => r.data))),
      fittingPhotos.list({ session: session.id }).then(r => r.data.results || r.data).catch(() => []),
    ]).then(([gs, ph]) => {
      if (cancelled) return
      setGrids(gs)
      setPhotos(Array.isArray(ph) ? ph : (ph.results || []))
    })
    return () => { cancelled = true }
  }, [pieces, session.id])

  // D4 — "Gravar i tornar": tanca les peces amb canvis, després SEGELLA la sessió
  // (→ Tancada + finished_at) i torna enrere. Sense peces → seal directe.
  const doSave = () => {
    if (grids === null) return
    setBusy(true); setError(null)
    const toClose = (grids || []).filter(hasSaveChanges)
    ;(async () => {
      if (toClose.length) {
        setProgress({ done: 0, total: toClose.length })
        let done = 0
        for (const g of toClose) {
          try {
            await pieceFittings.close(g.id)
            done += 1; setProgress({ done, total: toClose.length })
          } catch (e) {
            setError(t('fitting.save.save_error', { piece: g.model?.codi || g.id }))
            setBusy(false); return
          }
        }
      }
      try {
        await fittingSessions.seal(session.id)   // D4: segellat independent (no toca fase)
      } catch (e) {
        setError(t('fitting.save.seal_error'))
        setBusy(false); return
      }
      setBusy(false); onSaved()
    })()
  }

  // "Descartar canvis" (revert de mesures de les peces) — operació EXISTENT, no toca la sessió.
  const doDiscard = () => {
    if (!window.confirm(t('fitting.save.discard_confirm'))) return
    setBusy(true); setError(null)
    ;(async () => {
      for (const p of pieces) {
        try {
          await pieceFittings.discard(p.id)
        } catch (e) {
          setError(t('fitting.save.discard_error', { piece: p.model_codi || p.id }))
          setBusy(false); return
        }
      }
      setBusy(false); onDone()
    })()
  }

  // D5 — "Descartar sessió" (anul·la la sessió amb motiu) — DIFERENT del revert de mesures.
  const doDiscardSession = () => {
    setBusy(true); setError(null)
    fittingSessions.discardSession(session.id, discardMotiu)
      .then(() => { setBusy(false); onSaved() })
      .catch(() => { setBusy(false); setError(t('fitting.save.discard_session_error')) })
  }

  // D3 — registrar mesures (crea la peça i mostra la graella). Si no hi ha taula de talles → avís.
  const registrarMesures = () => {
    setPieceErr(null)
    Promise.resolve(onCreatePiece())
      .then(() => onShowGrid())
      .catch(e => {
        const msg = e?.response?.data?.error || ''
        setPieceErr(/SizeFitting|talles|GradingVersion/i.test(msg)
          ? t('fitting.save.no_sizes')
          : (msg || t('fitting.save.piece_error')))
      })
  }

  // FIX 5 — desa session.notes (autosave en perdre el focus).
  const saveNotes = () => { fittingSessions.update(session.id, { notes }).catch(() => {}) }

  // FIX 6 — puja imatges al fitting (POST multipart a /fitting-photos/) i recarrega.
  const reloadPhotos = () => {
    fittingPhotos.list({ session: session.id })
      .then(r => setPhotos(r.data.results || r.data || []))
      .catch(() => {})
  }
  const onUpload = (e) => {
    const files = Array.from(e.target.files || [])
    if (!files.length) return
    setUploading(true); setError(null)
    Promise.all(files.map(f => {
      const fd = new FormData()
      fd.append('session', session.id)
      fd.append('fitxer', f)
      return client.post('/api/v1/fitting-photos/', fd)
    }))
      .then(reloadPhotos)
      .catch(() => setError(t('fitting.save.image_error')))
      .finally(() => { setUploading(false); e.target.value = '' })
  }

  const sectionTitle = (icon, label) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 'var(--fs-body)', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 500, marginBottom: 10 }}>
      <i className={`ti ${icon}`} style={{ fontSize: 14, color: 'var(--gold)' }} />{label}
    </div>
  )
  const muted = { fontSize: 'var(--fs-body)', color: 'var(--text-muted)', fontStyle: 'italic' }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '1.25rem' }}>
        <button onClick={onBack} disabled={busy} style={{
          background: 'none', border: 'none', color: 'var(--text-muted)', cursor: busy ? 'default' : 'pointer', fontSize: 'var(--fs-body)', padding: 0, marginRight: 12,
        }}>← {t('fitting.save.back')}</button>
        <span style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, color: 'var(--text-main)' }}>{t('fitting.save.title')}</span>
      </div>

      {grids === null ? (
        <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>{t('app.loading')}</div>
      ) : (
        <>
          {/* D3 — TAULA DE MESURES (opcional): registrar/veure mesures. No bloqueja la revisió. */}
          {!readOnly && (
            <Card title={t('fitting.save.measures')} style={{ marginBottom: '1.25rem' }}>
              {hasPieces ? (
                <button onClick={onShowGrid} style={{
                  background: 'var(--white)', color: 'var(--gold)', border: '0.5px solid var(--gold)',
                  borderRadius: 8, padding: '6px 14px', fontSize: 'var(--fs-body)', cursor: 'pointer',
                }}>{t('fitting.save.view_measures')}</button>
              ) : (
                <>
                  <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginBottom: 8 }}>
                    {t('fitting.save.no_measures')}
                  </div>
                  <button onClick={registrarMesures} disabled={creatingPiece} style={{
                    background: 'var(--white)', color: 'var(--gold)', border: '0.5px solid var(--gold)',
                    borderRadius: 8, padding: '6px 14px', fontSize: 'var(--fs-body)', cursor: creatingPiece ? 'default' : 'pointer',
                  }}>{creatingPiece ? t('fitting.piece.creating') : t('fitting.save.register_measures')}</button>
                  {pieceErr && <div style={{ color: 'var(--err)', fontSize: 'var(--fs-body)', marginTop: 8 }}>{pieceErr}</div>}
                </>
              )}
            </Card>
          )}

          {/* a) CANVIS — per peça, files POM amb talles modificades vs Base (vermell) */}
          <Card title={t('fitting.save.changes')} style={{ marginBottom: '1.25rem' }}>
            {(() => {
              const piecesWithChanges = grids.map(g => ({ g, ...changedRows(g) })).filter(x => x.rows.length > 0)
              if (!piecesWithChanges.length) return <div style={muted}>{t('fitting.save.no_changes')}</div>
              return piecesWithChanges.map(({ g, sizeLabels, baseLabel, rows, isMod }) => (
                <div key={g.id} style={{ marginBottom: 18 }}>
                  <div style={{ fontSize: 'var(--fs-body)', fontWeight: 500, color: 'var(--text-main)', marginBottom: 8 }}>
                    {g.model?.codi}{g.model?.nom ? ` · ${g.model.nom}` : ''}
                  </div>
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ borderCollapse: 'collapse', fontSize: 'var(--fs-body)' }}>
                      <thead>
                        <tr>
                          <th style={{ ...thStyle, textAlign: 'left' }}>{t('fitting.grid.pom')}</th>
                          <th style={{ ...thStyle, textAlign: 'left' }}>{t('fitting.grid.name')}</th>
                          {sizeLabels.map(s => (
                            <th key={s} style={{ ...thStyle, textAlign: 'right', background: s === baseLabel ? 'var(--gold-pale)' : undefined }}>{s}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {rows.map((row, i) => {
                          const rowBg = i % 2 === 0 ? 'var(--white)' : 'var(--bg-card)'
                          return (
                            <tr key={row.pom_id} style={{ background: rowBg }}>
                              <td style={{ padding: '5px 10px', borderBottom: '0.5px solid var(--border)', fontWeight: 500, color: 'var(--gold)', whiteSpace: 'nowrap' }}>
                                {row.codi}{row.is_key && <i className="ti ti-star-filled" style={{ fontSize: 9, marginLeft: 3, color: 'var(--gold)' }} />}
                              </td>
                              <td style={{ padding: '5px 10px', borderBottom: '0.5px solid var(--border)', color: 'var(--text-muted)' }}>{row.nom}</td>
                              {sizeLabels.map(s => {
                                const line = row.cells[s]
                                const mod = isMod(line)
                                return (
                                  <td key={s} style={{
                                    padding: '5px 10px', borderBottom: '0.5px solid var(--border)', textAlign: 'right',
                                    fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap',
                                    background: s === baseLabel ? 'var(--gold-pale)' : undefined,
                                    color: mod ? 'var(--err)' : 'var(--text-main)', fontWeight: mod ? 700 : 400,
                                  }}>
                                    {line?.valor_real == null ? '—' : line.valor_real}
                                  </td>
                                )
                              })}
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))
            })()}
          </Card>

          {/* b) OBSERVACIONS — session.notes (editable, autosave on blur) */}
          <Card title={t('fitting.save.observations')} style={{ marginBottom: '1.25rem' }}>
            <textarea
              value={notes}
              onChange={e => setNotes(e.target.value)}
              onBlur={saveNotes}
              placeholder={t('fitting.save.no_observations')}
              style={{
                width: '100%', minHeight: 80, padding: '8px 10px', fontSize: 'var(--fs-body)',
                border: '1px solid var(--border)', borderRadius: 6, background: 'var(--white)',
                color: 'var(--text-main)', boxSizing: 'border-box', resize: 'vertical', fontFamily: 'inherit',
              }}
            />
          </Card>

          {/* c) IMATGES — pujada (multipart a /fitting-photos/) + miniatures */}
          <Card title={t('fitting.save.images')} style={{ marginBottom: '1.25rem' }}>
            <label style={{
              display: 'inline-flex', alignItems: 'center', gap: 6, marginBottom: 10,
              cursor: uploading ? 'default' : 'pointer', fontSize: 'var(--fs-body)', color: 'var(--gold)',
            }}>
              <input type="file" accept="image/*" multiple onChange={onUpload} disabled={uploading} style={{ display: 'none' }} />
              <i className="ti ti-upload" style={{ fontSize: 14 }} />
              {uploading ? t('fitting.save.uploading') : t('fitting.save.add_images')}
            </label>
            {photos.length === 0 ? (
              <div style={muted}>{t('fitting.save.no_images')}</div>
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
                {photos.map(f => (
                  <a key={f.id} href={f.fitxer} target="_blank" rel="noopener noreferrer"
                    style={{ display: 'block', width: 160, height: 160, borderRadius: 8, overflow: 'hidden', border: '0.5px solid var(--border)' }}>
                    <img src={f.fitxer} alt={f.caption || ''} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                  </a>
                ))}
              </div>
            )}
          </Card>

          {/* d) ENVIAR A (stub de mail) — AMAGAT (Peça 3 · D1): PDF/mail ajornat. */}
          {false && (
            <Card title={t('fitting.save.send_to')} style={{ marginBottom: '1.25rem' }} />
          )}

          {error && (
            <div style={{ color: 'var(--err)', fontSize: 'var(--fs-body)', marginBottom: 12 }}>{error}</div>
          )}
          {progress && busy && (
            <div style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-body)', marginBottom: 12 }}>
              {t('fitting.save.saving_progress', { done: progress.done, total: progress.total })}
            </div>
          )}

          {/* ACCIONS */}
          {readOnly ? (
            <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', paddingTop: 4 }}>
              {t('fitting.save.read_only')}
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, paddingTop: 4, flexWrap: 'wrap' }}>
              <button onClick={doSave} disabled={busy} style={{
                background: 'var(--gold)', color: 'var(--white)', border: 'none', borderRadius: 8,
                padding: '8px 18px', fontSize: 'var(--fs-body)', fontWeight: 500, cursor: busy ? 'default' : 'pointer', opacity: busy ? 0.6 : 1,
              }}>{t('fitting.save.save_and_back')}</button>
              {hasPieces && (
                <button onClick={doDiscard} disabled={busy} style={{
                  background: 'var(--white)', color: 'var(--text-muted)', border: '0.5px solid var(--border)', borderRadius: 8,
                  padding: '8px 18px', fontSize: 'var(--fs-body)', cursor: busy ? 'default' : 'pointer',
                }}>{t('fitting.save.discard_changes')}</button>
              )}
              {/* D5 — Descartar sessió (anul·lar) amb motiu inline */}
              {!discardOpen ? (
                <button onClick={() => setDiscardOpen(true)} disabled={busy} style={{
                  marginLeft: 'auto', background: 'var(--white)', color: 'var(--err)', border: '0.5px solid var(--err)', borderRadius: 8,
                  padding: '8px 18px', fontSize: 'var(--fs-body)', cursor: busy ? 'default' : 'pointer',
                }}>{t('fitting.save.discard_session')}</button>
              ) : (
                <span style={{ marginLeft: 'auto', display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                  <input type="text" value={discardMotiu} onChange={e => setDiscardMotiu(e.target.value)}
                    placeholder={t('fitting.save.discard_motiu_ph')}
                    style={{ fontSize: 'var(--fs-body)', padding: '6px 10px', border: '1px solid var(--border)', borderRadius: 6, minWidth: 200 }} />
                  <button onClick={doDiscardSession} disabled={busy} style={{
                    background: 'var(--err)', color: 'var(--white)', border: 'none', borderRadius: 8,
                    padding: '8px 14px', fontSize: 'var(--fs-body)', cursor: busy ? 'default' : 'pointer',
                  }}>{t('common.confirm')}</button>
                  <button onClick={() => { setDiscardOpen(false); setDiscardMotiu('') }} disabled={busy} style={{
                    background: 'var(--white)', color: 'var(--text-muted)', border: '0.5px solid var(--border)', borderRadius: 8,
                    padding: '8px 14px', fontSize: 'var(--fs-body)', cursor: busy ? 'default' : 'pointer',
                  }}>{t('common.cancel')}</button>
                </span>
              )}
            </div>
          )}
        </>
      )}
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
  // D2 — la revisió és la pantalla principal; la graella (taula de mesures) és opt-in.
  const [reviewMode, setReviewMode] = useState(true)
  // Valors editables lligats al parent → modificat reactiu i remuntatge net per peça.
  const [reals, setReals] = useState({})
  // Ancoratge únic mòbil (PG-4b-3b): conté NOMÉS la id de l'última cel·la editada a mà → negreta.
  // Les germanes propagades hi queden fora → vermell normal.
  const [editedIds, setEditedIds] = useState(() => new Set())
  // Race guard: id de la cel·la amb focus ara mateix; el repintat de propagar no l'ha de sobreescriure.
  const focusedIdRef = useRef(null)
  // Avís discret si setPomRegim falla (p.ex. 400 sense fallback); no trenca la graella.
  const [regimErr, setRegimErr] = useState(null)

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
    loadSession(true)
      .then(s => {
        // D2 — en entrar a una sessió Programada, obrir-la automàticament (→ Oberta + started_at).
        if (s && s.estat === 'Programada') {
          return fittingSessions.open(s.id).then(r => setSession(r.data)).catch(() => {})
        }
      })
      .finally(() => setLoading(false))
  }, [loadSession])

  const reloadGrid = useCallback(() => {
    if (!activePieceId) { setGrid(null); return Promise.resolve() }
    setGridLoading(true)
    return pieceFittings.get(activePieceId)
      .then(res => {
        setGrid(res.data)
        const r = {}
        for (const l of res.data.lines || []) { r[l.id] = l.valor_real ?? '' }
        setReals(r)
        setEditedIds(new Set())   // canvi de peça → cap ancoratge actiu
        focusedIdRef.current = null
      })
      .finally(() => setGridLoading(false))
  }, [activePieceId])

  useEffect(() => { reloadGrid() }, [reloadGrid])

  const createPiece = () => {
    if (!session?.model) return Promise.resolve()
    setCreatingPiece(true)
    return fittingSessions.createPiece(session.id, session.model)
      .then(res => loadSession().then(() => setActivePieceId(res.data.id)))
      .finally(() => setCreatingPiece(false))
  }

  if (loading) {
    return <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>{t('app.loading')}</div>
  }
  if (!session) return null

  const pieces = session.piece_fittings || []
  const lines = grid?.lines || []
  const model = grid?.model || {}
  // Trim perquè base_size_label coincideixi amb les etiquetes de talla (poden venir amb espais).
  const baseLabel = (model.base_size_label || '').trim()

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
    if (!pomMap.has(l.pom_id)) pomMap.set(l.pom_id, {
      pom_id: l.pom_id, codi: l.codi, nom: l.nom, is_key: l.is_key,
      // Règim per POM (mateix valor a cada talla) → etiqueta de regla a la capçalera de fila.
      logica: l.logica, increment_base: l.increment_base,
      increment_break: l.increment_break, talla_break_label: l.talla_break_label,
      cells: {},
    })
    pomMap.get(l.pom_id).cells[l.size_label] = l
  }
  const pomRows = [...pomMap.values()]

  // Etiqueta de regla compacta (delta·break) per a la capçalera de fila POM.
  // LINEAR amb break: "+2 · break XXL +2.5" · LINEAR uniforme: "+2" · STEP: "lliure" · sense regla: res.
  const regleLabel = (row) => {
    if (row.logica == null) return ''
    if (row.logica === 'STEP') return 'lliure'
    if (row.increment_base == null) return ''
    if (row.increment_break != null && row.talla_break_label)
      return `+${row.increment_base} · break ${row.talla_break_label} +${row.increment_break}`
    return `+${row.increment_base}`
  }

  // Columnes d'evolució: unió de version_number entre totes les línies (ascendent).
  // El primer (v1) és Base; els següents (v2..vM) són Fit 1..Fit (M-1); després el fit
  // actual editable (valor_real). Etiqueta Fit N amb N = version_number - 1.
  const versionNumbers = [...new Set(
    lines.flatMap(l => (l.evolucio || []).map(e => e.version_number))
  )].sort((a, b) => a - b)
  const versionLabel = (vn, idx) =>
    idx === 0 ? t('fitting.grid.base') : t('fitting.grid.fit', { n: vn - 1 })
  const groupSpan = versionNumbers.length + 1  // versions read-only + fit actual

  // Funcions planes (NO hooks): es declaren després dels early-returns, com onValue.
  const onValue = (lineId, v) => setReals(r => ({ ...r, [lineId]: v }))
  // Tocar una cel·la la converteix en l'ancoratge únic (les anteriors passen a propagades/normal).
  const onAnchor = (lineId) => setEditedIds(new Set([lineId]))
  // Aplica les línies que torna propagar; omet la cel·la amb focus (l'usuari pot estar-hi teclejant).
  const applyPropagar = (linies) => setReals(r => {
    const next = { ...r }
    for (const ln of linies) {
      if (ln.id === focusedIdRef.current) continue
      next[ln.id] = ln.valor_real ?? ''
    }
    return next
  })

  // PG-4b-3c — canvi de règim del POM des de la capçalera de fila. Materialitza NOMÉS si difereix
  // (mirar no materialitza). Èxit → actualitza in-place les línies del POM (logica + deltas) perquè
  // la propagació posterior obeeixi el nou règim, sense reload sencer. Error (400 sense fallback) →
  // avís discret; el select revé sol al valor anterior (és controlat per row.logica, inalterat).
  const onRegimChange = (row, nova) => {
    if (!nova || nova === (row.logica ?? '')) return
    setRegimErr(null)
    models.setPomRegim(session.model, row.pom_id, nova)
      .then(res => {
        const d = res.data
        setGrid(g => g ? { ...g, lines: (g.lines || []).map(l => l.pom_id === row.pom_id
          ? { ...l, logica: d.logica, increment_base: d.increment_base,
              increment_break: d.increment_break, talla_break_label: d.talla_break_label }
          : l) } : g)
      })
      .catch(err => setRegimErr(err?.response?.data?.detail || 'No s\'ha pogut canviar el règim.'))
  }

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
      {/* Banda d'identificació plana (cream, integrada amb la pàgina; mai card blanca) */}
      <div style={{ position: 'sticky', top: 0, zIndex: 10, background: 'var(--bg-muted)', padding: '10px 14px', marginBottom: '1rem', borderBottom: '0.5px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
          <button onClick={() => navigate('/fittings')} style={{
            background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 'var(--fs-body)', padding: 0, marginRight: 12,
          }}>← {t('app.back')}</button>
          <Badge variant="gate" style={{ marginRight: 6 }}>{session.fase_display || session.fase}</Badge>
          <Badge variant={estatVariant[session.estat] || 'gray'}>{session.estat_display || session.estat}</Badge>
        </div>
        {/* Línia 1 — identitat */}
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.9rem', flexWrap: 'wrap', marginBottom: 6 }}>
          {idCodi && <Badge variant="gold" style={{ fontSize: 'var(--fs-body)' }}>{idCodi}</Badge>}
          {idNom && <span style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, color: 'var(--text-main)' }}>{idNom}</span>}
          {collection && <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>{t('fitting.id.collection')}: {collection}</span>}
          {clientRef && <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>{t('fitting.id.client_ref')}: {clientRef}</span>}
        </div>
        {/* Línia 2 — context de sessió (persona/lloc editables inline; responsable read-only) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.9rem', flexWrap: 'wrap' }}>
          <EditableContextField sessionId={session.id} field="model_persona" label={t('fitting.id.persona')} value={session.model_persona} />
          <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>{t('fitting.id.responsible')}: {session.responsable_nom || '—'}</span>
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
                  background: active ? 'var(--gold-pale)' : 'transparent',
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

      {/* Pantalla de revisió "Gravar el fitting" (substitueix la taula de treball) */}
      {reviewMode && (
        <ReviewScreen
          session={session}
          pieces={pieces}
          onBack={() => setReviewMode(false)}
          onSaved={() => navigate(-1)}
          onDone={() => { loadSession().then(reloadGrid) }}
          onShowGrid={() => setReviewMode(false)}
          onCreatePiece={createPiece}
          creatingPiece={creatingPiece}
          readOnly={session.estat === 'Tancada' || session.estat === 'Anullada'}
        />
      )}

      {!reviewMode && (<>
      {/* Selector de peça */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginRight: 4 }}>{t('fitting.piece.select')}:</span>
        {pieces.map(p => {
          const active = p.id === activePieceId
          return (
            <button key={p.id} onClick={() => setActivePieceId(p.id)} style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              background: active ? 'var(--gold-pale)' : 'var(--white)',
              color: active ? 'var(--text-main)' : 'var(--text-muted)',
              border: `1px solid ${active ? 'var(--gold)' : 'var(--border)'}`, borderRadius: 8, padding: '5px 12px',
              fontSize: 'var(--fs-body)', cursor: 'pointer',
            }}>
              {p.model_codi || `#${p.model}`}
            </button>
          )
        })}
        {session.model && (
          <button onClick={createPiece} disabled={creatingPiece} style={{
            background: 'var(--white)', color: 'var(--gold)', border: '0.5px solid var(--gold)',
            borderRadius: 8, padding: '5px 12px', fontSize: 'var(--fs-body)', cursor: creatingPiece ? 'default' : 'pointer',
          }}>+ {creatingPiece ? t('fitting.piece.creating') : t('fitting.piece.create')}</button>
        )}
        <button onClick={() => setReviewMode(true)} style={{
          marginLeft: 'auto', background: 'var(--gold)', color: 'var(--white)', border: 'none',
          borderRadius: 8, padding: '6px 14px', fontSize: 'var(--fs-body)', fontWeight: 500, cursor: 'pointer',
        }}>← {t('fitting.save.back_to_review')}</button>
      </div>

      {pieces.length === 0 && (
        <Card><div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>{t('fitting.piece.none')}</div></Card>
      )}

      {/* Graella matricial */}
      {activePieceId && (
        <Card padding={0} style={{ marginBottom: '1.5rem' }}>
          {regimErr && (
            <div style={{ color: 'var(--err)', fontSize: 'var(--fs-body)', padding: '6px 10px' }}>{regimErr}</div>
          )}
          {gridLoading ? (
            <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>{t('app.loading')}</div>
          ) : lines.length === 0 ? (
            <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>{t('fitting.grid.empty')}</div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table key={activePieceId} style={{ borderCollapse: 'collapse', fontSize: 'var(--fs-body)' }}>
                <thead>
                  {/* Pis 1: talla (colspan = versions + fit actual) */}
                  <tr>
                    <th rowSpan={2} style={stickyHd(0, COL_POM_W)}>{t('fitting.grid.pom')}</th>
                    <th rowSpan={2} style={stickyHd(COL_POM_W, COL_NOM_W)}>{t('fitting.grid.name')}</th>
                    <th rowSpan={2} style={stickyHd(COL_POM_W + COL_NOM_W, COL_REG_W)}>Règim</th>
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
                        ...thStyle, textAlign: 'right', fontSize: 'var(--fs-caption)', padding: '3px 8px',
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
                          <span style={{ fontSize: 'var(--fs-body)', fontWeight: 500, color: 'var(--gold)' }}>
                            {row.codi}{row.is_key && <i className="ti ti-star-filled" style={{ fontSize: 9, marginLeft: 3, color: 'var(--gold)' }} title={t('fitting.key_measure')} />}
                          </span>
                        </td>
                        <td style={{ ...stickyTd(COL_POM_W, COL_NOM_W, rowBg), fontSize: 'var(--fs-body)', color: 'var(--text-muted)', whiteSpace: 'normal' }}>{row.nom}</td>
                        <td style={stickyTd(COL_POM_W + COL_NOM_W, COL_REG_W, rowBg)}>
                          {/* PG-4b-3c — règim del POM: select (dalt) + etiqueta de regla (sota, moguda des de la capçalera). */}
                          <select
                            value={row.logica ?? ''}
                            onChange={e => onRegimChange(row, e.target.value)}
                            style={{
                              font: 'inherit', fontSize: 'var(--fs-label)', width: '100%', padding: '1px 2px',
                              border: '1px solid var(--border)', borderRadius: 4,
                              background: 'var(--white)', color: 'var(--text-main)', boxSizing: 'border-box',
                            }}
                          >
                            {row.logica == null && <option value="">—</option>}
                            <option value="LINEAR">LINEAR</option>
                            <option value="STEP">STEP</option>
                          </select>
                          {regleLabel(row) && (
                            <div style={{ fontSize: 'var(--fs-caption)', fontWeight: 400, color: 'var(--text-muted)', whiteSpace: 'nowrap', marginTop: 1 }}>
                              {regleLabel(row)}
                            </div>
                          )}
                        </td>
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
                              value={line ? reals[line.id] ?? '' : ''}
                              edited={line ? editedIds.has(line.id) : false}
                              onValue={onValue} onAnchor={onAnchor} onPropagated={applyPropagar} focusRef={focusedIdRef} />
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
      </>)}

    </div>
  )
}

const thStyle = {
  padding: '0.5rem 0.8rem', fontSize: 'var(--fs-label)', letterSpacing: '0.08em',
  textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 500,
  borderBottom: '0.5px solid var(--border)', whiteSpace: 'nowrap',
}
