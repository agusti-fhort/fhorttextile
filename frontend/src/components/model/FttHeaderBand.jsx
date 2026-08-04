import { HDR_H_V3, headerLabels } from '../../pages/TechSheetEditor'

// LA CAPÇALERA DE FITXA TÈCNICA, EN HTML — per als fulls que s'imprimeixen fora del canvas.
//
// La fitxa tècnica és Konva + pdf-lib; el full de fitting és una pàgina HTML que va a la
// impressora. Són dos renders, però NO poden ser dues capçaleres: el que el fabricant rep ha de
// portar la mateixa banda, amb les mateixes caixes i els mateixos filets, vingui d'on vingui.
//
// Per això aquí NO hi ha ni una coordenada escrita: totes surten de `HDR_H_V3`, la transcripció
// literal de `docs/spec/capcalera_ftt_v3.md` que ja viu a l'editor de fitxa. Si la spec canvia,
// canvien les dues alhora. La llei de la casa és «no s'interpreta, es MESURA», i mesurar dues
// vegades és exactament com es diverge.
//
// ESCALA: la spec dona pt de document i la banda fa 784,7pt d'ample, que és el contingut d'un A4
// APAÏSAT amb els marges de la fitxa. El full de fitting té els seus (45px), o sigui que la banda
// s'hi encabeix CONTAIN: es dibuixa a mida natural i s'escala en bloc. Mai s'estira ni es retalla
// —seria deformar un disseny aprovat—, i el logo hi va a dins amb la seva caixa intocable.

const PT = 96 / 72   // 1pt de document = 1,3333px de pantalla a 96 dpi

const ESTIL = {
  lbl: { cos: 7, color: 'var(--text-muted)', ls: '0.02em', pes: 400 },
  v10: { cos: 10, color: 'var(--text-main)', pes: 400 },
  v12: { cos: 12, color: 'var(--text-main)', pes: 400 },
  v18: { cos: 18, color: 'var(--text-main)', pes: 400 },
}

/**
 * @param {number} amplada  amplada disponible en px; la banda s'hi escala CONTAIN.
 * @param {object} dades    { nom, temporada, collection, codi_intern, codi_client, run,
 *                            tallaActiva, target, data, format, pagina }
 * @param {string} logoUrl  asset del client (caixa intocable: mai se'n canvia mida ni proporció)
 * @param {function} t      traductor; les etiquetes de la banda surten de `headerLabels`
 */
export default function FttHeaderBand({ amplada, dades, logoUrl = null, t }) {
  const S = HDR_H_V3
  const natW = S.W * PT
  const natH = S.H * PT
  const escala = amplada ? amplada / natW : 1
  const lbls = headerLabels(t)

  const filet = '0.5px solid var(--text-main)'
  const px = (v) => v * PT

  return (
    <div style={{ width: amplada, maxWidth: '100%', height: natH * escala, overflow: 'hidden' }}>
      <div style={{
        position: 'relative', width: natW, height: natH,
        transform: `scale(${escala})`, transformOrigin: 'top left',
        border: filet, boxSizing: 'border-box',
        fontFamily: 'IBM Plex Mono, ui-monospace, monospace',
      }}>
        {/* Divisors verticals de la spec. Cap línia doble: les caixes comparteixen filet. */}
        {S.divisors.map(x => (
          <div key={x} style={{ position: 'absolute', left: px(x), top: 0, bottom: 0, borderLeft: filet }} />
        ))}

        {/* C1 · LA CAIXA DEL LOGO és intocable (regla amb acta): l'asset s'hi escala CONTAIN,
            proporcions intactes, alineat a l'esquerra i centrat verticalment. Sense asset, la
            caixa es queda buida — mai s'omple amb text ni es reaprofita l'espai. */}
        <div style={{
          position: 'absolute', left: px(S.logo.x), top: px(S.logo.y),
          width: px(S.logo.w), height: px(S.logo.h),
        }}>
          {logoUrl && (
            <img src={logoUrl} alt=""
              style={{ width: '100%', height: '100%', objectFit: 'contain', objectPosition: 'left center' }} />
          )}
        </div>

        {S.camps.map((c, i) => {
          const st = ESTIL[c.e] || ESTIL.v10
          const comu = {
            position: 'absolute', left: px(c.x), top: px(c.y),
            maxWidth: px(c.r - c.x), whiteSpace: 'nowrap', overflow: 'hidden',
            fontSize: px(st.cos), lineHeight: 1, color: st.color,
            letterSpacing: st.ls, fontWeight: st.pes,
          }
          // El RUN porta la talla activa subratllada amb una línia pròpia de l'amplada exacta
          // del glif (la spec ho demana com a prim, no com a `text-decoration`, perquè el gruix
          // i la separació de la línia base són part del disseny).
          if (c.e === 'run') {
            const talles = String(dades.run || '').split('·').map(s => s.trim()).filter(Boolean)
            return (
              <div key={i} style={{ ...comu, fontSize: px(ESTIL.v12.cos), color: ESTIL.v12.color }}>
                {talles.map((s, k) => (
                  <span key={s}>
                    {k > 0 && <span>{' · '}</span>}
                    <span style={s === dades.tallaActiva ? {
                      fontWeight: 700,
                      borderBottom: `${px(1.2)}px solid var(--text-main)`,
                      paddingBottom: px(2),
                    } : undefined}>{s}</span>
                  </span>
                ))}
              </div>
            )
          }
          return <div key={i} style={comu}>{c.k ? lbls[c.k] : (dades[c.f] ?? '')}</div>
        })}
      </div>
    </div>
  )
}
