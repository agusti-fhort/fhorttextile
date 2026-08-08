// LES TRES FUNCIONS PURES DEL RUN DE TALLES — mòdul compartit.
//
// Vivien a l'abast de mòdul de `ModelWizard.jsx`, que era l'únic que les feia servir. El
// **Resum amb el wizard partit** (NORMA_LAYOUT §8f) és la GERMANA DE PRESENTACIÓ d'aquell pas
// 3: pinta el mateix domini amb una altra pell i **ha de decidir exactament igual**. Copiar-les
// seria estrenar una segona veritat sobre què és un run vàlid i en quin ordre va.
//
// El moviment és PUR: el codi és el mateix, línia per línia, i el wizard les importa d'aquí.
// Cap comportament seu canvia.
//
// ⚠️ L'ORDRE EL MANA EL SISTEMA, NO L'ORDRE DE CLIC (llei S24b). És el defecte que va deixar el
// model 166 amb el run `XS·S·L·XXS·M` desat tal com s'havia anat clicant.

/** Etiquetes de talla d'un SizeSystem (les tres formes que retorna l'API, en ordre de preferència). */
export const labelsOf = (sys) => (sys?.talles || [])
  .map(s => s.etiqueta || s.size_label || s.label)
  .filter(Boolean)

/** Un run és VÀLID dins un sistema si totes les seves talles hi són (subconjunt legítim, forma
 *  normal i massiva al tenant: 218 models — DIAGNOSI_MODEL_174 §B0.4). */
export const runCapDins = (run, labels) => run.length > 0 && run.every(l => labels.includes(l))

/** Ordena un run per la posició de cada talla dins del sistema. `labels` ve ja ordenat per
 *  `SizeDefinition.ordre` (el prefetch de l'API respecta el `Meta.ordering`), i per tant ordenar
 *  per la seva posició és ordenar pel sistema. Les talles que no hi són queden al final en
 *  comptes de desaparèixer. */
export const ordenaPelSistema = (run, labels) =>
  [...run].sort((a, b) => {
    const ia = labels.indexOf(a), ib = labels.indexOf(b)
    return (ia < 0 ? Infinity : ia) - (ib < 0 ? Infinity : ib)
  })
