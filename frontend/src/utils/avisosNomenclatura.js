// ELS AVISOS D'HOMONÍMIA, DE LA RESPOSTA A LA FILA — M1194 · Decisió 8 (01/09).
//
// ── QUÈ ÉS UN AVÍS I QUÈ NO ÉS ───────────────────────────────────────────────────────────
// `gravar-pom` ja no barra el pas quan dues files es diuen igual: **desa i avisa**. El 200
// porta `avisos_nomenclatura`, i cada entrada és un ÀMBIT —no una fila i no una parella—:
// `{garment, capa, instancia, nom_fitxa, poms[], files[]}` amb dos POMs o més que comparteixen
// nom dins de la mateixa peça, capa i instància.
//
// 🚨 UN AVÍS NO ÉS UN REFÚS I NO S'HA DE PINTAR COM UN. La cel·la de nomenclatura ja té una
// ranura vermella (`refus`, Decisió 7) per al 409 d'unicitat, que sí que barra. Pintar-hi
// l'avís faria que dues lleis diferents es llegissin igual, que és la família d'errors que
// aquest projecte ja ha pagat una vegada (el comptador pintat amb la gramàtica d'un Δ). Són
// dues ranures i dos colors a posta.
//
// ── PER QUÈ LA CAPA S'HA DE NORMALITZAR AQUÍ ─────────────────────────────────────────────
// ⚠️ L'avís torna la capa **ja normalitzada pel backend** (`_identitat_de_mesura` hi posa
// `MeasurementLayer.SLUG_DEFECTE` quan el payload no en diu res), i una fila de la pantalla la
// pot dur buida. Comparar-les crues faria que l'avís no trobés mai la seva fila i el desat
// quedés mut: es desaria l'ambigüitat i no ho sabria ningú. Es normalitza als DOS costats, amb
// el mateix literal amb què `EditableTable` fa néixer tota fila nova.
//
// Mòdul pur i sense dependències —ni tan sols l'i18n: aquí no hi ha cap text de cara a
// l'usuari, només la regla—. Es prova amb `node --test` (v. avisosNomenclatura.test.js).

/** El literal de capa que el backend dona a qui no en diu res. Ha de ser el mateix als dos. */
export const CAPA_DEFECTE = 'exterior'

const eix = (v) => (v === null || v === undefined ? '' : String(v))
const capa = (v) => (eix(v) || CAPA_DEFECTE)
const nom = (v) => eix(v).trim().toLowerCase()

/**
 * L'avís que parla d'AQUESTA fila, o `null`.
 *
 * Una fila hi entra si comparteix els TRES eixos de l'àmbit, es diu igual (sense distingir
 * caixa, com el `casefold` del backend) i el seu POM és un dels que l'avís enumera. Els tres
 * criteris junts: dos POMs del mateix àmbit poden dir-se diferent, i el mateix nom a una altra
 * peça no és cap ambigüitat.
 */
export function avisDeLaFila(avisos, fila) {
  if (!Array.isArray(avisos) || !avisos.length || !fila) return null
  return avisos.find(a => (
    eix(a.garment) === eix(fila.garment)
    && capa(a.capa) === capa(fila.capa)
    && eix(a.instancia) === eix(fila.instancia)
    && nom(a.nom_fitxa) === nom(fila.nom_fitxa)
    && (a.poms || []).some(p => String(p) === String(fila.pom_id))
  )) || null
}

/**
 * Els NOMS que l'avís afecta, per dir-ho un cop a la capçalera («B, X1»).
 *
 * Sense repeticions i en l'ordre en què el backend els ha trobat: la persona els ha de poder
 * seguir de dalt a baix contra la taula que acaba de desar.
 */
export function nomsAmbAvis(avisos) {
  const out = []
  for (const a of avisos || []) {
    const n = eix(a?.nom_fitxa).trim()
    if (n && !out.includes(n)) out.push(n)
  }
  return out
}
