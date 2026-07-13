import { useTranslation } from 'react-i18next'

/**
 * Definir un tram: quin dels dos arcs, i com se'n diu.
 *
 * **Dos punts d'una vora tancada no defineixen un tram: en defineixen DOS** — l'arc que va
 * de A a B i el que hi torna per l'altre costat. Cap dels dos és «el bo» en abstracte:
 * depèn de quina costura s'estigui declarant. Per això es veuen tots dos, amb la seva
 * longitud, i es tria. En una vora oberta només n'hi ha un, i llavors no es pregunta res.
 *
 * El nom no és decoració: un tram és el vocabulari amb què després es cus, i «Tram 3» és
 * pitjor que «costura lateral» el dia que algú hagi de triar-lo d'una llista.
 */
export default function SegmentEditor({
  arcs, arcTriat, onTriaArc, nom, onNom, onCrea, onCancela, creant,
}) {
  const { t } = useTranslation()
  const cm = (mm) => (mm / 10).toFixed(1)

  const chip = (actiu) => ({
    background: actiu ? 'var(--gold)' : 'var(--white)',
    color: actiu ? 'var(--white)' : 'var(--text-main)',
    border: `1px solid ${actiu ? 'var(--gold)' : 'var(--border)'}`,
    borderRadius: 4, padding: '0.25rem 0.6rem', cursor: 'pointer',
    fontSize: 'var(--fs-caption)', fontFamily: 'var(--mono)',
  })

  return (
    <div style={{
      display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap',
      background: 'var(--bg-muted)', borderRadius: 4, padding: '0.4rem 0.6rem',
      fontSize: 'var(--fs-caption)', flexShrink: 0,
    }}>
      {arcs.map((arc, i) => (
        <button key={i} onClick={() => onTriaArc(i)} style={chip(i === arcTriat)}>
          {t(arc.unic ? 'pattern.taller.arc_only'
            : arc.arcLlarg ? 'pattern.taller.arc_long' : 'pattern.taller.arc_short',
            { cm: cm(arc.longitud) })}
        </button>
      ))}

      <label style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', flex: 1 }}>
        {t('pattern.taller.segment_name')}
        <input
          autoFocus
          value={nom}
          onChange={e => onNom(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && nom.trim()) onCrea() }}
          style={{
            flex: 1, minWidth: 120, maxWidth: 240,
            fontSize: 'var(--fs-caption)', padding: '0.2rem 0.4rem',
            border: '1px solid var(--border)', borderRadius: 4,
          }}
        />
      </label>

      <button onClick={onCancela} style={chip(false)}>
        {t('app.cancel')}
      </button>
      <button
        onClick={onCrea}
        disabled={creant || !nom.trim()}
        style={{
          ...chip(!creant && !!nom.trim()),
          opacity: creant || !nom.trim() ? 0.5 : 1,
          cursor: creant || !nom.trim() ? 'not-allowed' : 'pointer',
          fontFamily: 'inherit',
        }}
      >
        <i className="ti ti-check" /> {t('pattern.taller.segment_create')}
      </button>
    </div>
  )
}
