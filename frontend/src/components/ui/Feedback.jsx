// Banner de resultat d'una acció (ok/error). Patró estàndard de la fase.
// props: { feedback: {type:'ok'|'err', text} | null, onDismiss? }. Sense feedback → no renderitza res.
// Si es passa onDismiss, mostra una × per tancar-lo.
export default function Feedback({ feedback, onDismiss }) {
  if (!feedback) return null
  const ok = feedback.type === 'ok'
  return (
    <div style={{
      fontSize: 12, padding: '8px 12px', borderRadius: 6, marginBottom: 12,
      background: ok ? 'var(--ok-bg)' : 'var(--err-bg)',
      color: ok ? 'var(--ok)' : 'var(--err)',
      display: onDismiss ? 'flex' : 'block', justifyContent: 'space-between', alignItems: 'center', gap: 8,
    }}>
      <span>{feedback.text}</span>
      {onDismiss && (
        <button onClick={onDismiss} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', fontSize: 14 }}>×</button>
      )}
    </div>
  )
}
