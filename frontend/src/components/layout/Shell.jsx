import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Topbar from './Topbar'

export default function Shell() {
  return (
    <>
      {import.meta.env.VITE_STAGING === 'true' && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, zIndex: 9999,
          background: '#f59e0b', color: '#000',
          textAlign: 'center', fontSize: '12px',
          fontFamily: "'IBM Plex Mono', monospace", fontWeight: 600,
          padding: '4px 0', letterSpacing: '0.05em'
        }}>
          ⚠️ ENTORN DE STAGING — les dades no són reals
        </div>
      )}
      <div style={{
        display: 'flex',
        minHeight: '100vh',
        paddingTop: import.meta.env.VITE_STAGING === 'true' ? '28px' : 0,
      }}>
        <Sidebar />
        <div style={{
          marginLeft: 240,
          flex: 1,
          minWidth: 0,            // flex item: permet encongir per sota del min-content del fill (la taula)
          display: 'flex',
          flexDirection: 'column',
          minHeight: '100vh',
        }}>
          <Topbar />
          <main style={{
            flex: 1,
            minWidth: 0,          // no deixis que el contingut ample empenyi la columna
            padding: '1.5rem',
            background: 'var(--gray-l)',
            overflowY: 'auto',
          }}>
            <Outlet />
          </main>
        </div>
      </div>
    </>
  )
}
