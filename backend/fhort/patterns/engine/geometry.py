"""Model geomètric intern del motor de patrons.

Aquestes dataclasses són **la veritat del motor**: tot el que entra (DXF, RUL) es
converteix aquí, i tot el que surt es genera des d'aquí. No són els models Django
(que arriben a S3 i en seran una projecció persistida): aquí no hi ha ORM ni Django.

Unitats canòniques: **mil·límetres**. El reader normalitza-hi tot i deixa constància
de com ho ha fet a `UnitsFingerprint` — perquè el factor no sempre es pot llegir: hi
ha CAD que no declaren les unitats enlloc (l'AMELIA de PolyPattern té la `HEADER`
buida) i s'han de deduir de la geometria.

Convenció de mutabilitat: tot `frozen`. Un document llegit és un fet, no un esborrany;
les transformacions (S2, S7) construeixen documents nous, no els muten.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Capes — vocabulari ASTM D6673 / ANSI-AAMA-292
# ─────────────────────────────────────────────────────────────────────────────

class LayerRole(str, Enum):
    """Rol semàntic d'una capa AAMA.

    Els codis són numèrics i **no venen declarats a la taula LAYERS** dels fitxers
    reals (l'AMELIA només hi declara '0' i 'Defpoints'): la capa és una convenció
    d'indústria, no una entitat del DXF.
    """
    CUT = 'cut'            # 1  — contorn de tall (la vora que es retalla)
    SEW = 'sew'            # 14 — línia de cosit (OPCIONAL: molts CAD no l'emeten)
    INTERNAL = 'internal'  # 8  — línies internes (pinces, butxaques, plecs)
    TURN = 'turn'          # 2  — punts de gir (cantonada dura)
    CURVE = 'curve'        # 3  — punts de corba (la vora hi flueix)
    NOTCH = 'notch'        # 4  — piquets
    GRAIN = 'grain'        # 7  — fil de la roba
    MIRROR = 'mirror'      # 6  — eix de mirall / doblec (OPCIONAL i poc fiable)
    UNKNOWN = 'unknown'    # qualsevol codi no catalogat (p.ex. el 15 d'AMELIA)


#: Codi de capa DXF → rol. El que no hi sigui és `UNKNOWN` i es preserva a l'empremta.
AAMA_LAYER_ROLES: dict[str, LayerRole] = {
    '1': LayerRole.CUT,
    '2': LayerRole.TURN,
    '3': LayerRole.CURVE,
    '4': LayerRole.NOTCH,
    '6': LayerRole.MIRROR,
    '7': LayerRole.GRAIN,
    '8': LayerRole.INTERNAL,
    '14': LayerRole.SEW,
}


class PointKind(str, Enum):
    """Naturalesa d'un vèrtex del contorn.

    La classifiquen els POINT de les capes 2 i 3, que **seuen exactament sobre el
    vèrtex** que qualifiquen (verificat: 100% de coincidència a l'AMELIA). Un vèrtex
    que cap POINT no reclama queda `UNCLASSIFIED` — és un fet del fitxer, no un error.
    """
    TURN = 'turn'
    CURVE = 'curve'
    UNCLASSIFIED = 'unclassified'


# ─────────────────────────────────────────────────────────────────────────────
# Empremta — com era el fitxer d'origen (per poder-lo reproduir a S2)
# ─────────────────────────────────────────────────────────────────────────────

class UnitsMethod(str, Enum):
    """Com s'han esbrinat les unitats. Ordre de preferència descendent."""
    HEADER = 'header'                # $INSUNITS / $MEASUREMENT
    DOCUMENT_TEXT = 'document_text'  # TEXT de metadades ('Units: Metric')
    GEOMETRY = 'geometry'            # deducció per plausibilitat dimensional
    ASSUMED = 'assumed'              # cap evidència: s'assumeix mm


class Confidence(str, Enum):
    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'


@dataclass(frozen=True)
class UnitsFingerprint:
    """Factor de conversió a mm, i **com** s'ha arribat a saber.

    El `metode` i la `confianca` no són decoració: si un dia una exportació surt a
    escala 10×, això és el registre que dirà si el factor es va llegir o endevinar.
    """
    factor_to_mm: float
    metode: UnitsMethod
    confianca: Confidence
    evidencia: str = ''


@dataclass(frozen=True)
class Fingerprint:
    """Tot el que cal per tornar a escriure un fitxer que el CAD d'origen reconegui.

    Capturar-ho a la lectura és el que fa possible el round-trip de S2: el writer no
    inventa un format, reprodueix aquest.
    """
    font_cad: str = ''                                  # 'polypattern', 'tuka'…
    dxf_version: str = ''                               # 'AC1009' (R12)
    aama_version: str = ''                              # 'ANSI/AAMA-292-B' (ve del RUL)
    autor: str = ''                                     # TEXT 'Author: PolyPattern'
    ordre_seccions: tuple[str, ...] = ()
    capes_presents: tuple[str, ...] = ()                # codis literals vistos
    capes_desconegudes: tuple[str, ...] = ()            # les que no són a AAMA_LAYER_ROLES
    capes_declarades: tuple[str, ...] = ()              # les de la taula LAYERS (sovint no hi són)
    #: Separador decimal **per camp**: les coordenades poden usar punt i els TEXT coma
    #: (cas real d'AMELIA: `613.500` però `Quantity: 1,0`).
    separador_decimal: dict[str, str] = field(default_factory=dict)
    unitats: Optional[UnitsFingerprint] = None
    cens_entitats: dict[str, int] = field(default_factory=dict)
    #: TEXTs de metadades del modelspace, literals (autoria, style name, sample size…).
    textos_document: tuple[str, ...] = ()

    def te_capa_desconeguda(self) -> bool:
        return bool(self.capes_desconegudes)


# ─────────────────────────────────────────────────────────────────────────────
# Geometria
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RawTrace:
    """Rastre literal de l'entitat d'origen.

    ezdxf preserva els tags que no entén; això és el que permet no perdre res pel camí.
    No s'interpreta: es transporta.
    """
    dxftype: str = ''
    layer: str = ''
    handle: str = ''
    extra: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class PointData:
    """Un vèrtex, ja en mm."""
    x: float
    y: float
    kind: PointKind = PointKind.UNCLASSIFIED
    #: Regla de grading assignada al punt pel CAD (TEXT '# 1' que seu sobre el punt).
    #: És la clau que lliga la geometria amb el RUL (`RULE: DELTA 1`). None = sense regla.
    grade_rule: Optional[int] = None
    raw: Optional[RawTrace] = None


@dataclass(frozen=True)
class BoundaryData:
    """Una polilínia d'una capa: el contorn de tall, una interna, la línia de cosit…"""
    role: LayerRole
    layer: str
    points: tuple[PointData, ...]
    #: Tancada. Ull: els fitxers reals **no** fan servir el flag de tancament del DXF;
    #: repeteixen el primer vèrtex al final. Això ho decideix el reader per geometria.
    closed: bool = False


@dataclass(frozen=True)
class NotchData:
    """Piquet (capa 4)."""
    x: float
    y: float
    grade_rule: Optional[int] = None
    raw: Optional[RawTrace] = None


@dataclass(frozen=True)
class GrainLineData:
    """Fil de la roba (capa 7): un segment recte."""
    x1: float
    y1: float
    x2: float
    y2: float


@dataclass(frozen=True)
class FoldData:
    """Doblec detectat PER GEOMETRIA (la capa 6 és inconsistent entre CAD).

    Quan una peça arriba a mitges, el motor la desplega (materialitza la simetria) i
    guarda aquí l'eix original, perquè S2 la pugui tornar a plegar en exportar cap a
    un CAD que treballa a mitges.
    """
    eix_x1: float
    eix_y1: float
    eix_x2: float
    eix_y2: float
    materialitzat: bool = False


@dataclass(frozen=True)
class SegmentRange:
    """Un tram d'una vora, en coordenades paramètriques.

    És la manera d'ancorar coses (costures, POMs) a la vora sense clavar-les a un
    índex de vèrtex: si la geometria es mou, el tram continua sent el mateix tram.
    """
    boundary_index: int   # índex de la BoundaryData dins la peça
    t_inici: float        # 0.0 … 1.0 sobre la longitud de la vora
    t_fi: float
    tipus_vora: LayerRole = LayerRole.CUT


@dataclass(frozen=True)
class POMAnchorData:
    """Un POM ancorat a la geometria. S1 el defineix; S6 l'omple."""
    pom_code: str
    punts_ancora: tuple[tuple[float, float], ...] = ()
    definicio_mesura: dict = field(default_factory=dict)
    valor_mesurat_mm: Optional[float] = None


@dataclass(frozen=True)
class PieceMetadata:
    """Metadades d'una peça, llegides dels TEXT de la capa 1."""
    piece_name: str = ''
    size: str = ''
    quantity: Optional[float] = None
    material: str = ''
    extra: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PieceData:
    """Una peça = un BLOCK del DXF."""
    nom_block: str
    boundaries: tuple[BoundaryData, ...] = ()
    notches: tuple[NotchData, ...] = ()
    grain: Optional[GrainLineData] = None
    metadata: PieceMetadata = field(default_factory=PieceMetadata)
    rol: Optional[str] = None                     # BACK / FRONT / … (del nom o del TEXT)
    doblec_original: Optional[FoldData] = None
    #: Flags de CAPACITAT: què porta de debò aquest fitxer. No assumir mai el que no hi és.
    has_sew: bool = False                         # capa 14 present
    has_fold: bool = False                        # doblec detectat
    unknown_layers: tuple[str, ...] = ()

    def boundary(self, role: LayerRole) -> Optional[BoundaryData]:
        """La primera vora d'un rol donat (el contorn de tall n'és una)."""
        for b in self.boundaries:
            if b.role is role:
                return b
        return None

    def boundaries_of(self, role: LayerRole) -> tuple[BoundaryData, ...]:
        return tuple(b for b in self.boundaries if b.role is role)

    @property
    def punts_totals(self) -> int:
        return sum(len(b.points) for b in self.boundaries)


# ─────────────────────────────────────────────────────────────────────────────
# Grading (llegit del RUL)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GradeRuleData:
    """Una regla de grading del RUL: quant es mou un punt a cada talla.

    Els deltes són **relatius a la talla base** i van en mm (normalitzats com la
    geometria). Que a l'AMELIA siguin tots zero no fa la regla inútil: l'estructura
    (quantes talles, quin ordre, quina base) és el que el motor ha de saber llegir.
    """
    numero: int                                   # el 'n' de `RULE: DELTA n`
    deltes: dict[str, tuple[float, float]] = field(default_factory=dict)  # talla → (dx, dy)

    def delta(self, size_label: str) -> tuple[float, float]:
        return self.deltes.get(size_label, (0.0, 0.0))


@dataclass(frozen=True)
class GradeTable:
    """El RUL sencer."""
    nom: str = ''
    talles: tuple[str, ...] = ()                  # ordre del fitxer: XS S M L XL
    talla_base: str = ''                          # SAMPLE SIZE
    regles: dict[int, GradeRuleData] = field(default_factory=dict)
    unitats: str = ''                             # 'METRIC' | 'IMPERIAL'
    aama_version: str = ''
    autor: str = ''


# ─────────────────────────────────────────────────────────────────────────────
# L'agregat
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PatternDocument:
    """Un patró sencer: les peces + com era el fitxer + (si n'hi ha) el grading."""
    pieces: tuple[PieceData, ...] = ()
    fingerprint: Fingerprint = field(default_factory=Fingerprint)
    grade_table: Optional[GradeTable] = None

    def piece(self, nom_block: str) -> Optional[PieceData]:
        for p in self.pieces:
            if p.nom_block == nom_block:
                return p
        return None

    @property
    def noms_peces(self) -> tuple[str, ...]:
        return tuple(p.nom_block for p in self.pieces)

    @property
    def te_cosit(self) -> bool:
        """Cap peça no porta línia de cosit → no es pot derivar el tall per offset."""
        return any(p.has_sew for p in self.pieces)
