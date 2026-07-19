import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import TenantsPage from './pages/TenantsPage'
import TenantDetailPage from './pages/TenantDetailPage'
import TenantFormPage from './pages/TenantFormPage'
import ServeisPage from './pages/ServeisPage'
import FacturacioPage from './pages/FacturacioPage'
import SeedProfilesPage from './pages/SeedProfilesPage'
import LegalDocsPage from './pages/LegalDocsPage'
import ContractesPage from './pages/ContractesPage'
import ContractFormPage from './pages/ContractFormPage'
import ContractDetailPage from './pages/ContractDetailPage'

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
          <Route path="/serveis" element={<ServeisPage />} />
          <Route path="/perfils-sembra" element={<SeedProfilesPage />} />
          <Route path="/documents-legals" element={<LegalDocsPage />} />
          <Route path="/facturacio" element={<FacturacioPage />} />
          <Route path="/contractes" element={<ContractesPage />} />
          {/* Estàtica abans que dinàmica: /new no s'ha de capturar com a :id */}
          <Route path="/contractes/new" element={<ContractFormPage />} />
          <Route path="/contractes/:id" element={<ContractDetailPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
