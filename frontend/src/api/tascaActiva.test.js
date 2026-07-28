// K6 capa 1 — la decisió de pausar la tasca En curs en tancar la sessió.
//     cd frontend && node --test src/api/tascaActiva.test.js
//
// LA LLEI: marxar de la feina no és acabar-la (Paused, mai Done), i intentar-ho no pot
// bloquejar mai la sortida de qui està tancant la sessió.

import assert from 'node:assert/strict'
import { test } from 'node:test'

import { creaPausador } from './tascaActivaCore.js'

/** Pausador de joguina: registra què s'ha enviat i amb quin token. */
function fesPausador({ token = 'access-viu', resposta = true } = {}) {
  const enviats = []
  const pausador = creaPausador({
    llegeixToken: () => token,
    envia: (id, tk) => {
      enviats.push({ id, token: tk })
      if (resposta instanceof Error) return Promise.reject(resposta)
      return Promise.resolve(resposta)
    },
  })
  return { pausador, enviats }
}

test('logout voluntari amb tasca En curs → es demana Paused per a AQUELLA tasca', async () => {
  const { pausador, enviats } = fesPausador()
  pausador.recorda(152)

  assert.equal(await pausador.pausa(), true)
  assert.deepEqual(enviats, [{ id: 152, token: 'access-viu' }])
})

test('sense tasca En curs no s\'envia res', async () => {
  const { pausador, enviats } = fesPausador()
  assert.equal(await pausador.pausa(), false)
  assert.equal(enviats.length, 0)

  pausador.recorda(7)
  pausador.recorda(null)   // el guard diu que ja no n'hi ha cap
  assert.equal(await pausador.pausa(), false)
  assert.equal(enviats.length, 0)
})

test('sense token no s\'inventa cap crida', async () => {
  const { pausador, enviats } = fesPausador({ token: null })
  pausador.recorda(152)
  assert.equal(await pausador.pausa(), false)
  assert.equal(enviats.length, 0)
})

test('pausada amb èxit → s\'oblida (no es pausa dos cops)', async () => {
  const { pausador, enviats } = fesPausador()
  pausador.recorda(152)
  await pausador.pausa()
  assert.equal(pausador.id, null)

  assert.equal(await pausador.pausa(), false)
  assert.equal(enviats.length, 1, 'la segona crida no ha de sortir')
})

test('LA PARADOXA DEL TOKEN: 401 amb sessió morta → false en silenci, mai llança', async () => {
  const { pausador } = fesPausador({ resposta: false })
  pausador.recorda(152)

  // Si això llancés, `tancaSessio` es quedaria a mitges i la persona no arribaria a /login.
  assert.equal(await pausador.pausa(), false)
  // La tasca NO s'oblida: segueix En curs i el cron l'ha de poder recollir (capa 2).
  assert.equal(pausador.id, 152)
})

test('xarxa caiguda → false en silenci, i la tasca es recorda igualment', async () => {
  const { pausador } = fesPausador({ resposta: new Error('network down') })
  pausador.recorda(152)
  assert.equal(await pausador.pausa(), false)
  assert.equal(pausador.id, 152)
})
