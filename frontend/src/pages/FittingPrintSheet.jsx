import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

import { fittingSessions, pieceFittings, models } from '../api/endpoints'
import FttHeaderBand from '../components/model/FttHeaderBand'
import { etiquetaCapa, etiquetaInstancia } from '../utils/capaInstancia'
import { useEstatDiccionari } from '../utils/diccionariMesuresFont'
import { identitatMesura } from '../utils/identitatMesura'

// EL FULL DE FITTING QUE ES PORTA A LA PROVA — A4 APAÏSAT, per omplir A MÀ.
//
// No és una exportació de la pantalla: és el paper que la Montse porta a la sala i que després
// torna cap al fabricant. Per això la columna de la mesura surt BUIDA (s'escriu amb bolígraf) i
// els tres veredictes són caselles per marcar, no text.
//
// A4 APAÏSAT REAL: 297×210 mm amb 15 mm de marge perimetral.
//
// 🚨 UNA SOLA GEOMETRIA, EN MIL·LÍMETRES, I LA PANTALLA LA DERIVA. Abans hi havia dues
// declaracions —px cuits aquí (1123×794, marge 45) i mm a `@page`— i el comentari d'aquest
// bloc en feia una virtut: «si les dues no diguessin el mateix, el que es veu i el que surt
// serien dues coses». Deien el mateix per a A4 amb marge de 12 mm i prou. El dia que el marge
// va passar a 15 mm, l'àrea imprimible va baixar a 267 mm (1009 px) mentre la banda seguia
// dibuixant-se contra els 1033 px cuits: el 2,4% que sobrava se'l menjava l'`overflow: hidden`
// de la capçalera i **la data de la caixa C4 desapareixia del paper sense avisar** (mesurat al
// PDF real: `16/08/2026` present amb l'escala bona, absent amb la cuita).
//
// Per això els px ja no s'escriuen: es DERIVEN dels mm, que és el que la impressora obeeix.
const MM = 96 / 25.4          // px de pantalla per mil·límetre, a 96 dpi
const MARGE_MM = 15           // marge perimetral, el mateix número que `@page`
const A4_W = 297 * MM
const A4_H = 210 * MM
const MARGE = MARGE_MM * MM

// AQUÍ HI HAVIA `FILES_PER_PAGINA = 18`, i se n'ha anat amb la paginació a mà. Es declarava
// «un límit CONSERVADOR a posta», amb l'argument que una pàgina sencera de noms de dues línies
// encara hi cabria: mesurat, era fals —18 files amb un nom de dues línies ja donaven 695 px de
// 695 disponibles, i la llegenda i la signatura sortien retallades de la impressora sense que
// res ho anunciés (Q6)—. Un comptador de FILES no pot mesurar una ALÇADA que depèn del text.
// Ara qui talla és el navegador, que sí que la sap.

// ELS TRES VEREDICTES, en anglès i abreujats com al paper: és el que el fabricant marca.
const CASELLES = ['AC', 'AD', 'RJ']

const fmt = (n) => (n == null || n === '' ? '' : Number(n).toFixed(1))

// LES CAPES VAN EN ANGLÈS AL FULL (D-31.22), sigui quin sigui l'idioma de qui l'ha generat: el
// full viatja cap al fabricant i el fabricant llegeix anglès. El vocabulari NO es reescriu aquí
// —surt del mateix `etiquetaCapa` que la pantalla, i per tant del diccionari de la BD (F2.2)— i
// el que canvia és només l'idioma que se li demana.
const capaEn = (slug, dicc) => etiquetaCapa(slug, dicc, 'en')

export default function FittingPrintSheet() {
  const { sessionId, modelId } = useParams()
  // El vocabulari de capes, de la BD (F2.2). Si no arriba, el full ensenya el slug cru: mai
  // una paraula inventada en un document que va al fabricant.
  const { dicc } = useEstatDiccionari()
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

  const dataSessio = (dades.sessio?.data || '').split('-').reverse().join('/')
  const capcalera = {
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
    // EL «i/n» DE LA CAIXA C4 VA BUIT, I ÉS UNA DECISIÓ, NO UN OBLIT (Agus, 17/08). Qui pagina
    // ara és el navegador —la taula corre i ell talla on toca—, i Chrome NO sap dir-nos per
    // quina pàgina va: els tres mecanismes que ho haurien de fer estan mesurats i fallen tots
    // (`@page { @bottom-right }` no s'imprimeix; `counter(page)` dins del thead i dins d'un
    // `position: fixed` donen `0/0`). Comptar-les nosaltres voldria dir tornar a partir les
    // files a mà, que és exactament el que aquest commit desmunta. Els tècnics no el demanen,
    // com no demanen el peu: v. DIAGNOSI_S42 §Q9.1.3.
    pagina: '',
  }

  return (
    <div className="ftt-wrap" style={{ background: 'var(--bg-muted)', padding: '20px 0', minHeight: '100vh' }}>
      {/* `@page` en mm i `size: landscape` és el que fa que el navegador pagini com el full està
          dibuixat. `print-color-adjust` perquè els filets i els fons de casella no desapareguin
          en imprimir (per defecte el navegador els treu «per estalviar tinta»). */}
      <style>{`
        @page { size: A4 landscape; margin: 15mm; }
        @media print {
          body { background: #fff; }
          .ftt-noprint { display: none !important; }
          /* A LA IMPRESSORA, ELS MARGES ELS POSA @page — NO EL FULL.
             A pantalla el full es dibuixa com el paper que és (297×210 mm amb 15 mm de vora)
             perquè es vegi què s'endurà. En imprimir, aquesta mateixa vora se SUMARIA als 15 mm
             d'@page i el full no cabria a l'àrea imprimible: cada pàgina en vessava una de mig
             buida. Aquí es treu la vora pròpia i s'ocupa l'àrea imprimible sencera. */
          /* El CONTENIDOR també desapareix. Duia el fons de la pantalla, un encoixinat i un
             min-height de 100vh: tot això s'imprimeix i acaba repartit en pàgines mig buides. */
          .ftt-wrap { padding: 0 !important; min-height: 0 !important; background: #fff !important; }
          /* 🚨 NI ALÇADA FIXA NI OVERFLOW HIDDEN. El full ja no és una pila de divs d'una
             pàgina cadascun: és UNA taula que corre i que el navegador talla on toca. Amb una
             alçada de 180 mm i overflow hidden a sobre, tot el que passés de la primera pàgina
             es retallaria EN SILENCI —que és el mode de fallada que aquest fitxer ja va pagar
             un cop amb la llegenda i la signatura (Q6: 695 px de 695)—. */
          .ftt-full {
            box-shadow: none !important; border: none !important; margin: 0 !important;
            width: 100% !important; min-height: 0 !important; height: auto !important;
            padding: 0 !important; overflow: visible !important;
          }
        }
        /* LA CAPÇALERA ES REPETEIX SOLA perquè viu al THEAD, i la llegenda al TFOOT: és el
           navegador qui les torna a pintar a cada pàgina, sense que ningú compti res. Els dos
           display hi són explícits encara que siguin el valor per defecte — qualsevol regla que
           els toqués mataria la repetició sense dir-ho. I cap fila es parteix per la meitat
           entre dues pàgines: una mesura tallada horitzontalment no es llegeix. */
        .ftt-full thead { display: table-header-group; }
        .ftt-full tfoot { display: table-footer-group; }
        .ftt-full tr { page-break-inside: avoid; break-inside: avoid; }
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

      <Full files={files} capcalera={capcalera} dataSessio={dataSessio}
        logoUrl={ple.customer_logo || null} t={t} tEn={tEn} dicc={dicc} />
    </div>
  )
}

// EL FULL SENCER — UNA taula que corre, no una pila de pàgines.
//
// Abans això es deia `Pagina` i el nom era honest: el JS partia les files de divuit en divuit
// i en pintava un div per pàgina, capçalera inclosa. Divuit era un número escrit a mà, i un
// número no pot mesurar una alçada que depèn del text: amb noms de dues línies el full vessava
// (Q6), i amb les files-títol de peça partiria en dues pàgines un full que en necessita una.
//
// Ara qui talla és el navegador, i la capçalera es repeteix perquè viu al `thead` —mesurat amb
// el pipeline d'impressió real: la banda surt idèntica a cada pàgina, al mateix punt, i el
// tbody hi arrenca sempre just a sota (44,64 mm del cantell)—. El preu, decidit i acceptat, és
// que ningú pot numerar les pàgines: v. el camp `pagina` a la capçalera.
function Full({ files, capcalera, dataSessio, logoUrl, t, tEn, dicc }) {
  const ampladaUtil = A4_W - MARGE * 2
  return (
    <div className="ftt-full" style={{
      width: A4_W, minHeight: A4_H, padding: MARGE, margin: '0 auto 16px',
      background: 'var(--white)', border: '1px solid var(--border)',
      boxShadow: '0 1px 4px rgba(0,0,0,.07)', boxSizing: 'border-box',
      display: 'flex', flexDirection: 'column',
      fontFamily: 'IBM Plex Mono, ui-monospace, monospace', color: 'var(--text-main)',
    }}>
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
          {/* 🚨 LA CAPÇALERA ÉS EL `thead`, I PER AIXÒ ES REPETEIX SOLA.
              Abans la banda era germana de la taula dins d'un div per pàgina i qui la tornava a
              pintar era el bucle de paginació. Aquí dins, el navegador la repeteix a cada
              pàgina d'impressió pel seu compte i el tbody hi arrenca just a sota, sempre a la
              mateixa alçada, sense que ningú hagi de mesurar res.
              La banda no és una cel·la de la graella: ocupa les vuit columnes i porta la seva
              pròpia geometria (spec v3), o sigui que el `th` que la conté no ha de posar-hi ni
              vora ni encoixinat — només fer-li lloc. */}
          <thead>
            <tr>
              <th colSpan={8} style={{ padding: 0, border: 'none' }}>
                <FttHeaderBand amplada={ampladaUtil} dades={capcalera} logoUrl={logoUrl} t={t} />
              </th>
            </tr>
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
                  <TdPr>{j + 1}</TdPr>
                  <TdPr>{capaEn(l.capa, dicc)}</TdPr>
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

          {/* LA LLEGENDA VA A CADA PÀGINA: qui té el full 2 a la mà no té el full 1, i sense la
              llegenda les tres caselles són tres sigles sense significat. La promesa és la
              mateixa d'abans, però ara la manté el `tfoot` en comptes del bucle de pàgines —el
              navegador el repeteix igual que el `thead`—, i és l'única manera que li quedava:
              fora de la taula sortiria UN sol cop, al final de tot. */}
          <tfoot>
            <tr>
              <td colSpan={8} style={{ paddingTop: 9, borderTop: '1px solid var(--border)',
                                       fontSize: '7.5pt', color: 'var(--text-muted)',
                                       lineHeight: 1.9 }}>
                <b>AC</b> = {t('fitting.print.legend_ac')} &nbsp;·&nbsp;
                <b>AD</b> = {t('fitting.print.legend_ad')} &nbsp;·&nbsp;
                <b>RJ</b> = {t('fitting.print.legend_rj')}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      {/* LA SIGNATURA ES FIRMA UNA VEGADA i per això es queda FORA de la taula: aquí baix del
          flux, o sigui a l'última pàgina i enlloc més. Abans ho decidia un `ultima` que sortia
          de la paginació a mà; ara ho decideix el lloc on està escrita, que no es pot
          equivocar. */}
      <div style={{ marginTop: 10, fontSize: '7.5pt', color: 'var(--text-muted)' }}>
        {t('fitting.print.signature')}
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
