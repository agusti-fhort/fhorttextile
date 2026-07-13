// Helpers de presentació compartits.

import i18n from '../i18n';

// Minuts (enters) → "Hh MMm". Coherent amb el format de TimeTracking.jsx (que
// treballa en SEGONS); aquí l'entrada ja són minuts consolidats del backend.
export function formatMinutes(m) {
  if (m == null) return '—';
  const total = Math.round(m);   // mitjanes del backend poden venir fraccionàries
  const h = Math.floor(total / 60), mm = total % 60;
  return `${h}h ${String(mm).padStart(2, '0')}m`;
}

// ─────────────────────────────────────────────────────────────────────────────
// LONGITUDS — la llei d'unitat, en un sol lloc (W4b · T7)
// ─────────────────────────────────────────────────────────────────────────────
//
// El canònic és SEMPRE el centímetre: és el que la BD desa, el que l'API serveix i el que
// el motor calcula. Això d'aquí baix només PRESENTA.
//
// Dues regles, i totes dues importen:
//
//   · **La precisió és de la unitat**, no del valor: cm → 1 decimal, inch → 2. Un patró
//     tècnic no es llegeix a la centèsima de centímetre, i en polzades un sol decimal
//     amagaria mig mil·límetre.
//   · **La conversió surt del valor COMPLET, mai del ja arrodonit.** Convertir des del
//     valor pintat (45,1) donaria 17.76 en comptes de 17.77: mig error de mil·límetre
//     regalat per haver llegit la pantalla en comptes de la dada. La dada no s'arrodoneix
//     mai —ni a la BD, ni a l'API, ni als exports—; s'arrodoneix la seva IMATGE.
//
// Viu aquí i no al mòdul de patrons perquè la llei ja existia (`fmtMeasure`, a
// `pages/fittingShared`), i dues implementacions de la mateixa llei acaben dient coses
// diferents del mateix número. Ara les dues en beuen.

export const CM_PER_INCH = 2.54;

const DECIMALS = { CM: 1, INCH: 2 };

/** Els decimals que li toquen a la unitat. */
export function unitDecimals(unit = 'CM') {
  return DECIMALS[unit] ?? DECIMALS.CM;
}

/** El valor en la unitat demanada, SENSE arrodonir. L'arrodoniment és l'últim pas, sempre. */
export function toUnit(cm, unit = 'CM') {
  return unit === 'INCH' ? cm / CM_PER_INCH : cm;
}

/** "45,1" — el número sol, arrodonit a la unitat i amb el separador de l'idioma. */
export function formatLenNum(cm, unit = 'CM') {
  if (cm == null || cm === '') return null;
  const n = Number(cm);
  if (Number.isNaN(n)) return String(cm);
  const d = unitDecimals(unit);
  return toUnit(n, unit).toLocaleString(i18n.language || 'ca', {
    minimumFractionDigits: d, maximumFractionDigits: d,
  });
}

/** "45,1 cm" — el número amb la seva unitat. És el format per defecte del taller. */
export function formatLen(cm, unit = 'CM') {
  const n = formatLenNum(cm, unit);
  return n == null ? '—' : `${n} ${unitLabel(unit)}`;
}

/** "+0,1" / "−2,3" — una diferència: el signe hi és sempre, perquè el signe és la meitat. */
export function formatDelta(cm, unit = 'CM') {
  if (cm == null || cm === '') return null;
  const n = Number(cm);
  if (Number.isNaN(n)) return String(cm);
  const d = unitDecimals(unit);
  const abs = Math.abs(toUnit(n, unit)).toLocaleString(i18n.language || 'ca', {
    minimumFractionDigits: d, maximumFractionDigits: d,
  });
  // El zero no porta signe: "+0,0" faria pensar que sobra alguna cosa.
  const signe = Number(abs.replace(',', '.')) === 0 ? '' : (n < 0 ? '−' : '+');
  return `${signe}${abs}`;
}

export function unitLabel(unit = 'CM') {
  return unit === 'INCH' ? 'inch' : 'cm';
}

/** El valor COMPLET, per al `title`: la dada, tal com és, sense arrodonir. */
export function titleLen(cm) {
  return cm == null || cm === '' ? '' : `${cm} cm`;
}
