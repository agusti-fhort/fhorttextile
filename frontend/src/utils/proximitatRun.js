// proximitatRun.js — la PROXIMITAT d'un run de talles, com a funcions pures.
//
// Ve de `ModelWizard.jsx` (W2.2), on vivia inline. N3 (2026-08-06 nit) l'amplia de dues claus
// a cinc i l'extreu perquè es pugui provar sense muntar el wizard sencer.
//
// ── LA REGLA NO CANVIA: ORDENA, MAI AMAGA ────────────────────────────────────────────────
// Cap run cau de la llista per no encaixar. És la mateixa D-31.3 que regeix el pas 2: les eines
// s'ofereixen senceres i s'acoten amb informació, no amb ocultació. Un run que no encaixa amb
// res queda l'últim, però hi és, i la tècnica pot veure que existeix.
//
// ── QUÈ VOL DIR «A PROP», EN CINC CLAUS I EN AQUEST ORDRE ────────────────────────────────
//   1r · EL TARGET de la peça.
//   2n · DE QUI ÉS EL RUN — el del client d'aquest model primer, els canònics després, i els
//        d'ALTRES clients al final. Aquesta clau va SEGONA a posta i no baixa: el parany del
//        model 174 és oferir el run d'un altre client com si fos teu.
//   3r-5è · CONSTRUCCIÓ · FIT · GRUP, les tres capes que N1 va donar al run. Van DESPRÉS de
//        l'origen perquè són desempats: afinen entre runs igual de propers, no reordenen qui
//        és de qui.
//
// ── LA SEMÀNTICA DE CADA CAPA (idèntica a les 4) ─────────────────────────────────────────
// Una capa BUIDA no és universal i tampoc és incompatible: és NO DECLARADA, i queda al mig.
// Aquesta és la llei que el serializer ja declara per a `targets` i que N1 estén a les altres
// tres — «buit NO vol dir universal».

export const PROP = { SI: 0, SENSE: 1, ALTRE: 2 }

/** Proximitat d'UNA capa: 0 la declara · 1 no en declara cap · 2 en declara d'altres.
 *  Si el model no té valor per a aquest eix, la capa no pot discriminar i és NEUTRA (0 per a
 *  tothom): un eix que l'usuari no ha triat no ha de moure ningú de lloc. */
export function proximitatCapa(codis, valor) {
  if (!valor) return PROP.SI
  if (!codis || codis.length === 0) return PROP.SENSE
  return codis.includes(valor) ? PROP.SI : PROP.ALTRE
}

export function proximitatTarget(run, target) {
  return proximitatCapa(run.target_codis, target)
}

/** De qui és el run. `customer_codi` és el codi curt del run (`SizeSystem.customer_codi`). */
export function proximitatOrigen(run, customerCodi) {
  if (!run.customer_codi) return 1                                 // canònic de la casa
  return run.customer_codi === customerCodi ? 0 : 2                // meu · d'un altre client
}

/** Ordena una llista de runs per proximitat a `eixos` = {target, construction, fit, grup}.
 *  `nom`/`codi` desempaten al final perquè l'ordre sigui estable entre càrregues: dos runs
 *  igual de propers no poden ballar de posició a cada F5. */
export function ordenaPerProximitat(runs, eixos = {}, customerCodi = null) {
  const { target = null, construction = null, fit = null, grup = null } = eixos
  return [...runs].sort((a, b) =>
    proximitatTarget(a, target) - proximitatTarget(b, target) ||
    proximitatOrigen(a, customerCodi) - proximitatOrigen(b, customerCodi) ||
    proximitatCapa(a.construccio_codis, construction) - proximitatCapa(b.construccio_codis, construction) ||
    proximitatCapa(a.fit_codis, fit) - proximitatCapa(b.fit_codis, fit) ||
    proximitatCapa(a.grup_codis, grup) - proximitatCapa(b.grup_codis, grup) ||
    (a.nom || a.codi || '').localeCompare(b.nom || b.codi || ''))
}
