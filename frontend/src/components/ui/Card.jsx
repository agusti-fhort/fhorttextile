// LA TARGETA DE LA CASA (§1 · §3 · §8).
//
// Conformada a la part B amb la pantalla de Fittings, que la munta com a caixa de la llista.
// El que hi havia: `#e4e4e2` de vora —un dels tres colors fora de paleta que els blocs A i B
// tenien anotats, i que ja no és a la top bar—, vores de mig píxel (que no són de cap escala:
// el navegador les arrodoneix i el resultat depèn del zoom), radi literal 12 en comptes del
// token, paddings en `rem` fora de la base de 4, i la icona de capçalera a **18px en `--gold`**:
// la §8 només admet tres mides (14 · 16 · 20) i quatre tintes, i el daurat hi és l'ACTIVA.
export default function Card({ title, icon, action, children, padding, style }) {
  return (
    <div style={{
      background: 'var(--panel)',
      border: '1px solid var(--line)',
      borderRadius: 'var(--r-card)',
      // La targeta declara la MIDA DE COS: sense això hereta els 16px del document i el
      // contenidor computa un valor que ningú ha decidit (defecte mesurat al bloc A).
      fontSize: 'var(--fs-body)',
      overflow: 'hidden',
      ...style,
    }}>
      {(title || action) && (
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid var(--line)',
          display: 'flex', alignItems: 'center', gap: 12,
        }}>
          {icon && <i className={`ti ${icon}`} aria-hidden="true"
            style={{ fontSize: 16, color: 'var(--text-soft)' }} />}
          {title && <span style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, color: 'var(--text-main)' }}>{title}</span>}
          {action && <div style={{ marginLeft: 'auto' }}>{action}</div>}
        </div>
      )}
      <div style={{ padding: padding ?? 20 }}>
        {children}
      </div>
    </div>
  )
}
