import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import TenantsPage from './pages/TenantsPage'
import TenantDetailPage from './pages/TenantDetailPage'
import TenantFormPage from './pages/TenantFormPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        {/* Pàgines privades: layout amb sidebar + guarda d'autenticació */}
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/tenants" element={<TenantsPage />} />
          {/* Estàtica abans que dinàmica: /new no s'ha de capturar com a :codi */}
          <Route path="/tenants/new" element={<TenantFormPage />} />
          <Route path="/tenants/:codi" element={<TenantDetailPage />} />
          <Route path="/tenants/:codi/edit" element={<TenantFormPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
