import { Navigate, Outlet } from 'react-router-dom'
import useAuthStore from '../store/authStore'
import Sidebar from './Sidebar'

// Layout de les pàgines privades: guarda d'autenticació + sidebar fix + contingut.
// El sidebar és position:fixed (240px), així que el contingut es desplaça amb margin-left.
export default function Layout() {
  const token = useAuthStore((s) => s.token)
  if (!token) return <Navigate to="/login" replace />

  return (
    <>
      <Sidebar />
      <main style={{ marginLeft: 240, minWidth: 0, minHeight: '100vh', background: 'var(--bg-main)' }}>
        <Outlet />
      </main>
    </>
  )
}
