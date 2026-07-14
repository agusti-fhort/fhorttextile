"""Writer DXF-AAMA: model geomètric intern → fitxer.

**Reprodueix, no inventa.** Aquesta és tota la llei del mòdul. El writer no "millora"
el fitxer d'origen, no li completa la capçalera que li faltava, no li normalitza els
separadors ni li ordena les capes. Escriu el que l'empremta diu que hi havia, perquè un
fitxer millorat ja no és el fitxer del client: és un fitxer que el seu CAD potser ja no
reconeix com a seu.

Tres reproduccions que semblen detalls i no ho són:

  · **Seccions buides.** El material real porta `HEADER` i `TABLES` sense contingut.
    ezdxf, per bon ciutadà, les omple. El post-procés les torna a buidar si l'empremta
    diu que ho eren.
  · **Separador decimal per camp.** Les coordenades van amb punt i els TEXT amb coma
    (`Quantity: 1,0`) dins el MATEIX fitxer. Unificar-ho seria "netejar" l'origen.
  · **Els TEXT de regla de grading.** El CAD n'escriu un a la capa 2 per cada punt de
    gir, un ADDICIONAL a la capa 8 si el punt pertany a una línia interna, i un a la
    capa 4 per cada piquet. Reproduir aquesta llei —i no una versió raonable
    d'aquesta llei— és el que fa que el recompte d'entitats surti clavat.

PERFILS
-------
El registre està preparat per a N perfils de destí, però **només `polypattern` està
implementat**: és l'únic per al qual tenim material real. Escriure un perfil `tuka` o
`gerber` sense un fitxer d'aquell CAD davant seria inventar-se una empremta, i una
empremta inventada és pitjor que cap: dona la falsa seguretat d'un round-trip verd
contra un format que no hem vist mai. Quan arribi el fitxer, arribarà el perfil.

Per defecte, `write()` fa **reproducció pura**: es guia per l'empremta del document que
va llegir el reader, no per cap perfil. El perfil només mana quan s'exporta cap a un
destí DIFERENT de l'origen.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Optional

import ezdxf

from .errors import PatternEngineError
from .ftt_pom_layer import FTTPOMLayerWriter
from .geometry import (
    Fingerprint,
    LayerRole,
    PatternDocument,
    PieceData,
    PointKind,
)

#: Rol de capa → codi DXF. L'invers d'`AAMA_LAYER_ROLES`: el writer ha de saber a quin
#: número torna cada rol.
ROLE_TO_LAYER: dict[LayerRole, str] = {
    LayerRole.CUT: '1',
    LayerRole.TURN: '2',
    LayerRole.CURVE: '3',
    LayerRole.NOTCH: '4',
    LayerRole.MIRROR: '6',
    LayerRole.GRAIN: '7',
    LayerRole.INTERNAL: '8',
    LayerRole.SEW: '14',
}


@dataclass(frozen=True)
class WriterProfile:
    """Com escriu els fitxers un CAD de destí concret."""
    nom: str
    dxf_version: str = 'R12'
    decimal_coordenades: str = '.'
    decimal_text: str = '.'
    header_buida: bool = False
    tables_buida: bool = False


#: Registre de perfils. Un de sol, i a consciència (v. docstring del mòdul).
PROFILES: dict[str, WriterProfile] = {
    'polypattern': WriterProfile(
        nom='polypattern',
        dxf_version='R12',
        decimal_coordenades='.',
        decimal_text=',',      # 'Quantity: 1,0'
        header_buida=True,
        tables_buida=True,
    ),
}


class UnknownProfileError(PatternEngineError):
    """S'ha demanat un perfil de destí que no tenim.

    És un error dur i ha de ser-ho: el silenci (caure a un perfil per defecte)
    exportaria cap a un CAD real un fitxer amb l'empremta d'un altre.
    """


class AAMAWriter:
    """Implementa la meitat `write` del port `FormatCodec`."""

    def write(
        self,
        doc: PatternDocument,
        perfil: str = '',
        include_ftt_pom_layer: bool = False,
        ftt_meta: Optional[dict] = None,
    ) -> bytes:
        """Reprodueix el document.

        Sense `perfil`, es guia per l'empremta del fitxer d'origen: reproducció pura.
        Amb `perfil`, escriu segons el dialecte del destí demanat.

        `include_ftt_pom_layer` hi afegeix la capa `FTT-POM` amb els POMs ancorats
        (v. `ftt_pom_layer`). És opcional a posta: un destí podria rebutjar una capa que
        no coneix, i llavors ha de poder rebre el fitxer sense.
        """
        cfg = self._config(doc.fingerprint, perfil)
        factor = self._factor(doc.fingerprint)

        out = ezdxf.new(cfg.dxf_version)
        msp = out.modelspace()

        height = doc.fingerprint.text_height or 1.0
        pom_writer = FTTPOMLayerWriter() if include_ftt_pom_layer else None

        for piece in doc.pieces:
            block = out.blocks.new(name=piece.nom_block)
            self._write_piece(block, piece, cfg, factor, height)
            if pom_writer is not None and piece.poms:
                pom_writer.write_piece_poms(block, piece.poms, height=height / factor)
            msp.add_blockref(
                piece.nom_block,
                self._nat(piece.insert_at, factor),
                dxfattribs={'layer': ROLE_TO_LAYER[LayerRole.CUT]},
            )

        self._write_document_texts(msp, doc.fingerprint, factor)

        if pom_writer is not None:
            meta = ftt_meta or {}
            pom_writer.write_document_meta(
                msp,
                versio=meta.get('versio', 0),
                model=meta.get('model', ''),
                ts=meta.get('ts', ''),
                at=self._nat(doc.fingerprint.doc_text_anchor, factor),
                height=height / factor,
            )

        stream = io.StringIO()
        out.write(stream)
        return self._postprocess(stream.getvalue(), cfg)

    # ── configuració ─────────────────────────────────────────────────────────
    def _config(self, fp: Fingerprint, perfil: str) -> WriterProfile:
        if perfil:
            if perfil not in PROFILES:
                raise UnknownProfileError(
                    f"No hi ha perfil d'escriptura per a '{perfil}'. "
                    f"Implementats: {sorted(PROFILES)}. "
                    f"Un perfil s'escriu amb un fitxer real d'aquell CAD al davant, mai d'esma."
                )
            return PROFILES[perfil]

        # Reproducció pura: el perfil ÉS l'empremta del document llegit.
        seps = fp.separador_decimal or {}
        return WriterProfile(
            nom=fp.font_cad or 'reproduccio',
            dxf_version='R12' if fp.dxf_version in ('AC1009', '') else fp.dxf_version,
            decimal_coordenades=seps.get('coordenades', '.'),
            decimal_text=seps.get('text', '.'),
            header_buida=fp.header_buida,
            tables_buida=fp.tables_buida,
        )

    def _factor(self, fp: Fingerprint) -> float:
        """mm → unitats natives del fitxer (l'invers del que va fer el reader)."""
        if fp.unitats and fp.unitats.factor_to_mm:
            return fp.unitats.factor_to_mm
        return 1.0

    def _nat(self, punt: tuple[float, float], factor: float) -> tuple[float, float]:
        return (punt[0] / factor, punt[1] / factor)

    # ── peça ─────────────────────────────────────────────────────────────────
    def _write_piece(
        self, block, piece: PieceData, cfg: WriterProfile, factor: float, height: float
    ) -> None:
        # 1. Contorns (tall, internes, cosit si n'hi ha).
        for boundary in piece.boundaries:
            layer = ROLE_TO_LAYER.get(boundary.role, boundary.layer)
            punts = [self._nat((p.x, p.y), factor) for p in boundary.points]
            if boundary.closed and punts:
                # El CAD tanca repetint el primer vèrtex; el model intern no el guarda.
                punts.append(punts[0])
            if punts:
                block.add_polyline2d(punts, dxfattribs={'layer': layer})

        # 2. Els POINT que classifiquen els vèrtexs: capa 2 (gir) i capa 3 (corba),
        #    exactament damunt del punt que qualifiquen.
        for boundary in piece.boundaries:
            for p in boundary.points:
                capa = {
                    PointKind.TURN: ROLE_TO_LAYER[LayerRole.TURN],
                    PointKind.CURVE: ROLE_TO_LAYER[LayerRole.CURVE],
                }.get(p.kind)
                if capa:
                    block.add_point(self._nat((p.x, p.y), factor), dxfattribs={'layer': capa})

        # 3. Piquets.
        for n in piece.notches:
            block.add_point(
                self._nat((n.x, n.y), factor),
                dxfattribs={'layer': ROLE_TO_LAYER[LayerRole.NOTCH]},
            )

        # 4. Fil de la roba.
        if piece.grain:
            g = piece.grain
            block.add_line(
                self._nat((g.x1, g.y1), factor),
                self._nat((g.x2, g.y2), factor),
                dxfattribs={'layer': ROLE_TO_LAYER[LayerRole.GRAIN]},
            )

        # 5. Metadades de la peça (capa 1), al lloc on el CAD les posava.
        for text in self._metadata_texts(piece, cfg):
            self._add_text(block, text, piece.metadata.anchor, factor, height,
                           ROLE_TO_LAYER[LayerRole.CUT])

        # 6. Els TEXT de regla de grading, segons la llei del CAD (v. docstring).
        self._write_rule_texts(block, piece, factor, height)

        # 7. El que no entenem, tal com era.
        for raw in piece.raw_entities:
            self._write_raw(block, raw, factor)

    def _write_rule_texts(self, block, piece: PieceData, factor: float, height: float) -> None:
        for boundary in piece.boundaries:
            interna = boundary.role is LayerRole.INTERNAL
            for p in boundary.points:
                if p.grade_rule is None:
                    continue
                etiqueta = f'# {p.grade_rule}'
                self._add_text(block, etiqueta, (p.x, p.y), factor, height,
                               ROLE_TO_LAYER[LayerRole.TURN])
                if interna:
                    # El CAD duplica l'etiqueta a la capa de la línia interna.
                    self._add_text(block, etiqueta, (p.x, p.y), factor, height,
                                   ROLE_TO_LAYER[LayerRole.INTERNAL])

        for n in piece.notches:
            if n.grade_rule is not None:
                self._add_text(block, f'# {n.grade_rule}', (n.x, n.y), factor, height,
                               ROLE_TO_LAYER[LayerRole.NOTCH])

    def _metadata_texts(self, piece: PieceData, cfg: WriterProfile) -> list[str]:
        """Els TEXT 'Clau: valor' de la capa 1, amb el separador decimal del destí."""
        m = piece.metadata
        textos: list[str] = []
        if m.piece_name:
            textos.append(f'Piece Name: {m.piece_name}')
        if m.size:
            textos.append(f'Size: {m.size}')
        if m.quantity is not None:
            numero = f'{m.quantity:.1f}'.replace('.', cfg.decimal_text)
            textos.append(f'Quantity: {numero}')
        if m.material:
            textos.append(f'Material: {m.material}')
        for clau, valor in m.extra.items():
            textos.append(f'{clau.title()}: {valor}')
        return textos

    def _write_raw(self, block, raw, factor: float) -> None:
        punts = [self._nat(p, factor) for p in raw.punts]
        if raw.dxftype == 'TEXT' and punts:
            block.add_text(
                raw.text,
                dxfattribs={'layer': raw.layer, 'height': raw.height / factor or 1.0},
            ).set_placement(punts[0])
        elif raw.dxftype == 'POINT' and punts:
            block.add_point(punts[0], dxfattribs={'layer': raw.layer})
        elif raw.dxftype == 'LINE' and len(punts) >= 2:
            block.add_line(punts[0], punts[1], dxfattribs={'layer': raw.layer})
        elif raw.dxftype == 'POLYLINE' and punts:
            block.add_polyline2d(punts, dxfattribs={'layer': raw.layer})

    def _write_document_texts(self, msp, fp: Fingerprint, factor: float) -> None:
        for text in fp.textos_document:
            msp.add_text(
                text,
                dxfattribs={
                    'layer': ROLE_TO_LAYER[LayerRole.CUT],
                    'height': (fp.text_height / factor) or 1.0,
                },
            ).set_placement(self._nat(fp.doc_text_anchor, factor))

    def _add_text(self, block, text: str, punt, factor: float, height: float, capa: str) -> None:
        block.add_text(
            text,
            dxfattribs={'layer': capa, 'height': height / factor},
        ).set_placement(self._nat(punt, factor))

    # ── post-procés: el que ezdxf no ens deixa fer d'entrada ─────────────────
    def _postprocess(self, text: str, cfg: WriterProfile) -> bytes:
        buides = set()
        if cfg.header_buida:
            buides.add('HEADER')
        if cfg.tables_buida:
            buides.add('TABLES')
        if buides:
            text = _empty_out_sections(text, buides)
        if cfg.decimal_coordenades == ',':
            text = _coords_to_comma(text)
        return text.encode('utf-8')


def _empty_out_sections(text: str, noms: set[str]) -> str:
    """Deixa les seccions indicades tal com les tenia l'origen: buides.

    ezdxf no permet no escriure la HEADER, així que es buida a posteriori, sobre el
    text del DXF (que és una llista plana de parells codi/valor).
    """
    linies = text.splitlines()
    sortida: list[str] = []
    i = 0
    n = len(linies)
    while i < n:
        if (linies[i].strip() == 'SECTION'
                and i + 2 < n
                and linies[i + 1].strip() == '2'
                and linies[i + 2].strip() in noms):
            sortida += [linies[i], linies[i + 1], linies[i + 2], '  0', 'ENDSEC']
            # Saltem fins a l'ENDSEC real d'aquesta secció.
            i += 3
            while i < n and linies[i].strip() != 'ENDSEC':
                i += 1
            i += 1  # ens mengem l'ENDSEC original
            continue
        sortida.append(linies[i])
        i += 1
    return '\n'.join(sortida) + '\n'


def _coords_to_comma(text: str) -> str:
    """Coordenades amb coma decimal, per als CAD que les escriuen així.

    Cap dels fitxers que tenim ho fa (PolyPattern usa punt a les coordenades i coma
    només dins els TEXT), però el mecanisme de perfils ha de poder-ho fer: és
    precisament la mena de detall que fa que un CAD rebutgi un fitxer.
    """
    codis_coord = {'10', '20', '30', '11', '21', '31', '40'}
    linies = text.splitlines()
    for i in range(0, len(linies) - 1):
        if linies[i].strip() in codis_coord:
            valor = linies[i + 1]
            if '.' in valor and not valor.strip().startswith('$'):
                linies[i + 1] = valor.replace('.', ',')
    return '\n'.join(linies) + '\n'
