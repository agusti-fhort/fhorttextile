// NOMENCLATURA VISIBLE d'un POM dins un model — resolutor ÚNIC de presentació.
//
// Pur i sense dependències: qualsevol superfície (taules de la fitxa tècnica, cotes del
// croquis, graelles) l'ha de poder cridar sense arrossegar React ni l'estat de l'editor.
//
// LA CADENA, i per què és aquesta:
//   1. `nom_fitxa` — la nomenclatura curta que el tècnic ha escrit PER A AQUEST MODEL. Mana
//      per damunt de tot: és la que ell mateix ha decidit i la que surt al croquis.
//   2. `client_alias` — com anomena la mesura el CLIENT del model (`CustomerPOMAlias`, resolt
//      al servidor per `pom/nomenclatura.py`). Brownie diu "A" on el catàleg de la casa diu
//      "CH", i el document que el tècnic té al davant diu "A".
//   3. `pom_code_global` — el codi CANÒNIC del sector. Ja no és nomenclatura de ningú en
//      particular, però és cert i és estable.
//   4. `codi_client` — el codi del catàleg de la casa. Hi és perquè la promesa és que la
//      columna NO SURT MAI BUIDA: un POM tenant-only (sense `pom_global`) no té codi canònic,
//      i una fila de mesures sense nom no es pot llegir ni anotar a mà en un fitting
//      presencial. És l'últim recurs, no el segon.
//
// ⚠️ Hi ha superfícies que encara porten una còpia EN LÍNIA amb un ordre diferent
// (`cotaLabelDe` a TechSheetEditor.jsx posa `codi_client` per davant del canònic; la taula de
// fitting T1a fa servir `pom_abbreviation`). Convergir-les és un fix a part i EN CURS; aquest
// mòdul és la casa on han d'acabar. Cap consumidor nou hauria de tornar a escriure la cadena.
export function nomenclaturaDePom(bm) {
  if (!bm) return ''
  return bm.nom_fitxa || bm.client_alias || bm.pom_code_global || bm.codi_client || ''
}
