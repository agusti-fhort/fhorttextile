import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import useAuthStore from './store/auth'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Models from './pages/Models'
import POMs from './pages/POMs'
import Tasques from './pages/Tasques'
import SizeFittingLlista from './pages/SizeFittingLlista'
import SizeFittingDetall from './pages/SizeFittingDetall'
import FittingDetall from './pages/FittingDetall'
import GradingRuleSets from './pages/GradingRuleSets'
import SizeSystems from './pages/SizeSystems'
import SizeLibrary from './pages/SizeLibrary'
import GarmentPOMMapEditor from './pages/GarmentPOMMapEditor'
import OnboardingWizard from './pages/OnboardingWizard'
import NouSizeFitting from './pages/NouSizeFitting'
import ModelWizard from './pages/ModelWizard'
import ModelMesures from './pages/ModelMesures'
import ModelTeixit from './pages/ModelTeixit'
import ModelFitxa from './pages/ModelFitxa'
import KanbanTasques from './pages/KanbanTasques'
import Temps from './pages/Temps'
import Avisos from './pages/Avisos'
import Configuracio from './pages/Configuracio'
import PerfilUsuari from './pages/PerfilUsuari'
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
          <Route path="models/nou" element={<ModelWizard />} />
          <Route path="models/nou-des-de-fitxer" element={<Navigate to="/models/nou" replace />} />
          <Route path="models/:id" element={<ModelFitxa />} />
          <Route path="models/:id/editar" element={<ModelWizard />} />
          <Route path="models/:id/mesures" element={<ModelMesures />} />
          <Route path="models/:id/teixit" element={<ModelTeixit />} />
          <Route path="models/:id/fitxers" element={<ModelFitxa defaultTab="Fitxers" />} />
          <Route path="models/:id/nou-sf" element={<NouSizeFitting />} />
          <Route path="fitting" element={<SizeFittingLlista />} />
          <Route path="fitting/:id" element={<SizeFittingDetall />} />
          <Route path="fitting/:sfId/fitting/:id" element={<FittingDetall />} />
          <Route path="fittings" element={<SizeFittingLlista />} />
          <Route path="tasques" element={<Tasques />} />
          <Route path="tasques/catalog" element={<Tasques />} />
          <Route path="tasques/paquets" element={<Tasques />} />
          <Route path="tasques/kanban" element={<KanbanTasques />} />
          <Route path="temps" element={<Temps />} />
          <Route path="poms" element={<POMs />} />
          <Route path="poms/grading" element={<GradingRuleSets />} />
          <Route path="poms/sizes" element={<SizeSystems />} />
          <Route path="size-library" element={<SizeLibrary />} />
          <Route path="garment-pom-map" element={<GarmentPOMMapEditor />} />
          <Route path="garment-pom-map/:id" element={<GarmentPOMMapEditor />} />
          <Route path="onboarding" element={<OnboardingWizard />} />
          <Route path="configuracio/garment-types" element={<Configuracio />} />
          <Route path="configuracio/size-systems" element={<Configuracio />} />
          <Route path="configuracio/grading" element={<Configuracio />} />
          <Route path="avisos" element={<Avisos />} />
          <Route path="configuracio" element={<Configuracio />} />
          <Route path="perfil" element={<PerfilUsuari />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
