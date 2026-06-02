import { useEffect, lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import useAuthStore from './store/auth'
import Login from './pages/Login'
import Shell from './components/layout/Shell'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const Models = lazy(() => import('./pages/Models'))
const POMs = lazy(() => import('./pages/POMs'))
const Tasks = lazy(() => import('./pages/Tasks'))
const SizeFittingList = lazy(() => import('./pages/SizeFittingList'))
const SizeFittingDetail = lazy(() => import('./pages/SizeFittingDetail'))
const FittingDetail = lazy(() => import('./pages/FittingDetail'))
const FittingSessionList = lazy(() => import('./pages/FittingSessionList'))
const FittingSessionNew = lazy(() => import('./pages/FittingSessionNew'))
const GradingRuleSets = lazy(() => import('./pages/GradingRuleSets'))
const SizeSystems = lazy(() => import('./pages/SizeSystems'))
const SizeLibrary = lazy(() => import('./pages/SizeLibrary'))
const GarmentPOMMapEditor = lazy(() => import('./pages/GarmentPOMMapEditor'))
const OnboardingWizard = lazy(() => import('./pages/OnboardingWizard'))
const NewSizeFitting = lazy(() => import('./pages/NewSizeFitting'))
const ModelWizard = lazy(() => import('./pages/ModelWizard'))
const ModelMeasurements = lazy(() => import('./pages/ModelMeasurements'))
const ModelFabric = lazy(() => import('./pages/ModelFabric'))
const ModelSheet = lazy(() => import('./pages/ModelSheet'))
const KanbanTasks = lazy(() => import('./pages/KanbanTasks'))
const TimeTracking = lazy(() => import('./pages/TimeTracking'))
const Alerts = lazy(() => import('./pages/Alerts'))
const Settings = lazy(() => import('./pages/Settings'))
const UsersRoles = lazy(() => import('./pages/UsersRoles'))
const UserProfilePage = lazy(() => import('./pages/UserProfilePage'))
const CompanyCalendar = lazy(() => import('./pages/CompanyCalendar'))
const Planning = lazy(() => import('./pages/Planning'))

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
      <Suspense fallback={<div className="p-8 text-gray-500">Carregant…</div>}>
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
          {/* 5B.6 — capa nova de sessions de fitting */}
          <Route path="fittings" element={<FittingSessionList />} />
          <Route path="fittings/new" element={<FittingSessionNew />} />
          <Route path="fittings/:id" element={<FittingDetail />} />
          <Route path="tasques" element={<Tasks />} />
          <Route path="tasques/catalog" element={<Tasks />} />
          <Route path="tasques/paquets" element={<Tasks />} />
          <Route path="tasques/kanban" element={<KanbanTasks />} />
          <Route path="planificacio" element={<Planning />} />
          <Route path="temps" element={<TimeTracking />} />
          <Route path="poms" element={<POMs />} />
          <Route path="poms/grading" element={<GradingRuleSets />} />
          <Route path="poms/sizes" element={<SizeSystems />} />
          <Route path="size-library" element={<SizeLibrary />} />
          <Route path="garment-pom-map" element={<GarmentPOMMapEditor />} />
          <Route path="garment-pom-map/:id" element={<GarmentPOMMapEditor />} />
          <Route path="onboarding" element={<OnboardingWizard />} />
          <Route path="configuracio/usuaris" element={<UsersRoles />} />
          <Route path="configuracio/calendari" element={<CompanyCalendar />} />
          <Route path="configuracio/garment-types" element={<Settings />} />
          <Route path="configuracio/size-systems" element={<Settings />} />
          <Route path="configuracio/grading" element={<Settings />} />
          <Route path="avisos" element={<Alerts />} />
          <Route path="configuracio" element={<Settings />} />
          <Route path="perfil" element={<UserProfilePage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
