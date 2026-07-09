// <RowBtn> — botó d'acció de línia (patró row-btn): icona Tabler outline, discret, a l'esquerra de
// la fila (ull de visibilitat, eliminar…). `icon` = classe Tabler (p.ex. 'ti-eye'); `danger` el
// pinta en to d'error. Sense text: és icona + títol accessible.
const MONO = 'IBM Plex Mono, monospace'

export default function RowBtn({ icon, title, onClick, disabled, danger, active }) {
  const color = danger ? 'var(--err)' : active ? 'var(--gold)' : 'var(--text-muted)'
  return (
    <button type="button" onClick={onClick} disabled={disabled} title={title} aria-label={title} style={{
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6,
      width: 26, height: 26, padding: 0, cursor: disabled ? 'default' : 'pointer',
      opacity: disabled ? 0.4 : 1, color, fontFamily: MONO,
    }}>
      <i className={`ti ${icon}`} style={{ fontSize: 14 }} aria-hidden="true" />
    </button>
  )
}
