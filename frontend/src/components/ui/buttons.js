// Estils de botó/input compartits (tokens CSS) — patró estàndard de la fase.
// selS = input/botó secundari neutre · primaryBtn = acció primària daurada.
const MONO = 'IBM Plex Mono, monospace'

export const selS = {
  fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '6px 10px',
  border: '0.5px solid var(--gray-l)', borderRadius: 6, background: 'var(--white)', color: 'var(--text-main)',
}

// L'acció primària és el daurat de la CASA (`--gold` == #c27a2a, el mateix valor que el logotip):
// el fons no es toca. El que canvia (S37, decisió de l'Agus) és la TINTA: blanc sobre daurat dona
// 3.44:1 i incompleix WCAG AA, i `--text-main` en dona 4.91:1. No hi ha cap token d'acció nou —
// es va proposar un `--gold-action` més fosc i es va descartar: la marca es queda a tot arreu.
export const primaryBtn = {
  display: 'flex', alignItems: 'center', gap: 6, marginLeft: 'auto', background: 'var(--gold)', color: 'var(--text-main)',
  border: 'none', borderRadius: 6, padding: '7px 14px', fontSize: 'var(--fs-body)', fontWeight: 600, cursor: 'pointer', fontFamily: MONO,
}
