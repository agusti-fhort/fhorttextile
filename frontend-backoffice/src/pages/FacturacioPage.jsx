import { useState, useEffect, useCallback } from 'react';
import {
  getSeries, createSerie, updateSerie, deleteSerie,
  getTipusIva, createTipusIva, updateTipusIva, deleteTipusIva,
  getFactures, getFactura, createFactura, deleteFactura, previewFactura,
  emetreFactura, rectificarFactura, addLinia, deleteLinia, fetchPdf,
  previewPeriode, generarPeriode,
} from '../api/invoices';
import { getTenants } from '../api/tenants';

// Facturació: factures (camí manual complet), sèries de numeració i tipus d'IVA.
// Català literal, com la resta de pàgines de gestió del backoffice (l'i18n d'aquesta
// SPA només cobreix el login).

const MONO = "'IBM Plex Mono', monospace";
const TABS = [
  { key: 'factures', label: 'Factures', icon: 'ti-file-invoice' },
  { key: 'tancament', label: 'Tancament de període', icon: 'ti-calendar-stats' },
  { key: 'series', label: 'Sèries', icon: 'ti-list-numbers' },
  { key: 'iva', label: "Tipus d'IVA", icon: 'ti-receipt-tax' },
];
const ESTAT_COLOR = {
  esborrany: 'var(--text-muted)', emesa: 'var(--gold)',
  pagada: '#3d7a3d', 'cancel·lada': '#a33',
};
const REGIMS = [
  { v: '', l: '— cap (no és el defecte de cap règim)' },
  { v: 'espanyol', l: 'IVA espanyol' },
  { v: 'reverse_charge_ue', l: 'Reverse charge UE' },
  { v: 'oss_ue', l: 'OSS UE' },
  { v: 'fora_ue', l: 'Fora UE' },
];

const th = { padding: '8px 12px', fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase',
  letterSpacing: '0.04em', textAlign: 'left', borderBottom: '1px solid var(--border)', fontWeight: 400 };
const td = { padding: '10px 12px', fontSize: 13, color: 'var(--text-main)', borderBottom: '1px solid var(--border)' };
const inp = { padding: '7px 9px', fontSize: 13, fontFamily: 'inherit', border: '1px solid var(--border)',
  borderRadius: 6, background: 'var(--bg-main)', color: 'var(--text-main)', boxSizing: 'border-box' };
const btn = (kind) => ({
  padding: '7px 13px', fontSize: 13, borderRadius: 6, cursor: 'pointer', fontFamily: 'inherit',
  border: kind === 'ghost' ? '1px solid var(--border)' : 'none',
  background: kind === 'ghost' ? 'transparent' : kind === 'danger' ? '#a33' : 'var(--gold)',
  color: kind === 'ghost' ? 'var(--text-main)' : '#fff',
});
const err = (e) => e?.response?.data?.error || e?.response?.data?.detail
  || Object.values(e?.response?.data || {})?.flat?.()?.join(' · ') || e.message;
const money = (v, m = 'EUR') => `${Number(v ?? 0).toLocaleString('ca-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${m}`;

export default function FacturacioPage() {
  const [tab, setTab] = useState('factures');
  return (
    <div style={{ padding: '1.5rem 2rem', fontFamily: MONO }}>
      <h1 style={{ fontSize: 20, fontWeight: 500, margin: '0 0 4px' }}>Facturació</h1>
      <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: '0 0 18px' }}>
        Factures de FHORT als tenants · numeració per sèries · IVA per règim del client.
      </p>
      <div style={{ display: 'flex', gap: 6, marginBottom: 18, borderBottom: '1px solid var(--border)' }}>
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)} style={{
            padding: '8px 14px', fontSize: 13, fontFamily: 'inherit', cursor: 'pointer',
            border: 'none', background: 'transparent',
            color: tab === t.key ? 'var(--gold)' : 'var(--text-muted)',
            borderBottom: `2px solid ${tab === t.key ? 'var(--gold)' : 'transparent'}`,
          }}>
            <i className={`ti ${t.icon}`} style={{ marginRight: 6 }} />{t.label}
          </button>
        ))}
      </div>
      {tab === 'factures' && <Factures />}
      {tab === 'tancament' && <Tancament />}
      {tab === 'series' && <Series />}
      {tab === 'iva' && <TipusIva />}
    </div>
  );
}

// ───────────────────────────── Sèries ─────────────────────────────
function Series() {
  const [items, setItems] = useState([]);
  const [editing, setEditing] = useState(null);
  const [e, setE] = useState(null);
  const load = useCallback(() => {
    getSeries().then(r => setItems(r.data?.results ?? r.data ?? [])).catch(x => setE(err(x)));
  }, []);
  useEffect(() => { load(); }, [load]);

  const save = () => {
    const p = editing.id ? updateSerie(editing.id, editing) : createSerie(editing);
    p.then(() => { setEditing(null); setE(null); load(); }).catch(x => setE(err(x)));
  };
  const remove = (it) => {
    if (!confirm(`Esborrar la sèrie ${it.codi}?`)) return;
    deleteSerie(it.id).then(load).catch(x => setE(err(x)));
  };

  return (
    <div>
      <Bar onNew={() => setEditing({ codi: '', nom: '', format: '{codi}-{any}-{num:04d}', reinici_anual: true, activa: true })}
           label="Nova sèrie" e={e} />
      {editing && (
        <Card>
          <Row>
            <F label="Codi"><input style={{ ...inp, width: 90 }} value={editing.codi}
              onChange={ev => setEditing({ ...editing, codi: ev.target.value.toUpperCase() })} /></F>
            <F label="Nom" grow><input style={{ ...inp, width: '100%' }} value={editing.nom}
              onChange={ev => setEditing({ ...editing, nom: ev.target.value })} /></F>
          </Row>
          <Row>
            <F label="Format" grow hint="Claus: {codi} {any} {any2} {num}. Exemple: {codi}{any2}-{num:06d}">
              <input style={{ ...inp, width: '100%' }} value={editing.format}
                onChange={ev => setEditing({ ...editing, format: ev.target.value })} /></F>
          </Row>
          <Row>
            <label style={{ fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
              <input type="checkbox" checked={editing.reinici_anual}
                onChange={ev => setEditing({ ...editing, reinici_anual: ev.target.checked })} />
              Reiniciar el correlatiu cada any
            </label>
            <label style={{ fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
              <input type="checkbox" checked={editing.activa}
                onChange={ev => setEditing({ ...editing, activa: ev.target.checked })} />
              Activa
            </label>
          </Row>
          <Actions onSave={save} onCancel={() => { setEditing(null); setE(null); }} />
        </Card>
      )}
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead><tr>{['Codi', 'Nom', 'Format', 'Pròxim número', 'Correlatiu', 'Activa', ''].map(h =>
          <th key={h} style={th}>{h}</th>)}</tr></thead>
        <tbody>
          {items.map(it => (
            <tr key={it.id}>
              <td style={{ ...td, color: 'var(--gold)' }}>{it.codi}</td>
              <td style={td}>{it.nom}</td>
              <td style={{ ...td, color: 'var(--text-muted)' }}>{it.format}</td>
              <td style={td}>{it.exemple}</td>
              <td style={{ ...td, color: 'var(--text-muted)' }}>
                {it.any_actual ? `${it.any_actual} · ${it.comptador}` : '— (cap encara)'}
              </td>
              <td style={td}>{it.activa ? 'Sí' : 'No'}</td>
              <td style={{ ...td, textAlign: 'right', whiteSpace: 'nowrap' }}>
                <IconBtn icon="ti-edit" onClick={() => setEditing(it)} />
                <IconBtn icon="ti-trash" onClick={() => remove(it)} />
              </td>
            </tr>
          ))}
          {!items.length && <tr><td style={{ ...td, color: 'var(--text-muted)' }} colSpan={7}>
            Cap sèrie. Sense sèrie no es pot emetre cap factura.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

// ───────────────────────────── Tipus d'IVA ─────────────────────────────
function TipusIva() {
  const [items, setItems] = useState([]);
  const [editing, setEditing] = useState(null);
  const [e, setE] = useState(null);
  const load = useCallback(() => {
    getTipusIva().then(r => setItems(r.data?.results ?? r.data ?? [])).catch(x => setE(err(x)));
  }, []);
  useEffect(() => { load(); }, [load]);

  const save = () => {
    const p = editing.id ? updateTipusIva(editing.id, editing) : createTipusIva(editing);
    p.then(() => { setEditing(null); setE(null); load(); }).catch(x => setE(err(x)));
  };
  const remove = (it) => {
    if (!confirm(`Esborrar el tipus ${it.codi}?`)) return;
    deleteTipusIva(it.id).then(load).catch(x => setE(err(x)));
  };

  return (
    <div>
      <Bar onNew={() => setEditing({ codi: '', nom: '', percentatge: '21.00', regim_default: '', mencio_legal: '', actiu: true })}
           label="Nou tipus" e={e} />
      {editing && (
        <Card>
          <Row>
            <F label="Codi"><input style={{ ...inp, width: 120 }} value={editing.codi}
              onChange={ev => setEditing({ ...editing, codi: ev.target.value.toUpperCase() })} /></F>
            <F label="Nom" grow><input style={{ ...inp, width: '100%' }} value={editing.nom}
              onChange={ev => setEditing({ ...editing, nom: ev.target.value })} /></F>
            <F label="%"><input style={{ ...inp, width: 80 }} value={editing.percentatge}
              onChange={ev => setEditing({ ...editing, percentatge: ev.target.value })} /></F>
          </Row>
          <Row>
            <F label="Tipus per defecte del règim" grow
               hint="El règim del client es deriva sol del seu país i VAT. Un sol tipus per règim.">
              <select style={{ ...inp, width: '100%' }} value={editing.regim_default}
                onChange={ev => setEditing({ ...editing, regim_default: ev.target.value })}>
                {REGIMS.map(r => <option key={r.v} value={r.v}>{r.l}</option>)}
              </select></F>
          </Row>
          <Row>
            <F label="Menció legal" grow hint="Text obligatori al PDF (inversió del subjecte passiu, exempció…).">
              <textarea style={{ ...inp, width: '100%', minHeight: 54, resize: 'vertical' }}
                value={editing.mencio_legal}
                onChange={ev => setEditing({ ...editing, mencio_legal: ev.target.value })} /></F>
          </Row>
          <Row>
            <label style={{ fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
              <input type="checkbox" checked={editing.actiu}
                onChange={ev => setEditing({ ...editing, actiu: ev.target.checked })} /> Actiu
            </label>
          </Row>
          <Actions onSave={save} onCancel={() => { setEditing(null); setE(null); }} />
        </Card>
      )}
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead><tr>{['Codi', 'Nom', '%', 'Règim per defecte', 'Menció legal', 'Actiu', ''].map(h =>
          <th key={h} style={th}>{h}</th>)}</tr></thead>
        <tbody>
          {items.map(it => (
            <tr key={it.id}>
              <td style={{ ...td, color: 'var(--gold)' }}>{it.codi}</td>
              <td style={td}>{it.nom}</td>
              <td style={td}>{Number(it.percentatge)}%</td>
              <td style={{ ...td, color: 'var(--text-muted)' }}>
                {REGIMS.find(r => r.v === it.regim_default)?.l ?? '—'}</td>
              <td style={{ ...td, color: 'var(--text-muted)', maxWidth: 260, overflow: 'hidden',
                textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{it.mencio_legal || '—'}</td>
              <td style={td}>{it.actiu ? 'Sí' : 'No'}</td>
              <td style={{ ...td, textAlign: 'right', whiteSpace: 'nowrap' }}>
                <IconBtn icon="ti-edit" onClick={() => setEditing(it)} />
                <IconBtn icon="ti-trash" onClick={() => remove(it)} />
              </td>
            </tr>
          ))}
          {!items.length && <tr><td style={{ ...td, color: 'var(--text-muted)' }} colSpan={7}>
            Cap tipus d'IVA. Sense un tipus per al règim del client, emetre fallarà.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

// ───────────────────────────── Factures ─────────────────────────────
function Factures() {
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(null);       // id de la factura oberta
  const [nova, setNova] = useState(null);
  const [tenants, setTenants] = useState([]);
  const [estat, setEstat] = useState('');
  const [e, setE] = useState(null);

  const load = useCallback(() => {
    const params = estat ? { estat } : {};
    getFactures(params).then(r => setItems(r.data?.results ?? r.data ?? [])).catch(x => setE(err(x)));
  }, [estat]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    getTenants().then(r => setTenants(r.data?.results ?? r.data ?? [])).catch(() => {});
  }, []);

  const crear = () => {
    createFactura(nova).then(r => { setNova(null); setE(null); load(); setOpen(r.data.id); })
      .catch(x => setE(err(x)));
  };
  const remove = (it) => {
    if (!confirm(`Esborrar l'esborrany de ${it.client_codi}?`)) return;
    deleteFactura(it.id).then(load).catch(x => setE(err(x)));
  };

  if (open) return <FacturaDetall id={open} onBack={() => { setOpen(null); load(); }} />;

  return (
    <div>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 14 }}>
        <button style={btn()} onClick={() => setNova({ client: '', period: new Date().toISOString().slice(0, 7), nota: '' })}>
          <i className="ti ti-plus" style={{ marginRight: 5 }} />Nova factura manual
        </button>
        <select style={{ ...inp, width: 180 }} value={estat} onChange={ev => setEstat(ev.target.value)}>
          <option value="">Tots els estats</option>
          {['esborrany', 'emesa', 'pagada', 'cancel·lada'].map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        {e && <span style={{ color: '#a33', fontSize: 12 }}>{e}</span>}
      </div>
      {nova && (
        <Card>
          <Row>
            <F label="Client">
              <select style={{ ...inp, width: 220 }} value={nova.client}
                onChange={ev => setNova({ ...nova, client: ev.target.value })}>
                <option value="">— tria un tenant —</option>
                {tenants.map(t => <option key={t.codi_tenant} value={t.codi_tenant}>
                  {t.codi_tenant} · {t.nom}</option>)}
              </select></F>
            <F label="Període" hint="Mes de meritació (YYYY-MM).">
              <input style={{ ...inp, width: 110 }} value={nova.period}
                onChange={ev => setNova({ ...nova, period: ev.target.value })} /></F>
          </Row>
          <Row>
            <F label="Nota" grow><input style={{ ...inp, width: '100%' }} value={nova.nota}
              onChange={ev => setNova({ ...nova, nota: ev.target.value })} /></F>
          </Row>
          <Actions onSave={crear} onCancel={() => { setNova(null); setE(null); }} saveLabel="Crear esborrany" />
        </Card>
      )}
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead><tr>{['Número', 'Client', 'Període', 'Tipus', 'Estat', 'Base', 'IVA', 'Total', ''].map(h =>
          <th key={h} style={th}>{h}</th>)}</tr></thead>
        <tbody>
          {items.map(it => (
            <tr key={it.id} style={{ cursor: 'pointer' }} onClick={() => setOpen(it.id)}>
              <td style={{ ...td, color: 'var(--gold)' }}>{it.numero || <span style={{ color: 'var(--text-muted)' }}>— esborrany</span>}</td>
              <td style={td}>{it.client_codi}</td>
              <td style={td}>{it.period}</td>
              <td style={{ ...td, color: 'var(--text-muted)' }}>{it.tipus}</td>
              <td style={{ ...td, color: ESTAT_COLOR[it.estat] }}>{it.estat}</td>
              <td style={{ ...td, textAlign: 'right' }}>{money(it.base_imposable, '')}</td>
              <td style={{ ...td, textAlign: 'right' }}>{money(it.quota_iva, '')}</td>
              <td style={{ ...td, textAlign: 'right', fontWeight: 500 }}>{money(it.total, it.moneda)}</td>
              <td style={{ ...td, textAlign: 'right' }} onClick={ev => ev.stopPropagation()}>
                {it.estat === 'esborrany' && <IconBtn icon="ti-trash" onClick={() => remove(it)} />}
              </td>
            </tr>
          ))}
          {!items.length && <tr><td style={{ ...td, color: 'var(--text-muted)' }} colSpan={9}>Cap factura.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

function FacturaDetall({ id, onBack }) {
  const [inv, setInv] = useState(null);
  const [calcul, setCalcul] = useState(null);
  const [series, setSeries] = useState([]);
  const [serie, setSerie] = useState('');
  const [linia, setLinia] = useState(null);
  const [e, setE] = useState(null);

  const load = useCallback(() => {
    previewFactura(id)
      .then(r => { setInv(r.data); setCalcul(r.data.calcul); setE(null); })
      .catch(x => {
        // El preview pot fallar per configuració (cap tipus d'IVA per al règim): la
        // factura ha de seguir sent visible i el motiu, llegible.
        setE(err(x));
        getFactura(id).then(r2 => { setInv(r2.data); setCalcul(null); }).catch(() => {});
      });
  }, [id]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { getSeries({ activa: true }).then(r => setSeries(r.data?.results ?? r.data ?? [])).catch(() => {}); }, []);

  if (!inv) return <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Carregant…</div>;
  const draft = inv.estat === 'esborrany';

  const afegir = () => {
    addLinia(id, linia).then(() => { setLinia(null); load(); }).catch(x => setE(err(x)));
  };
  const treure = (l) => deleteLinia(id, l.id).then(load).catch(x => setE(err(x)));
  const emetre = () => {
    if (!serie) { setE('Tria la sèrie amb què vols emetre.'); return; }
    if (!confirm('Emetre la factura? Un cop emesa no es pot editar ni esborrar: només rectificar.')) return;
    emetreFactura(id, Number(serie)).then(load).catch(x => setE(err(x)));
  };
  const rectificar = () => {
    const motiu = prompt('Motiu de la rectificativa:');
    if (motiu === null) return;
    rectificarFactura(id, motiu).then(() => onBack()).catch(x => setE(err(x)));
  };
  const veurePdf = () => {
    fetchPdf(id).then(r => window.open(URL.createObjectURL(r.data), '_blank')).catch(x => setE(err(x)));
  };

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
        <button style={btn('ghost')} onClick={onBack}><i className="ti ti-arrow-left" /> Tornar</button>
        <div style={{ fontSize: 15 }}>
          <span style={{ color: 'var(--gold)' }}>{inv.numero || 'Esborrany'}</span>
          <span style={{ color: 'var(--text-muted)' }}> · {inv.client_codi} · {inv.period}</span>
        </div>
        <span style={{ fontSize: 12, color: ESTAT_COLOR[inv.estat], border: `1px solid ${ESTAT_COLOR[inv.estat]}`,
          borderRadius: 10, padding: '2px 9px' }}>{inv.estat}</span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
          <button style={btn('ghost')} onClick={veurePdf}><i className="ti ti-file-type-pdf" /> PDF</button>
          {!draft && inv.tipus !== 'rectificativa' &&
            <button style={btn('ghost')} onClick={rectificar}><i className="ti ti-file-diff" /> Rectificar</button>}
        </div>
      </div>
      {e && <div style={{ background: '#fdf0f0', border: '1px solid #a33', color: '#a33', borderRadius: 6,
        padding: '8px 12px', fontSize: 12, marginBottom: 12 }}>{e}</div>}
      {inv.rectifica_numero && <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 10 }}>
        Rectifica la factura {inv.rectifica_numero}.</div>}

      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 14 }}>
        <thead><tr>{['Concepte', 'Qtat', 'Preu', 'IVA', 'Import', ''].map(h => <th key={h} style={th}>{h}</th>)}</tr></thead>
        <tbody>
          {inv.lines.map(l => (
            <tr key={l.id}>
              <td style={td}>{l.descripcio}</td>
              <td style={{ ...td, textAlign: 'right' }}>{Number(l.quantitat)}</td>
              <td style={{ ...td, textAlign: 'right' }}>{money(l.preu_unit, '')}</td>
              <td style={{ ...td, textAlign: 'right', color: 'var(--text-muted)' }}>
                {l.pct_iva > 0 ? `${Number(l.pct_iva)}%` : '—'}</td>
              <td style={{ ...td, textAlign: 'right' }}>{money(l.total, '')}</td>
              <td style={{ ...td, textAlign: 'right' }}>
                {draft && <IconBtn icon="ti-trash" onClick={() => treure(l)} />}</td>
            </tr>
          ))}
          {!inv.lines.length && <tr><td style={{ ...td, color: 'var(--text-muted)' }} colSpan={6}>
            Cap línia. Una factura sense línies no es pot emetre.</td></tr>}
        </tbody>
      </table>

      {draft && (linia ? (
        <Card>
          <Row>
            <F label="Concepte" grow><input style={{ ...inp, width: '100%' }} autoFocus value={linia.descripcio}
              onChange={ev => setLinia({ ...linia, descripcio: ev.target.value })} /></F>
            <F label="Quantitat"><input style={{ ...inp, width: 90 }} value={linia.quantitat}
              onChange={ev => setLinia({ ...linia, quantitat: ev.target.value })} /></F>
            <F label="Preu unitari"><input style={{ ...inp, width: 110 }} value={linia.preu_unit}
              onChange={ev => setLinia({ ...linia, preu_unit: ev.target.value })} /></F>
          </Row>
          <Actions onSave={afegir} onCancel={() => setLinia(null)} saveLabel="Afegir línia" />
        </Card>
      ) : (
        <button style={btn('ghost')} onClick={() => setLinia({ descripcio: '', quantitat: '1', preu_unit: '' })}>
          <i className="ti ti-plus" /> Afegir línia
        </button>
      ))}

      {calcul && (
        <div style={{ marginTop: 18, marginLeft: 'auto', width: 340 }}>
          <Tot label="Base imposable" v={money(calcul.base_imposable, '')} />
          {calcul.per_tipus.map(t => (
            <Tot key={t.codi} label={`IVA ${Number(t.pct)}% sobre ${money(t.base, '')}`} v={money(t.quota, '')} />
          ))}
          <Tot label="TOTAL" v={money(calcul.total, inv.moneda)} strong />
          {calcul.per_tipus.filter(t => t.mencio_legal).map(t => (
            <div key={t.codi} style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>{t.mencio_legal}</div>
          ))}
        </div>
      )}

      {draft && (
        <div style={{ marginTop: 22, paddingTop: 14, borderTop: '1px solid var(--border)',
          display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>Emetre amb la sèrie</span>
          <select style={{ ...inp, width: 260 }} value={serie} onChange={ev => setSerie(ev.target.value)}>
            <option value="">— tria una sèrie —</option>
            {series.map(s => <option key={s.id} value={s.id}>{s.codi} · pròxim: {s.exemple}</option>)}
          </select>
          <button style={btn()} onClick={emetre}><i className="ti ti-stamp" style={{ marginRight: 5 }} />Emetre</button>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            El número s'assigna ara; després la factura queda congelada.
          </span>
        </div>
      )}
    </div>
  );
}

// ───────────────────────────── Tancament de període ─────────────────────────────
function Tancament() {
  const [period, setPeriod] = useState(new Date().toISOString().slice(0, 7));
  const [rows, setRows] = useState(null);
  const [busy, setBusy] = useState(false);
  const [generat, setGenerat] = useState(false);
  const [e, setE] = useState(null);

  const preview = () => {
    setBusy(true); setE(null); setGenerat(false);
    previewPeriode(period).then(r => setRows(r.data.clients)).catch(x => setE(err(x))).finally(() => setBusy(false));
  };
  const generar = () => {
    if (!confirm(`Generar els esborranys de ${period}? És idempotent: re-executar no duplica.`)) return;
    setBusy(true); setE(null);
    generarPeriode(period).then(r => { setRows(r.data.clients); setGenerat(true); })
      .catch(x => setE(err(x))).finally(() => setBusy(false));
  };

  return (
    <div>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 16 }}>
        <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>Període</span>
        <input style={{ ...inp, width: 120 }} value={period} onChange={ev => setPeriod(ev.target.value)} placeholder="YYYY-MM" />
        <button style={btn('ghost')} onClick={preview} disabled={busy}>
          <i className="ti ti-eye" style={{ marginRight: 5 }} />Previsualitzar
        </button>
        <button style={btn()} onClick={generar} disabled={busy || !rows}>
          <i className="ti ti-file-plus" style={{ marginRight: 5 }} />Generar esborranys
        </button>
        {e && <span style={{ color: '#a33', fontSize: 12 }}>{e}</span>}
      </div>
      {generat && <div style={{ background: '#f0f7f0', border: '1px solid #3d7a3d', color: '#3d7a3d',
        borderRadius: 6, padding: '8px 12px', fontSize: 12, marginBottom: 12 }}>
        Esborranys generats. Revisa'ls a la pestanya Factures i emet-los quan estiguin llestos.</div>}
      {rows && (rows.length === 0 ? (
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
          Cap client facturable en aquest període (viu, no gratuït i amb contracte vigent).
        </p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead><tr>{['Client', 'Quota', 'Consum', 'Exclosos', 'Total (s/IVA)', 'Estat', 'Avisos'].map(h =>
            <th key={h} style={th}>{h}</th>)}</tr></thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.codi_client}>
                <td style={{ ...td, color: 'var(--gold)' }}>{r.codi_client}</td>
                <td style={{ ...td, textAlign: 'right' }}>{r.quota ? money(r.quota, '') : '—'}</td>
                <td style={td}>{r.consum
                  ? `${r.consum.events} events · ${r.consum.facturats}×${Number(r.consum.tarifa)}`
                  : '—'}</td>
                <td style={{ ...td, textAlign: 'right', color: 'var(--text-muted)' }}>{r.exclosos || '—'}</td>
                <td style={{ ...td, textAlign: 'right', fontWeight: 500 }}>{money(r.total_sense_iva, '')}</td>
                <td style={td}>{r.invoice_id
                  ? <span style={{ color: '#3d7a3d' }}>DRAFT #{r.invoice_id}{r.creada ? '' : ' (reaprofitat)'}</span>
                  : <span style={{ color: 'var(--text-muted)' }}>—</span>}</td>
                <td style={{ ...td, fontSize: 11, color: 'var(--text-muted)' }}>
                  {(r.avisos || []).join(' · ') || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ))}
      {!rows && <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
        Tria un període i previsualitza: veuràs, per client, la quota i el consum que es facturarien.
        La previsualització no toca res; només «Generar esborranys» els crea (en DRAFT, mai emesos).
      </p>}
    </div>
  );
}

// ───────────────────────────── UI compartida ─────────────────────────────
function Bar({ onNew, label, e }) {
  return (
    <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 14 }}>
      <button style={btn()} onClick={onNew}><i className="ti ti-plus" style={{ marginRight: 5 }} />{label}</button>
      {e && <span style={{ color: '#a33', fontSize: 12 }}>{e}</span>}
    </div>
  );
}
const Card = ({ children }) => (
  <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8,
    padding: 14, marginBottom: 16 }}>{children}</div>
);
const Row = ({ children }) => (
  <div style={{ display: 'flex', gap: 12, marginBottom: 10, alignItems: 'flex-end' }}>{children}</div>
);
const F = ({ label, hint, grow, children }) => (
  <div style={{ flex: grow ? 1 : 'none' }}>
    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 3 }}>{label}</div>
    {children}
    {hint && <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3 }}>{hint}</div>}
  </div>
);
const Actions = ({ onSave, onCancel, saveLabel = 'Desar' }) => (
  <div style={{ display: 'flex', gap: 8 }}>
    <button style={btn()} onClick={onSave}>{saveLabel}</button>
    <button style={btn('ghost')} onClick={onCancel}>Cancel·lar</button>
  </div>
);
const IconBtn = ({ icon, onClick }) => (
  <button onClick={onClick} style={{ background: 'none', border: 'none', cursor: 'pointer',
    color: 'var(--text-muted)', padding: 4, fontSize: 15 }}><i className={`ti ${icon}`} /></button>
);
const Tot = ({ label, v, strong }) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0',
    fontSize: strong ? 14 : 13, fontWeight: strong ? 600 : 400,
    color: strong ? 'var(--gold)' : 'var(--text-main)',
    borderTop: strong ? '1px solid var(--gold)' : 'none', marginTop: strong ? 4 : 0, paddingTop: strong ? 8 : 4 }}>
    <span>{label}</span><span>{v}</span>
  </div>
);
