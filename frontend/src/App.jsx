import React, { useEffect, lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useParams, useSearchParams } from 'react-router-dom'
import useAuthStore from './store/auth'
import Login from './pages/Login'
import Shell from './components/layout/Shell'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const Models = lazy(() => import('./pages/Models'))
const POMs = lazy(() => import('./pages/POMs'))
const TaskTypes = lazy(() => import('./pages/TaskTypes'))
const GarmentTypes = lazy(() => import('./pages/GarmentTypes'))
const Suppliers = lazy(() => import('./pages/Suppliers'))
const Customers = lazy(() => import('./pages/Customers'))
const FittingDetail = lazy(() => import('./pages/FittingDetail'))
const FittingSessionList = lazy(() => import('./pages/FittingSessionList'))
const FittingSessionNew = lazy(() => import('./pages/FittingSessionNew'))
const GradingRuleSets = lazy(() => import('./pages/GradingRuleSets'))
const SizeLibrary = lazy(() => import('./pages/SizeLibrary'))
// CODI MORT (jubilat al sprint tasca-POM): GarmentPOMMapEditor.jsx — editor de pertinença per
// família amb endpoints fantasma (pom-map/* → 404). Substituït per POMBrowser-assign (per item).
// Fitxer no esborrat; netejar en passada futura. (MeasurementTable.jsx ja esborrat a P1.)
const OnboardingWizard = lazy(() => import('./pages/OnboardingWizard'))
const ModelWizard = lazy(() => import('./pages/ModelWizard'))
const BulkImportWizard = lazy(() => import('./pages/BulkImportWizard'))
const ModelFabric = lazy(() => import('./pages/ModelFabric'))
const ModelSheet = lazy(() => import('./pages/ModelSheet'))
const TechSheetEditor = lazy(() => import('./pages/TechSheetEditor'))
const TechSheetTemplateEditor = lazy(() => import('./pages/TechSheetTemplateEditor'))
const ItemAuthoring = lazy(() => import('./pages/ItemAuthoring'))
const TimeTracking = lazy(() => import('./pages/TimeTracking'))
const UsersRoles = lazy(() => import('./pages/UsersRoles'))
const UserProfilePage = lazy(() => import('./pages/UserProfilePage'))
const CompanyCalendar = lazy(() => import('./pages/CompanyCalendar'))
const Planning = lazy(() => import('./pages/Planning'))
const PlanningCalendar = lazy(() => import('./pages/PlanningCalendar'))
const ResetPassword = lazy(() => import('./pages/ResetPassword'))

function ProtectedRoute({ children }) {
  const isAuthenticated = useAuthStore(s => s.isAuthenticated)
  return isAuthenticated ? children : <Navigate to="/login" replace />
}

// v2/J1: el Size Check antic es jubila. /size-check redirigeix al TAB Mesures del ModelSheet,
// conservant task_id (que el tab consumeix). Ja NO apunta a la pàgina standalone (jubilada).
function SizeCheckRedirect() {
  const { id } = useParams()
  const [sp] = useSearchParams()
  const taskId = sp.get('task_id')
  return <Navigate to={`/models/${id}?tab=Mesures${taskId ? `&task_id=${taskId}` : ''}`} replace />
}

// J1: la pàgina standalone de Mesures (/models/:id/mesures) JUBILADA. La superfície única és el tab
// Mesures del ModelSheet. Aquesta ruta queda només com a REDIRECT (enllaços/punts vells) → tab,
// preservant task_id si en porta. La pàgina ja no existeix; ningú hi torna.
function MesuresRedirect() {
  const { id } = useParams()
  const [sp] = useSearchParams()
  const taskId = sp.get('task_id')
  return <Navigate to={`/models/${id}?tab=Mesures${taskId ? `&task_id=${taskId}` : ''}`} replace />
}

class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, info) {
    console.error('AppErrorBoundary caught:', error, info);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          height: '100vh', gap: 16, fontFamily: 'IBM Plex Mono, monospace'
        }}>
          <div style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>
            S'ha produït un error inesperat.
          </div>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
            style={{
              background: 'var(--gold)', color: '#fff',
              border: 'none', borderRadius: 4,
              padding: '8px 20px', cursor: 'pointer',
              fontFamily: 'IBM Plex Mono, monospace', fontSize: 'var(--fs-body)'
            }}
          >
            Recarregar
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function App() {
  const initAuth = useAuthStore(s => s.initAuth)

  useEffect(() => {
    initAuth()
  }, [])

  return (
    <AppErrorBoundary>
    <BrowserRouter>
      <Suspense fallback={<div className="p-8 text-gray-500">Carregant…</div>}>
      <Routes>
        <Route path="/login" element={<Login />} />
        {/* Recuperació de contrasenya: pública, fora del guard (la persona no està autenticada). */}
        <Route path="/reset-password/:uid/:token" element={<ResetPassword />} />
        {/* Fitxa tècnica: editor full-screen FORA del Shell (sense sidebar), però protegit. */}
        <Route path="/models/:id/fitxa" element={
          <ProtectedRoute>
            <TechSheetEditor />
          </ProtectedRoute>
        } />
        {/* Editor de document .ftt (ModelFitxer tipus TECHSHEET): mateix editor, font .ftt. */}
        <Route path="/models/:id/ftt/:fitxerId" element={
          <ProtectedRoute>
            <TechSheetEditor />
          </ProtectedRoute>
        } />
        {/* Plantilla de fitxa per client (TS-3): mateix editor full-screen, FORA del Shell. */}
        <Route path="/clients/:id/plantilla" element={
          <ProtectedRoute>
            <TechSheetTemplateEditor />
          </ProtectedRoute>
        } />
        <Route path="/" element={
          <ProtectedRoute>
            <Shell />
          </ProtectedRoute>
        }>
          <Route index element={<Dashboard />} />
          <Route path="models" element={<Models />} />
          <Route path="models/nou" element={<ModelWizard />} />
          <Route path="models/importar-colleccio" element={<BulkImportWizard />} />
          <Route path="models/nou-des-de-fitxer" element={<Navigate to="/models/nou" replace />} />
          <Route path="models/:id" element={<ModelSheet />} />
          <Route path="models/:id/editar" element={<ModelWizard />} />
          {/* J1: pàgina standalone JUBILADA → redirect al tab Mesures del ModelSheet. */}
          <Route path="models/:id/mesures" element={<MesuresRedirect />} />
          {/* Escalat: l'edició viu DINS el ModelSheet (tab Escalat en mode edició). La ruta de tasca
              hi entra directament (defaultTab+autoEdit), sense pàgina externa ni overlay. */}
          <Route path="models/:id/escalat" element={<ModelSheet defaultTab="Escalat" autoEdit="Escalat" />} />
          <Route path="models/:id/teixit" element={<ModelFabric />} />
          <Route path="models/:id/fitxers" element={<ModelSheet defaultTab="Fitxers" />} />
          {/* v2: Size Check jubilat → redirigeix a l'edició nova de mesures (conserva task_id). */}
          <Route path="models/:id/size-check" element={<SizeCheckRedirect />} />
          {/* 5B.6 — capa de sessions de fitting (l'antiga SizeFitting es va jubilar al Pas 1 catàlegs) */}
          <Route path="fittings" element={<FittingSessionList />} />
          <Route path="fittings/new" element={<FittingSessionNew />} />
          <Route path="fittings/:id" element={<FittingDetail />} />
          {/* Sprint 5: pàgina Kanban global jubilada → el board per-model viu al Dashboard (/).
              Bloc 3: la pàgina-llistat residual /tasques (Tasks.jsx) també jubilada (endpoint
              model-tasques/ inexistent → 404); deep-links cauen al catch-all *→/. */}
          <Route path="task-types" element={<TaskTypes />} />
          <Route path="garment-types" element={<GarmentTypes />} />
          {/* Autoria d'Item (Llibreria d'Items B3): DINS el Shell (àrea de contingut).
              Crear (des d'un garment type) i obrir-existent (un dels esquelets). */}
          <Route path="garment-type-items/nou/:typeId" element={<ItemAuthoring />} />
          <Route path="garment-type-items/:itemId/editar" element={<ItemAuthoring />} />
          <Route path="suppliers" element={<Suppliers />} />
          <Route path="clients" element={<Customers />} />
          <Route path="planificacio" element={<Planning />} />
          {/* Calendari propi (agenda) read-only: obert a qualsevol autenticat (scope per dades a
              calendar/events); NO gatejat per canPlan, a diferència de la gestió /planificacio. */}
          <Route path="planificacio/calendari" element={<PlanningCalendar />} />
          <Route path="temps" element={<TimeTracking />} />
          <Route path="poms" element={<POMs />} />
          <Route path="poms/grading" element={<GradingRuleSets />} />
          <Route path="size-library" element={<SizeLibrary />} />
          <Route path="onboarding" element={<OnboardingWizard />} />
          <Route path="configuracio/usuaris" element={<UsersRoles />} />
          <Route path="configuracio/calendari" element={<CompanyCalendar />} />
          {/* Bloc 2 Peça 3: Registre d'activitat retirat com a ruta standalone → ara tab de Planning
              (oversight, gate canPlan). Deep-links a /registre-activitat cauen al catch-all → /. */}
          <Route path="perfil" element={<UserProfilePage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </Suspense>
    </BrowserRouter>
    </AppErrorBoundary>
  )
}
