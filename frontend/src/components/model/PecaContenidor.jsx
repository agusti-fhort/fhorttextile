import { useTranslation } from 'react-i18next'

// SET-2/T7-A · EL CONTENIDOR DE PEÇA de la superfície de Mesures.
//
// D'ON VE: era `DependencyPanel`, una barra grisa d'una sola línia que penjava SOTA la barra
// crema de resum del model i AL COSTAT de la taula, no al voltant. La maqueta validada per
// Agus (10/08) el converteix en el CONTENIDOR de la peça: la taula de mesures viu a dins, i
// la barra crema de resum desapareix perquè el que deia ja és a la capçalera de la pàgina
// (referència + nom) o baixa aquí (el run de talles).
//
// ⚠️ FASE A (avui) — AMB UNA SOLA PEÇA, que és el 100% del corpus, NO hi ha fila superior de
// nom/caret/llapis: aquesta pàgina ha de quedar funcionalment idèntica a la d'abans, només
// més neta. La fila superior és de la Fase B i neix quan el model té 2+ peces, cosa que avui
// no pot passar (13 comportes CHECK congelen `garment` a '' i `ModelGarment` no existeix).
// Re-verificar amb: `grep -rn "class ModelGarment" backend/`.
//
// ⚠️ EL QUE NO HI ÉS, I PER DECISIÓ (Agus, 2026-08-11): `target` i `construction` («Dona»,
// «Teixit pla»). Els deia la barra crema i NO tornen a cap superfície de treball — són
// atributs de DEFINICIÓ i viuen al Resum (pas Peça), que és on s'editen. Una pantalla de
// mesura necessita dependència, joc de regles i run, i res més. Si algun dia es decideix que
// tornin, el lloc és aquesta fila de dependència, no una barra pròpia.
//
// EL RUN NO PORTA RÈTOL. La talla base es diu amb TIPOGRAFIA (negreta + subratllat), no amb
// un «Base: S» al davant — el mateix criteri que la fitxa tècnica, on la columna de la base
// es marca sobre ella mateixa i no en un títol. La barra crema sí que el portava escrit.
//
// `accioJoc` — SLOT per a l'acció sobre el JOC DE REGLES, al costat mateix del nom que mostra
// (Graduació hi posa «Canviar joc»). És opcional: a Mesures i a Escalat la fila és de lectura,
// i el rètol italic ja ho diu. En Fase B cada contenidor de peça portarà el SEU, perquè cada
// peça va a la seva elecció de graduació.
export default function PecaContenidor({ model, children, accioJoc = null }) {
  const { t } = useTranslation()
  if (!model) return null

  const gtItem = model.garment_type_item_nom
    ? `${model.garment_type_item_nom}${model.garment_type_item_code ? ` (${model.garment_type_item_code})` : ''}`
    : null
  // LA REFERÈNCIA INTERNA SURT DE LA CADENA: `codi_intern` hi era com a últim graó i és
  // exactament el que la capçalera de la pàgina ja diu, en gran, dues línies més amunt.
  // La dependència és d'on penja el model, no com es diu.
  const chain = [model.garment_type_nom, gtItem].filter(Boolean)
  // El run viatja com a cadena unida per '·' (`Model.size_run_model`); partir-la per aquest
  // separador és el que ja fan `FittingDetail.jsx:636` i `TechSheetEditor.jsx:1109`.
  const talles = (model.size_run_model || '').split('·').map(s => s.trim()).filter(Boolean)
  const base = (model.base_size_label || '').trim()

  return (
    <div style={{
      border: '1px solid var(--line)', borderRadius: 'var(--r-card)',
      background: 'var(--panel)', marginBottom: 12,
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
        padding: '9px 14px', borderBottom: '1px solid var(--line)',
        fontSize: 'var(--fs-body)',
      }}>
        <i className="ti ti-sitemap" style={{ color: 'var(--text-soft)' }} />
        <span style={{ color: 'var(--text-soft)' }}>{t('dependency.title')}:</span>
        {chain.map((c, i) => (
          <span key={i} style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
            {i > 0 && <i className="ti ti-chevron-right" style={{ fontSize: 11, color: 'var(--text-soft)' }} />}
            <span style={{ color: 'var(--text-main)' }}>{c}</span>
          </span>
        ))}
        <span style={{ marginLeft: 16, color: 'var(--text-soft)' }}>{t('dependency.ruleset')}:</span>
        <span style={{ color: model.grading_rule_set_nom ? 'var(--gold)' : 'var(--text-soft)' }}>
          {model.grading_rule_set_nom || t('dependency.no_ruleset')}
        </span>
        {accioJoc}
        {!accioJoc && (
          // La pista de «lectura» NOMÉS quan la fila no porta l'acció: amb el botó al costat,
          // dir que no es pot editar aquí seria contradir-se a un pam de distància.
          <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)', fontStyle: 'italic' }}>
            {t('dependency.editable_hint')}
          </span>
        )}
        {talles.length > 0 && (
          // `marginLeft:auto` = el run s'arrambla a la DRETA de la mateixa fila. Les talles NO
          // es tradueixen mai: són dades de domini.
          <span style={{ marginLeft: 'auto', display: 'inline-flex', gap: 6, fontSize: 11 }}>
            {talles.map(tl => (
              <span key={tl} style={tl === base
                ? { color: 'var(--text-main)', fontWeight: 700, textDecoration: 'underline', textUnderlineOffset: 3 }
                : { color: 'var(--text-soft)' }}>{tl}</span>
            ))}
          </span>
        )}
      </div>
      <div style={{ padding: '10px 12px 12px' }}>{children}</div>
    </div>
  )
}
