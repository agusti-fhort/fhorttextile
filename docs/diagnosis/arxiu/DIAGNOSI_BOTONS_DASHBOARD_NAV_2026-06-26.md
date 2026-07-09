> ⚠️ SUPERADA 2026-07-07 — implementada (ModelMilestones onOpenTab + preventDefault). Consulta només com a històric.

# DIAGNOSI — Botons de navegació del DashboardTab

Data: 2026-06-26  
Branca: `dev`  
Abast: `DashboardTab.jsx` i subcomponents renderitzats directament dins del dashboard del model.

## FET — Inventari i veredicte

| Superficie | Element | Fitxer:linia | Que fa | Veredicte |
|---|---|---:|---|---|
| Q1 On soc | Bloquejos oberts | `frontend/src/components/model/DashboardTab.jsx:119` i `frontend/src/components/model/DashboardTab.jsx:159` | `goKanban` fa `navigate('/tasques/kanban')`; boto `type="button"`. | SEGUR. Navegacio interna React Router; no fa `onRefresh` post-navegacio; no depen de `?tab=` ni remuntatge. |
| Q1 Artefactes | Fitxa tecnica | `frontend/src/components/model/DashboardTab.jsx:181` | `onOpenTab('Fitxa tecnica')`. | SEGUR. Canvia estat intern de pestanya; no navega URL ni refresca. |
| Q1 Artefactes | Escalat | `frontend/src/components/model/DashboardTab.jsx:202` | `onOpenTab('Escalat')`. | SEGUR. Canvia estat intern de pestanya; no navega URL ni refresca. |
| Q1 Artefactes | Mesures/base | `frontend/src/components/model/DashboardTab.jsx:223` | `onOpenTab('Mesures')`. | SEGUR. Canvia estat intern de pestanya; no navega URL ni refresca. |
| Q4 Pla de treball | Play/Pause/Stop | `frontend/src/components/model/DashboardTab.jsx:130`; `frontend/src/components/model/WorkPlan.jsx:84`; `frontend/src/components/model/WorkPlan.jsx:87`; `frontend/src/components/model/WorkPlan.jsx:247`; `frontend/src/components/model/WorkPlan.jsx:249`; `frontend/src/components/model/WorkPlan.jsx:251` | TransportBtn fa `preventDefault` + `stopPropagation`; `playMine` fa `openTask`, `onOpenTab` si cal, `navigate(...)`; nomes fa `onRefresh` si no hi ha ruta. | SEGUR. Ja segueix el patro net de `82c42ff`; no reintrodueix transicio crua ni refresh post-navegacio. |
| Properes fites | Event amb `ev.link` | `frontend/src/components/model/DashboardTab.jsx:243`; `frontend/src/components/model/ModelMilestones.jsx:85` | Boto `type="button"` fa `ev.link && navigate(ev.link)` directament. | AFECTAT. Navega intern, pero no aplica `preventDefault`/`stopPropagation`; si `ev.link` apunta a `/models/:id?tab=...`, depen del remuntatge de `ModelSheet` i no pot cridar `onOpenTab`. |
| Estat tecnic | Desplegar/plegar | `frontend/src/components/model/DashboardTab.jsx:249` | `setShowTech(...)`. | N/A. No navega. |
| Q3 Avisos | Watchpoints consultius | `frontend/src/components/model/DashboardTab.jsx:282`; `frontend/src/components/model/WatchpointsPanel.jsx:52`; `frontend/src/components/model/WatchpointsPanel.jsx:63`; `frontend/src/components/model/WatchpointsPanel.jsx:90`; `frontend/src/components/model/WatchpointsPanel.jsx:91` | Al dashboard `editable={false}`; el toggle de resolts no navega; add/resolve/reopen nomes existeixen en mode editable. | N/A. No navega dins el dashboard. |
| Timeline | Files d'historial | `frontend/src/components/model/DashboardTab.jsx:290`; `frontend/src/components/model/ModelTimeline.jsx:139` | Renderitza `<div>` per event, sense `onClick` ni `navigate`. | N/A. No navega. |

## FET — Causa dels afectats

- `ModelMilestones` rep `navigate` des del dashboard (`frontend/src/components/model/DashboardTab.jsx:243`) i el crida directament amb `ev.link` (`frontend/src/components/model/ModelMilestones.jsx:85`).
- No hi ha `window.location` ni `<a href>` en `DashboardTab`, `WorkPlan`, `ModelMilestones`, `WatchpointsPanel` o `ModelTimeline` per aquests accessos; les navegacions detectades son React Router o canvi d'estat intern.
- El patro que va arreglar el Play combina tres peces: blindar l'event (`frontend/src/components/model/WorkPlan.jsx:87`), canviar pestanya interna abans de navegar quan toca (`frontend/src/components/model/WorkPlan.jsx:248`) i evitar `onRefresh` post-navegacio (`frontend/src/components/model/WorkPlan.jsx:247`-`frontend/src/components/model/WorkPlan.jsx:251`).

## 💡 PROPOSTA (aplicada en fase B)

- Corregir nomes `ModelMilestones`: passar-li `onOpenTab`, interpretar links del mateix model amb `?tab=...`, fer `preventDefault` + `stopPropagation`, cridar `onOpenTab(tab)` abans de `navigate(ev.link)`.
- No extreure helper global encara: hi ha un unic afectat fora del `WorkPlan`; extreure ara afegiria mes superficie que valor.
