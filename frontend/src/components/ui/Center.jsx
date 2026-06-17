// Bloc centrat per a estats loading/buit/error d'una pàgina (patró estàndard de la fase).
// Extret byte-idèntic de Planning/PlanningCalendar; el text es passa com a children (i18n al cridador).
export default function Center({ children }) {
  return <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 'var(--fs-body)' }}>{children}</div>
}
