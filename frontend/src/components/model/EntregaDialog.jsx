import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import Modal from '../ui/Modal'
import { selS } from '../ui/buttons'
import { rondes as rondesApi } from '../../api/endpoints'

// M2 · FIT-1 + FIT-13 — INFORMAR L'ENTREGA D'UNA VOLTA.
//
// 🔒 **EL DIÀLEG HO HA DE DIR ABANS DE CONFIRMAR.** Informar una entrega no és només escriure una
// fila: `informar_entrega` obre una transacció i, dins seu, TANCA la ronda (FIT-13), i tancar-la
// tanca tota la feina viva de la volta (FIT-6). Un botó que digués només «Informar entrega»
// amagaria dues conseqüències irreversibles darrere d'un formulari de dos camps. L'avís va al
// COS del diàleg, no a un tooltip, i amb el recompte de la feina que es tancarà quan n'hi hagi.
//
// Els dos camps són TEXT LLIURE per disseny (FIT-1: l'entrega és un EVENT INFORMAT, no un
// artefacte controlat). `destinatari` és l'únic obligatori i el guard viu al servei
// («una entrega sense destinatari no diu res»); aquí només s'evita el viatge inútil.
// `data` no es demana: el servei la posa a ARA. Qui informa surt del JWT, mai del client.
export default function EntregaDialog({ ronda, viues = 0, onFet, onCancel }) {
  const { t } = useTranslation()
  const [destinatari, setDestinatari] = useState('')
  const [descripcio, setDescripcio] = useState('')
  const [enviant, setEnviant] = useState(false)
  const [error, setError] = useState(null)

  const confirma = () => {
    if (enviant || !destinatari.trim()) return
    setEnviant(true); setError(null)
    rondesApi.entrega(ronda.id, { destinatari: destinatari.trim(), descripcio: descripcio.trim() })
      .then(res => onFet?.(res?.data))
      .catch(e => {
        // El 409 té codi propi (`ronda_no_tancable`): l'entrega NO s'ha escrit i el motiu és la
        // feina de la volta, no la forma del formulari. El missatge del servidor mana sempre.
        setError(e?.response?.data?.error || t('rondes.entrega_error'))
        setEnviant(false)
      })
  }

  const camp = { ...selS, width: '100%', fontFamily: 'inherit' }
  const etiqueta = {
    display: 'block', fontSize: 'var(--fs-label)', letterSpacing: '.08em',
    textTransform: 'uppercase', color: 'var(--text-soft)', fontWeight: 600, marginBottom: 6,
  }

  return (
    <Modal
      title={t('rondes.entrega_titol', { n: ronda.seq })}
      confirmLabel={t('rondes.entrega_confirma')}
      cancelLabel={t('common.cancel')}
      confirmDisabled={enviant || !destinatari.trim()}
      onConfirm={confirma}
      onCancel={() => { if (!enviant) onCancel?.() }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div>
          <label style={etiqueta} htmlFor="entrega-destinatari">{t('rondes.entrega_destinatari')}</label>
          <input id="entrega-destinatari" style={camp} value={destinatari} autoFocus
                 placeholder={t('rondes.entrega_destinatari_ph')}
                 onChange={e => setDestinatari(e.target.value)} />
        </div>
        <div>
          <label style={etiqueta} htmlFor="entrega-descripcio">{t('rondes.entrega_descripcio')}</label>
          <textarea id="entrega-descripcio" style={{ ...camp, minHeight: 72, resize: 'vertical' }}
                    value={descripcio} placeholder={t('rondes.entrega_descripcio_ph')}
                    onChange={e => setDescripcio(e.target.value)} />
        </div>

        {/* L'AVÍS. Va abans del botó i diu les dues conseqüències amb el nom que tenen. */}
        <div style={{
          display: 'flex', gap: 8, alignItems: 'flex-start',
          background: 'var(--warn-state-bg)', border: '1px solid var(--warn-state)',
          borderRadius: 'var(--r-ctrl)', padding: '10px 12px',
          fontSize: 'var(--fs-body)', color: 'var(--warn-ink)',
        }}>
          <i className="ti ti-alert-triangle" aria-hidden="true" style={{ fontSize: 16, flexShrink: 0 }} />
          <span>
            {t('rondes.entrega_avis', { n: ronda.seq })}
            {viues > 0 && <> {t('rondes.entrega_avis_viues', { count: viues })}</>}
          </span>
        </div>

        {error && (
          <div style={{ fontSize: 'var(--fs-body)', color: 'var(--err)' }}>{error}</div>
        )}
      </div>
    </Modal>
  )
}
