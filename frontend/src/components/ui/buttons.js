// Estils de botó/input compartits (tokens CSS) — patró estàndard de la fase.
// selS = input/botó secundari neutre · primaryBtn = acció primària daurada.
const MONO = 'IBM Plex Mono, monospace'

export const selS = {
  fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '6px 10px',
  border: '0.5px solid var(--gray-l)', borderRadius: 6, background: 'var(--white)', color: 'var(--text-main)',
}

// L'ACCIÓ PRIMÀRIA ÉS BLAVA (NORMA_LAYOUT §5, T0-bis.2). «Blau = el que has vingut a fer, UNA per
// pantalla; vora daurada = accions i portes de la casa; gold = marca/selecció/base.» El daurat
// deixa de ser acció perquè feia dues feines alhora: marcar la casa i cridar l'acció, i quan un
// color diu dues coses no en diu cap.
//
// Substitueix la solució de S37, que era la bona MENTRE la primària fos daurada: aleshores el
// problema era el contrast (blanc sobre daurat = 3.44:1, per sota d'AA) i es va resoldre canviant
// la TINTA a `--text-main` (4.91:1) sense tocar la marca. Ara no canvia la tinta sinó el ROL: el
// fons ja no és de marca, i sobre `--accio` el blanc dóna 5.61:1 — AA amb marge.
//
// Es reescriu D'UN COP i no pantalla per pantalla (ordre d'Agus): 66 usos en 28 fitxers. L'efecte
// conegut i acceptat és que algunes pantalles ensenyaran més d'un blau alhora fins que passin la
// seva conformitat; van llistades al report de T0-bis, no s'arreglen aquí.
export const primaryBtn = {
  display: 'flex', alignItems: 'center', gap: 6, marginLeft: 'auto', background: 'var(--accio)', color: 'var(--white)',
  border: 'none', borderRadius: 6, padding: '7px 14px', fontSize: 'var(--fs-body)', fontWeight: 600, cursor: 'pointer', fontFamily: MONO,
}
