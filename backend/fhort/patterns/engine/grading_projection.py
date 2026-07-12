"""Projecció: del grading de l'FTT (GradedSpec) a les regles del CAD (GradeRuleData).

AQUÍ ÉS ON EL MOTOR ESCALA. I escalar **no és emetre N geometries**.

El lliurable AAMA és la geometria de la talla mostra, tal com és, **més un RUL poblat i un
número de regla assegut a cada punt**. El CAD del client reconstrueix cada talla fent
`punt_base + delta(regla, talla)`. Si li enviéssim cinc geometries, li enviaríem cinc
patrons morts; enviant-li les regles, li enviem un patró que el seu CAD sap graduar —i
que pot corregir— que és el que un patronista espera rebre.

LES TRES LLEIS D'AQUEST MÒDUL
------------------------------

**1. El grading va PINÇAT.** L'entrada és un `grading_version_id` EXPLÍCIT i prou. El
grading de l'FTT té set camins de lectura diferents per decidir "quina versió mana"
(S0-B7.5) i aquí no se'n tria cap: es rep la versió ja triada. Això esquiva les
col·lisions dual-path de G6 sense tocar-les.

**2. S'aplica el DELTA, mai el valor absolut.** `GradedSpec` porta dues xifres:
`graded_value_cm` (absolut) i `increment_applied_cm` (delta vs la base). Només serveix la
segona, i no és un detall d'implementació: **són magnituds diferents**. El valor que un POM
mesura sobre el PATRÓ i el valor que la fitxa del model DECLARA per a aquest POM no tenen
per què coincidir —i al material real no coincideixen ni de lluny (M-M79: el patró mesura
66.84 cm i la fitxa en declara 100.00)—, perquè es mesuren sobre coses diferents. Aplicar
l'absolut voldria dir estirar el patró 33 cm per fer-li dir el que la fitxa diu. Aplicar el
delta vol dir: *el que aquest patró mesuri, que creixi el que el grading mana*. La
invariant que en surt i que es compleix PER CONSTRUCCIÓ és:

        mesura(talla) − mesura(base) == increment_applied_cm(talla)

La discrepància entre les dues bases no s'amaga: surt a la previsualització (S7-T5) perquè
qui exporta la vegi. És informació, no error.

**3. La talla base ve DECLARADA, mai deduïda.** `Model.base_size_label`. Inferir-la per
`delta == 0` és incorrecte i està documentat que ho és: un POM amb regla ZERO té delta 0 a
TOTES les talles (S0-B7.2).

LA DISTRIBUCIÓ, v1: SIMÈTRICA I DELIBERADAMENT SIMPLE
------------------------------------------------------
Un POM és una mesura entre dos punts. Si el grading diu que ha de créixer 1 cm, aquest
mòdul mou cada punt d'ancoratge mig centímetre en sentits oposats, **al llarg de la
direcció de la mesura** (el vector a→b normalitzat sobre la geometria base). Per
construcció, la mesura creix exactament el que tocava.

Que sigui simètric és una DECISIÓ, no una simplificació amagada: el repartiment fi
—quant es queda el davanter i quant l'esquena, quant puja la sisa i quant baixa— és una
regla de patronatge que depèn de la peça i que s'escriu amb la Montse davant (backlog
§3.5). Fer-ho simètric per defecte és el que un patronista consideraria el punt de partida
raonable; endevinar-ne un altre seria pitjor que no endevinar res.

OMISSIONS: MAI EN SILENCI
-------------------------
Un POM ancorat sense `GradedSpec` no es gradua. Un `GradedSpec` sense POM ancorat no mou
res. Cap de les dues coses és un error —el patró i la fitxa es cobreixen parcialment, i
això és el cas NORMAL— però totes dues s'han de veure, perquè totes dues volen dir que
alguna cosa que algú esperava que passés, no ha passat.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from math import hypot
from typing import Optional

from .errors import PatternEngineError
from .geometry import (
    GradeRuleData,
    GradeTable,
    PatternDocument,
    PointKind,
)
from .operations import (
    MoveIssue,
    MoveReport,
    POMSpec,
    PointRef,
    SewReading,
    SewSpec,
    deltes_resultants,
    move_points,
)
from .ports import GradingSnapshot

MM_PER_CM = 10.0

#: Sota d'això, dos punts d'ancoratge són el mateix punt i la mesura no té direcció.
TOL_DIRECCIO_MM = 1e-6

#: La regla dels punts que no es mouen. Existeix de debò al RUL (amb els deltes a zero):
#: un punt sense regla és un punt que el CAD no sap què fer-ne; un punt amb regla 0 és un
#: punt que es queda quiet **perquè ho hem dit**.
REGLA_ZERO = 0


class GradingNotApproved(PatternEngineError):
    """La versió de grading no està aprovada. Precondició dura: no s'escala amb un
    grading que ningú no ha signat."""


class GradingContextError(PatternEngineError):
    """El context del model (talla base / size run) no es té dret."""


# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Omissio:
    """Una cosa que NO s'ha graduat, i per què. Cap d'aquestes és fatal; totes es veuen."""
    codi: str            # 'pom_sense_spec' | 'spec_sense_pom' | 'cella_buida' | …
    missatge: str
    pom_code: str = ''
    pom_id: Optional[int] = None
    detall: dict = field(default_factory=dict)

    def __str__(self) -> str:
        return f'{self.codi}: {self.missatge}'


@dataclass(frozen=True)
class ProjectionResult:
    """El resultat: la geometria base amb les regles assegudes al damunt, i el RUL."""
    #: La geometria de la talla MOSTRA, intacta, amb `grade_rule` posat a cada punt.
    #: (Intacta: escalar no la toca. El que canvia és què sap dir de si mateixa.)
    document: PatternDocument
    grade_table: GradeTable
    regles_per_punt: dict[PointRef, int]
    #: El que s'ha mogut cada punt a cada talla (mm). És el que alimenta la previsualització.
    deltes_per_talla: dict[str, dict[PointRef, tuple[float, float]]]
    #: Els informes de l'operació atòmica, un per talla (costures, POMs rellegits…).
    informes_per_talla: dict[str, MoveReport]
    omissions: tuple[Omissio, ...] = ()
    avisos: tuple[MoveIssue, ...] = ()

    @property
    def poms_projectats(self) -> tuple[str, ...]:
        """Els POMs que de debò han mogut geometria."""
        return tuple(sorted({
            p.pom_code
            for informe in self.informes_per_talla.values()
            for p in informe.poms
        }))

    @property
    def regles_actives(self) -> int:
        """Regles que mouen alguna cosa (la 0 no compta)."""
        return sum(1 for n in self.grade_table.regles if n != REGLA_ZERO)


# ─────────────────────────────────────────────────────────────────────────────

def project(
    doc: PatternDocument,
    snapshot: GradingSnapshot,
    poms: tuple[POMSpec, ...],
    sews: tuple[SewSpec, ...] = (),
) -> ProjectionResult:
    """GradedSpec (via el port) + POMs ancorats → regles de grading per punt.

    `snapshot` ve del port `GradingSource`: ja porta la versió PINÇADA i el context del
    model (talla base i size run) que `GradedSpec` tot sol no sap donar.
    """
    # ── Guard dur. No es negocia: sense grading aprovat no hi ha niada.
    if not snapshot.approved:
        raise GradingNotApproved(
            f'La versió de grading {snapshot.grading_version_id} NO està aprovada. '
            f'Una niada només es genera des d\'un grading que algú ha signat.'
        )
    if not snapshot.size_run:
        raise GradingContextError(
            'El model no té size run: no se sap quines talles s\'han de graduar.')
    if snapshot.base_size_label not in snapshot.size_run:
        raise GradingContextError(
            f'La talla base «{snapshot.base_size_label}» no és al size run '
            f'{list(snapshot.size_run)}. La base ve DECLARADA pel model; no s\'endevina.'
        )

    omissions: list[Omissio] = []
    avisos: list[MoveIssue] = []

    poms_per_id = {p.pom_id: p for p in poms if p.pom_id is not None}
    ids_amb_spec = {d.pom_id for d in snapshot.deltas}
    codis_spec = {d.pom_id: d.pom_code for d in snapshot.deltas}

    # ── Les dues cares de la cobertura parcial. Cap és un error; totes dues es diuen.
    for pom_id, spec in sorted(poms_per_id.items()):
        if pom_id not in ids_amb_spec:
            omissions.append(Omissio(
                'pom_sense_spec',
                f'El POM {spec.pom_code} està ancorat al patró (peça {spec.peca}) però la '
                f'versió de grading no en té cap valor: no es gradua i es queda igual a '
                f'totes les talles.',
                pom_code=spec.pom_code, pom_id=pom_id,
                detall={'peca': spec.peca},
            ))
    for pom_id in sorted(ids_amb_spec - set(poms_per_id)):
        omissions.append(Omissio(
            'spec_sense_pom',
            f'El POM {codis_spec[pom_id]} té grading a la versió però no està ancorat a cap '
            f'punt del patró: no mou res. (Ancorar-l\'hi el faria entrar a la niada.)',
            pom_code=codis_spec[pom_id], pom_id=pom_id,
        ))

    for p in poms:
        if p.pom_id is None:
            avisos.append(MoveIssue(
                'pom_sense_id',
                f'El POM {p.pom_code} no porta pom_id: no es pot lligar amb cap GradedSpec.',
                peca=p.peca,
            ))

    # ── Una passada per talla: es MOU per saber on van els punts, no per exportar-ho.
    deltes_per_talla: dict[str, dict[PointRef, tuple[float, float]]] = {}
    informes_per_talla: dict[str, MoveReport] = {}

    # Els POMs sense CAP spec ja s'han reportat com a `pom_sense_spec`; no tornen a entrar
    # (si no, cada talla en tornaria a parlar i l'informe diria dues vegades el mateix).
    graduables = {i: s for i, s in poms_per_id.items() if i in ids_amb_spec}

    for talla in snapshot.size_run:
        ordres, oms, avs = _deltes_dels_poms(doc, snapshot, graduables, talla)
        omissions += oms
        avisos += avs

        res = move_points(doc, ordres, poms=poms, sews=sews)
        deltes_per_talla[talla] = deltes_resultants(doc, res.document)
        informes_per_talla[talla] = res.informe
        avisos += [
            replace(a, detall={**a.detall, 'talla': talla}) for a in res.informe.avisos
        ]

    # ── De "on ha anat cada punt" a "quina regla té cada punt".
    regles_per_punt, regles = _regles_des_dels_deltes(doc, snapshot, deltes_per_talla)

    doc_amb_regles = _assignar_regles(doc, regles_per_punt)
    taula = _taula(doc, snapshot, regles)

    return ProjectionResult(
        document=doc_amb_regles,
        grade_table=taula,
        regles_per_punt=regles_per_punt,
        deltes_per_talla=deltes_per_talla,
        informes_per_talla=informes_per_talla,
        omissions=tuple(omissions),
        avisos=tuple(avisos),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Delta escalar → vector, i repartiment simètric
# ─────────────────────────────────────────────────────────────────────────────

def _deltes_dels_poms(
    doc: PatternDocument,
    snapshot: GradingSnapshot,
    poms_per_id: dict[int, POMSpec],
    talla: str,
) -> tuple[dict[PointRef, tuple[float, float]], list[Omissio], list[MoveIssue]]:
    """Per a una talla: quant s'ha de moure cada punt d'ancoratge, i cap on."""
    ordres: dict[PointRef, tuple[float, float]] = {}
    omissions: list[Omissio] = []
    avisos: list[MoveIssue] = []

    for pom_id, spec in sorted(poms_per_id.items()):
        cel = snapshot.delta(pom_id, talla)
        if cel is None:
            # Forat de la matriu: el POM TÉ grading (els que no en tenen gens ni entren
            # aquí), però no per a aquesta talla — una cel·la STEP invàlida no genera fila
            # (S0-B7.2). A la talla que li falti, el POM no es mou.
            omissions.append(Omissio(
                'cella_buida',
                f'El POM {spec.pom_code} no té valor de grading per a la talla {talla}: '
                f'a aquesta talla no es mou.',
                pom_code=spec.pom_code, pom_id=pom_id,
                detall={'talla': talla},
            ))
            continue

        delta_mm = cel.delta_cm * MM_PER_CM
        if delta_mm == 0.0:
            continue  # la talla base, i qualsevol POM amb regla ZERO

        direccio = _direccio(doc, spec)
        if direccio is None:
            avisos.append(MoveIssue(
                'pom_sense_direccio',
                f'El POM {spec.pom_code} té els dos punts d\'ancoratge al mateix lloc: la '
                f'mesura no té direcció i no se sap cap on créixer.',
                peca=spec.peca, detall={'pom': spec.pom_code, 'talla': talla},
            ))
            continue

        ux, uy = direccio
        mig = delta_mm / 2.0

        # Repartiment SIMÈTRIC (v1). S'ACUMULA: un punt pot ser ancoratge de dos POMs, i
        # llavors rep els dos moviments. Sumar-los és l'única cosa honesta que es pot fer;
        # quedar-se amb l'últim seria decidir en silenci quin POM mana.
        _acumular(ordres, spec.ref_a, (-ux * mig, -uy * mig))
        _acumular(ordres, spec.ref_b, (+ux * mig, +uy * mig))

    return ordres, omissions, avisos


def _acumular(
    ordres: dict[PointRef, tuple[float, float]],
    ref: PointRef,
    d: tuple[float, float],
) -> None:
    x, y = ordres.get(ref, (0.0, 0.0))
    ordres[ref] = (x + d[0], y + d[1])


def _direccio(doc: PatternDocument, spec: POMSpec) -> Optional[tuple[float, float]]:
    """El vector a→b normalitzat, sobre la geometria BASE.

    Sobre la BASE i no sobre la moguda: si es recalculés a cada talla, la direcció aniria
    derivant amb el propi moviment i el creixement deixaria de ser el que el grading mana.
    """
    peca = doc.piece(spec.peca)
    if peca is None:
        return None

    a = _punt(peca, spec.ref_a)
    b = _punt(peca, spec.ref_b)
    if a is None or b is None:
        return None

    dx, dy = b[0] - a[0], b[1] - a[1]
    llarg = hypot(dx, dy)
    if llarg <= TOL_DIRECCIO_MM:
        return None
    return (dx / llarg, dy / llarg)


def _punt(peca, ref: PointRef) -> Optional[tuple[float, float]]:
    if ref.vora is None:
        if ref.ordre < len(peca.notches):
            n = peca.notches[ref.ordre]
            return (n.x, n.y)
        return None
    if ref.vora >= len(peca.boundaries):
        return None
    punts = peca.boundaries[ref.vora].points
    if ref.ordre >= len(punts):
        return None
    p = punts[ref.ordre]
    return (p.x, p.y)


# ─────────────────────────────────────────────────────────────────────────────
# Deltes per punt → regles
# ─────────────────────────────────────────────────────────────────────────────

def _regles_des_dels_deltes(
    doc: PatternDocument,
    snapshot: GradingSnapshot,
    deltes_per_talla: dict[str, dict[PointRef, tuple[float, float]]],
) -> tuple[dict[PointRef, int], dict[int, GradeRuleData]]:
    """Una regla per punt MOGUT; la regla 0 per a la resta.

    Porten regla els punts de GIR i els PIQUETS. Els de corba, no: no es graden, flueixen
    —i és el CAD del client qui els fa fluir en reconstruir la talla, igual que hem fet
    nosaltres. Posar-los regla seria dir-li que no ho faci.
    """
    talles = snapshot.size_run
    regles: dict[int, GradeRuleData] = {
        REGLA_ZERO: GradeRuleData(
            numero=REGLA_ZERO,
            deltes={t: (0.0, 0.0) for t in talles},
        )
    }
    regles_per_punt: dict[PointRef, int] = {}
    seguent = 1

    for peca in doc.pieces:
        candidats: list[PointRef] = []
        for i, b in enumerate(peca.boundaries):
            for j, p in enumerate(b.points):
                if p.kind is PointKind.TURN:
                    candidats.append(PointRef(peca.nom_block, i, j))
        for j in range(len(peca.notches)):
            candidats.append(PointRef(peca.nom_block, None, j))

        for ref in candidats:
            per_talla = {
                t: deltes_per_talla.get(t, {}).get(ref, (0.0, 0.0)) for t in talles
            }
            if all(abs(dx) < 1e-9 and abs(dy) < 1e-9 for dx, dy in per_talla.values()):
                regles_per_punt[ref] = REGLA_ZERO
                continue

            regles[seguent] = GradeRuleData(numero=seguent, deltes=per_talla)
            regles_per_punt[ref] = seguent
            seguent += 1

    return regles_per_punt, regles


def _assignar_regles(
    doc: PatternDocument, regles_per_punt: dict[PointRef, int]
) -> PatternDocument:
    """El número de regla, assegut a cada punt. Document NOU: la base no es toca."""
    peces = []
    for peca in doc.pieces:
        vores = tuple(
            replace(b, points=tuple(
                replace(
                    p,
                    grade_rule=regles_per_punt.get(
                        PointRef(peca.nom_block, i, j),
                        # Els de corba no en porten, i és a posta.
                        None if p.kind is not PointKind.TURN else REGLA_ZERO,
                    ),
                )
                for j, p in enumerate(b.points)
            ))
            for i, b in enumerate(peca.boundaries)
        )
        piquets = tuple(
            replace(n, grade_rule=regles_per_punt.get(
                PointRef(peca.nom_block, None, j), REGLA_ZERO))
            for j, n in enumerate(peca.notches)
        )
        peces.append(replace(peca, boundaries=vores, notches=piquets))

    return replace(doc, pieces=tuple(peces))


# ─────────────────────────────────────────────────────────────────────────────
# S7-T3 · PREVIEW PER TALLA — la validació que un CAD no fa
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class POMPreview:
    """Un POM a una talla: el que la geometria diu, i el que el grading manava."""
    pom_code: str
    peca: str
    #: Llegit de la geometria reconstruïda amb LES REGLES.
    valor_cm: Optional[float]
    #: El que ha crescut respecte de la talla base, també llegit de la geometria.
    delta_llegit_cm: Optional[float]
    #: El que la `GradedSpec` manava que crescués.
    delta_spec_cm: Optional[float]
    #: `delta_llegit − delta_spec`. Ha de ser 0: la niada es construeix a partir del spec.
    #: Si no ho és, l'escalat no ha fet el que el grading deia i l'exportació s'ha d'aturar.
    desviament_cm: Optional[float] = None
    #: El que la fitxa del model DECLARA per a aquesta talla (valor absolut). NO té per què
    #: coincidir amb `valor_cm`: el patró i la fitxa mesuren coses diferents (v. §2 del
    #: docstring). Es mostra perquè es vegi, no perquè quadri.
    valor_spec_cm: Optional[float] = None
    error: str = ''

    @property
    def ok(self) -> bool:
        return self.desviament_cm is not None and abs(self.desviament_cm) < 1e-6


@dataclass(frozen=True)
class SizePreview:
    """Una talla sencera, reconstruïda des de les regles."""
    talla: str
    es_base: bool
    bbox: tuple[float, float, float, float]   # (min_x, min_y, max_x, max_y) en mm
    poms: tuple[POMPreview, ...]
    costures: tuple[SewReading, ...]
    avisos: tuple[MoveIssue, ...] = ()

    @property
    def ok(self) -> bool:
        return (
            all(p.ok for p in self.poms if p.delta_spec_cm is not None)
            and all(s.check is not None and s.check.casa for s in self.costures)
        )


def preview_per_talla(
    doc: PatternDocument,
    projeccio: ProjectionResult,
    snapshot: GradingSnapshot,
    poms: tuple[POMSpec, ...],
    sews: tuple[SewSpec, ...] = (),
) -> tuple[SizePreview, ...]:
    """Reconstrueix cada talla APLICANT LES REGLES i comprova que digui el que ha de dir.

    Això no és tornar a fer la projecció amb un altre nom: és el camí INVERS. La projecció
    va de "el grading mana +1 cm" a "aquests punts es mouen així". La previsualització
    agafa **el que sortirà pel fitxer** —les regles i prou, com faria el CAD del client— i
    en reconstrueix la geometria per preguntar-li a la GEOMETRIA quant mesura. Si les dues
    bandes no coincideixen, el que hem escrit al RUL no és el que volíem dir.

    És comptabilitat de doble entrada: el mateix número, calculat per dos camins que no es
    parlen. I és **la validació que cap CAD no et fa** — un CAD gradua i calla; nosaltres
    graduem i ho comprovem contra les mesures abans que el fitxer surti per la porta.
    """
    base = snapshot.base_size_label
    previews: list[SizePreview] = []

    # Els valors a la base, llegits de la geometria: és contra AIXÒ que es mesura el
    # creixement (mai contra el valor absolut de la fitxa, que parla d'una altra cosa).
    valors_base = _valors_dels_poms(doc, poms)

    for talla in snapshot.size_run:
        deltes = {
            ref: regla_delta
            for ref, num in projeccio.regles_per_punt.items()
            if (regla_delta := projeccio.grade_table.regles[num].delta(talla)) != (0.0, 0.0)
        }

        res = move_points(doc, deltes, poms=poms, sews=sews)
        lectures = {p.pom_code: p for p in res.informe.poms}

        fila: list[POMPreview] = []
        for spec in poms:
            lectura = lectures.get(spec.pom_code)
            cel = (
                snapshot.delta(spec.pom_id, talla)
                if spec.pom_id is not None else None
            )
            base_cm = valors_base.get(spec.pom_code)

            if lectura is None or lectura.valor_cm is None:
                fila.append(POMPreview(
                    spec.pom_code, spec.peca, None, None,
                    cel.delta_cm if cel else None,
                    error=(lectura.error if lectura else 'No s\'ha pogut llegir.'),
                ))
                continue

            delta_llegit = (
                round(lectura.valor_cm - base_cm, 6) if base_cm is not None else None
            )
            delta_spec = cel.delta_cm if cel else None
            desviament = (
                round(delta_llegit - delta_spec, 6)
                if (delta_llegit is not None and delta_spec is not None) else None
            )

            fila.append(POMPreview(
                pom_code=spec.pom_code,
                peca=spec.peca,
                valor_cm=lectura.valor_cm,
                delta_llegit_cm=delta_llegit,
                delta_spec_cm=delta_spec,
                desviament_cm=desviament,
                valor_spec_cm=cel.value_cm if cel else None,
            ))

        previews.append(SizePreview(
            talla=talla,
            es_base=(talla == base),
            bbox=_bbox(res.document),
            poms=tuple(fila),
            costures=res.informe.costures,
            avisos=res.informe.avisos,
        ))

    return tuple(previews)


def _valors_dels_poms(
    doc: PatternDocument, poms: tuple[POMSpec, ...]
) -> dict[str, float]:
    """El que cada POM mesura sobre la geometria base (sense moure res)."""
    res = move_points(doc, {}, poms=poms)
    return {
        p.pom_code: p.valor_cm
        for p in res.informe.poms
        if p.valor_cm is not None
    }


def _bbox(doc: PatternDocument) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for peca in doc.pieces:
        for b in peca.boundaries:
            for p in b.points:
                xs.append(p.x)
                ys.append(p.y)
    if not xs:
        return (0.0, 0.0, 0.0, 0.0)
    return (min(xs), min(ys), max(xs), max(ys))


def _taula(
    doc: PatternDocument,
    snapshot: GradingSnapshot,
    regles: dict[int, GradeRuleData],
) -> GradeTable:
    """El RUL que sortirà: les NOSTRES talles i la NOSTRA base.

    Ull, que això és un canvi de sobirania i s'ha de dir: el RUL que el client ens va donar
    graduava unes altres talles sobre una altra base (AMELIA: XS-S-M-L-XL sobre M). El que
    exportem gradua el size run del MODEL sobre la base del MODEL (S-M-L-XL-XXL sobre S),
    perquè el grading que manem és el de l'FTT, no el que venia dins el fitxer.
    """
    original = doc.grade_table
    return GradeTable(
        nom=original.nom if original else '',
        talles=tuple(snapshot.size_run),
        talla_base=snapshot.base_size_label,
        regles=regles,
        unitats=original.unitats if original else 'METRIC',
        # Els deltes es guarden en mm; el writer els torna a les unitats natives del fitxer
        # dividint per aquest factor. Ha de ser el MATEIX que el de la geometria, o el RUL
        # i el DXF parlarien d'escales diferents.
        unitats_factor_mm=(
            doc.fingerprint.unitats.factor_to_mm
            if doc.fingerprint.unitats else 1.0
        ),
        aama_version=original.aama_version if original else '',
        autor=original.autor if original else '',
    )
