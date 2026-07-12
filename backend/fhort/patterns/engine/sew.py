"""Validació de costures: aquests dos costats es poden cosir?

La regla sembla òbvia —dues vores que es cusen han de fer el mateix— i és falsa. El
diferencial de longitud **vol dir coses oposades segons el tipus de costura** (V1 §5.3.3):

  · **Casat**: els dos costats han de fer el mateix. Qualsevol diferència és un ERROR del
    patró, i com més gran, pitjor. Aquí el diferencial esperat és zero i punt.
  · **Frunzit**: el costat llarg SOBRA a posta. Aquesta tela de més és la que s'arruga
    contra el costat curt, i el diferencial és **la instrucció de muntatge**: digues-li a
    la cosidora quants centímetres ha d'arronsar.
  · **Pinça**: igual, però la tela sobrant es plega i es cus en comptes d'arronsar-se.

Per tant, un mateix desviament de 3 cm pot ser un patró trencat o una peça ben dissenyada,
i el motor no pot decidir-ho pel seu compte: ho decideix el TIPUS que el patronista ha
declarat. El que sí que pot fer —i fa— és dir si la realitat encaixa amb el que s'ha
declarat.
"""
from __future__ import annotations

from dataclasses import dataclass

MM_PER_CM = 10.0

#: Marge per sota del qual dues longituds es consideren iguals. Un patró real no casa mai
#: a la mil·lèsima: 1 mm és el que un CAD i una taula de tall donen per bo.
TOLERANCIA_CM = 0.1


@dataclass(frozen=True)
class SewCheck:
    """El veredicte d'una costura."""
    casa: bool
    longitud_a_cm: float
    longitud_b_cm: float
    #: Diferència REAL entre els dos costats (A − B). Signe inclòs: diu quin costat sobra.
    diferencia_cm: float
    #: Diferència que el patronista havia declarat.
    diferencial_declarat_cm: float
    #: El que separa la realitat del que s'esperava. Això és el que s'ha de mirar.
    desviament_cm: float
    tipus: str
    missatge: str


def validar(
    longitud_a_mm: float,
    longitud_b_mm: float,
    tipus: str = 'casat',
    diferencial_cm: float = 0.0,
    tolerancia_cm: float = TOLERANCIA_CM,
) -> SewCheck:
    """Compara els dos costats amb el que el TIPUS de costura promet."""
    a = longitud_a_mm / MM_PER_CM
    b = longitud_b_mm / MM_PER_CM
    diferencia = a - b

    if tipus == 'casat':
        # En un casat, el diferencial declarat ha de ser zero: si algú n'hi posa un, ha
        # triat malament el tipus, i val més dir-l'hi que no pas fer-li cas.
        if abs(diferencial_cm) > tolerancia_cm:
            return SewCheck(
                casa=False, longitud_a_cm=a, longitud_b_cm=b,
                diferencia_cm=diferencia, diferencial_declarat_cm=diferencial_cm,
                desviament_cm=abs(diferencial_cm), tipus=tipus,
                missatge=(
                    f'Una costura CASADA no pot tenir un diferencial declarat de '
                    f'{diferencial_cm:.1f} cm: si un costat ha de sobrar, és un frunzit o '
                    f'una pinça, no un casat.'
                ),
            )
        desviament = abs(diferencia)
        casa = desviament <= tolerancia_cm
        return SewCheck(
            casa=casa, longitud_a_cm=a, longitud_b_cm=b,
            diferencia_cm=diferencia, diferencial_declarat_cm=0.0,
            desviament_cm=desviament, tipus=tipus,
            missatge=(
                f'Casa: els dos costats fan {a:.1f} cm.' if casa else
                f'NO casa: el costat A fa {a:.1f} cm i el B {b:.1f} cm '
                f'({desviament:.1f} cm de diferència).'
            ),
        )

    # Frunzit i pinça: el diferencial és una PROMESA, i es comprova.
    desviament = abs(abs(diferencia) - abs(diferencial_cm))
    casa = desviament <= tolerancia_cm
    quin = 'A' if diferencia > 0 else 'B'
    nom = 'frunzit' if tipus == 'frunzit' else 'pinça'
    return SewCheck(
        casa=casa, longitud_a_cm=a, longitud_b_cm=b,
        diferencia_cm=diferencia, diferencial_declarat_cm=diferencial_cm,
        desviament_cm=desviament, tipus=tipus,
        missatge=(
            f'Casa: el costat {quin} sobra {abs(diferencia):.1f} cm, que és el '
            f'{nom} declarat.' if casa else
            f'NO casa: s\'havien declarat {abs(diferencial_cm):.1f} cm de {nom}, però '
            f'els costats es diferencien en {abs(diferencia):.1f} cm '
            f'({desviament:.1f} cm de desviament).'
        ),
    )
