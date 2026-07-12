// Metadades de presentació d'un fitxer, compartides per FileList (S03c · C4) i per la secció
// Fitxers de GarmentTypes (D21). Viuen fora del component perquè no en són: exportar-les des
// del .jsx trencaria el fast-refresh de Vite (un mòdul, o components, o constants).

// Només icones Tabler outline JA presents al codebase. La webfont ve per CDN: un nom inventat
// renderitza un quadre buit i cap build ho detecta.
const ICONA = [
  [/\.pdf$/i, 'ti-file-type-pdf'],
  [/\.(png|jpe?g|webp|gif)$/i, 'ti-photo'],
  [/\.svg$/i, 'ti-vector-bezier'],
  [/\.dxf$/i, 'ti-sitemap'],
  [/\.ftt$/i, 'ti-file-text'],
  [/\.(xlsx?|csv)$/i, 'ti-file-spreadsheet'],
]

export const iconaDe = (nom = '') => (ICONA.find(([re]) => re.test(nom)) || [null, 'ti-file'])[1]

// Base 1024 amb un decimal: coherent amb el missatge d'`UploadRejected` del backend
// (`services_fitxers.py`), que compta els MB en 1024.
export function midaLlegible(bytes) {
  if (bytes === null || bytes === undefined) return '—'
  if (bytes < 1024) return `${bytes} B`
  const kb = bytes / 1024
  if (kb < 1024) return `${kb.toFixed(kb < 10 ? 1 : 0)} KB`
  return `${(kb / 1024).toFixed(1)} MB`
}

export const dataCurta = (iso) => (iso ? String(iso).slice(0, 10) : '—')
