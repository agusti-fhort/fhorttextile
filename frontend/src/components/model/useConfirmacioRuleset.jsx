import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { FLAG_PER_TIPUS, clauDeConfirmacio } from '../../utils/confirmacioRuleset'
import Modal from '../ui/Modal'

// ELS DOS AVISOS CONSCIENTS D'ASSIGNAR UN JOC DE REGLES, en un sol lloc.
//
// `_validar_ruleset_assignable` (backend) té quatre casos: dos són bloqueig dur (ruleset buit,
// sistema de talles divergent) i arriben com a 400 —no hi ha res a preguntar—, i dos són AVISOS
// que es poden confirmar i tornen 409:
//   · `ruleset_altre_client`  (D1)     — el joc és d'un altre client. Flux de taller legítim.
//   · `esborrat_residents`    (D-31.4) — el model té regles pròpies i assignar el joc les esborra.
//
// Fins ara el primer es resolia amb DOS `window.confirm` calcats, un a `ModelWizard` i un altre a
// `ModelSheet`, i el segon no existia. Amb el segon cas la duplicació passava de dos llocs a
// quatre, i un `window.confirm` no pot ensenyar el que aquest avís ha d'ensenyar: quantes regles
// cauen i quantes d'elles vénen del document del client.
//
// 🔴 UN FLAG PER CAS, MAI ELS DOS ALHORA. Cada confirmació autoritza NOMÉS el seu cas i es
// reintenta amb el seu flag. Si els dos concorren, el backend els retorna d'un en un i aquí es
// demanen d'un en un: qui accepta fer servir el grading d'un altre client no ha acceptat, amb el
// mateix clic, que se li esborrin 88 regles pròpies.
// 🔑 EL TERCER CAS (10/08) no és d'assignar un joc a un model, sinó d'EDITAR-LO: canviar-li el
// sistema de talles quan alguna `talla_break_label` de les seves regles no existeix al run nou.
// Viu aquí igualment perquè el mecanisme és el mateix —409 amb `tipus`, un flag per cas— i
// tenir-ne dos de bessons en dos fitxers és exactament el que aquest hook va venir a acabar.
//
// 🔑 I DES DE SET-2/T7-B4, LA MEMÒRIA DEL BUCLE ÉS (TIPUS, GARMENT), no el flag sol. El motiu i
// el banc viuen a `utils/confirmacioRuleset`: amb dues prendes vives, «esborrar les regles de la
// 02» i «esborrar les de la mare» són dos avisos distints, i amb la clau vella el segon arribava
// com una avaria vermella en comptes d'una pregunta.

/** El nom d'una prenda dins d'un avís. `''` és la mare, i té nom propi: no és «cap peça». */
function nomDeLaPrenda(codi, t) {
  return codi ? t('graduacio.confirma.peca_codi', { codi }) : t('graduacio.confirma.peca_mare')
}

/**
 * DE QUINA PEÇA SÓN LES REGLES QUE ES PERDEN — SET-2/T7-B4.
 *
 * Amb dues prendes vives, «aquest model té 15 regles pròpies i les perdràs» no diu prou: perdre
 * les de tot el model i perdre les d'una sola prenda són dos gestos molt diferents, i qui
 * confirma ho ha de poder distingir ABANS de dir que sí. És el mateix argument que va fer néixer
 * `per_origen`, un tall més tard.
 *
 * NO es pinta quan el model és d'una sola peça: allà «tot» i «la mare» són la mateixa frase i el
 * desglossament només seria soroll. El 100% del corpus d'avui és així.
 */
function ResumPerGarment({ perGarment, t }) {
  const files = Object.entries(perGarment || {})
  if (files.length < 2 && !files.some(([codi]) => codi)) return null
  return (
    <div style={{ marginTop: 10 }}>
      <div style={{ fontSize: 'var(--fs-label)', letterSpacing: '.05em', textTransform: 'uppercase',
        color: 'var(--text-soft)', marginBottom: 4 }}>
        {t('graduacio.confirma.per_garment_titol')}
      </div>
      {files.sort(([a], [b]) => a.localeCompare(b)).map(([codi, n]) => (
        <div key={codi || 'base'} style={{
          display: 'flex', justifyContent: 'space-between', fontSize: 'var(--fs-body)',
        }}>
          <span>{nomDeLaPrenda(codi, t)}</span><strong>{n}</strong>
        </div>
      ))}
    </div>
  )
}

function ResumResidents({ dades, t }) {
  // La xifra d'IMPORTED, VISIBLE i separada: perdre una regla escrita a mà no és el mateix que
  // perdre'n una que ve del document del client i es pot tornar a importar. El backend la posa a
  // primer nivell del payload justament perquè aquí no s'hagi de deduir.
  const perOrigen = dades.per_origen || {}
  return (
    <div style={{
      border: '1px solid var(--border)', borderRadius: 8, padding: '10px 12px',
      background: 'var(--bg-soft, transparent)', fontSize: 'var(--fs-body)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
        <span>{t('graduacio.confirma.residents_total')}</span>
        <strong>{dades.residents}</strong>
      </div>
      {Object.entries(perOrigen).sort(([a], [b]) => a.localeCompare(b)).map(([origen, n]) => (
        <div key={origen} style={{
          display: 'flex', justifyContent: 'space-between',
          color: 'var(--text-muted)', fontSize: 'var(--fs-label)',
        }}>
          <span>{origen}</span><span>{n}</span>
        </div>
      ))}
      {dades.imported > 0 && (
        <p style={{ marginTop: 8, marginBottom: 0, color: 'var(--warn)' }}>
          {t('graduacio.confirma.imported_avis', { n: dades.imported })}
        </p>
      )}
      <ResumPerGarment perGarment={dades.per_garment} t={t} />
    </div>
  )
}

export default function useConfirmacioRuleset() {
  const { t } = useTranslation()
  const [peticio, setPeticio] = useState(null)

  const demana = (dades) => new Promise(resolve => setPeticio({ dades, resolve }))
  const tanca = (ok) => { peticio?.resolve(ok); setPeticio(null) }

  // `executa(fn, {garment})` — crida `fn(flags)` i, mentre el backend torni un 409 conegut,
  // demana la confirmació d'aquell cas i reintenta afegint NOMÉS el seu flag. Qualsevol altre
  // error passa de llarg tal com venia: aquest embolcall confirma avisos, no s'empassa errors.
  //
  // `garment` és DE QUINA PRENDA és el gest ('' = la mare), i només fa de pla B: si l'avís ho
  // diu (`d.garment`), mana el payload. Serveix per a dues coses i cap més: recordar què s'ha
  // preguntat —la clau és (tipus, garment)— i dir-ho al diàleg.
  const executa = async (fn, { garment = '' } = {}) => {
    const flags = {}
    const demanats = new Set()
    for (;;) {
      try {
        return await fn(flags)
      } catch (e) {
        const d = e?.response?.data
        const clau = e?.response?.status === 409 ? clauDeConfirmacio(d, garment) : null
        // El MATEIX avís (mateix tipus I mateixa peça) dues vegades vol dir que el backend no ha
        // acceptat el flag. Reintentar seria un bucle infinit amb cara de pantalla penjada. Un
        // avís del mateix tipus però d'UNA ALTRA peça no és el mateix avís: es torna a preguntar.
        if (!clau || demanats.has(clau)) throw e
        if (!(await demana({ ...d, garment_context: garment }))) throw e
        demanats.add(clau)
        // El flag segueix sent el del contracte del servidor, que és d'abast MODEL: la clau
        // decideix QUANTES vegades es pregunta, no QUÈ autoritza cada resposta.
        flags[FLAG_PER_TIPUS[d.tipus]] = true
      }
    }
  }

  // DE QUINA PEÇA PARLA AQUEST DIÀLEG. Només es diu quan l'avís és d'UNA prenda concreta i no és
  // la mare: en un model d'una sola peça —tot el corpus d'avui— dir-ho seria repetir el títol.
  // Quan l'avís és de tot el model, qui desglossa és `ResumPerGarment`, no el subtítol.
  const pecaDelAvis = peticio && (peticio.dades.garment ?? peticio.dades.garment_context)
  const dialeg = peticio ? (
    <Modal
      title={t(`graduacio.confirma.${peticio.dades.tipus}.titol`)}
      subtitle={pecaDelAvis ? t('graduacio.confirma.avis_de_la_peca',
        { peca: nomDeLaPrenda(pecaDelAvis, t) }) : undefined}
      confirmLabel={t('graduacio.confirma.continuar')}
      cancelLabel={t('common.cancel')}
      onCancel={() => tanca(false)}
      onConfirm={() => tanca(true)}
    >
      {/* El missatge el redacta el backend: és qui sap el nom del joc, el recompte i l'origen,
          i duplicar-lo aquí faria que pantalla i API expliquessin el mateix de dues maneres. */}
      <p style={{ fontSize: 'var(--fs-body)', marginBottom: 12 }}>{peticio.dades.message}</p>
      {peticio.dades.tipus === 'esborrat_residents' && (
        <ResumResidents dades={peticio.dades} t={t} />
      )}
      {/* Les etiquetes que no casen, ENUMERADES. «3 regles no casen» no es pot decidir; amb els
          codis a la vista, sí: qui llegeix sap si són les que no li importen o les que sí. */}
      {peticio.dades.tipus === 'etiquetes_fora_del_run' && !!peticio.dades.etiquetes?.length && (
        <ul style={{ margin: 0, paddingLeft: 20, fontSize: 'var(--fs-body)', lineHeight: 1.7 }}>
          {peticio.dades.etiquetes.map(e => (
            <li key={e.etiqueta}>
              <strong>{e.etiqueta}</strong>
              {' — '}
              {t('graduacio.confirma.etiquetes_fora_del_run.regles', { count: e.regles })}
              {!!e.poms?.length && <span style={{ color: 'var(--text-muted)' }}> ({e.poms.join(' · ')})</span>}
            </li>
          ))}
        </ul>
      )}
    </Modal>
  ) : null

  return { executa, dialeg }
}
