const MONO = "'IBM Plex Mono', monospace"

export default function DashboardPage() {
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg-main)',
        color: 'var(--text-muted)',
        fontFamily: MONO,
        fontSize: 15,
      }}
    >
      Dashboard — pròximament
    </div>
  )
}
