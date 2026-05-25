import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import useAuthStore from './store/auth'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Models from './pages/Models'
import Shell from './components/layout/Shell'

function ProtectedRoute({ children }) {
  const isAuthenticated = useAuthStore(s => s.isAuthenticated)
  return isAuthenticated ? children : <Navigate to="/login" replace />
}

export default function App() {
  const initAuth = useAuthStore(s => s.initAuth)

  useEffect(() => {
    initAuth()
  }, [])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={
          <ProtectedRoute>
            <Shell />
          </ProtectedRoute>
        }>
          <Route index element={<Dashboard />} />
          <Route path="models" element={<Models />} />
          <Route path="fitting" element={<Dashboard />} />
          <Route path="fittings" element={<Dashboard />} />
          <Route path="tasques" element={<Dashboard />} />
          <Route path="temps" element={<Dashboard />} />
          <Route path="fitxers" element={<Dashboard />} />
          <Route path="poms" element={<Dashboard />} />
          <Route path="ia" element={<Dashboard />} />
          <Route path="configuracio" element={<Dashboard />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
