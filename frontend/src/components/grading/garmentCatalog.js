import { useState, useEffect, useMemo } from 'react'
import { garmentTypes, garmentGroups } from '../../api/endpoints'
import { GARMENT_GROUPS } from './gradingAxes'

// garmentCatalog — FONT ÚNICA de la cascada de catàleg del wizard (sprint Wizard unificat · Onada 1).
// Donat un `target` OPCIONAL retorna els GRUPS de peça disponibles (registre de BD /garment-groups/,
// retallats als que tenen famílies COMPATIBLES amb el target) i les FAMÍLIES. Sense target → catàleg
// complet (no bloqueja). Consumit per CascadeSelector (component unic dels selectors de cascada) i
// per la pagina Garment Types, perquè totes les pantalles es comportin IGUAL.
//
// Compatibilitat target↔família: SizingProfile via el backend `?target` (vegeu
// docs/diagnosis/DIAGNOSI_WIZARD_CASCADA_TARGET.md). Els items segueixen carregant-se per família
// (peresós) allà on calgui.

// Ordre canònic + etiquetes localitzades dels grups coneguts. El registre de BD mana la DISPONIBILITAT
// (quins grups existeixen/actius, NEWBORN inclòs); el vocabulari només aporta ordre i noms ca/en/es dels
// canònics. Un grup nou de BD (sense entrada al vocabulari) surt amb el seu `nom` de BD.
const ORDER = GARMENT_GROUPS.map(g => g.codi)
const VOCAB = Object.fromEntries(GARMENT_GROUPS.map(g => [g.codi, g]))

function normGroup(codi, bdNom) {
  return VOCAB[codi] || { codi, nom_en: bdNom || codi, nom_ca: bdNom || codi, nom_es: bdNom || codi }
}

// `compat` (C5, 2026-07-23) — quan s'informa ({ construction, fit }, tots dos opcionals), el
// catàleg passa a mode ANOTAT: NO s'exclou cap família; cadascuna arriba amb `.compat = {ok,
// motiu}` i el consumidor l'atenua. És l'altra cara del mode històric (filtre excloent), que es
// conserva per a les superfícies que encara no han rebut C5.
export function useGarmentCatalog(target, compat = null) {
  const [registry, setRegistry] = useState([])   // /garment-groups/ (codi, nom, actiu)
  const [families, setFamilies] = useState([])    // GarmentType compatibles amb el target
  const [loading, setLoading] = useState(true)
  const compatKey = compat ? `${compat.construction || ''}|${compat.fit || ''}` : null

  // Registre de grups de la BD (una vegada). Font de disponibilitat + noms de grups nous.
  useEffect(() => {
    let alive = true
    garmentGroups.list({ page_size: 200 })
      .then(r => { if (alive) setRegistry(r.data?.results ?? r.data ?? []) })
      .catch(() => { if (alive) setRegistry([]) })
    return () => { alive = false }
  }, [])

  // Famílies — una sola crida. Mode històric: filtrades pel target (excloent). Mode C5: totes,
  // amb el veredicte de compatibilitat anotat pel backend.
  useEffect(() => {
    let alive = true
    setLoading(true)
    const params = compatKey != null
      ? {
        ...(target ? { compat_target: target } : {}),
        ...(compat?.construction ? { compat_construction: compat.construction } : {}),
        ...(compat?.fit ? { compat_fit: compat.fit } : {}),
      }
      : (target ? { target } : {})
    garmentTypes.list({ actiu: 'true', page_size: 500, ...params })
      .then(r => { if (alive) setFamilies(r.data?.results ?? r.data ?? []) })
      .catch(() => { if (alive) setFamilies([]) })
      .finally(() => { if (alive) setLoading(false) })
    // eslint-disable-next-line react-hooks/exhaustive-deps
    return () => { alive = false }
  }, [target, compatKey])

  // Grups a mostrar: presents a les famílies ∩ actius al registre, ordre canònic. En mode C5 un
  // grup és compatible si ho és alguna de les seves famílies (i s'atenua, no s'amaga).
  const groups = useMemo(() => {
    const present = [...new Set(families.map(f => f.grup).filter(Boolean))]
    const activeCodis = new Set(registry.filter(g => g.actiu !== false).map(g => g.codi))
    const bdNom = Object.fromEntries(registry.map(g => [g.codi, g.nom]))
    return present
      // si el registre encara no ha carregat, no amaguem res (evita cascada buida transitòria)
      .filter(codi => activeCodis.size === 0 || activeCodis.has(codi))
      .sort((a, b) => (ORDER.indexOf(a) + 1 || 999) - (ORDER.indexOf(b) + 1 || 999))
      .map(codi => {
        const g = normGroup(codi, bdNom[codi])
        if (compatKey == null) return g
        const seves = families.filter(f => f.grup === codi)
        const ok = seves.some(f => f.compat?.ok !== false)
        return { ...g, compat: { ok, motiu: ok ? null : (seves[0]?.compat?.motiu ?? 'target') } }
      })
  }, [families, registry, compatKey])

  // C5 — dins del grup, els compatibles amunt i els atenuats avall (ordre estable dins de cada
  // bloc). Sense mode compat, l'ordre és el del backend, intacte.
  const familiesOf = (grupCodi) => {
    const f = families.filter(x => x.grup === grupCodi)
    if (compatKey == null) return f
    return [...f.filter(x => x.compat?.ok !== false), ...f.filter(x => x.compat?.ok === false)]
  }

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
