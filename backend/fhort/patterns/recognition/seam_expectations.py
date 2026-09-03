"""FASE A · THE CATALOGUE'S EXPECTATION: which edges a garment like this one is sewn along.

F3 built `SeamPairTemplate` and F4.2 taught the pieces to name their edges. This is where the
two meet: with a piece role and an edge role on each side, a candidate pair stops being a
guess about two curves and becomes a question the catalogue can answer — *is this a seam the
house has seen 105 612 times, or one it has never seen at all?*

**It does not propose. It annotates, and it can veto.** The geometry still decides what is a
candidate; this says what the catalogue knows about it. Same law as everything in F4: the
green is the human's.

── THE THREE GRADES, AND WHY «RARE» IS NOT «WRONG» ──────────────────────────────
`observed_seams / observed_den` is **seams per applicable pattern**, so it goes above 1
routinely (a bodice has two side seams, so `side_seam↔side_seam` measures 4,84). The grades
cut it at 0,75 and 0,30.

🚨 **A rare pair is still a real pair.** `collar_attach↔neckline` measures 0,157 — and the
837, the house's own bank, has exactly that seam. So «rare» governs only whether the
catalogue speaks FIRST: a rare expectation never puts itself on the checklist of what is
missing, but it still annotates a candidate the geometry found. Reading «rare» as «wrong»
would tell the pattern maker their own dress is a mistake.

── 🚨 THE ZERO-MEASURED PAIRS ARE A DIRECTION, NOT AN OVERSIGHT (LAW D.02) ───────
Two templates carry `observed_seams = 0` over a real denominator:

    back/back.armhole  ↔ sleeve/front.sleeve_cap        0 of 90 273
    cuff/back.band_attach_upper ↔ pant/front.cuff_line  0 of 17 130

Their mirrors measure 105 612 and 15 882. A sleeve cap goes into an armhole ONE way round,
and the corpus says so with a denominator big enough to mean it. So a zero-measured template
is not an unfilled row to be treated as unknown: it is **evidence against**, and this module
never lets one become a proposal.
"""
from __future__ import annotations

from dataclasses import dataclass

#: Seams per applicable pattern. Above this the catalogue EXPECTS the pair and will say so
#: when it is missing; between the two it suggests; below, it only confirms what geometry
#: already found. Measured distribution over the 55 seeded templates: 34 core · 6 common ·
#: 13 rare · 2 zero.
GRAU_CORE = 0.75
GRAU_COMMON = 0.30

CORE, COMMON, RARE, NEVER = 'core', 'common', 'rare', 'never'


@dataclass(frozen=True)
class Costat:
    """One side of a seam, in catalogue vocabulary: what piece, which face, which edge."""

    piece_role: str
    face: str
    edge_role: str

    def clau(self) -> tuple[str, str]:
        """🚨 The matching key **ignores the face**, and that is measured, not lax.

        The 837's five pieces all carry `face = ''`, and correctly so: D1 put the front/back
        axis in the PIECE ROLE for body pieces (`front`, `back` are roles), and an empty face
        means «this piece has no face», not «unknown». The templates, coming from a generator
        that spells the axis twice, say `front/front.shoulder_seam`.

        Matching on face as well would miss every seam of the house's own bank — measured: 0
        of 8 instead of 6 of 8. The face is kept on the dataclass because it is real
        information and it travels into the evidence; it is just not what identifies a side.
        """
        return (self.piece_role, self.edge_role)


@dataclass(frozen=True)
class Expectativa:
    """What the catalogue knows about one pair of sides."""

    a: Costat
    b: Costat
    seam_kind: str
    grau: str
    ratio: float
    observed_seams: int | None
    observed_den: int | None
    co_generated: bool
    #: The template's own audit trail, so a chip can point at where the number came from.
    observed_ref: str = ''

    @property
    def proposable(self) -> bool:
        """A zero-measured pair is evidence AGAINST and never becomes a proposal (D.02)."""
        return self.grau != NEVER

    def frase(self) -> str:
        """The one line a chip shows. Numbers real, never rounded into a promise."""
        if self.grau == NEVER:
            return ('the catalogue has measured this pair {} times in {} patterns: it is the '
                    'mirror of a seam that only goes one way'
                    .format(self.observed_seams, self.observed_den))
        if self.observed_den:
            return ('the catalogue expects this pair — {} seams over {} patterns where it was '
                    'possible ({})'.format(self.observed_seams, self.observed_den, self.grau))
        return 'the catalogue knows this pair ({})'.format(self.grau)


def _grau(observed_seams, observed_den) -> tuple[str, float]:
    if not observed_den:
        # No denominator is NOT zero: it is a row nobody has measured. It stays usable as
        # vocabulary and unusable as evidence — the same honesty as `evidence_num = NULL`
        # on `LandmarkRole`.
        return (RARE, 0.0)
    ratio = (observed_seams or 0) / observed_den
    if observed_seams == 0:
        return (NEVER, 0.0)
    if ratio >= GRAU_CORE:
        return (CORE, ratio)
    if ratio >= GRAU_COMMON:
        return (COMMON, ratio)
    return (RARE, ratio)


class SeamExpectations:
    """The catalogue's templates, indexed so a pair can be looked up in one step.

    Built once per model and passed as plain data into the pure matcher, exactly as
    `Candidat.preferencia` is: the engine must keep not knowing what a database is.
    """

    def __init__(self, expectatives: list[Expectativa]):
        self._per_parella: dict[frozenset, Expectativa] = {}
        self._per_costat: dict[tuple[str, str], list[Expectativa]] = {}
        for e in expectatives:
            clau = frozenset((e.a.clau(), e.b.clau()))
            # A pair can be seeded twice (once per face combination). The STRONGEST wins:
            # `armhole↔sleeve_cap` exists as 105 612 and as 0, and reading the second as the
            # verdict on the pair would veto the commonest seam in the corpus. The zero is a
            # statement about a DIRECTION (D.02), and directions are handled per template.
            vell = self._per_parella.get(clau)
            if vell is None or e.ratio > vell.ratio:
                self._per_parella[clau] = e
            for c in (e.a, e.b):
                self._per_costat.setdefault(c.clau(), []).append(e)

    def __len__(self) -> int:
        return len(self._per_parella)


    @staticmethod
    def costat_de(candidat):
        """A `Candidat` → its catalogue side, or None if nobody has named it yet.

        Lives here and not in the engine so the pure matcher never has to know the shape of
        a catalogue side: it hands over a candidate and gets back something it only compares.
        """
        if not getattr(candidat, 'piece_role', '') or not getattr(candidat, 'edge_role', ''):
            return None
        return Costat(candidat.piece_role, getattr(candidat, 'face', '') or '',
                      candidat.edge_role)

    def per_parella(self, a: Costat, b: Costat) -> Expectativa | None:
        """What the catalogue says about these two sides, or None if it says nothing."""
        if not a.edge_role or not b.edge_role or not a.piece_role or not b.piece_role:
            return None
        return self._per_parella.get(frozenset((a.clau(), b.clau())))

    def esperades(self, costats: list[Costat]) -> list[Expectativa]:
        """The CORE expectations reachable with the sides this model actually has.

        Only core, and only pairs whose BOTH sides are present on the pattern: telling a
        pattern maker that their dress is missing a `crotch_seam` would be noise wearing the
        clothes of a checklist.
        """
        presents = {c.clau() for c in costats}
        fora = []
        vistes = set()
        for e in self._per_parella.values():
            if e.grau != CORE:
                continue
            if e.a.clau() not in presents or e.b.clau() not in presents:
                continue
            clau = frozenset((e.a.clau(), e.b.clau()))
            if clau in vistes:
                continue
            vistes.add(clau)
            fora.append(e)
        return sorted(fora, key=lambda e: -e.ratio)


def carrega(garment_type_item_id=None) -> SeamExpectations:
    """Read the templates from the catalogue. Generic rows always; the GTI's own too.

    Generic AND specific, not one or the other: F3 seeded every generic row with
    `garment_type_item = NULL`, and a model whose type has its own rows should get both —
    the specific ones are a refinement of the vocabulary, not a replacement for it.
    """
    from django.db.models import Q

    from fhort.pom.models import SeamPairTemplate

    q = Q(garment_type_item__isnull=True)
    if garment_type_item_id is not None:
        q |= Q(garment_type_item_id=garment_type_item_id)

    out = []
    for t in SeamPairTemplate.objects.filter(q):
        grau, ratio = _grau(t.observed_seams, t.observed_den)
        out.append(Expectativa(
            a=Costat(t.piece_role_a_slug, t.face_a, t.edge_role_a_slug),
            b=Costat(t.piece_role_b_slug, t.face_b, t.edge_role_b_slug),
            seam_kind=t.seam_kind, grau=grau, ratio=round(ratio, 4),
            observed_seams=t.observed_seams, observed_den=t.observed_den,
            co_generated=t.co_generated, observed_ref=t.observed_ref or ''))
    return SeamExpectations(out)
