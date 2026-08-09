import { useEffect, useState } from 'react'

// Data d'emissió d'un document comercial, editable in situ (2026-07-27). Un sol component per a
// les tres fitxes (oferta, comanda, albarà): la data viu al mateix camp `issued_at` de
// l'AbstractDocument i el guard d'estat és el mateix principi als tres — el que canvia és quins
// estats són vius, i això ho decideix el backend (serializers.guard_issued_at_editable).
//
// Quan `editable` és fals mostra el valor i prou. Quan és cert, el botó de desar només apareix
// si la data ha canviat: sense canvi no hi ha res a confirmar i la fitxa no s'omple de botons.
const MONO = 'IBM Plex Mono, monospace'

export default function IssueDateField({ value, editable, onSave, t, label }) {
  const [draft, setDraft] = useState(value || '')
  const [saving, setSaving] = useState(false)
  // El document arriba per fetch i es recarrega després de desar: la còpia local el segueix.
  useEffect(() => { setDraft(value || '') }, [value])

  const dirty = (draft || '') !== (value || '')

  const save = () => {
    setSaving(true)
    Promise.resolve(onSave(draft || null)).finally(() => setSaving(false))
  }

  return (
    <div style={{ marginBottom: 10 }}>
      <label style={{ fontSize: 'var(--fs-label)', fontFamily: MONO, color: 'var(--text-soft)', textTransform: 'uppercase', display: 'block', marginBottom: 6 }}>
        {label || t('commerce.issued_at')}
      </label>
      {editable ? (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <input type="date" value={draft} disabled={saving}
            onChange={e => setDraft(e.target.value)}
            style={{
              background: 'none', borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--line)', borderRadius: 6,
              padding: '5px 8px', fontSize: 'var(--fs-body)', fontFamily: MONO, // 🚨 `var(--text)` NO EXISTEIX a `:root` (el token és `--text-main`): la declaració queda
              // invàlida al càlcul i el color cau a l'heretat — es veia negre PER ACCIDENT.
              // Germà del `var(--fs-title)` de la pantalla de Documents; s'assembla massa a
              // `--text-main` per cridar l'atenció llegint. Trobat per la sessió de patrons.
              color: 'var(--text-main)',
            }} />
          {dirty && (
            <button onClick={save} disabled={saving} title={t('commerce.issued_at_save')} style={{
              display: 'inline-flex', alignItems: 'center', gap: 5,
              background: 'none', borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--gold-border)', borderRadius: 6,
              padding: '5px 9px', cursor: saving ? 'default' : 'pointer',
              fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--gold)',
            }}>
              <i className="ti ti-check" style={{ fontSize: 14 }} aria-hidden="true" />
              {t('commerce.issued_at_save')}
            </button>
          )}
        </span>
      ) : (
        <span style={{ fontFamily: MONO }}>{value || '—'}</span>
      )}
    </div>
  )
}
