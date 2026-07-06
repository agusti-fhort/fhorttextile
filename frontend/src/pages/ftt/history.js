import { useEffect, useRef } from 'react'

// ════════════════════════════════════════════════════════════════════════════
// S0 — Pila d'història (undo/redo) sobre `pages`, amb coalescing de ràfegues
// (drags, escriptura contínua…) via debounce. Timeline: past[] ⇄ baseline ⇄ future[].
// Cap mutació in-place: `pages` sempre és una referència NOVA (setPages via map/spread
// a updatePageObjects), per tant és segur desar snapshots per referència.
// ════════════════════════════════════════════════════════════════════════════

const HISTORY_LIMIT = 50
const COALESCE_MS = 500

export function useDocumentHistory({ pages, setPages, setSelectedIds }) {
  const past = useRef([])
  const future = useRef([])
  const baseline = useRef(pages)
  const pagesRef = useRef(pages)
  const timer = useRef(null)
  const pending = useRef(false)
  const applying = useRef(false)

  useEffect(() => {
    pagesRef.current = pages
  }, [pages])

  const commit = () => {
    timer.current = null
    if (!pending.current) return
    past.current.push(baseline.current)
    if (past.current.length > HISTORY_LIMIT) past.current.shift()
    future.current.length = 0
    baseline.current = pagesRef.current
    pending.current = false
  }

  useEffect(() => {
    if (applying.current) {
      applying.current = false
      baseline.current = pages
      return
    }
    if (pages === baseline.current) return
    pending.current = true
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(commit, COALESCE_MS)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pages])

  const undo = () => {
    if (timer.current) {
      clearTimeout(timer.current)
      timer.current = null
      commit()
    }
    if (!past.current.length) return
    const prev = past.current.pop()
    future.current.push(pagesRef.current)
    applying.current = true
    baseline.current = prev
    setPages(prev)
    setSelectedIds([])
  }

  const redo = () => {
    if (!future.current.length) return
    const next = future.current.pop()
    past.current.push(pagesRef.current)
    applying.current = true
    baseline.current = next
    setPages(next)
    setSelectedIds([])
  }

  const reset = (nextPages) => {
    if (timer.current) { clearTimeout(timer.current); timer.current = null }
    past.current.length = 0
    future.current.length = 0
    pending.current = false
    baseline.current = nextPages
    pagesRef.current = nextPages
  }

  return {
    undo,
    redo,
    reset,
    canUndo: () => past.current.length > 0,
    canRedo: () => future.current.length > 0,
  }
}

// ── Clipboard intern (S0): clonatge amb ids frescos + desplaçament en mm ──────
// `makeId` s'injecta des del cridant (uid de TechSheetEditor) per evitar cicle d'import.
export function cloneWithNewIds(obj, makeId) {
  const clone = JSON.parse(JSON.stringify(obj))
  const assignIds = (o) => {
    o.id = makeId()
    if (Array.isArray(o.children)) o.children.forEach(assignIds)
  }
  assignIds(clone)
  return clone
}

export function offsetObjectMm(obj, dx, dy) {
  return { ...obj, x: (obj.x || 0) + dx, y: (obj.y || 0) + dy }
}
