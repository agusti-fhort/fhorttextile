import { useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { poms, pomCategories, customerAliases } from '../../api/endpoints'
import { useTraduccioPoms } from '../../utils/traduccioPomFont'
import { useEstatVocabulari, codisDe } from '../../utils/vocabulariDominiFont'
import { InfoTraduccio } from '../EditableTable/EditableTable'

// Segueix la paginació de DRF fins al final. `page_size: 1000` era un SOSTRE: amb un catàleg més
// gran, la pantalla n'hauria pintat 1000 i el comptador n'hauria dit 1000, sense que res
// indiqués que en faltaven. Un número que menteix és pitjor que una llista curta. Mateix patró
// que `Planning.jsx:86` i `Dashboard.jsx:65`.
async function totesLesPagines(apiFn, params = {}) {
  const out = []
  let page = 1
  for (;;) {
    const res = await apiFn({ ...params, page })
    const d = res.data
    out.push(...(d?.results ?? (Array.isArray(d) ? d : [])))
    if (d?.next) page++
    else return out
  }
}

// U1 · CATÀLEG DE POMs — mitja i mitja: la llista no perd context i la fitxa té espai per
// dir-ho tot (maqueta_cataleg_poms_v1). Substitueix les dues pestanyes de POM Systems: aquí
// només hi ha catàleg. El `POMBrowser` no desapareix —el consumeixen 5 pantalles més—, però
// deixa de ser una pestanya d'aquesta.
//
// ⚠️ SOBRE ELS «TAGS» DE CAPES I INSTÀNCIES. La casa té `Chip` (botó seleccionable,
// `wizardUI.jsx:25`) i `ReadChip` (caixa etiqueta/valor), i cap dels dos té el contracte d'una
// llista de tags de NOMÉS LECTURA. El `tagBase` de `RunRestrictionTags` sí que el tindria, però
// és privat i el seu fitxer cau dins la frontera dura d'aquest sprint. Aquí es fa marcatge
// LOCAL de pàgina amb tokens —no un component compartit nou, que hauria demanat aturar-se— i
// s'ANOTA al report que un `Tag` compartit és la convergència òbvia de les tres formes.

// PELL NORMA_LAYOUT v1 (A1). L'estructura —mitja i mitja, seccions de la fitxa, peu d'accions—
// no es toca: ve de la maqueta v1 ja aprovada. El que canvia és el vestit, i tot són tokens:
//   --bg-card/--bg-muted → --panel (§1: «--white: TOT panell, targeta i capçalera»; les
//     capçaleres de panell i el peu deixen de ser crema) · --border → --line · --gold-pale →
//     --sel + filet d'or (§1: el crema ja no marca selecció) · --gray → --text-faint ·
//     --text-muted → --text-soft · radis 4/5/9 → --r-ctrl i --r-card · píndoles a --r-pill.
// Mides: capçaleres de secció i de categoria a 10px (§2, mínim absolut) via --fs-label, que és
// el rol correcte —van en MAJÚSCULES amb tracking—; --fs-caption queda per al text menor.
const cx = {
  wrap: { maxWidth: 1520, margin: '0 auto' },
  split: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, alignItems: 'start' },
  box: {
    background: 'var(--panel)', border: '1px solid var(--line)',
    borderRadius: 'var(--r-card)', overflow: 'hidden',
  },
  bhead: {
    padding: '12px 16px', background: 'var(--panel)', borderBottom: '1px solid var(--line)',
    display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
  },
  // La cerca viu a la fila d'identitat, al costat del comptador (maqueta v3 `.ident .cerca`).
  cerca: {
    flex: 1, minWidth: 220, alignSelf: 'center', fontFamily: 'inherit', fontSize: 'var(--fs-body)',
    border: '1px solid var(--line)', borderRadius: 'var(--r-ctrl)', padding: '8px 12px',
    background: 'var(--panel)', color: 'var(--text-main)',
  },
  list: { maxHeight: 660, overflowY: 'auto' },
  // §8e: capçalera de llista = th 10px MAJÚSCULES tracking .08em «a tot arreu (també llistes
  // <div>)». Deixa de ser daurada: el daurat és marca i selecció, no rètol de columna.
  cat: {
    padding: '8px 16px 6px', fontSize: 'var(--fs-label)', lineHeight: '12px',
    letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-soft)',
    fontWeight: 600, background: 'var(--panel)',
    borderBottom: '1px solid var(--line-soft)', position: 'sticky', top: 0, zIndex: 2,
  },
  // 🔴 AQUÍ HI HAVIA UNA LÍNIA NEGRA DE 3px, i el codi semblava correcte.
  //
  // Deia `borderBottom: '1px solid var(--line-soft)'` … i més avall, al mateix objecte,
  // `border: 'none'` (per matar la vora d'UA del `<button>`) seguit de
  // `borderBottomStyle: 'solid'`. Les propietats s'apliquen en ORDRE DE CLAU, i una SHORTHAND
  // aplicada DESPRÉS de la seva pròpia longhand la reescriu sencera: `border: none` posa
  // l'amplada a `medium` (3px) i el color a **`currentColor`**, i el `borderBottomStyle`
  // següent tornava a fer visible això —no la vora que la línia de dalt demanava—. Amb
  // `color: 'inherit'`, `currentColor` és `--text-main`: 3px de NEGRE sota cada fila,
  // en comptes d'un filet d'1px de `--line-soft`.
  //
  // El codi no ho delata: cal MESURAR-HO (`getComputedStyle`, §8d). Ho va veure l'Agus a
  // pantalla i ho confirma `ops/qa/qa_auditoria_computats.py`.
  //
  // Fix: cap shorthand de vora ni de font. `border: 0` primer (mata la d'UA sense tocar cap
  // color), després NOMÉS les longhands del filet que volem; i `fontFamily` en comptes de
  // `font`, que és qui es menjava la mida.
  row: {
    padding: '8px 16px', cursor: 'pointer',
    display: 'flex', alignItems: 'center', gap: 12, width: '100%', textAlign: 'left',
    background: 'transparent', color: 'inherit', fontFamily: 'inherit',
    // La MIDA també s'hereta, i del document: sense això la fila computava 16px (mesurat
    // contra `.pom.on`/`.run.on` de la maqueta, que són 12). Els fills posaven la seva i per
    // això no es veia — fins que un text hi cau sense mida pròpia.
    fontSize: 'var(--fs-body)',
    border: 0,
    borderBottomWidth: 1, borderBottomStyle: 'solid', borderBottomColor: 'var(--line-soft)',
  },
  rowOn: { background: 'var(--sel)', boxShadow: 'inset 3px 0 0 var(--gold)' },
  code: { fontSize: 'var(--fs-body)', fontWeight: 600, color: 'var(--gold)', width: 78, flex: 'none' },
  nm: { fontSize: 'var(--fs-body)', flex: 1, lineHeight: 1.35 },
  ab: {
    fontSize: 'var(--fs-label)', letterSpacing: '.04em', border: '1px solid var(--line)',
    borderRadius: 'var(--r-pill)', padding: '2px 8px', color: 'var(--text-soft)',
    background: 'var(--panel)', flex: 'none',
  },
  sec: { marginTop: 16 },
  secH: {
    fontSize: 'var(--fs-label)', lineHeight: '12px', letterSpacing: '.08em',
    textTransform: 'uppercase', color: 'var(--gold)', fontWeight: 600, paddingBottom: 6,
    borderBottom: '1px solid var(--line-soft)', marginBottom: 10,
  },
  kv: {
    display: 'grid', gridTemplateColumns: '132px 1fr', gap: 8, padding: '4px 0',
    fontSize: 'var(--fs-body)', alignItems: 'baseline',
  },
  k: {
    fontSize: 'var(--fs-label)', letterSpacing: '.05em', textTransform: 'uppercase',
    color: 'var(--text-soft)',
  },
  buit: { color: 'var(--text-faint)', fontStyle: 'italic' },
  tag: {
    fontSize: 'var(--fs-label)', border: '1px solid var(--line)', borderRadius: 'var(--r-pill)',
    padding: '3px 10px', background: 'var(--panel)',
  },
  us: { display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 'var(--fs-body)' },
  usN: { fontSize: 'var(--fs-h3)', color: 'var(--gold)', fontWeight: 600 },
  usL: {
    display: 'block', fontSize: 'var(--fs-label)', letterSpacing: '.05em',
    textTransform: 'uppercase', color: 'var(--text-soft)',
  },
  ffoot: {
    padding: '12px 16px', borderTop: '1px solid var(--line)', background: 'var(--panel)',
    display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap',
  },
  note: { fontSize: 'var(--fs-label)', color: 'var(--text-soft)', flex: 1, lineHeight: 1.5 },
  // §1 (esmena Agus 08/08): TOT badge d'estat és fons suau + tinta del color + VORA FINA DEL
  // MATEIX COLOR, sense excepció. Abans n'hi havia que anaven sense filet.
  badge: {
    fontSize: 'var(--fs-label)', lineHeight: '12px', fontWeight: 600, letterSpacing: '.04em',
    padding: '3px 10px', borderRadius: 'var(--r-pill)',
  },
}

// §5 · jerarquia d'acció. Aquesta pantalla és de CONSULTA i, ara mateix, no té cap acció
// primària: «Desactivar» és terciària (reversible, de servei) i «Esborrar» és destructiva amb
// vora. Per això no hi ha cap blau — §8c ho preveu: «pantalles de CONSULTA poden tenir ZERO
// accions primàries». El daurat ple que feia de `pri` desapareix: el daurat ja no és acció.
const btn = (variant) => ({
  border: '1px solid var(--gold-border)', background: 'var(--panel)', color: 'var(--text-main)',
  borderRadius: 'var(--r-ctrl)', padding: '8px 16px', fontFamily: 'inherit',
  fontSize: 'var(--fs-body)', fontWeight: 500, cursor: 'pointer', whiteSpace: 'nowrap',
  ...(variant === 'ter' ? { borderColor: 'transparent', background: 'none', color: 'var(--text-soft)' } : null),
  ...(variant === 'dang' ? { color: 'var(--err)', borderColor: 'var(--err)' } : null),
})

// ══ ELS TRES ESTATS DEL «COM ES MESURA» (A1 · Agus, 08/08) ═══════════════════════════════
//
// Un camp buit d'aquesta fitxa no vol dir una sola cosa, i pintar-hi un guió les confonia
// totes tres en el mateix silenci. El «com es mesura» viu a `POMGlobal`, i per tant:
//
//   · DADA                     el POM està lligat i el camp té valor
//   · «NO LLIGAT»              `pom_global` és `null` → no hi ha catàleg global on mirar-ho.
//                              No és que falti la dada: és que aquest POM no en té cap font.
//   · «LLIGAT SENSE INFORMAR»  `pom_global` hi és però el camp és `''` → la font existeix i
//                              ningú l'ha omplerta. És una feina pendent d'algú, no un no-hi-ha.
//
// Les dues últimes són ACCIONS DIFERENTS per a qui llegeix: la primera es resol lligant el POM
// al catàleg, la segona omplint-lo. Un «—» no permet saber quina de les dues toca.
//
// Això només és possible perquè F2.1a va fer que els 21 camps de `pom_global` s'emetin SEMPRE
// (amb `null` quan no hi ha lligam) en comptes de desaparèixer de la resposta: sense allò, «no
// lligat» i «camp inexistent» tenien la mateixa forma —la clau absent— i no es podien distingir.
const LLIGAT = 'lligat'
const NO_LLIGAT = 'no_lligat'
const SENSE_INFORMAR = 'sense_informar'

//
// 🚨 EL 22/08 AIXÒ VA CANVIAR D'ORDRE, i no és cosmètica. El tram 3 va fer que el «com es
// mesura» sigui INFORMABLE AL TENANT: un POM sense `pom_global` ja pot dir com es pren. Amb
// el predicat vell —`pom_global == null` PRIMER— un POM propi acabat d'omplir hauria seguit
// dient «no lligat al catàleg global» amb el valor escrit al davant i invisible. Ara mana el
// VALOR: si n'hi ha, es diu; i el «per què no» només es demana quan de debò no n'hi ha.
function estatCamp(sel, valor) {
  const buit = valor === null || valor === undefined || String(valor).trim() === ''
  if (!buit) return LLIGAT
  if (sel?.pom_global == null) return NO_LLIGAT
  return SENSE_INFORMAR
}

/** El valor d'un camp del «com es mesura», o LA PARAULA que diu per què no hi és. Mai un guió. */
function ValorGlobal({ sel, valor, t }) {
  const estat = estatCamp(sel, valor)
  if (estat === LLIGAT) return <span>{valor}</span>
  return (
    <span style={cx.buit}>
      {t(estat === NO_LLIGAT ? 'poms.cat.state_unlinked' : 'poms.cat.state_uninformed')}
    </span>
  )
}

// EL CATÀLEG VA EN ANGLÈS I LA TRADUCCIÓ VIU DARRERE LA ⓘ (maqueta v3, decisió vigent). El nom
// local deixa de competir amb el canònic a la mateixa línia; qui el necessiti l'hi troba. Va a
// `title` I a `aria-label`: una icona que només parla amb el ratolí no diu res a qui no en té.
// LA ⓘ DEL CATÀLEG — la MATEIXA del sistema (tram ⓘ), no una de pròpia.
//
// Aquí n'hi havia una feta a mà amb el caràcter «ⓘ» i un `title` natiu: el mecanisme que ja es
// va diagnosticar inservible el 06/08 (només amb el ratolí a sobre, sense clic ni teclat). Ara
// és `InfoTraduccio`, per portal i amb hover + clic + focus, com a la taula de mesures.
//
// I el que hi ha a dins ja no és només `name_cat`: el catàleg v4 no en porta cap, i per això
// aquesta ⓘ no sortia MAI. Quan la casa no té nom local, es demana (`traduccio`).
function InfoLocal({ nom, traduccio }) {
  const text = nom || traduccio || ''
  if (!text) return null
  return <InfoTraduccio text={text} />
}

function Tags({ valors, buit }) {
  if (!valors?.length) return <span style={cx.buit}>{buit}</span>
  return (
    <span style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
      {valors.map(v => <span key={v} style={cx.tag}>{v}</span>)}
    </span>
  )
}

// ── S46/TRAM 4 · ELS CONTROLS DE L'EDICIÓ ──────────────────────────────────────────────────
//
// Locals a aquesta pantalla i no components compartits: la casa no té un `Field` de fitxa i
// inventar-ne un aquí seria un component nou de sistema en un sprint que no ho demana (mateixa
// decisió que els «tags» d'aquesta mateixa pàgina). S'ANOTA al report.
//
// Mateixa graella `cx.kv` que la fitxa de lectura a posta: el que s'edita ha de caure EXACTAMENT
// on estava el text, o l'ull perd la fila que estava mirant.
const campInput = {
  fontFamily: 'inherit', fontSize: 'var(--fs-body)', border: '1px solid var(--line)',
  borderRadius: 'var(--r-ctrl)', padding: '5px 9px', background: 'var(--panel)',
  color: 'var(--text-main)', width: '100%', boxSizing: 'border-box', minWidth: 0,
}

function FilaEdit({ etiqueta, valor, onCanvia, mono, ...rest }) {
  return (
    <label style={cx.kv}>
      <span style={cx.k}>{etiqueta}</span>
      <input type="text" value={valor ?? ''} onChange={e => onCanvia(e.target.value)}
        style={mono ? { ...campInput, fontFamily: 'IBM Plex Mono, monospace' } : campInput}
        {...rest} />
    </label>
  )
}

/** Un select d'enumeració de domini. Els codis van CRUS: no es tradueixen (llei d'i18n). */
function FilaTria({ etiqueta, valor, codis, onCanvia, buit }) {
  return (
    <label style={cx.kv}>
      <span style={cx.k}>{etiqueta}</span>
      {/* `codis` a null vol dir «encara no se sap», i llavors no s'ofereix res: una llista de
          reserva escrita aquí seria la segona font de veritat que `vocabulariDominiFont` mata. */}
      <select value={valor ?? ''} onChange={e => onCanvia(e.target.value)}
        style={campInput} disabled={!codis}>
        <option value="">{buit}</option>
        {(codis || []).map(c => <option key={c} value={c}>{c}</option>)}
      </select>
    </label>
  )
}

export default function POMCataleg() {
  // Sense `lang`: EL CATÀLEG VA EN ANGLÈS (maqueta v3). El nom canònic i el de la categoria
  // surten de `nom_en`, i el local viu darrere la ⓘ — no hi ha cap text que depengui de l'idioma
  // de qui mira, i per això aquesta pantalla ja no llegeix `i18n.language`.
  const { t } = useTranslation()

  const [llista, setLlista] = useState([])
  const [cats, setCats] = useState([])
  const [q, setQ] = useState('')
  const [selId, setSelId] = useState(null)
  const [us, setUs] = useState(null)
  const [alies, setAlies] = useState([])
  const [carregant, setCarregant] = useState(true)
  const [error, setError] = useState(null)
  const [ocupat, setOcupat] = useState(false)
  // S45/D — ALTA DE POM AL CATÀLEG.
  //
  // 🚨 EL CENS §D DEIA «només falta la UI del POMBrowser», i el POMBrowser **ja no té ruta**:
  // U1 (07/08) li va treure la pestanya i `/poms` renderitza AQUESTA pantalla
  // (`pages/POMs.jsx:9`). L'acta d'allà encara diu «el consumeixen 5 pantalles més» i és
  // FALS: del seu `export default` no en queda cap importador (només dos exports amb nom,
  // que se'n van a `POMCatalogue`). Posar-hi el botó hauria estat enviar-lo a una pantalla
  // morta. Va aquí, que és el catàleg viu.
  //
  // I EL FORAT ERA REAL: el catàleg sabia LLEGIR, filtrar i esborrar; l'única alta de POM del
  // producte era la del MODEL (`pom-propi`, via la taula de Mesures), que exigeix un model al
  // davant i neix lligada a un client. Sense model, no hi havia porta.
  const [crearObert, setCrearObert] = useState(false)
  // S46/TRAM 4 — L'EDICIÓ. El catàleg sabia LLEGIR, crear, desactivar i esborrar; l'única
  // cosa que NO sabia fer era CORREGIR. Un POM mal batejat per l'import s'havia de deixar
  // com era o esborrar i tornar a crear, perdent-ne l'ús. I «complementar la informació»
  // era literalment impossible fins al tram 3: el «com es mesura» només vivia al catàleg
  // GLOBAL, i el tenant no hi podia escriure ni que volgués.
  const [editant, setEditant] = useState(false)
  const [esborrany, setEsborrany] = useState(null)
  // LA ⓘ TÉ FONT (tram ⓘ). El catàleg sencer d'un cop: són 142 POMs i la petició va en lot, o
  // sigui tres crides al proveïdor el primer cop de cada idioma i cap més mai.
  const traduccioDe = useTraduccioPoms(llista.map(p => p.id))
  // ELS VOCABULARIS TANCATS del «com es mesura», de la font única (`/api/v1/vocabulari/`).
  // Llei d'Agus (08/08): cap enumeració de domini es declara al frontend. Els codis van CRUS
  // —són dades de domini, com LINEAR/STEP— i per això no passen per `t()`.
  const { voc: vocDomini, error: vocError } = useEstatVocabulari()

  const carrega = useCallback(() => {
    setCarregant(true); setError(null)
    Promise.all([
      totesLesPagines(poms.list, { page_size: 200, ordering: 'codi_client' }),
      totesLesPagines(pomCategories.list, { page_size: 200 }),
    ])
      .then(([rows, categories]) => {
        setLlista(rows)
        setCats(categories)
        setSelId(prev => (prev && rows.some(r => r.id === prev)) ? prev : (rows[0]?.id ?? null))
      })
      .catch(() => setError(t('poms.cat.load_error')))
      .finally(() => setCarregant(false))
  }, [t])

  useEffect(() => { carrega() }, [carrega])

  // EL POM NEIX SOL. `poms/crear-tenant/` el crea al catàleg del TENANT: ACTIU, sense
  // `pom_global` (el pont amb els 290 canònics de `public` és de backoffice), sense
  // `CustomerPOMAlias`, sense `GarmentPOMMap` i sense entrar a cap sembra. Posar-lo en una
  // peça és el flux ASSIGN que ja existeix, i són dos gestos a posta: crear una mesura al
  // catàleg i decidir que una peça la porta són dues decisions, sovint de dues persones.
  const crearPom = useCallback(async ({ codi, nom, categoriaId }) => {
    setError(null); setOcupat(true)
    try {
      const r = await poms.crearTenant({
        codi_client: codi, nom_client: nom, categoria_id: categoriaId || null,
      })
      setCrearObert(false)
      carrega()
      // El deixa SELECCIONAT: qui acaba de crear-lo el vol veure, i sovint completar-lo.
      if (r.data?.id) setSelId(r.data.id)
    } catch (e) {
      setError(e?.response?.data?.error || t('poms.cat.create_error'))
    } finally { setOcupat(false) }
  }, [carrega, t])

  // L'ús es demana per POM seleccionat: és el que habilita el botó d'esborrar i el que
  // omple les dues seccions d'ús observat. Una crida per fitxa, no per fila de la llista.
  useEffect(() => {
    // Canviar de POM TANCA l'edició. Arrossegar l'esborrany d'una fila a una altra és el
    // mode de fallada clàssic d'aquest patró: es desa el nom del POM anterior sobre el nou.
    setEditant(false); setEsborrany(null)
    if (!selId) { setUs(null); setAlies([]); return }
    let viu = true
    setUs(null)
    poms.us(selId).then(r => { if (viu) setUs(r.data) }).catch(() => { if (viu) setUs(null) })
    customerAliases.list({ pom: selId, page_size: 100 })
      .then(r => { if (viu) setAlies(r.data?.results ?? (Array.isArray(r.data) ? r.data : [])) })
      .catch(() => { if (viu) setAlies([]) })
    return () => { viu = false }
  }, [selId])

  // 🔑 LA CATEGORIA ÉS LA DEL CATÀLEG (`POMMaster.categoria`, un ID), NO `categoria_nom`.
  //
  // `categoria_nom` és un `SerializerMethodField` que barreja DOS vocabularis: si el POM està
  // lligat, torna `POMGlobal.categoria` (un text lliure: «TORS», «MANIGA»); si no, el `nom_ca`
  // de la `POMCategory` del tenant («Part inferior del cos»). Per això la llista mostrava
  // capçaleres en dues llengües i dues convencions alhora. Aquí es resol per ID contra
  // `/pom-categories/`, que és l'única taula que sap com es diu una categoria i en quin ordre va.
  //
  // EL CATÀLEG ÉS EN ANGLÈS (maqueta v3): `nom_en` mana i `nom_ca` només és el recanvi.
  const catPerId = useMemo(() => new Map(cats.map(c => [c.id, c])), [cats])
  const nomCat = useCallback((id) => {
    const c = catPerId.get(id)
    return c ? (c.nom_en || c.nom_ca || c.codi) : t('poms.uncategorized')
  }, [catPerId, t])

  const filtrats = useMemo(() => {
    const s = q.trim().toLowerCase()
    if (!s) return llista
    return llista.filter(p => `${p.codi_client || ''} ${p.nom_client || ''} ${p.pom_code || ''} `
      .concat(`${p.name_en || ''} ${p.name_cat || ''} ${p.categoria || ''}`).toLowerCase().includes(s))
  }, [llista, q])

  // UN BLOC PER CATEGORIA REAL, i prou.
  //
  // Això agrupava TRAMS CONSECUTIUS: com que la llista ve ordenada per `codi_client`, les
  // categories s'entrellacen i la mateixa capçalera sortia quatre vegades («MÀNIGA · 1 …
  // TORS · 1 … MÀNIGA · 1 …»). No era agrupar: era detectar canvis de valor en una llista que
  // no estava ordenada per aquell valor. Ara els blocs són tantes com categories REALS hi hagi
  // amb POMs, en el `display_order` del catàleg, i els POMs sense categoria van a un bloc final
  // —no barrejats, però tampoc amagats—.
  const grups = useMemo(() => {
    const perCat = new Map()
    for (const p of filtrats) {
      const k = p.categoria ?? null
      if (!perCat.has(k)) perCat.set(k, [])
      perCat.get(k).push(p)
    }
    const ordre = (id) => (id == null ? Infinity : (catPerId.get(id)?.display_order ?? Infinity - 1))
    return [...perCat.entries()]
      .sort((a, b) => ordre(a[0]) - ordre(b[0]) || String(nomCat(a[0])).localeCompare(String(nomCat(b[0]))))
      .map(([id, items]) => ({ catId: id, cat: nomCat(id), items }))
  }, [filtrats, catPerId, nomCat])

  const sel = useMemo(() => llista.find(p => p.id === selId) || null, [llista, selId])

  // ── L'EDICIÓ ────────────────────────────────────────────────────────────────────────
  //
  // 🚨 EN DESAR UN POM LLIGAT AL CATÀLEG GLOBAL, EL POM ES SEPARA i passa a ser del tenant
  // (decisió d'Agus, 22/08). La separació la fa el BACKEND —copy-on-write: els valors que
  // venien del global es copien al tenant abans de desfer el lligam— i **no és un camp
  // d'aquest formulari**: `pom_global` ja no és escrivible per API. Aquí només s'avisa qui
  // està a punt de fer-ho, perquè és una decisió i no un efecte secundari.
  const CAMPS_EDITABLES = [
    'codi_client', 'nom_client', 'categoria', 'unitat',
    'start_point', 'end_point', 'reference_point',
    'scope', 'orientation', 'state', 'line', 'body_section',
  ]

  const obreEdicio = () => {
    if (!sel) return
    // L'esborrany surt del que la fitxa ENSENYA, no del camp cru: per a un POM lligat, el
    // «com es mesura» que es veu és el del global, i és el que el copy-on-write conservarà.
    // Si l'esborrany naixia buit, desar hauria semblat un canvi net i hauria estat un
    // ESBORRAT silenciós de la meitat de la fitxa.
    setEsborrany(Object.fromEntries(CAMPS_EDITABLES.map(c => [c, sel[c] ?? ''])))
    setEditant(true)
  }
  const tancaEdicio = () => { setEditant(false); setEsborrany(null) }

  const desaEdicio = async () => {
    if (!sel || !esborrany) return
    setError(null); setOcupat(true)
    try {
      // NOMÉS EL QUE HA CANVIAT. Un PATCH amb els dotze camps enviaria `codi_client` a cada
      // desat i faria que la validació d'unicitat s'hagués d'excloure a ella mateixa a cada
      // volta; i, sobretot, tocar `codi_client` és el que SEPARA un POM del global. Enviar-lo
      // sense que ningú l'hagi tocat separaria POMs per desar una nota.
      const canvis = Object.fromEntries(
        CAMPS_EDITABLES.filter(c => (esborrany[c] ?? '') !== (sel[c] ?? ''))
          .map(c => [c, c === 'categoria' ? (esborrany[c] || null) : esborrany[c]]))
      if (!Object.keys(canvis).length) { tancaEdicio(); return }
      await poms.update(sel.id, canvis)
      tancaEdicio()
      carrega()
    } catch (e) {
      // El backend diu QUIN camp i per què (p. ex. «U1 ja és al catàleg»). Un missatge
      // genèric aquí taparia l'única frase que permet arreglar-ho.
      const d = e?.response?.data
      const primer = d && typeof d === 'object'
        ? Object.values(d).flat().find(Boolean) : null
      setError(primer || t('poms.cat.save_error'))
    } finally { setOcupat(false) }
  }

  const desactiva = async () => {
    if (!sel) return
    setOcupat(true)
    try { await poms.update(sel.id, { actiu: !sel.actiu }); carrega() }
    catch { setError(t('poms.cat.save_error')) }
    finally { setOcupat(false) }
  }

  const esborra = async () => {
    if (!sel || !us?.pot_esborrar) return
    if (!window.confirm(t('poms.cat.confirm_delete', { codi: sel.codi_client }))) return
    setOcupat(true)
    try { await poms.remove(sel.id); setSelId(null); carrega() }
    catch { setError(t('poms.cat.delete_error')) }
    finally { setOcupat(false) }
  }

  return (
    <div style={cx.wrap}>
      {/* §8b.3 · IDENTITAT sobre el fons, sense contenidor: comptador + etiqueta + descripció.
          El comptador és SELECCIÓ, no KPI (§8e): el primer valor segueix el filtre de cerca i
          el total va menor i suau. Substitueix el títol h2 que hi havia: el nom de l'entitat
          deixa de ser títol i passa a ser element al costat del número. */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, padding: '16px 0 12px', flexWrap: 'wrap' }}>
        <span style={{ fontSize: 'var(--fs-h1)', lineHeight: '28px', fontWeight: 600, color: 'var(--text-main)' }}>
          {filtrats.length}
          <small style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, color: 'var(--text-soft)' }}>
            /{llista.length}</small>
        </span>
        <span style={{ fontSize: 'var(--fs-label)', letterSpacing: '.08em', textTransform: 'uppercase',
                       color: 'var(--text-soft)', fontWeight: 600 }}>{t('poms.cat.title')}</span>
        {/* LA CERCA PUJA AL COSTAT DEL COMPTADOR (maqueta v3 `.ident`). No és col·locació: el
            comptador diu «13/396» i el primer número ÉS EL RESULTAT DE LA CERCA. Tenir-los
            separats obligava a mirar dalt per saber quants en queden i avall per canviar-ho, i
            a la capçalera de la llista hi havia un SEGON comptador dient el mateix número. */}
        <input style={cx.cerca} value={q} onChange={e => setQ(e.target.value)}
               placeholder={t('poms.cat.search_ph')} aria-label={t('poms.cat.search_ph')} />
      {/* ⚠️ SENSE DESCRIPCIÓ SOTA EL COMPTADOR (esmena §8e d'Agus, 08/08): «comptador + cerca i
          prou». La línia hi era —i les maquetes v3/v4 encara la dibuixen (`.ident .desc`)— però
          l'ordre és posterior a la maqueta i mana. 🚩 Les maquetes s'han d'esmenar, o el pròxim
          tram la tornarà a pintar. */}
      </div>

      {error && (
        <div role="alert" style={{
          marginBottom: 12, padding: '8px 12px', borderRadius: 'var(--r-ctrl)',
          border: '1px solid var(--err)', background: 'var(--err-bg)', color: 'var(--err)',
          fontSize: 'var(--fs-body)',
        }}>{error}</div>
      )}

      <div style={cx.split}>
        {/* ── LLISTA ── */}
        <div style={cx.box}>
          <div style={cx.bhead}>
            <span style={{ fontSize: 'var(--fs-label)', color: 'var(--text-faint)', whiteSpace: 'nowrap' }}>
              {t('poms.cat.count', { n: filtrats.length })}
            </span>
            {/* S45/D — LA PORTA D'ALTA, a la capçalera de la LLISTA i no en un menú: el moment
                en què algú descobreix que la mesura no hi és és, exactament, el moment en què
                la busca — i la cerca és tres píxels més amunt. */}
            <button type="button" onClick={() => setCrearObert(v => !v)} disabled={ocupat}
              style={{
                marginLeft: 'auto', display: 'inline-flex', alignItems: 'center', gap: 6,
                border: `1px solid ${crearObert ? 'var(--gold)' : 'var(--line)'}`,
                borderRadius: 'var(--r-ctrl)', background: 'var(--panel)',
                color: crearObert ? 'var(--gold)' : 'var(--text-soft)',
                padding: '6px 14px', cursor: ocupat ? 'wait' : 'pointer', font: 'inherit',
                fontSize: 'var(--fs-body)', whiteSpace: 'nowrap',
              }}>
              <i className="ti ti-plus" aria-hidden="true" />
              {t('poms.cat.create_new')}
            </button>
          </div>
          {crearObert && (
            <FormulariPomNou cats={cats} ocupat={ocupat} t={t}
              onCrea={crearPom} onTanca={() => setCrearObert(false)} />
          )}
          <div style={cx.list}>
            {carregant && <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-faint)', fontStyle: 'italic' }}>
              {t('poms.loading_catalogue')}</div>}
            {!carregant && !filtrats.length && (
              <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-faint)', fontStyle: 'italic' }}>
                {t('poms.no_match')}</div>
            )}
            {grups.map(g => (
              <div key={g.catId ?? 'sense'}>
                <div style={cx.cat}>{g.cat}
                  <span style={{ color: 'var(--text-faint)', letterSpacing: 0 }}> · {g.items.length}</span>
                </div>
                {g.items.map(p => (
                  <button key={p.id} type="button"
                          onClick={() => setSelId(p.id)}
                          aria-current={p.id === selId ? 'true' : undefined}
                          style={{
                            ...cx.row,
                            ...(p.id === selId ? cx.rowOn : null),
                            opacity: p.actiu ? 1 : 0.5,
                          }}>
                    <span style={cx.code}>{p.pom_code || p.codi_client}</span>
                    <span style={cx.nm}>
                      {p.name_en || p.nom_client}
                      <InfoLocal nom={p.name_cat !== p.name_en ? p.name_cat : null}
                        traduccio={traduccioDe(p.id)} />
                    </span>
                    {(p.abbreviation || p.codi_client) && (
                      <span style={cx.ab}>{p.abbreviation || p.codi_client}</span>)}
                  </button>
                ))}
              </div>
            ))}
          </div>
        </div>

        {/* ── FITXA ── */}
        <div style={cx.box}>
          {!sel && (
            <div style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--text-faint)', fontStyle: 'italic' }}>
              {t('poms.cat.pick_one')}
            </div>
          )}
          {sel && (
            <>
              <div style={{ padding: '16px', borderBottom: '1px solid var(--line)' }}>
                <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-faint)', letterSpacing: '.04em' }}>
                  {sel.pom_code || sel.codi_client} · {nomCat(sel.categoria)}
                </div>
                <div style={{ fontSize: 'var(--fs-h3)', lineHeight: '20px', fontWeight: 600, marginTop: 4 }}>
                  {sel.name_en || sel.nom_client}
                  <InfoLocal nom={sel.name_cat !== sel.name_en ? sel.name_cat : null}
                    traduccio={traduccioDe(sel.id)} /></div>
                <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
                  <span style={{
                    ...cx.badge,
                    background: sel.actiu ? 'var(--ok-bg)' : 'var(--bg-page)',
                    color: sel.actiu ? 'var(--ok)' : 'var(--text-soft)',
                    border: `1px solid ${sel.actiu ? 'var(--ok)' : 'var(--line)'}`,
                  }}>{sel.actiu ? t('poms.cat.badge_active') : t('poms.cat.badge_off')}</span>
                  {us && (
                    <span style={{
                      ...cx.badge,
                      background: us.de_sistema ? 'var(--sel)' : 'var(--bg-page)',
                      color: 'var(--text-main)',
                      border: `1px solid ${us.de_sistema ? 'var(--gold-border)' : 'var(--line)'}`,
                    }}>{us.de_sistema ? t('poms.cat.badge_system') : t('poms.cat.badge_tenant')}</span>
                  )}
                  {sel.pendent_revisio && (
                    <span style={{ ...cx.badge, background: 'var(--warn-state-bg)', color: 'var(--warn-ink)',
                      border: '1px solid var(--warn-state)' }}>
                      {t('poms.cat.badge_review')}</span>
                  )}
                </div>
              </div>

              <div style={{ padding: '0 16px 14px', maxHeight: 560, overflowY: 'auto' }}>
                <section style={cx.sec}>
                  <div style={cx.secH}>{t('poms.cat.sec_identity')}</div>
                  {/* El NOM LOCAL ja no té fila pròpia: el catàleg va en anglès i la traducció
                      viu darrere la ⓘ del nom canònic (maqueta v3, mateix patró a llista i fitxa). */}
                  {!editant && (<>
                    <div style={cx.kv}><span style={cx.k}>{t('poms.cat.f_name_en')}</span>
                      <span>{sel.name_en || sel.nom_client}
                        <InfoLocal nom={sel.name_cat !== sel.name_en ? sel.name_cat : null}
                          traduccio={traduccioDe(sel.id)} /></span></div>
                    <div style={cx.kv}><span style={cx.k}>{t('poms.cat.f_nomenclature')}</span>
                      <span>{sel.abbreviation || sel.codi_client}</span></div>
                    <div style={cx.kv}><span style={cx.k}>{t('poms.cat.f_family')}</span>
                      <span>{sel.categoria != null
                        ? nomCat(sel.categoria)
                        : <span style={cx.buit}>{t('poms.cat.no_category')}</span>}</span></div>
                    <div style={cx.kv}><span style={cx.k}>{t('poms.cat.f_unit')}</span>
                      <ValorGlobal sel={sel} valor={sel.unitat} t={t} /></div>
                  </>)}
                  {editant && (<>
                    {/* L'AVÍS DE SEPARACIÓ. Un POM lligat al catàleg global es SEPARA en desar,
                        i això és una decisió del domini, no un efecte secundari: qui l'edita ho
                        ha de saber ABANS, no descobrir-ho a la fitxa de després. */}
                    {sel.pom_global != null && (
                      <p style={{ ...cx.note, margin: '0 0 8px', color: 'var(--warn-ink)' }}>
                        {t('poms.cat.edit_will_detach')}
                      </p>
                    )}
                    <FilaEdit etiqueta={t('poms.cat.f_name_en')} valor={esborrany?.nom_client}
                      onCanvia={v2 => setEsborrany(e => ({ ...e, nom_client: v2 }))} />
                    <FilaEdit etiqueta={t('poms.cat.f_nomenclature')} mono
                      valor={esborrany?.codi_client}
                      onCanvia={v2 => setEsborrany(e => ({ ...e, codi_client: v2.toUpperCase() }))} />
                    <label style={cx.kv}>
                      <span style={cx.k}>{t('poms.cat.f_family')}</span>
                      <select style={campInput} value={esborrany?.categoria ?? ''}
                        onChange={e2 => setEsborrany(e => ({
                          ...e, categoria: e2.target.value ? Number(e2.target.value) : '' }))}>
                        <option value="">{t('poms.cat.create_category_none')}</option>
                        {cats.map(c => (
                          <option key={c.id} value={c.id}>{c.nom_en || c.nom_ca || c.codi}</option>
                        ))}
                      </select>
                    </label>
                    <FilaTria etiqueta={t('poms.cat.f_unit')} valor={esborrany?.unitat}
                      codis={codisDe(vocDomini, 'unitats_pom')} buit={t('poms.cat.edit_unset')}
                      onCanvia={v2 => setEsborrany(e => ({ ...e, unitat: v2 }))} />
                  </>)}
                </section>

                <section style={cx.sec}>
                  <div style={cx.secH}>{t('poms.cat.sec_howto')}</div>
                  {/* La CAPÇALERA de la secció diu l'estat un sol cop quan afecta tota la secció:
                      repetir cinc vegades «no lligat al catàleg global» seria cert i il·legible. */}
                  {/* La nota de secció només si NO hi ha res: un POM propi que ja ha estat
                      informat no té cap avís a donar. Mateix criteri que `estatCamp`. */}
                  {sel.pom_global == null && !sel.start_point && !sel.end_point
                    && !sel.reference_point && !sel.scope && !sel.body_section && (
                    <p style={{ ...cx.note, margin: '0 0 8px' }}>{t('poms.cat.howto_unlinked')}</p>
                  )}
                  {sel.pom_global != null && !sel.start_point && !sel.end_point
                    && !sel.reference_point && !sel.scope && !sel.body_section && (
                    <p style={{ ...cx.note, margin: '0 0 8px' }}>{t('poms.cat.howto_uninformed')}</p>
                  )}
                  {!editant && (<>
                    <div style={cx.kv}><span style={cx.k}>{t('poms.cat.f_from')}</span>
                      <ValorGlobal sel={sel} valor={sel.start_point} t={t} /></div>
                    <div style={cx.kv}><span style={cx.k}>{t('poms.cat.f_to')}</span>
                      <ValorGlobal sel={sel} valor={sel.end_point} t={t} /></div>
                    <div style={cx.kv}><span style={cx.k}>{t('poms.cat.f_reference')}</span>
                      <ValorGlobal sel={sel} valor={sel.reference_point} t={t} /></div>
                    <div style={cx.kv}><span style={cx.k}>{t('poms.cat.f_scope')}</span>
                      <ValorGlobal sel={sel}
                        valor={[sel.scope, sel.orientation, sel.state, sel.line].filter(Boolean).join(' · ')}
                        t={t} /></div>
                    <div style={cx.kv}><span style={cx.k}>{t('poms.cat.f_body')}</span>
                      <ValorGlobal sel={sel} valor={sel.body_section} t={t} /></div>
                  </>)}
                  {editant && (<>
                    {/* Si el vocabulari no arriba, els selects es queden inerts i es DIU. La
                        pantalla no s'inventa opcions (llei de `vocabulariDominiFont`). */}
                    {vocError && (
                      <p role="alert" style={{ ...cx.note, margin: '0 0 8px', color: 'var(--err)' }}>
                        {t('poms.cat.edit_vocab_error')}</p>
                    )}
                    <FilaEdit etiqueta={t('poms.cat.f_from')} valor={esborrany?.start_point}
                      onCanvia={v2 => setEsborrany(e => ({ ...e, start_point: v2 }))} />
                    <FilaEdit etiqueta={t('poms.cat.f_to')} valor={esborrany?.end_point}
                      onCanvia={v2 => setEsborrany(e => ({ ...e, end_point: v2 }))} />
                    <FilaEdit etiqueta={t('poms.cat.f_reference')} valor={esborrany?.reference_point}
                      onCanvia={v2 => setEsborrany(e => ({ ...e, reference_point: v2 }))} />
                    {/* Els quatre eixos del scope, cadascun al seu select: a la lectura van en
                        una sola línia («FULL · CURVED · FLAT · ALONG CURVE») perquè es llegeixen
                        junts, però són quatre vocabularis independents i s'editen per separat. */}
                    <FilaTria etiqueta={t('poms.cat.f_scope')} valor={esborrany?.scope}
                      codis={codisDe(vocDomini, 'scopes_pom')} buit={t('poms.cat.edit_unset')}
                      onCanvia={v2 => setEsborrany(e => ({ ...e, scope: v2 }))} />
                    <FilaTria etiqueta={t('poms.cat.f_orientation')} valor={esborrany?.orientation}
                      codis={codisDe(vocDomini, 'orientacions_pom')} buit={t('poms.cat.edit_unset')}
                      onCanvia={v2 => setEsborrany(e => ({ ...e, orientation: v2 }))} />
                    <FilaTria etiqueta={t('poms.cat.f_state')} valor={esborrany?.state}
                      codis={codisDe(vocDomini, 'estats_pom')} buit={t('poms.cat.edit_unset')}
                      onCanvia={v2 => setEsborrany(e => ({ ...e, state: v2 }))} />
                    <FilaTria etiqueta={t('poms.cat.f_line')} valor={esborrany?.line}
                      codis={codisDe(vocDomini, 'linies_pom')} buit={t('poms.cat.edit_unset')}
                      onCanvia={v2 => setEsborrany(e => ({ ...e, line: v2 }))} />
                    <FilaTria etiqueta={t('poms.cat.f_body')} valor={esborrany?.body_section}
                      codis={codisDe(vocDomini, 'seccions_cos_pom')} buit={t('poms.cat.edit_unset')}
                      onCanvia={v2 => setEsborrany(e => ({ ...e, body_section: v2 }))} />
                  </>)}
                </section>

                {/* 🔑 ÚS OBSERVAT, no política declarada (decisió Agus 07/08). El model no té
                    enlloc «quines capes admet aquest POM»; això és el que es fa servir DE DEBÒ,
                    i el text ho ha de dir amb aquestes paraules. */}
                <section style={cx.sec}>
                  <div style={cx.secH}>{t('poms.cat.sec_observed')}</div>
                  <p style={{ ...cx.note, margin: '0 0 8px' }}>{t('poms.cat.observed_help')}</p>
                  <div style={cx.kv}><span style={cx.k}>{t('poms.cat.f_layers')}</span>
                    <Tags valors={us?.observat?.capes} buit={t('poms.cat.observed_none')} /></div>
                  <div style={cx.kv}><span style={cx.k}>{t('poms.cat.f_instances')}</span>
                    <Tags valors={us?.observat?.instancies} buit={t('poms.cat.observed_none')} /></div>
                </section>

                <section style={cx.sec}>
                  <div style={cx.secH}>{t('poms.cat.sec_aliases')}</div>
                  {!alies.length && <div style={cx.buit}>{t('poms.cat.aliases_none')}</div>}
                  {alies.map(a => (
                    <div key={a.id} style={{
                      display: 'grid', gridTemplateColumns: '96px 1fr', gap: 8, padding: '4px 0',
                      fontSize: 'var(--fs-body)', borderBottom: '1px solid var(--line-soft)',
                    }}>
                      <span style={{ ...cx.k, alignSelf: 'center' }}>{a.customer_codi || a.customer}</span>
                      <span><span style={{ fontWeight: 600, color: 'var(--gold)' }}>{a.client_code}</span>{' '}
                        <span style={{ color: 'var(--text-soft)', fontSize: 'var(--fs-label)' }}>
                          {a.client_description || ''}</span></span>
                    </div>
                  ))}
                  <p style={{ ...cx.note, marginTop: 8 }}>{t('poms.cat.aliases_readonly')}</p>
                </section>

                <section style={cx.sec}>
                  <div style={cx.secH}>{t('poms.cat.sec_usage')}</div>
                  <div style={cx.us}>
                    <span><b style={cx.usN}>{us?.us?.items ?? '—'}</b>
                      <span style={cx.usL}>{t('poms.cat.u_items')}</span></span>
                    <span><b style={cx.usN}>{us?.us?.families ?? '—'}</b>
                      <span style={cx.usL}>{t('poms.cat.u_families')}</span></span>
                    <span><b style={cx.usN}>{us?.us?.grups ?? '—'}</b>
                      <span style={cx.usL}>{t('poms.cat.u_groups')}</span></span>
                    <span><b style={cx.usN}>{us?.us?.models ?? '—'}</b>
                      <span style={cx.usL}>{t('poms.cat.u_models')}</span></span>
                    <span><b style={cx.usN}>{us?.us?.rules ?? '—'}</b>
                      <span style={cx.usL}>{t('poms.cat.u_rules')}</span></span>
                  </div>
                  {!!us?.cascada?.length && (
                    <p style={{ ...cx.note, marginTop: 8, color: 'var(--warn-ink)' }}>
                      {t('poms.cat.cascade_warn', {
                        n: us.cascada.reduce((a, f) => a + f.n, 0),
                      })}
                    </p>
                  )}
                </section>
              </div>

              <div style={cx.ffoot}>
                {!editant && (<>
                  <button type="button" style={btn()} onClick={obreEdicio} disabled={ocupat}>
                    {t('poms.cat.act_edit')}
                  </button>
                  <button type="button" style={btn('ter')} onClick={desactiva} disabled={ocupat}>
                    {sel.actiu ? t('poms.cat.act_deactivate') : t('poms.cat.act_reactivate')}
                  </button>
                  <button type="button" style={btn('dang')} onClick={esborra}
                          disabled={ocupat || !us || !us.pot_esborrar}>
                    {t('poms.cat.act_delete')}
                  </button>
                  {/* La nota diu SEMPRE el motiu, la redacta el backend (és qui sap el recompte). */}
                  <span style={cx.note}>{us ? us.motiu : t('poms.cat.usage_loading')}</span>
                </>)}
                {editant && (<>
                  <button type="button" style={btn('ter')} onClick={tancaEdicio} disabled={ocupat}>
                    {t('poms.cat.create_cancel')}
                  </button>
                  <button type="button" onClick={desaEdicio} disabled={ocupat}
                    style={{
                      border: 'none', borderRadius: 'var(--r-ctrl)',
                      background: ocupat ? 'var(--line)' : 'var(--accio)',
                      color: ocupat ? 'var(--text-faint)' : 'var(--white)',
                      padding: '7px 18px', cursor: ocupat ? 'wait' : 'pointer',
                      fontFamily: 'inherit', fontSize: 'var(--fs-body)', fontWeight: 600,
                    }}>
                    {ocupat ? t('poms.cat.edit_saving') : t('poms.cat.edit_save')}
                  </button>
                  {/* L'ÚS SEGUEIX DIT MENTRE S'EDITA: un POM en 12 models i 40 regles no s'ha
                      de rebatejar a la lleugera, i és justament ara que cal saber-ho. */}
                  <span style={cx.note}>{us ? us.motiu : t('poms.cat.usage_loading')}</span>
                </>)}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

// ── S45/D · EL FORMULARI D'ALTA DE POM AL CATÀLEG ─────────────────────────────────────────
//
// QUÈ DEMANA I PER QUÈ NOMÉS AIXÒ. `POMMaster` té onze camps i només DOS són obligatoris per
// néixer: `codi_client` —únic per tenant, i **les majúscules no el distingeixen**: la
// constraint és `uniq_pommaster_codi_client_ci`— i `nom_client`. La CATEGORIA és opcional al
// model (319 dels 645 POMs de `fhort` la tenen a NULL) i s'ofereix perquè és el que fa
// TROBABLE el POM en aquesta mateixa pantalla, que agrupa per categoria: un POM sense
// categoria cau al bloc final, i el bloc final no és on ningú el busca.
//
// 🔑 CAPES, INSTÀNCIES I UNITAT NO SURTEN AQUÍ, I NO ÉS UN OBLIT: **el POM no en porta.** La
// capa i la instància viatgen amb la MESURA (`BaseMeasurement.capa/instancia/garment`, la
// unicitat de cinc camps), no amb el POM del catàleg — el mateix «CF» és el del folre i el de
// l'exterior alhora. Demanar-les en néixer seria inventar un eix que el domini no té i que
// després ningú llegiria. Les TOLERÀNCIES tampoc: neixen a 0.6 i es copien a la mesura en
// abocar-la; canviar-les és una decisió del catàleg amb la seva pantalla.
//
// EL CATÀLEG VA EN ANGLÈS (maqueta v3) i per això el camp de nom no diu «nom local»: el que
// s'hi escriu és el `nom_client`, que és el que la llista pinta.
function FormulariPomNou({ cats, ocupat, t, onCrea, onTanca }) {
  const [codi, setCodi] = useState('')
  const [nom, setNom] = useState('')
  const [categoriaId, setCategoriaId] = useState('')

  // El codi va en MAJÚSCULES a la vista perquè és com es llegeix a tot el producte. La unicitat
  // és insensible a la caixa, o sigui que això no canvia QUÈ xoca amb què: fa que el que
  // s'escriu s'assembli al que es veurà.
  const codiNet = codi.trim().toUpperCase()
  const nomNet = nom.trim()
  const pot = !!codiNet && !!nomNet && !ocupat

  const desa = () => { if (pot) onCrea({ codi: codiNet, nom: nomNet, categoriaId }) }

  const camp = {
    fontFamily: 'inherit', fontSize: 'var(--fs-body)', border: '1px solid var(--line)',
    borderRadius: 'var(--r-ctrl)', padding: '8px 12px', background: 'var(--panel)',
    color: 'var(--text-main)', width: '100%', boxSizing: 'border-box', minWidth: 0,
  }
  const retol = {
    fontSize: 'var(--fs-label)', color: 'var(--text-faint)',
    textTransform: 'uppercase', letterSpacing: '.06em',
  }

  return (
    <div style={{
      padding: '12px 16px', borderBottom: '1px solid var(--line)', background: 'var(--sel)',
      display: 'flex', flexDirection: 'column', gap: 10,
    }}>
      <p style={{ margin: 0, fontSize: 'var(--fs-caption)', color: 'var(--text-soft)' }}>
        {t('poms.cat.create_hint')}
      </p>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        <label style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: '0 0 130px' }}>
          <span style={retol}>{t('poms.cat.create_code')}</span>
          <input type="text" value={codi} autoFocus onChange={e => setCodi(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') desa() }}
            style={{ ...camp, fontFamily: 'IBM Plex Mono, monospace', textTransform: 'uppercase' }} />
        </label>
        <label style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: '1 1 200px' }}>
          <span style={retol}>{t('poms.cat.create_name')}</span>
          <input type="text" value={nom} onChange={e => setNom(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') desa() }} style={camp} />
        </label>
        <label style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: '1 1 180px' }}>
          <span style={retol}>{t('poms.cat.create_category')}</span>
          <select value={categoriaId} onChange={e => setCategoriaId(e.target.value)} style={camp}>
            <option value="">{t('poms.cat.create_category_none')}</option>
            {cats.map(c => (
              <option key={c.id} value={c.id}>{c.nom_en || c.nom_ca || c.codi}</option>
            ))}
          </select>
        </label>
      </div>
      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', alignItems: 'center' }}>
        {!pot && !ocupat && (
          <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-faint)' }}>
            {t('poms.cat.create_need_fields')}
          </span>
        )}
        <button type="button" onClick={onTanca} disabled={ocupat}
          style={{
            border: '1px solid var(--line)', borderRadius: 'var(--r-ctrl)',
            background: 'var(--panel)', color: 'var(--text-soft)', padding: '7px 16px',
            cursor: ocupat ? 'wait' : 'pointer', font: 'inherit', fontSize: 'var(--fs-body)',
          }}>{t('poms.cat.create_cancel')}</button>
        <button type="button" onClick={desa} disabled={!pot}
          style={{
            border: 'none', borderRadius: 'var(--r-ctrl)',
            background: pot ? 'var(--accio)' : 'var(--line)',
            color: pot ? 'var(--white)' : 'var(--text-faint)',
            padding: '7px 18px', cursor: pot ? 'pointer' : 'default',
            font: 'inherit', fontSize: 'var(--fs-body)', fontWeight: 600,
          }}>{ocupat ? t('poms.cat.create_saving') : t('poms.cat.create_submit')}</button>
      </div>
    </div>
  )
}
