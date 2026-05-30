import { useState, useEffect } from 'react';

const API = import.meta.env.VITE_API_URL || '';

const CONFIDENCE_BADGES = {
  high:   { label: 'Alt',    bg: '#EBF8EC', color: '#1E8449' },
  medium: { label: 'Mitjà',  bg: '#FEF9E7', color: '#7D6608' },
  low:    { label: 'Baix',   bg: '#FDEDEC', color: '#C0392B' },
};

function authHeaders() {
  const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export default function ImportConfirmStep({ extracted, onConfirm, onBack, loading }) {
  const [garmentTypes, setGarmentTypes] = useState([]);
  const [sizeSystems, setSizeSystems] = useState([]);
  const [form, setForm] = useState({
    style_name:    extracted?.style_name?.value || extracted?.style_name || '',
    style_reference: extracted?.style_reference?.value || extracted?.style_reference || '',
    temporada:     String(extracted?.season?.value || extracted?.season || 'SS').slice(0, 2).toUpperCase(),
    any:           extracted?.year?.value || extracted?.year || new Date().getFullYear(),
    garment_type:  extracted?.garment_type_code || '',
    fit_type:      extracted?.fit_type || 'REGULAR',
    base_size:     extracted?.base_size?.value || extracted?.base_size || '',
    size_run:      extracted?.size_run?.value || extracted?.size_run || [],
    size_system:   '',
    codi_client:   String(extracted?.style_reference?.value || extracted?.style_reference || '').slice(0, 6),
  });
  const [pomOverrides, setPomOverrides] = useState({});

  useEffect(() => {
    fetch(`${API}/api/v1/garment-types/`, { headers: authHeaders() })
      .then(r => r.json())
      .then(d => setGarmentTypes(d.results || d || []))
      .catch(() => setGarmentTypes([]));
  }, []);

  useEffect(() => {
    fetch(`${API}/api/v1/size-systems/`, { headers: authHeaders() })
      .then(r => r.json())
      .then(d => {
        const all = d.results || d || [];
        const unique = Object.values(
          all.reduce((acc, ss) => { acc[ss.id] = ss; return acc; }, {})
        );
        setSizeSystems(unique);
      })
      .catch(() => setSizeSystems([]));
  }, []);

  const sizeRunArray = (() => {
    const raw = form.size_run;
    if (Array.isArray(raw)) return raw.map(s => String(s).trim()).filter(Boolean);
    if (typeof raw === 'string') {
      return raw.replace(/[\[\]'"\s]/g, '').split(',').filter(Boolean);
    }
    return [];
  })();

  const poms = extracted?.poms || [];

  const handleSubmit = () => {
    const overrides = {
      style_name:   form.style_name,
      temporada:    form.temporada,
      any:          parseInt(form.any),
      base_size:    form.base_size,
      size_run:     sizeRunArray.join('·'),
      codi_client:  form.codi_client,
      garment_type: form.garment_type,
      size_system:  form.size_system || undefined,
      pom_overrides: pomOverrides,
    };
    onConfirm(overrides);
  };

  const F = ({ label, required, children }) => (
    <div style={{ marginBottom: '0.75rem' }}>
      <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#666',
        display: 'block', marginBottom: 3, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {label}{required && <span style={{ color: '#C0392B' }}> *</span>}
      </label>
      {children}
    </div>
  );

  const Input = ({ field, ...props }) => (
    <input
      value={form[field] ?? ''}
      onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))}
      style={{ width: '100%', border: '1px solid #ddd', borderRadius: 6,
        padding: '0.4rem 0.6rem', fontSize: '0.85rem', boxSizing: 'border-box' }}
      {...props}
    />
  );

  const Select = ({ field, options, placeholder, ...props }) => (
    <select
      value={form[field] ?? ''}
      onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))}
      style={{ width: '100%', border: '1px solid #ddd', borderRadius: 6,
        padding: '0.4rem 0.6rem', fontSize: '0.85rem' }}
      {...props}
    >
      {placeholder && <option value="">{placeholder}</option>}
      {options.map(o => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  );

  return (
    <div style={{ fontFamily: 'IBM Plex Sans, sans-serif' }}>

      {/* Identification */}
      <Section title="IDENTIFICACIÓ">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
          <F label="Nom prenda" required>
            <Input field="style_name" placeholder="Olivia Dress" />
          </F>
          <F label="Referència client">
            <Input field="style_reference" placeholder="REPRISE SUMMER 26-08A" />
          </F>
          <F label="Codi intern (prefix)" required>
            <input
              value={form.codi_client ?? ''}
              maxLength={6}
              placeholder="BRW"
              onChange={e => setForm(f => ({
                ...f, codi_client: e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '')
              }))}
              style={{ width: '100%', border: '1px solid #ddd', borderRadius: 6,
                padding: '0.4rem 0.6rem', fontSize: '0.85rem', boxSizing: 'border-box' }}
            />
          </F>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
            <F label="Temporada">
              <Select field="temporada" options={[
                { value: 'SS', label: 'SS (Primavera-Estiu)' },
                { value: 'AW', label: 'AW (Tardor-Hivern)' },
                { value: 'FW', label: 'FW (Fall-Winter)' },
                { value: 'RE', label: 'RE (Resort)' },
              ]} />
            </F>
            <F label="Any">
              <Input field="any" type="number" min="2020" max="2040" />
            </F>
          </div>
        </div>
      </Section>

      {/* Garment type */}
      <Section title="TIPUS DE PRENDA">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem' }}>
          <F label="Garment Type" required>
            <Select field="garment_type"
              placeholder="— Selecciona —"
              options={garmentTypes.map(gt => ({
                value: gt.codi_client,
                label: gt.nom_en || gt.nom_client
              }))}
            />
          </F>
          <F label="Fit Type">
            <Select field="fit_type" options={[
              { value: 'REGULAR', label: 'Regular' },
              { value: 'SLIM', label: 'Slim / Fitted' },
              { value: 'RELAXED', label: 'Relaxed' },
              { value: 'OVERSIZED', label: 'Oversized' },
              { value: 'FLARED', label: 'Flared / Evasé' },
              { value: 'BODYCON', label: 'Bodycon' },
            ]} />
          </F>
        </div>
      </Section>

      {/* Size system */}
      <Section title="SISTEMA DE TALLES">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
          <F label="Size System">
            <Select field="size_system"
              placeholder="— Selecciona (opcional) —"
              options={sizeSystems.map(ss => ({
                value: ss.id,
                label: ss.nom || ss.codi
              }))}
            />
          </F>
          <F label="Talla base" required>
            <Input field="base_size" placeholder="S" />
          </F>
        </div>

        <F label="Run de talles">
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '0.25rem' }}>
            {sizeRunArray.map((s, i) => (
              <span key={i} style={{
                padding: '0.3rem 0.6rem', borderRadius: 6, fontSize: '0.8rem',
                fontFamily: 'IBM Plex Mono',
                background: s === form.base_size ? '#FEF5EC' : '#f0f0f0',
                border: `1px solid ${s === form.base_size ? '#c27a2a' : '#ddd'}`,
                color: s === form.base_size ? '#c27a2a' : '#444',
                fontWeight: s === form.base_size ? 700 : 400,
              }}>
                {s}{s === form.base_size ? ' ★' : ''}
              </span>
            ))}
            {sizeRunArray.length === 0 && (
              <span style={{ color: '#aaa', fontSize: '0.8rem' }}>
                No s'han detectat talles — introdueix manualment
              </span>
            )}
          </div>
          <input
            value={sizeRunArray.join(' ')}
            placeholder="XXS XS S M L XL (separa per espais o comes)"
            onChange={e => setForm(f => ({
              ...f,
              size_run: e.target.value.trim().split(/[\s,·]+/).filter(Boolean)
            }))}
            style={{ width: '100%', border: '1px solid #ddd', borderRadius: 6,
              padding: '0.4rem 0.6rem', fontSize: '0.85rem', boxSizing: 'border-box',
              marginTop: '0.4rem', fontFamily: 'IBM Plex Mono' }}
          />
        </F>
      </Section>

      {/* POMs detectats */}
      {poms.length > 0 && (
        <Section title={`PUNTS DE MESURA DETECTATS (${poms.length})`}>
          <p style={{ fontSize: '0.75rem', color: '#888', marginBottom: '0.75rem' }}>
            Matching automàtic per descripció. Els de confiança Baixa requereixen assignació manual.
            La nomenclatura (codi del client) s'usa com a nom de fletxa a la fitxa tècnica.
          </p>
          <table style={{ width: '100%', fontSize: '0.8rem', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f8f9fa' }}>
                {['Codi client', 'Descripció', 'Valor base', 'POM assignat', 'Confiança'].map(h => (
                  <th key={h} style={{ padding: '0.4rem 0.6rem', textAlign: 'left',
                    fontWeight: 600, color: '#666', fontSize: '0.7rem',
                    borderBottom: '1px solid #e5e7eb', textTransform: 'uppercase' }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {poms.map((p, i) => {
                const conf = (p.confidence || 'low').toLowerCase();
                const badge = CONFIDENCE_BADGES[conf] || CONFIDENCE_BADGES.low;
                const override = pomOverrides[p.code];
                return (
                  <tr key={i} style={{ background: i % 2 === 0 ? '#fff' : '#fafafa',
                    borderBottom: '1px solid #f0f0f0' }}>
                    <td style={{ padding: '0.4rem 0.6rem', fontFamily: 'IBM Plex Mono',
                      fontSize: '0.75rem', color: '#c27a2a', fontWeight: 600 }}>
                      {p.code}
                    </td>
                    <td style={{ padding: '0.4rem 0.6rem', color: '#333' }}>
                      {p.description}
                    </td>
                    <td style={{ padding: '0.4rem 0.6rem', fontFamily: 'IBM Plex Mono',
                      textAlign: 'right', color: '#444' }}>
                      {p.base_value_cm != null ? `${p.base_value_cm} cm` : '—'}
                    </td>
                    <td style={{ padding: '0.4rem 0.6rem' }}>
                      {conf === 'low' || override !== undefined ? (
                        <input
                          type="text"
                          placeholder="POM-001 o codi_client"
                          defaultValue={override || ''}
                          onBlur={e => setPomOverrides(prev => ({
                            ...prev, [p.code]: e.target.value.trim()
                          }))}
                          style={{ border: `1px solid ${conf === 'low' ? '#F5B7B1' : '#ddd'}`,
                            borderRadius: 4, padding: '0.2rem 0.4rem',
                            fontSize: '0.75rem', fontFamily: 'IBM Plex Mono', width: 100 }}
                        />
                      ) : (
                        <span style={{ fontFamily: 'IBM Plex Mono', fontSize: '0.75rem',
                          color: '#1A5276' }}>
                          {p.matched_pom || 'auto'}
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '0.4rem 0.6rem' }}>
                      <span style={{ fontSize: '0.7rem', padding: '0.15rem 0.4rem',
                        borderRadius: 3, background: badge.bg, color: badge.color }}>
                        {badge.label}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Section>
      )}

      {/* Botons */}
      <div style={{ display: 'flex', justifyContent: 'space-between',
        marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid #e5e7eb' }}>
        <button onClick={onBack}
          style={{ padding: '0.5rem 1rem', border: '1px solid #ddd', borderRadius: 6,
            background: '#fff', cursor: 'pointer', fontSize: '0.85rem' }}>
          ← Tornar
        </button>
        <button
          onClick={handleSubmit}
          disabled={loading || !form.style_name || !form.garment_type || !form.base_size}
          style={{ padding: '0.5rem 1.5rem', border: 'none', borderRadius: 6,
            background: (!form.style_name || !form.garment_type || !form.base_size)
              ? '#ddd' : '#c27a2a',
            color: '#fff', cursor: 'pointer', fontSize: '0.85rem', fontWeight: 500 }}>
          {loading ? 'Creant model...' : '✓ Crear model'}
        </button>
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: '1.25rem', padding: '1rem',
      border: '1px solid #e5e7eb', borderRadius: 8, background: '#fff' }}>
      <p style={{ margin: '0 0 0.75rem', fontSize: '0.7rem', fontWeight: 700,
        color: '#c27a2a', letterSpacing: '0.08em' }}>{title}</p>
      {children}
    </div>
  );
}
