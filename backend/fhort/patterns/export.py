"""Exportació de la niada: de la BD a un DXF+RUL que un CAD de patronatge reconegui.

El pipeline sencer, en ordre, i cap pas és opcional:

    geometria (BD) ──┐
                     ├─→ PROJECCIÓ (grading pinçat) ─→ WRITER ─→ AUTOVALIDACIÓ ─→ bytes
    GradedSpec ──────┘                                              │
    (versió aprovada, explícita)                                    └─ si falla: CAP byte

L'AUTOVALIDACIÓ NO ÉS UN TEST: ÉS UNA PORTA
--------------------------------------------
Abans de deixar sortir res, el motor **es rellegeix a si mateix**: torna a parsejar el
fitxer que acaba d'emetre i el compara amb el que volia dir. Dues voltes, no una —
`write→read→write→read` — perquè una volta demostra que sabem escriure i llegir el nostre
propi format, i dues demostren que el resultat és **estable**: que no hi ha res que es vagi
degradant a cada viatge.

Si el comparador troba qualsevol diferència, l'exportació **no surt**. Ni amb un avís, ni
amb un fitxer "gairebé bo". Un DXF que ha perdut un punt pel camí no és un fitxer amb un
defecte: és un patró equivocat que algú tallarà. Val infinitament més un error a la
pantalla que una peça mal tallada a la taula.

Això no és una precaució teòrica: és l'única cosa que ens separa d'enviar geometria
corrupta a un client, i és barata (el comparador ja existeix des de S2 i és l'eina
permanent de tota exportació futura).

QUÈ SURT
--------
- **DXF**: la geometria de la TALLA MOSTRA —intacta— amb un **número de regla assegut a
  cada punt** de gir i a cada piquet, més la capa `FTT-POM` amb les mesures ancorades.
- **RUL**: la taula de regles poblada, amb el size run i la talla base DEL MODEL.

El CAD del client reconstrueix cada talla amb `punt_base + delta(regla, talla)`. No li
enviem cinc geometries: li enviem un patró que el seu CAD sap graduar.

QUÈ NO ES PERSISTEIX (decisió v1, anotada a posta)
--------------------------------------------------
El fitxer generat **NO** es desa com un `PatternFile` nou. Es genera, es serveix, i el que
queda a la BD és l'`ExportAcknowledgement`: qui va exportar, quan, de quina versió de
patró i amb quin grading. Persistir el generat és una decisió posterior —vol dir decidir
si un fitxer que hem fabricat nosaltres entra a la mateixa cadena de versions que els que
ens dona el client, i això té conseqüències (¿es pot reimportar sobre si mateix? ¿què vol
dir "versió actual" si n'hi ha un de generat?)— i no es pren de passada.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone

from .adapters import (
    DjangoGeometryStore,
    DjangoGradingSource,
    GradingVersionNotFound,
    pom_specs,
    sew_specs,
)
from .engine.aama_reader import AAMAReader
from .engine.aama_writer import AAMAWriter, UnknownProfileError
from .engine.errors import PatternEngineError
from .engine.geometry import POMAnchorData
from .engine.grading_projection import (
    GradingContextError,
    GradingNotApproved,
    ProjectionResult,
    SizePreview,
    preview_per_talla,
    project,
)
from .engine.roundtrip import compare, compare_grade_tables
from .engine.rul_reader import RULReader
from .engine.rul_writer import RULWriter

MM_PER_CM = 10.0

#: Perfils de destí que es poden triar. `polypattern` és l'únic amb material real al
#: darrere; la resta no s'ofereixen perquè escriure'n l'empremta sense haver vist mai un
#: fitxer d'aquell CAD seria inventar-se-la, i un round-trip verd contra una empremta
#: inventada és pitjor que no tenir-ne cap: dona confiança falsa.
PERFILS_DISPONIBLES = {
    'polypattern': {'actiu': True, 'motiu': ''},
    'tuka': {'actiu': False, 'motiu': 'Cap fitxer real de Tuka per derivar-ne l\'empremta.'},
    'gerber': {'actiu': False, 'motiu': 'Cap fitxer real de Gerber per derivar-ne l\'empremta.'},
    'clo': {'actiu': False, 'motiu': 'Cap fitxer real de CLO per derivar-ne l\'empremta.'},
}


class ExportBlocked(PatternEngineError):
    """L'exportació s'ha aturat. Porta el motiu i, si l'ha aturat l'autovalidació, les
    diferències exactes que ha trobat."""

    def __init__(self, missatge: str, detall: dict | None = None):
        super().__init__(missatge)
        self.missatge = missatge
        self.detall = detall or {}

    def as_dict(self) -> dict:
        return {'error': self.missatge, 'detall': self.detall}


@dataclass(frozen=True)
class Autovalidacio:
    """El veredicte de rellegir-nos a nosaltres mateixos."""
    ok: bool
    punts_comparats: int = 0
    desviacio_maxima_um: float = 0.0
    regles_escrites: int = 0
    regles_rellegides: int = 0
    diferencies: tuple[str, ...] = ()
    #: Cens d'entitats a cada volta. Si les dues voltes no donen el mateix, el format no
    #: és estable i el fitxer no surt.
    cens_volta_1: int = 0
    cens_volta_2: int = 0

    def resum(self) -> str:
        if self.ok:
            return (
                f'✅ Autovalidació: {self.punts_comparats} punts rellegits sense cap '
                f'desviació (màx. {self.desviacio_maxima_um:.3f} µm), '
                f'{self.regles_rellegides}/{self.regles_escrites} regles idèntiques, '
                f'cens immòbil ({self.cens_volta_1} entitats a les dues voltes).'
            )
        return (
            f'❌ Autovalidació FALLIDA: {len(self.diferencies)} diferències entre el que '
            f'volíem escriure i el que hem rellegit.'
        )


@dataclass(frozen=True)
class ExportResult:
    """Els bytes, i tot el que caldria per defensar-los."""
    dxf: bytes
    rul: bytes
    nom_dxf: str
    nom_rul: str
    projeccio: ProjectionResult
    previews: tuple[SizePreview, ...]
    autovalidacio: Autovalidacio
    problemes_poms: tuple[str, ...] = field(default_factory=tuple)
    problemes_costures: tuple[str, ...] = field(default_factory=tuple)


# ═════════════════════════════════════════════════════════════════════════════

def build_export(
    pattern_file,
    grading_version_id: int,
    destination_profile: str = 'polypattern',
    ts: str = '',
) -> ExportResult:
    """El pipeline sencer. O torna bytes bons, o llança `ExportBlocked`.

    No hi ha terme mitjà a posta: qui crida això no ha de poder rebre un fitxer "amb
    avisos" i decidir si l'envia. Si no és bo, no és.
    """
    perfil = PERFILS_DISPONIBLES.get(destination_profile)
    if perfil is None:
        raise ExportBlocked(
            f'El perfil de destí «{destination_profile}» no existeix. '
            f'Disponibles: {sorted(PERFILS_DISPONIBLES)}.'
        )
    if not perfil['actiu']:
        raise ExportBlocked(
            f'El perfil «{destination_profile}» no està implementat: {perfil["motiu"]} '
            f'Un perfil s\'escriu amb un fitxer real d\'aquell CAD al davant, mai d\'esma.'
        )

    # ── 1. La geometria i les anotacions que hi pengen.
    doc = DjangoGeometryStore().load_from(pattern_file)
    specs, problemes = pom_specs(pattern_file)
    sews, problemes_sews = sew_specs(pattern_file)

    # ── 2. El grading, PINÇAT: la versió ve donada, no es tria.
    try:
        snapshot = DjangoGradingSource().snapshot(grading_version_id)
    except GradingVersionNotFound as e:
        raise ExportBlocked(str(e)) from e

    try:
        projeccio = project(doc, snapshot, specs, sews)
    except (GradingNotApproved, GradingContextError) as e:
        raise ExportBlocked(str(e)) from e

    previews = preview_per_talla(doc, projeccio, snapshot, specs, sews)

    # ── 3. La capa FTT-POM: les mesures, dibuixades dins el fitxer. I la taula de grading
    #       del document passa a ser LA NOSTRA: la que venia dins el fitxer del client
    #       graduava unes altres talles sobre una altra base (AMELIA: XS-S-M-L-XL sobre M)
    #       i deixar-la-hi faria que el DXF i el RUL germà diguessin coses diferents.
    doc_final = replace(
        _amb_capa_pom(projeccio.document, specs, previews),
        grade_table=projeccio.grade_table,
    )

    # ── 4. Escriure.
    meta = {
        'versio': pattern_file.versio,
        'model': _codi_model(pattern_file),
        'ts': ts or datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    }
    try:
        dxf = AAMAWriter().write(
            doc_final,
            perfil=destination_profile,
            include_ftt_pom_layer=True,
            ftt_meta=meta,
        )
    except UnknownProfileError as e:
        raise ExportBlocked(str(e)) from e

    rul = RULWriter().write(projeccio.grade_table)

    # ── 5. La porta: rellegir-nos abans de deixar sortir res.
    auto = _autovalidar(doc_final, projeccio, dxf, rul, destination_profile)
    if not auto.ok:
        raise ExportBlocked(
            'L\'exportació s\'ha ATURAT: el fitxer que el motor ha generat no es torna a '
            'llegir igual que el que volia escriure. No surt cap byte. '
            'Un DXF que ha perdut alguna cosa pel camí no és un fitxer amb un defecte: és '
            'un patró equivocat que algú tallaria.',
            detall={
                'diferencies': list(auto.diferencies),
                'punts_comparats': auto.punts_comparats,
                'desviacio_maxima_um': auto.desviacio_maxima_um,
                'cens_volta_1': auto.cens_volta_1,
                'cens_volta_2': auto.cens_volta_2,
            },
        )

    base = (pattern_file.nom_fitxer or 'patro.dxf').rsplit('.', 1)[0]
    return ExportResult(
        dxf=dxf,
        rul=rul,
        nom_dxf=f'{base}_niada.dxf',
        nom_rul=f'{base}_niada.rul',
        projeccio=projeccio,
        previews=previews,
        autovalidacio=auto,
        problemes_poms=tuple(problemes),
        problemes_costures=tuple(problemes_sews),
    )


# ─────────────────────────────────────────────────────────────────────────────

def _autovalidar(
    doc_escrit,
    projeccio: ProjectionResult,
    dxf: bytes,
    rul: bytes,
    perfil: str,
) -> Autovalidacio:
    """`read(write(x)) ≡ x`, i dues voltes per demostrar que a més és ESTABLE.

    Les dues comparacions no miren el mateix, i la diferència importa:

      · **Volta 1** (el que volíem escriure ↔ el que hem rellegit): compara la SEMÀNTICA
        —peces, punts, números de regla, POMs— i **no l'empremta**, perquè l'empremta del
        document projectat és la del fitxer d'ORIGEN (que no tenia capa FTT-POM) i la del
        rellegit ja la té. Aquesta diferència és el resultat esperat de l'exportació, no
        un defecte.
      · **Volta 2** (rellegit ↔ tornat a escriure i rellegit): ara sí, TOT, empremta
        inclosa. Aquí les dues bandes han passat pel mateix camí, així que qualsevol
        diferència és degradació pura.
    """
    diferencies: list[str] = []

    try:
        doc_r1 = AAMAReader().read(dxf)
    except PatternEngineError as e:
        return Autovalidacio(
            ok=False,
            diferencies=(f'El fitxer emès no es pot ni tornar a llegir: {e}',),
        )

    # El grading no s'hi compara: un DXF no porta taula de regles (la porta el RUL, que es
    # valida a part). Trobar-la a faltar en un format que no la pot contenir no és detectar
    # un defecte.
    informe_1 = compare(
        doc_escrit, doc_r1, comparar_empremta=False, comparar_grading=False)
    diferencies += [str(d) for d in informe_1.diferencies]

    # Volta 2: el mateix camí, un altre cop. Si el cens es mou, el format no és estable.
    dxf_2 = AAMAWriter().write(
        doc_r1, perfil=perfil, include_ftt_pom_layer=True,
    )
    doc_r2 = AAMAReader().read(dxf_2)
    informe_2 = compare(
        doc_r1, doc_r2, comparar_empremta=True, comparar_grading=False)
    diferencies += [str(d) for d in informe_2.diferencies]

    cens_1 = sum(doc_r1.fingerprint.cens_entitats.values())
    cens_2 = sum(doc_r2.fingerprint.cens_entitats.values())
    if cens_1 != cens_2:
        diferencies.append(
            f'cens_mobil: el fitxer té {cens_1} entitats a la primera volta i {cens_2} a '
            f'la segona. El format no és estable.'
        )

    # El RUL: les regles que escrivim, ¿es tornen a llegir iguals? Amb la resolució DEL
    # FORMAT, que escriu dos decimals en unitats natives (v. `compare_grade_tables`): el
    # RUL quantitza a 0.01, i exigir-li igualtat exacta de floats seria demanar-li una
    # precisió que el fitxer real de PolyPattern no té.
    taula_rellegida = RULReader().read(rul)
    informe_rul = compare_grade_tables(
        projeccio.grade_table, taula_rellegida, tol_deltes=_resolucio_rul(projeccio))
    diferencies += [str(d) for d in informe_rul.diferencies]

    # I els números de regla, punt per punt: que el RUL quadri i el DXF no, seria pitjor
    # que qualsevol dels dos errors per separat.
    regles_escrites = _regles_del_document(doc_escrit)
    regles_rellegides = _regles_del_document(doc_r1)
    if regles_escrites != regles_rellegides:
        diferents = {
            k for k in set(regles_escrites) | set(regles_rellegides)
            if regles_escrites.get(k) != regles_rellegides.get(k)
        }
        # key=str perquè les claus barregen `int` i `None` a la posició de la vora (els
        # piquets no en tenen), i ordenar-les crues peta. Un informe d'error que peta en
        # muntar-se és pitjor que no tenir-ne.
        diferencies.append(
            f'regles_per_punt: {len(diferents)} punts han canviat de número de regla en '
            f'el viatge (p. ex. {sorted(diferents, key=str)[:3]}).'
        )

    return Autovalidacio(
        ok=not diferencies,
        punts_comparats=informe_1.punts_comparats,
        desviacio_maxima_um=max(
            informe_1.desviacio_maxima_um, informe_2.desviacio_maxima_um),
        regles_escrites=len(projeccio.grade_table.regles),
        regles_rellegides=len(taula_rellegida.regles),
        diferencies=tuple(diferencies),
        cens_volta_1=cens_1,
        cens_volta_2=cens_2,
    )


#: Decimals amb què el RULWriter escriu els deltes (format real de PolyPattern).
RUL_DECIMALS = 2


def _resolucio_rul(projeccio: ProjectionResult) -> float:
    """La desviació màxima que el RUL pot introduir tot sol, en mm.

    Escriure amb 2 decimals en unitats natives quantitza a 10^-2 unitats; l'error màxim és
    la meitat del pas. Amb el factor de l'AMELIA (1.0 → natives = mm) surten 5 µm: cinc
    micres, dos ordres de magnitud per sota de qualsevol cosa que una taula de tall pugui
    distingir. Que sigui menyspreable no vol dir que es pugui deixar sense dir: és el
    límit REAL de precisió del que lliurem, i queda escrit aquí i a l'informe.
    """
    factor = projeccio.grade_table.unitats_factor_mm or 1.0
    return (10 ** -RUL_DECIMALS) / 2.0 * factor + 1e-9


def _regles_del_document(doc) -> dict[tuple, int]:
    """(peça, vora, ordre) → número de regla. Per comparar el DXF amb ell mateix."""
    fora: dict[tuple, int] = {}
    for peca in doc.pieces:
        for i, b in enumerate(peca.boundaries):
            for j, p in enumerate(b.points):
                if p.grade_rule is not None:
                    fora[(peca.nom_block, i, j)] = p.grade_rule
        for j, n in enumerate(peca.notches):
            if n.grade_rule is not None:
                fora[(peca.nom_block, None, j)] = n.grade_rule
    return fora


def _amb_capa_pom(doc, specs, previews: tuple[SizePreview, ...]):
    """Penja els POMs ancorats a les peces, perquè el writer els projecti a la capa FTT-POM.

    Els valors que hi van són **els de la talla base**: el DXF porta la geometria de la
    talla mostra, i la capa ha de dir el que aquesta geometria mesura. (Les altres talles
    les reconstrueix el CAD amb les regles; els seus valors viuen a la previsualització,
    no dins el fitxer.)
    """
    from dataclasses import replace

    base = next((p for p in previews if p.es_base), None)
    valors = {
        p.pom_code: p.valor_cm
        for p in (base.poms if base else ())
        if p.valor_cm is not None
    }

    per_peca: dict[str, list[POMAnchorData]] = {}
    for spec in specs:
        peca = doc.piece(spec.peca)
        if peca is None:
            continue
        a = _coord(peca, spec.ref_a)
        b = _coord(peca, spec.ref_b)
        if a is None or b is None:
            continue
        valor_cm = valors.get(spec.pom_code)
        per_peca.setdefault(spec.peca, []).append(POMAnchorData(
            pom_code=spec.pom_code,
            punts_ancora=(a, b),
            definicio_mesura={'nom': spec.nom},
            valor_mesurat_mm=(valor_cm * MM_PER_CM) if valor_cm is not None else None,
        ))

    return replace(doc, pieces=tuple(
        replace(p, poms=tuple(per_peca.get(p.nom_block, ())))
        for p in doc.pieces
    ))


def _coord(peca, ref):
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


def _codi_model(pattern_file) -> str:
    model = pattern_file.model
    if model is None:
        return ''
    return getattr(model, 'codi_intern', '') or str(model.pk)
