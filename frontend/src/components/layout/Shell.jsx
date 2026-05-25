import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Topbar from './Topbar'

export default function Shell() {
  return (
    <div style={{display: 'flex', minHeight: '100vh'}}>
      <Sidebar />
      <div style={{
        marginLeft: 240,
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100vh',
      }}>
        <Topbar />
        <main style={{
          flex: 1,
          padding: '1.5rem',
          background: 'var(--gray-l)',
          overflowY: 'auto',
        }}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
