import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { gradingRuleSets, garmentGroups } from '../../api/endpoints'
import RuleSetPicker from './RuleSetPicker'

// EL CONTENIDOR CENTRAL DE GRADUACIÓ (P0.5a · Agus, 06/08) — triar el joc de regles d'un model.
//
// PER QUÈ NO ÉS `GraduacioPanel`. Aquell és el pas 4 del wizard, i hi porta les seves portes:
// sense `size_system` no ensenya res, demana un FIT abans d'obrir el picker, i el picker corre
// en mode ESTRICTE (`matchingRuleSetsStrict`), que exclou tot el que no casi amb els cinc eixos.
// Amb un model real al davant això acaba en «falta la construcció» i una llista buida: el
// tècnic veu que li falta alguna cosa però no pot triar RES, i el que venia a fer era assignar
// un joc que ja existeix i que sap quin és.
//
// AQUÍ LA PERTINENÇA ORDENA, NO EXCLOU — la mateixa llei que el pas 3 del wizard aplica als
// sistemes de talles i que C5 va portar al catàleg de peces (D-31.3):
//   1r · els jocs del CLIENT del model (BRW → els seus primer)
//   2n · la resta, en l'ordre que el classificador ja els dona (compatibles i, avall, atenuats)
// Cap joc queda fora de la llista. El que no encaixa s'ATENUA i diu per què, però es pot triar:
// és una decisió del tècnic, no una porta del sistema.
//
// El `RuleSetPicker` en mode `eliminatiu` ja fa exactament això (C5) i ja pinta el nom, el
// recompte de regles i el joc seleccionat. No se'n fa cap de nou: el que faltava era que algú
// el cridés sense el mode estricte.
//
// L'ESCRIPTURA NO CANVIA: `onUsar(rs)` és el mateix `update-step2` de sempre, amb els seus dos
// avisos conscients (D1 · client aliè i D-31.4 · esborrat de regles residents) que ja porta
// `useConfirmacioRuleset` a qui el crida. Aquí no es duplica cap guard.
export default function GraduacioContenidor({
  model,
  gradingRuleSetId,
  onUsar,
  onManual,
  onTanca,
}) {
  const { t } = useTranslation()
  const [ruleSets, setRuleSets] = useState([])
  const [ggCodiById, setGgCodiById] = useState({})
  const [carregant, setCarregant] = useState(true)

  const clientId = model?.customer ?? null
  useEffect(() => {
    let viu = true
    Promise.all([
      // S45/C — I EL CATÀLEG ARRIBA JA ACOTAT. Abans es demanaven els 51 jocs amb regles de
      // PROD —18 d'ells JUBILATS i 24 de LOS— i el picker els pintava tots. El sedàs va al
      // SERVIDOR i no aquí: quatre pantalles filtrant pel seu compte serien quatre filtres
      // que divergeixen. `actiu=True` és ara el defecte del ViewSet (jubilar ≠ amagar: qui
      // els vol, passa `include_inactive=1`), i `per_client` demana els del client del model
      // MÉS els de catàleg —mai els d'un altre client.
        // 🚨 `inclou`: EL JOC QUE EL MODEL JA PORTA NO ES POT AMAGAR MAI. Al 1383 (TRV) hi
        // ha assignat el joc 219, que és de BRW: amb el sedàs de client, el picker s'obriria
        // sense ell i diria que el model no en té cap. El que està EN ÚS travessa el sedàs.
      gradingRuleSets.list({
        page_size: 200, amb_regles: 1,
        ...(clientId ? { per_client: clientId } : {}),
        ...(gradingRuleSetId ? { inclou: gradingRuleSetId } : {}),
      }),
      garmentGroups.list({ page_size: 200 }),
    ]).then(([rsRes, ggRes]) => {
      if (!viu) return
      const rs = rsRes.data?.results ?? (Array.isArray(rsRes.data) ? rsRes.data : [])
      const gg = ggRes.data?.results ?? (Array.isArray(ggRes.data) ? ggRes.data : [])
      const map = {}; gg.forEach(g => { map[g.id] = g.codi })
      setRuleSets(rs); setGgCodiById(map); setCarregant(false)
    }).catch(() => { if (viu) { setRuleSets([]); setCarregant(false) } })
    return () => { viu = false }
  }, [clientId, gradingRuleSetId])

  // ELS DEL CLIENT DEL MODEL, PRIMER. El classificador de dins del picker torna a partir la
  // llista en compatibles i atenuats, però conserva l'ordre relatiu dins de cada bloc: sortint
  // d'aquí ordenats per client, els del client encapçalen els dos blocs.
  const clientCodi = (model?.customer_codi || '').trim()
  const ordenats = useMemo(() => {
    if (!clientCodi) return ruleSets
    return [...ruleSets].sort((a, b) => {
      const seu = (rs) => ((rs.customer_codi || '').trim() === clientCodi ? 0 : 1)
      return seu(a) - seu(b)
    })
  }, [ruleSets, clientCodi])

  // Els eixos del model, per ATENUAR el que no encaixa (mai per excloure'l). Un eix buit no
  // penalitza ningú: el classificador només compara els que estan informats.
  const axes = useMemo(() => ({
    target: model?.target || null,
    construction: model?.construction || null,
    garmentGroup: model?.garment_type_grup || null,
    garmentTypeId: model?.garment_type ?? null,
    garmentTypeItemId: model?.garment_type_item ?? null,
  }), [model])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <p style={{ margin: 0, fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
        {t('graduacio.contenidor.intro')}
      </p>

      {/* L'ENTRADA MANUAL, a dalt i al mateix nivell que els jocs: graduar a mà no és el que
          es fa quan no hi ha res que encaixi, és una manera legítima de graduar un model. */}
      <button type="button" onClick={onManual}
        style={{
          display: 'flex', alignItems: 'center', gap: 10, width: '100%', textAlign: 'left',
          border: '1px dashed var(--gold)', borderRadius: 10, background: 'var(--white)',
          padding: '12px 16px', cursor: 'pointer', font: 'inherit',
        }}>
        <i className="ti ti-pencil-plus" style={{ fontSize: 16, color: 'var(--gold)' }} aria-hidden="true" />
        <span style={{ minWidth: 0 }}>
          <span style={{ display: 'block', fontWeight: 600, fontSize: 'var(--fs-body)' }}>
            {t('graduacio.contenidor.manual')}
          </span>
          <span style={{ display: 'block', fontSize: 'var(--fs-label)', color: 'var(--text-muted)' }}>
            {t('graduacio.contenidor.manual_hint')}
          </span>
        </span>
      </button>

      <div style={{ height: 1, background: 'var(--border)' }} />

      {carregant
        ? <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>
            {t('app.loading')}
          </p>
        : (
          <RuleSetPicker
            ruleSets={ordenats}
            garmentGroupCodiById={ggCodiById}
            axes={axes}
            eliminatiu
            selectedId={gradingRuleSetId ?? null}
            actionLabel={t('model_sheet.use_ruleset')}
            onPick={onUsar}
          />
        )}

      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button type="button" onClick={onTanca}
          style={{
            border: '0.5px solid var(--border)', borderRadius: 6, background: 'var(--white)',
            color: 'var(--text-muted)', padding: '6px 16px', cursor: 'pointer', font: 'inherit',
            fontSize: 'var(--fs-body)',
          }}>{t('app.close')}</button>
      </div>
    </div>
  )
}
