import { useState, useEffect } from 'react'
import { models as modelsApi } from '../../api/endpoints'
import { overlayBase } from '../ui/overlay'
import { selS } from '../ui/buttons'

const MONO = 'IBM Plex Mono, monospace'

/**
 * Selector de MODEL, desacoblat de l'acte.
 *
 * Extret de `FittingNowPicker` (FittingSessionList.jsx), que era l'únic lloc del sistema amb
 * cerca amb debounce sobre models — i que tenia el picker i la seva acció (`scheduleNow`)
 * cosits en una sola peça. Quan una segona superfície (la còpia model→model) ha necessitat
 * exactament la mateixa tria, la llei de `CLAUDE.md` («no més pedaços: unificar el ja
 * construït») deia extreure'l, no copiar-lo per tercera vegada.
 *
 * El component NOMÉS tria: crida `onPick(model)` i prou. Qui el munta decideix què fa amb la
 * tria, si tanca el modal, i com informa dels errors — per això `busyId`, `error` i el text de
 * la capçalera venen de fora. Així serveix tant per a un acte immediat (fitting ara) com per a
 * un formulari que continua després de la tria (còpia de POMs).
 *
 * Props:
 *   title, subtitle, searchPlaceholder, emptyLabel, loadingLabel, cancelLabel — textos ja
 *     traduïts pel consumidor (aquest component no crida `t()`: no té cap text propi).
 *   onPick(model)  — tria feta.
 *   onClose()      — cancel·lació (clic fora o botó).
 *   busyId         — id del model en curs, per deshabilitar-ne la fila (opcional).
 *   error          — missatge d'error a ensenyar sobre la llista (opcional).
 *   excludeId      — model que NO ha de sortir a la llista (p.ex. el model actual).
 */
export default function ModelPicker({
  title, subtitle, searchPlaceholder, emptyLabel, loadingLabel, cancelLabel,
  onPick, onClose, busyId = null, error = null, excludeId = null,
}) {
  const [q, setQ] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    setLoading(true)
    const id = setTimeout(() => {
      modelsApi.list({ ...(q.trim() ? { search: q.trim() } : {}), page_size: 20, ordering: '-data_entrada' })
        .then(r => { if (alive) setResults(r.data?.results ?? r.data ?? []) })
        .catch(() => { if (alive) setResults([]) })
        .finally(() => { if (alive) setLoading(false) })
    }, 200)
    return () => { alive = false; clearTimeout(id) }
  }, [q])

  const visibles = excludeId ? results.filter(m => m.id !== excludeId) : results

  return (
    <div onClick={onClose} style={overlayBase({ alignItems: 'center' })}>
      <div onClick={e => e.stopPropagation()} style={{
        background: 'var(--white)', borderRadius: 12, padding: 22, width: 460, maxWidth: '92vw',
        maxHeight: '85vh', display: 'flex', flexDirection: 'column', fontFamily: MONO,
      }}>
        <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>{title}</h2>
        {subtitle && <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', marginBottom: 12 }}>{subtitle}</p>}
        <input autoFocus value={q} onChange={e => setQ(e.target.value)} placeholder={searchPlaceholder}
          style={{ ...selS, width: '100%', marginBottom: 10 }} />
        {error && <div style={{ color: 'var(--err)', fontSize: 'var(--fs-body)', marginBottom: 8 }}>{error}</div>}
        <div style={{ overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4, minHeight: 120 }}>
          {loading ? (
            <div style={{ color: 'var(--gray)', fontSize: 'var(--fs-body)', padding: '10px 2px' }}>{loadingLabel}</div>
          ) : visibles.length === 0 ? (
            <div style={{ color: 'var(--gray)', fontSize: 'var(--fs-body)', padding: '10px 2px' }}>{emptyLabel}</div>
          ) : visibles.map(m => (
            <button key={m.id} type="button" disabled={busyId === m.id} onClick={() => onPick(m)}
              style={{
                display: 'flex', alignItems: 'center', gap: 10, textAlign: 'left', width: '100%',
                border: '0.5px solid var(--gray-l)', borderRadius: 6, padding: '8px 10px',
                background: 'var(--white)', cursor: busyId === m.id ? 'wait' : 'pointer',
                fontFamily: MONO, fontSize: 'var(--fs-body)',
              }}>
              <span style={{ fontWeight: 700, color: 'var(--gold)' }}>{m.codi_intern}</span>
              <span style={{ color: 'var(--text-main)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.nom_prenda}</span>
              <span style={{ marginLeft: 'auto', color: 'var(--gray)' }}>{m.fase_actual}</span>
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 14 }}>
          <button onClick={onClose} style={{ ...selS, cursor: 'pointer' }}>{cancelLabel}</button>
        </div>
      </div>
    </div>
  )
}
