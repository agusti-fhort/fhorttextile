// LA IDENTITAT D'UNA MESURA, per agrupar files al frontend — punt únic.
//
// C4/BLOC 1-BIS. Les superfícies que reben una llista PLANA de línies (una per POM i talla,
// o per POM i esdeveniment) i n'han de fer FILES agrupen per `pom_id`. Des que una mesura pot
// tenir dues cares —la mateixa al folre i a l'exterior, la sisa esquerra i la dreta— això
// deixa de ser una clau: dues línies hi cauen a sobre i el `Map` en descarta una en silenci.
// La fila desapareix de la pantalla i res no ho anuncia.
//
// Els payloads ja porten `capa` i `instancia` a cada línia (`fitting/serializers.py`,
// `repas_views`, `serializers_size_check`, `base-measurements/`). Això només els ajunta.
//
// ⚠️ AIXÒ NO ÉS LA CLAU DEL CONTRACTE. La clau de payload —`{pom}|{capa}|{instancia}`, la
// que fan servir `deltes` i `cells` per indexar un objecte JSON— la decideix el BACKEND i
// només ell (`pom/identitat.py`). Aquesta d'aquí és una clau de `Map` interna del client:
// no viatja, no es desa i no es compara mai amb res que vingui del servidor. Es manté
// separada a posta, perquè el dia que el backend canviï la seva forma no s'arrossegui res
// del front, i perquè ningú no tingui la temptació de construir la del contracte aquí.
//
// Qui hagi d'ENVIAR la identitat al servidor no ha de fer servir això: els tres camps van
// per separat al cos de la petició, que és el que mana `pom/identitat.py`.

// SET-2/T6b — EL GARMENT ENTRA, I ENTRA L'ÚLTIM. Des que una mesura pot viure a dues PRENDES
// del mateix model, `{pom}|{capa}|{instancia}` torna a ser insuficient pel mateix motiu que
// el `pom_id` sol ho va deixar de ser: dues files hi cauen a sobre i el `Map` en descarta una.
//
// L'últim, i no el primer, per la mateixa raó que `pom/identitat.py` (T6a): la clau és
// IDENTITAT, no jerarquia. Que la prenda sigui l'eix de fora mana l'AGRUPACIÓ i l'ORDRE, que
// viuen als partidors de taules, no l'ordre dels trams d'un token pla. I afegir al final és el
// canvi que menys demana als seus consumidors.
//
// Els quatre trams SEMPRE: `12|exterior||` i `12|exterior|` serien la mateixa mesura escrita de
// dues maneres. La PEÇA MARE és el tram buit, mai absent — igual que al backend.

/** Clau d'agrupació d'una línia o fila per la mesura a què pertany. */
export function identitatMesura(fila) {
  return `${fila.pom_id}|${fila.capa || ''}|${fila.instancia || ''}|${fila.garment || ''}`
}

/**
 * La clau de FILA per a `MeasureGrid`: la identitat més forta que el payload dona.
 *
 * La PK de `BaseMeasurement` mana quan hi és —la taula és única per (model, pom, capa,
 * instancia, garment), o sigui que la PK ja és tot això resolt i no cal recompondre res—, i
 * quan el payload no la serveix, el pla B són els quatre eixos. MAI el `pom_id` sol: aquell
 * era el pla B d'abans que una mesura pogués tenir dues cares, i col·lapsa germanes AVUI.
 *
 * La PK s'hi passa a part perquè cada payload li diu d'una manera (`bm_id` al fitting,
 * `base_measurement_id` al check): la regla viu aquí, el nom del camp al lloc que el llegeix.
 * I es compara amb `??` i no amb `||` perquè una PK no és mai «falsa»: només absent.
 */
export function clauDeFila(fila, pk) {
  return pk ?? identitatMesura(fila)
}

/**
 * LES FILES D'UNA PRENDA — SET-2/T7-B8 (el repartiment client-side).
 *
 * `taula-mesures` i `base-stages` NO filtren per peça (no tenen cap paràmetre per fer-ho):
 * serveixen totes les files del model amb el seu eix, i qui les reparteix per contenidor és la
 * pantalla. Aquesta funció és aquell repartiment, en un sol lloc.
 *
 * ⚠️ `eix` = `null` vol dir **encara no ho sabem** —`/peces/` no ha contestat, o ha fallat— i
 * llavors hi són TOTES. És la mateixa llei que `PecesDelModel` ja aplica al contenidor: el
 * pitjor que pot passar si la segona crida no arriba és no veure la fila de peça, mai no veure
 * la feina. Filtrar per un eix que no coneixem buidaria la taula d'un model sencer.
 *
 * La MARE és `''`, i és un valor: una fila sense `garment` és de la mare, no «de cap».
 */
export function filesDeLaPeca(files, eix) {
  if (eix === null || eix === undefined) return files || []
  return (files || []).filter(f => (f.garment || '') === eix)
}

/**
 * LA IDENTITAT D'UNA REGLA DE GRADUACIÓ — SET-2/T7-B10.
 *
 * `ModelGradingRule` és única per **(model, pom, garment)**: sense capa ni instància, perquè la
 * llei d'increments és del POM i de la prenda, no de cada germana. Dues capes del mateix POM
 * comparteixen regla a posta.
 *
 * ⚠️ NO ÉS `identitatMesura` retallada: són dues identitats diferents i confondre-les tornaria a
 * partir una regla en dues o a fondre'n dues en una. I NO és el `pom_id` sol, que és el que la
 * pantalla feia servir per indexar les edicions: amb dues prendes, tocar el mateix POM a la mare
 * i a la 02 escrivia al mateix calaix i la segona edició es menjava la primera ABANS de desar.
 */
export function clauRegla(fila) {
  return `${fila.pom_id}|${fila.garment || ''}`
}
