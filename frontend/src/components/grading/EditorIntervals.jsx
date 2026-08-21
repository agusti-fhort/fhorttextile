import { useTranslation } from 'react-i18next'
import { MAX_BREAKS, intervalsDe } from '../../utils/gradingRegime'

// ── TRAM F · L'EDITOR D'INTERVALS, UN DE SOL PER A LES DUES TAULES ──────────────────────────
//
// Les dues superfícies que escriuen regles —«Generar regles» (el joc del catàleg,
// `JocsDeRegles`) i «Graduació del model» (`GraduacioSuperficie`)— han de tenir la MATEIXA
// gramàtica: un signe [+] a la fila del POM i una SUB-LÍNIA per interval. Per això l'editor és
// un component compartit i no dues còpies que es bifurquin el segon dia (la lliçó de les
// amplades de `EditableTable`, que es van copiar «perquè la recerca les trobés als dos llocs»
// i es van separar el mateix dia).
//
// 🔑 N INTERVALS NO CABEN EN COLUMNES. Les dues taules tenen amplades DECLARADES
// (`EditableTable.AMPLADES`, el `colgroup` de `JocsDeRegles`) i la de la fitxa ja es reparteix
// en bandes per no passar l'A4. Afegir columnes per interval menjaria carril de talles a cada
// break. Per això cada interval és una `<tr>` FILLA de la fila del POM: creix cap avall, que és
// on hi ha lloc, i deixa les columnes exactament on eren.
//
// 🚨 CONVENCIÓ DE MOTOR, I AQUÍ NO ES FA CAP VOLTA (esmena del 21/08).
// La columna «Talla break» d'aquestes mateixes taules es pinta en convenció de DOCUMENT
// (`breakConvention.aDocument`: l'última talla del tram petit) perquè és com ho escriu el full
// del client. Els INTERVALS, no: `inici` és la PRIMERA talla que creix amb el Δ nou, que és el
// que la BD desa i el que el motor llegeix. Traduir-los hauria volgut dir fer la volta N
// vegades per fila —i «una superfície que en faci servir només una menteix»
// (`breakConvention.js:18`) passa de ser un risc a ser-ne tres—. El que s'hi posa, en canvi, és
// un rètol que ho diu amb paraules: la sub-línia porta el seu propi encapçalament.
//
// El run que s'ofereix és el del SISTEMA quan el cridador el té: el motor resol el relleu contra
// el run del sistema (llei S24b) i, si el picker només oferís el del model, un interval que
// acabés a una talla que el model no fabrica no seria ni triable ni re-desable.

const cellaSub = {
  padding: '3px 10px 3px 0', verticalAlign: 'middle', fontSize: 'var(--fs-label)',
  color: 'var(--text-muted)',
}
const inputSub = {
  boxSizing: 'border-box', textAlign: 'center', border: '0.5px solid var(--border)',
  borderRadius: 4, padding: '2px 6px', fontSize: '12.5px', font: 'inherit', width: 64,
  fontVariantNumeric: 'tabular-nums', background: 'var(--white)', color: 'var(--text-main)',
}
const selectSub = { ...inputSub, width: 78, textAlign: 'left', cursor: 'pointer' }

/** Text lliure → número o null (accepta la coma decimal, que és com s'escriu aquí). */
function num(v) {
  if (v === null || v === undefined || v === '') return null
  const n = Number(String(v).replace(',', '.'))
  return Number.isFinite(n) ? n : null
}

/**
 * El signe [+] de la fila del POM. Apagat quan la regla ja té `MAX_BREAKS` intervals o quan el
 * règim no els admet — i, apagat, DIU PER QUÈ (§8c: un control apagat sense motiu és una paret
 * sense porta).
 */
export function BotoAfegirInterval({ intervals, run, onCanvi, disabled = false, motiu = '' }) {
  const { t } = useTranslation()
  const llista = intervalsDe({ breaks: intervals })
  const ple = llista.length >= MAX_BREAKS
  const senseRun = !run || run.length < 2
  const off = disabled || ple || senseRun
  const titol = motiu || (ple ? t('grading.intervals.max', { max: MAX_BREAKS })
    : senseRun ? t('grading.intervals.sense_run') : t('grading.intervals.afegir'))
  return (
    <button type="button" disabled={off} title={titol} aria-label={titol}
      onClick={() => {
        // L'interval NEIX buit de Δ i cobrint de la talla triada cap amunt: és la forma que
        // té sentit per defecte (un break és «d'aquí endavant») i la que menys demana omplir.
        const darrera = run[run.length - 1]
        const inici = run[Math.min(llista.length + 1, run.length - 1)]
        onCanvi([...llista, { inici, final: darrera, delta: null }])
      }}
      style={{
        border: '0.5px solid var(--border)', borderRadius: 4, background: 'transparent',
        color: off ? 'var(--text-muted)' : 'var(--gold)', cursor: off ? 'not-allowed' : 'pointer',
        padding: '1px 6px', fontSize: 12, lineHeight: 1.4, opacity: off ? 0.45 : 1,
      }}>
      <i className="ti ti-plus" aria-hidden="true" style={{ fontSize: 12 }} />
    </button>
  )
}

/**
 * Les sub-línies: una `<tr>` per interval. `colSpanEsquerra` és el que cal saltar per caure sota
 * les columnes de regla de cada taula (les dues tenen identitats d'amplada diferent).
 */
export function FilesIntervals({ intervals, run, onCanvi, colSpanEsquerra, colSpanDreta = 1,
  readOnly = false, clau = 'iv' }) {
  const { t } = useTranslation()
  const llista = intervalsDe({ breaks: intervals })
  if (!llista.length) return null
  const canvia = (i, patch) => onCanvi(llista.map((iv, k) => (k === i ? { ...iv, ...patch } : iv)))
  const treu = (i) => onCanvi(llista.filter((_, k) => k !== i))
  return llista.map((iv, i) => (
    <tr key={`${clau}-${i}`} style={{ background: 'var(--fila-capa)' }}>
      <td colSpan={colSpanEsquerra} style={{ ...cellaSub, paddingLeft: 24 }}>
        <span style={{ color: 'var(--text-soft)' }}>
          <i className="ti ti-corner-down-right" aria-hidden="true"
            style={{ fontSize: 12, marginRight: 6 }} />
          {t('grading.intervals.linia', { n: i + 1 })}
        </span>
      </td>
      <td colSpan={colSpanDreta} style={cellaSub}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          <select value={iv.inici || ''} disabled={readOnly} style={selectSub}
            aria-label={t('grading.intervals.talla_inici')}
            title={t('grading.intervals.talla_inici_help')}
            onChange={e => canvia(i, { inici: e.target.value })}>
            <option value="">—</option>
            {run.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <span aria-hidden="true" style={{ color: 'var(--text-soft)' }}>→</span>
          <select value={iv.final || ''} disabled={readOnly} style={selectSub}
            aria-label={t('grading.intervals.talla_final')}
            title={t('grading.intervals.talla_final_help')}
            onChange={e => canvia(i, { final: e.target.value })}>
            <option value="">—</option>
            {run.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <input type="text" inputMode="decimal" size={4} disabled={readOnly}
            value={iv.delta === null || iv.delta === undefined ? '' : iv.delta}
            aria-label={t('grading.intervals.delta')} placeholder="Δ"
            title={t('grading.intervals.delta_help')}
            onChange={e => canvia(i, { delta: num(e.target.value) })}
            style={inputSub} />
          {!readOnly && (
            <button type="button" onClick={() => treu(i)}
              title={t('grading.intervals.treure')} aria-label={t('grading.intervals.treure')}
              style={{ border: 'none', background: 'transparent', color: 'var(--text-muted)',
                cursor: 'pointer', padding: '0 4px', fontSize: 12 }}>
              <i className="ti ti-x" aria-hidden="true" style={{ fontSize: 12 }} />
            </button>
          )}
        </span>
      </td>
    </tr>
  ))
}
