import { create } from 'zustand'

/**
 * LA CUA DEL MOLLA DE PA (NORMA_LAYOUT §8b · ordre d'Agus del 08/08 al bloc B).
 *
 * El breadcrumb de la top bar es dedueix de `navGroups`, i per a una llista això n'hi ha prou:
 * «Tenant › Projectes › Models» diu tot el que hi ha per dir. Però dins d'una ENTITAT ja no:
 * `/models/1319?tab=Mesures` és, mirat des del router, exactament la mateixa ruta que
 * `/models/1319`, i el molla les diria igual. Qui obre la pantalla de Mesures d'un model no
 * sap, llegint la barra, ni de quin model és ni què hi està mirant.
 *
 * L'ordre és de QUATRE segments: **Tenant › Models › {NOM DEL MODEL} › {Secció}**, i l'últim
 * només si l'entitat té seccions. La CUA (els segments a partir del tercer) no es pot deduir
 * de la ruta: la sap la pantalla, que és qui ha carregat l'entitat i qui sap en quina secció
 * està. Per això la publica aquí i la top bar la llegeix.
 *
 * ⚠️ EL SEGMENT DE GRUP CEDEIX EL LLOC. Amb cua, la barra passa de
 * «Tenant › Projectes › Models» a «Tenant › Models › {NOM} › {Secció}»: el nom del GRUP del
 * menú lateral («Projectes») en surt. Cinc segments no són un molla de pa, són una frase, i
 * l'ordre en nomena quatre i diu quins.
 *
 * Qui la publica, la neteja. `<Topbar>` no pot saber quan una pantalla ha marxat, i una cua
 * òrfena diria el nom d'un model a la pantalla d'un altre lloc: el `useEffect` de la pantalla
 * la buida al desmuntar-se.
 */
const useMolla = create((set) => ({
  /** @type {Array<{text: string, to?: string}>} — segments a partir del tercer */
  cua: [],
  setCua: (cua) => set({ cua }),
  netejaCua: () => set({ cua: [] }),
}))

export default useMolla
