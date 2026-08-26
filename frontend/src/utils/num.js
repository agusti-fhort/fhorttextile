// LA POLÍTICA DE NÚMEROS DE LA CASA — entrada tolerant, presentació per idioma. Punt únic.
//
// Decisió d'Agus (26/08), tres regles i totes tres viuen aquí:
//
//   R1 · ENTRADA TOLERANT — tot input numèric accepta el punt I la coma, indistintament.
//        Qui escriu «0,75» i qui escriu «0.75» diuen el mateix número i el sistema no els ha
//        de corregir.
//   R2 · PRESENTACIÓ PER IDIOMA DES D'UN SOL PUNT — `ca`/`es` → coma, `en` → punt. El que
//        s'acaba amb aquest mòdul és que cada component ho decideixi pel seu compte.
//   R3 · DOCUMENTS TÈCNICS SEMPRE PUNT (fitxa, PDF, Konva) — la fitxa va al fabricant i no es
//        llegeix en l'idioma de qui la va generar. **Aquest sprint NO els toca**: només s'han
//        inventariat (D0 de l'acta). `formatNum(v, { lang: 'en' })` és el que hi hauran de
//        cridar el dia que s'hi entri.
//
// ⚠️ AQUEST FITXER NO IMPORTA RES, i és la mateixa raó que `utils/diccionariMesures.js`: les
// regles pures han de poder córrer amb `node --test`, que no resol imports sense extensió ni
// sap què és React. `utils/format.js` —que sí que coneix l'i18n— hi beu i hi posa l'idioma
// actiu; qui necessiti l'idioma explícit (el paper, un export) crida directament aquí.
//
// ⚠️ I NO DUPLIQUIS LA LLEI DE LA LONGITUD. Els decimals per unitat (cm → 1, inch → 2) i la
// conversió viuen a `utils/format.js` i s'hi queden: això d'aquí és aritmètica de separadors,
// no domini de mesura.

/** Idiomes que escriuen el decimal amb COMA. La resta, punt. */
const AMB_COMA = new Set(['ca', 'es', 'fr', 'it', 'pt', 'de'])

/** `'ca-ES'` → `'ca'`. L'idioma pot arribar amb regió i la política és de LLENGUA. */
const arrel = (lang) => String(lang || '').trim().toLowerCase().slice(0, 2)

/**
 * TEXT LLIURE → NÚMERO, o `null`. La porta única d'entrada (R1).
 *
 * Accepta el punt i la coma indistintament, i també els espais (fins i tot el fi, que és el que
 * enganxa un copiar-i-enganxar d'un full de càlcul).
 *
 * ⚠️ **AMB DOS SEPARADORS DIFERENTS, L'ÚLTIM ÉS EL DECIMAL** i els altres són miler:
 * `'1.234,5'` → `1234.5` i `'1,234.5'` → `1234.5`. Amb UN de sol sempre és decimal —`'1.5'` és
 * un i mig, mai mil cinc-cents—, perquè aquí els números són mesures i deltes, no imports.
 *
 * `null`/`''`/només espais → `null`, que vol dir «buit», no «zero»: una cel·la sense mesura i
 * una cel·la amb 0 són coses diferents i el domini les distingeix.
 *
 * Brossa → `null`. No llança mai: qui crida ja té una branca per al buit i afegir-hi una
 * excepció només serviria per fer petar un `onBlur`.
 */
export function parseNum(v) {
  if (v === null || v === undefined) return null
  if (typeof v === 'number') return Number.isFinite(v) ? v : null
  // \s cobreix l'espai fi i el no-separable que porten els fulls de càlcul.
  const net = String(v).replace(/[\s  ]/g, '')
  if (net === '') return null
  const ultimPunt = net.lastIndexOf('.')
  const ultimaComa = net.lastIndexOf(',')
  let canonic
  if (ultimPunt >= 0 && ultimaComa >= 0) {
    // Tots dos presents: mana el de més a la dreta i l'altre era de miler.
    const dec = Math.max(ultimPunt, ultimaComa)
    canonic = net.slice(0, dec).replace(/[.,]/g, '') + '.' + net.slice(dec + 1)
  } else {
    canonic = net.replace(',', '.')
  }
  // `Number('')` és 0 i `Number('-')` és NaN: el buit ja ha sortit abans, i el guionet sol —un
  // estat d'edició vàlid— ha de tornar `null` i no zero. Per això la comprovació és explícita.
  if (!/^[+-]?(\d+\.?\d*|\.\d+)$/.test(canonic)) return null
  const n = Number(canonic)
  return Number.isFinite(n) ? n : null
}

/**
 * `true` si el text és un NÚMERO A MIG ESCRIURE i encara pot acabar bé.
 *
 * 🚨 AQUESTA ÉS L'ARREL DEL DEFECTE QUE AQUEST MÒDUL TANCA. L'input dels breaks parsejava a
 * CADA TECLA i es repintava amb el número que en sortia: `Number('1.')` és `1`, o sigui que el
 * separador desapareixia sota els dits i **no s'arribava mai al decimal**, ni amb punt ni amb
 * coma. L'estat `'1.'` ha d'EXISTIR mentre s'escriu; el que no pot és arribar a la BD.
 *
 * Per això la política és: **el text cru viu a l'estat, i `parseNum` s'aplica al BLUR o al
 * confirm, mai a l'`onChange`.** Aquesta funció és la que permet no pintar de vermell el que
 * només està a mitges: `''`, `'-'`, `'1.'`, `'1,'`, `'-0,'` són tots vàlids en curs.
 */
export function esNumeroEnCurs(text) {
  const net = String(text ?? '').replace(/[\s  ]/g, '')
  if (net === '') return true
  return /^[+-]?(\d*[.,]?\d*)$/.test(net)
}

/**
 * NÚMERO → TEXT en l'idioma de qui llegeix (R2).
 *
 * `dec` fixa els decimals; sense `dec`, se'n serveixen els que el número té —`0.5` surt «0,5»
 * i no «0,50»—, que és el que volen els deltes i els breaks: un `+0,50` fa pensar que algú ha
 * mesurat la centèsima.
 *
 * `null`/buit/brossa → `buit` (per defecte `''`). Qui vulgui el guionet de la casa el demana:
 * `formatNum(v, { buit: '—' })`.
 *
 * ⚠️ NO fa servir `toLocaleString`: aquell posa separador de MILER segons el locale i aquí no
 * el volem mai (un delta de graduació no arriba als mils, i una mesura amb un punt de miler
 * enmig es tornaria a llegir com un decimal en tornar a entrar al camp). Es canvia el
 * separador i prou — que és exactament tot el que la regla demana.
 */
export function formatNum(v, { dec, lang = 'ca', buit = '' } = {}) {
  const n = parseNum(v)
  if (n === null) return buit
  const text = dec === undefined || dec === null ? String(n) : n.toFixed(dec)
  return AMB_COMA.has(arrel(lang)) ? text.replace('.', ',') : text
}

/**
 * El SIGNE sempre davant (`+3` · `−1,5`), per als deltes de graduació.
 *
 * El zero no en porta: «+0» faria pensar que hi ha un increment que no hi és. El menys és el
 * MENYS TIPOGRÀFIC (U+2212) i no el guionet, que és el que ja fa `formatDelta` a `format.js`:
 * a una taula de xifres el guionet queda alt i curt i no s'alinea amb el `+`.
 */
export function formatDeltaNum(v, opcions = {}) {
  const n = parseNum(v)
  if (n === null) return opcions.buit ?? ''
  const cos = formatNum(Math.abs(n), opcions)
  return n === 0 ? cos : `${n < 0 ? '−' : '+'}${cos}`
}
