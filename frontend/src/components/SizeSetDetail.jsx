import { useMemo, useState } from 'react'
import Badge from './ui/Badge'

// Mock POMs i deltes — estructura preparada per versioning real
const MOCK_POMS = [
  { code: 'CHEST',   name: 'Chest width',  delta: 2 },
  { code: 'WAIST',   name: 'Waist width',  delta: 2 },
  { code: 'HIP',     name: 'Hip width',    delta: 2 },
  { code: 'LENGTH',  name: 'Body length',  delta: 1 },
  { code: 'SLEEVE',  name: 'Sleeve length', delta: 1 },
  { code: 'SHOULDER', name: 'Shoulder width', delta: 0.5 },
]

function buildRow(pom, sizes, base) {
  const baseIdx = sizes.indexOf(base)
  const baseValue = 50 // valor base arbitrari per mockup
  const row = {}
  sizes.forEach((s, i) => {
    row[s] = +(baseValue + (i - baseIdx) * pom.delta).toFixed(1)
  })
  return row
}

export default function SizeSetDetail({ profile }) {
  const sizes = profile.sizes
  const base = profile.base

  const initialRows = useMemo(
    () => MOCK_POMS.map(p => ({
      ...p,
      values: buildRow(p, sizes, base),
      customDelta: p.delta,
    })),
    [profile.id]
  )

  const [rows, setRows] = useState(initialRows)
  const [edited, setEdited] = useState(false)

  const onEditDelta = (idx, newDelta) => {
    setRows(prev => {
      const next = [...prev]
      const r = { ...next[idx], customDelta: newDelta }
      const num = parseFloat(newDelta)
      if (!isNaN(num)) {
        r.values = buildRow({ ...r, delta: num }, sizes, base)
      }
      next[idx] = r
      return next
    })
    setEdited(true)
  }

  return (
    <div style={{
      background: 'var(--white)',
      border: '0.5px solid var(--gold)',
      borderRadius: 12,
      overflow: 'hidden',
    }}>
      <div style={{
        padding: '0.9rem 1.3rem',
        borderBottom: '0.5px solid #e4e4e2',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8,
      }}>
        <div style={{display: 'flex', alignItems: 'center', gap: 8}}>
          <i className="ti ti-table" style={{fontSize: 16, color: 'var(--gold)'}} />
          <span style={{fontSize: 13, fontWeight: 500}}>Detall — {profile.name}</span>
        </div>
        {edited ? (
          <Badge variant="gold" icon="ti-user-cog">Personalitzat</Badge>
        ) : profile.customClient ? (
          <Badge variant="gold" icon="ti-user-cog">Personalitzat {profile.customClient}</Badge>
        ) : (
          <Badge variant="ok" icon="ti-certificate">Estàndard {profile.standard || 'ISO'}</Badge>
        )}
      </div>

      <div style={{overflowX: 'auto'}}>
        <table style={{width: '100%', borderCollapse: 'collapse'}}>
          <thead>
            <tr>
              <th style={hStyle}>POM</th>
              {sizes.map(s => (
                <th key={s} style={{
                  ...hStyle,
                  textAlign: 'center',
                  color: s === base ? 'var(--gold)' : 'var(--gray)',
                }}>
                  {s}{s === base ? ' ★' : ''}
                </th>
              ))}
              <th style={{...hStyle, textAlign: 'center'}}>Δ/talla</th>
              <th style={{...hStyle, width: 36}}></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.code} style={{borderBottom: i < rows.length - 1 ? '0.5px solid var(--gray-l)' : 'none'}}>
                <td style={{padding: '0.55rem 1rem'}}>
                  <div style={{fontSize: 11, fontWeight: 500, color: 'var(--gold)'}}>{r.code}</div>
                  <div style={{fontSize: 10, color: 'var(--gray)', fontWeight: 300}}>{r.name}</div>
                </td>
                {sizes.map(s => (
                  <td key={s} style={{
                    padding: '0.55rem 0.5rem',
                    textAlign: 'center',
                    fontSize: 11,
                    fontVariantNumeric: 'tabular-nums',
                    color: s === base ? 'var(--gold)' : 'var(--ink, #1d1d1b)',
                    fontWeight: s === base ? 500 : 400,
                  }}>
                    {r.values[s]}
                  </td>
                ))}
                <td style={{padding: '0.4rem 0.5rem', textAlign: 'center'}}>
                  <input
                    type="number"
                    step="0.1"
                    value={r.customDelta}
                    onChange={e => onEditDelta(i, e.target.value)}
                    style={{
                      width: 60,
                      padding: '4px 6px',
                      fontSize: 11,
                      textAlign: 'center',
                      border: '0.5px solid #e4e4e2',
                      borderRadius: 6,
                      fontFamily: 'inherit',
                      fontVariantNumeric: 'tabular-nums',
                      outline: 'none',
                      background: parseFloat(r.customDelta) !== r.delta ? 'var(--gold-pale)' : 'var(--white)',
                      color: parseFloat(r.customDelta) !== r.delta ? 'var(--gold)' : 'inherit',
                    }}
                  />
                </td>
                <td style={{padding: '0.4rem 0.5rem', textAlign: 'center', color: 'var(--gray)'}}>
                  <i className="ti ti-pencil" style={{fontSize: 13}} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {edited && (
        <div style={{
          padding: '0.7rem 1.3rem',
          borderTop: '0.5px solid #e4e4e2',
          background: 'var(--gold-pale)',
          display: 'flex', justifyContent: 'flex-end', gap: 8,
        }}>
          <button style={btnStyle(false)}>Cancel·lar</button>
          <button style={btnStyle(true)}>
            <i className="ti ti-device-floppy" style={{fontSize: 13, marginRight: 5}} />
            Desar com a versió
          </button>
        </div>
      )}
    </div>
  )
}

const hStyle = {
  padding: '0.6rem 1rem',
  fontSize: 10,
  letterSpacing: '0.1em',
  textTransform: 'uppercase',
  color: 'var(--gray)',
  fontWeight: 400,
  borderBottom: '0.5px solid #e4e4e2',
  textAlign: 'left',
  whiteSpace: 'nowrap',
}

const btnStyle = (primary) => ({
  background: primary ? 'var(--gold)' : 'var(--white)',
  color: primary ? 'white' : 'var(--ink, #1d1d1b)',
  border: primary ? 'none' : '0.5px solid #e4e4e2',
  borderRadius: 8,
  padding: '6px 14px',
  fontSize: 12,
  fontWeight: primary ? 500 : 400,
  cursor: 'pointer',
  fontFamily: 'inherit',
  display: 'inline-flex',
  alignItems: 'center',
})
