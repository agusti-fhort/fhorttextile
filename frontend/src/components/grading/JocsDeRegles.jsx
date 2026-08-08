import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { gradingRuleSets, gradingRules, sizeSystems } from '../../api/endpoints'
import PageMenu from '../ui/PageMenu'
import { useEixos } from './eixosFont'
import { useGarmentGroups } from './garmentCatalog'
import { useElements } from '../../utils/vocabulariDominiFont'
import { isDegenerateLinear } from '../../utils/gradingRegime'

// A3 · GRADING RULES — la LLISTA de jocs i la PANTALLA del joc amb dos tabs
// (maqueta_grading_rules_v4 + esmena v4.1).
//
// ⚠️ AIXÒ SUBSTITUEIX LA CASCADA. El que hi havia a `/poms/grading` era un `CascadeSelector` de
// quatre eixos que no ensenyava CAP joc fins que se n'havien triat els quatre, i llavors en
// pintava les targetes que hi casaven. La maqueta ho descarta amb aquestes paraules: «la llista
// és una llista, no mitja pantalla: hi caben totes les columnes que importen i es comparen d'un
// cop d'ull». El que la cascada responia («quin joc surt per a aquest cas») ho respon ara la
// columna «Es proposa a», que ho diu de tots els jocs alhora i sense obligar a endevinar.
// `CascadeSelector` NO s'esborra: el wizard i altres superfícies el segueixen muntant.
//
// ⚠️ ESTRUCTURA = MAQUETA (menú de pantalla → llista → «Editar» → pantalla pròpia amb tabs
// «Talles i regles» · «Relacions»); PELL = NORMA_LAYOUT v1; i el llenguatge és el de les seves
// dues germanes de Configuració tècnica (catàleg de POMs i catàleg de runs).
//
// 🔑 CARDINALITAT, QUE ÉS EL QUE DISTINGEIX AQUESTA PANTALLA DE LA DEL RUN. A `GradingRuleSet`
// només `targets` és M2M; `construction`, `fit_type` i `garment_group` són **ForeignKey** — un
// sol valor, i tornar a clicar el que ja hi és el DESDECLARA. (A `SizeSystem` les quatre capes
// són M2M: per això la Size Library va multi i aquí no.)
//
// 🔑 BUIT = «NO DECLARAT», MAI «SERVEIX A TOTHOM». Ho té escrit el backend (`pom/models.py:617`,
// `serializers.py:126`) i la diferència importa: «serveix a tothom» convida a deixar-ho buit;
// «no declarat» diu que hi falta una decisió.
//
// 🔑 EL BREAK ÉS DE LA REGLA, NO DEL JOC. `talla_break_label` i `increment_break` viuen a
// `GradingRule`. El gest de dalt (clicar una talla) es conserva perquè és el que es va ratificar
// a la v2, però és una COMODITAT que escriu a les regles que tenen Δ break — no un camp del joc.
//
// 🚩 DISTÀNCIA CAT2.1, ANOTADA I NO TANCADA AQUÍ. La maqueta diu «un joc no depèn de cap run».
// El pas (a) està fet (les regles ancoren per etiqueta i el motor hi resol), però la FK
// `GradingRuleSet.size_system` ENCARA HI ÉS i 40 de 47 jocs de `fhort` la tenen poblada — és
// d'on surten, avui, les talles de la barra de trencament. La pantalla pinta el que hi ha i ho
// DIU; retirar la FK és el pas (b) i no és d'aquest tram.

const cx = {
  wrap: { maxWidth: 1520, margin: '0 auto' },
  ident: { display: 'flex', alignItems: 'baseline', gap: 12, padding: '16px 0 12px', flexWrap: 'wrap' },
  kpi: { fontSize: 'var(--fs-h1)', lineHeight: '28px', fontWeight: 600, color: 'var(--text-main)' },
  kpiSmall: { fontSize: 'var(--fs-h3)', fontWeight: 500, color: 'var(--text-soft)' },
  lab: {
    fontSize: 'var(--fs-label)', letterSpacing: '.08em', textTransform: 'uppercase',
    color: 'var(--text-soft)', fontWeight: 600,
  },
  desc: { flexBasis: '100%', fontSize: 'var(--fs-body)', color: 'var(--text-soft)', marginTop: 4, lineHeight: 1.6 },
  box: {
    background: 'var(--panel)', border: '1px solid var(--line)',
    borderRadius: 'var(--r-card)', overflow: 'hidden',
  },
  // Amplades PER CONTINGUT (NORMA §8e), les de la maqueta: la dada reina generosa, la resta
  // ajustades. Cap columna elàstica que pugui trencar la fila en dues línies.
  grid: {
    display: 'grid', gridTemplateColumns: 'minmax(240px, 1fr) 132px 128px 92px 168px 96px',
    gap: 12, alignItems: 'center',
  },
  lhead: { padding: '8px 16px', background: 'var(--panel)', borderBottom: '1px solid var(--line)' },
  th: {
    fontSize: 'var(--fs-label)', lineHeight: '12px', letterSpacing: '.08em',
    textTransform: 'uppercase', color: 'var(--text-soft)', fontWeight: 600,
  },
  lrow: { padding: '12px 16px', borderBottom: '1px solid var(--line-soft)' },
  nm: { fontSize: 'var(--fs-body)', fontWeight: 600, color: 'var(--text-main)' },
  cd: { fontSize: 'var(--fs-label)', color: 'var(--text-soft)', letterSpacing: '.04em', marginTop: 2 },
  v: { fontSize: 'var(--fs-body)' },
  rel: { fontSize: 'var(--fs-label)', color: 'var(--text-soft)', lineHeight: 1.5 },
  // Una cel·la de fila = UNA LÍNIA amb ellipsis i el text sencer al `title` (NORMA §8e).
  tall: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  buit: { color: 'var(--text-faint)', fontStyle: 'italic' },
  badge: {
    fontSize: 'var(--fs-label)', lineHeight: '12px', fontWeight: 600, letterSpacing: '.04em',
    padding: '2px 8px', borderRadius: 'var(--r-pill)', display: 'inline-block',
  },
  shead: {
    padding: '12px 16px', background: 'var(--panel)', borderBottom: '1px solid var(--line)',
    display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
  },
  szbar: {
    padding: '12px 16px', borderBottom: '1px solid var(--line)', background: 'var(--panel)',
    display: 'flex', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap',
  },
  hint: {
    fontSize: 'var(--fs-label)', color: 'var(--text-soft)', marginLeft: 'auto',
    maxWidth: 420, lineHeight: 1.5, textAlign: 'right',
  },
  td: { padding: '4px 12px', borderBottom: '1px solid var(--line-soft)' },
  selr: {
    fontFamily: 'inherit', fontSize: 'var(--fs-body)', border: '1px solid var(--line)',
    borderRadius: 'var(--r-ctrl)', padding: '4px 8px', background: 'var(--panel)',
    color: 'var(--text-main)', width: '100%',
  },
  sfoot: {
    padding: '12px 16px', borderTop: '1px solid var(--line)', background: 'var(--panel)',
    display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap',
  },
  note: { fontSize: 'var(--fs-label)', color: 'var(--text-soft)', flex: 1, lineHeight: 1.5, minWidth: 200 },
  rblk: { marginBottom: 16 },
  rblkH: {
    fontSize: 'var(--fs-label)', lineHeight: '12px', letterSpacing: '.08em', textTransform: 'uppercase',
    color: 'var(--gold)', fontWeight: 600, paddingBottom: 8, borderBottom: '1px solid var(--line-soft)',
    marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12,
  },
  rblkEm: {
    fontStyle: 'normal', color: 'var(--text-soft)', letterSpacing: 0, textTransform: 'none',
    fontSize: 'var(--fs-label)', fontWeight: 400,
  },
  avis: {
    padding: '12px', borderRadius: 'var(--r-ctrl)', fontSize: 'var(--fs-body)',
    lineHeight: 1.6, marginBottom: 16,
  },
  prev: {
    marginTop: 8, padding: '12px 16px', border: '1px solid var(--gold-border)',
    borderLeft: '3px solid var(--gold)', borderRadius: '0 var(--r-ctrl) var(--r-ctrl) 0',
    background: 'var(--panel)',
  },
  menu: {
    position: 'absolute', right: 0, top: 'calc(100% + 4px)', zIndex: 10,
    background: 'var(--panel)', border: '1px solid var(--line)',
    borderRadius: 'var(--r-ctrl)', boxShadow: '0 6px 20px rgba(0,0,0,.10)',
    display: 'flex', flexDirection: 'column', minWidth: 200,
  },
}

// Deshabilitat: BAIXA EL FONS, NO LA TINTA (NORMA §5.7).
const off = { background: 'var(--bg-page)', borderColor: 'var(--line)', color: 'var(--text-faint)', cursor: 'default' }

// Els badges de la casa: fons suau + tinta del color + VORA FINA DEL MATEIX COLOR, sense
// excepció (esmena Agus 08/08, NORMA §1). Mai fons ple, mai color sense filet.
const BADGE = {
  ok:   { background: 'var(--ok-bg)', color: 'var(--ok)', border: '1px solid var(--ok)' },
  casa: { background: 'var(--sel)', color: 'var(--text-main)', border: '1px solid var(--gold-border)' },
  warn: { background: 'var(--warn-state-bg)', color: 'var(--warn-ink)', border: '1px solid var(--warn-state)' },
  err:  { background: 'var(--err-bg)', color: 'var(--err)', border: '1px solid var(--err)' },
  neu:  { background: 'var(--bg-page)', color: 'var(--text-soft)', border: '1px solid var(--line)' },
}

// L'ORIGEN NO ÉS UN SOL BADGE: la maqueta en dona tres formes distintes perquè les tres coses
// que diu són distintes. Canònic (viatja a un tenant nou) = verd · derivat de client (MAI viatja)
// = el neutre de la casa · importat = taronja viu · i el que ningú no ha classificat = --err,
// perquè és una decisió pendent, no un estat.
const ORIGEN = { CANONICAL: 'ok', CLIENT_RUN: 'casa', IMPORT: 'warn' }
const badgeOrigen = (origen) => BADGE[ORIGEN[origen] || 'err']

/**
 * Hover/focus amb estat de React, no amb CSS.
 *
 * Aquesta casa estila INLINE amb tokens; posar-hi classes obligaria a mantenir el CSS d'aquests
 * controls en un segon lloc. És el mateix patró —i el mateix motiu escrit— que `ui/PageMenu.jsx`.
 */
function useToc() {
  const [toc, setToc] = useState({ hover: false, focus: false })
  return [toc, {
    onMouseEnter: () => setToc(s => ({ ...s, hover: true })),
    onMouseLeave: () => setToc(s => ({ ...s, hover: false })),
    onFocus: () => setToc(s => ({ ...s, focus: true })),
    onBlur: () => setToc(s => ({ ...s, focus: false })),
  }]
}

/** Tanca amb `Esc` i amb un clic a fora. Un menú que només es tanca clicant-lo és una trampa. */
function useTancaFora(obert, tanca) {
  const ref = useRef(null)
  useEffect(() => {
    if (!obert) return undefined
    const fora = (e) => { if (ref.current && !ref.current.contains(e.target)) tanca() }
    const esc = (e) => { if (e.key === 'Escape') tanca() }
    document.addEventListener('mousedown', fora)
    document.addEventListener('keydown', esc)
    return () => {
      document.removeEventListener('mousedown', fora)
      document.removeEventListener('keydown', esc)
    }
  }, [obert, tanca])
  return ref
}

// Jerarquia d'acció (NORMA §5): secundari = blanc + vora daurada · `pri` = l'ÚNIC blau de la
// vista · `ter` = text sol · `dang` = vora vermella (mai plena en repòs).
function Boto({ variant, disabled, style, children, ...props }) {
  const [toc, gestos] = useToc()
  const base = {
    border: '1px solid var(--gold-border)', background: 'var(--panel)', color: 'var(--text-main)',
    borderRadius: 'var(--r-ctrl)', padding: variant === 'sm' ? '6px 12px' : '8px 16px',
    fontFamily: 'inherit', fontSize: 'var(--fs-body)', fontWeight: 500, cursor: 'pointer',
    whiteSpace: 'nowrap', display: 'inline-flex', alignItems: 'center', gap: 6,
  }
  const pell = {
    pri: { background: toc.hover && !disabled ? 'var(--accio-hover)' : 'var(--accio)',
           borderColor: 'transparent', color: 'var(--white)' },
    ter: { borderColor: 'transparent', background: toc.hover ? 'var(--sel)' : 'none',
           color: toc.hover ? 'var(--text-main)' : 'var(--text-soft)' },
    dang: { color: 'var(--err)', borderColor: 'var(--err)', background: toc.hover ? 'var(--err-bg)' : 'var(--panel)' },
  }[variant] || (toc.hover ? { background: 'var(--sel)' } : null)
  return (
    <button type="button" disabled={disabled} {...gestos} {...props}
            style={{
              ...base, ...pell,
              ...(disabled ? off : null),
              ...(toc.focus ? { outline: '2px solid var(--gold)', outlineOffset: 1 } : null),
              ...style,
            }}>{children}</button>
  )
}

/** Píndola commutable: capa de relació, talla de trencament, filtre. Marcada = el verd d'inclusió. */
function Xip({ on, disabled, verd, style, children, ...props }) {
  const [toc, gestos] = useToc()
  return (
    <button type="button" disabled={disabled} aria-pressed={on} {...gestos} {...props}
            style={{
              fontSize: 'var(--fs-body)', border: '1px solid var(--line)', borderRadius: 'var(--r-pill)',
              padding: '4px 12px', background: 'var(--panel)', color: 'var(--text-main)',
              // `fontFamily`, MAI la shorthand `font`: `font: 'inherit'` és una shorthand i,
              // com que les claus duplicades de JS conserven la posició de la PRIMERA, acabava
              // aplicant-se DESPRÉS del `fontSize` d'aquest mateix objecte i li menjava la mida
              // (a la Size Library això posava tots els xips a 16px en comptes de 10).
              fontFamily: 'inherit', cursor: disabled ? 'default' : 'pointer',
              ...(toc.hover && !disabled && !on ? { background: 'var(--sel)' } : null),
              // Esmena Agus 08/08 (NORMA §1): «INCLÒS en la definició» = VERD (marcar és
              // confirmar); «on soc» = --sel + filet d'or. Són dues seleccions diferents.
              ...(on && verd ? { background: 'var(--ok-bg)', borderColor: 'var(--ok)',
                                 color: 'var(--ok)', fontWeight: 600 } : null),
              ...(on && !verd ? { background: 'var(--sel)', borderColor: 'var(--gold-border)',
                                  color: 'var(--text-main)', fontWeight: 600 } : null),
              ...(disabled && !on ? { background: 'var(--bg-page)', color: 'var(--text-faint)' } : null),
              ...(toc.focus ? { outline: '2px solid var(--gold)', outlineOffset: 1 } : null),
              ...style,
            }}>{children}</button>
  )
}

/** Control de text/nombre de la casa: vora --line, radi 6, FOCUS DAURAT (NORMA §8c). */
function Camp({ style, ...props }) {
  const [toc, gestos] = useToc()
  return (
    <input {...gestos} {...props}
           style={{
             fontFamily: 'inherit', fontSize: 'var(--fs-body)', border: '1px solid var(--line)',
             borderRadius: 'var(--r-ctrl)', padding: '8px 12px', background: 'var(--panel)',
             color: 'var(--text-main)',
             ...(toc.focus ? { outline: 'none', borderColor: 'var(--gold)',
                               boxShadow: '0 0 0 3px rgba(194,122,42,.15)' } : null),
             ...style,
           }} />
  )
}

/**
 * Un desplegable del MENÚ DE PANTALLA («Nou joc ▾», «Accions ▾»).
 *
 * Va en ESTIL DE MENÚ, no de botó: §8e diu que una acció primària pujada al menú «deixa de ser
 * botó, deixa de ser blava — el blau viu al contingut; el menú té el seu llenguatge».
 */
function MenuDesplegable({ etiqueta, icona, items }) {
  const [obert, setObert] = useState(false)
  const ref = useTancaFora(obert, useCallback(() => setObert(false), []))
  const [toc, gestos] = useToc()
  return (
    <span ref={ref} style={{ position: 'relative' }}>
      <button type="button" aria-expanded={obert} onClick={() => setObert(o => !o)} {...gestos}
              style={{
                border: '1px solid transparent', borderRadius: 'var(--r-pill)',
                background: obert || toc.hover ? 'var(--sel)' : 'none', padding: '6px 14px',
                fontFamily: 'inherit', fontSize: 'var(--fs-body)', lineHeight: '16px',
                color: obert || toc.hover ? 'var(--text-main)' : 'var(--text-soft)',
                cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6,
                whiteSpace: 'nowrap',
                ...(toc.focus ? { outline: '2px solid var(--gold)', outlineOffset: 1 } : null),
              }}>
        {icona && <i className={`ti ${icona}`} aria-hidden="true" style={{ fontSize: 14 }} />}
        {etiqueta}
        <i className="ti ti-chevron-down" aria-hidden="true" style={{ fontSize: 14 }} />
      </button>
      {obert && (
        <span style={{ ...cx.menu, right: 'auto', left: 0 }}>
          {items.map(it => (
            <Boto key={it.label} variant="ter" onClick={() => { setObert(false); it.onClick() }}
                  style={{ justifyContent: 'flex-start', color: it.danger ? 'var(--err)' : 'var(--text-main)' }}>
              {it.label}
            </Boto>
          ))}
        </span>
      )}
    </span>
  )
}

/** El valor d'un input numèric: `null`/`undefined` han de deixar el camp BUIT, no escriure «null». */
const valorCamp = (v) => (v === null || v === undefined ? '' : String(v))

/** Text lliure → número o null. Accepta la coma decimal, que és com s'escriu aquí. */
function num(v) {
  if (v === null || v === undefined || String(v).trim() === '') return null
  const n = Number(String(v).replace(',', '.'))
  return Number.isFinite(n) ? n : null
}

/** Δ base d'una regla tal com es llegeix avui: forma canònica, o el camp legacy si no s'ha backfillat. */
const deltaLlegit = (r) => (r.increment_base !== null && r.increment_base !== undefined
  ? r.increment_base : r.increment)

/** true si la regla té Δ break informat — l'única que pot rebre un trencament. */
const potRebreBreak = (r) => {
  const v = r.increment_break
  return v !== null && v !== undefined && String(v) !== '' && Number(v) !== 0
}

/** El text del backend es pinta TAL QUAL: és qui sap el motiu. Només si no en diu cap, el genèric. */
function missatgeError(e, generic) {
  const d = e?.response?.data
  if (!d) return generic
  if (typeof d === 'string') return d
  if (d.detail) return String(d.detail)
  if (d.message) return String(d.message)
  const parts = Object.values(d).flat().map(String).filter(Boolean)
  return parts.length ? parts.join(' · ') : generic
}

// ── Una capa de relació ──────────────────────────────────────────────────────────────────────
// `mode='multi'` (M2M: només Target) · `mode='unic'` (FK: construcció, fit, grup). En mode únic,
// tornar a clicar el valor triat el DESDECLARA — que és l'única manera d'expressar «no declarat»
// quan el control és una llista de píndoles.
function Capa({ titol, ajuda, vocabulari, triats, mode, onTria, editable, motiuBloqueig, t }) {
  const sel = new Set(triats || [])
  return (
    <div style={cx.rblk}>
      <div style={cx.rblkH}><span>{titol}</span><em style={cx.rblkEm}>{ajuda}</em></div>
      {!vocabulari && <div style={cx.buit}>{t('grading.jocs.vocab_loading')}</div>}
      {!!vocabulari?.length && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {vocabulari.map(v => (
            <Xip key={v.codi} on={sel.has(v.codi)} verd disabled={!editable}
                 onClick={() => onTria(v.codi)}>{v.etiqueta}</Xip>
          ))}
        </div>
      )}
      {!!motiuBloqueig && <div style={{ ...cx.note, marginTop: 8, flex: 'none' }}>{motiuBloqueig}</div>}
      {/* El gest de desdeclarar només es diu quan hi ha què desdeclarar. I «no declarat» es diu
          UN cop, a l'avís de dalt i a la previsualització: repetit a cada capa, cinc vegades a la
          mateixa pantalla, deixa de llegir-se. */}
      {mode === 'unic' && !!sel.size && editable && (
        <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-soft)', marginTop: 4 }}>
          {t('grading.jocs.single_hint')}
        </div>
      )}
    </div>
  )
}

// ── El modal d'IDENTITAT ─────────────────────────────────────────────────────────────────────
// ⚠️ CONDUCTA AFEGIDA, LLISTADA AL REPORT (NORMA §9): la maqueta no dibuixa cap editor de nom,
// codi ni run — però sense ell un joc no es pot ni crear ni reanomenar, i això és una regressió
// que la pell no pot justificar. Els QUATRE EIXOS de relació NO hi són: viuen al tab
// «Relacions», que és on la maqueta els posa. Aquí només hi queda el que no té cap altra casa:
// identitat i run.
function JocModal({ joc, runs, onDesat, onError, onTanca }) {
  const { t } = useTranslation()
  const esEdicio = !!joc?.id
  const [nom, setNom] = useState(joc?.nom || '')
  const [codi, setCodi] = useState(joc?.codi_sistema || '')
  const [runId, setRunId] = useState(joc?.size_system ?? '')
  const [desant, setDesant] = useState(false)
  const ref = useTancaFora(true, onTanca)
  // Un joc AMB regles no pot canviar de run: les talla_base hi pertanyen. El guard dur viu al
  // serializer; això és l'UX que evita el 400.
  const runBloquejat = (joc?.regles_count || 0) > 0

  const desa = async () => {
    if (!nom.trim()) { onError(t('grading.name_required')); return }
    setDesant(true)
    const payload = { nom: nom.trim(), codi_sistema: codi.trim() }
    if (!esEdicio || Number(runId || 0) !== Number(joc?.size_system || 0)) {
      payload.size_system = runId ? Number(runId) : null
    }
    // D3 — EL CLON HEREDA. En creació s'arrossega el que el prefill porti (targets, eixos i
    // abast): si no s'enviés, un «Duplicar» tornaria un joc buit amb el nom del ple.
    if (!esEdicio) {
      if (joc?.targets?.length) payload.targets = joc.targets
      if (joc?.construction != null) payload.construction = joc.construction
      if (joc?.fit_type != null) payload.fit_type = joc.fit_type
      if (joc?.garment_group != null) payload.garment_group = joc.garment_group
      if (joc?.applies_to?.length) payload.applies_to = joc.applies_to
    }
    try {
      const { data } = esEdicio
        ? await gradingRuleSets.update(joc.id, payload)
        : await gradingRuleSets.create(payload)
      onDesat(data, esEdicio)
    } catch (e) {
      onError(missatgeError(e, t('grading.jocs.save_error')))
    } finally { setDesant(false) }
  }

  const label = { ...cx.lab, display: 'block', marginBottom: 4 }
  const ample = { width: '100%', boxSizing: 'border-box', display: 'block' }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,.4)', zIndex: 50,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
    }}>
      <div ref={ref} style={{
        background: 'var(--panel)', borderRadius: 'var(--r-card)', padding: 24,
        width: '100%', maxWidth: 520, maxHeight: '85vh', overflowY: 'auto',
        boxShadow: '0 12px 40px rgba(0,0,0,.18)',
      }}>
        <h2 style={{ margin: '0 0 16px', fontSize: 'var(--fs-h3)', fontWeight: 600, color: 'var(--text-main)' }}>
          {esEdicio ? t('grading.jocs.modal_edit') : t('grading.jocs.modal_new')}
        </h2>
        <div style={{ marginBottom: 16 }}>
          <label style={label} htmlFor="joc-nom">{t('grading.field_name')}</label>
          <Camp id="joc-nom" style={ample} value={nom} onChange={e => setNom(e.target.value)} />
        </div>
        <div style={{ marginBottom: 16 }}>
          <label style={label} htmlFor="joc-codi">{t('grading.field_codi')}</label>
          <Camp id="joc-codi" style={ample} value={codi} onChange={e => setCodi(e.target.value)} />
        </div>
        <div style={{ marginBottom: 16 }}>
          <label style={label} htmlFor="joc-run">{t('grading.jocs.field_run')}</label>
          <select id="joc-run" style={{ ...cx.selr, ...ample, padding: '8px 12px' }}
                  value={runId ?? ''} disabled={runBloquejat}
                  onChange={e => setRunId(e.target.value)}>
            <option value="">{t('grading.jocs.run_none')}</option>
            {runs.map(r => <option key={r.id} value={r.id}>{r.codi} · {r.nom}</option>)}
          </select>
          <p style={{ ...cx.note, flex: 'none', margin: '4px 0 0' }}>
            {runBloquejat
              ? t('grading.size_system_locked', { count: joc.regles_count })
              : t('grading.jocs.run_help')}
          </p>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
          <Boto variant="ter" onClick={onTanca}>{t('app.cancel')}</Boto>
          <Boto variant="pri" disabled={desant} onClick={desa}>
            {desant ? t('common.saving') : (esEdicio ? t('app.save') : t('app.create'))}
          </Boto>
        </div>
      </div>
    </div>
  )
}

// ── LA PANTALLA D'UN JOC ─────────────────────────────────────────────────────────────────────
function Joc({ joc, run, vocabularis, regimsAutorables, accions, onTanca, onCanviat, onError }) {
  const { t } = useTranslation()
  const [tab, setTab] = useState('regles')
  // 🔴 EL MAP DE LA LLEI (mateix patró que `GraduacioSuperficie`): neix buit i només hi entra el
  // que un gest humà canvia. Sense això, «Gravar» hauria de decidir què ha canviat comparant, i
  // una comparació de decimals amb strings escriu files que ningú no ha tocat.
  const [edicions, setEdicions] = useState(new Map())
  // ⚠️ ESTAT INICIAL, NO SINCRONITZAT. El component es remunta amb `key={joc.id}` en canviar de
  // joc, i a partir d'aquí la còpia local mana: una recàrrega de la LLISTA (que passa cada cop
  // que es desa) no ha de poder trepitjar el que s'està editant en aquesta pantalla.
  const [regles, setRegles] = useState(() => joc.regles || [])
  const [gravant, setGravant] = useState(false)
  // {targets, construction, fit, grup} en CODIS
  const [relacions, setRelacions] = useState(() => ({
    targets: [...(joc.targets_codis || [])],
    construction: joc.construction_codi || null,
    fit: joc.fit_type_codi || null,
    grup: joc.garment_group_codi || null,
  }))

  const teAbastPerNodes = !!joc.applies_to?.length
  // F-5 — un seed ISO (`is_system_default`) NO pot canviar d'eixos. El guard dur viu al
  // serializer; aquí es diu per què el control no respon.
  const eixosEditables = !joc.is_system_default

  // El valor VIU d'un camp: l'edició si n'hi ha, i si no el que va arribar de l'API.
  const viu = useCallback((r, camp) => {
    const e = edicions.get(r.id)
    return e && camp in e ? e[camp] : r[camp]
  }, [edicions])

  const edita = (id, patch) => setEdicions(prev => {
    const nou = new Map(prev)
    nou.set(id, { ...(nou.get(id) || {}), ...patch })
    return nou
  })

  // EL GEST DE LA BARRA DE TALLES, tal com es va ratificar a la v2 i com l'esmena la v4.1:
  // marca el trencament a totes les regles que TENEN Δ break. Les que no en tenen no en reben
  // cap — el break sense valor no vol dir res.
  const marcaBreak = (etiqueta) => {
    const candidates = regles.filter(r => potRebreBreak({ ...r, ...(edicions.get(r.id) || {}) }))
    if (!candidates.length) return
    const jaHi = candidates.some(r => viu(r, 'talla_break_label') === etiqueta)
    setEdicions(prev => {
      const nou = new Map(prev)
      for (const r of candidates) {
        nou.set(r.id, { ...(nou.get(r.id) || {}), talla_break_label: jaHi ? null : etiqueta })
      }
      return nou
    })
  }

  const gravaRegles = async () => {
    if (!edicions.size) return
    setGravant(true)
    try {
      const desades = []
      for (const [id, patch] of edicions) {
        const { data } = await gradingRules.update(id, patch)
        desades.push(data)
      }
      setRegles(prev => prev.map(r => desades.find(d => d.id === r.id) || r))
      setEdicions(new Map())
      onCanviat({ tipus: 'regles', n: desades.length })
    } catch (e) {
      onError(missatgeError(e, t('grading.jocs.save_error')))
    } finally { setGravant(false) }
  }

  const treuRegla = async (r) => {
    if (!window.confirm(t('grading.confirm_deactivate'))) return
    try {
      await gradingRules.remove(r.id)
      setRegles(prev => prev.filter(x => x.id !== r.id))
      onCanviat({ tipus: 'regla_treta' })
    } catch (e) { onError(missatgeError(e, t('grading.jocs.save_error'))) }
  }

  const gravaRelacions = async () => {
    setGravant(true)
    const idDe = (llista, codi) => (llista || []).find(x => x.codi === codi)?.id ?? null
    try {
      const payload = {
        targets: (relacions.targets || []).map(c => idDe(vocabularis.targetRaw, c)).filter(v => v != null),
        construction: idDe(vocabularis.constrRaw, relacions.construction),
        fit_type: idDe(vocabularis.fitRaw, relacions.fit),
      }
      // ⚠️ D1 · UNA SOLA FONT D'ABAST. Si el joc declara l'abast per NODES (`scope_nodes`), el seu
      // `garment_group` és NULL a posta i escriure'l aquí crearia la segona font que la
      // convergència per atrició va tancar. En aquest cas el camp no s'envia i el bloc va bloquejat.
      if (!teAbastPerNodes) payload.garment_group = idDe(vocabularis.grupRaw, relacions.grup)
      const { data } = await gradingRuleSets.update(joc.id, payload)
      // El que mana és el que el backend torna: si ha normalitzat res, es veu de seguida.
      setRelacions({
        targets: [...(data.targets_codis || [])],
        construction: data.construction_codi || null,
        fit: data.fit_type_codi || null,
        grup: data.garment_group_codi || null,
      })
      onCanviat({ tipus: 'relacions', joc: data })
    } catch (e) {
      onError(missatgeError(e, t('grading.jocs.save_error')))
    } finally { setGravant(false) }
  }

  const talles = useMemo(
    () => [...(run?.talles || [])].sort((a, b) => (a.ordre ?? 0) - (b.ordre ?? 0)), [run])
  const ambBreak = regles.filter(r => {
    const v = viu(r, 'talla_break_label')
    return v !== null && v !== undefined && String(v).trim() !== ''
  }).length
  const potBreak = regles.filter(r => potRebreBreak({ ...r, ...(edicions.get(r.id) || {}) })).length

  const previsualitzacio = useMemo(() => {
    const et = (llista, codi) => (llista || []).find(x => x.codi === codi)?.etiqueta || codi
    const parts = []
    if (relacions.targets?.length) {
      parts.push(t('grading.jocs.prev_target', {
        v: relacions.targets.map(c => et(vocabularis.target, c)).join(' · ') }))
    }
    if (relacions.construction) parts.push(t('grading.jocs.prev_constr', { v: et(vocabularis.construccio, relacions.construction) }))
    if (relacions.fit) parts.push(t('grading.jocs.prev_fit', { v: et(vocabularis.fit, relacions.fit) }))
    if (relacions.grup) parts.push(t('grading.jocs.prev_group', { v: et(vocabularis.grup, relacions.grup) }))
    return parts.length ? t('grading.jocs.prev_intro', { parts: parts.join(', ') }) : ''
  }, [relacions, vocabularis, t])

  const triaUnica = (camp, codi) =>
    setRelacions(r => ({ ...r, [camp]: r[camp] === codi ? null : codi }))
  const commutaTarget = (codi) => setRelacions(r => ({
    ...r,
    targets: r.targets.includes(codi) ? r.targets.filter(c => c !== codi) : [...r.targets, codi],
  }))

  const badges = [
    joc.actiu !== false ? { k: 'ok', txt: t('grading.jocs.badge_active') } : { k: 'neu', txt: t('grading.jocs.badge_retired') },
    joc.origen
      ? { k: ORIGEN[joc.origen] || 'err', txt: t(`grading.jocs.origen_short_${joc.origen}`).toUpperCase() }
      : { k: 'err', txt: t('grading.jocs.badge_no_origen') },
    ...(joc.is_system_default ? [{ k: 'casa', txt: t('grading.system') }] : []),
    ...(!regles.length ? [{ k: 'warn', txt: t('grading.jocs.badge_no_rules') }] : []),
  ]

  return (
    <div style={cx.wrap}>
      <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-soft)', padding: '16px 0 8px' }}>
        <Boto variant="ter" onClick={onTanca}
              style={{ padding: 0, color: 'var(--gold)', fontSize: 'var(--fs-label)' }}>
          <i className="ti ti-arrow-left" aria-hidden="true" style={{ fontSize: 14 }} />
          {t('grading.jocs.back_to_list')}
        </Boto>
        {' › '}<b style={{ color: 'var(--text-main)' }}>{joc.nom}</b>
      </div>

      <div style={cx.box}>
        <div style={cx.shead}>
          <span>
            <span style={{ fontSize: 'var(--fs-h3)', lineHeight: '20px', fontWeight: 600 }}>{joc.nom}</span>
            {' '}
            <span style={{ fontSize: 'var(--fs-label)', color: 'var(--text-soft)' }}>
              {joc.codi_sistema || t('grading.jocs.no_code')}
            </span>
          </span>
          <span style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {badges.map(b => <span key={b.txt} style={{ ...cx.badge, ...BADGE[b.k] }}>{b.txt}</span>)}
          </span>
          {/* NORMA §5.6 — «Accions ⋯» és UN menú, no quatre botons: són ocasionals (duplicar,
              jubilar, esborrar, identitat), mai passos de flux. */}
          <span style={{ marginLeft: 'auto' }}>
            <MenuDesplegable etiqueta={t('grading.jocs.actions')} items={accions || []} />
          </span>
          {/* Germanes dins d'un panell = TABS AMB SUBRATLLAT D'OR (NORMA §8b-bis), no caixetes. */}
          <span style={{ display: 'flex', gap: 4, flexBasis: '100%' }}>
            {[['regles', t('grading.jocs.tab_rules')], ['relacions', t('grading.jocs.tab_relations')]].map(([k, txt]) => (
              <Boto key={k} variant="ter" onClick={() => setTab(k)}
                    aria-current={tab === k ? 'true' : undefined}
                    style={{
                      borderRadius: 0,
                      borderBottom: `2px solid ${tab === k ? 'var(--gold)' : 'transparent'}`,
                      color: tab === k ? 'var(--text-main)' : 'var(--text-soft)',
                      fontWeight: tab === k ? 600 : 400,
                    }}>{txt}</Boto>
            ))}
          </span>
        </div>

        {tab === 'regles' && (
          <>
            <div style={cx.szbar}>
              <span>
                <span style={{ ...cx.lab, display: 'block', marginBottom: 4 }}>
                  {t('grading.jocs.sizes_covered')}
                </span>
                {!talles.length && (
                  <span style={cx.buit}>
                    {run ? t('grading.jocs.run_no_sizes') : t('grading.jocs.no_run')}
                  </span>
                )}
                <span style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {talles.map(s => {
                    const marcada = regles.some(r => viu(r, 'talla_break_label') === s.etiqueta)
                    return (
                      // El trencament NO és inclusió: és «on soc» de la barra → --sel + filet d'or.
                      <Xip key={s.id ?? s.etiqueta} on={marcada} disabled={!potBreak}
                           onClick={() => marcaBreak(s.etiqueta)}
                           title={potBreak ? t('grading.jocs.mark_break') : t('grading.jocs.no_break_candidates')}
                           style={{
                             borderRadius: 'var(--r-ctrl)', fontVariantNumeric: 'tabular-nums',
                             ...(marcada ? { boxShadow: 'inset 0 -2px 0 var(--gold)' } : null),
                           }}>{s.etiqueta}</Xip>
                    )
                  })}
                </span>
              </span>
              {/* 🚩 CAT2.1 · el text diu la VERITAT D'AVUI, no la del pas (b). */}
              <span style={cx.hint}>
                {run ? t('grading.jocs.sizes_hint', { run: run.codi }) : t('grading.jocs.sizes_hint_norun')}
              </span>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ borderCollapse: 'separate', borderSpacing: 0, width: '100%',
                              fontSize: 'var(--fs-body)', tableLayout: 'fixed' }}>
                <colgroup>
                  <col style={{ width: 44 }} /><col style={{ width: 152 }} /><col />
                  <col style={{ width: 168 }} /><col style={{ width: 112 }} />
                  <col style={{ width: 120 }} /><col style={{ width: 112 }} /><col style={{ width: 52 }} />
                </colgroup>
                <thead>
                  <tr>
                    {[
                      ['#', 'left'], [t('grading.col.code'), 'left'], [t('grading.col.pom_name'), 'left'],
                      [t('grading.jocs.col_regime'), 'left'], [t('grading.jocs.col_delta'), 'right'],
                      [t('grading.col.delta_break'), 'right'], [t('grading.jocs.col_break_size'), 'right'], ['', 'left'],
                    ].map(([txt, al], i) => (
                      <th key={i} style={{
                        ...cx.th, padding: '8px 12px', textAlign: al, background: 'var(--panel)',
                        borderBottom: '1px solid var(--line)',
                      }}>{txt}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {!regles.length && (
                    <tr><td colSpan={8} style={{ ...cx.td, padding: 24, textAlign: 'center',
                                                 ...cx.buit, lineHeight: 1.9 }}>
                      <b style={{ color: 'var(--text-soft)', display: 'block', fontSize: 'var(--fs-body)',
                                  fontStyle: 'normal' }}>
                        {t('grading.jocs.empty_rules_title')}</b>
                      {t('grading.jocs.empty_rules_body')}
                    </td></tr>
                  )}
                  {regles.map((r, i) => {
                    const logica = viu(r, 'logica')
                    // Valors de DADA (LINEAR/STEP/FIXED/ZERO/EXCEPTION): NO es tradueixen.
                    // El desplegable ofereix els AUTORABLES + el que la fila ja porta: poder-lo
                    // llegir i poder-lo triar no són la mateixa pregunta (coda F2.2).
                    const opcions = [...new Set([...(regimsAutorables || []), logica].filter(Boolean))]
                    const editada = edicions.get(r.id)
                    const degenerada = isDegenerateLinear({ ...r, ...(editada || {}) })
                    // ⚠️ EL BUIT S'HA DE PODER ESCRIURE. Amb `viu(…) ?? deltaLlegit(r)` un camp
                    // esborrat tornava a omplir-se sol amb el valor de la BD i no hi havia manera
                    // de deixar-lo a null: si la fila ja s'ha tocat mana l'edició tal com és
                    // —`null` inclòs—; només si no s'ha tocat es llegeix la dada.
                    const deltaVal = editada && 'increment_base' in editada
                      ? editada.increment_base : deltaLlegit(r)
                    return (
                      // ⚠️ CONDUCTA AFEGIDA (llistada): la fila amb canvis PENDENTS DE DESAR porta
                      // un filet taronja. No fa servir `--sel`: `--sel` és «on soc» i el verd és
                      // «inclòs» (§1), i «pendent» és una tercera cosa. El taronja és marca de
                      // dada, que és exactament el que això és.
                      <tr key={r.id} style={editada
                        ? { boxShadow: 'inset 3px 0 0 var(--warn-state)' } : undefined}>
                        <td style={{ ...cx.td, color: 'var(--text-faint)' }}>{i + 1}</td>
                        <td style={{ ...cx.td, ...cx.tall, color: 'var(--gold)', fontWeight: 600 }}
                            title={r.pom_abbreviation || r.pom_codi || ''}>
                          {r.pom_abbreviation || r.pom_codi}
                        </td>
                        <td style={{ ...cx.td, ...cx.tall, color: 'var(--text-main)' }}
                            title={r.pom_nom_en || r.pom_nom || ''}>
                          {r.pom_nom_en || r.pom_nom || ''}
                        </td>
                        <td style={cx.td}>
                          <select style={cx.selr} value={logica || ''}
                                  aria-label={t('grading.jocs.col_regime')}
                                  onChange={e => edita(r.id, { logica: e.target.value })}>
                            {opcions.map(o => <option key={o} value={o}>{o}</option>)}
                          </select>
                          {/* ⚠️ CONDUCTA AFEGIDA (llistada): LINEAR+0 sense break no gradua res i
                              es presenta com a FIXED a tota la casa (`gradingRegime.js`). El
                              desplegable segueix dient el que hi ha DESAT —reinterpretar-lo sota
                              els dits li canviaria la tria a qui l'està escrivint—, i el que
                              avisa és aquesta marca. */}
                          {degenerada && (
                            <span style={{ fontSize: 'var(--fs-label)', color: 'var(--text-soft)', marginLeft: 6 }}
                                  title={t('grading.jocs.degenerate_help')}>
                              {t('grading.jocs.degenerate')}
                            </span>
                          )}
                        </td>
                        <td style={{ ...cx.td, textAlign: 'right' }}>
                          <Camp inputMode="decimal" aria-label={t('grading.jocs.col_delta')}
                                value={valorCamp(deltaVal)} placeholder="—"
                                style={{ width: 76, textAlign: 'right', fontWeight: 600, padding: '4px 8px',
                                         fontVariantNumeric: 'tabular-nums' }}
                                onChange={e => edita(r.id, { increment_base: num(e.target.value) })} />
                        </td>
                        <td style={{ ...cx.td, textAlign: 'right' }}>
                          <Camp inputMode="decimal" aria-label={t('grading.col.delta_break')}
                                value={valorCamp(viu(r, 'increment_break'))} placeholder="—"
                                style={{ width: 76, textAlign: 'right', fontWeight: 600, padding: '4px 8px',
                                         fontVariantNumeric: 'tabular-nums' }}
                                onChange={e => edita(r.id, { increment_break: num(e.target.value) })} />
                        </td>
                        {/* La talla de trencament es MARCA a la barra de dalt; aquí es LLEGEIX
                            la de la seva fila, que és el que la v4.1 va corregir. */}
                        <td style={{ ...cx.td, textAlign: 'right', color: 'var(--text-soft)' }}>
                          {viu(r, 'talla_break_label') || '—'}
                        </td>
                        <td style={cx.td}>
                          <Boto variant="ter" onClick={() => treuRegla(r)}
                                title={t('grading.deactivate')} aria-label={t('grading.deactivate')}
                                style={{ padding: '2px 6px' }}>
                            <i className="ti ti-x" aria-hidden="true" style={{ fontSize: 14 }} />
                          </Boto>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            <div style={cx.sfoot}>
              {/* 🛑 BLOQUEJAT, I EL BOTÓ HO DIU. `GradingRuleSerializer` té `rule_set` com a
                  read_only: un POST a /grading-rules/ no pot dir a quin joc va, i `talla_base`
                  és FK obligatòria. Afegir un POM demana backend, no pell — v. el report. */}
              <Boto disabled title={t('grading.jocs.add_pom_blocked')}>
                <i className="ti ti-plus" aria-hidden="true" style={{ fontSize: 14 }} />
                {t('grading.jocs.add_pom')}
              </Boto>
              {/* Sense cap regla, el que s'ha de dir NO és què passa amb el trencament (seria
                  cert i buit): és per què el botó de dalt no respon. */}
              <span style={cx.note}>
                {!regles.length ? t('grading.jocs.add_pom_blocked')
                  : ambBreak ? t('grading.jocs.note_break', { count: ambBreak, total: regles.length })
                    : t('grading.jocs.note_no_break')}
              </span>
              <Boto onClick={onTanca}>{t('grading.jocs.back')}</Boto>
              <Boto variant="pri" onClick={gravaRegles} disabled={!edicions.size || gravant}>
                {gravant ? t('common.saving') : t('grading.jocs.save_rules')}
              </Boto>
            </div>
          </>
        )}

        {tab === 'relacions' && (
          <>
            <div style={{ padding: 16 }}>
              <div style={{ ...cx.avis, ...BADGE.casa }}>{t('grading.jocs.relations_notice')}</div>
              <Capa titol={t('grading.jocs.layer_target')} ajuda={t('grading.jocs.layer_target_help')}
                    vocabulari={vocabularis.target} triats={relacions.targets} mode="multi"
                    onTria={commutaTarget} editable={eixosEditables} t={t}
                    motiuBloqueig={eixosEditables ? null : t('grading.modal_note')} />
              <Capa titol={t('grading.jocs.layer_construction')} ajuda={t('grading.jocs.layer_single_help')}
                    vocabulari={vocabularis.construccio} triats={relacions.construction ? [relacions.construction] : []}
                    mode="unic" onTria={c => triaUnica('construction', c)} editable={eixosEditables} t={t} />
              <Capa titol={t('grading.jocs.layer_fit')} ajuda={t('grading.jocs.layer_fit_help')}
                    vocabulari={vocabularis.fit} triats={relacions.fit ? [relacions.fit] : []}
                    mode="unic" onTria={c => triaUnica('fit', c)} editable={eixosEditables} t={t} />
              <Capa titol={t('grading.jocs.layer_group')} ajuda={t('grading.jocs.layer_group_help')}
                    vocabulari={vocabularis.grup} triats={relacions.grup ? [relacions.grup] : []}
                    mode="unic" onTria={c => triaUnica('grup', c)}
                    editable={eixosEditables && !teAbastPerNodes} t={t}
                    motiuBloqueig={teAbastPerNodes
                      ? t('grading.jocs.scope_nodes_note', {
                        nodes: joc.applies_to.map(n => n.group_codi
                          || (n.garment_type_item_id ? `#${n.garment_type_item_id}` : `#${n.garment_type_id}`))
                          .join(' · '),
                      })
                      : null} />
              <div style={cx.prev}>
                <div style={{ ...cx.th, marginBottom: 8 }}>{t('grading.jocs.prev_title')}</div>
                <div style={{ fontSize: 'var(--fs-body)', lineHeight: 1.9 }}>
                  {previsualitzacio || t('grading.jocs.prev_empty')}
                </div>
              </div>
            </div>
            <div style={cx.sfoot}>
              <span style={cx.note}>{t('grading.jocs.relations_foot')}</span>
              <Boto onClick={onTanca}>{t('grading.jocs.back')}</Boto>
              <Boto variant="pri" onClick={gravaRelacions} disabled={gravant || !eixosEditables}>
                {gravant ? t('common.saving') : t('grading.jocs.save_relations')}
              </Boto>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

// ── LA PANTALLA ──────────────────────────────────────────────────────────────────────────────
export default function JocsDeRegles({ onImportar }) {
  const { t } = useTranslation()
  const [jocs, setJocs] = useState([])
  const [runs, setRuns] = useState([])
  const [q, setQ] = useState('')
  const [veureActius, setVeureActius] = useState(true)
  const [obertId, setObertId] = useState(null)
  const [carregant, setCarregant] = useState(true)
  const [msg, setMsg] = useState(null)
  const [modal, setModal] = useState(null)       // {joc} · joc.id null = creació/clon

  const { targets, constructions, fits } = useEixos()
  const grups = useGarmentGroups()
  // Els règims que un tècnic pot TRIAR els diu l'endpoint (`autorable`), no aquesta pantalla:
  // ZERO i EXCEPTION queden fora de l'autoria. Sense vocabulari la llista va buida i el
  // desplegable d'una fila només ofereix el règim que la fila ja porta.
  const { elements: vocRegims } = useElements('regims_graduacio')
  const regimsAutorables = useMemo(
    () => (vocRegims || []).filter(r => r.autorable).map(r => r.codi), [vocRegims])

  const carrega = useCallback(async (mantenirObert) => {
    setCarregant(true)
    try {
      const out = []
      for (let page = 1; ; page++) {
        const { data } = await gradingRuleSets.list({ page_size: 200, page })
        out.push(...(data?.results ?? (Array.isArray(data) ? data : [])))
        if (!data?.next) break
      }
      setJocs(out)
      if (mantenirObert && !out.some(j => j.id === mantenirObert)) setObertId(null)
    } catch (e) {
      setMsg({ type: 'err', text: missatgeError(e, t('grading.jocs.load_error')) })
    } finally { setCarregant(false) }
  }, [t])

  useEffect(() => { carrega() }, [carrega])

  // Els RUNS, una vegada: són d'on surten avui les talles d'un joc (`size_system`) i el
  // desplegable del modal. 🚩 Aquesta dependència és, literalment, la distància CAT2.1.
  useEffect(() => {
    let viu = true
    const totes = async () => {
      const out = []
      for (let page = 1; ; page++) {
        const { data } = await sizeSystems.list({ page_size: 200, page })
        out.push(...(data?.results ?? (Array.isArray(data) ? data : [])))
        if (!data?.next) return out
      }
    }
    totes().then(rows => { if (viu) setRuns(rows) }).catch(() => { if (viu) setRuns([]) })
    return () => { viu = false }
  }, [])

  const runsPerId = useMemo(() => Object.fromEntries(runs.map(r => [r.id, r])), [runs])

  const vocabularis = useMemo(() => ({
    target: targets?.map(x => ({ codi: x.codi, etiqueta: x.nom_en })) ?? null,
    construccio: constructions?.map(x => ({ codi: x.codi, etiqueta: x.nom_en })) ?? null,
    fit: fits?.map(x => ({ codi: x.codi, etiqueta: x.nom_en })) ?? null,
    grup: grups?.length ? grups.map(x => ({ codi: x.codi, etiqueta: x.nom_en })) : null,
    targetRaw: targets, constrRaw: constructions, fitRaw: fits, grupRaw: grups,
  }), [targets, constructions, fits, grups])

  const filtrats = useMemo(() => {
    const s = q.trim().toLowerCase()
    return jocs
      .filter(j => (veureActius ? j.actiu !== false : j.actiu === false))
      .filter(j => !s || `${j.codi_sistema || ''} ${j.nom || ''} ${j.customer_codi || ''}`.toLowerCase().includes(s))
  }, [jocs, q, veureActius])

  const obert = useMemo(() => jocs.find(j => j.id === obertId) || null, [jocs, obertId])

  // «Es proposa a» — el resum de les relacions d'un joc, amb el vocabulari resolt. Qui no en té
  // cap surt com a «no declarat», que NO és el mateix que «val per a tothom».
  const resumRelacions = useCallback((j) => {
    const et = (llista, codi) => (llista || []).find(x => x.codi === codi)?.etiqueta || codi
    return [
      ...(j.targets_codis || []).map(c => et(vocabularis.target, c)),
      j.construction_codi ? et(vocabularis.construccio, j.construction_codi) : null,
      j.fit_type_codi ? et(vocabularis.fit, j.fit_type_codi) : null,
      j.garment_group_codi ? et(vocabularis.grup, j.garment_group_codi) : null,
    ].filter(Boolean)
  }, [vocabularis])

  const esborra = useCallback(async (j, force = false) => {
    if (!force && !window.confirm(t('grading.confirm_delete', { name: j.nom }))) return
    try {
      await gradingRuleSets.remove(j.id, force)
      setObertId(null)
      setMsg({ type: 'ok', text: t('grading.deleted') })
      carrega()
    } catch (e) {
      // 409 = té perfils i/o models dependents. El missatge el redacta el BACKEND (és qui sap el
      // recompte) i es pinta tal qual; si es confirma, cascada controlada.
      if (e?.response?.status === 409) {
        const d = e.response.data || {}
        if (window.confirm(d.message || t('grading.confirm_delete_deps'))) return esborra(j, true)
        return
      }
      setMsg({ type: 'err', text: missatgeError(e, t('grading.jocs.save_error')) })
    }
  }, [t, carrega])

  const commutaActiu = async (j) => {
    try {
      await gradingRuleSets.update(j.id, { actiu: j.actiu === false })
      setMsg({ type: 'ok', text: t('grading.updated') })
      carrega(j.id)
    } catch (e) { setMsg({ type: 'err', text: missatgeError(e, t('grading.jocs.save_error')) }) }
  }

  const accionsDelJoc = obert ? [
    { label: t('grading.jocs.act_identity'), onClick: () => setModal({ joc: obert, mode: 'edit' }) },
    {
      label: t('grading.clone'),
      // D3 — el clon HEREDA els eixos i l'abast del joc original; el modal els arrossega.
      onClick: () => setModal({
        joc: {
          ...obert, id: null, regles_count: 0,
          nom: `${obert.nom} ${t('grading.jocs.copy_suffix')}`,
          codi_sistema: obert.codi_sistema ? `${obert.codi_sistema}_COPY` : '',
        },
        mode: 'clon',
      }),
    },
    {
      label: obert.actiu === false ? t('grading.jocs.act_revive') : t('grading.jocs.act_retire'),
      onClick: () => commutaActiu(obert),
    },
    { label: t('app.delete'), danger: true, onClick: () => esborra(obert) },
  ] : null

  return (
    <>
      {/* §8b · EL MENÚ DE PANTALLA, que és la segona franja de tota pantalla del producte i que
          la maqueta dibuixa amb aquest contingut exacte: ← · [Jocs actius · Jubilats] · Nou joc ▾.
          El component ja existia a `ui/PageMenu.jsx` i no el muntava ningú.
          ⚠️ El marge negatiu treu la barra dels 24px del `<main>` del Shell perquè vagi «de
          costat a costat» com mana la norma. Mentre el Shell no allotgi la barra ell mateix,
          aquesta és la manera contenida de fer-ho: afecta NOMÉS aquesta pantalla. */}
      <div style={{ margin: '-1.5rem -1.5rem 0' }}>
        <PageMenu
          backTo="/cataleg-peces"
          backTitle={t('grading.jocs.back_title')}
          items={[true, false].map(v => ({
            key: String(v),
            label: v ? t('grading.jocs.view_active') : t('grading.jocs.view_retired'),
            active: veureActius === v,
            onClick: () => { setVeureActius(v); setObertId(null) },
          }))}
        >
          {/* Ordre del §8e: primer QUÈ VEIG, després QUÈ HI FAIG. L'acció, en estil de menú. */}
          {!obert && (
            <>
              <span style={{ width: 1, height: 20, background: 'var(--line)', margin: '0 6px', flex: 'none' }} />
              <MenuDesplegable
                etiqueta={t('grading.jocs.new')} icona="ti-plus"
                items={[
                  { label: t('grading.jocs.new_manual'), onClick: () => setModal({ joc: null, mode: 'nou' }) },
                  { label: t('grading.jocs.new_import'), onClick: () => onImportar?.() },
                ]} />
            </>
          )}
        </PageMenu>
      </div>

      <div style={cx.wrap}>
      {msg && (
        <div role="alert" style={{
          margin: '12px 0', padding: '8px 12px', borderRadius: 'var(--r-ctrl)',
          fontSize: 'var(--fs-body)', display: 'flex', justifyContent: 'space-between', gap: 12,
          ...(msg.type === 'ok' ? BADGE.ok : BADGE.err),
        }}>
          <span>{msg.text}</span>
          <Boto variant="ter" onClick={() => setMsg(null)} aria-label={t('app.close')}
                style={{ padding: 0, color: 'inherit' }}>
            <i className="ti ti-x" aria-hidden="true" style={{ fontSize: 14 }} />
          </Boto>
        </div>
      )}

      {obert ? (
        <Joc
          key={obert.id}
          joc={obert}
          run={obert.size_system != null ? runsPerId[obert.size_system] : null}
          vocabularis={vocabularis}
          regimsAutorables={regimsAutorables}
          accions={accionsDelJoc}
          onTanca={() => setObertId(null)}
          onError={(text) => setMsg({ type: 'err', text })}
          onCanviat={(ev) => {
            setMsg({ type: 'ok', text: ev.tipus === 'relacions' ? t('grading.updated')
              : ev.tipus === 'regles' ? t('grading.jocs.rules_saved', { count: ev.n })
                : t('grading.jocs.rule_removed') })
            carrega(obert.id)
          }}
        />
      ) : (
        <>
          {/* COMPTADOR + CERCA A LA MATEIXA LÍNIA (NORMA §8e): el primer número ÉS el resultat de
              la cerca. La maqueta posa la cerca a la capçalera de la llista; la §8e va a missa i
              mana la pell — mateixa decisió que ja es va prendre al catàleg de POMs. */}
          <div style={cx.ident}>
            <span style={cx.kpi}>{filtrats.length}<small style={cx.kpiSmall}>/{jocs.length}</small></span>
            <span style={cx.lab}>{t('grading.jocs.title')}</span>
            <Camp style={{ flex: 1, minWidth: 220, alignSelf: 'center' }} value={q}
                  onChange={e => setQ(e.target.value)}
                  placeholder={t('grading.jocs.search_ph')} aria-label={t('grading.jocs.search_ph')} />
            <span style={cx.desc}>{t('grading.jocs.subtitle')}</span>
          </div>

          <div style={cx.box}>
            <div style={{ ...cx.grid, ...cx.lhead }}>
              <span style={cx.th}>{t('grading.jocs.col_set')}</span>
              <span style={cx.th}>{t('grading.jocs.col_client')}</span>
              <span style={cx.th}>{t('grading.jocs.col_origen')}</span>
              <span style={cx.th}>{t('grading.jocs.col_rules')}</span>
              <span style={cx.th}>{t('grading.jocs.col_proposed')}</span>
              <span style={cx.th} />
            </div>

            {carregant && (
              <div style={{ padding: 40, textAlign: 'center', ...cx.buit }}>{t('grading.loading')}</div>
            )}
            {!carregant && !filtrats.length && (
              <div style={{ padding: 40, textAlign: 'center', ...cx.buit }}>
                {veureActius ? t('grading.jocs.no_match') : t('grading.jocs.none_retired')}
              </div>
            )}
            {filtrats.map(j => <Fila key={j.id} j={j} rl={resumRelacions(j)}
                                     onObre={() => setObertId(j.id)} t={t} />)}
          </div>
        </>
      )}

      {modal && (
        <JocModal
          joc={modal.joc}
          runs={runs}
          onTanca={() => setModal(null)}
          onError={(text) => setMsg({ type: 'err', text })}
          onDesat={(data, esEdicio) => {
            setModal(null)
            setMsg({ type: 'ok', text: esEdicio ? t('grading.updated') : t('grading.created') })
            carrega(obertId)
            if (!esEdicio) setObertId(data.id)
          }}
        />
      )}
      </div>
    </>
  )
}

/** Una fila de la llista. Component propi perquè el hover és estat, no CSS. */
function Fila({ j, rl, onObre, t }) {
  const [toc, gestos] = useToc()
  const jubilat = j.actiu === false
  const relText = rl.length
    ? rl.slice(0, 4).join(' · ') + (rl.length > 4 ? ` +${rl.length - 4}` : '')
    : t('grading.jocs.undeclared')
  return (
    <div {...gestos} style={{
      ...cx.grid, ...cx.lrow,
      background: toc.hover ? 'var(--bg-page)' : 'var(--panel)',
      opacity: jubilat ? 0.55 : 1,
    }}>
      <span style={{ minWidth: 0 }}>
        <span style={{ ...cx.nm, ...cx.tall, display: 'block' }} title={j.nom}>{j.nom}</span>
        <span style={{ ...cx.cd, ...cx.tall, display: 'block' }}>
          {j.codi_sistema || t('grading.jocs.no_code')}
        </span>
      </span>
      <span style={{ ...cx.v, ...cx.tall }}>
        {j.customer_codi || <span style={cx.buit}>{t('grading.jocs.house')}</span>}
      </span>
      <span>
        {/* El badge diu la paraula CURTA (la fila és d'UNA línia, §8e) i el `title` en dona la
            sencera, que és la del vocabulari del backend. */}
        <span style={{ ...cx.badge, ...badgeOrigen(j.origen) }}
              title={j.origen ? t(`grading.origen_${j.origen}`) : t('grading.origen_none')}>
          {t(`grading.jocs.origen_short_${j.origen || 'none'}`)}
        </span>
      </span>
      <span style={cx.v}>{j.regles_count ?? 0}</span>
      <span style={{ ...cx.rel, ...cx.tall, ...(rl.length ? null : cx.buit) }} title={relText}>
        {relText}
      </span>
      <span style={{ textAlign: 'right' }}>
        {/* Un joc jubilat no s'edita: la maqueta hi posa el badge al lloc del botó. */}
        {jubilat
          ? <span style={{ ...cx.badge, ...BADGE.neu }}>{t('grading.jocs.badge_retired')}</span>
          : <Boto variant="sm" onClick={onObre}>{t('app.edit')}</Boto>}
      </span>
    </div>
  )
}
