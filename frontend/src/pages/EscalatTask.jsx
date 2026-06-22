import { useEffect } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { modelTasks } from '../api/endpoints'
import PropagatedEditor from './PropagatedEditor'

// PEÇA F — Superfície de TREBALL de l'escalat (tasca `scaling` "Escalat CAD").
// L'edició de la taula propagada NOMÉS és accessible des d'aquí (amb task_id), no des de la
// visualització: principi de temps (la tasca queda En curs en obrir-la via Kanban/WorkPlan i es
// Pausa en sortir, estil TechSheet). Fora de tasca, l'escalat és consulta read-only.
export default function EscalatTask() {
  const { id } = useParams()
  const [sp] = useSearchParams()
  const taskId = sp.get('task_id')
  const navigate = useNavigate()

  // Compta-temps: en desmuntar (sortir de la pantalla) es pausa la tasca, com TechSheetEditor.
  // L'obertura (En curs) la fa la navegació del Kanban/WorkPlan (fire-and-forget).
  useEffect(() => {
    return () => {
      if (taskId) modelTasks.transition(taskId, { to_status: 'Paused' }).catch(() => {})
    }
  }, [taskId])

  return <PropagatedEditor modelId={parseInt(id)} onClose={() => navigate(-1)} />
}
