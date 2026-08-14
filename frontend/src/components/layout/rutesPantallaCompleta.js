// LES RUTES QUE ES PINTEN A PANTALLA COMPLETA — declarades, no deduïdes.
//
// ── PER QUÈ AQUEST FITXER EXISTEIX ──────────────────────────────────────────────────────────
// La fitxa tècnica és una EINA: el llenç mana i el crom de l'app hi fa nosa. Fins al 09/08 això
// s'aconseguia declarant-ne la `<Route>` FORA del `Shell`, i el 133496e2 la va moure a dins per
// una raó bona —l'editor s'havia hagut de pintar el seu propi bastiment sencer (logo,
// breadcrumb, barra de 56px) i el resultat era una fitxa que no s'assemblava a cap altra
// secció del model, amb el camí escrit dues vegades. El que aquell tram no va veure és que,
// en entrar al bastiment, s'hi enduia TAMBÉ el sidebar, la top bar i les nou píndoles de
// seccions del model: l'eina va perdre la pantalla completa (Agus, a pantalla, 14/08).
//
// Les dues sortides òbvies són totes dues dolentes:
//   · tornar la ruta FORA del Shell → l'editor es queda SENSE fletxa de sortir i SENSE
//     «Exportar PDF», perquè des del 09/08 tots dos viuen al `PageMenu`, que es teletransporta
//     al forat que obre el Shell (`chromeSlot.js`). Fora del Shell el portal no té destí.
//     A més, `--chrome-h` el publica el Shell: l'alçada de l'editor deixaria de quadrar.
//   · deixar-ho com està → l'eina segueix amb tres nivells de crom aliè al damunt.
//
// LA SORTIDA: la ruta es queda DINS del Shell —conserva el portal, `--chrome-h` i el fet de no
// haver-se de repintar cap bastiment— i el Shell li amaga el crom de NAVEGACIÓ (sidebar, top
// bar). El que queda a pantalla és la barra pròpia de l'eina: fletxa de sortir, crom del
// document i Exportar PDF. La casa segueix posant el bastiment; simplement, aquí no hi posa
// menús.
//
// ⚠️ AIXÒ ÉS UNA LLISTA, I ÉS A POSTA. Deduir-ho («si la pàgina té un canvas…») seria màgia que
// el proper refactor trencaria sense dir res. Declarat, hi ha un guard que ho pot vigilar
// (`rutesPantallaCompleta.test.js`): comprova que la fitxa NO acabi renderitzant-se amb el
// layout general, tant si algú mou la `<Route>` com si algú buida aquesta llista.

/** Rutes que el `Shell` ha de pintar sense sidebar ni top bar. Ancorades (`^…$`) perquè
 *  `/models/1320` o `/models/1320/escalat` NO hi entrin: són pàgines, no eines. */
const PANTALLA_COMPLETA = [
  // Editor de fitxa tècnica (.ftt) — `/models/:id/ftt/:fitxerId`.
  /^\/models\/\d+\/ftt\/\d+\/?$/,
]

/** ¿Aquest `pathname` s'ha de pintar a pantalla completa? */
export function esPantallaCompleta(pathname) {
  if (typeof pathname !== 'string') return false
  return PANTALLA_COMPLETA.some(r => r.test(pathname))
}

export default PANTALLA_COMPLETA
