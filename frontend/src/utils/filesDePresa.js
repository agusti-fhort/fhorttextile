// LES FILES DEL MODE `presa` DE L'EINA `mesures` — la llei, fora del JSX (S42/G8).
//
// D'ON VE: vivia dins de `CheckMeasureEditor` com un `.map()` enmig del cos del component
// (`rowsPresa`), i per això no tenia banc: `node --test` no pot importar un `.jsx`. És el
// TERCER cop que aquesta casa paga el mateix preu —`calFilaDePeca` i `motiuPasPresa` van
// sortir del JSX pel mateix motiu.
//
// ⚠️ PER QUÈ NO N'HI HA PROU QUE EN TINGUI EL FILTRE: el que reparteix aquestes files entre
// contenidors (`filesDeLaPeca`) SÍ que tenia banc, i passava. Un banc que cobreix la funció
// compartida i deixa els seus ALIMENTADORS sense cobrir dona seguretat falsa. La pregunta bona
// no és «qui filtra malament» sinó «qui construeix les files que arriben al filtre».
//
// AQUEST COMMIT NO CANVIA CAP COMPORTAMENT: és el trasllat, literal, perquè el següent pugui
// ser vermell abans de ser verd.
//
// QUÈ ÉS AQUESTA TAULA. La font `check` deixa de construir columnes i serveix FILES amb la
// forma que la taula de mesures ja entén: identitat (capa · instància · prenda · nomenclatura
// · nom) + la presa + la base vigent. QUÈ HI HA DEIXAT DE SORTIR, i per què: el RÈGIM, la Δ,
// el break i «a partir de» (prendre una mesura no és editar la regla de graduació), la
// TOLERÀNCIA, i el vocabulari de fitting —«REAL (PROTO)» i «DECISIÓ · NOTA»—, que és d'una
// altra eina. Ordre d'Agus, 05/08.
//
//     node --test frontend/src/utils/filesDePresa.test.js

// ⚠️ Amb extensió: aquest mòdul l'ha de poder importar `node --test`, que no resol
// l'extensió implícita com fa Vite (mateixa convenció que `taulaBruta.js` i `grupsDelFull.js`).
import { clauRegla } from './identitatMesura.js'

/**
 * Construeix les files de la taula de mesures en mode presa/consulta.
 *
 * Funció PURA: no toca React, no llegeix res de fora i no muta els arguments.
 *
 * @param {object}  args
 * @param {Array}   args.baseRows     files de `base-stages` (`raw.baseData.rows`)
 * @param {Array}   args.linies       línies del SizeCheck obert (`raw.check.lines`), si n'hi ha
 * @param {Map}     args.reglaPerPom  Map<pom_id, {logica, increment_base, …}> per a les
 *                                    columnes de lectura de la consulta
 * @param {boolean} args.readOnly     consulta (`true`) o presa en curs (`false`)
 * @returns {Array} les files, en el mateix ordre que `baseRows`
 */
export function construeixFilesDePresa({ baseRows, linies, reglaPerPom, readOnly }) {
  const regles = reglaPerPom || new Map()
  return (baseRows || []).map(r => {
    const line = (linies || []).find(
      l => l.base_measurement_id != null && l.base_measurement_id === r.base_measurement_id)
    return {
      // La taula indexa per `row.id`, que és el que fa servir per saber si una fila ja viu a la
      // BD (el bateig hi penja). Aquí SEMPRE hi viu: la presa no inventa mesures.
      id: r.base_measurement_id,
      lineId: line?.id ?? null,
      pom_id: r.pom_id, pom_code: r.pom_code,
      capa: r.capa, instancia: r.instancia,
      // SET-2/T7-B8 · S42/F5 — L'EIX DE PRENDA, que és el que reparteix la fila entre
      // contenidors (`filesDeLaPeca`, cridat des de `CheckMeasureEditor`). Els altres tres
      // adaptadors de files el copien des de T7-B7 i aquest s'hi va quedar fora; `base-stages`
      // el serveix des de R11, o sigui que el camp hi era i el que faltava era recollir-lo.
      //
      // ⚠️ SENSE AQUESTA LÍNIA EL FORAT ÉS MUT, i per això va viure quatre dies. `filesDeLaPeca`
      // fa `(f.garment || '') === eix`, i `undefined || ''` és `''`: una fila sense eix no es
      // perd ni peta — se'n va al contenidor de la MARE com si fos seva, i el de la peça queda
      // amb el capçal i res més. Cap error, cap avís, cap rastre. El filtre no pot distingir
      // «és de la mare» de «algú l'ha deixat caure pel camí», i per això qui ho ha de garantir
      // és qui construeix la fila: aquí.
      garment: r.garment,
      nom_fitxa: r.nom_fitxa || '',
      nom_en: r.nom_en, nom_ca: r.nom_ca,
      nom_canonic_model: r.nom_canonic_model || '',
      nom_traduit_model: r.nom_traduit_model || '',
      is_key: r.is_key,
      // EL CARRIL PORTA LA PRESA, no la base: és el número que la modista escriu avui.
      //
      // …PERÒ EN CONSULTA NO HI HA PRESA. La «Taula de mesures» és una pantalla de LECTURA del
      // model: la pregunta que ve a respondre és quina base té la fitxa, no què s'està mesurant
      // avui. Llegint `line.valor_real`/`line.valor_teoric` també aquí, la consulta depenia d'un
      // SizeCheck obert: un model amb els valors gravats a Definició POM i sense cap check
      // (MILEY, BRW-SS26-0003 — 12 files MANUAL amb valor i zero SizeCheck) ensenyava les files
      // correctes i les dues columnes a «—». Les files arribaven perquè vénen de `base_stages`;
      // els valors no, perquè venien de l'altra banda.
      //
      // La font primària és `BaseMeasurement`, i `base_stages_view` ja la serveix a
      // `base_value_cm` (`models_app/views.py:3517`); el seu propi docstring fixa la semàntica:
      // «l'últim estadi coincideix amb la base vigent (BaseMeasurement)» (`:3418`). O sigui que
      // en consulta les dues columnes són la MATEIXA cosa, i és aquesta.
      //
      // El mode presa NO canvia: amb `readOnly=false` el carril segueix portant `valor_real` i la
      // base vigent segueix sent el `valor_teoric` que el check va congelar en obrir-se — que és
      // el que la presa ha de comparar, i no s'ha de moure mentre es pren.
      base_value_cm: readOnly ? (r.base_value_cm ?? null) : (line?.valor_real ?? null),
      // LA REGLA, per a les quatre columnes de lectura de la consulta. Es creua per `pom_id` i
      // no pels eixos a posta: `ModelGradingRule` no porta capa ni instancia (decisio de domini
      // amb acta —mateix POM, mateix increment a totes les cares—), o sigui que dues germanes
      // COMPARTEIXEN regla i han de sortir amb la mateixa. Creuar per la fila donaria buit.
      //
      // ✅ I EL GARMENT SÍ QUE HI ENTRA (S42/F1 · Q1-bis, 17/08). Aquí hi havia un 🚩 que
      // deia que la clau curta col·lapsa i que el contenidor de la 02 ensenya la llei de la
      // mare. Ja no: la clau és `(pom, garment)` via `clauRegla`, que és el punt únic que sap
      // com s'aplana la identitat d'una REGLA (i que NO és `identitatMesura` retallada —capa i
      // instància no hi entren, perquè són eixos de germanor i comparteixen llei).
      // El backend hi arriba per la mateixa passada: `taula-mesures` serveix la regla amb
      // `_regla_de(_load_grading_rules_per_garment(...))`, que hereta de la mare quan la peça
      // no en té de pròpia.
      ...(regles.get(clauRegla(r)) || {}),
      // …i al costat, la base VIGENT, que és contra el que es mesura.
      base_vigent: readOnly ? (r.base_value_cm ?? null) : (line?.valor_teoric ?? null),
    }
  })
}
