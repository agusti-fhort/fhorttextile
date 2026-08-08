// LA NAVEGACIÓ DE LA CASA — font única de seccions, rutes i etiquetes.
//
// Vivia dins de `Sidebar.jsx`. En surt a T0.3 perquè el breadcrumb de la top bar
// (NORMA_LAYOUT §8b) n'ha de menjar també: `Topbar.jsx` tenia el seu propi PATH_TO_KEY
// amb 11 de les 58 rutes del router i, fora d'aquelles, el rètol requeia al títol de
// l'app — d'aquí el «Fhort Textile Tech › Fhort Textile Tech» de qualsevol captura d'un
// model. Amb dues llistes, el molla i el ressaltat del menú acabarien contradient-se.
//
// Fitxer propi i no `export` des del component: exportar una constant des d'un fitxer de
// component trenca el fast-refresh de Vite (react-refresh/only-export-components).
export const navGroups = [
  { sectionKey: 'nav.section_projectes', items: [
    { to: '/', labelKey: 'nav.dashboard', icon: 'ti-layout-dashboard' },
    { to: '/models', labelKey: 'nav.models', icon: 'ti-shirt' },
    { to: '/planificacio', labelKey: 'nav.planning', icon: 'ti-subtask', cap: 'plan' },
    // Jubilades les entrades "El meu calendari" (/planificacio/calendari) i "Temps" (/temps): la
    // planificació de l'executor viu ara al Gantt de la home (tab "Planificació"). Les <Route>
    // segueixen vives (accessibles per URL); només es retira l'entrada de menú.
    { to: '/fittings', labelKey: 'nav.fittings', icon: 'ti-ruler-2' },
  ]},
  { sectionKey: 'nav.section_config_tecnica', items: [
    // U2 — l'entrada apunta al Catàleg de peces (maqueta v4). `/garment-types` segueix VIVA per
    // URL: encara és l'única superfície que edita i esborra famílies i items, que la v4 no cobreix.
    { to: '/cataleg-peces', labelKey: 'nav.cataleg_peces', icon: 'ti-shirt' },
    { to: '/poms', labelKey: 'nav.poms_list', icon: 'ti-ruler-measure' },
    { to: '/size-library', labelKey: 'nav.size_library', icon: 'ti-books' },
    { to: '/poms/grading', labelKey: 'nav.grading', icon: 'ti-chart-dots' },
  ]},
  // Disseny — documents .ftt (fitxes/maquetació) i patró DXF. Consulta oberta (sense `cap`).
  { sectionKey: 'nav.section_disseny', items: [
    // D10 — porta-menú: tria model → open-task('tech_sheet') → editor (o consulta si l'allow-list ho nega).
    { to: '/fitxa-tecnica', labelKey: 'nav.tech_sheet', icon: 'ti-file-description' },
    { to: '/disseny/documents', labelKey: 'nav.documents', icon: 'ti-file-text' },
    // "Patró DXF" retirat (S5): era un placeholder buit que apuntava al motor de patrons.
    // El motor ja existeix i viu on ha de viure — al tab "Patró" de la fitxa del model,
    // perquè un patró pertany a UN model i no és una secció solta del menú.
  ]},
  // Estudi tècnic — gestió INTERNA del tenant (NO el backoffice futur de tots els tenants).
  // B3-M: Clients i Proveïdors s'han mogut a Comercial (mestres comercials). La secció queda
  // reservada (buida → auto-oculta) per als futurs interns previstos: Configuració de l'Estudi ·
  // Equip/usuaris · Catàleg de serveis/tasques. Les rutes /clients i /suppliers no canvien.
  { sectionKey: 'nav.section_technical_studio', items: [
  ]},
  // Comercial Studio — mestres comercials (Clients, Proveïdors, Productes) + documents (Ofertes).
  // El gate de tier del mòdul arriba a B5; de moment sense `cap` (visible; l'escriptura la
  // gateja CONFIGURE dins la pàgina).
  { sectionKey: 'nav.section_comercial', items: [
    { to: '/clients', labelKey: 'nav.clients', icon: 'ti-users-group' },
    { to: '/suppliers', labelKey: 'nav.suppliers', icon: 'ti-building-factory' },
    { to: '/comercial/productes', labelKey: 'nav.products', icon: 'ti-package' },
    { to: '/comercial/ofertes', labelKey: 'nav.quotes', icon: 'ti-file-invoice' },
    { to: '/comercial/comandes', labelKey: 'nav.orders', icon: 'ti-clipboard-check' },
    { to: '/comercial/encarrecs', labelKey: 'nav.workorders', icon: 'ti-briefcase' },
    { to: '/comercial/orfes', labelKey: 'nav.orphans', icon: 'ti-unlink' },
    { to: '/comercial/albarans', labelKey: 'nav.deliverynotes', icon: 'ti-truck-delivery' },
    { to: '/comercial/condicions-pagament', labelKey: 'nav.payment_terms', icon: 'ti-calendar-dollar' },
  ]},
  { sectionKey: 'nav.section_sistema', items: [
    { to: '/onboarding', labelKey: 'nav.onboarding', icon: 'ti-rocket', cap: 'onboarding' },
    { to: '/configuracio/general', labelKey: 'nav.configuracio_general', icon: 'ti-settings', cap: 'configure' },
    // P7 — RECURSOS: els Studios amb qui la Marca té pont obert. Doble gate ('brand_configure'):
    // només en un tenant 'marca' I amb CONFIGURE. Un Estudi no emet vincles, els rep.
    { to: '/recursos', labelKey: 'nav.recursos', icon: 'ti-affiliate', cap: 'brand_configure' },
    // P8 — ENCÀRRECS: què m'han assignat els Brands vinculats. Gate simètric del de Recursos
    // ('studio_configure'): només en un tenant 'estudi' I amb CONFIGURE.
    // La safata és feina de TALLER, no de configuració: el backend (EncarrecViewSet.list) només
    // demana EsEstudi, sense CONFIGURE. El menú s'alinea amb l'endpoint i es gateja amb `isStudio`
    // sol — així un operari d'estudi sense CONFIGURE veu la seva safata (abans amagada tot i poder
    // entrar-hi per URL). El cas 'studio_configure' es manté per a qui el necessiti.
    { to: '/encarrecs', labelKey: 'nav.encarrecs', icon: 'ti-inbox', cap: 'studio' },
    { to: '/configuracio/calendari', labelKey: 'nav.company_calendar', icon: 'ti-calendar-cog', cap: 'configure' },
    { to: '/configuracio/usuaris', labelKey: 'nav.users', icon: 'ti-users', cap: 'manage_users' },
    // G9 "consulta sí / edició no": catàleg de tasques consultable per a tothom (sense `cap`).
    { to: '/task-types', labelKey: 'nav.tasques_catalog', icon: 'ti-list-details' },
    { to: '/perfil', labelKey: 'nav.perfil', icon: 'ti-user' },
  ]},
]
