import { useTranslation } from 'react-i18next'
import { IconChevronDown, IconChevronRight, IconChevronUp } from '@tabler/icons-react'
import { BUIDA, DECIDIDA, MESURANT, SENSE_PRESA, estatDeLaPresa } from '../../utils/estatPresa'
import { botoPorta } from '../ui/buttons'

// E1/B3 — LA BARRA D'ESTAT DE LA PRESA (R5).
//
// El flux d'E1 és PAUSABLE i ASÍNCRON entre persones: al taller es mesuren les peces a mesura
// que arriben, i al despatx algú decideix a la talla base, potser un altre dia. Qui obre
// l'Escalat ha de poder saber sense preguntar a ningú **de quina presa parla, què s'hi ha fet
// i què hi falta** — i tenir a mà el pas següent.
//
// ── LA FORMA, SEGONS NORMA_LAYOUT ───────────────────────────────────────────────────────────
// §5.3 — «Decidir a la talla base» és una **PORTA**, no una primària: porta a una ALTRA
// superfície («Mesurar prenda», al tab Mesures) i no completa la feina d'aquí. Per tant estil
// SECUNDARI amb vora daurada + chevron de destí, mai blau. Amb això la pantalla es queda sense
// cap blau, que és correcte: a l'Escalat la feina es fa TECLEJANT a les cel·les, no prement
// res, i inventar-hi una primària seria posar un blau que no completa res.
// §1 — els recomptes van en BADGES: fons suau + tinta del color + vora fina del mateix color,
// píndola. Mai fons ple.
//
// 🚩 PROPOSTA DE FORMA, decisió visual final d'Agus (Patró C): aquí s'implementa **porta
// prominent a la barra d'estat**. L'alternativa censada és un **sub-tab** dins d'Escalat
// («Presa | Decisió»), que NORMA §5.3 admet per a «seccions germanes». S'ha triat la porta
// perquè la decisió NO és una secció germana de l'Escalat: viu al tab Mesures, té tasca
// pròpia (`size_check`) i rellotge propi, i un sub-tab ho amagaria. Si Agus prefereix el
// sub-tab, el canvi és d'aquest fitxer i de la ruta del `onDecidir`.

const MONO = 'IBM Plex Mono, monospace'

/** §1 — badge: fons suau + tinta del color + vora fina del MATEIX color. Píndola sempre. */
function Badge({ to = 'neutre', children }) {
  const crom = {
    ok: { bg: 'var(--ok-bg)', ink: 'var(--ok)', line: 'var(--ok)' },
    warn: { bg: 'var(--warn-state-bg)', ink: 'var(--warn-ink)', line: 'var(--warn-state)' },
    neutre: { bg: 'var(--panel)', ink: 'var(--text-soft)', line: 'var(--line)' },
  }[to]
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', borderRadius: 999,
                   padding: '2px 10px', fontFamily: MONO, fontSize: 'var(--fs-caption)',
                   background: crom.bg, color: crom.ink, border: `1px solid ${crom.line}` }}>
      {children}
    </span>
  )
}

/**
 * @param {{presa: object|null, readOnly?: boolean, decisioOberta?: boolean,
 *          onDecidir: () => void, onObrir: () => void}} props
 */
export default function BarraPresaEscalat({ presa, readOnly = false, decisioOberta = false,
                                            onDecidir, onObrir }) {
  const { t } = useTranslation()
  const e = estatDeLaPresa(presa)
  const dia = e.session?.data
    ? new Date(e.session.data).toLocaleDateString('ca-ES', { day: '2-digit', month: '2-digit' })
    : null

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
                  padding: 16, marginBottom: 16, borderRadius: 12,
                  border: '1px solid var(--line)', background: 'var(--panel)' }}>
      <span style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-main)' }}>
        {e.estat === SENSE_PRESA
          ? t('escalat.presa_sense')
          : t('escalat.presa_del', { data: dia || '—' })}
      </span>

      {e.estat !== SENSE_PRESA && (
        <>
          {/* QUANTES, i sobre quantes: un «3 mesurades» sol no diu si en falten dues o dues-centes. */}
          <Badge to={e.n_preses ? 'ok' : 'neutre'}>
            {t('escalat.presa_comptador', { n: e.n_preses, total: e.n_linies })}
          </Badge>
          {/* DE QUINES TALLES: és el que qui reprèn la feina vol saber primer (quines peces han
              arribat), i no es dedueix del recompte. */}
          {e.talles.length > 0 && (
            <Badge>{t('escalat.presa_talles', { talles: e.talles.join(' · ') })}</Badge>
          )}
          {/* QUÈ FALTA. El buit NO és una decisió: mentre quedi una base sense veredicte, la
              feina no està tancada, i amb dues prendes n'hi ha dues. */}
          {e.pendents_base > 0
            ? <Badge to="warn">{t('escalat.presa_pendents', { n: e.pendents_base })}</Badge>
            : e.n_preses > 0 && <Badge to="ok">{t('escalat.presa_decidida')}</Badge>}
        </>
      )}

      <span style={{ flex: 1 }} />

      {/* LA PORTA. En mode consulta no s'ofereix cap gest d'escriptura. */}
      {!readOnly && (
        e.estat === SENSE_PRESA ? (
          <button type="button" onClick={onObrir} style={botoPorta}>
            {t('escalat.porta_obrir')}
            <IconChevronRight size={16} stroke={1.5} />
          </button>
        ) : (
          // ✅ E2c — JA NO ÉS UNA PORTA A UNA ALTRA SUPERFÍCIE: obre i tanca el panell de
          // decisió que viu a la mateixa pantalla. Per això el chevron deixa de ser de DESTÍ
          // (dreta) i passa a ser de PLEC (avall/amunt), i el botó declara `aria-expanded`:
          // un chevron dret prometria una navegació que ja no passa.
          <button type="button" onClick={onDecidir} style={botoPorta}
            disabled={e.estat === BUIDA} aria-expanded={decisioOberta}
            title={e.estat === BUIDA ? t('escalat.porta_decidir_buida') : undefined}>
            {t(decisioOberta ? 'escalat.porta_decidir_tanca'
              : (e.estat === DECIDIDA ? 'escalat.porta_revisar' : 'escalat.porta_decidir'))}
            {decisioOberta
              ? <IconChevronUp size={16} stroke={1.5} />
              : <IconChevronDown size={16} stroke={1.5} />}
          </button>
        )
      )}
      {/* MESURANT és l'estat normal i no necessita cap rètol propi: els badges ja el diuen. */}
      {e.estat === MESURANT && null}
    </div>
  )
}
