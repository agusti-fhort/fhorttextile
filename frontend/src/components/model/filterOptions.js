import { useState, useEffect } from 'react'
import {
  customers as customersApi, sizeSystems as sizeSystemsApi,
  gradingRuleSets as rulesetsApi, targets as targetsApi,
  fitTypes as fitTypesApi, constructionTypes as constrApi,
  taskTypes as taskTypesApi, users as usersApi,
  garmentTypes as garmentTypesApi, garmentGroups as garmentGroupsApi,
} from '../../api/endpoints'

// useFilterOptions — carrega UN sol cop les llistes d'opcions del panell de filtres de Models i
// exposa resolvers id→nom perquè els selects i els chips resolguin etiquetes sense pagar cap query
// per fila (els noms dels chips NO venen del ModelListSerializer, G-D2). Font única compartida entre
// el panell (ModelsFilterPanel) i els chips (Models.jsx).
const rows = (r) => r.data?.results ?? r.data ?? []

export function useFilterOptions() {
  const [o, setO] = useState({
    customers: [], sizeSystems: [], rulesets: [], targets: [], fits: [],
    constructions: [], taskTypes: [], users: [], garmentTypes: [], garmentGroups: [],
  })
  useEffect(() => {
    let alive = true
    Promise.allSettled([
      customersApi.list({ page_size: 500 }),
      sizeSystemsApi.list({ page_size: 500 }),
      rulesetsApi.list({ page_size: 500 }),
      targetsApi.list({ page_size: 200 }),
      fitTypesApi.list({ page_size: 200 }),
      constrApi.list({ page_size: 200 }),
      taskTypesApi.list({ page_size: 500 }),
      usersApi.list({ page_size: 500 }),
      garmentTypesApi.list({ actiu: 'true', page_size: 500 }),
      garmentGroupsApi.list({ page_size: 200 }),
    ]).then(res => {
      if (!alive) return
      const g = (i) => res[i].status === 'fulfilled' ? rows(res[i].value) : []
      setO({
        customers: g(0), sizeSystems: g(1), rulesets: g(2), targets: g(3), fits: g(4),
        constructions: g(5), taskTypes: g(6), users: g(7), garmentTypes: g(8), garmentGroups: g(9),
      })
    })
    return () => { alive = false }
  }, [])
  return o
}

// Resolvers d'etiqueta (idioma opcional per a famílies de garment i grups).
export function garmentTypeLabel(opts, id, lang = 'ca') {
  const f = opts.garmentTypes.find(g => String(g.id) === String(id))
  if (!f) return `#${id}`
  if (lang === 'es') return f.nom_es || f.nom_en || f.nom_client || `#${id}`
  if (lang === 'en') return f.nom_en || f.nom_client || `#${id}`
  return f.nom_ca || f.nom_en || f.nom_client || `#${id}`
}

export function garmentGroupLabel(opts, codi) {
  const g = opts.garmentGroups.find(x => x.codi === codi)
  return g?.nom || codi
}
