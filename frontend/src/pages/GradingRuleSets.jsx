import { useState } from 'react'
import JocsDeRegles from '../components/grading/JocsDeRegles'
import SizeAuthoringDrawer from '../components/SizeAuthoringDrawer'

// A3 (08/08) — AQUESTA PANTALLA ERA UNA CASCADA i ara és el CATÀLEG DE JOCS DE REGLES.
//
// El que hi havia era un `CascadeSelector` de quatre eixos que no ensenyava CAP joc fins que se
// n'havien triat els quatre, i llavors en pintava les targetes que hi casaven. La maqueta v4 ho
// descarta amb aquestes paraules: «la llista és una llista, no mitja pantalla: hi caben totes
// les columnes que importen i es comparen d'un cop d'ull». El que la cascada responia —quin joc
// surt per a aquest cas— ho respon ara la columna «Es proposa a», que ho diu de TOTS els jocs
// alhora i sense obligar a endevinar la combinació.
//
// ⚠️ `CascadeSelector`, `matchingRuleSets` i les targetes de RuleSet NO S'ESBORREN: la cascada la
// munten el wizard i altres superfícies, i esborrar el que aquí deixa de muntar-se seria una
// decisió d'abast que aquest tram no té. Queda anotat al report.
//
// PADDING ARREL 0 (NORMA §3): el `<main>` del Shell ja dona 24. El component és qui munta el
// menú de pantalla (§8b) i qui se n'obre pas a través d'aquest 24.
//
// EL DRAWER D'AUTORIA ES QUEDA MUNTAT: és la variant «Importar d'una fitxa» de l'acció composta
// «＋ Nou joc ▾» (NORMA §1: un sol botó amb desplegable, mai dues accions directes al mateix lloc).

export default function GradingRuleSets() {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [recarrega, setRecarrega] = useState(0)

  return (
    <>
      <JocsDeRegles key={recarrega} onImportar={() => setDrawerOpen(true)} />

      <SizeAuthoringDrawer
        open={drawerOpen}
        prefill={null}
        onClose={() => setDrawerOpen(false)}
        onComplete={() => { setDrawerOpen(false); setRecarrega(k => k + 1) }}
      />
    </>
  )
}
