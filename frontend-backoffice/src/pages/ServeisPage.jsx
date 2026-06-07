import { useState, useEffect, useCallback } from 'react';
import { IconCategory, IconPlus, IconEdit, IconTrash } from '@tabler/icons-react';
import { getServeis, createServei, updateServei, deleteServei } from '../api/contracts';

const MONO = "'IBM Plex Mono', monospace";
const TIPUS_LABELS = { tier_fee: 'Quota tier', model_count: 'Per model', manual: 'Manual' };

export default function ServeisPage() {
  const [items, setItems]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState(null);
  const [editing, setEditing] = useState(null);   // null=llista, {}=nou, {id,...}=editar
  const [tipus, setTipus]   = useState('');

  const load = useCallback(() => {
    setLoading(true);
    const params = {};
    if (tipus) params.tipus = tipus;
    getServeis(params)
      .then(r => setItems(Array.isArray(r.data) ? r.data : r.data?.results ?? []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [tipus]);

  useEffect(() => { load(); }, [load]);

  const save = (data) => {
    const p = editing?.id ? updateServei(editing.id, data) : createServei(data);
    p.then(() => { setEditing(null); load(); }).catch(e => alert(e.response?.data?.detail || e.message));
  };

  const remove = (id) => {
    if (!confirm('Esborrar aquest servei?')) return;
    deleteServei(id).then(load).catch(e => alert(e.response?.data?.detail || e.message));
  };

  const thStyle = { padding:'8px 12px', fontSize:11, color:'var(--text-muted)',
    textTransform:'uppercase', letterSpacing:'0.04em', textAlign:'left',
    borderBottom:'1px solid var(--border)', fontWeight:400 };
  const tdStyle = { padding:'10px 12px', fontSize:13, color:'var(--text-main)',
    borderBottom:'0.5px solid var(--border)', fontFamily:MONO };

  if (editing !== null) return (
    <ServeiForm initial={editing} onSave={save} onCancel={() => setEditing(null)} />
  );

  return (
    <div style={{ padding:24, maxWidth:900, margin:'0 auto', fontFamily:MONO }}>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20 }}>
        <div>
          <h1 style={{ fontSize:20, fontWeight:600, margin:0 }}>Catàleg de serveis</h1>
          <span style={{ fontSize:12, color:'var(--text-muted)' }}>{items.length} serveis</span>
        </div>
        <button onClick={() => setEditing({})}
          style={{ display:'flex', alignItems:'center', gap:6, padding:'7px 14px',
            background:'var(--gold)', color:'#fff', border:'none', borderRadius:6,
            cursor:'pointer', fontSize:13, fontFamily:MONO }}>
          <IconPlus size={15}/> Nou servei
        </button>
      </div>

      <div style={{ marginBottom:16 }}>
        <select value={tipus} onChange={e => setTipus(e.target.value)}
          style={{ padding:'6px 10px', fontSize:12, border:'1px solid var(--border)',
            borderRadius:6, fontFamily:MONO, background:'var(--bg-card)' }}>
          <option value="">Tots els tipus</option>
          {Object.entries(TIPUS_LABELS).map(([k,v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>

      {loading ? <div style={{ color:'var(--text-muted)' }}>…</div> : error ?
        <div style={{ color:'var(--err)' }}>{error}</div> : (
        <table style={{ width:'100%', borderCollapse:'collapse' }}>
          <thead><tr>
            {['Codi','Nom','Tipus','Actiu',''].map((h,i) => <th key={i} style={thStyle}>{h}</th>)}
          </tr></thead>
          <tbody>
            {items.map(s => (
              <tr key={s.id}>
                <td style={{ ...tdStyle, color:'var(--gold)', fontWeight:600 }}>{s.code}</td>
                <td style={tdStyle}>{s.nom}</td>
                <td style={tdStyle}>{TIPUS_LABELS[s.tipus] ?? s.tipus}</td>
                <td style={tdStyle}>
                  <span style={{ padding:'2px 8px', borderRadius:4, fontSize:11,
                    background: s.actiu ? 'var(--ok-pale,#e6f4ea)' : 'var(--bg-muted)',
                    color: s.actiu ? 'var(--ok,#2d7a3a)' : 'var(--text-muted)' }}>
                    {s.actiu ? 'Actiu' : 'Inactiu'}
                  </span>
                </td>
                <td style={{ ...tdStyle, textAlign:'right' }}>
                  <button onClick={() => setEditing(s)}
                    style={{ background:'none', border:'none', cursor:'pointer',
                      color:'var(--gold)', marginRight:8 }}>
                    <IconEdit size={15}/>
                  </button>
                  <button onClick={() => remove(s.id)}
                    style={{ background:'none', border:'none', cursor:'pointer',
                      color:'var(--err,#c0392b)' }}>
                    <IconTrash size={15}/>
                  </button>
                </td>
              </tr>
            ))}
            {!items.length && <tr><td colSpan={5}
              style={{ ...tdStyle, textAlign:'center', color:'var(--text-muted)' }}>
              Cap servei.
            </td></tr>}
          </tbody>
        </table>
      )}
    </div>
  );
}

function ServeiForm({ initial, onSave, onCancel }) {
  const [form, setForm] = useState({
    code: initial.code ?? '', nom: initial.nom ?? '',
    descripcio: initial.descripcio ?? '', tipus: initial.tipus ?? 'tier_fee', actiu: initial.actiu ?? true
  });
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const MONO = "'IBM Plex Mono', monospace";
  const inp = { padding:'7px 10px', fontSize:13, border:'1px solid var(--border)',
    borderRadius:6, fontFamily:MONO, background:'var(--bg-card)', width:'100%', boxSizing:'border-box' };

  return (
    <div style={{ padding:24, maxWidth:600, margin:'0 auto', fontFamily:MONO }}>
      <h2 style={{ fontSize:16, fontWeight:600, marginBottom:20 }}>
        {initial.id ? 'Editar servei' : 'Nou servei'}
      </h2>
      <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
        <div><label style={{ fontSize:11, color:'var(--text-muted)' }}>Codi</label>
          <input value={form.code} onChange={e => set('code', e.target.value)} style={inp} /></div>
        <div><label style={{ fontSize:11, color:'var(--text-muted)' }}>Nom</label>
          <input value={form.nom} onChange={e => set('nom', e.target.value)} style={inp} /></div>
        <div><label style={{ fontSize:11, color:'var(--text-muted)' }}>Descripció</label>
          <textarea value={form.descripcio} onChange={e => set('descripcio', e.target.value)}
            rows={3} style={{ ...inp }} /></div>
        <div><label style={{ fontSize:11, color:'var(--text-muted)' }}>Tipus</label>
          <select value={form.tipus} onChange={e => set('tipus', e.target.value)} style={inp}>
            <option value="tier_fee">Quota tier</option>
            <option value="model_count">Per model iniciat</option>
            <option value="manual">Manual (setup/formació)</option>
          </select></div>
        <label style={{ display:'flex', alignItems:'center', gap:8, fontSize:13 }}>
          <input type="checkbox" checked={form.actiu} onChange={e => set('actiu', e.target.checked)} />
          Actiu
        </label>
        <div style={{ display:'flex', gap:8, marginTop:8 }}>
          <button onClick={() => onSave(form)}
            style={{ padding:'8px 18px', background:'var(--gold)', color:'#fff',
              border:'none', borderRadius:6, cursor:'pointer', fontSize:13, fontFamily:MONO }}>
            Guardar
          </button>
          <button onClick={onCancel}
            style={{ padding:'8px 18px', background:'none', border:'1px solid var(--border)',
              borderRadius:6, cursor:'pointer', fontSize:13, fontFamily:MONO }}>
            Cancel·lar
          </button>
        </div>
      </div>
    </div>
  );
}
