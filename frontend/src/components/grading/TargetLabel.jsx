import { useTranslation } from 'react-i18next'
import { targetLabel, targetFranja } from './gradingAxes'

// TargetLabel — patró de presentació a 2 línies (DECISIONS.md §3, el mateix que ja fan servir
// els POMs): identitat a dalt, informació secundària a sota, més petita i grisa en cursiva.
// Implementació de referència: components/POMBrowser/POMBrowser.jsx:504-512.
//
// Aquí la informació secundària és la FRANJA D'EDAT. Viu a i18n
// (`model_wizard.target_franja_<CODI>`), no al component: la franja de KID_* és una decisió de
// producte que canvia per client i per idioma, i hardcodar-la aquí obligaria a tocar JSX per
// canviar-la. Els adults la tenen BUIDA i llavors la segona línia NO es pinta gens — ni un guió
// ni un espai reservat, que faria ballar l'alçada dels pills entre adults i infantil.
//
// Font única: cap superfície resol `model_wizard.target_*` pel seu compte. Els 4 consumidors
// (ModelWizard, GradingRuleSets/TargetPills, SizingProfileSelector, CascadeSelector) passen per
// aquí, així que afegir-hi una tercera línia o canviar el patró es fa en un sol lloc.
// `franjaColor`: el gris per defecte suposa fons clar. Sobre un xip SELECCIONAT de fons ple
// (ModelWizard pinta --warn amb text blanc) el gris quedaria il·legible, així que qui té un
// fons fort passa el seu propi color en comptes de renunciar a la segona línia.
export default function TargetLabel({
  codi, nomFallback, color, fontWeight, align = 'center',
  franjaColor = 'var(--text-muted)',
}) {
  const { t } = useTranslation()
  const franja = targetFranja(t, codi)
  return (
    <span style={{ display: 'block', textAlign: align, lineHeight: 1.3 }}>
      <span style={{ display: 'block', color, fontWeight }}>
        {targetLabel(t, codi, nomFallback)}
      </span>
      {franja && (
        <span style={{
          display: 'block', fontSize: 'var(--fs-caption)', color: franjaColor,
          fontStyle: 'italic', fontWeight: 400, marginTop: 1,
        }}>{franja}</span>
      )}
    </span>
  )
}
