import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { poms } from '../../api/endpoints'

/**
 * Cercador de POMs per ancorar-ne un a la geometria.
 *
 * Reutilitza l'ENDPOINT de cerca que ja existeix (`poms/cerca/`), no el `POMBrowser`:
 * aquell és un gestor de membresies d'un GarmentTypeItem (crea, ordena, marca com a clau)
 * i portar-lo aquí seria arrossegar mitja pantalla per triar una fila d'una llista.
 *
 * NOMENCLATURA (convenció de la casa): el codi canònic mana i el nom en la llengua de
 * l'usuari va a sota, en gris petit. Qui anota busca pel nom que coneix; el que queda
 * ancorat al patró és el codi.
 */
export default function POMPicker({ onTria, onCancel }) {
  const { t } = useTranslation()
  const [q, setQ] = useState('')
  const [resultats, setResultats] = useState([])
  const [carregant, setCarregant] = useState(false)
  const inputRef = useRef(null)

  useEffect(() => { inputRef.current?.focus() }, [])

  useEffect(() => {
    const timer = setTimeout(() => {
      setCarregant(true)
      poms.cerca({ q, page_size: 25 })
        .then(({ data }) => setResultats(data.results || data || []))
        .catch(() => setResultats([]))
        .finally(() => setCarregant(false))
    }, 220)   // el teclat va més ràpid que la xarxa
    return () => clearTimeout(timer)
  }, [q])

  return (
    <div style={{
      position: 'absolute', zIndex: 30, top: 40, left: 0,
      width: 340, maxHeight: 380, overflow: 'auto',
      background: 'var(--white)', border: '1px solid var(--gold)',
      borderRadius: 6, boxShadow: '0 4px 16px rgba(0,0,0,0.12)', padding: '0.6rem',
    }}>
      <div style={{ display: 'flex', gap: '0.4rem', marginBottom: '0.5rem' }}>
        <input
          ref={inputRef}
          value={q}
          onChange={e => setQ(e.target.value)}
          placeholder={t('pattern.pom_search')}
          style={{
            flex: 1, fontSize: 'var(--fs-body)', padding: '0.3rem 0.5rem',
            border: '1px solid var(--border)', borderRadius: 4,
          }}
        />
        <button
          onClick={onCancel}
          aria-label={t('app.cancel')}
          style={{ background: 'none', border: 'none', cursor: 'pointer' }}
        >
          <i className="ti ti-x" />
        </button>
      </div>

      {carregant && (
        <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', margin: 0 }}>
          {t('app.loading')}
        </p>
      )}
      {!carregant && resultats.length === 0 && (
        <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', margin: 0 }}>
          {t('pattern.pom_none')}
        </p>
      )}

      {resultats.map(pom => (
        <button
          key={pom.id}
          onClick={() => onTria(pom)}
          style={{
            display: 'block', width: '100%', textAlign: 'left', cursor: 'pointer',
            background: 'none', border: 'none', borderBottom: '1px solid var(--border)',
            padding: '0.4rem 0.2rem',
          }}
        >
          <div style={{ fontSize: 'var(--fs-body)', fontWeight: 600 }}>
            {pom.codi_client || pom.pom_code}
          </div>
          <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>
            {pom.nom_client || pom.nom}
          </div>
        </button>
      ))}
    </div>
  )
}
