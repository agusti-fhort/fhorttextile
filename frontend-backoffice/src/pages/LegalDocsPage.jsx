import { useState, useEffect, useCallback } from 'react';
import {
  IconGavel, IconPlus, IconArrowLeft, IconCopy, IconTrash, IconLock, IconCheck,
} from '@tabler/icons-react';
import {
  getLegalDocs, createLegalDoc, createLegalVersion, updateLegalVersion,
  deleteLegalVersion, publishLegalVersion, getLegalAcceptances,
} from '../api/legal';

const MONO = "'IBM Plex Mono', monospace";
const TIPUS = {
  TERMES: 'Termes i condicions', PRIVACITAT: 'Política de privacitat',
  DPA: 'DPA', SLA: 'SLA',
};

const th = { padding:'8px 12px', fontSize:11, color:'var(--text-muted)',
  textTransform:'uppercase', letterSpacing:'0.04em', textAlign:'left',
  borderBottom:'1px solid var(--border)', fontWeight:400 };
const td = { padding:'10px 12px', fontSize:13, color:'var(--text-main)',
  borderBottom:'0.5px solid var(--border)', fontFamily:MONO };

function Badge({ publicada }) {
  return (
    <span style={{ padding:'2px 8px', borderRadius:4, fontSize:11,
      background: publicada ? 'var(--ok-pale,#e6f4ea)' : 'var(--bg-muted)',
      color: publicada ? 'var(--ok,#2d7a3a)' : 'var(--text-muted)' }}>
      {publicada ? 'Publicada' : 'Esborrany'}
    </span>
  );
}

export default function LegalDocsPage() {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sel, setSel] = useState(null);        // document seleccionat (detall)
  const [newDoc, setNewDoc] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    getLegalDocs()
      .then(r => setDocs(Array.isArray(r.data) ? r.data : r.data?.results ?? []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  if (sel) {
    const fresh = docs.find(d => d.id === sel.id) || sel;
    return <DocumentDetail doc={fresh} onBack={() => setSel(null)} onChange={load} />;
  }

  return (
    <div style={{ padding:24, maxWidth:900, margin:'0 auto', fontFamily:MONO }}>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20 }}>
        <div>
          <h1 style={{ fontSize:20, fontWeight:600, margin:0, display:'flex', alignItems:'center', gap:8 }}>
            <IconGavel size={20}/> Documents legals
          </h1>
          <span style={{ fontSize:12, color:'var(--text-muted)' }}>
            {docs.length} documents · versions amb hash SHA-256 i acceptacions probatòries
          </span>
        </div>
        <button onClick={() => setNewDoc(true)}
          style={{ display:'flex', alignItems:'center', gap:6, padding:'7px 14px',
            background:'var(--gold)', color:'#fff', border:'none', borderRadius:6,
            cursor:'pointer', fontSize:13, fontFamily:MONO }}>
          <IconPlus size={15}/> Nou document
        </button>
      </div>

      {newDoc && <NewDocForm onDone={() => { setNewDoc(false); load(); }} onCancel={() => setNewDoc(false)} />}

      {loading ? <div style={{ color:'var(--text-muted)' }}>…</div> : error ?
        <div style={{ color:'var(--err)' }}>{error}</div> : (
        <table style={{ width:'100%', borderCollapse:'collapse' }}>
          <thead><tr>{['Tipus','Nom','Versions','Última publicada','Actiu'].map((h,i) =>
            <th key={i} style={th}>{h}</th>)}</tr></thead>
          <tbody>
            {docs.map(d => {
              const pubs = (d.versions || []).filter(v => v.estat === 'PUBLICADA');
              const ultima = pubs.sort((a,b) => b.numero_versio - a.numero_versio)[0];
              return (
                <tr key={d.id} style={{ cursor:'pointer' }} onClick={() => setSel(d)}>
                  <td style={{ ...td, color:'var(--gold)', fontWeight:600 }}>{TIPUS[d.tipus] ?? d.tipus}</td>
                  <td style={td}>{d.nom}</td>
                  <td style={td}>{(d.versions || []).length}</td>
                  <td style={td}>{ultima ? `v${ultima.numero_versio} · ${ultima.sha256.slice(0,10)}…` : '—'}</td>
                  <td style={td}>{d.actiu ? 'Sí' : 'No'}</td>
                </tr>
              );
            })}
            {!docs.length && <tr><td colSpan={5}
              style={{ ...td, textAlign:'center', color:'var(--text-muted)' }}>Cap document legal.</td></tr>}
          </tbody>
        </table>
      )}
    </div>
  );
}

function NewDocForm({ onDone, onCancel }) {
  const [tipus, setTipus] = useState('TERMES');
  const [nom, setNom] = useState('');
  const inp = { padding:'7px 10px', fontSize:13, border:'1px solid var(--border)',
    borderRadius:6, fontFamily:MONO, background:'var(--bg-card)' };
  const save = () => {
    if (!nom.trim()) { alert('El nom és obligatori.'); return; }
    createLegalDoc({ tipus, nom }).then(onDone)
      .catch(e => alert(e.response?.data?.detail || e.message));
  };
  return (
    <div style={{ display:'flex', gap:8, alignItems:'center', marginBottom:16,
      padding:12, border:'1px solid var(--border)', borderRadius:8 }}>
      <select value={tipus} onChange={e => setTipus(e.target.value)} style={inp}>
        {Object.entries(TIPUS).map(([k,v]) => <option key={k} value={k}>{v}</option>)}
      </select>
      <input placeholder="Nom del document" value={nom} onChange={e => setNom(e.target.value)}
        style={{ ...inp, flex:1 }} />
      <button onClick={save} style={{ padding:'7px 14px', background:'var(--gold)', color:'#fff',
        border:'none', borderRadius:6, cursor:'pointer', fontFamily:MONO }}>Crear</button>
      <button onClick={onCancel} style={{ padding:'7px 14px', background:'none',
        border:'1px solid var(--border)', borderRadius:6, cursor:'pointer', fontFamily:MONO }}>×</button>
    </div>
  );
}

function DocumentDetail({ doc, onBack, onChange }) {
  const [acceptances, setAcceptances] = useState([]);
  const [draftText, setDraftText] = useState('');
  const [editingVer, setEditingVer] = useState(null);   // versió DRAFT en edició
  const [creatingVer, setCreatingVer] = useState(false);

  const versions = (doc.versions || []).slice().sort((a,b) => b.numero_versio - a.numero_versio);

  const loadAcc = useCallback(() => {
    getLegalAcceptances({ /* totes; filtrem per document a client */ })
      .then(r => {
        const rows = Array.isArray(r.data) ? r.data : r.data?.results ?? [];
        const versIds = new Set(versions.map(v => v.id));
        setAcceptances(rows.filter(a => versIds.has(a.versio)));
      })
      .catch(() => {});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doc.id]);

  useEffect(() => { loadAcc(); }, [loadAcc]);

  const startNew = () => { setCreatingVer(true); setDraftText(''); setEditingVer(null); };
  const startEdit = (v) => { setEditingVer(v); setDraftText(v.contingut); setCreatingVer(false); };

  const saveDraft = () => {
    const p = editingVer
      ? updateLegalVersion(editingVer.id, { contingut: draftText })
      : createLegalVersion({ document: doc.id, contingut: draftText });
    p.then(() => { setEditingVer(null); setCreatingVer(false); onChange(); })
     .catch(e => alert(e.response?.data?.detail || JSON.stringify(e.response?.data) || e.message));
  };

  const publish = (v) => {
    if (!confirm(`Publicar v${v.numero_versio}? Es CONGELARÀ: contingut i hash immutables, `
      + `sense esborrat possible.`)) return;
    publishLegalVersion(v.id).then(onChange)
      .catch(e => alert(e.response?.data?.detail || e.message));
  };

  const removeDraft = (v) => {
    if (!confirm(`Esborrar l'esborrany v${v.numero_versio}?`)) return;
    deleteLegalVersion(v.id).then(onChange)
      .catch(e => alert(e.response?.data?.detail || e.message));
  };

  const copyHash = (h) => { navigator.clipboard?.writeText(h); };

  const inp = { padding:'8px 10px', fontSize:13, border:'1px solid var(--border)',
    borderRadius:6, fontFamily:MONO, background:'var(--bg-card)', width:'100%', boxSizing:'border-box' };

  return (
    <div style={{ padding:24, maxWidth:820, margin:'0 auto', fontFamily:MONO }}>
      <button onClick={onBack} style={{ display:'flex', alignItems:'center', gap:6,
        background:'none', border:'none', color:'var(--text-muted)', cursor:'pointer',
        fontFamily:MONO, fontSize:13, marginBottom:12 }}>
        <IconArrowLeft size={15}/> Documents legals
      </button>
      <h2 style={{ fontSize:18, fontWeight:600, margin:'0 0 4px', display:'flex', alignItems:'center', gap:8 }}>
        <IconGavel size={18}/> {TIPUS[doc.tipus] ?? doc.tipus} · {doc.nom}
      </h2>

      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', margin:'20px 0 8px' }}>
        <h3 style={{ fontSize:14, fontWeight:600, margin:0 }}>Versions</h3>
        <button onClick={startNew} style={{ display:'flex', alignItems:'center', gap:6,
          padding:'6px 12px', background:'var(--gold)', color:'#fff', border:'none',
          borderRadius:6, cursor:'pointer', fontSize:12, fontFamily:MONO }}>
          <IconPlus size={14}/> Nova versió (esborrany)
        </button>
      </div>

      {(creatingVer || editingVer) && (
        <div style={{ marginBottom:16, padding:12, border:'1px solid var(--border)', borderRadius:8 }}>
          <div style={{ fontSize:12, color:'var(--text-muted)', marginBottom:6 }}>
            {editingVer ? `Editant esborrany v${editingVer.numero_versio}` : 'Nova versió (esborrany)'} · markdown/text
          </div>
          <textarea value={draftText} onChange={e => setDraftText(e.target.value)} rows={10}
            style={{ ...inp, fontFamily:MONO }} placeholder="Contingut del document…" />
          <div style={{ display:'flex', gap:8, marginTop:8 }}>
            <button onClick={saveDraft} style={{ padding:'7px 16px', background:'var(--gold)',
              color:'#fff', border:'none', borderRadius:6, cursor:'pointer', fontFamily:MONO }}>Guardar esborrany</button>
            <button onClick={() => { setEditingVer(null); setCreatingVer(false); }}
              style={{ padding:'7px 16px', background:'none', border:'1px solid var(--border)',
                borderRadius:6, cursor:'pointer', fontFamily:MONO }}>Cancel·lar</button>
          </div>
        </div>
      )}

      <table style={{ width:'100%', borderCollapse:'collapse', marginBottom:24 }}>
        <thead><tr>{['Versió','Estat','SHA-256','Publicada','Re-accept','']
          .map((h,i) => <th key={i} style={th}>{h}</th>)}</tr></thead>
        <tbody>
          {versions.map(v => {
            const pub = v.estat === 'PUBLICADA';
            return (
              <tr key={v.id}>
                <td style={{ ...td, fontWeight:600 }}>v{v.numero_versio}</td>
                <td style={td}><Badge publicada={pub} /></td>
                <td style={td}>
                  {pub ? (
                    <span style={{ display:'inline-flex', alignItems:'center', gap:6 }}>
                      <span title={v.sha256}>{v.sha256.slice(0,16)}…</span>
                      <button onClick={() => copyHash(v.sha256)} title="Copiar hash complet"
                        style={{ background:'none', border:'none', cursor:'pointer', color:'var(--gold)' }}>
                        <IconCopy size={13}/></button>
                    </span>
                  ) : <span style={{ color:'var(--text-muted)' }}>—</span>}
                </td>
                <td style={td}>{v.data_publicacio ? v.data_publicacio.slice(0,10) : '—'}</td>
                <td style={td}>{v.requereix_reacceptacio ? <IconCheck size={14} style={{ color:'var(--gold)' }}/> : '—'}</td>
                <td style={{ ...td, textAlign:'right' }}>
                  {pub ? (
                    <span style={{ display:'inline-flex', alignItems:'center', gap:4,
                      color:'var(--text-muted)', fontSize:11 }}><IconLock size={13}/> immutable</span>
                  ) : (
                    <span style={{ display:'inline-flex', gap:8 }}>
                      <button onClick={() => startEdit(v)} style={{ background:'none', border:'none',
                        cursor:'pointer', color:'var(--gold)', fontSize:12, fontFamily:MONO }}>Editar</button>
                      <button onClick={() => publish(v)} style={{ background:'none', border:'none',
                        cursor:'pointer', color:'var(--ok,#2d7a3a)', fontSize:12, fontFamily:MONO }}>Publicar</button>
                      <button onClick={() => removeDraft(v)} style={{ background:'none', border:'none',
                        cursor:'pointer', color:'var(--err,#c0392b)' }}><IconTrash size={13}/></button>
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
          {!versions.length && <tr><td colSpan={6}
            style={{ ...td, textAlign:'center', color:'var(--text-muted)' }}>Cap versió encara.</td></tr>}
        </tbody>
      </table>

      {/* Contingut read-only de les versions publicades */}
      {versions.filter(v => v.estat === 'PUBLICADA').map(v => (
        <details key={v.id} style={{ marginBottom:10 }}>
          <summary style={{ cursor:'pointer', fontSize:13 }}>
            v{v.numero_versio} · contingut publicat (read-only) · hash {v.sha256.slice(0,16)}…
          </summary>
          <pre style={{ whiteSpace:'pre-wrap', fontSize:12, background:'var(--bg-muted)',
            padding:12, borderRadius:6, marginTop:6 }}>{v.contingut}</pre>
          <div style={{ fontSize:11, color:'var(--text-muted)', wordBreak:'break-all' }}>
            SHA-256: {v.sha256}
            <button onClick={() => copyHash(v.sha256)} style={{ marginLeft:6, background:'none',
              border:'none', cursor:'pointer', color:'var(--gold)' }}><IconCopy size={12}/></button>
          </div>
        </details>
      ))}

      <h3 style={{ fontSize:14, fontWeight:600, margin:'24px 0 8px' }}>
        Historial d'acceptacions ({acceptances.length})
      </h3>
      <table style={{ width:'100%', borderCollapse:'collapse' }}>
        <thead><tr>{['Client','Versió','Acceptat per','Data','IP','Mètode']
          .map((h,i) => <th key={i} style={th}>{h}</th>)}</tr></thead>
        <tbody>
          {acceptances.map(a => (
            <tr key={a.id}>
              <td style={{ ...td, color:'var(--gold)' }}>{a.codi_tenant}</td>
              <td style={td}>v{a.numero_versio}</td>
              <td style={td}>{a.accepted_by}</td>
              <td style={td}>{a.timestamp?.slice(0,19).replace('T',' ')}</td>
              <td style={td}>{a.ip || '—'}</td>
              <td style={td}>{a.metode}</td>
            </tr>
          ))}
          {!acceptances.length && <tr><td colSpan={6}
            style={{ ...td, textAlign:'center', color:'var(--text-muted)' }}>Cap acceptació encara.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
