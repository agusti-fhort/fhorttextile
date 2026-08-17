// Q8/B3 — EL SALT DE PÀGINA D'UNA TAULA DE LA FITXA, en un sol lloc i sense cap Konva a la vora.
//
// 🚨 PER QUÈ CAL AIXÒ I NO N'HI HA PROU AMB EL BUILDER. El full de fitting descarregable és HTML
// i qui el talla és el navegador: `thead` repeteix la capçalera i `break-inside: avoid` protegeix
// la fila, sense que ningú compti res (`FittingPrintSheet.jsx`). El canvas de la fitxa no té res
// d'això: una taula és UN objecte amb una x/y a UNA pàgina, i `fitTableObj` la feia cabre
// ESCALANT-LA sencera. O sigui que fins avui una taula llarga no es partia: s'encongia —i amb ella
// el cos de lletra, per sota del sòl de 8pt que el builder guarda a la seva banda—.
//
// Aquí el tall es decideix a la INSERCIÓ i el resultat són N objectes `table` normals i corrents,
// cadascun amb la seva capçalera i el seu títol, cadascun a la seva pàgina. Cap fila partida per
// la meitat, cap escala per alçada, cap primitiva nova.
//
// UNITAT-AGNÒSTIC A POSTA: entren números i en surten números, tots en la MATEIXA unitat. Qui
// crida treballa en mm (que és com la fitxa col·loca els objectes) i aquí no cal saber-ho.

/**
 * Reparteix N taules seguides en pàgines, tallant les files que no hi caben.
 *
 * Les taules van APILADES en un flux vertical: la primera arrenca a `yInici` de la pàgina on som
 * i cada següent cau sota l'anterior. Quan el que queda de pàgina no dona ni per a UNA fila, el
 * bloc salta a una pàgina nova i s'hi torna a emetre el títol i la capçalera.
 *
 * ⚠️ EL BLOC MÍNIM ÉS UNA FILA, MAI ZERO. Amb una fila més alta que la pàgina sencera —geometria
 * impossible que només pot venir d'un format minúscul o d'un cos enorme— la capacitat calculada
 * és 0 i un bucle honest no acabaria mai. S'emet igualment UNA fila i es deixa que vessi: una
 * taula que sobresurt es veu i es corregeix; un editor penjat, no.
 *
 * @param {Array<{hTitol: number, hCapcalera: number, hFila: number, nFiles: number}>} mesures
 *        geometria ja resolta de cada taula (el builder és qui la sap; aquí no es calcula).
 * @param {{yInici: number, yFinal: number, separacio?: number}} pagina
 *        `yInici` = on comença el cos útil · `yFinal` = on s'acaba · `separacio` = aire entre
 *        taules consecutives de la mateixa pàgina.
 * @returns {Array<{taula: number, ini: number, fi: number, pagina: number, y: number}>}
 *          un tros per objecte a inserir: `[ini, fi)` són índexs de fila de la taula `taula`.
 */
export function repartimentEnPagines(mesures, { yInici, yFinal, separacio = 6 }) {
  const trossos = []
  let pagina = 0
  let y = yInici

  ;(mesures || []).forEach((m, taula) => {
    const hTitol = Math.max(0, m?.hTitol || 0)
    const hCapcalera = Math.max(0, m?.hCapcalera || 0)
    const hFila = Math.max(0, m?.hFila || 0)
    const nFiles = Math.max(0, m?.nFiles || 0)
    const fixa = hTitol + hCapcalera

    // Una taula sense files és una capçalera sola: s'emet igualment. La decisió de si val la
    // pena inserir-la és de qui crida (l'espec de Q8a diu que una peça sense sessió no porta
    // taula), i barrejar-la aquí faria que aquest mòdul opinés sobre el domini.
    if (nFiles === 0) {
      if (y + fixa > yFinal && y > yInici) { pagina += 1; y = yInici }
      trossos.push({ taula, ini: 0, fi: 0, pagina, y })
      y += fixa + separacio
      return
    }

    let ini = 0
    while (ini < nFiles) {
      // Quantes files caben al que queda de pàgina, un cop pagats el títol i la capçalera.
      let capacitat = hFila > 0 ? Math.floor((yFinal - y - fixa) / hFila) : nFiles - ini
      // No hi cap ni una fila: pàgina nova. Només val la pena si NO estem ja al principi d'una
      // pàgina buida —si hi som, saltar-ne una altra no guanyaria ni un mil·límetre.
      if (capacitat < 1 && y > yInici) {
        pagina += 1
        y = yInici
        capacitat = hFila > 0 ? Math.floor((yFinal - y - fixa) / hFila) : nFiles - ini
      }
      if (capacitat < 1) capacitat = 1        // v. l'acta del bloc mínim, aquí sobre
      const n = Math.min(capacitat, nFiles - ini)
      trossos.push({ taula, ini, fi: ini + n, pagina, y })
      y += fixa + n * hFila + separacio
      ini += n
    }
  })

  return trossos
}

/** Quantes pàgines fan falta per a un repartiment (0 si no hi ha res). */
export const paginesDelRepartiment = (trossos) =>
  (trossos || []).reduce((n, t) => Math.max(n, t.pagina + 1), 0)

/**
 * L'AMPLADA QUE FA QUE EL NOM MÉS LLARG HI CÀPIGA EN `linies` LÍNIES.
 *
 * L'espec de Q8 diu «nom de POM mai tallat: amplada mínima = nom més llarg a màx 2 línies», i
 * això no es pot decidir amb un número escrit a mà: depèn del corpus del model. Un altre lloc
 * d'aquesta casa ja va pagar aquesta lliçó amb `FILES_PER_PAGINA = 18`, un límit «conservador a
 * posta» que era fals mesurat.
 *
 * Es pot comptar per CARÀCTERS i no estimar perquè la fitxa va en monoespaiada: `charMm` és
 * l'amplada exacta d'un caràcter. La mateixa aritmètica que el builder fa servir per no tallar
 * mai un títol de columna.
 *
 * @param {string[]} textos  els noms que hi han de cabre
 * @param {{charMm: number, padMm?: number, minMm?: number, maxMm?: number, linies?: number}} opts
 */
export function ampladaPerTextos(textos, { charMm, padMm = 0, minMm = 0, maxMm = Infinity, linies = 2 }) {
  const llarg = (textos || []).reduce((mx, s) => Math.max(mx, String(s ?? '').length), 0)
  if (!llarg || !(charMm > 0)) return Math.max(minMm, Math.min(maxMm, minMm))
  // Els caràcters que han de cabre en UNA línia perquè el text sencer ocupi `linies` com a molt.
  const perLinia = Math.ceil(llarg / Math.max(1, linies))
  const necessaria = perLinia * charMm + padMm
  return Math.max(minMm, Math.min(maxMm, necessaria))
}
