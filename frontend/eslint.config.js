import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

// PORTA DE LINT (Taller · W5). `npm run lint` entra al VERD de tot sprint de frontend.
//
// La lliçó de W4/T5: el build va passar VERD i la pàgina petava en obrir-se amb
// 'voraIman is not defined'. Rollup no es queixa d'un identificador que no existeix dins d'un
// component —no és feina seva—, i per tant **un verd de build no és un verd de producte**. El
// lint SÍ que ho caça: `no-undef` (de js.configs.recommended) l'hauria aturat abans d'arribar
// a cap pantalla. La regla ja hi era. El que faltava era que algú l'executés.
//
// I no s'executava perquè no es podia: `npm run lint` donava 174 errors, i una porta que mai
// no és verda no és una porta, és soroll. Per això aquí es decideix, explícitament, QUÈ atura
// un sprint i què només s'anota:
//
//   · ERROR (atura) — CORRECCIÓ. Codi que no pot funcionar o que amaga una feina a mitges:
//     `no-undef` (el de W4/T5), `no-const-assign`, `no-unused-vars`,
//     `no-constant-binary-expression`, `no-empty`… Tot ve de `js.configs.recommended` i es
//     queda com a error. També `react-hooks/rules-of-hooks`: cridar un hook dins d'un `if`
//     és un error de debò, no una opinió.
//
//   · WARNING (s'anota) — IDIOMA i DX. Consells del plugin de hooks v7 sobre com escriure
//     millor React (setState dins d'un effect, memoització, refs) i la regla de Fast Refresh,
//     que parla del HMR del `vite dev`, no del producte. Són avisos honestos i val la pena
//     anar-los pagant, però **no són defectes**: posar-los a la porta hauria volgut dir o bé
//     refactoritzar mig frontend en aquest sprint o bé deixar la porta desactivada un altre
//     cop. Es mantenen visibles perquè es puguin anar tancant, sense bloquejar.
//
// El dia que els avisos baixin a zero, es pugen a error i s'hi queden.
const IDIOMA_I_DX = {
  // Consells del plugin de hooks v7: com escriure millor React, no codi trencat.
  'react-hooks/set-state-in-effect': 'warn',
  'react-hooks/refs': 'warn',
  'react-hooks/immutability': 'warn',
  'react-hooks/static-components': 'warn',
  'react-hooks/purity': 'warn',
  'react-hooks/preserve-manual-memoization': 'warn',
  // Fast Refresh: afecta el HMR del servidor de desenvolupament, no el producte.
  'react-refresh/only-export-components': 'warn',
}

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    rules: {
      ...IDIOMA_I_DX,
      // Un argument que no es fa servir sovint és part d'una signatura (un handler que rep
      // l'event i no el mira), i un `catch (e)` que no mira l'error és un patró viu del codi.
      // El que no té excusa és una variable local morta: sol ser una feina a mitges.
      'no-unused-vars': ['error', {
        args: 'none',
        caughtErrors: 'none',
        varsIgnorePattern: '^_',    // `_alguna_cosa` = "ja sé que no la faig servir"
      }],
    },
  },
])
