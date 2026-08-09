// L'ESTAT DE PÀGINA de la casa (loading / buit / error). El text es passa com a children
// (i18n al cridador).
//
// §8c · «ESTAT BUIT = frase en `--text-faint` CURSIVA, mai caixa buida muda». El que hi havia
// era una caixa de 3rem centrada en `--gray` — un àlies legacy que dona 3.64:1— i el centrat
// feia que un missatge d'una línia semblés una pàgina d'error. El componen 30+ pantalles: es
// conforma AQUÍ, que és on viu la regla.
export default function Center({ children }) {
  return (
    <div style={{ padding: 16, color: 'var(--text-faint)', fontStyle: 'italic',
                  fontSize: 'var(--fs-body)', fontFamily: 'IBM Plex Mono, monospace' }}>
      {children}
    </div>
  )
}
