import { useState, useEffect, useCallback } from 'react'
import TaskTree from './TaskTree'

// B3/TL2 — Tab "Tasques" del Model Sheet: UNA sola llista unificada (TaskTree). Les targetes ja
// mostren les tasques existents amb el mateix detall que el WorkPlan del Dashboard (que es manté
// intacte allà), de manera que aquí no cal duplicar-lo. Seguim carregant el compositor del
// dashboard per alimentar el creuament estat/assignee de l'arbre (data.tasques).
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
    <TaskTree modelId={modelId} modelTaskRows={modelTaskRows} tasks={tasques} onTaskStarted={handleStarted} onOpenTab={onOpenTab} />
  )
}
