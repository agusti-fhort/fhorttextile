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

**Cobertura** (Taller de patró, W1). Validar cada costura pel seu compte no n'hi ha prou:
dues costures poden ser correctes cadascuna i, alhora, reclamar el mateix tros de vora, o
sumar més tela de la que la peça té. Això no ho veu ningú mirant una costura sola —cal
mirar la VORA sencera— i és exactament el que passa quan els trams es declaren a mà. Per
això `validar_cobertura` mira, per vora, tot el que s'hi cus.
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


# ─────────────────────────────────────────────────────────────────────────────
# COBERTURA D'UNA VORA — què s'hi cus, tot junt (Taller de patró · W1)
# ─────────────────────────────────────────────────────────────────────────────

MENA_SOLAPAMENT = 'solapament'
MENA_EXCES = 'exces'


@dataclass(frozen=True)
class TramCosit:
    """Un tram d'una vora que una costura reclama.

    `t_fi` < `t_inici` vol dir que el tram passa per l'origen de la vora (vora tancada):
    la mateixa convenció que `engine.segments.fraccio_tram`.
    """
    sew_id: int
    segment_id: int
    t_inici: float
    t_fi: float
    nom: str = ''


@dataclass(frozen=True)
class AvisCobertura:
    """Un problema de cobertura, amb les xifres. Mai un booleà pelat.

    Un avís que digui "hi ha solapament" i prou obliga el patronista a buscar-lo a mà. El
    que serveix és quins trams, de quines costures, i quants centímetres.
    """
    mena: str                      # MENA_SOLAPAMENT | MENA_EXCES
    vora: int
    longitud_vora_cm: float
    missatge: str
    #: Solapament: les dues costures i els dos trams que es trepitgen, i quant.
    sews: tuple[int, ...] = ()
    segments: tuple[int, ...] = ()
    solapament_cm: float = 0.0
    #: Excés: quanta tela reclamen totes les costures juntes, i quanta en sobra.
    suma_cosida_cm: float = 0.0
    exces_cm: float = 0.0


def _subtrams(tram: TramCosit) -> list[tuple[float, float]]:
    """Un tram, com a intervals que NO donen la volta.

    Un tram que passa per l'origen és, en paràmetre, dos trossos: [t_inici, 1] i [0, t_fi].
    Partir-lo aquí deixa la intersecció de més avall com una comparació d'intervals normals
    i corrents, en comptes d'un niu d'`if` sobre casos que donen la volta.
    """
    if tram.t_fi >= tram.t_inici:
        return [(tram.t_inici, tram.t_fi)]
    return [(tram.t_inici, 1.0), (0.0, tram.t_fi)]


def _solapament(a: TramCosit, b: TramCosit) -> float:
    """Fracció de vora que dos trams comparteixen."""
    total = 0.0
    for ai, af in _subtrams(a):
        for bi, bf in _subtrams(b):
            total += max(0.0, min(af, bf) - max(ai, bi))
    return total


def fraccio_cosida(tram: TramCosit) -> float:
    """Fracció de la vora que ocupa un tram (dona la volta si cal)."""
    return sum(f - i for i, f in _subtrams(tram))


def validar_cobertura(
    vora: int,
    longitud_vora_mm: float,
    trams: list[TramCosit],
    tolerancia_cm: float = TOLERANCIA_CM,
) -> list[AvisCobertura]:
    """Tot el que es cus sobre UNA vora, mirat junt.

    Dos defectes que només es veuen des d'aquí:

      · **SOLAPAMENT** — dues costures reclamen el mateix tros de vora. Cadascuna, mirada
        sola, pot casar perfectament; juntes, cusen dues vegades la mateixa tela. És el
        defecte típic de declarar trams a mà, i el que la segmentació gir→gir feia
        impossible (els trams derivats no es trepitgen mai perquè són consecutius).
      · **EXCÉS** — la suma del que es cus passa de la vora que hi ha. La peça no té tanta
        tela: o un tram està mal declarat, o hi ha una costura de més.

    Els dos avisos porten les xifres. `longitud_vora_mm` = 0 no és un avís: és una vora
    degenerada, i el que en digués aquesta funció seria soroll sobre un problema que ja
    s'ha reportat abans.
    """
    if longitud_vora_mm <= 0 or not trams:
        return []

    llarg_cm = longitud_vora_mm / MM_PER_CM
    avisos: list[AvisCobertura] = []

    # ── Solapaments, parell a parell ────────────────────────────────────────
    for i in range(len(trams)):
        for j in range(i + 1, len(trams)):
            a, b = trams[i], trams[j]
            solapa_cm = _solapament(a, b) * llarg_cm
            if solapa_cm <= tolerancia_cm:
                continue
            mateixa = a.sew_id == b.sew_id
            quins = ' i '.join(filter(None, [a.nom, b.nom])) or 'dos trams'
            avisos.append(AvisCobertura(
                mena=MENA_SOLAPAMENT, vora=vora, longitud_vora_cm=round(llarg_cm, 2),
                sews=(a.sew_id, b.sew_id), segments=(a.segment_id, b.segment_id),
                solapament_cm=round(solapa_cm, 2),
                missatge=(
                    f'La costura {a.sew_id} es trepitja a ella mateixa: {quins} comparteixen '
                    f'{solapa_cm:.1f} cm de la vora {vora}. La longitud del costat compta '
                    f'aquesta tela dues vegades.'
                    if mateixa else
                    f'Les costures {a.sew_id} i {b.sew_id} reclamen els mateixos '
                    f'{solapa_cm:.1f} cm de la vora {vora} ({quins}): aquesta tela no es pot '
                    f'cosir dues vegades.'
                ),
            ))

    # ── Excés: la suma no hi cap ────────────────────────────────────────────
    suma_cm = sum(fraccio_cosida(t) for t in trams) * llarg_cm
    exces_cm = suma_cm - llarg_cm
    if exces_cm > tolerancia_cm:
        avisos.append(AvisCobertura(
            mena=MENA_EXCES, vora=vora, longitud_vora_cm=round(llarg_cm, 2),
            sews=tuple(sorted({t.sew_id for t in trams})),
            segments=tuple(t.segment_id for t in trams),
            suma_cosida_cm=round(suma_cm, 2), exces_cm=round(exces_cm, 2),
            missatge=(
                f'La vora {vora} fa {llarg_cm:.1f} cm i les costures en reclamen '
                f'{suma_cm:.1f} cm: en sobren {exces_cm:.1f} cm. La peça no té tanta tela.'
            ),
        ))

    return avisos
