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
 * Des de F4.1 la pantalla ARRIBA PRE-OMPLERTA quan el reconeixedor ha sabut dir alguna cosa
 * (`p.proposta`). La proposta NO és una identitat: viu en camps a part al servidor
 * (`proposed_*`), es pinta amb el badge taronja d'estat de dada —mai amb el verd— i no
 * queda desada fins que algú l'accepta. Un camp pre-omplert que ja fos verd seria una
 * confirmació que ningú no ha fet.
 *
 * 🚨 **El verd només el posa un humà, i el color el decideix el SERVIDOR.**
 * `proposta.is_confirmed` ve de la fila, no es dedueix aquí: el color d'un estat no
 * s'endevina a la vista. El verd de confirmat tampoc no viu al navegador — es deriva de
 * l'acta que serveix el servidor. Un estat de confirmació a `localStorage` diria que algú
 * va confirmar en AQUELL ordinador, que no és el que la pregunta vol saber.
 */
export default function PieceIdentityList({
  pieces, rols, acta, versioPatro, pecaSel, onTria, onDesa, onConfirma, onReconeix,
  desant, reconeixent, error,
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

  // Propostes que encara no ha acceptat ningú. El recompte NO inclou les peces que ja
  // tenen rol: una proposta sobre una peça ja identificada no demana res a ningú.
  const proposades = pieces.filter(p => !p.piece_role && p.proposta?.role)
  const mudes = pieces.filter(p => !p.piece_role && !p.proposta?.role && p.proposta?.at)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      <p style={{
        fontSize: 'var(--fs-caption)', color: 'var(--text-soft)', margin: 0,
      }}>
        {t('pattern.identity_hint')}
      </p>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem',
                    flexWrap: 'wrap' }}>
        <button
          onClick={onReconeix}
          disabled={reconeixent || desant}
          style={{
            cursor: reconeixent ? 'progress' : 'pointer',
            background: 'var(--panel)', color: 'var(--text-main)',
            border: '1px solid var(--line)', borderRadius: 'var(--r-ctrl)',
            padding: '0.35rem 0.7rem', fontSize: 'var(--fs-caption)',
            display: 'flex', alignItems: 'center', gap: '0.35rem',
          }}
        >
          <i className="ti ti-wand" aria-hidden="true" />
          {reconeixent ? t('pattern.recognize_running') : t('pattern.recognize')}
        </button>
        {/* El SILENCI es diu, no s'amaga. Que el reconeixedor hagi mirat cinc peces i no
            n'hagi sabut dir cap és informació: sense aquesta línia, «no ha sortit res»
            i «no s'ha executat» es veurien igual. */}
        {(proposades.length > 0 || mudes.length > 0) && (
          <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)' }}>
            {t('pattern.recognize_summary', {
              proposades: proposades.length, mudes: mudes.length,
            })}
          </span>
        )}
      </div>

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
              color: 'var(--text-soft)', fontSize: 'var(--fs-caption)',
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
          fontSize: 'var(--fs-caption)', color: 'var(--text-soft)', margin: 0,
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
        <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)', margin: 0 }}>
          {t('pattern.identity_confirmed_stale', { versio: acta.versio_patro })}
        </p>
      )}

      <button
        onClick={onConfirma}
        disabled={ambRol.length === 0 || desant}
        title={ambRol.length === 0 ? t('pattern.identity_confirm_none') : ''}
        style={{
          cursor: ambRol.length === 0 ? 'not-allowed' : 'pointer',
          background: ambRol.length === 0 ? 'var(--panel)' : 'var(--accio)',
          color: ambRol.length === 0 ? 'var(--text-soft)' : 'var(--white)',
          border: '1px solid var(--line)', borderRadius: 6,
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

/**
 * Una peça: nom, picker de rol, cara, costat i estat — i, si n'hi ha, LA PROPOSTA.
 *
 * La regla de color, en una frase: **verd = un humà ho ha confirmat · taronja = una
 * màquina ho ha proposat · res = ningú no ho ha dit encara.** El taronja és el badge
 * d'estat de dada que la norma ja té ratificat (`--warn-state` / `--warn-state-bg` /
 * `--warn-ink`, §1b(d) d'`index.css`): no s'hi inventa cap color nou, perquè un color nou
 * per a una idea que ja en té un serien dos idiomes visuals per al mateix.
 */
function Targeta({ p, rols, t, idioma, sel, confirmada, onTria, onDesa }) {
  const [nom, setNom] = useState(p.nom || '')
  const prop = p.proposta || {}
  // Hi ha proposta VIVA quan la màquina ha dit alguna cosa i ningú no l'ha confirmada
  // encara. Un cop hi ha `piece_role`, la proposta deixa de demanar res: es queda a la
  // fila per a l'auditoria d'encert, no per a la pantalla.
  const proposta = (!p.piece_role && prop.role) ? prop : null
  // El reconeixedor ha mirat i ha CALLAT. Val la pena dir-ho: un silenci explicat és una
  // dada, i un silenci mut es confon amb no haver-ho provat mai.
  const mut = !p.piece_role && !prop.role && prop.at

  const camp = {
    fontSize: 'var(--fs-caption)', padding: '0.15rem 0.3rem',
    border: '1px solid var(--line)', borderRadius: 4,
    background: 'var(--panel)', color: 'var(--text-main)',
  }

  return (
    <div
      onClick={() => onTria(sel ? '' : p.nom_block)}
      style={{
        cursor: 'pointer',
        // El verd de confirmat és el token de FTP-1: el mateix que ja marca «això ja té
        // lloc» a l'editor de fitxa. Dos verds diferents per a la mateixa idea serien dos
        // idiomes visuals.
        background: confirmada ? 'var(--placed-bg)' : 'var(--panel)',
        border: `1px solid ${sel ? 'var(--gold)' : 'var(--line)'}`,
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
          fontSize: 'var(--fs-caption)', color: 'var(--text-soft)', fontStyle: 'italic',
        }}>
          {nomDelRol(p, idioma)}
        </span>
      )}

      <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap' }}
           onClick={e => e.stopPropagation()}>
        <select
          // PRE-OMPLERT amb la proposta, però la BD segueix sense rol: el valor que es
          // veu i el que hi ha desat no són el mateix, i per això el camp va marcat.
          value={p.piece_role?.id || proposta?.role?.id || ''}
          onChange={e => onDesa(p.id, {
            piece_role_id: e.target.value ? Number(e.target.value) : null,
          })}
          style={{
            ...camp, flex: '1 1 8rem',
            ...(proposta ? {
              borderColor: 'var(--warn-state)',
              background: 'var(--warn-state-bg)',
              color: 'var(--warn-ink)',
            } : null),
          }}
          title={proposta ? t('pattern.proposal_field_t') : ''}
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

        {/* L'eix DAVANT/DARRERE (D1). Buit NO vol dir «no ho sabem»: vol dir que la peça
            no té cara, com una cinturilla al doblec. Mateixa forma que la lateralitat,
            que és l'eix germà. */}
        <select
          value={p.face || proposta?.face || ''}
          onChange={e => onDesa(p.id, { face: e.target.value })}
          style={{
            ...camp,
            ...(proposta && proposta.face && !p.face ? {
              borderColor: 'var(--warn-state)',
              background: 'var(--warn-state-bg)',
              color: 'var(--warn-ink)',
            } : null),
          }}
          aria-label={t('pattern.identity_face')}
        >
          <option value="">{t('pattern.identity_face_none')}</option>
          <option value="front">{t('pattern.identity_face_front')}</option>
          <option value="back">{t('pattern.identity_face_back')}</option>
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

        {proposta && (
          <XipProposta
            proposta={proposta} t={t} idioma={idioma}
            onAccepta={() => onDesa(p.id, {
              piece_role_id: proposta.role.id,
              ...(proposta.face ? { face: proposta.face } : null),
            })}
          />
        )}

        {mut && (
          <span
            title={prop.evidence?.silent_because || ''}
            style={{
              fontSize: 'var(--fs-caption)', color: 'var(--text-faint)',
              alignSelf: 'center', display: 'flex', alignItems: 'center', gap: '0.25rem',
            }}
          >
            <i className="ti ti-help-circle" aria-hidden="true" />
            {t('pattern.proposal_silent')}
          </span>
        )}

        {/* El xip de Material del fitxer, intacte: és evidència, no una tria. */}
        {p.metadata?.material && (
          <span style={{
            fontSize: 'var(--fs-caption)', color: 'var(--text-soft)',
            border: '1px solid var(--line)', borderRadius: 8, padding: '0 6px',
            alignSelf: 'center',
          }}>
            {p.metadata.material}
          </span>
        )}
      </div>
    </div>
  )
}

/**
 * El XIP D'EVIDÈNCIA: per què la màquina diu el que diu, en una línia llegible.
 *
 * 🚨 **Un score sense la seva raó és un número que ningú no pot discutir.** El patronista
 * no ha de creure's un 0,57; ha de poder veure «s'assembla a la MANGA del 837» i decidir.
 * Per això el xip diu la peça VEÏNA amb el seu nom de bloc, i no una probabilitat.
 *
 * El vocabulari de senyal segueix el de la casa: `+` el que hi juga a favor, `o` el que és
 * neutre, `⚠` el que va just. Aquí es tradueix a la forma que la targeta de propostes ja
 * parla — una píndola amb la seva icona, no una frase.
 */
function XipProposta({ proposta, t, idioma, onAccepta }) {
  const ev = proposta.evidence || {}
  const veí = (ev.nearest || [])[0]
  const suport = ev.context?.seam_templates_supporting || 0
  const cusAmb = ev.context?.sewn_with || []

  // Les tres peces d'evidència, en ordre de força. `N1` és un cas a part i s'ha de veure
  // com a tal: no és «s'assembla molt», és «és la mateixa peça», i el patronista que
  // reimporta un patró ha de poder-ho llegir d'un cop d'ull.
  const trossos = []
  if (ev.stage === 'N1') {
    trossos.push(t('pattern.proposal_ev_exact', { peca: veí?.nom_block || '' }))
  } else if (veí) {
    trossos.push(t('pattern.proposal_ev_near', { peca: veí.nom_block }))
  }
  if (suport > 0) {
    trossos.push(t('pattern.proposal_ev_sewn', {
      count: suport, amb: cusAmb.join(', '),
    }))
  }

  return (
    <span
      style={{
        display: 'flex', alignItems: 'center', gap: '0.35rem', alignSelf: 'center',
        fontSize: 'var(--fs-caption)',
        background: 'var(--warn-state-bg)', color: 'var(--warn-ink)',
        border: '1px solid var(--warn-state)', borderRadius: 'var(--r-pill)',
        padding: '1px 8px',
      }}
      title={t('pattern.proposal_chip_t', {
        score: (proposta.score ?? 0).toFixed(2),
        llindar: (ev.threshold ?? 0).toFixed(2),
        veins: ev.n_neighbours ?? 0,
      })}
    >
      <i className="ti ti-wand" aria-hidden="true" />
      {trossos.join(' · ') || t('pattern.proposal_ev_plain')}
      <button
        onClick={e => { e.stopPropagation(); onAccepta() }}
        title={t('pattern.proposal_accept_t')}
        style={{
          cursor: 'pointer', background: 'transparent', border: 'none', padding: 0,
          margin: 0, color: 'var(--warn-ink)', display: 'flex', alignItems: 'center',
          // Una icona sola sense alçada mínima mesura 0 mentre la webfont no ha
          // arribat: la caixa la posa el botó, no la lletra.
          minHeight: 16, minWidth: 16,
        }}
        aria-label={t('pattern.proposal_accept')}
      >
        <i className="ti ti-check" aria-hidden="true" />
      </button>
    </span>
  )
}
