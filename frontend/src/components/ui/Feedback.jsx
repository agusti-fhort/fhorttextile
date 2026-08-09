// Banner de resultat d'una acció (ok/error). Patró estàndard de la fase.
// props: { feedback: {type:'ok'|'err', text} | null, onDismiss? }. Sense feedback → no renderitza res.
// Si es passa onDismiss, mostra una × per tancar-lo.
export default function Feedback({ feedback, onDismiss }) {
  if (!feedback) return null
  const ok = feedback.type === 'ok'
  return (
    // §1 · fons suau + tinta del color + VORA FINA DEL MATEIX COLOR. Aquest banner en tenia
    // dues de tres: hi faltava el filet, que la norma no fa opcional. I el radi era literal.
    <div role="status" style={{
      fontSize: 'var(--fs-body)', padding: '8px 12px', borderRadius: 'var(--r-ctrl)', marginBottom: 12,
      background: ok ? 'var(--ok-bg)' : 'var(--err-bg)',
      color: ok ? 'var(--ok)' : 'var(--err)',
      borderWidth: 1, borderStyle: 'solid', borderColor: ok ? 'var(--ok)' : 'var(--err)',
      display: onDismiss ? 'flex' : 'block', justifyContent: 'space-between', alignItems: 'center', gap: 8,
    }}>
      <span>{feedback.text}</span>
      {/* §8 · icona Tabler de 14px dins d'un botó, en `currentColor`. El `×` era un caràcter
          tipogràfic: ni la mida ni el traç del sistema, i cada font el dibuixa d'una manera.
          (El comentari va FORA del `{cond && (…)}`: a dins encara ets en context d'expressió.) */}
      {onDismiss && (
        <button onClick={onDismiss} aria-label="×"
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'currentColor', fontSize: 14, lineHeight: 1, padding: 0 }}>
          <i className="ti ti-x" aria-hidden="true" style={{ fontSize: 'inherit', color: 'currentColor' }} />
        </button>
      )}
    </div>
  )
}
