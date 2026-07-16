import { useEffect, useRef, useState } from 'react'

/**
 * SELECCIÓ I ESBORRAT EN BLOC del panell del Taller (QA-TALLER E · T3).
 *
 * Un patró té desenes de trams declarats i pot tenir 27 costures proposades: esborrar-los d'un
 * en un no és una feina, és una penitència. Però el gest en bloc és el gest que més pot destruir
 * d'un sol clic, i per això aquí hi ha tres lleis, no una:
 *
 * 1. **La selecció és PER GRUP.** Esborrar trams i esborrar costures són intencions diferents.
 *    Cap selecció travessa els blocs i **no hi ha cap «esborra-ho tot» global**.
 * 2. **Res cau sense confirmació**, i la confirmació diu el compte i la mena.
 * 3. **El que es reté s'informa**, no es perd: el PROTECT del servidor arriba a la pantalla
 *    id per id.
 *
 * Viu a part de `RelationsPanel` perquè les propostes es pinten al seu propi panell
 * (`ProposalsPanel`) i necessiten la MATEIXA casella: dues caselles diferents per a la mateixa
 * intenció haurien estat dos comportaments que un dia divergeixen.
 */

/**
 * La selecció d'UN grup, i prou.
 *
 * Els ids que ja no hi són surten sols de la selecció. Després d'un esborrat la llista es refà,
 * i una marca que sobrevisqués la seva fila reapareixeria sobre una fila NOVA que ningú no ha
 * triat — i llavors el compte de la paperera prometria una xifra que no és la que cauria.
 *
 * La poda es DERIVA al render, no se sincronitza amb un efecte. Amb un efecte, el render que
 * segueix l'esborrat encara pintaria el compte vell abans de corregir-lo: hi hauria un instant
 * en què la paperera diu «Esborrar 18» sobre disset files. El que no s'ha de veure mai no
 * s'arregla després —no es deixa passar.
 */
export function useSeleccio(ids) {
  const [marcats, setMarcats] = useState(() => new Set())

  const vius = new Set(ids)
  const sel = new Set([...marcats].filter(i => vius.has(i)))

  return {
    sel,
    alterna: id => setMarcats(s => {
      const n = new Set(s)
      if (n.has(id)) n.delete(id)
      else n.add(id)
      return n
    }),
    // El mateix gest marca'ls tots o desmarca'ls tots, segons el que ja hi ha — que és
    // exactament el que la casella indeterminada de la capçalera està dient.
    tots: () => setMarcats(sel.size === ids.length ? new Set() : new Set(ids)),
    buida: () => setMarcats(new Set()),
  }
}

/**
 * Una casella.
 *
 * L'estat INDETERMINAT no és un tercer estat que es pugui triar: és el que la capçalera diu
 * quan la selecció és parcial. No té atribut HTML —només el DOM el sap pintar—, i per això va
 * per ref.
 */
export function Casella({ marcat, indeterminat = false, onChange, etiqueta }) {
  const ref = useRef(null)
  useEffect(() => {
    if (ref.current) ref.current.indeterminate = indeterminat
  }, [indeterminat])

  return (
    <input
      ref={ref}
      type="checkbox"
      checked={marcat}
      onChange={onChange}
      onClick={e => e.stopPropagation()}
      aria-label={etiqueta}
      title={etiqueta}
      style={{ cursor: 'pointer', flexShrink: 0, margin: 0, accentColor: 'var(--gold)' }}
    />
  )
}

/**
 * El que la capçalera d'un grup esborrable porta: la paperera i el seleccionar-los tots.
 *
 * La paperera **només surt quan hi ha selecció**, i porta el COMPTE. Un botó d'esborrar sempre
 * visible és un botó que algú clicarà sense haver triat res; i «Esborrar 18» diu quant ABANS
 * del clic, no després.
 */
export function AccionsGrup({ t, n, total, onTots, onEsborra }) {
  if (!total) return null
  return (
    <>
      {n > 0 && (
        <button
          onClick={onEsborra}
          title={t('pattern.taller.bulk_delete', { count: n })}
          style={{
            display: 'flex', alignItems: 'center', gap: '0.25rem', flexShrink: 0,
            background: 'none', border: '1px solid var(--white)', borderRadius: 4,
            color: 'var(--white)', cursor: 'pointer', padding: '0 5px',
            fontSize: 'var(--fs-caption)',
          }}
        >
          <i className="ti ti-trash" />
          {t('pattern.taller.bulk_delete', { count: n })}
        </button>
      )}
      <Casella
        marcat={n > 0 && n === total}
        indeterminat={n > 0 && n < total}
        onChange={onTots}
        etiqueta={t('pattern.taller.bulk_select_all')}
      />
    </>
  )
}

/**
 * L'INFORME: QUÈ s'ha quedat, i per què.
 *
 * Només parla del que es reté. El que ha caigut ja no és a la llista i dir-ho seria repetir el
 * que la pantalla ja ensenya; el que s'ha quedat, en canvi, es confondria amb un esborrat que
 * no ha anat — i no ho és: és el servidor dient que no.
 */
export function Informe({ t, retinguts, onTanca }) {
  if (!retinguts?.length) return null
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start', gap: '0.35rem',
      fontSize: 'var(--fs-caption)', color: 'var(--warn)',
      background: 'var(--warn-bg)', borderRadius: 4, padding: '3px 6px',
      margin: '0 0 0.35rem',
    }}>
      <i className="ti ti-alert-triangle" style={{ marginTop: 2, flexShrink: 0 }} />
      <span style={{ flex: 1, minWidth: 0 }}>
        {t('pattern.taller.bulk_kept', {
          count: retinguts.length,
          ids: retinguts.map(r => `#${r.id}`).join(', '),
        })}
      </span>
      <button
        onClick={onTanca}
        aria-label={t('app.close')}
        style={{
          background: 'none', border: 'none', cursor: 'pointer',
          color: 'var(--warn)', flexShrink: 0, padding: 0,
        }}
      >
        <i className="ti ti-x" />
      </button>
    </div>
  )
}
