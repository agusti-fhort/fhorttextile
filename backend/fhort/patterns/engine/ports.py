"""Ports del motor — els únics forats per on el món hi entra.

Frontera hexagonal: aquí es declaren **contractes** (Protocols + dataclasses), mai
implementacions que sàpiguen de Django. Els adaptadors viuen fora d'`engine/`
(`patterns/adapters.py`, `models.py`, `views.py` — S3).

Tres ports:
  · `FormatCodec`   — llegir/escriure un format de fitxer (DXF-AAMA, RUL…).
  · `GradingSource` — d'on surten els deltes per POM×talla. **L'ÚNICA interfície del
                      motor amb el grading de l'FTT.**
  · `GeometryStore` — on es desa el resultat.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable

from .geometry import GradeTable, PatternDocument


# ─────────────────────────────────────────────────────────────────────────────
# Port 1 — FormatCodec
# ─────────────────────────────────────────────────────────────────────────────

@runtime_checkable
class FormatCodec(Protocol):
    """Llegeix i escriu un format de patró.

    `read` mai llança una excepció crua: o torna un `PatternDocument`, o llança
    `PatternParseError` amb els problemes detallats (errors.py).

    `write` reprodueix el format d'origen a partir de l'empremta del document; el
    `perfil` tria el dialecte de destí ('polypattern', 'tuka'…). S2 l'implementa.
    """

    def read(self, data: bytes) -> PatternDocument: ...

    def write(self, doc: PatternDocument, perfil: str = '') -> bytes: ...


@runtime_checkable
class GradeCodec(Protocol):
    """Llegeix i escriu la taula de grading (RUL)."""

    def read(self, data: bytes) -> GradeTable: ...

    def write(self, table: GradeTable) -> bytes: ...


# ─────────────────────────────────────────────────────────────────────────────
# Port 2 — GradingSource  (contracte clavat a la diagnosi S0 §B7.4)
# ─────────────────────────────────────────────────────────────────────────────
#
# Transcripció literal del contracte verificat contra el codi real de l'FTT. Els
# comentaris no són color: cadascun tapa una manera documentada d'equivocar-se.

@dataclass(frozen=True)
class GradedPOMDelta:
    """Una cel·la de la matriu POM × talla."""
    pom_id: int          # fitting_gradedspec.pom_id → pom.POMMaster (PK, MAI el codi)
    pom_code: str        # llegible (POMMaster.pom_code / codi_client)
    size_label: str      # STRING lliure, NO és FK: ve de Model.size_run_model
    value_cm: float      # graded_value_cm — valor ABSOLUT, en cm
    delta_cm: float      # increment_applied_cm — DELTA vs la base. **+ = talla MÉS GRAN**
    rule_applied: str    # LINEAR | STEP | FIXED | ZERO | EXCEPTION


@dataclass(frozen=True)
class GradingSnapshot:
    """El grading d'una versió CONCRETA, congelat.

    L'entrada del port és sempre un `grading_version_id` **explícit**: és el que
    esquiva les col·lisions dual-path (G6) del grading de l'FTT, que té set camins de
    lectura diferents per decidir "quina versió mana". Aquí no es decideix: es rep.
    """
    grading_version_id: int
    approved: bool           # GradingVersion.aprovada — el port EXIGEIX True

    # ── Context OBLIGATORI. NO és derivable dels deltes: ve del Model, per
    #    grading_version.size_fitting.model (GradingVersion NO té FK a Model).
    base_size_label: str     # Model.base_size_label
    size_run: tuple[str, ...]  # Model.size_run_model, ORDENAT

    # ── La matriu. Pot tenir FORATS: una cel·la STEP invàlida no genera fila.
    deltas: tuple[GradedPOMDelta, ...] = ()

    def delta(self, pom_id: int, size_label: str) -> Optional[GradedPOMDelta]:
        for d in self.deltas:
            if d.pom_id == pom_id and d.size_label == size_label:
                return d
        return None  # forat legítim, no error

    @property
    def base_index(self) -> int:
        """Posició de la talla base dins el size run.

        ⚠️ La talla base **NO s'infereix mai d'un `delta_cm == 0`**: un POM amb regla
        ZERO té delta 0 a TOTES les talles. Ve declarada, i prou.
        """
        return self.size_run.index(self.base_size_label)


@runtime_checkable
class GradingSource(Protocol):
    """L'única porta entre el motor de patrons i el grading de l'FTT.

    Implementació (S3/S7): un adaptador que llegeix `GradedSpec` filtrant per
    `grading_version_id` i `is_active=True` — lectura determinista, garantida per
    l'unique `(grading_version, pom, size_label)` que existeix a la BD.

    Guard dur del consumidor: si `snapshot.approved` és False → error. I el guard
    s'ha d'implementar amb `filter(pk=...)`, **mai** amb `get(aprovada=True)`:
    estructuralment poden coexistir diverses versions aprovades per SizeFitting (cap
    constraint no ho impedeix) i el `get` petaria amb MultipleObjectsReturned.
    """

    def snapshot(self, grading_version_id: int) -> GradingSnapshot: ...


# ─────────────────────────────────────────────────────────────────────────────
# Port 3 — GeometryStore
# ─────────────────────────────────────────────────────────────────────────────

@runtime_checkable
class GeometryStore(Protocol):
    """Persistència del resultat. L'engine no sap què hi ha a l'altra banda.

    L'adaptador de S3 (`DjangoGeometryStore`) tradueix dataclasses ↔ ORM en les dues
    direccions; el motor només veu aquests dos verbs.
    """

    def save(self, doc: PatternDocument, **context) -> int: ...

    def load(self, pattern_file_id: int) -> PatternDocument: ...
