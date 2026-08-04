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

/** Clau d'agrupació d'una línia o fila per la mesura a què pertany. */
export function identitatMesura(fila) {
  return `${fila.pom_id}|${fila.capa || ''}|${fila.instancia || ''}`
}
