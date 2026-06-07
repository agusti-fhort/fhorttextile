import { useState, useEffect, useCallback } from 'react';
import { IconPlus, IconEye } from '@tabler/icons-react';
import { getContractes } from '../api/contracts';
import { useNavigate } from 'react-router-dom';

const MONO = "'IBM Plex Mono', monospace";

export default function ContractesPage() {
  const [items, setItems]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState(null);
  const navigate = useNavigate();

  const load = useCallback(() => {
    setLoading(true);
    getContractes({ ordering: '-data_inici' })
      .then(r => setItems(Array.isArray(r.data) ? r.data : r.data?.results ?? []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const fmtDate = (v) => v ? new Date(v).toLocaleDateString('ca-ES', { dateStyle:'medium' }) : '—';
  const thStyle = { padding:'8px 12px', fontSize:11, color:'var(--text-muted)',
    textTransform:'uppercase', letterSpacing:'0.04em', textAlign:'left',
    borderBottom:'1px solid var(--border)', fontWeight:400 };
  const tdStyle = { padding:'10px 12px', fontSize:13, color:'var(--text-main)',
    borderBottom:'0.5px solid var(--border)', fontFamily:MONO };

  return (
    <div style={{ padding:24, maxWidth:900, margin:'0 auto', fontFamily:MONO }}>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20 }}>
        <div>
          <h1 style={{ fontSize:20, fontWeight:600, margin:0 }}>Contractes</h1>
          <span style={{ fontSize:12, color:'var(--text-muted)' }}>{items.length} contractes</span>
        </div>
        <button onClick={() => navigate('/contractes/new')}
          style={{ display:'flex', alignItems:'center', gap:6, padding:'7px 14px',
            background:'var(--gold)', color:'#fff', border:'none', borderRadius:6,
            cursor:'pointer', fontSize:13, fontFamily:MONO }}>
          <IconPlus size={15}/> Nou contracte
        </button>
      </div>

      {loading ? <div style={{ color:'var(--text-muted)' }}>…</div> : error ?
        <div style={{ color:'var(--err)' }}>{error}</div> : (
        <table style={{ width:'100%', borderCollapse:'collapse' }}>
          <thead><tr>
            {['Client','Inici','Fi','Línies','Actiu',''].map((h,i) => <th key={i} style={thStyle}>{h}</th>)}
          </tr></thead>
          <tbody>
            {items.map(c => (
              <tr key={c.id} onClick={() => navigate(`/contractes/${c.id}`)}
                style={{ cursor:'pointer' }}
                onMouseEnter={e => e.currentTarget.style.background='var(--bg-muted)'}
                onMouseLeave={e => e.currentTarget.style.background=''}>
                <td style={{ ...tdStyle, color:'var(--gold)', fontWeight:600 }}>{c.client_codi}</td>
                <td style={tdStyle}>{fmtDate(c.data_inici)}</td>
                <td style={tdStyle}>{fmtDate(c.data_fi)}</td>
                <td style={tdStyle}>{c.lines_count}</td>
                <td style={tdStyle}>
                  <span style={{ padding:'2px 8px', borderRadius:4, fontSize:11,
                    background: c.actiu ? 'var(--ok-pale,#e6f4ea)' : 'var(--bg-muted)',
                    color: c.actiu ? 'var(--ok,#2d7a3a)' : 'var(--text-muted)' }}>
                    {c.actiu ? 'Actiu' : 'Inactiu'}
                  </span>
                </td>
                <td style={{ ...tdStyle, textAlign:'right' }}>
                  <IconEye size={15} style={{ color:'var(--gold)' }}/>
                </td>
              </tr>
            ))}
            {!items.length && <tr><td colSpan={6}
              style={{ ...tdStyle, textAlign:'center', color:'var(--text-muted)' }}>
              Cap contracte.
            </td></tr>}
          </tbody>
        </table>
      )}
    </div>
  );
}
