// QUÈ PINTA UNA FILA DE LA DEFINICIÓ D'UNA PEÇA — SET-2/T7-B1.
//
// El contracte de `GET /models/<id>/peces/` serveix cada camp heretable com
// `{valor, etiqueta, heretat}`, i el docstring de `garment_views.py` és explícit sobre les
// tres coses que cal entendre abans de pintar-ho:
//
//   · `valor` ÉS SEMPRE L'EFECTIU. Si la peça no declara res, hi arriba el del model JA RESOLT.
//   · `heretat` diu D'ON VE, no si n'hi ha. «Hereta S·M·L» i «declara S·M·L» pinten el mateix
//     text i NO són el mateix estat: per això calen els dos camps i no un.
//   · `etiqueta` és per pintar i no és identitat. Qui desi o compari, que faci servir `valor`.
//
// ⚠️ EL FRONT NO RESOL HERÈNCIES. Aquest mòdul no fa cap `peca.X || model.X`: aquella frase és
// codi UNA vegada, a `services_garment.valor_efectiu`, i el motiu és el revert de `7cc133b5`
// —una vora que serveix el valor cru al costat d'una altra que serveix el resolt són dos
// orígens per al mateix camp—. Aquí només es tria COM es diu el que ja ve resolt.
//
// I el buit també és informació: una peça sense joc de graduació ha de dir que no en té, no
// desaparèixer de la llista. Per això `buit` és un estat i no l'absència de la fila.

/** El camp d'un contracte que encara no ha arribat (peça sense dades) es llegeix com a buit. */
const CAMP_BUIT = { valor: null, etiqueta: '', heretat: false }

/**
 * Com s'ha de llegir un camp resolt: el text que hi va i d'on ve.
 *
 * Retorna `{ text, heretat, buit }`. `text` és `''` quan no hi ha valor enlloc — qui pinti hi
 * posarà el seu «—», que és decisió de pantalla i no d'aquí.
 */
export function presentacioCamp(camp) {
  const c = camp || CAMP_BUIT
  const text = c.etiqueta || ''
  return {
    text,
    heretat: c.heretat === true,
    // `valor` i no `etiqueta`: un valor pot existir amb etiqueta buida (un FK sense `__str__`
    // útil), i llavors la fila té contingut encara que no tingui text.
    buit: c.valor === null || c.valor === undefined || c.valor === '',
  }
}

/**
 * El nom que encapçala el contenidor d'una peça.
 *
 * La mare no és «una peça sense nom»: és el model. Per això no s'hi cau amb un `||` sinó que
 * es decideix per `es_mare`, que és el que el contracte afirma.
 */
export function nomDeLaPeca(peca, etiquetaMare) {
  if (peca?.es_mare) return etiquetaMare
  return peca?.nom || peca?.codi || ''
}

/**
 * L'ancla d'una peça dins del Resum, per a l'enllaç que hi porta des de Mesures.
 *
 * La mare porta el seu propi codi buit i, per tant, `#peca-`, que seria una ancla sense nom:
 * se li dona `base`. El codi d'una peça (`'02'`) ja és estable i únic dins del model.
 */
export function anclaDeLaPeca(peca) {
  return `peca-${peca?.es_mare || !peca?.codi ? 'base' : peca.codi}`
}

/**
 * D'ON VE el que una fila ensenya. TRES estats, i el tercer no és una variant del segon.
 *
 *   `propi`      la peça ho declara.
 *   `heretat`    el contracte diu `heretat: true` — el valor és del model I EL SEGUIRÀ: si el
 *                model canvia, això canvia. És un vincle viu, i el pinta el mecanisme d'herència.
 *   `del_model`  informació DEL MODEL mostrada a títol de CONTEXT, en una fila que la peça no
 *                pot canviar mai perquè el contracte nega que aquell camp hi baixi (els eixos i
 *                el `garment_type_item`: v. `ElGarmentTypeItemNoHiEsTest`).
 *
 * ⚠️ LA DIFERÈNCIA NO ÉS DE MATÍS. «Hereta» és una FRASE SOBRE UN OVERRIDE que existeix i que
 * ara mateix és NULL —i que algun dia pot deixar de ser-ho—. «Del model» és una frase sobre un
 * camp que NO existeix a la peça i que no en tindrà. Dir «hereta» d'això últim prometria una
 * porta d'edició que no ha d'arribar mai, i el dia que algú la busqués no la trobaria.
 */
export const ORIGEN = { PROPI: 'propi', HERETAT: 'heretat', DEL_MODEL: 'del_model' }

export function origenDeLaFila(camp, { delModel = false } = {}) {
  if (delModel) return ORIGEN.DEL_MODEL
  return presentacioCamp(camp).heretat ? ORIGEN.HERETAT : ORIGEN.PROPI
}

/**
 * El codi que es PROPOSA per a la peça següent — SET-2/T7-B3.
 *
 * La mare és conceptualment la '01' i no té fila (D3), o sigui que la primera peça de debò és
 * la '02'. Es proposa el següent del MÀXIM numèric, no el següent del recompte: en un model on
 * la '02' s'ha esborrat i la '03' viu, comptar donaria '03' i xocaria (409 `garment_duplicat`).
 *
 * ⚠️ ÉS UNA PROPOSTA, NO UNA RESERVA. El camp queda editable i el codi el valida el servidor:
 * dues pestanyes obertes poden proposar el mateix i la segona rebrà el seu 409, que és
 * exactament el que aquell codi d'error existeix per dir. Aquí no s'hi endevina res més.
 *
 * Els codis no numèrics ('CAP', 'MANIGA') no participen del càlcul —no tenen «següent»— però
 * tampoc el trenquen: es proposa a partir dels que sí que en tenen.
 */
export function seguentCodiDePeca(peces) {
  const nums = (peces || [])
    .filter(p => !p?.es_mare)
    .map(p => String(p?.codi ?? ''))
    .filter(c => /^\d+$/.test(c))
    .map(Number)
  // L'1 hi entra sempre com a terra: la mare l'ocupa encara que no tingui fila.
  const seguent = Math.max(1, ...nums) + 1
  return String(seguent).padStart(2, '0')
}
