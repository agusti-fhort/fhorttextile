import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { IconArrowLeft, IconPlus } from '@tabler/icons-react';
import { getContracte } from '../api/contracts';

const MONO = "'IBM Plex Mono', monospace";

export default function ContractDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getContracte(id)
      .then(r => setData(r.data))
      .catch(() => navigate('/contractes'))
      .finally(() => setLoading(false));
  }, [id]);

  const fmtDate = (v) => v ? new Date(v).toLocaleDateString('ca-ES', { dateStyle:'medium' }) : '—';
  const thStyle = { padding:'8px 12px', fontSize:11, color:'var(--text-muted)',
    textTransform:'uppercase', letterSpacing:'0.04em', textAlign:'left',
    borderBottom:'1px solid var(--border)', fontWeight:400 };
  const tdStyle = { padding:'10px 12px', fontSize:13, color:'var(--text-main)',
    borderBottom:'0.5px solid var(--border)', fontFamily:MONO };

  if (loading) return <div style={{ padding:24, color:'var(--text-muted)', fontFamily:MONO }}>…</div>;
  if (!data) return null;

  return (
    <div style={{ padding:24, maxWidth:900, margin:'0 auto', fontFamily:MONO }}>
      <button onClick={() => navigate('/contractes')}
        style={{ display:'flex', alignItems:'center', gap:6, background:'none', border:'none',
          cursor:'pointer', color:'var(--gold)', fontSize:13, fontFamily:MONO, marginBottom:20 }}>
        <IconArrowLeft size={15}/> Contractes
      </button>

      <div style={{ background:'var(--bg-card)', border:'1px solid var(--border)',
        borderRadius:8, padding:20, marginBottom:20 }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start' }}>
          <div>
            <span style={{ fontSize:20, fontWeight:600, color:'var(--gold)' }}>{data.client_codi}</span>
            <div style={{ fontSize:12, color:'var(--text-muted)', marginTop:4 }}>
              {fmtDate(data.data_inici)} → {fmtDate(data.data_fi)}
            </div>
            {data.nota && <div style={{ fontSize:12, marginTop:8 }}>{data.nota}</div>}
          </div>
          <span style={{ padding:'3px 10px', borderRadius:4, fontSize:11,
            background: data.actiu ? 'var(--ok-pale,#e6f4ea)' : 'var(--bg-muted)',
            color: data.actiu ? 'var(--ok,#2d7a3a)' : 'var(--text-muted)' }}>
            {data.actiu ? 'Actiu' : 'Inactiu'}
          </span>
        </div>
      </div>

      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:12 }}>
        <h2 style={{ fontSize:14, fontWeight:600, margin:0 }}>Línies de servei</h2>
      </div>

      <table style={{ width:'100%', borderCollapse:'collapse' }}>
        <thead><tr>
          {['Servei','Nom','Preu','Moneda','Inclosos','Actiu'].map((h,i) =>
            <th key={i} style={thStyle}>{h}</th>)}
        </tr></thead>
        <tbody>
          {(data.lines || []).map(l => (
            <tr key={l.id}>
              <td style={{ ...tdStyle, color:'var(--gold)', fontWeight:600 }}>{l.service_code}</td>
              <td style={tdStyle}>{l.service_nom}</td>
              <td style={tdStyle}>{l.preu}</td>
              <td style={tdStyle}>{l.moneda}</td>
              <td style={tdStyle}>{l.inclosos}</td>
              <td style={tdStyle}>
                <span style={{ padding:'2px 8px', borderRadius:4, fontSize:11,
                  background: l.actiu ? 'var(--ok-pale,#e6f4ea)' : 'var(--bg-muted)',
                  color: l.actiu ? 'var(--ok,#2d7a3a)' : 'var(--text-muted)' }}>
                  {l.actiu ? 'Actiu' : 'Inactiu'}
                </span>
              </td>
            </tr>
          ))}
          {!data.lines?.length && <tr><td colSpan={6}
            style={{ ...tdStyle, textAlign:'center', color:'var(--text-muted)' }}>
            Cap línia de servei.
          </td></tr>}
        </tbody>
      </table>
    </div>
  );
}
