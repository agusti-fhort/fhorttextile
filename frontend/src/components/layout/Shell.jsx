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
          textAlign: 'center', fontSize: 'var(--fs-body)',
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
            // §1 · EL FONS DE PÀGINA ÉS `--bg-page` (#fbfaf8, blanc càlid). Aquí hi havia
            // `--gray-l` (#f0f0f0), que és un GRIS FRED i, a més, un àlies legacy que la casa
            // fa servir per a vores i farciments de control — no per a la superfície on viuen
            // totes les pantalles. El token de la norma existia des de T0.1 i aquest era
            // l'últim lloc que no el consumia: mentre el `<main>` pintés gris, cap pantalla
            // conforme podia acabar de casar amb la seva maqueta, que va tota sobre `--bg`.
            //
            // ⚠️ TOCA TOTES LES PANTALLES ALHORA, també les que encara no han passat
            // conformitat. Va en commit AÏLLAT a posta (ordre d'Agus): si alguna pantalla
            // vella se'n ressent, es revertreix una línia i prou.
            background: 'var(--bg-page)',
            overflowY: 'auto',
          }}>
            <Outlet />
          </main>
        </div>
      </div>
    </>
  )
}
