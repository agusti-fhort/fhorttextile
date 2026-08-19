import test from 'node:test'
import assert from 'node:assert/strict'

import {
  CAP, ERR_LLISTA, ERR_TASCA, OBERT, creaFontTramObert, tramObertDe,
} from './tramObertCore.js'

const tram = (extra = {}) => ({
  id: 5, model_task: 42, inici: '2026-08-05T10:00:00Z', fi: null,
  last_heartbeat: null, origen: 'mesurat', ...extra,
})
const tasca = (extra = {}) => ({ id: 42, status: 'InProgress', ...extra })

/** Font amb els dos lectors injectats i un cablatge de mentida que només compta. */
function font({ llista, llegeix } = {}) {
  const comptes = { arrencades: 0, aturades: 0, sondeigs: 0 }
  const f = creaFontTramObert({
    llistaTrams: () => { comptes.sondeigs += 1; return (llista ?? (() => ({ data: [] })))() },
    llegeixTasca: id => (llegeix ?? (() => ({ data: tasca() })))(id),
    arrenca: () => { comptes.arrencades += 1 },
    atura: () => { comptes.aturades += 1 },
  })
  return { f, comptes }
}

const rebuts = f => { const r = []; f.subscriu(v => r.push(v)); return r }

// ── Els quatre estats ────────────────────────────────────────────────────────

test('sense cap tram obert emet CAP', async () => {
  const { f } = font({ llista: () => ({ data: { results: [] } }) })
  const r = rebuts(f)
  await f.refresca()
  assert.equal(r.at(-1).estat, CAP)
})

test('un tram TANCAT no és un tram obert: emet CAP', async () => {
  const { f } = font({ llista: () => ({ data: [tram({ fi: '2026-08-05T11:00:00Z' })] }) })
  const r = rebuts(f)
  await f.refresca()
  assert.equal(r.at(-1).estat, CAP)
})

test('amb tram obert emet OBERT amb el tram I la seva tasca', async () => {
  const { f } = font({ llista: () => ({ data: { results: [tram()] } }) })
  const r = rebuts(f)
  await f.refresca()
  const ultim = r.at(-1)
  assert.equal(ultim.estat, OBERT)
  assert.equal(ultim.tram.id, 5)
  assert.equal(ultim.tasca.status, 'InProgress')
})

test('si la LLISTA falla emet ERR_LLISTA i no rebutja', async () => {
  const { f } = font({ llista: () => { throw new Error('xarxa') } })
  const r = rebuts(f)
  await f.refresca()
  assert.equal(r.at(-1).estat, ERR_LLISTA)
})

test('si la TASCA falla emet ERR_TASCA, amb el tram que sí que s\'ha llegit', async () => {
  const { f } = font({
    llista: () => ({ data: [tram()] }),
    llegeix: () => Promise.reject(new Error('404')),
  })
  const r = rebuts(f)
  await f.refresca()
  assert.equal(r.at(-1).estat, ERR_TASCA)
  assert.equal(r.at(-1).tram.id, 5)
})

// ── EL CAS QUE NO ES POT PERDRE EN CONVERGIR ─────────────────────────────────
// El guard es manté armat quan la xarxa cau i la píndola s'amaga. Això només és possible si
// «no hi ha tram» i «no ho he pogut saber» són estats DIFERENTS. Un `null` per a tots dos
// obligaria els dos consumidors a la mateixa reacció i el guard es desarmaria a cada GET fallit
// — justament quan hauria de comptar.
test('«no hi ha tram» i «no ho sé» NO són el mateix estat', async () => {
  const { f: fCap } = font({ llista: () => ({ data: [] }) })
  const rCap = rebuts(fCap)
  await fCap.refresca()

  const { f: fErr } = font({ llista: () => { throw new Error('xarxa') } })
  const rErr = rebuts(fErr)
  await fErr.refresca()

  assert.notEqual(rCap.at(-1).estat, rErr.at(-1).estat)
})

// Un tram obert damunt d'una tasca que NO és En curs (zombi) s'emet igualment: filtrar-lo aquí
// amagaria als consumidors un fet que cadascun ha de poder tractar a la seva manera — el guard
// se'n rendeix i l'apunta, `estatSessio` simplement no pinta.
test('un tram zombi (tasca no InProgress) s\'emet: el filtre és del consumidor', async () => {
  const { f } = font({
    llista: () => ({ data: [tram()] }),
    llegeix: () => ({ data: tasca({ status: 'Paused' }) }),
  })
  const r = rebuts(f)
  await f.refresca()
  assert.equal(r.at(-1).estat, OBERT)
  assert.equal(r.at(-1).tasca.status, 'Paused')
})

// ── L'ordre de les RESPOSTES, no el de les peticions ─────────────────────────

test('una resposta endarrerida no pot sobreescriure una de més nova', async () => {
  let torn = 0
  const { f } = font({
    llista: () => {
      torn += 1
      // La 1a consulta triga i diu que hi ha un tram; la 2a és immediata i diu que no.
      if (torn === 1) {
        return new Promise(res => setTimeout(() => res({ data: [tram()] }), 20))
      }
      return { data: [] }
    },
  })
  const r = rebuts(f)
  const lenta = f.refresca()
  await f.refresca()          // la que s'ha demanat DESPRÉS acaba ABANS
  assert.equal(r.at(-1).estat, CAP)
  await lenta                 // …i quan arriba la lenta, no torna enrere
  assert.equal(r.at(-1).estat, CAP)
})

// ── El sondeig viu només mentre hi ha algú escoltant ─────────────────────────

test('un sol sondeig per als dos consumidors, i para en marxar l\'últim', async () => {
  const { f, comptes } = font()
  const baixaA = f.subscriu(() => {})
  const baixaB = f.subscriu(() => {})
  assert.equal(comptes.arrencades, 1, 'el segon subscriptor no arrenca un segon rellotge')
  baixaA()
  assert.equal(comptes.aturades, 0, 'amb algú escoltant encara, no para')
  baixaB()
  assert.equal(comptes.aturades, 1)
})

test('el subscriptor que arriba tard rep l\'últim resultat sense esperar', async () => {
  const { f } = font({ llista: () => ({ data: [tram()] }) })
  f.subscriu(() => {})
  await f.refresca()
  const tardans = []
  f.subscriu(v => tardans.push(v))
  assert.equal(tardans.length, 1)
  assert.equal(tardans[0].estat, OBERT)
})

test('en marxar l\'últim s\'oblida el resultat: cap foto vella servida com si fos d\'ara', async () => {
  const { f } = font({ llista: () => ({ data: [tram()] }) })
  const baixa = f.subscriu(() => {})
  await f.refresca()
  assert.equal(f.ultim.estat, OBERT)
  baixa()
  assert.equal(f.ultim, null)
})

// ── La lectura de la llista ──────────────────────────────────────────────────

test('llegeix igual una resposta paginada que una llista pelada', () => {
  assert.equal(tramObertDe({ data: { results: [tram()] } }).id, 5)
  assert.equal(tramObertDe({ data: [tram()] }).id, 5)
  assert.equal(tramObertDe({ data: null }), null)
  assert.equal(tramObertDe(undefined), null)
})
