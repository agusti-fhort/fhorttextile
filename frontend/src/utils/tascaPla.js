// M2 · CODA — LA LÒGICA D'UNA TARGETA DE TASCA DEL PLA, en un sol lloc.
//
// El Dashboard pinta les tasques de DUES maneres: la targeta gran (models sense voltes, pla
// llarg) i la COMPACTA de la maqueta (dins d'un contenidor de ronda). Per llei de la casa, el
// que es duplica és **la capa de PRESENTACIÓ** —cada targeta té el seu JSX i les seves mides— i
// el que es comparteix és **el mòdul de LÒGICA**, que és aquest. No s'ha extret cap component:
// `TaskCard` es queda on era i amb el mateix JSX, i només canvia d'on li arriben aquests mapes.
//
// Aquí no hi ha res de pell: ni colors, ni mides, ni radis. Només les quatre preguntes que
// totes dues targetes han de respondre igual, perquè si divergissin dues superfícies dirien
// coses diferents de la mateixa tasca.

/** `task_type.code` → icona Tabler (outline). Design system; no hi havia mapa compartit. */
export const TASK_ICON = {
  pattern_digit: 'ti-vector', pattern_cad: 'ti-vector-bezier', pattern_hand: 'ti-pencil',
  pattern_review: 'ti-eye-check', pom: 'ti-ruler-2', size_check: 'ti-ruler-measure',
  tech_sheet: 'ti-file-text', bom: 'ti-list-details', scaling: 'ti-resize',
  marking: 'ti-layout-grid', Audit: 'ti-checklist',
}

/** status → variant del `Badge` del design system (mateix criteri que el dashboard F1). */
export const STATUS_VARIANT = { Done: 'ok', InProgress: 'gold', Paused: 'warn', Pending: 'gray' }

// Transport actiu per estat. Aquest és avui l'ÚNIC transport de la casa: l'ACTIONS de
// KanbanTasks que aquest mapa emmirallava ja no existeix (la pàgina Kanban global es va jubilar
// a fc98cab6), i cap altra superfície pinta play/pause/stop. No hi ha res amb què sincronitzar.
//
// play = Pending/Paused/Done (start/resume/reopen); en InProgress només es reactiva si hi ha eina
// per navegar-hi. pause = InProgress (només té sentit sobre feina en curs).
// stop = InProgress i PAUSED. A Paused no és una transició nova —`Paused → Done` segueix
// prohibida a la màquina d'estats (decisió Agus: NO es toca)— sinó un GEST: play+stop encadenat
// (`handleStop`). Pending NO en té: tancar una tasca mai començada és «cancel·lar», una altra
// cosa que aquell sprint no va decidir.
export const TRANSPORT = {
  Pending:    { play: true,  pause: false, stop: false },
  Paused:     { play: true,  pause: false, stop: true  },
  InProgress: { play: false, pause: true,  stop: true  },
  Done:       { play: true,  pause: false, stop: false },
}

// Fora d'encàrrec / fora de recepta: extra marcat al backend amb `off_recipe=True` (B4a).
// Activa el filet grana. NOMÉS marca.
//
// 🚨 **`origen === 'ad_hoc'` NO hi entra, i el motiu és una llei nova** (M2). Des d'M1-bis
// **totes** les tasques que crea `obrir_ronda` neixen `ad_hoc` A POSTA —és el que les deixa
// conviure amb la `prevista` del mateix tipus sota la unique parcial (`services_r`, nota de la
// funció)—, o sigui que a partir de la R2 el joc REPLICAT sencer hi entrava i cada volta nova es
// pintava amb el filet grana i el rètol «fora d'encàrrec». Mesurat a la QA de pantalla del banc.
//
// I no és una excepció inventada: és el MATEIX raonament que el backend ja va escriure a
// `_NO_ES_REPLICA` («l'únic camp que literalment vol dir *això no és de la recepta* és
// `off_recipe`»), i és el que les dues superfícies comercials —`WorkOrderDetail`, `OrderDetail`—
// ja feien servir soles.
export function isOutOfCharge(task) { return task?.off_recipe === true }

/**
 * Les quatre lectures que una targeta de tasca fa abans de pintar-se, siguin quines siguin les
 * seves mides. Cap d'elles és de pell.
 *
 *   · `transport`  — quins dels tres botons tenen sentit per a aquest estat
 *   · `playActive` — el Play és el gest que ANIRÀ A TREBALLAR, i per això és viu també sobre
 *                    tasca d'altri (hi obre el diàleg de handoff, P4a) i sobre una `InProgress`
 *                    pròpia quan hi ha eina on entrar
 *   · `otherTech`  — d'altri: fade i transport apagat (§5)
 *   · `out`        — fora d'encàrrec
 */
export function lecturaDeTasca(task, { mine, hasToolRoute } = {}) {
  const transport = TRANSPORT[task?.status] || TRANSPORT.Pending
  return {
    transport,
    playActive: mine ? (transport.play || (hasToolRoute && task?.status === 'InProgress')) : true,
    otherTech: !mine && task?.assignee_id != null,
    out: isOutOfCharge(task),
    icon: TASK_ICON[task?.task_type_code] || 'ti-checkbox',
    variant: STATUS_VARIANT[task?.status] || 'gray',
  }
}
