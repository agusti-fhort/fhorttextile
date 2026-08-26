import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import Modal from '../ui/Modal'
import { selS } from '../ui/buttons'
import { entregues } from '../../api/endpoints'

// M2 · FIT-1 — INFORMAR L'OK DEL CLIENT sobre una entrega ja informada.
//
// És el senyal MANUAL i POSTERIOR: no es dedueix de res i no toca la ronda (quan arriba, ja fa
// estona que és tancada). S'informa **UN SOL COP** —és un fet, no un interruptor— i per això el
// diàleg no ofereix cap manera de tornar-lo enrere: el segon PATCH el rebutja el servei amb
// `ok_client_invalid` i seria una promesa que la cara no pot complir.
//
// Es demana NOMÉS la data, i és opcional: l'OK arriba per telèfon o per correu i pot ser d'un
// altre dia (per això és un camp i no un botó sol), però el cas normal és «avui» i el servei ja
// hi posa ARA quan no en rep cap. **QUI l'informa no es demana mai**: surt del JWT, com a M1.
export default function OkClientDialog({ entrega, onFet, onCancel }) {
  const { t } = useTranslation()
  const [data, setData] = useState('')
  const [enviant, setEnviant] = useState(false)
  const [error, setError] = useState(null)

  const confirma = () => {
    if (enviant) return
    setEnviant(true); setError(null)
    // Camp buit = cap `data_ok` al cos: el servei hi posa ARA. Enviar-hi la cadena buida
    // seria un 400 de forma per no haver escrit res, que no és el que l'usuari ha dit.
    entregues.okClient(entrega.id, data ? { data_ok: new Date(data).toISOString() } : {})
      .then(res => onFet?.(res?.data))
      .catch(e => {
        setError(e?.response?.data?.error
          || e?.response?.data?.data_ok?.[0]
          || t('rondes.ok_client_error'))
        setEnviant(false)
      })
  }

  return (
    <Modal
      title={t('rondes.ok_client_titol')}
      subtitle={t('rondes.ok_client_cos', { destinatari: entrega.destinatari })}
      confirmLabel={t('rondes.ok_client_confirma')}
      cancelLabel={t('common.cancel')}
      confirmDisabled={enviant}
      onConfirm={confirma}
      onCancel={() => { if (!enviant) onCancel?.() }}
    >
      <div>
        <label htmlFor="ok-client-data" style={{
          display: 'block', fontSize: 'var(--fs-label)', letterSpacing: '.08em',
          textTransform: 'uppercase', color: 'var(--text-soft)', fontWeight: 600, marginBottom: 6,
        }}>{t('rondes.ok_client_data')}</label>
        <input id="ok-client-data" type="date" value={data} autoFocus
               style={{ ...selS, fontFamily: 'inherit' }}
               onChange={e => setData(e.target.value)} />
        <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', margin: '6px 0 0' }}>
          {t('rondes.ok_client_data_nota')}
        </p>
        {error && (
          <div style={{ fontSize: 'var(--fs-body)', color: 'var(--err)', marginTop: 10 }}>{error}</div>
        )}
      </div>
    </Modal>
  )
}
