import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  MAX_BREAKS, finalTriables, iniciTriables, intervalNou, intervalsVisibles, ordenaIntervals,
} from '../../utils/gradingRegime'

// ── F4-BIS · LA COLUMNA «BREAKS», UNA DE SOLA PER A LES DUES TAULES ──────────────────────────
//
// Les dues superfícies que escriuen regles —«Generar regles» (el joc del catàleg,
// `JocsDeRegles`) i «Graduació del model» (`GraduacioSuperficie`)— comparteixen component
// perquè han de tenir la MATEIXA gramàtica. La lliçó és la de les amplades d'`EditableTable`,
// que es van copiar «perquè la recerca les trobés als dos llocs» i es van separar el mateix dia.
//
// 🔑 QUÈ SUBSTITUEIX, I PER QUÈ NO ÉS UNA COLUMNA MÉS. Aquesta columna ocupa el lloc de «Δ
// break» + «Talla break». No s'hi suma: les REEMPLAÇA. Les dues deien entre totes dues UN
// trencament, en dues cel·les que s'havien de llegir juntes i en convencions diferents (la
// talla en convenció de DOCUMENT, el delta cru). Un xip diu el mateix trencament SENCER i en
// diu N: «de la M a la XL creix 3». El que abans eren dues columnes que no cabien més d'un cop,
// ara és una que en cap tants com el sostre permeti.
//
// 🚨 CONVENCIÓ DE MOTOR, I AQUÍ NO ES FA CAP VOLTA. `inici` és la PRIMERA talla que creix amb
// el Δ nou —el que la BD desa i el que `grading_utils.intervals_de` llegeix—. Amb la columna
// «Talla break» fora d'aquestes dues pantalles, l'ambigüitat de convenció desapareix d'aquí:
// no hi ha cap altre control al costat que parli en convenció de document i pugui contradir-lo.
// Traduir hauria volgut dir fer la volta N vegades per fila, i «una superfície que en faci
// servir només una menteix» (`breakConvention.js:18`) hauria passat de risc a ser-ne tres.
//
// 🔑 EL SOLAPAMENT NO ES POT TECLEJAR. Els dos selectors només ofereixen talles LLIURES
// (`iniciTriables`/`finalTriables`, mirall de la porta) i el final només va endavant des de
// l'inici: `BREAKS_SOLAPAMENT` i `BREAKS_ORDRE` deixen de ser errors possibles d'aquesta
// pantalla. La validació del servidor es queda igualment —una pantalla no és mai l'única
// guarda d'una dada— i quan parla, parla AQUÍ MATEIX (prop `error`), com fa la porta de
// `valors_step` a la columna «Mesura» de l'Escalat.
//
// 🔑 L'ESBORRANY NO ÉS LA REGLA. Mentre s'edita un xip, el que es toca viu a l'estat d'aquest
// component; només el ✓ el fa entrar a la llista de la regla. Per això un interval a mitges no
// pot bloquejar el «Gravar» de la fila: no hi arriba mai. (`intervalsIncomplets` es queda com a
// xarxa per a llistes que vinguin d'un altre camí.)

const FS_XIP = 11

const capsa = {
  display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap',
}

const xip = (actiu) => ({
  display: 'inline-flex', alignItems: 'center', gap: 4,
  border: `1px solid ${actiu ? 'var(--gold)' : 'var(--border)'}`,
  borderRadius: 'var(--r-pill)', background: 'var(--white)',
  fontSize: FS_XIP, whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums',
  padding: '0 4px 0 0', lineHeight: 1.5,
})

const xipEdicio = {
  display: 'inline-flex', alignItems: 'center', gap: 5,
  border: '1px solid var(--gold)', borderRadius: 'var(--r-pill)',
  background: 'var(--sel)', padding: '2px 6px', fontSize: FS_XIP,
}

const botoNu = {
  border: 'none', background: 'transparent', font: 'inherit', fontSize: FS_XIP,
  cursor: 'pointer', padding: '3px 0 3px 10px', color: 'var(--text-main)',
  display: 'inline-flex', alignItems: 'center', gap: 4,
  fontVariantNumeric: 'tabular-nums',
}

// ⚠️ UN BOTÓ NOMÉS-ICONA VOL CAIXA PRÒPIA. Els glifs Tabler venen d'un webfont del CDN
// (`index.html:8`): mentre no ha carregat —o si mai no carrega— l'`<i>` mesura 0×0, i un botó
// que només el conté es queda sense alçada i sense àrea de clic. Amb `minWidth`/`minHeight`
// la diana hi és igualment. Caçat a la primera correguda de `qa_f4bis_columna_breaks.py`,
// on el ✓ era «enabled» i alhora «not visible».
const botoIcona = {
  border: 'none', background: 'transparent', cursor: 'pointer', padding: 0,
  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
  minWidth: 18, minHeight: 18, lineHeight: 1,
}

const botoTreure = { ...botoIcona, color: 'var(--text-muted)', marginRight: 3 }

const control = {
  boxSizing: 'border-box', border: '0.5px solid var(--border)',
  borderRadius: 'var(--r-ctrl)', padding: '2px 4px', fontSize: 12, font: 'inherit',
  background: 'var(--white)', color: 'var(--text-main)',
}
const selTalla = { ...control, cursor: 'pointer', minWidth: 56 }
const inputDelta = { ...control, width: 52, textAlign: 'center', fontVariantNumeric: 'tabular-nums' }

/** Text lliure → número o null (accepta la coma decimal, que és com s'escriu aquí). */
function num(v) {
  if (v === null || v === undefined || v === '') return null
  const n = Number(String(v).replace(',', '.'))
  return Number.isFinite(n) ? n : null
}

/** `+3` / `-1.5` — el signe explícit del Δ, com a `breakConvention.etiquetaRegla`. */
function signe(v) {
  const n = Number(v)
  if (!Number.isFinite(n)) return '—'
  return n < 0 ? `${n}` : `+${n}`
}

/**
 * La columna «Breaks» d'una fila de regla.
 *
 * @param rule     la regla VIGENT de la fila (servidor + edicions a sobre)
 * @param run      el run del SISTEMA: és l'espai on el motor resol el relleu (llei S24b) i on
 *                 cau el final de tota regla d'1 break llegida com a interval
 * @param onCanvi  `(llista) => void` — la llista SENCERA d'intervals tal com queda
 * @param readOnly columna inerta (FIXED/STEP/ZERO: no hi ha relleu a dir)
 * @param motiu    per què està inerta, per al `title` del control apagat (§8c)
 * @param error    `{codi, detall}` del servidor per a AQUESTA fila, si n'hi ha
 */
export default function ColumnaBreaks({ rule, run, onCanvi, readOnly = false, motiu = '',
  error = null }) {
  const { t } = useTranslation()
  // `editant`: índex del xip obert, o `llista.length` per a un de NOU. `-1` = cap.
  const [editant, setEditant] = useState(-1)
  const [esborrany, setEsborrany] = useState(null)
  const [sobre, setSobre] = useState(-1)

  const llista = intervalsVisibles(rule, run)
  const ple = llista.length >= MAX_BREAKS
  const senseRun = !Array.isArray(run) || run.length < 2

  const tanca = () => { setEditant(-1); setEsborrany(null) }

  /** Confirma l'esborrany: entra a la llista (substituint o afegint) i es tanca. */
  const confirma = () => {
    if (!esborrany || !esborrany.inici || !esborrany.final || esborrany.delta === null) return
    const net = { inici: esborrany.inici, final: esborrany.final, delta: esborrany.delta }
    const nova = editant < llista.length
      ? llista.map((iv, k) => (k === editant ? net : { inici: iv.inici, final: iv.final, delta: iv.delta }))
      : [...llista.map(iv => ({ inici: iv.inici, final: iv.final, delta: iv.delta })), net]
    // ORDENATS, com els desarà el servidor (`valida_breaks` els ordena per posició d'inici).
    // Un xip afegit al final d'una llista que comença per la S es llegiria com si el relleu
    // anés a salts; i pitjor, la pantalla diria un ordre i la BD en guardaria un altre.
    onCanvi(ordenaIntervals(nova, run))
    tanca()
  }

  const treu = (i) => {
    onCanvi(llista.filter((_, k) => k !== i).map(iv => ({ inici: iv.inici, final: iv.final, delta: iv.delta })))
    tanca()
  }

  const obre = (i) => {
    const iv = llista[i]
    setEsborrany({ inici: iv.inici, final: iv.final, delta: iv.delta })
    setEditant(i)
  }

  const afegeix = () => {
    const nou = intervalNou(llista, run)
    if (!nou) return
    setEsborrany(nou)
    setEditant(llista.length)
  }

  // Les talles que l'esborrany pot triar. `editant` fa d'«excepte»: un xip que s'edita no es
  // tapa a si mateix, i un de nou (índex fora de la llista) no en tapa cap.
  const opcionsInici = esborrany ? iniciTriables(llista, run, editant) : []
  const opcionsFinal = esborrany ? finalTriables(llista, run, editant, esborrany.inici) : []
  const potConfirmar = !!esborrany && !!esborrany.inici && !!esborrany.final
    && esborrany.delta !== null

  const nouPossible = !readOnly && !ple && !senseRun && !!intervalNou(llista, run)
  const motiuApagat = motiu
    || (senseRun ? t('grading.intervals.sense_run') : t('grading.intervals.sense_lliures'))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <div style={capsa}>
        {llista.map((iv, i) => (
          editant === i && esborrany ? (
            <EditorXip key={`ed-${i}`} {...{ esborrany, setEsborrany, opcionsInici, opcionsFinal,
              potConfirmar, confirma, tanca, t }} />
          ) : (
            /* 🔑 DOS BOTONS GERMANS DINS D'UN `span`, MAI un botó dins d'un botó: és HTML
               invàlid i el clic de dins queda mort (el defecte que QA-TALLER-C va caçar a la
               llista de POMs amb la «i»). La vora del xip la porta el contenidor. */
            <span key={`xip-${i}`} style={xip(sobre === i)}
              onMouseEnter={() => setSobre(i)} onMouseLeave={() => setSobre(-1)}>
              <button type="button" disabled={readOnly} onClick={() => obre(i)}
                title={readOnly ? motiuApagat
                  : iv.llegat ? `${t('grading.intervals.editar')} · ${t('grading.intervals.llegat_help')}`
                    : t('grading.intervals.editar')}
                style={{ ...botoNu, cursor: readOnly ? 'default' : 'pointer' }}>
                <span>{iv.inici}</span>
                <span aria-hidden="true" style={{ color: 'var(--text-soft)' }}>→</span>
                <span>{iv.final}</span>
                <span style={{ fontWeight: 700 }}>{signe(iv.delta)}</span>
              </button>
              {!readOnly && (
                <button type="button" onClick={() => treu(i)}
                  title={t('grading.intervals.treure')} aria-label={t('grading.intervals.treure')}
                  style={botoTreure}>
                  <i className="ti ti-x" aria-hidden="true" style={{ fontSize: 11 }} />
                </button>
              )}
            </span>
          )
        ))}

        {/* L'esborrany d'un interval NOU va al final: encara no és a la llista. */}
        {editant >= llista.length && esborrany && (
          <EditorXip {...{ esborrany, setEsborrany, opcionsInici, opcionsFinal, potConfirmar,
            confirma, tanca, t }} />
        )}

        {/* AL MÀXIM, EL [+] DESAPAREIX I HO DIU. Un control apagat que ningú pot fer servir
            ocupa el lloc d'una explicació; el rètol la dóna. */}
        {ple ? (
          <span style={{ fontSize: 10, color: 'var(--text-soft)', fontStyle: 'italic' }}>
            {t('grading.intervals.max_curt', { max: MAX_BREAKS })}
          </span>
        ) : editant === -1 && (
          <button type="button" disabled={!nouPossible} onClick={afegeix}
            title={nouPossible ? t('grading.intervals.afegir') : motiuApagat}
            aria-label={nouPossible ? t('grading.intervals.afegir') : motiuApagat}
            style={{
              width: 22, height: 22, display: 'inline-flex', alignItems: 'center',
              justifyContent: 'center', border: '1px dashed var(--border)',
              borderRadius: 'var(--r-ctrl)', background: 'transparent',
              color: nouPossible ? 'var(--text-soft)' : 'var(--text-muted)',
              cursor: nouPossible ? 'pointer' : 'not-allowed', opacity: nouPossible ? 1 : 0.35,
              padding: 0,
            }}>
            <i className="ti ti-plus" aria-hidden="true" style={{ fontSize: 12 }} />
          </button>
        )}
      </div>

      {/* LA XARXA DEL SERVIDOR PARLA AQUÍ. Amb el missatge a la barra de peu, qui ha escrit
          l'interval havia de recordar quina fila havia tocat; amb el codi al costat del xip,
          l'error és de la regla que el va provocar. */}
      {error && (
        <span style={{ fontSize: 'var(--fs-label)', color: 'var(--err)', maxWidth: 260,
                       whiteSpace: 'normal', lineHeight: 1.35 }}
          title={error.codi || ''}>
          {error.detall || error.codi}
        </span>
      )}
    </div>
  )
}

/** El xip OBERT: dos selectors de talla + Δ + confirmar/cancel·lar. */
function EditorXip({ esborrany, setEsborrany, opcionsInici, opcionsFinal, potConfirmar,
  confirma, tanca, t }) {
  return (
    <span style={xipEdicio}
      onKeyDown={e => {
        if (e.key === 'Enter' && potConfirmar) { e.preventDefault(); confirma() }
        if (e.key === 'Escape') { e.preventDefault(); tanca() }
      }}>
      <select value={esborrany.inici || ''} style={selTalla}
        aria-label={t('grading.intervals.talla_inici')}
        title={t('grading.intervals.talla_inici_help')}
        onChange={e => {
          const inici = e.target.value
          // El final SEGUEIX l'inici quan es queda enrere o fora del tram lliure: així mai hi ha
          // un estat intermedi del revés, que és el que `BREAKS_ORDRE` castiga.
          setEsborrany(prev => ({ ...prev, inici, final: inici }))
        }}>
        {opcionsInici.map(s => <option key={s} value={s}>{s}</option>)}
      </select>
      <span aria-hidden="true" style={{ color: 'var(--text-soft)' }}>→</span>
      <select value={esborrany.final || ''} style={selTalla}
        aria-label={t('grading.intervals.talla_final')}
        title={t('grading.intervals.talla_final_help')}
        onChange={e => setEsborrany(prev => ({ ...prev, final: e.target.value }))}>
        {opcionsFinal.map(s => <option key={s} value={s}>{s}</option>)}
      </select>
      <input type="text" inputMode="decimal" size={4} autoFocus
        value={esborrany.delta === null || esborrany.delta === undefined ? '' : esborrany.delta}
        aria-label={t('grading.intervals.delta')} placeholder="Δ"
        title={t('grading.intervals.delta_help')}
        onChange={e => setEsborrany(prev => ({ ...prev, delta: num(e.target.value) }))}
        style={inputDelta} />
      <button type="button" onClick={confirma} disabled={!potConfirmar}
        title={t('grading.intervals.confirmar')} aria-label={t('grading.intervals.confirmar')}
        style={{ ...botoIcona, color: 'var(--ok)',
                 cursor: potConfirmar ? 'pointer' : 'not-allowed',
                 opacity: potConfirmar ? 1 : 0.4 }}>
        <i className="ti ti-check" aria-hidden="true" style={{ fontSize: 13 }} />
      </button>
      <button type="button" onClick={tanca}
        title={t('grading.intervals.cancellar')} aria-label={t('grading.intervals.cancellar')}
        style={{ ...botoIcona, color: 'var(--text-muted)' }}>
        <i className="ti ti-x" aria-hidden="true" style={{ fontSize: 13 }} />
      </button>
    </span>
  )
}
