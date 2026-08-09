
import { useState, useEffect } from "react"
import { useTranslation } from "react-i18next"
import useAuthStore from "../store/auth"

const API = import.meta.env.VITE_API_URL || ""

export function UnitToggle() {
  const { t } = useTranslation()
  const token = useAuthStore(s => s.token) || localStorage.getItem('access_token')
  const [unit, setUnit] = useState('CM')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetch(`${API}/api/v1/tenant-config/`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(d => setUnit(d.unitat_mesura || 'CM'))
      .catch(() => {})
  }, [token])

  const toggle = async () => {
    const nou = unit === 'CM' ? 'INCH' : 'CM'
    setSaving(true)
    try {
      const r = await fetch(`${API}/api/v1/tenant-config/`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ unitat_mesura: nou }),
      })
      if (r.ok) {
        setUnit(nou)
        // Notificar la resta de l'app
        window.dispatchEvent(new CustomEvent('unit-changed', { detail: { unit: nou } }))
      }
    } catch { /* preferència d'unitats: no poder-la desar no és fatal */ }
    setSaving(false)
  }

  // §8b-quater · el commutador viu a la TOP BAR, que passa conformitat en aquest tram.
  //
  // ⚠️ EL TÍTOL ERA UNA CADENA CATALANA A PÈL («Canviar a Polzades (inch)»), fora de `t()` i
  // per tant idèntica en anglès i en castellà. És la porta d'i18n de la casa, i aquesta és
  // l'única frase de cara a l'usuari del component: ara surt de `topbar.unit_switch` i el nom
  // de la unitat el donen les claus que la pantalla de Configuració general ja tenia
  // (`config_general.unit_cm` / `unit_inch`), que és on aquest valor es tria de debò.
  //
  // I la pell: aquí hi havia `#f5e6d0` (== `--gold-pale`, ELIMINAT del sistema per la §1),
  // `#f5f0ea`, `--border` i `--text-muted` (tots dos DEPRECATS per la §1b) i un radi de 4px
  // que no és cap dels tres de la casa. Ara és el control de la casa (§8c: vora `--line`,
  // radi `--r-ctrl`, fons `--panel`) i **cap dels dos estats porta daurat**: la unitat vigent
  // ja la diu la paraula escrita, i pintar-la de marca seria marca pintant una dada (§8c).
  const altra = unit === 'CM' ? t('config_general.unit_inch') : t('config_general.unit_cm')
  return (
    <button
      onClick={toggle}
      disabled={saving}
      title={t('topbar.unit_switch', { unitat: altra })}
      style={{
        display: 'flex', alignItems: 'center', gap: 4,
        padding: '4px 10px', borderRadius: 'var(--r-ctrl)',
        background: 'var(--panel)',
        color: 'var(--text-main)',
        border: '1px solid var(--line)',
        fontSize: 'var(--fs-body)',
        cursor: saving ? 'not-allowed' : 'pointer',
        transition: 'all .15s',
      }}
    >
      <span style={{ fontWeight: 600 }}>{unit === 'CM' ? 'cm' : 'inch'}</span>
      <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)' }}>
        {unit === 'CM' ? '→ inch' : '→ cm'}
      </span>
    </button>
  )
}

// Hook per consumir la unitat actual
export function useUnit() {
  const token = useAuthStore(s => s.token) || localStorage.getItem('access_token')
  const [unit, setUnit] = useState('CM')

  useEffect(() => {
    fetch(`${API}/api/v1/tenant-config/`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(d => setUnit(d.unitat_mesura || 'CM'))
      .catch(() => {})

    const handler = (e) => setUnit(e.detail.unit)
    window.addEventListener('unit-changed', handler)
    return () => window.removeEventListener('unit-changed', handler)
  }, [token])

  const format = (val_cm) => {
    if (val_cm == null) return '—'
    if (unit === 'INCH') return `${(val_cm * 0.393701).toFixed(2)}"` 
    return `${val_cm}cm`
  }

  return { unit, format }
}
