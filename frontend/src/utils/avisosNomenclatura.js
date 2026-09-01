// ELS AVISOS D'HOMONÍMIA, DE LA RESPOSTA A LA FILA — M1194 · Decisió 8 (01/09).
//
// ── QUÈ ÉS UN AVÍS I QUÈ NO ÉS ───────────────────────────────────────────────────────────
// `gravar-pom` ja no barra el pas quan dues files es diuen igual: **desa i avisa**. El 200
// porta `avisos_nomenclatura`, i cada entrada és un ÀMBIT —no una fila i no una parella—:
// `{garment, capa, instancia, nom_fitxa, poms[], files[]}` amb dos POMs o més que comparteixen
// nom dins de la mateixa peça, capa i instància.
//
// 🚨 UN AVÍS NO ÉS UN REFÚS I NO S'HA DE PINTAR COM UN. Quan això es va escriure (01/09,
// commit 2) la cel·la de nomenclatura tenia TAMBÉ una ranura vermella (`refus`, Decisió 7) per
// al `409` de `base-measurements/<id>/noms/`, i eren dues ranures i dos colors a posta: pintar
// dues lleis diferents amb la mateixa gramàtica és la família d'errors que aquest projecte ja
// ha pagat una vegada (el comptador pintat amb la gramàtica d'un Δ).
//
// El commit 4 del mateix dia va alinear aquella porta amb la Decisió 8 i el 409 va desaparèixer,
// o sigui que la ranura vermella ja no hi és i **ara les dues fonts d'avís entren per aquí**:
// el desat en bloc de `gravar-pom` i el rebateig fila a fila del llapis. La distinció es manté
// escrita perquè el dia que algú torni a voler una porta que BARRI sàpiga que la seva marca no
// pot ser aquesta.
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


// ─────────────────────────────────────────────────────────────────────────────
// LA SEGONA FAMÍLIA — GERMANES HOMÒNIMES (01/09)
// ─────────────────────────────────────────────────────────────────────────────
//
// 🚨 NO ÉS EL MATEIX AVÍS AMB UN ALTRE NOM, i per això té funció pròpia en comptes d'un
// paràmetre a `avisDeLaFila`. L'homonímia real diu «dues mesures DIFERENTS es diuen igual dins
// del mateix àmbit»; això diu «la mateixa mesura en dues instàncies es diu igual a totes dues».
// La primera obliga a decidir quin nom canvia; la segona, a decidir si la instància val la pena.
// Un flag que triés família dins d'una sola funció seria exactament el lloc on tornarien a
// confondre's, que és el que el backend evita amb dos jutges separats.
//
// ⚠️ EL RETROBAMENT NO MIRA EL POM. Al backend el POM és indiferent per a aquesta família, i
// mirar-lo aquí faria que l'avís no trobés la fila que l'ha provocat quan les dues germanes són
// del mateix POM — que és justament el cas central.

/**
 * L'avís de germanes que parla d'AQUESTA fila, o `null`.
 *
 * Hi entra si comparteix peça i capa amb el grup, es diu igual (sense distingir caixa) i la
 * seva instància és una de les que el grup enumera. La instància buida hi compta com una més,
 * igual que al backend.
 */
export function germanaDeLaFila(germanes, fila) {
  if (!Array.isArray(germanes) || !germanes.length || !fila) return null
  return germanes.find(g => (
    eix(g.garment) === eix(fila.garment)
    && capa(g.capa) === capa(fila.capa)
    && nom(g.nom_fitxa) === nom(fila.nom_fitxa)
    && (g.instancies || []).some(i => eix(i) === eix(fila.instancia))
  )) || null
}
