// ELS INTERRUPTORS DE DESPLEGAMENT DEL FRONT — un sol lector d'`import.meta.env`.
//
// PER QUÈ BUILD-TIME I NO UNA CRIDA AL SERVIDOR
// ---------------------------------------------
// La casa ja té un canal servidor→front, `user.capabilities` (`store/auth.js:86`, servit per
// `MeSerializer`), i NO és aquest. Una capability és per PERSONA: surt del rol, es pot atorgar
// i revocar individualment des de la matriu de `/configuracio/usuaris`, i la seva llista és
// l'ordre de les columnes d'aquella pantalla. Un interruptor de DESPLEGAMENT no és res d'això:
// no es regala a ningú ni se li treu, i posar-lo a la matriu hi obriria una columna falsa que
// un admin podria commutar per error. El `tenant-config` tampoc serveix: és per TENANT i viu
// a la BD, i el que s'apaga a PROD s'apaga per a tot PROD.
//
// L'única via que existeix per a una dada de desplegament és la de build (`import.meta.env`), i
// ja és la que la casa fa servir per a exactament això: `VITE_STAGING` (`layout/Sidebar.jsx:263`)
// distingeix staging de producció, i `VITE_API_URL` (`api/base.js:21`) diu on és l'API.
// Conseqüència operativa, i no és menor: **la variable ha d'estar posada ABANS del `npm run
// build`**; canviar-la després no mou el `dist` ja construït.
//
// EL DEFAULT ÉS LA XARXA DE SEGURETAT
// ------------------------------------
// Absent val ENCÈS, igual que al backend (`settings.FTT_PATTERNS_ENABLED`). Un entorn que no
// digui res no pot perdre el motor per descuit: `vite build` corre en mode `production` i només
// llegeix `.env` i `.env.production` —cap dels dos existeix avui al repo—, de manera que «cap
// valor» és l'estat NORMAL d'un build d'aquesta casa, no una anomalia. Només s'apaga qui ho
// escriu, i s'apaga amb les mateixes paraules que accepta el backend.
//
// `import.meta.env?.` amb interrogant perquè aquest mòdul es pugui importar des d'un banc de
// `node --test`, on `import.meta.env` no existeix.
const APAGAT = ['0', 'false', 'no']

/** ¿El motor de patrons és visible en aquest desplegament? Absent → sí. */
export const PATTERNS_ENABLED = !APAGAT.includes(
  String(import.meta.env?.VITE_FTT_PATTERNS_ENABLED ?? 'true').toLowerCase(),
)
