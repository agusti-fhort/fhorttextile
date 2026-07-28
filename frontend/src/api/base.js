/**
 * BASE URL — SAME-ORIGIN per defecte.
 *
 * Abans el baseURL era `import.meta.env.VITE_API_URL` a seques, i `.env` hi posava un
 * domini ABSOLUT (p.ex. `https://staging.fhorttextile.tech`). Conseqüència estructural:
 * el build quedava CABLEJAT a un domini, i qualsevol altre host que servís el mateix
 * `dist/` enviava igualment les crides al domini cablejat — amb el Host equivocat, que
 * amb django-tenants vol dir el TENANT equivocat. D'aquí naixia la necessitat de tenir
 * un build per domini (`dist-tenants/`) i d'obrir CORS cap a l'origen cablejat.
 *
 * Ara el defecte és RELATIU (`''`): la crida cau sobre l'origen que ha servit la pàgina,
 * el Host real viatja tal qual i UN SOL build serveix qualsevol domini/tenant. És el
 * mateix patró que `tenantDiscovery.submit` (endpoints.js) ja feia a posta.
 *
 * `VITE_API_URL` sobreviu com a OVERRIDE opcional: si està definit i no és buit, mana
 * (cas del dev local, on el front va a :5173 i el back a :8000 → `.env.development`).
 *
 * Viu en un mòdul propi (i no a `client.js`) perquè `sessio.js` el necessita i `client.js`
 * depèn de `sessio.js`: si el compartissin, seria un cicle d'imports.
 */
export const apiBaseURL = import.meta.env.VITE_API_URL || ''
