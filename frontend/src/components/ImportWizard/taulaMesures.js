// LA TAULA DEL PAS 3 DE L'IMPORT — la lògica pura, fora del component.
//
// Per què surt d'`ImportWizard.jsx`: aquesta és la baula on el valor teclejat es converteix
// en payload, i el projecte no té harness de test de components (ni vitest ni jest). Amb la
// lògica en un mòdul pur, el runner natiu de Node la pot defensar:
//     cd frontend && node --test src/components/ImportWizard/taulaMesures.test.js
// I hi guanya una segona cosa: els DOS camins de desat (continuar i Size Library) tenien el
// mateix bucle escrit dues vegades, i ara criden la mateixa funció — no poden divergir.
//
// 🔑 LA CLAU DE FILA ÉS L'`ordre`, NO EL POM. La graella indexava per `pom_master_id`, que és
// una clau més curta que la identitat d'una fila: la fitxa BROWNIE BRUMA/RUFFLES porta B «at
// the top» 30, BB «at the bottom» 31 i B1 «stretched out» 40 —el MATEIX POM B en tres
// instàncies— i les tres files es fonien en una sola entrada. Les tres cel·les ensenyaven i
// enviaven el mateix número, sense error i sense avís.
//
// És la mateixa lliçó que `cataleg/TaulaPOMsCataleg.jsx:66` (`pom_id|capa|instancia`): la
// identitat d'una fila no és el seu POM. Aquí n'hi ha prou amb l'`ordre` perquè els eixos ja
// viuen a la fila i el backend els hereta d'allà (Onada 3) — i perquè l'`ordre` el fixa
// l'extracció i sobreviu a tot el pipeline, o sigui que és ESTABLE entre renders. Aquesta
// darrera propietat no és cosmètica: és la que permet fer-lo servir de `key` de React sense
// que els `<input>` es desmuntin i es mengin el que s'està teclejant.

/** La clau amb què la graella indexa una fila. */
export const clauDeFila = (fila) => fila.ordre

/** `{ordre: {talla: valor}}` des de les files actives i les columnes triades del document. */
export const construeixTaula = (poms, talles) => {
  const t = {}
  for (const p of (poms || []).filter(x => x.actiu)) {
    const row = {}
    for (const talla of talles) {
      const v = (p.values || {})[talla]
      row[talla] = (v === undefined || v === null) ? '' : String(v)
    }
    t[clauDeFila(p)] = row
  }
  return t
}

/** El payload del pas 3. Les cel·les buides NO s'envien (mai `null`).
 *
 *  `ordre` és ADDITIU: `pom_master_id` hi segueix, amb el mateix número de sempre, perquè un
 *  import d'un-POM-per-fila ha d'emetre exactament el que emetia. Qui mana al backend, si hi
 *  és, és l'`ordre` — i el POM el llegeix de la fila, no del payload.
 */
export const construeixMesures = (poms, talles, taula) => {
  const mesures = []
  for (const p of poms) {
    for (const talla of talles) {
      const v = taula[clauDeFila(p)]?.[talla]
      if (v !== undefined && v !== '') {
        mesures.push({ ordre: p.ordre, pom_master_id: p.pom_master_id,
                       talla_label: talla, valor: parseFloat(v) })
      }
    }
  }
  return mesures
}

/** El cos del preview de graduació: LLISTA `[{ordre, valor}]`.
 *
 *  Llista i no objecte perquè un objecte JSON no pot tenir clau composta ni repetida: amb
 *  `{pom_id: valor}` les tres files de la Brumà no hi caben. El backend respon amb la mateixa
 *  clau amb què se li pregunta i ho declara al camp `clau`.
 */
export const construeixBaseValues = (poms, taula, baseSize) => {
  const base_values = []
  for (const p of poms) {
    const v = taula[clauDeFila(p)]?.[baseSize]
    if (v !== undefined && v !== '') base_values.push({ ordre: p.ordre, valor: v })
  }
  return base_values
}

/** Omple NOMÉS les cel·les buides amb el grading rebut; preserva el que ve del document.
 *
 *  `clau` és la que el backend declara a la resposta: 'ordre' (la pregunta per fila) o
 *  'pom_master_id' (el contracte antic, que aquí es manté per no dependre de l'ordre de
 *  desplegament entre backend i SPA).
 */
export const aplicaGrading = (taula, poms, talles, grading, clau = 'ordre') => {
  const next = { ...taula }
  for (const p of poms) {
    const g = (grading || {})[String(clau === 'ordre' ? p.ordre : p.pom_master_id)] || {}
    const row = { ...(next[clauDeFila(p)] || {}) }
    for (const talla of talles) {
      if (!(row[talla] ?? '').toString().trim() && g[talla] !== undefined) row[talla] = String(g[talla])
    }
    next[clauDeFila(p)] = row
  }
  return next
}

/** Columnes sense cap valor a cap fila → són les que el grading pot omplir. */
export const columnesBuides = (poms, talles, taula) =>
  talles.filter(talla => poms.every(p => !(taula[clauDeFila(p)]?.[talla] ?? '').toString().trim()))

/** Hi ha almenys un valor a la talla base? (habilita el botó de graduar) */
export const teValorABase = (poms, taula, baseSize) =>
  poms.some(p => (taula[clauDeFila(p)]?.[baseSize] ?? '').toString().trim())

/** Quantes cel·les portaran valor (resum del pas 5). */
export const comptaValors = (poms, talles, taula) =>
  poms.reduce((acc, p) =>
    acc + talles.filter(t => (taula[clauDeFila(p)]?.[t] ?? '').toString().trim()).length, 0)
