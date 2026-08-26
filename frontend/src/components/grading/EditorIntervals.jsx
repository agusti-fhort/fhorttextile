import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  MAX_BREAKS, finalTriables, iniciTriables, intervalNou, intervalsVisibles, ordenaIntervals,
} from '../../utils/gradingRegime'
import { esNumeroEnCurs, formatDeltaNum, formatNum, parseNum } from '../../utils/num'

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
// 🚨 L'ESBORRANY NO ÉS LA REGLA — I PER AIXÒ S'HA DE DIR EN VEU ALTA (21/08, reproduït al
// navegador amb l'evidència d'Agus). Mentre s'edita un xip, el que es toca viu a l'estat
// d'aquest component i només el ✓ el fa entrar a la llista. Això, sol, produïa dos danys que
// són el MATEIX defecte vist per les dues cares:
//
//   · **el missatge que menteix a l'ull.** Treure el xip llegat d'una regla amb Δ general 0 la
//     deixa sense relleu DESAT; obrir-ne un de nou i escriure-hi «+2» no l'hi torna a posar. El
//     guard de degenerada mirava la regla i deia «no gradua res» mentre a la pantalla hi havia
//     un xip amb un +2 escrit. La persona jutja el que VEU; el guard jutjava el que hi ha DESAT.
//   · **la pèrdua silenciosa.** Prémer «Gravar» amb un xip obert i complet el llençava sense
//     dir res: el POST sortia amb la llista d'abans i el xip desapareixia de la pantalla.
//
// Per això la columna AVISA cap amunt (`onEsborrany`) que té un xip pendent, i el «Gravar» de
// les dues superfícies el barra NOMENANT LA FILA. Ni s'escriu el que ningú ha confirmat —el ✓
// segueix sent el gest— ni es perd el que la persona té a mig escriure.

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

// `num()` i `signe()` vivien aquí, i eren la sisena i la setena còpia de la mateixa
// aritmètica. Ara la política de números és UNA i és `utils/num.js` (R1+R2, 26/08): el
// separador d'entrada i el de presentació els decideix aquell mòdul, no cada component.
//
// 🚨 I EL DEFECTE QUE AIXÒ TANCA NO ERA `num()`: era QUAN es cridava. L'input parsejava a cada
// tecla i es repintava amb el número que en sortia, o sigui que `Number('1.')` → `1` esborrava
// el separador sota els dits i **el decimal no s'hi podia escriure mai**, ni amb punt ni amb
// coma. Ara el TEXT CRU viu a l'esborrany (`delta_txt`) i el número se'n deriva.

/** El Δ de l'esborrany com a NÚMERO, derivat del text que s'hi està escrivint. */
const deltaDe = (esb) => parseNum(esb?.delta_txt)

/**
 * La columna «Breaks» d'una fila de regla.
 *
 * @param rule     la regla VIGENT de la fila (servidor + edicions a sobre)
 * @param run      el run del SISTEMA: és l'espai on el motor resol el relleu (llei S24b) i on
 *                 cau el final de tota regla d'1 break llegida com a interval
 * @param onCanvi  `(llista) => void` — la llista SENCERA d'intervals tal com queda
 * @param readOnly columna inerta (FIXED/STEP/ZERO: no hi ha relleu a dir)
 * @param motiu    per què està inerta, per al `title` del control apagat (§8c)
 * @param error       `{codi, detall}` del servidor per a AQUESTA fila, si n'hi ha
 * @param onEsborrany `({complet}|null) => void` — hi ha un xip obert? El pare ho ha de saber
 *                    per no gravar-lo en silenci ni acusar la fila de no tenir relleu
 */
export default function ColumnaBreaks({ rule, run, onCanvi, onEsborrany, readOnly = false,
  motiu = '', error = null }) {
  const { t, i18n } = useTranslation()
  // R2 · l'idioma de qui llegeix decideix el separador decimal, i es demana UN COP aquí: els
  // dos llocs que pinten un Δ (el xip tancat i el camp obert) han de dir-lo igual.
  const lang = i18n?.language || 'ca'
  // `editant`: índex del xip obert, o `llista.length` per a un de NOU. `-1` = cap.
  const [editant, setEditant] = useState(-1)
  const [esborrany, setEsborrany] = useState(null)
  const [sobre, setSobre] = useState(-1)

  /** Avisa el pare de si aquesta columna té un xip pendent. Es crida des dels GESTOS i no des
   *  d'un efecte: un `setState` dins d'un efecte encadena renders (i el lint ho canta). */
  const avisa = (esb) => onEsborrany?.(esb
    ? { complet: !!esb.inici && !!esb.final && deltaDe(esb) !== null } : null)

  const llista = intervalsVisibles(rule, run)
  const ple = llista.length >= MAX_BREAKS
  const senseRun = !Array.isArray(run) || run.length < 2

  const tanca = () => { setEditant(-1); setEsborrany(null); avisa(null) }

  /** Confirma l'esborrany: entra a la llista (substituint o afegint) i es tanca. */
  const confirma = () => {
    // El número es deriva del text AQUÍ —al confirm—, que és el moment en què el Δ deixa de
    // ser una cosa que s'està escrivint i passa a ser una dada.
    const delta = deltaDe(esborrany)
    if (!esborrany || !esborrany.inici || !esborrany.final || delta === null) return
    const net = { inici: esborrany.inici, final: esborrany.final, delta }
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
    // El Δ entra al camp en l'idioma de qui l'edita (R2): un catalanoparlant que obre un
    // Δ de 0,75 ha de veure-hi la coma que ell mateix hi escriuria.
    const esb = { inici: iv.inici, final: iv.final, delta_txt: formatNum(iv.delta, { lang }) }
    setEsborrany(esb); setEditant(i); avisa(esb)
  }

  const afegeix = () => {
    const nou = intervalNou(llista, run)
    if (!nou) return
    // `intervalNou` dona `delta: null` (encara no s'ha dit): al camp, text buit.
    const esb = { inici: nou.inici, final: nou.final, delta_txt: '' }
    setEsborrany(esb); setEditant(llista.length); avisa(esb)
  }

  /** Canvi dins del xip obert. Va per aquí i no per `setEsborrany` directe perquè cada tecla ha
   *  de poder canviar el veredicte que el pare té («pendent i incomplet» → «pendent i complet»). */
  const toca = (patch) => setEsborrany(prev => {
    const seg = { ...prev, ...patch }
    avisa(seg)
    return seg
  })

  // Les talles que l'esborrany pot triar. `editant` fa d'«excepte»: un xip que s'edita no es
  // tapa a si mateix, i un de nou (índex fora de la llista) no en tapa cap.
  const opcionsInici = esborrany ? iniciTriables(llista, run, editant) : []
  const opcionsFinal = esborrany ? finalTriables(llista, run, editant, esborrany.inici) : []
  const potConfirmar = !!esborrany && !!esborrany.inici && !!esborrany.final
    && deltaDe(esborrany) !== null

  const nouPossible = !readOnly && !ple && !senseRun && !!intervalNou(llista, run)
  const motiuApagat = motiu
    || (senseRun ? t('grading.intervals.sense_run') : t('grading.intervals.sense_lliures'))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <div style={capsa}>
        {llista.map((iv, i) => (
          editant === i && esborrany ? (
            <EditorXip key={`ed-${i}`} {...{ esborrany, toca, opcionsInici, opcionsFinal,
              potConfirmar, confirma, tanca, t, lang }} />
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
                <span style={{ fontWeight: 700 }}>{formatDeltaNum(iv.delta, { lang, buit: '—' })}</span>
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
          <EditorXip {...{ esborrany, toca, opcionsInici, opcionsFinal, potConfirmar,
            confirma, tanca, t, lang }} />
        )}

        {/* AL MÀXIM, EL [+] DESAPAREIX I HO DIU. Un control apagat que ningú pot fer servir
            ocupa el lloc d'una explicació; el rètol la dóna. */}
        {/* 🚨 SOTA UN RÈGIM QUE NO GRADUA, LA COLUMNA ÉS BUIDA DEL TOT (Agus, 21/08 — esmena
            del mockup, que hi deixava un [+] apagat). Ni xips —`intervalsVisibles` ja calla— ni
            [+]: un FIXED no creix i cap interval no li aplica, o sigui que un control apagat
            només convida a preguntar-se què hi fa. La columna sencera callada ÉS la resposta. */}
        {readOnly ? null : ple ? (
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
function EditorXip({ esborrany, toca, opcionsInici, opcionsFinal, potConfirmar,
  confirma, tanca, t, lang }) {
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
          toca({ inici, final: inici })
        }}>
        {opcionsInici.map(s => <option key={s} value={s}>{s}</option>)}
      </select>
      <span aria-hidden="true" style={{ color: 'var(--text-soft)' }}>→</span>
      <select value={esborrany.final || ''} style={selTalla}
        aria-label={t('grading.intervals.talla_final')}
        title={t('grading.intervals.talla_final_help')}
        onChange={e => toca({ final: e.target.value })}>
        {opcionsFinal.map(s => <option key={s} value={s}>{s}</option>)}
      </select>
      {/* 🚨 EL TEXT CRU MANA MENTRE S'ESCRIU. Això tenia `value={esborrany.delta}` amb un
          `onChange` que parsejava: l'estat intermedi «1.» no era representable —`Number('1.')`
          és 1 i es repintava «1»— i el separador decimal desapareixia sota els dits. Ni el
          punt ni la coma hi arribaven mai.
          Ara el camp és el TEXT (`delta_txt`) i el número se'n deriva al confirm; al BLUR, a
          més, el text es normalitza a l'idioma de qui l'escriu (R2), o sigui que qui teclegi
          «.75» hi acaba veient «0,75» i el que es desa és 0.75.
          `esNumeroEnCurs` és el que permet no pintar de vermell el que només està a mitges. */}
      <input type="text" inputMode="decimal" size={4} autoFocus
        value={esborrany.delta_txt ?? ''}
        aria-label={t('grading.intervals.delta')} placeholder="Δ"
        title={t('grading.intervals.delta_help')}
        onChange={e => toca({ delta_txt: e.target.value })}
        onBlur={e => {
          const n = parseNum(e.target.value)
          if (n !== null) toca({ delta_txt: formatNum(n, { lang }) })
        }}
        style={{ ...inputDelta,
                 borderColor: esNumeroEnCurs(esborrany.delta_txt) ? undefined : 'var(--err)' }} />
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
