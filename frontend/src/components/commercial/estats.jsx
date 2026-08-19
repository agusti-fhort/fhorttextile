// ELS BADGES D'ESTAT DEL MÒDUL COMERCIAL — un sol lloc per a tot el lot.
//
// **PER QUÈ EXISTEIX.** Cada pantalla del lot es declarava el seu propi mapa d'estats i, pitjor,
// la seva pròpia LLISTA de codis: `STATUSES = ['DRAFT','SENT',…]` a `Quotes`, un altre a `Orders`,
// un altre a `OrderDetail`, un altre a `DeliveryNotes`, un altre a `WorkOrders`… i **`ModelTask.status`
// declarat DUES vegades amb DOS mapes de color diferents** (`WorkOrderDetail.jsx:23` i
// `OrderDetail.jsx:299`). A sobre, `CustomerDetail` importava els badges de `pages/Quotes`,
// `pages/Orders` i `pages/DeliveryNotes` — una fitxa depenent de tres pàgines de llista.
//
// La llei d'Agus (08/08): **cap enumeració de domini es declara al frontend.** Els codis surten
// ara de `GET /api/v1/vocabulari/` via `utils/vocabulariDominiFont`, que és la font única de la
// casa. Aquí NO hi ha cap llista de codis: només el mapa de COLOR, que és presentació.
//
// ⚠️ **PER QUÈ UN MAPA DE COLOR NO ÉS UNA SEGONA FONT DE VERITAT, i on és la frontera.**
// Una llista (`['DRAFT','SENT',…]`) AFIRMA quins membres existeixen, i el dia que l'original
// n'afegeix un, menteix sense fallar (és exactament el que va passar amb `CustomerPOMAlias.origen`,
// que en va guanyar un cinquè —`MODEL`— i el client en seguia declarant quatre). Un mapa amb
// **fallback** no afirma res: qui no hi és, es pinta neutre i s'ensenya igualment. La llista de
// què s'ofereix ve sempre de l'endpoint; el mapa només diu de quin color es pinta el que arriba.
//
// ── EL CODI DE COLORS, I LA DECISIÓ DE CADA UN (§8e) ────────────────────────────────────────
// La §8e fixa TRES estats per a un badge comercial: **«Començat neutre · En curs taronja ·
// Acabat verd»**, i la §1 hi afegeix el vermell per al que ha acabat malament. El que hi havia
// feia servir `gold` per a «en curs», que és un QUART color que la norma no nomena — i el daurat
// és marca, no dada. Cada mapa d'aquí baixa a l'escala de la norma, i cada decisió s'explica.
//
// 🚩 **TRES DECISIONS DE DOMINI, no d'estil, que van al report perquè Agus les pugui vetar:**
//  1. **OFERTA · `EXPIRED` es pinta com `REJECTED` (vermell).** Des del punt de vista comercial
//     les dues volen dir el mateix: l'oferta s'ha acabat sense convertir-se en comanda. La
//     diferència (si el client va dir que no, o si simplement va passar la data) la diu la
//     PARAULA; el color diu el desenllaç. Abans `EXPIRED` era taronja, que en aquesta escala vol
//     dir «encara en curs», i una oferta caducada no ho està.
//  2. **TASCA · `Paused` i `Pending` comparteixen el neutre.** Són quatre estats sobre un eix de
//     tres colors, i el que col·lapsa és «ara mateix no corre». L'eix de la §8e és el PROGRÉS, no
//     el rellotge: una tasca pausada no ha avançat més que una de pendent. Els distingeix la
//     paraula.
//  3. **PROVINENÇA I TIPUS DE LÍNIA NO SÓN SEMÀFORS, i deixen de pintar-se com si ho fossin.**
//     `origen` d'un àlies (IMPORT · MANUAL · MIGRACIO · DICCIONARI · MODEL) i `line_kind` d'un
//     albarà (TASK · EXTRA · DEDUCTION · EXPENSE · MANUAL) són CLASSIFICACIONS: cap membre és
//     millor ni pitjor que un altre. Anaven amb verd, daurat, vermell i taronja repartits sense
//     cap criteri llegible —`TASK` verd i `DEDUCTION` vermell suggerien que una deducció és un
//     error—, i ara van **tots neutres**. El vermell d'una deducció el porta **el número**, que
//     és negatiu: D-31.21, «la dada porta el color».
import Badge from '../ui/Badge'
import { useEnumeracio } from '../../utils/vocabulariDominiFont'

/** Cap membre declarat: només de quin color es pinta el que arribi. Fallback → neutre. */
const COLOR = {
  estats_oferta: { DRAFT: 'gray', SENT: 'warn', ACCEPTED: 'ok', REJECTED: 'err', EXPIRED: 'err' },
  estats_comanda: { OPEN: 'warn', COMPLETED: 'ok', CANCELLED: 'err' },
  estats_albara: { DRAFT: 'gray', ISSUED: 'warn', INVOICED: 'ok' },
  estats_encarrec: { OPEN: 'warn', CLOSED: 'ok' },
  estats_tasca: { Pending: 'gray', Paused: 'gray', InProgress: 'warn', Done: 'ok' },
  estats_locals_encarrec: { PENDENT: 'warn', TRASPASSAT: 'ok' },
}

/**
 * El badge d'un estat. `clau` és la llista del vocabulari (per triar el mapa de color) i `codi`
 * el valor que ha arribat de l'API. L'etiqueta la posa qui crida, ja traduïda — aquest fitxer no
 * porta cap literal de cara a l'usuari, com `ui/PageMenu` i `ui/TaulaLlista`.
 *
 * Un codi desconegut **s'ensenya igualment**, en neutre: si el domini n'estrena un, la pantalla
 * l'ha de mostrar, no amagar-lo. Amagar-lo seria el mode de fallada silenciós que tot això
 * intenta matar.
 */
export function EstatBadge({ clau, codi, children }) {
  if (!codi) return null
  return <Badge variant={COLOR[clau]?.[codi] || 'gray'}>{children ?? codi}</Badge>
}

/**
 * Els codis oferibles d'una enumeració, per als selects de filtre.
 *
 * Torna `null` —i no `[]`— mentre no se sap, que és el contracte de `vocabulariDominiFont`:
 * `[]` voldria dir «aquesta enumeració és buida», i això és una afirmació que no podem fer. Qui
 * rep `null` NO ha d'oferir opcions; «totes» segueix funcionant, perquè no filtrar no demana
 * saber-se la llista.
 */
export function useCodisEstat(clau) {
  return useEnumeracio(clau)
}

/**
 * Les CLASSIFICACIONS (provinença, tipus de línia): sempre neutres. Té component propi i no un
 * `variant="gray"` escampat perquè el motiu és una regla, no una preferència — v. la decisió 3
 * de la capçalera. Si algun dia una classificació ha de portar color, es discuteix AQUÍ.
 */
export function ClassificacioBadge({ children }) {
  if (children == null) return null
  return <Badge variant="gray">{children}</Badge>
}
