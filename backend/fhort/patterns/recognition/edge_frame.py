"""The PIECE FRAME: which way is up, when the sheet does not say.

🚨 **THE FINDING THAT MADE THIS MODULE NECESSARY.** Every rule the edge catalogue speaks
in — "the hem is the lowest edge", "the shoulder is at the top", "the neckline sits on the
axis" — is a statement about the GARMENT's vertical, not the drawing's. On the workshop's
own material those two are not the same axis, and it is not a near miss: of the 60 pieces
in the tenant, **not one carries a vertical grain line**, and the 837's five pieces all lie
turned a quarter turn, garment-vertical running along the sheet's X.

Read raw sheet coordinates and every one of those rules is wrong by 90°. The measured
consequence is not subtle either: `pom.landmarks._verifica_highest_y` — the sanity check
that is supposed to catch a mislabelled neckline — REJECTS the 837's true HPS, because in
sheet coordinates that point is nowhere near the highest. The verifier was right to shout;
what was wrong was the frame it was shown.

**The grain line is the answer, and it is not a proxy for one.** Warp runs up and down the
body: that is what a grain line MEANS, and it is why the CAD draws it. All 60 pieces carry
one (`PatternPiece.grain`, 60/60), and on the 837 it lands on the symmetry axis to within a
millimetre — grain y=1054,0 against an axis measured at y=1053,15.

⚠️ **A grain line is a LINE, and a line has no up.** It fixes the axis and leaves the sign
free, and nothing in the DXF fills that in. This module does not guess: it hands out BOTH
signs and lets the labelling compete on them (`edge_labeler.label_piece`). Structure decides
which way the garment stands — a hem scored against the neck end scores badly — and if the
two hypotheses tie, the piece says nothing. That is the honest answer to a question the
file genuinely does not contain.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

#: A grain line shorter than this is noise, not a direction: two coincident points give an
#: angle of zero and would silently declare the sheet's own X to be the garment's vertical.
MIN_GRAIN_MM = 1.0


class NoFrame(Exception):
    """The piece carries no usable grain line. A silence, not a failure."""


@dataclass(frozen=True)
class PieceFrame:
    """Sheet coordinates → garment coordinates `(u, v)`.

    `u` runs along the grain: the garment's vertical, positive towards whichever end this
    hypothesis calls the top. `v` is the perpendicular, measured **from the grain line
    itself**, so `v = 0` is the axis a centre-front seam or a fold would sit on.

    Frozen and arithmetic-only: the frame is a fact about a piece, not a state anybody
    edits, and every consumer must be able to build one in a test without a database.
    """

    #: Origin: a point on the grain line, in sheet mm.
    ox: float
    oy: float
    #: Unit vector along the grain, in sheet mm.
    ux: float
    uy: float
    #: Which of the two signs this frame is. Carried so evidence can name it.
    flipped: bool = False

    def to_frame(self, x: float, y: float) -> tuple[float, float]:
        """One sheet point → `(u, v)`. The only conversion in the system."""
        dx, dy = x - self.ox, y - self.oy
        # v uses the left normal of u, so (u, v) stays a right-handed pair and a mirror
        # never sneaks in through the frame.
        return (dx * self.ux + dy * self.uy, -dx * self.uy + dy * self.ux)

    def flip(self) -> PieceFrame:
        """The same axis, the other way up. The second hypothesis."""
        return PieceFrame(self.ox, self.oy, -self.ux, -self.uy, not self.flipped)


def frame_of_grain(grain: dict | None) -> PieceFrame:
    """`PatternPiece.grain` → the frame with the arbitrary sign. Raises `NoFrame`.

    The sign here carries no claim at all: it is whichever way the CAD happened to draw
    the arrow. `edge_labeler` tries this frame and `frame.flip()` and keeps the one the
    structure prefers.
    """
    if not grain:
        raise NoFrame('the piece has no grain line, so it has no garment vertical')
    try:
        x1, y1 = float(grain['x1']), float(grain['y1'])
        x2, y2 = float(grain['x2']), float(grain['y2'])
    except (KeyError, TypeError, ValueError):
        raise NoFrame('the grain line is not two readable points')
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length < MIN_GRAIN_MM:
        raise NoFrame(
            'the grain line is {:.3g} mm long, which is not a direction'.format(length))
    return PieceFrame(ox=x1, oy=y1, ux=dx / length, uy=dy / length)
