// LES SECCIONS DEL MODEL — la llista canònica, en UN sol lloc.
//
// Vivien dins de `pages/ModelSheet.jsx`, que era l'únic que les pintava. Amb la fitxa tècnica
// entrant al bastiment comú n'hi ha un SEGON consumidor —l'editor .ftt munta el mateix menú de
// pantalla, i l'ordre d'Agus és que sigui «idèntic a Mesures/Fitting»—, i dos consumidors amb
// dues còpies és una llista que es pot contradir a si mateixa: el dia que se n'afegeixi una,
// l'editor ensenyaria un model amb una secció menys i ningú ho veuria fins que algú s'hi fixés.
//
// L'ORDRE ÉS DADA. És el recorregut del model (del panorama a l'execució) i el menú de pantalla
// el pinta tal com és; no s'ordena alfabèticament ni per gust de cap pantalla.
//
// L'ID EN CATALÀ NO ÉS UN DESCUIT: és la clau de lògica (`activeTab === 'Mesures'`, `defaultTab`,
// el `?tab=` de l'URL, i `CODE_PER_TAB` a `utils/sessioActiva.js`, que hi ancora l'obertura de
// tasca). Es tradueix l'ETIQUETA, mai la clau — canviar-la trencaria els enllaços que ja
// circulen i les tasques que hi apunten.
export const SECCIONS_MODEL = [
  'Dashboard', 'Resum', 'Mesures', 'Escalat', 'Patró', 'Fitxa tècnica',
  'Fitxers', "Registre d'activitat", 'Tasques',
]

export const ETIQUETA_SECCIO = {
  'Dashboard': 'model_sheet.tab_dashboard',
  'Tasques': 'model_sheet.tab_tasks',
  'Resum': 'model_sheet.tab_summary',
  'Mesures': 'model.tabs.mesures',
  'Escalat': 'model_sheet.tab_grading',
  'Patró': 'model_sheet.tab_pattern',
  'Fitxa tècnica': 'model_sheet.tab_tech_sheet',
  'Fitxers': 'model.tabs.fitxers',
  "Registre d'activitat": 'model_sheet.tab_activity_log',
}

/**
 * FASE A — les seccions que aquest DESPLEGAMENT ensenya.
 *
 * `SECCIONS_MODEL` segueix sent la llei: diu quines seccions té un model i en quin ordre, i no
 * es toca. El que aquesta funció retorna és una altra cosa —què es pinta AQUÍ—, i la diferència
 * entre les dues és exactament el que l'interruptor decideix.
 *
 * És PURA i rep el booleà en lloc de llegir-lo (`utils/flags.js` el llegeix un sol cop): així
 * es pot provar amb `node --test`, que no sap què és `import.meta.env`.
 *
 * Filtrar la llista TAMBÉ tanca el `?tab=Patró` de l'URL, i no per casualitat: `ModelSheet`
 * només accepta el paràmetre si la secció hi és (`TABS.includes(tabParam)`), de manera que un
 * enllaç antic cau al tab per defecte en comptes d'obrir una pantalla que aquí no existeix.
 *
 * @param {boolean} patternsEnabled  si el motor de patrons és visible en aquest desplegament
 */
export function seccionsVisibles(patternsEnabled) {
  return patternsEnabled ? SECCIONS_MODEL : SECCIONS_MODEL.filter((s) => s !== 'Patró')
}

/**
 * Les píndoles del menú de pantalla d'un model, per a `ui/PageMenu`.
 *
 * Les dues superfícies que el pinten hi arriben per camins diferents i per això `onTria` és
 * del qui crida: dins del ModelSheet, canviar de secció és canviar d'estat (no es navega);
 * des de l'editor .ftt, és SORTIR cap al model. La llista, l'ordre i les etiquetes són les
 * mateixes; el que passa en clicar, no.
 *
 * @param {(seccio: string) => void} onTria  què fa un clic (canviar de tab · navegar · sortir)
 * @param {string}   activa   la secció que s'està mirant
 * @param {Function} t        el `t()` de qui crida (les etiquetes són claus d'i18n)
 */
export function pindolesDeModel({ activa, onTria, t, seccions = SECCIONS_MODEL }) {
  return seccions.map((seccio) => ({
    key: seccio,
    label: t(ETIQUETA_SECCIO[seccio]),
    active: activa === seccio,
    onClick: () => onTria(seccio),
  }))
}
