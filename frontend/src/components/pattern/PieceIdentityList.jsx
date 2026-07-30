import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { etiquetaPeca, nomDelRol, nomOriginal } from './pieceText'

/**
 * IDENTITAT DE LES PECES (I2a) — dir què és cada peça, al tab Patró.
 *
 * Component propi i no un afegit a `PieceList` a posta: aquella llista la comparteixen el
 * tab i el Taller, i és un SELECTOR (clica una peça, mira-la al canvas). Posar-hi controls
 * d'edició els colaria a la columna del Taller, on la frontera del mòdul diu que hi van les
 * accions sobre el CONTINGUT i no sobre la fitxa.
 *
 * Tot MANUAL: aquí no hi ha cap proposta automàtica ni cap matcher. El que la pantalla sap
 * és el que una persona hi ha dit.
 *
 * El verd de confirmat NO viu al navegador: es deriva de l'acta que serveix el servidor. Un
 * estat de confirmació a `localStorage` diria que algú va confirmar en AQUELL ordinador, que
 * no és el que la pregunta vol saber — i un F5 en un altre lloc mentiria.
 */
export default function PieceIdentityList({
  pieces, rols, acta, versioPatro, pecaSel, onTria, onDesa, onConfirma, desant, error,
}) {
  const { t, i18n } = useTranslation()
  const [obertesTreball, setObertesTreball] = useState(false)

  // Els rols, agrupats per classe. El vocabulari per GTI encara no existeix com a dada
  // (`GarmentTypeItemPart` és composició d'item-CONJUNT, no peces de patró), així que el
  // catàleg va pla — agrupat, això sí, que trenta files seguides no es llegeixen.
  const perClasse = useMemo(() => {
    const grups = new Map()
    for (const r of rols) {
      if (!grups.has(r.classe)) grups.set(r.classe, [])
      grups.get(r.classe).push(r)
    }
    return [...grups.entries()]
  }, [rols])

  const produccio = pieces.filter(p => (p.estat_peca || 'produccio') === 'produccio')
  const treball = pieces.filter(p => (p.estat_peca || 'produccio') !== 'produccio')
  // TOTES les que tenen rol, no només les de producció: decidir que una peça és de
  // treball TAMBÉ és identificar-la, i l'acta la recull. Si el botó comptés només les de
  // producció, prometria un número i el verd en respondria un altre.
  const ambRol = pieces.filter(p => p.piece_role)

  // L'acta val per a la versió sobre la qual es va signar. Una versió nova del patró refà
  // les peces: el verd d'aleshores ja no parla d'aquestes.
  const actaVigent = acta && acta.versio_patro === versioPatro
  const confirmades = useMemo(
    () => new Set(actaVigent ? acta.snapshot.map(f => f.piece_id) : []),
    [actaVigent, acta],
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      <p style={{
        fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', margin: 0,
      }}>
        {t('pattern.identity_hint')}
      </p>

      {pieces.length > 0 && produccio.map(p => (
        <Targeta
          key={p.id} p={p} rols={perClasse} t={t} idioma={i18n.language}
          sel={p.nom_block === pecaSel} confirmada={confirmades.has(p.id)}
          onTria={onTria} onDesa={onDesa}
        />
      ))}

      {treball.length > 0 && (
        <div>
          <button
            onClick={() => setObertesTreball(v => !v)}
            style={{
              width: '100%', textAlign: 'left', cursor: 'pointer',
              background: 'transparent', border: 'none', padding: '0.4rem 0',
              color: 'var(--text-muted)', fontSize: 'var(--fs-caption)',
              display: 'flex', alignItems: 'center', gap: '0.3rem',
            }}
            aria-expanded={obertesTreball}
          >
            <i className={`ti ti-chevron-${obertesTreball ? 'down' : 'right'}`} />
            {t('pattern.identity_work_pieces', { count: treball.length })}
          </button>
          {obertesTreball && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {treball.map(p => (
                <Targeta
                  key={p.id} p={p} rols={perClasse} t={t} idioma={i18n.language}
                  sel={p.nom_block === pecaSel} confirmada={confirmades.has(p.id)}
                  onTria={onTria} onDesa={onDesa}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {error && (
        <p style={{ color: 'var(--error)', fontSize: 'var(--fs-caption)', margin: 0 }}>
          {error}
        </p>
      )}

      {actaVigent && (
        <p style={{
          fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', margin: 0,
          display: 'flex', alignItems: 'center', gap: '0.3rem',
        }}>
          <i className="ti ti-circle-check" style={{ color: 'var(--ok)' }} />
          {t('pattern.identity_confirmed', {
            data: new Date(acta.data).toLocaleDateString(i18n.language),
            count: acta.peces_confirmades,
          })}
        </p>
      )}
      {acta && !actaVigent && (
        <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', margin: 0 }}>
          {t('pattern.identity_confirmed_stale', { versio: acta.versio_patro })}
        </p>
      )}

      <button
        onClick={onConfirma}
        disabled={ambRol.length === 0 || desant}
        title={ambRol.length === 0 ? t('pattern.identity_confirm_none') : ''}
        style={{
          cursor: ambRol.length === 0 ? 'not-allowed' : 'pointer',
          background: ambRol.length === 0 ? 'var(--bg-card)' : 'var(--gold)',
          color: ambRol.length === 0 ? 'var(--text-muted)' : 'var(--white)',
          border: '1px solid var(--border)', borderRadius: 6,
          padding: '0.5rem 0.8rem', fontSize: 'var(--fs-body)',
        }}
      >
        {desant
          ? t('pattern.identity_saving')
          : t('pattern.identity_confirm', { count: ambRol.length })}
      </button>
    </div>
  )
}

/** Una peça: dues línies de nom, el picker de rol, el costat i l'estat. */
function Targeta({ p, rols, t, idioma, sel, confirmada, onTria, onDesa }) {
  const [nom, setNom] = useState(p.nom || '')

  const camp = {
    fontSize: 'var(--fs-caption)', padding: '0.15rem 0.3rem',
    border: '1px solid var(--border)', borderRadius: 4,
    background: 'var(--white)', color: 'var(--text)',
  }

  return (
    <div
      onClick={() => onTria(sel ? '' : p.nom_block)}
      style={{
        cursor: 'pointer',
        // El verd de confirmat és el token de FTP-1: el mateix que ja marca «això ja té
        // lloc» a l'editor de fitxa. Dos verds diferents per a la mateixa idea serien dos
        // idiomes visuals.
        background: confirmada ? 'var(--placed-bg)' : 'var(--bg-card)',
        border: `1px solid ${sel ? 'var(--gold)' : 'var(--border)'}`,
        borderRadius: 6, padding: '0.5rem 0.7rem',
        display: 'flex', flexDirection: 'column', gap: '0.35rem',
      }}
    >
      {/* L1 — el bateig del model. Buit: el nom que el fitxer portava, com a placeholder. */}
      <input
        value={nom}
        placeholder={etiquetaPeca(p)}
        title={nomOriginal(p) ? t('pattern.identity_block_orig', { nom: p.nom_block }) : ''}
        onClick={e => e.stopPropagation()}
        onChange={e => setNom(e.target.value)}
        onBlur={() => { if (nom !== (p.nom || '')) onDesa(p.id, { nom }) }}
        style={{ ...camp, fontSize: 'var(--fs-body)', fontWeight: 600 }}
      />

      {/* L2 — el rol, gris i cursiva. Si no en té, la línia no hi és. */}
      {nomDelRol(p, idioma) && (
        <span style={{
          fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', fontStyle: 'italic',
        }}>
          {nomDelRol(p, idioma)}
        </span>
      )}

      <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap' }}
           onClick={e => e.stopPropagation()}>
        <select
          value={p.piece_role?.id || ''}
          onChange={e => onDesa(p.id, {
            piece_role_id: e.target.value ? Number(e.target.value) : null,
          })}
          style={{ ...camp, flex: '1 1 8rem' }}
          aria-label={t('pattern.identity_role')}
        >
          <option value="">{t('pattern.identity_role_none')}</option>
          {rols.map(([classe, llista]) => (
            <optgroup key={classe} label={classe}>
              {llista.map(r => (
                <option key={r.id} value={r.id}>
                  {r[`nom_${idioma}`] || r.nom_ca || r.nom_en}
                </option>
              ))}
            </optgroup>
          ))}
        </select>

        <select
          value={p.lateralitat || ''}
          onChange={e => onDesa(p.id, { lateralitat: e.target.value })}
          style={camp} aria-label={t('pattern.identity_side')}
        >
          <option value="">{t('pattern.identity_side_none')}</option>
          <option value="L" title={t('pattern.identity_side_left_t')}>
            {t('pattern.identity_side_left')}
          </option>
          <option value="R" title={t('pattern.identity_side_right_t')}>
            {t('pattern.identity_side_right')}
          </option>
        </select>

        <select
          value={p.estat_peca || 'produccio'}
          onChange={e => onDesa(p.id, { estat_peca: e.target.value })}
          style={camp} aria-label={t('pattern.identity_state')}
        >
          {['produccio', 'treball', 'referencia', 'plantilla'].map(e => (
            <option key={e} value={e}>{t(`pattern.identity_state_${e}`)}</option>
          ))}
        </select>

        {/* El xip de Material del fitxer, intacte: és evidència, no una tria. */}
        {p.metadata?.material && (
          <span style={{
            fontSize: 'var(--fs-caption)', color: 'var(--text-muted)',
            border: '1px solid var(--border)', borderRadius: 8, padding: '0 6px',
            alignSelf: 'center',
          }}>
            {p.metadata.material}
          </span>
        )}
      </div>
    </div>
  )
}
