import { Navigate } from 'react-router-dom'
import useAuthStore from '../store/authStore'

// Bloqueja l'accés a rutes privades si no hi ha token; redirigeix al login.
export default function PrivateRoute({ children }) {
  const token = useAuthStore((s) => s.token)
  if (!token) return <Navigate to="/login" replace />
  return children
}
