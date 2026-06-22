// Etiqueta visible del tipus de tasca. Per defecte usa el nom que ve del backend
// (català, LANGUAGE_CODE='ca'); si hi ha una clau i18n per al code, té prioritat
// (permet renombrar tipus a la UI als 3 idiomes sense tocar el backend).
// v2: `size_check` ("Mesurar prenda") es mostra com a "Mesures".
export function taskTypeLabel(t, code, name) {
  return t(`tasktype.${code}`, { defaultValue: name || code || '—' })
}
