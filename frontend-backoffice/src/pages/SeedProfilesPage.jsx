import { useState, useEffect, useCallback, useMemo } from 'react';
import { IconSeeding, IconPlus, IconEdit, IconTrash, IconStar } from '@tabler/icons-react';
import {
  getSeedProfiles, createSeedProfile, updateSeedProfile, deleteSeedProfile,
  getSeedBlocksMeta,
} from '../api/seeding';

const MONO = "'IBM Plex Mono', monospace";

// Clausura transitiva de dependències de selecció (mateixa llei que el backend:
// seleccionar un bloc n'arrossega tots els que en depèn). `deps` de cada bloc és el
// conjunt DIRECTE; aquí en calculem la clausura per mostrar què arrossega de veritat.
function closure(selected, depMap) {
  const seen = new Set();
  const stack = [...selected];
  while (stack.length) {
    const b = stack.pop();
    if (seen.has(b)) continue;
    seen.add(b);
    (depMap[b] || []).forEach(d => { if (!seen.has(d)) stack.push(d); });
  }
  return seen;
}

export default function SeedProfilesPage() {
  const [items, setItems]     = useState([]);
  const [blocs, setBlocs]     = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const [editing, setEditing] = useState(null);   // null=llista, {}=nou, {id,...}=editar

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([getSeedProfiles(), getSeedBlocksMeta()])
      .then(([p, m]) => {
        setItems(Array.isArray(p.data) ? p.data : p.data?.results ?? []);
        setBlocs(m.data?.blocs ?? []);
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const save = (data) => {
    const p = editing?.id ? updateSeedProfile(editing.id, data) : createSeedProfile(data);
    p.then(() => { setEditing(null); load(); })
     .catch(e => alert(e.response?.data?.detail || JSON.stringify(e.response?.data) || e.message));
  };

  const remove = (id) => {
    if (!confirm('Esborrar aquest perfil de sembra?')) return;
    deleteSeedProfile(id).then(load).catch(e => alert(e.response?.data?.detail || e.message));
  };

  const thStyle = { padding:'8px 12px', fontSize:11, color:'var(--text-muted)',
    textTransform:'uppercase', letterSpacing:'0.04em', textAlign:'left',
    borderBottom:'1px solid var(--border)', fontWeight:400 };
  const tdStyle = { padding:'10px 12px', fontSize:13, color:'var(--text-main)',
    borderBottom:'0.5px solid var(--border)', fontFamily:MONO };

  if (editing !== null) return (
    <SeedProfileForm initial={editing} blocs={blocs} onSave={save} onCancel={() => setEditing(null)} />
  );

  return (
    <div style={{ padding:24, maxWidth:900, margin:'0 auto', fontFamily:MONO }}>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20 }}>
        <div>
          <h1 style={{ fontSize:20, fontWeight:600, margin:0, display:'flex', alignItems:'center', gap:8 }}>
            <IconSeeding size={20}/> Perfils de sembra
          </h1>
          <span style={{ fontSize:12, color:'var(--text-muted)' }}>
            {items.length} perfils · defineixen què se sembra a un tenant Free en donar-lo d'alta
          </span>
        </div>
        <button onClick={() => setEditing({})}
          style={{ display:'flex', alignItems:'center', gap:6, padding:'7px 14px',
            background:'var(--gold)', color:'#fff', border:'none', borderRadius:6,
            cursor:'pointer', fontSize:13, fontFamily:MONO }}>
          <IconPlus size={15}/> Nou perfil
        </button>
      </div>

      {loading ? <div style={{ color:'var(--text-muted)' }}>…</div> : error ?
        <div style={{ color:'var(--err)' }}>{error}</div> : (
        <table style={{ width:'100%', borderCollapse:'collapse' }}>
          <thead><tr>
            {['Nom','Blocs','Default Free','Actiu',''].map((h,i) => <th key={i} style={thStyle}>{h}</th>)}
          </tr></thead>
          <tbody>
            {items.map(p => (
              <tr key={p.id}>
                <td style={{ ...tdStyle, color:'var(--gold)', fontWeight:600 }}>{p.nom}</td>
                <td style={tdStyle}>{(p.blocks || []).length}</td>
                <td style={tdStyle}>
                  {p.is_default_free
                    ? <span style={{ display:'inline-flex', alignItems:'center', gap:4,
                        color:'var(--gold)' }}><IconStar size={13}/> Free</span>
                    : <span style={{ color:'var(--text-muted)' }}>—</span>}
                </td>
                <td style={tdStyle}>
                  <span style={{ padding:'2px 8px', borderRadius:4, fontSize:11,
                    background: p.actiu ? 'var(--ok-pale,#e6f4ea)' : 'var(--bg-muted)',
                    color: p.actiu ? 'var(--ok,#2d7a3a)' : 'var(--text-muted)' }}>
                    {p.actiu ? 'Actiu' : 'Inactiu'}
                  </span>
                </td>
                <td style={{ ...tdStyle, textAlign:'right' }}>
                  <button onClick={() => setEditing(p)}
                    style={{ background:'none', border:'none', cursor:'pointer',
                      color:'var(--gold)', marginRight:8 }}><IconEdit size={15}/></button>
                  <button onClick={() => remove(p.id)}
                    style={{ background:'none', border:'none', cursor:'pointer',
                      color:'var(--err,#c0392b)' }}><IconTrash size={15}/></button>
                </td>
              </tr>
            ))}
            {!items.length && <tr><td colSpan={5}
              style={{ ...tdStyle, textAlign:'center', color:'var(--text-muted)' }}>
              Cap perfil de sembra.
            </td></tr>}
          </tbody>
        </table>
      )}
    </div>
  );
}

function SeedProfileForm({ initial, blocs, onSave, onCancel }) {
  const [form, setForm] = useState({
    nom: initial.nom ?? '',
    descripcio: initial.descripcio ?? '',
    is_default_free: initial.is_default_free ?? false,
    actiu: initial.actiu ?? true,
  });
  // Selecció EXPLÍCITA de l'usuari (les dependències s'auto-inclouen en pintar i en sembrar).
  const [selected, setSelected] = useState(new Set(initial.blocks ?? []));
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const depMap = useMemo(() => Object.fromEntries(blocs.map(b => [b.key, b.deps || []])), [blocs]);
  const countMap = useMemo(() => Object.fromEntries(blocs.map(b => [b.key, b.total || 0])), [blocs]);
  const clos = useMemo(() => closure([...selected], depMap), [selected, depMap]);
  const totalRows = useMemo(
    () => [...clos].reduce((s, k) => s + (countMap[k] || 0), 0), [clos, countMap]);

  const toggle = (key) => setSelected(prev => {
    const n = new Set(prev);
    n.has(key) ? n.delete(key) : n.add(key);
    return n;
  });

  const submit = () => {
    if (!form.nom.trim()) { alert('El nom és obligatori.'); return; }
    onSave({ ...form, seleccio: { blocks: [...selected] } });
  };

  const inp = { padding:'7px 10px', fontSize:13, border:'1px solid var(--border)',
    borderRadius:6, fontFamily:MONO, background:'var(--bg-card)', width:'100%', boxSizing:'border-box' };

  return (
    <div style={{ padding:24, maxWidth:640, margin:'0 auto', fontFamily:MONO }}>
      <h2 style={{ fontSize:16, fontWeight:600, marginBottom:20 }}>
        {initial.id ? 'Editar perfil de sembra' : 'Nou perfil de sembra'}
      </h2>
      <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
        <div><label style={{ fontSize:11, color:'var(--text-muted)' }}>Nom</label>
          <input value={form.nom} onChange={e => set('nom', e.target.value)} style={inp} /></div>
        <div><label style={{ fontSize:11, color:'var(--text-muted)' }}>Descripció</label>
          <textarea value={form.descripcio} onChange={e => set('descripcio', e.target.value)}
            rows={2} style={inp} /></div>

        <div>
          <label style={{ fontSize:11, color:'var(--text-muted)' }}>
            Blocs a sembrar · seleccionar-ne un n'arrossega les dependències
          </label>
          <div style={{ display:'flex', flexDirection:'column', gap:6, marginTop:6 }}>
            {blocs.map(b => {
              const explicit = selected.has(b.key);
              const auto = !explicit && clos.has(b.key);   // inclòs per dependència
              return (
                <label key={b.key} style={{ display:'flex', alignItems:'center', gap:10,
                  padding:'8px 10px', borderRadius:6,
                  border:'1px solid var(--border)',
                  background: explicit ? 'var(--ok-pale,#e6f4ea)'
                            : auto ? 'var(--bg-muted)' : 'var(--bg-card)',
                  cursor:'pointer' }}>
                  <input type="checkbox" checked={explicit || auto} disabled={auto && !explicit}
                    onChange={() => toggle(b.key)} />
                  <span style={{ flex:1, fontSize:13 }}>
                    {b.label}
                    {auto && <span style={{ fontSize:11, color:'var(--text-muted)' }}> · auto (dependència)</span>}
                    {b.key === 'grading' &&
                      <span style={{ fontSize:11, color:'var(--gold)' }}> · només rulesets CANONICAL</span>}
                  </span>
                  <span style={{ fontSize:12, color:'var(--text-muted)' }}
                    title={Object.entries(b.models || {}).map(([m,c]) => `${m}: ${c}`).join('\n')}>
                    {b.total} files
                  </span>
                </label>
              );
            })}
          </div>
          <div style={{ marginTop:8, fontSize:12, color:'var(--text-muted)' }}>
            Total a sembrar (amb dependències): <b style={{ color:'var(--text-main)' }}>{totalRows}</b> files
            · {clos.size} blocs
          </div>
        </div>

        <label style={{ display:'flex', alignItems:'center', gap:8, fontSize:13 }}>
          <input type="checkbox" checked={form.is_default_free}
            onChange={e => set('is_default_free', e.target.checked)} />
          <IconStar size={14} style={{ color:'var(--gold)' }}/> Perfil per defecte del flux Free (únic)
        </label>
        <label style={{ display:'flex', alignItems:'center', gap:8, fontSize:13 }}>
          <input type="checkbox" checked={form.actiu} onChange={e => set('actiu', e.target.checked)} />
          Actiu
        </label>

        <div style={{ display:'flex', gap:8, marginTop:8 }}>
          <button onClick={submit}
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
