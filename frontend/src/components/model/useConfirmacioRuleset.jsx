import { useState } from 'react'
import { useTranslation } from 'react-i18next'
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
export const FLAG_PER_TIPUS = {
  ruleset_altre_client: 'confirmar_altre_client',
  esborrat_residents: 'confirmar_esborrat_residents',
  etiquetes_fora_del_run: 'confirmar_etiquetes_fora_del_run',
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
    </div>
  )
}

export default function useConfirmacioRuleset() {
  const { t } = useTranslation()
  const [peticio, setPeticio] = useState(null)

  const demana = (dades) => new Promise(resolve => setPeticio({ dades, resolve }))
  const tanca = (ok) => { peticio?.resolve(ok); setPeticio(null) }

  // `executa(fn)` — crida `fn(flags)` i, mentre el backend torni un 409 conegut, demana la
  // confirmació d'aquell cas i reintenta afegint NOMÉS el seu flag. Qualsevol altre error passa
  // de llarg tal com venia: aquest embolcall confirma avisos, no s'empassa errors.
  const executa = async (fn) => {
    const flags = {}
    for (;;) {
      try {
        return await fn(flags)
      } catch (e) {
        const d = e?.response?.data
        const flag = e?.response?.status === 409 ? FLAG_PER_TIPUS[d?.tipus] : undefined
        // Un flag JA enviat que torna a disparar el mateix 409 vol dir que el backend no l'ha
        // acceptat. Reintentar seria un bucle infinit amb cara de pantalla penjada.
        if (!flag || flags[flag]) throw e
        if (!(await demana(d))) throw e
        flags[flag] = true
      }
    }
  }

  const dialeg = peticio ? (
    <Modal
      title={t(`graduacio.confirma.${peticio.dades.tipus}.titol`)}
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
