import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import useAuthStore from './store/auth'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Models from './pages/Models'
import POMs from './pages/POMs'
import Tasks from './pages/Tasks'
import SizeFittingList from './pages/SizeFittingList'
import SizeFittingDetail from './pages/SizeFittingDetail'
import FittingDetail from './pages/FittingDetail'
import FittingSessionList from './pages/FittingSessionList'
import FittingSessionNew from './pages/FittingSessionNew'
import GradingRuleSets from './pages/GradingRuleSets'
import SizeSystems from './pages/SizeSystems'
import SizeLibrary from './pages/SizeLibrary'
import GarmentPOMMapEditor from './pages/GarmentPOMMapEditor'
import OnboardingWizard from './pages/OnboardingWizard'
import NewSizeFitting from './pages/NewSizeFitting'
import ModelWizard from './pages/ModelWizard'
import ModelMeasurements from './pages/ModelMeasurements'
import ModelFabric from './pages/ModelFabric'
import ModelSheet from './pages/ModelSheet'
import KanbanTasks from './pages/KanbanTasks'
import TimeTracking from './pages/TimeTracking'
import Alerts from './pages/Alerts'
import Settings from './pages/Settings'
import UserProfilePage from './pages/UserProfilePage'
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
          <Route path="models/:id" element={<ModelSheet />} />
          <Route path="models/:id/editar" element={<ModelWizard />} />
          <Route path="models/:id/mesures" element={<ModelMeasurements />} />
          <Route path="models/:id/teixit" element={<ModelFabric />} />
          <Route path="models/:id/fitxers" element={<ModelSheet defaultTab="Fitxers" />} />
          <Route path="models/:id/nou-sf" element={<NewSizeFitting />} />
          <Route path="fitting" element={<SizeFittingList />} />
          <Route path="fitting/:id" element={<SizeFittingDetail />} />
          {/* PENDENT A2: aquesta nidada es retira quan es reescrigui FittingDetail */}
          <Route path="fitting/:sfId/fitting/:id" element={<FittingDetail />} />
          {/* 5B.6 — capa nova de sessions de fitting */}
          <Route path="fittings" element={<FittingSessionList />} />
          <Route path="fittings/new" element={<FittingSessionNew />} />
          {/* PENDENT A2: FittingDetail es reescriu per consumir la sessió/graella */}
          <Route path="fittings/:id" element={<FittingDetail />} />
          <Route path="tasques" element={<Tasks />} />
          <Route path="tasques/catalog" element={<Tasks />} />
          <Route path="tasques/paquets" element={<Tasks />} />
          <Route path="tasques/kanban" element={<KanbanTasks />} />
          <Route path="temps" element={<TimeTracking />} />
          <Route path="poms" element={<POMs />} />
          <Route path="poms/grading" element={<GradingRuleSets />} />
          <Route path="poms/sizes" element={<SizeSystems />} />
          <Route path="size-library" element={<SizeLibrary />} />
          <Route path="garment-pom-map" element={<GarmentPOMMapEditor />} />
          <Route path="garment-pom-map/:id" element={<GarmentPOMMapEditor />} />
          <Route path="onboarding" element={<OnboardingWizard />} />
          <Route path="configuracio/garment-types" element={<Settings />} />
          <Route path="configuracio/size-systems" element={<Settings />} />
          <Route path="configuracio/grading" element={<Settings />} />
          <Route path="avisos" element={<Alerts />} />
          <Route path="configuracio" element={<Settings />} />
          <Route path="perfil" element={<UserProfilePage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
