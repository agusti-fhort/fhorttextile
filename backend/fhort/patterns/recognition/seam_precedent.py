"""FASE B · THE TENANT'S PRECEDENT: what this house has already sewn, in its own vocabulary.

The catalogue says what garments in general do. This says what **this workshop** did, on a
pattern somebody here confirmed. When the two agree, a proposal is standing on the corpus and
on the house at once; when only the house agrees, that is often the more useful signal —
`collar_attach↔neckline` is rare in the corpus (0,157) and the 837 has it.

**Transfer is by ROLE, never by geometry.** Two dresses whose fronts and backs carry the same
edge roles are sewn the same way even when nothing about their curves matches — that is the
entire reason F4.2 taught the edges to have names. A precedent that compared shapes would be
the corpus bank of F4.1 again, which measured 13 % and was retired.

⚠️ **The bank is only as big as what humans have confirmed, and today that is one model.**
`SewRelation` has 8 rows, all on the 837 (model 1383), and they are the whole precedent. This
module is written to be right at that size and to get better on its own as people confirm
more; it is NOT written to pretend eight rows are a statistic.

🚨 **A precedent is read from CONFIRMED seams and confirmed edge roles only.** Nothing this
module returns was ever produced by a proposer — otherwise the system would be learning from
its own guesses, which is exactly the trap `PatternPiece.rol_origen` exists to keep open to
inspection.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Precedent:
    """One pair of sides that this tenant has already sewn, and where."""

    clau: frozenset
    model_id: int
    model_nom: str
    seam_kind: str
    vegades: int = 1

    def frase(self) -> str:
        return ('this workshop already sews this pair on «{}»'.format(self.model_nom)
                if self.vegades == 1 else
                'this workshop already sews this pair on «{}» and {} more'
                .format(self.model_nom, self.vegades - 1))


class SeamPrecedents:
    """Confirmed seams of the tenant, indexed by the pair of role-sides they join."""

    def __init__(self, precedents: list[Precedent]):
        self._per_parella: dict[frozenset, Precedent] = {}
        for p in precedents:
            vell = self._per_parella.get(p.clau)
            if vell is None:
                self._per_parella[p.clau] = p
            else:
                self._per_parella[p.clau] = Precedent(
                    clau=p.clau, model_id=vell.model_id, model_nom=vell.model_nom,
                    seam_kind=vell.seam_kind, vegades=vell.vegades + 1)

    def __len__(self) -> int:
        return len(self._per_parella)

    @staticmethod
    def costat_de(candidat):
        """A `Candidat` → its catalogue side. Same contract as `SeamExpectations.costat_de`."""
        from .seam_expectations import SeamExpectations
        return SeamExpectations.costat_de(candidat)

    def per_parella(self, a, b) -> Precedent | None:
        if not a.edge_role or not b.edge_role:
            return None
        return self._per_parella.get(frozenset((a.clau(), b.clau())))


def carrega(exclou_model_id=None, rols_en_memoria: dict | None = None) -> SeamPrecedents:
    """Build the bank from the tenant's CONFIRMED seams. → `SeamPrecedents`.

    `exclou_model_id` keeps a model out of its own bank. Without it, running the proposer on
    the 837 would find the 837's own seams as precedent and report perfect confidence about
    nothing — the identical mistake `recognition.service.exclude_self` exists to prevent.

    `rols_en_memoria` (`{segment_id: edge_role_slug}`) lets the EXAM supply edge roles that
    no human has confirmed yet, so the mechanism can be measured without writing a single
    row. It is never passed in production: there, a role comes from the database or the seam
    contributes nothing.

    🚨 **Confirmed seams live on DECLARED segments; edge roles live on NATURAL ones.** They
    are two different populations over the same outline (measured, FASE 0), so a seam's side
    is resolved to the natural segment that covers most of it. A declared span that no
    natural segment covers contributes nothing rather than guessing.
    """
    from fhort.patterns.models import PatternSegment, SewRelation

    from .seam_expectations import Costat

    rols_en_memoria = rols_en_memoria or {}

    relacions = list(SewRelation.objects.all().prefetch_related(
        'segments_a__piece__piece_role', 'segments_b__piece__piece_role', 'model'))
    if exclou_model_id is not None:
        relacions = [r for r in relacions if r.model_id != exclou_model_id]
    if not relacions:
        return SeamPrecedents([])

    peces = set()
    for r in relacions:
        for d in list(r.segments_a.all()) + list(r.segments_b.all()):
            peces.add(d.piece_id)
    naturals: dict[int, list] = {}
    for s in PatternSegment.objects.filter(
            piece_id__in=peces, origen=PatternSegment.ORIGEN_NATURAL).select_related('edge_role'):
        naturals.setdefault(s.piece_id, []).append(s)

    out = []
    for r in relacions:
        costats = []
        for m2m in (r.segments_a, r.segments_b):
            declarats = list(m2m.all())
            if not declarats:
                costats.append(None)
                continue
            costats.append(_costat_de(declarats[0], naturals, rols_en_memoria))
        a, b = costats
        if a is None or b is None or not a.edge_role or not b.edge_role:
            continue
        out.append(Precedent(
            clau=frozenset((a.clau(), b.clau())), model_id=r.model_id,
            model_nom=str(getattr(r.model, 'nom_prenda', '') or r.model_id),
            seam_kind=r.tipus))
    return SeamPrecedents(out)


def _costat_de(declarat, naturals, rols_en_memoria):
    """A declared span → the catalogue side of the natural segment that covers most of it."""
    from .seam_expectations import Costat

    peca = declarat.piece
    rol = peca.piece_role.slug if peca.piece_role_id else ''
    millor, cobert = None, 0.0
    for n in naturals.get(declarat.piece_id, []):
        if n.vora != declarat.vora:
            continue
        c = _solapament(declarat.t_inici, declarat.t_fi, n.t_inici, n.t_fi)
        if c > cobert:
            millor, cobert = n, c
    if millor is None or cobert <= 0:
        return Costat(rol, peca.face or '', '')
    slug = (millor.edge_role.slug if millor.edge_role_id
            else rols_en_memoria.get(millor.pk, ''))
    return Costat(rol, peca.face or '', slug or '')


def _solapament(a0, a1, b0, b1) -> float:
    """Overlap of two `t` ranges on a CLOSED boundary, wrapping included.

    🚨 A span with `t_fi < t_inici` runs through the origin of the boundary — documented on
    `PatternSegment.t_inici` — so a plain `min`/`max` would silently read it as the whole rest
    of the outline. Measured in FASE 0: it mismatched a back armhole against the neckline.
    Wrapping ranges are split in two and compared piecewise.
    """
    def trossos(t0, t1):
        return [(t0, t1)] if t0 <= t1 else [(t0, 1.0), (0.0, t1)]

    total = 0.0
    for x0, x1 in trossos(a0, a1):
        for y0, y1 in trossos(b0, b1):
            total += max(0.0, min(x1, y1) - max(x0, y0))
    return total
