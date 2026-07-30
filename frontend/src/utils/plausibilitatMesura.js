// FIX-4 (DIAGNOSI_MESURES_TEA_205) — MESURA i DELTA no es poden confondre.
//
// EL CAS: al model 205, el POM B té la base a 46 cm i algú va escriure `1` a les cel·les de
// talla XXS i XS. `1` no és una llargada: és l'increment de la regla. La taula ho va acceptar
// sense dir res, perquè una cel·la de talla i un camp Δ són tots dos «un número» i seuen a
// pocs píxels l'un de l'altre.
//
// EL CRITERI: no es bloqueja mai. Existeixen peces petites legítimes (una trabeta de 2 cm amb
// base 2 cm) i existeixen deltes grans legítims (una faldilla que creix 4 cm per talla amb
// base 18). Un bloqueig dur els faria impossibles, i la conseqüència real seria que el tècnic
// aprengués a esquivar la validació. El que hi ha aquí és una PREGUNTA, i el «sí» desa amb
// normalitat.
//
// ELS LLINDARS són asimètrics a posta, perquè els dos errors ho són:
//   · escriure un DELTA on va una MESURA dóna un número molt més petit que la base → 40%
//   · escriure una MESURA on va un DELTA dóna un número molt més gran que un pas → 20%
//
// Funcions PURES, sense React ni i18n: la decisió és aquí, el text és a la capa que pregunta.
//     cd frontend && node --test src/utils/plausibilitatMesura.test.js

/** Fracció de la base per sobre de la qual una cel·la de TALLA deixa de semblar una mesura. */
export const LLINDAR_MESURA = 0.40

/** Fracció de la base per sobre de la qual un camp Δ deixa de semblar un increment. */
export const LLINDAR_DELTA = 0.20

/** Número finit, o null. Accepta la coma decimal (la graella la deixa escriure). */
function num(v) {
  if (v === '' || v == null) return null
  const n = Number(String(v).replace(',', '.'))
  return Number.isFinite(n) ? n : null
}

/**
 * Una cel·la de TALLA que sembla un increment i no una mesura.
 *
 * Cert quan el valor s'allunya de la base més del 40% de la base. Sense base (o base 0) no
 * hi ha res contra què comparar → no es pregunta: millor callar que acusar a cegues.
 */
export function mesuraSemblaIncrement(valor, base) {
  const v = num(valor)
  const b = num(base)
  if (v == null || b == null || b === 0) return false
  return Math.abs(v - b) > Math.abs(b) * LLINDAR_MESURA
}

/**
 * Un camp Δ que sembla una mesura i no un increment.
 *
 * Cert quan el delta supera el 20% de la base. El delta pot ser negatiu (una corba que
 * decreix); el que compta és la magnitud.
 */
export function deltaSemblaMesura(delta, base) {
  const d = num(delta)
  const b = num(base)
  if (d == null || b == null || b === 0) return false
  return Math.abs(d) > Math.abs(b) * LLINDAR_DELTA
}
