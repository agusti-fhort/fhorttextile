import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { anclaDeLaPeca, nomDeLaPeca } from '../../utils/pecaDefinicio'
import useToc, { anellFocus } from '../ui/toc'

// SET-2/T7-A · EL CONTENIDOR DE PEÇA de la superfície de Mesures.
//
// D'ON VE: era `DependencyPanel`, una barra grisa d'una sola línia que penjava SOTA la barra
// crema de resum del model i AL COSTAT de la taula, no al voltant. La maqueta validada per
// Agus (10/08) el converteix en el CONTENIDOR de la peça: la taula de mesures viu a dins, i
// la barra crema de resum desapareix perquè el que deia ja és a la capçalera de la pàgina
// (referència + nom) o baixa aquí (el run de talles).
//
// ⚠️ LA FILA SUPERIOR NEIX AMB LA SEGONA PEÇA (SET-2/T7-B2), no abans. Amb una sola prenda
// —el 100% del corpus d'avui— aquesta pàgina ha de quedar funcionalment IDÈNTICA a la d'abans:
// posar-hi un nom i un caret quan no hi ha res a distingir seria decorar. El predicat no el
// dedueix aquesta pantalla: el resol el servidor (`te_mes_duna_peca`, un sol lloc) i arriba per
// `mesDunaPeca`.
//
// EL LLAPIS D'AQUÍ NO EDITA: NAVEGA. El nom d'una prenda s'autoritza al Resum, que és on viu la
// definició; tenir-ne dos llocs d'edició seria tenir dues autories del mateix camp. Porta a
// l'ancla de la peça (`#peca-<codi>`) perquè s'obri on toca i no al capdamunt de la fitxa.
//
// ⚠️ EL QUE NO HI ÉS, I PER DECISIÓ (Agus, 2026-08-11): `target` i `construction` («Dona»,
// «Teixit pla»). Els deia la barra crema i NO tornen a cap superfície de treball — són
// atributs de DEFINICIÓ i viuen al Resum (pas Peça), que és on s'editen. Una pantalla de
// mesura necessita dependència, joc de regles i run, i res més. Si algun dia es decideix que
// tornin, el lloc és aquesta fila de dependència, no una barra pròpia.
//
// EL RUN NO PORTA RÈTOL. La talla base es diu amb TIPOGRAFIA (negreta + subratllat), no amb
// un «Base: S» al davant — el mateix criteri que la fitxa tècnica, on la columna de la base
// es marca sobre ella mateixa i no en un títol. La barra crema sí que el portava escrit.
//
// `accioJoc` — SLOT per a l'acció sobre el JOC DE REGLES, al costat mateix del nom que mostra
// (Graduació hi posa «Canviar joc»). És opcional: a Mesures i a Escalat la fila és de lectura,
// i el rètol italic ja ho diu. En Fase B cada contenidor de peça portarà el SEU, perquè cada
// peça va a la seva elecció de graduació.
export default function PecaContenidor({ model, children, accioJoc = null,
                                        peca = null, mesDunaPeca = false }) {
  const { t } = useTranslation()
  const [obert, setObert] = useState(true)
  if (!model) return null

  // La fila només existeix quan hi ha més d'una prenda: `peca` sense `mesDunaPeca` és el cas
  // d'avui —la mare sola— i llavors no hi ha res a encapçalar.
  const fila = mesDunaPeca && peca ? (
    <FilaPeca model={model} peca={peca} obert={obert} onCommutar={() => setObert(v => !v)} />
  ) : null

  const gtItem = model.garment_type_item_nom
    ? `${model.garment_type_item_nom}${model.garment_type_item_code ? ` (${model.garment_type_item_code})` : ''}`
    : null
  // LA REFERÈNCIA INTERNA SURT DE LA CADENA: `codi_intern` hi era com a últim graó i és
  // exactament el que la capçalera de la pàgina ja diu, en gran, dues línies més amunt.
  // La dependència és d'on penja el model, no com es diu.
  const chain = [model.garment_type_nom, gtItem].filter(Boolean)

  // ── EL JOC I EL RUN SÓN DE LA PEÇA, NO DEL MODEL (SET-2/T7-B2b) ─────────────────────────
  // Quan hi ha `peca`, els valors surten del CONTRACTE, que els serveix ja EFECTIUS: si la
  // prenda hereta, hi arriba el del model; si els declara, els seus. Aquesta pantalla no en
  // resol cap —la resolució viu en un sol punt al servidor (`valor_efectiu`)— i per això aquí
  // no hi ha cap `peca.X || model.X` sobre valors CRUS: es llegeix el que ja ve resolt.
  //
  // Sense `peca` (mentre la llista carrega, o si `/peces/` falla) es cau al model, que és
  // exactament la pantalla d'abans d'aquest canvi.
  const jocNom = peca ? (peca.grading_rule_set?.etiqueta || '') : (model.grading_rule_set_nom || '')
  const runCru = peca ? (peca.size_run_model?.valor || '') : (model.size_run_model || '')
  const baseCru = peca ? (peca.base_size_label?.valor || '') : (model.base_size_label || '')
  // El run viatja com a cadena unida per '·' (`Model.size_run_model`); partir-la per aquest
  // separador és el que ja fan `FittingDetail.jsx:636` i `TechSheetEditor.jsx:1109`.
  const talles = String(runCru).split('·').map(s => s.trim()).filter(Boolean)
  const base = String(baseCru).trim()

  return (
    // `data-peca` és el marcador ESTABLE amb què l'arnès compta contenidors i sap de quina
    // prenda és cadascun. Sense ell caldria comptar `div`s per l'estil, que és el que fa que un
    // guard es trenqui el dia que algú canviï un `border`. `''` = la mare (i cadena buida, no
    // absent: la llei del vocabulari separa «és la mare» de «no ho sé»).
    <div data-peca={peca ? peca.codi : ''} style={{
      border: '1px solid var(--line)', borderRadius: 'var(--r-card)',
      background: 'var(--panel)', marginBottom: 12,
    }}>
      {fila}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
        padding: '9px 14px', borderBottom: '1px solid var(--line)',
        fontSize: 'var(--fs-body)',
      }}>
        <i className="ti ti-sitemap" style={{ color: 'var(--text-soft)' }} />
        <span style={{ color: 'var(--text-soft)' }}>{t('dependency.title')}:</span>
        {chain.map((c, i) => (
          <span key={i} style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
            {i > 0 && <i className="ti ti-chevron-right" style={{ fontSize: 11, color: 'var(--text-soft)' }} />}
            <span style={{ color: 'var(--text-main)' }}>{c}</span>
          </span>
        ))}
        <span style={{ marginLeft: 16, color: 'var(--text-soft)' }}>{t('dependency.ruleset')}:</span>
        <span style={{ color: jocNom ? 'var(--gold)' : 'var(--text-soft)' }}>
          {jocNom || t('dependency.no_ruleset')}
        </span>
        {accioJoc}
        {!accioJoc && (
          // La pista de «lectura» NOMÉS quan la fila no porta l'acció: amb el botó al costat,
          // dir que no es pot editar aquí seria contradir-se a un pam de distància.
          <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)', fontStyle: 'italic' }}>
            {t('dependency.editable_hint')}
          </span>
        )}
        {talles.length > 0 && (
          // `marginLeft:auto` = el run s'arrambla a la DRETA de la mateixa fila. Les talles NO
          // es tradueixen mai: són dades de domini.
          <span style={{ marginLeft: 'auto', display: 'inline-flex', gap: 6, fontSize: 11 }}>
            {talles.map(tl => (
              <span key={tl} style={tl === base
                ? { color: 'var(--text-main)', fontWeight: 700, textDecoration: 'underline', textUnderlineOffset: 3 }
                : { color: 'var(--text-soft)' }}>{tl}</span>
            ))}
          </span>
        )}
      </div>
      {/* Col·lapsar amaga LA TAULA i prou. La dependència, el joc de regles i el run es
          queden: són el que et diu de quina prenda parla la fila que has plegat. */}
      {obert && <div style={{ padding: '10px 12px 12px' }}>{children}</div>}
    </div>
  )
}

/**
 * LA FILA SUPERIOR DEL CONTENIDOR: caret, nom i llapis.
 *
 * El caret plega la TAULA, no el contenidor: la identitat de la peça i el que la governa
 * (dependència, joc, run) es queden a la vista, que és el que fa que plegar sigui útil quan hi
 * ha tres prendes obertes alhora.
 */
function FilaPeca({ model, peca, obert, onCommutar }) {
  const { t } = useTranslation()
  const [toc, gestos] = useToc()
  const nom = nomDeLaPeca(peca, t('resum_wizard.model_base'))
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '9px 14px', borderBottom: '1px solid var(--line)',
    }}>
      <button type="button" onClick={onCommutar} {...gestos}
        title={t(obert ? 'peca.collapse' : 'peca.expand')}
        aria-expanded={obert}
        style={{
          width: 24, height: 24, flex: 'none', display: 'inline-flex',
          alignItems: 'center', justifyContent: 'center', padding: 0,
          borderRadius: 'var(--r-ctrl)', borderWidth: 1, borderStyle: 'solid',
          borderColor: toc.hover ? 'var(--gold)' : 'var(--line)',
          background: 'var(--panel)', color: 'var(--text-soft)', cursor: 'pointer',
          outline: 'none', ...(toc.focus ? anellFocus : null),
        }}>
        <i className={obert ? 'ti ti-chevron-down' : 'ti ti-chevron-right'} style={{ fontSize: 14 }} />
      </button>
      <span style={{ fontSize: 13, fontWeight: 600 }}>{nom}</span>
      {/* NAVEGA, no edita: el nom d'una prenda s'autoritza al Resum. */}
      <Link to={`/models/${model.id}#${anclaDeLaPeca(peca)}`} title={t('resum_wizard.rename_piece')}
        style={{
          marginLeft: 'auto', width: 24, height: 24, display: 'inline-flex',
          alignItems: 'center', justifyContent: 'center',
          borderRadius: 'var(--r-ctrl)', border: '1px solid var(--line)',
          color: 'var(--text-soft)', textDecoration: 'none',
        }}>
        <i className="ti ti-pencil" style={{ fontSize: 13 }} />
      </Link>
    </div>
  )
}
