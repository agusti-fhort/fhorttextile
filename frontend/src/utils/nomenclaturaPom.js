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
//
// TOLERÀNCIA DE CLAUS: les quatre taules de paper es nodreixen de payloads diferents i cada un
// bateja el mateix concepte amb un nom propi (`abbreviation` a graded-table, `pom_abbreviation`
// a base-measurements, `pom_code` al repàs…). El resolutor accepta la UNIÓ: convergir-hi no pot
// exigir tocar quatre serializers alhora, i afegir un sinònim aquí és una línia.
export function nomenclaturaDePom(bm) {
  if (!bm) return ''
  return bm.nom_fitxa
    || bm.client_alias
    || bm.pom_code_global
    || bm.codi_client
    || bm.pom_abbreviation || bm.abbreviation   // sinònims del codi curt segons el payload
    || bm.pom_code || bm.codi
    || ''
}

// ELS DOS NOMS LLARGS d'un POM dins un model → `{ canonic, local }`, la parella que totes les
// superfícies pinten a dues línies (nom internacional a dalt, llengua de qui llegeix a sota).
//
// LA LLEI (regla d'or, Agus 31/07): **un canvi de nom al model es veu IGUAL a la pantalla de
// mesures, al panell de cotes i a CADA taula de paper.** El BATEIG del model
// (`nom_canonic_model` / `nom_traduit_model`, editats a la cel·la del NOM de Mesures) MANA; buit
// —que és l'estat de gairebé totes les files— vol dir «no batejat» i llavors mana el catàleg,
// exactament com abans que el bateig existís.
//
// Existeix perquè la regla d'or es va trencar: el panell de cotes honorava el bateig i les
// quatre taules de la fitxa imprimien el nom vell, cadascuna amb la seva pròpia cadena en línia
// (v. DIAGNOSI_INTEGRAL_POST_CANVIS_2026-07-31 §R1). Amb el criteri en UN sol lloc, rebatejar un
// POM no pot tornar a sortir bé en una superfície i malament en una altra.
//
// `local` torna buit quan diria el mateix que `canonic`: una segona línia que repeteix la
// primera és soroll, i cada taula ho resolia pel seu compte.
export function nomsDePom(bm) {
  if (!bm) return { canonic: '', local: '' }
  const local = bm.nom_traduit_model || bm.nom_ca || bm.nom_local || bm.nom_client || ''
  const canonic = bm.nom_canonic_model || bm.nom_en || local || bm.pom_code_global || ''
  return { canonic, local: local && local !== canonic ? local : '' }
}
