"""The neighbour banks: the corpus (1,4 M panels) and the tenant's own confirmed pieces.

Two banks, on purpose, and they answer different questions:

- **`CorpusBank`** — 1,4 M GarmentCode panels. Wide, generic, and *not ours*: it knows
  what a sleeve looks like in general. It is the only thing that can say anything at all
  about a piece nobody in this workshop has ever confirmed.
- **`TenantBank`** — the pieces of THIS tenant that a human has already confirmed. Narrow,
  tiny (five pieces the day this was written), and worth more per row than the corpus by a
  wide margin: it knows what a sleeve looks like *here*, in this house's blocks, at this
  house's scale.

> **The common anonymised bank is NOT this sprint** (Agus, 26/08). The design that makes it
> possible is already here: `TenantBank` is built from a queryset, so a cross-tenant bank
> is the same class with a different queryset and an anonymisation step. What is missing is
> the consent and the anonymisation job, not the code shape.

**Everything is read-only against `ftt_corpus`.** The connection is opened `readonly=True`
on top of the `corpus_ro` role, which only has SELECT. Two locks, not one.
"""
from __future__ import annotations

import os
import re
import threading
import time

import numpy as np
from django.conf import settings

#: libpq conninfo for the read-only corpus role. Despite the name it is NOT a `.pgpass`
#: (see REPORT_GCD_CORPUS_IMPORT_2026-08-26 §3.7) — it is consumed as a connection string.
CORPUS_CONNINFO_FILE = getattr(
    settings, 'FTT_CORPUS_CONNINFO_FILE', '/root/gcd_corpus/corpus_ro.pgpass')

#: Where the built bank is cached as `.npz`. Building it from Postgres takes ~17 s and
#: 229 MB of transfer; loading the cache takes well under a second. A web worker must
#: never pay the first price.
CACHE_DIR = getattr(settings, 'FTT_RECOGNITION_CACHE_DIR',
                    os.path.join(settings.BASE_DIR, 'var', 'recognition'))

#: 🚨 **Channels 6 and 7 are masked for CORPUS queries, and it is not an optimisation.**
#: Channel 6 is the edge count and channel 7 the curved fraction. A GarmentCode edge is a
#: PARAMETRIC edge — one cubic Bezier can be a whole armhole — while an FTT edge count
#: comes from DXF turn points, where the same armhole is one span with a hundred vertices
#: inside it. Measured 2026-08-26: corpus median **5** edges per panel (mean 6,68) against
#: **8-28** turn points on the five 837 pieces. The two numbers do not measure the same
#: thing, and feeding them to the same channel puts a constant bias on every corpus query
#: that nothing would ever report. The TENANT bank does NOT mask them: there both sides
#: are DXF and the count is the same count.
CORPUS_MASKED_CHANNELS = (6, 7)

#: Panel name → GarmentCode role. Four passes because GarmentCode puts the side in three
#: different places depending on the family (`left_ftorso`, `sl_left_cuff_f`,
#: `pant_l_cuff_f`, `pant_f_l`). Verified over all 128.974 designs: exactly 24 roles.
_NORM = [
    (re.compile(r'^(left|right)_'), ''),
    (re.compile(r'^sl_(left|right)_'), 'sl_'),
    (re.compile(r'^pant_(l|r)_'), 'pant_'),
    (re.compile(r'(_(l|r)|_[0-9]+)$'), ''),
]


def gc_role_of(panel_name: str) -> str:
    out = panel_name
    for rx, rep in _NORM:
        out = rx.sub(rep, out)
    return out


def corpus_conninfo(path: str = None) -> str:
    with open(path or CORPUS_CONNINFO_FILE) as f:
        return ' '.join(ln.strip() for ln in f
                        if ln.strip() and not ln.lstrip().startswith('#'))


class _BankArrays:
    """The z-scored search structure shared by both banks.

    The z-score is not cosmetic: channel 0 is a log-area in the units of nature and the
    harmonics are ratios near zero. Without whitening, the distance is whatever the
    largest-variance channel says and the other 39 are decoration.
    """

    def __init__(self, X, labels: dict):
        self.X = np.ascontiguousarray(np.asarray(X, dtype=np.float32))
        self.labels = labels
        self.mu = self.X.mean(0)
        self.sd = self.X.std(0)
        self.sd[self.sd < 1e-8] = 1.0
        self._Z = None
        self._masked = None

    def __len__(self):
        return len(self.X)

    def _z(self, masked_channels):
        key = tuple(masked_channels or ())
        if self._Z is None or self._masked != key:
            Z = (self.X - self.mu) / self.sd
            if key:
                Z = Z.copy()
                Z[:, list(key)] = 0.0
            self._Z = np.ascontiguousarray(Z)
            self._masked = key
        return self._Z

    def query(self, vec, k=200, masked_channels=(), exclude=None):
        """→ `(indices, distances)`, nearest first.

        `exclude` is a boolean mask of rows to ignore. It is how a query avoids matching
        itself, and — more importantly for the exam — how a piece avoids matching the
        other pieces of its own pattern file, which would be marking your own homework.
        """
        Z = self._z(masked_channels)
        q = (np.asarray(vec, np.float32) - self.mu) / self.sd
        if masked_channels:
            q = q.copy()
            q[list(masked_channels)] = 0.0
        d = np.linalg.norm(Z - q[None, :], axis=1)
        if exclude is not None:
            d = np.where(exclude, np.inf, d)
        n = len(d)
        if n == 0:
            return np.empty(0, dtype=int), d
        kk = min(k, n)
        idx = np.argpartition(d, kk - 1)[:kk]
        return idx[np.argsort(d[idx])], d


# ═══════════════════════════════════════════════════════════════════════════════
# Corpus bank
# ═══════════════════════════════════════════════════════════════════════════════

_CORPUS_LOCK = threading.Lock()
_CORPUS_CACHE: dict = {}


def cache_path(fraction: int) -> str:
    return os.path.join(CACHE_DIR, 'corpus_bank_1in{}.npz'.format(fraction))


def build_corpus_cache(fraction: int = 1, conninfo_file: str = None) -> dict:
    """Read `ftt_corpus` once and write the `.npz`. → stats dict.

    `fraction` keeps one row in N, **deterministically and proportionally** (`id % N == 0`).
    Proportional and not stratified on purpose: the natural role distribution IS the prior,
    and the gym measured that the prior is worth +8,1 points on families
    (`INFORME_GIMNAS_N2_GARMENTCODEDATA_2026-08-25.md` §6.4). Flattening it to equalise
    the classes would throw that away to buy nothing.
    """
    import psycopg2

    os.makedirs(CACHE_DIR, exist_ok=True)
    conn = psycopg2.connect(corpus_conninfo(conninfo_file))
    t0 = time.time()
    try:
        conn.set_session(readonly=True, autocommit=True)
        with conn.cursor() as cur:
            where = 'TRUE' if fraction <= 1 else 'p.id % {} = 0'.format(fraction)
            cur.execute(
                'SELECT p.id, p.design_id, p.family, p.side, p.name, d.garment_category, '
                '       p.area_cm2, p.descriptor '
                'FROM panel p JOIN design d ON d.id = p.design_id '
                'WHERE {} ORDER BY p.id'.format(where))
            rows = cur.fetchall()
    finally:
        conn.close()

    X = np.asarray([r[7] for r in rows], dtype=np.float32)
    out = dict(
        panel_id=np.asarray([r[0] for r in rows], dtype=np.int64),
        design_id=np.asarray([r[1] for r in rows], dtype=np.int64),
        family=np.asarray([r[2] for r in rows]),
        side=np.asarray([r[3] for r in rows]),
        gc_role=np.asarray([gc_role_of(r[4]) for r in rows]),
        category=np.asarray([r[5] for r in rows]),
        area_cm2=np.asarray([r[6] for r in rows], dtype=np.float32),
        X=X,
    )
    np.savez_compressed(cache_path(fraction), **out)
    return {'rows': len(rows), 'seconds': round(time.time() - t0, 1),
            'megabytes': round(X.nbytes / 1e6, 1),
            'path': cache_path(fraction),
            'roles': int(len(set(out['gc_role'].tolist())))}


class CorpusBank:
    """The GarmentCode bank, lazily loaded from the `.npz` and cached per process."""

    def __init__(self, fraction: int, data: dict):
        self.fraction = fraction
        self.gc_role = data['gc_role']
        self.design_id = data['design_id']
        self.family = data['family']
        self.category = data['category']
        self.area_cm2 = data['area_cm2']
        self.arrays = _BankArrays(data['X'], {})

    def __len__(self):
        return len(self.arrays)

    def neighbours(self, vec, k=200):
        idx, d = self.arrays.query(vec, k=k, masked_channels=CORPUS_MASKED_CHANNELS)
        return [
            {'gc_role': str(self.gc_role[i]), 'family': str(self.family[i]),
             'category': str(self.category[i]), 'design_id': int(self.design_id[i]),
             'area_cm2': float(self.area_cm2[i]), 'dist': float(d[i])}
            for i in idx
        ]


def get_corpus_bank(fraction: int = None) -> CorpusBank:
    """Lazy, process-cached, invalidable (`invalidate_corpus_bank`)."""
    fraction = fraction or getattr(settings, 'FTT_RECOGNITION_CORPUS_FRACTION', 5)
    with _CORPUS_LOCK:
        bank = _CORPUS_CACHE.get(fraction)
        if bank is None:
            path = cache_path(fraction)
            if not os.path.exists(path):
                raise FileNotFoundError(
                    'corpus bank cache missing: {}. Build it with '
                    '`manage.py build_recognition_bank`.'.format(path))
            with np.load(path, allow_pickle=False) as z:
                bank = CorpusBank(fraction, {k: z[k] for k in z.files})
            _CORPUS_CACHE[fraction] = bank
        return bank


def invalidate_corpus_bank() -> None:
    with _CORPUS_LOCK:
        _CORPUS_CACHE.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# Tenant bank
# ═══════════════════════════════════════════════════════════════════════════════

class TenantBank:
    """This tenant's CONFIRMED pieces, in the same descriptor space.

    Built from a queryset so the same class serves a future cross-tenant bank; built at
    call time and not cached because it is small and because a bank that goes stale the
    moment somebody confirms a piece would be worse than no bank at all.

    Full fidelity, no anonymisation: this is the tenant's own data staying inside the
    tenant (Agus, 26/08).
    """

    def __init__(self, rows: list):
        self.rows = rows
        self.arrays = _BankArrays(
            np.asarray([r['descriptor'] for r in rows], dtype=np.float32).reshape(-1, 40)
            if rows else np.zeros((0, 40), np.float32), {})

    def __len__(self):
        return len(self.rows)

    def neighbours(self, vec, k=20, exclude_file_ids=()):
        if not self.rows:
            return []
        excl = np.asarray(
            [r['pattern_file_id'] in exclude_file_ids for r in self.rows], dtype=bool)
        idx, d = self.arrays.query(vec, k=k, exclude=excl)
        out = []
        for i in idx:
            if not np.isfinite(d[i]):
                continue
            r = dict(self.rows[i])
            r['dist'] = float(d[i])
            r.pop('descriptor', None)
            out.append(r)
        return out


def build_tenant_bank(queryset=None) -> TenantBank:
    """Every piece of this tenant with a CONFIRMED role, projected into the bank space.

    ⚠️ Confirmed means `piece_role` — the human's field. `proposed_role` is deliberately
    NOT eligible: a bank fed by its own proposals would agree with itself a little more
    every import, and the confidence would rise while the accuracy did not.
    """
    from fhort.patterns.models import PatternPiece

    from .ftt_geometry import NoGeometry, features_of_piece

    qs = queryset if queryset is not None else PatternPiece.objects.all()
    qs = (qs.filter(piece_role__isnull=False)
            .select_related('piece_role').prefetch_related('points'))
    rows = []
    for piece in qs:
        try:
            feats = features_of_piece(piece)
        except (NoGeometry, ValueError, IndexError, StopIteration):
            continue
        rows.append({
            'piece_id': piece.pk,
            'pattern_file_id': piece.pattern_file_id,
            'nom_block': piece.nom_block,
            'ftt_slug': piece.piece_role.slug,
            'face': piece.face,
            'lateralitat': piece.lateralitat,
            'area_cm2': feats['area_cm2'],
            'descriptor': feats['descriptor'],
        })
    return TenantBank(rows)
