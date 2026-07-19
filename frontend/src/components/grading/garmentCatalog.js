import { useState, useEffect, useMemo } from 'react'
import { garmentTypes, garmentGroups } from '../../api/endpoints'
import { GARMENT_GROUPS } from './gradingAxes'

// garmentCatalog — FONT ÚNICA de la cascada de catàleg del wizard (sprint Wizard unificat · Onada 1).
// Donat un `target` OPCIONAL retorna els GRUPS de peça disponibles (registre de BD /garment-groups/,
// retallats als que tenen famílies COMPATIBLES amb el target) i les FAMÍLIES. Sense target → catàleg
// complet (no bloqueja). Consumit per AxesSelector i GarmentTypeSelector (i, a l'Onada 2, ScopeSelector),
// perquè totes les pantalles es comportin IGUAL.
//
// Compatibilitat target↔família: SizingProfile via el backend `?target` (targets_recomanats és buit a
// staging — vegeu docs/diagnosis/DIAGNOSI_WIZARD_CASCADA_TARGET.md). Els items segueixen carregant-se
// per família (peresós) allà on calgui.

// Ordre canònic + etiquetes localitzades dels grups coneguts. El registre de BD mana la DISPONIBILITAT
// (quins grups existeixen/actius, NEWBORN inclòs); el vocabulari només aporta ordre i noms ca/en/es dels
// canònics. Un grup nou de BD (sense entrada al vocabulari) surt amb el seu `nom` de BD.
const ORDER = GARMENT_GROUPS.map(g => g.codi)
const VOCAB = Object.fromEntries(GARMENT_GROUPS.map(g => [g.codi, g]))

function normGroup(codi, bdNom) {
  return VOCAB[codi] || { codi, nom_en: bdNom || codi, nom_ca: bdNom || codi, nom_es: bdNom || codi }
}

export function useGarmentCatalog(target) {
  const [registry, setRegistry] = useState([])   // /garment-groups/ (codi, nom, actiu)
  const [families, setFamilies] = useState([])    // GarmentType compatibles amb el target
  const [loading, setLoading] = useState(true)

  // Registre de grups de la BD (una vegada). Font de disponibilitat + noms de grups nous.
  useEffect(() => {
    let alive = true
    garmentGroups.list({ page_size: 200 })
      .then(r => { if (alive) setRegistry(r.data?.results ?? r.data ?? []) })
      .catch(() => { if (alive) setRegistry([]) })
    return () => { alive = false }
  }, [])

  // Famílies (catàleg sencer, filtrat pel target quan n'hi ha) — una sola crida.
  useEffect(() => {
    let alive = true
    setLoading(true)
    garmentTypes.list({ actiu: 'true', page_size: 500, ...(target ? { target } : {}) })
      .then(r => { if (alive) setFamilies(r.data?.results ?? r.data ?? []) })
      .catch(() => { if (alive) setFamilies([]) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [target])

  // Grups a mostrar: presents a les famílies compatibles ∩ actius al registre, ordre canònic.
  const groups = useMemo(() => {
    const present = [...new Set(families.map(f => f.grup).filter(Boolean))]
    const activeCodis = new Set(registry.filter(g => g.actiu !== false).map(g => g.codi))
    const bdNom = Object.fromEntries(registry.map(g => [g.codi, g.nom]))
    return present
      // si el registre encara no ha carregat, no amaguem res (evita cascada buida transitòria)
      .filter(codi => activeCodis.size === 0 || activeCodis.has(codi))
      .sort((a, b) => (ORDER.indexOf(a) + 1 || 999) - (ORDER.indexOf(b) + 1 || 999))
      .map(codi => normGroup(codi, bdNom[codi]))
  }, [families, registry])

  const familiesOf = (grupCodi) => families.filter(f => f.grup === grupCodi)

  return { groups, familiesOf, families, loading }
}

// useGarmentGroups — TOTS els grups actius de la BD (registre normalitzat + ordenat pel vocabulari),
// SENSE filtre de target ni de famílies. Per a superfícies d'ADMINISTRACIÓ del catàleg (Garment Types
// CRUD) que gestionen tots els grups, també els encara buits. Mateixa font (/garment-groups/) i mateixa
// normalització d'etiquetes que la cascada.
export function useGarmentGroups() {
  const [registry, setRegistry] = useState([])
  useEffect(() => {
    let alive = true
    garmentGroups.list({ page_size: 200 })
      .then(r => { if (alive) setRegistry(r.data?.results ?? r.data ?? []) })
      .catch(() => { if (alive) setRegistry([]) })
    return () => { alive = false }
  }, [])
  return useMemo(() => registry
    .filter(g => g.actiu !== false)
    .map(g => normGroup(g.codi, g.nom))
    .sort((a, b) => (ORDER.indexOf(a.codi) + 1 || 999) - (ORDER.indexOf(b.codi) + 1 || 999)),
    [registry])
}
