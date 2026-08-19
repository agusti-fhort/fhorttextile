import POMCataleg from '../components/POMCataleg/POMCataleg'

// U1 (2026-08-07) — aquesta pantalla ERA dues pestanyes: «Navegador» (POMBrowser en mode
// assignació) i «Catàleg». El brief les retira i deixa NOMÉS el catàleg, amb la fitxa sencera.
//
// El `POMBrowser` NO s'esborra ni es toca: el consumeixen 5 pantalles més (TechSheetEditor,
// POMPicker de patrons, POMCatalogue, TargetLabel). El que desapareix és aquesta porta d'entrada,
// que duplicava el catàleg amb menys informació.
export default function POMs() {
  return <POMCataleg />
}
