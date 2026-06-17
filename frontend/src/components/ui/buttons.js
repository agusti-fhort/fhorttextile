// Estils de botó/input compartits (tokens CSS) — patró estàndard de la fase.
// selS = input/botó secundari neutre · primaryBtn = acció primària daurada.
const MONO = 'IBM Plex Mono, monospace'

export const selS = {
  fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '6px 10px',
  border: '0.5px solid var(--gray-l)', borderRadius: 6, background: 'var(--white)', color: 'var(--text-main)',
}

export const primaryBtn = {
  display: 'flex', alignItems: 'center', gap: 6, marginLeft: 'auto', background: 'var(--gold)', color: 'var(--white)',
  border: 'none', borderRadius: 6, padding: '7px 14px', fontSize: 'var(--fs-body)', fontWeight: 600, cursor: 'pointer', fontFamily: MONO,
}
