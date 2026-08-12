// --- REPÀS de fittings (taula POM × esdeveniments, LECTURA) --------------------------------------
//
// L'eix del fitting editor és la VERSIÓ (una sessió, com evoluciona la teoria). Aquí l'eix és
// l'ESDEVENIMENT: tot el que és fitting del model, vingui de l'eina (FittingSession) o de la mà
// (etapes de la taula de mesures). Mateixa anatomia: un sol group (la talla), N columnes
// d'història + l'ACTIVA = l'últim esdeveniment (és el que mana visualment, i el gold-pale de
// MeasureGrid ja diu «aquest») + trailCol COMENTARIS. Res editable: la font és l'endpoint de repàs.
//
// PER QUÈ AQUEST FITXER EXISTEIX. Aquest codi vivia dins de `fittingGridAdapter.jsx`, que
// `measureSources.jsx` importa — o sigui, un mòdul del qual PENJA LA TAULA DE MESURES. La taula de
// mesures és intocable (decisió Agus: és l'eina d'impressió per als fittings presencials), i el
// Repàs havia de créixer. Se separa perquè aquesta frontera sigui estructural i no una casualitat
// que el proper canvi es carregui: el Repàs ja no comparteix cap fitxer amb la taula de mesures
// tret de `MeasureGrid`, que no es toca.
//
// El moviment és una EXTRACCIÓ literal; l'únic afegit és el suport de les columnes d'etapa.

const fmtDia = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('ca-ES', { day: '2-digit', month: '2-digit' })
}

// Punt d'estat de la sessió: verd = tancada (el que s'hi va prendre ja no es mou), daurat = oberta.
const estatAccent = (estat) => (estat === 'Tancada' ? 'var(--ok)' : 'var(--gold)')

// Punt per ORIGEN de l'etapa. MATEIXA paleta que la taula de mesures fa servir per als seus
// estadis (CheckMeasureEditor.stageAccent): verd = sessió de fitting, daurat = presa humana de
// taller/proto. Es replica el criteri de color, no el codi — el mòdul d'allà no es toca.
const origenAccent = (origen) => ({
  FITTING: 'var(--ok)',
  CHECKED: 'var(--gold)',
  MANUAL: 'var(--gold-l)',
}[origen] || 'var(--gray)')

// Capçalera de columna. Dues menes d'esdeveniment amb la MATEIXA forma de dada (el backend les
// serveix igual), i per això un sol component:
//   · SESSIO → la fase de la sessió (dada de domini: NO es tradueix) + punt d'estat.
//   · etapa  → l'origen, TRADUÏT (FITTED/CHECKED/MANUAL no són text de cara a l'usuari) + punt
//              d'origen. Reusa les claus `basestage.ctx.*` que la taula de mesures ja fa servir
//              per als seus estadis: el tècnic ha de llegir la mateixa paraula als dos llocs.
// Si l'esdeveniment porta comentari propi (notes o motiu del gate), l'indicador viu aquí: és un
// comentari de SESSIÓ, no de cel·la.
function EsdevenimentLabel({ session, t }) {
  // B2 — L'ENTRADA DE POMs és la primera columna i NO és un esdeveniment de fitting: és d'on
  // es parteix. Per això no porta ni punt d'estat ni data —la data d'una entrada de fitxa no
  // diu res a qui repassa— sinó la icona de la taula i el seu nom, traduït.
  if (session.origen === 'ENTRADA') {
    return (
      <span>
        <i className="ti ti-table-plus" aria-hidden="true"
          style={{ fontSize: 12, marginRight: 4, color: 'var(--text-muted)', verticalAlign: 'middle' }} />
        {t('fitting.repas.col_entrada')}
      </span>
    )
  }
  const esEtapa = session.origen && session.origen !== 'SESSIO'
  const comentari = [
    session.notes && `${t('fitting.repas.session_notes')}: ${session.notes}`,
    session.gate_motiu && `${t('fitting.repas.gate_motiu')} (${session.gate}): ${session.gate_motiu}`,
  ].filter(Boolean).join('\n')
  const titol = esEtapa
    ? t(`basestage.ctx.${String(session.origen).toLowerCase()}`, session.origen)
    : session.fase
  return (
    <span>
      <span aria-hidden="true" style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%',
        background: esEtapa ? origenAccent(session.origen) : estatAccent(session.estat),
        marginRight: 4, verticalAlign: 'middle' }} />
      {titol}
      {esEtapa && (
        // Que la columna digui d'on surt: una presa escrita a la taula de mesures no és una
        // sessió de fitting, i el repàs no ha de fer-les passar per la mateixa cosa.
        <i className="ti ti-table" title={t('fitting.repas.des_de_mesures')}
          aria-label={t('fitting.repas.des_de_mesures')}
          style={{ fontSize: 11, marginLeft: 4, color: 'var(--text-muted)', verticalAlign: 'middle' }} />
      )}
      {comentari && (
        <i className="ti ti-message-circle" title={comentari} aria-label={comentari}
          style={{ fontSize: 11, marginLeft: 4, color: 'var(--gold)', verticalAlign: 'middle' }} />
      )}
      {session.data && <span style={{ display: 'block', fontWeight: 400, fontSize: 'var(--fs-caption)' }}>@{fmtDia(session.data)}</span>}
    </span>
  )
}

// Columna final: l'ÚLTIM comentari del POM (el darrer no buit, que el backend ja resol) amb la data
// d'on ve. Un POM sense cap comentari deixa la cel·la buida, no un guionet: no hi ha res a dir.
function UltimComentari({ ultim }) {
  if (!ultim?.text) return null
  return (
    <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)', whiteSpace: 'normal' }}>
      {ultim.text}
      {ultim.data && (
        <span style={{ marginLeft: 6, fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>@{fmtDia(ultim.data)}</span>
      )}
    </span>
  )
}

export function buildRepasGroups(sessions, talla, baseLabel, t) {
  if (!sessions?.length) return []
  const ultima = sessions[sessions.length - 1]
  return [{
    key: 'repas',
    label: talla
      ? (talla === baseLabel
        ? <span>{talla}<i className="ti ti-star" style={{ fontSize: 10, marginLeft: 4, color: 'var(--gold)' }} /></span>
        : talla)
      : '—',
    historyCols: sessions.slice(0, -1).map(s => ({ key: String(s.id), label: <EsdevenimentLabel session={s} t={t} /> })),
    activeLabel: <EsdevenimentLabel session={ultima} t={t} />,
    trailCols: [{ key: 'coment', label: t('fitting.repas.col_comments') }],
  }]
}

export function buildRepasRows(rows, sessions) {
  if (!sessions?.length) return []
  const ultima = sessions[sessions.length - 1]
  return (rows || []).map(row => {
    const history = {}
    for (const s of sessions.slice(0, -1)) {
      const v = row.valors?.[String(s.id)]
      // Objecte {value, nota} SEMPRE: és el contracte que fa aparèixer l'indicador de comentari
      // a MeasureGrid. Sense presa en aquell esdeveniment, la cel·la queda a null (surt '—').
      //
      // B2 — `canvi` i `veredicte` els decideix EL BACKEND (`repas_views`), que és qui coneix
      // l'ordre de les columnes. Aquí no es recalcula res: un front que comparés cel·les seria
      // un segon lloc capaç de dir una cosa diferent sobre el mateix parell de números.
      history[String(s.id)] = v
        ? { value: v.valor_real, nota: v.nota, canvi: !!v.canvi, veredicte: v.veredicte || null }
        : null
    }
    const v = row.valors?.[String(ultima.id)]
    // C4/BLOC 3 — l'identificador de línia porta els dos eixos. El repàs ja agrupa per
    // `(pom_id, capa, instancia)` al backend (`repas_views._fila`), o sigui que dues germanes
    // arriben com a dues files; amb `repas:${pom_id}` les dues compartien lineId i el buffer
    // per lineId de MeasureGrid els donava el mateix valor a la columna activa.
    //
    // Aquí NO s'hi posa la clau de payload (`{pom}|{capa}|{inst}`) sinó els camps tal com
    // vénen: aquest identificador és sintètic i intern del front —la columna és read-only i
    // no es desa enlloc—, i fer-lo passar per la clau del contracte seria un segon lloc que
    // decideix com s'aplana una identitat que decideix `pom/identitat.py`.
    // SET-2/T6b — l'eix de PRENDA hi entra pel mateix motiu que els dos de germanor, i per
    // aquí i no per `identitatMesura`: aquest identificador és sintètic, intern i amb dialecte
    // propi (prefix + `:`), i el paràgraf de sobre diu per què no ha de passar per la clau del
    // contracte. El que ha de créixer és l'eix, no el format.
    const ident = `repas:${row.pom_id}:${row.capa || ''}:${row.instancia || ''}:${row.garment || ''}`
    return {
      pom_id: row.pom_id, codi: row.codi, pom_code: row.pom_code, is_key: row.is_key,
      capa: row.capa, instancia: row.instancia,
      rowKey: ident,   // clau de fila per a MeasureGrid (v. `ident` aquí sobre)
      nom_en: row.nom_en, nom_local: row.nom_local, nom_fitxa: row.nom_fitxa, bm_id: row.bm_id,
      cells: {
        repas: {
          history,
          // El VEREDICTE només tenyeix la cel·la quan hi ha CANVI (ordre d'Agus: «els canvis es
          // marquen; la resta, normal»). Una presa que confirma el número anterior es llegeix
          // com el que és —res de nou— i la taula es queda quieta.
          active: v ? { lineId: ident, value: v.valor_real ?? '', baseValue: null, nota: v.nota,
                        readonly: true, canvi: !!v.canvi,
                        veredicte: v.canvi ? (v.veredicte || null) : null } : null,
          trail: { coment: <UltimComentari ultim={row.ultim_comentari} /> },
        },
      },
    }
  })
}
