import { useState, useEffect, useCallback } from 'react'
import WorkPlan from './WorkPlan'
import TaskTree from './TaskTree'

// B3 — Tab "Tasques" del Model Sheet: unifica les tasques EXISTENTS (WorkPlan, alimentat pel
// compositor del dashboard) + l'arbre per INICIAR-NE de noves (TaskTree). En iniciar una tasca
// des de l'arbre, es refresca el WorkPlan (load) i la llista de tasques del pare (onTasksChanged).
const API = import.meta.env.VITE_API_URL || ''

export default function TasksTab({ modelId, onOpenTab, modelTaskRows, onTasksChanged }) {
  const token = localStorage.getItem('access_token')
  const [tasques, setTasques] = useState([])

  const load = useCallback(() => {
    fetch(`${API}/api/v1/models/${modelId}/dashboard/`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => (r.ok ? r.json() : null))
      .then(d => { if (d) setTasques(Array.isArray(d.tasques) ? d.tasques : []) })
      .catch(() => {})
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modelId])

  useEffect(() => { load() }, [load])

  const handleStarted = useCallback(() => { load(); onTasksChanged?.() }, [load, onTasksChanged])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <WorkPlan tasques={tasques} modelId={modelId} onRefresh={load} onOpenTab={onOpenTab} />
      <div style={{ borderTop: '0.5px solid var(--border)', paddingTop: '1.5rem' }}>
        <TaskTree modelId={modelId} modelTaskRows={modelTaskRows} tasks={tasques} onTaskStarted={handleStarted} onOpenTab={onOpenTab} />
      </div>
    </div>
  )
}
