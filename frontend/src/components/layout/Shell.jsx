import { useEffect, useRef } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Topbar from './Topbar'
import { enganxaForat } from './chromeSlot'

export default function Shell() {
  // §8b-quater(3) · `--chrome-h` — L'ALÇADA DEL BLOC DE CROM, PUBLICADA EN VIU.
  //
  // La demana l'editor de fitxa tècnica, que és una pantalla a PANTALLA COMPLETA i ha de poder
  // dir `height: calc(100vh - var(--chrome-h))` sense inventar-se cap constant. És el mateix
  // principi que `--topbar-top` i `--chrome-top`: **el crom es declara un sol cop, aquí, i la
  // pàgina el LLEGEIX en comptes de calcular-lo.**
  //
  // 🚨 I NO ES POT ESCRIURE COM A NÚMERO, que era la pregunta que calia respondre abans de
  // publicar-la. Mesurat (`scratchpad/mesura_crom.py`, cinc amplades × tres rutes): el bloc fa
  // **de 106px a 245px**. El menú de pantalla porta `flexWrap` i, quan les píndoles no hi
  // caben, passa a dues o tres files:
  //     amplada 1600 → /models 106 · /models/1319 107 · /perfil 106
  //     amplada 1200 → /models 106 · /models/1319 143
  //     amplada  900 → /models 140 · /models/1319 143
  //     amplada  520 → /models 210 · /models/1319 245
  // O sigui que una constant seria correcta NOMÉS en una finestra ampla i mentiria en totes les
  // altres — i el mode de fallada seria una pantalla completa que desborda o que deixa un forat,
  // que és exactament el que ningú prova. Es MESURA amb un `ResizeObserver` i es publica.
  //
  // Va a `documentElement` i no al `<div>` de sota perquè així la llegeix qualsevol, també el
  // que es pinta per portal (v. `chromeSlot.js`).
  const blocCrom = useRef(null)
  useEffect(() => {
    const node = blocCrom.current
    if (!node) return
    const publica = () => document.documentElement.style.setProperty(
      '--chrome-h', `${node.getBoundingClientRect().height}px`)
    publica()
    // `ResizeObserver` i no `resize` de finestra: el bloc també canvia d'alçada quan canvia el
    // CONTINGUT del menú (una pantalla amb nou píndoles i una amb només la fletxa no fan el
    // mateix alt), i això no genera cap `resize`.
    const ro = new ResizeObserver(publica)
    ro.observe(node)
    return () => ro.disconnect()
  }, [])

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
          <div ref={blocCrom} style={{
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
            // 🛑 AQUÍ ANAVA `display: flex; flexDirection: column` (petició de la sessió de la
            // fitxa tècnica, perquè l'editor a pantalla completa pogués omplir l'alçada restant
            // amb `flex: 1; minHeight: 0` i cap número màgic). **NO HI ÉS, i el motiu és una
            // MESURA, no una opinió.**
            //
            // Tots dos vam deduir llegint que era zero risc: en una columna flex un fill de
            // bloc segueix ocupant tota l'amplada, i amb un sol fill arrel no hi ha res amb què
            // col·lapsar marges. `ops/qa/qa_diff_layout.py` (nou) va prendre una foto geomètrica
            // de les 26 rutes amb el canvi i sense, i en va trobar **8 amb moviment**:
            //   · A6 · A7 · A8 · A10 · C2 — el primer fill del `<main>` baixa **24px**: el
            //     `<div>` de marge negatiu que treu el menú de pantalla dels 24px de padding
            //     **deixa de pujar** com a element flex, i queda un forat a dalt de la pàgina;
            //   · A3 i les dues del wizard — una caixa centrada amb `maxWidth` + `margin: 0
            //     auto` deixa d'estirar-se (els marges automàtics anul·len l'`align-items:
            //     stretch`) i passa a mida de CONTINGUT: 1312 → 1064, 600 → 505.7, 920 → 561.6;
            //   · C1 · l'editor .ftt creix 67px i el document en desborda 2.
            //
            // Cap d'aquests vuit canvia un sol color ni una sola mida de lletra: **les tres
            // eines de mesura li haurien donat verd**. Per això el canvi torna a la taula amb
            // les dues sortides que hi ha (adaptar les 8 pantalles, o publicar `--chrome-h` i
            // que NOMÉS l'editor el consumeixi) i no entra fins que es decideixi quina.
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
