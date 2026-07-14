"""ESTALITUD — una versió de grading aprovada, ¿encara diu la veritat?

El sistema té dues lleis que no es toquen (decisió Patró C, registrada al PLA):

  · **La mesura és SOBIRANA.** Un canvi de base no es bloqueja mai perquè hi hagi un segell al
    davant. El patronista mesura el que mesura.
  · **El segell és HONEST.** Una versió aprovada no es re-signa sola ni s'auto-actualitza. El que
    algú va signar continua sent el que va signar.

De les dues juntes surt, inevitablement, una tercera cosa: **una versió aprovada pot quedar
enrere**. La base ha canviat després del segell i els seus `GradedSpec` continuen derivant d'una
base que ja no existeix. Això no és un error de ningú —és el preu de no mentir per cap dels dos
costats— i l'única sortida honesta és que **el sistema ho DIGUI**.

Aquest mòdul és el que ho diu. No bloqueja res, no repara res, no re-signa res: constata.

─────────────────────────────────────────────────────────────────────────────
PER QUÈ EL COMPTADOR NO N'HI HA PROU (i el que el terreny ja tenia)
─────────────────────────────────────────────────────────────────────────────
`GradedSpec.generated_from_version` (fitting/models.py:183-186) prometia el detector: comparar-lo
amb `Model.measurements_version` i veure si el spec s'ha quedat enrere. **És necessari i és
insuficient**, i el terreny diu per què: `measurements_version` **només s'incrementa a
`bump_grading_version_and_generate`** (`pom/services.py:691-697`). El desa de la fitxa
(`pom/wizard_views.py:205`) escriu `BaseMeasurement` directament i **no toca el comptador ni
regenera res**. Per aquest camí la base es mou i el comptador no se n'assabenta: la versió
aprovada semblaria fresca amb la base canviada sota els peus. És exactament el forat que el
detector havia de tapar.

El que sí que ho veu tot ja hi era: **`MeasurementChangeLog`** (`models_app/models.py:600`), el
registre APPEND-ONLY de tots els canvis de valor de base, amb data. Un `post_save` sobre
`BaseMeasurement` (`models_app/signals.py:215`) hi escriu una fila **passi el canvi pel camí que
passi** —fitting, import, wizard, correcció manual—, perquè penja del model de dades i no d'un
camí de codi.

**Per això aquí no s'afegeix cap snapshot ni cap columna nova.** Un snapshot de la base al moment
del segell hauria estat una segona còpia d'una veritat que el sistema ja registra, amb el deure de
mantenir-la sincronitzada i el risc que divergís. El registre append-only **és** l'snapshot: la
base del segell és la base d'avui menys tot el que s'hi ha escrit després.

El comptador es queda com a **segon testimoni**: veu els casos on el segell no té data (versions
aprovades per un camí de codi que ja no existeix — R11: gv 30, gv 53) i confirma els que el
registre ja denuncia.

─────────────────────────────────────────────────────────────────────────────
QUATRE ESTATS, I UN D'ELLS ÉS «NO HO SÉ»
─────────────────────────────────────────────────────────────────────────────
`NO_SEGELLADA` · una versió que ningú ha aprovat no promet res, i per tant no pot quedar enrere.
`FRESCA`       · segellada, i la base no s'ha mogut des del segell.
`ESTALA`       · segellada, i la base SÍ que s'ha mogut. Amb les xifres: quants canvis i quan.
`DESCONEGUDA`  · segellada, i **no es pot saber**: el segell no té data (`data_aprovacio` NULL) i
                 els seus specs no diuen de quina versió de mesures venen. Passa amb les dues
                 versions que va aprovar un camí de codi que ja no existeix.

El quart estat no és una comoditat: és la diferència entre no saber i dir que va bé. Una versió que
no es pot datar s'ensenya amb l'avís, no es dona per bona — perquè el que va a la taula de tall no
pot dependre d'un silenci.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

NO_SEGELLADA = 'no_segellada'
FRESCA = 'fresca'
ESTALA = 'estala'
DESCONEGUDA = 'desconeguda'


@dataclass(frozen=True)
class Estalitud:
    """El veredicte sobre una versió de grading, amb les xifres que el sostenen."""
    estat: str
    motiu: str
    #: Canvis de base registrats DESPRÉS del segell. És la prova, i va amb el veredicte.
    canvis_base: int = 0
    primer_canvi: datetime | None = None
    ultim_canvi: datetime | None = None
    #: Els dos testimonis, en cru, perquè el veredicte es pugui auditar sense tornar a la BD.
    generated_from: int | None = None
    measurements_version: int | None = None
    poms_afectats: tuple[str, ...] = field(default_factory=tuple)

    @property
    def avisa(self) -> bool:
        """¿Aquesta versió s'ha d'ensenyar amb avís? Estala i desconeguda, totes dues."""
        return self.estat in (ESTALA, DESCONEGUDA)


def estalitud(gv) -> Estalitud:
    """El veredicte d'una `GradingVersion`. Només lectura, i sense excuses.

    L'ordre de les preguntes és el de la certesa: primer el registre de canvis (que ho veu tot i
    porta dates), després el comptador (que veu menys però parla quan el segell no té data).
    """
    from fhort.models_app.models import MeasurementChangeLog

    if not gv.aprovada:
        return Estalitud(
            estat=NO_SEGELLADA,
            motiu='Aquesta versió no està segellada: no promet res, i per tant no pot quedar enrere.',
        )

    model = gv.size_fitting.model
    generated_from = _generated_from(gv)
    mv = model.measurements_version

    # ── Testimoni 1: el registre append-only. Ho veu tot, passi el canvi pel camí que passi.
    if gv.data_aprovacio is not None:
        canvis = list(
            MeasurementChangeLog.objects
            .filter(model_id=model.id, created_at__gt=gv.data_aprovacio)
            .select_related('pom')
            .order_by('created_at')
        )
        if canvis:
            poms = tuple(dict.fromkeys(
                c.pom.codi_client for c in canvis if c.pom_id is not None))
            return Estalitud(
                estat=ESTALA,
                motiu=(
                    f'Aprovada, però la base ha canviat des del segell: {len(canvis)} canvi(s) de '
                    f'mesura base registrats després del {gv.data_aprovacio:%d/%m/%Y %H:%M}. '
                    f'Els seus valors graduats deriven d\'una base que ja no és la del model.'
                ),
                canvis_base=len(canvis),
                primer_canvi=canvis[0].created_at,
                ultim_canvi=canvis[-1].created_at,
                generated_from=generated_from,
                measurements_version=mv,
                poms_afectats=poms,
            )
        return Estalitud(
            estat=FRESCA,
            motiu=(
                f'Segellada el {gv.data_aprovacio:%d/%m/%Y %H:%M} i cap canvi de base registrat '
                f'des de llavors.'
            ),
            generated_from=generated_from,
            measurements_version=mv,
        )

    # ── Testimoni 2: el comptador. Parla quan el segell no té data.
    #
    # Un spec nascut d'una versió de mesures ANTERIOR a la del model vol dir que la base s'ha
    # mogut i el grading no l'ha seguida. No sap DIR QUAN (per això no dona dates), però sap dir
    # que sí.
    if generated_from is not None and generated_from < mv:
        return Estalitud(
            estat=ESTALA,
            motiu=(
                f'Aprovada, però la base ha canviat des del segell: els seus specs venen de la '
                f'versió de mesures {generated_from} i el model ja va per la {mv}. '
                f'(El segell no té data: no se sap QUAN va passar.)'
            ),
            generated_from=generated_from,
            measurements_version=mv,
        )

    # ── Ni l'un ni l'altre poden parlar. Es diu, no s'endevina.
    return Estalitud(
        estat=DESCONEGUDA,
        motiu=(
            'Aquesta versió està aprovada però el seu segell no té data, i els seus specs no diuen '
            'de quina versió de mesures venen: NO es pot saber si la base ha canviat des que es va '
            'signar. Comprova-la abans de tallar-hi res.'
        ),
        generated_from=generated_from,
        measurements_version=mv,
    )


def _generated_from(gv) -> int | None:
    """De quina versió de mesures venen els specs d'aquesta versió.

    S'agafa el **mínim**: si una versió tingués specs de dues versions de mesures (no hauria de
    passar, però el detector no és qui ho ha d'impedir), el que compta és el més endarrerit — la
    versió és tan fresca com el seu spec més vell.
    """
    valors = [
        v for v in gv.graded_specs.values_list('generated_from_version', flat=True)
        if v is not None
    ]
    return min(valors) if valors else None


def com_a_dict(e: Estalitud) -> dict:
    """El veredicte, per a l'API. Les xifres viatgen amb ell: un avís sense proves no és auditable."""
    return {
        'estat': e.estat,
        'avisa': e.avisa,
        'motiu': e.motiu,
        'canvis_base': e.canvis_base,
        'primer_canvi': e.primer_canvi,
        'ultim_canvi': e.ultim_canvi,
        'generated_from': e.generated_from,
        'measurements_version': e.measurements_version,
        'poms_afectats': list(e.poms_afectats),
    }
