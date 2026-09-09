// M2 · LA CARA DE LES RONDES — el MÒDUL DE LÒGICA que les dues superfícies comparteixen.
//
// El Pla de treball (mockup A v2) i el Registre d'activitat (mockup B v3) pinten coses molt
// diferents —targetes contra graella— però responen EXACTAMENT les mateixes preguntes sobre una
// volta: de quina ronda és cada fila, quant temps porta, quantes n'hi ha de fetes, en quina fase
// va, si està entregada i quantes vegades s'ha reobert després d'entregar-la. Aquesta és la
// meitat que no es duplica (v. la vàlvula d'escapament a l'acta): la presentació sí que va
// separada, la lògica no.
//
// 🔒 CAP ENUMERACIÓ DE DOMINI AQUÍ. Ni fases, ni estats de tasca, ni motius de ronda: tot arriba
// del serializer o del catàleg (`TaskType.fase`), i el que aquest mòdul fa amb ells és comptar-los.
// L'única constant local són els tres noms d'estat de RONDA, que no són un `choices` del backend
// sinó la lectura de dos camps (`tancada_el` i l'entrega niuada) — v. `estatDeRonda`.
//
// 🔒 CAP `localStorage`. El col·lapse d'una volta es DERIVA del seu estat (entregada = tancada;
// vigent = oberta) i no es persisteix: una decisió d'usuari desada convertiria l'estat del
// domini en una preferència, i el dia que la volta s'entregués la cara seguiria dient que és
// vigent perquè algú la va desplegar una vegada.

/** Els tres estats d'una VOLTA, llegits de la ronda (no són cap `choices` del backend). */
export const RONDA_ENTREGADA = 'entregada'
export const RONDA_TANCADA = 'tancada'
export const RONDA_OBERTA = 'oberta'

/**
 * L'estat d'una volta, i els tres casos existeixen de debò.
 *
 * `entregada` i `tancada` NO són el mateix i el contracte del serializer és explícit: `entregada`
 * és el FET declarat (hi ha `Entrega`) i el tancament n'és la conseqüència (FIT-13). Però una
 * volta pot estar tancada sense entrega —`tancar_ronda` és un servei i l'entrega no és el seu
 * únic cridador possible—, i pintar-la «En curs» seria mentir sobre feina que ja no admet ningú.
 */
export function estatDeRonda(ronda) {
  if (!ronda) return null
  if (ronda.entregada) return RONDA_ENTREGADA
  if (ronda.tancada_el) return RONDA_TANCADA
  return RONDA_OBERTA
}

/**
 * La FASE d'una volta: la del gruix de la seva feina.
 *
 * La ronda no té camp `fase` i no se n'hi ha inventat cap: la fase viu al CATÀLEG
 * (`TaskType.fase`, que `TaskTypeSerializer` ja serveix) i una volta no és més que un joc de
 * tasques. Es tria la fase MAJORITÀRIA; l'empat el desfà el `default_order` més baix del
 * catàleg —el treball que va primer—, que és dada del catàleg i no una llista de fases escrita
 * aquí. Sense catàleg carregat o sense tasques, `null`: millor cap pastilla que una endevinada.
 */
export function faseDeTasques(tasques, tipusPerCode) {
  if (!tipusPerCode || !tasques?.length) return null
  const compte = new Map()   // fase -> { n, ordre }
  for (const t of tasques) {
    const tipus = tipusPerCode[t.task_type_code]
    if (!tipus?.fase) continue
    const ordre = tipus.default_order ?? Number.MAX_SAFE_INTEGER
    const prev = compte.get(tipus.fase)
    if (prev) { prev.n += 1; prev.ordre = Math.min(prev.ordre, ordre) }
    else compte.set(tipus.fase, { n: 1, ordre })
  }
  let guanyadora = null
  for (const [fase, { n, ordre }] of compte) {
    if (!guanyadora || n > guanyadora.n || (n === guanyadora.n && ordre < guanyadora.ordre)) {
      guanyadora = { fase, n, ordre }
    }
  }
  return guanyadora?.fase ?? null
}

/**
 * FIT-8 · Quantes vegades s'ha reobert cada volta DESPRÉS d'haver-la entregada.
 *
 * Es COMPTA, no es dedueix parsejant la frase: `TaskTransition.nota` només s'escriu quan la
 * tasca pertany a una volta amb entrega informada (`_nota_reobertura_post_entrega`), o sigui que
 * la seva PRESÈNCIA ja és el marcador; `ronda_seq` l'agrupa. Les dues coses les serveix
 * `task-log/` des d'M2 — abans la dada s'escrivia i no sortia per cap porta.
 *
 * Retorna un `Map(seq -> n)`. Una volta que no hi és no s'ha reobert mai.
 */
export function rectificacionsPerVolta(log) {
  const m = new Map()
  for (const fila of (log || [])) {
    if (!fila?.nota || fila.ronda_seq == null) continue
    m.set(fila.ronda_seq, (m.get(fila.ronda_seq) || 0) + 1)
  }
  return m
}

/**
 * M4 · FIT-12 — EL «PERQUÈ» D'UNA VOLTA FORA DE COMANDA, en peces i sense traduir.
 *
 * Retorna `{ clau, params }` per a `t()`, o `null` si la volta cau DINS del numeral (regla del
 * silenci: un xip només es pinta si diu alguna cosa). Les DUES superfícies que ho ensenyen —la
 * safata d'albaranables i el contenidor de ronda del Pla— han de dir exactament la mateixa
 * frase, i per això es compon en UN sol lloc i no a cada cara.
 *
 * 🔒 AQUÍ NO ES TRADUEIX RES, i és el motiu pel qual això torna una clau i no un text: aquest
 * mòdul és de regles pures i no pot importar l'i18n. Les claus viuen sota `deliverynotes.*`
 * perquè és on van néixer amb la safata; el nom del namespace és històric i no vol dir que la
 * frase sigui d'aquella pantalla.
 */
export function perqueForaDeComanda(ronda) {
  if (!ronda?.fora_de_comanda) return null
  return {
    clau: ronda.comanda ? 'deliverynotes.ronda_perque' : 'deliverynotes.ronda_perque_sense_comanda',
    params: { n: ronda.seq, numeral: ronda.numeral_vigent, comanda: ronda.comanda },
  }
}

/**
 * AGRUPA les files d'una superfície per VOLTA i n'agrega els mateixos eixos que el detall.
 *
 * `files` són les tasques del compositor del dashboard (Pla) o els passos de l'albarà
 * (Registre): tots dos porten `ronda_seq` des d'M2 i per això la clau és la SEQ i no l'id —
 * l'albarà no en té cap altre lligam amb la volta, i la seq és única dins del model.
 *
 * ⚠️ **LES FILES SENSE VOLTA NO ES PERDEN.** `ronda_seq` null vol dir feina d'abans del canvi de
 * llei (M1-bis · FIT-4) o nascuda al buit entre voltes, i és la forma que tenen ARA els models
 * llegats sencers. Van a un bloc propi al final, amb `ronda: null`: fer-les desaparèixer perquè
 * el mockup no les dibuixa seria que la pantalla n'ensenyés menys que abans d'aquest sprint.
 *
 * 🚨 **NI LES DE VOLTA DESCONEGUDA.** Els blocs es construeixen des de `voltes`, no des de les
 * files: una fila amb `ronda_seq = N` on `N` no és a `voltes` no queia a `orfes` (la guarda de
 * sota mira `== null`, i la seva no ho és) ni tenia bloc on anar — **desapareixia en silenci**,
 * sense error, sense buit i amb 200 OK a la xarxa. És el defecte que va reportar en Salva: les
 * dues fonts d'aquesta pantalla arriben per portes diferents (`/dashboard/` les tasques,
 * `/rondes/` les voltes) i, quan la segona va endarrerida, la tasca acabada d'assignar no
 * apareixia enlloc. Ara aquestes files cauen al mateix bloc `orfes`: sortir al lloc equivocat
 * és infinitament més diagnosticable que no sortir.
 * (v. DIAGNOSI_REACTIVITAT_FRONT.md §Q2.2 · §Q4.4·2)
 *
 * Opcions: `minutsDe` i `esFeta` (els dos payloads anomenen els seus camps diferent).
 */
export function agrupaPerRonda(files, rondes, opcions = {}) {
  const {
    minutsDe = (f) => f.temps_consumit_min ?? 0,
    esFeta = (f) => f.status === 'Done',
    tipusPerCode = null,
    log = null,
  } = opcions

  const llista = Array.isArray(files) ? files : []
  const voltes = Array.isArray(rondes) ? [...rondes].sort((a, b) => a.seq - b.seq) : []
  const rectificacions = rectificacionsPerVolta(log)

  const perSeq = new Map()
  const orfes = []
  for (const f of llista) {
    if (f.ronda_seq == null) { orfes.push(f); continue }
    if (!perSeq.has(f.ronda_seq)) perSeq.set(f.ronda_seq, [])
    perSeq.get(f.ronda_seq).push(f)
  }

  const bloc = (ronda, tasques) => {
    const total = tasques.length
    const fets = tasques.filter(esFeta).length
    return {
      clau: ronda ? `r${ronda.seq}` : 'orfe',
      ronda,
      seq: ronda?.seq ?? null,
      estat: estatDeRonda(ronda),
      entrega: ronda?.entrega ?? null,
      lliurable: ronda?.lliurable ?? false,
      // L'inici i el fi d'una volta són SEUS (`oberta_el`/`tancada_el`), no el mínim i el màxim
      // de les seves tasques: una volta comença quan s'obre encara que ningú no hi hagi tocat res.
      inici: ronda?.oberta_el ?? null,
      fi: ronda?.tancada_el ?? null,
      tasques,
      total,
      fets,
      pct: total ? Math.round((100 * fets) / total) : 0,
      minuts: tasques.reduce((s, f) => s + (minutsDe(f) || 0), 0),
      fase: faseDeTasques(tasques, tipusPerCode),
      rectificacions: ronda ? (rectificacions.get(ronda.seq) || 0) : 0,
      // Derivat, mai persistit: una volta entregada ja no demana atenció i neix plegada.
      obertPerDefecte: estatDeRonda(ronda) !== RONDA_ENTREGADA,
    }
  }

  const blocs = voltes.map(r => {
    const tasques = perSeq.get(r.seq) || []
    perSeq.delete(r.seq)          // consumida: el que quedi a `perSeq` és feina sense volta coneguda
    return bloc(r, tasques)
  })

  // Les files que reclamen una volta que no ens ha arribat. `perSeq` es consumeix a mesura que
  // es reparteix, i el que hi queda són exactament aquestes: cap fila pot sortir d'aquí sense
  // haver estat mirada. L'ordre de `seq` les manté estables entre renders.
  for (const seq of [...perSeq.keys()].sort((a, b) => a - b)) {
    orfes.push(...perSeq.get(seq))
  }
  if (orfes.length) blocs.push(bloc(null, orfes))
  return blocs
}
