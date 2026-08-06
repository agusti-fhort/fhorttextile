import test from 'node:test'
import assert from 'node:assert/strict'

import { targetDerivable, targetsDeLaFamilia } from './derivaTarget.js'

// Perfils REALS de `fhort` (SELECT del 06/08). Les dues primeres famílies són el cas que va
// fabricar el model 1307: serveixen adults i nens, i el catàleg posava KID_BOY al davant.
const PERFILS = {
  // 6 perfils, 6 públics: samarretes de dona, home, nen, nena i adolescents.
  JERSEY_TOPS: ['KID_BOY', 'KID_GIRL', 'MAN', 'TEEN_BOY', 'TEEN_GIRL', 'WOMAN'],
  TAILORED_PANTS: ['KID_BOY', 'MAN', 'TEEN_BOY', 'TEEN_GIRL', 'WOMAN'],
  SWIMWEAR: ['TEEN_GIRL'],                       // unívoca
  NEWBORN: ['BABY_GIRL', 'NEWBORN_GIRL'],
  SENSE_PERFILS: [],
}
const perfilsDe = (nom) => PERFILS[nom].map((codi, i) => ({ id: i, target: { codi } }))

test('família amb més d’un públic: NO es deriva res', () => {
  assert.equal(targetDerivable(perfilsDe('JERSEY_TOPS')), null)
  assert.equal(targetDerivable(perfilsDe('TAILORED_PANTS')), null)
  assert.equal(targetDerivable(perfilsDe('NEWBORN')), null)
})

test('família unívoca: es deriva el seu', () => {
  assert.equal(targetDerivable(perfilsDe('SWIMWEAR')), 'TEEN_GIRL')
})

test('el mateix target repetit en diversos perfils segueix sent unívoc', () => {
  // Una família pot tenir un perfil per construcció o per fit amb el MATEIX públic: això no
  // és ambigüitat, és el mateix target dit tres vegades.
  const perfils = [{ target: { codi: 'WOMAN' } }, { target: { codi: 'WOMAN' } },
                   { target: { codi: 'WOMAN' } }]
  assert.equal(targetDerivable(perfils), 'WOMAN')
})

test('sense perfils, sense res a derivar', () => {
  assert.equal(targetDerivable(perfilsDe('SENSE_PERFILS')), null)
  assert.equal(targetDerivable(undefined), null)
})

test('els perfils sense target no compten com a públic', () => {
  // `SizingProfile.target` és FK PROTECT, però la llista arriba del serializer i un `null` no
  // pot fer que una família unívoca sembli ambigua.
  const perfils = [{ target: null }, { target: { codi: 'MAN' } }, {}]
  assert.deepEqual(targetsDeLaFamilia(perfils), ['MAN'])
  assert.equal(targetDerivable(perfils), 'MAN')
})

test('l’ordre de la llista no decideix res', () => {
  // El defecte vell agafava el primer: amb l'ordre invertit hauria donat un target diferent
  // per a la MATEIXA família. Ara les dues llistes es comporten igual.
  const endavant = perfilsDe('JERSEY_TOPS')
  const enrere = [...endavant].reverse()
  assert.equal(targetDerivable(endavant), targetDerivable(enrere))
})
