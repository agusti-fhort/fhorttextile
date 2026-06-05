// Configuració fiscal compartida: llista de països (ISO 3166-1 alpha-2),
// conjunt UE i càlcul del règim de VAT.
//
// El backend és la font de veritat del regim_vat; aquí el calculem només com a
// fallback de presentació quan l'API encara no el retorna (Sprint 3 en curs).

export const EU_SET = new Set([
  'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR',
  'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK',
  'SI', 'ES', 'SE',
])

// Llista de països per al selector. Espanya i veïns UE al capdavant + resta comuns.
export const COUNTRIES = [
  { code: 'ES', name: 'Espanya' },
  { code: 'FR', name: 'França' },
  { code: 'PT', name: 'Portugal' },
  { code: 'IT', name: 'Itàlia' },
  { code: 'DE', name: 'Alemanya' },
  { code: 'NL', name: 'Països Baixos' },
  { code: 'BE', name: 'Bèlgica' },
  { code: 'AT', name: 'Àustria' },
  { code: 'IE', name: 'Irlanda' },
  { code: 'GR', name: 'Grècia' },
  { code: 'PL', name: 'Polònia' },
  { code: 'SE', name: 'Suècia' },
  { code: 'DK', name: 'Dinamarca' },
  { code: 'FI', name: 'Finlàndia' },
  { code: 'CZ', name: 'Txèquia' },
  { code: 'RO', name: 'Romania' },
  { code: 'HU', name: 'Hongria' },
  { code: 'BG', name: 'Bulgària' },
  { code: 'HR', name: 'Croàcia' },
  { code: 'SK', name: 'Eslovàquia' },
  { code: 'SI', name: 'Eslovènia' },
  { code: 'LT', name: 'Lituània' },
  { code: 'LV', name: 'Letònia' },
  { code: 'EE', name: 'Estònia' },
  { code: 'LU', name: 'Luxemburg' },
  { code: 'CY', name: 'Xipre' },
  { code: 'MT', name: 'Malta' },
  { code: 'GB', name: 'Regne Unit' },
  { code: 'CH', name: 'Suïssa' },
  { code: 'NO', name: 'Noruega' },
  { code: 'US', name: 'Estats Units' },
  { code: 'CA', name: 'Canadà' },
  { code: 'MX', name: 'Mèxic' },
  { code: 'MA', name: 'Marroc' },
  { code: 'TR', name: 'Turquia' },
  { code: 'CN', name: 'Xina' },
  { code: 'JP', name: 'Japó' },
]

export function countryName(code) {
  const c = COUNTRIES.find((x) => x.code === (code || '').toUpperCase())
  return c ? c.name : (code || '—')
}

export const REGIM_VAT_LABELS = {
  espanyol: 'Espanyol (IVA estàndard)',
  reverse_charge_ue: 'Inversió del subjecte passiu (UE B2B)',
  oss_ue: 'OSS (UE B2C)',
  fora_ue: 'Fora de la UE (exportació)',
}

// Calcula el règim de VAT a partir del país i el tipus de client.
// Empresa de referència: Espanya (ES).
export function regimVat(pais, tipusClient) {
  const p = (pais || '').toUpperCase()
  if (!p) return null
  if (p === 'ES') return 'espanyol'
  if (EU_SET.has(p)) return tipusClient === 'b2b' ? 'reverse_charge_ue' : 'oss_ue'
  return 'fora_ue'
}

export function regimVatLabel(regim) {
  return REGIM_VAT_LABELS[regim] || '—'
}
