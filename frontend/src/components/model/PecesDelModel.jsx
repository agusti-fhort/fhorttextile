import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { models } from '../../api/endpoints'
import { calFilaDePeca } from '../../utils/pecaDefinicio'
import PecaContenidor from './PecaContenidor'

// LES PRENDES D'UN MODEL A UNA SUPERFÍCIE DE TREBALL — SET-2/T7-B2b (12/08).
//
// ── EL BUG QUE AQUEST FITXER TANCA ────────────────────────────────────────────────────────
// B2 va construir la fila superior a `PecaContenidor` darrere de dos props (`peca` i
// `mesDunaPeca`) amb valors per defecte segurs... i **cap dels tres punts de muntatge els va
// passar mai**. Mesures, Escalat i Graduació munten `<PecaContenidor model={model}>` i prou, o
// sigui que `mesDunaPeca` sempre valia `false` i la fila no naixia MAI, tingués el model les
// prendes que tingués. El símptoma que va veure l'Agus —el 1320 amb dues peces en mode
// una-peça— no era una condició mal calculada: era una condició que **ningú no alimentava**.
//
// 🔑 I LA CAUSA D'ARREL: aquestes tres superfícies **no consumeixen `GET /peces/`**. Van néixer
// abans que l'endpoint existís, i l'únic lloc de la casa que el crida és el Resum. Un predicat
// que el servidor resol en un sol lloc (`te_mes_duna_peca`) no serveix de res si la pantalla
// que l'ha d'obeir no el demana mai. Per això el remei no és passar dos props a mà a tres
// llocs —tornaria a divergir— sinó **un sol component que demana la llista i reparteix**.
//
// ── QUÈ FA ───────────────────────────────────────────────────────────────────────────────
// Demana les prendes i pinta UN `PecaContenidor` PER PEÇA, cadascun amb la seva fila superior i
// amb el SEU joc i el SEU run (els EFECTIUS que el contracte serveix: els del Pantaló són els
// del model perquè els hereta, i això és exactament el que s'ha de veure).
//
// `children` és una funció `(peca) => cos`: el cos d'una prenda no és el mateix que el d'una
// altra i qui el sap fer és la superfície, no aquest component.
//
// ⚠️ MAI DEIXA LA PANTALLA EN BLANC. Mentre carrega —i si la crida falla— es pinta UN contenidor
// sense fila, que és EXACTAMENT la pantalla d'abans d'aquest canvi. Una superfície de treball no
// pot dependre d'una segona crida per ensenyar la taula que ja té: el pitjor que pot passar si
// `/peces/` no contesta és que no es vegi la fila de peça, no que no es vegi la feina.
export default function PecesDelModel({ model, accioJoc = null, accionsPeca = null, children }) {
  const [peces, setPeces] = useState(null)
  const id = model?.id

  useEffect(() => {
    if (!id) return undefined
    let viu = true
    models.peces(id)
      .then(r => { if (viu) setPeces(r.data?.peces || []) })
      .catch(() => { if (viu) setPeces([]) })
    return () => { viu = false }
  }, [id])

  if (!model) return null

  // Encara no ho sabem (o ha fallat): la pantalla de sempre, sense fila.
  if (!peces || peces.length === 0) {
    return (
      <PecaContenidor model={model} accioJoc={accioJoc} accionsPeca={accionsPeca?.(null)}>
        {children(null)}
      </PecaContenidor>
    )
  }

  // La llei («la fila neix amb la SEGONA prenda») viu a `utils/pecaDefinicio` amb banc
  // propi, no com a comparació solta aquí: ja es va perdre una vegada dins d'un JSX.
  const mesDunaPeca = calFilaDePeca(peces)
  return (
    <>
      {peces.map(peca => (
        <PecaContenidor key={peca.codi || 'base'} model={model} peca={peca}
          mesDunaPeca={mesDunaPeca}
          // L'acció sobre el joc de regles és de la MARE mentre la porta d'escriptura d'una
          // peça no arribi a aquestes superfícies: el Resum ja la té, i tenir-ne dues seria
          // tenir dues autories del mateix camp (el mateix argument que el llapis que NAVEGA).
          accioJoc={peca.es_mare ? accioJoc : null}
          accionsPeca={accionsPeca?.(peca)}>
          {children(peca)}
        </PecaContenidor>
      ))}
    </>
  )
}

/**
 * EL COS D'UNA PRENDA QUE ENCARA NO POT TENIR RES — i que ho ha de DIR.
 *
 * Fins al #12 cap fila de mesura pot existir per a una peça que no sigui la mare: les comportes
 * `*_garment_gate_set2` ho impedeixen a la base. O sigui que aquest buit no és un buit
 * qualsevol: **és un buit garantit per construcció**, i té una data de caducitat.
 *
 * ⚠️ PER QUÈ ES DIU EL MOTIU I NO ES DEIXA LA TAULA MUDA: la llei del vocabulari (F22) separa
 * «no en té» de «no ho hem carregat», i una taula buida sense frase les confon. Qui obri el
 * Pantaló ha de saber que el contenidor és correcte i que la feina encara no s'hi pot fer.
 *
 * 🚩 EL DIA DEL #12 AIXÒ S'HA DE SUBSTITUIR per la taula de debò filtrada per `garment` — les
 * files ja porten l'eix des de R11 i la identitat de fila ja hi creix (T6b). No és un placeholder
 * decoratiu: és l'estat real d'avui, i el fitxer que el pinta és el que s'ha d'anar a buscar.
 */
export function CosPecaSenseMesures() {
  const { t } = useTranslation()
  return (
    <p style={{
      margin: 0, padding: '10px 2px', fontSize: 'var(--fs-body)',
      color: 'var(--text-soft)', fontStyle: 'italic',
    }}>
      {t('peca.sense_mesures')}
    </p>
  )
}
