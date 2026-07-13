// Capa z dels modals (QA-S8 · D3).
//
// El Sidebar és `position: fixed`, left 0, 240px d'ample, zIndex 100 (Sidebar.jsx:312).
// Un overlay per SOTA d'aquests 100 el té a sobre: el panell surt escapçat per l'esquerra i el
// backdrop no enfosqueix la franja del menú. Es va veure al wizard del diccionari (panell de
// 1100px: en un portàtil de 1440 la vora esquerra cau a x=170, sota el sidebar), però hi eren
// TOTS els modals a zIndex 50/60 — només que amb panells prou estrets per no arribar-hi mai.
//
// Z_MODAL va per sobre del sidebar i per SOTA dels drawers (200) i dels editors a pantalla
// completa (1000), per no alterar-ne l'ordre relatiu.
export const Z_MODAL = 150

// Base de l'overlay d'un modal: fixed a tot el viewport + backdrop + centrat horitzontal.
// `extra` per a l'alineació vertical i el scroll, que depenen de l'alçada del panell.
export const overlayBase = (extra = {}) => ({
  position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: Z_MODAL,
  display: 'flex', justifyContent: 'center', ...extra,
})
