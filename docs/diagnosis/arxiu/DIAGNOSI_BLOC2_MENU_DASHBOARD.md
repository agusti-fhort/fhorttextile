> ⚠️ SUPERADA 2026-07-07 — implementada (trosseig G8: breadcrumb + claus + jubilació /tasques). Consulta només com a històric.

# DIAGNOSI BLOC 2 — Menú + Dashboard (READ-ONLY)

**Data:** 2026-06-26 · **Branca:** `dev` · **Patró:** A (READ-ONLY absolut, 0 codi, 0 push)
**Objectiu:** portar el codi real exacte dels 5 ítems del bloc 2 amb `fitxer:línia`, perquè el CTO
trossegi en peces d'1 commit sense obrir cap fitxer. **FET** = estat actual verificat · **💡PROPOSTA** =
no n'hi ha (read-only) · **OBERT** = no determinable en read-only.

> ⚠️ **Tres coses del bloc 2 JA estan fetes** (les sessions concurrents han avançat). Cal saber-ho
> abans de trossejar:
> 1. El **tab "Calendari" de Planning ja està jubilat** (no és a `GOV_TABS`) — §A3.
> 2. **TaskTypes ja és READ-ONLY** (cap control de mutació) — §A4.
> 3. El modal d'usuaris **ja llegeix el catàleg real** (no hardcoded) — §A5.

---

## A1 — `navGroups` del Sidebar  ([Sidebar.jsx](frontend/src/components/layout/Sidebar.jsx))

**`navGroups` complet ([Sidebar.jsx:45-80](frontend/src/components/layout/Sidebar.jsx#L45-L80)) — 4 seccions (no 3):**

### Secció PROJECTES (`nav.section_projectes`, [:46](frontend/src/components/layout/Sidebar.jsx#L46))
| Ítem | `to` | `labelKey` | `cap` (gate) | línia |
|---|---|---|---|---|
| Dashboard | `/` | `nav.dashboard` | — (cap) | [:47](frontend/src/components/layout/Sidebar.jsx#L47) |
| Models | `/models` | `nav.models` | — | [:48](frontend/src/components/layout/Sidebar.jsx#L48) |
| **Registre d'activitat** | `/registre-activitat` | `nav.registre_activitat` | — | [:49](frontend/src/components/layout/Sidebar.jsx#L49) |
| Planificació | `/planificacio` | `nav.planning` | **`plan`** | [:50](frontend/src/components/layout/Sidebar.jsx#L50) |
| El meu calendari | `/planificacio/calendari` | `nav.my_calendar` | **`execute`** | [:57](frontend/src/components/layout/Sidebar.jsx#L57) |
| Temps | `/temps` | `nav.temps` | — | [:58](frontend/src/components/layout/Sidebar.jsx#L58) |
| Fittings | `/fittings` | `nav.fittings` | — | [:59](frontend/src/components/layout/Sidebar.jsx#L59) |

### Secció CONFIG TÈCNICA (`nav.section_config_tecnica`, [:61](frontend/src/components/layout/Sidebar.jsx#L61))
| Ítem | `to` | `labelKey` | `cap` | línia |
|---|---|---|---|---|
| Garment Types | `/garment-types` | `nav.garment_types` | — | [:62](frontend/src/components/layout/Sidebar.jsx#L62) |
| POMs | `/poms` | `nav.poms_list` | — | [:63](frontend/src/components/layout/Sidebar.jsx#L63) |
| Size Library | `/size-library` | `nav.size_library` | — | [:64](frontend/src/components/layout/Sidebar.jsx#L64) |
| Grading | `/poms/grading` | `nav.grading` | — | [:65](frontend/src/components/layout/Sidebar.jsx#L65) |
| **Catàleg de tasques** | `/task-types` | `nav.tasques_catalog` | — | [:66](frontend/src/components/layout/Sidebar.jsx#L66) |

### Secció ESTUDI TÈCNIC (`nav.section_technical_studio`, [:70](frontend/src/components/layout/Sidebar.jsx#L70))
| Ítem | `to` | `labelKey` | `cap` | línia |
|---|---|---|---|---|
| Clients | `/clients` | `nav.clients` | — | [:71](frontend/src/components/layout/Sidebar.jsx#L71) |
| Suppliers | `/suppliers` | `nav.suppliers` | — | [:72](frontend/src/components/layout/Sidebar.jsx#L72) |

### Secció SISTEMA (`nav.section_sistema`, [:74](frontend/src/components/layout/Sidebar.jsx#L74))
| Ítem | `to` | `labelKey` | `cap` | línia |
|---|---|---|---|---|
| Onboarding | `/onboarding` | `nav.onboarding` | **`onboarding`** (pct<100) | [:75](frontend/src/components/layout/Sidebar.jsx#L75) |
| Calendari d'empresa | `/configuracio/calendari` | `nav.company_calendar` | **`configure`** | [:76](frontend/src/components/layout/Sidebar.jsx#L76) |
| Usuaris | `/configuracio/usuaris` | `nav.users` | **`manage_users`** | [:77](frontend/src/components/layout/Sidebar.jsx#L77) |
| Perfil | `/perfil` | `nav.perfil` | — | [:78](frontend/src/components/layout/Sidebar.jsx#L78) |

**Capabilities llegides de l'auth store ([:200-203](frontend/src/components/layout/Sidebar.jsx#L200-L203)):**
```js
canManageUsers = capabilities.includes('manage_users')           // :200
canConfigure   = capabilities.includes('configure')              // :201
canPlan        = capabilities.some(c => c==='define_tasks' || c==='configure')   // :202
canExecute     = capabilities.includes('execute_tasks')          // :203
```
**Mapa de gates** (`allowed()`, [:234-243](frontend/src/components/layout/Sidebar.jsx#L234-L243)): `plan→canPlan` · `execute→canExecute` ·
`configure→canConfigure` · `manage_users→canManageUsers` · `onboarding→onboardingPct<100` ·
**default→`true`** (sense `cap` = sempre visible). Filtre de secció: `.filter(g => g.items.length>0)`
([:246](frontend/src/components/layout/Sidebar.jsx#L246)) → una secció es mostra si ≥1 ítem passa.

**FET — resposta directa a "quina capability gate-eja CONFIG TÈCNICA i quina SISTEMA":**
- **CONFIG TÈCNICA: CAP.** Cap dels 5 ítems té `cap` → la secció és sempre visible a tot autenticat
  (inclòs `/task-types`, **sense gate**).
- **SISTEMA: no es gate-eja com a secció**; els ítems es gate-egen individualment (`configure` el
  calendari, `manage_users` els usuaris, `onboarding%<100` l'onboarding). **`/perfil` no té `cap`** →
  sempre visible → la secció SISTEMA sempre apareix.

**Ubicació exacta dels ítems demanats (FET):**
- **Dashboard** → PROJECTES, `to:'/'`, `nav.dashboard`, sense gate ([:47](frontend/src/components/layout/Sidebar.jsx#L47)).
- **/task-types** → CONFIG TÈCNICA, `nav.tasques_catalog`, **sense gate** ([:66](frontend/src/components/layout/Sidebar.jsx#L66)).
- **Registre d'activitat** → SÍ és entrada de menú, PROJECTES, sense gate ([:49](frontend/src/components/layout/Sidebar.jsx#L49)).
- **Fittings** → PROJECTES, sense gate ([:59](frontend/src/components/layout/Sidebar.jsx#L59)). **El meu calendari** → PROJECTES, gate `execute`
  ([:57](frontend/src/components/layout/Sidebar.jsx#L57)). **Temps** → PROJECTES, sense gate ([:58](frontend/src/components/layout/Sidebar.jsx#L58)).

---

## A2 — Sincronia de 3 puntes (rutes · breadcrumb)

**Rutes a [App.jsx](frontend/src/App.jsx) (tots dins el shell `ProtectedRoute`):**
| Ruta | Element / component | línia |
|---|---|---|
| `index` (`/`) | `<Dashboard />` | [:139](frontend/src/App.jsx#L139) |
| `task-types` | `<TaskTypes />` | [:161](frontend/src/App.jsx#L161) |
| `planificacio` | `<Planning />` | [:169](frontend/src/App.jsx#L169) |
| `planificacio/calendari` | `<PlanningCalendar />` (no gatejat; scope per dades) | [:172](frontend/src/App.jsx#L172) |
| `registre-activitat` | `<RegistreActivitat />` | [:180](frontend/src/App.jsx#L180) |

**Redireccions legacy properes (context):** `models/:id/mesures`→`MesuresRedirect` ([:147](frontend/src/App.jsx#L147)),
`models/:id/size-check`→`SizeCheckRedirect` ([:154](frontend/src/App.jsx#L154)), Kanban global jubilat (comentari [:160](frontend/src/App.jsx#L160), sense
ruta). Catch-all `*`→`/` ([:183](frontend/src/App.jsx#L183)).

**Breadcrumb `PATH_TO_KEY` ([Topbar.jsx:8-23](frontend/src/components/layout/Topbar.jsx#L8-L23)):**
```
'/'→nav.dashboard · '/models'→nav.models · '/models/nou'→nav.models_new ·
'/models/nou-des-de-fitxer'→nav.models_from_file · '/fittings'→nav.fittings ·
'/tasques'→nav.tasques · '/task-types'→nav.tasques_catalog · '/tasques/kanban'→nav.kanban ·
'/temps'→nav.temps · '/fitxers'→nav.fitxers · '/poms'→nav.poms · '/poms/grading'→nav.grading ·
'/ia'→nav.ia · '/perfil'→nav.perfil
```
Fallback si no hi és: `title = t('app.title')` ([Topbar.jsx:29-30](frontend/src/components/layout/Topbar.jsx#L29-L30)).

**Desajustos JA EXISTENTS (FET — a tenir en compte):**
- ❌ **`/registre-activitat`** té ruta ([App.jsx:180](frontend/src/App.jsx#L180)) + entrada de menú ([Sidebar.jsx:49](frontend/src/components/layout/Sidebar.jsx#L49)) però **NO és a
  `PATH_TO_KEY`** → el breadcrumb cau a `app.title`.
- ❌ **`/planificacio`** té ruta + menú però **NO és a `PATH_TO_KEY`** → breadcrumb = `app.title`.
- ⚠️ `PATH_TO_KEY` té entrades **sense ruta viva**: `/tasques/kanban` (jubilat, [App.jsx:160](frontend/src/App.jsx#L160)), `/ia` i
  `/fitxers` (no hi ha `<Route>`). Claus mortes.
- ✅ `/task-types` i `/temps` quadren (ruta + PATH_TO_KEY + sidebar).

---

## A3 — `Planning.jsx` (estructura de tabs)  ([Planning.jsx](frontend/src/pages/Planning.jsx))

**Declaració:** array `GOV_TABS` + render condicional (NO sub-rutes, NO switch).
```js
const GOV_TABS = ['dashboard','planificacio','assignacio','calendari_projecte','informes']   // :440
```
**Tabs ARA, en ordre ([Planning.jsx:440](frontend/src/pages/Planning.jsx#L440), render [:480-484](frontend/src/pages/Planning.jsx#L480-L484)):**
| # | clau | component renderitzat | línia |
|---|---|---|---|
| 1 | `dashboard` | `<DashboardGovPanel me={me} />` | [:480](frontend/src/pages/Planning.jsx#L480) |
| 2 | `planificacio` | `<PlanificacioPanel mode="pending" />` | [:481](frontend/src/pages/Planning.jsx#L481) |
| 3 | `assignacio` | `<PlanificacioPanel mode="assigned" />` | [:482](frontend/src/pages/Planning.jsx#L482) |
| 4 | `calendari_projecte` | `<ProjectGantt t={t} />` (Gantt model/dies) | [:483](frontend/src/pages/Planning.jsx#L483) |
| 5 | `informes` | `<InformesPanel me={me} />` | [:484](frontend/src/pages/Planning.jsx#L484) |

Gating de pantalla: `canPlan = define_tasks||configure` ([:445](frontend/src/pages/Planning.jsx#L445)); sense → pantalla bloquejada ([:449-454](frontend/src/pages/Planning.jsx#L449-L454)).
Labels via `t('planning.tabs.<clau>')` ([:475](frontend/src/pages/Planning.jsx#L475)).

**Tab "Calendari" a treure — FET, JA NO HI ÉS:** `GOV_TABS` **no conté `'calendari'`**. El tab antic
(PlanningCalendar incrustat) **ja s'ha jubilat**; només en queda el comentari ([Planning.jsx:437-438](frontend/src/pages/Planning.jsx#L437-L438)) i
**no hi ha cap `import PlanningCalendar` ni render** dins Planning.jsx (grep net). El calendari de
l'executor segueix viu només via ruta `/planificacio/calendari` ([App.jsx:172](frontend/src/App.jsx#L172)) + entrada de menú del
tècnic (Sidebar `cap:'execute'`, [:57](frontend/src/components/layout/Sidebar.jsx#L57)).
⚠️ **Residu:** la clau i18n `planning.tabs.calendari` encara existeix als 3 JSON (§A6) — òrfena.

**Registre d'activitat — on viu ARA (FET):** és **pàgina/ruta pròpia**, NO un tab.
- Component: `RegistreActivitat` ([pages/RegistreActivitat.jsx](frontend/src/pages/RegistreActivitat.jsx)), ruta `/registre-activitat` ([App.jsx:180](frontend/src/App.jsx#L180)),
  entrada de menú PROJECTES ([Sidebar.jsx:49](frontend/src/components/layout/Sidebar.jsx#L49)).
- **Endpoint principal:** `GET /api/v1/registre-activitat/?<params>` ([RegistreActivitat.jsx:60](frontend/src/pages/RegistreActivitat.jsx#L60)).
  Auxiliars: `GET /api/v1/users/` (filtre de tècnics, [:45](frontend/src/pages/RegistreActivitat.jsx#L45)) i `taskTypes` (filtre per tipus, import
  [:4](frontend/src/pages/RegistreActivitat.jsx#L4)). Paginació `PAGE_SIZE=25`, filtres `period`/`tecnicId`/`taskTypeId`.
- → Si el bloc 2 vol moure-ho a un tab de Planning, el component `RegistreActivitat` és **reusable
  tal qual** (autocontingut: fa els seus propis fetch). Caldria crear la clau `planning.tabs.<nova>`
  (§A6).

---

## A4 — Vista de TaskTypes (read-only)  ([TaskTypes.jsx](frontend/src/pages/TaskTypes.jsx))

- **Component i ruta (FET):** `TaskTypes` ([pages/TaskTypes.jsx:12](frontend/src/pages/TaskTypes.jsx#L12)), ruta `/task-types`→`<TaskTypes />`
  ([App.jsx:161](frontend/src/App.jsx#L161)). *(NO és `Tasks.jsx`; `Tasks.jsx` és la ruta `/tasques`, una altra pàgina.)*
- **Controls de mutació: NO N'HI HA — JA ÉS READ-ONLY (FET).** Comentari explícit ([TaskTypes.jsx:7-9](frontend/src/pages/TaskTypes.jsx#L7-L9)):
  *"Catàleg de TaskType — READ-ONLY … el tenant NO l'edita … Backend: TaskTypeViewSet
  (ReadOnlyModelViewSet); escriure-hi retorna 405."* No hi ha botons/handlers de crear/editar/esborrar;
  el render és només `<Table columns data>` ([:56](frontend/src/pages/TaskTypes.jsx#L56)). **→ no queda res a treure.**
- **Lectura del catàleg (GET):** `taskTypes.list({ ordering: 'default_order' })` ([TaskTypes.jsx:21](frontend/src/pages/TaskTypes.jsx#L21)) →
  `GET /api/v1/task-types/` ([endpoints.js:182](frontend/src/api/endpoints.js#L182)). Columnes: `code · name · default_order · active`
  ([:29-43](frontend/src/pages/TaskTypes.jsx#L29-L43)).
- ℹ️ L'endpoint `taskTypes` SÍ exposa `create/update/remove` al client ([endpoints.js:184-186](frontend/src/api/endpoints.js#L184-L186)) però **cap
  pantalla els crida** i el backend és ReadOnly (405). Mètodes morts al client.

---

## A5 — Modal d'usuaris (UsersRoles)  ([UsersRoles.jsx](frontend/src/pages/UsersRoles.jsx))

- **Pantalla/ruta:** `UsersRoles`, `/configuracio/usuaris` ([App.jsx:178](frontend/src/App.jsx#L178)), menú SISTEMA gate `manage_users`.
- **Modals i graella de "tasques permeses" (fitxer:línia):**
  - Matriu principal (capçalera de tasques + toggles per usuari): capçalera `taskTypes.map`
    ([UsersRoles.jsx:235](frontend/src/pages/UsersRoles.jsx#L235), [:252](frontend/src/pages/UsersRoles.jsx#L252)), cel·les per usuari ([:286](frontend/src/pages/UsersRoles.jsx#L286)).
  - `UserEditModal` (rol + tasques + nom + color), graella de tasques `taskTypes.map` ([:663](frontend/src/pages/UsersRoles.jsx#L663)); definició
    del component [:564](frontend/src/pages/UsersRoles.jsx#L564).
  - `NewUserModal` [:484](frontend/src/pages/UsersRoles.jsx#L484) · `BulkBar` (selector de tasca en bloc) `taskTypes.map` [:464](frontend/src/pages/UsersRoles.jsx#L464).
- **CLAU — fetch al catàleg vs hardcoded (FET): és FETCH, NO hardcoded.**
  ```js
  taskTypesApi.list()                                              // :94  → GET /api/v1/task-types/
    .then(res => { const tts = (res.data?.results ?? res.data ?? [])
                     .filter(tt => tt.active !== false)            // :96  només actius
                     .sort((a,b)=>(a.default_order??0)-(b.default_order??0))  // :97
                   setTaskTypes(tts) })                            // :98
  ```
  Les columnes de tasques surten d'aquest estat `taskTypes` (dinàmic). **NO hi ha cap llista
  hardcoded de tipus de tasca.**
  - *Matís:* SÍ hi ha hardcoded `CAPS` (capabilities, [:10](frontend/src/pages/UsersRoles.jsx#L10)) i `ROLES` ([:12](frontend/src/pages/UsersRoles.jsx#L12)) — però són
    **capacitats i rols, no tipus de tasca**; no afecten les columnes de tasques.
- **Catàleg avui i recompte a `fhort` (FET):** `GET /api/v1/task-types/` (`taskTypes.list`,
  [endpoints.js:182](frontend/src/api/endpoints.js#L182)). Al tenant **fhort: 14 TaskType, tots actius** → la matriu pinta **14 columnes**
  (coincideix amb els "14 reals"). Codis (per `default_order`): `design_review(5) · design_clarify(6)
  · pattern_digit(10) · pattern_cad(20) · pattern_hand(30) · pom(40) · size_check(45) · grading(46) ·
  tech_sheet(50) · pattern_review(55) · bom(70) · scaling(81) · marking(82) · Audit(90)`.

---

## A6 — i18n (rètols afectats, paritat ca/en/es)

**Claus de menú existents (FET, paritat ✅ als 3 locales):**
| Clau | ca | en | es |
|---|---|---|---|
| `nav.dashboard` | Dashboard | Dashboard | Dashboard |
| `nav.registre_activitat` | Registre d'activitat | Activity log | Registro de actividad |
| `nav.tasques_catalog` | Catàleg de tasques | Task catalog | Catálogo de tareas |
| `nav.section_projectes` | Projectes | Projects | Proyectos |
| `nav.section_config_tecnica` | Configuració tècnica | Technical config | Configuración técnica |
| `nav.section_technical_studio` | Estudi tècnic | Technical Studio | Estudio técnico |
| `nav.section_sistema` | Sistema | System | Sistema |
| `nav.my_calendar` | El meu calendari | My calendar | Mi calendario |

**`planning.tabs.*` (FET, paritat ✅ — 6 claus als 3 locales):**
| clau | ca | en | es |
|---|---|---|---|
| `dashboard` | Tauler | Dashboard | Panel |
| `planificacio` | Planificació | Planning | Planificación |
| `assignacio` | Assignació | Assignment | Asignación |
| `calendari` | Calendari | Calendar | Calendario |
| `calendari_projecte` | Calendari de projecte | Project calendar | Calendario de proyecto |
| `informes` | Informes | Reports | Informes |

**Per al CTO (FETS, sense proposta):**
- **QUÈ renombrar a "Desenvolupament":** la clau és `nav.dashboard` (valor actual "Dashboard" als 3).
  Existeix i té paritat → renombrar els 3 valors. *(El títol del tab intern de Planning seria
  `planning.tabs.dashboard` = "Tauler/Dashboard/Panel", clau separada.)*
- **Clau ÒRFENA:** `planning.tabs.calendari` (3 locales) ja no es renderitza (tab jubilat, §A3) →
  candidata a retirar.
- **QUÈ falta crear (tab nou):** si Registre d'activitat passa a tab de Planning, no existeix cap
  `planning.tabs.<registre>` → caldria crear-la (el rètol de menú `nav.registre_activitat` ja existeix
  i té paritat, reutilitzable com a base de traducció).

---

## Punts OBERTS (no determinables en read-only)
- Cap. Tots els fets demanats (A1–A6) s'han pogut resoldre amb codi + BD. Les úniques decisions
  pendents (renombrar Dashboard→Desenvolupament, moure Registre a tab, retirar clau òrfena) són de
  **disseny del CTO**, no de diagnòstic.

### Resum de "ja fet" que canvia el trossejat
1. Tab `calendari` de Planning: **jubilat** (§A3) — no cal "treure'l", sí retirar la clau i18n òrfena.
2. TaskTypes: **read-only** (§A4) — no cal treure mutacions.
3. Modal usuaris: **catàleg dinàmic de 14** (§A5) — no cal des-hardcodejar.
4. Desajustos de breadcrumb preexistents: `/registre-activitat` i `/planificacio` sense `PATH_TO_KEY`
   (§A2) — peça neta d'1 commit.
