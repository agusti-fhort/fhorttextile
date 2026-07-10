import React, { useEffect, useState, lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
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
const CustomerDetail = lazy(() => import('./pages/CustomerDetail'))
const Products = lazy(() => import('./pages/Products'))
const ProductDetail = lazy(() => import('./pages/ProductDetail'))
const Quotes = lazy(() => import('./pages/Quotes'))
const QuoteDetail = lazy(() => import('./pages/QuoteDetail'))
const PaymentTerms = lazy(() => import('./pages/PaymentTerms'))
const Orders = lazy(() => import('./pages/Orders'))
const OrderDetail = lazy(() => import('./pages/OrderDetail'))
const WorkOrders = lazy(() => import('./pages/WorkOrders'))
const WorkOrderDetail = lazy(() => import('./pages/WorkOrderDetail'))
const DeliveryNotes = lazy(() => import('./pages/DeliveryNotes'))
const DeliveryNoteDetail = lazy(() => import('./pages/DeliveryNoteDetail'))
// TEMPORAL (esborrable) — banc de proves del sistema visual comercial unificat. Ruta /comercial/_kit.
const CommercialKitDemo = lazy(() => import('./pages/CommercialKitDemo'))
const FittingDetail = lazy(() => import('./pages/FittingDetail'))
const FittingConvocatoriaSheet = lazy(() => import('./pages/FittingConvocatoriaSheet'))
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
const TechSheetEntry = lazy(() => import('./pages/TechSheetEntry'))
const DissenyPlaceholder = lazy(() => import('./pages/DissenyPlaceholder'))
const ItemAuthoring = lazy(() => import('./pages/ItemAuthoring'))
const TimeTracking = lazy(() => import('./pages/TimeTracking'))
const UsersRoles = lazy(() => import('./pages/UsersRoles'))
const UserProfilePage = lazy(() => import('./pages/UserProfilePage'))
const CompanyCalendar = lazy(() => import('./pages/CompanyCalendar'))
const GeneralConfig = lazy(() => import('./pages/GeneralConfig'))
const Planning = lazy(() => import('./pages/Planning'))
const PlanningCalendar = lazy(() => import('./pages/PlanningCalendar'))
const ResetPassword = lazy(() => import('./pages/ResetPassword'))
const PaperKonvaPoc = lazy(() => import('./pages/PaperKonvaPoc'))

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

// Cutover .ftt (F8): /models/:id/fitxa ja no munta l'editor TechSheet (O2O). Resol o crea el
// document .ftt del model (ModelFitxer tipus TECHSHEET) i redirigeix a l'editor .ftt, conservant
// task_id. Així WorkPlan (tasca tech_sheet) i el tab Fitxa segueixen apuntant a /fitxa sense canvis.
function FttResolver() {
  const { id } = useParams()
  const [sp] = useSearchParams()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const taskId = sp.get('task_id')
  // null = resolent | { templates } = mostra el selector (blanc | plantilla de tenant)
  const [choose, setChoose] = useState(null)
  const API = import.meta.env.VITE_API_URL || ''
  const headers = { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('access_token')}` }

  // Crea el document (blanc si templateId és null) i navega a l'editor.
  const createDoc = async (templateId) => {
    try {
      const r = await fetch(`${API}/api/v1/models/${id}/ftt-document/`, {
        method: 'POST', headers, body: JSON.stringify(templateId ? { template_id: templateId } : {}),
      })
      if (r.ok) {
        const f = await r.json()
        navigate(`/models/${id}/ftt/${f.id}${taskId ? `?task_id=${taskId}` : ''}`, { replace: true })
        return
      }
    } catch { /* noop */ }
    navigate(`/models/${id}`, { replace: true })
  }

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      let fitxerId = null
      try {
        const r = await fetch(`${API}/api/v1/model-fitxers/?model=${id}&tipus=TECHSHEET&is_current=true&ordering=-data_pujada`, { headers })
        if (r.ok) { const d = await r.json(); const list = d.results || d || []; if (list.length) fitxerId = list[0].id }
      } catch { /* noop */ }
      if (cancelled) return
      if (fitxerId) {
        navigate(`/models/${id}/ftt/${fitxerId}${taskId ? `?task_id=${taskId}` : ''}`, { replace: true })
        return
      }
      // Sense document existent: si el tenant té plantilles, pregunta; si no, crea en blanc directe.
      let templates = []
      try {
        const r = await fetch(`${API}/api/v1/document-templates/`, { headers })
        if (r.ok) { const d = await r.json(); templates = d.results || d || [] }
      } catch { /* noop */ }
      if (cancelled) return
      if (templates.length) { setChoose({ templates }); return }
      createDoc(null)
    })()
    return () => { cancelled = true }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  if (choose) {
    return (
      <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
        <div style={{ background: 'var(--bg-card)', borderRadius: 12, padding: '1.4rem', maxWidth: 360, width: '90%', border: '1px solid var(--border)' }}>
          <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 600, marginBottom: 12, color: 'var(--text)' }}>{t('tech_sheet.new_doc_title')}</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <button type="button" onClick={() => createDoc(null)}
              style={{ textAlign: 'left', fontSize: 'var(--fs-body)', padding: '8px 10px', border: '1px solid var(--gold)', borderRadius: 6, background: 'transparent', color: 'var(--gold)', fontWeight: 600, cursor: 'pointer' }}>
              {t('tech_sheet.new_doc_blank')}
            </button>
            {choose.templates.map(tpl => (
              <button key={tpl.id} type="button" onClick={() => createDoc(tpl.id)}
                style={{ textAlign: 'left', fontSize: 'var(--fs-body)', padding: '8px 10px', border: '1px solid var(--border)', borderRadius: 6, background: 'var(--bg-card)', color: 'var(--text)', cursor: 'pointer' }}>
                {tpl.nom}
                {tpl.descripcio && <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)' }}>{tpl.descripcio}</div>}
              </button>
            ))}
          </div>
        </div>
      </div>
    )
  }
  return <div style={{ padding: 24, color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>…</div>
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
        {/* Fitxa tècnica: /fitxa ja no munta l'editor TechSheet; resol/crea el .ftt i redirigeix. */}
        <Route path="/models/:id/fitxa" element={
          <ProtectedRoute>
            <FttResolver />
          </ProtectedRoute>
        } />
        {/* Editor de document .ftt (ModelFitxer tipus TECHSHEET): mateix editor, font .ftt. */}
        <Route path="/models/:id/ftt/:fitxerId" element={
          <ProtectedRoute>
            <TechSheetEditor />
          </ProtectedRoute>
        } />
        <Route path="/" element={
          <ProtectedRoute>
            <Shell />
          </ProtectedRoute>
        }>
          <Route index element={<Dashboard />} />
          {/* D10 — porta-menú de la fitxa tècnica (S03b · P6): tria model → open-task → editor. */}
          <Route path="fitxa-tecnica" element={<TechSheetEntry />} />
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
          {/* P4 — fulla de convocatòria: pas intermedi llista → sessió, per a les sessions de grup. */}
          <Route path="fittings/convocatoria/:uuid" element={<FittingConvocatoriaSheet />} />
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
          <Route path="clients/:id" element={<CustomerDetail />} />
          {/* Mòdul Comercial Studio (B1) — mestre d'articles. Gate de tier = B5. */}
          <Route path="comercial/productes" element={<Products />} />
          <Route path="comercial/productes/:id" element={<ProductDetail />} />
          {/* Comercial Studio (B2) — ofertes (Quote). */}
          <Route path="comercial/ofertes" element={<Quotes />} />
          <Route path="comercial/ofertes/:id" element={<QuoteDetail />} />
          {/* Comercial (M4) — condicions de pagament (PaymentTerms). */}
          <Route path="comercial/condicions-pagament" element={<PaymentTerms />} />
          {/* Comercial (B3b) — comandes de venda (SalesOrder). */}
          <Route path="comercial/comandes" element={<Orders />} />
          <Route path="comercial/comandes/:id" element={<OrderDetail />} />
          {/* Comercial (B4a) — encàrrecs / ordres de treball (WorkOrder). */}
          <Route path="comercial/encarrecs" element={<WorkOrders />} />
          <Route path="comercial/encarrecs/:id" element={<WorkOrderDetail />} />
          {/* Comercial (B4c) — albarans (DeliveryNote). */}
          <Route path="comercial/albarans" element={<DeliveryNotes />} />
          <Route path="comercial/albarans/:id" element={<DeliveryNoteDetail />} />
          {/* TEMPORAL (esborrable) — banc de proves dels components del sistema visual comercial. */}
          <Route path="comercial/_kit" element={<CommercialKitDemo />} />
          <Route path="planificacio" element={<Planning />} />
          {/* Calendari propi (agenda) read-only: obert a qualsevol autenticat (scope per dades a
              calendar/events); NO gatejat per canPlan, a diferència de la gestió /planificacio. */}
          <Route path="planificacio/calendari" element={<PlanningCalendar />} />
          <Route path="temps" element={<TimeTracking />} />
          <Route path="poms" element={<POMs />} />
          <Route path="poms/grading" element={<GradingRuleSets />} />
          <Route path="size-library" element={<SizeLibrary />} />
          {/* Grup Disseny (F6): documents .ftt i patró DXF. Placeholders fins als sprints propis. */}
          <Route path="disseny/documents" element={<DissenyPlaceholder titleKey="nav.documents" icon="ti-file-text" />} />
          <Route path="disseny/patro-dxf" element={<DissenyPlaceholder titleKey="nav.patro_dxf" icon="ti-vector" />} />
          <Route path="disseny/poc-paper" element={<PaperKonvaPoc />} />
          <Route path="onboarding" element={<OnboardingWizard />} />
          <Route path="configuracio/general" element={<GeneralConfig />} />
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
