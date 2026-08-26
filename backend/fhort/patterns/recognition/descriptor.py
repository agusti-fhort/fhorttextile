"""THE shape descriptor. One definition, two callers: the GCD corpus and FTT geometry.

🚨 **This module is the single most fragile thing in F4.1, and the reason is arithmetic.**
The neighbour bank compares an FTT piece against 1,4 M corpus panels by Euclidean distance
in a 40-dimensional space. If the two sides compute that vector even slightly differently
— a different resampling count, a different mirror convention, centimetres against
millimetres — every distance is wrong and **nothing complains**: the query still returns
200 neighbours, they are just the wrong ones, and the proposal that reaches the pattern
maker is confident nonsense.

So there is ONE definition, here, and a test (`tests_recognizer.py`) that pushes the same
geometry through both paths and asserts the vectors are bit-comparable. The corpus side of
that test imports `/root/gcd_corpus/scripts/descriptors.py` — the code that actually
computed the 1,4 M rows in the database — so the test compares against the data as it is,
not against a re-reading of how it should have been.

**Provenance.** The definition below is a port of `descriptors.py` from the corpus
ingest (`/root/gcd_corpus/scripts/descriptors.py`, itself building on
`/root/n2_gym/scripts/geom.py`). It is transcribed rather than imported because those
scripts live outside the repo, under `/root`, and are not deployable: an app that only
runs when a directory outside the project exists is an app with an invisible dependency.
The test keeps the copy honest.

**Units.** The corpus is in CENTIMETRES. FTT stores geometry in MILLIMETRES
(`aama_reader.factor_to_mm`). Channels 0 and 1 of the descriptor are absolute scale, so a
factor-of-ten mistake here does not degrade the match — it destroys it. `MM_PER_CM`
exists so the conversion has a name and appears exactly once.
"""
from __future__ import annotations

import math

import numpy as np

#: Contour resampling. Must match `descriptors.N_CONTOUR`: the stored `contour_rs` of
#: every corpus panel has this many points, and the re-rank compares them index by index.
N_CONTOUR = 128
#: Harmonics kept from the radial FFT. Must match `descriptors.N_HARM`.
N_HARM = 32
#: 8 head channels + the harmonics. Must match `descriptors.DESC_DIM`.
DESC_DIM = 8 + N_HARM

#: FTT geometry is in mm, the corpus in cm. The conversion lives here and nowhere else.
MM_PER_CM = 10.0


def resample_closed(points: np.ndarray, n: int = N_CONTOUR) -> np.ndarray:
    """Uniform arc-length resampling of a closed polyline. Port of `descriptors.py`."""
    P = np.asarray(points, dtype=float)
    Q = np.vstack([P, P[:1]])
    seg = np.linalg.norm(np.diff(Q, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    total = s[-1]
    if total <= 1e-12:
        return np.repeat(P[:1], n, axis=0)
    t = np.linspace(0.0, total, n, endpoint=False)
    x = np.interp(t, s, Q[:, 0])
    y = np.interp(t, s, Q[:, 1])
    return np.stack([x, y], axis=1)


def poly_area_moments(P: np.ndarray):
    """Signed area, area centroid and second-order central moments of a polygon.

    Green's theorem over the edges, **not** a point cloud: PCA on the vertices would make
    the frame depend on how finely each edge happens to be subdivided, and CAD files
    subdivide very unevenly. Port of `n2_gym/scripts/geom.poly_area_moments`.
    """
    x = np.asarray(P[:, 0], float)
    y = np.asarray(P[:, 1], float)
    x1, y1 = np.roll(x, -1), np.roll(y, -1)
    cross = x * y1 - x1 * y
    A = 0.5 * cross.sum()
    if abs(A) < 1e-12:
        c = np.array([x.mean(), y.mean()])
        return 0.0, c, np.eye(2) * 1e-12
    cx = ((x + x1) * cross).sum() / (6.0 * A)
    cy = ((y + y1) * cross).sum() / (6.0 * A)
    c = np.array([cx, cy])
    xx = ((x * x + x * x1 + x1 * x1) * cross).sum() / 12.0
    yy = ((y * y + y * y1 + y1 * y1) * cross).sum() / 12.0
    xy = ((x * y1 + 2 * x * y + 2 * x1 * y1 + x1 * y) * cross).sum() / 24.0
    cov = np.array([[xx / A - cx * cx, xy / A - cx * cy],
                    [xy / A - cx * cy, yy / A - cy * cy]])
    return A, c, cov


def canonical_frame(P: np.ndarray, mirror: bool):
    """Centre, rotate onto the principal axis, mirror if asked. → (points, elong, area).

    Every step here has a reason and every reason is a bug that was found once:

    - **the 180° flip is resolved by the third moment**, because the principal axis is a
      line and not a direction;
    - **the winding is forced CCW AFTER the mirror**, because the mirror flips the sign,
      and doing it before makes left/right pairs traverse their contours in opposite
      directions so they can never align;
    - **the start vertex breaks ties on (x, y)**, because a rectangle (a cuff, a
      waistband) has four near-equidistant corners and an unguarded `argmax` picks a
      different one on each side of a mirror pair.

    Port of `descriptors.canonical_frame`, comments included on purpose.
    """
    A, c, cov = poly_area_moments(P)
    Q = P - c
    if mirror:
        Q = Q * np.array([-1.0, 1.0])
        cov = cov * np.array([[1.0, -1.0], [-1.0, 1.0]])
    w, V = np.linalg.eigh(cov)
    order = np.argsort(w)[::-1]
    w = w[order]
    R = V[:, order]
    if np.linalg.det(R) < 0:                 # keep a pure rotation
        R[:, 1] = -R[:, 1]
    Q = Q @ R
    m3x = (Q[:, 0] ** 3).sum()
    if m3x < 0:
        Q = Q * np.array([-1.0, -1.0])
    x, y = Q[:, 0], Q[:, 1]
    if 0.5 * float((x * np.roll(y, -1) - np.roll(x, -1) * y).sum()) < 0:
        Q = Q[::-1]
    rad = np.linalg.norm(Q, axis=1)
    cand = np.flatnonzero(rad >= rad.max() * (1.0 - 1e-6))
    k = cand[np.lexsort((Q[cand, 1], Q[cand, 0]))[-1]]
    Q = np.roll(Q, -int(k), axis=0)
    elong = math.sqrt(max(w[0], 1e-12) / max(w[1], 1e-12))
    return Q, elong, abs(A)


def descriptor(Qc: np.ndarray, area: float, perim: float,
               n_edges: int, n_curved: int) -> np.ndarray:
    """The 40-d vector. Channels 0-1 carry ABSOLUTE scale on purpose.

    The gym measured that absolute scale is the single cheapest win available
    (`INFORME_GIMNAS_N2_GARMENTCODEDATA_2026-08-25.md` §6.1: **+4,8 points on roles, +8,2
    on families**) because it is what finally separates the rectangles — collar, cuff,
    waistband, leg band — that pure shape collapses into one blob. FTT has the scale: the
    measurements are the business.

    Port of `descriptors.descriptor`, with the two panel-derived counts passed in instead
    of read off a GarmentCode spec dict — which is the whole reason this function can
    serve both callers.
    """
    r = np.linalg.norm(Qc, axis=1)
    scale = math.sqrt(max(area, 1e-9))
    rn = r / scale
    F = np.abs(np.fft.rfft(rn))
    f0 = F[0] if F[0] > 1e-12 else 1.0
    harm = (F[1:N_HARM + 1] / f0)
    if len(harm) < N_HARM:
        harm = np.pad(harm, (0, N_HARM - len(harm)))
    bw = Qc[:, 0].max() - Qc[:, 0].min()
    bh = Qc[:, 1].max() - Qc[:, 1].min()
    head = np.array([
        math.log(max(area, 1e-6)),                       # 0 absolute scale (cm2)
        math.log(max(perim, 1e-6)),                      # 1 absolute scale (cm)
        4 * math.pi * area / max(perim ** 2, 1e-9),      # 2 circularity
        bw / max(bh, 1e-9),                              # 3 bbox aspect
        rn.mean(),                                       # 4
        rn.std(),                                        # 5
        n_edges / 10.0,                                  # 6
        n_curved / max(n_edges, 1),                      # 7 curved fraction
    ], float)
    return np.concatenate([head, harm]).astype(np.float32)


def features_from_outline(outline_cm, n_edges: int, n_curved: int, mirror: bool = False):
    """**The shared entry point.** Outline in CENTIMETRES → everything the bank needs.

    Both callers land here: the corpus (via the port test) and FTT (via
    `ftt_outline_cm`). Anything that computes a descriptor without going through this
    function is, by definition, a second definition.
    """
    P = np.asarray(outline_cm, dtype=float).reshape(-1, 2)
    Qc, elong, area = canonical_frame(resample_closed(P), mirror)
    perim = float(np.linalg.norm(
        np.diff(np.vstack([Qc, Qc[:1]]), axis=0), axis=1).sum())
    return {
        'contour_rs': Qc.astype(np.float32),
        'descriptor': descriptor(Qc, area, perim, n_edges, n_curved),
        'area_cm2': float(area),
        'perimeter_cm': perim,
        'elongation': float(elong),
        'mirror_canonical': bool(mirror),
    }
