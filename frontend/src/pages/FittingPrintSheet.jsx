import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

import { fittingSessions, pieceFittings, models } from '../api/endpoints'
import FttHeaderBand from '../components/model/FttHeaderBand'
import { etiquetaCapa, etiquetaInstancia } from '../utils/capaInstancia'
import { identitatMesura } from '../utils/identitatMesura'

// EL FULL DE FITTING QUE ES PORTA A LA PROVA — A4 APAÏSAT, per omplir A MÀ.
//
// No és una exportació de la pantalla: és el paper que la Montse porta a la sala i que després
// torna cap al fabricant. Per això la columna de la mesura surt BUIDA (s'escriu amb bolígraf) i
// els tres veredictes són caselles per marcar, no text.
//
// A4 APAÏSAT REAL: 297×210 mm = 1123×794 px a 96 dpi, marges 45 px. Les mides es declaren en px
// per a la pantalla i `@page` les torna a declarar en mm per a la impressora: el navegador
// pagina amb `@page`, i si les dues no diguessin el mateix el que es veu i el que surt serien
// dues coses.
const A4_W = 1123
const A4_H = 794
const MARGE = 45

// FILES PER PÀGINA. És un límit CONSERVADOR a posta: la llei del full és que una fila creix
// només si el seu NOM ho fa, i un nom llarg pot ocupar dues línies. Amb el marge que queda,
// una pàgina sencera de noms de dues línies encara hi cap sense trepitjar el peu.
const FILES_PER_PAGINA = 18

// ELS TRES VEREDICTES, en anglès i abreujats com al paper: és el que el fabricant marca.
const CASELLES = ['AC', 'AD', 'RJ']

const fmt = (n) => (n == null || n === '' ? '' : Number(n).toFixed(1))

// LES CAPES VAN EN ANGLÈS AL FULL (D-31.22), sigui quin sigui l'idioma de qui l'ha generat: el
// full viatja cap al fabricant i el fabricant llegeix anglès. El vocabulari NO es reescriu aquí
// —surt del mateix `etiquetaCapa` que la pantalla— i el que canvia és només el traductor.
const capaEn = (slug, tEn) => etiquetaCapa(slug, tEn)

export default function FittingPrintSheet() {
  const { sessionId, modelId } = useParams()
  const { t, i18n } = useTranslation()
  const tEn = i18n.getFixedT('en')
  const [dades, setDades] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let viu = true
    fittingSessions.get(sessionId)
      .then(r => {
        const peces = r.data?.piece_fittings || []
        const peca = peces.find(p => String(p.model ?? p.model_id) === String(modelId)) || peces[0]
        if (!peca) throw new Error('sense peça')
        // EL MODEL SENCER, a part. El `model` que porta la peça és el mínim per pintar la
        // graella (codi, nom, base, run) i la capçalera de fitxa en demana molt més —temporada,
        // col·lecció, referència de client, target|fit|construction, logo—. Amb només el que
        // porta la peça, la banda sortia amb les etiquetes i els valors buits: una capçalera
        // aprovada mig plena és pitjor que no tenir-la, perquè sembla que la dada no existeixi.
        return Promise.all([
          pieceFittings.get(peca.id),
          models.get(modelId).catch(() => null),
        ]).then(([g, m]) => ({ sessio: r.data, grid: g.data, model: m?.data || null }))
      })
      .then(d => { if (viu) setDades(d) })
      .catch(() => { if (viu) setError(t('fitting.print.load_err')) })
    return () => { viu = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, modelId])

  if (error) return <div style={{ padding: 40, fontFamily: 'monospace' }}>{error}</div>
  if (!dades) return <div style={{ padding: 40, fontFamily: 'monospace' }}>{t('common.loading')}</div>

  const model = dades.grid?.model || {}
  const ple = dades.model || {}
  const baseLabel = (model.base_size_label || '').trim()
  // TARGET | FIT TYPE | CONSTRUCTION és UN camp de la spec amb tres trams: es componen amb el
  // mateix separador que l'etiqueta ensenya, i els trams buits no deixen barres òrfenes.
  const targetFit = [ple.target, ple.fit_type, ple.construction].filter(Boolean).join(' | ')

  // UNA FILA PER MESURA (no per línia): les línies vénen per talla i el full és de la talla BASE,
  // que és on es prova la peça. S'agrupa per la identitat sencera —`pom_id|capa|instancia`— i no
  // pel POM: dues germanes són dues files del paper, i el tècnic n'ha de prendre dues mesures.
  const vistes = new Map()
  for (const l of (dades.grid?.lines || [])) {
    if (baseLabel && l.size_label !== baseLabel) continue
    const clau = identitatMesura(l)
    if (!vistes.has(clau)) vistes.set(clau, l)
  }
  const files = [...vistes.values()]

  const pagines = []
  for (let i = 0; i < Math.max(1, Math.ceil(files.length / FILES_PER_PAGINA)); i++) {
    pagines.push(files.slice(i * FILES_PER_PAGINA, (i + 1) * FILES_PER_PAGINA))
  }

  const dataSessio = (dades.sessio?.data || '').split('-').reverse().join('/')
  const capcalera = (n) => ({
    nom: ple.nom || model.nom || '',
    temporada: [ple.temporada, ple.any].filter(Boolean).join(' ') || '',
    collection: ple.collection || '',
    codi_intern: ple.codi_intern || model.codi || '',
    codi_client: ple.codi_client || '',
    run: ple.size_run_model || model.size_run_model || '',
    tallaActiva: baseLabel,
    target: targetFit,
    data: dataSessio,
    format: 'A4',
    pagina: `${n}/${pagines.length}`,
  })

  return (
    <div className="ftt-wrap" style={{ background: 'var(--bg-muted)', padding: '20px 0', minHeight: '100vh' }}>
      {/* `@page` en mm i `size: landscape` és el que fa que el navegador pagini com el full està
          dibuixat. `print-color-adjust` perquè els filets i els fons de casella no desapareguin
          en imprimir (per defecte el navegador els treu «per estalviar tinta»). */}
      <style>{`
        @page { size: A4 landscape; margin: 12mm; }
        @media print {
          body { background: #fff; }
          .ftt-noprint { display: none !important; }
          /* A LA IMPRESSORA, ELS MARGES ELS POSA @page — NO EL FULL.
             A pantalla el full es dibuixa com el paper que és (1123x794 px amb 45 px de vora)
             perquè es vegi què s'endurà. En imprimir, aquesta mateixa vora se SUMARIA als 12 mm
             d'@page i el full de 1123 px no cabria als 1032 px imprimibles: cada pàgina en
             vessava una de mig buida. Aquí es treu la vora pròpia i s'ocupa l'àrea imprimible
             sencera — 210 mm menys els dos marges = 186 mm—, que és el que manté la promesa
             d'un div = una pàgina i deixa el peu clavat a baix. */
          /* El CONTENIDOR també desapareix. Duia el fons de la pantalla, un encoixinat i un
             min-height de 100vh: tot això s'imprimeix, i tres fulls de 186 mm dins d'un
             contenidor més alt que la suma acaben repartits en cinc pàgines mig buides. */
          .ftt-wrap { padding: 0 !important; min-height: 0 !important; background: #fff !important; }
          .ftt-full {
            box-shadow: none !important; border: none !important; margin: 0 !important;
            width: 100% !important; height: 184mm !important; padding: 0 !important;
            page-break-inside: avoid; overflow: hidden;
          }
          .ftt-full + .ftt-full { page-break-before: always; }
        }
        .ftt-full, .ftt-full * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
      `}</style>

      <div className="ftt-noprint" style={{ textAlign: 'center', marginBottom: 16 }}>
        <button type="button" onClick={() => window.print()}
          style={{ border: '1px solid var(--gold)', background: 'var(--white)', color: 'var(--gold)',
                   borderRadius: 6, padding: '7px 15px', font: 'inherit',
                   fontFamily: 'monospace', fontSize: 'var(--fs-body)', cursor: 'pointer' }}>
          <i className="ti ti-printer" /> {t('fitting.print.print')}
        </button>
      </div>

      {pagines.map((files_pag, p) => (
        <Pagina key={p} files={files_pag} desDe={p * FILES_PER_PAGINA}
          capcalera={capcalera(p + 1)} ultima={p === pagines.length - 1}
          baseLabel={baseLabel} dataSessio={dataSessio}
          logoUrl={ple.customer_logo || null} t={t} tEn={tEn} />
      ))}
    </div>
  )
}

function Pagina({ files, desDe, capcalera, ultima, baseLabel, dataSessio, logoUrl, t, tEn }) {
  const ampladaUtil = A4_W - MARGE * 2
  return (
    <div className="ftt-full" style={{
      width: A4_W, height: A4_H, padding: MARGE, margin: '0 auto 16px',
      background: 'var(--white)', border: '1px solid var(--border)',
      boxShadow: '0 1px 4px rgba(0,0,0,.07)', boxSizing: 'border-box',
      display: 'flex', flexDirection: 'column', overflow: 'hidden',
      fontFamily: 'IBM Plex Mono, ui-monospace, monospace', color: 'var(--text-main)',
    }}>
      <FttHeaderBand amplada={ampladaUtil} dades={capcalera} logoUrl={logoUrl} t={t} />

      <div style={{ fontSize: '7.5pt', color: 'var(--text-muted)', margin: '8px 0 6px' }}>
        {t('fitting.print.session_line', { data: dataSessio, base: baseLabel })}
      </div>

      {/* LA LLIÇÓ DE FLEX/MIN-CONTENT: el contenidor de la taula porta `minWidth: 0` i la taula
          va a `width: 100%`. Un fill de flex té `min-width: auto` per defecte —o sigui, la seva
          amplada mínima de contingut— i una taula amb amplades fixes calculades a mà l'empeny
          fins que desborda la pàgina sense que res avisi. Les columnes es reparteixen en
          PERCENTATGE i el navegador les ajusta; cap número de px cuit a mà. */}
      <div style={{ minWidth: 0, width: '100%' }}>
        <table style={{ borderCollapse: 'collapse', width: '100%', maxWidth: '100%',
                        minWidth: 0, tableLayout: 'fixed', fontSize: '8.5pt' }}>
          <colgroup>
            <col style={{ width: '3%' }} />
            <col style={{ width: '9%' }} />
            <col style={{ width: '6%' }} />
            <col style={{ width: '33%' }} />
            <col style={{ width: '7%' }} />
            <col style={{ width: '7%' }} />
            <col style={{ width: '13%' }} />
            <col style={{ width: '22%' }} />
          </colgroup>
          <thead>
            <tr>
              {[t('fitting.print.col_n'), t('fitting.print.col_layer'), t('fitting.print.col_code'),
                t('fitting.print.col_name')].map(h => <ThPr key={h}>{h}</ThPr>)}
              <ThPr right>
                {t('fitting.print.col_spec')}
                <span style={{ display: 'block', fontWeight: 400, textTransform: 'none',
                               letterSpacing: 0, color: 'var(--text-muted)' }}>{dataSessio}</span>
              </ThPr>
              <ThPr center>{t('fitting.print.col_meas')}</ThPr>
              <ThPr>{t('fitting.print.col_decision')}</ThPr>
              <ThPr>{t('fitting.print.col_comments')}</ThPr>
            </tr>
          </thead>
          <tbody>
            {files.map((l, j) => {
              // La instància ja ÉS anglès canònic (no es tradueix): no li cal cap traductor.
              const inst = etiquetaInstancia(l.instancia)
              return (
                <tr key={l.id}>
                  <TdPr>{desDe + j + 1}</TdPr>
                  <TdPr>{capaEn(l.capa, tEn)}</TdPr>
                  <TdPr><b>{l.nom_fitxa || l.codi || ''}</b></TdPr>
                  {/* L'ÚNICA cel·la que embolcalla: la llei és que una fila creix només si el
                      seu nom ho fa. `keep-all` i `overflow-wrap: normal` perquè talli per
                      PARAULA i no per lletra — un nom partit a mitja paraula no es llegeix. */}
                  <TdPr wrap>{(l.nom_en || l.nom || '')}{inst ? ` · ${inst}` : ''}</TdPr>
                  <TdPr right>{fmt(l.valor_teoric)}</TdPr>
                  {/* MEAS. BUIDA: s'omple a mà, a la sala. */}
                  <TdPr caixa />
                  <TdPr nowrap>
                    {CASELLES.map(k => (
                      <span key={k} style={{ fontSize: '6.8pt', whiteSpace: 'nowrap',
                                             display: 'inline-block', marginRight: 5 }}>
                        <span style={{ display: 'inline-block', width: 9, height: 9,
                                       border: '1px solid var(--text-muted)', marginRight: 3,
                                       verticalAlign: '-1px' }} />{k}
                      </span>
                    ))}
                  </TdPr>
                  <TdPr />
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* LA LLEGENDA VA A CADA PÀGINA: qui té el full 2 a la mà no té el full 1, i sense la
          llegenda les tres caselles són tres sigles sense significat. El PEU I LA SIGNATURA,
          en canvi, es firmen UNA vegada — van només a l'última. */}
      <div style={{ marginTop: 'auto', paddingTop: 9, borderTop: '1px solid var(--border)',
                    fontSize: '7.5pt', color: 'var(--text-muted)', lineHeight: 1.9 }}>
        <div>
          <b>AC</b> = {t('fitting.print.legend_ac')} &nbsp;·&nbsp;
          <b>AD</b> = {t('fitting.print.legend_ad')} &nbsp;·&nbsp;
          <b>RJ</b> = {t('fitting.print.legend_rj')}
        </div>
        {ultima && (
          <div style={{ marginTop: 10 }}>{t('fitting.print.signature')}</div>
        )}
      </div>
    </div>
  )
}

const ThPr = ({ children, right, center }) => (
  <th style={{ background: 'var(--white)', border: 'none',
               borderBottom: '1px solid var(--text-main)', fontSize: '7.5pt',
               textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-main)',
               padding: '5px 4px', textAlign: right ? 'right' : center ? 'center' : 'left',
               verticalAlign: 'bottom' }}>{children}</th>
)

const TdPr = ({ children, right, wrap, nowrap, caixa }) => (
  <td style={{
    borderBottom: '1px solid var(--border)', padding: '2px 5px', fontSize: '8.5pt',
    verticalAlign: 'middle', lineHeight: 1.3, textAlign: right ? 'right' : undefined,
    whiteSpace: wrap ? 'normal' : nowrap ? 'nowrap' : 'nowrap',
    wordBreak: wrap ? 'keep-all' : undefined, overflowWrap: wrap ? 'normal' : undefined,
    overflow: wrap ? undefined : 'hidden',
    ...(caixa && { border: '1px solid var(--text-muted)', background: 'var(--bg-card)' }),
  }}>{children}</td>
)
