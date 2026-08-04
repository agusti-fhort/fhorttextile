"""LA CLAU D'UNA MESURA AL PAYLOAD — font única de la seva forma.

Fins a C4 la identitat d'una mesura al contracte HTTP era el `pom_id` pelat, i era suficient
perquè les comportes de C1/C1-ins garantien una sola fila per POM. Amb dues germanes vives
—la mateixa mesura a dues capes, o a dues instàncies— el `pom_id` deixa de ser una clau: dues
files hi caurien a sobre i l'última llegida guanyaria.

Dos dels lectors de payload publiquen la mesura com a **clau d'un objecte JSON**
(`grading_views.cells` i `models_app.views.deltes`), i un objecte JSON no pot tenir una clau
composta. La clau, doncs, s'ha d'aplanar a text. Aquesta funció és l'ÚNIC lloc on es decideix
com, perquè:

  · els dos lectors alimenten graelles del mateix front i han de parlar igual;
  · el frontend l'haurà de desmuntar (bloc 3), i desmuntar dos formats seria fabricar el bug
    que això existeix per matar.

FORMA: `{pom_id}|{capa}|{instancia}`, sempre els tres trams i sempre en aquest ordre.

Per què `|` i no `:`: el separador `:` ja viu al projecte per a un identificador sintètic
DIFERENT —`{pom_id}:{talla}` (`models_app/views.py:2876`, `fittingGridAdapter.jsx:144`)— i
reaprofitar-lo faria que dos formats sense res a veure es poguessin confondre en llegir-los.

Per què els tres trams SEMPRE, i no s'omet la part buida: `'12|exterior|'` i `'12|exterior'`
serien la mateixa mesura escrita de dues maneres, i qualsevol comparació de claus (un `Set` al
front, un `in` aquí) diria que són distintes. La instància única és el tram buit, no l'absència
del tram.

⚠️ Això NO és la clau de BASE DE DADES. A Postgres la identitat viu a la unicitat de quatre
columnes de `BaseMeasurement` (model, pom, capa, instancia) i no s'aplana mai. Aquesta funció
serveix la vora del payload i prou: qui hagi de consultar, filtrar o escriure, que faci servir
els tres camps per separat.
"""

#: Separador dels trams. Exportat perquè qui hagi de desmuntar la clau no el reescrigui.
SEPARADOR = '|'


def clau_mesura(pom_id, capa='exterior', instancia='') -> str:
    """Retorna la clau de payload d'una mesura: `{pom_id}|{capa}|{instancia}`.

    `capa` i `instancia` accepten `None` i el tracten com el seu valor buit —les columnes són
    `NOT NULL` amb default, però un `values()` sobre una taula sense la columna, o un objecte
    a mig construir, hi poden arribar amb `None`, i una clau amb el text «None» a dins seria
    un error mut que només es veuria a la pantalla del client.
    """
    return f'{pom_id}{SEPARADOR}{capa or "exterior"}{SEPARADOR}{instancia or ""}'
