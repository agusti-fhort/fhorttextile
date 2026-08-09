import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Topbar from './Topbar'
import { enganxaForat } from './chromeSlot'

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
        // §8b-quater (Agus 09/08) · EL CROM DEL SISTEMA ES DECLARA UN SOL COP, AQUÍ.
        // La top bar i el menú de pantalla han de quedar enganxats en scroll «com un sol
        // bloc», i per a això el menú —que viu dins del `<main>`, dins de cada pàgina— ha de
        // saber a quina alçada s'atura. Aquesta és l'única cosa que ha de saber, i no la pot
        // deduir: depèn de la franja de staging, que és una decisió de BUILD (`VITE_STAGING`).
        // Va com a variable CSS i no com a constant JS a posta: així la regla del §8b-quater
        // (index.css) i el `top` de la top bar la llegeixen tots dos del MATEIX lloc, i cap
        // pantalla no ha de re-declarar res.
        //   --topbar-top : on s'atura la top bar (sota la franja de staging, si n'hi ha)
        //   --chrome-top : on s'atura el menú de pantalla (= sota la top bar)
        '--topbar-top': import.meta.env.VITE_STAGING === 'true' ? '28px' : '0px',
        '--chrome-top': import.meta.env.VITE_STAGING === 'true' ? '84px' : '56px',
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
          {/* §8b-quater · EL BLOC DE CROM: top bar + menú de pantalla, enganxats COM UN SOL
              BLOC. La franja sencera és `sticky` aquí dalt i el menú s'hi teletransporta des de
              la pàgina (v. `chromeSlot.js` per al perquè d'un portal i no d'un `:has()`).
              El fons és `--panel` OPAC perquè el contingut hi passi per sota sense
              transparentar-se, i la z queda per sobre del contingut i per SOTA del menú lateral
              (100) i dels modals (150, `ui/overlay.js`). */}
          <div style={{
            position: 'sticky',
            top: 'var(--topbar-top)',
            zIndex: 30,
            background: 'var(--panel)',
          }}>
            <Topbar />
            <div ref={enganxaForat} />
          </div>
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
            // ⚠️ AQUÍ HI HAVIA `overflowY: 'auto'` I ERA EL QUE MATAVA EL STICKY (§8b-quater).
            // El `<main>` no ha tingut mai scroll propi: la seva columna té `minHeight: 100vh`
            // i cap alçada màxima, o sigui que el `<main>` creix amb el contingut i qui es
            // desplaça és el document. Però `overflow-y: auto` **crea igualment una caixa de
            // desplaçament** i, per a `position: sticky`, la caixa de desplaçament més propera
            // és la referència: qualsevol element enganxós de dins del `<main>` quedava
            // ancorat a un scrollport que no es desplaça MAI, o sigui mort sense fer soroll.
            // Treure-ho torna la referència al document, que és qui es desplaça de debò.
          }}>
            <Outlet />
          </main>
        </div>
      </div>
    </>
  )
}
