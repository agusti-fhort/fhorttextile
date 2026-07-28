// F4 — el `format` OPCIONAL per pàgina d'un document .ftt, en un sol lloc.
//
// EL CONTRACTE (no canvia): 'format' ∈ {A4L,A4P,A3L,A3P} és opcional a cada pàgina i la seva
// ABSÈNCIA vol dir "hereta el `pageFormat` del document". Per això la clau no s'escriu mai
// quan no hi és: un document que mai ha tocat formats mixtos ha de sobreviure el round-trip
// idèntic, i un `format: undefined` a cada pàgina ja no ho seria.
//
// Aquestes dues funcions són les úniques que reconstrueixen una pàgina camp a camp. Cada cop
// que se n'ha escrit una de nova, la clau nova s'hi ha perdut en silenci — que és exactament
// com el format per pàgina no arribava a sobreviure a reobrir el document.
// Anàleg JS de services_ftt._amb_format.

// Arrossega el `format` de l'origen a la pàgina reconstruïda, si en porta.
export const ambFormat = (origen, sortida) => (origen?.format ? { ...sortida, format: origen.format } : sortida)

// template_json v2 (del backend) → pàgines de l'estat de l'editor. `nouId` genera els ids que
// falten (documents antics sense id de pàgina o d'objecte).
export function hidratarPagines(v2Pages, nouId) {
  return (v2Pages || []).map(p => ambFormat(p, {
    id: p.id || nouId(),
    objects: (p.objects || []).map(o => ({ ...o, id: o.id || nouId() })),
    guides: p.guides || [],
  }))
}
