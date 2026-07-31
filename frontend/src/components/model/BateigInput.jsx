import { useState, useEffect } from 'react'

// EL BATEIG, en un sol lloc (Sprint NOMS-POM · extret de MeasureGrid el 31/07).
//
// L'input amb què una línia de mesura es rebateja: sembla text fins que t'hi acostes, i només
// llavors ensenya que es pot escriure (subratllat discontinu en hover, sòlid i fons blanc en
// focus). És deliberat: la columna del nom es llegeix molt més que s'edita, i omplir-la de
// caixes la faria un formulari en comptes d'una taula.
//
// `value` és el bateig CRU ('' = no batejat) i `placeholder` el que diu el catàleg. Buidar el
// camp torna a deixar manar el catàleg: per això el commit envia la cadena buida en comptes
// d'ignorar-la. Es desa a onBlur i amb Enter — mai a cada tecla.
//
// Viu aquí i no dins de MeasureGrid perquè les DUES superfícies que bategen —la graella de
// consulta/check i la taula d'entrada de Mesures— facin servir EL MATEIX camp i la mateixa
// porta (`baseMeasurements.setNoms`), i no dos mecanismes que divergeixin.
export default function BateigInput({ value, placeholder, title, onSave, style }) {
  const [val, setVal] = useState(value ?? '')
  const [focused, setFocused] = useState(false)
  const [hover, setHover] = useState(false)
  useEffect(() => { if (!focused) setVal(value ?? '') }, [value, focused])
  const commit = () => {
    setFocused(false)
    const v = (val ?? '').trim()
    setVal(v)
    if (v !== (value ?? '')) onSave(v)
  }
  const viu = focused || hover
  return (
    <input
      value={val ?? ''} placeholder={placeholder} title={title} aria-label={title}
      onChange={e => setVal(e.target.value)}
      onFocus={() => setFocused(true)} onBlur={commit}
      onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      onKeyDown={e => { if (e.key === 'Enter') e.currentTarget.blur() }}
      style={{
        font: 'inherit', width: '100%', padding: '0 2px', boxSizing: 'border-box', borderRadius: 3,
        background: focused ? 'var(--white)' : 'transparent',
        border: '1px solid transparent',
        borderBottom: viu ? `1px ${focused ? 'solid' : 'dashed'} var(--border)` : '1px solid transparent',
        ...style,
      }}
    />
  )
}
