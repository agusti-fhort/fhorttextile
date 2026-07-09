import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { taskTypes } from '../api/endpoints';
import i18n from '../i18n';
import { formatMinutes } from '../utils/format';
import { taskTypeLabel } from '../utils/taskType';

const API = import.meta.env.VITE_API_URL;
const authHeaders = () => ({ Authorization: `Bearer ${localStorage.getItem('access_token')}` });
const fmtDate = (v) => v ? new Date(v).toLocaleDateString(i18n.language || 'ca', { dateStyle: 'medium' }) : '—';
const PAGE_SIZE = 25;

// Navegador de mesos: period = '' (tots) o 'YYYY-MM'
const fmtPeriod = (p) => p ? new Date(p + '-01').toLocaleDateString(i18n.language || 'ca', { month: 'long', year: 'numeric' }) : i18n.t('registre.all_months_long');
const prevMonth = (p) => { const d = p ? new Date(p + '-01') : new Date(); d.setMonth(d.getMonth() - 1); return d.toISOString().slice(0, 7); };
const nextMonth = (p) => { const d = p ? new Date(p + '-01') : new Date(); d.setMonth(d.getMonth() + 1); return d.toISOString().slice(0, 7); };

// KPI mini-stat discret (inline, sense component extern)
const MiniStat = ({ label, value }) => (
  <div style={{ display:'flex', flexDirection:'column', gap:2,
                padding:'10px 16px', background:'var(--bg-card)',
                border:'0.5px solid var(--border)', borderRadius:8, minWidth:140 }}>
    <span style={{ fontSize: 'var(--fs-body)', color:'var(--text-muted)', textTransform:'uppercase',
                   letterSpacing:'0.04em' }}>{label}</span>
    <span style={{ fontSize:'1.05rem', color:'var(--text-main)', fontWeight:600 }}>{value}</span>
  </div>
);

export default function RegistreActivitat() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [items, setItems]     = useState([]);
  const [count, setCount]     = useState(0);
  const [totals, setTotals]   = useState({});
  const [loading, setLoading] = useState(true);
  const [period, setPeriod]   = useState('');
  const [tecnics, setTecnics] = useState([]);
  const [tecnicId, setTecnicId] = useState('');
  const [taskTypeList, setTaskTypeList] = useState([]);
  const [taskTypeId, setTaskTypeId] = useState('');
  const [page, setPage]       = useState(1);

  // Carregar selectors (tècnics + tipus de tasca) — una sola vegada
  useEffect(() => {
    fetch(`${API}/api/v1/users/`, { headers: authHeaders() })
      .then(r => r.json())
      .then(d => setTecnics(d.results || d))
      .catch(() => {});
    taskTypes.list()
      .then(d => setTaskTypeList(d.data?.results || d.data || []))
      .catch(() => {});
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    const params = new URLSearchParams({ page, page_size: PAGE_SIZE });
    if (period)     params.set('period', period);
    if (tecnicId)   params.set('tecnic_id', tecnicId);
    if (taskTypeId) params.set('task_type_id', taskTypeId);
    fetch(`${API}/api/v1/registre-activitat/?${params}`, { headers: authHeaders() })
      .then(r => r.json())
      .then(d => { setItems(d.results || []); setCount(d.count || 0); setTotals(d.totals || {}); })
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [period, tecnicId, taskTypeId, page]);

  useEffect(() => { setPage(1); }, [period, tecnicId, taskTypeId]);
  useEffect(() => { const id = setTimeout(load, 200); return () => clearTimeout(id); }, [load]);

  const thStyle = { padding:'8px 12px', fontSize: 'var(--fs-body)', color:'var(--text-muted)',
                    textTransform:'uppercase', letterSpacing:'0.04em',
                    borderBottom:'1px solid var(--border)', textAlign:'left', fontWeight:400 };
  const tdStyle = { padding:'10px 12px', fontSize: 'var(--fs-body)', color:'var(--text-main)',
                    borderBottom:'0.5px solid var(--border)' };

  return (
    <div style={{ padding:'24px', maxWidth:1240, margin:'0 auto',
                  fontFamily:'IBM Plex Mono, monospace' }}>
      {/* Header */}
      <div style={{ marginBottom:20 }}>
        <h1 style={{ fontSize: 'var(--fs-h1)', fontWeight:600, color:'var(--text-main)', margin:0 }}>
          {t('registre.title', "Registre d'activitat")}
        </h1>
        <span style={{ fontSize: 'var(--fs-body)', color:'var(--text-muted)' }}>
          {count} {t('registre.models', 'models')}
        </span>
      </div>

      {/* KPIs discrets */}
      <div style={{ display:'flex', gap:10, marginBottom:20, flexWrap:'wrap' }}>
        <MiniStat label={t('registre.kpi_models', 'Models')} value={totals.models ?? '—'} />
        <MiniStat label={t('registre.kpi_total', 'Temps total')} value={formatMinutes(totals.total_minutes)} />
        <MiniStat label={t('registre.kpi_avg_model', 'Mitjana/model')} value={formatMinutes(totals.avg_per_model)} />
        <MiniStat label={t('registre.kpi_avg_step', 'Mitjana/tasca')} value={formatMinutes(totals.avg_per_step)} />
      </div>

      {/* Filtres */}
      <div style={{ display:'flex', gap:10, marginBottom:16, flexWrap:'wrap', alignItems:'center' }}>
        {/* Navegador de mesos */}
        <div style={{ display:'flex', alignItems:'center', gap:4, border:'1px solid var(--border)',
                      borderRadius:6, background:'var(--bg-card)', padding:'2px' }}>
          <button onClick={() => setPeriod(prevMonth(period))}
            style={{ padding:'4px 8px', fontSize: 'var(--fs-body)', border:'none', background:'none',
                     cursor:'pointer', color:'var(--text-main)',
                     fontFamily:'IBM Plex Mono, monospace' }}>←</button>
          <span style={{ fontSize: 'var(--fs-body)', minWidth:120, textAlign:'center', color:'var(--text-main)' }}>
            {fmtPeriod(period)}
          </span>
          <button onClick={() => setPeriod(nextMonth(period))}
            style={{ padding:'4px 8px', fontSize: 'var(--fs-body)', border:'none', background:'none',
                     cursor:'pointer', color:'var(--text-main)',
                     fontFamily:'IBM Plex Mono, monospace' }}>→</button>
          {period && (
            <button onClick={() => setPeriod('')}
              style={{ padding:'4px 8px', fontSize: 'var(--fs-body)', border:'none', background:'none',
                       cursor:'pointer', color:'var(--text-muted)',
                       fontFamily:'IBM Plex Mono, monospace' }}>
              {t('registre.all_months', 'Tots')}
            </button>
          )}
        </div>

        <select value={tecnicId} onChange={e => setTecnicId(e.target.value)}
          style={{ padding:'6px 10px', fontSize: 'var(--fs-body)', border:'1px solid var(--border)',
                   borderRadius:6, fontFamily:'IBM Plex Mono, monospace',
                   background:'var(--bg-card)', color:'var(--text-main)' }}>
          <option value="">{t('registre.all_tecnics', 'Tots els tècnics')}</option>
          {tecnics.map(u => (
            <option key={u.id} value={u.id}>{u.nom_complet || u.username}</option>
          ))}
        </select>

        <select value={taskTypeId} onChange={e => setTaskTypeId(e.target.value)}
          style={{ padding:'6px 10px', fontSize: 'var(--fs-body)', border:'1px solid var(--border)',
                   borderRadius:6, fontFamily:'IBM Plex Mono, monospace',
                   background:'var(--bg-card)', color:'var(--text-main)' }}>
          <option value="">{t('registre.all_tasks', 'Totes les tasques')}</option>
          {taskTypeList.map(tt => (
            <option key={tt.id} value={tt.id}>{taskTypeLabel(t, tt.code, tt.name)}</option>
          ))}
        </select>

        {(period || tecnicId || taskTypeId) && (
          <button onClick={() => { setPeriod(''); setTecnicId(''); setTaskTypeId(''); }}
            style={{ padding:'6px 10px', fontSize: 'var(--fs-body)', border:'1px solid var(--border)',
                     borderRadius:6, background:'none', cursor:'pointer',
                     color:'var(--text-muted)', fontFamily:'IBM Plex Mono, monospace' }}>
            {t('registre.reset', 'Netejar')}
          </button>
        )}
      </div>

      {/* Taula */}
      {loading ? (
        <div style={{ color:'var(--text-muted)', fontSize: 'var(--fs-body)' }}>…</div>
      ) : (
        <table style={{ width:'100%', borderCollapse:'collapse' }}>
          <thead>
            <tr>
              {['registre.col_code','registre.col_name','registre.col_period',
                'registre.col_merited','registre.col_time','registre.col_steps'].map((k,i) => (
                <th key={i} style={thStyle}>{t(k, k)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map(row => (
              <tr key={row.id} onClick={() => navigate(`/models/${row.id}`)}
                style={{ cursor:'pointer' }}
                onMouseEnter={e => e.currentTarget.style.background='var(--bg-muted)'}
                onMouseLeave={e => e.currentTarget.style.background=''}>
                <td style={tdStyle}>
                  <span style={{ color:'var(--gold)', fontWeight:600 }}>{row.code}</span>
                </td>
                <td style={tdStyle}>{row.name || '—'}</td>
                <td style={tdStyle}>{row.period}</td>
                <td style={tdStyle}>{fmtDate(row.merited_at)}</td>
                <td style={tdStyle}>{formatMinutes(row.total_minutes)}</td>
                <td style={tdStyle}>{row.steps}</td>
              </tr>
            ))}
            {!items.length && (
              <tr><td colSpan={6} style={{ ...tdStyle, textAlign:'center',
                color:'var(--text-muted)' }}>
                {t('registre.empty', 'Cap model meritat amb aquests filtres.')}
              </td></tr>
            )}
          </tbody>
        </table>
      )}

      {/* Paginació */}
      {count > PAGE_SIZE && (
        <div style={{ display:'flex', gap:8, marginTop:16, justifyContent:'flex-end' }}>
          <button disabled={page===1} onClick={() => setPage(p => p-1)}
            style={{ padding:'4px 10px', fontSize: 'var(--fs-body)', border:'1px solid var(--border)',
                     borderRadius:6, cursor:'pointer', background:'var(--bg-card)',
                     fontFamily:'IBM Plex Mono, monospace' }}>←</button>
          <span style={{ fontSize: 'var(--fs-body)', color:'var(--text-muted)', padding:'4px 6px' }}>
            {page} / {Math.ceil(count/PAGE_SIZE)}
          </span>
          <button disabled={page>=Math.ceil(count/PAGE_SIZE)} onClick={() => setPage(p => p+1)}
            style={{ padding:'4px 10px', fontSize: 'var(--fs-body)', border:'1px solid var(--border)',
                     borderRadius:6, cursor:'pointer', background:'var(--bg-card)',
                     fontFamily:'IBM Plex Mono, monospace' }}>→</button>
        </div>
      )}
    </div>
  );
}
