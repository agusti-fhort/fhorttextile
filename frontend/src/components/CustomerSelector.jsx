import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { customers } from '../api/endpoints'
import CustomerModal from './CustomerModal'

// Selector de Customer reutilitzable (wizard de model i modal d'import massiu).
// Controlat: props `value` (customer_id o null) + `onChange(id)`. `allowCreate` mostra
// el botó "+ Nou client" (obre CustomerModal). Internament carrega customers.list().
const MONO = 'IBM Plex Mono, monospace'
const selectStyle = {
  // §8c · control de la casa: vora `--line`, radi 6. Anava amb `--gray-l` —un àlies de
  // FARCIMENT fent de vora, en gris fred— i un radi de 4 que no és cap dels tres.
  width: '100%', padding: '8px 10px', borderRadius: 'var(--r-ctrl)', border: '1px solid var(--line)',
  fontFamily: MONO, fontSize: 'var(--fs-body)', background: 'var(--panel)', boxSizing: 'border-box',
}
const ghostBtn = {
  // §5.2 · «+ Nou client» és una acció de la casa que NO completa la feina d'aquesta pantalla:
  // secundària (blanc + vora `--gold-border`). Anava amb `--warn` de tinta I de vora — el
  // TARONJA DEL SEMÀFOR fent de botó, quan la §1 el reserva a la dada.
  background: 'var(--panel)', color: 'var(--text-main)', borderWidth: 1, borderStyle: 'solid',
  borderColor: 'var(--gold-border)',
  borderRadius: 'var(--r-ctrl)', padding: '8px 16px', fontSize: 'var(--fs-body)', fontWeight: 500,
  cursor: 'pointer', fontFamily: MONO,
}

export default function CustomerSelector({ value, onChange, allowCreate = false, onError }) {
  const { t } = useTranslation()
  const [list, setList] = useState([])
  const [showModal, setShowModal] = useState(false)

  // NO s'envia `exclude_self` A PROPÒSIT: el client propi ha de ser seleccionable (en una Marca
  // és el titular dels seus propis models). Només la pàgina Clients filtra, i només si és Estudi.
  useEffect(() => {
    let alive = true
    customers.list({ ordering: 'codi', page_size: 500 })
      .then(r => { if (alive) setList(r.data?.results ?? (Array.isArray(r.data) ? r.data : [])) })
      .catch(() => { if (alive) setList([]) })
    return () => { alive = false }
  }, [])

  return (
    <>
      <div style={{ display: 'flex', gap: 8 }}>
        <select value={value || ''} onChange={e => onChange(e.target.value || null)} style={{ ...selectStyle, flex: 1 }}>
          <option value="">{t('model_wizard.customer_placeholder')}</option>
          {list.map(c => (
            <option key={c.id} value={c.id}>{c.codi} · {c.nom}</option>
          ))}
        </select>
        {allowCreate && (
          <button type="button" onClick={() => setShowModal(true)} style={ghostBtn}>{t('model_wizard.customer_new')}</button>
        )}
      </div>
      {showModal && (
        <CustomerModal mode="create" t={t}
          onCancel={() => setShowModal(false)}
          onSaved={(cust) => { setList(l => [...l, cust]); onChange(String(cust.id)); setShowModal(false) }}
          onError={(text) => { setShowModal(false); if (onError) onError(text) }} />
      )}
    </>
  )
}
