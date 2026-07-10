import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { fittingSessions, pieceFittings, fittingPhotos, modelFitxers, models, baseMeasurements } from '../api/endpoints'
import client from '../api/client'
import Card from '../components/ui/Card'
import Badge from '../components/ui/Badge'
import MeasureGrid from '../components/model/MeasureGrid'
import EditorHeader from '../components/model/EditorHeader'
import { buildFittingGroups, buildFittingRows, regimeLeadCol, makeFittingOnSave } from '../components/model/fittingGridAdapter'
import { thStyle, SaveStatus, useDebouncedSave } from './fittingShared'

const estatVariant = { Oberta: 'warn', Tancada: 'ok', Anullada: 'gray' }

// Ordre de talles segons el size run del model: split per '·' (U+00B7) o ';' + trim
// (mateixa normalització que el backend, que desa amb '·' però admet ';').
// Mai alfabètic. Talles presents a les línies que no surtin al run s'afegeixen al final.
function orderedSizes(sizeRun, present) {
  const run = (sizeRun || '').replace(/;/g, '·').split('·').map(s => s.trim()).filter(Boolean)
  const ordered = run.filter(s => present.has(s))
  const extras = [...present].filter(s => !run.includes(s))
  return [...ordered, ...extras]
}

// Autosave d'un camp de context de la sessió (model_persona / lloc...). PATCH sessió.
function useSessionField(sessionId, field) {
  const persist = useCallback((raw) => fittingSessions.update(sessionId, { [field]: raw }), [sessionId, field])
  return useDebouncedSave(persist)
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
    // Eix únic `tipus` (S03a · P1). Marcades queda amb el filtre correcte tot i que avui cap
    // escriptor emet tipus='MARCADA': és un forat amb nom, l'omplirà el flux de marcada.
    Promise.all([
      modelFitxers.list({ model: modelId, tipus__in: 'PATRO,ESCALAT' }),
      modelFitxers.list({ model: modelId, tipus: 'MARCADA' }),
      modelFitxers.list({ model: modelId, tipus: 'DOCUMENT' }),
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
          // D13: URL signada de curta vida. Un <a href> no pot portar Authorization.
          const url = f.download_url || f.url_extern || null
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

// Estats en què una sessió és de només lectura (mirall de SEALED_SESSION_ESTATS del backend).
const SEALED_ESTATS = ['Tancada', 'Anullada']

// Una peça té canvis a gravar si alguna línia de la TALLA BASE té valor_real ≠ valor_teoric.
// El filtre per talla base NO és redundant amb l'adapter (que ja només pinta la base): `grid.lines`
// ve de l'API amb totes les talles, i `propagar` reescriu el valor_real de les germanes a cada
// ancoratge. Sense el filtre, una peça sense cap canvi base es marcava "amb canvis" i es cridava
// un `close` que no consolidava res — exactament el que fa `consolidate_base_from_fitting` (P1).
function hasSaveChanges(grid) {
  const base = (grid.model?.base_size_label || '').trim()
  return (grid.lines || []).some(
    l => (!base || l.size_label === base) &&
      l.valor_real != null && Math.abs(Number(l.valor_real) - Number(l.valor_teoric)) > 1e-6
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
      let done = 0
      if (toClose.length) {
        setProgress({ done: 0, total: toClose.length })
        for (const g of toClose) {
          try {
            await pieceFittings.close(g.id)
            done += 1; setProgress({ done, total: toClose.length })
          } catch (e) {
            // P3 — tancament PARCIAL: hi ha peces ja tancades (i GradingVersions v+1 creades) i la
            // sessió segueix oberta. No hi ha rollback ni reintent: s'informa i NO es navega.
            setError(done
              ? t('fitting.save.partial_close', { done, total: toClose.length })
              : t('fitting.save.save_error', { piece: g.model?.codi || g.id }))
            setBusy(false); return
          }
        }
      }
      let estat = null
      try {
        const res = await fittingSessions.seal(session.id)   // D4: segellat independent (no toca fase)
        estat = res.data?.estat
      } catch (e) {
        setError(t('fitting.save.seal_error'))
        setBusy(false); return
      }
      setBusy(false)
      // P3 — el segellat pot ser un no-op silenciós: amb un GarmentSet, `_seal_session` retorna
      // sense tancar si queden peces sense resoldre. Abans es navegava igual i l'usuari marxava
      // creient que havia gravat. Ara es comprova l'estat REAL que retorna `seal`.
      if (estat !== 'Tancada') {
        setError(t('fitting.save.not_sealed'))
        return
      }
      onSaved()
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
  // P2 — la graella base és la pantalla de TREBALL i el landing per defecte. La revisió deixa de
  // ser un pas intermedi (no tenia endpoint ni estat: era un toggle de client) i s'hi arriba amb
  // "Tornar a revisió". Neix a `true` perquè, mentre la sessió carrega, no es pinti una graella
  // buida; l'efecte de càrrega la baixa a `false` si la sessió és editable.
  const [reviewMode, setReviewMode] = useState(true)
  // P5: l'editor és MeasureGrid, que OWNS el seu buffer d'edició (reals/ancoratge/focus interns).
  // El remuntatge net per peça es fa via key={activePieceId} a MeasureGrid. Aquí ja no cal estat de cel·la.
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
          return fittingSessions.open(s.id).then(r => { setSession(r.data); return r.data }).catch(() => s)
        }
        return s
      })
      .then(s => {
        // P2 — landing directe: la revisió només és el landing d'una sessió de només lectura
        // (branca del split de consulta). Si és editable, s'entra a la graella de treball.
        setReviewMode(!s || SEALED_ESTATS.includes(s.estat))
      })
      .finally(() => setLoading(false))
  }, [loadSession])

  // P3 — sortida EXPLÍCITA. Abans era `navigate(-1)`: depenia de l'historial del navegador
  // (podia tornar a qualsevol lloc) i no transportava cap context.
  const sortida = useCallback(() => navigate('/fittings'), [navigate])

  const reloadGrid = useCallback(() => {
    if (!activePieceId) { setGrid(null); return Promise.resolve() }
    setGridLoading(true)
    return pieceFittings.get(activePieceId)
      .then(res => { setGrid(res.data) })   // MeasureGrid sembra el seu buffer des de rows (key per peça)
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
  // Sessió tancada/anul·lada → tota la revisió és de lectura (split 40/60 amb taula en lectura).
  const readOnly = SEALED_ESTATS.includes(session.estat)
  const lines = grid?.lines || []
  const model = grid?.model || {}
  // Trim perquè base_size_label coincideixi amb les etiquetes de talla (poden venir amb espais).
  const baseLabel = (model.base_size_label || '').trim()

  // Identificació (codi/nom): del grid si hi ha peça; si no, de la primera peça.
  const idCodi = model.codi || pieces[0]?.model_codi || null
  const idNom = model.nom || pieces[0]?.model_nom || null
  const collection = session.model_temporada ? `${session.model_temporada}${session.model_any ? ` ${session.model_any}` : ''}` : null
  const clientRef = session.model_codi_client || null

  // Matriu: files = POM. P1 — l'única columna de talla és la BASE (l'eix multi-talla viu a Escalat).
  const pomMap = new Map()
  for (const l of lines) {
    if (!pomMap.has(l.pom_id)) pomMap.set(l.pom_id, {
      pom_id: l.pom_id, codi: l.codi, nom: l.nom, is_key: l.is_key,
      // Nomenclatura 2 línies (nom EN canònic dalt · idioma usuari sota) — heretada per MeasureGrid (P5).
      nom_en: l.nom_en, nom_local: l.nom_local, nom_fitxa: l.nom_fitxa, bm_id: l.bm_id,
      // Règim per POM (mateix valor a cada talla) → etiqueta de regla a la capçalera de fila.
      logica: l.logica, increment_base: l.increment_base,
      increment_break: l.increment_break, talla_break_label: l.talla_break_label,
      cells: {},
    })
    pomMap.get(l.pom_id).cells[l.size_label] = l
  }
  const pomRows = [...pomMap.values()]

  // Columnes d'evolució: unió de version_number entre totes les línies (ascendent).
  // El primer (v1) és Base; els següents (v2..vM) són Fit 1..Fit (M-1); després el fit
  // actual editable (valor_real). Etiqueta Fit N amb N = version_number - 1.
  const versionNumbers = [...new Set(
    lines.flatMap(l => (l.evolucio || []).map(e => e.version_number))
  )].sort((a, b) => a - b)

  // Projecció de l'eix talles×versions al contracte de MeasureGrid (editor únic). Els valors/ancoratge/
  // focus viuen DINS de MeasureGrid; aquí només es construeixen groups/rows/leadCols/onSave.
  const gridGroups = buildFittingGroups(baseLabel, versionNumbers, t)
  const gridRows = buildFittingRows(pomRows, baseLabel, versionNumbers)
  // Només les línies de la BASE són editables (guard de vista al backend); la resta ni es pinta.
  const lineRegimeMap = new Map(
    lines.filter(l => l.size_label === baseLabel).map(l => [l.id, l.logica]))
  const onGridSave = makeFittingOnSave(lineRegimeMap)
  // P4 — autoria del nom a nivell MODEL: nom_fitxa de BaseMeasurement (NO el POM tenant compartit).
  const onNomSave = (bmId, value) => baseMeasurements.update(bmId, { nom_fitxa: value || null }).catch(() => {})

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

  return (
    <div>
      {/* Capçalera UNIFICADA (EditorHeader): identitat de model comuna amb el check + franja
          contextual de la SESSIÓ (gate/estat · col·lecció/client · persona/responsable/lloc · icones). */}
      <div style={{ position: 'sticky', top: 0, zIndex: 10 }}>
        <EditorHeader
          model={{ codi_intern: idCodi, nom_prenda: idNom, base_size_label: model.base_size_label, size_run_model: model.size_run_model }}
          onBack={() => navigate('/fittings')}
          context={
            <>
              <Badge variant="gate">{session.fase_display || session.fase}</Badge>
              <Badge variant={estatVariant[session.estat] || 'gray'}>{session.estat_display || session.estat}</Badge>
              {collection && <span>{t('fitting.id.collection')}: {collection}</span>}
              {clientRef && <span>{t('fitting.id.client_ref')}: {clientRef}</span>}
              <EditableContextField sessionId={session.id} field="model_persona" label={t('fitting.id.persona')} value={session.model_persona} />
              <span>{t('fitting.id.responsible')}: {session.responsable_nom || '—'}</span>
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
            </>
          }
        />
      </div>

      {/* Panell info de fitxers del model (toggle des de la icona Info) */}
      {infoOpen && session.model && <ModelFilesPanel modelId={session.model} />}

      {/* Pantalla de revisió "Gravar el fitting" (substitueix la taula de treball) */}
      {/* Revisió OBERTA (sessió no segellada, "Tornar a revisió"): ReviewScreen sol, sense split. */}
      {reviewMode && !readOnly && (
        <ReviewScreen
          session={session}
          pieces={pieces}
          onBack={() => setReviewMode(false)}
          onSaved={sortida}
          onDone={() => { loadSession().then(reloadGrid) }}
          onShowGrid={() => setReviewMode(false)}
          onCreatePiece={createPiece}
          creatingPiece={creatingPiece}
          readOnly={false}
        />
      )}

      {/* Revisió TANCADA: split 40/60 — esquerra revisió, dreta taula en lectura (peça activa). */}
      {reviewMode && readOnly && (
        <div style={{ display: 'flex', gap: '1.25rem', alignItems: 'flex-start' }}>
          <div style={{ flex: '0 0 40%', minWidth: 0, overflowY: 'auto', maxHeight: 'calc(100vh - 180px)' }}>
            <ReviewScreen
              session={session}
              pieces={pieces}
              onBack={() => setReviewMode(false)}
              onSaved={sortida}
              onDone={() => { loadSession().then(reloadGrid) }}
              onShowGrid={() => setReviewMode(false)}
              onCreatePiece={createPiece}
              creatingPiece={creatingPiece}
              readOnly
            />
          </div>
          <div style={{ flex: '1 1 60%', minWidth: 0, overflow: 'auto', maxHeight: 'calc(100vh - 180px)' }}>
            {!activePieceId ? null
              : lines.length === 0
                ? <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>{t('fitting.grid.empty')}</div>
                : (
                  <MeasureGrid
                    key={activePieceId}
                    editable={false}
                    rows={gridRows} groups={gridGroups}
                    leadCols={[regimeLeadCol(t, onRegimChange, true)]}
                  />
                )}
          </div>
        </div>
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
            <MeasureGrid
              key={activePieceId}
              editable
              rows={gridRows} groups={gridGroups}
              leadCols={[regimeLeadCol(t, onRegimChange, false)]}
              onSave={onGridSave} onNomSave={onNomSave}
            />
          )}
        </Card>
      )}
      </>)}

    </div>
  )
}
