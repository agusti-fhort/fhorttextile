import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import DartProposalsPanel from './DartProposalsPanel'
import ProposalsPanel from './ProposalsPanel'
import { nomCostura, textAritmetica, textCobertura, textEstat } from './sewText'
import { formatLen, titleLen } from '../../utils/format'
import { AccionsGrup, Casella, Informe, useSeleccio } from './seleccio'
import Modal from '../ui/Modal'

/**
 * RELACIONS — el que s'ha declarat sobre el patró, editable.
 *
 * Quatre famílies: POMs ancorats · Costures · PINCES · Trams declarats. Els missatges es
 * construeixen AQUÍ a partir de les xifres del servidor, no es mostren els del servidor: el
 * backend els escriu en català pla (no són claus i18n) i el gate demana ca/en/es. La frase del
 * servidor es conserva com a `title` — hi ha matís que val la pena poder llegir sencer.
 *
 * **Aquí és d'on es REOBRE** (W4b/T5). Les tres entitats es corregeixen amb el mateix gest amb
 * què es van crear, al canvas, i sobre la MATEIXA fila: un POM reobert es recalcula, no es
 * torna a ancorar; un tram es recol·loca, no s'esborra i es refà. La diferència no és de
 * matís: les costures referencien els trams, i refer-los les buidaria en silenci.
 *
 * **I d'aquí és d'on s'esborra en BLOC** (QA-TALLER E · T3). Cada grup porta la seva pròpia
 * selecció, la seva pròpia paperera i el seu propi informe: v. `seleccio.jsx` per què la
 * selecció no travessa mai els blocs.
 */
export default function RelationsPanel({
  poms, sews, pinces, segments, tramsPerId, unit = 'CM',
  propostes = [], descartatsProp = null,
  onConfirmaProposta, onRebutjaProposta, onRessaltaProposta,
  pincesProposades = [], descartatsPinca = null,
  onConfirmaPinca, onRebutjaPinca, onRessaltaPinca,
  onEsborraPom, onReobrePom,
  onEsborraSew, onReobreSew, onReanomenaSew,
  onEsborraPinca, onReanomenaPinca,
  onReanomenaTram, onReobreTram, onEsborraTram,
  onEsborraBlocProposta, onEsborraBlocPom, onEsborraBlocSew,
  onEsborraBlocPinca, onEsborraBlocTram,
}) {
  const { t } = useTranslation()

  // Una selecció per grup. Cinc `useSeleccio` i no un de sol amb cinc claus: el que fa que no
  // hi pugui haver mai un «esborra-ho tot» no és una comprovació, és que l'estat no existeix.
  const selProp = useSeleccio(propostes.map(p => p.clau.join('-')))
  const selPom = useSeleccio(poms.map(p => p.id))
  const selSew = useSeleccio(sews.map(s => s.id))
  const selPinca = useSeleccio(pinces.map(p => p.id))
  const selTram = useSeleccio(segments.map(s => s.id))

  const [confirma, setConfirma] = useState(null)
  const [informes, setInformes] = useState({})

  /**
   * Res cau sense passar per aquí: es demana la confirmació, i només el «sí» executa.
   *
   * L'informe es desa PER MENA i la selecció es buida només quan l'esborrat ha anat: si
   * rebota, el que s'havia marcat continua marcat i es pot tornar a provar sense refer la
   * tria.
   */
  const demana = (mena, ids, fn, seleccio) => setConfirma({
    mena,
    count: ids.length,
    executa: async () => {
      const informe = await fn(ids)
      setInformes(i => ({ ...i, [mena]: informe?.retinguts || [] }))
      seleccio.buida()
    },
  })

  const tanca = mena => setInformes(i => ({ ...i, [mena]: [] }))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
      {/* LES PROPOSTES, a dalt de tot (A2). Van les primeres perquè són la feina que QUEDA per
          decidir; el que hi ha a sota ja està decidit. I van DINS de Relacions, no en un tab
          a part: proposar i declarar són el mateix ofici, i separar-los faria que la llista
          d'assistència fos una pantalla on s'ha d'anar en comptes d'una que ja s'està mirant. */}
      <Seccio
        titol={t('pattern.taller.proposals', { n: propostes.length })}
        accions={
          <AccionsGrup
            t={t} n={selProp.sel.size} total={propostes.length}
            onTots={selProp.tots}
            onEsborra={() => demana(
              'proposals',
              propostes.filter(p => selProp.sel.has(p.clau.join('-'))),
              onEsborraBlocProposta,
              selProp,
            )}
          />
        }
      >
        <Informe t={t} retinguts={informes.proposals} onTanca={() => tanca('proposals')} />
        <ProposalsPanel
          propostes={propostes} descartats={descartatsProp} unit={unit}
          sel={selProp.sel} onAlterna={selProp.alterna}
          onConfirma={onConfirmaProposta}
          onRebutja={onRebutjaProposta}
          onRessalta={onRessaltaProposta}
        />
      </Seccio>

      {/* LES PINCES PROPOSADES (A1), just sota les costures proposades: les dues llistes són la
          mateixa feina —el que el motor veu i encara ningú no ha decidit— i separar-les en dos
          llocs hauria fet que l'assistència visqués a mitges. */}
      <Seccio titol={t('pattern.taller.darts_proposed', { n: pincesProposades.length })}>
        <DartProposalsPanel
          candidats={pincesProposades} descartats={descartatsPinca} unit={unit}
          onConfirma={onConfirmaPinca}
          onRebutja={onRebutjaPinca}
          onRessalta={onRessaltaPinca}
        />
      </Seccio>

      <Seccio
        titol={t('pattern.poms_anchored', { n: poms.length })}
        accions={
          <AccionsGrup
            t={t} n={selPom.sel.size} total={poms.length}
            onTots={selPom.tots}
            onEsborra={() => demana(
              'poms', [...selPom.sel], onEsborraBlocPom, selPom)}
          />
        }
      >
        <Informe t={t} retinguts={informes.poms} onTanca={() => tanca('poms')} />
        {poms.length === 0 ? (
          <Buit text={t('pattern.poms_empty')} />
        ) : poms.map(p => (
          <Fila key={p.id}>
            <Casella
              marcat={selPom.sel.has(p.id)}
              onChange={() => selPom.alterna(p.id)}
              etiqueta={t('pattern.taller.bulk_select_row')}
            />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                fontSize: 'var(--fs-body)', fontWeight: 600, fontFamily: 'var(--mono)',
              }}>
                {p.pom_code}
              </div>
              <div style={{
                fontSize: 'var(--fs-caption)', color: 'var(--text-muted)',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>
                {p.pom_nom} · {p.peca}
              </div>
            </div>
            {/* La DADA no s'arrodoneix mai: el `title` porta el valor complet (T7c). */}
            <span
              title={titleLen(p.valor_mesurat_cm)}
              style={{
                fontFamily: 'var(--mono)', fontSize: 'var(--fs-body)',
                color: p.valor_mesurat_cm == null ? 'var(--err)' : 'var(--text-main)',
              }}
            >
              {p.valor_mesurat_cm != null
                ? formatLen(p.valor_mesurat_cm, unit)
                : t('pattern.pom_unmeasured')}
            </span>
            <BotoIcona
              icona="ti-pencil" etiqueta={t('pattern.taller.reopen')}
              onClick={() => onReobrePom(p)}
            />
            <BotoEsborra onClick={() => onEsborraPom(p.id)} etiqueta={t('app.delete')} />
          </Fila>
        ))}
      </Seccio>

      <Seccio
        titol={t('pattern.sews', { n: sews.length })}
        accions={
          <AccionsGrup
            t={t} n={selSew.sel.size} total={sews.length}
            onTots={selSew.tots}
            onEsborra={() => demana('sews', [...selSew.sel], onEsborraBlocSew, selSew)}
          />
        }
      >
        <Informe t={t} retinguts={informes.sews} onTanca={() => tanca('sews')} />
        {sews.length === 0 ? (
          <Buit text={t('pattern.sews_empty')} />
        ) : sews.map(s => (
          <Costura
            key={s.id} t={t} sew={s} unit={unit} tramsPerId={tramsPerId}
            marcat={selSew.sel.has(s.id)}
            onMarca={() => selSew.alterna(s.id)}
            onReobre={() => onReobreSew(s)}
            onReanomena={onReanomenaSew}
            onEsborra={() => onEsborraSew(s.id)}
          />
        ))}
      </Seccio>

      {/* Les PINCES a part (W4b): una pinça NO és una costura més. És el forat que explica per
          què una vora fa 32 cm i només n'aporta 30 a la costura, i barrejar-la amb les costures
          amagaria justament això. */}
      <Seccio
        titol={t('pattern.taller.pinces', { n: pinces.length })}
        accions={
          <AccionsGrup
            t={t} n={selPinca.sel.size} total={pinces.length}
            onTots={selPinca.tots}
            onEsborra={() => demana('pinces', [...selPinca.sel], onEsborraBlocPinca, selPinca)}
          />
        }
      >
        <Informe t={t} retinguts={informes.pinces} onTanca={() => tanca('pinces')} />
        {pinces.length === 0 ? (
          <Buit text={t('pattern.taller.pinces_empty')} />
        ) : pinces.map(p => (
          <Pinca
            key={p.id} t={t} pinca={p} unit={unit}
            marcat={selPinca.sel.has(p.id)}
            onMarca={() => selPinca.alterna(p.id)}
            onReanomena={onReanomenaPinca}
            onEsborra={() => onEsborraPinca(p.id)}
          />
        ))}
      </Seccio>

      <Seccio
        titol={t('pattern.taller.segments', { n: segments.length })}
        accions={
          <AccionsGrup
            t={t} n={selTram.sel.size} total={segments.length}
            onTots={selTram.tots}
            onEsborra={() => demana('segments', [...selTram.sel], onEsborraBlocTram, selTram)}
          />
        }
      >
        <Informe t={t} retinguts={informes.segments} onTanca={() => tanca('segments')} />
        {segments.length === 0 ? (
          <Buit text={t('pattern.taller.segments_empty')} />
        ) : segments.map(s => (
          <Tram
            key={s.id} t={t} tram={s} unit={unit}
            marcat={selTram.sel.has(s.id)}
            onMarca={() => selTram.alterna(s.id)}
            onReanomena={onReanomenaTram} onReobre={onReobreTram} onEsborra={onEsborraTram}
          />
        ))}
      </Seccio>

      {/* La CONFIRMACIÓ. Un esborrat en bloc és el gest que més pot destruir d'un sol clic, i
          el diàleg diu el compte i la MENA: «Esborrar 18 trams declarats?». Sense la mena, qui
          té cinc grups a la columna ha de recordar quina paperera ha clicat. */}
      {confirma && (
        <Modal
          title={t('pattern.taller.bulk_confirm_title', {
            count: confirma.count,
            mena: t(`pattern.taller.bulk_kind_${confirma.mena}`, { count: confirma.count }),
          })}
          subtitle={t('pattern.taller.bulk_confirm_body')}
          confirmLabel={t('pattern.taller.bulk_delete', { count: confirma.count })}
          cancelLabel={t('app.cancel')}
          onCancel={() => setConfirma(null)}
          onConfirm={() => {
            const executa = confirma.executa
            setConfirma(null)
            executa()
          }}
        />
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────

function Costura({ t, sew, unit, tramsPerId, marcat, onMarca, onReobre, onReanomena, onEsborra }) {
  const e = sew.estat || {}
  const cobertura = e.cobertura || []
  const [editantNom, setEditantNom] = useState(false)
  const [nom, setNom] = useState(sew.nom || '')

  // El nom GENERAT dels dos trams («Lateral ⛓ Esquena · Frunzit 2,0 cm») si ningú l'ha
  // batejada. No es desa: es refà cada cop, amb els noms que els trams tenen ARA.
  const titol = nomCostura(t, sew, tramsPerId, unit)

  const desa = async () => {
    setEditantNom(false)
    if ((nom || '') !== (sew.nom || '')) await onReanomena(sew.id, nom)
  }

  return (
    <div style={{
      border: `1px solid ${e.casa ? 'var(--ok)' : 'var(--err)'}`,
      background: e.casa ? 'var(--ok-bg)' : 'var(--err-bg)',
      borderRadius: 4, padding: '0.35rem 0.5rem',
      display: 'flex', flexDirection: 'column', gap: 4,
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.4rem' }}>
        <Casella
          marcat={marcat} onChange={onMarca}
          etiqueta={t('pattern.taller.bulk_select_row')}
        />
        <i className={`ti ${e.casa ? 'ti-check' : 'ti-alert-triangle'}`}
           style={{ color: e.casa ? 'var(--ok)' : 'var(--err)', marginTop: 2 }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          {editantNom ? (
            <input
              autoFocus
              value={nom}
              onChange={ev => setNom(ev.target.value)}
              onBlur={desa}
              onKeyDown={ev => {
                if (ev.key === 'Enter') desa()
                if (ev.key === 'Escape') { setNom(sew.nom || ''); setEditantNom(false) }
              }}
              placeholder={t('pattern.taller.sew_name_auto')}
              aria-label={t('pattern.taller.sew_name')}
              style={{
                width: '100%', fontSize: 'var(--fs-body)', padding: '0.1rem 0.3rem',
                border: '1px solid var(--gold)', borderRadius: 4,
              }}
            />
          ) : (
            <button
              onClick={() => setEditantNom(true)}
              title={t('pattern.taller.sew_name')}
              style={{
                background: 'none', border: 'none', padding: 0, cursor: 'text',
                textAlign: 'left', width: '100%',
                fontSize: 'var(--fs-body)', fontWeight: 600, color: 'var(--text-main)',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}
            >
              {titol}
            </button>
          )}
          {/* Les XIFRES, no l'adjectiu: "no casa" sense dir per quant no és diagnosticable.
              I amb pinces, l'ARITMÈTICA sencera: 32,1 − 2,3 (Pinça 1) = 29,8. */}
          <div
            title={e.missatge || undefined}
            style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-main)',
                     fontFamily: 'var(--mono)' }}
          >
            {textEstat(t, e, unit)}
          </div>
        </div>
        <BotoIcona
          icona="ti-pencil" etiqueta={t('pattern.taller.reopen')} onClick={onReobre}
        />
        <BotoEsborra onClick={onEsborra} etiqueta={t('app.delete')} />
      </div>

      {/* Cobertura (W1): la costura pot casar i la VORA estar malament igualment —
          dos trams que es trepitgen, o més centímetres cosits dels que la vora té. */}
      {cobertura.map((a, n) => (
        <div
          key={n}
          title={a.missatge || undefined}
          style={{
            display: 'flex', alignItems: 'flex-start', gap: '0.35rem',
            fontSize: 'var(--fs-caption)', color: 'var(--warn)',
            background: 'var(--warn-bg)', borderRadius: 4, padding: '3px 6px',
          }}
        >
          <i className="ti ti-alert-triangle" style={{ marginTop: 2 }} />
          <span>{textCobertura(t, a, unit)}</span>
        </div>
      ))}
    </div>
  )
}

/**
 * Una PINÇA: els seus dos costats, i la tela que es menja.
 *
 * El número que importa és la SUMA dels dos costats, perquè és el que després apareixerà
 * restat a la costura que la conté. Es diu aquí perquè, quan algú vegi «− 2,3 (Pinça 1)» a la
 * costura lateral, pugui venir a comprovar d'on surt aquell 2,3.
 */
function Pinca({ t, pinca, unit, marcat, onMarca, onReanomena, onEsborra }) {
  const [editant, setEditant] = useState(false)
  const [nom, setNom] = useState(pinca.sew?.nom || '')
  const e = pinca.estat || {}

  const desa = async () => {
    setEditant(false)
    if ((nom || '') !== (pinca.sew?.nom || '')) await onReanomena(pinca.id, nom)
  }

  return (
    <div style={{
      border: '1px solid var(--border)', borderRadius: 4,
      padding: '0.3rem 0.5rem', background: 'var(--bg-card)',
      display: 'flex', flexDirection: 'column', gap: 3,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <Casella
          marcat={marcat} onChange={onMarca}
          etiqueta={t('pattern.taller.bulk_select_row')}
        />
        <i className="ti ti-triangle" style={{ color: 'var(--gold)', flexShrink: 0 }} />

        <div style={{ flex: 1, minWidth: 0 }}>
          {editant ? (
            <input
              autoFocus
              value={nom}
              onChange={ev => setNom(ev.target.value)}
              onBlur={desa}
              onKeyDown={ev => {
                if (ev.key === 'Enter') desa()
                if (ev.key === 'Escape') { setNom(pinca.sew?.nom || ''); setEditant(false) }
              }}
              aria-label={t('pattern.taller.segment_rename')}
              style={{
                width: '100%', fontSize: 'var(--fs-body)', padding: '0.1rem 0.3rem',
                border: '1px solid var(--gold)', borderRadius: 4,
              }}
            />
          ) : (
            <button
              onClick={() => setEditant(true)}
              title={t('pattern.taller.segment_rename')}
              style={{
                background: 'none', border: 'none', padding: 0, cursor: 'text',
                textAlign: 'left', width: '100%',
                fontSize: 'var(--fs-body)', fontWeight: 600, color: 'var(--text-main)',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}
            >
              {pinca.nom}
            </button>
          )}
          <div style={{
            fontSize: 'var(--fs-caption)', color: 'var(--text-muted)',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {/* Els dos costats, amb la seva longitud. Si no fan el mateix, la pinça no es pot
                cosir plana — i el motor ho diu al veredicte, aquí sota. */}
            {pinca.legs.map(l => formatLen(l.longitud_cm, unit)).join(' + ')}
          </div>
        </div>

        {/* La TELA QUE ES MENJA: el número que la costura mostrarà restat. */}
        <span
          title={e.missatge || undefined}
          style={{
            fontFamily: 'var(--mono)', fontSize: 'var(--fs-body)', fontWeight: 600,
            color: 'var(--gold)', flexShrink: 0,
          }}
        >
          −{formatLen(pinca.cm, unit)}
        </span>
        <BotoEsborra onClick={onEsborra} etiqueta={t('app.delete')} />
      </div>

      {/* Els dos costats d'una pinça s'han de poder cosir l'un contra l'altre: si no fan el
          mateix, la pinça no tanca plana. No bloqueja res —el patró és del patronista— però
          es diu, amb la xifra. */}
      {e.casa === false && (
        <div style={{
          display: 'flex', alignItems: 'flex-start', gap: '0.35rem',
          fontSize: 'var(--fs-caption)', color: 'var(--warn)',
          background: 'var(--warn-bg)', borderRadius: 4, padding: '3px 6px',
        }}>
          <i className="ti ti-alert-triangle" style={{ marginTop: 2 }} />
          <span>
            {t('pattern.taller.pinca_uneven', {
              a: textAritmetica(e, 'a', unit), b: textAritmetica(e, 'b', unit),
              desv: formatLen(e.desviament_cm, unit),
            })}
          </span>
        </div>
      )}
    </div>
  )
}

function Tram({ t, tram, unit, marcat, onMarca, onReanomena, onReobre, onEsborra }) {
  const [editant, setEditant] = useState(false)
  const [nom, setNom] = useState(tram.nom || '')
  const [rebuig, setRebuig] = useState(null)   // per què no s'ha pogut esborrar

  const desa = async () => {
    setEditant(false)
    if ((nom || '') !== (tram.nom || '')) await onReanomena(tram.id, nom)
  }

  const esborra = async () => {
    setRebuig(null)
    const r = await onEsborra(tram.id)
    // 409: el tram el reté una costura. El motiu es diu SENCER (quantes i quines), perquè
    // qui el vulgui esborrar sàpiga exactament què ha de desfer primer.
    if (r && !r.ok) {
      setRebuig(t('pattern.taller.segment_in_use', {
        n: r.sews.length, ids: r.sews.map(x => `#${x}`).join(', '),
      }))
    }
  }

  return (
    <div style={{
      border: '1px solid var(--border)', borderRadius: 4,
      padding: '0.3rem 0.5rem', background: 'var(--bg-card)',
      display: 'flex', flexDirection: 'column', gap: 3,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <Casella
          marcat={marcat} onChange={onMarca}
          etiqueta={t('pattern.taller.bulk_select_row')}
        />
        <i className="ti ti-line" style={{ color: 'var(--gold)', flexShrink: 0 }} />

        <div style={{ flex: 1, minWidth: 0 }}>
          {editant ? (
            <input
              autoFocus
              value={nom}
              onChange={e => setNom(e.target.value)}
              onBlur={desa}
              onKeyDown={e => {
                if (e.key === 'Enter') desa()
                if (e.key === 'Escape') { setNom(tram.nom || ''); setEditant(false) }
              }}
              aria-label={t('pattern.taller.segment_rename')}
              style={{
                width: '100%', fontSize: 'var(--fs-body)', padding: '0.1rem 0.3rem',
                border: '1px solid var(--gold)', borderRadius: 4,
              }}
            />
          ) : (
            <button
              onClick={() => setEditant(true)}
              title={t('pattern.taller.segment_rename')}
              style={{
                background: 'none', border: 'none', padding: 0, cursor: 'text',
                textAlign: 'left', width: '100%',
                fontSize: 'var(--fs-body)', fontWeight: 600, color: 'var(--text-main)',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}
            >
              {tram.nom || t('pattern.taller.segment_unnamed')}
            </button>
          )}
          <div style={{
            fontSize: 'var(--fs-caption)', color: 'var(--text-muted)',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {tram.peca} · {t('pattern.taller.segment_edge', { vora: tram.vora })}
          </div>
        </div>

        {/* La DADA, a la MATEIXA escala que la d'un POM (QA-TALLER E · T2): un tram de 29,8 cm i
            un POM de 29,8 cm són la mateixa mena de xifra —una longitud llegida del patró— i
            anaven a mides diferents (caption vs body). La mida d'un número és una afirmació
            sobre quant importa; dir-ho diferent a cada bloc és dir-ho malament en un dels dos.
            El `title` porta el valor sense arrodonir (T7c). */}
        <span
          title={titleLen(tram.longitud_cm)}
          style={{
            fontFamily: 'var(--mono)', fontSize: 'var(--fs-body)',
            color: 'var(--text-main)', flexShrink: 0,
          }}
        >
          {formatLen(tram.longitud_cm, unit)}
        </span>

        {/* Un tram EN ÚS no s'esborra —el botó ho diu abans de clicar-lo—, però SÍ que es
            RECOL·LOCA (T5b): el PROTECT és per a esborrar, no per a corregir. */}
        {tram.en_us && (
          <i
            className="ti ti-needle-thread"
            title={t('pattern.taller.segment_used')}
            style={{ color: 'var(--text-muted)', flexShrink: 0 }}
          />
        )}
        <BotoIcona
          icona="ti-arrows-move" etiqueta={t('pattern.taller.relocate')}
          onClick={() => onReobre(tram)}
        />
        <BotoEsborra onClick={esborra} etiqueta={t('app.delete')} />
      </div>

      {rebuig && (
        <div style={{
          display: 'flex', alignItems: 'flex-start', gap: '0.35rem',
          fontSize: 'var(--fs-caption)', color: 'var(--err)',
          background: 'var(--err-bg)', borderRadius: 4, padding: '3px 6px',
        }}>
          <i className="ti ti-alert-triangle" style={{ marginTop: 2 }} />
          <span>{rebuig}</span>
        </div>
      )}
    </div>
  )
}

/**
 * La capçalera d'un sub-bloc de Relacions.
 *
 * Va en FOSC (QA-TALLER E · T1), com el contenidor de la columna: cinc famílies seguides, cada
 * una amb les seves files, i el títol en gris clar es llegia com una fila més. El que separa un
 * bloc del següent no pot pesar menys que el que hi ha a dins.
 *
 * Que sigui INSET (amb marge i cantonada) i no a sang és el que la diferencia de la capçalera
 * del contenidor que la conté: mateix color, jerarquia diferent.
 */
function Seccio({ titol, accions, children }) {
  return (
    <div>
      <div style={{
        display: 'flex', alignItems: 'center', gap: '0.4rem',
        background: 'var(--charcoal)', color: 'var(--white)',
        borderRadius: 4, padding: '0.25rem 0.5rem', margin: '0 0 0.35rem',
      }}>
        <h4 style={{
          flex: 1, minWidth: 0, margin: 0,
          fontSize: 'var(--fs-label)', textTransform: 'uppercase', letterSpacing: '0.03em',
          fontWeight: 600, color: 'var(--white)',
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {titol}
        </h4>
        {accions}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        {children}
      </div>
    </div>
  )
}

function Fila({ children }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '0.5rem',
      border: '1px solid var(--border)', borderRadius: 4,
      padding: '0.3rem 0.5rem', background: 'var(--bg-card)',
    }}>
      {children}
    </div>
  )
}

function Buit({ text }) {
  return (
    <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', margin: 0 }}>
      {text}
    </p>
  )
}

function BotoIcona({ icona, etiqueta, onClick }) {
  return (
    <button
      onClick={onClick}
      aria-label={etiqueta}
      title={etiqueta}
      style={{
        background: 'none', border: 'none', cursor: 'pointer',
        color: 'var(--text-muted)', flexShrink: 0, padding: 2,
      }}
    >
      <i className={`ti ${icona}`} />
    </button>
  )
}

function BotoEsborra({ onClick, etiqueta }) {
  return (
    <button
      onClick={onClick}
      aria-label={etiqueta}
      style={{
        background: 'none', border: 'none', cursor: 'pointer',
        color: 'var(--text-muted)', flexShrink: 0, padding: 2,
      }}
    >
      <i className="ti ti-trash" />
    </button>
  )
}
