// LA TARGETA DE KPI DE LA CASA (§8c · §1 · §3).
//
// Conformada a la part B amb la pantalla de Fittings, que és qui la munta més. El que hi havia:
//  · `#e4e4e2` de vora (un dels colors fora de paleta que els blocs A i B tenien anotats) i
//    radi literal 12 → `--line` i `--r-card`;
//  · la icona en **`--gold`**. La §8 només admet quatre tintes d'icona i el daurat hi és
//    l'ACTIVA, no la de repòs; i la §8c remata que «el daurat NO pinta números». Una icona
//    daurada al costat d'un recompte diu «alerta» amb el color del logo → `--text-soft`.
//  · `--gray` (àlies legacy, 3.64:1) al rètol i `--charcoal` al valor → l'escala de la norma
//    (`--text-soft` / `--text-main`);
//  · el valor a `2rem` escrit a mà, que és exactament `--fs-display` (32px) però sense nom;
//  · el subtítol a pes 300, que no és cap dels tres pesos de la casa (400 · 500 · 600).
//
// `subColor` es conserva perquè la §8c el necessita: **els KPI són NEUTRES i només els d'ALERTA
// porten semàfor** («En risc · 1» en `--err`). Qui en tingui un el passa; qui no, no.
// `valueStyle` (M2): un KPI el valor del qual és una DATA no cap a `--fs-display`. El mockup del
// registre per rondes ja ho deia (la seva targeta d'«Inici activitat» baixa el cos a mà mentre
// les altres tres es queden al display), i sense això la data embolica a tres línies i la fila de
// KPI queda desalineada. Additiu i opcional: cap muntatge existent canvia. Mateix precedent que
// `subColor`, que ja hi era per la mateixa raó (una excepció per instància, no una variant nova).
export default function StatCard({ icon, label, value, sub, subColor, valueStyle }) {
  return (
    <div style={{
      background: 'var(--panel)',
      border: '1px solid var(--line)',
      borderRadius: 'var(--r-card)',
      // La targeta declara la MIDA DE COS: sense això hereta els 16px del document i el
      // contenidor computa un valor que ningú ha decidit (defecte mesurat al bloc A).
      fontSize: 'var(--fs-body)',
      padding: 16,
    }}>
      <div style={{
        fontSize: 'var(--fs-body)', color: 'var(--text-soft)',
        marginBottom: 8,
        display: 'flex', alignItems: 'center', gap: 6,
      }}>
        {icon && <i className={`ti ${icon}`} aria-hidden="true" style={{ fontSize: 16, color: 'currentColor' }} />}
        {label}
      </div>
      <div style={{
        fontSize: 'var(--fs-display)', fontWeight: 600,
        color: 'var(--text-main)', lineHeight: 1,
        marginBottom: 4,
        ...valueStyle,
      }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: 'var(--fs-caption)', color: subColor || 'var(--text-soft)' }}>
          {sub}
        </div>
      )}
    </div>
  )
}
